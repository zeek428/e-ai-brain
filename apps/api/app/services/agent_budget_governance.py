from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import read_memory_dict


def _save(current_store: Any, record: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_trusted_delivery_record", None)
    if callable(save_record):
        save_record(record=record, record_type="agent_budget_ledger")
    read_memory_dict(current_store, "agent_budget_ledgers")[record["id"]] = deepcopy(record)


def _ledger(current_store: Any, ledger_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_trusted_delivery_records", None)
    if callable(list_records):
        return next(
            (
                dict(record)
                for record in list_records(record_type="agent_budget_ledger")
                if record.get("id") == ledger_id
            ),
            None,
        )
    record = read_memory_dict(current_store, "agent_budget_ledgers").get(ledger_id)
    return dict(record) if record else None


def latest_agent_budget_ledger(current_store: Any, *, ai_task_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_trusted_delivery_records", None)
    records = (
        list_records(record_type="agent_budget_ledger")
        if callable(list_records)
        else read_memory_dict(current_store, "agent_budget_ledgers").values()
    )
    matches = [dict(record) for record in records if record.get("ai_task_id") == ai_task_id]
    return max(matches, key=lambda record: str(record.get("created_at") or "")) if matches else None


def reserve_agent_budget(
    current_store: Any,
    *,
    ai_task_id: str,
    cost_budget: float | None,
    product_id: str | None = None,
    token_budget: int | None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    record = {
        "ai_task_id": ai_task_id,
        "cost_budget": cost_budget,
        "cost_reserved": float(cost_budget or 0),
        "cost_settled": 0.0,
        "created_at": now,
        "id": current_store.new_id("agent_budget_ledger"),
        "product_id": product_id,
        "status": "reserved",
        "token_budget": token_budget,
        "token_reserved": int(token_budget or 0),
        "token_settled": 0,
        "updated_at": now,
    }
    _save(current_store, record)
    return deepcopy(record)


def settle_agent_budget(
    current_store: Any,
    *,
    ledger_id: str,
    cost_used: float,
    token_used: int,
) -> dict[str, Any]:
    ledger = _ledger(current_store, ledger_id)
    if ledger is None:
        raise ValueError("Agent budget ledger not found")
    ledger = {
        **ledger,
        "cost_settled": min(float(ledger["cost_reserved"]), float(cost_used)),
        "status": "settled",
        "token_settled": min(int(ledger["token_reserved"]), int(token_used)),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _save(current_store, ledger)
    return deepcopy(ledger)


def evaluate_agent_circuit_breaker(iterations: list[dict[str, Any]]) -> str | None:
    recent = [
        item.get("failure_fingerprint")
        or (item.get("failure_analysis") or {}).get("failure_fingerprint")
        for item in iterations[-2:]
    ]
    if len(recent) == 2 and recent[0] and recent[0] == recent[1]:
        return "AGENT_LOOP_CIRCUIT_OPEN"
    return None
