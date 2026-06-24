from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.services.requirements import (
    REQUIREMENT_BATCH_SCHEDULABLE_STATUSES,
    ensure_non_blank,
    generate_product_detail_design_task,
    record_audit_event,
    requirement_summary_projection,
    save_audit_event,
    save_requirement_record,
)
from app.services.version_status import (
    can_batch_advance_requirement_status,
    canonical_requirement_status,
    requires_requirement_version_for_batch_advance,
    validate_requirement_batch_advance_target,
    validate_requirement_version,
)


def batch_generate_requirement_tasks_result(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    product = current_store.products.get(payload.product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")

    batch_id = current_store.new_id("requirement_task_batch")
    now = datetime.now(UTC).isoformat()
    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_requirement_ids: set[str] = set()

    for requirement_id in payload.requirement_ids:
        if requirement_id in seen_requirement_ids:
            skipped.append(
                {
                    "code": "DUPLICATE_REQUIREMENT",
                    "id": requirement_id,
                    "message": "Requirement was already included in this batch",
                }
            )
            continue
        seen_requirement_ids.add(requirement_id)

        requirement = current_store.requirements.get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        if requirement.get("product_id") != payload.product_id:
            skipped.append(
                {
                    "code": "PRODUCT_MISMATCH",
                    "id": requirement_id,
                    "message": "Requirement belongs to another product",
                }
            )
            continue
        if canonical_requirement_status(requirement.get("status")) != "planned":
            skipped.append(
                {
                    "code": "REQUIREMENT_STATE_INVALID",
                    "id": requirement_id,
                    "message": "Only planned requirements can generate tasks",
                }
            )
            continue

        generated.append(
            generate_product_detail_design_task(
                current_store,
                audit_payload={
                    "batch_id": batch_id,
                    "operation": "batch_generate_tasks",
                    "reason": payload.reason,
                },
                now=now,
                requirement=requirement,
                requirement_id=requirement_id,
                user=user,
            )
        )

    batch_audit_event = record_audit_event(
        current_store,
        event_type="requirement.batch_tasks_generated",
        actor_id=user["id"],
        subject_type="requirement_task_batch",
        subject_id=batch_id,
        payload={
            "generated_count": len(generated),
            "generated_task_ids": [item["task_id"] for item in generated],
            "product_id": payload.product_id,
            "reason": payload.reason,
            "requirement_ids": payload.requirement_ids,
            "skipped": skipped,
            "skipped_count": len(skipped),
        },
    )
    save_audit_event(current_store, batch_audit_event)
    return {
        "batch_id": batch_id,
        "generated": generated,
        "generated_count": len(generated),
        "product_id": payload.product_id,
        "reason": payload.reason,
        "skipped": skipped,
        "skipped_count": len(skipped),
    }


def batch_assign_requirement_owner_result(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    assignee = ensure_non_blank(payload.assignee, "assignee")
    batch_id = current_store.new_id("requirement_owner_batch")
    now = datetime.now(UTC).isoformat()
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_requirement_ids: set[str] = set()

    for requirement_id in payload.requirement_ids:
        if requirement_id in seen_requirement_ids:
            skipped.append(
                {
                    "code": "DUPLICATE_REQUIREMENT",
                    "id": requirement_id,
                    "message": "Requirement was already included in this batch",
                }
            )
            continue
        seen_requirement_ids.add(requirement_id)

        requirement = current_store.requirements.get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        current_status = canonical_requirement_status(requirement.get("status"))
        if current_status in {"cancelled", "closed"}:
            skipped.append(
                {
                    "code": "REQUIREMENT_STATE_INVALID",
                    "id": requirement_id,
                    "message": "Closed or cancelled requirements cannot be assigned",
                }
            )
            continue

        previous_assignee = requirement.get("assignee")
        assigned_requirement = {
            **requirement,
            "assignee": assignee,
            "updated_at": now,
        }
        audit_event = record_audit_event(
            current_store,
            event_type="requirement.updated",
            actor_id=user["id"],
            subject_type="requirement",
            subject_id=requirement_id,
            payload={
                "assignee": assignee,
                "batch_id": batch_id,
                "from_assignee": previous_assignee,
                "operation": "batch_assign_owner",
                "reason": payload.reason,
            },
        )
        save_requirement_record(
            current_store,
            assigned_requirement,
            audit_event=audit_event,
        )
        updated.append(requirement_summary_projection(assigned_requirement, current_store))

    batch_audit_event = record_audit_event(
        current_store,
        event_type="requirement.batch_owner_assigned",
        actor_id=user["id"],
        subject_type="requirement_owner_batch",
        subject_id=batch_id,
        payload={
            "assignee": assignee,
            "reason": payload.reason,
            "requirement_ids": payload.requirement_ids,
            "skipped": skipped,
            "skipped_count": len(skipped),
            "updated_count": len(updated),
            "updated_ids": [item["id"] for item in updated],
        },
    )
    save_audit_event(current_store, batch_audit_event)
    return {
        "assignee": assignee,
        "batch_id": batch_id,
        "reason": payload.reason,
        "skipped": skipped,
        "skipped_count": len(skipped),
        "updated": updated,
        "updated_count": len(updated),
    }


def batch_schedule_requirements_result(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    product = current_store.products.get(payload.product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    validate_requirement_version(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
    )

    batch_id = current_store.new_id("requirement_batch")
    now = datetime.now(UTC).isoformat()
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_requirement_ids: set[str] = set()

    for requirement_id in payload.requirement_ids:
        if requirement_id in seen_requirement_ids:
            skipped.append(
                {
                    "code": "DUPLICATE_REQUIREMENT",
                    "id": requirement_id,
                    "message": "Requirement was already included in this batch",
                }
            )
            continue
        seen_requirement_ids.add(requirement_id)

        requirement = current_store.requirements.get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        if requirement.get("product_id") != payload.product_id:
            skipped.append(
                {
                    "code": "PRODUCT_MISMATCH",
                    "id": requirement_id,
                    "message": "Requirement belongs to another product",
                }
            )
            continue

        current_status = canonical_requirement_status(requirement.get("status"))
        if current_status not in REQUIREMENT_BATCH_SCHEDULABLE_STATUSES:
            skipped.append(
                {
                    "code": "REQUIREMENT_STATE_INVALID",
                    "id": requirement_id,
                    "message": "Only requirement pool or planned requirements can be scheduled",
                }
            )
            continue

        from_version_id = requirement.get("version_id")
        scheduled_requirement = {
            **requirement,
            "status": "planned",
            "updated_at": now,
            "version_id": payload.version_id,
        }
        audit_event = record_audit_event(
            current_store,
            event_type="requirement.updated",
            actor_id=user["id"],
            subject_type="requirement",
            subject_id=requirement_id,
            payload={
                "batch_id": batch_id,
                "from_status": current_status,
                "from_version_id": from_version_id,
                "operation": "batch_schedule",
                "reason": payload.reason,
                "to_status": "planned",
                "to_version_id": payload.version_id,
            },
        )
        save_requirement_record(
            current_store,
            scheduled_requirement,
            audit_event=audit_event,
        )
        updated.append(requirement_summary_projection(scheduled_requirement, current_store))

    batch_audit_event = record_audit_event(
        current_store,
        event_type="requirement.batch_scheduled",
        actor_id=user["id"],
        subject_type="requirement_batch",
        subject_id=batch_id,
        payload={
            "product_id": payload.product_id,
            "reason": payload.reason,
            "requirement_ids": payload.requirement_ids,
            "skipped": skipped,
            "skipped_count": len(skipped),
            "updated_count": len(updated),
            "updated_ids": [item["id"] for item in updated],
            "version_id": payload.version_id,
        },
    )
    save_audit_event(current_store, batch_audit_event)
    return {
        "batch_id": batch_id,
        "product_id": payload.product_id,
        "reason": payload.reason,
        "skipped": skipped,
        "skipped_count": len(skipped),
        "updated": updated,
        "updated_count": len(updated),
        "version_id": payload.version_id,
    }


def batch_advance_requirement_status_result(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    target_status = canonical_requirement_status(payload.target_status)
    validate_requirement_batch_advance_target(target_status)
    batch_id = current_store.new_id("requirement_status_batch")
    now = datetime.now(UTC).isoformat()
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_requirement_ids: set[str] = set()

    for requirement_id in payload.requirement_ids:
        if requirement_id in seen_requirement_ids:
            skipped.append(
                {
                    "code": "DUPLICATE_REQUIREMENT",
                    "id": requirement_id,
                    "message": "Requirement was already included in this batch",
                }
            )
            continue
        seen_requirement_ids.add(requirement_id)

        requirement = current_store.requirements.get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        current_status = canonical_requirement_status(requirement.get("status"))
        if not can_batch_advance_requirement_status(current_status, target_status):
            skipped.append(
                {
                    "code": "REQUIREMENT_STATE_INVALID",
                    "id": requirement_id,
                    "message": "Requirement cannot be advanced to target status",
                }
            )
            continue
        if (
            requires_requirement_version_for_batch_advance(target_status)
            and not requirement.get("version_id")
        ):
            skipped.append(
                {
                    "code": "REQUIREMENT_VERSION_REQUIRED",
                    "id": requirement_id,
                    "message": (
                        "Requirement must be scheduled to a version before advancing "
                        "to this status"
                    ),
                }
            )
            continue

        advanced_requirement = {
            **requirement,
            "status": target_status,
            "updated_at": now,
        }
        audit_event = record_audit_event(
            current_store,
            event_type="requirement.updated",
            actor_id=user["id"],
            subject_type="requirement",
            subject_id=requirement_id,
            payload={
                "batch_id": batch_id,
                "from_status": current_status,
                "operation": "batch_advance_status",
                "reason": payload.reason,
                "to_status": target_status,
            },
        )
        save_requirement_record(
            current_store,
            advanced_requirement,
            audit_event=audit_event,
        )
        updated.append(requirement_summary_projection(advanced_requirement, current_store))

    batch_audit_event = record_audit_event(
        current_store,
        event_type="requirement.batch_status_advanced",
        actor_id=user["id"],
        subject_type="requirement_status_batch",
        subject_id=batch_id,
        payload={
            "reason": payload.reason,
            "requirement_ids": payload.requirement_ids,
            "skipped": skipped,
            "skipped_count": len(skipped),
            "target_status": target_status,
            "updated_count": len(updated),
            "updated_ids": [item["id"] for item in updated],
        },
    )
    save_audit_event(current_store, batch_audit_event)
    return {
        "batch_id": batch_id,
        "reason": payload.reason,
        "skipped": skipped,
        "skipped_count": len(skipped),
        "target_status": target_status,
        "updated": updated,
        "updated_count": len(updated),
    }
