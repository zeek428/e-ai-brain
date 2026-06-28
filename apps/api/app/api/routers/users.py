from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, api_error, require_permissions
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.roles import ASSIGNABLE_ROLE_CODES
from app.core.trace import envelope, get_trace_id

router = APIRouter(prefix="/api/users", tags=["users"])
USER_MANAGE_PERMISSION = "system.users.manage"
USER_STATUSES = {"active", "inactive"}
USER_LIST_SORT_FIELDS = {"created_at", "display_name", "id", "status", "username"}


class UserCreateRequest(BaseModel):
    username: str
    display_name: str
    password: str
    roles: list[str] = Field(default_factory=lambda: ["viewer"])
    status: str = "active"


class UserPatchRequest(BaseModel):
    display_name: str | None = None
    password: str | None = None
    roles: list[str] | None = None
    status: str | None = None


def _ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def _ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is not None and value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def _ensure_roles(roles: list[str]) -> None:
    if not roles:
        raise api_error(400, "VALIDATION_ERROR", "roles is required")
    if len(set(roles)) != len(roles):
        raise api_error(400, "VALIDATION_ERROR", "roles must be unique")
    invalid_roles = sorted(set(roles) - ASSIGNABLE_ROLE_CODES)
    if invalid_roles:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported roles: {', '.join(invalid_roles)}")


@router.get("")
def list_users(
    request: Request,
    display_name: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    role: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_order: str = Query(default="desc"),
    status: str | None = Query(default=None),
    username: str | None = Query(default=None),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {USER_MANAGE_PERMISSION})
    ensure_list_enum(status, USER_STATUSES, "user status")
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_list_enum(sort_by, USER_LIST_SORT_FIELDS, "sort_by")
    filters = {
        "display_name": display_name,
        "role": role,
        "status": status,
        "username": username,
    }
    started_at = perf_counter()
    repository = request.app.state.user_repository
    list_summaries = getattr(repository, "list_user_summaries", None)
    if callable(list_summaries) and (page is not None or page_size is not None):
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        payload = list_summaries(
            display_name=display_name,
            page=resolved_page,
            page_size=resolved_page_size,
            role=role,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
            username=username,
        )
        return envelope(
            add_list_observability(
                payload,
                filters=filters,
                list_name="users",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=sort_by,
                sort_order=sort_order,
                started_at=started_at,
            ),
            get_trace_id(request),
        )

    items = [
        item
        for item in repository.list_users()
        if list_text_matches(item, username, ("username",))
        and list_text_matches(item, display_name, ("display_name",))
        and (not status or item.get("status") == status)
        and (not role or role in item.get("roles", []))
    ]
    sorted_items = sort_list_items(
        items,
        allowed_fields=USER_LIST_SORT_FIELDS,
        default_sort_by="username",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        sorted_items,
        filters=filters,
        list_name="users",
        observed=page is not None or page_size is not None,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=get_trace_id(request),
    )


@router.post("")
def create_user(
    request: Request,
    payload: UserCreateRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {USER_MANAGE_PERMISSION})
    username = _ensure_non_blank(payload.username, "username")
    display_name = _ensure_non_blank(payload.display_name, "display_name")
    password = _ensure_non_blank(payload.password, "password")
    _ensure_enum(payload.status, USER_STATUSES, "user status")
    _ensure_roles(payload.roles)
    try:
        created = request.app.state.user_repository.create_user(
            display_name=display_name,
            password=password,
            roles=payload.roles,
            status=payload.status,
            username=username,
        )
    except ValueError as exc:
        if str(exc) == "user_exists":
            raise api_error(409, "USER_EXISTS", "User already exists") from exc
        raise
    return envelope(created, get_trace_id(request))


@router.patch("/{user_id}")
def patch_user(
    user_id: str,
    request: Request,
    payload: UserPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {USER_MANAGE_PERMISSION})
    updates = payload.model_dump(exclude_unset=True)
    if "display_name" in updates:
        updates["display_name"] = _ensure_non_blank(updates["display_name"], "display_name")
    if "password" in updates:
        updates["password"] = _ensure_non_blank(updates["password"], "password")
    if "roles" in updates:
        _ensure_roles(updates["roles"])
    if "status" in updates:
        _ensure_enum(updates["status"], USER_STATUSES, "user status")
    updated = request.app.state.user_repository.update_user(user_id, updates)
    if updated is None:
        raise api_error(404, "NOT_FOUND", "User not found")
    return envelope(updated, get_trace_id(request))


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {USER_MANAGE_PERMISSION})
    if user_id == user["id"]:
        raise api_error(409, "RESOURCE_IN_USE", "Current user cannot be deleted")
    deleted = request.app.state.user_repository.delete_user(user_id)
    if not deleted:
        raise api_error(404, "NOT_FOUND", "User not found")
    return envelope({"deleted": True, "id": user_id}, get_trace_id(request))
