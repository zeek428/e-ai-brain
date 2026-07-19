from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

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
        "escalated_work_item_ids": [],
        "human_review_required_work_item_ids": ["work-high"],
        "retryable_work_item_ids": [],
        "skipped_work_item_ids": [],
    }
    assert store.rd_work_items["work-low"]["status"] == "running"
    assert store.rd_work_items["work-medium"]["status"] == "running"
    high_work_item = store.rd_work_items["work-high"]
    assert high_work_item["status"] == "waiting_human"
    assert high_work_item["resume_state"] == "ready"
    assert high_work_item["suspended_decision_request_id"] == "auto-high-risk-dispatch:work-high:1"
    decision = store.decision_requests["auto-high-risk-dispatch:work-high:1"]
    assert (
        decision
        | {
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
        }
        == decision
    )
    assert decision["expires_at"]
    assert len(store.ai_executor_tasks) == 2


def test_auto_dispatch_does_not_create_a_second_high_risk_decision_for_a_paused_item() -> None:
    store = _store_with_ready_ai_work_items()

    dispatch_ready_ai_work_items(store)
    result = dispatch_ready_ai_work_items(store)

    assert result == {
        "capacity_deferred_work_item_ids": [],
        "dispatched_work_item_ids": [],
        "escalated_work_item_ids": [],
        "human_review_required_work_item_ids": [],
        "retryable_work_item_ids": [],
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
        "escalated_work_item_ids": [],
        "human_review_required_work_item_ids": [],
        "retryable_work_item_ids": [],
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
        "escalated_work_item_ids": [],
        "human_review_required_work_item_ids": [],
        "retryable_work_item_ids": [],
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
        "escalated_work_item_ids": [],
        "human_review_required_work_item_ids": ["work-high"],
        "retryable_work_item_ids": [],
        "skipped_work_item_ids": [],
    }
    assert store.rd_work_items["work-low"]["status"] == "running"
    assert store.rd_work_items["work-medium"]["status"] == "ready"


def test_auto_dispatch_limit_counts_dispatch_decision_and_deferred_outcomes() -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_run_seats["seat-developer"]["capacity"] = 1
    store.rd_work_items["work-low"]["priority"] = 10
    store.rd_work_items["work-high"]["priority"] = 20
    store.rd_work_items["work-medium"]["priority"] = 30

    result = dispatch_ready_ai_work_items(store, limit=2)

    assert result["dispatched_work_item_ids"] == ["work-low"]
    assert result["human_review_required_work_item_ids"] == ["work-high"]
    assert result["capacity_deferred_work_item_ids"] == []
    assert (
        len(result["dispatched_work_item_ids"])
        + len(result["capacity_deferred_work_item_ids"])
        + len(result["escalated_work_item_ids"])
        + len(result["human_review_required_work_item_ids"])
        + len(result["retryable_work_item_ids"])
    ) == 2


def test_auto_dispatch_escalates_a_frozen_runner_safety_fault_without_leaking_paths() -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}
    secret_workspace = "/tmp/rd-collaboration/customer-secret-token"
    store.rd_task_executor_policy_snapshots["snapshot-1"]["payload_json"]["git_config"] = {
        "workspace_root": secret_workspace
    }
    store.ai_executor_runners["runner-codex"]["workspace_roots"] = ["/srv/approved"]

    result = dispatch_ready_ai_work_items(store)

    assert result["escalated_work_item_ids"] == ["work-low"]
    assert result["retryable_work_item_ids"] == []
    paused = store.rd_work_items["work-low"]
    assert paused["status"] == "waiting_human"
    assert paused["resume_state"] == "ready"
    decision = store.decision_requests[paused["suspended_decision_request_id"]]
    assert decision["decision_type"] == "dispatch_fault_resolution"
    assert [option["code"] for option in decision["options_json"]] == [
        "retry_after_configuration_repair",
        "cancel_work_item",
    ]
    assert decision["evidence_json"] == [
        {
            "error_code": "AI_EXECUTOR_WORKSPACE_NOT_ALLOWED",
            "kind": "dispatch_fault",
            "message": "Frozen runner safety configuration rejected the dispatch",
        }
    ]
    persisted_fault_records = json.dumps(
        {
            "audit": store.audit_events,
            "decision": decision,
            "events": store.rd_collaboration_events,
        },
        ensure_ascii=False,
    )
    assert secret_workspace not in persisted_fault_records

    dispatch_ready_ai_work_items(store)
    assert len(store.decision_requests) == 1


def test_auto_dispatch_runner_safety_approval_resumes_exact_phase_and_dispatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}
    store.rd_work_items["work-low"]["status"] = "rework_required"
    secret = "customer-token=secret-value /tmp/private-workspace"
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: f"Run git push, then rm -rf build. {secret}",
    )

    blocked = dispatch_ready_ai_work_items(store)

    assert blocked["escalated_work_item_ids"] == ["work-low"]
    paused = store.rd_work_items["work-low"]
    assert paused["status"] == "waiting_human"
    assert paused["resume_state"] == "rework_required"
    approval_request_id = "rd-runner-safety:work-low:attempt:1"
    assert list(store.ai_executor_approval_requests) == [approval_request_id]
    approval_request = store.ai_executor_approval_requests[approval_request_id]
    assert approval_request["status"] == "pending"
    assert approval_request["blocked_operations"] == [
        "git_push_or_merge",
        "destructive_delete",
    ]
    assert approval_request["workspace_root"] == ""
    decision = store.decision_requests[paused["suspended_decision_request_id"]]
    assert len(store.decision_requests) == 1
    assert len(store.rd_collaboration_events) == 1
    assert len(store.audit_events) == 1
    assert decision["decision_type"] == "runner_safety_approval"
    assert [option["code"] for option in decision["options_json"]] == [
        "authorize_blocked_operations",
        "cancel_work_item",
    ]
    assert store.ai_tasks == {}
    assert store.ai_executor_tasks == {}
    assert store.rd_work_item_attempts == {}
    persisted_gate = json.dumps(
        {
            "approval_request": approval_request,
            "decision": decision,
            "events": store.rd_collaboration_events,
            "audits": store.audit_events,
            "worker_outcome": blocked,
        },
        ensure_ascii=False,
    )
    assert secret not in persisted_gate
    assert "/tmp/private-workspace" not in persisted_gate

    replay = dispatch_ready_ai_work_items(store)
    assert replay["escalated_work_item_ids"] == []
    assert list(store.ai_executor_approval_requests) == [approval_request_id]
    assert len(store.decision_requests) == 1

    frozen_strategy = json.dumps(store.rd_task_executor_policy_snapshots, sort_keys=True)
    decided = apply_decision(
        store,
        decision_request_id=decision["id"],
        selected_option="authorize_blocked_operations",
        input_value={},
        comment=None,
        actor={"id": "user-tester", "roles": []},
        version=1,
        idempotency_key="approve-runner-safety-work-low-attempt-1",
    )

    assert decided["work_item"]["status"] == "rework_required"
    approved_request = store.ai_executor_approval_requests[approval_request_id]
    approval = approved_request["approval"]
    assert approved_request["status"] == "approved"
    assert approval == {
        "approval_id": f"{approval_request_id}:approval",
        "approval_request_id": approval_request_id,
        "approved": True,
        "approved_at": approval["approved_at"],
        "approved_by": "user-tester",
        "approved_operations": ["git_push_or_merge", "destructive_delete"],
        "expires_at": approval["expires_at"],
        "mode": "platform_human_approval",
        "policy_version": "runner_safety_v1",
    }
    assert json.dumps(store.rd_task_executor_policy_snapshots, sort_keys=True) == frozen_strategy

    dispatched = dispatch_ready_ai_work_items(store)

    assert dispatched["dispatched_work_item_ids"] == ["work-low"]
    assert store.rd_work_items["work-low"]["status"] == "running"
    assert len(store.rd_work_item_attempts) == 1
    runner_task = next(iter(store.ai_executor_tasks.values()))
    assert runner_task["request_config"]["ai_executor_approval"] == approval
    assert runner_task["request_config"]["ai_executor_safety"]["status"] == "approved"


def test_auto_dispatch_runner_safety_rejection_cancels_without_execution_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: "Run git push",
    )
    dispatch_ready_ai_work_items(store)
    decision = next(iter(store.decision_requests.values()))

    decided = apply_decision(
        store,
        decision_request_id=decision["id"],
        selected_option="cancel_work_item",
        input_value={},
        comment="Unsafe operation is not authorized",
        actor={"id": "user-tester", "roles": []},
        version=1,
        idempotency_key="reject-runner-safety-work-low-attempt-1",
    )

    approval_request = store.ai_executor_approval_requests["rd-runner-safety:work-low:attempt:1"]
    assert approval_request["status"] == "rejected"
    assert approval_request["approval"] == {}
    assert decided["work_item"]["status"] == "cancelled"
    assert store.ai_tasks == {}
    assert store.ai_executor_tasks == {}
    assert store.rd_work_item_attempts == {}


@pytest.mark.parametrize(
    ("fault_kind", "expected_code"),
    [
        ("inactive_role", "RD_ROLE_ASSIGNMENT_REQUIRED"),
        ("role", "RD_ROLE_ASSIGNMENT_REQUIRED"),
        ("snapshot", "RD_ROLE_ASSIGNMENT_REQUIRED"),
        ("configuration", "RD_EXECUTION_POLICY_REQUIRED"),
    ],
)
def test_auto_dispatch_escalates_frozen_dispatch_configuration_faults(
    fault_kind: str,
    expected_code: str,
) -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}
    if fault_kind == "inactive_role":
        store.rd_run_seats["seat-developer"]["status"] = "disabled"
    elif fault_kind == "role":
        store.rd_executor_profiles["executor-codex"]["status"] = "disabled"
    elif fault_kind == "snapshot":
        store.rd_task_executor_policy_snapshots.clear()
    else:
        store.rd_task_executor_policy_snapshots["snapshot-1"]["payload_json"]["git_config"] = {}

    result = dispatch_ready_ai_work_items(store)

    assert result["escalated_work_item_ids"] == ["work-low"]
    paused = store.rd_work_items["work-low"]
    decision = store.decision_requests[paused["suspended_decision_request_id"]]
    assert decision["evidence_json"][0]["error_code"] == expected_code


def test_auto_dispatch_preserves_rework_as_the_frozen_fault_resume_state() -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}
    store.rd_work_items["work-low"]["status"] = "rework_required"
    store.rd_executor_profiles["executor-codex"]["status"] = "disabled"

    dispatch_ready_ai_work_items(store)

    assert store.rd_work_items["work-low"]["status"] == "waiting_human"
    assert store.rd_work_items["work-low"]["resume_state"] == "rework_required"


def test_auto_dispatch_classifies_stale_dispatch_reads_as_retryable(monkeypatch) -> None:
    from app.services import rd_collaboration_auto_dispatch

    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}

    def stale_dispatch(*_args, **_kwargs):
        raise HTTPException(
            status_code=409,
            detail={"code": "RD_WORK_ITEM_NOT_READY", "message": "stale"},
        )

    monkeypatch.setattr(
        rd_collaboration_auto_dispatch,
        "dispatch_ai_task_for_work_item",
        stale_dispatch,
    )

    result = dispatch_ready_ai_work_items(store)

    assert result["retryable_work_item_ids"] == ["work-low"]
    assert result["escalated_work_item_ids"] == []
    assert store.rd_work_items["work-low"]["status"] == "ready"
    assert store.decision_requests == {}


def test_auto_dispatch_persists_safe_retry_backoff_and_suppresses_early_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import rd_collaboration_auto_dispatch

    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}
    attempted: list[str] = []
    secret = "token=customer-secret /tmp/private-workspace prompt=do-not-store"

    def retryable_dispatch(*_args, **_kwargs):
        attempted.append("work-low")
        raise HTTPException(
            status_code=503,
            detail={"code": "UPSTREAM_TIMEOUT", "message": secret},
        )

    monkeypatch.setattr(
        rd_collaboration_auto_dispatch,
        "dispatch_ai_task_for_work_item",
        retryable_dispatch,
    )
    observed_at = datetime.now(UTC).replace(microsecond=0)

    first = dispatch_ready_ai_work_items(store, now=observed_at)
    early = dispatch_ready_ai_work_items(store, now=observed_at + timedelta(seconds=4))

    item = store.rd_work_items["work-low"]
    assert first["retryable_work_item_ids"] == ["work-low"]
    assert early["retryable_work_item_ids"] == []
    assert attempted == ["work-low"]
    assert item["status"] == "ready"
    assert item["dispatch_failure_count"] == 1
    assert item["last_dispatch_error_code"] == "RD_AUTO_DISPATCH_RETRYABLE"
    assert item["next_dispatch_at"] == (observed_at + timedelta(seconds=5)).isoformat()
    durable_and_observable = json.dumps(
        {"item": item, "first": first, "early": early},
        ensure_ascii=False,
    )
    assert secret not in durable_and_observable
    assert "customer-secret" not in durable_and_observable


def test_auto_dispatch_uses_bounded_backoff_then_escalates_the_fourth_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import rd_collaboration_auto_dispatch

    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}
    monkeypatch.setattr(
        rd_collaboration_auto_dispatch,
        "dispatch_ai_task_for_work_item",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HTTPException(status_code=503, detail={"code": "UPSTREAM_TIMEOUT"})
        ),
    )
    started_at = datetime.now(UTC).replace(microsecond=0)
    attempt_times = [
        started_at,
        started_at + timedelta(seconds=5),
        started_at + timedelta(seconds=15),
        started_at + timedelta(seconds=35),
    ]
    expected_delays = [5, 10, 20]

    for attempt_index, observed_at in enumerate(attempt_times[:3]):
        result = dispatch_ready_ai_work_items(store, now=observed_at)
        item = store.rd_work_items["work-low"]
        assert result["retryable_work_item_ids"] == ["work-low"]
        assert item["dispatch_failure_count"] == attempt_index + 1
        assert (
            item["next_dispatch_at"]
            == (observed_at + timedelta(seconds=expected_delays[attempt_index])).isoformat()
        )

    fourth = dispatch_ready_ai_work_items(store, now=attempt_times[3])

    paused = store.rd_work_items["work-low"]
    assert fourth["retryable_work_item_ids"] == []
    assert fourth["escalated_work_item_ids"] == ["work-low"]
    assert paused["status"] == "waiting_human"
    assert paused["resume_state"] == "ready"
    assert paused["dispatch_failure_count"] == 4
    assert paused["last_dispatch_error_code"] == "RD_AUTO_DISPATCH_RETRYABLE"
    assert paused["next_dispatch_at"] is None
    decision = store.decision_requests[paused["suspended_decision_request_id"]]
    assert decision["decision_type"] == "dispatch_fault_resolution"
    assert decision["decision_actor_selector"] == {"seat_ids": ["seat-reviewer"]}
    assert decision["evidence_json"][0]["error_code"] == "RD_AUTO_DISPATCH_RETRY_LIMIT"

    dispatch_ready_ai_work_items(store, now=attempt_times[3] + timedelta(seconds=1))
    assert list(store.decision_requests) == [decision["id"]]


def test_auto_dispatch_does_not_record_retry_after_candidate_becomes_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import rd_collaboration_auto_dispatch

    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}

    def stale_dispatch(*_args, **_kwargs):
        store.rd_work_items["work-low"].update({"status": "running", "version": 2})
        raise HTTPException(status_code=409, detail={"code": "RD_WORK_ITEM_NOT_READY"})

    monkeypatch.setattr(
        rd_collaboration_auto_dispatch,
        "dispatch_ai_task_for_work_item",
        stale_dispatch,
    )

    result = dispatch_ready_ai_work_items(
        store,
        now=datetime.now(UTC),
    )

    item = store.rd_work_items["work-low"]
    assert result["retryable_work_item_ids"] == []
    assert result["skipped_work_item_ids"] == ["work-low"]
    assert "dispatch_failure_count" not in item
    assert "last_dispatch_error_code" not in item
    assert "next_dispatch_at" not in item


def test_successful_auto_dispatch_clears_retry_state() -> None:
    store = _store_with_ready_ai_work_items()
    store.rd_work_items = {"work-low": store.rd_work_items["work-low"]}
    store.rd_work_items["work-low"].update(
        {
            "dispatch_failure_count": 3,
            "last_dispatch_error_code": "RD_AUTO_DISPATCH_RETRYABLE",
            "next_dispatch_at": datetime.now(UTC).isoformat(),
        }
    )

    result = dispatch_ready_ai_work_items(
        store,
        now=datetime.now(UTC) + timedelta(seconds=1),
    )

    item = store.rd_work_items["work-low"]
    assert result["dispatched_work_item_ids"] == ["work-low"]
    assert item["dispatch_failure_count"] == 0
    assert item["last_dispatch_error_code"] is None
    assert item["next_dispatch_at"] is None


def test_execution_worker_heartbeat_retains_classified_dispatch_outcomes(monkeypatch) -> None:
    from app.workers import execution_worker

    store = MemoryStore()
    monkeypatch.setattr(execution_worker, "process_execution_outbox_events", lambda *_a, **_k: 0)
    monkeypatch.setattr(
        execution_worker,
        "process_external_event_inbox_events",
        lambda *_a, **_k: 0,
    )
    monkeypatch.setattr(
        execution_worker,
        "process_rd_collaboration_graph_events",
        lambda *_a, **_k: 0,
    )
    monkeypatch.setattr(
        execution_worker,
        "plan_pending_collaboration_runs",
        lambda *_a, **_k: {"planned_run_ids": [], "skipped_run_ids": []},
    )
    monkeypatch.setattr(
        execution_worker,
        "dispatch_ready_ai_work_items",
        lambda *_a, **_k: {
            "capacity_deferred_work_item_ids": ["work-deferred"],
            "dispatched_work_item_ids": ["work-dispatched"],
            "escalated_work_item_ids": ["work-escalated"],
            "human_review_required_work_item_ids": [],
            "retryable_work_item_ids": ["work-retryable"],
            "skipped_work_item_ids": [],
        },
    )
    monkeypatch.setattr(execution_worker, "sync_due_jenkins_deployments", lambda *_a, **_k: 0)

    counts = execution_worker.run_execution_worker_iteration(store, worker_id="dispatch-worker")

    assert counts["rd_collaboration_auto_dispatch_count"] == 1
    assert counts["rd_collaboration_auto_dispatch_deferred_count"] == 1
    assert counts["rd_collaboration_auto_dispatch_escalated_count"] == 1
    assert counts["rd_collaboration_auto_dispatch_retryable_count"] == 1
    heartbeat = store.execution_worker_heartbeats["dispatch-worker"]
    assert heartbeat["counts"] == counts
    assert "customer-secret-token" not in json.dumps(heartbeat)
