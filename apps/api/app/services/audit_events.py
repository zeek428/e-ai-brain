from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.listing import (
    api_validation_error,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)

AUDIT_SORT_FIELDS = {
    "actor_id",
    "ai_task_id",
    "created_at",
    "event_type",
    "id",
    "result",
    "sequence",
    "subject_id",
    "subject_type",
}


def parse_audit_datetime(value: str, field_name: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    if len(normalized) >= 6 and normalized[-6] == " " and normalized[-3] == ":":
        normalized = f"{normalized[:-6]}+{normalized[-5:]}"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise api_validation_error(f"Invalid {field_name}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def audit_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    list_events = getattr(repository, "list_audit_events", None)
    return repository if callable(list_events) else None


def audit_events_response(
    current_store: Any,
    *,
    ai_task_id: str | None,
    actor: str | None,
    actor_id: str | None,
    subject: str | None,
    subject_type: str | None,
    subject_id: str | None,
    event_type: str | None,
    result: str | None,
    created_from: str | None,
    created_to: str | None,
    page: int | None,
    page_size: int | None,
    sort_by: str | None,
    sort_order: str,
    started_at: float | None,
    trace_id: str,
) -> dict[str, Any]:
    ensure_list_enum(result, {"failed", "success"}, "audit result")
    from_at = parse_audit_datetime(created_from, "created_from") if created_from else None
    to_at = parse_audit_datetime(created_to, "created_to") if created_to else None
    repository = audit_query_repository(current_store)
    if repository is not None:
        items = repository.list_audit_events(
            ai_task_id=ai_task_id,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            created_from=from_at,
            created_to=to_at,
        )
    else:
        items = list(current_store.audit_events)
        if actor_id:
            items = [item for item in items if item.get("actor_id") == actor_id]
        if event_type:
            items = [item for item in items if item.get("event_type") == event_type]
        if ai_task_id:
            items = [item for item in items if item.get("ai_task_id") == ai_task_id]
        if subject_type:
            items = [item for item in items if item.get("subject_type") == subject_type]
        if subject_id:
            items = [item for item in items if item.get("subject_id") == subject_id]
        if created_from or created_to:
            filtered_items = []
            for item in items:
                event_at = parse_audit_datetime(str(item.get("created_at") or ""), "created_at")
                if from_at and event_at < from_at:
                    continue
                if to_at and event_at > to_at:
                    continue
                filtered_items.append(item)
            items = filtered_items
    items = [{**item, "result": item.get("result", "success")} for item in items]
    if result:
        items = [item for item in items if item.get("result", "success") == result]
    items = [item for item in items if list_text_matches(item, actor, ("actor_id",))]
    items = [
        item
        for item in items
        if list_text_matches(item, subject, ("subject_type", "subject_id", "ai_task_id"))
    ]
    items = sort_list_items(
        items,
        allowed_fields=AUDIT_SORT_FIELDS,
        default_sort_by="sequence",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters={
            "actor": actor,
            "actor_id": actor_id,
            "ai_task_id": ai_task_id,
            "created_from": created_from,
            "created_to": created_to,
            "event_type": event_type,
            "result": result,
            "subject": subject,
            "subject_id": subject_id,
            "subject_type": subject_type,
        },
        list_name="audit_events",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=sort_by or "sequence",
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )
