from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from app.core.persistence import PostgresRuntimeStore, PostgresSnapshotRepository
from app.core.repositories.rd_collaboration import RdCollaborationRepositoryError
from app.main import app
from app.services.ai_executor_runner_approvals import (
    approve_plugin_action_ai_executor_response,
)
from app.services.ai_executor_runners import _sync_runner_completion_to_ai_task
from app.services.quality_gates import resolve_pre_merge_quality_gate_policy
from app.services.rd_collaboration_auto_dispatch import dispatch_ready_ai_work_items
from app.services.rd_collaboration_decisions import apply_decision
from app.services.rd_high_risk_dispatch_gate import (
    require_human_approval_for_high_risk_dispatch,
)
from app.services.rd_work_item_execution import (
    approve_work_item_after_task_review,
    project_work_item_quality_gate_result,
)
from app.services.task_start_execution import dispatch_ai_task_for_work_item
from tests.test_rd_collaboration_repository import (
    _accepted_assessment,
    _base_snapshot,
    _decision_record,
    _insert_product_version,
    _insert_requirement,
    _policy_record,
    _run_record,
    _run_scope,
    _version_snapshot,
    postgres_admin_url,
    repository,
)

__all__ = ["postgres_admin_url", "repository"]


def _seed_dispatchable_work_item(
    repository: PostgresSnapshotRepository,
    *,
    prefix: str,
    autonomy_mode: str = "single_pass",
    git_config: dict[str, object] | None = None,
    quality_gate_policy_id: str | None = None,
    seat_capacity: int = 1,
    with_verifier: bool = False,
) -> dict[str, str]:
    ids = _insert_product_version(repository, prefix=prefix, status="active")
    policy = _policy_record(ids, prefix=prefix)
    repository.save_rd_task_executor_policy_record(policy)
    base_snapshot = repository.freeze_base_policy_snapshot(_base_snapshot(policy, prefix=prefix))
    requirement_id = f"{prefix}-requirement"
    assessment_id = f"{prefix}-assessment"
    _insert_requirement(
        repository,
        ids,
        requirement_id=requirement_id,
        status="planned",
        version_id=ids["version"],
    )
    repository.save_assessment_bundle(
        assessment=_accepted_assessment(
            assessment_id=assessment_id,
            requirement_id=requirement_id,
            snapshot_id=str(base_snapshot["id"]),
        ),
        opinions=[],
    )
    version_snapshot = _version_snapshot(
        base_snapshot_id=str(base_snapshot["id"]),
        ids=ids,
        policy_id=str(policy["id"]),
        prefix=prefix,
    )
    version_snapshot["payload_json"] = {
        "autonomy_config": {
            "cost_budget": 5.0,
            "max_duration_seconds": 600,
            "max_iterations": 3,
            "mode": autonomy_mode,
            "timeout_seconds": 60,
            "token_budget": 10_000,
        },
        "git_config": {"workspace_root": "/srv/rd-work", **(git_config or {})},
        "quality_gate_config": {
            "code_change_review_mode": "manual_review",
            **(
                {"quality_gate_policy_id": quality_gate_policy_id}
                if quality_gate_policy_id is not None
                else {}
            ),
        },
    }
    repository.merge_version_policy_snapshot_with_sources(
        snapshot=version_snapshot,
        sources=[
            {
                "id": f"{prefix}-source",
                "snapshot_id": version_snapshot["id"],
                "source_snapshot_id": base_snapshot["id"],
                "requirement_id": requirement_id,
                "assessment_id": assessment_id,
            }
        ],
    )
    run = _run_record(
        ids=ids,
        snapshot_id=str(version_snapshot["id"]),
        prefix=prefix,
        status="running",
    )
    repository.create_collaboration_run_with_exact_scope(
        run=run,
        scope_rows=[
            _run_scope(
                assessment_id=assessment_id,
                final_snapshot_id=str(base_snapshot["id"]),
                requirement_id=requirement_id,
                run_id=str(run["id"]),
                prefix=prefix,
            )
        ],
    )
    run_id = str(run["id"])
    runner_id = f"{prefix}-runner"
    profile_id = f"{prefix}-profile"
    employee_id = f"{prefix}-employee"
    owner_seat_id = f"{prefix}-owner"
    reviewer_seat_id = f"{prefix}-reviewer"
    work_item_id = f"{prefix}-work-item"
    repository.save_ai_executor_runner_record(
        {
            "id": runner_id,
            "name": runner_id,
            "token_hash": sha256(b"rd-work-item-runner").hexdigest(),
            "executor_types": ["codex"],
            "workspace_roots": ["/srv/rd-work"],
            "trust_boundary_id": f"{prefix}-coding-boundary",
            "trust_domain": "coding",
            "attestation_status": "active",
            "created_by": "user_admin",
        }
    )
    if with_verifier:
        repository.save_ai_executor_runner_record(
            {
                "id": f"{prefix}-verification-runner",
                "name": f"{prefix}-verification-runner",
                "token_hash": sha256(b"rd-work-item-verification-runner").hexdigest(),
                "executor_types": ["codex"],
                "workspace_roots": ["/srv/rd-work"],
                "trust_boundary_id": f"{prefix}-verification-boundary",
                "trust_domain": "verification",
                "attestation_status": "active",
                "created_by": "user_admin",
            }
        )
    repository.save_rd_ai_employee_record(
        {
            "id": employee_id,
            "brain_app_id": "rd_brain",
            "code": employee_id,
            "name": employee_id,
            "created_by": "user_admin",
        }
    )
    repository.save_rd_executor_profile_record(
        {
            "id": profile_id,
            "brain_app_id": "rd_brain",
            "code": profile_id,
            "name": profile_id,
            "executor_type": "codex",
            "runner_id": runner_id,
            "created_by": "user_admin",
        }
    )
    repository.save_rd_run_seat_record(
        {
            "id": owner_seat_id,
            "collaboration_run_id": run_id,
            "role_code": "developer",
            "subject_type": "ai_employee",
            "ai_employee_id": employee_id,
            "executor_profile_id": profile_id,
            "capacity": seat_capacity,
            "status": "active",
        }
    )
    repository.save_rd_run_seat_record(
        {
            "id": reviewer_seat_id,
            "collaboration_run_id": run_id,
            "role_code": "tester",
            "subject_type": "human_user",
            "human_user_id": "user_reviewer",
            "status": "active",
        }
    )
    repository.save_rd_work_item_record(
        {
            "id": work_item_id,
            "collaboration_run_id": run_id,
            "requirement_id": requirement_id,
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "atomic work-item dispatch",
            "objective": "verify work-item dispatch transaction",
            "owner_seat_id": owner_seat_id,
            "reviewer_seat_id": reviewer_seat_id,
            "status": "ready",
            "idempotency_key": work_item_id,
        }
    )
    return {
        "run_id": run_id,
        "work_item_id": work_item_id,
        "owner_seat_id": owner_seat_id,
        "requirement_id": requirement_id,
        "product_id": ids["product"],
    }


def _assert_no_autonomous_dispatch_records(
    repository: PostgresSnapshotRepository,
    *,
    ai_task_id: str,
    loop_run_ids: list[str] | None = None,
) -> None:
    assert (
        repository.list_execution_context_manifests(
            subject_id=ai_task_id,
            subject_type="ai_task",
        )
        == []
    )
    assert repository.list_agent_loop_runs(ai_task_id=ai_task_id) == []
    for loop_run_id in loop_run_ids or []:
        assert repository.list_agent_loop_iterations(loop_run_id) == []
    assert [
        ledger
        for ledger in repository.list_trusted_delivery_records(record_type="agent_budget_ledger")
        if ledger.get("ai_task_id") == ai_task_id
    ] == []


def _approve_runner_safety_gate(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
    *,
    prefix: str,
) -> tuple[dict[str, str], dict[str, object], str]:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix=prefix,
        autonomy_mode="autonomous_loop",
    )
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: "Run git push",
    )
    store = PostgresRuntimeStore(repository)
    gated = dispatch_ready_ai_work_items(store)
    assert gated["escalated_work_item_ids"] == [ids["work_item_id"]]
    decision = repository.list_decision_requests(
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )[0]
    apply_decision(
        store,
        decision_request_id=str(decision["id"]),
        selected_option="authorize_blocked_operations",
        input_value={},
        comment=None,
        actor={"id": "user_reviewer", "roles": []},
        version=1,
        idempotency_key=f"{prefix}-approve-runner-safety",
    )
    return ids, decision, f"rd-runner-safety:{ids['work_item_id']}:attempt:1"


def _assert_no_dispatch_bundle_artifacts(
    repository: PostgresSnapshotRepository,
    *,
    work_item_id: str,
) -> None:
    assert repository.list_rd_work_item_attempts(work_item_id) == []
    assert repository.list_ai_executor_tasks(ai_task_id=None) == []
    with repository._connect() as connection:
        counts = connection.execute(
            """
            SELECT
              (SELECT count(*) FROM ai_tasks),
              (SELECT count(*) FROM execution_context_manifests),
              (SELECT count(*) FROM agent_loop_runs),
              (SELECT count(*) FROM agent_loop_iterations),
              (SELECT count(*) FROM trusted_delivery_records
               WHERE record_type = 'agent_budget_ledger')
            """
        ).fetchone()
    assert counts == (0, 0, 0, 0, 0)


def _quality_gate_policy(
    policy_id: str,
    *,
    check_type: str,
    product_id: str,
    version: int,
) -> dict[str, object]:
    return {
        "id": policy_id,
        "name": policy_id,
        "product_id": product_id,
        "phase": "pre_merge",
        "risk_levels": ["low", "medium", "high", "critical"],
        "required_checks": [{"required": True, "type": check_type}],
        "protected_paths": [],
        "required_ci_contexts": [],
        "minimum_independent_evidence": 1,
        "manual_review_on_migration": True,
        "status": "active",
        "version": version,
    }


def test_postgres_claim_allows_released_integration_work_while_run_is_integrating(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(repository, prefix="work-item-integrating-claim")
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            "UPDATE rd_collaboration_runs SET status = 'integrating' WHERE id = %s",
            (ids["run_id"],),
        )
        connection.execute(
            "UPDATE rd_work_items SET work_item_type = 'integration' WHERE id = %s",
            (ids["work_item_id"],),
        )

    claimed = repository.claim_ready_work_item(
        ids["work_item_id"],
        lease_owner="work-item-integrating-claim-owner",
        lease_seconds=60,
        expected_version=1,
    )

    assert claimed is not None
    assert claimed["status"] == "claimed"
    assert claimed["work_item"]["status"] == "claimed"


def test_postgres_high_risk_dispatch_gate_persists_the_decision_and_pauses_the_item(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(repository, prefix="high-risk-dispatch-gate")
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            "UPDATE rd_work_items SET risk_level = 'high' WHERE id = %s",
            (ids["work_item_id"],),
        )

    result = require_human_approval_for_high_risk_dispatch(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )

    decision = result["decision_request"]
    assert decision["decision_type"] == "high_risk_ai_dispatch"
    assert decision["decision_actor_selector"] == {"seat_ids": ["high-risk-dispatch-gate-reviewer"]}
    paused = repository.get_rd_work_item(ids["work_item_id"])
    assert paused is not None
    assert paused["status"] == "waiting_human"
    assert paused["resume_state"] == "ready"
    assert paused["suspended_decision_request_id"] == decision["id"]
    events = repository.list_rd_collaboration_events(ids["run_id"])
    assert events[-1]["event_type"] == "work_item.high_risk_dispatch_approval_required"


def test_postgres_auto_dispatch_releases_a_high_risk_item_only_after_its_decision(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(repository, prefix="high-risk-auto-dispatch")
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            "UPDATE rd_work_items SET risk_level = 'high' WHERE id = %s",
            (ids["work_item_id"],),
        )
    store = PostgresRuntimeStore(repository)
    gate = require_human_approval_for_high_risk_dispatch(
        store,
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    decision = gate["decision_request"]

    apply_decision(
        store,
        decision_request_id=decision["id"],
        selected_option="approve_dispatch",
        input_value={},
        comment=None,
        actor={"id": "user_reviewer", "roles": []},
        version=1,
        idempotency_key="high-risk-auto-dispatch-approved",
    )
    result = dispatch_ready_ai_work_items(store)

    assert result["dispatched_work_item_ids"] == [ids["work_item_id"]]
    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "running"


def test_postgres_auto_dispatch_atomically_escalates_a_frozen_runner_safety_fault(
    repository: PostgresSnapshotRepository,
) -> None:
    secret_workspace = "/srv/customer-secret-token"
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="dispatch-fault-escalation",
        git_config={"workspace_root": secret_workspace},
    )
    store = PostgresRuntimeStore(repository)

    result = dispatch_ready_ai_work_items(store)

    assert result["escalated_work_item_ids"] == [ids["work_item_id"]]
    assert result["retryable_work_item_ids"] == []
    paused = repository.get_rd_work_item(ids["work_item_id"])
    assert paused is not None
    assert paused["status"] == "waiting_human"
    assert paused["resume_state"] == "ready"
    decisions = repository.list_decision_requests(
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )
    assert len(decisions) == 1
    assert decisions[0]["decision_type"] == "dispatch_fault_resolution"
    events = repository.list_rd_collaboration_events(ids["run_id"])
    fault_events = [
        event for event in events if event["event_type"] == "work_item.dispatch_fault_escalated"
    ]
    assert len(fault_events) == 1
    audits = repository.list_audit_events(
        event_type="rd_work_item.dispatch_fault_escalated",
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )
    assert len(audits) == 1
    persisted_fault_records = json.dumps(
        {"audits": audits, "decisions": decisions, "events": fault_events},
        default=str,
    )
    assert secret_workspace not in persisted_fault_records

    dispatch_ready_ai_work_items(store)
    assert (
        len(
            repository.list_decision_requests(
                subject_type="rd_work_item",
                subject_id=ids["work_item_id"],
            )
        )
        == 1
    )


def test_postgres_dispatch_freezes_custom_quality_gate_before_later_policy_mutation(
    repository: PostgresSnapshotRepository,
) -> None:
    policy_id = "work-item-quality-gate-frozen"
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-quality-gate-frozen",
        quality_gate_policy_id=policy_id,
    )
    repository.save_quality_gate_policy_record(
        _quality_gate_policy(
            policy_id,
            check_type="unit_test",
            product_id="work-item-quality-gate-frozen-product",
            version=1,
        )
    )

    dispatched = dispatch_ai_task_for_work_item(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    frozen = dispatched["task"]["input_json"]["rd_collaboration"]["execution_policy_snapshot"]
    assert frozen["quality_gate_policy_snapshot"]["required_checks"] == [
        {"required": True, "type": "unit_test"}
    ]

    repository.save_quality_gate_policy_record(
        _quality_gate_policy(
            policy_id,
            check_type="secret_scan",
            product_id="work-item-quality-gate-frozen-product",
            version=2,
        ),
        expected_version=1,
    )
    resolved = resolve_pre_merge_quality_gate_policy(
        PostgresRuntimeStore(repository),
        ai_task=dispatched["task"],
        executor_policy={"quality_gate_policy_id": policy_id},
    )
    assert resolved["required_checks"] == [{"required": True, "type": "unit_test"}]


def test_postgres_dispatch_rolls_back_task_runner_attempt_event_and_audit_together(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-atomic-rollback",
        autonomy_mode="autonomous_loop",
    )
    allocated_ids: dict[str, list[str]] = {
        "agent_loop_run": [],
        "ai_executor_task": [],
        "execution_context_manifest": [],
        "task": [],
    }
    original_next_id = repository.next_id

    def capture_task_id(prefix: str) -> str:
        record_id = original_next_id(prefix)
        if prefix in allocated_ids:
            allocated_ids[prefix].append(record_id)
        return record_id

    def fail_runner_insert(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("inject runner insert failure")

    monkeypatch.setattr(repository, "next_id", capture_task_id)
    monkeypatch.setattr(repository, "upsert_ai_executor_tasks", fail_runner_insert)

    dispatch_error: Exception | None = None
    try:
        dispatch_ai_task_for_work_item(
            PostgresRuntimeStore(repository),
            collaboration_run_id=ids["run_id"],
            work_item_id=ids["work_item_id"],
        )
    except Exception as exc:  # noqa: BLE001 - the regression inspects rollback after any failure
        dispatch_error = exc

    work_item = repository.get_rd_work_item(ids["work_item_id"])
    assert work_item is not None and work_item["status"] == "ready"
    assert repository.list_rd_work_item_attempts(ids["work_item_id"]) == []
    assert [
        task
        for task in repository.load_ai_tasks()["ai_tasks"].values()
        if task.get("work_item_id") == ids["work_item_id"]
    ] == []
    assert repository.list_ai_executor_tasks(ai_task_id=None) == []
    assert repository.list_rd_collaboration_events(ids["run_id"]) == []
    assert len(allocated_ids["task"]) == 1
    _assert_no_autonomous_dispatch_records(
        repository,
        ai_task_id=allocated_ids["task"][0],
        loop_run_ids=allocated_ids["agent_loop_run"],
    )
    assert [
        event
        for event in repository.list_audit_events()
        if event.get("subject_id")
        in {
            allocated_ids["ai_executor_task"][0],
            allocated_ids["execution_context_manifest"][0],
            allocated_ids["agent_loop_run"][0],
            ids["work_item_id"],
        }
    ] == []
    assert isinstance(dispatch_error, RuntimeError)
    assert str(dispatch_error) == "inject runner insert failure"


def test_postgres_autonomous_dispatch_persists_explicit_audit_bundle_without_reading_store_audits(
    repository: PostgresSnapshotRepository,
) -> None:
    """Dispatch preparation must pass audit records explicitly to PostgreSQL."""
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-explicit-audit-bundle",
        autonomy_mode="autonomous_loop",
    )

    class AppendOnlyAuditEvents(list[dict[str, object]]):
        def __iter__(self):  # type: ignore[override]
            raise AssertionError("dispatch preparation must not read current_store.audit_events")

    store = PostgresRuntimeStore(repository)
    store.audit_events = AppendOnlyAuditEvents()

    dispatched = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )

    audit_types = {
        str(event["event_type"])
        for event in repository.list_audit_events()
        if event.get("subject_id")
        in {
            dispatched["runner_task"]["id"],
            dispatched["task"]["id"],
            dispatched["runner_task"]["context_manifest_id"],
            dispatched["runner_task"]["agent_loop_run_id"],
            ids["work_item_id"],
        }
    }
    assert {
        "agent_loop.started",
        "ai_executor_task.queued",
        "execution_context_manifest.created",
        "rd_work_item.ai_task_dispatched",
    } <= audit_types


def test_postgres_safety_rejected_dispatch_retry_leaves_no_preparation_records(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-safety-rejected",
        autonomy_mode="autonomous_loop",
    )
    store = PostgresRuntimeStore(repository)
    allocated_task_ids: list[str] = []
    original_next_id = repository.next_id

    def capture_task_id(prefix: str) -> str:
        record_id = original_next_id(prefix)
        if prefix == "task":
            allocated_task_ids.append(record_id)
        return record_id

    monkeypatch.setattr(repository, "next_id", capture_task_id)
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: "Run git push with token=customer-secret",
    )

    for _ in range(2):
        with pytest.raises(HTTPException) as exc_info:
            dispatch_ai_task_for_work_item(
                store,
                collaboration_run_id=ids["run_id"],
                work_item_id=ids["work_item_id"],
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "AI_EXECUTOR_APPROVAL_REQUIRED"
        safe_detail = json.dumps(exc_info.value.detail)
        assert "Run git push" not in safe_detail
        assert "customer-secret" not in safe_detail
        assert "/srv/rd-work" not in safe_detail

    assert len(allocated_task_ids) == 2
    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "ready"
    assert repository.list_rd_work_item_attempts(ids["work_item_id"]) == []
    assert repository.list_ai_executor_tasks(ai_task_id=None) == []
    for task_id in allocated_task_ids:
        _assert_no_autonomous_dispatch_records(repository, ai_task_id=task_id)
    with repository._connect() as connection:
        assert (
            connection.execute("SELECT count(*) FROM ai_executor_approval_requests").fetchone()[0]
            == 0
        )
    assert store.ai_executor_approval_requests == {}
    assert not any(
        event.get("event_type") == "ai_executor_task.approval_requested"
        for event in store.audit_events
    )


def test_postgres_runner_safety_approval_is_atomic_replay_safe_and_dispatchable(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="runner-safety-approval",
        autonomy_mode="autonomous_loop",
    )
    store = PostgresRuntimeStore(repository)
    secret = "customer-token=secret-value /srv/private-workspace"
    allocated_task_ids: list[str] = []
    original_next_id = repository.next_id

    def capture_task_id(prefix: str) -> str:
        record_id = original_next_id(prefix)
        if prefix == "task":
            allocated_task_ids.append(record_id)
        return record_id

    monkeypatch.setattr(repository, "next_id", capture_task_id)
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: f"Run git push, then rm -rf build. {secret}",
    )

    blocked = dispatch_ready_ai_work_items(store)

    assert blocked["escalated_work_item_ids"] == [ids["work_item_id"]]
    assert len(allocated_task_ids) == 1
    paused = repository.get_rd_work_item(ids["work_item_id"])
    assert paused is not None
    assert paused["status"] == "waiting_human"
    assert paused["resume_state"] == "ready"
    approval_request_id = f"rd-runner-safety:{ids['work_item_id']}:attempt:1"
    with repository._connect() as connection:
        approval_requests = connection.execute(
            """
            SELECT id, status, workspace_root, blocked_operations,
                   approval_request, approval
            FROM ai_executor_approval_requests
            """
        ).fetchall()
        counts = connection.execute(
            """
            SELECT
              (SELECT count(*) FROM ai_tasks),
              (SELECT count(*) FROM ai_executor_tasks),
              (SELECT count(*) FROM rd_work_item_attempts),
              (SELECT count(*) FROM execution_context_manifests),
              (SELECT count(*) FROM agent_loop_runs),
              (SELECT count(*) FROM agent_loop_iterations),
              (SELECT count(*) FROM trusted_delivery_records
               WHERE record_type = 'agent_budget_ledger')
            """
        ).fetchone()
    assert len(approval_requests) == 1
    approval_row = approval_requests[0]
    assert approval_row[0] == approval_request_id
    assert approval_row[1] == "pending"
    assert approval_row[2] == ""
    assert approval_row[3] == ["git_push_or_merge", "destructive_delete"]
    assert approval_row[4] == {
        "approval_request_id": approval_request_id,
        "attempt_no": 1,
        "blocked_operations": ["git_push_or_merge", "destructive_delete"],
        "policy_version": "runner_safety_v1",
        "source": "rd_collaboration_work_item",
        "work_item_id": ids["work_item_id"],
    }
    assert approval_row[5] == {}
    assert counts == (0, 0, 0, 0, 0, 0, 0)

    decisions = repository.list_decision_requests(
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision["decision_type"] == "runner_safety_approval"
    assert [option["code"] for option in decision["options_json"]] == [
        "authorize_blocked_operations",
        "cancel_work_item",
    ]
    events = [
        event
        for event in repository.list_rd_collaboration_events(ids["run_id"])
        if event["event_type"] == "work_item.runner_safety_approval_required"
    ]
    audits = repository.list_audit_events(
        event_type="rd_work_item.runner_safety_approval_required",
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )
    assert len(events) == 1
    assert len(audits) == 1
    persisted_gate = json.dumps(
        {
            "approval_request": approval_row[4],
            "decision": decision,
            "events": events,
            "audits": audits,
            "worker_outcome": blocked,
        },
        default=str,
    )
    assert secret not in persisted_gate
    assert "/srv/private-workspace" not in persisted_gate

    replay_store = PostgresRuntimeStore(repository)
    dispatch_ready_ai_work_items(replay_store)
    with repository._connect() as connection:
        assert (
            connection.execute("SELECT count(*) FROM ai_executor_approval_requests").fetchone()[0]
            == 1
        )
    assert (
        len(
            repository.list_decision_requests(
                subject_type="rd_work_item",
                subject_id=ids["work_item_id"],
            )
        )
        == 1
    )
    assert (
        len(
            [
                event
                for event in repository.list_rd_collaboration_events(ids["run_id"])
                if event["event_type"] == "work_item.runner_safety_approval_required"
            ]
        )
        == 1
    )

    frozen_snapshot = repository.get_rd_policy_snapshot(
        repository.get_rd_collaboration_run(ids["run_id"])["strategy_snapshot_id"]
    )
    decided = apply_decision(
        replay_store,
        decision_request_id=decision["id"],
        selected_option="authorize_blocked_operations",
        input_value={},
        comment=None,
        actor={"id": "user_reviewer", "roles": []},
        version=1,
        idempotency_key="approve-runner-safety-attempt-1",
    )

    assert decided["work_item"]["status"] == "ready"
    with repository._connect() as connection:
        approved_row = connection.execute(
            """
            SELECT status, blocked_operations, approval
            FROM ai_executor_approval_requests WHERE id = %s
            """,
            (approval_request_id,),
        ).fetchone()
    assert approved_row is not None
    assert approved_row[0] == "approved"
    approval = approved_row[2]
    assert approval == {
        "approval_id": f"{approval_request_id}:approval",
        "approval_request_id": approval_request_id,
        "approved": True,
        "approved_at": approval["approved_at"],
        "approved_by": "user_reviewer",
        "approved_operations": approved_row[1],
        "expires_at": approval["expires_at"],
        "mode": "platform_human_approval",
        "policy_version": "runner_safety_v1",
    }
    assert repository.get_rd_policy_snapshot(frozen_snapshot["id"]) == frozen_snapshot

    dispatched = dispatch_ready_ai_work_items(replay_store)

    assert dispatched["dispatched_work_item_ids"] == [ids["work_item_id"]]
    attempts = repository.list_rd_work_item_attempts(ids["work_item_id"])
    assert len(attempts) == 1
    assert attempts[0]["attempt_no"] == 1
    tasks = repository.list_ai_executor_tasks(ai_task_id=None)
    assert len(tasks) == 1
    assert tasks[0]["request_config"]["ai_executor_approval"] == approval
    assert tasks[0]["request_config"]["ai_executor_safety"]["status"] == "approved"


@pytest.mark.parametrize(
    "recommendation_json",
    [
        pytest.param(
            {"approval_request_id": "{approval_request_id}"},
            id="missing-action",
        ),
        pytest.param(
            {
                "action": "authorize_blocked_operations_or_cancel",
                "approval_request_id": "{approval_request_id}",
                "unexpected": True,
            },
            id="unexpected-field",
        ),
        pytest.param(
            {
                "action": "cancel_without_authorization",
                "approval_request_id": "{approval_request_id}",
            },
            id="modified-action",
        ),
    ],
)
def test_postgres_runner_safety_decision_requires_the_full_canonical_recommendation(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
    recommendation_json: dict[str, object],
) -> None:
    prefix = "runner-safety-recommendation-" + str(
        recommendation_json.get("unexpected") or recommendation_json.get("action") or "missing"
    ).replace("_", "-")
    ids = _seed_dispatchable_work_item(
        repository,
        prefix=prefix,
        autonomy_mode="autonomous_loop",
    )
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: "Run git push",
    )
    store = PostgresRuntimeStore(repository)
    gated = dispatch_ready_ai_work_items(store)
    assert gated["escalated_work_item_ids"] == [ids["work_item_id"]]
    decision = repository.list_decision_requests(
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )[0]
    approval_request_id = f"rd-runner-safety:{ids['work_item_id']}:attempt:1"
    mutated_recommendation = {
        key: approval_request_id if value == "{approval_request_id}" else value
        for key, value in recommendation_json.items()
    }
    with repository._connect() as connection:
        connection.execute(
            "UPDATE decision_requests SET recommendation_json = %s WHERE id = %s",
            (Jsonb(mutated_recommendation), decision["id"]),
        )
        connection.commit()

    with pytest.raises(RdCollaborationRepositoryError) as exc_info:
        apply_decision(
            store,
            decision_request_id=str(decision["id"]),
            selected_option="authorize_blocked_operations",
            input_value={},
            comment=None,
            actor={"id": "user_reviewer", "roles": []},
            version=1,
            idempotency_key=f"{prefix}-mutated-recommendation",
        )

    assert exc_info.value.code == "RD_DECISION_REQUIRED"
    assert repository.get_ai_executor_approval_request(approval_request_id)["status"] == "pending"
    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "waiting_human"
    _assert_no_dispatch_bundle_artifacts(repository, work_item_id=ids["work_item_id"])


def test_postgres_dispatch_bundle_rejects_a_reserved_approval_claim_without_provenance(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids, _decision, _approval_request_id = _approve_runner_safety_gate(
        repository,
        monkeypatch,
        prefix="runner-safety-missing-final-proof",
    )
    original_dispatch = repository.dispatch_work_item_execution_bundle

    def dispatch_without_provenance(**kwargs):  # type: ignore[no-untyped-def]
        kwargs.pop("runner_safety_approval_request", None)
        kwargs.pop("runner_safety_decision", None)
        return original_dispatch(**kwargs)

    monkeypatch.setattr(
        repository,
        "dispatch_work_item_execution_bundle",
        dispatch_without_provenance,
    )

    with pytest.raises(RdCollaborationRepositoryError) as exc_info:
        dispatch_ai_task_for_work_item(
            PostgresRuntimeStore(repository),
            collaboration_run_id=ids["run_id"],
            work_item_id=ids["work_item_id"],
        )

    assert exc_info.value.code == "RD_DECISION_REQUIRED"
    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "ready"
    _assert_no_dispatch_bundle_artifacts(repository, work_item_id=ids["work_item_id"])


@pytest.mark.parametrize("interleaved_change", ["approval_expiry", "decision_mutation"])
def test_postgres_dispatch_revalidates_runner_safety_after_preflight_before_commit(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
    interleaved_change: str,
) -> None:
    ids, decision, approval_request_id = _approve_runner_safety_gate(
        repository,
        monkeypatch,
        prefix=f"runner-safety-final-{interleaved_change.replace('_', '-')}",
    )
    preflight_complete = Event()
    allow_bundle_commit = Event()
    original_dispatch = repository.dispatch_work_item_execution_bundle

    def pause_after_preflight(**kwargs):  # type: ignore[no-untyped-def]
        preflight_complete.set()
        assert allow_bundle_commit.wait(timeout=10)
        return original_dispatch(**kwargs)

    monkeypatch.setattr(
        repository,
        "dispatch_work_item_execution_bundle",
        pause_after_preflight,
    )
    outcome: dict[str, object] = {}

    def dispatch() -> None:
        try:
            outcome["result"] = dispatch_ai_task_for_work_item(
                PostgresRuntimeStore(repository),
                collaboration_run_id=ids["run_id"],
                work_item_id=ids["work_item_id"],
            )
        except Exception as exc:  # noqa: BLE001 - thread transfers the exact failure
            outcome["error"] = exc

    thread = Thread(target=dispatch)
    thread.start()
    assert preflight_complete.wait(timeout=10)
    with repository._connect() as connection:
        if interleaved_change == "approval_expiry":
            expired_at = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
            approval = repository.get_ai_executor_approval_request(approval_request_id)["approval"]
            connection.execute(
                """
                UPDATE ai_executor_approval_requests
                SET approval = %s, expires_at = %s, updated_at = now()
                WHERE id = %s
                """,
                (Jsonb({**approval, "expires_at": expired_at}), expired_at, approval_request_id),
            )
        else:
            connection.execute(
                """
                UPDATE decision_requests
                SET recommendation_json = recommendation_json || '{"unexpected": true}'::jsonb,
                    updated_at = now()
                WHERE id = %s
                """,
                (decision["id"],),
            )
        connection.commit()
    allow_bundle_commit.set()
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert "result" not in outcome
    assert isinstance(outcome.get("error"), RdCollaborationRepositoryError)
    assert outcome["error"].code == "RD_DECISION_REQUIRED"  # type: ignore[union-attr]
    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "ready"
    _assert_no_dispatch_bundle_artifacts(repository, work_item_id=ids["work_item_id"])


def test_postgres_dispatch_rejects_approval_that_expires_while_waiting_for_its_row_lock(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids, _decision, approval_request_id = _approve_runner_safety_gate(
        repository,
        monkeypatch,
        prefix="runner-safety-lock-wait-expiry",
    )
    expires_at = datetime.now(UTC) + timedelta(seconds=1.5)
    with repository._connect() as connection:
        approval = repository.get_ai_executor_approval_request(approval_request_id)["approval"]
        connection.execute(
            """
            UPDATE ai_executor_approval_requests
            SET approval = %s, expires_at = %s, updated_at = now()
            WHERE id = %s
            """,
            (
                Jsonb({**approval, "expires_at": expires_at.isoformat()}),
                expires_at,
                approval_request_id,
            ),
        )
        connection.commit()

    validation_started = Event()
    original_validate = repository._validate_runner_safety_dispatch_cursor

    def signal_validation_started(*args, **kwargs):  # type: ignore[no-untyped-def]
        validation_started.set()
        return original_validate(*args, **kwargs)

    monkeypatch.setattr(
        repository,
        "_validate_runner_safety_dispatch_cursor",
        signal_validation_started,
    )
    outcome: dict[str, object] = {}

    def dispatch() -> None:
        try:
            outcome["result"] = dispatch_ai_task_for_work_item(
                PostgresRuntimeStore(repository),
                collaboration_run_id=ids["run_id"],
                work_item_id=ids["work_item_id"],
            )
        except Exception as exc:  # noqa: BLE001 - thread transfers the exact failure
            outcome["error"] = exc

    with repository._connect(autocommit=False) as lock_connection:
        lock_connection.execute(
            "SELECT id FROM ai_executor_approval_requests WHERE id = %s FOR UPDATE",
            (approval_request_id,),
        )
        thread = Thread(target=dispatch)
        thread.start()
        assert validation_started.wait(timeout=10)
        remaining_seconds = (expires_at - datetime.now(UTC)).total_seconds()
        if remaining_seconds > 0:
            Event().wait(timeout=remaining_seconds + 0.2)

    thread.join(timeout=10)

    assert not thread.is_alive()
    assert "result" not in outcome
    assert isinstance(outcome.get("error"), RdCollaborationRepositoryError)
    assert outcome["error"].code == "RD_DECISION_REQUIRED"  # type: ignore[union-attr]
    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "ready"
    _assert_no_dispatch_bundle_artifacts(repository, work_item_id=ids["work_item_id"])


@pytest.mark.parametrize("source", [None, "rd_collaboration_work_item"])
def test_postgres_dispatch_rejects_preseeded_reserved_approval_without_frozen_decision(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
    source: str | None,
) -> None:
    suffix = "missing-source" if source is None else "missing-decision"
    ids = _seed_dispatchable_work_item(
        repository,
        prefix=f"runner-safety-preseed-{suffix}",
        autonomy_mode="autonomous_loop",
    )
    approval_request_id = f"rd-runner-safety:{ids['work_item_id']}:attempt:1"
    request_snapshot = {
        "approval_request_id": approval_request_id,
        "attempt_no": 1,
        "blocked_operations": ["git_push_or_merge"],
        "policy_version": "runner_safety_v1",
        "work_item_id": ids["work_item_id"],
    }
    if source is not None:
        request_snapshot["source"] = source
    approved_at = datetime.now(UTC).isoformat()
    crafted_record = {
        "id": approval_request_id,
        "approval": {
            "approval_id": f"{approval_request_id}:approval",
            "approval_request_id": approval_request_id,
            "approved": True,
            "approved_at": approved_at,
            "approved_by": "user_admin",
            "approved_operations": ["git_push_or_merge"],
            "expires_at": "2099-01-01T00:00:00+00:00",
            "mode": "platform_human_approval",
            "policy_version": "runner_safety_v1",
        },
        "approval_request": request_snapshot,
        "approved_at": approved_at,
        "approved_by": "user_admin",
        "blocked_operations": ["git_push_or_merge"],
        "executor_type": "codex",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "requested_at": approved_at,
        "requested_by": "user_admin",
        "risk_level": "high",
        "runner_id": f"runner-safety-preseed-{suffix}-runner",
        "status": "approved",
        "workspace_root": "",
    }
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            repository._plugin_read_repository.upsert_ai_executor_approval_requests(
                cursor,
                {approval_request_id: crafted_record},
            )
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: "Run git push",
    )

    result = dispatch_ready_ai_work_items(PostgresRuntimeStore(repository))

    assert result["dispatched_work_item_ids"] == []
    assert repository.list_rd_work_item_attempts(ids["work_item_id"]) == []
    assert repository.list_ai_executor_tasks(ai_task_id=None) == []


def test_postgres_plugin_approval_rechecks_collaboration_source_at_final_mutation(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_id = "plugin-generic-approval-race"
    action_id = "action-generic-approval-race"
    approval_request_id = "generic-approval-race-request"
    repository.save_plugin_record(
        {
            "id": plugin_id,
            "code": "generic_approval_race",
            "name": "Generic approval race",
            "protocol": "mcp_http",
            "status": "active",
            "created_by": "user_admin",
        }
    )
    repository.save_plugin_action_record(
        {
            "id": action_id,
            "plugin_id": plugin_id,
            "code": "generic_approval_race_action",
            "name": "Generic approval race action",
            "action_type": "mcp_tool",
            "request_config": {},
            "result_mapping": {},
            "status": "active",
            "created_by": "user_admin",
        }
    )
    store = PostgresRuntimeStore(repository)
    from app.services import ai_executor_runner_approvals as approval_service

    original_build = approval_service.build_ai_executor_approval_snapshot

    def insert_collaboration_request_during_approval(**kwargs):  # type: ignore[no-untyped-def]
        now = datetime.now(UTC).isoformat()
        interleaved_record = {
            "id": approval_request_id,
            "approval": {},
            "approval_request": {
                "approval_request_id": approval_request_id,
                "attempt_no": 1,
                "blocked_operations": ["git_push_or_merge"],
                "policy_version": "runner_safety_v1",
                "source": "rd_collaboration_work_item",
                "work_item_id": "work-race",
            },
            "blocked_operations": ["git_push_or_merge"],
            "executor_type": "codex",
            "requested_at": now,
            "requested_by": "user_owner",
            "risk_level": "high",
            "runner_id": None,
            "status": "pending",
            "workspace_root": "",
        }
        with repository._connect() as connection:
            with connection.cursor() as cursor:
                repository._plugin_read_repository.upsert_ai_executor_approval_requests(
                    cursor,
                    {approval_request_id: interleaved_record},
                )
        return original_build(**kwargs)

    monkeypatch.setattr(
        approval_service,
        "build_ai_executor_approval_snapshot",
        insert_collaboration_request_during_approval,
    )

    with pytest.raises(HTTPException) as exc_info:
        approve_plugin_action_ai_executor_response(
            action_id=action_id,
            current_store=store,
            payload=SimpleNamespace(
                approval_id=None,
                approval_request={
                    "approval_request_id": approval_request_id,
                    "blocked_operations": ["git_push_or_merge"],
                    "executor_type": "codex",
                    "workspace_root": "",
                },
                approved_operations=["git_push_or_merge"],
                expires_at="2099-01-01T00:00:00+00:00",
                reason="generic approval",
            ),
            user={"id": "user_admin", "permissions": ["system.admin"], "roles": ["admin"]},
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {
        "code": "RD_COLLABORATION_APPROVAL_DECISION_REQUIRED",
        "message": "Collaboration approval must be resolved through its frozen decision",
    }
    persisted_action = next(
        item for item in repository.list_plugin_actions() if item["id"] == action_id
    )
    assert "ai_executor_approval" not in persisted_action["request_config"]
    assert repository.get_ai_executor_approval_request(approval_request_id)["status"] == "pending"


def test_postgres_expired_runner_safety_approval_renews_without_dispatch_artifacts(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="runner-safety-renewal",
        autonomy_mode="autonomous_loop",
    )
    store = PostgresRuntimeStore(repository)
    secret = "customer-token=secret-value /srv/private-workspace"
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: f"Run git push. {secret}",
    )

    first_gate = dispatch_ready_ai_work_items(store)
    assert first_gate["escalated_work_item_ids"] == [ids["work_item_id"]]
    first_decision = repository.list_decision_requests(
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )[0]
    first_approval_request_id = f"rd-runner-safety:{ids['work_item_id']}:attempt:1"
    apply_decision(
        store,
        decision_request_id=first_decision["id"],
        selected_option="authorize_blocked_operations",
        input_value={},
        comment=None,
        actor={"id": "user_reviewer", "roles": []},
        version=1,
        idempotency_key="approve-runner-safety-renewal-initial",
    )
    first_record = repository.get_ai_executor_approval_request(first_approval_request_id)
    assert first_record is not None
    expired_at = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    expired_approval = {**first_record["approval"], "expires_at": expired_at}
    with repository._connect() as connection:
        connection.execute(
            """
            UPDATE ai_executor_approval_requests
            SET approval = %s, expires_at = %s
            WHERE id = %s
            """,
            (Jsonb(expired_approval), expired_at, first_approval_request_id),
        )
        connection.commit()
    immutable_expired_record = repository.get_ai_executor_approval_request(
        first_approval_request_id
    )

    renewed_gate = dispatch_ready_ai_work_items(PostgresRuntimeStore(repository))

    assert renewed_gate["escalated_work_item_ids"] == [ids["work_item_id"]]
    renewal_request_id = f"{first_approval_request_id}:renewal:1"
    renewal_record = repository.get_ai_executor_approval_request(renewal_request_id)
    assert renewal_record is not None
    assert renewal_record["status"] == "pending"
    assert renewal_record["approval"] == {}
    assert renewal_record["approval_request"] == {
        "approval_request_id": renewal_request_id,
        "attempt_no": 1,
        "blocked_operations": ["git_push_or_merge"],
        "policy_version": "runner_safety_v1",
        "renewal_no": 1,
        "source": "rd_collaboration_work_item",
        "work_item_id": ids["work_item_id"],
    }
    assert (
        repository.get_ai_executor_approval_request(first_approval_request_id)
        == immutable_expired_record
    )
    decisions = repository.list_decision_requests(
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )
    renewal_decision = next(decision for decision in decisions if decision["status"] == "pending")
    assert renewal_decision["id"] == (
        f"runner-safety-approval:{ids['work_item_id']}:attempt:1:renewal:1"
    )
    assert renewal_decision["recommendation_json"]["approval_request_id"] == renewal_request_id
    assert repository.list_rd_work_item_attempts(ids["work_item_id"]) == []
    assert repository.list_ai_executor_tasks(ai_task_id=None) == []
    with repository._connect() as connection:
        artifact_counts = connection.execute(
            """
            SELECT
              (SELECT count(*) FROM ai_tasks),
              (SELECT count(*) FROM execution_context_manifests),
              (SELECT count(*) FROM agent_loop_runs),
              (SELECT count(*) FROM agent_loop_iterations),
              (SELECT count(*) FROM trusted_delivery_records
               WHERE record_type = 'agent_budget_ledger')
            """
        ).fetchone()
    assert artifact_counts == (0, 0, 0, 0, 0)
    renewal_events = [
        event
        for event in repository.list_rd_collaboration_events(ids["run_id"])
        if (event.get("payload_json") or {}).get("approval_request_id") == renewal_request_id
    ]
    renewal_audits = [
        event
        for event in repository.list_audit_events(
            event_type="rd_work_item.runner_safety_approval_required",
            subject_type="rd_work_item",
            subject_id=ids["work_item_id"],
        )
        if (event.get("payload") or {}).get("approval_request_id") == renewal_request_id
    ]
    assert len(renewal_events) == 1
    assert len(renewal_audits) == 1
    durable_gate = json.dumps(
        {
            "old_approval": immutable_expired_record,
            "renewal": renewal_record,
            "decision": renewal_decision,
            "events": renewal_events,
            "audits": renewal_audits,
            "outcome": renewed_gate,
        },
        default=str,
    )
    assert secret not in durable_gate
    assert "customer-token" not in durable_gate
    assert "/srv/private-workspace" not in durable_gate

    replay = dispatch_ready_ai_work_items(PostgresRuntimeStore(repository))
    assert replay["escalated_work_item_ids"] == []
    with repository._connect() as connection:
        assert (
            connection.execute("SELECT count(*) FROM ai_executor_approval_requests").fetchone()[0]
            == 2
        )
    assert (
        len(
            repository.list_decision_requests(
                subject_type="rd_work_item",
                subject_id=ids["work_item_id"],
            )
        )
        == 2
    )

    decided = apply_decision(
        PostgresRuntimeStore(repository),
        decision_request_id=renewal_decision["id"],
        selected_option="authorize_blocked_operations",
        input_value={},
        comment=None,
        actor={"id": "user_reviewer", "roles": []},
        version=1,
        idempotency_key="approve-runner-safety-renewal-1",
    )
    replayed_decision = apply_decision(
        PostgresRuntimeStore(repository),
        decision_request_id=renewal_decision["id"],
        selected_option="authorize_blocked_operations",
        input_value={},
        comment=None,
        actor={"id": "user_reviewer", "roles": []},
        version=1,
        idempotency_key="approve-runner-safety-renewal-1",
    )
    assert decided["idempotent_replay"] is False
    assert replayed_decision == {**decided, "idempotent_replay": True}

    dispatched = dispatch_ready_ai_work_items(PostgresRuntimeStore(repository))

    assert dispatched["dispatched_work_item_ids"] == [ids["work_item_id"]]
    attempts = repository.list_rd_work_item_attempts(ids["work_item_id"])
    assert len(attempts) == 1
    assert attempts[0]["attempt_no"] == 1
    tasks = repository.list_ai_executor_tasks(ai_task_id=None)
    assert len(tasks) == 1
    renewed_approval = repository.get_ai_executor_approval_request(renewal_request_id)["approval"]
    assert tasks[0]["request_config"]["ai_executor_approval"] == renewed_approval
    assert tasks[0]["request_config"]["ai_executor_safety"]["status"] == "approved"
    assert (
        repository.get_ai_executor_approval_request(first_approval_request_id)
        == immutable_expired_record
    )


def test_postgres_runner_safety_rejection_atomically_cancels_without_dispatch(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(repository, prefix="runner-safety-rejection")
    store = PostgresRuntimeStore(repository)
    monkeypatch.setattr(
        "app.services.rd_task_executor_policies.render_executor_instruction",
        lambda *_args, **_kwargs: "Run git push",
    )
    dispatch_ready_ai_work_items(store)
    decision = repository.list_decision_requests(
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )[0]

    decided = apply_decision(
        store,
        decision_request_id=decision["id"],
        selected_option="cancel_work_item",
        input_value={},
        comment="Unsafe operation is not authorized",
        actor={"id": "user_reviewer", "roles": []},
        version=1,
        idempotency_key="reject-runner-safety-attempt-1",
    )

    approval_request_id = f"rd-runner-safety:{ids['work_item_id']}:attempt:1"
    approval_request = repository.get_ai_executor_approval_request(approval_request_id)
    assert approval_request is not None
    assert approval_request["status"] == "rejected"
    assert approval_request["approval"] == {}
    assert decided["work_item"]["status"] == "cancelled"
    assert repository.list_rd_work_item_attempts(ids["work_item_id"]) == []
    assert repository.list_ai_executor_tasks(ai_task_id=None) == []


def test_concurrent_postgres_dispatch_reuses_one_active_task_attempt_and_runner(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-atomic-concurrent",
        autonomy_mode="autonomous_loop",
    )
    allocated_ids: dict[str, list[str]] = {"agent_loop_run": [], "task": []}
    original_next_id = repository.next_id

    def capture_task_id(prefix: str) -> str:
        record_id = original_next_id(prefix)
        if prefix in allocated_ids:
            allocated_ids[prefix].append(record_id)
        return record_id

    monkeypatch.setattr(repository, "next_id", capture_task_id)

    def dispatch() -> dict[str, object] | Exception:
        try:
            return dispatch_ai_task_for_work_item(
                PostgresRuntimeStore(repository),
                collaboration_run_id=ids["run_id"],
                work_item_id=ids["work_item_id"],
            )
        except Exception as exc:  # noqa: BLE001 - preserve both concurrent outcomes
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: dispatch(), range(2)))

    persisted_task_ids = {
        str(task["id"])
        for task in repository.load_ai_tasks()["ai_tasks"].values()
        if task.get("work_item_id") == ids["work_item_id"]
    }
    losing_task_ids = set(allocated_ids["task"]) - persisted_task_ids
    for losing_task_id in losing_task_ids:
        _assert_no_autonomous_dispatch_records(
            repository,
            ai_task_id=losing_task_id,
        )

    assert all(isinstance(outcome, dict) for outcome in outcomes)
    results = [outcome for outcome in outcomes if isinstance(outcome, dict)]

    task_ids = {str(result["task"]["id"]) for result in results}
    attempt_ids = {str(result["attempt"]["id"]) for result in results}
    runner_task_ids = {str(result["runner_task"]["id"]) for result in results}
    assert len(task_ids) == len(attempt_ids) == len(runner_task_ids) == 1
    assert sorted(bool(result["idempotent_replay"]) for result in results) == [False, True]
    persisted_tasks = [
        task
        for task in repository.load_ai_tasks()["ai_tasks"].values()
        if task.get("work_item_id") == ids["work_item_id"]
        and task.get("status") in {"draft", "running", "waiting_more_info", "waiting_review"}
    ]
    assert len(persisted_tasks) == 1
    assert len(repository.list_rd_work_item_attempts(ids["work_item_id"])) == 1
    assert len(repository.list_ai_executor_tasks(ai_task_id=next(iter(task_ids)))) == 1
    winning_task_id = next(iter(task_ids))
    losing_task_ids = set(allocated_ids["task"]) - {winning_task_id}
    assert len(losing_task_ids) == 1
    manifests = repository.list_execution_context_manifests(
        subject_id=winning_task_id,
        subject_type="ai_task",
    )
    loop_runs = repository.list_agent_loop_runs(ai_task_id=winning_task_id)
    assert len(manifests) == len(loop_runs) == 1
    assert len(repository.list_agent_loop_iterations(loop_runs[0]["id"])) == 1
    assert (
        len(
            [
                ledger
                for ledger in repository.list_trusted_delivery_records(
                    record_type="agent_budget_ledger"
                )
                if ledger.get("ai_task_id") == winning_task_id
            ]
        )
        == 1
    )


def test_postgres_work_item_transition_rolls_back_task_attempt_event_and_audit(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(repository, prefix="work-item-transition-atomic")
    dispatched = dispatch_ai_task_for_work_item(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    task = {**dispatched["task"], "status": "failed", "current_step": "rework_required"}
    attempt = {**dispatched["attempt"], "status": "failed"}

    def fail_after_event(stage: str) -> None:
        if stage == "after_event":
            raise RuntimeError("inject transition rollback")

    with pytest.raises(RuntimeError, match="inject transition rollback"):
        repository.save_work_item_attempt_bundle(
            work_item_id=ids["work_item_id"],
            expected_statuses=["running"],
            next_status="rework_required",
            attempt=attempt,
            expected_version=2,
            task=task,
            event={
                "id": "work-item-transition-atomic-event",
                "collaboration_run_id": ids["run_id"],
                "event_type": "work_item.quality_gate_failed",
                "event_key": "work-item-transition-atomic-event",
                "subject_type": "rd_work_item",
                "subject_id": ids["work_item_id"],
                "payload_json": {},
            },
            audit_events=[
                {
                    "id": "work-item-transition-atomic-audit",
                    "event_type": "rd_work_item.quality_gate_failed",
                    "actor_id": "system",
                    "subject_type": "rd_work_item",
                    "subject_id": ids["work_item_id"],
                    "payload": {},
                }
            ],
            failure_injection=fail_after_event,
        )

    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "running"
    assert repository.get_rd_work_item_attempt(dispatched["attempt"]["id"])["status"] == "running"
    assert repository.load_ai_tasks()["ai_tasks"][dispatched["task"]["id"]]["status"] == "running"
    assert not any(
        event["id"] == "work-item-transition-atomic-event"
        for event in repository.list_rd_collaboration_events(ids["run_id"])
    )
    assert not any(
        event["id"] == "work-item-transition-atomic-audit"
        for event in repository.list_audit_events(
            subject_type="rd_work_item",
            subject_id=ids["work_item_id"],
        )
    )


def test_postgres_coding_completion_creates_gate_verifier_and_task_projection_together(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-completion-atomic",
        with_verifier=True,
    )
    dispatched = dispatch_ai_task_for_work_item(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    coding_runner = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])[0]
    coding_runner.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-18T00:00:00+00:00",
            "result_json": {"summary": "atomic implementation complete"},
        }
    )

    _sync_runner_completion_to_ai_task(
        PostgresRuntimeStore(repository),
        task=coding_runner,
        runner_id=coding_runner["runner_id"],
    )

    linked_tasks = repository.load_ai_tasks()["ai_tasks"]
    persisted_task = linked_tasks[dispatched["task"]["id"]]
    gates = repository.list_quality_gate_runs(
        subject_type="ai_task",
        subject_id=persisted_task["id"],
    )
    runner_tasks = repository.list_ai_executor_tasks(ai_task_id=persisted_task["id"])
    assert persisted_task["current_step"] == "quality_gate_running"
    assert len(gates) == 1
    assert len([task for task in runner_tasks if task["task_kind"] == "quality_gate"]) == 1


def test_postgres_approved_work_items_advance_delivery_phases_transactionally(
    repository: PostgresSnapshotRepository,
) -> None:
    """No caller or callback may set the R&D delivery phase directly."""
    prefix = "work-item-delivery-phases"
    ids = _seed_dispatchable_work_item(repository, prefix=prefix)
    integration_work_item_id = f"{prefix}-integration-work-item"
    repository.save_rd_work_item_record(
        {
            "id": integration_work_item_id,
            "collaboration_run_id": ids["run_id"],
            "requirement_id": f"{prefix}-requirement",
            "plan_version": 1,
            "work_item_type": "automated_testing",
            "title": "version integration",
            "objective": "run version integration tests",
            "owner_seat_id": f"{prefix}-owner",
            "reviewer_seat_id": f"{prefix}-reviewer",
            "status": "ready",
            "idempotency_key": integration_work_item_id,
        }
    )
    runtime = PostgresRuntimeStore(repository)

    coding = dispatch_ai_task_for_work_item(
        runtime,
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    project_work_item_quality_gate_result(
        runtime,
        ai_task_id=coding["task"]["id"],
        quality_gate_run={"id": f"{prefix}-coding-gate", "status": "passed"},
        runner_task_id=coding["runner_task"]["id"],
    )
    approve_work_item_after_task_review(
        runtime,
        ai_task_id=coding["task"]["id"],
        review_id=f"{prefix}-coding-review",
        actor_id="user_reviewer",
    )

    assert repository.get_rd_collaboration_run(ids["run_id"])["status"] == "integrating"

    integration = dispatch_ai_task_for_work_item(
        runtime,
        collaboration_run_id=ids["run_id"],
        work_item_id=integration_work_item_id,
    )
    project_work_item_quality_gate_result(
        runtime,
        ai_task_id=integration["task"]["id"],
        quality_gate_run={"id": f"{prefix}-integration-gate", "status": "passed"},
        runner_task_id=integration["runner_task"]["id"],
    )
    approve_work_item_after_task_review(
        runtime,
        ai_task_id=integration["task"]["id"],
        review_id=f"{prefix}-integration-review",
        actor_id="user_reviewer",
    )

    assert repository.get_rd_collaboration_run(ids["run_id"])["status"] == "verifying"
    phase_events = [
        event
        for event in repository.list_rd_collaboration_events(ids["run_id"])
        if event["event_type"] == "run.delivery_phase_advanced"
    ]
    assert [event["payload_json"]["to_status"] for event in phase_events] == [
        "integrating",
        "verifying",
    ]


def test_postgres_coding_runner_queues_push_and_only_signed_inbox_callback_reconciles(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The production Runner -> Outbox -> signed Inbox path has no deploy step."""
    from app.services.external_event_inbox import (
        process_external_event_inbox_events,
        receive_external_event,
    )
    from app.services.operational_deployments import process_execution_outbox_events
    from app.services.rd_git_delivery import record_version_git_delivery

    prefix = "work-item-git-delivery-e2e"
    repository_id = f"{prefix}-repository"
    now = datetime.now(UTC)
    approval = {
        "approval_id": f"{prefix}-git-push-approval",
        "approved": True,
        "approved_at": now.isoformat(),
        "approved_by": "user_admin",
        "approved_operations": ["git_push_or_merge"],
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "mode": "platform_human_approval",
        "policy_version": "runner_safety_v1",
    }
    ids = _seed_dispatchable_work_item(
        repository,
        prefix=prefix,
        with_verifier=True,
        git_config={
            "provider": "gitlab",
            "push_approval": approval,
            "repository_id": repository_id,
        },
    )
    project_path = f"example/{prefix}"
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO product_git_repositories (
              id, product_id, repo_type, name, remote_url, git_provider,
              project_path, default_branch, status
            ) VALUES (%s, %s, 'service', %s, %s, 'gitlab', %s, 'main', 'active')
            """,
            (
                repository_id,
                ids["product_id"],
                repository_id,
                f"https://git.example.test/{project_path}.git",
                project_path,
            ),
        )
        connection.execute(
            """
            INSERT INTO product_version_branch_configs (
              id, product_id, version_id, repository_id, base_branch, working_branch
            ) VALUES (%s, %s, %s, %s, 'main', 'release/rd-e2e')
            """,
            (f"{prefix}-branch", ids["product_id"], f"{prefix}-version", repository_id),
        )

    integration_work_item_id = f"{prefix}-integration-work-item"
    repository.save_rd_work_item_record(
        {
            "id": integration_work_item_id,
            "collaboration_run_id": ids["run_id"],
            "requirement_id": f"{prefix}-requirement",
            "plan_version": 1,
            "work_item_type": "automated_testing",
            "title": "version integration",
            "objective": "record trusted version integration evidence",
            "owner_seat_id": f"{prefix}-owner",
            "reviewer_seat_id": f"{prefix}-reviewer",
            "status": "ready",
            "idempotency_key": integration_work_item_id,
        }
    )

    runtime = PostgresRuntimeStore(repository)
    dispatched = dispatch_ai_task_for_work_item(
        runtime,
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    coding_runner = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])[0]
    local_sha = "local-commit-from-frozen-runner"
    coding_runner.update(
        {
            "status": "succeeded",
            "finished_at": now.isoformat(),
            "result_json": {
                "summary": "implementation complete",
                "git_delivery": {
                    "local_commit_sha": local_sha,
                    "working_branch": f"rd/{ids['run_id']}/{ids['work_item_id']}",
                },
            },
        }
    )
    _sync_runner_completion_to_ai_task(
        runtime,
        task=coding_runner,
        runner_id=coding_runner["runner_id"],
    )

    deliveries = repository.list_rd_delivery_evidence_records(record_type="rd_git_delivery")
    assert len(deliveries) == 1
    delivery = deliveries[0]
    assert delivery["local_commit_sha"] == local_sha
    assert delivery.get("remote_commit_sha") is None
    assert delivery["repository_id"] == repository_id
    assert delivery["working_branch"] == f"rd/{ids['run_id']}/{ids['work_item_id']}"
    outbox = repository.list_execution_outbox_events(
        aggregate_id=delivery["id"],
        aggregate_type="rd_git_delivery",
        status="pending",
    )
    assert len(outbox) == 1
    assert outbox[0]["payload"]["delivery_id"] == delivery["id"]
    assert outbox[0]["payload"]["local_commit_sha"] == local_sha

    processed_push = process_execution_outbox_events(runtime, worker_id="rd-delivery-worker")
    push_events = repository.list_execution_outbox_events(
        aggregate_id=delivery["id"],
        aggregate_type="rd_git_delivery",
    )
    assert processed_push == 1, {
        key: push_events[0].get(key) for key in ("status", "last_error", "payload", "attempt_count")
    }
    push_task = next(
        task
        for task in repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])
        if task["task_kind"] == "git_push"
    )
    assert push_task["input_payload"]["local_commit_sha"] == local_sha
    assert "remote_commit_sha" not in push_task["input_payload"]
    assert push_task["task_kind"] == "git_push"
    assert "do not amend, reset, rebase, merge, deploy" in push_task["instruction"].lower()
    assert repository.list_execution_outbox_events(aggregate_type="deployment_request") == []

    # Phase progression is owned by the normal work-item quality/review path,
    # not by the later Git callback or a direct database mutation.
    project_work_item_quality_gate_result(
        runtime,
        ai_task_id=dispatched["task"]["id"],
        quality_gate_run={"id": f"{prefix}-coding-gate", "status": "passed"},
        runner_task_id=dispatched["runner_task"]["id"],
    )
    approve_work_item_after_task_review(
        runtime,
        ai_task_id=dispatched["task"]["id"],
        review_id=f"{prefix}-coding-review",
        actor_id="user_reviewer",
    )
    assert repository.get_rd_collaboration_run(ids["run_id"])["status"] == "integrating"

    repository.save_plugin_record(
        {
            "id": "plugin_standard_gitlab",
            "code": "gitlab",
            "name": "GitLab callback",
            "protocol": "http",
            "status": "active",
            "created_by": "user_admin",
        }
    )
    repository.save_plugin_connection_record(
        {
            "id": f"{prefix}-gitlab-connection",
            "plugin_id": "plugin_standard_gitlab",
            "name": "GitLab callback",
            "endpoint_url": "https://git.example.test/hooks",
            "auth_config": {"webhook_secret_ref": "env:RD_GITLAB_E2E_WEBHOOK_SECRET"},
            "status": "active",
            "created_by": "user_admin",
        }
    )
    monkeypatch.setenv("RD_GITLAB_E2E_WEBHOOK_SECRET", "rd-delivery-e2e-secret")
    body = json.dumps(
        {
            "project": {"path_with_namespace": project_path},
            "after": local_sha,
            "ref": f"refs/heads/rd/{ids['run_id']}/{ids['work_item_id']}",
            "ai_brain": {"rd_delivery_id": delivery["id"]},
        }
    ).encode()
    callback = receive_external_event(
        runtime,
        body=body,
        connection_id=f"{prefix}-gitlab-connection",
        headers={
            "x-gitlab-event-uuid": f"{prefix}-provider-callback",
            "x-gitlab-event": "Push Hook",
            "x-gitlab-token": "rd-delivery-e2e-secret",
        },
        provider="gitlab",
    )
    assert callback["signature_status"] == "verified"
    processed_callback = process_external_event_inbox_events(runtime, worker_id="rd-inbox-worker")
    inbox_events = repository.list_external_event_inbox()
    assert processed_callback == 0, {
        key: inbox_events[0].get(key)
        for key in ("status", "error_message", "signature_status", "payload")
    }

    reconciliations = repository.list_rd_delivery_evidence_records(
        record_type="rd_git_delivery_reconciliation"
    )
    assert len(reconciliations) == 1
    assert reconciliations[0]["delivery_id"] == delivery["id"]
    assert reconciliations[0]["remote_commit_sha"] == local_sha
    assert reconciliations[0]["provider_callback_event_id"] == callback["id"]
    assert reconciliations[0]["provider_callback_product_id"] == ids["product_id"]
    assert reconciliations[0]["provider_callback_repository_id"] == repository_id
    assert reconciliations[0]["provider_callback_ref"] == (
        f"rd/{ids['run_id']}/{ids['work_item_id']}"
    )
    persisted_callback = repository.get_external_event_inbox(callback["id"])
    assert persisted_callback is not None
    assert persisted_callback["status"] == "pending"
    assert persisted_callback["error_message"] == "RD_DELIVERY_EVIDENCE_INCOMPLETE"
    assert persisted_callback["lease_until"] is not None
    assert persisted_callback["payload"]["_context"] == {
        "connection_id": f"{prefix}-gitlab-connection",
        "environment": None,
        "product_id": ids["product_id"],
        "repository_id": repository_id,
        "repository_provider": "gitlab",
        "repository_ref": f"rd/{ids['run_id']}/{ids['work_item_id']}",
        "version_id": None,
    }

    # A signed event with the same delivery id and SHA but another branch must
    # not advance this delivery or create readiness evidence.
    wrong_ref_callback = receive_external_event(
        runtime,
        body=json.dumps(
            {
                "project": {"path_with_namespace": project_path},
                "after": local_sha,
                "ref": "refs/heads/main",
                "ai_brain": {"rd_delivery_id": delivery["id"]},
            }
        ).encode(),
        connection_id=f"{prefix}-gitlab-connection",
        headers={
            "x-gitlab-event-uuid": f"{prefix}-provider-callback-wrong-ref",
            "x-gitlab-event": "Push Hook",
            "x-gitlab-token": "rd-delivery-e2e-secret",
        },
        provider="gitlab",
    )
    assert process_external_event_inbox_events(runtime, worker_id="rd-inbox-worker") == 0
    wrong_ref = repository.get_external_event_inbox(wrong_ref_callback["id"])
    assert wrong_ref is not None and wrong_ref["status"] == "failed"
    assert repository.get_rd_collaboration_run(ids["run_id"])["status"] == "integrating"

    integration_task = dispatch_ai_task_for_work_item(
        runtime,
        collaboration_run_id=ids["run_id"],
        work_item_id=integration_work_item_id,
    )
    project_work_item_quality_gate_result(
        runtime,
        ai_task_id=integration_task["task"]["id"],
        quality_gate_run={"id": f"{prefix}-integration-gate", "status": "passed"},
        runner_task_id=integration_task["runner_task"]["id"],
    )
    approve_work_item_after_task_review(
        runtime,
        ai_task_id=integration_task["task"]["id"],
        review_id=f"{prefix}-integration-review",
        actor_id="user_reviewer",
    )
    assert repository.get_rd_collaboration_run(ids["run_id"])["status"] == "verifying"

    integration = record_version_git_delivery(
        runtime,
        collaboration_run_id=ids["run_id"],
        work_item_id=integration_work_item_id,
        repository_id=repository_id,
        provider="gitlab",
        working_branch="release/rd-e2e",
        version_branch="release/rd-e2e",
        target_branch="main",
        local_commit_sha=local_sha,
        test_evidence={"suite": "version-integration", "status": "passed"},
    )
    integration_callback = receive_external_event(
        runtime,
        body=json.dumps(
            {
                "project": {"path_with_namespace": project_path},
                "after": local_sha,
                "ref": "refs/heads/release/rd-e2e",
                "ai_brain": {"rd_delivery_id": integration["delivery"]["id"]},
            }
        ).encode(),
        connection_id=f"{prefix}-gitlab-connection",
        headers={
            "x-gitlab-event-uuid": f"{prefix}-integration-callback",
            "x-gitlab-event": "Push Hook",
            "x-gitlab-token": "rd-delivery-e2e-secret",
        },
        provider="gitlab",
    )
    assert process_external_event_inbox_events(runtime, worker_id="rd-inbox-worker") == 1
    assert repository.get_external_event_inbox(integration_callback["id"])["status"] == "completed"
    completed_run = repository.get_rd_collaboration_run(ids["run_id"])
    assert completed_run is not None
    assert completed_run["status"] == "completed"
    assert completed_run["completion_reason"] == "ready_for_release"
    assert repository.get_product_version(f"{prefix}-version")["status"] == "ready_for_release"
    assert (
        len(
            repository.list_rd_delivery_evidence_records(
                record_type="rd_ready_for_release_evidence"
            )
        )
        == 1
    )
    assert repository.list_execution_outbox_events(aggregate_type="deployment_request") == []


def test_postgres_cancel_after_accepted_completion_cancels_verifier_runner(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-completion-cancel-after-commit",
        with_verifier=True,
    )
    dispatched = dispatch_ai_task_for_work_item(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    coding_runner = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])[0]
    coding_runner.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-18T00:00:00+00:00",
            "result_json": {"summary": "completion accepted before cancellation"},
        }
    )
    _sync_runner_completion_to_ai_task(
        PostgresRuntimeStore(repository),
        task=coding_runner,
        runner_id=coding_runner["runner_id"],
    )

    repository.cancel_work_item_bundle(
        work_item_id=ids["work_item_id"],
        expected_version=2,
        high_risk=False,
    )

    runner_tasks = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])
    verifier = next(task for task in runner_tasks if task["task_kind"] == "quality_gate")
    assert repository.load_ai_tasks()["ai_tasks"][dispatched["task"]["id"]]["status"] == "cancelled"
    assert verifier["status"] == "cancelled"


def test_postgres_completion_bundle_rolls_back_gate_verifier_and_task_together(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-completion-bundle-rollback",
        with_verifier=True,
    )
    dispatched = dispatch_ai_task_for_work_item(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    coding_runner = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])[0]
    coding_runner.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-18T00:00:00+00:00",
            "result_json": {"summary": "completion that must roll back"},
        }
    )
    governance_writes = repository._execution_governance_read_repository._write_repository

    def fail_gate_checks(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("inject completion bundle rollback")

    monkeypatch.setattr(governance_writes, "upsert_quality_gate_checks", fail_gate_checks)

    with pytest.raises(RuntimeError, match="inject completion bundle rollback"):
        _sync_runner_completion_to_ai_task(
            PostgresRuntimeStore(repository),
            task=coding_runner,
            runner_id=coding_runner["runner_id"],
        )

    persisted_task = repository.load_ai_tasks()["ai_tasks"][dispatched["task"]["id"]]
    runner_tasks = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])
    assert persisted_task["current_step"] == "waiting_ai_executor"
    assert len(runner_tasks) == 1
    assert runner_tasks[0]["status"] == "queued"
    assert runner_tasks[0]["result_json"] == {}
    assert (
        repository.list_quality_gate_runs(
            subject_type="ai_task",
            subject_id=dispatched["task"]["id"],
        )
        == []
    )


def test_postgres_cancel_wins_completion_race_without_orphan_gate_or_verifier(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-completion-cancel-race",
        with_verifier=True,
    )
    dispatched = dispatch_ai_task_for_work_item(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    coding_runner = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])[0]
    coding_runner.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-18T00:00:00+00:00",
            "result_json": {"summary": "completion racing cancellation"},
        }
    )
    cancel_has_run_lock = Event()
    release_cancel = Event()
    original_cancel = repository._cancel_work_item_bundle_cursor
    errors: list[BaseException] = []

    def hold_cancel_run_lock(cursor, **kwargs):  # type: ignore[no-untyped-def]
        cursor.execute(
            "SELECT id FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
            (ids["run_id"],),
        )
        cancel_has_run_lock.set()
        assert release_cancel.wait(timeout=5)
        return original_cancel(cursor, **kwargs)

    monkeypatch.setattr(repository, "_cancel_work_item_bundle_cursor", hold_cancel_run_lock)

    def cancel() -> None:
        try:
            repository.cancel_work_item_bundle(
                work_item_id=ids["work_item_id"],
                expected_version=2,
                high_risk=False,
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def complete() -> None:
        try:
            _sync_runner_completion_to_ai_task(
                PostgresRuntimeStore(repository),
                task=coding_runner,
                runner_id=coding_runner["runner_id"],
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    cancelling = Thread(target=cancel)
    cancelling.start()
    assert cancel_has_run_lock.wait(timeout=5)
    completing = Thread(target=complete)
    completing.start()
    release_cancel.set()
    cancelling.join(timeout=10)
    completing.join(timeout=10)

    assert not errors
    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "cancelled"
    assert repository.load_ai_tasks()["ai_tasks"][dispatched["task"]["id"]]["status"] == "cancelled"
    assert (
        repository.list_quality_gate_runs(
            subject_type="ai_task",
            subject_id=dispatched["task"]["id"],
        )
        == []
    )
    runner_tasks = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])
    assert [task for task in runner_tasks if task["task_kind"] == "quality_gate"] == []
    fences = [
        event
        for event in repository.list_rd_collaboration_events(ids["run_id"])
        if event["event_type"] == "work_item.runner_result_fenced"
    ]
    audits = repository.list_audit_events(
        subject_type="rd_work_item",
        subject_id=ids["work_item_id"],
    )
    assert len(fences) == 1
    assert (
        len(
            [
                event
                for event in audits
                if event["event_type"] == "rd_work_item.runner_result_fenced"
            ]
        )
        == 1
    )


def test_postgres_runner_complete_http_race_is_fenced_after_cancel(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-http-completion-cancel-race",
        with_verifier=True,
    )
    original_store = app.state.store
    app.state.store = PostgresRuntimeStore(repository)
    try:
        dispatched = dispatch_ai_task_for_work_item(
            app.state.store,
            collaboration_run_id=ids["run_id"],
            work_item_id=ids["work_item_id"],
        )
        coding_runner = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])[0]
        cancel_has_run_lock = Event()
        completion_reached_bundle = Event()
        release_cancel = Event()
        original_cancel = repository._cancel_work_item_bundle_cursor
        original_complete = repository.complete_work_item_coding_bundle
        errors: list[BaseException] = []
        responses = []

        def hold_cancel_run_lock(cursor, **kwargs):  # type: ignore[no-untyped-def]
            cursor.execute(
                "SELECT id FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                (ids["run_id"],),
            )
            cancel_has_run_lock.set()
            assert release_cancel.wait(timeout=5)
            return original_cancel(cursor, **kwargs)

        monkeypatch.setattr(repository, "_cancel_work_item_bundle_cursor", hold_cancel_run_lock)

        def observe_completion_bundle(**kwargs):  # type: ignore[no-untyped-def]
            completion_reached_bundle.set()
            return original_complete(**kwargs)

        monkeypatch.setattr(
            repository,
            "complete_work_item_coding_bundle",
            observe_completion_bundle,
        )

        def cancel() -> None:
            try:
                repository.cancel_work_item_bundle(
                    work_item_id=ids["work_item_id"],
                    expected_version=2,
                    high_risk=False,
                )
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        def complete_over_http() -> None:
            try:
                client = TestClient(app)
                responses.append(
                    client.post(
                        f"/api/system/ai-executor-tasks/{coding_runner['id']}/complete",
                        headers={"Authorization": "Bearer rd-work-item-runner"},
                        json={
                            "runner_id": coding_runner["runner_id"],
                            "status": "succeeded",
                            "result_json": {"summary": "HTTP completion racing cancellation"},
                        },
                    )
                )
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        cancelling = Thread(target=cancel)
        cancelling.start()
        assert cancel_has_run_lock.wait(timeout=5)
        completing = Thread(target=complete_over_http)
        completing.start()
        assert completion_reached_bundle.wait(timeout=5)
        release_cancel.set()
        cancelling.join(timeout=10)
        completing.join(timeout=10)

        assert not errors
        assert len(responses) == 1 and responses[0].status_code == 200
        assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "cancelled"
        assert (
            repository.load_ai_tasks()["ai_tasks"][dispatched["task"]["id"]]["status"]
            == "cancelled"
        )
        assert (
            repository.list_quality_gate_runs(
                subject_type="ai_task",
                subject_id=dispatched["task"]["id"],
            )
            == []
        )
        runner_tasks = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])
        assert [task for task in runner_tasks if task["task_kind"] == "quality_gate"] == []
        fences = [
            event
            for event in repository.list_rd_collaboration_events(ids["run_id"])
            if event["event_type"] == "work_item.runner_result_fenced"
        ]
        assert len(fences) == 1
    finally:
        app.state.store = original_store


def test_postgres_suspend_wins_completion_race_without_creating_gate_or_verifier(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-completion-suspend-race",
        with_verifier=True,
    )
    dispatched = dispatch_ai_task_for_work_item(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    coding_runner = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])[0]
    coding_runner.update(
        {
            "status": "succeeded",
            "finished_at": "2026-07-18T00:00:00+00:00",
            "result_json": {"summary": "completion racing suspension"},
        }
    )
    decision_id = "work-item-completion-suspend-race-decision"
    repository.save_decision_request_record(
        _decision_record(
            {"product": ids["product_id"], "run": {"id": ids["run_id"]}},
            decision_id=decision_id,
        )
    )
    suspend_has_run_lock = Event()
    release_suspend = Event()
    original_suspend = repository._suspend_collaboration_run_cursor
    errors: list[BaseException] = []

    def hold_suspend_run_lock(cursor, **kwargs):  # type: ignore[no-untyped-def]
        cursor.execute(
            "SELECT id FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
            (ids["run_id"],),
        )
        suspend_has_run_lock.set()
        assert release_suspend.wait(timeout=5)
        return original_suspend(cursor, **kwargs)

    monkeypatch.setattr(repository, "_suspend_collaboration_run_cursor", hold_suspend_run_lock)

    def suspend() -> None:
        try:
            repository.suspend_collaboration_run(
                collaboration_run_id=ids["run_id"],
                decision_request_id=decision_id,
                expected_version=1,
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def complete() -> None:
        try:
            _sync_runner_completion_to_ai_task(
                PostgresRuntimeStore(repository),
                task=coding_runner,
                runner_id=coding_runner["runner_id"],
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    suspending = Thread(target=suspend)
    suspending.start()
    assert suspend_has_run_lock.wait(timeout=5)
    completing = Thread(target=complete)
    completing.start()
    release_suspend.set()
    suspending.join(timeout=10)
    completing.join(timeout=10)

    assert not errors
    assert repository.get_rd_collaboration_run(ids["run_id"])["status"] == "waiting_human"
    assert (
        repository.list_quality_gate_runs(
            subject_type="ai_task",
            subject_id=dispatched["task"]["id"],
        )
        == []
    )
    runner_tasks = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])
    assert [task for task in runner_tasks if task["task_kind"] == "quality_gate"] == []
    fences = [
        event
        for event in repository.list_rd_collaboration_events(ids["run_id"])
        if event["event_type"] == "work_item.runner_result_fenced"
    ]
    assert len(fences) == 1


def test_postgres_cancelled_work_item_fences_late_coding_completion_once(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(repository, prefix="work-item-late-fence")
    dispatched = dispatch_ai_task_for_work_item(
        PostgresRuntimeStore(repository),
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    repository.cancel_work_item_bundle(
        work_item_id=ids["work_item_id"],
        expected_version=2,
        high_risk=False,
    )
    late_runner_task = repository.list_ai_executor_tasks(ai_task_id=dispatched["task"]["id"])[0]
    late_runner_task.update({"status": "succeeded", "result_json": {"summary": "late completion"}})
    store = PostgresRuntimeStore(repository)

    _sync_runner_completion_to_ai_task(
        store,
        task=late_runner_task,
        runner_id=late_runner_task["runner_id"],
    )
    _sync_runner_completion_to_ai_task(
        store,
        task=late_runner_task,
        runner_id=late_runner_task["runner_id"],
    )

    fences = [
        event
        for event in repository.list_rd_collaboration_events(ids["run_id"])
        if event["event_type"] == "work_item.runner_result_fenced"
    ]
    assert len(fences) == 1
    assert fences[0]["payload_json"]["reason"] == "attempt_not_currently_running"
    assert repository.get_rd_work_item(ids["work_item_id"])["status"] == "cancelled"
    assert repository.load_ai_tasks()["ai_tasks"][dispatched["task"]["id"]]["status"] == "cancelled"


def test_postgres_dispatch_keeps_second_item_ready_when_the_frozen_seat_is_full(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(
        repository,
        prefix="work-item-seat-capacity",
        seat_capacity=1,
    )
    second_work_item_id = "work-item-seat-capacity-second"
    repository.save_rd_work_item_record(
        {
            "id": second_work_item_id,
            "collaboration_run_id": ids["run_id"],
            "requirement_id": ids["requirement_id"],
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "second capacity-bound work item",
            "objective": "verify atomic seat capacity enforcement",
            "owner_seat_id": ids["owner_seat_id"],
            "reviewer_seat_id": "work-item-seat-capacity-reviewer",
            "status": "ready",
            "idempotency_key": second_work_item_id,
        }
    )
    store = PostgresRuntimeStore(repository)

    dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id=ids["run_id"],
        work_item_id=ids["work_item_id"],
    )
    with pytest.raises(HTTPException) as exc_info:
        dispatch_ai_task_for_work_item(
            store,
            collaboration_run_id=ids["run_id"],
            work_item_id=second_work_item_id,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "RD_SEAT_CAPACITY_EXHAUSTED"
    assert repository.get_rd_work_item(second_work_item_id)["status"] == "ready"
    assert repository.list_rd_work_item_attempts(second_work_item_id) == []
