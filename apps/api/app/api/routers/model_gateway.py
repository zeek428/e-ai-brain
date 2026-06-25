from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error, require_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.model_gateway import (
    MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES,
    MODEL_GATEWAY_PROVIDERS,
    MODEL_GATEWAY_STATUSES,
    delete_model_gateway_config_record,
    embedding_connection_mode,
    get_model_gateway_config_record,
    model_gateway_config_records,
    model_gateway_configs_after_default,
    model_gateway_write_store,
    normalize_embedding_dimension,
    normalized_model_gateway_embedding_fields,
    optional_non_blank,
    public_model_gateway_config,
    replace_memory_model_gateway_configs,
    save_model_gateway_config_record,
)
from app.services.model_gateway_config_tests import run_model_gateway_config_test
from app.services.model_gateway_listing import (
    list_model_gateway_configs_response,
    list_model_gateway_logs_response,
)
from app.services.product_config_context import (
    ensure_enum,
    ensure_non_blank,
    payload_updates,
    record_audit_event,
)

router = APIRouter(tags=["model_gateway"])


class ModelGatewayConfigRequest(BaseModel):
    name: str
    provider: str = "openai_compatible"
    base_url: str
    api_key: str | None = None
    default_chat_model: str
    default_embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_connection_mode: str | None = None
    embedding_dimension: int | None = None
    timeout_seconds: int = 60
    max_retries: int = 1
    status: str = "active"
    is_default: bool = False


class ModelGatewayConfigPatchRequest(BaseModel):
    name: str | None = None
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    default_chat_model: str | None = None
    default_embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_connection_mode: str | None = None
    embedding_dimension: int | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    status: str | None = None
    is_default: bool | None = None


class ModelGatewayConfigTestRequest(BaseModel):
    name: str
    provider: str = "openai_compatible"
    base_url: str
    api_key: str | None = None
    default_chat_model: str | None = None
    default_embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_connection_mode: str | None = None
    embedding_dimension: int | None = None
    timeout_seconds: int = 60
    max_retries: int = 1
    status: str = "active"
    is_default: bool = False
    test_target: str = "chat_and_embedding"
    config_id: str | None = None


@router.get("/api/system/model-gateway-configs")
def list_model_gateway_configs(
    request: Request,
    default_chat_model: str | None = Query(default=None),
    default_embedding_model: str | None = Query(default=None),
    embedding_connection_mode: str | None = Query(default=None),
    is_default: str | None = Query(default=None),
    name: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    provider: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_order: str = Query(default="asc"),
    status: str | None = Query(default=None),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    return list_model_gateway_configs_response(
        current_store=store(request),
        default_chat_model=default_chat_model,
        default_embedding_model=default_embedding_model,
        embedding_connection_mode=embedding_connection_mode,
        is_default=is_default,
        name=name,
        page=page,
        page_size=page_size,
        provider=provider,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
        trace_id=get_trace_id(request),
    )


@router.post("/api/system/model-gateway-configs/test")
def test_model_gateway_config(
    request: Request,
    payload: ModelGatewayConfigTestRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    current_store = model_gateway_write_store(store(request))
    result = run_model_gateway_config_test(
        current_store,
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/system/model-gateway-configs")
def create_model_gateway_config(
    request: Request,
    payload: ModelGatewayConfigRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    current_store = store(request)
    name = ensure_non_blank(payload.name, "name")
    base_url = ensure_non_blank(payload.base_url, "base_url")
    default_chat_model = ensure_non_blank(payload.default_chat_model, "default_chat_model")
    ensure_enum(payload.provider, MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    ensure_enum(payload.status, MODEL_GATEWAY_STATUSES, "model gateway status")
    embedding_fields = normalized_model_gateway_embedding_fields(
        api_key=payload.api_key,
        base_url=base_url,
        default_embedding_model=payload.default_embedding_model,
        embedding_api_key=payload.embedding_api_key,
        embedding_base_url=payload.embedding_base_url,
        embedding_connection_mode=payload.embedding_connection_mode,
        embedding_dimension=payload.embedding_dimension,
    )
    config_id = current_store.new_id("model_gateway_config")
    config = {
        "id": config_id,
        "name": name,
        "provider": payload.provider,
        "base_url": base_url,
        "api_key": payload.api_key,
        "default_chat_model": default_chat_model,
        "timeout_seconds": payload.timeout_seconds,
        "max_retries": payload.max_retries,
        "status": payload.status,
        "is_default": payload.is_default,
        **embedding_fields,
    }
    next_configs = {
        **model_gateway_config_records(current_store),
        config_id: config,
    }
    next_configs = model_gateway_configs_after_default(
        next_configs,
        config_id=config_id,
        is_default=payload.is_default,
    )
    config = next_configs[config_id]
    audit_event = record_audit_event(
        current_store,
        event_type="model_gateway_config.created",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
    )
    if not save_model_gateway_config_record(current_store, config, audit_event=audit_event):
        replace_memory_model_gateway_configs(current_store, next_configs)
    return envelope(public_model_gateway_config(config), get_trace_id(request))


@router.patch("/api/system/model-gateway-configs/{config_id}")
def patch_model_gateway_config(
    config_id: str,
    request: Request,
    payload: ModelGatewayConfigPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    current_store = store(request)
    config = get_model_gateway_config_record(current_store, config_id)
    if config is None:
        raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    updates = payload_updates(payload)
    if "name" in updates:
        updates["name"] = ensure_non_blank(updates["name"], "name")
    if "base_url" in updates:
        updates["base_url"] = ensure_non_blank(updates["base_url"], "base_url")
    if "default_chat_model" in updates:
        updates["default_chat_model"] = ensure_non_blank(
            updates["default_chat_model"],
            "default_chat_model",
        )
    if "default_embedding_model" in updates:
        updates["default_embedding_model"] = optional_non_blank(
            updates["default_embedding_model"]
        )
    if "embedding_base_url" in updates:
        updates["embedding_base_url"] = optional_non_blank(updates["embedding_base_url"])
    if "embedding_api_key" in updates:
        updates["embedding_api_key"] = optional_non_blank(updates["embedding_api_key"])
    if "embedding_connection_mode" in updates:
        ensure_enum(
            updates["embedding_connection_mode"],
            MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES,
            "embedding connection mode",
        )
    if "embedding_dimension" in updates:
        updates["embedding_dimension"] = normalize_embedding_dimension(
            updates["embedding_dimension"]
        )
    if "status" in updates:
        ensure_enum(updates["status"], MODEL_GATEWAY_STATUSES, "model gateway status")
    if "provider" in updates:
        ensure_enum(updates["provider"], MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    if {
        "default_embedding_model",
        "embedding_api_key",
        "embedding_base_url",
        "embedding_connection_mode",
        "embedding_dimension",
    } & updates.keys():
        embedding_fields = normalized_model_gateway_embedding_fields(
            api_key=updates.get("api_key", config.get("api_key")),
            base_url=updates.get("base_url", config["base_url"]),
            default_embedding_model=updates.get(
                "default_embedding_model",
                config.get("default_embedding_model"),
            ),
            embedding_api_key=updates.get("embedding_api_key"),
            embedding_base_url=updates.get(
                "embedding_base_url",
                config.get("embedding_base_url"),
            ),
            embedding_connection_mode=updates.get(
                "embedding_connection_mode",
                embedding_connection_mode(config),
            ),
            embedding_dimension=updates.get(
                "embedding_dimension",
                config.get("embedding_dimension"),
            ),
            existing_config=config,
        )
        updates.update(embedding_fields)
    config = {**config, **updates}
    next_configs = {
        **model_gateway_config_records(current_store),
        config_id: config,
    }
    next_configs = model_gateway_configs_after_default(
        next_configs,
        config_id=config_id,
        is_default=bool(config.get("is_default")),
    )
    config = next_configs[config_id]
    audit_event = record_audit_event(
        current_store,
        event_type="model_gateway_config.updated",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
    )
    if not save_model_gateway_config_record(current_store, config, audit_event=audit_event):
        replace_memory_model_gateway_configs(current_store, next_configs)
    return envelope(public_model_gateway_config(config), get_trace_id(request))


@router.delete("/api/system/model-gateway-configs/{config_id}")
def delete_model_gateway_config(
    config_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    current_store = store(request)
    if get_model_gateway_config_record(current_store, config_id) is None:
        raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    next_configs = model_gateway_config_records(current_store)
    next_configs.pop(config_id, None)
    audit_event = record_audit_event(
        current_store,
        event_type="model_gateway_config.deleted",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
    )
    if not delete_model_gateway_config_record(current_store, config_id, audit_event=audit_event):
        replace_memory_model_gateway_configs(current_store, next_configs)
    return envelope({"deleted": True, "id": config_id}, get_trace_id(request))


@router.get("/api/model-gateway/logs")
def list_model_gateway_logs(
    request: Request,
    ai_task_id: str | None = None,
    purpose: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    return list_model_gateway_logs_response(
        ai_task_id=ai_task_id,
        current_store=store(request),
        purpose=purpose,
        status=status,
        trace_id=get_trace_id(request),
    )
