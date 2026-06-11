from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

LEGACY_TIME_PARAMETER_ALIASES = {
    "last_monday_00:00:00": "{{last_full_week.start}}",
    "this_monday_00:00:00": "{{last_full_week.end}}",
}

_TOKEN_PATTERN = re.compile(
    r"\{\{\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_.]*)(?:\s*(?P<sign>[+-])\s*(?P<days>\d+)\s*(?:d|day|days)?)?\s*\}\}",
)


def _local_now(*, now: datetime | None = None, timezone: ZoneInfo | None = None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(timezone or ZoneInfo("UTC"))


def _dynamic_parameter_datetimes(
    *,
    now: datetime | None = None,
    timezone: ZoneInfo | None = None,
) -> dict[str, datetime]:
    local_now = _local_now(now=now, timezone=timezone)
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    yesterday_start = today_start - timedelta(days=1)
    current_week_start = today_start - timedelta(days=today_start.weekday())
    last_full_week_start = current_week_start - timedelta(days=7)
    last_7_days_start = local_now - timedelta(days=7)
    return {
        "current_date": today_start,
        "current_date_iso": today_start,
        "date": today_start,
        "date_iso": today_start,
        "last_7_days.end": local_now,
        "last_7_days.start": last_7_days_start,
        "last_full_week.end": current_week_start,
        "last_full_week.start": last_full_week_start,
        "now": local_now,
        "today": today_start,
        "today.end": today_end,
        "today.start": today_start,
        "today_iso": today_start,
        "yesterday": yesterday_start,
        "yesterday.end": today_start,
        "yesterday.start": yesterday_start,
        "yesterday_iso": yesterday_start,
    }


def _format_dynamic_parameter(name: str, value: datetime) -> str:
    if name in {"current_date", "date", "today", "yesterday"}:
        return value.strftime("%Y%m%d")
    if name in {"current_date_iso", "date_iso", "today_iso", "yesterday_iso"}:
        return value.date().isoformat()
    return value.isoformat()


def dynamic_time_parameters(
    *,
    now: datetime | None = None,
    timezone: ZoneInfo | None = None,
) -> dict[str, str]:
    values = _dynamic_parameter_datetimes(now=now, timezone=timezone)
    return {key: _format_dynamic_parameter(key, value) for key, value in values.items()}


def dynamic_parameter_preview(
    *,
    now: datetime | None = None,
    timezone: ZoneInfo | None = None,
) -> list[dict[str, str]]:
    base_items = [
        ("{{current_date}}", "当前日期", "YYYYMMDD 格式，适合分区字段"),
        ("{{current_date-7}}", "当前日期 - 7 天", "YYYYMMDD 格式，适合近 7 天起始分区"),
        ("{{date_iso}}", "当前日期 ISO", "YYYY-MM-DD 格式"),
        ("{{now}}", "当前时间", "带时区的 ISO 时间"),
        ("{{today.start}}", "今天开始", "当天 00:00:00"),
        ("{{today.end}}", "今天结束", "次日 00:00:00"),
        ("{{last_full_week.start}}", "上完整周开始", "上周一 00:00:00"),
        ("{{last_full_week.end}}", "上完整周结束", "本周一 00:00:00"),
    ]
    return [
        {
            "description": description,
            "expression": expression,
            "label": label,
            "value": str(resolve_dynamic_parameter_value(expression, now=now, timezone=timezone)),
        }
        for expression, label, description in base_items
    ]


def _resolve_token(match: re.Match[str], *, now: datetime | None, timezone: ZoneInfo | None) -> str:
    name = match.group("name")
    values = _dynamic_parameter_datetimes(now=now, timezone=timezone)
    if name not in values:
        return match.group(0)
    value = values[name]
    days = match.group("days")
    if days is not None:
        multiplier = -1 if match.group("sign") == "-" else 1
        value = value + timedelta(days=multiplier * int(days))
    return _format_dynamic_parameter(name, value)


def resolve_dynamic_parameter_value(
    value: Any,
    parameters: dict[str, str] | None = None,
    *,
    now: datetime | None = None,
    timezone: ZoneInfo | None = None,
) -> Any:
    if isinstance(value, dict):
        return {
            key: resolve_dynamic_parameter_value(
                item,
                parameters,
                now=now,
                timezone=timezone,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            resolve_dynamic_parameter_value(item, parameters, now=now, timezone=timezone)
            for item in value
        ]
    if not isinstance(value, str):
        return value

    resolved = LEGACY_TIME_PARAMETER_ALIASES.get(value, value)
    for key, parameter_value in (parameters or {}).items():
        resolved = resolved.replace(f"{{{{{key}}}}}", parameter_value)
    return _TOKEN_PATTERN.sub(
        lambda match: _resolve_token(match, now=now, timezone=timezone),
        resolved,
    )
