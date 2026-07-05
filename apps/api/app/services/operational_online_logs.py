from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.operational_records import (
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

ONLINE_LOG_METRIC_STATUSES = {"collected", "failed", "partial"}


def parse_usage_window(value: str, field_name: str) -> str:
    text = ensure_non_blank(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"{field_name} must be an ISO datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def validate_online_log_metric_context(
    current_store: Any,
    *,
    product_id: str,
    module_code: str | None = None,
) -> None:
    product = read_memory_dict(current_store, "products").get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    if module_code is not None and not any(
        module["product_id"] == product_id
        and module["code"] == module_code
        and module.get("status", "active") == "active"
        for module in read_memory_records(current_store, "product_modules")
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")


def validate_online_log_metric_payload(payload: Any) -> tuple[str, str, float]:
    ensure_non_blank(payload.environment, "environment")
    ensure_enum(payload.status, ONLINE_LOG_METRIC_STATUSES, "status")
    for field_name in ("request_count", "error_count", "core_event_count"):
        if getattr(payload, field_name) < 0:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"{field_name} must be greater than or equal to 0",
            )
    for field_name in ("p95_latency_ms", "p99_latency_ms"):
        value = getattr(payload, field_name)
        if value is not None and value < 0:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"{field_name} must be greater than or equal to 0",
            )
    if payload.error_count > payload.request_count:
        raise api_error(400, "VALIDATION_ERROR", "error_count cannot exceed request_count")
    window_start = parse_usage_window(payload.window_start, "window_start")
    window_end = parse_usage_window(payload.window_end, "window_end")
    if window_end <= window_start:
        raise api_error(400, "VALIDATION_ERROR", "window_end must be after window_start")
    error_rate = payload.error_count / payload.request_count if payload.request_count else 0.0
    return window_start, window_end, error_rate


def list_online_log_metrics_response(
    *,
    current_store: Any,
    environment: str | None,
    from_: str | None,
    module_code: str | None,
    product_id: str | None,
    to: str | None,
) -> dict[str, Any]:
    from_value = parse_usage_window(from_, "from") if from_ is not None else None
    to_value = parse_usage_window(to, "to") if to is not None else None
    repository = operational_query_repository(current_store)
    list_metrics = getattr(repository, "list_online_log_metrics", None)
    if callable(list_metrics):
        items = list_metrics(
            product_id=product_id,
            module_code=module_code,
            environment=environment,
            from_value=from_value,
            to_value=to_value,
        )
        return {"items": items, "total": len(items)}
    items = []
    for metric in read_memory_records(current_store, "online_log_metrics"):
        if product_id is not None and metric.get("product_id") != product_id:
            continue
        if module_code is not None and metric.get("module_code") != module_code:
            continue
        if environment is not None and metric.get("environment") != environment:
            continue
        if from_value is not None and metric.get("window_end") < from_value:
            continue
        if to_value is not None and metric.get("window_start") > to_value:
            continue
        items.append(metric)
    items.sort(
        key=lambda item: (
            item.get("window_start") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return {"items": items, "total": len(items)}


def create_online_log_metric_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"devops.read"}, {"product_owner", "rd_owner"})
    write_store = operational_write_store(current_store)
    validate_online_log_metric_context(
        write_store,
        product_id=payload.product_id,
        module_code=payload.module_code,
    )
    window_start, window_end, error_rate = validate_online_log_metric_payload(payload)
    now = datetime.now(UTC).isoformat()
    metric_id = write_store.new_id("online_log_metric")
    metric = {
        "anomaly_summary": payload.anomaly_summary,
        "core_event_count": payload.core_event_count,
        "created_at": now,
        "created_by": user["id"],
        "environment": ensure_non_blank(payload.environment, "environment"),
        "error_count": payload.error_count,
        "error_rate": error_rate,
        "id": metric_id,
        "module_code": payload.module_code,
        "p95_latency_ms": payload.p95_latency_ms,
        "p99_latency_ms": payload.p99_latency_ms,
        "product_id": payload.product_id,
        "request_count": payload.request_count,
        "source_channel": payload.source_channel,
        "status": payload.status,
        "top_errors": payload.top_errors,
        "updated_at": now,
        "window_end": window_end,
        "window_start": window_start,
    }
    for optional_key in (
        "anomaly_summary",
        "module_code",
        "p95_latency_ms",
        "p99_latency_ms",
        "source_channel",
    ):
        if metric[optional_key] is None:
            metric.pop(optional_key)
    if not uses_repository_context(write_store):
        write_store.online_log_metrics[metric_id] = metric
    audit_event = record_audit_event(
        write_store,
        event_type="online_log_metric.created",
        actor_id=user["id"],
        subject_type="online_log_metric",
        subject_id=metric_id,
        payload={
            "environment": metric["environment"],
            "error_rate": metric["error_rate"],
            "product_id": metric["product_id"],
            "window_end": metric["window_end"],
            "window_start": metric["window_start"],
        },
    )
    save_single_repository_record(
        write_store,
        "save_online_log_metric_record",
        metric,
        audit_event=audit_event,
    )
    return metric
