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
