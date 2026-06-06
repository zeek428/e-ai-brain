import json

from fastapi.testclient import TestClient

import app.api.routers.assistant as assistant_router
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

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

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
    task_id = task["task_id"]
    now = "2026-06-05T08:00:00+00:00"
    app.state.store.human_reviews["review_assistant_pending"] = {
        "ai_task_id": task_id,
        "created_at": now,
        "id": "review_assistant_pending",
        "review_type": "product_design",
        "status": "pending",
        "updated_at": now,
        "version": 1,
    }
    app.state.store.bugs["bug_assistant_blocker"] = {
        "assignee": "qa@example.com",
        "created_at": now,
        "description": "助手上下文应展示高优先级阻塞缺陷。",
        "duplicate_of_bug_id": None,
        "evidence": {},
        "id": "bug_assistant_blocker",
        "module_code": None,
        "product_id": product["id"],
        "related_task_id": task_id,
        "reproduce_steps": ["打开助手", "查看进展"],
        "requirement_id": requirement["id"],
        "severity": "critical",
        "source": "manual_test",
        "status": "open",
        "title": "助手进度阻塞 Bug",
        "updated_at": now,
        "version_id": version["id"],
    }
    app.state.store.code_review_reports["report_assistant_recent"] = {
        "archived_at": now,
        "executor": {"executor_name": "pytest-code-review"},
        "findings": [{"file": "apps/web/src/pages/Assistant/index.tsx", "severity": "low"}],
        "gitlab_mr_snapshot_id": "snapshot_assistant_recent",
        "gitlab_writeback_performed": False,
        "id": "report_assistant_recent",
        "review_id": "review_assistant_pending",
        "risk_level": "low",
        "status": "confirmed",
        "summary": "最近代码 Review 结论：风险低，关注助手上下文覆盖。",
        "task_id": task_id,
    }
    app.state.store.knowledge_deposits["deposit_assistant_recent"] = {
        "ai_task_id": task_id,
        "content": "AI 助手上下文增强验证记录。",
        "created_at": now,
        "id": "deposit_assistant_recent",
        "knowledge_document_id": None,
        "status": "pending",
        "title": "AI 助手上下文增强知识沉淀",
        "updated_at": now,
    }

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

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "AI Brain 项目现在开发到哪里了？", "product_id": product["id"]},
        headers=headers,
    )

    assert response.status_code == 200
    response_payload = response.json()["data"]
    assert response_payload["message"]["references"][0] == {
        "id": requirement["id"],
        "title": "AI 助手聊天界面",
        "type": "requirement",
        "url": f"/delivery/requirements?requirement_id={requirement['id']}",
    }
    assert response_payload["message"]["tool_results"][0]["tool"] == (
        "assistant.delivery_progress"
    )
    assert response_payload["message"]["tool_results"][0]["summary"]["requirements_total"] == 1
    user_message = captured_messages[1]["content"]
    assert "system_context" in user_message
    user_payload = json.loads(user_message)
    assert user_payload["system_context"]["tool_results"][0]["tool"] == (
        "assistant.delivery_progress"
    )
    assert user_payload["system_context"]["tool_results"][0]["items"][0]["id"] == (
        requirement["id"]
    )
    assert "AI Brain" in user_message
    assert "requirements_total" in user_message
    assert "ai_tasks_total" in user_message
    assert "AI 助手聊天界面" in user_message
    assert task["task_id"] in user_message
    assert "iteration_progress" in user_message
    assert "pending_reviews" in user_message
    assert "review_assistant_pending" in user_message
    assert "bug_distribution" in user_message
    assert "助手进度阻塞 Bug" in user_message
    assert "blocked_requirements" in user_message
    assert "recent_code_review_reports" in user_message
    assert "最近代码 Review 结论：风险低" in user_message
    assert "knowledge_deposits_total" in user_message
    assert "AI 助手上下文增强知识沉淀" in user_message


def test_ai_assistant_chat_persists_user_scoped_conversation_history(monkeypatch):
    headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()

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
                                        "answer": "当前 AI Brain 已能回答系统进展。",
                                        "suggestions": ["查看任务中心"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 12, "prompt_tokens": 20, "total_tokens": 32},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "AI Brain 现在开发到哪里了？"},
        headers=headers,
    )

    assert response.status_code == 200
    conversation_id = response.json()["data"]["conversation_id"]

    conversations = client.get("/api/assistant/conversations", headers=headers).json()["data"]
    assert conversations["total"] == 1
    assert conversations["items"][0] == {
        "created_at": conversations["items"][0]["created_at"],
        "id": conversation_id,
        "last_message_at": conversations["items"][0]["last_message_at"],
        "message_count": 2,
        "product_id": None,
        "title": "AI Brain 现在开发到哪里了？",
        "updated_at": conversations["items"][0]["updated_at"],
    }

    messages = client.get(
        f"/api/assistant/conversations/{conversation_id}/messages",
        headers=headers,
    ).json()["data"]
    assert messages["total"] == 2
    assert [(item["role"], item["content"]) for item in messages["items"]] == [
        ("user", "AI Brain 现在开发到哪里了？"),
        ("assistant", "当前 AI Brain 已能回答系统进展。"),
    ]
    assert messages["items"][1]["tool_results"][0]["tool"] == "assistant.delivery_progress"

    reviewer_conversations = client.get(
        "/api/assistant/conversations",
        headers=reviewer_headers,
    ).json()["data"]
    assert reviewer_conversations == {"items": [], "total": 0}
    forbidden_messages = client.get(
        f"/api/assistant/conversations/{conversation_id}/messages",
        headers=reviewer_headers,
    )
    assert forbidden_messages.status_code == 404
