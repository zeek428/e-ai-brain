from __future__ import annotations

from typing import Any

from app.api.deps import api_error, require_permissions
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.services.task_workflow_context import task_workflow_read_store
from app.services.product_scope import product_scope_filter, user_can_read_product
from app.services.version_status import canonical_requirement_status

REQUIREMENT_SOURCE_VALUES = {
    "business_department",
    "internal_research",
    "other",
    "product_planning",
    "user_feedback",
}

REQUIREMENT_SORT_FIELDS = {
    "assignee",
    "created_at",
    "id",
    "priority",
    "product_code",
    "product_name",
    "source",
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


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def requirement_summary_projection(
    requirement: dict[str, Any],
    current_store: Any,
) -> dict[str, Any]:
    product = _memory_dict(current_store, "products").get(requirement.get("product_id"), {})
    version = _memory_dict(current_store, "product_versions").get(
        requirement.get("version_id"), {}
    )
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
    source: str | None,
    sort_by: str | None,
    sort_order: str,
    started_at: float | None,
    status: str | None,
    title: str | None,
    trace_id: str,
    user: dict[str, Any],
    version: str | None,
    version_id: str | None,
) -> dict[str, Any]:
    require_permissions(user, {"requirement.read"})
    ensure_list_enum(priority, {"P0", "P1", "P2"}, "requirement priority")
    ensure_list_enum(source, REQUIREMENT_SOURCE_VALUES, "requirement source")
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "created_at"
    if resolved_sort_by not in REQUIREMENT_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_status = canonical_requirement_status(status) if status else None
    filters = {
        "priority": priority,
        "product": product,
        "product_id": product_id,
        "source": source,
        "status": resolved_status,
        "title": title,
        "version": version,
        "version_id": version_id,
    }
    product_scope_ids = product_scope_filter(user)
    if product_id is not None and not user_can_read_product(user, product_id):
        empty_payload = paginated_list_payload(
            [],
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
        return add_list_observability(
            empty_payload,
            filters={
                **filters,
                "status": status,
            },
            list_name="requirements",
            page=empty_payload.get("page"),
            page_size=empty_payload.get("page_size"),
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    query_filters = dict(filters)
    if product_scope_ids is not None:
        query_filters["product_scope_ids"] = product_scope_ids

    repository = requirement_list_query_repository(current_store)
    if repository is not None:
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        total = repository.count_requirement_summaries(**query_filters)
        items = repository.list_requirement_summaries(
            **query_filters,
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
    if product_scope_ids is not None:
        items = [
            item
            for item in items
            if item.get("product_id") is not None
            and str(item.get("product_id")) in product_scope_ids
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
    if source:
        items = [item for item in items if item.get("source") == source]
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
