from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error, require_any_permission_or_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.acceptance_test_plans import (
    activate_acceptance_test_plan,
    create_acceptance_test_case,
    create_acceptance_test_plan,
    get_acceptance_test_case,
    get_acceptance_test_plan,
    list_acceptance_test_plans,
    record_acceptance_test_run,
)
from app.services.product_scope import product_scope_filter, require_product_scope

router = APIRouter(tags=["acceptance-tests"])


class AcceptancePlanCreateRequest(BaseModel):
    product_id: str
    title: str


class AcceptanceCaseCreateRequest(BaseModel):
    case_code: str
    criterion: str
    title: str


class AcceptanceRunCreateRequest(BaseModel):
    artifact_ref: str | None = None
    case_id: str
    commit_sha: str | None = None
    input_fingerprint: str | None = None
    status: str
    verifier_task_id: str | None = None


def _require_manage(user: dict[str, Any]) -> None:
    require_any_permission_or_roles(
        user,
        {"requirement.create", "task.execute"},
        {"product_manager", "developer", "qa"},
    )


@router.get("/api/requirements/{requirement_id}/acceptance-test-plans")
def list_requirement_acceptance_test_plans(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_manage(user)
    return envelope(
        {
            "items": list_acceptance_test_plans(
                store(request),
                product_scope_ids=product_scope_filter(user),
                requirement_id=requirement_id,
            )
        },
        get_trace_id(request),
    )


@router.post("/api/requirements/{requirement_id}/acceptance-test-plans")
def create_requirement_acceptance_test_plan(
    requirement_id: str,
    payload: AcceptancePlanCreateRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_manage(user)
    require_product_scope(user, payload.product_id, status_code=403, message="Product scope denied")
    if not payload.title.strip():
        raise api_error(400, "VALIDATION_ERROR", "title is required")
    plan = create_acceptance_test_plan(
        store(request),
        created_by=user["id"],
        product_id=payload.product_id,
        requirement_id=requirement_id,
        title=payload.title,
    )
    return envelope(plan, get_trace_id(request))


@router.post("/api/acceptance-test-plans/{plan_id}/cases")
def create_plan_case(
    plan_id: str,
    payload: AcceptanceCaseCreateRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_manage(user)
    plan = get_acceptance_test_plan(store(request), plan_id=plan_id)
    if plan is None:
        raise api_error(404, "NOT_FOUND", "Acceptance test plan not found")
    require_product_scope(user, plan["product_id"], status_code=403, message="Product scope denied")
    try:
        case = create_acceptance_test_case(
            store(request),
            case_code=payload.case_code,
            criterion=payload.criterion,
            created_by=user["id"],
            plan_id=plan_id,
            title=payload.title,
        )
    except ValueError as exc:
        raise api_error(404, "NOT_FOUND", str(exc)) from exc
    return envelope(case, get_trace_id(request))


@router.post("/api/acceptance-test-plans/{plan_id}/activate")
def activate_plan(
    plan_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_manage(user)
    existing_plan = get_acceptance_test_plan(store(request), plan_id=plan_id)
    if existing_plan is None:
        raise api_error(404, "NOT_FOUND", "Acceptance test plan not found")
    require_product_scope(
        user,
        existing_plan["product_id"],
        status_code=403,
        message="Product scope denied",
    )
    try:
        plan = activate_acceptance_test_plan(store(request), plan_id=plan_id, user_id=user["id"])
    except ValueError as exc:
        raise api_error(404, "NOT_FOUND", str(exc)) from exc
    return envelope(plan, get_trace_id(request))


@router.post("/api/acceptance-test-runs")
def create_acceptance_run(
    payload: AcceptanceRunCreateRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_manage(user)
    if payload.status not in {"passed", "failed", "blocked", "skipped"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported status")
    case = get_acceptance_test_case(store(request), case_id=payload.case_id)
    if case is None:
        raise api_error(404, "NOT_FOUND", "Acceptance test case not found")
    require_product_scope(user, case["product_id"], status_code=403, message="Product scope denied")
    try:
        run = record_acceptance_test_run(store(request), **payload.model_dump())
    except ValueError as exc:
        raise api_error(404, "NOT_FOUND", str(exc)) from exc
    return envelope(run, get_trace_id(request))
