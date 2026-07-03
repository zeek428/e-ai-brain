from __future__ import annotations

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
