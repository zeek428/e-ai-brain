import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.api.routers.assistant as assistant_router
import app.services.assistant_chat as assistant_chat_service
from app.core.security import hash_password
from app.core.users import MemoryUserRepository
from app.main import app

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
    assert templates_by_code["weekly_feedback_insight"]["wizard_steps"] == [
        "数据来源",
        "AI处理",
        "知识引用",
        "结果动作",
        "调度策略",
        "确认执行",
    ]
    assert "执行一次" in templates_by_code["weekly_feedback_insight"]["prompt"]
    assert templates_by_code["release_risk_analysis"]["roles"] == ["product_owner", "reviewer"]
    assert templates_by_code["knowledge_base_inspection"]["source_module"] == "知识库"
    assert templates_by_code["online_log_anomaly_analysis"]["available"] is True


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
    assert reference_by_type["ai_agent"]["id"] == "ai_agent_feedback_ops"
    assert reference_by_type["ai_skill"]["id"] == "ai_skill_feedback_summary"

    reviewer_response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "反馈", "type": "scheduled_job", "limit": 20},
        headers=reviewer_headers,
    )
    assert reviewer_response.status_code == 200
    assert reviewer_response.json()["data"] == {"items": [], "total": 0}


def test_ai_assistant_default_reference_candidates_are_balanced_across_types():
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()
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
    assert [item["type"] for item in items[:8]] == [
        "knowledge_document",
        "requirement",
        "ai_task",
        "scheduled_job",
        "scheduled_job_run",
        "plugin_action",
        "ai_agent",
        "ai_skill",
    ]


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
    assert draft["preview"]["validation"]["status"] == "passed"


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
    assert get_response.json()["data"]["status"] == "confirmed"

    audit_events = client.get(
        "/api/audit/events?subject_type=assistant_action_draft",
        headers=headers,
    ).json()["data"]["items"]
    audit_events = sorted(audit_events, key=lambda item: item["sequence"])
    assert [item["event_type"] for item in audit_events] == [
        "assistant_action_draft.created",
        "assistant_action_draft.confirmed",
    ]


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
            "metadata_json": {"modified_fields": ["cron_expression"]},
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
            "trigger_type": "manual_rerun",
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
                    {"id": "knowledge_payment_runbook", "type": "knowledge_document"}
                ]
            },
            "role": "assistant",
            "suggestions": [],
            "updated_at": now,
            "user_id": "user_admin",
        },
    }

    response = client.get("/api/assistant/metrics", headers=headers)

    assert response.status_code == 200
    metrics = response.json()["data"]
    assert metrics["summary"] == {
        "action_run_failed_count": 0,
        "action_run_succeeded_count": 1,
        "action_run_success_rate": 1.0,
        "action_run_total": 1,
        "draft_adoption_rate": 0.25,
        "draft_cancelled_count": 1,
        "draft_confirmed_count": 1,
        "draft_expired_count": 1,
        "draft_failed_count": 0,
        "draft_pending_count": 1,
        "draft_resolution_rate": 0.75,
        "draft_total": 4,
        "draft_user_modified_count": 1,
        "draft_user_modified_rate": 0.25,
        "failed_run_repair_rate": 1.0,
        "failed_run_repaired_count": 1,
        "failed_run_total": 1,
        "knowledge_reference_count": 3,
        "knowledge_reference_hit_count": 1,
        "knowledge_reference_hit_rate": 0.5,
        "knowledge_reference_request_count": 2,
        "message_total": 3,
        "reference_total": 4,
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

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_PRECHECK_FAILED"


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
    assert draft_response.json()["data"]["client_draft_id"] == "assistant_draft_email_digest"


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
        "option_count": 5,
        "wizard_steps": ["数据来源", "AI处理", "结果动作", "调度策略", "确认执行"],
    }
    assert [item["type"] for item in guide["items"]] == [
        "rd_task",
        "scheduled_job",
        "plugin_action",
        "code_inspection",
        "feedback_insight",
    ]
    assert guide["items"][3]["draft_action"] == "create_scheduled_job"
    assert guide["items"][3]["dependencies"] == ["GitHub/GitLab 连接", "代码巡检动作"]
    assert payload["suggestions"] == [
        "新增研发任务",
        "新增定时作业",
        "新增插件动作",
        "配置代码巡检定时作业",
        "配置每周用户反馈洞察定时作业",
    ]


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


def test_ai_assistant_chat_explicit_mention_overrides_wrong_command_reference(
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
    assert "已执行「提取每周用户反馈有价值信息」一次" in message["content"]
    run = next(iter(app.state.store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_exact"
    assert message["tool_results"][0]["summary"]["scheduled_job_id"] == (
        "scheduled_job_feedback_exact"
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
    assert reviewer_conversations == {"items": [], "total": 0}
    forbidden_messages = client.get(
        f"/api/assistant/conversations/{conversation_id}/messages",
        headers=reviewer_headers,
    )
    assert forbidden_messages.status_code == 404
