from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.core.repositories.rd_collaboration_shared import RdCollaborationVersionConflictError
from app.services.rd_ai_employees import qualify_ai_actor
from app.services.rd_policy_resolution import (
    PolicyResolutionError,
    resolve_final_rd_policy,
    resolve_initial_rd_policy,
)
from app.services.rd_role_definitions import qualify_human_actor
from app.services.requirement_assessment_execution import create_assessment_execution
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
    raise api_error(409, error.code, str(error), extra=error.details)


def _required_assessment_bindings(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    payload = snapshot.get("payload_json") or {}
    required_roles = set((payload.get("team_config") or {}).get("required_role_codes") or [])
    bindings = [
        binding
        for binding in payload.get("role_bindings") or []
        if binding.get("status") == "active" and binding.get("role_code") in required_roles
    ]
    if {binding.get("role_code") for binding in bindings} != required_roles:
        raise api_error(
            409, "RD_POLICY_ROLE_BINDING_INVALID", "Required assessment role is unbound"
        )
    return bindings


def _role_definition(repository: Any, *, brain_app_id: str, code: str) -> dict[str, Any]:
    list_roles = getattr(repository, "list_rd_role_definitions", None)
    roles = list_roles(brain_app_id=brain_app_id, status="active") if callable(list_roles) else []
    matches = [role for role in roles if role.get("code") == code]
    if len(matches) != 1:
        raise api_error(409, "ASSESSMENT_ACTOR_UNQUALIFIED", "Required role is unavailable")
    return matches[0]


def _resolve_assessment_actor(
    *,
    repository: Any,
    binding: dict[str, Any],
    role: dict[str, Any],
    product_id: str,
    user: dict[str, Any],
) -> tuple[str, str, str | None]:
    """Return one frozen `(subject type, subject id, executor profile)` or fail closed."""
    actor_mode = binding.get("actor_mode")
    candidates: list[tuple[str, str, str | None]] = []
    if (
        actor_mode in {"human", "hybrid"}
        and user.get("id") in set(binding.get("candidate_human_user_ids") or [])
        and qualify_human_actor(user, role_definition=role, product_id=product_id)
    ):
        candidates.append(("human_user", user["id"], None))
    if actor_mode in {"ai", "hybrid"}:
        get_employee = getattr(repository, "get_rd_ai_employee", None)
        get_profile = getattr(repository, "get_rd_executor_profile", None)
        profile = (
            get_profile(binding.get("primary_executor_profile_id"))
            if callable(get_profile)
            else None
        )
        for employee_id in binding.get("candidate_ai_employee_ids") or []:
            employee = get_employee(employee_id) if callable(get_employee) else None
            if (
                employee
                and profile
                and qualify_ai_actor(
                    employee, profile, role_definition=role, policy_binding=binding
                )
            ):
                candidates.append(("ai_employee", employee["id"], profile["id"]))
    if len(candidates) != 1:
        raise api_error(
            409,
            "ASSESSMENT_ACTOR_UNQUALIFIED",
            "Each required role must resolve to exactly one qualified actor",
        )
    return candidates[0]


_RISK_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _new_opinion_round(
    *,
    current_store: Any,
    repository: Any,
    requirement: dict[str, Any],
    assessment: dict[str, Any],
    snapshot: dict[str, Any],
    user: dict[str, Any],
    opinion_round: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Freeze fresh, complete assignments for every active required role."""
    now = datetime.now(UTC).isoformat()
    opinions: list[dict[str, Any]] = []
    executions: list[dict[str, Any]] = []
    for binding in _required_assessment_bindings(snapshot):
        role = _role_definition(
            repository,
            brain_app_id=str(requirement.get("brain_app_id") or "rd_brain"),
            code=str(binding["role_code"]),
        )
        subject_type, subject_id, executor_profile_id = _resolve_assessment_actor(
            repository=repository,
            binding=binding,
            role=role,
            product_id=requirement["product_id"],
            user=user,
        )
        opinion_id = _new_id(current_store, "requirement_assessment_opinion")
        execution_id = _new_id(current_store, "requirement_assessment_execution")
        opinions.append(
            {
                "id": opinion_id,
                "assessment_id": assessment["id"],
                "role_code": binding["role_code"],
                "ai_employee_id": subject_id if subject_type == "ai_employee" else None,
                "executor_profile_id": executor_profile_id,
                "assigned_subject_type": subject_type,
                "assigned_user_id": subject_id if subject_type == "human_user" else None,
                "assigned_ai_employee_id": subject_id if subject_type == "ai_employee" else None,
                "input_revision": assessment["requirement_revision"],
                "strategy_snapshot_id": snapshot["id"],
                "opinion_round": opinion_round,
                "conclusion_json": {},
                "evidence_refs": [],
                "risk_summary": {},
                "cost_summary": {},
                "created_at": now,
                "updated_at": now,
            }
        )
        executions.append(
            create_assessment_execution(
                execution_id=execution_id,
                assessment_id=assessment["id"],
                opinion_id=opinion_id,
                role_code=str(binding["role_code"]),
                actor_type=subject_type,
                actor_id=subject_id,
                executor_profile_id=executor_profile_id,
                input_revision=assessment["requirement_revision"],
                strategy_snapshot_id=snapshot["id"],
            )
        )
    return opinions, executions


def _aggregate_policy_proposal(
    *, snapshot: dict[str, Any], opinions: list[dict[str, Any]]
) -> tuple[dict[str, Any], str | None, list[Any]]:
    """Accept one comparable policy proposal only; ambiguity and excess risk stay human-owned."""
    proposals = {
        json.dumps(item.get("policy_proposal_json") or {}, sort_keys=True, separators=(",", ":"))
        for item in opinions
        if item.get("policy_proposal_json")
    }
    outcomes = {str(item.get("outcome_code")) for item in opinions if item.get("outcome_code")}
    if len(proposals) > 1 or len(outcomes) > 1:
        raise api_error(
            409,
            "ASSESSMENT_INCOMPARABLE_HUMAN_DECISION_REQUIRED",
            "Required assessment opinions have incomparable policy proposals or outcomes",
        )
    risk_levels = [
        str(item.get("risk_level") or (item.get("risk_summary") or {}).get("risk_level") or "none")
        for item in opinions
    ]
    maximum_risk = max(risk_levels, key=lambda item: _RISK_RANK.get(item, 99))
    configured_limit = ((snapshot.get("payload_json") or {}).get("quality_gate_config") or {}).get(
        "max_risk"
    )
    if configured_limit and _RISK_RANK.get(maximum_risk, 99) > _RISK_RANK.get(
        str(configured_limit), -1
    ):
        raise api_error(
            409,
            "ASSESSMENT_RISK_HUMAN_DECISION_REQUIRED",
            "Assessment risk exceeds the frozen policy limit",
        )
    proposal = json.loads(next(iter(proposals))) if proposals else {}
    evidence = [
        {"role_code": item["role_code"], "evidence_refs": item.get("evidence_refs") or []}
        for item in opinions
    ]
    return proposal, maximum_risk, evidence


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
    opinions, executions = _new_opinion_round(
        current_store=current_store,
        repository=repository,
        requirement=requirement,
        assessment=assessment,
        snapshot=initial_snapshot,
        user=user,
        opinion_round=1,
    )
    save = getattr(repository, "save_assessment_bundle", None)
    if not callable(save):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment transaction is unavailable")
    saved = save(assessment=assessment, opinions=opinions, executions=executions)
    persisted = deepcopy(saved.get("assessment") or assessment)
    persisted["initial_policy_snapshot"] = deepcopy(initial_snapshot)
    persisted["opinions"] = deepcopy(saved.get("opinions") or opinions)
    persisted["executions"] = deepcopy(saved.get("executions") or executions)
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


def _assessment_product_id(assessment: dict[str, Any]) -> str:
    product_id = str(assessment.get("product_id") or "").strip()
    if not product_id:
        raise api_error(409, "ASSESSMENT_PROVENANCE_INVALID", "Assessment product scope is missing")
    return product_id


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
    ensure_requirement_product_scope(user, _assessment_product_id(assessment))
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
    if opinion.get("assigned_subject_type") != "human_user" or opinion.get(
        "assigned_user_id"
    ) != user.get("id"):
        raise api_error(
            403,
            "ASSESSMENT_OPINION_ACTOR_INVALID",
            "AI opinions require the internal assessment execution path; human opinions "
            "require the frozen user",
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
        "policy_proposal_json": deepcopy(payload.get("policy_proposal_json") or {}),
        "outcome_code": payload.get("outcome_code"),
        "risk_level": payload.get("risk_level"),
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
    ensure_requirement_product_scope(user, _assessment_product_id(assessment))
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
            "decision_comment": payload.get("comment"),
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
    ensure_requirement_product_scope(user, _assessment_product_id(assessment))
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
    get_snapshot = getattr(repository, "get_rd_policy_snapshot", None)
    frozen_snapshot = (
        get_snapshot(assessment.get("strategy_snapshot_id")) if callable(get_snapshot) else None
    )
    if frozen_snapshot is None:
        raise api_error(409, "RD_POLICY_SNAPSHOT_INVALID", "Assessment snapshot is missing")
    try:
        proposal, risk_level, evidence = _aggregate_policy_proposal(
            snapshot=frozen_snapshot, opinions=opinions
        )
    except Exception as exc:
        detail = getattr(exc, "detail", {})
        code = detail.get("code") if isinstance(detail, dict) else None
        if code not in {
            "ASSESSMENT_INCOMPARABLE_HUMAN_DECISION_REQUIRED",
            "ASSESSMENT_RISK_HUMAN_DECISION_REQUIRED",
        }:
            raise
        _update_assessment(
            repository,
            {
                **assessment,
                "status": "waiting_human",
                "assessment_outcome": code,
                "assessment_evidence": [
                    {
                        "role_code": item["role_code"],
                        "evidence_refs": item.get("evidence_refs") or [],
                    }
                    for item in opinions
                ],
                "updated_at": datetime.now(UTC).isoformat(),
            },
            expected_version=expected_version,
        )
        raise
    # A policy change creates a fresh full round.  The new assignments are
    # derived only after Task4 accepts the monotonic strengthening.
    if proposal:
        command_key = f"finalize-round:{expected_version}:{current_round}"
        execute = getattr(repository, "execute_requirement_assessment_command", None)
        if not callable(execute):
            raise api_error(
                503,
                "REPOSITORY_REQUIRED",
                "Assessment command transaction is unavailable",
            )

        def effect(transaction: Any) -> dict[str, Any]:
            candidate_assessment = {
                **assessment,
                "policy_delta": proposal,
                "resolution_revision": current_round,
            }
            try:
                next_snapshot = resolve_final_rd_policy(
                    current_store,
                    requirement={
                        "id": assessment["requirement_id"],
                        "product_id": _assessment_product_id(assessment),
                    },
                    assessment=candidate_assessment,
                    repository=transaction,
                )
            except PolicyResolutionError as exc:
                _policy_error(exc)
            if next_snapshot["id"] == assessment.get("strategy_snapshot_id"):
                return {**assessment, "policy_re_evaluation_required": False}
            next_round = current_round + 1
            if next_round > 2:
                raise api_error(
                    409,
                    "RD_POLICY_RESOLUTION_LIMIT",
                    "At most two assessment strengthening rounds are permitted",
                )
            next_opinions, executions = _new_opinion_round(
                current_store=current_store,
                repository=repository,
                requirement={
                    "id": assessment["requirement_id"],
                    "brain_app_id": "rd_brain",
                    "product_id": _assessment_product_id(assessment),
                },
                assessment=assessment,
                snapshot=next_snapshot,
                user=user,
                opinion_round=next_round,
            )
            persisted = transaction.advance_assessment_policy_round(
                assessment={
                    **assessment,
                    "final_strategy_snapshot_id": next_snapshot["id"],
                    "strategy_snapshot_id": next_snapshot["id"],
                    "opinion_round": next_round,
                    "proposed_policy_json": proposal,
                    "proposed_risk_level": risk_level,
                    "assessment_outcome": "re_evaluation_required",
                    "assessment_evidence": evidence,
                },
                expected_version=expected_version,
                opinions=next_opinions,
                executions=executions,
            )
            return {
                **persisted,
                "policy_re_evaluation_required": True,
                "opinions": next_opinions,
                "executions": executions,
            }

        try:
            return execute(
                {
                    "id": _new_id(current_store, "requirement_assessment_command"),
                    "assessment_id": assessment_id,
                    "operation": "finalize",
                    "idempotency_key": command_key,
                    "request_hash": _request_hash(
                        {"expected_version": expected_version, "proposal": proposal}
                    ),
                    "created_by": user["id"],
                },
                effect,
            )
        except RdCollaborationVersionConflictError as exc:
            raise api_error(409, exc.code, str(exc), extra=exc.details) from exc
    try:
        final_snapshot = resolve_final_rd_policy(
            current_store,
            requirement={
                "id": assessment["requirement_id"],
                "product_id": assessment.get("product_id"),
            },
            assessment=assessment,
        )
    except PolicyResolutionError as exc:
        _policy_error(exc)
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
    require_any_permission_or_roles(
        user,
        {"delivery.requirement_assessments.read"},
        set(),
    )
    repository = _repository(current_store)
    list_assessments = getattr(repository, "list_requirement_assessments", None)
    if not callable(list_assessments):
        raise api_error(503, "REPOSITORY_REQUIRED", "Assessment read repository is unavailable")
    assessments = list_assessments(requirement_id)
    if not assessments:
        raise api_error(404, "NOT_FOUND", "Requirement assessment not found")
    latest = assessments[-1]
    ensure_requirement_product_scope(user, _assessment_product_id(latest))
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
    ensure_requirement_product_scope(user, _assessment_product_id(assessment))
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
