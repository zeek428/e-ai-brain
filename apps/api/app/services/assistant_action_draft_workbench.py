from __future__ import annotations

from typing import Any

from app.services.assistant_action_draft_common import (
    ASSISTANT_ACTION_DRAFT_STATUSES,
    ASSISTANT_ACTION_DRAFT_VALIDATION_STATUSES,
)


def assistant_action_draft_workbench_item(public_draft: dict[str, Any]) -> dict[str, Any]:
    metadata_json = (
        public_draft.get("metadata_json")
        if isinstance(public_draft.get("metadata_json"), dict)
        else {}
    )
    preview = public_draft.get("preview") if isinstance(public_draft.get("preview"), dict) else {}
    validation = preview.get("validation") if isinstance(preview.get("validation"), dict) else {}
    issues = validation.get("issues") if isinstance(validation.get("issues"), list) else []
    result_run = (
        public_draft.get("result_run") if isinstance(public_draft.get("result_run"), dict) else {}
    )
    governance = (
        public_draft.get("governance")
        if isinstance(public_draft.get("governance"), dict)
        else {}
    )
    impact = governance.get("impact") if isinstance(governance.get("impact"), dict) else {}
    permissions = (
        governance.get("permissions")
        if isinstance(governance.get("permissions"), dict)
        else {}
    )
    retries = governance.get("retries") if isinstance(governance.get("retries"), dict) else {}
    audit = governance.get("audit") if isinstance(governance.get("audit"), dict) else {}
    decision = (
        governance.get("decision")
        if isinstance(governance.get("decision"), dict)
        else {}
    )
    modified_fields = (
        metadata_json.get("modified_fields")
        if isinstance(metadata_json.get("modified_fields"), list)
        else []
    )
    validation_status = str(validation.get("status") or "unknown")
    result_status = str(result_run.get("status") or "").strip() or None
    return {
        "action": public_draft["action"],
        "cancel_reason": public_draft.get("cancel_reason"),
        "client_draft_id": public_draft.get("client_draft_id"),
        "can_confirm": bool(decision.get("can_confirm")),
        "confirmed_at": public_draft.get("confirmed_at"),
        "created_at": public_draft["created_at"],
        "created_by": public_draft["created_by"],
        "decision_label": decision.get("label"),
        "decision_next_action": decision.get("next_action"),
        "decision_reason": decision.get("reason"),
        "decision_status": decision.get("status"),
        "expires_at": public_draft.get("expires_at"),
        "id": public_draft["id"],
        "audit_event_count": _safe_int(audit.get("event_count")),
        "failure_count": _safe_int(retries.get("failure_count")),
        "impact_changed_field_count": _safe_int(impact.get("changed_field_count")),
        "impact_operation": impact.get("operation"),
        "impact_resource_id": impact.get("resource_id"),
        "impact_resource_type": impact.get("resource_type"),
        "latest_audit_event_at": audit.get("latest_event_at"),
        "latest_audit_event_type": audit.get("latest_event_type"),
        "modified_field_count": len(modified_fields),
        "permission_issue_count": _safe_int(permissions.get("issue_count")),
        "permission_status": permissions.get("status"),
        "retry_count": _safe_int(retries.get("retry_count")),
        "result_id": result_run.get("result_id"),
        "result_run_id": public_draft.get("result_run_id"),
        "result_status": result_status,
        "result_type": result_run.get("result_type"),
        "risk_level": public_draft.get("risk_level", "medium"),
        "source_link": f"/assistant?draft_id={public_draft['id']}",
        "source_message_id": public_draft.get("source_message_id"),
        "status": public_draft["status"],
        "title": public_draft["title"],
        "updated_at": public_draft["updated_at"],
        "user_modified": bool(metadata_json.get("user_modified") or modified_fields),
        "validation_issue_count": len(issues),
        "validation_status": (
            validation_status
            if validation_status in ASSISTANT_ACTION_DRAFT_VALIDATION_STATUSES
            else "unknown"
        ),
        "view_count": _safe_int(metadata_json.get("view_count")),
        "wizard_step_count": len(public_draft.get("wizard_steps") or []),
    }


def assistant_action_draft_workbench_summary(
    drafts: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(drafts)
    status_counts = {
        status: sum(1 for draft in drafts if draft.get("status") == status)
        for status in sorted(ASSISTANT_ACTION_DRAFT_STATUSES)
    }
    validation_counts = {
        status: sum(1 for draft in drafts if draft.get("validation_status") == status)
        for status in sorted(ASSISTANT_ACTION_DRAFT_VALIDATION_STATUSES)
    }
    risk_levels = {"critical", "high", "low", "medium", "unknown"}
    risk_counts = {
        risk: sum(1 for draft in drafts if str(draft.get("risk_level") or "unknown") == risk)
        for risk in sorted(risk_levels)
    }
    permission_statuses = {"blocked", "passed", "unknown", "warning"}
    permission_counts = {
        status: sum(
            1
            for draft in drafts
            if str(draft.get("permission_status") or "unknown") == status
        )
        for status in sorted(permission_statuses)
    }
    modified_count = sum(1 for draft in drafts if draft.get("user_modified"))
    high_risk_count = risk_counts["critical"] + risk_counts["high"]
    audit_event_total = sum(_safe_int(draft.get("audit_event_count")) for draft in drafts)
    permission_issue_total = sum(_safe_int(draft.get("permission_issue_count")) for draft in drafts)
    retry_total = sum(_safe_int(draft.get("retry_count")) for draft in drafts)
    validation_issue_total = sum(_safe_int(draft.get("validation_issue_count")) for draft in drafts)
    terminal_count = sum(
        status_counts[status] for status in ("cancelled", "confirmed", "expired", "failed")
    )
    confirmed_count = status_counts["confirmed"]
    decision_statuses = {"blocked", "expired", "failed", "ready", "terminal", "unknown", "warning"}
    decision_counts = {
        status: sum(
            1
            for draft in drafts
            if str(draft.get("decision_status") or "unknown") == status
        )
        for status in sorted(decision_statuses)
    }
    return {
        "adoption_rate": _ratio(confirmed_count, total),
        "confirm_blocked_count": (
            decision_counts["blocked"]
            + decision_counts["expired"]
            + decision_counts["failed"]
        ),
        "confirm_ready_count": decision_counts["ready"] + decision_counts["warning"],
        "decision_counts": decision_counts,
        "draft_total": total,
        "governance_counts": {
            "audit_events": audit_event_total,
            "failed": status_counts["failed"],
            "high_risk": high_risk_count,
            "permission_blocked": permission_counts["blocked"],
            "permission_issues": permission_issue_total,
            "permission_warning": permission_counts["warning"],
            "retry_total": retry_total,
            "validation_blocked": validation_counts["blocked"],
            "validation_issues": validation_issue_total,
            "validation_warning": validation_counts["warning"],
        },
        "permission_counts": permission_counts,
        "resolution_rate": _ratio(terminal_count, total),
        "risk_counts": risk_counts,
        "status_counts": status_counts,
        "user_modified_count": modified_count,
        "user_modified_rate": _ratio(modified_count, total),
        "validation_counts": validation_counts,
    }


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
