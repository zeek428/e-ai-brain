from __future__ import annotations

from typing import Any

from fastapi import Request

from app.api.deps import api_error
from app.core.listing import (
    add_list_observability,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.trace import envelope, get_trace_id
from app.services.product_config_context import (
    ensure_enum,
    product_version_list_query_repository,
    product_version_summary_projection,
    product_version_summary_repository,
    request_started_at,
)
from app.services.version_status import VERSION_STATUSES

VERSION_SORT_FIELDS = {
    "code",
    "created_at",
    "name",
    "product_code",
    "product_name",
    "release_date",
    "start_date",
    "status",
    "updated_at",
}


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_memory_dict(current_store, collection_name).values())


def list_all_product_versions_response(
    *,
    active_only: bool,
    code: str | None,
    current_store: Any,
    name: str | None,
    page: int | None,
    page_size: int | None,
    product: str | None,
    product_id: str | None,
    product_scope_ids: list[str] | None,
    request: Request,
    sort_by: str | None,
    sort_order: str,
    status: str | None,
) -> dict[str, Any]:
    ensure_enum(status, VERSION_STATUSES, "product version status")
    ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "code"
    if resolved_sort_by not in VERSION_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    filters = {
        "active_only": active_only,
        "code": code,
        "name": name,
        "product": product,
        "product_id": product_id,
        "product_scope_ids": product_scope_ids,
        "status": status,
    }
    list_repository = product_version_list_query_repository(current_store)
    if list_repository is not None:
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        total = list_repository.count_product_version_summaries(**filters)
        items = list_repository.list_product_version_summaries_page(
            **filters,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        return envelope(
            add_list_observability(
                {
                    "items": items,
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "total": total,
                },
                filters=filters,
                list_name="product_versions",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=request_started_at(request),
            ),
            get_trace_id(request),
        )
    repository = product_version_summary_repository(current_store)
    if repository is not None:
        items = repository.list_product_version_summaries(active_only=active_only)
    else:
        items = [
            product_version_summary_projection(version, current_store)
            for version in _memory_records(current_store, "product_versions")
        ]
        if active_only:
            items = [item for item in items if item.get("status") == "active"]
    if product_scope_ids is not None:
        product_scope_set = set(product_scope_ids)
        items = [item for item in items if str(item.get("product_id")) in product_scope_set]
    if product_id:
        items = [item for item in items if item.get("product_id") == product_id]
    if status:
        items = [item for item in items if item.get("status") == status]
    items = [item for item in items if list_text_matches(item, code, ("code",))]
    items = [item for item in items if list_text_matches(item, name, ("name",))]
    items = [
        item
        for item in items
        if list_text_matches(item, product, ("product_code", "product_name", "product_id"))
    ]
    items = sort_list_items(
        items,
        allowed_fields=VERSION_SORT_FIELDS,
        default_sort_by="code",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters=filters,
        list_name="product_versions",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=request_started_at(request),
        trace_id=get_trace_id(request),
    )
