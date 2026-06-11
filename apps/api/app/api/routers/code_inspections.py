from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.code_inspections import (
    code_inspection_detail_response,
    list_code_inspection_reports_response,
)

router = APIRouter(tags=["code-inspections"])


@router.get("/api/governance/code-inspections")
def list_code_inspections(
    request: Request,
    committer: str | None = None,
    product_id: str | None = None,
    repository_id: str | None = None,
    risk_level: str | None = None,
    status: str | None = None,
    title: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = list_code_inspection_reports_response(
        committer=committer,
        current_store=store(request),
        page=page,
        page_size=page_size,
        product_id=product_id,
        repository_id=repository_id,
        risk_level=risk_level,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=perf_counter(),
        status=status,
        title=title,
        trace_id=get_trace_id(request),
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/api/governance/code-inspections/{report_id}")
def get_code_inspection_detail(
    report_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        code_inspection_detail_response(
            current_store=store(request),
            report_id=report_id,
            user=user,
        ),
        get_trace_id(request),
    )
