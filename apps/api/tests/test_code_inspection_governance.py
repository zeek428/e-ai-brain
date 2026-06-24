import json
import os
import subprocess
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.services.native_code_scanner as native_code_scanner
import app.services.scheduled_jobs as scheduled_jobs_service
from app.core.repositories.code_inspections import CodeInspectionReadRepository
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
    default_branch: str = "main",
    name: str = "service-api",
    project_path: str = "example/service-api",
) -> dict:
    return client.post(
        f"/api/products/{product_id}/git-repositories",
        json={
            "default_branch": default_branch,
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


def create_local_git_repository(path) -> str:
    repo_path = path / "native-scan-repo"
    repo_path.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "seed@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Seed User"], cwd=repo_path, check=True)
    (repo_path / "README.md").write_text("# Native scan fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)
    subprocess.run(["git", "checkout", "-b", "release/native-scan"], cwd=repo_path, check=True)
    source_dir = repo_path / "src"
    source_dir.mkdir()
    (source_dir / "config.py").write_text(
        'API_KEY = "sk-live-native-scan-secret"\n'
        'INTERNAL_URL = "http://127.0.0.1:8080/admin"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "src/config.py"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add insecure config"],
        cwd=repo_path,
        env={
            "GIT_AUTHOR_EMAIL": "alice@example.com",
            "GIT_AUTHOR_NAME": "Alice Chen",
            "GIT_COMMITTER_EMAIL": "alice@example.com",
            "GIT_COMMITTER_NAME": "Alice Chen",
        },
        check=True,
    )
    return str(repo_path)


def create_local_scan_repository(
    headers: dict[str, str],
    product_id: str,
    *,
    remote_url: str,
) -> dict:
    return client.post(
        f"/api/products/{product_id}/git-repositories",
        json={
            "default_branch": "main",
            "git_provider": "github",
            "name": "Native Scan Repository",
            "project_path": "local/native-scan",
            "remote_url": remote_url,
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]


def test_code_inspection_report_upsert_accepts_native_scan_metadata():
    class CountingCursor:
        def execute(self, query: str, params: tuple | None = None) -> None:
            if "INSERT INTO code_inspection_reports" not in query:
                return
            assert params is not None
            assert query.count("%s") == len(params)

    repository = CodeInspectionReadRepository(None)
    repository.upsert_code_inspection_reports(
        CountingCursor(),
        {
            "code_inspection_report_native": {
                "branch": "release/native-scan",
                "commit_sha": "abc123",
                "coverage_warning": None,
                "created_at": "2026-06-15T00:00:00+00:00",
                "created_by": "user_admin",
                "files_scanned": 12,
                "finding_count": 2,
                "id": "code_inspection_report_native",
                "is_full_scan": True,
                "lines_scanned": 345,
                "repository": {"name": "Native Scan Repository"},
                "repository_id": "repo_native",
                "risk_level": "critical",
                "rules_loaded": ["secrets", "internal_addresses"],
                "scan_mode": "native_full_scan",
                "scanner_name": "ai_brain_builtin_static",
                "scheduled_job_id": "scheduled_job_native",
                "scheduled_job_run_id": "scheduled_job_run_native",
                "severe_finding_count": 1,
                "source_system": "native-code-scanner",
                "status": "completed",
                "summary": "本地完整扫描完成。",
            }
        },
    )


def test_code_inspection_finding_upsert_accepts_suppression_metadata():
    class CountingCursor:
        def execute(self, query: str, params: tuple | None = None) -> None:
            if "INSERT INTO code_inspection_findings" not in query:
                return
            assert params is not None
            assert query.count("%s") == len(params)

    repository = CodeInspectionReadRepository(None)
    repository.upsert_code_inspection_findings(
        CountingCursor(),
        {
            "code_inspection_finding_suppression": {
                "category": "security",
                "created_at": "2026-06-24T00:00:00+00:00",
                "description": "False positive candidate",
                "file_path": "src/config.py",
                "id": "code_inspection_finding_suppression",
                "line_number": 12,
                "raw": {"fingerprint": "finding-fingerprint"},
                "recommendation": "确认误报后审批忽略。",
                "report_id": "code_inspection_report_native",
                "rule_id": "metadata.internal_address_exposure",
                "severity": "medium",
                "suppression_note": "确认误报，批准忽略",
                "suppression_reason": "false_positive",
                "suppression_requested_at": "2026-06-24T00:01:00+00:00",
                "suppression_requested_by": "user_admin",
                "suppression_reviewed_at": "2026-06-24T00:02:00+00:00",
                "suppression_reviewed_by": "user_admin",
                "suppression_status": "approved",
                "title": "内部地址暴露于页面元数据",
                "updated_at": "2026-06-24T00:02:00+00:00",
            }
        },
    )


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


def test_code_inspection_finding_suppression_approval_updates_report_governance():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(
        headers,
        code="repo-suppression-product",
        name="Repository Suppression Product",
    )
    repository = create_repository(headers, product["id"])
    _, connection, action = create_scanner_plugin(headers, repository["id"])

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "branch": "main",
                "repository_id": repository["id"],
                "scan_scope": "quality_security_convention",
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Repository suppression inspection",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    ).json()["data"]
    run = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    ).json()["data"]
    report_id = run["result_summary"]["report_id"]
    detail = client.get(
        f"/api/governance/code-inspections/{report_id}",
        headers=headers,
    ).json()["data"]
    finding_id = detail["findings"][0]["id"]

    requested = client.post(
        f"/api/governance/code-inspections/{report_id}/findings/{finding_id}/suppression-request",
        headers=headers,
        json={
            "note": "自动化验收申请误报忽略",
            "reason": "false_positive",
        },
    )

    assert requested.status_code == 200
    requested_detail = requested.json()["data"]
    requested_finding = next(
        item for item in requested_detail["findings"] if item["id"] == finding_id
    )
    assert requested_finding["suppression_status"] == "pending"
    assert requested_finding["suppression_reason"] == "false_positive"
    assert requested_finding["suppression_requested_by"] == "user_admin"

    approved = client.post(
        f"/api/governance/code-inspections/{report_id}/findings/{finding_id}/suppression-review",
        headers=headers,
        json={
            "decision": "approve",
            "note": "确认误报，批准忽略",
        },
    )

    assert approved.status_code == 200
    approved_detail = approved.json()["data"]
    approved_finding = next(
        item for item in approved_detail["findings"] if item["id"] == finding_id
    )
    assert approved_finding["suppression_status"] == "approved"
    assert approved_finding["suppression_reviewed_by"] == "user_admin"
    assert approved_detail["report"]["suppressed_finding_count"] == 1
    assert approved_detail["report"]["suppression_summary"]["false_positive"] == 1

    duplicate_review = client.post(
        f"/api/governance/code-inspections/{report_id}/findings/{finding_id}/suppression-review",
        headers=headers,
        json={"decision": "approve"},
    )
    assert duplicate_review.status_code == 409

    dashboard = client.get(
        f"/api/governance/code-inspections/dashboard?product_id={product['id']}",
        headers=headers,
    ).json()["data"]
    suppression_distribution = {
        item["reason"]: item["count"]
        for item in dashboard["rule_governance"]["suppression_distribution"]
    }
    assert suppression_distribution["false_positive"] == 1
    assert dashboard["rule_governance"]["suppressed_finding_count"] == 1

    audit_events = [event["event_type"] for event in app.state.store.audit_events]
    assert "code_inspection_finding_suppression.requested" in audit_events
    assert "code_inspection_finding_suppression.approved" in audit_events


def test_code_inspection_uses_configured_repository_when_scanner_returns_project_path():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, code="gitlab-path-product", name="GitLab Path Product")
    repository = create_repository(
        headers,
        product["id"],
        name="intofun",
        project_path="zqf-play-app/intofun",
    )
    _, connection, action = create_scanner_plugin(
        headers,
        repository["id"],
        response_json=scanner_response("zqf-play-app/intofun", severity="high"),
    )

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {"repository_id": repository["id"]},
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "GitLab project path inspection",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    ).json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    report_id = run["result_summary"]["execution_nodes"]["code_inspection_report"]["report_id"]
    detail = client.get(
        f"/api/governance/code-inspections/{report_id}",
        headers=headers,
    ).json()["data"]
    assert detail["report"]["repository_id"] == repository["id"]
    assert detail["report"]["repository"]["project_path"] == "zqf-play-app/intofun"


def test_code_inspection_defaults_branch_from_repository_when_scanner_omits_branch():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, code="branch-default-product", name="Branch Default Product")
    repository = create_repository(
        headers,
        product["id"],
        default_branch="develop",
    )
    response_json = scanner_response(repository["id"], severity="high")
    response_json.pop("branch")
    _, connection, action = create_scanner_plugin(
        headers,
        repository["id"],
        response_json=response_json,
    )

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {"repository_id": repository["id"]},
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Default branch inspection",
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    ).json()["data"]

    assert job["config_json"]["branch"] == "develop"

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    report_id = run["result_summary"]["execution_nodes"]["code_inspection_report"]["report_id"]
    detail = client.get(
        f"/api/governance/code-inspections/{report_id}",
        headers=headers,
    ).json()["data"]
    assert detail["report"]["repository_id"] == repository["id"]
    assert detail["report"]["branch"] == "develop"


def test_native_repository_inspection_clones_branch_scans_files_and_blames_committers(
    monkeypatch,
    tmp_path,
):
    app.state.store.reset()
    scan_workdir = tmp_path / "code-scan-workdir"
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(scan_workdir))
    headers = auth_headers()
    product = create_product(headers, code="native-scan-product", name="Native Scan Product")
    local_repo_url = create_local_git_repository(tmp_path)
    repository = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )

    job_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "async_execution": False,
                "branch": "release/native-scan",
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Native full repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    )

    assert job_response.status_code == 200
    job = job_response.json()["data"]
    assert job["plugin_action_id"] is None
    assert job["config_json"]["scan_mode"] == "native_full_scan"

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["plugin_invocation_log_id"] is None
    assert run["records_imported"] == 2
    execution_nodes = run["result_summary"]["execution_nodes"]
    assert execution_nodes["native_scan"]["status"] == "succeeded"
    assert execution_nodes["native_scan"]["scan_mode"] == "native_full_scan"
    assert execution_nodes["native_scan"]["branch"] == "release/native-scan"
    assert execution_nodes["native_scan"]["files_scanned"] >= 1
    assert execution_nodes["native_scan"]["lines_scanned"] >= 2
    assert execution_nodes["native_scan"]["repository_id"] == repository["id"]
    assert execution_nodes["native_scan"]["remote_url_hash"]
    assert execution_nodes["native_scan"]["remote_url_summary"].startswith("file://")
    assert execution_nodes["native_scan"]["artifact_ref"].startswith("workdir://checkouts/")
    assert execution_nodes["native_scan"]["checkout_path_retained"] is False
    assert execution_nodes["native_scan"]["scan_started_at"]
    assert execution_nodes["native_scan"]["scan_finished_at"]
    assert execution_nodes["native_scan"]["scanner_version"]
    assert execution_nodes["native_scan"]["rules_version"]
    assert (scan_workdir / "mirrors").is_dir()
    assert any((scan_workdir / "mirrors").iterdir())
    checkout_path = execution_nodes["native_scan"].get("checkout_path")
    if checkout_path:
        assert not (tmp_path / checkout_path).exists()
    assert execution_nodes["data_connection"]["processing_mode"] == "native_full_scan"

    report_id = run["result_summary"]["report_id"]
    detail = client.get(
        f"/api/governance/code-inspections/{report_id}",
        headers=headers,
    ).json()["data"]
    report = detail["report"]
    assert report["repository_id"] == repository["id"]
    assert report["branch"] == "release/native-scan"
    assert report["scan_mode"] == "native_full_scan"
    assert report["scanner_name"] == "ai_brain_builtin_static"
    assert report["is_full_scan"] is True
    assert report["files_scanned"] >= 1
    assert report["lines_scanned"] >= 2
    assert report["coverage_warning"] is None
    assert report["commit_sha"]
    assert report["finding_count"] == 2
    assert report["remote_url_hash"] == execution_nodes["native_scan"]["remote_url_hash"]
    assert report["remote_url_summary"] == execution_nodes["native_scan"]["remote_url_summary"]
    assert report["artifact_ref"] == execution_nodes["native_scan"]["artifact_ref"]
    assert report["checkout_path_retained"] is False
    assert report["scan_started_at"]
    assert report["scan_finished_at"]
    assert report["scanner_version"] == execution_nodes["native_scan"]["scanner_version"]
    assert report["rules_version"] == execution_nodes["native_scan"]["rules_version"]

    findings_by_rule = {finding["rule_id"]: finding for finding in detail["findings"]}
    assert "secrets.hardcoded_credential" in findings_by_rule
    assert "metadata.internal_address_exposure" in findings_by_rule
    secret_finding = findings_by_rule["secrets.hardcoded_credential"]
    assert secret_finding["file_path"] == "src/config.py"
    assert secret_finding["committer_email"] == "alice@example.com"
    assert secret_finding["committer_name"] == "Alice Chen"
    assert secret_finding["raw"]["scan_mode"] == "native_full_scan"


def test_native_repository_inspection_uses_repository_credential_ref_for_git_clone(
    monkeypatch,
    tmp_path,
):
    scan_workdir = tmp_path / "code-scan-workdir"
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(scan_workdir))
    monkeypatch.setenv("GITLAB_READONLY_TOKEN", "gitlab-private-token")
    captured_auth_context = {}

    def fake_ensure_mirror(*, mirror_path, remote_url, auth_context):
        captured_auth_context.update(auth_context or {})
        mirror_path.mkdir(parents=True)
        assert remote_url == "http://gitlab.example/group/repo.git"
        return False

    def fake_checkout_commit(*, checkout_path, commit_sha, mirror_path):
        checkout_path.mkdir(parents=True)
        (checkout_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    monkeypatch.setattr(native_code_scanner, "_ensure_mirror", fake_ensure_mirror)
    monkeypatch.setattr(
        native_code_scanner,
        "_resolve_mirror_branch_commit",
        lambda mirror_path, branch: "a" * 40,
    )
    monkeypatch.setattr(native_code_scanner, "_checkout_commit", fake_checkout_commit)

    result = native_code_scanner.run_native_code_scan(
        SimpleNamespace(
            product_git_repositories={
                "repo_private": {
                    "credential_ref": "env:GITLAB_READONLY_TOKEN",
                    "default_branch": "main",
                    "git_provider": "gitlab",
                    "id": "repo_private",
                    "product_id": "product_private",
                    "remote_url": "http://gitlab.example/group/repo.git",
                    "root_path": "/",
                }
            }
        ),
        job={
            "config_json": {
                "async_execution": False,
                "repository_id": "repo_private",
                "scan_mode": "native_full_scan",
            },
            "id": "scheduled_job_private",
            "product_id": "product_private",
        },
        run_id="scheduled_job_run_private",
        user={"id": "user_admin"},
    )

    assert result["status"] == "succeeded"
    assert captured_auth_context["password"] == "gitlab-private-token"
    assert captured_auth_context["username"] == "oauth2"
    assert "GITLAB_READONLY_TOKEN" not in captured_auth_context


def test_ai_processed_code_inspection_preserves_native_scan_metadata():
    source_summary = {
        "response_summary": {
            "json": {
                "artifact_ref": "workdir://checkouts/run__repo__main__abc123",
                "branch": "main",
                "checkout_path_retained": False,
                "commit_sha": "abc123",
                "files_scanned": 12,
                "findings": [{"rule_id": "source.rule"}],
                "is_full_scan": True,
                "lines_scanned": 345,
                "quality_gate": {"enabled": False, "status": "skipped"},
                "remote_url_hash": "hash123",
                "remote_url_summary": "https://git.example/repo.git#hash123",
                "repository_id": "repo_001",
                "rules_loaded": ["secrets"],
                "rules_version": "builtin-test",
                "scan_finished_at": "2026-06-16T01:00:02+00:00",
                "scan_mode": "native_full_scan",
                "scan_profile": {"scanner_engines": ["builtin"]},
                "scan_started_at": "2026-06-16T01:00:00+00:00",
                "scanner_name": "ai_brain_builtin_static",
                "scanner_version": "test-version",
            }
        },
        "status": "succeeded",
    }
    process_for_ai = (
        scheduled_jobs_service.JobExecutionEngine.code_inspection_plugin_summary_for_ai_output
    )
    processed = process_for_ai(
        source_summary,
        ai_processing={
            "output_json": {
                "findings": [{"rule_id": "ai.rule"}],
                "risk_level": "critical",
                "summary": "AI processed summary",
            }
        },
    )

    output_json = processed["response_summary"]["json"]
    assert output_json["findings"] == [{"rule_id": "ai.rule"}]
    assert output_json["summary"] == "AI processed summary"
    assert output_json["scan_mode"] == "native_full_scan"
    assert output_json["scanner_name"] == "ai_brain_builtin_static"
    assert output_json["scanner_version"] == "test-version"
    assert output_json["files_scanned"] == 12
    assert output_json["lines_scanned"] == 345
    assert output_json["artifact_ref"].startswith("workdir://checkouts/")
    assert output_json["remote_url_summary"] == "https://git.example/repo.git#hash123"
    assert output_json["quality_gate"] == {"enabled": False, "status": "skipped"}


def test_native_repository_inspection_queues_run_and_worker_completes_scan(
    monkeypatch,
    tmp_path,
):
    app.state.store.reset()
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(tmp_path / "code-scan-workdir"))
    monkeypatch.setenv("SCHEDULED_JOB_ASYNC_WORKER_DISABLED", "1")
    headers = auth_headers()
    product = create_product(headers, code="native-scan-async-product", name="Native Scan Async")
    local_repo_url = create_local_git_repository(tmp_path)
    repository = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )

    job_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "branch": "release/native-scan",
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Async native full repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    )
    assert job_response.status_code == 200
    job = job_response.json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    queued_run = run_response.json()["data"]
    assert queued_run["status"] == "queued"
    assert queued_run["started_at"] is None
    assert queued_run["finished_at"] is None
    assert queued_run["result_summary"]["execution_nodes"]["native_scan"]["status"] == "queued"
    assert (
        queued_run["result_summary"]["execution_nodes"]["native_scan"]["repository_id"]
        == repository["id"]
    )

    worker_run = scheduled_jobs_service.execute_queued_scheduled_job_run_response(
        current_store=app.state.store,
        run_id=queued_run["id"],
        user={"id": "system_scheduled_job_worker", "roles": ["admin"]},
    )

    assert worker_run["id"] == queued_run["id"]
    assert worker_run["status"] == "succeeded"
    assert worker_run["records_imported"] == 2
    assert worker_run["result_summary"]["report_id"]
    assert worker_run["result_summary"]["execution_nodes"]["native_scan"]["scan_finished_at"]


def test_native_repository_inspection_worker_does_not_overwrite_cancelled_run(
    monkeypatch,
    tmp_path,
):
    app.state.store.reset()
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(tmp_path / "code-scan-workdir"))
    monkeypatch.setenv("SCHEDULED_JOB_ASYNC_WORKER_DISABLED", "1")
    headers = auth_headers()
    product = create_product(headers, code="native-scan-cancel-product", name="Native Scan Cancel")
    local_repo_url = create_local_git_repository(tmp_path)
    repository = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )

    job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "branch": "release/native-scan",
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Async cancellable native repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    ).json()["data"]
    queued_run = client.post(f"/api/system/scheduled-jobs/{job['id']}/run", headers=headers).json()[
        "data"
    ]

    def fake_native_scan(current_store, *, job, run_id, user):
        scheduled_jobs_service.cancel_scheduled_job_run_response(
            current_store=current_store,
            run_id=run_id,
            user={"id": "user_admin", "roles": ["admin"]},
        )
        return {
            "action_id": None,
            "connection_id": None,
            "invocation_log_id": None,
            "latency_ms": 1,
            "request_summary": {},
            "response_summary": {
                "json": {
                    "branch": "release/native-scan",
                    "commit_sha": "abc123",
                    "findings": [],
                    "repository_id": repository["id"],
                    "risk_level": "low",
                    "summary": "cancelled worker fixture",
                },
                "native_scan": {
                    "branch": "release/native-scan",
                    "commit_sha": "abc123",
                    "repository_id": repository["id"],
                    "scan_mode": "native_full_scan",
                },
                "status_code": None,
            },
            "status": "succeeded",
        }

    monkeypatch.setattr(scheduled_jobs_service, "run_native_code_scan", fake_native_scan)

    worker_run = scheduled_jobs_service.execute_queued_scheduled_job_run_response(
        current_store=app.state.store,
        run_id=queued_run["id"],
        user={"id": "system_scheduled_job_worker", "roles": ["admin"]},
    )

    assert worker_run["status"] == "cancelled"
    assert worker_run["records_imported"] == 0
    reports = client.get(
        f"/api/governance/code-inspections?product_id={product['id']}",
        headers=headers,
    ).json()["data"]
    assert reports["total"] == 0


def test_native_repository_inspection_applies_ignore_rules(monkeypatch, tmp_path):
    app.state.store.reset()
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(tmp_path / "code-scan-workdir"))
    headers = auth_headers()
    product = create_product(headers, code="native-scan-ignore-product", name="Native Scan Ignore")
    local_repo_url = create_local_git_repository(tmp_path)
    repository = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )

    job_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "async_execution": False,
                "branch": "release/native-scan",
                "ignore_rules": ["metadata.internal_address_exposure"],
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Native ignored rule repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    )
    assert job_response.status_code == 200
    job = job_response.json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 1
    report_id = run["result_summary"]["report_id"]
    detail = client.get(
        f"/api/governance/code-inspections/{report_id}",
        headers=headers,
    ).json()["data"]
    assert {finding["rule_id"] for finding in detail["findings"]} == {
        "secrets.hardcoded_credential"
    }


def test_native_repository_inspection_runs_external_semgrep_engine(monkeypatch, tmp_path):
    app.state.store.reset()
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(tmp_path / "code-scan-workdir"))
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker_path = tmp_path / "semgrep-called"
    semgrep = fake_bin / "semgrep"
    semgrep.write_text(
        "#!/bin/sh\n"
        f"touch {marker_path}\n"
        "cat <<'JSON'\n"
        "{\n"
        '  "results": [\n'
        "    {\n"
        '      "check_id": "python.lang.security.audit.dangerous-subprocess",\n'
        '      "path": "src/config.py",\n'
        '      "start": {"line": 2},\n'
        '      "extra": {\n'
        '        "message": "Subprocess shell execution should be reviewed",\n'
        '        "severity": "WARNING",\n'
        '        "metadata": {"category": "security"}\n'
        "      }\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "JSON\n",
        encoding="utf-8",
    )
    semgrep.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ.get('PATH', '')}")
    headers = auth_headers()
    product = create_product(
        headers,
        code="native-scan-semgrep-product",
        name="Native Scan Semgrep",
    )
    local_repo_url = create_local_git_repository(tmp_path)
    repository = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )

    job_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "async_execution": False,
                "branch": "release/native-scan",
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
                "scanner_engines": ["builtin", "semgrep"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Native semgrep repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    )
    assert job_response.status_code == 200
    job = job_response.json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert marker_path.exists()
    assert run["records_imported"] == 3
    native_scan = run["result_summary"]["execution_nodes"]["native_scan"]
    assert native_scan["scan_profile"]["external_scanner_status"] == {
        "configured": ["semgrep"],
        "executed": ["semgrep"],
        "failed": [],
        "skipped": [],
    }
    detail = client.get(
        f"/api/governance/code-inspections/{run['result_summary']['report_id']}",
        headers=headers,
    ).json()["data"]
    findings_by_rule = {finding["rule_id"]: finding for finding in detail["findings"]}
    assert "semgrep.python.lang.security.audit.dangerous-subprocess" in findings_by_rule
    semgrep_finding = findings_by_rule["semgrep.python.lang.security.audit.dangerous-subprocess"]
    assert semgrep_finding["severity"] == "medium"
    assert semgrep_finding["committer_email"] == "alice@example.com"
    assert semgrep_finding["raw"]["scanner_name"] == "semgrep"


def test_native_repository_inspection_supports_incremental_commit_range(monkeypatch, tmp_path):
    app.state.store.reset()
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(tmp_path / "code-scan-workdir"))
    headers = auth_headers()
    product = create_product(
        headers,
        code="native-scan-incremental-product",
        name="Native Scan Incremental",
    )
    local_repo_url = create_local_git_repository(tmp_path)
    current_commit = subprocess.run(
        ["git", "rev-parse", "release/native-scan"],
        capture_output=True,
        check=True,
        cwd=local_repo_url,
        text=True,
    ).stdout.strip()
    repository = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )

    job_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "async_execution": False,
                "branch": "release/native-scan",
                "incremental_from_commit": current_commit,
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Native incremental repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    )
    assert job_response.status_code == 200
    job = job_response.json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 0
    native_scan = run["result_summary"]["execution_nodes"]["native_scan"]
    assert native_scan["incremental_from_commit"] == current_commit
    assert native_scan["incremental_file_count"] == 0


def test_native_repository_inspection_applies_baseline_quality_gate_and_detail_summary(
    monkeypatch,
    tmp_path,
):
    app.state.store.reset()
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(tmp_path / "code-scan-workdir"))
    headers = auth_headers()
    product = create_product(
        headers,
        code="native-scan-baseline-product",
        name="Native Scan Baseline",
    )
    local_repo_url = create_local_git_repository(tmp_path)
    repository = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )

    first_job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "async_execution": False,
                "branch": "release/native-scan",
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Native baseline seed repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    ).json()["data"]
    first_run = client.post(f"/api/system/scheduled-jobs/{first_job['id']}/run", headers=headers)
    assert first_run.status_code == 200
    first_report_id = first_run.json()["data"]["result_summary"]["report_id"]

    secret_fingerprint = finding_fingerprint(
        {
            "committer_email": "alice@example.com",
            "file_path": "src/config.py",
            "line_number": 1,
            "rule_id": "secrets.hardcoded_credential",
        },
        {"branch": "release/native-scan", "repository_id": repository["id"]},
    )
    second_job = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "async_execution": False,
                "baseline_fingerprints": [secret_fingerprint],
                "branch": "release/native-scan",
                "quality_gate": {
                    "enabled": True,
                    "critical_max": 0,
                    "high_max": 0,
                    "medium_max": 0,
                },
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Native baseline repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    ).json()["data"]

    second_run = client.post(
        f"/api/system/scheduled-jobs/{second_job['id']}/run",
        headers=headers,
    )

    assert second_run.status_code == 200
    run_payload = second_run.json()["data"]
    assert run_payload["status"] == "succeeded"
    assert run_payload["records_imported"] == 1
    native_scan = run_payload["result_summary"]["execution_nodes"]["native_scan"]
    assert native_scan["suppressed_finding_count"] == 1
    assert native_scan["suppression_summary"]["baseline"] == 1
    assert native_scan["quality_gate"]["status"] == "failed"
    assert native_scan["quality_gate"]["violations"] == [
        {"limit": 0, "severity": "medium", "value": 1}
    ]

    second_report_id = run_payload["result_summary"]["report_id"]
    detail = client.get(
        f"/api/governance/code-inspections/{second_report_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    detail_payload = detail.json()["data"]
    report = detail_payload["report"]
    assert report["finding_count"] == 1
    assert report["suppressed_finding_count"] == 1
    assert report["quality_gate"]["status"] == "failed"
    assert report["previous_report_id"] == first_report_id
    assert report["previous_comparison"] == {
        "finding_delta": -1,
        "previous_finding_count": 2,
        "previous_report_id": first_report_id,
        "previous_severe_finding_count": 1,
        "severe_finding_delta": -1,
    }
    assert detail_payload["scan_summary"]["coverage"]["files_scanned"] >= 1
    assert detail_payload["scan_summary"]["rule_distribution"] == [
        {
            "category": "security",
            "finding_count": 1,
            "rule_id": "metadata.internal_address_exposure",
            "severity": "medium",
            "severe_finding_count": 0,
        }
    ]
    assert detail_payload["scan_summary"]["file_distribution"] == [
        {
            "file_path": "src/config.py",
            "finding_count": 1,
            "severe_finding_count": 0,
        }
    ]


def test_native_repository_inspection_runs_multiple_repositories_from_one_job(
    monkeypatch,
    tmp_path,
):
    app.state.store.reset()
    monkeypatch.setenv("CODE_SCAN_WORKDIR", str(tmp_path / "code-scan-workdir"))
    headers = auth_headers()
    product = create_product(
        headers,
        code="native-scan-multi-product",
        name="Native Scan Multi Repo",
    )
    local_repo_url = create_local_git_repository(tmp_path)
    repository_a = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )
    repository_b = create_local_scan_repository(
        headers,
        product["id"],
        remote_url=local_repo_url,
    )

    job_response = client.post(
        "/api/system/scheduled-jobs",
        json={
            "config_json": {
                "async_execution": False,
                "branch": "release/native-scan",
                "repository_ids": [repository_a["id"], repository_b["id"]],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": "Native multi repository inspection",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
        headers=headers,
    )
    assert job_response.status_code == 200
    job = job_response.json()["data"]

    run_response = client.post(
        f"/api/system/scheduled-jobs/{job['id']}/run",
        headers=headers,
    )

    assert run_response.status_code == 200
    run = run_response.json()["data"]
    assert run["status"] == "succeeded"
    assert run["records_imported"] == 4
    assert run["result_summary"]["report_count"] == 2
    assert set(run["result_summary"]["report_ids"]) == {
        run["result_summary"]["reports_by_repository"][repository_a["id"]]["report_id"],
        run["result_summary"]["reports_by_repository"][repository_b["id"]]["report_id"],
    }
    assert set(run["result_summary"]["reports_by_repository"]) == {
        repository_a["id"],
        repository_b["id"],
    }


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
                {
                    "severity_threshold": "critical",
                    "type": "create_task_for_severe_findings",
                },
            ],
            "schedule_type": "manual",
            "source_system": "repo-quality-scanner",
        },
        headers=headers,
    ).json()["data"]
    run = client.post(f"/api/system/scheduled-jobs/{job['id']}/run", headers=headers)
    assert run.status_code == 200
    report_id = run.json()["data"]["result_summary"]["report_id"]
    app.state.store.code_inspection_reports[report_id]["quality_gate"] = {
        "status": "failed",
        "violations": [{"metric": "critical", "actual": 1, "limit": 0}],
    }
    app.state.store.code_inspection_reports[report_id]["rules_version"] = "builtin-2026.06.16"
    app.state.store.code_inspection_reports[report_id]["scanner_version"] = "2026.06.16"
    app.state.store.code_inspection_reports[report_id]["suppressed_finding_count"] = 2
    app.state.store.code_inspection_reports[report_id]["suppression_summary"] = {
        "accepted_risk": 1,
        "baseline": 1,
        "ignored": 0,
        "severity_threshold": 0,
    }

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
    assert payload["sla"]["task_coverage_rate"] == 1
    assert payload["sla"]["covered_by_task_count"] == 1
    assert payload["sla"]["uncovered_task_finding_count"] == 0
    assert payload["sla"]["oldest_without_task_at"] is None
    assert payload["rule_distribution"][0]["rule_id"] == "SEC001"
    assert payload["rule_distribution"][0]["severe_finding_count"] == 1
    assert payload["repository_ranking"][0]["repository_id"] == repository["id"]
    assert payload["repository_ranking"][0]["risk_level"] == "critical"
    assert payload["branch_ranking"][0]["branch"] == "main"
    assert payload["committer_ranking"][0]["email"] == "alice@example.com"
    assert payload["committer_ranking"][0]["bug_count"] == 1
    assert payload["trend"][0]["report_count"] == 1
    assert payload["trend"][0]["quality_gate_passed_count"] == 0
    assert payload["trend"][0]["quality_gate_failed_count"] == 1
    assert payload["trend"][0]["quality_gate_skipped_count"] == 0
    assert payload["trend"][0]["quality_gate_unknown_count"] == 0
    assert payload["rule_governance"]["latest_report_rules_version"] == "builtin-2026.06.16"
    assert payload["rule_governance"]["latest_report_scanner_version"] == "2026.06.16"
    assert payload["rule_governance"]["mixed_rules_version"] is False
    assert payload["rule_governance"]["suppressed_finding_count"] == 2
    assert payload["rule_governance"]["report_with_suppression_count"] == 1
    assert payload["rule_governance"]["rule_version_distribution"] == [
        {"count": 1, "rules_version": "builtin-2026.06.16"}
    ]
    assert {"count": 1, "reason": "accepted_risk"} in payload["rule_governance"][
        "suppression_distribution"
    ]
    assert {"count": 1, "reason": "baseline"} in payload["rule_governance"][
        "suppression_distribution"
    ]

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
    assert user_payload["job"]["configured_branch"] == "main"
    assert user_payload["job"]["configured_repository_id"] == repository["id"]
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
