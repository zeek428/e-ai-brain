from __future__ import annotations

from typing import Any

from fastapi import Depends, Header, HTTPException, Request

from app.core.config import get_settings
from app.core.security import TokenError, parse_access_token
from app.core.store import MemoryStore

settings = get_settings()


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def store(request: Request) -> MemoryStore:
    return request.app.state.store


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise api_error(401, "UNAUTHORIZED", "Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = parse_access_token(token, secret_key=settings.app_secret_key)
    except TokenError as exc:
        code = "TOKEN_EXPIRED" if str(exc) == "token_expired" else "UNAUTHORIZED"
        raise api_error(401, code, "Invalid bearer token") from exc

    user = request.app.state.user_repository.get_by_username(str(payload.get("username", "")))
    if user is None:
        raise api_error(401, "UNAUTHORIZED", "User is inactive or missing")
    authorization_repository = getattr(request.app.state, "authorization_repository", None)
    snapshot_method = getattr(authorization_repository, "snapshot_for_user", None)
    if snapshot_method is None:
        snapshot_method = getattr(authorization_repository, "get_snapshot_for_user", None)
    if snapshot_method is None:
        return user
    snapshot = snapshot_method(user)
    enriched_user = dict(user)
    enriched_user["permissions"] = sorted(snapshot.permissions)
    enriched_user["scope_summary"] = snapshot.scopes
    return enriched_user


CurrentUser = Depends(get_current_user)


def require_roles(user: dict[str, Any], allowed_roles: set[str]) -> None:
    user_roles = set(user["roles"])
    if "admin" in user_roles or user_roles.intersection(allowed_roles):
        return
    raise api_error(403, "FORBIDDEN", "Role permission denied")


def require_permissions(user: dict[str, Any], required_permissions: set[str]) -> None:
    user_permissions = set(user.get("permissions") or [])
    legacy_roles = set(user.get("roles") or [])
    if (
        "admin" in legacy_roles
        or "system.admin" in user_permissions
        or required_permissions.issubset(user_permissions)
    ):
        return
    raise api_error(403, "FORBIDDEN", "Permission denied")


def require_any_permission(user: dict[str, Any], required_permissions: set[str]) -> None:
    user_permissions = set(user.get("permissions") or [])
    legacy_roles = set(user.get("roles") or [])
    if (
        "admin" in legacy_roles
        or "system.admin" in user_permissions
        or user_permissions.intersection(required_permissions)
    ):
        return
    raise api_error(403, "FORBIDDEN", "Permission denied")
