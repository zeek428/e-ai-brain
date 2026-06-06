from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from app.api.deps import api_error, require_roles
from app.services.bug_lifecycle import (
    ensure_bug_status_transition,
    initial_bug_status,
    validate_bug_context,
    validate_bug_enums,
)
from app.services.bug_listing import bug_summary_projection
from app.services.task_workflow_context import task_workflow_write_store


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def payload_updates(payload: Any) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


def require_bug_write_role(user: dict[str, Any]) -> None:
    require_roles(user, {"product_owner", "rd_owner"})


def bug_write_store(current_store: Any) -> Any:
    return task_workflow_write_store(current_store)


def record_audit_event(
    current_store: Any,
    *,
    actor_id: str,
    event_type: str,
    subject_id: str,
    subject_type: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not uses_repository_context(current_store):
        return current_store.audit(
            event_type=event_type,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
        )
    return {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": len(getattr(current_store, "audit_events", [])) + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }


def save_bug_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_bug_record", None)
    if callable(save_record):
        save_record(record, audit_event=audit_event)


def delete_bug_record(
    current_store: Any,
    record_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_bug_record", None)
    if callable(delete_record):
        delete_record(record_id, audit_event=audit_event)


def save_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    append_event = getattr(repository, "append_audit_event", None)
    if callable(append_event):
        append_event(audit_event)
        return
    save_events = getattr(repository, "save_audit_events", None)
    if callable(save_events):
        save_events({"audit_events": [audit_event]})


def create_bug_result(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_bug_write_role(user)
    validate_bug_enums(source=payload.source, severity=payload.severity)
    title = ensure_non_blank(payload.title, "title")
    description = ensure_non_blank(payload.description, "description")
    validate_bug_context(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
        module_code=payload.module_code,
        requirement_id=payload.requirement_id,
        related_task_id=payload.related_task_id,
        duplicate_of_bug_id=payload.duplicate_of_bug_id,
    )
    bug_id = current_store.new_id("bug")
    now = datetime.now(UTC).isoformat()
    bug = {
        "id": bug_id,
        "product_id": payload.product_id,
        "version_id": payload.version_id,
        "module_code": payload.module_code,
        "source": payload.source,
        "title": title,
        "severity": payload.severity,
        "description": description,
        "status": initial_bug_status(payload),
        "assignee": payload.assignee,
        "related_task_id": payload.related_task_id,
        "requirement_id": payload.requirement_id,
        "reproduce_steps": payload.reproduce_steps,
        "evidence": payload.evidence,
        "duplicate_of_bug_id": payload.duplicate_of_bug_id,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    if not uses_repository_context(current_store):
        current_store.bugs[bug_id] = bug
    audit_event = record_audit_event(
        current_store,
        event_type="bug.created",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
        payload={
            "severity": bug["severity"],
            "source": bug["source"],
            "status": bug["status"],
        },
    )
    save_bug_record(current_store, bug, audit_event=audit_event)
    return bug_summary_projection(bug, current_store)


def batch_update_bugs_result(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_bug_write_role(user)
    validate_bug_enums(severity=payload.severity, status=payload.status)
    update_fields: set[str] = set()
    if payload.status is not None:
        update_fields.add("status")
    if payload.severity is not None:
        update_fields.add("severity")
    if "assignee" in payload.model_fields_set:
        update_fields.add("assignee")
    if not update_fields:
        raise api_error(400, "VALIDATION_ERROR", "At least one bug update field is required")

    batch_id = current_store.new_id("bug_batch")
    now = datetime.now(UTC).isoformat()
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_bug_ids: set[str] = set()

    for bug_id in payload.bug_ids:
        if bug_id in seen_bug_ids:
            skipped.append(
                {
                    "code": "DUPLICATE_BUG",
                    "id": bug_id,
                    "message": "Bug was already included in this batch",
                }
            )
            continue
        seen_bug_ids.add(bug_id)

        bug = current_store.bugs.get(bug_id)
        if bug is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": bug_id,
                    "message": "Bug not found",
                }
            )
            continue

        updates: dict[str, Any] = {}
        if "status" in update_fields and payload.status is not None:
            try:
                ensure_bug_status_transition(bug["status"], payload.status)
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, dict) else {}
                skipped.append(
                    {
                        "code": str(detail.get("code") or "BUG_STATE_INVALID"),
                        "id": bug_id,
                        "message": str(
                            detail.get("message") or "Bug cannot move to requested status"
                        ),
                    }
                )
                continue
            updates["status"] = payload.status
        if "severity" in update_fields and payload.severity is not None:
            updates["severity"] = payload.severity
        if "assignee" in update_fields:
            updates["assignee"] = payload.assignee.strip() if payload.assignee else None

        patched_bug = {**bug, **updates, "updated_at": now}
        if not uses_repository_context(current_store):
            current_store.bugs[bug_id] = patched_bug
        audit_event = record_audit_event(
            current_store,
            event_type="bug.updated",
            actor_id=user["id"],
            subject_type="bug",
            subject_id=bug_id,
            payload={
                "batch_id": batch_id,
                "from_status": bug.get("status"),
                "operation": "batch_update",
                "reason": payload.reason,
                "to_status": patched_bug.get("status"),
                "updated_fields": sorted(updates.keys()),
            },
        )
        save_bug_record(current_store, patched_bug, audit_event=audit_event)
        updated.append(bug_summary_projection(patched_bug, current_store))

    batch_audit_event = record_audit_event(
        current_store,
        event_type="bug.batch_updated",
        actor_id=user["id"],
        subject_type="bug_batch",
        subject_id=batch_id,
        payload={
            "bug_ids": payload.bug_ids,
            "reason": payload.reason,
            "skipped": skipped,
            "skipped_count": len(skipped),
            "updated_count": len(updated),
            "updated_fields": sorted(update_fields),
            "updated_ids": [item["id"] for item in updated],
        },
    )
    save_audit_event(current_store, batch_audit_event)
    return {
        "batch_id": batch_id,
        "reason": payload.reason,
        "skipped": skipped,
        "skipped_count": len(skipped),
        "updated": updated,
        "updated_count": len(updated),
    }


def patch_bug_result(
    *,
    bug_id: str,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_bug_write_role(user)
    bug = current_store.bugs.get(bug_id)
    if bug is None:
        raise api_error(404, "NOT_FOUND", "Bug not found")
    updates = payload_updates(payload)
    validate_bug_enums(severity=updates.get("severity"), status=updates.get("status"))
    if "title" in updates:
        updates["title"] = ensure_non_blank(updates["title"], "title")
    if "description" in updates:
        updates["description"] = ensure_non_blank(updates["description"], "description")
    duplicate_of_bug_id = updates.get("duplicate_of_bug_id")
    if duplicate_of_bug_id is not None:
        validate_bug_context(
            current_store,
            product_id=bug["product_id"],
            duplicate_of_bug_id=duplicate_of_bug_id,
            bug_id=bug_id,
        )
        updates["status"] = "closed"
    next_status = updates.get("status")
    if next_status is not None:
        ensure_bug_status_transition(bug["status"], next_status)
    bug = {**bug, **updates}
    bug["updated_at"] = datetime.now(UTC).isoformat()
    if not uses_repository_context(current_store):
        current_store.bugs[bug_id] = bug
    audit_event = record_audit_event(
        current_store,
        event_type="bug.updated",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
        payload={
            "status": bug["status"],
            "updated_fields": sorted(updates.keys()),
        },
    )
    save_bug_record(current_store, bug, audit_event=audit_event)
    return bug_summary_projection(bug, current_store)


def delete_bug_result(
    *,
    bug_id: str,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_bug_write_role(user)
    if bug_id not in current_store.bugs:
        raise api_error(404, "NOT_FOUND", "Bug not found")
    if not uses_repository_context(current_store):
        del current_store.bugs[bug_id]
    now = datetime.now(UTC).isoformat()
    if not uses_repository_context(current_store):
        for bug in current_store.bugs.values():
            if bug.get("duplicate_of_bug_id") == bug_id:
                bug["duplicate_of_bug_id"] = None
                bug["updated_at"] = now
    audit_event = record_audit_event(
        current_store,
        event_type="bug.deleted",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
    )
    delete_bug_record(current_store, bug_id, audit_event=audit_event)
    return {"deleted": True, "id": bug_id}
