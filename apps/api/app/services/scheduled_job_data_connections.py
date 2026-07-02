from __future__ import annotations

from typing import Any

from app.services import scheduled_job_store as job_store
from app.services.plugins import invoke_plugin_action_response
from app.services.scheduled_job_access import scheduled_job_plugin_invocation_user
from app.services.scheduled_job_config import scheduled_job_data_connection_policy
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_refs import scheduled_job_multi_ids


def plugin_summary_from_log(current_store: Any, plugin_log: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": plugin_log.get("action_id"),
        "connection_environment": (
            job_store.read_memory_dict(current_store, "plugin_connections").get(
                plugin_log.get("connection_id"),
            )
            or {}
        ).get("environment"),
        "connection_id": plugin_log.get("connection_id"),
        "error_code": plugin_log.get("error_code"),
        "error_message": plugin_log.get("error_message"),
        "invocation_log_id": plugin_log["id"],
        "latency_ms": plugin_log.get("latency_ms"),
        "request_summary": plugin_log.get("request_summary") or {},
        "response_summary": plugin_log.get("response_summary") or {},
        "scheduled_job_id": plugin_log.get("scheduled_job_id"),
        "scheduled_job_run_id": plugin_log.get("scheduled_job_run_id"),
        "status": plugin_log["status"],
    }


def invoke_job_data_connections(
    current_store: Any,
    *,
    job: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    run_id: str,
    trigger_type: str,
    user: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not job.get("plugin_action_id"):
        return None, []
    connection_ids = scheduled_job_multi_ids(
        job,
        "plugin_connection_ids",
        "plugin_connection_id",
    )
    if not connection_ids and job.get("plugin_connection_id"):
        connection_ids = [str(job["plugin_connection_id"])]
    policy = scheduled_job_data_connection_policy(job)
    summaries: list[dict[str, Any]] = []
    for connection_id in connection_ids or [None]:
        job_config = job.get("config_json") or {}
        linked_scheduled_job_id = None if trigger_type == "dry_run" else job["id"]
        linked_scheduled_job_run_id = None if trigger_type == "dry_run" else run_id
        plugin_log = invoke_plugin_action_response(
            action_id=job["plugin_action_id"],
            connection_id=connection_id,
            current_store=current_store,
            input_payload={
                "branch": resolved_plugin_input_mapping.get("branch") or job_config.get("branch"),
                "config": job.get("config_json") or {},
                "input_mapping": resolved_plugin_input_mapping,
                "job_id": job["id"],
                "product_id": job.get("product_id"),
                "repository_id": (
                    resolved_plugin_input_mapping.get("repository_id")
                    or job_config.get("repository_id")
                ),
                "timezone": job.get("timezone") or "UTC",
            },
            raise_on_failed=False,
            scheduled_job_id=linked_scheduled_job_id,
            scheduled_job_run_id=linked_scheduled_job_run_id,
            trigger_type=trigger_type,
            user=scheduled_job_plugin_invocation_user(user),
        )
        summary = plugin_summary_from_log(current_store, plugin_log)
        summaries.append(summary)
        if summary["status"] != "succeeded" and policy["failure_policy"] == "fail_fast":
            break
    merged = JobExecutionEngine.merged_plugin_summary(
        summaries,
        failure_policy=policy["failure_policy"],
        merge_strategy=policy["merge_strategy"],
        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
    )
    return merged, summaries
