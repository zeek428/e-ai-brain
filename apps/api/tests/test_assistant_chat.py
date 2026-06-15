import json

from fastapi.testclient import TestClient

import app.api.routers.assistant as assistant_router
from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def seed_assistant_knowledge_reference_documents() -> None:
    now = "2026-06-14T08:00:00+00:00"
    app.state.store.knowledge_documents["knowledge_payment_runbook"] = {
        "brain_app_id": "rd_brain",
        "content": "支付页提交无响应时，先检查网关超时、回调状态和前端埋点。",
        "created_at": now,
        "created_by": "knowledge_owner@example.com",
        "doc_type": "manual",
        "id": "knowledge_payment_runbook",
        "index_status": "indexed",
        "permission_roles": ["reviewer"],
        "permission_scope": {},
        "product_id": None,
        "source_type": "manual",
        "tags": ["payment"],
        "title": "支付页超时排障手册",
        "updated_at": now,
        "vector_index_error": None,
        "version_id": None,
    }
    app.state.store.knowledge_documents["knowledge_private_runbook"] = {
        "brain_app_id": "rd_brain",
        "content": "非授权知识：内部成本和供应商账号。",
        "created_at": now,
        "created_by": "knowledge_owner@example.com",
        "doc_type": "manual",
        "id": "knowledge_private_runbook",
        "index_status": "indexed",
        "permission_roles": ["knowledge_owner"],
        "permission_scope": {},
        "product_id": None,
        "source_type": "manual",
        "tags": ["private"],
        "title": "非授权支付内部手册",
        "updated_at": now,
        "vector_index_error": None,
        "version_id": None,
    }
    app.state.store.knowledge_chunks["knowledge_payment_runbook_chunk_001"] = {
        "chunk_index": 0,
        "content": "支付页提交无响应：检查网关 30 秒超时、回调幂等键和前端 loading 状态。",
        "document_id": "knowledge_payment_runbook",
        "embedding": [0.1, 0.2, 0.3],
        "id": "knowledge_payment_runbook_chunk_001",
        "metadata": {},
        "permission_roles": ["reviewer"],
        "permission_scope": {"roles": ["reviewer"]},
    }
    app.state.store.knowledge_chunks["knowledge_private_runbook_chunk_001"] = {
        "chunk_index": 0,
        "content": "非授权知识：供应商账号和内部成本。",
        "document_id": "knowledge_private_runbook",
        "embedding": [0.4, 0.5, 0.6],
        "id": "knowledge_private_runbook_chunk_001",
        "metadata": {},
        "permission_roles": ["knowledge_owner"],
        "permission_scope": {"roles": ["knowledge_owner"]},
    }


def seed_assistant_operational_references() -> None:
    now = "2026-06-14T09:30:00+00:00"
    app.state.store.ai_agents["ai_agent_feedback_ops"] = {
        "brain_app_id": "rd_brain",
        "code": "feedback_ops",
        "created_at": now,
        "description": "负责用户反馈洞察和运行诊断。",
        "id": "ai_agent_feedback_ops",
        "name": "反馈洞察 AI 角色",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.ai_skills["ai_skill_feedback_summary"] = {
        "brain_app_id": "rd_brain",
        "code": "feedback_summary",
        "created_at": now,
        "description": "汇总反馈并生成洞察。",
        "id": "ai_skill_feedback_summary",
        "name": "反馈洞察 Skill",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.plugin_actions["plugin_action_feedback_write"] = {
        "action_type": "http_request",
        "code": "feedback_write",
        "created_at": now,
        "id": "plugin_action_feedback_write",
        "name": "反馈洞察写入动作",
        "plugin_id": "plugin_http",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.scheduled_jobs["scheduled_job_feedback_weekly"] = {
        "agent_id": "ai_agent_feedback_ops",
        "created_at": now,
        "enabled": True,
        "execution_mode": "ai_assisted",
        "id": "scheduled_job_feedback_weekly",
        "job_type": "user_feedback_insight",
        "name": "每周反馈洞察定时作业",
        "plugin_action_id": "plugin_action_feedback_write",
        "product_id": None,
        "schedule_type": "cron",
        "skill_ids": ["ai_skill_feedback_summary"],
        "source_system": "ai-assistant-test",
        "status": "active",
        "updated_at": now,
    }
    app.state.store.scheduled_job_runs["scheduled_job_run_feedback_failed"] = {
        "completed_at": "2026-06-14T09:35:00+00:00",
        "duration_ms": 4200,
        "error_message": "结果写入动作返回 500",
        "id": "scheduled_job_run_feedback_failed",
        "result_summary": {
            "execution_nodes": {
                "data_connection": {
                    "status": "succeeded",
                    "summary": "从 MaxCompute 读取 128 条反馈。",
                },
                "ai_processing": {
                    "model_gateway_log_id": "model_gateway_log_feedback_failed",
                    "status": "succeeded",
                    "summary": "生成 6 条洞察。",
                },
                "result_action": {
                    "error_message": "HTTP 500: downstream write failed",
                    "plugin_invocation_log_id": "plugin_invocation_log_feedback_failed",
                    "status": "failed",
                    "summary": "写入反馈洞察表失败。",
                },
            },
            "records_imported": 128,
        },
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "started_at": "2026-06-14T09:31:00+00:00",
        "status": "failed",
        "trigger_type": "manual",
        "updated_at": "2026-06-14T09:35:00+00:00",
    }
    app.state.store.plugin_invocation_logs["plugin_invocation_log_feedback_failed"] = {
        "action_id": "plugin_action_feedback_write",
        "connection_id": "plugin_connection_maxcompute",
        "created_at": "2026-06-14T09:34:58+00:00",
        "duration_ms": 1800,
        "error_message": "HTTP 500: downstream write failed",
        "id": "plugin_invocation_log_feedback_failed",
        "plugin_id": "plugin_http",
        "request_summary": {"method": "POST", "path": "/feedback/insights"},
        "response_summary": {"status_code": 500},
        "scheduled_job_id": "scheduled_job_feedback_weekly",
        "scheduled_job_run_id": "scheduled_job_run_feedback_failed",
        "status": "failed",
        "trigger_type": "scheduled_job",
    }
    app.state.store.model_gateway_logs.append(
        {
            "created_at": "2026-06-14T09:33:00+00:00",
            "id": "model_gateway_log_feedback_failed",
            "latency_ms": 900,
            "model": "test-chat-model",
            "provider": "test",
            "purpose": "scheduled_job.ai_processing",
            "status": "succeeded",
            "tokens": {"completion": 80, "prompt": 200, "total": 280},
        }
    )


def test_ai_assistant_reference_candidates_filter_readable_knowledge_documents():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "支付", "type": "knowledge_document", "limit": 5},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["items"] == [
        {
            "chunk_count": 1,
            "id": "knowledge_payment_runbook",
            "index_status": "indexed",
            "title": "支付页超时排障手册",
            "type": "knowledge_document",
            "url": "/knowledge/documents?document_id=knowledge_payment_runbook",
        }
    ]


def test_ai_assistant_reference_candidates_include_admin_operational_objects():
    headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_operational_references()

    response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "反馈", "limit": 20},
        headers=headers,
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    reference_by_type = {item["type"]: item for item in items}
    assert reference_by_type["scheduled_job"] == {
        "id": "scheduled_job_feedback_weekly",
        "title": "每周反馈洞察定时作业",
        "type": "scheduled_job",
        "url": "/tasks/scheduled-jobs?job_id=scheduled_job_feedback_weekly",
    }
    assert reference_by_type["scheduled_job_run"] == {
        "id": "scheduled_job_run_feedback_failed",
        "title": "每周反馈洞察定时作业 / failed",
        "type": "scheduled_job_run",
        "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
    }
    assert reference_by_type["plugin_action"]["id"] == "plugin_action_feedback_write"
    assert reference_by_type["ai_agent"]["id"] == "ai_agent_feedback_ops"
    assert reference_by_type["ai_skill"]["id"] == "ai_skill_feedback_summary"

    reviewer_response = client.get(
        "/api/assistant/reference-candidates",
        params={"query": "反馈", "type": "scheduled_job", "limit": 20},
        headers=reviewer_headers,
    )
    assert reviewer_response.status_code == 200
    assert reviewer_response.json()["data"] == {"items": [], "total": 0}


def test_ai_assistant_resolve_operational_reference_requires_admin_role():
    headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_operational_references()

    response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["items"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        }
    ]

    forbidden_response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ]
        },
        headers=reviewer_headers,
    )
    assert forbidden_response.status_code == 404
    assert forbidden_response.json()["detail"]["code"] == "REFERENCE_NOT_FOUND"


def test_ai_assistant_resolve_rejects_unreadable_knowledge_reference():
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()

    response = client.post(
        "/api/assistant/references/resolve",
        json={
            "references": [
                {"id": "knowledge_private_runbook", "type": "knowledge_document"},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REFERENCE_NOT_FOUND"


def test_ai_assistant_chat_injects_selected_knowledge_chunks_without_logging_content(
    monkeypatch,
):
    admin_headers = auth_headers()
    headers = auth_headers("reviewer@example.com", "reviewer123")
    app.state.store.reset()
    seed_assistant_knowledge_reference_documents()
    captured_messages: list[dict[str, str]] = []

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
                                        "answer": (
                                            "应优先检查网关超时、回调幂等键"
                                            "和前端 loading 状态。"
                                        ),
                                        "suggestions": ["生成支付页排障任务"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 13, "prompt_tokens": 31, "total_tokens": 44},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        del timeout
        request_body = json.loads(request.data.decode("utf-8"))
        captured_messages.extend(request_body["messages"])
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "基于 @支付页超时排障手册 说明如何定位支付页提交无响应。",
            "references": [
                {"id": "knowledge_payment_runbook", "type": "knowledge_document"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    assistant_message = response.json()["data"]["message"]
    assert assistant_message["references"][0] == {
        "id": "knowledge_payment_runbook",
        "title": "支付页超时排障手册",
        "type": "knowledge_document",
        "url": "/knowledge/documents?document_id=knowledge_payment_runbook",
    }
    user_payload = json.loads(captured_messages[1]["content"])
    assert user_payload["system_context"]["selected_references"] == [
        {
            "id": "knowledge_payment_runbook",
            "title": "支付页超时排障手册",
            "type": "knowledge_document",
            "url": "/knowledge/documents?document_id=knowledge_payment_runbook",
        }
    ]
    assert user_payload["system_context"]["knowledge_context"][0] == {
        "chunk_id": "knowledge_payment_runbook_chunk_001",
        "chunk_index": 0,
        "content": "支付页提交无响应：检查网关 30 秒超时、回调幂等键和前端 loading 状态。",
        "document_id": "knowledge_payment_runbook",
        "document_title": "支付页超时排障手册",
        "source": {
            "doc_type": "manual",
            "knowledge_space_id": None,
        },
    }
    assert "非授权知识" not in captured_messages[1]["content"]

    logs = client.get(
        "/api/model-gateway/logs?purpose=assistant_chat",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert logs[0]["purpose"] == "assistant_chat"
    assert "支付页提交无响应" not in str(logs[0])


def test_ai_assistant_chat_returns_scheduled_job_run_diagnostic(monkeypatch):
    headers = auth_headers()
    app.state.store.reset()
    seed_assistant_operational_references()

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
                                        "answer": "这次失败发生在结果动作写入阶段。",
                                        "suggestions": ["检查插件动作返回 500 的下游服务"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "为什么这次定时任务失败？",
            "references": [
                {"id": "scheduled_job_run_feedback_failed", "type": "scheduled_job_run"},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    diagnostic = next(
        result
        for result in message["tool_results"]
        if result["tool"] == "assistant.scheduled_job_diagnostic"
    )
    assert diagnostic["summary"] == {"failed_count": 1, "run_count": 1}
    assert diagnostic["references"] == [
        {
            "id": "scheduled_job_run_feedback_failed",
            "title": "每周反馈洞察定时作业 / failed",
            "type": "scheduled_job_run",
            "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_feedback_failed",
        }
    ]
    assert diagnostic["items"][0]["stages"] == [
        {
            "error_message": None,
            "log_id": None,
            "stage": "data_connection",
            "status": "succeeded",
            "summary": "从 MaxCompute 读取 128 条反馈。",
        },
        {
            "error_message": None,
            "log_id": "model_gateway_log_feedback_failed",
            "stage": "ai_processing",
            "status": "succeeded",
            "summary": "生成 6 条洞察。",
        },
        {
            "error_message": "HTTP 500: downstream write failed",
            "log_id": "plugin_invocation_log_feedback_failed",
            "stage": "result_action",
            "status": "failed",
            "summary": "写入反馈洞察表失败。",
        },
    ]


def test_ai_assistant_action_draft_can_be_confirmed_into_scheduled_job():
    headers = auth_headers()
    app.state.store.reset()

    draft_response = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "AI 助手草案仪表盘刷新",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": "创建仪表盘刷新定时任务",
        },
        headers=headers,
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["action"] == "create_scheduled_job"
    assert draft["status"] == "pending"
    assert draft["created_by"] == "user_admin"
    assert draft["payload"]["name"] == "AI 助手草案仪表盘刷新"

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )

    assert confirm_response.status_code == 200
    payload = confirm_response.json()["data"]
    assert payload["draft"]["id"] == draft["id"]
    assert payload["draft"]["status"] == "confirmed"
    assert payload["run"]["action"] == "create_scheduled_job"
    assert payload["run"]["status"] == "succeeded"
    assert payload["run"]["result_type"] == "scheduled_job"
    scheduled_job = payload["run"]["result"]
    assert scheduled_job["name"] == "AI 助手草案仪表盘刷新"
    assert scheduled_job["config_json"]["assistant_draft"] == {
        "draft_id": draft["id"],
        "source": "ai_assistant",
        "title": "创建仪表盘刷新定时任务",
    }

    get_response = client.get(f"/api/assistant/action-drafts/{draft['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["status"] == "confirmed"

    audit_events = client.get(
        "/api/audit/events?subject_type=assistant_action_draft",
        headers=headers,
    ).json()["data"]["items"]
    audit_events = sorted(audit_events, key=lambda item: item["sequence"])
    assert [item["event_type"] for item in audit_events] == [
        "assistant_action_draft.created",
        "assistant_action_draft.confirmed",
    ]


def test_ai_assistant_action_draft_cancel_prevents_confirmation():
    headers = auth_headers()
    app.state.store.reset()

    draft = client.post(
        "/api/assistant/action-drafts",
        json={
            "action": "create_scheduled_job",
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": "待取消定时任务",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "title": "取消用草案",
        },
        headers=headers,
    ).json()["data"]

    cancel_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/cancel",
        json={"reason": "用户决定暂不创建"},
        headers=headers,
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "cancelled"
    assert cancel_response.json()["data"]["cancel_reason"] == "用户决定暂不创建"

    confirm_response = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/confirm",
        headers=headers,
    )
    assert confirm_response.status_code == 409
    assert confirm_response.json()["detail"]["code"] == "DRAFT_NOT_PENDING"


def test_ai_assistant_chat_persists_action_draft_tool_results(monkeypatch):
    headers = auth_headers()
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
                                        "answer": "我已准备好定时任务草案，确认后再创建。",
                                        "suggestions": ["查看草案"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        del timeout
        return FakeResponse()

    monkeypatch.setattr(assistant_router, "urlopen", fake_urlopen)

    response = client.post(
        "/api/assistant/chat",
        json={"message": "帮我配置每周用户反馈洞察定时任务草案"},
        headers=headers,
    )

    assert response.status_code == 200
    message = response.json()["data"]["message"]
    draft_item = message["tool_results"][0]["items"][0]
    assert draft_item["client_draft_id"] == "assistant_draft_weekly_feedback_insight"
    assert draft_item["draft_id"].startswith("assistant_action_draft_")
    assert draft_item["server_draft_id"] == draft_item["draft_id"]
    assert draft_item["status"] == "pending"

    draft_response = client.get(
        f"/api/assistant/action-drafts/{draft_item['draft_id']}",
        headers=headers,
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["source_message_id"] == message["id"]
    assert draft["client_draft_id"] == "assistant_draft_weekly_feedback_insight"
    assert draft["action"] == "create_scheduled_job"
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
