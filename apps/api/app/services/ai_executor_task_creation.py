from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.ai_executor_runner_approvals import (
    save_pending_ai_executor_approval_request,
)
from app.services.ai_executor_runner_safety import runner_task_safety_snapshot
from app.services.operational_records import (
    read_memory_dict,
    record_audit_event,
    save_single_repository_record,
)


def _persist_ai_executor_task(
    current_store: Any,
    task: dict[str, Any],
    *,
    audit_event: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_ai_executor_task_record", None)
    if callable(save_record):
        save_single_repository_record(
            current_store,
            "save_ai_executor_task_record",
            task,
            audit_event=audit_event,
        )
        return
    if repository is None:
        read_memory_dict(current_store, "ai_executor_tasks")[task["id"]] = task


def create_ai_executor_task(
    current_store: Any,
    *,
    action_id: str | None,
    connection_id: str | None,
    created_by: str,
    executor_type: str,
    input_payload: dict[str, Any],
    instruction: str,
    plugin_invocation_log_id: str | None,
    request_config: dict[str, Any],
    runner_id: str,
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    timeout_seconds: int,
    workspace_root: str,
    ai_task_id: str | None = None,
    agent_loop_iteration_id: str | None = None,
    agent_loop_run_id: str | None = None,
    context_manifest_id: str | None = None,
    deployment_run_id: str | None = None,
    quality_gate_run_id: str | None = None,
    task_kind: str = "coding",
    persist: bool = True,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    task_id = current_store.new_id("ai_executor_task")
    safety_snapshot = runner_task_safety_snapshot(
        instruction=instruction,
        request_config=request_config,
    )
    if safety_snapshot["approval_required"] and not safety_snapshot["approval"]["approved"]:
        approval_request = {
            **dict(safety_snapshot.get("approval_request") or {}),
            "approval_request_id": current_store.new_id("ai_executor_approval_request"),
            "action_id": action_id,
            "connection_id": connection_id,
            "executor_type": executor_type,
            "runner_id": runner_id,
            "scheduled_job_id": scheduled_job_id,
            "scheduled_job_run_id": scheduled_job_run_id,
            "workspace_root": workspace_root,
        }
        safety_snapshot = {**safety_snapshot, "approval_request": approval_request}
        if persist:
            save_pending_ai_executor_approval_request(
                current_store,
                approval_request=approval_request,
                requested_by=created_by,
                safety_snapshot=safety_snapshot,
            )
            record_audit_event(
                current_store,
                event_type="ai_executor_task.approval_requested",
                actor_id=created_by,
                subject_type="ai_executor_runner",
                subject_id=runner_id,
                payload={
                    "action_id": action_id,
                    "approval_request": approval_request,
                    "blocked_operations": safety_snapshot["blocked_operations"],
                    "connection_id": connection_id,
                    "executor_type": executor_type,
                    "risk_level": safety_snapshot["risk_level"],
                    "scheduled_job_id": scheduled_job_id,
                    "scheduled_job_run_id": scheduled_job_run_id,
                    "workspace_root": workspace_root,
                },
            )
        raise api_error(
            409,
            "AI_EXECUTOR_APPROVAL_REQUIRED",
            "AI executor instruction requires human approval before Runner dispatch",
            {
                "approval": safety_snapshot["approval"],
                "approval_request": approval_request,
                "blocked_operations": safety_snapshot["blocked_operations"],
                "risk_level": safety_snapshot["risk_level"],
                "safety": safety_snapshot,
            },
        )
    task_request_config = {
        **dict(request_config or {}),
        "ai_executor_safety": safety_snapshot,
    }
    task = {
        "action_id": action_id,
        "agent_loop_iteration_id": agent_loop_iteration_id,
        "agent_loop_run_id": agent_loop_run_id,
        "ai_task_id": ai_task_id,
        "claimed_at": None,
        "connection_id": connection_id,
        "context_manifest_id": context_manifest_id,
        "created_at": now,
        "created_by": created_by,
        "deployment_run_id": deployment_run_id,
        "error_code": None,
        "error_message": None,
        "executor_type": executor_type,
        "finished_at": None,
        "id": task_id,
        "input_payload": input_payload,
        "instruction": instruction,
        "logs": [],
        "plugin_invocation_log_id": plugin_invocation_log_id,
        "quality_gate_run_id": quality_gate_run_id,
        "request_config": task_request_config,
        "result_json": {},
        "runner_id": runner_id,
        "scheduled_job_id": scheduled_job_id,
        "scheduled_job_run_id": scheduled_job_run_id,
        "status": "queued",
        "task_kind": task_kind,
        "timeout_seconds": timeout_seconds,
        "updated_at": now,
        "workspace_root": workspace_root,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.queued",
        actor_id=created_by,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={
            "executor_type": executor_type,
            "runner_id": runner_id,
            "scheduled_job_id": scheduled_job_id,
            "scheduled_job_run_id": scheduled_job_run_id,
            "ai_task_id": ai_task_id,
            "context_manifest_id": context_manifest_id,
            "approval_id": (safety_snapshot.get("approval") or {}).get("approval_id"),
            "approved_by": (safety_snapshot.get("approval") or {}).get("approved_by"),
            "approved_operations": (safety_snapshot.get("approval") or {}).get(
                "approved_operations",
            )
            or [],
            "risk_level": safety_snapshot["risk_level"],
            "safety_status": safety_snapshot["status"],
            "task_kind": task_kind,
            "workspace_root": workspace_root,
        },
    )
    if persist:
        _persist_ai_executor_task(current_store, task, audit_event=audit_event)
    return task
