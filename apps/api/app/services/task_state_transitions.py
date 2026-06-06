from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.services.task_access import task_allowed_roles
from app.services.task_graph_runtime import latest_graph_run, transition_latest_graph_run
from app.services.task_persistence_helpers import (
    save_review_decision_records,
    save_task_state_records,
)
from app.services.task_review_artifacts import ensure_review_decidable
from app.services.task_workflow_context import task_workflow_write_store


def reject_review_response(
    *,
    current_store: Any,
    decision_reason: str | None,
    review_id: str,
    user: dict[str, Any],
    version: int,
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    review, task = ensure_review_decidable(write_store, review_id=review_id, version=version)
    require_roles(user, task_allowed_roles(task))
    audit_start_index = len(write_store.audit_events)
    now = datetime.now(UTC).isoformat()
    review["status"] = "rejected"
    review["decision_reason"] = decision_reason
    review["decided_by"] = user["id"]
    review["decided_at"] = now
    review["updated_at"] = now
    task["status"] = "failed"
    task["updated_at"] = now
    checkpoint = transition_latest_graph_run(
        write_store,
        task=task,
        status="failed",
        current_step="failed",
        state_snapshot={
            "task_status": task["status"],
            "review_id": review_id,
            "decision_reason": decision_reason,
        },
    )
    write_store.audit(
        event_type="review.rejected",
        actor_id=user["id"],
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={"decision_reason": decision_reason},
    )
    graph_run = latest_graph_run(write_store, task)
    save_review_decision_records(
        write_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return {"review_status": review["status"], "task_status": task["status"]}


def request_more_info_review_response(
    *,
    current_store: Any,
    questions: list[str],
    review_id: str,
    user: dict[str, Any],
    version: int,
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    review, task = ensure_review_decidable(write_store, review_id=review_id, version=version)
    require_roles(user, task_allowed_roles(task))
    audit_start_index = len(write_store.audit_events)
    now = datetime.now(UTC).isoformat()
    review["status"] = "requested_more_info"
    review["questions"] = questions
    review["decided_by"] = user["id"]
    review["decided_at"] = now
    review["updated_at"] = now
    task["status"] = "waiting_more_info"
    task["updated_at"] = now
    checkpoint = transition_latest_graph_run(
        write_store,
        task=task,
        status="interrupted",
        current_step="wait_for_more_info",
        state_snapshot={
            "task_status": task["status"],
            "review_id": review_id,
            "questions": questions,
        },
    )
    write_store.audit(
        event_type="review.more_info_requested",
        actor_id=user["id"],
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={"questions": questions},
    )
    graph_run = latest_graph_run(write_store, task)
    save_review_decision_records(
        write_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return {"review_status": review["status"], "task_status": task["status"]}


def cancel_ai_task_response(
    *,
    current_store: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    task = write_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if task["status"] in {"completed", "failed", "cancelled"}:
        raise api_error(409, "TASK_STATE_INVALID", "Task cannot be cancelled from current status")
    require_roles(user, task_allowed_roles(task))
    audit_start_index = len(write_store.audit_events)
    now = datetime.now(UTC).isoformat()
    task["status"] = "cancelled"
    task["updated_at"] = now
    cancelled_reviews = []
    for review_id in task.get("review_ids", []):
        review = write_store.human_reviews.get(review_id)
        if review and review["status"] == "pending":
            review["status"] = "cancelled"
            review["version"] += 1
            review["decided_by"] = user["id"]
            review["decided_at"] = now
            review["updated_at"] = now
            cancelled_reviews.append(review)
    checkpoint = transition_latest_graph_run(
        write_store,
        task=task,
        status="cancelled",
        current_step="cancelled",
        state_snapshot={"task_status": task["status"]},
    )
    write_store.audit(
        event_type="ai_task.cancelled",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
    )
    graph_run = latest_graph_run(write_store, task)
    save_task_state_records(
        write_store,
        task=task,
        reviews=cancelled_reviews,
        graph_run=graph_run,
        checkpoint=checkpoint,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return {"id": task_id, "status": task["status"]}


def submit_more_info_response(
    *,
    answers: list[dict[str, str]],
    current_store: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    task = write_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if task["status"] != "waiting_more_info":
        raise api_error(409, "TASK_STATE_INVALID", "Task is not waiting for more info")
    require_roles(user, task_allowed_roles(task))
    audit_start_index = len(write_store.audit_events)
    now = datetime.now(UTC).isoformat()
    task.setdefault("input_json", {}).setdefault("more_info_answers", []).extend(answers)
    task["status"] = "draft"
    task["current_step"] = "draft"
    task["updated_at"] = now
    write_store.audit(
        event_type="ai_task.more_info_submitted",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
    )
    save_task_state_records(
        write_store,
        task=task,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return {"id": task_id, "status": task["status"]}
