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
VERSION_DASHBOARD_DELIVERY_STAGE_KEYS = [
    "requirements",
    "tasks",
    "branches",
    "inspections",
    "code-reviews",
    "bugs",
    "knowledge-deposits",
    "releases",
    "status-impact",
]
VERSION_DASHBOARD_EVIDENCE_STATUSES = {
    "blocked",
    "covered",
    "inaccessible",
    "missing",
    "not_applicable",
    "risk",
}
VERSION_DASHBOARD_LEVELS = {"error", "info", "success", "warning"}


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


def validate_version_dashboard_delivery_stage_overview(dashboard: dict[str, Any]) -> None:
    stages = dashboard.get("delivery_stage_overview")
    _assert(
        isinstance(stages, list),
        f"Version dashboard delivery_stage_overview is not a list: {stages}",
    )
    stage_keys = [str(stage.get("key") or "") for stage in stages if isinstance(stage, dict)]
    _assert(
        stage_keys == VERSION_DASHBOARD_DELIVERY_STAGE_KEYS,
        f"Version dashboard delivery stage order drifted: {stage_keys}",
    )
    for stage in stages:
        _assert(
            isinstance(stage, dict),
            f"Version dashboard delivery stage is not an object: {stage}",
        )
        for field in ("detail", "key", "level", "title", "value"):
            _assert(
                field in stage and stage.get(field),
                f"Version dashboard delivery stage missed {field}: {stage}",
            )
        _assert(
            stage.get("level") in {"error", "info", "success", "warning"},
            f"Version dashboard delivery stage level unsupported: {stage}",
        )
        if stage.get("key") != "status-impact":
            _assert(
                stage.get("action_label"),
                f"Version dashboard delivery stage missed action_label: {stage}",
            )
            _assert(
                stage.get("action_target_id"),
                f"Version dashboard delivery stage missed action_target_id: {stage}",
            )
            _assert(
                stage.get("action_target_type"),
                f"Version dashboard delivery stage missed action_target_type: {stage}",
            )
    summary = dashboard.get("summary") or {}
    blocker_count = int(summary.get("blockers") or 0)
    release_stage = next((stage for stage in stages if stage.get("key") == "releases"), {})
    if blocker_count:
        _assert(
            any(stage.get("level") in {"error", "warning"} for stage in stages),
            f"Version dashboard delivery stages should expose blocker pressure: {stages}",
        )
    has_release_blocker = any(
        blocker.get("source_type") == "jenkins_release"
        for blocker in dashboard.get("blockers") or []
    )
    _assert(
        "successful_releases" in summary,
        f"Version dashboard missed successful release summary: {summary}",
    )
    _assert(
        "failed_releases" in summary,
        f"Version dashboard missed failed release summary: {summary}",
    )
    release_stage_detail = str(release_stage.get("detail") or "")
    _assert(
        "成功" in release_stage_detail and "失败" in release_stage_detail,
        f"Version dashboard release stage missed release evidence counts: {release_stage}",
    )
    if has_release_blocker:
        _assert(
            release_stage.get("level") == "error",
            (
                "Version dashboard release stage should be error when release "
                f"blockers exist: {release_stage}"
            ),
        )
        _assert(
            "发布阻塞" in release_stage_detail,
            f"Version dashboard release stage missed release blocker detail: {release_stage}",
        )


def validate_version_dashboard_evidence_coverage(
    dashboard: dict[str, Any],
    *,
    require_blockers: bool = False,
) -> dict[str, Any]:
    coverage = dashboard.get("evidence_coverage")
    _assert(
        isinstance(coverage, dict),
        f"Version dashboard evidence_coverage is not an object: {coverage}",
    )
    for field in (
        "blocking_domains",
        "covered_domains",
        "domains",
        "gap_domains",
        "level",
        "score",
        "summary",
        "total_domains",
    ):
        _assert(
            field in coverage,
            f"Version dashboard evidence_coverage missed {field}: {coverage}",
        )
    _assert(
        coverage.get("level") in VERSION_DASHBOARD_LEVELS,
        f"Version dashboard evidence coverage level unsupported: {coverage}",
    )
    _assert(
        coverage.get("summary"),
        f"Version dashboard evidence coverage missed summary: {coverage}",
    )
    domains = coverage.get("domains")
    _assert(
        isinstance(domains, list),
        f"Version dashboard evidence coverage domains is not a list: {coverage}",
    )
    domain_keys = [str(domain.get("key") or "") for domain in domains if isinstance(domain, dict)]
    _assert(
        domain_keys == VERSION_DASHBOARD_DELIVERY_STAGE_KEYS,
        f"Version dashboard evidence coverage domain order drifted: {domain_keys}",
    )
    for domain in domains:
        _assert(
            isinstance(domain, dict),
            f"Version dashboard evidence coverage domain is not an object: {domain}",
        )
        for field in ("detail", "key", "level", "status", "title", "value"):
            _assert(
                field in domain and domain.get(field),
                f"Version dashboard evidence coverage domain missed {field}: {domain}",
            )
        _assert(
            domain.get("level") in VERSION_DASHBOARD_LEVELS,
            f"Version dashboard evidence coverage domain level unsupported: {domain}",
        )
        _assert(
            domain.get("status") in VERSION_DASHBOARD_EVIDENCE_STATUSES,
            f"Version dashboard evidence coverage domain status unsupported: {domain}",
        )
        if domain.get("status") != "not_applicable":
            _assert(
                domain.get("action_label"),
                f"Version dashboard evidence coverage domain missed action_label: {domain}",
            )
            _assert(
                domain.get("action_target_id"),
                f"Version dashboard evidence coverage domain missed action_target_id: {domain}",
            )
            _assert(
                domain.get("action_target_type"),
                f"Version dashboard evidence coverage domain missed action_target_type: {domain}",
            )

    scored_domains = [
        domain for domain in domains if domain.get("status") != "not_applicable"
    ]
    total_domains = len(scored_domains)
    covered_domains = sum(1 for domain in scored_domains if domain.get("status") == "covered")
    gap_domains = sum(
        1
        for domain in scored_domains
        if domain.get("status") in {"inaccessible", "missing", "risk"}
    )
    blocking_domains = sum(1 for domain in scored_domains if domain.get("level") == "error")
    expected_score = int(round((covered_domains / total_domains) * 100)) if total_domains else 100
    _assert(
        int(coverage.get("total_domains") or 0) == total_domains,
        f"Version dashboard evidence coverage total_domains drifted: {coverage}",
    )
    _assert(
        int(coverage.get("covered_domains") or 0) == covered_domains,
        f"Version dashboard evidence coverage covered_domains drifted: {coverage}",
    )
    _assert(
        int(coverage.get("gap_domains") or 0) == gap_domains,
        f"Version dashboard evidence coverage gap_domains drifted: {coverage}",
    )
    _assert(
        int(coverage.get("blocking_domains") or 0) == blocking_domains,
        f"Version dashboard evidence coverage blocking_domains drifted: {coverage}",
    )
    _assert(
        int(coverage.get("score") or 0) == expected_score,
        f"Version dashboard evidence coverage score drifted: {coverage}",
    )
    if blocking_domains:
        _assert(
            coverage.get("level") == "error",
            f"Version dashboard evidence coverage should be error when blocked: {coverage}",
        )
        _assert(
            "阻断" in str(coverage.get("summary") or ""),
            f"Version dashboard evidence coverage missed blocker summary: {coverage}",
        )
    elif gap_domains:
        _assert(
            coverage.get("level") == "warning",
            f"Version dashboard evidence coverage should warn when gaps exist: {coverage}",
        )
    else:
        _assert(
            coverage.get("level") == "success",
            f"Version dashboard evidence coverage should succeed when complete: {coverage}",
        )
    if require_blockers or int((dashboard.get("summary") or {}).get("blockers") or 0) > 0:
        _assert(
            blocking_domains >= 1,
            f"Version dashboard evidence coverage missed blocker domains: {coverage}",
        )
    return coverage


def validate_version_dashboard_status_impact(
    dashboard: dict[str, Any],
    *,
    expected_target_status: str | None = None,
    require_preview: bool = False,
) -> dict[str, Any]:
    status_impact = dashboard.get("status_impact")
    if status_impact is None:
        _assert(
            expected_target_status is None and not require_preview,
            f"Version dashboard missed status_impact: {dashboard}",
        )
        return {}
    _assert(
        isinstance(status_impact, dict),
        f"Version dashboard status_impact is not an object: {status_impact}",
    )
    target_status = status_impact.get("target_status")
    _assert(
        target_status,
        f"Version dashboard status_impact missed target_status: {status_impact}",
    )
    if expected_target_status is not None:
        _assert(
            target_status == expected_target_status,
            (
                "Version dashboard status_impact target status drifted: "
                f"expected={expected_target_status}, status_impact={status_impact}"
            ),
        )
    for field in (
        "updated_requirements",
        "blocked_requirements",
        "unchanged_requirements",
    ):
        _assert(
            isinstance(status_impact.get(field), list),
            f"Version dashboard status_impact missed list {field}: {status_impact}",
        )
    updated_requirements = status_impact["updated_requirements"]
    blocked_requirements = status_impact["blocked_requirements"]
    unchanged_requirements = status_impact["unchanged_requirements"]
    _assert(
        (
            updated_requirements
            or blocked_requirements
            or unchanged_requirements
            or not require_preview
        ),
        f"Version dashboard status_impact preview has no requirement rows: {status_impact}",
    )
    for requirement in updated_requirements:
        _assert(
            requirement.get("id"),
            f"Updated status impact missed id: {requirement}",
        )
        _assert(
            requirement.get("title"),
            f"Updated status impact missed title: {requirement}",
        )
        _assert(
            requirement.get("from_status") or requirement.get("status"),
            f"Updated status impact missed source status: {requirement}",
        )
        _assert(
            requirement.get("to_status") or target_status,
            f"Updated status impact missed target status: {requirement}",
        )
        if requirement.get("to_status"):
            _assert(
                requirement.get("to_status") == target_status,
                (
                    "Updated status impact target status drifted: "
                    f"target={target_status}, requirement={requirement}"
                ),
            )
    for requirement in blocked_requirements:
        _assert(
            requirement.get("id"),
            f"Blocked status impact missed id: {requirement}",
        )
        _assert(
            requirement.get("title"),
            f"Blocked status impact missed title: {requirement}",
        )
        _assert(
            requirement.get("status"),
            f"Blocked status impact missed status: {requirement}",
        )
        _assert(
            requirement.get("block_reason"),
            f"Blocked status impact missed block_reason: {requirement}",
        )
    for requirement in unchanged_requirements:
        _assert(
            requirement.get("id"),
            f"Unchanged status impact missed id: {requirement}",
        )
        _assert(
            requirement.get("title"),
            f"Unchanged status impact missed title: {requirement}",
        )
        _assert(
            requirement.get("status"),
            f"Unchanged status impact missed status: {requirement}",
        )
    return status_impact


def _status_impact_count(
    status_impact: dict[str, Any],
    count_key: str,
    list_key: str,
) -> int:
    if status_impact.get(count_key) is not None:
        return int(status_impact.get(count_key) or 0)
    value = status_impact.get(list_key)
    return len(value) if isinstance(value, list) else 0


def validate_version_dashboard_status_impact_projection(
    dashboard_status_impact: dict[str, Any],
    projection: Any,
    *,
    label: str,
) -> None:
    if not dashboard_status_impact:
        _assert(
            projection in ({}, None),
            f"{label} status_impact projection should be empty: {projection}",
        )
        return
    _assert(
        isinstance(projection, dict) and projection,
        f"{label} missed status_impact projection: {projection}",
    )
    expected = {
        "blocked_count": _status_impact_count(
            dashboard_status_impact,
            "blocked_count",
            "blocked_requirements",
        ),
        "from_status": dashboard_status_impact.get("from_status"),
        "target_status": dashboard_status_impact.get("target_status"),
        "unchanged_count": _status_impact_count(
            dashboard_status_impact,
            "unchanged_count",
            "unchanged_requirements",
        ),
        "updated_count": _status_impact_count(
            dashboard_status_impact,
            "updated_count",
            "updated_requirements",
        ),
    }
    for field, expected_value in expected.items():
        _assert(
            projection.get(field) == expected_value,
            (
                f"{label} status_impact drifted from version dashboard: "
                f"field={field}, expected={expected_value}, projection={projection}, "
                f"dashboard={dashboard_status_impact}"
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
