from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error
from app.core.config import get_settings
from app.core.listing import (
    ensure_list_enum,
    list_payload,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.roles import list_role_definitions
from app.core.security import create_access_token, verify_password
from app.core.trace import envelope, get_trace_id
from app.core.users import SEEDED_USERS

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])
ROLE_CATEGORIES = {"delivery", "knowledge", "readonly", "review", "system", "workspace"}
ROLE_LIST_SORT_FIELDS = {"category", "code", "name", "sort_order", "status"}
ROLE_STATUSES = {"active", "inactive"}


class LoginRequest(BaseModel):
    username: str
    password: str


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "roles": user["roles"],
    }


def _seeded_users_enabled() -> bool:
    return settings.allow_seeded_users or settings.app_env in {"local", "test", "development"}


@router.post("/login")
def login(request: Request, payload: LoginRequest) -> dict[str, Any]:
    if payload.username in SEEDED_USERS and not _seeded_users_enabled():
        raise api_error(
            403,
            "DEFAULT_CREDENTIALS_DISABLED",
            "Seeded local users are disabled outside local environments",
        )
    user = request.app.state.user_repository.get_by_username(payload.username)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise api_error(401, "INVALID_CREDENTIALS", "Invalid username or password")

    access_token = create_access_token(
        {"sub": user["id"], "username": user["username"], "roles": user["roles"]},
        secret_key=settings.app_secret_key,
        expires_in_seconds=settings.access_token_expire_seconds,
    )
    return envelope(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_seconds,
            "user": _public_user(user),
        },
        get_trace_id(request),
    )


@router.get("/me")
def me(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    return envelope(_public_user(user), get_trace_id(request))


@router.post("/logout")
def logout(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    return envelope({"success": True}, get_trace_id(request))


@router.get("/roles")
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
    items = [
        item
        for item in list_role_definitions()
        if list_text_matches(item, role, ("code", "name", "description"))
        and list_text_matches(item, business_role, ("business_roles",))
        and list_text_matches(item, menu_scope, ("menu_scope",))
        and list_text_matches(item, permission, ("permissions",))
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
    if page is None and page_size is None:
        return list_payload(sorted_items, trace_id=get_trace_id(request))
    return paginated_list_payload(
        sorted_items,
        filters=filters,
        list_name="roles",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=get_trace_id(request),
    )
