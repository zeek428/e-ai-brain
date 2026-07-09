from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.api.deps import CurrentUser, require_permissions, store
from app.core.trace import get_trace_id
from app.services.audit_events import audit_events_response

router = APIRouter(tags=["audit"])
AUDIT_READ_PERMISSION = "audit.read"


def _request_started_at(request: Request) -> float | None:
    started_at = getattr(request.state, "started_at", None)
    return started_at if isinstance(started_at, float) else None


@router.get("/api/audit/events")
def audit_events(
    request: Request,
    ai_task_id: str | None = None,
    actor: str | None = None,
    actor_id: str | None = None,
    subject: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    event_type: str | None = None,
    result: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {AUDIT_READ_PERMISSION})
    return audit_events_response(
        store(request),
        actor=actor,
        actor_id=actor_id,
        ai_task_id=ai_task_id,
        created_from=created_from,
        created_to=created_to,
        event_type=event_type,
        page=page,
        page_size=page_size,
        result=result,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=_request_started_at(request),
        subject=subject,
        subject_id=subject_id,
        subject_type=subject_type,
        trace_id=get_trace_id(request),
    )


@router.get("/api/audit/events/export")
def export_audit_events(
    request: Request,
    ai_task_id: str | None = None,
    actor: str | None = None,
    actor_id: str | None = None,
    subject: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    event_type: str | None = None,
    result: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> Response:
    require_permissions(user, {AUDIT_READ_PERMISSION})
    payload = audit_events_response(
        store(request),
        actor=actor,
        actor_id=actor_id,
        ai_task_id=ai_task_id,
        created_from=created_from,
        created_to=created_to,
        event_type=event_type,
        page=1,
        page_size=1000,
        result=result,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=_request_started_at(request),
        subject=subject,
        subject_id=subject_id,
        subject_type=subject_type,
        trace_id=get_trace_id(request),
    )
    data = payload.get("data") if isinstance(payload, dict) else {}
    items = data.get("items") if isinstance(data, dict) else []
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "sequence",
            "created_at",
            "actor_id",
            "event_type",
            "subject_type",
            "subject_id",
            "ai_task_id",
            "result",
            "trace_id",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    for item in items or []:
        if isinstance(item, dict):
            writer.writerow(item)
    return Response(
        content=output.getvalue(),
        headers={"Content-Disposition": "attachment; filename=ai-brain-audit-events.csv"},
        media_type="text/csv; charset=utf-8",
    )
