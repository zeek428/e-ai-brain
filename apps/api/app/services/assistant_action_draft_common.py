from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.api.deps import api_error

ASSISTANT_ACTION_DRAFT_STATUSES = {
    "cancelled",
    "confirmed",
    "expired",
    "failed",
    "pending",
}
ASSISTANT_ACTION_RUN_STATUSES = {"failed", "succeeded"}
ASSISTANT_ACTION_DRAFT_VALIDATION_STATUSES = {"blocked", "passed", "unknown", "warning"}
ASSISTANT_DRAFT_ACTIONS = {
    "create_ai_agent",
    "create_ai_skill",
    "create_analysis_draft",
    "create_plugin_action",
    "create_plugin_connection",
    "create_rd_task",
    "create_scheduled_job",
}
ASSISTANT_ACTION_DRAFT_SORT_FIELDS = {
    "action",
    "created_at",
    "expires_at",
    "id",
    "modified_field_count",
    "result_status",
    "risk_level",
    "status",
    "title",
    "updated_at",
    "validation_issue_count",
    "validation_status",
    "view_count",
}
AI_AGENT_DEFAULTS = {
    "brain_app_id": "rd_brain",
    "default_skill_ids": [],
    "description": None,
    "execution_policy": {},
    "model_gateway_config_id": None,
    "status": "active",
    "tool_policy": {},
}
AI_SKILL_DEFAULTS = {
    "allowed_tools": [],
    "description": None,
    "input_schema": {},
    "output_schema": {},
    "required_context": [],
    "requires_human_review": False,
    "risk_level": "medium",
    "status": "active",
    "version": "1.0.0",
}
SCHEDULED_JOB_DEFAULTS = {
    "agent_id": None,
    "config_json": {},
    "cron_expression": None,
    "enabled": True,
    "execution_mode": "deterministic",
    "interval_seconds": None,
    "knowledge_document_ids": [],
    "lock_ttl_seconds": 900,
    "max_retry_count": 0,
    "model_gateway_config_id": None,
    "plugin_action_id": None,
    "plugin_action_ids": [],
    "plugin_connection_id": None,
    "plugin_connection_ids": [],
    "plugin_input_mapping": {},
    "plugin_output_mapping": {},
    "product_id": None,
    "result_actions": [],
    "schedule_type": "manual",
    "skill_ids": [],
    "source_system": "ai-assistant",
    "timeout_seconds": 600,
    "timezone": "Asia/Shanghai",
}
PLUGIN_CONNECTION_DEFAULTS = {
    "auth_config": {},
    "auth_type": "none",
    "environment": "default",
    "max_retries": 0,
    "request_config": {},
    "status": "active",
    "timeout_seconds": 30,
}
PLUGIN_ACTION_DEFAULTS = {
    "action_type": "http_request",
    "connection_id": None,
    "description": None,
    "input_schema": {},
    "output_schema": {},
    "request_config": {},
    "requires_human_review": False,
    "result_mapping": {},
    "status": "active",
}
RD_TASK_DEFAULTS = {
    "input": {},
    "task_type": "product_detail_design",
}

CRON_MONTH_NAMES = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}
CRON_WEEKDAY_NAMES = {
    "SUN": 0,
    "MON": 1,
    "TUE": 2,
    "WED": 3,
    "THU": 4,
    "FRI": 5,
    "SAT": 6,
}


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_draft_action(action: str) -> str:
    normalized = ensure_non_blank(action, "action")
    if normalized not in ASSISTANT_DRAFT_ACTIONS:
        raise api_error(400, "UNSUPPORTED_DRAFT_ACTION", "Unsupported assistant draft action")
    return normalized


def with_defaults(defaults: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults)
    merged.update(deepcopy(payload))
    return merged


def valid_cron_expression(expression: str) -> bool:
    fields = expression.split()
    if len(fields) != 5:
        return False
    validators = (
        (0, 59, {}),
        (0, 23, {}),
        (1, 31, {}),
        (1, 12, CRON_MONTH_NAMES),
        (0, 7, CRON_WEEKDAY_NAMES),
    )
    return all(
        _valid_cron_field(field, minimum, maximum, aliases)
        for field, (minimum, maximum, aliases) in zip(fields, validators, strict=True)
    )


def _valid_cron_field(
    field: str,
    minimum: int,
    maximum: int,
    aliases: dict[str, int],
) -> bool:
    if not field:
        return False
    return all(
        _valid_cron_part(part, minimum, maximum, aliases) for part in field.upper().split(",")
    )


def _valid_cron_part(
    part: str,
    minimum: int,
    maximum: int,
    aliases: dict[str, int],
) -> bool:
    if not part:
        return False
    base, _, step = part.partition("/")
    if step:
        if not step.isdigit() or int(step) <= 0:
            return False
    if base == "*":
        return True
    start, separator, end = base.partition("-")
    if not _valid_cron_token(start, minimum, maximum, aliases):
        return False
    if not separator:
        return True
    return _valid_cron_token(end, minimum, maximum, aliases)


def _valid_cron_token(
    token: str,
    minimum: int,
    maximum: int,
    aliases: dict[str, int],
) -> bool:
    if not token:
        return False
    if token in aliases:
        return minimum <= aliases[token] <= maximum
    if not token.isdigit():
        return False
    value = int(token)
    return minimum <= value <= maximum
