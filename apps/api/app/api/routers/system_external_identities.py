from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentUser, api_error, require_permissions
from app.core.trace import envelope, get_trace_id
from app.services.operational_records import record_audit_event

router = APIRouter(prefix="/api/system/external-identities", tags=["system-external-identities"])
USER_MANAGE_PERMISSION = "system.users.manage"


def _identity_hint(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}***{value[-4:]}"


def _public_identity(identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "avatar_url": identity.get("avatar_url"),
        "corp_id": identity.get("corp_id"),
        "corp_name": identity.get("corp_name"),
        "display_name": identity.get("display_name"),
        "email": identity.get("email"),
        "id": identity.get("id"),
        "open_id_hint": _identity_hint(identity.get("open_id")),
        "provider": identity.get("provider"),
        "provider_subject_hint": _identity_hint(identity.get("provider_subject")),
        "status": identity.get("status"),
        "union_id_hint": _identity_hint(identity.get("union_id")),
        "user_id": identity.get("user_id"),
    }


def _find_user_summary(request: Request, user_id: str) -> dict[str, Any] | None:
    list_users = getattr(request.app.state.user_repository, "list_users", None)
    if not callable(list_users):
        return None
    return next((user for user in list_users() if user.get("id") == user_id), None)


def _local_password_configured(user: dict[str, Any] | None) -> bool:
    if user is None:
        return True
    return bool(user.get("local_password_configured", user.get("password_login_enabled", True)))


def _record_system_audit(
    request: Request,
    *,
    actor_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    subject_id: str,
    subject_type: str,
) -> None:
    current_store = request.app.state.store
    event = record_audit_event(
        current_store,
        actor_id=actor_id,
        event_type=event_type,
        payload=payload,
        subject_id=subject_id,
        subject_type=subject_type,
    )
    repository = getattr(current_store, "repository", None)
    audit_repository = getattr(repository, "_audit_read_repository", None)
    append_audit_event = getattr(audit_repository, "append_audit_event", None)
    if callable(append_audit_event):
        append_audit_event(event)


@router.get("")
def list_external_identities(
    request: Request,
    provider: str | None = Query(default=None),
    status: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {USER_MANAGE_PERMISSION})
    list_identities = getattr(
        request.app.state.external_identity_repository,
        "list_identities",
        None,
    )
    if not callable(list_identities):
        return envelope({"items": [], "total": 0}, get_trace_id(request))
    items = [
        _public_identity(identity)
        for identity in list_identities(provider=provider, status=status, user_id=user_id)
    ]
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@router.delete("/{identity_id}")
def unbind_external_identity(
    identity_id: str,
    request: Request,
    force: bool = Query(default=False),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {USER_MANAGE_PERMISSION})
    identity_repository = request.app.state.external_identity_repository
    find_by_id = getattr(identity_repository, "find_by_id", None)
    unbind_by_id = getattr(identity_repository, "unbind_by_id", None)
    if not callable(find_by_id) or not callable(unbind_by_id):
        raise api_error(404, "EXTERNAL_IDENTITY_NOT_FOUND", "External identity not found")
    identity = find_by_id(identity_id)
    if identity is None:
        raise api_error(404, "EXTERNAL_IDENTITY_NOT_FOUND", "External identity not found")
    if identity.get("status") != "active":
        raise api_error(409, "EXTERNAL_IDENTITY_NOT_ACTIVE", "External identity is not active")
    target_user = _find_user_summary(request, str(identity.get("user_id") or ""))
    if not force and not _local_password_configured(target_user):
        raise api_error(
            409,
            "DINGTALK_UNBIND_LOGIN_LOCKOUT_RISK",
            "Target user has no local password login configured",
        )
    if not unbind_by_id(identity_id):
        raise api_error(409, "EXTERNAL_IDENTITY_NOT_ACTIVE", "External identity is not active")
    _record_system_audit(
        request,
        actor_id=str(user.get("id") or user.get("username") or "unknown"),
        event_type="dingtalk_account.admin_unbound",
        payload={
            "corp_id": identity.get("corp_id"),
            "force": force,
            "provider": identity.get("provider"),
        },
        subject_id=str(identity.get("user_id") or ""),
        subject_type="user",
    )
    return envelope({"deleted": True, "id": identity_id}, get_trace_id(request))
