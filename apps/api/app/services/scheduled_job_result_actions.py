from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services.code_inspection_common import validate_code_inspection_result_actions
from app.services.plugin_result_mapping import (
    compact_preview_value,
    json_path_value,
    result_write_preview,
)
from app.services.result_write_targets import result_write_target_label
from app.services.scheduled_job_common import ensure_enum
from app.services.scheduled_job_config import scheduled_job_result_action_policy
from app.services.scheduled_job_runtime import exception_error_code_and_message

GENERIC_RESULT_ACTION_TYPES = {"save_scheduled_job_result", "send_notification"}
GENERIC_NOTIFICATION_CHANNELS = {"dingtalk", "email"}
GENERIC_RESULT_ACTION_JOB_TYPES = {"online_log_ai_analysis"}


def validate_scheduled_job_result_actions(job_type: str, actions: Any) -> list[dict[str, Any]]:
    if job_type == "code_repository_inspection":
        return validate_code_inspection_result_actions(actions)
    if actions is None:
        return []
    if not isinstance(actions, list):
        raise api_error(400, "VALIDATION_ERROR", "result_actions must be a list")
    if job_type not in GENERIC_RESULT_ACTION_JOB_TYPES:
        return []
    normalized: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            raise api_error(400, "VALIDATION_ERROR", "result action must be an object")
        action_type = str(action.get("type") or "")
        ensure_enum(action_type, GENERIC_RESULT_ACTION_TYPES, "result action type")
        if action_type == "send_notification":
            normalized.append(_normalize_notification_action(action))
        else:
            normalized.append({**action, "type": action_type})
    return normalized


def default_generic_result_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return actions if actions else [{"type": "save_scheduled_job_result"}]


def execute_generic_result_actions(
    *,
    job: dict[str, Any],
    output_json: dict[str, Any],
    output_mapping: dict[str, Any],
    result_actions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    policy = scheduled_job_result_action_policy(job)
    executed: list[dict[str, Any]] = []
    total_records = 0
    for action in default_generic_result_actions(result_actions):
        action_type = str(action.get("type") or "save_scheduled_job_result")
        try:
            result = _generic_result_action_node(
                action=action,
                action_type=action_type,
                output_json=output_json,
                output_mapping=output_mapping,
            )
            total_records += int(result.get("records_imported") or 0)
            executed.append(result)
        except Exception as exc:
            error_code, error_message = exception_error_code_and_message(exc)
            executed.append(
                {
                    "action_type": action_type,
                    "error_code": error_code,
                    "error_message": error_message,
                    "feedback": {"error_code": error_code, "error_message": error_message},
                    "label": "结果动作反馈内容",
                    "records_imported": 0,
                    "status": "failed",
                    "type": action_type,
                    "write_target": _write_target_for_action(action_type),
                    "write_target_label": result_write_target_label(
                        _write_target_for_action(action_type),
                    ),
                },
            )
            if policy["failure_policy"] == "fail_fast":
                raise
    return executed, total_records


def preview_generic_result_actions(
    *,
    output_mapping: dict[str, Any],
    preview_response_summary: dict[str, Any],
    result_actions: list[dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for action in default_generic_result_actions(result_actions):
        action_type = str(action.get("type") or "save_scheduled_job_result")
        mapping = {
            **output_mapping,
            "write_target": _write_target_for_action(action_type),
        }
        preview = result_write_preview(preview_response_summary, mapping)
        previews.append(
            {
                "action_type": action_type,
                "channels": (
                    action.get("channels") if isinstance(action.get("channels"), list) else []
                ),
                "recipients": (
                    action.get("recipients") if isinstance(action.get("recipients"), list) else []
                ),
                "type": action_type,
                "write_preview": preview,
                "write_preview_source": source,
                "write_target": preview.get("write_target"),
                "write_target_label": preview.get("write_target_label"),
            },
        )
    return previews


def inferred_output_record_count(
    output_json: dict[str, Any],
    output_mapping: dict[str, Any],
) -> int:
    for path in (
        output_mapping.get("records_imported_path"),
        output_mapping.get("anomalies_path"),
        output_mapping.get("insights_path"),
        output_mapping.get("findings_path"),
        "$.anomalies",
        "$.insights",
        "$.findings",
        "$.rows",
        "$.items",
    ):
        value = json_path_value(output_json, str(path)) if path else None
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, list):
            return len(value)
    return 1 if output_json else 0


def _normalize_notification_action(action: dict[str, Any]) -> dict[str, Any]:
    channels = action.get("channels") if isinstance(action.get("channels"), list) else []
    normalized_channels = [str(channel) for channel in channels if str(channel or "").strip()]
    if not normalized_channels:
        raise api_error(400, "VALIDATION_ERROR", "send_notification requires channels")
    for channel in normalized_channels:
        ensure_enum(channel, GENERIC_NOTIFICATION_CHANNELS, "notification channel")
    recipients = action.get("recipients") if isinstance(action.get("recipients"), list) else []
    return {
        **action,
        "channels": normalized_channels,
        "recipients": [str(item) for item in recipients if str(item or "").strip()],
        "type": "send_notification",
    }


def _generic_result_action_node(
    *,
    action: dict[str, Any],
    action_type: str,
    output_json: dict[str, Any],
    output_mapping: dict[str, Any],
) -> dict[str, Any]:
    write_target = _write_target_for_action(action_type)
    records_imported = inferred_output_record_count(output_json, output_mapping)
    write_preview = result_write_preview(
        {"json": output_json},
        {**output_mapping, "write_target": write_target},
    )
    feedback: dict[str, Any] = {
        "records_imported": records_imported,
        "stored_in_run_result": True,
        "write_preview": write_preview,
        "write_target": write_target,
    }
    if action_type == "send_notification":
        subject = action.get("subject") or output_json.get("summary") or "AI Brain 定时作业结果"
        feedback.update(
            {
                "channels": action.get("channels") or [],
                "delivery_status": "recorded",
                "recipients": action.get("recipients") or [],
                "sample_records": [compact_preview_value(output_json)],
                "subject": subject,
                "webhook_configured": bool(action.get("webhook_url")),
            },
        )
        records_imported = max(1, len(feedback["recipients"]))
        feedback["records_imported"] = records_imported
        feedback["sample_records"] = feedback["recipients"][:3] or feedback["sample_records"]
        feedback["write_preview"] = {
            **write_preview,
            "candidate_count": records_imported,
            "delivery_status": "recorded",
            "records_imported": records_imported,
            "sample_records": feedback["sample_records"],
            "subject": subject,
            "write_target": write_target,
            "write_target_label": result_write_target_label(write_target),
        }
    else:
        feedback["result_preview"] = compact_preview_value(output_json)
    return {
        "action_type": action_type,
        "feedback": feedback,
        "label": "结果动作反馈内容",
        "records_imported": records_imported,
        "status": "succeeded",
        "type": action_type,
        "write_target": write_target,
        "write_target_label": result_write_target_label(write_target),
    }


def _write_target_for_action(action_type: str) -> str:
    if action_type == "send_notification":
        return "email_notifications"
    return "scheduled_job_result"
