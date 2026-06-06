from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error, require_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.product_config_context import (
    delete_product_config_record,
    ensure_enum,
    ensure_non_blank,
    ensure_unique_value,
    payload_updates,
    product_config_write_store,
    record_audit_event,
    save_product_config_record,
    uses_repository_context,
)
from app.services.related_system_listing import list_related_systems_response

router = APIRouter(tags=["related_systems"])

RELATED_SYSTEM_STATUSES = {"active", "inactive"}


class RelatedSystemRequest(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    owner_team: str | None = None
    product_id: str | None = None
    status: str = "active"
    display_order: int = 0


class RelatedSystemPatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    owner_team: str | None = None
    product_id: str | None = None
    status: str | None = None
    display_order: int | None = None


@router.get("/api/system/related-systems")
def list_related_systems(
    request: Request,
    active_only: bool = False,
    product_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    return list_related_systems_response(
        active_only=active_only,
        current_store=current_store,
        product_id=product_id,
        trace_id=get_trace_id(request),
    )


@router.post("/api/system/related-systems")
def create_related_system(
    request: Request,
    payload: RelatedSystemRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    name = ensure_non_blank(payload.name, "name")
    ensure_enum(payload.status, RELATED_SYSTEM_STATUSES, "related system status")
    if payload.product_id is not None and payload.product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    system_id = current_store.new_id("system")
    code = ensure_non_blank(payload.code or system_id, "code")
    ensure_unique_value(
        current_store.related_systems,
        field="code",
        value=code,
        conflict_code="RELATED_SYSTEM_CODE_EXISTS",
        message="Related system code already exists",
    )
    related_system = {
        "id": system_id,
        "code": code,
        "name": name,
        "description": payload.description,
        "owner_team": payload.owner_team,
        "product_id": payload.product_id,
        "status": payload.status,
        "display_order": payload.display_order,
    }
    if not uses_repository_context(current_store):
        current_store.related_systems[system_id] = related_system
    audit_event = record_audit_event(
        current_store,
        event_type="related_system.created",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    save_product_config_record(
        current_store,
        "related_systems",
        related_system,
        audit_event=audit_event,
    )
    return envelope(related_system, get_trace_id(request))


@router.patch("/api/system/related-systems/{system_id}")
def patch_related_system(
    system_id: str,
    request: Request,
    payload: RelatedSystemPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    related_system = current_store.related_systems.get(system_id)
    if related_system is None:
        raise api_error(404, "NOT_FOUND", "Related system not found")
    updates = payload_updates(payload)
    if "name" in updates:
        updates["name"] = ensure_non_blank(updates["name"], "name")
    if "code" in updates:
        updates["code"] = ensure_non_blank(updates["code"], "code")
        ensure_unique_value(
            current_store.related_systems,
            field="code",
            value=updates["code"],
            conflict_code="RELATED_SYSTEM_CODE_EXISTS",
            message="Related system code already exists",
            exclude_id=system_id,
        )
    if "status" in updates:
        ensure_enum(updates["status"], RELATED_SYSTEM_STATUSES, "related system status")
    if "product_id" in updates and updates["product_id"] is not None:
        if updates["product_id"] not in current_store.products:
            raise api_error(404, "NOT_FOUND", "Product not found")
    related_system = {**related_system, **updates}
    if not uses_repository_context(current_store):
        current_store.related_systems[system_id] = related_system
    audit_event = record_audit_event(
        current_store,
        event_type="related_system.updated",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    save_product_config_record(
        current_store,
        "related_systems",
        related_system,
        audit_event=audit_event,
    )
    return envelope(related_system, get_trace_id(request))


@router.delete("/api/system/related-systems/{system_id}")
def delete_related_system(
    system_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    if system_id not in current_store.related_systems:
        raise api_error(404, "NOT_FOUND", "Related system not found")
    if not uses_repository_context(current_store):
        del current_store.related_systems[system_id]
    audit_event = record_audit_event(
        current_store,
        event_type="related_system.deleted",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    delete_product_config_record(
        current_store,
        "related_systems",
        system_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": system_id}, get_trace_id(request))
