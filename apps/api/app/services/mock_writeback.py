from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error


def writeback_idempotency_key(task_id: str) -> str:
    return f"mock_issue:{task_id}"


def completed_task_for_writeback(current_store: Any, task_id: str) -> dict[str, Any]:
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if task["status"] != "completed":
        raise api_error(409, "TASK_STATE_INVALID", "Only completed tasks can write mock issues")
    return task


def read_mock_writeback_result(current_store: Any, task_id: str) -> dict[str, Any]:
    completed_task_for_writeback(current_store, task_id)
    idempotency_key = writeback_idempotency_key(task_id)
    result = current_store.mock_writebacks.get(idempotency_key)
    if result is not None:
        return result
    return {
        "task_id": task_id,
        "status": "not_written",
        "idempotency_key": idempotency_key,
        "issues": [],
    }


def create_mock_writeback_result(
    current_store: Any,
    *,
    task_id: str,
    actor_id: str,
) -> dict[str, Any]:
    task = completed_task_for_writeback(current_store, task_id)
    idempotency_key = writeback_idempotency_key(task_id)
    result = current_store.mock_writebacks.get(idempotency_key)
    if result is not None:
        return result

    issue = {
        "id": current_store.new_id("mock_issue"),
        "title": task["title"],
        "source_task_id": task_id,
        "status": "open",
    }
    result = {
        "task_id": task_id,
        "status": "completed",
        "idempotency_key": idempotency_key,
        "issues": [issue],
    }
    current_store.mock_writebacks[idempotency_key] = result

    audit_event = record_writeback_audit_event(
        current_store,
        actor_id=actor_id,
        task_id=task_id,
        idempotency_key=idempotency_key,
    )
    save_mock_writeback_record(current_store, result, audit_event=audit_event)
    return result


def record_writeback_audit_event(
    current_store: Any,
    *,
    actor_id: str,
    task_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    if getattr(current_store, "repository", None) is None:
        return current_store.audit(
            event_type="mock_issue.written",
            actor_id=actor_id,
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload={"idempotency_key": idempotency_key},
        )
    return {
        "id": current_store.new_id("audit"),
        "event_type": "mock_issue.written",
        "actor_id": actor_id,
        "ai_task_id": task_id,
        "subject_type": "ai_task",
        "subject_id": task_id,
        "payload": {"idempotency_key": idempotency_key},
        "sequence": len(getattr(current_store, "audit_events", [])) + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }


def save_mock_writeback_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_mock_writeback_record", None)
    if callable(save_record):
        save_record(record, audit_event=audit_event)
