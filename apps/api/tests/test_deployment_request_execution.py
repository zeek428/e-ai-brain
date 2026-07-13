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


def create_runner_scheme(
    headers: dict[str, str],
    context: dict[str, str],
    *,
    rollback_config: dict | None = None,
    rollout_strategy: str = "all_at_once",
    wave_config: dict | None = None,
    health_probe_configured: bool | None = None,
) -> tuple[dict, str]:
    if health_probe_configured is None:
        health_probe_configured = rollout_strategy != "all_at_once"
    runner_token = "deployment-runner-token"
    runner_response = client.post(
        "/api/system/ai-executor-runners",
        json={
            "capabilities": ["deployment"],
            "executor_types": ["codex"],
            "name": "部署 Runner",
            "runner_token": runner_token,
            "trust_domain": "deployment",
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
                        "health_check_configured": health_probe_configured,
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
            "health_check_config": {"required": True}
            if health_probe_configured
            else {},
            "name": "生产 Docker 部署",
            "product_id": context["product_id"],
            "rollback_config": rollback_config or {},
            "rollout_strategy": rollout_strategy,
            "wave_config": wave_config or {},
            "runner_id": runner["id"],
            "target_code": "production-compose",
            "window_enforcement": "warn",
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
    assert [step["step_type"] for step in run["steps"]] == [
        "preflight",
        "deploy",
        "health_check",
        "smoke_test",
        "rollback",
    ]
    assert started["dispatch_events"][0]["status"] == "completed"
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


def test_strict_deployment_window_blocks_start_outside_window():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "strict-window")
    scheme = client.post(
        "/api/devops/deployment-schemes",
        json={
            "code": "strict-manual",
            "deployment_method": "manual",
            "environment": "prod",
            "name": "严格窗口人工部署",
            "product_id": context["product_id"],
            "window_enforcement": "strict",
        },
        headers=headers,
    ).json()["data"]
    deployment_response = client.post(
        "/api/devops/deployments",
        json={
            "deploy_window_end": "2026-01-01T02:00:00Z",
            "deploy_window_start": "2026-01-01T01:00:00Z",
            "deployment_scheme_id": scheme["id"],
            "environment": "prod",
            "product_id": context["product_id"],
            "requirement_ids": [context["requirement_id"]],
            "rollback_plan": "人工回滚",
            "title": "窗口外部署",
            "version_id": context["version_id"],
        },
        headers=headers,
    )
    assert deployment_response.status_code == 200
    deployment = deployment_response.json()["data"]

    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )

    assert started.status_code == 409
    assert started.json()["detail"]["code"] == "DEPLOYMENT_WINDOW_CLOSED"
    assert not app.state.store.deployment_runs
    assert not app.state.store.execution_outbox_events


def test_canary_rollout_dispatches_second_wave_before_release():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "canary-rollout")
    scheme, runner_token = create_runner_scheme(
        headers,
        context,
        rollout_strategy="canary",
    )
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]
    first_run = started["runs"][0]
    assert first_run["wave_number"] == 1
    assert first_run["wave_total"] == 2
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{first_run['runner_task_id']}/complete",
        json={
            "result_json": {
                "health_checks": [{"code": "api", "passed": True}],
                "health_status": "passed",
                "operation": "deploy",
                "wave_number": 1,
                "wave_total": 2,
            },
            "runner_id": scheme["runner_id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": runner_token},
    )
    after_first = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert after_first["status"] == "deploying"
    assert after_first["current_wave"] == 2
    assert len(after_first["runs"]) == 2
    second_run = after_first["runs"][0]
    assert second_run["wave_number"] == 2
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{second_run['runner_task_id']}/complete",
        json={
            "result_json": {
                "health_checks": [{"code": "api", "passed": True}],
                "health_status": "passed",
                "operation": "deploy",
                "wave_number": 2,
                "wave_total": 2,
            },
            "runner_id": scheme["runner_id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": runner_token},
    )
    completed = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert completed["status"] == "succeeded"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == "released"


def test_multiwave_start_requires_a_configured_health_probe() -> None:
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "multiwave-health-config")
    scheme, _ = create_runner_scheme(
        headers,
        context,
        rollout_strategy="canary",
        health_probe_configured=False,
    )
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])

    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    )

    assert started.status_code == 409
    assert started.json()["detail"]["code"] == "DEPLOYMENT_PREFLIGHT_FAILED"
    assert "post_deploy_health_ready" in started.json()["detail"]["failed_checks"]


def test_failed_health_check_queues_real_runner_rollback():
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "auto-rollback")
    scheme, runner_token = create_runner_scheme(
        headers,
        context,
        rollback_config={
            "auto_on_failure": True,
            "enabled": True,
            "strategy": "target_command",
        },
    )
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]
    deploy_run = started["runs"][0]
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{deploy_run['runner_task_id']}/complete",
        json={
            "error_code": "DEPLOYMENT_HEALTH_CHECK_FAILED",
            "error_message": "health check failed",
            "result_json": {
                "health_checks": [{"code": "api", "passed": False}],
                "health_status": "failed",
                "operation": "deploy",
            },
            "runner_id": scheme["runner_id"],
            "status": "failed",
        },
        headers={"X-Runner-Token": runner_token},
    )
    rolling_back = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert rolling_back["status"] == "rolling_back"
    rollback_run = rolling_back["runs"][0]
    assert rollback_run["operation"] == "rollback"
    rollback_task = app.state.store.ai_executor_tasks[rollback_run["runner_task_id"]]
    assert rollback_task["input_payload"]["operation"] == "rollback"
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{rollback_run['runner_task_id']}/complete",
        json={
            "result_json": {"health_status": "passed", "operation": "rollback"},
            "runner_id": scheme["runner_id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": runner_token},
    )
    rolled_back = client.get(
        f"/api/devops/deployments?product_id={context['product_id']}",
        headers=headers,
    ).json()["data"]["items"][0]
    assert rolled_back["status"] == "rolled_back"
    assert app.state.store.requirements[context["requirement_id"]]["status"] == (
        "ready_for_release"
    )


def test_batch_rollout_dispatches_every_configured_wave() -> None:
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "batch-rollout")
    scheme, runner_token = create_runner_scheme(
        headers,
        context,
        rollout_strategy="batch",
        wave_config={
            "waves": [
                {"name": "第一批", "traffic_percent": 25},
                {"name": "第二批", "traffic_percent": 60},
                {"name": "全量", "traffic_percent": 100},
            ]
        },
    )
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])
    current = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]

    for expected_wave in (1, 2, 3):
        run = current["runs"][0]
        assert run["wave_number"] == expected_wave
        client.post(
            "/api/system/ai-executor-tasks/claim",
            json={"runner_id": scheme["runner_id"]},
            headers={"X-Runner-Token": runner_token},
        )
        completed = client.post(
            f"/api/system/ai-executor-tasks/{run['runner_task_id']}/complete",
            json={
                "result_json": {
                    "health_checks": [{"code": "api", "passed": True}],
                    "health_status": "passed",
                    "operation": "deploy",
                    "wave_number": expected_wave,
                    "wave_total": 3,
                },
                "runner_id": scheme["runner_id"],
                "status": "succeeded",
            },
            headers={"X-Runner-Token": runner_token},
        )
        assert completed.status_code == 200, completed.text
        current = client.get(
            f"/api/devops/deployments/{deployment['id']}",
            headers=headers,
        ).json()["data"]

    assert current["status"] == "succeeded"
    assert len(current["runs"]) == 3


def test_batch_rollout_does_not_advance_without_health_evidence() -> None:
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "batch-health-gate")
    scheme, runner_token = create_runner_scheme(
        headers,
        context,
        rollout_strategy="batch",
        wave_config={
            "waves": [
                {"name": "第一批", "traffic_percent": 25},
                {"name": "全量", "traffic_percent": 100},
            ]
        },
    )
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])
    started = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]
    first_run = started["runs"][0]
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )

    completed = client.post(
        f"/api/system/ai-executor-tasks/{first_run['runner_task_id']}/complete",
        json={
            "result_json": {"operation": "deploy"},
            "runner_id": scheme["runner_id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": runner_token},
    )

    assert completed.status_code == 200, completed.text
    current = client.get(
        f"/api/devops/deployments/{deployment['id']}",
        headers=headers,
    ).json()["data"]
    assert current["status"] == "waiting_takeover"
    assert len(current["runs"]) == 1
    assert current["runs"][0]["health_status"] == "unhealthy"


def test_blue_green_final_wave_requires_and_records_traffic_switch() -> None:
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "blue-green-rollout")
    scheme, runner_token = create_runner_scheme(
        headers,
        context,
        rollout_strategy="blue_green",
        wave_config={
            "active_slot": "blue",
            "rollback_action": "target.blue_green_rollback",
            "switch_action": "target.blue_green_switch",
            "target_slot": "green",
        },
    )
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])
    current = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]
    first_run = current["runs"][0]
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{first_run['runner_task_id']}/complete",
        json={
            "result_json": {
                "health_checks": [{"code": "api", "passed": True}],
                "health_status": "passed",
                "operation": "deploy",
            },
            "runner_id": scheme["runner_id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": runner_token},
    )
    current = client.get(
        f"/api/devops/deployments/{deployment['id']}", headers=headers
    ).json()["data"]
    final_run = current["runs"][0]
    final_task = app.state.store.ai_executor_tasks[final_run["runner_task_id"]]
    assert final_task["input_payload"]["wave"]["action"] == "traffic_switch"
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{final_run['runner_task_id']}/complete",
        json={
            "result_json": {
                "health_checks": [{"code": "api", "passed": True}],
                "health_status": "passed",
                "operation": "deploy",
                "traffic_switch_action": "target.blue_green_switch",
                "traffic_switch_attempted": True,
                "traffic_switch_passed": True,
            },
            "runner_id": scheme["runner_id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": runner_token},
    )
    completed = client.get(
        f"/api/devops/deployments/{deployment['id']}", headers=headers
    ).json()["data"]
    traffic_step = next(
        step for step in completed["runs"][0]["steps"] if step["step_type"] == "traffic_switch"
    )
    assert completed["status"] == "succeeded"
    assert traffic_step["status"] == "passed"


def test_failed_runner_rollback_creates_critical_incident_and_takeover() -> None:
    app.state.store.reset()
    headers = auth_headers()
    context = create_context(headers, "rollback-failure")
    scheme, runner_token = create_runner_scheme(
        headers,
        context,
        rollback_config={
            "auto_on_failure": True,
            "enabled": True,
            "strategy": "target_command",
        },
    )
    deployment = create_deployment(headers, context, scheme_id=scheme["id"])
    deploy_run = client.post(
        f"/api/devops/deployments/{deployment['id']}/start",
        json={},
        headers=headers,
    ).json()["data"]["runs"][0]
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{deploy_run['runner_task_id']}/complete",
        json={
            "error_message": "health check failed",
            "result_json": {"health_status": "failed", "operation": "deploy"},
            "runner_id": scheme["runner_id"],
            "status": "failed",
        },
        headers={"X-Runner-Token": runner_token},
    )
    rollback_run = client.get(
        f"/api/devops/deployments/{deployment['id']}", headers=headers
    ).json()["data"]["runs"][0]
    client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"runner_id": scheme["runner_id"]},
        headers={"X-Runner-Token": runner_token},
    )
    client.post(
        f"/api/system/ai-executor-tasks/{rollback_run['runner_task_id']}/complete",
        json={
            "error_message": "rollback command failed",
            "result_json": {"operation": "rollback"},
            "runner_id": scheme["runner_id"],
            "status": "failed",
        },
        headers={"X-Runner-Token": runner_token},
    )
    takeover = client.get(
        f"/api/devops/deployments/{deployment['id']}", headers=headers
    ).json()["data"]
    incidents = [
        bug
        for bug in app.state.store.bugs.values()
        if bug.get("source") == "deployment_rollback_failure"
    ]

    assert takeover["status"] == "waiting_takeover"
    assert len(incidents) == 1
    assert incidents[0]["severity"] == "critical"
