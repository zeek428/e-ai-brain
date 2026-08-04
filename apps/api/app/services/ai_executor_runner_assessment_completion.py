from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from psycopg import Error as PsycopgError

from app.api.deps import api_error
from app.services.operational_records import record_audit_event


def complete_ai_assessment_gateway_runner_task(
    *,
    append_task_logs: Callable[[dict[str, Any], list[dict[str, Any]]], list[dict[str, Any]]],
    current_store: Any,
    model_invocation_id: str | None = None,
    model_log: dict[str, Any] | None = None,
    output: dict[str, Any] | None = None,
    runner_id: str,
    sync_ai_task: Callable[..., None],
    sync_scheduled_run: Callable[..., None],
    task: dict[str, Any],
    task_public: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Persist one gateway result and its assessment completion in one transaction."""
    resolved_model_invocation_id = str(
        model_invocation_id or (model_log or {}).get("id") or ""
    ).strip()
    if not resolved_model_invocation_id:
        raise api_error(
            409,
            "ASSESSMENT_MODEL_INVOCATION_INVALID",
            "Assessment gateway completion requires a frozen model invocation",
        )
    if (model_log is None) != (output is None):
        raise api_error(
            409,
            "ASSESSMENT_MODEL_INVOCATION_INVALID",
            "Assessment gateway completion requires both model log and output",
        )
    now = datetime.now(UTC).isoformat()
    completed_task = {
        **task,
        "error_code": None,
        "error_message": None,
        "finished_at": now,
        "logs": append_task_logs(
            task,
            [
                {
                    "event": "model_gateway_completed",
                    "model_invocation_id": resolved_model_invocation_id,
                }
            ],
        ),
        "result_json": {"model_invocation_id": resolved_model_invocation_id},
        "status": "succeeded",
        "updated_at": now,
    }
    input_payload = (
        completed_task.get("input_payload")
        if isinstance(completed_task.get("input_payload"), dict)
        else {}
    )
    assessment_id = str(input_payload.get("assessment_id") or "").strip()
    execution_id = str(input_payload.get("assessment_execution_id") or "").strip()
    executor_profile_id = str(input_payload.get("executor_profile_id") or "").strip()
    if not assessment_id or not execution_id or not executor_profile_id:
        raise api_error(
            409,
            "ASSESSMENT_EXECUTION_INVALID",
            "Assessment runner task is missing frozen execution provenance",
        )
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.succeeded",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=completed_task["id"],
        payload={
            "assessment_execution_id": execution_id,
            "executor_type": completed_task["executor_type"],
            "model_invocation_id": resolved_model_invocation_id,
            "runner_id": runner_id,
            "status": "succeeded",
        },
    )
    complete_atomically = getattr(
        getattr(current_store, "repository", None),
        "complete_ai_assessment_runner_task",
        None,
    )
    if not callable(complete_atomically):
        raise api_error(
            503,
            "REPOSITORY_REQUIRED",
            "Assessment completion repository is unavailable",
        )
    try:
        complete_atomically(
            task=completed_task,
            assessment_id=assessment_id,
            execution_id=execution_id,
            executor_profile_id=executor_profile_id,
            runner_id=runner_id,
            model_invocation_id=resolved_model_invocation_id,
            model_log=model_log,
            output=output,
            audit_event=audit_event,
            outbox_event={
                "id": f"assessment-runner-complete-{completed_task['id']}",
                "aggregate_type": "requirement_assessment_execution",
                "aggregate_id": execution_id,
                "event_type": "requirement_assessment.runner_completed",
                "idempotency_key": f"assessment-runner-complete:{completed_task['id']}",
                "payload_json": {
                    "assessment_id": assessment_id,
                    "execution_id": execution_id,
                    "model_invocation_id": resolved_model_invocation_id,
                    "runner_id": runner_id,
                },
            },
        )
    except PsycopgError:
        raise
    except Exception as exc:
        raise api_error(
            409,
            getattr(exc, "code", "ASSESSMENT_EXECUTION_INVALID"),
            str(exc),
        ) from exc
    sync_scheduled_run(current_store, task=completed_task, runner_id=runner_id)
    sync_ai_task(current_store, task=completed_task, runner_id=runner_id)
    return {
        "model_invocation_id": resolved_model_invocation_id,
        "task": task_public(completed_task),
    }
