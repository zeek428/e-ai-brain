from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.core.listing import list_payload
from app.core.trace import envelope
from app.services.product_config_context import product_config_query_repository


def public_git_repository(repository: dict[str, Any]) -> dict[str, Any]:
    public_repository = {
        key: value
        for key, value in repository.items()
        if key != "credential_ref"
    }
    public_repository["credential_ref_configured"] = bool(
        repository.get("credential_ref") or repository.get("credential_ref_configured")
    )
    return public_repository


def list_product_git_repositories_response(
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
        items = repository.list_product_git_repositories(product_id, active_only=active_only)
        public_items = [public_git_repository(item) for item in items]
        return envelope({"items": public_items, "total": len(public_items)}, trace_id)
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    items = [
        item
        for item in current_store.product_git_repositories.values()
        if item["product_id"] == product_id
    ]
    items.sort(key=lambda item: item["name"])
    public_items = [public_git_repository(item) for item in items]
    return list_payload(public_items, trace_id=trace_id, active_only=active_only)
