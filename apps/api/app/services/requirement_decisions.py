from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.requirements import (
    REQUIREMENT_CLOSABLE_STATUSES,
    ensure_requirement_product_scope,
    record_audit_event,
    save_requirement_record,
)
from app.services.version_status import canonical_requirement_status


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _requirement_has_open_assessment(current_store: Any, requirement_id: str) -> bool:
    repository = getattr(current_store, "repository", None)
    list_assessments = getattr(repository, "list_requirement_assessments", None)
    if callable(list_assessments):
        assessments = list_assessments(requirement_id)
    else:
        assessments = [
            item
            for item in _read_memory_dict(current_store, "requirement_assessments").values()
            if item.get("requirement_id") == requirement_id
        ]
    return any(
        item.get("status")
        in {"draft", "evaluating", "waiting_human", "needs_info", "rework_required"}
        for item in assessments
    )


def approve_requirement_result(
    *,
    current_store: Any,
    payload: Any,
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"requirement.approve"}, {"product_owner", "rd_owner"})
    requirements = _read_memory_dict(current_store, "requirements")
    requirement = requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    ensure_requirement_product_scope(user, requirement.get("product_id"))
    if _requirement_has_open_assessment(current_store, requirement_id):
        raise api_error(
            409,
            "REQUIREMENT_ASSESSMENT_REQUIRED",
            "Complete the requirement assessment instead of using standalone approval",
        )
    if canonical_requirement_status(requirement.get("status")) != "submitted":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not pending approval")

    requirement = {
        **requirement,
        "approval_comment": payload.comment,
        "status": "planned" if requirement.get("version_id") else "approved",
        "updated_at": datetime.now(UTC).isoformat(),
    }
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
    require_any_permission_or_roles(user, {"requirement.approve"}, {"product_owner"})
    requirements = _read_memory_dict(current_store, "requirements")
    requirement = requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    ensure_requirement_product_scope(user, requirement.get("product_id"))
    if _requirement_has_open_assessment(current_store, requirement_id):
        raise api_error(
            409,
            "REQUIREMENT_ASSESSMENT_REQUIRED",
            "Complete the requirement assessment instead of using standalone rejection",
        )
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
    require_any_permission_or_roles(
        user,
        {"requirement.approve", "requirement.create"},
        {"product_owner", "rd_owner"},
    )
    requirements = _read_memory_dict(current_store, "requirements")
    ai_tasks = _read_memory_dict(current_store, "ai_tasks")
    requirement = requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    ensure_requirement_product_scope(user, requirement.get("product_id"))
    if canonical_requirement_status(requirement.get("status")) not in REQUIREMENT_CLOSABLE_STATUSES:
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement cannot be closed")

    active_tasks = [
        ai_tasks[task_id]
        for task_id in requirement.get("task_ids", [])
        if ai_tasks[task_id]["status"] not in {"completed", "failed", "cancelled"}
    ]
    if active_tasks:
        raise api_error(409, "REQUIREMENT_HAS_ACTIVE_TASKS", "Requirement has active tasks")

    requirement = {
        **requirement,
        "status": "closed",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    audit_event = record_audit_event(
        current_store,
        event_type="requirement.closed",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    save_requirement_record(current_store, requirement, audit_event=audit_event)
    return requirement
