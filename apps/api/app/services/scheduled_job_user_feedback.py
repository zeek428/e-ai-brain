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
from app.services.scheduled_job_ai_executor import (
    dispatch_scheduled_job_ai_executor_processing,
    pending_ai_executor_result_summary,
    scheduled_job_uses_local_ai_executor,
    system_default_runner_node_from_ai_processing,
)
from app.services.scheduled_job_config import (
    scheduled_job_multi_ids,
    scheduled_job_result_action_policy,
)
from app.services.scheduled_job_constants import USER_FEEDBACK_INSIGHT_WRITE_TARGETS
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_runtime import exception_error_code_and_message
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


def resolve_job_plugin_result_mappings(
    current_store: Any,
    job: dict[str, Any],
) -> list[dict[str, Any]]:
    action_ids = scheduled_job_multi_ids(job, "plugin_action_ids", "plugin_action_id")
    job_mapping = job.get("plugin_output_mapping") or {}
    actions = _read_memory_dict(current_store, "plugin_actions")
    if not action_ids:
        return [
            {
                "action_code": None,
                "action_id": job.get("plugin_action_id"),
                "action_name": None,
                "mapping": dict(job_mapping) if isinstance(job_mapping, dict) else {},
            },
        ]
    result_mappings: list[dict[str, Any]] = []
    for index, action_id in enumerate(action_ids):
        action = actions.get(action_id) or {}
        action_mapping = action.get("result_mapping") if isinstance(action, dict) else {}
        if index == 0 and isinstance(job_mapping, dict) and job_mapping:
            mapping = dict(job_mapping)
        elif isinstance(action_mapping, dict) and action_mapping:
            mapping = dict(action_mapping)
        elif isinstance(job_mapping, dict) and job_mapping:
            mapping = dict(job_mapping)
        else:
            mapping = {}
        result_mappings.append(
            {
                "action_code": action.get("code"),
                "action_id": action_id,
                "action_name": action.get("name"),
                "mapping": mapping,
            },
        )
    return result_mappings


def _write_user_feedback_insights(
    current_store: Any,
    *,
    insights: list[Any],
    job: dict[str, Any],
    user: dict[str, Any],
) -> tuple[list[str], int]:
    created_ids: list[str] = []
    skipped = 0
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
    return created_ids, skipped


def _result_action_base(
    result_mapping: dict[str, Any],
    *,
    write_target: str,
) -> dict[str, Any]:
    return {
        "action_code": result_mapping.get("action_code"),
        "action_id": result_mapping.get("action_id"),
        "action_name": result_mapping.get("action_name"),
        "label": "结果动作反馈内容",
        "write_target": write_target,
    }


def _failed_result_action(
    result_mapping: dict[str, Any],
    *,
    error: Exception,
    write_target: str,
) -> dict[str, Any]:
    error_code, error_message = exception_error_code_and_message(error)
    return {
        **_result_action_base(result_mapping, write_target=write_target),
        "created_ids": [],
        "error_code": error_code,
        "error_message": error_message,
        "feedback": {
            "error_code": error_code,
            "error_message": error_message,
            "records_imported": 0,
            "write_target": write_target,
        },
        "records_imported": 0,
        "skipped_insights": 0,
        "status": "failed",
    }


def user_feedback_result_summary_from_ai_output(
    current_store: Any,
    *,
    ai_processing: dict[str, Any],
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    processed_json: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    source_row_count: int,
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    mapping = resolve_job_plugin_output_mapping(current_store, job)
    result_mappings = resolve_job_plugin_result_mappings(current_store, job)
    result_action_policy = scheduled_job_result_action_policy(job)
    for result_mapping in result_mappings:
        action_mapping = result_mapping.get("mapping") or {}
        write_target = str(action_mapping.get("write_target") or "user_feedback_insights")
        if write_target not in USER_FEEDBACK_INSIGHT_WRITE_TARGETS:
            raise api_error(
                400,
                "PLUGIN_WRITE_TARGET_UNSUPPORTED",
                f"Unsupported write_target for user_feedback_insight_extract: {write_target}",
            )
    insights = json_path_value(processed_json, str(mapping.get("insights_path") or "$.insights"))
    if insights is None:
        insights = []
    if not isinstance(insights, list):
        raise api_error(400, "PLUGIN_RESULT_INVALID", "Mapped insights result must be a list")

    created_ids: list[str] = []
    skipped = 0
    result_actions: list[dict[str, Any]] = []
    for result_mapping in result_mappings:
        action_mapping = result_mapping.get("mapping") or {}
        action_write_target = str(action_mapping.get("write_target") or "user_feedback_insights")
        try:
            action_insights = json_path_value(
                processed_json,
                str(action_mapping.get("insights_path") or "$.insights"),
            )
            if action_insights is None:
                action_insights = []
            if not isinstance(action_insights, list):
                raise api_error(
                    400,
                    "PLUGIN_RESULT_INVALID",
                    "Mapped insights result must be a list",
                )
            action_created_ids: list[str] = []
            action_skipped = 0
            if action_write_target == "user_feedback_insights":
                action_created_ids, action_skipped = _write_user_feedback_insights(
                    current_store,
                    insights=action_insights,
                    job=job,
                    user=user,
                )
                created_ids.extend(action_created_ids)
                skipped += action_skipped
            result_actions.append(
                {
                    **_result_action_base(result_mapping, write_target=action_write_target),
                    "created_ids": action_created_ids,
                    "feedback": {
                        "candidate_count": len(action_insights),
                        "created_ids": action_created_ids,
                        "records_imported": len(action_created_ids),
                        "skipped_insights": action_skipped,
                        "stored_in_run_result": action_write_target == "scheduled_job_result",
                        "write_target": action_write_target,
                    },
                    "records_imported": len(action_created_ids),
                    "skipped_insights": action_skipped,
                    "status": "succeeded",
                },
            )
        except Exception as exc:
            result_actions.append(
                _failed_result_action(
                    result_mapping,
                    error=exc,
                    write_target=action_write_target,
                ),
            )
            if result_action_policy["failure_policy"] == "fail_fast":
                raise
    primary_result_action = (
        result_actions[0]
        if result_actions
        else {
            "action_id": plugin_summary.get("action_id") or job.get("plugin_action_id"),
            "created_ids": [],
            "feedback": {
                "created_ids": [],
                "records_imported": 0,
                "skipped_insights": 0,
                "stored_in_run_result": False,
                "write_target": "user_feedback_insights",
            },
            "label": "结果动作反馈内容",
            "records_imported": 0,
            "skipped_insights": 0,
            "status": "succeeded",
            "write_target": "user_feedback_insights",
        }
    )

    skill_ids = list(job.get("skill_ids", []))
    skill_codes = skill_codes_for_job(current_store, job)
    model_gateway_called = bool(
        ai_processing.get("model_gateway_called", not ai_processing.get("runner_task_id")),
    )
    skill_processing_node = {
        "input": {
            "insights_path": str(mapping.get("insights_path") or "$.insights"),
            "knowledge_references": ai_processing.get("knowledge_references") or [],
            "source_row_count": source_row_count,
        },
        "label": "Skill 处理后内容",
        "model_gateway_called": model_gateway_called,
        "note": "数据连接返回内容已通过 AI 处理为用户洞察写入可消费的结构化 JSON。",
        "output": {
            "candidate_count": len(insights),
            "insights": insights,
            "insights_created": len(created_ids),
            "processed_json": processed_json,
            "skipped_insights": skipped,
        },
        "processing_mode": ai_processing.get("processing_mode")
        or ("model_gateway_json_transform" if model_gateway_called else "ai_executor_runner"),
        "skill_codes": skill_codes,
        "skill_ids": skill_ids,
        "status": ai_processing["status"],
    }
    if ai_processing.get("model_gateway_config_id"):
        skill_processing_node["model_gateway_config_id"] = ai_processing["model_gateway_config_id"]
    if ai_processing.get("model_log_id"):
        skill_processing_node["model_log_id"] = ai_processing["model_log_id"]
    if ai_processing.get("runner_id"):
        skill_processing_node["runner_id"] = ai_processing["runner_id"]
    if ai_processing.get("runner_task_id"):
        skill_processing_node["runner_task_id"] = ai_processing["runner_task_id"]

    execution_nodes = {
        "data_connection": JobExecutionEngine.data_connection_execution_node(
            job=job,
            plugin_summary=plugin_summary,
            records_imported=source_row_count,
            resolved_plugin_input_mapping=resolved_plugin_input_mapping,
        ),
        "result_action": primary_result_action,
        "result_actions": result_actions,
        "skill_processing": skill_processing_node,
    }
    runner_node = ai_processing.get("runner_node")
    if isinstance(runner_node, dict):
        execution_nodes["runner_execution"] = runner_node
    summary = {
        "execution_nodes": execution_nodes,
        "insight_ids": created_ids,
        "insights_created": len(created_ids),
        "plugin": plugin_summary,
        "processing": {
            "model_gateway_called": model_gateway_called,
            "runner_id": ai_processing.get("runner_id"),
            "runner_task_id": ai_processing.get("runner_task_id"),
            "skill_ids": skill_ids,
            "skill_codes": skill_codes,
        },
        "result_action_policy": result_action_policy,
        "skipped_insights": skipped,
        "source_row_count": source_row_count,
        "write_target": primary_result_action.get("write_target"),
        "write_targets": [action["write_target"] for action in result_actions],
    }
    return summary, len(created_ids)


def run_user_feedback_insight_extract_job(
    current_store: Any,
    *,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    mapping = resolve_job_plugin_output_mapping(current_store, job)
    result_mappings = resolve_job_plugin_result_mappings(current_store, job)
    result_action_policy = scheduled_job_result_action_policy(job)
    for result_mapping in result_mappings:
        action_mapping = result_mapping.get("mapping") or {}
        write_target = str(action_mapping.get("write_target") or "user_feedback_insights")
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
    if scheduled_job_uses_local_ai_executor(job):
        ai_processing = dispatch_scheduled_job_ai_executor_processing(
            current_store,
            job=job,
            output_mapping=mapping,
            plugin_summary=plugin_summary,
            resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            run_id=str(plugin_summary.get("scheduled_job_run_id") or ""),
            source_response_json=source_response_json,
            source_row_count=source_row_count,
            user=user,
        )
        return pending_ai_executor_result_summary(
            current_store,
            ai_processing=ai_processing,
            job=job,
            output_mapping=mapping,
            plugin_summary=plugin_summary,
            resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            source_count_key="source_row_count",
            source_row_count=source_row_count,
            wait_note="用户反馈数据已派发给 AI 执行器，等待 Runner 分析后写入用户洞察表。",
            write_target="user_feedback_insights",
        ), 0
    ai_processing = run_scheduled_job_ai_processing(
        current_store,
        job=job,
        output_mapping=mapping,
        source_response_json=source_response_json,
        source_row_count=source_row_count,
        user=user,
    )
    ai_processing["runner_node"] = system_default_runner_node_from_ai_processing(
        ai_processing,
        job=job,
    )
    processed_json = ai_processing["output_json"]
    return user_feedback_result_summary_from_ai_output(
        current_store,
        ai_processing=ai_processing,
        job=job,
        plugin_summary=plugin_summary,
        processed_json=processed_json,
        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
        source_row_count=source_row_count,
        user=user,
    )
