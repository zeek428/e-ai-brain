from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.core.repositories.rd_collaboration_shared import RdCollaborationVersionConflictError
from app.services.rd_policy_resolution import (
    PolicyResolutionError,
    resolve_final_rd_policy,
    resolve_initial_rd_policy,
)
from app.services.requirements import ensure_requirement_product_scope


def _repository(current_store: Any) -> Any:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        raise api_error(
            503,
            "REPOSITORY_REQUIRED",
            "Requirement assessments require a PostgreSQL repository",
        )
    return repository


def _new_id(current_store: Any, prefix: str) -> str:
    factory = getattr(current_store, "new_id", None)
    if not callable(factory):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment id generator is unavailable")
    return str(factory(prefix))


def _request_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _idempotent_replay(
    repository: Any, *, assessment_id: str, operation: str, key: str | None, payload: dict[str, Any]
) -> dict[str, Any] | None:
    if not key:
        return None
    get = getattr(repository, "get_requirement_assessment_command", None)
    if not callable(get):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment command repository is unavailable")
    command = get(assessment_id=assessment_id, operation=operation, idempotency_key=key)
    if command is None:
        return None
    if command.get("request_hash") != _request_hash(payload):
        raise api_error(
            409, "RD_IDEMPOTENCY_CONFLICT", "Idempotency key is bound to another request"
        )
    return deepcopy(command.get("response_snapshot") or {})


def _save_idempotent_response(
    current_store: Any,
    repository: Any,
    *,
    assessment_id: str,
    operation: str,
    key: str | None,
    payload: dict[str, Any],
    actor_id: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    if not key:
        return response
    save = getattr(repository, "save_requirement_assessment_command", None)
    if not callable(save):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment command repository is unavailable")
    saved = save(
        {
            "id": _new_id(current_store, "requirement_assessment_command"),
            "assessment_id": assessment_id,
            "operation": operation,
            "idempotency_key": key,
            "request_hash": _request_hash(payload),
            "response_snapshot": response,
            "created_by": actor_id,
        }
    )
    if saved.get("request_hash") != _request_hash(payload):
        raise api_error(
            409, "RD_IDEMPOTENCY_CONFLICT", "Idempotency key is bound to another request"
        )
    return deepcopy(saved.get("response_snapshot") or response)


def _policy_error(error: PolicyResolutionError) -> Any:
    raise api_error(409, error.code, str(error), details=error.details)


def start_requirement_assessment(
    *,
    current_store: Any,
    requirement: dict[str, Any],
    user: dict[str, Any],
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Freeze the initial policy and create the required opinion requests atomically."""
    require_any_permission_or_roles(
        user,
        {"requirement.approve"},
        {"product_owner", "rd_owner"},
    )
    ensure_requirement_product_scope(user, requirement.get("product_id"))
    if requirement.get("status") != "submitted":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not awaiting assessment")
    repository = _repository(current_store)
    try:
        initial_snapshot = resolve_initial_rd_policy(current_store, requirement=requirement)
    except PolicyResolutionError as exc:
        _policy_error(exc)
    list_assessments = getattr(repository, "list_requirement_assessments", None)
    if callable(list_assessments):
        existing = next(
            (
                item
                for item in list_assessments(requirement["id"])
                if item.get("initial_strategy_snapshot_id") == initial_snapshot["id"]
                and item.get("status")
                in {
                    "draft",
                    "evaluating",
                    "waiting_human",
                    "needs_info",
                    "rework_required",
                    "accepted",
                }
            ),
            None,
        )
        if existing is not None:
            replay = _idempotent_replay(
                repository,
                assessment_id=existing["id"],
                operation="start",
                key=idempotency_key,
                payload={"requirement_id": requirement["id"]},
            )
            if replay is not None:
                return replay
            existing["initial_policy_snapshot"] = deepcopy(initial_snapshot)
            existing["opinions"] = _assessment_opinions(repository, existing["id"])
            return existing
    assessment_id = _new_id(current_store, "requirement_assessment")
    now = datetime.now(UTC).isoformat()
    assessment = {
        "id": assessment_id,
        "requirement_id": requirement["id"],
        "requirement_revision": int(
            requirement.get("assessment_revision") or requirement.get("revision") or 1
        ),
        "product_id": requirement["product_id"],
        "initial_strategy_snapshot_id": initial_snapshot["id"],
        "final_strategy_snapshot_id": initial_snapshot["id"],
        "strategy_snapshot_id": initial_snapshot["id"],
        "structured_assessment": {},
        "risk_summary": {},
        "dependency_summary": [],
        "effort_estimate": {},
        "status": "evaluating",
        "version": 1,
        "opinion_round": 1,
        "llm_suggestion": {},
        "deterministic_validation": {},
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    role_bindings = initial_snapshot.get("payload_json", {}).get("role_bindings", [])
    opinions = [
        {
            "id": _new_id(current_store, "requirement_assessment_opinion"),
            "assessment_id": assessment_id,
            "role_code": binding["role_code"],
            "ai_employee_id": (binding.get("candidate_ai_employee_ids") or [None])[0],
            "candidate_human_user_ids": binding.get("candidate_human_user_ids") or [],
            "executor_profile_id": binding.get("primary_executor_profile_id"),
            "input_revision": assessment["requirement_revision"],
            "strategy_snapshot_id": initial_snapshot["id"],
            "opinion_round": 1,
            "conclusion_json": {},
            "evidence_refs": [],
            "risk_summary": {},
            "cost_summary": {},
            "created_at": now,
            "updated_at": now,
        }
        for binding in role_bindings
    ]
    save = getattr(repository, "save_assessment_bundle", None)
    if not callable(save):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment transaction is unavailable")
    saved = save(assessment=assessment, opinions=opinions)
    persisted = deepcopy(saved.get("assessment") or assessment)
    persisted["initial_policy_snapshot"] = deepcopy(initial_snapshot)
    persisted["opinions"] = deepcopy(saved.get("opinions") or opinions)
    return _save_idempotent_response(
        current_store,
        repository,
        assessment_id=assessment_id,
        operation="start",
        key=idempotency_key,
        payload={"requirement_id": requirement["id"]},
        actor_id=user["id"],
        response=persisted,
    )


def _assessment(repository: Any, assessment_id: str) -> dict[str, Any]:
    get = getattr(repository, "get_requirement_assessment", None)
    assessment = get(assessment_id) if callable(get) else None
    if assessment is None:
        raise api_error(404, "NOT_FOUND", "Requirement assessment not found")
    return assessment


def _assessment_opinions(repository: Any, assessment_id: str) -> list[dict[str, Any]]:
    list_opinions = getattr(repository, "list_requirement_assessment_opinions", None)
    if not callable(list_opinions):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment opinions are unavailable")
    return list_opinions(assessment_id)


def _update_assessment(
    repository: Any, assessment: dict[str, Any], *, expected_version: int
) -> dict[str, Any]:
    update = getattr(repository, "update_requirement_assessment", None)
    if not callable(update):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment state transaction is unavailable")
    try:
        return update(assessment, expected_version=expected_version)
    except RdCollaborationVersionConflictError as exc:
        raise api_error(409, exc.code, str(exc), extra=exc.details) from exc


def record_assessment_opinion(
    *,
    current_store: Any,
    assessment_id: str,
    payload: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    """Record only the opinion assigned to the authenticated actor for this round."""
    repository = _repository(current_store)
    replay = _idempotent_replay(
        repository,
        assessment_id=assessment_id,
        operation="opinion",
        key=payload.get("idempotency_key"),
        payload=payload,
    )
    if replay is not None:
        return replay
    assessment = _assessment(repository, assessment_id)
    ensure_requirement_product_scope(user, assessment.get("product_id") or "product_1")
    if assessment.get("status") not in {
        "evaluating",
        "waiting_human",
        "needs_info",
        "rework_required",
    }:
        raise api_error(409, "ASSESSMENT_STATE_INVALID", "Assessment is not accepting opinions")
    role_code = str(payload.get("role_code") or "").strip()
    opinions = _assessment_opinions(repository, assessment_id)
    expected_round = int(assessment.get("opinion_round") or 1)
    matches = [
        item
        for item in opinions
        if item.get("role_code") == role_code
        and int(item.get("opinion_round") or 1) == expected_round
    ]
    if len(matches) != 1:
        raise api_error(
            400, "ASSESSMENT_OPINION_INVALID", "Opinion role is not required for this round"
        )
    opinion = matches[0]
    assigned = {str(item) for item in (opinion.get("candidate_human_user_ids") or [])}
    if opinion.get("ai_employee_id"):
        assigned.add(str(opinion["ai_employee_id"]))
    if str(user.get("id") or "") not in assigned:
        raise api_error(
            403,
            "ASSESSMENT_OPINION_ACTOR_INVALID",
            "Opinion actor is not assigned to this assessment role",
        )
    if opinion.get("conclusion_json"):
        raise api_error(409, "ASSESSMENT_OPINION_RECORDED", "Opinion is already recorded")
    saved_opinion = {
        **opinion,
        "conclusion_json": deepcopy(payload.get("conclusion_json") or {}),
        "evidence_refs": deepcopy(payload.get("evidence_refs") or []),
        "confidence": payload.get("confidence"),
        "risk_summary": deepcopy(payload.get("risk_summary") or {}),
        "cost_summary": deepcopy(payload.get("cost_summary") or {}),
        "actor_id": user["id"],
        "updated_at": datetime.now(UTC).isoformat(),
    }
    save_opinion = getattr(repository, "update_requirement_assessment_opinion", None)
    if not callable(save_opinion):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment opinion transaction is unavailable")
    saved_opinion = save_opinion(saved_opinion)
    all_current = _assessment_opinions(repository, assessment_id)
    current_complete = all(
        item.get("conclusion_json")
        for item in all_current
        if int(item.get("opinion_round") or 1) == expected_round
    )
    if current_complete and assessment.get("status") == "evaluating":
        _update_assessment(
            repository,
            {**assessment, "status": "waiting_human", "updated_at": datetime.now(UTC).isoformat()},
            expected_version=int(assessment.get("version") or 1),
        )
    return _save_idempotent_response(
        current_store,
        repository,
        assessment_id=assessment_id,
        operation="opinion",
        key=payload.get("idempotency_key"),
        payload=payload,
        actor_id=user["id"],
        response=saved_opinion,
    )


_DECISION_STATUSES = {
    "accept": "accepted",
    "defer": "deferred",
    "reject": "rejected",
    "request_more_info": "needs_info",
    "request_rework": "rework_required",
}


def decide_requirement_assessment(
    *,
    current_store: Any,
    assessment_id: str,
    payload: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"requirement.approve", "delivery.requirement_assessments.decide"},
        {"product_owner", "rd_owner"},
    )
    action = str(payload.get("action") or "").strip()
    if action not in _DECISION_STATUSES:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "action must be accept, reject, request_more_info, request_rework, or defer",
        )
    expected_version = payload.get("expected_version")
    if not isinstance(expected_version, int) or expected_version < 1:
        raise api_error(400, "VALIDATION_ERROR", "expected_version is required")
    repository = _repository(current_store)
    replay = _idempotent_replay(
        repository,
        assessment_id=assessment_id,
        operation="decision",
        key=payload.get("idempotency_key"),
        payload=payload,
    )
    if replay is not None:
        return replay
    assessment = _assessment(repository, assessment_id)
    ensure_requirement_product_scope(user, assessment.get("product_id") or "product_1")
    if assessment.get("status") not in {
        "waiting_human",
        "evaluating",
        "needs_info",
        "rework_required",
    }:
        raise api_error(409, "ASSESSMENT_STATE_INVALID", "Assessment decision is not available")
    if action == "accept":
        result = finalize_requirement_assessment(
            current_store=current_store,
            assessment_id=assessment_id,
            expected_version=expected_version,
            user=user,
        )
        return _save_idempotent_response(
            current_store,
            repository,
            assessment_id=assessment_id,
            operation="decision",
            key=payload.get("idempotency_key"),
            payload=payload,
            actor_id=user["id"],
            response=result,
        )
    result = _update_assessment(
        repository,
        {
            **assessment,
            "status": _DECISION_STATUSES[action],
            "decided_by": user["id"],
            "decision_action": action,
            "decided_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        },
        expected_version=expected_version,
    )
    return _save_idempotent_response(
        current_store,
        repository,
        assessment_id=assessment_id,
        operation="decision",
        key=payload.get("idempotency_key"),
        payload=payload,
        actor_id=user["id"],
        response=result,
    )


def finalize_requirement_assessment(
    *,
    current_store: Any,
    assessment_id: str,
    expected_version: int,
    user: dict[str, Any],
) -> dict[str, Any]:
    """Accept only a complete compatible round and atomically approve the submitted requirement."""
    repository = _repository(current_store)
    assessment = _assessment(repository, assessment_id)
    ensure_requirement_product_scope(user, assessment.get("product_id") or "product_1")
    if int(assessment.get("version") or 1) != expected_version:
        raise api_error(409, "RD_VERSION_CONFLICT", "R&D collaboration record version conflict")
    current_round = int(assessment.get("opinion_round") or 1)
    opinions = [
        opinion
        for opinion in _assessment_opinions(repository, assessment_id)
        if int(opinion.get("opinion_round") or 1) == current_round
    ]
    if not opinions or any(not opinion.get("conclusion_json") for opinion in opinions):
        raise api_error(
            409, "ASSESSMENT_OPINIONS_INCOMPLETE", "All required assessment opinions are required"
        )
    final_snapshot = resolve_final_rd_policy(
        current_store,
        requirement={
            "id": assessment["requirement_id"],
            "product_id": assessment.get("product_id"),
        },
        assessment=assessment,
    )
    load_requirements = getattr(repository, "load_requirements", None)
    requirements = (
        (load_requirements() or {}).get("requirements", {}) if callable(load_requirements) else {}
    )
    requirement = requirements.get(assessment["requirement_id"])
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement.get("status") != "submitted":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not awaiting assessment")
    updated_requirement = {
        **requirement,
        "status": "approved",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    update = getattr(repository, "update_requirement_assessment", None)
    if not callable(update):
        raise api_error(
            503, "REPOSITORY_REQUIRED", "Assessment finalization transaction is unavailable"
        )
    try:
        return update(
            {
                **assessment,
                "status": "accepted",
                "final_strategy_snapshot_id": final_snapshot["id"],
                "strategy_snapshot_id": final_snapshot["id"],
                "decided_by": user["id"],
                "decided_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
            expected_version=expected_version,
            requirement=updated_requirement,
        )
    except RdCollaborationVersionConflictError as exc:
        raise api_error(409, exc.code, str(exc), extra=exc.details) from exc


def get_latest_requirement_assessment(
    *, current_store: Any, requirement_id: str, user: dict[str, Any]
) -> dict[str, Any]:
    repository = _repository(current_store)
    list_assessments = getattr(repository, "list_requirement_assessments", None)
    if not callable(list_assessments):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment read repository is unavailable")
    assessments = list_assessments(requirement_id)
    if not assessments:
        raise api_error(404, "NOT_FOUND", "Requirement assessment not found")
    latest = assessments[-1]
    ensure_requirement_product_scope(user, latest.get("product_id") or "product_1")
    latest["opinions"] = _assessment_opinions(repository, latest["id"])
    return latest


def submit_assessment_answers(
    *,
    current_store: Any,
    assessment_id: str,
    payload: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    """Persist answers as a new assessment/requirement revision; stale submissions fail closed."""
    repository = _repository(current_store)
    replay = _idempotent_replay(
        repository,
        assessment_id=assessment_id,
        operation="answers",
        key=payload.get("idempotency_key"),
        payload=payload,
    )
    if replay is not None:
        return replay
    assessment = _assessment(repository, assessment_id)
    require_any_permission_or_roles(
        user, {"requirement.create", "requirement.approve"}, {"product_owner", "rd_owner"}
    )
    ensure_requirement_product_scope(user, assessment.get("product_id") or "product_1")
    if assessment.get("status") not in {"needs_info", "rework_required"}:
        raise api_error(409, "ASSESSMENT_STATE_INVALID", "Assessment does not require answers")
    expected_version = payload.get("expected_version")
    advance = getattr(repository, "submit_assessment_answers", None)
    if not callable(advance):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment answer transaction is unavailable")
    try:
        result = advance(
            assessment_id=assessment_id,
            expected_version=expected_version,
            answers=deepcopy(payload.get("answers") or {}),
            actor_id=user["id"],
        )
        return _save_idempotent_response(
            current_store,
            repository,
            assessment_id=assessment_id,
            operation="answers",
            key=payload.get("idempotency_key"),
            payload=payload,
            actor_id=user["id"],
            response=result,
        )
    except RdCollaborationVersionConflictError as exc:
        raise api_error(409, exc.code, str(exc), extra=exc.details) from exc
