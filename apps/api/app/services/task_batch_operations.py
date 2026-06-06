from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from app.api.deps import require_roles
from app.services.task_access import task_allowed_roles
from app.services.task_graph_runtime import latest_graph_run, transition_latest_graph_run
from app.services.task_persistence_helpers import (
    record_audit_event,
    save_audit_event,
    save_task_state_records,
)
from app.services.task_start_execution import (
    RETRYABLE_TASK_FAILURE_STEPS,
    start_ai_task_response,
)
from app.services.task_workflow_context import task_workflow_write_store


def batch_cancel_ai_tasks_response(
    *,
    current_store: Any,
    reason: str | None,
    task_ids: list[str],
    user: dict[str, Any],
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    batch_id = write_store.new_id("ai_task_cancel_batch")
    updated: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    seen_task_ids: set[str] = set()

    for task_id in task_ids:
        if task_id in seen_task_ids:
            skipped.append(
                {
                    "code": "DUPLICATE_TASK",
                    "id": task_id,
                    "message": "Task was already included in this batch",
                }
            )
            continue
        seen_task_ids.add(task_id)

        task = write_store.ai_tasks.get(task_id)
        if task is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": task_id,
                    "message": "AI task not found",
                }
            )
            continue
        if task["status"] in {"completed", "failed", "cancelled"}:
            skipped.append(
                {
                    "code": "TASK_STATE_INVALID",
                    "id": task_id,
                    "message": "Task cannot be cancelled from current status",
                }
            )
            continue

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
            payload={
                "batch_id": batch_id,
                "operation": "batch_cancel",
                "reason": reason,
            },
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
        updated.append({"id": task_id, "status": task["status"]})

    batch_audit_event = record_audit_event(
        write_store,
        event_type="ai_task.batch_cancelled",
        actor_id=user["id"],
        subject_type="ai_task_cancel_batch",
        subject_id=batch_id,
        payload={
            "reason": reason,
            "skipped": skipped,
            "skipped_count": len(skipped),
            "task_ids": task_ids,
            "updated_count": len(updated),
            "updated_ids": [item["id"] for item in updated],
        },
    )
    save_audit_event(write_store, batch_audit_event)
    return {
        "batch_id": batch_id,
        "reason": reason,
        "skipped": skipped,
        "skipped_count": len(skipped),
        "updated": updated,
        "updated_count": len(updated),
    }


def http_exception_detail(exc: HTTPException) -> tuple[str, str]:
    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code") or "API_ERROR")
        message = str(exc.detail.get("message") or code)
        return code, message
    return "API_ERROR", str(exc.detail or "API request failed")


def batch_retry_ai_tasks_response(
    *,
    code_review_executor: Any | None = None,
    current_store: Any,
    opener: Any | None = None,
    reason: str | None,
    task_ids: list[str],
    user: dict[str, Any],
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    batch_id = write_store.new_id("ai_task_retry_batch")
    retried: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    updated: list[dict[str, str]] = []
    seen_task_ids: set[str] = set()

    for task_id in task_ids:
        if task_id in seen_task_ids:
            skipped.append(
                {
                    "code": "DUPLICATE_TASK",
                    "id": task_id,
                    "message": "Task was already included in this batch",
                }
            )
            continue
        seen_task_ids.add(task_id)

        task = write_store.ai_tasks.get(task_id)
        if task is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": task_id,
                    "message": "AI task not found",
                }
            )
            continue
        if (
            task.get("status") != "failed"
            or task.get("current_step") not in RETRYABLE_TASK_FAILURE_STEPS
        ):
            skipped.append(
                {
                    "code": "TASK_STATE_INVALID",
                    "id": task_id,
                    "message": "Task cannot be retried from current status",
                }
            )
            continue

        try:
            result = start_ai_task_response(
                code_review_executor=code_review_executor,
                current_store=write_store,
                opener=opener,
                task_id=task_id,
                user=user,
            )
        except HTTPException as exc:
            code, message = http_exception_detail(exc)
            refreshed_task = write_store.ai_tasks.get(task_id, task)
            if code in {
                "CODE_REVIEW_EXECUTOR_FAILED",
                "MODEL_GATEWAY_CONFIG_INVALID",
                "MODEL_GATEWAY_FAILED",
            }:
                retried.append(
                    {
                        "current_step": refreshed_task.get("current_step"),
                        "error_code": code,
                        "error_message": message,
                        "id": task_id,
                        "status": refreshed_task.get("status", "failed"),
                    }
                )
                continue
            raise

        updated_item = {
            "current_step": str(result.get("current_step") or ""),
            "id": task_id,
            "review_id": str(result.get("review_id") or ""),
            "status": str(result.get("status") or "waiting_review"),
        }
        updated.append(updated_item)
        retried.append(updated_item)

    batch_audit_event = record_audit_event(
        write_store,
        event_type="ai_task.batch_retried",
        actor_id=user["id"],
        subject_type="ai_task_retry_batch",
        subject_id=batch_id,
        payload={
            "reason": reason,
            "retried_count": len(retried),
            "retried_ids": [item["id"] for item in retried],
            "skipped": skipped,
            "skipped_count": len(skipped),
            "task_ids": task_ids,
            "updated_count": len(updated),
            "updated_ids": [item["id"] for item in updated],
        },
    )
    save_audit_event(write_store, batch_audit_event)
    return {
        "batch_id": batch_id,
        "reason": reason,
        "retried": retried,
        "retried_count": len(retried),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "updated": updated,
        "updated_count": len(updated),
    }
