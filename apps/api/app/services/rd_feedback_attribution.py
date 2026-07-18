"""Immutable role-feedback attribution for later experience review and reuse."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from threading import Lock
from typing import Any

from app.api.deps import api_error
from app.services.rd_role_experiences import generate_role_experience_candidate_from_feedback

_MEMORY_FEEDBACK_LOCK = Lock()


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
    producer: dict[str, Any],
    executor_profile_id: str | None,
    actor_id: str,
    outcome: str | None = None,
    feedback_kind: str | None = None,
    attempt_id: str | None = None,
    attributed: dict[str, Any] | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist one immutable feedback fact from its source event.

    Attribution is deliberately separate from production: a reviewer can
    produce feedback *about* a developer, while an executor is yet another
    frozen identity.  The fingerprint includes all immutable attribution facts
    so an exact source-event replay is safe but a distinct kind/subject is not
    accidentally collapsed.
    """
    kind = str(feedback_kind or outcome or "").strip()
    if not kind:
        raise api_error(422, "RD_FEEDBACK_ATTRIBUTION_INVALID", "Feedback kind is required")
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
    attributed = dict(attributed or producer)
    attributed_type = str(attributed.get("subject_type") or "")
    attributed_id = str(attributed.get("subject_id") or "")
    attributed_role = attributed.get("role_code")
    attributed_seat = attributed.get("seat_id")
    if attributed_type not in {"human_user", "ai_employee"} or not attributed_id:
        raise api_error(
            422,
            "RD_FEEDBACK_ATTRIBUTION_INVALID",
            "Feedback attribution must identify a human or AI employee",
        )
    if bool(attributed_role) != bool(attributed_seat):
        raise api_error(
            422,
            "RD_FEEDBACK_ATTRIBUTION_INVALID",
            "Attributed role and seat must be recorded together",
        )

    def validate_seat(
        *,
        expected_subject_id: str,
        expected_subject_type: str,
        role: str | None,
        seat: str | None,
        label: str,
    ) -> None:
        if not seat:
            return
        candidate = _records(store, "rd_run_seats").get(str(seat))
        # Memory fixtures without a materialized seat retain compatibility;
        # durable storage has the FK, and present seats must match exactly.
        if candidate is None:
            return
        if (
            candidate.get("collaboration_run_id") != collaboration_run_id
            or candidate.get("subject_type") != expected_subject_type
            or candidate.get("role_code") != role
            or (
                candidate.get("human_user_id")
                if expected_subject_type == "human_user"
                else candidate.get("ai_employee_id")
            )
            != expected_subject_id
        ):
            raise api_error(
                422,
                "RD_FEEDBACK_ATTRIBUTION_INVALID",
                f"{label} seat does not match frozen run attribution",
            )

    validate_seat(
        expected_subject_id=subject_id,
        expected_subject_type=subject_type,
        role=role_code,
        seat=seat_id,
        label="Producer",
    )
    validate_seat(
        expected_subject_id=attributed_id,
        expected_subject_type=attributed_type,
        role=attributed_role,
        seat=attributed_seat,
        label="Attributed",
    )
    run_generation = int((run or {}).get("run_generation") or 1)
    strategy_snapshot_id = (run or {}).get("strategy_snapshot_id")
    fingerprint = _hash(
        {
            "attempt_id": attempt_id,
            "attributed_role_code": attributed_role,
            "attributed_seat_id": attributed_seat,
            "attributed_subject_id": attributed_id,
            "attributed_subject_type": attributed_type,
            "feedback_kind": kind,
            "run_generation": run_generation,
            "source_event_id": source_event_id,
            "strategy_snapshot_id": strategy_snapshot_id,
            "work_item_id": work_item_id,
        }
    )
    record = {
        "id": _new_id(store, "role_feedback"),
        "brain_app_id": (run or {}).get("brain_app_id", "rd_brain"),
        "product_id": (run or {}).get("product_id"),
        "collaboration_run_id": collaboration_run_id,
        "feedback_kind": kind,
        "source_event_id": source_event_id,
        "feedback_fingerprint": fingerprint,
        "role_code": attributed_role or "system",
        "seat_id": attributed_seat,
        "human_user_id": attributed_id if attributed_type == "human_user" else None,
        "ai_employee_id": attributed_id if attributed_type == "ai_employee" else None,
        "executor_profile_id": executor_profile_id,
        "work_item_id": work_item_id,
        "attempt_id": attempt_id,
        "strategy_snapshot_id": strategy_snapshot_id,
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
        persisted = save(record)
        generate_role_experience_candidate_from_feedback(store, feedback=persisted)
        return persisted
    # A database unique key protects production.  The test-only memory store
    # needs the equivalent critical section so concurrent replays follow the
    # same one-row contract rather than a read-before-write race.
    with _MEMORY_FEEDBACK_LOCK:
        existing = next(
            (
                feedback
                for feedback in _records(store, "role_feedback_records").values()
                if feedback.get("collaboration_run_id") == collaboration_run_id
                and feedback.get("feedback_fingerprint") == fingerprint
            ),
            None,
        )
        persisted = deepcopy(existing) if existing is not None else deepcopy(record)
        if existing is None:
            _records(store, "role_feedback_records")[record["id"]] = deepcopy(record)
    generate_role_experience_candidate_from_feedback(store, feedback=persisted)
    return persisted
