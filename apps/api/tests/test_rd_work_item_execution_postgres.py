from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256

import pytest

from app.core.persistence import PostgresRuntimeStore, PostgresSnapshotRepository
from app.services.ai_executor_runners import _sync_runner_completion_to_ai_task
from app.services.task_start_execution import dispatch_ai_task_for_work_item
from tests.test_rd_collaboration_repository import (
    _accepted_assessment,
    _base_snapshot,
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
        "autonomy_config": {"mode": "single_pass", "timeout_seconds": 60},
        "git_config": {"workspace_root": "/srv/rd-work"},
        "quality_gate_config": {"code_change_review_mode": "manual_review"},
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
    }


def test_postgres_dispatch_rolls_back_task_runner_attempt_event_and_audit_together(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _seed_dispatchable_work_item(repository, prefix="work-item-atomic-rollback")

    def fail_runner_insert(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("inject runner insert failure")

    monkeypatch.setattr(repository, "upsert_ai_executor_tasks", fail_runner_insert)

    with pytest.raises(RuntimeError, match="inject runner insert failure"):
        dispatch_ai_task_for_work_item(
            PostgresRuntimeStore(repository),
            collaboration_run_id=ids["run_id"],
            work_item_id=ids["work_item_id"],
        )

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


def test_concurrent_postgres_dispatch_reuses_one_active_task_attempt_and_runner(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _seed_dispatchable_work_item(repository, prefix="work-item-atomic-concurrent")

    def dispatch() -> dict[str, object]:
        return dispatch_ai_task_for_work_item(
            PostgresRuntimeStore(repository),
            collaboration_run_id=ids["run_id"],
            work_item_id=ids["work_item_id"],
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: dispatch(), range(2)))

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
    late_runner_task.update(
        {"status": "succeeded", "result_json": {"summary": "late completion"}}
    )
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
