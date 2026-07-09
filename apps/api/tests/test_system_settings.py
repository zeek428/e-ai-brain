from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.core.repositories.authorization import CompatibilityAuthorizationRepository
from app.core.users import MemoryUserRepository
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_system_settings_dependencies():
    original_user_repository = app.state.user_repository
    original_authorization_repository = app.state.authorization_repository
    app.state.user_repository = MemoryUserRepository.seeded()
    app.state.authorization_repository = CompatibilityAuthorizationRepository()
    app.state.store.reset()
    yield
    app.state.store.reset()
    app.state.user_repository = original_user_repository
    app.state.authorization_repository = original_authorization_repository


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def sensitive_config_confirmation() -> dict[str, object]:
    return {"confirmed": True, "reason": "测试确认变更邮件发送配置"}


def test_admin_can_update_system_admin_email_and_audit_event_is_recorded():
    headers = auth_headers()

    initial = client.get("/api/system/settings", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["data"]["admin_email_configured"] is False

    updated = client.patch(
        "/api/system/settings",
        headers=headers,
        json={"admin_email": "ops@example.com"},
    )
    assert updated.status_code == 200
    payload = updated.json()["data"]
    assert payload["admin_email"] == "ops@example.com"
    assert payload["admin_email_configured"] is True
    assert payload["updated_by"] == "user_admin"

    reloaded = client.get("/api/system/settings", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["data"]["admin_email"] == "ops@example.com"

    assert app.state.store.audit_events[-1]["event_type"] == "system.settings.updated"
    assert app.state.store.audit_events[-1]["payload"] == {
        "admin_email_configured": True,
        "changed_fields": ["admin_email"],
    }


def test_admin_can_configure_email_delivery_without_returning_secret():
    headers = auth_headers()

    updated = client.patch(
        "/api/system/settings",
        headers=headers,
        json={
            "admin_email": "ops@example.com",
            "high_risk_confirmation": sensitive_config_confirmation(),
            "email_delivery": {
                "default_from": "noreply@example.com",
                "enabled": True,
                "reply_to": "support@example.com",
                "sender_email": "noreply@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_password": "super-secret-password",
                "smtp_port": 465,
                "smtp_secret_ref": "",
                "smtp_tls": "ssl",
                "smtp_username": "noreply@example.com",
            },
        },
    )
    assert updated.status_code == 200
    payload = updated.json()["data"]
    assert payload["email_delivery_configured"] is True
    assert payload["email_delivery"]["smtp_password_configured"] is True
    assert "smtp_password" not in payload["email_delivery"]

    reloaded = client.get("/api/system/settings", headers=headers)
    assert reloaded.status_code == 200
    reloaded_payload = reloaded.json()["data"]
    assert reloaded_payload["email_delivery"]["smtp_password_configured"] is True
    assert "smtp_password" not in reloaded_payload["email_delivery"]

    retained = client.patch(
        "/api/system/settings",
        headers=headers,
        json={
            "admin_email": "ops@example.com",
            "high_risk_confirmation": sensitive_config_confirmation(),
            "email_delivery": {
                "default_from": "noreply@example.com",
                "enabled": True,
                "reply_to": "support@example.com",
                "sender_email": "noreply@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_secret_ref": "",
                "smtp_tls": "starttls",
                "smtp_username": "noreply@example.com",
            },
        },
    )
    assert retained.status_code == 200
    assert retained.json()["data"]["email_delivery"]["smtp_password_configured"] is True

    audit_payload = app.state.store.audit_events[-1]["payload"]
    assert audit_payload == {
        "admin_email_configured": True,
        "changed_fields": ["admin_email", "email_delivery"],
        "email_delivery_configured": True,
        "sensitive_config_confirmation": {
            "changed_sensitive_fields": ["smtp_port", "smtp_tls"],
            "confirmed": True,
            "reason_configured": True,
        },
        "smtp_password_configured": True,
        "smtp_secret_ref_configured": False,
    }
    assert "super-secret-password" not in json.dumps(
        app.state.store.audit_events[-1],
        ensure_ascii=False,
    )


def test_email_delivery_sensitive_changes_require_confirmation_without_secret_echo():
    headers = auth_headers()
    audit_event_count = len(app.state.store.audit_events)

    response = client.patch(
        "/api/system/settings",
        headers=headers,
        json={
            "admin_email": "ops@example.com",
            "email_delivery": {
                "default_from": "noreply@example.com",
                "enabled": True,
                "sender_email": "noreply@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_password": "super-secret-password",
                "smtp_port": 465,
                "smtp_tls": "ssl",
                "smtp_username": "noreply@example.com",
            },
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "SENSITIVE_CONFIG_CONFIRMATION_REQUIRED"
    assert "smtp_password" in detail["changed_sensitive_fields"]
    assert "super-secret-password" not in json.dumps(detail, ensure_ascii=False)
    assert len(app.state.store.audit_events) == audit_event_count
    assert client.get("/api/system/settings", headers=headers).json()["data"][
        "email_delivery_configured"
    ] is False


def test_email_delivery_test_uses_smtp_configuration_without_echoing_secret(monkeypatch):
    headers = auth_headers()
    client.patch(
        "/api/system/settings",
        headers=headers,
        json={
            "admin_email": "ops@example.com",
            "high_risk_confirmation": sensitive_config_confirmation(),
            "email_delivery": {
                "default_from": "noreply@example.com",
                "enabled": True,
                "reply_to": "support@example.com",
                "sender_email": "noreply@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_password": "super-secret-password",
                "smtp_port": 465,
                "smtp_tls": "ssl",
                "smtp_username": "noreply@example.com",
            },
        },
    )

    calls: list[dict[str, object]] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append({"host": host, "port": port, "timeout": timeout})

        def __enter__(self) -> FakeSMTP:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            calls.append({"password": password, "username": username})

        def send_message(self, message: object) -> None:
            calls.append(
                {
                    "from": message["From"],
                    "message_id": message["Message-ID"],
                    "subject": message["Subject"],
                    "reply_to": message["Reply-To"],
                    "to": message["To"],
                }
            )

    monkeypatch.setattr("app.services.system_settings.smtplib.SMTP_SSL", FakeSMTP)

    response = client.post(
        "/api/system/settings/email/test",
        headers=headers,
        json={"recipient_email": "qa@example.com"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["delivery_status"] == "sent"
    assert payload["recipient_email"] == "qa@example.com"
    assert payload["smtp_host"] == "smtp.example.com"
    assert payload["smtp_port"] == 465
    assert payload["smtp_tls"] == "ssl"
    assert payload["message_id"].endswith("@example.com>")
    assert payload["message_subject"].startswith("[AI Brain] 邮件发送配置测试 ")
    assert payload["sent_at"]
    assert {"host": "smtp.example.com", "port": 465, "timeout": 15} in calls
    assert {"password": "super-secret-password", "username": "noreply@example.com"} in calls
    sent_call = next(call for call in calls if call.get("to") == "qa@example.com")
    assert sent_call["from"] == "noreply@example.com"
    assert sent_call["reply_to"] == "support@example.com"
    assert str(sent_call["subject"]).startswith("[AI Brain] 邮件发送配置测试 ")
    assert str(sent_call["message_id"]).endswith("@example.com>")
    assert "super-secret-password" not in json.dumps(payload, ensure_ascii=False)


def test_email_delivery_test_uses_saved_test_recipient_by_default(monkeypatch):
    headers = auth_headers()
    updated = client.patch(
        "/api/system/settings",
        headers=headers,
        json={
            "admin_email": "ops@example.com",
            "test_recipient_email": "qa-default@example.com",
            "high_risk_confirmation": sensitive_config_confirmation(),
            "email_delivery": {
                "default_from": "noreply@example.com",
                "enabled": True,
                "sender_email": "noreply@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_password": "super-secret-password",
                "smtp_port": 465,
                "smtp_tls": "ssl",
                "smtp_username": "noreply@example.com",
            },
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["test_recipient_email"] == "qa-default@example.com"
    assert updated.json()["data"]["test_recipient_email_configured"] is True

    calls: list[dict[str, object]] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append({"host": host, "port": port, "timeout": timeout})

        def __enter__(self) -> FakeSMTP:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            calls.append({"password": password, "username": username})

        def send_message(self, message: object) -> None:
            calls.append({"to": message["To"]})

    monkeypatch.setattr("app.services.system_settings.smtplib.SMTP_SSL", FakeSMTP)

    response = client.post(
        "/api/system/settings/email/test",
        headers=headers,
        json={},
    )

    assert response.status_code == 200
    assert response.json()["data"]["recipient_email"] == "qa-default@example.com"
    assert {"to": "qa-default@example.com"} in calls


def test_email_delivery_test_returns_stable_error_for_network_failures(monkeypatch):
    headers = auth_headers()
    client.patch(
        "/api/system/settings",
        headers=headers,
        json={
            "admin_email": "ops@example.com",
            "high_risk_confirmation": sensitive_config_confirmation(),
            "email_delivery": {
                "default_from": "noreply@example.com",
                "enabled": True,
                "sender_email": "noreply@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_password": "super-secret-password",
                "smtp_port": 465,
                "smtp_tls": "ssl",
                "smtp_username": "noreply@example.com",
            },
        },
    )

    class BrokenSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            raise ConnectionResetError("connection reset by peer")

    monkeypatch.setattr("app.services.system_settings.smtplib.SMTP_SSL", BrokenSMTP)

    response = client.post(
        "/api/system/settings/email/test",
        headers=headers,
        json={"recipient_email": "qa@example.com"},
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["code"] == "EMAIL_DELIVERY_TEST_FAILED"
    assert detail["error_type"] == "ConnectionResetError"
    assert "super-secret-password" not in json.dumps(detail, ensure_ascii=False)


def test_email_delivery_test_fails_when_smtp_refuses_recipient(monkeypatch):
    headers = auth_headers()
    client.patch(
        "/api/system/settings",
        headers=headers,
        json={
            "admin_email": "ops@example.com",
            "high_risk_confirmation": sensitive_config_confirmation(),
            "email_delivery": {
                "default_from": "noreply@example.com",
                "enabled": True,
                "sender_email": "noreply@example.com",
                "smtp_host": "smtp.example.com",
                "smtp_password": "super-secret-password",
                "smtp_port": 465,
                "smtp_tls": "ssl",
                "smtp_username": "noreply@example.com",
            },
        },
    )

    class RefusingSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            pass

        def __enter__(self) -> RefusingSMTP:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            return None

        def send_message(self, message: object) -> dict[str, tuple[int, bytes]]:
            return {"qa@example.com": (550, b"recipient rejected")}

    monkeypatch.setattr("app.services.system_settings.smtplib.SMTP_SSL", RefusingSMTP)

    response = client.post(
        "/api/system/settings/email/test",
        headers=headers,
        json={"recipient_email": "qa@example.com"},
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["code"] == "EMAIL_DELIVERY_TEST_FAILED"
    assert detail["error_type"] == "SMTPRecipientsRefused"
    assert detail["refused_recipients"] == ["qa@example.com"]


def test_admin_email_must_be_valid_when_present():
    response = client.patch(
        "/api/system/settings",
        headers=auth_headers(),
        json={"admin_email": "not-an-email"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_non_admin_cannot_read_system_settings():
    response = client.get(
        "/api/system/settings",
        headers=auth_headers("reviewer@example.com", "reviewer123"),
    )
    assert response.status_code == 403
