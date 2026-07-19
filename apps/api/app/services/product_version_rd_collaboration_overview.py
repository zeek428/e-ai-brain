"""Safe R&D-collaboration summary for the product-version delivery dashboard."""

from __future__ import annotations

from typing import Any

TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled"}
PENDING_DECISION_STATUSES = {"pending", "waiting_more_info"}
BLOCKED_WORK_ITEM_STATUSES = {"blocked", "failed", "rework_required"}
WAITING_HUMAN_WORK_ITEM_STATUSES = {"awaiting_human", "waiting_human"}
RD_COLLABORATION_ROLES = {"admin", "rd_owner", "product_owner", "developer", "tester"}


def _records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return list(collection.values()) if isinstance(collection, dict) else []


def _can_read_or_plan(user: dict[str, Any]) -> bool:
    roles = set(user.get("roles") or [])
    permissions = set(user.get("permissions") or [])
    return bool(
        roles & RD_COLLABORATION_ROLES
        or {"system.admin", "delivery.rd_collaboration.read", "delivery.rd_collaboration.plan"}
        & permissions
    )


def _run_summary(current_store: Any, run: dict[str, Any]) -> dict[str, Any]:
    run_id = str(run["id"])
    seats = [
        seat
        for seat in _records(current_store, "rd_run_seats")
        if seat.get("collaboration_run_id") == run_id
    ]
    work_items = [
        work_item
        for work_item in _records(current_store, "rd_work_items")
        if work_item.get("collaboration_run_id") == run_id
    ]
    decisions = [
        decision
        for decision in _records(current_store, "decision_requests")
        if decision.get("subject_type") == "rd_collaboration_run"
        and decision.get("subject_id") == run_id
        and decision.get("status") in PENDING_DECISION_STATUSES
    ]
    ai_seat_ids = {
        str(seat["id"])
        for seat in seats
        if seat.get("status") == "active"
        and seat.get("subject_type") == "ai_employee"
        and seat.get("id")
    }
    frozen_capacity = sum(
        max(0, int(seat.get("capacity") or 1))
        for seat in seats
        if str(seat.get("id") or "") in ai_seat_ids
    )
    used_capacity = sum(
        1
        for work_item in work_items
        if work_item.get("status") == "running"
        and str(work_item.get("owner_seat_id") or "") in ai_seat_ids
    )
    conflict_keys: set[tuple[str, str, str, str, str]] = set()
    for work_item in work_items:
        release_conditions = work_item.get("release_conditions")
        if isinstance(release_conditions, list):
            conflicts = [
                condition
                for condition in release_conditions
                if isinstance(condition, dict)
                and condition.get("kind") == "parallel_resource_conflict"
            ]
        elif isinstance(release_conditions, dict):
            # Compatibility with plans produced during the initial P1 rollout.
            conflicts = release_conditions.get("parallel_resource_conflicts") or []
        else:
            conflicts = []
        for conflict in conflicts:
            if not isinstance(conflict, dict):
                continue
            conflict_keys.add(
                (
                    str(conflict.get("predecessor_work_item_id") or ""),
                    str(conflict.get("successor_work_item_id") or ""),
                    str(conflict.get("repository_id") or ""),
                    str(conflict.get("path") or ""),
                    str(conflict.get("other_path") or ""),
                )
            )
    return {
        "capacity": {
            "available": max(0, frozen_capacity - used_capacity),
            "frozen": frozen_capacity,
            "used": used_capacity,
        },
        "blocked_work_item_count": sum(
            1
            for work_item in work_items
            if work_item.get("status") in BLOCKED_WORK_ITEM_STATUSES
        ),
        "delivery_target": run.get("delivery_target") or "ready_for_release",
        "id": run_id,
        "pending_decision_count": len(decisions),
        "parallel_conflict_count": len(conflict_keys),
        "role_codes": sorted(
            {
                str(seat["role_code"])
                for seat in seats
                if str(seat.get("role_code") or "").strip()
            }
        ),
        "run_generation": int(run.get("run_generation") or 1),
        "scope_version": int(run.get("scope_version") or 1),
        "seat_count": len(seats),
        "status": run.get("status") or "draft",
        "total_work_item_count": len(work_items),
        "waiting_human_work_item_count": sum(
            1
            for work_item in work_items
            if work_item.get("status") in WAITING_HUMAN_WORK_ITEM_STATUSES
        ),
    }


def version_rd_collaboration_overview(
    current_store: Any,
    *,
    user: dict[str, Any],
    version_id: str,
) -> dict[str, Any] | None:
    """Return a permission-safe entry summary without exposing policy payloads."""
    if not _can_read_or_plan(user):
        return None

    runs = [
        run
        for run in _records(current_store, "rd_collaboration_runs")
        if run.get("product_version_id") == version_id
    ]
    runs.sort(
        key=lambda run: (int(run.get("run_generation") or 1), str(run.get("id") or "")),
        reverse=True,
    )
    active_run = next(
        (run for run in runs if run.get("status") not in TERMINAL_RUN_STATUSES),
        None,
    )
    if active_run is not None:
        return {
            "action": {
                "label": "继续研发协同",
                "run_id": str(active_run["id"]),
                "type": "continue",
            },
            "active_run": _run_summary(current_store, active_run),
        }

    if runs:
        latest_run = _run_summary(current_store, runs[0])
        return {
            "action": {
                "label": "重新启动研发协同",
                "run_id": latest_run["id"],
                "type": "restart",
            },
            "active_run": None,
            "latest_run": latest_run,
        }

    return {
        "action": {"label": "启动研发协同", "type": "start"},
        "active_run": None,
    }
