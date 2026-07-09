from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, api_error, require_permissions, store
from app.core.repositories.authorization import (
    PRODUCT_MEMBER_ROLE_LABELS,
    PRODUCT_MEMBER_ROLES,
)
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
    product_related_record_counts,
    record_audit_event,
    save_product_config_record,
)
from app.services.product_listing import PRODUCT_STATUSES, list_products_response
from app.services.product_scope import product_scope_filter, user_can_read_product

router = APIRouter(prefix="/api/products", tags=["products"])
PRODUCT_READ_PERMISSION = "product.read"
PRODUCT_MANAGE_PERMISSION = "product.manage"
PRODUCT_MEMBER_READ_PERMISSION = "product.member.read"
PRODUCT_MEMBER_MANAGE_PERMISSION = "product.member.manage"


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


class ProductMemberRequest(BaseModel):
    user_id: str
    member_role: str
    scope_type: str = "product"
    scope_id: str | None = None


class ProductMembersReplaceRequest(BaseModel):
    members: list[ProductMemberRequest] = Field(default_factory=list)


def _ensure_product_scope(user: dict[str, Any], product_id: Any) -> None:
    if not user_can_read_product(user, product_id):
        raise api_error(404, "NOT_FOUND", "Product not found")


def _ensure_global_product_scope(user: dict[str, Any]) -> None:
    if product_scope_filter(user) is not None:
        raise api_error(403, "FORBIDDEN", "Global product scope required")


def _authorization_repository(request: Request) -> Any:
    repository = getattr(request.app.state, "authorization_repository", None)
    if repository is None:
        raise api_error(500, "AUTHORIZATION_REPOSITORY_MISSING", "Authorization repository missing")
    return repository


def _users_by_id(request: Request) -> dict[str, dict[str, Any]]:
    list_users = getattr(request.app.state.user_repository, "list_users", None)
    if not callable(list_users):
        return {}
    return {
        str(item.get("id")): dict(item)
        for item in list_users()
        if item.get("id") is not None
    }


def _active_member_candidates(request: Request) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for user in _users_by_id(request).values():
        if user.get("status", "active") != "active":
            continue
        candidates.append(
            {
                "display_name": user.get("display_name") or user.get("username") or user["id"],
                "id": user["id"],
                "roles": list(user.get("roles") or []),
                "status": user.get("status", "active"),
                "username": user.get("username") or user["id"],
            }
        )
    return sorted(candidates, key=lambda item: (item["display_name"], item["username"], item["id"]))


def _normalize_member_payloads(
    *,
    payload: ProductMembersReplaceRequest,
    product_id: str,
    request: Request,
) -> list[dict[str, Any]]:
    users_by_id = _users_by_id(request)
    normalized_members: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for member in payload.members:
        user_id = member.user_id.strip()
        member_role = member.member_role.strip()
        scope_type = member.scope_type.strip() or "product"
        scope_id = (member.scope_id or "*").strip() or "*"
        if not user_id or user_id not in users_by_id:
            raise api_error(400, "PRODUCT_MEMBER_USER_NOT_FOUND", "Product member user not found")
        if users_by_id[user_id].get("status", "active") != "active":
            raise api_error(400, "PRODUCT_MEMBER_USER_INACTIVE", "Product member user is inactive")
        if member_role not in PRODUCT_MEMBER_ROLES:
            raise api_error(
                400,
                "UNSUPPORTED_PRODUCT_MEMBER_ROLE",
                "Unsupported product member role",
            )
        if scope_type != "product" or scope_id not in {"*", product_id}:
            raise api_error(
                400,
                "UNSUPPORTED_PRODUCT_MEMBER_SCOPE",
                "Unsupported product member scope",
            )
        key = (user_id, member_role, scope_type, scope_id)
        if key in seen:
            continue
        seen.add(key)
        normalized_members.append(
            {
                "member_role": member_role,
                "product_id": product_id,
                "scope_id": scope_id,
                "scope_type": scope_type,
                "status": "active",
                "user_id": user_id,
            }
        )
    return normalized_members


def _enrich_product_members(
    *,
    members: list[dict[str, Any]],
    request: Request,
) -> list[dict[str, Any]]:
    users_by_id = _users_by_id(request)
    enriched: list[dict[str, Any]] = []
    for member in members:
        user = users_by_id.get(str(member.get("user_id") or "")) or {}
        member_role = str(member.get("member_role") or "")
        scope_id = str(member.get("scope_id") or "*")
        scope_type = str(member.get("scope_type") or "product")
        enriched.append(
            {
                "created_at": member.get("created_at"),
                "display_name": user.get("display_name")
                or user.get("username")
                or member.get("user_id"),
                "id": ":".join(
                    [
                        str(member.get("product_id") or ""),
                        str(member.get("user_id") or ""),
                        member_role,
                        scope_type,
                        scope_id,
                    ]
                ),
                "member_role": member_role,
                "member_role_label": PRODUCT_MEMBER_ROLE_LABELS.get(member_role, member_role),
                "product_id": member.get("product_id"),
                "scope_id": scope_id,
                "scope_label": "整个产品" if scope_id == "*" else scope_id,
                "scope_type": scope_type,
                "status": member.get("status", "active"),
                "updated_at": member.get("updated_at"),
                "user_id": member.get("user_id"),
                "username": user.get("username") or member.get("user_id"),
            }
        )
    return enriched


def _product_member_role_options() -> list[dict[str, str]]:
    return [
        {"label": label, "value": role}
        for role, label in PRODUCT_MEMBER_ROLE_LABELS.items()
    ]


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
    require_permissions(user, {PRODUCT_READ_PERMISSION})
    return list_products_response(
        active_only=active_only,
        code=code,
        current_store=store(request),
        name=name,
        owner_team=owner_team,
        page=page,
        page_size=page_size,
        product_scope_ids=product_scope_filter(user),
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
    require_permissions(user, {PRODUCT_MANAGE_PERMISSION})
    _ensure_global_product_scope(user)
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


@router.get("/{product_id}/members")
def list_product_members(
    product_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {PRODUCT_MEMBER_READ_PERMISSION})
    _ensure_product_scope(user, product_id)
    if get_product_record(store(request), product_id) is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    members = _authorization_repository(request).list_product_members(product_id)
    enriched = _enrich_product_members(members=members, request=request)
    return envelope(
        {
            "items": enriched,
            "role_options": _product_member_role_options(),
            "total": len(enriched),
        },
        get_trace_id(request),
    )


@router.put("/{product_id}/members")
def replace_product_members(
    product_id: str,
    request: Request,
    payload: ProductMembersReplaceRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {PRODUCT_MEMBER_MANAGE_PERMISSION})
    _ensure_product_scope(user, product_id)
    if get_product_record(store(request), product_id) is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    members = _normalize_member_payloads(
        payload=payload,
        product_id=product_id,
        request=request,
    )
    result = _authorization_repository(request).set_product_members(
        product_id,
        members,
        actor_id=str(user["id"]),
        trace_id=get_trace_id(request),
    )
    enriched = _enrich_product_members(
        members=list(result.get("items") or []),
        request=request,
    )
    return envelope(
        {
            "items": enriched,
            "role_options": _product_member_role_options(),
            "total": len(enriched),
        },
        get_trace_id(request),
    )


@router.get("/{product_id}/member-candidates")
def list_product_member_candidates(
    product_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {PRODUCT_MEMBER_MANAGE_PERMISSION})
    _ensure_product_scope(user, product_id)
    if get_product_record(store(request), product_id) is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    candidates = _active_member_candidates(request)
    return envelope(
        {
            "items": candidates,
            "role_options": _product_member_role_options(),
            "total": len(candidates),
        },
        get_trace_id(request),
    )


@router.get("/{product_id}")
def get_product(
    product_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {PRODUCT_READ_PERMISSION})
    _ensure_product_scope(user, product_id)
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
    require_permissions(user, {PRODUCT_MANAGE_PERMISSION})
    _ensure_product_scope(user, product_id)
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
    require_permissions(user, {PRODUCT_MANAGE_PERMISSION})
    _ensure_product_scope(user, product_id)
    current_store = product_config_write_store(store(request))
    if get_product_record(current_store, product_id) is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product_has_related_records(current_store, product_id):
        related_counts = product_related_record_counts(current_store, product_id)
        raise api_error(
            409,
            "RESOURCE_IN_USE",
            "Product still has related records",
            extra={
                "related_counts": related_counts,
                "related_total": sum(related_counts.values()),
            },
        )
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
