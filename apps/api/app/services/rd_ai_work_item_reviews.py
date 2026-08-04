from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.services.ai_executor_runner_persistence import _persist_task_state_records
from app.services.ai_executor_task_creation import create_ai_executor_task
from app.services.execution_attestations import verify_execution_attestation
from app.services.operational_records import read_memory_dict, record_audit_event
from app.services.rd_work_item_scheduler import review_work_item


def _record(
    current_store: Any,
    collection_name: str,
    record_id: str,
    repository_method: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    load = getattr(repository, repository_method, None)
    if callable(load):
        record = load(record_id)
        return dict(record) if isinstance(record, dict) else None
    record = read_memory_dict(current_store, collection_name).get(record_id)
    return deepcopy(record) if isinstance(record, dict) else None


def _runner_tasks(current_store: Any, *, ai_task_id: str) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_tasks = getattr(repository, "list_ai_executor_tasks", None)
    records = (
        list_tasks()
        if callable(list_tasks)
        else read_memory_dict(current_store, "ai_executor_tasks").values()
    )
    return [
        dict(record)
        for record in records
        if isinstance(record, dict) and record.get("ai_task_id") == ai_task_id
    ]


def _runner_record(current_store: Any, runner_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_runners = getattr(repository, "list_ai_executor_runners", None)
    records = (
        list_runners()
        if callable(list_runners)
        else read_memory_dict(current_store, "ai_executor_runners").values()
    )
    return next(
        (
            dict(record)
            for record in records
            if isinstance(record, dict) and record.get("id") == runner_id
        ),
        None,
    )


def _nested_dict(value: Any, *keys: str) -> dict[str, Any]:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return dict(current) if isinstance(current, dict) else {}


def _coding_delivery(coding_runner_task: dict[str, Any]) -> dict[str, Any]:
    result = (
        coding_runner_task.get("result_json")
        if isinstance(coding_runner_task.get("result_json"), dict)
        else {}
    )
    candidates = [
        _nested_dict(result, "git_delivery"),
        _nested_dict(result, "parsed_output", "git_delivery"),
        _nested_dict(result, "result", "git_delivery"),
        _nested_dict(result, "result", "parsed_output", "git_delivery"),
    ]
    return next((candidate for candidate in candidates if candidate), {})


def _coding_workspace(coding_runner_task: dict[str, Any]) -> str:
    result = (
        coding_runner_task.get("result_json")
        if isinstance(coding_runner_task.get("result_json"), dict)
        else {}
    )
    candidates = [
        _nested_dict(result, "workspace_isolation"),
        _nested_dict(result, "result", "workspace_isolation"),
    ]
    for isolation in candidates:
        worktree_path = str(isolation.get("worktree_path") or "").strip()
        if worktree_path:
            return worktree_path
    return str(coding_runner_task.get("workspace_root") or "").strip()


def _coding_workspace_isolation(coding_runner_task: dict[str, Any]) -> dict[str, Any]:
    result = (
        coding_runner_task.get("result_json")
        if isinstance(coding_runner_task.get("result_json"), dict)
        else {}
    )
    candidates = [
        _nested_dict(result, "workspace_isolation"),
        _nested_dict(result, "result", "workspace_isolation"),
    ]
    isolation = next((candidate for candidate in candidates if candidate), {})
    return {
        key: isolation[key]
        for key in ("base_workspace_root", "branch_name", "mode", "worktree_path")
        if isolation.get(key)
    }


def _mark_ai_reviewer_unavailable(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    reason: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    ai_task.update(
        {
            "current_step": "ai_reviewer_unavailable",
            "error_code": "RD_AI_REVIEWER_UNAVAILABLE",
            "error_message": reason,
            "status": "waiting_review",
            "updated_at": now,
        }
    )
    audit_event = record_audit_event(
        current_store,
        event_type="rd_work_item.ai_reviewer_unavailable",
        actor_id="system",
        subject_type="ai_task",
        subject_id=str(ai_task["id"]),
        payload={"reason": reason},
    )
    _persist_task_state_records(
        current_store,
        audit_events=[audit_event],
        reviews=None,
        task=ai_task,
    )


def queue_ai_work_item_review_if_needed(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    quality_gate_run: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Queue one read-only Runner task for a frozen AI reviewer seat.

    Human reviewer seats continue to use the existing Review UI.  The review
    Runner is idempotent by the pending Review identity so callback replay or a
    process restart cannot create duplicate reviewer executions.
    """
    work_item = _record(
        current_store,
        "rd_work_items",
        str(ai_task.get("work_item_id") or ""),
        "get_rd_work_item",
    )
    reviewer = _record(
        current_store,
        "rd_run_seats",
        str((work_item or {}).get("reviewer_seat_id") or ""),
        "get_rd_run_seat",
    )
    if not isinstance(reviewer, dict) or reviewer.get("subject_type") != "ai_employee":
        return None

    review_ids = [str(review_id) for review_id in ai_task.get("review_ids") or [] if review_id]
    review_id = review_ids[-1] if review_ids else ""
    profile = _record(
        current_store,
        "rd_executor_profiles",
        str(reviewer.get("executor_profile_id") or ""),
        "get_rd_executor_profile",
    )
    runner_id = str((profile or {}).get("runner_id") or "").strip()
    runner = _runner_record(current_store, runner_id) if runner_id else None
    if (
        not review_id
        or not isinstance(work_item, dict)
        or reviewer.get("status", "active") != "active"
        or not str(reviewer.get("ai_employee_id") or "").strip()
        or not isinstance(profile, dict)
        or profile.get("status") != "active"
        or not runner_id
        or not isinstance(runner, dict)
        or runner.get("status") != "active"
    ):
        _mark_ai_reviewer_unavailable(
            current_store,
            ai_task=ai_task,
            reason="Frozen AI reviewer seat has no active employee, executor profile, or Runner",
        )
        return None

    idempotency_key = f"rd-work-item-review:{review_id}"
    existing = next(
        (
            task
            for task in _runner_tasks(current_store, ai_task_id=str(ai_task["id"]))
            if task.get("task_kind") == "work_item_review"
            and (task.get("request_config") or {}).get("idempotency_key") == idempotency_key
        ),
        None,
    )
    if existing is not None:
        return existing

    gate_snapshot = (
        quality_gate_run.get("policy_snapshot")
        if isinstance(quality_gate_run, dict)
        and isinstance(quality_gate_run.get("policy_snapshot"), dict)
        else {}
    )
    coding_runner_task_id = str(gate_snapshot.get("coding_runner_task_id") or "").strip()
    coding_runner_task = next(
        (
            task
            for task in _runner_tasks(current_store, ai_task_id=str(ai_task["id"]))
            if task.get("id") == coding_runner_task_id
        ),
        None,
    )
    if coding_runner_task is None:
        _mark_ai_reviewer_unavailable(
            current_store,
            ai_task=ai_task,
            reason="Frozen coding Runner evidence is unavailable for independent review",
        )
        return None
    delivery = _coding_delivery(coding_runner_task)
    expected_commit_sha = str(delivery.get("local_commit_sha") or "").strip()
    workspace_isolation = _coding_workspace_isolation(coding_runner_task)
    workspace_root = str(workspace_isolation.get("base_workspace_root") or "").strip()
    if not workspace_root:
        workspace_root = _coding_workspace(coding_runner_task)
    if not expected_commit_sha or not workspace_root:
        _mark_ai_reviewer_unavailable(
            current_store,
            ai_task=ai_task,
            reason="Frozen commit or isolated workspace is unavailable for independent review",
        )
        return None

    acceptance_criteria = list(work_item.get("acceptance_criteria") or [])
    output_contract = dict(work_item.get("output_contract") or {})
    quality_gate_evidence = {
        key: (quality_gate_run or {}).get(key)
        for key in (
            "finished_at",
            "id",
            "independent_evidence_count",
            "status",
            "summary",
            "verified_attestation_count",
        )
        if (quality_gate_run or {}).get(key) is not None
    }
    quality_gate_evidence["coding_runner_task_id"] = coding_runner_task_id
    verifier_runner_task_id = str(gate_snapshot.get("verifier_runner_task_id") or "").strip()
    if verifier_runner_task_id:
        quality_gate_evidence["verifier_runner_task_id"] = verifier_runner_task_id
    instruction = (
        "Perform an independent read-only review of the frozen work-item commit. "
        "Do not alter repository files or perform external writes. Compare the implementation "
        "with the frozen acceptance criteria and quality-gate evidence. Return exactly one JSON "
        "object with decision (approve, request_rework, or reject), summary, comment, findings, "
        "and reviewed_commit_sha. The reviewed_commit_sha must equal the frozen commit.\n"
        f"Frozen commit: {expected_commit_sha}\n"
        f"Current work-item type: {work_item.get('work_item_type')}\n"
        "Review only facts available in the current work-item phase. Do not require downstream "
        "remote push, product-version ready_for_release, collaboration-run completion, or "
        "deployment outcomes from an implementation or test artifact. Those facts are owned by "
        "later deterministic delivery stages; never ask the producer to fabricate them.\n"
        "Quality-gate evidence: "
        f"{json.dumps(quality_gate_evidence, ensure_ascii=False, sort_keys=True)}\n"
        f"Acceptance criteria: {json.dumps(acceptance_criteria, ensure_ascii=False)}\n"
        f"Output contract: {json.dumps(output_contract, ensure_ascii=False, sort_keys=True)}"
    )
    review_task = create_ai_executor_task(
        current_store,
        action_id=None,
        ai_task_id=str(ai_task["id"]),
        connection_id=None,
        created_by=str(ai_task.get("created_by") or "user_admin"),
        executor_type=str(profile.get("executor_type") or "codex"),
        input_payload={
            "ai_employee_id": str(reviewer["ai_employee_id"]),
            "coding_runner_task_id": coding_runner_task_id,
            "expected_commit_sha": expected_commit_sha,
            "executor_profile_id": str(profile["id"]),
            "quality_gate_run_id": str((quality_gate_run or {}).get("id") or ""),
            "rd_collaboration_run_id": str(ai_task.get("collaboration_run_id") or ""),
            "rd_work_item_id": str(work_item["id"]),
            "review_id": review_id,
            "reviewer_seat_id": str(reviewer["id"]),
        },
        instruction=instruction,
        plugin_invocation_log_id=None,
        request_config={
            "idempotency_key": idempotency_key,
            "read_only": True,
            "required_trust_domain": str(runner.get("trust_domain") or "verification"),
            "source": "rd_ai_work_item_review",
            "workspace_isolation": workspace_isolation,
        },
        runner_id=runner_id,
        scheduled_job_id=None,
        scheduled_job_run_id=None,
        task_kind="work_item_review",
        timeout_seconds=max(60, int(profile.get("timeout_seconds") or 600)),
        workspace_root=workspace_root,
    )
    now = datetime.now(UTC).isoformat()
    ai_task.update(
        {
            "current_step": "ai_reviewer_running",
            "error_code": None,
            "error_message": None,
            "input_json": {
                **dict(ai_task.get("input_json") or {}),
                "review_executor": {
                    "ai_employee_id": reviewer["ai_employee_id"],
                    "executor_profile_id": profile["id"],
                    "runner_id": runner_id,
                    "runner_task_id": review_task["id"],
                    "reviewer_seat_id": reviewer["id"],
                },
            },
            "status": "running",
            "updated_at": now,
        }
    )
    audit_event = record_audit_event(
        current_store,
        event_type="rd_work_item.ai_reviewer_dispatched",
        actor_id="system",
        subject_type="rd_work_item",
        subject_id=str(work_item["id"]),
        payload={
            "ai_employee_id": reviewer["ai_employee_id"],
            "executor_profile_id": profile["id"],
            "review_id": review_id,
            "runner_id": runner_id,
            "runner_task_id": review_task["id"],
        },
    )
    _persist_task_state_records(
        current_store,
        audit_events=[audit_event],
        reviews=None,
        task=ai_task,
    )
    return review_task


def _pending_review(current_store: Any, review_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    load_runtime = getattr(repository, "load_workflow_runtime", None)
    if callable(load_runtime):
        runtime = load_runtime()
        record = (runtime.get("human_reviews") or {}).get(review_id)
        return dict(record) if isinstance(record, dict) else None
    record = read_memory_dict(current_store, "human_reviews").get(review_id)
    return deepcopy(record) if isinstance(record, dict) else None


def _review_output(result_json: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        result_json.get("parsed_output"),
        result_json.get("result"),
        _nested_dict(result_json, "result", "parsed_output"),
    ]
    return next((dict(candidate) for candidate in candidates if isinstance(candidate, dict)), {})


def _fail_ai_review_closed(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    error_code: str,
    error_message: str,
    runner_task: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    ai_task.update(
        {
            "current_step": "ai_reviewer_failed",
            "error_code": error_code,
            "error_message": error_message,
            "output_json": {
                **dict(ai_task.get("output_json") or {}),
                "ai_review": {
                    "runner_task_id": runner_task.get("id"),
                    "status": runner_task.get("status"),
                },
            },
            "status": "waiting_review",
            "updated_at": now,
        }
    )
    audit_event = record_audit_event(
        current_store,
        event_type="rd_work_item.ai_reviewer_failed",
        actor_id=str(runner_task.get("runner_id") or "system"),
        subject_type="ai_task",
        subject_id=str(ai_task["id"]),
        payload={
            "error_code": error_code,
            "runner_task_id": runner_task.get("id"),
        },
    )
    _persist_task_state_records(
        current_store,
        audit_events=[audit_event],
        reviews=None,
        task=ai_task,
    )
    return {"action": "blocked", "error_code": error_code}


def complete_ai_work_item_review(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    runner_task: dict[str, Any],
) -> dict[str, Any]:
    """Validate and project a signed AI reviewer decision to the work item."""
    input_payload = (
        runner_task.get("input_payload")
        if isinstance(runner_task.get("input_payload"), dict)
        else {}
    )
    work_item = _record(
        current_store,
        "rd_work_items",
        str(input_payload.get("rd_work_item_id") or ""),
        "get_rd_work_item",
    )
    reviewer = _record(
        current_store,
        "rd_run_seats",
        str(input_payload.get("reviewer_seat_id") or ""),
        "get_rd_run_seat",
    )
    profile = _record(
        current_store,
        "rd_executor_profiles",
        str(input_payload.get("executor_profile_id") or ""),
        "get_rd_executor_profile",
    )
    coding_runner_task = next(
        (
            task
            for task in _runner_tasks(current_store, ai_task_id=str(ai_task["id"]))
            if task.get("id") == input_payload.get("coding_runner_task_id")
        ),
        None,
    )
    if (
        not isinstance(work_item, dict)
        or work_item.get("status") != "reviewing"
        or not isinstance(reviewer, dict)
        or reviewer.get("subject_type") != "ai_employee"
        or reviewer.get("id") != work_item.get("reviewer_seat_id")
        or reviewer.get("ai_employee_id") != input_payload.get("ai_employee_id")
        or reviewer.get("executor_profile_id") != input_payload.get("executor_profile_id")
        or not isinstance(profile, dict)
        or profile.get("runner_id") != runner_task.get("runner_id")
        or profile.get("executor_type") != runner_task.get("executor_type")
        or not isinstance(coding_runner_task, dict)
    ):
        return _fail_ai_review_closed(
            current_store,
            ai_task=ai_task,
            error_code="RD_AI_REVIEW_PROVENANCE_INVALID",
            error_message="AI reviewer result does not match the frozen reviewer provenance",
            runner_task=runner_task,
        )
    if runner_task.get("status") != "succeeded":
        return _fail_ai_review_closed(
            current_store,
            ai_task=ai_task,
            error_code=str(runner_task.get("error_code") or "RD_AI_REVIEW_EXECUTION_FAILED"),
            error_message=str(runner_task.get("error_message") or "AI reviewer execution failed"),
            runner_task=runner_task,
        )

    request_config = (
        runner_task.get("request_config")
        if isinstance(runner_task.get("request_config"), dict)
        else {}
    )
    attestation = verify_execution_attestation(
        current_store,
        runner_task=runner_task,
        required_trust_domain=str(request_config.get("required_trust_domain") or "verification"),
        coding_runner_task=coding_runner_task,
    )
    if attestation.get("status") != "verified":
        return _fail_ai_review_closed(
            current_store,
            ai_task=ai_task,
            error_code=str(attestation.get("error_code") or "EXECUTION_ATTESTATION_INVALID"),
            error_message="AI reviewer execution attestation is not trusted",
            runner_task=runner_task,
        )

    result_json = (
        runner_task.get("result_json")
        if isinstance(runner_task.get("result_json"), dict)
        else {}
    )
    output = _review_output(result_json)
    decision = str(output.get("decision") or "").strip()
    comment = str(output.get("comment") or output.get("summary") or "").strip()
    expected_commit_sha = str(input_payload.get("expected_commit_sha") or "").strip()
    reviewed_commit_sha = str(output.get("reviewed_commit_sha") or "").strip()
    if (
        decision not in {"approve", "request_rework", "reject"}
        or reviewed_commit_sha != expected_commit_sha
        or (decision == "request_rework" and not comment)
    ):
        return _fail_ai_review_closed(
            current_store,
            ai_task=ai_task,
            error_code="RD_AI_REVIEW_RESULT_INVALID",
            error_message="AI reviewer result is malformed or references another commit",
            runner_task=runner_task,
        )

    review_id = str(input_payload.get("review_id") or "")
    review = _pending_review(current_store, review_id)
    if not isinstance(review, dict) or review.get("status") != "pending":
        return _fail_ai_review_closed(
            current_store,
            ai_task=ai_task,
            error_code="RD_AI_REVIEW_STATE_INVALID",
            error_message="AI reviewer result has no matching pending Review",
            runner_task=runner_task,
        )
    work_item_result = review_work_item(
        current_store,
        work_item_id=str(work_item["id"]),
        decision=decision,
        comment=comment or None,
        actor={"id": str(reviewer["ai_employee_id"]), "roles": []},
        version=int(work_item.get("version") or 1),
        idempotency_key=f"ai-review:{runner_task['id']}",
        reviewer_executor_profile_id=str(profile["id"]),
    )
    now = datetime.now(UTC).isoformat()
    review_status = {
        "approve": "approved",
        "request_rework": "requested_more_info",
        "reject": "rejected",
    }[decision]
    review.update(
        {
            "content": {
                **dict(review.get("content") or {}),
                "ai_review": output,
                "execution_attestation_id": attestation["id"],
                "runner_task_id": runner_task["id"],
            },
            "decided_at": now,
            "decided_by": reviewer["ai_employee_id"],
            "decision_reason": comment or None,
            "status": review_status,
            "updated_at": now,
        }
    )
    task_status = "completed" if decision == "approve" else "failed"
    task_step = {
        "approve": "ai_review_approved",
        "request_rework": "ai_review_rework_requested",
        "reject": "ai_review_rejected",
    }[decision]
    ai_task.update(
        {
            "current_step": task_step,
            "error_code": None if decision == "approve" else "RD_WORK_ITEM_REVIEW_NOT_APPROVED",
            "error_message": None if decision == "approve" else comment,
            "output_json": {
                **dict(ai_task.get("output_json") or {}),
                "ai_review": {
                    **output,
                    "execution_attestation_id": attestation["id"],
                    "runner_task_id": runner_task["id"],
                },
            },
            "status": task_status,
            "updated_at": now,
        }
    )
    audit_event = record_audit_event(
        current_store,
        event_type="rd_work_item.ai_review_completed",
        actor_id=str(reviewer["ai_employee_id"]),
        subject_type="rd_work_item",
        subject_id=str(work_item["id"]),
        payload={
            "decision": decision,
            "execution_attestation_id": attestation["id"],
            "review_id": review_id,
            "runner_task_id": runner_task["id"],
        },
    )
    _persist_task_state_records(
        current_store,
        audit_events=[audit_event],
        reviews=[review],
        task=ai_task,
    )
    return {
        "action": decision,
        "review": review,
        "work_item": work_item_result.get("work_item"),
    }
