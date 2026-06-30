from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_full_chain_regression_module():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    spec = importlib.util.spec_from_file_location("full_chain_regression", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_full_chain_version_dashboard_module():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression_version_dashboard.py"
    spec = importlib.util.spec_from_file_location(
        "full_chain_regression_version_dashboard",
        script_path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_smoke_script_runs_fixed_readiness_and_web_gates():
    script_path = REPO_ROOT / "scripts" / "release_smoke.sh"
    assert script_path.exists()
    assert script_path.stat().st_mode & 0o111

    content = script_path.read_text(encoding="utf-8")
    assert "scripts/production_readiness_check.py" in content
    assert "--rebuild" in content
    assert "--web-smoke" in content
    assert "READINESS_API_BASE_URL" in content
    assert "READINESS_WEB_BASE_URL" in content


def test_web_page_smoke_fails_on_network_4xx_or_5xx_responses():
    script_path = REPO_ROOT / "scripts" / "web_page_smoke.mjs"
    content = script_path.read_text(encoding="utf-8")

    assert "Network.enable" in content
    assert "Network.responseReceived" in content
    assert "collectRelevantNetworkFailures" in content
    assert "network errors:" in content
    assert "--viewport WIDTHxHEIGHT" in content
    assert "Emulation.setDeviceMetricsOverride" in content
    assert "route viewport check" in content


def test_full_chain_regression_script_covers_public_api_workflow():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    code_inspection_path = REPO_ROOT / "scripts" / "full_chain_regression_code_inspection.py"
    runner_path = REPO_ROOT / "scripts" / "full_chain_regression_runner.py"
    version_dashboard_path = REPO_ROOT / "scripts" / "full_chain_regression_version_dashboard.py"
    assert script_path.exists()
    assert script_path.stat().st_mode & 0o111

    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + code_inspection_path.read_text(encoding="utf-8")
        + "\n"
        + runner_path.read_text(encoding="utf-8")
        + "\n"
        + version_dashboard_path.read_text(encoding="utf-8")
    )
    for marker in [
        "http.client",
        "/api/insights/user-feedback",
        "convert-requirement",
        "/api/requirements/batch-schedule",
        "/api/ai-tasks/{task_id}/start",
        "execution_mode",
        "deterministic",
        "native_full_scan",
        "quality_gate",
        "quality_gate_failed_count",
        "quality_gate_violations",
        "governance_pressure",
        "quality_gate_failed_report_count",
        "quality_gate_violation_count",
        "uncovered_bug_finding_count",
        "uncovered_task_finding_count",
        "code_inspection_governance_pressure",
        "Code inspection dashboard missed governance pressure summary",
        "/api/knowledge/index-health",
        "/api/knowledge/search",
        "retrieval_modes",
        "Version dashboard missed knowledge deposit row",
        "searchable_knowledge_deposits",
        "Version dashboard missed searchable knowledge deposit summary.",
        "knowledge_retrieval_mode",
        "Version dashboard knowledge deposit missed chunk health",
        "/api/product-versions/",
        "/dashboard",
        "/api/lifecycle/full-chain",
        "/api/dashboard/it-team",
        "/api/assistant/chat",
        "committer_distribution",
        "committer_governance",
        "code_inspection_trend_comparison",
        "previous_comparison",
        "previous_report_id",
        "previous_finding_count",
        "severe_finding_delta",
        "active_severe_finding_count",
        "covered_by_bug_count",
        "covered_by_task_count",
        "action_label",
        "action_target_type",
        "resolution_hint",
        "validate_version_dashboard_blocker_actions",
        "validate_version_dashboard_delivery_stage_overview",
        "validate_version_dashboard_next_actions",
        "validate_version_dashboard_governance_conclusion",
        "validate_version_dashboard_branch_quality",
        "validate_version_dashboard_evidence_coverage",
        "validate_version_dashboard_status_impact",
        "validate_version_dashboard_status_impact_projection",
        "evidence_coverage",
        "Version dashboard evidence coverage score drifted",
        "governance_conclusion",
        "Version dashboard blocker missed source_type",
        "Version dashboard governance conclusion missed next_action",
        "Version dashboard next action full-chain type drifted",
        "Version dashboard blocker missed reason",
        "Version dashboard blocker has unsupported severity",
        "Assistant version governance question should be deterministic",
        "Assistant iteration tool did not carry version dashboard next_actions",
        "status_impact drifted from version dashboard",
        'label="Assistant iteration tool"',
        'label="Persisted assistant iteration tool"',
        "branch_quality_governance",
        "branch_quality_action_required",
        "branch_quality_active_severe_findings",
        "accepted_risk_count",
        "expired_accepted_risk_count",
        "false_positive_count",
        "pending_suppression_count",
        "branch_quality_pending_scan",
        "Version dashboard branch quality status mismatch",
        "blocker_actions",
        "缺少成功发布记录",
        'action_target_type") == "product_version"',
        "release_evidence_blockers",
        "successful_releases",
        "failed_releases",
        "Version dashboard release stage missed release evidence counts",
        "validate_ai_executor_runner_reliability",
        "validate_assistant_draft_governance",
        "validate_permission_visibility_quick_regression",
        "validate_runner_health_alert_projection",
        "runner_never_connected",
        "runner_health_alert",
        "health_alert",
        "/api/system/ai-executor-tasks/claim",
        "/api/system/ai-executor-tasks/timeout-scan",
        "requeued_task_ids",
        "dead_letter_task_ids",
        "AI_EXECUTOR_TASK_LEASE_EXPIRED",
        "user_feedback_status_counts",
        "latest_high_severity_bugs",
        "/api/assistant/conversations/{conversation_id}/messages",
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_targeted_suites():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    content = script_path.read_text(encoding="utf-8")

    for marker in [
        "FULL_CHAIN_SUITE",
        "--suite",
        '"all-targeted"',
        '"assistant-qa"',
        '"code-inspection-governance"',
        '"knowledge-index-health"',
        '"permission-visibility"',
        "REGRESSION_TARGETED_SUITE_NAMES",
        "run_regression_suite(",
        'suite == "all-targeted"',
        'suite == "assistant-qa"',
        'suite == "runner-reliability"',
        'suite == "code-inspection-governance"',
        'suite == "knowledge-index-health"',
        'suite == "permission-visibility"',
        'StepResult("suite", suite)',
    ]:
        assert marker in content


def test_full_chain_regression_script_writes_structured_json_report():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    suite_path = REPO_ROOT / "scripts" / "full_chain_regression_suites.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + suite_path.read_text(encoding="utf-8")
    )

    for marker in [
        "FULL_CHAIN_JSON_OUTPUT",
        "--json-output",
        "build_regression_report(",
        "regression_suite_coverage(",
        "validate_regression_suite_coverage(",
        "write_json_report(",
        '"coverage": regression_suite_coverage(suite)',
        '"covered_keys": covered_keys',
        '"skipped_keys": skipped_keys',
        '"is_complete_chain": not skipped_keys',
        '"status": status',
        '"steps": [{"detail": step.detail, "name": step.name} for step in steps]',
        'status="passed"',
        'status="failed"',
        "Full-chain regression report written to",
    ]:
        assert marker in content


def test_full_chain_regression_suite_metadata_is_split_from_runner():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    suite_path = REPO_ROOT / "scripts" / "full_chain_regression_suites.py"
    script_content = script_path.read_text(encoding="utf-8")
    suite_content = suite_path.read_text(encoding="utf-8")

    assert "from full_chain_regression_suites import" in script_content
    assert "REGRESSION_SUITE_DOMAINS: dict" not in script_content
    assert "REGRESSION_OBJECTIVE_DOMAINS: tuple" not in script_content
    assert "def regression_suite_coverage(" not in script_content
    assert "REGRESSION_SUITE_DOMAINS: dict" in suite_content
    assert "REGRESSION_OBJECTIVE_DOMAINS: tuple" in suite_content
    assert "def regression_suite_coverage(" in suite_content


def test_full_chain_regression_runner_reliability_is_split_from_runner():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    runner_path = REPO_ROOT / "scripts" / "full_chain_regression_runner.py"
    script_content = script_path.read_text(encoding="utf-8")
    runner_content = runner_path.read_text(encoding="utf-8")

    assert (
        "from full_chain_regression_runner import "
        "validate_ai_executor_runner_reliability"
    ) in script_content
    assert "def validate_ai_executor_runner_reliability(" not in script_content
    assert "def validate_runner_token_rotation(" not in script_content
    assert "def validate_runner_health_alert_projection(" not in script_content
    assert "def validate_ai_executor_runner_reliability(" in runner_content
    assert "def validate_runner_token_rotation(" in runner_content
    assert "def validate_runner_health_alert_projection(" in runner_content


def test_full_chain_regression_version_dashboard_checks_are_split_from_runner():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_version_dashboard.py"
    script_content = script_path.read_text(encoding="utf-8")
    helper_content = helper_path.read_text(encoding="utf-8")

    assert "from full_chain_regression_version_dashboard import" in script_content
    assert "def validate_version_dashboard_blocker_actions(" not in script_content
    assert "def validate_version_dashboard_delivery_stage_overview(" not in script_content
    assert "def validate_version_dashboard_next_actions(" not in script_content
    assert "def validate_version_dashboard_governance_conclusion(" not in script_content
    assert "def validate_version_dashboard_branch_quality(" not in script_content
    assert "def validate_version_dashboard_evidence_coverage(" not in script_content
    assert "def validate_version_dashboard_status_impact(" not in script_content
    assert "VERSION_DASHBOARD_BLOCKER_SOURCE_PRIORITY" not in script_content
    assert "VERSION_DASHBOARD_EVIDENCE_STATUSES" not in script_content
    assert "def validate_version_dashboard_blocker_actions(" in helper_content
    assert "def validate_version_dashboard_delivery_stage_overview(" in helper_content
    assert "def validate_version_dashboard_next_actions(" in helper_content
    assert "def validate_version_dashboard_governance_conclusion(" in helper_content
    assert "def validate_version_dashboard_branch_quality(" in helper_content
    assert "def validate_version_dashboard_evidence_coverage(" in helper_content
    assert "def validate_version_dashboard_status_impact(" in helper_content
    assert "VERSION_DASHBOARD_BLOCKER_SOURCE_PRIORITY" in helper_content
    assert "VERSION_DASHBOARD_EVIDENCE_STATUSES" in helper_content


def test_full_chain_regression_validates_version_dashboard_evidence_coverage():
    module = _load_full_chain_version_dashboard_module()
    domain_statuses = {
        "requirements": ("success", "covered"),
        "tasks": ("success", "covered"),
        "branches": ("error", "blocked"),
        "inspections": ("warning", "missing"),
        "code-reviews": ("error", "blocked"),
        "bugs": ("error", "blocked"),
        "knowledge-deposits": ("warning", "risk"),
        "releases": ("error", "blocked"),
        "status-impact": ("success", "covered"),
    }
    domains = [
        {
            "action_label": "处理",
            "action_target_id": "version_demo",
            "action_target_type": "product_version",
            "detail": f"{key} detail",
            "key": key,
            "level": level,
            "status": status,
            "title": key,
            "value": key,
        }
        for key, (level, status) in domain_statuses.items()
    ]
    dashboard = {
        "evidence_coverage": {
            "blocking_domains": 4,
            "covered_domains": 3,
            "domains": domains,
            "gap_domains": 2,
            "level": "error",
            "score": 33,
            "summary": "4 个交付域存在阻断，需先处理阻塞队列。",
            "total_domains": 9,
        },
        "summary": {"blockers": 4},
    }

    assert module.validate_version_dashboard_evidence_coverage(
        dashboard,
        require_blockers=True,
    ) == dashboard["evidence_coverage"]


def test_full_chain_regression_assistant_draft_checks_are_split_from_runner():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_assistant_drafts.py"
    script_content = script_path.read_text(encoding="utf-8")
    helper_content = helper_path.read_text(encoding="utf-8")

    assert (
        "from full_chain_regression_assistant_drafts import "
        "validate_assistant_draft_governance"
    ) in script_content
    assert "def validate_assistant_draft_governance(" not in script_content
    assert "DRAFT_PRECHECK_FAILED" not in script_content
    assert "assistant_action_draft.retry_requested" not in script_content
    assert "def validate_assistant_draft_governance(" in helper_content
    assert "DRAFT_PRECHECK_FAILED" in helper_content
    assert "assistant_action_draft.retry_requested" in helper_content


def test_full_chain_regression_knowledge_index_checks_are_split_from_runner():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_knowledge.py"
    script_content = script_path.read_text(encoding="utf-8")
    helper_content = helper_path.read_text(encoding="utf-8")

    assert (
        "from full_chain_regression_knowledge import "
        "validate_knowledge_index_health_quick_regression"
    ) in script_content
    assert "def validate_knowledge_index_health_quick_regression(" not in script_content
    assert "Knowledge index health missed readable permission scope labels" not in script_content
    assert "/api/knowledge/documents/{document_id}/retry-index" not in script_content
    assert "def validate_knowledge_index_health_quick_regression(" in helper_content
    assert "Knowledge index health missed readable permission scope labels" in helper_content
    assert "/api/knowledge/documents/{document_id}/retry-index" in helper_content


def test_full_chain_regression_code_inspection_checks_are_split_from_runner():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_code_inspection.py"
    script_content = script_path.read_text(encoding="utf-8")
    helper_content = helper_path.read_text(encoding="utf-8")

    assert (
        "from full_chain_regression_code_inspection import "
        "validate_code_inspection_governance_quick_regression"
    ) in script_content
    assert "def validate_code_inspection_governance_quick_regression(" not in script_content
    assert "version_dashboard_code_inspection_governance" not in script_content
    assert "def validate_code_inspection_governance_quick_regression(" in helper_content
    assert "version_dashboard_code_inspection_governance" in helper_content
    assert "native_full_scan" in helper_content
    assert "create_bug_for_severe_findings" in helper_content
    assert "create_task_for_severe_findings" in helper_content


def test_full_chain_regression_assistant_qa_checks_are_split_from_runner():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_assistant_qa.py"
    script_content = script_path.read_text(encoding="utf-8")
    helper_content = helper_path.read_text(encoding="utf-8")

    assert (
        "from full_chain_regression_assistant_qa import "
        "validate_assistant_qa_quick_regression"
    ) in script_content
    assert "def validate_assistant_qa_quick_regression(" not in script_content
    assert '"assistant_qa_quick"' not in script_content
    assert "Assistant QA history missed iteration tool result" not in script_content
    assert "def validate_assistant_qa_quick_regression(" in helper_content
    assert '"assistant_qa_quick"' in helper_content
    assert "Assistant QA history missed iteration tool result" in helper_content


def test_full_chain_regression_permission_visibility_checks_are_split_from_runner():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_permissions.py"
    script_content = script_path.read_text(encoding="utf-8")
    helper_content = helper_path.read_text(encoding="utf-8")

    assert (
        "from full_chain_regression_permissions import "
        "validate_permission_visibility_quick_regression"
    ) in script_content
    assert "def validate_permission_visibility_quick_regression(" not in script_content
    assert "permission_visibility_role_preview" not in script_content
    assert "Permission diagnostics missed readable effective scope" not in script_content
    assert "def validate_permission_visibility_quick_regression(" in helper_content
    assert "permission_visibility_role_preview" in helper_content
    assert "Permission diagnostics missed readable effective scope" in helper_content


def test_full_chain_regression_report_includes_suite_coverage():
    module = _load_full_chain_regression_module()

    report = module.build_regression_report(
        api_base_url="http://api.test",
        duration_ms=123,
        error=None,
        finished_at="2026-06-30T00:00:01+00:00",
        started_at="2026-06-30T00:00:00+00:00",
        status="passed",
        steps=[module.StepResult("suite", "full")],
        suite="full",
        task_execution_mode="deterministic",
    )

    coverage = report["coverage"]
    assert coverage["suite"] == "full"
    assert coverage["is_complete_chain"] is True
    assert coverage["skipped_keys"] == []
    assert "assistant_draft_governance" in coverage["covered_keys"]
    assert "permission_visibility" in coverage["covered_keys"]
    assert coverage["covered_domain_count"] == coverage["objective_domain_count"]

    dashboard_coverage = module.regression_suite_coverage("version-dashboard")
    assert dashboard_coverage["is_complete_chain"] is False
    assert "version_dashboard" in dashboard_coverage["covered_keys"]
    assert "bug_remediation" in dashboard_coverage["covered_keys"]
    assert "runner_reliability" in dashboard_coverage["skipped_keys"]

    targeted_coverage = module.regression_suite_coverage("all-targeted")
    assert targeted_coverage["is_complete_chain"] is False
    assert "runner_reliability" in targeted_coverage["covered_keys"]
    assert "assistant_qa" in targeted_coverage["covered_keys"]
    assert "assistant_draft_governance" in targeted_coverage["covered_keys"]
    assert "permission_visibility" in targeted_coverage["covered_keys"]
    assert "full_chain_trace" in targeted_coverage["skipped_keys"]
    assert targeted_coverage["covered_domain_count"] > dashboard_coverage["covered_domain_count"]


def test_full_chain_regression_all_targeted_suite_aggregates_fast_suite_results(monkeypatch):
    module = _load_full_chain_regression_module()
    called: list[str] = []

    class FakeClient:
        def login(self, username: str, password: str):
            del password
            called.append("runner-reliability")
            return {"user": {"username": username}}

    def fixture_repository(slug: str, branch: str):
        del slug, branch
        return Path("/tmp/full-chain-fixture")

    def runner_reliability(client, *, repo_path, slug):
        del client, repo_path, slug
        return [module.StepResult("runner_reliability", "ok")]

    def suite_result(name: str):
        def _result(*args, **kwargs):
            del args, kwargs
            called.append(name)
            return [module.StepResult(name, "ok")]

        return _result

    monkeypatch.setattr(module, "create_fixture_repository", fixture_repository)
    monkeypatch.setattr(module, "validate_ai_executor_runner_reliability", runner_reliability)
    monkeypatch.setattr(
        module,
        "validate_version_dashboard_quick_regression",
        suite_result("version_dashboard"),
    )
    monkeypatch.setattr(
        module,
        "validate_assistant_qa_quick_regression",
        suite_result("assistant_qa"),
    )
    monkeypatch.setattr(
        module,
        "validate_assistant_draft_governance",
        suite_result("assistant_draft_governance"),
    )
    monkeypatch.setattr(
        module,
        "validate_code_inspection_governance_quick_regression",
        suite_result("code_inspection_governance"),
    )
    monkeypatch.setattr(
        module,
        "validate_knowledge_index_health_quick_regression",
        suite_result("knowledge_index_health"),
    )
    monkeypatch.setattr(
        module,
        "validate_permission_visibility_quick_regression",
        suite_result("permission_visibility"),
    )

    results = module.run_regression_suite(
        FakeClient(),
        suite="all-targeted",
        task_execution_mode="deterministic",
        username="admin@example.com",
        password="admin123",
    )

    assert [item.name for item in results[:2]] == ["suite", "coverage"]
    result_names = [item.name for item in results]
    assert "runner-reliability:runner_reliability" in result_names
    assert "version-dashboard:version_dashboard" in result_names
    assert "assistant-qa:assistant_qa" in result_names
    assert "assistant-draft-governance:assistant_draft_governance" in result_names
    assert "code-inspection-governance:code_inspection_governance" in result_names
    assert "knowledge-index-health:knowledge_index_health" in result_names
    assert "permission-visibility:permission_visibility" in result_names
    assert called == [
        "runner-reliability",
        "version_dashboard",
        "assistant_qa",
        "assistant_draft_governance",
        "code_inspection_governance",
        "knowledge_index_health",
        "permission_visibility",
    ]


def test_full_chain_regression_failed_json_report_keeps_suite_coverage_steps(
    monkeypatch,
    tmp_path,
):
    module = _load_full_chain_regression_module()
    report_path = tmp_path / "full-chain-failed.json"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

    def fail_regression(*args, **kwargs):
        del args, kwargs
        raise module.RegressionError("boom")

    monkeypatch.setattr(module, "ApiClient", FakeClient)
    monkeypatch.setattr(module, "run_regression_suite", fail_regression)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "full_chain_regression.py",
            "--suite",
            "all-targeted",
            "--json-output",
            str(report_path),
        ],
    )

    assert module.main() == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["status"] == "failed"
    assert report["suite"] == "all-targeted"
    assert report["error"] == "boom"
    assert report["coverage"]["is_complete_chain"] is False
    assert [step["name"] for step in report["steps"]] == ["suite", "coverage"]


def test_full_chain_regression_failed_json_report_catches_helper_assertion(
    monkeypatch,
    tmp_path,
):
    module = _load_full_chain_regression_module()
    report_path = tmp_path / "full-chain-helper-failed.json"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

    def fail_regression(*args, **kwargs):
        del args, kwargs
        raise AssertionError("helper assertion failed")

    monkeypatch.setattr(module, "ApiClient", FakeClient)
    monkeypatch.setattr(module, "run_regression_suite", fail_regression)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "full_chain_regression.py",
            "--suite",
            "version-dashboard",
            "--json-output",
            str(report_path),
        ],
    )

    assert module.main() == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["status"] == "failed"
    assert report["suite"] == "version-dashboard"
    assert report["error"] == "helper assertion failed"
    assert [step["name"] for step in report["steps"]] == ["suite", "coverage"]


def test_full_chain_regression_script_supports_version_dashboard_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_version_dashboard.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + helper_path.read_text(encoding="utf-8")
    )

    for marker in [
        '"version-dashboard"',
        "validate_version_dashboard_quick_regression(",
        'suite == "version-dashboard"',
        "/api/product-versions/{version['id']}/dashboard",
        "/api/bugs",
        "version_dashboard_quick",
        "version_dashboard_branch_quality",
        "version_dashboard_code_review",
        "delivery_stage_overview",
        "validate_version_dashboard_status_impact(",
        "Version dashboard status_impact target status drifted",
        "Version dashboard delivery stage order drifted",
        "pending_code_review_reports",
        "Version dashboard missed pending-scan branch quality summary",
        "Version dashboard quick check missed code review report",
        "Version dashboard quick check missed pending code review blocker",
        "Version dashboard quick check missed Bug summary",
        "Version dashboard quick check missed Bug row",
        "Version dashboard quick check missed open Bug status count",
        "Version dashboard quick check missed Bug blocker",
        "Version dashboard next actions should prioritize blocker Bug",
        "bug_status_counts",
        'source_type") == "code_review_report"',
        'source_type") == "bug"',
        "release_evidence_blockers",
    ]:
        assert marker in content


def test_full_chain_regression_script_validates_runner_token_rotation():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    runner_path = REPO_ROOT / "scripts" / "full_chain_regression_runner.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + runner_path.read_text(encoding="utf-8")
    )

    for marker in [
        "validate_runner_token_rotation(",
        "/api/system/ai-executor-runners/{runner['id']}/rotate-token",
        "old runner token was still accepted after rotation",
        "runner_token_rotation",
        "token_version",
        "Runner heartbeat with rotated token did not restore online health",
        "Runner heartbeat with rotated token still returned health_alert",
    ]:
        assert marker in content


def test_full_chain_regression_script_validates_runner_cancel_retry():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    runner_path = REPO_ROOT / "scripts" / "full_chain_regression_runner.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + runner_path.read_text(encoding="utf-8")
    )

    for marker in [
        "validate_runner_cancel_retry(",
        "full-chain-runner-cancel-retry",
        "runner_cancel_retry",
        "/api/system/ai-executor-tasks/{cancel_task_id}/logs",
        "/api/system/ai-executor-tasks/{cancel_task_id}/cancel",
        "/api/system/ai-executor-tasks/{cancel_task_id}/retry",
        "/api/system/ai-executor-tasks/{retry_task_id}/complete",
        "AI_EXECUTOR_TASK_CANCELLED",
        "retry_of_task_id",
        "retry_history",
        "AI_EXECUTOR_TASK_NOT_RETRYABLE",
        "ai_executor_task.retry_requested",
        "lease/dead-letter/cancel-retry gate",
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_assistant_draft_governance_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_assistant_drafts.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + helper_path.read_text(encoding="utf-8")
    )

    for marker in [
        '"assistant-draft-governance"',
        "validate_assistant_draft_governance(",
        "/api/assistant/action-drafts/{draft['id']}/view",
        "/api/assistant/action-drafts/{draft['id']}/confirm",
        "assistant_draft_governance",
        "permission_status",
        "impact_changed_field_count",
        "latest_audit_event_type",
        "DRAFT_PRECHECK_FAILED",
        "/api/assistant/action-drafts/{retry_draft['id']}/retry",
        "failure_history",
        "last_failure_code",
        "assistant_action_draft.retry_requested",
        "assistant_action_draft.confirmed",
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_assistant_qa_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_assistant_qa.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + helper_path.read_text(encoding="utf-8")
    )

    for marker in [
        '"assistant-qa"',
        "validate_assistant_qa_quick_regression(",
        'suite == "assistant-qa"',
        "/api/assistant/chat",
        "/api/assistant/conversations/{conversation_id}/messages",
        "assistant-deterministic",
        "assistant.iteration",
        "assistant_qa_quick",
        "Assistant QA next_actions drifted from version dashboard",
        "Assistant QA governance_conclusion drifted from version dashboard",
        "validate_version_dashboard_status_impact_projection(",
        'label="Assistant QA"',
        'label="Assistant QA history"',
        "Assistant QA history missed iteration tool result",
        "product_version",
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_code_inspection_governance_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_code_inspection.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + helper_path.read_text(encoding="utf-8")
    )

    for marker in [
        '"code-inspection-governance"',
        "validate_code_inspection_governance_quick_regression(",
        'suite == "code-inspection-governance"',
        "native_full_scan",
        "quality_gate_violations",
        "code_inspection_governance_pressure",
        "Code inspection governance pressure did not close Bug coverage",
        "Code inspection committer governance did not close the loop",
        "inspection_writeback",
        "code_inspection_trend_comparison",
        "version_dashboard_code_inspection_governance",
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_knowledge_index_health_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_knowledge.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + helper_path.read_text(encoding="utf-8")
    )

    for marker in [
        '"knowledge-index-health"',
        "validate_knowledge_index_health_quick_regression(",
        'suite == "knowledge-index-health"',
        "/api/knowledge/documents",
        "/api/knowledge/index-health",
        "/api/knowledge/search",
        "/api/knowledge/documents/{document_id}/retry-index",
        "index_failed",
        "knowledge_index_health_quick",
        "Knowledge index health missed readable permission scope labels",
        "Knowledge index health did not expose usable retrieval mode",
        "Knowledge index health missed vector-backfill warning for text-indexed document",
        "Knowledge index health missed retry issue for failed document",
        "Knowledge search did not retrieve created document",
        "Knowledge search did not retrieve document after retry-index",
        "permission_scope",
        "retrieval_modes",
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_permission_visibility_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    helper_path = REPO_ROOT / "scripts" / "full_chain_regression_permissions.py"
    content = (
        script_path.read_text(encoding="utf-8")
        + "\n"
        + helper_path.read_text(encoding="utf-8")
    )

    for marker in [
        '"permission-visibility"',
        "validate_permission_visibility_quick_regression(",
        'suite == "permission-visibility"',
        "/api/system/roles",
        "/api/system/permissions/matrix",
        "/api/system/permissions/diagnostics",
        "menu_permission_gap",
        "missing_menu_permission_codes",
        "scope_name",
        "access_preview",
        "visible_menus",
        "operation_permissions",
        "scope_groups",
        "permission_visibility_role_preview",
        "permission_visibility_matrix",
        "permission_visibility_diagnostics",
        "Permission diagnostics missed readable effective scope",
    ]:
        assert marker in content
