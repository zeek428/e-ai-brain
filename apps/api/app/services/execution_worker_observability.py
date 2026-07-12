from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import read_memory_records


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _trusted_delivery_records(
    current_store: Any,
    record_type: str,
    memory_name: str,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_trusted_delivery_records", None)
    if callable(list_records):
        return [dict(item) for item in list_records(record_type=record_type)]
    return [dict(item) for item in read_memory_records(current_store, memory_name)]


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
    heartbeats = getattr(current_store, "execution_worker_heartbeats", None)
    if isinstance(heartbeats, dict):
        heartbeats[worker_id] = deepcopy(record)
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
    now = datetime.now(UTC)
    status_counts: dict[str, int] = {}
    pending_ages: list[int] = []
    expired_lease_count = 0
    retry_count = 0
    for event in outbox:
        status = str(event.get("status") or "pending")
        status_counts[status] = status_counts.get(status, 0) + 1
        attempts = int(event.get("attempt_count") or 0)
        if attempts > 1:
            retry_count += 1
        created_at = _parse_timestamp(event.get("created_at"))
        if status in {"pending", "failed", "processing"} and created_at is not None:
            pending_ages.append(max(0, int((now - created_at).total_seconds())))
        lease_until = _parse_timestamp(event.get("lease_until"))
        if status == "processing" and lease_until is not None and lease_until <= now:
            expired_lease_count += 1
    operations = _trusted_delivery_records(
        current_store,
        "external_operation",
        "external_operations",
    )
    reconciliation_items = [
        {
            "id": item.get("id"),
            "operation_type": item.get("operation_type"),
            "product_id": item.get("product_id"),
            "provider": item.get("provider"),
            "status": item.get("status"),
            "updated_at": item.get("updated_at"),
        }
        for item in operations
        if item.get("status") in {"unknown", "reconciling", "manual_reconciliation"}
    ]
    reconciliation_items.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return {
        "backlog": {
            "dead_letter_count": status_counts.get("dead_letter", 0),
            "expired_lease_count": expired_lease_count,
            "oldest_pending_seconds": max(pending_ages, default=0),
            "pending_count": sum(
                status_counts.get(status, 0) for status in ("pending", "failed", "processing")
            ),
            "retry_count": retry_count,
        },
        "outbox_status_counts": status_counts,
        "reconciliation": {
            "items": reconciliation_items[:50],
            "manual_count": sum(
                1 for item in reconciliation_items if item.get("status") == "manual_reconciliation"
            ),
            "pending_count": sum(
                1 for item in reconciliation_items if item.get("status") != "manual_reconciliation"
            ),
        },
        "workers": [
            {
                "claimed_count": item.get("claimed_count", 0),
                "updated_at": item.get("updated_at"),
                "worker_id": item.get("worker_id"),
            }
            for item in heartbeats
        ],
    }
