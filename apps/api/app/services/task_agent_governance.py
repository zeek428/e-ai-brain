from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.agent_autonomy import (
    latest_agent_loop_for_task,
    request_agent_loop_human_takeover,
)
from app.services.ai_executor_runner_constants import AI_EXECUTOR_TASK_TERMINAL_STATUSES
from app.services.ai_executor_runners import request_ai_executor_task_cancel
from app.services.task_access import require_task_permission_or_roles
from app.services.task_graph_runtime import latest_graph_run, transition_latest_graph_run
from app.services.task_persistence_helpers import save_task_state_records
from app.services.task_workflow_context import task_workflow_write_store


def _runner_task(current_store: Any, task_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_tasks = getattr(repository, "list_ai_executor_tasks", None)
    if callable(list_tasks):
        return next((item for item in list_tasks() if item.get("id") == task_id), None)
    tasks = getattr(current_store, "ai_executor_tasks", None)
    return tasks.get(task_id) if isinstance(tasks, dict) else None


def _active_runner_task_ids(loop: dict[str, Any]) -> list[str]:
    task_ids: list[str] = []
    for iteration in loop.get("iterations") or []:
        if not isinstance(iteration, dict):
            continue
        for key in ("coding_runner_task_id", "verifier_runner_task_id"):
            task_id = str(iteration.get(key) or "").strip()
            if task_id and task_id not in task_ids:
                task_ids.append(task_id)
    return task_ids


def request_agent_loop_takeover_response(
    *,
    current_store: Any,
    reason: str | None,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    task = write_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    require_task_permission_or_roles(user, task, {"task.execute"})
    loop = latest_agent_loop_for_task(
        current_store,
        product_scope_ids=None,
        task_id=task_id,
    )
    if loop is None:
        raise api_error(409, "AGENT_LOOP_NOT_ACTIVE", "Task has no active Agent loop")

    takeover_reason = str(reason or "human takeover requested").strip()
    cancelled_runner_tasks: list[dict[str, Any]] = []
    for runner_task_id in _active_runner_task_ids(loop):
        runner_task = _runner_task(current_store, runner_task_id)
        if runner_task is None or runner_task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
            continue
        cancelled_runner_tasks.append(
            request_ai_executor_task_cancel(
                current_store,
                actor_id=user["id"],
                reason=takeover_reason,
                task_id=runner_task_id,
            )
        )

    # Runner cancellation synchronizes its terminal state back to the AI task.
    # Reload before applying the takeover transition so that state cannot win last-write.
    write_store = task_workflow_write_store(current_store)
    task = write_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    updated_loop = request_agent_loop_human_takeover(
        current_store,
        actor_id=user["id"],
        reason=takeover_reason,
        task_id=task_id,
    )
    now = datetime.now(UTC).isoformat()
    review = {
        "ai_task_id": task_id,
        "content": {
            "agent_loop_run_id": updated_loop["id"],
            "cancelled_runner_task_ids": [item["id"] for item in cancelled_runner_tasks],
            "context_manifest_id": updated_loop.get("context_manifest_id"),
            "takeover_reason": takeover_reason,
        },
        "created_at": now,
        "decided_at": None,
        "decided_by": None,
        "decision_reason": None,
        "id": write_store.new_id("review"),
        "questions": [],
        "stage": "agent_loop_takeover",
        "status": "pending",
        "updated_at": now,
        "version": 1,
    }
    write_store.human_reviews[review["id"]] = review
    review_ids = list(task.get("review_ids") or [])
    review_ids.append(review["id"])
    task.update(
        {
            "current_step": "agent_loop_human_takeover",
            "review_ids": review_ids,
            "status": "waiting_review",
            "updated_at": now,
        }
    )
    checkpoint = transition_latest_graph_run(
        write_store,
        task=task,
        status="interrupted",
        current_step="agent_loop_human_takeover",
        state_snapshot={
            "agent_loop_run_id": updated_loop["id"],
            "review_id": review["id"],
            "task_status": "waiting_review",
            "takeover_reason": takeover_reason,
        },
    )
    audit_start_index = len(write_store.audit_events)
    write_store.audit(
        event_type="ai_task.agent_loop_human_takeover",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
        payload={
            "agent_loop_run_id": updated_loop["id"],
            "cancelled_runner_task_ids": [item["id"] for item in cancelled_runner_tasks],
            "reason": takeover_reason,
            "review_id": review["id"],
        },
    )
    save_task_state_records(
        write_store,
        task=task,
        reviews=[review],
        graph_run=latest_graph_run(write_store, task),
        checkpoint=checkpoint,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return {
        "agent_loop": updated_loop,
        "cancelled_runner_task_ids": [item["id"] for item in cancelled_runner_tasks],
        "current_step": task["current_step"],
        "review_id": review["id"],
        "status": task["status"],
        "task_id": task_id,
    }
