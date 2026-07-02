from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services.scheduled_job_ai_processing import (
    run_scheduled_job_ai_processing,
    skill_codes_for_job,
)
from app.services.scheduled_job_config import scheduled_job_result_action_policy
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_result_actions import (
    execute_generic_result_actions,
    inferred_output_record_count,
)
from app.services.scheduled_job_user_feedback import resolve_job_plugin_output_mapping


def run_plugin_action_ai_processing_job(
    current_store: Any,
    *,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    if plugin_summary.get("status") != "succeeded":
        raise api_error(
            502,
            plugin_summary.get("error_code") or "PLUGIN_ACTION_FAILED",
            plugin_summary.get("error_message") or "Scheduled job data connection failed",
        )
    output_mapping = {
        "write_target": "scheduled_job_result",
        **resolve_job_plugin_output_mapping(current_store, job),
    }
    source_response_json = (plugin_summary.get("response_summary") or {}).get("json")
    if not isinstance(source_response_json, dict):
        source_response_json = (
            {}
            if source_response_json is None
            else {"value": source_response_json}
        )
    source_row_count = JobExecutionEngine.plugin_records_imported_from_result(
        plugin_summary,
        output_mapping,
    )
    ai_processing = run_scheduled_job_ai_processing(
        current_store,
        job=job,
        output_mapping=output_mapping,
        source_response_json=source_response_json,
        source_row_count=source_row_count,
        user=user,
    )
    processed_json = ai_processing["output_json"]
    result_actions, action_records_imported = execute_generic_result_actions(
        job=job,
        output_json=processed_json,
        output_mapping=output_mapping,
        result_actions=job.get("result_actions") or [],
    )
    primary_result_action = result_actions[0] if result_actions else {}
    skill_ids = list(job.get("skill_ids", []))
    skill_codes = skill_codes_for_job(current_store, job)
    records_imported = max(
        action_records_imported,
        inferred_output_record_count(processed_json, output_mapping),
    )
    summary = {
        "execution_nodes": {
            "data_connection": JobExecutionEngine.data_connection_execution_node(
                job=job,
                plugin_summary=plugin_summary,
                records_imported=source_row_count,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            ),
            "result_action": primary_result_action,
            "result_actions": result_actions,
            "skill_processing": {
                "input": {
                    "knowledge_references": ai_processing.get("knowledge_references") or [],
                    "source_row_count": source_row_count,
                },
                "label": "Skill 处理后内容",
                "model_gateway_called": True,
                "model_gateway_config_id": ai_processing["model_gateway_config_id"],
                "model_log_id": ai_processing["model_log_id"],
                "note": "数据连接返回内容已通过平台 AI 大模型处理为结果动作可消费的结构化 JSON。",
                "output": {
                    "processed_json": processed_json,
                    "records_imported": records_imported,
                    "summary": (
                        processed_json.get("summary")
                        if isinstance(processed_json, dict)
                        else None
                    ),
                },
                "processing_mode": "model_gateway_json_transform",
                "skill_codes": skill_codes,
                "skill_ids": skill_ids,
                "status": ai_processing["status"],
            },
        },
        "job_type": job.get("job_type"),
        "message": "插件执行调用完成，数据已通过 AI 处理并进入结果动作。",
        "plugin": plugin_summary,
        "processing": {
            "model_gateway_called": True,
            "skill_codes": skill_codes,
            "skill_ids": skill_ids,
        },
        "result_action_policy": scheduled_job_result_action_policy(job),
        "source_row_count": source_row_count,
        "write_target": primary_result_action.get("write_target"),
        "write_targets": [action["write_target"] for action in result_actions],
    }
    return summary, records_imported
