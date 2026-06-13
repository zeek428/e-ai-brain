from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product(headers: dict[str, str]) -> dict:
    return client.post(
        "/api/products",
        json={"code": "scheduled-ai-product", "name": "定时 AI 产品"},
        headers=headers,
    ).json()["data"]


def create_model_gateway(headers: dict[str, str]) -> dict:
    return client.post(
        "/api/system/model-gateway-configs",
        json={
            "name": "定时任务模型",
            "provider": "openai_compatible",
            "base_url": "https://llm.test/v1",
            "api_key": "sk-test",
            "default_chat_model": "test-chat-model",
            "status": "active",
            "is_default": True,
        },
        headers=headers,
    ).json()["data"]


def create_feedback(headers: dict[str, str], product_id: str) -> dict:
    return client.post(
        "/api/insights/user-feedback",
        json={
            "content": "结算链路最近反馈较多，希望优先优化。",
            "feedback_type": "improvement",
            "product_id": product_id,
            "source_channel": "in_app",
            "tags": ["checkout"],
        },
        headers=headers,
    ).json()["data"]


def test_scheduled_job_templates_are_admin_managed_and_versioned():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden = client.get("/api/system/scheduled-job-templates", headers=reviewer_headers)
    assert forbidden.status_code == 403

    response = client.get("/api/system/scheduled-job-templates", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    by_code = {item["code"]: item for item in data["items"]}

    weekly = by_code["weekly_feedback_insight"]
    assert weekly["name"] == "每周用户反馈洞察抽取"
    assert weekly["publisher"] == "AI Brain 官方"
    assert weekly["template_version"] == "v1"
    assert weekly["payload_defaults"]["job_type"] == "user_feedback_insight_extract"
    assert weekly["payload_defaults"]["plugin_input_mapping"] == {
        "week_end": "{{last_full_week.end}}",
        "week_start": "{{last_full_week.start}}",
    }
    assert weekly["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "fetch_weekly_user_feedback",
    ]

    code_inspection = by_code["code_repository_inspection"]
    assert code_inspection["payload_defaults"]["job_type"] == "code_repository_inspection"
    assert code_inspection["payload_defaults"]["result_actions"][0] == {
        "type": "write_code_inspection_report",
    }
    assert code_inspection["resource_selectors"]["plugin_action"]["code_candidates"] == [
        "scan_github_code_inspection",
        "scan_gitlab_code_inspection",
    ]


def build_skill_package() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as package:
        package.writestr(
            "skill.yaml",
            "\n".join(
                [
                    "code: packaged_iteration_planning",
                    "name: 文件包迭代规划",
                    "version: 1.0.0",
                    "entry: SKILL.md",
                    "allowed_tools:",
                    "  - user_feedback",
                    "  - bugs",
                    "requires_human_review: true",
                    "risk_level: high",
                ],
            ),
        )
        package.writestr(
            "SKILL.md",
            "# 文件包迭代规划\n\n基于真实用户反馈、Bug 和线上日志生成迭代建议。",
        )
        package.writestr("schemas/input.json", '{"type":"object"}')
        package.writestr("schemas/output.json", '{"type":"object"}')
    return buffer.getvalue()


def test_ai_skill_package_upload_stores_manifest_and_local_files():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden = client.post(
        "/api/system/ai-skills/upload",
        params={"code": "packaged_iteration_planning", "name": "文件包迭代规划"},
        content=build_skill_package(),
        headers={**reviewer_headers, "Content-Type": "application/zip"},
    )
    assert forbidden.status_code == 403

    response = client.post(
        "/api/system/ai-skills/upload",
        params={"code": "packaged_iteration_planning", "name": "文件包迭代规划"},
        content=build_skill_package(),
        headers={**admin_headers, "Content-Type": "application/zip"},
    )

    assert response.status_code == 200
    skill = response.json()["data"]
    assert skill["source_type"] == "package"
    assert skill["package_checksum"]
    assert skill["package_uri"].startswith("file://")
    assert skill["manifest"]["entry"] == "SKILL.md"
    assert skill["manifest"]["code"] == "packaged_iteration_planning"
    assert skill["package_entry"] == "SKILL.md"
    assert "SKILL.md" in skill["package_files"]
    assert skill["prompt_template"].startswith("# 文件包迭代规划")

    listed = client.get("/api/system/ai-skills", headers=admin_headers).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["package_checksum"] == skill["package_checksum"]


def test_ai_skills_agents_and_scheduled_jobs_are_admin_managed():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    model_gateway = create_model_gateway(admin_headers)

    forbidden = client.post(
        "/api/system/ai-skills",
        json={
            "code": "iteration_planning",
            "name": "迭代规划",
            "prompt_template": "生成迭代建议",
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403

    skill = client.post(
        "/api/system/ai-skills",
        json={
            "allowed_tools": ["user_feedback", "bugs"],
            "code": "iteration_planning",
            "input_schema": {"type": "object"},
            "name": "迭代规划",
            "output_schema": {"type": "object"},
            "prompt_template": "根据真实证据生成迭代建议",
            "requires_human_review": True,
            "risk_level": "high",
            "status": "active",
            "version": "1.0.0",
        },
        headers=admin_headers,
    )
    assert skill.status_code == 200
    skill_data = skill.json()["data"]
    assert skill_data["id"].startswith("skill_")
    assert "api_key" not in skill_data

    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "iteration_planner",
            "default_skill_ids": [skill_data["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "迭代规划 Agent",
            "status": "active",
            "system_prompt": "你是产品迭代规划助手。",
        },
        headers=admin_headers,
    )
    assert agent.status_code == 200
    agent_data = agent.json()["data"]
    assert agent_data["default_skill_ids"] == [skill_data["id"]]

    product = create_product(admin_headers)
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent_data["id"],
            "config_json": {
                "include_evidence": True,
                "planning_cycle": "weekly",
            },
            "cron_expression": "0 9 * * MON",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "iteration_plan_suggestion_generate",
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周迭代建议",
            "product_id": product["id"],
            "schedule_type": "cron",
            "skill_ids": [skill_data["id"]],
            "source_system": "ai-brain",
            "timezone": "Asia/Shanghai",
        },
        headers=admin_headers,
    )
    assert job.status_code == 200
    job_data = job.json()["data"]
    assert job_data["id"].startswith("scheduled_job_")
    assert job_data["next_run_at"]

    listed = client.get("/api/system/scheduled-jobs", headers=admin_headers).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["agent_id"] == agent_data["id"]

    patched = client.patch(
        f"/api/system/scheduled-jobs/{job_data['id']}",
        json={"enabled": False, "name": "每周迭代建议 v2"},
        headers=admin_headers,
    )
    assert patched.status_code == 200
    patched_data = patched.json()["data"]
    assert patched_data["enabled"] is False
    assert patched_data["name"] == "每周迭代建议 v2"
    assert patched_data["status"] == "disabled"

    deleted = client.delete(
        f"/api/system/scheduled-jobs/{job_data['id']}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"deleted": True, "id": job_data["id"]}
    listed_after_delete = client.get(
        "/api/system/scheduled-jobs",
        headers=admin_headers,
    ).json()["data"]
    assert listed_after_delete["total"] == 0


def test_scheduled_job_audit_includes_assistant_draft_source():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_insight",
            "name": "反馈洞察",
            "prompt_template": "提取用户反馈洞察",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈分析 Agent",
            "status": "active",
            "system_prompt": "你负责分析用户反馈。",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "config_json": {
                "assistant_draft": {
                    "draft_id": "assistant_draft_weekly_feedback_insight",
                    "source": "assistant.action_draft",
                    "title": "每周用户反馈洞察抽取",
                },
            },
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "iteration_plan_suggestion_generate",
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周用户反馈洞察抽取",
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    job = response.json()["data"]

    audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job.created&subject_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert audit_events[0]["payload"]["assistant_draft"] == {
        "draft_id": "assistant_draft_weekly_feedback_insight",
        "source": "assistant.action_draft",
        "title": "每周用户反馈洞察抽取",
    }

    update_response = client.patch(
        f"/api/system/scheduled-jobs/{job['id']}",
        json={"name": "每周用户反馈洞察抽取 v2"},
        headers=admin_headers,
    )
    assert update_response.status_code == 200

    updated_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job.updated&subject_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert updated_audit_events[0]["payload"]["assistant_draft"] == {
        "draft_id": "assistant_draft_weekly_feedback_insight",
        "source": "assistant.action_draft",
        "title": "每周用户反馈洞察抽取",
    }


def test_scheduled_job_audit_includes_template_source():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "template_source": {
                    "source_id": "scheduled_job_run_weekly_feedback",
                    "source_type": "scheduled_job_run",
                    "title": "每周用户反馈洞察",
                },
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "dashboard_snapshot_refresh",
            "name": "每周用户反馈洞察 运行快照副本",
            "schedule_type": "manual",
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    job = response.json()["data"]

    audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job.created&subject_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert audit_events[0]["payload"]["template_source"] == {
        "source_id": "scheduled_job_run_weekly_feedback",
        "source_type": "scheduled_job_run",
        "title": "每周用户反馈洞察",
    }

    update_response = client.patch(
        f"/api/system/scheduled-jobs/{job['id']}",
        json={"enabled": False},
        headers=admin_headers,
    )
    assert update_response.status_code == 200

    updated_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job.updated&subject_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert updated_audit_events[0]["payload"]["template_source"] == {
        "source_id": "scheduled_job_run_weekly_feedback",
        "source_type": "scheduled_job_run",
        "title": "每周用户反馈洞察",
    }


def test_scheduled_job_rejects_unsearchable_knowledge_reference():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_insight",
            "name": "反馈洞察",
            "prompt_template": "结合知识文档提取用户反馈洞察",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈分析 Agent",
            "status": "active",
            "system_prompt": "你负责分析用户反馈。",
        },
        headers=admin_headers,
    ).json()["data"]
    knowledge = client.post(
        "/api/knowledge/documents",
        json={
            "content": "支付页无响应时优先排查回调超时。",
            "doc_type": "runbook",
            "permission_roles": ["admin"],
            "product_id": product["id"],
            "title": "支付排障知识",
        },
        headers=admin_headers,
    ).json()["data"]
    app.state.store.knowledge_documents[knowledge["id"]]["index_status"] = "pending_index"

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "iteration_plan_suggestion_generate",
            "knowledge_document_ids": [knowledge["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周带知识反馈洞察",
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "KNOWLEDGE_DOCUMENT_NOT_SEARCHABLE"


def test_user_feedback_collect_with_ai_pipeline_is_normalized_to_insight_extract():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "feedback_insight",
            "name": "反馈洞察",
            "prompt_template": "提取用户反馈洞察",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "feedback_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "反馈分析 Agent",
            "status": "active",
            "system_prompt": "你负责分析用户反馈。",
        },
        headers=admin_headers,
    ).json()["data"]
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "maxcompute_feedback",
            "name": "MaxCompute 用户反馈",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://example.com/feedback",
            "name": "反馈数据连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_feedback",
            "connection_id": connection["id"],
            "name": "获取反馈",
            "plugin_id": plugin["id"],
            "request_config": {"method": "GET", "mock_response_json": {"row_count": 0}},
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "user_feedback_collect",
            "model_gateway_config_id": model_gateway["id"],
            "name": "提取每周用户反馈有价值信息",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
            "source_system": "aliyun-maxcompute",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    job = response.json()["data"]
    assert job["job_type"] == "user_feedback_insight_extract"
    assert job["execution_mode"] == "ai_generated"
    assert job["agent_id"] == agent["id"]
    assert job["model_gateway_config_id"] == model_gateway["id"]
    assert job["skill_ids"] == [skill["id"]]


def test_plugin_action_scheduled_job_run_records_request_trace_summary():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "business_system",
            "code": "feedback_api",
            "name": "反馈 API",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://example.com",
            "environment": "prod",
            "name": "生产反馈 API",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_feedback",
            "connection_id": connection["id"],
            "name": "获取反馈",
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"rows": [{"id": "feedback_001"}]},
                "path": "/feedback",
                "query": {"start_pt": "{{current_date-7}}"},
            },
            "result_mapping": {
                "records_imported_path": "$.rows",
                "write_target": "scheduled_job_result",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "反馈接口取数",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "schedule_type": "manual",
            "source_system": "feedback-api",
        },
        headers=admin_headers,
    ).json()["data"]

    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    ).json()["data"]

    data_node = run["result_summary"]["execution_nodes"]["data_connection"]
    assert data_node["connection_environment"] == "prod"
    assert data_node["request_method"] == "GET"
    assert data_node["request_url"].startswith("https://example.com/feedback")
    assert "start_pt=" in data_node["request_url"]
    assert isinstance(data_node["latency_ms"], int)
    assert data_node["response_summary"] == {
        "json": {"rows": [{"id": "feedback_001"}]},
        "mocked": True,
    }
    assert data_node["records_imported"] == 1

    app.state.store.model_gateway_logs.append(
        {
            "id": "model_log_scheduled_observability",
            "tokens": {"completion": 12, "prompt": 30, "total": 42},
        },
    )
    app.state.store.scheduled_job_runs["scheduled_job_run_failed_observability"] = {
        **run,
        "error_code": "MODEL_GATEWAY_FAILED",
        "error_message": "模型处理失败",
        "finished_at": "2026-06-13T09:00:05+00:00",
        "id": "scheduled_job_run_failed_observability",
        "plugin_invocation_log_id": None,
        "records_imported": 0,
        "result_summary": {
            "execution_nodes": {
                "data_connection": {"records_imported": 1, "status": "succeeded"},
                "result_action": {
                    "records_imported": 0,
                    "status": "failed",
                    "write_target": "user_feedback_insights",
                },
                "skill_processing": {
                    "model_gateway_called": True,
                    "model_log_id": "model_log_scheduled_observability",
                    "status": "failed",
                },
            },
        },
        "started_at": "2026-06-13T09:00:00+00:00",
        "status": "failed",
    }

    observability_response = client.get(
        "/api/system/scheduled-job-runs/observability",
        headers=admin_headers,
    )
    assert observability_response.status_code == 200
    observability = observability_response.json()["data"]
    assert observability["summary"]["total_runs"] == 2
    assert observability["summary"]["succeeded_runs"] == 1
    assert observability["summary"]["failed_runs"] == 1
    assert observability["summary"]["success_rate"] == 50.0
    assert observability["summary"]["failure_rate"] == 50.0
    assert observability["summary"]["model_gateway_called_runs"] == 1
    assert observability["summary"]["model_gateway_token_total"] == 42
    assert observability["summary"]["plugin_invocation_runs"] == 1
    assert observability["summary"]["action_write_success_runs"] == 1
    assert observability["summary"]["action_write_success_rate"] == 50.0
    assert observability["error_distribution"] == [
        {"count": 1, "error": "MODEL_GATEWAY_FAILED"},
    ]
    assert observability["recent_failures"][0]["id"] == "scheduled_job_run_failed_observability"
    assert observability["slow_runs"][0]["latency_ms"] == 5000


def test_online_log_ai_analysis_requires_ai_runtime_configuration():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "online_log_ai_analysis",
            "name": "线上日志异常分析",
            "schedule_type": "manual",
            "source_system": "online-log-platform",
        },
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "AI_AGENT_REQUIRED"
    assert "AI job requires agent_id" in response.text


def test_manual_scheduled_ai_job_run_creates_snapshot_collector_run_and_suggestion():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    create_feedback(admin_headers, product["id"])

    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "iteration_planning",
            "name": "迭代规划",
            "prompt_template": "根据真实证据生成迭代建议",
            "requires_human_review": True,
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "iteration_planner",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "迭代规划 Agent",
            "status": "active",
            "system_prompt": "你是产品迭代规划助手。",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "config_json": {"include_evidence": True, "planning_cycle": "weekly"},
            "enabled": True,
            "execution_mode": "ai_generated",
            "interval_seconds": 86400,
            "job_type": "iteration_plan_suggestion_generate",
            "name": "每周迭代建议",
            "product_id": product["id"],
            "schedule_type": "interval",
            "skill_ids": [skill["id"]],
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["trigger_type"] == "manual"
    assert run["collector_run_id"].startswith("collector_run_")
    assert run["config_snapshot"]["job_type"] == "iteration_plan_suggestion_generate"
    assert run["resolved_agent_snapshot"]["id"] == agent["id"]
    assert run["resolved_skill_snapshots"][0]["id"] == skill["id"]
    assert run["tool_policy_snapshot"] == agent["tool_policy"]
    assert run["result_summary"]["suggestion_id"].startswith("suggestion_")

    suggestions = client.get(
        f"/api/planning/iteration-suggestions?product_id={product['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert suggestions["total"] == 1
    assert suggestions["items"][0]["status"] == "suggested"

    runs = client.get(
        f"/api/system/scheduled-job-runs?scheduled_job_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert runs["total"] == 1
    assert runs["items"][0]["id"] == run["id"]

    run_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job_run.succeeded&subject_id={run['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert run_audit_events[0]["payload"] == {
        "agent_id": agent["id"],
        "collector_run_id": run["collector_run_id"],
        "execution_mode": "ai_generated",
        "job_type": "iteration_plan_suggestion_generate",
        "model_gateway_config_id": model_gateway["id"],
        "product_id": product["id"],
        "records_imported": 1,
        "scheduled_job_id": job["id"],
        "skill_ids": [skill["id"]],
        "status": "succeeded",
        "trigger_type": "manual",
    }

    invalid_trigger_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        json={"trigger_type": "rerun"},
        headers=admin_headers,
    )
    assert invalid_trigger_response.status_code == 400
    assert invalid_trigger_response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "Unsupported scheduled job run trigger_type" in invalid_trigger_response.text

    rerun_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        json={"source_run_id": run["id"], "trigger_type": "manual_rerun"},
        headers=admin_headers,
    )
    assert rerun_response.status_code == 200
    rerun = rerun_response.json()["data"]
    assert rerun["status"] == "succeeded"
    assert rerun["source_run_id"] == run["id"]
    assert rerun["source_run_summary"] == {
        "error_code": None,
        "finished_at": run["finished_at"],
        "id": run["id"],
        "latency_ms": None,
        "records_imported": 1,
        "started_at": run["started_at"],
        "status": "succeeded",
        "trigger_type": "manual",
    }
    assert rerun["trigger_type"] == "manual_rerun"

    runs = client.get(
        f"/api/system/scheduled-job-runs?scheduled_job_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert runs["total"] == 2
    assert {item["id"] for item in runs["items"]} == {run["id"], rerun["id"]}
    listed_rerun = next(item for item in runs["items"] if item["id"] == rerun["id"])
    assert listed_rerun["source_run_summary"]["id"] == run["id"]
    assert listed_rerun["source_run_summary"]["records_imported"] == 1

    rerun_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job_run.succeeded&subject_id={rerun['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert rerun_audit_events[0]["payload"] == {
        "agent_id": agent["id"],
        "collector_run_id": rerun["collector_run_id"],
        "execution_mode": "ai_generated",
        "job_type": "iteration_plan_suggestion_generate",
        "model_gateway_config_id": model_gateway["id"],
        "product_id": product["id"],
        "records_imported": 1,
        "scheduled_job_id": job["id"],
        "skill_ids": [skill["id"]],
        "source_run_id": run["id"],
        "status": "succeeded",
        "trigger_type": "manual_rerun",
    }

    invalid_source_trigger_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        json={"source_run_id": run["id"], "trigger_type": "manual"},
        headers=admin_headers,
    )
    assert invalid_source_trigger_response.status_code == 400
    assert invalid_source_trigger_response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert (
        "source_run_id is only supported for manual_rerun"
        in invalid_source_trigger_response.text
    )

    missing_source_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        json={"source_run_id": "scheduled_job_run_missing", "trigger_type": "manual_rerun"},
        headers=admin_headers,
    )
    assert missing_source_response.status_code == 404
    assert missing_source_response.json()["detail"]["code"] == "NOT_FOUND"


def test_scheduled_ai_job_run_loads_packaged_skill_files_into_snapshot():
    app.state.store.reset()
    admin_headers = auth_headers()
    model_gateway = create_model_gateway(admin_headers)
    product = create_product(admin_headers)
    create_feedback(admin_headers, product["id"])

    skill = client.post(
        "/api/system/ai-skills/upload",
        params={"code": "packaged_iteration_planning", "name": "文件包迭代规划"},
        content=build_skill_package(),
        headers={**admin_headers, "Content-Type": "application/zip"},
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "packaged_iteration_planner",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "文件包迭代规划 Agent",
            "status": "active",
            "system_prompt": "你是产品迭代规划助手。",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "config_json": {"include_evidence": True, "planning_cycle": "weekly"},
            "enabled": True,
            "execution_mode": "ai_generated",
            "interval_seconds": 86400,
            "job_type": "iteration_plan_suggestion_generate",
            "name": "每周文件包迭代建议",
            "product_id": product["id"],
            "schedule_type": "interval",
            "skill_ids": [skill["id"]],
            "source_system": "ai-brain",
        },
        headers=admin_headers,
    ).json()["data"]

    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    ).json()["data"]

    skill_snapshot = run["resolved_skill_snapshots"][0]
    assert skill_snapshot["source_type"] == "package"
    assert skill_snapshot["package_snapshot"]["entry"] == "SKILL.md"
    assert "真实用户反馈" in skill_snapshot["package_snapshot"]["entry_content"]
    assert skill_snapshot["package_snapshot"]["checksum"] == skill["package_checksum"]
