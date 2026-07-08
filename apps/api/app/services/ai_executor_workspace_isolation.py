from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.api.deps import api_error
from app.services.ai_executor_runners import _authenticated_runner
from app.services.operational_records import record_audit_event

WORKSPACE_ISOLATION_DECISIONS = {"discard", "merge"}
WORKSPACE_ISOLATION_DECISION_STATUSES = {"completed", "failed"}


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    if not callable(getattr(repository, "list_ai_executor_tasks", None)):
        return None
    if not callable(getattr(repository, "save_ai_executor_task_record", None)):
        return None
    return repository


def _runner_tasks_for_ai_task(current_store: Any, ai_task_id: str) -> list[dict[str, Any]]:
    repository = _repository(current_store)
    if repository is not None:
        return list(
            repository.list_ai_executor_tasks(
                ai_task_id=ai_task_id,
                product_scope_ids=None,
                runner_id=None,
                scheduled_job_run_id=None,
                status=None,
            )
        )
    collection = getattr(current_store, "ai_executor_tasks", {})
    if not isinstance(collection, dict):
        return []
    return [dict(task) for task in collection.values() if task.get("ai_task_id") == ai_task_id]


def _runner_task_by_id(
    current_store: Any,
    *,
    runner_id: str,
    task_id: str,
) -> dict[str, Any] | None:
    repository = _repository(current_store)
    if repository is not None:
        for task in repository.list_ai_executor_tasks(
            ai_task_id=None,
            product_scope_ids=None,
            runner_id=runner_id,
            scheduled_job_run_id=None,
            status=None,
        ):
            if task.get("id") == task_id:
                return dict(task)
        return None
    collection = getattr(current_store, "ai_executor_tasks", {})
    if not isinstance(collection, dict):
        return None
    task = collection.get(task_id)
    if task and task.get("runner_id") == runner_id:
        return dict(task)
    return None


def _persist_runner_task(
    current_store: Any,
    runner_task: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _repository(current_store)
    if repository is not None:
        repository.save_ai_executor_task_record(runner_task, audit_event=audit_event)
        return
    collection = getattr(current_store, "ai_executor_tasks", None)
    if isinstance(collection, dict):
        collection[runner_task["id"]] = runner_task


def _workspace_isolation(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    isolation = value.get("workspace_isolation")
    return dict(isolation) if isinstance(isolation, dict) else None


def _merge_workspace_isolation_decision(
    isolation: dict[str, Any],
    *,
    action: str,
    decided_by: str,
    reason: str | None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        **isolation,
        "decision": {
            "action": action,
            "decided_at": now,
            "decided_by": decided_by,
            "reason": reason,
            "status": "requested",
        },
        "status": f"{action}_requested",
        "updated_at": now,
    }


def mark_ai_executor_workspace_isolation_decision(
    current_store: Any,
    *,
    action: str,
    decided_by: str,
    reason: str | None = None,
    task: dict[str, Any],
) -> dict[str, Any] | None:
    if action not in WORKSPACE_ISOLATION_DECISIONS:
        raise ValueError(f"Unsupported workspace isolation decision: {action}")
    ai_task_id = str(task.get("id") or "")
    if not ai_task_id:
        return None
    output_json = task.get("output_json") if isinstance(task.get("output_json"), dict) else {}
    output_result = output_json.get("result") if isinstance(output_json.get("result"), dict) else {}
    output_isolation = _workspace_isolation(output_result)
    runner_task_id = (
        (output_json.get("executor") or {}).get("runner_task_id")
        if isinstance(output_json.get("executor"), dict)
        else None
    )
    runner_tasks = _runner_tasks_for_ai_task(current_store, ai_task_id)
    if runner_task_id:
        runner_tasks = [
            runner_task for runner_task in runner_tasks if runner_task.get("id") == runner_task_id
        ]
    for runner_task in runner_tasks:
        result_json = dict(runner_task.get("result_json") or {})
        isolation = _workspace_isolation(result_json) or output_isolation
        if not isolation:
            continue
        isolation = _merge_workspace_isolation_decision(
            isolation,
            action=action,
            decided_by=decided_by,
            reason=reason,
        )
        runner_task = {
            **runner_task,
            "result_json": {
                **result_json,
                "workspace_isolation": isolation,
            },
            "updated_at": datetime.now(UTC).isoformat(),
        }
        audit_event = record_audit_event(
            current_store,
            event_type=f"ai_executor_workspace.{action}_requested",
            actor_id=decided_by,
            subject_type="ai_executor_task",
            subject_id=str(runner_task["id"]),
            payload={
                "action": action,
                "ai_task_id": ai_task_id,
                "runner_id": runner_task.get("runner_id"),
                "worktree_path": isolation.get("worktree_path"),
                "workspace_root": isolation.get("base_workspace_root"),
            },
        )
        _persist_runner_task(current_store, runner_task, audit_event=audit_event)
        return isolation
    return None


def complete_ai_executor_workspace_isolation_decision(
    current_store: Any,
    *,
    action: str,
    message: str | None,
    request: Request,
    runner_id: str,
    status: str,
    task_id: str,
) -> dict[str, Any]:
    if action not in WORKSPACE_ISOLATION_DECISIONS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported workspace isolation action")
    if status not in WORKSPACE_ISOLATION_DECISION_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported workspace isolation status")
    _authenticated_runner(current_store, request=request, runner_id=runner_id)
    runner_task = _runner_task_by_id(current_store, runner_id=runner_id, task_id=task_id)
    if runner_task is None:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    result_json = dict(runner_task.get("result_json") or {})
    isolation = _workspace_isolation(result_json)
    if isolation is None:
        raise api_error(409, "WORKSPACE_ISOLATION_NOT_FOUND", "Task has no workspace isolation")
    decision = dict(isolation.get("decision") or {})
    if decision.get("action") != action:
        raise api_error(
            409,
            "WORKSPACE_ISOLATION_DECISION_MISMATCH",
            "Workspace decision action mismatch",
        )
    now = datetime.now(UTC).isoformat()
    decision = {
        **decision,
        "completed_at": now if status == "completed" else None,
        "failed_at": now if status == "failed" else None,
        "message": message,
        "status": status,
    }
    isolation = {
        **isolation,
        "decision": decision,
        "status": (
            "merged"
            if action == "merge" and status == "completed"
            else "discarded"
            if action == "discard" and status == "completed"
            else f"{action}_failed"
        ),
        "updated_at": now,
    }
    runner_task = {
        **runner_task,
        "result_json": {
            **result_json,
            "workspace_isolation": isolation,
        },
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type=f"ai_executor_workspace.{action}_{status}",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={
            "action": action,
            "message": message,
            "status": status,
            "worktree_path": isolation.get("worktree_path"),
            "workspace_root": isolation.get("base_workspace_root"),
        },
    )
    _persist_runner_task(current_store, runner_task, audit_event=audit_event)
    return {"task_id": task_id, "workspace_isolation": isolation}
