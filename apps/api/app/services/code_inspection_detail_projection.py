from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.code_inspection_common import (
    SEVERE_FINDING_THRESHOLD,
    normalize_severity,
    severity_rank,
)


def normalize_optional_datetime(value: Any, field_name: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise api_error(
            422,
            "INVALID_DATETIME",
            f"{field_name} must be an ISO datetime",
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def parse_optional_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def finding_accepted_risk_is_expired(
    finding: dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    if finding.get("suppression_status") != "approved":
        return False
    if finding.get("suppression_reason") != "accepted_risk":
        return False
    expires_at = parse_optional_datetime(finding.get("suppression_expires_at"))
    if expires_at is None:
        return False
    return expires_at <= (now or datetime.now(UTC))


def finding_suppression_is_effective(finding: dict[str, Any]) -> bool:
    return finding.get("suppression_status") == "approved" and not finding_accepted_risk_is_expired(
        finding
    )


def _distribution_rows(
    items: dict[str, dict[str, Any]],
    *,
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    return sorted(
        items.values(),
        key=lambda item: (
            -int(item.get("severe_finding_count") or 0),
            -int(item.get("finding_count") or 0),
            *(str(item.get(field) or "") for field in key_fields),
        ),
    )


def code_inspection_scan_summary(
    report: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    rule_distribution: dict[str, dict[str, Any]] = {}
    file_distribution: dict[str, dict[str, Any]] = {}
    committer_distribution: dict[str, dict[str, Any]] = {}
    for finding in findings:
        severity = normalize_severity(finding.get("severity"), fallback="info")
        is_severe = severity_rank(severity) >= severity_rank(SEVERE_FINDING_THRESHOLD)
        rule_id = str(finding.get("rule_id") or "unknown")
        rule_entry = rule_distribution.setdefault(
            rule_id,
            {
                "category": finding.get("category") or "uncategorized",
                "finding_count": 0,
                "rule_id": rule_id,
                "severity": severity,
                "severe_finding_count": 0,
            },
        )
        rule_entry["finding_count"] += 1
        if severity_rank(severity) > severity_rank(rule_entry.get("severity")):
            rule_entry["severity"] = severity
        if is_severe:
            rule_entry["severe_finding_count"] += 1

        file_path = str(finding.get("file_path") or "-")
        file_entry = file_distribution.setdefault(
            file_path,
            {
                "file_path": file_path,
                "finding_count": 0,
                "severe_finding_count": 0,
            },
        )
        file_entry["finding_count"] += 1
        if is_severe:
            file_entry["severe_finding_count"] += 1

        identity = (
            finding.get("committer_email")
            or finding.get("committer_username")
            or finding.get("committer_name")
            or "unknown"
        )
        committer_entry = committer_distribution.setdefault(
            str(identity),
            {
                "email": finding.get("committer_email"),
                "finding_count": 0,
                "name": finding.get("committer_name"),
                "severe_finding_count": 0,
                "username": finding.get("committer_username"),
            },
        )
        committer_entry["finding_count"] += 1
        if is_severe:
            committer_entry["severe_finding_count"] += 1
    return {
        "coverage": {
            "files_scanned": report.get("files_scanned") or 0,
            "incremental_file_count": report.get("incremental_file_count"),
            "incremental_from_commit": report.get("incremental_from_commit"),
            "is_full_scan": bool(report.get("is_full_scan")),
            "lines_scanned": report.get("lines_scanned") or 0,
            "suppressed_finding_count": report.get("suppressed_finding_count") or 0,
        },
        "file_distribution": _distribution_rows(
            file_distribution,
            key_fields=("file_path",),
        ),
        "quality_gate": report.get("quality_gate") or {},
        "rule_distribution": _distribution_rows(
            rule_distribution,
            key_fields=("rule_id",),
        ),
        "committer_distribution": _distribution_rows(
            committer_distribution,
            key_fields=("email", "username", "name"),
        ),
        "previous_comparison": report.get("previous_comparison") or {},
        "scan_profile": report.get("scan_profile") or {},
        "suppression_summary": report.get("suppression_summary") or {},
    }


def code_inspection_governance_summary(
    report: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    severe_findings = [
        finding
        for finding in findings
        if severity_rank(finding.get("severity")) >= severity_rank(SEVERE_FINDING_THRESHOLD)
    ]
    active_severe_findings = [
        finding
        for finding in severe_findings
        if not finding_suppression_is_effective(finding)
    ]
    pending_suppression_findings = [
        finding
        for finding in findings
        if finding.get("suppression_status") == "pending"
    ]
    approved_suppression_findings = [
        finding
        for finding in findings
        if finding.get("suppression_status") == "approved"
    ]
    accepted_risk_findings = [
        finding
        for finding in approved_suppression_findings
        if finding.get("suppression_reason") == "accepted_risk"
    ]
    expired_accepted_risk_findings = [
        finding for finding in accepted_risk_findings if finding_accepted_risk_is_expired(finding)
    ]
    bug_covered = [finding for finding in active_severe_findings if finding.get("created_bug_id")]
    task_covered = [finding for finding in active_severe_findings if finding.get("created_task_id")]
    uncovered_bug_findings = [
        finding for finding in active_severe_findings if not finding.get("created_bug_id")
    ]
    uncovered_task_findings = [
        finding for finding in active_severe_findings if not finding.get("created_task_id")
    ]
    active_count = len(active_severe_findings)
    bug_coverage_rate = round(len(bug_covered) / active_count, 4) if active_count else 1
    task_coverage_rate = round(len(task_covered) / active_count, 4) if active_count else 1
    action_items = []
    if uncovered_bug_findings:
        action_items.append(
            {
                "code": "create_bug_for_uncovered_severe_findings",
                "count": len(uncovered_bug_findings),
                "label": "为未关联 Bug 的严重问题创建缺陷",
            }
        )
    if uncovered_task_findings:
        action_items.append(
            {
                "code": "promote_bug_or_requirement_after_confirmation",
                "count": len(uncovered_task_findings),
                "label": "Bug 或需求确认后推进研发任务",
            }
        )
    if pending_suppression_findings:
        action_items.append(
            {
                "code": "review_pending_suppression",
                "count": len(pending_suppression_findings),
                "label": "审批待处理的忽略申请",
            }
        )
    if expired_accepted_risk_findings:
        action_items.append(
            {
                "code": "review_expired_accepted_risk",
                "count": len(expired_accepted_risk_findings),
                "label": "复核已过期的接受风险",
            }
        )
    status = "healthy"
    if uncovered_bug_findings or expired_accepted_risk_findings:
        status = "action_required"
    elif pending_suppression_findings:
        status = "pending_review"
    return {
        "accepted_risk_count": len(accepted_risk_findings),
        "action_items": action_items,
        "active_severe_finding_count": active_count,
        "bug_coverage_rate": bug_coverage_rate,
        "covered_by_bug_count": len(bug_covered),
        "covered_by_task_count": len(task_covered),
        "expired_accepted_risk_count": len(expired_accepted_risk_findings),
        "pending_suppression_count": len(pending_suppression_findings),
        "severe_threshold": SEVERE_FINDING_THRESHOLD,
        "status": status,
        "suppressed_finding_count": len(approved_suppression_findings),
        "task_coverage_rate": task_coverage_rate,
        "uncovered_bug_finding_count": len(uncovered_bug_findings),
        "uncovered_task_finding_count": len(uncovered_task_findings),
    }
