from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_started_design_task(headers: dict[str, str]) -> str:
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1 MVP"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "模型网关日志",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "敏感需求正文 secret-business-context 不应进入模型调用日志。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)
    return task["task_id"]


def test_model_gateway_call_logs_metadata_without_prompt_or_output_payload():
    headers = auth_headers()
    task_id = create_started_design_task(headers)

    logs = client.get(f"/api/model-gateway/logs?ai_task_id={task_id}", headers=headers).json()[
        "data"
    ]["items"]

    assert len(logs) == 1
    log = logs[0]
    assert log["ai_task_id"] == task_id
    assert log["provider"] == "local_fallback"
    assert log["purpose"] == "product_detail_design"
    assert log["model"].startswith("local-")
    assert log["status"] == "succeeded"
    assert log["tokens"]["prompt"] > 0
    assert log["tokens"]["completion"] > 0
    assert log["latency_ms"] >= 0
    assert "prompt" not in log
    assert "output" not in log
    assert "secret-business-context" not in str(log)
    assert "围绕" not in str(log)

    audit_events = client.get(
        f"/api/audit/events?ai_task_id={task_id}&event_type=model_gateway.called",
        headers=headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    assert audit_events[0]["payload"]["model_log_id"] == log["id"]


def test_model_gateway_logs_are_admin_only():
    admin_headers = auth_headers()
    create_started_design_task(admin_headers)
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    response = client.get("/api/model-gateway/logs", headers=reviewer_headers)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"
