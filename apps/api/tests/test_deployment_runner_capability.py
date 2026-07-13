import json
import zipfile
from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_executor_runner_constants import AI_EXECUTOR_TYPES
from app.services.ai_executor_runner_task_context import (
    _ai_executor_task_product_id,
    _ai_executor_task_visible_to_user,
)

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def create_deployment_runner(headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/system/ai-executor-runners",
        json={
            "capabilities": ["deployment"],
            "executor_types": ["codex"],
            "name": "部署 Runner",
            "runner_token": "deployment-runner-token",
            "trust_domain": "deployment",
            "workspace_roots": ["/workspace"],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_deployment_is_a_runner_capability_not_an_ai_executor_type():
    assert "deployment" not in AI_EXECUTOR_TYPES


def test_deployment_runner_task_inherits_product_scope_from_deployment_request():
    store = SimpleNamespace(
        deployment_requests={
            "deployment_request_scope": {
                "id": "deployment_request_scope",
                "product_id": "product_scope",
            }
        },
        deployment_runs={
            "deployment_run_scope": {
                "id": "deployment_run_scope",
                "deployment_request_id": "deployment_request_scope",
            }
        },
    )
    task = {
        "id": "ai_executor_task_scope",
        "deployment_run_id": "deployment_run_scope",
        "executor_type": "deployment",
    }
    scoped_user = {
        "roles": [],
        "permissions": ["system.plugins.manage"],
        "scope_summary": [
            {
                "access_level": "read",
                "scope_id": "product_scope",
                "scope_type": "product",
            }
        ],
    }
    other_product_user = {
        **scoped_user,
        "scope_summary": [
            {
                "access_level": "read",
                "scope_id": "product_other",
                "scope_type": "product",
            }
        ],
    }

    assert _ai_executor_task_product_id(store, task) == "product_scope"
    assert _ai_executor_task_visible_to_user(store, task=task, user=scoped_user) is True
    assert (
        _ai_executor_task_visible_to_user(store, task=task, user=other_product_user)
        is False
    )


def test_runner_package_contains_local_only_deployment_target_template():
    app.state.store.reset()
    headers = auth_headers()
    runner = create_deployment_runner(headers)

    response = client.get(
        f"/api/system/ai-executor-runners/{runner['id']}/install-package"
        "?target_os=manual&arch=universal&install_mode=manual",
        headers=headers,
    )
    assert response.status_code == 200
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        config = json.loads(archive.read("runner_config.json").decode("utf-8"))
        env_text = archive.read("ai-brain-runner.env").decode("utf-8")
        runner_agent = archive.read("runner_agent.py").decode("utf-8")

    assert config["runner"]["capabilities"] == ["deployment"]
    assert config["deployment_targets"] == {}
    assert "AI_BRAIN_CAPABILITIES=deployment" in env_text
    assert "DEPLOYMENT_TARGETS" in runner_agent
    assert "deployment_targets" in runner_agent


def test_heartbeat_sanitizes_deployment_target_metadata():
    app.state.store.reset()
    headers = auth_headers()
    runner = create_deployment_runner(headers)

    heartbeat = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        json={
            "metadata": {
                "deployment_targets": [
                    {
                        "code": "production-compose",
                        "name": "生产 Docker Compose",
                        "method": "docker",
                        "ready": True,
                        "host": "secret.internal",
                        "identity_file": "/secret/id_ed25519",
                        "working_directory": "/srv/private",
                    }
                ]
            }
        },
        headers={"X-Runner-Token": "deployment-runner-token"},
    )
    assert heartbeat.status_code == 200, heartbeat.text
    targets = heartbeat.json()["data"]["metadata"]["deployment_targets"]
    assert targets == [
        {
            "code": "production-compose",
            "method": "docker",
            "name": "生产 Docker Compose",
            "ready": True,
        }
    ]

    listed = client.get(
        f"/api/devops/deployment-runner-targets?runner_id={runner['id']}&method=docker",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"] == {
        "items": [
            {
                "code": "production-compose",
                "method": "docker",
                "name": "生产 Docker Compose",
                "ready": True,
                "runner_id": runner["id"],
            }
        ],
        "total": 1,
    }


def test_offline_runner_is_not_available_for_deployment_schemes():
    app.state.store.reset()
    headers = auth_headers()
    product = client.post(
        "/api/products",
        json={"code": "offline-runner", "name": "离线 Runner 产品"},
        headers=headers,
    ).json()["data"]
    runner = create_deployment_runner(headers)
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
        headers={"X-Runner-Token": "deployment-runner-token"},
    )
    assert heartbeat.status_code == 200, heartbeat.text
    app.state.store.ai_executor_runners[runner["id"]]["last_heartbeat_at"] = (
        "2020-01-01T00:00:00+00:00"
    )

    listed = client.get(
        f"/api/devops/deployment-runner-targets?runner_id={runner['id']}",
        headers=headers,
    )
    created = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "offline-docker",
            "deployment_method": "docker",
            "environment": "prod",
            "name": "离线 Docker 部署",
            "product_id": product["id"],
            "runner_id": runner["id"],
            "target_code": "production-compose",
        },
        headers=headers,
    )

    assert listed.status_code == 200
    assert listed.json()["data"]["items"] == []
    assert created.status_code == 409
    assert created.json()["detail"]["code"] == "DEPLOYMENT_RUNNER_UNAVAILABLE"


def test_coding_runner_is_not_available_for_deployment_schemes():
    app.state.store.reset()
    headers = auth_headers()
    product = client.post(
        "/api/products",
        json={"code": "coding-runner", "name": "编码 Runner 产品"},
        headers=headers,
    ).json()["data"]
    runner = client.post(
        "/api/system/ai-executor-runners",
        json={
            "capabilities": ["deployment"],
            "executor_types": ["codex"],
            "name": "编码 Runner",
            "runner_token": "coding-runner-token",
            "trust_domain": "coding",
        },
        headers=headers,
    ).json()["data"]
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
        headers={"X-Runner-Token": "coding-runner-token"},
    )
    assert heartbeat.status_code == 200, heartbeat.text

    listed = client.get(
        f"/api/devops/deployment-runner-targets?runner_id={runner['id']}",
        headers=headers,
    )
    created = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "coding-docker",
            "deployment_method": "docker",
            "environment": "prod",
            "name": "编码 Docker 部署",
            "product_id": product["id"],
            "runner_id": runner["id"],
            "target_code": "production-compose",
        },
        headers=headers,
    )

    assert listed.json()["data"]["items"] == []
    assert created.status_code == 409
    assert created.json()["detail"]["code"] == "DEPLOYMENT_RUNNER_UNAVAILABLE"


def test_deployment_capable_runner_can_claim_deployment_task():
    app.state.store.reset()
    headers = auth_headers()
    runner = create_deployment_runner(headers)
    app.state.store.ai_executor_tasks["ai_executor_task_deploy"] = {
        "id": "ai_executor_task_deploy",
        "runner_id": runner["id"],
        "executor_type": "deployment",
        "instruction": "execute configured deployment target",
        "workspace_root": "",
        "timeout_seconds": 1800,
        "input_payload": {"target_code": "production-compose"},
        "request_config": {},
        "result_json": {},
        "logs": [],
        "status": "queued",
        "created_by": "user_admin",
        "created_at": "2026-07-11T00:00:00+00:00",
        "updated_at": "2026-07-11T00:00:00+00:00",
    }

    response = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": runner["id"]},
        headers={"X-Runner-Token": "deployment-runner-token"},
    )

    assert response.status_code == 200, response.text
    task = response.json()["data"]["task"]
    assert task["id"] == "ai_executor_task_deploy"
    assert task["executor_type"] == "deployment"
    assert task["status"] == "claimed"
