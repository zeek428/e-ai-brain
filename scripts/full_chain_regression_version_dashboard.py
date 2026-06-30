from __future__ import annotations

from typing import Any


VERSION_DASHBOARD_BLOCKER_SEVERITIES = {"info", "low", "medium", "high", "critical", "blocker"}
VERSION_DASHBOARD_BLOCKER_SEVERITY_PRIORITY = {
    "blocker": 1,
    "critical": 1,
    "high": 1,
    "medium": 2,
    "low": 3,
}
VERSION_DASHBOARD_BLOCKER_SOURCE_PRIORITY = {
    "bug": 1,
    "jenkins_release": 2,
    "code_inspection_report": 3,
    "code_review_report": 4,
    "requirement": 5,
    "product_version_branch_config": 6,
}
VERSION_DASHBOARD_FULL_CHAIN_SUBJECT_TYPES = {
    "bug",
    "code_inspection_report",
    "code_review_report",
    "jenkins_release",
    "product_version",
    "product_version_branch_config",
    "requirement",
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_version_dashboard_blocker_actions(blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        _assert(blocker.get("source_type"), f"Version dashboard blocker missed source_type: {blocker}")
        _assert(blocker.get("title"), f"Version dashboard blocker missed title: {blocker}")
        _assert(blocker.get("reason"), f"Version dashboard blocker missed reason: {blocker}")
        severity = str(blocker.get("severity") or "").lower()
        _assert(
            severity in VERSION_DASHBOARD_BLOCKER_SEVERITIES,
            f"Version dashboard blocker has unsupported severity: {blocker}",
        )
        _assert(blocker.get("action_label"), f"Version dashboard blocker missed action_label: {blocker}")
        _assert(blocker.get("action_target_type"), f"Version dashboard blocker missed action_target_type: {blocker}")
        _assert(blocker.get("action_target_id"), f"Version dashboard blocker missed action_target_id: {blocker}")
        _assert(blocker.get("resolution_hint"), f"Version dashboard blocker missed resolution_hint: {blocker}")


def _version_dashboard_blocker_sort_key(blocker: dict[str, Any]) -> tuple[int, int, str, str]:
    severity = str(blocker.get("severity") or "").lower()
    source_type = str(blocker.get("source_type") or "")
    return (
        VERSION_DASHBOARD_BLOCKER_SEVERITY_PRIORITY.get(severity, 4),
        VERSION_DASHBOARD_BLOCKER_SOURCE_PRIORITY.get(source_type, 99),
        str(blocker.get("title") or ""),
        str(blocker.get("action_target_id") or blocker.get("id") or ""),
    )


def _version_dashboard_full_chain_subject(
    blocker: dict[str, Any],
) -> tuple[str | None, str | None]:
    source_type = str(blocker.get("source_type") or "")
    blocker_id = blocker.get("id")
    if source_type in VERSION_DASHBOARD_FULL_CHAIN_SUBJECT_TYPES and blocker_id:
        return source_type, str(blocker_id)
    action_target_type = str(blocker.get("action_target_type") or "")
    action_target_id = blocker.get("action_target_id")
    if (
        action_target_type in VERSION_DASHBOARD_FULL_CHAIN_SUBJECT_TYPES
        and action_target_id
    ):
        return action_target_type, str(action_target_id)
    return None, None


def validate_version_dashboard_next_actions(
    dashboard: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    next_actions = dashboard.get("next_actions")
    _assert(
        isinstance(next_actions, list),
        f"Version dashboard next_actions is not a list: {next_actions}",
    )
    if not blockers:
        _assert(
            next_actions == [],
            f"Version dashboard next_actions should be empty: {next_actions}",
        )
        return
    expected_blockers = sorted(blockers, key=_version_dashboard_blocker_sort_key)[:3]
    _assert(
        len(next_actions) == len(expected_blockers),
        (
            "Version dashboard next_actions should expose top "
            f"{len(expected_blockers)} blockers: {next_actions}"
        ),
    )
    for index, (action, blocker) in enumerate(
        zip(next_actions, expected_blockers),
        start=1,
    ):
        _assert(
            action.get("priority") == index,
            f"Version dashboard next action priority drifted: {action}",
        )
        for field in (
            "action_label",
            "action_target_id",
            "action_target_type",
            "reason",
            "resolution_hint",
            "severity",
            "source_type",
            "title",
        ):
            _assert(
                action.get(field) == blocker.get(field),
                (
                    f"Version dashboard next action {field} drifted: "
                    f"action={action}, blocker={blocker}"
                ),
            )
        _assert(
            action.get("source_label"),
            f"Version dashboard next action missed source_label: {action}",
        )
        subject_type, subject_id = _version_dashboard_full_chain_subject(blocker)
        _assert(
            action.get("full_chain_subject_type") == subject_type,
            (
                "Version dashboard next action full-chain type drifted: "
                f"action={action}, blocker={blocker}"
            ),
        )
        _assert(
            action.get("full_chain_subject_id") == subject_id,
            (
                "Version dashboard next action full-chain id drifted: "
                f"action={action}, blocker={blocker}"
            ),
        )


def validate_version_dashboard_governance_conclusion(
    dashboard: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    conclusion = dashboard.get("governance_conclusion")
    _assert(
        isinstance(conclusion, dict),
        f"Version dashboard governance_conclusion is not an object: {conclusion}",
    )
    for field in ("detail", "level", "next_action", "risks", "title", "value"):
        _assert(
            field in conclusion,
            f"Version dashboard governance_conclusion missed {field}: {conclusion}",
        )
    _assert(
        conclusion.get("title") == "版本治理结论",
        f"Version dashboard governance conclusion title drifted: {conclusion}",
    )
    _assert(
        conclusion.get("level") in {"error", "info", "success", "warning"},
        f"Version dashboard governance conclusion level unsupported: {conclusion}",
    )
    _assert(
        isinstance(conclusion.get("risks"), list),
        f"Version dashboard governance conclusion risks is not a list: {conclusion}",
    )
    _assert(
        conclusion.get("value"),
        f"Version dashboard governance conclusion missed value: {conclusion}",
    )
    _assert(
        conclusion.get("detail"),
        f"Version dashboard governance conclusion missed detail: {conclusion}",
    )
    _assert(
        conclusion.get("next_action"),
        f"Version dashboard governance conclusion missed next_action: {conclusion}",
    )
    if blockers:
        blocker_count = int((dashboard.get("summary") or {}).get("blockers") or len(blockers))
        _assert(
            conclusion.get("level") in {"error", "warning"},
            f"Version dashboard governance conclusion should warn when blockers exist: {conclusion}",
        )
        _assert(
            any(str(risk) == f"发布阻塞 {blocker_count}" for risk in conclusion.get("risks", [])),
            (
                "Version dashboard governance conclusion missed blocker risk label: "
                f"blockers={blocker_count}, conclusion={conclusion}"
            ),
        )


def validate_version_dashboard_branch_quality(
    dashboard: dict[str, Any],
    *,
    branch_config_id: str,
    branch_name: str,
    expected_status: str,
    report_id: str | None = None,
) -> dict[str, Any]:
    summary = dashboard.get("summary") or {}
    branch_quality_governance = dashboard.get("branch_quality_governance") or []
    _assert(
        isinstance(branch_quality_governance, list),
        f"Version dashboard branch quality governance is not a list: {branch_quality_governance}",
    )
    branch_quality = next(
        (
            item
            for item in branch_quality_governance
            if str(item.get("branch_config_id")) == branch_config_id
            or str(item.get("branch")) == branch_name
        ),
        None,
    )
    _assert(
        branch_quality is not None,
        f"Version dashboard missed branch quality governance row for {branch_name}: {branch_quality_governance}",
    )
    _assert(
        branch_quality.get("branch") == branch_name,
        f"Version dashboard branch quality row used wrong branch: {branch_quality}",
    )
    _assert(
        branch_quality.get("status") == expected_status,
        f"Version dashboard branch quality status mismatch: {branch_quality}",
    )
    if expected_status == "action_required":
        _assert(
            int(summary.get("branch_quality_action_required") or 0) >= 1,
            f"Version dashboard missed action-required branch quality summary: {summary}",
        )
        _assert(
            "branch_quality_active_severe_findings" in summary,
            f"Version dashboard missed active severe branch quality summary: {summary}",
        )
        _assert(
            int(branch_quality.get("quality_gate_failed_report_count") or 0) >= 1,
            f"Version dashboard branch quality missed failed quality gate report count: {branch_quality}",
        )
        _assert(
            int(branch_quality.get("quality_gate_violation_count") or 0) >= 1,
            f"Version dashboard branch quality missed quality gate violation count: {branch_quality}",
        )
    if expected_status == "pending_scan":
        _assert(
            int(summary.get("branch_quality_pending_scan") or 0) >= 1,
            f"Version dashboard missed pending-scan branch quality summary: {summary}",
        )
        _assert(
            int(branch_quality.get("report_count") or 0) == 0,
            f"Version dashboard pending-scan branch unexpectedly had reports: {branch_quality}",
        )
    if report_id is not None:
        _assert(
            str(branch_quality.get("latest_report_id")) == report_id,
            f"Version dashboard branch quality missed latest report id {report_id}: {branch_quality}",
        )
        _assert(
            int(branch_quality.get("report_count") or 0) >= 1,
            f"Version dashboard branch quality missed report count: {branch_quality}",
        )
    for field_name in [
        "created_bug_count",
        "created_task_count",
        "finding_count",
        "accepted_risk_count",
        "active_severe_finding_count",
        "expired_accepted_risk_count",
        "false_positive_count",
        "pending_suppression_count",
        "severe_finding_count",
        "suppressed_finding_count",
        "uncovered_severe_bug_count",
        "uncovered_severe_task_count",
    ]:
        _assert(
            field_name in branch_quality,
            f"Version dashboard branch quality missed {field_name}: {branch_quality}",
        )
    return branch_quality
