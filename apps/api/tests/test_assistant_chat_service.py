from __future__ import annotations

import json
import threading
from time import perf_counter

import pytest

from app.core.store import MemoryStore
from app.services import assistant_chat as assistant_chat_service
from app.services.assistant_chat import (
    AssistantChatRequest,
    AssistantServiceError,
    assistant_chat_response,
    assistant_conversation_messages_response,
    assistant_conversations_response,
)
from app.services.assistant_history import ensure_assistant_conversation


ASSISTANT_RUNNABLE_PLUGIN_ID = "plugin_assistant_http"
ASSISTANT_RUNNABLE_CONNECTION_ID = "plugin_connection_assistant_test"
ASSISTANT_RUNNABLE_ACTION_ID = "plugin_action_assistant_test"


def seed_assistant_plugin_action_runtime(store: MemoryStore) -> None:
    now = "2026-06-16T08:00:00+00:00"
    store.integration_plugins[ASSISTANT_RUNNABLE_PLUGIN_ID] = {
        "category": "general",
        "code": "assistant_http",
        "created_at": now,
        "description": "助手测试 HTTP 插件。",
        "id": ASSISTANT_RUNNABLE_PLUGIN_ID,
        "is_system": False,
        "name": "助手测试 HTTP 插件",
        "plugin_type": "http",
        "protocol": "http",
        "risk_level": "low",
        "status": "active",
        "updated_at": now,
    }
    store.plugin_connections[ASSISTANT_RUNNABLE_CONNECTION_ID] = {
        "auth_config": {},
        "auth_type": "none",
        "created_at": now,
        "created_by": "user_admin",
        "endpoint_url": "https://assistant-plugin.example.com",
        "environment": "prod",
        "id": ASSISTANT_RUNNABLE_CONNECTION_ID,
        "max_retries": 0,
        "name": "助手测试连接",
        "plugin_id": ASSISTANT_RUNNABLE_PLUGIN_ID,
        "request_config": {},
        "status": "active",
        "timeout_seconds": 30,
        "updated_at": now,
    }
    store.plugin_actions[ASSISTANT_RUNNABLE_ACTION_ID] = {
        "action_type": "http_request",
        "code": "assistant_test_action",
        "connection_id": ASSISTANT_RUNNABLE_CONNECTION_ID,
        "created_at": now,
        "id": ASSISTANT_RUNNABLE_ACTION_ID,
        "name": "助手测试动作",
        "plugin_id": ASSISTANT_RUNNABLE_PLUGIN_ID,
        "request_config": {
            "method": "GET",
            "mock_response_json": {"records_imported": 0},
            "path": "/ok",
        },
        "result_mapping": {
            "records_imported_path": "$.records_imported",
            "write_target": "scheduled_job_result",
        },
        "status": "active",
        "updated_at": now,
    }


def seed_assistant_runnable_job(
    store: MemoryStore,
    *,
    job_id: str = "scheduled_job_feedback_insight",
    name: str = "提取每周用户反馈有价值信息",
    **overrides,
) -> dict[str, object]:
    seed_assistant_plugin_action_runtime(store)
    now = "2026-06-16T08:00:00+00:00"
    job: dict[str, object] = {
        "agent_id": None,
        "config_json": {},
        "created_at": now,
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": job_id,
        "interval_seconds": None,
        "job_type": "plugin_action_invoke",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": name,
        "next_run_at": None,
        "plugin_action_id": ASSISTANT_RUNNABLE_ACTION_ID,
        "plugin_action_ids": [ASSISTANT_RUNNABLE_ACTION_ID],
        "plugin_connection_id": ASSISTANT_RUNNABLE_CONNECTION_ID,
        "plugin_connection_ids": [ASSISTANT_RUNNABLE_CONNECTION_ID],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {
            "records_imported_path": "$.records_imported",
            "write_target": "scheduled_job_result",
        },
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": now,
    }
    job.update(overrides)
    store.scheduled_jobs[job_id] = job
    return job


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


def test_assistant_history_service_collapses_duplicate_command_conversations():
    store = MemoryStore()
    command_title = "@提取每周用户反馈有价值信息 执行一次"
    store.assistant_conversations = {
        "conversation_latest_feedback": {
            "created_at": "2026-06-20T08:00:00+00:00",
            "id": "conversation_latest_feedback",
            "last_message_at": "2026-06-20T08:03:00+00:00",
            "message_count": 2,
            "product_id": "product_119",
            "title": command_title,
            "updated_at": "2026-06-20T08:03:00+00:00",
            "user_id": "user_admin",
        },
        "conversation_old_feedback": {
            "created_at": "2026-06-19T08:00:00+00:00",
            "id": "conversation_old_feedback",
            "last_message_at": "2026-06-19T08:03:00+00:00",
            "message_count": 2,
            "product_id": "product_119",
            "title": f"  {command_title}  ",
            "updated_at": "2026-06-19T08:03:00+00:00",
            "user_id": "user_admin",
        },
        "conversation_unique": {
            "created_at": "2026-06-18T08:00:00+00:00",
            "id": "conversation_unique",
            "last_message_at": "2026-06-18T08:01:00+00:00",
            "message_count": 1,
            "product_id": "product_119",
            "title": "当前系统状态",
            "updated_at": "2026-06-18T08:01:00+00:00",
            "user_id": "user_admin",
        },
    }

    collapsed = assistant_conversations_response(store, user_id="user_admin")

    assert collapsed["total"] == 2
    feedback_item = collapsed["items"][0]
    assert feedback_item["id"] == "conversation_latest_feedback"
    assert feedback_item["duplicate_count"] == 2
    assert feedback_item["duplicate_conversation_ids"] == ["conversation_old_feedback"]
    assert feedback_item["collapsed_message_count"] == 4
    assert feedback_item["collapsed_conversation_ids"] == [
        "conversation_latest_feedback",
        "conversation_old_feedback",
    ]
    assert "duplicate_count" not in collapsed["items"][1]

    expanded = assistant_conversations_response(
        store,
        collapse_duplicates=False,
        user_id="user_admin",
    )
    assert expanded["total"] == 3
    assert [item["id"] for item in expanded["items"]] == [
        "conversation_latest_feedback",
        "conversation_old_feedback",
        "conversation_unique",
    ]


def test_assistant_history_prefers_command_signature_when_collapsing():
    store = MemoryStore()
    store.assistant_conversations = {
        "conversation_create_requirement": {
            "command_signature": "signature_requirement",
            "context_scope": "product:product_119",
            "created_at": "2026-06-20T08:00:00+00:00",
            "id": "conversation_create_requirement",
            "last_message_at": "2026-06-20T08:03:00+00:00",
            "message_count": 2,
            "product_id": "product_119",
            "source_message_hash": "hash_requirement",
            "title": "新建需求",
            "updated_at": "2026-06-20T08:03:00+00:00",
            "user_id": "user_admin",
        },
        "conversation_create_bug": {
            "command_signature": "signature_bug",
            "context_scope": "product:product_119",
            "created_at": "2026-06-20T07:00:00+00:00",
            "id": "conversation_create_bug",
            "last_message_at": "2026-06-20T07:03:00+00:00",
            "message_count": 2,
            "product_id": "product_119",
            "source_message_hash": "hash_bug",
            "title": "新建需求",
            "updated_at": "2026-06-20T07:03:00+00:00",
            "user_id": "user_admin",
        },
    }

    collapsed = assistant_conversations_response(store, user_id="user_admin")

    assert collapsed["total"] == 2
    assert [item["command_signature"] for item in collapsed["items"]] == [
        "signature_requirement",
        "signature_bug",
    ]


def test_assistant_history_does_not_collapse_blank_titles():
    store = MemoryStore()
    store.assistant_conversations = {
        "conversation_blank_first": {
            "created_at": "2026-06-20T08:00:00+00:00",
            "id": "conversation_blank_first",
            "last_message_at": "2026-06-20T08:02:00+00:00",
            "message_count": 1,
            "product_id": None,
            "title": "",
            "updated_at": "2026-06-20T08:02:00+00:00",
            "user_id": "user_admin",
        },
        "conversation_blank_second": {
            "created_at": "2026-06-20T07:00:00+00:00",
            "id": "conversation_blank_second",
            "last_message_at": "2026-06-20T07:02:00+00:00",
            "message_count": 1,
            "product_id": None,
            "title": "   ",
            "updated_at": "2026-06-20T07:02:00+00:00",
            "user_id": "user_admin",
        },
    }

    collapsed = assistant_conversations_response(store, user_id="user_admin")

    assert collapsed["total"] == 2
    assert [item["id"] for item in collapsed["items"]] == [
        "conversation_blank_first",
        "conversation_blank_second",
    ]


def test_assistant_history_paginates_conversations_with_cursor():
    store = MemoryStore()
    store.assistant_conversations = {
        f"conversation_{index}": {
            "created_at": f"2026-06-20T0{index}:00:00+00:00",
            "id": f"conversation_{index}",
            "last_message_at": f"2026-06-20T0{index}:01:00+00:00",
            "message_count": 1,
            "product_id": None,
            "title": f"对话 {index}",
            "updated_at": f"2026-06-20T0{index}:01:00+00:00",
            "user_id": "user_admin",
        }
        for index in range(1, 5)
    }

    first_page = assistant_conversations_response(
        store,
        collapse_duplicates=False,
        limit=2,
        user_id="user_admin",
    )

    assert [item["id"] for item in first_page["items"]] == ["conversation_4", "conversation_3"]
    assert first_page["limit"] == 2
    assert first_page["next_cursor"] == "2026-06-20T03:01:00+00:00|conversation_3"

    second_page = assistant_conversations_response(
        store,
        collapse_duplicates=False,
        cursor=first_page["next_cursor"],
        limit=2,
        user_id="user_admin",
    )

    assert [item["id"] for item in second_page["items"]] == ["conversation_2", "conversation_1"]
    assert second_page["next_cursor"] is None


def test_assistant_history_collapsed_pagination_fills_page_after_duplicate_window():
    store = MemoryStore()
    duplicate_title = "@提取每周用户反馈有价值信息 执行一次"
    store.assistant_conversations = {
        f"conversation_duplicate_{index:02d}": {
            "created_at": f"2026-06-20T09:{30 - index:02d}:00+00:00",
            "id": f"conversation_duplicate_{index:02d}",
            "last_message_at": f"2026-06-20T09:{30 - index:02d}:00+00:00",
            "message_count": 2,
            "product_id": "product_119",
            "title": duplicate_title,
            "updated_at": f"2026-06-20T09:{30 - index:02d}:00+00:00",
            "user_id": "user_admin",
        }
        for index in range(10)
    }
    store.assistant_conversations.update(
        {
            "conversation_unique_next": {
                "created_at": "2026-06-20T09:20:00+00:00",
                "id": "conversation_unique_next",
                "last_message_at": "2026-06-20T09:20:00+00:00",
                "message_count": 1,
                "product_id": "product_119",
                "title": "唯一对话一",
                "updated_at": "2026-06-20T09:20:00+00:00",
                "user_id": "user_admin",
            },
            "conversation_unique_tail": {
                "created_at": "2026-06-20T09:19:00+00:00",
                "id": "conversation_unique_tail",
                "last_message_at": "2026-06-20T09:19:00+00:00",
                "message_count": 1,
                "product_id": "product_119",
                "title": "唯一对话二",
                "updated_at": "2026-06-20T09:19:00+00:00",
                "user_id": "user_admin",
            },
        }
    )

    first_page = assistant_conversations_response(
        store,
        limit=2,
        user_id="user_admin",
    )

    assert [item["id"] for item in first_page["items"]] == [
        "conversation_duplicate_00",
        "conversation_unique_next",
    ]
    assert first_page["items"][0]["duplicate_count"] == 10
    assert first_page["items"][0]["collapsed_message_count"] == 20
    assert first_page["next_cursor"] == (
        "2026-06-20T09:20:00+00:00|conversation_unique_next"
    )

    second_page = assistant_conversations_response(
        store,
        cursor=first_page["next_cursor"],
        limit=2,
        user_id="user_admin",
    )

    assert [item["id"] for item in second_page["items"]] == ["conversation_unique_tail"]
    assert second_page["next_cursor"] is None


def test_ensure_assistant_conversation_reuses_existing_command_conversation():
    store = MemoryStore()
    user_id = "user_admin"
    message = "@提取每周用户反馈有价值信息 执行一次"

    first = ensure_assistant_conversation(
        store,
        conversation_id=None,
        message=message,
        now="2026-06-20T08:00:00+00:00",
        product_id="product_119",
        user={"id": user_id},
    )
    second = ensure_assistant_conversation(
        store,
        conversation_id=None,
        message=message,
        now="2026-06-20T08:01:00+00:00",
        product_id="product_119",
        user={"id": user_id},
    )
    natural_first = ensure_assistant_conversation(
        store,
        conversation_id=None,
        message="查询当前系统状态",
        now="2026-06-20T08:02:00+00:00",
        product_id="product_119",
        user={"id": user_id},
    )
    natural_second = ensure_assistant_conversation(
        store,
        conversation_id=None,
        message="查询当前系统状态",
        now="2026-06-20T08:03:00+00:00",
        product_id="product_119",
        user={"id": user_id},
    )

    assert second["id"] == first["id"]
    assert first["command_signature"]
    assert first["context_scope"] == "product:product_119"
    assert first["source_message_hash"]
    assert natural_second["id"] != natural_first["id"]


def test_ensure_assistant_conversation_reuses_repository_command_conversation():
    store = MemoryStore()
    message = "@提取每周用户反馈有价值信息 执行一次"
    existing = ensure_assistant_conversation(
        MemoryStore(),
        conversation_id=None,
        message=message,
        now="2026-06-20T08:00:00+00:00",
        product_id="product_119",
        user={"id": "user_admin"},
    )
    existing["id"] = "conversation_repository_reused"

    class Repository:
        def __init__(self):
            self.request: dict[str, str] | None = None

        def list_assistant_conversations(self, *, user_id: str):
            del user_id
            return []

        def list_assistant_conversation_messages(self, *, conversation_id: str, user_id: str):
            del conversation_id, user_id
            return []

        def find_reusable_assistant_conversation(
            self,
            *,
            command_signature: str,
            context_scope: str,
            user_id: str,
        ):
            self.request = {
                "command_signature": command_signature,
                "context_scope": context_scope,
                "user_id": user_id,
            }
            return dict(existing)

    repository = Repository()
    store.repository = repository

    reused = ensure_assistant_conversation(
        store,
        conversation_id=None,
        message=message,
        now="2026-06-20T08:01:00+00:00",
        product_id="product_119",
        user={"id": "user_admin"},
    )

    assert reused["id"] == "conversation_repository_reused"
    assert repository.request == {
        "command_signature": existing["command_signature"],
        "context_scope": "product:product_119",
        "user_id": "user_admin",
    }


def test_assistant_chat_persists_run_and_message_lifecycle_for_model_success():
    store = MemoryStore()
    user = {"id": "user_admin", "roles": ["admin"]}

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
                                        "answer": "当前进展正常。",
                                        "suggestions": ["查看需求进展"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 6, "prompt_tokens": 20, "total_tokens": 26},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    response = assistant_chat_response(
        store,
        model_gateway_api_key="test-key",
        model_gateway_base_url="https://model.example/v1",
        model_gateway_default_chat_model="assistant-test",
        model_gateway_status="configured",
        payload=AssistantChatRequest(
            client_request_id="client_request_success",
            message="查询 AI Brain 进展",
            run_id="assistant_chat_run_success",
        ),
        urlopen_func=lambda _request, timeout=None: FakeResponse(),
        user=user,
    )

    assert response["run_id"] == "assistant_chat_run_success"
    assert response["run"]["status"] == "succeeded"
    run = store.assistant_chat_runs["assistant_chat_run_success"]
    assert run["status"] == "succeeded"
    messages = list(store.assistant_messages.values())
    assert [message["status"] for message in messages] == ["completed", "completed"]
    assert all(message["run_id"] == "assistant_chat_run_success" for message in messages)
    assert messages[0]["client_request_id"] == "client_request_success"


def test_assistant_chat_cancel_run_marks_turn_cancelled_after_model_returns():
    store = MemoryStore()
    user = {"id": "user_admin", "roles": ["admin"]}

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
                                        "answer": "这条回答不应进入历史。",
                                        "suggestions": ["不应显示"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 6, "prompt_tokens": 20, "total_tokens": 26},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout=None):
        assistant_chat_service.cancel_assistant_chat_run_response(
            store,
            reason="test_cancel",
            run_id="assistant_chat_run_cancel",
            user=user,
        )
        return FakeResponse()

    response = assistant_chat_response(
        store,
        model_gateway_api_key="test-key",
        model_gateway_base_url="https://model.example/v1",
        model_gateway_default_chat_model="assistant-test",
        model_gateway_status="configured",
        payload=AssistantChatRequest(
            client_request_id="client_request_cancel",
            message="请生成长分析",
            run_id="assistant_chat_run_cancel",
        ),
        urlopen_func=fake_urlopen,
        user=user,
    )

    assert response["model"] == "assistant-cancelled"
    assert response["message"]["status"] == "cancelled"
    run = store.assistant_chat_runs["assistant_chat_run_cancel"]
    assert run["status"] == "cancelled"
    assert run["cancel_reason"] == "test_cancel"
    contents = [message["content"] for message in store.assistant_messages.values()]
    assert "这条回答不应进入历史。" not in contents
    assert [message["status"] for message in store.assistant_messages.values()] == [
        "cancelled",
        "cancelled",
    ]


def test_assistant_chat_cancel_run_returns_before_blocking_model_response_finishes():
    store = MemoryStore()
    user = {"id": "user_admin", "roles": ["admin"]}
    request_started = threading.Event()
    release_response = threading.Event()

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
                                        "answer": "这条慢响应不应落库。",
                                        "suggestions": ["不应显示"],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ],
                    "usage": {"completion_tokens": 6, "prompt_tokens": 20, "total_tokens": 26},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout=None):
        request_started.set()
        release_response.wait(timeout=2)
        return FakeResponse()

    def cancel_after_request_starts():
        assert request_started.wait(timeout=1)
        assistant_chat_service.cancel_assistant_chat_run_response(
            store,
            reason="test_cancel_without_waiting",
            run_id="assistant_chat_run_async_cancel",
            user=user,
        )

    canceller = threading.Thread(target=cancel_after_request_starts)
    canceller.start()

    started = perf_counter()
    response = assistant_chat_response(
        store,
        model_gateway_api_key="test-key",
        model_gateway_base_url="https://model.example/v1",
        model_gateway_default_chat_model="assistant-test",
        model_gateway_status="configured",
        payload=AssistantChatRequest(
            client_request_id="client_request_async_cancel",
            message="请生成非常长的分析",
            run_id="assistant_chat_run_async_cancel",
        ),
        urlopen_func=fake_urlopen,
        user=user,
    )
    elapsed_seconds = perf_counter() - started
    release_response.set()
    canceller.join(timeout=1)

    assert elapsed_seconds < 1
    assert response["model"] == "assistant-cancelled"
    assert response["message"]["status"] == "cancelled"
    assert store.assistant_chat_runs["assistant_chat_run_async_cancel"]["status"] == "cancelled"
    assert "这条慢响应不应落库。" not in [
        message["content"] for message in store.assistant_messages.values()
    ]


def test_assistant_chat_runs_explicitly_mentioned_scheduled_job_once_without_model_gateway():
    store = MemoryStore()
    seed_assistant_runnable_job(store)

    response = assistant_chat_response(
        store,
        model_gateway_api_key="",
        model_gateway_base_url="",
        model_gateway_default_chat_model="",
        model_gateway_status="not_configured",
        payload=AssistantChatRequest(
            message="@提取每周用户反馈有价值信息 执行一次",
        ),
        user={"id": "user_admin", "roles": ["admin"]},
    )

    assert response["model"] == "assistant-deterministic"
    assert "已执行" in response["message"]["content"]
    assert len(store.scheduled_job_runs) == 1
    run = next(iter(store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_insight"
    assert run["trigger_type"] == "manual"
    assert run["status"] == "succeeded"
    assert run["triggered_by_assistant"] is True
    assert response["message"]["references"] == [
        {
            "id": "scheduled_job_feedback_insight",
            "title": "提取每周用户反馈有价值信息",
            "type": "scheduled_job",
            "url": "/tasks/scheduled-jobs?job_id=scheduled_job_feedback_insight",
        },
        {
            "id": run["id"],
            "title": f"提取每周用户反馈有价值信息 / {run['status']}",
            "type": "scheduled_job_run",
            "url": f"/tasks/scheduled-jobs?run_id={run['id']}",
        },
    ]
    assert response["message"]["tool_results"] == [
        {
            "intent": "scheduled_job_run_once",
            "intent_code": "scheduled_job_run_once",
            "intent_confidence": 0.95,
            "items": [
                {
                    "id": run["id"],
                    "records_imported": 0,
                    "scheduled_job_id": "scheduled_job_feedback_insight",
                    "status": "succeeded",
                    "title": f"提取每周用户反馈有价值信息 / {run['status']}",
                    "trigger_type": "manual",
                    "type": "scheduled_job_run",
                    "url": f"/tasks/scheduled-jobs?run_id={run['id']}",
                }
            ],
            "references": [
                {
                    "id": run["id"],
                    "title": f"提取每周用户反馈有价值信息 / {run['status']}",
                    "type": "scheduled_job_run",
                    "url": f"/tasks/scheduled-jobs?run_id={run['id']}",
                }
            ],
            "required_refs": ["scheduled_job"],
            "summary": {
                "error_code": None,
                "error_message": None,
                "records_imported": 0,
                "run_id": run["id"],
                "scheduled_job_id": "scheduled_job_feedback_insight",
                "scheduled_job_name": "提取每周用户反馈有价值信息",
                "status": "succeeded",
                "trigger_type": "manual",
            },
            "tool": "assistant.scheduled_job_run",
        }
    ]


def test_assistant_chat_runs_weekly_feedback_alias_job_once_without_model_gateway():
    store = MemoryStore()
    seed_assistant_runnable_job(store, name="每周用户反馈洞察抽取")

    response = assistant_chat_response(
        store,
        model_gateway_api_key="",
        model_gateway_base_url="",
        model_gateway_default_chat_model="",
        model_gateway_status="not_configured",
        payload=AssistantChatRequest(
            message="@提取每周用户反馈有价值信息 执行一次",
        ),
        user={"id": "user_admin", "roles": ["admin"]},
    )

    assert response["model"] == "assistant-deterministic"
    assert "已执行" in response["message"]["content"]
    run = next(iter(store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_insight"
    assert response["message"]["references"][0] == {
        "id": "scheduled_job_feedback_insight",
        "title": "每周用户反馈洞察抽取",
        "type": "scheduled_job",
        "url": "/tasks/scheduled-jobs?job_id=scheduled_job_feedback_insight",
    }


def test_assistant_chat_allows_run_once_with_scheduled_job_permission():
    store = MemoryStore()
    seed_assistant_runnable_job(store)

    response = assistant_chat_response(
        store,
        model_gateway_api_key="",
        model_gateway_base_url="",
        model_gateway_default_chat_model="",
        model_gateway_status="not_configured",
        payload=AssistantChatRequest(
            message="@提取每周用户反馈有价值信息 执行一次",
        ),
        user={
            "id": "user_ops",
            "permissions": ["system.scheduled_jobs.run"],
            "roles": ["release_owner"],
        },
    )

    assert response["model"] == "assistant-deterministic"
    assert "已执行" in response["message"]["content"]
    run = next(iter(store.scheduled_job_runs.values()))
    assert run["scheduled_job_id"] == "scheduled_job_feedback_insight"
    assert response["message"]["tool_results"][0]["summary"]["status"] == "succeeded"


def test_assistant_chat_generates_run_once_draft_with_scheduled_job_permission():
    store = MemoryStore()

    response = assistant_chat_response(
        store,
        model_gateway_api_key="",
        model_gateway_base_url="",
        model_gateway_default_chat_model="",
        model_gateway_status="not_configured",
        payload=AssistantChatRequest(
            message="@提取每周用户反馈有价值信息 执行一次",
        ),
        user={
            "id": "user_ops",
            "permissions": ["system.scheduled_jobs.run"],
            "roles": ["release_owner"],
        },
    )

    assert response["model"] == "assistant-deterministic"
    assert "尚未执行" in response["message"]["content"]
    assert store.scheduled_job_runs == {}
    draft_result = response["message"]["tool_results"][0]
    assert draft_result["tool"] == "assistant.action_draft"
    assert draft_result["intent"] == "scheduled_job_draft"
    assert draft_result["summary"]["run_once_requested"] is True
    draft_item = draft_result["items"][0]
    assert draft_item["server_draft_id"] in store.assistant_action_drafts
    assert draft_item["payload"]["config_json"]["assistant_run_once_request"] == {
        "requested": True,
        "source_message": "@提取每周用户反馈有价值信息 执行一次",
    }


def test_assistant_chat_returns_running_record_for_long_ai_job_once_without_waiting(
    monkeypatch,
):
    store = MemoryStore()
    store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": "agent_feedback",
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "ai_generated",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "user_feedback_insight_extract",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": "model_gateway_feedback",
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": "plugin_action_feedback",
        "plugin_action_ids": [],
        "plugin_connection_id": "plugin_connection_feedback",
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": ["skill_feedback"],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }
    started = threading.Event()
    release = threading.Event()
    completed = threading.Event()

    def fake_run_scheduled_job_response(
        *,
        current_store,
        job_id,
        source_run_id,
        trigger_type,
        user,
    ):
        del source_run_id, user
        started.set()
        run_id = current_store.new_id("scheduled_job_run")
        run = {
            "collector_run_id": "collector_run_feedback_insight",
            "config_snapshot": {},
            "created_at": "2026-06-16T08:01:00+00:00",
            "error_code": None,
            "error_message": None,
            "finished_at": None,
            "id": run_id,
            "plugin_invocation_log_id": None,
            "records_imported": 0,
            "result_summary": {},
            "scheduled_for": "2026-06-16T08:01:00+00:00",
            "scheduled_job_id": job_id,
            "source_run_id": None,
            "started_at": "2026-06-16T08:01:00+00:00",
            "status": "running",
            "trigger_type": trigger_type,
            "updated_at": "2026-06-16T08:01:00+00:00",
        }
        current_store.scheduled_job_runs[run_id] = run
        release.wait(timeout=0.5)
        completed.set()
        run = {
            **run,
            "finished_at": "2026-06-16T08:02:00+00:00",
            "records_imported": 19,
            "status": "succeeded",
            "updated_at": "2026-06-16T08:02:00+00:00",
        }
        current_store.scheduled_job_runs[run_id] = run
        return run

    monkeypatch.setattr(
        assistant_chat_service,
        "run_scheduled_job_response",
        fake_run_scheduled_job_response,
    )

    response = assistant_chat_service.assistant_chat_response(
        store,
        model_gateway_api_key="",
        model_gateway_base_url="",
        model_gateway_default_chat_model="",
        model_gateway_status="not_configured",
        payload=AssistantChatRequest(
            message="@提取每周用户反馈有价值信息 执行一次",
        ),
        user={"id": "user_admin", "roles": ["admin"]},
    )

    assert started.is_set()
    assert not completed.is_set()
    assert response["model"] == "assistant-deterministic"
    assert "已触发" in response["message"]["content"]
    assert response["message"]["tool_results"][0]["summary"]["status"] == "running"
    release.set()
    assert completed.wait(timeout=1)


def test_assistant_chat_explains_run_once_waiting_for_ai_executor(monkeypatch):
    store = MemoryStore()
    seed_assistant_runnable_job(store)

    def fake_run_scheduled_job_response(
        *,
        current_store,
        job_id,
        source_run_id,
        trigger_type,
        user,
    ):
        del source_run_id, user
        run = {
            "collector_run_id": "collector_run_feedback_insight",
            "config_snapshot": {},
            "created_at": "2026-06-16T08:01:00+00:00",
            "error_code": None,
            "error_message": None,
            "finished_at": None,
            "id": "scheduled_job_run_feedback_waiting_runner",
            "plugin_invocation_log_id": "plugin_invocation_log_feedback",
            "records_imported": 0,
            "result_summary": {
                "execution_nodes": {
                    "result_action": {
                        "label": "结果动作反馈内容",
                        "status": "waiting_runner",
                    },
                    "runner_execution": {
                        "executor_type": "openclaw",
                        "label": "AI 执行器执行内容",
                        "runner_task_id": "ai_executor_task_feedback",
                        "status": "queued",
                    },
                }
            },
            "scheduled_for": "2026-06-16T08:01:00+00:00",
            "scheduled_job_id": job_id,
            "source_run_id": None,
            "started_at": "2026-06-16T08:01:00+00:00",
            "status": "running",
            "trigger_type": trigger_type,
            "updated_at": "2026-06-16T08:01:00+00:00",
        }
        current_store.scheduled_job_runs[run["id"]] = run
        return run

    monkeypatch.setattr(
        assistant_chat_service,
        "run_scheduled_job_response",
        fake_run_scheduled_job_response,
    )

    response = assistant_chat_service.assistant_chat_response(
        store,
        model_gateway_api_key="",
        model_gateway_base_url="",
        model_gateway_default_chat_model="",
        model_gateway_status="not_configured",
        payload=AssistantChatRequest(
            message="@提取每周用户反馈有价值信息 执行一次",
        ),
        user={"id": "user_admin", "roles": ["admin"]},
    )

    assert "已触发" in response["message"]["content"]
    assert "等待 AI 执行器" in response["message"]["content"]
    run_item = response["message"]["tool_results"][0]["items"][0]
    assert run_item["progress_text"] == (
        "等待 AI 执行器接单：openclaw / ai_executor_task_feedback"
    )
    assert response["message"]["tool_results"][0]["summary"]["progress_text"] == (
        "等待 AI 执行器接单：openclaw / ai_executor_task_feedback"
    )
