from app.core.persistence import PersistentMemoryStore


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
