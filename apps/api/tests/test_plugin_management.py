import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

import app.services.plugins as plugin_services
import app.services.scheduled_jobs as scheduled_jobs_service
from app.main import app
from app.services.plugins import records_imported_from_mapping, resolve_action_request_config
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
    assert result["request_summary"]["masked_placeholder_headers"] == []
    assert result["request_summary"]["query"]["start_pt"].isdigit()
    assert "{{" not in result["request_summary"]["url"]
    assert result["response_summary"] == {}
    assert [step["name"] for step in result["diagnostics"]] == [
        "endpoint_configured",
        "protocol_supported",
        "auth_configured",
        "network_request",
    ]
    assert result["diagnostics"][-1]["status"] == "mocked"

    audit_events = client.get("/api/audit/events", headers=admin_headers).json()["data"]["items"]
    assert "plugin_connection.test_succeeded" in [event["event_type"] for event in audit_events]


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

    logs = client.get(
        f"/api/system/plugin-invocation-logs?scheduled_job_id={job_data['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert logs["total"] == 1
    assert logs["items"][0]["id"] == run["plugin_invocation_log_id"]
    assert logs["items"][0]["status"] == "succeeded"


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
            "description": "通过 PyODPS 查询 MaxCompute 用户反馈表",
            "name": "阿里云 MaxCompute",
            "protocol": "mcp_http",
            "risk_level": "high",
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_config": {
                "header_name": "X-Internal-Token",
                "secret_ref": "vault/ai-brain/maxcompute-mcp-token",
            },
            "auth_type": "api_key_header",
            "endpoint_url": "https://ai-brain-maxcompute-mcp.internal/mcp",
            "environment": "prod",
            "max_retries": 1,
            "name": "生产 MaxCompute 项目",
            "plugin_id": plugin["id"],
            "status": "active",
            "timeout_seconds": 120,
        },
        headers=admin_headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "mcp_tool",
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
                "sql_template": (
                    "SELECT feedback_id, product_id, content, created_at FROM ods_user_feedback "
                    "WHERE created_at >= '${week_start}' AND created_at < '${week_end}' LIMIT 1000"
                ),
                "tool_name": "maxcompute.execute_sql",
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
    assert execution_nodes["data_connection"]["records_imported"] == 18
    assert execution_nodes["data_connection"]["input_mapping"]["time_field"] == "created_at"
    request_preview = execution_nodes["data_connection"]["request_summary"]["request_preview"]
    assert request_preview["tool_name"] == "maxcompute.execute_sql"
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
