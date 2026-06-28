from __future__ import annotations

from typing import Any

from app.core.listing import list_payload
from app.core.trace import envelope
from app.services.product_config_context import product_config_query_repository


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_memory_dict(current_store, collection_name).values())


def list_related_systems_response(
    *,
    active_only: bool,
    current_store: Any,
    product_id: str | None,
    product_scope_ids: list[str] | None = None,
    trace_id: str,
) -> dict[str, Any]:
    repository = product_config_query_repository(current_store)
    if repository is not None:
        list_kwargs: dict[str, Any] = {
            "active_only": active_only,
            "product_id": product_id,
        }
        if product_scope_ids is not None:
            list_kwargs["product_scope_ids"] = product_scope_ids
        items = repository.list_related_systems(**list_kwargs)
        return envelope({"items": items, "total": len(items)}, trace_id)
    product_scope_set = set(product_scope_ids) if product_scope_ids is not None else None
    items = sorted(
        (
            item
            for item in _memory_records(current_store, "related_systems")
            if product_id is None or item.get("product_id") == product_id
            if product_scope_set is None or str(item.get("product_id")) in product_scope_set
        ),
        key=lambda item: (item.get("display_order", 0), item["code"]),
    )
    return list_payload(items, trace_id=trace_id, active_only=active_only)
