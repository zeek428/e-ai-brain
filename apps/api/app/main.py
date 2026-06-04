from __future__ import annotations

import hashlib
import json
import os
import re
import socket
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.core.code_review_executor import (
    CodeReviewExecutorError,
    CodeReviewExecutorResult,
    ExternalCommandCodeReviewExecutor,
    normalize_code_review_output,
)
from app.core.config import get_settings
from app.core.graph_runtime import run_ai_task_graph
from app.core.persistence import (
    PostgresRuntimeStore,
    PostgresSnapshotRepository,
)
from app.core.roles import ASSIGNABLE_ROLE_CODES, list_role_definitions
from app.core.security import TokenError, create_access_token, parse_access_token, verify_password
from app.core.store import DEFAULT_BRAIN_APP_ID, MemoryStore, default_brain_apps
from app.core.trace import envelope, get_trace_id, new_trace_id
from app.core.users import SEEDED_USERS, MemoryUserRepository, PostgresUserRepository

settings = get_settings()

app = FastAPI(title="Enterprise AI Brain API", version="0.1.0")


def _is_test_env() -> bool:
    return settings.app_env.lower() in {"test", "testing", "pytest"}


def _ensure_memory_mode_allowed() -> None:
    if settings.persistence_mode == "memory" and not _is_test_env():
        raise RuntimeError("PERSISTENCE_MODE=memory is only allowed when APP_ENV=test")


def _runtime_data_access_mode() -> str:
    if settings.persistence_mode == "memory":
        return "memory_test_helper"
    return "db_first_migration"


def build_store() -> MemoryStore:
    if settings.persistence_mode == "postgres":
        repository = PostgresSnapshotRepository(
            settings.database_url,
            pool_max_size=settings.database_pool_max_size,
        )
        return PostgresRuntimeStore(repository)
    _ensure_memory_mode_allowed()
    if settings.persistence_mode != "memory":
        raise RuntimeError(f"Unsupported PERSISTENCE_MODE={settings.persistence_mode}")
    return MemoryStore()


def build_user_repository() -> MemoryUserRepository | PostgresUserRepository:
    if settings.persistence_mode == "postgres":
        return PostgresUserRepository(
            settings.database_url,
            pool_max_size=settings.database_pool_max_size,
        )
    _ensure_memory_mode_allowed()
    if settings.persistence_mode != "memory":
        raise RuntimeError(f"Unsupported PERSISTENCE_MODE={settings.persistence_mode}")
    return MemoryUserRepository.seeded()


app.state.store = build_store()
app.state.user_repository = build_user_repository()
app.state.code_review_executor = None
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


TECHNICAL_SOLUTION_FOLLOWUP_TASK_TYPES = {
    "development_planning",
    "automated_testing",
    "release_readiness",
}
RELEASE_READINESS_FOLLOWUP_TASK_TYPES = {"post_release_analysis"}
REQUIREMENT_STATUSES = {
    "accepted",
    "approved",
    "cancelled",
    "closed",
    "code_reviewing",
    "deferred",
    "designing",
    "developing",
    "draft",
    "planned",
    "ready_for_dev",
    "ready_for_release",
    "rejected",
    "released",
    "submitted",
    "testing",
}
LEGACY_REQUIREMENT_STATUS_ALIASES = {
    "pending_approval": "submitted",
    "task_created": "designing",
}
REQUIREMENT_CLOSABLE_STATUSES = REQUIREMENT_STATUSES - {"draft", "submitted"}
REQUIREMENT_BATCH_SCHEDULABLE_STATUSES = {"approved", "planned"}
REQUIREMENT_TASK_CREATABLE_STATUSES = {
    "code_reviewing",
    "designing",
    "developing",
    "planned",
    "ready_for_dev",
    "ready_for_release",
    "released",
    "testing",
}
REQUIREMENT_STATUS_AFTER_TASK_CREATED = {
    "automated_testing": "testing",
    "code_review": "code_reviewing",
    "development_planning": "developing",
    "post_release_analysis": "released",
    "product_detail_design": "designing",
    "release_readiness": "ready_for_release",
    "technical_solution": "ready_for_dev",
}
REQUIREMENT_STATUS_AFTER_TASK_COMPLETED = {
    "automated_testing": "ready_for_release",
    "code_review": "testing",
    "development_planning": "developing",
    "post_release_analysis": "accepted",
    "product_detail_design": "ready_for_dev",
    "release_readiness": "released",
    "technical_solution": "ready_for_dev",
}
BUG_SOURCES = {"ai_auto_test", "ai_post_release", "manual_test"}
BUG_SEVERITIES = {"blocker", "critical", "major", "minor"}
BUG_STATUSES = {
    "open",
    "triaged",
    "needs_info",
    "assigned",
    "fixed",
    "verified",
    "closed",
    "reopened",
}
USER_FEEDBACK_TYPES = {"bug", "complaint", "improvement", "praise", "question"}
USER_FEEDBACK_SENTIMENTS = {"negative", "neutral", "positive"}
USER_FEEDBACK_STATUSES = {"archived", "linked", "open", "resolved", "triaged"}
GITLAB_DAILY_METRIC_STATUSES = {"collected", "failed", "partial"}
JENKINS_RELEASE_STATUSES = {"canceled", "failed", "running", "success"}
ONLINE_LOG_METRIC_STATUSES = {"collected", "failed", "partial"}
ITERATION_SUGGESTION_STATUSES = {
    "accepted",
    "converted_to_requirement",
    "draft",
    "edited_accepted",
    "rejected",
    "suggested",
}
ITERATION_DECISIONS = {"accepted", "edited_accepted", "rejected"}
ITERATION_PRIORITIES = {"P0", "P1", "P2", "P3"}
ITERATION_CONFIDENCE_LEVELS = {"high", "low", "medium"}
ITERATION_EFFORTS = {"high", "low", "medium"}
COLLECTOR_TYPES = {
    "gitlab_daily_code_metric",
    "iteration_plan_suggestion",
    "jenkins_release",
    "online_log_metric",
    "user_feedback",
    "user_usage_metric",
}
COLLECTOR_RUN_STATUSES = {"cancelled", "failed", "running", "succeeded"}
COLLECTOR_TERMINAL_STATUSES = {"cancelled", "failed", "succeeded"}
PENDING_ATTRIBUTION_SOURCE_TYPES = COLLECTOR_TYPES
PENDING_ATTRIBUTION_STATUSES = {"ignored", "pending", "resolved"}
PENDING_ATTRIBUTION_RESOLUTION_ACTIONS = {"ignore_as_noise", "link_existing_context"}
USER_ROLES = ASSIGNABLE_ROLE_CODES
USER_STATUSES = {"active", "inactive"}
PRODUCT_STATUSES = {"active", "inactive"}
VERSION_STATUSES = {"active", "archived", "planning", "released", "testing"}
VERSION_MAIN_STATUSES = {"active", "planning", "released", "testing"}
VERSION_STATUS_TRANSITIONS = {
    "active": {"testing"},
    "planning": {"active"},
    "released": {"archived"},
    "testing": {"released"},
}
VERSION_REQUIREMENT_AUTO_ADVANCE = {
    "active": {
        "approved": "ready_for_dev",
        "planned": "ready_for_dev",
    },
    "released": {
        "ready_for_release": "released",
        "testing": "released",
    },
    "testing": {
        "approved": "testing",
        "code_reviewing": "testing",
        "designing": "testing",
        "developing": "testing",
        "planned": "testing",
        "ready_for_dev": "testing",
    },
}
VERSION_REQUIREMENT_ALLOWED_UNCHANGED = {
    "active": {
        "accepted",
        "cancelled",
        "closed",
        "code_reviewing",
        "deferred",
        "developing",
        "ready_for_dev",
        "ready_for_release",
        "rejected",
        "released",
        "testing",
    },
    "released": {
        "accepted",
        "cancelled",
        "closed",
        "deferred",
        "rejected",
        "released",
    },
    "archived": {
        "accepted",
        "cancelled",
        "closed",
        "deferred",
        "rejected",
        "released",
    },
    "testing": {
        "accepted",
        "cancelled",
        "closed",
        "deferred",
        "ready_for_release",
        "rejected",
        "released",
        "testing",
    },
}
VERSION_REQUIREMENT_BLOCK_REASONS = {
    "active": "需求尚未进入可开发状态，版本进入开发会形成范围风险",
    "archived": "需求尚未达到发布或终止状态，归档会形成历史数据风险",
    "released": "需求尚未达到发布或终止状态，不能发布版本",
    "testing": "需求尚未进入可交付状态，进入测试会形成版本风险",
}
REQUIREMENT_SCHEDULABLE_VERSION_STATUSES = {"active", "planning"}
MODULE_STATUSES = {"active", "inactive"}
GIT_REPO_STATUSES = {"active", "inactive"}
GIT_REPO_PROVIDERS = {"gitlab", "github"}
RELATED_SYSTEM_STATUSES = {"active", "inactive"}
MODEL_GATEWAY_PROVIDERS = {"openai_compatible"}
MODEL_GATEWAY_STATUSES = {"active", "inactive"}
MODEL_GATEWAY_TEST_TARGETS = {"chat", "chat_and_embedding", "embedding"}
MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES = {"custom", "disabled", "reuse_chat"}
RETRYABLE_TASK_FAILURE_STEPS = {"code_review_executor_failed", "model_gateway_failed"}
KNOWLEDGE_INDEX_STATUSES = {
    "archived",
    "importing",
    "indexed",
    "index_failed",
    "pending_index",
    "text_indexed",
    "vector_indexed",
}
KNOWLEDGE_SEARCHABLE_STATUSES = {"indexed", "text_indexed", "vector_indexed"}
BUG_STATUS_TRANSITIONS = {
    "open": {"triaged", "assigned", "closed"},
    "needs_info": {"open", "triaged", "closed"},
    "triaged": {"assigned", "closed"},
    "assigned": {"fixed", "reopened", "closed"},
    "fixed": {"verified", "reopened"},
    "verified": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"triaged", "assigned", "closed"},
}


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    display_name: str
    password: str
    roles: list[str] = Field(default_factory=lambda: ["viewer"])
    status: str = "active"


class UserPatchRequest(BaseModel):
    display_name: str | None = None
    password: str | None = None
    roles: list[str] | None = None
    status: str | None = None


class ProductRequest(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    owner_team: str | None = None
    status: str = "active"
    display_order: int = 0


class ProductPatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    owner_team: str | None = None
    status: str | None = None
    display_order: int | None = None


class ProductVersionRequest(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    status: str = "planning"
    start_date: str | None = None
    release_date: str | None = None


class ProductVersionPatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    start_date: str | None = None
    release_date: str | None = None


class ProductVersionAdvanceStatusRequest(BaseModel):
    target_status: str
    reason: str | None = None
    force: bool = False
    preview_only: bool = False


class ProductModuleRequest(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    owner_team: str | None = None
    status: str = "active"
    display_order: int = 0


class ProductModulePatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    owner_team: str | None = None
    status: str | None = None
    display_order: int | None = None


class ProductGitRepositoryRequest(BaseModel):
    repo_type: str = "code"
    name: str
    remote_url: str | None = None
    git_provider: str = "gitlab"
    project_id: str | None = None
    project_path: str | None = None
    credential_ref: str | None = None
    default_branch: str = "main"
    root_path: str = "/"
    status: str = "active"


class ProductGitRepositoryPatchRequest(BaseModel):
    repo_type: str | None = None
    name: str | None = None
    remote_url: str | None = None
    git_provider: str | None = None
    project_id: str | None = None
    project_path: str | None = None
    credential_ref: str | None = None
    default_branch: str | None = None
    root_path: str | None = None
    status: str | None = None


class RelatedSystemRequest(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    owner_team: str | None = None
    product_id: str | None = None
    status: str = "active"
    display_order: int = 0


class RelatedSystemPatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    owner_team: str | None = None
    product_id: str | None = None
    status: str | None = None
    display_order: int | None = None


class ModelGatewayConfigRequest(BaseModel):
    name: str
    provider: str = "openai_compatible"
    base_url: str
    api_key: str | None = None
    default_chat_model: str
    default_embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_connection_mode: str | None = None
    embedding_dimension: int | None = None
    timeout_seconds: int = 60
    max_retries: int = 1
    status: str = "active"
    is_default: bool = False


class ModelGatewayConfigPatchRequest(BaseModel):
    name: str | None = None
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    default_chat_model: str | None = None
    default_embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_connection_mode: str | None = None
    embedding_dimension: int | None = None
    timeout_seconds: int | None = None
    max_retries: int | None = None
    status: str | None = None
    is_default: bool | None = None


class ModelGatewayConfigTestRequest(BaseModel):
    name: str
    provider: str = "openai_compatible"
    base_url: str
    api_key: str | None = None
    default_chat_model: str | None = None
    default_embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_connection_mode: str | None = None
    embedding_dimension: int | None = None
    timeout_seconds: int = 60
    max_retries: int = 1
    status: str = "active"
    is_default: bool = False
    config_id: str | None = None
    test_target: str = "chat_and_embedding"


class RequirementRequest(BaseModel):
    title: str
    product_id: str
    version_id: str | None = None
    module_code: str | None = None
    content: str
    priority: str = "P1"


class RequirementPatchRequest(BaseModel):
    title: str | None = None
    product_id: str | None = None
    version_id: str | None = None
    module_code: str | None = None
    content: str | None = None
    priority: str | None = None


class RequirementBatchScheduleRequest(BaseModel):
    product_id: str
    version_id: str
    requirement_ids: list[str] = Field(min_length=1)
    reason: str | None = None


class RequirementDecisionRequest(BaseModel):
    comment: str | None = None
    rejection_reason: str | None = None


class AiTaskRequest(BaseModel):
    task_type: str
    title: str
    requirement_id: str
    input: dict[str, Any] = Field(default_factory=dict)


class AssistantChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    product_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class GitLabSnapshotRequest(BaseModel):
    requirement_id: str
    technical_solution_task_id: str


class KnowledgeDocumentRequest(BaseModel):
    title: str
    content: str
    doc_type: str = "manual"
    product_id: str | None = None
    permission_roles: list[str] = Field(default_factory=lambda: ["admin"])
    tags: list[str] = Field(default_factory=list)


class KnowledgeDocumentPatchRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    doc_type: str | None = None
    product_id: str | None = None
    permission_roles: list[str] | None = None
    tags: list[str] | None = None
    index_status: str | None = None
    index_error: str | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 8


class KnowledgeDepositApproveRequest(BaseModel):
    title: str | None = None
    permission_roles: list[str] = Field(default_factory=lambda: ["admin"])


class KnowledgeDepositRejectRequest(BaseModel):
    reason: str


class MoreInfoRequest(BaseModel):
    answers: list[dict[str, str]] = Field(default_factory=list)


class ReviewDecisionRequest(BaseModel):
    version: int
    edited_content: dict[str, Any] | None = None
    decision_reason: str | None = None
    questions: list[str] = Field(default_factory=list)


class BugRequest(BaseModel):
    product_id: str
    version_id: str | None = None
    module_code: str | None = None
    source: str
    title: str
    severity: str
    description: str
    related_task_id: str | None = None
    requirement_id: str | None = None
    reproduce_steps: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    assignee: str | None = None
    duplicate_of_bug_id: str | None = None


class BugPatchRequest(BaseModel):
    status: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None
    assignee: str | None = None
    reproduce_steps: list[str] | None = None
    evidence: dict[str, Any] | None = None
    duplicate_of_bug_id: str | None = None


class GitlabDailyCodeMetricRequest(BaseModel):
    product_id: str
    repository_id: str
    metric_date: str
    commit_count: int = 0
    active_author_count: int = 0
    merge_request_count: int = 0
    changed_files: int = 0
    additions: int = 0
    deletions: int = 0
    quality_score: float | None = None
    risk_count: int = 0
    author_metrics: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "collected"
    source_channel: str | None = None


class JenkinsReleaseRequest(BaseModel):
    product_id: str
    version_id: str
    job_name: str
    build_id: str
    build_number: int | None = None
    environment: str = "prod"
    status: str = "success"
    trigger_actor: str | None = None
    commit_sha: str | None = None
    duration_seconds: int | None = None
    started_at: str | None = None
    deployed_at: str | None = None
    failure_reason: str | None = None
    source_channel: str | None = None


class OnlineLogMetricRequest(BaseModel):
    product_id: str
    module_code: str | None = None
    environment: str = "prod"
    window_start: str
    window_end: str
    request_count: int = 0
    error_count: int = 0
    p95_latency_ms: float | None = None
    p99_latency_ms: float | None = None
    core_event_count: int = 0
    top_errors: list[dict[str, Any]] = Field(default_factory=list)
    anomaly_summary: str | None = None
    status: str = "collected"
    source_channel: str | None = None


class UserFeedbackRequest(BaseModel):
    product_id: str
    module_code: str | None = None
    feature_code: str | None = None
    source_channel: str = "in_app"
    feedback_type: str
    sentiment: str | None = None
    satisfaction_score: int | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    related_requirement_id: str | None = None


class UserFeedbackPatchRequest(BaseModel):
    status: str | None = None
    sentiment: str | None = None
    satisfaction_score: int | None = None
    content: str | None = None
    tags: list[str] | None = None
    triage_note: str | None = None


class UserUsageMetricRequest(BaseModel):
    product_id: str
    module_code: str | None = None
    feature_code: str
    user_segment: str = "all"
    window_start: str
    window_end: str
    active_users: int = 0
    event_count: int = 0
    conversion_count: int = 0
    conversion_rate: float | None = None
    avg_duration_seconds: float | None = None
    bounce_rate: float | None = None
    error_count: int = 0
    source_channel: str | None = None


class CollectorRunRequest(BaseModel):
    collector_type: str
    error_message: str | None = None
    payload_summary: dict[str, Any] = Field(default_factory=dict)
    product_id: str | None = None
    records_imported: int = 0
    source_system: str
    started_at: str | None = None
    status: str = "running"


class CollectorRunPatchRequest(BaseModel):
    error_message: str | None = None
    finished_at: str | None = None
    payload_summary: dict[str, Any] | None = None
    records_imported: int | None = None
    status: str | None = None


class PendingAttributionRequest(BaseModel):
    collector_run_id: str | None = None
    confidence: float | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    raw_subject_id: str | None = None
    source_system: str
    source_type: str
    suggested_module_code: str | None = None
    suggested_product_id: str | None = None
    summary: str


class PendingAttributionResolveRequest(BaseModel):
    resolution_action: str
    resolution_note: str | None = None
    resolved_module_code: str | None = None
    resolved_product_id: str | None = None
    resolved_requirement_id: str | None = None
    resolved_subject_id: str | None = None
    resolved_subject_type: str | None = None


class IterationSuggestionRequest(BaseModel):
    product_id: str
    planning_cycle: str
    version_id: str | None = None
    module_codes: list[str] = Field(default_factory=list)
    include_evidence: bool = True
    constraints: dict[str, Any] = Field(default_factory=dict)


class IterationSuggestionDecisionRequest(BaseModel):
    decision: str
    edited_title: str | None = None
    edited_scope: str | None = None
    comment: str | None = None
    convert_to_requirement: bool = False


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    request.state.trace_id = new_trace_id()
    response = await call_next(request)
    response.headers["X-Trace-Id"] = request.state.trace_id
    return response


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def store(request: Request) -> MemoryStore:
    return request.app.state.store


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail: dict[str, Any]
    if isinstance(exc.detail, dict):
        detail = dict(exc.detail)
    else:
        detail = {"code": "HTTP_ERROR", "message": str(exc.detail)}
    detail["trace_id"] = get_trace_id(request)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "errors": exc.errors(),
                "trace_id": get_trace_id(request),
            }
        },
    )


def _tcp_check(host: str, port: int, timeout: float = 0.15) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "ok"
    except OSError:
        return "error"


def _tcp_endpoint_from_url(url: str, default_host: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(url)
    return parsed.hostname or default_host, parsed.port or default_port


def _model_gateway_health_status(current_store: MemoryStore) -> str:
    default_gateway = _default_model_gateway_config(current_store)
    if (
        default_gateway
        and default_gateway.get("base_url")
        and default_gateway.get("api_key")
    ):
        return "configured"
    return settings.model_gateway_status


def _chat_gateway_health_status(current_store: MemoryStore) -> str:
    return _model_gateway_health_status(current_store)


def _embedding_gateway_health_status(current_store: MemoryStore) -> str:
    default_gateway = _default_model_gateway_config(current_store)
    if default_gateway:
        if _embedding_connection_mode(default_gateway) == "disabled":
            return "disabled"
        try:
            _model_gateway_embedding_runtime_config(default_gateway)
        except ModelGatewayConfigError:
            return "failed"
        return "configured"
    return settings.model_gateway_status


@app.get("/health")
def health(request: Request) -> dict[str, str]:
    postgres_host, postgres_port = _tcp_endpoint_from_url(
        settings.database_url,
        "127.0.0.1",
        5432,
    )
    redis_host, redis_port = _tcp_endpoint_from_url(settings.redis_url, "127.0.0.1", 6379)
    postgres = _tcp_check(postgres_host, postgres_port)
    redis = _tcp_check(redis_host, redis_port)
    status = "ok" if postgres == "ok" and redis == "ok" else "degraded"
    return {
        "status": status,
        "postgres": postgres,
        "redis": redis,
        "model_gateway": _model_gateway_health_status(store(request)),
        "chat_gateway": _chat_gateway_health_status(store(request)),
        "embedding_gateway": _embedding_gateway_health_status(store(request)),
        "data_access_mode": _runtime_data_access_mode(),
        "long_memory": settings.long_memory_status,
        "trace_id": get_trace_id(request),
    }


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "roles": user["roles"],
    }


def _user_can_read_roles(user: dict[str, Any], permission_roles: list[str]) -> bool:
    user_roles = set(user["roles"])
    if "admin" in user_roles:
        return True
    return bool(user_roles.intersection(permission_roles))


def _require_roles(user: dict[str, Any], allowed_roles: set[str]) -> None:
    user_roles = set(user["roles"])
    if "admin" in user_roles or user_roles.intersection(allowed_roles):
        return
    raise api_error(403, "FORBIDDEN", "Role permission denied")


def _task_allowed_roles(task: dict[str, Any]) -> set[str]:
    if task["task_type"] == "code_review":
        return {"reviewer", "rd_owner"}
    return {"product_owner", "rd_owner"}


def _can_read_task(user: dict[str, Any], task: dict[str, Any]) -> bool:
    user_roles = set(user["roles"])
    return "admin" in user_roles or bool(user_roles.intersection(_task_allowed_roles(task)))


def _task_read_scope(user: dict[str, Any]) -> str:
    user_roles = set(user["roles"])
    if "admin" in user_roles or "rd_owner" in user_roles:
        return "all"
    if "product_owner" in user_roles and "reviewer" in user_roles:
        return "all"
    if "product_owner" in user_roles:
        return "non_code_review"
    if "reviewer" in user_roles:
        return "code_review"
    return "none"


def _require_task_read_role(user: dict[str, Any], task: dict[str, Any]) -> None:
    _require_roles(user, _task_allowed_roles(task))


def _require_review_decision_role(user: dict[str, Any], task: dict[str, Any]) -> None:
    _require_roles(user, _task_allowed_roles(task))


def _raise_gitlab_context_mismatch(message: str) -> None:
    raise api_error(400, "GITLAB_CONTEXT_MISMATCH", message)


def _raise_task_context_mismatch(message: str) -> None:
    raise api_error(400, "TASK_CONTEXT_MISMATCH", message)


def _canonical_requirement_status(status: str | None) -> str:
    if status is None:
        return "draft"
    return LEGACY_REQUIREMENT_STATUS_ALIASES.get(status, status)


def _set_requirement_status(requirement: dict[str, Any], status: str) -> None:
    _ensure_enum(status, REQUIREMENT_STATUSES, "requirement status")
    requirement["status"] = status
    requirement["updated_at"] = datetime.now(UTC).isoformat()


def _validate_requirement_version(
    current_store: MemoryStore,
    *,
    product_id: str,
    version_id: str | None,
) -> dict[str, Any] | None:
    if version_id is None:
        return None
    version = current_store.product_versions.get(version_id)
    if version is None or version["product_id"] != product_id:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if version["status"] == "archived":
        raise api_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")
    if version["status"] not in REQUIREMENT_SCHEDULABLE_VERSION_STATUSES:
        raise api_error(
            400,
            "PRODUCT_VERSION_NOT_SCHEDULABLE",
            "Only planning or active versions can be used for requirement scheduling",
        )
    return version


def _requirement_advance_item(
    requirement: dict[str, Any],
    *,
    from_status: str,
    to_status: str,
) -> dict[str, str]:
    return {
        "from_status": from_status,
        "id": requirement["id"],
        "title": requirement["title"],
        "to_status": to_status,
    }


def _requirement_block_item(
    requirement: dict[str, Any],
    *,
    block_reason: str,
    status: str,
) -> dict[str, str]:
    return {
        "block_reason": block_reason,
        "id": requirement["id"],
        "status": status,
        "title": requirement["title"],
    }


def _requirements_for_version(
    current_store: MemoryStore,
    version_id: str,
) -> list[dict[str, Any]]:
    requirements = [
        requirement
        for requirement in current_store.requirements.values()
        if requirement.get("version_id") == version_id
    ]
    requirements.sort(key=lambda item: (item.get("created_at") or "", item.get("id") or ""))
    return requirements


def _build_version_advance_impact(
    current_store: MemoryStore,
    *,
    target_status: str,
    version_id: str,
) -> dict[str, list[dict[str, str]]]:
    auto_advance = VERSION_REQUIREMENT_AUTO_ADVANCE.get(target_status, {})
    allowed_unchanged = VERSION_REQUIREMENT_ALLOWED_UNCHANGED.get(target_status, set())
    block_reason = VERSION_REQUIREMENT_BLOCK_REASONS.get(
        target_status,
        "需求状态不满足版本推进条件",
    )
    updated: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    unchanged: list[dict[str, str]] = []
    for requirement in _requirements_for_version(current_store, version_id):
        status = _canonical_requirement_status(requirement.get("status"))
        next_status = auto_advance.get(status)
        if next_status is not None:
            updated.append(
                _requirement_advance_item(
                    requirement,
                    from_status=status,
                    to_status=next_status,
                )
            )
            continue
        if status in allowed_unchanged:
            unchanged.append(
                {
                    "id": requirement["id"],
                    "status": status,
                    "title": requirement["title"],
                }
            )
            continue
        blocked.append(
            _requirement_block_item(
                requirement,
                block_reason=block_reason,
                status=status,
            )
        )
    return {
        "blocked_requirements": blocked,
        "unchanged_requirements": unchanged,
        "updated_requirements": updated,
    }


def _validate_version_status_transition(from_status: str, target_status: str) -> None:
    _ensure_enum(target_status, VERSION_STATUSES, "product version target status")
    if target_status == "archived":
        if from_status != "released":
            raise api_error(
                409,
                "PRODUCT_VERSION_STATUS_INVALID",
                "Only released versions can be archived",
            )
        return
    if target_status not in VERSION_MAIN_STATUSES:
        raise api_error(
            400,
            "PRODUCT_VERSION_STATUS_INVALID",
            "Target status is not a version delivery stage",
        )
    if target_status == from_status:
        raise api_error(
            400,
            "PRODUCT_VERSION_STATUS_UNCHANGED",
            "Target status must be different from current status",
        )
    if target_status not in VERSION_STATUS_TRANSITIONS.get(from_status, set()):
        raise api_error(
            409,
            "PRODUCT_VERSION_STATUS_INVALID",
            "Version status must be advanced through the configured delivery flow",
        )


def _advance_requirement_after_task_created(
    current_store: MemoryStore,
    task: dict[str, Any],
) -> None:
    requirement = current_store.requirements.get(task.get("requirement_id"))
    if requirement is None:
        return
    next_status = REQUIREMENT_STATUS_AFTER_TASK_CREATED.get(task["task_type"])
    if next_status:
        _set_requirement_status(requirement, next_status)


def _advance_requirement_after_task_completed(
    current_store: MemoryStore,
    task: dict[str, Any],
) -> None:
    requirement = current_store.requirements.get(task.get("requirement_id"))
    if requirement is None:
        return
    next_status = REQUIREMENT_STATUS_AFTER_TASK_COMPLETED.get(task["task_type"])
    if next_status and requirement.get("status") not in {"accepted", "closed", "cancelled"}:
        _set_requirement_status(requirement, next_status)


def _ensure_task_matches_requirement(
    task: dict[str, Any],
    requirement: dict[str, Any],
    *,
    source_label: str,
) -> None:
    if task["requirement_id"] != requirement["id"]:
        _raise_task_context_mismatch(f"{source_label} task must belong to the same requirement")
    if task["product_id"] != requirement["product_id"]:
        _raise_task_context_mismatch(f"{source_label} task must belong to the same product")
    if task["version_id"] != requirement["version_id"]:
        _raise_task_context_mismatch(f"{source_label} task must belong to the same version")


def _require_bug_write_role(user: dict[str, Any]) -> None:
    _require_roles(user, {"product_owner", "rd_owner"})


def _validate_bug_enums(
    *,
    source: str | None = None,
    severity: str | None = None,
    status: str | None = None,
) -> None:
    if source is not None and source not in BUG_SOURCES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported bug source")
    if severity is not None and severity not in BUG_SEVERITIES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported bug severity")
    if status is not None and status not in BUG_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported bug status")


def _validate_bug_context(
    current_store: MemoryStore,
    *,
    product_id: str,
    version_id: str | None = None,
    module_code: str | None = None,
    requirement_id: str | None = None,
    related_task_id: str | None = None,
    duplicate_of_bug_id: str | None = None,
    bug_id: str | None = None,
) -> None:
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if version_id is not None:
        version = current_store.product_versions.get(version_id)
        if version is None or version["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "Product version not found")
    if module_code is not None and not any(
        module["product_id"] == product_id and module["code"] == module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")
    if requirement_id is not None:
        requirement = current_store.requirements.get(requirement_id)
        if requirement is None or requirement["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "Requirement not found")
    if related_task_id is not None:
        task = current_store.ai_tasks.get(related_task_id)
        if task is None or task["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "AI task not found")
    if duplicate_of_bug_id is not None:
        if duplicate_of_bug_id == bug_id:
            raise api_error(400, "VALIDATION_ERROR", "Bug cannot duplicate itself")
        duplicate = current_store.bugs.get(duplicate_of_bug_id)
        if duplicate is None or duplicate["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "Duplicate bug not found")


def _initial_bug_status(payload: BugRequest) -> str:
    if payload.duplicate_of_bug_id:
        return "closed"
    if payload.source == "ai_auto_test" and not payload.reproduce_steps:
        return "needs_info"
    return "open"


def _ensure_bug_status_transition(current_status: str, next_status: str) -> None:
    if current_status == next_status:
        return
    allowed = BUG_STATUS_TRANSITIONS.get(current_status, set())
    if next_status not in allowed:
        raise api_error(409, "BUG_STATE_INVALID", "Bug cannot move to requested status")


def _require_user_feedback_triage_role(user: dict[str, Any]) -> None:
    _require_roles(user, {"product_owner", "rd_owner"})


def _parse_metric_date(value: str, field_name: str = "metric_date") -> str:
    text = _ensure_non_blank(value, field_name)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"{field_name} must be YYYY-MM-DD") from exc


def _validate_gitlab_metric_payload(payload: GitlabDailyCodeMetricRequest) -> str:
    _ensure_enum(payload.status, GITLAB_DAILY_METRIC_STATUSES, "status")
    for field_name in (
        "active_author_count",
        "additions",
        "changed_files",
        "commit_count",
        "deletions",
        "merge_request_count",
        "risk_count",
    ):
        if getattr(payload, field_name) < 0:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"{field_name} must be greater than or equal to 0",
            )
    if payload.quality_score is not None and (
        payload.quality_score < 0 or payload.quality_score > 100
    ):
        raise api_error(400, "VALIDATION_ERROR", "quality_score must be between 0 and 100")
    return _parse_metric_date(payload.metric_date)


def _validate_gitlab_metric_context(
    current_store: MemoryStore,
    *,
    product_id: str,
    repository_id: str,
) -> None:
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None or repository["product_id"] != product_id:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    if repository.get("status") != "active":
        raise api_error(400, "VALIDATION_ERROR", "Inactive Git repository cannot be used")
    if repository.get("git_provider") != "gitlab":
        raise api_error(400, "VALIDATION_ERROR", "Only GitLab repositories are supported")


def _validate_git_repository_binding(
    provider: str,
    *,
    project_id: str | None,
    project_path: str | None,
    remote_url: str | None,
) -> None:
    _ensure_enum(provider, GIT_REPO_PROVIDERS, "git provider")
    if provider == "gitlab" and not project_id and not project_path:
        raise api_error(400, "VALIDATION_ERROR", "GitLab project_id or project_path is required")
    if provider == "github" and not project_path and not remote_url:
        raise api_error(400, "VALIDATION_ERROR", "GitHub project_path or remote_url is required")


def _parse_optional_release_time(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _parse_usage_window(value, field_name)


def _validate_jenkins_release_payload(
    payload: JenkinsReleaseRequest,
) -> tuple[str | None, str | None]:
    _ensure_non_blank(payload.job_name, "job_name")
    _ensure_non_blank(payload.build_id, "build_id")
    _ensure_non_blank(payload.environment, "environment")
    _ensure_enum(payload.status, JENKINS_RELEASE_STATUSES, "status")
    if payload.build_number is not None and payload.build_number < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "build_number must be greater than or equal to 0",
        )
    if payload.duration_seconds is not None and payload.duration_seconds < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "duration_seconds must be greater than or equal to 0",
        )
    started_at = _parse_optional_release_time(payload.started_at, "started_at")
    deployed_at = _parse_optional_release_time(payload.deployed_at, "deployed_at")
    if started_at is not None and deployed_at is not None and deployed_at < started_at:
        raise api_error(400, "VALIDATION_ERROR", "deployed_at must be after started_at")
    return started_at, deployed_at


def _validate_jenkins_release_context(
    current_store: MemoryStore,
    *,
    product_id: str,
    version_id: str,
) -> None:
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    version = current_store.product_versions.get(version_id)
    if version is None or version["product_id"] != product_id:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if version["status"] == "archived":
        raise api_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")


def _validate_online_log_metric_context(
    current_store: MemoryStore,
    *,
    product_id: str,
    module_code: str | None = None,
) -> None:
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    if module_code is not None and not any(
        module["product_id"] == product_id
        and module["code"] == module_code
        and module.get("status", "active") == "active"
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")


def _validate_online_log_metric_payload(
    payload: OnlineLogMetricRequest,
) -> tuple[str, str, float]:
    _ensure_non_blank(payload.environment, "environment")
    _ensure_enum(payload.status, ONLINE_LOG_METRIC_STATUSES, "status")
    for field_name in ("request_count", "error_count", "core_event_count"):
        if getattr(payload, field_name) < 0:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"{field_name} must be greater than or equal to 0",
            )
    for field_name in ("p95_latency_ms", "p99_latency_ms"):
        value = getattr(payload, field_name)
        if value is not None and value < 0:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"{field_name} must be greater than or equal to 0",
            )
    if payload.error_count > payload.request_count:
        raise api_error(400, "VALIDATION_ERROR", "error_count cannot exceed request_count")
    window_start = _parse_usage_window(payload.window_start, "window_start")
    window_end = _parse_usage_window(payload.window_end, "window_end")
    if window_end <= window_start:
        raise api_error(400, "VALIDATION_ERROR", "window_end must be after window_start")
    error_rate = payload.error_count / payload.request_count if payload.request_count else 0.0
    return window_start, window_end, error_rate


def _validate_user_feedback_enums(
    *,
    feedback_type: str | None = None,
    sentiment: str | None = None,
    status: str | None = None,
) -> None:
    _ensure_enum(feedback_type, USER_FEEDBACK_TYPES, "feedback_type")
    _ensure_enum(sentiment, USER_FEEDBACK_SENTIMENTS, "sentiment")
    _ensure_enum(status, USER_FEEDBACK_STATUSES, "status")


def _validate_satisfaction_score(score: int | None) -> None:
    if score is not None and (score < 1 or score > 5):
        raise api_error(400, "VALIDATION_ERROR", "satisfaction_score must be between 1 and 5")


def _parse_usage_window(value: str, field_name: str) -> str:
    text = _ensure_non_blank(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"{field_name} must be an ISO datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def _validate_usage_metric_payload(payload: UserUsageMetricRequest) -> tuple[str, str]:
    for field_name in ("active_users", "event_count", "conversion_count", "error_count"):
        if getattr(payload, field_name) < 0:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"{field_name} must be greater than or equal to 0",
            )
    for field_name in ("conversion_rate", "bounce_rate"):
        value = getattr(payload, field_name)
        if value is not None and (value < 0 or value > 1):
            raise api_error(400, "VALIDATION_ERROR", f"{field_name} must be between 0 and 1")
    if payload.avg_duration_seconds is not None and payload.avg_duration_seconds < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "avg_duration_seconds must be greater than or equal to 0",
        )
    window_start = _parse_usage_window(payload.window_start, "window_start")
    window_end = _parse_usage_window(payload.window_end, "window_end")
    if window_end <= window_start:
        raise api_error(400, "VALIDATION_ERROR", "window_end must be after window_start")
    return window_start, window_end


def _validate_user_feedback_context(
    current_store: MemoryStore,
    *,
    product_id: str,
    module_code: str | None = None,
    related_requirement_id: str | None = None,
) -> None:
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if module_code is not None and not any(
        module["product_id"] == product_id and module["code"] == module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")
    if related_requirement_id is not None:
        requirement = current_store.requirements.get(related_requirement_id)
        if requirement is None or requirement["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "Requirement not found")


def _validate_usage_metric_context(
    current_store: MemoryStore,
    *,
    product_id: str,
    module_code: str | None = None,
) -> None:
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    if module_code is not None and not any(
        module["product_id"] == product_id and module["code"] == module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")


def _require_collector_run_write_role(user: dict[str, Any]) -> None:
    _require_roles(user, {"product_owner", "rd_owner"})


def _validate_collector_product_context(
    current_store: MemoryStore,
    *,
    product_id: str | None,
) -> None:
    if product_id is None:
        return
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")


def _parse_optional_collector_time(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _parse_usage_window(value, field_name)


def _validate_collector_run_request(
    current_store: MemoryStore,
    payload: CollectorRunRequest,
) -> tuple[str, str | None]:
    _ensure_enum(payload.collector_type, COLLECTOR_TYPES, "collector_type")
    _ensure_enum(payload.status, COLLECTOR_RUN_STATUSES, "status")
    source_system = _ensure_non_blank(payload.source_system, "source_system")
    if payload.records_imported < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "records_imported must be greater than or equal to 0",
        )
    _validate_collector_product_context(current_store, product_id=payload.product_id)
    if payload.status == "failed":
        _ensure_non_blank(payload.error_message, "error_message")
    started_at = _parse_optional_collector_time(payload.started_at, "started_at")
    return source_system, started_at


def _collector_run_patch_updates(
    run: dict[str, Any],
    payload: CollectorRunPatchRequest,
) -> dict[str, Any]:
    requested = _payload_updates(payload)
    if requested.get("status") is None:
        requested.pop("status", None)
    if "payload_summary" in requested and requested["payload_summary"] is None:
        raise api_error(400, "VALIDATION_ERROR", "payload_summary must be an object")
    if "records_imported" in requested and requested["records_imported"] is None:
        raise api_error(400, "VALIDATION_ERROR", "records_imported is required")
    status = requested.get("status", run["status"])
    _ensure_enum(status, COLLECTOR_RUN_STATUSES, "status")
    if run["status"] in COLLECTOR_TERMINAL_STATUSES and status != run["status"]:
        raise api_error(
            409,
            "COLLECTOR_RUN_STATE_INVALID",
            "Terminal collector run cannot change status",
        )
    if requested.get("records_imported") is not None and requested["records_imported"] < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "records_imported must be greater than or equal to 0",
        )

    finished_at = _parse_optional_collector_time(requested.get("finished_at"), "finished_at")
    if status == "running" and finished_at is not None:
        raise api_error(400, "VALIDATION_ERROR", "running collector run cannot have finished_at")

    error_message = requested.get("error_message", run.get("error_message"))
    if status == "failed":
        _ensure_non_blank(error_message, "error_message")

    updates = {}
    for key in ("error_message", "payload_summary", "records_imported", "status"):
        if key in requested:
            updates[key] = requested[key]
    if finished_at is not None:
        updates["finished_at"] = finished_at
    elif status in COLLECTOR_TERMINAL_STATUSES and not run.get("finished_at"):
        updates["finished_at"] = datetime.now(UTC).isoformat()
    if status == "running":
        updates["finished_at"] = None
    return updates


def _require_pending_attribution_write_role(user: dict[str, Any]) -> None:
    _require_roles(user, {"product_owner", "rd_owner"})


def _validate_pending_attribution_suggested_context(
    current_store: MemoryStore,
    *,
    suggested_product_id: str | None,
    suggested_module_code: str | None,
) -> None:
    if suggested_product_id is None:
        return
    product = current_store.products.get(suggested_product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Suggested product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive suggested product cannot be used")
    if suggested_module_code is not None and not any(
        module["product_id"] == suggested_product_id and module["code"] == suggested_module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Suggested product module not found")


def _validate_pending_attribution_create_request(
    current_store: MemoryStore,
    payload: PendingAttributionRequest,
) -> tuple[str, str, str | None, str | None]:
    _ensure_enum(payload.source_type, PENDING_ATTRIBUTION_SOURCE_TYPES, "source_type")
    source_system = _ensure_non_blank(payload.source_system, "source_system")
    summary = _ensure_non_blank(payload.summary, "summary")
    raw_subject_id = payload.raw_subject_id.strip() if payload.raw_subject_id else None
    suggested_module_code = (
        payload.suggested_module_code.strip() if payload.suggested_module_code else None
    )
    if payload.confidence is not None and (
        payload.confidence < 0 or payload.confidence > 1
    ):
        raise api_error(400, "VALIDATION_ERROR", "confidence must be between 0 and 1")
    if payload.collector_run_id is not None and payload.collector_run_id not in (
        current_store.collector_runs
    ):
        raise api_error(404, "NOT_FOUND", "Collector run not found")
    _validate_pending_attribution_suggested_context(
        current_store,
        suggested_product_id=payload.suggested_product_id,
        suggested_module_code=suggested_module_code,
    )
    return source_system, summary, raw_subject_id, suggested_module_code


def _validate_pending_attribution_resolve_request(
    current_store: MemoryStore,
    item: dict[str, Any],
    payload: PendingAttributionResolveRequest,
) -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
    if item["status"] != "pending":
        raise api_error(
            409,
            "PENDING_ATTRIBUTION_STATE_INVALID",
            "Pending attribution item is already terminal",
        )
    _ensure_enum(
        payload.resolution_action,
        PENDING_ATTRIBUTION_RESOLUTION_ACTIONS,
        "resolution_action",
    )
    resolution_note = (
        payload.resolution_note.strip() if payload.resolution_note else None
    )
    resolved_module_code = (
        payload.resolved_module_code.strip() if payload.resolved_module_code else None
    )
    resolved_subject_type = (
        payload.resolved_subject_type.strip() if payload.resolved_subject_type else None
    )
    resolved_subject_id = (
        payload.resolved_subject_id.strip() if payload.resolved_subject_id else None
    )
    if payload.resolution_action == "ignore_as_noise":
        if any(
            (
                payload.resolved_product_id,
                resolved_module_code,
                payload.resolved_requirement_id,
                resolved_subject_type,
                resolved_subject_id,
            )
        ):
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "Ignored attribution item cannot include resolved context",
            )
        return resolution_note, None, None, None, None, None
    if payload.resolved_product_id is None:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "resolved_product_id is required for link_existing_context",
        )
    product = current_store.products.get(payload.resolved_product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Resolved product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive resolved product cannot be used")
    if resolved_module_code is not None and not any(
        module["product_id"] == payload.resolved_product_id
        and module["code"] == resolved_module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Resolved product module not found")
    if payload.resolved_requirement_id is not None:
        requirement = current_store.requirements.get(payload.resolved_requirement_id)
        if requirement is None or requirement["product_id"] != payload.resolved_product_id:
            raise api_error(404, "NOT_FOUND", "Resolved requirement not found")
    return (
        resolution_note,
        payload.resolved_product_id,
        resolved_module_code,
        payload.resolved_requirement_id,
        resolved_subject_type,
        resolved_subject_id,
    )


def _normalized_tags(tags: list[str]) -> list[str]:
    normalized = []
    for tag in tags:
        value = tag.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _require_iteration_planning_role(user: dict[str, Any]) -> None:
    _require_roles(user, {"product_owner", "rd_owner"})


def _validate_iteration_enums(
    *,
    decision: str | None = None,
    status: str | None = None,
) -> None:
    _ensure_enum(decision, ITERATION_DECISIONS, "decision")
    _ensure_enum(status, ITERATION_SUGGESTION_STATUSES, "status")


def _normalized_module_codes(module_codes: list[str]) -> list[str]:
    normalized = []
    for module_code in module_codes:
        value = module_code.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _validate_iteration_context(
    current_store: MemoryStore,
    *,
    product_id: str,
    version_id: str | None = None,
    module_codes: list[str] | None = None,
) -> None:
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    if version_id is not None:
        version = current_store.product_versions.get(version_id)
        if version is None or version["product_id"] != product_id:
            raise api_error(404, "NOT_FOUND", "Product version not found")
        if version["status"] == "archived":
            raise api_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")
    for module_code in module_codes or []:
        if not any(
            module["product_id"] == product_id and module["code"] == module_code
            for module in current_store.product_modules.values()
        ):
            raise api_error(404, "NOT_FOUND", "Product module not found")


def _iteration_evidence_matches_modules(
    item: dict[str, Any],
    module_codes: list[str],
) -> bool:
    return not module_codes or item.get("module_code") in module_codes


def _collect_iteration_evidence(
    current_store: MemoryStore,
    *,
    product_id: str,
    module_codes: list[str],
    include_evidence: bool,
) -> list[dict[str, Any]]:
    if not include_evidence:
        return []
    feedback_evidence = [
        {
            "subject_id": feedback["id"],
            "subject_type": "user_feedback",
            "summary": feedback["content"],
        }
        for feedback in sorted(
            current_store.user_feedback.values(),
            key=lambda item: (item.get("created_at") or "", item["id"]),
        )
        if feedback["product_id"] == product_id
        and feedback.get("status") not in {"archived", "resolved"}
        and _iteration_evidence_matches_modules(feedback, module_codes)
    ]
    bug_evidence = [
        {
            "subject_id": bug["id"],
            "subject_type": "bug",
            "summary": bug["title"],
        }
        for bug in sorted(
            current_store.bugs.values(),
            key=lambda item: (item.get("created_at") or "", item["id"]),
        )
        if bug["product_id"] == product_id
        and bug.get("status") not in {"closed", "verified"}
        and _iteration_evidence_matches_modules(bug, module_codes)
    ]
    return (feedback_evidence + bug_evidence)[:12]


def _build_iteration_suggestion(
    current_store: MemoryStore,
    *,
    evidence: list[dict[str, Any]],
    module_codes: list[str],
    payload: IterationSuggestionRequest,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    product_name = current_store.products[payload.product_id]["name"]
    module_scope = "、".join(module_codes) if module_codes else product_name
    evidence_types = {item["subject_type"] for item in evidence}
    if len(evidence) >= 4:
        confidence_level = "high"
        priority_score = 88
    elif len(evidence) >= 2:
        confidence_level = "medium"
        priority_score = 76
    else:
        confidence_level = "low"
        priority_score = 52
    risk_signals = []
    if "user_feedback" in evidence_types:
        risk_signals.append("user_feedback_signal")
    if "bug" in evidence_types:
        risk_signals.append("bug_quality_signal")
    return {
        "business_value": f"提升 {module_scope} 的用户体验和交付质量。",
        "confidence_level": confidence_level,
        "created_at": now,
        "created_by": user["id"],
        "dependencies": ["产品负责人确认范围", "研发负责人评估投入"],
        "estimated_effort": "medium",
        "evidence": evidence,
        "evidence_insufficient": confidence_level == "low",
        "id": current_store.new_id("suggestion"),
        "module_codes": module_codes,
        "planning_cycle": _ensure_non_blank(payload.planning_cycle, "planning_cycle"),
        "priority": "P1",
        "priority_score": priority_score,
        "product_id": payload.product_id,
        "recommendation_reason": (
            f"{module_scope} 已出现 {len(evidence)} 条真实反馈或缺陷证据，"
            "建议进入下一阶段迭代评估。"
        ),
        "risk_signals": risk_signals,
        "status": "suggested",
        "title": f"优化{module_scope}反馈与缺陷集中问题",
        "updated_at": now,
        "version_id": payload.version_id,
    }


def _create_iteration_requirement(
    current_store: MemoryStore,
    *,
    payload: IterationSuggestionDecisionRequest,
    suggestion: dict[str, Any],
    user: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    version_id = suggestion.get("version_id")
    if not version_id:
        raise api_error(
            400,
            "ITERATION_PLAN_VERSION_REQUIRED",
            "version_id is required to convert suggestion to requirement",
        )
    title = _ensure_non_blank(
        payload.edited_title or suggestion["title"],
        "edited_title",
    )
    scope = payload.edited_scope or suggestion["recommendation_reason"]
    now = datetime.now(UTC).isoformat()
    requirement_id = current_store.new_id("requirement")
    requirement = {
        "content": "\n".join(
            [
                scope,
                "",
                f"业务价值：{suggestion['business_value']}",
                f"推荐理由：{suggestion['recommendation_reason']}",
            ]
        ),
        "created_at": now,
        "created_by": user["id"],
        "id": requirement_id,
        "module_code": suggestion["module_codes"][0] if suggestion["module_codes"] else None,
        "priority": suggestion["priority"],
        "product_id": suggestion["product_id"],
        "status": "submitted",
        "task_ids": [],
        "title": title,
        "version_id": version_id,
    }
    if not _uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = _record_audit_event(
        current_store,
        event_type="requirement.created",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
        payload={"source": "iteration_plan_suggestion", "suggestion_id": suggestion["id"]},
    )
    return requirement, audit_event


def _payload_updates(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


def _ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def _ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is not None and value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def _ensure_roles(roles: list[str]) -> None:
    if not roles:
        raise api_error(400, "VALIDATION_ERROR", "roles is required")
    if len(set(roles)) != len(roles):
        raise api_error(400, "VALIDATION_ERROR", "roles must be unique")
    invalid_roles = sorted(set(roles) - USER_ROLES)
    if invalid_roles:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported roles: {', '.join(invalid_roles)}")


def _ensure_unique_value(
    collection: dict[str, dict[str, Any]],
    *,
    field: str,
    value: str,
    conflict_code: str,
    message: str,
    exclude_id: str | None = None,
    scope: dict[str, Any] | None = None,
) -> None:
    for item_id, item in collection.items():
        if exclude_id is not None and item_id == exclude_id:
            continue
        if scope and any(
            item.get(scope_key) != scope_value for scope_key, scope_value in scope.items()
        ):
            continue
        if item.get(field) == value:
            raise api_error(409, conflict_code, message)


def _list_payload(
    items: list[dict[str, Any]],
    *,
    trace_id: str,
    active_only: bool = False,
) -> dict[str, Any]:
    visible_items = [item for item in items if not active_only or item.get("status") == "active"]
    return envelope({"items": visible_items, "total": len(visible_items)}, trace_id)


def _normalize_list_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _list_text_matches(item: dict[str, Any], keyword: str | None, fields: tuple[str, ...]) -> bool:
    normalized_keyword = _normalize_list_text(keyword)
    if not normalized_keyword:
        return True
    return normalized_keyword in " ".join(_normalize_list_text(item.get(field)) for field in fields)


def _first_list_value(item: dict[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = item.get(field)
        if value is not None and value != "":
            return value
    return None


def _list_sort_value(value: Any) -> tuple[int, float | str]:
    if value is None or value == "":
        return (0, "")
    if isinstance(value, bool):
        return (1, float(int(value)))
    if isinstance(value, (int, float)):
        return (1, float(value))
    return (2, _normalize_list_text(value))


def _sort_list_items(
    items: list[dict[str, Any]],
    *,
    allowed_fields: set[str],
    default_sort_by: str,
    sort_by: str | None,
    sort_order: str,
) -> list[dict[str, Any]]:
    _ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or default_sort_by
    if resolved_sort_by not in allowed_fields:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    return sorted(
        items,
        key=lambda item: _list_sort_value(item.get(resolved_sort_by)),
        reverse=sort_order == "desc",
    )


def _paginated_list_payload(
    items: list[dict[str, Any]],
    *,
    page: int | None,
    page_size: int | None,
    trace_id: str,
) -> dict[str, Any]:
    if page is None and page_size is None:
        return envelope({"items": items, "total": len(items)}, trace_id)
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    total = len(items)
    start = (resolved_page - 1) * resolved_page_size
    end = start + resolved_page_size
    return envelope(
        {
            "items": items[start:end],
            "page": resolved_page,
            "page_size": resolved_page_size,
            "total": total,
        },
        trace_id,
    )


def _list_datetime_timestamp(value: Any) -> float:
    if not value:
        return 0.0
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def _product_current_version_for_list(
    current_store: MemoryStore,
    product_id: str,
) -> dict[str, Any] | None:
    status_order = {"active": 0, "testing": 1, "released": 2, "planning": 3, "archived": 4}
    versions = [
        version
        for version in current_store.product_versions.values()
        if version.get("product_id") == product_id
    ]
    if not versions:
        return None
    return sorted(
        versions,
        key=lambda version: (
            status_order.get(str(version.get("status") or ""), 9),
            -_list_datetime_timestamp(version.get("updated_at") or version.get("created_at")),
            _normalize_list_text(version.get("code")),
        ),
    )[0]


def _product_list_projection(
    item: dict[str, Any],
    current_store: MemoryStore,
) -> dict[str, Any]:
    product_id = str(item.get("id") or "")
    current_version = (
        None
        if item.get("current_version_name") and item.get("current_version_code")
        else _product_current_version_for_list(current_store, product_id)
    )
    module_count = item.get("module_count")
    if module_count is None:
        module_count = sum(
            1
            for module in current_store.product_modules.values()
            if module.get("product_id") == product_id and module.get("status") == "active"
        )
    return {
        **item,
        "current_version_code": item.get("current_version_code")
        or (current_version or {}).get("code"),
        "current_version_name": item.get("current_version_name")
        or (current_version or {}).get("name"),
        "module_count": module_count,
    }


class _RepositoryRequestContext:
    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self.brain_apps: dict[str, dict[str, Any]] = default_brain_apps()
        self.products: dict[str, dict[str, Any]] = {}
        self.product_versions: dict[str, dict[str, Any]] = {}
        self.product_modules: dict[str, dict[str, Any]] = {}
        self.product_git_repositories: dict[str, dict[str, Any]] = {}
        self.related_systems: dict[str, dict[str, Any]] = {}
        self.model_gateway_configs: dict[str, dict[str, Any]] = {}
        self.model_gateway_logs: list[dict[str, Any]] = []
        self.assistant_conversations: dict[str, dict[str, Any]] = {}
        self.assistant_messages: dict[str, dict[str, Any]] = {}
        self.gitlab_mr_snapshots: dict[str, dict[str, Any]] = {}
        self.code_review_reports: dict[str, dict[str, Any]] = {}
        self.knowledge_documents: dict[str, dict[str, Any]] = {}
        self.knowledge_chunks: dict[str, dict[str, Any]] = {}
        self.knowledge_deposits: dict[str, dict[str, Any]] = {}
        self.mock_writebacks: dict[str, dict[str, Any]] = {}
        self.bugs: dict[str, dict[str, Any]] = {}
        self.gitlab_daily_code_metrics: dict[str, dict[str, Any]] = {}
        self.jenkins_release_records: dict[str, dict[str, Any]] = {}
        self.online_log_metrics: dict[str, dict[str, Any]] = {}
        self.user_usage_metrics: dict[str, dict[str, Any]] = {}
        self.user_feedback: dict[str, dict[str, Any]] = {}
        self.iteration_plan_suggestions: dict[str, dict[str, Any]] = {}
        self.iteration_plan_decisions: dict[str, dict[str, Any]] = {}
        self.lifecycle_context_edges: dict[str, dict[str, Any]] = {}
        self.lifecycle_risk_signals: dict[str, dict[str, Any]] = {}
        self.dashboard_metric_snapshots: dict[str, dict[str, Any]] = {}
        self.collector_runs: dict[str, dict[str, Any]] = {}
        self.pending_attribution_items: dict[str, dict[str, Any]] = {}
        self.requirements: dict[str, dict[str, Any]] = {}
        self.ai_tasks: dict[str, dict[str, Any]] = {}
        self.graph_runs: dict[str, dict[str, Any]] = {}
        self.graph_checkpoints: dict[str, dict[str, Any]] = {}
        self.human_reviews: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        next_id = getattr(self.repository, "next_id", None)
        if not callable(next_id):
            next_value = self.counters.get(prefix, 0) + 1
            self.counters[prefix] = next_value
            return f"{prefix}_{next_value:03d}"
        allocated_id = next_id(prefix)
        suffix = allocated_id.removeprefix(f"{prefix}_")
        if suffix.isdigit():
            self.counters[prefix] = max(self.counters.get(prefix, 0), int(suffix))
        return allocated_id

    def snapshot(self, value: Any) -> Any:
        return deepcopy(value)

    def audit(
        self,
        *,
        event_type: str,
        actor_id: str,
        ai_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": self.new_id("audit"),
            "event_type": event_type,
            "actor_id": actor_id,
            "ai_task_id": ai_task_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "payload": payload or {},
            "sequence": len(self.audit_events) + 1,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.audit_events.append(event)
        return event


def _postgres_snapshot_repository(current_store: MemoryStore) -> PostgresSnapshotRepository | None:
    repository = getattr(current_store, "repository", None)
    if isinstance(repository, PostgresSnapshotRepository):
        return repository
    return None


def _runtime_repository(current_store: MemoryStore) -> Any | None:
    return getattr(current_store, "repository", None)


def _uses_repository_context(current_store: Any) -> bool:
    return _runtime_repository(current_store) is not None


def _record_audit_event(
    current_store: Any,
    *,
    event_type: str,
    actor_id: str,
    ai_task_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not _uses_repository_context(current_store):
        return current_store.audit(
            event_type=event_type,
            actor_id=actor_id,
            ai_task_id=ai_task_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
        )
    return {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": ai_task_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": len(getattr(current_store, "audit_events", [])) + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }


def _brain_app_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    if getattr(repository, "load_brain_apps", None) is not None:
        return repository
    return None


def _brain_app_rows_from_repository(repository: Any) -> dict[str, dict[str, Any]]:
    payload = repository.load_brain_apps() or {}
    return {
        str(item_id): dict(item)
        for item_id, item in payload.get("brain_apps", {}).items()
    }


def _product_config_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = [
        "get_product",
        "list_product_git_repositories",
        "list_product_modules",
        "list_product_versions",
        "list_products",
        "list_related_systems",
    ]
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _payload_collection(payload: dict[str, Any] | None, key: str) -> dict[str, dict[str, Any]]:
    return {str(item_id): dict(item) for item_id, item in (payload or {}).get(key, {}).items()}


def _product_config_source_store(repository: Any) -> Any:
    source_store = _RepositoryRequestContext(repository)
    products = repository.list_products(active_only=False)
    source_store.products = {
        str(product["id"]): dict(product)
        for product in products
        if product.get("id") is not None
    }
    for product in products:
        product_id = str(product["id"])
        for version in repository.list_product_versions(product_id, active_only=False):
            source_store.product_versions[str(version["id"])] = dict(version)
        for module in repository.list_product_modules(product_id, active_only=False):
            source_store.product_modules[str(module["id"])] = dict(module)
        for git_repository in repository.list_product_git_repositories(
            product_id,
            active_only=False,
        ):
            source_store.product_git_repositories[str(git_repository["id"])] = dict(
                git_repository
            )
    source_store.related_systems = {
        str(system["id"]): dict(system)
        for system in repository.list_related_systems(active_only=False)
        if system.get("id") is not None
    }
    load_requirements = getattr(repository, "load_requirements", None)
    if callable(load_requirements):
        source_store.requirements = _payload_collection(load_requirements(), "requirements")
    load_ai_tasks = getattr(repository, "load_ai_tasks", None)
    if callable(load_ai_tasks):
        source_store.ai_tasks = _payload_collection(load_ai_tasks(), "ai_tasks")
    load_bugs = getattr(repository, "load_bugs", None)
    if callable(load_bugs):
        source_store.bugs = _payload_collection(load_bugs(), "bugs")
    return source_store


def _product_config_write_store(current_store: MemoryStore) -> MemoryStore:
    repository = _product_config_query_repository(current_store)
    if repository is None:
        return current_store
    return _product_config_source_store(repository)


def _model_gateway_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = [
        "list_model_gateway_configs",
        "list_model_gateway_logs",
    ]
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _model_gateway_source_store(repository: Any) -> Any:
    source_store = _RepositoryRequestContext(repository)
    source_store.model_gateway_configs = {
        str(item["id"]): dict(item)
        for item in repository.list_model_gateway_configs()
        if item.get("id") is not None
    }
    source_store.model_gateway_logs = [
        dict(item) for item in repository.list_model_gateway_logs()
    ]
    return source_store


def _model_gateway_write_store(current_store: MemoryStore) -> MemoryStore:
    repository = _model_gateway_query_repository(current_store)
    if repository is None:
        return current_store
    return _model_gateway_source_store(repository)


def _knowledge_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    if getattr(repository, "list_knowledge_documents", None) is not None:
        return repository
    return None


def _knowledge_source_store(repository: Any) -> Any:
    source_store = _product_config_source_store(repository)
    load_knowledge = getattr(repository, "load_knowledge", None)
    if callable(load_knowledge):
        knowledge_payload = load_knowledge()
        source_store.knowledge_documents = _payload_collection(
            knowledge_payload,
            "knowledge_documents",
        )
        source_store.knowledge_chunks = _payload_collection(
            knowledge_payload,
            "knowledge_chunks",
        )
        source_store.knowledge_deposits = _payload_collection(
            knowledge_payload,
            "knowledge_deposits",
        )
    load_model_gateway = getattr(repository, "load_model_gateway", None)
    if callable(load_model_gateway):
        model_gateway_payload = load_model_gateway() or {}
        source_store.model_gateway_configs = _payload_collection(
            model_gateway_payload,
            "model_gateway_configs",
        )
        source_store.model_gateway_logs = [
            dict(item) for item in model_gateway_payload.get("model_gateway_logs", [])
        ]
    return source_store


def _knowledge_write_store(current_store: MemoryStore) -> MemoryStore:
    repository = _knowledge_query_repository(current_store)
    if repository is None:
        return current_store
    return _knowledge_source_store(repository)


def _assistant_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = [
        "list_assistant_conversation_messages",
        "list_assistant_conversations",
    ]
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _assistant_source_store(repository: Any, *, user_id: str) -> Any:
    load_task_rows = getattr(repository, "get_task_workflow_source_rows", None)
    source_store = (
        _task_workflow_source_store(load_task_rows(), repository=repository)
        if callable(load_task_rows)
        else _RepositoryRequestContext(repository)
    )
    conversations = repository.list_assistant_conversations(user_id=user_id)
    source_store.assistant_conversations = {
        str(conversation["id"]): dict(conversation)
        for conversation in conversations
        if conversation.get("id") is not None
    }
    messages: dict[str, dict[str, Any]] = {}
    for conversation in conversations:
        conversation_id = conversation.get("id")
        if conversation_id is None:
            continue
        conversation_messages = repository.list_assistant_conversation_messages(
            conversation_id=str(conversation_id),
            user_id=user_id,
        )
        for message in conversation_messages or []:
            if message.get("id") is not None:
                messages[str(message["id"])] = dict(message)
    source_store.assistant_messages = messages
    return source_store


def _assistant_write_store(current_store: MemoryStore, *, user_id: str) -> MemoryStore:
    repository = _assistant_query_repository(current_store)
    if repository is None:
        return current_store
    return _assistant_source_store(repository, user_id=user_id)


def _audit_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    if getattr(repository, "list_audit_events", None) is not None:
        return repository
    return None


def _bug_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    if getattr(repository, "list_bugs", None) is not None:
        return repository
    return None


def _insight_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = (
        "list_user_usage_metrics",
        "list_user_feedback",
        "list_iteration_plan_suggestions",
    )
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _insight_source_store(repository: Any) -> Any:
    source_store = _product_config_source_store(repository)
    source_store.user_usage_metrics = {
        str(item["id"]): dict(item)
        for item in repository.list_user_usage_metrics()
        if item.get("id") is not None
    }
    source_store.user_feedback = {
        str(item["id"]): dict(item)
        for item in repository.list_user_feedback()
        if item.get("id") is not None
    }
    source_store.iteration_plan_suggestions = {
        str(item["id"]): dict(item)
        for item in repository.list_iteration_plan_suggestions()
        if item.get("id") is not None
    }
    load_iteration_planning = getattr(repository, "load_iteration_planning", None)
    if callable(load_iteration_planning):
        source_store.iteration_plan_decisions = _payload_collection(
            load_iteration_planning(),
            "iteration_plan_decisions",
        )
    return source_store


def _insight_write_store(current_store: MemoryStore) -> MemoryStore:
    repository = _insight_query_repository(current_store)
    if repository is None:
        return current_store
    return _insight_source_store(repository)


def _operational_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = (
        "list_collector_runs",
        "list_pending_attribution_items",
        "list_gitlab_daily_code_metrics",
        "list_jenkins_release_records",
        "list_online_log_metrics",
    )
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _operational_source_store(repository: Any) -> Any:
    source_store = _product_config_source_store(repository)
    collection_loaders = {
        "collector_runs": lambda: repository.list_collector_runs(),
        "gitlab_daily_code_metrics": lambda: repository.list_gitlab_daily_code_metrics(),
        "jenkins_release_records": lambda: repository.list_jenkins_release_records(),
        "online_log_metrics": lambda: repository.list_online_log_metrics(),
        "pending_attribution_items": lambda: repository.list_pending_attribution_items(),
    }
    for collection_name, loader in collection_loaders.items():
        setattr(
            source_store,
            collection_name,
            {
                str(item["id"]): dict(item)
                for item in loader()
                if item.get("id") is not None
            },
        )
    return source_store


def _operational_write_store(current_store: MemoryStore) -> MemoryStore:
    repository = _operational_query_repository(current_store)
    if repository is None:
        return current_store
    return _operational_source_store(repository)


def _dashboard_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = (
        "get_dashboard_it_team_source_rows",
        "get_product",
        "save_dashboard_metric_snapshot_record",
    )
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _lifecycle_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = (
        "get_lifecycle_context_source_rows",
        "save_lifecycle_context",
    )
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _task_workflow_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = ("get_task_workflow_source_rows",)
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def _pending_review_query_repository(current_store: MemoryStore) -> Any | None:
    repository = _runtime_repository(current_store)
    if repository is None:
        return None
    list_pending_reviews = getattr(repository, "list_pending_review_summaries", None)
    if callable(list_pending_reviews):
        return repository
    return None


def _repository_read_model_store(current_store: MemoryStore) -> MemoryStore:
    return current_store


def _save_product_config_record(
    current_store: MemoryStore,
    collection_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_record = getattr(repository, "save_product_config_record", None)
    if save_record is not None:
        save_record(collection_name, record, audit_event=audit_event)


def _delete_product_config_record(
    current_store: MemoryStore,
    collection_name: str,
    record_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    delete_record = getattr(repository, "delete_product_config_record", None)
    if delete_record is not None:
        delete_record(collection_name, record_id, audit_event=audit_event)


def _save_requirement_record(
    current_store: MemoryStore,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_record = getattr(repository, "save_requirement_record", None)
    if save_record is not None:
        save_record(record, audit_event=audit_event)


def _save_audit_event(current_store: MemoryStore, audit_event: dict[str, Any]) -> None:
    repository = _runtime_repository(current_store)
    append_event = getattr(repository, "append_audit_event", None)
    if append_event is not None:
        append_event(audit_event)
        return
    save_events = getattr(repository, "save_audit_events", None)
    if save_events is not None:
        save_events({"audit_events": [audit_event]})


def _delete_requirement_record(
    current_store: MemoryStore,
    record_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    delete_record = getattr(repository, "delete_requirement_record", None)
    if delete_record is not None:
        delete_record(record_id, audit_event=audit_event)


def _save_requirement_and_ai_task_records(
    current_store: MemoryStore,
    *,
    requirement: dict[str, Any],
    task: dict[str, Any],
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_requirement_and_ai_task_records", None)
    if save_records is not None:
        save_records(requirement=requirement, task=task, audit_event=audit_event)


def _save_task_start_records(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
    review: dict[str, Any],
    graph_run: dict[str, Any],
    checkpoint: dict[str, Any],
    audit_events: list[dict[str, Any]],
    model_log: dict[str, Any] | None = None,
    code_review_report: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_task_start_records", None)
    if save_records is not None:
        save_records(
            task=task,
            review=review,
            graph_run=graph_run,
            checkpoint=checkpoint,
            audit_events=audit_events,
            model_log=model_log,
            code_review_report=code_review_report,
        )


def _save_review_decision_records(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
    review: dict[str, Any],
    graph_run: dict[str, Any] | None,
    checkpoint: dict[str, Any] | None,
    audit_events: list[dict[str, Any]],
    requirement: dict[str, Any] | None = None,
    knowledge_deposits: list[dict[str, Any]] | None = None,
    bugs: list[dict[str, Any]] | None = None,
    code_review_report: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_review_decision_records", None)
    if save_records is not None:
        save_records(
            task=task,
            review=review,
            graph_run=graph_run,
            checkpoint=checkpoint,
            audit_events=audit_events,
            requirement=requirement,
            knowledge_deposits=knowledge_deposits,
            bugs=bugs,
            code_review_report=code_review_report,
        )


def _save_task_state_records(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
    audit_events: list[dict[str, Any]],
    reviews: list[dict[str, Any]] | None = None,
    graph_run: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
    model_log: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_task_state_records", None)
    if save_records is not None:
        save_records(
            task=task,
            audit_events=audit_events,
            reviews=reviews,
            graph_run=graph_run,
            checkpoint=checkpoint,
            model_log=model_log,
        )


def _knowledge_chunks_for_document(
    current_store: MemoryStore,
    document_id: str,
) -> list[dict[str, Any]]:
    return [
        chunk
        for chunk in current_store.knowledge_chunks.values()
        if chunk.get("document_id") == document_id
    ]


def _save_mock_writeback_record(
    current_store: MemoryStore,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_record = getattr(repository, "save_mock_writeback_record", None)
    if save_record is not None:
        save_record(record, audit_event=audit_event)


def _save_knowledge_document_records(
    current_store: MemoryStore,
    *,
    document: dict[str, Any],
    chunks: list[dict[str, Any]] | None = None,
    audit_event: dict[str, Any] | None = None,
    model_logs: list[dict[str, Any]] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_knowledge_document_records", None)
    if save_records is not None:
        save_records(
            document=document,
            chunks=chunks
            if chunks is not None
            else _knowledge_chunks_for_document(current_store, document["id"]),
            audit_event=audit_event,
            model_logs=model_logs,
        )


def _delete_knowledge_document_records(
    current_store: MemoryStore,
    *,
    document_id: str,
    deposits: list[dict[str, Any]],
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    delete_records = getattr(repository, "delete_knowledge_document_records", None)
    if delete_records is not None:
        delete_records(
            document_id=document_id,
            deposits=deposits,
            audit_event=audit_event,
        )


def _save_knowledge_deposit_records(
    current_store: MemoryStore,
    *,
    deposit: dict[str, Any],
    audit_event: dict[str, Any] | None = None,
    document: dict[str, Any] | None = None,
    chunks: list[dict[str, Any]] | None = None,
    model_logs: list[dict[str, Any]] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_knowledge_deposit_records", None)
    if save_records is not None:
        save_records(
            deposit=deposit,
            document=document,
            chunks=chunks
            if chunks is not None
            else (
                _knowledge_chunks_for_document(current_store, document["id"])
                if document is not None
                else None
            ),
            audit_event=audit_event,
            model_logs=model_logs,
        )


def _get_knowledge_deposit(current_store: MemoryStore, deposit_id: str) -> dict[str, Any] | None:
    repository = _runtime_repository(current_store)
    get_deposit = getattr(repository, "get_knowledge_deposit", None)
    if get_deposit is not None:
        return get_deposit(deposit_id)
    return current_store.knowledge_deposits.get(deposit_id)


def _save_assistant_chat_records(
    current_store: MemoryStore,
    *,
    conversation: dict[str, Any] | None,
    messages: list[dict[str, Any]],
    audit_events: list[dict[str, Any]],
    model_log: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_assistant_chat_records", None)
    if save_records is not None:
        save_records(
            conversation=conversation,
            messages=messages,
            model_log=model_log,
            audit_events=audit_events,
        )


def _save_gitlab_review_snapshot_record(
    current_store: MemoryStore,
    *,
    snapshot: dict[str, Any] | None,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_record = getattr(repository, "save_gitlab_review_snapshot_record", None)
    if save_record is not None:
        save_record(snapshot=snapshot, audit_event=audit_event)


def _save_bug_record(
    current_store: MemoryStore,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_record = getattr(repository, "save_bug_record", None)
    if save_record is not None:
        save_record(record, audit_event=audit_event)


def _delete_bug_record(
    current_store: MemoryStore,
    record_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    delete_record = getattr(repository, "delete_bug_record", None)
    if delete_record is not None:
        delete_record(record_id, audit_event=audit_event)


def _save_single_repository_record(
    current_store: MemoryStore,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_record = getattr(repository, method_name, None)
    if save_record is not None:
        save_record(record, audit_event=audit_event)


def _save_iteration_decision_records(
    current_store: MemoryStore,
    *,
    suggestion: dict[str, Any],
    decision: dict[str, Any],
    audit_events: list[dict[str, Any]],
    requirement: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_iteration_decision_records", None)
    if save_records is not None:
        save_records(
            suggestion=suggestion,
            decision=decision,
            audit_events=audit_events,
            requirement=requirement,
        )


def _save_lifecycle_context_records(current_store: MemoryStore) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_lifecycle_context", None)
    if save_records is not None:
        save_records(
            {
                "lifecycle_context_edges": current_store.lifecycle_context_edges,
                "lifecycle_risk_signals": current_store.lifecycle_risk_signals,
            }
        )


def _save_dashboard_snapshot_records(current_store: MemoryStore) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_dashboard_snapshots", None)
    if save_records is not None:
        save_records({"dashboard_metric_snapshots": current_store.dashboard_metric_snapshots})


def _save_dashboard_metric_snapshot_record(
    current_store: MemoryStore,
    snapshot: dict[str, Any],
) -> None:
    repository = _runtime_repository(current_store)
    save_record = getattr(repository, "save_dashboard_metric_snapshot_record", None)
    if save_record is not None:
        save_record(snapshot)


def _save_model_gateway_records(
    current_store: MemoryStore,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    _save_model_gateway_payload(
        current_store,
        configs=current_store.model_gateway_configs,
        logs=current_store.model_gateway_logs,
        audit_event=audit_event,
    )


def _save_model_gateway_payload(
    current_store: Any,
    *,
    configs: dict[str, dict[str, Any]],
    logs: list[dict[str, Any]],
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _runtime_repository(current_store)
    save_records = getattr(repository, "save_model_gateway_records", None)
    if save_records is not None:
        save_records(
            {
                "model_gateway_configs": configs,
                "model_gateway_logs": logs,
            },
            audit_event=audit_event,
        )


def _product_version_summary_projection(
    version: dict[str, Any],
    current_store: MemoryStore,
) -> dict[str, Any]:
    product = current_store.products.get(version.get("product_id"), {})
    return {
        **version,
        "product_code": product.get("code"),
        "product_name": product.get("name"),
    }


def _requirement_summary_projection(
    requirement: dict[str, Any],
    current_store: MemoryStore,
) -> dict[str, Any]:
    product = current_store.products.get(requirement.get("product_id"), {})
    version = current_store.product_versions.get(requirement.get("version_id"), {})
    return {
        **requirement,
        "product_code": product.get("code"),
        "product_name": product.get("name"),
        "version_code": version.get("code"),
        "version_name": version.get("name"),
    }


def _bug_summary_projection(
    bug: dict[str, Any],
    current_store: MemoryStore,
) -> dict[str, Any]:
    version = current_store.product_versions.get(bug.get("version_id"), {})
    return {
        **bug,
        "version_code": version.get("code"),
        "version_name": version.get("name"),
    }


def _first_present_value(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = item.get(field)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _sort_by_lifecycle_time(items: list[dict[str, Any]], *fields: str) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (_first_present_value(item, fields), str(item.get("id") or "")),
    )


def _compact_lifecycle_title(prefix: str, subject_id: str, label: str | None = None) -> str:
    text = (label or "").strip()
    if not text or len(text) > 48:
        text = subject_id
    return f"{prefix}：{text}"


def _full_chain_event(
    *,
    event_type: str,
    occurred_at: str,
    subject_id: str,
    title: str,
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"{event_type}:{subject_id}",
        "metadata": metadata or {},
        "occurred_at": occurred_at,
        "status": status,
        "subject_id": subject_id,
        "subject_type": event_type,
        "title": title,
        "type": event_type,
    }


def _requirement_full_chain_payload(
    current_store: MemoryStore,
    requirement: dict[str, Any],
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    requirement_id = str(requirement["id"])
    product = current_store.products.get(str(requirement.get("product_id"))) or {}
    version_id = requirement.get("version_id")
    iteration_version = (
        current_store.product_versions.get(str(version_id))
        if version_id is not None
        else None
    )
    tasks = _sort_by_lifecycle_time(
        [
            task
            for task in current_store.ai_tasks.values()
            if str(task.get("requirement_id")) == requirement_id and _can_read_task(user, task)
        ],
        "created_at",
        "updated_at",
    )
    task_ids = {str(task["id"]) for task in tasks}
    review_ids = {
        str(review_id)
        for task in tasks
        for review_id in task.get("review_ids", [])
    }
    reviews = _sort_by_lifecycle_time(
        [
            review
            for review in current_store.human_reviews.values()
            if str(review.get("ai_task_id")) in task_ids or str(review.get("id")) in review_ids
        ],
        "created_at",
        "decided_at",
        "updated_at",
    )
    code_review_report_ids = {
        str(task.get("code_review_report_id"))
        for task in tasks
        if task.get("code_review_report_id")
    }
    code_review_reports = _sort_by_lifecycle_time(
        [
            report
            for report in current_store.code_review_reports.values()
            if str(report.get("task_id")) in task_ids
            or str(report.get("id")) in code_review_report_ids
        ],
        "created_at",
        "archived_at",
        "updated_at",
    )
    git_snapshots = _sort_by_lifecycle_time(
        [
            snapshot
            for snapshot in current_store.gitlab_mr_snapshots.values()
            if str(snapshot.get("requirement_id")) == requirement_id
            or str(snapshot.get("technical_solution_task_id")) in task_ids
        ],
        "created_at",
        "captured_at",
        "updated_at",
    )
    bugs = _sort_by_lifecycle_time(
        [
            _bug_summary_projection(bug, current_store)
            for bug in current_store.bugs.values()
            if str(bug.get("requirement_id")) == requirement_id
            or str(bug.get("related_task_id")) in task_ids
        ],
        "created_at",
        "updated_at",
    )
    knowledge_deposits = _sort_by_lifecycle_time(
        [
            deposit
            for deposit in current_store.knowledge_deposits.values()
            if str(deposit.get("ai_task_id")) in task_ids
        ],
        "created_at",
        "updated_at",
    )
    jenkins_releases = _sort_by_lifecycle_time(
        [
            release
            for release in current_store.jenkins_release_records.values()
            if release.get("product_id") == requirement.get("product_id")
            and (
                not requirement.get("version_id")
                or release.get("version_id") == requirement.get("version_id")
            )
        ],
        "started_at",
        "deployed_at",
        "created_at",
        "updated_at",
    )

    timeline = [
        _full_chain_event(
            event_type="requirement",
            occurred_at=_first_present_value(requirement, ("created_at", "updated_at")),
            subject_id=requirement_id,
            status=requirement.get("status"),
            title=f"需求：{requirement.get('title') or requirement_id}",
        )
    ]
    if iteration_version is not None:
        timeline.append(
            _full_chain_event(
                event_type="iteration_version",
                occurred_at=_first_present_value(
                    iteration_version,
                    ("start_date", "planned_release_at", "created_at", "updated_at"),
                )
                or _first_present_value(requirement, ("created_at", "updated_at")),
                subject_id=str(iteration_version["id"]),
                status=iteration_version.get("status"),
                title=(
                    f"迭代版本：{iteration_version.get('name') or iteration_version.get('code')}"
                ),
            )
        )
    timeline.extend(
        _full_chain_event(
            event_type="ai_task",
            occurred_at=_first_present_value(task, ("created_at", "updated_at")),
            subject_id=str(task["id"]),
            status=task.get("status"),
            title=f"AI 任务：{task.get('title') or task['id']}",
            metadata={"task_type": task.get("task_type")},
        )
        for task in tasks
    )
    timeline.extend(
        _full_chain_event(
            event_type="review",
            occurred_at=_first_present_value(review, ("decided_at", "created_at", "updated_at")),
            subject_id=str(review["id"]),
            status=review.get("status"),
            title=f"人工确认：{review.get('review_type') or review['id']}",
            metadata={"ai_task_id": review.get("ai_task_id")},
        )
        for review in reviews
    )
    timeline.extend(
        _full_chain_event(
            event_type="git_snapshot",
            occurred_at=_first_present_value(snapshot, ("captured_at", "created_at", "updated_at")),
            subject_id=str(snapshot["id"]),
            status=snapshot.get("status"),
            title=(
                f"PR/MR 快照：{snapshot.get('source_ref') or snapshot.get('mr_iid') or snapshot['id']}"
            ),
            metadata={"repository_id": snapshot.get("repository_id")},
        )
        for snapshot in git_snapshots
    )
    timeline.extend(
        _full_chain_event(
            event_type="code_review_report",
            occurred_at=_first_present_value(report, ("archived_at", "created_at", "updated_at")),
            subject_id=str(report["id"]),
            status=report.get("status"),
            title=_compact_lifecycle_title(
                "代码评审",
                str(report["id"]),
                report.get("title"),
            ),
            metadata={
                "risk_level": report.get("risk_level"),
                "summary": report.get("summary"),
                "task_id": report.get("task_id"),
            },
        )
        for report in code_review_reports
    )
    timeline.extend(
        _full_chain_event(
            event_type="bug",
            occurred_at=_first_present_value(bug, ("created_at", "updated_at")),
            subject_id=str(bug["id"]),
            status=bug.get("status"),
            title=f"Bug：{bug.get('title') or bug['id']}",
            metadata={"severity": bug.get("severity"), "source": bug.get("source")},
        )
        for bug in bugs
    )
    timeline.extend(
        _full_chain_event(
            event_type="jenkins_release",
            occurred_at=_first_present_value(
                release,
                ("deployed_at", "started_at", "created_at", "updated_at"),
            ),
            subject_id=str(release["id"]),
            status=release.get("status"),
            title=f"发布：{release.get('job_name') or release.get('build_id') or release['id']}",
            metadata={"environment": release.get("environment")},
        )
        for release in jenkins_releases
    )
    timeline.extend(
        _full_chain_event(
            event_type="knowledge_deposit",
            occurred_at=_first_present_value(deposit, ("created_at", "updated_at")),
            subject_id=str(deposit["id"]),
            status=deposit.get("status"),
            title=f"知识沉淀：{deposit.get('title') or deposit['id']}",
            metadata={"ai_task_id": deposit.get("ai_task_id")},
        )
        for deposit in knowledge_deposits
    )
    timeline.sort(key=lambda item: (item["occurred_at"], item["type"], item["subject_id"]))

    return {
        "status": "available",
        "requirement": _requirement_summary_projection(requirement, current_store),
        "product": current_store.snapshot(product) if product else None,
        "iteration_version": (
            current_store.snapshot(iteration_version)
            if iteration_version is not None
            else None
        ),
        "ai_tasks": [_task_summary_projection(task, current_store) for task in tasks],
        "reviews": current_store.snapshot(reviews),
        "git_snapshots": current_store.snapshot(git_snapshots),
        "code_review_reports": current_store.snapshot(code_review_reports),
        "bugs": current_store.snapshot(bugs),
        "jenkins_releases": current_store.snapshot(jenkins_releases),
        "knowledge_deposits": current_store.snapshot(knowledge_deposits),
        "timeline": timeline,
        "summary": {
            "ai_tasks": len(tasks),
            "reviews": len(reviews),
            "git_snapshots": len(git_snapshots),
            "code_review_reports": len(code_review_reports),
            "bugs": len(bugs),
            "jenkins_releases": len(jenkins_releases),
            "knowledge_deposits": len(knowledge_deposits),
            "timeline_events": len(timeline),
        },
    }


def _public_model_gateway_config(config: dict[str, Any]) -> dict[str, Any]:
    public_config = {
        key: value
        for key, value in config.items()
        if key not in {"api_key", "embedding_api_key"}
    }
    api_key = config.get("api_key")
    embedding_api_key = config.get("embedding_api_key")
    public_config["api_key_configured"] = bool(api_key)
    public_config["embedding_api_key_configured"] = bool(embedding_api_key)
    public_config["embedding_connection_mode"] = _embedding_connection_mode(config)
    public_config.setdefault("default_embedding_model", None)
    return public_config


def _optional_non_blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _embedding_connection_mode(config: dict[str, Any]) -> str:
    mode = config.get("embedding_connection_mode")
    if mode:
        return str(mode)
    if _optional_non_blank(config.get("default_embedding_model")):
        return "reuse_chat"
    return "disabled"


def _normalize_embedding_connection_mode(
    mode: str | None,
    *,
    default_embedding_model: str | None,
) -> str:
    normalized_mode = _optional_non_blank(mode)
    if normalized_mode is None:
        return "reuse_chat" if _optional_non_blank(default_embedding_model) else "disabled"
    _ensure_enum(
        normalized_mode,
        MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES,
        "embedding connection mode",
    )
    return normalized_mode


def _normalize_embedding_dimension(value: int | None) -> int | None:
    if value is None:
        return None
    if value <= 0:
        raise api_error(400, "VALIDATION_ERROR", "embedding_dimension must be positive")
    if value != settings.vector_dimension:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            (
                "embedding_dimension must equal configured vector dimension "
                f"{settings.vector_dimension}"
            ),
        )
    return value


def _normalized_model_gateway_embedding_fields(
    *,
    api_key: str | None,
    base_url: str,
    default_embedding_model: str | None,
    embedding_api_key: str | None,
    embedding_base_url: str | None,
    embedding_connection_mode: str | None,
    embedding_dimension: int | None,
    existing_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = _optional_non_blank(default_embedding_model)
    mode = _normalize_embedding_connection_mode(
        embedding_connection_mode,
        default_embedding_model=model,
    )
    dimension = _normalize_embedding_dimension(embedding_dimension)
    if mode == "disabled":
        return {
            "default_embedding_model": None,
            "embedding_api_key": None,
            "embedding_base_url": None,
            "embedding_connection_mode": mode,
            "embedding_dimension": None,
        }
    if model is None:
        raise api_error(400, "VALIDATION_ERROR", "default_embedding_model is required")
    if mode == "reuse_chat":
        return {
            "default_embedding_model": model,
            "embedding_api_key": None,
            "embedding_base_url": None,
            "embedding_connection_mode": mode,
            "embedding_dimension": dimension or settings.vector_dimension,
        }

    custom_base_url = _optional_non_blank(embedding_base_url)
    if custom_base_url is None:
        raise api_error(400, "VALIDATION_ERROR", "embedding_base_url is required")
    custom_api_key = (
        _optional_non_blank(embedding_api_key)
        or (existing_config or {}).get("embedding_api_key")
    )
    if custom_api_key is None:
        raise api_error(400, "VALIDATION_ERROR", "embedding_api_key is required")
    return {
        "default_embedding_model": model,
        "embedding_api_key": custom_api_key,
        "embedding_base_url": custom_base_url,
        "embedding_connection_mode": mode,
        "embedding_dimension": dimension or settings.vector_dimension,
    }


def _model_gateway_embedding_test_fields(
    *,
    default_embedding_model: str | None,
    embedding_api_key: str | None,
    embedding_base_url: str | None,
    embedding_connection_mode: str | None,
    embedding_dimension: int | None,
    existing_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = _optional_non_blank(default_embedding_model)
    mode = _normalize_embedding_connection_mode(
        embedding_connection_mode,
        default_embedding_model=model,
    )
    dimension = (
        embedding_dimension
        if embedding_dimension is not None and embedding_dimension > 0
        else None
    )
    if mode == "disabled":
        return {
            "default_embedding_model": None,
            "embedding_api_key": None,
            "embedding_base_url": None,
            "embedding_connection_mode": mode,
            "embedding_dimension": None,
        }
    return {
        "default_embedding_model": model,
        "embedding_api_key": (
            _optional_non_blank(embedding_api_key)
            or (existing_config or {}).get("embedding_api_key")
        ),
        "embedding_base_url": (
            _optional_non_blank(embedding_base_url)
            or (existing_config or {}).get("embedding_base_url")
        ),
        "embedding_connection_mode": mode,
        "embedding_dimension": (
            dimension
            or (existing_config or {}).get("embedding_dimension")
            or (settings.vector_dimension if model else None)
        ),
    }


def _model_gateway_test_failure(
    *,
    error_code: str,
    model: str,
    started: float,
) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "latency_ms": int((perf_counter() - started) * 1000),
        "model": model,
        "ok": False,
        "status": "failed",
    }


def _model_gateway_test_skipped(*, model: str = "") -> dict[str, Any]:
    return {
        "model": model,
        "ok": True,
        "status": "skipped",
    }


def _test_model_gateway_chat(config: dict[str, Any]) -> dict[str, Any]:
    model = config["default_chat_model"]
    body = {
        "messages": [
            {
                "content": (
                    "Return one compact JSON object with a string field named summary. "
                    "This is an AI Brain model gateway connectivity test."
                ),
                "role": "user",
            }
        ],
        "model": model,
        "response_format": {"type": "json_object"},
        "temperature": 0,
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
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Model gateway chat response is missing choices")
        return {
            "latency_ms": int((perf_counter() - started) * 1000),
            "model": model,
            "ok": True,
            "status": "succeeded",
        }
    except (
        AttributeError,
        HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return _model_gateway_test_failure(
            error_code="MODEL_GATEWAY_CHAT_FAILED",
            model=model,
            started=started,
        )


def _runtime_required_text(value: Any, message: str) -> str:
    if value is None:
        raise ModelGatewayConfigError(message)
    text = str(value).strip()
    if not text:
        raise ModelGatewayConfigError(message)
    return text


def _model_gateway_embedding_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("provider") != "openai_compatible":
        raise ModelGatewayConfigError("Active model gateway provider is not supported")
    mode = _embedding_connection_mode(config)
    if mode == "disabled":
        raise ModelGatewayConfigError("Embedding gateway is disabled")
    model = _runtime_required_text(
        config.get("default_embedding_model"),
        "Active model gateway config is missing default_embedding_model",
    )
    if mode == "custom":
        base_url = _runtime_required_text(
            config.get("embedding_base_url"),
            "Active model gateway config is missing embedding_base_url",
        )
        api_key = _runtime_required_text(
            config.get("embedding_api_key"),
            "Active model gateway config is missing embedding_api_key",
        )
    else:
        base_url = _runtime_required_text(
            config.get("base_url"),
            "Active model gateway config is missing base_url",
        )
        api_key = _runtime_required_text(
            config.get("api_key"),
            "Active model gateway config is missing api_key",
        )
    return {
        **config,
        "api_key": api_key,
        "base_url": base_url,
        "default_embedding_model": model,
        "embedding_connection_mode": mode,
    }


def _test_model_gateway_embedding(config: dict[str, Any]) -> dict[str, Any]:
    try:
        embedding_config = _model_gateway_embedding_runtime_config(config)
    except ModelGatewayConfigError:
        started = perf_counter()
        return _model_gateway_test_failure(
            error_code="MODEL_GATEWAY_EMBEDDING_CONFIG_INVALID",
            model=str(config.get("default_embedding_model") or ""),
            started=started,
        )
    model = embedding_config["default_embedding_model"]
    body = {
        "input": ["AI Brain model gateway embedding connectivity test"],
        "model": model,
    }
    request = UrlRequest(
        _model_gateway_embeddings_url(embedding_config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {embedding_config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            payload = json.loads(response.read().decode("utf-8"))
        embeddings = _parse_embedding_response(payload, expected_count=1)
        return {
            "dimension": len(embeddings[0]),
            "latency_ms": int((perf_counter() - started) * 1000),
            "model": model,
            "ok": True,
            "status": "succeeded",
        }
    except (
        AttributeError,
        HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return _model_gateway_test_failure(
            error_code="MODEL_GATEWAY_EMBEDDING_FAILED",
            model=model,
            started=started,
        )


def _public_git_repository(repository: dict[str, Any]) -> dict[str, Any]:
    public_repository = {
        key: value
        for key, value in repository.items()
        if key != "credential_ref"
    }
    public_repository["credential_ref_configured"] = bool(
        repository.get("credential_ref") or repository.get("credential_ref_configured")
    )
    return public_repository


def _public_product_context(product_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(product_context, dict):
        return {}
    public_context = json.loads(json.dumps(product_context, ensure_ascii=False))
    repositories = public_context.get("repositories")
    if isinstance(repositories, dict):
        items = repositories.get("items")
        if isinstance(items, list):
            repositories["items"] = [
                _public_git_repository(item) if isinstance(item, dict) else item
                for item in items
            ]
            repositories["total"] = len(repositories["items"])
    return public_context


def _set_default_model_gateway_config(
    current_store: MemoryStore,
    *,
    config_id: str,
    is_default: bool,
) -> None:
    if not is_default:
        return
    for item_id, item in current_store.model_gateway_configs.items():
        item["is_default"] = item_id == config_id


def _model_gateway_configs_after_default(
    configs: dict[str, dict[str, Any]],
    *,
    config_id: str,
    is_default: bool,
) -> dict[str, dict[str, Any]]:
    if not is_default:
        return configs
    return {
        item_id: {**item, "is_default": item_id == config_id}
        for item_id, item in configs.items()
    }


def _default_model_gateway_config(current_store: MemoryStore) -> dict[str, Any] | None:
    for item in current_store.model_gateway_configs.values():
        if item.get("is_default") and item.get("status") == "active":
            return item
    return None


def _estimate_tokens(value: Any) -> int:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return max(1, len(serialized) // 4)


class ModelGatewayCallError(Exception):
    def __init__(self, log: dict[str, Any]):
        super().__init__("Model gateway request failed")
        self.log = log


class ModelGatewayConfigError(Exception):
    def __init__(self, message: str, current_step: str = "model_gateway_config_invalid"):
        super().__init__(message)
        self.current_step = current_step


def _model_gateway_chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _model_gateway_embeddings_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/embeddings"):
        return normalized
    return f"{normalized}/embeddings"


def _model_gateway_messages(
    current_store: MemoryStore,
    task: dict[str, Any],
) -> list[dict[str, str]]:
    if task["task_type"] == "code_review":
        payload = _code_review_executor_payload(current_store, task)
        payload["expected_output_schema"] = {
            "summary": "string",
            "risk_level": "low | medium | high",
            "findings": [
                {
                    "severity": "low | medium | high",
                    "file_path": "string",
                    "line_start": "integer or null",
                    "line_end": "integer or null",
                    "category": "string",
                    "message": "string",
                    "suggestion": "string",
                    "confidence": "number from 0 to 1",
                }
            ],
        }
        system_content = (
            "You are the AI Brain code-review executor. Review only the provided MR/PR "
            "snapshot, requirement, technical solution, and product context. Return one "
            "JSON object only with summary, risk_level, and findings. Do not invent file "
            "paths that are absent from changed_files_summary."
        )
    else:
        payload = {
            "input_json": task.get("input_json", {}),
            "product_context": _public_product_context(task.get("product_context")),
            "requirement_snapshot": task.get("requirement_snapshot", {}),
            "task_type": task["task_type"],
            "title": task["title"],
        }
        system_content = (
            "You are the AI Brain model gateway. Return one JSON object only, "
            "without markdown, comments, or explanatory text."
        )
    return [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def _model_gateway_log(
    current_store: MemoryStore,
    *,
    provider: str,
    model: str,
    config_id: str | None,
    tokens: dict[str, int],
    latency_ms: int,
    status: str,
    task: dict[str, Any] | None = None,
    purpose: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    ai_task_id = task["id"] if task else None
    resolved_purpose = purpose or (task["task_type"] if task else "model_gateway")
    log = {
        "id": current_store.new_id("model_log"),
        "ai_task_id": ai_task_id,
        "provider": provider,
        "model": model,
        "purpose": resolved_purpose,
        "tokens": tokens,
        "latency_ms": latency_ms,
        "status": status,
        "error": error,
        "model_gateway_config_id": config_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    current_store.model_gateway_logs.append(log)
    return log


def _derive_code_review_risk_level(output: dict[str, Any]) -> str:
    risk_level = output.get("risk_level")
    if isinstance(risk_level, str) and risk_level.strip():
        return risk_level.strip()
    overall = str(output.get("overall") or output.get("decision") or "").lower()
    if any(marker in overall for marker in ("block", "request_changes", "high", "reject")):
        return "high"
    if any(marker in overall for marker in ("warn", "medium", "conditional", "review")):
        return "medium"
    if any(marker in overall for marker in ("approve", "low", "pass")):
        return "low"
    score = output.get("score")
    if isinstance(score, int | float):
        if score < 60:
            return "high"
        if score < 80:
            return "medium"
        return "low"
    findings = output.get("findings")
    if isinstance(findings, list):
        severities = {
            str(item.get("severity") or "").lower()
            for item in findings
            if isinstance(item, dict)
        }
        if severities & {"critical", "blocker", "high"}:
            return "high"
        if severities & {"major", "medium"}:
            return "medium"
        return "low"
    return "medium"


def _normalize_model_gateway_code_review_output(output: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(output)
    normalized["risk_level"] = _derive_code_review_risk_level(normalized)
    if not isinstance(normalized.get("executor"), dict):
        normalized["executor"] = {}
    return normalized


def _parse_model_gateway_output(
    response_payload: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Model gateway response is missing choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError("Model gateway response is missing message")
    content = message.get("content")
    if isinstance(content, str):
        parsed = json.loads(content)
    elif isinstance(content, dict):
        parsed = content
    else:
        raise ValueError("Model gateway response content must be a JSON object")
    if not isinstance(parsed, dict):
        raise ValueError("Model gateway response content must be a JSON object")

    output = parsed
    if task["task_type"] == "code_review":
        output = _normalize_model_gateway_code_review_output(output)
    if not isinstance(output.get("summary"), str) or not output["summary"].strip():
        raise ValueError("Model gateway response content is missing summary")
    if task["task_type"] == "code_review":
        if not isinstance(output.get("risk_level"), str):
            raise ValueError("Code review response is missing risk_level")
        if not isinstance(output.get("findings"), list):
            raise ValueError("Code review response is missing findings")
        if not isinstance(output.get("executor"), dict):
            raise ValueError("Code review response is missing executor")
    return output


def _openai_usage_tokens(
    usage: Any,
    *,
    messages: list[dict[str, str]],
    output: dict[str, Any],
) -> dict[str, int]:
    if not isinstance(usage, dict):
        prompt = _estimate_tokens(messages)
        completion = _estimate_tokens(output)
        return {"prompt": prompt, "completion": completion, "total": prompt + completion}
    prompt = int(usage.get("prompt_tokens") or _estimate_tokens(messages))
    completion = int(usage.get("completion_tokens") or _estimate_tokens(output))
    total = int(usage.get("total_tokens") or prompt + completion)
    return {"prompt": prompt, "completion": completion, "total": total}


def _assistant_model_gateway_config(current_store: MemoryStore) -> dict[str, Any]:
    config = _default_model_gateway_config(current_store)
    if config:
        if config.get("provider") != "openai_compatible":
            raise ModelGatewayConfigError("Active model gateway provider is not supported")
        if not config.get("api_key"):
            raise ModelGatewayConfigError("Active model gateway config is missing api_key")
        return config
    if settings.model_gateway_status == "configured":
        return {
            "api_key": settings.model_gateway_api_key,
            "base_url": settings.model_gateway_base_url,
            "default_chat_model": settings.model_gateway_default_chat_model,
            "id": None,
            "provider": "openai_compatible",
            "timeout_seconds": 60,
        }
    raise ModelGatewayConfigError("No active/default model gateway config is configured")


def _assistant_system_context(
    current_store: MemoryStore,
    *,
    product_id: str | None,
) -> dict[str, Any]:
    products = list(current_store.products.values())
    if product_id:
        products = [product for product in products if product["id"] == product_id]
    product_ids = {product["id"] for product in products}
    requirements = [
        requirement
        for requirement in current_store.requirements.values()
        if not product_ids or requirement.get("product_id") in product_ids
    ]
    tasks = [
        task
        for task in current_store.ai_tasks.values()
        if not product_ids or task.get("product_id") in product_ids
    ]
    repositories = [
        repository
        for repository in current_store.product_git_repositories.values()
        if not product_ids or repository.get("product_id") in product_ids
    ]
    default_gateway = _default_model_gateway_config(current_store)
    return {
        "ai_tasks_by_status": _count_by(tasks, "status"),
        "ai_tasks_by_type": _count_by(tasks, "task_type"),
        "ai_tasks_total": len(tasks),
        "git_repositories": [
            {
                "default_branch": repository.get("default_branch"),
                "id": repository["id"],
                "name": repository["name"],
                "provider": repository.get("git_provider", "gitlab"),
                "status": repository.get("status"),
            }
            for repository in repositories[:8]
        ],
        "latest_requirements": [
            {
                "id": requirement["id"],
                "priority": requirement.get("priority"),
                "status": requirement["status"],
                "title": requirement["title"],
            }
            for requirement in sorted(
                requirements,
                key=lambda item: item.get("created_at", ""),
                reverse=True,
            )[:6]
        ],
        "latest_tasks": [
            {
                "id": task["id"],
                "status": task["status"],
                "title": task["title"],
                "type": task["task_type"],
            }
            for task in sorted(tasks, key=lambda item: item.get("created_at", ""), reverse=True)[:8]
        ],
        "model_gateway": {
            "api_key_configured": bool(default_gateway and default_gateway.get("api_key")),
            "chat_model": default_gateway.get("default_chat_model") if default_gateway else None,
            "is_configured": bool(default_gateway) or settings.model_gateway_status == "configured",
            "provider": default_gateway.get("provider") if default_gateway else "openai_compatible",
        },
        "products": [
            {
                "code": product.get("code"),
                "id": product["id"],
                "name": product["name"],
                "status": product.get("status"),
            }
            for product in products[:8]
        ],
        "requirements_by_status": _count_by(requirements, "status"),
        "requirements_total": len(requirements),
    }


def _assistant_chat_messages(
    current_store: MemoryStore,
    payload: AssistantChatRequest,
) -> list[dict[str, str]]:
    user_payload = {
        "context": payload.context,
        "conversation_id": payload.conversation_id,
        "message": payload.message,
        "product_id": payload.product_id,
        "system_context": _assistant_system_context(
            current_store,
            product_id=payload.product_id,
        ),
    }
    return [
        {
            "role": "system",
            "content": (
                "You are AI Brain's assistant for R&D delivery work. Answer in Chinese. "
                "Use system_context to answer questions about AI Brain configuration, "
                "development progress, requirements, tasks, repositories, "
                "and model gateway status. "
                "Return one compact JSON object with string field answer and optional "
                "array field suggestions. Do not include markdown fences."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def _assistant_response_content(content: Any) -> dict[str, Any]:
    parsed: Any = content
    if isinstance(content, str):
        stripped = content.strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {"answer": stripped, "suggestions": []}
    if not isinstance(parsed, dict):
        return {"answer": str(parsed), "suggestions": []}
    answer = parsed.get("answer") or parsed.get("content") or parsed.get("message") or ""
    suggestions = parsed.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = []
    return {
        "answer": str(answer).strip(),
        "suggestions": [str(item).strip() for item in suggestions if str(item).strip()][:4],
    }


def _assistant_conversation_title(message: str) -> str:
    normalized = " ".join(message.strip().split())
    if len(normalized) <= 60:
        return normalized
    return f"{normalized[:57]}..."


def _assistant_conversation_messages(
    current_store: MemoryStore,
    *,
    conversation_id: str,
) -> list[dict[str, Any]]:
    messages = [
        message
        for message in current_store.assistant_messages.values()
        if message.get("conversation_id") == conversation_id
    ]
    return sorted(messages, key=lambda item: item.get("created_at", ""))


def _public_assistant_conversation(conversation: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": conversation["created_at"],
        "id": conversation["id"],
        "last_message_at": conversation.get("last_message_at") or conversation["updated_at"],
        "message_count": int(conversation.get("message_count") or 0),
        "product_id": conversation.get("product_id"),
        "title": conversation["title"],
        "updated_at": conversation["updated_at"],
    }


def _public_assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    public_message = {
        "content": message["content"],
        "conversation_id": message["conversation_id"],
        "created_at": message["created_at"],
        "id": message["id"],
        "role": message["role"],
    }
    if message.get("model"):
        public_message["model"] = message["model"]
    if message.get("suggestions"):
        public_message["suggestions"] = message["suggestions"]
    return public_message


def _assistant_conversation_for_user(
    current_store: MemoryStore,
    *,
    conversation_id: str,
    user_id: str,
) -> dict[str, Any]:
    conversation = current_store.assistant_conversations.get(conversation_id)
    if conversation is None or conversation.get("user_id") != user_id:
        raise api_error(404, "NOT_FOUND", "Assistant conversation not found")
    return conversation


def _ensure_assistant_conversation(
    current_store: MemoryStore,
    *,
    conversation_id: str | None,
    message: str,
    product_id: str | None,
    user: dict[str, Any],
    now: str,
) -> dict[str, Any]:
    user_id = user["id"]
    if conversation_id:
        existing = current_store.assistant_conversations.get(conversation_id)
        if existing is not None:
            if existing.get("user_id") != user_id:
                raise api_error(404, "NOT_FOUND", "Assistant conversation not found")
            if (
                product_id
                and existing.get("product_id")
                and existing.get("product_id") != product_id
            ):
                raise api_error(400, "VALIDATION_ERROR", "Conversation product_id does not match")
            conversation = dict(existing)
            if product_id and not conversation.get("product_id"):
                conversation["product_id"] = product_id
            conversation["updated_at"] = now
            if not _uses_repository_context(current_store):
                current_store.assistant_conversations[conversation_id] = conversation
            return conversation
        resolved_id = conversation_id
    else:
        resolved_id = current_store.new_id("conversation")
    conversation = {
        "created_at": now,
        "id": resolved_id,
        "last_message_at": now,
        "message_count": 0,
        "product_id": product_id,
        "title": _assistant_conversation_title(message),
        "updated_at": now,
        "user_id": user_id,
    }
    if not _uses_repository_context(current_store):
        current_store.assistant_conversations[resolved_id] = conversation
    return conversation


def _append_assistant_message(
    current_store: MemoryStore,
    *,
    content: str,
    conversation: dict[str, Any],
    now: str,
    role: str,
    user_id: str,
    model: str | None = None,
    suggestions: list[str] | None = None,
) -> dict[str, Any]:
    message = {
        "content": content,
        "conversation_id": conversation["id"],
        "created_at": now,
        "id": current_store.new_id("assistant_message"),
        "model": model,
        "product_id": conversation.get("product_id"),
        "role": role,
        "suggestions": suggestions or [],
        "user_id": user_id,
    }
    if not _uses_repository_context(current_store):
        current_store.assistant_messages[message["id"]] = message
    conversation["last_message_at"] = now
    conversation["message_count"] = int(conversation.get("message_count") or 0) + 1
    conversation["updated_at"] = now
    return message


def _call_model_gateway_for_assistant_chat(
    current_store: MemoryStore,
    *,
    payload: AssistantChatRequest,
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = _assistant_model_gateway_config(current_store)
    provider = config["provider"]
    model = config["default_chat_model"]
    messages = _assistant_chat_messages(current_store, payload)
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
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Assistant response is missing choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise ValueError("Assistant response is missing message")
        assistant_output = _assistant_response_content(message.get("content"))
        if not assistant_output["answer"]:
            raise ValueError("Assistant response is missing answer")
        latency_ms = int((perf_counter() - started) * 1000)
        log = _model_gateway_log(
            current_store,
            purpose="assistant_chat",
            provider=provider,
            model=model,
            config_id=config["id"],
            tokens=_openai_usage_tokens(
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
        prompt_tokens = _estimate_tokens(messages)
        log = _model_gateway_log(
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
        raise ModelGatewayCallError(log) from exc


def _openai_embedding_usage_tokens(
    usage: Any,
    *,
    inputs: list[str],
) -> dict[str, int]:
    if not isinstance(usage, dict):
        prompt = _estimate_tokens(inputs)
        return {"prompt": prompt, "completion": 0, "total": prompt}
    prompt = int(usage.get("prompt_tokens") or _estimate_tokens(inputs))
    total = int(usage.get("total_tokens") or prompt)
    return {"prompt": prompt, "completion": 0, "total": total}


def _parse_embedding_response(
    response_payload: dict[str, Any],
    *,
    expected_count: int,
) -> list[list[float]]:
    data = response_payload.get("data")
    if not isinstance(data, list) or len(data) != expected_count:
        raise ValueError("Embedding response data count does not match request")
    embeddings_by_index: dict[int, list[float]] = {}
    for fallback_index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError("Embedding response item must be an object")
        index = int(item.get("index", fallback_index))
        embedding = item.get("embedding")
        if not isinstance(embedding, list):
            raise ValueError("Embedding response item is missing embedding")
        vector = [float(value) for value in embedding]
        if len(vector) != settings.vector_dimension:
            raise ValueError("Embedding dimension does not match configured vector dimension")
        embeddings_by_index[index] = vector
    return [embeddings_by_index[index] for index in range(expected_count)]


def _model_gateway_embedding_config(current_store: MemoryStore) -> dict[str, Any]:
    config = _default_model_gateway_config(current_store)
    if config:
        return _model_gateway_embedding_runtime_config(config)
    if settings.model_gateway_status == "configured":
        return {
            "api_key": settings.model_gateway_api_key,
            "base_url": settings.model_gateway_base_url,
            "default_embedding_model": settings.model_gateway_default_embedding_model,
            "embedding_connection_mode": "reuse_chat",
            "embedding_dimension": settings.vector_dimension,
            "id": None,
            "provider": "openai_compatible",
            "timeout_seconds": 60,
        }
    raise ModelGatewayConfigError(
        "No active/default model gateway config is configured",
        current_step="model_gateway_config_invalid",
    )


def _call_openai_compatible_embeddings(
    current_store: MemoryStore,
    *,
    config: dict[str, Any],
    inputs: list[str],
) -> tuple[list[list[float]], dict[str, Any]]:
    provider = config["provider"]
    model = config["default_embedding_model"]
    config_id = config["id"]
    body = {"model": model, "input": inputs}
    request = UrlRequest(
        _model_gateway_embeddings_url(config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        embeddings = _parse_embedding_response(response_payload, expected_count=len(inputs))
        latency_ms = int((perf_counter() - started) * 1000)
        log = _model_gateway_log(
            current_store,
            purpose="knowledge_embedding",
            provider=provider,
            model=model,
            config_id=config_id,
            tokens=_openai_embedding_usage_tokens(
                response_payload.get("usage"),
                inputs=inputs,
            ),
            latency_ms=latency_ms,
            status="succeeded",
        )
        return embeddings, log
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
        prompt_tokens = _estimate_tokens(inputs)
        log = _model_gateway_log(
            current_store,
            purpose="knowledge_embedding",
            provider=provider,
            model=model,
            config_id=config_id,
            tokens={"prompt": prompt_tokens, "completion": 0, "total": prompt_tokens},
            latency_ms=latency_ms,
            status="failed",
            error="Model gateway embedding request failed",
        )
        raise ModelGatewayCallError(log) from exc


def _call_model_gateway_embeddings(
    current_store: MemoryStore,
    inputs: list[str],
) -> list[list[float]]:
    embeddings, _context = _call_model_gateway_embeddings_with_context(current_store, inputs)
    return embeddings


def _embedding_context_from_config(
    config: dict[str, Any],
    embeddings: list[list[float]],
) -> dict[str, Any]:
    dimension = len(embeddings[0]) if embeddings else config.get("embedding_dimension")
    context = {
        "embedding_dimension": dimension,
        "embedding_model": config["default_embedding_model"],
    }
    if config.get("id"):
        context["embedding_config_id"] = config["id"]
    return context


def _call_model_gateway_embeddings_with_context(
    current_store: MemoryStore,
    inputs: list[str],
) -> tuple[list[list[float]], dict[str, Any]]:
    config = _model_gateway_embedding_config(current_store)
    embeddings, _log = _call_openai_compatible_embeddings(
        current_store,
        config=config,
        inputs=inputs,
    )
    return embeddings, _embedding_context_from_config(config, embeddings)


def _call_openai_compatible_model_gateway(
    current_store: MemoryStore,
    *,
    config: dict[str, Any],
    task: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = config["provider"]
    model = config["default_chat_model"]
    config_id = config["id"]
    messages = _model_gateway_messages(current_store, task)
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
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
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        output = _parse_model_gateway_output(response_payload, task)
        latency_ms = int((perf_counter() - started) * 1000)
        log = _model_gateway_log(
            current_store,
            task=task,
            provider=provider,
            model=model,
            config_id=config_id,
            tokens=_openai_usage_tokens(
                response_payload.get("usage"),
                messages=messages,
                output=output,
            ),
            latency_ms=latency_ms,
            status="succeeded",
        )
        return output, log
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
        prompt_tokens = _estimate_tokens(messages)
        log = _model_gateway_log(
            current_store,
            task=task,
            provider=provider,
            model=model,
            config_id=config_id,
            tokens={"prompt": prompt_tokens, "completion": 0, "total": prompt_tokens},
            latency_ms=latency_ms,
            status="failed",
            error="Model gateway request failed",
        )
        raise ModelGatewayCallError(log) from exc


def _call_model_gateway_for_task(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = _default_model_gateway_config(current_store)
    if config:
        if config.get("provider") != "openai_compatible":
            raise ModelGatewayConfigError("Active model gateway provider is not supported")
        if not config.get("api_key"):
            raise ModelGatewayConfigError("Active model gateway config is missing api_key")
        return _call_openai_compatible_model_gateway(current_store, config=config, task=task)

    if settings.model_gateway_status == "configured":
        return _call_openai_compatible_model_gateway(
            current_store,
            config={
                "api_key": settings.model_gateway_api_key,
                "base_url": settings.model_gateway_base_url,
                "default_chat_model": settings.model_gateway_default_chat_model,
                "id": None,
                "provider": "openai_compatible",
                "timeout_seconds": 60,
            },
            task=task,
        )

    raise ModelGatewayConfigError(
        "No active/default model gateway config is configured",
        current_step="model_gateway_config_invalid",
    )


def _code_review_executor_payload(
    current_store: MemoryStore,
    task: dict[str, Any],
) -> dict[str, Any]:
    snapshot_id = str(task.get("input_json", {}).get("gitlab_mr_snapshot_id") or "")
    snapshot = current_store.gitlab_mr_snapshots.get(snapshot_id)
    technical_solution = (
        current_store.ai_tasks.get(snapshot["technical_solution_task_id"])
        if snapshot is not None
        else None
    )
    return {
        "task": {
            "id": task["id"],
            "title": task["title"],
            "task_type": task["task_type"],
            "input_json": current_store.snapshot(task.get("input_json", {})),
            "product_context": _public_product_context(task.get("product_context")),
            "requirement_snapshot": current_store.snapshot(task.get("requirement_snapshot", {})),
        },
        "gitlab_mr_snapshot": current_store.snapshot(snapshot),
        "technical_solution_task": current_store.snapshot(technical_solution),
    }


def _code_review_executor_metadata(executor: Any | None = None) -> tuple[str, str]:
    executor_type = (
        str(getattr(executor, "executor_type", "")).strip()
        if executor is not None
        else ""
    ) or settings.code_review_executor_type
    executor_name = (
        str(getattr(executor, "executor_name", "")).strip()
        if executor is not None
        else ""
    ) or settings.code_review_executor_name
    return executor_type, executor_name


def _should_use_model_gateway_code_review_executor(
    current_store: MemoryStore,
    *,
    executor_type: str,
) -> bool:
    if executor_type != "claude_code_skill" or settings.code_review_executor_command.strip():
        return False
    if _default_model_gateway_config(current_store) is not None:
        return True
    return settings.model_gateway_status == "configured"


def _coerce_code_review_executor_result(
    raw_result: Any,
    *,
    executor_type: str,
    executor_name: str,
) -> CodeReviewExecutorResult:
    if isinstance(raw_result, CodeReviewExecutorResult):
        output = raw_result.output
        model_log = raw_result.model_log
    elif isinstance(raw_result, tuple):
        output = raw_result[0]
        model_log = raw_result[1] if len(raw_result) > 1 else None
    else:
        output = raw_result
        model_log = None
    try:
        normalized = normalize_code_review_output(
            output,
            executor_type=executor_type,
            executor_name=executor_name,
        )
    except (TypeError, ValueError) as exc:
        raise CodeReviewExecutorError(
            "Code review executor returned invalid output",
            executor_type=executor_type,
            executor_name=executor_name,
            stage="parse_output",
            retryable=True,
        ) from exc
    return CodeReviewExecutorResult(
        output=normalized,
        executor=normalized["executor"],
        model_log=model_log,
    )


def _call_configured_code_review_executor(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
) -> CodeReviewExecutorResult:
    injected_executor = getattr(app.state, "code_review_executor", None)
    payload = _code_review_executor_payload(current_store, task)
    if injected_executor is not None:
        executor_type, executor_name = _code_review_executor_metadata(injected_executor)
        try:
            raw_result = injected_executor.execute(
                current_store=current_store,
                task=task,
                payload=payload,
            )
        except CodeReviewExecutorError:
            raise
        except Exception as exc:
            raise CodeReviewExecutorError(
                "Code review executor failed",
                executor_type=executor_type,
                executor_name=executor_name,
                stage="execute",
                retryable=True,
            ) from exc
        return _coerce_code_review_executor_result(
            raw_result,
            executor_type=executor_type,
            executor_name=executor_name,
        )

    executor_type, executor_name = _code_review_executor_metadata()
    if executor_type == "model_gateway" or _should_use_model_gateway_code_review_executor(
        current_store,
        executor_type=executor_type,
    ):
        executor_type = "model_gateway"
        try:
            output, model_log = _call_model_gateway_for_task(current_store, task=task)
        except ModelGatewayConfigError as exc:
            raise CodeReviewExecutorError(
                str(exc),
                executor_type=executor_type,
                executor_name=executor_name,
                stage=exc.current_step,
                retryable=False,
            ) from exc
        except ModelGatewayCallError as exc:
            raise CodeReviewExecutorError(
                "Code review executor failed",
                executor_type=executor_type,
                executor_name=executor_name,
                stage="execute",
                retryable=True,
                model_log=exc.log,
            ) from exc
        return _coerce_code_review_executor_result(
            (output, model_log),
            executor_type=executor_type,
            executor_name=executor_name,
        )

    if executor_type == "claude_code_skill":
        executor = ExternalCommandCodeReviewExecutor(
            command=settings.code_review_executor_command,
            executor_type=executor_type,
            executor_name=executor_name,
            timeout_seconds=settings.code_review_executor_timeout_seconds,
        )
        return executor.execute(current_store=current_store, task=task, payload=payload)

    raise CodeReviewExecutorError(
        "Unsupported code review executor type",
        executor_type=executor_type,
        executor_name=executor_name,
        stage="configure",
        retryable=False,
    )


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise api_error(401, "UNAUTHORIZED", "Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = parse_access_token(token, secret_key=settings.app_secret_key)
    except TokenError as exc:
        code = "TOKEN_EXPIRED" if str(exc) == "token_expired" else "UNAUTHORIZED"
        raise api_error(401, code, "Invalid bearer token") from exc

    user = request.app.state.user_repository.get_by_username(str(payload.get("username", "")))
    if user is None:
        raise api_error(401, "UNAUTHORIZED", "User is inactive or missing")
    return user


CurrentUser = Depends(get_current_user)


def _long_memory_status_payload() -> dict[str, Any]:
    configured = settings.long_memory_status == "configured"
    return {
        "api_key_configured": bool(settings.gbrain_api_key),
        "base_url_configured": bool(settings.gbrain_base_url),
        "capabilities": [
            "hybrid_retrieval",
            "answer_synthesis",
            "knowledge_graph",
        ]
        if configured
        else [],
        "connector": "gbrain",
        "fallback_retriever": "postgres_pgvector",
        "status": settings.long_memory_status,
    }


@app.get("/api/long-memory/status")
def get_long_memory_status(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(_long_memory_status_payload(), get_trace_id(request))


def _seeded_users_enabled() -> bool:
    return settings.allow_seeded_users or settings.app_env in {"local", "test", "development"}


@app.post("/api/auth/login")
def login(request: Request, payload: LoginRequest) -> dict[str, Any]:
    if payload.username in SEEDED_USERS and not _seeded_users_enabled():
        raise api_error(
            403,
            "DEFAULT_CREDENTIALS_DISABLED",
            "Seeded local users are disabled outside local environments",
        )
    user = request.app.state.user_repository.get_by_username(payload.username)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise api_error(401, "INVALID_CREDENTIALS", "Invalid username or password")

    access_token = create_access_token(
        {"sub": user["id"], "username": user["username"], "roles": user["roles"]},
        secret_key=settings.app_secret_key,
        expires_in_seconds=settings.access_token_expire_seconds,
    )
    return envelope(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_seconds,
            "user": _public_user(user),
        },
        get_trace_id(request),
    )


@app.get("/api/auth/me")
def me(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    return envelope(_public_user(user), get_trace_id(request))


@app.post("/api/auth/logout")
def logout(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    return envelope({"success": True}, get_trace_id(request))


@app.get("/api/auth/roles")
def list_roles(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    return _list_payload(list_role_definitions(), trace_id=get_trace_id(request))


@app.get("/api/users")
def list_users(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    items = request.app.state.user_repository.list_users()
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/users")
def create_user(
    request: Request,
    payload: UserCreateRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    username = _ensure_non_blank(payload.username, "username")
    display_name = _ensure_non_blank(payload.display_name, "display_name")
    password = _ensure_non_blank(payload.password, "password")
    _ensure_enum(payload.status, USER_STATUSES, "user status")
    _ensure_roles(payload.roles)
    try:
        created = request.app.state.user_repository.create_user(
            display_name=display_name,
            password=password,
            roles=payload.roles,
            status=payload.status,
            username=username,
        )
    except ValueError as exc:
        if str(exc) == "user_exists":
            raise api_error(409, "USER_EXISTS", "User already exists") from exc
        raise
    return envelope(created, get_trace_id(request))


@app.patch("/api/users/{user_id}")
def patch_user(
    user_id: str,
    request: Request,
    payload: UserPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    updates = payload.model_dump(exclude_unset=True)
    if "display_name" in updates:
        updates["display_name"] = _ensure_non_blank(updates["display_name"], "display_name")
    if "password" in updates:
        updates["password"] = _ensure_non_blank(updates["password"], "password")
    if "roles" in updates:
        _ensure_roles(updates["roles"])
    if "status" in updates:
        _ensure_enum(updates["status"], USER_STATUSES, "user status")
    updated = request.app.state.user_repository.update_user(user_id, updates)
    if updated is None:
        raise api_error(404, "NOT_FOUND", "User not found")
    return envelope(updated, get_trace_id(request))


@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    if user_id == user["id"]:
        raise api_error(409, "RESOURCE_IN_USE", "Current user cannot be deleted")
    deleted = request.app.state.user_repository.delete_user(user_id)
    if not deleted:
        raise api_error(404, "NOT_FOUND", "User not found")
    return envelope({"deleted": True, "id": user_id}, get_trace_id(request))


@app.get("/api/brain-apps")
def list_brain_apps(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    current_store = store(request)
    repository = _brain_app_query_repository(current_store)
    brain_apps = (
        _brain_app_rows_from_repository(repository)
        if repository is not None
        else current_store.brain_apps
    )
    items = sorted(brain_apps.values(), key=lambda item: item["code"])
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/brain-apps/{brain_app_id}")
def get_brain_app(
    brain_app_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    repository = _brain_app_query_repository(current_store)
    brain_apps = (
        _brain_app_rows_from_repository(repository)
        if repository is not None
        else current_store.brain_apps
    )
    brain_app = brain_apps.get(brain_app_id)
    if brain_app is None:
        brain_app = next(
            (
                item
                for item in brain_apps.values()
                if item["id"] == brain_app_id or item["code"] == brain_app_id
            ),
            None,
        )
    if brain_app is None:
        raise api_error(404, "NOT_FOUND", "Brain app not found")
    return envelope(brain_app, get_trace_id(request))


@app.get("/api/products")
def list_products(
    request: Request,
    active_only: bool = False,
    code: str | None = None,
    name: str | None = None,
    owner_team: str | None = None,
    status: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "asc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _ensure_enum(status, PRODUCT_STATUSES, "product status")
    current_store = store(request)
    repository = _product_config_query_repository(current_store)
    if repository is not None:
        items = repository.list_products(active_only=active_only)
    else:
        items = sorted(
            current_store.products.values(),
            key=lambda item: (item.get("display_order", 0), item["code"]),
        )
        if active_only:
            items = [item for item in items if item.get("status") == "active"]
    items = [_product_list_projection(item, current_store) for item in items]
    if status:
        items = [item for item in items if item.get("status") == status]
    items = [item for item in items if _list_text_matches(item, code, ("code", "id"))]
    items = [item for item in items if _list_text_matches(item, name, ("name",))]
    items = [item for item in items if _list_text_matches(item, owner_team, ("owner_team",))]
    items = _sort_list_items(
        items,
        allowed_fields={
            "code",
            "current_version_name",
            "display_order",
            "id",
            "module_count",
            "name",
            "owner_team",
            "status",
        },
        default_sort_by="display_order",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginated_list_payload(
        items,
        page=page,
        page_size=page_size,
        trace_id=get_trace_id(request),
    )


@app.post("/api/products")
def create_product(
    request: Request,
    payload: ProductRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    name = _ensure_non_blank(payload.name, "name")
    _ensure_enum(payload.status, PRODUCT_STATUSES, "product status")
    product_id = current_store.new_id("product")
    code = _ensure_non_blank(payload.code or product_id, "code")
    _ensure_unique_value(
        current_store.products,
        field="code",
        value=code,
        conflict_code="PRODUCT_CODE_EXISTS",
        message="Product code already exists",
    )
    product = {
        "id": product_id,
        "code": code,
        "name": name,
        "description": payload.description,
        "owner_team": payload.owner_team,
        "status": payload.status,
        "display_order": payload.display_order,
    }
    if not _uses_repository_context(current_store):
        current_store.products[product_id] = product
    audit_event = _record_audit_event(
        current_store,
        event_type="product.created",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    _save_product_config_record(
        current_store,
        "products",
        product,
        audit_event=audit_event,
    )
    return envelope(product, get_trace_id(request))


@app.get("/api/products/{product_id}")
def get_product(
    product_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    repository = _product_config_query_repository(current_store)
    if repository is not None:
        product = repository.get_product(product_id)
        if product is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        return envelope(product, get_trace_id(request))
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    return envelope(product, get_trace_id(request))


@app.patch("/api/products/{product_id}")
def patch_product(
    product_id: str,
    request: Request,
    payload: ProductPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    updates = _payload_updates(payload)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "code" in updates:
        updates["code"] = _ensure_non_blank(updates["code"], "code")
        _ensure_unique_value(
            current_store.products,
            field="code",
            value=updates["code"],
            conflict_code="PRODUCT_CODE_EXISTS",
            message="Product code already exists",
            exclude_id=product_id,
        )
    if "status" in updates:
        _ensure_enum(updates["status"], PRODUCT_STATUSES, "product status")
    product = {**product, **updates}
    if not _uses_repository_context(current_store):
        current_store.products[product_id] = product
    audit_event = _record_audit_event(
        current_store,
        event_type="product.updated",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    _save_product_config_record(
        current_store,
        "products",
        product,
        audit_event=audit_event,
    )
    return envelope(product, get_trace_id(request))


@app.delete("/api/products/{product_id}")
def delete_product(
    product_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    has_dependencies = any(
        item["product_id"] == product_id
        for collection in [
            current_store.requirements,
            current_store.ai_tasks,
            current_store.bugs,
        ]
        for item in collection.values()
    )
    if has_dependencies:
        raise api_error(409, "RESOURCE_IN_USE", "Product still has related records")
    for collection_name, collection in [
        ("product_versions", current_store.product_versions),
        ("product_modules", current_store.product_modules),
        ("product_git_repositories", current_store.product_git_repositories),
        ("related_systems", current_store.related_systems),
    ]:
        for item_id, item in list(collection.items()):
            if item.get("product_id") == product_id:
                if not _uses_repository_context(current_store):
                    del collection[item_id]
                _delete_product_config_record(current_store, collection_name, item_id)
    if not _uses_repository_context(current_store):
        del current_store.products[product_id]
    audit_event = _record_audit_event(
        current_store,
        event_type="product.deleted",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    _delete_product_config_record(
        current_store,
        "products",
        product_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": product_id}, get_trace_id(request))


@app.get("/api/product-versions")
def list_all_product_versions(
    request: Request,
    active_only: bool = False,
    code: str | None = None,
    name: str | None = None,
    product: str | None = None,
    product_id: str | None = None,
    status: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "asc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _ensure_enum(status, VERSION_STATUSES, "product version status")
    current_store = store(request)
    repository = _postgres_snapshot_repository(current_store)
    if repository is not None:
        items = repository.list_product_version_summaries(active_only=active_only)
    else:
        items = [
            _product_version_summary_projection(version, current_store)
            for version in current_store.product_versions.values()
        ]
        if active_only:
            items = [item for item in items if item.get("status") == "active"]
    if product_id:
        items = [item for item in items if item.get("product_id") == product_id]
    if status:
        items = [item for item in items if item.get("status") == status]
    items = [item for item in items if _list_text_matches(item, code, ("code",))]
    items = [item for item in items if _list_text_matches(item, name, ("name",))]
    items = [
        item
        for item in items
        if _list_text_matches(item, product, ("product_code", "product_name", "product_id"))
    ]
    items = _sort_list_items(
        items,
        allowed_fields={
            "code",
            "created_at",
            "name",
            "product_code",
            "product_name",
            "release_date",
            "start_date",
            "status",
            "updated_at",
        },
        default_sort_by="code",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginated_list_payload(
        items,
        page=page,
        page_size=page_size,
        trace_id=get_trace_id(request),
    )


@app.get("/api/products/{product_id}/versions")
def list_product_versions(
    product_id: str,
    request: Request,
    active_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    repository = _product_config_query_repository(current_store)
    if repository is not None:
        if repository.get_product(product_id) is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        items = repository.list_product_versions(product_id, active_only=active_only)
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    items = [
        item
        for item in current_store.product_versions.values()
        if item["product_id"] == product_id
    ]
    items.sort(key=lambda item: item["code"])
    return _list_payload(items, trace_id=get_trace_id(request), active_only=active_only)


@app.post("/api/products/{product_id}/versions")
def create_product_version(
    product_id: str,
    request: Request,
    payload: ProductVersionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    name = _ensure_non_blank(payload.name, "name")
    _ensure_enum(payload.status, VERSION_STATUSES, "product version status")
    version_id = current_store.new_id("version")
    code = _ensure_non_blank(payload.code or version_id, "code")
    _ensure_unique_value(
        current_store.product_versions,
        field="code",
        value=code,
        conflict_code="PRODUCT_VERSION_CODE_EXISTS",
        message="Product version code already exists",
        scope={"product_id": product_id},
    )
    version = {
        "id": version_id,
        "product_id": product_id,
        "code": code,
        "name": name,
        "description": payload.description,
        "status": payload.status,
        "start_date": payload.start_date,
        "release_date": payload.release_date,
    }
    if not _uses_repository_context(current_store):
        current_store.product_versions[version_id] = version
    audit_event = _record_audit_event(
        current_store,
        event_type="product_version.created",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    _save_product_config_record(
        current_store,
        "product_versions",
        version,
        audit_event=audit_event,
    )
    return envelope(version, get_trace_id(request))


@app.post("/api/product-versions/{version_id}/advance-status")
def advance_product_version_status(
    version_id: str,
    request: Request,
    payload: ProductVersionAdvanceStatusRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    version = current_store.product_versions.get(version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    from_status = version.get("status", "planning")
    target_status = payload.target_status
    _validate_version_status_transition(from_status, target_status)
    impact = _build_version_advance_impact(
        current_store,
        target_status=target_status,
        version_id=version_id,
    )
    blocked_requirements = impact["blocked_requirements"]
    if (
        not payload.preview_only
        and blocked_requirements
        and (target_status == "released" or not payload.force)
    ):
        raise api_error(
            409,
            "PRODUCT_VERSION_STATUS_BLOCKED",
            "Version has requirements that block this status transition",
        )

    response_version = version
    if not payload.preview_only:
        now = datetime.now(UTC).isoformat()
        response_version = {
            **version,
            "status": target_status,
            "updated_at": now,
        }
        if not _uses_repository_context(current_store):
            current_store.product_versions[version_id] = response_version
        for item in impact["updated_requirements"]:
            requirement = current_store.requirements[item["id"]]
            updated_requirement = {
                **requirement,
                "status": item["to_status"],
                "updated_at": now,
            }
            if not _uses_repository_context(current_store):
                current_store.requirements[item["id"]] = updated_requirement
            requirement_audit_event = _record_audit_event(
                current_store,
                event_type="requirement.updated",
                actor_id=user["id"],
                subject_type="requirement",
                subject_id=item["id"],
                payload={
                    "from_status": item["from_status"],
                    "operation": "version_status_advance",
                    "product_id": version["product_id"],
                    "reason": payload.reason,
                    "to_status": item["to_status"],
                    "version_id": version_id,
                    "version_status_from": from_status,
                    "version_status_to": target_status,
                },
            )
            _save_requirement_record(
                current_store,
                updated_requirement,
                audit_event=requirement_audit_event,
            )
        version_audit_event = _record_audit_event(
            current_store,
            event_type="product_version.status_advanced",
            actor_id=user["id"],
            subject_type="product_version",
            subject_id=version_id,
            payload={
                "blocked_requirements": blocked_requirements,
                "force": payload.force,
                "from_status": from_status,
                "reason": payload.reason,
                "target_status": target_status,
                "unchanged_requirements": impact["unchanged_requirements"],
                "updated_requirements": impact["updated_requirements"],
            },
        )
        _save_product_config_record(
            current_store,
            "product_versions",
            response_version,
            audit_event=version_audit_event,
        )

    return envelope(
        {
            **impact,
            "force": payload.force,
            "from_status": from_status,
            "preview_only": payload.preview_only,
            "target_status": target_status,
            "version": _product_version_summary_projection(response_version, current_store),
        },
        get_trace_id(request),
    )


@app.patch("/api/product-versions/{version_id}")
def patch_product_version(
    version_id: str,
    request: Request,
    payload: ProductVersionPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    version = current_store.product_versions.get(version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    updates = _payload_updates(payload)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "code" in updates:
        updates["code"] = _ensure_non_blank(updates["code"], "code")
        _ensure_unique_value(
            current_store.product_versions,
            field="code",
            value=updates["code"],
            conflict_code="PRODUCT_VERSION_CODE_EXISTS",
            message="Product version code already exists",
            exclude_id=version_id,
            scope={"product_id": version["product_id"]},
        )
    if "status" in updates:
        _ensure_enum(updates["status"], VERSION_STATUSES, "product version status")
        if updates["status"] != version.get("status"):
            raise api_error(
                409,
                "PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED",
                "Use the version status advance endpoint to change delivery status",
            )
    version = {**version, **updates}
    if not _uses_repository_context(current_store):
        current_store.product_versions[version_id] = version
    audit_event = _record_audit_event(
        current_store,
        event_type="product_version.updated",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    _save_product_config_record(
        current_store,
        "product_versions",
        version,
        audit_event=audit_event,
    )
    return envelope(version, get_trace_id(request))


@app.delete("/api/product-versions/{version_id}")
def delete_product_version(
    version_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    version = current_store.product_versions.get(version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if (
        any(item["version_id"] == version_id for item in current_store.requirements.values())
        or any(item.get("version_id") == version_id for item in current_store.ai_tasks.values())
        or any(item.get("version_id") == version_id for item in current_store.bugs.values())
    ):
        raise api_error(409, "RESOURCE_IN_USE", "Product version still has related records")
    if not _uses_repository_context(current_store):
        del current_store.product_versions[version_id]
    audit_event = _record_audit_event(
        current_store,
        event_type="product_version.deleted",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    _delete_product_config_record(
        current_store,
        "product_versions",
        version_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": version_id}, get_trace_id(request))


@app.get("/api/products/{product_id}/modules")
def list_product_modules(
    product_id: str,
    request: Request,
    active_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    repository = _product_config_query_repository(current_store)
    if repository is not None:
        if repository.get_product(product_id) is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        items = repository.list_product_modules(product_id, active_only=active_only)
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    items = [
        item
        for item in current_store.product_modules.values()
        if item["product_id"] == product_id
    ]
    items.sort(key=lambda item: (item.get("display_order", 0), item["code"]))
    return _list_payload(items, trace_id=get_trace_id(request), active_only=active_only)


@app.post("/api/products/{product_id}/modules")
def create_product_module(
    product_id: str,
    request: Request,
    payload: ProductModuleRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    name = _ensure_non_blank(payload.name, "name")
    _ensure_enum(payload.status, MODULE_STATUSES, "product module status")
    module_id = current_store.new_id("module")
    code = _ensure_non_blank(payload.code or module_id, "code")
    _ensure_unique_value(
        current_store.product_modules,
        field="code",
        value=code,
        conflict_code="PRODUCT_MODULE_CODE_EXISTS",
        message="Product module code already exists",
        scope={"product_id": product_id},
    )
    module = {
        "id": module_id,
        "product_id": product_id,
        "code": code,
        "name": name,
        "description": payload.description,
        "owner_team": payload.owner_team,
        "status": payload.status,
        "display_order": payload.display_order,
    }
    if not _uses_repository_context(current_store):
        current_store.product_modules[module_id] = module
    audit_event = _record_audit_event(
        current_store,
        event_type="product_module.created",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
    )
    _save_product_config_record(
        current_store,
        "product_modules",
        module,
        audit_event=audit_event,
    )
    return envelope(module, get_trace_id(request))


@app.patch("/api/product-modules/{module_id}")
def patch_product_module(
    module_id: str,
    request: Request,
    payload: ProductModulePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    module = current_store.product_modules.get(module_id)
    if module is None:
        raise api_error(404, "NOT_FOUND", "Product module not found")
    updates = _payload_updates(payload)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "code" in updates:
        updates["code"] = _ensure_non_blank(updates["code"], "code")
        _ensure_unique_value(
            current_store.product_modules,
            field="code",
            value=updates["code"],
            conflict_code="PRODUCT_MODULE_CODE_EXISTS",
            message="Product module code already exists",
            exclude_id=module_id,
            scope={"product_id": module["product_id"]},
        )
    if "status" in updates:
        _ensure_enum(updates["status"], MODULE_STATUSES, "product module status")
    module = {**module, **updates}
    if not _uses_repository_context(current_store):
        current_store.product_modules[module_id] = module
    audit_event = _record_audit_event(
        current_store,
        event_type="product_module.updated",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
    )
    _save_product_config_record(
        current_store,
        "product_modules",
        module,
        audit_event=audit_event,
    )
    return envelope(module, get_trace_id(request))


@app.delete("/api/product-modules/{module_id}")
def delete_product_module(
    module_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    module = current_store.product_modules.get(module_id)
    if module is None:
        raise api_error(404, "NOT_FOUND", "Product module not found")
    if any(
        item["product_id"] == module["product_id"]
        and item.get("module_code") == module["code"]
        for item in [
            *current_store.requirements.values(),
            *current_store.ai_tasks.values(),
            *current_store.bugs.values(),
        ]
    ):
        raise api_error(409, "RESOURCE_IN_USE", "Product module still has related records")
    if not _uses_repository_context(current_store):
        del current_store.product_modules[module_id]
    audit_event = _record_audit_event(
        current_store,
        event_type="product_module.deleted",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
    )
    _delete_product_config_record(
        current_store,
        "product_modules",
        module_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": module_id}, get_trace_id(request))


@app.get("/api/products/{product_id}/git-repositories")
def list_product_git_repositories(
    product_id: str,
    request: Request,
    active_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = store(request)
    repository = _product_config_query_repository(current_store)
    if repository is not None:
        if repository.get_product(product_id) is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        items = repository.list_product_git_repositories(product_id, active_only=active_only)
        public_items = [_public_git_repository(item) for item in items]
        return envelope({"items": public_items, "total": len(public_items)}, get_trace_id(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    items = [
        item
        for item in current_store.product_git_repositories.values()
        if item["product_id"] == product_id
    ]
    items.sort(key=lambda item: item["name"])
    public_items = [_public_git_repository(item) for item in items]
    return _list_payload(public_items, trace_id=get_trace_id(request), active_only=active_only)


@app.post("/api/products/{product_id}/git-repositories")
def create_product_git_repository(
    product_id: str,
    request: Request,
    payload: ProductGitRepositoryRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    name = _ensure_non_blank(payload.name, "name")
    _ensure_enum(payload.status, GIT_REPO_STATUSES, "product Git repository status")
    _validate_git_repository_binding(
        payload.git_provider,
        project_id=payload.project_id,
        project_path=payload.project_path,
        remote_url=payload.remote_url,
    )

    repository_id = current_store.new_id("repo")
    repository = {
        "id": repository_id,
        "product_id": product_id,
        "repo_type": payload.repo_type,
        "name": name,
        "remote_url": payload.remote_url,
        "git_provider": payload.git_provider,
        "project_id": payload.project_id,
        "project_path": payload.project_path,
        "credential_ref": payload.credential_ref,
        "default_branch": payload.default_branch,
        "root_path": payload.root_path,
        "status": payload.status,
    }
    if not _uses_repository_context(current_store):
        current_store.product_git_repositories[repository_id] = repository
    audit_event = _record_audit_event(
        current_store,
        event_type="product_git_repository.created",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
    )
    _save_product_config_record(
        current_store,
        "product_git_repositories",
        repository,
        audit_event=audit_event,
    )
    return envelope(_public_git_repository(repository), get_trace_id(request))


@app.patch("/api/product-git-repositories/{repo_id}")
def patch_product_git_repository(
    repo_id: str,
    request: Request,
    payload: ProductGitRepositoryPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    repository = current_store.product_git_repositories.get(repo_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    updates = _payload_updates(payload)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "status" in updates:
        _ensure_enum(updates["status"], GIT_REPO_STATUSES, "product Git repository status")
    next_provider = updates.get("git_provider", repository["git_provider"])
    next_project_id = updates.get("project_id", repository.get("project_id"))
    next_project_path = updates.get("project_path", repository.get("project_path"))
    next_remote_url = updates.get("remote_url", repository.get("remote_url"))
    _validate_git_repository_binding(
        next_provider,
        project_id=next_project_id,
        project_path=next_project_path,
        remote_url=next_remote_url,
    )
    repository = {**repository, **updates}
    if not _uses_repository_context(current_store):
        current_store.product_git_repositories[repo_id] = repository
    audit_event = _record_audit_event(
        current_store,
        event_type="product_git_repository.updated",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repo_id,
    )
    _save_product_config_record(
        current_store,
        "product_git_repositories",
        repository,
        audit_event=audit_event,
    )
    return envelope(_public_git_repository(repository), get_trace_id(request))


@app.delete("/api/product-git-repositories/{repo_id}")
def delete_product_git_repository(
    repo_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    if repo_id not in current_store.product_git_repositories:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    if not _uses_repository_context(current_store):
        del current_store.product_git_repositories[repo_id]
    audit_event = _record_audit_event(
        current_store,
        event_type="product_git_repository.deleted",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repo_id,
    )
    _delete_product_config_record(
        current_store,
        "product_git_repositories",
        repo_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": repo_id}, get_trace_id(request))


@app.get("/api/system/related-systems")
def list_related_systems(
    request: Request,
    active_only: bool = False,
    product_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    repository = _product_config_query_repository(current_store)
    if repository is not None:
        items = repository.list_related_systems(active_only=active_only, product_id=product_id)
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = sorted(
        (
            item
            for item in current_store.related_systems.values()
            if product_id is None or item.get("product_id") == product_id
        ),
        key=lambda item: (item.get("display_order", 0), item["code"]),
    )
    return _list_payload(items, trace_id=get_trace_id(request), active_only=active_only)


@app.post("/api/system/related-systems")
def create_related_system(
    request: Request,
    payload: RelatedSystemRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    name = _ensure_non_blank(payload.name, "name")
    _ensure_enum(payload.status, RELATED_SYSTEM_STATUSES, "related system status")
    if payload.product_id is not None and payload.product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    system_id = current_store.new_id("system")
    code = _ensure_non_blank(payload.code or system_id, "code")
    _ensure_unique_value(
        current_store.related_systems,
        field="code",
        value=code,
        conflict_code="RELATED_SYSTEM_CODE_EXISTS",
        message="Related system code already exists",
    )
    related_system = {
        "id": system_id,
        "code": code,
        "name": name,
        "description": payload.description,
        "owner_team": payload.owner_team,
        "product_id": payload.product_id,
        "status": payload.status,
        "display_order": payload.display_order,
    }
    if not _uses_repository_context(current_store):
        current_store.related_systems[system_id] = related_system
    audit_event = _record_audit_event(
        current_store,
        event_type="related_system.created",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    _save_product_config_record(
        current_store,
        "related_systems",
        related_system,
        audit_event=audit_event,
    )
    return envelope(related_system, get_trace_id(request))


@app.patch("/api/system/related-systems/{system_id}")
def patch_related_system(
    system_id: str,
    request: Request,
    payload: RelatedSystemPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    related_system = current_store.related_systems.get(system_id)
    if related_system is None:
        raise api_error(404, "NOT_FOUND", "Related system not found")
    updates = _payload_updates(payload)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "code" in updates:
        updates["code"] = _ensure_non_blank(updates["code"], "code")
        _ensure_unique_value(
            current_store.related_systems,
            field="code",
            value=updates["code"],
            conflict_code="RELATED_SYSTEM_CODE_EXISTS",
            message="Related system code already exists",
            exclude_id=system_id,
        )
    if "status" in updates:
        _ensure_enum(updates["status"], RELATED_SYSTEM_STATUSES, "related system status")
    if "product_id" in updates and updates["product_id"] is not None:
        if updates["product_id"] not in current_store.products:
            raise api_error(404, "NOT_FOUND", "Product not found")
    related_system = {**related_system, **updates}
    if not _uses_repository_context(current_store):
        current_store.related_systems[system_id] = related_system
    audit_event = _record_audit_event(
        current_store,
        event_type="related_system.updated",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    _save_product_config_record(
        current_store,
        "related_systems",
        related_system,
        audit_event=audit_event,
    )
    return envelope(related_system, get_trace_id(request))


@app.delete("/api/system/related-systems/{system_id}")
def delete_related_system(
    system_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _product_config_write_store(store(request))
    if system_id not in current_store.related_systems:
        raise api_error(404, "NOT_FOUND", "Related system not found")
    if not _uses_repository_context(current_store):
        del current_store.related_systems[system_id]
    audit_event = _record_audit_event(
        current_store,
        event_type="related_system.deleted",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    _delete_product_config_record(
        current_store,
        "related_systems",
        system_id,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": system_id}, get_trace_id(request))


@app.get("/api/system/model-gateway-configs")
def list_model_gateway_configs(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = _model_gateway_write_store(store(request))
    repository = _model_gateway_query_repository(current_store)
    if repository is not None:
        configs = repository.list_model_gateway_configs()
    else:
        configs = sorted(
            current_store.model_gateway_configs.values(),
            key=lambda item: item["id"],
        )
    items = [
        _public_model_gateway_config(item)
        for item in configs
    ]
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/system/model-gateway-configs/test")
def test_model_gateway_config(
    request: Request,
    payload: ModelGatewayConfigTestRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = _model_gateway_write_store(store(request))
    name = _ensure_non_blank(payload.name, "name")
    base_url = _ensure_non_blank(payload.base_url, "base_url")
    _ensure_enum(
        payload.test_target,
        MODEL_GATEWAY_TEST_TARGETS,
        "model gateway test target",
    )
    test_target = payload.test_target
    should_test_chat = test_target in {"chat", "chat_and_embedding"}
    default_chat_model = (
        _ensure_non_blank(payload.default_chat_model, "default_chat_model")
        if should_test_chat
        else (payload.default_chat_model or "").strip()
    )
    _ensure_enum(payload.provider, MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    _ensure_enum(payload.status, MODEL_GATEWAY_STATUSES, "model gateway status")
    existing_config = None
    if payload.config_id:
        existing_config = current_store.model_gateway_configs.get(payload.config_id)
        if existing_config is None:
            raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    api_key = payload.api_key or (existing_config or {}).get("api_key")
    if should_test_chat and not api_key:
        raise api_error(
            400,
            "MODEL_GATEWAY_CONFIG_INVALID",
            "Model gateway test requires an API key",
        )
    should_test_embedding = test_target in {"chat_and_embedding", "embedding"}
    if should_test_embedding:
        embedding_fields = _normalized_model_gateway_embedding_fields(
            api_key=api_key,
            base_url=base_url,
            default_embedding_model=payload.default_embedding_model,
            embedding_api_key=payload.embedding_api_key,
            embedding_base_url=payload.embedding_base_url,
            embedding_connection_mode=payload.embedding_connection_mode,
            embedding_dimension=payload.embedding_dimension,
            existing_config=existing_config,
        )
    else:
        embedding_fields = _model_gateway_embedding_test_fields(
            default_embedding_model=payload.default_embedding_model,
            embedding_api_key=payload.embedding_api_key,
            embedding_base_url=payload.embedding_base_url,
            embedding_connection_mode=payload.embedding_connection_mode,
            embedding_dimension=payload.embedding_dimension,
            existing_config=existing_config,
        )
    should_test_embedding = (
        should_test_embedding and embedding_fields["embedding_connection_mode"] != "disabled"
    )
    test_config = {
        "api_key": api_key,
        "base_url": base_url,
        "default_chat_model": default_chat_model,
        "id": payload.config_id or "model_gateway_config_test",
        "is_default": False,
        "max_retries": payload.max_retries,
        "name": name,
        "provider": payload.provider,
        "status": payload.status,
        "timeout_seconds": payload.timeout_seconds,
        **embedding_fields,
    }
    chat_result = (
        _test_model_gateway_chat(test_config)
        if should_test_chat
        else _model_gateway_test_skipped(model=default_chat_model)
    )
    embedding_result = (
        _test_model_gateway_embedding(test_config)
        if should_test_embedding
        else _model_gateway_test_skipped(model=embedding_fields["default_embedding_model"] or "")
    )
    result = {
        "chat": chat_result,
        "embedding": embedding_result,
        "ok": bool(chat_result["ok"] and embedding_result["ok"]),
        "test_target": test_target,
    }
    audit_event = _record_audit_event(
        current_store,
        event_type="model_gateway_config.tested",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=payload.config_id,
        payload={
            "chat_status": chat_result["status"],
            "embedding_status": embedding_result["status"],
            "provider": payload.provider,
            "test_target": test_target,
        },
    )
    _save_model_gateway_payload(
        current_store,
        configs=current_store.model_gateway_configs,
        logs=current_store.model_gateway_logs,
        audit_event=audit_event,
    )
    return envelope(result, get_trace_id(request))


@app.post("/api/system/model-gateway-configs")
def create_model_gateway_config(
    request: Request,
    payload: ModelGatewayConfigRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = _model_gateway_write_store(store(request))
    name = _ensure_non_blank(payload.name, "name")
    base_url = _ensure_non_blank(payload.base_url, "base_url")
    default_chat_model = _ensure_non_blank(payload.default_chat_model, "default_chat_model")
    _ensure_enum(payload.provider, MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    _ensure_enum(payload.status, MODEL_GATEWAY_STATUSES, "model gateway status")
    embedding_fields = _normalized_model_gateway_embedding_fields(
        api_key=payload.api_key,
        base_url=base_url,
        default_embedding_model=payload.default_embedding_model,
        embedding_api_key=payload.embedding_api_key,
        embedding_base_url=payload.embedding_base_url,
        embedding_connection_mode=payload.embedding_connection_mode,
        embedding_dimension=payload.embedding_dimension,
    )
    config_id = current_store.new_id("model_gateway_config")
    config = {
        "id": config_id,
        "name": name,
        "provider": payload.provider,
        "base_url": base_url,
        "api_key": payload.api_key,
        "default_chat_model": default_chat_model,
        "timeout_seconds": payload.timeout_seconds,
        "max_retries": payload.max_retries,
        "status": payload.status,
        "is_default": payload.is_default,
        **embedding_fields,
    }
    next_configs = {
        **current_store.model_gateway_configs,
        config_id: config,
    }
    next_configs = _model_gateway_configs_after_default(
        next_configs,
        config_id=config_id,
        is_default=payload.is_default,
    )
    if not _uses_repository_context(current_store):
        current_store.model_gateway_configs = next_configs
    audit_event = _record_audit_event(
        current_store,
        event_type="model_gateway_config.created",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
    )
    _save_model_gateway_payload(
        current_store,
        configs=next_configs,
        logs=current_store.model_gateway_logs,
        audit_event=audit_event,
    )
    return envelope(_public_model_gateway_config(config), get_trace_id(request))


@app.patch("/api/system/model-gateway-configs/{config_id}")
def patch_model_gateway_config(
    config_id: str,
    request: Request,
    payload: ModelGatewayConfigPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = _model_gateway_write_store(store(request))
    config = current_store.model_gateway_configs.get(config_id)
    if config is None:
        raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    updates = _payload_updates(payload)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "base_url" in updates:
        updates["base_url"] = _ensure_non_blank(updates["base_url"], "base_url")
    if "default_chat_model" in updates:
        updates["default_chat_model"] = _ensure_non_blank(
            updates["default_chat_model"],
            "default_chat_model",
        )
    if "default_embedding_model" in updates:
        updates["default_embedding_model"] = _optional_non_blank(
            updates["default_embedding_model"]
        )
    if "embedding_base_url" in updates:
        updates["embedding_base_url"] = _optional_non_blank(updates["embedding_base_url"])
    if "embedding_api_key" in updates:
        updates["embedding_api_key"] = _optional_non_blank(updates["embedding_api_key"])
    if "embedding_connection_mode" in updates:
        _ensure_enum(
            updates["embedding_connection_mode"],
            MODEL_GATEWAY_EMBEDDING_CONNECTION_MODES,
            "embedding connection mode",
        )
    if "embedding_dimension" in updates:
        updates["embedding_dimension"] = _normalize_embedding_dimension(
            updates["embedding_dimension"]
        )
    if "status" in updates:
        _ensure_enum(updates["status"], MODEL_GATEWAY_STATUSES, "model gateway status")
    if "provider" in updates:
        _ensure_enum(updates["provider"], MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    if {
        "default_embedding_model",
        "embedding_api_key",
        "embedding_base_url",
        "embedding_connection_mode",
        "embedding_dimension",
    } & updates.keys():
        embedding_fields = _normalized_model_gateway_embedding_fields(
            api_key=updates.get("api_key", config.get("api_key")),
            base_url=updates.get("base_url", config["base_url"]),
            default_embedding_model=updates.get(
                "default_embedding_model",
                config.get("default_embedding_model"),
            ),
            embedding_api_key=updates.get("embedding_api_key"),
            embedding_base_url=updates.get(
                "embedding_base_url",
                config.get("embedding_base_url"),
            ),
            embedding_connection_mode=updates.get(
                "embedding_connection_mode",
                _embedding_connection_mode(config),
            ),
            embedding_dimension=updates.get(
                "embedding_dimension",
                config.get("embedding_dimension"),
            ),
            existing_config=config,
        )
        updates.update(embedding_fields)
    config = {**config, **updates}
    next_configs = {
        **current_store.model_gateway_configs,
        config_id: config,
    }
    next_configs = _model_gateway_configs_after_default(
        next_configs,
        config_id=config_id,
        is_default=bool(config.get("is_default")),
    )
    if not _uses_repository_context(current_store):
        current_store.model_gateway_configs = next_configs
    audit_event = _record_audit_event(
        current_store,
        event_type="model_gateway_config.updated",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
    )
    _save_model_gateway_payload(
        current_store,
        configs=next_configs,
        logs=current_store.model_gateway_logs,
        audit_event=audit_event,
    )
    return envelope(_public_model_gateway_config(config), get_trace_id(request))


@app.delete("/api/system/model-gateway-configs/{config_id}")
def delete_model_gateway_config(
    config_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = _model_gateway_write_store(store(request))
    if config_id not in current_store.model_gateway_configs:
        raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    next_configs = dict(current_store.model_gateway_configs)
    next_configs.pop(config_id, None)
    if not _uses_repository_context(current_store):
        current_store.model_gateway_configs = next_configs
    audit_event = _record_audit_event(
        current_store,
        event_type="model_gateway_config.deleted",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
    )
    _save_model_gateway_payload(
        current_store,
        configs=next_configs,
        logs=current_store.model_gateway_logs,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": config_id}, get_trace_id(request))


@app.get("/api/model-gateway/logs")
def list_model_gateway_logs(
    request: Request,
    ai_task_id: str | None = None,
    purpose: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = store(request)
    repository = _model_gateway_query_repository(current_store)
    if repository is not None:
        items = repository.list_model_gateway_logs(
            ai_task_id=ai_task_id,
            purpose=purpose,
            status=status,
        )
    else:
        items = list(current_store.model_gateway_logs)
        if ai_task_id:
            items = [item for item in items if item.get("ai_task_id") == ai_task_id]
        if purpose:
            items = [item for item in items if item["purpose"] == purpose]
        if status:
            items = [item for item in items if item["status"] == status]
        items.sort(key=lambda item: item["created_at"], reverse=True)
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/assistant/conversations")
def list_assistant_conversations(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin", "product_owner", "rd_owner", "reviewer", "knowledge_owner"})
    current_store = store(request)
    repository = _assistant_query_repository(current_store)
    if repository is not None:
        conversations = repository.list_assistant_conversations(user_id=user["id"])
    else:
        conversations = [
            conversation
            for conversation in current_store.assistant_conversations.values()
            if conversation.get("user_id") == user["id"]
        ]
    items = [_public_assistant_conversation(conversation) for conversation in conversations]
    items.sort(key=lambda item: item.get("last_message_at") or item["updated_at"], reverse=True)
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/assistant/conversations/{conversation_id}/messages")
def list_assistant_conversation_messages(
    conversation_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin", "product_owner", "rd_owner", "reviewer", "knowledge_owner"})
    current_store = store(request)
    repository = _assistant_query_repository(current_store)
    if repository is not None:
        messages = repository.list_assistant_conversation_messages(
            conversation_id=conversation_id,
            user_id=user["id"],
        )
        if messages is None:
            raise api_error(404, "NOT_FOUND", "Assistant conversation not found")
    else:
        _assistant_conversation_for_user(
            current_store,
            conversation_id=conversation_id,
            user_id=user["id"],
        )
        messages = _assistant_conversation_messages(
            current_store,
            conversation_id=conversation_id,
        )
    items = [_public_assistant_message(message) for message in messages]
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/assistant/chat")
def chat_with_assistant(
    request: Request,
    payload: AssistantChatRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin", "product_owner", "rd_owner", "reviewer", "knowledge_owner"})
    current_store = _assistant_write_store(store(request), user_id=user["id"])
    message = _ensure_non_blank(payload.message, "message")
    normalized_payload = AssistantChatRequest(
        context=payload.context,
        conversation_id=payload.conversation_id,
        message=message,
        product_id=payload.product_id,
    )
    if (
        normalized_payload.product_id
        and normalized_payload.product_id not in current_store.products
    ):
        raise api_error(404, "NOT_FOUND", "Product not found")
    if normalized_payload.conversation_id:
        existing_conversation = current_store.assistant_conversations.get(
            normalized_payload.conversation_id,
        )
        if existing_conversation is not None and existing_conversation.get("user_id") != user["id"]:
            raise api_error(404, "NOT_FOUND", "Assistant conversation not found")
    audit_start_index = len(current_store.audit_events)
    try:
        assistant_output, model_log = _call_model_gateway_for_assistant_chat(
            current_store,
            payload=normalized_payload,
        )
    except ModelGatewayConfigError as exc:
        raise api_error(400, "MODEL_GATEWAY_CONFIG_INVALID", str(exc)) from exc
    except ModelGatewayCallError as exc:
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
        _save_assistant_chat_records(
            current_store,
            conversation=None,
            messages=[],
            model_log=exc.log,
            audit_events=current_store.audit_events[audit_start_index:],
        )
        raise api_error(
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
    now = datetime.now(UTC).isoformat()
    conversation = _ensure_assistant_conversation(
        current_store,
        conversation_id=normalized_payload.conversation_id,
        message=message,
        now=now,
        product_id=normalized_payload.product_id,
        user=user,
    )
    user_message = _append_assistant_message(
        current_store,
        content=message,
        conversation=conversation,
        now=now,
        role="user",
        user_id=user["id"],
    )
    assistant_message = _append_assistant_message(
        current_store,
        content=assistant_output["answer"],
        conversation=conversation,
        model=assistant_output["model"],
        now=now,
        role="assistant",
        suggestions=assistant_output["suggestions"],
        user_id=user["id"],
    )
    current_store.audit(
        event_type="assistant.chat_completed",
        actor_id=user["id"],
        subject_type="assistant_conversation",
        subject_id=conversation["id"],
        payload={
            "latency_ms": assistant_output["latency_ms"],
            "model": assistant_output["model"],
            "model_log_id": model_log["id"],
            "product_id": normalized_payload.product_id,
            "suggestion_count": len(assistant_output["suggestions"]),
        },
    )
    _save_assistant_chat_records(
        current_store,
        conversation=conversation,
        messages=[user_message, assistant_message],
        model_log=model_log,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return envelope(
        {
            "conversation_id": conversation["id"],
            "latency_ms": assistant_output["latency_ms"],
            "message": _public_assistant_message(assistant_message),
            "model": assistant_output["model"],
            "suggestions": assistant_output["suggestions"],
        },
        get_trace_id(request),
    )


@app.post("/api/requirements")
def create_requirement(
    request: Request,
    payload: RequirementRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    title = _ensure_non_blank(payload.title, "title")
    content = _ensure_non_blank(payload.content, "content")
    product = current_store.products.get(payload.product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    _validate_requirement_version(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
    )
    if payload.module_code is not None and not any(
        module["product_id"] == payload.product_id and module["code"] == payload.module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")

    requirement_id = current_store.new_id("requirement")
    requirement = {
        "id": requirement_id,
        "brain_app_id": DEFAULT_BRAIN_APP_ID,
        "title": title,
        "product_id": payload.product_id,
        "version_id": payload.version_id,
        "module_code": payload.module_code,
        "content": content,
        "priority": payload.priority,
        "status": "submitted",
        "created_by": user["id"],
        "task_ids": [],
        "created_at": datetime.now(UTC).isoformat(),
    }
    if not _uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = _record_audit_event(
        current_store,
        event_type="requirement.created",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    _save_requirement_record(current_store, requirement, audit_event=audit_event)
    return envelope(requirement, get_trace_id(request))


@app.post("/api/requirements/batch-schedule")
def batch_schedule_requirements(
    request: Request,
    payload: RequirementBatchScheduleRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    product = current_store.products.get(payload.product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    _validate_requirement_version(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
    )

    batch_id = current_store.new_id("requirement_batch")
    now = datetime.now(UTC).isoformat()
    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_requirement_ids: set[str] = set()

    for requirement_id in payload.requirement_ids:
        if requirement_id in seen_requirement_ids:
            skipped.append(
                {
                    "code": "DUPLICATE_REQUIREMENT",
                    "id": requirement_id,
                    "message": "Requirement was already included in this batch",
                }
            )
            continue
        seen_requirement_ids.add(requirement_id)

        requirement = current_store.requirements.get(requirement_id)
        if requirement is None:
            skipped.append(
                {
                    "code": "NOT_FOUND",
                    "id": requirement_id,
                    "message": "Requirement not found",
                }
            )
            continue
        if requirement.get("product_id") != payload.product_id:
            skipped.append(
                {
                    "code": "PRODUCT_MISMATCH",
                    "id": requirement_id,
                    "message": "Requirement belongs to another product",
                }
            )
            continue

        current_status = _canonical_requirement_status(requirement.get("status"))
        if current_status not in REQUIREMENT_BATCH_SCHEDULABLE_STATUSES:
            skipped.append(
                {
                    "code": "REQUIREMENT_STATE_INVALID",
                    "id": requirement_id,
                    "message": "Only requirement pool or planned requirements can be scheduled",
                }
            )
            continue

        from_version_id = requirement.get("version_id")
        scheduled_requirement = {
            **requirement,
            "status": "planned",
            "updated_at": now,
            "version_id": payload.version_id,
        }
        if not _uses_repository_context(current_store):
            current_store.requirements[requirement_id] = scheduled_requirement
        audit_event = _record_audit_event(
            current_store,
            event_type="requirement.updated",
            actor_id=user["id"],
            subject_type="requirement",
            subject_id=requirement_id,
            payload={
                "batch_id": batch_id,
                "from_status": current_status,
                "from_version_id": from_version_id,
                "operation": "batch_schedule",
                "reason": payload.reason,
                "to_status": "planned",
                "to_version_id": payload.version_id,
            },
        )
        _save_requirement_record(current_store, scheduled_requirement, audit_event=audit_event)
        updated.append(_requirement_summary_projection(scheduled_requirement, current_store))

    batch_audit_event = _record_audit_event(
        current_store,
        event_type="requirement.batch_scheduled",
        actor_id=user["id"],
        subject_type="requirement_batch",
        subject_id=batch_id,
        payload={
            "product_id": payload.product_id,
            "reason": payload.reason,
            "requirement_ids": payload.requirement_ids,
            "skipped": skipped,
            "skipped_count": len(skipped),
            "updated_count": len(updated),
            "updated_ids": [item["id"] for item in updated],
            "version_id": payload.version_id,
        },
    )
    _save_audit_event(current_store, batch_audit_event)
    return envelope(
        {
            "batch_id": batch_id,
            "product_id": payload.product_id,
            "reason": payload.reason,
            "skipped": skipped,
            "skipped_count": len(skipped),
            "updated": updated,
            "updated_count": len(updated),
            "version_id": payload.version_id,
        },
        get_trace_id(request),
    )


@app.get("/api/requirements")
def list_requirements(
    request: Request,
    priority: str | None = None,
    product_id: str | None = None,
    product: str | None = None,
    status: str | None = None,
    title: str | None = None,
    version: str | None = None,
    version_id: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _ensure_enum(priority, {"P0", "P1", "P2"}, "requirement priority")
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    items = [
        _requirement_summary_projection(requirement, read_store)
        for requirement in read_store.requirements.values()
    ]
    if product_id:
        items = [item for item in items if item["product_id"] == product_id]
    if status:
        expected_status = _canonical_requirement_status(status)
        items = [
            item
            for item in items
            if _canonical_requirement_status(item.get("status")) == expected_status
        ]
    if version_id:
        items = [item for item in items if item.get("version_id") == version_id]
    if priority:
        items = [item for item in items if item.get("priority") == priority]
    items = [item for item in items if _list_text_matches(item, title, ("title", "id"))]
    items = [
        item
        for item in items
        if _list_text_matches(item, product, ("product_code", "product_name", "product_id"))
    ]
    items = [
        item
        for item in items
        if _list_text_matches(item, version, ("version_code", "version_name", "version_id"))
    ]
    items = _sort_list_items(
        items,
        allowed_fields={
            "created_at",
            "id",
            "priority",
            "product_code",
            "product_name",
            "status",
            "title",
            "updated_at",
            "version_code",
            "version_name",
        },
        default_sort_by="created_at",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginated_list_payload(
        items,
        page=page,
        page_size=page_size,
        trace_id=get_trace_id(request),
    )


@app.get("/api/requirements/{requirement_id}/full-chain")
def get_requirement_full_chain(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    requirement = read_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    return envelope(
        _requirement_full_chain_payload(read_store, requirement, user=user),
        get_trace_id(request),
    )


@app.get("/api/requirements/{requirement_id}")
def get_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    requirement = read_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    return envelope(requirement, get_trace_id(request))


@app.patch("/api/requirements/{requirement_id}")
def patch_requirement(
    requirement_id: str,
    request: Request,
    payload: RequirementPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    current_status = _canonical_requirement_status(requirement.get("status"))
    if current_status not in {"approved", "planned", "rejected", "submitted"}:
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement cannot be edited")
    updates = _payload_updates(payload)
    if "title" in updates:
        updates["title"] = _ensure_non_blank(updates["title"], "title")
    if "content" in updates:
        updates["content"] = _ensure_non_blank(updates["content"], "content")
    next_product_id = updates.get("product_id", requirement["product_id"])
    next_version_id = updates.get("version_id", requirement["version_id"])
    product = current_store.products.get(next_product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    _validate_requirement_version(
        current_store,
        product_id=next_product_id,
        version_id=next_version_id,
    )
    next_module_code = updates.get("module_code", requirement.get("module_code"))
    if next_module_code is not None and not any(
        module["product_id"] == next_product_id and module["code"] == next_module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")
    requirement = {**requirement, **updates}
    if current_status in {"approved", "planned"} and "version_id" in updates:
        requirement["status"] = "planned" if updates["version_id"] else "approved"
    requirement["updated_at"] = datetime.now(UTC).isoformat()
    if not _uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = _record_audit_event(
        current_store,
        event_type="requirement.updated",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    _save_requirement_record(current_store, requirement, audit_event=audit_event)
    return envelope(requirement, get_trace_id(request))


@app.delete("/api/requirements/{requirement_id}")
def delete_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement.get("task_ids"):
        raise api_error(409, "RESOURCE_IN_USE", "Requirement already has tasks")
    if not _uses_repository_context(current_store):
        del current_store.requirements[requirement_id]
    audit_event = _record_audit_event(
        current_store,
        event_type="requirement.deleted",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    _delete_requirement_record(current_store, requirement_id, audit_event=audit_event)
    return envelope({"deleted": True, "id": requirement_id}, get_trace_id(request))


@app.post("/api/requirements/{requirement_id}/approve")
def approve_requirement(
    requirement_id: str,
    request: Request,
    payload: RequirementDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if _canonical_requirement_status(requirement.get("status")) != "submitted":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not pending approval")
    requirement = {
        **requirement,
        "approval_comment": payload.comment,
        "status": "planned" if requirement.get("version_id") else "approved",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if not _uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = _record_audit_event(
        current_store,
        event_type="requirement.approved",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    _save_requirement_record(current_store, requirement, audit_event=audit_event)
    return envelope(requirement, get_trace_id(request))


@app.post("/api/requirements/{requirement_id}/reject")
def reject_requirement(
    requirement_id: str,
    request: Request,
    payload: RequirementDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = _task_workflow_write_store(store(request))
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if _canonical_requirement_status(requirement.get("status")) != "submitted":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not pending approval")
    rejection_reason = payload.rejection_reason or payload.comment
    if not rejection_reason:
        raise api_error(400, "VALIDATION_ERROR", "rejection_reason is required")
    requirement = {
        **requirement,
        "rejection_reason": rejection_reason,
        "status": "rejected",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if not _uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = _record_audit_event(
        current_store,
        event_type="requirement.rejected",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    _save_requirement_record(current_store, requirement, audit_event=audit_event)
    return envelope(requirement, get_trace_id(request))


@app.post("/api/requirements/{requirement_id}/close")
def close_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if (
        _canonical_requirement_status(requirement.get("status"))
        not in REQUIREMENT_CLOSABLE_STATUSES
    ):
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement cannot be closed")
    active_tasks = [
        current_store.ai_tasks[task_id]
        for task_id in requirement.get("task_ids", [])
        if current_store.ai_tasks[task_id]["status"]
        not in {"completed", "failed", "cancelled"}
    ]
    if active_tasks:
        raise api_error(409, "REQUIREMENT_HAS_ACTIVE_TASKS", "Requirement has active tasks")
    requirement = {
        **requirement,
        "status": "closed",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if not _uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = _record_audit_event(
        current_store,
        event_type="requirement.closed",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    _save_requirement_record(current_store, requirement, audit_event=audit_event)
    return envelope(requirement, get_trace_id(request))


def _product_context(current_store: MemoryStore, requirement: dict[str, Any]) -> dict[str, Any]:
    product = current_store.products[requirement["product_id"]]
    version = (
        current_store.product_versions.get(requirement["version_id"])
        if requirement.get("version_id")
        else None
    )
    module = next(
        (
            item
            for item in current_store.product_modules.values()
            if item["product_id"] == product["id"]
            and item["code"] == requirement.get("module_code")
        ),
        None,
    )
    repositories = [
        _public_git_repository(repository)
        for repository in current_store.product_git_repositories.values()
        if repository["product_id"] == product["id"] and repository.get("status") == "active"
    ]
    related_systems = [
        related_system
        for related_system in current_store.related_systems.values()
        if related_system.get("product_id") == product["id"]
        and related_system.get("status") == "active"
    ]
    return {
        "product": current_store.snapshot(product),
        "version": current_store.snapshot(version) if version else None,
        "module": current_store.snapshot(module) if module else None,
        "repositories": current_store.snapshot({"items": repositories, "total": len(repositories)}),
        "related_systems": current_store.snapshot(
            {"items": related_systems, "total": len(related_systems)}
        ),
    }


@app.post("/api/requirements/{requirement_id}/generate-task")
def generate_task_from_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if _canonical_requirement_status(requirement.get("status")) != "planned":
        raise api_error(
            409,
            "REQUIREMENT_STATE_INVALID",
            "Only planned requirements can generate tasks",
        )

    now = datetime.now(UTC).isoformat()
    task_id = current_store.new_id("task")
    task = {
        "id": task_id,
        "brain_app_id": requirement.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "task_type": "product_detail_design",
        "title": f"产品详细设计：{requirement['title']}",
        "status": "draft",
        "requirement_id": requirement_id,
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "module_code": requirement.get("module_code"),
        "requirement_snapshot": current_store.snapshot(requirement),
        "product_context": _product_context(current_store, requirement),
        "input_json": {},
        "output_json": None,
        "review_ids": [],
        "graph_run_ids": [],
        "current_step": "draft",
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    updated_requirement = {
        **requirement,
        "task_ids": [*requirement.get("task_ids", []), task_id],
    }
    next_status = REQUIREMENT_STATUS_AFTER_TASK_CREATED.get(task["task_type"])
    if next_status:
        _set_requirement_status(updated_requirement, next_status)
    if not _uses_repository_context(current_store):
        current_store.ai_tasks[task_id] = task
        current_store.requirements[requirement_id] = updated_requirement
    audit_event = _record_audit_event(
        current_store,
        event_type="ai_task.created",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
        payload={
            "brain_app_code": task["brain_app_id"],
            "task_type": "product_detail_design",
        },
    )
    _save_requirement_and_ai_task_records(
        current_store,
        requirement=updated_requirement,
        task=task,
        audit_event=audit_event,
    )
    return envelope(
        {"task_id": task_id, "task_type": task["task_type"], "task_status": task["status"]},
        get_trace_id(request),
    )


def _gitlab_base_url(repository: dict[str, Any]) -> str | None:
    remote_url = str(repository.get("remote_url") or "").strip()
    if remote_url.startswith("git@") and ":" in remote_url:
        host = remote_url.split("@", 1)[1].split(":", 1)[0]
        return f"https://{host}"
    if remote_url:
        parsed = urlparse(remote_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    configured_base_url = os.getenv("GITLAB_BASE_URL", "").strip()
    return configured_base_url.rstrip("/") if configured_base_url else None


def _credential_ref_env_candidates(credential_ref: str) -> list[str]:
    if credential_ref.startswith("env:"):
        return [credential_ref.removeprefix("env:").strip()]
    normalized = credential_ref.removeprefix("secret://").removeprefix("secret/")
    env_name = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").upper()
    if not env_name:
        return []
    candidates = [env_name]
    if not env_name.endswith("_TOKEN"):
        candidates.append(f"{env_name}_TOKEN")
    if "GITLAB" in env_name and "READONLY" in env_name:
        candidates.append("GITLAB_READONLY_TOKEN")
    return candidates


def _credential_ref_token(
    credential_ref: str,
    *,
    fallback_env_names: list[str],
) -> str | None:
    credential_ref = credential_ref.strip()
    if credential_ref and not credential_ref.startswith(("env:", "secret://", "secret/")):
        return credential_ref
    for env_name in _credential_ref_env_candidates(credential_ref):
        token = os.getenv(env_name, "").strip()
        if token:
            return token
    for env_name in fallback_env_names:
        token = os.getenv(env_name, "").strip()
        if token:
            return token
    return None


def _gitlab_access_token(repository: dict[str, Any]) -> str | None:
    credential_ref = str(repository.get("credential_ref") or "").strip()
    return _credential_ref_token(
        credential_ref,
        fallback_env_names=["GITLAB_READONLY_TOKEN"],
    )


def _gitlab_project_key(repository: dict[str, Any]) -> str:
    project_key = repository.get("project_id") or repository.get("project_path")
    if not project_key:
        raise api_error(
            400,
            "GITLAB_CONFIG_INVALID",
            "GitLab project_id or project_path is required",
        )
    return str(project_key)


def _gitlab_request_json(base_url: str, token: str, path: str) -> dict[str, Any]:
    request = UrlRequest(
        f"{base_url.rstrip('/')}{path}",
        headers={
            "Accept": "application/json",
            "PRIVATE-TOKEN": token,
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise api_error(404, "GITLAB_MR_NOT_FOUND", "GitLab merge request not found") from exc
        if exc.code == 403:
            raise api_error(403, "FORBIDDEN", "GitLab merge request is not accessible") from exc
        if exc.code in {408, 429} or exc.code >= 500:
            raise api_error(
                503,
                "DEVOPS_SOURCE_UNAVAILABLE",
                "GitLab API source unavailable",
            ) from exc
        raise api_error(exc.code, "GITLAB_REQUEST_FAILED", "GitLab API request failed") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise api_error(503, "DEVOPS_SOURCE_UNAVAILABLE", "GitLab API source unavailable") from exc


def _summarize_gitlab_change(change: dict[str, Any]) -> dict[str, Any]:
    diff_lines = str(change.get("diff") or "").splitlines()
    additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return {
        "path": change.get("new_path") or change.get("old_path") or "-",
        "additions": additions,
        "deletions": deletions,
    }


def _gitlab_changes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    changes = payload.get("changes")
    if isinstance(changes, list):
        return [item for item in changes if isinstance(item, dict)]
    diffs = payload.get("diffs")
    if isinstance(diffs, list):
        return [item for item in diffs if isinstance(item, dict)]
    return []


def _real_gitlab_preview(repository: dict[str, Any], mr_iid: int) -> dict[str, Any]:
    base_url = _gitlab_base_url(repository)
    if not base_url:
        raise api_error(
            400,
            "GITLAB_CONFIG_INVALID",
            "GitLab repository remote_url or GITLAB_BASE_URL is required",
        )
    token = _gitlab_access_token(repository)
    if not token:
        raise api_error(
            400,
            "GITLAB_CREDENTIAL_UNAVAILABLE",
            "GitLab readonly credential is not available",
        )
    encoded_project = quote(_gitlab_project_key(repository), safe="")
    mr_path = f"/api/v4/projects/{encoded_project}/merge_requests/{mr_iid}"
    changes_path = f"{mr_path}/changes"
    mr = _gitlab_request_json(base_url, token, mr_path)
    changes_payload = _gitlab_request_json(base_url, token, changes_path)
    changes_summary = [
        _summarize_gitlab_change(change)
        for change in _gitlab_changes(changes_payload)
    ]
    diff_refs = mr.get("diff_refs") if isinstance(mr.get("diff_refs"), dict) else {}
    base_sha = diff_refs.get("base_sha") or diff_refs.get("start_sha") or mr.get("sha")
    head_sha = diff_refs.get("head_sha") or mr.get("sha")
    project_path = repository.get("project_path") or str(repository.get("project_id") or "")
    return {
        "repository_id": repository["id"],
        "project_id": repository.get("project_id"),
        "project_path": project_path,
        "mr_iid": int(mr.get("iid") or mr_iid),
        "title": mr.get("title") or f"MR !{mr_iid}",
        "author": mr.get("author") or {},
        "source_branch": mr.get("source_branch"),
        "target_branch": mr.get("target_branch"),
        "base_sha": base_sha,
        "head_sha": head_sha,
        "diff_refs": diff_refs,
        "changed_file_count": len(changes_summary),
        "changed_files_summary": changes_summary,
        "web_url": mr.get("web_url"),
        "writeback_allowed": False,
    }


def _gitlab_preview(repository: dict[str, Any], mr_iid: int) -> dict[str, Any]:
    return _real_gitlab_preview(repository, mr_iid)


def _github_base_url(repository: dict[str, Any]) -> str | None:
    configured_base_url = os.getenv("GITHUB_BASE_URL", "").strip()
    if configured_base_url:
        return configured_base_url.rstrip("/")
    remote_url = str(repository.get("remote_url") or "").strip()
    host = ""
    if remote_url.startswith("git@") and ":" in remote_url:
        host = remote_url.split("@", 1)[1].split(":", 1)[0]
    elif remote_url:
        parsed = urlparse(remote_url)
        host = parsed.netloc
    if host in {"github.com", "www.github.com"}:
        return "https://api.github.com"
    if host:
        return f"https://{host}/api/v3"
    return "https://api.github.com"


def _github_access_token(repository: dict[str, Any]) -> str | None:
    credential_ref = str(repository.get("credential_ref") or "").strip()
    return _credential_ref_token(
        credential_ref,
        fallback_env_names=["GITHUB_READONLY_TOKEN", "GITHUB_TOKEN"],
    )


def _clean_repository_path(value: str) -> str:
    cleaned = value.strip().strip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    return cleaned


def _github_repository_path(repository: dict[str, Any]) -> str:
    project_path = _clean_repository_path(str(repository.get("project_path") or ""))
    if project_path and not project_path.startswith("Users/") and len(project_path.split("/")) == 2:
        return project_path

    remote_url = str(repository.get("remote_url") or "").strip()
    candidate = ""
    if remote_url.startswith("git@") and ":" in remote_url:
        candidate = remote_url.split(":", 1)[1]
    elif remote_url:
        parsed = urlparse(remote_url)
        candidate = parsed.path
    candidate = _clean_repository_path(candidate)
    if len(candidate.split("/")) == 2:
        return candidate
    raise api_error(
        400,
        "GITHUB_CONFIG_INVALID",
        "GitHub repository owner/repo path is required",
    )


def _github_request_json(base_url: str, token: str, path: str) -> dict[str, Any] | list[Any]:
    request = UrlRequest(
        f"{base_url.rstrip('/')}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise api_error(404, "GITHUB_PR_NOT_FOUND", "GitHub pull request not found") from exc
        if exc.code == 403:
            raise api_error(403, "FORBIDDEN", "GitHub pull request is not accessible") from exc
        if exc.code in {408, 429} or exc.code >= 500:
            raise api_error(
                503,
                "DEVOPS_SOURCE_UNAVAILABLE",
                "GitHub API source unavailable",
            ) from exc
        raise api_error(exc.code, "GITHUB_REQUEST_FAILED", "GitHub API request failed") from exc
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise api_error(503, "DEVOPS_SOURCE_UNAVAILABLE", "GitHub API source unavailable") from exc


def _summarize_github_file(file_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": file_item.get("filename") or "-",
        "additions": int(file_item.get("additions") or 0),
        "deletions": int(file_item.get("deletions") or 0),
    }


def _github_pull_request_summary(
    repository: dict[str, Any],
    *,
    owner_repo: str,
    pull_request: dict[str, Any],
) -> dict[str, Any]:
    user = pull_request.get("user") if isinstance(pull_request.get("user"), dict) else {}
    head = pull_request.get("head") if isinstance(pull_request.get("head"), dict) else {}
    base = pull_request.get("base") if isinstance(pull_request.get("base"), dict) else {}
    return {
        "author": {
            "username": user.get("login") or "-",
            "name": user.get("name") or user.get("login") or "-",
        },
        "base_sha": base.get("sha") or pull_request.get("base_sha"),
        "created_at": pull_request.get("created_at"),
        "head_sha": head.get("sha") or pull_request.get("head_sha"),
        "number": int(pull_request.get("number") or 0),
        "project_path": owner_repo,
        "repository_id": repository["id"],
        "source_branch": head.get("ref"),
        "state": pull_request.get("state"),
        "target_branch": base.get("ref"),
        "title": pull_request.get("title") or f"PR #{pull_request.get('number')}",
        "updated_at": pull_request.get("updated_at"),
        "web_url": pull_request.get("html_url"),
        "writeback_allowed": False,
    }


def _real_github_pull_requests(
    repository: dict[str, Any],
    *,
    state: str,
    limit: int,
) -> list[dict[str, Any]]:
    base_url = _github_base_url(repository)
    if not base_url:
        raise api_error(
            400,
            "GITHUB_CONFIG_INVALID",
            "GitHub repository remote_url or GITHUB_BASE_URL is required",
        )
    token = _github_access_token(repository)
    if not token:
        raise api_error(
            400,
            "GITHUB_CREDENTIAL_UNAVAILABLE",
            "GitHub readonly credential is not available",
        )
    owner_repo = _github_repository_path(repository)
    encoded_owner_repo = quote(owner_repo, safe="/")
    pull_requests = _github_request_json(
        base_url,
        token,
        f"/repos/{encoded_owner_repo}/pulls?state={state}&per_page={limit}",
    )
    if not isinstance(pull_requests, list):
        raise api_error(503, "DEVOPS_SOURCE_UNAVAILABLE", "GitHub API source unavailable")
    return [
        _github_pull_request_summary(
            repository,
            owner_repo=owner_repo,
            pull_request=item,
        )
        for item in pull_requests
        if isinstance(item, dict)
    ]


def _github_pull_requests(
    repository: dict[str, Any],
    *,
    state: str,
    limit: int,
) -> list[dict[str, Any]]:
    return _real_github_pull_requests(repository, state=state, limit=limit)


def _real_github_preview(repository: dict[str, Any], pr_number: int) -> dict[str, Any]:
    base_url = _github_base_url(repository)
    if not base_url:
        raise api_error(
            400,
            "GITHUB_CONFIG_INVALID",
            "GitHub repository remote_url or GITHUB_BASE_URL is required",
        )
    token = _github_access_token(repository)
    if not token:
        raise api_error(
            400,
            "GITHUB_CREDENTIAL_UNAVAILABLE",
            "GitHub readonly credential is not available",
        )
    owner_repo = _github_repository_path(repository)
    encoded_owner_repo = quote(owner_repo, safe="/")
    pr_path = f"/repos/{encoded_owner_repo}/pulls/{pr_number}"
    files_path = f"{pr_path}/files?per_page=100"
    pr = _github_request_json(base_url, token, pr_path)
    files_payload = _github_request_json(base_url, token, files_path)
    if not isinstance(pr, dict) or not isinstance(files_payload, list):
        raise api_error(503, "DEVOPS_SOURCE_UNAVAILABLE", "GitHub API source unavailable")
    user = pr.get("user") if isinstance(pr.get("user"), dict) else {}
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
    base_sha = base.get("sha") or pr.get("base_sha")
    head_sha = head.get("sha") or pr.get("head_sha")
    return {
        "repository_id": repository["id"],
        "project_id": repository.get("project_id"),
        "project_path": owner_repo,
        "mr_iid": int(pr.get("number") or pr_number),
        "title": pr.get("title") or f"PR #{pr_number}",
        "author": {
            "username": user.get("login") or "-",
            "name": user.get("name") or user.get("login") or "-",
        },
        "source_branch": head.get("ref"),
        "target_branch": base.get("ref"),
        "base_sha": base_sha,
        "head_sha": head_sha,
        "diff_refs": {"base_sha": base_sha, "head_sha": head_sha},
        "changed_file_count": len(files_payload),
        "changed_files_summary": [
            _summarize_github_file(file_item)
            for file_item in files_payload
            if isinstance(file_item, dict)
        ],
        "web_url": pr.get("html_url"),
        "writeback_allowed": False,
    }


def _github_preview(repository: dict[str, Any], pr_number: int) -> dict[str, Any]:
    return _real_github_preview(repository, pr_number)


def _diff_payload(preview: dict[str, Any]) -> str:
    return json.dumps(
        {
            "mr_iid": preview["mr_iid"],
            "base_sha": preview["base_sha"],
            "head_sha": preview["head_sha"],
            "files": preview["changed_files_summary"],
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _ensure_gitlab_snapshot_context(
    *,
    repository: dict[str, Any],
    requirement: dict[str, Any],
    technical_solution: dict[str, Any],
) -> None:
    if repository["product_id"] != requirement["product_id"]:
        _raise_gitlab_context_mismatch(
            "GitLab repository binding and requirement must belong to the same product"
        )
    if technical_solution["requirement_id"] != requirement["id"]:
        _raise_gitlab_context_mismatch(
            "Technical solution task must be derived from the snapshot requirement"
        )
    if technical_solution["product_id"] != requirement["product_id"]:
        _raise_gitlab_context_mismatch(
            "Technical solution task and requirement must belong to the same product"
        )
    if technical_solution["version_id"] != requirement["version_id"]:
        _raise_gitlab_context_mismatch(
            "Technical solution task and requirement must belong to the same version"
        )


def _ensure_confirmed_technical_solution_task(
    current_store: MemoryStore,
    *,
    requirement: dict[str, Any],
    technical_solution_task_id: Any,
) -> dict[str, Any]:
    technical_solution = current_store.ai_tasks.get(str(technical_solution_task_id))
    if (
        technical_solution is None
        or technical_solution["task_type"] != "technical_solution"
        or technical_solution["status"] != "completed"
    ):
        raise api_error(
            400,
            "TECHNICAL_SOLUTION_NOT_CONFIRMED",
            "Task requires a confirmed technical solution",
        )
    _ensure_task_matches_requirement(
        technical_solution,
        requirement,
        source_label="Technical solution",
    )
    return technical_solution


def _create_code_review_source_snapshot(
    current_store: MemoryStore,
    *,
    repository: dict[str, Any],
    requirement: dict[str, Any],
    mr_iid: int,
    preview: dict[str, Any],
    payload: GitLabSnapshotRequest,
    user: dict[str, Any],
    event_prefix: str,
    diff_storage_prefix: str,
) -> dict[str, Any]:
    diff_payload = _diff_payload(preview)
    diff_size_bytes = len(diff_payload.encode())
    diff_limit_bytes = 204_800
    changed_file_count = len(preview["changed_files_summary"])
    changed_file_limit = 50
    file_diff_line_limit = 2_000
    if changed_file_count > changed_file_limit:
        audit_event = current_store.audit(
            event_type=f"{event_prefix}.snapshot_failed",
            actor_id=user["id"],
            subject_type="product_git_repository",
            subject_id=repository["id"],
            payload={
                "changed_file_count": changed_file_count,
                "changed_file_limit": changed_file_limit,
                "diff_limit_bytes": diff_limit_bytes,
                "diff_size_bytes": diff_size_bytes,
                "mr_iid": mr_iid,
                "reason": "changed_file_count_too_large",
                "requirement_id": payload.requirement_id,
                "technical_solution_task_id": payload.technical_solution_task_id,
            },
        )
        _save_gitlab_review_snapshot_record(
            current_store,
            snapshot=None,
            audit_event=audit_event,
        )
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")
    oversized_file = next(
        (
            item
            for item in preview["changed_files_summary"]
            if int(item.get("additions") or 0) + int(item.get("deletions") or 0)
            > file_diff_line_limit
        ),
        None,
    )
    if oversized_file:
        file_diff_line_count = int(oversized_file.get("additions") or 0) + int(
            oversized_file.get("deletions") or 0
        )
        audit_event = current_store.audit(
            event_type=f"{event_prefix}.snapshot_failed",
            actor_id=user["id"],
            subject_type="product_git_repository",
            subject_id=repository["id"],
            payload={
                "diff_limit_bytes": diff_limit_bytes,
                "diff_size_bytes": diff_size_bytes,
                "file_diff_line_count": file_diff_line_count,
                "file_diff_line_limit": file_diff_line_limit,
                "file_path": oversized_file.get("path") or "-",
                "mr_iid": mr_iid,
                "reason": "single_file_diff_too_large",
                "requirement_id": payload.requirement_id,
                "technical_solution_task_id": payload.technical_solution_task_id,
            },
        )
        _save_gitlab_review_snapshot_record(
            current_store,
            snapshot=None,
            audit_event=audit_event,
        )
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")
    if diff_size_bytes > diff_limit_bytes:
        audit_event = current_store.audit(
            event_type=f"{event_prefix}.snapshot_failed",
            actor_id=user["id"],
            subject_type="product_git_repository",
            subject_id=repository["id"],
            payload={
                "diff_limit_bytes": diff_limit_bytes,
                "diff_size_bytes": diff_size_bytes,
                "mr_iid": mr_iid,
                "reason": "diff_too_large",
                "requirement_id": payload.requirement_id,
                "technical_solution_task_id": payload.technical_solution_task_id,
            },
        )
        _save_gitlab_review_snapshot_record(
            current_store,
            snapshot=None,
            audit_event=audit_event,
        )
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")

    snapshot_hash = hashlib.sha256(diff_payload.encode()).hexdigest()
    existing_snapshot = next(
        (
            snapshot
            for snapshot in current_store.gitlab_mr_snapshots.values()
            if snapshot.get("repository_id") == repository["id"]
            and snapshot.get("snapshot_hash") == snapshot_hash
        ),
        None,
    )
    if existing_snapshot is not None:
        audit_event = current_store.audit(
            event_type=f"{event_prefix}.snapshot_reused",
            actor_id=user["id"],
            subject_type="gitlab_mr_snapshot",
            subject_id=existing_snapshot["id"],
            payload={
                "repository_id": repository["id"],
                "mr_iid": mr_iid,
                "requirement_id": payload.requirement_id,
                "technical_solution_task_id": payload.technical_solution_task_id,
            },
        )
        _save_gitlab_review_snapshot_record(
            current_store,
            snapshot=None,
            audit_event=audit_event,
        )
        return existing_snapshot

    snapshot_id = current_store.new_id("snapshot")
    snapshot = {
        "id": snapshot_id,
        "repository_id": repository["id"],
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "project_id": preview["project_id"],
        "project_path": preview["project_path"],
        "mr_iid": mr_iid,
        "title": preview["title"],
        "author": preview["author"],
        "source_branch": preview["source_branch"],
        "target_branch": preview["target_branch"],
        "base_sha": preview["base_sha"],
        "head_sha": preview["head_sha"],
        "diff_refs": preview["diff_refs"],
        "changed_files_summary": preview["changed_files_summary"],
        "diff_storage_ref": f"memory://{diff_storage_prefix}/{snapshot_id}",
        "diff_size_bytes": diff_size_bytes,
        "diff_limit_bytes": diff_limit_bytes,
        "snapshot_hash": snapshot_hash,
        "requirement_id": payload.requirement_id,
        "technical_solution_task_id": payload.technical_solution_task_id,
        "created_by": user["id"],
        "created_at": datetime.now(UTC).isoformat(),
        "source_provider": repository.get("git_provider", "gitlab"),
        "writeback_allowed": False,
    }
    current_store.gitlab_mr_snapshots[snapshot_id] = snapshot
    audit_event = current_store.audit(
        event_type=f"{event_prefix}.snapshotted",
        actor_id=user["id"],
        subject_type="gitlab_mr_snapshot",
        subject_id=snapshot_id,
        payload={"repository_id": repository["id"], "mr_iid": mr_iid},
    )
    _save_gitlab_review_snapshot_record(
        current_store,
        snapshot=snapshot,
        audit_event=audit_event,
    )
    return snapshot


def _ensure_confirmed_release_readiness_task(
    current_store: MemoryStore,
    *,
    requirement: dict[str, Any],
    release_readiness_task_id: Any,
) -> dict[str, Any]:
    release_readiness = current_store.ai_tasks.get(str(release_readiness_task_id))
    if (
        release_readiness is None
        or release_readiness["task_type"] != "release_readiness"
        or release_readiness["status"] != "completed"
    ):
        raise api_error(
            400,
            "RELEASE_READINESS_NOT_CONFIRMED",
            "Task requires a confirmed release readiness task",
        )
    _ensure_task_matches_requirement(
        release_readiness,
        requirement,
        source_label="Release readiness",
    )
    return release_readiness


def _collection_snapshot(
    current_store: MemoryStore,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    return current_store.snapshot({"items": items, "total": len(items)})


def _source_task_context(current_store: MemoryStore, task: dict[str, Any]) -> dict[str, Any]:
    return current_store.snapshot(
        {
            "id": task["id"],
            "task_type": task["task_type"],
            "title": task["title"],
            "status": task["status"],
            "summary": (task.get("output_json") or {}).get("summary"),
            "output": task.get("output_json"),
        }
    )


def _matching_bugs_for_task_context(
    current_store: MemoryStore,
    task: dict[str, Any],
    *,
    include_closed: bool = False,
) -> list[dict[str, Any]]:
    bugs = []
    for bug in current_store.bugs.values():
        if bug["product_id"] != task["product_id"]:
            continue
        if bug.get("version_id") not in {None, task["version_id"]}:
            continue
        if bug.get("requirement_id") not in {None, task["requirement_id"]}:
            continue
        if not include_closed and bug["status"] == "closed":
            continue
        bugs.append(bug)
    bugs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return bugs


def _matching_jenkins_releases(
    current_store: MemoryStore,
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    releases = [
        release
        for release in current_store.jenkins_release_records.values()
        if release.get("product_id") == task["product_id"]
        and release.get("version_id") == task["version_id"]
    ]
    releases.sort(
        key=lambda item: (
            item.get("deployed_at") or item.get("created_at") or "",
            item.get("updated_at") or "",
        ),
        reverse=True,
    )
    return releases


def _matching_online_log_metrics(
    current_store: MemoryStore,
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    module_code = task.get("module_code")
    metrics = []
    for metric in current_store.online_log_metrics.values():
        if metric.get("product_id") != task["product_id"]:
            continue
        if module_code is not None and metric.get("module_code") not in {None, module_code}:
            continue
        metrics.append(metric)
    metrics.sort(
        key=lambda item: (
            item.get("window_start") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return metrics


def _matching_gitlab_daily_code_metrics(
    current_store: MemoryStore,
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    product_repository_ids = {
        repository["id"]
        for repository in current_store.product_git_repositories.values()
        if repository["product_id"] == task["product_id"]
    }
    metrics = [
        metric
        for metric in current_store.gitlab_daily_code_metrics.values()
        if metric.get("product_id") == task["product_id"]
        and metric.get("repository_id") in product_repository_ids
    ]
    metrics.sort(
        key=lambda item: (
            item.get("metric_date") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return metrics


def _release_readiness_context(
    current_store: MemoryStore,
    *,
    requirement: dict[str, Any],
    technical_solution: dict[str, Any],
) -> dict[str, Any]:
    task_context = {
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "module_code": requirement.get("module_code"),
        "requirement_id": requirement["id"],
    }
    return {
        "source_technical_solution": _source_task_context(current_store, technical_solution),
        "bugs": _collection_snapshot(
            current_store,
            _matching_bugs_for_task_context(current_store, task_context),
        ),
        "jenkins_releases": _collection_snapshot(
            current_store,
            _matching_jenkins_releases(current_store, task_context),
        ),
        "online_log_metrics": _collection_snapshot(
            current_store,
            _matching_online_log_metrics(current_store, task_context),
        ),
        "gitlab_daily_code_metrics": _collection_snapshot(
            current_store,
            _matching_gitlab_daily_code_metrics(current_store, task_context),
        ),
    }


def _post_release_analysis_context(
    current_store: MemoryStore,
    *,
    requirement: dict[str, Any],
    release_readiness: dict[str, Any],
) -> dict[str, Any]:
    task_context = {
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "module_code": requirement.get("module_code"),
        "requirement_id": requirement["id"],
    }
    return {
        "source_release_readiness": _source_task_context(current_store, release_readiness),
        "bugs": _collection_snapshot(
            current_store,
            _matching_bugs_for_task_context(current_store, task_context, include_closed=True),
        ),
        "jenkins_releases": _collection_snapshot(
            current_store,
            _matching_jenkins_releases(current_store, task_context),
        ),
        "online_log_metrics": _collection_snapshot(
            current_store,
            _matching_online_log_metrics(current_store, task_context),
        ),
    }


@app.get("/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview")
def preview_gitlab_mr(
    repository_id: str,
    mr_iid: int,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"reviewer", "rd_owner"})
    current_store = _product_config_write_store(store(request))
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitLab repository binding not found")
    if repository["git_provider"] != "gitlab":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitLab binding")
    preview = _gitlab_preview(repository, mr_iid)
    audit_event = current_store.audit(
        event_type="gitlab_mr.previewed",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
        payload={"mr_iid": mr_iid},
    )
    _save_gitlab_review_snapshot_record(
        current_store,
        snapshot=None,
        audit_event=audit_event,
    )
    return envelope(preview, get_trace_id(request))


@app.post("/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot")
def snapshot_gitlab_mr(
    repository_id: str,
    mr_iid: int,
    request: Request,
    payload: GitLabSnapshotRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"reviewer", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitLab repository binding not found")
    requirement = current_store.requirements.get(payload.requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    technical_solution = current_store.ai_tasks.get(payload.technical_solution_task_id)
    if (
        technical_solution is None
        or technical_solution["task_type"] != "technical_solution"
        or technical_solution["status"] != "completed"
    ):
        raise api_error(
            400,
            "TECHNICAL_SOLUTION_NOT_CONFIRMED",
            "MR snapshot requires a confirmed technical solution task",
        )
    _ensure_gitlab_snapshot_context(
        repository=repository,
        requirement=requirement,
        technical_solution=technical_solution,
    )

    snapshot = _create_code_review_source_snapshot(
        current_store,
        repository=repository,
        requirement=requirement,
        mr_iid=mr_iid,
        preview=_gitlab_preview(repository, mr_iid),
        payload=payload,
        user=user,
        event_prefix="gitlab_mr",
        diff_storage_prefix="gitlab-mr-diff",
    )
    return envelope(snapshot, get_trace_id(request))


@app.get("/api/devops/github/pull-requests/{repository_id}")
def list_github_pull_requests(
    repository_id: str,
    request: Request,
    state: str = "open",
    limit: int = Query(default=20, ge=1, le=100),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"reviewer", "rd_owner"})
    _ensure_enum(state, {"open", "closed", "all"}, "GitHub pull request state")
    current_store = _product_config_write_store(store(request))
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitHub repository binding not found")
    if repository["git_provider"] != "github":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitHub binding")
    items = _github_pull_requests(repository, state=state, limit=limit)
    audit_event = current_store.audit(
        event_type="github_pr.listed",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
        payload={"limit": limit, "state": state},
    )
    _save_gitlab_review_snapshot_record(
        current_store,
        snapshot=None,
        audit_event=audit_event,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/devops/github/pull-requests/{repository_id}/{pr_number}/preview")
def preview_github_pr(
    repository_id: str,
    pr_number: int,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"reviewer", "rd_owner"})
    current_store = _product_config_write_store(store(request))
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitHub repository binding not found")
    if repository["git_provider"] != "github":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitHub binding")
    preview = _github_preview(repository, pr_number)
    audit_event = current_store.audit(
        event_type="github_pr.previewed",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
        payload={"pr_number": pr_number},
    )
    _save_gitlab_review_snapshot_record(
        current_store,
        snapshot=None,
        audit_event=audit_event,
    )
    return envelope(preview, get_trace_id(request))


@app.post("/api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot")
def snapshot_github_pr(
    repository_id: str,
    pr_number: int,
    request: Request,
    payload: GitLabSnapshotRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"reviewer", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitHub repository binding not found")
    if repository["git_provider"] != "github":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitHub binding")
    requirement = current_store.requirements.get(payload.requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    technical_solution = current_store.ai_tasks.get(payload.technical_solution_task_id)
    if (
        technical_solution is None
        or technical_solution["task_type"] != "technical_solution"
        or technical_solution["status"] != "completed"
    ):
        raise api_error(
            400,
            "TECHNICAL_SOLUTION_NOT_CONFIRMED",
            "PR snapshot requires a confirmed technical solution task",
        )
    _ensure_gitlab_snapshot_context(
        repository=repository,
        requirement=requirement,
        technical_solution=technical_solution,
    )

    snapshot = _create_code_review_source_snapshot(
        current_store,
        repository=repository,
        requirement=requirement,
        mr_iid=pr_number,
        preview=_github_preview(repository, pr_number),
        payload=payload,
        user=user,
        event_prefix="github_pr",
        diff_storage_prefix="github-pr-diff",
    )
    return envelope(snapshot, get_trace_id(request))


@app.get("/api/ai-tasks")
def list_ai_tasks(
    request: Request,
    status: str | None = None,
    task_type: str | None = None,
    product_id: str | None = None,
    requirement_id: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    keyword: str | None = None,
    created_by: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    from_at = _parse_iso_datetime(created_from, "created_from") if created_from else None
    to_at = _parse_iso_datetime(created_to, "created_to") if created_to else None
    task_sort_fields = {
        "created_at",
        "created_by",
        "id",
        "product_id",
        "product_name",
        "status",
        "task_type",
        "title",
        "updated_at",
    }
    _ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "created_at"
    if resolved_sort_by not in task_sort_fields:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    repository = _postgres_snapshot_repository(current_store)
    if repository is not None:
        read_scope = _task_read_scope(user)
        total = repository.count_ai_task_summaries(
            status=status,
            task_type=task_type,
            product_id=product_id,
            requirement_id=requirement_id,
            created_from=from_at,
            created_to=to_at,
            keyword=keyword,
            created_by=created_by,
            read_scope=read_scope,
        )
        items = repository.list_ai_task_summaries(
            status=status,
            task_type=task_type,
            product_id=product_id,
            requirement_id=requirement_id,
            created_from=from_at,
            created_to=to_at,
            keyword=keyword,
            created_by=created_by,
            read_scope=read_scope,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        return envelope(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            get_trace_id(request),
        )
    items = [
        item
        for item in current_store.ai_tasks.values()
        if _can_read_task(user, item)
    ]
    if status:
        items = [item for item in items if item["status"] == status]
    if task_type:
        items = [item for item in items if item["task_type"] == task_type]
    if product_id:
        items = [item for item in items if item["product_id"] == product_id]
    if requirement_id:
        items = [item for item in items if item["requirement_id"] == requirement_id]
    if from_at or to_at:
        filtered_items = []
        for item in items:
            created_at = item.get("created_at") or item.get("updated_at")
            if not created_at:
                continue
            item_created_at = _parse_iso_datetime(str(created_at), "created_at")
            if from_at and item_created_at < from_at:
                continue
            if to_at and item_created_at > to_at:
                continue
            filtered_items.append(item)
        items = filtered_items
    if keyword:
        normalized_keyword = keyword.lower()
        items = [
            item
            for item in items
            if normalized_keyword
            in f"{item.get('id', '')} {item.get('title', '')} {item.get('task_type', '')}".lower()
        ]
    if created_by:
        normalized_created_by = created_by.lower()
        items = [
            item
            for item in items
            if normalized_created_by in str(item.get("created_by", "")).lower()
        ]
    items = [_task_summary_projection(item, current_store) for item in items]
    items = _sort_list_items(
        items,
        allowed_fields=task_sort_fields,
        default_sort_by="created_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    items = items[(resolved_page - 1) * resolved_page_size : resolved_page * resolved_page_size]
    return envelope(
        {
            "items": items,
            "page": resolved_page,
            "page_size": resolved_page_size,
            "total": total,
        },
        get_trace_id(request),
    )


@app.post("/api/ai-tasks")
def create_ai_task(
    request: Request,
    payload: AiTaskRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _task_workflow_write_store(store(request))
    requirement = current_store.requirements.get(payload.requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")

    input_json = current_store.snapshot(payload.input)
    if payload.task_type == "technical_solution":
        _require_roles(user, {"product_owner", "rd_owner"})
        design_task_id = payload.input.get("product_detail_design_task_id")
        design_task = current_store.ai_tasks.get(str(design_task_id))
        if (
            design_task is None
            or design_task["task_type"] != "product_detail_design"
            or design_task["status"] != "completed"
        ):
            raise api_error(
                400,
                "PRODUCT_DETAIL_DESIGN_NOT_CONFIRMED",
                "technical_solution requires a confirmed product detail design task",
            )
        _ensure_task_matches_requirement(
            design_task,
            requirement,
            source_label="Product detail design",
        )
    elif payload.task_type in TECHNICAL_SOLUTION_FOLLOWUP_TASK_TYPES:
        _require_roles(user, {"product_owner", "rd_owner"})
        technical_solution = _ensure_confirmed_technical_solution_task(
            current_store,
            requirement=requirement,
            technical_solution_task_id=payload.input.get("technical_solution_task_id"),
        )
        if payload.task_type == "release_readiness":
            input_json.update(
                _release_readiness_context(
                    current_store,
                    requirement=requirement,
                    technical_solution=technical_solution,
                )
            )
    elif payload.task_type in RELEASE_READINESS_FOLLOWUP_TASK_TYPES:
        _require_roles(user, {"product_owner", "rd_owner"})
        release_readiness = _ensure_confirmed_release_readiness_task(
            current_store,
            requirement=requirement,
            release_readiness_task_id=payload.input.get("release_readiness_task_id"),
        )
        input_json.update(
            _post_release_analysis_context(
                current_store,
                requirement=requirement,
                release_readiness=release_readiness,
            )
        )
    elif payload.task_type == "code_review":
        _require_roles(user, {"reviewer", "rd_owner"})
        snapshot_id = payload.input.get("gitlab_mr_snapshot_id")
        snapshot = current_store.gitlab_mr_snapshots.get(str(snapshot_id))
        if snapshot is None:
            raise api_error(400, "GITLAB_MR_SNAPSHOT_REQUIRED", "code_review requires MR snapshot")
        if snapshot["requirement_id"] != requirement["id"]:
            _raise_gitlab_context_mismatch(
                "code_review requirement must match the GitLab MR snapshot requirement"
            )
        if snapshot["product_id"] != requirement["product_id"]:
            _raise_gitlab_context_mismatch(
                "code_review product must match the GitLab MR snapshot product"
            )
        technical_solution = current_store.ai_tasks.get(snapshot["technical_solution_task_id"])
        if (
            technical_solution is None
            or technical_solution["task_type"] != "technical_solution"
            or technical_solution["status"] != "completed"
        ):
            raise api_error(
                400,
                "TECHNICAL_SOLUTION_NOT_CONFIRMED",
                "code_review requires a confirmed technical solution",
            )
        _ensure_gitlab_snapshot_context(
            repository=current_store.product_git_repositories[snapshot["repository_id"]],
            requirement=requirement,
            technical_solution=technical_solution,
        )
    else:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported task_type")

    if (
        _canonical_requirement_status(requirement.get("status"))
        not in REQUIREMENT_TASK_CREATABLE_STATUSES
    ):
        raise api_error(
            409,
            "REQUIREMENT_STATE_INVALID",
            "Requirement must be in delivery before creating AI tasks",
        )

    now = datetime.now(UTC).isoformat()
    task_id = current_store.new_id("task")
    task = {
        "id": task_id,
        "brain_app_id": requirement.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "task_type": payload.task_type,
        "title": payload.title,
        "status": "draft",
        "requirement_id": requirement["id"],
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "module_code": requirement.get("module_code"),
        "requirement_snapshot": current_store.snapshot(requirement),
        "product_context": _product_context(current_store, requirement),
        "input_json": input_json,
        "output_json": None,
        "review_ids": [],
        "graph_run_ids": [],
        "current_step": "draft",
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    updated_task_ids = list(requirement.get("task_ids", []))
    if task_id not in updated_task_ids:
        updated_task_ids.append(task_id)
    updated_requirement = {
        **requirement,
        "task_ids": updated_task_ids,
    }
    next_status = REQUIREMENT_STATUS_AFTER_TASK_CREATED.get(task["task_type"])
    if next_status:
        _set_requirement_status(updated_requirement, next_status)
    if not _uses_repository_context(current_store):
        current_store.ai_tasks[task_id] = task
        current_store.requirements[requirement["id"]] = updated_requirement
    audit_event = _record_audit_event(
        current_store,
        event_type="ai_task.created",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
        payload={
            "brain_app_code": task["brain_app_id"],
            "task_type": payload.task_type,
        },
    )
    _save_requirement_and_ai_task_records(
        current_store,
        requirement=updated_requirement,
        task=task,
        audit_event=audit_event,
    )
    return envelope(task, get_trace_id(request))


def _create_code_review_report(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
    output: dict[str, Any],
) -> dict[str, Any]:
    snapshot_id = task["input_json"]["gitlab_mr_snapshot_id"]
    report_id = current_store.new_id("report")
    report = {
        "id": report_id,
        "task_id": task["id"],
        "gitlab_mr_snapshot_id": snapshot_id,
        "summary": output["summary"],
        "risk_level": output["risk_level"],
        "findings": output["findings"],
        "executor": output["executor"],
        "status": "pending_review",
        "review_id": None,
        "archived_at": None,
        "gitlab_writeback_performed": False,
    }
    if not _uses_repository_context(current_store):
        current_store.code_review_reports[report_id] = report
    task["code_review_report_id"] = report_id
    return report


def _confirm_code_review_report(current_store: MemoryStore, task: dict[str, Any]) -> None:
    if task["task_type"] != "code_review":
        return
    report_id = task.get("code_review_report_id")
    if not report_id:
        return
    report = current_store.code_review_reports[report_id]
    output = task.get("output_json") or {}
    for key in ("summary", "risk_level", "findings", "executor"):
        if key in output:
            report[key] = current_store.snapshot(output[key])
    report["status"] = "confirmed"
    report["archived_at"] = datetime.now(UTC).isoformat()


def _bug_suggestion_text(
    suggestion: dict[str, Any],
    key: str,
    fallback: str,
) -> str:
    value = suggestion.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _bug_suggestion_steps(
    suggestion: dict[str, Any],
    *,
    fallback: str = "执行自动化测试建议中的用例并复现失败。",
) -> list[str]:
    raw_steps = suggestion.get("reproduce_steps") or suggestion.get("steps") or []
    if isinstance(raw_steps, str):
        raw_steps = [raw_steps]
    if not isinstance(raw_steps, list):
        raw_steps = []
    steps = [str(step).strip() for step in raw_steps if str(step).strip()]
    if steps:
        return steps
    return [fallback]


def _create_automated_testing_bugs(
    current_store: MemoryStore,
    *,
    actor_id: str,
    task: dict[str, Any],
) -> list[str]:
    if task["task_type"] != "automated_testing":
        return []
    output = task.get("output_json") or {}
    suggestions = output.get("bug_suggestions")
    if not isinstance(suggestions, list):
        return []

    created_bug_ids: list[str] = []
    now = datetime.now(UTC).isoformat()
    for index, raw_suggestion in enumerate(suggestions, start=1):
        suggestion = raw_suggestion if isinstance(raw_suggestion, dict) else {}
        severity = str(suggestion.get("severity") or "major")
        if severity not in BUG_SEVERITIES:
            severity = "major"
        assignee = suggestion.get("assignee")
        bug_id = current_store.new_id("bug")
        bug = {
            "id": bug_id,
            "product_id": task["product_id"],
            "version_id": task["version_id"],
            "module_code": task.get("module_code"),
            "source": "ai_auto_test",
            "title": _bug_suggestion_text(
                suggestion,
                "title",
                f"自动化测试发现 {index}：{task['title']}",
            ),
            "severity": severity,
            "description": _bug_suggestion_text(
                suggestion,
                "description",
                "自动化测试任务确认后生成的缺陷建议。",
            ),
            "status": "open",
            "assignee": assignee if isinstance(assignee, str) else None,
            "related_task_id": task["id"],
            "requirement_id": task["requirement_id"],
            "reproduce_steps": _bug_suggestion_steps(suggestion),
            "evidence": {
                "generated_by_task_type": task["task_type"],
                "suggestion": current_store.snapshot(suggestion),
            },
            "duplicate_of_bug_id": None,
            "created_by": actor_id,
            "created_at": now,
            "updated_at": now,
        }
        current_store.bugs[bug_id] = bug
        created_bug_ids.append(bug_id)
        current_store.audit(
            event_type="bug.created",
            actor_id=actor_id,
            ai_task_id=task["id"],
            subject_type="bug",
            subject_id=bug_id,
            payload={
                "severity": bug["severity"],
                "source": bug["source"],
                "status": bug["status"],
            },
        )

    if created_bug_ids:
        task["generated_bug_ids"] = created_bug_ids
        current_store.audit(
            event_type="automated_testing.bugs_created",
            actor_id=actor_id,
            ai_task_id=task["id"],
            subject_type="ai_task",
            subject_id=task["id"],
            payload={"bug_ids": created_bug_ids},
        )
    return created_bug_ids


def _create_post_release_bugs(
    current_store: MemoryStore,
    *,
    actor_id: str,
    task: dict[str, Any],
) -> list[str]:
    if task["task_type"] != "post_release_analysis":
        return []
    output = task.get("output_json") or {}
    suggestions = output.get("bug_suggestions")
    if not isinstance(suggestions, list):
        return []

    created_bug_ids: list[str] = []
    now = datetime.now(UTC).isoformat()
    for index, raw_suggestion in enumerate(suggestions, start=1):
        suggestion = raw_suggestion if isinstance(raw_suggestion, dict) else {}
        severity = str(suggestion.get("severity") or "major")
        if severity not in BUG_SEVERITIES:
            severity = "major"
        assignee = suggestion.get("assignee")
        bug_id = current_store.new_id("bug")
        bug = {
            "id": bug_id,
            "product_id": task["product_id"],
            "version_id": task["version_id"],
            "module_code": task.get("module_code"),
            "source": "ai_post_release",
            "title": _bug_suggestion_text(
                suggestion,
                "title",
                f"上线后分析发现 {index}：{task['title']}",
            ),
            "severity": severity,
            "description": _bug_suggestion_text(
                suggestion,
                "description",
                "上线后分析任务确认后生成的缺陷建议。",
            ),
            "status": "open",
            "assignee": assignee if isinstance(assignee, str) else None,
            "related_task_id": task["id"],
            "requirement_id": task["requirement_id"],
            "reproduce_steps": _bug_suggestion_steps(
                suggestion,
                fallback="结合上线后观测窗口和日志异常复现问题。",
            ),
            "evidence": {
                "generated_by_task_type": task["task_type"],
                "suggestion": current_store.snapshot(suggestion),
            },
            "duplicate_of_bug_id": None,
            "created_by": actor_id,
            "created_at": now,
            "updated_at": now,
        }
        current_store.bugs[bug_id] = bug
        created_bug_ids.append(bug_id)
        current_store.audit(
            event_type="bug.created",
            actor_id=actor_id,
            ai_task_id=task["id"],
            subject_type="bug",
            subject_id=bug_id,
            payload={
                "severity": bug["severity"],
                "source": bug["source"],
                "status": bug["status"],
            },
        )

    if created_bug_ids:
        task["generated_bug_ids"] = created_bug_ids
        current_store.audit(
            event_type="post_release_analysis.bugs_created",
            actor_id=actor_id,
            ai_task_id=task["id"],
            subject_type="ai_task",
            subject_id=task["id"],
            payload={"bug_ids": created_bug_ids},
        )
    return created_bug_ids


def _ensure_review_decidable(
    current_store: MemoryStore,
    *,
    review_id: str,
    version: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    review = current_store.human_reviews.get(review_id)
    if review is None:
        raise api_error(404, "NOT_FOUND", "Review not found")
    if review["status"] != "pending":
        raise api_error(409, "REVIEW_STATE_INVALID", "Review has already been decided")
    if review["version"] != version:
        raise api_error(409, "REVIEW_VERSION_CONFLICT", "Review version conflict")
    task = current_store.ai_tasks[review["ai_task_id"]]
    return review, task


def _complete_review_with_edited_approval(
    current_store: MemoryStore,
    *,
    actor_id: str,
    edited_content: dict[str, Any],
    review: dict[str, Any],
    review_id: str,
    task: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    task["output_json"] = {**task["output_json"], **edited_content}
    review["status"] = "edited_approved"
    review["edited_content"] = edited_content
    review["decided_by"] = actor_id
    review["decided_at"] = now
    review["updated_at"] = now
    task["status"] = "completed"
    task["updated_at"] = now
    _confirm_code_review_report(current_store, task)
    created_bug_ids = [
        *_create_automated_testing_bugs(current_store, actor_id=actor_id, task=task),
        *_create_post_release_bugs(current_store, actor_id=actor_id, task=task),
    ]
    _advance_requirement_after_task_completed(current_store, task)
    knowledge_deposit = _create_knowledge_deposit(current_store, task)
    checkpoint = _transition_latest_graph_run(
        current_store,
        task=task,
        status="completed",
        current_step="complete_archive",
        state_snapshot={"task_status": task["status"], "review_id": review_id},
    )
    current_store.audit(
        event_type="review.submitted",
        actor_id=actor_id,
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={"decision": "edited_approved"},
    )
    return {
        "review_status": review["status"],
        "task_status": task["status"],
        "bug_ids": created_bug_ids,
        "knowledge_deposit": knowledge_deposit,
        "checkpoint": checkpoint,
    }


def _create_knowledge_deposit(current_store: MemoryStore, task: dict[str, Any]) -> dict[str, Any]:
    deposit_id = current_store.new_id("deposit")
    now = datetime.now(UTC).isoformat()
    deposit = {
        "id": deposit_id,
        "ai_task_id": task["id"],
        "title": f"{task['title']} 知识沉淀",
        "content": task["output_json"]["summary"],
        "status": "pending",
        "knowledge_document_id": None,
        "created_at": now,
        "updated_at": now,
    }
    if not _uses_repository_context(current_store):
        current_store.knowledge_deposits[deposit_id] = deposit
    return deposit


def _graph_runs_for_task(
    current_store: MemoryStore,
    task_id: str,
) -> list[dict[str, Any]]:
    runs = [
        run
        for run in current_store.graph_runs.values()
        if run["ai_task_id"] == task_id
    ]
    runs.sort(key=lambda run: run["started_at"])
    return runs


def _latest_graph_run(
    current_store: MemoryStore,
    task: dict[str, Any],
) -> dict[str, Any] | None:
    graph_run_ids = task.get("graph_run_ids", [])
    if not graph_run_ids:
        return None
    return current_store.graph_runs.get(graph_run_ids[-1])


def _write_graph_checkpoint(
    current_store: MemoryStore,
    *,
    graph_run: dict[str, Any],
    task: dict[str, Any],
    current_step: str,
    state_snapshot: dict[str, Any],
) -> dict[str, Any]:
    checkpoint_id = current_store.new_id("checkpoint")
    snapshot = current_store.snapshot(state_snapshot)
    if graph_run.get("runtime") and "graph_runtime" not in snapshot:
        snapshot["graph_runtime"] = {
            "package": graph_run["runtime"],
            "node_path": current_store.snapshot(graph_run.get("node_path", [])),
        }
    checkpoint = {
        "id": checkpoint_id,
        "graph_run_id": graph_run["id"],
        "ai_task_id": task["id"],
        "current_step": current_step,
        "state_snapshot": current_store.snapshot(snapshot),
        "created_at": datetime.now(UTC).isoformat(),
    }
    if not _uses_repository_context(current_store):
        current_store.graph_checkpoints[checkpoint_id] = checkpoint
    graph_run["checkpoint_id"] = checkpoint_id
    graph_run["current_step"] = current_step
    graph_run["state_snapshot"] = current_store.snapshot(snapshot)
    task["current_step"] = current_step
    task["checkpoint_id"] = checkpoint_id
    return checkpoint


def _start_graph_run(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
    review_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    graph_run_id = current_store.new_id("graph_run")
    graph_state = run_ai_task_graph(task, review_id=review_id)
    graph_run = {
        "id": graph_run_id,
        "ai_task_id": task["id"],
        "task_type": task["task_type"],
        "status": "interrupted",
        "runtime": graph_state["runtime"],
        "node_path": current_store.snapshot(graph_state.get("node_path", [])),
        "current_step": graph_state["current_step"],
        "checkpoint_id": None,
        "state_snapshot": {},
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": None,
    }
    if not _uses_repository_context(current_store):
        current_store.graph_runs[graph_run_id] = graph_run
    task.setdefault("graph_run_ids", []).append(graph_run_id)
    checkpoint = _write_graph_checkpoint(
        current_store,
        graph_run=graph_run,
        task=task,
        current_step=graph_state["current_step"],
        state_snapshot={
            "task_status": graph_state["task_status"],
            "task_type": task["task_type"],
            "review_id": review_id,
            "output_kind": graph_state.get("output_kind"),
            "graph_runtime": graph_state["runtime_metadata"],
        },
    )
    return graph_run, checkpoint


def _transition_latest_graph_run(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
    status: str,
    current_step: str,
    state_snapshot: dict[str, Any],
) -> dict[str, Any] | None:
    graph_run = _latest_graph_run(current_store, task)
    if graph_run is None:
        task["current_step"] = current_step
        return None
    graph_run["status"] = status
    if status in {"completed", "failed", "cancelled"}:
        graph_run["completed_at"] = datetime.now(UTC).isoformat()
    return _write_graph_checkpoint(
        current_store,
        graph_run=graph_run,
        task=task,
        current_step=current_step,
        state_snapshot=state_snapshot,
    )


def _task_detail_projection(current_store: MemoryStore, task: dict[str, Any]) -> dict[str, Any]:
    detail = current_store.snapshot(task)
    detail["product_context"] = _public_product_context(task.get("product_context"))
    reviews = [
        current_store.human_reviews[review_id]
        for review_id in task.get("review_ids", [])
        if review_id in current_store.human_reviews
    ]
    pending_review = next(
        (review for review in reviews if review["status"] == "pending"),
        None,
    )
    graph_runs = _graph_runs_for_task(current_store, task["id"])
    detail["input"] = {
        "task_type": task["task_type"],
        "brain_app_id": task.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "requirement_id": task.get("requirement_id"),
        "requirement_snapshot": task.get("requirement_snapshot"),
        "product_context": _public_product_context(task.get("product_context")),
        **task.get("input_json", {}),
    }
    detail["output"] = task.get("output_json")
    detail["current_step"] = task.get("current_step")
    detail["pending_review"] = current_store.snapshot(pending_review) if pending_review else None
    detail["reviews"] = current_store.snapshot({"items": reviews, "total": len(reviews)})
    detail["graph_runs"] = current_store.snapshot(graph_runs)
    detail["knowledge_deposits"] = {
        "items": [
            deposit
            for deposit in current_store.knowledge_deposits.values()
            if deposit["ai_task_id"] == task["id"]
        ]
    }
    writeback = current_store.mock_writebacks.get(_writeback_idempotency_key(task["id"]))
    detail["mock_issues"] = {
        "status": writeback["status"] if writeback else "not_written",
        "items": current_store.snapshot(writeback["issues"]) if writeback else [],
    }
    return detail


def _task_product_name(current_store: MemoryStore, task: dict[str, Any]) -> str | None:
    product_id = task.get("product_id")
    product = current_store.products.get(str(product_id)) if product_id else None
    if product:
        return product.get("name")
    product_context = task.get("product_context")
    if isinstance(product_context, dict):
        product_snapshot = product_context.get("product")
        if isinstance(product_snapshot, dict):
            return product_snapshot.get("name")
    return None


def _task_summary_projection(task: dict[str, Any], current_store: MemoryStore) -> dict[str, Any]:
    return {
        "id": task["id"],
        "brain_app_id": task.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "task_type": task["task_type"],
        "title": task["title"],
        "status": task["status"],
        "requirement_id": task["requirement_id"],
        "product_id": task["product_id"],
        "product_name": _task_product_name(current_store, task),
        "version_id": task["version_id"],
        "module_code": task.get("module_code"),
        "current_step": task.get("current_step"),
        "created_by": task.get("created_by"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
    }


@app.post("/api/ai-tasks/{task_id}/start")
def start_ai_task(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _task_workflow_write_store(store(request))
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_review_decision_role(user, task)
    is_retry_start = (
        task["status"] == "failed"
        and task.get("current_step") in RETRYABLE_TASK_FAILURE_STEPS
    )
    if task["status"] != "draft" and not is_retry_start:
        raise api_error(409, "TASK_STATE_INVALID", "Task cannot be started from current status")
    audit_start_index = len(current_store.audit_events)
    if is_retry_start:
        current_store.audit(
            event_type="ai_task.retry_started",
            actor_id=user["id"],
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload={"previous_step": task.get("current_step")},
        )

    if task["task_type"] == "code_review":
        try:
            executor_result = _call_configured_code_review_executor(current_store, task=task)
            task["output_json"] = executor_result.output
            model_log = executor_result.model_log
            executor_meta = executor_result.executor
        except CodeReviewExecutorError as exc:
            now = datetime.now(UTC).isoformat()
            task["status"] = "failed"
            task["current_step"] = "code_review_executor_failed"
            task["updated_at"] = now
            if exc.model_log is not None:
                current_store.audit(
                    event_type="model_gateway.called",
                    actor_id="system",
                    ai_task_id=task_id,
                    subject_type="model_gateway_log",
                    subject_id=exc.model_log["id"],
                    payload={
                        "model_log_id": exc.model_log["id"],
                        "provider": exc.model_log["provider"],
                        "model": exc.model_log["model"],
                        "purpose": exc.model_log["purpose"],
                        "status": exc.model_log["status"],
                    },
                )
            payload = {
                "current_step": task["current_step"],
                "executor_name": exc.executor_name,
                "executor_type": exc.executor_type,
                "retryable": exc.retryable,
                "stage": exc.stage,
            }
            if exc.model_log is not None:
                payload["model_log_id"] = exc.model_log["id"]
            current_store.audit(
                event_type="code_review.executor_failed",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="ai_task",
                subject_id=task_id,
                payload=payload,
            )
            current_store.audit(
                event_type="ai_task.failed",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="ai_task",
                subject_id=task_id,
                payload={
                    "current_step": task["current_step"],
                    "reason": "code_review_executor_failed",
                },
            )
            _save_task_state_records(
                current_store,
                task=task,
                model_log=exc.model_log,
                audit_events=current_store.audit_events[audit_start_index:],
            )
            raise api_error(
                502,
                "CODE_REVIEW_EXECUTOR_FAILED",
                "Code review executor failed",
            ) from exc
    else:
        try:
            task["output_json"], model_log = _call_model_gateway_for_task(
                current_store,
                task=task,
            )
        except ModelGatewayConfigError as exc:
            now = datetime.now(UTC).isoformat()
            task["status"] = "failed"
            task["current_step"] = exc.current_step
            task["updated_at"] = now
            current_store.audit(
                event_type="ai_task.failed",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="ai_task",
                subject_id=task_id,
                payload={
                    "current_step": task["current_step"],
                    "reason": "model_gateway_config_invalid",
                },
            )
            _save_task_state_records(
                current_store,
                task=task,
                audit_events=current_store.audit_events[audit_start_index:],
            )
            raise api_error(400, "MODEL_GATEWAY_CONFIG_INVALID", str(exc)) from exc
        except ModelGatewayCallError as exc:
            now = datetime.now(UTC).isoformat()
            task["status"] = "failed"
            task["current_step"] = "model_gateway_failed"
            task["updated_at"] = now
            current_store.audit(
                event_type="model_gateway.called",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="model_gateway_log",
                subject_id=exc.log["id"],
                payload={
                    "model_log_id": exc.log["id"],
                    "provider": exc.log["provider"],
                    "model": exc.log["model"],
                    "purpose": exc.log["purpose"],
                    "status": exc.log["status"],
                },
            )
            current_store.audit(
                event_type="ai_task.failed",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="ai_task",
                subject_id=task_id,
                payload={
                    "current_step": task["current_step"],
                    "reason": "model_gateway_failed",
                },
            )
            _save_task_state_records(
                current_store,
                task=task,
                model_log=exc.log,
                audit_events=current_store.audit_events[audit_start_index:],
            )
            raise api_error(502, "MODEL_GATEWAY_FAILED", "Model gateway request failed") from exc

    now = datetime.now(UTC).isoformat()
    task["status"] = "waiting_review"
    task["updated_at"] = now
    if model_log is not None:
        current_store.audit(
            event_type="model_gateway.called",
            actor_id="system",
            ai_task_id=task_id,
            subject_type="model_gateway_log",
            subject_id=model_log["id"],
            payload={
                "model_log_id": model_log["id"],
                "provider": model_log["provider"],
                "model": model_log["model"],
                "purpose": model_log["purpose"],
                "status": model_log["status"],
            },
        )
    if task["task_type"] == "code_review":
        current_store.audit(
            event_type="code_review.executor_called",
            actor_id="system",
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload={
                "executor_name": executor_meta["executor_name"],
                "executor_type": executor_meta["executor_type"],
                "retryable": executor_meta["retryable"],
                "stage": "execute",
            },
        )
    current_store.audit(
        event_type="ai_task.started",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
    )
    code_review_report = None
    if task["task_type"] == "code_review":
        report = _create_code_review_report(
            current_store,
            task=task,
            output=task["output_json"],
        )
        code_review_report = report
        current_store.audit(
            event_type="code_review.generated",
            actor_id="system",
            ai_task_id=task_id,
            subject_type="code_review_report",
            subject_id=report["id"],
            payload={"risk_level": report["risk_level"]},
        )

    review_id = current_store.new_id("review")
    review = {
        "id": review_id,
        "ai_task_id": task_id,
        "stage": task["task_type"],
        "status": "pending",
        "version": 1,
        "content": current_store.snapshot(task["output_json"]),
        "created_at": now,
        "updated_at": now,
    }
    if not _uses_repository_context(current_store):
        current_store.human_reviews[review_id] = review
    task["review_ids"].append(review_id)
    if task["task_type"] == "code_review":
        report_id = task.get("code_review_report_id")
        if code_review_report is not None:
            code_review_report = {**code_review_report, "review_id": review_id}
        elif report_id is not None:
            current_store.code_review_reports[report_id]["review_id"] = review_id
            code_review_report = current_store.code_review_reports[report_id]
    graph_run, checkpoint = _start_graph_run(current_store, task=task, review_id=review_id)
    current_store.audit(
        event_type="human_review.created",
        actor_id="system",
        ai_task_id=task_id,
        subject_type="human_review",
        subject_id=review_id,
    )
    _save_task_start_records(
        current_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        model_log=model_log,
        code_review_report=code_review_report,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return envelope(
        {
            "id": task_id,
            "status": task["status"],
            "review_id": review_id,
            "graph_run_id": graph_run["id"],
            "checkpoint_id": graph_run["checkpoint_id"],
            "current_step": graph_run["current_step"],
        },
        get_trace_id(request),
    )


@app.get("/api/ai-tasks/{task_id}")
def get_ai_task(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    task = read_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_task_read_role(user, task)
    return envelope(_task_detail_projection(read_store, task), get_trace_id(request))


@app.post("/api/ai-tasks/{task_id}/cancel")
def cancel_ai_task(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _task_workflow_write_store(store(request))
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if task["status"] in {"completed", "failed", "cancelled"}:
        raise api_error(409, "TASK_STATE_INVALID", "Task cannot be cancelled from current status")
    _require_review_decision_role(user, task)
    audit_start_index = len(current_store.audit_events)
    now = datetime.now(UTC).isoformat()
    task["status"] = "cancelled"
    task["updated_at"] = now
    cancelled_reviews = []
    for review_id in task.get("review_ids", []):
        review = current_store.human_reviews.get(review_id)
        if review and review["status"] == "pending":
            review["status"] = "cancelled"
            review["version"] += 1
            review["decided_by"] = user["id"]
            review["decided_at"] = now
            review["updated_at"] = now
            cancelled_reviews.append(review)
    checkpoint = _transition_latest_graph_run(
        current_store,
        task=task,
        status="cancelled",
        current_step="cancelled",
        state_snapshot={"task_status": task["status"]},
    )
    current_store.audit(
        event_type="ai_task.cancelled",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
    )
    graph_run = _latest_graph_run(current_store, task)
    _save_task_state_records(
        current_store,
        task=task,
        reviews=cancelled_reviews,
        graph_run=graph_run,
        checkpoint=checkpoint,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return envelope({"id": task_id, "status": task["status"]}, get_trace_id(request))


@app.get("/api/graph-runs")
def list_graph_runs(
    request: Request,
    ai_task_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    items = list(read_store.graph_runs.values())
    if ai_task_id:
        task = read_store.ai_tasks.get(ai_task_id)
        if task is None:
            raise api_error(404, "NOT_FOUND", "AI task not found")
        _require_task_read_role(user, task)
        items = [item for item in items if item["ai_task_id"] == ai_task_id]
    else:
        items = [
            item
            for item in items
            if (task := read_store.ai_tasks.get(item["ai_task_id"])) is not None
            and _can_read_task(user, task)
        ]
    items.sort(key=lambda item: item["started_at"], reverse=True)
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/reviews/pending")
def pending_reviews(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    repository = _pending_review_query_repository(current_store)
    if repository is not None:
        items = repository.list_pending_review_summaries(read_scope=_task_read_scope(user))
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    read_store = _task_workflow_read_store(current_store)
    items = [
        review
        for review in read_store.human_reviews.values()
        if review["status"] == "pending"
        and (task := read_store.ai_tasks.get(review["ai_task_id"])) is not None
        and _can_read_task(user, task)
    ]
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/reviews/{review_id}")
def get_review(
    review_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    review = read_store.human_reviews.get(review_id)
    if review is None:
        raise api_error(404, "NOT_FOUND", "Review not found")
    task = read_store.ai_tasks.get(review["ai_task_id"])
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_task_read_role(user, task)
    return envelope(
        {
            **read_store.snapshot(review),
            "task": read_store.snapshot(task),
        },
        get_trace_id(request),
    )


@app.post("/api/reviews/{review_id}/approve")
def approve_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _task_workflow_write_store(store(request))
    review, task = _ensure_review_decidable(
        current_store,
        review_id=review_id,
        version=payload.version,
    )
    _require_review_decision_role(user, task)
    audit_start_index = len(current_store.audit_events)
    now = datetime.now(UTC).isoformat()
    review["status"] = "approved"
    review["decided_by"] = user["id"]
    review["decided_at"] = now
    review["updated_at"] = now
    task["status"] = "completed"
    task["updated_at"] = now
    _confirm_code_review_report(current_store, task)
    created_bug_ids = [
        *_create_automated_testing_bugs(current_store, actor_id=user["id"], task=task),
        *_create_post_release_bugs(current_store, actor_id=user["id"], task=task),
    ]
    _advance_requirement_after_task_completed(current_store, task)
    knowledge_deposit = _create_knowledge_deposit(current_store, task)
    checkpoint = _transition_latest_graph_run(
        current_store,
        task=task,
        status="completed",
        current_step="complete_archive",
        state_snapshot={"task_status": task["status"], "review_id": review_id},
    )
    current_store.audit(
        event_type="review.submitted",
        actor_id=user["id"],
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={"decision": "approved"},
    )
    graph_run = _latest_graph_run(current_store, task)
    requirement = current_store.requirements.get(task.get("requirement_id"))
    code_review_report = (
        current_store.code_review_reports.get(task.get("code_review_report_id"))
        if task.get("code_review_report_id")
        else None
    )
    _save_review_decision_records(
        current_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        requirement=requirement,
        knowledge_deposits=[knowledge_deposit],
        bugs=[current_store.bugs[bug_id] for bug_id in created_bug_ids],
        code_review_report=code_review_report,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return envelope(
        {"review_status": review["status"], "task_status": task["status"]},
        get_trace_id(request),
    )


@app.post("/api/reviews/{review_id}/edit-approve")
def edit_approve_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _task_workflow_write_store(store(request))
    review, task = _ensure_review_decidable(
        current_store,
        review_id=review_id,
        version=payload.version,
    )
    _require_review_decision_role(user, task)
    audit_start_index = len(current_store.audit_events)
    edited_content = payload.edited_content or {}
    result = _complete_review_with_edited_approval(
        current_store,
        actor_id=user["id"],
        edited_content=edited_content,
        review=review,
        review_id=review_id,
        task=task,
    )
    graph_run = _latest_graph_run(current_store, task)
    checkpoint = result["checkpoint"]
    requirement = current_store.requirements.get(task.get("requirement_id"))
    code_review_report = (
        current_store.code_review_reports.get(task.get("code_review_report_id"))
        if task.get("code_review_report_id")
        else None
    )
    _save_review_decision_records(
        current_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        requirement=requirement,
        knowledge_deposits=[result["knowledge_deposit"]],
        bugs=[current_store.bugs[bug_id] for bug_id in result["bug_ids"]],
        code_review_report=code_review_report,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return envelope(
        {
            "review_status": result["review_status"],
            "task_status": result["task_status"],
        },
        get_trace_id(request),
    )


@app.post("/api/reviews/{review_id}/reject")
def reject_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _task_workflow_write_store(store(request))
    review, task = _ensure_review_decidable(
        current_store,
        review_id=review_id,
        version=payload.version,
    )
    _require_review_decision_role(user, task)
    audit_start_index = len(current_store.audit_events)
    now = datetime.now(UTC).isoformat()
    review["status"] = "rejected"
    review["decision_reason"] = payload.decision_reason
    review["decided_by"] = user["id"]
    review["decided_at"] = now
    review["updated_at"] = now
    task["status"] = "failed"
    task["updated_at"] = now
    checkpoint = _transition_latest_graph_run(
        current_store,
        task=task,
        status="failed",
        current_step="failed",
        state_snapshot={
            "task_status": task["status"],
            "review_id": review_id,
            "decision_reason": payload.decision_reason,
        },
    )
    current_store.audit(
        event_type="review.rejected",
        actor_id=user["id"],
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={"decision_reason": payload.decision_reason},
    )
    graph_run = _latest_graph_run(current_store, task)
    _save_review_decision_records(
        current_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return envelope(
        {"review_status": review["status"], "task_status": task["status"]},
        get_trace_id(request),
    )


@app.post("/api/reviews/{review_id}/request-more-info")
def request_more_info_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _task_workflow_write_store(store(request))
    review, task = _ensure_review_decidable(
        current_store,
        review_id=review_id,
        version=payload.version,
    )
    _require_review_decision_role(user, task)
    audit_start_index = len(current_store.audit_events)
    now = datetime.now(UTC).isoformat()
    review["status"] = "requested_more_info"
    review["questions"] = payload.questions
    review["decided_by"] = user["id"]
    review["decided_at"] = now
    review["updated_at"] = now
    task["status"] = "waiting_more_info"
    task["updated_at"] = now
    checkpoint = _transition_latest_graph_run(
        current_store,
        task=task,
        status="interrupted",
        current_step="wait_for_more_info",
        state_snapshot={
            "task_status": task["status"],
            "review_id": review_id,
            "questions": payload.questions,
        },
    )
    current_store.audit(
        event_type="review.more_info_requested",
        actor_id=user["id"],
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={"questions": payload.questions},
    )
    graph_run = _latest_graph_run(current_store, task)
    _save_review_decision_records(
        current_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return envelope(
        {"review_status": review["status"], "task_status": task["status"]},
        get_trace_id(request),
    )


@app.post("/api/ai-tasks/{task_id}/more-info")
def submit_more_info(
    task_id: str,
    request: Request,
    payload: MoreInfoRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _task_workflow_write_store(store(request))
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if task["status"] != "waiting_more_info":
        raise api_error(409, "TASK_STATE_INVALID", "Task is not waiting for more info")
    _require_review_decision_role(user, task)
    audit_start_index = len(current_store.audit_events)
    now = datetime.now(UTC).isoformat()
    task["input_json"].setdefault("more_info_answers", []).extend(payload.answers)
    task["status"] = "draft"
    task["current_step"] = "draft"
    task["updated_at"] = now
    current_store.audit(
        event_type="ai_task.more_info_submitted",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
    )
    _save_task_state_records(
        current_store,
        task=task,
        audit_events=current_store.audit_events[audit_start_index:],
    )
    return envelope({"id": task_id, "status": task["status"]}, get_trace_id(request))


@app.get("/api/knowledge/documents")
def list_knowledge_documents(
    request: Request,
    keyword: str | None = None,
    doc_type: str | None = None,
    index_status: str | None = None,
    permission_role: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "asc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    if index_status:
        _ensure_enum(index_status, KNOWLEDGE_INDEX_STATUSES, "knowledge index status")
    current_store = store(request)
    repository = _knowledge_query_repository(current_store)
    if repository is not None:
        items = repository.list_knowledge_documents(
            user_roles=list(user.get("roles", [])),
            keyword=keyword,
            doc_type=doc_type,
            index_status=index_status,
        )
    else:
        items = [
            document
            for document in current_store.knowledge_documents.values()
            if _user_can_read_roles(user, document["permission_roles"])
        ]
        if keyword:
            normalized_keyword = keyword.lower()
            items = [
                item
                for item in items
                if normalized_keyword in f"{item['title']} {item['content']}".lower()
            ]
        if doc_type:
            items = [item for item in items if item["doc_type"] == doc_type]
        if index_status:
            items = [item for item in items if item["index_status"] == index_status]
        items = [_knowledge_document_response(current_store, item) for item in items]
    items = [
        item
        for item in items
        if _list_text_matches(item, permission_role, ("permission_roles",))
    ]
    items = _sort_list_items(
        items,
        allowed_fields={
            "created_at",
            "doc_type",
            "id",
            "index_status",
            "title",
            "updated_at",
        },
        default_sort_by="id",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginated_list_payload(
        items,
        page=page,
        page_size=page_size,
        trace_id=get_trace_id(request),
    )


def _split_knowledge_content(content: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", content) if part.strip()]
    if not paragraphs:
        paragraphs = [content.strip()]
    chunks: list[str] = []
    max_chars = 1200
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        for start in range(0, len(paragraph), max_chars):
            chunk = paragraph[start : start + max_chars].strip()
            if chunk:
                chunks.append(chunk)
    return chunks


def _knowledge_document_chunks(
    current_store: MemoryStore,
    document_id: str,
) -> list[dict[str, Any]]:
    chunks = [
        chunk
        for chunk in current_store.knowledge_chunks.values()
        if chunk.get("document_id") == document_id
    ]
    return sorted(chunks, key=lambda chunk: (chunk.get("chunk_index", 0), chunk.get("id", "")))


def _knowledge_document_response(
    current_store: MemoryStore,
    document: dict[str, Any],
    chunks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    response = current_store.snapshot(document)
    response["chunk_count"] = (
        len(chunks)
        if chunks is not None
        else len(_knowledge_document_chunks(current_store, document["id"]))
    )
    response["index_error"] = document.get("index_error")
    response["vector_index_error"] = document.get("vector_index_error")
    return response


def _clear_knowledge_chunks(current_store: MemoryStore, document_id: str) -> None:
    current_store.knowledge_chunks = {
        chunk_id: chunk
        for chunk_id, chunk in current_store.knowledge_chunks.items()
        if chunk.get("document_id") != document_id
    }


def _mark_knowledge_index_failed(
    current_store: MemoryStore,
    document: dict[str, Any],
    error: str,
) -> None:
    _clear_knowledge_chunks(current_store, document["id"])
    document["chunk_count"] = 0
    document["index_error"] = _ensure_non_blank(error, "index_error")
    document["index_status"] = "index_failed"
    document["vector_index_error"] = None


def _build_knowledge_chunks(
    document: dict[str, Any],
    chunks: list[str],
    *,
    embeddings: list[list[float]] | None = None,
    embedding_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    permission_roles = list(document.get("permission_roles", ["admin"]))
    now = datetime.now(UTC).isoformat()
    records: list[dict[str, Any]] = []
    for chunk_index, content in enumerate(chunks, start=1):
        chunk_id = f"{document['id']}_chunk_{chunk_index:03d}"
        metadata = {
            "doc_type": document.get("doc_type", "manual"),
            "product_id": document.get("product_id"),
            "tags": list(document.get("tags", [])),
            "title": document["title"],
        }
        if embeddings is not None and embedding_context is not None:
            metadata.update(
                {
                    key: value
                    for key, value in {
                        **embedding_context,
                        "embedding_created_at": datetime.now(UTC).isoformat(),
                    }.items()
                    if value is not None
                }
            )
        records.append(
            {
                "chunk_index": chunk_index,
                "content": content,
                "document_id": document["id"],
                "embedding": embeddings[chunk_index - 1] if embeddings is not None else None,
                "id": chunk_id,
                "metadata": metadata,
                "permission_roles": permission_roles,
                "permission_scope": {"roles": permission_roles},
                "created_at": now,
                "updated_at": now,
            }
        )
    return records


def _store_knowledge_chunks(
    current_store: MemoryStore,
    document: dict[str, Any],
    chunks: list[str],
    *,
    embeddings: list[list[float]] | None = None,
    embedding_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    records = _build_knowledge_chunks(
        document,
        chunks,
        embeddings=embeddings,
        embedding_context=embedding_context,
    )
    for chunk in records:
        current_store.knowledge_chunks[chunk["id"]] = chunk
    document["chunk_count"] = len(records)
    return records


def _mark_knowledge_text_indexed(
    current_store: MemoryStore,
    document: dict[str, Any],
    chunks: list[str],
    *,
    vector_error: str | None = None,
) -> None:
    _store_knowledge_chunks(current_store, document, chunks)
    document["index_status"] = "text_indexed"
    document["index_error"] = vector_error
    document["vector_index_error"] = vector_error


def _mark_knowledge_vector_indexed(
    current_store: MemoryStore,
    document: dict[str, Any],
    chunks: list[str],
    embeddings: list[list[float]],
    embedding_context: dict[str, Any],
) -> None:
    _store_knowledge_chunks(
        current_store,
        document,
        chunks,
        embeddings=embeddings,
        embedding_context=embedding_context,
    )
    document["index_status"] = "vector_indexed"
    document["index_error"] = None
    document["vector_index_error"] = None


def _knowledge_index_failed_result(
    document: dict[str, Any],
    error: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    updated_document["chunk_count"] = 0
    updated_document["index_error"] = _ensure_non_blank(error, "index_error")
    updated_document["index_status"] = "index_failed"
    updated_document["vector_index_error"] = None
    return updated_document, []


def _knowledge_text_indexed_result(
    document: dict[str, Any],
    chunks: list[str],
    *,
    vector_error: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    chunk_records = _build_knowledge_chunks(updated_document, chunks)
    updated_document["chunk_count"] = len(chunk_records)
    updated_document["index_status"] = "text_indexed"
    updated_document["index_error"] = vector_error
    updated_document["vector_index_error"] = vector_error
    return updated_document, chunk_records


def _knowledge_vector_indexed_result(
    document: dict[str, Any],
    chunks: list[str],
    embeddings: list[list[float]],
    embedding_context: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    chunk_records = _build_knowledge_chunks(
        updated_document,
        chunks,
        embeddings=embeddings,
        embedding_context=embedding_context,
    )
    updated_document["chunk_count"] = len(chunk_records)
    updated_document["index_status"] = "vector_indexed"
    updated_document["index_error"] = None
    updated_document["vector_index_error"] = None
    return updated_document, chunk_records


def _replace_knowledge_chunks_result(
    current_store: MemoryStore,
    document: dict[str, Any],
    *,
    attempt_vector: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    chunks = _split_knowledge_content(document["content"])
    if not chunks:
        return _knowledge_index_failed_result(document, "NO_INDEXABLE_CONTENT")
    if not attempt_vector:
        return _knowledge_text_indexed_result(document, chunks)
    try:
        embeddings, embedding_context = _call_model_gateway_embeddings_with_context(
            current_store,
            chunks,
        )
    except ModelGatewayConfigError as exc:
        return _knowledge_text_indexed_result(document, chunks, vector_error=str(exc))
    except ModelGatewayCallError as exc:
        return _knowledge_text_indexed_result(
            document,
            chunks,
            vector_error=exc.log.get("error") or "Model gateway embedding request failed",
        )
    return _knowledge_vector_indexed_result(
        document,
        chunks,
        embeddings,
        embedding_context,
    )


def _replace_knowledge_chunks(
    current_store: MemoryStore,
    document: dict[str, Any],
    *,
    attempt_vector: bool = True,
) -> None:
    document_id = document["id"]
    _clear_knowledge_chunks(current_store, document_id)
    chunks = _split_knowledge_content(document["content"])
    if not chunks:
        _mark_knowledge_index_failed(current_store, document, "NO_INDEXABLE_CONTENT")
        return
    if not attempt_vector:
        _mark_knowledge_text_indexed(current_store, document, chunks)
        return
    try:
        embeddings, embedding_context = _call_model_gateway_embeddings_with_context(
            current_store,
            chunks,
        )
    except ModelGatewayConfigError as exc:
        _mark_knowledge_text_indexed(current_store, document, chunks, vector_error=str(exc))
        return
    except ModelGatewayCallError as exc:
        _mark_knowledge_text_indexed(
            current_store,
            document,
            chunks,
            vector_error=exc.log.get("error") or "Model gateway embedding request failed",
        )
        return
    _mark_knowledge_vector_indexed(
        current_store,
        document,
        chunks,
        embeddings,
        embedding_context,
    )


def _apply_knowledge_document_to_memory(
    current_store: MemoryStore,
    document: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> None:
    current_store.knowledge_documents[document["id"]] = document
    _clear_knowledge_chunks(current_store, document["id"])
    for chunk in chunks:
        current_store.knowledge_chunks[chunk["id"]] = chunk


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _knowledge_query_embedding(
    current_store: MemoryStore,
    query: str,
) -> tuple[list[float], dict[str, Any]] | None:
    try:
        embeddings, embedding_context = _call_model_gateway_embeddings_with_context(
            current_store,
            [query],
        )
        return embeddings[0], embedding_context
    except (ModelGatewayConfigError, ModelGatewayCallError):
        return None


def _chunk_embedding_is_compatible(
    chunk: dict[str, Any],
    query_embedding_context: dict[str, Any],
) -> bool:
    embedding = chunk.get("embedding")
    if not isinstance(embedding, list):
        return False
    metadata = chunk.get("metadata") or {}
    query_dimension = query_embedding_context.get("embedding_dimension")
    chunk_dimension = metadata.get("embedding_dimension")
    if query_dimension is not None:
        try:
            normalized_query_dimension = int(query_dimension)
            normalized_chunk_dimension = (
                int(chunk_dimension) if chunk_dimension is not None else None
            )
        except (TypeError, ValueError):
            return False
        if (
            normalized_chunk_dimension is not None
            and normalized_chunk_dimension != normalized_query_dimension
        ):
            return False
        if len(embedding) != normalized_query_dimension:
            return False
    query_model = query_embedding_context.get("embedding_model")
    chunk_model = metadata.get("embedding_model")
    if query_model and chunk_model and chunk_model != query_model:
        return False
    query_config_id = query_embedding_context.get("embedding_config_id")
    chunk_config_id = metadata.get("embedding_config_id")
    if query_config_id and chunk_config_id and chunk_config_id != query_config_id:
        return False
    return True


def _has_readable_vector_chunks(current_store: MemoryStore, user: dict[str, Any]) -> bool:
    for document in current_store.knowledge_documents.values():
        if document.get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES:
            continue
        if not _user_can_read_roles(user, document["permission_roles"]):
            continue
        for chunk in _knowledge_document_chunks(current_store, document["id"]):
            chunk_roles = chunk.get("permission_roles", document["permission_roles"])
            if _user_can_read_roles(user, chunk_roles) and isinstance(chunk.get("embedding"), list):
                return True
    return False


@app.post("/api/knowledge/documents")
def create_knowledge_document(
    request: Request,
    payload: KnowledgeDocumentRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = _knowledge_write_store(store(request))
    title = _ensure_non_blank(payload.title, "title")
    content = _ensure_non_blank(payload.content, "content")
    if payload.product_id is not None and payload.product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    _ensure_roles(payload.permission_roles)
    document_id = current_store.new_id("knowledge")
    now = datetime.now(UTC).isoformat()
    document = {
        "id": document_id,
        "title": title,
        "content": content,
        "doc_type": payload.doc_type,
        "product_id": payload.product_id,
        "permission_roles": payload.permission_roles,
        "tags": payload.tags,
        "index_status": "pending_index",
        "index_error": None,
        "vector_index_error": None,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    model_log_start_index = len(current_store.model_gateway_logs)
    document, chunks = _replace_knowledge_chunks_result(current_store, document)
    if not _uses_repository_context(current_store):
        _apply_knowledge_document_to_memory(current_store, document, chunks)
    audit_event = _record_audit_event(
        current_store,
        event_type="knowledge_document.created",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    _save_knowledge_document_records(
        current_store,
        document=document,
        chunks=chunks,
        audit_event=audit_event,
        model_logs=current_store.model_gateway_logs[model_log_start_index:],
    )
    return envelope(
        _knowledge_document_response(current_store, document, chunks),
        get_trace_id(request),
    )


@app.patch("/api/knowledge/documents/{document_id}")
def patch_knowledge_document(
    document_id: str,
    request: Request,
    payload: KnowledgeDocumentPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = _knowledge_write_store(store(request))
    document = current_store.knowledge_documents.get(document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    updates = _payload_updates(payload)
    if "title" in updates:
        updates["title"] = _ensure_non_blank(updates["title"], "title")
    if "content" in updates:
        updates["content"] = _ensure_non_blank(updates["content"], "content")
    if "permission_roles" in updates:
        _ensure_roles(updates["permission_roles"])
    if "product_id" in updates and updates["product_id"] is not None:
        if updates["product_id"] not in current_store.products:
            raise api_error(404, "NOT_FOUND", "Product not found")
    if "index_status" in updates:
        _ensure_enum(updates["index_status"], KNOWLEDGE_INDEX_STATUSES, "knowledge index status")
    if "index_error" in updates and updates["index_error"] is not None:
        updates["index_error"] = _ensure_non_blank(updates["index_error"], "index_error")
    document = {**document, **updates, "updated_at": datetime.now(UTC).isoformat()}
    model_log_start_index = len(current_store.model_gateway_logs)
    if updates.get("index_status") == "index_failed":
        document, chunks = _knowledge_index_failed_result(
            document,
            document.get("index_error") or "Knowledge indexing failed",
        )
    elif updates.get("index_status") in {"archived", "importing", "pending_index"}:
        chunks = []
        document["chunk_count"] = 0
        document["index_error"] = None
        document["vector_index_error"] = None
    elif updates.get("index_status") == "text_indexed":
        document, chunks = _replace_knowledge_chunks_result(
            current_store,
            document,
            attempt_vector=False,
        )
    elif updates.get("index_status") in {"indexed", "vector_indexed"} or {
        "content",
        "title",
        "permission_roles",
        "product_id",
        "doc_type",
        "tags",
    }.intersection(updates):
        document, chunks = _replace_knowledge_chunks_result(current_store, document)
    else:
        chunks = _knowledge_chunks_for_document(current_store, document_id)
    if not _uses_repository_context(current_store):
        _apply_knowledge_document_to_memory(current_store, document, chunks)
    audit_event = _record_audit_event(
        current_store,
        event_type="knowledge_document.updated",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    _save_knowledge_document_records(
        current_store,
        document=document,
        chunks=chunks,
        audit_event=audit_event,
        model_logs=current_store.model_gateway_logs[model_log_start_index:],
    )
    return envelope(
        _knowledge_document_response(current_store, document, chunks),
        get_trace_id(request),
    )


@app.post("/api/knowledge/documents/{document_id}/retry-index")
def retry_knowledge_document_index(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = _knowledge_write_store(store(request))
    document = current_store.knowledge_documents.get(document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if document.get("index_status") not in {"index_failed", "text_indexed"}:
        raise api_error(
            409,
            "KNOWLEDGE_INDEX_STATE_INVALID",
            "Knowledge document is not eligible for index retry",
        )
    document = {**document, "updated_at": datetime.now(UTC).isoformat()}
    model_log_start_index = len(current_store.model_gateway_logs)
    document, chunks = _replace_knowledge_chunks_result(current_store, document)
    if not _uses_repository_context(current_store):
        _apply_knowledge_document_to_memory(current_store, document, chunks)
    audit_event = _record_audit_event(
        current_store,
        event_type="knowledge_document.index_retried",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    _save_knowledge_document_records(
        current_store,
        document=document,
        chunks=chunks,
        audit_event=audit_event,
        model_logs=current_store.model_gateway_logs[model_log_start_index:],
    )
    return envelope(
        _knowledge_document_response(current_store, document, chunks),
        get_trace_id(request),
    )


@app.delete("/api/knowledge/documents/{document_id}")
def delete_knowledge_document(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = _knowledge_write_store(store(request))
    if document_id not in current_store.knowledge_documents:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    affected_deposits = []
    now = datetime.now(UTC).isoformat()
    for deposit in current_store.knowledge_deposits.values():
        if deposit.get("knowledge_document_id") == document_id:
            affected_deposit = {
                **deposit,
                "knowledge_document_id": None,
                "updated_at": now,
            }
            affected_deposits.append(affected_deposit)
    if not _uses_repository_context(current_store):
        del current_store.knowledge_documents[document_id]
        current_store.knowledge_chunks = {
            chunk_id: chunk
            for chunk_id, chunk in current_store.knowledge_chunks.items()
            if chunk.get("document_id") != document_id
        }
        for deposit in affected_deposits:
            current_store.knowledge_deposits[deposit["id"]] = deposit
    audit_event = _record_audit_event(
        current_store,
        event_type="knowledge_document.deleted",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    _delete_knowledge_document_records(
        current_store,
        document_id=document_id,
        deposits=affected_deposits,
        audit_event=audit_event,
    )
    return envelope({"deleted": True, "id": document_id}, get_trace_id(request))


@app.post("/api/knowledge/search")
def search_knowledge(
    request: Request,
    payload: KnowledgeSearchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    query = _ensure_non_blank(payload.query, "query").lower()
    repository = _knowledge_query_repository(current_store)
    has_vector_chunks = getattr(repository, "has_readable_vector_chunks", None)
    search_chunks = getattr(repository, "search_knowledge_chunks", None)
    if has_vector_chunks is not None and search_chunks is not None:
        user_roles = list(user.get("roles", []))
        query_embedding_result = (
            _knowledge_query_embedding(current_store, query)
            if has_vector_chunks(user_roles=user_roles)
            else None
        )
        candidates = search_chunks(
            user_roles=user_roles,
            query=None if query_embedding_result is not None else query,
        )
    else:
        query_embedding_result = (
            _knowledge_query_embedding(current_store, query)
            if _has_readable_vector_chunks(current_store, user)
            else None
        )
        candidates = []
        for document in current_store.knowledge_documents.values():
            if document.get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES:
                continue
            if not _user_can_read_roles(user, document["permission_roles"]):
                continue
            chunks = _knowledge_document_chunks(current_store, document["id"])
            if not chunks:
                continue
            for chunk in chunks:
                chunk_roles = chunk.get("permission_roles", document["permission_roles"])
                if not _user_can_read_roles(user, chunk_roles):
                    continue
                candidates.append({"chunk": chunk, "document": document})
    query_embedding = query_embedding_result[0] if query_embedding_result else None
    query_embedding_context = query_embedding_result[1] if query_embedding_result else None
    items = []
    for candidate in candidates:
        document = candidate["document"]
        chunk = candidate["chunk"]
        haystack = f"{document['title']} {chunk['content']}".lower()
        embedding = chunk.get("embedding")
        score = None
        if (
            query_embedding is not None
            and query_embedding_context is not None
            and isinstance(embedding, list)
            and _chunk_embedding_is_compatible(chunk, query_embedding_context)
        ):
            score = _cosine_similarity(query_embedding, [float(value) for value in embedding])
            if score <= 0 and query not in haystack:
                continue
        elif query not in haystack:
            continue
        retrieval_mode = "vector" if score is not None else "keyword"
        items.append(
            {
                "chunk_id": chunk["id"],
                "chunk_index": chunk["chunk_index"],
                "document_id": document["id"],
                "title": document["title"],
                "content": chunk["content"],
                "retrieval_mode": retrieval_mode,
                "score": round(score, 6) if score is not None else None,
                "source": {
                    "chunk_id": chunk["id"],
                    "doc_type": document["doc_type"],
                    "title": document["title"],
                },
            }
        )
    items.sort(
        key=lambda item: (
            -(item["score"] if item["score"] is not None else -1.0),
            item["document_id"],
            item["chunk_index"],
        )
    )
    return envelope({"items": items[: payload.top_k], "total": len(items)}, get_trace_id(request))


@app.get("/api/knowledge/deposits")
def list_knowledge_deposits(
    request: Request,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = _knowledge_write_store(store(request))
    repository = _knowledge_query_repository(current_store)
    list_deposits = getattr(repository, "list_knowledge_deposits", None)
    if list_deposits is not None:
        items = list_deposits(status=status)
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = list(current_store.knowledge_deposits.values())
    if status:
        items = [item for item in items if item["status"] == status]
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/knowledge/deposits/{deposit_id}/approve")
def approve_knowledge_deposit(
    deposit_id: str,
    request: Request,
    payload: KnowledgeDepositApproveRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = _knowledge_write_store(store(request))
    deposit = _get_knowledge_deposit(current_store, deposit_id)
    if deposit is None:
        raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
    if deposit["status"] != "pending":
        raise api_error(409, "KNOWLEDGE_DEPOSIT_STATE_INVALID", "Deposit is not pending")
    _ensure_roles(payload.permission_roles)

    document_id = current_store.new_id("knowledge")
    now = datetime.now(UTC).isoformat()
    document = {
        "id": document_id,
        "title": payload.title or deposit["title"],
        "content": deposit["content"],
        "doc_type": "task_deposit",
        "permission_roles": payload.permission_roles,
        "tags": ["task_deposit"],
        "index_status": "pending_index",
        "index_error": None,
        "vector_index_error": None,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    model_log_start_index = len(current_store.model_gateway_logs)
    document, chunks = _replace_knowledge_chunks_result(current_store, document)
    deposit = {
        **deposit,
        "status": "approved",
        "knowledge_document_id": document_id,
        "updated_at": now,
    }
    if not _uses_repository_context(current_store):
        _apply_knowledge_document_to_memory(current_store, document, chunks)
        current_store.knowledge_deposits[deposit_id] = deposit
    audit_event = _record_audit_event(
        current_store,
        event_type="knowledge_deposit.approved",
        actor_id=user["id"],
        subject_type="knowledge_deposit",
        subject_id=deposit_id,
    )
    _save_knowledge_deposit_records(
        current_store,
        deposit=deposit,
        document=document,
        chunks=chunks,
        audit_event=audit_event,
        model_logs=current_store.model_gateway_logs[model_log_start_index:],
    )
    return envelope(deposit, get_trace_id(request))


@app.post("/api/knowledge/deposits/{deposit_id}/reject")
def reject_knowledge_deposit(
    deposit_id: str,
    request: Request,
    payload: KnowledgeDepositRejectRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = _knowledge_write_store(store(request))
    deposit = _get_knowledge_deposit(current_store, deposit_id)
    if deposit is None:
        raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
    if deposit["status"] != "pending":
        raise api_error(409, "KNOWLEDGE_DEPOSIT_STATE_INVALID", "Deposit is not pending")

    deposit = {
        **deposit,
        "status": "rejected",
        "rejection_reason": payload.reason,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if not _uses_repository_context(current_store):
        current_store.knowledge_deposits[deposit_id] = deposit
    audit_event = _record_audit_event(
        current_store,
        event_type="knowledge_deposit.rejected",
        actor_id=user["id"],
        subject_type="knowledge_deposit",
        subject_id=deposit_id,
    )
    _save_knowledge_deposit_records(
        current_store,
        deposit=deposit,
        audit_event=audit_event,
    )
    return envelope(deposit, get_trace_id(request))


def _writeback_idempotency_key(task_id: str) -> str:
    return f"mock_issue:{task_id}"


def _completed_task_for_writeback(current_store: MemoryStore, task_id: str) -> dict[str, Any]:
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if task["status"] != "completed":
        raise api_error(409, "TASK_STATE_INVALID", "Only completed tasks can write mock issues")
    return task


@app.get("/api/writeback/results/{task_id}")
def get_writeback_results(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    _completed_task_for_writeback(read_store, task_id)

    idempotency_key = _writeback_idempotency_key(task_id)
    result = read_store.mock_writebacks.get(idempotency_key)
    if result is None:
        result = {
            "task_id": task_id,
            "status": "not_written",
            "idempotency_key": idempotency_key,
            "issues": [],
        }
    return envelope(result, get_trace_id(request))


@app.post("/api/writeback/results/{task_id}")
def create_writeback_results(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _task_workflow_write_store(store(request))
    task = _completed_task_for_writeback(current_store, task_id)
    idempotency_key = _writeback_idempotency_key(task_id)
    result = current_store.mock_writebacks.get(idempotency_key)
    if result is None:
        issue = {
            "id": current_store.new_id("mock_issue"),
            "title": task["title"],
            "source_task_id": task_id,
            "status": "open",
        }
        result = {
            "task_id": task_id,
            "status": "completed",
            "idempotency_key": idempotency_key,
            "issues": [issue],
        }
        if not _uses_repository_context(current_store):
            current_store.mock_writebacks[idempotency_key] = result
        audit_event = _record_audit_event(
            current_store,
            event_type="mock_issue.written",
            actor_id=user["id"],
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload={"idempotency_key": idempotency_key},
        )
        _save_mock_writeback_record(current_store, result, audit_event=audit_event)
    return envelope(result, get_trace_id(request))


@app.get("/api/ai-tasks/{task_id}/code-review-report")
def get_code_review_report(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"reviewer", "rd_owner"})
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    task = read_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_task_read_role(user, task)
    report_id = task.get("code_review_report_id")
    if not report_id:
        raise api_error(404, "NOT_FOUND", "Code review report not found")
    report = read_store.code_review_reports.get(report_id)
    if report is None:
        raise api_error(404, "NOT_FOUND", "Code review report not found")
    return envelope(report, get_trace_id(request))


@app.get("/api/audit/events")
def audit_events(
    request: Request,
    ai_task_id: str | None = None,
    actor: str | None = None,
    actor_id: str | None = None,
    subject: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    event_type: str | None = None,
    result: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    _ensure_enum(result, {"failed", "success"}, "audit result")
    current_store = store(request)
    from_at = _parse_iso_datetime(created_from, "created_from") if created_from else None
    to_at = _parse_iso_datetime(created_to, "created_to") if created_to else None
    repository = _audit_query_repository(current_store)
    if repository is not None:
        items = repository.list_audit_events(
            ai_task_id=ai_task_id,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            created_from=from_at,
            created_to=to_at,
        )
    else:
        items = list(current_store.audit_events)
        if actor_id:
            items = [item for item in items if item.get("actor_id") == actor_id]
        if event_type:
            items = [item for item in items if item.get("event_type") == event_type]
        if ai_task_id:
            items = [item for item in items if item.get("ai_task_id") == ai_task_id]
        if subject_type:
            items = [item for item in items if item.get("subject_type") == subject_type]
        if subject_id:
            items = [item for item in items if item.get("subject_id") == subject_id]
        if created_from or created_to:
            filtered_items = []
            for item in items:
                event_at = _parse_iso_datetime(str(item.get("created_at") or ""), "created_at")
                if from_at and event_at < from_at:
                    continue
                if to_at and event_at > to_at:
                    continue
                filtered_items.append(item)
            items = filtered_items
    items = [{**item, "result": item.get("result", "success")} for item in items]
    if result:
        items = [item for item in items if item.get("result", "success") == result]
    items = [item for item in items if _list_text_matches(item, actor, ("actor_id",))]
    items = [
        item
        for item in items
        if _list_text_matches(item, subject, ("subject_type", "subject_id", "ai_task_id"))
    ]
    items = _sort_list_items(
        items,
        allowed_fields={
            "actor_id",
            "ai_task_id",
            "created_at",
            "event_type",
            "id",
            "result",
            "sequence",
            "subject_id",
            "subject_type",
        },
        default_sort_by="sequence",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginated_list_payload(
        items,
        page=page,
        page_size=page_size,
        trace_id=get_trace_id(request),
    )


def _render_markdown(current_store: MemoryStore, task: dict[str, Any]) -> str:
    requirement = task["requirement_snapshot"]
    design_task_id = task["input_json"].get("product_detail_design_task_id")
    design_task = current_store.ai_tasks.get(str(design_task_id))
    design_output = design_task.get("output_json") if design_task else None
    solution_output = task.get("output_json")
    design_summary = (
        design_output.get("summary", "未找到已确认产品详细设计。")
        if design_output
        else "未找到已确认产品详细设计。"
    )
    solution_summary = (
        solution_output.get("summary", "未找到已确认技术方案。")
        if solution_output
        else "未找到已确认技术方案。"
    )

    sections = [
        f"# {requirement['title']}",
        "",
        "## 需求",
        requirement["content"],
        "",
        "## 产品详细设计",
        design_summary,
        "",
        "## 技术方案",
        solution_summary,
    ]
    if solution_output and solution_output.get("architecture"):
        sections.extend(["", "### 架构要点"])
        sections.extend(f"- {item}" for item in solution_output["architecture"])
    return "\n".join(sections) + "\n"


def empty_list_payload() -> dict[str, Any]:
    return {
        "items": [],
        "total": 0,
    }


def _parse_iso_datetime(value: str, field_name: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    if len(normalized) >= 6 and normalized[-6] == " " and normalized[-3] == ":":
        normalized = f"{normalized[:-6]}+{normalized[-5:]}"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"Invalid {field_name}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _lifecycle_relation(
    *,
    subject_type: str,
    subject_id: str,
    relation_type: str,
    summary: str,
    product_id: str | None = None,
    version_id: str | None = None,
    module_code: str | None = None,
    source_module: str = "lifecycle_context",
    observed_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "relation_type": relation_type,
        "summary": summary,
        "confidence": 1.0,
        "product_id": product_id,
        "version_id": version_id,
        "module_code": module_code,
        "source_module": source_module,
        "observed_at": observed_at,
        "metadata": metadata or {},
    }


def _lifecycle_mock_issue(
    current_store: MemoryStore,
    subject_id: str,
) -> dict[str, Any] | None:
    for result in current_store.mock_writebacks.values():
        for issue in result["issues"]:
            if issue["id"] == subject_id:
                return issue
    return None


def _lifecycle_audit_event(
    current_store: MemoryStore,
    subject_id: str,
) -> dict[str, Any] | None:
    return next(
        (event for event in current_store.audit_events if event["id"] == subject_id),
        None,
    )


def _lifecycle_require_tasks_by_requirement(
    current_store: MemoryStore,
    requirement_id: str,
) -> list[dict[str, Any]]:
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    return [
        task
        for task in current_store.ai_tasks.values()
        if task.get("requirement_id") == requirement_id
    ]


def _lifecycle_require_task(
    current_store: MemoryStore,
    task_id: str | None,
) -> dict[str, Any]:
    task = current_store.ai_tasks.get(str(task_id))
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    return task


def _lifecycle_subject_tasks(
    current_store: MemoryStore,
    *,
    subject_type: str,
    subject_id: str,
    resolving_audit_subject: bool = False,
) -> list[dict[str, Any]]:
    if subject_type == "requirement":
        return _lifecycle_require_tasks_by_requirement(current_store, subject_id)
    if subject_type == "ai_task":
        return [_lifecycle_require_task(current_store, subject_id)]
    if subject_type == "product":
        if subject_id not in current_store.products:
            raise api_error(404, "NOT_FOUND", "Product not found")
        return [
            task
            for task in current_store.ai_tasks.values()
            if task.get("product_id") == subject_id
        ]
    if subject_type == "human_review":
        review = current_store.human_reviews.get(subject_id)
        if review is None:
            raise api_error(404, "NOT_FOUND", "Review not found")
        return [_lifecycle_require_task(current_store, review.get("ai_task_id"))]
    if subject_type == "code_review_report":
        report = current_store.code_review_reports.get(subject_id)
        if report is None:
            raise api_error(404, "NOT_FOUND", "Code review report not found")
        return [_lifecycle_require_task(current_store, report.get("task_id"))]
    if subject_type == "gitlab_mr_snapshot":
        snapshot = current_store.gitlab_mr_snapshots.get(subject_id)
        if snapshot is None:
            raise api_error(404, "NOT_FOUND", "GitLab MR snapshot not found")
        return [_lifecycle_require_task(current_store, snapshot.get("technical_solution_task_id"))]
    if subject_type == "mock_issue":
        issue = _lifecycle_mock_issue(current_store, subject_id)
        if issue is None:
            raise api_error(404, "NOT_FOUND", "Mock issue not found")
        return [_lifecycle_require_task(current_store, issue.get("source_task_id"))]
    if subject_type == "knowledge_deposit":
        deposit = current_store.knowledge_deposits.get(subject_id)
        if deposit is None:
            raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
        return [_lifecycle_require_task(current_store, deposit.get("ai_task_id"))]
    if subject_type == "audit_event":
        event = _lifecycle_audit_event(current_store, subject_id)
        if event is None:
            raise api_error(404, "NOT_FOUND", "Audit event not found")
        if event.get("ai_task_id"):
            return [_lifecycle_require_task(current_store, event.get("ai_task_id"))]
        nested_type = event.get("subject_type")
        nested_id = event.get("subject_id")
        if nested_type and nested_id and not resolving_audit_subject:
            return _lifecycle_subject_tasks(
                current_store,
                subject_type=nested_type,
                subject_id=nested_id,
                resolving_audit_subject=True,
            )
        return []
    if subject_type == "bug":
        bug = current_store.bugs.get(subject_id)
        if bug is None:
            raise api_error(404, "NOT_FOUND", "Bug not found")
        if bug.get("related_task_id"):
            return [_lifecycle_require_task(current_store, bug.get("related_task_id"))]
        if bug.get("requirement_id"):
            return _lifecycle_require_tasks_by_requirement(current_store, bug["requirement_id"])
        return [
            task
            for task in current_store.ai_tasks.values()
            if task.get("product_id") == bug.get("product_id")
        ]
    v1_2_collections = {
        "gitlab_daily_code_metric": (
            current_store.gitlab_daily_code_metrics,
            "GitLab daily code metric",
        ),
        "jenkins_release": (current_store.jenkins_release_records, "Jenkins release"),
        "online_log_metric": (current_store.online_log_metrics, "Online log metric"),
        "user_usage_metric": (current_store.user_usage_metrics, "User usage metric"),
        "user_feedback": (current_store.user_feedback, "User feedback"),
        "iteration_plan_suggestion": (
            current_store.iteration_plan_suggestions,
            "Iteration plan suggestion",
        ),
    }
    if subject_type in v1_2_collections:
        collection, label = v1_2_collections[subject_type]
        evidence = collection.get(subject_id)
        if evidence is None:
            raise api_error(404, "NOT_FOUND", f"{label} not found")
        return [
            task
            for task in current_store.ai_tasks.values()
            if task.get("product_id") == evidence.get("product_id")
            and (
                not evidence.get("version_id")
                or not task.get("version_id")
                or task.get("version_id") == evidence.get("version_id")
            )
            and (
                not evidence.get("module_code")
                or not task.get("module_code")
                or task.get("module_code") == evidence.get("module_code")
            )
        ]
    raise api_error(400, "VALIDATION_ERROR", "Unsupported lifecycle subject_type")


def _tasks_for_lifecycle_subject(
    current_store: MemoryStore,
    *,
    subject_type: str | None,
    subject_id: str | None,
    product_id: str | None,
    version_id: str | None,
    module_code: str | None,
) -> list[dict[str, Any]]:
    if subject_type:
        if not subject_id:
            raise api_error(400, "VALIDATION_ERROR", "subject_id is required")
        tasks = _lifecycle_subject_tasks(
            current_store,
            subject_type=subject_type,
            subject_id=str(subject_id),
        )
    else:
        tasks = [
            task
            for task in current_store.ai_tasks.values()
            if not product_id or task.get("product_id") == product_id
        ]

    if product_id:
        tasks = [task for task in tasks if task.get("product_id") == product_id]
    if version_id:
        tasks = [task for task in tasks if task.get("version_id") == version_id]
    if module_code:
        tasks = [task for task in tasks if task.get("module_code") == module_code]
    tasks.sort(key=lambda task: task["id"])
    return tasks


def _lifecycle_subject(
    current_store: MemoryStore,
    *,
    subject_type: str | None,
    subject_id: str | None,
    product_id: str | None,
) -> dict[str, Any]:
    if subject_type and subject_id:
        normalized_subject_id = str(subject_id)
        tasks = _lifecycle_subject_tasks(
            current_store,
            subject_type=subject_type,
            subject_id=normalized_subject_id,
        )
        resolved_product_id = tasks[0]["product_id"] if tasks else None
        if subject_type == "requirement":
            requirement = current_store.requirements[normalized_subject_id]
            resolved_product_id = requirement["product_id"]
        elif subject_type == "product":
            resolved_product_id = normalized_subject_id
        elif subject_type == "gitlab_mr_snapshot":
            snapshot = current_store.gitlab_mr_snapshots[normalized_subject_id]
            resolved_product_id = snapshot["product_id"]
        elif subject_type == "bug":
            bug = current_store.bugs[normalized_subject_id]
            resolved_product_id = bug["product_id"]
        elif subject_type in {
            "gitlab_daily_code_metric",
            "jenkins_release",
            "online_log_metric",
            "user_usage_metric",
            "user_feedback",
            "iteration_plan_suggestion",
        }:
            resolved_product_id = _subject_product_id(
                current_store,
                subject_type,
                normalized_subject_id,
            )
        return {
            "type": subject_type,
            "id": normalized_subject_id,
            "product_id": resolved_product_id,
        }
    return {"type": "product", "id": product_id, "product_id": product_id}


def _lifecycle_task_scope(tasks: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {
        "module_codes": {
            str(task["module_code"])
            for task in tasks
            if task.get("module_code")
        },
        "product_ids": {
            str(task["product_id"])
            for task in tasks
            if task.get("product_id")
        },
        "requirement_ids": {
            str(task["requirement_id"])
            for task in tasks
            if task.get("requirement_id")
        },
        "task_ids": {
            str(task["id"])
            for task in tasks
            if task.get("id")
        },
        "version_ids": {
            str(task["version_id"])
            for task in tasks
            if task.get("version_id")
        },
    }


def _lifecycle_matches_scope(
    item: dict[str, Any],
    scope: dict[str, set[str]],
) -> bool:
    if item.get("related_task_id") and str(item["related_task_id"]) in scope["task_ids"]:
        return True
    if item.get("requirement_id") and str(item["requirement_id"]) in scope["requirement_ids"]:
        return True
    product_id = item.get("product_id")
    if product_id and str(product_id) not in scope["product_ids"]:
        return False
    version_id = item.get("version_id")
    if version_id and scope["version_ids"] and str(version_id) not in scope["version_ids"]:
        return False
    module_code = item.get("module_code")
    if module_code and scope["module_codes"] and str(module_code) not in scope["module_codes"]:
        return False
    return bool(product_id and str(product_id) in scope["product_ids"])


def _lifecycle_matching_v1_2_evidence(
    current_store: MemoryStore,
    tasks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    scope = _lifecycle_task_scope(tasks)
    return {
        "bug": [
            item
            for item in current_store.bugs.values()
            if _lifecycle_matches_scope(item, scope)
        ],
        "gitlab_daily_code_metric": [
            item
            for item in current_store.gitlab_daily_code_metrics.values()
            if _lifecycle_matches_scope(item, scope)
        ],
        "jenkins_release": [
            item
            for item in current_store.jenkins_release_records.values()
            if _lifecycle_matches_scope(item, scope)
        ],
        "online_log_metric": [
            item
            for item in current_store.online_log_metrics.values()
            if _lifecycle_matches_scope(item, scope)
        ],
        "user_usage_metric": [
            item
            for item in current_store.user_usage_metrics.values()
            if _lifecycle_matches_scope(item, scope)
        ],
        "user_feedback": [
            item
            for item in current_store.user_feedback.values()
            if _lifecycle_matches_scope(item, scope)
        ],
        "iteration_plan_suggestion": [
            item
            for item in current_store.iteration_plan_suggestions.values()
            if _lifecycle_matches_scope(item, scope)
        ],
    }


def _lifecycle_missing_context(
    current_store: MemoryStore,
    *,
    tasks: list[dict[str, Any]],
) -> list[str]:
    missing = []
    if not any(task["task_type"] == "automated_testing" for task in tasks):
        missing.append("automated_testing")
    matching_evidence = _lifecycle_matching_v1_2_evidence(current_store, tasks)
    missing.extend(
        subject_type
        for subject_type, items in matching_evidence.items()
        if not items
    )
    return missing


def _lifecycle_upstream(
    current_store: MemoryStore,
    *,
    subject_type: str | None,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if subject_type in {None, "product", "requirement"}:
        return []
    relations: list[dict[str, Any]] = []
    seen_requirement_ids: set[str] = set()
    for task in tasks:
        requirement_id = task.get("requirement_id")
        if not requirement_id or requirement_id in seen_requirement_ids:
            continue
        requirement = current_store.requirements.get(requirement_id)
        if requirement is None:
            continue
        seen_requirement_ids.add(requirement_id)
        relations.append(
            _lifecycle_relation(
                subject_type="requirement",
                subject_id=requirement["id"],
                relation_type="derived_from_requirement",
                summary=requirement["title"],
                product_id=requirement["product_id"],
                version_id=requirement["version_id"],
                module_code=requirement.get("module_code"),
                source_module="requirement",
                observed_at=requirement.get("created_at"),
                metadata={"status": requirement["status"]},
            )
        )
    return relations


def _lifecycle_downstream(
    current_store: MemoryStore,
    *,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    task_ids = {task["id"] for task in tasks}

    for task in tasks:
        task_type = task["task_type"]
        relations.append(
            _lifecycle_relation(
                subject_type="ai_task",
                subject_id=task["id"],
                relation_type=f"generates_{task_type}",
                summary=task["title"],
                product_id=task["product_id"],
                version_id=task["version_id"],
                module_code=task.get("module_code"),
                source_module="ai_task",
                observed_at=task.get("created_at"),
                metadata={"task_type": task_type, "status": task["status"]},
            )
        )

        for review_id in task.get("review_ids", []):
            review = current_store.human_reviews.get(review_id)
            if review is None:
                continue
            relations.append(
                _lifecycle_relation(
                    subject_type="human_review",
                    subject_id=review_id,
                    relation_type="creates_human_review",
                    summary=f"{review['stage']} review {review['status']}",
                    product_id=task["product_id"],
                    version_id=task["version_id"],
                    module_code=task.get("module_code"),
                    source_module="review",
                    metadata={"status": review["status"], "stage": review["stage"]},
                )
            )

        report_id = task.get("code_review_report_id")
        if report_id and report_id in current_store.code_review_reports:
            report = current_store.code_review_reports[report_id]
            relations.append(
                _lifecycle_relation(
                    subject_type="code_review_report",
                    subject_id=report_id,
                    relation_type="creates_code_review_report",
                    summary=report["summary"],
                    product_id=task["product_id"],
                    version_id=task["version_id"],
                    module_code=task.get("module_code"),
                    source_module="code_review_executor",
                    metadata={
                        "status": report["status"],
                        "risk_level": report["risk_level"],
                    },
                )
            )

    for snapshot in current_store.gitlab_mr_snapshots.values():
        if snapshot.get("technical_solution_task_id") not in task_ids:
            continue
        relations.append(
            _lifecycle_relation(
                subject_type="gitlab_mr_snapshot",
                subject_id=snapshot["id"],
                relation_type="captures_gitlab_mr_snapshot",
                summary=snapshot["title"],
                product_id=next(
                    task["product_id"]
                    for task in tasks
                    if task["id"] == snapshot["technical_solution_task_id"]
                ),
                source_module="gitlab_review",
                observed_at=snapshot.get("created_at"),
                metadata={"mr_iid": snapshot["mr_iid"], "writeback_allowed": False},
            )
        )

    for result in current_store.mock_writebacks.values():
        for issue in result["issues"]:
            if issue["source_task_id"] not in task_ids:
                continue
            task = current_store.ai_tasks[issue["source_task_id"]]
            relations.append(
                _lifecycle_relation(
                    subject_type="mock_issue",
                    subject_id=issue["id"],
                    relation_type="creates_mock_issue",
                    summary=issue["title"],
                    product_id=task["product_id"],
                    version_id=task["version_id"],
                    module_code=task.get("module_code"),
                    source_module="integration",
                    metadata={
                        "status": issue["status"],
                        "idempotency_key": result["idempotency_key"],
                    },
                )
            )

    for deposit in current_store.knowledge_deposits.values():
        if deposit["ai_task_id"] not in task_ids:
            continue
        task = current_store.ai_tasks[deposit["ai_task_id"]]
        relations.append(
            _lifecycle_relation(
                subject_type="knowledge_deposit",
                subject_id=deposit["id"],
                relation_type="creates_knowledge_deposit",
                summary=deposit["title"],
                product_id=task["product_id"],
                version_id=task["version_id"],
                module_code=task.get("module_code"),
                source_module="knowledge",
                metadata={"status": deposit["status"]},
            )
        )

    for event in current_store.audit_events:
        task_match = event.get("ai_task_id") in task_ids
        subject_task_match = (
            event.get("subject_type") == "ai_task"
            and event.get("subject_id") in task_ids
        )
        requirement_match = any(
            event.get("subject_type") == "requirement"
            and event.get("subject_id") == task.get("requirement_id")
            for task in tasks
        )
        if not (task_match or subject_task_match or requirement_match):
            continue
        relations.append(
            _lifecycle_relation(
                subject_type="audit_event",
                subject_id=event["id"],
                relation_type="creates_audit_event",
                summary=event["event_type"],
                product_id=None,
                source_module="audit",
                observed_at=event.get("created_at"),
                metadata={"event_type": event["event_type"]},
            )
        )

    matching_evidence = _lifecycle_matching_v1_2_evidence(current_store, tasks)
    for bug in matching_evidence["bug"]:
        relations.append(
            _lifecycle_relation(
                subject_type="bug",
                subject_id=bug["id"],
                relation_type="observes_bug",
                summary=bug["title"],
                product_id=bug["product_id"],
                version_id=bug.get("version_id"),
                module_code=bug.get("module_code"),
                source_module="bug",
                observed_at=bug.get("updated_at") or bug.get("created_at"),
                metadata={
                    "severity": bug["severity"],
                    "source": bug["source"],
                    "status": bug["status"],
                },
            )
        )
    for metric in matching_evidence["gitlab_daily_code_metric"]:
        relations.append(
            _lifecycle_relation(
                subject_type="gitlab_daily_code_metric",
                subject_id=metric["id"],
                relation_type="observes_gitlab_code_metric",
                summary=f"{metric.get('metric_date')} commit_count={metric.get('commit_count', 0)}",
                product_id=metric["product_id"],
                source_module="devops_metrics",
                observed_at=metric.get("metric_date") or metric.get("updated_at"),
                metadata={
                    "changed_files": metric.get("changed_files", 0),
                    "commit_count": metric.get("commit_count", 0),
                    "quality_score": metric.get("quality_score"),
                    "risk_count": metric.get("risk_count", 0),
                },
            )
        )
    for release in matching_evidence["jenkins_release"]:
        relations.append(
            _lifecycle_relation(
                subject_type="jenkins_release",
                subject_id=release["id"],
                relation_type="observes_jenkins_release",
                summary=f"{release['job_name']} {release['status']}",
                product_id=release["product_id"],
                version_id=release.get("version_id"),
                source_module="devops_metrics",
                observed_at=release.get("deployed_at") or release.get("updated_at"),
                metadata={
                    "build_id": release["build_id"],
                    "environment": release.get("environment"),
                    "failure_reason": release.get("failure_reason"),
                    "status": release["status"],
                },
            )
        )
    for metric in matching_evidence["online_log_metric"]:
        relations.append(
            _lifecycle_relation(
                subject_type="online_log_metric",
                subject_id=metric["id"],
                relation_type="observes_online_log_metric",
                summary=f"{metric['environment']} error_rate={metric.get('error_rate', 0)}",
                product_id=metric["product_id"],
                module_code=metric.get("module_code"),
                source_module="devops_metrics",
                observed_at=metric.get("window_end") or metric.get("updated_at"),
                metadata={
                    "environment": metric["environment"],
                    "error_count": metric.get("error_count", 0),
                    "error_rate": metric.get("error_rate", 0),
                    "request_count": metric.get("request_count", 0),
                },
            )
        )
    for metric in matching_evidence["user_usage_metric"]:
        relations.append(
            _lifecycle_relation(
                subject_type="user_usage_metric",
                subject_id=metric["id"],
                relation_type="observes_user_usage_metric",
                summary=f"{metric['feature_code']} events={metric.get('event_count', 0)}",
                product_id=metric["product_id"],
                module_code=metric.get("module_code"),
                source_module="user_insights",
                observed_at=metric.get("window_end") or metric.get("updated_at"),
                metadata={
                    "active_users": metric.get("active_users", 0),
                    "event_count": metric.get("event_count", 0),
                    "feature_code": metric["feature_code"],
                    "user_segment": metric.get("user_segment"),
                },
            )
        )
    for feedback in matching_evidence["user_feedback"]:
        relations.append(
            _lifecycle_relation(
                subject_type="user_feedback",
                subject_id=feedback["id"],
                relation_type="observes_user_feedback",
                summary=feedback["content"],
                product_id=feedback["product_id"],
                module_code=feedback.get("module_code"),
                source_module="user_insights",
                observed_at=feedback.get("updated_at") or feedback.get("created_at"),
                metadata={
                    "feedback_type": feedback["feedback_type"],
                    "sentiment": feedback.get("sentiment"),
                    "status": feedback["status"],
                },
            )
        )
    for suggestion in matching_evidence["iteration_plan_suggestion"]:
        relations.append(
            _lifecycle_relation(
                subject_type="iteration_plan_suggestion",
                subject_id=suggestion["id"],
                relation_type="observes_iteration_suggestion",
                summary=suggestion["title"],
                product_id=suggestion["product_id"],
                version_id=suggestion.get("version_id"),
                module_code=",".join(suggestion.get("module_codes", [])) or None,
                source_module="iteration_planning",
                observed_at=suggestion.get("updated_at") or suggestion.get("created_at"),
                metadata={
                    "confidence_level": suggestion.get("confidence_level"),
                    "priority": suggestion.get("priority"),
                    "status": suggestion["status"],
                },
            )
        )

    return relations


def _lifecycle_risk_signals(
    current_store: MemoryStore,
    *,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals = []
    task_ids = {task["id"] for task in tasks}
    for report in current_store.code_review_reports.values():
        if report["task_id"] not in task_ids or report["risk_level"] == "low":
            continue
        signals.append(
            {
                "risk_type": f"code_review_{report['risk_level']}_risk",
                "severity": report["risk_level"],
                "source_subject_type": "code_review_report",
                "source_subject_id": report["id"],
                "impact_summary": f"Review 报告提示：{report['summary']}",
                "recommendation": "优先处理高置信度 Review findings，并在关闭前补充边界测试。",
            }
        )
    matching_evidence = _lifecycle_matching_v1_2_evidence(current_store, tasks)
    for bug in matching_evidence["bug"]:
        if bug.get("status") == "closed" or bug.get("severity") not in {
            "blocker",
            "critical",
            "major",
        }:
            continue
        severity = "critical" if bug["severity"] in {"blocker", "critical"} else "high"
        signals.append(
            {
                "risk_type": f"{bug['severity']}_bug_open"
                if bug["severity"] != "critical"
                else "critical_bug_open",
                "severity": severity,
                "source_subject_type": "bug",
                "source_subject_id": bug["id"],
                "impact_summary": f"未关闭 Bug：{bug['title']}",
                "recommendation": "先完成修复、验证和关闭，再继续下游发布或迭代决策。",
            }
        )
    for metric in matching_evidence["gitlab_daily_code_metric"]:
        risk_count = metric.get("risk_count", 0) or 0
        quality_score = metric.get("quality_score")
        if risk_count <= 0 and (quality_score is None or quality_score >= 80):
            continue
        signals.append(
            {
                "risk_type": "gitlab_code_risk",
                "severity": "high" if risk_count >= 3 or (quality_score or 100) < 75 else "medium",
                "source_subject_type": "gitlab_daily_code_metric",
                "source_subject_id": metric["id"],
                "impact_summary": f"GitLab 代码指标存在 {risk_count} 个风险点。",
                "recommendation": "结合 MR、变更文件数和质量评分复核代码风险来源。",
            }
        )
    for release in matching_evidence["jenkins_release"]:
        if release.get("status") != "failed":
            continue
        signals.append(
            {
                "risk_type": "jenkins_release_failed",
                "severity": "high",
                "source_subject_type": "jenkins_release",
                "source_subject_id": release["id"],
                "impact_summary": f"Jenkins 发布失败：{release['job_name']}",
                "recommendation": "先定位失败原因并确认回滚或重试策略。",
            }
        )
    for metric in matching_evidence["online_log_metric"]:
        error_rate = metric.get("error_rate", 0) or 0
        error_count = metric.get("error_count", 0) or 0
        if error_rate < 0.01 and error_count < 10:
            continue
        signals.append(
            {
                "risk_type": "online_error_rate_high",
                "severity": "high" if error_rate >= 0.02 else "medium",
                "source_subject_type": "online_log_metric",
                "source_subject_id": metric["id"],
                "impact_summary": (
                    f"{metric['environment']} 错误率 {error_rate:.4f}，"
                    f"错误数 {error_count}。"
                ),
                "recommendation": "优先排查核心错误、回归范围和受影响模块。",
            }
        )
    for feedback in matching_evidence["user_feedback"]:
        satisfaction_score = feedback.get("satisfaction_score")
        is_negative = feedback.get("sentiment") == "negative" or feedback.get(
            "feedback_type"
        ) == "complaint" or (
            isinstance(satisfaction_score, int | float) and satisfaction_score <= 2
        )
        if not is_negative:
            continue
        signals.append(
            {
                "risk_type": "negative_user_feedback",
                "severity": "medium",
                "source_subject_type": "user_feedback",
                "source_subject_id": feedback["id"],
                "impact_summary": f"负向用户反馈：{feedback['content']}",
                "recommendation": "将反馈归因到模块和需求，纳入迭代建议或 Bug 修复队列。",
            }
        )
    for suggestion in matching_evidence["iteration_plan_suggestion"]:
        if suggestion.get("confidence_level") != "low":
            continue
        signals.append(
            {
                "risk_type": "iteration_suggestion_low_confidence",
                "severity": "medium",
                "source_subject_type": "iteration_plan_suggestion",
                "source_subject_id": suggestion["id"],
                "impact_summary": f"低置信度迭代建议：{suggestion['title']}",
                "recommendation": "补充更多 Bug、反馈、使用或线上证据后再采纳。",
            }
        )
    return signals


def _stable_record_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha1(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _first_lifecycle_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    return min(tasks, key=lambda task: task["id"]) if tasks else None


def _lifecycle_risk_context(
    current_store: MemoryStore,
    signal: dict[str, Any],
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    source_type = signal["source_subject_type"]
    source_id = signal["source_subject_id"]
    task = _first_lifecycle_task(tasks)
    context = {
        "module_code": task.get("module_code") if task else None,
        "observed_at": None,
        "product_id": task.get("product_id") if task else None,
        "requirement_id": task.get("requirement_id") if task else None,
        "task_id": task.get("id") if task else None,
        "version_id": task.get("version_id") if task else None,
    }
    if source_type == "code_review_report":
        report = current_store.code_review_reports.get(source_id)
        report_task = current_store.ai_tasks.get(str(report.get("task_id"))) if report else None
        if report_task:
            context.update(
                {
                    "module_code": report_task.get("module_code"),
                    "observed_at": report.get("updated_at") or report.get("created_at"),
                    "product_id": report_task.get("product_id"),
                    "requirement_id": report_task.get("requirement_id"),
                    "task_id": report_task.get("id"),
                    "version_id": report_task.get("version_id"),
                }
            )
    elif source_type == "bug":
        bug = current_store.bugs.get(source_id)
        if bug:
            context.update(
                {
                    "module_code": bug.get("module_code"),
                    "observed_at": bug.get("updated_at") or bug.get("created_at"),
                    "product_id": bug.get("product_id"),
                    "requirement_id": bug.get("requirement_id") or context["requirement_id"],
                    "task_id": bug.get("related_task_id") or context["task_id"],
                    "version_id": bug.get("version_id") or context["version_id"],
                }
            )
    elif source_type == "gitlab_daily_code_metric":
        metric = current_store.gitlab_daily_code_metrics.get(source_id)
        if metric:
            context.update(
                {
                    "observed_at": metric.get("metric_date") or metric.get("updated_at"),
                    "product_id": metric.get("product_id"),
                }
            )
    elif source_type == "jenkins_release":
        release = current_store.jenkins_release_records.get(source_id)
        if release:
            context.update(
                {
                    "observed_at": release.get("deployed_at")
                    or release.get("updated_at")
                    or release.get("created_at"),
                    "product_id": release.get("product_id"),
                    "version_id": release.get("version_id") or context["version_id"],
                }
            )
    elif source_type == "online_log_metric":
        metric = current_store.online_log_metrics.get(source_id)
        if metric:
            context.update(
                {
                    "module_code": metric.get("module_code"),
                    "observed_at": metric.get("window_end") or metric.get("updated_at"),
                    "product_id": metric.get("product_id"),
                }
            )
    elif source_type == "user_feedback":
        feedback = current_store.user_feedback.get(source_id)
        if feedback:
            context.update(
                {
                    "module_code": feedback.get("module_code"),
                    "observed_at": feedback.get("updated_at") or feedback.get("created_at"),
                    "product_id": feedback.get("product_id"),
                    "requirement_id": feedback.get("related_requirement_id")
                    or context["requirement_id"],
                }
            )
    elif source_type == "iteration_plan_suggestion":
        suggestion = current_store.iteration_plan_suggestions.get(source_id)
        if suggestion:
            context.update(
                {
                    "module_code": ",".join(suggestion.get("module_codes", [])) or None,
                    "observed_at": suggestion.get("updated_at") or suggestion.get("created_at"),
                    "product_id": suggestion.get("product_id"),
                    "version_id": suggestion.get("version_id") or context["version_id"],
                }
            )
    if context["observed_at"] is None:
        context["observed_at"] = datetime.now(UTC).isoformat()
    return context


def _sync_lifecycle_context_records(
    current_store: MemoryStore,
    *,
    subject: dict[str, Any],
    upstream: list[dict[str, Any]],
    downstream: list[dict[str, Any]],
    risk_signals: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> None:
    anchor_type = subject.get("type")
    anchor_id = subject.get("id")
    if not anchor_type or not anchor_id:
        return
    current_store.lifecycle_context_edges = {
        edge_id: edge
        for edge_id, edge in current_store.lifecycle_context_edges.items()
        if not (
            (
                edge.get("source_subject_type") == anchor_type
                and edge.get("source_subject_id") == anchor_id
            )
            or (
                edge.get("target_subject_type") == anchor_type
                and edge.get("target_subject_id") == anchor_id
            )
        )
    }
    now = datetime.now(UTC).isoformat()

    def upsert_edge(
        relation: dict[str, Any],
        *,
        source_subject_type: str,
        source_subject_id: str,
        target_subject_type: str,
        target_subject_id: str,
    ) -> None:
        edge_id = _stable_record_id(
            "lifecycle_edge",
            {
                "relation_type": relation["relation_type"],
                "source_subject_id": source_subject_id,
                "source_subject_type": source_subject_type,
                "target_subject_id": target_subject_id,
                "target_subject_type": target_subject_type,
            },
        )
        current_store.lifecycle_context_edges[edge_id] = {
            "confidence": relation.get("confidence", 1.0),
            "id": edge_id,
            "metadata": current_store.snapshot(relation.get("metadata", {})),
            "module_code": relation.get("module_code"),
            "observed_at": relation.get("observed_at") or now,
            "product_id": relation.get("product_id") or subject.get("product_id"),
            "relation_type": relation["relation_type"],
            "source_module": relation.get("source_module", "lifecycle_context"),
            "source_subject_id": source_subject_id,
            "source_subject_type": source_subject_type,
            "summary": relation.get("summary"),
            "target_subject_id": target_subject_id,
            "target_subject_type": target_subject_type,
            "version_id": relation.get("version_id"),
        }

    for relation in upstream:
        upsert_edge(
            relation,
            source_subject_type=relation["subject_type"],
            source_subject_id=relation["subject_id"],
            target_subject_type=anchor_type,
            target_subject_id=anchor_id,
        )
    for relation in downstream:
        upsert_edge(
            relation,
            source_subject_type=anchor_type,
            source_subject_id=anchor_id,
            target_subject_type=relation["subject_type"],
            target_subject_id=relation["subject_id"],
        )

    task_scope = _lifecycle_task_scope(tasks)
    risk_source_keys = {
        (signal["source_subject_type"], signal["source_subject_id"])
        for signal in risk_signals
    }
    current_store.lifecycle_risk_signals = {
        risk_id: risk
        for risk_id, risk in current_store.lifecycle_risk_signals.items()
        if not (
            risk.get("task_id") in task_scope["task_ids"]
            or risk.get("requirement_id") in task_scope["requirement_ids"]
            or (risk.get("source_subject_type"), risk.get("source_subject_id"))
            in risk_source_keys
        )
    }
    for signal in risk_signals:
        context = _lifecycle_risk_context(current_store, signal, tasks)
        risk_id = _stable_record_id(
            "lifecycle_risk",
            {
                "risk_type": signal["risk_type"],
                "source_subject_id": signal["source_subject_id"],
                "source_subject_type": signal["source_subject_type"],
                "task_id": context.get("task_id"),
            },
        )
        risk = {
            **context,
            "id": risk_id,
            "impact_summary": signal["impact_summary"],
            "recommendation": signal["recommendation"],
            "risk_type": signal["risk_type"],
            "severity": signal["severity"],
            "source_subject_id": signal["source_subject_id"],
            "source_subject_type": signal["source_subject_type"],
        }
        current_store.lifecycle_risk_signals[risk_id] = risk


def _sync_dashboard_metric_snapshot(
    current_store: MemoryStore,
    *,
    product_id: str | None,
    time_range: str | None,
    cutoff: datetime | None,
    data: dict[str, Any],
) -> None:
    now = datetime.now(UTC).isoformat()
    snapshot_id = _stable_record_id(
        "dashboard_snapshot",
        {
            "product_id": product_id or "all",
            "time_range": time_range or "all",
        },
    )
    existing = current_store.dashboard_metric_snapshots.get(snapshot_id, {})
    current_store.dashboard_metric_snapshots[snapshot_id] = {
        "created_at": existing.get("created_at") or now,
        "id": snapshot_id,
        "metrics": current_store.snapshot(data),
        "product_id": product_id,
        "time_range": time_range or "all",
        "updated_at": now,
        "window_end": now,
        "window_start": cutoff.isoformat() if cutoff else None,
    }


def _dashboard_metric_snapshot_record(
    *,
    product_id: str | None,
    time_range: str | None,
    cutoff: datetime | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    snapshot_id = _stable_record_id(
        "dashboard_snapshot",
        {
            "product_id": product_id or "all",
            "time_range": time_range or "all",
        },
    )
    return {
        "created_at": now,
        "id": snapshot_id,
        "metrics": json.loads(json.dumps(data, ensure_ascii=False)),
        "product_id": product_id,
        "time_range": time_range or "all",
        "updated_at": now,
        "window_end": now,
        "window_start": cutoff.isoformat() if cutoff else None,
    }


def _dashboard_source_rows_from_store(
    current_store: MemoryStore,
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    return {
        "audit_events": list(current_store.audit_events),
        "bugs": list(current_store.bugs.values()),
        "code_review_reports": list(current_store.code_review_reports.values()),
        "gitlab_daily_code_metrics": list(current_store.gitlab_daily_code_metrics.values()),
        "gitlab_mr_snapshots": list(current_store.gitlab_mr_snapshots.values()),
        "human_reviews": list(current_store.human_reviews.values()),
        "iteration_plan_suggestions": list(current_store.iteration_plan_suggestions.values()),
        "jenkins_release_records": list(current_store.jenkins_release_records.values()),
        "knowledge_deposits": list(current_store.knowledge_deposits.values()),
        "knowledge_documents": [
            document
            for document in current_store.knowledge_documents.values()
            if _user_can_read_roles(user, document["permission_roles"])
        ],
        "mock_writebacks": list(current_store.mock_writebacks.values()),
        "online_log_metrics": list(current_store.online_log_metrics.values()),
        "product_git_repositories": list(current_store.product_git_repositories.values()),
        "product_modules": list(current_store.product_modules.values()),
        "product_versions": list(current_store.product_versions.values()),
        "products": [
            product
            for product in current_store.products.values()
            if product.get("status") == "active"
        ],
        "requirements": list(current_store.requirements.values()),
        "tasks": list(current_store.ai_tasks.values()),
        "user_feedback": list(current_store.user_feedback.values()),
        "user_usage_metrics": list(current_store.user_usage_metrics.values()),
    }


class LifecycleContextReadModel:
    def __init__(self) -> None:
        self.ai_tasks: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.bugs: dict[str, dict[str, Any]] = {}
        self.code_review_reports: dict[str, dict[str, Any]] = {}
        self.gitlab_daily_code_metrics: dict[str, dict[str, Any]] = {}
        self.gitlab_mr_snapshots: dict[str, dict[str, Any]] = {}
        self.human_reviews: dict[str, dict[str, Any]] = {}
        self.iteration_plan_suggestions: dict[str, dict[str, Any]] = {}
        self.jenkins_release_records: dict[str, dict[str, Any]] = {}
        self.knowledge_deposits: dict[str, dict[str, Any]] = {}
        self.lifecycle_context_edges: dict[str, dict[str, Any]] = {}
        self.lifecycle_risk_signals: dict[str, dict[str, Any]] = {}
        self.mock_writebacks: dict[str, dict[str, Any]] = {}
        self.online_log_metrics: dict[str, dict[str, Any]] = {}
        self.product_git_repositories: dict[str, dict[str, Any]] = {}
        self.product_modules: dict[str, dict[str, Any]] = {}
        self.product_versions: dict[str, dict[str, Any]] = {}
        self.products: dict[str, dict[str, Any]] = {}
        self.requirements: dict[str, dict[str, Any]] = {}
        self.user_feedback: dict[str, dict[str, Any]] = {}
        self.user_usage_metrics: dict[str, dict[str, Any]] = {}

    def snapshot(self, value: Any) -> Any:
        return deepcopy(value)


def _lifecycle_source_store(rows: dict[str, Any]) -> LifecycleContextReadModel:
    source_store = LifecycleContextReadModel()
    source_store.audit_events = list(rows.get("audit_events", []))
    collection_keys = {
        "ai_tasks": "tasks",
        "bugs": "bugs",
        "code_review_reports": "code_review_reports",
        "gitlab_daily_code_metrics": "gitlab_daily_code_metrics",
        "gitlab_mr_snapshots": "gitlab_mr_snapshots",
        "human_reviews": "human_reviews",
        "iteration_plan_suggestions": "iteration_plan_suggestions",
        "jenkins_release_records": "jenkins_release_records",
        "knowledge_deposits": "knowledge_deposits",
        "lifecycle_context_edges": "lifecycle_context_edges",
        "lifecycle_risk_signals": "lifecycle_risk_signals",
        "mock_writebacks": "mock_writebacks",
        "online_log_metrics": "online_log_metrics",
        "product_git_repositories": "product_git_repositories",
        "product_modules": "product_modules",
        "product_versions": "product_versions",
        "products": "products",
        "requirements": "requirements",
        "user_feedback": "user_feedback",
        "user_usage_metrics": "user_usage_metrics",
    }
    for store_key, row_key in collection_keys.items():
        setattr(
            source_store,
            store_key,
            {
                str(item["id"]): dict(item)
                for item in rows.get(row_key, [])
                if item.get("id") is not None
            },
        )
    for result in rows.get("mock_writebacks", []):
        idempotency_key = result.get("idempotency_key") or result.get("task_id") or result.get("id")
        if idempotency_key is not None:
            source_store.mock_writebacks[str(idempotency_key)] = dict(result)
    return source_store


def _task_workflow_source_store(
    rows: dict[str, Any],
    *,
    repository: Any | None = None,
) -> Any:
    source_store = (
        _RepositoryRequestContext(repository)
        if repository is not None
        else MemoryStore()
    )
    source_store.audit_events = list(rows.get("audit_events", []))
    source_store.model_gateway_logs = list(rows.get("model_gateway_logs", []))
    collection_keys = {
        "ai_tasks": "tasks",
        "bugs": "bugs",
        "code_review_reports": "code_review_reports",
        "gitlab_daily_code_metrics": "gitlab_daily_code_metrics",
        "gitlab_mr_snapshots": "gitlab_mr_snapshots",
        "graph_checkpoints": "graph_checkpoints",
        "graph_runs": "graph_runs",
        "human_reviews": "human_reviews",
        "jenkins_release_records": "jenkins_release_records",
        "knowledge_deposits": "knowledge_deposits",
        "model_gateway_configs": "model_gateway_configs",
        "mock_writebacks": "mock_writebacks",
        "online_log_metrics": "online_log_metrics",
        "product_git_repositories": "product_git_repositories",
        "product_modules": "product_modules",
        "product_versions": "product_versions",
        "products": "products",
        "related_systems": "related_systems",
        "requirements": "requirements",
    }
    for store_key, row_key in collection_keys.items():
        setattr(
            source_store,
            store_key,
            {
                str(item["id"]): dict(item)
                for item in rows.get(row_key, [])
                if item.get("id") is not None
            },
        )
    for result in rows.get("mock_writebacks", []):
        idempotency_key = result.get("idempotency_key") or result.get("task_id") or result.get("id")
        if idempotency_key is not None:
            source_store.mock_writebacks[str(idempotency_key)] = dict(result)
    return source_store


def _task_workflow_read_store(current_store: MemoryStore) -> MemoryStore:
    repository = _task_workflow_query_repository(current_store)
    if repository is None:
        return _repository_read_model_store(current_store)
    return _task_workflow_source_store(
        repository.get_task_workflow_source_rows(),
        repository=repository,
    )


def _task_workflow_write_store(current_store: MemoryStore) -> MemoryStore:
    repository = _task_workflow_query_repository(current_store)
    if repository is None:
        return current_store
    return _task_workflow_source_store(
        repository.get_task_workflow_source_rows(),
        repository=repository,
    )


def _dashboard_items_by_id(rows: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in rows.get(key, []) if item.get("id") is not None}


def _dashboard_task_product_id(rows: dict[str, Any], task_id: str | None) -> str | None:
    if not task_id:
        return None
    task = _dashboard_items_by_id(rows, "tasks").get(str(task_id))
    return str(task["product_id"]) if task is not None and task.get("product_id") else None


def _dashboard_mock_issue(rows: dict[str, Any], subject_id: str) -> dict[str, Any] | None:
    for result in rows.get("mock_writebacks", []):
        for issue in result.get("issues", []):
            if str(issue.get("id")) == subject_id:
                return issue
    return None


def _dashboard_knowledge_document_product_id(
    rows: dict[str, Any],
    document: dict[str, Any],
) -> str | None:
    if document.get("product_id"):
        return str(document["product_id"])
    document_id = document.get("id")
    for deposit in rows.get("knowledge_deposits", []):
        if deposit.get("knowledge_document_id") == document_id:
            return _dashboard_task_product_id(rows, deposit.get("ai_task_id"))
    return None


def _dashboard_subject_product_id(
    rows: dict[str, Any],
    subject_type: str | None,
    subject_id: str | None,
) -> str | None:
    if not subject_type or not subject_id:
        return None
    normalized_id = str(subject_id)
    if subject_type == "product":
        return normalized_id
    product_scoped_maps = {
        "product_version": "product_versions",
        "product_module": "product_modules",
        "product_git_repository": "product_git_repositories",
        "requirement": "requirements",
        "bug": "bugs",
        "gitlab_daily_code_metric": "gitlab_daily_code_metrics",
        "jenkins_release": "jenkins_release_records",
        "online_log_metric": "online_log_metrics",
        "user_feedback": "user_feedback",
        "user_usage_metric": "user_usage_metrics",
        "iteration_plan_suggestion": "iteration_plan_suggestions",
    }
    collection_key = product_scoped_maps.get(subject_type)
    if collection_key is not None:
        item = _dashboard_items_by_id(rows, collection_key).get(normalized_id)
        return str(item["product_id"]) if item is not None and item.get("product_id") else None
    if subject_type == "ai_task":
        return _dashboard_task_product_id(rows, normalized_id)
    if subject_type == "human_review":
        review = _dashboard_items_by_id(rows, "human_reviews").get(normalized_id)
        return _dashboard_task_product_id(rows, review.get("ai_task_id") if review else None)
    if subject_type == "code_review_report":
        report = _dashboard_items_by_id(rows, "code_review_reports").get(normalized_id)
        return _dashboard_task_product_id(rows, report.get("task_id") if report else None)
    if subject_type == "gitlab_mr_snapshot":
        snapshot = _dashboard_items_by_id(rows, "gitlab_mr_snapshots").get(normalized_id)
        if snapshot is not None and snapshot.get("product_id"):
            return str(snapshot["product_id"])
        return None
    if subject_type == "mock_issue":
        issue = _dashboard_mock_issue(rows, normalized_id)
        return _dashboard_task_product_id(rows, issue.get("source_task_id") if issue else None)
    if subject_type == "knowledge_document":
        document = _dashboard_items_by_id(rows, "knowledge_documents").get(normalized_id)
        return _dashboard_knowledge_document_product_id(rows, document) if document else None
    if subject_type == "knowledge_deposit":
        deposit = _dashboard_items_by_id(rows, "knowledge_deposits").get(normalized_id)
        return _dashboard_task_product_id(rows, deposit.get("ai_task_id") if deposit else None)
    return None


def _dashboard_audit_event_matches_product(
    rows: dict[str, Any],
    event: dict[str, Any],
    product_id: str | None,
) -> bool:
    if product_id is None:
        return True
    if _dashboard_task_product_id(rows, event.get("ai_task_id")) == product_id:
        return True
    return (
        _dashboard_subject_product_id(
            rows,
            event.get("subject_type"),
            event.get("subject_id"),
        )
        == product_id
    )


def _build_dashboard_metrics_data(
    rows: dict[str, Any],
    *,
    product_id: str | None,
    time_range: str | None,
    cutoff: datetime | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    products = [
        product
        for product in rows.get("products", [])
        if product.get("status") == "active" and (product_id is None or product["id"] == product_id)
    ]
    requirements = [
        requirement
        for requirement in rows.get("requirements", [])
        if product_id is None or requirement["product_id"] == product_id
    ]
    tasks = [
        task
        for task in rows.get("tasks", [])
        if (product_id is None or task["product_id"] == product_id) and _can_read_task(user, task)
    ]
    task_ids = {task["id"] for task in tasks}
    pending_reviews = [
        review
        for review in rows.get("human_reviews", [])
        if review["status"] == "pending" and review["ai_task_id"] in task_ids
    ]
    knowledge_documents = [
        document
        for document in rows.get("knowledge_documents", [])
        if product_id is None
        or _dashboard_knowledge_document_product_id(rows, document) == product_id
    ]
    knowledge_deposits = [
        deposit
        for deposit in rows.get("knowledge_deposits", [])
        if deposit["ai_task_id"] in task_ids
    ]
    audit_events = [
        event
        for event in rows.get("audit_events", [])
        if _dashboard_audit_event_matches_product(rows, event, product_id)
    ]
    bugs = [
        bug
        for bug in rows.get("bugs", [])
        if (product_id is None or bug.get("product_id") == product_id)
        and _dashboard_matches_time_range(bug, cutoff, ("updated_at", "created_at"))
    ]
    gitlab_metrics = [
        metric
        for metric in rows.get("gitlab_daily_code_metrics", [])
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("metric_date", "updated_at", "created_at"),
        )
    ]
    jenkins_releases = [
        release
        for release in rows.get("jenkins_release_records", [])
        if (product_id is None or release.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            release,
            cutoff,
            ("deployed_at", "started_at", "updated_at", "created_at"),
        )
    ]
    online_log_metrics = [
        metric
        for metric in rows.get("online_log_metrics", [])
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("window_end", "window_start", "updated_at", "created_at"),
        )
    ]
    usage_metrics = [
        metric
        for metric in rows.get("user_usage_metrics", [])
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("window_end", "window_start", "updated_at", "created_at"),
        )
    ]
    feedback_items = [
        feedback
        for feedback in rows.get("user_feedback", [])
        if (product_id is None or feedback.get("product_id") == product_id)
        and _dashboard_matches_time_range(feedback, cutoff, ("updated_at", "created_at"))
    ]
    iteration_suggestions = [
        suggestion
        for suggestion in rows.get("iteration_plan_suggestions", [])
        if (product_id is None or suggestion.get("product_id") == product_id)
        and _dashboard_matches_time_range(suggestion, cutoff, ("updated_at", "created_at"))
    ]
    open_bugs = [bug for bug in bugs if bug.get("status") != "closed"]
    high_severity_bugs = [
        bug for bug in open_bugs if bug.get("severity") in {"blocker", "critical", "major"}
    ]
    latest_high_severity_bugs = sorted(
        high_severity_bugs,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )[:5]
    online_request_count = int(_dashboard_number_total(online_log_metrics, "request_count"))
    online_error_count = int(_dashboard_number_total(online_log_metrics, "error_count"))
    online_error_rate = (
        round(online_error_count / online_request_count, 6)
        if online_request_count
        else 0
    )
    latest_tasks = sorted(tasks, key=lambda item: item["id"], reverse=True)[:5]
    recent_audit_events = sorted(
        audit_events,
        key=lambda item: item["sequence"],
        reverse=True,
    )[:8]
    recent_knowledge_documents = sorted(
        knowledge_documents,
        key=lambda item: item["id"],
        reverse=True,
    )[:5]
    return {
        "summary": {
            "active_products": len(products),
            "ai_tasks": len(tasks),
            "audit_events": len(audit_events),
            "knowledge_deposits": len(knowledge_deposits),
            "knowledge_documents": len(knowledge_documents),
            "pending_reviews": len(pending_reviews),
            "requirements": len(requirements),
            "bugs": len(bugs),
            "open_bugs": len(open_bugs),
            "high_severity_bugs": len(high_severity_bugs),
            "gitlab_commits": int(_dashboard_number_total(gitlab_metrics, "commit_count")),
            "jenkins_releases": len(jenkins_releases),
            "online_errors": online_error_count,
            "user_feedback": len(feedback_items),
            "usage_events": int(_dashboard_number_total(usage_metrics, "event_count")),
            "iteration_suggestions": len(iteration_suggestions),
        },
        "bug_status_counts": _status_counts(bugs),
        "latest_high_severity_bugs": json.loads(
            json.dumps(latest_high_severity_bugs, ensure_ascii=False)
        ),
        "gitlab_daily_summary": {
            "metric_count": len(gitlab_metrics),
            "commit_count": int(_dashboard_number_total(gitlab_metrics, "commit_count")),
            "merge_request_count": int(
                _dashboard_number_total(gitlab_metrics, "merge_request_count")
            ),
            "changed_files": int(_dashboard_number_total(gitlab_metrics, "changed_files")),
            "risk_count": int(_dashboard_number_total(gitlab_metrics, "risk_count")),
            "average_quality_score": _dashboard_average_number(
                gitlab_metrics,
                "quality_score",
            ),
        },
        "jenkins_release_status_counts": _status_counts(jenkins_releases),
        "online_log_summary": {
            "metric_count": len(online_log_metrics),
            "request_count": online_request_count,
            "error_count": online_error_count,
            "error_rate": online_error_rate,
            "max_p95_latency_ms": _dashboard_max_number(online_log_metrics, "p95_latency_ms"),
            "max_p99_latency_ms": _dashboard_max_number(online_log_metrics, "p99_latency_ms"),
        },
        "usage_metric_summary": {
            "metric_count": len(usage_metrics),
            "active_users": int(_dashboard_number_total(usage_metrics, "active_users")),
            "event_count": int(_dashboard_number_total(usage_metrics, "event_count")),
            "conversion_count": int(_dashboard_number_total(usage_metrics, "conversion_count")),
            "error_count": int(_dashboard_number_total(usage_metrics, "error_count")),
        },
        "user_feedback_status_counts": _status_counts(feedback_items),
        "iteration_suggestion_status_counts": _status_counts(iteration_suggestions),
        "requirement_status_counts": _status_counts(requirements),
        "task_status_counts": _status_counts(tasks),
        "latest_tasks": json.loads(json.dumps(latest_tasks, ensure_ascii=False)),
        "pending_reviews": json.loads(json.dumps(pending_reviews, ensure_ascii=False)),
        "recent_knowledge_documents": json.loads(
            json.dumps(recent_knowledge_documents, ensure_ascii=False)
        ),
        "recent_audit_events": json.loads(json.dumps(recent_audit_events, ensure_ascii=False)),
        "requirement_titles": [requirement["title"] for requirement in requirements[:10]],
        "time_range": time_range or "all",
    }


def _status_counts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return [
        {"status": status, "count": count}
        for status, count in sorted(counts.items(), key=lambda item: item[0])
    ]


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _dashboard_time_cutoff(time_range: str | None) -> datetime | None:
    normalized = (time_range or "all").strip().lower()
    if normalized in {"", "all"}:
        return None
    if normalized.endswith("d") and normalized[:-1].isdigit():
        days = int(normalized[:-1])
        if days > 0:
            return datetime.now(UTC) - timedelta(days=days)
    return None


def _dashboard_item_datetime(
    item: dict[str, Any],
    fields: tuple[str, ...],
) -> datetime | None:
    for field in fields:
        value = item.get(field)
        if value is None:
            continue
        text = str(value)
        try:
            if len(text) == 10 and text[4] == "-" and text[7] == "-":
                parsed = datetime.fromisoformat(text).replace(tzinfo=UTC)
            else:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                parsed = parsed.astimezone(UTC)
        except ValueError:
            continue
        return parsed
    return None


def _dashboard_matches_time_range(
    item: dict[str, Any],
    cutoff: datetime | None,
    fields: tuple[str, ...],
) -> bool:
    if cutoff is None:
        return True
    item_time = _dashboard_item_datetime(item, fields)
    return item_time is None or item_time >= cutoff


def _dashboard_number_total(items: list[dict[str, Any]], field: str) -> float:
    total = 0.0
    for item in items:
        value = item.get(field)
        if isinstance(value, int | float):
            total += float(value)
    return total


def _dashboard_max_number(items: list[dict[str, Any]], field: str) -> float | None:
    values = [float(item[field]) for item in items if isinstance(item.get(field), int | float)]
    return max(values) if values else None


def _dashboard_average_number(items: list[dict[str, Any]], field: str) -> float | None:
    values = [float(item[field]) for item in items if isinstance(item.get(field), int | float)]
    return round(sum(values) / len(values), 2) if values else None


def _task_product_id(current_store: MemoryStore, task_id: str | None) -> str | None:
    if not task_id:
        return None
    task = current_store.ai_tasks.get(str(task_id))
    return str(task["product_id"]) if task is not None and task.get("product_id") else None


def _knowledge_document_product_id(
    current_store: MemoryStore,
    document: dict[str, Any],
) -> str | None:
    if document.get("product_id"):
        return str(document["product_id"])
    document_id = document.get("id")
    for deposit in current_store.knowledge_deposits.values():
        if deposit.get("knowledge_document_id") == document_id:
            return _task_product_id(current_store, deposit.get("ai_task_id"))
    return None


def _subject_product_id(
    current_store: MemoryStore,
    subject_type: str | None,
    subject_id: str | None,
) -> str | None:
    if not subject_type or not subject_id:
        return None
    normalized_id = str(subject_id)
    if subject_type == "product":
        return normalized_id if normalized_id in current_store.products else None
    if subject_type == "product_version":
        version = current_store.product_versions.get(normalized_id)
        return str(version["product_id"]) if version is not None else None
    if subject_type == "product_module":
        module = current_store.product_modules.get(normalized_id)
        return str(module["product_id"]) if module is not None else None
    if subject_type == "product_git_repository":
        repository = current_store.product_git_repositories.get(normalized_id)
        return str(repository["product_id"]) if repository is not None else None
    if subject_type == "requirement":
        requirement = current_store.requirements.get(normalized_id)
        return str(requirement["product_id"]) if requirement is not None else None
    if subject_type == "ai_task":
        return _task_product_id(current_store, normalized_id)
    if subject_type == "human_review":
        review = current_store.human_reviews.get(normalized_id)
        return _task_product_id(current_store, review.get("ai_task_id") if review else None)
    if subject_type == "code_review_report":
        report = current_store.code_review_reports.get(normalized_id)
        return _task_product_id(current_store, report.get("task_id") if report else None)
    if subject_type == "gitlab_mr_snapshot":
        snapshot = current_store.gitlab_mr_snapshots.get(normalized_id)
        return str(snapshot["product_id"]) if snapshot is not None else None
    if subject_type == "mock_issue":
        issue = _lifecycle_mock_issue(current_store, normalized_id)
        return _task_product_id(current_store, issue.get("source_task_id") if issue else None)
    if subject_type == "knowledge_document":
        document = current_store.knowledge_documents.get(normalized_id)
        return _knowledge_document_product_id(current_store, document) if document else None
    if subject_type == "knowledge_deposit":
        deposit = current_store.knowledge_deposits.get(normalized_id)
        return _task_product_id(current_store, deposit.get("ai_task_id") if deposit else None)
    product_scoped_collections = {
        "bug": current_store.bugs,
        "gitlab_daily_code_metric": current_store.gitlab_daily_code_metrics,
        "jenkins_release": current_store.jenkins_release_records,
        "online_log_metric": current_store.online_log_metrics,
        "user_feedback": current_store.user_feedback,
        "user_usage_metric": current_store.user_usage_metrics,
        "iteration_plan_suggestion": current_store.iteration_plan_suggestions,
    }
    collection = product_scoped_collections.get(subject_type)
    if collection is None:
        return None
    item = collection.get(normalized_id)
    return str(item["product_id"]) if item is not None and item.get("product_id") else None


def _audit_event_matches_product(
    current_store: MemoryStore,
    event: dict[str, Any],
    product_id: str | None,
) -> bool:
    if product_id is None:
        return True
    if _task_product_id(current_store, event.get("ai_task_id")) == product_id:
        return True
    return (
        _subject_product_id(
            current_store,
            event.get("subject_type"),
            event.get("subject_id"),
        )
        == product_id
    )


@app.get("/api/dashboard/it-team")
def dashboard_metrics(
    request: Request,
    product_id: str | None = None,
    time_range: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    runtime_store = store(request)
    cutoff = _dashboard_time_cutoff(time_range)
    repository = _dashboard_query_repository(runtime_store)
    if repository is not None:
        if product_id and repository.get_product(product_id) is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        rows = repository.get_dashboard_it_team_source_rows(
            user_roles=list(user["roles"]),
            product_id=product_id,
        )
        data = _build_dashboard_metrics_data(
            rows,
            product_id=product_id,
            time_range=time_range,
            cutoff=cutoff,
            user=user,
        )
        repository.save_dashboard_metric_snapshot_record(
            _dashboard_metric_snapshot_record(
                product_id=product_id,
                time_range=time_range,
                cutoff=cutoff,
                data=data,
            )
        )
        return envelope(data, get_trace_id(request))

    current_store = _repository_read_model_store(runtime_store)
    if product_id and product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")

    rows = _dashboard_source_rows_from_store(current_store, user=user)
    data = _build_dashboard_metrics_data(
        rows,
        product_id=product_id,
        time_range=time_range,
        cutoff=cutoff,
        user=user,
    )
    _sync_dashboard_metric_snapshot(
        current_store,
        product_id=product_id,
        time_range=time_range,
        cutoff=cutoff,
        data=data,
    )
    _save_dashboard_snapshot_records(current_store)
    return envelope(data, get_trace_id(request))


@app.get("/api/bugs")
def list_bugs(
    request: Request,
    module: str | None = None,
    product_id: str | None = None,
    version_id: str | None = None,
    version: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    title: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _validate_bug_enums(source=source, severity=severity, status=status)
    current_store = store(request)
    repository = _bug_query_repository(current_store)
    if repository is not None:
        items = repository.list_bugs(
            product_id=product_id,
            version_id=version_id,
            status=status,
            severity=severity,
            source=source,
        )
    else:
        items = list(current_store.bugs.values())
        if product_id:
            items = [item for item in items if item["product_id"] == product_id]
        if version_id:
            items = [item for item in items if item.get("version_id") == version_id]
        if status:
            items = [item for item in items if item["status"] == status]
        if severity:
            items = [item for item in items if item["severity"] == severity]
        if source:
            items = [item for item in items if item["source"] == source]
        items.sort(key=lambda item: item["created_at"], reverse=True)
        items = [_bug_summary_projection(item, current_store) for item in items]
    items = [item for item in items if _list_text_matches(item, title, ("title", "id"))]
    items = [item for item in items if _list_text_matches(item, module, ("module_code",))]
    items = [
        item
        for item in items
        if _list_text_matches(item, version, ("version_code", "version_name", "version_id"))
    ]
    items = _sort_list_items(
        items,
        allowed_fields={
            "assignee",
            "created_at",
            "id",
            "module_code",
            "severity",
            "source",
            "status",
            "title",
            "updated_at",
            "version_code",
            "version_name",
        },
        default_sort_by="created_at",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginated_list_payload(
        items,
        page=page,
        page_size=page_size,
        trace_id=get_trace_id(request),
    )


@app.post("/api/bugs")
def create_bug(
    request: Request,
    payload: BugRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_bug_write_role(user)
    _validate_bug_enums(source=payload.source, severity=payload.severity)
    current_store = _task_workflow_write_store(store(request))
    title = _ensure_non_blank(payload.title, "title")
    description = _ensure_non_blank(payload.description, "description")
    _validate_bug_context(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
        module_code=payload.module_code,
        requirement_id=payload.requirement_id,
        related_task_id=payload.related_task_id,
        duplicate_of_bug_id=payload.duplicate_of_bug_id,
    )
    bug_id = current_store.new_id("bug")
    now = datetime.now(UTC).isoformat()
    bug = {
        "id": bug_id,
        "product_id": payload.product_id,
        "version_id": payload.version_id,
        "module_code": payload.module_code,
        "source": payload.source,
        "title": title,
        "severity": payload.severity,
        "description": description,
        "status": _initial_bug_status(payload),
        "assignee": payload.assignee,
        "related_task_id": payload.related_task_id,
        "requirement_id": payload.requirement_id,
        "reproduce_steps": payload.reproduce_steps,
        "evidence": payload.evidence,
        "duplicate_of_bug_id": payload.duplicate_of_bug_id,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    if not _uses_repository_context(current_store):
        current_store.bugs[bug_id] = bug
    audit_event = _record_audit_event(
        current_store,
        event_type="bug.created",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
        payload={
            "severity": bug["severity"],
            "source": bug["source"],
            "status": bug["status"],
        },
    )
    _save_bug_record(current_store, bug, audit_event=audit_event)
    return envelope(_bug_summary_projection(bug, current_store), get_trace_id(request))


@app.patch("/api/bugs/{bug_id}")
def patch_bug(
    bug_id: str,
    request: Request,
    payload: BugPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_bug_write_role(user)
    current_store = _task_workflow_write_store(store(request))
    bug = current_store.bugs.get(bug_id)
    if bug is None:
        raise api_error(404, "NOT_FOUND", "Bug not found")
    updates = _payload_updates(payload)
    _validate_bug_enums(
        severity=updates.get("severity"),
        status=updates.get("status"),
    )
    if "title" in updates:
        updates["title"] = _ensure_non_blank(updates["title"], "title")
    if "description" in updates:
        updates["description"] = _ensure_non_blank(updates["description"], "description")
    duplicate_of_bug_id = updates.get("duplicate_of_bug_id")
    if duplicate_of_bug_id is not None:
        _validate_bug_context(
            current_store,
            product_id=bug["product_id"],
            duplicate_of_bug_id=duplicate_of_bug_id,
            bug_id=bug_id,
        )
        updates["status"] = "closed"
    next_status = updates.get("status")
    if next_status is not None:
        _ensure_bug_status_transition(bug["status"], next_status)
    bug = {**bug, **updates}
    bug["updated_at"] = datetime.now(UTC).isoformat()
    if not _uses_repository_context(current_store):
        current_store.bugs[bug_id] = bug
    audit_event = _record_audit_event(
        current_store,
        event_type="bug.updated",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
        payload={
            "status": bug["status"],
            "updated_fields": sorted(updates.keys()),
        },
    )
    _save_bug_record(current_store, bug, audit_event=audit_event)
    return envelope(_bug_summary_projection(bug, current_store), get_trace_id(request))


@app.delete("/api/bugs/{bug_id}")
def delete_bug(
    bug_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_bug_write_role(user)
    current_store = _task_workflow_write_store(store(request))
    if bug_id not in current_store.bugs:
        raise api_error(404, "NOT_FOUND", "Bug not found")
    if not _uses_repository_context(current_store):
        del current_store.bugs[bug_id]
    now = datetime.now(UTC).isoformat()
    if not _uses_repository_context(current_store):
        for bug in current_store.bugs.values():
            if bug.get("duplicate_of_bug_id") == bug_id:
                bug["duplicate_of_bug_id"] = None
                bug["updated_at"] = now
    audit_event = _record_audit_event(
        current_store,
        event_type="bug.deleted",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
    )
    _delete_bug_record(current_store, bug_id, audit_event=audit_event)
    return envelope({"deleted": True, "id": bug_id}, get_trace_id(request))


@app.get("/api/collectors/runs")
def collector_runs(
    request: Request,
    collector_type: str | None = None,
    product_id: str | None = None,
    status: str | None = None,
    source_system: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _ensure_enum(collector_type, COLLECTOR_TYPES, "collector_type")
    _ensure_enum(status, COLLECTOR_RUN_STATUSES, "status")
    source_system = _ensure_non_blank(source_system, "source_system") if source_system else None
    current_store = store(request)
    repository = _operational_query_repository(current_store)
    if repository is not None:
        items = repository.list_collector_runs(
            collector_type=collector_type,
            product_id=product_id,
            status=status,
            source_system=source_system,
        )
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = []
    for run in current_store.collector_runs.values():
        if collector_type is not None and run.get("collector_type") != collector_type:
            continue
        if product_id is not None and run.get("product_id") != product_id:
            continue
        if status is not None and run.get("status") != status:
            continue
        if source_system is not None and run.get("source_system") != source_system:
            continue
        items.append(run)
    items.sort(
        key=lambda item: (
            item.get("started_at") or "",
            item.get("updated_at") or item.get("created_at") or "",
            item["id"],
        ),
        reverse=True,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/collectors/runs")
def create_collector_run(
    payload: CollectorRunRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_collector_run_write_role(user)
    current_store = _operational_write_store(store(request))
    source_system, started_at = _validate_collector_run_request(current_store, payload)
    now = datetime.now(UTC).isoformat()
    status = payload.status
    run_id = current_store.new_id("collector_run")
    run = {
        "collector_type": payload.collector_type,
        "created_at": now,
        "created_by": user["id"],
        "error_message": payload.error_message,
        "finished_at": now if status in COLLECTOR_TERMINAL_STATUSES else None,
        "id": run_id,
        "payload_summary": payload.payload_summary,
        "product_id": payload.product_id,
        "records_imported": payload.records_imported,
        "source_system": source_system,
        "started_at": started_at or now,
        "status": status,
        "updated_at": now,
    }
    if not _uses_repository_context(current_store):
        current_store.collector_runs[run_id] = run
    audit_event = _record_audit_event(
        current_store,
        event_type="collector_run.created",
        actor_id=user["id"],
        subject_type="collector_run",
        subject_id=run_id,
        payload={
            "collector_type": run["collector_type"],
            "product_id": run["product_id"],
            "source_system": run["source_system"],
            "status": run["status"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_collector_run_record",
        run,
        audit_event=audit_event,
    )
    return envelope(run, get_trace_id(request))


@app.patch("/api/collectors/runs/{run_id}")
def patch_collector_run(
    run_id: str,
    payload: CollectorRunPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_collector_run_write_role(user)
    current_store = _operational_write_store(store(request))
    run = current_store.collector_runs.get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Collector run not found")
    updates = _collector_run_patch_updates(run, payload)
    if updates:
        run = {**run, **updates, "updated_at": datetime.now(UTC).isoformat()}
        if not _uses_repository_context(current_store):
            current_store.collector_runs[run_id] = run
    audit_event = _record_audit_event(
        current_store,
        event_type="collector_run.updated",
        actor_id=user["id"],
        subject_type="collector_run",
        subject_id=run_id,
        payload={
            "collector_type": run["collector_type"],
            "records_imported": run["records_imported"],
            "status": run["status"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_collector_run_record",
        run,
        audit_event=audit_event,
    )
    return envelope(run, get_trace_id(request))


@app.get("/api/attribution/pending-items")
def pending_attribution_items(
    request: Request,
    source_type: str | None = None,
    status: str | None = None,
    resolved_product_id: str | None = None,
    collector_run_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _ensure_enum(source_type, PENDING_ATTRIBUTION_SOURCE_TYPES, "source_type")
    _ensure_enum(status, PENDING_ATTRIBUTION_STATUSES, "status")
    current_store = store(request)
    repository = _operational_query_repository(current_store)
    if repository is not None:
        items = repository.list_pending_attribution_items(
            source_type=source_type,
            status=status,
            resolved_product_id=resolved_product_id,
            collector_run_id=collector_run_id,
        )
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = []
    for item in current_store.pending_attribution_items.values():
        if source_type is not None and item.get("source_type") != source_type:
            continue
        if status is not None and item.get("status") != status:
            continue
        if (
            resolved_product_id is not None
            and item.get("resolved_product_id") != resolved_product_id
        ):
            continue
        if collector_run_id is not None and item.get("collector_run_id") != collector_run_id:
            continue
        items.append(item)
    items.sort(
        key=lambda item: (
            item.get("created_at") or "",
            item.get("updated_at") or "",
            item["id"],
        ),
        reverse=True,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/attribution/pending-items")
def create_pending_attribution_item(
    payload: PendingAttributionRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_pending_attribution_write_role(user)
    current_store = _operational_write_store(store(request))
    source_system, summary, raw_subject_id, suggested_module_code = (
        _validate_pending_attribution_create_request(current_store, payload)
    )
    now = datetime.now(UTC).isoformat()
    item_id = current_store.new_id("pending_attr")
    item = {
        "collector_run_id": payload.collector_run_id,
        "confidence": payload.confidence,
        "created_at": now,
        "created_by": user["id"],
        "id": item_id,
        "raw_payload": payload.raw_payload,
        "raw_subject_id": raw_subject_id,
        "resolution_action": None,
        "resolution_note": None,
        "resolved_at": None,
        "resolved_by": None,
        "resolved_module_code": None,
        "resolved_product_id": None,
        "resolved_requirement_id": None,
        "resolved_subject_id": None,
        "resolved_subject_type": None,
        "source_system": source_system,
        "source_type": payload.source_type,
        "status": "pending",
        "suggested_module_code": suggested_module_code,
        "suggested_product_id": payload.suggested_product_id,
        "summary": summary,
        "updated_at": now,
    }
    if not _uses_repository_context(current_store):
        current_store.pending_attribution_items[item_id] = item
    audit_event = _record_audit_event(
        current_store,
        event_type="pending_attribution.created",
        actor_id=user["id"],
        subject_type="pending_attribution_item",
        subject_id=item_id,
        payload={
            "source_system": item["source_system"],
            "source_type": item["source_type"],
            "status": item["status"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_pending_attribution_item_record",
        item,
        audit_event=audit_event,
    )
    return envelope(item, get_trace_id(request))


@app.post("/api/attribution/pending-items/{item_id}/resolve")
def resolve_pending_attribution_item(
    item_id: str,
    payload: PendingAttributionResolveRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_pending_attribution_write_role(user)
    current_store = _operational_write_store(store(request))
    item = current_store.pending_attribution_items.get(item_id)
    if item is None:
        raise api_error(404, "NOT_FOUND", "Pending attribution item not found")
    (
        resolution_note,
        resolved_product_id,
        resolved_module_code,
        resolved_requirement_id,
        resolved_subject_type,
        resolved_subject_id,
    ) = _validate_pending_attribution_resolve_request(current_store, item, payload)
    now = datetime.now(UTC).isoformat()
    status = "resolved" if payload.resolution_action == "link_existing_context" else "ignored"
    item = {
        **item,
        "resolution_action": payload.resolution_action,
        "resolution_note": resolution_note,
        "resolved_at": now,
        "resolved_by": user["id"],
        "resolved_module_code": resolved_module_code,
        "resolved_product_id": resolved_product_id,
        "resolved_requirement_id": resolved_requirement_id,
        "resolved_subject_id": resolved_subject_id,
        "resolved_subject_type": resolved_subject_type,
        "status": status,
        "updated_at": now,
    }
    if not _uses_repository_context(current_store):
        current_store.pending_attribution_items[item_id] = item
    audit_event = _record_audit_event(
        current_store,
        event_type=(
            "pending_attribution.resolved"
            if status == "resolved"
            else "pending_attribution.ignored"
        ),
        actor_id=user["id"],
        subject_type="pending_attribution_item",
        subject_id=item_id,
        payload={
            "resolution_action": item["resolution_action"],
            "resolved_product_id": item.get("resolved_product_id"),
            "status": item["status"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_pending_attribution_item_record",
        item,
        audit_event=audit_event,
    )
    return envelope(item, get_trace_id(request))


def _operational_metric_projection(category: str, item: dict[str, Any]) -> dict[str, Any]:
    updated_at = _first_list_value(
        item,
        (
            "updated_at",
            "created_at",
            "collected_at",
            "deployed_at",
            "started_at",
            "metric_date",
            "window_start",
        ),
    )
    return {
        **item,
        "category": category,
        "name": str(
            _first_list_value(
                item,
                (
                    "name",
                    "metric_name",
                    "repository_name",
                    "release_name",
                    "title",
                    "job_name",
                    "build_id",
                    "repository_id",
                    "metric_date",
                    "environment",
                    "window_start",
                ),
            )
            or "-"
        ),
        "status": str(item.get("status") or "-"),
        "updated_at": str(updated_at or ""),
        "value": _first_list_value(
            item,
            (
                "value",
                "count",
                "score",
                "summary",
                "commit_count",
                "quality_score",
                "build_id",
                "duration_seconds",
                "error_rate",
                "request_count",
                "p95_latency_ms",
            ),
        ),
    }


def _operational_metric_rows(current_store: MemoryStore) -> list[dict[str, Any]]:
    repository = _operational_query_repository(current_store)
    if repository is not None:
        gitlab_metrics = repository.list_gitlab_daily_code_metrics()
        jenkins_releases = repository.list_jenkins_release_records()
        online_logs = repository.list_online_log_metrics()
    else:
        gitlab_metrics = list(current_store.gitlab_daily_code_metrics.values())
        jenkins_releases = list(current_store.jenkins_release_records.values())
        online_logs = list(current_store.online_log_metrics.values())
    return [
        *(_operational_metric_projection("GitLab 指标", item) for item in gitlab_metrics),
        *(_operational_metric_projection("Jenkins 发布", item) for item in jenkins_releases),
        *(_operational_metric_projection("线上日志", item) for item in online_logs),
    ]


@app.get("/api/devops/operational-metrics")
def operational_metrics(
    request: Request,
    category: str | None = None,
    name: str | None = None,
    status: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    items = _operational_metric_rows(store(request))
    if category is not None:
        items = [item for item in items if item.get("category") == category]
    if status is not None:
        items = [item for item in items if item.get("status") == status]
    items = [
        item
        for item in items
        if _list_text_matches(item, name, ("name", "id", "product_id", "version_id", "module_code"))
    ]
    items = _sort_list_items(
        items,
        allowed_fields={"category", "id", "name", "status", "updated_at", "value"},
        default_sort_by="updated_at",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginated_list_payload(
        items,
        page=page,
        page_size=page_size,
        trace_id=get_trace_id(request),
    )


@app.get("/api/devops/gitlab/daily-code-metrics")
def gitlab_metrics(
    request: Request,
    product_id: str | None = None,
    repository_id: str | None = None,
    date: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    metric_date = _parse_metric_date(date, "date") if date is not None else None
    current_store = store(request)
    repository = _operational_query_repository(current_store)
    if repository is not None:
        items = repository.list_gitlab_daily_code_metrics(
            product_id=product_id,
            repository_id=repository_id,
            metric_date=metric_date,
        )
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = []
    for metric in current_store.gitlab_daily_code_metrics.values():
        if product_id is not None and metric.get("product_id") != product_id:
            continue
        if repository_id is not None and metric.get("repository_id") != repository_id:
            continue
        if metric_date is not None and metric.get("metric_date") != metric_date:
            continue
        items.append(metric)
    items.sort(
        key=lambda item: (
            item.get("metric_date") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/devops/gitlab/daily-code-metrics")
def create_gitlab_metric(
    payload: GitlabDailyCodeMetricRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _operational_write_store(store(request))
    _validate_gitlab_metric_context(
        current_store,
        product_id=payload.product_id,
        repository_id=payload.repository_id,
    )
    metric_date = _validate_gitlab_metric_payload(payload)
    now = datetime.now(UTC).isoformat()
    metric_id = current_store.new_id("gitlab_metric")
    metric = {
        "active_author_count": payload.active_author_count,
        "additions": payload.additions,
        "author_metrics": payload.author_metrics,
        "changed_files": payload.changed_files,
        "collected_at": now,
        "commit_count": payload.commit_count,
        "created_at": now,
        "created_by": user["id"],
        "deletions": payload.deletions,
        "id": metric_id,
        "merge_request_count": payload.merge_request_count,
        "metric_date": metric_date,
        "product_id": payload.product_id,
        "quality_score": payload.quality_score,
        "repository_id": payload.repository_id,
        "risk_count": payload.risk_count,
        "source_channel": payload.source_channel,
        "status": payload.status,
        "updated_at": now,
    }
    for optional_key in ("quality_score", "source_channel"):
        if metric[optional_key] is None:
            metric.pop(optional_key)
    if not _uses_repository_context(current_store):
        current_store.gitlab_daily_code_metrics[metric_id] = metric
    audit_event = _record_audit_event(
        current_store,
        event_type="gitlab_daily_code_metric.created",
        actor_id=user["id"],
        subject_type="gitlab_daily_code_metric",
        subject_id=metric_id,
        payload={
            "metric_date": metric["metric_date"],
            "product_id": metric["product_id"],
            "repository_id": metric["repository_id"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_gitlab_daily_code_metric_record",
        metric,
        audit_event=audit_event,
    )
    return envelope(metric, get_trace_id(request))


@app.get("/api/devops/jenkins/releases")
def jenkins_releases(
    request: Request,
    product_id: str | None = None,
    version_id: str | None = None,
    status: str | None = None,
    environment: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _ensure_enum(status, JENKINS_RELEASE_STATUSES, "status")
    current_store = store(request)
    repository = _operational_query_repository(current_store)
    if repository is not None:
        items = repository.list_jenkins_release_records(
            product_id=product_id,
            version_id=version_id,
            status=status,
            environment=environment,
        )
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = []
    for release in current_store.jenkins_release_records.values():
        if product_id is not None and release.get("product_id") != product_id:
            continue
        if version_id is not None and release.get("version_id") != version_id:
            continue
        if status is not None and release.get("status") != status:
            continue
        if environment is not None and release.get("environment") != environment:
            continue
        items.append(release)
    items.sort(
        key=lambda item: (
            item.get("deployed_at") or item.get("created_at") or "",
            item.get("updated_at") or "",
        ),
        reverse=True,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/devops/jenkins/releases")
def create_jenkins_release(
    payload: JenkinsReleaseRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _operational_write_store(store(request))
    _validate_jenkins_release_context(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
    )
    started_at, deployed_at = _validate_jenkins_release_payload(payload)
    now = datetime.now(UTC).isoformat()
    release_id = current_store.new_id("jenkins_release")
    release = {
        "build_id": _ensure_non_blank(payload.build_id, "build_id"),
        "build_number": payload.build_number,
        "commit_sha": payload.commit_sha,
        "created_at": now,
        "created_by": user["id"],
        "deployed_at": deployed_at,
        "duration_seconds": payload.duration_seconds,
        "environment": _ensure_non_blank(payload.environment, "environment"),
        "failure_reason": payload.failure_reason,
        "id": release_id,
        "job_name": _ensure_non_blank(payload.job_name, "job_name"),
        "product_id": payload.product_id,
        "source_channel": payload.source_channel,
        "started_at": started_at,
        "status": payload.status,
        "trigger_actor": payload.trigger_actor,
        "updated_at": now,
        "version_id": payload.version_id,
    }
    for optional_key in (
        "build_number",
        "commit_sha",
        "deployed_at",
        "duration_seconds",
        "failure_reason",
        "source_channel",
        "started_at",
        "trigger_actor",
    ):
        if release[optional_key] is None:
            release.pop(optional_key)
    if not _uses_repository_context(current_store):
        current_store.jenkins_release_records[release_id] = release
    audit_event = _record_audit_event(
        current_store,
        event_type="jenkins_release.created",
        actor_id=user["id"],
        subject_type="jenkins_release",
        subject_id=release_id,
        payload={
            "build_id": release["build_id"],
            "job_name": release["job_name"],
            "product_id": release["product_id"],
            "version_id": release["version_id"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_jenkins_release_record",
        release,
        audit_event=audit_event,
    )
    return envelope(release, get_trace_id(request))


@app.get("/api/ops/online-log-metrics")
def online_log_metrics(
    request: Request,
    product_id: str | None = None,
    module_code: str | None = None,
    environment: str | None = None,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    from_value = _parse_usage_window(from_, "from") if from_ is not None else None
    to_value = _parse_usage_window(to, "to") if to is not None else None
    repository = _operational_query_repository(current_store)
    if repository is not None:
        items = repository.list_online_log_metrics(
            product_id=product_id,
            module_code=module_code,
            environment=environment,
            from_value=from_value,
            to_value=to_value,
        )
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = []
    for metric in current_store.online_log_metrics.values():
        if product_id is not None and metric.get("product_id") != product_id:
            continue
        if module_code is not None and metric.get("module_code") != module_code:
            continue
        if environment is not None and metric.get("environment") != environment:
            continue
        if from_value is not None and metric.get("window_end") < from_value:
            continue
        if to_value is not None and metric.get("window_start") > to_value:
            continue
        items.append(metric)
    items.sort(
        key=lambda item: (
            item.get("window_start") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/ops/online-log-metrics")
def create_online_log_metric(
    payload: OnlineLogMetricRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _operational_write_store(store(request))
    _validate_online_log_metric_context(
        current_store,
        product_id=payload.product_id,
        module_code=payload.module_code,
    )
    window_start, window_end, error_rate = _validate_online_log_metric_payload(payload)
    now = datetime.now(UTC).isoformat()
    metric_id = current_store.new_id("online_log_metric")
    metric = {
        "anomaly_summary": payload.anomaly_summary,
        "core_event_count": payload.core_event_count,
        "created_at": now,
        "created_by": user["id"],
        "environment": _ensure_non_blank(payload.environment, "environment"),
        "error_count": payload.error_count,
        "error_rate": error_rate,
        "id": metric_id,
        "module_code": payload.module_code,
        "p95_latency_ms": payload.p95_latency_ms,
        "p99_latency_ms": payload.p99_latency_ms,
        "product_id": payload.product_id,
        "request_count": payload.request_count,
        "source_channel": payload.source_channel,
        "status": payload.status,
        "top_errors": payload.top_errors,
        "updated_at": now,
        "window_end": window_end,
        "window_start": window_start,
    }
    for optional_key in (
        "anomaly_summary",
        "module_code",
        "p95_latency_ms",
        "p99_latency_ms",
        "source_channel",
    ):
        if metric[optional_key] is None:
            metric.pop(optional_key)
    if not _uses_repository_context(current_store):
        current_store.online_log_metrics[metric_id] = metric
    audit_event = _record_audit_event(
        current_store,
        event_type="online_log_metric.created",
        actor_id=user["id"],
        subject_type="online_log_metric",
        subject_id=metric_id,
        payload={
            "environment": metric["environment"],
            "error_rate": metric["error_rate"],
            "product_id": metric["product_id"],
            "window_end": metric["window_end"],
            "window_start": metric["window_start"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_online_log_metric_record",
        metric,
        audit_event=audit_event,
    )
    return envelope(metric, get_trace_id(request))


def _user_insight_projection(category: str, item: dict[str, Any]) -> dict[str, Any]:
    updated_at = _first_list_value(
        item,
        (
            "updated_at",
            "created_at",
            "observed_at",
            "window_start",
        ),
    )
    return {
        **item,
        "category": category,
        "confidence_level": str(item.get("confidence_level") or "-"),
        "converted_requirement_id": str(item.get("converted_requirement_id") or "-"),
        "feature_code": str(item.get("feature_code") or "-"),
        "feedback_type": str(item.get("feedback_type") or "-"),
        "module_code": str(item.get("module_code") or "-"),
        "owner": str(
            _first_list_value(item, ("user_id", "owner_id", "created_by", "actor_id")) or "-"
        ),
        "planning_cycle": str(item.get("planning_cycle") or "-"),
        "priority": str(item.get("priority") or "-"),
        "product_id": str(item.get("product_id") or "-"),
        "status": str(item.get("status") or "-"),
        "summary": str(
            _first_list_value(
                item,
                (
                    "summary",
                    "title",
                    "content",
                    "feedback_text",
                    "suggestion",
                    "recommendation_reason",
                    "feature_code",
                ),
            )
            or "-"
        ),
        "updated_at": str(updated_at or ""),
        "version_id": str(item.get("version_id") or "-"),
    }


def _user_insight_rows(current_store: MemoryStore) -> list[dict[str, Any]]:
    repository = _insight_query_repository(current_store)
    if repository is not None:
        usage_metrics = repository.list_user_usage_metrics()
        feedback_items = repository.list_user_feedback()
        iteration_suggestions = repository.list_iteration_plan_suggestions()
    else:
        usage_metrics = list(current_store.user_usage_metrics.values())
        feedback_items = list(current_store.user_feedback.values())
        iteration_suggestions = list(current_store.iteration_plan_suggestions.values())
    return [
        *(_user_insight_projection("使用趋势", item) for item in usage_metrics),
        *(_user_insight_projection("用户反馈", item) for item in feedback_items),
        *(_user_insight_projection("迭代建议", item) for item in iteration_suggestions),
    ]


@app.get("/api/insights/items")
def insight_items(
    request: Request,
    category: str | None = None,
    summary: str | None = None,
    status: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    items = _user_insight_rows(store(request))
    if category is not None:
        items = [item for item in items if item.get("category") == category]
    if status is not None:
        items = [item for item in items if item.get("status") == status]
    items = [
        item
        for item in items
        if _list_text_matches(
            item,
            summary,
            ("summary", "id", "product_id", "version_id", "module_code", "feature_code"),
        )
    ]
    items = _sort_list_items(
        items,
        allowed_fields={"category", "id", "owner", "status", "summary", "updated_at"},
        default_sort_by="updated_at",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginated_list_payload(
        items,
        page=page,
        page_size=page_size,
        trace_id=get_trace_id(request),
    )


@app.get("/api/insights/usage-metrics")
def usage_metrics(
    request: Request,
    product_id: str | None = None,
    module_code: str | None = None,
    feature_code: str | None = None,
    user_segment: str | None = None,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    from_value = _parse_usage_window(from_, "from") if from_ is not None else None
    to_value = _parse_usage_window(to, "to") if to is not None else None
    repository = _insight_query_repository(current_store)
    if repository is not None:
        items = repository.list_user_usage_metrics(
            product_id=product_id,
            module_code=module_code,
            feature_code=feature_code,
            user_segment=user_segment,
            from_value=from_value,
            to_value=to_value,
        )
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = []
    for metric in current_store.user_usage_metrics.values():
        if product_id is not None and metric.get("product_id") != product_id:
            continue
        if module_code is not None and metric.get("module_code") != module_code:
            continue
        if feature_code is not None and metric.get("feature_code") != feature_code:
            continue
        if user_segment is not None and metric.get("user_segment") != user_segment:
            continue
        if from_value is not None and metric.get("window_end") < from_value:
            continue
        if to_value is not None and metric.get("window_start") > to_value:
            continue
        items.append(metric)
    items.sort(
        key=lambda item: (
            item.get("window_start") or "",
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/insights/usage-metrics")
def create_usage_metric(
    payload: UserUsageMetricRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = _insight_write_store(store(request))
    _validate_usage_metric_context(
        current_store,
        product_id=payload.product_id,
        module_code=payload.module_code,
    )
    window_start, window_end = _validate_usage_metric_payload(payload)
    now = datetime.now(UTC).isoformat()
    metric_id = current_store.new_id("usage")
    metric = {
        "active_users": payload.active_users,
        "avg_duration_seconds": payload.avg_duration_seconds,
        "bounce_rate": payload.bounce_rate,
        "conversion_count": payload.conversion_count,
        "conversion_rate": payload.conversion_rate,
        "created_at": now,
        "created_by": user["id"],
        "error_count": payload.error_count,
        "event_count": payload.event_count,
        "feature_code": _ensure_non_blank(payload.feature_code, "feature_code"),
        "id": metric_id,
        "module_code": payload.module_code,
        "product_id": payload.product_id,
        "source_channel": payload.source_channel,
        "updated_at": now,
        "user_segment": _ensure_non_blank(payload.user_segment, "user_segment"),
        "window_end": window_end,
        "window_start": window_start,
    }
    for optional_key in (
        "avg_duration_seconds",
        "bounce_rate",
        "conversion_rate",
        "module_code",
        "source_channel",
    ):
        if metric[optional_key] is None:
            metric.pop(optional_key)
    if not _uses_repository_context(current_store):
        current_store.user_usage_metrics[metric_id] = metric
    audit_event = _record_audit_event(
        current_store,
        event_type="usage_metric.created",
        actor_id=user["id"],
        subject_type="usage_metric",
        subject_id=metric_id,
        payload={
            "feature_code": metric["feature_code"],
            "product_id": metric["product_id"],
            "window_end": metric["window_end"],
            "window_start": metric["window_start"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_user_usage_metric_record",
        metric,
        audit_event=audit_event,
    )
    return envelope(metric, get_trace_id(request))


@app.get("/api/insights/user-feedback")
def user_feedback(
    request: Request,
    product_id: str | None = None,
    module_code: str | None = None,
    feature_code: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _validate_user_feedback_enums(status=status)
    current_store = store(request)
    repository = _insight_query_repository(current_store)
    if repository is not None:
        items = repository.list_user_feedback(
            product_id=product_id,
            module_code=module_code,
            feature_code=feature_code,
            status=status,
            created_by=created_by,
        )
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = []
    for feedback in current_store.user_feedback.values():
        if product_id is not None and feedback.get("product_id") != product_id:
            continue
        if module_code is not None and feedback.get("module_code") != module_code:
            continue
        if feature_code is not None and feedback.get("feature_code") != feature_code:
            continue
        if status is not None and feedback.get("status") != status:
            continue
        if created_by is not None and feedback.get("created_by") != created_by:
            continue
        items.append(feedback)
    items.sort(
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/insights/user-feedback")
def create_user_feedback(
    payload: UserFeedbackRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = _insight_write_store(store(request))
    _validate_user_feedback_enums(
        feedback_type=payload.feedback_type,
        sentiment=payload.sentiment,
    )
    _validate_satisfaction_score(payload.satisfaction_score)
    _validate_user_feedback_context(
        current_store,
        product_id=payload.product_id,
        module_code=payload.module_code,
        related_requirement_id=payload.related_requirement_id,
    )
    now = datetime.now(UTC).isoformat()
    feedback = {
        "content": _ensure_non_blank(payload.content, "content"),
        "created_at": now,
        "created_by": user["id"],
        "feature_code": payload.feature_code.strip() if payload.feature_code else None,
        "feedback_type": payload.feedback_type,
        "id": current_store.new_id("feedback"),
        "module_code": payload.module_code,
        "product_id": payload.product_id,
        "related_requirement_id": payload.related_requirement_id,
        "satisfaction_score": payload.satisfaction_score,
        "sentiment": payload.sentiment,
        "source_channel": _ensure_non_blank(payload.source_channel, "source_channel"),
        "status": "open",
        "tags": _normalized_tags(payload.tags),
        "updated_at": now,
    }
    if not _uses_repository_context(current_store):
        current_store.user_feedback[feedback["id"]] = feedback
    audit_event = _record_audit_event(
        current_store,
        event_type="user_feedback.created",
        actor_id=user["id"],
        subject_type="user_feedback",
        subject_id=feedback["id"],
        payload={
            "feedback_type": feedback["feedback_type"],
            "product_id": feedback["product_id"],
            "status": feedback["status"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_user_feedback_record",
        feedback,
        audit_event=audit_event,
    )
    return envelope(feedback, get_trace_id(request))


@app.patch("/api/insights/user-feedback/{feedback_id}")
def patch_user_feedback(
    feedback_id: str,
    payload: UserFeedbackPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_user_feedback_triage_role(user)
    current_store = _insight_write_store(store(request))
    feedback = current_store.user_feedback.get(feedback_id)
    if feedback is None:
        raise api_error(404, "NOT_FOUND", "User feedback not found")
    updates = _payload_updates(payload)
    _validate_user_feedback_enums(
        sentiment=updates.get("sentiment"),
        status=updates.get("status"),
    )
    _validate_satisfaction_score(updates.get("satisfaction_score"))
    if "content" in updates:
        updates["content"] = _ensure_non_blank(updates["content"], "content")
    if "tags" in updates:
        updates["tags"] = _normalized_tags(updates["tags"])
    feedback = {**feedback, **updates, "updated_at": datetime.now(UTC).isoformat()}
    if not _uses_repository_context(current_store):
        current_store.user_feedback[feedback_id] = feedback
    audit_event = _record_audit_event(
        current_store,
        event_type="user_feedback.updated",
        actor_id=user["id"],
        subject_type="user_feedback",
        subject_id=feedback_id,
        payload={
            "status": feedback["status"],
            "updated_fields": sorted(updates.keys()),
        },
    )
    _save_single_repository_record(
        current_store,
        "save_user_feedback_record",
        feedback,
        audit_event=audit_event,
    )
    return envelope(feedback, get_trace_id(request))


@app.get("/api/planning/iteration-suggestions")
def iteration_suggestions(
    request: Request,
    product_id: str | None = None,
    planning_cycle: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _validate_iteration_enums(status=status)
    current_store = store(request)
    repository = _insight_query_repository(current_store)
    if repository is not None:
        items = repository.list_iteration_plan_suggestions(
            product_id=product_id,
            planning_cycle=planning_cycle,
            status=status,
        )
        return envelope({"items": items, "total": len(items)}, get_trace_id(request))
    items = []
    for suggestion in current_store.iteration_plan_suggestions.values():
        if product_id is not None and suggestion.get("product_id") != product_id:
            continue
        if planning_cycle is not None and suggestion.get("planning_cycle") != planning_cycle:
            continue
        if status is not None and suggestion.get("status") != status:
            continue
        items.append(suggestion)
    items.sort(
        key=lambda item: (
            item.get("priority_score", 0),
            item.get("updated_at") or item.get("created_at") or "",
        ),
        reverse=True,
    )
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/planning/iteration-suggestions")
def create_iteration_suggestions(
    payload: IterationSuggestionRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_iteration_planning_role(user)
    current_store = _insight_write_store(store(request))
    module_codes = _normalized_module_codes(payload.module_codes)
    _validate_iteration_context(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
        module_codes=module_codes,
    )
    evidence = _collect_iteration_evidence(
        current_store,
        product_id=payload.product_id,
        module_codes=module_codes,
        include_evidence=payload.include_evidence,
    )
    if not evidence:
        return envelope(empty_list_payload(), get_trace_id(request))
    suggestion = _build_iteration_suggestion(
        current_store,
        evidence=evidence,
        module_codes=module_codes,
        payload=payload,
        user=user,
    )
    if not _uses_repository_context(current_store):
        current_store.iteration_plan_suggestions[suggestion["id"]] = suggestion
    audit_event = _record_audit_event(
        current_store,
        event_type="iteration_suggestion.generated",
        actor_id=user["id"],
        subject_type="iteration_plan_suggestion",
        subject_id=suggestion["id"],
        payload={
            "evidence_count": len(evidence),
            "planning_cycle": suggestion["planning_cycle"],
            "product_id": suggestion["product_id"],
            "status": suggestion["status"],
        },
    )
    _save_single_repository_record(
        current_store,
        "save_iteration_suggestion_record",
        suggestion,
        audit_event=audit_event,
    )
    return envelope({"items": [suggestion], "total": 1}, get_trace_id(request))


@app.post("/api/planning/iteration-suggestions/{suggestion_id}/decide")
def decide_iteration_suggestion(
    suggestion_id: str,
    payload: IterationSuggestionDecisionRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_iteration_planning_role(user)
    _validate_iteration_enums(decision=payload.decision)
    current_store = _insight_write_store(store(request))
    suggestion = current_store.iteration_plan_suggestions.get(suggestion_id)
    if suggestion is None:
        raise api_error(404, "NOT_FOUND", "Iteration suggestion not found")
    if suggestion["status"] not in {"suggested", "accepted", "edited_accepted"}:
        raise api_error(
            409,
            "ITERATION_PLAN_STATE_INVALID",
            "Suggestion cannot be decided from current status",
        )
    if payload.convert_to_requirement and payload.decision == "rejected":
        raise api_error(
            400,
            "ITERATION_PLAN_DECISION_INVALID",
            "Rejected suggestion cannot convert to requirement",
        )
    audit_start_index = len(current_store.audit_events)
    requirement = None
    requirement_audit_event = None
    if payload.convert_to_requirement:
        requirement, requirement_audit_event = _create_iteration_requirement(
            current_store,
            payload=payload,
            suggestion=suggestion,
            user=user,
        )
    now = datetime.now(UTC).isoformat()
    suggestion = {
        **suggestion,
        "status": "converted_to_requirement" if requirement is not None else payload.decision,
        "decision": payload.decision,
        "updated_at": now,
    }
    if payload.edited_title:
        suggestion["title"] = _ensure_non_blank(payload.edited_title, "edited_title")
    if requirement is not None:
        suggestion["converted_requirement_id"] = requirement["id"]
    decision = {
        "comment": payload.comment,
        "convert_to_requirement": payload.convert_to_requirement,
        "created_requirement_id": requirement["id"] if requirement is not None else None,
        "decided_at": now,
        "decided_by": user["id"],
        "decision": payload.decision,
        "edited_scope": payload.edited_scope,
        "edited_title": payload.edited_title,
        "id": current_store.new_id("iteration_decision"),
        "suggestion_id": suggestion_id,
    }
    if not _uses_repository_context(current_store):
        current_store.iteration_plan_suggestions[suggestion_id] = suggestion
        current_store.iteration_plan_decisions[decision["id"]] = decision
    audit_event = _record_audit_event(
        current_store,
        event_type="iteration_suggestion.decided",
        actor_id=user["id"],
        subject_type="iteration_plan_suggestion",
        subject_id=suggestion_id,
        payload={
            "converted_requirement_id": suggestion.get("converted_requirement_id"),
            "decision": payload.decision,
            "status": suggestion["status"],
        },
    )
    _save_iteration_decision_records(
        current_store,
        suggestion=suggestion,
        decision=decision,
        requirement=requirement,
        audit_events=[
            *current_store.audit_events[audit_start_index:],
            *(
                []
                if requirement_audit_event is None
                or requirement_audit_event in current_store.audit_events
                else [requirement_audit_event]
            ),
            *([] if audit_event in current_store.audit_events else [audit_event]),
        ],
    )
    return envelope(
        {
            **suggestion,
            "converted_requirement_id": suggestion.get("converted_requirement_id"),
            "decision": payload.decision,
        },
        get_trace_id(request),
    )


@app.get("/api/lifecycle/context")
def lifecycle_context(
    request: Request,
    subject_type: str | None = None,
    subject_id: str | None = None,
    product_id: str | None = None,
    version_id: str | None = None,
    module_code: str | None = None,
    direction: str = "both",
    include_risks: bool = True,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    runtime_store = store(request)
    repository = _lifecycle_query_repository(runtime_store)
    if repository is not None:
        source_product_id = (
            product_id
            or (str(subject_id) if subject_type == "product" and subject_id else None)
        )
        current_store = _lifecycle_source_store(
            repository.get_lifecycle_context_source_rows(product_id=source_product_id)
        )
    else:
        current_store = _repository_read_model_store(runtime_store)
    if not ((subject_type and subject_id) or product_id):
        raise api_error(
            400,
            "LIFECYCLE_SUBJECT_REQUIRED",
            "subject_type/subject_id or product_id is required",
        )
    if direction not in {"upstream", "downstream", "both"}:
        raise api_error(400, "VALIDATION_ERROR", "direction must be upstream, downstream, or both")

    tasks = _tasks_for_lifecycle_subject(
        current_store,
        subject_type=subject_type,
        subject_id=subject_id,
        product_id=product_id,
        version_id=version_id,
        module_code=module_code,
    )
    if subject_type == "ai_task":
        subject_task = current_store.ai_tasks.get(str(subject_id))
        if subject_task is None:
            raise api_error(404, "NOT_FOUND", "AI task not found")
        _require_task_read_role(user, subject_task)
    tasks = [task for task in tasks if _can_read_task(user, task)]
    upstream = (
        _lifecycle_upstream(current_store, subject_type=subject_type, tasks=tasks)
        if direction in {"upstream", "both"}
        else []
    )
    downstream = (
        _lifecycle_downstream(current_store, tasks=tasks)
        if direction in {"downstream", "both"}
        else []
    )
    risk_signals = (
        _lifecycle_risk_signals(current_store, tasks=tasks)
        if include_risks
        else []
    )
    missing_context = _lifecycle_missing_context(current_store, tasks=tasks)
    subject = _lifecycle_subject(
        current_store,
        subject_type=subject_type,
        subject_id=subject_id,
        product_id=product_id,
    )
    _sync_lifecycle_context_records(
        current_store,
        subject=subject,
        upstream=upstream,
        downstream=downstream,
        risk_signals=risk_signals,
        tasks=tasks,
    )
    if repository is not None:
        repository.save_lifecycle_context(
            {
                "lifecycle_context_edges": current_store.lifecycle_context_edges,
                "lifecycle_risk_signals": current_store.lifecycle_risk_signals,
            }
        )
    else:
        _save_lifecycle_context_records(current_store)

    return envelope(
        {
            "status": "available",
            "subject": subject,
            "upstream": upstream,
            "downstream": downstream,
            "risk_signals": risk_signals,
            "missing_context": missing_context,
            "summary": {
                "upstream_count": len(upstream),
                "downstream_count": len(downstream),
                "risk_count": len(risk_signals),
                "missing_context_count": len(missing_context),
            },
        },
        get_trace_id(request),
    )


@app.get("/api/export/tasks/{task_id}/markdown")
def export_task_markdown(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> PlainTextResponse:
    current_store = store(request)
    read_store = _task_workflow_read_store(current_store)
    task = read_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_task_read_role(user, task)
    if task["status"] != "completed":
        raise api_error(409, "TASK_STATE_INVALID", "Only completed tasks can be exported")

    trace_id = get_trace_id(request)
    return PlainTextResponse(
        _render_markdown(read_store, task),
        media_type="text/markdown",
        headers={"X-Trace-Id": trace_id},
    )
