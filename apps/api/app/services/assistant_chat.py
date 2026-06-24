from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from time import perf_counter, sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen as default_urlopen

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.core.store import MemoryStore
from app.services.assistant_action_drafts import (
    persist_assistant_action_drafts_from_tool_results,
)
from app.services.assistant_context import (
    assistant_chat_messages as assistant_context_chat_messages,
)
from app.services.assistant_context import (
    assistant_conversation_history_context,
    assistant_reference_candidates,
    assistant_response_content,
    build_assistant_system_context,
    public_assistant_message,
)
from app.services.assistant_errors import AssistantServiceError
from app.services.assistant_history import (
    append_assistant_message,
    assistant_conversation_messages_response,
    assistant_conversations_response,
    ensure_assistant_conversation,
)
from app.services.assistant_metrics import assistant_metrics_response
from app.services.assistant_references import (
    AssistantReferenceError,
    assistant_reference_matches_query,
    resolve_assistant_references,
)
from app.services.assistant_request_context import (
    assistant_request_store as assistant_context_request_store,
)
from app.services.assistant_request_context import (
    runtime_repository,
    save_assistant_chat_records,
)
from app.services.assistant_tools import assistant_tool_results
from app.services.model_gateway_logging import (
    estimate_tokens,
    model_gateway_log,
    openai_usage_tokens,
)
from app.services.scheduled_jobs import persist_record, run_scheduled_job_response

ASSISTANT_ACCESS_ROLES = {
    "admin",
    "knowledge_owner",
    "product_owner",
    "rd_owner",
    "reviewer",
    "release_owner",
    "test_owner",
    "tester",
}
SCHEDULED_JOB_RUN_ONCE_KEYWORDS = (
    "执行一次",
    "执行一下",
    "运行一次",
    "运行一下",
    "跑一次",
    "跑一下",
    "立即执行",
    "立即运行",
    "手动执行",
    "run once",
    "run now",
    "execute once",
)
SCHEDULED_JOB_RUN_NEGATION_KEYWORDS = ("不要执行", "别执行", "不执行", "不要运行", "别运行")
ASSISTANT_ASYNC_SCHEDULED_JOB_TYPES = {
    "iteration_plan_suggestion_generate",
    "online_log_ai_analysis",
    "user_feedback_insight_extract",
}
ASSISTANT_ASYNC_RUN_START_TIMEOUT_SECONDS = 2.0
ASSISTANT_ASYNC_RUN_POLL_SECONDS = 0.05
ASSISTANT_TRACKED_RUN_STATUSES = {"queued", "running"}
SCHEDULED_JOB_MANAGE_PERMISSION = "system.scheduled_jobs.manage"
SCHEDULED_JOB_RUN_PERMISSION = "system.scheduled_jobs.run"
TASK_CREATION_WIZARD_STEPS = ["数据来源", "AI处理", "结果动作", "调度策略", "确认执行"]
TASK_CREATION_GUIDE_ITEMS = [
    {
        "dependencies": [],
        "description": "选择或 @ 一个已规划需求后，生成可确认的产品详细设计研发任务草案。",
        "draft_action": "create_rd_task",
        "prompt": "我要新增研发任务，请先让我 @需求 后生成产品详细设计任务草案",
        "title": "研发任务",
        "type": "rd_task",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["数据连接", "AI能力", "结果动作"],
        "description": "按数据来源、AI处理、结果动作和调度策略生成可确认的定时作业草案。",
        "draft_action": "create_scheduled_job",
        "prompt": "帮我新增定时作业，先按数据来源、AI处理、结果动作和调度策略生成草案",
        "title": "定时作业",
        "type": "scheduled_job",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["业务场景", "模型网关", "Skill", "AI角色"],
        "description": "选择代码巡检或线上日志等场景后，生成 Skill 和 AI角色配置草案。",
        "draft_action": "create_ai_capability",
        "prompt": "帮我新增代码巡检 AI能力配置草案，生成 Skill 和 AI角色草案",
        "title": "AI能力配置",
        "type": "ai_capability",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["插件连接"],
        "description": "为 GitHub、GitLab、邮箱等插件生成结果动作草案，确认前不写入真实动作。",
        "draft_action": "create_plugin_action",
        "prompt": "帮我新增插件动作，先生成可确认的动作草案",
        "title": "插件动作",
        "type": "plugin_action",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["GitHub/GitLab 连接", "代码巡检动作"],
        "description": "按仓库、分支、AI处理和结果动作生成代码巡检定时作业草案。",
        "draft_action": "create_scheduled_job",
        "prompt": "帮我配置代码巡检定时作业草案",
        "title": "代码巡检",
        "type": "code_inspection",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
    {
        "dependencies": ["用户反馈数据连接", "反馈洞察动作"],
        "description": "抽取每周用户反馈、经过 AI 处理后写入反馈洞察结果。",
        "draft_action": "create_scheduled_job",
        "prompt": "帮我配置每周用户反馈洞察定时作业草案",
        "title": "反馈洞察",
        "type": "feedback_insight",
        "wizard_steps": TASK_CREATION_WIZARD_STEPS,
    },
]
_ASSISTANT_CHAT_RUN_INTERRUPTERS: dict[str, Callable[[], None]] = {}
_ASSISTANT_CHAT_RUN_INTERRUPTERS_LOCK = threading.Lock()

__all__ = [
    "ASSISTANT_ACCESS_ROLES",
    "AssistantChatRequest",
    "AssistantServiceError",
    "cancel_assistant_chat_run_response",
    "assistant_chat_response",
    "assistant_chat_runs_response",
    "assistant_conversation_messages_response",
    "assistant_conversations_response",
    "assistant_request_store",
]


class AssistantChatRequest(BaseModel):
    message: str
    client_request_id: str | None = None
    conversation_id: str | None = None
    product_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    references: list[dict[str, Any]] = Field(default_factory=list)
    run_id: str | None = None


class _AssistantGatewayRequestFailed(Exception):
    def __init__(self, log: dict[str, Any]):
        super().__init__("Assistant model gateway request failed")
        self.log = log


class _AssistantGatewayRequestCancelled(Exception):
    pass


def assistant_request_store(current_store: MemoryStore, *, user_id: str) -> Any:
    return assistant_context_request_store(current_store, user_id=user_id)


def assistant_chat_response(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
    model_gateway_api_key: str,
    model_gateway_base_url: str,
    model_gateway_default_chat_model: str,
    model_gateway_status: str,
    urlopen_func: Callable[[Any, int], Any] = default_urlopen,
) -> dict[str, Any]:
    message = _ensure_non_blank(payload.message, "message")
    normalized_payload = AssistantChatRequest(
        client_request_id=payload.client_request_id,
        context=payload.context,
        conversation_id=payload.conversation_id,
        message=message,
        product_id=payload.product_id,
        references=payload.references,
        run_id=payload.run_id,
    )
    if (
        normalized_payload.product_id
        and normalized_payload.product_id not in current_store.products
    ):
        raise AssistantServiceError(404, "NOT_FOUND", "Product not found")
    if normalized_payload.conversation_id:
        existing_conversation = current_store.assistant_conversations.get(
            normalized_payload.conversation_id,
        )
        if existing_conversation is not None and existing_conversation.get("user_id") != user["id"]:
            raise AssistantServiceError(404, "NOT_FOUND", "Assistant conversation not found")

    turn = _start_assistant_chat_run(
        current_store,
        message=message,
        normalized_payload=normalized_payload,
        user=user,
    )
    try:
        if _assistant_chat_run_is_cancelled(current_store, turn["chat_run"]["id"], user=user):
            return _persist_assistant_chat_cancelled(
                current_store,
                normalized_payload=normalized_payload,
                turn=turn,
                user=user,
            )
        deterministic_output = _deterministic_assistant_output(
            current_store,
            payload=normalized_payload,
            user=user,
        )
        if deterministic_output is not None:
            if _assistant_chat_run_is_cancelled(current_store, turn["chat_run"]["id"], user=user):
                return _persist_assistant_chat_cancelled(
                    current_store,
                    normalized_payload=normalized_payload,
                    turn=turn,
                    user=user,
                )
            return _persist_assistant_chat_output(
                current_store,
                model_log=None,
                normalized_payload=normalized_payload,
                assistant_output=deterministic_output,
                turn=turn,
                user=user,
            )
        assistant_output, model_log = _call_model_gateway_for_assistant_chat(
            current_store,
            cancel_checker=lambda: _assistant_chat_run_is_cancelled(
                current_store,
                turn["chat_run"]["id"],
                user=user,
            ),
            model_gateway_api_key=model_gateway_api_key,
            model_gateway_base_url=model_gateway_base_url,
            model_gateway_default_chat_model=model_gateway_default_chat_model,
            model_gateway_status=model_gateway_status,
            payload=normalized_payload,
            run_id=turn["chat_run"]["id"],
            urlopen_func=urlopen_func,
            user=user,
        )
    except AssistantServiceError as exc:
        _persist_assistant_chat_failed(
            current_store,
            error_code=exc.code,
            error_message=exc.message,
            model_log=None,
            normalized_payload=normalized_payload,
            turn=turn,
            user=user,
        )
        raise
    except _AssistantGatewayRequestCancelled:
        return _persist_assistant_chat_cancelled(
            current_store,
            normalized_payload=normalized_payload,
            turn=turn,
            user=user,
        )
    except _AssistantGatewayRequestFailed as exc:
        model_gateway_audit_event = assistant_chat_audit_event(
            current_store,
            event_type="model_gateway.called",
            actor_id="system",
            subject_type="model_gateway_log",
            subject_id=exc.log["id"],
            payload={
                "model_log_id": exc.log["id"],
                "model": exc.log["model"],
                "provider": exc.log["provider"],
                "purpose": exc.log["purpose"],
                "status": exc.log["status"],
            },
        )
        _persist_assistant_chat_failed(
            current_store,
            audit_events=[model_gateway_audit_event],
            error_code="ASSISTANT_CHAT_FAILED",
            error_message="Assistant model gateway request failed",
            model_log=exc.log,
            normalized_payload=normalized_payload,
            turn=turn,
            user=user,
        )
        raise AssistantServiceError(
            502,
            "ASSISTANT_CHAT_FAILED",
            "Assistant model gateway request failed",
        ) from exc

    model_gateway_audit_event = assistant_chat_audit_event(
        current_store,
        event_type="model_gateway.called",
        actor_id="system",
        subject_type="model_gateway_log",
        subject_id=model_log["id"],
        payload={
            "model_log_id": model_log["id"],
            "model": model_log["model"],
            "provider": model_log["provider"],
            "purpose": model_log["purpose"],
            "status": model_log["status"],
        },
    )
    if _assistant_chat_run_is_cancelled(current_store, turn["chat_run"]["id"], user=user):
        return _persist_assistant_chat_cancelled(
            current_store,
            audit_events=[model_gateway_audit_event],
            model_log=model_log,
            normalized_payload=normalized_payload,
            turn=turn,
            user=user,
        )
    return _persist_assistant_chat_output(
        current_store,
        audit_events=[model_gateway_audit_event],
        model_log=model_log,
        normalized_payload=normalized_payload,
        assistant_output=assistant_output,
        turn=turn,
        user=user,
    )


def _assistant_chat_run_id(current_store: MemoryStore, payload: AssistantChatRequest) -> str:
    run_id = str(payload.run_id or "").strip()
    return run_id or current_store.new_id("assistant_chat_run")


def _assistant_chat_client_request_id(
    payload: AssistantChatRequest,
    *,
    run_id: str,
) -> str:
    client_request_id = str(payload.client_request_id or "").strip()
    return client_request_id or run_id


def _assistant_chat_run_record(
    current_store: MemoryStore,
    run_id: str,
) -> dict[str, Any] | None:
    repository = runtime_repository(current_store)
    get_run = getattr(repository, "get_assistant_chat_run", None)
    if callable(get_run):
        run = get_run(run_id=run_id)
        return dict(run) if run is not None else None
    run = getattr(current_store, "assistant_chat_runs", {}).get(run_id)
    return dict(run) if run is not None else None


def assistant_chat_audit_event(
    current_store: MemoryStore,
    *,
    event_type: str,
    actor_id: str,
    ai_task_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    payload: dict[str, Any] | None = None,
    sequence_offset: int = 0,
) -> dict[str, Any]:
    return {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": ai_task_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": len(_memory_list(current_store, "audit_events")) + sequence_offset + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }


def _memory_collection(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, list):
        collection = []
        setattr(current_store, collection_name, collection)
    return collection


def _start_assistant_chat_run(
    current_store: MemoryStore,
    *,
    message: str,
    normalized_payload: AssistantChatRequest,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    run_id = _assistant_chat_run_id(current_store, normalized_payload)
    client_request_id = _assistant_chat_client_request_id(normalized_payload, run_id=run_id)
    existing_run = _assistant_chat_run_record(current_store, run_id)
    if existing_run is not None and existing_run.get("user_id") != user["id"]:
        raise AssistantServiceError(404, "NOT_FOUND", "Assistant chat run not found")
    conversation = ensure_assistant_conversation(
        current_store,
        conversation_id=normalized_payload.conversation_id,
        message=message,
        now=now,
        product_id=normalized_payload.product_id,
        user=user,
    )
    user_message = append_assistant_message(
        current_store,
        client_request_id=client_request_id,
        content=message,
        conversation=conversation,
        now=now,
        references=[],
        role="user",
        run_id=run_id,
        status="pending",
        user_id=user["id"],
    )
    metadata_json = {
        **dict((existing_run or {}).get("metadata_json") or {}),
        "context_source": normalized_payload.context.get("source"),
        "message_excerpt": message[:160],
        "product_id": normalized_payload.product_id,
        "reference_count": len(normalized_payload.references),
    }
    chat_run = {
        **(existing_run or {}),
        "client_request_id": client_request_id,
        "conversation_id": conversation["id"],
        "created_at": (existing_run or {}).get("created_at") or now,
        "id": run_id,
        "metadata_json": metadata_json,
        "started_at": (existing_run or {}).get("started_at") or now,
        "status": (existing_run or {}).get("status") or "running",
        "updated_at": now,
        "user_id": user["id"],
        "user_message_id": user_message["id"],
    }
    if chat_run["status"] not in {"cancelled", "failed", "succeeded"}:
        chat_run["status"] = "running"
    save_assistant_chat_records(
        current_store,
        chat_run=chat_run,
        conversation=conversation,
        messages=[user_message],
        audit_events=[],
    )
    return {
        "chat_run": chat_run,
        "client_request_id": client_request_id,
        "conversation": conversation,
        "user_message": user_message,
    }


def _assistant_chat_run_is_cancelled(
    current_store: MemoryStore,
    run_id: str,
    *,
    user: dict[str, Any],
) -> bool:
    run = _assistant_chat_run_record(current_store, run_id)
    if run is None:
        return False
    if run.get("user_id") != user["id"]:
        raise AssistantServiceError(404, "NOT_FOUND", "Assistant chat run not found")
    return run.get("status") == "cancelled"


def _assistant_chat_run_public(run: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "assistant_message_id": run.get("assistant_message_id"),
            "cancel_reason": run.get("cancel_reason"),
            "cancelled_at": run.get("cancelled_at"),
            "cancelled_by": run.get("cancelled_by"),
            "client_request_id": run.get("client_request_id"),
            "conversation_id": run.get("conversation_id"),
            "error_code": run.get("error_code"),
            "error_message": run.get("error_message"),
            "finished_at": run.get("finished_at"),
            "id": run.get("id"),
            "started_at": run.get("started_at"),
            "status": run.get("status"),
            "user_message_id": run.get("user_message_id"),
        }.items()
        if value is not None
    }


def assistant_chat_runs_response(
    current_store: MemoryStore,
    *,
    limit: int = 20,
    status: str | None = None,
    user: dict[str, Any],
) -> dict[str, Any]:
    statuses = _assistant_chat_run_status_filter(status)
    repository = runtime_repository(current_store)
    list_runs = getattr(repository, "list_assistant_chat_runs", None)
    if callable(list_runs):
        runs = [dict(run) for run in list_runs(user_id=user["id"])]
    else:
        runs = [
            dict(run)
            for run in getattr(current_store, "assistant_chat_runs", {}).values()
            if isinstance(run, dict) and run.get("user_id") == user["id"]
        ]
    if statuses:
        runs = [run for run in runs if str(run.get("status") or "") in statuses]
    runs.sort(key=_assistant_chat_run_sort_key, reverse=True)
    cleaned_limit = max(1, min(int(limit or 20), 50))
    return {
        "items": [_assistant_chat_run_public(run) for run in runs[:cleaned_limit]],
        "total": len(runs),
    }


def _assistant_chat_run_status_filter(status: str | None) -> set[str]:
    if status is None or not str(status).strip():
        return set()
    statuses = {
        item.strip()
        for item in str(status).split(",")
        if item.strip()
    }
    allowed_statuses = {"running", "succeeded", "cancelled", "failed"}
    invalid_statuses = sorted(statuses - allowed_statuses)
    if invalid_statuses:
        raise AssistantServiceError(
            400,
            "VALIDATION_ERROR",
            f"Invalid assistant chat run status: {', '.join(invalid_statuses)}",
        )
    return statuses


def _assistant_chat_run_sort_key(run: dict[str, Any]) -> str:
    return str(
        run.get("updated_at")
        or run.get("finished_at")
        or run.get("started_at")
        or run.get("created_at")
        or ""
    )


def cancel_assistant_chat_run_response(
    current_store: MemoryStore,
    *,
    reason: str | None,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    cleaned_run_id = _ensure_non_blank(run_id, "run_id")
    now = datetime.now(UTC).isoformat()
    run = _assistant_chat_run_record(current_store, cleaned_run_id)
    if run is not None and run.get("user_id") != user["id"]:
        raise AssistantServiceError(404, "NOT_FOUND", "Assistant chat run not found")
    if run is None:
        run = {
            "created_at": now,
            "id": cleaned_run_id,
            "metadata_json": {"cancel_requested_before_start": True},
            "started_at": now,
            "user_id": user["id"],
        }
    if run.get("status") not in {"succeeded", "failed", "cancelled"}:
        run.update(
            {
                "cancel_reason": reason or "user_cancelled",
                "cancelled_at": now,
                "cancelled_by": user["id"],
                "finished_at": now,
                "status": "cancelled",
                "updated_at": now,
            }
        )
        audit_event = assistant_chat_audit_event(
            current_store,
            event_type="assistant.chat_run_cancelled",
            actor_id=user["id"],
            subject_type="assistant_chat_run",
            subject_id=cleaned_run_id,
            payload={"reason": run.get("cancel_reason")},
        )
        save_assistant_chat_records(
            current_store,
            chat_run=run,
            conversation=None,
            messages=[],
            audit_events=[audit_event],
        )
        _interrupt_assistant_chat_run(cleaned_run_id)
    return _assistant_chat_run_public(run)


def _persist_assistant_chat_output(
    current_store: MemoryStore,
    *,
    assistant_output: dict[str, Any],
    audit_events: list[dict[str, Any]] | None = None,
    model_log: dict[str, Any] | None,
    normalized_payload: AssistantChatRequest,
    turn: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    conversation = turn["conversation"]
    user_message = turn["user_message"]
    chat_run = turn["chat_run"]
    run_id = chat_run["id"]
    client_request_id = turn["client_request_id"]
    user_message.update(
        {
            "completed_at": now,
            "references": assistant_output.get("selected_references") or [],
            "status": "completed",
            "updated_at": now,
        }
    )
    user_message.setdefault("metadata_json", {})["references"] = user_message["references"]
    _attach_assistant_message_attribution_to_scheduled_job_runs(
        current_store,
        assistant_output=assistant_output,
        source_message_id=user_message["id"],
    )
    assistant_message = append_assistant_message(
        current_store,
        client_request_id=client_request_id,
        completed_at=now,
        content=assistant_output["answer"],
        conversation=conversation,
        intent=assistant_output.get("intent"),
        model=assistant_output["model"],
        now=now,
        references=assistant_output["references"],
        role="assistant",
        run_id=run_id,
        status="completed",
        suggestions=assistant_output["suggestions"],
        tool_results=assistant_output["tool_results"],
        user_id=user["id"],
    )
    if assistant_output.get("tool_results"):
        assistant_output["tool_results"] = persist_assistant_action_drafts_from_tool_results(
            current_store,
            source_message_id=assistant_message["id"],
            tool_results=assistant_output["tool_results"],
            user=user,
        )
        assistant_message["metadata_json"]["tool_results"] = assistant_output["tool_results"]
    chat_run.update(
        {
            "assistant_message_id": assistant_message["id"],
            "finished_at": now,
            "status": "succeeded",
            "updated_at": now,
        }
    )
    audit_payload = {
        "chat_run_id": run_id,
        "client_request_id": client_request_id,
        "latency_ms": assistant_output["latency_ms"],
        "model": assistant_output["model"],
        "product_id": normalized_payload.product_id,
        "reference_count": len(assistant_output["references"]),
        "suggestion_count": len(assistant_output["suggestions"]),
        "tool_count": len(assistant_output["tool_results"]),
    }
    if assistant_output.get("intent"):
        audit_payload["intent"] = assistant_output["intent"]
    if model_log is not None:
        audit_payload["model_log_id"] = model_log["id"]
    pending_audit_events = list(audit_events or [])
    pending_audit_events.append(
        assistant_chat_audit_event(
            current_store,
            event_type="assistant.chat_completed",
            actor_id=user["id"],
            subject_type="assistant_conversation",
            subject_id=conversation["id"],
            payload=audit_payload,
            sequence_offset=len(pending_audit_events),
        )
    )
    save_assistant_chat_records(
        current_store,
        chat_run=chat_run,
        conversation=conversation,
        messages=[user_message, assistant_message],
        model_log=model_log,
        audit_events=pending_audit_events,
    )
    return {
        "conversation_id": conversation["id"],
        "latency_ms": assistant_output["latency_ms"],
        "message": public_assistant_message(assistant_message),
        "model": assistant_output["model"],
        "run": _assistant_chat_run_public(chat_run),
        "run_id": run_id,
        "suggestions": assistant_output["suggestions"],
    }


def _persist_assistant_chat_cancelled(
    current_store: MemoryStore,
    *,
    audit_events: list[dict[str, Any]] | None = None,
    normalized_payload: AssistantChatRequest,
    turn: dict[str, Any],
    user: dict[str, Any],
    model_log: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    conversation = turn["conversation"]
    user_message = turn["user_message"]
    latest_run = _assistant_chat_run_record(current_store, turn["chat_run"]["id"]) or {}
    chat_run = {**turn["chat_run"], **latest_run}
    run_id = chat_run["id"]
    client_request_id = turn["client_request_id"]
    cancelled_at = chat_run.get("cancelled_at") or now
    user_message.update(
        {
            "cancelled_at": cancelled_at,
            "status": "cancelled",
            "updated_at": now,
        }
    )
    assistant_message = append_assistant_message(
        current_store,
        cancelled_at=cancelled_at,
        client_request_id=client_request_id,
        content="已停止生成。",
        conversation=conversation,
        now=now,
        references=[],
        role="assistant",
        run_id=run_id,
        status="cancelled",
        suggestions=[],
        user_id=user["id"],
    )
    chat_run.update(
        {
            "assistant_message_id": assistant_message["id"],
            "cancelled_at": cancelled_at,
            "cancelled_by": chat_run.get("cancelled_by") or user["id"],
            "finished_at": chat_run.get("finished_at") or now,
            "status": "cancelled",
            "updated_at": now,
        }
    )
    pending_audit_events = list(audit_events or [])
    pending_audit_events.append(
        assistant_chat_audit_event(
            current_store,
            event_type="assistant.chat_cancelled",
            actor_id=user["id"],
            subject_type="assistant_chat_run",
            subject_id=run_id,
            payload={
                "client_request_id": client_request_id,
                "model_log_id": model_log.get("id") if model_log else None,
                "product_id": normalized_payload.product_id,
            },
            sequence_offset=len(pending_audit_events),
        )
    )
    save_assistant_chat_records(
        current_store,
        chat_run=chat_run,
        conversation=conversation,
        messages=[user_message, assistant_message],
        model_log=model_log,
        audit_events=pending_audit_events,
    )
    return {
        "conversation_id": conversation["id"],
        "latency_ms": 0,
        "message": public_assistant_message(assistant_message),
        "model": "assistant-cancelled",
        "run": _assistant_chat_run_public(chat_run),
        "run_id": run_id,
        "suggestions": [],
    }


def _persist_assistant_chat_failed(
    current_store: MemoryStore,
    *,
    audit_events: list[dict[str, Any]] | None = None,
    error_code: str,
    error_message: str,
    model_log: dict[str, Any] | None,
    normalized_payload: AssistantChatRequest,
    turn: dict[str, Any],
    user: dict[str, Any],
) -> None:
    now = datetime.now(UTC).isoformat()
    conversation = turn["conversation"]
    user_message = turn["user_message"]
    chat_run = turn["chat_run"]
    run_id = chat_run["id"]
    client_request_id = turn["client_request_id"]
    user_message.update(
        {
            "completed_at": now,
            "status": "completed",
            "updated_at": now,
        }
    )
    assistant_message = append_assistant_message(
        current_store,
        client_request_id=client_request_id,
        content=error_message,
        conversation=conversation,
        error_code=error_code,
        failed_at=now,
        now=now,
        references=[],
        role="assistant",
        run_id=run_id,
        status="failed",
        suggestions=[],
        user_id=user["id"],
    )
    chat_run.update(
        {
            "assistant_message_id": assistant_message["id"],
            "error_code": error_code,
            "error_message": error_message,
            "finished_at": now,
            "status": "failed",
            "updated_at": now,
        }
    )
    pending_audit_events = list(audit_events or [])
    pending_audit_events.append(
        assistant_chat_audit_event(
            current_store,
            event_type="assistant.chat_failed",
            actor_id=user["id"],
            subject_type="assistant_chat_run",
            subject_id=run_id,
            payload={
                "client_request_id": client_request_id,
                "error_code": error_code,
                "model_log_id": model_log.get("id") if model_log else None,
                "product_id": normalized_payload.product_id,
            },
            sequence_offset=len(pending_audit_events),
        )
    )
    save_assistant_chat_records(
        current_store,
        chat_run=chat_run,
        conversation=conversation,
        messages=[user_message, assistant_message],
        model_log=model_log,
        audit_events=pending_audit_events,
    )


def _mark_scheduled_job_run_triggered_by_assistant(
    current_store: MemoryStore,
    *,
    run: dict[str, Any],
) -> None:
    run_id = str(run.get("id") or "").strip()
    if not run_id:
        return
    scheduled_job_runs = _memory_collection(current_store, "scheduled_job_runs")
    run_record = scheduled_job_runs.get(run_id)
    if not isinstance(run_record, dict):
        run_record = dict(run)
    now = datetime.now(UTC).isoformat()
    run_record = {
        **run_record,
        "triggered_by_assistant": True,
        "updated_at": now,
    }
    scheduled_job_runs[run_id] = run_record
    persist_record(current_store, "save_scheduled_job_run_record", run_record)
    run.update(run_record)


def _attach_assistant_message_attribution_to_scheduled_job_runs(
    current_store: MemoryStore,
    *,
    assistant_output: dict[str, Any],
    source_message_id: str,
) -> None:
    run_ids = {
        str(item.get("id") or item.get("run_id") or "").strip()
        for tool_result in assistant_output.get("tool_results") or []
        if (
            isinstance(tool_result, dict)
            and tool_result.get("tool") == "assistant.scheduled_job_run"
        )
        for item in tool_result.get("items") or []
        if isinstance(item, dict)
    }
    for tool_result in assistant_output.get("tool_results") or []:
        if (
            not isinstance(tool_result, dict)
            or tool_result.get("tool") != "assistant.scheduled_job_run"
        ):
            continue
        summary = tool_result.get("summary")
        if isinstance(summary, dict):
            run_ids.add(str(summary.get("run_id") or "").strip())
    run_ids.discard("")
    if not run_ids:
        return
    scheduled_job_runs = _memory_collection(current_store, "scheduled_job_runs")
    now = datetime.now(UTC).isoformat()
    for run_id in run_ids:
        run = scheduled_job_runs.get(run_id)
        if not isinstance(run, dict) or run.get("triggered_by_assistant") is not True:
            continue
        run = {
            **run,
            "assistant_source_message_id": source_message_id,
            "updated_at": now,
        }
        scheduled_job_runs[run_id] = run
        persist_record(current_store, "save_scheduled_job_run_record", run)


def _deterministic_assistant_output(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    intent_match = _match_deterministic_intent(payload.message)
    if intent_match is None:
        return None
    handler = intent_match.get("handler")
    if not callable(handler):
        return None
    intent_metadata = _intent_metadata(intent_match)
    return _with_intent_metadata(
        handler(
            current_store,
            payload=payload,
            user=user,
            intent=intent_metadata,
        ),
        intent_metadata,
    )


def _handle_task_creation_guide_intent(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        resolved_references = resolve_assistant_references(
            current_store,
            references=payload.references,
            user=user,
        )
    except AssistantReferenceError as exc:
        raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
    return _task_creation_guide_output(selected_references=resolved_references["items"])


def _handle_plugin_connection_diagnostic_intent(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        resolved_references = resolve_assistant_references(
            current_store,
            references=payload.references,
            user=user,
        )
    except AssistantReferenceError as exc:
        raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
    return _plugin_connection_diagnostic_output(
        current_store,
        payload=payload,
        selected_references=resolved_references["items"],
    )


def _handle_scheduled_job_run_once_intent(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _deterministic_scheduled_job_run_once_output(
        current_store,
        payload=payload,
        user=user,
    )


def _handle_scheduled_job_diagnostic_intent(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        resolved_references = resolve_assistant_references(
            current_store,
            references=payload.references,
            user=user,
        )
    except AssistantReferenceError as exc:
        raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
    return _scheduled_job_diagnostic_output(
        current_store,
        payload=payload,
        selected_references=resolved_references["items"],
    )


def _handle_assistant_metrics_explanation_intent(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del payload, intent
    return _assistant_metrics_explanation_output(current_store, user=user)


def _handle_action_draft_intent(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
    intent: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    return _deterministic_action_draft_output(
        current_store,
        payload=payload,
        user=user,
    )


def _deterministic_scheduled_job_run_once_output(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
) -> dict[str, Any]:
    try:
        resolved_references = resolve_assistant_references(
            current_store,
            references=payload.references,
            user=user,
        )
    except AssistantReferenceError as exc:
        raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
    selected_references = resolved_references["items"]
    scheduled_job_references = [
        reference for reference in selected_references if reference.get("type") == "scheduled_job"
    ]
    mention_resolution = _scheduled_job_references_from_explicit_mentions(
        current_store,
        message=payload.message,
        product_id=payload.product_id,
        user=user,
    )
    if scheduled_job_references:
        mention_resolution = {"attempted": False, "queries": [], "references": []}
    elif mention_resolution["references"]:
        selected_references = _merge_assistant_references(
            [
                reference
                for reference in selected_references
                if reference.get("type") != "scheduled_job"
            ],
            mention_resolution["references"],
        )
        scheduled_job_references = mention_resolution["references"]
    elif not scheduled_job_references:
        if mention_resolution["attempted"]:
            if mention_resolution.get("blocked_reason") == "permission_denied":
                return _scheduled_job_run_once_permission_denied_output(
                    attempted_queries=mention_resolution["queries"],
                    selected_references=selected_references,
                )
            draft_output = _scheduled_job_run_once_missing_job_draft_output(
                current_store=current_store,
                message=payload.message,
                product_id=payload.product_id,
                queries=mention_resolution["queries"],
                selected_references=selected_references,
                user=user,
            )
            if draft_output is not None:
                return draft_output
            return _scheduled_job_reference_needed_output(
                attempted_queries=mention_resolution["queries"],
                selected_references=selected_references,
            )
        return _deterministic_action_draft_output(
            current_store,
            payload=payload,
            user=user,
        )
    started = perf_counter()
    if len(scheduled_job_references) > 1:
        answer = "我检测到多个定时作业引用。请只保留一个定时作业后，再发送“执行一次”。"
        return {
            "answer": answer,
            "latency_ms": int((perf_counter() - started) * 1000),
            "model": "assistant-deterministic",
            "references": selected_references,
            "selected_references": selected_references,
            "suggestions": ["只保留一个定时作业引用后执行一次"],
            "tool_results": [
                {
                    "intent": "scheduled_job_run_once",
                    "items": [],
                    "summary": {
                        "scheduled_job_ids": [
                            str(reference["id"]) for reference in scheduled_job_references
                        ],
                        "status": "needs_single_reference",
                    },
                    "tool": "assistant.scheduled_job_run",
                }
            ],
        }
    scheduled_job_reference = scheduled_job_references[0]
    job_id = str(scheduled_job_reference["id"])
    job = getattr(current_store, "scheduled_jobs", {}).get(job_id) or {}
    active_run = _active_scheduled_job_run_for_job(
        current_store,
        job=job,
        job_id=job_id,
    )
    if active_run is not None:
        run_id = str(active_run.get("id") or "")
        run_status = str(active_run.get("status") or "unknown")
        return {
            "answer": (
                f"「{_scheduled_job_title(job, job_id)}」已有一次执行正在进行中，"
                f"运行记录 {run_id} 当前状态为 {run_status}。"
            ),
            "latency_ms": int((perf_counter() - started) * 1000),
            "model": "assistant-deterministic",
            "references": _merge_assistant_references(
                selected_references,
                [_scheduled_job_run_reference(job=job, job_id=job_id, run=active_run)],
            ),
            "selected_references": selected_references,
            "suggestions": ["查看本次运行记录", "为什么这次任务失败？"],
            "tool_results": [
                _scheduled_job_run_tool_result(
                    error_code=None,
                    error_message=None,
                    job=job,
                    job_id=job_id,
                    run=active_run,
                )
            ],
        }
    try:
        if _scheduled_job_run_should_return_immediately(job):
            run = _start_scheduled_job_run_once_in_background(
                current_store=current_store,
                job_id=job_id,
                user=user,
            )
        else:
            run = run_scheduled_job_response(
                current_store=current_store,
                job_id=job_id,
                source_run_id=None,
                trigger_type="manual",
                user=user,
            )
        _mark_scheduled_job_run_triggered_by_assistant(current_store, run=run)
    except HTTPException as exc:
        error_code, error_message = _http_exception_code_and_message(exc)
        return {
            "answer": f"没有执行成功：{error_message}",
            "latency_ms": int((perf_counter() - started) * 1000),
            "model": "assistant-deterministic",
            "references": selected_references,
            "selected_references": selected_references,
            "suggestions": ["检查定时作业配置", "打开定时作业详情"],
            "tool_results": [
                _scheduled_job_run_tool_result(
                    error_code=error_code,
                    error_message=error_message,
                    job=job,
                    job_id=job_id,
                    run=None,
                )
            ],
        }
    run_reference = _scheduled_job_run_reference(job=job, job_id=job_id, run=run)
    run_status = str(run.get("status") or "unknown")
    run_id = str(run.get("id") or "")
    if run_status in {"queued", "running"}:
        progress_text = _scheduled_job_run_progress_text(run)
        progress_suffix = f"{progress_text}。" if progress_text else ""
        answer = (
            f"已触发「{_scheduled_job_title(job, job_id)}」执行一次，"
            f"运行记录 {run_id} 当前状态为 {run_status}。{progress_suffix}"
        )
    elif run_status == "succeeded":
        answer = (
            f"已执行「{_scheduled_job_title(job, job_id)}」一次，"
            f"运行记录 {run_id} 已成功完成。"
        )
    else:
        error_message = run.get("error_message") or "请查看运行记录详情。"
        answer = (
            f"已执行「{_scheduled_job_title(job, job_id)}」一次，"
            f"运行记录 {run_id} 状态为 {run_status}：{error_message}"
        )
    return {
        "answer": answer,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": _merge_assistant_references(selected_references, [run_reference]),
        "selected_references": selected_references,
        "suggestions": ["查看本次运行记录", "为什么这次任务失败？"],
        "tool_results": [
            _scheduled_job_run_tool_result(
                error_code=None,
                error_message=None,
                job=job,
                job_id=job_id,
                run=run,
            )
        ],
    }


def _deterministic_intent_registry() -> list[dict[str, Any]]:
    return [
        {
            "action": "guide_task_creation",
            "conflict_policy": "first_match",
            "confidence": 0.95,
            "detector": _task_creation_guide_requested,
            "handler": _handle_task_creation_guide_intent,
            "intent_code": "task_creation_guide",
            "priority": 100,
            "required_refs": [],
            "summary": "将执行：任务类型向导",
        },
        {
            "action": "diagnose_plugin_connection",
            "conflict_policy": "first_match",
            "confidence": 0.9,
            "detector": _plugin_connection_diagnostic_requested,
            "handler": _handle_plugin_connection_diagnostic_intent,
            "intent_code": "plugin_connection_diagnostic",
            "priority": 90,
            "required_refs": ["plugin_connection"],
            "summary": "将执行：插件连接诊断",
            "tool": "assistant.plugin_connection_diagnostic",
        },
        {
            "action": "diagnose_scheduled_job_run",
            "conflict_policy": "first_match",
            "confidence": 0.9,
            "detector": _scheduled_job_diagnostic_requested,
            "handler": _handle_scheduled_job_diagnostic_intent,
            "intent_code": "scheduled_job_diagnostic",
            "priority": 85,
            "required_refs": ["scheduled_job", "scheduled_job_run"],
            "summary": "将执行：定时作业运行诊断",
            "tool": "assistant.scheduled_job_diagnostic",
        },
        {
            "action": "run_scheduled_job_once",
            "conflict_policy": "first_match",
            "confidence": 0.95,
            "detector": _scheduled_job_run_once_requested,
            "handler": _handle_scheduled_job_run_once_intent,
            "intent_code": "scheduled_job_run_once",
            "priority": 80,
            "required_refs": ["scheduled_job"],
            "summary": "将执行：运行定时作业一次",
            "tool": "assistant.scheduled_job_run",
        },
        {
            "action": "explain_assistant_metrics",
            "conflict_policy": "first_match",
            "confidence": 0.88,
            "detector": _assistant_metrics_explanation_requested,
            "handler": _handle_assistant_metrics_explanation_intent,
            "intent_code": "assistant_metrics_explanation",
            "priority": 70,
            "required_refs": [],
            "summary": "将执行：解释助手效果指标",
            "tool": "assistant.metrics_summary",
        },
        {
            "action": "create_action_draft",
            "conflict_policy": "fallback",
            "confidence": 0.7,
            "detector": lambda _message: True,
            "handler": _handle_action_draft_intent,
            "intent_code": "action_draft",
            "priority": 0,
            "required_refs": [],
            "summary": "将执行：生成可确认草案",
        },
    ]


def _match_deterministic_intent(message: str) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for intent in _deterministic_intent_registry():
        detector = intent["detector"]
        if detector(message):
            matches.append(dict(intent))
    return _resolve_deterministic_intent_conflict(matches)


def _resolve_deterministic_intent_conflict(
    matches: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not matches:
        return None
    non_fallback_matches = [
        intent
        for intent in matches
        if str(intent.get("conflict_policy") or "first_match") != "fallback"
    ]
    candidates = non_fallback_matches or matches
    return sorted(
        candidates,
        key=lambda item: int(item.get("priority") or 0),
        reverse=True,
    )[0]


def _intent_metadata(intent: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "confidence": intent["confidence"],
        "conflict_policy": intent.get("conflict_policy"),
        "intent_code": intent["intent_code"],
        "priority": intent.get("priority"),
        "required_refs": list(intent.get("required_refs") or []),
        "summary": intent["summary"],
    }
    if intent.get("action"):
        metadata["action"] = intent["action"]
    if intent.get("tool"):
        metadata["tool"] = intent["tool"]
    return {key: value for key, value in metadata.items() if value is not None}


def _with_intent_metadata(
    output: dict[str, Any] | None,
    intent: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if output is None or intent is None:
        return output
    output["intent"] = intent
    for tool_result in output.get("tool_results") or []:
        tool_result.setdefault("intent_code", intent["intent_code"])
        tool_result.setdefault("intent_confidence", intent["confidence"])
        tool_result.setdefault("required_refs", intent["required_refs"])
    return output


def _deterministic_action_draft_output(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    started = perf_counter()
    try:
        resolved_references = resolve_assistant_references(
            current_store,
            references=payload.references,
            user=user,
        )
    except AssistantReferenceError as exc:
        raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
    tool_results = assistant_tool_results(
        current_store,
        message=payload.message,
        product_id=payload.product_id,
        references=resolved_references["items"],
    )
    draft_results = [
        result
        for result in tool_results
        if result.get("tool") == "assistant.action_draft"
    ]
    if not draft_results:
        return None
    draft_references = [
        reference
        for result in draft_results
        for reference in result.get("references", [])
        if isinstance(reference, dict)
    ]
    return {
        "answer": _action_draft_answer(draft_results),
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": _merge_assistant_references(
            resolved_references["items"],
            draft_references,
        ),
        "selected_references": resolved_references["items"],
        "suggestions": ["查看并确认草案", "补齐阻塞字段"],
        "tool_results": draft_results,
    }


def _action_draft_answer(draft_results: list[dict[str, Any]]) -> str:
    draft_count = sum(len(result.get("items") or []) for result in draft_results)
    if any(result.get("intent") == "ai_capability_draft" for result in draft_results):
        return "我已生成 AI 能力草案，确认前不会写入真实 Skill 或 AI角色配置。"
    if draft_count <= 1:
        return "我已生成可确认的配置草案，确认前不会写入真实配置。"
    return f"我已生成 {draft_count} 个可确认的配置草案，并标明前置依赖关系。"


def _default_model_gateway_config(current_store: MemoryStore) -> dict[str, Any] | None:
    for item in current_store.model_gateway_configs.values():
        if item.get("is_default") and item.get("status") == "active":
            return item
    return None


def _assistant_model_gateway_config(
    current_store: MemoryStore,
    *,
    model_gateway_api_key: str,
    model_gateway_base_url: str,
    model_gateway_default_chat_model: str,
    model_gateway_status: str,
) -> dict[str, Any]:
    config = _default_model_gateway_config(current_store)
    if config:
        if config.get("provider") != "openai_compatible":
            raise AssistantServiceError(
                400,
                "MODEL_GATEWAY_CONFIG_INVALID",
                "Active model gateway provider is not supported",
            )
        if not config.get("api_key"):
            raise AssistantServiceError(
                400,
                "MODEL_GATEWAY_CONFIG_INVALID",
                "Active model gateway config is missing api_key",
            )
        return config
    if model_gateway_status == "configured":
        return {
            "api_key": model_gateway_api_key,
            "base_url": model_gateway_base_url,
            "default_chat_model": model_gateway_default_chat_model,
            "id": None,
            "provider": "openai_compatible",
            "timeout_seconds": 60,
        }
    raise AssistantServiceError(
        400,
        "MODEL_GATEWAY_CONFIG_INVALID",
        "No active/default model gateway config is configured",
    )


def _assistant_chat_messages(
    current_store: MemoryStore,
    *,
    model_gateway_status: str,
    payload: AssistantChatRequest,
    resolved_references: dict[str, Any],
    tool_results: list[dict[str, Any]],
    user: dict[str, Any],
) -> list[dict[str, str]]:
    default_gateway = _default_model_gateway_config(current_store)
    system_context = build_assistant_system_context(
        current_store,
        default_gateway=default_gateway,
        model_gateway_status=model_gateway_status,
        product_id=payload.product_id,
    )
    system_context["tool_results"] = tool_results
    system_context["selected_references"] = resolved_references["items"]
    system_context["knowledge_context"] = resolved_references["knowledge_context"]
    system_context["reference_candidates"] = assistant_reference_candidates(
        current_store,
        message=payload.message,
        product_id=payload.product_id,
        user=user,
    )
    system_context["reference_candidates"] = _merge_assistant_references(
        resolved_references["items"],
        [
            reference
            for tool_result in tool_results
            for reference in tool_result.get("references", [])
        ],
        system_context["reference_candidates"],
    )
    return assistant_context_chat_messages(
        conversation_history=assistant_conversation_history_context(
            current_store,
            conversation_id=payload.conversation_id,
        ),
        context=payload.context,
        conversation_id=payload.conversation_id,
        message=payload.message,
        product_id=payload.product_id,
        system_context=system_context,
    )


def _register_assistant_chat_run_interrupter(
    run_id: str | None,
    interrupter: Callable[[], None],
) -> None:
    if not run_id:
        return
    with _ASSISTANT_CHAT_RUN_INTERRUPTERS_LOCK:
        _ASSISTANT_CHAT_RUN_INTERRUPTERS[run_id] = interrupter


def _unregister_assistant_chat_run_interrupter(
    run_id: str | None,
    interrupter: Callable[[], None],
) -> None:
    if not run_id:
        return
    with _ASSISTANT_CHAT_RUN_INTERRUPTERS_LOCK:
        if _ASSISTANT_CHAT_RUN_INTERRUPTERS.get(run_id) is interrupter:
            _ASSISTANT_CHAT_RUN_INTERRUPTERS.pop(run_id, None)


def _interrupt_assistant_chat_run(run_id: str | None) -> None:
    if not run_id:
        return
    with _ASSISTANT_CHAT_RUN_INTERRUPTERS_LOCK:
        interrupter = _ASSISTANT_CHAT_RUN_INTERRUPTERS.get(run_id)
    if interrupter is None:
        return
    try:
        interrupter()
    except Exception:
        return


def _read_model_gateway_response_payload(
    request: UrlRequest,
    *,
    cancel_checker: Callable[[], bool] | None,
    run_id: str | None,
    timeout_seconds: int,
    urlopen_func: Callable[[Any, int], Any],
) -> dict[str, Any]:
    if cancel_checker is not None and cancel_checker():
        raise _AssistantGatewayRequestCancelled()
    result: dict[str, Any] = {}
    done = threading.Event()

    def request_worker() -> None:
        try:
            if urlopen_func is default_urlopen:
                result["payload"] = _read_model_gateway_response_payload_with_httpx(
                    request,
                    run_id=run_id,
                    timeout_seconds=timeout_seconds,
                )
            else:
                with urlopen_func(request, timeout=timeout_seconds) as response:
                    result["payload"] = json.loads(response.read().decode("utf-8"))
        except BaseException as exc:
            result["error"] = exc
        finally:
            done.set()

    thread = threading.Thread(
        target=request_worker,
        name=f"assistant-chat-gateway-{run_id or 'request'}",
        daemon=True,
    )
    thread.start()
    while not done.wait(ASSISTANT_ASYNC_RUN_POLL_SECONDS):
        if cancel_checker is not None and cancel_checker():
            _interrupt_assistant_chat_run(run_id)
            raise _AssistantGatewayRequestCancelled()
    if cancel_checker is not None and cancel_checker():
        raise _AssistantGatewayRequestCancelled()
    error = result.get("error")
    if error is not None:
        raise error
    payload = result.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Assistant response is missing payload")
    return payload


def _read_model_gateway_response_payload_with_httpx(
    request: UrlRequest,
    *,
    run_id: str | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    client = httpx.Client(timeout=timeout_seconds)

    def close_client() -> None:
        client.close()

    _register_assistant_chat_run_interrupter(run_id, close_client)
    try:
        response = client.request(
            request.get_method(),
            request.full_url,
            content=request.data,
            headers=dict(request.header_items()),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Assistant response is missing payload")
        return payload
    finally:
        _unregister_assistant_chat_run_interrupter(run_id, close_client)
        client.close()


def _call_model_gateway_for_assistant_chat(
    current_store: MemoryStore,
    *,
    model_gateway_api_key: str,
    model_gateway_base_url: str,
    model_gateway_default_chat_model: str,
    model_gateway_status: str,
    payload: AssistantChatRequest,
    urlopen_func: Callable[[Any, int], Any],
    user: dict[str, Any],
    cancel_checker: Callable[[], bool] | None = None,
    run_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = _assistant_model_gateway_config(
        current_store,
        model_gateway_api_key=model_gateway_api_key,
        model_gateway_base_url=model_gateway_base_url,
        model_gateway_default_chat_model=model_gateway_default_chat_model,
        model_gateway_status=model_gateway_status,
    )
    provider = config["provider"]
    model = config["default_chat_model"]
    try:
        resolved_references = resolve_assistant_references(
            current_store,
            references=payload.references,
            user=user,
        )
    except AssistantReferenceError as exc:
        raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
    tool_results = assistant_tool_results(
        current_store,
        message=payload.message,
        product_id=payload.product_id,
        references=resolved_references["items"],
    )
    messages = _assistant_chat_messages(
        current_store,
        model_gateway_status=model_gateway_status,
        payload=payload,
        resolved_references=resolved_references,
        tool_results=tool_results,
        user=user,
    )
    body = {
        "messages": messages,
        "model": model,
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    request = UrlRequest(
        _model_gateway_chat_completions_url(config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        response_payload = _read_model_gateway_response_payload(
            request,
            cancel_checker=cancel_checker,
            run_id=run_id,
            timeout_seconds=int(config.get("timeout_seconds") or 60),
            urlopen_func=urlopen_func,
        )
        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Assistant response is missing choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise ValueError("Assistant response is missing message")
        assistant_output = assistant_response_content(message.get("content"))
        if not assistant_output["answer"]:
            raise ValueError("Assistant response is missing answer")
        references = _merge_assistant_references(
            resolved_references["items"],
            assistant_output.get("references") or [],
            [
                reference
                for tool_result in tool_results
                for reference in tool_result.get("references", [])
            ],
            assistant_reference_candidates(
                current_store,
                message=payload.message,
                product_id=payload.product_id,
                user=user,
            ),
        )
        assistant_output["references"] = references
        assistant_output["selected_references"] = resolved_references["items"]
        assistant_output["tool_results"] = tool_results
        latency_ms = int((perf_counter() - started) * 1000)
        log = model_gateway_log(
            current_store,
            purpose="assistant_chat",
            provider=provider,
            model=model,
            config_id=config["id"],
            tokens=openai_usage_tokens(
                response_payload.get("usage"),
                messages=messages,
                output=assistant_output,
            ),
            latency_ms=latency_ms,
            status="succeeded",
        )
        return {**assistant_output, "latency_ms": latency_ms, "model": model}, log
    except (
        AttributeError,
        HTTPError,
        httpx.HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        prompt_tokens = estimate_tokens(messages)
        log = model_gateway_log(
            current_store,
            purpose="assistant_chat",
            provider=provider,
            model=model,
            config_id=config["id"],
            tokens={"prompt": prompt_tokens, "completion": 0, "total": prompt_tokens},
            latency_ms=latency_ms,
            status="failed",
            error="Assistant model gateway request failed",
        )
        raise _AssistantGatewayRequestFailed(log) from exc


def _model_gateway_chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _scheduled_job_run_once_requested(message: str) -> bool:
    normalized = message.lower()
    if any(keyword in normalized for keyword in SCHEDULED_JOB_RUN_NEGATION_KEYWORDS):
        return False
    return any(keyword in normalized for keyword in SCHEDULED_JOB_RUN_ONCE_KEYWORDS)


def _scheduled_job_diagnostic_requested(message: str) -> bool:
    normalized = message.lower()
    has_diagnostic_intent = any(
        keyword in normalized
        for keyword in ("为什么", "原因", "失败", "诊断", "排查", "failed", "failure", "diagnose")
    )
    has_scheduled_job_context = any(
        keyword in normalized
        for keyword in ("定时任务", "定时作业", "作业", "运行", "scheduled job", "run")
    )
    has_create_intent = any(
        keyword in normalized
        for keyword in ("创建", "新增", "配置", "生成", "新建", "create", "draft")
    )
    return has_diagnostic_intent and has_scheduled_job_context and not has_create_intent


def _assistant_metrics_explanation_requested(message: str) -> bool:
    normalized = message.lower()
    has_metrics_intent = any(
        keyword in normalized
        for keyword in ("指标", "效果", "漏斗", "采纳率", "修复率", "成功率", "metrics", "funnel")
    )
    has_assistant_context = any(
        keyword in normalized
        for keyword in ("助手", "ai assistant", "草案", "引用", "运行", "失败修复")
    )
    return has_metrics_intent and has_assistant_context


def _task_creation_guide_requested(message: str) -> bool:
    normalized = message.lower()
    has_create_intent = any(
        keyword in normalized
        for keyword in ("新增", "新建", "创建", "增加", "create", "add")
    )
    has_task_context = any(keyword in normalized for keyword in ("任务", "作业", "task"))
    has_specific_task_type = any(
        keyword in normalized
        for keyword in (
            "定时作业",
            "定时任务",
            "研发任务",
            "ai任务",
            "ai 任务",
            "产品详细设计",
            "插件动作",
            "插件连接",
            "代码巡检",
            "反馈洞察",
            "用户反馈",
            "scheduled job",
            "plugin action",
            "code inspection",
            "feedback",
        )
    )
    has_generic_ai_capability_config = any(
        keyword in normalized
        for keyword in (
            "ai 能力配置",
            "ai能力配置",
            "ai 能力",
            "ai能力",
            "ai 角色",
            "ai角色",
            "skill",
            "agent",
            "智能体",
        )
    )
    has_specific_ai_capability_scenario = (
        _ai_capability_specific_scenario_requested(normalized)
    )
    return (
        has_create_intent
        and (
            (has_task_context and not has_specific_task_type)
            or (
                has_generic_ai_capability_config
                and not has_specific_ai_capability_scenario
            )
        )
    )


def _ai_capability_specific_scenario_requested(normalized_message: str) -> bool:
    return any(
        keyword in normalized_message
        for keyword in (
            "代码巡检",
            "code inspection",
            "github",
            "gitlab",
            "线上日志异常",
            "线上日志分析",
            "日志异常",
            "日志分析",
            "online log anomaly",
            "online_log_anomaly",
            "online_log",
            "log anomaly",
        )
    )


def _plugin_connection_diagnostic_requested(message: str) -> bool:
    normalized = message.lower()
    has_connection_context = any(
        keyword in normalized
        for keyword in ("插件连接", "连接失败", "连接不可用", "connection", "connector")
    )
    has_failure_intent = any(
        keyword in normalized
        for keyword in (
            "为什么",
            "原因",
            "失败",
            "不可用",
            "诊断",
            "排查",
            "怎么修",
            "修复",
            "failed",
            "failure",
            "diagnose",
            "repair",
            "fix",
        )
    )
    has_create_intent = any(
        keyword in normalized
        for keyword in ("创建", "新增", "配置", "生成", "新建", "接入", "create", "draft")
    )
    return has_connection_context and has_failure_intent and not has_create_intent


def _plugin_connection_diagnostic_output(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    started = perf_counter()
    tool_results = [
        result
        for result in assistant_tool_results(
            current_store,
            message=payload.message,
            product_id=payload.product_id,
            references=selected_references,
        )
        if result.get("tool") == "assistant.plugin_connection_diagnostic"
    ]
    diagnosed_count = sum(len(result.get("items") or []) for result in tool_results)
    failed_count = sum(
        int((result.get("summary") or {}).get("failed_count") or 0)
        for result in tool_results
    )
    if diagnosed_count:
        answer = (
            f"我已读取最近插件连接测试记录，找到 {failed_count} 个失败连接，"
            "并按连接配置、最近测试、修复建议整理如下。"
        )
    else:
        answer = (
            "我没有找到最近失败的插件连接测试记录。"
            "请先在插件管理里执行一次连接测试，或补充具体连接名称后继续排查。"
        )
    diagnostic_references = [
        reference
        for result in tool_results
        for reference in result.get("references", [])
        if isinstance(reference, dict)
    ]
    return {
        "answer": answer,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": _merge_assistant_references(
            selected_references,
            diagnostic_references,
        ),
        "selected_references": selected_references,
        "suggestions": ["生成插件连接修复草案", "打开插件管理"],
        "tool_results": tool_results,
    }


def _scheduled_job_diagnostic_output(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    started = perf_counter()
    tool_results = [
        result
        for result in assistant_tool_results(
            current_store,
            message=payload.message,
            product_id=payload.product_id,
            references=selected_references,
        )
        if result.get("tool") == "assistant.scheduled_job_diagnostic"
    ]
    diagnosed_count = sum(len(result.get("items") or []) for result in tool_results)
    failed_count = sum(
        int((result.get("summary") or {}).get("failed_count") or 0)
        for result in tool_results
    )
    if diagnosed_count:
        answer = (
            f"我已读取最近定时作业运行记录，找到 {failed_count} 个失败运行，"
            "并按数据连接、AI 处理、结果动作三段整理诊断。"
        )
    else:
        answer = (
            "我没有找到可诊断的失败运行。"
            "可以先 @具体定时作业或 @运行记录，或手动执行一次后再继续排查。"
        )
    diagnostic_references = [
        reference
        for result in tool_results
        for reference in result.get("references", [])
        if isinstance(reference, dict)
    ]
    return {
        "answer": answer,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": _merge_assistant_references(
            selected_references,
            diagnostic_references,
        ),
        "selected_references": selected_references,
        "suggestions": [
            "围绕某次运行继续追问",
            "生成失败修复草案",
            "查看定时作业运行记录",
        ],
        "tool_results": tool_results,
    }


def _assistant_metrics_explanation_output(
    current_store: MemoryStore,
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    started = perf_counter()
    metrics = assistant_metrics_response(current_store, user=user)
    summary = metrics.get("summary") or {}
    answer = (
        "当前 AI 助手效果指标："
        f"草案生成 {int(summary.get('draft_total') or 0)} 个，"
        f"草案确认率 {_format_ratio(summary.get('draft_adoption_rate'))}，"
        f"@ 引用使用率 {_format_ratio(summary.get('reference_usage_rate'))}，"
        f"作业运行成功率 {_format_ratio(summary.get('scheduled_job_run_success_rate'))}，"
        f"失败修复率 {_format_ratio(summary.get('failed_run_repair_rate'))}。"
    )
    return {
        "answer": answer,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": [],
        "selected_references": [],
        "suggestions": [
            "查看草案采纳漏斗",
            "解释作业运行成功率",
            "分析失败修复率",
        ],
        "tool_results": [
            {
                "intent": "assistant_metrics_explanation",
                "items": metrics.get("funnel", {}).get("stages", []),
                "summary": summary,
                "tool": "assistant.metrics_summary",
            }
        ],
    }


def _format_ratio(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def _task_creation_guide_output(
    *,
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    started = perf_counter()
    return {
        "answer": (
            "你想新增哪类任务？我会先按向导生成可确认的草案，确认前不会写入真实配置。"
        ),
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": selected_references,
        "selected_references": selected_references,
        "suggestions": [
            "新增研发任务",
            "新增定时作业",
            "新增AI能力配置",
            "新增插件动作",
            "配置代码巡检定时作业",
            "配置每周用户反馈洞察定时作业",
        ],
        "tool_results": [
            {
                "intent": "task_creation_guide",
                "items": TASK_CREATION_GUIDE_ITEMS,
                "summary": {
                    "draft_first": True,
                    "option_count": len(TASK_CREATION_GUIDE_ITEMS),
                    "wizard_steps": TASK_CREATION_WIZARD_STEPS,
                },
                "tool": "assistant.task_creation_guide",
            }
        ],
    }


def _scheduled_job_reference_needed_output(
    *,
    attempted_queries: list[str],
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    query_text = "、".join(attempted_queries) if attempted_queries else "这个 @ 引用"
    return {
        "answer": (
            f"我没有找到唯一匹配的定时作业：{query_text}。"
            "请从 @ 候选中点选一个定时作业后再执行一次。"
        ),
        "latency_ms": 0,
        "model": "assistant-deterministic",
        "references": selected_references,
        "selected_references": selected_references,
        "suggestions": ["输入 @ 后选择定时作业，再发送执行一次"],
        "tool_results": [
            {
                "intent": "scheduled_job_run_once",
                "items": [],
                "summary": {
                    "queries": attempted_queries,
                    "status": "needs_scheduled_job_reference",
                },
                "tool": "assistant.scheduled_job_run",
            }
        ],
    }


def _scheduled_job_run_once_missing_job_draft_output(
    *,
    current_store: MemoryStore,
    message: str,
    product_id: str | None,
    queries: list[str],
    selected_references: list[dict[str, str]],
    user: dict[str, Any],
) -> dict[str, Any] | None:
    if not _user_can_run_scheduled_job_from_assistant(user):
        return None
    if not _weekly_feedback_run_once_draft_requested(message, queries):
        return None
    started = perf_counter()
    tool_results = assistant_tool_results(
        current_store,
        message="请帮我生成每周用户反馈洞察定时作业草案",
        product_id=product_id,
        references=selected_references,
    )
    draft_results = [
        result
        for result in tool_results
        if result.get("tool") == "assistant.action_draft"
        and result.get("intent") == "scheduled_job_draft"
    ]
    if not draft_results:
        return None
    for result in draft_results:
        summary = dict(result.get("summary") or {})
        summary["run_once_requested"] = True
        summary["status"] = "draft_required"
        result["summary"] = summary
        for item in result.get("items") or []:
            if not isinstance(item, dict):
                continue
            payload = dict(item.get("payload") or {})
            config_json = dict(payload.get("config_json") or {})
            config_json["assistant_run_once_request"] = {
                "requested": True,
                "source_message": message,
            }
            payload["config_json"] = config_json
            item["payload"] = payload
            item["run_once_requested"] = True
    draft_references = [
        reference
        for result in draft_results
        for reference in result.get("references", [])
        if isinstance(reference, dict)
    ]
    query_text = "、".join(queries) if queries else "这个 @ 引用"
    return {
        "answer": (
            f"还没有找到可执行的定时作业：{query_text}。"
            "当前尚未执行；我先生成周反馈洞察定时作业草案，"
            "确认并补齐校验项后再执行一次。"
        ),
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": "assistant-deterministic",
        "references": _merge_assistant_references(selected_references, draft_references),
        "selected_references": selected_references,
        "suggestions": ["查看并确认草案", "补齐数据连接和结果动作"],
        "tool_results": draft_results,
    }


def _weekly_feedback_run_once_draft_requested(message: str, queries: list[str]) -> bool:
    normalized = f"{message} {' '.join(queries)}".lower()
    has_feedback_context = any(
        keyword in normalized
        for keyword in ("用户反馈", "周反馈", "每周", "feedback", "user feedback")
    )
    has_insight_context = any(
        keyword in normalized
        for keyword in ("洞察", "提取", "抽取", "有价值", "价值", "信息", "insight", "extract")
    )
    return has_feedback_context and has_insight_context


def _scheduled_job_references_from_explicit_mentions(
    current_store: MemoryStore,
    *,
    message: str,
    product_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    queries = _explicit_mention_queries_for_run_once(message)
    if not queries:
        return {"attempted": False, "queries": [], "references": []}
    if not _user_can_run_scheduled_job_from_assistant(user):
        return {
            "attempted": True,
            "blocked_reason": "permission_denied",
            "queries": queries,
            "references": [],
        }
    jobs = list(getattr(current_store, "scheduled_jobs", {}).values())
    if product_id:
        jobs = [job for job in jobs if job.get("product_id") == product_id]
    references: list[dict[str, str]] = []
    for query in queries:
        matches = [job for job in jobs if _scheduled_job_matches_mention(job, query)]
        preferred_matches = _scheduled_job_preferred_run_once_mention_matches(
            matches,
            query,
            require_official_insight=True,
        )
        if len(preferred_matches) == 1:
            matches = preferred_matches
        if len(matches) != 1:
            exact_matches = [
                job for job in matches if _scheduled_job_exactly_matches_mention(job, query)
            ]
            if len(exact_matches) == 1:
                matches = exact_matches
        if len(matches) != 1:
            preferred_matches = _scheduled_job_preferred_run_once_mention_matches(
                matches,
                query,
                require_official_insight=False,
            )
            if len(preferred_matches) == 1:
                matches = preferred_matches
        if len(matches) != 1:
            runnable_matches = [
                job for job in matches if _scheduled_job_is_runnable_mention_match(job)
            ]
            if len(runnable_matches) == 1:
                matches = runnable_matches
        if len(matches) != 1:
            return {"attempted": True, "queries": queries, "references": []}
        job = matches[0]
        job_id = str(job["id"])
        references.append(
            {
                "id": job_id,
                "title": _scheduled_job_title(job, job_id),
                "type": "scheduled_job",
                "url": f"/tasks/scheduled-jobs?job_id={job_id}",
            }
        )
    return {
        "attempted": True,
        "queries": queries,
        "references": _merge_assistant_references(references),
    }


def _explicit_mention_queries_for_run_once(message: str) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"[@＠]([^@＠\n]+)", message):
        raw_tail = match.group(1).strip()
        if not raw_tail:
            continue
        end_index = len(raw_tail)
        normalized_tail = raw_tail.lower()
        for keyword in SCHEDULED_JOB_RUN_ONCE_KEYWORDS:
            keyword_index = normalized_tail.find(keyword)
            if keyword_index >= 0:
                end_index = min(end_index, keyword_index)
        query = raw_tail[:end_index].strip(" \t，,。；;：:")
        query = re.sub(r"(请|麻烦|帮我|帮忙)$", "", query).strip()
        if not query:
            continue
        normalized_query = query.lower()
        if normalized_query in seen:
            continue
        seen.add(normalized_query)
        queries.append(query)
    return queries


def _scheduled_job_run_once_permission_denied_output(
    *,
    attempted_queries: list[str],
    selected_references: list[dict[str, str]],
) -> dict[str, Any]:
    query_text = "、".join(attempted_queries) if attempted_queries else "这个 @ 引用"
    return {
        "answer": (
            f"我识别到你想执行定时作业：{query_text}，"
            "但当前账号没有执行定时作业的权限。请使用管理员账号，"
            "或让管理员授予定时作业执行权限后再执行。"
        ),
        "latency_ms": 0,
        "model": "assistant-deterministic",
        "references": selected_references,
        "selected_references": selected_references,
        "suggestions": ["联系管理员授权", "生成可确认的配置草案"],
        "tool_results": [
            {
                "intent": "scheduled_job_run_once",
                "items": [],
                "summary": {
                    "queries": attempted_queries,
                    "required_permission": SCHEDULED_JOB_RUN_PERMISSION,
                    "status": "permission_denied",
                },
                "tool": "assistant.scheduled_job_run",
            }
        ],
    }


def _scheduled_job_matches_mention(job: dict[str, Any], query: str) -> bool:
    normalized_query = query.lower().strip()
    haystack = " ".join(
        str(value or "")
        for value in (
            job.get("id"),
            job.get("name"),
            job.get("title"),
            job.get("code"),
            job.get("job_type"),
        )
    ).lower()
    if normalized_query in haystack:
        return True
    return assistant_reference_matches_query(
        "scheduled_job",
        job,
        query,
        current_store=None,
    )


def _scheduled_job_exactly_matches_mention(job: dict[str, Any], query: str) -> bool:
    normalized_query = _normalized_mention_token(query)
    if not normalized_query:
        return False
    return any(
        _normalized_mention_token(value) == normalized_query
        for value in (
            job.get("id"),
            job.get("name"),
            job.get("title"),
            job.get("code"),
        )
    )


def _scheduled_job_preferred_run_once_mention_matches(
    jobs: list[dict[str, Any]],
    query: str,
    *,
    require_official_insight: bool = False,
) -> list[dict[str, Any]]:
    if not _weekly_feedback_run_once_draft_requested(query, [query]):
        return []
    scored_matches = [
        (_scheduled_job_weekly_feedback_insight_score(job), job)
        for job in jobs
    ]
    preferred_matches = [
        (score, job)
        for score, job in scored_matches
        if score > 0
    ]
    if not preferred_matches:
        return []
    runnable_matches = [
        (score, job)
        for score, job in preferred_matches
        if _scheduled_job_is_runnable_mention_match(job)
    ]
    candidates = runnable_matches or preferred_matches
    if require_official_insight:
        candidates = [
            (score, job)
            for score, job in candidates
            if _scheduled_job_is_official_weekly_feedback_insight(job)
        ]
        if not candidates:
            return []
    ranked = sorted(
        candidates,
        key=lambda item: (
            item[0],
            str(item[1].get("updated_at") or item[1].get("created_at") or ""),
            str(item[1].get("id") or ""),
        ),
        reverse=True,
    )
    if len(ranked) == 1 or ranked[0][0] > ranked[1][0]:
        return [ranked[0][1]]
    return [job for _, job in ranked]


def _scheduled_job_is_official_weekly_feedback_insight(job: dict[str, Any]) -> bool:
    config_json = job.get("config_json")
    assistant_template = (
        config_json.get("assistant_template")
        if isinstance(config_json, dict)
        else None
    )
    template_code = (
        assistant_template.get("code")
        if isinstance(assistant_template, dict)
        else None
    )
    return (
        template_code == "weekly_feedback_insight"
        or str(job.get("job_type") or "").strip() == "user_feedback_insight_extract"
    )


def _scheduled_job_weekly_feedback_insight_score(job: dict[str, Any]) -> int:
    config_json = job.get("config_json")
    assistant_template = (
        config_json.get("assistant_template")
        if isinstance(config_json, dict)
        else None
    )
    template_code = (
        assistant_template.get("code")
        if isinstance(assistant_template, dict)
        else None
    )
    code = str(job.get("code") or "").strip()
    job_type = str(job.get("job_type") or "").strip()
    title = _normalized_mention_token(
        " ".join(
            str(value or "")
            for value in (
                job.get("name"),
                job.get("title"),
                job.get("description"),
                job.get("summary"),
            )
        )
    )
    source_system = str(job.get("source_system") or "").strip()
    score = 0
    if code == "weekly_feedback_insight":
        score += 70
    if template_code == "weekly_feedback_insight":
        score += 65
    if job_type == "user_feedback_insight_extract":
        score += 60
    if "用户反馈" in title or "feedback" in title:
        score += 20
    if any(
        keyword in title
        for keyword in ("洞察", "提取", "抽取", "有价值", "价值", "insight", "extract")
    ):
        score += 20
    if "每周" in title or "weekly" in title:
        score += 10
    if source_system == "aliyun-maxcompute":
        score += 5
    if _scheduled_job_is_runnable_mention_match(job):
        score += 5
    return score


def _scheduled_job_is_runnable_mention_match(job: dict[str, Any]) -> bool:
    return bool(job.get("enabled")) and str(job.get("status") or "active") == "active"


def _user_can_run_scheduled_job_from_assistant(user: dict[str, Any]) -> bool:
    roles = set(user.get("roles") or [])
    permissions = set(user.get("permissions") or [])
    return (
        "admin" in roles
        or "system.admin" in permissions
        or SCHEDULED_JOB_MANAGE_PERMISSION in permissions
        or SCHEDULED_JOB_RUN_PERMISSION in permissions
    )


def _normalized_mention_token(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _scheduled_job_run_should_return_immediately(job: dict[str, Any]) -> bool:
    if not job.get("enabled"):
        return False
    return str(job.get("job_type") or "") in ASSISTANT_ASYNC_SCHEDULED_JOB_TYPES


def _active_scheduled_job_run_for_job(
    current_store: MemoryStore,
    *,
    job: dict[str, Any],
    job_id: str,
) -> dict[str, Any] | None:
    candidates = [
        run
        for run in getattr(current_store, "scheduled_job_runs", {}).values()
        if str(run.get("scheduled_job_id") or "") == job_id
        and str(run.get("status") or "") in ASSISTANT_TRACKED_RUN_STATUSES
        and not _scheduled_job_run_is_stale(run, job)
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda run: str(
            run.get("updated_at")
            or run.get("created_at")
            or run.get("started_at")
            or run.get("scheduled_for")
            or "",
        ),
    )[-1]


def _scheduled_job_run_is_stale(run: dict[str, Any], job: dict[str, Any]) -> bool:
    ttl_seconds = int(job.get("lock_ttl_seconds") or job.get("timeout_seconds") or 0)
    if ttl_seconds <= 0:
        return False
    timestamp = _scheduled_job_run_timestamp(run)
    if timestamp is None:
        return False
    return datetime.now(UTC) - timestamp > timedelta(seconds=ttl_seconds)


def _scheduled_job_run_timestamp(run: dict[str, Any]) -> datetime | None:
    for field in ("updated_at", "started_at", "created_at", "scheduled_for"):
        raw_value = run.get(field)
        if not raw_value:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None


def _start_scheduled_job_run_once_in_background(
    *,
    current_store: MemoryStore,
    job_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    existing_run_ids = {
        str(run.get("id"))
        for run in getattr(current_store, "scheduled_job_runs", {}).values()
        if run.get("id") is not None
    }
    result: dict[str, dict[str, Any]] = {}
    error: dict[str, HTTPException] = {}
    done = threading.Event()

    def worker() -> None:
        try:
            result["run"] = run_scheduled_job_response(
                current_store=current_store,
                job_id=job_id,
                source_run_id=None,
                trigger_type="manual",
                user=user,
            )
        except HTTPException as exc:
            error["exception"] = exc
        finally:
            done.set()

    thread = threading.Thread(
        target=worker,
        name=f"assistant-scheduled-job-run-{job_id}",
        daemon=True,
    )
    thread.start()
    deadline = perf_counter() + ASSISTANT_ASYNC_RUN_START_TIMEOUT_SECONDS
    while perf_counter() < deadline:
        run = _new_scheduled_job_run(
            current_store,
            existing_run_ids=existing_run_ids,
            job_id=job_id,
        )
        if run is not None:
            return run
        if done.is_set():
            if error.get("exception") is not None:
                raise error["exception"]
            if result.get("run") is not None:
                return result["run"]
            break
        sleep(ASSISTANT_ASYNC_RUN_POLL_SECONDS)
    if error.get("exception") is not None:
        raise error["exception"]
    if result.get("run") is not None:
        return result["run"]
    raise HTTPException(
        status_code=504,
        detail={
            "code": "SCHEDULED_JOB_RUN_START_TIMEOUT",
            "message": "Scheduled job run did not start in time",
        },
    )


def _new_scheduled_job_run(
    current_store: MemoryStore,
    *,
    existing_run_ids: set[str],
    job_id: str,
) -> dict[str, Any] | None:
    candidates = [
        run
        for run in getattr(current_store, "scheduled_job_runs", {}).values()
        if run.get("id") is not None
        and str(run.get("id")) not in existing_run_ids
        and str(run.get("scheduled_job_id")) == job_id
    ]
    if not candidates:
        return None
    for run in reversed(
        sorted(
            candidates,
            key=lambda item: str(item.get("created_at") or item.get("started_at") or ""),
        )
    ):
        traceable_run = _traceable_scheduled_job_run(current_store, run)
        if traceable_run is not None:
            return traceable_run
    return None


def _traceable_scheduled_job_run(
    current_store: MemoryStore,
    run: dict[str, Any],
) -> dict[str, Any] | None:
    if not run.get("collector_run_id"):
        return None
    repository = getattr(current_store, "repository", None)
    list_scheduled_job_runs = getattr(repository, "list_scheduled_job_runs", None)
    if not callable(list_scheduled_job_runs):
        return run
    persisted_runs = list_scheduled_job_runs(
        scheduled_job_id=str(run.get("scheduled_job_id") or ""),
        status=str(run.get("status") or ""),
    )
    return next(
        (
            persisted_run
            for persisted_run in persisted_runs
            if str(persisted_run.get("id") or "") == str(run.get("id") or "")
        ),
        None,
    )


def _http_exception_code_and_message(exc: HTTPException) -> tuple[str, str]:
    detail = exc.detail
    if isinstance(detail, dict):
        return (
            str(detail.get("code") or exc.status_code),
            str(detail.get("message") or "Scheduled job run failed"),
        )
    return str(exc.status_code), str(detail or "Scheduled job run failed")


def _scheduled_job_title(job: dict[str, Any], job_id: str) -> str:
    return str(job.get("name") or job.get("title") or job.get("code") or job_id)


def _scheduled_job_run_reference(
    *,
    job: dict[str, Any],
    job_id: str,
    run: dict[str, Any],
) -> dict[str, str]:
    run_id = str(run["id"])
    return {
        "id": run_id,
        "title": f"{_scheduled_job_title(job, job_id)} / {run.get('status') or 'unknown'}",
        "type": "scheduled_job_run",
        "url": f"/tasks/scheduled-jobs?run_id={run_id}",
    }


def _scheduled_job_run_tool_result(
    *,
    error_code: str | None,
    error_message: str | None,
    job: dict[str, Any],
    job_id: str,
    run: dict[str, Any] | None,
) -> dict[str, Any]:
    job_name = _scheduled_job_title(job, job_id)
    if run is None:
        return {
            "intent": "scheduled_job_run_once",
            "items": [],
            "references": [],
            "summary": {
                "error_code": error_code,
                "error_message": error_message,
                "scheduled_job_id": job_id,
                "scheduled_job_name": job_name,
                "status": "failed",
                "trigger_type": "manual",
            },
            "tool": "assistant.scheduled_job_run",
        }
    run_reference = _scheduled_job_run_reference(job=job, job_id=job_id, run=run)
    progress_text = _scheduled_job_run_progress_text(run)
    item = {
        "id": run_reference["id"],
        "records_imported": int(run.get("records_imported") or 0),
        "scheduled_job_id": job_id,
        "status": str(run.get("status") or "unknown"),
        "title": run_reference["title"],
        "trigger_type": str(run.get("trigger_type") or "manual"),
        "type": "scheduled_job_run",
        "url": run_reference["url"],
    }
    if progress_text:
        item["progress_text"] = progress_text
    summary = {
        "error_code": error_code,
        "error_message": error_message,
        "records_imported": int(run.get("records_imported") or 0),
        "run_id": run_reference["id"],
        "scheduled_job_id": job_id,
        "scheduled_job_name": job_name,
        "status": str(run.get("status") or "unknown"),
        "trigger_type": str(run.get("trigger_type") or "manual"),
    }
    if progress_text:
        summary["progress_text"] = progress_text
    return {
        "intent": "scheduled_job_run_once",
        "items": [item],
        "references": [run_reference],
        "summary": summary,
        "tool": "assistant.scheduled_job_run",
    }


def _scheduled_job_run_progress_text(run: dict[str, Any]) -> str | None:
    result_summary = run.get("result_summary")
    if not isinstance(result_summary, dict):
        return None
    execution_nodes = result_summary.get("execution_nodes")
    if not isinstance(execution_nodes, dict):
        return None
    runner_node = execution_nodes.get("runner_execution")
    if not isinstance(runner_node, dict):
        return None
    runner_status = str(runner_node.get("status") or "").strip()
    if runner_status not in {"claimed", "queued", "running"}:
        return None
    executor_type = str(runner_node.get("executor_type") or "AI 执行器").strip()
    runner_task_id = str(runner_node.get("runner_task_id") or "").strip()
    status_labels = {
        "claimed": "等待 AI 执行器开始执行",
        "queued": "等待 AI 执行器接单",
        "running": "AI 执行器执行中",
    }
    suffix = f"{executor_type} / {runner_task_id}" if runner_task_id else executor_type
    return f"{status_labels[runner_status]}：{suffix}"


def _merge_assistant_references(
    *reference_lists: list[dict[str, str]],
) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for reference_list in reference_lists:
        for reference in reference_list:
            key = (str(reference.get("type")), str(reference.get("id")))
            if key in seen:
                continue
            if not all(reference.get(field) for field in ("id", "title", "type", "url")):
                continue
            seen.add(key)
            references.append(reference)
            if len(references) >= 6:
                return references
    return references


def _ensure_non_blank(value: str | None, field: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise AssistantServiceError(400, "VALIDATION_ERROR", f"{field} is required")
    return normalized
