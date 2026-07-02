from __future__ import annotations

from typing import Any

from app.services.ai_executor_runner_constants import (
    AI_EXECUTOR_TASK_STATUSES,
    AI_EXECUTOR_TASK_TERMINAL_STATUSES,
)


def _read_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def runner_tasks(
    current_store: Any,
    runner_id: str | None,
) -> list[dict[str, Any]]:
    if runner_id is None:
        return []
    return [
        task
        for task in _read_collection(current_store, "ai_executor_tasks").values()
        if task.get("runner_id") == runner_id
    ]


def latest_task_for_runner(
    current_store: Any,
    runner_id: str | None,
) -> dict[str, Any] | None:
    return max(
        runner_tasks(current_store, runner_id),
        key=lambda task: (
            task.get("updated_at") or task.get("created_at") or "",
            task.get("id") or "",
        ),
        default=None,
    )


def runner_queue_summary(
    current_store: Any,
    runner: dict[str, Any],
) -> dict[str, Any]:
    tasks = runner_tasks(current_store, runner.get("id"))
    counts_by_status = {status: 0 for status in sorted(AI_EXECUTOR_TASK_STATUSES)}
    for task in tasks:
        status = str(task.get("status") or "")
        if status in counts_by_status:
            counts_by_status[status] += 1

    running_count = counts_by_status["claimed"] + counts_by_status["running"]
    terminal_count = sum(
        counts_by_status[status] for status in AI_EXECUTOR_TASK_TERMINAL_STATUSES
    )
    failed_count = (
        counts_by_status["dead_letter"]
        + counts_by_status["failed"]
        + counts_by_status["timed_out"]
    )
    max_concurrent_tasks = max(0, int(runner.get("max_concurrent_tasks") or 0))
    summary: dict[str, Any] = {
        "available_slots": max(0, max_concurrent_tasks - running_count),
        "cancelled": counts_by_status["cancelled"],
        "claimed": counts_by_status["claimed"],
        "counts_by_status": counts_by_status,
        "dead_letter": counts_by_status["dead_letter"],
        "failed": counts_by_status["failed"],
        "failed_total": failed_count,
        "max_concurrent_tasks": max_concurrent_tasks,
        "queued": counts_by_status["queued"],
        "running": counts_by_status["running"],
        "running_total": running_count,
        "succeeded": counts_by_status["succeeded"],
        "terminal_total": terminal_count,
        "timed_out": counts_by_status["timed_out"],
        "total": len(tasks),
    }
    latest_failed_task = _latest_failed_task(tasks)
    if latest_failed_task is not None:
        summary["latest_failure"] = {
            "error_code": latest_failed_task.get("error_code"),
            "error_message": latest_failed_task.get("error_message"),
            "finished_at": latest_failed_task.get("finished_at"),
            "id": latest_failed_task.get("id"),
            "status": latest_failed_task.get("status"),
            "updated_at": latest_failed_task.get("updated_at"),
        }
    return summary


def _latest_failed_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(
        (
            task
            for task in tasks
            if task.get("status") in {"dead_letter", "failed", "timed_out"}
        ),
        key=lambda task: (
            task.get("finished_at") or task.get("updated_at") or task.get("created_at") or "",
            task.get("id") or "",
        ),
        default=None,
    )
