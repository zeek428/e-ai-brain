from __future__ import annotations

from typing import Any
from urllib.request import urlopen

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, api_error, require_roles, store
from app.core.config import get_settings
from app.core.trace import envelope, get_trace_id
from app.services.assistant_chat import (
    ASSISTANT_ACCESS_ROLES,
    AssistantChatRequest,
    AssistantServiceError,
    assistant_chat_response,
    assistant_conversation_messages_response,
    assistant_conversations_response,
    assistant_request_store,
)

settings = get_settings()
router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.get("/conversations")
def list_assistant_conversations(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_conversations_response(store(request), user_id=user["id"])
    return envelope(payload, get_trace_id(request))


@router.get("/conversations/{conversation_id}/messages")
def list_assistant_conversation_messages(
    conversation_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    try:
        payload = assistant_conversation_messages_response(
            store(request),
            conversation_id=conversation_id,
            user_id=user["id"],
        )
    except AssistantServiceError as exc:
        raise api_error(exc.status_code, exc.code, exc.message) from exc
    return envelope(payload, get_trace_id(request))


@router.post("/chat")
def chat_with_assistant(
    request: Request,
    payload: AssistantChatRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    current_store = assistant_request_store(store(request), user_id=user["id"])
    try:
        response_payload = assistant_chat_response(
            current_store,
            model_gateway_api_key=settings.model_gateway_api_key,
            model_gateway_base_url=settings.model_gateway_base_url,
            model_gateway_default_chat_model=settings.model_gateway_default_chat_model,
            model_gateway_status=settings.model_gateway_status,
            payload=payload,
            urlopen_func=urlopen,
            user=user,
        )
    except AssistantServiceError as exc:
        raise api_error(exc.status_code, exc.code, exc.message) from exc
    return envelope(response_payload, get_trace_id(request))
