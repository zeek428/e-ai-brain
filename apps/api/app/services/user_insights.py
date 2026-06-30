from __future__ import annotations

from datetime import UTC, datetime
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
from app.services.product_config_context import product_config_source_store

USER_INSIGHT_SORT_FIELDS = {"category", "id", "owner", "status", "summary", "updated_at"}
def user_insight_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    list_items = getattr(repository, "list_user_insight_items", None)
    if callable(list_items):
        return repository
    required_methods = (
        "list_user_usage_metrics",
        "list_user_feedback",
        "list_iteration_plan_suggestions",
    )
    if all(callable(getattr(repository, method_name, None)) for method_name in required_methods):
        return repository
    return None


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def user_insight_write_store(current_store: Any) -> Any:
    repository = user_insight_query_repository(current_store)
    if repository is None:
        return current_store
    source_store = product_config_source_store(repository)
    source_store.user_usage_metrics = {
        str(item["id"]): dict(item)
        for item in repository.list_user_usage_metrics()
        if item.get("id") is not None
    }
    source_store.user_feedback = {
        str(item["id"]): dict(item)
        for item in repository.list_user_feedback()
        if item.get("id") is not None
    }
    source_store.iteration_plan_suggestions = {
        str(item["id"]): dict(item)
        for item in repository.list_iteration_plan_suggestions()
        if item.get("id") is not None
    }
    load_iteration_planning = getattr(repository, "load_iteration_planning", None)
    if callable(load_iteration_planning):
        payload = load_iteration_planning() or {}
        source_store.iteration_plan_decisions = {
            str(item["id"]): dict(item)
            for item in payload.get("iteration_plan_decisions", {}).values()
            if item.get("id") is not None
        }
    return source_store


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is not None and value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def payload_updates(payload: Any) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


def _memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, list):
        collection = []
        setattr(current_store, collection_name, collection)
    return collection


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_memory_dict(current_store, collection_name).values())


def _audit_events_collection(current_store: Any) -> list[dict[str, Any]]:
    return _memory_list(current_store, "audit_events")


def record_audit_event(
    current_store: Any,
    *,
    event_type: str,
    actor_id: str,
    subject_type: str,
    subject_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audit = getattr(current_store, "audit", None)
    if callable(audit):
        return audit(
            event_type=event_type,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
        )
    now = datetime.now(UTC).isoformat()
    event = {
        "id": current_store.new_id("audit_event"),
        "event_type": event_type,
        "actor_id": actor_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "created_at": now,
    }
    _audit_events_collection(current_store).append(event)
    return event


def save_single_repository_record(
    current_store: Any,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, method_name, None)
    if callable(save_record):
        save_record(record, audit_event=audit_event)


def save_iteration_decision_records(
    current_store: Any,
    *,
    suggestion: dict[str, Any],
    decision: dict[str, Any],
    audit_events: list[dict[str, Any]],
    requirement: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_iteration_decision_records", None)
    if callable(save_records):
        save_records(
            suggestion=suggestion,
            decision=decision,
            audit_events=audit_events,
            requirement=requirement,
        )


def user_insight_projection(category: str, item: dict[str, Any]) -> dict[str, Any]:
    updated_at = first_list_value(
        item,
        (
            "updated_at",
            "created_at",
            "observed_at",
            "window_start",
        ),
    )
    summary = str(
        first_list_value(
            item,
            (
                "summary",
                "title",
                "content",
                "feedback_text",
                "suggestion",
                "recommendation_reason",
                "feature_code",
            ),
        )
        or "-"
    )
    if len(summary) > 240:
        summary = f"{summary[:240]}..."
    return {
        **item,
        "category": category,
        "confidence_level": str(item.get("confidence_level") or "-"),
        "converted_requirement_id": str(item.get("converted_requirement_id") or "-"),
        "feature_code": str(item.get("feature_code") or "-"),
        "feedback_type": str(item.get("feedback_type") or "-"),
        "module_code": str(item.get("module_code") or "-"),
        "owner": str(
            first_list_value(item, ("user_id", "owner_id", "created_by", "actor_id")) or "-"
        ),
        "planning_cycle": str(item.get("planning_cycle") or "-"),
        "priority": str(item.get("priority") or "-"),
        "product_id": str(item.get("product_id") or "-"),
        "status": str(item.get("status") or "-"),
        "summary": summary,
        "updated_at": str(updated_at or ""),
        "version_id": str(item.get("version_id") or "-"),
    }


def user_insight_rows(current_store: Any) -> list[dict[str, Any]]:
    repository = user_insight_query_repository(current_store)
    if repository is not None and not callable(
        getattr(repository, "list_user_insight_items", None)
    ):
        usage_metrics = repository.list_user_usage_metrics()
        feedback_items = repository.list_user_feedback()
        iteration_suggestions = repository.list_iteration_plan_suggestions()
    else:
        usage_metrics = _memory_records(current_store, "user_usage_metrics")
        feedback_items = _memory_records(current_store, "user_feedback")
        iteration_suggestions = _memory_records(current_store, "iteration_plan_suggestions")
    return [
        *(user_insight_projection("使用趋势", item) for item in usage_metrics),
        *(user_insight_projection("用户反馈", item) for item in feedback_items),
        *(user_insight_projection("迭代建议", item) for item in iteration_suggestions),
    ]


def list_user_insight_items_response(
    *,
    category: str | None,
    current_store: Any,
    page: int | None,
    page_size: int | None,
    sort_by: str | None,
    sort_order: str,
    started_at: float | None,
    status: str | None,
    summary: str | None,
    trace_id: str,
) -> dict[str, Any]:
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "updated_at"
    if resolved_sort_by not in USER_INSIGHT_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    filters = {"category": category, "status": status, "summary": summary}

    repository = user_insight_query_repository(current_store)
    list_items = (
        getattr(repository, "list_user_insight_items", None) if repository is not None else None
    )
    if callable(list_items):
        return add_list_observability(
            list_items(
                category=category,
                summary=summary,
                status=status,
                page=page,
                page_size=page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
            ),
            filters=filters,
            list_name="user_insights",
            page=page or 1,
            page_size=page_size or 10,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )

    items = user_insight_rows(current_store)
    if category is not None:
        items = [item for item in items if item.get("category") == category]
    if status is not None:
        items = [item for item in items if item.get("status") == status]
    items = [
        item
        for item in items
        if list_text_matches(
            item,
            summary,
            ("summary", "id", "product_id", "version_id", "module_code", "feature_code"),
        )
    ]
    items = sort_list_items(
        items,
        allowed_fields=USER_INSIGHT_SORT_FIELDS,
        default_sort_by="updated_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters=filters,
        list_name="user_insights",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )["data"]
