from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.task_batch_operations import (
    batch_cancel_ai_tasks_response,
    batch_retry_ai_tasks_response,
)
from app.services.task_creation import create_ai_task_response
from app.services.task_listing import list_ai_tasks_response
from app.services.task_read_details import (
    get_ai_task_response,
    get_review_response,
    list_graph_runs_response,
    pending_reviews_response,
)
from app.services.task_review_decisions import (
    approve_review_response,
    edit_approve_review_response,
)
from app.services.task_start_execution import start_ai_task_response
from app.services.task_state_transitions import (
    cancel_ai_task_response,
    reject_review_response,
    request_more_info_review_response,
    submit_more_info_response,
)

router = APIRouter(tags=["tasks"])


class AiTaskRequest(BaseModel):
    task_type: str
    title: str
    requirement_id: str
    input: dict[str, Any] = Field(default_factory=dict)


class MoreInfoRequest(BaseModel):
    answers: list[dict[str, str]] = Field(default_factory=list)


class BatchCancelAiTasksRequest(BaseModel):
    task_ids: list[str] = Field(min_length=1)
    reason: str | None = None


class BatchRetryAiTasksRequest(BaseModel):
    task_ids: list[str] = Field(min_length=1)
    reason: str | None = None


class ReviewDecisionRequest(BaseModel):
    version: int
    edited_content: dict[str, Any] | None = None
    decision_reason: str | None = None
    questions: list[str] = Field(default_factory=list)


@router.get("/api/ai-tasks")
def list_ai_tasks(
    request: Request,
    status: str | None = None,
    task_type: str | None = None,
    product_id: str | None = None,
    requirement_id: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    keyword: str | None = None,
    created_by: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    started_at = getattr(request.state, "started_at", None)
    payload = list_ai_tasks_response(
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
        current_store=store(request),
        keyword=keyword,
        page=page,
        page_size=page_size,
        product_id=product_id,
        requirement_id=requirement_id,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at if isinstance(started_at, float) else perf_counter(),
        status=status,
        task_type=task_type,
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.post("/api/ai-tasks")
def create_ai_task(
    request: Request,
    payload: AiTaskRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = create_ai_task_response(
        current_store=store(request),
        input_payload=payload.input,
        requirement_id=payload.requirement_id,
        task_type=payload.task_type,
        title=payload.title,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/ai-tasks/batch-cancel")
def batch_cancel_ai_tasks(
    request: Request,
    payload: BatchCancelAiTasksRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = batch_cancel_ai_tasks_response(
        current_store=store(request),
        reason=payload.reason,
        task_ids=payload.task_ids,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/ai-tasks/batch-retry")
def batch_retry_ai_tasks(
    request: Request,
    payload: BatchRetryAiTasksRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = batch_retry_ai_tasks_response(
        code_review_executor=getattr(request.app.state, "code_review_executor", None),
        current_store=store(request),
        reason=payload.reason,
        task_ids=payload.task_ids,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/ai-tasks/{task_id}/start")
def start_ai_task(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = start_ai_task_response(
        code_review_executor=getattr(request.app.state, "code_review_executor", None),
        current_store=store(request),
        task_id=task_id,
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/api/ai-tasks/{task_id}")
def get_ai_task(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = get_ai_task_response(
        current_store=store(request),
        task_id=task_id,
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.post("/api/ai-tasks/{task_id}/cancel")
def cancel_ai_task(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = cancel_ai_task_response(
        current_store=store(request),
        task_id=task_id,
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.post("/api/ai-tasks/{task_id}/more-info")
def submit_more_info(
    task_id: str,
    request: Request,
    payload: MoreInfoRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = submit_more_info_response(
        answers=payload.answers,
        current_store=store(request),
        task_id=task_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/graph-runs")
def list_graph_runs(
    request: Request,
    ai_task_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = list_graph_runs_response(
        ai_task_id=ai_task_id,
        current_store=store(request),
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/api/reviews/pending")
def pending_reviews(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = pending_reviews_response(current_store=store(request), user=user)
    return envelope(payload, get_trace_id(request))


@router.get("/api/reviews/{review_id}")
def get_review(
    review_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    payload = get_review_response(
        current_store=store(request),
        review_id=review_id,
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.post("/api/reviews/{review_id}/approve")
def approve_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = approve_review_response(
        current_store=store(request),
        review_id=review_id,
        user=user,
        version=payload.version,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/reviews/{review_id}/edit-approve")
def edit_approve_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = edit_approve_review_response(
        current_store=store(request),
        edited_content=payload.edited_content,
        review_id=review_id,
        user=user,
        version=payload.version,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/reviews/{review_id}/reject")
def reject_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = reject_review_response(
        current_store=store(request),
        decision_reason=payload.decision_reason,
        review_id=review_id,
        user=user,
        version=payload.version,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/reviews/{review_id}/request-more-info")
def request_more_info_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = request_more_info_review_response(
        current_store=store(request),
        questions=payload.questions,
        review_id=review_id,
        user=user,
        version=payload.version,
    )
    return envelope(result, get_trace_id(request))
