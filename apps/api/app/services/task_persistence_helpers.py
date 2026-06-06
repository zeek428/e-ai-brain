from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def save_task_state_records(
    current_store: Any,
    *,
    task: dict[str, Any],
    audit_events: list[dict[str, Any]],
    reviews: list[dict[str, Any]] | None = None,
    graph_run: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
    model_log: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_task_state_records", None)
    if callable(save_records):
        save_records(
            task=task,
            audit_events=audit_events,
            reviews=reviews,
            graph_run=graph_run,
            checkpoint=checkpoint,
            model_log=model_log,
        )


def save_task_start_records(
    current_store: Any,
    *,
    task: dict[str, Any],
    review: dict[str, Any],
    graph_run: dict[str, Any],
    checkpoint: dict[str, Any],
    audit_events: list[dict[str, Any]],
    model_log: dict[str, Any] | None = None,
    code_review_report: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_task_start_records", None)
    if callable(save_records):
        save_records(
            task=task,
            review=review,
            graph_run=graph_run,
            checkpoint=checkpoint,
            audit_events=audit_events,
            model_log=model_log,
            code_review_report=code_review_report,
        )


def save_requirement_and_ai_task_records(
    current_store: Any,
    *,
    requirement: dict[str, Any],
    task: dict[str, Any],
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_requirement_and_ai_task_records", None)
    if callable(save_records):
        save_records(requirement=requirement, task=task, audit_event=audit_event)


def save_review_decision_records(
    current_store: Any,
    *,
    task: dict[str, Any],
    review: dict[str, Any],
    graph_run: dict[str, Any] | None,
    checkpoint: dict[str, Any] | None,
    audit_events: list[dict[str, Any]],
    requirement: dict[str, Any] | None = None,
    knowledge_deposits: list[dict[str, Any]] | None = None,
    bugs: list[dict[str, Any]] | None = None,
    code_review_report: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_review_decision_records", None)
    if callable(save_records):
        save_records(
            task=task,
            review=review,
            graph_run=graph_run,
            checkpoint=checkpoint,
            audit_events=audit_events,
            requirement=requirement,
            knowledge_deposits=knowledge_deposits,
            bugs=bugs,
            code_review_report=code_review_report,
        )


def record_audit_event(
    current_store: Any,
    *,
    event_type: str,
    actor_id: str,
    ai_task_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not uses_repository_context(current_store):
        return current_store.audit(
            event_type=event_type,
            actor_id=actor_id,
            ai_task_id=ai_task_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
        )
    return {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": ai_task_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": len(current_store.audit_events) + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }


def save_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    append_event = getattr(repository, "append_audit_event", None)
    if callable(append_event):
        append_event(audit_event)
        return
    save_events = getattr(repository, "save_audit_events", None)
    if callable(save_events):
        save_events({"audit_events": [audit_event]})
