from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.services.bug_lifecycle import validate_bug_enums

BUG_SORT_FIELDS = {
    "assignee",
    "created_at",
    "id",
    "module_code",
    "severity",
    "source",
    "status",
    "title",
    "updated_at",
    "version_code",
    "version_name",
}


def bug_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    if callable(getattr(repository, "list_bugs", None)):
        return repository
    return None


def bug_list_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    count_bugs = getattr(repository, "count_bug_summaries", None)
    list_bugs = getattr(repository, "list_bug_summaries", None)
    if callable(count_bugs) and callable(list_bugs):
        return repository
    return None


def bug_summary_projection(bug: dict[str, Any], current_store: Any) -> dict[str, Any]:
    version = current_store.product_versions.get(bug.get("version_id"), {})
    return {
        **bug,
        "version_code": version.get("code"),
        "version_name": version.get("name"),
    }


def list_bugs_response(
    *,
    current_store: Any,
    module: str | None,
    page: int | None,
    page_size: int | None,
    product_id: str | None,
    severity: str | None,
    sort_by: str | None,
    sort_order: str,
    source: str | None,
    started_at: float | None,
    status: str | None,
    title: str | None,
    trace_id: str,
    version: str | None,
    version_id: str | None,
) -> dict[str, Any]:
    validate_bug_enums(source=source, severity=severity, status=status)
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "created_at"
    if resolved_sort_by not in BUG_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")

    filters = {
        "module": module,
        "product_id": product_id,
        "severity": severity,
        "source": source,
        "status": status,
        "title": title,
        "version": version,
        "version_id": version_id,
    }
    list_repository = bug_list_query_repository(current_store)
    if list_repository is not None:
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        total = list_repository.count_bug_summaries(**filters)
        items = list_repository.list_bug_summaries(
            **filters,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="bugs",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )

    repository = bug_query_repository(current_store)
    if repository is not None:
        items = repository.list_bugs(
            product_id=product_id,
            version_id=version_id,
            status=status,
            severity=severity,
            source=source,
        )
    else:
        items = list(current_store.bugs.values())
        if product_id:
            items = [item for item in items if item["product_id"] == product_id]
        if version_id:
            items = [item for item in items if item.get("version_id") == version_id]
        if status:
            items = [item for item in items if item["status"] == status]
        if severity:
            items = [item for item in items if item["severity"] == severity]
        if source:
            items = [item for item in items if item["source"] == source]
        items.sort(key=lambda item: item["created_at"], reverse=True)
        items = [bug_summary_projection(item, current_store) for item in items]
    items = [item for item in items if list_text_matches(item, title, ("title", "id"))]
    items = [item for item in items if list_text_matches(item, module, ("module_code",))]
    items = [
        item
        for item in items
        if list_text_matches(item, version, ("version_code", "version_name", "version_id"))
    ]
    items = sort_list_items(
        items,
        allowed_fields=BUG_SORT_FIELDS,
        default_sort_by="created_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters=filters,
        list_name="bugs",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )["data"]
