from __future__ import annotations

import hashlib
import json
import logging
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, api_error, store
from app.core.config import get_settings
from app.core.trace import envelope, get_trace_id
from app.services.dashboard_cache import (
    dashboard_cache_entry_metadata,
    dashboard_cache_key,
    dashboard_cache_store,
    dashboard_transient_entry,
    dashboard_with_metadata,
    get_dashboard_cache_entry,
    record_dashboard_performance,
    set_dashboard_cache_entry,
)
from app.services.dashboard_metrics import (
    build_dashboard_metrics_data,
    dashboard_metric_snapshot_record,
    dashboard_source_rows_from_store,
    dashboard_time_cutoff,
    sync_dashboard_metric_snapshot,
)
from app.services.product_config_context import get_product_record
from app.services.task_access import can_read_task

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/it-team")
def dashboard_metrics(
    request: Request,
    product_id: str | None = None,
    refresh: bool = False,
    time_range: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    runtime_store = store(request)
    cutoff = dashboard_time_cutoff(time_range)
    repository = _dashboard_query_repository(runtime_store)
    if repository is not None:
        if product_id and repository.get_product(product_id) is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        started_at = perf_counter()
        cache_key = dashboard_cache_key(
            product_id=product_id,
            repository=repository,
            time_range=time_range,
            user=user,
        )
        cache = dashboard_cache_store(request.app.state)
        if refresh:
            cache.pop(cache_key, None)
        cache_entry = get_dashboard_cache_entry(
            cache,
            cache_key,
            ttl_seconds=settings.dashboard_cache_ttl_seconds,
        )
        if cache_entry is not None:
            duration_ms = int((perf_counter() - started_at) * 1000)
            metadata = dashboard_cache_entry_metadata(
                cache_hit=True,
                default_ttl_seconds=settings.dashboard_cache_ttl_seconds,
                duration_ms=duration_ms,
                entry=cache_entry,
                slow_threshold_ms=settings.dashboard_slow_threshold_ms,
            )
            record_dashboard_performance(
                logger,
                cache_hit=True,
                duration_ms=duration_ms,
                product_id=product_id,
                slow_threshold_ms=settings.dashboard_slow_threshold_ms,
                time_range=time_range,
                user=user,
            )
            return envelope(
                dashboard_with_metadata(cache_entry["data"], metadata),
                get_trace_id(request),
            )
        rows = repository.get_dashboard_it_team_source_rows(
            user_roles=list(user["roles"]),
            product_id=product_id,
        )
        data = build_dashboard_metrics_data(
            rows,
            can_read_task=can_read_task,
            product_id=product_id,
            time_range=time_range,
            cutoff=cutoff,
            user=user,
        )
        repository.save_dashboard_metric_snapshot_record(
            dashboard_metric_snapshot_record(
                product_id=product_id,
                time_range=time_range,
                cutoff=cutoff,
                data=data,
                stable_record_id=_stable_record_id,
            )
        )
        cache_entry = set_dashboard_cache_entry(
            cache,
            cache_key,
            data,
            ttl_seconds=settings.dashboard_cache_ttl_seconds,
        )
        duration_ms = int((perf_counter() - started_at) * 1000)
        metadata = dashboard_cache_entry_metadata(
            cache_hit=False,
            default_ttl_seconds=settings.dashboard_cache_ttl_seconds,
            duration_ms=duration_ms,
            entry=cache_entry,
            slow_threshold_ms=settings.dashboard_slow_threshold_ms,
        )
        record_dashboard_performance(
            logger,
            cache_hit=False,
            duration_ms=duration_ms,
            product_id=product_id,
            slow_threshold_ms=settings.dashboard_slow_threshold_ms,
            time_range=time_range,
            user=user,
        )
        return envelope(dashboard_with_metadata(data, metadata), get_trace_id(request))

    current_store = runtime_store
    if product_id and get_product_record(current_store, product_id) is None:
        raise api_error(404, "NOT_FOUND", "Product not found")

    started_at = perf_counter()
    rows = dashboard_source_rows_from_store(
        current_store,
        can_read_roles=_user_can_read_roles,
        user=user,
    )
    data = build_dashboard_metrics_data(
        rows,
        can_read_task=can_read_task,
        product_id=product_id,
        time_range=time_range,
        cutoff=cutoff,
        user=user,
    )
    sync_dashboard_metric_snapshot(
        current_store,
        product_id=product_id,
        time_range=time_range,
        cutoff=cutoff,
        data=data,
        stable_record_id=_stable_record_id,
    )
    _save_dashboard_snapshot_records(current_store)
    cache_entry = dashboard_transient_entry()
    duration_ms = int((perf_counter() - started_at) * 1000)
    metadata = dashboard_cache_entry_metadata(
        cache_hit=False,
        default_ttl_seconds=settings.dashboard_cache_ttl_seconds,
        duration_ms=duration_ms,
        entry=cache_entry,
        slow_threshold_ms=settings.dashboard_slow_threshold_ms,
    )
    record_dashboard_performance(
        logger,
        cache_hit=False,
        duration_ms=duration_ms,
        product_id=product_id,
        slow_threshold_ms=settings.dashboard_slow_threshold_ms,
        time_range=time_range,
        user=user,
    )
    return envelope(dashboard_with_metadata(data, metadata), get_trace_id(request))


def _runtime_repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def _dashboard_query_repository(current_store: Any) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = (
        "get_dashboard_it_team_source_rows",
        "get_product",
        "save_dashboard_metric_snapshot_record",
    )
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _save_dashboard_snapshot_records(current_store: Any) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_dashboard_snapshots", None)
    if save_records is not None:
        save_records({"dashboard_metric_snapshots": _dashboard_metric_snapshot_rows(current_store)})


def _dashboard_metric_snapshot_rows(current_store: Any) -> dict[str, dict[str, Any]]:
    snapshots = getattr(current_store, "dashboard_metric_snapshots", {})
    return snapshots if isinstance(snapshots, dict) else {}


def _stable_record_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha1(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _user_can_read_roles(user: dict[str, Any], permission_roles: list[str]) -> bool:
    user_roles = set(user["roles"])
    if "admin" in user_roles:
        return True
    return bool(user_roles.intersection(permission_roles))
