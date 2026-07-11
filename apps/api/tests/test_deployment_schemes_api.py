from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def login_headers(username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def create_product(headers: dict[str, str], *, code: str = "deployment-product") -> dict:
    response = client.post(
        "/api/products",
        json={"code": code, "name": "部署方案产品"},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_product_creation_adds_default_manual_deployment_scheme():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)

    response = client.get(
        f"/api/devops/deployment-schemes?product_id={product['id']}",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == 1
    scheme = body["items"][0]
    assert scheme["code"] == "default-manual-prod"
    assert scheme["config"] == {}
    assert scheme["created_by"] == "user_admin"
    assert scheme["deployment_method"] == "manual"
    assert scheme["environment"] == "prod"
    assert scheme["executor_channel"] == "manual"
    assert scheme["is_default"] is True
    assert scheme["name"] == "默认人工部署"
    assert scheme["product_id"] == product["id"]
    assert scheme["status"] == "active"
    assert scheme["timeout_seconds"] == 1800
    assert scheme["version"] == 1


def test_deployment_jenkins_connection_candidates_hide_authentication_config():
    app.state.store.reset()
    headers = auth_headers()
    app.state.store.integration_plugins["plugin_jenkins"] = {
        "code": "jenkins",
        "id": "plugin_jenkins",
        "name": "Jenkins",
        "status": "active",
    }
    app.state.store.plugin_connections["connection_jenkins"] = {
        "auth_config": {"password_ref": "env:JENKINS_TOKEN", "username": "deploy"},
        "environment": "prod",
        "id": "connection_jenkins",
        "name": "生产 Jenkins",
        "plugin_id": "plugin_jenkins",
        "status": "active",
    }

    response = client.get("/api/devops/deployment-jenkins-connections", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {
        "items": [
            {
                "environment": "prod",
                "id": "connection_jenkins",
                "name": "生产 Jenkins",
                "ready": True,
                "status": "active",
            }
        ],
        "total": 1,
    }


def test_deployment_resource_candidates_require_scheme_management_permission():
    app.state.store.reset()
    admin_headers = auth_headers()
    username = "deployment-reader@example.com"
    password = "deployment-reader-123"
    created = client.post(
        "/api/users",
        json={
            "display_name": "Deployment Reader",
            "password": password,
            "roles": ["tester"],
            "username": username,
        },
        headers=admin_headers,
    )
    assert created.status_code == 200, created.text
    reader_headers = login_headers(username, password)

    runner_targets = client.get(
        "/api/devops/deployment-runner-targets",
        headers=reader_headers,
    )
    jenkins_connections = client.get(
        "/api/devops/deployment-jenkins-connections",
        headers=reader_headers,
    )

    assert runner_targets.status_code == 403
    assert jenkins_connections.status_code == 403


def test_runner_scheme_requires_runner_and_target_binding():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)

    response = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "prod-ssh",
            "deployment_method": "ssh",
            "environment": "prod",
            "name": "生产 SSH 部署",
            "product_id": product["id"],
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_runner_scheme_rejects_runner_without_deployment_capability():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, code="runner-capability")
    runner = client.post(
        "/api/system/ai-executor-runners",
        json={
            "capabilities": [],
            "executor_types": ["codex"],
            "name": "仅研发 Runner",
        },
        headers=headers,
    ).json()["data"]

    response = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "prod-docker",
            "deployment_method": "docker",
            "environment": "prod",
            "name": "生产 Docker 部署",
            "product_id": product["id"],
            "runner_id": runner["id"],
            "target_code": "production-compose",
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DEPLOYMENT_RUNNER_UNAVAILABLE"


def test_scheme_update_uses_optimistic_version_and_switches_default():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    default_scheme = client.get(
        f"/api/devops/deployment-schemes?product_id={product['id']}",
        headers=headers,
    ).json()["data"]["items"][0]

    created_response = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "manual-blue",
            "deployment_method": "manual",
            "environment": "prod",
            "is_default": True,
            "name": "蓝区人工部署",
            "product_id": product["id"],
        },
        headers=headers,
    )
    assert created_response.status_code == 200
    created = created_response.json()["data"]
    assert created["is_default"] is True

    listed = client.get(
        f"/api/devops/deployment-schemes?product_id={product['id']}",
        headers=headers,
    ).json()["data"]["items"]
    existing_default = next(item for item in listed if item["id"] == default_scheme["id"])
    assert existing_default["is_default"] is False
    assert existing_default["version"] == default_scheme["version"] + 1

    updated_response = client.patch(
        f"/api/devops/deployment-schemes/{created['id']}",
        json={"name": "蓝区人工发布", "version": created["version"]},
        headers=headers,
    )
    assert updated_response.status_code == 200
    updated = updated_response.json()["data"]
    assert updated["name"] == "蓝区人工发布"
    assert updated["version"] == created["version"] + 1

    stale_update = client.patch(
        f"/api/devops/deployment-schemes/{created['id']}",
        json={"name": "过期修改", "version": created["version"]},
        headers=headers,
    )
    assert stale_update.status_code == 409
    assert stale_update.json()["detail"]["code"] == "VERSION_CONFLICT"


def test_active_default_scheme_requires_replacement_before_disabling():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, code="default-scheme-guard")
    default_scheme = client.get(
        f"/api/devops/deployment-schemes?product_id={product['id']}",
        headers=headers,
    ).json()["data"]["items"][0]

    response = client.patch(
        f"/api/devops/deployment-schemes/{default_scheme['id']}",
        json={"status": "disabled", "version": default_scheme["version"]},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DEFAULT_SCHEME_REQUIRED"


def test_referenced_deployment_scheme_cannot_be_deleted():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    scheme = client.get(
        f"/api/devops/deployment-schemes?product_id={product['id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    app.state.store.deployment_requests["deployment_request_001"] = {
        "id": "deployment_request_001",
        "deployment_scheme_id": scheme["id"],
        "product_id": product["id"],
    }

    response = client.delete(
        f"/api/devops/deployment-schemes/{scheme['id']}",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "RESOURCE_IN_USE"
