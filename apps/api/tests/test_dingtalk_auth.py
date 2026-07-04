from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from test_database_persistence import app, client

from app.api.routers import auth as auth_router
from app.core.dingtalk_oauth import DingTalkProfile
from app.core.dingtalk_oauth_state import MemoryDingTalkOAuthStateRepository
from app.core.external_identities import MemoryExternalIdentityRepository
from app.core.security import hash_password
from app.core.store import MemoryStore
from app.core.users import MemoryUserRepository


class FakeDingTalkOAuthClient:
    def __init__(self, profile: DingTalkProfile) -> None:
        self.profile = profile
        self.authorize_requests: list[dict[str, str]] = []

    def build_authorize_url(self, *, redirect_uri: str, state: str) -> str:
        self.authorize_requests.append({"redirect_uri": redirect_uri, "state": state})
        return f"https://dingtalk.test/oauth?redirect_uri={redirect_uri}&state={state}"

    def exchange_code_for_profile(self, code: str) -> DingTalkProfile:
        if code == "denied":
            raise AssertionError("unexpected exchange for denied code")
        return self.profile


SETTING_NAMES = (
    "dingtalk_allowed_corp_ids",
    "dingtalk_auth_url",
    "dingtalk_auto_provision",
    "dingtalk_auto_provision_role",
    "dingtalk_bind_redirect_uri",
    "dingtalk_client_id",
    "dingtalk_client_secret",
    "dingtalk_client_secret_ref",
    "dingtalk_frontend_base_url",
    "dingtalk_frontend_callback_path",
    "dingtalk_login_enabled",
    "dingtalk_pending_approval",
    "dingtalk_redirect_uri",
)


def _install_dingtalk_test_state(
    profile: DingTalkProfile,
    *,
    auto_provision: bool = False,
    allowed_corp_ids: str = "",
    pending_approval: bool = False,
    state_repository: MemoryDingTalkOAuthStateRepository | None = None,
    user_repository: MemoryUserRepository | None = None,
):
    original_state = {
        "dingtalk_bind_states": getattr(app.state, "dingtalk_bind_states", None),
        "dingtalk_login_tickets": getattr(app.state, "dingtalk_login_tickets", None),
        "dingtalk_oauth_client": app.state.dingtalk_oauth_client,
        "dingtalk_oauth_state_repository": getattr(
            app.state,
            "dingtalk_oauth_state_repository",
            None,
        ),
        "dingtalk_oauth_states": getattr(app.state, "dingtalk_oauth_states", None),
        "external_identity_repository": app.state.external_identity_repository,
        "store": app.state.store,
        "user_repository": app.state.user_repository,
    }
    original_settings = {
        name: getattr(auth_router.settings, name)
        for name in SETTING_NAMES
    }
    fake_client = FakeDingTalkOAuthClient(profile)
    app.state.store = MemoryStore()
    app.state.user_repository = user_repository or MemoryUserRepository.seeded()
    app.state.external_identity_repository = MemoryExternalIdentityRepository()
    app.state.dingtalk_bind_states = {}
    app.state.dingtalk_login_tickets = {}
    app.state.dingtalk_oauth_client = fake_client
    app.state.dingtalk_oauth_state_repository = (
        state_repository or MemoryDingTalkOAuthStateRepository()
    )
    app.state.dingtalk_oauth_states = {}

    auth_router.settings.dingtalk_allowed_corp_ids = allowed_corp_ids
    auth_router.settings.dingtalk_auth_url = "https://dingtalk.test/oauth"
    auth_router.settings.dingtalk_auto_provision = auto_provision
    auth_router.settings.dingtalk_auto_provision_role = "viewer"
    auth_router.settings.dingtalk_bind_redirect_uri = ""
    auth_router.settings.dingtalk_client_id = "ding-client-id"
    auth_router.settings.dingtalk_client_secret = "ding-secret"
    auth_router.settings.dingtalk_client_secret_ref = ""
    auth_router.settings.dingtalk_frontend_base_url = "http://localhost:5173"
    auth_router.settings.dingtalk_frontend_callback_path = "/login/dingtalk/callback"
    auth_router.settings.dingtalk_login_enabled = True
    auth_router.settings.dingtalk_pending_approval = pending_approval
    auth_router.settings.dingtalk_redirect_uri = (
        "http://localhost:8000/api/auth/dingtalk/callback"
    )

    def restore() -> None:
        for name, value in original_state.items():
            setattr(app.state, name, value)
        for name, value in original_settings.items():
            setattr(auth_router.settings, name, value)

    return fake_client, restore


def _start_dingtalk_login(redirect: str = "/welcome") -> tuple[str, str]:
    response = client.get(
        f"/api/auth/dingtalk/start?redirect={redirect}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers["location"]
    query = parse_qs(urlparse(location).query)
    return location, query["state"][0]


def test_dingtalk_provider_is_hidden_until_configured():
    profile = DingTalkProfile(subject="union_hidden", union_id="union_hidden")
    fake_client, restore = _install_dingtalk_test_state(profile)
    try:
        auth_router.settings.dingtalk_login_enabled = False
        disabled = client.get("/api/auth/providers")
        assert disabled.status_code == 200
        assert disabled.json()["data"]["local"]["enabled"] is True
        assert disabled.json()["data"]["dingtalk"]["enabled"] is False

        auth_router.settings.dingtalk_login_enabled = True
        enabled = client.get("/api/auth/providers")
        assert enabled.status_code == 200
        data = enabled.json()["data"]
        assert data["dingtalk"]["enabled"] is True
        assert data["dingtalk"]["start_url"] == "/api/auth/dingtalk/start"
        assert "ding-secret" not in str(data)
        assert fake_client.authorize_requests == []
    finally:
        restore()


def test_dingtalk_start_sanitizes_redirect_and_creates_state():
    profile = DingTalkProfile(subject="union_start", union_id="union_start")
    fake_client, restore = _install_dingtalk_test_state(profile)
    try:
        location, state = _start_dingtalk_login("https://evil.test/phish")
        assert location.startswith("https://dingtalk.test/oauth")
        state_payload = app.state.dingtalk_oauth_state_repository.states[state]
        assert state_payload["redirect"] == "/welcome"
        assert state_payload["purpose"] == "login"
        assert fake_client.authorize_requests == [
            {
                "redirect_uri": "http://localhost:8000/api/auth/dingtalk/callback",
                "state": state,
            }
        ]
    finally:
        restore()


def test_dingtalk_login_state_and_ticket_are_backed_by_shared_repository():
    profile = DingTalkProfile(
        corp_id="corp_allowed",
        display_name="钉钉张三",
        email="zhangsan@example.com",
        subject="union_zhangsan",
        union_id="union_zhangsan",
    )
    state_repository = MemoryDingTalkOAuthStateRepository()
    _fake_client, restore = _install_dingtalk_test_state(
        profile,
        allowed_corp_ids="corp_allowed",
        auto_provision=False,
        pending_approval=False,
        state_repository=state_repository,
        user_repository=MemoryUserRepository(
            {
                "zhangsan@example.com": {
                    "display_name": "钉钉张三",
                    "id": "user_zhangsan",
                    "password_hash": hash_password("local-secret", salt="zhangsan-salt"),
                    "roles": ["viewer"],
                    "status": "active",
                    "username": "zhangsan@example.com",
                }
            }
        ),
    )
    try:
        app.state.external_identity_repository.upsert_identity(
            provider="dingtalk",
            provider_subject="union_zhangsan",
            profile=profile.identity_profile(),
            user_id="user_zhangsan",
        )
        _location, state = _start_dingtalk_login("/delivery/bugs")
        assert state in state_repository.states

        callback = client.get(
            f"/api/auth/dingtalk/callback?code=ok&state={state}",
            follow_redirects=False,
        )
        assert callback.status_code == 302
        callback_query = parse_qs(urlparse(callback.headers["location"]).query)
        ticket = callback_query["ticket"][0]
        assert ticket in state_repository.tickets

        app.state.dingtalk_oauth_states = {}
        app.state.dingtalk_login_tickets = {}
        exchanged = client.post(
            "/api/auth/dingtalk/exchange-ticket",
            json={"ticket": ticket},
        )
        assert exchanged.status_code == 200
        assert exchanged.json()["data"]["user"]["id"] == "user_zhangsan"
        replay = client.post(
            "/api/auth/dingtalk/exchange-ticket",
            json={"ticket": ticket},
        )
        assert replay.status_code == 401
    finally:
        restore()


def test_dingtalk_callback_auto_provisions_pending_user_without_ticket():
    profile = DingTalkProfile(
        corp_id="corp_allowed",
        display_name="钉钉张三",
        email="zhangsan@example.com",
        subject="union_zhangsan",
        union_id="union_zhangsan",
    )
    _fake_client, restore = _install_dingtalk_test_state(
        profile,
        allowed_corp_ids="corp_allowed",
        auto_provision=True,
        pending_approval=False,
        user_repository=MemoryUserRepository({}),
    )
    try:
        _location, state = _start_dingtalk_login("/delivery/bugs")
        callback = client.get(
            f"/api/auth/dingtalk/callback?code=ok&state={state}",
            follow_redirects=False,
        )
        assert callback.status_code == 302
        callback_url = urlparse(callback.headers["location"])
        callback_query = parse_qs(callback_url.query)
        assert callback_url.path == "/login/dingtalk/callback"
        assert callback_query["redirect"] == ["/delivery/bugs"]
        assert callback_query["error"] == ["DINGTALK_ACCOUNT_PENDING_APPROVAL"]
        assert "ticket" not in callback_query
        user = next(
            item
            for item in app.state.user_repository.list_users()
            if item["username"] == "zhangsan@example.com"
        )
        assert user["roles"] == ["viewer"]
        assert user["status"] == "pending_approval"
        assert [
            event["event_type"]
            for event in app.state.store.audit_events
        ] == ["dingtalk_account.provisioned"]
    finally:
        restore()


def test_dingtalk_pending_auto_provision_login_remains_pending_until_user_is_active():
    profile = DingTalkProfile(
        corp_id="corp_allowed",
        display_name="钉钉张三",
        email="zhangsan@example.com",
        subject="union_zhangsan",
        union_id="union_zhangsan",
    )
    user_repository = MemoryUserRepository({})
    _fake_client, restore = _install_dingtalk_test_state(
        profile,
        allowed_corp_ids="corp_allowed",
        auto_provision=True,
        user_repository=user_repository,
    )
    try:
        _location, state = _start_dingtalk_login("/delivery/bugs")
        first_callback = client.get(
            f"/api/auth/dingtalk/callback?code=ok&state={state}",
            follow_redirects=False,
        )
        assert parse_qs(urlparse(first_callback.headers["location"]).query)["error"] == [
            "DINGTALK_ACCOUNT_PENDING_APPROVAL"
        ]

        _location, second_state = _start_dingtalk_login("/delivery/bugs")
        second_callback = client.get(
            f"/api/auth/dingtalk/callback?code=ok&state={second_state}",
            follow_redirects=False,
        )
        assert parse_qs(urlparse(second_callback.headers["location"]).query)["error"] == [
            "DINGTALK_ACCOUNT_PENDING_APPROVAL"
        ]

        pending_user = next(
            item
            for item in user_repository.list_users()
            if item["username"] == "zhangsan@example.com"
        )
        user_repository.update_user(pending_user["id"], {"status": "active"})

        _location, approved_state = _start_dingtalk_login("/delivery/bugs")
        approved_callback = client.get(
            f"/api/auth/dingtalk/callback?code=ok&state={approved_state}",
            follow_redirects=False,
        )
        approved_query = parse_qs(urlparse(approved_callback.headers["location"]).query)
        assert "ticket" in approved_query
        assert "error" not in approved_query
    finally:
        restore()


def test_dingtalk_callback_rejects_unapproved_corp():
    profile = DingTalkProfile(
        corp_id="corp_denied",
        display_name="钉钉李四",
        subject="union_lisi",
        union_id="union_lisi",
    )
    _fake_client, restore = _install_dingtalk_test_state(
        profile,
        allowed_corp_ids="corp_allowed",
        auto_provision=True,
    )
    try:
        _location, state = _start_dingtalk_login("/delivery/bugs")
        callback = client.get(
            f"/api/auth/dingtalk/callback?code=ok&state={state}",
            follow_redirects=False,
        )
        assert callback.status_code == 302
        callback_query = parse_qs(urlparse(callback.headers["location"]).query)
        assert callback_query["error"] == ["DINGTALK_CORP_NOT_ALLOWED"]
        assert "ticket" not in callback_query
    finally:
        restore()


def test_dingtalk_bind_and_unbind_current_user():
    profile = DingTalkProfile(
        corp_id="corp_allowed",
        display_name="AI Brain Admin",
        subject="union_admin",
        union_id="union_admin",
    )
    fake_client, restore = _install_dingtalk_test_state(
        profile,
        allowed_corp_ids="corp_allowed",
    )
    try:
        login = client.post(
            "/api/auth/login",
            json={"password": "admin123", "username": "admin@example.com"},
        )
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        started = client.post(
            "/api/auth/dingtalk/bind/start?redirect=/welcome",
            headers=headers,
        )
        assert started.status_code == 200
        authorize_url = started.json()["data"]["authorize_url"]
        state = parse_qs(urlparse(authorize_url).query)["state"][0]
        assert fake_client.authorize_requests[-1]["redirect_uri"] == (
            "http://localhost:8000/api/auth/dingtalk/bind/callback"
        )

        callback = client.get(
            f"/api/auth/dingtalk/bind/callback?code=ok&state={state}",
            follow_redirects=False,
        )
        assert callback.status_code == 302
        assert parse_qs(urlparse(callback.headers["location"]).query)["dingtalk_bound"] == [
            "true"
        ]

        unbound = client.post("/api/auth/dingtalk/unbind", headers=headers)
        assert unbound.status_code == 200
        assert unbound.json()["data"]["success"] is True

        second_unbind = client.post("/api/auth/dingtalk/unbind", headers=headers)
        assert second_unbind.status_code == 404
    finally:
        restore()


def test_current_user_profile_updates_contact_password_and_binding_status():
    profile = DingTalkProfile(
        avatar_url="https://static.example.com/avatar.png",
        corp_id="corp_allowed",
        display_name="AI Brain Admin DingTalk",
        email="admin.dingtalk@example.com",
        subject="union_admin_profile",
        union_id="union_admin_profile",
    )
    fake_client, restore = _install_dingtalk_test_state(
        profile,
        allowed_corp_ids="corp_allowed",
    )
    try:
        login = client.post(
            "/api/auth/login",
            json={"password": "admin123", "username": "admin@example.com"},
        )
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        initial_profile = client.get("/api/auth/profile", headers=headers)
        assert initial_profile.status_code == 200
        initial_data = initial_profile.json()["data"]
        assert initial_data["email"] == "admin@example.com"
        assert initial_data["mobile"] == ""
        assert initial_data["dingtalk_binding"] == {"bound": False}

        started = client.post(
            "/api/auth/dingtalk/bind/start?redirect=/account/profile",
            headers=headers,
        )
        assert started.status_code == 200
        state = parse_qs(urlparse(started.json()["data"]["authorize_url"]).query)["state"][0]
        assert fake_client.authorize_requests[-1]["redirect_uri"] == (
            "http://localhost:8000/api/auth/dingtalk/bind/callback"
        )
        callback = client.get(
            f"/api/auth/dingtalk/bind/callback?code=ok&state={state}",
            follow_redirects=False,
        )
        assert callback.status_code == 302
        assert urlparse(callback.headers["location"]).path == "/account/profile"

        bound_profile = client.get("/api/auth/profile", headers=headers).json()["data"]
        assert bound_profile["dingtalk_binding"]["bound"] is True
        assert bound_profile["dingtalk_binding"]["display_name"] == "AI Brain Admin DingTalk"
        assert "provider_subject" not in bound_profile["dingtalk_binding"]

        contact_update = client.patch(
            "/api/auth/profile",
            json={
                "display_name": "AI Brain Owner",
                "mobile": "+86 13800000000",
            },
            headers=headers,
        )
        assert contact_update.status_code == 200
        assert contact_update.json()["data"]["user"]["display_name"] == "AI Brain Owner"
        assert contact_update.json()["data"]["user"]["mobile"] == "+86 13800000000"
        assert "access_token" not in contact_update.json()["data"]

        missing_password = client.patch(
            "/api/auth/profile",
            json={"email": "admin.renamed@example.com"},
            headers=headers,
        )
        assert missing_password.status_code == 400
        assert missing_password.json()["detail"]["code"] == "VALIDATION_ERROR"

        wrong_password = client.patch(
            "/api/auth/profile",
            json={
                "current_password": "wrong-password",
                "email": "admin.renamed@example.com",
            },
            headers=headers,
        )
        assert wrong_password.status_code == 403
        assert wrong_password.json()["detail"]["code"] == "CURRENT_PASSWORD_INVALID"

        duplicate_email = client.patch(
            "/api/auth/profile",
            json={
                "current_password": "admin123",
                "email": "reviewer@example.com",
            },
            headers=headers,
        )
        assert duplicate_email.status_code == 409
        assert duplicate_email.json()["detail"]["code"] == "USER_EXISTS"

        secure_update = client.patch(
            "/api/auth/profile",
            json={
                "current_password": "admin123",
                "email": "admin.renamed@example.com",
                "new_password": "new-admin-secret",
            },
            headers=headers,
        )
        assert secure_update.status_code == 200
        secure_data = secure_update.json()["data"]
        assert secure_data["access_token"]
        assert secure_data["user"]["email"] == "admin.renamed@example.com"
        assert secure_data["user"]["username"] == "admin.renamed@example.com"

        old_login = client.post(
            "/api/auth/login",
            json={"password": "admin123", "username": "admin@example.com"},
        )
        assert old_login.status_code == 401
        new_login = client.post(
            "/api/auth/login",
            json={
                "password": "new-admin-secret",
                "username": "admin.renamed@example.com",
            },
        )
        assert new_login.status_code == 200

        profile_events = [
            event
            for event in app.state.store.audit_events
            if event["event_type"] == "auth.profile.updated"
        ]
        assert profile_events[-1]["payload"] == {
            "changed_fields": ["email", "password"]
        }
        assert "new-admin-secret" not in str(profile_events)
    finally:
        restore()


def test_dingtalk_bind_rejects_identity_bound_to_another_user():
    profile = DingTalkProfile(
        corp_id="corp_allowed",
        display_name="AI Brain Reviewer",
        subject="union_reviewer",
        union_id="union_reviewer",
    )
    _fake_client, restore = _install_dingtalk_test_state(
        profile,
        allowed_corp_ids="corp_allowed",
    )
    try:
        app.state.external_identity_repository.upsert_identity(
            provider="dingtalk",
            provider_subject="union_reviewer",
            profile=profile.identity_profile(),
            user_id="user_reviewer",
        )
        login = client.post(
            "/api/auth/login",
            json={"password": "admin123", "username": "admin@example.com"},
        )
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        started = client.post(
            "/api/auth/dingtalk/bind/start?redirect=/welcome",
            headers=headers,
        )
        state = parse_qs(urlparse(started.json()["data"]["authorize_url"]).query)["state"][0]
        callback = client.get(
            f"/api/auth/dingtalk/bind/callback?code=ok&state={state}",
            follow_redirects=False,
        )
        assert callback.status_code == 302
        assert parse_qs(urlparse(callback.headers["location"]).query)[
            "dingtalk_bind_error"
        ] == ["EXTERNAL_IDENTITY_CONFLICT"]
        identity = app.state.external_identity_repository.find_active(
            "dingtalk",
            "union_reviewer",
        )
        assert identity["user_id"] == "user_reviewer"
    finally:
        restore()


def test_dingtalk_bound_identity_can_login_without_auto_provision():
    profile = DingTalkProfile(
        corp_id="corp_allowed",
        display_name="绑定用户",
        subject="union_bound",
        union_id="union_bound",
    )
    user_repository = MemoryUserRepository(
        {
            "bound@example.com": {
                "display_name": "绑定用户",
                "id": "user_bound",
                "password_hash": hash_password("bound-secret", salt="bound-user-salt"),
                "roles": ["reviewer"],
                "status": "active",
                "username": "bound@example.com",
            }
        }
    )
    _fake_client, restore = _install_dingtalk_test_state(
        profile,
        allowed_corp_ids="corp_allowed",
        user_repository=user_repository,
    )
    try:
        app.state.external_identity_repository.upsert_identity(
            provider="dingtalk",
            provider_subject="union_bound",
            profile=profile.identity_profile(),
            user_id="user_bound",
        )
        _location, state = _start_dingtalk_login("/welcome")
        callback = client.get(
            f"/api/auth/dingtalk/callback?code=ok&state={state}",
            follow_redirects=False,
        )
        ticket = parse_qs(urlparse(callback.headers["location"]).query)["ticket"][0]
        exchanged = client.post(
            "/api/auth/dingtalk/exchange-ticket",
            json={"ticket": ticket},
        )
        assert exchanged.status_code == 200
        assert exchanged.json()["data"]["user"]["id"] == "user_bound"
    finally:
        restore()
