import json
from urllib.error import URLError

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_started_design_task(headers: dict[str, str]) -> str:
    app.state.store.reset()
    task = create_draft_design_task(headers)
    client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)
    return task["task_id"]


def create_draft_design_task(headers: dict[str, str]) -> dict[str, str]:
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
    return task


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


def test_active_model_gateway_config_calls_openai_compatible_chat_completion(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "acceptance_points": ["真实调用"],
                                        "kind": "product_detail_design",
                                        "summary": "真实模型输出摘要",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {
                        "completion_tokens": 22,
                        "prompt_tokens": 11,
                        "total_tokens": 33,
                    },
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "body": request.data.decode("utf-8"),
                "headers": dict(request.header_items()),
                "timeout": timeout,
                "url": request.full_url,
            }
        )
        return FakeResponse()

    monkeypatch.setattr("app.main.urlopen", fake_urlopen)
    config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-real-model",
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "gpt-real",
            "default_embedding_model": "text-embedding-real",
            "is_default": True,
            "name": "真实模型网关",
            "provider": "openai_compatible",
            "status": "active",
            "timeout_seconds": 12,
        },
        headers=headers,
    ).json()["data"]
    task = create_draft_design_task(headers)

    started = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)

    assert started.status_code == 200
    assert calls and calls[0]["url"] == "https://llm.example.com/v1/chat/completions"
    assert calls[0]["timeout"] == 12
    assert calls[0]["headers"]["Authorization"] == "Bearer sk-real-model"
    request_body = calls[0]["body"]
    assert '"model": "gpt-real"' in request_body
    assert '"response_format": {"type": "json_object"}' in request_body

    detail = client.get(f"/api/ai-tasks/{task['task_id']}", headers=headers).json()["data"]
    assert detail["output"]["summary"] == "真实模型输出摘要"
    assert detail["output"]["acceptance_points"] == ["真实调用"]
    assert "user_value" not in detail["output"]

    logs = client.get(
        f"/api/model-gateway/logs?ai_task_id={task['task_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert logs[0]["provider"] == "openai_compatible"
    assert logs[0]["model"] == "gpt-real"
    assert logs[0]["model_gateway_config_id"] == config["id"]
    assert logs[0]["tokens"] == {"prompt": 11, "completion": 22, "total": 33}
    assert logs[0]["status"] == "succeeded"
    assert "sk-real-model" not in str(logs[0])
    assert "真实模型输出摘要" not in str(logs[0])


def test_model_gateway_failure_marks_task_failed_and_logs_error(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()

    def fake_urlopen(_request, _timeout):
        raise URLError("connection refused")

    monkeypatch.setattr("app.main.urlopen", fake_urlopen)
    client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-failing-model",
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "gpt-failing",
            "default_embedding_model": "text-embedding-real",
            "is_default": True,
            "name": "失败模型网关",
            "provider": "openai_compatible",
            "status": "active",
        },
        headers=headers,
    )
    task = create_draft_design_task(headers)

    response = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "MODEL_GATEWAY_FAILED"
    detail = client.get(f"/api/ai-tasks/{task['task_id']}", headers=headers).json()["data"]
    assert detail["status"] == "failed"
    assert detail["current_step"] == "model_gateway_failed"
    logs = client.get(
        f"/api/model-gateway/logs?ai_task_id={task['task_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert logs[0]["status"] == "failed"
    assert logs[0]["error"] == "Model gateway request failed"


def test_active_model_gateway_without_api_key_does_not_fallback_to_local_output():
    headers = auth_headers()
    app.state.store.reset()
    client.post(
        "/api/system/model-gateway-configs",
        json={
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "gpt-missing-key",
            "default_embedding_model": "text-embedding-real",
            "is_default": True,
            "name": "缺少密钥的模型网关",
            "provider": "openai_compatible",
            "status": "active",
        },
        headers=headers,
    )
    task = create_draft_design_task(headers)

    response = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MODEL_GATEWAY_CONFIG_INVALID"
    detail = client.get(f"/api/ai-tasks/{task['task_id']}", headers=headers).json()["data"]
    assert detail["status"] == "failed"
    assert detail["current_step"] == "model_gateway_config_invalid"
