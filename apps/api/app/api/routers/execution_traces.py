from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUser, require_permissions, store
from app.core.trace import envelope, get_trace_id
from app.services.execution_traces import (
    get_execution_trace_response,
    list_execution_traces_response,
)

router = APIRouter(tags=["execution-traces"])


def _request_started_at(request: Request) -> float | None:
    started_at = getattr(request.state, "started_at", None)
    return started_at if isinstance(started_at, float) else None


@router.get("/api/governance/execution-traces")
def list_execution_traces(
    request: Request,
    created_from: str | None = None,
    created_to: str | None = None,
    keyword: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    source_id: str | None = None,
    source_type: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"diagnostics.execution_traces.read"})
    return list_execution_traces_response(
        created_from=created_from,
        created_to=created_to,
        current_store=store(request),
        keyword=keyword,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        source_id=source_id,
        source_type=source_type,
        started_at=_request_started_at(request),
        status=status,
        trace_id=get_trace_id(request),
    )


@router.get("/api/governance/execution-traces/{trace_id}")
def get_execution_trace(
    request: Request,
    trace_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"diagnostics.execution_traces.read"})
    return envelope(
        get_execution_trace_response(current_store=store(request), trace_id=trace_id),
        get_trace_id(request),
    )
