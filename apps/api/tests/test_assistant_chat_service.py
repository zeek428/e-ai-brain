from __future__ import annotations

import pytest

from app.core.store import MemoryStore
from app.services.assistant_chat import (
    AssistantChatRequest,
    AssistantServiceError,
    assistant_chat_response,
    assistant_conversation_messages_response,
    assistant_conversations_response,
)


def test_assistant_chat_service_owns_validation_and_gateway_errors():
    store = MemoryStore()
    user = {"id": "user_admin"}

    with pytest.raises(AssistantServiceError) as blank_error:
        assistant_chat_response(
            store,
            model_gateway_api_key="",
            model_gateway_base_url="",
            model_gateway_default_chat_model="",
            model_gateway_status="not_configured",
            payload=AssistantChatRequest(message="   "),
            user=user,
        )
    assert blank_error.value.status_code == 400
    assert blank_error.value.code == "VALIDATION_ERROR"

    with pytest.raises(AssistantServiceError) as gateway_error:
        assistant_chat_response(
            store,
            model_gateway_api_key="",
            model_gateway_base_url="",
            model_gateway_default_chat_model="",
            model_gateway_status="not_configured",
            payload=AssistantChatRequest(message="查询 AI Brain 进度"),
            user=user,
        )
    assert gateway_error.value.status_code == 400
    assert gateway_error.value.code == "MODEL_GATEWAY_CONFIG_INVALID"


def test_assistant_history_service_is_user_scoped():
    store = MemoryStore()
    store.assistant_conversations = {
        "conversation_admin": {
            "created_at": "2026-06-05T08:00:00+00:00",
            "id": "conversation_admin",
            "last_message_at": "2026-06-05T08:02:00+00:00",
            "message_count": 2,
            "product_id": "product_001",
            "title": "管理员会话",
            "updated_at": "2026-06-05T08:02:00+00:00",
            "user_id": "user_admin",
        },
        "conversation_reviewer": {
            "created_at": "2026-06-05T07:00:00+00:00",
            "id": "conversation_reviewer",
            "last_message_at": "2026-06-05T07:01:00+00:00",
            "message_count": 1,
            "product_id": None,
            "title": "评审会话",
            "updated_at": "2026-06-05T07:01:00+00:00",
            "user_id": "user_reviewer",
        },
    }
    store.assistant_messages = {
        "assistant_message_admin_001": {
            "content": "查询进度",
            "conversation_id": "conversation_admin",
            "created_at": "2026-06-05T08:00:00+00:00",
            "id": "assistant_message_admin_001",
            "model": None,
            "product_id": "product_001",
            "role": "user",
            "suggestions": [],
            "user_id": "user_admin",
        },
        "assistant_message_admin_002": {
            "content": "当前需求已进入测试。",
            "conversation_id": "conversation_admin",
            "created_at": "2026-06-05T08:02:00+00:00",
            "id": "assistant_message_admin_002",
            "model": "gpt-assistant",
            "product_id": "product_001",
            "role": "assistant",
            "suggestions": ["查看需求"],
            "user_id": "user_admin",
        },
    }

    conversations = assistant_conversations_response(store, user_id="user_admin")
    assert [item["id"] for item in conversations["items"]] == ["conversation_admin"]

    messages = assistant_conversation_messages_response(
        store,
        conversation_id="conversation_admin",
        user_id="user_admin",
    )
    assert [item["role"] for item in messages["items"]] == ["user", "assistant"]

    with pytest.raises(AssistantServiceError) as not_found:
        assistant_conversation_messages_response(
            store,
            conversation_id="conversation_admin",
            user_id="user_reviewer",
        )
    assert not_found.value.status_code == 404
    assert not_found.value.code == "NOT_FOUND"
