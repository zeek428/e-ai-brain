"""Dispatch eligible AI work items from the durable collaboration DAG."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from app.core.repositories.rd_collaboration import RdCollaborationRepositoryError
from app.services.rd_dispatch_fault_decision import (
    classify_dispatch_fault,
    escalate_dispatch_fault_for_human,
    record_retryable_dispatch_fault,
)
from app.services.rd_high_risk_dispatch_gate import (
    high_risk_dispatch_is_approved,
    require_human_approval_for_high_risk_dispatch,
)
from app.services.rd_work_item_scheduler import ready_work_item_page
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


def _decode_cursor(value: Any) -> tuple[datetime | None, int, str] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    due_at = value[0]
    if isinstance(due_at, str):
        due_at = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
    if due_at is not None and not isinstance(due_at, datetime):
        return None
    return due_at, int(value[1]), str(value[2])


def _encode_cursor(cursor: tuple[datetime | None, int, str]) -> list[Any]:
    return [cursor[0].isoformat() if cursor[0] is not None else None, cursor[1], cursor[2]]


def dispatch_ready_ai_work_items(
    store: Any,
    *,
    limit: int = 50,
    now: datetime | None = None,
) -> dict[str, list[str]]:
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
    observed_at = now or datetime.now(UTC)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    scheduler_now = observed_at if now is not None else None

    def record_retry(work_item: dict[str, Any], fault: Any) -> None:
        work_item_id = str(work_item["id"])
        recorded = record_retryable_dispatch_fault(
            store,
            collaboration_run_id=str(work_item["collaboration_run_id"]),
            work_item_id=work_item_id,
            expected_version=int(work_item.get("version") or 1),
            fault=fault,
            observed_at=observed_at,
        )
        if recorded is None:
            skipped.append(work_item_id)
        elif recorded.get("outcome") == "escalated":
            escalated.append(work_item_id)
        else:
            retryable.append(work_item_id)

    candidate_pages: list[tuple[str, list[dict[str, Any]], bool]] = []
    repository = getattr(store, "repository", None)
    reserve_candidates = getattr(repository, "reserve_due_rd_dispatch_candidates", None)
    if callable(reserve_candidates):
        reserved = [
            dict(item)
            for item in reserve_candidates(
                limit=limit,
                due_at=observed_at,
            )
        ][:limit]
        candidates_by_run: dict[str, list[dict[str, Any]]] = {}
        for item in reserved:
            run_id = str(item.get("collaboration_run_id") or "")
            if run_id:
                candidates_by_run.setdefault(run_id, []).append(item)
        for run_id, candidates in candidates_by_run.items():
            page, _, _ = ready_work_item_page(
                store,
                collaboration_run_id=run_id,
                scan_limit=len(candidates),
                now=scheduler_now,
                candidate_items=candidates,
            )
            candidate_pages.append((run_id, page, True))
    else:
        runs = [
            run
            for run in sorted(_runs(store), key=lambda item: str(item.get("id") or ""))
            if run.get("status") in _DISPATCHABLE_RUN_STATUSES and str(run.get("id") or "")
        ]
        settings = getattr(store, "system_settings", None)
        if not isinstance(settings, dict):
            settings = {}
            store.system_settings = settings
        cursor_state = settings.setdefault(
            "_rd_dispatch_candidate_cursor",
            {"last_run_id": None, "runs": {}},
        )
        last_run_id = cursor_state.get("last_run_id")
        run_ids = [str(run["id"]) for run in runs]
        if last_run_id in run_ids:
            split = run_ids.index(last_run_id) + 1
            run_ids = run_ids[split:] + run_ids[:split]
        examined = 0
        for run_id in run_ids:
            if examined >= limit:
                break
            cursor = _decode_cursor(cursor_state["runs"].get(run_id))
            page, next_cursor, examined_count = ready_work_item_page(
                store,
                collaboration_run_id=run_id,
                scan_limit=limit - examined,
                after=cursor,
                now=scheduler_now,
            )
            if examined_count == 0 and cursor is not None:
                page, next_cursor, examined_count = ready_work_item_page(
                    store,
                    collaboration_run_id=run_id,
                    scan_limit=limit - examined,
                    after=None,
                    now=scheduler_now,
                )
            examined += examined_count
            if next_cursor is not None:
                cursor_state["runs"][run_id] = _encode_cursor(next_cursor)
            cursor_state["last_run_id"] = run_id
            candidate_pages.append((run_id, page, False))

    for run_id, page, reservation_bound in candidate_pages:
        for work_item in page:
            if work_item.get("status") not in {"ready", "rework_required"}:
                continue
            if not _is_ai_owned(store, work_item):
                continue
            work_item_id = str(work_item["id"])
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
                            record_retry(work_item, fault)
                        continue
                    human_review_required.append(work_item_id)
                    continue
            try:
                reservation_kwargs = (
                    {
                        "expected_work_item_version": int(work_item.get("version") or 1),
                        "dispatch_due_at": observed_at,
                    }
                    if reservation_bound
                    else {}
                )
                dispatch_ai_task_for_work_item(
                    store,
                    collaboration_run_id=run_id,
                    work_item_id=work_item_id,
                    **reservation_kwargs,
                )
            except (HTTPException, RdCollaborationRepositoryError) as exc:
                if isinstance(exc, RdCollaborationRepositoryError) and exc.code in {
                    "RD_DISPATCH_RESERVATION_STALE",
                    "RD_VERSION_CONFLICT",
                }:
                    skipped.append(work_item_id)
                    continue
                fault = classify_dispatch_fault(exc)
                if fault.outcome == "deferred":
                    capacity_deferred.append(work_item_id)
                    continue
                if fault.outcome == "retryable":
                    record_retry(work_item, fault)
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
                        record_retry(work_item, escalation_fault)
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
