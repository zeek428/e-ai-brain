import re
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from app.main import _tcp_endpoint_from_url, app

client = TestClient(app)


def test_health_includes_dependencies_and_trace_id(monkeypatch):
    monkeypatch.setattr(main.settings, "model_gateway_base_url", "")
    monkeypatch.setattr(main.settings, "model_gateway_api_key", "")

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["postgres"] in {"ok", "error"}
    assert body["redis"] in {"ok", "error"}
    assert body["model_gateway"] == "not_configured"
    assert body["long_memory"] == "not_configured"
    assert body["trace_id"].startswith("trace_")


def test_health_dependency_endpoint_parsing_supports_docker_service_names():
    assert _tcp_endpoint_from_url(
        "postgresql://ai_brain:password@postgres:5432/ai_brain",
        "127.0.0.1",
        5432,
    ) == ("postgres", 5432)
    assert _tcp_endpoint_from_url("redis://redis:6379/0", "127.0.0.1", 6379) == (
        "redis",
        6379,
    )


def auth_headers() -> dict[str, str]:
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = login_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_long_memory_status_reports_not_configured_without_gbrain(monkeypatch):
    monkeypatch.setattr(main.settings, "gbrain_base_url", "")
    monkeypatch.setattr(main.settings, "gbrain_api_key", "")

    response = client.get("/api/long-memory/status", headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"].startswith("trace_")
    assert body["data"] == {
        "api_key_configured": False,
        "base_url_configured": False,
        "capabilities": [],
        "connector": "gbrain",
        "fallback_retriever": "postgres_pgvector",
        "status": "not_configured",
    }


def test_long_memory_status_masks_configured_gbrain_secret(monkeypatch):
    monkeypatch.setattr(main.settings, "gbrain_base_url", "https://gbrain.internal")
    monkeypatch.setattr(main.settings, "gbrain_api_key", "secret-gbrain-key")

    response = client.get("/api/long-memory/status", headers=auth_headers())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "configured"
    assert data["base_url_configured"] is True
    assert data["api_key_configured"] is True
    assert data["capabilities"] == [
        "hybrid_retrieval",
        "answer_synthesis",
        "knowledge_graph",
    ]
    assert "secret-gbrain-key" not in str(data)


def test_login_and_current_user_use_bearer_token():
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )

    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["trace_id"].startswith("trace_")
    assert login_body["data"]["token_type"] == "bearer"
    token = login_body["data"]["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["trace_id"].startswith("trace_")
    assert me_body["data"] == {
        "id": "user_admin",
        "username": "admin@example.com",
        "display_name": "AI Brain Admin",
        "roles": ["admin"],
    }


def test_api_errors_include_trace_id_and_error_code():
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "UNAUTHORIZED"
    assert body["detail"]["trace_id"].startswith("trace_")


def test_logout_requires_bearer_token():
    response = client.post("/api/auth/logout")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_role_catalog_defines_supported_mvp_roles():
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = login_response.json()["data"]["access_token"]

    response = client.get("/api/auth/roles", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"].startswith("trace_")
    assert body["data"]["total"] == 6
    roles = body["data"]["items"]
    assert [role["code"] for role in roles] == [
        "admin",
        "product_owner",
        "rd_owner",
        "reviewer",
        "knowledge_owner",
        "viewer",
    ]
    assert roles[0]["name"] == "系统管理员"
    assert "system.users.manage" in roles[0]["permissions"]
    assert all(role["description"] for role in roles)
    assert all(role["responsibilities"] for role in roles)
    assert all(role["data_scope"] for role in roles)
    assert all(role["decision_scope"] for role in roles)
    assert all(role["business_roles"] for role in roles)
    assert all(role["menu_scope"] for role in roles)
    assert all(role["limitations"] for role in roles)
    assert [role["sort_order"] for role in roles] == [10, 20, 30, 40, 50, 60]
    assert roles[0]["business_roles"] == ["平台管理员"]
    assert "系统管理" in roles[0]["menu_scope"]
    assert roles[1]["responsibilities"][1] == "审批需求并从已批准需求生成 AI 任务。"
    assert roles[5]["decision_scope"] == "无写入或审批决策权限。"
    assert "不能执行写操作、审批或配置变更。" in roles[5]["limitations"]

    unsupported_role = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "bad-role@example.com",
            "display_name": "Bad Role",
            "password": "password123",
            "roles": ["viewer", "undefined_role"],
            "status": "active",
        },
    )
    assert unsupported_role.status_code == 400
    assert unsupported_role.json()["detail"]["code"] == "VALIDATION_ERROR"

    duplicate_role = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "duplicate-role@example.com",
            "display_name": "Duplicate Role",
            "password": "password123",
            "roles": ["viewer", "viewer"],
            "status": "active",
        },
    )
    assert duplicate_role.status_code == 400
    assert duplicate_role.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_initial_migration_defines_core_mvp_tables():
    migration = Path("app/db/migrations/001_init.sql").read_text()

    for table_name in [
        "role_definitions",
        "users",
        "brain_apps",
        "ai_tasks",
        "human_reviews",
        "gitlab_mr_snapshots",
        "code_review_reports",
        "knowledge_documents",
        "knowledge_chunks",
        "knowledge_deposits",
        "mock_issues",
        "bugs",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in migration


def test_all_structured_tables_define_created_and_updated_timestamps():
    missing: list[str] = []
    for migration_path in sorted(Path("app/db/migrations").glob("*.sql")):
        migration = migration_path.read_text()
        for match in re.finditer(
            r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+)\s*\((.*?)\n\);",
            migration,
            flags=re.DOTALL,
        ):
            table_name = match.group(1)
            table_body = match.group(2)
            for column_name in ("created_at", "updated_at"):
                if not re.search(rf"\b{column_name}\s+timestamptz\b", table_body):
                    missing.append(f"{migration_path.name}:{table_name}.{column_name}")

    assert missing == []


def test_initial_migration_matches_runtime_record_shapes():
    migration = Path("app/db/migrations/001_init.sql").read_text()

    assert "stage text NOT NULL" in migration
    assert "content jsonb NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "responsibilities jsonb NOT NULL DEFAULT '[]'::jsonb" in migration
    assert "data_scope text NOT NULL DEFAULT ''" in migration
    assert "decision_scope text NOT NULL DEFAULT ''" in migration
    assert "id text PRIMARY KEY" in migration
    assert "sequence integer NOT NULL DEFAULT 0" in migration
    assert "review_type text NOT NULL" not in migration
    assert "original_content jsonb" not in migration

    assert "task_id text NOT NULL REFERENCES ai_tasks(id)" in migration
    assert "executor jsonb NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "executor_type text NOT NULL" not in migration
    assert "executor_name text NOT NULL" not in migration

    assert "created_by text NOT NULL" in migration


def test_pgvector_migration_defines_knowledge_embedding_index():
    migrations = "\n".join(
        path.read_text()
        for path in sorted(Path("app/db/migrations").glob("*.sql"))
    )

    assert "CREATE EXTENSION IF NOT EXISTS vector" in migrations
    assert "idx_knowledge_chunks_embedding" in migrations
    assert "USING hnsw" in migrations
    assert "vector_cosine_ops" in migrations
