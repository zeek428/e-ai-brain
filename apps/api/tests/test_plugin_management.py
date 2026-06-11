from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.services.plugins import resolve_action_request_config
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


def test_plugins_connections_and_actions_are_admin_managed_masked_and_audited():
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
    assert connection["auth_config"]["secret_ref"] == "***"
    assert "vault/gitlab/token" not in str(connection)
    assert action["connection_id"] == connection["id"]

    listed_connections = client.get(
        f"/api/system/plugin-connections?plugin_id={plugin['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert listed_connections["total"] == 1
    assert listed_connections["items"][0]["auth_config"]["secret_ref"] == "***"

    audit_events = client.get("/api/audit/events", headers=admin_headers).json()["data"]["items"]
    event_types = [event["event_type"] for event in audit_events]
    assert "plugin.created" in event_types
    assert "plugin_connection.created" in event_types
    assert "plugin_action.created" in event_types
    assert "vault/gitlab/token" not in str(audit_events)


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
    assert [step["name"] for step in result["diagnostics"]] == [
        "endpoint_configured",
        "protocol_supported",
        "auth_configured",
        "network_request",
    ]
    assert result["diagnostics"][-1]["status"] == "mocked"

    audit_events = client.get("/api/audit/events", headers=admin_headers).json()["data"]["items"]
    assert "plugin_connection.test_succeeded" in [event["event_type"] for event in audit_events]


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
    assert run["resolved_plugin_snapshot"]["connection"]["auth_config"]["secret_ref"] == "***"
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


def test_maxcompute_weekly_feedback_job_creates_user_feedback_insights():
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)

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
            },
            "status": "active",
        },
        headers=admin_headers,
    ).json()["data"]
    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "name": "每周 MaxCompute 用户反馈洞察提取",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "plugin_input_mapping": {
                "time_field": "created_at",
                "week_end": "this_monday_00:00:00",
                "week_start": "last_monday_00:00:00",
            },
            "plugin_output_mapping": {
                "insights_path": "$.insights",
                "records_imported_path": "$.row_count",
            },
            "schedule_type": "cron",
            "cron_expression": "0 9 * * MON",
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
    assert run["result_summary"]["insights_created"] == 1
    assert run["result_summary"]["plugin"]["response_summary"]["json"]["row_count"] == 18

    feedback_items = client.get(
        f"/api/insights/user-feedback?product_id={product['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert feedback_items["total"] == 1
    assert feedback_items["items"][0]["source_channel"] == "maxcompute_weekly_ai"
    assert "支付页提交后无响应" in feedback_items["items"][0]["content"]
