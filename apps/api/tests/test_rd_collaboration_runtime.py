from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import api_error
from app.core.store import MemoryStore
from app.main import app
from app.services.rd_collaboration_decisions import (
    answer_decision_request,
    apply_decision,
    expire_decision_requests,
)
from app.services.rd_collaboration_planning import (
    persist_work_item_plan,
    restart_terminal_collaboration_run,
    start_collaboration_run,
    validate_work_item_plan,
)
from app.services.rd_feedback_attribution import record_role_feedback
from app.services.rd_scope_changes import (
    apply_scope_change_decision,
    create_scope_change_request,
)


def test_plan_validation_rejects_cycles_before_any_work_item_is_persisted() -> None:
    plan = {
        "work_items": [
            {
                "id": "design",
                "owner_role_code": "developer",
                "reviewer_role_code": "tester",
            },
            {
                "id": "test",
                "owner_role_code": "tester",
                "reviewer_role_code": "developer",
            },
        ],
        "dependencies": [
            {"predecessor_work_item_id": "design", "successor_work_item_id": "test"},
            {"predecessor_work_item_id": "test", "successor_work_item_id": "design"},
        ],
    }

    with pytest.raises(type(api_error(422, "RD_PLAN_INVALID", "invalid"))) as exc_info:
        validate_work_item_plan(plan, available_role_codes={"developer", "tester"})

    assert exc_info.value.detail["code"] == "RD_PLAN_INVALID"
    assert exc_info.value.detail["reason"] == "dependency_cycle"


def _paused_run_store() -> MemoryStore:
    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "status": "waiting_human",
        "resume_state": "integrating",
        "suspended_decision_request_id": "decision-1",
        "suspended_at": "2026-07-18T00:00:00+00:00",
        "version": 4,
    }
    store.decision_requests["decision-1"] = {
        "id": "decision-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "subject_type": "rd_collaboration_run",
        "subject_id": "run-1",
        "status": "pending",
        "plan_version": 1,
        "version": 2,
        "options_json": [
            {
                "code": "continue",
                "outcome": "approve",
                "subject_transition": "resume",
                "input_schema": {},
            },
            {
                "code": "need_info",
                "outcome": "request_more_info",
                "subject_transition": "keep_paused",
                "requires_comment": True,
                "input_schema": {},
            },
        ],
        "answer_actor_selector": {"user_ids": ["user-owner"]},
        "answer_schema": {"type": "object", "additionalProperties": False},
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    return store


def test_decision_resume_uses_frozen_run_phase_and_clears_pause_fields() -> None:
    store = _paused_run_store()

    result = apply_decision(
        store,
        decision_request_id="decision-1",
        selected_option="continue",
        input_value={},
        comment=None,
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=2,
        idempotency_key="decision:decision-1:v2:continue",
    )

    assert result["run"]["status"] == "integrating"
    assert result["run"]["resume_state"] is None
    assert result["decision_request"]["status"] == "approved"


def test_answer_returns_decision_to_pending_without_resuming_subject() -> None:
    store = _paused_run_store()
    apply_decision(
        store,
        decision_request_id="decision-1",
        selected_option="need_info",
        input_value={},
        comment="需要补充证据",
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=2,
        idempotency_key="decision:decision-1:v2:more-info",
    )

    result = answer_decision_request(
        store,
        decision_request_id="decision-1",
        answer={},
        evidence=[{"kind": "log", "id": "evidence-1"}],
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=3,
        idempotency_key="answer:decision-1:v3",
    )

    assert result["decision_request"]["status"] == "pending"
    assert store.rd_collaboration_runs["run-1"]["status"] == "waiting_human"


def test_expiry_keeps_subject_paused_and_never_auto_approves() -> None:
    store = _paused_run_store()
    store.decision_requests["decision-1"]["expires_at"] = "2000-01-01T00:00:00+00:00"

    result = expire_decision_requests(store)

    assert result["expired_count"] == 1
    assert store.decision_requests["decision-1"]["status"] == "expired"
    assert store.rd_collaboration_runs["run-1"]["status"] == "waiting_human"
    assert all(item["status"] != "approved" for item in store.decision_requests.values())


def test_start_freezes_exact_accepted_requirement_scope_and_replays_request() -> None:
    store = MemoryStore()
    store.product_versions["version-1"] = {
        "id": "version-1",
        "product_id": "product-1",
        "scope_version": 3,
        "status": "planning",
    }
    store.requirements["requirement-1"] = {
        "id": "requirement-1",
        "product_id": "product-1",
        "version_id": "version-1",
        "assessment_revision": 1,
        "status": "planned",
        "acceptance_criteria": ["测试通过"],
    }
    store.requirement_assessments["assessment-1"] = {
        "id": "assessment-1",
        "requirement_id": "requirement-1",
        "requirement_revision": 1,
        "final_strategy_snapshot_id": "snapshot-1",
        "status": "accepted",
    }
    store.rd_task_executor_policy_snapshots["snapshot-1"] = {
        "id": "snapshot-1",
        "policy_id": "policy-1",
        "policy_version": 2,
        "payload_json": {
            "delivery_target": "ready_for_release",
            "role_bindings": [
                {
                    "role_code": "developer",
                    "actor_mode": "human",
                    "candidate_human_user_ids": ["user-owner"],
                    "status": "active",
                }
            ],
        },
    }

    first = start_collaboration_run(
        store,
        product_version_id="version-1",
        request_id="start:version-1:3",
        scope_version=3,
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        reason="启动研发协作",
    )
    replay = start_collaboration_run(
        store,
        product_version_id="version-1",
        request_id="start:version-1:3",
        scope_version=3,
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        reason="启动研发协作",
    )

    assert first["run"]["scope_version"] == 3
    assert first["run"]["strategy_snapshot_kind"] == "version_resolved"
    assert first["strategy_source_count"] == 1
    assert replay["run"]["id"] == first["run"]["id"]
    assert replay["idempotent_replay"] is True
    assert store.product_versions["version-1"]["status"] == "active"
    assert [seat["role_code"] for seat in store.rd_run_seats.values()] == ["developer"]
    assert next(iter(store.rd_run_seats.values()))["human_user_id"] == "user-owner"


def test_start_requires_planning_version_and_never_reuses_terminal_generation() -> None:
    store = MemoryStore()
    store.product_versions["version-1"] = {
        "id": "version-1",
        "product_id": "product-1",
        "scope_version": 1,
        "status": "active",
    }
    store.rd_collaboration_runs["terminal-run"] = {
        "id": "terminal-run",
        "product_version_id": "version-1",
        "status": "cancelled",
        "run_generation": 4,
    }

    with pytest.raises(type(api_error(409, "RD_RUN_RESTART_REQUIRED", "invalid"))) as exc_info:
        start_collaboration_run(
            store,
            product_version_id="version-1",
            request_id="new-start",
            scope_version=1,
            actor={"id": "user-owner", "roles": ["rd_owner"]},
        )

    assert exc_info.value.detail["code"] == "RD_RUN_RESTART_REQUIRED"


def test_approved_scope_change_fences_old_run_and_increments_scope_once() -> None:
    store = MemoryStore()
    store.product_versions["version-1"] = {
        "id": "version-1",
        "product_id": "product-1",
        "scope_version": 3,
        "status": "active",
    }
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "product_version_id": "version-1",
        "run_generation": 1,
        "status": "running",
        "version": 2,
    }
    store.requirements["requirement-2"] = {
        "id": "requirement-2",
        "product_id": "product-1",
        "status": "approved",
    }
    store.requirement_assessments["assessment-2"] = {
        "id": "assessment-2",
        "requirement_id": "requirement-2",
        "requirement_revision": 1,
        "final_strategy_snapshot_id": "snapshot-2",
        "status": "accepted",
    }
    store.rd_work_items["work-1"] = {
        "id": "work-1",
        "collaboration_run_id": "run-1",
        "status": "running",
        "version": 1,
    }

    pending = create_scope_change_request(
        store,
        product_version_id="version-1",
        request_id="scope:version-1:4",
        expected_scope_version=3,
        expected_run_generation=1,
        source_run_id="run-1",
        reason="增加整改需求",
        operations=[
            {
                "op": "add_requirement",
                "requirement_id": "requirement-2",
                "requirement_revision": 1,
                "assessment_id": "assessment-2",
                "final_strategy_snapshot_id": "snapshot-2",
            }
        ],
        actor={"id": "user-owner", "roles": ["rd_owner"]},
    )
    applied = apply_scope_change_decision(
        store,
        scope_change_request_id=pending["scope_change_request"]["id"],
        decision="approve_apply_and_restart",
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=1,
        idempotency_key="decision:scope:approve",
    )
    replay = apply_scope_change_decision(
        store,
        scope_change_request_id=pending["scope_change_request"]["id"],
        decision="approve_apply_and_restart",
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=1,
        idempotency_key="decision:scope:approve",
    )

    assert applied["run"]["status"] == "cancelled"
    assert applied["scope_change_request"]["applied_scope_version"] == 4
    assert store.product_versions["version-1"]["scope_version"] == 4
    assert store.rd_work_items["work-1"]["status"] == "cancelled"
    assert replay["idempotent_replay"] is True


def test_replacement_scope_provenance_is_used_by_the_restarted_generation() -> None:
    store = MemoryStore()
    store.product_versions["version-replace"] = {
        "id": "version-replace",
        "product_id": "product-replace",
        "scope_version": 1,
        "status": "active",
    }
    store.rd_collaboration_runs["run-replace"] = {
        "id": "run-replace",
        "brain_app_id": "rd_brain",
        "product_id": "product-replace",
        "product_version_id": "version-replace",
        "strategy_snapshot_id": "snapshot-original",
        "run_generation": 1,
        "scope_version": 1,
        "status": "running",
        "version": 1,
    }
    store.requirements["requirement-replace"] = {
        "id": "requirement-replace",
        "product_id": "product-replace",
        "version_id": "version-replace",
        "assessment_revision": 1,
        "status": "planned",
    }
    for assessment_id, snapshot_id in (
        ("assessment-original", "snapshot-original"),
        ("assessment-replacement", "snapshot-replacement"),
    ):
        store.requirement_assessments[assessment_id] = {
            "id": assessment_id,
            "requirement_id": "requirement-replace",
            "requirement_revision": 1,
            "final_strategy_snapshot_id": snapshot_id,
            "status": "accepted",
        }
    for snapshot_id in ("snapshot-original", "snapshot-replacement"):
        store.rd_task_executor_policy_snapshots[snapshot_id] = {
            "id": snapshot_id,
            "policy_id": "policy-replace",
            "policy_version": 1,
            "payload_json": {"delivery_target": "ready_for_release"},
        }

    scope = create_scope_change_request(
        store,
        product_version_id="version-replace",
        request_id="replace-scope",
        expected_scope_version=1,
        expected_run_generation=1,
        source_run_id="run-replace",
        reason="replace accepted assessment",
        operations=[
            {
                "op": "replace_requirement_snapshot",
                "requirement_id": "requirement-replace",
                "requirement_revision": 1,
                "assessment_id": "assessment-replacement",
                "final_strategy_snapshot_id": "snapshot-replacement",
            }
        ],
        actor={"id": "user-owner", "roles": ["rd_owner"]},
    )
    apply_scope_change_decision(
        store,
        scope_change_request_id=scope["scope_change_request"]["id"],
        decision="approve_apply_and_restart",
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=1,
        idempotency_key="approve-replacement",
    )

    restarted = restart_terminal_collaboration_run(
        store,
        product_version_id="version-replace",
        terminal_run_id="run-replace",
        request_id="restart-replacement",
        scope_version=2,
        actor={"id": "user-owner", "roles": ["rd_owner"]},
    )

    scope_row = next(iter(store.rd_collaboration_run_requirements.values()))
    assert restarted["run"]["supersedes_run_id"] == "run-replace"
    assert scope_row["collaboration_run_id"] == restarted["run"]["id"]
    assert scope_row["assessment_id"] == "assessment-replacement"
    assert scope_row["final_strategy_snapshot_id"] == "snapshot-replacement"


def test_feedback_keeps_producer_seat_attribution_distinct_from_executor() -> None:
    store = MemoryStore()
    feedback = record_role_feedback(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
        source_event_id="event-review-1",
        outcome="accepted",
        producer={
            "subject_type": "human_user",
            "subject_id": "user-reviewer",
            "role_code": "tester",
            "seat_id": "seat-reviewer",
        },
        executor_profile_id="executor-codex",
        actor_id="user-reviewer",
    )

    assert feedback["producer_subject_id"] == "user-reviewer"
    assert feedback["producer_seat_id"] == "seat-reviewer"
    assert feedback["executor_profile_id"] == "executor-codex"


def test_persisted_plan_binds_work_items_to_frozen_role_seats() -> None:
    store = MemoryStore()
    store.rd_collaboration_runs["run-plan"] = {
        "id": "run-plan",
        "status": "planning",
        "plan_version": 0,
        "version": 1,
    }
    store.rd_run_seats.update(
        {
            "seat-dev": {
                "id": "seat-dev",
                "collaboration_run_id": "run-plan",
                "role_code": "developer",
                "status": "active",
                "capacity": 1,
            },
            "seat-test": {
                "id": "seat-test",
                "collaboration_run_id": "run-plan",
                "role_code": "tester",
                "status": "active",
                "capacity": 1,
            },
        }
    )

    result = persist_work_item_plan(
        store,
        collaboration_run_id="run-plan",
        proposal={
            "work_items": [
                {
                    "id": "design",
                    "title": "设计",
                    "objective": "输出设计",
                    "owner_role_code": "developer",
                    "reviewer_role_code": "tester",
                }
            ],
            "dependencies": [],
        },
        actor={"id": "user-owner", "roles": ["rd_owner"]},
    )

    assert result["plan_version"] == 1
    assert result["work_items"][0]["owner_seat_id"] == "seat-dev"
    assert result["work_items"][0]["reviewer_seat_id"] == "seat-test"


def test_start_route_returns_versioned_snapshot_contract_and_trace_id() -> None:
    client = TestClient(app)
    app.state.store.reset()
    login = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    app.state.store.product_versions["version-route"] = {
        "id": "version-route",
        "product_id": "product-route",
        "scope_version": 1,
        "status": "planning",
    }
    app.state.store.requirements["requirement-route"] = {
        "id": "requirement-route",
        "product_id": "product-route",
        "version_id": "version-route",
        "assessment_revision": 1,
        "status": "planned",
    }
    app.state.store.requirement_assessments["assessment-route"] = {
        "id": "assessment-route",
        "requirement_id": "requirement-route",
        "requirement_revision": 1,
        "final_strategy_snapshot_id": "snapshot-route",
        "status": "accepted",
    }
    app.state.store.rd_task_executor_policy_snapshots["snapshot-route"] = {
        "id": "snapshot-route",
        "policy_id": "policy-route",
        "policy_version": 1,
        "payload_json": {
            "delivery_target": "ready_for_release",
            "role_bindings": [
                {
                    "role_code": "developer",
                    "actor_mode": "human",
                    "candidate_human_user_ids": ["user_admin"],
                    "status": "active",
                },
                {
                    "role_code": "tester",
                    "actor_mode": "human",
                    "candidate_human_user_ids": ["user_admin"],
                    "status": "active",
                },
            ],
        },
    }

    response = client.post(
        "/api/product-versions/version-route/collaboration-runs",
        json={"request_id": "start:route", "scope_version": 1, "reason": "route test"},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["strategy_snapshot_kind"] == "version_resolved"
    assert response.json()["trace_id"]
    run_id = response.json()["data"]["id"]
    planned = client.post(
        f"/api/delivery/rd-collaboration-runs/{run_id}/plan",
        json={
            "work_items": [
                {
                    "id": "route-root",
                    "owner_role_code": "developer",
                    "reviewer_role_code": "tester",
                }
            ],
            "dependencies": [],
        },
        headers=headers,
    )
    assert planned.status_code == 200
    work_item = planned.json()["data"]["work_items"][0]
    assert work_item["status"] == "ready"
    claimed = client.post(
        f"/api/delivery/rd-work-items/{work_item['id']}/claim",
        json={"expected_version": 1, "lease_seconds": 60, "idempotency_key": "claim-route-root"},
        headers=headers,
    )
    assert claimed.status_code == 200
    assert claimed.json()["data"]["work_item"]["status"] == "running"


def test_collaboration_routes_enforce_aggregate_product_scope() -> None:
    client = TestClient(app)
    app.state.store.reset()
    admin = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin.json()['data']['access_token']}"}
    created = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "username": "collaboration-scope@example.com",
            "password": "scope123",
            "display_name": "Scoped developer",
            "roles": ["developer"],
        },
    ).json()["data"]
    client.put(
        f"/api/users/{created['id']}/scopes",
        headers=admin_headers,
        json={
            "scopes": [
                {"scope_type": "product", "scope_id": "product-allowed", "access_level": "write"}
            ]
        },
    )
    scoped_login = client.post(
        "/api/auth/login",
        json={"username": "collaboration-scope@example.com", "password": "scope123"},
    )
    scoped_headers = {"Authorization": f"Bearer {scoped_login.json()['data']['access_token']}"}
    app.state.store.rd_collaboration_runs["run-cross-product"] = {
        "id": "run-cross-product",
        "product_id": "product-denied",
        "product_version_id": "version-denied",
        "status": "running",
    }

    denied = client.get(
        "/api/delivery/rd-collaboration-runs/run-cross-product",
        headers=scoped_headers,
    )

    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "FORBIDDEN"
