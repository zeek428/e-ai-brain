from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Request

from app.api.deps import api_error
from app.services.model_gateway import call_model_gateway_for_task
from app.services.model_gateway_config_context import model_gateway_source_store


def execute_assessment_gateway_task(
    *,
    authenticate_runner: Callable[..., Any],
    complete_assessment: Callable[..., dict[str, Any]],
    current_store: Any,
    request: Request,
    runner_id: str,
    sync_task: Callable[[Any, str], dict[str, Any]],
    task_id: str,
) -> dict[str, Any]:
    """Run a claimed assessment task and complete it from a frozen gateway result."""
    authenticate_runner(current_store, request=request, runner_id=runner_id)
    task = sync_task(current_store, task_id)
    if task.get("runner_id") != runner_id:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    if task.get("task_kind") != "assessment" or task.get("status") != "claimed":
        raise api_error(
            409,
            "ASSESSMENT_EXECUTION_INVALID",
            "Assessment gateway execution requires a claimed assessment task",
        )
    payload = task.get("input_payload") if isinstance(task.get("input_payload"), dict) else {}
    execution_id = str(payload.get("assessment_execution_id") or "").strip()
    if not execution_id:
        raise api_error(
            409,
            "ASSESSMENT_EXECUTION_INVALID",
            "Assessment runner task is missing frozen execution provenance",
        )
    repository = getattr(current_store, "repository", None)
    requirements = getattr(repository, "load_requirements", lambda: {"requirements": {}})()
    requirement = (requirements.get("requirements") or {}).get(payload.get("requirement_id"))
    if not isinstance(requirement, dict):
        raise api_error(
            409, "ASSESSMENT_REQUIREMENT_INVALID", "Assessment requirement is unavailable"
        )
    gateway_task = {
        "id": task["id"],
        "task_type": "requirement_assessment",
        "title": f"Requirement assessment: {requirement['id']}",
        "input_json": {
            "assessment_execution_id": execution_id,
            "requirement_id": requirement["id"],
            "requirement_revision": payload.get("requirement_revision"),
        },
        "input_payload": payload,
        "product_context": {"product_id": requirement.get("product_id")},
        "requirement_snapshot": requirement,
    }
    get_existing_invocation = getattr(
        repository,
        "get_assessment_model_invocation_for_execution",
        None,
    )
    existing_invocation = (
        get_existing_invocation(execution_id) if callable(get_existing_invocation) else None
    )
    if isinstance(existing_invocation, dict):
        return complete_assessment(
            current_store=current_store,
            model_invocation_id=existing_invocation.get("id"),
            runner_id=runner_id,
            task=task,
        )
    gateway_store = model_gateway_source_store(repository)
    output, model_log = call_model_gateway_for_task(gateway_store, task=gateway_task)
    return complete_assessment(
        current_store=current_store,
        model_log=model_log,
        output=output,
        runner_id=runner_id,
        task=task,
    )
