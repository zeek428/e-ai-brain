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
    get_product_module_record,
    list_product_module_records,
    payload_updates,
    product_config_record_write_store,
    product_config_write_store,
    record_audit_event,
    save_product_config_record,
    uses_repository_context,
)
from app.services.product_module_listing import list_product_modules_response

router = APIRouter(tags=["product_modules"])

MODULE_STATUSES = {"active", "inactive"}


class ProductModuleRequest(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    owner_team: str | None = None
    status: str = "active"
    display_order: int = 0


class ProductModulePatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    owner_team: str | None = None
    status: str | None = None
    display_order: int | None = None


@router.get("/api/products/{product_id}/modules")
def list_product_modules(
    product_id: str,
    request: Request,
    active_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return list_product_modules_response(
        active_only=active_only,
        current_store=store(request),
        product_id=product_id,
        trace_id=get_trace_id(request),
    )


@router.post("/api/products/{product_id}/modules")
def create_product_module(
    product_id: str,
    request: Request,
    payload: ProductModuleRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    name = ensure_non_blank(payload.name, "name")
    ensure_enum(payload.status, MODULE_STATUSES, "product module status")
    module_id = current_store.new_id("module")
    code = ensure_non_blank(payload.code or module_id, "code")
    ensure_unique_value(
        current_store.product_modules,
        field="code",
        value=code,
        conflict_code="PRODUCT_MODULE_CODE_EXISTS",
        message="Product module code already exists",
        scope={"product_id": product_id},
    )
    module = {
        "id": module_id,
        "product_id": product_id,
        "code": code,
        "name": name,
        "description": payload.description,
        "owner_team": payload.owner_team,
        "status": payload.status,
        "display_order": payload.display_order,
    }
    if not uses_repository_context(current_store):
        current_store.product_modules[module_id] = module
    audit_event = record_audit_event(
        current_store,
        event_type="product_module.created",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
    )
    save_product_config_record(
        current_store,
        "product_modules",
        module,
        audit_event=audit_event,
    )
    return envelope(module, get_trace_id(request))


@router.patch("/api/product-modules/{module_id}")
def patch_product_module(
    module_id: str,
    request: Request,
    payload: ProductModulePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_record_write_store(store(request))
    module = get_product_module_record(current_store, module_id)
    if module is None:
        raise api_error(404, "NOT_FOUND", "Product module not found")
    updates = payload_updates(payload)
    if "name" in updates:
        updates["name"] = ensure_non_blank(updates["name"], "name")
    if "code" in updates:
        updates["code"] = ensure_non_blank(updates["code"], "code")
        modules_for_product = {
            str(item["id"]): dict(item)
            for item in list_product_module_records(
                current_store,
                str(module["product_id"]),
                active_only=False,
            )
            if item.get("id") is not None
        }
        ensure_unique_value(
            modules_for_product,
            field="code",
            value=updates["code"],
            conflict_code="PRODUCT_MODULE_CODE_EXISTS",
            message="Product module code already exists",
            exclude_id=module_id,
            scope={"product_id": module["product_id"]},
        )
    if "status" in updates:
        ensure_enum(updates["status"], MODULE_STATUSES, "product module status")
    module = {**module, **updates}
    if not uses_repository_context(current_store):
        current_store.product_modules[module_id] = module
    audit_event = record_audit_event(
        current_store,
        event_type="product_module.updated",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
    )
    save_product_config_record(
        current_store,
        "product_modules",
        module,
        audit_event=audit_event,
    )
    return envelope(module, get_trace_id(request))


@router.delete("/api/product-modules/{module_id}")
def delete_product_module(
    module_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    module = current_store.product_modules.get(module_id)
    if module is None:
        raise api_error(404, "NOT_FOUND", "Product module not found")
    if any(
        item["product_id"] == module["product_id"]
        and item.get("module_code") == module["code"]
        for item in [
            *current_store.requirements.values(),
            *current_store.ai_tasks.values(),
            *current_store.bugs.values(),
        ]
    ):
        raise api_error(409, "RESOURCE_IN_USE", "Product module still has related records")
    if not uses_repository_context(current_store):
        del current_store.product_modules[module_id]
    audit_event = record_audit_event(
        current_store,
        event_type="product_module.deleted",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
    )
    delete_product_config_record(
        current_store,
        "product_modules",
        module_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": module_id}, get_trace_id(request))
