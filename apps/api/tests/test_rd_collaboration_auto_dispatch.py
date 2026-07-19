from __future__ import annotations

from app.core.store import MemoryStore
from app.services.rd_collaboration_auto_dispatch import dispatch_ready_ai_work_items
from app.services.rd_collaboration_decisions import apply_decision


def _store_with_ready_ai_work_items() -> MemoryStore:
    store = MemoryStore()
    store.products["product-1"] = {
        "id": "product-1",
        "code": "PRODUCT-1",
        "name": "自动派发测试产品",
        "status": "active",
    }
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "product_id": "product-1",
        "product_version_id": "version-1",
        "status": "running",
        "strategy_snapshot_id": "snapshot-1",
        "created_by": "user-owner",
    }
    store.requirements["requirement-1"] = {
        "id": "requirement-1",
        "product_id": "product-1",
        "version_id": "version-1",
        "task_ids": [],
    }
    store.rd_task_executor_policy_snapshots["snapshot-1"] = {
        "id": "snapshot-1",
        "policy_id": "policy-1",
        "policy_version": 1,
        "payload_json": {
            "autonomy_config": {"mode": "single_pass"},
            "git_config": {"workspace_root": "/tmp/rd-collaboration"},
            "quality_gate_config": {"code_change_review_mode": "manual_review"},
        },
    }
    store.rd_run_seats["seat-developer"] = {
        "id": "seat-developer",
        "collaboration_run_id": "run-1",
        "role_code": "developer",
        "subject_type": "ai_employee",
        "ai_employee_id": "employee-developer",
        "executor_profile_id": "executor-codex",
        "capacity": 2,
        "status": "active",
    }
    store.rd_run_seats["seat-reviewer"] = {
        "id": "seat-reviewer",
        "collaboration_run_id": "run-1",
        "role_code": "tester",
        "subject_type": "human_user",
        "human_user_id": "user-tester",
        "status": "active",
    }
    store.rd_executor_profiles["executor-codex"] = {
        "id": "executor-codex",
        "executor_type": "codex",
        "runner_id": "runner-codex",
        "status": "active",
    }
    store.ai_executor_runners["runner-codex"] = {
        "id": "runner-codex",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/rd-collaboration"],
    }
    store.rd_work_items.update(
        {
            "work-low": {
                "id": "work-low",
                "collaboration_run_id": "run-1",
                "requirement_id": "requirement-1",
                "work_item_type": "implementation",
                "title": "低风险开发工作项",
                "owner_seat_id": "seat-developer",
                "reviewer_seat_id": "seat-reviewer",
                "status": "ready",
                "risk_level": "low",
                "version": 1,
            },
            "work-high": {
                "id": "work-high",
                "collaboration_run_id": "run-1",
                "requirement_id": "requirement-1",
                "work_item_type": "implementation",
                "title": "高风险开发工作项",
                "owner_seat_id": "seat-developer",
                "reviewer_seat_id": "seat-reviewer",
                "status": "ready",
                "risk_level": "high",
                "version": 1,
            },
            "work-medium": {
                "id": "work-medium",
                "collaboration_run_id": "run-1",
                "requirement_id": "requirement-1",
                "work_item_type": "implementation",
                "title": "中风险开发工作项",
                "owner_seat_id": "seat-developer",
                "reviewer_seat_id": "seat-reviewer",
                "status": "ready",
                "risk_level": "medium",
                "version": 1,
            },
        }
    )
    return store


def test_auto_dispatches_ready_non_high_risk_ai_work_items() -> None:
    store = _store_with_ready_ai_work_items()

    result = dispatch_ready_ai_work_items(store)

    assert result == {
        "capacity_deferred_work_item_ids": [],
        "dispatched_work_item_ids": ["work-low", "work-medium"],
        "human_review_required_work_item_ids": ["work-high"],
        "skipped_work_item_ids": [],
    }
    assert store.rd_work_items["work-low"]["status"] == "running"
    assert store.rd_work_items["work-medium"]["status"] == "running"
    high_work_item = store.rd_work_items["work-high"]
    assert high_work_item["status"] == "waiting_human"
    assert high_work_item["resume_state"] == "ready"
    assert high_work_item["suspended_decision_request_id"] == "auto-high-risk-dispatch:work-high:1"
    decision = store.decision_requests["auto-high-risk-dispatch:work-high:1"]
    assert decision | {
        "answer_actor_selector": {},
        "brain_app_id": "rd_brain",
        "created_by": "user-owner",
        "decision_actor_selector": {"seat_ids": ["seat-reviewer"]},
        "decision_type": "high_risk_ai_dispatch",
        "escalation_target_selector": {"seat_ids": ["seat-reviewer"]},
        "options_json": [
            {
                "code": "approve_dispatch",
                "input_schema": {},
                "outcome": "approve",
                "subject_transition": "ready",
            },
            {
                "code": "cancel_work_item",
                "input_schema": {},
                "outcome": "reject",
                "requires_comment": True,
                "subject_transition": "cancelled",
            },
        ],
        "plan_version": 0,
        "product_id": "product-1",
        "recommendation_json": {"action": "human_approval_required"},
        "status": "pending",
        "subject_id": "work-high",
        "subject_type": "rd_work_item",
        "timeout_policy": "escalate_keep_paused",
        "version": 1,
    } == decision
    assert decision["expires_at"]
    assert len(store.ai_executor_tasks) == 2


def test_auto_dispatch_does_not_create_a_second_high_risk_decision_for_a_paused_item() -> None:
    store = _store_with_ready_ai_work_items()

    dispatch_ready_ai_work_items(store)
    result = dispatch_ready_ai_work_items(store)

    assert result == {
        "capacity_deferred_work_item_ids": [],
        "dispatched_work_item_ids": [],
        "human_review_required_work_item_ids": [],
        "skipped_work_item_ids": [],
    }
    assert list(store.decision_requests) == ["auto-high-risk-dispatch:work-high:1"]


def test_auto_dispatch_starts_a_high_risk_item_only_after_the_assigned_human_approves() -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_run_seats["seat-developer"]["capacity"] = 3
    dispatch_ready_ai_work_items(store)
    decision = store.decision_requests["auto-high-risk-dispatch:work-high:1"]

    apply_decision(
        store,
        decision_request_id=decision["id"],
        selected_option="approve_dispatch",
        input_value={},
        comment=None,
        actor={"id": "user-tester", "roles": []},
        version=1,
        idempotency_key="human-approved-high-risk-dispatch",
    )
    result = dispatch_ready_ai_work_items(store)

    assert result == {
        "capacity_deferred_work_item_ids": [],
        "dispatched_work_item_ids": ["work-high"],
        "human_review_required_work_item_ids": [],
        "skipped_work_item_ids": [],
    }
    assert store.rd_work_items["work-high"]["status"] == "running"


def test_auto_dispatch_never_dispatches_when_the_run_is_waiting_for_human_decision() -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_collaboration_runs["run-1"]["status"] = "waiting_human"

    result = dispatch_ready_ai_work_items(store)

    assert result == {
        "capacity_deferred_work_item_ids": [],
        "dispatched_work_item_ids": [],
        "human_review_required_work_item_ids": [],
        "skipped_work_item_ids": [],
    }
    assert store.rd_work_items["work-low"]["status"] == "ready"
    assert store.ai_executor_tasks == {}


def test_auto_dispatch_defers_ready_ai_work_when_the_frozen_seat_is_full() -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_run_seats["seat-developer"]["capacity"] = 1

    result = dispatch_ready_ai_work_items(store)

    assert result == {
        "capacity_deferred_work_item_ids": ["work-medium"],
        "dispatched_work_item_ids": ["work-low"],
        "human_review_required_work_item_ids": ["work-high"],
        "skipped_work_item_ids": [],
    }
    assert store.rd_work_items["work-low"]["status"] == "running"
    assert store.rd_work_items["work-medium"]["status"] == "ready"
