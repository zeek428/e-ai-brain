from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, api_error, store
from app.core.trace import envelope, get_trace_id
from app.services.external_event_inbox import (
    SUPPORTED_EXTERNAL_EVENT_PROVIDERS,
    list_external_events_response,
    receive_external_event,
    retry_external_event_response,
)

router = APIRouter()


class ExternalEventRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)


@router.post(
    "/api/integrations/webhooks/{provider}/{connection_id}",
    status_code=status.HTTP_202_ACCEPTED,
)
async def external_event_webhook(
    provider: str,
    connection_id: str,
    request: Request,
) -> dict[str, Any]:
    if provider not in SUPPORTED_EXTERNAL_EVENT_PROVIDERS:
        raise api_error(404, "NOT_FOUND", "Webhook provider not found")
    event = receive_external_event(
        store(request),
        body=await request.body(),
        connection_id=connection_id,
        headers=request.headers,
        provider=provider,
    )
    acknowledgement = {
        key: event.get(key)
        for key in (
            "id",
            "provider",
            "event_type",
            "delivery_id",
            "status",
            "duplicate",
            "received_at",
        )
    }
    return envelope(acknowledgement, get_trace_id(request))


@router.get("/api/system/external-events")
def list_external_events(
    request: Request,
    event_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    provider: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_external_events_response(
        current_store=store(request),
        event_type=event_type,
        page=page,
        page_size=page_size,
        provider=provider,
        status=status_filter,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/system/external-events/{event_id}/retry")
def retry_external_event(
    event_id: str,
    payload: ExternalEventRetryRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = retry_external_event_response(
        current_store=store(request),
        event_id=event_id,
        reason=payload.reason,
        user=user,
    )
    return envelope(result, get_trace_id(request))
