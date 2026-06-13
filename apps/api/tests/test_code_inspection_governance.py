import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.services.scheduled_jobs as scheduled_jobs_service
from app.main import app
from app.services.code_inspections import existing_code_inspection_bug_id, finding_fingerprint

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product(
    headers: dict[str, str],
    *,
    code: str = "repo-quality-product",
    name: str = "Repository Quality Product",
) -> dict:
    return client.post(
        "/api/products",
        json={"code": code, "name": name},
        headers=headers,
    ).json()["data"]


def create_repository(
    headers: dict[str, str],
    product_id: str,
    *,
    name: str = "service-api",
    project_path: str = "example/service-api",
) -> dict:
    return client.post(
        f"/api/products/{product_id}/git-repositories",
        json={
            "default_branch": "main",
            "git_provider": "github",
            "name": name,
            "project_path": project_path,
            "remote_url": f"https://github.com/{project_path}.git",
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]


def create_model_gateway(headers: dict[str, str]) -> dict:
    return client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-code-inspection",
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "code-inspection-model",
            "is_default": True,
            "name": "代码巡检模型",
            "provider": "openai_compatible",
            "status": "active",
            "timeout_seconds": 12,
        },
        headers=headers,
    ).json()["data"]


def scanner_response(repository_id: str, *, severity: str = "critical") -> dict:
    return {
        "branch": "main",
        "commit_sha": "abc1234",
        "findings": [
            {
                "category": "security",
                "committer_email": "alice@example.com",
                "committer_name": "Alice Chen",
                "committer_username": "alice",
                "description": "Access key is committed in source code.",
                "file_path": "src/config.py",
                "line_number": 12,
                "recommendation": "Move the key to a secret manager.",
                "rule_id": "SEC001",
                "severity": severity,
                "title": "Hardcoded access key",
            },
            {
                "category": "quality",
                "committer_email": "bob@example.com",
                "committer_name": "Bob Li",
                "committer_username": "bob",
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
        "risk_level": severity,
        "summary": "2 issues found, including 1 critical security issue.",
    }


def create_scanner_plugin(
    headers: dict[str, str],
    repository_id: str,
    *,
    code: str = "repo_quality_scanner",
    result_mapping: dict | None = None,
    request_config_extra: dict | None = None,
    response_json: dict | None = None,
) -> tuple[dict, dict, dict]:
    plugin = client.post(
        "/api/system/plugins",
        json={
            "category": "devops",
            "code": code,
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
                **(request_config_extra or {}),
                "method": "POST",
                "mock_response_json": response_json or scanner_response(repository_id),
                "path": "/scan",
            },
            "result_mapping": result_mapping or {"records_imported_path": "$.findings"},
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    return plugin, connection, action


def create_scoped_user(
    headers: dict[str, str],
    *,
    product_id: str,
    username: str,
) -> dict[str, str]:
    created = client.post(
        "/api/users",
        headers=headers,
        json={
            "display_name": username,
            "password": "password123",
            "roles": ["rd_owner"],
            "status": "active",
            "username": username,
        },
    )
    assert created.status_code == 200
    user = created.json()["data"]
    scope_response = client.put(
        f"/api/users/{user['id']}/scopes",
        headers=headers,
        json={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": product_id,
                    "scope_type": "product",
                }
            ]
        },
    )
    assert scope_response.status_code == 200
    return auth_headers(username, "password123")


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
                    "severity_threshold": "high",
                    "type": "create_task_for_severe_findings",
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
    assert execution_nodes["task_creation"]["created_task_ids"][0].startswith("task_")
    assert execution_nodes["notifications"]["created_notification_ids"]

    report_id = execution_nodes["code_inspection_report"]["report_id"]
    listed = client.get(
        f"/api/governance/code-inspections?product_id={product['id']}",
        headers=headers,
    )
    assert listed.status_code == 200
    listed_payload = listed.json()["data"]
    assert listed_payload["total"] == 1
    listed_report = listed_payload["items"][0]
    assert listed_report["id"] == report_id
    assert listed_report["finding_count"] == 2
    assert listed_report["risk_level"] == "critical"
    assert listed_report["severe_finding_count"] == 1
    assert listed_report["scheduled_job_id"] == job["id"]
    assert listed_report["scheduled_job_run_id"] == run["id"]
    assert listed_report["plugin_connection_id"] == connection["id"]
    assert listed_report["plugin_action_id"] == action["id"]
    assert listed_report["plugin_invocation_log_id"].startswith("plugin_invocation_log_")

    detail = client.get(
        f"/api/governance/code-inspections/{report_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    detail_payload = detail.json()["data"]
    assert detail_payload["report"]["repository_id"] == repository["id"]
    assert detail_payload["report"]["scheduled_job_id"] == job["id"]
    assert detail_payload["report"]["scheduled_job_run_id"] == run["id"]
    assert detail_payload["report"]["plugin_connection_id"] == connection["id"]
    assert detail_payload["report"]["plugin_action_id"] == action["id"]
    assert detail_payload["report"]["plugin_invocation_log_id"].startswith(
        "plugin_invocation_log_",
    )
    assert detail_payload["report"]["created_task_ids"][0].startswith("task_")
    assert detail_payload["report"]["committer_summary"][0]["email"] == "alice@example.com"
    assert detail_payload["findings"][0]["severity"] == "critical"
    assert detail_payload["findings"][0]["committer_email"] == "alice@example.com"
    assert detail_payload["findings"][0]["created_task_id"].startswith("task_")
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
    assert bug_items[0]["evidence"]["committer_email"] == "alice@example.com"

    tasks = client.get(
        f"/api/ai-tasks?product_id={product['id']}&task_type=code_inspection_remediation",
        headers=headers,
    )
    assert tasks.status_code == 200
    task_items = tasks.json()["data"]["items"]
    assert len(task_items) == 1
    assert task_items[0]["title"].startswith("[Code Inspection Remediation]")
    task_detail = client.get(f"/api/ai-tasks/{task_items[0]['id']}", headers=headers)
    assert task_detail.status_code == 200
    assert task_detail.json()["data"]["input"]["code_inspection_report_id"] == report_id


def test_code_inspection_dashboard_summarizes_reports_rules_rankings_and_sla():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, code="repo-quality-product-dashboard")
    repository = create_repository(headers, product["id"])
    _, connection, action = create_scanner_plugin(headers, repository["id"])

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {"branch": "main", "repository_id": repository["id"]},
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Dashboard repository inspection",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {
                    "severity_threshold": "critical",
                    "type": "create_bug_for_severe_findings",
                },
            ],
            "schedule_type": "manual",
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    ).json()["data"]
    run = client.post(f"/api/system/scheduled-jobs/{job['id']}/run", headers=headers)
    assert run.status_code == 200

    dashboard = client.get(
        f"/api/governance/code-inspections/dashboard?product_id={product['id']}",
        headers=headers,
    )

    assert dashboard.status_code == 200
    payload = dashboard.json()["data"]
    assert payload["summary"]["report_count"] == 1
    assert payload["summary"]["finding_count"] == 2
    assert payload["summary"]["severe_finding_count"] == 1
    assert payload["summary"]["bug_created_count"] == 1
    assert payload["sla"]["status"] == "healthy"
    assert payload["sla"]["bug_coverage_rate"] == 1
    assert payload["rule_distribution"][0]["rule_id"] == "SEC001"
    assert payload["rule_distribution"][0]["severe_finding_count"] == 1
    assert payload["repository_ranking"][0]["repository_id"] == repository["id"]
    assert payload["repository_ranking"][0]["risk_level"] == "critical"
    assert payload["branch_ranking"][0]["branch"] == "main"
    assert payload["committer_ranking"][0]["email"] == "alice@example.com"
    assert payload["committer_ranking"][0]["bug_count"] == 1
    assert payload["trend"][0]["report_count"] == 1

    filtered = client.get(
        "/api/governance/code-inspections/dashboard?committer=carol@example.com",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["data"]["summary"]["report_count"] == 0


def test_ai_generated_repository_inspection_calls_model_before_writing_report(monkeypatch):
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, code="repo-quality-product-ai")
    repository = create_repository(headers, product["id"])
    model_gateway = create_model_gateway(headers)
    skill = client.post(
        "/api/system/ai-skills",
        json={
            "code": "code_inspection_analysis",
            "name": "代码巡检分析",
            "prompt_template": "归一化扫描器结果，提取安全、质量和规范问题。",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    agent = client.post(
        "/api/system/ai-agents",
        json={
            "brain_app_id": "rd_brain",
            "code": "code_inspection_agent",
            "default_skill_ids": [skill["id"]],
            "model_gateway_config_id": model_gateway["id"],
            "name": "代码巡检 Agent",
            "status": "active",
            "system_prompt": "你是代码巡检分析助手。",
        },
        headers=headers,
    ).json()["data"]
    _, connection, action = create_scanner_plugin(
        headers,
        repository["id"],
        code="repo_quality_scanner_ai",
        response_json=scanner_response(repository["id"], severity="minor"),
    )
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
                                        "branch": "main",
                                        "commit_sha": "ai5678",
                                        "findings": [
                                            {
                                                "category": "security",
                                                "committer_email": "alice@example.com",
                                                "committer_name": "Alice Chen",
                                                "description": "AI 复核后确认存在密钥泄露风险。",
                                                "file_path": "src/config.py",
                                                "line_number": 12,
                                                "recommendation": "立即轮转密钥并迁移到密钥管理。",
                                                "rule_id": "AI_SEC001",
                                                "severity": "critical",
                                                "title": "AI confirmed hardcoded access key",
                                            },
                                        ],
                                        "repository_id": repository["id"],
                                        "risk_level": "critical",
                                        "summary": "AI 复核确认 1 个 critical 安全问题。",
                                    },
                                    ensure_ascii=False,
                                ),
                            },
                        },
                    ],
                    "usage": {
                        "completion_tokens": 28,
                        "prompt_tokens": 80,
                        "total_tokens": 108,
                    },
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

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "agent_id": agent["id"],
            "config_json": {"repository_id": repository["id"]},
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "code_repository_inspection",
            "model_gateway_config_id": model_gateway["id"],
            "name": "AI repository inspection",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "skill_ids": [skill["id"]],
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    ).json()["data"]

    run = client.post(f"/api/system/scheduled-jobs/{job['id']}/run", headers=headers)

    assert run.status_code == 200
    run_payload = run.json()["data"]
    assert run_payload["status"] == "succeeded"
    assert model_calls and model_calls[0]["url"] == "https://llm.example.com/v1/chat/completions"
    assert model_calls[0]["timeout"] == 12
    model_body = json.loads(str(model_calls[0]["body"]))
    assert model_body["model"] == "code-inspection-model"
    user_payload = json.loads(model_body["messages"][1]["content"])
    assert user_payload["job"]["job_type"] == "code_repository_inspection"
    assert user_payload["output_contract"]["write_target"] == "code_inspection_reports"
    assert user_payload["source_row_count"] == 2

    execution_nodes = run_payload["result_summary"]["execution_nodes"]
    assert execution_nodes["data_connection"]["records_imported"] == 2
    assert execution_nodes["skill_processing"]["model_gateway_called"] is True
    assert execution_nodes["skill_processing"]["model_log_id"].startswith("model_log_")
    assert execution_nodes["skill_processing"]["output"]["finding_count"] == 1
    assert execution_nodes["result_action"]["write_target"] == "code_inspection_reports"
    assert execution_nodes["result_action"]["feedback"]["report_id"].startswith(
        "code_inspection_report_",
    )
    assert run_payload["result_summary"]["plugin"]["response_summary"]["ai_processed"] is True

    report_id = run_payload["result_summary"]["report_id"]
    detail = client.get(f"/api/governance/code-inspections/{report_id}", headers=headers)
    detail_payload = detail.json()["data"]
    assert detail_payload["report"]["commit_sha"] == "ai5678"
    assert detail_payload["report"]["risk_level"] == "critical"
    assert detail_payload["findings"][0]["rule_id"] == "AI_SEC001"
    assert detail_payload["findings"][0]["severity"] == "critical"


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


def test_repository_inspection_supports_committer_filter_severity_mapping_and_bug_dedupe():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, code="repo-quality-product-committer")
    repository = create_repository(headers, product["id"])
    _, connection, action = create_scanner_plugin(
        headers,
        repository["id"],
        code="repo_quality_scanner_committer",
        request_config_extra={
            "severity_mapping": {
                "blocker": "critical",
                "minor": "low",
            }
        },
        response_json=scanner_response(repository["id"], severity="blocker"),
    )

    job_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "branch": "main",
                "repository_id": repository["id"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Weekly repository inspection by committer",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {
                    "severity_threshold": "high",
                    "type": "create_bug_for_severe_findings",
                },
            ],
            "schedule_type": "manual",
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    )
    assert job_response.status_code == 200
    job = job_response.json()["data"]

    first_run = client.post(f"/api/system/scheduled-jobs/{job['id']}/run", headers=headers)
    assert first_run.status_code == 200
    first_summary = first_run.json()["data"]["result_summary"]
    first_report_id = first_summary["report_id"]
    first_bug_id = first_summary["bug_ids"][0]
    assert first_summary["execution_nodes"]["result_actions"][0]["status"] == "succeeded"

    detail = client.get(f"/api/governance/code-inspections/{first_report_id}", headers=headers)
    assert detail.status_code == 200
    detail_payload = detail.json()["data"]
    assert detail_payload["report"]["risk_level"] == "critical"
    assert detail_payload["report"]["committer_count"] == 2
    assert detail_payload["report"]["committer_summary"] == [
        {
            "bug_count": 1,
            "email": "alice@example.com",
            "finding_count": 1,
            "name": "Alice Chen",
            "severe_finding_count": 1,
            "username": "alice",
        },
        {
            "bug_count": 0,
            "email": "bob@example.com",
            "finding_count": 1,
            "name": "Bob Li",
            "severe_finding_count": 0,
            "username": "bob",
        },
    ]
    assert detail_payload["findings"][0]["severity"] == "critical"
    assert detail_payload["findings"][0]["committer_email"] == "alice@example.com"
    assert detail_payload["findings"][1]["severity"] == "low"

    listed = client.get(
        "/api/governance/code-inspections?committer=alice@example.com",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    missed = client.get(
        "/api/governance/code-inspections?committer=carol@example.com",
        headers=headers,
    )
    assert missed.status_code == 200
    assert missed.json()["data"]["total"] == 0

    second_run = client.post(f"/api/system/scheduled-jobs/{job['id']}/run", headers=headers)
    assert second_run.status_code == 200
    second_summary = second_run.json()["data"]["result_summary"]
    bug_creation = second_summary["execution_nodes"]["bug_creation"]
    assert bug_creation["created_bug_ids"] == []
    assert bug_creation["deduplicated_bug_ids"] == [first_bug_id]

    bugs = client.get(
        f"/api/bugs?product_id={product['id']}&source=code_inspection",
        headers=headers,
    )
    assert bugs.status_code == 200
    assert [item["id"] for item in bugs.json()["data"]["items"]] == [first_bug_id]


def test_repository_inspection_applies_action_result_mapping_before_writing_report():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, code="repo-quality-product-mapped")
    repository = create_repository(headers, product["id"])
    nested_response = {
        "payload": {
            "alerts": [
                {
                    "author": {
                        "email": "security@example.com",
                        "name": "Security Owner",
                        "username": "sec-owner",
                    },
                    "category": "security",
                    "description": "Token is committed.",
                    "file_path": "app/settings.py",
                    "line_number": 7,
                    "recommendation": "Rotate the token and move it to vault.",
                    "rule_id": "GITHUB_SECRET_001",
                    "severity": "error",
                    "title": "Secret token exposure",
                }
            ],
            "branch": "release/2026.06",
            "commit": "def5678",
            "repository": repository["id"],
            "risk": "error",
            "summary": "1 secret scanning alert needs action.",
        }
    }
    _, connection, action = create_scanner_plugin(
        headers,
        repository["id"],
        code="repo_quality_scanner_mapped",
        request_config_extra={
            "severity_mapping": {
                "error": "critical",
            }
        },
        response_json=nested_response,
        result_mapping={
            "branch_path": "$.payload.branch",
            "commit_sha_path": "$.payload.commit",
            "findings_path": "$.payload.alerts",
            "repository_id_path": "$.payload.repository",
            "risk_level_path": "$.payload.risk",
            "summary_path": "$.payload.summary",
            "write_target": "code_inspection_reports",
        },
    )

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {"repository_id": repository["id"]},
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Mapped repository inspection",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    ).json()["data"]

    run = client.post(f"/api/system/scheduled-jobs/{job['id']}/run", headers=headers)

    assert run.status_code == 200
    summary = run.json()["data"]["result_summary"]
    assert summary["finding_count"] == 1
    assert summary["risk_level"] == "critical"
    report_id = summary["report_id"]
    detail = client.get(f"/api/governance/code-inspections/{report_id}", headers=headers)
    detail_payload = detail.json()["data"]
    assert detail_payload["report"]["repository_id"] == repository["id"]
    assert detail_payload["report"]["branch"] == "release/2026.06"
    assert detail_payload["report"]["commit_sha"] == "def5678"
    assert detail_payload["report"]["summary"] == "1 secret scanning alert needs action."
    assert detail_payload["findings"][0]["severity"] == "critical"
    assert detail_payload["findings"][0]["committer_email"] == "security@example.com"


def test_repository_inspection_is_filtered_by_product_scope():
    app.state.store.reset()
    headers = auth_headers()
    product_a = create_product(headers, code="repo-quality-product-a", name="Product A")
    repository_a = create_repository(
        headers,
        product_a["id"],
        name="service-a",
        project_path="example/service-a",
    )
    _, connection_a, action_a = create_scanner_plugin(
        headers,
        repository_a["id"],
        code="repo_quality_scanner_a",
    )
    product_b = create_product(headers, code="repo-quality-product-b", name="Product B")
    repository_b = create_repository(
        headers,
        product_b["id"],
        name="service-b",
        project_path="example/service-b",
    )
    _, connection_b, action_b = create_scanner_plugin(
        headers,
        repository_b["id"],
        code="repo_quality_scanner_b",
    )

    report_ids = []
    for product, repository, connection, action in [
        (product_a, repository_a, connection_a, action_a),
        (product_b, repository_b, connection_b, action_b),
    ]:
        job = client.post(
            "/api/system/scheduled-jobs",
            json={
                "config_json": {"repository_id": repository["id"]},
                "enabled": True,
                "execution_mode": "deterministic",
                "job_type": "code_repository_inspection",
                "name": f"Inspection {product['code']}",
                "plugin_action_id": action["id"],
                "plugin_connection_id": connection["id"],
                "product_id": product["id"],
                "result_actions": [{"type": "write_code_inspection_report"}],
                "schedule_type": "manual",
                "source_system": "repo-quality-scanner",
            },
            headers=headers,
        ).json()["data"]
        run = client.post(f"/api/system/scheduled-jobs/{job['id']}/run", headers=headers)
        assert run.status_code == 200
        report_ids.append(run.json()["data"]["result_summary"]["report_id"])

    scoped_headers = create_scoped_user(
        headers,
        product_id=product_a["id"],
        username="repo-scope-reader@example.com",
    )
    scoped_list = client.get("/api/governance/code-inspections", headers=scoped_headers)
    assert scoped_list.status_code == 200
    assert [item["id"] for item in scoped_list.json()["data"]["items"]] == [report_ids[0]]

    hidden_detail = client.get(
        f"/api/governance/code-inspections/{report_ids[1]}",
        headers=scoped_headers,
    )
    assert hidden_detail.status_code == 404


def test_code_inspection_bug_dedupe_reads_repository_when_runtime_store_is_stale():
    bug = {
        "evidence": {"finding_fingerprint": "fingerprint_001"},
        "id": "bug_existing",
        "product_id": "product_001",
        "source": "code_inspection",
        "status": "open",
    }
    fake_store = SimpleNamespace(
        bugs={},
        repository=SimpleNamespace(
            list_bug_summaries=lambda **kwargs: [bug]
        ),
    )

    assert (
        existing_code_inspection_bug_id(
            fake_store,
            fingerprint="fingerprint_001",
            product_id="product_001",
        )
        == "bug_existing"
    )


def test_code_inspection_fingerprint_uses_non_email_committer_identity():
    report = {"branch": "main", "repository_id": "repo_001"}
    base_finding = {
        "file_path": "src/service.py",
        "line_number": 42,
        "rule_id": "unsafe-call",
    }

    alice = {**base_finding, "committer_username": "alice", "title": "Unsafe call"}
    alice_renamed = {**base_finding, "committer_username": "alice", "title": "Unsafe API call"}
    bob = {**base_finding, "committer_username": "bob", "title": "Unsafe call"}

    assert finding_fingerprint(alice, report) == finding_fingerprint(alice_renamed, report)
    assert finding_fingerprint(alice, report) != finding_fingerprint(bob, report)
