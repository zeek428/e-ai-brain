import json
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.api.routers.assistant as assistant_router
import app.services.assistant_action_drafts as assistant_action_drafts_service
import app.services.assistant_chat as assistant_chat_service
import app.services.assistant_metrics as assistant_metrics_service
import app.services.assistant_role_quick_tasks as assistant_role_quick_tasks_service
from app.api.deps import api_error
from app.core.repositories.authorization import CompatibilityAuthorizationRepository
from app.core.security import hash_password
from app.core.users import MemoryUserRepository
from app.main import app
from app.services.assistant_metrics import (
    assistant_metric_details_response,
    assistant_metrics_response,
)
from app.services.assistant_references import (
    assistant_reference_candidates_response,
    resolve_assistant_references,
)
from app.services.assistant_request_context import assistant_task_source_store

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ai_assistant_draft_templates_list_official_market_entries():
    response = client.get("/api/assistant/draft-templates", headers=auth_headers())

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["total"] == 6
    templates_by_code = {item["code"]: item for item in payload["items"]}
    assert set(templates_by_code) == {
        "code_inspection",
        "email_digest",
        "knowledge_base_inspection",
        "online_log_anomaly_analysis",
        "release_risk_analysis",
        "weekly_feedback_insight",
    }
    assert templates_by_code["weekly_feedback_insight"]["draft_action"] == "create_scheduled_job"
    assert templates_by_code["weekly_feedback_insight"]["target_resource"] == "scheduled_job"
    expected_wizard_steps = [
        "数据来源",
        "AI处理",
        "结果动作",
        "调度策略",
        "确认执行",
    ]
    assert all(
        item["wizard_steps"] == expected_wizard_steps
        for item in templates_by_code.values()
    )
    assert "执行一次" in templates_by_code["weekly_feedback_insight"]["prompt"]
    assert templates_by_code["release_risk_analysis"]["roles"] == [
        "product_owner",
        "reviewer",
        "test_owner",
        "tester",
        "release_owner",
    ]
    assert templates_by_code["knowledge_base_inspection"]["source_module"] == "知识库"
    assert all(template["available"] is True for template in templates_by_code.values())


def test_ai_assistant_role_quick_tasks_are_backend_configured():
    response = client.get("/api/assistant/role-quick-tasks", headers=auth_headers())

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["total"] >= 1
    admin_group = next(item for item in payload["items"] if item["key"] == "admin")
    assert admin_group["label"] == "管理员快捷任务"
    assert admin_group["enabled"] is True
    assert admin_group["sort_order"] > 0
    scheduled_job_task = next(
        task for task in admin_group["tasks"] if task["key"] == "scheduled_jobs"
    )
    assert scheduled_job_task == {
        "analytics_key": "admin.scheduled_jobs",
        "enabled": True,
        "key": "scheduled_jobs",
        "label": "定时作业",
        "permissions": ["system.scheduled_jobs.manage"],
        "prompt": "请汇总定时作业配置、运行健康和需要补齐的依赖。",
        "sort_order": 30,
        "target_draft_type": "create_scheduled_job",
    }


def test_ai_assistant_runtime_status_returns_self_check_guidance():
    response = client.get("/api/assistant/runtime-status", headers=auth_headers())

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    checks_by_code = {item["code"]: item for item in payload["checks"]}
    checks_by_key = {item["key"]: item for item in payload["checks"]}
    assert {"postgres", "redis", "model_gateway", "embedding_gateway", "long_memory"}.issubset(
        checks_by_code
    )
    assert checks_by_key["long_memory"]["required"] is False
    assert checks_by_key["long_memory"]["severity"] == "info"
    assert checks_by_key["model_gateway"]["action_url"] == "/system/model-gateway"
    assert checks_by_key["redis"]["label"] == "Redis"
    assert checks_by_key["redis"]["detail"]
    assert checks_by_code["model_gateway"]["url"] == "/system/model-gateway"
    assert checks_by_code["redis"]["remediation"]
    assert isinstance(payload["ready"], bool)
    assert "operations" in payload


def test_ai_assistant_runtime_status_includes_operational_diagnostics():
    app.state.store.reset()
    app.state.store.assistant_chat_runs = {
        "assistant_chat_run_failed_runtime": {
            "conversation_id": "assistant_conversation_runtime",
            "created_at": "2026-06-20T09:00:00+00:00",
            "error_code": "ASSISTANT_CHAT_FAILED",
            "error_message": "模型网关 504",
            "finished_at": "2026-06-20T09:00:10+00:00",
            "id": "assistant_chat_run_failed_runtime",
            "status": "failed",
            "updated_at": "2026-06-20T09:00:10+00:00",
            "user_id": "user_admin",
        },
        "assistant_chat_run_other_runtime": {
            "created_at": "2026-06-20T09:01:00+00:00",
            "error_message": "其他用户失败",
            "id": "assistant_chat_run_other_runtime",
            "status": "failed",
            "updated_at": "2026-06-20T09:01:00+00:00",
            "user_id": "user_reviewer",
        },
    }
    app.state.store.model_gateway_logs = [
        {
            "created_at": "2026-06-20T09:03:00+00:00",
            "error": "upstream timeout",
            "id": "model_gateway_log_runtime_failed",
            "model": "gpt-test",
            "provider": "openai_compatible",
            "purpose": "assistant_chat",
            "status": "failed",
            "updated_at": "2026-06-20T09:03:01+00:00",
        }
    ]
    app.state.store.scheduled_job_runs = {
        "scheduled_job_run_runtime_failed": {
            "created_at": "2026-06-20T09:02:00+00:00",
            "error_code": "RUNNER_TIMEOUT",
            "error_message": "执行器未接单",
            "id": "scheduled_job_run_runtime_failed",
            "scheduled_job_id": "scheduled_job_runtime",
            "status": "failed",
            "updated_at": "2026-06-20T09:02:05+00:00",
        }
    }
    app.state.store.ai_executor_runners = {
        "runner_active": {
            "id": "runner_active",
            "status": "active",
            "updated_at": "2026-06-20T09:00:00+00:00",
        },
        "runner_offline": {
            "id": "runner_offline",
            "status": "offline",
            "updated_at": "2026-06-20T08:00:00+00:00",
        },
    }
    app.state.store.ai_executor_tasks = {
        "executor_task_queued": {
            "created_at": "2026-06-20T08:58:00+00:00",
            "id": "executor_task_queued",
            "status": "queued",
        },
        "executor_task_running": {
            "created_at": "2026-06-20T08:59:00+00:00",
            "id": "executor_task_running",
            "status": "running",
        },
        "executor_task_failed": {
            "created_at": "2026-06-20T08:57:00+00:00",
            "id": "executor_task_failed",
            "status": "failed",
        },
    }

    response = client.get("/api/assistant/runtime-status", headers=auth_headers())

    assert response.status_code == 200, response.text
    operations = response.json()["data"]["operations"]
    assert operations["executor_queue"] == {
        "active_runners": 1,
        "failed": 1,
        "offline_runners": 1,
        "oldest_pending_task_created_at": "2026-06-20T08:58:00+00:00",
        "oldest_pending_task_id": "executor_task_queued",
        "queued": 1,
        "running": 1,
        "succeeded": 0,
        "total_runners": 2,
        "visible": True,
    }
    assert operations["model_gateway_recent_failure"]["id"] == "model_gateway_log_runtime_failed"
    assert [
        item["kind"] for item in operations["recent_failures"]
    ] == [
        "model_gateway_log",
        "scheduled_job_run",
        "assistant_chat_run",
    ]
    assert operations["recent_failures"][0]["url"] == (
        "/system/model-gateway?log_id=model_gateway_log_runtime_failed"
    )


def test_ai_assistant_role_quick_tasks_can_be_loaded_from_repository_config():
    app.state.store.reset()

    class ConfiguredRoleQuickTaskRepository:
        def list_assistant_role_quick_tasks(self):
            return [
                {
                    "analytics_key": "ops.custom_health",
                    "enabled": True,
                    "group_enabled": True,
                    "group_key": "configured_admin",
                    "group_label": "运营配置快捷任务",
                    "group_roles": ["admin"],
                    "group_sort_order": 5,
                    "id": "assistant_role_quick_task_configured",
                    "permissions": [],
                    "prompt": "请检查运营配置里的快捷任务",
                    "sort_order": 7,
                    "target_draft_type": None,
                    "task_key": "custom_health",
                    "template_version": "2026.06",
                    "title": "运营配置项",
                }
            ]

    had_repository = hasattr(app.state.store, "repository")
    original_repository = getattr(app.state.store, "repository", None)
    app.state.store.repository = ConfiguredRoleQuickTaskRepository()
    try:
        response = client.get("/api/assistant/role-quick-tasks", headers=auth_headers())
    finally:
        if had_repository:
            app.state.store.repository = original_repository
        else:
            delattr(app.state.store, "repository")

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload == {
        "items": [
            {
                "enabled": True,
                "key": "configured_admin",
                "label": "运营配置快捷任务",
                "roles": ["admin"],
                "sort_order": 5,
                "tasks": [
                    {
                        "analytics_key": "ops.custom_health",
                        "enabled": True,
                        "key": "custom_health",
                        "label": "运营配置项",
                        "permissions": [],
                        "prompt": "请检查运营配置里的快捷任务",
                        "sort_order": 7,
                        "target_draft_type": None,
                        "template_version": "2026.06",
                    }
                ],
            }
        ],
        "total": 1,
    }


def test_ai_assistant_role_quick_task_configs_support_operations_rollout_and_audit():
    app.state.store.reset()
    headers = auth_headers()

    create_response = client.post(
        "/api/assistant/role-quick-task-configs",
        headers=headers,
        json={
            "analytics_key": "admin.enterprise_health",
            "enabled": True,
            "enterprise_id": "enterprise_a",
            "group_enabled": True,
            "group_key": "admin_ops",
            "group_label": "运营快捷任务",
            "group_roles": ["admin"],
            "group_sort_order": 3,
            "permissions": [],
            "prompt": "请检查企业 A 的助手运营任务",
            "rollout_json": {
                "enterprise_ids": ["enterprise_a"],
                "percentage": 100,
                "template_versions": ["2026.06"],
            },
            "sort_order": 9,
            "target_draft_type": "create_analysis_draft",
            "task_key": "enterprise_health",
            "template_version": "2026.06",
            "title": "企业运营巡检",
        },
    )

    assert create_response.status_code == 200, create_response.text
    config = create_response.json()["data"]
    config_id = config["id"]
    assert config["enterprise_id"] == "enterprise_a"
    assert config["rollout_json"]["template_versions"] == ["2026.06"]

    patch_response = client.patch(
        f"/api/assistant/role-quick-task-configs/{config_id}",
        headers=headers,
        json={"title": "企业运营巡检 V2", "sort_order": 5},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["data"]["title"] == "企业运营巡检 V2"
    assert patch_response.json()["data"]["sort_order"] == 5

    disable_response = client.post(
        f"/api/assistant/role-quick-task-configs/{config_id}/status",
        headers=headers,
        json={"enabled": False},
    )
    assert disable_response.status_code == 200, disable_response.text
    assert disable_response.json()["data"]["enabled"] is False

    rollout_response = client.put(
        f"/api/assistant/role-quick-task-configs/{config_id}/rollout",
        headers=headers,
        json={
            "enterprise_id": "enterprise_b",
            "rollout_json": {
                "enterprise_ids": ["enterprise_b"],
                "percentage": 100,
                "template_versions": ["2026.07"],
            },
            "template_version": "2026.07",
        },
    )
    assert rollout_response.status_code == 200, rollout_response.text
    assert rollout_response.json()["data"]["enterprise_id"] == "enterprise_b"
    assert rollout_response.json()["data"]["template_version"] == "2026.07"

    enable_response = client.post(
        f"/api/assistant/role-quick-task-configs/{config_id}/status",
        headers=headers,
        json={"enabled": True},
    )
    assert enable_response.status_code == 200, enable_response.text

    configs_response = client.get("/api/assistant/role-quick-task-configs", headers=headers)
    assert configs_response.status_code == 200, configs_response.text
    assert configs_response.json()["data"]["total"] == 1

    visible_payload = assistant_role_quick_tasks_service.list_assistant_role_quick_tasks_response(
        current_store=app.state.store,
        user={
            "assistant_template_version": "2026.07",
            "enterprise_id": "enterprise_b",
            "id": "user_enterprise_b",
            "permissions": [],
            "roles": ["admin"],
        },
    )
    assert visible_payload["items"][0]["key"] == "admin_ops"
    assert visible_payload["items"][0]["tasks"][0]["label"] == "企业运营巡检 V2"

    filtered_payload = assistant_role_quick_tasks_service.list_assistant_role_quick_tasks_response(
        current_store=app.state.store,
        user={
            "assistant_template_version": "2026.06",
            "enterprise_id": "enterprise_a",
            "id": "user_enterprise_a",
            "permissions": [],
            "roles": ["admin"],
        },
    )
    assert filtered_payload == {"items": [], "total": 0}

    audit_types = [event["event_type"] for event in app.state.store.audit_events]
    assert "assistant_role_quick_task.created" in audit_types
    assert "assistant_role_quick_task.updated" in audit_types
    assert "assistant_role_quick_task.status_changed" in audit_types
    assert "assistant_role_quick_task.rollout_changed" in audit_types


def test_ai_assistant_role_quick_task_configs_support_remote_list_query():
    app.state.store.reset()
    headers = auth_headers()
    for index, payload in enumerate(
        [
            {
                "enabled": True,
                "group_roles": ["admin"],
                "permissions": ["system.scheduled_jobs.manage"],
                "task_key": "enterprise_health",
                "title": "企业运营巡检",
            },
            {
                "enabled": False,
                "group_roles": ["release_owner"],
                "permissions": ["release.manage"],
                "task_key": "release_risk",
                "title": "发布风险确认",
            },
        ],
        start=1,
    ):
        response = client.post(
            "/api/assistant/role-quick-task-configs",
            headers=headers,
            json={
                "analytics_key": f"remote.quick_task.{index}",
                "enterprise_id": "enterprise_a",
                "group_enabled": True,
                "group_key": "remote_admin",
                "group_label": "远程快捷任务",
                "group_sort_order": 3,
                "prompt": f"请处理{payload['title']}。",
                "rollout_json": {},
                "sort_order": index * 10,
                "target_draft_type": "create_analysis_draft",
                "template_version": "2026.07",
                **payload,
            },
        )
        assert response.status_code == 200, response.text

    response = client.get(
        (
            "/api/assistant/role-quick-task-configs"
            "?keyword=发布&status=disabled&role=release_owner&page=1&page_size=1"
            "&sort_by=sort_order&sort_order=desc"
        ),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total"] == 1
    assert data["items"][0]["title"] == "发布风险确认"
    assert data["query"]["name"] == "assistant_role_quick_task_configs"
    assert data["query"]["filters"] == {
        "keyword": "发布",
        "role": "release_owner",
        "status": "disabled",
    }
    assert data["performance"]["result_count"] == 1


def test_ai_assistant_role_quick_task_rollout_percentage_filters_candidates():
    app.state.store.reset()
    app.state.store.assistant_role_quick_tasks["assistant_role_quick_task_off"] = {
        "enabled": True,
        "group_enabled": True,
        "group_key": "admin_gray",
        "group_label": "灰度快捷任务",
        "group_roles": ["admin"],
        "group_sort_order": 1,
        "id": "assistant_role_quick_task_off",
        "permissions": [],
        "prompt": "灰度关闭时不可见",
        "rollout_json": {"percentage": 0},
        "sort_order": 1,
        "task_key": "gray_off",
        "title": "灰度关闭",
    }

    payload = assistant_role_quick_tasks_service.list_assistant_role_quick_tasks_response(
        current_store=app.state.store,
        user={"id": "user_admin", "permissions": [], "roles": ["admin"]},
    )

    assert payload == {"items": [], "total": 0}


def test_ai_assistant_allows_testing_delivery_roles_to_use_workbench_apis(monkeypatch):
    original_user_repository = app.state.user_repository
    app.state.store.reset()
    app.state.user_repository = MemoryUserRepository(
        {
            "test-owner@example.com": {
                "display_name": "测试负责人",
                "id": "user_test_owner",
                "password_hash": hash_password("test123"),
                "roles": ["test_owner"],
                "status": "active",
                "username": "test-owner@example.com",
            },
            "tester@example.com": {
                "display_name": "测试人员",
                "id": "user_tester",
                "password_hash": hash_password("test123"),
                "roles": ["tester"],
                "status": "active",
                "username": "tester@example.com",
            },
            "release-owner@example.com": {
                "display_name": "发布负责人",
                "id": "user_release_owner",
                "password_hash": hash_password("test123"),
                "roles": ["release_owner"],
                "status": "active",
                "username": "release-owner@example.com",
            },
        },
    )
    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("model gateway should not be called")

    monkeypatch.setattr(assistant_router, "urlopen", fail_urlopen)
    try:
        for username in (
            "test-owner@example.com",
            "tester@example.com",
            "release-owner@example.com",
        ):
            headers = auth_headers(username, "test123")

            conversations_response = client.get("/api/assistant/conversations", headers=headers)
            assert conversations_response.status_code == 200, conversations_response.text

            templates_response = client.get("/api/assistant/draft-templates", headers=headers)
            assert templates_response.status_code == 200, templates_response.text
            template_codes = {
                item["code"] for item in templates_response.json()["data"]["items"]
            }
            assert "release_risk_analysis" in template_codes

            quick_tasks_response = client.get(
                "/api/assistant/role-quick-tasks",
                headers=headers,
            )
            assert quick_tasks_response.status_code == 200, quick_tasks_response.text
            quick_task_keys = {
                task["key"]
                for group in quick_tasks_response.json()["data"]["items"]
                for task in group["tasks"]
            }
            assert "release_risk" in quick_task_keys

            chat_response = client.post(
                "/api/assistant/chat",
                headers=headers,
                json={"message": "我要新增任务"},
            )
            assert chat_response.status_code == 200, chat_response.text
            assert chat_response.json()["data"]["message"]["tool_results"][0]["tool"] == (
                "assistant.task_creation_guide"
            )
    finally:
        app.state.user_repository = original_user_repository


def test_ai_assistant_reference_candidates_filter_operational_items_by_product_scope():
    app.state.store.reset()
    app.state.store.products = {
        "product_allowed": {
            "code": "allowed",
            "id": "product_allowed",
            "name": "允许产品",
            "status": "active",
        },
        "product_denied": {
            "code": "denied",
            "id": "product_denied",
            "name": "无权产品",
            "status": "active",
        },
    }
    app.state.store.scheduled_jobs = {
        "scheduled_job_allowed": {
            "id": "scheduled_job_allowed",
            "job_type": "dashboard_snapshot_refresh",
            "name": "允许产品定时作业",
            "product_id": "product_allowed",
            "status": "active",
        },
        "scheduled_job_denied": {
            "id": "scheduled_job_denied",
            "job_type": "dashboard_snapshot_refresh",
            "name": "无权产品定时作业",
            "product_id": "product_denied",
            "status": "active",
        },
    }
    app.state.store.scheduled_job_runs = {
        "scheduled_job_run_allowed": {
            "id": "scheduled_job_run_allowed",
            "scheduled_job_id": "scheduled_job_allowed",
            "status": "failed",
        },
        "scheduled_job_run_denied": {
            "id": "scheduled_job_run_denied",
            "scheduled_job_id": "scheduled_job_denied",
            "status": "failed",
        },
    }
    scoped_user = {
        "id": "user_ops",
        "permissions": ["system.scheduled_jobs.run"],
        "roles": ["rd_owner"],
        "scope_summary": [
            {
                "access_level": "read",
                "scope_id": "product_allowed",
                "scope_type": "product",
            }
        ],
    }

    jobs = assistant_reference_candidates_response(
        app.state.store,
        limit=10,
        message="定时作业",
        product_id=None,
        reference_type="scheduled_job",
        user=scoped_user,
    )["items"]
    runs = assistant_reference_candidates_response(
        app.state.store,
        limit=10,
        message="运行记录",
        product_id=None,
        reference_type="scheduled_job_run",
        user=scoped_user,
    )["items"]

    assert [item["id"] for item in jobs] == ["scheduled_job_allowed"]
    assert [item["id"] for item in runs] == ["scheduled_job_run_allowed"]

    denied_product_jobs = assistant_reference_candidates_response(
        app.state.store,
        limit=10,
        message="定时作业",
        product_id="product_denied",
        reference_type="scheduled_job",
        user=scoped_user,
    )["items"]
    denied_product_runs = assistant_reference_candidates_response(
        app.state.store,
        limit=10,
        message="运行记录",
        product_id="product_denied",
        reference_type="scheduled_job_run",
        user=scoped_user,
    )["items"]

    assert denied_product_jobs == []
    assert denied_product_runs == []


def test_ai_assistant_reference_candidates_include_action_candidates_for_create_commands():
    app.state.store.reset()

    payload = assistant_reference_candidates_response(
        app.state.store,
        limit=20,
        message="新建",
        product_id=None,
        reference_type=None,
        user={
            "id": "user_admin",
            "permissions": [
                "system.ai_capabilities.manage",
                "system.plugins.manage",
                "system.scheduled_jobs.manage",
            ],
            "roles": ["admin"],
        },
    )

    actions = [item for item in payload["items"] if item["type"] == "assistant_action"]
    assert [item["id"] for item in actions] == [
        "create_requirement",
        "create_bug",
        "create_plugin_connection",
        "create_plugin_action",
        "create_scheduled_job",
        "create_knowledge_document",
        "create_ai_capability",
    ]
    assert actions[0]["source_module"] == "动作"
    assert actions[0]["permission_label"] == "可执行"
    assert actions[0]["action"] == "create_requirement"
    assert actions[0]["prompt"].startswith("我要新建需求")
    assert actions[0]["url"] == "/delivery/requirements"

    diagnostic_payload = assistant_reference_candidates_response(
        app.state.store,
        limit=5,
        message="诊断",
        product_id=None,
        reference_type="assistant_action",
        user={"id": "user_admin", "permissions": ["system.admin"], "roles": ["admin"]},
    )
    diagnostic_actions = [item["action"] for item in diagnostic_payload["items"]]
    assert "diagnose_scheduled_job_run" in diagnostic_actions

    metrics_payload = assistant_reference_candidates_response(
        app.state.store,
        limit=5,
        message="指标",
        product_id=None,
        reference_type="assistant_action",
        user={"id": "user_admin", "permissions": ["system.admin"], "roles": ["admin"]},
    )
    metrics_actions = [item["action"] for item in metrics_payload["items"]]
    assert "explain_assistant_metrics" in metrics_actions


def test_ai_assistant_action_reference_configs_override_default_candidates():
    app.state.store.reset()
    disabled_requirement_config_id = "assistant_action_reference_config_requirement_off"
    app.state.store.assistant_action_reference_configs[disabled_requirement_config_id] = {
        "action_key": "create_requirement",
        "aliases": ["新建", "需求"],
        "enabled": False,
        "id": "assistant_action_reference_config_requirement_off",
        "metadata_json": {},
        "permissions": [],
        "prompt": "禁用默认新建需求入口",
        "roles": [],
        "rollout_json": {},
        "sort_order": 10,
        "summary": "禁用默认新建需求入口",
        "title": "新建需求",
        "url": "/delivery/requirements",
    }
    custom_config_id = "assistant_action_reference_config_custom"
    app.state.store.assistant_action_reference_configs[custom_config_id] = {
        "action_key": "create_security_review",
        "aliases": ["新建", "安全评审"],
        "enabled": True,
        "enterprise_id": "enterprise_a",
        "id": "assistant_action_reference_config_custom",
        "metadata_json": {"source": "ops"},
        "permissions": [],
        "prompt": "请生成安全评审草案。",
        "roles": ["admin"],
        "rollout_json": {
            "enterprise_ids": ["enterprise_a"],
            "percentage": 100,
            "template_versions": ["2026.06"],
        },
        "sort_order": 5,
        "summary": "运营配置的安全评审动作。",
        "template_version": "2026.06",
        "title": "新建安全评审",
        "url": "/security/reviews",
    }

    visible_payload = assistant_reference_candidates_response(
        app.state.store,
        limit=20,
        message="新建",
        product_id=None,
        reference_type="assistant_action",
        user={
            "assistant_template_version": "2026.06",
            "enterprise_id": "enterprise_a",
            "id": "user_admin",
            "permissions": ["system.admin"],
            "roles": ["admin"],
        },
    )
    visible_actions = [item["action"] for item in visible_payload["items"]]

    assert visible_actions[0] == "create_security_review"
    assert "create_requirement" not in visible_actions
    assert visible_payload["items"][0]["id"] == "create_security_review"
    assert visible_payload["items"][0]["config_id"] == "assistant_action_reference_config_custom"
    assert visible_payload["items"][0]["prompt"] == "请生成安全评审草案。"

    filtered_payload = assistant_reference_candidates_response(
        app.state.store,
        limit=20,
        message="安全评审",
        product_id=None,
        reference_type="assistant_action",
        user={
            "assistant_template_version": "2026.07",
            "enterprise_id": "enterprise_b",
            "id": "user_admin_b",
            "permissions": ["system.admin"],
            "roles": ["admin"],
        },
    )

    assert filtered_payload["items"] == []


def test_ai_assistant_action_reference_config_apis_support_operations_rollout_and_audit():
    app.state.store.reset()
    headers = auth_headers()

    create_response = client.post(
        "/api/assistant/action-reference-configs",
        headers=headers,
        json={
            "action_key": "create_incident_review",
            "aliases": ["新建", "事故复盘"],
            "enabled": True,
            "enterprise_id": "enterprise_a",
            "permissions": [],
            "prompt": "请生成事故复盘草案。",
            "roles": ["admin"],
            "rollout_json": {
                "enterprise_ids": ["enterprise_a"],
                "percentage": 100,
                "template_versions": ["2026.06"],
            },
            "sort_order": 12,
            "summary": "运营配置的事故复盘动作。",
            "template_version": "2026.06",
            "title": "新建事故复盘",
            "url": "/ops/incidents",
        },
    )

    assert create_response.status_code == 200, create_response.text
    config = create_response.json()["data"]
    config_id = config["id"]
    assert config["action_key"] == "create_incident_review"
    assert config["rollout_json"]["template_versions"] == ["2026.06"]

    patch_response = client.patch(
        f"/api/assistant/action-reference-configs/{config_id}",
        headers=headers,
        json={"title": "新建事故复盘 V2", "sort_order": 8},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["data"]["title"] == "新建事故复盘 V2"
    assert patch_response.json()["data"]["sort_order"] == 8

    disable_response = client.post(
        f"/api/assistant/action-reference-configs/{config_id}/status",
        headers=headers,
        json={"enabled": False},
    )
    assert disable_response.status_code == 200, disable_response.text
    assert disable_response.json()["data"]["enabled"] is False

    rollout_response = client.put(
        f"/api/assistant/action-reference-configs/{config_id}/rollout",
        headers=headers,
        json={
            "enterprise_id": "enterprise_b",
            "rollout_json": {
                "enterprise_ids": ["enterprise_b"],
                "percentage": 100,
                "template_versions": ["2026.07"],
            },
            "template_version": "2026.07",
        },
    )
    assert rollout_response.status_code == 200, rollout_response.text
    assert rollout_response.json()["data"]["enterprise_id"] == "enterprise_b"
    assert rollout_response.json()["data"]["template_version"] == "2026.07"

    configs_response = client.get("/api/assistant/action-reference-configs", headers=headers)
    assert configs_response.status_code == 200, configs_response.text
    assert configs_response.json()["data"]["total"] == 1

    audit_types = [event["event_type"] for event in app.state.store.audit_events]
    assert "assistant_action_reference_config.created" in audit_types
    assert "assistant_action_reference_config.updated" in audit_types
    assert "assistant_action_reference_config.status_changed" in audit_types
    assert "assistant_action_reference_config.rollout_changed" in audit_types


def test_ai_assistant_action_reference_config_apis_allow_permission_granted_non_admin():
    app.state.store.reset()
    original_authorization_repository = app.state.authorization_repository
    original_user_repository = app.state.user_repository
    authorization_repository = CompatibilityAuthorizationRepository()
    authorization_repository.set_role_permissions(
        "reviewer",
        ["assistant.action_references.manage"],
        actor_id="user_admin",
        trace_id="test-trace",
    )
    authorization_repository.set_role_menus(
        "reviewer",
        ["system.assistant_action_references"],
        actor_id="user_admin",
        trace_id="test-trace",
    )
    app.state.authorization_repository = authorization_repository
    app.state.user_repository = MemoryUserRepository.seeded()
    try:
        headers = auth_headers("reviewer@example.com", "reviewer123")
        response = client.get("/api/assistant/action-reference-configs", headers=headers)
    finally:
        app.state.authorization_repository = original_authorization_repository
        app.state.user_repository = original_user_repository

    assert response.status_code == 200, response.text
    assert response.json()["data"]["items"] == []


def test_ai_assistant_action_reference_configs_support_remote_list_query():
    app.state.store.reset()
    headers = auth_headers()
    for index, title in enumerate(["新建需求", "新建 Bug"], start=1):
        response = client.post(
            "/api/assistant/action-reference-configs",
            headers=headers,
            json={
                "action_key": f"remote_action_{index}",
                "aliases": ["远程列表", title],
                "enabled": index == 1,
                "enterprise_id": "enterprise_a",
                "permissions": ["assistant.action_references.manage"],
                "prompt": f"请生成{title}草案。",
                "roles": ["admin"],
                "rollout_json": {},
                "sort_order": index * 10,
                "summary": f"{title}远程列表验证。",
                "template_version": "2026.07",
                "title": title,
                "url": "/assistant",
            },
        )
        assert response.status_code == 200, response.text

    response = client.get(
        (
            "/api/assistant/action-reference-configs"
            "?keyword=Bug&status=disabled&role=admin&page=1&page_size=1"
            "&sort_by=sort_order&sort_order=desc"
        ),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total"] == 1
    assert data["items"][0]["title"] == "新建 Bug"
    assert data["query"]["name"] == "assistant_action_reference_configs"
    assert data["query"]["filters"] == {
        "keyword": "Bug",
        "role": "admin",
        "status": "disabled",
    }
    assert data["performance"]["result_count"] == 1


def test_ai_assistant_chat_returns_registered_intent_metadata(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("task guide should be handled by registered deterministic intent")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        headers=headers,
        json={"message": "我要新增任务"},
    )

    assert response.status_code == 200, response.text
    message = response.json()["data"]["message"]
    assert message["intent"] == {
        "action": "guide_task_creation",
        "confidence": 0.95,
        "conflict_policy": "first_match",
        "intent_code": "task_creation_guide",
        "priority": 100,
        "required_refs": [],
        "summary": "将执行：任务类型向导",
    }
    assert message["tool_results"][0]["intent_code"] == "task_creation_guide"
    assert message["tool_results"][0]["intent_confidence"] == 0.95


def test_ai_assistant_deterministic_intent_registry_dispatches_registered_handler(monkeypatch):
    app.state.store.reset()
    handled_messages = []

    def synthetic_handler(current_store, *, intent, payload, user):
        assert current_store is app.state.store
        assert user["id"] == "user_admin"
        handled_messages.append(payload.message)
        return {
            "answer": "synthetic intent handled",
            "latency_ms": 0,
            "model": "assistant-deterministic",
            "references": [],
            "selected_references": [],
            "suggestions": ["synthetic next"],
            "tool_results": [
                {
                    "items": [],
                    "summary": {"status": "handled"},
                    "tool": "assistant.synthetic",
                }
            ],
        }

    monkeypatch.setattr(
        assistant_chat_service,
        "_deterministic_intent_registry",
        lambda: [
            {
                "confidence": 0.88,
                "conflict_policy": "first_match",
                "detector": lambda message: "synthetic" in message,
                "handler": synthetic_handler,
                "intent_code": "synthetic_intent",
                "priority": 1,
                "required_refs": [],
                "summary": "将执行：synthetic",
            }
        ],
    )

    output = assistant_chat_service._deterministic_assistant_output(
        app.state.store,
        payload=assistant_chat_service.AssistantChatRequest(message="synthetic please"),
        user={"id": "user_admin", "permissions": ["system.admin"], "roles": ["admin"]},
    )

    assert handled_messages == ["synthetic please"]
    assert output["answer"] == "synthetic intent handled"
    assert output["intent"] == {
        "confidence": 0.88,
        "conflict_policy": "first_match",
        "intent_code": "synthetic_intent",
        "priority": 1,
        "required_refs": [],
        "summary": "将执行：synthetic",
    }
    assert output["tool_results"][0]["intent_code"] == "synthetic_intent"


def test_ai_assistant_deterministic_registry_handles_run_diagnostic():
    app.state.store.reset()
    app.state.store.scheduled_jobs["scheduled_job_failed"] = {
        "created_at": "2026-06-05T08:00:00+00:00",
        "enabled": True,
        "id": "scheduled_job_failed",
        "job_type": "user_feedback_insight_extract",
        "name": "每周反馈洞察",
        "status": "active",
        "updated_at": "2026-06-05T08:00:00+00:00",
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_failed"] = {
        "completed_at": "2026-06-05T08:05:00+00:00",
        "error_message": "结果动作写入失败",
        "id": "scheduled_job_run_failed",
        "scheduled_job_id": "scheduled_job_failed",
        "started_at": "2026-06-05T08:00:00+00:00",
        "status": "failed",
    }

    output = assistant_chat_service._deterministic_assistant_output(
        app.state.store,
        payload=assistant_chat_service.AssistantChatRequest(message="为什么定时作业运行失败？"),
        user={"id": "user_admin", "permissions": ["system.admin"], "roles": ["admin"]},
    )

    assert output is not None
    assert output["intent"]["action"] == "diagnose_scheduled_job_run"
    assert output["intent"]["tool"] == "assistant.scheduled_job_diagnostic"
    assert output["tool_results"][0]["tool"] == "assistant.scheduled_job_diagnostic"
    assert output["tool_results"][0]["items"][0]["id"] == "scheduled_job_run_failed"
    assert "三段整理诊断" in output["answer"]


def test_ai_assistant_deterministic_registry_handles_metrics_explanation():
    app.state.store.reset()

    output = assistant_chat_service._deterministic_assistant_output(
        app.state.store,
        payload=assistant_chat_service.AssistantChatRequest(message="解释一下 AI 助手效果指标"),
        user={"id": "user_admin", "permissions": ["system.admin"], "roles": ["admin"]},
    )

    assert output is not None
    assert output["intent"]["action"] == "explain_assistant_metrics"
    assert output["intent"]["tool"] == "assistant.metrics_summary"
    assert output["tool_results"][0]["tool"] == "assistant.metrics_summary"
    assert "草案确认率" in output["answer"]


def test_ai_assistant_intent_registry_uses_conflict_policy_before_priority(monkeypatch):
    monkeypatch.setattr(
        assistant_chat_service,
        "_deterministic_intent_registry",
        lambda: [
            {
                "confidence": 0.1,
                "conflict_policy": "fallback",
                "detector": lambda _message: True,
                "handler": lambda *_args, **_kwargs: None,
                "intent_code": "fallback_intent",
                "priority": 1000,
                "required_refs": [],
                "summary": "fallback",
            },
            {
                "confidence": 0.9,
                "conflict_policy": "first_match",
                "detector": lambda _message: True,
                "handler": lambda *_args, **_kwargs: None,
                "intent_code": "specific_intent",
                "priority": 1,
                "required_refs": [],
                "summary": "specific",
            },
        ],
    )

    intent = assistant_chat_service._match_deterministic_intent("任意消息")

    assert intent is not None
    assert intent["intent_code"] == "specific_intent"


def test_ai_assistant_test_owner_can_run_explicit_mention_job_once(monkeypatch):
    original_user_repository = app.state.user_repository
    app.state.store.reset()
    app.state.user_repository = MemoryUserRepository(
        {
            "test-owner@example.com": {
                "display_name": "测试负责人",
                "id": "user_test_owner",
                "password_hash": hash_password("test123"),
                "roles": ["test_owner"],
                "status": "active",
                "username": "test-owner@example.com",
            },
        },
    )
    app.state.store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)
    try:
        response = client.post(
            "/api/assistant/chat",
            json={
                "message": "@提取每周用户反馈有价值信息 执行一次",
            },
            headers=auth_headers("test-owner@example.com", "test123"),
        )
    finally:
        app.state.user_repository = original_user_repository

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "已执行「提取每周用户反馈有价值信息」一次" in message["content"]
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_insight"
    assert message["tool_results"][0]["summary"]["status"] == "succeeded"


def seed_assistant_knowledge_reference_documents() -> None:
    now = "2026-06-14T08:00:00+00:00"
    app.state.store.knowledge_documents["knowledge_payment_runbook"] = {
        "brain_app_id": "rd_brain",
        "content": "支付页提交无响应时，先检查网关超时、回调状态和前端埋点。",
        "created_at": now,
        "created_by": "knowledge_owner@example.com",
        "doc_type": "manual",
        "id": "knowledge_payment_runbook",
        "index_status": "indexed",
        "permission_roles": ["reviewer"],
        "permission_scope": {},
        "product_id": None,
        "source_type": "manual",
        "tags": ["payment"],
        "title": "支付页超时排障手册",
        "updated_at": now,
        "vector_index_error": None,
        "version_id": None,
    }
    app.state.store.knowledge_documents["knowledge_private_runbook"] = {
        "brain_app_id": "rd_brain",
        "content": "非授权知识：内部成本和供应商账号。",
        "created_at": now,
        "created_by": "knowledge_owner@example.com",
        "doc_type": "manual",
        "id": "knowledge_private_runbook",
        "index_status": "indexed",
        "permission_roles": ["knowledge_owner"],
        "permission_scope": {},
        "product_id": None,
        "source_type": "manual",
        "tags": ["private"],
        "title": "非授权支付内部手册",
        "updated_at": now,
        "vector_index_error": None,
        "version_id": None,
    }
    app.state.store.knowledge_chunks["knowledge_payment_runbook_chunk_001"] = {
        "chunk_index": 0,
        "content": "支付页提交无响应：检查网关 30 秒超时、回调幂等键和前端 loading 状态。",
        "document_id": "knowledge_payment_runbook",
        "embedding": [0.1, 0.2, 0.3],
        "id": "knowledge_payment_runbook_chunk_001",
        "metadata": {},
        "permission_roles": ["reviewer"],
        "permission_scope": {"roles": ["reviewer"]},
    }
    app.state.store.knowledge_chunks["knowledge_private_runbook_chunk_001"] = {
        "chunk_index": 0,
        "content": "非授权知识：供应商账号和内部成本。",
        "document_id": "knowledge_private_runbook",
        "embedding": [0.4, 0.5, 0.6],
        "id": "knowledge_private_runbook_chunk_001",
        "metadata": {},
        "permission_roles": ["knowledge_owner"],
        "permission_scope": {"roles": ["knowledge_owner"]},
    }


def seed_assistant_knowledge_space_references() -> None:
    now = "2026-06-14T08:30:00+00:00"
    app.state.store.knowledge_spaces["knowledge_space_support"] = {
        "code": "support",
        "created_at": now,
        "created_by": "user_admin",
        "description": "支付与订单支持知识空间。",
        "id": "knowledge_space_support",
        "name": "支付支持知识空间",
        "owner_user_id": "user_admin",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.knowledge_space_members[
        "knowledge_space_support:user_reviewer:reader"
    ] = {
        "created_at": now,
        "granted_by": "user_admin",
        "knowledge_space_id": "knowledge_space_support",
        "space_role": "reader",
        "status": "active",
        "updated_at": now,
        "user_id": "user_reviewer",
    }
    app.state.store.knowledge_folders["knowledge_folder_payment_support"] = {
        "created_at": now,
        "created_by": "user_admin",
        "id": "knowledge_folder_payment_support",
        "knowledge_space_id": "knowledge_space_support",
        "name": "支付排障目录",
        "parent_folder_id": None,
        "path": "支付排障目录",
        "sort_order": 1,
        "status": "active",
        "updated_at": now,
    }
    app.state.store.knowledge_documents["knowledge_space_payment_runbook"] = {
        "brain_app_id": "rd_brain",
        "content": "支付空间文档：检查支付网关、订单回调和风控状态。",
        "created_at": now,
        "created_by": "knowledge_owner@example.com",
        "doc_type": "manual",
        "folder_id": "knowledge_folder_payment_support",
        "id": "knowledge_space_payment_runbook",
        "index_status": "indexed",
        "knowledge_space_id": "knowledge_space_support",
        "permission_roles": [],
        "permission_scope": {"knowledge_space_id": "knowledge_space_support"},
        "product_id": None,
        "source_type": "manual",
        "tags": ["payment"],
        "title": "空间支付排障手册",
        "updated_at": now,
        "vector_index_error": None,
        "version_id": None,
    }
    app.state.store.knowledge_chunks["knowledge_space_payment_runbook_chunk_001"] = {
        "chunk_index": 0,
        "content": "空间支付排障：检查支付网关、订单回调和风控状态。",
        "document_id": "knowledge_space_payment_runbook",
        "embedding": [0.2, 0.3, 0.4],
        "id": "knowledge_space_payment_runbook_chunk_001",
        "metadata": {
            "folder_id": "knowledge_folder_payment_support",
            "knowledge_space_id": "knowledge_space_support",
        },
        "permission_roles": [],
        "permission_scope": {"knowledge_space_id": "knowledge_space_support"},
    }
    app.state.store.knowledge_spaces["knowledge_space_private"] = {
        "code": "private",
        "created_at": now,
        "created_by": "user_admin",
        "description": "非授权私有知识空间。",
        "id": "knowledge_space_private",
        "name": "私有知识空间",
        "owner_user_id": "user_admin",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.knowledge_folders["knowledge_folder_private"] = {
        "created_at": now,
        "created_by": "user_admin",
        "id": "knowledge_folder_private",
        "knowledge_space_id": "knowledge_space_private",
        "name": "私有目录",
        "parent_folder_id": None,
        "path": "私有目录",
        "sort_order": 1,
        "status": "active",
        "updated_at": now,
    }


def seed_assistant_operational_references() -> None:
    now = "2026-06-14T09:30:00+00:00"
    app.state.store.integration_plugins["plugin_http"] = {
        "code": "generic_http",
        "created_at": now,
        "description": "通用 HTTP 插件。",
        "id": "plugin_http",
        "name": "通用 HTTP 插件",
        "plugin_type": "http",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.plugin_connections["plugin_connection_maxcompute"] = {
        "auth_config": {},
        "auth_type": "none",
        "created_at": now,
        "created_by": "user_admin",
        "endpoint_url": "https://feedback.example.com",
        "environment": "prod",
        "id": "plugin_connection_maxcompute",
        "max_retries": 0,
        "name": "MaxCompute 用户反馈连接",
        "plugin_id": "plugin_http",
        "request_config": {},
        "status": "active",
        "timeout_seconds": 30,
        "updated_at": now,
    }
    app.state.store.ai_agents["ai_agent_feedback_ops"] = {
        "brain_app_id": "rd_brain",
        "code": "feedback_ops",
        "created_at": now,
        "description": "负责用户反馈洞察和运行诊断。",
        "id": "ai_agent_feedback_ops",
        "name": "反馈洞察 AI 角色",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.ai_skills["ai_skill_feedback_summary"] = {
        "brain_app_id": "rd_brain",
        "code": "feedback_summary",
        "created_at": now,
        "description": "汇总反馈并生成洞察。",
        "id": "ai_skill_feedback_summary",
        "name": "反馈洞察 Skill",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.plugin_actions["plugin_action_feedback_write"] = {
        "action_type": "http_request",
        "code": "feedback_write",
        "created_at": now,
        "id": "plugin_action_feedback_write",
        "name": "反馈洞察写入动作",
        "plugin_id": "plugin_http",
        "request_config": {
            "body": {"token": "should-not-be-copied"},
            "headers": {"Authorization": "Bearer should-not-be-copied"},
        },
        "status": "active",
        "updated_at": now,
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_weekly"] = {
        "agent_id": "ai_agent_feedback_ops",
        "created_at": now,
        "enabled": True,
        "execution_mode": "ai_assisted",
        "id": "scheduled_job_feedback_weekly",
        "job_type": "user_feedback_insight",
        "name": "每周反馈洞察定时作业",
        "plugin_action_id": "plugin_action_feedback_write",
        "product_id": None,
        "schedule_type": "cron",
        "skill_ids": ["ai_skill_feedback_summary"],
        "source_system": "ai-assistant-test",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_feedback_failed"] = {
        "completed_at": "2026-06-14T09:35:00+00:00",
        "duration_ms": 4200,
        "error_message": "结果写入动作返回 500",
        "id": "scheduled_job_run_feedback_failed",
        "result_summary": {
            "execution_nodes": {
                "data_connection": {
                    "status": "succeeded",
                    "summary": "从 MaxCompute 读取 128 条反馈。",
                },
                "ai_processing": {
                    "model_gateway_log_id": "model_gateway_log_feedback_failed",
                    "status": "succeeded",
                    "summary": "生成 6 条洞察。",
                },
                "result_action": {
                    "error_code": "RESULT_WRITE_FAILED",
                    "error_message": "HTTP 500: downstream write failed",
                    "plugin_invocation_log_id": "plugin_invocation_log_feedback_failed",
                    "status": "failed",
                    "summary": "写入反馈洞察表失败。",
                    "write_target": "user_feedback_insights",
                    "write_target_label": "用户洞察表",
                },
            },
            "records_imported": 128,
        },
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "started_at": "2026-06-14T09:31:00+00:00",
        "status": "failed",
        "trigger_type": "manual",
        "updated_at": "2026-06-14T09:35:00+00:00",
    }
    app.state.store.plugin_invocation_logs["plugin_invocation_log_feedback_failed"] = {
        "action_id": "plugin_action_feedback_write",
        "connection_id": "plugin_connection_maxcompute",
        "created_at": "2026-06-14T09:34:58+00:00",
        "duration_ms": 1800,
        "error_message": "HTTP 500: downstream write failed",
        "id": "plugin_invocation_log_feedback_failed",
        "plugin_id": "plugin_http",
        "request_summary": {"method": "POST", "path": "/feedback/insights"},
        "response_summary": {"status_code": 500},
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "scheduled_job_run_id": "scheduled_job_run_feedback_failed",
        "status": "failed",
        "trigger_type": "scheduled_job",
    }
    app.state.store.model_gateway_logs.append(
        {
            "created_at": "2026-06-14T09:33:00+00:00",
            "id": "model_gateway_log_feedback_failed",
            "latency_ms": 900,
            "model": "test-chat-model",
            "provider": "test",
            "purpose": "scheduled_job.ai_processing",
            "status": "succeeded",
            "tokens": {"completion": 80, "prompt": 200, "total": 280},
        }
    )


def seed_previous_successful_feedback_run() -> None:
    app.state.store.scheduled_job_runs["scheduled_job_run_feedback_success"] = {
        "completed_at": "2026-06-07T09:28:00+00:00",
        "duration_ms": 3600,
        "error_message": None,
        "id": "scheduled_job_run_feedback_success",
        "records_imported": 120,
        "result_summary": {
            "execution_nodes": {
                "data_connection": {
                    "status": "succeeded",
                    "summary": "从 MaxCompute 读取 120 条反馈。",
                },
                "ai_processing": {
                    "model_gateway_log_id": "model_gateway_log_feedback_success",
                    "status": "succeeded",
                    "summary": "生成 5 条洞察。",
                },
                "result_action": {
                    "plugin_invocation_log_id": "plugin_invocation_log_feedback_success",
                    "status": "succeeded",
                    "summary": "写入反馈洞察表成功。",
                    "write_target": "user_feedback_insights",
                    "write_target_label": "用户洞察表",
                },
            },
            "records_imported": 120,
        },
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "started_at": "2026-06-07T09:25:00+00:00",
        "status": "succeeded",
        "trigger_type": "scheduler",
        "updated_at": "2026-06-07T09:28:00+00:00",
    }
    app.state.store.plugin_invocation_logs["plugin_invocation_log_feedback_success"] = {
        "action_id": "plugin_action_feedback_write",
        "connection_id": "plugin_connection_maxcompute",
        "created_at": "2026-06-07T09:27:50+00:00",
        "duration_ms": 900,
        "error_message": None,
        "id": "plugin_invocation_log_feedback_success",
        "plugin_id": "plugin_http",
        "request_summary": {"method": "POST", "path": "/feedback/insights"},
        "response_summary": {"status_code": 200},
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "scheduled_job_run_id": "scheduled_job_run_feedback_success",
        "status": "succeeded",
        "trigger_type": "scheduled_job",
    }
    app.state.store.model_gateway_logs.append(
        {
            "created_at": "2026-06-07T09:26:30+00:00",
            "id": "model_gateway_log_feedback_success",
            "latency_ms": 700,
            "model": "test-chat-model",
            "provider": "test",
            "purpose": "scheduled_job.ai_processing",
            "status": "succeeded",
            "tokens": {"completion": 70, "prompt": 180, "total": 250},
        }
    )


def test_ai_assistant_reference_candidates_filter_readable_knowledge_documents():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "支付", "type": "knowledge_document", "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["items"] == [
        {
            "chunk_count": 1,
            "id": "knowledge_payment_runbook",
            "index_status": "indexed",
            "permission_label": "可引用",
            "source_module": "知识库",
            "summary": "支付页提交无响应时，先检查网关超时、回调状态和前端埋点。",
            "title": "支付页超时排障手册",
            "type": "knowledge_document",
            "updated_at": "2026-06-14T08:00:00+00:00",
            "url": "/knowledge/documents?document_id=knowledge_payment_runbook",
        }
    ]


def test_ai_assistant_resolves_code_inspection_report_from_repository_context():
    source_store = assistant_task_source_store(
        {
            "code_inspection_reports": [
                {
                    "branch": "release/full-chain",
                    "created_at": "2026-06-28T10:00:00+00:00",
                    "id": "code_inspection_report_assistant",
                    "product_id": "product_assistant",
                    "repository_id": "repo_assistant",
                    "risk_level": "critical",
                    "status": "completed",
                    "summary": "全链路回归代码巡检报告",
                }
            ],
            "product_versions": [
                {
                    "code": "v-full-chain",
                    "id": "version_assistant",
                    "name": "全链路回归版本",
                    "product_id": "product_assistant",
                    "status": "active",
                }
            ],
        },
        repository=SimpleNamespace(),
    )

    resolved = resolve_assistant_references(
        source_store,
        references=[
            {
                "id": "version_assistant",
                "type": "product_version",
            },
            {
                "id": "code_inspection_report_assistant",
                "type": "code_inspection_report",
            }
        ],
        user={"id": "user_admin", "roles": ["admin"]},
    )

    assert resolved["items"] == [
        {
            "id": "version_assistant",
            "title": "全链路回归版本",
            "type": "product_version",
            "url": "/delivery/versions?version_id=version_assistant",
        },
        {
            "id": "code_inspection_report_assistant",
            "summary": "全链路回归代码巡检报告",
            "title": "全链路回归代码巡检报告",
            "type": "code_inspection_report",
            "url": (
                "/governance/execution-traces?"
                "source_id=code_inspection_report_assistant&source_type=code_inspection_report"
            ),
        }
    ]


def test_ai_assistant_reference_candidates_count_only_injectable_document_chunks():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()
    document = app.state.store.knowledge_documents["knowledge_payment_runbook"]
    document["active_chunk_set_id"] = "knowledge_payment_runbook_chunk_set_active"
    app.state.store.knowledge_chunks["knowledge_payment_runbook_chunk_001"][
        "chunk_set_id"
    ] = "knowledge_payment_runbook_chunk_set_active"
    app.state.store.knowledge_chunks["knowledge_payment_runbook_parent_chunk"] = {
        "chunk_index": 0,
        "chunk_set_id": "knowledge_payment_runbook_chunk_set_active",
        "content": "父级聚合 chunk 不应计入可注入数量。",
        "document_id": "knowledge_payment_runbook",
        "embedding": [0.1, 0.2, 0.3],
        "id": "knowledge_payment_runbook_parent_chunk",
        "metadata": {"chunk_role": "parent"},
        "permission_roles": ["reviewer"],
        "permission_scope": {"roles": ["reviewer"]},
    }
    app.state.store.knowledge_chunks["knowledge_payment_runbook_stale_chunk"] = {
        "chunk_index": 1,
        "chunk_set_id": "knowledge_payment_runbook_chunk_set_old",
        "content": "历史 chunk set 不应计入可注入数量。",
        "document_id": "knowledge_payment_runbook",
        "embedding": [0.1, 0.2, 0.3],
        "id": "knowledge_payment_runbook_stale_chunk",
        "metadata": {},
        "permission_roles": ["reviewer"],
        "permission_scope": {"roles": ["reviewer"]},
    }

    candidate_response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "支付", "type": "knowledge_document", "limit": 5},
        headers=headers,
    )
    resolve_response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "knowledge_payment_runbook", "type": "knowledge_document"},
            ]
        },
        headers=headers,
    )

    assert candidate_response.status_code == 200, candidate_response.text
    assert resolve_response.status_code == 200, resolve_response.text
    assert candidate_response.json()["data"]["items"][0]["chunk_count"] == 1
    assert len(resolve_response.json()["data"]["knowledge_context"]) == 1


def test_ai_assistant_reference_candidates_filter_readable_knowledge_chunks():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "loading", "type": "knowledge_chunk", "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["items"] == [
        {
            "chunk_count": 1,
            "chunk_index": 0,
            "document_id": "knowledge_payment_runbook",
            "id": "knowledge_payment_runbook_chunk_001",
            "permission_label": "可引用",
            "source_module": "知识库",
            "summary": "支付页提交无响应：检查网关 30 秒超时、回调幂等键和前端 loading 状态。",
            "title": "支付页超时排障手册 #1",
            "type": "knowledge_chunk",
            "updated_at": "2026-06-14T08:00:00+00:00",
            "url": (
                "/knowledge/documents?document_id=knowledge_payment_runbook"
                "&chunk_id=knowledge_payment_runbook_chunk_001"
            ),
        }
    ]


def test_ai_assistant_reference_candidates_include_readable_knowledge_spaces_and_folders():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_space_references()

    space_response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "知识空间", "limit": 5},
        headers=headers,
    )

    assert space_response.status_code == 200
    space_items = space_response.json()["data"]["items"]
    assert space_items[0] == {
        "chunk_count": 1,
        "document_count": 1,
        "id": "knowledge_space_support",
        "permission_label": "可引用",
        "source_module": "知识库",
        "summary": (
            "支付与订单支持知识空间。 支付支持知识空间 下 1 篇可检索知识文档，"
            "1 个知识 chunk 可按权限注入。"
        ),
        "title": "支付支持知识空间",
        "type": "knowledge_space",
        "updated_at": "2026-06-14T08:30:00+00:00",
        "url": "/knowledge/documents?knowledge_space_id=knowledge_space_support",
    }
    assert all(item["id"] != "knowledge_space_private" for item in space_items)

    folder_response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "支付排障目录", "limit": 5},
        headers=headers,
    )

    assert folder_response.status_code == 200
    folder_items = folder_response.json()["data"]["items"]
    assert folder_items[0] == {
        "chunk_count": 1,
        "document_count": 1,
        "folder_path": "支付排障目录",
        "id": "knowledge_folder_payment_support",
        "knowledge_space_id": "knowledge_space_support",
        "permission_label": "可引用",
        "source_module": "知识库",
        "summary": "支付排障目录 下 1 篇可检索知识文档，1 个知识 chunk 可按权限注入。",
        "title": "支付排障目录",
        "type": "knowledge_folder",
        "updated_at": "2026-06-14T08:30:00+00:00",
        "url": (
            "/knowledge/documents?knowledge_space_id=knowledge_space_support"
            "&folder_id=knowledge_folder_payment_support"
        ),
    }
    assert all(item["id"] != "knowledge_folder_private" for item in folder_items)


def test_ai_assistant_reference_candidates_read_knowledge_scopes_from_repository():
    class FakeKnowledgeRepository:
        def load_knowledge(self):
            return {
                "knowledge_folders": {},
                "knowledge_space_members": {},
                "knowledge_spaces": {
                    "knowledge_space_repository": {
                        "code": "repository",
                        "description": "Repository backed knowledge space.",
                        "id": "knowledge_space_repository",
                        "name": "Repository 知识空间",
                        "owner_user_id": "user_admin",
                        "status": "active",
                        "updated_at": "2026-06-14T08:30:00+00:00",
                    }
                },
            }

    store = SimpleNamespace(
        ai_agents={},
        ai_skills={},
        ai_tasks={},
        bugs={},
        code_review_reports={},
        human_reviews={},
        knowledge_chunks={},
        knowledge_deposits={},
        knowledge_documents={},
        knowledge_folders={},
        knowledge_space_members={},
        knowledge_spaces={},
        plugin_actions={},
        plugin_connections={},
        product_versions={},
        products={},
        repository=FakeKnowledgeRepository(),
        requirements={},
        scheduled_job_runs={},
        scheduled_jobs={},
    )

    payload = assistant_reference_candidates_response(
        store,
        limit=5,
        message="知识空间",
        product_id=None,
        reference_type=None,
        user={"id": "user_admin", "roles": ["admin"]},
    )

    assert payload["items"][0] == {
        "chunk_count": 0,
        "document_count": 0,
        "id": "knowledge_space_repository",
        "permission_label": "可引用",
        "source_module": "知识库",
        "summary": (
            "Repository backed knowledge space. Repository 知识空间 下 "
            "0 篇可检索知识文档，0 个知识 chunk 可按权限注入。"
        ),
        "title": "Repository 知识空间",
        "type": "knowledge_space",
        "updated_at": "2026-06-14T08:30:00+00:00",
        "url": "/knowledge/documents?knowledge_space_id=knowledge_space_repository",
    }


def test_ai_assistant_reference_candidates_include_admin_operational_objects():
    headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_operational_references()

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "反馈", "limit": 20},
        headers=headers,
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    reference_by_type = {item["type"]: item for item in items}
    assert reference_by_type["scheduled_job"] == {
        "id": "scheduled_job_feedback_weekly",
        "permission_label": "管理员可引用",
        "source_module": "任务中心",
        "title": "每周反馈洞察定时作业",
        "type": "scheduled_job",
        "updated_at": "2026-06-14T09:30:00+00:00",
        "url": "/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly",
    }
    assert reference_by_type["scheduled_job_run"] == {
        "id": "scheduled_job_run_feedback_failed",
        "permission_label": "管理员可引用",
        "source_module": "任务中心",
        "title": "每周反馈洞察定时作业 / failed",
        "type": "scheduled_job_run",
        "updated_at": "2026-06-14T09:35:00+00:00",
        "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
    }
    assert reference_by_type["plugin_action"]["id"] == "plugin_action_feedback_write"
    assert reference_by_type["plugin_connection"] == {
        "id": "plugin_connection_maxcompute",
        "permission_label": "管理员可引用",
        "source_module": "插件管理",
        "title": "MaxCompute 用户反馈连接",
        "type": "plugin_connection",
        "updated_at": "2026-06-14T09:30:00+00:00",
        "url": "/tasks/plugins?connection_id=plugin_connection_maxcompute",
    }
    assert reference_by_type["ai_agent"]["id"] == "ai_agent_feedback_ops"
    assert reference_by_type["ai_skill"]["id"] == "ai_skill_feedback_summary"

    reviewer_response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "反馈", "type": "scheduled_job", "limit": 20},
        headers=reviewer_headers,
    )
    assert reviewer_response.status_code == 200
    assert reviewer_response.json()["data"] == {"items": [], "total": 0}


def test_ai_assistant_reference_candidates_include_execution_trace_sources():
    app.state.store.reset()
    app.state.store.assistant_chat_runs["assistant_chat_run_trace"] = {
        "conversation_id": "assistant_conversation_trace",
        "created_at": "2026-06-20T02:00:00+00:00",
        "error_message": "模型网关调用失败",
        "finished_at": "2026-06-20T02:00:05+00:00",
        "id": "assistant_chat_run_trace",
        "status": "failed",
        "updated_at": "2026-06-20T02:00:05+00:00",
        "user_id": "user_admin",
    }

    payload = assistant_reference_candidates_response(
        app.state.store,
        limit=5,
        message="assistant_chat_run_trace",
        product_id=None,
        reference_type="assistant_chat_run",
        user={
            "id": "user_admin",
            "permissions": ["diagnostics.execution_traces.read"],
            "roles": ["admin"],
        },
    )

    assert payload["items"] == [
        {
            "id": "assistant_chat_run_trace",
            "permission_label": "管理员可引用",
            "source_module": "执行诊断",
            "summary": "模型网关调用失败",
            "title": "AI 助手运行 assistant_chat_run_trace / failed",
            "type": "assistant_chat_run",
            "updated_at": "2026-06-20T02:00:05+00:00",
            "url": (
                "/governance/execution-traces?"
                "source_id=assistant_chat_run_trace&source_type=assistant_chat_run"
            ),
        }
    ]


def test_ai_assistant_reference_candidates_read_execution_trace_sources_from_repository():
    class ExecutionTraceReferenceRepository:
        def list_execution_trace_assistant_chat_runs(self):
            return [
                {
                    "created_at": "2026-06-20T02:00:00+00:00",
                    "error_message": "仓储读取到模型网关失败",
                    "id": "assistant_chat_run_repo",
                    "status": "failed",
                    "updated_at": "2026-06-20T02:00:05+00:00",
                    "user_id": "user_admin",
                }
            ]

    payload = assistant_reference_candidates_response(
        SimpleNamespace(repository=ExecutionTraceReferenceRepository()),
        limit=5,
        message="assistant_chat_run_repo",
        product_id=None,
        reference_type="assistant_chat_run",
        user={
            "id": "user_admin",
            "permissions": ["diagnostics.execution_traces.read"],
            "roles": [],
        },
    )

    assert payload == {
        "items": [
            {
                "id": "assistant_chat_run_repo",
                "permission_label": "执行诊断权限可引用",
                "source_module": "执行诊断",
                "summary": "仓储读取到模型网关失败",
                "title": "AI 助手运行 assistant_chat_run_repo / failed",
                "type": "assistant_chat_run",
                "updated_at": "2026-06-20T02:00:05+00:00",
                "url": (
                    "/governance/execution-traces?"
                    "source_id=assistant_chat_run_repo&source_type=assistant_chat_run"
                ),
            }
        ],
        "total": 1,
    }


def test_ai_assistant_default_reference_candidates_are_balanced_across_types():
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()
    seed_assistant_knowledge_space_references()
    seed_assistant_operational_references()
    for index in range(8):
        doc_id = f"knowledge_extra_runbook_{index}"
        app.state.store.knowledge_documents[doc_id] = {
            "brain_app_id": "rd_brain",
            "content": f"默认 @ 候选知识文档 {index}",
            "created_at": f"2026-06-14T08:0{index}:00+00:00",
            "created_by": "knowledge_owner@example.com",
            "doc_type": "manual",
            "id": doc_id,
            "index_status": "indexed",
            "permission_roles": ["admin"],
            "permission_scope": {},
            "product_id": None,
            "source_type": "manual",
            "tags": ["assistant"],
            "title": f"默认候选知识文档 {index}",
            "updated_at": f"2026-06-14T08:0{index}:00+00:00",
            "vector_index_error": None,
            "version_id": None,
        }
    app.state.store.requirements["requirement_assistant_workbench"] = {
        "created_at": "2026-06-14T09:10:00+00:00",
        "id": "requirement_assistant_workbench",
        "product_id": None,
        "status": "approved",
        "summary": "AI 助手工作台升级",
        "title": "AI 助手工作台升级",
        "updated_at": "2026-06-14T09:10:00+00:00",
    }
    app.state.store.ai_tasks["ai_task_assistant_workbench"] = {
        "assignee": "rd@example.com",
        "created_at": "2026-06-14T09:20:00+00:00",
        "id": "ai_task_assistant_workbench",
        "product_id": None,
        "requirement_id": "requirement_assistant_workbench",
        "status": "running",
        "summary": "补齐助手闭环",
        "title": "补齐助手闭环",
        "updated_at": "2026-06-14T09:20:00+00:00",
    }

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "", "limit": 12},
        headers=headers,
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["type"] for item in items[:9]] == [
        "knowledge_document",
        "requirement",
        "ai_task",
        "scheduled_job",
        "scheduled_job_run",
        "plugin_action",
        "plugin_connection",
        "ai_agent",
        "ai_skill",
    ]
    item_types = [item["type"] for item in items]
    assert "model_gateway_log" in item_types
    assert item_types.index("model_gateway_log") > item_types.index("ai_skill")


def test_ai_assistant_reference_candidates_match_weekly_feedback_alias():
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    app.state.store.scheduled_jobs["scheduled_job_feedback_weekly"]["name"] = (
        "每周用户反馈洞察抽取"
    )

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "提取每周用户反馈有价值信息", "type": "scheduled_job", "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["items"] == [
        {
            "id": "scheduled_job_feedback_weekly",
            "permission_label": "管理员可引用",
            "source_module": "任务中心",
            "title": "每周用户反馈洞察抽取",
            "type": "scheduled_job",
            "updated_at": "2026-06-14T09:30:00+00:00",
            "url": "/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly",
        }
    ]


def test_ai_assistant_reference_candidates_allow_scheduled_job_runners():
    app.state.store.reset()
    seed_assistant_operational_references()

    payload = assistant_reference_candidates_response(
        app.state.store,
        limit=5,
        message="@提取每周用户反馈有价值信息 执行一次",
        product_id=None,
        reference_type="scheduled_job",
        user={
            "id": "user_ops",
            "permissions": ["system.scheduled_jobs.run"],
            "roles": ["release_owner"],
        },
    )

    assert payload["items"] == [
        {
            "id": "scheduled_job_feedback_weekly",
            "permission_label": "定时作业执行权限可引用",
            "source_module": "任务中心",
            "title": "每周反馈洞察定时作业",
            "type": "scheduled_job",
            "updated_at": "2026-06-14T09:30:00+00:00",
            "url": "/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly",
        }
    ]

    plugin_payload = assistant_reference_candidates_response(
        app.state.store,
        limit=5,
        message="插件动作",
        product_id=None,
        reference_type="plugin_action",
        user={
            "id": "user_ops",
            "permissions": ["system.scheduled_jobs.run"],
            "roles": ["release_owner"],
        },
    )
    assert plugin_payload == {"items": [], "total": 0}


def test_ai_assistant_reference_candidates_prioritize_scheduled_jobs_for_job_type_words():
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "定时作业", "limit": 3},
        headers=headers,
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items
    assert items[0]["type"] == "scheduled_job"
    assert items[0]["id"] == "scheduled_job_feedback_weekly"


def test_ai_assistant_reference_candidates_prioritize_runs_for_run_failure_words():
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "为什么这次任务失败", "limit": 3},
        headers=headers,
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items
    assert items[0]["type"] == "scheduled_job_run"
    assert items[0]["id"] == "scheduled_job_run_feedback_failed"


def test_ai_assistant_type_specific_default_candidates_are_not_globally_truncated():
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    for index in range(8):
        requirement_id = f"requirement_irrelevant_{index}"
        app.state.store.requirements[requirement_id] = {
            "created_at": f"2026-06-14T08:2{index}:00+00:00",
            "id": requirement_id,
            "product_id": None,
            "status": "approved",
            "summary": f"无关需求 {index}",
            "title": f"无关需求 {index}",
            "updated_at": f"2026-06-14T08:2{index}:00+00:00",
        }
        task_id = f"ai_task_irrelevant_{index}"
        app.state.store.ai_tasks[task_id] = {
            "assignee": "rd@example.com",
            "created_at": f"2026-06-14T08:3{index}:00+00:00",
            "id": task_id,
            "product_id": None,
            "requirement_id": requirement_id,
            "status": "running",
            "summary": f"无关 AI 任务 {index}",
            "title": f"无关 AI 任务 {index}",
            "updated_at": f"2026-06-14T08:3{index}:00+00:00",
        }

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "", "type": "scheduled_job", "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["items"] == [
        {
            "id": "scheduled_job_feedback_weekly",
            "permission_label": "管理员可引用",
            "source_module": "任务中心",
            "title": "每周反馈洞察定时作业",
            "type": "scheduled_job",
            "updated_at": "2026-06-14T09:30:00+00:00",
            "url": "/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly",
        }
    ]


def test_ai_assistant_resolve_operational_reference_requires_admin_role():
    headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_operational_references()

    response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["items"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        }
    ]

    forbidden_response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ]
        },
        headers=reviewer_headers,
    )
    assert forbidden_response.status_code == 404
    assert forbidden_response.json()["detail"]["code"] == "REFERENCE_NOT_FOUND"


def test_ai_assistant_resolve_rejects_unreadable_knowledge_reference():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()

    response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "knowledge_private_runbook", "type": "knowledge_document"},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REFERENCE_NOT_FOUND"


def test_ai_assistant_resolve_rejects_unsearchable_knowledge_document_reference():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()
    app.state.store.knowledge_documents["knowledge_index_failed_runbook"] = {
        "brain_app_id": "rd_brain",
        "content": "索引失败的文档正文不应进入 AI 助手上下文。",
        "created_at": "2026-06-14T08:00:00+00:00",
        "created_by": "reviewer@example.com",
        "doc_type": "manual",
        "id": "knowledge_index_failed_runbook",
        "index_error": "embedding failed",
        "index_status": "index_failed",
        "permission_roles": ["reviewer"],
        "status": "active",
        "tags": ["runbook"],
        "title": "索引失败的排障手册",
        "updated_at": "2026-06-14T08:00:00+00:00",
    }

    response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "knowledge_index_failed_runbook", "type": "knowledge_document"},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REFERENCE_NOT_FOUND"


def test_ai_assistant_resolve_knowledge_space_and_folder_injects_scoped_chunks():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_space_references()

    space_response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "knowledge_space_support", "type": "knowledge_space"},
            ]
        },
        headers=headers,
    )

    assert space_response.status_code == 200
    space_payload = space_response.json()["data"]
    assert space_payload["items"] == [
        {
            "chunk_count": 1,
            "document_count": 1,
            "id": "knowledge_space_support",
            "summary": (
                "支付与订单支持知识空间。 支付支持知识空间 下 1 篇可检索知识文档，"
                "1 个知识 chunk 可按权限注入。"
            ),
            "title": "支付支持知识空间",
            "type": "knowledge_space",
            "url": "/knowledge/documents?knowledge_space_id=knowledge_space_support",
        }
    ]
    assert space_payload["knowledge_context"] == [
        {
            "chunk_id": "knowledge_space_payment_runbook_chunk_001",
            "chunk_index": 0,
            "content": "空间支付排障：检查支付网关、订单回调和风控状态。",
            "document_id": "knowledge_space_payment_runbook",
            "document_title": "空间支付排障手册",
            "source": {
                "doc_type": "manual",
                "knowledge_space_id": "knowledge_space_support",
            },
        }
    ]

    folder_response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "knowledge_folder_payment_support", "type": "knowledge_folder"},
            ]
        },
        headers=headers,
    )

    assert folder_response.status_code == 200
    folder_payload = folder_response.json()["data"]
    assert folder_payload["items"][0]["type"] == "knowledge_folder"
    assert folder_payload["items"][0]["chunk_count"] == 1
    assert folder_payload["items"][0]["document_count"] == 1
    assert folder_payload["knowledge_context"] == space_payload["knowledge_context"]

    private_response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "knowledge_space_private", "type": "knowledge_space"},
            ]
        },
        headers=headers,
    )
    assert private_response.status_code == 404
    assert private_response.json()["detail"]["code"] == "REFERENCE_NOT_FOUND"


def test_ai_assistant_resolve_selected_knowledge_chunk_injects_only_that_chunk():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()
    app.state.store.knowledge_chunks["knowledge_payment_runbook_chunk_002"] = {
        "chunk_index": 1,
        "content": "支付页第二段：检查浏览器控制台和订单状态机。",
        "document_id": "knowledge_payment_runbook",
        "embedding": [0.7, 0.8, 0.9],
        "id": "knowledge_payment_runbook_chunk_002",
        "metadata": {},
        "permission_roles": ["reviewer"],
        "permission_scope": {"roles": ["reviewer"]},
    }

    response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "knowledge_payment_runbook_chunk_002", "type": "knowledge_chunk"},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["items"] == [
        {
            "id": "knowledge_payment_runbook_chunk_002",
            "title": "支付页超时排障手册 #2",
            "type": "knowledge_chunk",
            "url": (
                "/knowledge/documents?document_id=knowledge_payment_runbook"
                "&chunk_id=knowledge_payment_runbook_chunk_002"
            ),
        }
    ]
    assert payload["knowledge_context"] == [
        {
            "chunk_id": "knowledge_payment_runbook_chunk_002",
            "chunk_index": 1,
            "content": "支付页第二段：检查浏览器控制台和订单状态机。",
            "document_id": "knowledge_payment_runbook",
            "document_title": "支付页超时排障手册",
            "source": {
                "doc_type": "manual",
                "knowledge_space_id": None,
            },
        }
    ]


def test_ai_assistant_chat_injects_selected_knowledge_chunks_without_logging_content(
    monkeypatch,
):
    admin_headers = auth_headers()
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()
    captured_messages: list[dict[str, str]] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": (
                                            "应优先检查网关超时、回调幂等键"
                                            "和前端 loading 状态。"
                                        ),
                                        "suggestions": ["生成支付页排障任务"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 13, "prompt_tokens": 31, "total_tokens": 44},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        del timeout
        request_body = json.loads(request.data.decode("utf-8"))
        captured_messages.extend(request_body["messages"])
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "基于 @支付页超时排障手册 说明如何定位支付页提交无响应。",
            "references": [
                {"id": "knowledge_payment_runbook", "type": "knowledge_document"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    assistant_message = response.json()["data"]["message"]
    assert assistant_message["references"][0] == {
        "id": "knowledge_payment_runbook",
        "title": "支付页超时排障手册",
        "type": "knowledge_document",
        "url": "/knowledge/documents?document_id=knowledge_payment_runbook",
    }
    user_payload = json.loads(captured_messages[1]["content"])
    assert user_payload["system_context"]["selected_references"] == [
        {
            "id": "knowledge_payment_runbook",
            "title": "支付页超时排障手册",
            "type": "knowledge_document",
            "url": "/knowledge/documents?document_id=knowledge_payment_runbook",
        }
    ]
    assert user_payload["system_context"]["knowledge_context"][0] == {
        "chunk_id": "knowledge_payment_runbook_chunk_001",
        "chunk_index": 0,
        "content": "支付页提交无响应：检查网关 30 秒超时、回调幂等键和前端 loading 状态。",
        "document_id": "knowledge_payment_runbook",
        "document_title": "支付页超时排障手册",
        "source": {
            "doc_type": "manual",
            "knowledge_space_id": None,
        },
    }
    assert "非授权知识" not in captured_messages[1]["content"]

    logs = client.get(
        "/api/model-gateway/logs?purpose=assistant_chat",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert logs[0]["purpose"] == "assistant_chat"
    assert "支付页提交无响应" not in str(logs[0])


def test_ai_assistant_chat_returns_scheduled_job_run_diagnostic(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "这次失败发生在结果动作写入阶段。",
                                        "suggestions": ["检查插件动作返回 500 的下游服务"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "为什么这次失败？",
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    diagnostic = next(
        result
        for result in message["tool_results"]
        if result["tool"] == "assistant.scheduled_job_diagnostic"
    )
    assert diagnostic["summary"] == {"failed_count": 1, "run_count": 1}
    assert diagnostic["references"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        }
    ]
    assert diagnostic["items"][0]["stages"] == [
        {
            "error_message": None,
            "log_id": None,
            "stage": "data_connection",
            "status": "succeeded",
            "summary": "从 MaxCompute 读取 128 条反馈。",
        },
        {
            "error_message": None,
            "log_id": "model_gateway_log_feedback_failed",
            "stage": "ai_processing",
            "status": "succeeded",
            "summary": "生成 6 条洞察。",
        },
        {
            "error_code": "RESULT_WRITE_FAILED",
            "error_message": "HTTP 500: downstream write failed",
            "log_id": "plugin_invocation_log_feedback_failed",
            "result_write_record_id": "result_write_record_scheduled_job_run_feedback_failed",
            "result_write_status": "failed",
            "result_write_target": "user_feedback_insights",
            "result_write_target_label": "用户洞察表",
            "stage": "result_action",
            "status": "failed",
            "summary": "写入反馈洞察表失败。",
        },
    ]


def test_ai_assistant_run_diagnostic_keeps_data_connection_plugin_log(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    failed_run = app.state.store.scheduled_job_runs["scheduled_job_run_feedback_failed"]
    failed_run["result_summary"]["execution_nodes"]["data_connection"][
        "plugin_invocation_log_id"
    ] = "plugin_invocation_log_feedback_fetch"
    app.state.store.plugin_invocation_logs["plugin_invocation_log_feedback_fetch"] = {
        "action_id": "plugin_action_feedback_fetch",
        "connection_id": "plugin_connection_maxcompute",
        "created_at": "2026-06-14T09:31:20+00:00",
        "duration_ms": 720,
        "error_message": None,
        "id": "plugin_invocation_log_feedback_fetch",
        "plugin_id": "plugin_http",
        "request_summary": {"method": "GET", "path": "/feedback/raw"},
        "response_summary": {"status_code": 200},
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "scheduled_job_run_id": "scheduled_job_run_feedback_failed",
        "status": "succeeded",
        "trigger_type": "scheduled_job",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "这次失败发生在结果动作写入阶段。",
                                        "suggestions": ["查看数据连接和结果动作日志"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "为什么这次任务失败？",
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    diagnostic = next(
        result
        for result in response.json()["data"]["message"]["tool_results"]
        if result["tool"] == "assistant.scheduled_job_diagnostic"
    )
    stages = {
        stage["stage"]: stage
        for stage in diagnostic["items"][0]["stages"]
    }
    assert stages["data_connection"]["log_id"] == "plugin_invocation_log_feedback_fetch"
    assert stages["result_action"]["log_id"] == "plugin_invocation_log_feedback_failed"


def test_ai_assistant_chat_scopes_diagnostic_to_referenced_scheduled_job(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    app.state.store.scheduled_jobs["scheduled_job_other_failed"] = {
        "created_at": "2026-06-15T09:00:00+00:00",
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_other_failed",
        "job_type": "dashboard_snapshot_refresh",
        "name": "其他失败定时作业",
        "product_id": None,
        "schedule_type": "manual",
        "source_system": "ai-assistant-test",
        "status": "active",
        "updated_at": "2026-06-15T09:00:00+00:00",
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_other_failed"] = {
        "completed_at": "2026-06-15T09:20:00+00:00",
        "duration_ms": 3000,
        "error_message": "其他作业失败",
        "id": "scheduled_job_run_other_failed",
        "result_summary": {
            "execution_nodes": {
                "result_action": {
                    "status": "failed",
                    "summary": "其他作业写入失败。",
                },
            }
        },
        "scheduled_job_id": "scheduled_job_other_failed",
        "started_at": "2026-06-15T09:18:00+00:00",
        "status": "failed",
        "trigger_type": "manual",
        "updated_at": "2026-06-15T09:20:00+00:00",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "已按所引用的定时作业诊断最近失败运行。",
                                        "suggestions": ["查看本次运行记录"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "为什么这个定时作业失败？",
            "references": [
                {"id": "scheduled_job_feedback_weekly", "type": "scheduled_job"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    diagnostic = next(
        result
        for result in message["tool_results"]
        if result["tool"] == "assistant.scheduled_job_diagnostic"
    )
    assert diagnostic["summary"] == {"failed_count": 1, "run_count": 1}
    assert [item["id"] for item in diagnostic["items"]] == [
        "scheduled_job_run_feedback_failed",
    ]
    assert diagnostic["references"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        }
    ]


def test_ai_assistant_chat_compares_run_with_previous_success(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    seed_previous_successful_feedback_run()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": (
                                            "这次和上次成功相比，"
                                            "差异集中在结果动作写入阶段。"
                                        ),
                                        "suggestions": ["检查用户洞察表写入接口"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "和上次成功有什么不同？",
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    comparison = next(
        result
        for result in message["tool_results"]
        if result["tool"] == "assistant.scheduled_job_run_comparison"
    )
    assert comparison["summary"] == {"baseline_found_count": 1, "comparison_count": 1}
    item = comparison["items"][0]
    assert item["current_run"]["id"] == "scheduled_job_run_feedback_failed"
    assert item["baseline_run"]["id"] == "scheduled_job_run_feedback_success"
    assert item["differences"][0] == {
        "baseline": "succeeded",
        "current": "failed",
        "field": "status",
    }
    result_action_difference = next(
        difference
        for difference in item["differences"]
        if difference.get("stage") == "result_action"
    )
    assert result_action_difference == {
        "baseline_result_write_status": "succeeded",
        "baseline_result_write_target": "user_feedback_insights",
        "baseline_status": "succeeded",
        "baseline_summary": "写入反馈洞察表成功。",
        "current_result_write_status": "failed",
        "current_result_write_target": "user_feedback_insights",
        "current_status": "failed",
        "current_summary": "写入反馈洞察表失败。",
        "field": "stage.result_action",
        "stage": "result_action",
    }
    assert comparison["references"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        },
        {
            "id": "scheduled_job_run_feedback_success",
            "title": "每周反馈洞察定时作业 / succeeded",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_success",
        },
    ]


def test_ai_assistant_chat_compares_referenced_scheduled_job_latest_failure_with_previous_success(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    seed_previous_successful_feedback_run()
    app.state.store.scheduled_jobs["scheduled_job_order_sync"] = {
        "agent_id": "ai_agent_feedback_ops",
        "created_at": "2026-06-15T08:00:00+00:00",
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_order_sync",
        "job_type": "order_sync",
        "name": "订单同步定时作业",
        "plugin_action_id": "plugin_action_feedback_write",
        "product_id": None,
        "schedule_type": "cron",
        "skill_ids": [],
        "source_system": "ai-assistant-test",
        "status": "active",
        "updated_at": "2026-06-15T08:00:00+00:00",
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_order_sync_failed"] = {
        "completed_at": "2026-06-15T08:05:00+00:00",
        "duration_ms": 1800,
        "error_message": "订单同步接口超时",
        "id": "scheduled_job_run_order_sync_failed",
        "records_imported": 0,
        "result_summary": {
            "execution_nodes": {
                "data_connection": {
                    "error_message": "upstream timeout",
                    "status": "failed",
                    "summary": "订单源接口超时。",
                }
            },
            "records_imported": 0,
        },
        "scheduled_job_id": "scheduled_job_order_sync",
        "started_at": "2026-06-15T08:03:00+00:00",
        "status": "failed",
        "trigger_type": "scheduler",
        "updated_at": "2026-06-15T08:05:00+00:00",
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_feedback_failed_older"] = {
        "completed_at": "2026-06-13T09:35:00+00:00",
        "duration_ms": 3900,
        "error_message": "历史写入动作失败",
        "id": "scheduled_job_run_feedback_failed_older",
        "records_imported": 118,
        "result_summary": {
            "execution_nodes": {
                "data_connection": {
                    "status": "succeeded",
                    "summary": "从 MaxCompute 读取 118 条反馈。",
                },
                "result_action": {
                    "status": "failed",
                    "summary": "历史写入反馈洞察表失败。",
                    "write_target": "user_feedback_insights",
                },
            },
            "records_imported": 118,
        },
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "started_at": "2026-06-13T09:31:00+00:00",
        "status": "failed",
        "trigger_type": "scheduler",
        "updated_at": "2026-06-13T09:35:00+00:00",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": (
                                            "已限定到引用的定时作业，"
                                            "对比最近失败运行和上次成功运行。"
                                        ),
                                        "suggestions": ["检查用户洞察表写入接口"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "这个定时作业和上次成功有什么不同？",
            "references": [
                {"id": "scheduled_job_feedback_weekly", "type": "scheduled_job"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    comparison = next(
        result
        for result in message["tool_results"]
        if result["tool"] == "assistant.scheduled_job_run_comparison"
    )
    assert comparison["summary"] == {"baseline_found_count": 1, "comparison_count": 1}
    item = comparison["items"][0]
    assert item["current_run"]["id"] == "scheduled_job_run_feedback_failed"
    assert item["baseline_run"]["id"] == "scheduled_job_run_feedback_success"
    assert item["scheduled_job_id"] == "scheduled_job_feedback_weekly"
    assert {reference["id"] for reference in comparison["references"]} == {
        "scheduled_job_run_feedback_failed",
        "scheduled_job_run_feedback_success",
    }


def test_ai_assistant_chat_generates_repair_action_draft_for_failed_run(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": (
                                            "我已生成结果动作修复草案，"
                                            "确认前不会写入真实动作。"
                                        ),
                                        "suggestions": ["查看修复草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "这次失败怎么修？帮我生成修复草案",
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    draft_result = next(
        result
        for result in message["tool_results"]
        if result["tool"] == "assistant.action_draft"
        and result["intent"] == "scheduled_job_run_repair_draft"
    )
    assert draft_result["summary"] == {
        "draft_count": 1,
        "requires_confirmation": True,
        "source_run_id": "scheduled_job_run_feedback_failed",
        "target": "plugin_action",
    }
    draft_item = draft_result["items"][0]
    assert draft_item["action"] == "create_plugin_action"
    assert draft_item["client_draft_id"] == (
        "assistant_draft_repair_scheduled_job_run_feedback_failed"
    )
    assert draft_item["draft_id"].startswith("assistant_action_draft_")
    assert draft_item["server_draft_id"] == draft_item["draft_id"]
    assert draft_item["status"] == "pending"
    assert draft_item["title"] == "反馈洞察写入动作修复草案"
    assert draft_item["requires_confirmation"] is True
    assert draft_item["risk_level"] == "medium"
    assert draft_item["references"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        }
    ]
    assert draft_item["payload"] == {
        "action_type": "http_request",
        "code": "feedback_write_repair",
        "connection_id": "plugin_connection_maxcompute",
        "description": (
            "从失败运行 scheduled_job_run_feedback_failed 生成，"
            "用于修复结果动作写入失败。"
        ),
        "name": "反馈洞察写入动作修复草案",
        "plugin_id": "plugin_http",
        "request_config": {"method": "POST", "path": "/feedback/insights"},
        "result_mapping": {"write_target": "user_feedback_insights"},
        "status": "active",
    }

    draft_response = client.get(
        f"/api/assistant/action-drafts/{draft_item['draft_id']}",
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["action"] == "create_plugin_action"
    assert draft["client_draft_id"] == (
        "assistant_draft_repair_scheduled_job_run_feedback_failed"
    )
    assert draft["source_message_id"] == message["id"]
    assert draft_item["source_resource"] == {
        "id": "plugin_action_feedback_write",
        "title": "反馈洞察写入动作",
        "type": "plugin_action",
        "url": "/tasks/plugins?action_id=plugin_action_feedback_write",
    }
    assert draft["metadata_json"]["source_resource"] == draft_item["source_resource"]
    assert draft["preview"]["target"]["source_resource"] == {
        "resource_id": "plugin_action_feedback_write",
        "resource_type": "plugin_action",
        "title": "反馈洞察写入动作",
    }
    diff_by_field = {item["field"]: item for item in draft["preview"]["diffs"]}
    assert diff_by_field["code"] == {
        "change_type": "update",
        "current": "feedback_write",
        "field": "code",
        "label": "编码",
        "proposed": "feedback_write_repair",
    }
    assert diff_by_field["name"] == {
        "change_type": "update",
        "current": "反馈洞察写入动作",
        "field": "name",
        "label": "名称",
        "proposed": "反馈洞察写入动作修复草案",
    }
    assert draft["preview"]["validation"]["status"] == "passed"


def test_ai_assistant_chat_scopes_repair_draft_to_referenced_scheduled_job(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    app.state.store.plugin_actions["plugin_action_other_write"] = {
        "action_type": "http_request",
        "code": "other_write",
        "created_at": "2026-06-15T09:00:00+00:00",
        "id": "plugin_action_other_write",
        "name": "其他写入动作",
        "plugin_id": "plugin_http",
        "request_config": {"method": "POST", "path": "/other/results"},
        "status": "active",
        "updated_at": "2026-06-15T09:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_other_failed"] = {
        "created_at": "2026-06-15T09:00:00+00:00",
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_other_failed",
        "job_type": "dashboard_snapshot_refresh",
        "name": "其他失败定时作业",
        "plugin_action_id": "plugin_action_other_write",
        "product_id": None,
        "schedule_type": "manual",
        "source_system": "ai-assistant-test",
        "status": "active",
        "updated_at": "2026-06-15T09:00:00+00:00",
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_other_failed"] = {
        "completed_at": "2026-06-15T09:20:00+00:00",
        "duration_ms": 3000,
        "error_message": "其他作业失败",
        "id": "scheduled_job_run_other_failed",
        "result_summary": {
            "execution_nodes": {
                "result_action": {
                    "plugin_invocation_log_id": "plugin_invocation_log_other_failed",
                    "status": "failed",
                    "summary": "其他作业写入失败。",
                    "write_target": "dashboard_metric_snapshots",
                },
            }
        },
        "scheduled_job_id": "scheduled_job_other_failed",
        "started_at": "2026-06-15T09:18:00+00:00",
        "status": "failed",
        "trigger_type": "manual",
        "updated_at": "2026-06-15T09:20:00+00:00",
    }
    app.state.store.plugin_invocation_logs["plugin_invocation_log_other_failed"] = {
        "action_id": "plugin_action_other_write",
        "connection_id": "plugin_connection_other",
        "created_at": "2026-06-15T09:19:58+00:00",
        "duration_ms": 1200,
        "error_message": "HTTP 500: other failed",
        "id": "plugin_invocation_log_other_failed",
        "plugin_id": "plugin_http",
        "request_summary": {"method": "POST", "path": "/other/results"},
        "response_summary": {"status_code": 500},
        "scheduled_job_id": "scheduled_job_other_failed",
        "scheduled_job_run_id": "scheduled_job_run_other_failed",
        "status": "failed",
        "trigger_type": "scheduled_job",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "已按所引用的定时作业生成修复草案。",
                                        "suggestions": ["查看修复草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "这个定时作业失败怎么修？帮我生成修复草案",
            "references": [
                {"id": "scheduled_job_feedback_weekly", "type": "scheduled_job"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    draft_result = next(
        result
        for result in message["tool_results"]
        if result["tool"] == "assistant.action_draft"
        and result["intent"] == "scheduled_job_run_repair_draft"
    )
    assert draft_result["summary"]["source_run_id"] == "scheduled_job_run_feedback_failed"
    draft_item = draft_result["items"][0]
    assert draft_item["client_draft_id"] == (
        "assistant_draft_repair_scheduled_job_run_feedback_failed"
    )
    assert draft_item["references"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        }
    ]
    assert draft_item["payload"]["description"] == (
        "从失败运行 scheduled_job_run_feedback_failed 生成，"
        "用于修复结果动作写入失败。"
    )


def test_ai_assistant_chat_generates_business_drafts_from_scheduled_job_run(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "我已基于本次运行生成业务草案，确认后归档。",
                                        "suggestions": ["查看草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    monkeypatch.setattr(assistant_router, "urlopen", lambda _request, timeout: FakeResponse())

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "请基于这次定时作业运行结果生成用户洞察、需求和 Bug 草案",
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    draft_result = next(
        result
        for result in message["tool_results"]
        if result["tool"] == "assistant.action_draft"
        and result["intent"] == "scheduled_job_run_business_draft"
    )
    assert draft_result["summary"] == {
        "draft_count": 3,
        "draft_types": ["user_insight", "requirement", "bug"],
        "requires_confirmation": True,
        "source_run_id": "scheduled_job_run_feedback_failed",
        "target": "assistant_analysis",
    }
    items_by_analysis_type = {
        item["payload"]["analysis_type"]: item for item in draft_result["items"]
    }
    assert set(items_by_analysis_type) == {
        "scheduled_job_run_bug_draft",
        "scheduled_job_run_requirement_draft",
        "scheduled_job_run_user_insight_draft",
    }
    insight_item = items_by_analysis_type["scheduled_job_run_user_insight_draft"]
    assert insight_item["action"] == "create_analysis_draft"
    assert insight_item["client_draft_id"] == (
        "assistant_draft_user_insight_scheduled_job_run_feedback_failed"
    )
    assert insight_item["draft_id"].startswith("assistant_action_draft_")
    assert insight_item["server_draft_id"] == insight_item["draft_id"]
    assert insight_item["status"] == "pending"
    assert insight_item["requires_confirmation"] is True
    assert insight_item["references"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        }
    ]
    assert insight_item["payload"]["summary"] == {
        "records_imported": 128,
        "result_write_record_id": (
            "result_write_record_scheduled_job_run_feedback_failed"
        ),
        "result_write_status": "failed",
        "result_write_target": "user_feedback_insights",
        "run_id": "scheduled_job_run_feedback_failed",
        "run_status": "failed",
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "trigger_type": "manual",
    }
    assert insight_item["payload"]["findings"][0]["type"] == (
        "scheduled_job_run_user_insight"
    )

    requirement_item = items_by_analysis_type["scheduled_job_run_requirement_draft"]
    assert requirement_item["payload"]["findings"][0]["title"] == "待提炼需求"
    bug_item = items_by_analysis_type["scheduled_job_run_bug_draft"]
    assert bug_item["payload"]["findings"][0]["message"] == "结果写入动作返回 500"

    draft_response = client.get(
        f"/api/assistant/action-drafts/{insight_item['draft_id']}",
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["action"] == "create_analysis_draft"
    assert draft["source_message_id"] == message["id"]
    assert draft["preview"]["target"]["resource_type"] == "assistant_analysis"

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{insight_item['draft_id']}/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 200
    run = confirm_response.json()["data"]["run"]
    assert run["action"] == "create_analysis_draft"
    assert run["result_type"] == "assistant_analysis"
    assert run["result"]["analysis_type"] == "scheduled_job_run_user_insight_draft"
    assert run["result"]["source_draft_id"] == insight_item["draft_id"]


def test_ai_assistant_action_draft_can_be_confirmed_into_scheduled_job():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "AI 助手草案仪表盘刷新",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建仪表盘刷新定时任务",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["action"] == "create_scheduled_job"
    assert draft["status"] == "pending"
    assert draft["created_by"] == "user_admin"
    assert draft["payload"]["name"] == "AI 助手草案仪表盘刷新"

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 200
    payload = confirm_response.json()["data"]
    assert payload["draft"]["id"] == draft["id"]
    assert payload["draft"]["status"] == "confirmed"
    assert payload["run"]["action"] == "create_scheduled_job"
    assert payload["run"]["status"] == "succeeded"
    assert payload["run"]["result_type"] == "scheduled_job"
    scheduled_job = payload["run"]["result"]
    assert scheduled_job["name"] == "AI 助手草案仪表盘刷新"
    assert scheduled_job["config_json"]["assistant_draft"] == {
        "draft_id": draft["id"],
        "source": "ai_assistant",
        "title": "创建仪表盘刷新定时任务",
    }

    get_response = client.get(f"/api/assistant/action-drafts/{draft['id']}", headers=headers)
    assert get_response.status_code == 200
    persisted_draft = get_response.json()["data"]
    assert persisted_draft["status"] == "confirmed"
    assert persisted_draft["result_run"]["id"] == payload["run"]["id"]
    assert persisted_draft["result_run"]["result_type"] == "scheduled_job"
    assert persisted_draft["result_run"]["result_id"] == scheduled_job["id"]

    audit_events = client.get(
        "/api/audit/events?subject_type=assistant_action_draft",
        headers=headers,
    ).json()["data"]["items"]
    audit_events = sorted(audit_events, key=lambda item: item["sequence"])
    assert [item["event_type"] for item in audit_events] == [
        "assistant_action_draft.created",
        "assistant_action_draft.confirmed",
    ]


def test_ai_assistant_ai_capability_draft_can_be_confirmed_by_ai_capability_manager():
    app.state.store.reset()
    user = {
        "id": "user_ai_capability_manager",
        "permissions": ["system.ai_capabilities.manage"],
        "roles": [],
    }

    draft = assistant_action_drafts_service.create_assistant_action_draft_response(
        current_store=app.state.store,
        payload=SimpleNamespace(
            action="create_ai_skill",
            client_draft_id=None,
            metadata_json={},
            payload={
                "allowed_tools": [],
                "code": "feedback_signal_extract",
                "description": "提取用户反馈中的高价值信号。",
                "input_schema": {},
                "name": "反馈价值信号提取",
                "output_schema": {},
                "prompt_template": "提取用户反馈中的需求、缺陷和风险信号。",
                "required_context": [],
                "requires_human_review": False,
                "risk_level": "medium",
                "status": "active",
                "version": "1.0.0",
            },
            risk_level="medium",
            source_message_id=None,
            title="创建反馈价值信号 Skill",
        ),
        user=user,
    )

    assert draft["preview"]["validation"]["status"] == "passed"

    confirmed = assistant_action_drafts_service.confirm_assistant_action_draft_response(
        current_store=app.state.store,
        draft_id=draft["id"],
        user=user,
    )

    assert confirmed["draft"]["status"] == "confirmed"
    assert confirmed["run"]["result_type"] == "ai_skill"
    assert confirmed["run"]["result"]["code"] == "feedback_signal_extract"
    assert confirmed["run"]["result"]["id"] in app.state.store.ai_skills


def test_ai_assistant_ai_agent_draft_can_be_confirmed_by_ai_capability_manager():
    app.state.store.reset()
    user = {
        "id": "user_ai_capability_manager",
        "permissions": ["system.ai_capabilities.manage"],
        "roles": [],
    }

    draft = assistant_action_drafts_service.create_assistant_action_draft_response(
        current_store=app.state.store,
        payload=SimpleNamespace(
            action="create_ai_agent",
            client_draft_id=None,
            metadata_json={},
            payload={
                "brain_app_id": "rd_brain",
                "code": "feedback_agent",
                "default_skill_ids": [],
                "description": "负责用户反馈分析。",
                "execution_policy": {},
                "model_gateway_config_id": None,
                "name": "反馈洞察 AI 角色",
                "status": "active",
                "system_prompt": "你负责把用户反馈归纳为可行动洞察。",
                "tool_policy": {},
            },
            risk_level="medium",
            source_message_id=None,
            title="创建反馈洞察 AI 角色",
        ),
        user=user,
    )

    assert draft["preview"]["validation"]["status"] == "passed"

    confirmed = assistant_action_drafts_service.confirm_assistant_action_draft_response(
        current_store=app.state.store,
        draft_id=draft["id"],
        user=user,
    )

    assert confirmed["draft"]["status"] == "confirmed"
    assert confirmed["run"]["result_type"] == "ai_agent"
    assert confirmed["run"]["result"]["code"] == "feedback_agent"
    assert confirmed["run"]["result"]["id"] in app.state.store.ai_agents


def test_ai_assistant_plugin_connection_draft_can_be_confirmed_by_plugin_manager():
    app.state.store.reset()
    seed_assistant_operational_references()
    user = {
        "id": "user_plugin_manager",
        "permissions": ["system.plugins.manage"],
        "roles": [],
    }

    draft = assistant_action_drafts_service.create_assistant_action_draft_response(
        current_store=app.state.store,
        payload=SimpleNamespace(
            action="create_plugin_connection",
            client_draft_id=None,
            metadata_json={},
            payload={
                "auth_config": {},
                "auth_type": "none",
                "endpoint_url": "https://plugins.example.com",
                "environment": "prod",
                "name": "插件管理连接",
                "plugin_id": "plugin_http",
                "request_config": {},
                "status": "active",
            },
            risk_level="medium",
            source_message_id=None,
            title="创建插件管理连接",
        ),
        user=user,
    )

    assert draft["preview"]["validation"]["status"] == "passed"

    confirmed = assistant_action_drafts_service.confirm_assistant_action_draft_response(
        current_store=app.state.store,
        draft_id=draft["id"],
        user=user,
    )

    assert confirmed["draft"]["status"] == "confirmed"
    assert confirmed["run"]["result_type"] == "plugin_connection"
    assert confirmed["run"]["result"]["name"] == "插件管理连接"
    assert confirmed["run"]["result"]["id"] in app.state.store.plugin_connections


def test_ai_assistant_plugin_action_draft_can_be_confirmed_by_plugin_manager():
    app.state.store.reset()
    seed_assistant_operational_references()
    user = {
        "id": "user_plugin_manager",
        "permissions": ["system.plugins.manage"],
        "roles": [],
    }

    draft = assistant_action_drafts_service.create_assistant_action_draft_response(
        current_store=app.state.store,
        payload=SimpleNamespace(
            action="create_plugin_action",
            client_draft_id=None,
            metadata_json={},
            payload={
                "action_type": "http_request",
                "code": "feedback_signal_write",
                "connection_id": "plugin_connection_maxcompute",
                "name": "反馈信号写入动作",
                "plugin_id": "plugin_http",
                "request_config": {
                    "method": "POST",
                    "path": "/feedback/signals",
                },
                "result_mapping": {"write_target": "user_feedback_insights"},
                "status": "active",
            },
            risk_level="medium",
            source_message_id=None,
            title="创建反馈信号写入动作",
        ),
        user=user,
    )

    assert draft["preview"]["validation"]["status"] == "passed"

    confirmed = assistant_action_drafts_service.confirm_assistant_action_draft_response(
        current_store=app.state.store,
        draft_id=draft["id"],
        user=user,
    )

    assert confirmed["draft"]["status"] == "confirmed"
    assert confirmed["run"]["result_type"] == "plugin_action"
    assert confirmed["run"]["result"]["code"] == "feedback_signal_write"
    assert confirmed["run"]["result"]["id"] in app.state.store.plugin_actions


def test_ai_assistant_action_draft_confirm_failure_is_persisted(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "会确认失败的定时任务",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建会确认失败的定时任务",
        },
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft_id = draft_response.json()["data"]["id"]

    def failing_create_scheduled_job_response(*, current_store, payload, user):
        raise api_error(400, "SCHEDULED_JOB_INVALID", "模拟定时任务保存失败")

    monkeypatch.setattr(
        assistant_action_drafts_service,
        "create_scheduled_job_response",
        failing_create_scheduled_job_response,
    )

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 400
    assert confirm_response.json()["detail"]["code"] == "SCHEDULED_JOB_INVALID"

    detail_response = client.get(
        f"/api/assistant/action-drafts/{draft_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    draft = detail_response.json()["data"]
    assert draft["status"] == "failed"
    assert draft["metadata_json"]["failure"] == {
        "code": "SCHEDULED_JOB_INVALID",
        "message": "模拟定时任务保存失败",
    }

    run_id = draft["result_run_id"]
    run = app.state.store.assistant_action_runs[run_id]
    assert run["draft_id"] == draft_id
    assert run["status"] == "failed"
    assert run["error_code"] == "SCHEDULED_JOB_INVALID"
    assert run["error_message"] == "模拟定时任务保存失败"

    metrics = client.get("/api/assistant/metrics", headers=headers).json()["data"]
    assert metrics["summary"]["draft_failed_count"] == 1
    assert metrics["summary"]["action_run_failed_count"] == 1

    audit_events = client.get(
        "/api/audit/events?subject_type=assistant_action_draft",
        headers=headers,
    ).json()["data"]["items"]
    failed_event = next(
        item
        for item in audit_events
        if item["event_type"] == "assistant_action_draft.failed"
    )
    assert failed_event["subject_id"] == draft_id
    assert failed_event["payload"]["error_code"] == "SCHEDULED_JOB_INVALID"
    assert failed_event["payload"]["run_id"] == run_id


def test_ai_assistant_action_draft_payload_update_marks_modified_before_confirmation():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": True,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "原始草案作业",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建可编辑的定时任务",
        },
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft_id = draft_response.json()["data"]["id"]

    patch_response = client.patch(
        f"/api/assistant/action-drafts/{draft_id}",
        json={
            "modified_fields": ["name"],
            "payload": {
                "enabled": True,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "表单调整后的草案作业",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
        },
        headers=headers,
    )

    assert patch_response.status_code == 200
    draft = patch_response.json()["data"]
    assert draft["status"] == "pending"
    assert draft["payload"]["name"] == "表单调整后的草案作业"
    assert draft["metadata_json"]["user_modified"] is True
    assert draft["metadata_json"]["modified_fields"] == ["name"]

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 200
    result = confirm_response.json()["data"]["run"]["result"]
    assert result["name"] == "表单调整后的草案作业"


def test_ai_assistant_action_draft_confirm_is_idempotent_after_success():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": True,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "幂等确认定时任务",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建幂等确认定时任务",
        },
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft_id = draft_response.json()["data"]["id"]

    first_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/confirm",
        headers=headers,
    )
    second_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/confirm",
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.json()["data"]
    second = second_response.json()["data"]
    assert second["draft"]["status"] == "confirmed"
    assert second["run"]["id"] == first["run"]["id"]
    assert second["run"]["result_id"] == first["run"]["result_id"]
    assert len(app.state.store.scheduled_jobs) == 1
    assert len(app.state.store.assistant_action_runs) == 1


def test_ai_assistant_action_draft_modification_rejects_terminal_status():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": True,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "已确认后不可修改的定时任务",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建确认后不可修改定时任务",
        },
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft_id = draft_response.json()["data"]["id"]
    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 200

    modification_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/modification",
        json={"modified_fields": ["name"], "user_modified": True},
        headers=headers,
    )

    assert modification_response.status_code == 409
    assert modification_response.json()["detail"]["code"] == "DRAFT_NOT_PENDING"


def test_ai_assistant_run_once_draft_confirm_triggers_scheduled_job_run():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "config_json": {
                    "assistant_run_once_request": {
                        "requested": True,
                        "source_message": "@提取每周用户反馈有价值信息 执行一次",
                    },
                },
                "enabled": True,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "确认后立即执行的反馈洞察作业",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建并执行反馈洞察定时作业",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 200
    payload = confirm_response.json()["data"]
    scheduled_job = payload["run"]["result"]
    triggered_run = scheduled_job["scheduled_job_run"]
    assert payload["run"]["result_type"] == "scheduled_job"
    assert triggered_run["scheduled_job_id"] == scheduled_job["id"]
    assert triggered_run["trigger_type"] == "manual"
    assert triggered_run["status"] == "succeeded"
    assert triggered_run["id"] in app.state.store.scheduled_job_runs
    assert scheduled_job["config_json"]["assistant_run_once_request"] == {
        "requested": True,
        "source_message": "@提取每周用户反馈有价值信息 执行一次",
    }
    audit_events = client.get(
        "/api/audit/events?subject_type=assistant_action_draft",
        headers=headers,
    ).json()["data"]["items"]
    confirmed_event = next(
        item
        for item in audit_events
        if item["event_type"] == "assistant_action_draft.confirmed"
    )
    assert confirmed_event["payload"]["scheduled_job_run_id"] == triggered_run["id"]


def test_ai_assistant_metrics_summarize_drafts_runs_and_reference_usage():
    headers = auth_headers()
    app.state.store.reset()
    now = "2026-06-16T10:00:00+00:00"

    app.state.store.assistant_action_drafts = {
        "assistant_action_draft_pending": {
            "action": "create_scheduled_job",
            "created_at": now,
            "created_by": "user_admin",
            "id": "assistant_action_draft_pending",
            "metadata_json": {},
            "payload": {"name": "待确认草案"},
            "risk_level": "medium",
            "status": "pending",
            "title": "待确认草案",
            "updated_at": now,
        },
        "assistant_action_draft_confirmed": {
            "action": "create_scheduled_job",
            "confirmed_at": now,
            "confirmed_by": "user_admin",
            "created_at": now,
            "created_by": "user_admin",
            "id": "assistant_action_draft_confirmed",
            "metadata_json": {
                "deeplink_viewed_at": now,
                "detail_viewed_at": now,
                "modified_fields": ["cron_expression"],
                "viewed_at": now,
            },
            "payload": {"name": "已确认草案"},
            "result_run_id": "assistant_action_run_succeeded",
            "risk_level": "medium",
            "status": "confirmed",
            "title": "已确认草案",
            "updated_at": now,
        },
        "assistant_action_draft_cancelled": {
            "action": "create_plugin_action",
            "cancelled_at": now,
            "cancelled_by": "user_admin",
            "created_at": now,
            "created_by": "user_admin",
            "id": "assistant_action_draft_cancelled",
            "metadata_json": {"user_modified": False},
            "payload": {"name": "已取消草案"},
            "risk_level": "low",
            "status": "cancelled",
            "title": "已取消草案",
            "updated_at": now,
        },
        "assistant_action_draft_expired": {
            "action": "create_scheduled_job",
            "created_at": now,
            "created_by": "user_admin",
            "expires_at": "2026-06-15T10:00:00+00:00",
            "id": "assistant_action_draft_expired",
            "metadata_json": {},
            "payload": {"name": "已过期草案"},
            "risk_level": "medium",
            "status": "pending",
            "title": "已过期草案",
            "updated_at": now,
        },
        "assistant_action_draft_other_user": {
            "action": "create_scheduled_job",
            "created_at": now,
            "created_by": "user_reviewer",
            "id": "assistant_action_draft_other_user",
            "metadata_json": {},
            "payload": {"name": "其他人的草案"},
            "risk_level": "medium",
            "status": "confirmed",
            "title": "其他人的草案",
            "updated_at": now,
        },
    }
    app.state.store.assistant_action_runs = {
        "assistant_action_run_succeeded": {
            "action": "create_scheduled_job",
            "created_at": now,
            "draft_id": "assistant_action_draft_confirmed",
            "executed_by": "user_admin",
            "finished_at": now,
            "id": "assistant_action_run_succeeded",
            "result": {"id": "scheduled_job_metrics"},
            "result_id": "scheduled_job_metrics",
            "result_type": "scheduled_job",
            "started_at": now,
            "status": "succeeded",
            "updated_at": now,
        },
        "assistant_action_run_other_user": {
            "action": "create_scheduled_job",
            "created_at": now,
            "draft_id": "assistant_action_draft_other_user",
            "executed_by": "user_reviewer",
            "finished_at": now,
            "id": "assistant_action_run_other_user",
            "result": {},
            "started_at": now,
            "status": "failed",
            "updated_at": now,
        },
    }
    app.state.store.scheduled_job_runs = {
        "scheduled_job_run_failed_metrics": {
            "created_at": now,
            "error_code": "RESULT_ACTION_FAILED",
            "error_message": "结果写入失败",
            "finished_at": now,
            "id": "scheduled_job_run_failed_metrics",
            "records_imported": 0,
            "result_summary": {},
            "scheduled_job_id": "scheduled_job_metrics",
            "source_run_id": None,
            "started_at": now,
            "status": "failed",
            "trigger_type": "manual",
            "updated_at": now,
        },
        "scheduled_job_run_repair_metrics": {
            "assistant_action_draft_id": "assistant_action_draft_confirmed",
            "assistant_action_run_id": "assistant_action_run_succeeded",
            "created_at": now,
            "error_code": None,
            "error_message": None,
            "finished_at": now,
            "id": "scheduled_job_run_repair_metrics",
            "records_imported": 6,
            "result_summary": {},
            "scheduled_job_id": "scheduled_job_metrics",
            "source_run_id": "scheduled_job_run_failed_metrics",
            "started_at": now,
            "status": "succeeded",
            "triggered_by_assistant": True,
            "trigger_type": "manual_rerun",
            "updated_at": now,
        },
        "scheduled_job_run_non_repair_failed_metrics": {
            "created_at": now,
            "error_code": "SCHEDULED_FAILURE",
            "error_message": "普通调度失败不应被非 manual_rerun 成功计为修复。",
            "finished_at": now,
            "id": "scheduled_job_run_non_repair_failed_metrics",
            "records_imported": 0,
            "result_summary": {},
            "scheduled_job_id": "scheduled_job_metrics",
            "source_run_id": None,
            "started_at": now,
            "status": "failed",
            "trigger_type": "scheduled",
            "updated_at": now,
        },
        "scheduled_job_run_non_repair_success_metrics": {
            "created_at": now,
            "error_code": None,
            "error_message": None,
            "finished_at": now,
            "id": "scheduled_job_run_non_repair_success_metrics",
            "records_imported": 4,
            "result_summary": {},
            "scheduled_job_id": "scheduled_job_metrics",
            "source_run_id": "scheduled_job_run_non_repair_failed_metrics",
            "started_at": now,
            "status": "succeeded",
            "trigger_type": "scheduled",
            "updated_at": now,
        },
        "scheduled_job_run_other_user_failed": {
            "created_at": now,
            "error_code": "OTHER_FAILURE",
            "error_message": "其他用户作业失败",
            "finished_at": now,
            "id": "scheduled_job_run_other_user_failed",
            "records_imported": 0,
            "result_summary": {},
            "scheduled_job_id": "scheduled_job_other_user",
            "source_run_id": None,
            "started_at": now,
            "status": "failed",
            "trigger_type": "manual",
            "updated_at": now,
        },
    }
    app.state.store.assistant_messages = {
        "assistant_message_user_plain": {
            "content": "当前进展如何？",
            "conversation_id": "assistant_conversation_metrics",
            "created_at": now,
            "id": "assistant_message_user_plain",
            "metadata_json": {"references": []},
            "role": "user",
            "suggestions": [],
            "updated_at": now,
            "user_id": "user_admin",
        },
        "assistant_message_user_refs": {
            "content": "@支付页超时排障手册 总结一下",
            "conversation_id": "assistant_conversation_metrics",
            "created_at": now,
            "id": "assistant_message_user_refs",
            "metadata_json": {
                "references": [
                    {"id": "knowledge_payment_runbook", "type": "knowledge_document"},
                    {"id": "knowledge_checkout_runbook", "type": "knowledge_document"},
                    {"id": "knowledge_folder_checkout", "type": "knowledge_folder"},
                    {"id": "scheduled_job_feedback_weekly", "type": "scheduled_job"},
                ]
            },
            "role": "user",
            "suggestions": [],
            "updated_at": now,
            "user_id": "user_admin",
        },
        "assistant_message_assistant_refs": {
            "content": "已结合知识文档回答。",
            "conversation_id": "assistant_conversation_metrics",
            "created_at": now,
            "id": "assistant_message_assistant_refs",
            "metadata_json": {
                "references": [
                    {"id": "knowledge_payment_runbook", "type": "knowledge_document"},
                    {"id": "knowledge_folder_checkout", "type": "knowledge_folder"},
                ]
            },
            "role": "assistant",
            "suggestions": [],
            "updated_at": now,
            "user_id": "user_admin",
        },
    }
    app.state.store.assistant_chat_runs = {
        "assistant_chat_run_succeeded_metrics": {
            "created_at": now,
            "finished_at": "2026-06-16T10:00:02+00:00",
            "id": "assistant_chat_run_succeeded_metrics",
            "started_at": now,
            "status": "succeeded",
            "updated_at": "2026-06-16T10:00:02+00:00",
            "user_id": "user_admin",
        },
        "assistant_chat_run_cancelled_metrics": {
            "cancel_reason": "user_cancelled",
            "cancelled_at": "2026-06-16T10:00:01+00:00",
            "created_at": now,
            "finished_at": "2026-06-16T10:00:01+00:00",
            "id": "assistant_chat_run_cancelled_metrics",
            "started_at": now,
            "status": "cancelled",
            "updated_at": "2026-06-16T10:00:01+00:00",
            "user_id": "user_admin",
        },
        "assistant_chat_run_failed_metrics": {
            "created_at": now,
            "error_code": "ASSISTANT_CHAT_FAILED",
            "error_message": "Assistant model gateway request failed",
            "finished_at": "2026-06-16T10:00:04+00:00",
            "id": "assistant_chat_run_failed_metrics",
            "started_at": now,
            "status": "failed",
            "updated_at": "2026-06-16T10:00:04+00:00",
            "user_id": "user_admin",
        },
        "assistant_chat_run_running_metrics": {
            "created_at": now,
            "id": "assistant_chat_run_running_metrics",
            "started_at": now,
            "status": "running",
            "updated_at": now,
            "user_id": "user_admin",
        },
        "assistant_chat_run_other_user_metrics": {
            "created_at": now,
            "finished_at": "2026-06-16T10:00:05+00:00",
            "id": "assistant_chat_run_other_user_metrics",
            "started_at": now,
            "status": "failed",
            "updated_at": "2026-06-16T10:00:05+00:00",
            "user_id": "user_reviewer",
        },
    }

    response = client.get("/api/assistant/metrics", headers=headers)

    assert response.status_code == 200
    metrics = response.json()["data"]
    assert metrics["window"] == {"days": None, "label": "全部时间"}
    assert metrics["summary"] == {
        "action_run_failed_count": 0,
        "action_run_succeeded_count": 1,
        "action_run_success_rate": 1.0,
        "action_run_total": 1,
        "chat_run_average_duration_ms": 2333,
        "chat_run_cancel_rate": 0.25,
        "chat_run_cancelled_count": 1,
        "chat_run_failed_count": 1,
        "chat_run_failure_rate": 0.25,
        "chat_run_model_failed_count": 1,
        "chat_run_model_failure_rate": 0.25,
        "chat_run_running_count": 1,
        "chat_run_succeeded_count": 1,
        "chat_run_success_rate": 0.25,
        "chat_run_total": 4,
        "draft_adoption_rate": 0.25,
        "draft_cancelled_count": 1,
        "draft_confirmed_count": 1,
        "draft_expired_count": 1,
        "draft_failed_count": 0,
        "draft_inferred_viewed_count": 1,
        "draft_pending_count": 1,
        "draft_resolution_rate": 0.75,
        "draft_total": 4,
        "draft_deeplink_viewed_count": 1,
        "draft_detail_viewed_count": 1,
        "draft_tracked_viewed_count": 1,
        "draft_user_modified_count": 1,
        "draft_user_modified_rate": 0.25,
        "draft_viewed_count": 2,
        "failed_run_repair_rate": 1.0,
        "failed_run_repaired_count": 1,
        "failed_run_total": 1,
        "knowledge_reference_count": 5,
        "knowledge_reference_hit_count": 2,
        "knowledge_reference_hit_rate": 0.667,
        "knowledge_reference_request_count": 3,
        "message_total": 3,
        "reference_total": 6,
        "reference_usage_rate": 0.5,
        "referenced_user_message_count": 1,
        "scheduled_job_run_failed_count": 1,
        "scheduled_job_run_succeeded_count": 1,
        "scheduled_job_run_success_rate": 0.5,
        "scheduled_job_run_total": 2,
        "user_message_total": 2,
    }
    assert metrics["drafts_by_action"] == [
        {
            "action": "create_plugin_action",
            "cancelled_count": 1,
            "confirmed_count": 0,
            "expired_count": 0,
            "failed_count": 0,
            "pending_count": 0,
            "total": 1,
        },
        {
            "action": "create_scheduled_job",
            "cancelled_count": 0,
            "confirmed_count": 1,
            "expired_count": 1,
            "failed_count": 0,
            "pending_count": 1,
            "total": 3,
        },
    ]
    assert metrics["scheduled_job_run_attribution"] == {
        "items": [
            {"count": 1, "key": "assistant_triggered", "label": "助手触发"},
            {"count": 0, "key": "explicit_reference", "label": "显式引用"},
            {"count": 1, "key": "rerun_chain", "label": "复跑链"},
        ],
        "total": 2,
    }
    assert metrics["funnel"] == {
        "stages": [
            {
                "count": 2,
                "key": "intent_triggered",
                "label": "触发意图",
                "sort_order": 10,
            },
            {
                "count": 4,
                "key": "draft_generated",
                "label": "生成草案",
                "sort_order": 20,
            },
            {
                "count": 2,
                "key": "draft_viewed",
                "label": "查看草案",
                "sort_order": 30,
            },
            {
                "count": 1,
                "key": "draft_detail_viewed",
                "label": "查看详情",
                "sort_order": 31,
            },
            {
                "count": 1,
                "key": "draft_deeplink_viewed",
                "label": "深链打开",
                "sort_order": 32,
            },
            {
                "count": 1,
                "key": "draft_modified",
                "label": "修改字段",
                "sort_order": 40,
            },
            {
                "count": 1,
                "key": "draft_confirmed",
                "label": "确认草案",
                "sort_order": 50,
            },
            {
                "count": 1,
                "key": "run_succeeded",
                "label": "运行成功",
                "sort_order": 60,
            },
            {
                "count": 0,
                "key": "continued_followup_or_repair",
                "label": "继续追问/修复",
                "sort_order": 70,
            },
        ]
    }
    assert metrics["instrumentation"]["view_metrics"] == {
        "effective_viewed_count": 2,
        "inferred_legacy_count": 1,
        "tracked_count": 1,
    }
    assert metrics["instrumentation"]["notes"][0]["code"] == "DRAFT_VIEW_TRACKING_ROLLOUT"

    windowed_response = client.get("/api/assistant/metrics?window_days=1", headers=headers)

    assert windowed_response.status_code == 200
    windowed_metrics = windowed_response.json()["data"]
    assert windowed_metrics["window"] == {"days": 1, "label": "最近 1 天"}
    assert windowed_metrics["summary"]["draft_total"] == 0
    assert windowed_metrics["summary"]["chat_run_total"] == 0

    draft_details_response = client.get(
        "/api/assistant/metrics/details?metric=draft_total&limit=2",
        headers=headers,
    )
    assert draft_details_response.status_code == 200, draft_details_response.text
    draft_details = draft_details_response.json()["data"]
    assert draft_details["metric"] == "draft_total"
    assert draft_details["title"] == "草案生成"
    assert draft_details["total"] == 4
    assert len(draft_details["items"]) == 2
    assert draft_details["items"][0]["type"] == "draft"
    assert draft_details["items"][0]["url"].startswith("/assistant?draft_id=")

    failed_run_details_response = client.get(
        "/api/assistant/metrics/details?metric=failed_run_repaired_count",
        headers=headers,
    )
    assert failed_run_details_response.status_code == 200, failed_run_details_response.text
    failed_run_details = failed_run_details_response.json()["data"]
    assert failed_run_details["total"] == 1
    assert failed_run_details["items"][0]["id"] == "scheduled_job_run_failed_metrics"
    assert failed_run_details["items"][0]["type"] == "scheduled_job_run"

    windowed_details_response = client.get(
        "/api/assistant/metrics/details?metric=draft_total&window_days=1",
        headers=headers,
    )
    assert windowed_details_response.status_code == 200, windowed_details_response.text
    windowed_details = windowed_details_response.json()["data"]
    assert windowed_details["window"] == {"days": 1, "label": "最近 1 天"}
    assert windowed_details["total"] == 0


def test_ai_assistant_metrics_support_product_role_date_action_filters_and_export():
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.assistant_action_drafts = {
        "assistant_action_draft_product_alpha": {
            "action": "create_scheduled_job",
            "confirmed_at": "2026-06-16T09:30:00+00:00",
            "confirmed_by": "user_admin",
            "created_at": "2026-06-16T09:00:00+00:00",
            "created_by": "user_admin",
            "id": "assistant_action_draft_product_alpha",
            "metadata_json": {"viewed_at": "2026-06-16T09:10:00+00:00"},
            "payload": {"name": "Alpha 周反馈洞察", "product_id": "product_alpha"},
            "product_id": "product_alpha",
            "risk_level": "medium",
            "status": "confirmed",
            "title": "Alpha 周反馈洞察",
            "updated_at": "2026-06-16T09:30:00+00:00",
        },
        "assistant_action_draft_product_beta": {
            "action": "create_plugin_action",
            "created_at": "2026-06-16T10:00:00+00:00",
            "created_by": "user_admin",
            "id": "assistant_action_draft_product_beta",
            "metadata_json": {},
            "payload": {"name": "Beta 动作配置", "product_id": "product_beta"},
            "product_id": "product_beta",
            "risk_level": "low",
            "status": "pending",
            "title": "Beta 动作配置",
            "updated_at": "2026-06-16T10:00:00+00:00",
        },
    }
    app.state.store.assistant_action_runs = {
        "assistant_action_run_product_alpha": {
            "action": "create_scheduled_job",
            "created_at": "2026-06-16T09:35:00+00:00",
            "draft_id": "assistant_action_draft_product_alpha",
            "executed_by": "user_admin",
            "finished_at": "2026-06-16T09:36:00+00:00",
            "id": "assistant_action_run_product_alpha",
            "result": {"id": "scheduled_job_product_alpha"},
            "result_id": "scheduled_job_product_alpha",
            "result_type": "scheduled_job",
            "started_at": "2026-06-16T09:35:00+00:00",
            "status": "succeeded",
            "updated_at": "2026-06-16T09:36:00+00:00",
        },
        "assistant_action_run_product_beta": {
            "action": "create_plugin_action",
            "created_at": "2026-06-16T10:05:00+00:00",
            "draft_id": "assistant_action_draft_product_beta",
            "executed_by": "user_admin",
            "finished_at": "2026-06-16T10:06:00+00:00",
            "id": "assistant_action_run_product_beta",
            "result": {},
            "started_at": "2026-06-16T10:05:00+00:00",
            "status": "failed",
            "updated_at": "2026-06-16T10:06:00+00:00",
        },
    }
    app.state.store.assistant_messages = {
        "assistant_message_product_alpha_user": {
            "content": "@Alpha 周反馈洞察 执行一次",
            "conversation_id": "assistant_conversation_product_alpha",
            "created_at": "2026-06-16T09:20:00+00:00",
            "id": "assistant_message_product_alpha_user",
            "metadata_json": {"references": []},
            "product_id": "product_alpha",
            "role": "user",
            "updated_at": "2026-06-16T09:20:00+00:00",
            "user_id": "user_admin",
        },
        "assistant_message_product_beta_user": {
            "content": "帮我新建插件动作",
            "conversation_id": "assistant_conversation_product_beta",
            "created_at": "2026-06-16T10:10:00+00:00",
            "id": "assistant_message_product_beta_user",
            "metadata_json": {"references": []},
            "product_id": "product_beta",
            "role": "user",
            "updated_at": "2026-06-16T10:10:00+00:00",
            "user_id": "user_admin",
        },
    }
    app.state.store.assistant_chat_runs = {
        "assistant_chat_run_product_alpha": {
            "conversation_id": "assistant_conversation_product_alpha",
            "created_at": "2026-06-16T09:20:00+00:00",
            "finished_at": "2026-06-16T09:20:02+00:00",
            "id": "assistant_chat_run_product_alpha",
            "product_id": "product_alpha",
            "started_at": "2026-06-16T09:20:00+00:00",
            "status": "succeeded",
            "updated_at": "2026-06-16T09:20:02+00:00",
            "user_id": "user_admin",
        },
        "assistant_chat_run_product_beta": {
            "conversation_id": "assistant_conversation_product_beta",
            "created_at": "2026-06-16T10:10:00+00:00",
            "finished_at": "2026-06-16T10:10:02+00:00",
            "id": "assistant_chat_run_product_beta",
            "product_id": "product_beta",
            "started_at": "2026-06-16T10:10:00+00:00",
            "status": "failed",
            "updated_at": "2026-06-16T10:10:02+00:00",
            "user_id": "user_admin",
        },
    }
    app.state.store.scheduled_job_runs = {
        "scheduled_job_run_product_alpha": {
            "assistant_action_draft_id": "assistant_action_draft_product_alpha",
            "assistant_action_run_id": "assistant_action_run_product_alpha",
            "created_at": "2026-06-16T09:37:00+00:00",
            "finished_at": "2026-06-16T09:38:00+00:00",
            "id": "scheduled_job_run_product_alpha",
            "product_id": "product_alpha",
            "scheduled_job_id": "scheduled_job_product_alpha",
            "started_at": "2026-06-16T09:37:00+00:00",
            "status": "succeeded",
            "triggered_by_assistant": True,
            "trigger_type": "manual",
            "updated_at": "2026-06-16T09:38:00+00:00",
        },
        "scheduled_job_run_product_beta": {
            "assistant_action_draft_id": "assistant_action_draft_product_beta",
            "assistant_action_run_id": "assistant_action_run_product_beta",
            "created_at": "2026-06-16T10:07:00+00:00",
            "finished_at": "2026-06-16T10:08:00+00:00",
            "id": "scheduled_job_run_product_beta",
            "product_id": "product_beta",
            "scheduled_job_id": "scheduled_job_product_beta",
            "started_at": "2026-06-16T10:07:00+00:00",
            "status": "failed",
            "triggered_by_assistant": True,
            "trigger_type": "manual",
            "updated_at": "2026-06-16T10:08:00+00:00",
        },
    }

    response = client.get(
        "/api/assistant/metrics"
        "?product_id=product_alpha&action=create_scheduled_job"
        "&date_from=2026-06-16&date_to=2026-06-16&role=admin",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    metrics = response.json()["data"]
    assert metrics["filters"] == {
        "action": "create_scheduled_job",
        "date_from": "2026-06-16",
        "date_to": "2026-06-16",
        "product_id": "product_alpha",
        "role": "admin",
        "window_days": None,
    }
    assert metrics["summary"]["draft_total"] == 1
    assert metrics["summary"]["action_run_total"] == 1
    assert metrics["summary"]["message_total"] == 1
    assert metrics["summary"]["chat_run_total"] == 1
    assert metrics["summary"]["scheduled_job_run_total"] == 1
    assert metrics["dimensions"]["products"] == [
        {
            "chat_run_total": 1,
            "draft_adoption_rate": 1.0,
            "draft_confirmed_count": 1,
            "draft_total": 1,
            "message_total": 1,
            "product_id": "product_alpha",
            "scheduled_job_run_failed_count": 0,
            "scheduled_job_run_succeeded_count": 1,
            "scheduled_job_run_success_rate": 1.0,
            "scheduled_job_run_total": 1,
        }
    ]
    assert metrics["dimensions"]["roles"] == [
        {
            "chat_run_total": 1,
            "draft_total": 1,
            "message_total": 1,
            "role": "admin",
            "scheduled_job_run_total": 1,
        }
    ]
    assert metrics["trends"]["daily"][0]["day"] == "2026-06-16"
    assert metrics["trends"]["daily"][0]["draft_total"] == 1
    assert metrics["trends"]["drafts_by_action_daily"] == [
        {
            "action": "create_scheduled_job",
            "cancelled_count": 0,
            "confirmed_count": 1,
            "day": "2026-06-16",
            "expired_count": 0,
            "failed_count": 0,
            "pending_count": 0,
            "total": 1,
        }
    ]

    details_response = client.get(
        "/api/assistant/metrics/details?metric=draft_total&product_id=product_alpha",
        headers=headers,
    )
    assert details_response.status_code == 200, details_response.text
    assert details_response.json()["data"]["filters"]["product_id"] == "product_alpha"
    assert details_response.json()["data"]["total"] == 1

    export_response = client.get(
        "/api/assistant/metrics/export?format=csv&product_id=product_alpha&action=create_scheduled_job",
        headers=headers,
    )
    assert export_response.status_code == 200, export_response.text
    export_payload = export_response.json()["data"]
    assert export_payload["content_type"] == "text/csv"
    assert export_payload["filename"] == "assistant_metrics.csv"
    assert "dimension_product,product_alpha,draft_total,1" in export_payload["content"]


def test_ai_assistant_metric_details_limits_knowledge_reference_materialization(monkeypatch):
    app.state.store.reset()
    app.state.store.assistant_messages = {
        f"assistant_message_knowledge_{index}": {
            "content": f"引用知识 {index}",
            "conversation_id": "conversation_knowledge_metrics",
            "created_at": f"2026-06-20T08:{index:02d}:00+00:00",
            "id": f"assistant_message_knowledge_{index}",
            "metadata_json": {
                "references": [
                    {
                        "id": f"knowledge_document_{index}",
                        "title": f"知识文档 {index}",
                        "type": "knowledge_document",
                    }
                ]
            },
            "role": "user",
            "updated_at": f"2026-06-20T08:{index:02d}:00+00:00",
            "user_id": "user_admin",
        }
        for index in range(10)
    }
    materialized_knowledge_records: list[str] = []
    original_with_metric_kind = assistant_metrics_service._with_metric_kind

    def counting_with_metric_kind(record: dict, kind: str):
        if kind == "knowledge_reference":
            materialized_knowledge_records.append(str(record.get("id")))
        return original_with_metric_kind(record, kind)

    monkeypatch.setattr(
        assistant_metrics_service,
        "_with_metric_kind",
        counting_with_metric_kind,
    )

    details = assistant_metric_details_response(
        app.state.store,
        limit=3,
        metric="knowledge_reference_count",
        user={"id": "user_admin"},
    )

    assert details["total"] == 10
    assert len(details["items"]) == 3
    assert len(materialized_knowledge_records) == 3
    assert [item["id"] for item in details["items"]] == [
        "assistant_message_knowledge_9:knowledge_document:knowledge_document_9",
        "assistant_message_knowledge_8:knowledge_document:knowledge_document_8",
        "assistant_message_knowledge_7:knowledge_document:knowledge_document_7",
    ]


def test_ai_assistant_action_draft_view_updates_metrics_and_audit():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "查看详情统计草案",
                "schedule_type": "manual",
            },
            "risk_level": "medium",
            "title": "查看详情统计草案",
        },
        headers=headers,
    )
    assert draft_response.status_code == 200, draft_response.text
    draft_id = draft_response.json()["data"]["id"]

    view_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/view",
        json={"surface": "detail_modal"},
        headers=headers,
    )

    assert view_response.status_code == 200, view_response.text
    draft = view_response.json()["data"]
    metadata = draft["metadata_json"]
    assert metadata["viewed_by"] == "user_admin"
    assert metadata["view_count"] == 1
    assert metadata["viewed_at"]
    assert metadata["detail_viewed_at"] == metadata["viewed_at"]
    assert "deeplink_viewed_at" not in metadata
    assert metadata["last_viewed_at"] == metadata["viewed_at"]
    assert metadata["last_view_surface"] == "detail_modal"

    metrics = client.get("/api/assistant/metrics", headers=headers).json()["data"]
    assert metrics["summary"]["draft_detail_viewed_count"] == 1
    assert metrics["summary"]["draft_deeplink_viewed_count"] == 0
    stages = {stage["key"]: stage["count"] for stage in metrics["funnel"]["stages"]}
    assert stages["draft_viewed"] == 1
    assert stages["draft_detail_viewed"] == 1
    assert stages["draft_deeplink_viewed"] == 0

    audit_events = client.get(
        "/api/audit/events?subject_type=assistant_action_draft",
        headers=headers,
    ).json()["data"]["items"]
    viewed_event = next(
        item
        for item in audit_events
        if item["event_type"] == "assistant_action_draft.viewed"
    )
    assert viewed_event["subject_id"] == draft_id
    assert viewed_event["payload"] == {
        "surface": "detail_modal",
        "view_count": 1,
    }


def test_ai_assistant_action_draft_deeplink_view_is_tracked_separately():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "深链统计草案",
                "schedule_type": "manual",
            },
            "risk_level": "medium",
            "title": "深链统计草案",
        },
        headers=headers,
    )
    assert draft_response.status_code == 200, draft_response.text
    draft_id = draft_response.json()["data"]["id"]

    view_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/view",
        json={"surface": "deeplink"},
        headers=headers,
    )

    assert view_response.status_code == 200, view_response.text
    metadata = view_response.json()["data"]["metadata_json"]
    assert metadata["deeplink_viewed_at"] == metadata["viewed_at"]
    assert "detail_viewed_at" not in metadata
    assert metadata["last_view_surface"] == "deeplink"

    metrics = client.get("/api/assistant/metrics", headers=headers).json()["data"]
    assert metrics["summary"]["draft_viewed_count"] == 1
    assert metrics["summary"]["draft_detail_viewed_count"] == 0
    assert metrics["summary"]["draft_deeplink_viewed_count"] == 1


def test_ai_assistant_metrics_only_count_runs_attributed_to_assistant_action():
    now = "2026-06-16T10:00:00+00:00"

    class RepositoryBackedMetricsStore:
        def list_assistant_action_drafts(self, *, user_id: str):
            assert user_id == "user_admin"
            return [
                {
                    "action": "create_scheduled_job",
                    "confirmed_at": now,
                    "confirmed_by": "user_admin",
                    "created_at": now,
                    "created_by": "user_admin",
                    "id": "assistant_action_draft_attributed",
                    "metadata_json": {},
                    "payload": {"name": "助手创建作业"},
                    "result_run_id": "assistant_action_run_attributed",
                    "risk_level": "medium",
                    "status": "confirmed",
                    "title": "助手创建作业",
                    "updated_at": now,
                }
            ]

        def load_assistant_chat(self):
            return {
                "assistant_action_runs": {
                    "assistant_action_run_attributed": {
                        "action": "create_scheduled_job",
                        "created_at": now,
                        "draft_id": "assistant_action_draft_attributed",
                        "executed_by": "user_admin",
                        "finished_at": now,
                        "id": "assistant_action_run_attributed",
                        "result": {"id": "scheduled_job_attributed"},
                        "result_id": "scheduled_job_attributed",
                        "result_type": "scheduled_job",
                        "started_at": now,
                        "status": "succeeded",
                        "updated_at": now,
                    }
                },
                "assistant_messages": {},
            }

        def list_scheduled_job_runs(
            self,
            *,
            scheduled_job_id: str | None = None,
            status: str | None = None,
        ):
            runs = [
                {
                    "assistant_action_run_id": "assistant_action_run_attributed",
                    "created_at": now,
                    "error_code": None,
                    "error_message": None,
                    "finished_at": now,
                    "id": "scheduled_job_run_assistant",
                    "records_imported": 5,
                    "result_summary": {},
                    "scheduled_job_id": "scheduled_job_attributed",
                    "source_run_id": None,
                    "started_at": now,
                    "status": "succeeded",
                    "trigger_type": "manual",
                    "triggered_by_assistant": True,
                    "updated_at": now,
                },
                {
                    "assistant_action_run_id": None,
                    "created_at": now,
                    "error_code": "SCHEDULED_FAILURE",
                    "error_message": "后续普通调度失败",
                    "finished_at": now,
                    "id": "scheduled_job_run_unattributed",
                    "records_imported": 0,
                    "result_summary": {},
                    "scheduled_job_id": "scheduled_job_attributed",
                    "source_run_id": None,
                    "started_at": now,
                    "status": "failed",
                    "trigger_type": "scheduled",
                    "triggered_by_assistant": False,
                    "updated_at": now,
                },
            ]
            if scheduled_job_id is not None:
                runs = [run for run in runs if run["scheduled_job_id"] == scheduled_job_id]
            if status is not None:
                runs = [run for run in runs if run["status"] == status]
            return runs

    metrics = assistant_metrics_response(
        SimpleNamespace(repository=RepositoryBackedMetricsStore(), scheduled_job_runs={}),
        user={"id": "user_admin"},
    )

    assert metrics["summary"]["scheduled_job_run_total"] == 1
    assert metrics["summary"]["scheduled_job_run_succeeded_count"] == 1
    assert metrics["summary"]["scheduled_job_run_failed_count"] == 0
    assert metrics["scheduled_job_run_attribution"] == {
        "items": [
            {"count": 1, "key": "assistant_triggered", "label": "助手触发"},
            {"count": 0, "key": "explicit_reference", "label": "显式引用"},
            {"count": 0, "key": "rerun_chain", "label": "复跑链"},
        ],
        "total": 1,
    }
    stages = {stage["key"]: stage["count"] for stage in metrics["funnel"]["stages"]}
    assert stages["run_succeeded"] == 1


def test_ai_assistant_metrics_explain_explicit_run_reference_attribution():
    now = "2026-06-16T10:00:00+00:00"
    app.state.store.reset()
    app.state.store.assistant_messages = {
        "assistant_message_user_run_ref": {
            "content": "@失败运行 为什么失败？",
            "conversation_id": "assistant_conversation_run_ref",
            "created_at": now,
            "id": "assistant_message_user_run_ref",
            "metadata_json": {
                "references": [
                    {"id": "scheduled_job_run_explicit_ref", "type": "scheduled_job_run"}
                ]
            },
            "role": "user",
            "suggestions": [],
            "updated_at": now,
            "user_id": "user_admin",
        }
    }
    app.state.store.scheduled_job_runs = {
        "scheduled_job_run_explicit_ref": {
            "created_at": now,
            "error_code": "FAILED",
            "error_message": "显式引用失败运行",
            "finished_at": now,
            "id": "scheduled_job_run_explicit_ref",
            "records_imported": 0,
            "result_summary": {},
            "scheduled_job_id": "scheduled_job_ref",
            "source_run_id": None,
            "started_at": now,
            "status": "failed",
            "trigger_type": "manual",
            "updated_at": now,
        }
    }

    metrics = assistant_metrics_response(app.state.store, user={"id": "user_admin"})

    assert metrics["summary"]["scheduled_job_run_total"] == 1
    assert metrics["scheduled_job_run_attribution"] == {
        "items": [
            {"count": 0, "key": "assistant_triggered", "label": "助手触发"},
            {"count": 1, "key": "explicit_reference", "label": "显式引用"},
            {"count": 0, "key": "rerun_chain", "label": "复跑链"},
        ],
        "total": 1,
    }


def test_ai_assistant_metrics_reads_scheduled_job_runs_from_repository_read_model():
    now = "2026-06-16T10:00:00+00:00"

    class RepositoryBackedMetricsStore:
        def list_assistant_action_drafts(self, *, user_id: str):
            assert user_id == "user_admin"
            return [
                {
                    "action": "create_scheduled_job",
                    "confirmed_at": now,
                    "confirmed_by": "user_admin",
                    "created_at": now,
                    "created_by": "user_admin",
                    "id": "assistant_action_draft_db",
                    "metadata_json": {},
                    "payload": {"name": "DB-first 作业草案"},
                    "result_run_id": "assistant_action_run_db",
                    "risk_level": "medium",
                    "status": "confirmed",
                    "title": "DB-first 作业草案",
                    "updated_at": now,
                }
            ]

        def load_assistant_chat(self):
            return {
                "assistant_action_runs": {
                    "assistant_action_run_db": {
                        "action": "create_scheduled_job",
                        "created_at": now,
                        "draft_id": "assistant_action_draft_db",
                        "executed_by": "user_admin",
                        "finished_at": now,
                        "id": "assistant_action_run_db",
                        "result": {"id": "scheduled_job_db"},
                        "result_id": "scheduled_job_db",
                        "result_type": "scheduled_job",
                        "started_at": now,
                        "status": "succeeded",
                        "updated_at": now,
                    }
                },
                "assistant_messages": {},
            }

        def list_scheduled_job_runs(
            self,
            *,
            scheduled_job_id: str | None = None,
            status: str | None = None,
        ):
            runs = [
                {
                    "created_at": now,
                    "error_code": "RESULT_ACTION_FAILED",
                    "error_message": "结果写入失败",
                    "finished_at": now,
                    "id": "scheduled_job_run_db_failed",
                    "records_imported": 0,
                    "result_summary": {},
                    "scheduled_job_id": "scheduled_job_db",
                    "source_run_id": None,
                    "started_at": now,
                    "status": "failed",
                    "trigger_type": "manual",
                    "updated_at": now,
                },
                {
                    "assistant_action_draft_id": "assistant_action_draft_db",
                    "assistant_action_run_id": "assistant_action_run_db",
                    "created_at": now,
                    "error_code": None,
                    "error_message": None,
                    "finished_at": now,
                    "id": "scheduled_job_run_db_repaired",
                    "records_imported": 8,
                    "result_summary": {},
                    "scheduled_job_id": "scheduled_job_db",
                    "source_run_id": "scheduled_job_run_db_failed",
                    "started_at": now,
                    "status": "succeeded",
                    "triggered_by_assistant": True,
                    "trigger_type": "manual_rerun",
                    "updated_at": now,
                },
            ]
            if scheduled_job_id is not None:
                runs = [run for run in runs if run["scheduled_job_id"] == scheduled_job_id]
            if status is not None:
                runs = [run for run in runs if run["status"] == status]
            return runs

    metrics = assistant_metrics_response(
        SimpleNamespace(repository=RepositoryBackedMetricsStore(), scheduled_job_runs={}),
        user={"id": "user_admin"},
    )

    assert metrics["summary"]["scheduled_job_run_total"] == 2
    assert metrics["summary"]["scheduled_job_run_failed_count"] == 1
    assert metrics["summary"]["scheduled_job_run_succeeded_count"] == 1
    assert metrics["summary"]["scheduled_job_run_success_rate"] == 0.5
    assert metrics["summary"]["failed_run_repaired_count"] == 1
    assert metrics["summary"]["failed_run_repair_rate"] == 1.0
    assert metrics["scheduled_job_run_attribution"] == {
        "items": [
            {"count": 1, "key": "assistant_triggered", "label": "助手触发"},
            {"count": 0, "key": "explicit_reference", "label": "显式引用"},
            {"count": 1, "key": "rerun_chain", "label": "复跑链"},
        ],
        "total": 2,
    }
    details = assistant_metric_details_response(
        SimpleNamespace(repository=RepositoryBackedMetricsStore(), scheduled_job_runs={}),
        metric="scheduled_job_run_failed_count",
        user={"id": "user_admin"},
    )
    assert details["total"] == 1
    assert details["items"][0]["id"] == "scheduled_job_run_db_failed"
    assert details["items"][0]["url"] == (
        "/tasks/scheduled-jobs?job_id=scheduled_job_db&run_id=scheduled_job_run_db_failed"
    )


def test_ai_assistant_metrics_uses_repository_scoped_scheduled_job_runs_query():
    now = datetime.now(UTC).isoformat()

    class RepositoryBackedMetricsStore:
        def __init__(self):
            self.scoped_calls: list[dict[str, object]] = []

        def list_assistant_action_drafts(self, *, user_id: str):
            assert user_id == "user_admin"
            return [
                {
                    "action": "create_scheduled_job",
                    "confirmed_at": now,
                    "confirmed_by": "user_admin",
                    "created_at": now,
                    "created_by": "user_admin",
                    "id": "assistant_action_draft_scoped",
                    "metadata_json": {},
                    "payload": {"name": "Scoped 作业草案"},
                    "result_run_id": "assistant_action_run_scoped",
                    "risk_level": "medium",
                    "status": "confirmed",
                    "title": "Scoped 作业草案",
                    "updated_at": now,
                }
            ]

        def load_assistant_chat(self):
            return {
                "assistant_action_runs": {
                    "assistant_action_run_scoped": {
                        "action": "create_scheduled_job",
                        "created_at": now,
                        "draft_id": "assistant_action_draft_scoped",
                        "executed_by": "user_admin",
                        "finished_at": now,
                        "id": "assistant_action_run_scoped",
                        "result": {"id": "scheduled_job_scoped"},
                        "result_id": "scheduled_job_scoped",
                        "result_type": "scheduled_job",
                        "started_at": now,
                        "status": "succeeded",
                        "updated_at": now,
                    }
                },
                "assistant_messages": {
                    "assistant_message_run_ref": {
                        "conversation_id": "assistant_conversation_scoped",
                        "created_at": now,
                        "id": "assistant_message_run_ref",
                        "metadata_json": {
                            "references": [
                                {
                                    "id": "scheduled_job_run_scoped_failed",
                                    "type": "scheduled_job_run",
                                }
                            ]
                        },
                        "role": "user",
                        "updated_at": now,
                        "user_id": "user_admin",
                    }
                },
            }

        def list_scheduled_job_runs(self, **_kwargs):
            raise AssertionError("assistant metrics should use scoped repository query")

        def list_assistant_scoped_scheduled_job_runs(
            self,
            *,
            action_draft_ids: list[str],
            action_run_ids: list[str],
            message_ids: list[str],
            referenced_run_ids: list[str],
            since: str | None = None,
        ):
            self.scoped_calls.append(
                {
                    "action_draft_ids": action_draft_ids,
                    "action_run_ids": action_run_ids,
                    "message_ids": message_ids,
                    "referenced_run_ids": referenced_run_ids,
                    "since": since,
                }
            )
            return [
                {
                    "assistant_action_draft_id": None,
                    "assistant_action_run_id": None,
                    "created_at": now,
                    "error_code": "FAILED",
                    "error_message": "首跑失败",
                    "finished_at": now,
                    "id": "scheduled_job_run_scoped_failed",
                    "records_imported": 0,
                    "result_summary": {},
                    "scheduled_job_id": "scheduled_job_scoped",
                    "source_run_id": None,
                    "started_at": now,
                    "status": "failed",
                    "triggered_by_assistant": False,
                    "trigger_type": "manual",
                    "updated_at": now,
                },
                {
                    "assistant_action_draft_id": "assistant_action_draft_scoped",
                    "assistant_action_run_id": "assistant_action_run_scoped",
                    "created_at": now,
                    "error_code": None,
                    "error_message": None,
                    "finished_at": now,
                    "id": "scheduled_job_run_scoped_repaired",
                    "records_imported": 8,
                    "result_summary": {},
                    "scheduled_job_id": "scheduled_job_scoped",
                    "source_run_id": "scheduled_job_run_scoped_failed",
                    "started_at": now,
                    "status": "succeeded",
                    "triggered_by_assistant": True,
                    "trigger_type": "manual_rerun",
                    "updated_at": now,
                },
            ]

    repository = RepositoryBackedMetricsStore()
    metrics = assistant_metrics_response(
        SimpleNamespace(repository=repository, scheduled_job_runs={}),
        user={"id": "user_admin"},
        window_days=30,
    )

    assert len(repository.scoped_calls) == 1
    call = repository.scoped_calls[0]
    assert call["action_draft_ids"] == ["assistant_action_draft_scoped"]
    assert call["action_run_ids"] == ["assistant_action_run_scoped"]
    assert call["message_ids"] == ["assistant_message_run_ref"]
    assert call["referenced_run_ids"] == ["scheduled_job_run_scoped_failed"]
    assert call["since"]
    assert metrics["summary"]["scheduled_job_run_total"] == 2
    assert metrics["summary"]["failed_run_repaired_count"] == 1
    assert metrics["scheduled_job_run_attribution"]["total"] == 2


def test_ai_assistant_action_draft_modification_updates_metrics_and_audit():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": True,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "AI 助手草案仪表盘刷新",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建仪表盘刷新定时任务",
        },
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft_id = draft_response.json()["data"]["id"]

    modification_response = client.post(
        f"/api/assistant/action-drafts/{draft_id}/modification",
        json={
            "modified_fields": [
                "cron_expression",
                "",
                "cron_expression",
                "plugin_action_id",
            ]
        },
        headers=headers,
    )

    assert modification_response.status_code == 200
    draft = modification_response.json()["data"]
    assert draft["metadata_json"]["user_modified"] is True
    assert draft["metadata_json"]["modified_fields"] == [
        "cron_expression",
        "plugin_action_id",
    ]
    assert draft["metadata_json"]["modified_by"] == "user_admin"

    metrics = client.get("/api/assistant/metrics", headers=headers).json()["data"]
    assert metrics["summary"]["draft_total"] == 1
    assert metrics["summary"]["draft_user_modified_count"] == 1
    assert metrics["summary"]["draft_user_modified_rate"] == 1.0

    audit_events = client.get(
        "/api/audit/events?subject_type=assistant_action_draft",
        headers=headers,
    ).json()["data"]["items"]
    modified_event = next(
        item
        for item in audit_events
        if item["event_type"] == "assistant_action_draft.modified"
    )
    assert modified_event["subject_id"] == draft_id
    assert modified_event["payload"] == {
        "modified_field_count": 2,
        "modified_fields": ["cron_expression", "plugin_action_id"],
    }


def test_ai_assistant_action_draft_previews_diff_and_blocks_invalid_confirmation():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "execution_mode": "deterministic",
                "job_type": "user_feedback_insight_extract",
                "name": "缺少配置的反馈洞察作业",
                "schedule_type": "cron",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建反馈洞察定时任务",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    preview = draft["preview"]
    assert preview["target"] == {
        "operation": "create",
        "resource_id": None,
        "resource_type": "scheduled_job",
    }
    diff_by_field = {item["field"]: item for item in preview["diffs"]}
    assert diff_by_field["name"]["proposed"] == "缺少配置的反馈洞察作业"
    assert diff_by_field["schedule_type"]["proposed"] == "cron"
    validation = preview["validation"]
    assert validation["status"] == "blocked"
    issues_by_field = {item["field"]: item for item in validation["issues"]}
    assert issues_by_field["cron_expression"]["severity"] == "error"
    assert issues_by_field["plugin_action_id"]["severity"] == "error"
    assert issues_by_field["cron_expression"]["repair_action"] == {
        "action": "edit_field",
        "field": "cron_expression",
        "label": "修正 Cron 表达式",
    }
    assert issues_by_field["plugin_action_id"]["repair_action"] == {
        "action": "generate_plugin_action_draft",
        "field": "plugin_action_id",
        "label": "生成结果动作草案",
    }

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_PRECHECK_FAILED"


def test_ai_assistant_scheduled_job_draft_precheck_blocks_invalid_cron_expression():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "cron_expression": "61 8 * * MON",
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "非法 Cron 的看板刷新作业",
                "schedule_type": "cron",
            },
            "risk_level": "medium",
            "title": "创建非法 Cron 定时任务",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    validation = draft["preview"]["validation"]
    assert validation["status"] == "blocked"
    issues_by_field = {item["field"]: item for item in validation["issues"]}
    assert issues_by_field["cron_expression"]["severity"] == "error"
    assert "Invalid cron_expression" in issues_by_field["cron_expression"]["message"]
    assert issues_by_field["cron_expression"]["repair_action"] == {
        "action": "edit_field",
        "field": "cron_expression",
        "label": "修正 Cron 表达式",
    }

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_PRECHECK_FAILED"


def test_ai_assistant_scheduled_job_draft_precheck_blocks_missing_manage_permission():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "评审角色创建的看板刷新作业",
                "schedule_type": "manual",
            },
            "risk_level": "medium",
            "title": "创建看板刷新定时任务",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    validation = draft["preview"]["validation"]
    assert validation["status"] == "blocked"
    issues_by_field = {item["field"]: item for item in validation["issues"]}
    assert issues_by_field["permission"]["severity"] == "error"
    assert "system.scheduled_jobs.manage" in issues_by_field["permission"]["message"]

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_PRECHECK_FAILED"


def test_ai_assistant_action_draft_precheck_blocks_failed_plugin_connection():
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    connection = app.state.store.plugin_connections["plugin_connection_maxcompute"]
    connection["last_test_summary"] = {
        "checked_at": "2026-06-17T09:20:00+00:00",
        "error_code": "HTTP_ERROR",
        "error_message": "HTTP 403: forbidden",
        "status": "failed",
    }

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_plugin_action",
            "payload": {
                "action_type": "http_request",
                "code": "feedback_write_retry",
                "connection_id": "plugin_connection_maxcompute",
                "name": "反馈洞察写入动作",
                "plugin_id": "plugin_http",
            },
            "risk_level": "medium",
            "title": "创建反馈洞察写入动作",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    validation = draft["preview"]["validation"]
    assert validation["status"] == "blocked"
    issues_by_field = {item["field"]: item for item in validation["issues"]}
    assert issues_by_field["connection_id"]["severity"] == "error"
    assert "last test failed" in issues_by_field["connection_id"]["message"]
    assert "HTTP 403: forbidden" in issues_by_field["connection_id"]["message"]
    assert issues_by_field["connection_id"]["repair_action"] == {
        "action": "open_plugin_connection_test",
        "field": "connection_id",
        "label": "打开连接测试",
        "resource_id": "plugin_connection_maxcompute",
        "resource_type": "plugin_connection",
    }

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_PRECHECK_FAILED"


def test_ai_assistant_scheduled_job_draft_precheck_blocks_failed_plugin_connection():
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    connection = app.state.store.plugin_connections["plugin_connection_maxcompute"]
    connection["last_test_summary"] = {
        "checked_at": "2026-06-17T09:20:00+00:00",
        "error_code": "HTTP_ERROR",
        "error_message": "HTTP 403: forbidden",
        "status": "failed",
    }

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "execution_mode": "deterministic",
                "job_type": "plugin_action_invoke",
                "name": "使用失败连接的定时任务",
                "plugin_action_id": "plugin_action_feedback_write",
                "plugin_connection_id": "plugin_connection_maxcompute",
                "schedule_type": "manual",
            },
            "risk_level": "medium",
            "title": "创建使用失败连接的定时任务",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    validation = draft["preview"]["validation"]
    assert validation["status"] == "blocked"
    issues_by_field = {item["field"]: item for item in validation["issues"]}
    assert issues_by_field["plugin_connection_id"]["severity"] == "error"
    assert "last test failed" in issues_by_field["plugin_connection_id"]["message"]
    assert "HTTP 403: forbidden" in issues_by_field["plugin_connection_id"]["message"]


def test_ai_assistant_action_draft_cancel_prevents_confirmation():
    headers = auth_headers()
    app.state.store.reset()

    draft = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "待取消定时任务",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "title": "取消用草案",
        },
        headers=headers,
    ).json()["data"]

    cancel_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/cancel",
        json={"reason": "用户决定暂不创建"},
        headers=headers,
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "cancelled"
    assert cancel_response.json()["data"]["cancel_reason"] == "用户决定暂不创建"

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_NOT_PENDING"


def test_ai_assistant_action_draft_expires_before_confirmation():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "metadata_json": {"expires_at": "2020-01-01T00:00:00+00:00"},
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "已过期定时任务草案",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "title": "已过期草案",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["status"] == "expired"
    assert draft["expires_at"] == "2020-01-01T00:00:00+00:00"

    get_response = client.get(f"/api/assistant/action-drafts/{draft['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["status"] == "expired"

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_EXPIRED"
    assert app.state.store.scheduled_jobs == {}


def test_ai_assistant_chat_persists_action_draft_tool_results(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "我已准备好定时任务草案，确认后再创建。",
                                        "suggestions": ["查看草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我配置每周用户反馈洞察定时任务草案"},
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    draft_item = message["tool_results"][0]["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_weekly_feedback_insight"
    assert draft_item["draft_id"].startswith("assistant_action_draft_")
    assert draft_item["server_draft_id"] == draft_item["draft_id"]
    assert draft_item["status"] == "pending"

    draft_response = client.get(
        f"/api/assistant/action-drafts/{draft_item['draft_id']}",
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["source_message_id"] == message["id"]
    assert draft["client_draft_id"] == "assistant_draft_weekly_feedback_insight"
    assert draft["action"] == "create_scheduled_job"


def test_ai_assistant_chat_generates_email_digest_job_draft(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.integration_plugins["plugin_standard_email"] = {
        "category": "collaboration",
        "code": "email",
        "id": "plugin_standard_email",
        "is_system": True,
        "name": "邮箱",
        "protocol": "http",
        "risk_level": "medium",
        "status": "active",
    }
    app.state.store.plugin_connections["plugin_connection_email_prod"] = {
        "auth_config": {"secret_ref": "vault/email/api_key"},
        "auth_type": "api_key_header",
        "created_at": "2026-06-17T08:00:00+00:00",
        "created_by": "user_admin",
        "endpoint_url": "https://mail-gateway.example.com/api",
        "environment": "prod",
        "id": "plugin_connection_email_prod",
        "name": "生产邮箱连接",
        "plugin_id": "plugin_standard_email",
        "request_config": {"query": {"mailbox_folder": "INBOX"}},
        "status": "active",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.plugin_actions["plugin_action_receive_email_messages"] = {
        "action_type": "http_request",
        "code": "receive_email_messages",
        "connection_id": "plugin_connection_email_prod",
        "created_at": "2026-06-17T08:00:00+00:00",
        "created_by": "user_admin",
        "id": "plugin_action_receive_email_messages",
        "name": "收取邮箱邮件",
        "plugin_id": "plugin_standard_email",
        "request_config": {
            "method": "GET",
            "path": "/messages/search",
            "query": {"folder": "{{mailbox_folder}}", "since": "{{poll_since}}"},
        },
        "result_mapping": {"write_target": "scheduled_job_result"},
        "status": "active",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            answer = "我已准备好邮件摘要收取定时作业草案，确认后再创建。"
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": answer,
                                        "suggestions": ["查看草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "请帮我生成邮件摘要收取定时作业草案，先检查邮箱连接和邮件收取动作"},
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    tool_result = message["tool_results"][0]
    assert tool_result["tool"] == "assistant.action_draft"
    assert tool_result["intent"] == "email_digest_job_draft"
    draft_item = tool_result["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_email_digest"
    assert draft_item["status"] == "pending"
    assert draft_item["action"] == "create_scheduled_job"
    assert draft_item["title"] == "邮件摘要收取"
    assert draft_item["payload"] == {
        "cron_expression": "0 8 * * MON-FRI",
        "enabled": True,
        "execution_mode": "deterministic",
        "job_type": "plugin_action_invoke",
        "name": "每日邮件摘要收取",
        "plugin_action_id": "plugin_action_receive_email_messages",
        "plugin_connection_id": "plugin_connection_email_prod",
        "plugin_input_mapping": {"poll_since": "{{current_date-1}}"},
        "schedule_type": "cron",
        "source_system": "email",
    }
    assert draft_item["wizard_steps"] == [
        {
            "depends_on": [],
            "key": "data_source",
            "status": "ready",
            "summary": "已选择 收取邮箱邮件",
            "title": "数据来源",
        },
        {
            "depends_on": [],
            "key": "ai_processing",
            "status": "skipped",
            "summary": "不调用 AI",
            "title": "AI处理",
        },
        {
            "depends_on": [],
            "key": "result_action",
            "status": "ready",
            "summary": "记录运行结果",
            "title": "结果动作",
        },
        {
            "depends_on": [],
            "key": "schedule",
            "status": "ready",
            "summary": "cron: 0 8 * * MON-FRI",
            "title": "调度策略",
        },
        {
            "depends_on": [],
            "key": "confirm",
            "status": "pending",
            "summary": "确认后创建定时作业",
            "title": "确认执行",
        },
    ]
    draft_response = client.get(
        f"/api/assistant/action-drafts/{draft_item['draft_id']}",
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["client_draft_id"] == "assistant_draft_email_digest"
    assert draft["wizard_steps"] == draft_item["wizard_steps"]


def test_ai_assistant_email_digest_draft_generates_missing_prerequisites(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.integration_plugins["plugin_standard_email"] = {
        "category": "collaboration",
        "code": "email",
        "id": "plugin_standard_email",
        "is_system": True,
        "name": "邮箱",
        "protocol": "http",
        "risk_level": "medium",
        "status": "active",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "我已生成邮件摘要配置草案链。",
                                        "suggestions": ["先确认邮箱连接", "再确认邮件收取动作"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    monkeypatch.setattr(assistant_router, "urlopen", lambda _request, timeout: FakeResponse())

    response = client.post(
        "/api/assistant/chat",
        json={"message": "请帮我生成邮件摘要收取定时作业草案，先检查邮箱连接和邮件收取动作"},
        headers=headers,
    )

    assert response.status_code == 200
    tool_result = response.json()["data"]["message"]["tool_results"][0]
    assert tool_result["tool"] == "assistant.action_draft"
    assert tool_result["intent"] == "email_digest_setup_draft"
    assert tool_result["summary"]["draft_count"] == 3
    connection_item, action_item, job_item = tool_result["items"]
    assert connection_item["action"] == "create_plugin_connection"
    assert connection_item["client_draft_id"] == "assistant_draft_email_plugin_connection"
    assert action_item["action"] == "create_plugin_action"
    assert action_item["title"] == "邮件收取动作"
    assert action_item["payload"]["code"] == "receive_email_messages"
    assert action_item["payload"]["assistant_prerequisite_draft_ids"] == [
        "assistant_draft_email_plugin_connection"
    ]
    assert job_item["action"] == "create_scheduled_job"
    assert job_item["client_draft_id"] == "assistant_draft_email_digest"
    assert job_item["payload"]["plugin_action_id"] is None
    assert job_item["payload"]["plugin_connection_id"] is None
    assert job_item["payload"]["assistant_prerequisite_draft_ids"] == [
        "assistant_draft_email_plugin_connection",
        "assistant_draft_email_receive_action",
    ]
    assert job_item["wizard_steps"][0] == {
        "depends_on": [
            "assistant_draft_email_plugin_connection",
            "assistant_draft_email_receive_action",
        ],
        "key": "data_source",
        "status": "needs_prerequisite",
        "summary": "需先确认邮箱连接和邮件收取动作",
        "title": "数据来源",
    }
    assert job_item["wizard_steps"][-1]["depends_on"] == [
        "assistant_draft_email_plugin_connection",
        "assistant_draft_email_receive_action",
    ]
    assert job_item["wizard_steps"][-1]["summary"] == "确认前置草案后创建定时作业"


def test_ai_assistant_chat_generates_online_log_anomaly_job_draft(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.products["product_online_ops"] = {
        "code": "online_ops",
        "created_at": "2026-06-17T08:00:00+00:00",
        "id": "product_online_ops",
        "name": "线上运营系统",
        "status": "active",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.model_gateway_configs["model_gateway_online_log"] = {
        "api_key": "sk-online-log-test",
        "base_url": "https://models.example.com/v1",
        "created_at": "2026-06-17T08:00:00+00:00",
        "default_chat_model": "ops-chat",
        "default_embedding_model": "ops-embedding",
        "id": "model_gateway_online_log",
        "is_default": True,
        "model": "ops-chat",
        "name": "运维模型",
        "provider": "openai_compatible",
        "status": "active",
        "timeout_seconds": 60,
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.ai_agents["ai_agent_online_log_ops"] = {
        "brain_app_id": "rd_brain",
        "code": "online_log_ops",
        "created_at": "2026-06-17T08:00:00+00:00",
        "created_by": "user_admin",
        "default_skill_ids": ["ai_skill_online_log_anomaly"],
        "id": "ai_agent_online_log_ops",
        "model_gateway_config_id": "model_gateway_online_log",
        "name": "线上日志运维助手",
        "status": "active",
        "system_prompt": "分析线上日志异常并给出处置建议。",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.ai_skills["ai_skill_online_log_anomaly"] = {
        "code": "online_log_anomaly",
        "created_at": "2026-06-17T08:00:00+00:00",
        "created_by": "user_admin",
        "id": "ai_skill_online_log_anomaly",
        "name": "线上日志异常检测",
        "prompt_template": "识别错误率、延迟和异常模式，输出处置建议。",
        "status": "active",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.integration_plugins["plugin_standard_observability"] = {
        "category": "operations",
        "code": "observability",
        "id": "plugin_standard_observability",
        "is_system": True,
        "name": "可观测平台",
        "protocol": "http",
        "risk_level": "medium",
        "status": "active",
    }
    app.state.store.plugin_connections["plugin_connection_online_log_prod"] = {
        "auth_config": {"secret_ref": "vault/observability/api_key"},
        "auth_type": "api_key_header",
        "created_at": "2026-06-17T08:00:00+00:00",
        "created_by": "user_admin",
        "endpoint_url": "https://logs.example.com/api",
        "environment": "prod",
        "id": "plugin_connection_online_log_prod",
        "name": "生产线上日志连接",
        "plugin_id": "plugin_standard_observability",
        "request_config": {"headers": {"X-App": "ai-brain"}},
        "status": "active",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.plugin_actions["plugin_action_query_online_log_metrics"] = {
        "action_type": "http_request",
        "code": "query_online_log_metrics",
        "connection_id": "plugin_connection_online_log_prod",
        "created_at": "2026-06-17T08:00:00+00:00",
        "created_by": "user_admin",
        "id": "plugin_action_query_online_log_metrics",
        "name": "查询线上日志指标",
        "plugin_id": "plugin_standard_observability",
        "request_config": {
            "method": "GET",
            "path": "/logs/anomaly-metrics",
            "query": {
                "window_end": "{{window_end}}",
                "window_start": "{{window_start}}",
            },
        },
        "result_mapping": {
            "records_imported_path": "$.row_count",
            "source_rows_path": "$.logs",
        },
        "status": "active",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            answer = "我已准备好线上日志异常分析定时作业草案，确认后再创建。"
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": answer,
                                        "suggestions": ["查看草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    monkeypatch.setattr(assistant_router, "urlopen", lambda _request, timeout: FakeResponse())

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": (
                "请生成线上日志异常分析定时作业草案，"
                "说明需要的数据连接、AI处理、结果动作和调度策略"
            )
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    tool_result = message["tool_results"][0]
    assert tool_result["tool"] == "assistant.action_draft"
    assert tool_result["intent"] == "online_log_anomaly_job_draft"
    draft_item = tool_result["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_online_log_anomaly_analysis"
    assert draft_item["status"] == "pending"
    assert draft_item["action"] == "create_scheduled_job"
    assert draft_item["title"] == "线上日志异常分析"
    assert draft_item["payload"] == {
        "agent_id": "ai_agent_online_log_ops",
        "cron_expression": "*/30 * * * *",
        "enabled": True,
        "execution_mode": "ai_generated",
        "job_type": "online_log_ai_analysis",
        "knowledge_document_ids": [],
        "model_gateway_config_id": "model_gateway_online_log",
        "name": "线上日志异常分析",
        "plugin_action_id": "plugin_action_query_online_log_metrics",
        "plugin_connection_id": "plugin_connection_online_log_prod",
        "plugin_input_mapping": {
            "window_end": "{{now}}",
            "window_start": "{{current_date}}",
        },
        "product_id": "product_online_ops",
        "result_actions": [{"channels": ["email"], "recipients": [], "type": "send_notification"}],
        "schedule_type": "cron",
        "skill_ids": ["ai_skill_online_log_anomaly"],
        "source_system": "online-log",
    }
    assert draft_item["wizard_steps"] == [
        {
            "depends_on": [],
            "key": "data_source",
            "status": "ready",
            "summary": "已选择 查询线上日志指标",
            "title": "数据来源",
        },
        {
            "depends_on": [],
            "key": "ai_processing",
            "status": "ready",
            "summary": "已选择 AI角色和 Skill",
            "title": "AI处理",
        },
        {
            "depends_on": [],
            "key": "result_action",
            "status": "ready",
            "summary": "发送通知",
            "title": "结果动作",
        },
        {
            "depends_on": [],
            "key": "schedule",
            "status": "ready",
            "summary": "cron: */30 * * * *",
            "title": "调度策略",
        },
        {
            "depends_on": [],
            "key": "confirm",
            "status": "pending",
            "summary": "确认后创建定时作业",
            "title": "确认执行",
        },
    ]
    draft_response = client.get(
        f"/api/assistant/action-drafts/{draft_item['draft_id']}",
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["client_draft_id"] == "assistant_draft_online_log_anomaly_analysis"
    assert draft["preview"]["target"]["resource_type"] == "scheduled_job"


def test_ai_assistant_online_log_draft_generates_missing_prerequisites(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.products["product_online_ops"] = {
        "code": "online_ops",
        "created_at": "2026-06-18T08:00:00+00:00",
        "id": "product_online_ops",
        "name": "线上运营系统",
        "status": "active",
        "updated_at": "2026-06-18T08:00:00+00:00",
    }
    app.state.store.model_gateway_configs["model_gateway_online_log"] = {
        "api_key": "sk-online-log-test",
        "base_url": "https://models.example.com/v1",
        "created_at": "2026-06-18T08:00:00+00:00",
        "default_chat_model": "ops-chat",
        "default_embedding_model": "ops-embedding",
        "id": "model_gateway_online_log",
        "is_default": True,
        "model": "ops-chat",
        "name": "运维模型",
        "provider": "openai_compatible",
        "status": "active",
        "timeout_seconds": 60,
        "updated_at": "2026-06-18T08:00:00+00:00",
    }
    app.state.store.integration_plugins["plugin_standard_observability"] = {
        "category": "operations",
        "code": "observability",
        "id": "plugin_standard_observability",
        "is_system": True,
        "name": "可观测平台",
        "protocol": "http",
        "risk_level": "medium",
        "status": "active",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "我已生成线上日志异常分析配置草案链。",
                                        "suggestions": ["先确认数据来源", "再确认 AI 能力"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    monkeypatch.setattr(assistant_router, "urlopen", lambda _request, timeout: FakeResponse())

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": (
                "请生成线上日志异常分析定时作业草案，"
                "说明需要的数据连接、AI处理、结果动作和调度策略"
            )
        },
        headers=headers,
    )

    assert response.status_code == 200
    tool_result = response.json()["data"]["message"]["tool_results"][0]
    assert tool_result["tool"] == "assistant.action_draft"
    assert tool_result["intent"] == "online_log_anomaly_setup_draft"
    assert tool_result["summary"]["draft_count"] == 5
    connection_item, action_item, skill_item, agent_item, job_item = tool_result["items"]
    assert connection_item["action"] == "create_plugin_connection"
    assert connection_item["client_draft_id"] == "assistant_draft_observability_plugin_connection"
    assert action_item["action"] == "create_plugin_action"
    assert action_item["title"] == "线上日志查询动作"
    assert action_item["payload"]["code"] == "query_online_log_metrics"
    assert action_item["payload"]["assistant_prerequisite_draft_ids"] == [
        "assistant_draft_observability_plugin_connection"
    ]
    assert skill_item["action"] == "create_ai_skill"
    assert skill_item["client_draft_id"] == "assistant_draft_online_log_anomaly_ai_skill"
    assert agent_item["action"] == "create_ai_agent"
    assert agent_item["client_draft_id"] == "assistant_draft_online_log_anomaly_ai_agent"
    assert agent_item["payload"]["assistant_prerequisite_draft_ids"] == [
        "assistant_draft_online_log_anomaly_ai_skill"
    ]
    assert job_item["action"] == "create_scheduled_job"
    assert job_item["client_draft_id"] == "assistant_draft_online_log_anomaly_analysis"
    assert job_item["payload"]["assistant_prerequisite_draft_ids"] == [
        "assistant_draft_observability_plugin_connection",
        "assistant_draft_observability_online_log_action",
        "assistant_draft_online_log_anomaly_ai_skill",
        "assistant_draft_online_log_anomaly_ai_agent",
    ]
    assert job_item["wizard_steps"][0] == {
        "depends_on": [
            "assistant_draft_observability_plugin_connection",
            "assistant_draft_observability_online_log_action",
        ],
        "key": "data_source",
        "status": "needs_prerequisite",
        "summary": "需先确认可观测平台连接和线上日志查询动作",
        "title": "数据来源",
    }
    assert job_item["wizard_steps"][1] == {
        "depends_on": [
            "assistant_draft_online_log_anomaly_ai_skill",
            "assistant_draft_online_log_anomaly_ai_agent",
        ],
        "key": "ai_processing",
        "status": "needs_prerequisite",
        "summary": "需先确认线上日志异常检测 Skill、线上日志分析 AI角色",
        "title": "AI处理",
    }
    assert job_item["wizard_steps"][-1]["depends_on"] == job_item["payload"][
        "assistant_prerequisite_draft_ids"
    ]


def test_ai_assistant_chat_generates_knowledge_inspection_analysis_draft(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.knowledge_documents["knowledge_doc_ready"] = {
        "content": "支付故障排查手册摘要",
        "created_at": "2026-06-17T08:00:00+00:00",
        "created_by": "knowledge_owner@example.com",
        "doc_type": "manual",
        "id": "knowledge_doc_ready",
        "index_status": "indexed",
        "permission_roles": ["admin"],
        "source_type": "manual",
        "tags": ["payment"],
        "title": "支付排障手册",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.knowledge_documents["knowledge_doc_failed"] = {
        "content": "旧版发布检查清单",
        "created_at": "2026-06-01T08:00:00+00:00",
        "created_by": "knowledge_owner@example.com",
        "doc_type": "manual",
        "id": "knowledge_doc_failed",
        "index_status": "index_failed",
        "permission_roles": ["admin"],
        "source_type": "manual",
        "tags": ["release"],
        "title": "旧版发布检查清单",
        "updated_at": "2026-06-01T08:00:00+00:00",
        "vector_index_error": "embedding gateway unavailable",
    }
    app.state.store.knowledge_deposits["knowledge_deposit_pending"] = {
        "content": "本周新增排障经验待沉淀",
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "id": "knowledge_deposit_pending",
        "source_task_id": "ai_task_001",
        "status": "pending",
        "title": "支付排障经验",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "我已生成知识库巡检分析草案，确认后归档结果。",
                                        "suggestions": ["查看草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    monkeypatch.setattr(assistant_router, "urlopen", lambda _request, timeout: FakeResponse())

    response = client.post(
        "/api/assistant/chat",
        json={"message": "请生成知识库巡检草案，检查索引失败、过期知识和待处理知识沉淀"},
        headers=headers,
    )

    assert response.status_code == 200
    tool_result = response.json()["data"]["message"]["tool_results"][0]
    assert tool_result["tool"] == "assistant.action_draft"
    assert tool_result["intent"] == "knowledge_base_inspection_draft"
    draft_item = tool_result["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_knowledge_base_inspection"
    assert draft_item["status"] == "pending"
    assert draft_item["action"] == "create_analysis_draft"
    assert draft_item["title"] == "知识库巡检"
    assert draft_item["payload"]["analysis_type"] == "knowledge_base_inspection"
    assert draft_item["payload"]["summary"] == {
        "indexed_document_count": 1,
        "index_failed_document_count": 1,
        "knowledge_document_count": 2,
        "pending_deposit_count": 1,
    }
    assert draft_item["wizard_steps"] == [
        {
            "depends_on": ["知识文档索引", "知识沉淀候选"],
            "key": "data_source",
            "status": "ready",
            "summary": "读取 2 篇知识文档和 1 条待处理知识沉淀",
            "title": "数据来源",
        },
        {
            "depends_on": [],
            "key": "ai_processing",
            "status": "ready",
            "summary": "生成索引失败、权限异常、过期知识和沉淀候选巡检结论",
            "title": "AI处理",
        },
        {
            "depends_on": [],
            "key": "result_action",
            "status": "ready",
            "summary": "确认后写入助手分析结果并提供追踪入口",
            "title": "结果动作",
        },
        {
            "depends_on": [],
            "key": "schedule",
            "status": "skipped",
            "summary": "一次性分析草案，不创建定时调度",
            "title": "调度策略",
        },
        {
            "depends_on": [],
            "key": "confirm",
            "status": "pending",
            "summary": "等待人工确认后归档分析结果",
            "title": "确认执行",
        },
    ]
    assert draft_item["payload"]["findings"][0]["type"] == "index_failed"
    assert draft_item["payload"]["findings"][0]["document_id"] == "knowledge_doc_failed"

    draft_response = client.get(
        f"/api/assistant/action-drafts/{draft_item['draft_id']}",
        headers=headers,
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["data"]["preview"]["target"]["resource_type"] == (
        "assistant_analysis"
    )

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft_item['draft_id']}/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 200
    run = confirm_response.json()["data"]["run"]
    assert run["action"] == "create_analysis_draft"
    assert run["result_type"] == "assistant_analysis"
    assert run["result"]["analysis_type"] == "knowledge_base_inspection"
    assert run["result"]["source_draft_id"] == draft_item["draft_id"]


def test_ai_assistant_iteration_governance_is_deterministic_and_keeps_history(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.products["product_iteration_governance"] = {
        "code": "iteration-governance",
        "created_at": "2026-06-30T08:00:00+00:00",
        "id": "product_iteration_governance",
        "name": "迭代治理产品",
        "status": "active",
        "updated_at": "2026-06-30T08:00:00+00:00",
    }
    app.state.store.product_versions["version_iteration_governance"] = {
        "code": "v1.0",
        "created_at": "2026-06-30T08:00:00+00:00",
        "id": "version_iteration_governance",
        "name": "v1.0 迭代",
        "product_id": "product_iteration_governance",
        "status": "testing",
        "updated_at": "2026-06-30T08:00:00+00:00",
    }
    app.state.store.requirements["requirement_iteration_governance"] = {
        "created_at": "2026-06-30T08:00:00+00:00",
        "id": "requirement_iteration_governance",
        "priority": "P1",
        "product_id": "product_iteration_governance",
        "status": "testing",
        "title": "版本治理助手问答",
        "updated_at": "2026-06-30T08:00:00+00:00",
        "version_id": "version_iteration_governance",
    }
    app.state.store.bugs["bug_iteration_governance"] = {
        "created_at": "2026-06-30T08:00:00+00:00",
        "id": "bug_iteration_governance",
        "product_id": "product_iteration_governance",
        "severity": "critical",
        "status": "open",
        "title": "发布前关键缺陷",
        "updated_at": "2026-06-30T08:00:00+00:00",
        "version_id": "version_iteration_governance",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("iteration governance should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "请总结当前迭代版本阻塞项、版本总览和下一步行动",
            "product_id": "product_iteration_governance",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["model"] == "assistant-deterministic"
    message = payload["message"]
    assert "版本治理摘要" in message["content"]
    iteration_tool = next(
        item for item in message["tool_results"] if item["tool"] == "assistant.iteration"
    )
    version_item = iteration_tool["items"][0]
    assert version_item["id"] == "version_iteration_governance"
    assert version_item["blocker_count"] >= 2
    assert [item["source_type"] for item in version_item["next_actions"][:2]] == [
        "bug",
        "jenkins_release",
    ]
    assert version_item["delivery_stage_overview"][0]["key"] == "requirements"
    assert version_item["delivery_stage_overview"][0]["title"] == "需求范围"
    assert version_item["status_impact"]["target_status"] == "released"
    assert set(version_item["status_impact"]) >= {
        "blocked_count",
        "from_status",
        "target_status",
        "unchanged_count",
        "updated_count",
    }

    history_response = client.get(
        f"/api/assistant/conversations/{payload['conversation_id']}/messages",
        headers=headers,
    )
    assert history_response.status_code == 200, history_response.text
    assistant_message = [
        item
        for item in history_response.json()["data"]["items"]
        if item["role"] == "assistant"
    ][0]
    history_iteration_tool = next(
        item
        for item in assistant_message["tool_results"]
        if item["tool"] == "assistant.iteration"
    )
    assert history_iteration_tool["items"][0]["next_actions"]
    assert history_iteration_tool["items"][0]["delivery_stage_overview"][0]["key"] == "requirements"
    assert history_iteration_tool["items"][0]["status_impact"]["target_status"] == "released"
    assert set(history_iteration_tool["items"][0]["status_impact"]) >= {
        "blocked_count",
        "from_status",
        "target_status",
        "unchanged_count",
        "updated_count",
    }


def test_ai_assistant_chat_generates_release_risk_analysis_draft(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.products["product_release"] = {
        "code": "release",
        "created_at": "2026-06-17T08:00:00+00:00",
        "id": "product_release",
        "name": "发布系统",
        "status": "active",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.product_versions["version_release"] = {
        "code": "v1.2",
        "created_at": "2026-06-17T08:00:00+00:00",
        "id": "version_release",
        "name": "v1.2 发布",
        "product_id": "product_release",
        "release_date": "2026-06-20",
        "status": "testing",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.requirements["requirement_open"] = {
        "created_at": "2026-06-17T08:00:00+00:00",
        "id": "requirement_open",
        "product_id": "product_release",
        "status": "testing",
        "title": "支付回调验收",
        "updated_at": "2026-06-17T08:00:00+00:00",
        "version_id": "version_release",
    }
    app.state.store.bugs["bug_open"] = {
        "created_at": "2026-06-17T08:00:00+00:00",
        "id": "bug_open",
        "product_id": "product_release",
        "severity": "critical",
        "status": "open",
        "title": "支付回调偶发失败",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "我已生成发布风险分析草案，确认后可追踪。",
                                        "suggestions": ["查看草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    monkeypatch.setattr(assistant_router, "urlopen", lambda _request, timeout: FakeResponse())

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "请基于当前发布记录、未关闭缺陷、测试结论和需求状态生成发布风险分析草案",
            "product_id": "product_release",
        },
        headers=headers,
    )

    assert response.status_code == 200
    tool_result = response.json()["data"]["message"]["tool_results"][0]
    assert tool_result["intent"] == "release_risk_analysis_draft"
    draft_item = tool_result["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_release_risk_analysis"
    assert draft_item["status"] == "pending"
    assert draft_item["action"] == "create_analysis_draft"
    assert draft_item["payload"]["analysis_type"] == "release_risk_analysis"
    assert draft_item["payload"]["summary"] == {
        "active_release_version_count": 1,
        "critical_open_bug_count": 1,
        "open_bug_count": 1,
        "unclosed_requirement_count": 1,
    }
    assert draft_item["wizard_steps"] == [
        {
            "depends_on": ["发布记录", "缺陷列表", "需求状态"],
            "key": "data_source",
            "status": "ready",
            "summary": "读取 1 个发布版本、1 条未关闭需求和 1 个未关闭缺陷",
            "title": "数据来源",
        },
        {
            "depends_on": [],
            "key": "ai_processing",
            "status": "ready",
            "summary": "生成发布风险、阻塞项和需人工确认的风险结论",
            "title": "AI处理",
        },
        {
            "depends_on": [],
            "key": "result_action",
            "status": "ready",
            "summary": "确认后写入助手分析结果并提供追踪入口",
            "title": "结果动作",
        },
        {
            "depends_on": [],
            "key": "schedule",
            "status": "skipped",
            "summary": "一次性分析草案，不创建定时调度",
            "title": "调度策略",
        },
        {
            "depends_on": [],
            "key": "confirm",
            "status": "pending",
            "summary": "等待人工确认后归档分析结果",
            "title": "确认执行",
        },
    ]


def test_ai_assistant_chat_guides_generic_new_task_without_model_gateway(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("generic task creation guide should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "我要新增任务"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "你想新增哪类任务" in message["content"]
    guide = message["tool_results"][0]
    assert guide["tool"] == "assistant.task_creation_guide"
    assert guide["intent"] == "task_creation_guide"
    assert guide["summary"] == {
        "draft_first": True,
        "option_count": 6,
        "wizard_steps": ["数据来源", "AI处理", "结果动作", "调度策略", "确认执行"],
    }
    assert [item["type"] for item in guide["items"]] == [
        "rd_task",
        "scheduled_job",
        "ai_capability",
        "plugin_action",
        "code_inspection",
        "feedback_insight",
    ]
    assert all(
        item["wizard_steps"] == guide["summary"]["wizard_steps"]
        for item in guide["items"]
    )
    assert guide["items"][2]["draft_action"] == "create_ai_capability"
    assert guide["items"][2]["dependencies"] == ["业务场景", "模型网关", "Skill", "AI角色"]
    assert guide["items"][4]["draft_action"] == "create_scheduled_job"
    assert guide["items"][4]["dependencies"] == ["GitHub/GitLab 连接", "代码巡检动作"]
    assert payload["suggestions"] == [
        "新增研发任务",
        "新增定时作业",
        "新增AI能力配置",
        "新增动作",
        "配置代码巡检定时作业",
        "配置每周用户反馈洞察定时作业",
    ]


def test_ai_assistant_chat_guides_generic_ai_capability_configuration_without_model_gateway(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("generic AI capability guide should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "我要新增 AI能力配置"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "你想新增哪类任务" in message["content"]
    guide = message["tool_results"][0]
    assert guide["tool"] == "assistant.task_creation_guide"
    assert guide["summary"]["draft_first"] is True
    assert guide["summary"]["option_count"] == 6
    ai_capability_item = next(
        item for item in guide["items"] if item["type"] == "ai_capability"
    )
    assert ai_capability_item["title"] == "AI能力配置"
    assert ai_capability_item["draft_action"] == "create_ai_capability"
    assert ai_capability_item["wizard_steps"] == guide["summary"]["wizard_steps"]
    assert "新增AI能力配置" in payload["suggestions"]


def test_ai_assistant_chat_generates_and_confirms_rd_task_draft_from_requirement_reference(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.products["product_assistant_rd"] = {
        "code": "assistant-rd",
        "created_at": "2026-06-17T08:00:00+00:00",
        "id": "product_assistant_rd",
        "name": "AI 助手研发产品",
        "status": "active",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.product_versions["version_assistant_rd"] = {
        "code": "v1.0",
        "created_at": "2026-06-17T08:00:00+00:00",
        "id": "version_assistant_rd",
        "name": "v1.0",
        "product_id": "product_assistant_rd",
        "status": "planning",
        "updated_at": "2026-06-17T08:00:00+00:00",
    }
    app.state.store.requirements["requirement_assistant_rd"] = {
        "brain_app_id": "rd_brain",
        "content": "AI 助手需要能从 @需求 创建研发任务草案。",
        "created_at": "2026-06-17T08:00:00+00:00",
        "created_by": "user_admin",
        "id": "requirement_assistant_rd",
        "module_code": None,
        "priority": "P1",
        "product_id": "product_assistant_rd",
        "source": "product_planning",
        "status": "planned",
        "task_ids": [],
        "title": "AI 助手研发任务闭环",
        "updated_at": "2026-06-17T08:00:00+00:00",
        "version_id": "version_assistant_rd",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("rd task draft should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "请基于 @需求 新增研发任务",
            "references": [{"id": "requirement_assistant_rd", "type": "requirement"}],
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    message = response.json()["data"]["message"]
    assert "可确认" in message["content"]
    tool_result = message["tool_results"][0]
    assert tool_result["tool"] == "assistant.action_draft"
    assert tool_result["intent"] == "rd_task_draft"
    draft_item = tool_result["items"][0]
    assert draft_item["action"] == "create_rd_task"
    assert draft_item["client_draft_id"] == (
        "assistant_draft_rd_task_requirement_assistant_rd"
    )
    assert draft_item["payload"]["requirement_id"] == "requirement_assistant_rd"
    assert draft_item["payload"]["task_type"] == "product_detail_design"
    assert draft_item["preview"]["target"]["resource_type"] == "ai_task"
    assert draft_item["preview"]["validation"]["status"] == "passed"
    assert draft_item["status"] == "pending"
    assert [step["title"] for step in draft_item["wizard_steps"]] == [
        "数据来源",
        "AI处理",
        "结果动作",
        "调度策略",
        "确认执行",
    ]
    assert draft_item["wizard_steps"][3]["status"] == "skipped"

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft_item['draft_id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 200, confirm_response.text
    confirm_payload = confirm_response.json()["data"]
    assert confirm_payload["draft"]["status"] == "confirmed"
    run = confirm_payload["run"]
    assert run["action"] == "create_rd_task"
    assert run["result_type"] == "ai_task"
    task_id = run["result_id"]
    task = app.state.store.ai_tasks[task_id]
    assert task["task_type"] == "product_detail_design"
    assert task["requirement_id"] == "requirement_assistant_rd"
    assert app.state.store.requirements["requirement_assistant_rd"]["status"] == "designing"
    assert app.state.store.requirements["requirement_assistant_rd"]["task_ids"] == [task_id]


def test_ai_assistant_chat_diagnoses_failed_plugin_connection_without_model_gateway(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()
    connection = app.state.store.plugin_connections["plugin_connection_maxcompute"]
    connection["last_test_summary"] = {
        "checked_at": "2026-06-17T09:20:00+00:00",
        "error_code": "HTTP_ERROR",
        "error_message": "HTTP 403: forbidden",
        "failed_step": "http_request",
        "latency_ms": 320,
        "response_status_code": 403,
        "status": "failed",
    }
    connection["test_history"] = [
        {
            "checked_at": "2026-06-17T09:20:00+00:00",
            "error_code": "HTTP_ERROR",
            "error_message": "HTTP 403: forbidden",
            "repair_suggestions": [
                {
                    "code": "http_authentication_failed",
                    "detail": "检查认证方式、Token/API Key、Header 名和目标环境权限。",
                    "title": "检查认证配置",
                }
            ],
            "request_summary": {
                "headers": {"Authorization": "***"},
                "method": "GET",
                "url": "https://feedback.example.com",
            },
            "response_summary": {"status_code": 403},
            "status": "failed",
        }
    ]
    connection["auth_config"] = {"token": "should-not-leak"}

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("plugin connection diagnostics should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "为什么插件连接失败？"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "找到 1 个失败连接" in message["content"]
    diagnostic = message["tool_results"][0]
    assert diagnostic["tool"] == "assistant.plugin_connection_diagnostic"
    assert diagnostic["summary"] == {
        "diagnosed_count": 1,
        "failed_count": 1,
        "source": "plugin_connection.last_test_summary",
    }
    item = diagnostic["items"][0]
    assert item["id"] == "plugin_connection_maxcompute"
    assert item["status"] == "failed"
    assert item["failed_step"] == "http_request"
    assert item["error_message"] == "HTTP 403: forbidden"
    assert item["repair_suggestions"] == [
        {
            "code": "http_authentication_failed",
            "detail": "检查认证方式、Token/API Key、Header 名和目标环境权限。",
            "title": "检查认证配置",
        }
    ]
    serialized_item = json.dumps(item, ensure_ascii=False)
    assert "should-not-leak" not in serialized_item
    assert "Authorization" not in serialized_item
    assert payload["suggestions"] == ["生成插件连接修复草案", "打开插件管理"]
    assert message["references"][0]["type"] == "plugin_connection"


def _seed_ai_code_inspection_draft_context() -> None:
    now = "2026-06-17T09:00:00+00:00"
    app.state.store.products["product_rd"] = {
        "code": "rd",
        "created_at": now,
        "id": "product_rd",
        "name": "研发平台",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.integration_plugins["plugin_github"] = {
        "code": "github",
        "created_at": now,
        "id": "plugin_github",
        "name": "GitHub",
        "plugin_type": "http",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.plugin_connections["plugin_connection_github"] = {
        "auth_config": {},
        "auth_type": "bearer",
        "created_at": now,
        "created_by": "user_admin",
        "endpoint_url": "https://api.github.com",
        "environment": "prod",
        "id": "plugin_connection_github",
        "max_retries": 0,
        "name": "GitHub 生产连接",
        "plugin_id": "plugin_github",
        "request_config": {},
        "status": "active",
        "timeout_seconds": 30,
        "updated_at": now,
    }
    app.state.store.plugin_actions["plugin_action_github_code_inspection"] = {
        "action_type": "http_request",
        "code": "scan_github_code_inspection",
        "connection_id": "plugin_connection_github",
        "created_at": now,
        "created_by": "user_admin",
        "id": "plugin_action_github_code_inspection",
        "name": "GitHub 代码巡检动作",
        "plugin_id": "plugin_github",
        "request_config": {"method": "GET", "path": "/repos/{{owner}}/{{repo}}/pulls"},
        "result_mapping": {"write_target": "code_inspection_reports"},
        "status": "active",
        "updated_at": now,
    }
    app.state.store.model_gateway_configs["model_gateway_default"] = {
        "api_key": "sk-test",
        "base_url": "https://models.example.com/v1",
        "chat_model": "gpt-test",
        "created_at": now,
        "default_chat_model": "gpt-test",
        "embedding_model": "text-embedding-test",
        "id": "model_gateway_default",
        "is_default": True,
        "name": "默认模型",
        "provider": "openai_compatible",
        "status": "active",
        "updated_at": now,
    }


def _seed_git_provider_plugins() -> None:
    now = "2026-06-18T08:00:00+00:00"
    app.state.store.integration_plugins["plugin_github"] = {
        "code": "github",
        "created_at": now,
        "id": "plugin_github",
        "name": "GitHub",
        "plugin_type": "http",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.integration_plugins["plugin_gitlab"] = {
        "code": "gitlab",
        "created_at": now,
        "id": "plugin_gitlab",
        "name": "GitLab",
        "plugin_type": "http",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.plugin_connections["plugin_connection_gitlab"] = {
        "auth_config": {},
        "auth_type": "none",
        "created_at": now,
        "created_by": "user_admin",
        "endpoint_url": "https://gitlab.example.com",
        "environment": "prod",
        "id": "plugin_connection_gitlab",
        "max_retries": 0,
        "name": "GitLab 生产连接",
        "plugin_id": "plugin_gitlab",
        "request_config": {},
        "status": "active",
        "timeout_seconds": 30,
        "updated_at": now,
    }


def test_ai_assistant_chat_generates_provider_choice_for_ambiguous_git_connection(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    _seed_git_provider_plugins()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("provider choice draft generation should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我新增代码托管插件连接"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    draft_result = response.json()["data"]["message"]["tool_results"][0]
    assert draft_result["intent"] == "plugin_connection_draft"
    draft_item = draft_result["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_plugin_provider_choice_connection"
    assert draft_item["payload"]["provider_candidates"] == ["github", "gitlab"]
    assert draft_item["server_draft_id"] in app.state.store.assistant_action_drafts

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft_item['server_draft_id']}/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_PRECHECK_FAILED"

    selected_response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我新增 GitHub 插件连接"},
        headers=headers,
    )

    assert selected_response.status_code == 200, selected_response.text
    selected_item = selected_response.json()["data"]["message"]["tool_results"][0]["items"][0]
    assert selected_item["client_draft_id"] == "assistant_draft_github_plugin_connection"
    assert selected_item["payload"]["plugin_id"] == "plugin_github"
    assert selected_item["payload"]["endpoint_url"] == "https://api.github.com"
    selected_detail_response = client.get(
        f"/api/assistant/action-drafts/{selected_item['server_draft_id']}",
        headers=headers,
    )
    assert selected_detail_response.status_code == 200
    assert selected_detail_response.json()["data"]["preview"]["validation"]["status"] == "passed"


def test_ai_assistant_chat_generates_provider_choice_for_ambiguous_git_action(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    _seed_git_provider_plugins()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("provider choice draft generation should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我新增代码巡检插件动作"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    draft_item = response.json()["data"]["message"]["tool_results"][0]["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_plugin_provider_choice_action"
    assert draft_item["payload"]["provider_candidates"] == ["github", "gitlab"]

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft_item['server_draft_id']}/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_PRECHECK_FAILED"

    selected_response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我新增 GitLab 代码巡检插件动作"},
        headers=headers,
    )

    assert selected_response.status_code == 200, selected_response.text
    selected_item = selected_response.json()["data"]["message"]["tool_results"][0]["items"][0]
    assert selected_item["client_draft_id"] == "assistant_draft_gitlab_plugin_action"
    assert selected_item["payload"]["plugin_id"] == "plugin_gitlab"
    assert selected_item["payload"]["connection_id"] == "plugin_connection_gitlab"
    selected_detail_response = client.get(
        f"/api/assistant/action-drafts/{selected_item['server_draft_id']}",
        headers=headers,
    )
    assert selected_detail_response.status_code == 200
    assert selected_detail_response.json()["data"]["preview"]["validation"]["status"] == "passed"


def test_ai_assistant_chat_generates_ai_capability_prerequisites_for_ai_code_inspection(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    _seed_ai_code_inspection_draft_context()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant draft generation should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我配置 AI 代码巡检定时作业草案，用大模型分析扫描结果"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["model"] == "assistant-deterministic"
    draft_result = payload["message"]["tool_results"][0]
    assert draft_result["tool"] == "assistant.action_draft"
    assert draft_result["intent"] == "code_inspection_setup_draft"
    assert [item["action"] for item in draft_result["items"]] == [
        "create_ai_skill",
        "create_ai_agent",
        "create_scheduled_job",
    ]
    skill_item, agent_item, job_item = draft_result["items"]
    assert skill_item["server_draft_id"] in app.state.store.assistant_action_drafts
    assert agent_item["server_draft_id"] in app.state.store.assistant_action_drafts
    assert skill_item["payload"]["code"] == "code_inspection_analysis"
    assert agent_item["payload"]["code"] == "code_inspection_agent"
    assert agent_item["payload"]["assistant_prerequisite_draft_ids"] == [
        skill_item["client_draft_id"]
    ]
    assert job_item["payload"]["assistant_prerequisite_draft_ids"] == [
        skill_item["client_draft_id"],
        agent_item["client_draft_id"],
    ]
    assert job_item["payload"]["execution_mode"] == "ai_generated"
    assert job_item["payload"]["plugin_action_id"] == "plugin_action_github_code_inspection"
    assert job_item["payload"]["model_gateway_config_id"] == "model_gateway_default"
    assert job_item["wizard_steps"] == [
        {
            "depends_on": [],
            "key": "data_source",
            "status": "ready",
            "summary": "已选择 GitHub 代码巡检动作",
            "title": "数据来源",
        },
        {
            "depends_on": [
                skill_item["client_draft_id"],
                agent_item["client_draft_id"],
            ],
            "key": "ai_processing",
            "status": "needs_prerequisite",
            "summary": "需先确认代码巡检分析 Skill、代码巡检 AI角色",
            "title": "AI处理",
        },
        {
            "depends_on": [],
            "key": "result_action",
            "status": "ready",
            "summary": "写代码巡检报告、严重问题建 Bug、发送通知",
            "title": "结果动作",
        },
        {
            "depends_on": [],
            "key": "schedule",
            "status": "ready",
            "summary": "cron: 0 2 * * MON",
            "title": "调度策略",
        },
        {
            "depends_on": [
                skill_item["client_draft_id"],
                agent_item["client_draft_id"],
            ],
            "key": "confirm",
            "status": "pending",
            "summary": "确认前置草案后创建定时作业",
            "title": "确认执行",
        },
    ]


def test_ai_assistant_chat_generates_ai_capability_drafts_directly(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    now = "2026-06-18T08:00:00+00:00"
    app.state.store.model_gateway_configs["model_gateway_default"] = {
        "api_key_secret_ref": "env:MODEL_GATEWAY_API_KEY",
        "base_url": "https://model.example.test/v1",
        "chat_model": "gpt-4.1-mini",
        "created_at": now,
        "created_by": "user_admin",
        "id": "model_gateway_default",
        "name": "默认模型网关",
        "provider": "openai_compatible",
        "status": "active",
        "updated_at": now,
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("AI capability draft generation should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我新增代码巡检 AI 能力配置草案"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["model"] == "assistant-deterministic"
    message = payload["message"]
    assert "AI 能力草案" in message["content"]
    draft_result = message["tool_results"][0]
    assert draft_result["tool"] == "assistant.action_draft"
    assert draft_result["intent"] == "ai_capability_draft"
    assert draft_result["summary"] == {
        "draft_count": 2,
        "scenario": "code_inspection",
        "target": "ai_capabilities",
    }
    skill_item, agent_item = draft_result["items"]
    assert skill_item["action"] == "create_ai_skill"
    assert skill_item["client_draft_id"] == "assistant_draft_code_inspection_ai_skill"
    assert skill_item["server_draft_id"] in app.state.store.assistant_action_drafts
    assert skill_item["status"] == "pending"
    assert agent_item["action"] == "create_ai_agent"
    assert agent_item["client_draft_id"] == "assistant_draft_code_inspection_ai_agent"
    assert agent_item["server_draft_id"] in app.state.store.assistant_action_drafts
    assert agent_item["payload"]["assistant_prerequisite_draft_ids"] == [
        "assistant_draft_code_inspection_ai_skill"
    ]
    assert agent_item["payload"]["model_gateway_config_id"] == "model_gateway_default"


def test_ai_assistant_explicit_ai_skill_action_generates_skill_draft_without_task_guide(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("explicit AI Skill draft generation should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": (
                "@新建AI能力配置 新建一个基于用户客服聊天对话内容"
                "提炼成产品迭代需求的skill"
            )
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["model"] == "assistant-deterministic"
    message = payload["message"]
    assert "你想新增哪类任务" not in message["content"]
    assert "AI 能力草案" in message["content"]
    draft_result = message["tool_results"][0]
    assert draft_result["tool"] == "assistant.action_draft"
    assert draft_result["intent"] == "ai_capability_draft"
    assert draft_result["summary"] == {
        "draft_count": 1,
        "scenario": "customer_feedback_requirement",
        "target": "ai_skill",
    }
    assert len(draft_result["items"]) == 1
    skill_item = draft_result["items"][0]
    assert skill_item["action"] == "create_ai_skill"
    assert skill_item["title"] == "客服对话需求提炼 Skill"
    assert skill_item["payload"]["code"] == "customer_feedback_requirement_mining"
    assert "客服聊天对话" in skill_item["payload"]["prompt_template"]
    assert "产品迭代需求" in skill_item["payload"]["prompt_template"]
    assert skill_item["preview"]["validation"]["status"] == "passed"
    assert skill_item["server_draft_id"] in app.state.store.assistant_action_drafts

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{skill_item['server_draft_id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 200, confirm_response.text
    run = confirm_response.json()["data"]["run"]
    assert run["result_type"] == "ai_skill"
    assert app.state.store.ai_skills[run["result_id"]]["code"] == (
        "customer_feedback_requirement_mining"
    )


def test_ai_assistant_generated_ai_code_inspection_drafts_confirm_in_order(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    _seed_ai_code_inspection_draft_context()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant draft generation should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我配置 AI 代码巡检定时作业草案，用大模型分析扫描结果"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    items = response.json()["data"]["message"]["tool_results"][0]["items"]
    skill_item, agent_item, job_item = items

    skill_confirm_response = client.post(
        f"/api/assistant/action-drafts/{skill_item['server_draft_id']}/confirm",
        headers=headers,
    )
    assert skill_confirm_response.status_code == 200
    skill_id = skill_confirm_response.json()["data"]["run"]["result_id"]

    agent_confirm_response = client.post(
        f"/api/assistant/action-drafts/{agent_item['server_draft_id']}/confirm",
        headers=headers,
    )
    assert agent_confirm_response.status_code == 200, agent_confirm_response.text
    agent_run = agent_confirm_response.json()["data"]["run"]
    agent_id = agent_run["result_id"]
    assert agent_run["result"]["default_skill_ids"] == [skill_id]

    job_get_response = client.get(
        f"/api/assistant/action-drafts/{job_item['server_draft_id']}",
        headers=headers,
    )
    assert job_get_response.status_code == 200
    assert job_get_response.json()["data"]["preview"]["validation"]["status"] == "passed"

    job_confirm_response = client.post(
        f"/api/assistant/action-drafts/{job_item['server_draft_id']}/confirm",
        headers=headers,
    )
    assert job_confirm_response.status_code == 200, job_confirm_response.text
    job_run = job_confirm_response.json()["data"]["run"]
    assert job_run["result_type"] == "scheduled_job"
    assert job_run["result"]["agent_id"] == agent_id
    assert job_run["result"]["skill_ids"] == [skill_id]
    assert job_run["result"]["model_gateway_config_id"] == "model_gateway_default"


def test_ai_assistant_ai_capability_drafts_can_be_confirmed():
    headers = auth_headers()
    app.state.store.reset()

    skill_draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_ai_skill",
            "payload": {
                "code": "code_inspection_analysis",
                "name": "代码巡检分析 Skill",
                "prompt_template": "请归一化代码扫描结果并输出风险摘要。",
                "required_context": ["code_repository_inspection"],
                "status": "active",
            },
            "risk_level": "medium",
            "title": "创建代码巡检分析 Skill",
        },
        headers=headers,
    )

    assert skill_draft_response.status_code == 200
    skill_draft = skill_draft_response.json()["data"]
    assert skill_draft["preview"]["validation"]["status"] == "passed"

    skill_confirm_response = client.post(
        f"/api/assistant/action-drafts/{skill_draft['id']}/confirm",
        headers=headers,
    )

    assert skill_confirm_response.status_code == 200
    skill_result = skill_confirm_response.json()["data"]["run"]
    assert skill_result["result_type"] == "ai_skill"
    skill_id = skill_result["result_id"]
    assert app.state.store.ai_skills[skill_id]["code"] == "code_inspection_analysis"

    agent_draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_ai_agent",
            "payload": {
                "brain_app_id": "rd_brain",
                "code": "code_inspection_agent",
                "default_skill_ids": [skill_id],
                "name": "代码巡检 AI角色",
                "status": "active",
                "system_prompt": "你负责代码仓库质量、安全和规范巡检。",
            },
            "risk_level": "medium",
            "title": "创建代码巡检 AI角色",
        },
        headers=headers,
    )

    assert agent_draft_response.status_code == 200
    agent_draft = agent_draft_response.json()["data"]
    assert agent_draft["preview"]["validation"]["status"] == "passed"

    agent_confirm_response = client.post(
        f"/api/assistant/action-drafts/{agent_draft['id']}/confirm",
        headers=headers,
    )

    assert agent_confirm_response.status_code == 200
    agent_result = agent_confirm_response.json()["data"]["run"]
    assert agent_result["result_type"] == "ai_agent"
    agent_id = agent_result["result_id"]
    assert app.state.store.ai_agents[agent_id]["code"] == "code_inspection_agent"
    assert app.state.store.ai_agents[agent_id]["default_skill_ids"] == [skill_id]


def test_ai_assistant_chat_runs_explicit_mention_job_once_without_model_gateway(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 999999999,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "已执行" in message["content"]
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_insight"
    assert run["trigger_type"] == "manual"
    assert message["references"][-1] == {
        "id": run["id"],
        "title": f"提取每周用户反馈有价值信息 / {run['status']}",
        "type": "scheduled_job_run",
        "url": f"/tasks/scheduled-jobs?run_id={run['id']}",
    }
    assert message["tool_results"][0]["tool"] == "assistant.scheduled_job_run"
    assert message["tool_results"][0]["summary"]["run_id"] == run["id"]


def test_ai_assistant_chat_runs_fullwidth_explicit_mention_job_once(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 999999999,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "＠提取每周用户反馈有价值信息 执行一次"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "已执行" in message["content"]
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_insight"
    assert message["tool_results"][0]["tool"] == "assistant.scheduled_job_run"


def test_ai_assistant_chat_explains_run_once_permission_denied(monkeypatch):
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    app.state.store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

    def fail_if_model_or_run_called(*_args, **_kwargs):
        raise AssertionError("permission-denied run-once command should be deterministic")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_or_run_called)
    monkeypatch.setattr(
        assistant_chat_service,
        "run_scheduled_job_response",
        fail_if_model_or_run_called,
    )

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "没有执行定时作业的权限" in message["content"]
    assert app.state.store.scheduled_job_runs == {}
    tool_result = message["tool_results"][0]
    assert tool_result["tool"] == "assistant.scheduled_job_run"
    assert tool_result["summary"] == {
        "queries": ["提取每周用户反馈有价值信息"],
        "required_permission": "system.scheduled_jobs.run",
        "status": "permission_denied",
    }


def test_ai_assistant_chat_reuses_active_run_once_execution(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "ai_generated",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "user_feedback_insight_extract",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": "2026-06-17T06:10:00+00:00",
        "last_success_at": None,
        "lock_ttl_seconds": 999999999,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": "plugin_action_feedback",
        "plugin_action_ids": [],
        "plugin_connection_id": "plugin_connection_feedback",
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-17T06:10:00+00:00",
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_feedback_running"] = {
        "collector_run_id": "collector_run_feedback_running",
        "config_snapshot": {},
        "created_at": "2026-06-17T06:10:00+00:00",
        "error_code": None,
        "error_message": None,
        "finished_at": None,
        "id": "scheduled_job_run_feedback_running",
        "records_imported": 0,
        "result_summary": {},
        "scheduled_for": "2026-06-17T06:10:00+00:00",
        "scheduled_job_id": "scheduled_job_feedback_insight",
        "source_run_id": None,
        "started_at": "2026-06-17T06:10:00+00:00",
        "status": "running",
        "trigger_type": "manual",
        "updated_at": "2026-06-17T06:10:00+00:00",
    }

    def fail_if_run_started(**_kwargs):
        raise AssertionError("existing active run-once execution should be reused")

    monkeypatch.setattr(assistant_chat_service, "run_scheduled_job_response", fail_if_run_started)
    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "已有一次执行正在进行中" in message["content"]
    assert len(app.state.store.scheduled_job_runs) == 1
    assert message["references"][-1] == {
        "id": "scheduled_job_run_feedback_running",
        "title": "提取每周用户反馈有价值信息 / running",
        "type": "scheduled_job_run",
        "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_running",
    }
    assert message["tool_results"][0]["summary"] == {
        "error_code": None,
        "error_message": None,
        "records_imported": 0,
        "run_id": "scheduled_job_run_feedback_running",
        "scheduled_job_id": "scheduled_job_feedback_insight",
        "scheduled_job_name": "提取每周用户反馈有价值信息",
        "status": "running",
        "trigger_type": "manual",
    }


def test_ai_assistant_run_once_waits_until_new_run_is_traceable():
    run = {
        "collector_run_id": None,
        "created_at": "2026-06-17T06:20:00+00:00",
        "id": "scheduled_job_run_feedback_new",
        "scheduled_job_id": "scheduled_job_feedback_insight",
        "status": "running",
        "updated_at": "2026-06-17T06:20:00+00:00",
    }
    store = SimpleNamespace(
        scheduled_job_runs={"scheduled_job_run_feedback_new": run},
    )

    assert (
        assistant_chat_service._new_scheduled_job_run(
            store,
            existing_run_ids=set(),
            job_id="scheduled_job_feedback_insight",
        )
        is None
    )

    run["collector_run_id"] = "collector_run_feedback_new"
    assert (
        assistant_chat_service._new_scheduled_job_run(
            store,
            existing_run_ids=set(),
            job_id="scheduled_job_feedback_insight",
        )
        == run
    )


def test_ai_assistant_run_once_waits_until_repository_can_read_new_run():
    class RepositoryStub:
        def __init__(self) -> None:
            self.persisted_runs: dict[str, dict] = {}

        def list_scheduled_job_runs(
            self,
            *,
            scheduled_job_id: str | None = None,
            status: str | None = None,
        ) -> list[dict]:
            return [
                dict(run)
                for run in self.persisted_runs.values()
                if (
                    (scheduled_job_id is None or run["scheduled_job_id"] == scheduled_job_id)
                    and (status is None or run["status"] == status)
                )
            ]

    run = {
        "collector_run_id": "collector_run_feedback_new",
        "created_at": "2026-06-17T06:20:00+00:00",
        "id": "scheduled_job_run_feedback_new",
        "scheduled_job_id": "scheduled_job_feedback_insight",
        "status": "running",
        "updated_at": "2026-06-17T06:20:00+00:00",
    }
    repository = RepositoryStub()
    store = SimpleNamespace(
        repository=repository,
        scheduled_job_runs={"scheduled_job_run_feedback_new": run},
    )

    assert (
        assistant_chat_service._new_scheduled_job_run(
            store,
            existing_run_ids=set(),
            job_id="scheduled_job_feedback_insight",
        )
        is None
    )

    persisted_run = {**run, "result_summary": {"persisted": True}}
    repository.persisted_runs["scheduled_job_run_feedback_new"] = persisted_run
    assert assistant_chat_service._new_scheduled_job_run(
        store,
        existing_run_ids=set(),
        job_id="scheduled_job_feedback_insight",
    ) == persisted_run


def test_ai_assistant_chat_generates_feedback_draft_when_run_once_job_missing(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant run-once fallback should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "还没有找到可执行的定时作业" in message["content"]
    assert "尚未执行" in message["content"]
    assert app.state.store.scheduled_job_runs == {}
    draft_result = message["tool_results"][0]
    assert draft_result["tool"] == "assistant.action_draft"
    assert draft_result["intent"] == "scheduled_job_draft"
    assert draft_result["summary"]["run_once_requested"] is True
    draft_item = draft_result["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_weekly_feedback_insight"
    assert draft_item["server_draft_id"] in app.state.store.assistant_action_drafts
    assert draft_item["payload"]["config_json"]["assistant_run_once_request"] == {
        "requested": True,
        "source_message": "@提取每周用户反馈有价值信息 执行一次",
    }
    history_response = client.get(
        f"/api/assistant/conversations/{payload['conversation_id']}/messages",
        headers=headers,
    )
    assert history_response.status_code == 200, history_response.text
    history_items = history_response.json()["data"]["items"]
    history_draft_result = history_items[1]["tool_results"][0]
    history_draft_item = history_draft_result["items"][0]
    assert history_draft_item["payload"]["job_type"] == "user_feedback_insight_extract"
    assert history_draft_item["payload"]["config_json"]["assistant_run_once_request"] == {
        "requested": True,
        "source_message": "@提取每周用户反馈有价值信息 执行一次",
    }
    assert history_draft_item["wizard_steps"][0]["title"] == "数据来源"


def test_ai_assistant_history_redacts_sensitive_action_draft_payload_fields():
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.assistant_conversations = {
        "conversation_sensitive_draft": {
            "created_at": "2026-06-20T08:00:00+00:00",
            "id": "conversation_sensitive_draft",
            "last_message_at": "2026-06-20T08:01:00+00:00",
            "message_count": 1,
            "product_id": None,
            "title": "敏感草案",
            "updated_at": "2026-06-20T08:01:00+00:00",
            "user_id": "user_admin",
        }
    }
    app.state.store.assistant_messages = {
        "assistant_message_sensitive_draft": {
            "content": "我生成了一个插件连接草案。",
            "conversation_id": "conversation_sensitive_draft",
            "created_at": "2026-06-20T08:01:00+00:00",
            "id": "assistant_message_sensitive_draft",
            "metadata_json": {
                "tool_results": [
                    {
                        "intent": "plugin_connection_draft",
                        "items": [
                            {
                                "action": "create_plugin_connection",
                                "draft_id": "assistant_draft_sensitive_connection",
                                "payload": {
                                    "api_key": "sk-history-should-not-leak",
                                    "auth_config": {"token": "token-should-not-leak"},
                                    "endpoint_url": "https://api.example.com",
                                    "name": "敏感连接",
                                    "plugin_id": "plugin_sensitive",
                                    "request_config": {
                                        "headers": {
                                            "Authorization": "Bearer should-not-leak"
                                        }
                                    },
                                    "status": "active",
                                },
                                "preview": {
                                    "diffs": [
                                        {
                                            "current": "old-secret",
                                            "field": "auth_config.token",
                                            "label": "Token",
                                            "proposed": "new-secret",
                                        }
                                    ],
                                    "validation": {"issues": [], "status": "passed"},
                                },
                                "requires_confirmation": True,
                                "risk_level": "medium",
                                "title": "敏感连接草案",
                                "wizard_steps": [
                                    {
                                        "key": "configuration",
                                        "status": "ready",
                                        "summary": "使用密钥配置连接",
                                        "title": "配置",
                                    }
                                ],
                            }
                        ],
                        "tool": "assistant.action_draft",
                    }
                ]
            },
            "role": "assistant",
            "updated_at": "2026-06-20T08:01:00+00:00",
            "user_id": "user_admin",
        }
    }

    response = client.get(
        "/api/assistant/conversations/conversation_sensitive_draft/messages",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    item = response.json()["data"]["items"][0]["tool_results"][0]["items"][0]
    serialized_item = json.dumps(item, ensure_ascii=False)
    assert item["payload"] == {
        "endpoint_url": "https://api.example.com",
        "name": "敏感连接",
        "plugin_id": "plugin_sensitive",
        "status": "active",
    }
    assert item["preview"]["diffs"][0]["current"] == "***"
    assert item["preview"]["diffs"][0]["proposed"] == "***"
    assert "sk-history-should-not-leak" not in serialized_item
    assert "token-should-not-leak" not in serialized_item
    assert "should-not-leak" not in serialized_item
    assert "Authorization" not in serialized_item
    assert "auth_config" not in serialized_item


def test_ai_assistant_chat_runs_exact_explicit_mention_when_similar_jobs_exist(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    base_job = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_exact"] = {
        **base_job,
        "code": "feedback_exact",
        "id": "scheduled_job_feedback_exact",
        "name": "提取每周用户反馈有价值信息",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_similar"] = {
        **base_job,
        "code": "weekly_feedback_insight",
        "id": "scheduled_job_feedback_similar",
        "name": "每周用户反馈洞察抽取",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    message = payload["message"]
    assert payload["model"] == "assistant-deterministic"
    assert "已执行「提取每周用户反馈有价值信息」一次" in message["content"]
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_exact"
    assert message["tool_results"][0]["summary"]["scheduled_job_id"] == (
        "scheduled_job_feedback_exact"
    )


def test_ai_assistant_chat_prioritizes_structured_reference_over_text_mention(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    base_job = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_selected"] = {
        **base_job,
        "id": "scheduled_job_selected",
        "name": "结构化引用选中的作业",
    }
    app.state.store.scheduled_jobs["scheduled_job_text"] = {
        **base_job,
        "id": "scheduled_job_text",
        "name": "文本里另一个作业",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("structured run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@文本里另一个作业 执行一次",
            "references": [{"id": "scheduled_job_selected", "type": "scheduled_job"}],
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_selected"
    message = response.json()["data"]["message"]
    assert "已执行「结构化引用选中的作业」一次" in message["content"]
    assert message["intent"]["intent_code"] == "scheduled_job_run_once"


def test_ai_assistant_chat_keeps_structured_reference_even_when_text_mentions_official_feedback(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    base_job = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "interval_seconds": None,
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_selected_daily"] = {
        **base_job,
        "id": "scheduled_job_selected_daily",
        "job_type": "dashboard_snapshot_refresh",
        "name": "用户明确选择的每日看板刷新",
        "source_system": "ai-brain",
    }
    app.state.store.scheduled_jobs["scheduled_job_weekly_feedback_official"] = {
        **base_job,
        "code": "weekly_feedback_insight",
        "config_json": {"assistant_template": {"code": "weekly_feedback_insight"}},
        "id": "scheduled_job_weekly_feedback_official",
        "job_type": "user_feedback_insight_extract",
        "name": "提取每周用户反馈有价值信息",
        "source_system": "aliyun-maxcompute",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("structured run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
            "references": [
                {
                    "id": "scheduled_job_selected_daily",
                    "type": "scheduled_job",
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_selected_daily"
    message = response.json()["data"]["message"]
    assert "已执行「用户明确选择的每日看板刷新」一次" in message["content"]
    assert message["tool_results"][0]["summary"]["scheduled_job_id"] == (
        "scheduled_job_selected_daily"
    )


def test_ai_assistant_chat_prefers_enabled_job_when_run_once_alias_matches_history(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    base_job = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "execution_mode": "deterministic",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_active"] = {
        **base_job,
        "code": "weekly_feedback_insight",
        "enabled": True,
        "id": "scheduled_job_feedback_active",
        "name": "每周用户反馈洞察抽取",
        "status": "active",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_history"] = {
        **base_job,
        "code": "weekly_feedback_insight_history",
        "enabled": False,
        "id": "scheduled_job_feedback_history",
        "name": "每周用户反馈洞察历史任务",
        "status": "disabled",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    assert "已执行「每周用户反馈洞察抽取」一次" in message["content"]
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_active"
    assert message["tool_results"][0]["summary"]["scheduled_job_id"] == (
        "scheduled_job_feedback_active"
    )


def test_ai_assistant_chat_prefers_weekly_feedback_job_when_alias_matches_multiple_active_jobs(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    base_job = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "interval_seconds": None,
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        **base_job,
        "code": "weekly_feedback_insight",
        "id": "scheduled_job_feedback_insight",
        "job_type": "user_feedback_insight_extract",
        "name": "每周用户反馈洞察抽取",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_sync"] = {
        **base_job,
        "code": "weekly_feedback_sync",
        "id": "scheduled_job_feedback_sync",
        "job_type": "plugin_action_invoke",
        "name": "每周用户反馈原始数据同步",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    assert "已执行「每周用户反馈洞察抽取」一次" in message["content"]
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_insight"
    assert message["tool_results"][0]["summary"]["scheduled_job_id"] == (
        "scheduled_job_feedback_insight"
    )


def test_ai_assistant_chat_prefers_structured_reference_over_official_feedback_text(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    base_job = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "interval_seconds": None,
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "aliyun-maxcompute",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        **base_job,
        "code": "weekly_feedback_insight",
        "config_json": {"assistant_template": {"code": "weekly_feedback_insight"}},
        "id": "scheduled_job_feedback_insight",
        "job_type": "user_feedback_insight_extract",
        "name": "每周用户反馈洞察抽取",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_raw_sync"] = {
        **base_job,
        "code": "weekly_feedback_raw_sync",
        "id": "scheduled_job_feedback_raw_sync",
        "job_type": "plugin_action_invoke",
        "name": "每周用户反馈原始数据同步",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
            "references": [
                {
                    "id": "scheduled_job_feedback_raw_sync",
                    "type": "scheduled_job",
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    assert "已执行「每周用户反馈原始数据同步」一次" in message["content"]
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_raw_sync"
    assert message["tool_results"][0]["summary"]["scheduled_job_id"] == (
        "scheduled_job_feedback_raw_sync"
    )


def test_ai_assistant_chat_keeps_disabled_structured_reference_in_strict_mode(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    base_job = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "execution_mode": "deterministic",
        "interval_seconds": None,
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "aliyun-maxcompute",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        **base_job,
        "enabled": True,
        "id": "scheduled_job_feedback_insight",
        "job_type": "user_feedback_insight_extract",
        "name": "每周用户反馈洞察抽取",
        "status": "active",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_raw_disabled"] = {
        **base_job,
        "enabled": False,
        "id": "scheduled_job_feedback_raw_disabled",
        "job_type": "plugin_action_invoke",
        "name": "提取每周用户反馈有价值信息",
        "status": "disabled",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
            "references": [
                {
                    "id": "scheduled_job_feedback_raw_disabled",
                    "type": "scheduled_job",
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    assert "没有执行成功：Scheduled job is disabled" in message["content"]
    assert app.state.store.scheduled_job_runs == {}
    assert message["tool_results"][0]["summary"]["scheduled_job_id"] == (
        "scheduled_job_feedback_raw_disabled"
    )


def test_ai_assistant_chat_does_not_override_wrong_structured_reference_with_text_mention(
    monkeypatch,
):
    headers = auth_headers()
    app.state.store.reset()
    base_job = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "execution_mode": "deterministic",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_exact"] = {
        **base_job,
        "code": "feedback_exact",
        "enabled": True,
        "id": "scheduled_job_feedback_exact",
        "name": "提取每周用户反馈有价值信息",
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_similar"] = {
        **base_job,
        "code": "weekly_feedback_insight",
        "enabled": False,
        "id": "scheduled_job_feedback_similar",
        "name": "每周用户反馈洞察抽取",
    }

    def fail_if_model_called(_request, timeout):
        del timeout
        raise AssertionError("assistant deterministic run should not call the model gateway")

    monkeypatch.setattr(assistant_router, "urlopen", fail_if_model_called)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "@提取每周用户反馈有价值信息 执行一次",
            "references": [
                {
                    "id": "scheduled_job_feedback_similar",
                    "type": "scheduled_job",
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    assert "没有执行成功：Scheduled job is disabled" in message["content"]
    assert app.state.store.scheduled_job_runs == {}
    assert message["tool_results"][0]["summary"]["scheduled_job_id"] == (
        "scheduled_job_feedback_similar"
    )


def test_ai_assistant_chat_uses_model_gateway_without_logging_prompt_or_answer(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "可以从需求审批开始，再生成详细设计和技术方案。",
                                        "suggestions": [
                                            "创建需求",
                                            "查看模型网关",
                                            "检查 GitHub PR",
                                        ],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 17, "prompt_tokens": 29, "total_tokens": 46},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        body = json.loads(request.data.decode("utf-8"))
        calls.append(
            {
                "body": body,
                "timeout": timeout,
                "url": request.full_url,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "conversation_id": "conv-real-demand",
            "message": "如何跑通 AI Brain 实际需求迭代？ secret-chat-context",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["conversation_id"] == "conv-real-demand"
    assert payload["message"]["role"] == "assistant"
    assert payload["message"]["content"] == "可以从需求审批开始，再生成详细设计和技术方案。"
    assert payload["suggestions"] == ["创建需求", "查看模型网关", "检查 GitHub PR"]
    assert payload["model"] == "test-chat-model"

    assert calls and calls[0]["url"] == "https://llm.test/v1/chat/completions"
    assert calls[0]["body"]["model"] == "test-chat-model"
    assert calls[0]["body"]["messages"][0]["role"] == "system"
    assert "secret-chat-context" in calls[0]["body"]["messages"][1]["content"]

    logs = client.get("/api/model-gateway/logs?purpose=assistant_chat", headers=headers).json()[
        "data"
    ]["items"]
    assert len(logs) == 1
    assert logs[0]["purpose"] == "assistant_chat"
    assert logs[0]["status"] == "succeeded"
    assert logs[0]["tokens"] == {"prompt": 29, "completion": 17, "total": 46}
    assert "secret-chat-context" not in str(logs[0])
    assert "可以从需求审批开始" not in str(logs[0])

    audit_events = client.get(
        "/api/audit/events?event_type=assistant.chat_completed",
        headers=headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    assert audit_events[0]["payload"]["model"] == "test-chat-model"


def test_ai_assistant_chat_includes_ai_brain_system_progress_context(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    captured_messages: list[dict[str, str]] = []
    product = client.post(
        "/api/products",
        json={"code": "AI-BRAIN", "name": "AI Brain"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1.2", "name": "v1.2"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "增加 AI 助手聊天界面，回答项目开发进展。",
            "product_id": product["id"],
            "title": "AI 助手聊天界面",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task_response = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    )
    task = task_response.json()["data"]
    task_id = task["task_id"]
    now = "2026-06-05T08:00:00+00:00"
    app.state.store.human_reviews["review_assistant_pending"] = {
        "ai_task_id": task_id,
        "created_at": now,
        "id": "review_assistant_pending",
        "review_type": "product_design",
        "status": "pending",
        "updated_at": now,
        "version": 1,
    }
    app.state.store.bugs["bug_assistant_blocker"] = {
        "assignee": "qa@example.com",
        "created_at": now,
        "description": "助手上下文应展示高优先级阻塞缺陷。",
        "duplicate_of_bug_id": None,
        "evidence": {},
        "id": "bug_assistant_blocker",
        "module_code": None,
        "product_id": product["id"],
        "related_task_id": task_id,
        "reproduce_steps": ["打开助手", "查看进展"],
        "requirement_id": requirement["id"],
        "severity": "critical",
        "source": "manual_test",
        "status": "open",
        "title": "助手进度阻塞 Bug",
        "updated_at": now,
        "version_id": version["id"],
    }
    app.state.store.code_review_reports["report_assistant_recent"] = {
        "archived_at": now,
        "executor": {"executor_name": "pytest-code-review"},
        "findings": [{"file": "apps/web/src/pages/Assistant/index.tsx", "severity": "low"}],
        "gitlab_mr_snapshot_id": "snapshot_assistant_recent",
        "gitlab_writeback_performed": False,
        "id": "report_assistant_recent",
        "review_id": "review_assistant_pending",
        "risk_level": "low",
        "status": "confirmed",
        "summary": "最近代码 Review 结论：风险低，关注助手上下文覆盖。",
        "task_id": task_id,
    }
    app.state.store.knowledge_deposits["deposit_assistant_recent"] = {
        "ai_task_id": task_id,
        "content": "AI 助手上下文增强验证记录。",
        "created_at": now,
        "id": "deposit_assistant_recent",
        "knowledge_document_id": None,
        "status": "pending",
        "title": "AI 助手上下文增强知识沉淀",
        "updated_at": now,
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "AI Brain 当前已有 1 个需求和 1 个任务。",
                                        "suggestions": ["查看任务中心"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        request_body = json.loads(request.data.decode("utf-8"))
        captured_messages.extend(request_body["messages"])
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "AI Brain 项目现在开发到哪里了？", "product_id": product["id"]},
        headers=headers,
    )

    assert response.status_code == 200
    response_payload = response.json()["data"]
    assert response_payload["message"]["references"][0] == {
        "id": requirement["id"],
        "title": "AI 助手聊天界面",
        "type": "requirement",
        "url": f"/delivery/requirements?requirement_id={requirement['id']}",
    }
    assert response_payload["message"]["tool_results"][0]["tool"] == (
        "assistant.delivery_progress"
    )
    assert response_payload["message"]["tool_results"][0]["summary"]["requirements_total"] == 1
    user_message = captured_messages[1]["content"]
    assert "system_context" in user_message
    user_payload = json.loads(user_message)
    assert user_payload["system_context"]["tool_results"][0]["tool"] == (
        "assistant.delivery_progress"
    )
    assert user_payload["system_context"]["tool_results"][0]["items"][0]["id"] == (
        requirement["id"]
    )
    assert "AI Brain" in user_message
    assert "requirements_total" in user_message
    assert "ai_tasks_total" in user_message
    assert "AI 助手聊天界面" in user_message
    assert task["task_id"] in user_message
    assert "iteration_progress" in user_message
    assert "pending_reviews" in user_message
    assert "review_assistant_pending" in user_message
    assert "bug_distribution" in user_message
    assert "助手进度阻塞 Bug" in user_message
    assert "blocked_requirements" in user_message
    assert "recent_code_review_reports" in user_message
    assert "最近代码 Review 结论：风险低" in user_message
    assert "knowledge_deposits_total" in user_message
    assert "AI 助手上下文增强知识沉淀" in user_message


def test_ai_assistant_chat_includes_bounded_conversation_history(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    captured_bodies: list[dict[str, object]] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            turn = len(captured_bodies)
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": f"第 {turn} 轮回答",
                                        "suggestions": ["继续追问"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 8, "prompt_tokens": 16, "total_tokens": 24},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        del timeout
        captured_bodies.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    first_response = client.post(
        "/api/assistant/chat",
        json={"message": "请帮我分析当前 AI 助手草案能力。"},
        headers=headers,
    )

    assert first_response.status_code == 200
    conversation_id = first_response.json()["data"]["conversation_id"]
    first_payload = json.loads(captured_bodies[0]["messages"][1]["content"])
    assert first_payload["conversation_history"] == []

    assistant_message = next(
        message
        for message in app.state.store.assistant_messages.values()
        if message["conversation_id"] == conversation_id and message["role"] == "assistant"
    )
    assistant_message["metadata_json"]["tool_results"] = [
        {
            "intent": "knowledge_search",
            "items": [
                {
                    "content": "secret-full-knowledge-body",
                    "id": "knowledge_chunk_secret",
                    "status": "available",
                    "title": "隐私知识正文",
                    "type": "knowledge_chunk",
                    "url": "/assets/knowledge?chunk_id=knowledge_chunk_secret",
                }
            ],
            "references": [
                {
                    "id": "knowledge_chunk_secret",
                    "title": "隐私知识正文",
                    "type": "knowledge_chunk",
                    "url": "/assets/knowledge?chunk_id=knowledge_chunk_secret",
                }
            ],
            "summary": {"hit_count": 1},
            "tool": "assistant.knowledge_search",
        }
    ]

    second_response = client.post(
        "/api/assistant/chat",
        json={
            "conversation_id": conversation_id,
            "message": "继续刚才那个草案，下一步怎么做？",
        },
        headers=headers,
    )

    assert second_response.status_code == 200
    second_user_content = captured_bodies[1]["messages"][1]["content"]
    second_payload = json.loads(second_user_content)
    conversation_history = second_payload["conversation_history"]
    assert [item["role"] for item in conversation_history] == ["user", "assistant"]
    assert conversation_history[0]["content"] == "请帮我分析当前 AI 助手草案能力。"
    assert conversation_history[1]["content"] == "第 1 轮回答"
    history_tool_result = conversation_history[1]["tool_results"][0]
    assert history_tool_result["summary"] == {"hit_count": 1}
    assert history_tool_result["items"] == [
        {
            "id": "knowledge_chunk_secret",
            "status": "available",
            "title": "隐私知识正文",
            "type": "knowledge_chunk",
            "url": "/assets/knowledge?chunk_id=knowledge_chunk_secret",
        }
    ]
    assert "secret-full-knowledge-body" not in second_user_content


def test_ai_assistant_chat_persists_user_scoped_conversation_history(monkeypatch):
    headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "当前 AI Brain 已能回答系统进展。",
                                        "suggestions": ["查看任务中心"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 12, "prompt_tokens": 20, "total_tokens": 32},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "AI Brain 现在开发到哪里了？"},
        headers=headers,
    )

    assert response.status_code == 200
    conversation_id = response.json()["data"]["conversation_id"]

    conversations = client.get("/api/assistant/conversations", headers=headers).json()["data"]
    assert conversations["total"] == 1
    assert conversations["items"][0] == {
        "created_at": conversations["items"][0]["created_at"],
        "id": conversation_id,
        "last_message_at": conversations["items"][0]["last_message_at"],
        "message_count": 2,
        "product_id": None,
        "title": "AI Brain 现在开发到哪里了？",
        "updated_at": conversations["items"][0]["updated_at"],
    }

    messages = client.get(
        f"/api/assistant/conversations/{conversation_id}/messages",
        headers=headers,
    ).json()["data"]
    assert messages["total"] == 2
    assert [(item["role"], item["content"]) for item in messages["items"]] == [
        ("user", "AI Brain 现在开发到哪里了？"),
        ("assistant", "当前 AI Brain 已能回答系统进展。"),
    ]
    assert messages["items"][1]["tool_results"][0]["tool"] == "assistant.delivery_progress"

    reviewer_conversations = client.get(
        "/api/assistant/conversations",
        headers=reviewer_headers,
    ).json()["data"]
    assert reviewer_conversations == {
        "items": [],
        "limit": 50,
        "next_cursor": None,
        "total": 0,
    }
    forbidden_messages = client.get(
        f"/api/assistant/conversations/{conversation_id}/messages",
        headers=reviewer_headers,
    )
    assert forbidden_messages.status_code == 404


def test_ai_assistant_chat_run_cancel_endpoint_marks_current_user_run_cancelled():
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.assistant_chat_runs["assistant_chat_run_endpoint"] = {
        "created_at": "2026-06-20T08:00:00+00:00",
        "id": "assistant_chat_run_endpoint",
        "started_at": "2026-06-20T08:00:00+00:00",
        "status": "running",
        "updated_at": "2026-06-20T08:00:00+00:00",
        "user_id": "user_admin",
    }

    response = client.post(
        "/api/assistant/chat-runs/assistant_chat_run_endpoint/cancel",
        headers=headers,
        json={"reason": "用户终止"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == "assistant_chat_run_endpoint"
    assert data["status"] == "cancelled"
    assert data["cancel_reason"] == "用户终止"
    assert app.state.store.assistant_chat_runs["assistant_chat_run_endpoint"]["status"] == (
        "cancelled"
    )


def test_ai_assistant_chat_run_list_endpoint_filters_current_user_and_status():
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.assistant_chat_runs = {
        "assistant_chat_run_running_new": {
            "created_at": "2026-06-20T08:01:00+00:00",
            "id": "assistant_chat_run_running_new",
            "started_at": "2026-06-20T08:01:00+00:00",
            "status": "running",
            "updated_at": "2026-06-20T08:02:00+00:00",
            "user_id": "user_admin",
        },
        "assistant_chat_run_running_old": {
            "created_at": "2026-06-20T08:00:00+00:00",
            "id": "assistant_chat_run_running_old",
            "started_at": "2026-06-20T08:00:00+00:00",
            "status": "running",
            "updated_at": "2026-06-20T08:00:30+00:00",
            "user_id": "user_admin",
        },
        "assistant_chat_run_cancelled": {
            "created_at": "2026-06-20T07:55:00+00:00",
            "finished_at": "2026-06-20T07:56:00+00:00",
            "id": "assistant_chat_run_cancelled",
            "started_at": "2026-06-20T07:55:00+00:00",
            "status": "cancelled",
            "updated_at": "2026-06-20T07:56:00+00:00",
            "user_id": "user_admin",
        },
        "assistant_chat_run_other_user": {
            "created_at": "2026-06-20T08:03:00+00:00",
            "id": "assistant_chat_run_other_user",
            "started_at": "2026-06-20T08:03:00+00:00",
            "status": "running",
            "updated_at": "2026-06-20T08:03:00+00:00",
            "user_id": "user_reviewer",
        },
    }

    response = client.get(
        "/api/assistant/chat-runs?status=running&limit=1",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total"] == 2
    assert [item["id"] for item in data["items"]] == ["assistant_chat_run_running_new"]
    assert data["items"][0]["status"] == "running"


def test_ai_assistant_chat_run_list_endpoint_rejects_invalid_status():
    headers = auth_headers()
    app.state.store.reset()

    response = client.get(
        "/api/assistant/chat-runs?status=unknown",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
