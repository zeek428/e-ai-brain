"""Dispatch eligible AI work items from the durable collaboration DAG."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.core.repositories.rd_collaboration import RdCollaborationRepositoryError
from app.services.rd_dispatch_fault_decision import (
    classify_dispatch_fault,
    escalate_dispatch_fault_for_human,
)
from app.services.rd_high_risk_dispatch_gate import (
    high_risk_dispatch_is_approved,
    require_human_approval_for_high_risk_dispatch,
)
from app.services.rd_work_item_scheduler import ready_work_items
from app.services.task_start_execution import dispatch_ai_task_for_work_item

_DISPATCHABLE_RUN_STATUSES = {"running", "integrating", "verifying"}
_HUMAN_REVIEW_RISK_LEVELS = {"high", "critical"}


def _records(store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    records = getattr(store, collection_name, None)
    return records if isinstance(records, dict) else {}


def _runs(store: Any) -> list[dict[str, Any]]:
    repository = getattr(store, "repository", None)
    list_runs = getattr(repository, "list_rd_collaboration_runs", None)
    if callable(list_runs):
        return [dict(run) for run in list_runs() if isinstance(run, dict)]
    return [dict(run) for run in _records(store, "rd_collaboration_runs").values()]


def _seat(store: Any, seat_id: str) -> dict[str, Any] | None:
    repository = getattr(store, "repository", None)
    get_seat = getattr(repository, "get_rd_run_seat", None)
    if callable(get_seat):
        record = get_seat(seat_id)
        return dict(record) if isinstance(record, dict) else None
    record = _records(store, "rd_run_seats").get(seat_id)
    return dict(record) if isinstance(record, dict) else None


def _is_ai_owned(store: Any, work_item: dict[str, Any]) -> bool:
    owner = _seat(store, str(work_item.get("owner_seat_id") or ""))
    # An inactive frozen AI seat is still AI-owned work and must reach the
    # classifier so it can be paused for repair instead of silently omitted.
    return bool(owner and owner.get("subject_type") == "ai_employee")


def dispatch_ready_ai_work_items(store: Any, *, limit: int = 50) -> dict[str, list[str]]:
    """Dispatch AI-owned DAG work only after the frozen risk gate allows it.

    The dispatcher intentionally delegates the state transition to
    ``dispatch_ai_task_for_work_item``.  That command owns the compare-and-set
    write, immutable attempt identity, Runner queue record, and replay response,
    so repeated worker sweeps and concurrent workers cannot create duplicate
    tasks.  High and critical risks atomically create a human decision and
    pause first; only an approved frozen decision permits their later dispatch.
    """
    if limit <= 0:
        return {
            "capacity_deferred_work_item_ids": [],
            "dispatched_work_item_ids": [],
            "escalated_work_item_ids": [],
            "human_review_required_work_item_ids": [],
            "retryable_work_item_ids": [],
            "skipped_work_item_ids": [],
        }

    dispatched: list[str] = []
    capacity_deferred: list[str] = []
    escalated: list[str] = []
    human_review_required: list[str] = []
    retryable: list[str] = []
    skipped: list[str] = []
    processed = 0
    for run in sorted(_runs(store), key=lambda item: str(item.get("id") or "")):
        if processed >= limit or run.get("status") not in _DISPATCHABLE_RUN_STATUSES:
            continue
        run_id = str(run.get("id") or "")
        if not run_id:
            continue
        for work_item in ready_work_items(store, collaboration_run_id=run_id):
            if processed >= limit:
                break
            if work_item.get("status") not in {"ready", "rework_required"}:
                continue
            if not _is_ai_owned(store, work_item):
                continue
            work_item_id = str(work_item["id"])
            processed += 1
            risk_level = str(work_item.get("risk_level") or "medium").lower()
            if risk_level in _HUMAN_REVIEW_RISK_LEVELS:
                if not high_risk_dispatch_is_approved(
                    store,
                    collaboration_run_id=run_id,
                    work_item_id=work_item_id,
                ):
                    try:
                        require_human_approval_for_high_risk_dispatch(
                            store,
                            collaboration_run_id=run_id,
                            work_item_id=work_item_id,
                        )
                    except HTTPException as exc:
                        fault = classify_dispatch_fault(exc)
                        if fault.outcome == "deferred":
                            capacity_deferred.append(work_item_id)
                        else:
                            retryable.append(work_item_id)
                        continue
                    human_review_required.append(work_item_id)
                    continue
            try:
                dispatch_ai_task_for_work_item(
                    store,
                    collaboration_run_id=run_id,
                    work_item_id=work_item_id,
                )
            except (HTTPException, RdCollaborationRepositoryError) as exc:
                fault = classify_dispatch_fault(exc)
                if fault.outcome == "deferred":
                    capacity_deferred.append(work_item_id)
                    continue
                if fault.outcome == "retryable":
                    retryable.append(work_item_id)
                    continue
                try:
                    escalate_dispatch_fault_for_human(
                        store,
                        collaboration_run_id=run_id,
                        work_item_id=work_item_id,
                        fault=fault,
                    )
                except HTTPException as escalation_exc:
                    escalation_fault = classify_dispatch_fault(escalation_exc)
                    if escalation_fault.outcome == "deferred":
                        capacity_deferred.append(work_item_id)
                    else:
                        retryable.append(work_item_id)
                    continue
                escalated.append(work_item_id)
                continue
            dispatched.append(work_item_id)
    return {
        "capacity_deferred_work_item_ids": capacity_deferred,
        "dispatched_work_item_ids": dispatched,
        "escalated_work_item_ids": escalated,
        "human_review_required_work_item_ids": human_review_required,
        "retryable_work_item_ids": retryable,
        "skipped_work_item_ids": skipped,
    }
