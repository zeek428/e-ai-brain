from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.api.deps import api_error, require_permissions
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.core.task_titles import code_inspection_remediation_title
from app.services.bugs import create_bug_result
from app.services.code_inspection_common import (
    CODE_INSPECTION_SUPPRESSION_REASONS,
    OPEN_BUG_STATUSES,
    SEVERE_FINDING_THRESHOLD,
    committer_count,
    committer_field,
    committer_key,
    committer_summary,
    default_code_inspection_result_actions,
    ensure_enum,
    normalize_risk_level,
    normalize_severity,
    normalized_severity_mapping,
    severity_rank,
)
from app.services.code_inspection_common import (
    validate_code_inspection_result_actions as validate_code_inspection_result_actions,
)
from app.services.code_inspection_detail_projection import (
    code_inspection_governance_summary,
    code_inspection_scan_summary,
    normalize_optional_datetime,
)
from app.services.code_inspection_read_models import (
    code_inspection_dashboard_response as code_inspection_dashboard_response,
)
from app.services.code_inspection_read_models import (
    code_inspection_query_repository,
    public_code_inspection_report,
)
from app.services.code_inspection_read_models import (
    list_code_inspection_reports_response as list_code_inspection_reports_response,
)
from app.services.plugin_result_mapping import json_path_value
from app.services.product_scope import user_can_read_product
from app.services.system_settings import send_system_email


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def record_audit_event(
    current_store: Any,
    *,
    event_type: str,
    actor_id: str,
    subject_type: str,
    subject_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audit_events = getattr(current_store, "audit_events", None)
    sequence = len(audit_events) + 1 if isinstance(audit_events, list) else 1
    return {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": sequence,
        "created_at": now_iso(),
    }


def _memory_collection(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


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


def _memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, list):
        collection = []
        setattr(current_store, collection_name, collection)
    return collection


def _merged_unique_ids(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for item in group:
            item_id = str(item)
            if item_id and item_id not in merged:
                merged.append(item_id)
    return merged


def require_code_inspection_read(user: dict[str, Any]) -> None:
    require_permissions(user, {"code_inspection.read"})


def code_inspection_response_json(plugin_summary: dict[str, Any]) -> Any:
    return (plugin_summary.get("response_summary") or {}).get("json") or {}


def code_inspection_source_json(plugin_summary: dict[str, Any]) -> dict[str, Any]:
    response_json = code_inspection_response_json(plugin_summary)
    return response_json if isinstance(response_json, dict) else {}


def code_inspection_result_mapping(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    job_mapping = job.get("plugin_output_mapping") or {}
    if isinstance(job_mapping, dict) and job_mapping:
        return dict(job_mapping)
    action = _read_memory_record(
        current_store,
        "plugin_actions",
        job.get("plugin_action_id"),
    ) or {}
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
    action = _read_memory_record(
        current_store,
        "plugin_actions",
        job.get("plugin_action_id"),
    ) or {}
    action_config = action.get("request_config") or {}
    job_config = job.get("config_json") or {}
    return normalized_severity_mapping(
        action_config.get("severity_mapping"),
        job_config.get("severity_mapping"),
    )


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
    repository = _read_memory_record(
        current_store,
        "product_git_repositories",
        repository_id,
    )
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
    repositories = _read_memory_collection(current_store, "product_git_repositories")
    if source_repository_id and source_repository_id in repositories:
        return source_repository_id
    if source_repository_id:
        for repository in repositories.values():
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
            _memory_collection(current_store, "product_git_repositories")[
                str(git_repository["id"])
            ] = dict(git_repository)


def previous_code_inspection_report(
    current_store: Any,
    *,
    branch: str | None,
    product_id: str | None,
    repository_id: str | None,
) -> dict[str, Any] | None:
    if not repository_id:
        return None
    query_repository = code_inspection_query_repository(current_store)
    if query_repository is not None and callable(
        getattr(query_repository, "list_code_inspection_reports", None)
    ):
        reports = {
            str(report["id"]): report
            for report in query_repository.list_code_inspection_reports(
                product_id=product_id,
                repository_id=repository_id,
            )
            if report.get("id") is not None
        }
    else:
        reports = _read_memory_collection(current_store, "code_inspection_reports")
    candidates = [
        report
        for report in reports.values()
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
        repository = _read_memory_record(
            current_store,
            "product_git_repositories",
            repository_id,
        )
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
        "incremental_file_count": (
            source_json.get("incremental_file_count")
            if isinstance(source_json.get("incremental_file_count"), int)
            else None
        ),
        "incremental_from_commit": source_json.get("incremental_from_commit"),
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
        bugs = list(_read_memory_collection(current_store, "bugs").values())
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
    report["created_bug_ids"] = _merged_unique_ids(
        [str(item) for item in report.get("created_bug_ids", [])],
        created_ids,
        deduplicated_ids,
    )
    report["committer_count"] = committer_count(findings)
    report["committer_summary"] = committer_summary(findings)
    report["updated_at"] = datetime.now(UTC).isoformat()
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
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_ai_task_record", None)
    if callable(save_record):
        save_record(task, audit_event=audit_event)
        return
    _memory_collection(current_store, "ai_tasks")[str(task["id"])] = task
    _memory_list(current_store, "audit_events").append(audit_event)


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


def finding_task_title(finding: dict[str, Any]) -> str:
    return code_inspection_remediation_title(finding)


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
            "title": finding_task_title(finding),
            "updated_at": now,
            "version_id": None,
        }
        finding["created_task_id"] = task_id
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
        response_summary: dict[str, Any] = {"status": "recorded"}
        if channel == "email":
            response_summary = send_system_email(
                current_store,
                body=(
                    f"代码巡检报告 {report['id']} 已完成。\n"
                    f"风险等级: {report['risk_level']}\n"
                    f"问题数: {report['finding_count']}\n"
                    f"严重问题数: {report['severe_finding_count']}"
                ),
                recipients=[str(recipient) for recipient in recipients],
                subject=(
                    f"[AI Brain] 代码巡检问题通知 "
                    f"{report['id']} · {report['risk_level']}"
                ),
            )
        target = (
            str(action.get("webhook_url"))
            if channel == "dingtalk" and action.get("webhook_url")
            else ",".join(str(recipient) for recipient in recipients)
        )
        status = str(
            response_summary.get("delivery_status")
            or response_summary.get("status")
            or "recorded",
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
            "response_summary": response_summary,
            "status": status,
            "target": target,
            "updated_at": now,
        }
        notifications.append(notification)
        created_ids.append(notification_id)
    report["notification_ids"] = [*report.get("notification_ids", []), *created_ids]
    report["updated_at"] = datetime.now(UTC).isoformat()
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
    task_promotion_deferred = False
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
            bug_result = create_bugs_for_findings(
                current_store,
                findings=findings,
                report=report,
                severity_threshold=action.get("severity_threshold") or "high",
                user=user,
            )
            bug_ids.extend(bug_result["created_ids"])
            deduplicated_bug_ids.extend(bug_result["deduplicated_ids"])
            task_promotion_deferred = True
            action_results.append(
                {
                    "action_type": action_type,
                    "created_bug_ids": bug_result["created_ids"],
                    "created_task_ids": [],
                    "deduplicated_bug_ids": bug_result["deduplicated_ids"],
                    "deferred_to": "bug_confirmation",
                    "message": "代码扫描不直接创建研发任务；请在 Bug 确认后推进 AI Task。",
                    "severity_threshold": action.get("severity_threshold") or "high",
                    "status": "deferred_to_bug_confirmation",
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
        "task_promotion_deferred": task_promotion_deferred,
        "task_ids": task_ids,
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
        detail["governance_summary"] = code_inspection_governance_summary(
            detail["report"],
            detail.get("findings") or [],
        )
        return detail
    report = _read_memory_record(current_store, "code_inspection_reports", report_id)
    if report is None:
        raise api_error(404, "NOT_FOUND", "Code inspection report not found")
    if not user_can_read_product(user, report.get("product_id")):
        raise api_error(404, "NOT_FOUND", "Code inspection report not found")
    findings = [
        finding
        for finding in _read_memory_collection(
            current_store,
            "code_inspection_findings",
        ).values()
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
        for notification in _read_memory_collection(
            current_store,
            "code_inspection_notifications",
        ).values()
        if notification.get("report_id") == report_id
    ]
    notifications.sort(key=lambda item: (item.get("created_at") or "", item["id"]))
    return {
        "findings": findings,
        "governance_summary": code_inspection_governance_summary(report, findings),
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
    report = _read_memory_record(current_store, "code_inspection_reports", report_id)
    if report is None:
        raise api_error(404, "NOT_FOUND", "Code inspection report not found")
    findings = [
        finding
        for finding in _read_memory_collection(
            current_store,
            "code_inspection_findings",
        ).values()
        if finding.get("report_id") == report_id
    ]
    notifications = [
        notification
        for notification in _read_memory_collection(
            current_store,
            "code_inspection_notifications",
        ).values()
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
    expires_at = normalize_optional_datetime(
        getattr(payload, "expires_at", None),
        "expires_at",
    )
    owner = str(getattr(payload, "owner", None) or "").strip() or None
    if reason == "accepted_risk" and expires_at is None:
        raise api_error(
            422,
            "ACCEPTED_RISK_EXPIRY_REQUIRED",
            "Accepted risk suppression requires expires_at",
        )
    timestamp = now_iso()
    finding["suppression_status"] = "pending"
    finding["suppression_reason"] = reason
    finding["suppression_note"] = str(getattr(payload, "note", None) or "").strip() or None
    finding["suppression_owner"] = owner or (user["id"] if reason == "accepted_risk" else None)
    finding["suppression_expires_at"] = expires_at if reason == "accepted_risk" else None
    finding["suppression_requested_by"] = user["id"]
    finding["suppression_requested_at"] = timestamp
    finding["suppression_reviewed_by"] = None
    finding["suppression_reviewed_at"] = None
    finding["updated_at"] = timestamp
    report["updated_at"] = timestamp
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type="code_inspection_finding_suppression.requested",
        payload={
            "finding_id": finding_id,
            "owner": finding.get("suppression_owner"),
            "reason": reason,
            "report_id": report_id,
            "rule_id": finding.get("rule_id"),
            "suppression_expires_at": expires_at,
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
    audit_event = record_audit_event(
        current_store,
        actor_id=user["id"],
        event_type=(
            "code_inspection_finding_suppression.approved"
            if decision == "approve"
            else "code_inspection_finding_suppression.rejected"
        ),
        payload={
            "decision": decision,
            "finding_id": finding_id,
            "owner": finding.get("suppression_owner"),
            "reason": reason,
            "report_id": report_id,
            "rule_id": finding.get("rule_id"),
            "suppression_expires_at": finding.get("suppression_expires_at"),
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
    _memory_collection(current_store, "code_inspection_reports")[str(report["id"])] = report
    finding_collection = _memory_collection(current_store, "code_inspection_findings")
    for finding in findings:
        finding_collection[str(finding["id"])] = finding
    notification_collection = _memory_collection(current_store, "code_inspection_notifications")
    for notification in notifications:
        notification_collection[str(notification["id"])] = notification
    if audit_event is not None:
        _memory_list(current_store, "audit_events").append(audit_event)
