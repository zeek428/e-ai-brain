from __future__ import annotations

from typing import Any, Protocol

from app.api.deps import api_error
from app.services.model_gateway import (
    MODEL_GATEWAY_PROVIDERS,
    MODEL_GATEWAY_STATUSES,
    MODEL_GATEWAY_TEST_TARGETS,
    model_gateway_embedding_test_fields,
    model_gateway_test_skipped,
    normalized_model_gateway_embedding_fields,
    save_model_gateway_payload,
    test_model_gateway_chat,
    test_model_gateway_embedding,
)
from app.services.product_config_context import (
    ensure_enum,
    ensure_non_blank,
    record_audit_event,
)


class ModelGatewayConfigTestPayload(Protocol):
    api_key: str | None
    base_url: str
    config_id: str | None
    default_chat_model: str | None
    default_embedding_model: str | None
    embedding_api_key: str | None
    embedding_base_url: str | None
    embedding_connection_mode: str | None
    embedding_dimension: int | None
    max_retries: int
    name: str
    provider: str
    status: str
    test_target: str
    timeout_seconds: int


def run_model_gateway_config_test(
    current_store: Any,
    *,
    payload: ModelGatewayConfigTestPayload,
    user: dict[str, Any],
) -> dict[str, Any]:
    name = ensure_non_blank(payload.name, "name")
    base_url = ensure_non_blank(payload.base_url, "base_url")
    ensure_enum(
        payload.test_target,
        MODEL_GATEWAY_TEST_TARGETS,
        "model gateway test target",
    )
    test_target = payload.test_target
    should_test_chat = test_target in {"chat", "chat_and_embedding"}
    default_chat_model = (
        ensure_non_blank(payload.default_chat_model, "default_chat_model")
        if should_test_chat
        else (payload.default_chat_model or "").strip()
    )
    ensure_enum(payload.provider, MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    ensure_enum(payload.status, MODEL_GATEWAY_STATUSES, "model gateway status")
    existing_config = None
    if payload.config_id:
        existing_config = current_store.model_gateway_configs.get(payload.config_id)
        if existing_config is None:
            raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    api_key = payload.api_key or (existing_config or {}).get("api_key")
    if should_test_chat and not api_key:
        raise api_error(
            400,
            "MODEL_GATEWAY_CONFIG_INVALID",
            "Model gateway test requires an API key",
        )
    should_test_embedding = test_target in {"chat_and_embedding", "embedding"}
    if should_test_embedding:
        embedding_fields = normalized_model_gateway_embedding_fields(
            api_key=api_key,
            base_url=base_url,
            default_embedding_model=payload.default_embedding_model,
            embedding_api_key=payload.embedding_api_key,
            embedding_base_url=payload.embedding_base_url,
            embedding_connection_mode=payload.embedding_connection_mode,
            embedding_dimension=payload.embedding_dimension,
            existing_config=existing_config,
        )
    else:
        embedding_fields = model_gateway_embedding_test_fields(
            default_embedding_model=payload.default_embedding_model,
            embedding_api_key=payload.embedding_api_key,
            embedding_base_url=payload.embedding_base_url,
            embedding_connection_mode=payload.embedding_connection_mode,
            embedding_dimension=payload.embedding_dimension,
            existing_config=existing_config,
        )
    should_test_embedding = (
        should_test_embedding and embedding_fields["embedding_connection_mode"] != "disabled"
    )
    test_config = {
        "api_key": api_key,
        "base_url": base_url,
        "default_chat_model": default_chat_model,
        "id": payload.config_id or "model_gateway_config_test",
        "is_default": False,
        "max_retries": payload.max_retries,
        "name": name,
        "provider": payload.provider,
        "status": payload.status,
        "timeout_seconds": payload.timeout_seconds,
        **embedding_fields,
    }
    chat_result = (
        test_model_gateway_chat(test_config)
        if should_test_chat
        else model_gateway_test_skipped(model=default_chat_model)
    )
    embedding_result = (
        test_model_gateway_embedding(test_config)
        if should_test_embedding
        else model_gateway_test_skipped(model=embedding_fields["default_embedding_model"] or "")
    )
    result = {
        "chat": chat_result,
        "embedding": embedding_result,
        "ok": bool(chat_result["ok"] and embedding_result["ok"]),
        "test_target": test_target,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="model_gateway_config.tested",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=payload.config_id,
        payload={
            "chat_status": chat_result["status"],
            "embedding_status": embedding_result["status"],
            "provider": payload.provider,
            "test_target": test_target,
        },
    )
    save_model_gateway_payload(
        current_store,
        configs=current_store.model_gateway_configs,
        logs=current_store.model_gateway_logs,
        audit_event=audit_event,
    )
    return result
