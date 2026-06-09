from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error
from app.core.authorization import AuthorizationSnapshot, build_menu_tree
from app.core.config import get_settings
from app.core.listing import (
    ensure_list_enum,
    list_payload,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.repositories.authorization import CompatibilityAuthorizationRepository
from app.core.roles import list_role_definitions
from app.core.security import create_access_token, verify_password
from app.core.trace import envelope, get_trace_id
from app.core.users import SEEDED_USERS

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])
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


def _candidate_authorization_repositories(request: Request) -> list[Any]:
    repositories: list[Any] = []
    state_repository = getattr(request.app.state, "authorization_repository", None)
    if state_repository is not None:
        repositories.append(state_repository)

    store_repository = getattr(getattr(request.app.state, "store", None), "repository", None)
    if store_repository is not None:
        for attribute_name in (
            "authorization_repository",
            "authorization",
            "auth",
        ):
            repository = getattr(store_repository, attribute_name, None)
            if repository is not None:
                repositories.append(repository)

    repositories.append(CompatibilityAuthorizationRepository())
    return repositories


def _snapshot_from_repository(
    repository: Any,
    user: dict[str, Any],
) -> AuthorizationSnapshot:
    for method_name in ("get_snapshot_for_user", "snapshot_for_user"):
        method = getattr(repository, method_name, None)
        if method is not None:
            return method(user)
    raise AttributeError("authorization repository has no snapshot method")


def _authorization_context(
    request: Request,
    user: dict[str, Any],
) -> tuple[Any, AuthorizationSnapshot]:
    for repository in _candidate_authorization_repositories(request):
        try:
            return repository, _snapshot_from_repository(repository, user)
        except AttributeError:
            continue
    fallback = CompatibilityAuthorizationRepository()
    return fallback, fallback.snapshot_for_user(user)


def _repository_menu_resources(repository: Any) -> list[dict[str, Any]]:
    method = getattr(repository, "menu_resources", None)
    if method is None:
        return CompatibilityAuthorizationRepository().menu_resources()
    return method()


def _repository_granted_menu_codes(
    repository: Any,
    snapshot: AuthorizationSnapshot,
) -> set[str]:
    method = getattr(repository, "granted_menu_codes_for_roles", None)
    if method is not None:
        return set(method(snapshot.roles))
    return {menu["code"] for menu in snapshot.menus if menu.get("code")}


def _route_permissions(resources: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        resource["path"]: sorted(resource.get("required_permissions") or [])
        for resource in resources
        if resource.get("status", "active") == "active"
        and resource.get("menu_type") == "hidden_page"
        and resource.get("path")
        and resource.get("required_permissions")
    }


def _authorized_user(request: Request, user: dict[str, Any]) -> dict[str, Any]:
    repository, snapshot = _authorization_context(request, user)
    resources = _repository_menu_resources(repository)
    payload = _public_user(user)
    payload.update(
        {
            "permissions": sorted(snapshot.permissions),
            "scope_summary": snapshot.scopes,
            "menu_tree": build_menu_tree(
                granted_codes=_repository_granted_menu_codes(repository, snapshot),
                resources=resources,
                permissions=snapshot.permissions,
            ),
            "route_permissions": _route_permissions(resources),
        }
    )
    return payload


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
    return envelope(_authorized_user(request, user), get_trace_id(request))


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
