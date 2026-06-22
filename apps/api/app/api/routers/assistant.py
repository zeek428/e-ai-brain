from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.request import urlopen

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, api_error, require_permissions, require_roles, store
from app.core.config import get_settings
from app.core.trace import envelope, get_trace_id
from app.services.assistant_action_drafts import (
    cancel_assistant_action_draft_response,
    confirm_assistant_action_draft_response,
    create_assistant_action_draft_response,
    get_assistant_action_draft_response,
    mark_assistant_action_draft_modified_response,
    mark_assistant_action_draft_viewed_response,
    patch_assistant_action_draft_response,
)
from app.services.assistant_chat import (
    ASSISTANT_ACCESS_ROLES,
    AssistantChatRequest,
    AssistantServiceError,
    assistant_chat_response,
    assistant_chat_runs_response,
    assistant_conversation_messages_response,
    assistant_conversations_response,
    assistant_request_store,
    cancel_assistant_chat_run_response,
)
from app.services.assistant_draft_templates import list_assistant_draft_templates_response
from app.services.assistant_metrics import (
    assistant_metric_details_response,
    assistant_metrics_export_response,
    assistant_metrics_response,
)
from app.services.assistant_references import (
    AssistantReferenceError,
    assistant_reference_candidates_response,
    create_assistant_action_reference_config_response,
    delete_assistant_action_reference_config_response,
    list_assistant_action_reference_configs_response,
    patch_assistant_action_reference_config_response,
    resolve_assistant_references,
    set_assistant_action_reference_config_status_response,
    update_assistant_action_reference_config_rollout_response,
)
from app.services.assistant_role_quick_tasks import (
    create_assistant_role_quick_task_config_response,
    delete_assistant_role_quick_task_config_response,
    list_assistant_role_quick_task_configs_response,
    list_assistant_role_quick_tasks_response,
    patch_assistant_role_quick_task_config_response,
    set_assistant_role_quick_task_status_response,
    update_assistant_role_quick_task_rollout_response,
)
from app.services.platform_status import health_payload

settings = get_settings()
router = APIRouter(prefix="/api/assistant", tags=["assistant"])
ASSISTANT_ACTION_REFERENCES_MANAGE_PERMISSION = "assistant.action_references.manage"


class AssistantReferenceItem(BaseModel):
    id: str
    type: str


class AssistantReferenceResolveRequest(BaseModel):
    references: list[AssistantReferenceItem] = Field(default_factory=list)


class AssistantActionDraftRequest(BaseModel):
    action: str
    client_draft_id: str | None = None
    expires_at: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    source_message_id: str | None = None
    title: str


class AssistantActionDraftCancelRequest(BaseModel):
    reason: str | None = None


class AssistantChatRunCancelRequest(BaseModel):
    reason: str | None = None


class AssistantActionDraftModificationRequest(BaseModel):
    modified_fields: list[str] = Field(default_factory=list)
    user_modified: bool = True


class AssistantActionDraftPatchRequest(BaseModel):
    modified_fields: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    user_modified: bool = True


class AssistantActionDraftViewRequest(BaseModel):
    surface: str | None = None


class AssistantRoleQuickTaskConfigRequest(BaseModel):
    analytics_key: str | None = None
    enabled: bool = True
    enterprise_id: str | None = None
    group_enabled: bool = True
    group_key: str
    group_label: str
    group_roles: list[str] = Field(default_factory=list)
    group_sort_order: int = 0
    id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    prompt: str
    rollout_json: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    target_draft_type: str | None = None
    task_key: str
    template_version: str | None = None
    title: str


class AssistantRoleQuickTaskConfigPatchRequest(BaseModel):
    analytics_key: str | None = None
    enabled: bool | None = None
    enterprise_id: str | None = None
    group_enabled: bool | None = None
    group_key: str | None = None
    group_label: str | None = None
    group_roles: list[str] | None = None
    group_sort_order: int | None = None
    metadata_json: dict[str, Any] | None = None
    permissions: list[str] | None = None
    prompt: str | None = None
    rollout_json: dict[str, Any] | None = None
    sort_order: int | None = None
    target_draft_type: str | None = None
    task_key: str | None = None
    template_version: str | None = None
    title: str | None = None


class AssistantRoleQuickTaskStatusRequest(BaseModel):
    enabled: bool
    group_enabled: bool | None = None


class AssistantRoleQuickTaskRolloutRequest(BaseModel):
    enterprise_id: str | None = None
    rollout_json: dict[str, Any] = Field(default_factory=dict)
    template_version: str | None = None


class AssistantActionReferenceConfigRequest(BaseModel):
    action_key: str
    aliases: list[str] = Field(default_factory=list)
    enabled: bool = True
    enterprise_id: str | None = None
    id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    prompt: str
    roles: list[str] = Field(default_factory=list)
    rollout_json: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    summary: str
    template_version: str | None = None
    title: str
    url: str


class AssistantActionReferenceConfigPatchRequest(BaseModel):
    action_key: str | None = None
    aliases: list[str] | None = None
    enabled: bool | None = None
    enterprise_id: str | None = None
    metadata_json: dict[str, Any] | None = None
    permissions: list[str] | None = None
    prompt: str | None = None
    roles: list[str] | None = None
    rollout_json: dict[str, Any] | None = None
    sort_order: int | None = None
    summary: str | None = None
    template_version: str | None = None
    title: str | None = None
    url: str | None = None


class AssistantActionReferenceConfigStatusRequest(BaseModel):
    enabled: bool


class AssistantActionReferenceConfigRolloutRequest(BaseModel):
    enterprise_id: str | None = None
    rollout_json: dict[str, Any] = Field(default_factory=dict)
    template_version: str | None = None


@router.get("/runtime-status")
def assistant_runtime_status(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    trace_id = get_trace_id(request)
    current_store = store(request)
    health = health_payload(
        current_store=current_store,
        settings=settings,
        trace_id=trace_id,
    )
    model_gateway_configured = health["chat_gateway"] == "configured"
    checks = _assistant_runtime_checks(health)
    required_checks_ready = all(
        check["status"] in {"ok", "configured", "disabled"}
        for check in checks
        if check.get("required")
    )
    payload = {
        "chat_gateway": health["chat_gateway"],
        "embedding_gateway": health["embedding_gateway"],
        "long_memory": health["long_memory"],
        "model_gateway": health["model_gateway"],
        "mode": "model_gateway" if model_gateway_configured else "deterministic_only",
        "checks": checks,
        "operations": _assistant_runtime_operations(current_store, user=user),
        "ready": required_checks_ready,
        "warnings": [] if model_gateway_configured else [
            {
                "code": "MODEL_GATEWAY_NOT_CONFIGURED",
                "message": "模型网关未配置，AI 助手当前仅可稳定执行规则能力和已注册动作。",
            }
        ],
    }
    return envelope(payload, trace_id)


def _assistant_runtime_operations(
    current_store: Any,
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    can_view_scheduled_jobs = _assistant_runtime_user_has_any_permission(
        user,
        {"system.admin", "system.scheduled_jobs.manage", "system.scheduled_jobs.run"},
    )
    can_view_model_gateway = _assistant_runtime_user_has_any_permission(
        user,
        {"system.admin", "system.model_gateway.manage"},
    )
    can_view_executor_queue = _assistant_runtime_user_has_any_permission(
        user,
        {"system.admin", "system.plugins.manage", "system.scheduled_jobs.manage"},
    )
    chat_failures = [
        _assistant_runtime_chat_failure_item(run)
        for run in _assistant_runtime_chat_runs(current_store, user_id=str(user["id"]))
        if str(run.get("status") or "") == "failed"
    ]
    model_failures = (
        [
            _assistant_runtime_model_failure_item(log)
            for log in _assistant_runtime_model_gateway_logs(current_store, status="failed")
        ]
        if can_view_model_gateway
        else []
    )
    scheduled_failures = (
        [
            _assistant_runtime_scheduled_job_failure_item(run)
            for run in _assistant_runtime_scheduled_job_runs(current_store, status="failed")
        ]
        if can_view_scheduled_jobs
        else []
    )
    recent_failures = sorted(
        [
            item
            for item in chat_failures + model_failures + scheduled_failures
            if item is not None
        ],
        key=lambda item: _assistant_runtime_sort_time(
            item.get("updated_at") or item.get("created_at")
        ),
        reverse=True,
    )[:5]
    model_gateway_recent_failure = model_failures[0] if model_failures else None
    return {
        "executor_queue": (
            _assistant_runtime_executor_queue(current_store)
            if can_view_executor_queue
            else {
                "active_runners": 0,
                "failed": 0,
                "offline_runners": 0,
                "oldest_pending_task_created_at": None,
                "oldest_pending_task_id": None,
                "queued": 0,
                "running": 0,
                "succeeded": 0,
                "total_runners": 0,
                "visible": False,
            }
        ),
        "model_gateway_recent_failure": model_gateway_recent_failure,
        "recent_failures": recent_failures,
    }


def _assistant_runtime_user_has_any_permission(
    user: dict[str, Any],
    permissions: set[str],
) -> bool:
    roles = set(user.get("roles") or [])
    user_permissions = set(user.get("permissions") or [])
    return "admin" in roles or bool(user_permissions & permissions)


def _assistant_runtime_chat_runs(current_store: Any, *, user_id: str) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_assistant_chat_runs", None)
    if callable(list_runs):
        return [dict(run) for run in list_runs(user_id=user_id)]
    return [
        dict(run)
        for run in getattr(current_store, "assistant_chat_runs", {}).values()
        if str(run.get("user_id") or "") == user_id
    ]


def _assistant_runtime_model_gateway_logs(
    current_store: Any,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_logs = getattr(repository, "list_model_gateway_logs", None)
    if callable(list_logs):
        return [dict(log) for log in list_logs(status=status)]
    logs = [dict(log) for log in getattr(current_store, "model_gateway_logs", [])]
    if status is not None:
        logs = [log for log in logs if str(log.get("status") or "") == status]
    return sorted(
        logs,
        key=lambda item: _assistant_runtime_sort_time(
            item.get("created_at") or item.get("updated_at")
        ),
        reverse=True,
    )


def _assistant_runtime_scheduled_job_runs(
    current_store: Any,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_scheduled_job_runs", None)
    if callable(list_runs):
        return [dict(run) for run in list_runs(status=status)]
    runs = [dict(run) for run in getattr(current_store, "scheduled_job_runs", {}).values()]
    if status is not None:
        runs = [run for run in runs if str(run.get("status") or "") == status]
    return sorted(
        runs,
        key=lambda item: _assistant_runtime_sort_time(
            item.get("updated_at") or item.get("created_at")
        ),
        reverse=True,
    )


def _assistant_runtime_ai_executor_tasks(current_store: Any) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_tasks = getattr(repository, "list_ai_executor_tasks", None)
    if callable(list_tasks):
        return [dict(task) for task in list_tasks()]
    return [dict(task) for task in getattr(current_store, "ai_executor_tasks", {}).values()]


def _assistant_runtime_ai_executor_runners(current_store: Any) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_runners = getattr(repository, "list_ai_executor_runners", None)
    if callable(list_runners):
        return [dict(runner) for runner in list_runners()]
    return [dict(runner) for runner in getattr(current_store, "ai_executor_runners", {}).values()]


def _assistant_runtime_chat_failure_item(run: dict[str, Any]) -> dict[str, Any]:
    run_id = str(run.get("id") or "")
    conversation_id = str(run.get("conversation_id") or "")
    return {
        "created_at": run.get("created_at") or run.get("started_at"),
        "error_code": run.get("error_code"),
        "error_message": run.get("error_message") or "助手生成失败，请查看会话或模型网关日志。",
        "id": run_id,
        "kind": "assistant_chat_run",
        "label": "助手聊天失败",
        "status": run.get("status"),
        "title": run.get("title") or run_id,
        "updated_at": run.get("updated_at") or run.get("finished_at"),
        "url": f"/assistant?conversation_id={conversation_id}" if conversation_id else "/assistant",
    }


def _assistant_runtime_model_failure_item(log: dict[str, Any]) -> dict[str, Any]:
    log_id = str(log.get("id") or "")
    return {
        "created_at": log.get("created_at"),
        "error_code": "MODEL_GATEWAY_LOG_FAILED",
        "error_message": log.get("error") or "模型网关调用失败。",
        "id": log_id,
        "kind": "model_gateway_log",
        "label": "模型网关失败",
        "status": log.get("status"),
        "title": str(log.get("purpose") or "模型调用"),
        "updated_at": log.get("updated_at") or log.get("created_at"),
        "url": f"/system/model-gateway?log_id={log_id}",
    }


def _assistant_runtime_scheduled_job_failure_item(run: dict[str, Any]) -> dict[str, Any]:
    run_id = str(run.get("id") or "")
    job_id = str(run.get("scheduled_job_id") or "")
    return {
        "created_at": run.get("created_at") or run.get("started_at"),
        "error_code": run.get("error_code"),
        "error_message": run.get("error_message") or "定时作业运行失败。",
        "id": run_id,
        "kind": "scheduled_job_run",
        "label": "定时作业失败",
        "status": run.get("status"),
        "title": run.get("title") or run_id,
        "updated_at": run.get("updated_at") or run.get("finished_at"),
        "url": (
            f"/tasks/scheduled-jobs?job_id={job_id}&run_id={run_id}"
            if job_id
            else f"/tasks/scheduled-jobs?run_id={run_id}"
        ),
    }


def _assistant_runtime_executor_queue(current_store: Any) -> dict[str, Any]:
    tasks = _assistant_runtime_ai_executor_tasks(current_store)
    runners = _assistant_runtime_ai_executor_runners(current_store)
    status_counts: dict[str, int] = {
        "failed": 0,
        "queued": 0,
        "running": 0,
        "succeeded": 0,
    }
    pending_tasks: list[dict[str, Any]] = []
    for task in tasks:
        status = str(task.get("status") or "")
        if status in {"queued", "pending"}:
            status_counts["queued"] += 1
            pending_tasks.append(task)
        elif status in {"claimed", "running"}:
            status_counts["running"] += 1
        elif status == "succeeded":
            status_counts["succeeded"] += 1
        elif status == "failed":
            status_counts["failed"] += 1
    pending_tasks = sorted(
        pending_tasks,
        key=lambda item: _assistant_runtime_sort_time(item.get("created_at")),
    )
    active_runners = sum(1 for runner in runners if str(runner.get("status") or "") == "active")
    offline_runners = sum(
        1
        for runner in runners
        if str(runner.get("status") or "") in {"inactive", "offline", "disabled"}
    )
    oldest_pending = pending_tasks[0] if pending_tasks else None
    return {
        "active_runners": active_runners,
        "failed": status_counts["failed"],
        "offline_runners": offline_runners,
        "oldest_pending_task_created_at": (
            oldest_pending.get("created_at") if oldest_pending else None
        ),
        "oldest_pending_task_id": oldest_pending.get("id") if oldest_pending else None,
        "queued": status_counts["queued"],
        "running": status_counts["running"],
        "succeeded": status_counts["succeeded"],
        "total_runners": len(runners),
        "visible": True,
    }


def _assistant_runtime_sort_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)
    return datetime.min.replace(tzinfo=UTC)


def _assistant_runtime_checks(health: dict[str, str]) -> list[dict[str, Any]]:
    raw_checks = [
        {
            "action_label": "检查 PostgreSQL",
            "code": "postgres",
            "description": "助手会话、草案、指标和审计依赖 PostgreSQL 持久化。",
            "label": "PostgreSQL",
            "remediation": "确认 DATABASE_URL 指向的 PostgreSQL 可连接，并已执行数据库迁移。",
            "required": True,
            "severity": "critical",
            "status": health["postgres"],
        },
        {
            "action_label": "检查 Redis",
            "code": "redis",
            "description": "Redis 用于运行缓存、队列协作和部分异步任务协调。",
            "label": "Redis",
            "remediation": "启动 Redis，或修正 REDIS_URL 后重启 API。",
            "required": True,
            "severity": "critical",
            "status": health["redis"],
        },
        {
            "action_label": "配置模型网关",
            "code": "model_gateway",
            "description": "开放式问答需要可用的 OpenAI-compatible chat gateway。",
            "label": "模型网关",
            "remediation": "在模型网关页面配置默认 chat 模型、base_url 和 api_key。",
            "required": False,
            "severity": "warning",
            "status": health["model_gateway"],
            "url": "/system/model-gateway",
        },
        {
            "action_label": "配置 Embedding",
            "code": "embedding_gateway",
            "description": "知识 chunk 检索和语义召回需要 embedding gateway。",
            "label": "Embedding 网关",
            "remediation": "在默认模型网关中配置 embedding 模型，或明确选择禁用 embedding。",
            "required": False,
            "severity": "warning",
            "status": health["embedding_gateway"],
            "url": "/system/model-gateway",
        },
        {
            "action_label": "配置长期记忆",
            "code": "long_memory",
            "description": "GBrain 长期记忆是增强能力；未配置时回退到系统上下文和知识库。",
            "label": "GBrain 长期记忆",
            "remediation": "配置 GBRAIN_BASE_URL 和 GBRAIN_API_KEY，或保持未配置并使用知识库回退。",
            "required": False,
            "severity": "info",
            "status": health["long_memory"],
        },
    ]
    return [
        {
            **check,
            "action_url": check.get("url"),
            "detail": check.get("description"),
            "key": check["code"],
        }
        for check in raw_checks
    ]


@router.get("/conversations")
def list_assistant_conversations(
    request: Request,
    collapse: bool = True,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_conversations_response(
        store(request),
        collapse_duplicates=collapse,
        cursor=cursor,
        limit=limit,
        user_id=user["id"],
    )
    return envelope(payload, get_trace_id(request))


@router.post("/action-drafts")
def create_assistant_action_draft(
    request: Request,
    payload: AssistantActionDraftRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = create_assistant_action_draft_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/action-drafts/{draft_id}")
def get_assistant_action_draft(
    draft_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = get_assistant_action_draft_response(
        current_store=store(request),
        draft_id=draft_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/action-drafts/{draft_id}/confirm")
def confirm_assistant_action_draft(
    draft_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = confirm_assistant_action_draft_response(
        current_store=store(request),
        draft_id=draft_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/action-drafts/{draft_id}/cancel")
def cancel_assistant_action_draft(
    draft_id: str,
    request: Request,
    payload: AssistantActionDraftCancelRequest | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = cancel_assistant_action_draft_response(
        current_store=store(request),
        draft_id=draft_id,
        reason=payload.reason if payload else None,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/action-drafts/{draft_id}/modification")
def mark_assistant_action_draft_modified(
    draft_id: str,
    request: Request,
    payload: AssistantActionDraftModificationRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = mark_assistant_action_draft_modified_response(
        current_store=store(request),
        draft_id=draft_id,
        modified_fields=payload.modified_fields,
        user=user,
        user_modified=payload.user_modified,
    )
    return envelope(result, get_trace_id(request))


@router.patch("/action-drafts/{draft_id}")
def patch_assistant_action_draft(
    draft_id: str,
    request: Request,
    payload: AssistantActionDraftPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = patch_assistant_action_draft_response(
        current_store=store(request),
        draft_id=draft_id,
        modified_fields=payload.modified_fields,
        payload=payload.payload,
        user=user,
        user_modified=payload.user_modified,
    )
    return envelope(result, get_trace_id(request))


@router.post("/action-drafts/{draft_id}/view")
def mark_assistant_action_draft_viewed(
    draft_id: str,
    request: Request,
    payload: AssistantActionDraftViewRequest | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    result = mark_assistant_action_draft_viewed_response(
        current_store=store(request),
        draft_id=draft_id,
        surface=payload.surface if payload else None,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/metrics")
def assistant_metrics(
    request: Request,
    action: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    role: str | None = Query(default=None),
    window_days: int | None = Query(default=None, ge=1, le=365),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_metrics_response(
        assistant_request_store(store(request), user_id=user["id"]),
        action=action,
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
        role=role,
        user=user,
        window_days=window_days,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/metrics/details")
def assistant_metric_details(
    request: Request,
    action: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    metric: str = Query(default="draft_total"),
    product_id: str | None = Query(default=None),
    role: str | None = Query(default=None),
    window_days: int | None = Query(default=None, ge=1, le=365),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_metric_details_response(
        assistant_request_store(store(request), user_id=user["id"]),
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        metric=metric,
        product_id=product_id,
        role=role,
        user=user,
        window_days=window_days,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/metrics/export")
def assistant_metrics_export(
    request: Request,
    action: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    export_format: str = Query(default="csv", alias="format"),
    product_id: str | None = Query(default=None),
    role: str | None = Query(default=None),
    window_days: int | None = Query(default=None, ge=1, le=365),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_metrics_export_response(
        assistant_request_store(store(request), user_id=user["id"]),
        action=action,
        date_from=date_from,
        date_to=date_to,
        export_format=export_format,
        product_id=product_id,
        role=role,
        user=user,
        window_days=window_days,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/draft-templates")
def list_assistant_draft_templates(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = list_assistant_draft_templates_response(user=user)
    return envelope(payload, get_trace_id(request))


@router.get("/role-quick-tasks")
def list_assistant_role_quick_tasks(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = list_assistant_role_quick_tasks_response(
        current_store=store(request),
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.get("/role-quick-task-configs")
def list_assistant_role_quick_task_configs(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    payload = list_assistant_role_quick_task_configs_response(
        current_store=store(request),
    )
    return envelope(payload, get_trace_id(request))


@router.post("/role-quick-task-configs")
def create_assistant_role_quick_task_config(
    request: Request,
    payload: AssistantRoleQuickTaskConfigRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    result = create_assistant_role_quick_task_config_response(
        current_store=store(request),
        payload=payload.model_dump(exclude_none=True),
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.patch("/role-quick-task-configs/{config_id}")
def patch_assistant_role_quick_task_config(
    config_id: str,
    request: Request,
    payload: AssistantRoleQuickTaskConfigPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    result = patch_assistant_role_quick_task_config_response(
        config_id=config_id,
        current_store=store(request),
        payload=payload.model_dump(exclude_unset=True),
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/role-quick-task-configs/{config_id}/status")
def set_assistant_role_quick_task_status(
    config_id: str,
    request: Request,
    payload: AssistantRoleQuickTaskStatusRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    result = set_assistant_role_quick_task_status_response(
        config_id=config_id,
        current_store=store(request),
        enabled=payload.enabled,
        group_enabled=payload.group_enabled,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.put("/role-quick-task-configs/{config_id}/rollout")
def update_assistant_role_quick_task_rollout(
    config_id: str,
    request: Request,
    payload: AssistantRoleQuickTaskRolloutRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    result = update_assistant_role_quick_task_rollout_response(
        config_id=config_id,
        current_store=store(request),
        enterprise_id=payload.enterprise_id,
        rollout_json=payload.rollout_json,
        template_version=payload.template_version,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.delete("/role-quick-task-configs/{config_id}")
def delete_assistant_role_quick_task_config(
    config_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    result = delete_assistant_role_quick_task_config_response(
        config_id=config_id,
        current_store=store(request),
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/action-reference-configs")
def list_assistant_action_reference_configs(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {ASSISTANT_ACTION_REFERENCES_MANAGE_PERMISSION})
    payload = list_assistant_action_reference_configs_response(
        current_store=store(request),
    )
    return envelope(payload, get_trace_id(request))


@router.post("/action-reference-configs")
def create_assistant_action_reference_config(
    request: Request,
    payload: AssistantActionReferenceConfigRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {ASSISTANT_ACTION_REFERENCES_MANAGE_PERMISSION})
    result = create_assistant_action_reference_config_response(
        current_store=store(request),
        payload=payload.model_dump(exclude_none=True),
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.patch("/action-reference-configs/{config_id}")
def patch_assistant_action_reference_config(
    config_id: str,
    request: Request,
    payload: AssistantActionReferenceConfigPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {ASSISTANT_ACTION_REFERENCES_MANAGE_PERMISSION})
    result = patch_assistant_action_reference_config_response(
        config_id=config_id,
        current_store=store(request),
        payload=payload.model_dump(exclude_unset=True),
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/action-reference-configs/{config_id}/status")
def set_assistant_action_reference_config_status(
    config_id: str,
    request: Request,
    payload: AssistantActionReferenceConfigStatusRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {ASSISTANT_ACTION_REFERENCES_MANAGE_PERMISSION})
    result = set_assistant_action_reference_config_status_response(
        config_id=config_id,
        current_store=store(request),
        enabled=payload.enabled,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.put("/action-reference-configs/{config_id}/rollout")
def update_assistant_action_reference_config_rollout(
    config_id: str,
    request: Request,
    payload: AssistantActionReferenceConfigRolloutRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {ASSISTANT_ACTION_REFERENCES_MANAGE_PERMISSION})
    result = update_assistant_action_reference_config_rollout_response(
        config_id=config_id,
        current_store=store(request),
        enterprise_id=payload.enterprise_id,
        rollout_json=payload.rollout_json,
        template_version=payload.template_version,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.delete("/action-reference-configs/{config_id}")
def delete_assistant_action_reference_config(
    config_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {ASSISTANT_ACTION_REFERENCES_MANAGE_PERMISSION})
    result = delete_assistant_action_reference_config_response(
        config_id=config_id,
        current_store=store(request),
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/reference-candidates")
def list_assistant_reference_candidates(
    request: Request,
    query: str = "",
    product_id: str | None = None,
    reference_type: str | None = Query(default=None, alias="type"),
    limit: int = Query(default=8, ge=1, le=20),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    payload = assistant_reference_candidates_response(
        assistant_request_store(store(request), user_id=user["id"]),
        limit=limit,
        message=query,
        product_id=product_id,
        reference_type=reference_type,
        user=user,
    )
    return envelope(payload, get_trace_id(request))


@router.post("/references/resolve")
def resolve_assistant_reference_items(
    request: Request,
    payload: AssistantReferenceResolveRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    try:
        result = resolve_assistant_references(
            assistant_request_store(store(request), user_id=user["id"]),
            references=[item.model_dump() for item in payload.references],
            user=user,
        )
    except AssistantReferenceError as exc:
        raise api_error(exc.status_code, exc.code, exc.message) from exc
    return envelope(result, get_trace_id(request))


@router.get("/conversations/{conversation_id}/messages")
def list_assistant_conversation_messages(
    conversation_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    try:
        payload = assistant_conversation_messages_response(
            store(request),
            conversation_id=conversation_id,
            user_id=user["id"],
        )
    except AssistantServiceError as exc:
        raise api_error(exc.status_code, exc.code, exc.message) from exc
    return envelope(payload, get_trace_id(request))


@router.post("/chat")
def chat_with_assistant(
    request: Request,
    payload: AssistantChatRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    current_store = assistant_request_store(store(request), user_id=user["id"])
    try:
        response_payload = assistant_chat_response(
            current_store,
            model_gateway_api_key=settings.model_gateway_api_key,
            model_gateway_base_url=settings.model_gateway_base_url,
            model_gateway_default_chat_model=settings.model_gateway_default_chat_model,
            model_gateway_status=settings.model_gateway_status,
            payload=payload,
            urlopen_func=urlopen,
            user=user,
        )
    except AssistantServiceError as exc:
        raise api_error(exc.status_code, exc.code, exc.message) from exc
    return envelope(response_payload, get_trace_id(request))


@router.get("/chat-runs")
def list_assistant_chat_runs(
    request: Request,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    current_store = assistant_request_store(store(request), user_id=user["id"])
    try:
        result = assistant_chat_runs_response(
            current_store,
            limit=limit,
            status=status,
            user=user,
        )
    except AssistantServiceError as exc:
        raise api_error(exc.status_code, exc.code, exc.message) from exc
    return envelope(result, get_trace_id(request))


@router.post("/chat-runs/{run_id}/cancel")
def cancel_assistant_chat_run(
    run_id: str,
    request: Request,
    payload: AssistantChatRunCancelRequest | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, ASSISTANT_ACCESS_ROLES)
    current_store = assistant_request_store(store(request), user_id=user["id"])
    try:
        result = cancel_assistant_chat_run_response(
            current_store,
            reason=payload.reason if payload else None,
            run_id=run_id,
            user=user,
        )
    except AssistantServiceError as exc:
        raise api_error(exc.status_code, exc.code, exc.message) from exc
    return envelope(result, get_trace_id(request))
