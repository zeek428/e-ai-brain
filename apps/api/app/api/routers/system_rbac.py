from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, api_error, require_any_permission, require_permissions
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.trace import envelope, get_trace_id
from app.services.rbac_matrix import build_rbac_policy_matrix, build_user_permission_diagnostic

router = APIRouter(tags=["system-rbac"])
ROLE_CATEGORIES = {
    "delivery",
    "knowledge",
    "readonly",
    "release",
    "review",
    "system",
    "testing",
    "workspace",
}
ROLE_LIST_SORT_FIELDS = {"category", "code", "name", "sort_order", "status"}
ROLE_STATUSES = {"active", "inactive"}
MENU_LIST_SORT_FIELDS = {
    "code",
    "menu_type",
    "name",
    "parent_code",
    "path",
    "sort_order",
    "status",
}
MENU_RESOURCE_STATUSES = {"active", "inactive"}
MENU_RESOURCE_TYPES = {"group", "hidden_page", "page"}


class RoleCreateRequest(BaseModel):
    code: str
    name: str
    description: str = ""
    category: str = "workspace"
    is_assignable: bool = True
    sort_order: int | None = None


class RoleCopyRequest(BaseModel):
    code: str
    name: str | None = None
    description: str | None = None


class RolePatchRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    is_assignable: bool | None = None
    sort_order: int | None = None


class RolePermissionGrantRequest(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)


class RoleMenuGrantRequest(BaseModel):
    menu_codes: list[str] = Field(default_factory=list)


class MenuResourceRequest(BaseModel):
    code: str
    name: str
    path: str = ""
    parent_code: str | None = None
    menu_type: str = "page"
    icon: str = ""
    sort_order: int = 0
    required_permissions: list[str] = Field(default_factory=list)
    status: str = "active"


class MenuResourcePatchRequest(BaseModel):
    name: str | None = None
    path: str | None = None
    parent_code: str | None = None
    menu_type: str | None = None
    icon: str | None = None
    sort_order: int | None = None
    required_permissions: list[str] | None = None
    status: str | None = None


class MenuReorderItem(BaseModel):
    code: str
    sort_order: int


class MenuReorderRequest(BaseModel):
    items: list[MenuReorderItem] = Field(default_factory=list)


class ScopeGrant(BaseModel):
    scope_type: str
    scope_id: str
    access_level: str = "read"


class ScopeGrantRequest(BaseModel):
    scopes: list[ScopeGrant] = Field(default_factory=list)


class UserRoleGrantRequest(BaseModel):
    role_codes: list[str] = Field(default_factory=list)


def _authorization_repository(request: Request) -> Any:
    return request.app.state.authorization_repository


def _find_user(request: Request, user_id: str) -> dict[str, Any] | None:
    return next(
        (user for user in request.app.state.user_repository.list_users() if user["id"] == user_id),
        None,
    )


def _non_blank(value: str, field: str) -> str:
    if not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def _unique_codes(codes: list[str], field: str) -> list[str]:
    normalized = [_non_blank(code, field) for code in codes]
    if len(set(normalized)) != len(normalized):
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be unique")
    return normalized


def _menu_payload(payload: MenuResourceRequest | MenuResourcePatchRequest) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True)
    if "code" in values and values["code"] is not None:
        values["code"] = _non_blank(values["code"], "code")
    if "name" in values and values["name"] is not None:
        values["name"] = _non_blank(values["name"], "name")
    for field in ("icon", "menu_type", "parent_code", "path", "status"):
        if field in values and values[field] is not None:
            values[field] = values[field].strip()
            if field == "parent_code" and not values[field]:
                values[field] = None
    if "required_permissions" in values and values["required_permissions"] is not None:
        values["required_permissions"] = _unique_codes(
            values["required_permissions"],
            "required_permissions",
        )
    return values


def _map_repository_error(exc: ValueError) -> None:
    code = str(exc)
    status_code = (
        409
        if code in {
            "MENU_CODE_EXISTS",
            "MENU_HAS_CHILDREN",
            "ROLE_CODE_EXISTS",
            "SYSTEM_MENU_PROTECTED",
            "SYSTEM_ROLE_PROTECTED",
        }
        else 400
    )
    messages = {
        "MENU_CODE_EXISTS": "Menu code already exists",
        "MENU_HAS_CHILDREN": "Menu has child resources",
        "MENU_PARENT_NOT_FOUND": "Parent menu not found",
        "ROLE_CODE_EXISTS": "Role code already exists",
        "SYSTEM_MENU_PROTECTED": "System menu cannot be deleted",
        "SYSTEM_ROLE_PROTECTED": "System role cannot be disabled",
        "UNSUPPORTED_MENU_STATUS": "Unsupported menu status",
        "UNSUPPORTED_MENU_TYPE": "Unsupported menu type",
        "UNSUPPORTED_PERMISSION": "Unsupported permission code",
        "UNSUPPORTED_MENU": "Unsupported menu code",
        "INVALID_SCOPE": "Invalid scope grant",
        "UNSUPPORTED_ROLE": "Unsupported role code",
    }
    raise api_error(status_code, code, messages.get(code, code))


@router.get("/api/system/permissions")
def list_permissions(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    return envelope(
        {"items": _authorization_repository(request).list_permissions()},
        get_trace_id(request),
    )


@router.get("/api/system/permissions/matrix")
def get_permission_matrix(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission(user, {"system.roles.read", "system.roles.manage"})
    return envelope(
        build_rbac_policy_matrix(_authorization_repository(request)),
        get_trace_id(request),
    )


@router.get("/api/system/permissions/diagnostics")
def get_permission_diagnostics(
    request: Request,
    user_id: str,
    path: str | None = None,
    permission_code: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission(
        user,
        {"system.roles.read", "system.roles.manage", "system.users.manage"},
    )
    target_user = _find_user(request, user_id)
    if target_user is None:
        raise api_error(404, "NOT_FOUND", "User not found")
    return envelope(
        build_user_permission_diagnostic(
            _authorization_repository(request),
            target_user,
            path=path,
            permission_code=permission_code,
            scope_type=scope_type,
            scope_id=scope_id,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/menus")
def list_menus(
    request: Request,
    menu: str | None = Query(default=None),
    menu_type: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    parent: str | None = Query(default=None),
    path: str | None = Query(default=None),
    permission: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_order: str = Query(default="asc"),
    status: str | None = Query(default=None),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission(
        user,
        {"system.menus.read", "system.menus.manage", "system.roles.manage"},
    )
    ensure_list_enum(menu_type, MENU_RESOURCE_TYPES, "menu_type")
    ensure_list_enum(status, MENU_RESOURCE_STATUSES, "status")
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_list_enum(sort_by, MENU_LIST_SORT_FIELDS, "sort_by")
    started_at = perf_counter()
    filters = {
        "menu": menu,
        "menu_type": menu_type,
        "parent": parent,
        "path": path,
        "permission": permission,
        "status": status,
    }
    repository = _authorization_repository(request)
    resolved_sort_by = sort_by or "sort_order"
    paged = page is not None or page_size is not None
    count_menu_resources = getattr(repository, "count_menu_resources", None)
    list_menu_resources_page = getattr(repository, "list_menu_resources_page", None)
    if paged and callable(count_menu_resources) and callable(list_menu_resources_page):
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        total = count_menu_resources(
            menu=menu,
            menu_type=menu_type,
            parent=parent,
            path=path,
            permission=permission,
            status=status,
        )
        items = list_menu_resources_page(
            limit=resolved_page_size,
            menu=menu,
            menu_type=menu_type,
            offset=(resolved_page - 1) * resolved_page_size,
            parent=parent,
            path=path,
            permission=permission,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            status=status,
        )
        return envelope(
            add_list_observability(
                {
                    "items": items,
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "total": int(total),
                },
                filters=filters,
                list_name="menus",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=started_at,
            ),
            get_trace_id(request),
        )
    parent_names = {
        item["code"]: item.get("name", "")
        for item in repository.menu_resources()
    }
    items = [
        item
        for item in repository.menu_resources()
        if list_text_matches(item, menu, ("code", "name"))
        and list_text_matches(
            {
                **item,
                "parent_text": " ".join(
                    str(value or "")
                    for value in (
                        item.get("parent_code"),
                        parent_names.get(str(item.get("parent_code") or ""), ""),
                    )
                ),
                "permission_text": " ".join(item.get("required_permissions") or []),
            },
            parent,
            ("parent_text",),
        )
        and list_text_matches(item, path, ("path",))
        and list_text_matches(
            {"permission_text": " ".join(item.get("required_permissions") or [])},
            permission,
            ("permission_text",),
        )
        and (not menu_type or item.get("menu_type") == menu_type)
        and (not status or item.get("status") == status)
    ]
    sorted_items = sort_list_items(
        items,
        allowed_fields=MENU_LIST_SORT_FIELDS,
        default_sort_by="sort_order",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        sorted_items,
        filters=filters,
        list_name="menus",
        observed=paged,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=get_trace_id(request),
    )


@router.post("/api/system/menus")
def create_menu(
    request: Request,
    payload: MenuResourceRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.menus.manage"})
    try:
        menu = _authorization_repository(request).create_menu_resource(
            _menu_payload(payload),
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    return envelope(menu, get_trace_id(request))


@router.put("/api/system/menus/reorder")
def reorder_menus(
    request: Request,
    payload: MenuReorderRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.menus.manage"})
    try:
        items = _authorization_repository(request).reorder_menu_resources(
            [item.model_dump() for item in payload.items],
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@router.patch("/api/system/menus/{menu_code}")
def update_menu(
    menu_code: str,
    request: Request,
    payload: MenuResourcePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.menus.manage"})
    try:
        menu = _authorization_repository(request).update_menu_resource(
            menu_code,
            _menu_payload(payload),
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if menu is None:
        raise api_error(404, "NOT_FOUND", "Menu not found")
    return envelope(menu, get_trace_id(request))


@router.delete("/api/system/menus/{menu_code}")
def delete_menu(
    menu_code: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.menus.manage"})
    try:
        deleted = _authorization_repository(request).delete_menu_resource(
            menu_code,
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if deleted is None:
        raise api_error(404, "NOT_FOUND", "Menu not found")
    return envelope({"deleted": True, "code": menu_code}, get_trace_id(request))


@router.post("/api/system/menus/{menu_code}/disable")
def disable_menu(
    menu_code: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return _set_menu_status(menu_code, request, user, "inactive")


@router.post("/api/system/menus/{menu_code}/enable")
def enable_menu(
    menu_code: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return _set_menu_status(menu_code, request, user, "active")


def _set_menu_status(
    menu_code: str,
    request: Request,
    user: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    require_permissions(user, {"system.menus.manage"})
    try:
        menu = _authorization_repository(request).set_menu_status(
            menu_code,
            status,
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if menu is None:
        raise api_error(404, "NOT_FOUND", "Menu not found")
    return envelope(menu, get_trace_id(request))


@router.get("/api/system/roles")
def list_roles(
    request: Request,
    business_role: str | None = Query(default=None),
    category: str | None = Query(default=None),
    menu_scope: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    permission: str | None = Query(default=None),
    role: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_order: str = Query(default="asc"),
    status: str | None = Query(default=None),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission(user, {"system.roles.read", "system.roles.manage"})
    ensure_list_enum(category, ROLE_CATEGORIES, "role category")
    ensure_list_enum(status, ROLE_STATUSES, "role status")
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_list_enum(sort_by, ROLE_LIST_SORT_FIELDS, "sort_by")
    started_at = perf_counter()
    filters = {
        "business_role": business_role,
        "category": category,
        "menu_scope": menu_scope,
        "permission": permission,
        "role": role,
        "status": status,
    }
    repository = _authorization_repository(request)
    count_role_summaries = getattr(repository, "count_role_summaries", None)
    list_role_summaries_page = getattr(repository, "list_role_summaries_page", None)
    resolved_sort_by = sort_by or "sort_order"
    if callable(count_role_summaries) and callable(list_role_summaries_page):
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        total = count_role_summaries(
            business_role=business_role,
            category=category,
            menu_scope=menu_scope,
            permission=permission,
            role=role,
            status=status,
        )
        items = list_role_summaries_page(
            business_role=business_role,
            category=category,
            limit=resolved_page_size,
            menu_scope=menu_scope,
            offset=(resolved_page - 1) * resolved_page_size,
            permission=permission,
            role=role,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            status=status,
        )
        return envelope(
            add_list_observability(
                {
                    "items": items,
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "total": int(total),
                },
                filters=filters,
                list_name="roles",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=started_at,
            ),
            get_trace_id(request),
        )
    items = [
        item
        for item in repository.list_roles()
        if list_text_matches(item, role, ("code", "name", "description"))
        and list_text_matches(item, business_role, ("business_roles",))
        and list_text_matches(item, menu_scope, ("menu_codes", "menu_scope"))
        and list_text_matches(item, permission, ("permission_codes", "permissions"))
        and (not category or item.get("category") == category)
        and (not status or item.get("status") == status)
    ]
    sorted_items = sort_list_items(
        items,
        allowed_fields=ROLE_LIST_SORT_FIELDS,
        default_sort_by="sort_order",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        sorted_items,
        filters=filters,
        list_name="roles",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=get_trace_id(request),
    )


@router.post("/api/system/roles")
def create_role(
    request: Request,
    payload: RoleCreateRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    create_payload = payload.model_dump()
    create_payload["code"] = _non_blank(create_payload["code"], "code")
    create_payload["name"] = _non_blank(create_payload["name"], "name")
    try:
        role = _authorization_repository(request).create_role(
            create_payload,
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    return envelope(role, get_trace_id(request))


@router.post("/api/system/roles/{role_id}/copy")
def copy_role(
    role_id: str,
    request: Request,
    payload: RoleCopyRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    copy_payload = payload.model_dump(exclude_none=True)
    copy_payload["code"] = _non_blank(copy_payload["code"], "code")
    try:
        role = _authorization_repository(request).copy_role(
            role_id,
            copy_payload,
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if role is None:
        raise api_error(404, "NOT_FOUND", "Role not found")
    return envelope(role, get_trace_id(request))


@router.get("/api/system/roles/{role_id}")
def get_role(
    role_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    role = _authorization_repository(request).get_role(role_id)
    if role is None:
        raise api_error(404, "NOT_FOUND", "Role not found")
    return envelope(role, get_trace_id(request))


@router.patch("/api/system/roles/{role_id}")
def update_role(
    role_id: str,
    request: Request,
    payload: RolePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        updates["name"] = _non_blank(updates["name"], "name")
    try:
        role = _authorization_repository(request).update_role(
            role_id,
            updates,
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if role is None:
        raise api_error(404, "NOT_FOUND", "Role not found")
    return envelope(role, get_trace_id(request))


@router.post("/api/system/roles/{role_id}/disable")
def disable_role(
    role_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return _set_role_status(role_id, request, user, "inactive")


@router.post("/api/system/roles/{role_id}/enable")
def enable_role(
    role_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return _set_role_status(role_id, request, user, "active")


def _set_role_status(
    role_id: str,
    request: Request,
    user: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    try:
        role = _authorization_repository(request).set_role_status(
            role_id,
            status,
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if role is None:
        raise api_error(404, "NOT_FOUND", "Role not found")
    return envelope(role, get_trace_id(request))


@router.put("/api/system/roles/{role_id}/permissions")
def update_role_permissions(
    role_id: str,
    request: Request,
    payload: RolePermissionGrantRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    try:
        role = _authorization_repository(request).set_role_permissions(
            role_id,
            _unique_codes(payload.permission_codes, "permission_codes"),
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if role is None:
        raise api_error(404, "NOT_FOUND", "Role not found")
    return envelope(role, get_trace_id(request))


@router.put("/api/system/roles/{role_id}/menus")
def update_role_menus(
    role_id: str,
    request: Request,
    payload: RoleMenuGrantRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    try:
        role = _authorization_repository(request).set_role_menus(
            role_id,
            _unique_codes(payload.menu_codes, "menu_codes"),
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if role is None:
        raise api_error(404, "NOT_FOUND", "Role not found")
    return envelope(role, get_trace_id(request))


@router.put("/api/system/roles/{role_id}/scopes")
def update_role_scopes(
    role_id: str,
    request: Request,
    payload: ScopeGrantRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    try:
        role = _authorization_repository(request).set_role_scopes(
            role_id,
            [scope.model_dump() for scope in payload.scopes],
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    if role is None:
        raise api_error(404, "NOT_FOUND", "Role not found")
    return envelope(role, get_trace_id(request))


@router.get("/api/users/{user_id}/permissions")
def get_user_permissions(
    user_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.users.manage"})
    target_user = _find_user(request, user_id)
    if target_user is None:
        raise api_error(404, "NOT_FOUND", "User not found")
    return envelope(
        _authorization_repository(request).effective_permissions_for_user(target_user),
        get_trace_id(request),
    )


@router.put("/api/users/{user_id}/roles")
def update_user_roles(
    user_id: str,
    request: Request,
    payload: UserRoleGrantRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.users.manage"})
    if _find_user(request, user_id) is None:
        raise api_error(404, "NOT_FOUND", "User not found")
    try:
        result = _authorization_repository(request).set_user_roles(
            user_id,
            _unique_codes(payload.role_codes, "role_codes"),
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    return envelope(result, get_trace_id(request))


@router.put("/api/users/{user_id}/scopes")
def update_user_scopes(
    user_id: str,
    request: Request,
    payload: ScopeGrantRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.users.manage"})
    if _find_user(request, user_id) is None:
        raise api_error(404, "NOT_FOUND", "User not found")
    try:
        result = _authorization_repository(request).set_user_scopes(
            user_id,
            [scope.model_dump() for scope in payload.scopes],
            actor_id=str(user["id"]),
            trace_id=get_trace_id(request),
        )
    except ValueError as exc:
        _map_repository_error(exc)
    return envelope(result, get_trace_id(request))
