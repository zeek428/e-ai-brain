from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from app.api.deps import api_error, require_permissions
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.services.code_inspection_common import (
    CODE_INSPECTION_RISK_LEVELS,
    CODE_INSPECTION_SORT_FIELDS,
    DEFAULT_DASHBOARD_TREND_DAYS,
    SEVERE_FINDING_THRESHOLD,
    committer_key,
    ensure_enum,
    normalize_severity,
    report_matches_committer,
    severity_rank,
)
from app.services.code_inspection_detail_projection import (
    finding_accepted_risk_is_expired,
    finding_suppression_is_effective,
)
from app.services.full_chain_subject_resolution import (
    resolve_code_inspection_report_requirement_id,
)
from app.services.product_scope import user_product_access
from app.services.task_workflow_context import task_workflow_read_store


def _read_memory_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _read_memory_record(
    current_store: Any,
    collection_name: str,
    record_id: Any,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    record = _read_memory_collection(current_store, collection_name).get(str(record_id))
    return record if isinstance(record, dict) else None


def require_code_inspection_read(user: dict[str, Any]) -> None:
    require_permissions(user, {"code_inspection.read"})


def code_inspection_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    if callable(getattr(repository, "list_code_inspection_reports", None)):
        return repository
    return None


def _code_inspection_full_chain_metadata(
    report: dict[str, Any],
    current_store: Any,
) -> dict[str, Any]:
    report_id = report.get("id")
    if report_id is None:
        return {
            "full_chain_available": False,
            "full_chain_subject_id": None,
            "full_chain_subject_type": None,
            "full_chain_unavailable_reason": "NO_REQUIREMENT_CONTEXT",
        }
    requirement_id = resolve_code_inspection_report_requirement_id(current_store, report)
    if requirement_id is None:
        return {
            "full_chain_available": False,
            "full_chain_subject_id": None,
            "full_chain_subject_type": None,
            "full_chain_unavailable_reason": "NO_REQUIREMENT_CONTEXT",
        }
    return {
        "full_chain_available": True,
        "full_chain_subject_id": str(report_id),
        "full_chain_subject_type": "code_inspection_report",
        "full_chain_unavailable_reason": None,
    }


def public_code_inspection_report(
    report: dict[str, Any],
    current_store: Any,
    *,
    full_chain_store: Any | None = None,
) -> dict[str, Any]:
    repository_id = report.get("repository_id")
    product_id = report.get("product_id")
    repository = (
        report.get("repository")
        or _read_memory_record(
            current_store,
            "product_git_repositories",
            repository_id,
        )
        or {}
    )
    product = (
        report.get("product")
        or _read_memory_record(
            current_store,
            "products",
            product_id,
        )
        or {}
    )
    chain_store = (
        full_chain_store
        if full_chain_store is not None
        else task_workflow_read_store(current_store)
    )
    return {
        **report,
        **_code_inspection_full_chain_metadata(report, chain_store),
        "product_code": product.get("code"),
        "product_name": product.get("name"),
        "repository_name": repository.get("name"),
        "repository_path": repository.get("project_path") or repository.get("remote_url"),
    }


def scoped_code_inspection_reports(
    *,
    current_store: Any,
    product_id: str | None,
    repository_id: str | None,
    risk_level: str | None,
    status: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    global_access, product_scope_ids = user_product_access(user)
    if not global_access and product_id is not None and str(product_id) not in product_scope_ids:
        return []
    repository = code_inspection_query_repository(current_store)
    if repository is not None:
        items = repository.list_code_inspection_reports(
            product_id=product_id,
            repository_id=repository_id,
            risk_level=risk_level,
            status=status,
        )
    else:
        items = list(_read_memory_collection(current_store, "code_inspection_reports").values())
    if product_id:
        items = [item for item in items if item.get("product_id") == product_id]
    if repository_id:
        items = [item for item in items if item.get("repository_id") == repository_id]
    if risk_level:
        items = [item for item in items if item.get("risk_level") == risk_level]
    if status:
        items = [item for item in items if item.get("status") == status]
    if not global_access:
        items = [
            item
            for item in items
            if item.get("product_id") is not None
            and str(item.get("product_id")) in product_scope_ids
        ]
    full_chain_store = task_workflow_read_store(current_store)
    return [
        public_code_inspection_report(item, current_store, full_chain_store=full_chain_store)
        for item in items
    ]


def findings_for_code_inspection_reports(
    *,
    current_store: Any,
    reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    report_ids = {str(report["id"]) for report in reports if report.get("id") is not None}
    if not report_ids:
        return []
    repository = code_inspection_query_repository(current_store)
    findings: list[dict[str, Any]] = []
    if repository is not None and callable(getattr(repository, "get_code_inspection_detail", None)):
        for report_id in sorted(report_ids):
            detail = repository.get_code_inspection_detail(report_id)
            if detail is not None:
                findings.extend(detail.get("findings") or [])
        return findings
    return [
        finding
        for finding in _read_memory_collection(
            current_store,
            "code_inspection_findings",
        ).values()
        if str(finding.get("report_id")) in report_ids
    ]


def report_date_bucket(report: dict[str, Any]) -> str:
    raw_created_at = str(report.get("created_at") or "")
    try:
        return datetime.fromisoformat(raw_created_at.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return raw_created_at[:10] or "unknown"


def report_quality_gate_status(report: dict[str, Any]) -> str:
    quality_gate = report.get("quality_gate")
    if not isinstance(quality_gate, dict):
        return "unknown"
    status = str(quality_gate.get("status") or "").strip().lower()
    if status in {"passed", "pass", "succeeded", "success"}:
        return "passed"
    if status in {"failed", "fail", "blocked"}:
        return "failed"
    if status in {"skipped", "disabled", "not_configured"}:
        return "skipped"
    return status or "unknown"


def counter_rows(counter: Counter[str], *, key_name: str = "key") -> list[dict[str, Any]]:
    return [
        {key_name: key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def highest_risk_level(current: str | None, candidate: str | None) -> str:
    current_rank = severity_rank(current or "low")
    candidate_rank = severity_rank(candidate or "low")
    return str(candidate or "low") if candidate_rank > current_rank else str(current or "low")


def report_recency_key(report: dict[str, Any]) -> str:
    return str(
        report.get("scan_finished_at")
        or report.get("updated_at")
        or report.get("created_at")
        or ""
    )


def code_inspection_dashboard_response(
    *,
    committer: str | None,
    current_store: Any,
    product_id: str | None,
    repository_id: str | None,
    risk_level: str | None,
    status: str | None,
    title: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_code_inspection_read(user)
    if risk_level is not None:
        ensure_enum(risk_level, CODE_INSPECTION_RISK_LEVELS, "risk_level")
    reports = scoped_code_inspection_reports(
        current_store=current_store,
        product_id=product_id,
        repository_id=repository_id,
        risk_level=risk_level,
        status=status,
        user=user,
    )
    reports = [
        report
        for report in reports
        if list_text_matches(report, title, ("id", "summary", "repository_id"))
        and report_matches_committer(report, committer)
    ]
    findings = findings_for_code_inspection_reports(
        current_store=current_store,
        reports=reports,
    )
    findings_by_report: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        if finding.get("report_id") is not None:
            findings_by_report[str(finding["report_id"])].append(finding)

    severity_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    rule_stats: dict[str, dict[str, Any]] = {}
    repository_stats: dict[str, dict[str, Any]] = {}
    branch_stats: dict[str, dict[str, Any]] = {}
    branch_governance_stats: dict[str, dict[str, Any]] = {}
    committer_stats: dict[str, dict[str, Any]] = {}
    committer_governance_stats: dict[str, dict[str, Any]] = {}
    quality_gate_violation_stats: dict[str, dict[str, Any]] = {}
    rule_version_counts: Counter[str] = Counter()
    scanner_version_counts: Counter[str] = Counter()
    suppression_counts: Counter[str] = Counter()
    trend_stats: dict[str, dict[str, Any]] = {}
    severe_finding_count = 0
    covered_by_bug_count = 0
    covered_by_task_count = 0
    quality_gate_failed_report_count = 0
    oldest_uncovered_at: str | None = None
    oldest_without_task_at: str | None = None

    for report in reports:
        report_id = str(report["id"])
        report_findings = findings_by_report.get(report_id, [])
        risk_level_value = str(report.get("risk_level") or "low")
        risk_counts[risk_level_value] += 1
        rules_version = str(report.get("rules_version") or "unknown")
        scanner_version = str(report.get("scanner_version") or "unknown")
        rule_version_counts[rules_version] += 1
        scanner_version_counts[scanner_version] += 1
        suppression_summary = report.get("suppression_summary")
        if isinstance(suppression_summary, dict):
            for key, value in suppression_summary.items():
                try:
                    suppression_counts[str(key)] += int(value or 0)
                except (TypeError, ValueError):
                    continue
        bucket = report_date_bucket(report)
        trend = trend_stats.setdefault(
            bucket,
            {
                "bug_count": 0,
                "date": bucket,
                "finding_count": 0,
                "quality_gate_failed_count": 0,
                "quality_gate_passed_count": 0,
                "quality_gate_skipped_count": 0,
                "quality_gate_unknown_count": 0,
                "report_count": 0,
                "severe_finding_count": 0,
            },
        )
        trend["report_count"] += 1
        trend["finding_count"] += int(report.get("finding_count") or len(report_findings))
        trend["severe_finding_count"] += int(report.get("severe_finding_count") or 0)
        trend["bug_count"] += len(report.get("created_bug_ids") or [])
        quality_gate_status = report_quality_gate_status(report)
        if quality_gate_status == "passed":
            trend["quality_gate_passed_count"] += 1
        elif quality_gate_status == "failed":
            trend["quality_gate_failed_count"] += 1
            quality_gate_failed_report_count += 1
        elif quality_gate_status == "skipped":
            trend["quality_gate_skipped_count"] += 1
        else:
            trend["quality_gate_unknown_count"] += 1
        report_quality_gate_violation_count = 0
        quality_gate = report.get("quality_gate")
        if isinstance(quality_gate, dict):
            violations = quality_gate.get("violations")
            if isinstance(violations, list):
                for violation in violations:
                    if not isinstance(violation, dict):
                        continue
                    report_quality_gate_violation_count += 1
                    metric = str(
                        violation.get("metric")
                        or violation.get("rule_id")
                        or violation.get("code")
                        or "unknown"
                    ).strip() or "unknown"
                    violation_severity = normalize_severity(
                        violation.get("severity") or violation.get("level"),
                        fallback=risk_level_value,
                    )
                    violation_entry = quality_gate_violation_stats.setdefault(
                        metric,
                        {
                            "_report_ids": set(),
                            "actual": None,
                            "latest_report_id": None,
                            "_latest_report_recency_key": "",
                            "latest_report_summary": None,
                            "limit": None,
                            "metric": metric,
                            "report_count": 0,
                            "severity": violation_severity,
                            "violation_count": 0,
                        },
                    )
                    violation_entry["violation_count"] += 1
                    violation_entry["_report_ids"].add(report_id)
                    violation_entry["report_count"] = len(violation_entry["_report_ids"])
                    violation_entry["severity"] = highest_risk_level(
                        str(violation_entry.get("severity") or "low"),
                        violation_severity,
                    )
                    report_key = report_recency_key(report)
                    if report_key >= str(violation_entry.get("_latest_report_recency_key") or ""):
                        violation_entry["_latest_report_recency_key"] = report_key
                        violation_entry["actual"] = violation.get("actual", violation.get("value"))
                        violation_entry["limit"] = violation.get("limit")
                        violation_entry["latest_report_id"] = report_id
                        violation_entry["latest_report_summary"] = report.get("summary")

        repository_key = str(report.get("repository_id") or report.get("repository_name") or "-")
        repository_entry = repository_stats.setdefault(
            repository_key,
            {
                "branch_count": set(),
                "finding_count": 0,
                "repository_id": report.get("repository_id"),
                "repository_name": report.get("repository_name"),
                "repository_path": report.get("repository_path"),
                "report_count": 0,
                "risk_level": "low",
                "severe_finding_count": 0,
            },
        )
        repository_entry["report_count"] += 1
        repository_entry["finding_count"] += int(
            report.get("finding_count") or len(report_findings)
        )
        repository_entry["severe_finding_count"] += int(report.get("severe_finding_count") or 0)
        repository_entry["risk_level"] = highest_risk_level(
            repository_entry["risk_level"],
            risk_level_value,
        )
        if report.get("branch"):
            repository_entry["branch_count"].add(str(report["branch"]))

        branch_key = f"{repository_key}:{report.get('branch') or '-'}"
        branch_entry = branch_stats.setdefault(
            branch_key,
            {
                "branch": report.get("branch") or "-",
                "finding_count": 0,
                "repository_id": report.get("repository_id"),
                "repository_name": report.get("repository_name"),
                "report_count": 0,
                "severe_finding_count": 0,
            },
        )
        branch_entry["report_count"] += 1
        branch_entry["finding_count"] += int(report.get("finding_count") or len(report_findings))
        branch_entry["severe_finding_count"] += int(report.get("severe_finding_count") or 0)
        branch_governance_entry = branch_governance_stats.setdefault(
            branch_key,
            {
                "_latest_report_recency_key": "",
                "_quality_gate_failed_report_ids": set(),
                "_report_ids": set(),
                "accepted_risk_count": 0,
                "active_severe_finding_count": 0,
                "branch": report.get("branch") or "-",
                "covered_by_bug_count": 0,
                "covered_by_task_count": 0,
                "expired_accepted_risk_count": 0,
                "finding_count": 0,
                "latest_report_id": None,
                "latest_report_summary": None,
                "oldest_uncovered_at": None,
                "pending_suppression_count": 0,
                "quality_gate_failed_report_count": 0,
                "quality_gate_violation_count": 0,
                "repository_id": report.get("repository_id"),
                "repository_name": report.get("repository_name"),
                "severe_finding_count": 0,
                "status": "healthy",
                "uncovered_bug_finding_count": 0,
                "uncovered_task_finding_count": 0,
            },
        )
        branch_governance_entry["_report_ids"].add(report_id)
        report_key = report_recency_key(report)
        if report_key >= str(branch_governance_entry.get("_latest_report_recency_key") or ""):
            branch_governance_entry["_latest_report_recency_key"] = report_key
            branch_governance_entry["latest_report_id"] = report_id
            branch_governance_entry["latest_report_summary"] = report.get("summary")
        if quality_gate_status == "failed":
            branch_governance_entry["_quality_gate_failed_report_ids"].add(report_id)
            branch_governance_entry["quality_gate_failed_report_count"] = len(
                branch_governance_entry["_quality_gate_failed_report_ids"]
            )
        branch_governance_entry["quality_gate_violation_count"] += (
            report_quality_gate_violation_count
        )

        for committer in report.get("committer_summary") or []:
            identity = (
                committer.get("email")
                or committer.get("username")
                or committer.get("name")
                or "unknown"
            )
            committer_entry = committer_stats.setdefault(
                str(identity),
                {
                    "bug_count": 0,
                    "email": committer.get("email"),
                    "finding_count": 0,
                    "name": committer.get("name"),
                    "severe_finding_count": 0,
                    "username": committer.get("username"),
                },
            )
            committer_entry["finding_count"] += int(committer.get("finding_count") or 0)
            committer_entry["severe_finding_count"] += int(
                committer.get("severe_finding_count") or 0
            )
            committer_entry["bug_count"] += int(committer.get("bug_count") or 0)

        for finding in report_findings:
            severity = normalize_severity(finding.get("severity"), fallback="info")
            category = str(finding.get("category") or "uncategorized")
            rule_id = str(finding.get("rule_id") or "unknown")
            severity_counts[severity] += 1
            category_counts[category] += 1
            is_severe = severity_rank(severity) >= severity_rank(SEVERE_FINDING_THRESHOLD)
            committer_identity = committer_key(finding) or "unknown"
            committer_governance_entry = committer_governance_stats.setdefault(
                str(committer_identity),
                {
                    "_latest_report_recency_key": "",
                    "_report_ids": set(),
                    "accepted_risk_count": 0,
                    "active_severe_finding_count": 0,
                    "covered_by_bug_count": 0,
                    "covered_by_task_count": 0,
                    "email": finding.get("committer_email"),
                    "expired_accepted_risk_count": 0,
                    "finding_count": 0,
                    "latest_report_id": None,
                    "latest_report_summary": None,
                    "name": finding.get("committer_name"),
                    "oldest_uncovered_at": None,
                    "pending_suppression_count": 0,
                    "severe_finding_count": 0,
                    "status": "healthy",
                    "uncovered_bug_finding_count": 0,
                    "uncovered_task_finding_count": 0,
                    "username": finding.get("committer_username"),
                },
            )
            committer_governance_entry["_report_ids"].add(report_id)
            committer_governance_entry["finding_count"] += 1
            report_key = report_recency_key(report)
            if report_key >= str(
                committer_governance_entry.get("_latest_report_recency_key") or ""
            ):
                committer_governance_entry["_latest_report_recency_key"] = report_key
                committer_governance_entry["latest_report_id"] = report_id
                committer_governance_entry["latest_report_summary"] = report.get("summary")
            suppression_status = finding.get("suppression_status")
            if suppression_status == "pending":
                committer_governance_entry["pending_suppression_count"] += 1
                branch_governance_entry["pending_suppression_count"] += 1
            if (
                suppression_status == "approved"
                and finding.get("suppression_reason") == "accepted_risk"
            ):
                committer_governance_entry["accepted_risk_count"] += 1
                branch_governance_entry["accepted_risk_count"] += 1
                if finding_accepted_risk_is_expired(finding):
                    committer_governance_entry["expired_accepted_risk_count"] += 1
                    branch_governance_entry["expired_accepted_risk_count"] += 1
            branch_governance_entry["finding_count"] += 1
            if is_severe:
                severe_finding_count += 1
                committer_governance_entry["severe_finding_count"] += 1
                branch_governance_entry["severe_finding_count"] += 1
                if not finding_suppression_is_effective(finding):
                    committer_governance_entry["active_severe_finding_count"] += 1
                    branch_governance_entry["active_severe_finding_count"] += 1
                    if finding.get("created_bug_id"):
                        committer_governance_entry["covered_by_bug_count"] += 1
                        branch_governance_entry["covered_by_bug_count"] += 1
                    else:
                        committer_governance_entry["uncovered_bug_finding_count"] += 1
                        branch_governance_entry["uncovered_bug_finding_count"] += 1
                        if (
                            committer_governance_entry.get("oldest_uncovered_at") is None
                            or str(finding.get("created_at") or "")
                            < str(committer_governance_entry.get("oldest_uncovered_at") or "")
                        ):
                            committer_governance_entry["oldest_uncovered_at"] = str(
                                finding.get("created_at") or ""
                            )
                        if (
                            branch_governance_entry.get("oldest_uncovered_at") is None
                            or str(finding.get("created_at") or "")
                            < str(branch_governance_entry.get("oldest_uncovered_at") or "")
                        ):
                            branch_governance_entry["oldest_uncovered_at"] = str(
                                finding.get("created_at") or ""
                            )
                    if finding.get("created_task_id"):
                        committer_governance_entry["covered_by_task_count"] += 1
                        branch_governance_entry["covered_by_task_count"] += 1
                    else:
                        committer_governance_entry["uncovered_task_finding_count"] += 1
                        branch_governance_entry["uncovered_task_finding_count"] += 1
                if finding.get("created_bug_id"):
                    covered_by_bug_count += 1
                elif (
                    oldest_uncovered_at is None
                    or str(finding.get("created_at") or "") < oldest_uncovered_at
                ):
                    oldest_uncovered_at = str(finding.get("created_at") or "")
                if finding.get("created_task_id"):
                    covered_by_task_count += 1
                elif (
                    oldest_without_task_at is None
                    or str(finding.get("created_at") or "") < oldest_without_task_at
                ):
                    oldest_without_task_at = str(finding.get("created_at") or "")
            rule_entry = rule_stats.setdefault(
                rule_id,
                {
                    "category": category,
                    "finding_count": 0,
                    "rule_id": rule_id,
                    "severity": severity,
                    "severe_finding_count": 0,
                },
            )
            rule_entry["finding_count"] += 1
            rule_entry["severity"] = (
                severity
                if severity_rank(severity) > severity_rank(rule_entry.get("severity"))
                else rule_entry.get("severity")
            )
            if is_severe:
                rule_entry["severe_finding_count"] += 1

    repository_ranking = sorted(
        (
            {**entry, "branch_count": len(entry["branch_count"])}
            for entry in repository_stats.values()
        ),
        key=lambda item: (
            -int(item["severe_finding_count"]),
            -int(item["finding_count"]),
            str(item.get("repository_name") or ""),
        ),
    )[:5]
    branch_ranking = sorted(
        branch_stats.values(),
        key=lambda item: (
            -int(item["severe_finding_count"]),
            -int(item["finding_count"]),
            str(item.get("branch") or ""),
        ),
    )[:5]
    committer_ranking = sorted(
        committer_stats.values(),
        key=lambda item: (
            -int(item["severe_finding_count"]),
            -int(item["finding_count"]),
            str(item.get("email") or item.get("username") or item.get("name") or ""),
        ),
    )[:5]
    for entry in committer_governance_stats.values():
        if (
            entry["uncovered_bug_finding_count"]
            or entry["expired_accepted_risk_count"]
        ):
            entry["status"] = "action_required"
        elif entry["pending_suppression_count"]:
            entry["status"] = "pending_review"
    for entry in branch_governance_stats.values():
        if (
            entry["uncovered_bug_finding_count"]
            or entry["expired_accepted_risk_count"]
            or entry["quality_gate_failed_report_count"]
        ):
            entry["status"] = "action_required"
        elif entry["pending_suppression_count"]:
            entry["status"] = "pending_review"
    branch_governance = sorted(
        (
            {
                key: value
                for key, value in {
                    **entry,
                    "report_count": len(entry["_report_ids"]),
                }.items()
                if key
                not in {
                    "_latest_report_recency_key",
                    "_quality_gate_failed_report_ids",
                    "_report_ids",
                }
            }
            for entry in branch_governance_stats.values()
        ),
        key=lambda item: (
            -int(item.get("uncovered_bug_finding_count") or 0),
            -int(item.get("uncovered_task_finding_count") or 0),
            -int(item.get("quality_gate_failed_report_count") or 0),
            -int(item.get("pending_suppression_count") or 0),
            -int(item.get("expired_accepted_risk_count") or 0),
            -int(item.get("active_severe_finding_count") or 0),
            str(item.get("repository_name") or item.get("repository_id") or ""),
            str(item.get("branch") or ""),
        ),
    )[:10]
    committer_governance = sorted(
        (
            {
                key: value
                for key, value in {
                    **entry,
                    "report_count": len(entry["_report_ids"]),
                }.items()
                if key not in {"_latest_report_recency_key", "_report_ids"}
            }
            for entry in committer_governance_stats.values()
        ),
        key=lambda item: (
            -int(item.get("uncovered_bug_finding_count") or 0),
            -int(item.get("uncovered_task_finding_count") or 0),
            -int(item.get("pending_suppression_count") or 0),
            -int(item.get("expired_accepted_risk_count") or 0),
            -int(item.get("active_severe_finding_count") or 0),
            str(item.get("email") or item.get("username") or item.get("name") or ""),
        ),
    )[:10]
    governance_pressure = {
        "accepted_risk_count": sum(
            int(entry.get("accepted_risk_count") or 0)
            for entry in committer_governance_stats.values()
        ),
        "action_required_committer_count": sum(
            1
            for entry in committer_governance_stats.values()
            if entry.get("status") == "action_required"
        ),
        "action_required_branch_count": sum(
            1
            for entry in branch_governance_stats.values()
            if entry.get("status") == "action_required"
        ),
        "active_severe_finding_count": sum(
            int(entry.get("active_severe_finding_count") or 0)
            for entry in committer_governance_stats.values()
        ),
        "expired_accepted_risk_count": sum(
            int(entry.get("expired_accepted_risk_count") or 0)
            for entry in committer_governance_stats.values()
        ),
        "failed_report_count": sum(1 for report in reports if report.get("status") == "failed"),
        "pending_review_committer_count": sum(
            1
            for entry in committer_governance_stats.values()
            if entry.get("status") == "pending_review"
        ),
        "pending_review_branch_count": sum(
            1
            for entry in branch_governance_stats.values()
            if entry.get("status") == "pending_review"
        ),
        "pending_suppression_count": sum(
            int(entry.get("pending_suppression_count") or 0)
            for entry in committer_governance_stats.values()
        ),
        "quality_gate_failed_report_count": quality_gate_failed_report_count,
        "quality_gate_violation_count": sum(
            int(entry.get("violation_count") or 0)
            for entry in quality_gate_violation_stats.values()
        ),
        "uncovered_bug_finding_count": sum(
            int(entry.get("uncovered_bug_finding_count") or 0)
            for entry in committer_governance_stats.values()
        ),
        "uncovered_task_finding_count": sum(
            int(entry.get("uncovered_task_finding_count") or 0)
            for entry in committer_governance_stats.values()
        ),
    }
    if (
        governance_pressure["failed_report_count"]
        or governance_pressure["quality_gate_failed_report_count"]
        or governance_pressure["uncovered_bug_finding_count"]
        or governance_pressure["expired_accepted_risk_count"]
    ):
        governance_pressure["status"] = "action_required"
    elif governance_pressure["pending_suppression_count"]:
        governance_pressure["status"] = "pending_review"
    else:
        governance_pressure["status"] = "healthy"
    rule_distribution = sorted(
        rule_stats.values(),
        key=lambda item: (
            -int(item["severe_finding_count"]),
            -int(item["finding_count"]),
            str(item["rule_id"]),
        ),
    )[:10]
    quality_gate_violations = sorted(
        (
            {
                key: value
                for key, value in entry.items()
                if key not in {"_latest_report_recency_key", "_report_ids"}
            }
            for entry in quality_gate_violation_stats.values()
        ),
        key=lambda item: (
            -severity_rank(str(item.get("severity") or "low")),
            -int(item.get("violation_count") or 0),
            str(item.get("metric") or ""),
        ),
    )[:10]
    trend = sorted(trend_stats.values(), key=lambda item: str(item["date"]))[
        -DEFAULT_DASHBOARD_TREND_DAYS:
    ]
    rule_version_distribution = counter_rows(
        rule_version_counts,
        key_name="rules_version",
    )
    scanner_version_distribution = counter_rows(
        scanner_version_counts,
        key_name="scanner_version",
    )
    latest_report = max(
        reports,
        key=lambda item: str(item.get("scan_finished_at") or item.get("created_at") or ""),
        default=None,
    )
    bug_coverage_rate = (
        round(covered_by_bug_count / severe_finding_count, 4)
        if severe_finding_count
        else 1
    )
    task_coverage_rate = (
        round(covered_by_task_count / severe_finding_count, 4)
        if severe_finding_count
        else 1
    )
    sla_status = "healthy" if bug_coverage_rate >= 0.8 else "at_risk"
    return {
        "branch_governance": branch_governance,
        "branch_ranking": branch_ranking,
        "category_distribution": counter_rows(category_counts, key_name="category"),
        "committer_governance": committer_governance,
        "committer_ranking": committer_ranking,
        "governance_pressure": governance_pressure,
        "query": {
            "product_id": product_id,
            "repository_id": repository_id,
            "risk_level": risk_level,
            "status": status,
        },
        "quality_gate_violations": quality_gate_violations,
        "repository_ranking": repository_ranking,
        "risk_distribution": counter_rows(risk_counts, key_name="risk_level"),
        "rule_distribution": rule_distribution,
        "rule_governance": {
            "expired_accepted_risk_count": sum(
                1
                for finding in findings
                if finding_accepted_risk_is_expired(finding)
            ),
            "latest_report_rules_version": (
                latest_report.get("rules_version") if latest_report else None
            ),
            "latest_report_scanner_version": (
                latest_report.get("scanner_version") if latest_report else None
            ),
            "mixed_rules_version": len(rule_version_counts) > 1,
            "mixed_scanner_version": len(scanner_version_counts) > 1,
            "report_with_suppression_count": sum(
                1 for report in reports if int(report.get("suppressed_finding_count") or 0) > 0
            ),
            "rule_version_distribution": rule_version_distribution[:10],
            "scanner_version_distribution": scanner_version_distribution[:10],
            "suppressed_finding_count": sum(
                int(report.get("suppressed_finding_count") or 0) for report in reports
            ),
            "suppression_distribution": counter_rows(
                suppression_counts,
                key_name="reason",
            ),
        },
        "severity_distribution": counter_rows(severity_counts, key_name="severity"),
        "sla": {
            "bug_coverage_rate": bug_coverage_rate,
            "covered_by_bug_count": covered_by_bug_count,
            "covered_by_task_count": covered_by_task_count,
            "oldest_uncovered_at": oldest_uncovered_at,
            "oldest_without_task_at": oldest_without_task_at,
            "severe_finding_count": severe_finding_count,
            "severe_threshold": SEVERE_FINDING_THRESHOLD,
            "status": sla_status,
            "task_coverage_rate": task_coverage_rate,
            "uncovered_severe_finding_count": severe_finding_count - covered_by_bug_count,
            "uncovered_task_finding_count": severe_finding_count - covered_by_task_count,
        },
        "summary": {
            "bug_created_count": sum(
                len(report.get("created_bug_ids") or []) for report in reports
            ),
            "critical_finding_count": severity_counts["critical"],
            "failed_report_count": sum(1 for report in reports if report.get("status") == "failed"),
            "finding_count": sum(int(report.get("finding_count") or 0) for report in reports),
            "high_finding_count": severity_counts["high"],
            "repository_count": len(
                {
                    report.get("repository_id")
                    for report in reports
                    if report.get("repository_id")
                }
            ),
            "report_count": len(reports),
            "severe_finding_count": sum(
                int(report.get("severe_finding_count") or 0) for report in reports
            ),
        },
        "trend": trend,
    }


def list_code_inspection_reports_response(
    *,
    committer: str | None,
    current_store: Any,
    page: int | None,
    page_size: int | None,
    product_id: str | None,
    repository_id: str | None,
    risk_level: str | None,
    sort_by: str | None,
    sort_order: str,
    started_at: float | None,
    status: str | None,
    title: str | None,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_code_inspection_read(user)
    if risk_level is not None:
        ensure_enum(risk_level, CODE_INSPECTION_RISK_LEVELS, "risk_level")
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "created_at"
    if resolved_sort_by not in CODE_INSPECTION_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    filters = {
        "product_id": product_id,
        "repository_id": repository_id,
        "risk_level": risk_level,
        "status": status,
        "title": title,
        "committer": committer,
    }
    global_access, product_scope_ids = user_product_access(user)
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    if not global_access and product_id is not None and str(product_id) not in product_scope_ids:
        items = []
        payload = paginated_list_payload(
            items,
            filters=filters,
            list_name="code_inspections",
            observed=True,
            page=page,
            page_size=page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
            trace_id=trace_id,
        )["data"]
        return add_list_observability(
            payload,
            filters=filters,
            list_name="code_inspections",
            page=payload.get("page"),
            page_size=payload.get("page_size"),
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    repository = code_inspection_query_repository(current_store)
    if (
        repository is not None
        and callable(getattr(repository, "count_code_inspection_reports", None))
        and callable(getattr(repository, "list_code_inspection_reports_page", None))
    ):
        product_scope_filter = None if global_access else sorted(product_scope_ids)
        query_filters = {
            "committer": committer,
            "product_id": product_id,
            "product_scope_ids": product_scope_filter,
            "repository_id": repository_id,
            "risk_level": risk_level,
            "status": status,
            "title": title,
        }
        total = repository.count_code_inspection_reports(**query_filters)
        full_chain_store = task_workflow_read_store(current_store)
        items = [
            public_code_inspection_report(item, current_store, full_chain_store=full_chain_store)
            for item in repository.list_code_inspection_reports_page(
                **query_filters,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
            )
        ]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="code_inspections",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    items = [
        item
        for item in scoped_code_inspection_reports(
            current_store=current_store,
            product_id=product_id,
            repository_id=repository_id,
            risk_level=risk_level,
            status=status,
            user=user,
        )
        if list_text_matches(item, title, ("id", "summary", "repository_id"))
        and report_matches_committer(item, committer)
    ]
    items = sort_list_items(
        items,
        allowed_fields=CODE_INSPECTION_SORT_FIELDS,
        default_sort_by="created_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    payload = paginated_list_payload(
        items,
        filters=filters,
        list_name="code_inspections",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )["data"]
    return add_list_observability(
        payload,
        filters=filters,
        list_name="code_inspections",
        page=payload.get("page"),
        page_size=payload.get("page_size"),
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
    )
