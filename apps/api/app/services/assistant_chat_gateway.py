from __future__ import annotations

import json
import threading
from collections.abc import Callable
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen as default_urlopen

import httpx

from app.core.store import MemoryStore
from app.services.assistant_chat_intents import (
    merge_assistant_references as _merge_assistant_references,
)
from app.services.assistant_context import (
    assistant_chat_messages as assistant_context_chat_messages,
)
from app.services.assistant_context import (
    assistant_conversation_history_context,
    assistant_reference_candidates,
    assistant_response_content,
    build_assistant_system_context,
)
from app.services.assistant_errors import AssistantServiceError
from app.services.assistant_references import (
    AssistantReferenceError,
    resolve_assistant_references,
)
from app.services.assistant_tools import assistant_tool_results
from app.services.model_gateway_logging import (
    estimate_tokens,
    model_gateway_log,
    openai_usage_tokens,
)

ASSISTANT_GATEWAY_RUN_POLL_SECONDS = 0.05

_ASSISTANT_CHAT_RUN_INTERRUPTERS: dict[str, Callable[[], None]] = {}
_ASSISTANT_CHAT_RUN_INTERRUPTERS_LOCK = threading.Lock()


class AssistantGatewayRequestFailed(Exception):
    def __init__(self, log: dict[str, Any]):
        super().__init__("Assistant model gateway request failed")
        self.log = log


class AssistantGatewayRequestCancelled(Exception):
    pass


def call_model_gateway_for_assistant_chat(
    current_store: MemoryStore,
    *,
    model_gateway_api_key: str,
    model_gateway_base_url: str,
    model_gateway_default_chat_model: str,
    model_gateway_status: str,
    payload: Any,
    urlopen_func: Callable[[Any, int], Any],
    user: dict[str, Any],
    cancel_checker: Callable[[], bool] | None = None,
    run_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = _assistant_model_gateway_config(
        current_store,
        model_gateway_api_key=model_gateway_api_key,
        model_gateway_base_url=model_gateway_base_url,
        model_gateway_default_chat_model=model_gateway_default_chat_model,
        model_gateway_status=model_gateway_status,
    )
    provider = config["provider"]
    model = config["default_chat_model"]
    try:
        resolved_references = resolve_assistant_references(
            current_store,
            references=payload.references,
            user=user,
        )
    except AssistantReferenceError as exc:
        raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
    tool_results = assistant_tool_results(
        current_store,
        message=payload.message,
        product_id=payload.product_id,
        references=resolved_references["items"],
    )
    messages = _assistant_chat_messages(
        current_store,
        model_gateway_status=model_gateway_status,
        payload=payload,
        resolved_references=resolved_references,
        tool_results=tool_results,
        user=user,
    )
    body = {
        "messages": messages,
        "model": model,
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    request = UrlRequest(
        _model_gateway_chat_completions_url(config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        response_payload = _read_model_gateway_response_payload(
            request,
            cancel_checker=cancel_checker,
            run_id=run_id,
            timeout_seconds=int(config.get("timeout_seconds") or 60),
            urlopen_func=urlopen_func,
        )
        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Assistant response is missing choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise ValueError("Assistant response is missing message")
        assistant_output = assistant_response_content(message.get("content"))
        if not assistant_output["answer"]:
            raise ValueError("Assistant response is missing answer")
        references = _merge_assistant_references(
            resolved_references["items"],
            assistant_output.get("references") or [],
            [
                reference
                for tool_result in tool_results
                for reference in tool_result.get("references", [])
            ],
            assistant_reference_candidates(
                current_store,
                message=payload.message,
                product_id=payload.product_id,
                user=user,
            ),
        )
        assistant_output["references"] = references
        assistant_output["selected_references"] = resolved_references["items"]
        assistant_output["tool_results"] = tool_results
        latency_ms = int((perf_counter() - started) * 1000)
        log = model_gateway_log(
            current_store,
            purpose="assistant_chat",
            provider=provider,
            model=model,
            config_id=config["id"],
            tokens=openai_usage_tokens(
                response_payload.get("usage"),
                messages=messages,
                output=assistant_output,
            ),
            latency_ms=latency_ms,
            status="succeeded",
        )
        return {**assistant_output, "latency_ms": latency_ms, "model": model}, log
    except (
        AttributeError,
        HTTPError,
        httpx.HTTPError,
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
            purpose="assistant_chat",
            provider=provider,
            model=model,
            config_id=config["id"],
            tokens={"prompt": prompt_tokens, "completion": 0, "total": prompt_tokens},
            latency_ms=latency_ms,
            status="failed",
            error="Assistant model gateway request failed",
        )
        raise AssistantGatewayRequestFailed(log) from exc


def interrupt_assistant_chat_gateway_run(run_id: str | None) -> None:
    _interrupt_assistant_chat_run(run_id)


def _default_model_gateway_config(current_store: MemoryStore) -> dict[str, Any] | None:
    for item in _read_memory_dict(current_store, "model_gateway_configs").values():
        if item.get("is_default") and item.get("status") == "active":
            return item
    return None


def _assistant_model_gateway_config(
    current_store: MemoryStore,
    *,
    model_gateway_api_key: str,
    model_gateway_base_url: str,
    model_gateway_default_chat_model: str,
    model_gateway_status: str,
) -> dict[str, Any]:
    config = _default_model_gateway_config(current_store)
    if config:
        if config.get("provider") != "openai_compatible":
            raise AssistantServiceError(
                400,
                "MODEL_GATEWAY_CONFIG_INVALID",
                "Active model gateway provider is not supported",
            )
        if not config.get("api_key"):
            raise AssistantServiceError(
                400,
                "MODEL_GATEWAY_CONFIG_INVALID",
                "Active model gateway config is missing api_key",
            )
        return config
    if model_gateway_status == "configured":
        return {
            "api_key": model_gateway_api_key,
            "base_url": model_gateway_base_url,
            "default_chat_model": model_gateway_default_chat_model,
            "id": None,
            "provider": "openai_compatible",
            "timeout_seconds": 60,
        }
    raise AssistantServiceError(
        400,
        "MODEL_GATEWAY_CONFIG_INVALID",
        "No active/default model gateway config is configured",
    )


def _assistant_chat_messages(
    current_store: MemoryStore,
    *,
    model_gateway_status: str,
    payload: Any,
    resolved_references: dict[str, Any],
    tool_results: list[dict[str, Any]],
    user: dict[str, Any],
) -> list[dict[str, str]]:
    default_gateway = _default_model_gateway_config(current_store)
    system_context = build_assistant_system_context(
        current_store,
        default_gateway=default_gateway,
        model_gateway_status=model_gateway_status,
        product_id=payload.product_id,
    )
    system_context["tool_results"] = tool_results
    system_context["selected_references"] = resolved_references["items"]
    system_context["knowledge_context"] = resolved_references["knowledge_context"]
    system_context["reference_candidates"] = assistant_reference_candidates(
        current_store,
        message=payload.message,
        product_id=payload.product_id,
        user=user,
    )
    system_context["reference_candidates"] = _merge_assistant_references(
        resolved_references["items"],
        [
            reference
            for tool_result in tool_results
            for reference in tool_result.get("references", [])
        ],
        system_context["reference_candidates"],
    )
    return assistant_context_chat_messages(
        conversation_history=assistant_conversation_history_context(
            current_store,
            conversation_id=payload.conversation_id,
        ),
        context=payload.context,
        conversation_id=payload.conversation_id,
        message=payload.message,
        product_id=payload.product_id,
        system_context=system_context,
    )


def _read_model_gateway_response_payload(
    request: UrlRequest,
    *,
    cancel_checker: Callable[[], bool] | None,
    run_id: str | None,
    timeout_seconds: int,
    urlopen_func: Callable[[Any, int], Any],
) -> dict[str, Any]:
    if cancel_checker is not None and cancel_checker():
        raise AssistantGatewayRequestCancelled()
    result: dict[str, Any] = {}
    done = threading.Event()

    def request_worker() -> None:
        try:
            if urlopen_func is default_urlopen:
                result["payload"] = _read_model_gateway_response_payload_with_httpx(
                    request,
                    run_id=run_id,
                    timeout_seconds=timeout_seconds,
                )
            else:
                with urlopen_func(request, timeout=timeout_seconds) as response:
                    result["payload"] = json.loads(response.read().decode("utf-8"))
        except BaseException as exc:
            result["error"] = exc
        finally:
            done.set()

    thread = threading.Thread(
        target=request_worker,
        name=f"assistant-chat-gateway-{run_id or 'request'}",
        daemon=True,
    )
    thread.start()
    while not done.wait(ASSISTANT_GATEWAY_RUN_POLL_SECONDS):
        if cancel_checker is not None and cancel_checker():
            _interrupt_assistant_chat_run(run_id)
            raise AssistantGatewayRequestCancelled()
    if cancel_checker is not None and cancel_checker():
        raise AssistantGatewayRequestCancelled()
    error = result.get("error")
    if error is not None:
        raise error
    payload = result.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Assistant response is missing payload")
    return payload


def _read_model_gateway_response_payload_with_httpx(
    request: UrlRequest,
    *,
    run_id: str | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    client = httpx.Client(timeout=timeout_seconds)

    def close_client() -> None:
        client.close()

    _register_assistant_chat_run_interrupter(run_id, close_client)
    try:
        response = client.request(
            request.get_method(),
            request.full_url,
            content=request.data,
            headers=dict(request.header_items()),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Assistant response is missing payload")
        return payload
    finally:
        _unregister_assistant_chat_run_interrupter(run_id, close_client)
        client.close()


def _register_assistant_chat_run_interrupter(
    run_id: str | None,
    interrupter: Callable[[], None],
) -> None:
    if not run_id:
        return
    with _ASSISTANT_CHAT_RUN_INTERRUPTERS_LOCK:
        _ASSISTANT_CHAT_RUN_INTERRUPTERS[run_id] = interrupter


def _unregister_assistant_chat_run_interrupter(
    run_id: str | None,
    interrupter: Callable[[], None],
) -> None:
    if not run_id:
        return
    with _ASSISTANT_CHAT_RUN_INTERRUPTERS_LOCK:
        if _ASSISTANT_CHAT_RUN_INTERRUPTERS.get(run_id) is interrupter:
            _ASSISTANT_CHAT_RUN_INTERRUPTERS.pop(run_id, None)


def _interrupt_assistant_chat_run(run_id: str | None) -> None:
    if not run_id:
        return
    with _ASSISTANT_CHAT_RUN_INTERRUPTERS_LOCK:
        interrupter = _ASSISTANT_CHAT_RUN_INTERRUPTERS.get(run_id)
    if interrupter is None:
        return
    try:
        interrupter()
    except Exception:
        return


def _model_gateway_chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, Any]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}
