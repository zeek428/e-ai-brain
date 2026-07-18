"""Collaboration projections around the existing Runner and quality-gate loop.

The Runner remains responsible for physical execution.  This module owns the
small, deterministic projection back into the collaboration aggregate so a
late or duplicate Runner result cannot revive a cancelled or reworked lease.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.operational_records import read_memory_dict
from app.services.task_persistence_helpers import (
    record_audit_event,
    save_audit_event,
    save_task_state_records,
)


def _records(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    return read_memory_dict(current_store, collection_name)


def _record(
    current_store: Any,
    collection_name: str,
    record_id: str,
) -> dict[str, Any] | None:
    """Read collaboration facts from PostgreSQL before request-local scratch.

    `PostgresRuntimeStore` deliberately inherits empty MemoryStore collections.
    Reading those first would make a real Runner completion look as if its
    work-item provenance had disappeared, so v2 projections must use the
    repository as their source of truth.
    """
    repository = getattr(current_store, "repository", None)
    method_name = {
        "rd_collaboration_runs": "get_rd_collaboration_run",
        "rd_work_items": "get_rd_work_item",
        "rd_work_item_attempts": "get_rd_work_item_attempt",
        "rd_run_seats": "get_rd_run_seat",
    }.get(collection_name)
    load = getattr(repository, method_name, None) if method_name else None
    persisted = load(record_id) if callable(load) else None
    if isinstance(persisted, dict):
        return dict(persisted)
    candidate = _records(current_store, collection_name).get(record_id)
    return dict(candidate) if isinstance(candidate, dict) else None


def _work_item_attempts(current_store: Any, work_item_id: str) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    load = getattr(repository, "list_rd_work_item_attempts", None)
    persisted = load(work_item_id) if callable(load) else None
    if isinstance(persisted, list):
        return [dict(attempt) for attempt in persisted if isinstance(attempt, dict)]
    return [
        dict(attempt)
        for attempt in _records(current_store, "rd_work_item_attempts").values()
        if attempt.get("work_item_id") == work_item_id
    ]


def _runner_task(
    current_store: Any,
    *,
    task: dict[str, Any],
    runner_task_id: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_tasks = getattr(repository, "list_ai_executor_tasks", None)
    if callable(list_tasks):
        persisted = list_tasks(ai_task_id=task["id"])
        candidate = next(
            (
                item
                for item in persisted
                if isinstance(item, dict) and item.get("id") == runner_task_id
            ),
            None,
        )
        if isinstance(candidate, dict):
            return dict(candidate)
    candidate = _records(current_store, "ai_executor_tasks").get(runner_task_id)
    return dict(candidate) if isinstance(candidate, dict) else None


def is_rd_collaboration_task(task: dict[str, Any] | None) -> bool:
    return bool(
        isinstance(task, dict) and task.get("collaboration_run_id") and task.get("work_item_id")
    )


def _task(current_store: Any, ai_task_id: str) -> dict[str, Any] | None:
    task = _records(current_store, "ai_tasks").get(ai_task_id)
    if isinstance(task, dict):
        return task
    repository = getattr(current_store, "repository", None)
    load = getattr(repository, "load_ai_tasks", None)
    if callable(load):
        payload = load()
        records = payload.get("ai_tasks", {}) if isinstance(payload, dict) else {}
        candidate = records.get(ai_task_id) if isinstance(records, dict) else None
        return dict(candidate) if isinstance(candidate, dict) else None
    return None


def _attempt_for_runner(
    current_store: Any,
    *,
    task: dict[str, Any],
    runner_task_id: str,
) -> dict[str, Any] | None:
    runner_task = _runner_task(current_store, task=task, runner_task_id=runner_task_id) or {}
    payload = runner_task.get("input_payload") if isinstance(runner_task, dict) else {}
    attempt_id = str((payload or {}).get("rd_work_item_attempt_id") or "").strip()
    if not attempt_id:
        collaboration = task.get("input_json") if isinstance(task.get("input_json"), dict) else {}
        frozen = collaboration.get("rd_collaboration") if isinstance(collaboration, dict) else {}
        attempt_id = str((frozen or {}).get("attempt_id") or "").strip()
    return _record(current_store, "rd_work_item_attempts", attempt_id)


def _save_event(
    current_store: Any,
    *,
    event_key: str,
    event_type: str,
    task: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    events = _records(current_store, "rd_collaboration_events")
    existing = next(
        (
            event
            for event in events.values()
            if event.get("collaboration_run_id") == task.get("collaboration_run_id")
            and event.get("event_key") == event_key
        ),
        None,
    )
    if existing is not None:
        return existing
    event = {
        "id": current_store.new_id("rd_collaboration_event"),
        "collaboration_run_id": task["collaboration_run_id"],
        "event_type": event_type,
        "event_key": event_key,
        "subject_type": "rd_work_item",
        "subject_id": task["work_item_id"],
        "payload_json": deepcopy(payload),
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    events[event["id"]] = event
    repository = getattr(current_store, "repository", None)
    save = getattr(repository, "save_rd_collaboration_event_record", None)
    if callable(save):
        persisted = save(event)
        if isinstance(persisted, dict):
            events[event["id"]] = dict(persisted)
            return dict(persisted)
    return event


def _existing_event(
    current_store: Any,
    *,
    collaboration_run_id: str,
    event_key: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_events = getattr(repository, "list_rd_collaboration_events", None)
    if callable(list_events):
        persisted = list_events(collaboration_run_id)
        candidate = next(
            (
                event
                for event in persisted
                if isinstance(event, dict) and event.get("event_key") == event_key
            ),
            None,
        )
        if isinstance(candidate, dict):
            return dict(candidate)
    return next(
        (
            dict(event)
            for event in _records(current_store, "rd_collaboration_events").values()
            if event.get("collaboration_run_id") == collaboration_run_id
            and event.get("event_key") == event_key
        ),
        None,
    )


def fence_stale_coding_runner_completion(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    runner_task: dict[str, Any],
) -> bool:
    """Return ``True`` only after a v2 completion has been durably fenced.

    This is deliberately the first v2 coding-completion operation.  It checks
    the immutable attempt provenance before creating a quality gate, Review or
    task-state projection, so a completion racing cancellation/suspension can
    never revive the collaboration aggregate.
    """
    if not is_rd_collaboration_task(ai_task):
        return False
    task_kind = str(runner_task.get("task_kind") or "coding")
    if task_kind != "coding":
        return False
    runner_status = str(runner_task.get("status") or "")
    if runner_status in {"queued", "claimed", "running"}:
        return False

    input_payload = (
        runner_task.get("input_payload")
        if isinstance(runner_task.get("input_payload"), dict)
        else {}
    )
    frozen = (
        (ai_task.get("input_json") or {}).get("rd_collaboration")
        if isinstance(ai_task.get("input_json"), dict)
        else {}
    )
    expected_attempt_id = str(input_payload.get("rd_work_item_attempt_id") or "")
    current_attempt_id = str((frozen or {}).get("attempt_id") or "")
    attempt_id = expected_attempt_id or current_attempt_id or "missing"
    collaboration_run_id = str(ai_task.get("collaboration_run_id") or "")
    work_item_id = str(ai_task.get("work_item_id") or "")
    repository = getattr(current_store, "repository", None)
    persist_fence = getattr(repository, "fence_work_item_runner_result", None)
    if callable(persist_fence):
        event_key = (
            f"work-item-runner-fenced:{work_item_id}:{attempt_id}:{runner_task.get('id')}"
        )
        event = {
            "id": current_store.new_id("rd_collaboration_event"),
            "collaboration_run_id": collaboration_run_id,
            "event_type": "work_item.runner_result_fenced",
            "event_key": event_key,
            "subject_type": "rd_work_item",
            "subject_id": work_item_id,
            "payload_json": {},
            "occurred_at": datetime.now(UTC).isoformat(),
        }
        audit_event = record_audit_event(
            current_store,
            event_type="rd_work_item.runner_result_fenced",
            actor_id="system",
            ai_task_id=ai_task["id"],
            subject_type="rd_work_item",
            subject_id=work_item_id,
            payload={},
        )
        persisted = persist_fence(
            collaboration_run_id=collaboration_run_id,
            work_item_id=work_item_id,
            attempt_id=attempt_id,
            ai_task_id=ai_task["id"],
            runner_task_id=str(runner_task.get("id") or ""),
            runner_status=runner_status,
            event=event,
            audit_event=audit_event,
        )
        return bool(persisted.get("fenced"))

    item = _record(current_store, "rd_work_items", str(ai_task.get("work_item_id") or ""))
    attempt = _attempt_for_runner(
        current_store,
        task=ai_task,
        runner_task_id=str(runner_task.get("id") or ""),
    )
    run = _record(
        current_store,
        "rd_collaboration_runs",
        str(ai_task.get("collaboration_run_id") or ""),
    )
    reasons: list[str] = []
    if item is None or attempt is None or run is None:
        reasons.append("missing_frozen_provenance")
    if attempt is not None and attempt.get("id") not in {expected_attempt_id, current_attempt_id}:
        reasons.append("attempt_provenance_mismatch")
    if attempt is not None and attempt.get("status") != "running":
        reasons.append("attempt_not_currently_running")
    if item is not None and item.get("status") != "running":
        reasons.append("work_item_not_currently_running")
    if run is not None and run.get("status") not in {"running", "integrating", "verifying"}:
        reasons.append("collaboration_run_not_dispatchable")
    if not reasons:
        return False

    attempt_id = str((attempt or {}).get("id") or expected_attempt_id or "missing")
    event_key = f"work-item-runner-fenced:{work_item_id}:{attempt_id}:{runner_task.get('id')}"
    existing = _existing_event(
        current_store,
        collaboration_run_id=collaboration_run_id,
        event_key=event_key,
    )
    if existing is not None:
        return True
    event = _save_event(
        current_store,
        event_key=event_key,
        event_type="work_item.runner_result_fenced",
        task=ai_task,
        payload={
            "attempt_id": attempt_id,
            "reason": reasons[0],
            "reasons": reasons,
            "runner_task_id": runner_task.get("id"),
            "runner_status": runner_status,
        },
    )
    audit_event = record_audit_event(
        current_store,
        event_type="rd_work_item.runner_result_fenced",
        actor_id="system",
        ai_task_id=ai_task["id"],
        subject_type="rd_work_item",
        subject_id=work_item_id,
        payload={"event_id": event["id"], "attempt_id": attempt_id, "reasons": reasons},
    )
    save_audit_event(current_store, audit_event)
    return True


def project_work_item_quality_gate_result(
    current_store: Any,
    *,
    ai_task_id: str,
    quality_gate_run: dict[str, Any],
    runner_task_id: str,
) -> dict[str, Any] | None:
    """Project one terminal quality-gate fact to its frozen work-item attempt.

    A failed gate deliberately keeps the old attempt as evidence and exposes
    `rework_required`; dispatching again creates a distinct attempt/Runner
    lease.  Terminal/cancelled/suspended attempts are late-result fences: the
    incoming Runner report is audit-only and cannot change collaboration state.
    """
    task = _task(current_store, ai_task_id)
    if not is_rd_collaboration_task(task):
        return None
    assert task is not None
    item = _record(current_store, "rd_work_items", str(task["work_item_id"]))
    attempt = _attempt_for_runner(current_store, task=task, runner_task_id=runner_task_id)
    if item is None or attempt is None or attempt.get("work_item_id") != item.get("id"):
        raise api_error(
            409,
            "RD_WORK_ITEM_NOT_READY",
            "Runner result is missing work-item attempt provenance",
        )

    gate_id = str(quality_gate_run.get("id") or "").strip()
    if not gate_id:
        raise api_error(409, "RD_WORK_ITEM_NOT_READY", "Quality gate has no immutable identity")
    gate_status = str(quality_gate_run.get("status") or "failed")
    event_key = f"work-item-quality-gate:{item['id']}:{attempt['id']}:{gate_id}"
    terminal_attempt_states = {
        "cancelled",
        "expired",
        "failed",
        "suspended_for_decision",
        "waiting_human",
    }
    if attempt.get("status") in terminal_attempt_states or item.get("status") in {
        "cancelled",
        "failed",
        "waiting_human",
    }:
        event = _save_event(
            current_store,
            event_key=event_key,
            event_type="work_item.runner_result_fenced",
            task=task,
            payload={
                "attempt_id": attempt["id"],
                "quality_gate_run_id": gate_id,
                "quality_gate_status": gate_status,
                "reason": "late_or_revoked_attempt",
            },
        )
        audit_event = record_audit_event(
            current_store,
            event_type="rd_work_item.runner_result_fenced",
            actor_id="system",
            ai_task_id=task["id"],
            subject_type="rd_work_item",
            subject_id=item["id"],
            payload={"event_id": event["id"], "attempt_id": attempt["id"], "gate_id": gate_id},
        )
        save_audit_event(current_store, audit_event)
        return {"attempt": deepcopy(attempt), "event": event, "late_result": True}

    if gate_status == "passed":
        next_status = "reviewing"
        attempt["status"] = "completed"
        attempt["completed_at"] = attempt.get("completed_at") or datetime.now(UTC).isoformat()
        event_type = "work_item.quality_gate_passed"
    else:
        next_status = "rework_required"
        attempt["status"] = "failed"
        attempt["failure_json"] = {
            "blocked_reasons": deepcopy(quality_gate_run.get("blocked_reasons") or []),
            "quality_gate_run_id": gate_id,
        }
        task.update(
            {
                "current_step": "rework_required",
                "error_code": "RD_QUALITY_GATE_FAILED",
                "error_message": str(quality_gate_run.get("summary") or "Quality gate failed"),
                "status": "failed",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        event_type = "work_item.quality_gate_failed"
    attempt["result_json"] = {
        **dict(attempt.get("result_json") or {}),
        "quality_gate": deepcopy(quality_gate_run),
    }
    item.update(
        {
            "status": next_status,
            "lease_owner": None,
            "lease_expires_at": None,
            "version": int(item.get("version") or 1) + 1,
        }
    )
    event_payload = {
        "attempt_id": attempt["id"],
        "quality_gate_run_id": gate_id,
        "quality_gate_status": gate_status,
    }
    event_record = {
        "id": current_store.new_id("rd_collaboration_event"),
        "collaboration_run_id": task["collaboration_run_id"],
        "event_type": event_type,
        "event_key": event_key,
        "subject_type": "rd_work_item",
        "subject_id": item["id"],
        "payload_json": deepcopy(event_payload),
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    audit_event = record_audit_event(
        current_store,
        event_type=f"rd_work_item.{event_type.rsplit('.', 1)[-1]}",
        actor_id="system",
        ai_task_id=task["id"],
        subject_type="rd_work_item",
        subject_id=item["id"],
        payload={"attempt_id": attempt["id"], "event_id": event_record["id"], "gate_id": gate_id},
    )
    repository = getattr(current_store, "repository", None)
    save_bundle = getattr(repository, "save_work_item_attempt_bundle", None)
    if callable(save_bundle):
        persisted = save_bundle(
            work_item_id=item["id"],
            expected_statuses=["running"],
            next_status=next_status,
            attempt=attempt,
            expected_version=int(item["version"]) - 1,
            event=event_record,
            task=task,
            audit_events=[audit_event],
        )
        item = dict(persisted["work_item"])
        attempt = dict(persisted["attempt"])
        event = dict(persisted["event"] or event)
        _records(current_store, "rd_work_items")[item["id"]] = item
        _records(current_store, "rd_work_item_attempts")[attempt["id"]] = attempt
        _records(current_store, "rd_collaboration_events")[event["id"]] = event
    else:
        event = _save_event(
            current_store,
            event_key=event_key,
            event_type=event_type,
            task=task,
            payload=event_payload,
        )
        _records(current_store, "rd_work_items")[item["id"]] = item
        _records(current_store, "rd_work_item_attempts")[attempt["id"]] = attempt
        audit_event["payload"]["event_id"] = event["id"]
    if not callable(save_bundle):
        if next_status == "rework_required":
            save_task_state_records(current_store, task=task, audit_events=[audit_event])
        else:
            save_audit_event(current_store, audit_event)
    elif next_status != "rework_required":
        # The transaction already persisted the audit with the work-item
        # transition; retaining this branch makes the no-op intent explicit.
        pass
    return {
        "attempt": deepcopy(attempt),
        "event": event,
        "next_state": next_status,
        "work_item": deepcopy(item),
    }


def _promote_ready_successors(current_store: Any, *, completed_work_item_id: str) -> None:
    dependencies = _records(current_store, "rd_work_item_dependencies")
    items = _records(current_store, "rd_work_items")
    for dependency in dependencies.values():
        if (
            dependency.get("predecessor_work_item_id") == completed_work_item_id
            and dependency.get("status", "pending") == "pending"
        ):
            dependency["status"] = "satisfied"
            dependency["satisfied_at"] = datetime.now(UTC).isoformat()
    for item in items.values():
        if item.get("status") != "blocked":
            continue
        incoming = [
            dependency
            for dependency in dependencies.values()
            if dependency.get("successor_work_item_id") == item.get("id")
        ]
        if incoming and all(edge.get("status") == "satisfied" for edge in incoming):
            item["status"] = "ready"
            item["version"] = int(item.get("version") or 1) + 1


def approve_work_item_after_task_review(
    current_store: Any,
    *,
    ai_task_id: str,
    review_id: str,
    actor_id: str,
) -> dict[str, Any] | None:
    """Finish the collaboration item after its independent AI-task Review passes."""
    task = _task(current_store, ai_task_id)
    if not is_rd_collaboration_task(task):
        return None
    assert task is not None
    item = _record(current_store, "rd_work_items", str(task["work_item_id"]))
    if item is None:
        raise api_error(409, "RD_WORK_ITEM_NOT_READY", "Linked work item is unavailable")
    reviewer = _record(current_store, "rd_run_seats", str(item.get("reviewer_seat_id") or ""))
    owner = _record(current_store, "rd_run_seats", str(item.get("owner_seat_id") or ""))
    reviewer_subject_id = (
        reviewer.get("human_user_id")
        if isinstance(reviewer, dict) and reviewer.get("subject_type") == "human_user"
        else reviewer.get("ai_employee_id")
        if isinstance(reviewer, dict)
        else None
    )
    if (
        reviewer is None
        or owner is None
        or reviewer.get("id") == owner.get("id")
        or reviewer.get("status") != "active"
        or str(reviewer_subject_id or "") != actor_id
    ):
        raise api_error(403, "FORBIDDEN", "Review actor must match the frozen independent reviewer")
    attempts = _work_item_attempts(current_store, item["id"])
    attempt = max(attempts, key=lambda entry: int(entry.get("attempt_no") or 0), default=None)
    if attempt is None or attempt.get("status") != "completed" or item.get("status") != "reviewing":
        raise api_error(
            409,
            "RD_WORK_ITEM_NOT_READY",
            "Work item is not awaiting its independent review",
        )
    event_key = f"work-item-review-approved:{item['id']}:{attempt['id']}:{review_id}"
    existing_event = _existing_event(
        current_store,
        collaboration_run_id=task["collaboration_run_id"],
        event_key=event_key,
    )
    if existing_event is not None:
        return {
            "work_item": deepcopy(item),
            "attempt": deepcopy(attempt),
            "event": deepcopy(existing_event),
            "idempotent_replay": True,
        }
    repository = getattr(current_store, "repository", None)
    save_bundle = getattr(repository, "save_work_item_attempt_bundle", None)
    event_payload = {
        "attempt_id": attempt["id"],
        "review_id": review_id,
        "reviewer_seat_id": reviewer["id"],
    }
    event_record = {
        "id": current_store.new_id("rd_collaboration_event"),
        "collaboration_run_id": task["collaboration_run_id"],
        "event_type": "work_item.review_approved",
        "event_key": event_key,
        "subject_type": "rd_work_item",
        "subject_id": item["id"],
        "payload_json": deepcopy(event_payload),
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    audit_event = record_audit_event(
        current_store,
        event_type="rd_work_item.review_approved",
        actor_id=actor_id,
        ai_task_id=task["id"],
        subject_type="rd_work_item",
        subject_id=item["id"],
        payload={
            "attempt_id": attempt["id"],
            "event_id": event_record["id"],
            "review_id": review_id,
        },
    )
    if callable(save_bundle):
        persisted = save_bundle(
            work_item_id=item["id"],
            expected_statuses=["reviewing"],
            next_status="completed",
            attempt=attempt,
            expected_version=int(item["version"]),
            event=event_record,
            task=task,
            audit_events=[audit_event],
        )
        item = dict(persisted["work_item"])
        attempt = dict(persisted["attempt"])
        event = dict(persisted["event"] or event_record)
        _records(current_store, "rd_work_items")[item["id"]] = item
        _records(current_store, "rd_work_item_attempts")[attempt["id"]] = attempt
        _records(current_store, "rd_collaboration_events")[event["id"]] = event
    else:
        item.update(
            {
                "status": "completed",
                "lease_owner": None,
                "lease_expires_at": None,
                "version": int(item.get("version") or 1) + 1,
            }
        )
        _promote_ready_successors(current_store, completed_work_item_id=item["id"])
        event = _save_event(
            current_store,
            event_key=event_key,
            event_type="work_item.review_approved",
            task=task,
            payload=event_payload,
        )
        _records(current_store, "rd_work_items")[item["id"]] = item
        _records(current_store, "rd_work_item_attempts")[attempt["id"]] = attempt
        audit_event["payload"]["event_id"] = event["id"]
        save_audit_event(current_store, audit_event)
    return {
        "work_item": deepcopy(item),
        "attempt": deepcopy(attempt),
        "event": event,
        "idempotent_replay": False,
    }
