from fastapi.testclient import TestClient

from app.core.store import MemoryStore
from app.main import app
from app.services.requirement_iteration_planning import (
    plan_accepted_requirement,
    validate_manual_iteration_assignment,
)

client = TestClient(app)


def _headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def _store_with_accepted_requirement() -> MemoryStore:
    store = MemoryStore()
    store.products["product-1"] = {"id": "product-1", "status": "active"}
    store.requirements["req-1"] = {
        "assessment_revision": 1,
        "id": "req-1",
        "product_id": "product-1",
        "status": "approved",
        "title": "归入兼容迭代",
        "version_id": None,
    }
    store.requirement_assessments["assessment-1"] = {
        "final_strategy_snapshot_id": "snapshot-1",
        "id": "assessment-1",
        "requirement_id": "req-1",
        "requirement_revision": 1,
        "risk_summary": {"risk_level": "low"},
        "status": "accepted",
    }
    store.rd_task_executor_policy_snapshots["snapshot-1"] = {
        "id": "snapshot-1",
        "policy_id": "policy-1",
        "policy_version": 7,
    }
    return store


def test_accepted_requirement_prefers_compatible_planning_version() -> None:
    store = _store_with_accepted_requirement()
    store.product_versions["version-planning-compatible"] = {
        "code": "2026-Q3",
        "id": "version-planning-compatible",
        "product_id": "product-1",
        "scope_version": 1,
        "status": "planning",
    }

    result = plan_accepted_requirement(
        store,
        requirement_id="req-1",
        assessment_id="assessment-1",
        actor_id="system",
    )

    assert result["version_id"] == "version-planning-compatible"
    assert result["created_version"] is False
    assert result["idempotency_key"] == "requirement:req-1:assessment:assessment-1"
    assert result["score_breakdown"]["hard_eligible"] is True
    assert store.requirements["req-1"]["status"] == "planned"
    assert store.product_versions["version-planning-compatible"]["scope_version"] == 2


def test_grouping_dry_runs_a_compatible_policy_merge_before_selecting_version() -> None:
    store = _store_with_accepted_requirement()
    store.rd_task_executor_policy_snapshots["snapshot-1"]["payload_json"] = {
        "delivery_target": "ready_for_release",
        "iteration_config": {"capacity": {"max_requirements": 4}},
    }
    store.rd_task_executor_policy_snapshots["snapshot-2"] = {
        "id": "snapshot-2",
        "payload_json": {
            "delivery_target": "ready_for_release",
            "iteration_config": {"capacity": {"max_requirements": 4}},
        },
        "policy_id": "policy-1",
        "policy_version": 7,
    }
    store.product_versions["version-planning-compatible"] = {
        "code": "2026-Q3",
        "id": "version-planning-compatible",
        "product_id": "product-1",
        "scope_version": 1,
        "status": "planning",
    }
    store.requirements["req-existing"] = {
        "assessment_revision": 1,
        "id": "req-existing",
        "product_id": "product-1",
        "status": "planned",
        "version_id": "version-planning-compatible",
    }
    store.requirement_assessments["assessment-existing"] = {
        "final_strategy_snapshot_id": "snapshot-2",
        "id": "assessment-existing",
        "requirement_id": "req-existing",
        "requirement_revision": 1,
        "status": "accepted",
    }

    result = plan_accepted_requirement(
        store,
        requirement_id="req-1",
        assessment_id="assessment-1",
        actor_id="system",
    )

    assert result["version_id"] == "version-planning-compatible"
    assert result["score_breakdown"]["hard_eligible"] is True


def test_grouping_creates_one_planning_version_when_no_candidate_exists() -> None:
    store = _store_with_accepted_requirement()

    result = plan_accepted_requirement(
        store,
        requirement_id="req-1",
        assessment_id="assessment-1",
        actor_id="system",
    )

    assert result["created_version"] is True
    assert result["version"]["status"] == "planning"
    assert result["version"]["scope_version"] == 2
    assert store.requirements["req-1"]["version_id"] == result["version_id"]


def test_tied_candidates_wait_for_a_plan_version_zero_decision() -> None:
    store = _store_with_accepted_requirement()
    for version_id in ("version-a", "version-b"):
        store.product_versions[version_id] = {
            "code": version_id,
            "id": version_id,
            "product_id": "product-1",
            "scope_version": 1,
            "status": "planning",
        }

    result = plan_accepted_requirement(
        store,
        requirement_id="req-1",
        assessment_id="assessment-1",
        actor_id="system",
    )

    assert result["status"] == "waiting_human"
    assert result["decision_request"]["plan_version"] == 0
    assert store.requirements["req-1"]["status"] == "approved"
    assert store.requirements["req-1"]["version_id"] is None


def test_high_risk_new_version_waits_for_human_confirmation() -> None:
    store = _store_with_accepted_requirement()
    store.requirement_assessments["assessment-1"]["risk_summary"] = {"risk_level": "high"}

    result = plan_accepted_requirement(
        store,
        requirement_id="req-1",
        assessment_id="assessment-1",
        actor_id="system",
    )

    assert result["status"] == "waiting_human"
    assert result["decision_request"]["plan_version"] == 0
    assert store.requirements["req-1"]["status"] == "approved"


def test_manual_grouping_rechecks_repository_backed_assessment_provenance() -> None:
    class Repository:
        def get_rd_policy_snapshot(self, snapshot_id: str) -> dict[str, object] | None:
            return snapshots.get(snapshot_id)

        def list_rd_collaboration_runs(self, *, product_version_id: str) -> list[dict[str, object]]:
            assert product_version_id == "version-planning"
            return []

        def list_requirement_assessments(self, requirement_id: str) -> list[dict[str, object]]:
            assert requirement_id == "req-1"
            return assessments

    snapshots: dict[str, dict[str, object]] = {
        "snapshot-1": {
            "id": "snapshot-1",
            "payload_json": {"delivery_target": "ready_for_release"},
            "policy_id": "policy-1",
            "policy_version": 1,
        }
    }
    assessments = [
        {
            "final_strategy_snapshot_id": "snapshot-1",
            "id": "assessment-1",
            "requirement_id": "req-1",
            "requirement_revision": 1,
            "status": "accepted",
        }
    ]
    store = MemoryStore()
    store.repository = Repository()
    store.requirements["req-1"] = {
        "assessment_revision": 1,
        "id": "req-1",
        "product_id": "product-1",
        "status": "approved",
    }
    store.product_versions["version-planning"] = {
        "id": "version-planning",
        "product_id": "product-1",
        "scope_version": 1,
        "status": "planning",
    }

    result = validate_manual_iteration_assignment(
        store,
        requirement_id="req-1",
        version_id="version-planning",
    )

    assert result["hard_eligible"] is True


def test_follow_up_requirement_rejects_supersedes_without_a_source_run() -> None:
    app.state.store.reset()
    headers = _headers()
    product = client.post(
        "/api/products",
        json={"code": "iteration-lineage", "name": "iteration-lineage"},
        headers=headers,
    ).json()["data"]

    response = client.post(
        "/api/requirements",
        json={
            "content": "后续需求内容",
            "product_id": product["id"],
            "supersedes_requirement_id": "requirement-original",
            "title": "后续需求",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "REQUIREMENT_LINEAGE_INVALID"


def test_follow_up_requirement_persists_same_product_ready_run_lineage() -> None:
    app.state.store.reset()
    headers = _headers()
    product = client.post(
        "/api/products",
        json={"code": "iteration-lineage-valid", "name": "iteration-lineage-valid"},
        headers=headers,
    ).json()["data"]
    app.state.store.product_versions["version-ready"] = {
        "id": "version-ready",
        "product_id": product["id"],
        "scope_version": 1,
        "status": "ready_for_release",
    }
    app.state.store.rd_collaboration_runs["run-ready"] = {
        "id": "run-ready",
        "product_id": product["id"],
        "product_version_id": "version-ready",
        "status": "completed",
    }
    app.state.store.requirements["requirement-original"] = {
        "id": "requirement-original",
        "product_id": product["id"],
        "status": "released",
    }

    response = client.post(
        "/api/requirements",
        json={
            "content": "后续需求内容",
            "product_id": product["id"],
            "source_collaboration_run_id": "run-ready",
            "supersedes_requirement_id": "requirement-original",
            "title": "后续需求",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        **response.json()["data"],
        "source_collaboration_run_id": "run-ready",
        "status": "submitted",
        "supersedes_requirement_id": "requirement-original",
    }
