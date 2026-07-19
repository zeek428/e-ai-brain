"""Classify automatic dispatch faults and freeze permanent ones for human repair."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException

from app.api.deps import api_error
from app.core.repositories.rd_collaboration import (
    RdCollaborationRepositoryError,
    RdCollaborationVersionConflictError,
)
from app.services.ai_executor_runner_safety import (
    RUNNER_SAFETY_POLICY_VERSION,
    safe_runner_blocked_operations,
)

DispatchFaultOutcome = Literal["deferred", "escalated", "retryable"]

_PERMANENT_FAULT_MESSAGES = {
    "AI_EXECUTOR_RUNNER_DISABLED": "Frozen runner configuration is disabled",
    "AI_EXECUTOR_RUNNER_NOT_FOUND": "Frozen runner configuration is unavailable",
    "AI_EXECUTOR_RUNNER_UNAVAILABLE": "Frozen runner configuration cannot execute the work item",
    "AI_EXECUTOR_WORKSPACE_NOT_ALLOWED": (
        "Frozen runner safety configuration rejected the dispatch"
    ),
    "RD_EXECUTION_POLICY_INVALID": "Frozen execution policy configuration is invalid",
    "RD_EXECUTION_POLICY_REQUIRED": "Frozen execution policy configuration is unavailable",
    "RD_EXECUTOR_INSTRUCTION_REQUIRED": "Frozen executor instruction configuration is invalid",
    "RD_EXECUTOR_UNAVAILABLE": "Frozen executor configuration is unavailable",
    "RD_ROLE_ASSIGNMENT_REQUIRED": "Frozen role or executor assignment is unavailable",
}


@dataclass(frozen=True)
class DispatchFault:
    outcome: DispatchFaultOutcome
    error_code: str
    safe_message: str
    attempt_no: int | None = None
    blocked_operations: tuple[str, ...] = ()


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _records(store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    records = getattr(store, collection_name, None)
    if not isinstance(records, dict):
        records = {}
        setattr(store, collection_name, records)
    return records


def _error_code(exc: HTTPException | RdCollaborationRepositoryError) -> str:
    if isinstance(exc, RdCollaborationRepositoryError):
        return str(exc.code or "").strip().upper()
    detail = exc.detail
    return str(detail.get("code") or "").strip().upper() if isinstance(detail, dict) else ""


def classify_dispatch_fault(
    exc: HTTPException | RdCollaborationRepositoryError,
) -> DispatchFault:
    """Return a deterministic outcome without retaining exception details."""
    code = _error_code(exc)
    if code == "RD_SEAT_CAPACITY_EXHAUSTED":
        return DispatchFault(
            outcome="deferred",
            error_code=code,
            safe_message="Frozen collaboration seat is at capacity",
        )
    if code == "AI_EXECUTOR_APPROVAL_REQUIRED":
        detail = (
            exc.detail if isinstance(exc, HTTPException) and isinstance(exc.detail, dict) else {}
        )
        try:
            attempt_no = int(detail.get("attempt_no") or 0)
        except (TypeError, ValueError):
            attempt_no = 0
        return DispatchFault(
            outcome="escalated",
            error_code=code,
            safe_message="Runner safety approval is required for blocked operations",
            attempt_no=attempt_no if attempt_no > 0 else None,
            blocked_operations=tuple(
                safe_runner_blocked_operations(detail.get("blocked_operations"))
            ),
        )
    safe_message = _PERMANENT_FAULT_MESSAGES.get(code)
    if safe_message is not None:
        return DispatchFault(outcome="escalated", error_code=code, safe_message=safe_message)
    return DispatchFault(
        outcome="retryable",
        error_code="RD_AUTO_DISPATCH_RETRYABLE",
        safe_message="Dispatch will be retried from durable work-item state",
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _human_decision_selector(reviewer: dict[str, Any] | None) -> dict[str, list[str]]:
    if (
        reviewer
        and reviewer.get("status", "active") == "active"
        and reviewer.get("subject_type") == "human_user"
    ):
        return {"seat_ids": [str(reviewer["id"])]}
    return {"role_codes": ["rd_owner"]}


def runner_safety_approval_request_id(
    *,
    work_item_id: str,
    attempt_no: int,
    renewal_no: int = 0,
) -> str:
    """Return the stable approval identity for the next durable attempt."""
    base = f"rd-runner-safety:{work_item_id}:attempt:{attempt_no}"
    return f"{base}:renewal:{renewal_no}" if renewal_no > 0 else base


def runner_safety_decision_id(
    *,
    work_item_id: str,
    attempt_no: int,
    renewal_no: int = 0,
) -> str:
    base = f"runner-safety-approval:{work_item_id}:attempt:{attempt_no}"
    return f"{base}:renewal:{renewal_no}" if renewal_no > 0 else base


def runner_safety_decision_options() -> list[dict[str, Any]]:
    return [
        {
            "code": "authorize_blocked_operations",
            "input_schema": {},
            "outcome": "approve",
            "subject_transition": "resume",
        },
        {
            "code": "cancel_work_item",
            "input_schema": {},
            "outcome": "reject",
            "requires_comment": True,
            "subject_transition": "cancelled",
        },
    ]


def runner_safety_decision_recommendation(approval_request_id: str) -> dict[str, str]:
    return {
        "action": "authorize_blocked_operations_or_cancel",
        "approval_request_id": approval_request_id,
    }


def _load_runner_safety_approval_request(store: Any, record_id: str) -> dict[str, Any] | None:
    repository = getattr(store, "repository", None)
    get_request = getattr(repository, "get_ai_executor_approval_request", None)
    record = (
        get_request(record_id)
        if callable(get_request)
        else _records(store, "ai_executor_approval_requests").get(record_id)
    )
    return dict(record) if isinstance(record, dict) else None


def current_runner_safety_approval_request(
    store: Any,
    *,
    work_item_id: str,
    attempt_no: int,
) -> tuple[str, dict[str, Any] | None, int]:
    """Return the latest contiguous immutable approval identity for one attempt."""
    renewal_no = 0
    record_id = runner_safety_approval_request_id(
        work_item_id=work_item_id,
        attempt_no=attempt_no,
    )
    record = _load_runner_safety_approval_request(store, record_id)
    if record is None:
        return record_id, None, renewal_no
    while True:
        next_renewal_no = renewal_no + 1
        next_record_id = runner_safety_approval_request_id(
            work_item_id=work_item_id,
            attempt_no=attempt_no,
            renewal_no=next_renewal_no,
        )
        next_record = _load_runner_safety_approval_request(store, next_record_id)
        if next_record is None:
            return record_id, record, renewal_no
        renewal_no = next_renewal_no
        record_id = next_record_id
        record = next_record


def _approved_request_expired(record: dict[str, Any]) -> bool:
    if record.get("status") == "expired":
        return True
    approval = record.get("approval")
    expires_at = approval.get("expires_at") if isinstance(approval, dict) else None
    if not expires_at:
        return False
    try:
        parsed = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC) <= _now()


def _next_attempt_no(store: Any, work_item_id: str) -> int:
    repository = getattr(store, "repository", None)
    list_attempts = getattr(repository, "list_rd_work_item_attempts", None)
    attempts = (
        list_attempts(work_item_id)
        if callable(list_attempts)
        else [
            item
            for item in _records(store, "rd_work_item_attempts").values()
            if item.get("work_item_id") == work_item_id
        ]
    )
    return 1 + max((int(item.get("attempt_no") or 0) for item in attempts), default=0)


def _runner_identity(store: Any, work_item: dict[str, Any]) -> tuple[str, str]:
    repository = getattr(store, "repository", None)
    seat_id = str(work_item.get("owner_seat_id") or "")
    get_seat = getattr(repository, "get_rd_run_seat", None)
    seat = get_seat(seat_id) if callable(get_seat) else _records(store, "rd_run_seats").get(seat_id)
    profile_id = str((seat or {}).get("executor_profile_id") or "")
    get_profile = getattr(repository, "get_rd_executor_profile", None)
    profile = (
        get_profile(profile_id)
        if callable(get_profile)
        else _records(store, "rd_executor_profiles").get(profile_id)
    )
    executor_type = str((profile or {}).get("executor_type") or "").strip()
    runner_id = str((profile or {}).get("runner_id") or "").strip()
    if not executor_type or not runner_id:
        raise api_error(
            409,
            "RD_EXECUTOR_UNAVAILABLE",
            "Frozen executor configuration is unavailable",
        )
    return executor_type, runner_id


def _runner_safety_approval_records(
    store: Any,
    *,
    run: dict[str, Any],
    work_item: dict[str, Any],
    fault: DispatchFault,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    attempt_no = _next_attempt_no(store, str(work_item["id"]))
    if fault.attempt_no is not None and fault.attempt_no != attempt_no:
        raise api_error(
            409,
            "RD_WORK_ITEM_STATE_INVALID",
            "Work item attempt identity changed before approval suspension",
        )
    blocked_operations = list(fault.blocked_operations)
    if not blocked_operations:
        raise api_error(
            409,
            "RD_WORK_ITEM_STATE_INVALID",
            "Runner safety approval has no stable blocked-operation evidence",
        )
    work_item_id = str(work_item["id"])
    approval_request_id, existing_approval_request, renewal_no = (
        current_runner_safety_approval_request(
            store,
            work_item_id=work_item_id,
            attempt_no=attempt_no,
        )
    )
    if existing_approval_request is not None:
        status = str(existing_approval_request.get("status") or "")
        if status in {"approved", "expired"} and _approved_request_expired(
            existing_approval_request
        ):
            renewal_no += 1
            approval_request_id = runner_safety_approval_request_id(
                work_item_id=work_item_id,
                attempt_no=attempt_no,
                renewal_no=renewal_no,
            )
        elif status != "pending":
            raise api_error(
                409,
                "RD_DECISION_REQUIRED",
                "Runner safety approval request cannot be renewed",
            )
    identity_suffix = f":renewal:{renewal_no}" if renewal_no > 0 else ""
    decision_id = runner_safety_decision_id(
        work_item_id=work_item_id,
        attempt_no=attempt_no,
        renewal_no=renewal_no,
    )
    executor_type, runner_id = _runner_identity(store, work_item)
    now = _now().isoformat()
    approval_request_snapshot = {
        "approval_request_id": approval_request_id,
        "attempt_no": attempt_no,
        "blocked_operations": blocked_operations,
        "policy_version": RUNNER_SAFETY_POLICY_VERSION,
        "source": "rd_collaboration_work_item",
        "work_item_id": work_item_id,
    }
    if renewal_no > 0:
        approval_request_snapshot["renewal_no"] = renewal_no
    approval_request = {
        "id": approval_request_id,
        "action_id": None,
        "ai_task_id": None,
        "approval": {},
        "approval_request": approval_request_snapshot,
        "blocked_operations": blocked_operations,
        "connection_id": None,
        "created_at": now,
        "executor_type": executor_type,
        "requested_at": now,
        "requested_by": str(run["created_by"]),
        "risk_level": "high",
        "runner_id": runner_id,
        "scheduled_job_id": None,
        "scheduled_job_run_id": None,
        "status": "pending",
        "updated_at": now,
        # The generic table predates RD collaboration. Keep the required field
        # empty so approval evidence never persists a workspace path.
        "workspace_root": "",
    }
    repository = getattr(store, "repository", None)
    get_reviewer = getattr(repository, "get_rd_run_seat", None)
    reviewer_seat_id = str(work_item.get("reviewer_seat_id") or "")
    reviewer = (
        get_reviewer(reviewer_seat_id)
        if callable(get_reviewer)
        else _records(store, "rd_run_seats").get(reviewer_seat_id)
    )
    selector = _human_decision_selector(reviewer)
    options = runner_safety_decision_options()
    safe_evidence = {
        "approval_request_id": approval_request_id,
        "attempt_no": attempt_no,
        "blocked_operations": blocked_operations,
        "kind": "runner_safety_approval",
        "policy_version": RUNNER_SAFETY_POLICY_VERSION,
    }
    if renewal_no > 0:
        safe_evidence["renewal_no"] = renewal_no
    decision = {
        "id": decision_id,
        "brain_app_id": run.get("brain_app_id", "rd_brain"),
        "product_id": run["product_id"],
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "decision_type": "runner_safety_approval",
        "plan_version": int(run.get("plan_version") or 0),
        "options_json": options,
        "options_hash": _canonical_hash(options),
        "evidence_json": [safe_evidence],
        "recommendation_json": runner_safety_decision_recommendation(approval_request_id),
        "decision_actor_selector": selector,
        "answer_actor_selector": {},
        "answer_schema": {},
        "status": "pending",
        "expires_at": (_now() + timedelta(hours=24)).isoformat(),
        "timeout_policy": "escalate_keep_paused",
        "escalation_target_selector": selector,
        "escalation_level": 0,
        "version": 1,
        "created_by": run["created_by"],
    }
    event = {
        "id": (
            f"runner-safety-approval-required:{work_item_id}:attempt:{attempt_no}{identity_suffix}"
        ),
        "collaboration_run_id": str(run["id"]),
        "event_type": "work_item.runner_safety_approval_required",
        "event_key": (
            f"runner-safety-approval-required:{work_item_id}:attempt:{attempt_no}{identity_suffix}"
        ),
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "payload_json": safe_evidence,
    }
    audit = {
        "id": (
            f"runner-safety-approval-required-audit:{work_item_id}:attempt:{attempt_no}"
            f"{identity_suffix}"
        ),
        "event_type": "rd_work_item.runner_safety_approval_required",
        "actor_id": str(run["created_by"]),
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "payload": safe_evidence,
    }
    return approval_request, decision, event, audit


def escalate_dispatch_fault_for_human(
    store: Any,
    *,
    collaboration_run_id: str,
    work_item_id: str,
    fault: DispatchFault,
) -> dict[str, Any]:
    """Atomically pause one ready item and freeze a repair-or-cancel decision."""
    if fault.outcome != "escalated":
        raise ValueError("only permanent dispatch faults can be escalated")
    repository = getattr(store, "repository", None)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    get_item = getattr(repository, "get_rd_work_item", None)
    get_seat = getattr(repository, "get_rd_run_seat", None)
    run = (
        get_run(collaboration_run_id)
        if callable(get_run)
        else _records(store, "rd_collaboration_runs").get(collaboration_run_id)
    )
    work_item = (
        get_item(work_item_id)
        if callable(get_item)
        else _records(store, "rd_work_items").get(work_item_id)
    )
    if (
        run is None
        or work_item is None
        or work_item.get("collaboration_run_id") != collaboration_run_id
    ):
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Work item is no longer available")
    if work_item.get("status") not in {"ready", "rework_required"}:
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Work item is no longer dispatchable")

    if fault.error_code == "AI_EXECUTOR_APPROVAL_REQUIRED":
        approval_request, decision, event, audit_event = _runner_safety_approval_records(
            store,
            run=run,
            work_item=work_item,
            fault=fault,
        )
        version = int(work_item.get("version") or 1)
        execute = getattr(repository, "execute_idempotent_rd_command", None)
        if callable(execute):
            renewal_no = int(
                (approval_request.get("approval_request") or {}).get("renewal_no") or 0
            )
            identity_suffix = f":renewal:{renewal_no}" if renewal_no > 0 else ""

            def approval_operation(transaction: Any) -> dict[str, Any]:
                transaction.save_runner_safety_approval_request(approval_request)
                paused = transaction.suspend_work_item_for_decision(
                    work_item_id=work_item_id,
                    decision_request=decision,
                    expected_version=version,
                )
                transaction.save_rd_collaboration_event_record(event)
                transaction.save_audit_event(audit_event)
                return {
                    "result_type": "decision_request",
                    "result_id": paused["decision_request"]["id"],
                    "http_status": 202,
                    "response_json": {
                        **paused,
                        "approval_request": approval_request,
                    },
                }

            try:
                result = execute(
                    command_type="runner_safety_approval_required",
                    aggregate_type="rd_work_item",
                    aggregate_id=work_item_id,
                    idempotency_key=(f"attempt:{fault.attempt_no or 0}{identity_suffix}"),
                    request_hash=_canonical_hash(
                        {
                            "approval_request_id": approval_request["id"],
                            "blocked_operations": approval_request["blocked_operations"],
                            "plan_version": decision["plan_version"],
                            "resume_state": work_item["status"],
                        }
                    ),
                    command_record_id=(
                        f"runner-safety-approval-command:{work_item_id}:"
                        f"attempt:{fault.attempt_no or 0}{identity_suffix}"
                    ),
                    operation=approval_operation,
                )
            except RdCollaborationVersionConflictError as exc:
                raise api_error(409, exc.code, str(exc), exc.details) from exc
            except RdCollaborationRepositoryError as exc:
                raise api_error(409, exc.code, str(exc), exc.details) from exc
            return {
                **dict(result["response_json"]),
                "idempotent_replay": bool(result["idempotent_replay"]),
            }

        existing = _records(store, "ai_executor_approval_requests").get(approval_request["id"])
        if existing is not None and existing.get("status") != "pending":
            raise api_error(
                409,
                "RD_DECISION_REQUIRED",
                "Runner safety approval request is no longer pending",
            )
        if existing is None:
            _records(store, "ai_executor_approval_requests")[approval_request["id"]] = (
                approval_request
            )
        _records(store, "decision_requests")[decision["id"]] = decision
        work_item.update(
            {
                "status": "waiting_human",
                "resume_state": work_item["status"],
                "suspended_attempt_id": None,
                "suspended_decision_request_id": decision["id"],
                "suspended_at": _now().isoformat(),
                "lease_owner": None,
                "lease_expires_at": None,
                "version": version + 1,
            }
        )
        _records(store, "rd_collaboration_events")[event["id"]] = event
        audit = getattr(store, "audit", None)
        if callable(audit):
            audit(**{key: value for key, value in audit_event.items() if key != "id"})
        return {
            "approval_request": deepcopy(approval_request),
            "decision_request": deepcopy(decision),
            "work_item": deepcopy(work_item),
            "idempotent_replay": existing is not None,
        }

    version = int(work_item.get("version") or 1)
    decision_id = f"auto-dispatch-fault:{work_item_id}:{version}"
    selector = _human_decision_selector(
        get_seat(str(work_item.get("reviewer_seat_id") or ""))
        if callable(get_seat)
        else _records(store, "rd_run_seats").get(str(work_item.get("reviewer_seat_id") or ""))
    )
    options = [
        {
            "code": "retry_after_configuration_repair",
            "input_schema": {},
            "outcome": "approve",
            "subject_transition": "resume",
        },
        {
            "code": "cancel_work_item",
            "input_schema": {},
            "outcome": "reject",
            "requires_comment": True,
            "subject_transition": "cancelled",
        },
    ]
    decision = {
        "id": decision_id,
        "brain_app_id": run.get("brain_app_id", "rd_brain"),
        "product_id": run["product_id"],
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "decision_type": "dispatch_fault_resolution",
        "plan_version": int(run.get("plan_version") or 0),
        "options_json": options,
        "options_hash": _canonical_hash(options),
        "evidence_json": [
            {
                "error_code": fault.error_code,
                "kind": "dispatch_fault",
                "message": fault.safe_message,
            }
        ],
        "recommendation_json": {
            "action": "repair_configuration_or_cancel",
            "error_code": fault.error_code,
        },
        "decision_actor_selector": selector,
        "answer_actor_selector": {},
        "answer_schema": {},
        "status": "pending",
        "expires_at": (_now() + timedelta(hours=24)).isoformat(),
        "timeout_policy": "escalate_keep_paused",
        "escalation_target_selector": selector,
        "escalation_level": 0,
        "version": 1,
        "created_by": run["created_by"],
    }
    event = {
        "id": f"dispatch-fault-escalation:{work_item_id}:{version}",
        "collaboration_run_id": collaboration_run_id,
        "event_type": "work_item.dispatch_fault_escalated",
        "event_key": f"dispatch-fault-escalation:{work_item_id}:{version}",
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "payload_json": {
            "decision_request_id": decision_id,
            "error_code": fault.error_code,
            "message": fault.safe_message,
        },
    }

    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if callable(execute):

        def operation(transaction: Any) -> dict[str, Any]:
            paused = transaction.suspend_work_item_for_decision(
                work_item_id=work_item_id,
                decision_request=decision,
                expected_version=version,
            )
            transaction.save_rd_collaboration_event_record(event)
            transaction.save_audit_event(
                {
                    "id": f"dispatch-fault-escalation-audit:{work_item_id}:{version}",
                    "event_type": "rd_work_item.dispatch_fault_escalated",
                    "actor_id": run["created_by"],
                    "subject_type": "rd_work_item",
                    "subject_id": work_item_id,
                    "payload": {
                        "decision_request_id": decision_id,
                        "error_code": fault.error_code,
                        "message": fault.safe_message,
                    },
                }
            )
            return {
                "result_type": "decision_request",
                "result_id": paused["decision_request"]["id"],
                "http_status": 202,
                "response_json": paused,
            }

        try:
            result = execute(
                command_type="dispatch_fault_escalation",
                aggregate_type="rd_work_item",
                aggregate_id=work_item_id,
                idempotency_key=f"fault:{version}",
                request_hash=_canonical_hash(
                    {
                        "decision_type": decision["decision_type"],
                        "error_code": fault.error_code,
                        "plan_version": decision["plan_version"],
                        "resume_state": work_item["status"],
                    }
                ),
                command_record_id=f"dispatch-fault-escalation-command:{work_item_id}:{version}",
                operation=operation,
            )
        except RdCollaborationVersionConflictError as exc:
            raise api_error(409, exc.code, str(exc), exc.details) from exc
        except RdCollaborationRepositoryError as exc:
            raise api_error(409, exc.code, str(exc), exc.details) from exc
        return {
            **dict(result["response_json"]),
            "idempotent_replay": bool(result["idempotent_replay"]),
        }

    _records(store, "decision_requests")[decision_id] = decision
    work_item.update(
        {
            "status": "waiting_human",
            "resume_state": work_item["status"],
            "suspended_attempt_id": None,
            "suspended_decision_request_id": decision_id,
            "suspended_at": _now().isoformat(),
            "lease_owner": None,
            "lease_expires_at": None,
            "version": version + 1,
        }
    )
    _records(store, "rd_collaboration_events")[event["id"]] = event
    audit = getattr(store, "audit", None)
    if callable(audit):
        audit(
            event_type="rd_work_item.dispatch_fault_escalated",
            actor_id=str(run["created_by"]),
            subject_type="rd_work_item",
            subject_id=work_item_id,
            payload={
                "decision_request_id": decision_id,
                "error_code": fault.error_code,
                "message": fault.safe_message,
            },
        )
    return {
        "decision_request": deepcopy(decision),
        "work_item": deepcopy(work_item),
        "idempotent_replay": False,
    }
