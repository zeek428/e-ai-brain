"""Preflight and health evidence for the one-way R&D collaboration cutover."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.rd_maintenance_fence import (
    get_rd_maintenance_state,
    lock_rd_maintenance_fence,
    save_rd_maintenance_state,
)

_ACTIVE_AI_TASK_STATUSES = {
    "draft",
    "running",
    "waiting_more_info",
    "waiting_review",
    "writing_back",
}
_ACTIVE_AGENT_LOOP_STATUSES = {
    "planning",
    "executing",
    "verifying",
    "reflecting",
    "waiting_review",
}
_ACTIVE_RUNNER_STATUSES = {"queued", "claimed", "running"}
_ACTIVE_COLLABORATION_STATUSES = {
    "running",
    "integrating",
    "verifying",
    "waiting_human",
    "ready_for_release",
    "deploying",
}


def _rows(current_store: Any, collection: str, repository_method: str) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    getter = getattr(repository, repository_method, None)
    if callable(getter):
        try:
            return [dict(row) for row in getter()]
        except TypeError:
            pass
    values = getattr(current_store, collection, {})
    return [dict(row) for row in values.values()] if isinstance(values, dict) else []


def _active_count(rows: list[dict[str, Any]], statuses: set[str]) -> int:
    return sum(1 for row in rows if str(row.get("status")) in statuses)


def build_upgrade_preflight(current_store: Any) -> dict[str, Any]:
    ai_tasks = _rows(current_store, "ai_tasks", "list_ai_task_summaries")
    agent_loops = _rows(current_store, "agent_loop_runs", "list_agent_loop_runs")
    runner_tasks = _rows(current_store, "ai_executor_tasks", "list_ai_executor_tasks")
    runs = _rows(current_store, "rd_collaboration_runs", "list_rd_collaboration_runs")
    policies = _rows(current_store, "rd_task_executor_policies", "list_rd_task_executor_policies")
    active_counts = {
        "active_agent_loops": _active_count(agent_loops, _ACTIVE_AGENT_LOOP_STATUSES),
        "active_ai_tasks": _active_count(ai_tasks, _ACTIVE_AI_TASK_STATUSES),
        "active_collaboration_runs": _active_count(runs, _ACTIVE_COLLABORATION_STATUSES),
        "active_runner_tasks": _active_count(runner_tasks, _ACTIVE_RUNNER_STATUSES),
    }
    blockers: list[dict[str, Any]] = []
    for key, code in (
        ("active_ai_tasks", "RD_UPGRADE_ACTIVE_TASKS"),
        ("active_agent_loops", "RD_UPGRADE_ACTIVE_AGENT_LOOPS"),
        ("active_runner_tasks", "RD_UPGRADE_ACTIVE_RUNNER_TASKS"),
        ("active_collaboration_runs", "RD_UPGRADE_ACTIVE_COLLABORATION_RUNS"),
    ):
        if active_counts[key]:
            blockers.append({"code": code, "count": active_counts[key]})
    legacy_policy_ids = [
        str(policy.get("id"))
        for policy in policies
        if policy.get("status") == "active"
        and (
            not isinstance(policy.get("strategy_config"), dict) or not policy.get("strategy_config")
        )
    ]
    if legacy_policy_ids:
        blockers.append(
            {
                "code": "RD_UPGRADE_POLICY_CONVERSION_REQUIRED",
                "policy_ids": legacy_policy_ids,
            }
        )
    return {
        "active_counts": active_counts,
        "blockers": blockers,
        "checked_at": datetime.now(UTC).isoformat(),
        "policy_conversion_preview": {
            "legacy_policy_ids": legacy_policy_ids,
            "requires_conversion": bool(legacy_policy_ids),
        },
        "ready": not blockers,
    }


def begin_cutover(
    current_store: Any,
    *,
    actor_id: str,
    backup_marker: str,
    expected_version: int,
    v2_api_version: str,
    v2_graph_version: str,
    v2_worker_version: str,
) -> dict[str, Any]:
    if not all(value.strip() for value in (v2_api_version, v2_graph_version, v2_worker_version)):
        raise api_error(422, "VALIDATION_ERROR", "Every v2 runtime version is required")
    report = build_upgrade_preflight(current_store)
    return lock_rd_maintenance_fence(
        current_store,
        actor_id=actor_id,
        expected_version=expected_version,
        backup_marker=backup_marker,
        locked_preflight=report,
        versions={
            "v2_api_version": v2_api_version,
            "v2_graph_version": v2_graph_version,
            "v2_worker_version": v2_worker_version,
        },
    )


def record_cutover_health(
    current_store: Any,
    *,
    actor_id: str,
    expected_version: int,
    health_marker: str,
    smoke_test: dict[str, Any],
    v2_api_version: str,
    v2_graph_version: str,
    v2_worker_version: str,
) -> dict[str, Any]:
    state = get_rd_maintenance_state(current_store)
    if state["fence_mode"] != "cutover_locked":
        raise api_error(409, "RD_UPGRADE_STATE_INVALID", "Health evidence requires cutover lock")
    versions_match = (
        state.get("v2_api_version") == v2_api_version
        and state.get("v2_graph_version") == v2_graph_version
        and state.get("v2_worker_version") == v2_worker_version
    )
    if not versions_match:
        raise api_error(
            409,
            "RD_UPGRADE_STATE_INVALID",
            "V2 health versions do not match cutover lock",
        )
    if (
        not health_marker.strip()
        or smoke_test.get("assessment") != "passed"
        or smoke_test.get("collaboration") != "passed"
    ):
        raise api_error(
            409,
            "RD_UPGRADE_STATE_INVALID",
            "V2 health and both write smoke tests are required",
        )
    return save_rd_maintenance_state(
        current_store,
        expected_version=expected_version,
        actor_id=actor_id,
        reason="v2 worker and write smoke validation",
        changes={
            "health_marker": health_marker,
            "smoke_test_json": smoke_test,
        },
    )


def record_cleanup_completed(
    current_store: Any,
    *,
    actor_id: str,
    expected_version: int,
) -> dict[str, Any]:
    """Testable state projection for the explicit SQL cleanup script result."""
    state = get_rd_maintenance_state(current_store)
    if state["fence_mode"] != "cutover_locked" or int(state.get("schema_version") or 0) != 2:
        raise api_error(
            409,
            "RD_UPGRADE_STATE_INVALID",
            "Cleanup completion requires locked schema v2",
        )
    return save_rd_maintenance_state(
        current_store,
        expected_version=expected_version,
        actor_id=actor_id,
        reason="explicit cleanup completed",
        changes={
            "cleanup_started_at": state.get("cleanup_started_at") or datetime.now(UTC).isoformat(),
            "cleanup_completed_at": datetime.now(UTC).isoformat(),
        },
    )
