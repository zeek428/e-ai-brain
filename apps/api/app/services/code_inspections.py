from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
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
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.bugs import create_bug_result
from app.services.operational_records import record_audit_event, save_single_repository_record
from app.services.plugins import json_path_value

CODE_INSPECTION_ACTION_TYPES = {
    "create_bug_for_severe_findings",
    "create_task_for_severe_findings",
    "send_notification",
    "write_code_inspection_report",
}
CODE_INSPECTION_SEVERITIES = {"info", "low", "medium", "high", "critical"}
CODE_INSPECTION_RISK_LEVELS = {"low", "medium", "high", "critical"}
CODE_INSPECTION_NOTIFICATION_CHANNELS = {"dingtalk", "email", "webhook"}
CODE_INSPECTION_SUPPRESSION_REASONS = {
    "accepted_risk",
    "baseline",
    "false_positive",
    "ignored",
    "other",
}
CODE_INSPECTION_SORT_FIELDS = {
    "created_at",
    "committer_count",
    "finding_count",
    "id",
    "risk_level",
    "severe_finding_count",
    "status",
    "updated_at",
}
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
SEVERE_FINDING_THRESHOLD = "high"
DEFAULT_DASHBOARD_TREND_DAYS = 14
DEFAULT_SEVERITY_MAPPING = {
    "blocker": "critical",
    "major": "high",
    "minor": "low",
}
OPEN_BUG_STATUSES = {"assigned", "fixed", "needs_info", "open", "reopened", "triaged"}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


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


def normalized_severity_mapping(*mappings: Any) -> dict[str, str]:
    normalized = dict(DEFAULT_SEVERITY_MAPPING)
    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        for source, target in mapping.items():
            source_key = str(source or "").strip().lower()
            target_value = str(target or "").strip().lower()
            if source_key and target_value in CODE_INSPECTION_SEVERITIES:
                normalized[source_key] = target_value
    return normalized


def normalize_severity(
    value: Any,
    *,
    fallback: str = "medium",
    severity_mapping: dict[str, str] | None = None,
) -> str:
    normalized = str(value or fallback).lower()
    if severity_mapping and normalized in severity_mapping:
        normalized = severity_mapping[normalized]
    return normalized if normalized in CODE_INSPECTION_SEVERITIES else fallback


def normalize_risk_level(
    value: Any,
    findings: list[dict[str, Any]],
    *,
    severity_mapping: dict[str, str] | None = None,
) -> str:
    normalized = str(value or "").lower()
    if severity_mapping and normalized in severity_mapping:
        normalized = severity_mapping[normalized]
    if normalized in CODE_INSPECTION_RISK_LEVELS:
        return normalized
    if not findings:
        return "low"
    highest = max(findings, key=lambda item: severity_rank(item.get("severity")))
    highest_severity = str(highest.get("severity") or "medium")
    return highest_severity if highest_severity in CODE_INSPECTION_RISK_LEVELS else "medium"


def user_product_access(user: dict[str, Any]) -> tuple[bool, set[str]]:
    roles = set(user.get("roles") or [])
    if "admin" in roles:
        return True, set()
    product_ids: set[str] = set()
    for scope in user.get("scope_summary") or []:
        if scope.get("access_level") not in {"admin", "read", "write"}:
            continue
        scope_type = scope.get("scope_type")
        scope_id = scope.get("scope_id")
        if scope_type == "global" and scope_id == "*":
            return True, set()
        if scope_type == "product" and scope_id:
            product_ids.add(str(scope_id))
    return False, product_ids


def user_can_read_product(user: dict[str, Any], product_id: Any) -> bool:
    global_access, product_ids = user_product_access(user)
    if global_access:
        return True
    return product_id is not None and str(product_id) in product_ids


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
        if action_type in {"create_bug_for_severe_findings", "create_task_for_severe_findings"}:
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


def code_inspection_response_json(plugin_summary: dict[str, Any]) -> Any:
    return (plugin_summary.get("response_summary") or {}).get("json") or {}


def code_inspection_source_json(plugin_summary: dict[str, Any]) -> dict[str, Any]:
    response_json = code_inspection_response_json(plugin_summary)
    return response_json if isinstance(response_json, dict) else {}


def code_inspection_result_mapping(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    job_mapping = job.get("plugin_output_mapping") or {}
    if isinstance(job_mapping, dict) and job_mapping:
        return dict(job_mapping)
    action = current_store.plugin_actions.get(job.get("plugin_action_id")) or {}
    action_mapping = action.get("result_mapping") or {}
    return dict(action_mapping) if isinstance(action_mapping, dict) else {}


def mapped_code_inspection_source_json(
    current_store: Any,
    *,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
) -> dict[str, Any]:
    raw_json = code_inspection_response_json(plugin_summary)
    source = dict(raw_json) if isinstance(raw_json, dict) else {}
    mapping = code_inspection_result_mapping(current_store, job)
    path_fields = {
        "branch_path": "branch",
        "commit_sha_path": "commit_sha",
        "findings_path": "findings",
        "repository_id_path": "repository_id",
        "risk_level_path": "risk_level",
        "summary_path": "summary",
    }
    for mapping_key, source_key in path_fields.items():
        path = mapping.get(mapping_key)
        if not isinstance(path, str):
            continue
        value = json_path_value(raw_json, path)
        if value is not None:
            source[source_key] = value
    return source


def action_severity_mapping(current_store: Any, job: dict[str, Any]) -> dict[str, str]:
    action = current_store.plugin_actions.get(job.get("plugin_action_id")) or {}
    action_config = action.get("request_config") or {}
    job_config = job.get("config_json") or {}
    return normalized_severity_mapping(
        action_config.get("severity_mapping"),
        job_config.get("severity_mapping"),
    )


def nested_value(raw: dict[str, Any], section: str, key: str) -> Any:
    nested = raw.get(section)
    return nested.get(key) if isinstance(nested, dict) else None


def committer_field(raw: dict[str, Any], field: str) -> str | None:
    value = (
        raw.get(f"committer_{field}")
        or nested_value(raw, "committer", field)
        or raw.get(f"author_{field}")
        or nested_value(raw, "author", field)
    )
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def committer_key(finding: dict[str, Any]) -> str | None:
    value = (
        finding.get("committer_email")
        or finding.get("committer_username")
        or finding.get("committer_name")
    )
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def committer_summary(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for finding in findings:
        key = committer_key(finding)
        if key is None:
            continue
        entry = grouped.setdefault(
            key,
            {
                "bug_count": 0,
                "email": finding.get("committer_email"),
                "finding_count": 0,
                "name": finding.get("committer_name"),
                "severe_finding_count": 0,
                "username": finding.get("committer_username"),
            },
        )
        entry["finding_count"] += 1
        if severity_rank(finding.get("severity")) >= severity_rank(SEVERE_FINDING_THRESHOLD):
            entry["severe_finding_count"] += 1
        if finding.get("created_bug_id"):
            entry["bug_count"] += 1
    return sorted(
        grouped.values(),
        key=lambda item: (
            -int(item["severe_finding_count"]),
            -int(item["finding_count"]),
            str(item.get("email") or item.get("username") or item.get("name") or ""),
        ),
    )


def committer_count(findings: list[dict[str, Any]]) -> int:
    return len({key for finding in findings if (key := committer_key(finding))})


def report_matches_committer(report: dict[str, Any], committer: str | None) -> bool:
    if not committer:
        return True
    needle = committer.lower()
    for item in report.get("committer_summary") or []:
        haystack = " ".join(
            str(item.get(field) or "")
            for field in ("email", "name", "username")
        ).lower()
        if needle in haystack:
            return True
    return False


def finding_fingerprint(finding: dict[str, Any], report: dict[str, Any]) -> str:
    payload = {
        "branch": report.get("branch"),
        "committer": committer_key(finding),
        "file_path": finding.get("file_path"),
        "line_number": finding.get("line_number"),
        "repository_id": report.get("repository_id"),
        "rule_id": finding.get("rule_id"),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalized_findings(
    current_store: Any,
    *,
    raw_findings: Any,
    report_id: str,
    severity_mapping: dict[str, str] | None = None,
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
            "committer_email": committer_field(raw, "email"),
            "committer_name": committer_field(raw, "name"),
            "committer_username": committer_field(raw, "username"),
            "created_at": now,
            "created_bug_id": None,
            "created_task_id": None,
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
            "severity": normalize_severity(
                raw.get("severity"),
                severity_mapping=severity_mapping,
            ),
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


def normalized_repository_identifier(value: Any) -> str:
    return str(value or "").strip().removesuffix(".git").strip("/")


def repository_matches_identifier(repository: dict[str, Any], identifier: str) -> bool:
    if not identifier:
        return False
    candidates = {
        normalized_repository_identifier(repository.get("id")),
        normalized_repository_identifier(repository.get("project_id")),
        normalized_repository_identifier(repository.get("project_path")),
        normalized_repository_identifier(repository.get("remote_url")),
    }
    normalized = normalized_repository_identifier(identifier)
    return normalized in {candidate for candidate in candidates if candidate}


def configured_repository_id(job: dict[str, Any]) -> str | None:
    repository_id = normalized_repository_identifier(
        (job.get("config_json") or {}).get("repository_id"),
    )
    return repository_id or None


def resolve_code_inspection_repository_id(
    current_store: Any,
    *,
    job: dict[str, Any],
    source_json: dict[str, Any],
) -> str | None:
    source_repository_id = normalized_repository_identifier(source_json.get("repository_id"))
    configured_id = configured_repository_id(job)
    if source_repository_id and source_repository_id in current_store.product_git_repositories:
        return source_repository_id
    if source_repository_id:
        for repository in current_store.product_git_repositories.values():
            if job.get("product_id") and repository.get("product_id") != job.get("product_id"):
                continue
            if repository_matches_identifier(repository, source_repository_id):
                return str(repository["id"])
    return configured_id or source_repository_id or None


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


def previous_code_inspection_report(
    current_store: Any,
    *,
    branch: str | None,
    product_id: str | None,
    repository_id: str | None,
) -> dict[str, Any] | None:
    if not repository_id:
        return None
    candidates = [
        report
        for report in current_store.code_inspection_reports.values()
        if report.get("repository_id") == repository_id
        and report.get("branch") == branch
        and report.get("product_id") == product_id
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")),
        reverse=True,
    )[0]


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
    source_json = mapped_code_inspection_source_json(
        current_store,
        job=job,
        plugin_summary=plugin_summary,
    )
    severity_mapping = action_severity_mapping(current_store, job)
    repository_id = resolve_code_inspection_repository_id(
        current_store,
        job=job,
        source_json=source_json,
    )
    repository = None
    if repository_id is not None:
        source_json["repository_id"] = repository_id
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
        severity_mapping=severity_mapping,
    )
    now = datetime.now(UTC).isoformat()
    repository_default_branch = repository.get("default_branch") if repository else None
    branch = (
        source_json.get("branch")
        or (job.get("config_json") or {}).get("branch")
        or repository_default_branch
    )
    severe_finding_count = sum(
        1
        for finding in findings
        if severity_rank(finding.get("severity")) >= severity_rank(SEVERE_FINDING_THRESHOLD)
    )
    previous_report = previous_code_inspection_report(
        current_store,
        branch=branch,
        product_id=job.get("product_id"),
        repository_id=repository_id,
    )
    previous_report_id = previous_report.get("id") if previous_report else None
    previous_comparison = (
        {
            "finding_delta": len(findings) - int(previous_report.get("finding_count") or 0),
            "previous_finding_count": int(previous_report.get("finding_count") or 0),
            "previous_report_id": previous_report_id,
            "previous_severe_finding_count": int(
                previous_report.get("severe_finding_count") or 0
            ),
            "severe_finding_delta": severe_finding_count
            - int(previous_report.get("severe_finding_count") or 0),
        }
        if previous_report
        else {}
    )
    report = {
        "branch": branch,
        "collector_run_id": collector_run_id,
        "commit_sha": source_json.get("commit_sha"),
        "created_at": now,
        "created_bug_ids": [],
        "created_task_ids": [],
        "created_by": user["id"],
        "committer_count": committer_count(findings),
        "committer_summary": committer_summary(findings),
        "finding_count": len(findings),
        "id": report_id,
        "notification_ids": [],
        "plugin_action_id": job.get("plugin_action_id"),
        "plugin_connection_id": job.get("plugin_connection_id"),
        "plugin_invocation_log_id": plugin_summary.get("invocation_log_id"),
        "product_id": job.get("product_id"),
        "repository": repository_snapshot(current_store, repository_id),
        "repository_id": repository_id,
        "result_actions": result_actions,
        "risk_level": normalize_risk_level(
            source_json.get("risk_level"),
            findings,
            severity_mapping=severity_mapping,
        ),
        "coverage_warning": source_json.get("coverage_warning"),
        "artifact_ref": source_json.get("artifact_ref"),
        "checkout_path": source_json.get("checkout_path"),
        "checkout_path_retained": bool(source_json.get("checkout_path_retained")),
        "remote_url_hash": source_json.get("remote_url_hash"),
        "remote_url_summary": source_json.get("remote_url_summary"),
        "rules_version": source_json.get("rules_version"),
        "previous_comparison": previous_comparison,
        "previous_report_id": previous_report_id,
        "quality_gate": (
            source_json.get("quality_gate")
            if isinstance(source_json.get("quality_gate"), dict)
            else {}
        ),
        "scan_profile": (
            source_json.get("scan_profile")
            if isinstance(source_json.get("scan_profile"), dict)
            else {}
        ),
        "scan_finished_at": source_json.get("scan_finished_at"),
        "scan_started_at": source_json.get("scan_started_at"),
        "scanner_version": source_json.get("scanner_version"),
        "files_scanned": (
            source_json.get("files_scanned")
            if isinstance(source_json.get("files_scanned"), int)
            else 0
        ),
        "scheduled_job_id": job["id"],
        "scheduled_job_run_id": run_id,
        "scan_mode": source_json.get("scan_mode"),
        "scanner_name": source_json.get("scanner_name"),
        "severe_finding_count": severe_finding_count,
        "is_full_scan": bool(source_json.get("is_full_scan")),
        "lines_scanned": (
            source_json.get("lines_scanned")
            if isinstance(source_json.get("lines_scanned"), int)
            else 0
        ),
        "rules_loaded": (
            source_json.get("rules_loaded")
            if isinstance(source_json.get("rules_loaded"), list)
            else []
        ),
        "source_system": job.get("source_system"),
        "status": "completed",
        "summary": str(source_json.get("summary") or ""),
        "suppressed_finding_count": (
            source_json.get("suppressed_finding_count")
            if isinstance(source_json.get("suppressed_finding_count"), int)
            else 0
        ),
        "suppression_summary": (
            source_json.get("suppression_summary")
            if isinstance(source_json.get("suppression_summary"), dict)
            else {}
        ),
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
    if finding.get("committer_email") or finding.get("committer_name"):
        parts.append(
            "Committer: "
            f"{finding.get('committer_name') or '-'} "
            f"<{finding.get('committer_email') or '-'}>"
        )
    if finding.get("recommendation"):
        parts.append(f"Recommendation: {finding['recommendation']}")
    return "\n".join(str(part) for part in parts if str(part).strip())


def existing_code_inspection_bug_id(
    current_store: Any,
    *,
    fingerprint: str,
    product_id: str,
) -> str | None:
    repository = getattr(current_store, "repository", None)
    list_bug_summaries = getattr(repository, "list_bug_summaries", None)
    if callable(list_bug_summaries):
        bugs = list_bug_summaries(
            product_id=product_id,
            source="code_inspection",
            sort_by="created_at",
            sort_order="desc",
        )
    else:
        bugs = list(current_store.bugs.values())
    for bug in bugs:
        evidence = bug.get("evidence") or {}
        if (
            bug.get("product_id") == product_id
            and bug.get("source") == "code_inspection"
            and bug.get("status") in OPEN_BUG_STATUSES
            and evidence.get("finding_fingerprint") == fingerprint
        ):
            return str(bug["id"])
    return None


def create_bugs_for_findings(
    current_store: Any,
    *,
    findings: list[dict[str, Any]],
    report: dict[str, Any],
    severity_threshold: str,
    user: dict[str, Any],
) -> dict[str, list[str]]:
    created_ids: list[str] = []
    deduplicated_ids: list[str] = []
    threshold_rank = severity_rank(severity_threshold)
    for finding in findings:
        if severity_rank(finding.get("severity")) < threshold_rank:
            continue
        fingerprint = finding_fingerprint(finding, report)
        existing_bug_id = existing_code_inspection_bug_id(
            current_store,
            fingerprint=fingerprint,
            product_id=report["product_id"],
        )
        if existing_bug_id is not None:
            finding["created_bug_id"] = existing_bug_id
            current_store.code_inspection_findings[finding["id"]] = finding
            deduplicated_ids.append(existing_bug_id)
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
                "committer_email": finding.get("committer_email"),
                "committer_name": finding.get("committer_name"),
                "committer_username": finding.get("committer_username"),
                "file_path": finding.get("file_path"),
                "finding_fingerprint": fingerprint,
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
    report["created_bug_ids"] = [
        *report.get("created_bug_ids", []),
        *created_ids,
        *deduplicated_ids,
    ]
    report["committer_count"] = committer_count(findings)
    report["committer_summary"] = committer_summary(findings)
    report["updated_at"] = datetime.now(UTC).isoformat()
    current_store.code_inspection_reports[report["id"]] = report
    persist_code_inspection_records(
        current_store,
        report=report,
        findings=findings,
        notifications=[],
    )
    return {"created_ids": created_ids, "deduplicated_ids": deduplicated_ids}


def persist_ai_task_record(
    current_store: Any,
    *,
    audit_event: dict[str, Any],
    task: dict[str, Any],
) -> None:
    save_single_repository_record(
        current_store,
        "save_ai_task_record",
        task,
        audit_event=audit_event,
    )


def finding_task_input(finding: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    return {
        "branch": report.get("branch"),
        "code_inspection_finding_id": finding["id"],
        "code_inspection_report_id": report["id"],
        "commit_sha": report.get("commit_sha"),
        "committer_email": finding.get("committer_email"),
        "committer_name": finding.get("committer_name"),
        "committer_username": finding.get("committer_username"),
        "description": finding.get("description"),
        "file_path": finding.get("file_path"),
        "line_number": finding.get("line_number"),
        "recommendation": finding.get("recommendation"),
        "repository": report.get("repository") or {},
        "repository_id": report.get("repository_id"),
        "risk_level": report.get("risk_level"),
        "rule_id": finding.get("rule_id"),
        "severity": finding.get("severity"),
        "title": finding.get("title"),
    }


def create_tasks_for_findings(
    current_store: Any,
    *,
    findings: list[dict[str, Any]],
    report: dict[str, Any],
    severity_threshold: str,
    user: dict[str, Any],
) -> list[str]:
    created_ids: list[str] = []
    threshold_rank = severity_rank(severity_threshold)
    now = datetime.now(UTC).isoformat()
    for finding in findings:
        if severity_rank(finding.get("severity")) < threshold_rank:
            continue
        if finding.get("created_task_id"):
            continue
        task_id = current_store.new_id("task")
        task = {
            "brain_app_id": DEFAULT_BRAIN_APP_ID,
            "created_at": now,
            "created_by": user["id"],
            "current_step": "draft",
            "error_code": None,
            "error_message": None,
            "graph_run_ids": [],
            "id": task_id,
            "input_json": finding_task_input(finding, report),
            "module_code": None,
            "output_json": None,
            "product_context": {
                "repository": report.get("repository") or {},
                "source": "code_inspection",
            },
            "product_id": report["product_id"],
            "requirement_id": None,
            "requirement_snapshot": None,
            "review_ids": [],
            "status": "draft",
            "task_type": "code_inspection_remediation",
            "title": f"[Code Inspection Remediation] {finding['title']}",
            "updated_at": now,
            "version_id": None,
        }
        current_store.ai_tasks[task_id] = task
        finding["created_task_id"] = task_id
        current_store.code_inspection_findings[finding["id"]] = finding
        created_ids.append(task_id)
        audit_event = record_audit_event(
            current_store,
            event_type="code_inspection_remediation_task.created",
            actor_id=user["id"],
            subject_type="ai_task",
            subject_id=task_id,
            payload={
                "code_inspection_finding_id": finding["id"],
                "code_inspection_report_id": report["id"],
                "severity": finding.get("severity"),
            },
        )
        persist_ai_task_record(current_store, task=task, audit_event=audit_event)
    report["created_task_ids"] = [*report.get("created_task_ids", []), *created_ids]
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
    deduplicated_bug_ids: list[str] = []
    notification_ids: list[str] = []
    task_ids: list[str] = []
    action_results: list[dict[str, Any]] = []
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
            action_results.append(
                {
                    "action_type": action_type,
                    "finding_count": len(findings),
                    "report_id": report["id"],
                    "status": "succeeded",
                }
            )
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
                action_results.append(
                    {
                        "action_type": "write_code_inspection_report",
                        "finding_count": len(findings),
                        "report_id": report["id"],
                        "status": "succeeded",
                    }
                )
            bug_result = create_bugs_for_findings(
                current_store,
                findings=findings,
                report=report,
                severity_threshold=action.get("severity_threshold") or "critical",
                user=user,
            )
            bug_ids.extend(bug_result["created_ids"])
            deduplicated_bug_ids.extend(bug_result["deduplicated_ids"])
            action_results.append(
                {
                    "action_type": action_type,
                    "created_bug_ids": bug_result["created_ids"],
                    "deduplicated_bug_ids": bug_result["deduplicated_ids"],
                    "severity_threshold": action.get("severity_threshold") or "critical",
                    "status": "succeeded",
                }
            )
        elif action_type == "create_task_for_severe_findings":
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
                action_results.append(
                    {
                        "action_type": "write_code_inspection_report",
                        "finding_count": len(findings),
                        "report_id": report["id"],
                        "status": "succeeded",
                    }
                )
            created_task_ids = create_tasks_for_findings(
                current_store,
                findings=findings,
                report=report,
                severity_threshold=action.get("severity_threshold") or "high",
                user=user,
            )
            task_ids.extend(created_task_ids)
            action_results.append(
                {
                    "action_type": action_type,
                    "created_task_ids": created_task_ids,
                    "severity_threshold": action.get("severity_threshold") or "high",
                    "status": "succeeded",
                }
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
                action_results.append(
                    {
                        "action_type": "write_code_inspection_report",
                        "finding_count": len(findings),
                        "report_id": report["id"],
                        "status": "succeeded",
                    }
                )
            created_notification_ids = create_code_inspection_notifications(
                current_store,
                action=action,
                report=report,
                user=user,
            )
            notification_ids.extend(created_notification_ids)
            action_results.append(
                {
                    "action_type": action_type,
                    "channels": action.get("channels") or [],
                    "created_notification_ids": created_notification_ids,
                    "status": "succeeded",
                }
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
        action_results.append(
            {
                "action_type": "write_code_inspection_report",
                "finding_count": len(findings),
                "report_id": report["id"],
                "status": "succeeded",
            }
        )
    return {
        "action_results": action_results,
        "bug_ids": bug_ids,
        "deduplicated_bug_ids": deduplicated_bug_ids,
        "finding_count": len(findings),
        "findings": findings,
        "notification_ids": notification_ids,
        "report": report,
        "report_written": report_written,
        "result_actions": actions,
        "task_ids": task_ids,
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
        items = list(current_store.code_inspection_reports.values())
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
    return [public_code_inspection_report(item, current_store) for item in items]


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
        for finding in current_store.code_inspection_findings.values()
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
    committer_stats: dict[str, dict[str, Any]] = {}
    rule_version_counts: Counter[str] = Counter()
    scanner_version_counts: Counter[str] = Counter()
    suppression_counts: Counter[str] = Counter()
    trend_stats: dict[str, dict[str, Any]] = {}
    severe_finding_count = 0
    covered_by_bug_count = 0
    covered_by_task_count = 0
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
        elif quality_gate_status == "skipped":
            trend["quality_gate_skipped_count"] += 1
        else:
            trend["quality_gate_unknown_count"] += 1

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
            if is_severe:
                severe_finding_count += 1
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
    rule_distribution = sorted(
        rule_stats.values(),
        key=lambda item: (
            -int(item["severe_finding_count"]),
            -int(item["finding_count"]),
            str(item["rule_id"]),
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
    sla_status = (
        "healthy" if bug_coverage_rate >= 0.8 and task_coverage_rate >= 0.8 else "at_risk"
    )
    return {
        "branch_ranking": branch_ranking,
        "category_distribution": counter_rows(category_counts, key_name="category"),
        "committer_ranking": committer_ranking,
        "query": {
            "product_id": product_id,
            "repository_id": repository_id,
            "risk_level": risk_level,
            "status": status,
        },
        "repository_ranking": repository_ranking,
        "risk_distribution": counter_rows(risk_counts, key_name="risk_level"),
        "rule_distribution": rule_distribution,
        "rule_governance": {
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
        items = [
            public_code_inspection_report(item, current_store)
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
        if not user_can_read_product(user, detail["report"].get("product_id")):
            raise api_error(404, "NOT_FOUND", "Code inspection report not found")
        detail["report"] = public_code_inspection_report(detail["report"], current_store)
        detail["scan_summary"] = code_inspection_scan_summary(
            detail["report"],
            detail.get("findings") or [],
        )
        return detail
    report = current_store.code_inspection_reports.get(report_id)
    if report is None:
        raise api_error(404, "NOT_FOUND", "Code inspection report not found")
    if not user_can_read_product(user, report.get("product_id")):
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
        "scan_summary": code_inspection_scan_summary(report, findings),
    }


def _code_inspection_detail_raw(current_store: Any, report_id: str) -> dict[str, Any]:
    repository = code_inspection_query_repository(current_store)
    if repository is not None and callable(getattr(repository, "get_code_inspection_detail", None)):
        detail = repository.get_code_inspection_detail(report_id)
        if detail is None:
            raise api_error(404, "NOT_FOUND", "Code inspection report not found")
        return detail
    report = current_store.code_inspection_reports.get(report_id)
    if report is None:
        raise api_error(404, "NOT_FOUND", "Code inspection report not found")
    findings = [
        finding
        for finding in current_store.code_inspection_findings.values()
        if finding.get("report_id") == report_id
    ]
    notifications = [
        notification
        for notification in current_store.code_inspection_notifications.values()
        if notification.get("report_id") == report_id
    ]
    return {"findings": findings, "notifications": notifications, "report": report}


def _code_inspection_finding_from_detail(
    detail: dict[str, Any],
    finding_id: str,
) -> dict[str, Any]:
    for finding in detail.get("findings") or []:
        if finding.get("id") == finding_id:
            return finding
    raise api_error(404, "NOT_FOUND", "Code inspection finding not found")


def _persist_code_inspection_suppression_change(
    current_store: Any,
    *,
    audit_event: dict[str, Any],
    finding: dict[str, Any],
    notifications: list[dict[str, Any]],
    report: dict[str, Any],
) -> None:
    if hasattr(current_store, "code_inspection_reports"):
        current_store.code_inspection_reports[report["id"]] = report
    if hasattr(current_store, "code_inspection_findings"):
        current_store.code_inspection_findings[finding["id"]] = finding
    persist_code_inspection_records(
        current_store,
        audit_event=audit_event,
        findings=[finding],
        notifications=notifications,
        report=report,
    )


def request_code_inspection_finding_suppression_response(
    *,
    current_store: Any,
    finding_id: str,
    payload: Any,
    report_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_code_inspection_read(user)
    detail = _code_inspection_detail_raw(current_store, report_id)
    report = detail["report"]
    if not user_can_read_product(user, report.get("product_id")):
        raise api_error(404, "NOT_FOUND", "Code inspection report not found")
    finding = _code_inspection_finding_from_detail(detail, finding_id)
    if finding.get("suppression_status") == "approved":
        raise api_error(
            409,
            "CODE_INSPECTION_SUPPRESSION_ALREADY_APPROVED",
            "Code inspection finding suppression is already approved",
        )
    reason = str(getattr(payload, "reason", None) or "false_positive").strip() or "false_positive"
    ensure_enum(reason, CODE_INSPECTION_SUPPRESSION_REASONS, "reason")
    timestamp = now_iso()
    finding["suppression_status"] = "pending"
    finding["suppression_reason"] = reason
    finding["suppression_note"] = str(getattr(payload, "note", None) or "").strip() or None
    finding["suppression_requested_by"] = user["id"]
    finding["suppression_requested_at"] = timestamp
    finding["suppression_reviewed_by"] = None
    finding["suppression_reviewed_at"] = None
    finding["updated_at"] = timestamp
    report["updated_at"] = timestamp
    audit_event = current_store.audit(
        actor_id=user["id"],
        event_type="code_inspection_finding_suppression.requested",
        payload={
            "finding_id": finding_id,
            "reason": reason,
            "report_id": report_id,
            "rule_id": finding.get("rule_id"),
        },
        subject_id=finding_id,
        subject_type="code_inspection_finding",
    )
    _persist_code_inspection_suppression_change(
        current_store,
        audit_event=audit_event,
        finding=finding,
        notifications=detail.get("notifications") or [],
        report=report,
    )
    return code_inspection_detail_response(
        current_store=current_store,
        report_id=report_id,
        user=user,
    )


def review_code_inspection_finding_suppression_response(
    *,
    current_store: Any,
    finding_id: str,
    payload: Any,
    report_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_code_inspection_read(user)
    detail = _code_inspection_detail_raw(current_store, report_id)
    report = detail["report"]
    if not user_can_read_product(user, report.get("product_id")):
        raise api_error(404, "NOT_FOUND", "Code inspection report not found")
    finding = _code_inspection_finding_from_detail(detail, finding_id)
    if finding.get("suppression_status") != "pending":
        raise api_error(
            409,
            "CODE_INSPECTION_SUPPRESSION_REVIEW_INVALID",
            "Only pending suppression requests can be reviewed",
        )
    decision = str(getattr(payload, "decision", None) or "").strip().lower()
    ensure_enum(decision, {"approve", "reject"}, "decision")
    timestamp = now_iso()
    reason = str(finding.get("suppression_reason") or "false_positive")
    if decision == "approve":
        finding["suppression_status"] = "approved"
        summary = dict(report.get("suppression_summary") or {})
        summary[reason] = int(summary.get(reason) or 0) + 1
        report["suppression_summary"] = summary
        report["suppressed_finding_count"] = int(report.get("suppressed_finding_count") or 0) + 1
    else:
        finding["suppression_status"] = "rejected"
    finding["suppression_note"] = str(getattr(payload, "note", None) or "").strip() or finding.get(
        "suppression_note"
    )
    finding["suppression_reviewed_by"] = user["id"]
    finding["suppression_reviewed_at"] = timestamp
    finding["updated_at"] = timestamp
    report["updated_at"] = timestamp
    audit_event = current_store.audit(
        actor_id=user["id"],
        event_type=(
            "code_inspection_finding_suppression.approved"
            if decision == "approve"
            else "code_inspection_finding_suppression.rejected"
        ),
        payload={
            "decision": decision,
            "finding_id": finding_id,
            "reason": reason,
            "report_id": report_id,
            "rule_id": finding.get("rule_id"),
        },
        subject_id=finding_id,
        subject_type="code_inspection_finding",
    )
    _persist_code_inspection_suppression_change(
        current_store,
        audit_event=audit_event,
        finding=finding,
        notifications=detail.get("notifications") or [],
        report=report,
    )
    return code_inspection_detail_response(
        current_store=current_store,
        report_id=report_id,
        user=user,
    )


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
