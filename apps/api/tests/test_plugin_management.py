import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

import app.services.plugins as plugin_services
import app.services.scheduled_jobs as scheduled_jobs_service
from app.main import app
from app.services.plugins import (
    records_imported_from_mapping,
    resolve_action_request_config,
    resolve_plugin_request_config,
)
from app.services.scheduled_jobs import resolve_plugin_input_mapping

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_plugin_bundle(headers: dict[str, str]) -> tuple[dict, dict, dict]:
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "devops",
            "code": "gitlab_metrics",
            "description": "采集 GitLab 指标",
            "name": "GitLab 指标插件",
            "protocol": "http",
            "risk_level": "medium",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {"header_name": "PRIVATE-TOKEN", "secret_ref": "vault/gitlab/token"},
            "auth_type": "api_key_header",
            "endpoint_url": "https://gitlab.example.com",
            "environment": "test",
            "max_retries": 1,
            "name": "测试 GitLab",
            "plugin_id": plugin["id"],
            "request_config": {
                "headers": {
                    "Authorization": "APPCODE connection-secret",
                    "X-Connection-Source": "connection-default",
                    "X-Override": "connection",
                },
                "query": {"scope": "connection", "shared_token": "gitlab"},
            },
            "status": "active",
            "timeout_seconds": 30,
        },
        headers=headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_daily_metrics",
            "connection_id": connection["id"],
            "input_schema": {"type": "object"},
            "name": "拉取每日指标",
            "output_schema": {"type": "object"},
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {"commits": 8, "mrs": 2},
                "path": "/api/v4/projects/1/metrics",
                "headers": {"X-Action-Source": "action-default", "X-Override": "action"},
                "query": {"metric": "daily", "scope": "action"},
            },
            "result_mapping": {"records_imported_path": "$.commits"},
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    return plugin, connection, action


def create_product(headers: dict[str, str]) -> dict:
    return client.post(
        "/api/products",
        json={"code": "maxcompute-insight-product", "name": "MaxCompute 洞察产品"},
        headers=headers,
    ).json()["data"]


def test_plugins_connections_and_actions_are_admin_managed_plaintext_and_audited():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden = client.post(
        "/api/system/plugins",
        json={"code": "forbidden", "name": "无权插件", "protocol": "http"},
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403

    plugin, connection, action = create_plugin_bundle(admin_headers)

    assert plugin["id"].startswith("plugin_")
    assert plugin["protocol"] == "http"
    assert connection["auth_config"]["secret_ref"] == "vault/gitlab/token"
    assert connection["request_config"]["headers"]["Authorization"] == "APPCODE connection-secret"
    assert connection["request_config"]["headers"]["X-Connection-Source"] == "connection-default"
    assert action["connection_id"] == connection["id"]

    listed_connections = client.get(
        f"/api/system/plugin-connections?plugin_id={plugin['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert listed_connections["total"] == 1
    assert listed_connections["items"][0]["auth_config"]["secret_ref"] == "vault/gitlab/token"
    assert (
        listed_connections["items"][0]["request_config"]["headers"]["Authorization"]
        == "APPCODE connection-secret"
    )
    assert listed_connections["items"][0]["request_config"]["query"]["shared_token"] == "gitlab"

    audit_events = client.get("/api/audit/events", headers=admin_headers).json()["data"]["items"]
    event_types = [event["event_type"] for event in audit_events]
    assert "plugin.created" in event_types
    assert "plugin_connection.created" in event_types
    assert "plugin_action.created" in event_types
    assert "vault/gitlab/token" not in str(audit_events)


def test_plugin_marketplace_lists_official_catalog_with_runtime_status():
    app.state.store.reset()
    admin_headers = auth_headers()

    marketplace = client.get(
        "/api/system/plugin-marketplace",
        headers=admin_headers,
    )

    assert marketplace.status_code == 200
    items = marketplace.json()["data"]["items"]
    by_code = {item["code"]: item for item in items}
    assert set(by_code) == {"ai_executor", "email", "github", "gitlab"}
    assert by_code["ai_executor"]["installed"] is True
    assert by_code["ai_executor"]["is_system"] is True
    assert by_code["ai_executor"]["latest_template_version"] == "v1"
    assert by_code["ai_executor"]["template_version"] == "v1"
    assert by_code["ai_executor"]["upgrade_available"] is False
    assert by_code["ai_executor"]["version_status"] == "latest"
    assert by_code["ai_executor"]["plugin_id"] == "plugin_standard_ai_executor"
    assert "AI 执行器下达指令" in by_code["ai_executor"]["action_templates"]
    assert "执行完成后同步回写" in by_code["ai_executor"]["recommended_scenarios"]
    assert by_code["ai_executor"]["connection_defaults"]["protocol"] == "runner_polling"
    assert by_code["ai_executor"]["connection_defaults"]["endpoint_url"] == "model-gateway://default"
    assert by_code["ai_executor"]["connection_defaults"]["auth_type"] == "none"
    assert by_code["ai_executor"]["connection_defaults"]["auth_config"] == {}
    ai_executor_query = by_code["ai_executor"]["connection_defaults"]["request_config"]["query"]
    assert ai_executor_query["executor_type"] == "model_gateway"
    assert ai_executor_query["runner_id"] == "ai_executor_runner_system_default"
    assert ai_executor_query["supported_executor_types"] == [
        "model_gateway",
        "codex",
        "claude",
        "hermes",
        "openclaw",
    ]
    assert ai_executor_query["result_callback_url"] == ""
    assert ai_executor_query["workspace_root"] == "/workspace"
    ai_executor_schema = by_code["ai_executor"]["connection_schema"]
    assert ai_executor_schema["sections"][0]["title"] == "执行器调用配置"
    assert ai_executor_schema["sections"][0]["fields"][0]["key"] == "runner_id"
    assert ai_executor_schema["sections"][0]["fields"][1]["options"] == [
        "model_gateway",
        "codex",
        "claude",
        "hermes",
        "openclaw",
    ]
    assert "aliyun_maxcompute" not in by_code
    assert by_code["github"]["installed"] is True
    assert by_code["github"]["is_system"] is True
    assert by_code["github"]["plugin_id"] == "plugin_standard_github"
    assert by_code["github"]["publisher"] == "AI Brain 官方"
    assert "GitHub 代码巡检" in by_code["github"]["action_templates"]
    assert by_code["github"]["connection_template_version"] == "v1"
    assert by_code["github"]["latest_template_version"] == "v1"
    assert by_code["github"]["template_version"] == "v1"
    assert by_code["github"]["version_status"] == "latest"
    assert by_code["github"]["connection_defaults"]["auth_type"] == "bearer"
    assert by_code["github"]["connection_defaults"]["auth_config"] == {}
    assert by_code["github"]["connection_defaults"]["endpoint_url"] == "https://api.github.com"
    github_repository_field = by_code["github"]["connection_schema"]["sections"][0]["fields"][0]
    assert github_repository_field["key"] == "repository_url"
    assert github_repository_field["label"] == "仓库地址"
    assert github_repository_field["managed_query_keys"] == ["owner", "repo"]
    assert (
        by_code["github"]["connection_defaults"]["request_config"]["headers"][
            "X-GitHub-Api-Version"
        ]
        == "2022-11-28"
    )
    assert by_code["gitlab"]["connection_defaults"]["auth_config"]["header_name"] == "PRIVATE-TOKEN"
    assert by_code["gitlab"]["connection_defaults"]["endpoint_url"] == "http://gitlab.local"
    gitlab_project_field = by_code["gitlab"]["connection_schema"]["sections"][0]["fields"][0]
    assert gitlab_project_field["key"] == "gitlab_project_url"
    assert gitlab_project_field["label"] == "GitLab 地址"
    assert gitlab_project_field["managed_query_keys"] == [
        "api_version",
        "group_id",
        "project_id",
        "project_path",
    ]
    email_defaults = by_code["email"]["connection_defaults"]
    assert email_defaults["request_config"]["headers"] == {
        "Content-Type": "application/json",
    }
    email_query = email_defaults["request_config"]["query"]
    assert email_query["send_protocol"] == "smtp"
    assert email_query["receive_protocol"] == "imap"
    assert email_query["smtp_host"] == "smtp.example.com"
    assert email_query["smtp_port"] == 465
    assert email_query["imap_host"] == "imap.example.com"
    assert email_query["imap_port"] == 993
    assert email_query["mailbox_folder"] == "INBOX"
    assert email_query["poll_since"] == "{{current_date-7}}"
    assert by_code["email"]["connection_schema"]["sections"][1]["title"] == "收件配置"
    assert by_code["github"]["connection_count"] == 0
    assert by_code["github"]["action_count"] == 0

    missing_github_token = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {},
            "auth_type": "bearer",
            "endpoint_url": "https://api.github.com",
            "environment": "prod",
            "name": "缺少 Token 的 GitHub 连接",
            "plugin_id": "plugin_standard_github",
            "status": "active",
        },
        headers=admin_headers,
    )
    assert missing_github_token.status_code == 400
    assert missing_github_token.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert missing_github_token.json()["detail"]["message"] == "GitHub token_ref is required"

    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {"token_ref": "vault/github/token"},
            "auth_type": "bearer",
            "endpoint_url": "https://api.github.com",
            "environment": "prod",
            "name": "生产 GitHub 组织",
            "plugin_id": "plugin_standard_github",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "scan_github_code_inspection",
            "connection_id": connection["id"],
            "name": "GitHub 代码巡检",
            "plugin_id": "plugin_standard_github",
            "request_config": {
                "method": "GET",
                "path": "/repos/{{owner}}/{{repo}}/code-scanning/alerts",
            },
            "result_mapping": {
                "findings_path": "$.alerts",
                "write_target": "code_inspection_reports",
            },
            "status": "active",
        },
        headers=admin_headers,
    )

    marketplace = client.get(
        "/api/system/plugin-marketplace",
        headers=admin_headers,
    ).json()["data"]
    github_item = {item["code"]: item for item in marketplace["items"]}["github"]
    assert github_item["connection_count"] == 1
    assert github_item["action_count"] == 1


def test_plugin_action_templates_are_structured_for_dynamic_forms():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.get(
        "/api/system/plugin-action-templates",
        headers=admin_headers,
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    by_code = {item["code"]: item for item in items}
    assert set(by_code) >= {
        "ai_executor_command",
        "ai_executor_result_sync",
        "email_notification",
        "email_receive",
        "github_code_inspection",
        "gitlab_code_inspection",
    }
    assert "maxcompute_weekly_feedback" not in by_code
    ai_command_template = by_code["ai_executor_command"]
    assert ai_command_template["template_version"] == "v1"
    assert ai_command_template["plugin_code"] == "ai_executor"
    assert ai_command_template["action_type"] == "mcp_tool"
    assert "OpenClaw" in ai_command_template["description"]
    assert ai_command_template["form_defaults"]["executor_type"] == "model_gateway"
    assert ai_command_template["form_defaults"]["runner_id"] == "ai_executor_runner_system_default"
    assert ai_command_template["form_defaults"]["instruction_timeout_seconds"] == 1800
    assert ai_command_template["request_config"]["tool_name"] == "ai_executor.run_instruction"
    assert ai_command_template["request_config"]["executor_type"] == "{{executor_type}}"
    assert ai_command_template["request_config"]["runner_id"] == "{{runner_id}}"
    assert ai_command_template["request_config"]["instruction_timeout_seconds"] == (
        "{{instruction_timeout_seconds}}"
    )
    assert ai_command_template["request_config"]["query"]["runner_id"] == "{{runner_id}}"
    assert ai_command_template["request_config"]["wait_for_completion"] is True
    assert ai_command_template["result_mapping"]["write_target"] == "scheduled_job_result"
    ai_sync_template = by_code["ai_executor_result_sync"]
    assert ai_sync_template["plugin_code"] == "ai_executor"
    assert ai_sync_template["request_config"]["tool_name"] == "ai_executor.sync_result"
    assert ai_sync_template["request_config"]["query"]["result_callback_url"] == (
        "{{result_callback_url}}"
    )
    github_template = by_code["github_code_inspection"]
    assert github_template["template_version"] == "v1"
    assert github_template["plugin_code"] == "github"
    assert github_template["action_type"] == "http_request"
    assert github_template["request_config"]["path"] == (
        "/repos/{{owner}}/{{repo}}/code-scanning/alerts"
    )
    assert github_template["request_config"]["query"]["state"] == "open"
    assert github_template["result_mapping"]["write_target"] == "code_inspection_reports"
    email_template = by_code["email_notification"]
    assert email_template["template_version"] == "v1"
    assert email_template["request_config"]["path"] == "/messages/send"
    assert email_template["request_config"]["headers"]["Content-Type"] == "application/json"
    assert email_template["result_mapping"]["write_target"] == "email_notifications"
    email_receive_template = by_code["email_receive"]
    assert email_receive_template["plugin_code"] == "email"
    assert email_receive_template["request_config"]["path"] == "/messages/search"
    assert email_receive_template["request_config"]["query"]["folder"] == "{{mailbox_folder}}"
    assert email_receive_template["request_config"]["query"]["since"] == "{{poll_since}}"

def test_plugin_request_config_replaces_path_templates_from_connection_params():
    connection = {
        "endpoint_url": "https://api.github.com",
        "request_config": {
            "query": {
                "owner": "acme",
                "repo": "ai-brain",
            },
        },
    }
    action = {
        "request_config": {
            "method": "GET",
            "path": "/repos/{{owner}}/{{repo}}/code-scanning/alerts",
            "query": {
                "per_page": 100,
                "state": "open",
            },
        },
    }

    request_config = resolve_plugin_request_config(connection, action)

    assert request_config["path"] == "/repos/acme/ai-brain/code-scanning/alerts"
    assert request_config["query"] == {
        "owner": "acme",
        "per_page": 100,
        "repo": "ai-brain",
        "state": "open",
    }


def test_ai_executor_runners_include_system_default_model_gateway_executor():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.get(
        "/api/system/ai-executor-runners",
        headers=admin_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    runners = {item["id"]: item for item in payload["items"]}
    system_runner = runners["ai_executor_runner_system_default"]
    assert system_runner["name"] == "系统默认执行器"
    assert system_runner["protocol"] == "model_gateway"
    assert system_runner["endpoint_url"] == "model-gateway://default"
    assert system_runner["executor_types"] == ["model_gateway"]
    assert system_runner["workspace_roots"] == ["*"]
    assert system_runner["health_status"] == "managed"
    assert system_runner["metadata"]["is_system"] is True
    assert system_runner["token_configured"] is False
    assert "无需启动本地 Runner" in system_runner["setup_command"]
    assert payload["total"] == len(payload["items"])

    delete_response = client.delete(
        "/api/system/ai-executor-runners/ai_executor_runner_system_default",
        headers=admin_headers,
    )

    assert delete_response.status_code == 409
    assert delete_response.json()["detail"]["code"] == "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED"


def test_ai_executor_action_invokes_system_default_model_gateway_executor(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    client.get("/api/system/plugin-marketplace", headers=admin_headers)
    captured_tasks = []

    def fake_call_model_gateway_for_task(
        current_store,
        *,
        code_review_payload=None,
        opener=None,
        task,
    ):
        captured_tasks.append(task)
        log = {
            "config_id": "model_gateway_default",
            "id": current_store.new_id("model_gateway_log"),
            "latency_ms": 8,
            "model": "system-default-chat",
            "provider": "openai_compatible",
            "status": "succeeded",
            "task_id": task["id"],
        }
        current_store.model_gateway_logs.append(log)
        return {"summary": "默认模型已完成分析", "insights": ["发现 1 个可优化项"]}, log

    monkeypatch.setattr(
        plugin_services,
        "call_model_gateway_for_task",
        fake_call_model_gateway_for_task,
        raising=False,
    )

    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "model-gateway://default",
            "environment": "prod",
            "name": "系统默认模型执行器",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "query": {
                    "executor_type": "model_gateway",
                    "instruction_timeout_seconds": 600,
                    "runner_id": "ai_executor_runner_system_default",
                    "workspace_root": "/workspace",
                },
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "mcp_tool",
            "code": "run_system_model_instruction",
            "connection_id": connection["id"],
            "name": "系统默认模型执行",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "instruction": "分析输入数据并输出结构化结论。",
                "tool_name": "ai_executor.run_instruction",
            },
            "result_mapping": {"write_target": "scheduled_job_result"},
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    invoked = client.post(
        f"/api/system/plugin-actions/{action['id']}/invoke",
        json={"input_payload": {"rows": [{"feedback": "导出体验慢"}]}},
        headers=admin_headers,
    )

    assert invoked.status_code == 200
    log = invoked.json()["data"]
    assert log["status"] == "succeeded"
    response_json = log["response_summary"]["json"]
    assert response_json["executor_type"] == "model_gateway"
    assert response_json["runner_id"] == "ai_executor_runner_system_default"
    assert response_json["status"] == "succeeded"
    assert response_json["model_gateway_called"] is True
    assert response_json["result_json"]["summary"] == "默认模型已完成分析"
    runner_node = log["response_summary"]["runner"]
    assert runner_node["status"] == "succeeded"
    assert runner_node["result_json"]["insights"] == ["发现 1 个可优化项"]
    assert captured_tasks[0]["task_type"] == "ai_executor_instruction"
    assert captured_tasks[0]["input_json"]["instruction"] == "分析输入数据并输出结构化结论。"
    assert captured_tasks[0]["input_json"]["input_payload"]["rows"][0]["feedback"] == "导出体验慢"


def test_ai_executor_runner_polling_lifecycle_supports_openclaw_tasks():
    app.state.store.reset()
    admin_headers = auth_headers()
    client.get("/api/system/plugin-marketplace", headers=admin_headers)

    created_runner = client.post(
        "/api/system/ai-executor-runners",
        json={
            "executor_types": ["codex", "openclaw"],
            "name": "Zeek Mac 本地执行器",
            "protocol": "runner_polling",
            "runner_token": "runner-secret",
            "workspace_roots": ["/Users/zeek/source/e-ai-brain"],
        },
        headers=admin_headers,
    )
    assert created_runner.status_code == 200
    runner = created_runner.json()["data"]
    assert runner["executor_types"] == ["codex", "openclaw"]
    assert runner["runner_token"] == "runner-secret"
    assert runner["token_configured"] is True
    assert "token_hash" not in runner

    bad_heartbeat = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        json={"metadata": {"codex_path": "/Applications/Codex.app/Contents/Resources/codex"}},
        headers={"X-Runner-Token": "wrong"},
    )
    assert bad_heartbeat.status_code == 401
    assert bad_heartbeat.json()["detail"]["code"] == "AI_EXECUTOR_RUNNER_TOKEN_INVALID"

    heartbeat = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        json={"metadata": {"openclaw_path": "/usr/local/bin/openclaw"}},
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["data"]["metadata"]["openclaw_path"] == "/usr/local/bin/openclaw"
    assert heartbeat.json()["data"]["last_heartbeat_at"]

    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "runner://ai-executor",
            "environment": "dev",
            "name": "本地 OpenClaw Runner",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "query": {
                    "executor_type": "openclaw",
                    "instruction_timeout_seconds": 900,
                    "runner_id": runner["id"],
                    "workspace_root": "/Users/zeek/source/e-ai-brain",
                },
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "mcp_tool",
            "code": "run_openclaw_instruction",
            "connection_id": connection["id"],
            "name": "OpenClaw 执行指令",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "instruction": "扫描仓库质量、安全和规范问题，输出 JSON。",
                "tool_name": "ai_executor.run_instruction",
            },
            "result_mapping": {"write_target": "scheduled_job_result"},
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    invoked = client.post(
        f"/api/system/plugin-actions/{action['id']}/invoke",
        json={"input_payload": {"source": "manual"}},
        headers=admin_headers,
    )
    assert invoked.status_code == 200
    log = invoked.json()["data"]
    assert log["status"] == "succeeded"
    assert log["response_summary"]["json"]["executor_type"] == "openclaw"
    assert log["response_summary"]["json"]["status"] == "queued"
    task_id = log["response_summary"]["json"]["runner_task_id"]

    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "openclaw", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert claimed.status_code == 200
    task = claimed.json()["data"]["task"]
    assert task["id"] == task_id
    assert task["executor_type"] == "openclaw"
    assert task["instruction"].startswith("扫描仓库质量")
    assert task["plugin_invocation_log_id"] == log["id"]

    completed = client.post(
        f"/api/system/ai-executor-tasks/{task_id}/complete",
        json={
            "logs": [{"level": "info", "message": "openclaw finished"}],
            "result_json": {"finding_count": 0, "summary": "未发现高风险问题"},
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200
    completed_task = completed.json()["data"]["task"]
    assert completed_task["status"] == "succeeded"
    assert completed_task["result_json"]["summary"] == "未发现高风险问题"

    listed_runners = client.get(
        "/api/system/ai-executor-runners",
        headers=admin_headers,
    ).json()["data"]
    assert listed_runners["total"] == 2
    listed_runner = next(item for item in listed_runners["items"] if item["id"] == runner["id"])
    assert listed_runner["token_configured"] is True
    assert listed_runner["health_status"] == "online"
    assert isinstance(listed_runner["heartbeat_age_seconds"], int)
    assert "ai-brain-runner" in listed_runner["setup_command"]


def test_ai_executor_runner_token_rotation_logs_cancel_and_timeout_controls():
    app.state.store.reset()
    admin_headers = auth_headers()
    client.get("/api/system/plugin-marketplace", headers=admin_headers)

    runner = client.post(
        "/api/system/ai-executor-runners",
        json={
            "executor_types": ["openclaw"],
            "heartbeat_timeout_seconds": 30,
            "name": "OpenClaw Runner",
            "protocol": "runner_polling",
            "runner_token": "runner-secret-v1",
            "workspace_roots": ["/Users/zeek/source/e-ai-brain"],
        },
        headers=admin_headers,
    ).json()["data"]

    rotated = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/rotate-token",
        json={"runner_token": "runner-secret-v2"},
        headers=admin_headers,
    )
    assert rotated.status_code == 200
    rotated_runner = rotated.json()["data"]
    assert rotated_runner["runner_token"] == "runner-secret-v2"
    assert rotated_runner["token_rotated_at"]
    assert rotated_runner["token_version"] == 2

    old_heartbeat = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        json={"metadata": {}},
        headers={"X-Runner-Token": "runner-secret-v1"},
    )
    assert old_heartbeat.status_code == 401

    new_heartbeat = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        json={"metadata": {"pid": 123}},
        headers={"X-Runner-Token": "runner-secret-v2"},
    )
    assert new_heartbeat.status_code == 200

    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "runner://ai-executor",
            "environment": "dev",
            "name": "OpenClaw Runner 连接",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "query": {
                    "executor_type": "openclaw",
                    "instruction_timeout_seconds": 1,
                    "runner_id": runner["id"],
                    "workspace_root": "/Users/zeek/source/e-ai-brain",
                },
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "mcp_tool",
            "code": "openclaw_cancel_timeout",
            "connection_id": connection["id"],
            "name": "OpenClaw 取消超时",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "instruction": "执行较长仓库扫描并持续输出日志。",
                "tool_name": "ai_executor.run_instruction",
            },
            "result_mapping": {"write_target": "scheduled_job_result"},
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    invoked = client.post(
        f"/api/system/plugin-actions/{action['id']}/invoke",
        json={"input_payload": {"source": "manual"}},
        headers=admin_headers,
    ).json()["data"]
    task_id = invoked["response_summary"]["json"]["runner_task_id"]

    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "openclaw", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret-v2"},
    )
    assert claimed.status_code == 200

    appended_logs = client.post(
        f"/api/system/ai-executor-tasks/{task_id}/logs",
        json={
            "logs": [
                {"level": "info", "message": "checkout repository"},
                {"level": "info", "message": "scan started"},
            ],
            "runner_id": runner["id"],
            "status": "running",
        },
        headers={"X-Runner-Token": "runner-secret-v2"},
    )
    assert appended_logs.status_code == 200
    assert appended_logs.json()["data"]["task"]["status"] == "running"

    logs = client.get(
        f"/api/system/ai-executor-tasks/{task_id}/logs",
        headers=admin_headers,
    )
    assert logs.status_code == 200
    assert [entry["sequence"] for entry in logs.json()["data"]["logs"]] == [1, 2]
    assert logs.json()["data"]["logs"][1]["message"] == "scan started"

    cancelled = client.post(
        f"/api/system/ai-executor-tasks/{task_id}/cancel",
        json={"reason": "用户手动停止"},
        headers=admin_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["task"]["status"] == "cancelled"
    assert cancelled.json()["data"]["task"]["error_code"] == "AI_EXECUTOR_TASK_CANCELLED"

    timed_out_task = client.post(
        f"/api/system/plugin-actions/{action['id']}/invoke",
        json={"input_payload": {"source": "manual-timeout"}},
        headers=admin_headers,
    ).json()["data"]
    timed_out_task_id = timed_out_task["response_summary"]["json"]["runner_task_id"]
    scanned = client.post(
        "/api/system/ai-executor-tasks/timeout-scan",
        json={"now": "2099-01-01T00:00:00+00:00"},
        headers=admin_headers,
    )
    assert scanned.status_code == 200
    assert timed_out_task_id in scanned.json()["data"]["timed_out_task_ids"]

    timeout_logs = client.get(
        f"/api/system/ai-executor-tasks/{timed_out_task_id}/logs",
        headers=admin_headers,
    ).json()["data"]
    assert timeout_logs["task"]["status"] == "timed_out"
    assert timeout_logs["task"]["error_code"] == "AI_EXECUTOR_TASK_TIMEOUT"


def test_scheduled_ai_executor_runner_completion_updates_run_detail():
    app.state.store.reset()
    admin_headers = auth_headers()
    client.get("/api/system/plugin-marketplace", headers=admin_headers)

    runner = client.post(
        "/api/system/ai-executor-runners",
        json={
            "executor_types": ["openclaw"],
            "name": "OpenClaw 本地执行器",
            "protocol": "runner_polling",
            "runner_token": "runner-secret",
            "workspace_roots": ["/Users/zeek/source/e-ai-brain"],
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "runner://ai-executor",
            "environment": "dev",
            "name": "OpenClaw Runner 连接",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "query": {
                    "executor_type": "openclaw",
                    "runner_id": runner["id"],
                    "workspace_root": "/Users/zeek/source/e-ai-brain",
                },
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "mcp_tool",
            "code": "openclaw_code_scan",
            "connection_id": connection["id"],
            "name": "OpenClaw 代码扫描",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "instruction": "定期扫描仓库质量、安全和规范问题，输出 JSON。",
                "tool_name": "ai_executor.run_instruction",
            },
            "result_mapping": {"write_target": "scheduled_job_result"},
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
            "name": "OpenClaw 定时巡检",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "schedule_type": "manual",
            "source_system": "ai_executor",
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )
    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "running"
    assert run["finished_at"] is None
    runner_node = run["result_summary"]["execution_nodes"]["runner_execution"]
    assert runner_node["executor_type"] == "openclaw"
    assert runner_node["status"] == "queued"
    assert run["result_summary"]["execution_nodes"]["result_action"]["status"] == "waiting_runner"
    task_id = runner_node["runner_task_id"]

    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "openclaw", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert claimed.status_code == 200
    assert claimed.json()["data"]["task"]["id"] == task_id

    completed = client.post(
        f"/api/system/ai-executor-tasks/{task_id}/complete",
        json={
            "logs": [{"level": "info", "message": "openclaw scan finished"}],
            "result_json": {
                "finding_count": 2,
                "records_imported": 2,
                "summary": "发现 2 个中风险规范问题",
            },
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200

    runs = client.get(
        f"/api/system/scheduled-job-runs?scheduled_job_id={job['id']}",
        headers=admin_headers,
    ).json()["data"]
    completed_run = runs["items"][0]
    assert completed_run["id"] == run["id"]
    assert completed_run["status"] == "succeeded"
    assert completed_run["records_imported"] == 2
    completed_runner_node = completed_run["result_summary"]["execution_nodes"]["runner_execution"]
    assert completed_runner_node["status"] == "succeeded"
    assert completed_runner_node["result_json"]["summary"] == "发现 2 个中风险规范问题"
    result_action = completed_run["result_summary"]["execution_nodes"]["result_action"]
    assert result_action["status"] == "succeeded"
    assert result_action["feedback"]["runner_result"]["finding_count"] == 2


def test_result_write_targets_registry_drives_action_mapping_forms():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.get(
        "/api/system/result-write-targets",
        headers=admin_headers,
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    by_code = {item["code"]: item for item in items}
    assert set(by_code) >= {
        "code_inspection_reports",
        "email_notifications",
        "scheduled_job_result",
        "user_feedback_insights",
    }
    code_inspection = by_code["code_inspection_reports"]
    assert code_inspection["label"] == "代码巡检报告"
    assert code_inspection["form_label"] == "代码巡检报告"
    assert code_inspection["default_result_mapping"] == {
        "branch_path": "$.branch",
        "commit_sha_path": "$.commit_sha",
        "findings_path": "$.findings",
        "repository_id_path": "$.repository_id",
        "risk_level_path": "$.risk_level",
        "summary_path": "$.summary",
        "write_target": "code_inspection_reports",
    }
    assert code_inspection["mapping_fields"][0] == {
        "description": "代码问题列表所在路径。",
        "key": "findings_path",
        "label": "Finding 列表 JSONPath",
        "placeholder": "$.findings",
        "required": True,
    }
    email = by_code["email_notifications"]
    assert email["default_result_mapping"]["recipients_path"] == "$.recipients"
    assert email["mapping_fields"][0]["required"] is True


def test_plugin_resources_delete_requires_unused_dependencies():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin, connection, action = create_plugin_bundle(admin_headers)

    blocked_plugin_delete = client.delete(
        f"/api/system/plugins/{plugin['id']}",
        headers=admin_headers,
    )
    assert blocked_plugin_delete.status_code == 409
    assert "正在被使用" in blocked_plugin_delete.text
    assert "连接" in blocked_plugin_delete.text
    assert "动作" in blocked_plugin_delete.text

    blocked_connection_delete = client.delete(
        f"/api/system/plugin-connections/{connection['id']}",
        headers=admin_headers,
    )
    assert blocked_connection_delete.status_code == 409
    assert "动作" in blocked_connection_delete.text

    deleted_action = client.delete(
        f"/api/system/plugin-actions/{action['id']}",
        headers=admin_headers,
    )
    assert deleted_action.status_code == 200
    assert deleted_action.json()["data"] == {"deleted": True, "id": action["id"]}

    deleted_connection = client.delete(
        f"/api/system/plugin-connections/{connection['id']}",
        headers=admin_headers,
    )
    assert deleted_connection.status_code == 200
    assert deleted_connection.json()["data"] == {"deleted": True, "id": connection["id"]}

    deleted_plugin = client.delete(
        f"/api/system/plugins/{plugin['id']}",
        headers=admin_headers,
    )
    assert deleted_plugin.status_code == 200
    assert deleted_plugin.json()["data"] == {"deleted": True, "id": plugin["id"]}

    audit_events = client.get("/api/audit/events", headers=admin_headers).json()["data"]["items"]
    event_types = [event["event_type"] for event in audit_events]
    assert "plugin_action.deleted" in event_types
    assert "plugin_connection.deleted" in event_types
    assert "plugin.deleted" in event_types


def test_plugin_connection_patch_preserves_masked_secret_values():
    app.state.store.reset()
    admin_headers = auth_headers()
    _, connection, _ = create_plugin_bundle(admin_headers)

    response = client.patch(
        f"/api/system/plugin-connections/{connection['id']}",
        json={
            "auth_config": {"header_name": "PRIVATE-TOKEN", "secret_ref": "***"},
            "name": "测试 GitLab 更新",
            "request_config": {
                "headers": {
                    "Authorization": "***",
                    "X-Connection-Source": "connection-default-updated",
                },
                "query": connection["request_config"]["query"],
            },
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    patched = response.json()["data"]
    assert patched["name"] == "测试 GitLab 更新"
    persisted = app.state.store.plugin_connections[connection["id"]]
    assert persisted["auth_config"]["secret_ref"] == "vault/gitlab/token"
    assert persisted["request_config"]["headers"]["Authorization"] == "APPCODE connection-secret"
    assert (
        persisted["request_config"]["headers"]["X-Connection-Source"]
        == "connection-default-updated"
    )


def test_plugin_category_must_use_predefined_values():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.post(
        "/api/system/plugins",
        json={
            "category": "free_text_category",
            "code": "free_text_plugin",
            "name": "自由文本分类插件",
            "protocol": "http",
            "status": "active",
        },
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert "Unsupported category" in response.text


def test_standard_plugins_are_seeded_and_immutable():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.get("/api/system/plugins", headers=admin_headers)
    assert response.status_code == 200
    plugins = response.json()["data"]["items"]
    by_code = {plugin["code"]: plugin for plugin in plugins}
    assert by_code["gitlab"]["is_system"] is True
    assert by_code["gitlab"]["category"] == "devops"
    assert by_code["gitlab"]["protocol"] == "http"
    assert by_code["github"]["is_system"] is True
    assert by_code["github"]["category"] == "devops"
    assert by_code["github"]["protocol"] == "http"
    assert by_code["email"]["is_system"] is True
    assert by_code["email"]["category"] == "collaboration"
    assert by_code["email"]["protocol"] == "http"
    assert by_code["ai_executor"]["is_system"] is True
    assert by_code["ai_executor"]["category"] == "ai_service"
    assert by_code["ai_executor"]["protocol"] == "runner_polling"

    patch_response = client.patch(
        f"/api/system/plugins/{by_code['gitlab']['id']}",
        json={"name": "被修改的 GitLab"},
        headers=admin_headers,
    )
    assert patch_response.status_code == 409
    assert "官方标准插件" in patch_response.text

    delete_response = client.delete(
        f"/api/system/plugins/{by_code['github']['id']}",
        headers=admin_headers,
    )
    assert delete_response.status_code == 409
    assert "官方标准插件" in delete_response.text

    email_patch_response = client.patch(
        f"/api/system/plugins/{by_code['email']['id']}",
        json={"name": "被修改的邮箱"},
        headers=admin_headers,
    )
    assert email_patch_response.status_code == 409
    assert "官方标准插件" in email_patch_response.text

    ai_executor_patch_response = client.patch(
        f"/api/system/plugins/{by_code['ai_executor']['id']}",
        json={"name": "被修改的 AI 执行器"},
        headers=admin_headers,
    )
    assert ai_executor_patch_response.status_code == 409
    assert "官方标准插件" in ai_executor_patch_response.text


def test_legacy_maxcompute_standard_plugin_is_demoted_to_custom_http_plugin():
    app.state.store.reset()
    admin_headers = auth_headers()
    app.state.store.integration_plugins["plugin_standard_aliyun_maxcompute"] = {
        "category": "data_warehouse",
        "code": "aliyun_maxcompute",
        "description": "官方标准阿里云 MaxCompute 插件",
        "id": "plugin_standard_aliyun_maxcompute",
        "is_system": True,
        "name": "阿里云 MaxCompute",
        "protocol": "mcp_http",
        "risk_level": "high",
        "status": "active",
        "template_version": "v1",
    }

    response = client.get("/api/system/plugins", headers=admin_headers)

    assert response.status_code == 200
    by_code = {plugin["code"]: plugin for plugin in response.json()["data"]["items"]}
    maxcompute = by_code["aliyun_maxcompute"]
    assert maxcompute["is_system"] is False
    assert maxcompute["protocol"] == "http"
    assert maxcompute["version_status"] == "custom"

    patch_response = client.patch(
        f"/api/system/plugins/{maxcompute['id']}",
        json={"name": "阿里云 MaxCompute HTTP"},
        headers=admin_headers,
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["name"] == "阿里云 MaxCompute HTTP"


def test_standard_plugin_can_be_copied_as_custom_plugin_for_extension():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugins = client.get("/api/system/plugins", headers=admin_headers).json()["data"]["items"]
    github = {plugin["code"]: plugin for plugin in plugins}["github"]

    copy_response = client.post(
        f"/api/system/plugins/{github['id']}/copy",
        json={"code": "github_enterprise_custom", "name": "GitHub 企业版扩展"},
        headers=admin_headers,
    )

    assert copy_response.status_code == 200
    copied = copy_response.json()["data"]
    assert copied["code"] == "github_enterprise_custom"
    assert copied["name"] == "GitHub 企业版扩展"
    assert copied["is_system"] is False
    assert copied["source_plugin_id"] == github["id"]
    assert copied["template_version"] == "v1"
    assert copied["version_status"] == "custom"

    patch_response = client.patch(
        f"/api/system/plugins/{copied['id']}",
        json={"description": "可按企业规范自定义"},
        headers=admin_headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["data"]["description"] == "可按企业规范自定义"


def test_standard_plugin_connections_store_platform_parameters():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugins = client.get("/api/system/plugins", headers=admin_headers).json()["data"]["items"]
    by_code = {plugin["code"]: plugin for plugin in plugins}

    gitlab_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {
                "header_name": "PRIVATE-TOKEN",
                "secret_ref": "vault/gitlab/prod-token",
            },
            "auth_type": "api_key_header",
            "endpoint_url": "http://gitlab.local",
            "environment": "prod",
            "name": "生产 GitLab",
            "plugin_id": by_code["gitlab"]["id"],
            "request_config": {
                "headers": {"X-GitLab-Instance": "corp"},
                "query": {
                    "gitlab_project_url": "http://gitlab.local/rd-platform/ai-brain.git",
                },
            },
            "status": "active",
        },
        headers=admin_headers,
    )
    assert gitlab_connection.status_code == 200
    assert gitlab_connection.json()["data"]["auth_config"]["header_name"] == "PRIVATE-TOKEN"
    assert gitlab_connection.json()["data"]["endpoint_url"] == "http://gitlab.local"
    gitlab_query = gitlab_connection.json()["data"]["request_config"]["query"]
    assert gitlab_query["api_version"] == "v4"
    assert gitlab_query["group_id"] == "rd-platform"
    assert gitlab_query["project_id"] == "rd-platform%2Fai-brain"
    assert gitlab_query["project_path"] == "rd-platform/ai-brain"
    assert "gitlab_project_url" not in gitlab_query

    github_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {"token_ref": "vault/github/prod-token"},
            "auth_type": "bearer",
            "endpoint_url": "https://api.github.com",
            "environment": "prod",
            "name": "生产 GitHub",
            "plugin_id": by_code["github"]["id"],
            "request_config": {
                "headers": {"Accept": "application/vnd.github+json"},
                "query": {
                    "api_version": "2022-11-28",
                    "repository_url": "https://github.com/acme/ai-brain.git",
                },
            },
            "status": "active",
        },
        headers=admin_headers,
    )
    assert github_connection.status_code == 200
    assert github_connection.json()["data"]["auth_type"] == "bearer"
    github_query = github_connection.json()["data"]["request_config"]["query"]
    assert github_query["api_version"] == "2022-11-28"
    assert github_query["owner"] == "acme"
    assert github_query["repo"] == "ai-brain"
    assert "repository_url" not in github_query

    email_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {
                "header_name": "Authorization",
                "secret_ref": "vault/email/prod-token",
            },
            "auth_type": "api_key_header",
            "endpoint_url": "https://mail-gateway.example.com/api/send",
            "environment": "prod",
            "name": "生产邮件网关",
            "plugin_id": by_code["email"]["id"],
            "request_config": {
                "headers": {"Content-Type": "application/json"},
                "query": {
                    "default_from": "noreply@example.com",
                    "mail_provider": "enterprise_mail_gateway",
                },
            },
            "status": "active",
        },
        headers=admin_headers,
    )
    assert email_connection.status_code == 200
    email_data = email_connection.json()["data"]
    assert email_data["auth_type"] == "api_key_header"
    assert email_data["auth_config"]["header_name"] == "Authorization"
    assert email_data["request_config"]["headers"]["Content-Type"] == "application/json"
    assert email_data["request_config"]["query"]["mail_provider"] == "enterprise_mail_gateway"


def test_plugin_connection_environment_must_use_predefined_values():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin, _, _ = create_plugin_bundle(admin_headers)

    response = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://example.com",
            "environment": "production-cn",
            "name": "非法环境连接",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert "Unsupported environment" in response.text


def test_plugin_connections_can_be_filtered_by_environment():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin, test_connection, _ = create_plugin_bundle(admin_headers)
    prod_connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://gitlab-prod.example.com",
            "environment": "prod",
            "name": "生产 GitLab",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.get(
        f"/api/system/plugin-connections?plugin_id={plugin['id']}&environment=prod",
        headers=admin_headers,
    )
    payload = response.json()["data"]

    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == prod_connection["id"]
    assert payload["items"][0]["environment"] == "prod"
    assert test_connection["id"] not in {item["id"] for item in payload["items"]}

    invalid = client.get(
        "/api/system/plugin-connections?environment=production-cn",
        headers=admin_headers,
    )
    assert invalid.status_code == 400
    assert "Unsupported environment" in invalid.text


def test_plugin_connection_can_be_tested_with_structured_result_and_audit():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin, _, _ = create_plugin_bundle(admin_headers)
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {"mock_test_response": {"ok": True}},
            "auth_type": "none",
            "endpoint_url": "https://maxcompute.example.com/mcp",
            "environment": "sandbox",
            "name": "沙箱 MaxCompute",
            "plugin_id": plugin["id"],
            "request_config": {
                "headers": {"X-Request-Source": "connection-test"},
                "query": {"appCode": "demo", "start_pt": "{{current_date-7}}"},
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        f"/api/system/plugin-connections/{connection['id']}/test",
        headers=admin_headers,
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "succeeded"
    assert result["mocked"] is True
    assert result["environment"] == "sandbox"
    assert result["protocol"] == "http"
    assert result["request_summary"]["auth_config"]["mock_test_response"]["ok"] is True
    assert (
        result["request_summary"]["request_config"]["headers"]["X-Request-Source"]
        == "connection-test"
    )
    assert result["request_summary"]["request_config"]["query"]["appCode"] == "demo"
    assert result["request_summary"]["headers"]["X-Request-Source"] == "connection-test"
    assert (
        result["request_summary"]["header_sources"]["X-Request-Source"]
        == "request_config.headers"
    )
    assert (
        result["request_summary"]["curl_command"]
        == "curl -X GET -H 'X-Request-Source: connection-test' "
        "'https://maxcompute.example.com/mcp?appCode=demo&start_pt="
        f"{result['request_summary']['query']['start_pt']}'"
    )
    assert result["request_summary"]["masked_placeholder_headers"] == []
    assert result["request_summary"]["query"]["start_pt"].isdigit()
    assert (
        result["request_summary"]["original_request_config"]["query"]["start_pt"]
        == "{{current_date-7}}"
    )
    assert result["request_summary"]["variable_resolution_timezone"] == "UTC"
    assert result["request_summary"]["variable_resolutions"] == [
        {
            "expression": "{{current_date-7}}",
            "name": "current_date",
            "normalized_expression": "{{current_date-7}}",
            "offset_days": -7,
            "path": "query.start_pt",
            "resolved_text": result["request_summary"]["query"]["start_pt"],
            "resolved_value": result["request_summary"]["query"]["start_pt"],
            "status": "resolved",
            "token": "{{current_date-7}}",
        },
    ]
    assert result["action_template_draft"] == {
        "action_type": "http_request",
        "code": "test_sandbox_maxcompute",
        "connection_id": connection["id"],
        "description": "由连接测试请求回放生成，请确认请求路径、Params、Headers 和结果映射后保存。",
        "name": "沙箱 MaxCompute 请求动作",
        "plugin_id": plugin["id"],
        "request_config": {
            "headers": {"X-Request-Source": "connection-test"},
            "method": "GET",
            "path": "/mcp",
            "query": {"appCode": "demo", "start_pt": "{{current_date-7}}"},
        },
        "requires_human_review": False,
        "result_mapping": {"write_target": "scheduled_job_result"},
        "status": "draft",
    }
    assert result["repair_suggestions"] == []
    assert result["test_history"][0]["checked_at"] == result["checked_at"]
    assert result["test_history"][0]["status"] == "succeeded"
    history_request = result["test_history"][0]["request_summary"]
    assert history_request["url"] == result["request_summary"]["url"]
    assert history_request["original_request_config"]["query"]["start_pt"] == "{{current_date-7}}"
    assert result["test_history"][0]["action_template_draft"]["code"] == "test_sandbox_maxcompute"
    assert "{{" not in result["request_summary"]["url"]
    assert result["response_summary"] == {}
    assert [step["name"] for step in result["diagnostics"]] == [
        "endpoint_configured",
        "protocol_supported",
        "auth_configured",
        "network_request",
    ]
    assert result["diagnostics"][-1]["status"] == "mocked"

    listed_after_test = client.get(
        f"/api/system/plugin-connections?plugin_id={plugin['id']}",
        headers=admin_headers,
    ).json()["data"]
    listed_connection = listed_after_test["items"][0]
    assert listed_connection["last_test_summary"] == {
        "checked_at": result["checked_at"],
        "error_code": None,
        "error_message": None,
        "failed_step": None,
        "latency_ms": result["latency_ms"],
        "mocked": True,
        "response_status_code": None,
        "status": "succeeded",
    }
    assert listed_connection["test_history"][0]["checked_at"] == result["checked_at"]
    listed_history_request = listed_connection["test_history"][0]["request_summary"]
    assert listed_history_request["url"] == result["request_summary"]["url"]

    audit_events = client.get("/api/audit/events", headers=admin_headers).json()["data"]["items"]
    assert "plugin_connection.test_succeeded" in [event["event_type"] for event in audit_events]


def test_plugin_connection_test_generates_repair_suggestions_for_failed_response(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin, _, _ = create_plugin_bundle(admin_headers)
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {},
            "auth_type": "none",
            "endpoint_url": "https://maxcompute.example.com/api",
            "environment": "prod",
            "name": "生产 MaxCompute API",
            "plugin_id": plugin["id"],
            "request_config": {
                "headers": {"Authorization": "***"},
                "query": {"start_pt": "{{current_date-7}}"},
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    def fake_urlopen(request, timeout):
        raise plugin_services.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr(plugin_services, "urlopen", fake_urlopen)

    response = client.post(
        f"/api/system/plugin-connections/{connection['id']}/test",
        headers=admin_headers,
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "failed"
    assert result["repair_suggestions"] == [
        {
            "code": "masked_header_placeholder",
            "detail": (
                "最终请求 Header 仍包含 *** 占位，请填写真实 Header 值，"
                "或把 Authorization/API Key 放到认证配置中统一生成。"
            ),
            "title": "替换脱敏 Header 占位",
        },
        {
            "code": "http_400_request_parameters",
            "detail": (
                "远端返回 HTTP 400，优先检查 Params、Headers、动态日期分区"
                "和请求路径是否符合第三方接口要求。"
            ),
            "title": "检查请求参数和日期分区",
        },
    ]
    assert result["test_history"][0]["repair_suggestions"] == result["repair_suggestions"]


def test_plugin_connection_test_auth_config_overrides_masked_authorization_header(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "aliyun_maxcompute_gateway",
            "name": "阿里云 MaxCompute 网关",
            "protocol": "http",
            "risk_level": "high",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {
                "header_name": "Authorization",
                "secret_ref": "APPCODE real-authorization",
            },
            "auth_type": "api_key_header",
            "endpoint_url": "https://example.aliyunapi.com/zqf_api/feedback",
            "environment": "prod",
            "name": "生产 MaxCompute API",
            "plugin_id": plugin["id"],
            "request_config": {
                "headers": {"Authorization": "***"},
                "query": {"start_pt": "{{current_date-7}}"},
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    captured: dict[str, object] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self, size=-1):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(plugin_services, "urlopen", fake_urlopen)

    response = client.post(
        f"/api/system/plugin-connections/{connection['id']}/test",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert captured["headers"]["Authorization"] == "APPCODE real-authorization"
    result = response.json()["data"]
    assert result["status"] == "succeeded"
    assert result["request_summary"]["headers"]["Authorization"] == "APPCODE real-authorization"
    assert (
        result["request_summary"]["header_sources"]["Authorization"]
        == "auth_config.api_key_header"
    )
    assert result["request_summary"]["masked_placeholder_headers"] == []
    assert "{{" not in str(captured["url"])


def test_plugin_connection_test_sends_plain_authorization_without_auth_config(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "aliyun_maxcompute_header_only",
            "name": "阿里云 MaxCompute Header",
            "protocol": "http",
            "risk_level": "high",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://example.aliyunapi.com/zqf_api/feedback",
            "environment": "prod",
            "name": "Header-only MaxCompute API",
            "plugin_id": plugin["id"],
            "request_config": {
                "headers": {"Authorization": "***"},
                "query": {"start_pt": "{{current_date-7}}"},
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    captured: dict[str, object] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self, size=-1):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(plugin_services, "urlopen", fake_urlopen)

    response = client.post(
        f"/api/system/plugin-connections/{connection['id']}/test",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert captured["headers"]["Authorization"] == "***"
    result = response.json()["data"]
    assert result["status"] == "succeeded"
    assert result["error_code"] is None
    assert result["request_summary"]["headers"]["Authorization"] == "***"
    assert result["request_summary"]["masked_placeholder_headers"] == ["Authorization"]
    assert "{{" not in str(captured["url"])
    assert all(step["name"] != "request_headers_valid" for step in result["diagnostics"])


def test_plugin_system_variables_preview_includes_date_offsets():
    app.state.store.reset()
    admin_headers = auth_headers()

    response = client.get(
        "/api/system/plugin-system-variables?timezone=Asia/Shanghai",
        headers=admin_headers,
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["timezone"] == "Asia/Shanghai"
    expressions = {item["expression"]: item for item in result["items"]}
    assert "{{current_date-7}}" in expressions
    assert expressions["{{current_date-7}}"]["value"].isdigit()


def test_plugin_input_mapping_resolves_dynamic_time_tokens_by_job_timezone():
    mapping = {
        "current_pt": "{{current_date}}",
        "date_iso": "{{date_iso-7}}",
        "nested": {"started_at": "{{today.start}}"},
        "start_pt": "{{current_date-7}}",
        "today_start_minus_7": "{{today.start-7}}",
        "week_end": "{{last_full_week.end}}",
        "week_start": "{{last_full_week.start}}",
    }

    resolved = resolve_plugin_input_mapping(
        mapping,
        {"timezone": "Asia/Shanghai"},
        now=datetime(2026, 6, 10, 8, 30, tzinfo=UTC),
    )

    assert resolved["current_pt"] == "20260610"
    assert resolved["date_iso"] == "2026-06-03"
    assert resolved["start_pt"] == "20260603"
    assert resolved["today_start_minus_7"] == "2026-06-03T00:00:00+08:00"
    assert resolved["week_start"] == "2026-06-01T00:00:00+08:00"
    assert resolved["week_end"] == "2026-06-08T00:00:00+08:00"
    assert resolved["nested"]["started_at"] == "2026-06-10T00:00:00+08:00"


def test_plugin_action_request_config_resolves_system_variable_expressions():
    action = {
        "request_config": {
            "headers": {"X-Run-Date": "{{current_date}}"},
            "method": "GET",
            "path": "/zqf_api/feedback",
            "query": {
                "end_pt": "{{current_date}}",
                "start_pt": "{{current_date-7}}",
                "window_start": "{{today.start-7}}",
            },
        },
    }

    resolved = resolve_action_request_config(
        action,
        {"timezone": "Asia/Shanghai"},
        now=datetime(2026, 6, 10, 8, 30, tzinfo=UTC),
    )

    assert resolved["headers"]["X-Run-Date"] == "20260610"
    assert resolved["query"]["end_pt"] == "20260610"
    assert resolved["query"]["start_pt"] == "20260603"
    assert resolved["query"]["window_start"] == "2026-06-03T00:00:00+08:00"


def test_records_imported_mapping_counts_array_values():
    response_summary = {"json": {"data": {"rows": [{"id": 1}, {"id": 2}]}}}

    assert (
        records_imported_from_mapping(
            response_summary,
            {"records_imported_path": "$.data.rows"},
        )
        == 2
    )
    assert (
        records_imported_from_mapping(
            {"json": [{"id": 1}, {"id": 2}, {"id": 3}]},
            {"records_imported_path": "$"},
        )
        == 3
    )


def test_plugin_action_trial_returns_request_preview_and_mapping_hits():
    app.state.store.reset()
    admin_headers = auth_headers()
    _, connection, action = create_plugin_bundle(admin_headers)

    response = client.post(
        f"/api/system/plugin-actions/{action['id']}/trial",
        json={
            "connection_id": connection["id"],
            "input_payload": {"timezone": "Asia/Shanghai"},
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "succeeded"
    assert result["request_preview"]["method"] == "GET"
    assert result["request_preview"]["headers"]["X-Action-Source"] == "action-default"
    assert result["request_preview"]["headers"]["X-Connection-Source"] == "connection-default"
    assert result["request_preview"]["headers"]["X-Override"] == "action"
    assert result["request_preview"]["headers"]["PRIVATE-TOKEN"] == "vault/gitlab/token"
    assert result["request_preview"]["query"] == {
        "metric": "daily",
        "scope": "action",
        "shared_token": "gitlab",
    }
    assert result["response_summary"]["json"]["commits"] == 8
    assert result["mapping_hits"] == [
        {
            "key": "records_imported_path",
            "matched": True,
            "path": "$.commits",
            "value_preview": 8,
        }
    ]
    assert result["write_preview"] == {
        "candidate_count": 0,
        "preview_value": 8,
        "records_imported": 8,
        "sample_records": [],
        "write_target": "scheduled_job_result",
        "write_target_label": "定时作业结果",
    }
    audit_events = client.get(
        f"/api/audit/events?event_type=plugin_action.trial_succeeded&subject_id={action['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    audit_payload = audit_events[0]["payload"]
    assert audit_payload == {
        "action_code": "fetch_daily_metrics",
        "action_id": action["id"],
        "connection_environment": "test",
        "connection_id": connection["id"],
        "error_code": None,
        "input_keys": ["timezone"],
        "latency_ms": audit_payload["latency_ms"],
        "plugin_code": "gitlab_metrics",
        "plugin_id": action["plugin_id"],
        "status": "succeeded",
        "write_target": "scheduled_job_result",
    }
    assert isinstance(audit_payload["latency_ms"], int)
    assert "vault/gitlab/token" not in str(audit_events)
    assert "PRIVATE-TOKEN" not in str(audit_events)


def test_plugin_action_trial_failure_writes_lightweight_audit():
    app.state.store.reset()
    admin_headers = auth_headers()

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "devops",
            "code": "local_scanner",
            "name": "本地扫描器",
            "protocol": "mcp_stdio",
            "risk_level": "high",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "stdio://local-scanner",
            "environment": "sandbox",
            "name": "沙箱本地扫描器",
            "plugin_id": plugin["id"],
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "mcp_tool",
            "code": "scan_local_repository",
            "connection_id": connection["id"],
            "name": "扫描本地仓库",
            "plugin_id": plugin["id"],
            "request_config": {"tool_name": "scanner.scan_repository"},
            "result_mapping": {"write_target": "code_inspection_reports"},
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        f"/api/system/plugin-actions/{action['id']}/trial",
        json={
            "connection_id": connection["id"],
            "input_payload": {"repository": "rd-brain", "secret": "do-not-persist"},
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "failed"
    assert result["error_code"] == "PLUGIN_PROTOCOL_UNSUPPORTED"
    assert result["write_preview"]["write_target"] == "code_inspection_reports"

    audit_events = client.get(
        f"/api/audit/events?event_type=plugin_action.trial_failed&subject_id={action['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    audit_payload = audit_events[0]["payload"]
    assert audit_payload == {
        "action_code": "scan_local_repository",
        "action_id": action["id"],
        "connection_environment": "sandbox",
        "connection_id": connection["id"],
        "error_code": "PLUGIN_PROTOCOL_UNSUPPORTED",
        "input_keys": ["repository", "secret"],
        "latency_ms": audit_payload["latency_ms"],
        "plugin_code": "local_scanner",
        "plugin_id": plugin["id"],
        "status": "failed",
        "write_target": "code_inspection_reports",
    }
    assert isinstance(audit_payload["latency_ms"], int)
    assert "do-not-persist" not in str(audit_events)
    assert "scanner.scan_repository" not in str(audit_events)


def test_plugin_action_trial_returns_write_preview_for_code_inspection_mapping():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin, connection, _ = create_plugin_bundle(admin_headers)

    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "scan_repository_alerts",
            "connection_id": connection["id"],
            "input_schema": {"type": "object"},
            "name": "扫描仓库告警",
            "output_schema": {"type": "object"},
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "GET",
                "mock_response_json": {
                    "payload": {
                        "alerts": [
                            {
                                "file_path": "src/config.py",
                                "line_number": 12,
                                "rule_id": "SEC001",
                                "severity": "critical",
                                "title": "Hardcoded key",
                            }
                        ],
                        "branch": "main",
                        "commit": "abc1234",
                        "repository": "repo_001",
                        "risk": "critical",
                        "summary": "1 critical issue found.",
                    }
                },
                "path": "/alerts",
            },
            "result_mapping": {
                "branch_path": "$.payload.branch",
                "commit_sha_path": "$.payload.commit",
                "findings_path": "$.payload.alerts",
                "repository_id_path": "$.payload.repository",
                "risk_level_path": "$.payload.risk",
                "summary_path": "$.payload.summary",
                "write_target": "code_inspection_reports",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        f"/api/system/plugin-actions/{action['id']}/trial",
        headers=admin_headers,
        json={"connection_id": connection["id"], "input_payload": {}},
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["write_preview"] == {
        "candidate_count": 1,
        "records_imported": 1,
        "report_preview": {
            "branch": "main",
            "commit_sha": "abc1234",
            "repository_id": "repo_001",
            "risk_level": "critical",
            "summary": "1 critical issue found.",
        },
        "sample_records": [
            {
                "file_path": "src/config.py",
                "line_number": 12,
                "rule_id": "SEC001",
                "severity": "critical",
                "title": "Hardcoded key",
            }
        ],
        "write_target": "code_inspection_reports",
        "write_target_label": "代码巡检报告",
    }


def test_plugin_action_trial_returns_write_preview_for_email_notification_mapping():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugins = client.get("/api/system/plugins", headers=admin_headers).json()["data"]["items"]
    email_plugin = {plugin["code"]: plugin for plugin in plugins}["email"]

    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {
                "header_name": "Authorization",
                "secret_ref": "vault/email/prod-token",
            },
            "auth_type": "api_key_header",
            "endpoint_url": "https://mail-gateway.example.com/api",
            "environment": "prod",
            "name": "生产邮件网关",
            "plugin_id": email_plugin["id"],
            "request_config": {
                "headers": {"Content-Type": "application/json"},
                "query": {
                    "default_to": "owner@example.com",
                    "mail_provider": "enterprise_mail_gateway",
                },
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "send_email_notification",
            "connection_id": connection["id"],
            "name": "发送邮件通知",
            "plugin_id": email_plugin["id"],
            "request_config": {
                "method": "POST",
                "mock_response_json": {
                    "message_id": "mail_001",
                    "recipients": ["owner@example.com", "security@example.com"],
                    "status": "queued",
                    "subject": "代码巡检完成",
                },
                "path": "/messages/send",
            },
            "result_mapping": {
                "delivery_id_path": "$.message_id",
                "delivery_status_path": "$.status",
                "recipients_path": "$.recipients",
                "subject_path": "$.subject",
                "write_target": "email_notifications",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.post(
        f"/api/system/plugin-actions/{action['id']}/trial",
        headers=admin_headers,
        json={"connection_id": connection["id"], "input_payload": {}},
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["write_preview"] == {
        "candidate_count": 2,
        "delivery_id": "mail_001",
        "delivery_status": "queued",
        "records_imported": 1,
        "sample_records": ["owner@example.com", "security@example.com"],
        "subject": "代码巡检完成",
        "write_target": "email_notifications",
        "write_target_label": "邮件通知记录",
    }


def test_scheduled_job_can_invoke_configured_plugin_action_with_snapshots_and_logs():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin, connection, action = create_plugin_bundle(admin_headers)

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "deterministic",
            "interval_seconds": 3600,
            "job_type": "plugin_action_invoke",
            "name": "定时拉取 GitLab 指标",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "plugin_input_mapping": {"window": "last_success_to_now"},
            "plugin_output_mapping": {"records_imported_path": "$.commits"},
            "schedule_type": "interval",
            "source_system": "gitlab",
        },
        headers=admin_headers,
    )
    assert job.status_code == 200
    job_data = job.json()["data"]
    assert job_data["plugin_action_id"] == action["id"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job_data['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["plugin_invocation_log_id"].startswith("plugin_invocation_log_")
    assert run["resolved_plugin_snapshot"]["plugin"]["id"] == plugin["id"]
    assert (
        run["resolved_plugin_snapshot"]["connection"]["auth_config"]["secret_ref"]
        == "vault/gitlab/token"
    )
    assert run["resolved_plugin_snapshot"]["action"]["id"] == action["id"]
    assert run["result_summary"]["plugin"]["status"] == "succeeded"
    assert run["result_summary"]["plugin"]["response_summary"]["json"]["commits"] == 8
    run_request_preview = run["result_summary"]["plugin"]["request_summary"]["request_preview"]
    assert run_request_preview["headers"]["Authorization"] == "***"
    assert run_request_preview["headers"]["PRIVATE-TOKEN"] == "***"
    assert run_request_preview["headers"]["X-Action-Source"] == "action-default"

    logs = client.get(
        f"/api/system/plugin-invocation-logs?scheduled_job_id={job_data['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert logs["total"] == 1
    assert logs["items"][0]["id"] == run["plugin_invocation_log_id"]
    assert logs["items"][0]["status"] == "succeeded"
    log_request_preview = logs["items"][0]["request_summary"]["request_preview"]
    assert log_request_preview["headers"]["Authorization"] == "***"
    assert log_request_preview["headers"]["PRIVATE-TOKEN"] == "***"
    assert log_request_preview["headers"]["X-Connection-Source"] == "connection-default"


def test_scheduled_email_action_run_exposes_notification_write_preview():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugins = client.get("/api/system/plugins", headers=admin_headers).json()["data"]["items"]
    email_plugin = {plugin["code"]: plugin for plugin in plugins}["email"]

    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {
                "header_name": "Authorization",
                "secret_ref": "vault/email/prod-token",
            },
            "auth_type": "api_key_header",
            "endpoint_url": "https://mail-gateway.example.com/api",
            "environment": "prod",
            "name": "生产邮件网关",
            "plugin_id": email_plugin["id"],
            "request_config": {
                "headers": {"Content-Type": "application/json"},
                "query": {"default_to": "owner@example.com"},
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "send_email_notification",
            "connection_id": connection["id"],
            "name": "发送邮件通知",
            "plugin_id": email_plugin["id"],
            "request_config": {
                "headers": {"Content-Type": "application/json"},
                "method": "POST",
                "mock_response_json": {
                    "message_id": "mail_001",
                    "recipients": ["owner@example.com"],
                    "status": "queued",
                    "subject": "定时作业完成",
                },
                "path": "/messages/send",
                "query": {
                    "body_template": "{{result_summary}}",
                    "subject_template": "{{subject_template}}",
                    "to": "{{default_to}}",
                },
            },
            "result_mapping": {
                "delivery_id_path": "$.message_id",
                "delivery_status_path": "$.status",
                "recipients_path": "$.recipients",
                "subject_path": "$.subject",
                "write_target": "email_notifications",
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
            "name": "定时发送运行通知",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "schedule_type": "manual",
            "source_system": "email",
        },
        headers=admin_headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=admin_headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    result_action = run["result_summary"]["execution_nodes"]["result_action"]
    assert run["records_imported"] == 1
    assert result_action["records_imported"] == 1
    assert result_action["write_target"] == "email_notifications"
    assert result_action["write_target_label"] == "邮件通知记录"
    assert result_action["feedback"]["delivery_id"] == "mail_001"
    assert result_action["feedback"]["delivery_status"] == "queued"
    assert result_action["feedback"]["subject"] == "定时作业完成"
    assert result_action["feedback"]["sample_records"] == ["owner@example.com"]

    records_response = client.get(
        "/api/system/result-write-records?write_target=email_notifications",
        headers=admin_headers,
    )

    assert records_response.status_code == 200
    records_payload = records_response.json()["data"]
    assert records_payload["total"] == 1
    record = records_payload["items"][0]
    assert record["id"] == f"result_write_record_{run['id']}"
    assert record["write_target"] == "email_notifications"
    assert record["write_target_label"] == "邮件通知记录"
    assert record["status"] == "succeeded"
    assert record["source_type"] == "scheduled_job_run"
    assert record["scheduled_job_id"] == job["id"]
    assert record["scheduled_job_run_id"] == run["id"]
    assert record["plugin_action_id"] == action["id"]
    assert record["plugin_invocation_log_id"] == run["plugin_invocation_log_id"]
    assert record["records_imported"] == 1
    assert record["summary_fields"]["delivery_id"] == "mail_001"
    assert record["summary_fields"]["delivery_status"] == "queued"
    assert record["summary_fields"]["subject"] == "定时作业完成"
    assert record["summary_fields"]["sample_records"] == ["owner@example.com"]

    run_records_response = client.get(
        f"/api/system/result-write-records?scheduled_job_run_id={run['id']}",
        headers=admin_headers,
    )

    assert run_records_response.status_code == 200
    run_records_payload = run_records_response.json()["data"]
    assert run_records_payload["total"] == 1
    assert run_records_payload["items"][0]["id"] == f"result_write_record_{run['id']}"


def test_result_write_records_support_future_write_targets_from_action_logs():
    app.state.store.reset()
    admin_headers = auth_headers()
    plugin, connection, action = create_plugin_bundle(admin_headers)
    action["result_mapping"] = {
        "records_imported_path": "$.external_ticket_id",
        "write_target": "external_ticket_records",
    }
    app.state.store.plugin_actions[action["id"]] = action

    invoke_response = client.post(
        f"/api/system/plugin-actions/{action['id']}/invoke",
        headers=admin_headers,
        json={"connection_id": connection["id"], "input_payload": {}},
    )
    assert invoke_response.status_code == 200
    invocation_log = invoke_response.json()["data"]

    records_response = client.get(
        "/api/system/result-write-records?write_target=external_ticket_records",
        headers=admin_headers,
    )

    assert records_response.status_code == 200
    payload = records_response.json()["data"]
    assert payload["total"] == 1
    record = payload["items"][0]
    assert record["id"] == f"result_write_record_{invocation_log['id']}"
    assert record["write_target"] == "external_ticket_records"
    assert record["write_target_label"] == "external_ticket_records"
    assert record["source_type"] == "plugin_invocation_log"
    assert record["plugin_action_id"] == action["id"]
    assert record["plugin_invocation_log_id"] == invocation_log["id"]
    assert record["status"] == "succeeded"
    assert record["preview"]["write_target"] == "external_ticket_records"


def test_maxcompute_weekly_feedback_job_creates_user_feedback_insights(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "weekly_feedback_analysis",
            "name": "每周反馈分析",
            "prompt_template": "分析 MaxCompute 用户反馈明细，提取高价值用户洞察。",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    model_gateway = client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-scheduled-job",
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "scheduled-job-model",
            "name": "定时作业模型",
            "provider": "openai_compatible",
            "status": "active",
            "timeout_seconds": 12,
        },
        headers=admin_headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "weekly_feedback_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周反馈 Agent",
            "status": "active",
            "system_prompt": "你负责分析 MaxCompute 用户反馈数据并输出结构化洞察。",
        },
        headers=admin_headers,
    ).json()["data"]
    knowledge = client.post(
        "/api/knowledge/documents",
        json={
            "content": (
                "支付页提交后无响应时，应优先排查订单幂等锁、"
                "支付回调超时和前端按钮防重复提交状态。"
            ),
            "doc_type": "runbook",
            "permission_roles": ["admin"],
            "product_id": product["id"],
            "tags": ["支付体验", "排障知识"],
            "title": "支付页无响应排障知识",
        },
        headers=admin_headers,
    ).json()["data"]

    model_calls: list[dict[str, object]] = []

    class FakeModelResponse:
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
                                        "insights": [
                                            {
                                                "content": (
                                                    "AI 分析发现支付页提交后无响应集中出现，"
                                                    "建议优先排查试用转化阻断。"
                                                ),
                                                "feedback_type": "complaint",
                                                "product_id": product["id"],
                                                "sentiment": "negative",
                                                "source_channel": "maxcompute_weekly_ai",
                                                "tags": ["支付体验", "AI洞察"],
                                            }
                                        ],
                                        "row_count": 18,
                                    },
                                    ensure_ascii=False,
                                ),
                            },
                        },
                    ],
                    "usage": {"completion_tokens": 24, "prompt_tokens": 60, "total_tokens": 84},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_model_urlopen(request, timeout):
        model_calls.append(
            {
                "body": request.data.decode("utf-8"),
                "headers": dict(request.header_items()),
                "timeout": timeout,
                "url": request.full_url,
            },
        )
        return FakeModelResponse()

    monkeypatch.setattr(scheduled_jobs_service, "urlopen", fake_model_urlopen)

    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "data_warehouse",
            "code": "aliyun_maxcompute",
            "description": "通过 HTTP 查询 MaxCompute 用户反馈表",
            "name": "阿里云 MaxCompute",
            "protocol": "http",
            "risk_level": "high",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {},
            "auth_type": "none",
            "endpoint_url": "https://ai-brain-maxcompute-http.internal/app_data",
            "environment": "prod",
            "max_retries": 1,
            "name": "生产 MaxCompute HTTP",
            "plugin_id": plugin["id"],
            "status": "active",
            "timeout_seconds": 120,
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "fetch_weekly_user_feedback",
            "connection_id": connection["id"],
            "input_schema": {"type": "object"},
            "name": "获取本周用户反馈数据",
            "output_schema": {"type": "object"},
            "plugin_id": plugin["id"],
            "request_config": {
                "mock_response_json": {
                    "insights": [
                        {
                            "content": "本周 18 条反馈集中提到支付页提交后无响应，影响试用转化。",
                            "feedback_type": "complaint",
                            "product_id": product["id"],
                            "sentiment": "negative",
                            "source_channel": "maxcompute_weekly_ai",
                            "tags": ["支付体验", "高价值洞察"],
                        }
                    ],
                    "row_count": 18,
                },
                "method": "GET",
                "path": "",
                "query": {
                    "end_pt": "{{current_date}}",
                    "pageNum": "1",
                    "pageSize": "100",
                    "start_pt": "{{current_date-7}}",
                },
            },
            "result_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
                "write_target": "user_feedback_insights",
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "knowledge_document_ids": [knowledge["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "每周 MaxCompute 用户反馈洞察提取",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "plugin_input_mapping": {
                "time_field": "created_at",
                "week_end": "this_monday_00:00:00",
                "week_start": "last_monday_00:00:00",
            },
            "schedule_type": "cron",
            "cron_expression": "0 9 * * MON",
            "skill_ids": [skill["id"]],
            "source_system": "aliyun-maxcompute",
            "timezone": "Asia/Shanghai",
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
    assert run["records_imported"] == 1
    collector_run = app.state.store.collector_runs[run["collector_run_id"]]
    assert collector_run["collector_type"] == "user_feedback"
    assert run["result_summary"]["insights_created"] == 1
    assert run["result_summary"]["processing"]["skill_codes"] == ["weekly_feedback_analysis"]
    assert run["result_summary"]["plugin"]["response_summary"]["json"]["row_count"] == 18
    assert run["result_summary"]["write_target"] == "user_feedback_insights"
    assert model_calls and model_calls[0]["url"] == "https://llm.example.com/v1/chat/completions"
    assert model_calls[0]["timeout"] == 12
    model_body = json.loads(str(model_calls[0]["body"]))
    assert model_body["model"] == "scheduled-job-model"
    assert model_body["response_format"] == {"type": "json_object"}
    user_payload = json.loads(model_body["messages"][1]["content"])
    assert user_payload["knowledge_references"][0]["document_id"] == knowledge["id"]
    assert "支付页提交后无响应" in user_payload["knowledge_references"][0]["content"]
    execution_nodes = run["result_summary"]["execution_nodes"]
    assert execution_nodes["data_connection"]["connection_environment"] == "prod"
    assert execution_nodes["data_connection"]["records_imported"] == 18
    assert execution_nodes["data_connection"]["input_mapping"]["time_field"] == "created_at"
    request_preview = execution_nodes["data_connection"]["request_summary"]["request_preview"]
    assert request_preview["method"] == "GET"
    assert request_preview["protocol"] == "http"
    assert str(request_preview["query"]["start_pt"]).isdigit()
    assert str(request_preview["query"]["end_pt"]).isdigit()
    assert request_preview["url"].startswith("https://ai-brain-maxcompute-http.internal/app_data")
    assert execution_nodes["data_connection"]["response_summary"]["json"]["row_count"] == 18
    assert execution_nodes["skill_processing"]["status"] == "succeeded"
    assert execution_nodes["skill_processing"]["model_gateway_called"] is True
    assert (
        execution_nodes["skill_processing"]["input"]["knowledge_references"][0]["document_id"]
        == knowledge["id"]
    )
    assert execution_nodes["skill_processing"]["model_log_id"].startswith("model_log_")
    assert execution_nodes["skill_processing"]["processing_mode"] == "model_gateway_json_transform"
    assert execution_nodes["skill_processing"]["output"]["candidate_count"] == 1
    assert "AI 分析发现支付页提交后无响应" in str(
        execution_nodes["skill_processing"]["output"]["processed_json"],
    )
    assert execution_nodes["result_action"]["created_ids"][0].startswith("feedback_")
    assert execution_nodes["result_action"]["write_target"] == "user_feedback_insights"

    feedback_items = client.get(
        f"/api/insights/user-feedback?product_id={product['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert feedback_items["total"] == 1
    assert feedback_items["items"][0]["source_channel"] == "maxcompute_weekly_ai"
    assert "AI 分析发现支付页提交后无响应" in feedback_items["items"][0]["content"]

    run_audit_events = client.get(
        f"/api/audit/events?event_type=scheduled_job_run.succeeded&subject_id={run['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    audit_payload = run_audit_events[0]["payload"]
    assert audit_payload["agent_id"] == agent["id"]
    assert audit_payload["execution_mode"] == "ai_generated"
    assert audit_payload["job_type"] == "user_feedback_insight_extract"
    assert audit_payload["knowledge_document_ids"] == [knowledge["id"]]
    assert audit_payload["model_gateway_called"] is True
    assert audit_payload["model_gateway_config_id"] == model_gateway["id"]
    assert audit_payload["plugin_action_code"] == "fetch_weekly_user_feedback"
    assert audit_payload["plugin_action_id"] == action["id"]
    assert audit_payload["plugin_code"] == "aliyun_maxcompute"
    assert audit_payload["plugin_connection_environment"] == "prod"
    assert audit_payload["plugin_connection_id"] == connection["id"]
    assert audit_payload["plugin_invocation_log_id"] == run["plugin_invocation_log_id"]
    assert audit_payload["records_imported"] == 1
    assert audit_payload["result_write_target"] == "user_feedback_insights"
    assert audit_payload["scheduled_job_id"] == job["id"]
    assert audit_payload["skill_ids"] == [skill["id"]]
    assert audit_payload["status"] == "succeeded"
    assert audit_payload["trigger_type"] == "manual"
