from __future__ import annotations

from typing import Any

from fastapi import Request

from app.api.deps import api_error
from app.services.ai_executor_runners import (
    _authenticated_runner,
    _read_record,
    sync_ai_executor_task_store,
)


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return text


def runner_ai_executor_task_status_response(
    *,
    current_store: Any,
    request: Request,
    runner_id: str,
    task_id: str,
) -> dict[str, Any]:
    normalized_runner_id = _required_text(runner_id, "runner_id")
    _authenticated_runner(current_store, request=request, runner_id=normalized_runner_id)
    sync_ai_executor_task_store(current_store, runner_id=normalized_runner_id)
    task = _read_record(current_store, "ai_executor_tasks", task_id)
    if task is None or task.get("runner_id") != normalized_runner_id:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    result_json = task.get("result_json") if isinstance(task.get("result_json"), dict) else {}
    workspace_isolation = result_json.get("workspace_isolation")
    return {
        "task": {
            "error_code": task.get("error_code"),
            "error_message": task.get("error_message"),
            "finished_at": task.get("finished_at"),
            "id": task.get("id"),
            "lease_expires_at": task.get("lease_expires_at"),
            "runner_id": task.get("runner_id"),
            "status": task.get("status"),
            "timeout_seconds": task.get("timeout_seconds"),
            "updated_at": task.get("updated_at"),
            "workspace_isolation": (
                workspace_isolation if isinstance(workspace_isolation, dict) else None
            ),
        }
    }
