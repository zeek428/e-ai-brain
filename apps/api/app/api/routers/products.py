from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error, require_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.product_config_context import (
    delete_product_config_record,
    ensure_enum,
    ensure_non_blank,
    ensure_unique_value,
    get_product_record,
    list_product_child_config_records,
    list_product_records,
    payload_updates,
    product_config_write_store,
    product_has_related_records,
    record_audit_event,
    save_product_config_record,
)
from app.services.product_listing import PRODUCT_STATUSES, list_products_response

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductRequest(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    owner_team: str | None = None
    status: str = "active"
    display_order: int = 0


class ProductPatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    owner_team: str | None = None
    status: str | None = None
    display_order: int | None = None


@router.get("")
def list_products(
    request: Request,
    active_only: bool = False,
    code: str | None = None,
    name: str | None = None,
    owner_team: str | None = None,
    status: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "asc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return list_products_response(
        active_only=active_only,
        code=code,
        current_store=store(request),
        name=name,
        owner_team=owner_team,
        page=page,
        page_size=page_size,
        request=request,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
    )


@router.post("")
def create_product(
    request: Request,
    payload: ProductRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    name = ensure_non_blank(payload.name, "name")
    ensure_enum(payload.status, PRODUCT_STATUSES, "product status")
    product_id = current_store.new_id("product")
    code = ensure_non_blank(payload.code or product_id, "code")
    products_by_id = {
        str(product["id"]): dict(product)
        for product in list_product_records(current_store, active_only=False)
        if product.get("id") is not None
    }
    ensure_unique_value(
        products_by_id,
        field="code",
        value=code,
        conflict_code="PRODUCT_CODE_EXISTS",
        message="Product code already exists",
    )
    product = {
        "id": product_id,
        "code": code,
        "name": name,
        "description": payload.description,
        "owner_team": payload.owner_team,
        "status": payload.status,
        "display_order": payload.display_order,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="product.created",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    save_product_config_record(
        current_store,
        "products",
        product,
        audit_event=audit_event,
    )
    return envelope(product, get_trace_id(request))


@router.get("/{product_id}")
def get_product(
    product_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    product = get_product_record(current_store, product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    return envelope(product, get_trace_id(request))


@router.patch("/{product_id}")
def patch_product(
    product_id: str,
    request: Request,
    payload: ProductPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    product = get_product_record(current_store, product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    updates = payload_updates(payload)
    if "name" in updates:
        updates["name"] = ensure_non_blank(updates["name"], "name")
    if "code" in updates:
        updates["code"] = ensure_non_blank(updates["code"], "code")
        products_by_id = {
            str(item["id"]): dict(item)
            for item in list_product_records(current_store, active_only=False)
            if item.get("id") is not None
        }
        ensure_unique_value(
            products_by_id,
            field="code",
            value=updates["code"],
            conflict_code="PRODUCT_CODE_EXISTS",
            message="Product code already exists",
            exclude_id=product_id,
        )
    if "status" in updates:
        ensure_enum(updates["status"], PRODUCT_STATUSES, "product status")
    product = {**product, **updates}
    audit_event = record_audit_event(
        current_store,
        event_type="product.updated",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    save_product_config_record(
        current_store,
        "products",
        product,
        audit_event=audit_event,
    )
    return envelope(product, get_trace_id(request))


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner"})
    current_store = product_config_write_store(store(request))
    if get_product_record(current_store, product_id) is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product_has_related_records(current_store, product_id):
        raise api_error(409, "RESOURCE_IN_USE", "Product still has related records")
    for collection_name in [
        "product_versions",
        "product_modules",
        "product_git_repositories",
        "related_systems",
    ]:
        for item in list_product_child_config_records(current_store, collection_name, product_id):
            delete_product_config_record(current_store, collection_name, str(item["id"]))
    audit_event = record_audit_event(
        current_store,
        event_type="product.deleted",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    delete_product_config_record(
        current_store,
        "products",
        product_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": product_id}, get_trace_id(request))
