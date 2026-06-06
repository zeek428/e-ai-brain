from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.core.config import get_settings

settings = get_settings()

MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES = {"custom", "disabled", "reuse_chat"}


def optional_non_blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def embedding_connection_mode(config: dict[str, Any]) -> str:
    mode = config.get("embedding_connection_mode")
    if mode:
        return str(mode)
    if optional_non_blank(config.get("default_embedding_model")):
        return "reuse_chat"
    return "disabled"


def normalize_embedding_connection_mode(
    mode: str | None,
    *,
    default_embedding_model: str | None,
) -> str:
    normalized_mode = optional_non_blank(mode)
    if normalized_mode is None:
        return "reuse_chat" if optional_non_blank(default_embedding_model) else "disabled"
    if normalized_mode not in MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported embedding connection mode")
    return normalized_mode


def normalize_embedding_dimension(value: int | None) -> int | None:
    if value is None:
        return None
    if value <= 0:
        raise api_error(400, "VALIDATION_ERROR", "embedding_dimension must be positive")
    if value != settings.vector_dimension:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            (
                "embedding_dimension must equal configured vector dimension "
                f"{settings.vector_dimension}"
            ),
        )
    return value


def normalized_model_gateway_embedding_fields(
    *,
    api_key: str | None,
    base_url: str,
    default_embedding_model: str | None,
    embedding_api_key: str | None,
    embedding_base_url: str | None,
    embedding_connection_mode: str | None,
    embedding_dimension: int | None,
    existing_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = optional_non_blank(default_embedding_model)
    mode = normalize_embedding_connection_mode(
        embedding_connection_mode,
        default_embedding_model=model,
    )
    dimension = normalize_embedding_dimension(embedding_dimension)
    if mode == "disabled":
        return {
            "default_embedding_model": None,
            "embedding_api_key": None,
            "embedding_base_url": None,
            "embedding_connection_mode": mode,
            "embedding_dimension": None,
        }
    if model is None:
        raise api_error(400, "VALIDATION_ERROR", "default_embedding_model is required")
    if mode == "reuse_chat":
        return {
            "default_embedding_model": model,
            "embedding_api_key": None,
            "embedding_base_url": None,
            "embedding_connection_mode": mode,
            "embedding_dimension": dimension or settings.vector_dimension,
        }

    custom_base_url = optional_non_blank(embedding_base_url)
    if custom_base_url is None:
        raise api_error(400, "VALIDATION_ERROR", "embedding_base_url is required")
    custom_api_key = (
        optional_non_blank(embedding_api_key)
        or (existing_config or {}).get("embedding_api_key")
    )
    if custom_api_key is None:
        raise api_error(400, "VALIDATION_ERROR", "embedding_api_key is required")
    return {
        "default_embedding_model": model,
        "embedding_api_key": custom_api_key,
        "embedding_base_url": custom_base_url,
        "embedding_connection_mode": mode,
        "embedding_dimension": dimension or settings.vector_dimension,
    }


def model_gateway_embedding_test_fields(
    *,
    default_embedding_model: str | None,
    embedding_api_key: str | None,
    embedding_base_url: str | None,
    embedding_connection_mode: str | None,
    embedding_dimension: int | None,
    existing_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = optional_non_blank(default_embedding_model)
    mode = normalize_embedding_connection_mode(
        embedding_connection_mode,
        default_embedding_model=model,
    )
    dimension = (
        embedding_dimension
        if embedding_dimension is not None and embedding_dimension > 0
        else None
    )
    if mode == "disabled":
        return {
            "default_embedding_model": None,
            "embedding_api_key": None,
            "embedding_base_url": None,
            "embedding_connection_mode": mode,
            "embedding_dimension": None,
        }
    return {
        "default_embedding_model": model,
        "embedding_api_key": (
            optional_non_blank(embedding_api_key)
            or (existing_config or {}).get("embedding_api_key")
        ),
        "embedding_base_url": (
            optional_non_blank(embedding_base_url)
            or (existing_config or {}).get("embedding_base_url")
        ),
        "embedding_connection_mode": mode,
        "embedding_dimension": (
            dimension
            or (existing_config or {}).get("embedding_dimension")
            or (settings.vector_dimension if model else None)
        ),
    }
