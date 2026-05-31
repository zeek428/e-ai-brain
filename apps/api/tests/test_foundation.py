from pathlib import Path

from fastapi.testclient import TestClient

from app.main import _tcp_endpoint_from_url, app

client = TestClient(app)


def test_health_includes_dependencies_and_trace_id():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["postgres"] in {"ok", "error"}
    assert body["redis"] in {"ok", "error"}
    assert body["model_gateway"] in {"configured", "local_fallback"}
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


def test_initial_migration_matches_runtime_record_shapes():
    migration = Path("app/db/migrations/001_init.sql").read_text()

    assert "stage text NOT NULL" in migration
    assert "content jsonb NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "review_type text NOT NULL" not in migration
    assert "original_content jsonb" not in migration

    assert "task_id text NOT NULL REFERENCES ai_tasks(id)" in migration
    assert "executor jsonb NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "executor_type text NOT NULL" not in migration
    assert "executor_name text NOT NULL" not in migration

    assert "created_by text NOT NULL" in migration
