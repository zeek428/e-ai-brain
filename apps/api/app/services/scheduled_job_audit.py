from __future__ import annotations

from typing import Any

from app.services.scheduled_job_refs import scheduled_job_multi_ids


def scheduled_job_audit_payload(job: dict[str, Any]) -> dict[str, Any]:
    payload = {"job_type": job["job_type"], "enabled": job["enabled"]}
    plugin_action_ids = scheduled_job_multi_ids(job, "plugin_action_ids", "plugin_action_id")
    plugin_connection_ids = scheduled_job_multi_ids(
        job,
        "plugin_connection_ids",
        "plugin_connection_id",
    )
    if plugin_action_ids:
        payload["plugin_action_ids"] = plugin_action_ids
    if plugin_connection_ids:
        payload["plugin_connection_ids"] = plugin_connection_ids
    assistant_draft = (job.get("config_json") or {}).get("assistant_draft")
    if isinstance(assistant_draft, dict):
        payload["assistant_draft"] = {
            key: value
            for key, value in {
                "draft_id": assistant_draft.get("draft_id"),
                "source": assistant_draft.get("source"),
                "title": assistant_draft.get("title"),
            }.items()
            if value
        }
    template_source = (job.get("config_json") or {}).get("template_source")
    if isinstance(template_source, dict):
        payload["template_source"] = {
            key: value
            for key, value in {
                "source_id": template_source.get("source_id"),
                "source_type": template_source.get("source_type"),
                "title": template_source.get("title"),
            }.items()
            if value
        }
    return payload


def scheduled_job_run_audit_payload(
    *,
    job: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    result_summary = run.get("result_summary") or {}
    execution_nodes = result_summary.get("execution_nodes") or {}
    skill_processing = execution_nodes.get("skill_processing") or {}
    result_action = execution_nodes.get("result_action") or {}
    processing = result_summary.get("processing") or {}
    plugin_snapshot = run.get("resolved_plugin_snapshot") or {}
    plugin = plugin_snapshot.get("plugin") or {}
    connection = plugin_snapshot.get("connection") or {}
    action = plugin_snapshot.get("action") or {}

    model_gateway_called = None
    if isinstance(skill_processing.get("model_gateway_called"), bool):
        model_gateway_called = skill_processing["model_gateway_called"]
    elif isinstance(processing.get("model_gateway_called"), bool):
        model_gateway_called = processing["model_gateway_called"]

    result_action_types = [
        item.get("type")
        for item in (job.get("result_actions") or [])
        if isinstance(item, dict) and item.get("type")
    ]
    payload = {
        "agent_id": job.get("agent_id"),
        "collector_run_id": run.get("collector_run_id"),
        "error_code": run.get("error_code"),
        "execution_mode": job.get("execution_mode"),
        "job_type": job["job_type"],
        "knowledge_document_ids": list(job.get("knowledge_document_ids") or []) or None,
        "model_gateway_called": model_gateway_called,
        "model_gateway_config_id": job.get("model_gateway_config_id"),
        "plugin_action_code": action.get("code"),
        "plugin_action_id": job.get("plugin_action_id"),
        "plugin_action_ids": scheduled_job_multi_ids(
            job,
            "plugin_action_ids",
            "plugin_action_id",
        )
        or None,
        "plugin_code": plugin.get("code"),
        "plugin_connection_environment": connection.get("environment"),
        "plugin_connection_id": job.get("plugin_connection_id"),
        "plugin_connection_ids": scheduled_job_multi_ids(
            job,
            "plugin_connection_ids",
            "plugin_connection_id",
        )
        or None,
        "plugin_invocation_log_id": run.get("plugin_invocation_log_id"),
        "product_id": job.get("product_id"),
        "records_imported": run.get("records_imported", 0),
        "result_action_types": result_action_types or None,
        "result_write_target": result_action.get("write_target")
        or result_summary.get("write_target"),
        "scheduled_job_id": run.get("scheduled_job_id"),
        "skill_ids": list(job.get("skill_ids") or []) or None,
        "source_run_id": run.get("source_run_id"),
        "status": run.get("status"),
        "trigger_type": run.get("trigger_type"),
    }
    return {key: value for key, value in payload.items() if value is not None}
