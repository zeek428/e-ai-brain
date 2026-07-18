from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.rd_role_experiences import (
    decide_role_experience,
    get_role_experience_response,
    list_role_experiences_response,
)

router = APIRouter(tags=["rd_role_experiences"])


class ExperienceDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject", "retire"]
    comment: str | None = Field(default=None, max_length=4000)
    version: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=256)


@router.get("/api/delivery/rd-role-experiences")
def list_role_experiences(
    request: Request,
    brain_app_id: str | None = None,
    product_id: str | None = None,
    role_code: str | None = None,
    work_item_type: str | None = None,
    scenario: str | None = None,
    risk_level: str | None = None,
    repository_trust_domain: str | None = None,
    tool_trust_domain: str | None = None,
    minimum_confidence: float | None = Query(default=None, ge=0, le=1),
    status: str | None = None,
    version: int | None = Query(default=None, gt=0),
    evidence_subject_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: dict = CurrentUser,
) -> dict:
    payload = list_role_experiences_response(
        current_store=store(request),
        user=user,
        filters={
            "brain_app_id": brain_app_id,
            "product_id": product_id,
            "role_code": role_code,
            "work_item_type": work_item_type,
            "scenario": scenario,
            "risk_level": risk_level,
            "repository_trust_domain": repository_trust_domain,
            "tool_trust_domain": tool_trust_domain,
            "minimum_confidence": minimum_confidence,
            "status": status,
            "version": version,
            "evidence_subject_id": evidence_subject_id,
        },
        page=page,
        page_size=page_size,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/api/delivery/rd-role-experiences/{experience_id}")
def get_role_experience(experience_id: str, request: Request, user: dict = CurrentUser) -> dict:
    return envelope(
        get_role_experience_response(
            current_store=store(request), user=user, experience_id=experience_id
        ),
        get_trace_id(request),
    )


@router.post("/api/delivery/rd-role-experiences/{experience_id}/decide")
def decide_experience(
    experience_id: str,
    request: Request,
    payload: ExperienceDecisionRequest,
    user: dict = CurrentUser,
) -> dict:
    return envelope(
        decide_role_experience(
            store(request),
            experience_id=experience_id,
            decision=payload.decision,
            comment=payload.comment,
            expected_version=payload.version,
            idempotency_key=payload.idempotency_key,
            user=user,
        ),
        get_trace_id(request),
    )
