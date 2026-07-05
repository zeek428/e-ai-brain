from __future__ import annotations

from typing import Any

from fastapi import Request

from app.api.deps import api_error

AUTHORIZATION_MANAGER_PERMISSIONS = {"system.roles.manage", "system.users.manage"}
SYSTEM_ADMIN_PERMISSION = "system.admin"


def authorization_repository_from_request(request: Request) -> Any | None:
    repository = getattr(request.app.state, "authorization_repository", None)
    if repository is not None:
        return repository
    store_repository = getattr(getattr(request.app.state, "store", None), "repository", None)
    if store_repository is None:
        return None
    for attribute_name in ("authorization_repository", "authorization"):
        candidate = getattr(store_repository, attribute_name, None)
        if candidate is not None:
            return candidate
    return None


def ensure_authorization_managers_remain(
    request: Request,
    *,
    deleted_user_id: str | None = None,
    role_permission_overrides: dict[str, set[str]] | None = None,
    role_status_overrides: dict[str, str] | None = None,
    user_role_overrides: dict[str, list[str]] | None = None,
    user_status_overrides: dict[str, str] | None = None,
) -> None:
    authorization_repository = authorization_repository_from_request(request)
    if authorization_repository is None:
        return

    user_repository = request.app.state.user_repository
    users = user_repository.list_users()
    roles_by_code = {
        str(role.get("code")): role
        for role in authorization_repository.list_roles()
        if role.get("code")
    }
    role_permission_overrides = role_permission_overrides or {}
    role_status_overrides = role_status_overrides or {}
    user_role_overrides = user_role_overrides or {}
    user_status_overrides = user_status_overrides or {}

    active_admin_users = 0
    active_authorization_managers = 0
    for user in users:
        user_id = str(user.get("id") or "")
        if not user_id or user_id == deleted_user_id:
            continue
        status = user_status_overrides.get(user_id, str(user.get("status") or "active"))
        if status != "active":
            continue
        if user_id in user_role_overrides:
            role_codes = list(dict.fromkeys(user_role_overrides[user_id]))
        else:
            role_codes = _effective_role_codes(authorization_repository, user)
        active_roles, permissions = _permissions_for_roles(
            role_codes,
            roles_by_code,
            role_permission_overrides=role_permission_overrides,
            role_status_overrides=role_status_overrides,
        )
        if "admin" in active_roles:
            active_admin_users += 1
        if _has_authorization_manager_access(active_roles, permissions):
            active_authorization_managers += 1

    if active_admin_users == 0:
        raise api_error(
            409,
            "LAST_ADMIN_PROTECTED",
            "At least one active admin user is required",
        )
    if active_authorization_managers == 0:
        raise api_error(
            409,
            "LAST_AUTHORIZATION_MANAGER_PROTECTED",
            "At least one active user or role manager is required",
        )


def _effective_role_codes(authorization_repository: Any, user: dict[str, Any]) -> list[str]:
    effective_permissions_for_user = getattr(
        authorization_repository,
        "effective_permissions_for_user",
        None,
    )
    if callable(effective_permissions_for_user):
        return list(effective_permissions_for_user(user).get("role_codes") or [])
    return list(user.get("roles") or [])


def _permissions_for_roles(
    role_codes: list[str],
    roles_by_code: dict[str, dict[str, Any]],
    *,
    role_permission_overrides: dict[str, set[str]],
    role_status_overrides: dict[str, str],
) -> tuple[set[str], set[str]]:
    active_roles: set[str] = set()
    permissions: set[str] = set()
    for role_code in role_codes:
        role = roles_by_code.get(role_code)
        if role is None:
            continue
        status = role_status_overrides.get(role_code, str(role.get("status") or "active"))
        if status != "active":
            continue
        active_roles.add(role_code)
        if role_code == "admin":
            permissions.update(AUTHORIZATION_MANAGER_PERMISSIONS)
            permissions.add(SYSTEM_ADMIN_PERMISSION)
            continue
        if role_code in role_permission_overrides:
            permissions.update(role_permission_overrides[role_code])
        else:
            permissions.update(
                str(permission_code)
                for permission_code in role.get("permission_codes") or []
            )
    return active_roles, permissions


def _has_authorization_manager_access(active_roles: set[str], permissions: set[str]) -> bool:
    return (
        "admin" in active_roles
        or SYSTEM_ADMIN_PERMISSION in permissions
        or bool(AUTHORIZATION_MANAGER_PERMISSIONS.intersection(permissions))
    )
