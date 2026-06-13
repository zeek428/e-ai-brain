from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.api.deps import api_error, require_roles
from app.services.operational_records import record_audit_event, save_single_repository_record

AI_EXECUTOR_TYPES = {"claude", "codex", "hermes", "openclaw"}
AI_EXECUTOR_RUNNER_PROTOCOLS = {"mcp_http", "mcp_stdio", "runner_polling", "runner_websocket"}
AI_EXECUTOR_RUNNER_STATUSES = {"active", "disabled", "offline"}
AI_EXECUTOR_TASK_STATUSES = {
    "cancelled",
    "claimed",
    "failed",
    "queued",
    "running",
    "succeeded",
    "timed_out",
}
AI_EXECUTOR_TASK_TERMINAL_STATUSES = {"cancelled", "failed", "succeeded", "timed_out"}


def _ensure_admin(user: dict[str, Any]) -> None:
    require_roles(user, {"admin"})


def _ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def _ensure_enum(value: str | None, allowed_values: set[str], field: str) -> str:
    normalized = _ensure_non_blank(value, field).lower()
    if normalized not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")
    return normalized


def _normalized_string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be an array")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalized_executor_types(value: Any) -> list[str]:
    executor_types = _normalized_string_list(value, "executor_types")
    if not executor_types:
        executor_types = ["codex"]
    for executor_type in executor_types:
        _ensure_enum(executor_type, AI_EXECUTOR_TYPES, "executor_type")
    return executor_types


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _runner_public(runner: dict[str, Any]) -> dict[str, Any]:
    public = dict(runner)
    public.pop("token_hash", None)
    public["token_configured"] = bool(runner.get("token_hash"))
    heartbeat_age = _heartbeat_age_seconds(runner.get("last_heartbeat_at"))
    public["heartbeat_age_seconds"] = heartbeat_age
    public["health_status"] = _runner_health_status(runner, heartbeat_age)
    public["setup_command"] = _runner_setup_command(runner)
    public["token_rotated_at"] = runner.get("token_rotated_at")
    public["token_version"] = int(runner.get("token_version") or 1)
    return public


def _task_public(task: dict[str, Any]) -> dict[str, Any]:
    return dict(task)


def _heartbeat_age_seconds(value: Any) -> int | None:
    if not value:
        return None
    try:
        heartbeat_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if heartbeat_at.tzinfo is None:
        heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
    return max(0, int((datetime.now(UTC) - heartbeat_at.astimezone(UTC)).total_seconds()))


def _runner_health_status(runner: dict[str, Any], heartbeat_age: int | None) -> str:
    if runner.get("status") == "disabled":
        return "disabled"
    if runner.get("status") == "offline":
        return "offline"
    if heartbeat_age is None:
        return "never_connected"
    timeout_seconds = int(runner.get("heartbeat_timeout_seconds") or 120)
    return "online" if heartbeat_age <= timeout_seconds else "offline"


def _runner_setup_command(runner: dict[str, Any]) -> str:
    executor_types = ",".join(str(item) for item in runner.get("executor_types") or ["codex"])
    workspace_roots = ",".join(str(item) for item in runner.get("workspace_roots") or ["*"])
    return (
        "ai-brain-runner start "
        f"--runner-id {runner.get('id')} "
        "--token <runner_token> "
        f"--endpoint {runner.get('endpoint_url') or 'runner://local'} "
        f"--executors {executor_types} "
        f"--workspace-roots {workspace_roots}"
    )


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    required = (
        "list_ai_executor_runners",
        "list_ai_executor_tasks",
        "save_ai_executor_runner_record",
        "save_ai_executor_task_record",
    )
    if repository is not None and all(
        callable(getattr(repository, name, None)) for name in required
    ):
        return repository
    return None


def _replace_collection(
    current_store: Any,
    collection_name: str,
    items: list[dict[str, Any]],
) -> None:
    setattr(
        current_store,
        collection_name,
        {str(item["id"]): dict(item) for item in items if item.get("id") is not None},
    )


def sync_ai_executor_runner_store(current_store: Any, *, status: str | None = None) -> None:
    repository = _repository(current_store)
    if repository is None:
        return
    _replace_collection(
        current_store,
        "ai_executor_runners",
        repository.list_ai_executor_runners(status=status),
    )


def sync_ai_executor_task_store(
    current_store: Any,
    *,
    runner_id: str | None = None,
    scheduled_job_run_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = _repository(current_store)
    if repository is None:
        return
    _replace_collection(
        current_store,
        "ai_executor_tasks",
        repository.list_ai_executor_tasks(
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        ),
    )


def _persist_record(
    current_store: Any,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    save_single_repository_record(current_store, method_name, record, audit_event=audit_event)


def _load_scheduled_job_run(current_store: Any, task: dict[str, Any]) -> dict[str, Any] | None:
    run_id = task.get("scheduled_job_run_id")
    if not run_id:
        return None
    run = current_store.scheduled_job_runs.get(run_id)
    if run is not None:
        return run
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_scheduled_job_runs", None)
    if callable(list_runs):
        for candidate in list_runs(scheduled_job_id=task.get("scheduled_job_id")):
            if candidate.get("id") == run_id:
                current_store.scheduled_job_runs[run_id] = candidate
                return candidate
    return None


def _load_plugin_invocation_log(current_store: Any, task: dict[str, Any]) -> dict[str, Any] | None:
    log_id = task.get("plugin_invocation_log_id")
    if not log_id:
        return None
    log = current_store.plugin_invocation_logs.get(log_id)
    if log is not None:
        return log
    repository = getattr(current_store, "repository", None)
    list_logs = getattr(repository, "list_plugin_invocation_logs", None)
    if callable(list_logs):
        for candidate in list_logs(scheduled_job_run_id=task.get("scheduled_job_run_id")):
            if candidate.get("id") == log_id:
                current_store.plugin_invocation_logs[log_id] = candidate
                return candidate
    return None


def _load_collector_run(current_store: Any, collector_run_id: str | None) -> dict[str, Any] | None:
    if not collector_run_id:
        return None
    collector_run = current_store.collector_runs.get(collector_run_id)
    if collector_run is not None:
        return collector_run
    repository = getattr(current_store, "repository", None)
    list_collector_runs = getattr(repository, "list_collector_runs", None)
    if callable(list_collector_runs):
        for candidate in list_collector_runs():
            if candidate.get("id") == collector_run_id:
                current_store.collector_runs[collector_run_id] = candidate
                return candidate
    return None


def _load_scheduled_job(current_store: Any, scheduled_job_id: str | None) -> dict[str, Any] | None:
    if not scheduled_job_id:
        return None
    job = current_store.scheduled_jobs.get(scheduled_job_id)
    if job is not None:
        return job
    repository = getattr(current_store, "repository", None)
    list_jobs = getattr(repository, "list_scheduled_jobs", None)
    if callable(list_jobs):
        for candidate in list_jobs():
            if candidate.get("id") == scheduled_job_id:
                current_store.scheduled_jobs[scheduled_job_id] = candidate
                return candidate
    return None


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
    if task_status in {"failed", "timed_out"}:
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


def _sync_runner_completion_to_scheduled_run(
    current_store: Any,
    *,
    task: dict[str, Any],
    runner_id: str,
) -> None:
    run = _load_scheduled_job_run(current_store, task)
    if run is None:
        return
    now = datetime.now(UTC).isoformat()
    runner_node = _runner_node_from_task(task)
    result_summary = dict(run.get("result_summary") or {})
    execution_nodes = dict(result_summary.get("execution_nodes") or {})
    execution_nodes["runner_execution"] = runner_node
    result_action = dict(execution_nodes.get("result_action") or {})
    if result_action:
        feedback = dict(result_action.get("feedback") or {})
        feedback["runner_result"] = task.get("result_json") or {}
        result_action["feedback"] = feedback
        result_action["status"] = _status_for_runner_task(str(task.get("status") or "running"))
        execution_nodes["result_action"] = result_action
    result_summary["execution_nodes"] = execution_nodes

    log = _load_plugin_invocation_log(current_store, task)
    if log is not None:
        response_summary = dict(log.get("response_summary") or {})
        response_summary["runner"] = runner_node
        json_payload = dict(response_summary.get("json") or {})
        json_payload.update(
            {
                "executor_type": task.get("executor_type"),
                "result_json": task.get("result_json") or {},
                "runner_id": task.get("runner_id"),
                "runner_task_id": task.get("id"),
                "status": task.get("status"),
                "workspace_root": task.get("workspace_root"),
            },
        )
        response_summary["json"] = json_payload
        log_status = log.get("status") or "succeeded"
        if task.get("status") in {"failed", "cancelled", "timed_out"}:
            log_status = "failed"
        updated_log = {
            **log,
            "error_code": task.get("error_code"),
            "error_message": task.get("error_message"),
            "response_summary": response_summary,
            "status": log_status,
            "updated_at": now,
        }
        current_store.plugin_invocation_logs[updated_log["id"]] = updated_log
        _persist_record(current_store, "save_plugin_invocation_log_record", updated_log)
        plugin_summary = dict(result_summary.get("plugin") or {})
        if plugin_summary:
            plugin_summary.update(
                {
                    "error_code": updated_log.get("error_code"),
                    "error_message": updated_log.get("error_message"),
                    "response_summary": response_summary,
                    "status": log_status,
                },
            )
            result_summary["plugin"] = plugin_summary

    run_status = _status_for_runner_task(str(task.get("status") or "running"))
    records_imported = _records_imported_from_runner_result(
        task,
        fallback=int(run.get("records_imported") or 0),
    )
    updated_run = {
        **run,
        "error_code": task.get("error_code") if run_status == "failed" else None,
        "error_message": task.get("error_message") if run_status == "failed" else None,
        "finished_at": now if run_status in {"cancelled", "failed", "succeeded"} else None,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": run_status,
        "updated_at": now,
    }
    current_store.scheduled_job_runs[updated_run["id"]] = updated_run
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{run_status}",
        actor_id=runner_id,
        subject_type="scheduled_job_run",
        subject_id=updated_run["id"],
        payload={
            "ai_executor_task_id": task["id"],
            "records_imported": records_imported,
            "runner_id": runner_id,
            "scheduled_job_id": task.get("scheduled_job_id"),
            "status": run_status,
        },
    )
    _persist_record(
        current_store,
        "save_scheduled_job_run_record",
        updated_run,
        audit_event=audit_event,
    )

    if run_status not in {"cancelled", "failed", "succeeded"}:
        return
    collector_run = _load_collector_run(current_store, updated_run.get("collector_run_id"))
    if collector_run is not None:
        collector_status = "succeeded" if run_status == "succeeded" else "failed"
        updated_collector = {
            **collector_run,
            "error_message": updated_run.get("error_message"),
            "finished_at": now,
            "records_imported": records_imported,
            "status": collector_status,
            "updated_at": now,
        }
        current_store.collector_runs[updated_collector["id"]] = updated_collector
        _persist_record(current_store, "save_collector_run_record", updated_collector)
    job = _load_scheduled_job(current_store, task.get("scheduled_job_id"))
    if job is not None:
        updated_job = {
            **job,
            "last_error_message": updated_run.get("error_message"),
            "last_failure_at": now if run_status == "failed" else job.get("last_failure_at"),
            "last_run_at": now,
            "last_success_at": now if run_status == "succeeded" else job.get("last_success_at"),
            "updated_at": now,
        }
        current_store.scheduled_jobs[updated_job["id"]] = updated_job
        _persist_record(current_store, "save_scheduled_job_record", updated_job)


def create_ai_executor_runner_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    runner_token = str(getattr(payload, "runner_token", None) or secrets.token_urlsafe(32))
    now = datetime.now(UTC).isoformat()
    runner_id = current_store.new_id("ai_executor_runner")
    runner = {
        "created_at": now,
        "created_by": user["id"],
        "endpoint_url": _ensure_non_blank(
            getattr(payload, "endpoint_url", None) or "runner://local",
            "endpoint_url",
        ),
        "executor_types": _normalized_executor_types(getattr(payload, "executor_types", None)),
        "heartbeat_timeout_seconds": int(
            getattr(payload, "heartbeat_timeout_seconds", None) or 120,
        ),
        "id": runner_id,
        "last_heartbeat_at": None,
        "max_concurrent_tasks": int(getattr(payload, "max_concurrent_tasks", None) or 1),
        "metadata": dict(getattr(payload, "metadata", None) or {}),
        "name": _ensure_non_blank(getattr(payload, "name", None), "name"),
        "protocol": _ensure_enum(
            getattr(payload, "protocol", None) or "runner_polling",
            AI_EXECUTOR_RUNNER_PROTOCOLS,
            "protocol",
        ),
        "status": _ensure_enum(
            getattr(payload, "status", None) or "active",
            AI_EXECUTOR_RUNNER_STATUSES,
            "status",
        ),
        "token_hash": _token_hash(runner_token),
        "token_rotated_at": None,
        "token_version": 1,
        "updated_at": now,
        "workspace_roots": _normalized_string_list(
            getattr(payload, "workspace_roots", None),
            "workspace_roots",
        ),
    }
    current_store.ai_executor_runners[runner_id] = runner
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.created",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={
            "executor_types": runner["executor_types"],
            "protocol": runner["protocol"],
            "status": runner["status"],
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return {**_runner_public(runner), "runner_token": runner_token}


def list_ai_executor_runners_response(
    *,
    current_store: Any,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if status is not None:
        _ensure_enum(status, AI_EXECUTOR_RUNNER_STATUSES, "status")
    sync_ai_executor_runner_store(current_store, status=status)
    sync_ai_executor_task_store(current_store)
    items = []
    for runner in current_store.ai_executor_runners.values():
        if status is not None and runner.get("status") != status:
            continue
        latest_task = max(
            (
                task
                for task in current_store.ai_executor_tasks.values()
                if task.get("runner_id") == runner.get("id")
            ),
            key=lambda task: (
                task.get("updated_at") or task.get("created_at") or "",
                task.get("id") or "",
            ),
            default=None,
        )
        item = _runner_public(runner)
        if latest_task is not None:
            item["latest_task_id"] = latest_task.get("id")
            item["latest_task_status"] = latest_task.get("status")
        items.append(item)
    items.sort(key=lambda item: (item.get("updated_at") or "", item["id"]), reverse=True)
    return {"items": items, "total": len(items)}


def patch_ai_executor_runner_response(
    *,
    current_store: Any,
    payload: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    sync_ai_executor_runner_store(current_store)
    runner = current_store.ai_executor_runners.get(runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "endpoint_url" in updates:
        updates["endpoint_url"] = _ensure_non_blank(updates["endpoint_url"], "endpoint_url")
    if "protocol" in updates:
        updates["protocol"] = _ensure_enum(
            updates["protocol"],
            AI_EXECUTOR_RUNNER_PROTOCOLS,
            "protocol",
        )
    if "status" in updates:
        updates["status"] = _ensure_enum(
            updates["status"],
            AI_EXECUTOR_RUNNER_STATUSES,
            "status",
        )
    if "executor_types" in updates:
        updates["executor_types"] = _normalized_executor_types(updates["executor_types"])
    if "workspace_roots" in updates:
        updates["workspace_roots"] = _normalized_string_list(
            updates["workspace_roots"],
            "workspace_roots",
        )
    if "runner_token" in updates:
        updates["token_hash"] = _token_hash(
            _ensure_non_blank(updates.pop("runner_token"), "runner_token"),
        )
        updates["token_rotated_at"] = datetime.now(UTC).isoformat()
        updates["token_version"] = int(runner.get("token_version") or 1) + 1
    for int_key in ("heartbeat_timeout_seconds", "max_concurrent_tasks"):
        if int_key in updates:
            updates[int_key] = int(updates[int_key])
    if "metadata" in updates:
        updates["metadata"] = dict(updates["metadata"] or {})
    runner = {**runner, **updates, "updated_at": datetime.now(UTC).isoformat()}
    current_store.ai_executor_runners[runner_id] = runner
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.updated",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={
            "executor_types": runner["executor_types"],
            "protocol": runner["protocol"],
            "status": runner["status"],
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return _runner_public(runner)


def rotate_ai_executor_runner_token_response(
    *,
    current_store: Any,
    payload: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    sync_ai_executor_runner_store(current_store)
    runner = current_store.ai_executor_runners.get(runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    runner_token = str(getattr(payload, "runner_token", None) or secrets.token_urlsafe(32))
    now = datetime.now(UTC).isoformat()
    runner = {
        **runner,
        "token_hash": _token_hash(_ensure_non_blank(runner_token, "runner_token")),
        "token_rotated_at": now,
        "token_version": int(runner.get("token_version") or 1) + 1,
        "updated_at": now,
    }
    current_store.ai_executor_runners[runner_id] = runner
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.token_rotated",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={"token_version": runner["token_version"]},
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return {**_runner_public(runner), "runner_token": runner_token}


def delete_ai_executor_runner_response(
    *,
    current_store: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    sync_ai_executor_runner_store(current_store)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    runner = current_store.ai_executor_runners.get(runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    active_tasks = [
        task["id"]
        for task in current_store.ai_executor_tasks.values()
        if task.get("runner_id") == runner_id
        and task.get("status") not in AI_EXECUTOR_TASK_TERMINAL_STATUSES
    ]
    if active_tasks:
        raise api_error(
            409,
            "AI_EXECUTOR_RUNNER_IN_USE",
            "AI executor runner has active tasks: " + ", ".join(active_tasks),
        )
    current_store.ai_executor_runners.pop(runner_id, None)
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.deleted",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={"name": runner["name"], "protocol": runner["protocol"]},
    )
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_ai_executor_runner_record", None)
    if callable(delete_record):
        delete_record(runner_id, audit_event=audit_event)
    return {"deleted": True, "id": runner_id}


def _runner_token_from_request(request: Request) -> str:
    explicit = request.headers.get("X-Runner-Token")
    if explicit:
        return explicit.strip()
    authorization = request.headers.get("Authorization") or ""
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    raise api_error(401, "AI_EXECUTOR_RUNNER_TOKEN_REQUIRED", "Runner token is required")


def _authenticated_runner(
    current_store: Any,
    *,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    sync_ai_executor_runner_store(current_store)
    runner = current_store.ai_executor_runners.get(runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    token = _runner_token_from_request(request)
    if not secrets.compare_digest(_token_hash(token), str(runner.get("token_hash") or "")):
        raise api_error(401, "AI_EXECUTOR_RUNNER_TOKEN_INVALID", "Runner token is invalid")
    if runner.get("status") == "disabled":
        raise api_error(409, "AI_EXECUTOR_RUNNER_DISABLED", "AI executor runner is disabled")
    return runner


def runner_heartbeat_response(
    *,
    current_store: Any,
    metadata: dict[str, Any] | None,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    runner = _authenticated_runner(current_store, request=request, runner_id=runner_id)
    now = datetime.now(UTC).isoformat()
    merged_metadata = {**dict(runner.get("metadata") or {}), **dict(metadata or {})}
    runner = {
        **runner,
        "last_heartbeat_at": now,
        "metadata": merged_metadata,
        "status": "active" if runner.get("status") != "disabled" else "disabled",
        "updated_at": now,
    }
    current_store.ai_executor_runners[runner_id] = runner
    _persist_record(current_store, "save_ai_executor_runner_record", runner)
    return _runner_public(runner)


def _workspace_allowed(runner: dict[str, Any], workspace_root: str) -> bool:
    roots = [str(root) for root in runner.get("workspace_roots") or []]
    if not roots or "*" in roots:
        return True
    return workspace_root in roots


def find_available_runner(
    current_store: Any,
    *,
    executor_type: str,
    runner_id: str | None,
    workspace_root: str,
) -> dict[str, Any]:
    sync_ai_executor_runner_store(current_store)
    candidates = list(current_store.ai_executor_runners.values())
    if runner_id:
        candidates = [runner for runner in candidates if runner.get("id") == runner_id]
    for runner in candidates:
        if runner.get("status") != "active":
            continue
        if executor_type not in (runner.get("executor_types") or []):
            continue
        if not _workspace_allowed(runner, workspace_root):
            continue
        return runner
    raise api_error(
        409,
        "AI_EXECUTOR_RUNNER_UNAVAILABLE",
        "No active AI executor runner supports the requested executor and workspace",
    )


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
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    task_id = current_store.new_id("ai_executor_task")
    task = {
        "action_id": action_id,
        "claimed_at": None,
        "connection_id": connection_id,
        "created_at": now,
        "created_by": created_by,
        "error_code": None,
        "error_message": None,
        "executor_type": executor_type,
        "finished_at": None,
        "id": task_id,
        "input_payload": input_payload,
        "instruction": instruction,
        "logs": [],
        "plugin_invocation_log_id": plugin_invocation_log_id,
        "request_config": request_config,
        "result_json": {},
        "runner_id": runner_id,
        "scheduled_job_id": scheduled_job_id,
        "scheduled_job_run_id": scheduled_job_run_id,
        "status": "queued",
        "timeout_seconds": timeout_seconds,
        "updated_at": now,
        "workspace_root": workspace_root,
    }
    current_store.ai_executor_tasks[task_id] = task
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
            "workspace_root": workspace_root,
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    return task


def claim_ai_executor_task_response(
    *,
    current_store: Any,
    executor_type: str | None,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    runner = _authenticated_runner(current_store, request=request, runner_id=runner_id)
    requested_executor = executor_type.lower() if isinstance(executor_type, str) else None
    if requested_executor is not None:
        _ensure_enum(requested_executor, AI_EXECUTOR_TYPES, "executor_type")
    sync_ai_executor_task_store(current_store, runner_id=runner_id, status="queued")
    queued = [
        task
        for task in current_store.ai_executor_tasks.values()
        if task.get("runner_id") == runner_id
        and task.get("status") == "queued"
        and (requested_executor is None or task.get("executor_type") == requested_executor)
    ]
    queued.sort(key=lambda task: (task.get("created_at") or "", task["id"]))
    if not queued:
        return {"task": None}
    task = queued[0]
    if task.get("executor_type") not in (runner.get("executor_types") or []):
        raise api_error(
            409,
            "AI_EXECUTOR_TASK_UNSUPPORTED",
            "Runner does not support task executor",
        )
    now = datetime.now(UTC).isoformat()
    task = {**task, "claimed_at": now, "status": "claimed", "updated_at": now}
    current_store.ai_executor_tasks[task["id"]] = task
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.claimed",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task["id"],
        payload={"executor_type": task["executor_type"], "runner_id": runner_id},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    return {"task": _task_public(task)}


def _sync_ai_executor_task_by_id(current_store: Any, task_id: str) -> dict[str, Any]:
    sync_ai_executor_task_store(current_store)
    task = current_store.ai_executor_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    return task


def _log_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _append_task_logs(task: dict[str, Any], logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = [dict(item) for item in task.get("logs") or [] if isinstance(item, dict)]
    next_sequence = int(existing[-1].get("sequence") or len(existing)) + 1 if existing else 1
    normalized: list[dict[str, Any]] = []
    for item in logs:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "level": str(item.get("level") or "info"),
                "message": str(item.get("message") or ""),
                "sequence": int(item.get("sequence") or next_sequence),
                "timestamp": item.get("timestamp") or _log_timestamp(),
            }
        )
        next_sequence += 1
    return [*existing, *normalized]


def list_ai_executor_task_logs_response(
    *,
    current_store: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    task = _sync_ai_executor_task_by_id(current_store, task_id)
    return {"logs": list(task.get("logs") or []), "task": _task_public(task)}


def append_ai_executor_task_logs_response(
    *,
    current_store: Any,
    payload: Any,
    request: Request,
    task_id: str,
) -> dict[str, Any]:
    runner_id = _ensure_non_blank(getattr(payload, "runner_id", None), "runner_id")
    _authenticated_runner(current_store, request=request, runner_id=runner_id)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    task = current_store.ai_executor_tasks.get(task_id)
    if task is None or task.get("runner_id") != runner_id:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
        raise api_error(409, "AI_EXECUTOR_TASK_TERMINAL", "Terminal task cannot append logs")
    status = str(getattr(payload, "status", None) or task.get("status") or "running")
    if status not in {"claimed", "running"}:
        raise api_error(400, "VALIDATION_ERROR", "Log append status is invalid")
    now = datetime.now(UTC).isoformat()
    task = {
        **task,
        "logs": _append_task_logs(task, list(getattr(payload, "logs", None) or [])),
        "status": status,
        "updated_at": now,
    }
    current_store.ai_executor_tasks[task_id] = task
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.logs_appended",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={"log_count": len(getattr(payload, "logs", None) or []), "runner_id": runner_id},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(current_store, task=task, runner_id=runner_id)
    return {"logs": list(task.get("logs") or []), "task": _task_public(task)}


def cancel_ai_executor_task_response(
    *,
    current_store: Any,
    payload: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    task = _sync_ai_executor_task_by_id(current_store, task_id)
    if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
        raise api_error(409, "AI_EXECUTOR_TASK_TERMINAL", "Terminal task cannot be cancelled")
    now = datetime.now(UTC).isoformat()
    reason = str(getattr(payload, "reason", None) or "cancelled by user")
    task = {
        **task,
        "error_code": "AI_EXECUTOR_TASK_CANCELLED",
        "error_message": reason,
        "finished_at": now,
        "logs": _append_task_logs(
            task,
            [{"level": "warning", "message": f"Task cancelled: {reason}", "timestamp": now}],
        ),
        "status": "cancelled",
        "updated_at": now,
    }
    current_store.ai_executor_tasks[task_id] = task
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.cancelled",
        actor_id=user["id"],
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={"reason": reason, "runner_id": task.get("runner_id")},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=task,
        runner_id=str(task.get("runner_id") or user["id"]),
    )
    return {"task": _task_public(task)}


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


def timeout_ai_executor_tasks_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    now = _datetime_value(getattr(payload, "now", None)) or datetime.now(UTC)
    sync_ai_executor_task_store(current_store)
    timed_out: list[dict[str, Any]] = []
    for task in list(current_store.ai_executor_tasks.values()):
        if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
            continue
        reference_at = (
            _datetime_value(task.get("claimed_at"))
            or _datetime_value(task.get("updated_at"))
            or _datetime_value(task.get("created_at"))
            or now
        )
        timeout_seconds = int(task.get("timeout_seconds") or 1800)
        if (now - reference_at).total_seconds() < timeout_seconds:
            continue
        now_iso = now.isoformat()
        updated_task = {
            **task,
            "error_code": "AI_EXECUTOR_TASK_TIMEOUT",
            "error_message": f"AI executor task timed out after {timeout_seconds}s",
            "finished_at": now_iso,
            "logs": _append_task_logs(
                task,
                [
                    {
                        "level": "error",
                        "message": f"Task timed out after {timeout_seconds}s",
                        "timestamp": now_iso,
                    }
                ],
            ),
            "status": "timed_out",
            "updated_at": now_iso,
        }
        current_store.ai_executor_tasks[updated_task["id"]] = updated_task
        audit_event = record_audit_event(
            current_store,
            event_type="ai_executor_task.timed_out",
            actor_id=user["id"],
            subject_type="ai_executor_task",
            subject_id=updated_task["id"],
            payload={
                "runner_id": updated_task.get("runner_id"),
                "timeout_seconds": timeout_seconds,
            },
        )
        _persist_record(
            current_store,
            "save_ai_executor_task_record",
            updated_task,
            audit_event=audit_event,
        )
        _sync_runner_completion_to_scheduled_run(
            current_store,
            task=updated_task,
            runner_id=str(updated_task.get("runner_id") or user["id"]),
        )
        timed_out.append(updated_task)
    return {
        "timed_out_task_ids": [task["id"] for task in timed_out],
        "tasks": [_task_public(task) for task in timed_out],
    }


def complete_ai_executor_task_response(
    *,
    current_store: Any,
    payload: Any,
    request: Request,
    task_id: str,
) -> dict[str, Any]:
    runner_id = _ensure_non_blank(getattr(payload, "runner_id", None), "runner_id")
    _authenticated_runner(current_store, request=request, runner_id=runner_id)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    task = current_store.ai_executor_tasks.get(task_id)
    if task is None or task.get("runner_id") != runner_id:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    status = _ensure_enum(getattr(payload, "status", None), AI_EXECUTOR_TASK_STATUSES, "status")
    if status not in AI_EXECUTOR_TASK_TERMINAL_STATUSES and status != "running":
        raise api_error(400, "VALIDATION_ERROR", "Task completion status is invalid")
    now = datetime.now(UTC).isoformat()
    task = {
        **task,
        "error_code": getattr(payload, "error_code", None),
        "error_message": getattr(payload, "error_message", None),
        "finished_at": now if status in AI_EXECUTOR_TASK_TERMINAL_STATUSES else None,
        "logs": list(getattr(payload, "logs", None) or []),
        "result_json": dict(getattr(payload, "result_json", None) or {}),
        "status": status,
        "updated_at": now,
    }
    current_store.ai_executor_tasks[task_id] = task
    audit_event = record_audit_event(
        current_store,
        event_type=f"ai_executor_task.{status}",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={
            "executor_type": task["executor_type"],
            "runner_id": runner_id,
            "scheduled_job_id": task.get("scheduled_job_id"),
            "scheduled_job_run_id": task.get("scheduled_job_run_id"),
            "status": status,
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    return {"task": _task_public(task)}
