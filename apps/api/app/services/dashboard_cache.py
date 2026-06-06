from __future__ import annotations

import logging
from copy import deepcopy
from datetime import UTC, datetime
from time import perf_counter
from typing import Any


def dashboard_cache_key(
    *,
    product_id: str | None,
    repository: Any,
    time_range: str | None,
    user: dict[str, Any],
) -> tuple[Any, ...]:
    return (
        id(repository),
        product_id or "all",
        time_range or "all",
        tuple(sorted(str(role) for role in user.get("roles", []))),
    )


def dashboard_cache_store(app_state: Any) -> dict[tuple[Any, ...], dict[str, Any]]:
    cache = getattr(app_state, "dashboard_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        app_state.dashboard_cache = cache
    return cache


def dashboard_cache_entry_metadata(
    *,
    cache_hit: bool,
    default_ttl_seconds: int,
    duration_ms: int,
    entry: dict[str, Any],
    slow_threshold_ms: int,
) -> dict[str, Any]:
    now = perf_counter()
    expires_at = float(entry["expires_at"])
    generated_at_monotonic = float(entry["generated_at_monotonic"])
    ttl_seconds = int(entry.get("ttl_seconds", default_ttl_seconds))
    return {
        "dashboard_cache": {
            "age_ms": max(0, int((now - generated_at_monotonic) * 1000)),
            "cache_enabled": bool(entry.get("cache_enabled", ttl_seconds > 0)),
            "cache_hit": cache_hit,
            "duration_ms": duration_ms,
            "expires_in_ms": max(0, int((expires_at - now) * 1000)),
            "generated_at": entry["generated_at"],
            "slow": duration_ms > slow_threshold_ms,
            "slow_threshold_ms": slow_threshold_ms,
            "ttl_seconds": ttl_seconds,
        }
    }


def dashboard_with_metadata(data: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    enriched = deepcopy(data)
    enriched["metadata"] = metadata
    return enriched


def get_dashboard_cache_entry(
    cache: dict[tuple[Any, ...], dict[str, Any]],
    cache_key: tuple[Any, ...],
    *,
    ttl_seconds: int,
) -> dict[str, Any] | None:
    if ttl_seconds <= 0:
        return None
    entry = cache.get(cache_key)
    if entry is None:
        return None
    if perf_counter() >= float(entry["expires_at"]):
        cache.pop(cache_key, None)
        return None
    return entry


def set_dashboard_cache_entry(
    cache: dict[tuple[Any, ...], dict[str, Any]],
    cache_key: tuple[Any, ...],
    data: dict[str, Any],
    *,
    ttl_seconds: int,
) -> dict[str, Any]:
    now = perf_counter()
    generated_at = datetime.now(UTC).isoformat()
    entry = {
        "cache_enabled": ttl_seconds > 0,
        "data": deepcopy(data),
        "expires_at": now + ttl_seconds,
        "generated_at": generated_at,
        "generated_at_monotonic": now,
        "ttl_seconds": ttl_seconds,
    }
    if ttl_seconds > 0:
        cache[cache_key] = entry
    return entry


def dashboard_transient_entry() -> dict[str, Any]:
    now = perf_counter()
    return {
        "cache_enabled": False,
        "expires_at": now,
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_at_monotonic": now,
        "ttl_seconds": 0,
    }


def record_dashboard_performance(
    logger: logging.Logger,
    *,
    cache_hit: bool,
    duration_ms: int,
    product_id: str | None,
    slow_threshold_ms: int,
    time_range: str | None,
    user: dict[str, Any],
) -> None:
    if duration_ms <= slow_threshold_ms:
        return
    logger.warning(
        "slow_dashboard_query duration_ms=%s threshold_ms=%s cache_hit=%s product_id=%s "
        "time_range=%s roles=%s",
        duration_ms,
        slow_threshold_ms,
        cache_hit,
        product_id or "all",
        time_range or "all",
        ",".join(sorted(str(role) for role in user.get("roles", []))),
    )
