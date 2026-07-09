from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.repositories.authorization import CompatibilityAuthorizationRepository
from app.core.users import MemoryUserRepository
from app.main import app

client = TestClient(app)


class FakeRoleSummaryPagingRepository(CompatibilityAuthorizationRepository):
    def __init__(self) -> None:
        super().__init__()
        self.count_kwargs: dict[str, object] | None = None
        self.page_kwargs: dict[str, object] | None = None

    def list_roles(self) -> list[dict[str, object]]:  # pragma: no cover - failure path
        raise AssertionError("roles list should use repository count/page read model")

    def count_role_summaries(
        self,
        *,
        business_role: str | None,
        category: str | None,
        menu_scope: str | None,
        permission: str | None,
        role: str | None,
        status: str | None,
    ) -> int:
        self.count_kwargs = {
            "business_role": business_role,
            "category": category,
            "menu_scope": menu_scope,
            "permission": permission,
            "role": role,
            "status": status,
        }
        return 2

    def list_role_summaries_page(
        self,
        *,
        business_role: str | None,
        category: str | None,
        limit: int,
        menu_scope: str | None,
        offset: int,
        permission: str | None,
        role: str | None,
        sort_by: str,
        sort_order: str,
        status: str | None,
    ) -> list[dict[str, object]]:
        self.page_kwargs = {
            "business_role": business_role,
            "category": category,
            "limit": limit,
            "menu_scope": menu_scope,
            "offset": offset,
            "permission": permission,
            "role": role,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "status": status,
        }
        return [
            {
                "id": "role_delivery_operator",
                "code": "delivery_operator",
                "name": "Delivery Operator",
                "description": "Operate delivery.",
                "category": "delivery",
                "is_system": False,
                "is_assignable": True,
                "status": "active",
                "sort_order": 30,
                "permission_codes": ["task.read"],
                "menu_codes": ["task.center"],
                "scopes": [],
                "business_roles": ["交付负责人"],
                "responsibilities": "Operate delivery workflows.",
                "data_scope": "product",
                "decision_scope": "task",
                "menu_scope": ["任务中心"],
                "boundary": "No system config changes.",
            }
        ]


class FakeMenuResourcePagingRepository(CompatibilityAuthorizationRepository):
    def __init__(self) -> None:
        super().__init__()
        self.count_kwargs: dict[str, object] | None = None
        self.page_kwargs: dict[str, object] | None = None

    def menu_resources(self) -> list[dict[str, object]]:  # pragma: no cover - failure path
        raise AssertionError("menu list should use repository count/page read model")

    def count_menu_resources(
        self,
        *,
        menu: str | None,
        menu_type: str | None,
        parent: str | None,
        path: str | None,
        permission: str | None,
        status: str | None,
    ) -> int:
        self.count_kwargs = {
            "menu": menu,
            "menu_type": menu_type,
            "parent": parent,
            "path": path,
            "permission": permission,
            "status": status,
        }
        return 2

    def list_menu_resources_page(
        self,
        *,
        limit: int,
        menu: str | None,
        menu_type: str | None,
        offset: int,
        parent: str | None,
        path: str | None,
        permission: str | None,
        sort_by: str,
        sort_order: str,
        status: str | None,
    ) -> list[dict[str, object]]:
        self.page_kwargs = {
            "limit": limit,
            "menu": menu,
            "menu_type": menu_type,
            "offset": offset,
            "parent": parent,
            "path": path,
            "permission": permission,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "status": status,
        }
        return [
            {
                "code": "system.menus",
                "icon": "MenuOutlined",
                "is_system": True,
                "menu_type": "page",
                "name": "菜单管理",
                "parent_code": "system",
                "path": "/system/menus",
                "required_permissions": ["system.menus.manage"],
                "sort_order": 64,
                "status": "active",
            }
        ]


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


def test_internal_data_source_detail_permission_is_assignable():
    headers = auth_headers()
    permissions_response = client.get("/api/system/permissions", headers=headers)
    assert permissions_response.status_code == 200
    permission_codes = {
        item["code"]
        for item in permissions_response.json()["data"]["items"]
    }
    assert "system.internal_data_source.detail" in permission_codes

    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={
            "code": "internal_data_source_detail_reader",
            "name": "Internal Data Source Detail Reader",
            "category": "system",
        },
    ).json()["data"]
    permissions = client.put(
        f"/api/system/roles/{role['id']}/permissions",
        headers=headers,
        json={"permission_codes": ["system.internal_data_source.detail"]},
    )

    assert permissions.status_code == 200
    assert permissions.json()["data"]["permission_codes"] == [
        "system.internal_data_source.detail",
    ]


def test_system_roles_list_supports_remote_pagination_filters_sort_and_observability():
    headers = auth_headers()
    for code, name in (
        ("delivery_operator_alpha", "Delivery Operator Alpha"),
        ("delivery_operator_beta", "Delivery Operator Beta"),
    ):
        response = client.post(
            "/api/system/roles",
            headers=headers,
            json={
                "code": code,
                "name": name,
                "category": "delivery",
            },
        )
        assert response.status_code == 200

    response = client.get(
        "/api/system/roles",
        headers=headers,
        params={
            "category": "delivery",
            "page": 1,
            "page_size": 1,
            "role": "Delivery Operator",
            "sort_by": "code",
            "sort_order": "desc",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total"] == 2
    assert data["items"][0]["code"] == "delivery_operator_beta"
    assert data["query"]["name"] == "roles"
    assert data["query"]["filters"]["category"] == "delivery"
    assert data["query"]["filters"]["role"] == "Delivery Operator"
    assert data["performance"]["total"] == 2

    business_role_response = client.get(
        "/api/system/roles",
        headers=headers,
        params={"business_role": "平台管理员", "page": 1, "page_size": 10},
    )
    assert business_role_response.status_code == 200
    business_role_data = business_role_response.json()["data"]
    assert business_role_data["total"] == 1
    assert business_role_data["items"][0]["code"] == "admin"
    assert business_role_data["items"][0]["business_roles"] == ["平台管理员"]


def test_system_roles_list_uses_repository_pagination_when_available():
    repository = FakeRoleSummaryPagingRepository()
    original_authorization_repository = app.state.authorization_repository
    app.state.authorization_repository = repository
    try:
        response = client.get(
            "/api/system/roles",
            headers=auth_headers(),
            params={
                "business_role": "交付",
                "category": "delivery",
                "menu_scope": "任务",
                "page": 2,
                "page_size": 1,
                "permission": "task.read",
                "role": "Delivery",
                "sort_by": "code",
                "sort_order": "desc",
                "status": "active",
            },
        )
    finally:
        app.state.authorization_repository = original_authorization_repository

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["page"] == 2
    assert data["page_size"] == 1
    assert data["total"] == 2
    assert data["items"][0]["code"] == "delivery_operator"
    assert data["query"]["name"] == "roles"
    assert data["query"]["filters"] == {
        "business_role": "交付",
        "category": "delivery",
        "menu_scope": "任务",
        "permission": "task.read",
        "role": "Delivery",
        "status": "active",
    }
    assert data["query"]["sort_by"] == "code"
    assert data["query"]["sort_order"] == "desc"
    assert data["performance"]["p95_target_ms"] == 300
    assert repository.count_kwargs == {
        "business_role": "交付",
        "category": "delivery",
        "menu_scope": "任务",
        "permission": "task.read",
        "role": "Delivery",
        "status": "active",
    }
    assert repository.page_kwargs == {
        "business_role": "交付",
        "category": "delivery",
        "limit": 1,
        "menu_scope": "任务",
        "offset": 1,
        "permission": "task.read",
        "role": "Delivery",
        "sort_by": "code",
        "sort_order": "desc",
        "status": "active",
    }


def test_system_roles_list_rejects_unsupported_sort_field():
    response = client.get(
        "/api/system/roles",
        headers=auth_headers(),
        params={"page": 1, "page_size": 10, "sort_by": "permission_codes"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


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


def test_permission_matrix_explains_role_grants_and_menu_permission_gaps():
    headers = auth_headers()
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "matrix_operator", "name": "Matrix Operator"},
    ).json()["data"]
    client.put(
        f"/api/system/roles/{role['id']}/menus",
        headers=headers,
        json={"menu_codes": ["workspace.dashboard"]},
    )

    response = client.get("/api/system/permissions/matrix", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["role_count"] >= 1
    assert data["summary"]["permission_count"] >= 1
    assert data["summary"]["roles_with_menu_permission_gaps"] >= 1
    rows_by_code = {row["role_code"]: row for row in data["rows"]}
    matrix_row = rows_by_code["matrix_operator"]
    assert matrix_row["menu_count"] == 1
    assert matrix_row["permission_count"] == 0
    assert matrix_row["missing_menu_permission_codes"] == ["workspace.read"]
    assert matrix_row["diagnostics"][0]["code"] == "menu_permission_gap"


def test_permission_matrix_enriches_product_and_knowledge_scope_names():
    headers = auth_headers()
    app.state.store.products["product_scope_matrix"] = {
        "code": "AIBRAIN",
        "id": "product_scope_matrix",
        "name": "AI Brain",
        "status": "active",
    }
    app.state.store.knowledge_spaces["knowledge_space_scope_matrix"] = {
        "id": "knowledge_space_scope_matrix",
        "name": "研发知识空间",
        "status": "active",
    }
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "scope_matrix_operator", "name": "Scope Matrix Operator"},
    ).json()["data"]
    client.put(
        f"/api/system/roles/{role['id']}/scopes",
        headers=headers,
        json={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": "product_scope_matrix",
                    "scope_type": "product",
                },
                {
                    "access_level": "write",
                    "scope_id": "knowledge_space_scope_matrix",
                    "scope_type": "knowledge_space",
                },
            ]
        },
    )

    response = client.get("/api/system/permissions/matrix", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    row = {
        current["role_code"]: current
        for current in data["rows"]
    }["scope_matrix_operator"]
    assert row["scope_summary"] == "知识空间 1 项，产品 1 项"
    assert row["scopes"] == [
        {
            "access_level": "write",
            "scope_id": "knowledge_space_scope_matrix",
            "scope_name": "研发知识空间",
            "scope_type": "knowledge_space",
        },
        {
            "access_level": "read",
            "scope_id": "product_scope_matrix",
            "scope_name": "AI Brain",
            "scope_type": "product",
        },
    ]


def test_role_detail_includes_readable_access_preview():
    headers = auth_headers()
    app.state.store.products["product_role_preview"] = {
        "code": "PREVIEW",
        "id": "product_role_preview",
        "name": "预览产品",
        "status": "active",
    }
    app.state.store.knowledge_spaces["knowledge_space_role_preview"] = {
        "id": "knowledge_space_role_preview",
        "name": "预览知识空间",
        "status": "active",
    }
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "role_preview_operator", "name": "Role Preview Operator"},
    ).json()["data"]
    client.put(
        f"/api/system/roles/{role['id']}/menus",
        headers=headers,
        json={"menu_codes": ["knowledge.center", "workspace.dashboard"]},
    )
    client.put(
        f"/api/system/roles/{role['id']}/permissions",
        headers=headers,
        json={"permission_codes": ["knowledge.read"]},
    )
    client.put(
        f"/api/system/roles/{role['id']}/scopes",
        headers=headers,
        json={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": "product_role_preview",
                    "scope_type": "product",
                },
                {
                    "access_level": "write",
                    "scope_id": "knowledge_space_role_preview",
                    "scope_type": "knowledge_space",
                },
            ]
        },
    )

    response = client.get(f"/api/system/roles/{role['id']}", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    preview = data["access_preview"]
    assert preview["role_code"] == "role_preview_operator"
    assert preview["menu_count"] == 2
    assert preview["permission_count"] == 1
    assert preview["scope_count"] == 2
    assert preview["scope_summary"] == "知识空间 1 项，产品 1 项"
    assert preview["missing_menu_permission_codes"] == ["workspace.read"]
    assert preview["diagnostics"][0]["code"] == "menu_permission_gap"
    assert {
        "code": "workspace.dashboard",
        "name": "团队看板",
        "path": "/welcome",
        "required_permissions": ["workspace.read"],
    }.items() <= preview["visible_menus"][0].items()
    assert preview["operation_permissions"] == [
        {
            "category": "knowledge",
            "code": "knowledge.read",
            "description": "",
            "name": "knowledge.read",
            "risk_level": "normal",
            "status": "active",
        }
    ]
    assert preview["scopes"] == [
        {
            "access_level": "write",
            "scope_id": "knowledge_space_role_preview",
            "scope_name": "预览知识空间",
            "scope_type": "knowledge_space",
        },
        {
            "access_level": "read",
            "scope_id": "product_role_preview",
            "scope_name": "预览产品",
            "scope_type": "product",
        },
    ]
    assert [group["scope_type"] for group in preview["scope_groups"]] == [
        "knowledge_space",
        "product",
    ]
    assert preview["scope_groups"][0]["scope_type_label"] == "知识空间"
    assert preview["scope_groups"][1]["scope_type_label"] == "产品"


def test_permission_diagnostics_explains_user_menu_permission_and_scope_blocks():
    headers = auth_headers()
    app.state.store.products["product_alpha"] = {
        "code": "ALPHA",
        "id": "product_alpha",
        "name": "Alpha 产品",
        "status": "active",
    }
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "diagnostic_operator", "name": "Diagnostic Operator"},
    ).json()["data"]
    client.put(
        f"/api/system/roles/{role['id']}/menus",
        headers=headers,
        json={"menu_codes": ["task.center"]},
    )
    client.put(
        f"/api/system/roles/{role['id']}/scopes",
        headers=headers,
        json={
            "scopes": [
                {
                    "scope_type": "product",
                    "scope_id": "product_alpha",
                    "access_level": "read",
                }
            ]
        },
    )
    created_user = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "diagnostic-user@example.com",
            "display_name": "Diagnostic User",
            "password": "diagnostic123",
            "roles": ["viewer"],
            "status": "active",
        },
    ).json()["data"]
    role_response = client.put(
        f"/api/users/{created_user['id']}/roles",
        headers=headers,
        json={"role_codes": ["diagnostic_operator"]},
    )
    assert role_response.status_code == 200

    response = client.get(
        "/api/system/permissions/diagnostics",
        headers=headers,
        params={
            "user_id": created_user["id"],
            "path": "/delivery/rd-tasks",
            "permission_code": "task.read",
            "scope_type": "product",
            "scope_id": "product_beta",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["decision"]["allowed"] is False
    assert "未授予菜单" not in " ".join(data["decision"]["blocked_reasons"])
    assert "缺少菜单权限：task.read" in data["decision"]["blocked_reasons"]
    assert "缺少权限点：task.read" in data["decision"]["blocked_reasons"]
    assert "缺少范围：product:product_beta" in data["decision"]["blocked_reasons"]
    assert data["effective"]["scopes"] == [
        {
            "access_level": "read",
            "scope_id": "product_alpha",
            "scope_name": "Alpha 产品",
            "scope_type": "product",
        }
    ]
    checks = {check["code"]: check for check in data["checks"]}
    assert checks["menu_path"]["status"] == "blocked"
    assert checks["menu_path"]["granted_menu_code"] == "task.center"
    assert checks["menu_path"]["missing_permission_codes"] == ["task.read"]
    assert checks["permission"]["status"] == "blocked"
    assert checks["scope"]["status"] == "blocked"


def test_user_menu_preview_explains_visible_and_blocked_menus():
    headers = auth_headers()
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "menu_preview_operator", "name": "Menu Preview Operator"},
    ).json()["data"]
    client.put(
        f"/api/system/roles/{role['id']}/menus",
        headers=headers,
        json={"menu_codes": ["workspace.dashboard"]},
    )
    created_user = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "menu-preview-user@example.com",
            "display_name": "Menu Preview User",
            "password": "menuPreview123",
            "roles": ["viewer"],
            "status": "active",
        },
    ).json()["data"]
    role_response = client.put(
        f"/api/users/{created_user['id']}/roles",
        headers=headers,
        json={"role_codes": ["menu_preview_operator"]},
    )
    assert role_response.status_code == 200

    response = client.get(
        "/api/system/permissions/menu-preview",
        headers=headers,
        params={"user_id": created_user["id"]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user"]["id"] == created_user["id"]
    assert data["summary"] == {
        "blocked_menu_count": 1,
        "granted_menu_count": 1,
        "visible_menu_count": 0,
    }
    assert data["visible_menus"] == []
    assert data["blocked_menus"] == [
        {
            "code": "workspace.dashboard",
            "message": "菜单已授权，但缺少菜单所需权限点",
            "missing_permission_codes": ["workspace.read"],
            "name": "团队看板",
            "path": "/welcome",
            "reason": "permission_missing",
            "required_permission_codes": ["workspace.read"],
        }
    ]


def test_role_risk_precheck_blocks_menu_permission_gap_and_suggests_fix():
    headers = auth_headers()
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "risk_precheck_operator", "name": "Risk Precheck Operator"},
    ).json()["data"]

    blocked = client.post(
        f"/api/system/roles/{role['id']}/risk-precheck",
        headers=headers,
        json={
            "menu_codes": ["workspace.dashboard"],
            "permission_codes": [],
        },
    )

    assert blocked.status_code == 200
    blocked_data = blocked.json()["data"]
    assert blocked_data["decision"] == {
        "can_save": False,
        "risk_count": 2,
        "status": "blocked",
    }
    assert [risk["code"] for risk in blocked_data["risks"]] == [
        "menu_permission_gap",
        "scope_not_configured",
    ]
    assert blocked_data["risks"][0]["severity"] == "blocked"
    assert blocked_data["auto_fix_suggestions"][0] == {
        "action": "add_permissions",
        "description": "补齐菜单所需权限点，避免菜单可见但接口 Forbidden。",
        "permission_codes": ["workspace.read"],
    }
    assert blocked_data["scope_comparison"]["candidate"] == {}

    warning = client.post(
        f"/api/system/roles/{role['id']}/risk-precheck",
        headers=headers,
        json={
            "menu_codes": ["workspace.dashboard"],
            "permission_codes": ["workspace.read"],
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": "*",
                    "scope_type": "global",
                }
            ],
        },
    )

    assert warning.status_code == 200
    warning_data = warning.json()["data"]
    assert warning_data["decision"] == {
        "can_save": True,
        "risk_count": 0,
        "status": "pass",
    }
    assert warning_data["scope_comparison"]["candidate"] == {
        "global": {"admin": 0, "read": 1, "write": 0}
    }


def test_task_center_contains_ai_jobs_and_plugin_menus():
    response = client.get("/api/system/menus", headers=auth_headers())

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    menus = {item["code"]: item for item in items}
    task_menu_codes = [item["code"] for item in items if item.get("parent_code") == "task"]
    assert task_menu_codes == [
        "system.scheduled_jobs",
        "system.ai_capabilities",
        "system.plugins",
    ]
    assert menus["system.menus"]["parent_code"] == "system"
    assert menus["system.menus"]["path"] == "/system/menus"
    assert menus["system.menus"]["required_permissions"] == ["system.menus.manage"]
    assert menus["system.ai_capabilities"]["parent_code"] == "task"
    assert menus["system.ai_capabilities"]["path"] == "/tasks/ai-capabilities"
    assert menus["system.scheduled_jobs"]["parent_code"] == "task"
    assert menus["system.scheduled_jobs"]["path"] == "/tasks/scheduled-jobs"
    assert menus["system.plugins"]["parent_code"] == "task"
    assert menus["system.plugins"]["path"] == "/tasks/plugins"
    assert menus["system.users"]["parent_code"] == "system"
    assert menus["system.roles"]["parent_code"] == "system"
    assert menus["system.model_gateway"]["parent_code"] == "system"


def test_system_menus_list_uses_repository_pagination_when_requested():
    repository = FakeMenuResourcePagingRepository()
    app.state.authorization_repository = repository

    response = client.get(
        "/api/system/menus",
        headers=auth_headers(),
        params={
            "menu": "菜单",
            "menu_type": "page",
            "page": 2,
            "page_size": 5,
            "parent": "系统",
            "path": "/system",
            "permission": "system.menus",
            "sort_by": "name",
            "sort_order": "desc",
            "status": "active",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"][0]["code"] == "system.menus"
    assert data["page"] == 2
    assert data["page_size"] == 5
    assert data["total"] == 2
    assert data["query"]["name"] == "menus"
    assert data["query"]["sort_by"] == "name"
    assert data["performance"]["total"] == 2
    assert repository.count_kwargs == {
        "menu": "菜单",
        "menu_type": "page",
        "parent": "系统",
        "path": "/system",
        "permission": "system.menus",
        "status": "active",
    }
    assert repository.page_kwargs == {
        **repository.count_kwargs,
        "limit": 5,
        "offset": 5,
        "sort_by": "name",
        "sort_order": "desc",
    }


def test_admin_can_manage_menu_resources_and_reorder():
    headers = auth_headers()

    created = client.post(
        "/api/system/menus",
        headers=headers,
        json={
            "code": "system.demo_menu",
            "icon": "AppstoreOutlined",
            "menu_type": "page",
            "name": "演示菜单",
            "parent_code": "system",
            "path": "/system/demo-menu",
            "required_permissions": ["system.menus.manage"],
            "sort_order": 69,
        },
    )
    assert created.status_code == 200
    menu = created.json()["data"]
    assert menu["code"] == "system.demo_menu"
    assert menu["is_system"] is False
    assert menu["status"] == "active"

    patched = client.patch(
        "/api/system/menus/system.demo_menu",
        headers=headers,
        json={
            "name": "演示菜单配置",
            "required_permissions": ["system.menus.read"],
            "sort_order": 70,
        },
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["name"] == "演示菜单配置"
    assert patched.json()["data"]["required_permissions"] == ["system.menus.read"]

    disabled = client.post("/api/system/menus/system.demo_menu/disable", headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["data"]["status"] == "inactive"

    enabled = client.post("/api/system/menus/system.demo_menu/enable", headers=headers)
    assert enabled.status_code == 200
    assert enabled.json()["data"]["status"] == "active"

    reordered = client.put(
        "/api/system/menus/reorder",
        headers=headers,
        json={"items": [{"code": "system.demo_menu", "sort_order": 68}]},
    )
    assert reordered.status_code == 200
    assert reordered.json()["data"]["items"][0]["sort_order"] == 68

    deleted = client.delete("/api/system/menus/system.demo_menu", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"code": "system.demo_menu", "deleted": True}


def test_system_menu_delete_is_protected():
    response = client.delete("/api/system/menus/system.roles", headers=auth_headers())

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SYSTEM_MENU_PROTECTED"


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


def test_user_management_role_edits_sync_to_effective_rbac_permissions():
    headers = auth_headers()
    role = client.post(
        "/api/system/roles",
        headers=headers,
        json={"code": "assistant_operator", "name": "Assistant Operator"},
    ).json()["data"]
    permissions = client.put(
        f"/api/system/roles/{role['id']}/permissions",
        headers=headers,
        json={"permission_codes": ["assistant.chat"]},
    )
    assert permissions.status_code == 200

    created_user = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "assistant-operator@example.com",
            "display_name": "Assistant Operator",
            "password": "assistant123",
            "roles": ["assistant_operator"],
            "status": "active",
        },
    ).json()["data"]

    effective = client.get(
        f"/api/users/{created_user['id']}/permissions",
        headers=headers,
    )
    assert effective.status_code == 200
    assert effective.json()["data"]["role_codes"] == ["assistant_operator"]
    assert effective.json()["data"]["permission_codes"] == ["assistant.chat"]

    assistant_headers = auth_headers("assistant-operator@example.com", "assistant123")
    runtime_status = client.get("/api/assistant/runtime-status", headers=assistant_headers)
    assert runtime_status.status_code == 200

    patched = client.patch(
        f"/api/users/{created_user['id']}",
        headers=headers,
        json={"roles": ["viewer"]},
    )
    assert patched.status_code == 200

    effective_after_patch = client.get(
        f"/api/users/{created_user['id']}/permissions",
        headers=headers,
    )
    assert effective_after_patch.status_code == 200
    assert effective_after_patch.json()["data"]["role_codes"] == ["viewer"]
    assert "assistant.chat" not in effective_after_patch.json()["data"]["permission_codes"]

    runtime_status_after_patch = client.get(
        "/api/assistant/runtime-status",
        headers=assistant_headers,
    )
    assert runtime_status_after_patch.status_code == 403


def test_last_admin_user_cannot_be_demoted_through_user_management():
    response = client.patch(
        "/api/users/user_admin",
        headers=auth_headers(),
        json={"roles": ["viewer"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LAST_ADMIN_PROTECTED"
