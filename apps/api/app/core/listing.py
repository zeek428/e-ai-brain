from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from fastapi import HTTPException

from app.core.trace import envelope

DEFAULT_LIST_P95_TARGET_MS = 500
DEFAULT_LIST_SLOW_THRESHOLD_MS = DEFAULT_LIST_P95_TARGET_MS
LIST_P95_TARGETS_MS = {
    "ai_tasks": 300,
    "audit_events": 500,
    "assistant_action_drafts": 400,
    "bugs": 300,
    "code_inspections": 400,
    "devops_operational_metrics": 500,
    "execution_traces": 500,
    "knowledge_documents": 400,
    "model_gateway_configs": 300,
    "plugin_actions": 400,
    "plugin_connections": 400,
    "product_versions": 300,
    "products": 300,
    "rd_task_executor_policies": 300,
    "roles": 300,
    "requirements": 300,
    "scheduled_job_runs": 400,
    "scheduled_jobs": 400,
    "users": 300,
    "user_insights": 400,
}
logger = logging.getLogger(__name__)


def api_validation_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"code": "VALIDATION_ERROR", "message": message},
    )


def ensure_list_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is not None and value not in allowed_values:
        raise api_validation_error(f"Unsupported {field}")


def normalize_list_text(value: Any) -> str:
    return str(value or "").strip().lower()


def list_text_matches(item: dict[str, Any], keyword: str | None, fields: tuple[str, ...]) -> bool:
    normalized_keyword = normalize_list_text(keyword)
    if not normalized_keyword:
        return True
    return normalized_keyword in " ".join(
        normalize_list_text(item.get(field)) for field in fields
    )


def first_list_value(item: dict[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = item.get(field)
        if value is not None and value != "":
            return value
    return None


def list_sort_value(value: Any) -> tuple[int, float | str]:
    if value is None or value == "":
        return (0, "")
    if isinstance(value, bool):
        return (1, float(int(value)))
    if isinstance(value, (int, float)):
        return (1, float(value))
    return (2, normalize_list_text(value))


def sort_list_items(
    items: list[dict[str, Any]],
    *,
    allowed_fields: set[str],
    default_sort_by: str,
    sort_by: str | None,
    sort_order: str,
) -> list[dict[str, Any]]:
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or default_sort_by
    if resolved_sort_by not in allowed_fields:
        raise api_validation_error("Unsupported sort_by")
    return sorted(
        items,
        key=lambda item: list_sort_value(item.get(resolved_sort_by)),
        reverse=sort_order == "desc",
    )


def normalized_list_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                continue
            normalized[key] = trimmed
            continue
        normalized[key] = value
    return normalized


def list_query_metadata(
    *,
    filters: dict[str, Any] | None = None,
    name: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "filters": normalized_list_filters(filters),
    }
    if name:
        metadata["name"] = name
    if page is not None:
        metadata["page"] = page
    if page_size is not None:
        metadata["page_size"] = page_size
    if sort_by:
        metadata["sort_by"] = sort_by
    if sort_order:
        metadata["sort_order"] = sort_order
    return metadata


def list_p95_target_ms(list_name: str | None) -> int:
    return LIST_P95_TARGETS_MS.get(str(list_name or ""), DEFAULT_LIST_P95_TARGET_MS)


def list_performance_metadata(
    *,
    list_name: str | None = None,
    result_count: int,
    total: int,
    started_at: float | None = None,
    slow_threshold_ms: int | None = None,
) -> dict[str, Any]:
    duration_ms = int((perf_counter() - started_at) * 1000) if started_at else 0
    p95_target_ms = list_p95_target_ms(list_name)
    resolved_slow_threshold_ms = slow_threshold_ms or p95_target_ms
    return {
        "duration_ms": max(0, duration_ms),
        "p95_target_ms": p95_target_ms,
        "result_count": result_count,
        "slow": duration_ms > resolved_slow_threshold_ms,
        "slow_threshold_ms": resolved_slow_threshold_ms,
        "total": total,
    }


def record_list_performance(
    *,
    performance: dict[str, Any],
    query: dict[str, Any],
) -> None:
    if not performance.get("slow"):
        return
    logger.warning(
        (
            "slow_list_query name=%s duration_ms=%s threshold_ms=%s p95_target_ms=%s "
            "result_count=%s total=%s query=%s"
        ),
        query.get("name", "unknown"),
        performance.get("duration_ms"),
        performance.get("slow_threshold_ms"),
        performance.get("p95_target_ms"),
        performance.get("result_count"),
        performance.get("total"),
        json.dumps(query, ensure_ascii=False, sort_keys=True),
    )


def list_payload(
    items: list[dict[str, Any]],
    *,
    trace_id: str,
    active_only: bool = False,
) -> dict[str, Any]:
    visible_items = [item for item in items if not active_only or item.get("status") == "active"]
    return envelope({"items": visible_items, "total": len(visible_items)}, trace_id)


def paginated_list_payload(
    items: list[dict[str, Any]],
    *,
    page: int | None,
    page_size: int | None,
    trace_id: str,
    filters: dict[str, Any] | None = None,
    list_name: str | None = None,
    observed: bool = False,
    slow_threshold_ms: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    started_at: float | None = None,
) -> dict[str, Any]:
    if page is None and page_size is None:
        payload: dict[str, Any] = {"items": items, "total": len(items)}
        if observed:
            payload["query"] = list_query_metadata(
                filters=filters,
                name=list_name,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            payload["performance"] = list_performance_metadata(
                list_name=list_name,
                result_count=len(items),
                slow_threshold_ms=slow_threshold_ms,
                started_at=started_at,
                total=len(items),
            )
            record_list_performance(
                performance=payload["performance"],
                query=payload["query"],
            )
        return envelope(payload, trace_id)
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    total = len(items)
    start = (resolved_page - 1) * resolved_page_size
    end = start + resolved_page_size
    page_items = items[start:end]
    payload = {
        "items": page_items,
        "page": resolved_page,
        "page_size": resolved_page_size,
        "total": total,
    }
    if observed:
        payload["query"] = list_query_metadata(
            filters=filters,
            name=list_name,
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        payload["performance"] = list_performance_metadata(
            list_name=list_name,
            result_count=len(page_items),
            slow_threshold_ms=slow_threshold_ms,
            started_at=started_at,
            total=total,
        )
        record_list_performance(
            performance=payload["performance"],
            query=payload["query"],
        )
    return envelope(payload, trace_id)


def add_list_observability(
    payload: dict[str, Any],
    *,
    filters: dict[str, Any] | None = None,
    list_name: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    slow_threshold_ms: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    started_at: float | None = None,
) -> dict[str, Any]:
    items = payload.get("items") if isinstance(payload, dict) else []
    total = payload.get("total") if isinstance(payload, dict) else 0
    result_count = len(items) if isinstance(items, list) else 0
    total_count = int(total) if isinstance(total, int) else result_count
    enriched = dict(payload)
    enriched["query"] = list_query_metadata(
        filters=filters,
        name=list_name,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    enriched["performance"] = list_performance_metadata(
        list_name=list_name,
        result_count=result_count,
        slow_threshold_ms=slow_threshold_ms,
        started_at=started_at,
        total=total_count,
    )
    record_list_performance(
        performance=enriched["performance"],
        query=enriched["query"],
    )
    return enriched


def list_datetime_timestamp(value: Any) -> float:
    if not value:
        return 0.0
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()
