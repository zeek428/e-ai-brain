"""Advance the collaboration graph from committed scheduler events.

The work-item scheduler owns the transactional state transition and writes its
``rd_collaboration_events`` fact first.  This projector is deliberately the
next, retryable step: it feeds that immutable fact to ``RdCollaborationGraphRuntime``
without trying to repeat the scheduler command.  The runtime then writes its
own idempotent audit/feedback bundle before it advances the LangGraph
checkpoint.
"""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

from app.core.config import get_settings
from app.core.graph_checkpointer import build_checkpointer
from app.services.rd_collaboration_graph_runtime import RdCollaborationGraphRuntime

_PROJECTION_EVENT_PREFIX = "event-projection:"
_RUNTIME_EVENT_KEY_PREFIX = "graph-event:"


def _event_value(event: dict[str, Any], field: str, fallback: Any = None) -> Any:
    value = event.get(field)
    return fallback if value is None else value


def _is_runtime_event(event: dict[str, Any]) -> bool:
    return str(event.get("event_key") or "").startswith(_RUNTIME_EVENT_KEY_PREFIX)


def _projected_event_id(event: dict[str, Any]) -> str:
    source_event_id = str(event.get("id") or "").strip()
    if not source_event_id:
        raise ValueError("Collaboration event id is required for graph projection")
    return f"{_PROJECTION_EVENT_PREFIX}{source_event_id}"


def _runtime_settings(current_store: Any) -> Any:
    """Use the store's PostgreSQL URL even when a repository test runs in APP_ENV=test."""
    repository = getattr(current_store, "repository", None)
    database_url = str(getattr(repository, "database_url", "") or "").strip()
    if database_url:
        return SimpleNamespace(
            is_test_env=False,
            persistence_mode="postgres",
            database_url=database_url,
        )
    return get_settings()


def _build_runtime(current_store: Any) -> RdCollaborationGraphRuntime:
    return RdCollaborationGraphRuntime(
        current_store,
        checkpointer=build_checkpointer(_runtime_settings(current_store)),
    )


def _close_owned_runtime(runtime: RdCollaborationGraphRuntime) -> None:
    connection = getattr(runtime.checkpointer, "conn", None)
    close = getattr(connection, "close", None)
    if callable(close):
        close()


def _source_events(current_store: Any) -> list[dict[str, Any]]:
    """Read canonical scheduler facts, never the runtime events they generate."""
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_rd_collaboration_runs", None)
    list_events = getattr(repository, "list_rd_collaboration_events", None)
    if callable(list_runs) and callable(list_events):
        events = [dict(event) for run in list_runs() for event in list_events(str(run["id"]))]
    else:
        records = getattr(current_store, "rd_collaboration_events", {})
        events = [dict(event) for event in records.values()] if isinstance(records, dict) else []
    return sorted(
        (event for event in events if not _is_runtime_event(event)),
        key=lambda event: (
            str(event.get("occurred_at") or event.get("created_at") or ""),
            str(event.get("id") or ""),
        ),
    )


def project_committed_rd_collaboration_event(
    current_store: Any,
    *,
    event: dict[str, Any],
    runtime: RdCollaborationGraphRuntime | None = None,
) -> dict[str, Any]:
    """Project one already-committed scheduler event to a graph cursor.

    The projection event id is stable for a source event.  Retrying this method
    after a checkpointer failure therefore reuses the same idempotent command
    bundle and cannot duplicate event, audit, or role-feedback rows.
    """
    if _is_runtime_event(event):
        return {"checkpoint_status": "skipped", "reason": "runtime_event"}
    collaboration_run_id = str(event.get("collaboration_run_id") or "").strip()
    event_type = str(event.get("event_type") or "").strip()
    if not collaboration_run_id or not event_type:
        raise ValueError("Collaboration event provenance is unavailable")
    source_payload = _event_value(event, "payload_json", {})
    if not isinstance(source_payload, dict):
        source_payload = {}
    owns_runtime = runtime is None
    current_runtime = runtime or _build_runtime(current_store)
    try:
        return current_runtime.handle_event(
            collaboration_run_id=collaboration_run_id,
            event_id=_projected_event_id(event),
            event_type=event_type,
            payload={
                "source_event_id": str(event["id"]),
                "source_event_key": str(event.get("event_key") or ""),
                "source_event_type": event_type,
                "source_payload": deepcopy(source_payload),
            },
            subject_type=str(event.get("subject_type") or "rd_collaboration_run"),
            subject_id=str(event.get("subject_id") or collaboration_run_id),
        )
    finally:
        if owns_runtime:
            _close_owned_runtime(current_runtime)


def process_rd_collaboration_graph_events(
    current_store: Any,
    *,
    limit: int = 100,
    runtime: RdCollaborationGraphRuntime | None = None,
) -> int:
    """Consume committed collaboration facts through the production worker path.

    Every source event is safe to revisit.  ``handle_event`` first reuses its
    idempotent domain bundle, then the graph reducer ignores an already-seen
    event id.  Revisiting facts is intentional: it heals a prior checkpoint
    failure without re-running the scheduler's atomic work-item transition.

    The batch limit applies to *uncheckpointed* facts, rather than to the
    first source rows.  Otherwise a run with a long settled history would
    repeatedly examine the same first page and starve every newer pending
    event.  A concurrent worker may still persist one selected event first;
    the runtime's idempotent domain command and graph reducer make that replay
    safe.
    """
    if limit <= 0:
        return 0
    owns_runtime = runtime is None
    current_runtime = runtime or _build_runtime(current_store)
    persisted = 0
    try:
        pending_events: list[dict[str, Any]] = []
        for event in _source_events(current_store):
            collaboration_run_id = str(event.get("collaboration_run_id") or "").strip()
            projected_event_id = _projected_event_id(event)
            if collaboration_run_id and current_runtime.is_event_checkpointed(
                collaboration_run_id=collaboration_run_id,
                event_id=projected_event_id,
            ):
                continue
            pending_events.append(event)
            if len(pending_events) >= limit:
                break
        for event in pending_events:
            result = project_committed_rd_collaboration_event(
                current_store,
                event=event,
                runtime=current_runtime,
            )
            if result.get("checkpoint_status") == "persisted":
                persisted += 1
    finally:
        if owns_runtime:
            _close_owned_runtime(current_runtime)
    return persisted
