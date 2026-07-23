"""HTTP contracts for the deterministic R&D collaboration control plane."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, api_error, require_any_permission_or_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.rd_collaboration_access import (
    require_decision_scope,
    require_requirement_scope,
    require_run_scope,
    require_scope_change_scope,
    require_version_scope,
    require_work_item_scope,
)
from app.services.rd_collaboration_decisions import answer_decision_request, apply_decision
from app.services.rd_collaboration_plan_generation import generate_and_persist_work_item_plan
from app.services.rd_collaboration_planning import (
    persist_work_item_plan,
    restart_terminal_collaboration_run,
    start_collaboration_run,
)
from app.services.rd_scope_changes import (
    apply_scope_change_decision,
    create_scope_change_request,
)
from app.services.rd_work_item_scheduler import (
    cancel_work_item,
    claim_work_item,
    complete_attempt,
    review_work_item,
)

router = APIRouter(tags=["rd_collaboration"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CollaborationStartRequest(_StrictModel):
    request_id: str = Field(min_length=1)
    scope_version: int = Field(gt=0)
    reason: str | None = None


class CollaborationRestartRequest(CollaborationStartRequest):
    terminal_run_id: str = Field(min_length=1)


class ScopeChangeRequest(_StrictModel):
    request_id: str = Field(min_length=1)
    expected_scope_version: int = Field(gt=0)
    expected_run_generation: int = Field(gt=0)
    source_run_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    operations: list[dict[str, Any]] = Field(min_length=1)


class ClaimRequest(_StrictModel):
    expected_version: int = Field(gt=0)
    lease_seconds: int = Field(ge=60, le=1800)
    idempotency_key: str = Field(min_length=1)


class SubmitRequest(_StrictModel):
    attempt_id: str = Field(min_length=1)
    lease_token: str = Field(min_length=1)
    version: int = Field(gt=0)
    output: dict[str, Any]
    evidence: dict[str, Any]
    idempotency_key: str = Field(min_length=1)


class ReviewRequest(_StrictModel):
    decision: str
    comment: str | None = None
    version: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1)


class CancelRequest(_StrictModel):
    reason: str = Field(min_length=1)
    version: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1)


class DecisionRequest(_StrictModel):
    selected_option: str = Field(min_length=1)
    input: Any = None
    comment: str | None = None
    version: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1)


class DecisionAnswerRequest(_StrictModel):
    answer: Any
    evidence: list[Any] = Field(default_factory=list)
    version: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1)


class WorkItemPlanRequest(_StrictModel):
    work_items: list[dict[str, Any]] = Field(min_length=1)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)


def _require(user: dict[str, Any], permission: str) -> None:
    require_any_permission_or_roles(
        user,
        {permission},
        {"admin", "rd_owner", "product_owner", "developer", "tester"},
    )


def _get(
    current_store: Any, collection: str, record_id: str, repository_method: str
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    getter = getattr(repository, repository_method, None)
    if callable(getter):
        return getter(record_id)
    records = getattr(current_store, collection, {})
    return records.get(record_id) if isinstance(records, dict) else None


def _list(
    current_store: Any, collection: str, run_id: str, repository_method: str
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    method = getattr(repository, repository_method, None)
    if callable(method):
        return method(run_id)
    records = getattr(current_store, collection, {})
    if not isinstance(records, dict):
        return []
    key = "collaboration_run_id"
    return sorted(
        [deepcopy(value) for value in records.values() if value.get(key) == run_id],
        key=lambda value: str(value.get("id")),
    )


def _run_payload(result: dict[str, Any]) -> dict[str, Any]:
    run = dict(result["run"])
    return {
        **run,
        "strategy_source_count": result.get("strategy_source_count", 0),
        "idempotent_replay": bool(result.get("idempotent_replay")),
    }


@router.post("/api/product-versions/{version_id}/collaboration-runs", status_code=201)
def start_run(
    version_id: str,
    request: Request,
    payload: CollaborationStartRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.plan")
    current_store = store(request)
    require_version_scope(current_store, user, version_id)
    result = start_collaboration_run(
        current_store,
        product_version_id=version_id,
        request_id=payload.request_id,
        scope_version=payload.scope_version,
        actor=user,
        reason=payload.reason,
    )
    return envelope(_run_payload(result), get_trace_id(request))


@router.post("/api/product-versions/{version_id}/collaboration-runs/restart", status_code=201)
def restart_run(
    version_id: str,
    request: Request,
    payload: CollaborationRestartRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.plan")
    current_store = store(request)
    require_version_scope(current_store, user, version_id)
    result = restart_terminal_collaboration_run(
        current_store,
        product_version_id=version_id,
        terminal_run_id=payload.terminal_run_id,
        request_id=payload.request_id,
        scope_version=payload.scope_version,
        actor=user,
        reason=payload.reason,
    )
    body = _run_payload(result)
    body["reused_evidence_refs"] = result.get("reused_evidence_refs", [])
    return envelope(body, get_trace_id(request))


@router.post("/api/product-versions/{version_id}/scope-change-requests", status_code=202)
def create_scope_change(
    version_id: str,
    request: Request,
    payload: ScopeChangeRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.plan")
    current_store = store(request)
    require_version_scope(current_store, user, version_id)
    result = create_scope_change_request(
        current_store,
        product_version_id=version_id,
        request_id=payload.request_id,
        expected_scope_version=payload.expected_scope_version,
        expected_run_generation=payload.expected_run_generation,
        source_run_id=payload.source_run_id,
        reason=payload.reason,
        operations=payload.operations,
        actor=user,
    )
    item = result["scope_change_request"]
    return envelope(
        {
            "scope_change_request_id": item["id"],
            "request_id": item["request_id"],
            "status": item["status"],
            "decision_request_id": item["decision_request_id"],
            "source_run_id": item["source_run_id"],
            "source_run_state": item["source_run_state"],
            "expected_run_generation": item["expected_run_generation"],
            "current_scope_version": result["current_scope_version"],
            "operations_hash": item["operations_hash"],
            "restart_required": result["restart_required"],
            "idempotent_replay": result["idempotent_replay"],
        },
        get_trace_id(request),
    )


@router.get("/api/delivery/rd-scope-change-requests/{scope_change_request_id}")
def get_scope_change(
    scope_change_request_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.read")
    current_store = store(request)
    require_scope_change_scope(current_store, user, scope_change_request_id)
    item = _get(
        current_store,
        "rd_scope_change_requests",
        scope_change_request_id,
        "get_rd_scope_change_request",
    )
    if item is None:
        raise api_error(404, "NOT_FOUND", "Scope change request not found")
    repository = getattr(current_store, "repository", None)
    list_operations = getattr(repository, "list_rd_scope_change_request_operations", None)
    if callable(list_operations):
        operations = list_operations(scope_change_request_id)
    else:
        operations = sorted(
            [
                value
                for value in getattr(
                    current_store, "rd_scope_change_request_operations", {}
                ).values()
                if value.get("scope_change_request_id") == scope_change_request_id
            ],
            key=lambda value: int(value.get("position") or 0),
        )
    return envelope({**item, "operations": operations}, get_trace_id(request))


@router.get("/api/requirements/{requirement_id}/collaboration-run")
def requirement_run(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.read")
    current_store = store(request)
    require_requirement_scope(current_store, user, requirement_id)
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_rd_collaboration_runs", None)
    runs = (
        list_runs()
        if callable(list_runs)
        else getattr(current_store, "rd_collaboration_runs", {}).values()
    )
    for run in runs:
        scope = _list(
            current_store,
            "rd_collaboration_run_requirements",
            str(run["id"]),
            "list_rd_collaboration_run_requirements",
        )
        if any(entry.get("requirement_id") == requirement_id for entry in scope):
            return envelope(run, get_trace_id(request))
    raise api_error(404, "NOT_FOUND", "Requirement has no collaboration run")


@router.get("/api/delivery/rd-collaboration-runs/{run_id}")
def get_run(run_id: str, request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.read")
    current_store = store(request)
    require_run_scope(current_store, user, run_id)
    run = _get(current_store, "rd_collaboration_runs", run_id, "get_rd_collaboration_run")
    if run is None:
        raise api_error(404, "NOT_FOUND", "Collaboration run not found")
    return envelope(
        {
            **run,
            "scope": _list(
                current_store,
                "rd_collaboration_run_requirements",
                run_id,
                "list_rd_collaboration_run_requirements",
            ),
            "seats": _list(current_store, "rd_run_seats", run_id, "list_rd_run_seats"),
        },
        get_trace_id(request),
    )


@router.get("/api/delivery/rd-collaboration-runs/{run_id}/work-items")
def list_work_items(
    run_id: str, request: Request, user: dict[str, Any] = CurrentUser
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.read")
    require_run_scope(store(request), user, run_id)
    return envelope(
        {
            "items": _list(store(request), "rd_work_items", run_id, "list_rd_work_items"),
            "dependencies": _list(
                store(request),
                "rd_work_item_dependencies",
                run_id,
                "list_rd_work_item_dependencies",
            ),
        },
        get_trace_id(request),
    )


@router.post("/api/delivery/rd-collaboration-runs/{run_id}/plan")
@router.post("/api/delivery/rd-collaboration-runs/{run_id}/replan")
def validate_plan(
    run_id: str,
    request: Request,
    payload: WorkItemPlanRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.plan")
    current_store = store(request)
    require_run_scope(current_store, user, run_id)
    plan = persist_work_item_plan(
        current_store,
        collaboration_run_id=run_id,
        proposal=payload.model_dump(),
        actor=user,
    )
    return envelope(plan, get_trace_id(request))


@router.post("/api/delivery/rd-collaboration-runs/{run_id}/generate-plan")
def generate_plan(
    run_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    """Generate a bounded LLM proposal, then persist only its validated DAG."""
    _require(user, "delivery.rd_collaboration.plan")
    current_store = store(request)
    require_run_scope(current_store, user, run_id)
    plan = generate_and_persist_work_item_plan(
        current_store,
        collaboration_run_id=run_id,
    )
    return envelope(plan, get_trace_id(request))


@router.post("/api/delivery/rd-work-items/{work_item_id}/claim")
def claim(
    work_item_id: str,
    request: Request,
    payload: ClaimRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.work")
    require_work_item_scope(store(request), user, work_item_id)
    result = claim_work_item(
        store(request),
        work_item_id=work_item_id,
        actor=user,
        expected_version=payload.expected_version,
        lease_seconds=payload.lease_seconds,
        idempotency_key=payload.idempotency_key,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/delivery/rd-work-items/{work_item_id}/submit")
def submit(
    work_item_id: str,
    request: Request,
    payload: SubmitRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.work")
    require_work_item_scope(store(request), user, work_item_id)
    _ = user
    result = complete_attempt(
        store(request),
        work_item_id=work_item_id,
        attempt_id=payload.attempt_id,
        lease_token=payload.lease_token,
        version=payload.version,
        output=payload.output,
        evidence=payload.evidence,
        idempotency_key=payload.idempotency_key,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/delivery/rd-work-items/{work_item_id}/review")
def review(
    work_item_id: str,
    request: Request,
    payload: ReviewRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.work")
    require_work_item_scope(store(request), user, work_item_id)
    result = review_work_item(
        store(request),
        work_item_id=work_item_id,
        decision=payload.decision,
        comment=payload.comment,
        actor=user,
        version=payload.version,
        idempotency_key=payload.idempotency_key,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/delivery/rd-work-items/{work_item_id}/cancel")
def cancel(
    work_item_id: str,
    request: Request,
    payload: CancelRequest,
    response: Response,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.rd_collaboration.plan")
    require_work_item_scope(store(request), user, work_item_id)
    result = cancel_work_item(
        store(request),
        work_item_id=work_item_id,
        reason=payload.reason,
        actor=user,
        version=payload.version,
        idempotency_key=payload.idempotency_key,
    )
    if result.get("decision_request"):
        response.status_code = 202
    return envelope(result, get_trace_id(request))


@router.post("/api/delivery/decision-requests/{decision_request_id}/decide")
def decide(
    decision_request_id: str,
    request: Request,
    payload: DecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.decision_requests.decide")
    current_store = store(request)
    decision_record = require_decision_scope(current_store, user, decision_request_id)
    if decision_record and decision_record.get("subject_type") == "rd_scope_change_request":
        scope = apply_scope_change_decision(
            current_store,
            scope_change_request_id=str(decision_record["subject_id"]),
            decision=payload.selected_option,
            actor=user,
            version=payload.version,
            idempotency_key=payload.idempotency_key,
        )
        return envelope(scope, get_trace_id(request))
    result = apply_decision(
        current_store,
        decision_request_id=decision_request_id,
        selected_option=payload.selected_option,
        input_value=payload.input,
        comment=payload.comment,
        actor=user,
        version=payload.version,
        idempotency_key=payload.idempotency_key,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/delivery/decision-requests/{decision_request_id}")
def get_decision_request(
    decision_request_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    """Expose the frozen options and optimistic-lock version for the human workbench."""
    _require(user, "delivery.rd_collaboration.read")
    decision = require_decision_scope(store(request), user, decision_request_id)
    return envelope(decision, get_trace_id(request))


@router.post("/api/delivery/decision-requests/{decision_request_id}/answers")
def answer(
    decision_request_id: str,
    request: Request,
    payload: DecisionAnswerRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require(user, "delivery.decision_requests.answer")
    require_decision_scope(store(request), user, decision_request_id)
    result = answer_decision_request(
        store(request),
        decision_request_id=decision_request_id,
        answer=payload.answer,
        evidence=payload.evidence,
        actor=user,
        version=payload.version,
        idempotency_key=payload.idempotency_key,
    )
    return envelope(result, get_trace_id(request))
