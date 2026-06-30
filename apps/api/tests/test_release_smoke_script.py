from __future__ import annotations

import importlib.util
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
    assert script_path.exists()
    assert script_path.stat().st_mode & 0o111

    content = script_path.read_text(encoding="utf-8")
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
        "validate_version_dashboard_next_actions",
        "validate_version_dashboard_branch_quality",
        "Version dashboard blocker missed source_type",
        "Version dashboard next action full-chain type drifted",
        "Version dashboard blocker missed reason",
        "Version dashboard blocker has unsupported severity",
        "Assistant version governance question should be deterministic",
        "Assistant iteration tool did not carry version dashboard next_actions",
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
        '"code-inspection-governance"',
        '"knowledge-index-health"',
        '"permission-visibility"',
        "run_regression_suite(",
        'suite == "runner-reliability"',
        'suite == "code-inspection-governance"',
        'suite == "knowledge-index-health"',
        'suite == "permission-visibility"',
        'StepResult("suite", suite)',
    ]:
        assert marker in content


def test_full_chain_regression_script_writes_structured_json_report():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    content = script_path.read_text(encoding="utf-8")

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
    assert "runner_reliability" in dashboard_coverage["skipped_keys"]


def test_full_chain_regression_script_supports_version_dashboard_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    content = script_path.read_text(encoding="utf-8")

    for marker in [
        '"version-dashboard"',
        "validate_version_dashboard_quick_regression(",
        'suite == "version-dashboard"',
        "/api/product-versions/{version['id']}/dashboard",
        "version_dashboard_quick",
        "version_dashboard_branch_quality",
        "version_dashboard_code_review",
        "pending_code_review_reports",
        "Version dashboard missed pending-scan branch quality summary",
        "Version dashboard quick check missed code review report",
        "Version dashboard quick check missed pending code review blocker",
        'source_type") == "code_review_report"',
        "release_evidence_blockers",
    ]:
        assert marker in content


def test_full_chain_regression_script_validates_runner_token_rotation():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    content = script_path.read_text(encoding="utf-8")

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


def test_full_chain_regression_script_supports_assistant_draft_governance_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    content = script_path.read_text(encoding="utf-8")

    for marker in [
        '"assistant-draft-governance"',
        "validate_assistant_draft_governance(",
        "/api/assistant/action-drafts/{draft['id']}/view",
        "/api/assistant/action-drafts/{draft['id']}/confirm",
        "assistant_draft_governance",
        "permission_status",
        "impact_changed_field_count",
        "latest_audit_event_type",
        "assistant_action_draft.confirmed",
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_code_inspection_governance_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    content = script_path.read_text(encoding="utf-8")

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
    content = script_path.read_text(encoding="utf-8")

    for marker in [
        '"knowledge-index-health"',
        "validate_knowledge_index_health_quick_regression(",
        'suite == "knowledge-index-health"',
        "/api/knowledge/documents",
        "/api/knowledge/index-health",
        "/api/knowledge/search",
        "knowledge_index_health_quick",
        "Knowledge index health missed readable permission scope labels",
        "Knowledge index health did not expose usable retrieval mode",
        "Knowledge index health missed vector-backfill warning for text-indexed document",
        "Knowledge search did not retrieve created document",
        "permission_scope",
        "retrieval_modes",
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_permission_visibility_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    content = script_path.read_text(encoding="utf-8")

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
