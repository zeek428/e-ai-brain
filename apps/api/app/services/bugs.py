from __future__ import annotations

import base64
import hashlib
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from app.api.deps import api_error, require_any_permission_or_roles, require_permissions
from app.core.config import get_settings
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.bug_lifecycle import (
    ensure_bug_status_transition,
    initial_bug_status,
    validate_bug_context,
    validate_bug_enums,
)
from app.services.bug_listing import bug_summary_projection
from app.services.object_storage import object_storage
from app.services.task_persistence_helpers import (
    record_audit_event as record_task_audit_event,
    save_bug_and_ai_task_records,
)
from app.services.task_start_execution import start_ai_task_response
from app.services.task_workflow_context import task_workflow_write_store

BUG_IMAGE_MIME_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
}
BUG_IMAGE_UPLOAD_SOURCES = {"clipboard", "file_picker"}
MAX_BUG_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
BUG_IMAGE_OBJECT_PREFIX = "bugs/evidence/"
BUG_FIX_TASK_TYPE = "bug_fix"


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def decode_bug_image_content(content_base64: str) -> bytes:
    try:
        content = base64.b64decode(content_base64.encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise api_error(400, "VALIDATION_ERROR", "content_base64 is invalid") from exc
    if not content:
        raise api_error(400, "VALIDATION_ERROR", "Image content is required")
    if len(content) > MAX_BUG_IMAGE_SIZE_BYTES:
        raise api_error(400, "VALIDATION_ERROR", "Image is larger than 10MB")
    return content


def normalize_bug_image_filename(filename: str | None) -> str:
    normalized = (filename or "bug-image").replace("\\", "/").split("/")[-1].strip()
    if not normalized:
        return "bug-image"
    return normalized[:160]


def safe_object_filename(filename: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip(".-")
    return sanitized or "bug-image"


def payload_updates(payload: Any) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


def require_bug_write_role(user: dict[str, Any]) -> None:
    require_any_permission_or_roles(user, {"bug.manage"}, {"product_owner", "rd_owner"})


def bug_write_store(current_store: Any) -> Any:
    return task_workflow_write_store(current_store)


def upload_bug_image_result(
    *,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_bug_write_role(user)
    mime_type = ensure_non_blank(payload.mime_type, "mime_type")
    if mime_type not in BUG_IMAGE_MIME_TYPES:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "Only PNG, JPEG, GIF, or WebP images are supported",
        )
    source = ensure_non_blank(payload.source, "source")
    if source not in BUG_IMAGE_UPLOAD_SOURCES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported image upload source")

    filename = normalize_bug_image_filename(payload.filename)
    content = decode_bug_image_content(payload.content_base64)
    digest = hashlib.sha256(content).hexdigest()
    settings = get_settings()
    storage = object_storage()
    uploaded_at = datetime.now(UTC).isoformat()
    date_path = uploaded_at[:10]
    object_key = (
        f"bugs/evidence/{user['id']}/{date_path}/{digest}/{safe_object_filename(filename)}"
    )
    stored = storage.put_bytes(
        bucket=settings.object_storage_bucket,
        content=content,
        mime_type=mime_type,
        object_key=object_key,
    )
    return {
        "id": f"bug_image_{digest[:16]}",
        "bucket": stored.bucket,
        "content_hash": digest,
        "filename": filename,
        "mime_type": mime_type,
        "object_key": stored.object_key,
        "size_bytes": stored.size_bytes,
        "source": source,
        "storage_provider": storage.provider,
        "uploaded_at": uploaded_at,
        "uploaded_by": user["id"],
    }


def _is_object_storage_missing_error(exc: Exception) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    if exc.__class__.__name__ != "S3Error":
        return False
    return getattr(exc, "code", None) in {"NoSuchBucket", "NoSuchKey", "NoSuchObject"}


def preview_bug_image_result(
    *,
    bucket: str | None,
    mime_type: str | None,
    object_key: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_permissions(user, {"bug.read"})
    normalized_bucket = ensure_non_blank(bucket, "bucket")
    normalized_object_key = ensure_non_blank(object_key, "object_key")
    normalized_mime_type = ensure_non_blank(mime_type, "mime_type")
    settings = get_settings()
    if normalized_bucket != settings.object_storage_bucket:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported image bucket")
    if normalized_mime_type not in BUG_IMAGE_MIME_TYPES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported image MIME type")
    if not normalized_object_key.startswith(BUG_IMAGE_OBJECT_PREFIX):
        raise api_error(400, "VALIDATION_ERROR", "Unsupported image object key")
    if any(part in {"", ".", ".."} for part in normalized_object_key.split("/")):
        raise api_error(400, "VALIDATION_ERROR", "Invalid image object key")

    try:
        content = object_storage().get_bytes(
            bucket=normalized_bucket,
            object_key=normalized_object_key,
        )
    except Exception as exc:
        if _is_object_storage_missing_error(exc):
            raise api_error(404, "NOT_FOUND", "Bug image not found") from exc
        raise
    return {"content": content, "mime_type": normalized_mime_type}


def record_audit_event(
    current_store: Any,
    *,
    actor_id: str,
    event_type: str,
    subject_id: str,
    subject_type: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": len(_memory_list(current_store, "audit_events")) + 1,
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
        return
    _memory_collection(current_store, "bugs")[str(record["id"])] = record
    if audit_event is not None:
        save_audit_event(current_store, audit_event)


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
        return
    bugs = _memory_collection(current_store, "bugs")
    bugs.pop(record_id, None)
    now = datetime.now(UTC).isoformat()
    for bug in bugs.values():
        if bug.get("duplicate_of_bug_id") == record_id:
            bug["duplicate_of_bug_id"] = None
            bug["updated_at"] = now
    if audit_event is not None:
        save_audit_event(current_store, audit_event)


def save_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    append_event = getattr(repository, "append_audit_event", None)
    if callable(append_event):
        append_event(audit_event)
        return
    save_events = getattr(repository, "save_audit_events", None)
    if callable(save_events):
        save_events({"audit_events": [audit_event]})
        return
    _memory_list(current_store, "audit_events").append(audit_event)


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


def bug_task_product_context(current_store: Any, bug: dict[str, Any]) -> dict[str, Any]:
    product = _read_memory_record(current_store, "products", bug["product_id"])
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    version = (
        _read_memory_record(current_store, "product_versions", bug.get("version_id"))
        if bug.get("version_id")
        else None
    )
    module = next(
        (
            item
            for item in _read_memory_collection(current_store, "product_modules").values()
            if item["product_id"] == product["id"] and item["code"] == bug.get("module_code")
        ),
        None,
    )
    repositories = [
        repository
        for repository in _read_memory_collection(
            current_store,
            "product_git_repositories",
        ).values()
        if repository["product_id"] == product["id"] and repository.get("status") == "active"
    ]
    related_systems = [
        related_system
        for related_system in _read_memory_collection(current_store, "related_systems").values()
        if related_system.get("product_id") == product["id"]
        and related_system.get("status") == "active"
    ]
    return {
        "bug": current_store.snapshot(bug),
        "module": current_store.snapshot(module) if module else None,
        "product": current_store.snapshot(product),
        "related_systems": current_store.snapshot(
            {"items": related_systems, "total": len(related_systems)}
        ),
        "repositories": current_store.snapshot({"items": repositories, "total": len(repositories)}),
        "version": current_store.snapshot(version) if version else None,
    }


def promote_bug_to_ai_task_result(
    *,
    bug_id: str,
    code_review_executor: Any | None = None,
    current_store: Any,
    opener: Any | None = None,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_bug_write_role(user)
    write_store = task_workflow_write_store(current_store)
    bug = _read_memory_record(write_store, "bugs", bug_id)
    if bug is None:
        raise api_error(404, "NOT_FOUND", "Bug not found")
    if bug.get("duplicate_of_bug_id"):
        raise api_error(409, "BUG_STATE_INVALID", "Duplicate Bug cannot be promoted")
    if bug.get("status") == "closed":
        raise api_error(409, "BUG_STATE_INVALID", "Closed Bug cannot be promoted")

    evidence = dict(bug.get("evidence") or {})
    automation = dict(evidence.get("ai_task_automation") or {})
    existing_task_id = automation.get("latest_task_id")
    existing_task = (
        _read_memory_record(write_store, "ai_tasks", existing_task_id)
        if existing_task_id
        else None
    )
    if existing_task and existing_task.get("status") not in {"cancelled", "completed", "failed"}:
        raise api_error(
            409,
            "BUG_AI_TASK_IN_PROGRESS",
            "Bug already has an active AI task",
        )

    now = datetime.now(UTC).isoformat()
    task_id = write_store.new_id("task")
    requirement = (
        _read_memory_record(write_store, "requirements", bug.get("requirement_id"))
        if bug.get("requirement_id")
        else None
    )
    title = str(getattr(payload, "title", None) or "").strip() or f"Bug 修复：{bug['title']}"
    bug_snapshot = write_store.snapshot(bug)
    task = {
        "brain_app_id": DEFAULT_BRAIN_APP_ID,
        "created_at": now,
        "created_by": user["id"],
        "current_step": "draft",
        "error_code": None,
        "error_message": None,
        "graph_run_ids": [],
        "id": task_id,
        "input_json": {
            "bug": bug_snapshot,
            "source": {"id": bug["id"], "type": "bug"},
        },
        "module_code": bug.get("module_code"),
        "output_json": None,
        "product_context": bug_task_product_context(write_store, bug),
        "product_id": bug["product_id"],
        "requirement_id": bug.get("requirement_id"),
        "requirement_snapshot": write_store.snapshot(requirement) if requirement else None,
        "review_ids": [],
        "status": "draft",
        "task_type": BUG_FIX_TASK_TYPE,
        "title": title,
        "updated_at": now,
        "version_id": bug.get("version_id"),
    }
    task_ids = [str(item) for item in automation.get("task_ids") or [] if item]
    if task_id not in task_ids:
        task_ids.append(task_id)
    evidence["ai_task_automation"] = {
        **automation,
        "latest_task_id": task_id,
        "latest_task_status": task["status"],
        "source": "bug_promote_ai_task",
        "task_ids": task_ids,
        "updated_at": now,
    }
    updated_bug = {
        **bug,
        "evidence": evidence,
        "related_task_id": bug.get("related_task_id") or task_id,
        "updated_at": now,
    }

    if not uses_repository_context(write_store):
        write_store.ai_tasks[task_id] = task
        write_store.bugs[bug["id"]] = updated_bug
    created_event = record_task_audit_event(
        write_store,
        event_type="ai_task.created",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
        payload={
            "source_bug_id": bug["id"],
            "task_type": task["task_type"],
        },
    )
    promoted_event = record_task_audit_event(
        write_store,
        event_type="bug.ai_task_promoted",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="bug",
        subject_id=bug["id"],
        payload={
            "auto_start": bool(getattr(payload, "auto_start", True)),
            "task_id": task_id,
            "task_type": task["task_type"],
        },
    )
    save_bug_and_ai_task_records(
        write_store,
        bug=updated_bug,
        task=task,
        audit_events=[created_event, promoted_event],
    )

    start_payload = None
    if getattr(payload, "auto_start", True):
        start_payload = start_ai_task_response(
            code_review_executor=code_review_executor,
            current_store=write_store,
            execution_mode=getattr(payload, "execution_mode", None),
            execution_reason=getattr(payload, "reason", None),
            opener=opener,
            task_id=task_id,
            user=user,
        )
        refreshed_store = task_workflow_write_store(write_store)
        task = refreshed_store.ai_tasks.get(task_id, task)
        updated_bug = refreshed_store.bugs.get(bug["id"], updated_bug)
        refreshed_evidence = dict(updated_bug.get("evidence") or {})
        refreshed_automation = dict(refreshed_evidence.get("ai_task_automation") or {})
        refreshed_evidence["ai_task_automation"] = {
            **refreshed_automation,
            "latest_task_status": task.get("status"),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        updated_bug = {
            **updated_bug,
            "evidence": refreshed_evidence,
            "updated_at": refreshed_evidence["ai_task_automation"]["updated_at"],
        }
        if not uses_repository_context(refreshed_store):
            refreshed_store.bugs[bug["id"]] = updated_bug
        save_bug_record(refreshed_store, updated_bug)

    return {
        "bug": write_store.snapshot(updated_bug),
        "start": start_payload,
        "task": write_store.snapshot(task),
    }


def _memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, list):
        collection = []
        setattr(current_store, collection_name, collection)
    return collection


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

        bug = _read_memory_record(current_store, "bugs", bug_id)
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
    bug = _read_memory_record(current_store, "bugs", bug_id)
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
    if _read_memory_record(current_store, "bugs", bug_id) is None:
        raise api_error(404, "NOT_FOUND", "Bug not found")
    audit_event = record_audit_event(
        current_store,
        event_type="bug.deleted",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
    )
    delete_bug_record(current_store, bug_id, audit_event=audit_event)
    return {"deleted": True, "id": bug_id}
