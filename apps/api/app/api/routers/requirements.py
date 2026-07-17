from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.requirement_batch_operations import (
    batch_advance_requirement_status_result,
    batch_assign_requirement_owner_result,
    batch_generate_requirement_tasks_result,
    batch_schedule_requirements_result,
)
from app.services.requirement_decisions import (
    approve_requirement_result,
    close_requirement_result,
    reject_requirement_result,
)
from app.services.requirement_full_chain import (
    get_requirement_full_chain_response,
    get_requirement_response,
)
from app.services.requirements import (
    create_requirement_result,
    delete_requirement_result,
    generate_requirement_task_result,
    list_requirements_response,
    patch_requirement_result,
    requirement_write_store,
)

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


class RequirementRequest(BaseModel):
    title: str
    product_id: str
    version_id: str | None = None
    module_code: str | None = None
    content: str
    priority: str = "P1"
    source: str = "business_department"
    source_collaboration_run_id: str | None = None
    supersedes_requirement_id: str | None = None


class RequirementPatchRequest(BaseModel):
    title: str | None = None
    product_id: str | None = None
    version_id: str | None = None
    module_code: str | None = None
    content: str | None = None
    priority: str | None = None
    source: str | None = None


class RequirementBatchScheduleRequest(BaseModel):
    product_id: str
    version_id: str
    requirement_ids: list[str] = Field(min_length=1)
    reason: str | None = None


class RequirementBatchAssignOwnerRequest(BaseModel):
    assignee: str
    requirement_ids: list[str] = Field(min_length=1)
    reason: str | None = None


class RequirementBatchAdvanceStatusRequest(BaseModel):
    reason: str | None = None
    requirement_ids: list[str] = Field(min_length=1)
    target_status: str


class RequirementBatchGenerateTasksRequest(BaseModel):
    product_id: str
    requirement_ids: list[str] = Field(min_length=1)
    reason: str | None = None


class RequirementDecisionRequest(BaseModel):
    comment: str | None = None
    rejection_reason: str | None = None


@router.post("")
def create_requirement(
    request: Request,
    payload: RequirementRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    requirement = create_requirement_result(
        current_store=requirement_write_store(store(request)),
        payload=payload,
        user=user,
    )
    return envelope(requirement, get_trace_id(request))


@router.post("/batch-schedule")
def batch_schedule_requirements(
    request: Request,
    payload: RequirementBatchScheduleRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = batch_schedule_requirements_result(
        current_store=requirement_write_store(store(request)),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/batch-assign-owner")
def batch_assign_requirement_owner(
    request: Request,
    payload: RequirementBatchAssignOwnerRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = batch_assign_requirement_owner_result(
        current_store=requirement_write_store(store(request)),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/batch-advance-status")
def batch_advance_requirement_status(
    request: Request,
    payload: RequirementBatchAdvanceStatusRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = batch_advance_requirement_status_result(
        current_store=requirement_write_store(store(request)),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("")
def list_requirements(
    request: Request,
    priority: str | None = None,
    product_id: str | None = None,
    product: str | None = None,
    source: str | None = None,
    status: str | None = None,
    title: str | None = None,
    version: str | None = None,
    version_id: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    started_at = getattr(request.state, "started_at", None)
    payload = list_requirements_response(
        current_store=store(request),
        page=page,
        page_size=page_size,
        priority=priority,
        product=product,
        product_id=product_id,
        source=source,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at if isinstance(started_at, float) else perf_counter(),
        status=status,
        title=title,
        trace_id=get_trace_id(request),
        user=user,
        version=version,
        version_id=version_id,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/{requirement_id}/full-chain")
def get_requirement_full_chain(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = get_requirement_full_chain_response(
        current_store=store(request),
        requirement_id=requirement_id,
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/{requirement_id}")
def get_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    requirement = get_requirement_response(
        current_store=store(request),
        requirement_id=requirement_id,
        user=user,
    )
    return envelope(requirement, get_trace_id(request))


@router.patch("/{requirement_id}")
def patch_requirement(
    requirement_id: str,
    request: Request,
    payload: RequirementPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    requirement = patch_requirement_result(
        current_store=requirement_write_store(store(request)),
        payload=payload,
        requirement_id=requirement_id,
        user=user,
    )
    return envelope(requirement, get_trace_id(request))


@router.delete("/{requirement_id}")
def delete_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = delete_requirement_result(
        current_store=requirement_write_store(store(request)),
        requirement_id=requirement_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/{requirement_id}/approve")
def approve_requirement(
    requirement_id: str,
    request: Request,
    payload: RequirementDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    requirement = approve_requirement_result(
        current_store=requirement_write_store(store(request)),
        payload=payload,
        requirement_id=requirement_id,
        user=user,
    )
    return envelope(requirement, get_trace_id(request))


@router.post("/{requirement_id}/reject")
def reject_requirement(
    requirement_id: str,
    request: Request,
    payload: RequirementDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    requirement = reject_requirement_result(
        current_store=requirement_write_store(store(request)),
        payload=payload,
        requirement_id=requirement_id,
        user=user,
    )
    return envelope(requirement, get_trace_id(request))


@router.post("/{requirement_id}/close")
def close_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    requirement = close_requirement_result(
        current_store=requirement_write_store(store(request)),
        requirement_id=requirement_id,
        user=user,
    )
    return envelope(requirement, get_trace_id(request))


@router.post("/batch-generate-tasks")
def batch_generate_requirement_tasks(
    request: Request,
    payload: RequirementBatchGenerateTasksRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = batch_generate_requirement_tasks_result(
        current_store=requirement_write_store(store(request)),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/{requirement_id}/generate-task")
def generate_task_from_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = generate_requirement_task_result(
        current_store=requirement_write_store(store(request)),
        requirement_id=requirement_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))
