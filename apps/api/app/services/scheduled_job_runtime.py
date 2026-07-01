from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.deps import api_error
from app.services.dynamic_parameters import (
    dynamic_time_parameters,
    resolve_dynamic_parameter_value,
)


def scheduled_job_timezone(job: dict[str, Any]) -> ZoneInfo:
    timezone_name = str(job.get("timezone") or "UTC")
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported timezone: {timezone_name}") from None


def resolve_plugin_input_mapping(
    mapping: dict[str, Any],
    job: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    return resolve_dynamic_parameter_value(
        mapping,
        dynamic_time_parameters(now=now, timezone=scheduled_job_timezone(job)),
        now=now,
        timezone=scheduled_job_timezone(job),
    )


def exception_error_code_and_message(exc: Exception) -> tuple[str, str]:
    error_code = exc.__class__.__name__
    error_message = str(exc)
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        error_code = str(detail.get("code") or error_code)
        error_message = str(detail.get("message") or error_message)
    return error_code, error_message


def model_gateway_failure_diagnostics(exc: Exception) -> dict[str, Any]:
    detail = getattr(exc, "detail", None)
    if not isinstance(detail, dict):
        return {}
    return {
        key: detail[key]
        for key in (
            "latency_ms",
            "model",
            "model_gateway_config_id",
            "model_log_id",
            "provider",
        )
        if key in detail
    }


def generic_scheduled_job_result_summary(job_type: str) -> dict[str, Any]:
    message = "通用定时作业运行完成"
    if job_type == "plugin_action_invoke":
        message = "插件执行调用完成"
    return {
        "job_type": job_type,
        "message": message,
    }
