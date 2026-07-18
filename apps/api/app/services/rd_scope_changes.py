"""Governed, typed product-version scope changes for active collaboration."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from app.api.deps import api_error

_ALLOWED_OPERATIONS = {
    "add_requirement",
    "remove_requirement",
    "replace_requirement_snapshot",
    "update_repository_baseline",
}
_TERMINAL_RUN_STATES = {"completed", "failed", "cancelled"}


def _records(store: Any, name: str) -> dict[str, dict[str, Any]]:
    values = getattr(store, name, None)
    if not isinstance(values, dict):
        values = {}
        setattr(store, name, values)
    return values


def _new_id(store: Any, prefix: str) -> str:
    factory = getattr(store, "new_id", None)
    if callable(factory):
        return str(factory(prefix))
    return f"{prefix}_{hashlib.sha256(str(datetime.now(UTC)).encode()).hexdigest()[:16]}"


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _canonical_operations(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for position, raw in enumerate(operations):
        if not isinstance(raw, dict) or raw.get("op") not in _ALLOWED_OPERATIONS:
            raise api_error(
                422,
                "RD_SCOPE_CHANGE_INVALID",
                "Scope operation is invalid",
                {"operation": position, "field": "op", "retryable": False},
            )
        operation = {key: value for key, value in raw.items() if value is not None}
        op = str(operation["op"])
        required = {
            "add_requirement": {
                "requirement_id",
                "requirement_revision",
                "assessment_id",
                "final_strategy_snapshot_id",
            },
            "remove_requirement": {"requirement_id", "destination"},
            "replace_requirement_snapshot": {
                "requirement_id",
                "requirement_revision",
                "assessment_id",
                "final_strategy_snapshot_id",
            },
            "update_repository_baseline": {
                "repository_id",
                "branch_config_version",
                "base_commit_sha",
            },
        }[op]
        missing = sorted(key for key in required if key not in operation)
        if missing or (
            op == "remove_requirement" and operation.get("destination") != "approved_pool"
        ):
            raise api_error(
                422,
                "RD_SCOPE_CHANGE_INVALID",
                "Scope operation has invalid typed fields",
                {
                    "operation": position,
                    "field": missing[0] if missing else "destination",
                    "retryable": False,
                },
            )
        canonical.append(operation)
    if not canonical:
        raise api_error(422, "RD_SCOPE_CHANGE_INVALID", "At least one scope operation is required")
    return canonical


def _validate_requirement_operation(
    store: Any,
    *,
    version: dict[str, Any],
    operation: dict[str, Any],
) -> None:
    if operation["op"] not in {"add_requirement", "replace_requirement_snapshot"}:
        return
    requirement = _records(store, "requirements").get(str(operation["requirement_id"]))
    assessment = _records(store, "requirement_assessments").get(str(operation["assessment_id"]))
    if (
        requirement is None
        or assessment is None
        or requirement.get("product_id") != version.get("product_id")
        or assessment.get("requirement_id") != requirement.get("id")
        or assessment.get("status") != "accepted"
        or int(assessment.get("requirement_revision") or 1)
        != int(operation["requirement_revision"])
        or assessment.get("final_strategy_snapshot_id") != operation["final_strategy_snapshot_id"]
    ):
        raise api_error(
            422,
            "RD_SCOPE_CHANGE_INVALID",
            "Scope operation does not reference a current accepted assessment",
            {"field": "assessment_id", "retryable": False},
        )
    version_id = version.get("id")
    if (
        operation["op"] == "replace_requirement_snapshot"
        and requirement.get("version_id") != version_id
    ):
        raise api_error(
            422,
            "RD_SCOPE_CHANGE_INVALID",
            "Replacement requirement is not in the current version scope",
            {"field": "requirement_id", "retryable": False},
        )
    if operation["op"] == "add_requirement" and requirement.get("version_id") not in {
        None,
        version_id,
    }:
        raise api_error(
            422,
            "RD_SCOPE_CHANGE_INVALID",
            "Added requirement is already scoped to another version",
            {"field": "requirement_id", "retryable": False},
        )


def _response(
    request: dict[str, Any],
    *,
    current_scope_version: int,
    idempotent_replay: bool,
) -> dict[str, Any]:
    return {
        "scope_change_request": deepcopy(request),
        "current_scope_version": current_scope_version,
        "restart_required": False,
        "idempotent_replay": idempotent_replay,
    }


def create_scope_change_request(
    store: Any,
    *,
    product_version_id: str,
    request_id: str,
    expected_scope_version: int,
    expected_run_generation: int,
    source_run_id: str,
    reason: str,
    operations: list[dict[str, Any]],
    actor: dict[str, Any],
) -> dict[str, Any]:
    """Create exactly one pending, human-governed scope-change proposal."""
    canonical_operations = _canonical_operations(operations)
    repository = getattr(store, "repository", None)
    if repository is not None:
        return _create_scope_change_request_repository(
            store,
            repository=repository,
            product_version_id=product_version_id,
            request_id=request_id,
            expected_scope_version=expected_scope_version,
            expected_run_generation=expected_run_generation,
            source_run_id=source_run_id,
            reason=reason,
            operations=canonical_operations,
            actor=actor,
        )
    version = _records(store, "product_versions").get(product_version_id)
    run = _records(store, "rd_collaboration_runs").get(source_run_id)
    if version is None or run is None or run.get("product_version_id") != product_version_id:
        raise api_error(404, "NOT_FOUND", "Product version or source collaboration run not found")
    if (
        version.get("status") in {"ready_for_release", "deploying", "released"}
        or run.get("status") == "completed"
    ):
        raise api_error(
            409,
            "RD_SCOPE_FROZEN",
            "Version is frozen for release or completed delivery",
            {
                "resolution": "new_planning_version",
                "next_action": "create_followup_requirement",
                "retryable": False,
            },
        )
    if int(version.get("scope_version") or 1) != expected_scope_version:
        raise api_error(
            409,
            "RD_SCOPE_VERSION_CONFLICT",
            "Product version scope is stale",
            {"current_scope_version": version.get("scope_version"), "retryable": False},
        )
    if int(run.get("run_generation") or 1) != expected_run_generation:
        raise api_error(
            409,
            "RD_RUN_GENERATION_CONFLICT",
            "Source run generation is stale",
            {"current_run_generation": run.get("run_generation"), "retryable": False},
        )
    if run.get("status") == "waiting_human":
        raise api_error(
            409,
            "RD_SCOPE_FROZEN",
            "Source run is already waiting for another human decision",
            {
                "decision_request_id": run.get("suspended_decision_request_id"),
                "next_action": "resolve_existing_decision",
            },
        )
    for operation in canonical_operations:
        _validate_requirement_operation(store, version=version, operation=operation)
        if operation["op"] == "remove_requirement":
            requirement = _records(store, "requirements").get(str(operation["requirement_id"]))
            if requirement is None or requirement.get("version_id") != version.get("id"):
                raise api_error(
                    422,
                    "RD_SCOPE_CHANGE_INVALID",
                    "Removed requirement is not in the current version scope",
                    {"field": "requirement_id", "retryable": False},
                )
    existing = next(
        (
            item
            for item in _records(store, "rd_scope_change_requests").values()
            if item.get("product_version_id") == product_version_id
            and item.get("request_id") == request_id
        ),
        None,
    )
    operations_hash = _hash(canonical_operations)
    if existing is not None:
        if existing.get("operations_hash") != operations_hash:
            raise api_error(
                409, "RD_IDEMPOTENCY_CONFLICT", "request_id has another operations hash"
            )
        return _response(
            existing,
            current_scope_version=int(version["scope_version"]),
            idempotent_replay=True,
        )
    if any(
        item.get("product_version_id") == product_version_id
        and item.get("status") == "pending_decision"
        for item in _records(store, "rd_scope_change_requests").values()
    ):
        raise api_error(409, "RD_SCOPE_FROZEN", "A scope-change decision is already pending")
    decision_id = _new_id(store, "decision_request")
    request = {
        "id": _new_id(store, "rd_scope_change_request"),
        "product_version_id": product_version_id,
        "request_id": request_id,
        "source_run_id": source_run_id,
        "source_run_state": run["status"],
        "expected_scope_version": expected_scope_version,
        "expected_run_generation": expected_run_generation,
        "operations_json": canonical_operations,
        "operations_hash": operations_hash,
        "reason": reason,
        "status": "pending_decision",
        "decision_request_id": decision_id,
        "requested_by": actor["id"],
    }
    decision = {
        "id": decision_id,
        "brain_app_id": run.get("brain_app_id", "rd_brain"),
        "product_id": run["product_id"],
        "subject_type": "rd_scope_change_request",
        "subject_id": request["id"],
        "decision_type": "scope_change",
        "plan_version": int(run.get("plan_version") or 0),
        "options_json": [
            {
                "code": "approve_apply_and_restart",
                "outcome": "approve",
                "subject_transition": "cancel_and_restart",
                "input_schema": {},
            },
            {
                "code": "reject_keep_current_scope",
                "outcome": "reject",
                "subject_transition": "resume",
                "input_schema": {},
            },
        ],
        "decision_actor_selector": {"role_codes": ["rd_owner", "product_owner"]},
        "answer_actor_selector": {},
        "answer_schema": {},
        "status": "pending",
        "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        "timeout_policy": "escalate_keep_paused",
        "escalation_target_selector": {"role_codes": ["rd_owner"]},
        "escalation_level": 0,
        "version": 1,
        "created_by": actor["id"],
    }
    _records(store, "rd_scope_change_requests")[request["id"]] = request
    _records(store, "decision_requests")[decision_id] = decision
    for position, operation in enumerate(canonical_operations):
        _records(store, "rd_scope_change_request_operations")[
            _new_id(store, "rd_scope_operation")
        ] = {
            "scope_change_request_id": request["id"],
            "position": position,
            **operation,
        }
    if run.get("status") in {"running", "integrating", "verifying"}:
        run.update(
            {
                "status": "waiting_human",
                "resume_state": request["source_run_state"],
                "suspended_decision_request_id": decision_id,
                "suspended_at": datetime.now(UTC).isoformat(),
                "version": int(run.get("version") or 1) + 1,
            }
        )
    return _response(
        request, current_scope_version=int(version["scope_version"]), idempotent_replay=False
    )


def apply_scope_change_decision(
    store: Any,
    *,
    scope_change_request_id: str,
    decision: str,
    actor: dict[str, Any],
    version: int,
    idempotency_key: str,
) -> dict[str, Any]:
    """Atomically fence the old generation before applying an approved scope bundle."""
    repository = getattr(store, "repository", None)
    get_request = getattr(repository, "get_rd_scope_change_request", None)
    request = (
        get_request(scope_change_request_id)
        if callable(get_request)
        else _records(store, "rd_scope_change_requests").get(scope_change_request_id)
    )
    if request is None:
        raise api_error(404, "NOT_FOUND", "Scope change request not found")
    if decision not in {"approve_apply_and_restart", "reject_keep_current_scope"}:
        raise api_error(422, "RD_SCOPE_CHANGE_INVALID", "Scope decision is invalid")
    if repository is not None:
        execute = getattr(repository, "execute_idempotent_rd_command", None)
        if not callable(execute):
            raise api_error(503, "REPOSITORY_REQUIRED", "Scope-change repository is unavailable")
        command_request = {
            "decision": decision,
            "version": version,
            "actor_id": actor.get("id"),
        }

        def operation(transaction: Any) -> dict[str, Any]:
            result = transaction.apply_scope_change_bundle(
                scope_change_request_id=scope_change_request_id,
                decision=decision,
                decided_by=str(actor["id"]),
                expected_decision_version=version,
                actor_role_codes=[str(role) for role in actor.get("roles") or []],
            )
            return {
                "result_type": "rd_scope_change_request",
                "result_id": scope_change_request_id,
                "http_status": 200,
                "response_json": result,
            }

        result = execute(
            command_type="apply_scope_change_decision",
            aggregate_type="rd_scope_change_request",
            aggregate_id=scope_change_request_id,
            idempotency_key=idempotency_key,
            request_hash=_hash(command_request),
            operation=operation,
        )
        return {
            **dict(result["response_json"]),
            "idempotent_replay": bool(result["idempotent_replay"]),
        }
    command_request = {
        "decision": decision,
        "version": version,
        "actor_id": actor.get("id"),
    }
    command_id = f"apply_scope_change_decision:{scope_change_request_id}:{idempotency_key}"
    commands = _records(store, "rd_command_idempotency_records")
    existing = commands.get(command_id)
    if existing is not None:
        if existing.get("request_hash") != _hash(command_request):
            raise api_error(
                409, "RD_IDEMPOTENCY_CONFLICT", "Scope decision key has another payload"
            )
        return {**deepcopy(existing["response_snapshot"]), "idempotent_replay": True}
    decision_record = _records(store, "decision_requests").get(str(request["decision_request_id"]))
    version_row = _records(store, "product_versions").get(str(request["product_version_id"]))
    run = _records(store, "rd_collaboration_runs").get(str(request["source_run_id"]))
    if decision_record is None or version_row is None or run is None:
        raise api_error(409, "RD_SCOPE_CHANGE_INVALID", "Frozen scope-change state is unavailable")
    if (
        request.get("status") != "pending_decision"
        or int(decision_record.get("version") or 1) != version
    ):
        raise api_error(409, "RD_VERSION_CONFLICT", "Scope-change decision version is stale")
    if int(version_row.get("scope_version") or 1) != int(request["expected_scope_version"]) or int(
        run.get("run_generation") or 1
    ) != int(request["expected_run_generation"]):
        raise api_error(
            409, "RD_SCOPE_VERSION_CONFLICT", "Scope or generation changed before decision"
        )
    if decision == "reject_keep_current_scope":
        decision_record.update(
            {"status": "rejected", "version": version + 1, "decided_by": actor["id"]}
        )
        request["status"] = "rejected"
        if run.get("suspended_decision_request_id") == decision_record["id"]:
            run.update(
                {
                    "status": run.get("resume_state"),
                    "resume_state": None,
                    "suspended_decision_request_id": None,
                    "suspended_at": None,
                    "version": int(run.get("version") or 1) + 1,
                }
            )
        response = {
            "scope_change_request": deepcopy(request),
            "run": deepcopy(run),
            "terminal_run_id": None,
            "restart_required": False,
            "next_state": "rejected",
            "idempotent_replay": False,
        }
        commands[command_id] = {
            "id": command_id,
            "command_type": "apply_scope_change_decision",
            "aggregate_id": scope_change_request_id,
            "idempotency_key": idempotency_key,
            "request_hash": _hash(command_request),
            "response_hash": _hash(response),
            "response_snapshot": deepcopy(response),
        }
        return response
    for item in _records(store, "rd_work_items").values():
        if item.get("collaboration_run_id") == run["id"] and item.get("status") not in {
            "completed",
            "failed",
            "cancelled",
        }:
            item.update(
                {
                    "status": "cancelled",
                    "lease_owner": None,
                    "lease_expires_at": None,
                    "version": int(item.get("version") or 1) + 1,
                }
            )
    for attempt in _records(store, "rd_work_item_attempts").values():
        work_item = _records(store, "rd_work_items").get(str(attempt.get("work_item_id")))
        if (
            work_item
            and work_item.get("collaboration_run_id") == run["id"]
            and attempt.get("status")
            not in {
                "completed",
                "failed",
                "cancelled",
                "expired",
            }
        ):
            attempt["status"] = "cancelled"
    for operation in request["operations_json"]:
        if operation["op"] == "add_requirement":
            requirement = _records(store, "requirements")[operation["requirement_id"]]
            requirement.update({"version_id": version_row["id"], "status": "planned"})
            _records(store, "rd_product_version_requirement_provenance")[
                f"{version_row['id']}:{requirement['id']}"
            ] = {
                "product_version_id": version_row["id"],
                "requirement_id": requirement["id"],
                "requirement_revision": operation["requirement_revision"],
                "assessment_id": operation["assessment_id"],
                "final_strategy_snapshot_id": operation["final_strategy_snapshot_id"],
                "applied_scope_change_request_id": request["id"],
            }
        elif operation["op"] == "replace_requirement_snapshot":
            requirement = _records(store, "requirements")[operation["requirement_id"]]
            requirement["assessment_revision"] = operation["requirement_revision"]
            _records(store, "rd_product_version_requirement_provenance")[
                f"{version_row['id']}:{requirement['id']}"
            ] = {
                "product_version_id": version_row["id"],
                "requirement_id": requirement["id"],
                "requirement_revision": operation["requirement_revision"],
                "assessment_id": operation["assessment_id"],
                "final_strategy_snapshot_id": operation["final_strategy_snapshot_id"],
                "applied_scope_change_request_id": request["id"],
            }
        elif operation["op"] == "remove_requirement":
            requirement = _records(store, "requirements").get(operation["requirement_id"])
            if requirement:
                requirement.update({"version_id": None, "status": "approved"})
                _records(store, "rd_product_version_requirement_provenance").pop(
                    f"{version_row['id']}:{requirement['id']}", None
                )
    run.update(
        {
            "status": "cancelled",
            "completion_reason": "scope_change",
            "resume_state": None,
            "suspended_decision_request_id": None,
            "suspended_at": None,
            "version": int(run.get("version") or 1) + 1,
        }
    )
    version_row["scope_version"] = int(version_row.get("scope_version") or 1) + 1
    request.update(
        {
            "status": "applied",
            "applied_scope_version": version_row["scope_version"],
            "applied_at": datetime.now(UTC).isoformat(),
        }
    )
    decision_record.update(
        {"status": "approved", "version": version + 1, "decided_by": actor["id"]}
    )
    response = {
        "scope_change_request": deepcopy(request),
        "run": deepcopy(run),
        "terminal_run_id": run["id"],
        "restart_required": True,
        "next_state": "applied",
        "idempotent_replay": False,
    }
    commands[command_id] = {
        "id": command_id,
        "command_type": "apply_scope_change_decision",
        "aggregate_id": scope_change_request_id,
        "idempotency_key": idempotency_key,
        "request_hash": _hash(command_request),
        "response_hash": _hash(response),
        "response_snapshot": deepcopy(response),
    }
    return response


def _create_scope_change_request_repository(
    store: Any,
    *,
    repository: Any,
    product_version_id: str,
    request_id: str,
    expected_scope_version: int,
    expected_run_generation: int,
    source_run_id: str,
    reason: str,
    operations: list[dict[str, Any]],
    actor: dict[str, Any],
) -> dict[str, Any]:
    get_version = getattr(repository, "get_product_version", None)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    create = getattr(repository, "create_scope_change_request", None)
    if not all(callable(method) for method in (get_version, get_run, create)):
        raise api_error(503, "REPOSITORY_REQUIRED", "Scope-change repository is unavailable")
    version = get_version(product_version_id)
    run = get_run(source_run_id)
    if version is None or run is None:
        raise api_error(404, "NOT_FOUND", "Product version or source collaboration run not found")
    decision_id = _new_id(store, "decision_request")
    request = {
        "id": _new_id(store, "rd_scope_change_request"),
        "product_version_id": product_version_id,
        "request_id": request_id,
        "source_run_id": source_run_id,
        "source_run_state": run["status"],
        "expected_scope_version": expected_scope_version,
        "expected_run_generation": expected_run_generation,
        "operations_json": operations,
        "operations_hash": _hash(operations),
        "reason": reason,
        "status": "pending_decision",
        "decision_request_id": decision_id,
        "requested_by": actor["id"],
    }
    decision = {
        "id": decision_id,
        "brain_app_id": run["brain_app_id"],
        "product_id": run["product_id"],
        "subject_type": "rd_scope_change_request",
        "subject_id": request["id"],
        "decision_type": "scope_change",
        "plan_version": int(run.get("plan_version") or 0),
        "options_json": [
            {"code": "approve_apply_and_restart", "outcome": "approve", "input_schema": {}},
            {"code": "reject_keep_current_scope", "outcome": "reject", "input_schema": {}},
        ],
        "options_hash": _hash(["approve_apply_and_restart", "reject_keep_current_scope"]),
        "decision_actor_selector": {"role_codes": ["rd_owner", "product_owner"]},
        "answer_actor_selector": {},
        "answer_schema": {},
        "status": "pending",
        "expires_at": datetime.now(UTC) + timedelta(hours=24),
        "timeout_policy": "escalate_keep_paused",
        "escalation_target_selector": {"role_codes": ["rd_owner"]},
        "escalation_level": 0,
        "version": 1,
        "created_by": actor["id"],
    }
    saved = create(request=request, operations=operations, decision_request=decision)
    return _response(
        saved, current_scope_version=int(version["scope_version"]), idempotent_replay=False
    )
