from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.operational_records import (
    create_collector_run_response,
    list_collector_runs_response,
    patch_collector_run_response,
)

router = APIRouter(tags=["collectors"])


class CollectorRunRequest(BaseModel):
    collector_type: str
    error_message: str | None = None
    payload_summary: dict[str, Any] = Field(default_factory=dict)
    product_id: str | None = None
    records_imported: int = 0
    source_system: str
    started_at: str | None = None
    status: str = "running"


class CollectorRunPatchRequest(BaseModel):
    error_message: str | None = None
    finished_at: str | None = None
    payload_summary: dict[str, Any] | None = None
    records_imported: int | None = None
    status: str | None = None


@router.get("/api/collectors/runs")
def collector_runs(
    request: Request,
    collector_type: str | None = None,
    product_id: str | None = None,
    status: str | None = None,
    source_system: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_collector_runs_response(
        collector_type=collector_type,
        current_store=store(request),
        product_id=product_id,
        source_system=source_system,
        status=status,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/collectors/runs")
def create_collector_run(
    payload: CollectorRunRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    run = create_collector_run_response(current_store=store(request), payload=payload, user=user)
    return envelope(run, get_trace_id(request))


@router.patch("/api/collectors/runs/{run_id}")
def patch_collector_run(
    run_id: str,
    payload: CollectorRunPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    run = patch_collector_run_response(
        current_store=store(request),
        payload=payload,
        run_id=run_id,
        user=user,
    )
    return envelope(run, get_trace_id(request))
