from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.listing import add_list_observability, ensure_list_enum, sort_list_items
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.core.task_titles import code_inspection_remediation_title
from app.services.product_scope import product_scope_filter
from app.services.task_access import can_read_task, task_read_scope

AI_TASK_SORT_FIELDS = {
    "created_at",
    "created_by",
    "id",
    "product_id",
    "product_name",
    "status",
    "task_type",
    "title",
    "updated_at",
}


def parse_iso_datetime(value: str, field_name: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    if len(normalized) >= 6 and normalized[-6] == " " and normalized[-3] == ":":
        normalized = f"{normalized[:-6]}+{normalized[-5:]}"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"Invalid {field_name}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def ai_task_list_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    count_tasks = getattr(repository, "count_ai_task_summaries", None)
    list_tasks = getattr(repository, "list_ai_task_summaries", None)
    if callable(count_tasks) and callable(list_tasks):
        return repository
    return None


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_memory_dict(current_store, collection_name).values())


def task_product_name(current_store: Any, task: dict[str, Any]) -> str | None:
    if task.get("product_name"):
        return task.get("product_name")
    product_id = task.get("product_id")
    product = _memory_dict(current_store, "products").get(str(product_id)) if product_id else None
    if product:
        return product.get("name")
    product_context = task.get("product_context")
    if isinstance(product_context, dict):
        product_snapshot = product_context.get("product")
        if isinstance(product_snapshot, dict):
            return product_snapshot.get("name")
    return None


def task_display_title(task: dict[str, Any]) -> str:
    title = str(task.get("title") or "")
    if task.get("task_type") != "code_inspection_remediation":
        return title
    input_json = task.get("input_json")
    context = input_json if isinstance(input_json, dict) else {}
    if not context:
        return title
    return code_inspection_remediation_title(context, fallback_title=title)


def task_summary_projection(task: dict[str, Any], current_store: Any) -> dict[str, Any]:
    return {
        "brain_app_id": task.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "created_at": task.get("created_at"),
        "created_by": task.get("created_by"),
        "current_step": task.get("current_step"),
        "id": task["id"],
        "module_code": task.get("module_code"),
        "product_id": task["product_id"],
        "product_name": task_product_name(current_store, task),
        "requirement_id": task["requirement_id"],
        "status": task["status"],
        "task_type": task["task_type"],
        "title": task_display_title(task),
        "updated_at": task.get("updated_at"),
        "version_id": task["version_id"],
    }


def list_ai_tasks_response(
    *,
    created_by: str | None,
    created_from: str | None,
    created_to: str | None,
    current_store: Any,
    keyword: str | None,
    page: int | None,
    page_size: int | None,
    product_id: str | None,
    requirement_id: str | None,
    sort_by: str | None,
    sort_order: str,
    started_at: float | None,
    status: str | None,
    task_type: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    from_at = parse_iso_datetime(created_from, "created_from") if created_from else None
    to_at = parse_iso_datetime(created_to, "created_to") if created_to else None
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "created_at"
    if resolved_sort_by not in AI_TASK_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    filters = {
        "created_by": created_by,
        "created_from": created_from,
        "created_to": created_to,
        "keyword": keyword,
        "product_id": product_id,
        "requirement_id": requirement_id,
        "status": status,
        "task_type": task_type,
    }

    repository = ai_task_list_query_repository(current_store)
    if repository is not None:
        read_scope = task_read_scope(user)
        product_scope_ids = product_scope_filter(user)
        query_filters = {
            "created_by": created_by,
            "created_from": from_at,
            "created_to": to_at,
            "keyword": keyword,
            "product_id": product_id,
            "product_scope_ids": product_scope_ids,
            "read_scope": read_scope,
            "requirement_id": requirement_id,
            "status": status,
            "task_type": task_type,
        }
        total = repository.count_ai_task_summaries(**query_filters)
        items = repository.list_ai_task_summaries(
            **query_filters,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        items = [task_summary_projection(item, current_store) for item in items]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_tasks",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )

    items = [
        item
        for item in _memory_records(current_store, "ai_tasks")
        if can_read_task(user, item)
    ]
    if status:
        items = [item for item in items if item["status"] == status]
    if task_type:
        items = [item for item in items if item["task_type"] == task_type]
    if product_id:
        items = [item for item in items if item["product_id"] == product_id]
    if requirement_id:
        items = [item for item in items if item["requirement_id"] == requirement_id]
    if from_at or to_at:
        filtered_items = []
        for item in items:
            created_at = item.get("created_at") or item.get("updated_at")
            if not created_at:
                continue
            item_created_at = parse_iso_datetime(str(created_at), "created_at")
            if from_at and item_created_at < from_at:
                continue
            if to_at and item_created_at > to_at:
                continue
            filtered_items.append(item)
        items = filtered_items
    if keyword:
        normalized_keyword = keyword.lower()
        items = [
            item
            for item in items
            if normalized_keyword
            in f"{item.get('id', '')} {item.get('title', '')} {item.get('task_type', '')}".lower()
        ]
    if created_by:
        normalized_created_by = created_by.lower()
        items = [
            item
            for item in items
            if normalized_created_by in str(item.get("created_by", "")).lower()
        ]

    items = [task_summary_projection(item, current_store) for item in items]
    items = sort_list_items(
        items,
        allowed_fields=AI_TASK_SORT_FIELDS,
        default_sort_by="created_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    items = items[(resolved_page - 1) * resolved_page_size : resolved_page * resolved_page_size]
    return add_list_observability(
        {
            "items": items,
            "page": resolved_page,
            "page_size": resolved_page_size,
            "total": total,
        },
        filters=filters,
        list_name="ai_tasks",
        page=resolved_page,
        page_size=resolved_page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
    )
