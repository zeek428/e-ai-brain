from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import require_roles
from app.services.task_access import task_allowed_roles
from app.services.task_graph_runtime import latest_graph_run, transition_latest_graph_run
from app.services.task_persistence_helpers import save_review_decision_records
from app.services.task_review_artifacts import (
    advance_requirement_after_task_completed,
    complete_review_with_edited_approval,
    confirm_code_review_report,
    create_automated_testing_bugs,
    create_knowledge_deposit,
    create_post_release_bugs,
    ensure_review_decidable,
)
from app.services.task_workflow_context import task_workflow_write_store


def approve_review_response(
    *,
    current_store: Any,
    review_id: str,
    user: dict[str, Any],
    version: int,
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    review, task = ensure_review_decidable(write_store, review_id=review_id, version=version)
    require_roles(user, task_allowed_roles(task))
    audit_start_index = len(write_store.audit_events)
    now = datetime.now(UTC).isoformat()
    review["status"] = "approved"
    review["decided_by"] = user["id"]
    review["decided_at"] = now
    review["updated_at"] = now
    task["status"] = "completed"
    task["updated_at"] = now
    confirm_code_review_report(write_store, task)
    created_bug_ids = [
        *create_automated_testing_bugs(write_store, actor_id=user["id"], task=task),
        *create_post_release_bugs(write_store, actor_id=user["id"], task=task),
    ]
    advance_requirement_after_task_completed(write_store, task)
    knowledge_deposit = create_knowledge_deposit(write_store, task)
    checkpoint = transition_latest_graph_run(
        write_store,
        task=task,
        status="completed",
        current_step="complete_archive",
        state_snapshot={"task_status": task["status"], "review_id": review_id},
    )
    write_store.audit(
        event_type="review.submitted",
        actor_id=user["id"],
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={"decision": "approved"},
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
    return {"review_status": review["status"], "task_status": task["status"]}


def edit_approve_review_response(
    *,
    current_store: Any,
    edited_content: dict[str, Any] | None,
    review_id: str,
    user: dict[str, Any],
    version: int,
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    review, task = ensure_review_decidable(write_store, review_id=review_id, version=version)
    require_roles(user, task_allowed_roles(task))
    audit_start_index = len(write_store.audit_events)
    result = complete_review_with_edited_approval(
        write_store,
        actor_id=user["id"],
        edited_content=edited_content or {},
        review=review,
        review_id=review_id,
        task=task,
    )
    graph_run = latest_graph_run(write_store, task)
    checkpoint = result["checkpoint"]
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
        knowledge_deposits=[result["knowledge_deposit"]],
        bugs=[write_store.bugs[bug_id] for bug_id in result["bug_ids"]],
        code_review_report=code_review_report,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return {
        "review_status": result["review_status"],
        "task_status": result["task_status"],
    }
