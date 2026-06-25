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
    product_config_query_repository,
    product_list_projection,
    product_list_query_repository,
    request_started_at,
)

PRODUCT_STATUSES = {"active", "inactive"}
PRODUCT_SORT_FIELDS = {
    "code",
    "current_version_name",
    "display_order",
    "id",
    "module_count",
    "name",
    "owner_team",
    "status",
}


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_memory_dict(current_store, collection_name).values())


def list_products_response(
    *,
    active_only: bool,
    code: str | None,
    current_store: Any,
    name: str | None,
    owner_team: str | None,
    page: int | None,
    page_size: int | None,
    request: Request,
    sort_by: str | None,
    sort_order: str,
    status: str | None,
) -> dict[str, Any]:
    ensure_enum(status, PRODUCT_STATUSES, "product status")
    ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "display_order"
    if resolved_sort_by not in PRODUCT_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    filters = {
        "active_only": active_only,
        "code": code,
        "name": name,
        "owner_team": owner_team,
        "status": status,
    }
    list_repository = product_list_query_repository(current_store)
    if list_repository is not None:
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        total = list_repository.count_product_summaries(**filters)
        items = list_repository.list_product_summaries(
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
                list_name="products",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=request_started_at(request),
            ),
            get_trace_id(request),
        )
    repository = product_config_query_repository(current_store)
    if repository is not None:
        items = repository.list_products(active_only=active_only)
    else:
        items = sorted(
            _memory_records(current_store, "products"),
            key=lambda item: (item.get("display_order", 0), item["code"]),
        )
        if active_only:
            items = [item for item in items if item.get("status") == "active"]
    items = [product_list_projection(item, current_store) for item in items]
    if status:
        items = [item for item in items if item.get("status") == status]
    items = [item for item in items if list_text_matches(item, code, ("code", "id"))]
    items = [item for item in items if list_text_matches(item, name, ("name",))]
    items = [item for item in items if list_text_matches(item, owner_team, ("owner_team",))]
    items = sort_list_items(
        items,
        allowed_fields=PRODUCT_SORT_FIELDS,
        default_sort_by="display_order",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters=filters,
        list_name="products",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=request_started_at(request),
        trace_id=get_trace_id(request),
    )
