from __future__ import annotations

from time import perf_counter
from typing import Any

from app.core.listing import (
    ensure_list_enum,
    list_payload,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.trace import envelope
from app.services.model_gateway import (
    MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES,
    MODEL_GATEWAY_PROVIDERS,
    MODEL_GATEWAY_STATUSES,
    model_gateway_query_repository,
    model_gateway_write_store,
    public_model_gateway_config,
)

MODEL_GATEWAY_CONFIG_SORT_FIELDS = {
    "base_url",
    "default_chat_model",
    "default_embedding_model",
    "embedding_connection_mode",
    "id",
    "is_default",
    "name",
    "provider",
    "status",
}
BOOLEAN_FILTER_VALUES = {"false", "true"}


def _memory_model_gateway_logs(current_store: Any) -> list[dict[str, Any]]:
    logs = getattr(current_store, "model_gateway_logs", [])
    if isinstance(logs, dict):
        return list(logs.values())
    return list(logs or [])


def list_model_gateway_configs_response(
    *,
    current_store: Any,
    default_chat_model: str | None,
    default_embedding_model: str | None,
    embedding_connection_mode: str | None,
    is_default: str | None,
    name: str | None,
    page: int | None,
    page_size: int | None,
    provider: str | None,
    sort_by: str | None,
    sort_order: str,
    status: str | None,
    trace_id: str,
) -> dict[str, Any]:
    ensure_list_enum(provider, MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    ensure_list_enum(status, MODEL_GATEWAY_STATUSES, "model gateway status")
    ensure_list_enum(
        embedding_connection_mode,
        MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES,
        "embedding connection mode",
    )
    ensure_list_enum(is_default, BOOLEAN_FILTER_VALUES, "is_default")
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_list_enum(sort_by, MODEL_GATEWAY_CONFIG_SORT_FIELDS, "sort_by")

    started_at = perf_counter()
    read_store = model_gateway_write_store(current_store)
    repository = model_gateway_query_repository(read_store)
    if repository is not None:
        configs = repository.list_model_gateway_configs()
    else:
        configs = sorted(
            read_store.model_gateway_configs.values(),
            key=lambda item: item["id"],
        )
    filters = {
        "default_chat_model": default_chat_model,
        "default_embedding_model": default_embedding_model,
        "embedding_connection_mode": embedding_connection_mode,
        "is_default": is_default,
        "name": name,
        "provider": provider,
        "status": status,
    }
    is_default_bool = None if is_default is None else is_default == "true"
    items = [
        item
        for item in (public_model_gateway_config(config) for config in configs)
        if list_text_matches(item, name, ("id", "name", "base_url"))
        and list_text_matches(item, default_chat_model, ("default_chat_model",))
        and list_text_matches(item, default_embedding_model, ("default_embedding_model",))
        and (not provider or item.get("provider") == provider)
        and (not status or item.get("status") == status)
        and (
            not embedding_connection_mode
            or item.get("embedding_connection_mode") == embedding_connection_mode
        )
        and (is_default_bool is None or item.get("is_default") is is_default_bool)
    ]
    sorted_items = sort_list_items(
        items,
        allowed_fields=MODEL_GATEWAY_CONFIG_SORT_FIELDS,
        default_sort_by="name",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    if page is None and page_size is None:
        return list_payload(sorted_items, trace_id=trace_id)
    return paginated_list_payload(
        sorted_items,
        filters=filters,
        list_name="model_gateway_configs",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )


def list_model_gateway_logs_response(
    *,
    ai_task_id: str | None,
    current_store: Any,
    purpose: str | None,
    status: str | None,
    trace_id: str,
) -> dict[str, Any]:
    repository = model_gateway_query_repository(current_store)
    if repository is not None:
        items = repository.list_model_gateway_logs(
            ai_task_id=ai_task_id,
            purpose=purpose,
            status=status,
        )
    else:
        items = _memory_model_gateway_logs(current_store)
        if ai_task_id:
            items = [item for item in items if item.get("ai_task_id") == ai_task_id]
        if purpose:
            items = [item for item in items if item["purpose"] == purpose]
        if status:
            items = [item for item in items if item["status"] == status]
        items.sort(key=lambda item: item["created_at"], reverse=True)
    return envelope({"items": items, "total": len(items)}, trace_id)
