from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.ai_executor_runner_persistence import _memory_collection
from app.services.quality_gates import quality_gate_allows_auto_merge
from app.services.task_graph_runtime import latest_graph_run, transition_latest_graph_run
from app.services.task_persistence_helpers import (
    record_audit_event as record_task_audit_event,
)
from app.services.task_persistence_helpers import save_review_decision_records
from app.services.task_review_artifacts import (
    advance_requirement_after_task_completed,
    confirm_code_review_report,
    create_automated_testing_bugs,
    create_knowledge_deposit,
    create_post_release_bugs,
)
from app.services.task_workflow_context import task_workflow_write_store


def complete_ai_task_with_auto_commit(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    executor_snapshot: dict[str, Any],
    output_json: dict[str, Any],
    policy: dict[str, Any] | None,
    quality_gate_run: dict[str, Any] | None,
    runner_id: str,
) -> bool:
    if (
        str((policy or {}).get("code_change_review_mode") or "manual_review")
        != "auto_commit"
        or quality_gate_run is None
        or not quality_gate_allows_auto_merge(quality_gate_run)
    ):
        return False

    write_store = task_workflow_write_store(current_store)
    task = write_store.ai_tasks.get(ai_task["id"], dict(ai_task))
    now = datetime.now(UTC).isoformat()
    review_id = current_store.new_id("review")
    review = {
        "ai_task_id": task["id"],
        "content": output_json,
        "created_at": now,
        "decided_at": now,
        "decided_by": "system",
        "decision_reason": "auto_commit_by_executor_policy",
        "id": review_id,
        "questions": [],
        "stage": task.get("task_type") or "executor_result",
        "status": "approved",
        "updated_at": now,
        "version": 1,
    }
    if getattr(write_store, "repository", None) is None:
        _memory_collection(write_store, "human_reviews")[review_id] = review
    review_ids = list(task.get("review_ids") or [])
    if review_id not in review_ids:
        review_ids.append(review_id)
    task.update(
        {
            "current_step": "executor_completed",
            "output_json": output_json,
            "review_ids": review_ids,
            "status": "completed",
            "updated_at": now,
        }
    )

    audit_start_index = len(write_store.audit_events)
    record_task_audit_event(
        write_store,
        event_type="ai_task.executor_completed",
        actor_id=runner_id,
        ai_task_id=task["id"],
        subject_type="ai_task",
        subject_id=task["id"],
        payload={
            "ai_task_id": task["id"],
            **executor_snapshot,
            "code_change_review_mode": "auto_commit",
            "executor_policy_id": (policy or {}).get("id"),
            "quality_gate_run_id": quality_gate_run["id"],
        },
    )
    from app.services.ai_executor_workspace_isolation import (
        mark_ai_executor_workspace_isolation_decision,
    )

    mark_ai_executor_workspace_isolation_decision(
        current_store,
        action="merge",
        decided_by="system",
        reason="auto_commit_by_executor_policy",
        task=task,
    )
    confirm_code_review_report(write_store, task)
    created_bug_ids = [
        *create_automated_testing_bugs(write_store, actor_id="system", task=task),
        *create_post_release_bugs(write_store, actor_id="system", task=task),
    ]
    advance_requirement_after_task_completed(write_store, task)
    knowledge_deposit = create_knowledge_deposit(write_store, task)
    checkpoint = transition_latest_graph_run(
        write_store,
        task=task,
        status="completed",
        current_step="complete_archive",
        state_snapshot={
            "code_change_review_mode": "auto_commit",
            "quality_gate_run_id": quality_gate_run["id"],
            "review_id": review_id,
            "task_status": task["status"],
        },
    )
    record_task_audit_event(
        write_store,
        event_type="review.submitted",
        actor_id="system",
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={
            "code_change_review_mode": "auto_commit",
            "decision": "approved",
            "executor_policy_id": (policy or {}).get("id"),
            "quality_gate_run_id": quality_gate_run["id"],
        },
    )
    record_task_audit_event(
        write_store,
        event_type="ai_task.executor_auto_committed",
        actor_id="system",
        ai_task_id=task["id"],
        subject_type="ai_task",
        subject_id=task["id"],
        payload={
            "executor_policy_id": (policy or {}).get("id"),
            "quality_gate_run_id": quality_gate_run["id"],
            "runner_id": runner_id,
            "runner_task_id": executor_snapshot.get("runner_task_id"),
        },
    )
    graph_run = latest_graph_run(write_store, task)
    requirement = write_store.requirements.get(task.get("requirement_id"))
    code_review_report = (
        write_store.code_review_reports.get(task.get("code_review_report_id"))
        if task.get("code_review_report_id")
        else None
    )
    save_review_decision_records(
        write_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        requirement=requirement,
        knowledge_deposits=[knowledge_deposit],
        bugs=[write_store.bugs[bug_id] for bug_id in created_bug_ids],
        code_review_report=code_review_report,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return True
