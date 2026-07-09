from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_viewer_can_read_product_management_without_write_permission():
    app.state.store.reset()
    headers = auth_headers()
    unique = uuid4().hex[:8]
    product = client.post(
        "/api/products",
        json={"code": f"viewer-read-{unique}", "name": "Viewer Read Product"},
        headers=headers,
    ).json()["data"]
    viewer_username = f"viewer-product-{unique}@example.com"
    viewer_password = "viewer123"
    viewer_user = client.post(
        "/api/users",
        json={
            "display_name": "Viewer Product Read",
            "password": viewer_password,
            "roles": ["viewer"],
            "username": viewer_username,
        },
        headers=headers,
    ).json()["data"]
    scope_response = client.put(
        f"/api/users/{viewer_user['id']}/scopes",
        json={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": product["id"],
                    "scope_type": "product",
                }
            ]
        },
        headers=headers,
    )
    assert scope_response.status_code == 200
    viewer_headers = auth_headers(viewer_username, viewer_password)
    try:
        me = client.get("/api/auth/me", headers=viewer_headers).json()["data"]
        assert "product.read" in me["permissions"]
        assert "product.manage" not in me["permissions"]
        menu_codes = {
            child["code"]
            for item in me["menu_tree"]
            for child in item.get("children", [])
        }
        assert "product.products" in menu_codes

        product_list = client.get("/api/products", headers=viewer_headers)
        assert product_list.status_code == 200
        assert product["id"] in [item["id"] for item in product_list.json()["data"]["items"]]
        product_detail = client.get(f"/api/products/{product['id']}", headers=viewer_headers)
        assert product_detail.status_code == 200
        assert product_detail.json()["data"]["id"] == product["id"]

        denied_create = client.post(
            "/api/products",
            json={"code": f"viewer-write-{unique}", "name": "Denied"},
            headers=viewer_headers,
        )
        assert denied_create.status_code == 403
        denied_update = client.patch(
            f"/api/products/{product['id']}",
            json={"name": "Viewer Should Not Update"},
            headers=viewer_headers,
        )
        assert denied_update.status_code == 403
    finally:
        client.delete(f"/api/users/{viewer_user['id']}", headers=headers)


def test_product_members_grant_product_scoped_permissions_and_can_be_revoked():
    app.state.store.reset()
    headers = auth_headers()
    unique = uuid4().hex[:8]
    product = client.post(
        "/api/products",
        json={"code": f"member-scope-{unique}", "name": "成员范围产品"},
        headers=headers,
    ).json()["data"]
    other_product = client.post(
        "/api/products",
        json={"code": f"member-other-{unique}", "name": "其他产品"},
        headers=headers,
    ).json()["data"]
    member_username = f"product-member-{unique}@example.com"
    member_password = "member123"
    member_user = client.post(
        "/api/users",
        json={
            "display_name": "Product Member",
            "password": member_password,
            "roles": ["viewer"],
            "username": member_username,
        },
        headers=headers,
    ).json()["data"]

    try:
        updated = client.put(
            f"/api/products/{product['id']}/members",
            json={
                "members": [
                    {"member_role": "developer", "user_id": member_user["id"]},
                ]
            },
            headers=headers,
        )
        assert updated.status_code == 200
        updated_payload = updated.json()["data"]
        assert updated_payload["revision"]
        member_rows = updated_payload["items"]
        assert member_rows[0]["display_name"] == "Product Member"
        assert member_rows[0]["member_role_label"] == "开发工程师"

        member_headers = auth_headers(member_username, member_password)
        me = client.get("/api/auth/me", headers=member_headers).json()["data"]
        assert "product.read" in me["permissions"]
        assert "task.execute" in me["permissions"]
        assert {
            "access_level": "write",
            "scope_id": product["id"],
            "scope_type": "product",
        } in me["scope_summary"]
        menu_codes = {
            child["code"]
            for item in me["menu_tree"]
            for child in item.get("children", [])
        }
        assert "product.products" in menu_codes
        assert "task.center" in menu_codes

        visible_products = client.get("/api/products", headers=member_headers).json()["data"]
        assert [item["id"] for item in visible_products["items"]] == [product["id"]]
        assert other_product["id"] not in [item["id"] for item in visible_products["items"]]

        revoked = client.put(
            f"/api/products/{product['id']}/members",
            json={"members": []},
            headers=headers,
        )
        assert revoked.status_code == 200
        assert revoked.json()["data"]["items"] == []
        refreshed_me = client.get("/api/auth/me", headers=member_headers).json()["data"]
        assert {
            "access_level": "write",
            "scope_id": product["id"],
            "scope_type": "product",
        } not in refreshed_me["scope_summary"]
        empty_products = client.get("/api/products", headers=member_headers).json()["data"]
        assert empty_products["items"] == []
    finally:
        client.delete(f"/api/users/{member_user['id']}", headers=headers)


def test_product_owner_member_can_manage_members_inside_assigned_product():
    app.state.store.reset()
    headers = auth_headers()
    unique = uuid4().hex[:8]
    product = client.post(
        "/api/products",
        json={"code": f"member-owner-{unique}", "name": "成员经理产品"},
        headers=headers,
    ).json()["data"]
    owner_username = f"product-owner-member-{unique}@example.com"
    developer_username = f"developer-member-{unique}@example.com"
    owner_user = client.post(
        "/api/users",
        json={
            "display_name": "Scoped Product Owner",
            "password": "owner123",
            "roles": ["viewer"],
            "username": owner_username,
        },
        headers=headers,
    ).json()["data"]
    developer_user = client.post(
        "/api/users",
        json={
            "display_name": "Scoped Developer",
            "password": "developer123",
            "roles": ["viewer"],
            "username": developer_username,
        },
        headers=headers,
    ).json()["data"]

    try:
        client.put(
            f"/api/products/{product['id']}/members",
            json={
                "members": [
                    {"member_role": "product_owner", "user_id": owner_user["id"]},
                ]
            },
            headers=headers,
        )
        owner_headers = auth_headers(owner_username, "owner123")
        empty_candidates = client.get(
            f"/api/products/{product['id']}/member-candidates",
            headers=owner_headers,
        )
        assert empty_candidates.status_code == 200
        assert empty_candidates.json()["data"]["items"] == []

        candidates = client.get(
            f"/api/products/{product['id']}/member-candidates?keyword=developer",
            headers=owner_headers,
        )
        assert candidates.status_code == 200
        assert developer_user["id"] in [
            item["id"] for item in candidates.json()["data"]["items"]
        ]

        before_members = client.get(
            f"/api/products/{product['id']}/members",
            headers=owner_headers,
        ).json()["data"]
        managed = client.put(
            f"/api/products/{product['id']}/members",
            json={
                "expected_revision": before_members["revision"],
                "members": [
                    {"member_role": "product_owner", "user_id": owner_user["id"]},
                    {"member_role": "developer", "user_id": developer_user["id"]},
                ]
            },
            headers=owner_headers,
        )
        assert managed.status_code == 200
        assert {item["member_role"] for item in managed.json()["data"]["items"]} == {
            "developer",
            "product_owner",
        }
        stale = client.put(
            f"/api/products/{product['id']}/members",
            json={
                "expected_revision": before_members["revision"],
                "members": [
                    {"member_role": "product_owner", "user_id": owner_user["id"]},
                ],
            },
            headers=owner_headers,
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "PRODUCT_MEMBERS_CONFLICT"
    finally:
        client.delete(f"/api/users/{developer_user['id']}", headers=headers)
        client.delete(f"/api/users/{owner_user['id']}", headers=headers)


def _create_requirement_and_task(
    headers: dict[str, str],
    *,
    product: dict[str, str],
    suffix: str,
) -> tuple[dict[str, str], dict[str, str]]:
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": f"v-{suffix}", "name": f"版本 {suffix}"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": f"产品范围权限验证 {suffix}",
            "product_id": product["id"],
            "title": f"产品范围需求 {suffix}",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    return requirement, task


def test_product_member_permissions_are_limited_to_assigned_product_business_data():
    app.state.store.reset()
    headers = auth_headers()
    unique = uuid4().hex[:8]
    product = client.post(
        "/api/products",
        json={"code": f"scope-a-{unique}", "name": "授权产品"},
        headers=headers,
    ).json()["data"]
    other_product = client.post(
        "/api/products",
        json={"code": f"scope-b-{unique}", "name": "未授权产品"},
        headers=headers,
    ).json()["data"]
    requirement, task = _create_requirement_and_task(
        headers,
        product=product,
        suffix=f"a-{unique}",
    )
    other_requirement, other_task = _create_requirement_and_task(
        headers,
        product=other_product,
        suffix=f"b-{unique}",
    )
    bug = client.post(
        "/api/bugs",
        json={
            "description": "授权产品 Bug",
            "product_id": product["id"],
            "severity": "major",
            "source": "manual_test",
            "title": "授权产品 Bug",
        },
        headers=headers,
    ).json()["data"]
    other_bug = client.post(
        "/api/bugs",
        json={
            "description": "未授权产品 Bug",
            "product_id": other_product["id"],
            "severity": "major",
            "source": "manual_test",
            "title": "未授权产品 Bug",
        },
        headers=headers,
    ).json()["data"]
    owner_username = f"scoped-owner-{unique}@example.com"
    developer_username = f"scoped-developer-{unique}@example.com"
    owner_user = client.post(
        "/api/users",
        json={
            "display_name": "Scoped Owner",
            "password": "owner123",
            "roles": ["viewer"],
            "username": owner_username,
        },
        headers=headers,
    ).json()["data"]
    developer_user = client.post(
        "/api/users",
        json={
            "display_name": "Scoped Developer",
            "password": "developer123",
            "roles": ["viewer"],
            "username": developer_username,
        },
        headers=headers,
    ).json()["data"]

    try:
        client.put(
            f"/api/products/{product['id']}/members",
            json={
                "members": [
                    {"member_role": "product_owner", "user_id": owner_user["id"]},
                    {"member_role": "developer", "user_id": developer_user["id"]},
                ]
            },
            headers=headers,
        )
        owner_headers = auth_headers(owner_username, "owner123")
        developer_headers = auth_headers(developer_username, "developer123")

        allowed_requirement = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=owner_headers,
        )
        assert allowed_requirement.status_code == 200
        denied_requirement = client.get(
            f"/api/requirements/{other_requirement['id']}",
            headers=owner_headers,
        )
        assert denied_requirement.status_code == 404

        denied_create_requirement = client.post(
            "/api/requirements",
            json={
                "content": "不应能跨产品创建需求。",
                "product_id": other_product["id"],
                "title": "跨产品创建需求",
            },
            headers=owner_headers,
        )
        assert denied_create_requirement.status_code == 404
        denied_approve_requirement = client.post(
            f"/api/requirements/{other_requirement['id']}/approve",
            json={},
            headers=owner_headers,
        )
        assert denied_approve_requirement.status_code == 404

        visible_tasks = client.get("/api/ai-tasks", headers=developer_headers).json()["data"]
        assert task["task_id"] in [item["id"] for item in visible_tasks["items"]]
        assert other_task["task_id"] not in [item["id"] for item in visible_tasks["items"]]
        denied_task_detail = client.get(
            f"/api/ai-tasks/{other_task['task_id']}",
            headers=developer_headers,
        )
        assert denied_task_detail.status_code == 403
        denied_task_start = client.post(
            f"/api/ai-tasks/{other_task['task_id']}/start",
            headers=developer_headers,
        )
        assert denied_task_start.status_code == 403

        visible_bugs = client.get("/api/bugs", headers=developer_headers).json()["data"]
        assert bug["id"] in [item["id"] for item in visible_bugs["items"]]
        assert other_bug["id"] not in [item["id"] for item in visible_bugs["items"]]
        denied_create_bug = client.post(
            "/api/bugs",
            json={
                "description": "不应能跨产品登记 Bug。",
                "product_id": other_product["id"],
                "severity": "major",
                "source": "manual_test",
                "title": "跨产品 Bug",
            },
            headers=developer_headers,
        )
        assert denied_create_bug.status_code == 404
        denied_patch_bug = client.patch(
            f"/api/bugs/{other_bug['id']}",
            json={"title": "不应能跨产品编辑 Bug"},
            headers=developer_headers,
        )
        assert denied_patch_bug.status_code == 404
    finally:
        client.delete(f"/api/users/{developer_user['id']}", headers=headers)
        client.delete(f"/api/users/{owner_user['id']}", headers=headers)


def test_product_config_supports_list_patch_and_active_filters():
    app.state.store.reset()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={
            "code": "ai-brain",
            "name": "AI Brain",
            "description": "企业 AI 大脑平台",
            "owner_team": "rd",
            "display_order": 100,
        },
        headers=headers,
    ).json()["data"]
    related_system = client.post(
        "/api/system/related-systems",
        json={
            "code": "billing",
            "name": "计费系统",
            "owner_team": "business-platform",
            "product_id": product["id"],
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    assert related_system["product_id"] == product["id"]
    related_systems = client.get(
        f"/api/system/related-systems?product_id={product['id']}",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in related_systems["items"]] == [related_system["id"]]

    inactive = client.post(
        "/api/products",
        json={"code": "legacy", "name": "Legacy", "status": "inactive"},
        headers=headers,
    ).json()["data"]

    product_list = client.get("/api/products?active_only=true", headers=headers).json()["data"]
    assert [item["id"] for item in product_list["items"]] == [product["id"]]
    assert inactive["id"] not in [item["id"] for item in product_list["items"]]

    patched_product = client.patch(
        f"/api/products/{product['id']}",
        json={"name": "Enterprise AI Brain", "status": "active"},
        headers=headers,
    ).json()["data"]
    assert patched_product["name"] == "Enterprise AI Brain"
    assert patched_product["display_order"] == 100

    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1", "status": "active"},
        headers=headers,
    ).json()["data"]
    archived = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "old", "name": "old", "status": "archived"},
        headers=headers,
    ).json()["data"]
    versions = client.get(
        f"/api/products/{product['id']}/versions?active_only=true",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in versions["items"]] == [version["id"]]
    assert archived["id"] not in [item["id"] for item in versions["items"]]

    patched_version = client.patch(
        f"/api/product-versions/{version['id']}",
        json={"release_date": "2026-05-31"},
        headers=headers,
    ).json()["data"]
    assert patched_version["release_date"] == "2026-05-31"

    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "knowledge", "name": "知识中心", "display_order": 10},
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "legacy", "name": "旧模块", "status": "inactive"},
        headers=headers,
    )
    modules = client.get(
        f"/api/products/{product['id']}/modules?active_only=true",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in modules["items"]] == [module["id"]]

    patched_module = client.patch(
        f"/api/product-modules/{module['id']}",
        json={"owner_team": "knowledge-platform"},
        headers=headers,
    ).json()["data"]
    assert patched_module["owner_team"] == "knowledge-platform"

    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "repo_type": "code",
            "name": "ai-brain-api",
            "remote_url": "https://gitlab.internal/rd/ai-brain-api.git",
            "git_provider": "gitlab",
            "credential_ref": "secret://gitlab/readonly",
            "default_branch": "main",
            "root_path": "/",
        },
        headers=headers,
    ).json()["data"]
    assert "credential_ref" not in repository
    assert repository["credential_ref_configured"] is True
    assert repository["project_path"] == "rd/ai-brain-api"
    repositories = client.get(
        f"/api/products/{product['id']}/git-repositories?active_only=true",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in repositories["items"]] == [repository["id"]]
    assert "credential_ref" not in repositories["items"][0]
    assert repositories["items"][0]["credential_ref_configured"] is True

    branch_config = client.post(
        f"/api/product-versions/{version['id']}/branch-configs",
        json={
            "base_branch": "main",
            "branch_status": "active",
            "creation_source": "manual",
            "repository_id": repository["id"],
            "working_branch": "release/2026-v1",
        },
        headers=headers,
    ).json()["data"]
    assert branch_config["product_id"] == product["id"]
    assert branch_config["version_id"] == version["id"]
    assert branch_config["repository_id"] == repository["id"]
    assert branch_config["repository_name"] == "ai-brain-api"
    assert branch_config["working_branch"] == "release/2026-v1"
    branch_configs = client.get(
        f"/api/product-versions/{version['id']}/branch-configs",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in branch_configs["items"]] == [branch_config["id"]]
    patched_branch_config = client.patch(
        f"/api/product-version-branch-configs/{branch_config['id']}",
        json={"branch_status": "testing"},
        headers=headers,
    ).json()["data"]
    assert patched_branch_config["branch_status"] == "testing"

    patched_repository = client.patch(
        f"/api/product-git-repositories/{repository['id']}",
        json={"status": "inactive"},
        headers=headers,
    ).json()["data"]
    assert patched_repository["status"] == "inactive"
    assert "credential_ref" not in patched_repository
    assert patched_repository["credential_ref_configured"] is True
    patched_repository_path = client.patch(
        f"/api/product-git-repositories/{repository['id']}",
        json={"project_path": "rd/ai-brain-explicit"},
        headers=headers,
    ).json()["data"]
    assert patched_repository_path["project_path"] == "rd/ai-brain-explicit"
    patched_repository_remote = client.patch(
        f"/api/product-git-repositories/{repository['id']}",
        json={"remote_url": "https://gitlab.internal/rd/ai-brain-worker.git"},
        headers=headers,
    ).json()["data"]
    assert patched_repository_remote["project_path"] == "rd/ai-brain-worker"
    repositories_after_remote_patch = client.get(
        f"/api/products/{product['id']}/git-repositories?active_only=false",
        headers=headers,
    ).json()["data"]["items"]
    assert repositories_after_remote_patch[0]["project_path"] == "rd/ai-brain-worker"


def test_product_detail_endpoint_returns_single_product():
    app.state.store.reset()
    headers = auth_headers()
    product = client.post(
        "/api/products",
        json={"code": "detail-product", "name": "产品详情"},
        headers=headers,
    ).json()["data"]

    detail = client.get(f"/api/products/{product['id']}", headers=headers)
    missing = client.get("/api/products/product_missing", headers=headers)

    assert detail.status_code == 200
    assert detail.json()["data"] == product
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "NOT_FOUND"


def test_product_list_supports_server_pagination_sort_and_filters():
    app.state.store.reset()
    headers = auth_headers()
    first = client.post(
        "/api/products",
        json={
            "code": "list-a",
            "name": "列表产品 A",
            "owner_team": "growth",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/products/{first['id']}/versions",
        json={"code": "list-a-v1", "name": "列表产品 A 版本", "status": "testing"},
        headers=headers,
    )
    client.post(
        f"/api/products/{first['id']}/modules",
        json={"code": "list-a-module", "name": "列表产品 A 模块", "status": "active"},
        headers=headers,
    )
    second = client.post(
        "/api/products",
        json={
            "code": "list-b",
            "name": "列表产品 B",
            "owner_team": "platform",
            "status": "inactive",
        },
        headers=headers,
    ).json()["data"]

    filtered = client.get(
        "/api/products?owner_team=platform&status=inactive&page=1&page_size=1"
        "&sort_by=code&sort_order=desc",
        headers=headers,
    ).json()["data"]
    invalid_sort = client.get(
        "/api/products?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )

    assert filtered["page"] == 1
    assert filtered["page_size"] == 1
    assert filtered["total"] == 1
    assert [item["id"] for item in filtered["items"]] == [second["id"]]
    assert first["id"] not in [item["id"] for item in filtered["items"]]
    assert invalid_sort.status_code == 400
    assert invalid_sort.json()["detail"]["code"] == "VALIDATION_ERROR"

    projected = client.get(
        "/api/products?code=list-a&page=1&page_size=1",
        headers=headers,
    ).json()["data"]
    assert projected["items"][0]["current_version_name"] == "列表产品 A 版本"
    assert projected["items"][0]["module_count"] == 1


def test_related_systems_are_saved_in_generated_task_product_context():
    app.state.store.reset()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={"code": "context-product", "name": "上下文产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1"},
        headers=headers,
    ).json()["data"]
    client.post(
        "/api/system/related-systems",
        json={
            "code": "crm",
            "name": "CRM 系统",
            "product_id": product["id"],
            "status": "active",
        },
        headers=headers,
    )
    other_product = client.post(
        "/api/products",
        json={"code": "other-context-product", "name": "其他产品"},
        headers=headers,
    ).json()["data"]
    client.post(
        "/api/system/related-systems",
        json={
            "code": "other-crm",
            "name": "其他 CRM",
            "product_id": other_product["id"],
            "status": "active",
        },
        headers=headers,
    )
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "需要把相关系统带入任务上下文",
            "product_id": product["id"],
            "title": "相关系统上下文需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/requirements/{requirement['id']}/approve",
        json={"comment": "进入设计"},
        headers=headers,
    )

    generated = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    task_detail = client.get(
        f"/api/ai-tasks/{generated['task_id']}",
        headers=headers,
    ).json()["data"]

    related_systems = task_detail["product_context"]["related_systems"]["items"]
    assert [item["code"] for item in related_systems] == ["crm"]


def test_generated_task_product_context_does_not_expose_git_credentials():
    app.state.store.reset()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={"code": "context-credential-product", "name": "凭据上下文产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1"},
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "credential_ref": "secret://git/readonly",
            "git_provider": "github",
            "name": "代码仓库",
            "project_path": "org/repo",
            "remote_url": "git@github.com:org/repo.git",
        },
        headers=headers,
    )
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "生成任务上下文时不能泄露 Git 凭据",
            "product_id": product["id"],
            "title": "Git 凭据脱敏需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)

    generated = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    task_detail = client.get(
        f"/api/ai-tasks/{generated['task_id']}",
        headers=headers,
    ).json()["data"]

    repositories = task_detail["product_context"]["repositories"]["items"]
    input_repositories = task_detail["input"]["product_context"]["repositories"]["items"]
    assert repositories[0]["credential_ref_configured"] is True
    assert input_repositories[0]["credential_ref_configured"] is True
    assert "credential_ref" not in repositories[0]
    assert "credential_ref" not in input_repositories[0]


def test_product_config_rejects_duplicate_codes_and_invalid_statuses():
    app.state.store.reset()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={"code": "unique-product", "name": "唯一产品"},
        headers=headers,
    ).json()["data"]
    duplicate_product = client.post(
        "/api/products",
        json={"code": "unique-product", "name": "重复产品"},
        headers=headers,
    )
    assert duplicate_product.status_code == 409
    assert duplicate_product.json()["detail"]["code"] == "PRODUCT_CODE_EXISTS"

    invalid_product_status = client.patch(
        f"/api/products/{product['id']}",
        json={"status": "deleted"},
        headers=headers,
    )
    assert invalid_product_status.status_code == 400
    assert invalid_product_status.json()["detail"]["code"] == "VALIDATION_ERROR"

    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1"},
        headers=headers,
    ).json()["data"]
    duplicate_version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "重复版本"},
        headers=headers,
    )
    assert duplicate_version.status_code == 409
    assert duplicate_version.json()["detail"]["code"] == "PRODUCT_VERSION_CODE_EXISTS"

    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "core", "name": "核心模块"},
        headers=headers,
    ).json()["data"]
    duplicate_module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": module["code"], "name": "重复模块"},
        headers=headers,
    )
    assert duplicate_module.status_code == 409
    assert duplicate_module.json()["detail"]["code"] == "PRODUCT_MODULE_CODE_EXISTS"

    direct_archive = client.patch(
        f"/api/product-versions/{version['id']}",
        json={"status": "archived"},
        headers=headers,
    )
    assert direct_archive.status_code == 409
    assert direct_archive.json()["detail"]["code"] == "PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED"

    for target_status in ["active", "testing", "released", "archived"]:
        advance_response = client.post(
            f"/api/product-versions/{version['id']}/advance-status",
            json={"reason": "验证归档版本校验", "target_status": target_status},
            headers=headers,
        )
        assert advance_response.status_code == 200
        archived = advance_response.json()["data"]["version"]
    assert archived["status"] == "archived"

    requirement = client.post(
        "/api/requirements",
        json={
            "content": "归档版本不能创建需求",
            "product_id": product["id"],
            "title": "归档版本需求",
            "version_id": archived["id"],
        },
        headers=headers,
    )
    assert requirement.status_code == 400
    assert requirement.json()["detail"]["code"] == "PRODUCT_VERSION_ARCHIVED"


def test_related_systems_and_model_gateway_configs_mask_secrets_and_audit_writes():
    app.state.store.reset()
    headers = auth_headers()

    related_system = client.post(
        "/api/system/related-systems",
        json={
            "code": "knowledge",
            "name": "知识中心",
            "description": "文档导入、检索和知识沉淀",
            "owner_team": "rd",
            "display_order": 100,
        },
        headers=headers,
    ).json()["data"]
    patched_system = client.patch(
        f"/api/system/related-systems/{related_system['id']}",
        json={"status": "inactive"},
        headers=headers,
    ).json()["data"]
    assert patched_system["status"] == "inactive"
    assert client.get(
        "/api/system/related-systems?active_only=true",
        headers=headers,
    ).json()["data"]["items"] == []

    config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "name": "默认模型网关",
            "provider": "openai_compatible",
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-secret-value",
            "default_chat_model": "chat-model",
            "default_embedding_model": "embedding-model",
            "timeout_seconds": 60,
            "max_retries": 1,
            "status": "active",
            "is_default": True,
        },
        headers=headers,
    ).json()["data"]
    assert config["api_key_configured"] is True
    assert "api_key" not in config
    assert "api_key_masked" not in config

    second_config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "name": "备用模型网关",
            "provider": "openai_compatible",
            "base_url": "https://backup.example.com/v1",
            "api_key": "backup-secret",
            "default_chat_model": "backup-chat",
            "default_embedding_model": "backup-embedding",
            "is_default": True,
        },
        headers=headers,
    ).json()["data"]
    configs = client.get("/api/system/model-gateway-configs", headers=headers).json()["data"][
        "items"
    ]
    assert [item["id"] for item in configs if item["is_default"]] == [second_config["id"]]
    assert all("api_key" not in item for item in configs)
    assert all("api_key_masked" not in item for item in configs)

    patched_config = client.patch(
        f"/api/system/model-gateway-configs/{second_config['id']}",
        json={"api_key": "rotated-secret", "timeout_seconds": 45},
        headers=headers,
    ).json()["data"]
    assert patched_config["api_key_configured"] is True
    assert "api_key_masked" not in patched_config
    assert patched_config["timeout_seconds"] == 45

    audit_events = client.get("/api/audit/events", headers=headers).json()["data"]["items"]
    assert "related_system.created" in [event["event_type"] for event in audit_events]
    assert "model_gateway_config.updated" in [event["event_type"] for event in audit_events]
    assert "sk-secret-value" not in str(audit_events)
