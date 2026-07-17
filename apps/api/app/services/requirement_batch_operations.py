from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.rd_requirement_entry_adapters import raise_legacy_rd_entrypoint_required
from app.services.requirement_iteration_planning import validate_manual_iteration_assignment
from app.services.requirements import (
    REQUIREMENT_BATCH_SCHEDULABLE_STATUSES,
    ensure_non_blank,
    ensure_requirement_product_scope,
    generate_product_detail_design_task,
    record_audit_event,
    requirement_summary_projection,
    save_audit_event,
    save_requirement_record,
)
from app.services.version_status import (
    canonical_requirement_status,
    validate_requirement_version,
)


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _has_active_collaboration_run(current_store: Any, requirement_id: str) -> bool:
    """Prevent a legacy batch close from bypassing a v2 work-item decision."""
    terminal_statuses = {"cancelled", "completed", "failed"}
    runs = _read_memory_dict(current_store, "rd_collaboration_runs")
    scope_by_run: dict[str, set[str]] = {}
    for scope in _read_memory_dict(
        current_store,
        "rd_collaboration_run_requirements",
    ).values():
        run_id = str(scope.get("collaboration_run_id") or "")
        scoped_requirement_id = str(scope.get("requirement_id") or "")
        if run_id and scoped_requirement_id:
            scope_by_run.setdefault(run_id, set()).add(scoped_requirement_id)
    for run in runs.values():
        if str(run.get("status") or "") in terminal_statuses:
            continue
        run_requirement_ids = {
            str(value)
            for value in run.get("requirement_ids", [])
            if value is not None
        }
        run_requirement_ids.update(scope_by_run.get(str(run.get("id") or ""), set()))
        if (
            str(run.get("requirement_id") or "") == requirement_id
            or requirement_id in run_requirement_ids
        ):
            return True
    return False


def _assign_requirement_to_planning_version(
    current_store: Any,
    *,
    requirement: dict[str, Any],
    target_version: dict[str, Any],
    now: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Persist requirement membership and the corresponding scope version together."""
    if (
        requirement.get("version_id") == target_version["id"]
        and requirement.get("status") == "planned"
    ):
        return requirement, target_version
    repository = getattr(current_store, "repository", None)
    assign = getattr(repository, "assign_requirement_to_version_and_increment_scope", None)
    if callable(assign):
        assigned = assign(
            requirement_id=requirement["id"],
            product_version_id=target_version["id"],
            expected_scope_version=int(target_version.get("scope_version") or 1),
        )
        return assigned["requirement"], assigned

    scheduled_requirement = {
        **requirement,
        "status": "planned",
        "updated_at": now,
        "version_id": target_version["id"],
    }
    updated_version = {
        **target_version,
        "scope_version": int(target_version.get("scope_version") or 1) + 1,
        "updated_at": now,
    }
    _read_memory_dict(current_store, "product_versions")[updated_version["id"]] = updated_version
    return scheduled_requirement, updated_version


def batch_generate_requirement_tasks_result(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    raise_legacy_rd_entrypoint_required(entrypoint="requirements.batch_generate_tasks")
    require_any_permission_or_roles(
        user,
        {"requirement.task_generate", "task.create"},
        {"product_owner", "rd_owner"},
    )
    product = _read_memory_dict(current_store, "products").get(payload.product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    ensure_requirement_product_scope(user, payload.product_id)
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

        requirement = _read_memory_dict(current_store, "requirements").get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        try:
            ensure_requirement_product_scope(user, requirement.get("product_id"))
        except HTTPException:
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
    require_any_permission_or_roles(
        user,
        {"requirement.create"},
        {"product_owner", "rd_owner"},
    )
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

        requirement = _read_memory_dict(current_store, "requirements").get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        try:
            ensure_requirement_product_scope(user, requirement.get("product_id"))
        except HTTPException:
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
    require_any_permission_or_roles(
        user,
        {"requirement.create"},
        {"product_owner", "rd_owner"},
    )
    product = _read_memory_dict(current_store, "products").get(payload.product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    ensure_requirement_product_scope(user, payload.product_id)
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    target_version = validate_requirement_version(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
    )
    if target_version is None or target_version.get("status") != "planning":
        raise api_error(
            400,
            "PRODUCT_VERSION_NOT_SCHEDULABLE",
            "Manual scheduling only accepts planning versions",
        )

    batch_id = current_store.new_id("requirement_batch")
    now = datetime.now(UTC).isoformat()
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_requirement_ids: set[str] = set()
    pending_repository_schedule: list[tuple[dict[str, Any], str, str | None]] = []
    repository = getattr(current_store, "repository", None)
    schedule_atomically = getattr(
        repository, "batch_schedule_requirements_into_planning_version", None
    )

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

        requirement = _read_memory_dict(current_store, "requirements").get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        try:
            ensure_requirement_product_scope(user, requirement.get("product_id"))
        except HTTPException:
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

        grouping_check = validate_manual_iteration_assignment(
            current_store,
            requirement_id=requirement_id,
            version_id=payload.version_id,
        )
        if not grouping_check["hard_eligible"]:
            reason = str(grouping_check["reasons"][0])
            skipped.append(
                {
                    "code": "ITERATION_CONSTRAINT_UNSATISFIED",
                    "id": requirement_id,
                    "message": f"Target planning version is not compatible: {reason}",
                }
            )
            continue

        from_version_id = requirement.get("version_id")
        if callable(schedule_atomically):
            pending_repository_schedule.append((requirement, current_status, from_version_id))
            continue
        scheduled_requirement, target_version = _assign_requirement_to_planning_version(
            current_store,
            requirement=requirement,
            target_version=target_version,
            now=now,
        )
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

    if pending_repository_schedule:
        requirement_audits = [
            record_audit_event(
                current_store,
                event_type="requirement.updated",
                actor_id=user["id"],
                subject_type="requirement",
                subject_id=requirement["id"],
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
            for requirement, current_status, from_version_id in pending_repository_schedule
        ]
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
                "updated_count": len(pending_repository_schedule),
                "updated_ids": [item[0]["id"] for item in pending_repository_schedule],
                "version_id": payload.version_id,
            },
        )
        saved = schedule_atomically(
            product_id=payload.product_id,
            product_version_id=payload.version_id,
            requirement_ids=[item[0]["id"] for item in pending_repository_schedule],
            audit_events=[*requirement_audits, batch_audit_event],
        )
        target_version = saved["version"]
        saved_by_id = {item["id"]: item for item in saved["requirements"]}
        updated.extend(
            requirement_summary_projection(saved_by_id[requirement["id"]], current_store)
            for requirement, _, _ in pending_repository_schedule
            if requirement["id"] in saved_by_id
        )
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
    require_any_permission_or_roles(
        user,
        {"requirement.create"},
        {"product_owner", "rd_owner"},
    )
    target_status = canonical_requirement_status(payload.target_status)
    if target_status not in {"cancelled", "closed"}:
        raise_legacy_rd_entrypoint_required(
            entrypoint="requirements.batch_advance_status",
        )
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

        requirement = _read_memory_dict(current_store, "requirements").get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        try:
            ensure_requirement_product_scope(user, requirement.get("product_id"))
        except HTTPException:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        current_status = canonical_requirement_status(requirement.get("status"))
        if _has_active_collaboration_run(current_store, requirement_id):
            skipped.append(
                {
                    "code": "RD_COLLABORATION_REQUIRED",
                    "id": requirement_id,
                    "message": "Active v2 collaboration must be cancelled through its work item",
                }
            )
            continue
        if current_status in {"cancelled", "closed"} or current_status == target_status:
            skipped.append(
                {
                    "code": "REQUIREMENT_STATE_INVALID",
                    "id": requirement_id,
                    "message": "Requirement is already in a terminal status",
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
            event_type=f"requirement.batch_{target_status}",
            actor_id=user["id"],
            subject_type="requirement",
            subject_id=requirement_id,
            payload={
                "batch_id": batch_id,
                "from_status": current_status,
                "operation": f"batch_{target_status}",
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
        event_type=f"requirement.batch_{target_status}",
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
