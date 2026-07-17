from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.requirement_assessments import (
    decide_requirement_assessment,
    get_latest_requirement_assessment,
    record_assessment_opinion,
    start_requirement_assessment,
    submit_assessment_answers,
)
from app.services.requirement_full_chain import get_requirement_response
from app.services.requirements import requirement_write_store

requirements_router = APIRouter(prefix="/api/requirements", tags=["requirement_assessments"])
assessments_router = APIRouter(
    prefix="/api/requirement-assessments", tags=["requirement_assessments"]
)


class AssessmentStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=200)
    requirement_revision: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)


class AssessmentOpinionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_code: str
    conclusion_json: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    cost_summary: dict[str, Any] = Field(default_factory=dict)
    policy_proposal_json: dict[str, Any] = Field(default_factory=dict)
    outcome_code: str | None = Field(default=None, max_length=100)
    risk_level: str | None = Field(default=None, max_length=20)
    idempotency_key: str | None = Field(default=None, max_length=200)


class AssessmentAnswersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: dict[str, Any]
    expected_version: int = Field(ge=1)
    idempotency_key: str | None = Field(default=None, max_length=200)


class AssessmentDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    version: int = Field(ge=1)
    comment: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=200)


@requirements_router.post("/{requirement_id}/assessments")
def start_assessment(
    requirement_id: str,
    request: Request,
    payload: AssessmentStartRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    requirement = get_requirement_response(
        current_store=store(request), requirement_id=requirement_id, user=user
    )
    result = start_requirement_assessment(
        current_store=requirement_write_store(store(request)),
        requirement=requirement,
        user=user,
        request_id=payload.request_id,
        requirement_revision=payload.requirement_revision,
        reason=payload.reason,
    )
    return envelope(result, get_trace_id(request))


@requirements_router.get("/{requirement_id}/assessments/latest")
def latest_assessment(
    requirement_id: str, request: Request, user: dict[str, Any] = CurrentUser
) -> dict[str, Any]:
    return envelope(
        get_latest_requirement_assessment(
            current_store=store(request), requirement_id=requirement_id, user=user
        ),
        get_trace_id(request),
    )


@assessments_router.post("/{assessment_id}/opinions")
def record_opinion(
    assessment_id: str,
    request: Request,
    payload: AssessmentOpinionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        record_assessment_opinion(
            current_store=requirement_write_store(store(request)),
            assessment_id=assessment_id,
            payload=payload.model_dump(),
            user=user,
        ),
        get_trace_id(request),
    )


@assessments_router.post("/{assessment_id}/answers")
def submit_answers(
    assessment_id: str,
    request: Request,
    payload: AssessmentAnswersRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        submit_assessment_answers(
            current_store=requirement_write_store(store(request)),
            assessment_id=assessment_id,
            payload=payload.model_dump(),
            user=user,
        ),
        get_trace_id(request),
    )


@assessments_router.post("/{assessment_id}/decisions")
def decide_assessment(
    assessment_id: str,
    request: Request,
    payload: AssessmentDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        decide_requirement_assessment(
            current_store=requirement_write_store(store(request)),
            assessment_id=assessment_id,
            payload=payload.model_dump(),
            user=user,
        ),
        get_trace_id(request),
    )
