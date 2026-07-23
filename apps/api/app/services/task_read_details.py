from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.core.listing import add_list_observability, ensure_list_enum, sort_list_items
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.agent_autonomy import latest_agent_loop_for_task
from app.services.execution_context_manifests import execution_context_manifest_for_task
from app.services.mock_writeback import writeback_idempotency_key
from app.services.product_scope import product_scope_filter
from app.services.quality_gates import latest_quality_gate_for_task
from app.services.task_access import can_read_task, task_read_scope
from app.services.task_contexts import public_product_context
from app.services.task_graph_runtime import graph_runs_for_task
from app.services.task_output_summary import (
    readable_runner_task_output_summary,
    readable_task_output_summary,
)
from app.services.task_workflow_context import task_workflow_read_store

PENDING_REVIEW_SORT_FIELDS = {
    "ai_task_id",
    "created_at",
    "id",
    "stage",
    "status",
    "updated_at",
}


def pending_review_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    list_pending_reviews = getattr(repository, "list_pending_review_summaries", None)
    if callable(list_pending_reviews):
        return repository
    return None


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _task_summary_uses_raw_runner_preview(task: dict[str, Any]) -> bool:
    output = task.get("output_json")
    if not isinstance(output, dict):
        return False
    summary = output.get("summary")
    result = output.get("result")
    if not isinstance(summary, str) or not summary.strip() or not isinstance(result, dict):
        return False
    preview_summary = readable_task_output_summary({"result": result})
    return bool(preview_summary) and summary.strip() == preview_summary.strip()


def _runner_log_summary_for_task(current_store: Any, task_id: str) -> str | None:
    runner_tasks = [
        item
        for item in _read_memory_dict(current_store, "ai_executor_tasks").values()
        if item.get("ai_task_id") == task_id
    ]
    if not runner_tasks:
        repository = getattr(current_store, "repository", None)
        list_runner_tasks = getattr(repository, "list_ai_executor_tasks", None)
        if callable(list_runner_tasks):
            runner_tasks = list_runner_tasks(ai_task_id=task_id)
    runner_tasks.sort(
        key=lambda item: (
            item.get("finished_at") or "",
            item.get("updated_at") or "",
            item.get("created_at") or "",
            item.get("id") or "",
        ),
    )
    for runner_task in reversed(runner_tasks):
        if runner_task.get("status") != "succeeded":
            continue
        if runner_task.get("task_kind") not in {None, "", "coding"}:
            continue
        summary = readable_runner_task_output_summary(runner_task)
        if summary:
            return summary
    return None


def _pending_reviews_with_recovered_summaries(
    current_store: Any,
    items: list[dict[str, Any]],
    *,
    read_store: Any,
) -> list[dict[str, Any]]:
    recovered_items: list[dict[str, Any]] = []
    for review in items:
        content = review.get("content")
        task = read_store.ai_tasks.get(review.get("ai_task_id"))
        if (
            not isinstance(content, dict)
            or task is None
            or not _task_summary_uses_raw_runner_preview(task)
        ):
            recovered_items.append(review)
            continue
        content_summary = readable_task_output_summary(content)
        task_summary = readable_task_output_summary(task.get("output_json"))
        recovered_summary = _runner_log_summary_for_task(current_store, task["id"])
        if (
            not content_summary
            or not task_summary
            or content_summary.strip() != task_summary.strip()
            or not recovered_summary
        ):
            recovered_items.append(review)
            continue
        recovered_items.append(
            {
                **review,
                "content": {**content, "summary": recovered_summary},
            }
        )
    return recovered_items


def task_detail_projection(
    current_store: Any,
    task: dict[str, Any],
    *,
    execution_context_manifest: dict[str, Any] | None = None,
    agent_loop: dict[str, Any] | None = None,
    quality_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail = current_store.snapshot(task)
    detail["product_context"] = public_product_context(task.get("product_context"))
    human_reviews = _read_memory_dict(current_store, "human_reviews")
    reviews = [
        human_reviews[review_id]
        for review_id in task.get("review_ids", [])
        if review_id in human_reviews
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
    output_json = task.get("output_json")
    detail["output"] = output_json
    detail["output_summary"] = (
        _runner_log_summary_for_task(current_store, task["id"])
        if _task_summary_uses_raw_runner_preview(task)
        else None
    ) or readable_task_output_summary(output_json)
    detail["current_step"] = task.get("current_step")
    detail["pending_review"] = current_store.snapshot(pending_review) if pending_review else None
    detail["reviews"] = current_store.snapshot({"items": reviews, "total": len(reviews)})
    detail["graph_runs"] = current_store.snapshot(graph_runs)
    detail["execution_context_manifest"] = current_store.snapshot(
        execution_context_manifest
    )
    detail["agent_loop"] = current_store.snapshot(agent_loop)
    detail["quality_gate"] = current_store.snapshot(quality_gate)
    detail["knowledge_deposits"] = {
        "items": [
            deposit
            for deposit in _read_memory_dict(current_store, "knowledge_deposits").values()
            if deposit["ai_task_id"] == task["id"]
        ]
    }
    writeback = _read_memory_dict(current_store, "mock_writebacks").get(
        writeback_idempotency_key(task["id"])
    )
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
    context_manifest = execution_context_manifest_for_task(
        current_store,
        task_id=task_id,
        product_scope_ids=product_scope_filter(user),
    )
    quality_gate = latest_quality_gate_for_task(
        current_store,
        product_scope_ids=product_scope_filter(user),
        task_id=task_id,
    )
    agent_loop = latest_agent_loop_for_task(
        current_store,
        product_scope_ids=product_scope_filter(user),
        task_id=task_id,
    )
    return task_detail_projection(
        read_store,
        task,
        agent_loop=agent_loop,
        execution_context_manifest=context_manifest,
        quality_gate=quality_gate,
    )


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
    ai_task_id: str | None = None,
    current_store: Any,
    page: int | None = None,
    page_size: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "created_at"
    if resolved_sort_by not in PENDING_REVIEW_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    filters = {"ai_task_id": ai_task_id}
    repository = pending_review_query_repository(current_store)
    if repository is not None:
        read_scope = task_read_scope(user)
        product_scope_ids = product_scope_filter(user)
        count_pending_reviews = getattr(repository, "count_pending_review_summaries", None)
        if callable(count_pending_reviews):
            total = count_pending_reviews(
                ai_task_id=ai_task_id,
                product_scope_ids=product_scope_ids,
                read_scope=read_scope,
            )
            items = repository.list_pending_review_summaries(
                ai_task_id=ai_task_id,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                product_scope_ids=product_scope_ids,
                read_scope=read_scope,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
            )
            items = _pending_reviews_with_recovered_summaries(
                current_store,
                items,
                read_store=task_workflow_read_store(current_store),
            )
            return add_list_observability(
                {
                    "items": items,
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "total": total,
                },
                filters=filters,
                list_name="pending_reviews",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=started_at,
            )
        items = repository.list_pending_review_summaries(
            product_scope_ids=product_scope_ids,
            read_scope=read_scope,
        )
        if ai_task_id:
            items = [item for item in items if item.get("ai_task_id") == ai_task_id]
        items = sort_list_items(
            items,
            allowed_fields=PENDING_REVIEW_SORT_FIELDS,
            default_sort_by="created_at",
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        total = len(items)
        page_items = items[
            (resolved_page - 1) * resolved_page_size : resolved_page * resolved_page_size
        ]
        page_items = _pending_reviews_with_recovered_summaries(
            current_store,
            page_items,
            read_store=task_workflow_read_store(current_store),
        )
        return add_list_observability(
            {
                "items": page_items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="pending_reviews",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    read_store = task_workflow_read_store(current_store)
    items = [
        review
        for review in read_store.human_reviews.values()
        if review["status"] == "pending"
        and (not ai_task_id or review["ai_task_id"] == ai_task_id)
        and (task := read_store.ai_tasks.get(review["ai_task_id"])) is not None
        and can_read_task(user, task)
    ]
    items = sort_list_items(
        items,
        allowed_fields=PENDING_REVIEW_SORT_FIELDS,
        default_sort_by="created_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    page_items = items[
        (resolved_page - 1) * resolved_page_size : resolved_page * resolved_page_size
    ]
    page_items = _pending_reviews_with_recovered_summaries(
        current_store,
        page_items,
        read_store=read_store,
    )
    return add_list_observability(
        {
            "items": page_items,
            "page": resolved_page,
            "page_size": resolved_page_size,
            "total": total,
        },
        filters=filters,
        list_name="pending_reviews",
        page=resolved_page,
        page_size=resolved_page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
    )


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
