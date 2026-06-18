from __future__ import annotations

import threading

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


def test_assistant_chat_runs_explicitly_mentioned_scheduled_job_once_without_model_gateway():
    store = MemoryStore()
    store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

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
    store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "每周用户反馈洞察抽取",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

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
    store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

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
    store.scheduled_jobs["scheduled_job_feedback_insight"] = {
        "agent_id": None,
        "config_json": {},
        "created_at": "2026-06-16T08:00:00+00:00",
        "created_by": "user_admin",
        "cron_expression": None,
        "enabled": True,
        "execution_mode": "deterministic",
        "id": "scheduled_job_feedback_insight",
        "interval_seconds": None,
        "job_type": "dashboard_snapshot_refresh",
        "knowledge_document_ids": [],
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": 900,
        "max_retry_count": 0,
        "model_gateway_config_id": None,
        "name": "提取每周用户反馈有价值信息",
        "next_run_at": None,
        "plugin_action_id": None,
        "plugin_action_ids": [],
        "plugin_connection_id": None,
        "plugin_connection_ids": [],
        "plugin_input_mapping": {},
        "plugin_output_mapping": {},
        "product_id": None,
        "result_actions": [],
        "schedule_type": "manual",
        "skill_ids": [],
        "source_system": "ai-brain",
        "status": "active",
        "timeout_seconds": 600,
        "timezone": "Asia/Shanghai",
        "updated_at": "2026-06-16T08:00:00+00:00",
    }

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
