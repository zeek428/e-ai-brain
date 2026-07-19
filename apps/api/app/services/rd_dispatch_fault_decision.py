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
