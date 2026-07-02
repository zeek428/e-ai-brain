from __future__ import annotations

from typing import Any

from app.services.scheduled_job_sample_reuse_wizard import scheduled_job_dry_run_reuse_wizard


def dry_run_sample_reuse_summary(
    *,
    job: dict[str, Any],
    output_preview: dict[str, Any],
    plugin_summary: dict[str, Any] | None,
    records_imported: int,
    result_actions: list[dict[str, Any]],
    result_action_preview_source: str,
    resolved_input_mapping: dict[str, Any],
) -> dict[str, Any]:
    response_summary = plugin_summary.get("response_summary") if plugin_summary else {}
    response_json = response_summary.get("json") if isinstance(response_summary, dict) else None
    response_available = isinstance(response_json, dict) and bool(response_json)
    data_connection_sample_source = (
        str(plugin_summary.get("sample_source"))
        if plugin_summary and plugin_summary.get("sample_source")
        else "live_dry_run_response"
    )
    action_preview_ready = any(
        isinstance(action.get("write_preview"), dict)
        and bool(action.get("write_preview"))
        for action in result_actions
    )
    job_config_preview = {
        "config_json": job.get("config_json") or {},
        "plugin_action_id": job.get("plugin_action_id"),
        "plugin_action_ids": list(job.get("plugin_action_ids") or []),
        "plugin_connection_id": job.get("plugin_connection_id"),
        "plugin_connection_ids": list(job.get("plugin_connection_ids") or []),
        "plugin_input_mapping": resolved_input_mapping,
        "plugin_output_mapping": job.get("plugin_output_mapping") or {},
        "result_actions": list(job.get("result_actions") or []),
    }
    steps = [
        {
            "key": "data_connection_sample",
            "label": "复用数据连接样例",
            "source": data_connection_sample_source if response_available else "not_available",
            "status": "ready" if response_available else "not_available",
        },
        {
            "key": "action_write_preview",
            "label": "预览动作写入",
            "source": result_action_preview_source,
            "status": "ready" if action_preview_ready else "not_configured",
        },
        {
            "key": "scheduled_job_config",
            "label": "保存为定时作业配置",
            "source": "current_dry_run_payload",
            "status": "ready",
        },
    ]
    return {
        "action_preview_ready": action_preview_ready,
        "data_connection_sample": {
            "records_imported": records_imported,
            "response_available": response_available,
            "source": data_connection_sample_source if response_available else "not_available",
            "status": "ready" if response_available else "not_available",
        },
        "job_config_preview": job_config_preview,
        "output_preview_ready": bool(output_preview),
        "preferred_action_preview_source": result_action_preview_source,
        "reusable_steps": steps,
        "reuse_wizard": scheduled_job_dry_run_reuse_wizard(
            action_preview_ready=action_preview_ready,
            data_connection_sample_source=data_connection_sample_source,
            output_preview_ready=bool(output_preview),
            response_available=response_available,
            result_action_preview_source=result_action_preview_source,
        ),
    }
