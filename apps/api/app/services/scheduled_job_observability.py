from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any


def _scheduled_jobs_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    required_methods = ("list_scheduled_job_runs", "list_scheduled_jobs")
    if all(callable(getattr(repository, method_name, None)) for method_name in required_methods):
        return repository
    return None


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def _scheduled_job_rows(current_store: Any) -> list[dict[str, Any]]:
    repository = _scheduled_jobs_repository(current_store)
    if repository is not None:
        return repository.list_scheduled_jobs(enabled=None, job_type=None, status=None)
    return list(_memory_dict(current_store, "scheduled_jobs").values())


def _scheduled_job_run_rows(current_store: Any) -> list[dict[str, Any]]:
    repository = _scheduled_jobs_repository(current_store)
    if repository is not None:
        return repository.list_scheduled_job_runs(scheduled_job_id=None, status=None)
    return list(_memory_dict(current_store, "scheduled_job_runs").values())


def _scheduled_job_run_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _scheduled_job_run_latency_ms(run: dict[str, Any]) -> int | None:
    explicit_latency = run.get("latency_ms")
    if isinstance(explicit_latency, int | float) and not isinstance(explicit_latency, bool):
        return max(int(explicit_latency), 0)
    started_at = _scheduled_job_run_datetime(run.get("started_at"))
    finished_at = _scheduled_job_run_datetime(run.get("finished_at"))
    if started_at is None or finished_at is None:
        return None
    return max(int((finished_at - started_at).total_seconds() * 1000), 0)


def _scheduled_job_run_nodes(run: dict[str, Any]) -> dict[str, Any]:
    result_summary = run.get("result_summary") or {}
    if not isinstance(result_summary, dict):
        return {}
    execution_nodes = result_summary.get("execution_nodes") or {}
    return execution_nodes if isinstance(execution_nodes, dict) else {}


def _scheduled_job_run_model_gateway_called(run: dict[str, Any]) -> bool:
    result_summary = run.get("result_summary") or {}
    processing = result_summary.get("processing") if isinstance(result_summary, dict) else None
    execution_nodes = _scheduled_job_run_nodes(run)
    skill_processing = execution_nodes.get("skill_processing")
    if isinstance(skill_processing, dict):
        if isinstance(skill_processing.get("model_gateway_called"), bool):
            return skill_processing["model_gateway_called"]
        if skill_processing.get("model_log_id"):
            return True
    if isinstance(processing, dict) and isinstance(processing.get("model_gateway_called"), bool):
        return processing["model_gateway_called"]
    return False


def _scheduled_job_run_model_log_id(run: dict[str, Any]) -> str | None:
    result_summary = run.get("result_summary") or {}
    execution_nodes = _scheduled_job_run_nodes(run)
    skill_processing = execution_nodes.get("skill_processing")
    if isinstance(skill_processing, dict) and skill_processing.get("model_log_id"):
        return str(skill_processing["model_log_id"])
    processing = result_summary.get("processing") if isinstance(result_summary, dict) else None
    if isinstance(processing, dict) and processing.get("model_log_id"):
        return str(processing["model_log_id"])
    return None


def _model_gateway_log_total_tokens(log: dict[str, Any] | None) -> int:
    if not isinstance(log, dict):
        return 0
    tokens = log.get("tokens")
    if isinstance(tokens, dict):
        for key in ("total", "total_tokens"):
            value = tokens.get(key)
            if isinstance(value, int | float) and not isinstance(value, bool):
                return int(value)
        prompt = tokens.get("prompt") or tokens.get("prompt_tokens") or 0
        completion = tokens.get("completion") or tokens.get("completion_tokens") or 0
        if isinstance(prompt, int | float) and isinstance(completion, int | float):
            return int(prompt + completion)
    usage = log.get("usage")
    if isinstance(usage, dict):
        value = usage.get("total_tokens") or usage.get("total")
        if isinstance(value, int | float) and not isinstance(value, bool):
            return int(value)
    return 0


def _model_gateway_log_index(current_store: Any) -> dict[str, dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_logs = getattr(repository, "list_model_gateway_logs", None)
    if callable(list_logs):
        logs = list_logs()
    else:
        logs = getattr(current_store, "model_gateway_logs", [])
    if isinstance(logs, dict):
        iterable = logs.values()
    else:
        iterable = logs or []
    return {
        str(log["id"]): log
        for log in iterable
        if isinstance(log, dict) and log.get("id")
    }


def _counter_distribution(counter: Counter[str], *, key_name: str) -> list[dict[str, Any]]:
    return [
        {key_name: key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _percentage(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total * 100, 2)


def scheduled_job_run_observability_response(*, current_store: Any) -> dict[str, Any]:
    runs = _scheduled_job_run_rows(current_store)
    jobs_by_id = {
        str(job["id"]): job
        for job in _scheduled_job_rows(current_store)
        if job.get("id") is not None
    }
    model_logs_by_id = _model_gateway_log_index(current_store)

    status_counter: Counter[str] = Counter()
    job_type_counter: Counter[str] = Counter()
    trigger_type_counter: Counter[str] = Counter()
    error_counter: Counter[str] = Counter()
    write_target_counter: Counter[str] = Counter()
    latencies: list[int] = []
    model_log_ids: set[str] = set()
    model_gateway_called_runs = 0
    plugin_invocation_runs = 0
    action_write_runs = 0
    action_write_success_runs = 0
    records_imported_total = 0
    slow_runs: list[dict[str, Any]] = []
    recent_failures: list[dict[str, Any]] = []

    for run in runs:
        status = str(run.get("status") or "unknown")
        status_counter[status] += 1
        scheduled_job_id = str(run.get("scheduled_job_id") or "")
        job = jobs_by_id.get(scheduled_job_id) or {}
        config_snapshot = (
            run.get("config_snapshot") if isinstance(run.get("config_snapshot"), dict) else {}
        )
        job_type = str(job.get("job_type") or config_snapshot.get("job_type") or "unknown")
        job_name = str(job.get("name") or config_snapshot.get("name") or scheduled_job_id or "-")
        job_type_counter[job_type] += 1
        trigger_type_counter[str(run.get("trigger_type") or "unknown")] += 1
        records_imported = run.get("records_imported")
        if isinstance(records_imported, int | float) and not isinstance(records_imported, bool):
            records_imported_total += int(records_imported)
        latency_ms = _scheduled_job_run_latency_ms(run)
        if latency_ms is not None:
            latencies.append(latency_ms)
            slow_runs.append(
                {
                    "error_code": run.get("error_code"),
                    "id": run["id"],
                    "job_name": job_name,
                    "latency_ms": latency_ms,
                    "records_imported": int(records_imported or 0),
                    "scheduled_job_id": scheduled_job_id or None,
                    "started_at": run.get("started_at"),
                    "status": status,
                },
            )
        if run.get("plugin_invocation_log_id"):
            plugin_invocation_runs += 1
        if _scheduled_job_run_model_gateway_called(run):
            model_gateway_called_runs += 1
        model_log_id = _scheduled_job_run_model_log_id(run)
        if model_log_id:
            model_log_ids.add(model_log_id)
        execution_nodes = _scheduled_job_run_nodes(run)
        result_action = execution_nodes.get("result_action")
        if isinstance(result_action, dict):
            action_write_runs += 1
            if result_action.get("status") == "succeeded":
                action_write_success_runs += 1
            write_target = result_action.get("write_target") or result_action.get(
                "write_target_label",
            )
            if write_target:
                write_target_counter[str(write_target)] += 1
        if status == "failed":
            failure_key = str(
                run.get("error_code")
                or run.get("error_message")
                or "unknown_error",
            )
            error_counter[failure_key] += 1
            recent_failures.append(
                {
                    "error_code": run.get("error_code"),
                    "error_message": run.get("error_message"),
                    "id": run["id"],
                    "job_name": job_name,
                    "latency_ms": latency_ms,
                    "scheduled_job_id": scheduled_job_id or None,
                    "started_at": run.get("started_at"),
                },
            )

    total_runs = len(runs)
    succeeded_runs = status_counter.get("succeeded", 0)
    failed_runs = status_counter.get("failed", 0)
    cancelled_runs = status_counter.get("cancelled", 0)
    running_runs = status_counter.get("running", 0) + status_counter.get("queued", 0)
    token_total = sum(
        _model_gateway_log_total_tokens(model_logs_by_id.get(model_log_id))
        for model_log_id in model_log_ids
    )
    slow_runs.sort(
        key=lambda item: (item.get("latency_ms") or 0, item.get("started_at") or ""),
        reverse=True,
    )
    recent_failures.sort(key=lambda item: item.get("started_at") or "", reverse=True)

    return {
        "error_distribution": _counter_distribution(error_counter, key_name="error"),
        "generated_at": datetime.now(UTC).isoformat(),
        "job_type_distribution": _counter_distribution(job_type_counter, key_name="job_type"),
        "recent_failures": recent_failures[:5],
        "slow_runs": slow_runs[:5],
        "status_distribution": _counter_distribution(status_counter, key_name="status"),
        "summary": {
            "action_write_runs": action_write_runs,
            "action_write_success_rate": _percentage(
                action_write_success_runs,
                action_write_runs,
            ),
            "action_write_success_runs": action_write_success_runs,
            "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "average_records_imported": round(records_imported_total / total_runs, 2)
            if total_runs
            else 0,
            "cancelled_runs": cancelled_runs,
            "failed_runs": failed_runs,
            "failure_rate": _percentage(failed_runs, total_runs),
            "model_gateway_called_runs": model_gateway_called_runs,
            "model_gateway_token_total": token_total,
            "plugin_invocation_runs": plugin_invocation_runs,
            "running_runs": running_runs,
            "success_rate": _percentage(succeeded_runs, total_runs),
            "succeeded_runs": succeeded_runs,
            "total_runs": total_runs,
        },
        "trigger_type_distribution": _counter_distribution(
            trigger_type_counter,
            key_name="trigger_type",
        ),
        "write_target_distribution": _counter_distribution(
            write_target_counter,
            key_name="write_target",
        ),
    }
