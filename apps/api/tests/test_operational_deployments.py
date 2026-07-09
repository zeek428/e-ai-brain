from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_ready_deployment_context(headers: dict[str, str]) -> dict[str, str]:
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "deploy-product", "name": "部署产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v-deploy", "name": "部署版本"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "完成测试后进入运维部署。",
            "product_id": product["id"],
            "title": "部署链路需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    app.state.store.requirements[requirement["id"]]["status"] = "ready_for_release"
    return {
        "product_id": product["id"],
        "requirement_id": requirement["id"],
        "version_id": version["id"],
    }


def _create_deployment(headers: dict[str, str], context: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/api/devops/deployments",
        json={
            "environment": "prod",
            "product_id": context["product_id"],
            "requirement_ids": [context["requirement_id"]],
            "risk_level": "medium",
            "rollback_plan": "回滚到上一稳定版本。",
            "title": "生产部署",
            "version_id": context["version_id"],
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_deployment_success_moves_requirement_to_released():
    headers = auth_headers()
    context = _create_ready_deployment_context(headers)
    deployment = _create_deployment(headers, context)

    assert deployment["status"] == "pending_ops"
    assert deployment["requirement_ids"] == [context["requirement_id"]]

    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={"external_job_name": "prod-deploy", "external_build_id": "build-100"},
        headers=headers,
    ).json()["data"]
    assert started["status"] == "deploying"
    assert started["runs"][0]["status"] == "running"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "deploying"

    completed = client.post(
        f"/api/devops/deployments/{deployment['id']}/complete",
        json={"status": "success", "external_build_id": "build-100"},
        headers=headers,
    ).json()["data"]

    assert completed["status"] == "succeeded"
    assert completed["runs"][0]["status"] == "success"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "released"


def test_deployment_failure_reopens_requirement_and_creates_bug():
    headers = auth_headers()
    context = _create_ready_deployment_context(headers)
    deployment = _create_deployment(headers, context)
    client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={"external_job_name": "prod-deploy", "external_build_id": "build-101"},
        headers=headers,
    )

    failed = client.post(
        f"/api/devops/deployments/{deployment['id']}/complete",
        json={
            "failure_reason": "健康检查失败",
            "status": "failed",
            "external_build_id": "build-101",
        },
        headers=headers,
    ).json()["data"]

    assert failed["status"] == "failed"
    assert failed["runs"][0]["status"] == "failed"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "ready_for_release"

    bugs = client.get(
        "/api/bugs?source=deployment_failure",
        headers=headers,
    ).json()["data"]["items"]
    assert len(bugs) == 1
    assert bugs[0]["requirement_id"] == context["requirement_id"]
    assert bugs[0]["source"] == "deployment_failure"
    assert bugs[0]["status"] == "open"
    assert bugs[0]["evidence"]["deployment_request_id"] == deployment["id"]
