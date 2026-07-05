from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.operational_records import (
    GITLAB_DAILY_METRIC_STATUSES,
    ensure_enum,
    ensure_non_blank,
    operational_query_repository,
    operational_write_store,
    read_memory_dict,
    read_memory_records,
    record_audit_event,
    save_single_repository_record,
    uses_repository_context,
)


def parse_metric_date(value: str, field_name: str = "metric_date") -> str:
    text = ensure_non_blank(value, field_name)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"{field_name} must be YYYY-MM-DD") from exc


def validate_gitlab_metric_payload(payload: Any) -> str:
    ensure_enum(payload.status, GITLAB_DAILY_METRIC_STATUSES, "status")
    for field_name in (
        "active_author_count",
        "additions",
        "changed_files",
        "commit_count",
        "deletions",
        "merge_request_count",
        "risk_count",
    ):
        if getattr(payload, field_name) < 0:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"{field_name} must be greater than or equal to 0",
            )
    if payload.quality_score is not None and (
        payload.quality_score < 0 or payload.quality_score > 100
    ):
        raise api_error(400, "VALIDATION_ERROR", "quality_score must be between 0 and 100")
    return parse_metric_date(payload.metric_date)


def validate_gitlab_metric_context(
    current_store: Any,
    *,
    product_id: str,
    repository_id: str,
) -> None:
    product = read_memory_dict(current_store, "products").get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    repository = read_memory_dict(current_store, "product_git_repositories").get(repository_id)
    if repository is None or repository["product_id"] != product_id:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    if repository.get("status") != "active":
        raise api_error(400, "VALIDATION_ERROR", "Inactive Git repository cannot be used")
    if repository.get("git_provider") != "gitlab":
        raise api_error(400, "VALIDATION_ERROR", "Only GitLab repositories are supported")


def list_gitlab_metrics_response(
    *,
    current_store: Any,
    date: str | None,
    product_id: str | None,
    repository_id: str | None,
) -> dict[str, Any]:
    metric_date = parse_metric_date(date, "date") if date is not None else None
    repository = operational_query_repository(current_store)
    list_metrics = getattr(repository, "list_gitlab_daily_code_metrics", None)
    if callable(list_metrics):
        items = list_metrics(
            product_id=product_id,
            repository_id=repository_id,
            metric_date=metric_date,
        )
        return {"items": items, "total": len(items)}
    items = []
    for metric in read_memory_records(current_store, "gitlab_daily_code_metrics"):
        if product_id is not None and metric.get("product_id") != product_id:
            continue
        if repository_id is not None and metric.get("repository_id") != repository_id:
            continue
        if metric_date is not None and metric.get("metric_date") != metric_date:
            continue
        items.append(metric)
    items.sort(
        key=lambda item: (
            item.get("metric_date") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return {"items": items, "total": len(items)}


def create_gitlab_metric_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"devops.read"}, {"product_owner", "rd_owner"})
    write_store = operational_write_store(current_store)
    validate_gitlab_metric_context(
        write_store,
        product_id=payload.product_id,
        repository_id=payload.repository_id,
    )
    metric_date = validate_gitlab_metric_payload(payload)
    now = datetime.now(UTC).isoformat()
    metric_id = write_store.new_id("gitlab_metric")
    metric = {
        "active_author_count": payload.active_author_count,
        "additions": payload.additions,
        "author_metrics": payload.author_metrics,
        "changed_files": payload.changed_files,
        "collected_at": now,
        "commit_count": payload.commit_count,
        "created_at": now,
        "created_by": user["id"],
        "deletions": payload.deletions,
        "id": metric_id,
        "merge_request_count": payload.merge_request_count,
        "metric_date": metric_date,
        "product_id": payload.product_id,
        "quality_score": payload.quality_score,
        "repository_id": payload.repository_id,
        "risk_count": payload.risk_count,
        "source_channel": payload.source_channel,
        "status": payload.status,
        "updated_at": now,
    }
    for optional_key in ("quality_score", "source_channel"):
        if metric[optional_key] is None:
            metric.pop(optional_key)
    if not uses_repository_context(write_store):
        write_store.gitlab_daily_code_metrics[metric_id] = metric
    audit_event = record_audit_event(
        write_store,
        event_type="gitlab_daily_code_metric.created",
        actor_id=user["id"],
        subject_type="gitlab_daily_code_metric",
        subject_id=metric_id,
        payload={
            "metric_date": metric["metric_date"],
            "product_id": metric["product_id"],
            "repository_id": metric["repository_id"],
        },
    )
    save_single_repository_record(
        write_store,
        "save_gitlab_daily_code_metric_record",
        metric,
        audit_event=audit_event,
    )
    return metric
