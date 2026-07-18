from __future__ import annotations

from pathlib import Path

from app.core.store import MemoryStore
from app.services.rd_collaboration_migration import (
    begin_cutover,
    build_upgrade_preflight,
    record_cleanup_completed,
    record_cutover_health,
)
from app.services.rd_maintenance_fence import get_rd_maintenance_state


def test_upgrade_preflight_blocks_active_ai_task() -> None:
    store = MemoryStore()
    store.ai_tasks["task-active"] = {"id": "task-active", "status": "running"}

    report = build_upgrade_preflight(store)

    assert report["ready"] is False
    assert report["blockers"][0]["code"] == "RD_UPGRADE_ACTIVE_TASKS"


def test_upgrade_preflight_requires_explicit_conversion_for_empty_legacy_policy() -> None:
    store = MemoryStore()
    store.rd_task_executor_policies["legacy-policy"] = {
        "id": "legacy-policy",
        "status": "active",
        "strategy_config": {},
    }

    report = build_upgrade_preflight(store)

    assert report["ready"] is False
    assert report["policy_conversion_preview"] == {
        "legacy_policy_ids": ["legacy-policy"],
        "requires_conversion": True,
    }
    assert report["blockers"][-1]["code"] == "RD_UPGRADE_POLICY_CONVERSION_REQUIRED"


def test_cutover_requires_draining_backup_and_a_clean_locked_preflight() -> None:
    store = MemoryStore()

    state = get_rd_maintenance_state(store)
    assert state["fence_mode"] == "disabled"

    from app.services.rd_maintenance_fence import set_rd_maintenance_fence

    draining = set_rd_maintenance_fence(
        store,
        mode="draining",
        actor_id="admin",
        expected_version=state["version"],
        reason="perform preflight",
    )
    locked = begin_cutover(
        store,
        actor_id="admin",
        backup_marker="backup:2026-07-18",
        expected_version=draining["version"],
        v2_api_version="2.0.0",
        v2_graph_version="2",
        v2_worker_version="2.0.0",
    )
    assert locked["fence_mode"] == "cutover_locked"
    assert locked["schema_version"] == 2

    healthy = record_cutover_health(
        store,
        actor_id="admin",
        expected_version=locked["version"],
        health_marker="health:2026-07-18",
        smoke_test={"assessment": "passed", "collaboration": "passed"},
        v2_api_version="2.0.0",
        v2_graph_version="2",
        v2_worker_version="2.0.0",
    )
    assert healthy["health_marker"] == "health:2026-07-18"
    cleaned = record_cleanup_completed(store, actor_id="admin", expected_version=healthy["version"])
    assert cleaned["cleanup_completed_at"]


def test_destructive_cleanup_is_not_in_automatic_migration_registry() -> None:
    persistence_source = Path(__file__).parents[1] / "app" / "core" / "persistence.py"
    source = persistence_source.read_text(encoding="utf-8")
    assert "121_requirement_driven_rd_cutover.sql" not in source
