from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.mock_writeback import writeback_idempotency_key
from app.services.task_access import can_read_task, task_read_scope
from app.services.task_contexts import public_product_context
from app.services.task_graph_runtime import graph_runs_for_task
from app.services.task_workflow_context import task_workflow_read_store


def pending_review_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    list_pending_reviews = getattr(repository, "list_pending_review_summaries", None)
    if callable(list_pending_reviews):
        return repository
    return None


def task_detail_projection(current_store: Any, task: dict[str, Any]) -> dict[str, Any]:
    detail = current_store.snapshot(task)
    detail["product_context"] = public_product_context(task.get("product_context"))
    reviews = [
        current_store.human_reviews[review_id]
        for review_id in task.get("review_ids", [])
        if review_id in current_store.human_reviews
    ]
    pending_review = next(
        (review for review in reviews if review["status"] == "pending"),
        None,
    )
    graph_runs = graph_runs_for_task(current_store, task["id"])
    detail["input"] = {
        "task_type": task["task_type"],
        "brain_app_id": task.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "requirement_id": task.get("requirement_id"),
        "requirement_snapshot": task.get("requirement_snapshot"),
        "product_context": public_product_context(task.get("product_context")),
        **task.get("input_json", {}),
    }
    detail["output"] = task.get("output_json")
    detail["current_step"] = task.get("current_step")
    detail["pending_review"] = current_store.snapshot(pending_review) if pending_review else None
    detail["reviews"] = current_store.snapshot({"items": reviews, "total": len(reviews)})
    detail["graph_runs"] = current_store.snapshot(graph_runs)
    detail["knowledge_deposits"] = {
        "items": [
            deposit
            for deposit in current_store.knowledge_deposits.values()
            if deposit["ai_task_id"] == task["id"]
        ]
    }
    writeback = current_store.mock_writebacks.get(writeback_idempotency_key(task["id"]))
    detail["mock_issues"] = {
        "status": writeback["status"] if writeback else "not_written",
        "items": current_store.snapshot(writeback["issues"]) if writeback else [],
    }
    return detail


def get_ai_task_response(
    *,
    current_store: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    read_store = task_workflow_read_store(current_store)
    task = read_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if not can_read_task(user, task):
        raise api_error(403, "FORBIDDEN", "Insufficient role for this AI task")
    return task_detail_projection(read_store, task)


def list_graph_runs_response(
    *,
    ai_task_id: str | None,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    read_store = task_workflow_read_store(current_store)
    items = list(read_store.graph_runs.values())
    if ai_task_id:
        task = read_store.ai_tasks.get(ai_task_id)
        if task is None:
            raise api_error(404, "NOT_FOUND", "AI task not found")
        if not can_read_task(user, task):
            raise api_error(403, "FORBIDDEN", "Insufficient role for this AI task")
        items = [item for item in items if item["ai_task_id"] == ai_task_id]
    else:
        items = [
            item
            for item in items
            if (task := read_store.ai_tasks.get(item["ai_task_id"])) is not None
            and can_read_task(user, task)
        ]
    items.sort(key=lambda item: item["started_at"], reverse=True)
    return {"items": items, "total": len(items)}


def pending_reviews_response(
    *,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    repository = pending_review_query_repository(current_store)
    if repository is not None:
        items = repository.list_pending_review_summaries(read_scope=task_read_scope(user))
        return {"items": items, "total": len(items)}
    read_store = task_workflow_read_store(current_store)
    items = [
        review
        for review in read_store.human_reviews.values()
        if review["status"] == "pending"
        and (task := read_store.ai_tasks.get(review["ai_task_id"])) is not None
        and can_read_task(user, task)
    ]
    return {"items": items, "total": len(items)}


def get_review_response(
    *,
    current_store: Any,
    review_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    read_store = task_workflow_read_store(current_store)
    review = read_store.human_reviews.get(review_id)
    if review is None:
        raise api_error(404, "NOT_FOUND", "Review not found")
    task = read_store.ai_tasks.get(review["ai_task_id"])
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if not can_read_task(user, task):
        raise api_error(403, "FORBIDDEN", "Insufficient role for this AI task")
    return {
        **read_store.snapshot(review),
        "task": read_store.snapshot(task),
    }
