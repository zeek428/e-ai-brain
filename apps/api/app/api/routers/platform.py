from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, store
from app.core.config import get_settings
from app.core.trace import envelope, get_trace_id
from app.services.platform_status import health_payload, long_memory_status_payload

settings = get_settings()
router = APIRouter(tags=["platform"])


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    return health_payload(
        current_store=store(request),
        settings=settings,
        trace_id=get_trace_id(request),
    )


@router.get("/api/long-memory/status")
def get_long_memory_status(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(long_memory_status_payload(settings), get_trace_id(request))
