from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.listing import ensure_list_enum
from app.services.bug_lifecycle import BUG_SEVERITIES
from app.services.task_graph_runtime import transition_latest_graph_run
from app.services.task_persistence_helpers import record_audit_event

REQUIREMENT_STATUSES = {
    "accepted",
    "approved",
    "cancelled",
    "closed",
    "code_reviewing",
    "deferred",
    "designing",
    "developing",
    "draft",
    "planned",
    "ready_for_dev",
    "ready_for_release",
    "rejected",
    "released",
    "submitted",
    "testing",
}
REQUIREMENT_STATUS_AFTER_TASK_COMPLETED = {
    "automated_testing": "ready_for_release",
    "code_review": "testing",
    "development_planning": "developing",
    "post_release_analysis": "accepted",
    "product_detail_design": "ready_for_dev",
    "release_readiness": "released",
    "technical_solution": "ready_for_dev",
}


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def set_requirement_status(requirement: dict[str, Any], status: str) -> None:
    ensure_list_enum(status, REQUIREMENT_STATUSES, "requirement status")
    requirement["status"] = status
    requirement["updated_at"] = datetime.now(UTC).isoformat()


def advance_requirement_after_task_completed(current_store: Any, task: dict[str, Any]) -> None:
    requirement = _memory_dict(current_store, "requirements").get(task.get("requirement_id"))
    if requirement is None:
        return
    next_status = REQUIREMENT_STATUS_AFTER_TASK_COMPLETED.get(task["task_type"])
    if next_status and requirement.get("status") not in {"accepted", "closed", "cancelled"}:
        set_requirement_status(requirement, next_status)


def confirm_code_review_report(current_store: Any, task: dict[str, Any]) -> None:
    if task["task_type"] != "code_review":
        return
    report_id = task.get("code_review_report_id")
    if not report_id:
        return
    report = _memory_dict(current_store, "code_review_reports")[report_id]
    output = task.get("output_json") or {}
    for key in ("summary", "risk_level", "findings", "executor"):
        if key in output:
            report[key] = current_store.snapshot(output[key])
    report["status"] = "confirmed"
    report["archived_at"] = datetime.now(UTC).isoformat()


def bug_suggestion_text(suggestion: dict[str, Any], key: str, fallback: str) -> str:
    value = suggestion.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def bug_suggestion_steps(
    suggestion: dict[str, Any],
    *,
    fallback: str = "执行自动化测试建议中的用例并复现失败。",
) -> list[str]:
    raw_steps = suggestion.get("reproduce_steps") or suggestion.get("steps") or []
    if isinstance(raw_steps, str):
        raw_steps = [raw_steps]
    if not isinstance(raw_steps, list):
        raw_steps = []
    steps = [str(step).strip() for step in raw_steps if str(step).strip()]
    return steps or [fallback]


def create_task_suggested_bugs(
    current_store: Any,
    *,
    actor_id: str,
    fallback_description: str,
    fallback_steps: str,
    source: str,
    title_prefix: str,
    task: dict[str, Any],
) -> list[str]:
    output = task.get("output_json") or {}
    suggestions = output.get("bug_suggestions")
    if not isinstance(suggestions, list):
        return []

    created_bug_ids: list[str] = []
    now = datetime.now(UTC).isoformat()
    for index, raw_suggestion in enumerate(suggestions, start=1):
        suggestion = raw_suggestion if isinstance(raw_suggestion, dict) else {}
        severity = str(suggestion.get("severity") or "major")
        if severity not in BUG_SEVERITIES:
            severity = "major"
        assignee = suggestion.get("assignee")
        bug_id = current_store.new_id("bug")
        bug = {
            "id": bug_id,
            "product_id": task["product_id"],
            "version_id": task["version_id"],
            "module_code": task.get("module_code"),
            "source": source,
            "title": bug_suggestion_text(
                suggestion,
                "title",
                f"{title_prefix} {index}：{task['title']}",
            ),
            "severity": severity,
            "description": bug_suggestion_text(
                suggestion,
                "description",
                fallback_description,
            ),
            "status": "open",
            "assignee": assignee if isinstance(assignee, str) else None,
            "related_task_id": task["id"],
            "requirement_id": task["requirement_id"],
            "reproduce_steps": bug_suggestion_steps(suggestion, fallback=fallback_steps),
            "evidence": {
                "generated_by_task_type": task["task_type"],
                "suggestion": current_store.snapshot(suggestion),
            },
            "duplicate_of_bug_id": None,
            "created_by": actor_id,
            "created_at": now,
            "updated_at": now,
        }
        _memory_dict(current_store, "bugs")[bug_id] = bug
        created_bug_ids.append(bug_id)
        record_audit_event(
            current_store,
            event_type="bug.created",
            actor_id=actor_id,
            ai_task_id=task["id"],
            subject_type="bug",
            subject_id=bug_id,
            payload={
                "severity": bug["severity"],
                "source": bug["source"],
                "status": bug["status"],
            },
        )
    return created_bug_ids


def create_automated_testing_bugs(
    current_store: Any,
    *,
    actor_id: str,
    task: dict[str, Any],
) -> list[str]:
    if task["task_type"] != "automated_testing":
        return []
    created_bug_ids = create_task_suggested_bugs(
        current_store,
        actor_id=actor_id,
        fallback_description="自动化测试任务确认后生成的缺陷建议。",
        fallback_steps="执行自动化测试建议中的用例并复现失败。",
        source="ai_auto_test",
        title_prefix="自动化测试发现",
        task=task,
    )
    if created_bug_ids:
        task["generated_bug_ids"] = created_bug_ids
        record_audit_event(
            current_store,
            event_type="automated_testing.bugs_created",
            actor_id=actor_id,
            ai_task_id=task["id"],
            subject_type="ai_task",
            subject_id=task["id"],
            payload={"bug_ids": created_bug_ids},
        )
    return created_bug_ids


def create_post_release_bugs(
    current_store: Any,
    *,
    actor_id: str,
    task: dict[str, Any],
) -> list[str]:
    if task["task_type"] != "post_release_analysis":
        return []
    created_bug_ids = create_task_suggested_bugs(
        current_store,
        actor_id=actor_id,
        fallback_description="上线后分析任务确认后生成的缺陷建议。",
        fallback_steps="结合上线后观测窗口和日志异常复现问题。",
        source="ai_post_release",
        title_prefix="上线后分析发现",
        task=task,
    )
    if created_bug_ids:
        task["generated_bug_ids"] = created_bug_ids
        record_audit_event(
            current_store,
            event_type="post_release_analysis.bugs_created",
            actor_id=actor_id,
            ai_task_id=task["id"],
            subject_type="ai_task",
            subject_id=task["id"],
            payload={"bug_ids": created_bug_ids},
        )
    return created_bug_ids


def ensure_review_decidable(
    current_store: Any,
    *,
    review_id: str,
    version: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    review = _memory_dict(current_store, "human_reviews").get(review_id)
    if review is None:
        raise api_error(404, "NOT_FOUND", "Review not found")
    if review["status"] != "pending":
        raise api_error(409, "REVIEW_STATE_INVALID", "Review has already been decided")
    if review["version"] != version:
        raise api_error(409, "REVIEW_VERSION_CONFLICT", "Review version conflict")
    task = _memory_dict(current_store, "ai_tasks")[review["ai_task_id"]]
    return review, task


def _first_non_blank_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _task_output_knowledge_content(task: dict[str, Any]) -> str:
    output = task.get("output_json")
    if not isinstance(output, dict):
        return str(output).strip() if output is not None else task["title"]

    result = output.get("result")
    if not isinstance(result, dict):
        result = {}
    content = _first_non_blank_string(
        output.get("summary"),
        result.get("summary"),
        output.get("output_preview"),
        result.get("output_preview"),
    )
    if content is not None:
        return content
    if output:
        return json.dumps(output, ensure_ascii=False, sort_keys=True)
    return task["title"]


def create_knowledge_deposit(current_store: Any, task: dict[str, Any]) -> dict[str, Any]:
    deposit_id = current_store.new_id("deposit")
    now = datetime.now(UTC).isoformat()
    deposit = {
        "id": deposit_id,
        "ai_task_id": task["id"],
        "title": f"{task['title']} 知识沉淀",
        "content": _task_output_knowledge_content(task),
        "status": "pending",
        "knowledge_document_id": None,
        "created_at": now,
        "updated_at": now,
    }
    if not uses_repository_context(current_store):
        _memory_dict(current_store, "knowledge_deposits")[deposit_id] = deposit
    return deposit


def complete_review_with_edited_approval(
    current_store: Any,
    *,
    actor_id: str,
    edited_content: dict[str, Any],
    review: dict[str, Any],
    review_id: str,
    task: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    task["output_json"] = {**task["output_json"], **edited_content}
    review["status"] = "edited_approved"
    review["edited_content"] = edited_content
    review["decided_by"] = actor_id
    review["decided_at"] = now
    review["updated_at"] = now
    task["status"] = "completed"
    task["updated_at"] = now
    confirm_code_review_report(current_store, task)
    created_bug_ids = [
        *create_automated_testing_bugs(current_store, actor_id=actor_id, task=task),
        *create_post_release_bugs(current_store, actor_id=actor_id, task=task),
    ]
    advance_requirement_after_task_completed(current_store, task)
    knowledge_deposit = create_knowledge_deposit(current_store, task)
    checkpoint = transition_latest_graph_run(
        current_store,
        task=task,
        status="completed",
        current_step="complete_archive",
        state_snapshot={"task_status": task["status"], "review_id": review_id},
    )
    record_audit_event(
        current_store,
        event_type="review.submitted",
        actor_id=actor_id,
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={"decision": "edited_approved"},
    )
    return {
        "review_status": review["status"],
        "task_status": task["status"],
        "bug_ids": created_bug_ids,
        "knowledge_deposit": knowledge_deposit,
        "checkpoint": checkpoint,
    }
