from __future__ import annotations

from typing import Any

from app.api.deps import api_error
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


def list_product_modules_response(
    *,
    active_only: bool,
    current_store: Any,
    product_id: str,
    trace_id: str,
) -> dict[str, Any]:
    repository = product_config_query_repository(current_store)
    if repository is not None:
        if repository.get_product(product_id) is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        items = repository.list_product_modules(product_id, active_only=active_only)
        return envelope({"items": items, "total": len(items)}, trace_id)
    if product_id not in _memory_dict(current_store, "products"):
        raise api_error(404, "NOT_FOUND", "Product not found")
    items = [
        item
        for item in _memory_records(current_store, "product_modules")
        if item["product_id"] == product_id
    ]
    items.sort(key=lambda item: (item.get("display_order", 0), item["code"]))
    return list_payload(items, trace_id=trace_id, active_only=active_only)
