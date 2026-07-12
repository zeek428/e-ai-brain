from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import read_memory_dict, read_memory_records


def record_execution_worker_heartbeat(
    current_store: Any,
    *,
    counts: dict[str, int],
    worker_id: str,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    record = {
        "claimed_count": sum(int(value or 0) for value in counts.values()),
        "counts": dict(counts),
        "id": worker_id,
        "product_id": None,
        "updated_at": now,
        "worker_id": worker_id,
    }
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_trusted_delivery_record", None)
    if callable(save_record):
        save_record(record=record, record_type="execution_worker_heartbeat")
    read_memory_dict(current_store, "execution_worker_heartbeats")[worker_id] = deepcopy(record)
    return record


def execution_operations_overview(current_store: Any) -> dict[str, Any]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_trusted_delivery_records", None)
    heartbeats = (
        list_records(record_type="execution_worker_heartbeat")
        if callable(list_records)
        else read_memory_records(current_store, "execution_worker_heartbeats")
    )
    outbox = read_memory_records(current_store, "execution_outbox_events")
    if getattr(current_store, "repository", None) is not None:
        list_outbox = getattr(repository, "list_execution_outbox_events", None)
        if callable(list_outbox):
            outbox = list_outbox(aggregate_id=None, aggregate_type=None, status=None)
    status_counts: dict[str, int] = {}
    for event in outbox:
        status = str(event.get("status") or "pending")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "outbox_status_counts": status_counts,
        "workers": [
            {
                "claimed_count": item.get("claimed_count", 0),
                "updated_at": item.get("updated_at"),
                "worker_id": item.get("worker_id"),
            }
            for item in heartbeats
        ],
    }
