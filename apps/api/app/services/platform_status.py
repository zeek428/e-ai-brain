from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse

from app.core.config import Settings
from app.core.store import MemoryStore


def runtime_data_access_mode(settings: Settings) -> str:
    if settings.persistence_mode == "memory":
        return "memory_test_helper"
    return "db_first_migration"


def tcp_check(host: str, port: int, timeout: float = 0.15) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "ok"
    except OSError:
        return "error"


def tcp_endpoint_from_url(url: str, default_host: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(url)
    return parsed.hostname or default_host, parsed.port or default_port


def _optional_non_blank(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _embedding_connection_mode(config: dict[str, Any]) -> str:
    mode = config.get("embedding_connection_mode")
    if mode:
        return str(mode)
    if _optional_non_blank(config.get("default_embedding_model")):
        return "reuse_chat"
    return "disabled"


def _default_model_gateway_config(current_store: MemoryStore) -> dict[str, Any] | None:
    for item in current_store.model_gateway_configs.values():
        if item.get("is_default") and item.get("status") == "active":
            return item
    return None


def _model_gateway_health_status(current_store: MemoryStore, settings: Settings) -> str:
    default_gateway = _default_model_gateway_config(current_store)
    if (
        default_gateway
        and default_gateway.get("base_url")
        and default_gateway.get("api_key")
    ):
        return "configured"
    return settings.model_gateway_status


def _embedding_gateway_health_status(current_store: MemoryStore, settings: Settings) -> str:
    default_gateway = _default_model_gateway_config(current_store)
    if default_gateway is None:
        return settings.model_gateway_status
    mode = _embedding_connection_mode(default_gateway)
    if mode == "disabled":
        return "disabled"
    if (
        default_gateway.get("provider") != "openai_compatible"
        or not _optional_non_blank(default_gateway.get("default_embedding_model"))
    ):
        return "failed"
    if mode == "custom":
        if not _optional_non_blank(default_gateway.get("embedding_base_url")):
            return "failed"
        if not _optional_non_blank(default_gateway.get("embedding_api_key")):
            return "failed"
        return "configured"
    if not _optional_non_blank(default_gateway.get("base_url")):
        return "failed"
    if not _optional_non_blank(default_gateway.get("api_key")):
        return "failed"
    return "configured"


def health_payload(
    *,
    current_store: MemoryStore,
    settings: Settings,
    trace_id: str,
) -> dict[str, str]:
    postgres_host, postgres_port = tcp_endpoint_from_url(
        settings.database_url,
        "127.0.0.1",
        5432,
    )
    redis_host, redis_port = tcp_endpoint_from_url(settings.redis_url, "127.0.0.1", 6379)
    postgres = tcp_check(postgres_host, postgres_port)
    redis = tcp_check(redis_host, redis_port)
    status = "ok" if postgres == "ok" and redis == "ok" else "degraded"
    model_gateway = _model_gateway_health_status(current_store, settings)
    return {
        "status": status,
        "postgres": postgres,
        "redis": redis,
        "model_gateway": model_gateway,
        "chat_gateway": model_gateway,
        "embedding_gateway": _embedding_gateway_health_status(current_store, settings),
        "data_access_mode": runtime_data_access_mode(settings),
        "long_memory": settings.long_memory_status,
        "trace_id": trace_id,
    }


def long_memory_status_payload(settings: Settings) -> dict[str, Any]:
    configured = settings.long_memory_status == "configured"
    return {
        "api_key_configured": bool(settings.gbrain_api_key),
        "base_url_configured": bool(settings.gbrain_base_url),
        "capabilities": [
            "hybrid_retrieval",
            "answer_synthesis",
            "knowledge_graph",
        ]
        if configured
        else [],
        "connector": "gbrain",
        "fallback_retriever": "postgres_pgvector",
        "status": settings.long_memory_status,
    }
