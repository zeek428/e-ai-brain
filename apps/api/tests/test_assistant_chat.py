import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ai_assistant_chat_uses_model_gateway_without_logging_prompt_or_answer(monkeypatch):
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
                                        "answer": "可以从需求审批开始，再生成详细设计和技术方案。",
                                        "suggestions": [
                                            "创建需求",
                                            "查看模型网关",
                                            "检查 GitHub PR",
                                        ],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 17, "prompt_tokens": 29, "total_tokens": 46},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        body = json.loads(request.data.decode("utf-8"))
        calls.append(
            {
                "body": body,
                "timeout": timeout,
                "url": request.full_url,
            }
        )
        return FakeResponse()

    monkeypatch.setattr("app.main.urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "conversation_id": "conv-real-demand",
            "message": "如何跑通 AI Brain 实际需求迭代？ secret-chat-context",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["conversation_id"] == "conv-real-demand"
    assert payload["message"]["role"] == "assistant"
    assert payload["message"]["content"] == "可以从需求审批开始，再生成详细设计和技术方案。"
    assert payload["suggestions"] == ["创建需求", "查看模型网关", "检查 GitHub PR"]
    assert payload["model"] == "test-chat-model"

    assert calls and calls[0]["url"] == "https://llm.test/v1/chat/completions"
    assert calls[0]["body"]["model"] == "test-chat-model"
    assert calls[0]["body"]["messages"][0]["role"] == "system"
    assert "secret-chat-context" in calls[0]["body"]["messages"][1]["content"]

    logs = client.get("/api/model-gateway/logs?purpose=assistant_chat", headers=headers).json()[
        "data"
    ]["items"]
    assert len(logs) == 1
    assert logs[0]["purpose"] == "assistant_chat"
    assert logs[0]["status"] == "succeeded"
    assert logs[0]["tokens"] == {"prompt": 29, "completion": 17, "total": 46}
    assert "secret-chat-context" not in str(logs[0])
    assert "可以从需求审批开始" not in str(logs[0])

    audit_events = client.get(
        "/api/audit/events?event_type=assistant.chat_completed",
        headers=headers,
    ).json()["data"]["items"]
    assert len(audit_events) == 1
    assert audit_events[0]["payload"]["model"] == "test-chat-model"


def test_ai_assistant_chat_includes_ai_brain_system_progress_context(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    captured_messages: list[dict[str, str]] = []
    product = client.post(
        "/api/products",
        json={"code": "AI-BRAIN", "name": "AI Brain"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1.2", "name": "v1.2"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "增加 AI 助手聊天界面，回答项目开发进展。",
            "product_id": product["id"],
            "title": "AI 助手聊天界面",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task_response = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    )
    task = task_response.json()["data"]

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
                                        "answer": "AI Brain 当前已有 1 个需求和 1 个任务。",
                                        "suggestions": ["查看任务中心"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        request_body = json.loads(request.data.decode("utf-8"))
        captured_messages.extend(request_body["messages"])
        return FakeResponse()

    monkeypatch.setattr("app.main.urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "AI Brain 项目现在开发到哪里了？", "product_id": product["id"]},
        headers=headers,
    )

    assert response.status_code == 200
    user_message = captured_messages[1]["content"]
    assert "system_context" in user_message
    assert "AI Brain" in user_message
    assert "requirements_total" in user_message
    assert "ai_tasks_total" in user_message
    assert "AI 助手聊天界面" in user_message
    assert task["task_id"] in user_message
