from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.deps import api_error
from app.services.assistant_action_draft_common import (
    CRON_MONTH_NAMES,
    CRON_WEEKDAY_NAMES,
    valid_cron_expression,
)
from app.services.code_inspections import sync_product_git_repository_store
from app.services.native_code_scanner import code_inspection_uses_native_scan
from app.services.scheduled_job_catalog import (
    AI_REQUIRED_SCHEDULED_JOB_TYPES,
    CODE_INSPECTION_SCAN_MODES,
    DEFAULT_CODE_INSPECTION_SCAN_MODE,
)
from app.services.scheduled_job_common import ensure_enum
from app.services.scheduled_job_constants import (
    DEFAULT_DATA_CONNECTION_POLICY,
    DEFAULT_RESULT_ACTION_POLICY,
)
from app.services.scheduled_job_refs import (
    payload_field,
    scheduled_job_multi_ids,
    scheduled_job_orchestration_config,
)
from app.services.scheduled_job_store import (
    persist_record,
    put_memory_record,
    read_memory_dict,
    sync_reference_store,
)


def validate_product(current_store: Any, product_id: str | None) -> None:
    if product_id is None:
        return
    sync_reference_store(current_store)
    product = read_memory_dict(current_store, "products").get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product.get("status") != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")


def _aware_utc(value: datetime | None = None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _timezone(value: Any) -> ZoneInfo:
    try:
        return ZoneInfo(str(value or "Asia/Shanghai"))
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _cron_token_value(token: str, aliases: dict[str, int]) -> int:
    normalized = token.upper()
    if normalized in aliases:
        return aliases[normalized]
    return int(normalized)


def _cron_range_values(start: int, end: int, minimum: int, maximum: int, step: int) -> list[int]:
    if start <= end:
        return list(range(start, end + 1, step))
    return list(range(start, maximum + 1, step)) + list(range(minimum, end + 1, step))


def _cron_field_values(
    field: str,
    *,
    aliases: dict[str, int] | None = None,
    maximum: int,
    minimum: int,
    normalize: Any | None = None,
) -> list[int]:
    aliases = aliases or {}
    values: set[int] = set()
    for raw_part in field.upper().split(","):
        base, _, step_text = raw_part.partition("/")
        step = int(step_text) if step_text else 1
        if base == "*":
            part_values = list(range(minimum, maximum + 1, step))
        else:
            start_text, separator, end_text = base.partition("-")
            start = _cron_token_value(start_text, aliases)
            if separator:
                end = _cron_token_value(end_text, aliases)
                part_values = _cron_range_values(start, end, minimum, maximum, step)
            else:
                part_values = [start]
        for value in part_values:
            normalized = normalize(value) if normalize else value
            values.add(normalized)
    return sorted(values)


def _cron_day_matches(
    candidate_date: date,
    *,
    day_of_month_field: str,
    day_of_month_values: list[int],
    weekday_field: str,
    weekday_values: list[int],
) -> bool:
    day_of_month_match = candidate_date.day in day_of_month_values
    cron_weekday = (candidate_date.weekday() + 1) % 7
    weekday_match = cron_weekday in weekday_values
    day_of_month_restricted = day_of_month_field != "*"
    weekday_restricted = weekday_field != "*"
    if day_of_month_restricted and weekday_restricted:
        return day_of_month_match or weekday_match
    return day_of_month_match and weekday_match


def _next_cron_run_at(expression: str, *, now: datetime, timezone: ZoneInfo) -> str:
    if not valid_cron_expression(expression):
        raise api_error(400, "VALIDATION_ERROR", "Invalid cron_expression")
    minute_field, hour_field, day_field, month_field, weekday_field = expression.split()
    minutes = _cron_field_values(minute_field, minimum=0, maximum=59)
    hours = _cron_field_values(hour_field, minimum=0, maximum=23)
    days = _cron_field_values(day_field, minimum=1, maximum=31)
    months = _cron_field_values(
        month_field,
        aliases=CRON_MONTH_NAMES,
        minimum=1,
        maximum=12,
    )
    weekdays = _cron_field_values(
        weekday_field,
        aliases=CRON_WEEKDAY_NAMES,
        minimum=0,
        maximum=7,
        normalize=lambda value: 0 if value == 7 else value,
    )
    local_base = _aware_utc(now).astimezone(timezone).replace(second=0, microsecond=0)
    search_date = local_base.date()
    for day_offset in range(0, 366 * 5):
        candidate_date = search_date + timedelta(days=day_offset)
        if candidate_date.month not in months:
            continue
        if not _cron_day_matches(
            candidate_date,
            day_of_month_field=day_field,
            day_of_month_values=days,
            weekday_field=weekday_field,
            weekday_values=weekdays,
        ):
            continue
        for hour in hours:
            for minute in minutes:
                local_candidate = datetime.combine(
                    candidate_date,
                    time(hour, minute),
                    tzinfo=timezone,
                )
                if local_candidate > local_base:
                    return local_candidate.astimezone(UTC).isoformat()
    raise api_error(400, "VALIDATION_ERROR", "cron_expression has no future run")


def next_run_at(payload: Any, *, now: datetime | None = None) -> str | None:
    current_time = _aware_utc(now)
    schedule_type = payload_field(payload, "schedule_type")
    if schedule_type == "manual":
        return None
    if schedule_type == "interval":
        interval_seconds = payload_field(payload, "interval_seconds")
        if interval_seconds is None or interval_seconds <= 0:
            raise api_error(400, "VALIDATION_ERROR", "interval_seconds is required")
        return (current_time + timedelta(seconds=interval_seconds)).isoformat()
    cron_expression = payload_field(payload, "cron_expression")
    if not cron_expression:
        raise api_error(400, "VALIDATION_ERROR", "cron_expression is required")
    return _next_cron_run_at(
        str(cron_expression).strip(),
        now=current_time,
        timezone=_timezone(payload_field(payload, "timezone", "Asia/Shanghai")),
    )


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return _aware_utc(parsed)


def _scheduled_job_next_run_is_stale(job: dict[str, Any], *, now: datetime) -> bool:
    if not job.get("enabled") or job.get("status") == "disabled":
        return False
    if job.get("schedule_type") == "manual":
        return False
    parsed_next_run = _parse_datetime(job.get("next_run_at"))
    return parsed_next_run is None or parsed_next_run <= now


def refresh_stale_scheduled_job_next_runs(
    current_store: Any,
    *,
    jobs: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    current_time = _aware_utc(now)
    source_jobs = (
        jobs
        if jobs is not None
        else list(read_memory_dict(current_store, "scheduled_jobs").values())
    )
    refreshed_jobs: list[dict[str, Any]] = []
    for job in source_jobs:
        if not _scheduled_job_next_run_is_stale(job, now=current_time):
            refreshed_jobs.append(job)
            continue
        try:
            refreshed_next_run_at = next_run_at(job, now=current_time)
        except Exception:
            refreshed_jobs.append(job)
            continue
        if refreshed_next_run_at == job.get("next_run_at"):
            refreshed_jobs.append(job)
            continue
        updated_job = {
            **job,
            "next_run_at": refreshed_next_run_at,
            "updated_at": current_time.isoformat(),
        }
        put_memory_record(current_store, "scheduled_jobs", updated_job)
        persist_record(current_store, "save_scheduled_job_record", updated_job)
        refreshed_jobs.append(updated_job)
    return refreshed_jobs


def scheduled_job_config_with_multi_refs(
    config_json: Any,
    *,
    plugin_action_ids: list[str],
    plugin_connection_ids: list[str],
) -> dict[str, Any]:
    config = dict(config_json) if isinstance(config_json, dict) else {}
    existing_orchestration = scheduled_job_orchestration_config(config)
    config["orchestration"] = {
        **existing_orchestration,
        "data_connections": {
            **DEFAULT_DATA_CONNECTION_POLICY,
            **(
                existing_orchestration.get("data_connections")
                if isinstance(existing_orchestration.get("data_connections"), dict)
                else {}
            ),
        },
        "plugin_action_ids": list(plugin_action_ids),
        "plugin_connection_ids": list(plugin_connection_ids),
        "result_actions": {
            **DEFAULT_RESULT_ACTION_POLICY,
            **(
                existing_orchestration.get("result_actions")
                if isinstance(existing_orchestration.get("result_actions"), dict)
                else {}
            ),
        },
    }
    return config


def optional_stripped(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def scheduled_job_config_with_code_inspection_defaults(
    current_store: Any,
    *,
    config_json: Any,
    job_type: str,
    product_id: str | None,
) -> dict[str, Any]:
    config = dict(config_json) if isinstance(config_json, dict) else {}
    if job_type != "code_repository_inspection":
        return config

    scan_mode = optional_stripped(config.get("scan_mode")) or DEFAULT_CODE_INSPECTION_SCAN_MODE
    ensure_enum(scan_mode, CODE_INSPECTION_SCAN_MODES, "config_json.scan_mode")
    config["scan_mode"] = scan_mode

    repository_id = optional_stripped(config.get("repository_id"))
    if repository_id is None:
        branch = optional_stripped(config.get("branch"))
        if branch is not None:
            config["branch"] = branch
        return config

    config["repository_id"] = repository_id
    sync_product_git_repository_store(current_store, product_id)
    repository = read_memory_dict(current_store, "product_git_repositories").get(repository_id)
    if repository is None:
        return config
    if product_id and repository.get("product_id") != product_id:
        raise api_error(400, "VALIDATION_ERROR", "Repository does not belong to product")

    branch = optional_stripped(config.get("branch"))
    if branch is None:
        branch = optional_stripped(repository.get("default_branch")) or "main"
    config["branch"] = branch
    return config


def scheduled_job_data_connection_policy(job: dict[str, Any]) -> dict[str, str]:
    policy = scheduled_job_orchestration_config(job.get("config_json") or {}).get(
        "data_connections",
    )
    if not isinstance(policy, dict):
        return dict(DEFAULT_DATA_CONNECTION_POLICY)
    return {
        "failure_policy": str(policy.get("failure_policy") or "fail_fast"),
        "merge_strategy": str(policy.get("merge_strategy") or "append_json_arrays"),
        "mode": str(policy.get("mode") or "sequential"),
    }


def scheduled_job_result_action_policy(job: dict[str, Any]) -> dict[str, str]:
    policy = scheduled_job_orchestration_config(job.get("config_json") or {}).get(
        "result_actions",
    )
    if not isinstance(policy, dict):
        return dict(DEFAULT_RESULT_ACTION_POLICY)
    return {
        "failure_policy": str(policy.get("failure_policy") or "continue_on_error"),
        "mode": str(policy.get("mode") or "sequential"),
    }


def scheduled_job_with_multi_refs(job: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(job)
    plugin_action_ids = scheduled_job_multi_ids(enriched, "plugin_action_ids", "plugin_action_id")
    plugin_connection_ids = scheduled_job_multi_ids(
        enriched,
        "plugin_connection_ids",
        "plugin_connection_id",
    )
    enriched["plugin_action_ids"] = plugin_action_ids
    enriched["plugin_connection_ids"] = plugin_connection_ids
    if plugin_action_ids:
        enriched["plugin_action_id"] = plugin_action_ids[0]
    if plugin_connection_ids:
        enriched["plugin_connection_id"] = plugin_connection_ids[0]
    enriched["config_json"] = scheduled_job_config_with_multi_refs(
        enriched.get("config_json") or {},
        plugin_action_ids=plugin_action_ids,
        plugin_connection_ids=plugin_connection_ids,
    )
    return enriched


def effective_scheduled_job_type(payload: Any) -> str:
    job_type = str(payload_field(payload, "job_type") or "")
    skill_ids = list(payload_field(payload, "skill_ids", []) or [])
    if (
        job_type == "user_feedback_collect"
        and bool(scheduled_job_multi_ids(payload, "plugin_action_ids", "plugin_action_id"))
        and (
            payload_field(payload, "agent_id") is not None
            or payload_field(payload, "model_gateway_config_id") is not None
            or bool(skill_ids)
        )
    ):
        return "user_feedback_insight_extract"
    return job_type


def effective_scheduled_job_execution_mode(payload: Any, job_type: str) -> str:
    if job_type in AI_REQUIRED_SCHEDULED_JOB_TYPES:
        return "ai_generated"
    return str(payload_field(payload, "execution_mode") or "deterministic")


def scheduled_job_uses_native_code_inspection(payload: Any) -> bool:
    return (
        effective_scheduled_job_type(payload) == "code_repository_inspection"
        and code_inspection_uses_native_scan(payload)
    )
