from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.task_persistence_helpers import (
    record_audit_event,
    save_bug_and_ai_task_records,
    uses_repository_context,
)
from app.services.task_start_execution import start_ai_task_response
from app.services.task_workflow_context import task_workflow_write_store


def requests_legacy_bug_task(payload: Any) -> bool:
    """Recognize the explicit, pre-v2 immediate Bug-to-task API contract."""
    return bool(getattr(payload, "auto_start", False)) and "auto_start" in getattr(
        payload,
        "model_fields_set",
        set(),
    )


def _read_record(current_store: Any, collection_name: str, record_id: Any) -> dict[str, Any] | None:
    if record_id is None:
        return None
    records = getattr(current_store, collection_name, None)
    if not isinstance(records, dict):
        return None
    record = records.get(str(record_id))
    return record if isinstance(record, dict) else None


def _save_bug_record(current_store: Any, record: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_bug_record", None)
    if callable(save_record):
        save_record(record)
        return
    bugs = getattr(current_store, "bugs", None)
    if isinstance(bugs, dict):
        bugs[str(record["id"])] = record


def promote_legacy_bug_to_ai_task(
    *,
    bug: dict[str, Any],
    code_review_executor: Any | None,
    current_store: Any,
    opener: Any | None,
    payload: Any,
    product_context: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    """Adapt an explicit legacy Bug→AI-task request without entering v2 flow."""
    write_store = task_workflow_write_store(current_store)
    evidence = dict(bug.get("evidence") or {})
    automation = dict(evidence.get("ai_task_automation") or {})
    existing_task_id = automation.get("latest_task_id")
    existing_task = _read_record(write_store, "ai_tasks", existing_task_id)
    if existing_task and existing_task.get("status") not in {"cancelled", "completed", "failed"}:
        raise api_error(
            409,
            "BUG_AI_TASK_IN_PROGRESS",
            "Bug already has an active AI task",
        )

    now = datetime.now(UTC).isoformat()
    task_id = write_store.new_id("task")
    requirement = _read_record(write_store, "requirements", bug.get("requirement_id"))
    title = str(getattr(payload, "title", None) or "").strip() or f"Bug 修复：{bug['title']}"
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
            "bug": write_store.snapshot(bug),
            "source": {"id": bug["id"], "type": "bug"},
        },
        "module_code": bug.get("module_code"),
        "output_json": None,
        "product_context": product_context,
        "product_id": bug["product_id"],
        "requirement_id": bug.get("requirement_id"),
        "requirement_snapshot": write_store.snapshot(requirement) if requirement else None,
        "review_ids": [],
        "status": "draft",
        "task_type": "bug_fix",
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
    created_event = record_audit_event(
        write_store,
        event_type="ai_task.created",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
        payload={"source_bug_id": bug["id"], "task_type": task["task_type"]},
    )
    promoted_event = record_audit_event(
        write_store,
        event_type="bug.ai_task_promoted",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="bug",
        subject_id=bug["id"],
        payload={"auto_start": True, "task_id": task_id, "task_type": task["task_type"]},
    )
    save_bug_and_ai_task_records(
        write_store,
        bug=updated_bug,
        task=task,
        audit_events=[created_event, promoted_event],
    )

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
    _save_bug_record(refreshed_store, updated_bug)

    return {
        "bug": write_store.snapshot(updated_bug),
        "start": start_payload,
        "task": write_store.snapshot(task),
    }
