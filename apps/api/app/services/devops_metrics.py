from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    first_list_value,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.services.product_scope import product_scope_filter

OPERATIONAL_METRIC_SORT_FIELDS = {"category", "id", "name", "status", "updated_at", "value"}


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_memory_dict(current_store, collection_name).values())


def operational_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    list_items = getattr(repository, "list_operational_metric_items", None)
    if callable(list_items):
        return repository
    required_methods = (
        "list_gitlab_daily_code_metrics",
        "list_jenkins_release_records",
        "list_online_log_metrics",
    )
    if all(callable(getattr(repository, method_name, None)) for method_name in required_methods):
        return repository
    return None


def operational_metric_projection(category: str, item: dict[str, Any]) -> dict[str, Any]:
    updated_at = first_list_value(
        item,
        (
            "updated_at",
            "created_at",
            "collected_at",
            "deployed_at",
            "started_at",
            "metric_date",
            "window_start",
        ),
    )
    return {
        **item,
        "category": category,
        "name": str(
            first_list_value(
                item,
                (
                    "name",
                    "metric_name",
                    "repository_name",
                    "release_name",
                    "title",
                    "job_name",
                    "build_id",
                    "repository_id",
                    "metric_date",
                    "environment",
                    "window_start",
                ),
            )
            or "-"
        ),
        "status": str(item.get("status") or "-"),
        "updated_at": str(updated_at or ""),
        "value": first_list_value(
            item,
            (
                "value",
                "count",
                "score",
                "summary",
                "commit_count",
                "quality_score",
                "build_id",
                "duration_seconds",
                "error_rate",
                "request_count",
                "p95_latency_ms",
            ),
        ),
    }


def operational_metric_rows(current_store: Any) -> list[dict[str, Any]]:
    repository = operational_query_repository(current_store)
    if repository is not None and not callable(
        getattr(repository, "list_operational_metric_items", None)
    ):
        gitlab_metrics = repository.list_gitlab_daily_code_metrics()
        jenkins_releases = repository.list_jenkins_release_records()
        deployment_requests = (
            repository.list_deployment_requests()
            if callable(getattr(repository, "list_deployment_requests", None))
            else []
        )
        online_logs = repository.list_online_log_metrics()
    else:
        gitlab_metrics = _memory_records(current_store, "gitlab_daily_code_metrics")
        jenkins_releases = _memory_records(current_store, "jenkins_release_records")
        deployment_requests = _memory_records(current_store, "deployment_requests")
        online_logs = _memory_records(current_store, "online_log_metrics")
    return [
        *(operational_metric_projection("GitLab 指标", item) for item in gitlab_metrics),
        *(operational_metric_projection("Jenkins 发布", item) for item in jenkins_releases),
        *(operational_metric_projection("运维部署", item) for item in deployment_requests),
        *(operational_metric_projection("线上日志", item) for item in online_logs),
    ]


def list_operational_metrics_response(
    *,
    category: str | None,
    current_store: Any,
    name: str | None,
    page: int | None,
    page_size: int | None,
    sort_by: str | None,
    sort_order: str,
    started_at: float | None,
    status: str | None,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "updated_at"
    if resolved_sort_by not in OPERATIONAL_METRIC_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    filters = {"category": category, "name": name, "status": status}
    scoped_product_ids = product_scope_filter(user)

    repository = operational_query_repository(current_store)
    list_items = (
        getattr(repository, "list_operational_metric_items", None)
        if repository is not None
        else None
    )
    if callable(list_items):
        return add_list_observability(
            list_items(
                category=category,
                name=name,
                status=status,
                product_scope_ids=scoped_product_ids,
                page=page,
                page_size=page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
            ),
            filters=filters,
            list_name="devops_operational_metrics",
            page=page or 1,
            page_size=page_size or 10,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )

    items = operational_metric_rows(current_store)
    if scoped_product_ids is not None:
        scoped_set = set(scoped_product_ids)
        items = [
            item
            for item in items
            if item.get("product_id") is not None and str(item.get("product_id")) in scoped_set
        ]
    if category is not None:
        items = [item for item in items if item.get("category") == category]
    if status is not None:
        items = [item for item in items if item.get("status") == status]
    items = [
        item
        for item in items
        if list_text_matches(
            item,
            name,
            ("name", "id", "product_id", "version_id", "module_code"),
        )
    ]
    items = sort_list_items(
        items,
        allowed_fields=OPERATIONAL_METRIC_SORT_FIELDS,
        default_sort_by="updated_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters=filters,
        list_name="devops_operational_metrics",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )["data"]
