from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen as default_urlopen

from pydantic import BaseModel, Field

from app.core.store import MemoryStore
from app.services.assistant_action_drafts import (
    persist_assistant_action_drafts_from_tool_results,
)
from app.services.assistant_context import (
    assistant_chat_messages as assistant_context_chat_messages,
)
from app.services.assistant_context import (
    assistant_reference_candidates,
    assistant_response_content,
    build_assistant_system_context,
    public_assistant_message,
)
from app.services.assistant_errors import AssistantServiceError
from app.services.assistant_history import (
    append_assistant_message,
    assistant_conversation_messages_response,
    assistant_conversations_response,
    ensure_assistant_conversation,
)
from app.services.assistant_references import (
    AssistantReferenceError,
    resolve_assistant_references,
)
from app.services.assistant_request_context import (
    assistant_request_store as assistant_context_request_store,
)
from app.services.assistant_request_context import (
    save_assistant_chat_records,
)
from app.services.assistant_tools import assistant_tool_results
from app.services.model_gateway_logging import (
    estimate_tokens,
    model_gateway_log,
    openai_usage_tokens,
)

ASSISTANT_ACCESS_ROLES = {
    "admin",
    "knowledge_owner",
    "product_owner",
    "rd_owner",
    "reviewer",
}

__all__ = [
    "ASSISTANT_ACCESS_ROLES",
    "AssistantChatRequest",
    "AssistantServiceError",
    "assistant_chat_response",
    "assistant_conversation_messages_response",
    "assistant_conversations_response",
    "assistant_request_store",
]


class AssistantChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    product_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    references: list[dict[str, Any]] = Field(default_factory=list)


class _AssistantGatewayRequestFailed(Exception):
    def __init__(self, log: dict[str, Any]):
        super().__init__("Assistant model gateway request failed")
        self.log = log


def assistant_request_store(current_store: MemoryStore, *, user_id: str) -> Any:
    return assistant_context_request_store(current_store, user_id=user_id)


def assistant_chat_response(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
    model_gateway_api_key: str,
    model_gateway_base_url: str,
    model_gateway_default_chat_model: str,
    model_gateway_status: str,
    urlopen_func: Callable[[Any, int], Any] = default_urlopen,
) -> dict[str, Any]:
    message = _ensure_non_blank(payload.message, "message")
    normalized_payload = AssistantChatRequest(
        context=payload.context,
        conversation_id=payload.conversation_id,
        message=message,
        product_id=payload.product_id,
        references=payload.references,
    )
    if (
        normalized_payload.product_id
        and normalized_payload.product_id not in current_store.products
    ):
        raise AssistantServiceError(404, "NOT_FOUND", "Product not found")
    if normalized_payload.conversation_id:
        existing_conversation = current_store.assistant_conversations.get(
            normalized_payload.conversation_id,
        )
        if existing_conversation is not None and existing_conversation.get("user_id") != user["id"]:
            raise AssistantServiceError(404, "NOT_FOUND", "Assistant conversation not found")

    audit_start_index = len(current_store.audit_events)
    try:
        assistant_output, model_log = _call_model_gateway_for_assistant_chat(
            current_store,
            model_gateway_api_key=model_gateway_api_key,
            model_gateway_base_url=model_gateway_base_url,
            model_gateway_default_chat_model=model_gateway_default_chat_model,
            model_gateway_status=model_gateway_status,
            payload=normalized_payload,
            urlopen_func=urlopen_func,
            user=user,
        )
    except AssistantServiceError:
        raise
    except _AssistantGatewayRequestFailed as exc:
        current_store.audit(
            event_type="model_gateway.called",
            actor_id="system",
            subject_type="model_gateway_log",
            subject_id=exc.log["id"],
            payload={
                "model_log_id": exc.log["id"],
                "model": exc.log["model"],
                "provider": exc.log["provider"],
                "purpose": exc.log["purpose"],
                "status": exc.log["status"],
            },
        )
        save_assistant_chat_records(
            current_store,
            conversation=None,
            messages=[],
            model_log=exc.log,
            audit_events=current_store.audit_events[audit_start_index:],
        )
        raise AssistantServiceError(
            502,
            "ASSISTANT_CHAT_FAILED",
            "Assistant model gateway request failed",
        ) from exc

    current_store.audit(
        event_type="model_gateway.called",
        actor_id="system",
        subject_type="model_gateway_log",
        subject_id=model_log["id"],
        payload={
            "model_log_id": model_log["id"],
            "model": model_log["model"],
            "provider": model_log["provider"],
            "purpose": model_log["purpose"],
            "status": model_log["status"],
        },
    )
    now = datetime.now(UTC).isoformat()
    conversation = ensure_assistant_conversation(
        current_store,
        conversation_id=normalized_payload.conversation_id,
        message=message,
        now=now,
        product_id=normalized_payload.product_id,
        user=user,
    )
    user_message = append_assistant_message(
        current_store,
        content=message,
        conversation=conversation,
        now=now,
        references=assistant_output.get("selected_references") or [],
        role="user",
        user_id=user["id"],
    )
    assistant_message = append_assistant_message(
        current_store,
        content=assistant_output["answer"],
        conversation=conversation,
        model=assistant_output["model"],
        now=now,
        references=assistant_output["references"],
        role="assistant",
        suggestions=assistant_output["suggestions"],
        tool_results=assistant_output["tool_results"],
        user_id=user["id"],
    )
    assistant_output["tool_results"] = persist_assistant_action_drafts_from_tool_results(
        current_store,
        source_message_id=assistant_message["id"],
        tool_results=assistant_output["tool_results"],
        user=user,
    )
    assistant_message["metadata_json"]["tool_results"] = assistant_output["tool_results"]
    current_store.audit(
        event_type="assistant.chat_completed",
        actor_id=user["id"],
        subject_type="assistant_conversation",
        subject_id=conversation["id"],
        payload={
            "latency_ms": assistant_output["latency_ms"],
            "model": assistant_output["model"],
            "model_log_id": model_log["id"],
            "product_id": normalized_payload.product_id,
            "reference_count": len(assistant_output["references"]),
            "suggestion_count": len(assistant_output["suggestions"]),
            "tool_count": len(assistant_output["tool_results"]),
        },
    )
    save_assistant_chat_records(
        current_store,
        conversation=conversation,
        messages=[user_message, assistant_message],
        model_log=model_log,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return {
        "conversation_id": conversation["id"],
        "latency_ms": assistant_output["latency_ms"],
        "message": public_assistant_message(assistant_message),
        "model": assistant_output["model"],
        "suggestions": assistant_output["suggestions"],
    }


def _default_model_gateway_config(current_store: MemoryStore) -> dict[str, Any] | None:
    for item in current_store.model_gateway_configs.values():
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
    payload: AssistantChatRequest,
    resolved_references: dict[str, Any],
    tool_results: list[dict[str, Any]],
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
        context=payload.context,
        conversation_id=payload.conversation_id,
        message=payload.message,
        product_id=payload.product_id,
        system_context=system_context,
    )


def _call_model_gateway_for_assistant_chat(
    current_store: MemoryStore,
    *,
    model_gateway_api_key: str,
    model_gateway_base_url: str,
    model_gateway_default_chat_model: str,
    model_gateway_status: str,
    payload: AssistantChatRequest,
    urlopen_func: Callable[[Any, int], Any],
    user: dict[str, Any],
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
    tool_results = assistant_tool_results(
        current_store,
        message=payload.message,
        product_id=payload.product_id,
    )
    try:
        resolved_references = resolve_assistant_references(
            current_store,
            references=payload.references,
            user=user,
        )
    except AssistantReferenceError as exc:
        raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
    messages = _assistant_chat_messages(
        current_store,
        model_gateway_status=model_gateway_status,
        payload=payload,
        resolved_references=resolved_references,
        tool_results=tool_results,
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
        with urlopen_func(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
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
        raise _AssistantGatewayRequestFailed(log) from exc


def _model_gateway_chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _merge_assistant_references(
    *reference_lists: list[dict[str, str]],
) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for reference_list in reference_lists:
        for reference in reference_list:
            key = (str(reference.get("type")), str(reference.get("id")))
            if key in seen:
                continue
            if not all(reference.get(field) for field in ("id", "title", "type", "url")):
                continue
            seen.add(key)
            references.append(reference)
            if len(references) >= 6:
                return references
    return references


def _ensure_non_blank(value: str | None, field: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise AssistantServiceError(400, "VALIDATION_ERROR", f"{field} is required")
    return normalized
