from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.api.deps import api_error, require_roles
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.services.bugs import create_bug_result
from app.services.operational_records import record_audit_event

CODE_INSPECTION_ACTION_TYPES = {
    "create_bug_for_severe_findings",
    "send_notification",
    "write_code_inspection_report",
}
CODE_INSPECTION_SEVERITIES = {"info", "low", "medium", "high", "critical"}
CODE_INSPECTION_RISK_LEVELS = {"low", "medium", "high", "critical"}
CODE_INSPECTION_NOTIFICATION_CHANNELS = {"dingtalk", "email", "webhook"}
CODE_INSPECTION_SORT_FIELDS = {
    "created_at",
    "finding_count",
    "id",
    "risk_level",
    "severe_finding_count",
    "status",
    "updated_at",
}
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
SEVERE_FINDING_THRESHOLD = "high"


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is None or value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def require_code_inspection_read(user: dict[str, Any]) -> None:
    require_roles(user, {"product_owner", "rd_owner"})


def severity_rank(value: str | None) -> int:
    return SEVERITY_ORDER.get(str(value or "").lower(), SEVERITY_ORDER["medium"])


def normalize_severity(value: Any, *, fallback: str = "medium") -> str:
    normalized = str(value or fallback).lower()
    return normalized if normalized in CODE_INSPECTION_SEVERITIES else fallback


def normalize_risk_level(value: Any, findings: list[dict[str, Any]]) -> str:
    normalized = str(value or "").lower()
    if normalized in CODE_INSPECTION_RISK_LEVELS:
        return normalized
    if not findings:
        return "low"
    highest = max(findings, key=lambda item: severity_rank(item.get("severity")))
    highest_severity = str(highest.get("severity") or "medium")
    return highest_severity if highest_severity in CODE_INSPECTION_RISK_LEVELS else "medium"


def validate_code_inspection_result_actions(actions: Any) -> list[dict[str, Any]]:
    if actions is None:
        return []
    if not isinstance(actions, list):
        raise api_error(400, "VALIDATION_ERROR", "result_actions must be a list")
    normalized: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            raise api_error(400, "VALIDATION_ERROR", "result action must be an object")
        action_type = str(action.get("type") or "")
        ensure_enum(action_type, CODE_INSPECTION_ACTION_TYPES, "result action type")
        if action_type == "create_bug_for_severe_findings":
            threshold = normalize_severity(action.get("severity_threshold"), fallback="critical")
            normalized.append({**action, "severity_threshold": threshold, "type": action_type})
        elif action_type == "send_notification":
            channels = action.get("channels") if isinstance(action.get("channels"), list) else []
            channels = [str(channel) for channel in channels if str(channel or "").strip()]
            if not channels:
                raise api_error(400, "VALIDATION_ERROR", "send_notification requires channels")
            for channel in channels:
                ensure_enum(channel, CODE_INSPECTION_NOTIFICATION_CHANNELS, "notification channel")
            recipients = (
                action.get("recipients")
                if isinstance(action.get("recipients"), list)
                else []
            )
            normalized.append(
                {
                    **action,
                    "channels": channels,
                    "recipients": [
                        str(recipient)
                        for recipient in recipients
                        if str(recipient or "").strip()
                    ],
                    "type": action_type,
                }
            )
        else:
            normalized.append({**action, "type": action_type})
    return normalized


def default_code_inspection_result_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if actions:
        return actions
    return [{"type": "write_code_inspection_report"}]


def code_inspection_source_json(plugin_summary: dict[str, Any]) -> dict[str, Any]:
    response_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
    return response_json if isinstance(response_json, dict) else {}


def normalized_findings(
    current_store: Any,
    *,
    raw_findings: Any,
    report_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(raw_findings, list):
        return []
    now = datetime.now(UTC).isoformat()
    findings: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_findings, start=1):
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or raw.get("rule_id") or f"Finding {index}").strip()
        finding_id = current_store.new_id("code_inspection_finding")
        finding = {
            "category": str(raw.get("category") or "quality"),
            "created_at": now,
            "created_bug_id": None,
            "description": str(raw.get("description") or ""),
            "file_path": str(raw.get("file_path") or ""),
            "id": finding_id,
            "line_number": (
                raw.get("line_number")
                if isinstance(raw.get("line_number"), int)
                else None
            ),
            "raw": raw,
            "recommendation": str(raw.get("recommendation") or ""),
            "report_id": report_id,
            "rule_id": str(raw.get("rule_id") or ""),
            "severity": normalize_severity(raw.get("severity")),
            "title": title,
            "updated_at": now,
        }
        findings.append(finding)
    return findings


def repository_snapshot(current_store: Any, repository_id: str | None) -> dict[str, Any]:
    if not repository_id:
        return {}
    repository = current_store.product_git_repositories.get(repository_id)
    return dict(repository) if repository is not None else {}


def sync_product_git_repository_store(current_store: Any, product_id: str | None) -> None:
    if not product_id:
        return
    repository = getattr(current_store, "repository", None)
    list_repositories = getattr(repository, "list_product_git_repositories", None)
    if not callable(list_repositories):
        return
    for git_repository in list_repositories(product_id, active_only=False):
        if git_repository.get("id") is not None:
            current_store.product_git_repositories[str(git_repository["id"])] = dict(
                git_repository
            )


def create_code_inspection_report_records(
    current_store: Any,
    *,
    collector_run_id: str | None,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    result_actions: list[dict[str, Any]],
    run_id: str,
    user: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sync_product_git_repository_store(current_store, job.get("product_id"))
    source_json = code_inspection_source_json(plugin_summary)
    repository_id = str(
        source_json.get("repository_id")
        or (job.get("config_json") or {}).get("repository_id")
        or ""
    ).strip() or None
    if repository_id is not None:
        repository = current_store.product_git_repositories.get(repository_id)
        if repository is None:
            raise api_error(404, "NOT_FOUND", "Product Git repository not found")
        if job.get("product_id") and repository.get("product_id") != job.get("product_id"):
            raise api_error(400, "VALIDATION_ERROR", "Repository does not belong to product")
    report_id = current_store.new_id("code_inspection_report")
    findings = normalized_findings(
        current_store,
        raw_findings=source_json.get("findings"),
        report_id=report_id,
    )
    now = datetime.now(UTC).isoformat()
    report = {
        "branch": source_json.get("branch") or (job.get("config_json") or {}).get("branch"),
        "collector_run_id": collector_run_id,
        "commit_sha": source_json.get("commit_sha"),
        "created_at": now,
        "created_bug_ids": [],
        "created_by": user["id"],
        "finding_count": len(findings),
        "id": report_id,
        "notification_ids": [],
        "plugin_invocation_log_id": plugin_summary.get("invocation_log_id"),
        "product_id": job.get("product_id"),
        "repository": repository_snapshot(current_store, repository_id),
        "repository_id": repository_id,
        "result_actions": result_actions,
        "risk_level": normalize_risk_level(source_json.get("risk_level"), findings),
        "scheduled_job_id": job["id"],
        "scheduled_job_run_id": run_id,
        "severe_finding_count": sum(
            1
            for finding in findings
            if severity_rank(finding.get("severity")) >= severity_rank(SEVERE_FINDING_THRESHOLD)
        ),
        "source_system": job.get("source_system"),
        "status": "completed",
        "summary": str(source_json.get("summary") or ""),
        "updated_at": now,
    }
    current_store.code_inspection_reports[report_id] = report
    for finding in findings:
        current_store.code_inspection_findings[finding["id"]] = finding
    audit_event = record_audit_event(
        current_store,
        event_type="code_inspection_report.created",
        actor_id=user["id"],
        subject_type="code_inspection_report",
        subject_id=report_id,
        payload={
            "finding_count": report["finding_count"],
            "risk_level": report["risk_level"],
            "scheduled_job_id": job["id"],
        },
    )
    persist_code_inspection_records(
        current_store,
        report=report,
        findings=findings,
        notifications=[],
        audit_event=audit_event,
    )
    return report, findings


def bug_severity_from_finding(severity: str) -> str:
    if severity == "critical":
        return "critical"
    if severity == "high":
        return "major"
    if severity == "medium":
        return "minor"
    return "minor"


def finding_bug_description(finding: dict[str, Any], report: dict[str, Any]) -> str:
    parts = [
        finding.get("description") or finding["title"],
        f"Repository: {report.get('repository_id') or '-'}",
        f"File: {finding.get('file_path') or '-'}",
    ]
    if finding.get("line_number") is not None:
        parts.append(f"Line: {finding['line_number']}")
    if finding.get("recommendation"):
        parts.append(f"Recommendation: {finding['recommendation']}")
    return "\n".join(str(part) for part in parts if str(part).strip())


def create_bugs_for_findings(
    current_store: Any,
    *,
    findings: list[dict[str, Any]],
    report: dict[str, Any],
    severity_threshold: str,
    user: dict[str, Any],
) -> list[str]:
    created_ids: list[str] = []
    threshold_rank = severity_rank(severity_threshold)
    for finding in findings:
        if severity_rank(finding.get("severity")) < threshold_rank:
            continue
        payload = SimpleNamespace(
            assignee=None,
            description=finding_bug_description(finding, report),
            duplicate_of_bug_id=None,
            evidence={
                "branch": report.get("branch"),
                "code_inspection_finding_id": finding["id"],
                "code_inspection_report_id": report["id"],
                "commit_sha": report.get("commit_sha"),
                "file_path": finding.get("file_path"),
                "line_number": finding.get("line_number"),
                "rule_id": finding.get("rule_id"),
            },
            module_code=None,
            product_id=report["product_id"],
            related_task_id=None,
            requirement_id=None,
            reproduce_steps=[
                "Open the referenced repository and branch.",
                "Review the file and line reported by the code inspection finding.",
            ],
            severity=bug_severity_from_finding(str(finding.get("severity") or "medium")),
            source="code_inspection",
            title=f"[Code Inspection] {finding['title']}",
            version_id=None,
        )
        created = create_bug_result(
            current_store=current_store,
            payload=payload,
            user=user,
        )
        created_ids.append(created["id"])
        finding["created_bug_id"] = created["id"]
        current_store.code_inspection_findings[finding["id"]] = finding
    report["created_bug_ids"] = [*report.get("created_bug_ids", []), *created_ids]
    report["updated_at"] = datetime.now(UTC).isoformat()
    current_store.code_inspection_reports[report["id"]] = report
    persist_code_inspection_records(
        current_store,
        report=report,
        findings=findings,
        notifications=[],
    )
    return created_ids


def create_code_inspection_notifications(
    current_store: Any,
    *,
    action: dict[str, Any],
    report: dict[str, Any],
    user: dict[str, Any],
) -> list[str]:
    now = datetime.now(UTC).isoformat()
    created_ids: list[str] = []
    notifications: list[dict[str, Any]] = []
    recipients = action.get("recipients") if isinstance(action.get("recipients"), list) else []
    for channel in action.get("channels") or []:
        notification_id = current_store.new_id("code_inspection_notification")
        target = (
            str(action.get("webhook_url"))
            if channel == "dingtalk" and action.get("webhook_url")
            else ",".join(str(recipient) for recipient in recipients)
        )
        notification = {
            "channel": str(channel),
            "created_at": now,
            "created_by": user["id"],
            "id": notification_id,
            "message": (
                f"Code inspection {report['id']} completed with "
                f"{report['finding_count']} findings and risk {report['risk_level']}."
            ),
            "report_id": report["id"],
            "request_config": {
                "recipients": recipients,
                "webhook_url": action.get("webhook_url"),
            },
            "response_summary": {"status": "recorded"},
            "status": "recorded",
            "target": target,
            "updated_at": now,
        }
        current_store.code_inspection_notifications[notification_id] = notification
        notifications.append(notification)
        created_ids.append(notification_id)
    report["notification_ids"] = [*report.get("notification_ids", []), *created_ids]
    report["updated_at"] = datetime.now(UTC).isoformat()
    current_store.code_inspection_reports[report["id"]] = report
    persist_code_inspection_records(
        current_store,
        report=report,
        findings=[],
        notifications=notifications,
    )
    return created_ids


def execute_code_inspection_result_actions(
    current_store: Any,
    *,
    collector_run_id: str | None,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    result_actions: list[dict[str, Any]],
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    actions = default_code_inspection_result_actions(result_actions)
    report: dict[str, Any] | None = None
    findings: list[dict[str, Any]] = []
    bug_ids: list[str] = []
    notification_ids: list[str] = []
    report_written = False
    for action in actions:
        action_type = action["type"]
        if action_type == "write_code_inspection_report":
            report, findings = create_code_inspection_report_records(
                current_store,
                collector_run_id=collector_run_id,
                job=job,
                plugin_summary=plugin_summary,
                result_actions=actions,
                run_id=run_id,
                user=user,
            )
            report_written = True
        elif action_type == "create_bug_for_severe_findings":
            if report is None:
                report, findings = create_code_inspection_report_records(
                    current_store,
                    collector_run_id=collector_run_id,
                    job=job,
                    plugin_summary=plugin_summary,
                    result_actions=actions,
                    run_id=run_id,
                    user=user,
                )
                report_written = True
            bug_ids.extend(
                create_bugs_for_findings(
                    current_store,
                    findings=findings,
                    report=report,
                    severity_threshold=action.get("severity_threshold") or "critical",
                    user=user,
                )
            )
        elif action_type == "send_notification":
            if report is None:
                report, findings = create_code_inspection_report_records(
                    current_store,
                    collector_run_id=collector_run_id,
                    job=job,
                    plugin_summary=plugin_summary,
                    result_actions=actions,
                    run_id=run_id,
                    user=user,
                )
                report_written = True
            notification_ids.extend(
                create_code_inspection_notifications(
                    current_store,
                    action=action,
                    report=report,
                    user=user,
                )
            )
    if report is None:
        report, findings = create_code_inspection_report_records(
            current_store,
            collector_run_id=collector_run_id,
            job=job,
            plugin_summary=plugin_summary,
            result_actions=actions,
            run_id=run_id,
            user=user,
        )
        report_written = True
    return {
        "bug_ids": bug_ids,
        "finding_count": len(findings),
        "findings": findings,
        "notification_ids": notification_ids,
        "report": report,
        "report_written": report_written,
        "result_actions": actions,
    }


def code_inspection_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    if callable(getattr(repository, "list_code_inspection_reports", None)):
        return repository
    return None


def public_code_inspection_report(report: dict[str, Any], current_store: Any) -> dict[str, Any]:
    repository_id = report.get("repository_id")
    repository = (
        report.get("repository")
        or current_store.product_git_repositories.get(repository_id)
        or {}
    )
    return {
        **report,
        "repository_name": repository.get("name"),
        "repository_path": repository.get("project_path") or repository.get("remote_url"),
    }


def list_code_inspection_reports_response(
    *,
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
    }
    repository = code_inspection_query_repository(current_store)
    if repository is not None:
        items = repository.list_code_inspection_reports(
            product_id=product_id,
            repository_id=repository_id,
            risk_level=risk_level,
            status=status,
        )
    else:
        items = list(current_store.code_inspection_reports.values())
    if product_id:
        items = [item for item in items if item.get("product_id") == product_id]
    if repository_id:
        items = [item for item in items if item.get("repository_id") == repository_id]
    if risk_level:
        items = [item for item in items if item.get("risk_level") == risk_level]
    if status:
        items = [item for item in items if item.get("status") == status]
    items = [
        public_code_inspection_report(item, current_store)
        for item in items
        if list_text_matches(item, title, ("id", "summary", "repository_id"))
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


def code_inspection_detail_response(
    *,
    current_store: Any,
    report_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_code_inspection_read(user)
    repository = code_inspection_query_repository(current_store)
    if repository is not None and callable(getattr(repository, "get_code_inspection_detail", None)):
        detail = repository.get_code_inspection_detail(report_id)
        if detail is None:
            raise api_error(404, "NOT_FOUND", "Code inspection report not found")
        detail["report"] = public_code_inspection_report(detail["report"], current_store)
        return detail
    report = current_store.code_inspection_reports.get(report_id)
    if report is None:
        raise api_error(404, "NOT_FOUND", "Code inspection report not found")
    findings = [
        finding
        for finding in current_store.code_inspection_findings.values()
        if finding.get("report_id") == report_id
    ]
    findings.sort(
        key=lambda item: (
            -severity_rank(item.get("severity")),
            str(item.get("file_path") or ""),
            int(item.get("line_number") or 0),
            item["id"],
        )
    )
    notifications = [
        notification
        for notification in current_store.code_inspection_notifications.values()
        if notification.get("report_id") == report_id
    ]
    notifications.sort(key=lambda item: (item.get("created_at") or "", item["id"]))
    return {
        "findings": findings,
        "notifications": notifications,
        "report": public_code_inspection_report(report, current_store),
    }


def persist_code_inspection_records(
    current_store: Any,
    *,
    report: dict[str, Any],
    findings: list[dict[str, Any]],
    notifications: list[dict[str, Any]],
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_code_inspection_records", None)
    if callable(save_records):
        save_records(
            report=report,
            findings=findings,
            notifications=notifications,
            audit_event=audit_event,
        )
        return
