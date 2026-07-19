"""Durable human approval gate for high-risk AI work-item dispatch."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from app.api.deps import api_error
from app.core.repositories.rd_collaboration import (
    RdCollaborationRepositoryError,
    RdCollaborationVersionConflictError,
)

_HIGH_RISK_DISPATCH_DECISION_TYPE = "high_risk_ai_dispatch"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _records(store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    records = getattr(store, collection_name, None)
    if not isinstance(records, dict):
        records = {}
        setattr(store, collection_name, records)
    return records


def _now() -> datetime:
    return datetime.now(UTC)


def _decision_id(work_item: dict[str, Any]) -> str:
    return f"auto-high-risk-dispatch:{work_item['id']}:{int(work_item.get('version') or 1)}"


def _human_decision_selector(reviewer: dict[str, Any] | None) -> dict[str, list[str]]:
    if (
        reviewer
        and reviewer.get("status", "active") == "active"
        and reviewer.get("subject_type") == "human_user"
    ):
        return {"seat_ids": [str(reviewer["id"])]}
    return {"role_codes": ["rd_owner"]}


def _decision_record(
    *,
    run: dict[str, Any],
    work_item: dict[str, Any],
    reviewer: dict[str, Any] | None,
) -> dict[str, Any]:
    selector = _human_decision_selector(reviewer)
    options = [
        {
            "code": "approve_dispatch",
            "input_schema": {},
            "outcome": "approve",
            "subject_transition": "ready",
        },
        {
            "code": "cancel_work_item",
            "input_schema": {},
            "outcome": "reject",
            "requires_comment": True,
            "subject_transition": "cancelled",
        },
    ]
    return {
        "id": _decision_id(work_item),
        "brain_app_id": run.get("brain_app_id", "rd_brain"),
        "product_id": run["product_id"],
        "subject_type": "rd_work_item",
        "subject_id": work_item["id"],
        "decision_type": _HIGH_RISK_DISPATCH_DECISION_TYPE,
        "plan_version": int(run.get("plan_version") or 0),
        "options_json": options,
        "options_hash": _canonical_hash(options),
        "evidence_json": [
            {
                "kind": "risk_gate",
                "risk_level": str(work_item.get("risk_level") or "high").lower(),
                "work_item_id": work_item["id"],
            }
        ],
        "recommendation_json": {"action": "human_approval_required"},
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


def high_risk_dispatch_is_approved(
    store: Any,
    *,
    collaboration_run_id: str,
    work_item_id: str,
) -> bool:
    """Return whether the active plan has a human approval to dispatch this item."""
    repository = getattr(store, "repository", None)
    get_run = getattr(repository, "get_rd_collaboration_run", None)
    list_decisions = getattr(repository, "list_decision_requests", None)
    run = (
        get_run(collaboration_run_id)
        if callable(get_run)
        else _records(store, "rd_collaboration_runs").get(collaboration_run_id)
    )
    if run is None:
        return False
    decisions = (
        list_decisions(subject_type="rd_work_item", subject_id=work_item_id)
        if callable(list_decisions)
        else [
            value
            for value in _records(store, "decision_requests").values()
            if value.get("subject_type") == "rd_work_item"
            and value.get("subject_id") == work_item_id
        ]
    )
    return any(
        decision.get("decision_type") == _HIGH_RISK_DISPATCH_DECISION_TYPE
        and decision.get("status") == "approved"
        and decision.get("selected_option_code") == "approve_dispatch"
        and int(decision.get("plan_version") or 0) == int(run.get("plan_version") or 0)
        for decision in decisions
    )


def require_human_approval_for_high_risk_dispatch(
    store: Any,
    *,
    collaboration_run_id: str,
    work_item_id: str,
) -> dict[str, Any]:
    """Pause an eligible work item and create its one immutable approval request.

    The PostgreSQL path keeps the decision, pause, collaboration event, audit
    record, and idempotency record in one transaction.  The memory path is a
    test double with the same state transition and frozen request identity.
    """
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
        raise api_error(404, "NOT_FOUND", "Collaboration work item not found")
    if str(work_item.get("risk_level") or "").lower() not in {"high", "critical"}:
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Work item is not high risk")
    reviewer = (
        get_seat(str(work_item.get("reviewer_seat_id") or ""))
        if callable(get_seat)
        else _records(store, "rd_run_seats").get(str(work_item.get("reviewer_seat_id") or ""))
    )
    decision = _decision_record(run=run, work_item=work_item, reviewer=reviewer)
    event = {
        "id": f"high-risk-dispatch-gate:{work_item_id}:{int(work_item.get('version') or 1)}",
        "collaboration_run_id": collaboration_run_id,
        "event_type": "work_item.high_risk_dispatch_approval_required",
        "event_key": f"high-risk-dispatch-gate:{work_item_id}:{int(work_item.get('version') or 1)}",
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "payload_json": {
            "decision_request_id": decision["id"],
            "risk_level": work_item["risk_level"],
        },
    }

    execute = getattr(repository, "execute_idempotent_rd_command", None)
    if callable(execute):

        def operation(transaction: Any) -> dict[str, Any]:
            paused = transaction.suspend_work_item_for_decision(
                work_item_id=work_item_id,
                decision_request=decision,
                expected_version=int(work_item.get("version") or 1),
            )
            transaction.save_rd_collaboration_event_record(event)
            transaction.save_audit_event(
                {
                    "id": (
                        "high-risk-dispatch-gate-audit:"
                        f"{work_item_id}:{int(work_item.get('version') or 1)}"
                    ),
                    "event_type": "rd_work_item.high_risk_dispatch_approval_required",
                    "actor_id": run["created_by"],
                    "subject_type": "rd_work_item",
                    "subject_id": work_item_id,
                    "payload": {"decision_request_id": decision["id"]},
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
                command_type="high_risk_work_item_dispatch_gate",
                aggregate_type="rd_work_item",
                aggregate_id=work_item_id,
                idempotency_key=f"risk-gate:{int(work_item.get('version') or 1)}",
                request_hash=_canonical_hash(
                    {
                        "decision_type": decision["decision_type"],
                        "plan_version": decision["plan_version"],
                        "risk_level": work_item["risk_level"],
                    }
                ),
                command_record_id=(
                    "high-risk-dispatch-gate-command:"
                    f"{work_item_id}:{int(work_item.get('version') or 1)}"
                ),
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

    if work_item.get("status") == "waiting_human":
        if work_item.get("suspended_decision_request_id") == decision["id"]:
            return {
                "decision_request": deepcopy(_records(store, "decision_requests")[decision["id"]]),
                "work_item": deepcopy(work_item),
                "idempotent_replay": True,
            }
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Work item is already paused")
    if work_item.get("status") not in {"ready", "rework_required"}:
        raise api_error(409, "RD_WORK_ITEM_STATE_INVALID", "Work item cannot be paused")
    _records(store, "decision_requests")[decision["id"]] = decision
    work_item.update(
        {
            "status": "waiting_human",
            "resume_state": "ready",
            "suspended_attempt_id": None,
            "suspended_decision_request_id": decision["id"],
            "suspended_at": _now().isoformat(),
            "lease_owner": None,
            "lease_expires_at": None,
            "version": int(work_item.get("version") or 1) + 1,
        }
    )
    _records(store, "rd_collaboration_events")[event["id"]] = event
    audit = getattr(store, "audit", None)
    if callable(audit):
        audit(
            event_type="rd_work_item.high_risk_dispatch_approval_required",
            actor_id=str(run["created_by"]),
            subject_type="rd_work_item",
            subject_id=work_item_id,
            payload={"decision_request_id": decision["id"]},
        )
    return {
        "decision_request": deepcopy(decision),
        "work_item": deepcopy(work_item),
        "idempotent_replay": False,
    }
