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
from app.services.assistant_references import (
    AssistantReferenceError,
    assistant_reference_matches_query,
    resolve_assistant_references,
)
from app.services.assistant_request_context import (
    assistant_request_store as assistant_context_request_store,
)
from app.services.assistant_request_context import (
    save_assistant_chat_records,
)
from app.services.assistant_tools import assistant_tool_results
from app.services.model_gateway_logging import (
    estimate_tokens,
    model_gateway_log,
    openai_usage_tokens,
)
from app.services.scheduled_jobs import run_scheduled_job_response

ASSISTANT_ACCESS_ROLES = {
    "admin",
    "knowledge_owner",
    "product_owner",
    "rd_owner",
    "reviewer",
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
TASK_CREATION_WIZARD_STEPS = ["数据来源", "AI处理", "结果动作", "调度策略", "确认执行"]
TASK_CREATION_GUIDE_ITEMS = [
    {
        "dependencies": [],
        "description": "创建普通研发任务前，先补齐产品、需求、版本、负责人和验收标准。",
        "draft_action": "clarify_rd_task",
        "prompt": "我要新增研发任务，请按产品、需求、版本、负责人和验收标准引导我补齐信息",
        "title": "研发任务",
        "type": "rd_task",
        "wizard_steps": ["任务目标", "产品/版本", "负责人", "验收标准", "确认创建"],
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
        "dependencies": ["插件连接"],
        "description": "为 GitHub、GitLab、邮箱等插件生成结果动作草案，确认前不写入真实动作。",
        "draft_action": "create_plugin_action",
        "prompt": "帮我新增插件动作，先生成可确认的动作草案",
        "title": "插件动作",
        "type": "plugin_action",
        "wizard_steps": ["插件", "连接", "请求配置", "结果映射", "确认创建"],
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

__all__ = [
    "ASSISTANT_ACCESS_ROLES",
    "AssistantChatRequest",
    "AssistantServiceError",
    "assistant_chat_response",
    "assistant_conversation_messages_response",
    "assistant_conversations_response",
    "assistant_request_store",
]


class AssistantChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    product_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    references: list[dict[str, Any]] = Field(default_factory=list)


class _AssistantGatewayRequestFailed(Exception):
    def __init__(self, log: dict[str, Any]):
        super().__init__("Assistant model gateway request failed")
        self.log = log


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
        context=payload.context,
        conversation_id=payload.conversation_id,
        message=message,
        product_id=payload.product_id,
        references=payload.references,
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

    audit_start_index = len(current_store.audit_events)
    deterministic_output = _deterministic_assistant_output(
        current_store,
        payload=normalized_payload,
        user=user,
    )
    if deterministic_output is not None:
        return _persist_assistant_chat_output(
            current_store,
            audit_start_index=len(current_store.audit_events),
            message=message,
            model_log=None,
            normalized_payload=normalized_payload,
            assistant_output=deterministic_output,
            user=user,
        )
    try:
        assistant_output, model_log = _call_model_gateway_for_assistant_chat(
            current_store,
            model_gateway_api_key=model_gateway_api_key,
            model_gateway_base_url=model_gateway_base_url,
            model_gateway_default_chat_model=model_gateway_default_chat_model,
            model_gateway_status=model_gateway_status,
            payload=normalized_payload,
            urlopen_func=urlopen_func,
            user=user,
        )
    except AssistantServiceError:
        raise
    except _AssistantGatewayRequestFailed as exc:
        current_store.audit(
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
        save_assistant_chat_records(
            current_store,
            conversation=None,
            messages=[],
            model_log=exc.log,
            audit_events=current_store.audit_events[audit_start_index:],
        )
        raise AssistantServiceError(
            502,
            "ASSISTANT_CHAT_FAILED",
            "Assistant model gateway request failed",
        ) from exc

    current_store.audit(
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
    return _persist_assistant_chat_output(
        current_store,
        audit_start_index=audit_start_index,
        message=message,
        model_log=model_log,
        normalized_payload=normalized_payload,
        assistant_output=assistant_output,
        user=user,
    )


def _persist_assistant_chat_output(
    current_store: MemoryStore,
    *,
    assistant_output: dict[str, Any],
    audit_start_index: int,
    message: str,
    model_log: dict[str, Any] | None,
    normalized_payload: AssistantChatRequest,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
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
        content=message,
        conversation=conversation,
        now=now,
        references=assistant_output.get("selected_references") or [],
        role="user",
        user_id=user["id"],
    )
    assistant_message = append_assistant_message(
        current_store,
        content=assistant_output["answer"],
        conversation=conversation,
        model=assistant_output["model"],
        now=now,
        references=assistant_output["references"],
        role="assistant",
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
    audit_payload = {
        "latency_ms": assistant_output["latency_ms"],
        "model": assistant_output["model"],
        "product_id": normalized_payload.product_id,
        "reference_count": len(assistant_output["references"]),
        "suggestion_count": len(assistant_output["suggestions"]),
        "tool_count": len(assistant_output["tool_results"]),
    }
    if model_log is not None:
        audit_payload["model_log_id"] = model_log["id"]
    current_store.audit(
        event_type="assistant.chat_completed",
        actor_id=user["id"],
        subject_type="assistant_conversation",
        subject_id=conversation["id"],
        payload=audit_payload,
    )
    save_assistant_chat_records(
        current_store,
        conversation=conversation,
        messages=[user_message, assistant_message],
        model_log=model_log,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return {
        "conversation_id": conversation["id"],
        "latency_ms": assistant_output["latency_ms"],
        "message": public_assistant_message(assistant_message),
        "model": assistant_output["model"],
        "suggestions": assistant_output["suggestions"],
    }


def _deterministic_assistant_output(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    if _task_creation_guide_requested(payload.message):
        try:
            resolved_references = resolve_assistant_references(
                current_store,
                references=payload.references,
                user=user,
            )
        except AssistantReferenceError as exc:
            raise AssistantServiceError(exc.status_code, exc.code, exc.message) from exc
        return _task_creation_guide_output(selected_references=resolved_references["items"])
    if not _scheduled_job_run_once_requested(payload.message):
        return _deterministic_action_draft_output(
            current_store,
            payload=payload,
            user=user,
        )
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
    if mention_resolution["references"]:
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
        answer = (
            f"已触发「{_scheduled_job_title(job, job_id)}」执行一次，"
            f"运行记录 {run_id} 当前状态为 {run_status}。"
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
        context=payload.context,
        conversation_id=payload.conversation_id,
        message=payload.message,
        product_id=payload.product_id,
        system_context=system_context,
    )


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
        with urlopen_func(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
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
    return has_create_intent and has_task_context and not has_specific_task_type


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
    if "admin" not in set(user.get("roles") or []):
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
            "我先生成周反馈洞察定时作业草案，确认并补齐校验项后再执行一次。"
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
    if "admin" not in set(user.get("roles") or []):
        return {"attempted": True, "queries": queries, "references": []}
    jobs = list(getattr(current_store, "scheduled_jobs", {}).values())
    if product_id:
        jobs = [job for job in jobs if job.get("product_id") == product_id]
    references: list[dict[str, str]] = []
    for query in queries:
        matches = [job for job in jobs if _scheduled_job_matches_mention(job, query)]
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
    for match in re.finditer(r"@([^@\n]+)", message):
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
) -> list[dict[str, Any]]:
    if not _weekly_feedback_run_once_draft_requested(query, [query]):
        return []
    preferred_matches = [
        job for job in jobs if _scheduled_job_is_weekly_feedback_insight_job(job)
    ]
    runnable_matches = [
        job for job in preferred_matches if _scheduled_job_is_runnable_mention_match(job)
    ]
    if len(runnable_matches) == 1:
        return runnable_matches
    return preferred_matches


def _scheduled_job_is_weekly_feedback_insight_job(job: dict[str, Any]) -> bool:
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
    source_system = str(job.get("source_system") or "").strip()
    return (
        code == "weekly_feedback_insight"
        or job_type == "user_feedback_insight_extract"
        or template_code == "weekly_feedback_insight"
        or source_system == "aliyun-maxcompute"
    )


def _scheduled_job_is_runnable_mention_match(job: dict[str, Any]) -> bool:
    return bool(job.get("enabled")) and str(job.get("status") or "active") == "active"


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
    return {
        "intent": "scheduled_job_run_once",
        "items": [
            {
                "id": run_reference["id"],
                "records_imported": int(run.get("records_imported") or 0),
                "scheduled_job_id": job_id,
                "status": str(run.get("status") or "unknown"),
                "title": run_reference["title"],
                "trigger_type": str(run.get("trigger_type") or "manual"),
                "type": "scheduled_job_run",
                "url": run_reference["url"],
            }
        ],
        "references": [run_reference],
        "summary": {
            "error_code": error_code,
            "error_message": error_message,
            "records_imported": int(run.get("records_imported") or 0),
            "run_id": run_reference["id"],
            "scheduled_job_id": job_id,
            "scheduled_job_name": job_name,
            "status": str(run.get("status") or "unknown"),
            "trigger_type": str(run.get("trigger_type") or "manual"),
        },
        "tool": "assistant.scheduled_job_run",
    }


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
