from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.api.deps import api_error
from app.services.plugin_result_mapping import (
    json_path_value,
    records_imported_from_mapping,
)
from app.services.scheduled_job_ai_processing import (
    run_scheduled_job_ai_processing,
    skill_codes_for_job,
)
from app.services.scheduled_job_constants import USER_FEEDBACK_INSIGHT_WRITE_TARGETS
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_store import read_memory_dict as _read_memory_dict
from app.services.user_feedback import (
    USER_FEEDBACK_SENTIMENTS,
    USER_FEEDBACK_TYPES,
    create_user_feedback_response,
)


def normalized_insight_enum(value: Any, allowed_values: set[str], fallback: str) -> str:
    if isinstance(value, str) and value in allowed_values:
        return value
    return fallback


def resolve_job_plugin_output_mapping(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    job_mapping = job.get("plugin_output_mapping") or {}
    if job_mapping:
        return job_mapping
    action_id = job.get("plugin_action_id")
    if not action_id:
        return {}
    action = _read_memory_dict(current_store, "plugin_actions").get(action_id) or {}
    action_mapping = action.get("result_mapping") or {}
    return dict(action_mapping) if isinstance(action_mapping, dict) else {}


def run_user_feedback_insight_extract_job(
    current_store: Any,
    *,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    mapping = resolve_job_plugin_output_mapping(current_store, job)
    write_target = str(mapping.get("write_target") or "user_feedback_insights")
    if write_target not in USER_FEEDBACK_INSIGHT_WRITE_TARGETS:
        raise api_error(
            400,
            "PLUGIN_WRITE_TARGET_UNSUPPORTED",
            f"Unsupported write_target for user_feedback_insight_extract: {write_target}",
        )
    source_response_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
    if not isinstance(source_response_json, dict):
        source_response_json = {}
    source_row_count = records_imported_from_mapping(
        plugin_summary.get("response_summary") or {},
        {"records_imported_path": mapping.get("records_imported_path")},
    )
    ai_processing = run_scheduled_job_ai_processing(
        current_store,
        job=job,
        output_mapping=mapping,
        source_response_json=source_response_json,
        source_row_count=source_row_count,
        user=user,
    )
    processed_json = ai_processing["output_json"]
    insights = json_path_value(processed_json, str(mapping.get("insights_path") or "$.insights"))
    if insights is None:
        insights = []
    if not isinstance(insights, list):
        raise api_error(400, "PLUGIN_RESULT_INVALID", "Mapped insights result must be a list")

    created_ids: list[str] = []
    skipped = 0
    if write_target == "user_feedback_insights":
        for insight in insights:
            if not isinstance(insight, dict) or not str(insight.get("content") or "").strip():
                skipped += 1
                continue
            product_id = insight.get("product_id") or job.get("product_id")
            if not isinstance(product_id, str) or not product_id:
                skipped += 1
                continue
            feature_code = insight.get("feature_code")
            module_code = insight.get("module_code")
            related_requirement_id = insight.get("related_requirement_id")
            payload = SimpleNamespace(
                content=str(insight["content"]),
                feature_code=feature_code if isinstance(feature_code, str) else None,
                feedback_type=normalized_insight_enum(
                    insight.get("feedback_type"),
                    USER_FEEDBACK_TYPES,
                    "improvement",
                ),
                module_code=module_code if isinstance(module_code, str) else None,
                product_id=product_id,
                related_requirement_id=related_requirement_id
                if isinstance(related_requirement_id, str)
                else None,
                satisfaction_score=insight.get("satisfaction_score")
                if isinstance(insight.get("satisfaction_score"), int)
                else None,
                sentiment=normalized_insight_enum(
                    insight.get("sentiment"),
                    USER_FEEDBACK_SENTIMENTS,
                    "neutral",
                ),
                source_channel=str(insight.get("source_channel") or "maxcompute_weekly_ai"),
                tags=insight.get("tags") if isinstance(insight.get("tags"), list) else [],
            )
            created = create_user_feedback_response(
                current_store=current_store,
                payload=payload,
                user=user,
            )
            created_ids.append(created["id"])

    skill_ids = list(job.get("skill_ids", []))
    skill_codes = skill_codes_for_job(current_store, job)
    summary = {
        "execution_nodes": {
            "data_connection": JobExecutionEngine.data_connection_execution_node(
                job=job,
                plugin_summary=plugin_summary,
                records_imported=source_row_count,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            ),
            "result_action": {
                "action_id": plugin_summary.get("action_id") or job.get("plugin_action_id"),
                "created_ids": created_ids,
                "feedback": {
                    "created_ids": created_ids,
                    "records_imported": len(created_ids),
                    "skipped_insights": skipped,
                    "stored_in_run_result": write_target == "scheduled_job_result",
                    "write_target": write_target,
                },
                "label": "结果动作反馈内容",
                "records_imported": len(created_ids),
                "skipped_insights": skipped,
                "status": "succeeded",
                "write_target": write_target,
            },
            "skill_processing": {
                "input": {
                    "insights_path": str(mapping.get("insights_path") or "$.insights"),
                    "knowledge_references": ai_processing.get("knowledge_references") or [],
                    "source_row_count": source_row_count,
                },
                "label": "Skill 处理后内容",
                "model_gateway_called": True,
                "model_gateway_config_id": ai_processing["model_gateway_config_id"],
                "model_log_id": ai_processing["model_log_id"],
                "note": "数据连接返回内容已通过平台 AI 大模型处理为结果动作可消费的结构化 JSON。",
                "output": {
                    "candidate_count": len(insights),
                    "insights": insights,
                    "insights_created": len(created_ids),
                    "processed_json": processed_json,
                    "skipped_insights": skipped,
                },
                "processing_mode": "model_gateway_json_transform",
                "skill_codes": skill_codes,
                "skill_ids": skill_ids,
                "status": ai_processing["status"],
            },
        },
        "insight_ids": created_ids,
        "insights_created": len(created_ids),
        "plugin": plugin_summary,
        "processing": {
            "skill_ids": skill_ids,
            "skill_codes": skill_codes,
        },
        "skipped_insights": skipped,
        "source_row_count": source_row_count,
        "write_target": write_target,
    }
    return summary, len(created_ids)
