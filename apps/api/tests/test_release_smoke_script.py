from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


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
        "/api/knowledge/index-health",
        "/api/knowledge/search",
        "retrieval_modes",
        "Version dashboard missed knowledge deposit row",
        "/api/product-versions/",
        "/dashboard",
        "/api/lifecycle/full-chain",
        "/api/dashboard/it-team",
        "/api/assistant/chat",
        "committer_distribution",
        "committer_governance",
        "active_severe_finding_count",
        "covered_by_bug_count",
        "covered_by_task_count",
        "action_label",
        "action_target_type",
        "resolution_hint",
        "validate_version_dashboard_blocker_actions",
        "Version dashboard blocker missed source_type",
        "Version dashboard blocker missed reason",
        "Version dashboard blocker has unsupported severity",
        "blocker_actions",
        "缺少成功发布记录",
        "action_target_type\") == \"product_version\"",
        "release_evidence_blockers",
        "validate_ai_executor_runner_reliability",
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
        'choices=["full", "runner-reliability", "version-dashboard", "assistant-draft-governance"]',
        "run_regression_suite(",
        'suite == "runner-reliability"',
        'StepResult("suite", suite)',
    ]:
        assert marker in content


def test_full_chain_regression_script_supports_version_dashboard_suite():
    script_path = REPO_ROOT / "scripts" / "full_chain_regression.py"
    content = script_path.read_text(encoding="utf-8")

    for marker in [
        '"version-dashboard"',
        "validate_version_dashboard_quick_regression(",
        'suite == "version-dashboard"',
        "/api/product-versions/{version['id']}/dashboard",
        "version_dashboard_quick",
        "version_dashboard_code_review",
        "pending_code_review_reports",
        "Version dashboard quick check missed code review report",
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
