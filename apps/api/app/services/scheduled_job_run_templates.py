from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services import scheduled_job_store as job_store
from app.services.scheduled_job_access import require_admin
from app.services.scheduled_job_templates import STANDARD_WIZARD_STEPS


def scheduled_job_template_from_run_response(
    *,
    current_store: Any,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    job_store.sync_scheduled_job_run_store(current_store)
    run = job_store.read_memory_dict(current_store, "scheduled_job_runs").get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job run not found")
    if run.get("status") != "succeeded":
        raise api_error(
            409,
            "SCHEDULED_JOB_RUN_NOT_SUCCESSFUL",
            "Only successful scheduled job runs can generate templates",
        )
    config = dict(run.get("config_snapshot") or {})
    job_name = str(config.get("name") or run.get("scheduled_job_id") or run_id)
    payload_keys = (
        "agent_id",
        "config_json",
        "cron_expression",
        "enabled",
        "execution_mode",
        "interval_seconds",
        "job_type",
        "knowledge_document_ids",
        "lock_ttl_seconds",
        "max_retry_count",
        "model_gateway_config_id",
        "plugin_action_id",
        "plugin_action_ids",
        "plugin_connection_id",
        "plugin_connection_ids",
        "plugin_input_mapping",
        "plugin_output_mapping",
        "product_id",
        "result_actions",
        "schedule_type",
        "skill_ids",
        "source_system",
        "timeout_seconds",
        "timezone",
    )
    payload_defaults = {
        key: config.get(key)
        for key in payload_keys
        if key in config and config.get(key) is not None
    }
    source = {
        "source_id": run_id,
        "source_type": "scheduled_job_run",
        "title": job_name,
    }
    config_json = dict(payload_defaults.get("config_json") or {})
    config_json["template_source"] = source
    payload_defaults["config_json"] = config_json
    payload_defaults["enabled"] = True
    payload_defaults["name"] = f"{job_name} 模板"
    return {
        "category": str(config.get("job_type") or "generated"),
        "code": f"generated_from_{run_id}",
        "description": f"由成功运行 {run_id} 反向生成，可作为新增定时作业模板。",
        "name": f"{job_name} 模板",
        "payload_defaults": payload_defaults,
        "recommended_scenarios": ["成功运行复用", "配置模板化", "快速创建同类任务"],
        "resource_selectors": {},
        "source_run_id": run_id,
        "template_version": "generated-v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    }
