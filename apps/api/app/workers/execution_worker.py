from __future__ import annotations

import logging
import os
import signal
import threading
from typing import Any

from app.core.config import Settings, get_settings
from app.core.persistence import PostgresRuntimeStore, PostgresSnapshotRepository
from app.services.deployment_sync_worker import sync_due_jenkins_deployments
from app.services.execution_worker_observability import record_execution_worker_heartbeat
from app.services.external_event_inbox import process_external_event_inbox_events
from app.services.operational_deployments import (
    process_execution_outbox_events,
    reconcile_platform_external_operations,
)
from app.services.rd_collaboration_auto_dispatch import dispatch_ready_ai_work_items
from app.services.rd_collaboration_graph_event_projection import (
    process_rd_collaboration_graph_events,
)
from app.services.rd_collaboration_plan_generation import plan_pending_collaboration_runs

logger = logging.getLogger(__name__)


def run_execution_worker_iteration(
    current_store: Any,
    *,
    worker_id: str,
    rd_collaboration_graph_runtime: Any | None = None,
    collaboration_planner: Any | None = None,
) -> dict[str, int]:
    outbox_count = process_execution_outbox_events(
        current_store,
        worker_id=worker_id,
    )
    external_event_count = process_external_event_inbox_events(
        current_store,
        worker_id=worker_id,
    )
    rd_collaboration_graph_event_count = process_rd_collaboration_graph_events(
        current_store,
        runtime=rd_collaboration_graph_runtime,
    )
    rd_collaboration_planning = plan_pending_collaboration_runs(
        current_store,
        planner=collaboration_planner,
    )
    rd_collaboration_auto_dispatch = dispatch_ready_ai_work_items(current_store)
    jenkins_sync_count = sync_due_jenkins_deployments(
        current_store,
        worker_id=worker_id,
    )
    supports_reconciliation = hasattr(current_store, "repository") or hasattr(
        current_store,
        "external_operations",
    )
    reconciliation_count = (
        len(reconcile_platform_external_operations(current_store, actor_id=worker_id))
        if supports_reconciliation
        else 0
    )
    counts = {
        "external_event_count": external_event_count,
        "jenkins_sync_count": jenkins_sync_count,
        "outbox_count": outbox_count,
        "rd_collaboration_auto_dispatch_count": len(
            rd_collaboration_auto_dispatch["dispatched_work_item_ids"]
        ),
        "rd_collaboration_graph_event_count": rd_collaboration_graph_event_count,
        "rd_collaboration_plan_count": len(rd_collaboration_planning["planned_run_ids"]),
        "reconciliation_count": reconciliation_count,
    }
    classified_dispatch_counts = {
        "rd_collaboration_auto_dispatch_deferred_count": len(
            rd_collaboration_auto_dispatch.get("capacity_deferred_work_item_ids", [])
        ),
        "rd_collaboration_auto_dispatch_escalated_count": len(
            rd_collaboration_auto_dispatch.get("escalated_work_item_ids", [])
        ),
        "rd_collaboration_auto_dispatch_retryable_count": len(
            rd_collaboration_auto_dispatch.get("retryable_work_item_ids", [])
        ),
    }
    if any(
        key in rd_collaboration_auto_dispatch
        for key in (
            "capacity_deferred_work_item_ids",
            "escalated_work_item_ids",
            "retryable_work_item_ids",
        )
    ):
        counts.update(classified_dispatch_counts)
    record_execution_worker_heartbeat(current_store, counts=counts, worker_id=worker_id)
    return counts


def build_execution_worker_store(settings: Settings) -> PostgresRuntimeStore:
    if settings.persistence_mode != "postgres":
        raise RuntimeError("The dedicated execution worker requires PostgreSQL")
    repository = PostgresSnapshotRepository(
        settings.database_url,
        ensure_schema_compatibility=False,
        pool_max_size=settings.database_pool_max_size,
    )
    return PostgresRuntimeStore(repository)


def run_execution_worker_forever(
    *,
    settings: Settings | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    resolved_settings = settings or get_settings()
    current_store = build_execution_worker_store(resolved_settings)
    stop = stop_event or threading.Event()
    worker_id = f"execution-worker-{os.getpid()}"

    def request_stop(*_: object) -> None:
        stop.set()

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)
    logger.info("Execution worker %s started", worker_id)
    while not stop.is_set():
        try:
            counts = run_execution_worker_iteration(
                current_store,
                worker_id=worker_id,
            )
            if any(counts.values()):
                logger.info("Execution worker iteration: %s", counts)
        except Exception:  # noqa: BLE001 - the durable worker must keep polling.
            logger.exception("Execution worker iteration failed")
        stop.wait(resolved_settings.execution_worker_poll_interval_seconds)
