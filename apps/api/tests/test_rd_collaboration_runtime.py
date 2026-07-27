from __future__ import annotations

import hashlib

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


def test_start_rejects_empty_active_policy_bindings_before_any_run_is_written() -> None:
    store = MemoryStore()
    store.product_versions["version-empty-seats"] = {
        "id": "version-empty-seats",
        "product_id": "product-empty-seats",
        "scope_version": 1,
        "status": "planning",
    }
    store.requirements["requirement-empty-seats"] = {
        "id": "requirement-empty-seats",
        "product_id": "product-empty-seats",
        "version_id": "version-empty-seats",
        "assessment_revision": 1,
        "status": "planned",
    }
    store.requirement_assessments["assessment-empty-seats"] = {
        "id": "assessment-empty-seats",
        "requirement_id": "requirement-empty-seats",
        "requirement_revision": 1,
        "final_strategy_snapshot_id": "snapshot-empty-seats",
        "status": "accepted",
    }
    store.rd_task_executor_policy_snapshots["snapshot-empty-seats"] = {
        "id": "snapshot-empty-seats",
        "policy_id": "policy-empty-seats",
        "policy_version": 1,
        "payload_json": {"role_bindings": []},
    }

    with pytest.raises(type(api_error(409, "RD_ROLE_ASSIGNMENT_REQUIRED", "invalid"))) as exc_info:
        start_collaboration_run(
            store,
            product_version_id="version-empty-seats",
            request_id="start:empty-seats",
            scope_version=1,
            actor={"id": "user-owner", "roles": ["rd_owner"]},
        )

    assert exc_info.value.detail["code"] == "RD_ROLE_ASSIGNMENT_REQUIRED"
    assert store.rd_collaboration_runs == {}
    assert store.rd_run_seats == {}
    assert store.product_versions["version-empty-seats"]["status"] == "planning"


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
    store.rd_role_definitions["role-developer"] = {
        "id": "role-developer",
        "brain_app_id": "rd_brain",
        "code": "developer",
        "status": "active",
        "assignable_subject_types": ["human_user"],
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
    assert [seat["role_code"] for seat in store.rd_run_seats.values()] == ["developer"]


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


def test_start_route_returns_versioned_snapshot_contract_and_trace_id(monkeypatch) -> None:
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
    generated_plan_calls: list[str] = []

    def generate_plan(current_store, *, collaboration_run_id: str) -> dict:
        assert current_store is app.state.store
        generated_plan_calls.append(collaboration_run_id)
        return {
            "status": "planned",
            **persist_work_item_plan(
                current_store,
                collaboration_run_id=collaboration_run_id,
                proposal={
                    "work_items": [
                        {
                            "id": "route-root",
                            "owner_role_code": "developer",
                            "reviewer_role_code": "tester",
                        }
                    ],
                    "dependencies": [],
                },
                actor={"id": "user_admin", "roles": ["rd_owner"]},
            ),
        }

    monkeypatch.setattr(
        "app.api.routers.rd_collaboration.generate_and_persist_work_item_plan",
        generate_plan,
    )
    planned = client.post(
        f"/api/delivery/rd-collaboration-runs/{run_id}/generate-plan",
        headers=headers,
    )
    assert planned.status_code == 200
    assert generated_plan_calls == [run_id]
    work_item = planned.json()["data"]["work_items"][0]
    assert work_item["status"] == "ready"
    claimed = client.post(
        f"/api/delivery/rd-work-items/{work_item['id']}/claim",
        json={"expected_version": 1, "lease_seconds": 60, "idempotency_key": "claim-route-root"},
        headers=headers,
    )
    assert claimed.status_code == 200
    assert claimed.json()["data"]["work_item"]["status"] == "running"


def test_start_route_rejects_empty_policy_bindings_without_creating_a_run() -> None:
    client = TestClient(app)
    app.state.store.reset()
    login = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    app.state.store.product_versions["version-route-empty-seats"] = {
        "id": "version-route-empty-seats",
        "product_id": "product-route-empty-seats",
        "scope_version": 1,
        "status": "planning",
    }
    app.state.store.requirements["requirement-route-empty-seats"] = {
        "id": "requirement-route-empty-seats",
        "product_id": "product-route-empty-seats",
        "version_id": "version-route-empty-seats",
        "assessment_revision": 1,
        "status": "planned",
    }
    app.state.store.requirement_assessments["assessment-route-empty-seats"] = {
        "id": "assessment-route-empty-seats",
        "requirement_id": "requirement-route-empty-seats",
        "requirement_revision": 1,
        "final_strategy_snapshot_id": "snapshot-route-empty-seats",
        "status": "accepted",
    }
    app.state.store.rd_task_executor_policy_snapshots["snapshot-route-empty-seats"] = {
        "id": "snapshot-route-empty-seats",
        "policy_id": "policy-route-empty-seats",
        "policy_version": 1,
        "payload_json": {"role_bindings": []},
    }

    response = client.post(
        "/api/product-versions/version-route-empty-seats/collaboration-runs",
        json={"request_id": "start:route-empty-seats", "scope_version": 1},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "RD_ROLE_ASSIGNMENT_REQUIRED"
    assert app.state.store.rd_collaboration_runs == {}
    assert app.state.store.rd_run_seats == {}
    assert app.state.store.product_versions["version-route-empty-seats"]["status"] == "planning"


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
    app.state.store.rd_git_deliveries = {"denied-delivery": {
        "id": "denied-delivery",
        "collaboration_run_id": "run-cross-product",
        "product_id": "product-denied",
        "work_item_id": "denied-work-item",
        "working_branch": "rd/run-cross-product/denied-work-item",
        "local_commit_sha": "must-not-leak",
    }}
    app.state.store.rd_work_items["denied-work-item"] = {
        "id": "denied-work-item",
        "collaboration_run_id": "run-cross-product",
        "status": "running",
    }
    app.state.store.rd_work_item_attempts["denied-attempt"] = {
        "id": "denied-attempt",
        "work_item_id": "denied-work-item",
        "status": "running",
        "lease_token_hash": "must-not-leak-attempt-token",
    }

    denied = client.get(
        "/api/delivery/rd-collaboration-runs/run-cross-product",
        headers=scoped_headers,
    )

    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "FORBIDDEN"
    assert "must-not-leak" not in denied.text

    denied_work_items = client.get(
        "/api/delivery/rd-collaboration-runs/run-cross-product/work-items",
        headers=scoped_headers,
    )

    assert denied_work_items.status_code == 403
    assert denied_work_items.json()["detail"]["code"] == "FORBIDDEN"
    assert "must-not-leak-attempt-token" not in denied_work_items.text


def test_work_item_list_projects_bounded_redacted_attempt_history() -> None:
    client = TestClient(app)
    app.state.store.reset()
    login = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    app.state.store.rd_collaboration_runs["run-attempt-summary"] = {
        "id": "run-attempt-summary",
        "product_id": "product-attempt-summary",
        "product_version_id": "version-attempt-summary",
        "status": "running",
    }
    app.state.store.rd_work_items.update(
        {
            "work-blocked": {
                "id": "work-blocked",
                "collaboration_run_id": "run-attempt-summary",
                "status": "blocked",
            },
            "work-running": {
                "id": "work-running",
                "collaboration_run_id": "run-attempt-summary",
                "status": "running",
            },
        }
    )
    app.state.store.rd_work_item_attempts.update(
        {
            "attempt-completed": {
                "id": "attempt-completed",
                "work_item_id": "work-running",
                "attempt_no": 1,
                "status": "failed",
                "lease_id": "secret-completed-lease",
                "lease_token_hash": "secret-completed-token",
                "executor_profile_id": "secret-completed-executor",
                "idempotency_key": "secret-completed-idempotency",
                "input_json": {"task_id": "ai-task-first", "secret": "secret-input"},
                "result_json": {"raw_payload": "secret-completed-output"},
                "failure_json": {
                    "error_code": "QUALITY_GATE_FAILED",
                    "error_message": "secret-error-message",
                },
                "rework_evidence": [{"comment": "secret-rework-comment"}],
                "started_at": "2026-07-27T01:00:00+00:00",
                "completed_at": "2026-07-27T01:01:00+00:00",
            },
            "attempt-running": {
                "id": "attempt-running",
                "work_item_id": "work-running",
                "attempt_no": 2,
                "status": "running",
                "executor_profile_id": "secret-executor-profile",
                "idempotency_key": "secret-idempotency-key",
                "lease_id": "secret-running-lease",
                "lease_token_hash": "secret-running-token",
                "input_json": {"task_id": "ai-task-second"},
                "started_at": "2026-07-27T01:02:00+00:00",
            },
        }
    )
    app.state.store.ai_tasks.update(
        {
            "ai-task-first": {
                "id": "ai-task-first",
                "product_id": "product-attempt-summary",
            },
            "ai-task-second": {
                "id": "ai-task-second",
                "product_id": "product-attempt-summary",
            },
            "ai-task-other-product": {
                "id": "ai-task-other-product",
                "product_id": "product-other",
            },
        }
    )
    app.state.store.ai_executor_tasks.update(
        {
            "runner-first": {
                "id": "runner-first",
                "ai_task_id": "ai-task-first",
                "task_kind": "coding",
                "status": "succeeded",
                "workspace_root": "/secret/worktrees/attempt-first",
                "request_config": {
                    "rd_work_item_attempt_id": "attempt-completed",
                    "authorization": "secret-runner-auth",
                },
                "result_json": {"secret": "secret-runner-result"},
            },
            "runner-second": {
                "id": "runner-second",
                "ai_task_id": "ai-task-second",
                "task_kind": "coding",
                "status": "running",
                "workspace_root": "/secret/worktrees/attempt-second",
                "request_config": {"rd_work_item_attempt_id": "attempt-running"},
            },
            "runner-verifier": {
                "id": "runner-verifier",
                "ai_task_id": "ai-task-first",
                "task_kind": "quality_gate",
                "status": "succeeded",
                "workspace_root": "/secret/verifier",
                "request_config": {"rd_work_item_attempt_id": "attempt-completed"},
            },
            "runner-other-product": {
                "id": "runner-other-product",
                "ai_task_id": "ai-task-other-product",
                "task_kind": "coding",
                "status": "succeeded",
                "workspace_root": "/secret/cross-product-worktree",
                "request_config": {
                    "rd_work_item_attempt_id": "attempt-completed",
                    "secret": "secret-cross-product-runner",
                },
            },
        }
    )
    app.state.store.rd_collaboration_events["fence-first"] = {
        "id": "fence-first",
        "collaboration_run_id": "run-attempt-summary",
        "event_type": "work_item.runner_result_fenced",
        "event_key": "work-item-runner-fenced:work-running:attempt-completed:runner-first",
        "subject_type": "rd_work_item",
        "subject_id": "work-running",
        "payload_json": {
            "attempt_id": "attempt-completed",
            "raw": "secret-fence-payload",
        },
    }

    response = client.get(
        "/api/delivery/rd-collaboration-runs/run-attempt-summary/work-items",
        headers=headers,
    )

    assert response.status_code == 200
    items = {
        item["id"]: item for item in response.json()["data"]["items"]
    }
    assert items["work-blocked"]["active_attempt_count"] == 0
    assert items["work-running"]["active_attempt_count"] == 1
    assert items["work-blocked"]["attempt_history"] == {
        "items": [],
        "total": 0,
        "truncated": False,
    }
    history = items["work-running"]["attempt_history"]
    assert history["total"] == 2
    assert history["truncated"] is False
    assert history["items"] == [
        {
            "ai_task_id": "ai-task-first",
            "attempt_no": 1,
            "completed_at": "2026-07-27T01:01:00+00:00",
            "failure_code": "QUALITY_GATE_FAILED",
            "fence_event_id": "fence-first",
            "late_result_fenced": True,
            "rework_evidence_count": 1,
            "runner_status": "succeeded",
            "runner_task_id": "runner-first",
            "started_at": "2026-07-27T01:00:00+00:00",
            "status": "failed",
            "workspace_fingerprint": (
                "sha256:"
                + hashlib.sha256(b"/secret/worktrees/attempt-first").hexdigest()
            ),
        },
        {
            "ai_task_id": "ai-task-second",
            "attempt_no": 2,
            "completed_at": None,
            "failure_code": None,
            "fence_event_id": None,
            "late_result_fenced": False,
            "rework_evidence_count": 0,
            "runner_status": "running",
            "runner_task_id": "runner-second",
            "started_at": "2026-07-27T01:02:00+00:00",
            "status": "running",
            "workspace_fingerprint": (
                "sha256:"
                + hashlib.sha256(b"/secret/worktrees/attempt-second").hexdigest()
            ),
        },
    ]
    assert set(history["items"][0]) == {
        "ai_task_id",
        "attempt_no",
        "completed_at",
        "failure_code",
        "fence_event_id",
        "late_result_fenced",
        "rework_evidence_count",
        "runner_status",
        "runner_task_id",
        "started_at",
        "status",
        "workspace_fingerprint",
    }
    for sensitive in (
        "attempt-completed",
        "attempt-running",
        "/secret/worktrees/attempt-first",
        "/secret/worktrees/attempt-second",
        "secret-completed-lease",
        "secret-completed-executor",
        "secret-completed-idempotency",
        "secret-completed-output",
        "secret-completed-token",
        "secret-cross-product-runner",
        "secret-error-message",
        "secret-executor-profile",
        "secret-fence-payload",
        "secret-idempotency-key",
        "secret-input",
        "secret-rework-comment",
        "secret-runner-auth",
        "secret-runner-result",
        "secret-running-lease",
        "secret-running-token",
    ):
        assert sensitive not in response.text


def test_work_item_attempt_history_is_latest_twenty_and_sanitizes_dirty_rows() -> None:
    client = TestClient(app)
    app.state.store.reset()
    login = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    app.state.store.rd_collaboration_runs["run-attempt-bounds"] = {
        "id": "run-attempt-bounds",
        "product_id": "product-attempt-bounds",
        "product_version_id": "version-attempt-bounds",
        "status": "running",
    }
    app.state.store.rd_work_items["work-attempt-bounds"] = {
        "id": "work-attempt-bounds",
        "collaboration_run_id": "run-attempt-bounds",
        "status": "running",
    }
    for attempt_no in range(1, 23):
        app.state.store.rd_work_item_attempts[f"dirty-attempt-{attempt_no}"] = {
            "id": f"dirty-attempt-{attempt_no}",
            "work_item_id": "work-attempt-bounds",
            "attempt_no": attempt_no,
            "status": "not-a-public-status" if attempt_no == 22 else "completed",
            "failure_json": {
                "error_code": (
                    "BAD CODE with spaces" if attempt_no == 22 else "SAFE_CODE"
                ),
            },
            "rework_evidence": "not-a-list" if attempt_no == 22 else [],
            "input_json": (
                {"task_id": "safe-looking-cross-product-task"}
                if attempt_no == 22
                else {}
            ),
            "started_at": "not-a-timestamp" if attempt_no == 22 else None,
            "completed_at": "x" * 500 if attempt_no == 22 else None,
            "secret": "must-never-leak-dirty-row",
        }
    app.state.store.ai_executor_tasks.update(
        {
            "ambiguous-runner-a": {
                "id": "ambiguous-runner-a",
                "ai_task_id": "ambiguous-task-a",
                "task_kind": "coding",
                "status": "succeeded",
                "workspace_root": "/must/not/select/a",
                "request_config": {
                    "rd_work_item_attempt_id": "dirty-attempt-21",
                },
            },
            "ambiguous-runner-b": {
                "id": "ambiguous-runner-b",
                "ai_task_id": "ambiguous-task-b",
                "task_kind": "coding",
                "status": "succeeded",
                "workspace_root": "/must/not/select/b",
                "request_config": {
                    "rd_work_item_attempt_id": "dirty-attempt-21",
                },
            },
        }
    )

    response = client.get(
        "/api/delivery/rd-collaboration-runs/run-attempt-bounds/work-items",
        headers=headers,
    )

    assert response.status_code == 200
    history = response.json()["data"]["items"][0]["attempt_history"]
    assert history["total"] == 22
    assert history["truncated"] is True
    assert [item["attempt_no"] for item in history["items"]] == list(range(3, 23))
    assert history["items"][-1]["status"] == "unknown"
    assert history["items"][-1]["failure_code"] is None
    assert history["items"][-1]["rework_evidence_count"] == 0
    assert history["items"][-1]["started_at"] is None
    assert history["items"][-1]["completed_at"] is None
    assert history["items"][-1]["ai_task_id"] is None
    assert history["items"][-2]["ai_task_id"] is None
    assert history["items"][-2]["runner_task_id"] is None
    assert history["items"][-2]["runner_status"] is None
    assert history["items"][-2]["workspace_fingerprint"] is None
    assert "must-never-leak-dirty-row" not in response.text
    assert "safe-looking-cross-product-task" not in response.text


def test_work_item_attempt_history_uses_repository_rows() -> None:
    class AttemptHistoryRepository:
        def get_rd_collaboration_run(self, run_id: str) -> dict[str, object] | None:
            if run_id != "run-repository-history":
                return None
            return {
                "id": run_id,
                "product_id": "product-repository-history",
                "status": "running",
            }

        def list_rd_work_items(self, run_id: str) -> list[dict[str, object]]:
            assert run_id == "run-repository-history"
            return [
                {
                    "id": "work-repository-history",
                    "collaboration_run_id": run_id,
                    "status": "completed",
                }
            ]

        def list_rd_work_item_attempts(
            self,
            work_item_id: str,
        ) -> list[dict[str, object]]:
            assert work_item_id == "work-repository-history"
            return [
                {
                    "id": "repository-attempt",
                    "work_item_id": work_item_id,
                    "attempt_no": 1,
                    "status": "completed",
                    "input_json": {"task_id": "repository-ai-task"},
                }
            ]

        def list_ai_executor_tasks(self, **filters: object) -> list[dict[str, object]]:
            assert filters == {
                "product_scope_ids": ["product-repository-history"],
            }
            return [
                {
                    "id": "repository-runner-task",
                    "ai_task_id": "repository-ai-task",
                    "task_kind": "coding",
                    "status": "succeeded",
                    "workspace_root": "/repository/secret/worktree",
                    "request_config": {
                        "rd_work_item_attempt_id": "repository-attempt",
                    },
                }
            ]

        def list_rd_collaboration_events(
            self,
            run_id: str,
        ) -> list[dict[str, object]]:
            assert run_id == "run-repository-history"
            return []

        def list_rd_work_item_dependencies(
            self,
            run_id: str,
        ) -> list[dict[str, object]]:
            assert run_id == "run-repository-history"
            return []

    client = TestClient(app)
    app.state.store.reset()
    login = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    original_repository = getattr(app.state.store, "repository", None)
    app.state.store.repository = AttemptHistoryRepository()
    try:
        response = client.get(
            "/api/delivery/rd-collaboration-runs/run-repository-history/work-items",
            headers=headers,
        )
    finally:
        app.state.store.repository = original_repository

    assert response.status_code == 200
    history = response.json()["data"]["items"][0]["attempt_history"]
    assert history["total"] == 1
    assert history["items"][0]["attempt_no"] == 1
    assert history["items"][0]["runner_task_id"] == "repository-runner-task"
    assert history["items"][0]["ai_task_id"] == "repository-ai-task"
    assert history["items"][0]["workspace_fingerprint"] == (
        "sha256:"
        + hashlib.sha256(b"/repository/secret/worktree").hexdigest()
    )
    assert "repository-attempt" not in response.text
    assert "/repository/secret/worktree" not in response.text


def test_collaboration_run_detail_hydrates_allowlisted_git_delivery_evidence() -> None:
    client = TestClient(app)
    app.state.store.reset()
    login = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    app.state.store.rd_collaboration_runs["run-with-delivery"] = {
        "id": "run-with-delivery",
        "product_id": "product-allowed",
        "product_version_id": "version-allowed",
        "status": "verifying",
    }
    app.state.store.rd_git_deliveries = {"delivery-allowed": {
        "id": "delivery-allowed",
        "collaboration_run_id": "run-with-delivery",
        "product_id": "product-allowed",
        "work_item_id": "work-item-allowed",
        "work_item_type": "implementation",
        "repository_id": "repository-allowed",
        "provider": "gitlab",
        "working_branch": "rd/run-with-delivery/work-item-allowed",
        "local_commit_sha": "local-sha",
        "outbox_event_id": "secret-outbox",
        "workspace_isolation": {"worktree_path": "/tmp/secret-worktree"},
        "created_at": "2026-07-26T00:00:00+00:00",
        "evidence_hash": "sha256:delivery",
    }}
    app.state.store.rd_git_delivery_reconciliations = {"reconciliation-allowed": {
        "id": "reconciliation-allowed",
        "delivery_id": "delivery-allowed",
        "collaboration_run_id": "run-with-delivery",
        "product_id": "product-allowed",
        "local_commit_sha": "local-sha",
        "remote_commit_sha": "local-sha",
        "status": "reconciled",
        "created_at": "2026-07-26T00:01:00+00:00",
        "evidence_hash": "sha256:reconciliation",
        "provider_callback_event_id": "secret-callback",
    }}

    response = client.get(
        "/api/delivery/rd-collaboration-runs/run-with-delivery",
        headers=headers,
    )

    assert response.status_code == 200
    deliveries = response.json()["data"]["git_deliveries"]
    assert deliveries["total"] == 1
    assert deliveries["items"][0]["reconciliation_status"] == "reconciled"
    assert deliveries["items"][0]["remote_commit_sha"] == "local-sha"
    assert "secret-outbox" not in response.text
    assert "secret-worktree" not in response.text
    assert "secret-callback" not in response.text


def test_decision_request_detail_route_returns_the_versioned_human_choice() -> None:
    client = TestClient(app)
    app.state.store.reset()
    login = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    app.state.store.decision_requests["decision-detail-route"] = {
        "id": "decision-detail-route",
        "options_json": [
            {"label": "继续协作", "code": "continue"},
            {"label": "停止并返工", "code": "rework"},
        ],
        "product_id": "product-route",
        "status": "pending",
        "subject_id": "run-route",
        "subject_type": "rd_collaboration_run",
        "version": 3,
    }

    response = client.get(
        "/api/delivery/decision-requests/decision-detail-route",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["version"] == 3
    assert response.json()["data"]["options_json"][0]["code"] == "continue"
