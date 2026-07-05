from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.user_insights import (
    ensure_non_blank,
    record_audit_event,
    user_insight_query_repository,
    user_insight_write_store,
)


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _user_usage_metrics_collection(current_store: Any) -> dict[str, dict[str, Any]]:
    return _memory_dict(current_store, "user_usage_metrics")


def save_user_usage_metric_record(
    current_store: Any,
    metric: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_user_usage_metric_record", None)
    if callable(save_record):
        save_record(metric, audit_event=audit_event)
        return
    _user_usage_metrics_collection(current_store)[str(metric["id"])] = dict(metric)


def parse_usage_window(value: str, field_name: str) -> str:
    text = ensure_non_blank(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"{field_name} must be an ISO datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def validate_usage_metric_payload(payload: Any) -> tuple[str, str]:
    for field_name in ("active_users", "event_count", "conversion_count", "error_count"):
        if getattr(payload, field_name) < 0:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"{field_name} must be greater than or equal to 0",
            )
    for field_name in ("conversion_rate", "bounce_rate"):
        value = getattr(payload, field_name)
        if value is not None and (value < 0 or value > 1):
            raise api_error(400, "VALIDATION_ERROR", f"{field_name} must be between 0 and 1")
    if payload.avg_duration_seconds is not None and payload.avg_duration_seconds < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "avg_duration_seconds must be greater than or equal to 0",
        )
    window_start = parse_usage_window(payload.window_start, "window_start")
    window_end = parse_usage_window(payload.window_end, "window_end")
    if window_end <= window_start:
        raise api_error(400, "VALIDATION_ERROR", "window_end must be after window_start")
    return window_start, window_end


def validate_usage_metric_context(
    current_store: Any,
    *,
    product_id: str,
    module_code: str | None = None,
) -> None:
    product = _memory_dict(current_store, "products").get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    if module_code is not None and not any(
        module["product_id"] == product_id and module["code"] == module_code
        for module in _memory_dict(current_store, "product_modules").values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")


def list_usage_metrics_response(
    *,
    current_store: Any,
    feature_code: str | None,
    from_: str | None,
    module_code: str | None,
    product_id: str | None,
    to: str | None,
    user_segment: str | None,
) -> dict[str, Any]:
    from_value = parse_usage_window(from_, "from") if from_ is not None else None
    to_value = parse_usage_window(to, "to") if to is not None else None
    repository = user_insight_query_repository(current_store)
    if repository is not None:
        items = repository.list_user_usage_metrics(
            product_id=product_id,
            module_code=module_code,
            feature_code=feature_code,
            user_segment=user_segment,
            from_value=from_value,
            to_value=to_value,
        )
        return {"items": items, "total": len(items)}
    items = []
    for metric in _user_usage_metrics_collection(current_store).values():
        if product_id is not None and metric.get("product_id") != product_id:
            continue
        if module_code is not None and metric.get("module_code") != module_code:
            continue
        if feature_code is not None and metric.get("feature_code") != feature_code:
            continue
        if user_segment is not None and metric.get("user_segment") != user_segment:
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


def create_usage_metric_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"insight.read"}, {"product_owner", "rd_owner"})
    current_store = user_insight_write_store(current_store)
    validate_usage_metric_context(
        current_store,
        product_id=payload.product_id,
        module_code=payload.module_code,
    )
    window_start, window_end = validate_usage_metric_payload(payload)
    now = datetime.now(UTC).isoformat()
    metric_id = current_store.new_id("usage")
    metric = {
        "active_users": payload.active_users,
        "avg_duration_seconds": payload.avg_duration_seconds,
        "bounce_rate": payload.bounce_rate,
        "conversion_count": payload.conversion_count,
        "conversion_rate": payload.conversion_rate,
        "created_at": now,
        "created_by": user["id"],
        "error_count": payload.error_count,
        "event_count": payload.event_count,
        "feature_code": ensure_non_blank(payload.feature_code, "feature_code"),
        "id": metric_id,
        "module_code": payload.module_code,
        "product_id": payload.product_id,
        "source_channel": payload.source_channel,
        "updated_at": now,
        "user_segment": ensure_non_blank(payload.user_segment, "user_segment"),
        "window_end": window_end,
        "window_start": window_start,
    }
    for optional_key in (
        "avg_duration_seconds",
        "bounce_rate",
        "conversion_rate",
        "module_code",
        "source_channel",
    ):
        if metric[optional_key] is None:
            metric.pop(optional_key)
    audit_event = record_audit_event(
        current_store,
        event_type="usage_metric.created",
        actor_id=user["id"],
        subject_type="usage_metric",
        subject_id=metric_id,
        payload={
            "feature_code": metric["feature_code"],
            "product_id": metric["product_id"],
            "window_end": metric["window_end"],
            "window_start": metric["window_start"],
        },
    )
    save_user_usage_metric_record(
        current_store,
        metric,
        audit_event=audit_event,
    )
    return metric
