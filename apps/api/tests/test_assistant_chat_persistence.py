import json

from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

import app.api.routers.assistant as assistant_router
from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.users import MemoryUserRepository


class AssistantChatRepositoryStub:
    def __init__(self) -> None:
        self.payload: dict | None = None
        self.assistant_chat_payload: dict | None = None
        self.id_counters: dict[str, int] = {}

    def load(self) -> dict | None:
        return self.payload

    def save(self, payload: dict) -> None:
        self.payload = payload

    def load_assistant_chat(self) -> dict | None:
        return self.assistant_chat_payload

    def save_assistant_chat(self, payload: dict) -> None:
        self.assistant_chat_payload = payload

    def next_id(self, prefix: str) -> str:
        self.id_counters[prefix] = self._max_existing_id(prefix) + 1
        return f"{prefix}_{self.id_counters[prefix]:03d}"

    def _max_existing_id(self, prefix: str) -> int:
        max_value = self.id_counters.get(prefix, 0)
        expected_prefix = f"{prefix}_"

        def visit(value: object) -> None:
            nonlocal max_value
            if isinstance(value, dict):
                for key, item in value.items():
                    if isinstance(key, str) and key.startswith(expected_prefix):
                        suffix = key.removeprefix(expected_prefix)
                        if suffix.isdigit():
                            max_value = max(max_value, int(suffix))
                    if key == "id" and isinstance(item, str) and item.startswith(expected_prefix):
                        suffix = item.removeprefix(expected_prefix)
                        if suffix.isdigit():
                            max_value = max(max_value, int(suffix))
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(self.assistant_chat_payload)
        return max_value


def test_assistant_chat_history_is_persisted_through_fine_grained_repository_payload():
    repository = AssistantChatRepositoryStub()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.assistant_conversations["conversation_009"] = {
        "created_at": "2026-06-03T08:00:00+00:00",
        "id": "conversation_009",
        "last_message_at": "2026-06-03T08:01:00+00:00",
        "message_count": 2,
        "product_id": "product_001",
        "title": "AI Brain 进展",
        "updated_at": "2026-06-03T08:01:00+00:00",
        "user_id": "user_admin",
    }
    current_store.assistant_messages["assistant_message_011"] = {
        "content": "AI Brain 现在开发到哪里了？",
        "conversation_id": "conversation_009",
        "created_at": "2026-06-03T08:00:00+00:00",
        "id": "assistant_message_011",
        "model": None,
        "product_id": "product_001",
        "role": "user",
        "suggestions": [],
        "user_id": "user_admin",
    }
    current_store.assistant_messages["assistant_message_012"] = {
        "content": "已完成 GitHub PR Review 链路。",
        "conversation_id": "conversation_009",
        "created_at": "2026-06-03T08:01:00+00:00",
        "id": "assistant_message_012",
        "model": "gpt-review",
        "product_id": "product_001",
        "role": "assistant",
        "suggestions": ["查看任务中心"],
        "user_id": "user_admin",
    }

    current_store.persist()

    assert repository.assistant_chat_payload == {
        "assistant_conversations": current_store.assistant_conversations,
        "assistant_messages": current_store.assistant_messages,
    }


def test_structured_assistant_chat_history_restore_and_sync_counters():
    repository = AssistantChatRepositoryStub()
    repository.payload = {
        "assistant_conversations": {
            "conversation_002": {
                "id": "conversation_002",
                "message_count": 1,
                "title": "旧快照会话",
                "user_id": "user_admin",
            }
        },
        "assistant_messages": {
            "assistant_message_002": {
                "content": "旧快照消息",
                "conversation_id": "conversation_002",
                "id": "assistant_message_002",
                "role": "user",
                "user_id": "user_admin",
            }
        },
    }
    repository.assistant_chat_payload = {
        "assistant_conversations": {
            "conversation_009": {
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "conversation_009",
                "last_message_at": "2026-06-03T08:01:00+00:00",
                "message_count": 2,
                "product_id": None,
                "title": "结构表会话",
                "updated_at": "2026-06-03T08:01:00+00:00",
                "user_id": "user_admin",
            }
        },
        "assistant_messages": {
            "assistant_message_011": {
                "content": "结构表消息",
                "conversation_id": "conversation_009",
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "assistant_message_011",
                "model": None,
                "product_id": None,
                "role": "user",
                "suggestions": [],
                "user_id": "user_admin",
            }
        },
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert list(rebuilt_store.assistant_conversations) == ["conversation_009"]
    assert list(rebuilt_store.assistant_messages) == ["assistant_message_011"]
    assert rebuilt_store.new_id("conversation") == "conversation_010"
    assert rebuilt_store.new_id("assistant_message") == "assistant_message_012"


def test_assistant_chat_writes_repository_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.model_gateway_payload = {
        "model_gateway_configs": {
            "model_gateway_config_assistant": {
                "api_key": "sk-assistant-test",
                "base_url": "https://api.example.com/v1",
                "default_chat_model": "gpt-assistant",
                "default_embedding_model": "text-embedding-assistant",
                "embedding_connection_mode": "disabled",
                "id": "model_gateway_config_assistant",
                "is_default": True,
                "max_retries": 1,
                "name": "Assistant test gateway",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            }
        },
        "model_gateway_logs": [],
    }

    class FakeResponse:
        def __init__(self, answer: str):
            self.answer = answer

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
                                        "answer": self.answer,
                                        "suggestions": ["查看需求", "查看任务"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 9, "prompt_tokens": 21, "total_tokens": 30},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def use_empty_postgres_runtime_store() -> None:
        app.state.store = PostgresRuntimeStore(repository)

    def successful_urlopen(request, timeout):
        body = json.loads(request.data.decode("utf-8"))
        user_message = body["messages"][1]["content"]
        return FakeResponse(f"已记录：{json.loads(user_message)['message']}")

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()
    monkeypatch.setattr(assistant_router, "urlopen", successful_urlopen)

    try:
        headers = auth_headers()
        first = client.post(
            "/api/assistant/chat",
            json={"conversation_id": "conv_dbfirst", "message": "查询 AI Brain 进度"},
            headers=headers,
        ).json()["data"]
        assert first["conversation_id"] == "conv_dbfirst"

        use_empty_postgres_runtime_store()
        conversations = client.get("/api/assistant/conversations", headers=headers).json()[
            "data"
        ]["items"]
        messages = client.get(
            "/api/assistant/conversations/conv_dbfirst/messages",
            headers=headers,
        ).json()["data"]["items"]
        assert [conversation["id"] for conversation in conversations] == ["conv_dbfirst"]
        assert conversations[0]["message_count"] == 2
        assert [message["role"] for message in messages] == ["user", "assistant"]
        assert messages[1]["content"] == "已记录：查询 AI Brain 进度"

        second = client.post(
            "/api/assistant/chat",
            json={"conversation_id": "conv_dbfirst", "message": "继续记录下一步"},
            headers=headers,
        ).json()["data"]
        assert second["conversation_id"] == "conv_dbfirst"

        use_empty_postgres_runtime_store()
        updated_conversation = client.get("/api/assistant/conversations", headers=headers).json()[
            "data"
        ]["items"][0]
        updated_messages = client.get(
            "/api/assistant/conversations/conv_dbfirst/messages",
            headers=headers,
        ).json()["data"]["items"]
        assert updated_conversation["message_count"] == 4
        assert updated_messages[-1]["content"] == "已记录：继续记录下一步"

        def failing_urlopen(_request, timeout):
            raise OSError("assistant gateway unavailable")

        monkeypatch.setattr(assistant_router, "urlopen", failing_urlopen)
        failed = client.post(
            "/api/assistant/chat",
            json={"message": "触发失败日志"},
            headers=headers,
        )
        assert failed.status_code == 502
        assert failed.json()["detail"]["code"] == "ASSISTANT_CHAT_FAILED"

        use_empty_postgres_runtime_store()
        logs = client.get(
            "/api/model-gateway/logs?purpose=assistant_chat",
            headers=headers,
        ).json()["data"]["items"]
        assert [log["status"] for log in logs].count("succeeded") == 2
        assert any(log["status"] == "failed" for log in logs)
        assert any(
            event["event_type"] == "assistant.chat_completed"
            for event in repository.audit_events_payload["audit_events"]
        )
        assert any(
            event["event_type"] == "model_gateway.called"
            and event["payload"]["status"] == "failed"
            for event in repository.audit_events_payload["audit_events"]
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_assistant_history_uses_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.assistant_chat_payload = {
        "assistant_conversations": {
            "conversation_repo_admin": {
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "conversation_repo_admin",
                "last_message_at": "2026-06-03T08:01:00+00:00",
                "message_count": 2,
                "product_id": "product_119",
                "title": "Admin 会话",
                "updated_at": "2026-06-03T08:01:00+00:00",
                "user_id": "user_admin",
            },
            "conversation_repo_reviewer": {
                "created_at": "2026-06-03T09:00:00+00:00",
                "id": "conversation_repo_reviewer",
                "last_message_at": "2026-06-03T09:01:00+00:00",
                "message_count": 1,
                "product_id": None,
                "title": "Reviewer 会话",
                "updated_at": "2026-06-03T09:01:00+00:00",
                "user_id": "user_reviewer",
            },
        },
        "assistant_messages": {
            "assistant_message_repo_admin_001": {
                "content": "admin question",
                "conversation_id": "conversation_repo_admin",
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "assistant_message_repo_admin_001",
                "role": "user",
                "suggestions": [],
                "user_id": "user_admin",
            },
            "assistant_message_repo_admin_002": {
                "content": "admin answer",
                "conversation_id": "conversation_repo_admin",
                "created_at": "2026-06-03T08:01:00+00:00",
                "id": "assistant_message_repo_admin_002",
                "model": "gpt-read",
                "role": "assistant",
                "suggestions": ["查看任务"],
                "user_id": "user_admin",
            },
            "assistant_message_repo_reviewer_001": {
                "content": "reviewer question",
                "conversation_id": "conversation_repo_reviewer",
                "created_at": "2026-06-03T09:00:00+00:00",
                "id": "assistant_message_repo_reviewer_001",
                "role": "user",
                "suggestions": [],
                "user_id": "user_reviewer",
            },
        },
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.assistant_conversations = {}
    stale_store.assistant_messages = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        admin_conversations = client.get(
            "/api/assistant/conversations",
            headers=auth_headers(),
        ).json()["data"]["items"]
        assert [item["id"] for item in admin_conversations] == ["conversation_repo_admin"]
        assert admin_conversations[0]["message_count"] == 2

        admin_messages = client.get(
            "/api/assistant/conversations/conversation_repo_admin/messages",
            headers=auth_headers(),
        ).json()["data"]["items"]
        assert [item["id"] for item in admin_messages] == [
            "assistant_message_repo_admin_001",
            "assistant_message_repo_admin_002",
        ]
        assert admin_messages[1]["model"] == "gpt-read"
        assert admin_messages[1]["suggestions"] == ["查看任务"]

        reviewer_conversations = client.get(
            "/api/assistant/conversations",
            headers=auth_headers("reviewer@example.com", "reviewer123"),
        ).json()["data"]["items"]
        assert [item["id"] for item in reviewer_conversations] == [
            "conversation_repo_reviewer"
        ]
        cross_user_messages = client.get(
            "/api/assistant/conversations/conversation_repo_admin/messages",
            headers=auth_headers("reviewer@example.com", "reviewer123"),
        )
        assert cross_user_messages.status_code == 404
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
