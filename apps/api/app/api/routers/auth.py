from __future__ import annotations

import secrets
from dataclasses import replace
from time import perf_counter
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser, api_error
from app.core.authorization import AuthorizationSnapshot, build_menu_tree
from app.core.config import get_settings
from app.core.dingtalk_oauth import DingTalkOAuthError, DingTalkProfile
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
from app.services.operational_records import record_audit_event

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])
DINGTALK_PROVIDER = "dingtalk"
DINGTALK_STATE_TTL_SECONDS = 600
DINGTALK_TICKET_TTL_SECONDS = 300
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
    challenge_answer: str | None = None
    challenge_id: str | None = None
    username: str
    password: str


class DingTalkTicketExchangeRequest(BaseModel):
    ticket: str


class ProfilePatchRequest(BaseModel):
    current_password: str | None = None
    display_name: str | None = None
    email: str | None = None
    mobile: str | None = None
    new_password: str | None = None


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["username"],
        "display_name": user["display_name"],
        "local_password_configured": bool(user.get("password_login_enabled", True)),
        "mobile": user.get("mobile") or "",
        "roles": user["roles"],
        "status": user.get("status", "active"),
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
    return settings.is_test_env or settings.allow_seeded_users


def _is_disabled_seeded_default_login(username: str, password: str) -> bool:
    seeded_user = SEEDED_USERS.get(username)
    if seeded_user is None or _seeded_users_enabled():
        return False
    return verify_password(password, seeded_user["password_hash"])


def _login_challenge_repository(request: Request) -> Any:
    repository = getattr(request.app.state, "login_challenge_repository", None)
    if repository is None:
        raise api_error(503, "LOGIN_CHALLENGE_UNAVAILABLE", "安全校验暂时不可用")
    return repository


def _require_login_challenge(request: Request, payload: LoginRequest) -> None:
    if not settings.login_challenge_enabled:
        return
    if not payload.challenge_id or not payload.challenge_answer:
        raise api_error(400, "LOGIN_CHALLENGE_REQUIRED", "请输入安全校验答案")
    verified = _login_challenge_repository(request).consume_challenge(
        answer=payload.challenge_answer,
        challenge_id=payload.challenge_id,
    )
    if not verified:
        raise api_error(401, "LOGIN_CHALLENGE_INVALID", "安全校验答案错误或已过期")


def _issue_access_token(user: dict[str, Any]) -> str:
    return create_access_token(
        {"sub": user["id"], "username": user["username"], "roles": user["roles"]},
        secret_key=settings.app_secret_key,
        expires_in_seconds=settings.access_token_expire_seconds,
    )


def _issue_login_response(request: Request, user: dict[str, Any]) -> dict[str, Any]:
    access_token = _issue_access_token(user)
    return envelope(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_seconds,
            "user": _public_user(user),
        },
        get_trace_id(request),
    )


def _safe_redirect_path(redirect: str | None, *, default: str = "/welcome") -> str:
    if (
        redirect
        and redirect.startswith("/")
        and not redirect.startswith("//")
        and redirect != "/login"
        and not redirect.startswith("/login/dingtalk/callback")
    ):
        return redirect
    return default


def _frontend_base_url() -> str:
    if getattr(settings, "dingtalk_frontend_base_url", ""):
        return settings.dingtalk_frontend_base_url.rstrip("/")
    origins = settings.cors_origin_list
    return origins[0].rstrip("/") if origins else ""


def _frontend_location(path: str, params: dict[str, str | None]) -> str:
    query = urlencode({key: value for key, value in params.items() if value})
    location = f"{path}?{query}" if query else path
    base_url = _frontend_base_url()
    if base_url:
        return f"{base_url}{location}"
    return location


def _frontend_callback_location(params: dict[str, str | None]) -> str:
    return _frontend_location(settings.dingtalk_frontend_callback_path, params)


def _dingtalk_configured() -> bool:
    return settings.dingtalk_login_configured


def _require_dingtalk_configured() -> None:
    if _dingtalk_configured():
        return
    raise api_error(
        503,
        "DINGTALK_LOGIN_NOT_CONFIGURED",
        "DingTalk login is not configured",
    )


def _dingtalk_oauth_state_repository(request: Request) -> Any:
    repository = getattr(request.app.state, "dingtalk_oauth_state_repository", None)
    if repository is None:
        raise api_error(503, "DINGTALK_LOGIN_NOT_CONFIGURED", "DingTalk login is not configured")
    return repository


def _create_oauth_state(
    request: Request,
    *,
    attribute_name: str,
    purpose: str,
    redirect: str,
    user_id: str | None = None,
) -> str:
    del attribute_name
    return _dingtalk_oauth_state_repository(request).create_state(
        expires_in_seconds=DINGTALK_STATE_TTL_SECONDS,
        purpose=purpose,
        redirect=redirect,
        user_id=user_id,
    )


def _consume_oauth_state(
    request: Request,
    *,
    attribute_name: str,
    purpose: str,
    state: str | None,
) -> dict[str, Any]:
    if not state:
        raise api_error(400, "DINGTALK_STATE_INVALID", "DingTalk state is required")
    del attribute_name
    payload = _dingtalk_oauth_state_repository(request).consume_state(
        purpose=purpose,
        state=state,
    )
    if payload is None:
        raise api_error(400, "DINGTALK_STATE_INVALID", "DingTalk state is invalid or expired")
    return payload


def _create_login_ticket(request: Request, *, redirect: str, user_id: str) -> str:
    return _dingtalk_oauth_state_repository(request).create_ticket(
        expires_in_seconds=DINGTALK_TICKET_TTL_SECONDS,
        redirect=redirect,
        user_id=user_id,
    )


def _consume_login_ticket(request: Request, ticket: str) -> dict[str, Any]:
    if not ticket:
        raise api_error(400, "DINGTALK_TICKET_INVALID", "DingTalk login ticket is required")
    payload = _dingtalk_oauth_state_repository(request).consume_ticket(ticket)
    if payload is None:
        raise api_error(401, "DINGTALK_TICKET_INVALID", "DingTalk login ticket is invalid")
    return payload


def _dingtalk_oauth_client(request: Request) -> Any:
    client = getattr(request.app.state, "dingtalk_oauth_client", None)
    if client is None:
        raise api_error(503, "DINGTALK_LOGIN_NOT_CONFIGURED", "DingTalk login is not configured")
    return client


def _profile_from_exchange_result(result: Any) -> DingTalkProfile:
    if isinstance(result, DingTalkProfile):
        return _profile_with_configured_corp_name(result)
    if not isinstance(result, dict):
        raise api_error(502, "DINGTALK_PROFILE_INCOMPLETE", "DingTalk profile is invalid")
    union_id = _first_profile_text(result, "union_id", "unionId", "unionid")
    open_id = _first_profile_text(result, "open_id", "openId", "openid")
    subject = _first_profile_text(result, "subject") or union_id or open_id
    if not subject:
        raise api_error(502, "DINGTALK_PROFILE_INCOMPLETE", "DingTalk subject missing")
    corp_id = _first_profile_text(result, "corp_id", "corpId")
    return _profile_with_configured_corp_name(
        DingTalkProfile(
            avatar_url=_first_profile_text(result, "avatar_url", "avatarUrl", "avatar"),
            corp_id=corp_id,
            corp_name=_first_profile_text(
                result,
                "corp_name",
                "corpName",
                "companyName",
                "organizationName",
                "orgName",
                "tenantName",
            ),
            display_name=_first_profile_text(result, "display_name", "displayName", "name", "nick"),
            email=_first_profile_text(result, "email"),
            open_id=open_id,
            subject=subject,
            union_id=union_id,
        )
    )


def _first_profile_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _profile_with_configured_corp_name(profile: DingTalkProfile) -> DingTalkProfile:
    if profile.corp_name or not profile.corp_id:
        return profile
    corp_name = settings.dingtalk_corp_name_map.get(profile.corp_id)
    if not corp_name:
        return profile
    return replace(profile, corp_name=corp_name)


def _ensure_dingtalk_corp_allowed(profile: DingTalkProfile) -> None:
    allowed_corp_ids = settings.dingtalk_allowed_corp_id_set
    if not allowed_corp_ids:
        return
    if profile.corp_id in allowed_corp_ids:
        return
    raise api_error(403, "DINGTALK_CORP_NOT_ALLOWED", "DingTalk corp is not allowed")


def _record_auth_audit(
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


def _normalize_profile_text(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def _normalize_optional_profile_text(value: str | None) -> str:
    return str(value or "").strip()


def _normalize_profile_email(value: str | None) -> str:
    email = _normalize_profile_text(value, "email")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise api_error(400, "VALIDATION_ERROR", "email is invalid")
    return email.lower()


def _normalize_profile_mobile(value: str | None) -> str:
    mobile = _normalize_optional_profile_text(value)
    if not mobile:
        return ""
    if len(mobile) > 32:
        raise api_error(400, "VALIDATION_ERROR", "mobile is too long")
    allowed_characters = set("0123456789+- ()")
    if any(character not in allowed_characters for character in mobile):
        raise api_error(400, "VALIDATION_ERROR", "mobile is invalid")
    return mobile


def _dingtalk_binding_summary(request: Request, user_id: str) -> dict[str, Any]:
    identity_repository = getattr(request.app.state, "external_identity_repository", None)
    find_active_by_user = getattr(identity_repository, "find_active_by_user", None)
    if not callable(find_active_by_user):
        return {"bound": False}
    identity = find_active_by_user(DINGTALK_PROVIDER, user_id)
    if identity is None:
        return {"bound": False}
    corp_id = identity.get("corp_id")
    return {
        "avatar_url": identity.get("avatar_url"),
        "bound": True,
        "corp_id": corp_id,
        "corp_name": identity.get("corp_name")
        or settings.dingtalk_corp_name_map.get(corp_id or ""),
        "display_name": identity.get("display_name"),
        "email": identity.get("email"),
        "provider": DINGTALK_PROVIDER,
    }


def _profile_payload(request: Request, user: dict[str, Any]) -> dict[str, Any]:
    payload = _authorized_user(request, user)
    payload["dingtalk_binding"] = _dingtalk_binding_summary(request, user["id"])
    payload["local_password_configured"] = bool(user.get("password_login_enabled", True))
    return payload


def _dingtalk_generated_username(profile: DingTalkProfile) -> str:
    if profile.email:
        return profile.email
    normalized_subject = "".join(
        character if character.isalnum() else "_"
        for character in profile.subject.lower()
    )
    return f"dingtalk_{normalized_subject}@dingtalk.local"


def _dingtalk_display_name(profile: DingTalkProfile) -> str:
    return profile.display_name or profile.email or f"DingTalk {profile.subject[-6:]}"


def _find_user_any_status(request: Request, user_id: str) -> dict[str, Any] | None:
    list_users = getattr(request.app.state.user_repository, "list_users", None)
    if not callable(list_users):
        return None
    return next(
        (user for user in list_users() if user.get("id") == user_id),
        None,
    )


def _resolve_dingtalk_user(request: Request, profile: DingTalkProfile) -> dict[str, Any]:
    identity_repository = request.app.state.external_identity_repository
    identity = identity_repository.find_active(DINGTALK_PROVIDER, profile.subject)
    if identity is not None:
        user = request.app.state.user_repository.get_by_id(identity["user_id"])
        if user is None:
            inactive_user = _find_user_any_status(request, str(identity["user_id"]))
            if inactive_user is not None and inactive_user.get("status") == "pending_approval":
                raise api_error(
                    403,
                    "DINGTALK_ACCOUNT_PENDING_APPROVAL",
                    "DingTalk account is pending approval",
                )
            raise api_error(403, "DINGTALK_ACCOUNT_INACTIVE", "DingTalk account is inactive")
        return user

    if not settings.dingtalk_auto_provision:
        raise api_error(
            403,
            "DINGTALK_ACCOUNT_NOT_BOUND",
            "DingTalk account is not bound to an AI Brain user",
        )

    status = "pending_approval"
    try:
        user = request.app.state.user_repository.create_user(
            display_name=_dingtalk_display_name(profile),
            password=secrets.token_urlsafe(32),
            password_login_enabled=False,
            roles=[settings.dingtalk_auto_provision_role or "viewer"],
            status=status,
            username=_dingtalk_generated_username(profile),
        )
    except ValueError as exc:
        raise api_error(
            403,
            "DINGTALK_ACCOUNT_NOT_BOUND",
            "Existing AI Brain user must bind DingTalk explicitly",
        ) from exc

    try:
        identity_repository.upsert_identity(
            provider=DINGTALK_PROVIDER,
            provider_subject=profile.subject,
            profile=profile.identity_profile(),
            user_id=user["id"],
        )
    except ValueError as exc:
        raise api_error(
            409,
            "EXTERNAL_IDENTITY_CONFLICT",
            "DingTalk account is already bound",
        ) from exc
    _record_auth_audit(
        request,
        actor_id="system",
        event_type="dingtalk_account.provisioned",
        payload={"corp_id": profile.corp_id, "status": status},
        subject_id=user["id"],
        subject_type="user",
    )
    if status != "active":
        raise api_error(
            403,
            "DINGTALK_ACCOUNT_PENDING_APPROVAL",
            "DingTalk account is pending approval",
        )
    return user


def _callback_error_redirect(
    code: str,
    message: str,
    *,
    redirect: str = "/welcome",
) -> RedirectResponse:
    return RedirectResponse(
        _frontend_callback_location(
            {
                "error": code,
                "message": message,
                "redirect": _safe_redirect_path(redirect),
            }
        ),
        status_code=302,
    )


@router.post("/login")
def login(request: Request, payload: LoginRequest) -> dict[str, Any]:
    _require_login_challenge(request, payload)
    user = request.app.state.user_repository.get_by_username(payload.username)
    if user is None:
        raise api_error(401, "INVALID_CREDENTIALS", "Invalid username or password")
    if not user.get("password_login_enabled", True):
        raise api_error(403, "PASSWORD_LOGIN_DISABLED", "Password login is not configured")
    if not verify_password(payload.password, user["password_hash"]):
        raise api_error(401, "INVALID_CREDENTIALS", "Invalid username or password")
    if _is_disabled_seeded_default_login(payload.username, payload.password):
        raise api_error(
            403,
            "DEFAULT_CREDENTIALS_DISABLED",
            "Seeded default credentials are disabled unless explicitly enabled for local testing",
        )

    return _issue_login_response(request, user)


@router.post("/login-challenge")
def login_challenge(request: Request) -> dict[str, Any]:
    challenge = _login_challenge_repository(request).create_challenge(
        expires_in_seconds=settings.login_challenge_ttl_seconds,
    )
    return envelope(challenge, get_trace_id(request))


@router.get("/providers")
def providers(request: Request) -> dict[str, Any]:
    dingtalk_configured = _dingtalk_configured()
    return envelope(
        {
            "dingtalk": {
                "bind_start_url": "/api/auth/dingtalk/bind/start"
                if dingtalk_configured
                else None,
                "configured": dingtalk_configured,
                "display_name": "钉钉登录",
                "enabled": dingtalk_configured,
                "start_url": "/api/auth/dingtalk/start" if dingtalk_configured else None,
            },
            "local": {
                "challenge_required": settings.login_challenge_enabled,
                "challenge_url": "/api/auth/login-challenge",
                "display_name": "账号密码登录",
                "enabled": True,
                "start_url": "/api/auth/login",
            },
        },
        get_trace_id(request),
    )


@router.get("/dingtalk/start")
def dingtalk_start(
    request: Request,
    redirect: str | None = Query(default=None),
) -> RedirectResponse:
    _require_dingtalk_configured()
    safe_redirect = _safe_redirect_path(redirect)
    state = _create_oauth_state(
        request,
        attribute_name="dingtalk_oauth_states",
        purpose="login",
        redirect=safe_redirect,
    )
    authorize_url = _dingtalk_oauth_client(request).build_authorize_url(
        redirect_uri=settings.dingtalk_redirect_uri,
        state=state,
    )
    return RedirectResponse(authorize_url, status_code=302)


@router.get("/dingtalk/callback")
def dingtalk_callback(
    request: Request,
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> RedirectResponse:
    try:
        state_payload = _consume_oauth_state(
            request,
            attribute_name="dingtalk_oauth_states",
            purpose="login",
            state=state,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return _callback_error_redirect(
            str(detail.get("code") or "DINGTALK_STATE_INVALID"),
            str(detail.get("message") or "DingTalk state is invalid"),
        )

    redirect = _safe_redirect_path(str(state_payload.get("redirect") or ""))
    if error:
        return _callback_error_redirect("DINGTALK_AUTH_DENIED", error, redirect=redirect)
    if not code:
        return _callback_error_redirect(
            "DINGTALK_CODE_MISSING",
            "DingTalk authorization code is missing",
            redirect=redirect,
        )

    try:
        profile = _profile_from_exchange_result(
            _dingtalk_oauth_client(request).exchange_code_for_profile(code)
        )
        _ensure_dingtalk_corp_allowed(profile)
        user = _resolve_dingtalk_user(request, profile)
    except DingTalkOAuthError as exc:
        return _callback_error_redirect(exc.code, exc.message, redirect=redirect)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return _callback_error_redirect(
            str(detail.get("code") or "DINGTALK_LOGIN_FAILED"),
            str(detail.get("message") or "DingTalk login failed"),
            redirect=redirect,
        )

    ticket = _create_login_ticket(request, redirect=redirect, user_id=user["id"])
    _record_auth_audit(
        request,
        actor_id=user["id"],
        event_type="dingtalk_login.succeeded",
        payload={"corp_id": profile.corp_id},
        subject_id=user["id"],
        subject_type="user",
    )
    return RedirectResponse(
        _frontend_callback_location({"redirect": redirect, "ticket": ticket}),
        status_code=302,
    )


@router.post("/dingtalk/exchange-ticket")
def dingtalk_exchange_ticket(
    request: Request,
    payload: DingTalkTicketExchangeRequest,
) -> dict[str, Any]:
    ticket_payload = _consume_login_ticket(request, payload.ticket)
    user = request.app.state.user_repository.get_by_id(str(ticket_payload.get("user_id") or ""))
    if user is None:
        raise api_error(401, "DINGTALK_TICKET_INVALID", "DingTalk login ticket is invalid")
    return _issue_login_response(request, user)


@router.post("/dingtalk/bind/start")
def dingtalk_bind_start(
    request: Request,
    redirect: str | None = Query(default=None),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_dingtalk_configured()
    safe_redirect = _safe_redirect_path(redirect)
    state = _create_oauth_state(
        request,
        attribute_name="dingtalk_bind_states",
        purpose="bind",
        redirect=safe_redirect,
        user_id=user["id"],
    )
    authorize_url = _dingtalk_oauth_client(request).build_authorize_url(
        redirect_uri=settings.dingtalk_bind_redirect_uri_value,
        state=state,
    )
    return envelope(
        {
            "authorize_url": authorize_url,
            "expires_in": DINGTALK_STATE_TTL_SECONDS,
        },
        get_trace_id(request),
    )


@router.get("/dingtalk/bind/callback")
def dingtalk_bind_callback(
    request: Request,
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> RedirectResponse:
    try:
        state_payload = _consume_oauth_state(
            request,
            attribute_name="dingtalk_bind_states",
            purpose="bind",
            state=state,
        )
    except HTTPException:
        return RedirectResponse(
            _frontend_location(
                "/welcome",
                {"dingtalk_bind_error": "DINGTALK_STATE_INVALID"},
            ),
            status_code=302,
        )
    redirect = _safe_redirect_path(str(state_payload.get("redirect") or ""))
    if error:
        return RedirectResponse(
            _frontend_location(redirect, {"dingtalk_bind_error": "DINGTALK_AUTH_DENIED"}),
            status_code=302,
        )
    if not code:
        return RedirectResponse(
            _frontend_location(redirect, {"dingtalk_bind_error": "DINGTALK_CODE_MISSING"}),
            status_code=302,
        )
    try:
        profile = _profile_from_exchange_result(
            _dingtalk_oauth_client(request).exchange_code_for_profile(code)
        )
        _ensure_dingtalk_corp_allowed(profile)
    except DingTalkOAuthError:
        return RedirectResponse(
            _frontend_location(redirect, {"dingtalk_bind_error": "DINGTALK_BIND_FAILED"}),
            status_code=302,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return RedirectResponse(
            _frontend_location(
                redirect,
                {"dingtalk_bind_error": str(detail.get("code") or "DINGTALK_BIND_FAILED")},
            ),
            status_code=302,
        )
    user_id = str(state_payload.get("user_id") or "")
    user = request.app.state.user_repository.get_by_id(user_id)
    if user is None:
        return RedirectResponse(
            _frontend_location(redirect, {"dingtalk_bind_error": "DINGTALK_ACCOUNT_INACTIVE"}),
            status_code=302,
        )
    previous_identity = request.app.state.external_identity_repository.find_active_by_user(
        DINGTALK_PROVIDER,
        user_id,
    )
    try:
        request.app.state.external_identity_repository.upsert_identity(
            provider=DINGTALK_PROVIDER,
            provider_subject=profile.subject,
            profile=profile.identity_profile(),
            replace_existing_user_identity=True,
            user_id=user_id,
        )
    except ValueError as exc:
        error_code = (
            "DINGTALK_USER_ALREADY_BOUND"
            if str(exc) == "user_identity_exists"
            else "EXTERNAL_IDENTITY_CONFLICT"
        )
        return RedirectResponse(
            _frontend_location(redirect, {"dingtalk_bind_error": error_code}),
            status_code=302,
        )
    rebound = (
        previous_identity is not None
        and previous_identity.get("provider_subject") != profile.subject
    )
    _record_auth_audit(
        request,
        actor_id=user_id,
        event_type="dingtalk_account.rebound" if rebound else "dingtalk_account.bound",
        payload={
            "corp_id": profile.corp_id,
            "previous_corp_id": previous_identity.get("corp_id") if rebound else None,
        },
        subject_id=user_id,
        subject_type="user",
    )
    return RedirectResponse(
        _frontend_location(redirect, {"dingtalk_bound": "true"}),
        status_code=302,
    )


@router.post("/dingtalk/unbind")
def dingtalk_unbind(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    if not user.get("password_login_enabled", True):
        raise api_error(
            409,
            "DINGTALK_UNBIND_LOGIN_LOCKOUT_RISK",
            "Set a local password before unbinding DingTalk",
        )
    unbound = request.app.state.external_identity_repository.unbind(
        provider=DINGTALK_PROVIDER,
        user_id=user["id"],
    )
    if not unbound:
        raise api_error(404, "DINGTALK_ACCOUNT_NOT_BOUND", "DingTalk account is not bound")
    _record_auth_audit(
        request,
        actor_id=user["id"],
        event_type="dingtalk_account.unbound",
        subject_id=user["id"],
        subject_type="user",
    )
    return envelope({"success": True}, get_trace_id(request))


@router.get("/profile")
def profile(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    return envelope(_profile_payload(request, user), get_trace_id(request))


@router.patch("/profile")
def update_profile(
    request: Request,
    payload: ProfilePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    changed_fields: list[str] = []
    require_current_password = False

    if "display_name" in payload.model_fields_set:
        display_name = _normalize_profile_text(payload.display_name, "display_name")
        if display_name != user.get("display_name"):
            updates["display_name"] = display_name
            changed_fields.append("display_name")

    if "mobile" in payload.model_fields_set:
        mobile = _normalize_profile_mobile(payload.mobile)
        if mobile != (user.get("mobile") or ""):
            updates["mobile"] = mobile
            changed_fields.append("mobile")

    if "email" in payload.model_fields_set:
        email = _normalize_profile_email(payload.email)
        if email != user.get("username"):
            updates["username"] = email
            changed_fields.append("email")
            require_current_password = True

    if "new_password" in payload.model_fields_set:
        new_password = _normalize_profile_text(payload.new_password, "new_password")
        if len(new_password) < 8:
            raise api_error(400, "VALIDATION_ERROR", "new_password is too short")
        updates["password"] = new_password
        changed_fields.append("password")
        require_current_password = bool(user.get("password_login_enabled", True))

    if require_current_password:
        current_password = _normalize_profile_text(
            payload.current_password,
            "current_password",
        )
        if not verify_password(current_password, user["password_hash"]):
            raise api_error(403, "CURRENT_PASSWORD_INVALID", "Current password is invalid")

    try:
        updated_user = request.app.state.user_repository.update_user(user["id"], updates)
    except ValueError as exc:
        if str(exc) == "user_exists":
            raise api_error(409, "USER_EXISTS", "User already exists") from exc
        raise
    if updated_user is None:
        raise api_error(404, "NOT_FOUND", "User not found")

    if changed_fields:
        _record_auth_audit(
            request,
            actor_id=user["id"],
            event_type="auth.profile.updated",
            payload={"changed_fields": sorted(changed_fields)},
            subject_id=user["id"],
            subject_type="user",
        )

    response_payload: dict[str, Any] = {"user": _profile_payload(request, updated_user)}
    if "email" in changed_fields:
        response_payload.update(
            {
                "access_token": _issue_access_token(updated_user),
                "expires_in": settings.access_token_expire_seconds,
                "token_type": "bearer",
            }
        )
    return envelope(response_payload, get_trace_id(request))


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
