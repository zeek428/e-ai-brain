from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.bug_listing import list_bugs_response
from app.services.bugs import (
    batch_update_bugs_result,
    bug_write_store,
    create_bug_result,
    delete_bug_result,
    patch_bug_result,
)

router = APIRouter(tags=["bugs"])


class BugRequest(BaseModel):
    product_id: str
    version_id: str | None = None
    module_code: str | None = None
    source: str
    title: str
    severity: str
    description: str
    related_task_id: str | None = None
    requirement_id: str | None = None
    reproduce_steps: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    assignee: str | None = None
    duplicate_of_bug_id: str | None = None


class BugPatchRequest(BaseModel):
    status: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None
    assignee: str | None = None
    reproduce_steps: list[str] | None = None
    evidence: dict[str, Any] | None = None
    duplicate_of_bug_id: str | None = None


class BugBatchUpdateRequest(BaseModel):
    bug_ids: list[str] = Field(min_length=1, max_length=100)
    status: str | None = None
    severity: str | None = None
    assignee: str | None = None
    reason: str | None = None


@router.get("/api/bugs")
def list_bugs(
    request: Request,
    module: str | None = None,
    product_id: str | None = None,
    version_id: str | None = None,
    version: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    title: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = list_bugs_response(
        current_store=store(request),
        module=module,
        page=page,
        page_size=page_size,
        product_id=product_id,
        severity=severity,
        sort_by=sort_by,
        sort_order=sort_order,
        source=source,
        started_at=perf_counter(),
        status=status,
        title=title,
        trace_id=get_trace_id(request),
        version=version,
        version_id=version_id,
    )
    return envelope(payload, get_trace_id(request))


@router.post("/api/bugs")
def create_bug(
    request: Request,
    payload: BugRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    bug = create_bug_result(
        current_store=bug_write_store(store(request)),
        payload=payload,
        user=user,
    )
    return envelope(bug, get_trace_id(request))


@router.post("/api/bugs/batch-update")
def batch_update_bugs(
    request: Request,
    payload: BugBatchUpdateRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = batch_update_bugs_result(
        current_store=bug_write_store(store(request)),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.patch("/api/bugs/{bug_id}")
def patch_bug(
    bug_id: str,
    request: Request,
    payload: BugPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    bug = patch_bug_result(
        bug_id=bug_id,
        current_store=bug_write_store(store(request)),
        payload=payload,
        user=user,
    )
    return envelope(bug, get_trace_id(request))


@router.delete("/api/bugs/{bug_id}")
def delete_bug(
    bug_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = delete_bug_result(
        bug_id=bug_id,
        current_store=bug_write_store(store(request)),
        user=user,
    )
    return envelope(result, get_trace_id(request))
