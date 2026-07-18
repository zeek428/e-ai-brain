from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import api_error
from app.core.store import MemoryStore
from app.main import app
from app.services.rd_collaboration_migration import (
    begin_cutover,
    record_cleanup_completed,
    record_cutover_health,
)
from app.services.rd_maintenance_fence import (
    get_rd_maintenance_state,
    require_rd_write_allowed,
    set_rd_maintenance_fence,
)
from app.services.rd_work_item_scheduler import cancel_work_item


def test_maintenance_fence_blocks_writes_but_allows_inflight_and_leaves_scheduled_jobs() -> None:
    store = MemoryStore()
    store.scheduled_jobs["scheduled-1"] = {"id": "scheduled-1", "status": "active"}
    draining = set_rd_maintenance_fence(
        store,
        mode="draining",
        actor_id="admin",
        expected_version=get_rd_maintenance_state(store)["version"],
        reason="cutover",
    )

    with pytest.raises(type(api_error(423, "RD_UPGRADE_MAINTENANCE", "blocked"))) as exc_info:
        require_rd_write_allowed(store, operation="requirement_assessment.start")
    assert exc_info.value.detail["code"] == "RD_UPGRADE_MAINTENANCE"
    assert exc_info.value.detail["fence_version"] == draining["version"]
    require_rd_write_allowed(
        store,
        operation="work_item.inflight_completion",
        allow_inflight_completion=True,
    )
    assert store.scheduled_jobs["scheduled-1"]["status"] == "active"
    assert draining["fence_mode"] == "draining"


def test_only_controlled_admin_drain_cancellation_can_cancel_existing_work() -> None:
    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "product_id": "product-1",
        "status": "running",
    }
    store.rd_work_items["work-1"] = {
        "id": "work-1",
        "collaboration_run_id": "run-1",
        "status": "ready",
        "risk_level": "low",
        "version": 1,
    }
    draining = set_rd_maintenance_fence(
        store,
        mode="draining",
        actor_id="admin",
        expected_version=get_rd_maintenance_state(store)["version"],
        reason="cutover",
    )

    with pytest.raises(type(api_error(423, "RD_UPGRADE_MAINTENANCE", "blocked"))):
        cancel_work_item(
            store,
            work_item_id="work-1",
            reason="ordinary cancellation",
            actor={"id": "owner"},
            version=1,
            idempotency_key="ordinary-cancel",
        )
    cancelled = cancel_work_item(
        store,
        work_item_id="work-1",
        reason="controlled drain cancellation",
        actor={"id": "admin"},
        version=1,
        idempotency_key="drain-cancel",
        maintenance_drain_cancel=True,
    )
    assert draining["fence_mode"] == "draining"
    assert cancelled["work_item"]["status"] == "cancelled"


def test_draining_abort_and_locked_release_require_their_respective_evidence() -> None:
    store = MemoryStore()
    draining = set_rd_maintenance_fence(
        store,
        mode="draining",
        actor_id="admin",
        expected_version=get_rd_maintenance_state(store)["version"],
        reason="preflight",
    )
    aborted = set_rd_maintenance_fence(
        store,
        mode="disabled",
        actor_id="admin",
        expected_version=draining["version"],
        reason="preflight blocker",
    )
    assert aborted["fence_mode"] == "disabled"

    draining = set_rd_maintenance_fence(
        store,
        mode="draining",
        actor_id="admin",
        expected_version=aborted["version"],
        reason="retry",
    )
    locked = begin_cutover(
        store,
        actor_id="admin",
        backup_marker="backup:ok",
        expected_version=draining["version"],
        v2_api_version="2.0.0",
        v2_graph_version="2",
        v2_worker_version="2.0.0",
    )
    with pytest.raises(type(api_error(409, "RD_UPGRADE_ABORT_NOT_ALLOWED", "blocked"))) as exc_info:
        set_rd_maintenance_fence(
            store,
            mode="disabled",
            actor_id="admin",
            expected_version=locked["version"],
            reason="try rollback",
        )
    assert exc_info.value.detail["code"] == "RD_UPGRADE_ABORT_NOT_ALLOWED"

    healthy = record_cutover_health(
        store,
        actor_id="admin",
        expected_version=locked["version"],
        health_marker="healthy",
        smoke_test={"assessment": "passed", "collaboration": "passed"},
        v2_api_version="2.0.0",
        v2_graph_version="2",
        v2_worker_version="2.0.0",
    )
    cleaned = record_cleanup_completed(
        store,
        actor_id="admin",
        expected_version=healthy["version"],
    )
    released = set_rd_maintenance_fence(
        store,
        mode="disabled",
        actor_id="admin",
        expected_version=cleaned["version"],
        reason="release v2",
        expected_schema_version=2,
    )
    assert released["fence_mode"] == "disabled"


def test_admin_upgrade_endpoints_expose_read_only_preflight_and_versioned_fence() -> None:
    original_store = app.state.store
    test_store = MemoryStore()
    test_store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "product_id": "product-1",
        "status": "running",
    }
    test_store.rd_work_items["work-1"] = {
        "id": "work-1",
        "collaboration_run_id": "run-1",
        "status": "ready",
        "risk_level": "low",
        "version": 1,
    }
    app.state.store = test_store
    try:
        client = TestClient(app)
        login = client.post(
            "/api/auth/login", json={"username": "admin@example.com", "password": "admin123"}
        )
        headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        preflight = client.get("/api/system/rd-collaboration-upgrade/preflight", headers=headers)
        assert preflight.status_code == 200
        assert preflight.json()["data"]["report"]["ready"] is False
        blocker = preflight.json()["data"]["report"]["blockers"][0]
        assert blocker["code"] == "RD_UPGRADE_ACTIVE_COLLABORATION_RUNS"
        state = preflight.json()["data"]["state"]
        draining = client.post(
            "/api/system/rd-collaboration-upgrade/maintenance-fence",
            headers=headers,
            json={
                "mode": "draining",
                "expected_version": state["version"],
                "reason": "test cutover",
            },
        )
        assert draining.status_code == 200
        assert draining.json()["data"]["fence_mode"] == "draining"
        drain_cancel = client.post(
            "/api/system/rd-collaboration-upgrade/drain-cancel/work-1",
            headers=headers,
            json={
                "reason": "clear a remaining work item",
                "version": 1,
                "idempotency_key": "test-drain-cancel",
            },
        )
        assert drain_cancel.status_code == 200
        assert drain_cancel.json()["data"]["work_item"]["status"] == "cancelled"
    finally:
        app.state.store = original_store
