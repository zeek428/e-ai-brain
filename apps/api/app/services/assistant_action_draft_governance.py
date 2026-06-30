from __future__ import annotations

from typing import Any

from app.services.assistant_action_draft_common import assistant_action_draft_decision


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _user_has_permission(user: dict[str, Any], permission: str) -> bool:
    permissions = set(user.get("permissions") or [])
    roles = set(user.get("roles") or [])
    return "system.admin" in permissions or "admin" in roles or permission in permissions


def assistant_action_required_permissions(action: str) -> list[str]:
    if action in {"create_ai_agent", "create_ai_skill"}:
        return ["system.ai_capabilities.manage"]
    if action == "create_scheduled_job":
        return ["system.scheduled_jobs.manage"]
    if action in {"create_plugin_action", "create_plugin_connection"}:
        return ["system.plugins.manage"]
    if action == "create_rd_task":
        return ["role:product_owner_or_rd_owner"]
    return []


def assistant_action_missing_permissions(
    *,
    action: str,
    required_permissions: list[str],
    user: dict[str, Any] | None,
) -> list[str]:
    if user is None:
        return []
    if action == "create_rd_task":
        roles = set(user.get("roles") or [])
        if "admin" in roles or roles.intersection({"product_owner", "rd_owner"}):
            return []
        return required_permissions
    return [
        permission
        for permission in required_permissions
        if not _user_has_permission(user, permission)
    ]


def assistant_action_draft_governance(
    draft: dict[str, Any],
    *,
    audit_events: list[dict[str, Any]],
    preview: dict[str, Any],
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata_json = (
        draft.get("metadata_json")
        if isinstance(draft.get("metadata_json"), dict)
        else {}
    )
    validation = preview.get("validation") if isinstance(preview.get("validation"), dict) else {}
    validation_issues = (
        validation.get("issues") if isinstance(validation.get("issues"), list) else []
    )
    permission_issues = [
        dict(issue)
        for issue in validation_issues
        if isinstance(issue, dict) and str(issue.get("field") or "") == "permission"
    ]
    action = str(draft.get("action") or "")
    required_permissions = assistant_action_required_permissions(action)
    missing_permissions = assistant_action_missing_permissions(
        action=action,
        required_permissions=required_permissions,
        user=user,
    )
    permission_status = "blocked" if missing_permissions or permission_issues else "passed"
    target = preview.get("target") if isinstance(preview.get("target"), dict) else {}
    diffs = preview.get("diffs") if isinstance(preview.get("diffs"), list) else []
    payload = draft.get("payload") if isinstance(draft.get("payload"), dict) else {}
    normalized_diffs = [
        {
            "change_type": str(diff.get("change_type") or ""),
            "field": str(diff.get("field") or ""),
            "label": str(diff.get("label") or diff.get("field") or ""),
        }
        for diff in diffs
        if isinstance(diff, dict)
    ]
    failure_history = metadata_json.get("failure_history")
    if not isinstance(failure_history, list):
        failure_history = []
    current_failure = metadata_json.get("failure")
    failure_sources = list(failure_history)
    if isinstance(current_failure, dict):
        failure_sources.append({"failure": current_failure})
    last_failure = failure_sources[-1] if failure_sources else {}
    last_failure_payload = (
        last_failure.get("failure") if isinstance(last_failure.get("failure"), dict) else {}
    )
    latest_event = audit_events[-1] if audit_events else {}
    audit_snapshot = {
        "event_count": len(audit_events),
        "event_types": sorted(
            {
                str(event.get("event_type") or "")
                for event in audit_events
                if str(event.get("event_type") or "")
            }
        ),
        "latest_actor_id": latest_event.get("actor_id"),
        "latest_event_at": latest_event.get("created_at"),
        "latest_event_id": latest_event.get("id"),
        "latest_event_type": latest_event.get("event_type"),
    }
    retry_snapshot = {
        "can_retry": draft.get("status") == "failed",
        "failure_count": len(failure_sources),
        "last_failure_code": last_failure_payload.get("code"),
        "last_failure_message": last_failure_payload.get("message"),
        "retry_count": _safe_int(metadata_json.get("retry_count")),
        "retry_reason": metadata_json.get("retry_reason"),
    }
    risk_level = str(draft.get("risk_level") or "medium")
    validation_status = str(validation.get("status") or "unknown")
    permission_issue_count = len(permission_issues) + len(missing_permissions)
    decision = assistant_action_draft_decision(
        audit_event_count=audit_snapshot["event_count"],
        draft=draft,
        last_failure_payload=last_failure_payload,
        missing_permissions=missing_permissions,
        permission_issue_count=permission_issue_count,
        permission_status=permission_status,
        risk_level=risk_level,
        validation_issue_count=len(validation_issues),
        validation_status=validation_status,
    )
    return {
        "audit": audit_snapshot,
        "decision": decision,
        "diff": {
            "changed_fields": normalized_diffs,
            "count": len(normalized_diffs),
        },
        "impact": {
            "changed_field_count": len(normalized_diffs),
            "operation": target.get("operation") or "create",
            "payload_field_count": len(payload),
            "resource_id": target.get("resource_id"),
            "resource_type": target.get("resource_type") or draft.get("action"),
            "source_resource": target.get("source_resource"),
        },
        "permissions": {
            "issue_count": permission_issue_count,
            "issues": permission_issues,
            "missing_permissions": missing_permissions,
            "required_permissions": required_permissions,
            "status": permission_status,
        },
        "retries": retry_snapshot,
        "risk": {
            "level": risk_level,
            "reason": metadata_json.get("risk_reason"),
        },
    }
