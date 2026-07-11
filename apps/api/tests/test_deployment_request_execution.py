from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def create_context(headers: dict[str, str], code: str) -> dict[str, str]:
    product = client.post(
        "/api/products",
        json={"code": code, "name": f"部署产品-{code}"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "版本 1"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "完成测试后部署。",
            "product_id": product["id"],
            "title": "部署需求",
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


def create_deployment(
    headers: dict[str, str],
    context: dict[str, str],
    *,
    scheme_id: str | None = None,
) -> dict:
    payload = {
        "environment": "prod",
        "product_id": context["product_id"],
        "requirement_ids": [context["requirement_id"]],
        "risk_level": "medium",
        "rollback_plan": "回滚到上一稳定版本。",
        "title": "生产部署",
        "version_id": context["version_id"],
    }
    if scheme_id is not None:
        payload["deployment_scheme_id"] = scheme_id
    response = client.post("/api/devops/deployments", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_runner_scheme(headers: dict[str, str], context: dict[str, str]) -> tuple[dict, str]:
    runner_token = "deployment-runner-token"
    runner_response = client.post(
        "/api/system/ai-executor-runners",
        json={
            "capabilities": ["deployment"],
            "executor_types": ["codex"],
            "name": "部署 Runner",
            "runner_token": runner_token,
        },
        headers=headers,
    )
    assert runner_response.status_code == 200, runner_response.text
    runner = runner_response.json()["data"]
    heartbeat = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        json={
            "metadata": {
                "deployment_targets": [
                    {
                        "code": "production-compose",
                        "method": "docker",
                        "name": "生产 Docker Compose",
                        "ready": True,
                    }
                ]
            }
        },
        headers={"X-Runner-Token": runner_token},
    )
    assert heartbeat.status_code == 200, heartbeat.text
    scheme_response = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "prod-docker",
            "deployment_method": "docker",
            "environment": "prod",
            "name": "生产 Docker 部署",
            "product_id": context["product_id"],
            "runner_id": runner["id"],
            "target_code": "production-compose",
        },
        headers=headers,
    )
    assert scheme_response.status_code == 200, scheme_response.text
    return scheme_response.json()["data"], runner_token


def test_deployment_request_resolves_default_scheme_and_freezes_snapshot():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "default-scheme")

    deployment = create_deployment(headers, context)

    assert deployment["deployment_scheme_id"]
    assert deployment["deployment_method"] == "manual"
    assert deployment["executor_channel"] == "manual"
    assert deployment["scheme_snapshot"]["name"] == "默认人工部署"
    assert "created_by" not in deployment["scheme_snapshot"]


def test_deployment_request_keeps_scheme_snapshot_after_scheme_update():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "frozen-scheme")
    created = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "manual-green",
            "deployment_method": "manual",
            "environment": "prod",
            "name": "绿区人工部署",
            "product_id": context["product_id"],
        },
        headers=headers,
    ).json()["data"]
    deployment = create_deployment(headers, context, scheme_id=created["id"])

    update = client.patch(
        f"/api/devops/deployment-schemes/{created['id']}",
        json={"name": "绿区人工发布", "version": created["version"]},
        headers=headers,
    )
    assert update.status_code == 200
    listed = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"]

    persisted = next(item for item in listed if item["id"] == deployment["id"])
    assert persisted["scheme_snapshot"]["name"] == "绿区人工部署"


def test_start_is_idempotent_and_manual_cancel_finishes_immediately():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "manual-idempotent")
    deployment = create_deployment(headers, context)

    first = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )
    second = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["data"]["runs"]) == 1
    assert second.json()["data"]["runs"][0]["executor_channel"] == "manual"

    cancelled = client.post(
        f"/api/devops/deployments/{deployment['id']}/cancel",
        json={"reason": "人工终止"},
        headers=headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"
    assert cancelled.json()["data"]["runs"][0]["status"] == "cancelled"


def test_runner_cancel_waits_for_external_confirmation():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "runner-cancel")
    scheme, runner_token = create_runner_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )
    assert started.status_code == 200
    run = started.json()["data"]["runs"][0]
    assert run["status"] == "queued"
    assert run["executor_channel"] == "runner"
    assert run["runner_task_id"]
    runner_task = app.state.store.ai_executor_tasks[run["runner_task_id"]]
    assert runner_task["deployment_run_id"] == run["id"]
    assert runner_task["input_payload"]["target_code"] == "production-compose"

    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["data"]["task"]["status"] == "claimed"

    cancelled = client.post(
        f"/api/devops/deployments/{deployment['id']}/cancel",
        json={"reason": "等待 Runner 停止"},
        headers=headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelling"
    assert cancelled.json()["data"]["runs"][0]["status"] == "cancelling"
    assert app.state.store.ai_executor_tasks[run["runner_task_id"]]["status"] == "cancel_requested"

    confirmed = client.post(
        f"/api/system/ai-executor-tasks/{run['runner_task_id']}/complete",
        json={
            "error_code": "AI_EXECUTOR_TASK_CANCELLED",
            "error_message": "Deployment cancelled by platform request",
            "runner_id": scheme["runner_id"],
            "status": "cancelled",
        },
        headers={"X-Runner-Token": runner_token},
    )
    assert confirmed.status_code == 200, confirmed.text
    persisted = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert persisted["status"] == "cancelled"
    assert persisted["runs"][0]["status"] == "cancelled"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "ready_for_release"


def test_runner_success_syncs_logs_and_releases_requirement():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "runner-success")
    scheme, runner_token = create_runner_scheme(headers, context)
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]
    run = started["runs"][0]
    manual_completion = client.post(
        f"/api/devops/deployments/{deployment['id']}/complete",
        json={"status": "success"},
        headers=headers,
    )
    assert manual_completion.status_code == 409
    assert manual_completion.json()["detail"]["code"] == "DEPLOYMENT_RESULT_MANAGED_EXTERNALLY"
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    logs = client.post(
        f"/api/system/ai-executor-tasks/{run['runner_task_id']}/logs",
        json={
            "logs": [{"level": "info", "message": "Docker services are healthy"}],
            "runner_id": scheme["runner_id"],
            "status": "running",
        },
        headers={"X-Runner-Token": runner_token},
    )
    assert logs.status_code == 200, logs.text
    completed = client.post(
        f"/api/system/ai-executor-tasks/{run['runner_task_id']}/complete",
        json={
            "logs": [{"level": "info", "message": "Deployment completed"}],
            "result_json": {"deployment_method": "docker", "exit_code": 0},
            "runner_id": scheme["runner_id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": runner_token},
    )
    assert completed.status_code == 200, completed.text

    persisted = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert persisted["status"] == "succeeded"
    assert persisted["runs"][0]["status"] == "success"
    assert [item["message"] for item in persisted["runs"][0]["logs"]] == [
        "Docker services are healthy",
        "Deployment completed",
    ]
    log_response = client.get(
        f"/api/devops/deployments/{deployment['id']}/runs/{run['id']}/logs",
        headers=headers,
    )
    assert log_response.status_code == 200, log_response.text
    log_items = log_response.json()["data"]["items"]
    assert [item["message"] for item in log_items] == [
        "Docker services are healthy",
        "Deployment completed",
    ]
    assert {item["source"] for item in log_items} == {"runner"}
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "released"
