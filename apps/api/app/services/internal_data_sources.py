from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.listing import list_text_matches, sort_list_items
from app.services.bug_listing import list_bugs_response
from app.services.product_config_context import (
    product_config_query_repository,
    product_list_projection,
)
from app.services.product_scope import product_scope_filter
from app.services.requirement_listing import list_requirements_response
from app.services.user_insights import (
    list_user_insight_items_response,
    user_insight_rows,
)

INTERNAL_DATA_SOURCE_PROTOCOL = "internal_read_model"
INTERNAL_DATA_SOURCE_ACTION_TYPE = "internal_query"
INTERNAL_DATA_SOURCE_DETAIL_PERMISSION = "system.internal_data_source.detail"
INTERNAL_DATA_SOURCE_FETCH_PAGE_SIZE = 500
INTERNAL_DATA_SOURCE_MAX_SCAN_PAGES = 20

INTERNAL_DATA_SOURCE_REGISTRY: dict[str, dict[str, Any]] = {
    "bugs": {
        "detail_fields": [
            "id",
            "title",
            "description",
            "product_id",
            "version_id",
            "version_name",
            "module_code",
            "severity",
            "priority",
            "status",
            "source",
            "assignee",
            "reporter",
            "created_at",
            "updated_at",
            "closed_at",
            "raw_payload",
        ],
        "field_permissions": {
            "description": INTERNAL_DATA_SOURCE_DETAIL_PERMISSION,
            "raw_payload": INTERNAL_DATA_SOURCE_DETAIL_PERMISSION,
        },
        "label": "Bug 数据",
        "read_permission": "bug.read",
        "summary_fields": [
            "id",
            "title",
            "product_id",
            "version_id",
            "version_name",
            "module_code",
            "severity",
            "status",
            "source",
            "assignee",
            "created_at",
            "updated_at",
        ],
    },
    "products": {
        "detail_fields": [
            "id",
            "code",
            "name",
            "description",
            "status",
            "owner_team",
            "current_version_id",
            "current_version_name",
            "module_count",
            "created_at",
            "updated_at",
        ],
        "field_permissions": {
            "description": INTERNAL_DATA_SOURCE_DETAIL_PERMISSION,
        },
        "label": "产品数据",
        "read_permission": "product.read",
        "summary_fields": [
            "id",
            "code",
            "name",
            "status",
            "owner_team",
            "current_version_name",
            "module_count",
            "updated_at",
        ],
    },
    "requirements": {
        "detail_fields": [
            "id",
            "title",
            "description",
            "product_id",
            "product_name",
            "version_id",
            "version_name",
            "module_code",
            "priority",
            "status",
            "source",
            "assignee",
            "created_at",
            "updated_at",
            "raw_payload",
        ],
        "field_permissions": {
            "description": INTERNAL_DATA_SOURCE_DETAIL_PERMISSION,
            "raw_payload": INTERNAL_DATA_SOURCE_DETAIL_PERMISSION,
        },
        "label": "需求数据",
        "read_permission": "requirement.read",
        "summary_fields": [
            "id",
            "title",
            "product_id",
            "product_name",
            "version_id",
            "version_name",
            "priority",
            "status",
            "source",
            "assignee",
            "created_at",
            "updated_at",
        ],
    },
    "user_insights": {
        "detail_fields": [
            "id",
            "category",
            "summary",
            "evidence",
            "product_id",
            "version_id",
            "module_code",
            "feature_code",
            "owner",
            "priority",
            "status",
            "confidence_level",
            "created_at",
            "updated_at",
            "raw_feedback",
        ],
        "field_permissions": {
            "evidence": INTERNAL_DATA_SOURCE_DETAIL_PERMISSION,
            "raw_feedback": INTERNAL_DATA_SOURCE_DETAIL_PERMISSION,
        },
        "label": "用户洞察数据",
        "read_permission": "insight.read",
        "summary_fields": [
            "id",
            "category",
            "summary",
            "product_id",
            "version_id",
            "module_code",
            "feature_code",
            "owner",
            "priority",
            "status",
            "confidence_level",
            "updated_at",
        ],
    },
}

INTERNAL_DATA_SOURCE_TYPES = {
    source_type: str(config["label"])
    for source_type, config in INTERNAL_DATA_SOURCE_REGISTRY.items()
}
INTERNAL_DATA_SOURCE_DEFAULT_TYPES = (
    "user_insights",
    "requirements",
    "products",
    "bugs",
)

DATE_FIELDS = (
    "updated_at",
    "created_at",
    "observed_at",
    "window_start",
    "window_end",
)


def _query_section(config: dict[str, Any]) -> dict[str, Any]:
    query = config.get("query")
    return dict(query) if isinstance(query, dict) else {}


def _input_mapping(input_payload: dict[str, Any]) -> dict[str, Any]:
    mapping = input_payload.get("input_mapping")
    return dict(mapping) if isinstance(mapping, dict) else {}


def _first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, list | tuple | set):
        raw_items = list(value)
    else:
        raw_items = [value]
    return [str(item).strip() for item in raw_items if str(item).strip()]


def _normalize_source_types(value: Any) -> list[str]:
    raw_source_types = _string_list(value)
    if not raw_source_types:
        raw_source_types = list(INTERNAL_DATA_SOURCE_DEFAULT_TYPES)
    source_types: list[str] = []
    seen: set[str] = set()
    for source_type in raw_source_types:
        if source_type in seen:
            continue
        source_types.append(source_type)
        seen.add(source_type)
    unsupported = [source for source in source_types if source not in INTERNAL_DATA_SOURCE_TYPES]
    if unsupported:
        raise api_error(
            400,
            "INTERNAL_DATA_SOURCE_UNSUPPORTED",
            f"Unsupported internal source: {', '.join(unsupported)}",
        )
    return source_types


def internal_data_source_source_options() -> list[dict[str, str]]:
    ordered_source_types = [
        *INTERNAL_DATA_SOURCE_DEFAULT_TYPES,
        *[
            source_type
            for source_type in INTERNAL_DATA_SOURCE_TYPES
            if source_type not in INTERNAL_DATA_SOURCE_DEFAULT_TYPES
        ],
    ]
    return [
        {"label": INTERNAL_DATA_SOURCE_TYPES[source_type], "value": source_type}
        for source_type in ordered_source_types
    ]


def _normalize_source_filters(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    filters: dict[str, dict[str, Any]] = {}
    for source_type, source_filter in value.items():
        normalized_source_type = str(source_type).strip()
        if not normalized_source_type:
            continue
        if normalized_source_type not in INTERNAL_DATA_SOURCE_TYPES:
            raise api_error(
                400,
                "INTERNAL_DATA_SOURCE_UNSUPPORTED",
                f"Unsupported internal source: {normalized_source_type}",
            )
        if source_filter is None:
            continue
        if not isinstance(source_filter, dict):
            raise api_error(
                400,
                "INTERNAL_DATA_SOURCE_FILTER_INVALID",
                "Internal source filter must be an object",
            )
        filters[normalized_source_type] = dict(source_filter)
    return filters


def _positive_int(value: Any, *, default: int, maximum: int) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        resolved = default
    if resolved <= 0:
        return default
    return min(resolved, maximum)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        try:
            return datetime.strptime(text, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _row_datetime(row: dict[str, Any]) -> datetime | None:
    for field in DATE_FIELDS:
        parsed = _parse_datetime(row.get(field))
        if parsed is not None:
            return parsed
    return None


def _within_window(
    row: dict[str, Any],
    *,
    window_end: Any,
    window_start: Any,
) -> bool:
    row_time = _row_datetime(row)
    if row_time is None:
        return True
    start_time = _parse_datetime(window_start)
    end_time = _parse_datetime(window_end)
    if start_time is not None and row_time < start_time:
        return False
    if end_time is not None and row_time >= end_time:
        return False
    return True


def _window_requested(filters: dict[str, Any]) -> bool:
    return bool(filters.get("window_start") or filters.get("window_end"))


def _source_page_size(limit: int) -> int:
    return max(1, max(limit, INTERNAL_DATA_SOURCE_FETCH_PAGE_SIZE))


def _user_permissions(user: dict[str, Any]) -> set[str]:
    permissions = set(str(item) for item in user.get("permissions") or [])
    roles = set(str(item) for item in user.get("roles") or [])
    if "admin" in roles or "system.admin" in permissions:
        permissions.add(INTERNAL_DATA_SOURCE_DETAIL_PERMISSION)
    return permissions


def _has_permission(user: dict[str, Any], permission: str | None) -> bool:
    if not permission:
        return True
    permissions = set(str(item) for item in user.get("permissions") or [])
    roles = set(str(item) for item in user.get("roles") or [])
    return "admin" in roles or "system.admin" in permissions or permission in permissions


def _source_read_permission(source_type: str) -> str | None:
    source_config = INTERNAL_DATA_SOURCE_REGISTRY.get(source_type) or {}
    permission = source_config.get("read_permission")
    return str(permission) if permission else None


def _source_access_issue(source_type: str) -> dict[str, Any]:
    label = INTERNAL_DATA_SOURCE_TYPES.get(source_type, source_type)
    return {
        "code": "INTERNAL_DATA_SOURCE_PERMISSION_DENIED",
        "label": label,
        "message": f"缺少读取{label}的权限",
        "missing_permission": _source_read_permission(source_type),
        "source_type": source_type,
    }


def _visible_fields(
    *,
    field_mode: str,
    source_type: str,
    user: dict[str, Any],
) -> list[str]:
    if not _has_permission(user, _source_read_permission(source_type)):
        return []
    source_config = INTERNAL_DATA_SOURCE_REGISTRY[source_type]
    fields = (
        source_config["detail_fields"]
        if field_mode == "detail"
        else source_config["summary_fields"]
    )
    field_permissions = source_config.get("field_permissions")
    if not isinstance(field_permissions, dict) or not field_permissions:
        return list(fields)
    permissions = _user_permissions(user)
    return [
        str(field)
        for field in fields
        if not field_permissions.get(str(field))
        or str(field_permissions[str(field)]) in permissions
    ]


def _safe_row(
    row: dict[str, Any],
    *,
    field_mode: str,
    source_type: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    fields = _visible_fields(
        field_mode=field_mode,
        source_type=source_type,
        user=user,
    )
    return {field: row.get(field) for field in fields if field in row}


def _limit_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return rows[:limit]


def _product_rows(
    current_store: Any,
    *,
    filters: dict[str, Any],
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    product_scope_ids = product_scope_filter(user)
    repository = product_config_query_repository(current_store)
    if repository is not None:
        rows = repository.list_products(active_only=False)
    else:
        products = getattr(current_store, "products", {})
        rows = list(products.values()) if isinstance(products, dict) else []
    if product_scope_ids is not None:
        allowed = set(product_scope_ids)
        rows = [row for row in rows if str(row.get("id")) in allowed]
    if filters.get("product_id"):
        rows = [row for row in rows if str(row.get("id")) == str(filters["product_id"])]
    if filters.get("status"):
        rows = [row for row in rows if str(row.get("status")) == str(filters["status"])]
    rows = [
        row
        for row in rows
        if list_text_matches(row, filters.get("keyword"), ("code", "id", "name", "owner_team"))
    ]
    rows = [product_list_projection(row, current_store) for row in rows]
    return sort_list_items(
        rows,
        allowed_fields={"code", "display_order", "id", "name", "status", "updated_at"},
        default_sort_by="display_order",
        sort_by="display_order",
        sort_order="asc",
    )


def _requirement_rows(
    current_store: Any,
    *,
    filters: dict[str, Any],
    limit: int,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    def fetch_page(page: int, page_size: int) -> dict[str, Any]:
        return list_requirements_response(
            current_store=current_store,
            page=page,
            page_size=page_size,
            priority=filters.get("priority"),
            product=filters.get("product"),
            product_id=filters.get("product_id"),
            source=filters.get("source"),
            sort_by="created_at",
            sort_order="desc",
            started_at=None,
            status=filters.get("status"),
            title=filters.get("keyword"),
            trace_id="internal_data_source",
            user=user,
            version=None,
            version_id=filters.get("version_id"),
        )

    if _window_requested(filters):
        return _windowed_page_rows(fetch_page=fetch_page, filters=filters, limit=limit)
    return list(fetch_page(1, limit).get("items") or [])


def _bug_rows(
    current_store: Any,
    *,
    filters: dict[str, Any],
    limit: int,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    def fetch_page(page: int, page_size: int) -> dict[str, Any]:
        return list_bugs_response(
            current_store=current_store,
            module=filters.get("module_code"),
            page=page,
            page_size=page_size,
            product_id=filters.get("product_id"),
            severity=filters.get("severity"),
            sort_by="created_at",
            sort_order="desc",
            source=filters.get("source"),
            started_at=None,
            status=filters.get("status"),
            title=filters.get("keyword"),
            trace_id="internal_data_source",
            user=user,
            version=None,
            version_id=filters.get("version_id"),
        )

    if _window_requested(filters):
        return _windowed_page_rows(fetch_page=fetch_page, filters=filters, limit=limit)
    return list(fetch_page(1, limit).get("items") or [])


def _windowed_page_rows(
    *,
    fetch_page: Any,
    filters: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    page_size = _source_page_size(limit)
    collected: list[dict[str, Any]] = []
    for page in range(1, INTERNAL_DATA_SOURCE_MAX_SCAN_PAGES + 1):
        payload = fetch_page(page, page_size)
        items = list(payload.get("items") or [])
        for item in items:
            if _within_window(
                item,
                window_end=filters.get("window_end"),
                window_start=filters.get("window_start"),
            ):
                collected.append(item)
                if len(collected) >= limit:
                    return collected
        total = payload.get("total")
        if isinstance(total, int) and page * page_size >= total:
            break
        if len(items) < page_size:
            break
    return collected


def _user_insight_rows(
    current_store: Any,
    *,
    filters: dict[str, Any],
    limit: int,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_items = getattr(repository, "list_user_insight_items", None)
    if callable(list_items):
        payload = (
            _windowed_user_insight_payload(list_items=list_items, filters=filters, limit=limit)
            if _window_requested(filters)
            else list_items(
                category=filters.get("category"),
                product_id=filters.get("product_id"),
                summary=filters.get("keyword"),
                status=filters.get("status"),
                page=1,
                page_size=limit,
                sort_by="updated_at",
                sort_order="desc",
            )
        )
    else:
        payload = (
            _windowed_memory_user_insight_payload(
                current_store=current_store,
                filters=filters,
                limit=limit,
            )
            if _window_requested(filters)
            else list_user_insight_items_response(
                category=filters.get("category"),
                current_store=current_store,
                page=1,
                page_size=limit,
                product_id=filters.get("product_id"),
                sort_by="updated_at",
                sort_order="desc",
                started_at=None,
                status=filters.get("status"),
                summary=filters.get("keyword"),
                trace_id="internal_data_source",
            )
        )
    rows = list(payload.get("items") or [])
    if rows:
        result_rows = rows
    else:
        result_rows = user_insight_rows(current_store)
    product_scope_ids = product_scope_filter(user)
    if product_scope_ids is not None:
        allowed = set(product_scope_ids)
        result_rows = [
            row
            for row in result_rows
            if row.get("product_id") is not None and str(row.get("product_id")) in allowed
        ]
    return result_rows


def _windowed_user_insight_payload(
    *,
    filters: dict[str, Any],
    limit: int,
    list_items: Any,
) -> dict[str, Any]:
    page_size = _source_page_size(limit)
    collected: list[dict[str, Any]] = []
    total: int | None = None
    for page in range(1, INTERNAL_DATA_SOURCE_MAX_SCAN_PAGES + 1):
        payload = list_items(
            category=filters.get("category"),
            product_id=filters.get("product_id"),
            summary=filters.get("keyword"),
            status=filters.get("status"),
            page=page,
            page_size=page_size,
            sort_by="updated_at",
            sort_order="desc",
        )
        page_items = list(payload.get("items") or [])
        if isinstance(payload.get("total"), int):
            total = int(payload["total"])
        for item in page_items:
            if _within_window(
                item,
                window_end=filters.get("window_end"),
                window_start=filters.get("window_start"),
            ):
                collected.append(item)
                if len(collected) >= limit:
                    return {**payload, "items": collected, "total": total or len(collected)}
        if total is not None and page * page_size >= total:
            break
        if len(page_items) < page_size:
            break
    return {"items": collected, "total": total or len(collected)}


def _windowed_memory_user_insight_payload(
    *,
    current_store: Any,
    filters: dict[str, Any],
    limit: int,
) -> dict[str, Any]:
    rows = user_insight_rows(current_store)
    if filters.get("category"):
        rows = [row for row in rows if str(row.get("category")) == str(filters["category"])]
    if filters.get("product_id"):
        rows = [row for row in rows if str(row.get("product_id")) == str(filters["product_id"])]
    if filters.get("status"):
        rows = [row for row in rows if str(row.get("status")) == str(filters["status"])]
    rows = [
        row
        for row in rows
        if list_text_matches(row, filters.get("keyword"), ("summary", "evidence", "id"))
        and _within_window(
            row,
            window_end=filters.get("window_end"),
            window_start=filters.get("window_start"),
        )
    ]
    rows = sort_list_items(
        rows,
        allowed_fields={"created_at", "id", "updated_at"},
        default_sort_by="updated_at",
        sort_by="updated_at",
        sort_order="desc",
    )
    return {"items": rows[:limit], "total": len(rows)}


def _source_rows(
    current_store: Any,
    *,
    filters: dict[str, Any],
    limit: int,
    source_type: str,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    if source_type == "bugs":
        return _bug_rows(current_store, filters=filters, limit=limit, user=user)
    if source_type == "products":
        return _product_rows(current_store, filters=filters, user=user)
    if source_type == "requirements":
        return _requirement_rows(current_store, filters=filters, limit=limit, user=user)
    if source_type == "user_insights":
        return _user_insight_rows(current_store, filters=filters, limit=limit, user=user)
    raise api_error(400, "INTERNAL_DATA_SOURCE_UNSUPPORTED", "Unsupported internal source")


def internal_data_source_filters(
    request_config: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = input_payload or {}
    query = _query_section(request_config)
    input_mapping = _input_mapping(payload)
    source_types = _normalize_source_types(
        _first_value(
            payload.get("source_types"),
            input_mapping.get("source_types"),
            query.get("source_types"),
        ),
    )
    source_filters = _normalize_source_filters(
        _first_value(
            payload.get("source_filters"),
            input_mapping.get("source_filters"),
            query.get("source_filters"),
        ),
    )
    selected_source_filters = {
        source_type: source_filters[source_type]
        for source_type in source_types
        if source_type in source_filters
    }
    return {
        "category": _first_value(
            payload.get("category"),
            input_mapping.get("category"),
            query.get("category"),
        ),
        "field_mode": str(
            _first_value(
                payload.get("field_mode"),
                input_mapping.get("field_mode"),
                query.get("field_mode"),
                "summary",
            ),
        ),
        "keyword": _first_value(
            payload.get("keyword"),
            input_mapping.get("keyword"),
            query.get("keyword"),
        ),
        "limit": _positive_int(
            _first_value(payload.get("limit"), input_mapping.get("limit"), query.get("limit")),
            default=100,
            maximum=500,
        ),
        "module_code": _first_value(
            payload.get("module_code"),
            input_mapping.get("module_code"),
            query.get("module_code"),
        ),
        "priority": _first_value(
            payload.get("priority"),
            input_mapping.get("priority"),
            query.get("priority"),
        ),
        "product": _first_value(
            payload.get("product"),
            input_mapping.get("product"),
            query.get("product"),
        ),
        "product_id": _first_value(
            payload.get("product_id"),
            input_mapping.get("product_id"),
            query.get("product_id"),
        ),
        "severity": _first_value(
            payload.get("severity"),
            input_mapping.get("severity"),
            query.get("severity"),
        ),
        "source": _first_value(
            payload.get("source"),
            input_mapping.get("source"),
            query.get("source"),
        ),
        "source_filters": selected_source_filters,
        "source_types": source_types,
        "status": _first_value(
            payload.get("status"),
            input_mapping.get("status"),
            query.get("status"),
        ),
        "version_id": _first_value(
            payload.get("version_id"),
            input_mapping.get("version_id"),
            query.get("version_id"),
        ),
        "window_end": _first_value(
            payload.get("window_end"),
            input_mapping.get("window_end"),
            query.get("window_end"),
            input_mapping.get("week_end"),
        ),
        "window_start": _first_value(
            payload.get("window_start"),
            input_mapping.get("window_start"),
            query.get("window_start"),
            input_mapping.get("week_start"),
        ),
    }


def _filters_for_source(filters: dict[str, Any], source_type: str) -> dict[str, Any]:
    source_filters = filters.get("source_filters")
    if not isinstance(source_filters, dict):
        return filters
    source_filter = source_filters.get(source_type)
    if not isinstance(source_filter, dict):
        return filters
    return {
        **filters,
        **source_filter,
        "source_filters": source_filters,
        "source_types": filters.get("source_types"),
    }


def _limit_for_source(filters: dict[str, Any], default_limit: int) -> int:
    return _positive_int(
        filters.get("limit"),
        default=default_limit,
        maximum=500,
    )


def internal_data_source_dataset_schemas(
    *,
    field_mode: str,
    source_types: list[str],
    user: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        source_type: {
            **(
                {
                    "access_status": "denied",
                    "missing_permission": _source_read_permission(source_type),
                }
                if not _has_permission(user, _source_read_permission(source_type))
                else {"access_status": "granted"}
            ),
            "field_mode": field_mode,
            "fields": _visible_fields(
                field_mode=field_mode,
                source_type=source_type,
                user=user,
            ),
            "label": INTERNAL_DATA_SOURCE_TYPES[source_type],
        }
        for source_type in source_types
    }


def read_internal_data_source(
    *,
    current_store: Any,
    input_payload: dict[str, Any] | None,
    request_config: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    filters = internal_data_source_filters(request_config, input_payload)
    field_mode = "detail" if filters["field_mode"] == "detail" else "summary"
    limit = int(filters["limit"])
    datasets: dict[str, list[dict[str, Any]]] = {}
    access_issues: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    for source_type in filters["source_types"]:
        if not _has_permission(user, _source_read_permission(source_type)):
            datasets[source_type] = []
            source_counts[source_type] = 0
            access_issues.append(_source_access_issue(source_type))
            continue
        source_filters = _filters_for_source(filters, source_type)
        source_limit = _limit_for_source(source_filters, limit)
        rows = _source_rows(
            current_store,
            filters=source_filters,
            limit=source_limit,
            source_type=source_type,
            user=user,
        )
        rows = [
            row
            for row in rows
            if _within_window(
                row,
                window_end=source_filters.get("window_end"),
                window_start=source_filters.get("window_start"),
            )
        ]
        safe_rows = [
            _safe_row(
                row,
                field_mode=field_mode,
                source_type=source_type,
                user=user,
            )
            for row in _limit_rows(rows, source_limit)
        ]
        datasets[source_type] = safe_rows
        source_counts[source_type] = len(safe_rows)
    total_rows = sum(source_counts.values())
    return {
        "access_issues": access_issues,
        "datasets": datasets,
        "filters": {
            key: value
            for key, value in filters.items()
            if key not in {"source_types"} and value not in (None, "")
        },
        "labels": {
            source_type: INTERNAL_DATA_SOURCE_TYPES[source_type]
            for source_type in filters["source_types"]
        },
        "row_count": total_rows,
        "schemas": internal_data_source_dataset_schemas(
            field_mode=field_mode,
            source_types=filters["source_types"],
            user=user,
        ),
        "source_counts": source_counts,
        "source_types": filters["source_types"],
        "total_rows": total_rows,
    }


def internal_data_source_request_preview(
    *,
    connection: dict[str, Any],
    input_payload: dict[str, Any] | None,
    request_config: dict[str, Any],
) -> dict[str, Any]:
    filters = internal_data_source_filters(request_config, input_payload)
    return {
        "endpoint_url": connection.get("endpoint_url"),
        "filters": {
            key: value
            for key, value in filters.items()
            if key not in {"source_types"} and value not in (None, "")
        },
        "method": "INTERNAL_READ",
        "protocol": INTERNAL_DATA_SOURCE_PROTOCOL,
        "source_labels": {
            source_type: INTERNAL_DATA_SOURCE_TYPES[source_type]
            for source_type in filters["source_types"]
        },
        "source_types": filters["source_types"],
    }
