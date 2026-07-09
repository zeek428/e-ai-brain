import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.core.config import Settings
from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.store import MemoryStore
from app.main import app
from app.services.platform_status import runtime_data_access_mode, tcp_endpoint_from_url
from app.services.plugin_constants import PLUGIN_PROTOCOLS
from app.services.plugin_templates import STANDARD_PLUGIN_CONNECTION_DEFAULTS
from app.services.task_workflow_context import task_workflow_read_store, task_workflow_source_store

client = TestClient(app)


def test_settings_default_to_postgres_outside_tests(monkeypatch):
    monkeypatch.delenv("PERSISTENCE_MODE", raising=False)

    assert Settings().persistence_mode == "postgres"


def test_local_network_cors_origin_regex_defaults_to_local_dev_only(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_LOCAL_NETWORK_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "local")

    assert Settings().cors_origin_regex is not None

    monkeypatch.setenv("APP_ENV", "production")

    assert Settings().cors_origin_regex is None


def test_runtime_security_rejects_placeholder_secret_outside_local_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        Settings().validate_runtime_security()


def test_runtime_security_rejects_seeded_users_outside_local_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_SECRET_KEY", "production-secret-key-with-more-than-32-characters")
    monkeypatch.setenv("ALLOW_SEEDED_USERS", "true")

    with pytest.raises(RuntimeError, match="ALLOW_SEEDED_USERS"):
        Settings().validate_runtime_security()


def test_runtime_security_allows_strong_secret_outside_local_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_SECRET_KEY", "production-secret-key-with-more-than-32-characters")
    monkeypatch.delenv("ALLOW_SEEDED_USERS", raising=False)

    Settings().validate_runtime_security()


def test_cors_preflight_allows_local_network_frontend_origin():
    response = client.options(
        "/api/auth/providers",
        headers={
            "Access-Control-Request-Headers": "content-type",
            "Access-Control-Request-Method": "GET",
            "Origin": "http://192.168.71.198:5173",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://192.168.71.198:5173"


def test_build_store_rejects_memory_mode_outside_tests(monkeypatch):
    monkeypatch.setattr(main.settings, "app_env", "local")
    monkeypatch.setattr(main.settings, "persistence_mode", "memory")

    try:
        try:
            main.build_store()
        except RuntimeError as exc:
            assert "PERSISTENCE_MODE=memory" in str(exc)
        else:
            raise AssertionError("build_store should reject memory mode outside tests")
    finally:
        monkeypatch.setattr(main.settings, "app_env", "test")
        monkeypatch.setattr(main.settings, "persistence_mode", "memory")


def test_build_store_uses_postgres_runtime_container(monkeypatch):
    monkeypatch.setattr(main.settings, "persistence_mode", "postgres")

    runtime_store = main.build_store()

    assert isinstance(runtime_store, PostgresRuntimeStore)
    assert not isinstance(runtime_store, PersistentMemoryStore)
    assert hasattr(runtime_store, "repository")
    assert runtime_store.products == {}
    assert runtime_store.requirements == {}
    assert runtime_store.ai_tasks == {}


def test_repository_read_model_store_does_not_restore_snapshot_payload():
    class SnapshotRestoreForbiddenRepository:
        def load(self) -> dict:
            raise AssertionError("repository read snapshot should not be restored")

    runtime_store = PostgresRuntimeStore(SnapshotRestoreForbiddenRepository())

    assert task_workflow_read_store(runtime_store) is runtime_store


def test_repository_source_context_is_not_memory_store():
    class SourceRowsRepository:
        def __init__(self) -> None:
            self.counter = 0

        def next_id(self, prefix: str) -> str:
            self.counter += 1
            return f"{prefix}_{self.counter:03d}"

    context = task_workflow_source_store({}, repository=SourceRowsRepository())

    assert not isinstance(context, MemoryStore)
    assert context.new_id("task") == "task_001"
    event = context.audit(
        event_type="db_first.context_checked",
        actor_id="user_admin",
        subject_type="runtime_context",
        subject_id="postgres_source_rows",
    )
    assert event["id"] == "audit_002"
    assert context.audit_events == [event]


def test_postgres_runtime_reports_db_first_migration_mode(monkeypatch):
    monkeypatch.setattr(main.settings, "persistence_mode", "postgres")

    assert runtime_data_access_mode(main.settings) == "db_first_migration"


def test_health_includes_dependencies_and_trace_id(monkeypatch):
    app.state.store.reset()
    monkeypatch.setattr(main.settings, "model_gateway_base_url", "")
    monkeypatch.setattr(main.settings, "model_gateway_api_key", "")

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["postgres"] in {"ok", "error"}
    assert body["redis"] in {"ok", "error"}
    assert body["model_gateway"] == "not_configured"
    assert body["data_access_mode"] in {"db_first_migration", "memory_test_helper"}
    assert body["long_memory"] == "not_configured"
    assert body["trace_id"].startswith("trace_")


def test_health_uses_persisted_default_model_gateway_config(monkeypatch):
    app.state.store.reset()
    monkeypatch.setattr(main.settings, "model_gateway_base_url", "")
    monkeypatch.setattr(main.settings, "model_gateway_api_key", "")
    app.state.store.model_gateway_configs["model_gateway_config_health"] = {
        "id": "model_gateway_config_health",
        "name": "健康检查模型网关",
        "provider": "openai_compatible",
        "base_url": "http://model-gateway.test/v1",
        "api_key": "sk-health",
        "default_chat_model": "chat",
        "default_embedding_model": "embedding",
        "timeout_seconds": 60,
        "max_retries": 0,
        "status": "active",
        "is_default": True,
    }

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["model_gateway"] == "configured"


def test_system_health_center_aggregates_dependency_and_configuration_checks(monkeypatch):
    app.state.store.reset()
    monkeypatch.setattr(main.settings, "object_storage_provider", "local")
    monkeypatch.setattr(main.settings, "dingtalk_login_enabled", True)
    monkeypatch.setattr(main.settings, "dingtalk_client_id", "ding-client")
    monkeypatch.setattr(main.settings, "dingtalk_client_secret", "ding-secret")
    monkeypatch.setattr(main.settings, "dingtalk_redirect_uri", "https://example.com/api/auth/dingtalk/callback")
    monkeypatch.setattr(main.settings, "dingtalk_corp_name_map", {"dingcorp_health": "青锋科技"})
    app.state.store.model_gateway_configs["model_gateway_config_health_center"] = {
        "id": "model_gateway_config_health_center",
        "name": "健康中心模型网关",
        "provider": "openai_compatible",
        "base_url": "http://model-gateway.test/v1",
        "api_key": "sk-health-center",
        "default_chat_model": "chat",
        "default_embedding_model": "embedding",
        "timeout_seconds": 60,
        "max_retries": 0,
        "status": "active",
        "is_default": True,
    }
    app.state.store.integration_plugins["plugin_dingtalk_health_center"] = {
        "id": "plugin_dingtalk_health_center",
        "code": "dingtalk-doc",
        "name": "钉钉知识库",
        "status": "active",
    }
    app.state.store.plugin_connections["connection_dingtalk_health_center"] = {
        "id": "connection_dingtalk_health_center",
        "auth_config": {
            "auth_subject_type": "system",
            "corp_id": "dingcorp_health",
            "key_expires_at": "2030-01-01T00:00:00+00:00",
            "secret_ref": "vault/dingtalk/shared/url_key",
            "url_key": "secret-url-key",
        },
        "plugin_code": "dingtalk-doc",
        "plugin_name": "钉钉知识库",
        "status": "error",
        "error_message": "request failed for https://mcp.example.test/wiki?key=secret-url-key&token=secret-token",
    }
    app.state.store.products["product_health_center"] = {
        "id": "product_health_center",
        "code": "health-center",
        "name": "健康中心产品",
        "status": "active",
    }
    app.state.store.product_versions["product_version_health_center"] = {
        "id": "product_version_health_center",
        "product_id": "product_health_center",
        "name": "v1",
        "status": "active",
    }
    app.state.store.product_modules["product_module_health_center"] = {
        "id": "product_module_health_center",
        "product_id": "product_health_center",
        "name": "运维模块",
        "status": "active",
    }
    app.state.store.product_git_repositories["product_git_health_center"] = {
        "id": "product_git_health_center",
        "product_id": "product_health_center",
        "name": "健康中心代码库",
        "status": "active",
    }
    app.state.store.knowledge_documents["knowledge_document_health_center"] = {
        "id": "knowledge_document_health_center",
        "chunk_count": 4,
        "knowledge_space_id": "knowledge_space_health_center",
        "product_id": "product_health_center",
        "title": "健康中心说明",
        "index_status": "indexed",
        "permission_roles": ["admin"],
        "updated_at": "2030-01-01T00:00:00+00:00",
    }
    app.state.store.knowledge_documents["knowledge_document_health_failed"] = {
        "id": "knowledge_document_health_failed",
        "chunk_count": 0,
        "knowledge_space_id": "knowledge_space_health_center",
        "product_id": "product_health_center",
        "title": "失败索引文档",
        "index_status": "index_failed",
        "permission_roles": ["admin"],
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    app.state.store.knowledge_documents["knowledge_document_health_stale"] = {
        "id": "knowledge_document_health_stale",
        "chunk_count": 2,
        "knowledge_space_id": "knowledge_space_health_center",
        "product_id": "product_health_center",
        "title": "长期未更新文档",
        "index_status": "text_indexed",
        "permission_roles": ["admin"],
        "updated_at": "2024-01-01T00:00:00+00:00",
    }
    app.state.store.knowledge_spaces["knowledge_space_health_center"] = {
        "id": "knowledge_space_health_center",
        "name": "健康中心空间",
        "product_id": "product_health_center",
        "status": "active",
    }
    app.state.store.knowledge_assets["knowledge_asset_orphan"] = {
        "id": "knowledge_asset_orphan",
        "bucket": "ai-brain",
        "document_id": "knowledge_document_deleted",
        "object_key": "knowledge/deleted.pdf",
    }
    app.state.store.knowledge_import_jobs["knowledge_import_job_old"] = {
        "id": "knowledge_import_job_old",
        "created_at": "2024-01-01T00:00:00+00:00",
        "status": "completed",
    }
    app.state.store.model_gateway_logs.append(
        {
            "id": "model_log_old",
            "created_at": "2024-01-01T00:00:00+00:00",
            "purpose": "retention-check",
            "status": "success",
        }
    )
    app.state.store.audit_events.append(
        {
            "id": "audit_event_old",
            "created_at": "2024-01-01T00:00:00+00:00",
            "event_type": "system.settings.updated",
            "result": "success",
        }
    )
    app.state.store.scheduled_job_runs["scheduled_job_run_old"] = {
        "id": "scheduled_job_run_old",
        "created_at": "2024-01-01T00:00:00+00:00",
        "status": "success",
    }
    app.state.store.ai_executor_runners["runner_health_center"] = {
        "id": "runner_health_center",
        "name": "本地 Runner",
        "max_concurrent_tasks": 2,
        "status": "active",
    }
    app.state.store.ai_executor_tasks["ai_executor_task_health_center"] = {
        "id": "ai_executor_task_health_center",
        "executor_type": "openclaw",
        "runner_id": "runner_health_center",
        "status": "queued",
    }
    app.state.store.ai_executor_tasks["ai_executor_task_health_failed"] = {
        "id": "ai_executor_task_health_failed",
        "error_code": "AI_EXECUTOR_TASK_FAILED",
        "error_message": "runner command exited with code 1",
        "executor_type": "openclaw",
        "runner_id": "runner_health_center",
        "status": "failed",
    }

    response = client.get("/api/system/health", headers=auth_headers())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["overall_status"] in {"ok", "warning", "degraded", "error"}
    assert data["summary"]["total"] >= 10
    checks = {item["key"]: item for item in data["checks"]}
    assert {"postgres", "redis", "pgvector", "smtp", "dingtalk_login", "model_gateway"} <= set(checks)
    assert checks["dingtalk_login"]["status"] == "configured"
    assert checks["model_gateway"]["metrics"]["embedding_gateway"] in {
        "configured",
        "disabled",
        "failed",
        "not_configured",
    }
    assert checks["dingtalk_mcp"]["last_error"] == (
        "request failed for https://mcp.example.test/wiki?key=***&token=***"
    )
    operations = data["operations"]
    assert operations["alert_center"]["summary"]["open_count"] >= 1
    assert operations["ai_executor_ops"]["summary"]["queued_count"] == 1
    assert operations["ai_executor_ops"]["operation_targets"] == {
        "cancellable_count": 1,
        "retryable_count": 1,
        "timeout_scan_count": 0,
    }
    assert operations["ai_executor_ops"]["latest_active_tasks"][0]["id"] == (
        "ai_executor_task_health_center"
    )
    assert operations["ai_executor_ops"]["latest_failures"][0]["id"] == (
        "ai_executor_task_health_failed"
    )
    assert operations["ai_executor_ops"]["failure_reason_distribution"][0] == {
        "count": 1,
        "reason": "AI_EXECUTOR_TASK_FAILED",
    }
    assert operations["dingtalk_lifecycle"]["mcp"]["connection_count"] == 1
    assert operations["dingtalk_lifecycle"]["authorization_subject_summary"]["system"] == 1
    dingtalk_subject = operations["dingtalk_lifecycle"]["authorization_subjects"][0]
    assert dingtalk_subject["subject_type_label"] == "系统授权"
    assert dingtalk_subject["corp_name"] == "青锋科技"
    assert dingtalk_subject["secret_ref_configured"] is True
    assert dingtalk_subject["expires_at"] == "2030-01-01T00:00:00+00:00"
    assert operations["knowledge_quality_loop"]["summary"]["total_documents"] >= 1
    retention = operations["help_and_retention"]
    assert retention["cleanup_status"]["total_expired_count"] >= 3
    assert any(
        item["policy_key"] == "model_gateway_logs"
        and item["title"] == "retention-check"
        for item in retention["cleanup_status"]["expired_records"]
    )
    assert retention["object_storage_cleanup"]["orphan_asset_count"] == 1
    assert retention["object_storage_cleanup"]["sample_assets"][0]["asset_id"] == "knowledge_asset_orphan"
    knowledge_governance = operations["knowledge_quality_loop"]["governance_summary"]
    assert knowledge_governance["governance_candidate_count"] >= 2
    assert knowledge_governance["index_failed_document_count"] >= 1
    assert knowledge_governance["keyword_only_document_count"] >= 1
    assert knowledge_governance["stale_document_count"] >= 1
    knowledge_candidates = operations["knowledge_quality_loop"]["governance_candidates"]
    assert any(item["title"] == "失败索引文档" for item in knowledge_candidates)
    assert any(
        item["title"] == "长期未更新文档"
        and item["knowledge_space_name"] == "健康中心空间"
        and "补齐 Embedding" in item["suggested_action"]
        for item in knowledge_candidates
    )
    assert operations["permission_diagnostics"]["summary"]["active_role_count"] >= 1
    product_scores = operations["product_onboarding_scores"]["products"]
    assert any(item["product_id"] == "product_health_center" for item in product_scores)
    assert "secret-url-key" not in response.text
    assert "secret-token" not in response.text
    assert data["trace_id"].startswith("trace_")


def test_health_dependency_endpoint_parsing_supports_docker_service_names():
    assert tcp_endpoint_from_url(
        "postgresql://ai_brain:password@postgres:5432/ai_brain",
        "127.0.0.1",
        5432,
    ) == ("postgres", 5432)
    assert tcp_endpoint_from_url("redis://redis:6379/0", "127.0.0.1", 6379) == (
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


def test_api_requests_do_not_call_global_request_end_persist():
    original_store = app.state.store

    class PersistTrackingStore:
        def __init__(self) -> None:
            self.persist_calls = 0

        def persist(self) -> None:
            self.persist_calls += 1

    tracking_store = PersistTrackingStore()
    app.state.store = tracking_store
    try:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )

        assert response.status_code == 200
        assert tracking_store.persist_calls == 0
    finally:
        app.state.store = original_store


def test_brain_apps_read_from_repository_under_postgres_runtime():
    original_store = app.state.store

    class BrainAppsRepository:
        def load_brain_apps(self) -> dict:
            return {
                "brain_apps": {
                    "rd_brain": {
                        "id": "rd_brain",
                        "code": "rd_brain",
                        "name": "研发大脑",
                        "description": "Repository backed brain app",
                        "status": "active",
                    }
                }
            }

    app.state.store = PostgresRuntimeStore(BrainAppsRepository())
    try:
        response = client.get("/api/brain-apps", headers=auth_headers())
        detail_response = client.get("/api/brain-apps/rd_brain", headers=auth_headers())

        assert response.status_code == 200
        assert response.json()["data"]["items"] == [
            {
                "id": "rd_brain",
                "code": "rd_brain",
                "name": "研发大脑",
                "description": "Repository backed brain app",
                "status": "active",
            }
        ]
        assert detail_response.status_code == 200
        assert detail_response.json()["data"]["code"] == "rd_brain"
    finally:
        app.state.store = original_store


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
    assert {
        "id": me_body["data"]["id"],
        "username": me_body["data"]["username"],
        "display_name": me_body["data"]["display_name"],
        "roles": me_body["data"]["roles"],
    } == {
        "id": "user_admin",
        "username": "admin@example.com",
        "display_name": "AI Brain Admin",
        "roles": ["admin"],
    }
    assert "system.roles.manage" in me_body["data"]["permissions"]
    assert me_body["data"]["scope_summary"]
    assert me_body["data"]["menu_tree"]
    assert "/system/departments" in me_body["data"]["route_permissions"]
    assert "/system/roles" not in me_body["data"]["route_permissions"]


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
    assert body["data"]["total"] == 10
    roles = body["data"]["items"]
    assert [role["code"] for role in roles][:6] == [
        "admin",
        "product_owner",
        "rd_owner",
        "reviewer",
        "knowledge_owner",
        "viewer",
    ]
    assert [role["code"] for role in roles][6:] == [
        "developer",
        "test_owner",
        "tester",
        "release_owner",
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
    assert [role["sort_order"] for role in roles] == [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
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


def test_role_catalog_supports_server_pagination_sort_filters_and_observability():
    headers = auth_headers()

    response = client.get(
        "/api/auth/roles?category=delivery&business_role=产品负责人"
        "&page=1&page_size=1&sort_by=sort_order&sort_order=asc",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] == 1

    testing_response = client.get(
        "/api/auth/roles?category=testing&page=1&page_size=10",
        headers=headers,
    )
    assert testing_response.status_code == 200
    assert {
        role["code"]
        for role in testing_response.json()["data"]["items"]
    } == {"test_owner", "tester"}
    assert body["items"][0]["code"] == "product_owner"
    assert body["query"]["name"] == "roles"
    assert body["query"]["filters"] == {
        "business_role": "产品负责人",
        "category": "delivery",
    }
    assert body["performance"]["p95_target_ms"] == 300
    assert body["performance"]["result_count"] == 1

    unsupported = client.get(
        "/api/auth/roles?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_user_list_supports_server_pagination_sort_filters_and_observability():
    headers = auth_headers()
    for username, display_name, status in [
        ("server-list-a@example.com", "Server List Alpha", "active"),
        ("server-list-b@example.com", "Server List Beta", "inactive"),
    ]:
        created = client.post(
            "/api/users",
            headers=headers,
            json={
                "display_name": display_name,
                "password": "password123",
                "roles": ["viewer"],
                "status": status,
                "username": username,
            },
        )
        if created.status_code not in {200, 409}:
            raise AssertionError(created.text)

    response = client.get(
        "/api/users?display_name=Server%20List&role=viewer&status=inactive"
        "&page=1&page_size=1&sort_by=username&sort_order=desc",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] >= 1
    assert body["items"][0]["username"] == "server-list-b@example.com"
    assert body["query"]["name"] == "users"
    assert body["query"]["filters"] == {
        "display_name": "Server List",
        "role": "viewer",
        "status": "inactive",
    }
    assert body["performance"]["p95_target_ms"] == 300
    assert body["performance"]["result_count"] == 1

    unsupported = client.get("/api/users?page=1&page_size=10&sort_by=unsupported", headers=headers)
    assert unsupported.status_code == 400
    assert unsupported.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_core_management_lists_expose_explicit_p95_targets():
    headers = auth_headers()
    cases = [
        ("/api/products?page=1&page_size=1&sort_by=display_order&sort_order=asc", "products", 300),
        (
            "/api/product-versions?page=1&page_size=1&sort_by=code&sort_order=asc",
            "product_versions",
            300,
        ),
        (
            "/api/knowledge/documents?page=1&page_size=1&sort_by=created_at&sort_order=desc",
            "knowledge_documents",
            400,
        ),
        (
            "/api/audit/events?page=1&page_size=1&sort_by=created_at&sort_order=desc",
            "audit_events",
            500,
        ),
    ]

    for path, list_name, p95_target_ms in cases:
        response = client.get(path, headers=headers)

        assert response.status_code == 200, response.text
        body = response.json()["data"]
        assert body["query"]["name"] == list_name
        assert body["query"]["page"] == 1
        assert body["query"]["page_size"] == 1
        assert body["performance"]["p95_target_ms"] == p95_target_ms
        assert "duration_ms" in body["performance"]
        assert "result_count" in body["performance"]
        assert "total" in body["performance"]


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


def test_migrations_define_db_first_id_counters():
    migrations = "\n".join(
        path.read_text()
        for path in sorted(Path("app/db/migrations").glob("*.sql"))
    )

    assert "CREATE TABLE IF NOT EXISTS id_counters" in migrations
    assert "prefix text PRIMARY KEY" in migrations
    assert "next_value integer NOT NULL DEFAULT 1" in migrations


def test_integration_plugin_protocol_constraints_cover_supported_protocols():
    missing_by_migration: list[str] = []
    for migration_path in sorted(Path("app/db/migrations").glob("*.sql")):
        migration = migration_path.read_text()
        if "ck_integration_plugins_protocol" not in migration:
            continue
        for protocol in sorted(PLUGIN_PROTOCOLS):
            if f"'{protocol}'" not in migration:
                missing_by_migration.append(f"{migration_path.name} missing {protocol}")

    assert not missing_by_migration, (
        "All migrations that create or rebuild ck_integration_plugins_protocol "
        "must include every supported plugin protocol:\n"
        + "\n".join(missing_by_migration)
    )


def test_ai_executor_official_default_docs_match_model_gateway_template():
    ai_executor_defaults = STANDARD_PLUGIN_CONNECTION_DEFAULTS["ai_executor"]
    ai_executor_query = ai_executor_defaults["request_config"]["query"]

    assert ai_executor_defaults["endpoint_url"] == "model-gateway://default"
    assert ai_executor_query["executor_type"] == "model_gateway"
    assert ai_executor_query["runner_id"] == "ai_executor_runner_system_default"
    assert ai_executor_query["supported_executor_types"][0] == "model_gateway"

    repository_root = Path(__file__).resolve().parents[3]
    spec_source = (
        repository_root / "docs/02-specs/enterprise-ai-brain/spec.md"
    ).read_text()
    integration_plugin_line = next(
        line
        for line in spec_source.splitlines()
        if line.startswith("| integration_plugins |")
    )

    assert "`executor_type=model_gateway`" in integration_plugin_line
    assert "`model-gateway://default`" in integration_plugin_line
    assert "`runner_id=ai_executor_runner_system_default`" in integration_plugin_line
    assert "`executor_type=codex`" not in integration_plugin_line


def test_postgres_repository_patches_additive_schema_gaps_for_existing_volumes():
    source = Path("app/core/persistence.py").read_text()

    assert "_ensure_schema_compatibility" in source
    assert "ensure_schema_compatibility: bool = False" in source
    assert "ADD COLUMN IF NOT EXISTS assignee text" in source
    assert "idx_requirements_assignee" in source

    main_source = Path("app/main.py").read_text()
    assert "ensure_schema_compatibility=not _is_test_env()" in main_source


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
