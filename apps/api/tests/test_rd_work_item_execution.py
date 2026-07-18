from __future__ import annotations

from app.core.store import MemoryStore
from app.services.ai_executor_runners import (
    _load_executor_policy_for_ai_task,
    _sync_runner_completion_to_ai_task,
)
from app.services.quality_gates import resolve_pre_merge_quality_gate_policy
from app.services.rd_collaboration_decisions import apply_decision
from app.services.rd_work_item_execution import (
    approve_work_item_after_task_review,
    project_work_item_quality_gate_result,
)
from app.services.task_creation import create_ai_task_for_work_item
from app.services.task_review_decisions import approve_review_response
from app.services.task_start_execution import dispatch_ai_task_for_work_item
from app.services.task_state_transitions import cancel_ai_task_for_work_item


def _ai_work_item_store() -> MemoryStore:
    store = MemoryStore()
    store.products["product-1"] = {"id": "product-1", "name": "协作产品"}
    store.product_versions["version-1"] = {
        "id": "version-1",
        "product_id": "product-1",
        "status": "active",
    }
    store.requirements["requirement-1"] = {
        "id": "requirement-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "version_id": "version-1",
        "title": "协作需求",
        "status": "developing",
        "task_ids": [],
    }
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "product_version_id": "version-1",
        "status": "running",
        "strategy_snapshot_id": "snapshot-1",
    }
    store.rd_task_executor_policy_snapshots["snapshot-1"] = {
        "id": "snapshot-1",
        "policy_id": "policy-1",
        "policy_version": 3,
        "schema_version": 2,
        "content_hash": "sha256:frozen-policy",
        "payload_json": {
            "autonomy_config": {"mode": "single_pass", "timeout_seconds": 600},
            "git_config": {"workspace_root": "/tmp/work-item"},
            "quality_gate_config": {"code_change_review_mode": "manual_review"},
        },
    }
    store.rd_run_seats.update(
        {
            "seat-developer": {
                "id": "seat-developer",
                "collaboration_run_id": "run-1",
                "role_code": "developer",
                "subject_type": "ai_employee",
                "ai_employee_id": "employee-dev",
                "executor_profile_id": "executor-codex",
                "status": "active",
            },
            "seat-reviewer": {
                "id": "seat-reviewer",
                "collaboration_run_id": "run-1",
                "role_code": "tester",
                "subject_type": "human_user",
                "human_user_id": "reviewer-1",
                "status": "active",
            },
        }
    )
    store.rd_executor_profiles["executor-codex"] = {
        "id": "executor-codex",
        "executor_type": "codex",
        "runner_id": "runner-frozen",
        "status": "active",
    }
    store.rd_work_items["work-1"] = {
        "id": "work-1",
        "collaboration_run_id": "run-1",
        "requirement_id": "requirement-1",
        "work_item_type": "product_detail_design",
        "title": "完成产品设计",
        "owner_seat_id": "seat-developer",
        "reviewer_seat_id": "seat-reviewer",
        "input_contract": {"background": "需求背景"},
        "output_contract": {"summary": "string"},
        "acceptance_criteria": ["设计可审核"],
        "status": "ready",
        "risk_level": "low",
        "version": 1,
    }
    return store


def test_internal_creation_links_work_item_and_freezes_employee_and_executor() -> None:
    store = _ai_work_item_store()

    created = create_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    task = created["task"]
    frozen = task["input_json"]["rd_collaboration"]
    assert task["collaboration_run_id"] == "run-1"
    assert task["work_item_id"] == "work-1"
    assert task["requirement_id"] == "requirement-1"
    assert frozen["owner_seat_id"] == "seat-developer"
    assert frozen["ai_employee_id"] == "employee-dev"
    assert frozen["executor_profile_id"] == "executor-codex"
    assert frozen["strategy_snapshot_id"] == "snapshot-1"
    assert store.requirements["requirement-1"]["task_ids"] == [task["id"]]

    replay = create_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    assert replay["task"]["id"] == task["id"]
    assert replay["idempotent_replay"] is True


def test_internal_dispatch_uses_only_frozen_executor_and_creates_attempt() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    created = create_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    dispatched = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    task = created["task"]
    assert dispatched["task"]["id"] == task["id"]
    assert dispatched["task"]["status"] == "running"
    assert dispatched["task"]["current_step"] == "waiting_ai_executor"
    assert dispatched["runner_task"]["runner_id"] == "runner-frozen"
    assert dispatched["runner_task"]["executor_type"] == "codex"
    assert dispatched["attempt"]["executor_profile_id"] == "executor-codex"
    assert dispatched["attempt"]["ai_employee_id"] == "employee-dev"
    assert store.rd_work_items["work-1"]["status"] == "running"


def test_internal_dispatch_persists_complete_immutable_execution_gate_snapshot() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    store.rd_task_executor_policy_snapshots["snapshot-1"]["payload_json"].update(
        {
            "quality_gate_config": {
                "code_change_review_mode": "manual_review",
                "quality_gate_policy_id": "quality-gate-frozen",
                "required_checks": ["unit_test", "code_review"],
            },
            "git_config": {
                "workspace_root": "/tmp/work-item",
                "branch": "release/frozen",
                "repository_id": "repo-frozen",
            },
        }
    )
    store.quality_gate_policies["quality-gate-frozen"] = {
        "id": "quality-gate-frozen",
        "phase": "pre_merge",
        "status": "active",
        "required_checks": [{"required": True, "type": "unit_test"}],
        "version": 8,
    }

    dispatched = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    frozen = dispatched["task"]["input_json"]["rd_collaboration"]["execution_policy_snapshot"]
    assert frozen["source_snapshot_id"] == "snapshot-1"
    assert frozen["source_policy_id"] == "policy-1"
    assert frozen["source_policy_version"] == 3
    assert frozen["source_content_hash"] == "sha256:frozen-policy"
    assert frozen["quality_gate_config"] == {
        "code_change_review_mode": "manual_review",
        "quality_gate_policy_id": "quality-gate-frozen",
        "required_checks": ["unit_test", "code_review"],
    }
    assert frozen["git_config"]["branch"] == "release/frozen"
    assert dispatched["runner_task"]["request_config"]["rd_execution_policy_snapshot"] == frozen
    store.quality_gate_policies["quality-gate-frozen"]["required_checks"] = [
        {"required": True, "type": "secret_scan"}
    ]
    resolved_gate = resolve_pre_merge_quality_gate_policy(
        store,
        ai_task=dispatched["task"],
        executor_policy={"quality_gate_policy_id": "mutable-policy-id"},
    )
    assert resolved_gate["id"] == "quality-gate-frozen"
    assert resolved_gate["required_checks"] == [{"required": True, "type": "unit_test"}]
    assert _load_executor_policy_for_ai_task(store, dispatched["task"]) == {
        "autonomy_mode": "single_pass",
        "auto_merge_risk_threshold": "low",
        "code_change_review_mode": "manual_review",
        "cost_budget": None,
        "id": "policy-1",
        "max_duration_seconds": 3600,
        "max_iterations": 1,
        "quality_gate_policy_id": "quality-gate-frozen",
        "token_budget": None,
    }


def test_failed_quality_gate_preserves_attempt_and_requires_a_new_attempt() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    result = project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run={
            "id": "gate-1",
            "status": "failed",
            "blocked_reasons": [{"code": "REQUIRED_CHECK_FAILED"}],
        },
        runner_task_id=dispatch["runner_task"]["id"],
    )

    assert result["next_state"] == "rework_required"
    assert store.rd_work_items["work-1"]["status"] == "rework_required"
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "failed"
    assert store.ai_tasks[dispatch["task"]["id"]]["status"] == "failed"

    retry = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    assert retry["attempt"]["id"] != dispatch["attempt"]["id"]
    assert retry["attempt"]["attempt_no"] == 2


def test_coding_runner_success_always_enters_independent_verification() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners.update(
        {
            "runner-frozen": {
                "id": "runner-frozen",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
                "trust_boundary_id": "coding-boundary",
                "trust_domain": "coding",
                "attestation_status": "active",
            },
            "runner-verifier": {
                "id": "runner-verifier",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
                "trust_boundary_id": "verification-boundary",
                "trust_domain": "verification",
                "attestation_status": "active",
            },
        }
    )
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-18T00:00:00+00:00",
            "result_json": {"summary": "实现完成"},
        }
    )

    _sync_runner_completion_to_ai_task(store, task=coding_task, runner_id="runner-frozen")

    assert store.ai_tasks[dispatch["task"]["id"]]["current_step"] == "quality_gate_running"
    assert len(store.quality_gate_runs) == 1
    assert next(iter(store.quality_gate_runs.values()))["status"] == "running"


def test_cancelled_attempt_fences_coding_completion_before_quality_gate() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners.update(
        {
            "runner-frozen": {
                "id": "runner-frozen",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
                "trust_boundary_id": "coding-boundary",
                "trust_domain": "coding",
                "attestation_status": "active",
            },
            "runner-verifier": {
                "id": "runner-verifier",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
                "trust_boundary_id": "verification-boundary",
                "trust_domain": "verification",
                "attestation_status": "active",
            },
        }
    )
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    attempt = store.rd_work_item_attempts[dispatch["attempt"]["id"]]
    attempt["status"] = "cancelled"
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-18T00:00:00+00:00",
            "result_json": {"summary": "late implementation"},
        }
    )

    _sync_runner_completion_to_ai_task(store, task=coding_task, runner_id="runner-frozen")
    _sync_runner_completion_to_ai_task(store, task=coding_task, runner_id="runner-frozen")

    assert store.quality_gate_runs == {}
    events = [
        event
        for event in store.rd_collaboration_events.values()
        if event["event_type"] == "work_item.runner_result_fenced"
    ]
    assert len(events) == 1
    assert events[0]["payload_json"]["reason"] == "attempt_not_currently_running"


def test_passed_independent_review_completes_the_linked_work_item() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run={"id": "gate-1", "status": "passed", "blocked_reasons": []},
        runner_task_id=dispatch["runner_task"]["id"],
    )

    result = approve_work_item_after_task_review(
        store,
        ai_task_id=dispatch["task"]["id"],
        review_id="review-1",
        actor_id="reviewer-1",
    )

    assert result["work_item"]["status"] == "completed"
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "completed"
    assert any(
        event["event_type"] == "work_item.review_approved"
        for event in store.rd_collaboration_events.values()
    )


def test_approving_the_ai_task_review_projects_to_the_work_item() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run={"id": "gate-1", "status": "passed", "blocked_reasons": []},
        runner_task_id=dispatch["runner_task"]["id"],
    )
    task = store.ai_tasks[dispatch["task"]["id"]]
    task.update({"status": "waiting_review", "review_ids": ["review-1"]})
    store.human_reviews["review-1"] = {
        "id": "review-1",
        "ai_task_id": task["id"],
        "stage": task["task_type"],
        "status": "pending",
        "version": 1,
        "content": {},
    }

    approved = approve_review_response(
        current_store=store,
        review_id="review-1",
        user={"id": "reviewer-1", "roles": ["admin"]},
        version=1,
    )

    assert approved["task_status"] == "completed"
    assert store.rd_work_items["work-1"]["status"] == "completed"


def test_low_risk_work_item_cancel_fences_task_review_attempt_and_runner() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    store.human_reviews["review-1"] = {
        "id": "review-1",
        "ai_task_id": dispatch["task"]["id"],
        "status": "pending",
        "version": 1,
    }

    cancelled = cancel_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
        reason="取消可选工作",
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=dispatch["task"]["input_json"]["rd_collaboration"]["work_item_version"] + 1,
        idempotency_key="cancel:work-1:1",
    )

    assert cancelled["next_state"] == "cancelled"
    assert store.rd_work_items["work-1"]["status"] == "cancelled"
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "cancelled"
    assert store.ai_tasks[dispatch["task"]["id"]]["status"] == "cancelled"
    assert store.human_reviews["review-1"]["status"] == "cancelled"
    assert store.ai_executor_tasks[dispatch["runner_task"]["id"]]["status"] in {
        "cancel_requested",
        "cancelled",
    }
    assert any(
        outbox["event_type"] == "rd.work_item.cancel_runner"
        for outbox in store.execution_outbox_events.values()
    )

    late = project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run={"id": "late-gate", "status": "passed", "blocked_reasons": []},
        runner_task_id=dispatch["runner_task"]["id"],
    )
    assert late and late["late_result"] is True


def test_high_risk_cancel_pauses_then_continue_requires_a_new_attempt_and_task() -> None:
    store = _ai_work_item_store()
    store.rd_work_items["work-1"]["risk_level"] = "high"
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    paused = cancel_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
        reason="高风险变更需要人工确认",
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=2,
        idempotency_key="cancel:work-1:high",
    )

    decision = paused["decision_request"]
    assert paused["next_state"] == "waiting_human"
    assert store.rd_work_items["work-1"]["status"] == "waiting_human"
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "waiting_human"
    assert store.ai_tasks[dispatch["task"]["id"]]["status"] == "cancelled"
    assert any(
        outbox["event_type"] == "rd.work_item.cancel_runner"
        for outbox in store.execution_outbox_events.values()
    )

    continued = apply_decision(
        store,
        decision_request_id=decision["id"],
        selected_option="continue_with_new_attempt",
        input_value={},
        comment="继续但必须重新领取",
        actor={"id": "user-owner", "roles": ["rd_owner"]},
        version=decision["version"],
        idempotency_key="decision:continue:1",
    )
    retry = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    assert continued["work_item"]["status"] == "ready"
    assert retry["attempt"]["id"] != dispatch["attempt"]["id"]
    assert retry["task"]["id"] != dispatch["task"]["id"]
