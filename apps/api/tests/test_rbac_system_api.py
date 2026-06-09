from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.repositories.authorization import CompatibilityAuthorizationRepository
from app.core.users import MemoryUserRepository
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rbac_repositories():
    original_user_repository = app.state.user_repository
    original_authorization_repository = app.state.authorization_repository
    app.state.user_repository = MemoryUserRepository.seeded()
    app.state.authorization_repository = CompatibilityAuthorizationRepository()
    yield
    app.state.user_repository = original_user_repository
    app.state.authorization_repository = original_authorization_repository


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    login_response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_role_update_permissions_disable_and_enable():
    headers = auth_headers()

    created = client.post(
        "/api/system/roles",
        headers=headers,
        json={
            "code": "delivery_operator",
            "name": "Delivery Operator",
            "description": "Can operate delivery queues.",
            "category": "delivery",
        },
    )
    assert created.status_code == 200
    role = created.json()["data"]
    assert role["code"] == "delivery_operator"
    assert role["status"] == "active"

    permissions = client.put(
        f"/api/system/roles/{role['id']}/permissions",
        headers=headers,
        json={"permission_codes": ["task.read", "bug.read"]},
    )
    assert permissions.status_code == 200
    assert permissions.json()["data"]["permission_codes"] == ["bug.read", "task.read"]

    disabled = client.post(f"/api/system/roles/{role['id']}/disable", headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["data"]["status"] == "inactive"

    enabled = client.post(f"/api/system/roles/{role['id']}/enable", headers=headers)
    assert enabled.status_code == 200
    assert enabled.json()["data"]["status"] == "active"


def test_non_admin_gets_403_on_role_create():
    response = client.post(
        "/api/system/roles",
        headers=auth_headers("reviewer@example.com", "reviewer123"),
        json={"code": "forbidden_role", "name": "Forbidden"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_system_role_disable_returns_409_system_role_protected():
    admin_role = client.get("/api/system/roles/admin", headers=auth_headers()).json()["data"]

    response = client.post(
        f"/api/system/roles/{admin_role['id']}/disable",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SYSTEM_ROLE_PROTECTED"


def test_role_menu_grants_return_updated_menu_codes():
    headers = auth_headers()
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "menu_operator", "name": "Menu Operator"},
    ).json()["data"]

    response = client.put(
        f"/api/system/roles/{role['id']}/menus",
        headers=headers,
        json={"menu_codes": ["workspace.dashboard", "task", "task.center"]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["menu_codes"] == [
        "task",
        "task.center",
        "workspace.dashboard",
    ]


def test_mutating_role_operation_writes_role_change_and_audit_events():
    headers = auth_headers()

    response = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "audited_role", "name": "Audited Role"},
    )

    assert response.status_code == 200
    repository = app.state.authorization_repository
    assert repository.role_change_events[-1]["event_type"] == "role.created"
    assert repository.role_change_events[-1]["actor_id"] == "user_admin"
    assert repository.audit_events[-1]["event_type"] == "system.role.created"
    assert repository.audit_events[-1]["subject_id"] == response.json()["data"]["id"]


def test_user_role_scope_update_and_user_permissions_endpoint():
    headers = auth_headers()
    created_user = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "delivery-user@example.com",
            "display_name": "Delivery User",
            "password": "delivery123",
            "roles": ["viewer"],
            "status": "active",
        },
    ).json()["data"]
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "scoped_delivery", "name": "Scoped Delivery"},
    ).json()["data"]
    client.put(
        f"/api/system/roles/{role['id']}/permissions",
        headers=headers,
        json={"permission_codes": ["task.read", "bug.read"]},
    )

    role_response = client.put(
        f"/api/users/{created_user['id']}/roles",
        headers=headers,
        json={"role_codes": ["scoped_delivery"]},
    )
    assert role_response.status_code == 200
    assert role_response.json()["data"]["role_codes"] == ["scoped_delivery"]

    scope_response = client.put(
        f"/api/users/{created_user['id']}/scopes",
        headers=headers,
        json={
            "scopes": [
                {
                    "scope_type": "product",
                    "scope_id": "product_alpha",
                    "access_level": "write",
                }
            ]
        },
    )
    assert scope_response.status_code == 200

    effective = client.get(
        f"/api/users/{created_user['id']}/permissions",
        headers=headers,
    )

    assert effective.status_code == 200
    assert effective.json()["data"]["role_codes"] == ["scoped_delivery"]
    assert effective.json()["data"]["permission_codes"] == ["bug.read", "task.read"]
    assert effective.json()["data"]["scopes"] == [
        {
            "scope_type": "product",
            "scope_id": "product_alpha",
            "access_level": "write",
        }
    ]
