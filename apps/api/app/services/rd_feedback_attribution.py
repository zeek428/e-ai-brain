"""Immutable role-feedback attribution for later experience review and reuse."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from app.api.deps import api_error


def _records(store: Any, name: str) -> dict[str, dict[str, Any]]:
    records = getattr(store, name, None)
    if not isinstance(records, dict):
        records = {}
        setattr(store, name, records)
    return records


def _new_id(store: Any, prefix: str) -> str:
    factory = getattr(store, "new_id", None)
    if callable(factory):
        return str(factory(prefix))
    return f"{prefix}_{hashlib.sha256(prefix.encode()).hexdigest()[:16]}"


def _hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def record_role_feedback(
    store: Any,
    *,
    collaboration_run_id: str,
    work_item_id: str | None,
    source_event_id: str,
    outcome: str,
    producer: dict[str, Any],
    executor_profile_id: str | None,
    actor_id: str,
    attempt_id: str | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist one feedback fact keyed by source event and producer identity.

    The producer is deliberately independent from the executor.  A reviewer
    using an AI executor is still attributed to the reviewer seat, so later
    experience approval can enforce independent review correctly.
    """
    subject_type = str(producer.get("subject_type") or "")
    subject_id = str(producer.get("subject_id") or "")
    if subject_type not in {"human_user", "ai_employee", "service"} or not subject_id:
        raise api_error(422, "RD_FEEDBACK_ATTRIBUTION_INVALID", "Feedback producer is invalid")
    role_code = producer.get("role_code")
    seat_id = producer.get("seat_id")
    if bool(role_code) != bool(seat_id):
        raise api_error(
            422,
            "RD_FEEDBACK_ATTRIBUTION_INVALID",
            "Producer role and seat must be recorded together",
        )
    run = _records(store, "rd_collaboration_runs").get(collaboration_run_id)
    fingerprint = _hash(
        {
            "source_event_id": source_event_id,
            "outcome": outcome,
            "producer_subject_type": subject_type,
            "producer_subject_id": subject_id,
            "producer_role_code": role_code,
            "producer_seat_id": seat_id,
        }
    )
    record = {
        "id": _new_id(store, "role_feedback"),
        "brain_app_id": (run or {}).get("brain_app_id", "rd_brain"),
        "product_id": (run or {}).get("product_id"),
        "collaboration_run_id": collaboration_run_id,
        "feedback_kind": outcome,
        "source_event_id": source_event_id,
        "feedback_fingerprint": fingerprint,
        "role_code": role_code or "system",
        "seat_id": seat_id,
        "human_user_id": subject_id if subject_type == "human_user" else None,
        "ai_employee_id": subject_id if subject_type == "ai_employee" else None,
        "executor_profile_id": executor_profile_id,
        "work_item_id": work_item_id,
        "attempt_id": attempt_id,
        "strategy_snapshot_id": (run or {}).get("strategy_snapshot_id"),
        "evidence_refs": deepcopy(evidence_refs or []),
        "producer_subject_type": subject_type,
        "producer_subject_id": subject_id,
        "producer_role_code": role_code,
        "producer_seat_id": seat_id,
        "recorded_by": actor_id,
    }
    repository = getattr(store, "repository", None)
    save = getattr(repository, "save_role_feedback_once", None)
    if callable(save):
        if not record["product_id"] or not record["strategy_snapshot_id"]:
            raise api_error(409, "RD_FEEDBACK_ATTRIBUTION_INVALID", "Run provenance is unavailable")
        return save(record)
    existing = next(
        (
            feedback
            for feedback in _records(store, "role_feedback_records").values()
            if feedback.get("collaboration_run_id") == collaboration_run_id
            and feedback.get("feedback_fingerprint") == fingerprint
        ),
        None,
    )
    if existing is not None:
        return deepcopy(existing)
    _records(store, "role_feedback_records")[record["id"]] = record
    return deepcopy(record)
