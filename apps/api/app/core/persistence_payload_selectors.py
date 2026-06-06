from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.persistence_fields import (
    AI_TASK_FIELDS,
    AUDIT_FIELDS,
    BRAIN_APP_FIELDS,
    BUG_FIELDS,
    COLLECTOR_RUN_FIELDS,
    DASHBOARD_FIELDS,
    GITLAB_DAILY_CODE_METRIC_FIELDS,
    GITLAB_REVIEW_FIELDS,
    ITERATION_PLANNING_FIELDS,
    JENKINS_RELEASE_RECORD_FIELDS,
    KNOWLEDGE_FIELDS,
    LIFECYCLE_CONTEXT_FIELDS,
    MOCK_WRITEBACK_FIELDS,
    ONLINE_LOG_METRIC_FIELDS,
    PENDING_ATTRIBUTION_FIELDS,
    PRODUCT_CONFIG_FIELDS,
    REQUIREMENT_FIELDS,
    USER_FEEDBACK_FIELDS,
    USER_USAGE_METRIC_FIELDS,
    WORKFLOW_RUNTIME_FIELDS,
)


def _product_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in PRODUCT_CONFIG_FIELDS}


def _brain_apps_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in BRAIN_APP_FIELDS}


def _requirements_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in REQUIREMENT_FIELDS}


def _ai_tasks_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in AI_TASK_FIELDS}


def _workflow_runtime_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in WORKFLOW_RUNTIME_FIELDS}


def _knowledge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in KNOWLEDGE_FIELDS}


def _audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, [])) for field in AUDIT_FIELDS}


def _bugs_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in BUG_FIELDS}


def _gitlab_daily_code_metric_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in GITLAB_DAILY_CODE_METRIC_FIELDS}


def _jenkins_release_record_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in JENKINS_RELEASE_RECORD_FIELDS}


def _online_log_metric_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in ONLINE_LOG_METRIC_FIELDS}


def _user_usage_metric_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in USER_USAGE_METRIC_FIELDS}


def _user_feedback_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in USER_FEEDBACK_FIELDS}


def _iteration_planning_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in ITERATION_PLANNING_FIELDS}


def _lifecycle_context_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in LIFECYCLE_CONTEXT_FIELDS}


def _dashboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in DASHBOARD_FIELDS}


def _collector_run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in COLLECTOR_RUN_FIELDS}


def _pending_attribution_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in PENDING_ATTRIBUTION_FIELDS}


def _model_gateway_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_gateway_configs": deepcopy(payload.get("model_gateway_configs", {})),
        "model_gateway_logs": deepcopy(payload.get("model_gateway_logs", [])),
    }


def _assistant_chat_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "assistant_conversations": deepcopy(payload.get("assistant_conversations", {})),
        "assistant_messages": deepcopy(payload.get("assistant_messages", {})),
    }


def _gitlab_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in GITLAB_REVIEW_FIELDS}


def _mock_writebacks_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in MOCK_WRITEBACK_FIELDS}


def _ai_tasks_merge_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    merge_payload = _ai_tasks_payload(payload or {})
    for task in merge_payload.get("ai_tasks", {}).values():
        for field in ("graph_run_ids", "review_ids"):
            if task.get(field) == []:
                task.pop(field)
    return merge_payload


def _merge_collection_payload(
    payload: dict[str, Any],
    overlay: dict[str, Any],
    fields: list[str],
    *,
    merge_items: bool = False,
) -> None:
    for field in fields:
        existing_items = deepcopy(payload.get(field, {}))
        overlay_items = deepcopy(overlay.get(field, {}))
        if merge_items:
            merged_items = existing_items
            for item_id, item in overlay_items.items():
                merged_items[item_id] = {
                    **deepcopy(merged_items.get(item_id, {})),
                    **item,
                }
            payload[field] = merged_items
        else:
            payload[field] = {**existing_items, **overlay_items}


def _replace_collection_payload(
    payload: dict[str, Any],
    overlay: dict[str, Any],
    fields: list[str],
) -> None:
    for field in fields:
        payload[field] = deepcopy(overlay.get(field, {}))


def _merge_audit_payload(payload: dict[str, Any], overlay: dict[str, Any]) -> None:
    payload["audit_events"] = deepcopy(overlay.get("audit_events", []))
