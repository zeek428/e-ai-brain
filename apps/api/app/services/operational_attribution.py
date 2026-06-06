from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.services.operational_records import (
    PENDING_ATTRIBUTION_RESOLUTION_ACTIONS,
    PENDING_ATTRIBUTION_SOURCE_TYPES,
    PENDING_ATTRIBUTION_STATUSES,
    ensure_enum,
    ensure_non_blank,
    operational_query_repository,
    operational_write_store,
    record_audit_event,
    save_single_repository_record,
    uses_repository_context,
)


def require_pending_attribution_write_role(user: dict[str, Any]) -> None:
    require_roles(user, {"product_owner", "rd_owner"})


def validate_pending_attribution_suggested_context(
    current_store: Any,
    *,
    suggested_product_id: str | None,
    suggested_module_code: str | None,
) -> None:
    if suggested_product_id is None:
        return
    product = current_store.products.get(suggested_product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Suggested product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive suggested product cannot be used")
    if suggested_module_code is not None and not any(
        module["product_id"] == suggested_product_id and module["code"] == suggested_module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Suggested product module not found")


def validate_pending_attribution_create_request(
    current_store: Any,
    payload: Any,
) -> tuple[str, str, str | None, str | None]:
    ensure_enum(payload.source_type, PENDING_ATTRIBUTION_SOURCE_TYPES, "source_type")
    source_system = ensure_non_blank(payload.source_system, "source_system")
    summary = ensure_non_blank(payload.summary, "summary")
    raw_subject_id = payload.raw_subject_id.strip() if payload.raw_subject_id else None
    suggested_module_code = (
        payload.suggested_module_code.strip() if payload.suggested_module_code else None
    )
    if payload.confidence is not None and (
        payload.confidence < 0 or payload.confidence > 1
    ):
        raise api_error(400, "VALIDATION_ERROR", "confidence must be between 0 and 1")
    if payload.collector_run_id is not None and payload.collector_run_id not in (
        current_store.collector_runs
    ):
        raise api_error(404, "NOT_FOUND", "Collector run not found")
    validate_pending_attribution_suggested_context(
        current_store,
        suggested_product_id=payload.suggested_product_id,
        suggested_module_code=suggested_module_code,
    )
    return source_system, summary, raw_subject_id, suggested_module_code


def validate_pending_attribution_resolve_request(
    current_store: Any,
    item: dict[str, Any],
    payload: Any,
) -> tuple[str | None, str | None, str | None, str | None, str | None, str | None]:
    if item["status"] != "pending":
        raise api_error(
            409,
            "PENDING_ATTRIBUTION_STATE_INVALID",
            "Pending attribution item is already terminal",
        )
    ensure_enum(
        payload.resolution_action,
        PENDING_ATTRIBUTION_RESOLUTION_ACTIONS,
        "resolution_action",
    )
    resolution_note = payload.resolution_note.strip() if payload.resolution_note else None
    resolved_module_code = (
        payload.resolved_module_code.strip() if payload.resolved_module_code else None
    )
    resolved_subject_type = (
        payload.resolved_subject_type.strip() if payload.resolved_subject_type else None
    )
    resolved_subject_id = (
        payload.resolved_subject_id.strip() if payload.resolved_subject_id else None
    )
    if payload.resolution_action == "ignore_as_noise":
        if any(
            (
                payload.resolved_product_id,
                resolved_module_code,
                payload.resolved_requirement_id,
                resolved_subject_type,
                resolved_subject_id,
            )
        ):
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "Ignored attribution item cannot include resolved context",
            )
        return resolution_note, None, None, None, None, None
    if payload.resolved_product_id is None:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "resolved_product_id is required for link_existing_context",
        )
    product = current_store.products.get(payload.resolved_product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Resolved product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive resolved product cannot be used")
    if resolved_module_code is not None and not any(
        module["product_id"] == payload.resolved_product_id
        and module["code"] == resolved_module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Resolved product module not found")
    if payload.resolved_requirement_id is not None:
        requirement = current_store.requirements.get(payload.resolved_requirement_id)
        if requirement is None or requirement["product_id"] != payload.resolved_product_id:
            raise api_error(404, "NOT_FOUND", "Resolved requirement not found")
    return (
        resolution_note,
        payload.resolved_product_id,
        resolved_module_code,
        payload.resolved_requirement_id,
        resolved_subject_type,
        resolved_subject_id,
    )


def list_pending_attribution_items_response(
    *,
    collector_run_id: str | None,
    current_store: Any,
    resolved_product_id: str | None,
    source_type: str | None,
    status: str | None,
) -> dict[str, Any]:
    ensure_enum(source_type, PENDING_ATTRIBUTION_SOURCE_TYPES, "source_type")
    ensure_enum(status, PENDING_ATTRIBUTION_STATUSES, "status")
    repository = operational_query_repository(current_store)
    list_items = getattr(repository, "list_pending_attribution_items", None)
    if callable(list_items):
        items = list_items(
            source_type=source_type,
            status=status,
            resolved_product_id=resolved_product_id,
            collector_run_id=collector_run_id,
        )
        return {"items": items, "total": len(items)}
    items = []
    for item in current_store.pending_attribution_items.values():
        if source_type is not None and item.get("source_type") != source_type:
            continue
        if status is not None and item.get("status") != status:
            continue
        if resolved_product_id is not None and item.get("resolved_product_id") != (
            resolved_product_id
        ):
            continue
        if collector_run_id is not None and item.get("collector_run_id") != collector_run_id:
            continue
        items.append(item)
    items.sort(
        key=lambda item: (
            item.get("created_at") or "",
            item.get("updated_at") or "",
            item["id"],
        ),
        reverse=True,
    )
    return {"items": items, "total": len(items)}


def create_pending_attribution_item_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_pending_attribution_write_role(user)
    write_store = operational_write_store(current_store)
    source_system, summary, raw_subject_id, suggested_module_code = (
        validate_pending_attribution_create_request(write_store, payload)
    )
    now = datetime.now(UTC).isoformat()
    item_id = write_store.new_id("pending_attr")
    item = {
        "collector_run_id": payload.collector_run_id,
        "confidence": payload.confidence,
        "created_at": now,
        "created_by": user["id"],
        "id": item_id,
        "raw_payload": payload.raw_payload,
        "raw_subject_id": raw_subject_id,
        "resolution_action": None,
        "resolution_note": None,
        "resolved_at": None,
        "resolved_by": None,
        "resolved_module_code": None,
        "resolved_product_id": None,
        "resolved_requirement_id": None,
        "resolved_subject_id": None,
        "resolved_subject_type": None,
        "source_system": source_system,
        "source_type": payload.source_type,
        "status": "pending",
        "suggested_module_code": suggested_module_code,
        "suggested_product_id": payload.suggested_product_id,
        "summary": summary,
        "updated_at": now,
    }
    if not uses_repository_context(write_store):
        write_store.pending_attribution_items[item_id] = item
    audit_event = record_audit_event(
        write_store,
        event_type="pending_attribution.created",
        actor_id=user["id"],
        subject_type="pending_attribution_item",
        subject_id=item_id,
        payload={
            "source_system": item["source_system"],
            "source_type": item["source_type"],
            "status": item["status"],
        },
    )
    save_single_repository_record(
        write_store,
        "save_pending_attribution_item_record",
        item,
        audit_event=audit_event,
    )
    return item


def resolve_pending_attribution_item_response(
    *,
    current_store: Any,
    item_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_pending_attribution_write_role(user)
    write_store = operational_write_store(current_store)
    item = write_store.pending_attribution_items.get(item_id)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Pending attribution item not found")
    (
        resolution_note,
        resolved_product_id,
        resolved_module_code,
        resolved_requirement_id,
        resolved_subject_type,
        resolved_subject_id,
    ) = validate_pending_attribution_resolve_request(write_store, item, payload)
    now = datetime.now(UTC).isoformat()
    status = "resolved" if payload.resolution_action == "link_existing_context" else "ignored"
    item = {
        **item,
        "resolution_action": payload.resolution_action,
        "resolution_note": resolution_note,
        "resolved_at": now,
        "resolved_by": user["id"],
        "resolved_module_code": resolved_module_code,
        "resolved_product_id": resolved_product_id,
        "resolved_requirement_id": resolved_requirement_id,
        "resolved_subject_id": resolved_subject_id,
        "resolved_subject_type": resolved_subject_type,
        "status": status,
        "updated_at": now,
    }
    if not uses_repository_context(write_store):
        write_store.pending_attribution_items[item_id] = item
    audit_event = record_audit_event(
        write_store,
        event_type=(
            "pending_attribution.resolved"
            if status == "resolved"
            else "pending_attribution.ignored"
        ),
        actor_id=user["id"],
        subject_type="pending_attribution_item",
        subject_id=item_id,
        payload={
            "resolution_action": item["resolution_action"],
            "resolved_product_id": item.get("resolved_product_id"),
            "status": item["status"],
        },
    )
    save_single_repository_record(
        write_store,
        "save_pending_attribution_item_record",
        item,
        audit_event=audit_event,
    )
    return item
