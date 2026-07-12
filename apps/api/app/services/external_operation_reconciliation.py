from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import read_memory_dict


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _records(current_store: Any) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_trusted_delivery_records", None)
    if callable(list_records):
        return [dict(item) for item in list_records(record_type="external_operation")]
    return [dict(item) for item in read_memory_dict(current_store, "external_operations").values()]


def _save(current_store: Any, record: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_trusted_delivery_record", None)
    if callable(save_record):
        save_record(record=record, record_type="external_operation")
    read_memory_dict(current_store, "external_operations")[record["id"]] = deepcopy(record)


def record_external_operation(
    current_store: Any,
    *,
    idempotency_key: str,
    operation_type: str,
    product_id: str,
    provider: str,
    status: str,
) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in _records(current_store)
            if item.get("idempotency_key") == idempotency_key
        ),
        None,
    )
    if existing:
        return deepcopy(existing)
    now = _now()
    operation = {
        "created_at": now,
        "dispatch_count": 1,
        "id": current_store.new_id("external_operation"),
        "idempotency_key": idempotency_key,
        "operation_type": operation_type,
        "product_id": product_id,
        "provider": provider,
        "status": status,
        "updated_at": now,
    }
    _save(current_store, operation)
    return deepcopy(operation)


def reconcile_external_operations(
    current_store: Any,
    *,
    provider_lookup: Callable[[dict[str, Any]], dict[str, Any]],
) -> list[dict[str, Any]]:
    outcomes: list[dict[str, Any]] = []
    for operation in _records(current_store):
        if operation.get("status") not in {"unknown", "reconciling"}:
            continue
        operation["status"] = "reconciling"
        lookup = provider_lookup(deepcopy(operation))
        provider_status = str(lookup.get("provider_status") or "unknown")
        operation.update(
            {
                "provider_receipt": lookup.get("receipt"),
                "status": provider_status
                if provider_status in {"succeeded", "failed"}
                else "manual_reconciliation",
                "updated_at": _now(),
            }
        )
        _save(current_store, operation)
        outcomes.append({"id": operation["id"], "status": operation["status"]})
    return outcomes


def update_external_operation_status(
    current_store: Any,
    *,
    idempotency_key: str,
    status: str,
    receipt: str | None = None,
) -> dict[str, Any] | None:
    operation = next(
        (
            item
            for item in _records(current_store)
            if item.get("idempotency_key") == idempotency_key
        ),
        None,
    )
    if operation is None:
        return None
    operation.update(
        {
            "provider_receipt": receipt or operation.get("provider_receipt"),
            "status": status,
            "updated_at": _now(),
        }
    )
    _save(current_store, operation)
    return deepcopy(operation)
