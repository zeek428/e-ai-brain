import json
from urllib.error import URLError

from fastapi.testclient import TestClient

import app.main as main
import app.services.model_gateway as model_gateway_service
from app.main import app
from app.services.model_gateway_listing import list_model_gateway_configs_response

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
    assert log["provider"] == "openai_compatible"
    assert log["purpose"] == "product_detail_design"
    assert log["model"] == "test-chat-model"
    assert log["model_gateway_config_id"] is None
    assert log["status"] == "succeeded"
    assert log["tokens"] == {"prompt": 11, "completion": 22, "total": 33}
    assert log["latency_ms"] >= 0
    assert "prompt" not in log
    assert "output" not in log
    assert "secret-business-context" not in str(log)
    assert "测试模型生成" not in str(log)

    audit_events = client.get(
        f"/api/audit/events?ai_task_id={task_id}&event_type=model_gateway.called",
        headers=headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    assert audit_events[0]["payload"]["model_log_id"] == log["id"]


def test_missing_model_gateway_configuration_does_not_generate_local_output(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    monkeypatch.setattr(main.settings, "model_gateway_base_url", "")
    monkeypatch.setattr(main.settings, "model_gateway_api_key", "")
    task = create_draft_design_task(headers)

    response = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MODEL_GATEWAY_CONFIG_INVALID"
    detail = client.get(f"/api/ai-tasks/{task['task_id']}", headers=headers).json()["data"]
    assert detail["status"] == "failed"
    assert detail["current_step"] == "model_gateway_config_invalid"
    assert detail["output"] is None


def test_ai_task_explicit_deterministic_start_bypasses_model_gateway(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    monkeypatch.setattr(main.settings, "model_gateway_base_url", "")
    monkeypatch.setattr(main.settings, "model_gateway_api_key", "")
    task = create_draft_design_task(headers)

    response = client.post(
        f"/api/ai-tasks/{task['task_id']}/start",
        json={
            "execution_mode": "deterministic",
            "reason": "full-chain regression",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "waiting_review"
    detail = client.get(f"/api/ai-tasks/{task['task_id']}", headers=headers).json()["data"]
    assert detail["output"]["generated_by"] == "ai_brain_deterministic_execution"
    assert detail["output"]["kind"] == "product_detail_design"
    logs = client.get(
        f"/api/model-gateway/logs?ai_task_id={task['task_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert logs == []
    audit_events = client.get(
        f"/api/audit/events?ai_task_id={task['task_id']}&event_type=ai_task.deterministic_execution_used",
        headers=headers,
    ).json()["data"]["items"]
    assert audit_events[0]["payload"]["reason"] == "full-chain regression"


def test_ai_task_explicit_deterministic_start_bypasses_executor_policy(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    monkeypatch.setattr(main.settings, "model_gateway_base_url", "")
    monkeypatch.setattr(main.settings, "model_gateway_api_key", "")
    task = create_draft_design_task(headers)
    product_id = app.state.store.ai_tasks[task["task_id"]]["product_id"]
    runner = client.post(
        "/api/system/ai-executor-runners",
        json={
            "executor_types": ["codex"],
            "name": "全链路回归 Runner",
            "protocol": "runner_polling",
            "runner_token": "runner-secret",
            "workspace_roots": ["/tmp"],
        },
        headers=headers,
    ).json()["data"]
    policy = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "codex",
            "instruction_template": "处理任务 {{task_id}}",
            "name": "产品设计任务走 Runner",
            "output_contract": {"summary": "string"},
            "priority": 1,
            "product_id": product_id,
            "runner_id": runner["id"],
            "status": "active",
            "task_type": "product_detail_design",
            "timeout_seconds": 600,
            "workspace_root": "/tmp",
        },
        headers=headers,
    ).json()["data"]

    response = client.post(
        f"/api/ai-tasks/{task['task_id']}/start",
        json={"execution_mode": "deterministic", "reason": "full-chain regression"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "waiting_review"
    assert "executor_task_id" not in payload
    assert not app.state.store.ai_executor_tasks
    detail = client.get(f"/api/ai-tasks/{task['task_id']}", headers=headers).json()["data"]
    assert detail["output"]["generated_by"] == "ai_brain_deterministic_execution"
    assert policy["id"] not in str(detail["input"])


def test_model_gateway_logs_are_admin_only():
    admin_headers = auth_headers()
    create_started_design_task(admin_headers)
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    response = client.get("/api/model-gateway/logs", headers=reviewer_headers)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_model_gateway_logs_filter_ignores_logs_without_ai_task_id():
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.model_gateway_logs.extend(
        [
            {
                "created_at": "2026-06-02T00:00:00+00:00",
                "id": "model_log_assistant",
                "latency_ms": 10,
                "model": "chat",
                "provider": "openai_compatible",
                "purpose": "assistant_chat",
                "status": "succeeded",
                "tokens": {"total": 1},
            },
            {
                "ai_task_id": "task_123",
                "created_at": "2026-06-02T00:01:00+00:00",
                "id": "model_log_task",
                "latency_ms": 20,
                "model": "chat",
                "provider": "openai_compatible",
                "purpose": "technical_solution",
                "status": "succeeded",
                "tokens": {"total": 2},
            },
        ]
    )

    response = client.get("/api/model-gateway/logs?ai_task_id=task_123", headers=headers)

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["id"] for item in items] == ["model_log_task"]


def test_model_gateway_log_list_supports_server_pagination_sort_filters_and_observability():
    headers = auth_headers()
    app.state.store.reset()
    app.state.store.model_gateway_logs.extend(
        [
            {
                "created_at": "2026-06-02T00:03:00+00:00",
                "id": "model_log_latest_success",
                "latency_ms": 30,
                "model": "gpt-4.1",
                "provider": "openai_compatible",
                "purpose": "assistant_chat",
                "status": "succeeded",
                "tokens": {"total": 3},
            },
            {
                "created_at": "2026-06-02T00:01:00+00:00",
                "error": "failed",
                "id": "model_log_failed",
                "latency_ms": 10,
                "model": "gpt-4.1",
                "provider": "openai_compatible",
                "purpose": "assistant_chat",
                "status": "failed",
                "tokens": {"total": 1},
            },
            {
                "created_at": "2026-06-02T00:02:00+00:00",
                "id": "model_log_old_success",
                "latency_ms": 20,
                "model": "gpt-4.1",
                "provider": "openai_compatible",
                "purpose": "assistant_chat",
                "status": "succeeded",
                "tokens": {"total": 2},
            },
        ]
    )

    response = client.get(
        "/api/model-gateway/logs"
        "?page=1&page_size=1&purpose=assistant_chat&status=succeeded"
        "&sort_by=created_at&sort_order=asc",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert [item["id"] for item in body["items"]] == ["model_log_old_success"]
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] == 2
    assert body["query"]["name"] == "model_gateway_logs"
    assert body["query"]["filters"]["purpose"] == "assistant_chat"
    assert body["query"]["filters"]["status"] == "succeeded"
    assert body["performance"]["result_count"] == 1
    assert body["performance"]["total"] == 2
    assert body["performance"]["p95_target_ms"] == 400

    invalid = client.get(
        "/api/model-gateway/logs?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "VALIDATION_ERROR"


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

    monkeypatch.setattr(model_gateway_service, "urlopen", fake_urlopen)
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

    def fake_urlopen(_request, timeout):
        raise URLError("connection refused")

    monkeypatch.setattr(model_gateway_service, "urlopen", fake_urlopen)
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


def test_model_gateway_failed_task_can_be_started_again(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    calls = {"count": 0}

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
                                        "acceptance_points": ["重试成功"],
                                        "kind": "product_detail_design",
                                        "summary": "模型重试后生成的产品详细设计。",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 8, "prompt_tokens": 4, "total_tokens": 12},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise URLError("temporary upstream failure")
        return FakeResponse()

    monkeypatch.setattr(model_gateway_service, "urlopen", fake_urlopen)
    client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-retry-model",
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "gpt-retry",
            "default_embedding_model": "text-embedding-real",
            "is_default": True,
            "name": "可重试模型网关",
            "provider": "openai_compatible",
            "status": "active",
        },
        headers=headers,
    )
    task = create_draft_design_task(headers)

    failed = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)
    retried = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)

    assert failed.status_code == 502
    assert failed.json()["detail"]["code"] == "MODEL_GATEWAY_FAILED"
    assert retried.status_code == 200
    detail = client.get(f"/api/ai-tasks/{task['task_id']}", headers=headers).json()["data"]
    assert detail["status"] == "waiting_review"
    assert detail["current_step"] == "interrupt_for_human_review"
    assert detail["output"]["summary"] == "模型重试后生成的产品详细设计。"
    logs = client.get(
        f"/api/model-gateway/logs?ai_task_id={task['task_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [log["status"] for log in logs] == ["succeeded", "failed"]


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


def test_model_gateway_config_rejects_unsupported_provider():
    headers = auth_headers()
    app.state.store.reset()

    response = client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-local",
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "gpt-local",
            "default_embedding_model": "text-embedding-local",
            "is_default": True,
            "name": "错误 provider",
            "provider": "direct_sdk",
            "status": "active",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    configs = client.get("/api/system/model-gateway-configs", headers=headers).json()["data"]
    assert configs["items"] == []


def test_model_gateway_config_patch_rejects_unsupported_provider():
    headers = auth_headers()
    app.state.store.reset()
    config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-local",
            "base_url": "https://llm.example.com/v1",
            "default_chat_model": "gpt-local",
            "default_embedding_model": "text-embedding-local",
            "is_default": True,
            "name": "正确 provider",
            "provider": "openai_compatible",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]

    response = client.patch(
        f"/api/system/model-gateway-configs/{config['id']}",
        json={"provider": "direct_sdk"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    unchanged = client.get("/api/system/model-gateway-configs", headers=headers).json()["data"][
        "items"
    ][0]
    assert unchanged["provider"] == "openai_compatible"


def test_model_gateway_config_list_supports_server_pagination_sort_filters_and_observability():
    headers = auth_headers()
    app.state.store.reset()
    client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-default",
            "base_url": "https://llm-a.example.com/v1",
            "default_chat_model": "gpt-a",
            "default_embedding_model": "text-embedding-a",
            "embedding_connection_mode": "reuse_chat",
            "is_default": True,
            "name": "A 默认模型网关",
            "provider": "openai_compatible",
            "status": "active",
        },
        headers=headers,
    )
    client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-secondary",
            "base_url": "https://llm-b.example.com/v1",
            "default_chat_model": "gpt-b",
            "default_embedding_model": "text-embedding-b",
            "embedding_connection_mode": "disabled",
            "is_default": False,
            "name": "B 停用模型网关",
            "provider": "openai_compatible",
            "status": "inactive",
        },
        headers=headers,
    )

    response = client.get(
        "/api/system/model-gateway-configs"
        "?page=1&page_size=1&status=active&is_default=true&sort_by=name&sort_order=desc",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["items"][0]["name"] == "A 默认模型网关"
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] == 1
    assert body["query"]["name"] == "model_gateway_configs"
    assert body["query"]["filters"]["status"] == "active"
    assert body["query"]["filters"]["is_default"] == "true"
    assert body["performance"]["result_count"] == 1
    assert body["performance"]["total"] == 1
    assert body["performance"]["p95_target_ms"] == 300

    invalid = client.get(
        "/api/system/model-gateway-configs?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_model_gateway_config_list_prefers_count_page_repository_for_paged_query():
    calls: list[tuple[str, dict]] = []

    class FakeRepository:
        def list_model_gateway_configs(self) -> list[dict]:
            calls.append(("full_configs", {}))
            return []

        def list_model_gateway_logs(self) -> list[dict]:
            return []

        def count_model_gateway_configs(self, **kwargs) -> int:
            calls.append(("count_configs", kwargs))
            return 2

        def list_model_gateway_configs_page(self, **kwargs) -> list[dict]:
            calls.append(("page_configs", kwargs))
            return [
                {
                    "api_key": "sk-secret",
                    "base_url": "https://llm-a.example.com/v1",
                    "default_chat_model": "gpt-a",
                    "embedding_connection_mode": "reuse_chat",
                    "id": "model_gateway_config_a",
                    "is_default": True,
                    "max_retries": 1,
                    "name": "A 默认模型网关",
                    "provider": "openai_compatible",
                    "status": "active",
                    "timeout_seconds": 60,
                }
            ]

    class FakeStore:
        repository = FakeRepository()

    response = list_model_gateway_configs_response(
        current_store=FakeStore(),
        default_chat_model="gpt",
        default_embedding_model=None,
        embedding_connection_mode="reuse_chat",
        is_default="true",
        name="默认",
        page=1,
        page_size=1,
        provider="openai_compatible",
        sort_by="name",
        sort_order="asc",
        status="active",
        trace_id="trace_config_page",
    )

    body = response["data"]
    assert body["items"][0]["id"] == "model_gateway_config_a"
    assert body["items"][0]["api_key_configured"] is True
    assert "api_key" not in body["items"][0]
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] == 2
    assert body["query"]["name"] == "model_gateway_configs"
    assert body["performance"]["total"] == 2
    assert calls == [
        (
            "count_configs",
            {
                "default_chat_model": "gpt",
                "default_embedding_model": None,
                "embedding_connection_mode": "reuse_chat",
                "is_default": True,
                "name": "默认",
                "provider": "openai_compatible",
                "status": "active",
            },
        ),
        (
            "page_configs",
            {
                "default_chat_model": "gpt",
                "default_embedding_model": None,
                "embedding_connection_mode": "reuse_chat",
                "is_default": True,
                "limit": 1,
                "name": "默认",
                "offset": 0,
                "provider": "openai_compatible",
                "sort_by": "name",
                "sort_order": "asc",
                "status": "active",
            },
        ),
    ]


def test_model_gateway_config_test_checks_chat_and_embedding_without_persisting_key(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    calls = []

    class FakeResponse:
        def __init__(self, payload: dict):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def fake_urlopen(request, timeout):
        body = json.loads(request.data.decode("utf-8"))
        calls.append(
            {
                "body": body,
                "headers": dict(request.header_items()),
                "timeout": timeout,
                "url": request.full_url,
            }
        )
        if request.full_url.endswith("/embeddings"):
            return FakeResponse(
                {
                    "data": [{"embedding": [0.1] * 1536, "index": 0}],
                    "usage": {"prompt_tokens": 2, "total_tokens": 2},
                }
            )
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"summary": "model gateway test ok"},
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "usage": {"completion_tokens": 1, "prompt_tokens": 2, "total_tokens": 3},
            }
        )

    monkeypatch.setattr("app.services.model_gateway.urlopen", fake_urlopen)

    response = client.post(
        "/api/system/model-gateway-configs/test",
        json={
            "api_key": "sk-test-secret",
            "base_url": "http://127.0.0.1:8080/v1",
            "default_chat_model": "test-chat",
            "default_embedding_model": "test-embedding",
            "name": "临时测试",
            "provider": "openai_compatible",
            "status": "active",
            "timeout_seconds": 9,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "chat": {
            "latency_ms": data["chat"]["latency_ms"],
            "model": "test-chat",
            "ok": True,
            "status": "succeeded",
        },
        "embedding": {
            "dimension": 1536,
            "latency_ms": data["embedding"]["latency_ms"],
            "model": "test-embedding",
            "ok": True,
            "status": "succeeded",
        },
        "ok": True,
        "test_target": "chat_and_embedding",
    }
    assert calls[0]["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert calls[1]["url"] == "http://127.0.0.1:8080/v1/embeddings"
    assert all(call["headers"]["Authorization"] == "Bearer sk-test-secret" for call in calls)
    assert all(call["timeout"] == 9 for call in calls)
    assert app.state.store.model_gateway_configs == {}
    assert app.state.store.model_gateway_logs == []
    assert "sk-test-secret" not in str(data)


def test_model_gateway_config_test_allows_chat_only_without_embedding_model(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    calls = []

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
                                "content": json.dumps({"ok": True}, ensure_ascii=False)
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 1, "prompt_tokens": 2, "total_tokens": 3},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append({"timeout": timeout, "url": request.full_url})
        return FakeResponse()

    monkeypatch.setattr("app.services.model_gateway.urlopen", fake_urlopen)

    response = client.post(
        "/api/system/model-gateway-configs/test",
        json={
            "api_key": "sk-chat-only-secret",
            "base_url": "http://127.0.0.1:8080/v1",
            "default_chat_model": "codex-auto-review",
            "name": "Sub2API Chat",
            "provider": "openai_compatible",
            "status": "active",
            "test_target": "chat",
            "timeout_seconds": 11,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "chat": {
            "latency_ms": data["chat"]["latency_ms"],
            "model": "codex-auto-review",
            "ok": True,
            "status": "succeeded",
        },
        "embedding": {
            "model": "",
            "ok": True,
            "status": "skipped",
        },
        "ok": True,
        "test_target": "chat",
    }
    assert calls == [{"timeout": 11, "url": "http://127.0.0.1:8080/v1/chat/completions"}]
    assert app.state.store.model_gateway_configs == {}
    assert app.state.store.model_gateway_logs == []
    assert "sk-chat-only-secret" not in str(data)


def test_model_gateway_config_test_allows_chat_only_with_partial_embedding_config(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    calls = []

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
                                "content": json.dumps({"ok": True}, ensure_ascii=False)
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 1, "prompt_tokens": 2, "total_tokens": 3},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append({"timeout": timeout, "url": request.full_url})
        return FakeResponse()

    monkeypatch.setattr("app.services.model_gateway.urlopen", fake_urlopen)

    response = client.post(
        "/api/system/model-gateway-configs/test",
        json={
            "api_key": "sk-chat-only-secret",
            "base_url": "http://127.0.0.1:8080/v1",
            "default_chat_model": "codex-auto-review",
            "embedding_connection_mode": "custom",
            "embedding_dimension": 768,
            "name": "Sub2API Chat",
            "provider": "openai_compatible",
            "status": "active",
            "test_target": "chat",
            "timeout_seconds": 11,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["chat"]["status"] == "succeeded"
    assert data["embedding"] == {"model": "", "ok": True, "status": "skipped"}
    assert data["ok"] is True
    assert data["test_target"] == "chat"
    assert calls == [{"timeout": 11, "url": "http://127.0.0.1:8080/v1/chat/completions"}]
    assert app.state.store.model_gateway_configs == {}
    assert app.state.store.model_gateway_logs == []
    assert "sk-chat-only-secret" not in str(data)


def test_model_gateway_config_test_allows_custom_embedding_only_without_chat_key(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "data": [{"embedding": [0.2] * 1536, "index": 0}],
                    "usage": {"prompt_tokens": 2, "total_tokens": 2},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "headers": dict(request.header_items()),
                "timeout": timeout,
                "url": request.full_url,
            }
        )
        return FakeResponse()

    monkeypatch.setattr("app.services.model_gateway.urlopen", fake_urlopen)

    response = client.post(
        "/api/system/model-gateway-configs/test",
        json={
            "base_url": "https://chat.example.com/v1",
            "default_chat_model": "gpt-unused",
            "default_embedding_model": "embedding-only",
            "embedding_api_key": "sk-embedding-only",
            "embedding_base_url": "https://embedding.example.com/v1",
            "embedding_connection_mode": "custom",
            "embedding_dimension": 1536,
            "name": "独立 Embedding 测试",
            "provider": "openai_compatible",
            "status": "active",
            "test_target": "embedding",
            "timeout_seconds": 13,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["chat"] == {"model": "gpt-unused", "ok": True, "status": "skipped"}
    assert data["embedding"]["status"] == "succeeded"
    assert data["embedding"]["dimension"] == 1536
    assert data["ok"] is True
    assert data["test_target"] == "embedding"
    assert calls == [
        {
            "headers": {
                "Authorization": "Bearer sk-embedding-only",
                "Content-type": "application/json",
            },
            "timeout": 13,
            "url": "https://embedding.example.com/v1/embeddings",
        }
    ]
    assert app.state.store.model_gateway_configs == {}
    assert app.state.store.model_gateway_logs == []
    assert "sk-embedding-only" not in str(data)


def test_model_gateway_config_allows_embedding_disabled_for_chat_only_runtime(monkeypatch):
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
                                        "acceptance_points": ["Chat-only"],
                                        "kind": "product_detail_design",
                                        "summary": "Chat-only 模型网关生成结果。",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 3, "prompt_tokens": 2, "total_tokens": 5},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
                "url": request.full_url,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(model_gateway_service, "urlopen", fake_urlopen)

    config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-chat-only",
            "base_url": "https://chat.example.com/v1",
            "default_chat_model": "gpt-chat-only",
            "embedding_connection_mode": "disabled",
            "is_default": True,
            "name": "仅 Chat 模型网关",
            "provider": "openai_compatible",
            "status": "active",
        },
        headers=headers,
    )

    assert config.status_code == 200
    config_data = config.json()["data"]
    assert config_data["default_embedding_model"] is None
    assert config_data["embedding_connection_mode"] == "disabled"
    assert config_data["embedding_api_key_configured"] is False

    task = create_draft_design_task(headers)
    started = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers)

    assert started.status_code == 200
    assert calls == [
        {
            "body": {
                "messages": calls[0]["body"]["messages"],
                "model": "gpt-chat-only",
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            "timeout": 60,
            "url": "https://chat.example.com/v1/chat/completions",
        }
    ]


def test_custom_embedding_connection_indexes_knowledge_and_records_vector_metadata(monkeypatch):
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
                    "data": [{"embedding": [1.0, *([0.0] * 1535)], "index": 0}],
                    "usage": {"prompt_tokens": 1, "total_tokens": 1},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "body": json.loads(request.data.decode("utf-8")),
                "headers": dict(request.header_items()),
                "timeout": timeout,
                "url": request.full_url,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(model_gateway_service, "urlopen", fake_urlopen)

    config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "api_key": "sk-chat",
            "base_url": "https://chat.example.com/v1",
            "default_chat_model": "gpt-chat",
            "default_embedding_model": "embedding-current",
            "embedding_api_key": "sk-embedding",
            "embedding_base_url": "https://embedding.example.com/v1",
            "embedding_connection_mode": "custom",
            "embedding_dimension": 1536,
            "is_default": True,
            "name": "Chat 与 Embedding 分离网关",
            "provider": "openai_compatible",
            "status": "active",
            "timeout_seconds": 7,
        },
        headers=headers,
    ).json()["data"]

    document = client.post(
        "/api/knowledge/documents",
        json={
            "content": "custom-embedding-token should be vector indexed.",
            "permission_roles": ["admin"],
            "title": "自定义 Embedding 知识",
        },
        headers=headers,
    ).json()["data"]

    assert document["index_status"] == "vector_indexed"
    assert calls == [
        {
            "body": {
                "input": ["custom-embedding-token should be vector indexed."],
                "model": "embedding-current",
            },
            "headers": {
                "Authorization": "Bearer sk-embedding",
                "Content-type": "application/json",
            },
            "timeout": 7,
            "url": "https://embedding.example.com/v1/embeddings",
        }
    ]
    stored_chunk = next(
        chunk
        for chunk in app.state.store.knowledge_chunks.values()
        if chunk["document_id"] == document["id"]
    )
    assert stored_chunk["metadata"]["embedding_config_id"] == config["id"]
    assert stored_chunk["metadata"]["embedding_dimension"] == 1536
    assert stored_chunk["metadata"]["embedding_model"] == "embedding-current"
