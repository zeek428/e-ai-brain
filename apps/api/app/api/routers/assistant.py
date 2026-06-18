from __future__ import annotations

from typing import Any
from urllib.request import urlopen

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, api_error, require_roles, store
from app.core.config import get_settings
from app.core.trace import envelope, get_trace_id
from app.services.assistant_action_drafts import (
    cancel_assistant_action_draft_response,
    confirm_assistant_action_draft_response,
    create_assistant_action_draft_response,
    get_assistant_action_draft_response,
    mark_assistant_action_draft_modified_response,
)
from app.services.assistant_chat import (
    ASSISTANT_ACCESS_ROLES,
    AssistantChatRequest,
    AssistantServiceError,
    assistant_chat_response,
    assistant_conversation_messages_response,
    assistant_conversations_response,
    assistant_request_store,
)
from app.services.assistant_draft_templates import list_assistant_draft_templates_response
from app.services.assistant_metrics import assistant_metrics_response
from app.services.assistant_references import (
    AssistantReferenceError,
    assistant_reference_candidates_response,
    resolve_assistant_references,
)
from app.services.assistant_role_quick_tasks import list_assistant_role_quick_tasks_response

settings = get_settings()
router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AssistantReferenceItem(BaseModel):
    id: str
    type: str


class AssistantReferenceResolveRequest(BaseModel):
    references: list[AssistantReferenceItem] = Field(default_factory=list)


class AssistantActionDraftRequest(BaseModel):
    action: str
    client_draft_id: str | None = None
    expires_at: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    source_message_id: str | None = None
    title: str


class AssistantActionDraftCancelRequest(BaseModel):
    reason: str | None = None


class AssistantActionDraftModificationRequest(BaseModel):
    modified_fields: list[str] = Field(default_factory=list)
    user_modified: bool = True


@router.get("/conversations")
def list_assistant_conversations(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_conversations_response(store(request), user_id=user["id"])
    return envelope(payload, get_trace_id(request))


@router.post("/action-drafts")
def create_assistant_action_draft(
    request: Request,
    payload: AssistantActionDraftRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = create_assistant_action_draft_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/action-drafts/{draft_id}")
def get_assistant_action_draft(
    draft_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = get_assistant_action_draft_response(
        current_store=store(request),
        draft_id=draft_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/action-drafts/{draft_id}/confirm")
def confirm_assistant_action_draft(
    draft_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = confirm_assistant_action_draft_response(
        current_store=store(request),
        draft_id=draft_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/action-drafts/{draft_id}/cancel")
def cancel_assistant_action_draft(
    draft_id: str,
    request: Request,
    payload: AssistantActionDraftCancelRequest | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = cancel_assistant_action_draft_response(
        current_store=store(request),
        draft_id=draft_id,
        reason=payload.reason if payload else None,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/action-drafts/{draft_id}/modification")
def mark_assistant_action_draft_modified(
    draft_id: str,
    request: Request,
    payload: AssistantActionDraftModificationRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = mark_assistant_action_draft_modified_response(
        current_store=store(request),
        draft_id=draft_id,
        modified_fields=payload.modified_fields,
        user=user,
        user_modified=payload.user_modified,
    )
    return envelope(result, get_trace_id(request))


@router.get("/metrics")
def assistant_metrics(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_metrics_response(
        assistant_request_store(store(request), user_id=user["id"]),
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/draft-templates")
def list_assistant_draft_templates(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = list_assistant_draft_templates_response(user=user)
    return envelope(payload, get_trace_id(request))


@router.get("/role-quick-tasks")
def list_assistant_role_quick_tasks(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = list_assistant_role_quick_tasks_response(user=user)
    return envelope(payload, get_trace_id(request))


@router.get("/reference-candidates")
def list_assistant_reference_candidates(
    request: Request,
    query: str = "",
    product_id: str | None = None,
    reference_type: str | None = Query(default=None, alias="type"),
    limit: int = Query(default=8, ge=1, le=20),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_reference_candidates_response(
        assistant_request_store(store(request), user_id=user["id"]),
        limit=limit,
        message=query,
        product_id=product_id,
        reference_type=reference_type,
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.post("/references/resolve")
def resolve_assistant_reference_items(
    request: Request,
    payload: AssistantReferenceResolveRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    try:
        result = resolve_assistant_references(
            assistant_request_store(store(request), user_id=user["id"]),
            references=[item.model_dump() for item in payload.references],
            user=user,
        )
    except AssistantReferenceError as exc:
        raise api_error(exc.status_code, exc.code, exc.message) from exc
    return envelope(result, get_trace_id(request))


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
