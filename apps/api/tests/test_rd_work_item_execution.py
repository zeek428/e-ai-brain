from __future__ import annotations

import base64
import hashlib
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.store import MemoryStore
from app.services.ai_executor_runner_rd_completion import move_ai_task_to_executor_review
from app.services.ai_executor_runners import (
    _load_executor_policy_for_ai_task,
    _sync_runner_completion_to_ai_task,
)
from app.services.quality_gates import resolve_pre_merge_quality_gate_policy
from app.services.rd_collaboration_decisions import apply_decision
from app.services.rd_git_branches import rd_work_item_branch_name
from app.services.rd_work_item_execution import (
    approve_work_item_after_task_review,
    project_work_item_quality_gate_result,
)
from app.services.rd_work_item_scheduler import review_work_item
from app.services.task_creation import create_ai_task_for_work_item
from app.services.task_review_decisions import approve_review_response
from app.services.task_start_execution import dispatch_ai_task_for_work_item
from app.services.task_state_transitions import cancel_ai_task_for_work_item


def _ai_work_item_store(*, task_type: str = "product_detail_design") -> MemoryStore:
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
        "work_item_type": task_type,
        "title": "完成产品设计",
        "owner_seat_id": "seat-developer",
        "reviewer_seat_id": "seat-reviewer",
        "input_contract": (
            {
                "background": "需求背景",
                "gitlab_mr_snapshot_id": "snapshot-1",
            }
            if task_type == "code_review"
            else {"background": "需求背景"}
        ),
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
    frozen_contract = dispatched["runner_task"]["input_payload"]["frozen_work_item_contract"]
    assert frozen_contract["input_contract"] == {"background": "需求背景"}
    assert frozen_contract["output_contract"] == {"summary": "string"}
    assert frozen_contract["acceptance_criteria"] == ["设计可审核"]
    assert "冻结工作项契约" in dispatched["runner_task"]["instruction"]
    assert '"background": "需求背景"' in dispatched["runner_task"]["instruction"]
    assert '"summary": "string"' in dispatched["runner_task"]["instruction"]
    assert store.rd_work_items["work-1"]["status"] == "running"


def test_internal_dispatch_overrides_source_branch_with_frozen_work_item_branch() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    store.rd_task_executor_policy_snapshots["snapshot-1"]["payload_json"]["git_config"][
        "branch"
    ] = "codex/rd-collaboration-v2"

    dispatched = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    branch = rd_work_item_branch_name("run-1", "work-1")
    runner_task = dispatched["runner_task"]
    assert runner_task["request_config"]["branch"] == branch
    assert runner_task["input_payload"]["branch"] == branch
    assert branch in runner_task["instruction"]


def test_dependent_work_item_dispatch_freezes_upstream_delivery_commits() -> None:
    store = _ai_work_item_store(task_type="automated_testing")
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    upstream_sha = "c" * 40
    store.rd_work_items["work-upstream"] = {
        "id": "work-upstream",
        "ai_task_id": "task-upstream",
        "collaboration_run_id": "run-1",
        "status": "completed",
    }
    store.rd_work_item_dependencies["dependency-1"] = {
        "id": "dependency-1",
        "collaboration_run_id": "run-1",
        "predecessor_work_item_id": "work-upstream",
        "successor_work_item_id": "work-1",
    }
    store.ai_executor_tasks["runner-task-upstream"] = {
        "id": "runner-task-upstream",
        "ai_task_id": "task-upstream",
        "created_at": "2026-08-04T00:00:00+00:00",
        "result_json": {"git_delivery": {"local_commit_sha": upstream_sha}},
        "status": "succeeded",
        "task_kind": "coding",
    }

    dispatched = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    runner_task = dispatched["runner_task"]
    assert runner_task["request_config"]["upstream_delivery_commit_shas"] == [upstream_sha]
    assert runner_task["input_payload"]["upstream_delivery_commit_shas"] == [upstream_sha]
    assert upstream_sha in runner_task["instruction"]


def test_internal_dispatch_reuses_latest_retained_worktree_for_work_item_rework() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    store.ai_executor_tasks["previous-runner-task"] = {
        "id": "previous-runner-task",
        "ai_task_id": "previous-ai-task",
        "created_at": "2026-07-30T00:00:00+00:00",
        "input_payload": {"rd_work_item_id": "work-1"},
        "result_json": {
            "workspace_isolation": {
                "base_workspace_root": "/tmp/work-item",
                "branch_name": "rd/run-1/work-1",
                "mode": "git_worktree",
                "status": "retained_after_cancel",
                "worktree_path": "/tmp/reused-work-item-worktree",
            }
        },
        "status": "cancelled",
    }

    dispatched = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    config = dispatched["runner_task"]["request_config"]
    assert config["reuse_workspace"] is True
    assert config["workspace_isolation"]["worktree_path"] == "/tmp/reused-work-item-worktree"
    assert dispatched["runner_task"]["workspace_root"] == "/tmp/work-item"


def test_internal_dispatch_carries_structured_review_feedback_into_rework_task() -> None:
    store = _ai_work_item_store()
    store.ai_executor_runners["runner-frozen"] = {
        "id": "runner-frozen",
        "status": "active",
        "executor_types": ["codex"],
        "workspace_roots": ["/tmp/work-item"],
    }
    store.rd_work_item_attempts["attempt-1"] = {
        "id": "attempt-1",
        "work_item_id": "work-1",
        "attempt_no": 1,
        "status": "completed",
        "rework_evidence": [
            {
                "comment": "补充质量门禁 ID、自动测试结果和零部署证据",
                "review_id": "review-1",
            }
        ],
    }

    dispatched = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    expected_feedback = [
        {
            "comment": "补充质量门禁 ID、自动测试结果和零部署证据",
            "review_id": "review-1",
        }
    ]
    runner_task = dispatched["runner_task"]
    assert runner_task["input_payload"]["rework_feedback"] == expected_feedback
    assert runner_task["request_config"]["rework_feedback"] == expected_feedback
    assert dispatched["attempt"]["input_json"]["rework_feedback"] == expected_feedback
    assert "补充质量门禁 ID、自动测试结果和零部署证据" in runner_task["instruction"]
    assert "不得把尚未发生的下游状态写成已完成事实" in runner_task["instruction"]


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


def test_implementation_runner_success_always_enters_independent_verification() -> None:
    store = _ai_work_item_store()
    store.rd_work_items["work-1"]["work_item_type"] = "implementation"
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
    verifier_task = next(
        task for task in store.ai_executor_tasks.values() if task["task_kind"] == "quality_gate"
    )
    assert verifier_task["input_payload"]["rd_work_item_attempt_id"] == dispatch["attempt"]["id"]

    verifier_task.update(
        {
            "error_code": "AI_EXECUTOR_WORKSPACE_NOT_ALLOWED",
            "error_message": "Verifier worktree is outside the legacy whitelist",
            "status": "failed",
        }
    )
    _sync_runner_completion_to_ai_task(store, task=verifier_task, runner_id="runner-verifier")

    assert store.rd_work_items["work-1"]["status"] == "rework_required"
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "failed"


def test_product_detail_design_runner_success_waits_for_human_review() -> None:
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
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-23T04:00:00+00:00",
            "result_json": {"summary": "详细设计完成"},
        }
    )

    _sync_runner_completion_to_ai_task(store, task=coding_task, runner_id="runner-frozen")

    task = store.ai_tasks[dispatch["task"]["id"]]
    assert task["status"] == "waiting_review"
    assert store.quality_gate_runs == {}
    review = next(iter(store.human_reviews.values()))
    assert review["stage"] == "product_detail_design"
    assert store.rd_work_items["work-1"]["status"] == "running"
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "running"

    approved = approve_review_response(
        current_store=store,
        review_id=review["id"],
        user={"id": "reviewer-1", "roles": ["admin"]},
        version=1,
    )

    assert approved["task_status"] == "completed"
    assert store.rd_work_items["work-1"]["status"] == "completed"
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "completed"


def test_v2_code_review_runner_completion_persists_report_with_pending_review() -> None:
    store = _ai_work_item_store(task_type="code_review")
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
    runner_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    runner_task.update(
        {
            "result_json": {
                "findings": [],
                "risk_level": "low",
                "summary": "No blocking findings",
            },
            "status": "succeeded",
        }
    )

    _sync_runner_completion_to_ai_task(store, task=runner_task, runner_id="runner-frozen")

    task = store.ai_tasks[dispatch["task"]["id"]]
    report = store.code_review_reports[task["code_review_report_id"]]
    review = store.human_reviews[task["review_ids"][0]]
    assert task["status"] == "waiting_review"
    assert report["gitlab_mr_snapshot_id"] == "snapshot-1"
    assert report["review_id"] == review["id"]
    assert report["status"] == "pending_review"

    approve_review_response(
        current_store=store,
        review_id=review["id"],
        user={"id": "reviewer-1", "roles": ["admin"]},
        version=1,
    )

    assert store.code_review_reports[report["id"]]["status"] == "confirmed"
    assert store.rd_work_items["work-1"]["status"] == "completed"


def test_legacy_quality_verifier_without_attempt_provenance_uses_coding_retry_attempt() -> None:
    store = _ai_work_item_store()
    store.rd_work_items["work-1"]["work_item_type"] = "implementation"
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
    first = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    first_runner = store.ai_executor_tasks[first["runner_task"]["id"]]
    first_runner.update(
        {
            "error_code": "AI_EXECUTOR_COMMAND_FAILED",
            "error_message": "first attempt failed",
            "status": "failed",
        }
    )
    _sync_runner_completion_to_ai_task(store, task=first_runner, runner_id="runner-frozen")

    retry = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    retry_runner = store.ai_executor_tasks[retry["runner_task"]["id"]]
    retry_runner.update({"result_json": {"summary": "retry complete"}, "status": "succeeded"})
    _sync_runner_completion_to_ai_task(store, task=retry_runner, runner_id="runner-frozen")

    verifier_task = next(
        task
        for task in store.ai_executor_tasks.values()
        if task["task_kind"] == "quality_gate" and task["status"] == "queued"
    )
    assert retry["attempt"]["attempt_no"] == 2
    assert verifier_task["input_payload"]["rd_work_item_attempt_id"] == retry["attempt"]["id"]

    # Simulate the historical task/provenance combination from the
    # pre-provenance Runner package.  Its parent task still carries the first
    # attempt, so the projection must derive the retry attempt through the
    # immutable coding-runner linkage on the quality-gate snapshot instead of
    # fencing this failure as stale.
    store.ai_tasks[retry["task"]["id"]]["input_json"]["rd_collaboration"]["attempt_id"] = (
        first["attempt"]["id"]
    )
    verifier_task["input_payload"].pop("rd_work_item_attempt_id")

    verifier_task.update(
        {
            "error_code": "AI_EXECUTOR_WORKSPACE_NOT_ALLOWED",
            "error_message": "verification worktree rejected",
            "status": "failed",
        }
    )
    _sync_runner_completion_to_ai_task(store, task=verifier_task, runner_id="runner-verifier")

    assert store.rd_work_items["work-1"]["status"] == "rework_required"
    assert store.rd_work_item_attempts[retry["attempt"]["id"]]["status"] == "failed"


def test_failed_coding_runner_requires_a_new_work_item_attempt() -> None:
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
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task.update(
        {
            "error_code": "AI_EXECUTOR_COMMAND_NOT_ALLOWED",
            "error_message": "Configured Codex command was not found",
            "finished_at": "2026-07-23T03:00:00+00:00",
            "status": "failed",
        }
    )

    _sync_runner_completion_to_ai_task(store, task=coding_task, runner_id="runner-frozen")

    work_item = store.rd_work_items["work-1"]
    attempt = store.rd_work_item_attempts[dispatch["attempt"]["id"]]
    ai_task = store.ai_tasks[dispatch["task"]["id"]]
    assert work_item["status"] == "rework_required"
    assert work_item["lease_owner"] is None
    assert work_item["lease_expires_at"] is None
    assert attempt["status"] == "failed"
    assert attempt["failure_json"]["error_code"] == "AI_EXECUTOR_COMMAND_NOT_ALLOWED"
    assert ai_task["current_step"] == "executor_failed"
    assert ai_task["status"] == "failed"
    assert any(
        event["event_type"] == "work_item.runner_execution_failed"
        for event in store.rd_collaboration_events.values()
    )

    retry = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    assert retry["attempt"]["attempt_no"] == 2


def test_timed_out_coding_runner_stops_at_frozen_auto_recovery_limit() -> None:
    store = _ai_work_item_store()
    store.rd_task_executor_policy_snapshots["snapshot-1"]["payload_json"][
        "autonomy_config"
    ] = {
        "mode": "single_pass",
        "timeout_seconds": 600,
        "max_duration_seconds": 3600,
        "max_iterations": 1,
    }
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
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task.update(
        {
            "error_code": "AI_EXECUTOR_TASK_TIMEOUT",
            "error_message": "Executor timed out after 600s",
            "finished_at": "2026-07-24T03:00:00+00:00",
            "status": "timed_out",
        }
    )

    _sync_runner_completion_to_ai_task(store, task=coding_task, runner_id="runner-frozen")

    work_item = store.rd_work_items["work-1"]
    assert work_item["status"] == "waiting_human"
    assert work_item["resume_state"] == "ready"
    decision = store.decision_requests[work_item["suspended_decision_request_id"]]
    assert decision["decision_type"] == "runner_timeout_recovery"
    assert decision["options_hash"].startswith("sha256:")
    assert decision["recommendation_json"]["max_iterations"] == 1
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "failed"

    resumed = apply_decision(
        store,
        decision_request_id=decision["id"],
        selected_option="retry_after_human_confirmation",
        input_value={},
        comment=None,
        actor={"id": "reviewer-1", "roles": []},
        version=decision["version"],
        idempotency_key="decision:runner-timeout-retry:1",
    )
    retry = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )

    assert resumed["next_state"] == "ready"
    assert retry["attempt"]["attempt_no"] == 2


def test_failed_coding_runner_reconciles_an_older_task_only_failure() -> None:
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
    store.ai_tasks[dispatch["task"]["id"]].update(
        {
            "current_step": "executor_failed",
            "error_code": "AI_EXECUTOR_COMMAND_NOT_ALLOWED",
            "status": "failed",
        }
    )
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task.update(
        {
            "error_code": "AI_EXECUTOR_COMMAND_NOT_ALLOWED",
            "error_message": "Configured Codex command was not found",
            "status": "failed",
        }
    )

    _sync_runner_completion_to_ai_task(store, task=coding_task, runner_id="runner-frozen")

    assert store.rd_work_items["work-1"]["status"] == "rework_required"
    assert store.rd_work_item_attempts[dispatch["attempt"]["id"]]["status"] == "failed"
    assert store.ai_tasks[dispatch["task"]["id"]]["status"] == "failed"


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


def test_ai_reviewer_seat_queues_read_only_review_runner_after_quality_gate() -> None:
    """An AI reviewer seat must receive executable work instead of a human-only Review."""
    store = _ai_work_item_store(task_type="development_planning")
    store.rd_run_seats["seat-reviewer"].update(
        {
            "subject_type": "ai_employee",
            "human_user_id": None,
            "ai_employee_id": "employee-reviewer",
            "executor_profile_id": "executor-reviewer",
        }
    )
    store.rd_executor_profiles["executor-reviewer"] = {
        "id": "executor-reviewer",
        "executor_type": "codex",
        "runner_id": "runner-reviewer",
        "status": "active",
        "timeout_seconds": 300,
    }
    store.ai_executor_runners.update(
        {
            "runner-frozen": {
                "id": "runner-frozen",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
            },
            "runner-reviewer": {
                "id": "runner-reviewer",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
                "trust_domain": "verification",
            },
        }
    )
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task["result_json"] = {
        "git_delivery": {"local_commit_sha": "a" * 40},
        "workspace_isolation": {
            "base_workspace_root": "/tmp/work-item",
            "mode": "git_worktree",
            "worktree_path": "/tmp/work-item/reviewable",
        },
    }
    quality_gate = {
        "id": "gate-1",
        "status": "passed",
        "policy_snapshot": {"coding_runner_task_id": coding_task["id"]},
    }
    project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run=quality_gate,
        runner_task_id=coding_task["id"],
    )

    move_ai_task_to_executor_review(
        store,
        ai_task=store.ai_tasks[dispatch["task"]["id"]],
        actor_id="runner-reviewer",
        executor_snapshot={"runner_task_id": coding_task["id"]},
        output_json={"summary": "quality gate passed"},
        quality_gate_run=quality_gate,
    )

    review_tasks = [
        task
        for task in store.ai_executor_tasks.values()
        if task.get("task_kind") == "work_item_review"
    ]
    assert len(review_tasks) == 1
    assert review_tasks[0]["runner_id"] == "runner-reviewer"
    assert review_tasks[0]["workspace_root"] == "/tmp/work-item"
    assert review_tasks[0]["input_payload"] == {
        "ai_employee_id": "employee-reviewer",
        "coding_runner_task_id": coding_task["id"],
        "expected_commit_sha": "a" * 40,
        "executor_profile_id": "executor-reviewer",
        "quality_gate_run_id": "gate-1",
        "rd_collaboration_run_id": "run-1",
        "rd_work_item_id": "work-1",
        "review_id": store.ai_tasks[dispatch["task"]["id"]]["review_ids"][0],
        "reviewer_seat_id": "seat-reviewer",
    }
    assert "Current work-item type: development_planning" in review_tasks[0]["instruction"]
    assert '"id": "gate-1"' in review_tasks[0]["instruction"]
    assert "Do not require downstream remote push" in review_tasks[0]["instruction"]
    assert store.ai_tasks[dispatch["task"]["id"]]["current_step"] == "ai_reviewer_running"
    assert store.ai_tasks[dispatch["task"]["id"]]["status"] == "running"


def test_non_terminal_ai_reviewer_updates_do_not_fail_the_review() -> None:
    """Claim and log updates are progress signals, not terminal review results."""
    store = _ai_work_item_store(task_type="development_planning")
    store.rd_run_seats["seat-reviewer"].update(
        {
            "subject_type": "ai_employee",
            "human_user_id": None,
            "ai_employee_id": "employee-reviewer",
            "executor_profile_id": "executor-reviewer",
        }
    )
    store.rd_executor_profiles["executor-reviewer"] = {
        "id": "executor-reviewer",
        "executor_type": "codex",
        "runner_id": "runner-reviewer",
        "status": "active",
    }
    store.ai_executor_runners.update(
        {
            "runner-frozen": {
                "id": "runner-frozen",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
            },
            "runner-reviewer": {
                "id": "runner-reviewer",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
                "trust_domain": "verification",
            },
        }
    )
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task["result_json"] = {
        "git_delivery": {"local_commit_sha": "a" * 40},
        "workspace_isolation": {
            "mode": "git_worktree",
            "worktree_path": "/tmp/work-item/reviewable",
        },
    }
    quality_gate = {
        "id": "gate-1",
        "status": "passed",
        "policy_snapshot": {"coding_runner_task_id": coding_task["id"]},
    }
    project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run=quality_gate,
        runner_task_id=coding_task["id"],
    )
    move_ai_task_to_executor_review(
        store,
        ai_task=store.ai_tasks[dispatch["task"]["id"]],
        actor_id="runner-reviewer",
        executor_snapshot={"runner_task_id": coding_task["id"]},
        output_json={"summary": "quality gate passed"},
        quality_gate_run=quality_gate,
    )
    review_task = next(
        task
        for task in store.ai_executor_tasks.values()
        if task.get("task_kind") == "work_item_review"
    )

    for status in ("claimed", "running"):
        review_task["status"] = status
        _sync_runner_completion_to_ai_task(
            store,
            task=review_task,
            runner_id="runner-reviewer",
        )

    ai_task = store.ai_tasks[dispatch["task"]["id"]]
    assert ai_task["current_step"] == "ai_reviewer_running"
    assert ai_task["error_code"] is None
    assert ai_task["status"] == "running"


def test_signed_ai_reviewer_approval_completes_frozen_work_item() -> None:
    """A trusted AI reviewer result must own the same state transition as a seat Review."""
    store = _ai_work_item_store(task_type="development_planning")
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    store.rd_run_seats["seat-reviewer"].update(
        {
            "subject_type": "ai_employee",
            "human_user_id": None,
            "ai_employee_id": "employee-reviewer",
            "executor_profile_id": "executor-reviewer",
        }
    )
    store.rd_executor_profiles["executor-reviewer"] = {
        "id": "executor-reviewer",
        "executor_type": "codex",
        "runner_id": "runner-reviewer",
        "status": "active",
    }
    store.ai_executor_runners.update(
        {
            "runner-frozen": {
                "id": "runner-frozen",
                "status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
                "trust_boundary_id": "coding-boundary",
                "trust_domain": "coding",
            },
            "runner-reviewer": {
                "id": "runner-reviewer",
                "status": "active",
                "attestation_public_key": base64.b64encode(public_key).decode("ascii"),
                "attestation_status": "active",
                "executor_types": ["codex"],
                "workspace_roots": ["/tmp/work-item"],
                "trust_boundary_id": "review-boundary",
                "trust_domain": "verification",
            },
        }
    )
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    coding_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    coding_task["result_json"] = {
        "git_delivery": {"local_commit_sha": "b" * 40},
        "workspace_isolation": {
            "mode": "git_worktree",
            "worktree_path": "/tmp/work-item/reviewable",
        },
    }
    quality_gate = {
        "id": "gate-1",
        "status": "passed",
        "policy_snapshot": {"coding_runner_task_id": coding_task["id"]},
    }
    project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run=quality_gate,
        runner_task_id=coding_task["id"],
    )
    move_ai_task_to_executor_review(
        store,
        ai_task=store.ai_tasks[dispatch["task"]["id"]],
        actor_id="runner-reviewer",
        executor_snapshot={"runner_task_id": coding_task["id"]},
        output_json={"summary": "quality gate passed"},
        quality_gate_run=quality_gate,
    )
    review_task = next(
        task
        for task in store.ai_executor_tasks.values()
        if task.get("task_kind") == "work_item_review"
    )
    unsigned_result = {
        "parsed_output": {
            "comment": "Acceptance evidence and implementation are consistent.",
            "decision": "approve",
            "findings": [],
            "reviewed_commit_sha": "b" * 40,
            "summary": "Independent AI review passed",
        }
    }
    payload = {
        "result_sha256": hashlib.sha256(
            json.dumps(
                unsigned_result,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        "runner_task_id": review_task["id"],
        "status": "succeeded",
    }
    review_task.update(
        {
            "finished_at": "2026-08-04T00:00:00+00:00",
            "result_json": {
                **unsigned_result,
                "execution_attestation": {
                    "payload": payload,
                    "signature": base64.b64encode(
                        private_key.sign(
                            json.dumps(
                                payload,
                                ensure_ascii=True,
                                separators=(",", ":"),
                                sort_keys=True,
                            ).encode("utf-8")
                        )
                    ).decode("ascii"),
                },
            },
            "status": "succeeded",
        }
    )

    _sync_runner_completion_to_ai_task(
        store,
        task=review_task,
        runner_id="runner-reviewer",
    )

    ai_task = store.ai_tasks[dispatch["task"]["id"]]
    review = store.human_reviews[ai_task["review_ids"][0]]
    assert store.rd_work_items["work-1"]["status"] == "completed"
    assert ai_task["status"] == "completed"
    assert ai_task["current_step"] == "ai_review_approved"
    assert review["status"] == "approved"
    assert review["decided_by"] == "employee-reviewer"
    assert any(
        feedback.get("producer_subject_id") == "employee-reviewer"
        and feedback.get("executor_profile_id") == "executor-reviewer"
        for feedback in store.role_feedback_records.values()
    )


def test_passed_quality_gate_projection_replays_without_retransitioning_work_item() -> None:
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
    quality_gate = {"id": "gate-1", "status": "passed", "blocked_reasons": []}
    first = project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run=quality_gate,
        runner_task_id=dispatch["runner_task"]["id"],
    )
    replay = project_work_item_quality_gate_result(
        store,
        ai_task_id=dispatch["task"]["id"],
        quality_gate_run=quality_gate,
        runner_task_id=dispatch["runner_task"]["id"],
    )

    assert first["work_item"]["status"] == "reviewing"
    assert replay["idempotent_replay"] is True
    assert replay["work_item"]["version"] == first["work_item"]["version"]
    assert replay["attempt"]["status"] == "completed"


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


def test_approved_work_item_evidence_advances_delivery_phases_once() -> None:
    """The durable work-item review path, not a caller, owns phase changes."""
    store = _ai_work_item_store()
    coding_item = store.rd_work_items["work-1"]
    coding_item.update({"work_item_type": "implementation", "status": "reviewing"})
    store.rd_work_item_attempts["attempt-coding"] = {
        "id": "attempt-coding",
        "work_item_id": "work-1",
        "attempt_no": 1,
        "status": "completed",
    }
    store.rd_work_items["integration-1"] = {
        "id": "integration-1",
        "collaboration_run_id": "run-1",
        "work_item_type": "integration",
        "title": "版本集成测试",
        "owner_seat_id": "seat-developer",
        "reviewer_seat_id": "seat-reviewer",
        "status": "reviewing",
        "risk_level": "low",
        "version": 1,
    }
    store.rd_work_item_attempts["attempt-integration"] = {
        "id": "attempt-integration",
        "work_item_id": "integration-1",
        "attempt_no": 1,
        "status": "completed",
    }

    review_work_item(
        store,
        work_item_id="work-1",
        decision="approve",
        comment=None,
        actor={"id": "reviewer-1"},
        version=1,
        idempotency_key="approve-coding",
    )

    assert store.rd_collaboration_runs["run-1"]["status"] == "integrating"

    review_work_item(
        store,
        work_item_id="integration-1",
        decision="approve",
        comment=None,
        actor={"id": "reviewer-1"},
        version=1,
        idempotency_key="approve-integration",
    )

    assert store.rd_collaboration_runs["run-1"]["status"] == "verifying"
    assert [
        event["event_type"]
        for event in store.rd_collaboration_events.values()
        if event["event_type"] == "run.delivery_phase_advanced"
    ] == ["run.delivery_phase_advanced", "run.delivery_phase_advanced"]


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
