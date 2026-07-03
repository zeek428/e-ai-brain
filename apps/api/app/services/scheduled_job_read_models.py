from __future__ import annotations

from time import perf_counter
from typing import Any

from app.api.deps import api_error
from app.core.listing import add_list_observability, sort_list_items
from app.services.scheduled_job_access import (
    require_scheduled_job_runner,
    scheduled_job_matches_product_scope,
    scheduled_job_product_scope_filter,
    scheduled_job_run_matches_product_scope,
)
from app.services.scheduled_job_catalog import SCHEDULED_JOB_TYPES
from app.services.scheduled_job_common import ensure_enum
from app.services.scheduled_job_config import scheduled_job_with_multi_refs
from app.services.scheduled_job_constants import (
    SCHEDULED_JOB_RUN_SORT_FIELDS,
    SCHEDULED_JOB_RUN_STATUSES,
    SCHEDULED_JOB_SORT_FIELDS,
)
from app.services.scheduled_job_run_projection import public_scheduled_job_run_projection
from app.services.scheduled_job_store import (
    read_memory_dict as _read_memory_dict,
)
from app.services.scheduled_job_store import (
    scheduled_jobs_query_repository,
    sync_scheduled_job_run_store,
    sync_scheduled_job_store,
)


def list_scheduled_jobs_response(
    *,
    current_store: Any,
    enabled: bool | None,
    job_type: str | None,
    keyword: str | None = None,
    name: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    product_id: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    source_system: str | None = None,
    started_at: float | None = None,
    status: str | None = None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_scheduled_job_runner(user)
    if job_type is not None:
        ensure_enum(job_type, SCHEDULED_JOB_TYPES, "job_type")
    if status is not None:
        ensure_enum(status, {"active", "disabled"}, "status")
    if sort_order not in {"asc", "desc"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_order")
    resolved_sort_by = sort_by or "next_run_at"
    if resolved_sort_by not in SCHEDULED_JOB_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_started_at = started_at or perf_counter()
    with_pagination = page is not None or page_size is not None
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    product_scope_ids = scheduled_job_product_scope_filter(user)
    if (
        product_id is not None
        and product_scope_ids is not None
        and product_id not in product_scope_ids
    ):
        return add_list_observability(
            {
                "items": [],
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": 0,
            }
            if with_pagination
            else {"items": [], "total": 0},
            filters={
                "enabled": enabled,
                "job_type": job_type,
                "keyword": keyword,
                "name": name,
                "product_id": product_id,
                "source_system": source_system,
                "status": status,
            },
            list_name="scheduled_jobs",
            page=resolved_page if with_pagination else None,
            page_size=resolved_page_size if with_pagination else None,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=resolved_started_at,
        )
    filters = {
        "enabled": enabled,
        "job_type": job_type,
        "keyword": keyword,
        "name": name,
        "product_id": product_id,
        "product_scope_ids": product_scope_ids,
        "source_system": source_system,
        "status": status,
    }
    query_filters = {
        "enabled": enabled,
        "job_type": job_type,
        "keyword": keyword,
        "name": name,
        "product_id": product_id,
        "product_scope_ids": product_scope_ids,
        "source_system": source_system,
        "status": status,
    }
    repository = scheduled_jobs_query_repository(current_store)
    if (
        repository is not None
        and with_pagination
        and callable(getattr(repository, "count_scheduled_jobs", None))
        and callable(getattr(repository, "list_scheduled_jobs_page", None))
    ):
        total = repository.count_scheduled_jobs(**query_filters)
        items = [
            scheduled_job_with_multi_refs(job)
            for job in repository.list_scheduled_jobs_page(
                **query_filters,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
            )
        ]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="scheduled_jobs",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=resolved_started_at,
        )
    sync_scheduled_job_store(
        current_store,
        enabled=enabled,
        job_type=job_type,
        status=status,
    )
    normalized_keyword = str(keyword or "").strip().lower()
    normalized_name = str(name or "").strip().lower()
    items = []
    for job in _read_memory_dict(current_store, "scheduled_jobs").values():
        if enabled is not None and job.get("enabled") is not enabled:
            continue
        if job_type is not None and job.get("job_type") != job_type:
            continue
        if product_id is not None and job.get("product_id") != product_id:
            continue
        if product_scope_ids is not None and str(job.get("product_id")) not in product_scope_ids:
            continue
        if source_system is not None and job.get("source_system") != source_system:
            continue
        if status is not None and job.get("status") != status:
            continue
        if normalized_name and normalized_name not in str(job.get("name") or "").lower():
            continue
        if normalized_keyword:
            searchable = " ".join(
                str(job.get(field) or "")
                for field in ("id", "name", "job_type", "source_system", "product_id")
            ).lower()
            if normalized_keyword not in searchable:
                continue
        items.append(scheduled_job_with_multi_refs(job))
    items = sort_list_items(
        items,
        allowed_fields=SCHEDULED_JOB_SORT_FIELDS,
        default_sort_by="next_run_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    payload: dict[str, Any] = {"items": items, "total": total}
    if with_pagination:
        payload = {
            "items": items[
                (resolved_page - 1) * resolved_page_size : resolved_page * resolved_page_size
            ],
            "page": resolved_page,
            "page_size": resolved_page_size,
            "total": total,
        }
    return add_list_observability(
        payload,
        filters=filters,
        list_name="scheduled_jobs",
        page=resolved_page if with_pagination else None,
        page_size=resolved_page_size if with_pagination else None,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=resolved_started_at,
    )


def public_scheduled_job_run(
    run: dict[str, Any],
    *,
    current_store: Any,
) -> dict[str, Any]:
    public_run = dict(run)
    if not public_run.get("scheduled_job_name"):
        scheduled_job_id = public_run.get("scheduled_job_id")
        job = (
            _read_memory_dict(current_store, "scheduled_jobs").get(str(scheduled_job_id))
            if scheduled_job_id
            else None
        )
        if isinstance(job, dict):
            public_run["scheduled_job_name"] = job.get("name")
    source_run_id = run.get("source_run_id")
    source_run = (
        _read_memory_dict(current_store, "scheduled_job_runs").get(str(source_run_id))
        if source_run_id
        else None
    )
    return public_scheduled_job_run_projection(public_run, source_run=source_run)


def list_scheduled_job_runs_response(
    *,
    current_store: Any,
    scheduled_job_id: str | None,
    status: str | None,
    user: dict[str, Any],
    page: int | None = None,
    page_size: int | None = None,
    run_ids: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
) -> dict[str, Any]:
    require_scheduled_job_runner(user)
    if status is not None:
        ensure_enum(status, SCHEDULED_JOB_RUN_STATUSES, "status")
    if sort_order not in {"asc", "desc"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_order")
    resolved_sort_by = sort_by or "started_at"
    if resolved_sort_by not in SCHEDULED_JOB_RUN_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_started_at = started_at or perf_counter()
    with_pagination = page is not None or page_size is not None
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    product_scope_ids = scheduled_job_product_scope_filter(user)
    sync_scheduled_job_store(current_store)
    if scheduled_job_id is not None:
        job = _read_memory_dict(current_store, "scheduled_jobs").get(scheduled_job_id)
        if job is None or not scheduled_job_matches_product_scope(job, user):
            return add_list_observability(
                {
                    "items": [],
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "total": 0,
                }
                if with_pagination
                else {"items": [], "total": 0},
                filters={
                    "run_ids": run_ids,
                    "scheduled_job_id": scheduled_job_id,
                    "status": status,
                },
                list_name="scheduled_job_runs",
                page=resolved_page if with_pagination else None,
                page_size=resolved_page_size if with_pagination else None,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=resolved_started_at,
            )
    normalized_run_ids = {
        str(run_id).strip()
        for run_id in (run_ids or [])
        if str(run_id).strip()
    }
    filters = {
        "run_ids": sorted(normalized_run_ids) if normalized_run_ids else None,
        "scheduled_job_id": scheduled_job_id,
        "status": status,
    }
    repository = scheduled_jobs_query_repository(current_store)
    if (
        repository is not None
        and with_pagination
        and callable(getattr(repository, "count_scheduled_job_runs", None))
        and callable(getattr(repository, "list_scheduled_job_runs_page", None))
    ):
        total = repository.count_scheduled_job_runs(
            product_scope_ids=product_scope_ids,
            run_ids=sorted(normalized_run_ids) if normalized_run_ids else None,
            scheduled_job_id=scheduled_job_id,
            status=status,
        )
        page_items = repository.list_scheduled_job_runs_page(
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            product_scope_ids=product_scope_ids,
            run_ids=sorted(normalized_run_ids) if normalized_run_ids else None,
            scheduled_job_id=scheduled_job_id,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            status=status,
        )
        source_run_ids = sorted(
            {
                str(item.get("source_run_id"))
                for item in page_items
                if item.get("source_run_id")
            }
        )
        if source_run_ids:
            sync_scheduled_job_run_store(current_store, run_ids=source_run_ids)
        return add_list_observability(
            {
                "items": [
                    public_scheduled_job_run(run, current_store=current_store) for run in page_items
                ],
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="scheduled_job_runs",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=resolved_started_at,
        )
    sync_scheduled_job_run_store(
        current_store,
        run_ids=sorted(normalized_run_ids) if normalized_run_ids else None,
        scheduled_job_id=scheduled_job_id,
        status=status,
    )
    items = []
    for run in _read_memory_dict(current_store, "scheduled_job_runs").values():
        if normalized_run_ids and run.get("id") not in normalized_run_ids:
            continue
        if scheduled_job_id is not None and run.get("scheduled_job_id") != scheduled_job_id:
            continue
        if status is not None and run.get("status") != status:
            continue
        if not scheduled_job_run_matches_product_scope(current_store, run, user):
            continue
        items.append(public_scheduled_job_run(run, current_store=current_store))
    items = sort_list_items(
        items,
        allowed_fields=SCHEDULED_JOB_RUN_SORT_FIELDS,
        default_sort_by="started_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    payload: dict[str, Any] = {"items": items, "total": total}
    if with_pagination:
        payload = {
            "items": items[
                (resolved_page - 1) * resolved_page_size : resolved_page * resolved_page_size
            ],
            "page": resolved_page,
            "page_size": resolved_page_size,
            "total": total,
        }
    return add_list_observability(
        payload,
        filters=filters,
        list_name="scheduled_job_runs",
        page=resolved_page if with_pagination else None,
        page_size=resolved_page_size if with_pagination else None,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=resolved_started_at,
    )
