from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.operational_attribution import (
    create_pending_attribution_item_response,
    list_pending_attribution_items_response,
    resolve_pending_attribution_item_response,
)

router = APIRouter(tags=["attribution"])


class PendingAttributionRequest(BaseModel):
    collector_run_id: str | None = None
    confidence: float | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    raw_subject_id: str | None = None
    source_system: str
    source_type: str
    suggested_module_code: str | None = None
    suggested_product_id: str | None = None
    summary: str


class PendingAttributionResolveRequest(BaseModel):
    resolution_action: str
    resolution_note: str | None = None
    resolved_module_code: str | None = None
    resolved_product_id: str | None = None
    resolved_requirement_id: str | None = None
    resolved_subject_id: str | None = None
    resolved_subject_type: str | None = None


@router.get("/api/attribution/pending-items")
def pending_attribution_items(
    request: Request,
    source_type: str | None = None,
    status: str | None = None,
    resolved_product_id: str | None = None,
    collector_run_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_pending_attribution_items_response(
        collector_run_id=collector_run_id,
        current_store=store(request),
        resolved_product_id=resolved_product_id,
        source_type=source_type,
        status=status,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/attribution/pending-items")
def create_pending_attribution_item(
    payload: PendingAttributionRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    item = create_pending_attribution_item_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(item, get_trace_id(request))


@router.post("/api/attribution/pending-items/{item_id}/resolve")
def resolve_pending_attribution_item(
    item_id: str,
    payload: PendingAttributionResolveRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    item = resolve_pending_attribution_item_response(
        current_store=store(request),
        item_id=item_id,
        payload=payload,
        user=user,
    )
    return envelope(item, get_trace_id(request))
