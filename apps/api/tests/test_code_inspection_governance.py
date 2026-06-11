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
        json={"code": "repo-quality-product", "name": "Repository Quality Product"},
        headers=headers,
    ).json()["data"]


def create_repository(headers: dict[str, str], product_id: str) -> dict:
    return client.post(
        f"/api/products/{product_id}/git-repositories",
        json={
            "default_branch": "main",
            "git_provider": "github",
            "name": "service-api",
            "project_path": "example/service-api",
            "remote_url": "https://github.com/example/service-api.git",
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]


def create_scanner_plugin(headers: dict[str, str], repository_id: str) -> tuple[dict, dict, dict]:
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "devops",
            "code": "repo_quality_scanner",
            "description": "Scans repository quality, security and convention issues.",
            "name": "Repository Quality Scanner",
            "protocol": "http",
            "risk_level": "high",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    connection = client.post(
        "/api/system/plugin-connections",
        json={
            "auth_type": "none",
            "endpoint_url": "https://scanner.example.com",
            "environment": "test",
            "name": "Scanner Test",
            "plugin_id": plugin["id"],
            "status": "active",
            "timeout_seconds": 60,
        },
        headers=headers,
    ).json()["data"]
    action = client.post(
        "/api/system/plugin-actions",
        json={
            "action_type": "http_request",
            "code": "scan_repository",
            "connection_id": connection["id"],
            "input_schema": {"type": "object"},
            "name": "Scan Repository",
            "output_schema": {"type": "object"},
            "plugin_id": plugin["id"],
            "request_config": {
                "method": "POST",
                "mock_response_json": {
                    "branch": "main",
                    "commit_sha": "abc1234",
                    "findings": [
                        {
                            "category": "security",
                            "description": "Access key is committed in source code.",
                            "file_path": "src/config.py",
                            "line_number": 12,
                            "recommendation": "Move the key to a secret manager.",
                            "rule_id": "SEC001",
                            "severity": "critical",
                            "title": "Hardcoded access key",
                        },
                        {
                            "category": "quality",
                            "description": "Function is too complex.",
                            "file_path": "src/service.py",
                            "line_number": 88,
                            "recommendation": "Split the function into smaller units.",
                            "rule_id": "QLT010",
                            "severity": "minor",
                            "title": "High cyclomatic complexity",
                        },
                    ],
                    "repository_id": repository_id,
                    "risk_level": "critical",
                    "summary": "2 issues found, including 1 critical security issue.",
                },
                "path": "/scan",
            },
            "result_mapping": {"records_imported_path": "$.findings"},
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    return plugin, connection, action


def test_scheduled_repository_inspection_runs_multiple_result_actions():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    repository = create_repository(headers, product["id"])
    _, connection, action = create_scanner_plugin(headers, repository["id"])

    job_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "branch": "main",
                "repository_id": repository["id"],
                "scan_scope": "quality_security_convention",
            },
            "cron_expression": "0 2 * * MON",
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Weekly repository quality inspection",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {
                    "severity_threshold": "critical",
                    "type": "create_bug_for_severe_findings",
                },
                {
                    "channels": ["email", "dingtalk"],
                    "recipients": ["quality@example.com"],
                    "type": "send_notification",
                    "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test",
                },
            ],
            "schedule_type": "cron",
            "source_system": "repo-quality-scanner",
            "timezone": "Asia/Shanghai",
        },
        headers=headers,
    )

    assert job_response.status_code == 200
    job = job_response.json()["data"]
    assert job["result_actions"][0]["type"] == "write_code_inspection_report"

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 2
    execution_nodes = run["result_summary"]["execution_nodes"]
    assert execution_nodes["data_connection"]["records_imported"] == 2
    assert execution_nodes["code_inspection_report"]["report_id"].startswith(
        "code_inspection_report_",
    )
    assert execution_nodes["bug_creation"]["created_bug_ids"][0].startswith("bug_")
    assert execution_nodes["notifications"]["created_notification_ids"]

    report_id = execution_nodes["code_inspection_report"]["report_id"]
    listed = client.get(
        f"/api/governance/code-inspections?product_id={product['id']}",
        headers=headers,
    )
    assert listed.status_code == 200
    listed_payload = listed.json()["data"]
    assert listed_payload["total"] == 1
    assert listed_payload["items"][0]["id"] == report_id
    assert listed_payload["items"][0]["finding_count"] == 2
    assert listed_payload["items"][0]["risk_level"] == "critical"
    assert listed_payload["items"][0]["severe_finding_count"] == 1

    detail = client.get(
        f"/api/governance/code-inspections/{report_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    detail_payload = detail.json()["data"]
    assert detail_payload["report"]["repository_id"] == repository["id"]
    assert detail_payload["findings"][0]["severity"] == "critical"
    assert detail_payload["notifications"][0]["channel"] in {"email", "dingtalk"}

    bugs = client.get(
        f"/api/bugs?product_id={product['id']}&source=code_inspection",
        headers=headers,
    )
    assert bugs.status_code == 200
    bug_items = bugs.json()["data"]["items"]
    assert len(bug_items) == 1
    assert bug_items[0]["severity"] == "critical"
    assert bug_items[0]["source"] == "code_inspection"
    assert bug_items[0]["evidence"]["code_inspection_report_id"] == report_id


def test_scheduled_repository_inspection_rejects_unsupported_notification_channel():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    repository = create_repository(headers, product["id"])
    _, connection, action = create_scanner_plugin(headers, repository["id"])

    response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {"repository_id": repository["id"]},
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Weekly repository inspection with bad notification",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {"channels": ["sms"], "type": "send_notification"},
            ],
            "schedule_type": "manual",
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
