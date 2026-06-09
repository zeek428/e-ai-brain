from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, api_error, require_permissions
from app.core.trace import envelope, get_trace_id

router = APIRouter(tags=["system-rbac"])


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


def _map_repository_error(exc: ValueError) -> None:
    code = str(exc)
    status_code = 409 if code in {"ROLE_CODE_EXISTS", "SYSTEM_ROLE_PROTECTED"} else 400
    messages = {
        "ROLE_CODE_EXISTS": "Role code already exists",
        "SYSTEM_ROLE_PROTECTED": "System role cannot be disabled",
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


@router.get("/api/system/menus")
def list_menus(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    return envelope(
        {"items": _authorization_repository(request).menu_resources()},
        get_trace_id(request),
    )


@router.get("/api/system/roles")
def list_roles(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.roles.manage"})
    return envelope(
        {"items": _authorization_repository(request).list_roles()},
        get_trace_id(request),
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
