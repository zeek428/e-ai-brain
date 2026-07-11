from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.product_scope import user_can_read_product


def _read_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def _read_record(
    current_store: Any,
    collection_name: str,
    record_id: str | None,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    item = _read_collection(current_store, collection_name).get(str(record_id))
    return item if isinstance(item, dict) else None


def _task_public(task: dict[str, Any]) -> dict[str, Any]:
    return dict(task)


def _load_scheduled_job_run(current_store: Any, task: dict[str, Any]) -> dict[str, Any] | None:
    run_id = task.get("scheduled_job_run_id")
    if not run_id:
        return None
    run = _read_record(current_store, "scheduled_job_runs", run_id)
    if run is not None:
        return run
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_scheduled_job_runs", None)
    if callable(list_runs):
        for candidate in list_runs(scheduled_job_id=task.get("scheduled_job_id")):
            if candidate.get("id") == run_id:
                return candidate
    return None


def _load_plugin_invocation_log(current_store: Any, task: dict[str, Any]) -> dict[str, Any] | None:
    log_id = task.get("plugin_invocation_log_id")
    if not log_id:
        return None
    log = _read_record(current_store, "plugin_invocation_logs", log_id)
    if log is not None:
        return log
    repository = getattr(current_store, "repository", None)
    list_logs = getattr(repository, "list_plugin_invocation_logs", None)
    if callable(list_logs):
        for candidate in list_logs(scheduled_job_run_id=task.get("scheduled_job_run_id")):
            if candidate.get("id") == log_id:
                return candidate
    return None


def _load_collector_run(current_store: Any, collector_run_id: str | None) -> dict[str, Any] | None:
    if not collector_run_id:
        return None
    collector_run = _read_record(current_store, "collector_runs", collector_run_id)
    if collector_run is not None:
        return collector_run
    repository = getattr(current_store, "repository", None)
    list_collector_runs = getattr(repository, "list_collector_runs", None)
    if callable(list_collector_runs):
        for candidate in list_collector_runs():
            if candidate.get("id") == collector_run_id:
                return candidate
    return None


def _load_scheduled_job(current_store: Any, scheduled_job_id: str | None) -> dict[str, Any] | None:
    if not scheduled_job_id:
        return None
    job = _read_record(current_store, "scheduled_jobs", scheduled_job_id)
    if job is not None:
        return job
    repository = getattr(current_store, "repository", None)
    list_jobs = getattr(repository, "list_scheduled_jobs", None)
    if callable(list_jobs):
        for candidate in list_jobs():
            if candidate.get("id") == scheduled_job_id:
                return candidate
    return None


def _load_ai_task(current_store: Any, ai_task_id: str | None) -> dict[str, Any] | None:
    if not ai_task_id:
        return None
    task = _read_record(current_store, "ai_tasks", ai_task_id)
    if task is not None:
        return task
    repository = getattr(current_store, "repository", None)
    load_ai_tasks = getattr(repository, "load_ai_tasks", None)
    if callable(load_ai_tasks):
        payload = load_ai_tasks()
        for candidate in payload.get("ai_tasks", {}).values():
            if candidate.get("id") == ai_task_id:
                return candidate
        return _read_record(current_store, "ai_tasks", ai_task_id)
    return None


def _load_deployment_run(
    current_store: Any,
    deployment_run_id: str | None,
) -> dict[str, Any] | None:
    if not deployment_run_id:
        return None
    run = _read_record(current_store, "deployment_runs", deployment_run_id)
    if run is not None:
        return run
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_deployment_runs", None)
    if callable(list_runs):
        for candidate in list_runs():
            if candidate.get("id") == deployment_run_id:
                return candidate
    return None


def _load_deployment_request(
    current_store: Any,
    deployment_request_id: str | None,
) -> dict[str, Any] | None:
    if not deployment_request_id:
        return None
    deployment = _read_record(
        current_store,
        "deployment_requests",
        deployment_request_id,
    )
    if deployment is not None:
        return deployment
    repository = getattr(current_store, "repository", None)
    list_requests = getattr(repository, "list_deployment_requests", None)
    if callable(list_requests):
        for candidate in list_requests():
            if candidate.get("id") == deployment_request_id:
                return candidate
    return None


def _ai_executor_task_product_id(current_store: Any, task: dict[str, Any]) -> Any:
    if task.get("product_id") is not None:
        return task.get("product_id")
    job = _load_scheduled_job(current_store, task.get("scheduled_job_id"))
    if job is not None and job.get("product_id") is not None:
        return job.get("product_id")
    run = _load_scheduled_job_run(current_store, task)
    if run is not None:
        config_snapshot = run.get("config_snapshot")
        if isinstance(config_snapshot, dict) and config_snapshot.get("product_id") is not None:
            return config_snapshot.get("product_id")
        run_job = _load_scheduled_job(current_store, run.get("scheduled_job_id"))
        if run_job is not None and run_job.get("product_id") is not None:
            return run_job.get("product_id")
    ai_task = _load_ai_task(current_store, task.get("ai_task_id"))
    if ai_task is not None:
        return ai_task.get("product_id")
    deployment_run = _load_deployment_run(current_store, task.get("deployment_run_id"))
    if deployment_run is not None:
        deployment = _load_deployment_request(
            current_store,
            deployment_run.get("deployment_request_id"),
        )
        if deployment is not None:
            return deployment.get("product_id")
    return None


def _ai_executor_task_visible_to_user(
    current_store: Any,
    *,
    task: dict[str, Any],
    user: dict[str, Any],
) -> bool:
    return user_can_read_product(user, _ai_executor_task_product_id(current_store, task))


def _runner_node_from_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "error_code": task.get("error_code"),
        "error_message": task.get("error_message"),
        "executor_type": task.get("executor_type"),
        "finished_at": task.get("finished_at"),
        "label": "AI 执行器执行内容",
        "logs": task.get("logs") or [],
        "result_json": task.get("result_json") or {},
        "runner_id": task.get("runner_id"),
        "runner_task_id": task.get("id"),
        "status": task.get("status"),
        "workspace_root": task.get("workspace_root"),
    }


def _status_for_runner_task(task_status: str) -> str:
    if task_status == "succeeded":
        return "succeeded"
    if task_status == "cancelled":
        return "cancelled"
    if task_status in {"dead_letter", "failed", "timed_out"}:
        return "failed"
    return "running"


def _records_imported_from_runner_result(task: dict[str, Any], fallback: int = 0) -> int:
    result_json = task.get("result_json")
    if isinstance(result_json, dict):
        for key in ("records_imported", "finding_count", "row_count", "count"):
            value = result_json.get(key)
            if isinstance(value, int) and value >= 0:
                return value
    return fallback


def _datetime_value(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
