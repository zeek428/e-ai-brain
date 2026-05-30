from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product_context(headers: dict[str, str]) -> dict[str, str]:
    product = client.post(
        "/api/products",
        json={"code": "crud-product", "name": "CRUD 产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1"},
        headers=headers,
    ).json()["data"]
    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "core", "name": "核心模块"},
        headers=headers,
    ).json()["data"]
    return {
        "module_code": module["code"],
        "module_id": module["id"],
        "product_id": product["id"],
        "version_id": version["id"],
    }


def test_product_children_support_full_delete_crud_and_dependency_guards():
    app.state.store.reset()
    headers = auth_headers()
    context = create_product_context(headers)

    blocked_product_delete = client.delete(f"/api/products/{context['product_id']}", headers=headers)
    assert blocked_product_delete.status_code == 409
    assert blocked_product_delete.json()["detail"]["code"] == "RESOURCE_IN_USE"

    repository = client.post(
        f"/api/products/{context['product_id']}/git-repositories",
        json={"name": "core-api", "project_path": "rd/core-api"},
        headers=headers,
    ).json()["data"]
    related = client.post(
        "/api/system/related-systems",
        json={"code": "jira", "name": "Jira"},
        headers=headers,
    ).json()["data"]
    config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "base_url": "https://model.example.com/v1",
            "default_chat_model": "chat",
            "default_embedding_model": "embedding",
            "name": "CRUD 模型网关",
        },
        headers=headers,
    ).json()["data"]

    assert client.delete(f"/api/product-git-repositories/{repository['id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/product-modules/{context['module_id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/product-versions/{context['version_id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/system/related-systems/{related['id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/system/model-gateway-configs/{config['id']}", headers=headers).status_code == 200

    deleted_product = client.delete(f"/api/products/{context['product_id']}", headers=headers)
    assert deleted_product.status_code == 200
    assert deleted_product.json()["data"]["deleted"] is True
    assert client.get("/api/products", headers=headers).json()["data"]["items"] == []


def test_requirements_documents_bugs_and_users_support_update_and_delete():
    app.state.store.reset()
    headers = auth_headers()
    context = create_product_context(headers)

    requirement = client.post(
        "/api/requirements",
        json={
            "content": "初始需求内容",
            "priority": "P1",
            "product_id": context["product_id"],
            "title": "初始需求",
            "version_id": context["version_id"],
        },
        headers=headers,
    ).json()["data"]
    patched_requirement = client.patch(
        f"/api/requirements/{requirement['id']}",
        json={"priority": "P0", "title": "更新后的需求"},
        headers=headers,
    ).json()["data"]
    assert patched_requirement["priority"] == "P0"
    assert patched_requirement["title"] == "更新后的需求"
    assert client.delete(f"/api/requirements/{requirement['id']}", headers=headers).status_code == 200
    assert client.get("/api/requirements", headers=headers).json()["data"]["items"] == []

    document = client.post(
        "/api/knowledge/documents",
        json={
            "content": "知识内容",
            "doc_type": "Spec",
            "permission_roles": ["admin"],
            "tags": ["crud"],
            "title": "初始知识",
        },
        headers=headers,
    ).json()["data"]
    patched_document = client.patch(
        f"/api/knowledge/documents/{document['id']}",
        json={"title": "更新后的知识", "tags": ["crud", "updated"]},
        headers=headers,
    ).json()["data"]
    assert patched_document["title"] == "更新后的知识"
    assert patched_document["tags"] == ["crud", "updated"]
    assert client.delete(f"/api/knowledge/documents/{document['id']}", headers=headers).status_code == 200
    assert client.get("/api/knowledge/documents", headers=headers).json()["data"]["items"] == []

    bug = client.post(
        "/api/bugs",
        json={
            "description": "Bug 描述",
            "module_code": context["module_code"],
            "product_id": context["product_id"],
            "severity": "major",
            "source": "manual_test",
            "title": "初始 Bug",
            "version_id": context["version_id"],
        },
        headers=headers,
    ).json()["data"]
    assert client.delete(f"/api/bugs/{bug['id']}", headers=headers).status_code == 200
    assert client.get("/api/bugs", headers=headers).json()["data"]["items"] == []

    user = client.post(
        "/api/users",
        json={
            "display_name": "CRUD User",
            "password": "crud-secret",
            "roles": ["viewer"],
            "status": "active",
            "username": "crud_user@example.com",
        },
        headers=headers,
    ).json()["data"]
    assert client.delete(f"/api/users/{user['id']}", headers=headers).status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"username": "crud_user@example.com", "password": "crud-secret"},
    )
    assert login.status_code == 401
