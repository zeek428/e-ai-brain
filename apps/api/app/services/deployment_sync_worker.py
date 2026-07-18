from __future__ import annotations

import logging
import os
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.jenkins_deployments import sync_jenkins_deployment

logger = logging.getLogger(__name__)


def _release_failed_lease(
    current_store: Any,
    run: dict[str, Any],
    *,
    error: Exception,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_deployment_run_record", None)
    if not callable(save_record):
        return
    attempts = int(run.get("sync_attempts") or 0) + 1
    retry_seconds = min(300, max(5, 2 ** min(attempts, 8)))
    failed_run = {
        **run,
        "failure_reason": f"Jenkins synchronization failed: {type(error).__name__}",
        "next_sync_at": (datetime.now(UTC) + timedelta(seconds=retry_seconds)).isoformat(),
        "sync_attempts": attempts,
        "sync_lease_owner": None,
        "sync_lease_until": None,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    save_record(failed_run)


def sync_due_jenkins_deployments(
    current_store: Any,
    *,
    lease_seconds: int = 30,
    limit: int = 10,
    worker_id: str,
) -> int:
    repository = getattr(current_store, "repository", None)
    claim_due = getattr(repository, "claim_due_deployment_runs", None)
    if not callable(claim_due):
        return 0
    runs = claim_due(
        lease_seconds=lease_seconds,
        limit=limit,
        worker_id=worker_id,
    )
    processed = 0
    for run in runs:
        try:
            sync_jenkins_deployment(
                current_store=current_store,
                deployment_request_id=str(run["deployment_request_id"]),
                deployment_run_id=str(run["id"]),
                actor_id=worker_id,
            )
            processed += 1
        except Exception as exc:  # noqa: BLE001 - worker must release leases and continue.
            logger.exception("Jenkins deployment synchronization failed for %s", run.get("id"))
            _release_failed_lease(current_store, run, error=exc)
    return processed


def _worker_loop(application: Any, stop_event: threading.Event, worker_id: str) -> None:
    while not stop_event.is_set():
        try:
            from app.services.operational_deployments import (
                process_execution_outbox_events,
            )
            from app.services.rd_collaboration_graph_event_projection import (
                process_rd_collaboration_graph_events,
            )

            process_execution_outbox_events(
                application.state.store,
                worker_id=worker_id,
            )
            process_rd_collaboration_graph_events(application.state.store)
            sync_due_jenkins_deployments(
                application.state.store,
                worker_id=worker_id,
            )
        except Exception:  # noqa: BLE001 - keep background synchronization alive.
            logger.exception("Jenkins deployment synchronization worker iteration failed")
        stop_event.wait(5)


def start_deployment_sync_worker(application: Any) -> None:
    repository = getattr(application.state.store, "repository", None)
    if not any(
        callable(getattr(repository, method_name, None))
        for method_name in (
            "claim_due_deployment_runs",
            "claim_execution_outbox_events",
        )
    ):
        return
    current = getattr(application.state, "deployment_sync_worker", None)
    if isinstance(current, dict) and current.get("thread") is not None:
        return
    stop_event = threading.Event()
    worker_id = f"deployment-sync-{os.getpid()}"
    thread = threading.Thread(
        target=_worker_loop,
        args=(application, stop_event, worker_id),
        daemon=True,
        name="deployment-sync-worker",
    )
    application.state.deployment_sync_worker = {
        "stop_event": stop_event,
        "thread": thread,
        "worker_id": worker_id,
    }
    thread.start()


def stop_deployment_sync_worker(application: Any) -> None:
    current = getattr(application.state, "deployment_sync_worker", None)
    if not isinstance(current, dict):
        return
    stop_event = current.get("stop_event")
    thread = current.get("thread")
    if isinstance(stop_event, threading.Event):
        stop_event.set()
    if isinstance(thread, threading.Thread):
        thread.join(timeout=5)
    application.state.deployment_sync_worker = None
