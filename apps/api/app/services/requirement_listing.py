from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.services.task_workflow_context import task_workflow_read_store
from app.services.version_status import canonical_requirement_status

REQUIREMENT_SORT_FIELDS = {
    "assignee",
    "created_at",
    "id",
    "priority",
    "product_code",
    "product_name",
    "status",
    "title",
    "updated_at",
    "version_code",
    "version_name",
}


def requirement_list_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    count_requirements = getattr(repository, "count_requirement_summaries", None)
    list_requirements = getattr(repository, "list_requirement_summaries", None)
    if callable(count_requirements) and callable(list_requirements):
        return repository
    return None


def requirement_summary_projection(
    requirement: dict[str, Any],
    current_store: Any,
) -> dict[str, Any]:
    product = current_store.products.get(requirement.get("product_id"), {})
    version = current_store.product_versions.get(requirement.get("version_id"), {})
    return {
        **requirement,
        "product_code": product.get("code"),
        "product_name": product.get("name"),
        "version_code": version.get("code"),
        "version_name": version.get("name"),
    }


def list_requirements_response(
    *,
    current_store: Any,
    page: int | None,
    page_size: int | None,
    priority: str | None,
    product: str | None,
    product_id: str | None,
    sort_by: str | None,
    sort_order: str,
    started_at: float | None,
    status: str | None,
    title: str | None,
    trace_id: str,
    version: str | None,
    version_id: str | None,
) -> dict[str, Any]:
    ensure_list_enum(priority, {"P0", "P1", "P2"}, "requirement priority")
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "created_at"
    if resolved_sort_by not in REQUIREMENT_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_status = canonical_requirement_status(status) if status else None
    filters = {
        "priority": priority,
        "product": product,
        "product_id": product_id,
        "status": resolved_status,
        "title": title,
        "version": version,
        "version_id": version_id,
    }

    repository = requirement_list_query_repository(current_store)
    if repository is not None:
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        total = repository.count_requirement_summaries(**filters)
        items = repository.list_requirement_summaries(
            **filters,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters={
                **filters,
                "status": status,
            },
            list_name="requirements",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )

    read_store = task_workflow_read_store(current_store)
    items = [
        requirement_summary_projection(requirement, read_store)
        for requirement in read_store.requirements.values()
    ]
    if product_id:
        items = [item for item in items if item["product_id"] == product_id]
    if status:
        items = [
            item
            for item in items
            if canonical_requirement_status(item.get("status")) == resolved_status
        ]
    if version_id:
        items = [item for item in items if item.get("version_id") == version_id]
    if priority:
        items = [item for item in items if item.get("priority") == priority]
    items = [item for item in items if list_text_matches(item, title, ("title", "id"))]
    items = [
        item
        for item in items
        if list_text_matches(
            item,
            product,
            ("product_code", "product_name", "product_id"),
        )
    ]
    items = [
        item
        for item in items
        if list_text_matches(item, version, ("version_code", "version_name", "version_id"))
    ]
    items = sort_list_items(
        items,
        allowed_fields=REQUIREMENT_SORT_FIELDS,
        default_sort_by="created_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters={
            **filters,
            "status": status,
        },
        list_name="requirements",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )["data"]
