from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.iteration_planning import (
    create_iteration_suggestions_response,
    decide_iteration_suggestion_response,
    list_iteration_suggestions_response,
)
from app.services.user_feedback import (
    convert_user_feedback_to_requirement_response,
    create_user_feedback_response,
    list_user_feedback_response,
    patch_user_feedback_response,
)
from app.services.user_insights import (
    list_user_insight_items_response,
)
from app.services.user_usage_metrics import (
    create_usage_metric_response,
    list_usage_metrics_response,
)

router = APIRouter(tags=["user-insights"])


class UserFeedbackRequest(BaseModel):
    product_id: str
    module_code: str | None = None
    feature_code: str | None = None
    source_channel: str = "in_app"
    feedback_type: str
    sentiment: str | None = None
    satisfaction_score: int | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    related_requirement_id: str | None = None


class UserFeedbackPatchRequest(BaseModel):
    status: str | None = None
    sentiment: str | None = None
    satisfaction_score: int | None = None
    content: str | None = None
    tags: list[str] | None = None
    triage_note: str | None = None


class UserFeedbackConvertRequirementRequest(BaseModel):
    title: str
    content: str | None = None
    product_id: str | None = None
    version_id: str | None = None
    module_code: str | None = None
    priority: str = "P1"
    triage_note: str | None = None


class UserUsageMetricRequest(BaseModel):
    product_id: str
    module_code: str | None = None
    feature_code: str
    user_segment: str = "all"
    window_start: str
    window_end: str
    active_users: int = 0
    event_count: int = 0
    conversion_count: int = 0
    conversion_rate: float | None = None
    avg_duration_seconds: float | None = None
    bounce_rate: float | None = None
    error_count: int = 0
    source_channel: str | None = None


class IterationSuggestionRequest(BaseModel):
    product_id: str
    planning_cycle: str
    version_id: str | None = None
    module_codes: list[str] = Field(default_factory=list)
    include_evidence: bool = True
    constraints: dict[str, Any] = Field(default_factory=dict)


class IterationSuggestionDecisionRequest(BaseModel):
    decision: str
    edited_title: str | None = None
    edited_scope: str | None = None
    comment: str | None = None
    convert_to_requirement: bool = False


@router.get("/api/insights/items")
def insight_items(
    request: Request,
    category: str | None = None,
    product_id: str | None = None,
    summary: str | None = None,
    status: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    started_at = getattr(request.state, "started_at", None)
    payload = list_user_insight_items_response(
        category=category,
        current_store=store(request),
        page=page,
        page_size=page_size,
        product_id=product_id,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at if isinstance(started_at, float) else perf_counter(),
        status=status,
        summary=summary,
        trace_id=get_trace_id(request),
    )
    return envelope(payload, get_trace_id(request))


@router.get("/api/insights/usage-metrics")
def usage_metrics(
    request: Request,
    product_id: str | None = None,
    module_code: str | None = None,
    feature_code: str | None = None,
    user_segment: str | None = None,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_usage_metrics_response(
            current_store=store(request),
            feature_code=feature_code,
            from_=from_,
            module_code=module_code,
            product_id=product_id,
            to=to,
            user_segment=user_segment,
        ),
        get_trace_id(request),
    )


@router.post("/api/insights/usage-metrics")
def create_usage_metric(
    payload: UserUsageMetricRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_usage_metric_response(current_store=store(request), payload=payload, user=user),
        get_trace_id(request),
    )


@router.get("/api/insights/user-feedback")
def user_feedback(
    request: Request,
    product_id: str | None = None,
    module_code: str | None = None,
    feature_code: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    summary_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    started_at = getattr(request.state, "started_at", None)
    return envelope(
        list_user_feedback_response(
            created_by=created_by,
            current_store=store(request),
            feature_code=feature_code,
            module_code=module_code,
            page=page,
            page_size=page_size,
            product_id=product_id,
            started_at=started_at if isinstance(started_at, float) else perf_counter(),
            status=status,
            summary_only=summary_only,
            trace_id=get_trace_id(request),
        ),
        get_trace_id(request),
    )


@router.post("/api/insights/user-feedback")
def create_user_feedback(
    payload: UserFeedbackRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_user_feedback_response(current_store=store(request), payload=payload, user=user),
        get_trace_id(request),
    )


@router.patch("/api/insights/user-feedback/{feedback_id}")
def patch_user_feedback(
    feedback_id: str,
    payload: UserFeedbackPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_user_feedback_response(
            current_store=store(request),
            feedback_id=feedback_id,
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/insights/user-feedback/{feedback_id}/convert-requirement")
def convert_user_feedback_to_requirement(
    feedback_id: str,
    payload: UserFeedbackConvertRequirementRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        convert_user_feedback_to_requirement_response(
            current_store=store(request),
            feedback_id=feedback_id,
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/planning/iteration-suggestions")
def iteration_suggestions(
    request: Request,
    product_id: str | None = None,
    planning_cycle: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_iteration_suggestions_response(
            current_store=store(request),
            planning_cycle=planning_cycle,
            product_id=product_id,
            status=status,
        ),
        get_trace_id(request),
    )


@router.post("/api/planning/iteration-suggestions")
def create_iteration_suggestions(
    payload: IterationSuggestionRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_iteration_suggestions_response(
            current_store=store(request),
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/planning/iteration-suggestions/{suggestion_id}/decide")
def decide_iteration_suggestion(
    suggestion_id: str,
    payload: IterationSuggestionDecisionRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        decide_iteration_suggestion_response(
            current_store=store(request),
            payload=payload,
            suggestion_id=suggestion_id,
            user=user,
        ),
        get_trace_id(request),
    )
