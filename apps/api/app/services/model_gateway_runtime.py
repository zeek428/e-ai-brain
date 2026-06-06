from __future__ import annotations

from time import perf_counter
from typing import Any

from app.core.config import get_settings


def model_gateway_test_failure(
    *,
    error_code: str,
    model: str,
    started: float,
) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": model,
        "ok": False,
        "status": "failed",
    }


def model_gateway_test_skipped(*, model: str = "") -> dict[str, Any]:
    return {
        "model": model,
        "ok": True,
        "status": "skipped",
    }


def model_gateway_chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def model_gateway_embeddings_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/embeddings"):
        return normalized
    return f"{normalized}/embeddings"


def parse_embedding_response(
    response_payload: dict[str, Any],
    *,
    expected_count: int,
    vector_dimension: int | None = None,
) -> list[list[float]]:
    expected_dimension = vector_dimension or get_settings().vector_dimension
    data = response_payload.get("data")
    if not isinstance(data, list) or len(data) != expected_count:
        raise ValueError("Embedding response data count does not match request")
    embeddings_by_index: dict[int, list[float]] = {}
    for fallback_index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError("Embedding response item must be an object")
        index = int(item.get("index", fallback_index))
        embedding = item.get("embedding")
        if not isinstance(embedding, list):
            raise ValueError("Embedding response item is missing embedding")
        vector = [float(value) for value in embedding]
        if len(vector) != expected_dimension:
            raise ValueError("Embedding dimension does not match configured vector dimension")
        embeddings_by_index[index] = vector
    return [embeddings_by_index[index] for index in range(expected_count)]


def embedding_context_from_config(
    config: dict[str, Any],
    embeddings: list[list[float]],
) -> dict[str, Any]:
    dimension = len(embeddings[0]) if embeddings else config.get("embedding_dimension")
    context = {
        "embedding_dimension": dimension,
        "embedding_model": config["default_embedding_model"],
    }
    if config.get("id"):
        context["embedding_config_id"] = config["id"]
    return context
