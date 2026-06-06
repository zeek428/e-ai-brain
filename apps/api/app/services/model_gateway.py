from __future__ import annotations

import json
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from app.core.config import get_settings
from app.services.model_gateway_config_context import (
    ModelGatewayRequestContext,
    default_model_gateway_config,
    model_gateway_configs_after_default,
    model_gateway_query_repository,
    model_gateway_source_store,
    model_gateway_write_store,
    public_model_gateway_config,
    runtime_repository,
    save_model_gateway_payload,
    save_model_gateway_records,
)
from app.services.model_gateway_embeddings import (
    MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES,
    embedding_connection_mode,
    model_gateway_embedding_test_fields,
    normalize_embedding_dimension,
    normalized_model_gateway_embedding_fields,
    optional_non_blank,
)
from app.services.model_gateway_logging import (
    estimate_tokens,
    model_gateway_log,
    openai_embedding_usage_tokens,
    openai_usage_tokens,
)
from app.services.model_gateway_runtime import (
    embedding_context_from_config,
    model_gateway_chat_completions_url,
    model_gateway_embeddings_url,
    model_gateway_test_failure,
    model_gateway_test_skipped,
    parse_embedding_response,
)
from app.services.model_gateway_task_io import (
    derive_code_review_risk_level,
    model_gateway_messages,
    normalize_model_gateway_code_review_output,
    parse_model_gateway_task_output,
    public_git_repository,
    public_product_context,
)

settings = get_settings()

__all__ = [
    "MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES",
    "ModelGatewayRequestContext",
    "default_model_gateway_config",
    "derive_code_review_risk_level",
    "embedding_connection_mode",
    "model_gateway_configs_after_default",
    "model_gateway_chat_completions_url",
    "model_gateway_embedding_test_fields",
    "model_gateway_embeddings_url",
    "model_gateway_messages",
    "model_gateway_query_repository",
    "model_gateway_source_store",
    "model_gateway_test_failure",
    "model_gateway_test_skipped",
    "model_gateway_write_store",
    "normalize_embedding_dimension",
    "normalize_model_gateway_code_review_output",
    "normalized_model_gateway_embedding_fields",
    "optional_non_blank",
    "parse_model_gateway_task_output",
    "parse_embedding_response",
    "public_git_repository",
    "public_model_gateway_config",
    "public_product_context",
    "runtime_repository",
    "save_model_gateway_payload",
    "save_model_gateway_records",
]

MODEL_GATEWAY_PROVIDERS = {"openai_compatible"}
MODEL_GATEWAY_STATUSES = {"active", "inactive"}
MODEL_GATEWAY_TEST_TARGETS = {"chat", "chat_and_embedding", "embedding"}


class ModelGatewayCallError(Exception):
    def __init__(self, log: dict[str, Any]):
        super().__init__("Model gateway request failed")
        self.log = log


class ModelGatewayConfigError(Exception):
    def __init__(self, message: str, current_step: str = "model_gateway_config_invalid"):
        super().__init__(message)
        self.current_step = current_step


def call_openai_compatible_model_gateway(
    current_store: Any,
    *,
    code_review_payload: dict[str, Any] | None = None,
    config: dict[str, Any],
    opener: Any | None = None,
    task: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = config["provider"]
    model = config["default_chat_model"]
    config_id = config["id"]
    messages = model_gateway_messages(code_review_payload=code_review_payload, task=task)
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    request = UrlRequest(
        model_gateway_chat_completions_url(config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    resolved_opener = opener or urlopen
    started = perf_counter()
    try:
        with resolved_opener(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        output = parse_model_gateway_task_output(response_payload, task)
        latency_ms = int((perf_counter() - started) * 1000)
        log = model_gateway_log(
            current_store,
            task=task,
            provider=provider,
            model=model,
            config_id=config_id,
            tokens=openai_usage_tokens(
                response_payload.get("usage"),
                messages=messages,
                output=output,
            ),
            latency_ms=latency_ms,
            status="succeeded",
        )
        return output, log
    except (
        AttributeError,
        HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        prompt_tokens = estimate_tokens(messages)
        log = model_gateway_log(
            current_store,
            task=task,
            provider=provider,
            model=model,
            config_id=config_id,
            tokens={"prompt": prompt_tokens, "completion": 0, "total": prompt_tokens},
            latency_ms=latency_ms,
            status="failed",
            error="Model gateway request failed",
        )
        raise ModelGatewayCallError(log) from exc


def call_model_gateway_for_task(
    current_store: Any,
    *,
    code_review_payload: dict[str, Any] | None = None,
    opener: Any | None = None,
    task: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = default_model_gateway_config(current_store)
    if config:
        if config.get("provider") != "openai_compatible":
            raise ModelGatewayConfigError("Active model gateway provider is not supported")
        if not config.get("api_key"):
            raise ModelGatewayConfigError("Active model gateway config is missing api_key")
        return call_openai_compatible_model_gateway(
            current_store,
            code_review_payload=code_review_payload,
            config=config,
            opener=opener,
            task=task,
        )

    if settings.model_gateway_status == "configured":
        return call_openai_compatible_model_gateway(
            current_store,
            code_review_payload=code_review_payload,
            config={
                "api_key": settings.model_gateway_api_key,
                "base_url": settings.model_gateway_base_url,
                "default_chat_model": settings.model_gateway_default_chat_model,
                "id": None,
                "provider": "openai_compatible",
                "timeout_seconds": 60,
            },
            opener=opener,
            task=task,
        )

    raise ModelGatewayConfigError(
        "No active/default model gateway config is configured",
        current_step="model_gateway_config_invalid",
    )


def runtime_required_text(value: Any, message: str) -> str:
    if value is None:
        raise ModelGatewayConfigError(message)
    text = str(value).strip()
    if not text:
        raise ModelGatewayConfigError(message)
    return text


def model_gateway_embedding_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("provider") != "openai_compatible":
        raise ModelGatewayConfigError("Active model gateway provider is not supported")
    mode = embedding_connection_mode(config)
    if mode == "disabled":
        raise ModelGatewayConfigError("Embedding gateway is disabled")
    model = runtime_required_text(
        config.get("default_embedding_model"),
        "Active model gateway config is missing default_embedding_model",
    )
    if mode == "custom":
        base_url = runtime_required_text(
            config.get("embedding_base_url"),
            "Active model gateway config is missing embedding_base_url",
        )
        api_key = runtime_required_text(
            config.get("embedding_api_key"),
            "Active model gateway config is missing embedding_api_key",
        )
    else:
        base_url = runtime_required_text(
            config.get("base_url"),
            "Active model gateway config is missing base_url",
        )
        api_key = runtime_required_text(
            config.get("api_key"),
            "Active model gateway config is missing api_key",
        )
    return {
        **config,
        "api_key": api_key,
        "base_url": base_url,
        "default_embedding_model": model,
        "embedding_connection_mode": mode,
    }


def model_gateway_embedding_config(current_store: Any) -> dict[str, Any]:
    config = default_model_gateway_config(current_store)
    if config:
        return model_gateway_embedding_runtime_config(config)
    if settings.model_gateway_status == "configured":
        return {
            "api_key": settings.model_gateway_api_key,
            "base_url": settings.model_gateway_base_url,
            "default_embedding_model": settings.model_gateway_default_embedding_model,
            "embedding_connection_mode": "reuse_chat",
            "embedding_dimension": settings.vector_dimension,
            "id": None,
            "provider": "openai_compatible",
            "timeout_seconds": 60,
        }
    raise ModelGatewayConfigError(
        "No active/default model gateway config is configured",
        current_step="model_gateway_config_invalid",
    )


def call_openai_compatible_embeddings(
    current_store: Any,
    *,
    config: dict[str, Any],
    inputs: list[str],
) -> tuple[list[list[float]], dict[str, Any]]:
    provider = config["provider"]
    model = config["default_embedding_model"]
    config_id = config["id"]
    body = {"model": model, "input": inputs}
    request = UrlRequest(
        model_gateway_embeddings_url(config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        embeddings = parse_embedding_response(response_payload, expected_count=len(inputs))
        latency_ms = int((perf_counter() - started) * 1000)
        log = model_gateway_log(
            current_store,
            purpose="knowledge_embedding",
            provider=provider,
            model=model,
            config_id=config_id,
            tokens=openai_embedding_usage_tokens(
                response_payload.get("usage"),
                inputs=inputs,
            ),
            latency_ms=latency_ms,
            status="succeeded",
        )
        return embeddings, log
    except (
        AttributeError,
        HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        prompt_tokens = estimate_tokens(inputs)
        log = model_gateway_log(
            current_store,
            purpose="knowledge_embedding",
            provider=provider,
            model=model,
            config_id=config_id,
            tokens={"prompt": prompt_tokens, "completion": 0, "total": prompt_tokens},
            latency_ms=latency_ms,
            status="failed",
            error="Model gateway embedding request failed",
        )
        raise ModelGatewayCallError(log) from exc


def call_model_gateway_embeddings_with_context(
    current_store: Any,
    inputs: list[str],
) -> tuple[list[list[float]], dict[str, Any]]:
    config = model_gateway_embedding_config(current_store)
    embeddings, _log = call_openai_compatible_embeddings(
        current_store,
        config=config,
        inputs=inputs,
    )
    return embeddings, embedding_context_from_config(config, embeddings)


def test_model_gateway_chat(config: dict[str, Any]) -> dict[str, Any]:
    model = config["default_chat_model"]
    body = {
        "messages": [
            {
                "content": (
                    "Return one compact JSON object with a string field named summary. "
                    "This is an AI Brain model gateway connectivity test."
                ),
                "role": "user",
            }
        ],
        "model": model,
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    request = UrlRequest(
        model_gateway_chat_completions_url(config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Model gateway chat response is missing choices")
        return {
            "latency_ms": int((perf_counter() - started) * 1000),
            "model": model,
            "ok": True,
            "status": "succeeded",
        }
    except (
        AttributeError,
        HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return model_gateway_test_failure(
            error_code="MODEL_GATEWAY_CHAT_FAILED",
            model=model,
            started=started,
        )


def test_model_gateway_embedding(config: dict[str, Any]) -> dict[str, Any]:
    try:
        embedding_config = model_gateway_embedding_runtime_config(config)
    except ModelGatewayConfigError:
        started = perf_counter()
        return model_gateway_test_failure(
            error_code="MODEL_GATEWAY_EMBEDDING_CONFIG_INVALID",
            model=str(config.get("default_embedding_model") or ""),
            started=started,
        )
    model = embedding_config["default_embedding_model"]
    body = {
        "input": ["AI Brain model gateway embedding connectivity test"],
        "model": model,
    }
    request = UrlRequest(
        model_gateway_embeddings_url(embedding_config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {embedding_config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            payload = json.loads(response.read().decode("utf-8"))
        embeddings = parse_embedding_response(payload, expected_count=1)
        return {
            "dimension": len(embeddings[0]),
            "latency_ms": int((perf_counter() - started) * 1000),
            "model": model,
            "ok": True,
            "status": "succeeded",
        }
    except (
        AttributeError,
        HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return model_gateway_test_failure(
            error_code="MODEL_GATEWAY_EMBEDDING_FAILED",
            model=model,
            started=started,
        )
