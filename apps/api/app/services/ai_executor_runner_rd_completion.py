"""Atomic v2 Runner-completion and review projections.

The generic Runner API remains in :mod:`ai_executor_runners`; these helpers
keep the collaboration-specific transaction boundary small enough to audit.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.services.agent_autonomy import record_agent_coding_completed
from app.services.ai_executor_runner_persistence import (
    _existing_pending_review,
    _memory_collection,
    _persist_task_state_records,
)
from app.services.operational_records import record_audit_event
from app.services.quality_gates import start_pre_merge_quality_gate
from app.services.rd_git_delivery import record_version_git_delivery_from_runner
from app.services.rd_work_item_execution import is_rd_collaboration_task
from app.services.task_output_summary import readable_task_output_summary
from app.services.task_persistence_helpers import record_audit_event as record_task_audit_event


def move_ai_task_to_executor_review(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    actor_id: str,
    executor_snapshot: dict[str, Any],
    output_json: dict[str, Any],
    quality_gate_run: dict[str, Any] | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    review_output = (
        {**output_json, "quality_gate": quality_gate_run}
        if quality_gate_run is not None
        else output_json
    )
    updated_task = {
        **ai_task,
        "current_step": "executor_completed",
        "output_json": review_output,
        "status": "waiting_review",
        "updated_at": now,
    }
    reviews: list[dict[str, Any]] = []
    existing_review = _existing_pending_review(
        current_store,
        updated_task["id"],
        str(updated_task.get("task_type") or "executor_result"),
    )
    if existing_review is None:
        review_id = current_store.new_id("review")
        reviews.append(
            {
                "ai_task_id": updated_task["id"],
                "content": review_output,
                "created_at": now,
                "decided_at": None,
                "decided_by": None,
                "decision_reason": None,
                "id": review_id,
                "questions": [],
                "stage": updated_task.get("task_type") or "executor_result",
                "status": "pending",
                "updated_at": now,
                "version": 1,
            }
        )
    review_ids = list(updated_task.get("review_ids") or [])
    for review in reviews or ([existing_review] if existing_review else []):
        if review and review["id"] not in review_ids:
            review_ids.append(review["id"])
    updated_task["review_ids"] = review_ids
    audit_event = record_audit_event(
        current_store,
        event_type="ai_task.executor_completed",
        actor_id=actor_id,
        subject_type="ai_task",
        subject_id=updated_task["id"],
        payload={
            "ai_task_id": updated_task["id"],
            **executor_snapshot,
            "quality_gate_run_id": (quality_gate_run or {}).get("id"),
            "quality_gate_status": (quality_gate_run or {}).get("status"),
        },
    )
    _persist_task_state_records(
        current_store,
        audit_events=[audit_event],
        reviews=reviews or None,
        task=updated_task,
    )


def complete_rd_coding_runner_atomically(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    coding_runner_task: dict[str, Any],
    runner_id: str,
    resolve_executor_policy: Callable[[Any, dict[str, Any]], dict[str, Any] | None],
) -> bool:
    """Persist a v2 coding completion and its gate/verifier in one transaction."""
    if (
        not is_rd_collaboration_task(ai_task)
        or coding_runner_task.get("task_kind") not in {None, "", "coding"}
        or coding_runner_task.get("status") != "succeeded"
    ):
        return False
    repository = getattr(current_store, "repository", None)
    complete_bundle = getattr(repository, "complete_work_item_coding_bundle", None)
    if not callable(complete_bundle):
        return False
    input_json = ai_task.get("input_json") if isinstance(ai_task.get("input_json"), dict) else {}
    collaboration = (
        input_json.get("rd_collaboration")
        if isinstance(input_json.get("rd_collaboration"), dict)
        else {}
    )
    attempt_id = str(
        (coding_runner_task.get("input_payload") or {}).get("rd_work_item_attempt_id")
        or collaboration.get("attempt_id")
        or ""
    ).strip()
    work_item_id = str(ai_task.get("work_item_id") or "").strip()
    run_id = str(ai_task.get("collaboration_run_id") or "").strip()
    if not attempt_id or not work_item_id or not run_id:
        return False

    runner_status = str(coding_runner_task.get("status") or "")
    executor_snapshot = {
        "executor_type": coding_runner_task.get("executor_type"),
        "runner_id": coding_runner_task.get("runner_id"),
        "runner_task_id": coding_runner_task.get("id"),
        "status": runner_status,
        "workspace_root": coding_runner_task.get("workspace_root"),
    }
    output_json = {
        "executor": {
            **executor_snapshot,
            "finished_at": coding_runner_task.get("finished_at"),
        },
        "result": coding_runner_task.get("result_json") or {},
    }
    output_summary = readable_task_output_summary(output_json)
    if output_summary:
        output_json["summary"] = output_summary
    prepared = start_pre_merge_quality_gate(
        current_store,
        ai_task=ai_task,
        coding_runner_task=coding_runner_task,
        executor_policy=resolve_executor_policy(current_store, ai_task),
        persist=False,
        return_bundle=True,
    )
    quality_gate_run, verifier_task, quality_gate_checks, quality_gate_audit = prepared
    verifier_task = {
        **verifier_task,
        "input_payload": {
            **dict(verifier_task.get("input_payload") or {}),
            "rd_collaboration_run_id": run_id,
            "rd_work_item_attempt_id": attempt_id,
            "rd_work_item_id": work_item_id,
        },
        "request_config": {
            **dict(verifier_task.get("request_config") or {}),
            "rd_collaboration_run_id": run_id,
            "rd_work_item_attempt_id": attempt_id,
            "rd_work_item_id": work_item_id,
        },
    }
    now = datetime.now(UTC).isoformat()
    updated_task = {
        **ai_task,
        "current_step": "quality_gate_running",
        "input_json": {
            **input_json,
            "executor": executor_snapshot,
            "quality_gate": {
                "id": quality_gate_run["id"],
                "status": quality_gate_run["status"],
                "verifier_runner_task_id": verifier_task["id"],
            },
        },
        "output_json": output_json,
        "status": "running",
        "updated_at": now,
    }
    runner_completion_audit = record_audit_event(
        current_store,
        event_type="ai_executor_task.succeeded",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=coding_runner_task["id"],
        payload={
            "executor_type": coding_runner_task["executor_type"],
            "runner_id": runner_id,
            "scheduled_job_id": coding_runner_task.get("scheduled_job_id"),
            "scheduled_job_run_id": coding_runner_task.get("scheduled_job_run_id"),
            "status": runner_status,
        },
    )
    verifier_queued_audit = record_audit_event(
        current_store,
        event_type="ai_executor_task.queued",
        actor_id=str(ai_task.get("created_by") or "system"),
        subject_type="ai_executor_task",
        subject_id=verifier_task["id"],
        payload={
            "ai_task_id": ai_task["id"],
            "executor_type": verifier_task["executor_type"],
            "runner_id": verifier_task.get("runner_id"),
            "task_kind": "quality_gate",
        },
    )
    gate_started_audit = record_audit_event(
        current_store,
        event_type="ai_task.quality_gate_started",
        actor_id=runner_id,
        subject_type="ai_task",
        subject_id=updated_task["id"],
        payload={
            "ai_task_id": updated_task["id"],
            "coding_runner_task_id": coding_runner_task["id"],
            "quality_gate_run_id": quality_gate_run["id"],
            "verifier_runner_task_id": verifier_task["id"],
        },
    )
    fence_event = {
        "id": current_store.new_id("rd_collaboration_event"),
        "collaboration_run_id": run_id,
        "event_type": "work_item.runner_result_fenced",
        "event_key": (
            f"work-item-runner-fenced:{work_item_id}:{attempt_id}:{coding_runner_task['id']}"
        ),
        "subject_type": "rd_work_item",
        "subject_id": work_item_id,
        "payload_json": {},
        "occurred_at": now,
    }
    fence_audit_event = record_task_audit_event(
        current_store,
        event_type="rd_work_item.runner_result_fenced",
        actor_id="system",
        ai_task_id=ai_task["id"],
        subject_type="rd_work_item",
        subject_id=work_item_id,
        payload={},
    )
    result = complete_bundle(
        collaboration_run_id=run_id,
        work_item_id=work_item_id,
        attempt_id=attempt_id,
        ai_task=updated_task,
        coding_runner_task=coding_runner_task,
        quality_gate_run=quality_gate_run,
        quality_gate_checks=quality_gate_checks,
        verifier_runner_task=verifier_task,
        audit_events=[
            runner_completion_audit,
            quality_gate_audit,
            verifier_queued_audit,
            gate_started_audit,
        ],
        fence_event=fence_event,
        fence_audit_event=fence_audit_event,
    )
    _memory_collection(current_store, "ai_executor_tasks")[coding_runner_task["id"]] = dict(
        coding_runner_task
    )
    if result.get("fenced"):
        return True
    _memory_collection(current_store, "ai_executor_tasks")[verifier_task["id"]] = dict(
        verifier_task
    )
    _memory_collection(current_store, "quality_gate_runs")[quality_gate_run["id"]] = dict(
        quality_gate_run
    )
    for check in quality_gate_checks:
        _memory_collection(current_store, "quality_gate_checks")[check["id"]] = dict(check)
    _memory_collection(current_store, "ai_tasks")[updated_task["id"]] = dict(updated_task)
    # A successful Runner can create only a *local* delivery fact.  This
    # queues a remote-push intent from frozen execution context; it deliberately
    # does not accept a remote SHA from the Runner or advance release state.
    record_version_git_delivery_from_runner(
        current_store,
        ai_task=updated_task,
        runner_task=coding_runner_task,
    )
    record_agent_coding_completed(
        current_store,
        coding_runner_task=coding_runner_task,
        quality_gate_run_id=quality_gate_run["id"],
        verifier_runner_task_id=verifier_task["id"],
    )
    return True
