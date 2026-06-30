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


def assistant_action_draft_decision(
    *,
    audit_event_count: int,
    draft: dict[str, Any],
    last_failure_payload: dict[str, Any],
    missing_permissions: list[str],
    permission_issue_count: int,
    permission_status: str,
    risk_level: str,
    validation_issue_count: int,
    validation_status: str,
) -> dict[str, Any]:
    status = str(draft.get("status") or "unknown")
    if status == "confirmed":
        return {
            "blocking_count": 0,
            "can_confirm": False,
            "can_retry": False,
            "label": "已采纳",
            "next_action": "查看结果和审计链路",
            "reason": "草案已确认执行",
            "status": "terminal",
        }
    if status == "cancelled":
        return {
            "blocking_count": 0,
            "can_confirm": False,
            "can_retry": False,
            "label": "已取消",
            "next_action": "无需确认",
            "reason": draft.get("cancel_reason") or "草案已取消",
            "status": "terminal",
        }
    if status == "expired":
        return {
            "blocking_count": 1,
            "can_confirm": False,
            "can_retry": False,
            "label": "已过期",
            "next_action": "重新生成草案",
            "reason": "草案超过确认有效期",
            "status": "expired",
        }
    if status == "failed":
        return {
            "blocking_count": 1,
            "can_confirm": False,
            "can_retry": True,
            "label": "执行失败",
            "next_action": "查看失败原因并重新打开",
            "reason": (
                last_failure_payload.get("message")
                or last_failure_payload.get("code")
                or "草案确认执行失败"
            ),
            "status": "failed",
        }

    if validation_status == "blocked":
        issue_count = max(validation_issue_count, 1)
        return {
            "blocking_count": issue_count,
            "can_confirm": False,
            "can_retry": False,
            "label": "校验阻断",
            "next_action": "补齐必填字段和校验问题",
            "reason": f"存在 {issue_count} 个校验阻断问题",
            "status": "blocked",
        }
    if permission_status == "blocked":
        issue_count = max(permission_issue_count, len(missing_permissions), 1)
        missing = "、".join(missing_permissions[:3])
        return {
            "blocking_count": issue_count,
            "can_confirm": False,
            "can_retry": False,
            "label": "权限阻断",
            "next_action": "补齐权限或调整草案",
            "reason": missing or f"存在 {issue_count} 个权限问题",
            "status": "blocked",
        }
    if risk_level in {"critical", "high"}:
        return {
            "blocking_count": 0,
            "can_confirm": True,
            "can_retry": False,
            "label": "高风险待复核",
            "next_action": "逐条核对影响对象和执行前后差异",
            "reason": "高风险草案确认前需要人工复核",
            "status": "warning",
        }
    if validation_status == "warning" or permission_status == "warning":
        return {
            "blocking_count": 0,
            "can_confirm": True,
            "can_retry": False,
            "label": "有警告可确认",
            "next_action": "核对警告后确认执行",
            "reason": "存在非阻断校验或权限警告",
            "status": "warning",
        }
    if audit_event_count == 0:
        return {
            "blocking_count": 0,
            "can_confirm": True,
            "can_retry": False,
            "label": "审计待补齐",
            "next_action": "打开详情确认来源链路",
            "reason": "当前草案尚未产生审计事件",
            "status": "warning",
        }
    if status == "pending":
        return {
            "blocking_count": 0,
            "can_confirm": True,
            "can_retry": False,
            "label": "可确认",
            "next_action": "可确认执行",
            "reason": "校验、权限和审计链路已通过",
            "status": "ready",
        }
    return {
        "blocking_count": 0,
        "can_confirm": False,
        "can_retry": False,
        "label": "未知",
        "next_action": "查看草案详情",
        "reason": f"未知草案状态：{status}",
        "status": "unknown",
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
