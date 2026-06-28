from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

DEFAULT_LEASE_TIMEOUT_SECONDS = 300
DEFAULT_MAX_RECLAIM_COUNT = 1
LEASE_ACTIVE_STATUSES = {"claimed", "running"}


def _datetime_value(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _request_config(task: dict[str, Any]) -> dict[str, Any]:
    value = task.get("request_config")
    return dict(value) if isinstance(value, dict) else {}


def _config_value(config: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in config:
        return config.get(key)
    query = config.get("query") if isinstance(config.get("query"), dict) else {}
    return query.get(key, default)


def _reliability_config(task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    config = _request_config(task)
    reliability = config.get("reliability")
    normalized_reliability = dict(reliability) if isinstance(reliability, dict) else {}
    return config, normalized_reliability


def lease_timeout_seconds(task: dict[str, Any]) -> int:
    config, reliability = _reliability_config(task)
    return _positive_int(
        reliability.get("lease_timeout_seconds")
        or _config_value(config, "lease_timeout_seconds")
        or DEFAULT_LEASE_TIMEOUT_SECONDS,
        DEFAULT_LEASE_TIMEOUT_SECONDS,
    )


def max_reclaim_count(task: dict[str, Any]) -> int:
    config, reliability = _reliability_config(task)
    return _non_negative_int(
        reliability.get("max_reclaim_count")
        if reliability.get("max_reclaim_count") is not None
        else _config_value(config, "max_reclaim_count", DEFAULT_MAX_RECLAIM_COUNT),
        DEFAULT_MAX_RECLAIM_COUNT,
    )


def reclaim_count(task: dict[str, Any]) -> int:
    _, reliability = _reliability_config(task)
    return _non_negative_int(reliability.get("reclaim_count"), 0)


def _with_reliability(task: dict[str, Any], reliability: dict[str, Any]) -> dict[str, Any]:
    config = _request_config(task)
    return {
        **task,
        "request_config": {
            **config,
            "reliability": reliability,
        },
    }


def apply_task_claim_lease(task: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    timeout_seconds = lease_timeout_seconds(task)
    _, reliability = _reliability_config(task)
    now_iso = now.isoformat()
    return _with_reliability(
        task,
        {
            **reliability,
            "dead_letter_at": None,
            "dead_letter_reason": None,
            "last_claimed_at": now_iso,
            "lease_expires_at": (now + timedelta(seconds=timeout_seconds)).isoformat(),
            "lease_started_at": now_iso,
            "lease_timeout_seconds": timeout_seconds,
            "max_reclaim_count": max_reclaim_count(task),
        },
    )


def refresh_task_lease(task: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    if str(task.get("status") or "") not in LEASE_ACTIVE_STATUSES:
        return task
    timeout_seconds = lease_timeout_seconds(task)
    _, reliability = _reliability_config(task)
    now_iso = now.isoformat()
    return _with_reliability(
        task,
        {
            **reliability,
            "last_heartbeat_at": now_iso,
            "lease_expires_at": (now + timedelta(seconds=timeout_seconds)).isoformat(),
            "lease_timeout_seconds": timeout_seconds,
            "max_reclaim_count": max_reclaim_count(task),
        },
    )


def task_lease_expired(task: dict[str, Any], *, now: datetime) -> bool:
    if str(task.get("status") or "") not in LEASE_ACTIVE_STATUSES:
        return False
    _, reliability = _reliability_config(task)
    lease_expires_at = _datetime_value(reliability.get("lease_expires_at"))
    if lease_expires_at is not None:
        return now >= lease_expires_at
    reference_at = (
        _datetime_value(task.get("claimed_at"))
        or _datetime_value(task.get("updated_at"))
        or _datetime_value(task.get("created_at"))
    )
    if reference_at is None:
        return False
    return (now - reference_at).total_seconds() >= lease_timeout_seconds(task)


def should_dead_letter_after_lease(task: dict[str, Any]) -> bool:
    return reclaim_count(task) >= max_reclaim_count(task)


def apply_task_lease_requeue(
    task: dict[str, Any],
    *,
    now: datetime,
    reason: str,
) -> dict[str, Any]:
    _, reliability = _reliability_config(task)
    now_iso = now.isoformat()
    return _with_reliability(
        {
            **task,
            "claimed_at": None,
            "error_code": None,
            "error_message": None,
            "finished_at": None,
            "status": "queued",
            "updated_at": now_iso,
        },
        {
            **reliability,
            "last_reclaim_reason": reason,
            "last_reclaimed_at": now_iso,
            "lease_expires_at": None,
            "lease_started_at": None,
            "reclaim_count": reclaim_count(task) + 1,
        },
    )


def apply_task_dead_letter(
    task: dict[str, Any],
    *,
    now: datetime,
    reason: str,
) -> dict[str, Any]:
    _, reliability = _reliability_config(task)
    now_iso = now.isoformat()
    return _with_reliability(
        {
            **task,
            "error_code": "AI_EXECUTOR_TASK_LEASE_EXPIRED",
            "error_message": reason,
            "finished_at": now_iso,
            "status": "dead_letter",
            "updated_at": now_iso,
        },
        {
            **reliability,
            "dead_letter_at": now_iso,
            "dead_letter_reason": reason,
        },
    )
