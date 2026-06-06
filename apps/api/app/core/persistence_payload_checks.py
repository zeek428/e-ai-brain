from __future__ import annotations

from typing import Any

from app.core.persistence_fields import (
    AI_TASK_FIELDS,
    ASSISTANT_CHAT_FIELDS,
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
    MODEL_GATEWAY_FIELDS,
    ONLINE_LOG_METRIC_FIELDS,
    PENDING_ATTRIBUTION_FIELDS,
    PRODUCT_CONFIG_FIELDS,
    REQUIREMENT_FIELDS,
    USER_FEEDBACK_FIELDS,
    USER_USAGE_METRIC_FIELDS,
    WORKFLOW_RUNTIME_FIELDS,
)


def _has_product_config_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in PRODUCT_CONFIG_FIELDS)


def _has_brain_app_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in BRAIN_APP_FIELDS)


def _has_requirement_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in REQUIREMENT_FIELDS)


def _has_ai_task_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in AI_TASK_FIELDS)


def _has_workflow_runtime_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in WORKFLOW_RUNTIME_FIELDS)


def _has_knowledge_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in KNOWLEDGE_FIELDS)


def _has_audit_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in AUDIT_FIELDS)


def _has_bug_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in BUG_FIELDS)


def _has_gitlab_daily_code_metric_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in GITLAB_DAILY_CODE_METRIC_FIELDS)


def _has_jenkins_release_record_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in JENKINS_RELEASE_RECORD_FIELDS)


def _has_online_log_metric_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in ONLINE_LOG_METRIC_FIELDS)


def _has_user_usage_metric_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in USER_USAGE_METRIC_FIELDS)


def _has_user_feedback_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in USER_FEEDBACK_FIELDS)


def _has_iteration_planning_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in ITERATION_PLANNING_FIELDS)


def _has_lifecycle_context_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in LIFECYCLE_CONTEXT_FIELDS)


def _has_dashboard_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in DASHBOARD_FIELDS)


def _has_collector_run_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in COLLECTOR_RUN_FIELDS)


def _has_pending_attribution_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in PENDING_ATTRIBUTION_FIELDS)


def _has_model_gateway_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in MODEL_GATEWAY_FIELDS)


def _has_assistant_chat_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in ASSISTANT_CHAT_FIELDS)


def _has_gitlab_review_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in GITLAB_REVIEW_FIELDS)


def _has_mock_writeback_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in MOCK_WRITEBACK_FIELDS)
