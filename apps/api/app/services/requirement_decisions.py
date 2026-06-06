from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.services.requirements import (
    REQUIREMENT_CLOSABLE_STATUSES,
    record_audit_event,
    save_requirement_record,
    uses_repository_context,
)
from app.services.version_status import canonical_requirement_status


def approve_requirement_result(
    *,
    current_store: Any,
    payload: Any,
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if canonical_requirement_status(requirement.get("status")) != "submitted":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not pending approval")

    requirement = {
        **requirement,
        "approval_comment": payload.comment,
        "status": "planned" if requirement.get("version_id") else "approved",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if not uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = record_audit_event(
        current_store,
        event_type="requirement.approved",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    save_requirement_record(current_store, requirement, audit_event=audit_event)
    return requirement


def reject_requirement_result(
    *,
    current_store: Any,
    payload: Any,
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if canonical_requirement_status(requirement.get("status")) != "submitted":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not pending approval")

    rejection_reason = payload.rejection_reason or payload.comment
    if not rejection_reason:
        raise api_error(400, "VALIDATION_ERROR", "rejection_reason is required")
    requirement = {
        **requirement,
        "rejection_reason": rejection_reason,
        "status": "rejected",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if not uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = record_audit_event(
        current_store,
        event_type="requirement.rejected",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    save_requirement_record(current_store, requirement, audit_event=audit_event)
    return requirement


def close_requirement_result(
    *,
    current_store: Any,
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if canonical_requirement_status(requirement.get("status")) not in REQUIREMENT_CLOSABLE_STATUSES:
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement cannot be closed")

    active_tasks = [
        current_store.ai_tasks[task_id]
        for task_id in requirement.get("task_ids", [])
        if current_store.ai_tasks[task_id]["status"]
        not in {"completed", "failed", "cancelled"}
    ]
    if active_tasks:
        raise api_error(409, "REQUIREMENT_HAS_ACTIVE_TASKS", "Requirement has active tasks")

    requirement = {
        **requirement,
        "status": "closed",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if not uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = record_audit_event(
        current_store,
        event_type="requirement.closed",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    save_requirement_record(current_store, requirement, audit_event=audit_event)
    return requirement
