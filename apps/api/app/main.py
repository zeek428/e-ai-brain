from __future__ import annotations

import hashlib
import json
import os
import re
import socket
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
from app.core.persistence import PersistentMemoryStore, PostgresSnapshotRepository
from app.core.roles import ASSIGNABLE_ROLE_CODES, list_role_definitions
from app.core.security import TokenError, create_access_token, parse_access_token, verify_password
from app.core.store import DEFAULT_BRAIN_APP_ID, MemoryStore
from app.core.trace import envelope, get_trace_id, new_trace_id
from app.core.users import SEEDED_USERS, MemoryUserRepository, PostgresUserRepository

settings = get_settings()

app = FastAPI(title="Enterprise AI Brain API", version="0.1.0")


def build_store() -> MemoryStore:
    if settings.persistence_mode == "postgres":
        repository = PostgresSnapshotRepository(settings.database_url)
        return PersistentMemoryStore.from_repository(repository)
    return MemoryStore()


def build_user_repository() -> MemoryUserRepository | PostgresUserRepository:
    if settings.persistence_mode == "postgres":
        return PostgresUserRepository(settings.database_url)
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
VERSION_STATUSES = {"planning", "active", "archived"}
MODULE_STATUSES = {"active", "inactive"}
GIT_REPO_STATUSES = {"active", "inactive"}
RELATED_SYSTEM_STATUSES = {"active", "inactive"}
MODEL_GATEWAY_PROVIDERS = {"openai_compatible"}
MODEL_GATEWAY_STATUSES = {"active", "inactive"}
MODEL_GATEWAY_TEST_TARGETS = {"chat", "chat_and_embedding", "embedding"}
KNOWLEDGE_INDEX_STATUSES = {"archived", "importing", "indexed", "index_failed", "pending_index"}
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
    default_embedding_model: str
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
    timeout_seconds: int = 60
    max_retries: int = 1
    status: str = "active"
    is_default: bool = False
    config_id: str | None = None
    test_target: str = "chat_and_embedding"


class RequirementRequest(BaseModel):
    title: str
    product_id: str
    version_id: str
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


class RequirementDecisionRequest(BaseModel):
    comment: str | None = None
    rejection_reason: str | None = None


class AiTaskRequest(BaseModel):
    task_type: str
    title: str
    requirement_id: str
    input: dict[str, Any] = Field(default_factory=dict)


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
    current_store = getattr(request.app.state, "store", None)
    if request.url.path.startswith("/api/") and hasattr(current_store, "persist"):
        current_store.persist()
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
        "model_gateway": settings.model_gateway_status,
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


def _require_task_read_role(user: dict[str, Any], task: dict[str, Any]) -> None:
    _require_roles(user, _task_allowed_roles(task))


def _require_review_decision_role(user: dict[str, Any], task: dict[str, Any]) -> None:
    _require_roles(user, _task_allowed_roles(task))


def _raise_gitlab_context_mismatch(message: str) -> None:
    raise api_error(400, "GITLAB_CONTEXT_MISMATCH", message)


def _raise_task_context_mismatch(message: str) -> None:
    raise api_error(400, "TASK_CONTEXT_MISMATCH", message)


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
) -> dict[str, Any]:
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
        "status": "pending_approval",
        "task_ids": [],
        "title": title,
        "version_id": version_id,
    }
    current_store.requirements[requirement_id] = requirement
    current_store.audit(
        event_type="requirement.created",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
        payload={"source": "iteration_plan_suggestion", "suggestion_id": suggestion["id"]},
    )
    return requirement


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


def _public_model_gateway_config(config: dict[str, Any]) -> dict[str, Any]:
    public_config = {
        key: value
        for key, value in config.items()
        if key not in {"api_key"}
    }
    api_key = config.get("api_key")
    public_config["api_key_configured"] = bool(api_key)
    return public_config


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


def _test_model_gateway_embedding(config: dict[str, Any]) -> dict[str, Any]:
    model = config["default_embedding_model"]
    body = {
        "input": ["AI Brain model gateway embedding connectivity test"],
        "model": model,
    }
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
    public_repository["credential_ref_configured"] = bool(repository.get("credential_ref"))
    return public_repository


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


def _model_gateway_messages(task: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "input_json": task.get("input_json", {}),
        "product_context": task.get("product_context", {}),
        "requirement_snapshot": task.get("requirement_snapshot", {}),
        "task_type": task["task_type"],
        "title": task["title"],
    }
    return [
        {
            "role": "system",
            "content": (
                "You are the AI Brain model gateway. Return one JSON object only, "
                "without markdown, comments, or explanatory text."
            ),
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
        if config.get("provider") != "openai_compatible":
            raise ModelGatewayConfigError("Active model gateway provider is not supported")
        if not config.get("api_key"):
            raise ModelGatewayConfigError("Active model gateway config is missing api_key")
        return config
    if settings.model_gateway_status == "configured":
        return {
            "api_key": settings.model_gateway_api_key,
            "base_url": settings.model_gateway_base_url,
            "default_embedding_model": settings.model_gateway_default_embedding_model,
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
    config = _model_gateway_embedding_config(current_store)
    embeddings, _log = _call_openai_compatible_embeddings(
        current_store,
        config=config,
        inputs=inputs,
    )
    return embeddings


def _call_openai_compatible_model_gateway(
    current_store: MemoryStore,
    *,
    config: dict[str, Any],
    task: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = config["provider"]
    model = config["default_chat_model"]
    config_id = config["id"]
    messages = _model_gateway_messages(task)
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
            "product_context": current_store.snapshot(task.get("product_context", {})),
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
    if executor_type == "model_gateway":
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
    items = sorted(current_store.brain_apps.values(), key=lambda item: item["code"])
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/brain-apps/{brain_app_id}")
def get_brain_app(
    brain_app_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    brain_app = current_store.brain_apps.get(brain_app_id)
    if brain_app is None:
        brain_app = next(
            (
                item
                for item in current_store.brain_apps.values()
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
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    items = sorted(
        current_store.products.values(),
        key=lambda item: (item.get("display_order", 0), item["code"]),
    )
    return _list_payload(items, trace_id=get_trace_id(request), active_only=active_only)


@app.post("/api/products")
def create_product(
    request: Request,
    payload: ProductRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
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
    current_store.products[product_id] = product
    current_store.audit(
        event_type="product.created",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    return envelope(product, get_trace_id(request))


@app.patch("/api/products/{product_id}")
def patch_product(
    product_id: str,
    request: Request,
    payload: ProductPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
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
    product.update(updates)
    current_store.audit(
        event_type="product.updated",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    return envelope(product, get_trace_id(request))


@app.delete("/api/products/{product_id}")
def delete_product(
    product_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
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
    for collection in [
        current_store.product_versions,
        current_store.product_modules,
        current_store.product_git_repositories,
    ]:
        for item_id, item in list(collection.items()):
            if item["product_id"] == product_id:
                del collection[item_id]
    del current_store.products[product_id]
    current_store.audit(
        event_type="product.deleted",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    return envelope({"deleted": True, "id": product_id}, get_trace_id(request))


@app.get("/api/products/{product_id}/versions")
def list_product_versions(
    product_id: str,
    request: Request,
    active_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
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
    current_store = store(request)
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
    current_store.product_versions[version_id] = version
    current_store.audit(
        event_type="product_version.created",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    return envelope(version, get_trace_id(request))


@app.patch("/api/product-versions/{version_id}")
def patch_product_version(
    version_id: str,
    request: Request,
    payload: ProductVersionPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
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
    version.update(updates)
    current_store.audit(
        event_type="product_version.updated",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    return envelope(version, get_trace_id(request))


@app.delete("/api/product-versions/{version_id}")
def delete_product_version(
    version_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
    version = current_store.product_versions.get(version_id)
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if (
        any(item["version_id"] == version_id for item in current_store.requirements.values())
        or any(item.get("version_id") == version_id for item in current_store.ai_tasks.values())
        or any(item.get("version_id") == version_id for item in current_store.bugs.values())
    ):
        raise api_error(409, "RESOURCE_IN_USE", "Product version still has related records")
    del current_store.product_versions[version_id]
    current_store.audit(
        event_type="product_version.deleted",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
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
    current_store = store(request)
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
    current_store.product_modules[module_id] = module
    current_store.audit(
        event_type="product_module.created",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
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
    current_store = store(request)
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
    module.update(updates)
    current_store.audit(
        event_type="product_module.updated",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
    )
    return envelope(module, get_trace_id(request))


@app.delete("/api/product-modules/{module_id}")
def delete_product_module(
    module_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
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
    del current_store.product_modules[module_id]
    current_store.audit(
        event_type="product_module.deleted",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
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
    current_store = store(request)
    if product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    name = _ensure_non_blank(payload.name, "name")
    _ensure_enum(payload.status, GIT_REPO_STATUSES, "product Git repository status")
    if payload.git_provider != "gitlab":
        raise api_error(400, "VALIDATION_ERROR", "v1 MVP only supports GitLab bindings")
    if not payload.project_id and not payload.project_path:
        raise api_error(400, "VALIDATION_ERROR", "GitLab project_id or project_path is required")

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
    current_store.product_git_repositories[repository_id] = repository
    current_store.audit(
        event_type="product_git_repository.created",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
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
    current_store = store(request)
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
    if next_provider != "gitlab":
        raise api_error(400, "VALIDATION_ERROR", "v1 MVP only supports GitLab bindings")
    if not next_project_id and not next_project_path:
        raise api_error(400, "VALIDATION_ERROR", "GitLab project_id or project_path is required")
    repository.update(updates)
    current_store.audit(
        event_type="product_git_repository.updated",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repo_id,
    )
    return envelope(_public_git_repository(repository), get_trace_id(request))


@app.delete("/api/product-git-repositories/{repo_id}")
def delete_product_git_repository(
    repo_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
    if repo_id not in current_store.product_git_repositories:
        raise api_error(404, "NOT_FOUND", "Product Git repository not found")
    del current_store.product_git_repositories[repo_id]
    current_store.audit(
        event_type="product_git_repository.deleted",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repo_id,
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
    current_store = store(request)
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
    current_store.related_systems[system_id] = related_system
    current_store.audit(
        event_type="related_system.created",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
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
    current_store = store(request)
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
    related_system.update(updates)
    current_store.audit(
        event_type="related_system.updated",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    return envelope(related_system, get_trace_id(request))


@app.delete("/api/system/related-systems/{system_id}")
def delete_related_system(
    system_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
    if system_id not in current_store.related_systems:
        raise api_error(404, "NOT_FOUND", "Related system not found")
    del current_store.related_systems[system_id]
    current_store.audit(
        event_type="related_system.deleted",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    return envelope({"deleted": True, "id": system_id}, get_trace_id(request))


@app.get("/api/system/model-gateway-configs")
def list_model_gateway_configs(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = store(request)
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
    current_store = store(request)
    name = _ensure_non_blank(payload.name, "name")
    base_url = _ensure_non_blank(payload.base_url, "base_url")
    _ensure_enum(
        payload.test_target,
        MODEL_GATEWAY_TEST_TARGETS,
        "model gateway test target",
    )
    test_target = payload.test_target
    should_test_chat = test_target in {"chat", "chat_and_embedding"}
    should_test_embedding = test_target in {"chat_and_embedding", "embedding"}
    default_chat_model = (
        _ensure_non_blank(payload.default_chat_model, "default_chat_model")
        if should_test_chat
        else (payload.default_chat_model or "").strip()
    )
    default_embedding_model = (
        _ensure_non_blank(payload.default_embedding_model, "default_embedding_model")
        if should_test_embedding
        else (payload.default_embedding_model or "").strip()
    )
    _ensure_enum(payload.provider, MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    _ensure_enum(payload.status, MODEL_GATEWAY_STATUSES, "model gateway status")
    existing_config = None
    if payload.config_id:
        existing_config = current_store.model_gateway_configs.get(payload.config_id)
        if existing_config is None:
            raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    api_key = payload.api_key or (existing_config or {}).get("api_key")
    if not api_key:
        raise api_error(
            400,
            "MODEL_GATEWAY_CONFIG_INVALID",
            "Model gateway test requires an API key",
        )
    test_config = {
        "api_key": api_key,
        "base_url": base_url,
        "default_chat_model": default_chat_model,
        "default_embedding_model": default_embedding_model,
        "id": payload.config_id or "model_gateway_config_test",
        "is_default": False,
        "max_retries": payload.max_retries,
        "name": name,
        "provider": payload.provider,
        "status": payload.status,
        "timeout_seconds": payload.timeout_seconds,
    }
    chat_result = (
        _test_model_gateway_chat(test_config)
        if should_test_chat
        else _model_gateway_test_skipped(model=default_chat_model)
    )
    embedding_result = (
        _test_model_gateway_embedding(test_config)
        if should_test_embedding
        else _model_gateway_test_skipped(model=default_embedding_model)
    )
    result = {
        "chat": chat_result,
        "embedding": embedding_result,
        "ok": bool(chat_result["ok"] and embedding_result["ok"]),
        "test_target": test_target,
    }
    current_store.audit(
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
    return envelope(result, get_trace_id(request))


@app.post("/api/system/model-gateway-configs")
def create_model_gateway_config(
    request: Request,
    payload: ModelGatewayConfigRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = store(request)
    name = _ensure_non_blank(payload.name, "name")
    base_url = _ensure_non_blank(payload.base_url, "base_url")
    default_chat_model = _ensure_non_blank(payload.default_chat_model, "default_chat_model")
    default_embedding_model = _ensure_non_blank(
        payload.default_embedding_model,
        "default_embedding_model",
    )
    _ensure_enum(payload.provider, MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    _ensure_enum(payload.status, MODEL_GATEWAY_STATUSES, "model gateway status")
    config_id = current_store.new_id("model_gateway_config")
    config = {
        "id": config_id,
        "name": name,
        "provider": payload.provider,
        "base_url": base_url,
        "api_key": payload.api_key,
        "default_chat_model": default_chat_model,
        "default_embedding_model": default_embedding_model,
        "timeout_seconds": payload.timeout_seconds,
        "max_retries": payload.max_retries,
        "status": payload.status,
        "is_default": payload.is_default,
    }
    current_store.model_gateway_configs[config_id] = config
    _set_default_model_gateway_config(
        current_store,
        config_id=config_id,
        is_default=payload.is_default,
    )
    current_store.audit(
        event_type="model_gateway_config.created",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
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
    current_store = store(request)
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
        updates["default_embedding_model"] = _ensure_non_blank(
            updates["default_embedding_model"],
            "default_embedding_model",
        )
    if "status" in updates:
        _ensure_enum(updates["status"], MODEL_GATEWAY_STATUSES, "model gateway status")
    if "provider" in updates:
        _ensure_enum(updates["provider"], MODEL_GATEWAY_PROVIDERS, "model gateway provider")
    config.update(updates)
    _set_default_model_gateway_config(
        current_store,
        config_id=config_id,
        is_default=bool(config.get("is_default")),
    )
    current_store.audit(
        event_type="model_gateway_config.updated",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
    )
    return envelope(_public_model_gateway_config(config), get_trace_id(request))


@app.delete("/api/system/model-gateway-configs/{config_id}")
def delete_model_gateway_config(
    config_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = store(request)
    if config_id not in current_store.model_gateway_configs:
        raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    del current_store.model_gateway_configs[config_id]
    current_store.audit(
        event_type="model_gateway_config.deleted",
        actor_id=user["id"],
        subject_type="model_gateway_config",
        subject_id=config_id,
    )
    return envelope({"deleted": True, "id": config_id}, get_trace_id(request))


@app.get("/api/model-gateway/logs")
def list_model_gateway_logs(
    request: Request,
    ai_task_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = store(request)
    items = list(current_store.model_gateway_logs)
    if ai_task_id:
        items = [item for item in items if item["ai_task_id"] == ai_task_id]
    if status:
        items = [item for item in items if item["status"] == status]
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/requirements")
def create_requirement(
    request: Request,
    payload: RequirementRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = store(request)
    title = _ensure_non_blank(payload.title, "title")
    content = _ensure_non_blank(payload.content, "content")
    product = current_store.products.get(payload.product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    version = current_store.product_versions.get(payload.version_id)
    if version is None or version["product_id"] != payload.product_id:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if version["status"] == "archived":
        raise api_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")
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
        "status": "pending_approval",
        "created_by": user["id"],
        "task_ids": [],
        "created_at": datetime.now(UTC).isoformat(),
    }
    current_store.requirements[requirement_id] = requirement
    current_store.audit(
        event_type="requirement.created",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    return envelope(requirement, get_trace_id(request))


@app.get("/api/requirements")
def list_requirements(
    request: Request,
    product_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    items = list(current_store.requirements.values())
    if product_id:
        items = [item for item in items if item["product_id"] == product_id]
    if status:
        items = [item for item in items if item["status"] == status]
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/requirements/{requirement_id}")
def get_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    requirement = current_store.requirements.get(requirement_id)
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
    current_store = store(request)
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement["status"] not in {"pending_approval", "rejected"}:
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
    version = current_store.product_versions.get(next_version_id)
    if version is None or version["product_id"] != next_product_id:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if version["status"] == "archived":
        raise api_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")
    next_module_code = updates.get("module_code", requirement.get("module_code"))
    if next_module_code is not None and not any(
        module["product_id"] == next_product_id and module["code"] == next_module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")
    requirement.update(updates)
    requirement["updated_at"] = datetime.now(UTC).isoformat()
    current_store.audit(
        event_type="requirement.updated",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    return envelope(requirement, get_trace_id(request))


@app.delete("/api/requirements/{requirement_id}")
def delete_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = store(request)
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement.get("task_ids"):
        raise api_error(409, "RESOURCE_IN_USE", "Requirement already has tasks")
    del current_store.requirements[requirement_id]
    current_store.audit(
        event_type="requirement.deleted",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    return envelope({"deleted": True, "id": requirement_id}, get_trace_id(request))


@app.post("/api/requirements/{requirement_id}/approve")
def approve_requirement(
    requirement_id: str,
    request: Request,
    payload: RequirementDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = store(request)
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement["status"] != "pending_approval":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not pending approval")
    requirement["status"] = "approved"
    requirement["approval_comment"] = payload.comment
    current_store.audit(
        event_type="requirement.approved",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    return envelope(requirement, get_trace_id(request))


@app.post("/api/requirements/{requirement_id}/reject")
def reject_requirement(
    requirement_id: str,
    request: Request,
    payload: RequirementDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner"})
    current_store = store(request)
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement["status"] != "pending_approval":
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement is not pending approval")
    rejection_reason = payload.rejection_reason or payload.comment
    if not rejection_reason:
        raise api_error(400, "VALIDATION_ERROR", "rejection_reason is required")
    requirement["status"] = "rejected"
    requirement["rejection_reason"] = rejection_reason
    current_store.audit(
        event_type="requirement.rejected",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    return envelope(requirement, get_trace_id(request))


@app.post("/api/requirements/{requirement_id}/close")
def close_requirement(
    requirement_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"product_owner", "rd_owner"})
    current_store = store(request)
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement["status"] not in {"approved", "rejected", "task_created"}:
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement cannot be closed")
    active_tasks = [
        current_store.ai_tasks[task_id]
        for task_id in requirement.get("task_ids", [])
        if current_store.ai_tasks[task_id]["status"]
        not in {"completed", "failed", "cancelled"}
    ]
    if active_tasks:
        raise api_error(409, "REQUIREMENT_HAS_ACTIVE_TASKS", "Requirement has active tasks")
    requirement["status"] = "closed"
    current_store.audit(
        event_type="requirement.closed",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    return envelope(requirement, get_trace_id(request))


def _product_context(current_store: MemoryStore, requirement: dict[str, Any]) -> dict[str, Any]:
    product = current_store.products[requirement["product_id"]]
    version = current_store.product_versions[requirement["version_id"]]
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
        repository
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
        "version": current_store.snapshot(version),
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
    current_store = store(request)
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement["status"] != "approved":
        raise api_error(
            409,
            "REQUIREMENT_STATE_INVALID",
            "Only approved requirements can generate tasks",
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
    current_store.ai_tasks[task_id] = task
    requirement["status"] = "task_created"
    requirement.setdefault("task_ids", []).append(task_id)
    current_store.audit(
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


def _gitlab_access_token(repository: dict[str, Any]) -> str | None:
    credential_ref = str(repository.get("credential_ref") or "").strip()
    for env_name in _credential_ref_env_candidates(credential_ref):
        token = os.getenv(env_name, "").strip()
        if token:
            return token
    configured_token = os.getenv("GITLAB_READONLY_TOKEN", "").strip()
    return configured_token or None


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
    current_store = store(request)
    repository = current_store.product_git_repositories.get(repository_id)
    if repository is None:
        raise api_error(404, "NOT_FOUND", "GitLab repository binding not found")
    if repository["git_provider"] != "gitlab":
        raise api_error(400, "VALIDATION_ERROR", "Repository is not a GitLab binding")
    preview = _gitlab_preview(repository, mr_iid)
    current_store.audit(
        event_type="gitlab_mr.previewed",
        actor_id=user["id"],
        subject_type="product_git_repository",
        subject_id=repository_id,
        payload={"mr_iid": mr_iid},
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
    current_store = store(request)
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

    preview = _gitlab_preview(repository, mr_iid)
    diff_payload = _diff_payload(preview)
    diff_size_bytes = len(diff_payload.encode())
    diff_limit_bytes = 204_800
    changed_file_count = len(preview["changed_files_summary"])
    changed_file_limit = 50
    file_diff_line_limit = 2_000
    if changed_file_count > changed_file_limit:
        current_store.audit(
            event_type="gitlab_mr.snapshot_failed",
            actor_id=user["id"],
            subject_type="product_git_repository",
            subject_id=repository_id,
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
        current_store.audit(
            event_type="gitlab_mr.snapshot_failed",
            actor_id=user["id"],
            subject_type="product_git_repository",
            subject_id=repository_id,
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
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")
    if diff_size_bytes > diff_limit_bytes:
        current_store.audit(
            event_type="gitlab_mr.snapshot_failed",
            actor_id=user["id"],
            subject_type="product_git_repository",
            subject_id=repository_id,
            payload={
                "diff_limit_bytes": diff_limit_bytes,
                "diff_size_bytes": diff_size_bytes,
                "mr_iid": mr_iid,
                "reason": "diff_too_large",
                "requirement_id": payload.requirement_id,
                "technical_solution_task_id": payload.technical_solution_task_id,
            },
        )
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")

    snapshot_hash = hashlib.sha256(diff_payload.encode()).hexdigest()
    existing_snapshot = next(
        (
            snapshot
            for snapshot in current_store.gitlab_mr_snapshots.values()
            if snapshot.get("repository_id") == repository_id
            and snapshot.get("snapshot_hash") == snapshot_hash
        ),
        None,
    )
    if existing_snapshot is not None:
        current_store.audit(
            event_type="gitlab_mr.snapshot_reused",
            actor_id=user["id"],
            subject_type="gitlab_mr_snapshot",
            subject_id=existing_snapshot["id"],
            payload={
                "repository_id": repository_id,
                "mr_iid": mr_iid,
                "requirement_id": payload.requirement_id,
                "technical_solution_task_id": payload.technical_solution_task_id,
            },
        )
        return envelope(existing_snapshot, get_trace_id(request))

    snapshot_id = current_store.new_id("snapshot")
    snapshot = {
        "id": snapshot_id,
        "repository_id": repository_id,
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
        "diff_storage_ref": f"memory://gitlab-mr-diff/{snapshot_id}",
        "diff_size_bytes": diff_size_bytes,
        "diff_limit_bytes": diff_limit_bytes,
        "snapshot_hash": snapshot_hash,
        "requirement_id": payload.requirement_id,
        "technical_solution_task_id": payload.technical_solution_task_id,
        "created_by": user["id"],
        "created_at": datetime.now(UTC).isoformat(),
        "writeback_allowed": False,
    }
    current_store.gitlab_mr_snapshots[snapshot_id] = snapshot
    current_store.audit(
        event_type="gitlab_mr.snapshotted",
        actor_id=user["id"],
        subject_type="gitlab_mr_snapshot",
        subject_id=snapshot_id,
        payload={"repository_id": repository_id, "mr_iid": mr_iid},
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
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
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
    if created_from or created_to:
        from_at = _parse_iso_datetime(created_from, "created_from") if created_from else None
        to_at = _parse_iso_datetime(created_to, "created_to") if created_to else None
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
    items.sort(key=lambda item: item["id"])
    return envelope(
        {
            "items": [_task_summary_projection(item, current_store) for item in items],
            "total": len(items),
        },
        get_trace_id(request),
    )


@app.post("/api/ai-tasks")
def create_ai_task(
    request: Request,
    payload: AiTaskRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
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

    if requirement["status"] not in {"approved", "task_created"}:
        raise api_error(
            409,
            "REQUIREMENT_STATE_INVALID",
            "Requirement must be approved or task_created before creating AI tasks",
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
    current_store.ai_tasks[task_id] = task
    requirement["status"] = "task_created"
    task_ids = requirement.setdefault("task_ids", [])
    if task_id not in task_ids:
        task_ids.append(task_id)
    current_store.audit(
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
    task["output_json"] = {**task["output_json"], **edited_content}
    review["status"] = "edited_approved"
    review["edited_content"] = edited_content
    review["decided_by"] = actor_id
    task["status"] = "completed"
    _confirm_code_review_report(current_store, task)
    _create_automated_testing_bugs(current_store, actor_id=actor_id, task=task)
    _create_post_release_bugs(current_store, actor_id=actor_id, task=task)
    _create_knowledge_deposit(current_store, task)
    _transition_latest_graph_run(
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
    return {"review_status": review["status"], "task_status": task["status"]}


def _create_knowledge_deposit(current_store: MemoryStore, task: dict[str, Any]) -> None:
    deposit_id = current_store.new_id("deposit")
    current_store.knowledge_deposits[deposit_id] = {
        "id": deposit_id,
        "ai_task_id": task["id"],
        "title": f"{task['title']} 知识沉淀",
        "content": task["output_json"]["summary"],
        "status": "pending",
        "knowledge_document_id": None,
    }


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
) -> dict[str, Any]:
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
    current_store.graph_runs[graph_run_id] = graph_run
    task.setdefault("graph_run_ids", []).append(graph_run_id)
    _write_graph_checkpoint(
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
    return graph_run


def _transition_latest_graph_run(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
    status: str,
    current_step: str,
    state_snapshot: dict[str, Any],
) -> None:
    graph_run = _latest_graph_run(current_store, task)
    if graph_run is None:
        task["current_step"] = current_step
        return
    graph_run["status"] = status
    if status in {"completed", "failed", "cancelled"}:
        graph_run["completed_at"] = datetime.now(UTC).isoformat()
    _write_graph_checkpoint(
        current_store,
        graph_run=graph_run,
        task=task,
        current_step=current_step,
        state_snapshot=state_snapshot,
    )


def _task_detail_projection(current_store: MemoryStore, task: dict[str, Any]) -> dict[str, Any]:
    detail = current_store.snapshot(task)
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
        "product_context": task.get("product_context"),
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
    current_store = store(request)
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_review_decision_role(user, task)
    if task["status"] != "draft":
        raise api_error(409, "TASK_STATE_INVALID", "Task cannot be started from current status")

    if task["task_type"] == "code_review":
        try:
            executor_result = _call_configured_code_review_executor(current_store, task=task)
            task["output_json"] = executor_result.output
            model_log = executor_result.model_log
            executor_meta = executor_result.executor
        except CodeReviewExecutorError as exc:
            task["status"] = "failed"
            task["current_step"] = "code_review_executor_failed"
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
            task["status"] = "failed"
            task["current_step"] = exc.current_step
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
            raise api_error(400, "MODEL_GATEWAY_CONFIG_INVALID", str(exc)) from exc
        except ModelGatewayCallError as exc:
            task["status"] = "failed"
            task["current_step"] = "model_gateway_failed"
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
            raise api_error(502, "MODEL_GATEWAY_FAILED", "Model gateway request failed") from exc

    task["status"] = "waiting_review"
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
    if task["task_type"] == "code_review":
        report = _create_code_review_report(
            current_store,
            task=task,
            output=task["output_json"],
        )
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
    }
    current_store.human_reviews[review_id] = review
    task["review_ids"].append(review_id)
    if task["task_type"] == "code_review":
        report_id = task.get("code_review_report_id")
        current_store.code_review_reports[report_id]["review_id"] = review_id
    graph_run = _start_graph_run(current_store, task=task, review_id=review_id)
    current_store.audit(
        event_type="human_review.created",
        actor_id="system",
        ai_task_id=task_id,
        subject_type="human_review",
        subject_id=review_id,
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
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_task_read_role(user, task)
    return envelope(_task_detail_projection(current_store, task), get_trace_id(request))


@app.post("/api/ai-tasks/{task_id}/cancel")
def cancel_ai_task(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if task["status"] in {"completed", "failed", "cancelled"}:
        raise api_error(409, "TASK_STATE_INVALID", "Task cannot be cancelled from current status")
    _require_review_decision_role(user, task)
    task["status"] = "cancelled"
    for review_id in task.get("review_ids", []):
        review = current_store.human_reviews.get(review_id)
        if review and review["status"] == "pending":
            review["status"] = "cancelled"
            review["version"] += 1
            review["decided_by"] = user["id"]
    _transition_latest_graph_run(
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
    return envelope({"id": task_id, "status": task["status"]}, get_trace_id(request))


@app.get("/api/graph-runs")
def list_graph_runs(
    request: Request,
    ai_task_id: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    items = list(current_store.graph_runs.values())
    if ai_task_id:
        task = current_store.ai_tasks.get(ai_task_id)
        if task is None:
            raise api_error(404, "NOT_FOUND", "AI task not found")
        _require_task_read_role(user, task)
        items = [item for item in items if item["ai_task_id"] == ai_task_id]
    else:
        items = [
            item
            for item in items
            if (task := current_store.ai_tasks.get(item["ai_task_id"])) is not None
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
    items = [
        review
        for review in current_store.human_reviews.values()
        if review["status"] == "pending"
        and (task := current_store.ai_tasks.get(review["ai_task_id"])) is not None
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
    review = current_store.human_reviews.get(review_id)
    if review is None:
        raise api_error(404, "NOT_FOUND", "Review not found")
    task = current_store.ai_tasks.get(review["ai_task_id"])
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_task_read_role(user, task)
    return envelope(
        {
            **current_store.snapshot(review),
            "task": current_store.snapshot(task),
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
    current_store = store(request)
    review, task = _ensure_review_decidable(
        current_store,
        review_id=review_id,
        version=payload.version,
    )
    _require_review_decision_role(user, task)
    review["status"] = "approved"
    review["decided_by"] = user["id"]
    task["status"] = "completed"
    _confirm_code_review_report(current_store, task)
    _create_automated_testing_bugs(current_store, actor_id=user["id"], task=task)
    _create_post_release_bugs(current_store, actor_id=user["id"], task=task)
    _create_knowledge_deposit(current_store, task)
    _transition_latest_graph_run(
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
    current_store = store(request)
    review, task = _ensure_review_decidable(
        current_store,
        review_id=review_id,
        version=payload.version,
    )
    _require_review_decision_role(user, task)
    edited_content = payload.edited_content or {}
    result = _complete_review_with_edited_approval(
        current_store,
        actor_id=user["id"],
        edited_content=edited_content,
        review=review,
        review_id=review_id,
        task=task,
    )
    return envelope(result, get_trace_id(request))


@app.post("/api/reviews/{review_id}/reject")
def reject_review(
    review_id: str,
    request: Request,
    payload: ReviewDecisionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    review, task = _ensure_review_decidable(
        current_store,
        review_id=review_id,
        version=payload.version,
    )
    _require_review_decision_role(user, task)
    review["status"] = "rejected"
    review["decision_reason"] = payload.decision_reason
    review["decided_by"] = user["id"]
    task["status"] = "failed"
    _transition_latest_graph_run(
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
    current_store = store(request)
    review, task = _ensure_review_decidable(
        current_store,
        review_id=review_id,
        version=payload.version,
    )
    _require_review_decision_role(user, task)
    review["status"] = "requested_more_info"
    review["questions"] = payload.questions
    review["decided_by"] = user["id"]
    task["status"] = "waiting_more_info"
    _transition_latest_graph_run(
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
    current_store = store(request)
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    if task["status"] != "waiting_more_info":
        raise api_error(409, "TASK_STATE_INVALID", "Task is not waiting for more info")
    _require_review_decision_role(user, task)
    task["input_json"].setdefault("more_info_answers", []).extend(payload.answers)
    task["status"] = "draft"
    task["current_step"] = "draft"
    current_store.audit(
        event_type="ai_task.more_info_submitted",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
    )
    return envelope({"id": task_id, "status": task["status"]}, get_trace_id(request))


@app.get("/api/knowledge/documents")
def list_knowledge_documents(
    request: Request,
    keyword: str | None = None,
    doc_type: str | None = None,
    index_status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    if index_status:
        _ensure_enum(index_status, KNOWLEDGE_INDEX_STATUSES, "knowledge index status")
    current_store = store(request)
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
    items.sort(key=lambda item: item["id"])
    return envelope(
        {
            "items": [_knowledge_document_response(current_store, item) for item in items],
            "total": len(items),
        },
        get_trace_id(request),
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
) -> dict[str, Any]:
    response = current_store.snapshot(document)
    response["chunk_count"] = len(_knowledge_document_chunks(current_store, document["id"]))
    response["index_error"] = document.get("index_error")
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


def _replace_knowledge_chunks(current_store: MemoryStore, document: dict[str, Any]) -> None:
    document_id = document["id"]
    _clear_knowledge_chunks(current_store, document_id)
    chunks = _split_knowledge_content(document["content"])
    if not chunks:
        _mark_knowledge_index_failed(current_store, document, "NO_INDEXABLE_CONTENT")
        return
    try:
        embeddings = _call_model_gateway_embeddings(current_store, chunks)
    except ModelGatewayConfigError as exc:
        _mark_knowledge_index_failed(current_store, document, str(exc))
        return
    except ModelGatewayCallError as exc:
        _mark_knowledge_index_failed(
            current_store,
            document,
            exc.log.get("error") or "Model gateway embedding request failed",
        )
        return
    permission_roles = list(document.get("permission_roles", ["admin"]))
    for chunk_index, content in enumerate(chunks, start=1):
        chunk_id = f"{document_id}_chunk_{chunk_index:03d}"
        current_store.knowledge_chunks[chunk_id] = {
            "chunk_index": chunk_index,
            "content": content,
            "document_id": document_id,
            "embedding": embeddings[chunk_index - 1],
            "id": chunk_id,
            "metadata": {
                "doc_type": document.get("doc_type", "manual"),
                "product_id": document.get("product_id"),
                "tags": list(document.get("tags", [])),
                "title": document["title"],
            },
            "permission_roles": permission_roles,
            "permission_scope": {"roles": permission_roles},
        }
    document["chunk_count"] = len(chunks)
    document["index_status"] = "indexed"
    document.pop("index_error", None)


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
) -> list[float] | None:
    try:
        return _call_model_gateway_embeddings(current_store, [query])[0]
    except (ModelGatewayConfigError, ModelGatewayCallError):
        return None


@app.post("/api/knowledge/documents")
def create_knowledge_document(
    request: Request,
    payload: KnowledgeDocumentRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = store(request)
    title = _ensure_non_blank(payload.title, "title")
    content = _ensure_non_blank(payload.content, "content")
    if payload.product_id is not None and payload.product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")
    _ensure_roles(payload.permission_roles)
    document_id = current_store.new_id("knowledge")
    document = {
        "id": document_id,
        "title": title,
        "content": content,
        "doc_type": payload.doc_type,
        "product_id": payload.product_id,
        "permission_roles": payload.permission_roles,
        "tags": payload.tags,
        "index_status": "indexed",
        "index_error": None,
        "created_by": user["id"],
    }
    current_store.knowledge_documents[document_id] = document
    _replace_knowledge_chunks(current_store, document)
    current_store.audit(
        event_type="knowledge_document.created",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    return envelope(_knowledge_document_response(current_store, document), get_trace_id(request))


@app.patch("/api/knowledge/documents/{document_id}")
def patch_knowledge_document(
    document_id: str,
    request: Request,
    payload: KnowledgeDocumentPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = store(request)
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
    document.update(updates)
    document["updated_at"] = datetime.now(UTC).isoformat()
    if updates.get("index_status") == "index_failed":
        _mark_knowledge_index_failed(
            current_store,
            document,
            document.get("index_error") or "Knowledge indexing failed",
        )
    elif updates.get("index_status") in {"archived", "importing", "pending_index"}:
        _clear_knowledge_chunks(current_store, document_id)
        document["chunk_count"] = 0
        document["index_error"] = None
    elif updates.get("index_status") == "indexed" or {
        "content",
        "title",
        "permission_roles",
        "product_id",
        "doc_type",
        "tags",
    }.intersection(updates):
        _replace_knowledge_chunks(current_store, document)
    current_store.audit(
        event_type="knowledge_document.updated",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    return envelope(_knowledge_document_response(current_store, document), get_trace_id(request))


@app.post("/api/knowledge/documents/{document_id}/retry-index")
def retry_knowledge_document_index(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = store(request)
    document = current_store.knowledge_documents.get(document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if document.get("index_status") != "index_failed":
        raise api_error(409, "KNOWLEDGE_INDEX_STATE_INVALID", "Knowledge document is not failed")
    _replace_knowledge_chunks(current_store, document)
    document["updated_at"] = datetime.now(UTC).isoformat()
    current_store.audit(
        event_type="knowledge_document.index_retried",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    return envelope(_knowledge_document_response(current_store, document), get_trace_id(request))


@app.delete("/api/knowledge/documents/{document_id}")
def delete_knowledge_document(
    document_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = store(request)
    if document_id not in current_store.knowledge_documents:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    del current_store.knowledge_documents[document_id]
    current_store.knowledge_chunks = {
        chunk_id: chunk
        for chunk_id, chunk in current_store.knowledge_chunks.items()
        if chunk.get("document_id") != document_id
    }
    for deposit in current_store.knowledge_deposits.values():
        if deposit.get("knowledge_document_id") == document_id:
            deposit["knowledge_document_id"] = None
    current_store.audit(
        event_type="knowledge_document.deleted",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
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
    query_embedding = _knowledge_query_embedding(current_store, query)
    items = []
    for document in current_store.knowledge_documents.values():
        if document.get("index_status") != "indexed":
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
            haystack = f"{document['title']} {chunk['content']}".lower()
            embedding = chunk.get("embedding")
            score = None
            if query_embedding is not None and isinstance(embedding, list):
                score = _cosine_similarity(query_embedding, [float(value) for value in embedding])
                if score <= 0 and query not in haystack:
                    continue
            elif query not in haystack:
                continue
            items.append(
                {
                    "chunk_id": chunk["id"],
                    "chunk_index": chunk["chunk_index"],
                    "document_id": document["id"],
                    "title": document["title"],
                    "content": chunk["content"],
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
    current_store = store(request)
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
    current_store = store(request)
    deposit = current_store.knowledge_deposits.get(deposit_id)
    if deposit is None:
        raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
    if deposit["status"] != "pending":
        raise api_error(409, "KNOWLEDGE_DEPOSIT_STATE_INVALID", "Deposit is not pending")

    document_id = current_store.new_id("knowledge")
    document = {
        "id": document_id,
        "title": payload.title or deposit["title"],
        "content": deposit["content"],
        "doc_type": "task_deposit",
        "permission_roles": payload.permission_roles,
        "tags": ["task_deposit"],
        "index_status": "indexed",
        "created_by": user["id"],
    }
    current_store.knowledge_documents[document_id] = document
    _replace_knowledge_chunks(current_store, document)
    deposit["status"] = "approved"
    deposit["knowledge_document_id"] = document_id
    current_store.audit(
        event_type="knowledge_deposit.approved",
        actor_id=user["id"],
        subject_type="knowledge_deposit",
        subject_id=deposit_id,
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
    current_store = store(request)
    deposit = current_store.knowledge_deposits.get(deposit_id)
    if deposit is None:
        raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
    if deposit["status"] != "pending":
        raise api_error(409, "KNOWLEDGE_DEPOSIT_STATE_INVALID", "Deposit is not pending")

    deposit["status"] = "rejected"
    deposit["rejection_reason"] = payload.reason
    current_store.audit(
        event_type="knowledge_deposit.rejected",
        actor_id=user["id"],
        subject_type="knowledge_deposit",
        subject_id=deposit_id,
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
    _completed_task_for_writeback(current_store, task_id)

    idempotency_key = _writeback_idempotency_key(task_id)
    result = current_store.mock_writebacks.get(idempotency_key)
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
    current_store = store(request)
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
        current_store.mock_writebacks[idempotency_key] = result
        current_store.audit(
            event_type="mock_issue.written",
            actor_id=user["id"],
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload={"idempotency_key": idempotency_key},
        )
    return envelope(result, get_trace_id(request))


@app.get("/api/ai-tasks/{task_id}/code-review-report")
def get_code_review_report(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"reviewer", "rd_owner"})
    current_store = store(request)
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_task_read_role(user, task)
    report_id = task.get("code_review_report_id")
    if not report_id:
        raise api_error(404, "NOT_FOUND", "Code review report not found")
    return envelope(current_store.code_review_reports[report_id], get_trace_id(request))


@app.get("/api/audit/events")
def audit_events(
    request: Request,
    ai_task_id: str | None = None,
    actor_id: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    event_type: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = store(request)
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
        from_at = _parse_iso_datetime(created_from, "created_from") if created_from else None
        to_at = _parse_iso_datetime(created_to, "created_to") if created_to else None
        filtered_items = []
        for item in items:
            event_at = _parse_iso_datetime(str(item.get("created_at") or ""), "created_at")
            if from_at and event_at < from_at:
                continue
            if to_at and event_at > to_at:
                continue
            filtered_items.append(item)
        items = filtered_items
    items.sort(key=lambda item: item["sequence"], reverse=True)
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


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


def _status_counts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return [
        {"status": status, "count": count}
        for status, count in sorted(counts.items(), key=lambda item: item[0])
    ]


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
    current_store = store(request)
    if product_id and product_id not in current_store.products:
        raise api_error(404, "NOT_FOUND", "Product not found")

    cutoff = _dashboard_time_cutoff(time_range)
    products = [
        product
        for product in current_store.products.values()
        if product.get("status") == "active" and (product_id is None or product["id"] == product_id)
    ]
    requirements = [
        requirement
        for requirement in current_store.requirements.values()
        if product_id is None or requirement["product_id"] == product_id
    ]
    tasks = [
        task
        for task in current_store.ai_tasks.values()
        if (product_id is None or task["product_id"] == product_id) and _can_read_task(user, task)
    ]
    task_ids = {task["id"] for task in tasks}
    pending_reviews = [
        review
        for review in current_store.human_reviews.values()
        if review["status"] == "pending" and review["ai_task_id"] in task_ids
    ]
    knowledge_documents = [
        document
        for document in current_store.knowledge_documents.values()
        if _user_can_read_roles(user, document["permission_roles"])
        and (
            product_id is None
            or _knowledge_document_product_id(current_store, document) == product_id
        )
    ]
    knowledge_deposits = [
        deposit
        for deposit in current_store.knowledge_deposits.values()
        if deposit["ai_task_id"] in task_ids
    ]
    audit_events = [
        event
        for event in current_store.audit_events
        if _audit_event_matches_product(current_store, event, product_id)
    ]
    bugs = [
        bug
        for bug in current_store.bugs.values()
        if (product_id is None or bug.get("product_id") == product_id)
        and _dashboard_matches_time_range(bug, cutoff, ("updated_at", "created_at"))
    ]
    gitlab_metrics = [
        metric
        for metric in current_store.gitlab_daily_code_metrics.values()
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("metric_date", "updated_at", "created_at"),
        )
    ]
    jenkins_releases = [
        release
        for release in current_store.jenkins_release_records.values()
        if (product_id is None or release.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            release,
            cutoff,
            ("deployed_at", "started_at", "updated_at", "created_at"),
        )
    ]
    online_log_metrics = [
        metric
        for metric in current_store.online_log_metrics.values()
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("window_end", "window_start", "updated_at", "created_at"),
        )
    ]
    usage_metrics = [
        metric
        for metric in current_store.user_usage_metrics.values()
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("window_end", "window_start", "updated_at", "created_at"),
        )
    ]
    feedback_items = [
        feedback
        for feedback in current_store.user_feedback.values()
        if (product_id is None or feedback.get("product_id") == product_id)
        and _dashboard_matches_time_range(feedback, cutoff, ("updated_at", "created_at"))
    ]
    iteration_suggestions = [
        suggestion
        for suggestion in current_store.iteration_plan_suggestions.values()
        if (product_id is None or suggestion.get("product_id") == product_id)
        and _dashboard_matches_time_range(suggestion, cutoff, ("updated_at", "created_at"))
    ]
    open_bugs = [bug for bug in bugs if bug.get("status") != "closed"]
    high_severity_bugs = [
        bug
        for bug in open_bugs
        if bug.get("severity") in {"blocker", "critical", "major"}
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
    data = {
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
        "latest_high_severity_bugs": current_store.snapshot(latest_high_severity_bugs),
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
        "latest_tasks": current_store.snapshot(latest_tasks),
        "pending_reviews": current_store.snapshot(pending_reviews),
        "recent_knowledge_documents": current_store.snapshot(recent_knowledge_documents),
        "recent_audit_events": current_store.snapshot(recent_audit_events),
        "requirement_titles": [requirement["title"] for requirement in requirements[:10]],
        "time_range": time_range or "all",
    }
    _sync_dashboard_metric_snapshot(
        current_store,
        product_id=product_id,
        time_range=time_range,
        cutoff=cutoff,
        data=data,
    )
    return envelope(data, get_trace_id(request))


@app.get("/api/bugs")
def list_bugs(
    request: Request,
    product_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _validate_bug_enums(source=source, severity=severity, status=status)
    current_store = store(request)
    items = list(current_store.bugs.values())
    if product_id:
        items = [item for item in items if item["product_id"] == product_id]
    if status:
        items = [item for item in items if item["status"] == status]
    if severity:
        items = [item for item in items if item["severity"] == severity]
    if source:
        items = [item for item in items if item["source"] == source]
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/bugs")
def create_bug(
    request: Request,
    payload: BugRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_bug_write_role(user)
    _validate_bug_enums(source=payload.source, severity=payload.severity)
    current_store = store(request)
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
    current_store.bugs[bug_id] = bug
    current_store.audit(
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
    return envelope(bug, get_trace_id(request))


@app.patch("/api/bugs/{bug_id}")
def patch_bug(
    bug_id: str,
    request: Request,
    payload: BugPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_bug_write_role(user)
    current_store = store(request)
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
    bug.update(updates)
    bug["updated_at"] = datetime.now(UTC).isoformat()
    current_store.audit(
        event_type="bug.updated",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
        payload={
            "status": bug["status"],
            "updated_fields": sorted(updates.keys()),
        },
    )
    return envelope(bug, get_trace_id(request))


@app.delete("/api/bugs/{bug_id}")
def delete_bug(
    bug_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_bug_write_role(user)
    current_store = store(request)
    if bug_id not in current_store.bugs:
        raise api_error(404, "NOT_FOUND", "Bug not found")
    del current_store.bugs[bug_id]
    current_store.audit(
        event_type="bug.deleted",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
    )
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
    current_store = store(request)
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
    current_store.collector_runs[run_id] = run
    current_store.audit(
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
    return envelope(run, get_trace_id(request))


@app.patch("/api/collectors/runs/{run_id}")
def patch_collector_run(
    run_id: str,
    payload: CollectorRunPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_collector_run_write_role(user)
    current_store = store(request)
    run = current_store.collector_runs.get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Collector run not found")
    updates = _collector_run_patch_updates(run, payload)
    if updates:
        run.update(updates)
        run["updated_at"] = datetime.now(UTC).isoformat()
    current_store.audit(
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
    current_store = store(request)
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
    current_store.pending_attribution_items[item_id] = item
    current_store.audit(
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
    return envelope(item, get_trace_id(request))


@app.post("/api/attribution/pending-items/{item_id}/resolve")
def resolve_pending_attribution_item(
    item_id: str,
    payload: PendingAttributionResolveRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_pending_attribution_write_role(user)
    current_store = store(request)
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
    item.update(
        {
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
    )
    current_store.audit(
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
    return envelope(item, get_trace_id(request))


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
    current_store = store(request)
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
    current_store.gitlab_daily_code_metrics[metric_id] = metric
    current_store.audit(
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
    current_store = store(request)
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
    current_store.jenkins_release_records[release_id] = release
    current_store.audit(
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
    current_store = store(request)
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
    current_store.online_log_metrics[metric_id] = metric
    current_store.audit(
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
    return envelope(metric, get_trace_id(request))


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
    current_store = store(request)
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
    current_store.user_usage_metrics[metric_id] = metric
    current_store.audit(
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
    current_store = store(request)
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
    current_store.user_feedback[feedback["id"]] = feedback
    current_store.audit(
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
    return envelope(feedback, get_trace_id(request))


@app.patch("/api/insights/user-feedback/{feedback_id}")
def patch_user_feedback(
    feedback_id: str,
    payload: UserFeedbackPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_user_feedback_triage_role(user)
    current_store = store(request)
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
    feedback.update(updates)
    feedback["updated_at"] = datetime.now(UTC).isoformat()
    current_store.audit(
        event_type="user_feedback.updated",
        actor_id=user["id"],
        subject_type="user_feedback",
        subject_id=feedback_id,
        payload={
            "status": feedback["status"],
            "updated_fields": sorted(updates.keys()),
        },
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
    current_store = store(request)
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
    current_store.iteration_plan_suggestions[suggestion["id"]] = suggestion
    current_store.audit(
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
    current_store = store(request)
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
    requirement = None
    if payload.convert_to_requirement:
        requirement = _create_iteration_requirement(
            current_store,
            payload=payload,
            suggestion=suggestion,
            user=user,
        )
    now = datetime.now(UTC).isoformat()
    suggestion["status"] = (
        "converted_to_requirement" if requirement is not None else payload.decision
    )
    suggestion["decision"] = payload.decision
    if payload.edited_title:
        suggestion["title"] = _ensure_non_blank(payload.edited_title, "edited_title")
    if requirement is not None:
        suggestion["converted_requirement_id"] = requirement["id"]
    suggestion["updated_at"] = now
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
    current_store.iteration_plan_decisions[decision["id"]] = decision
    current_store.audit(
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
    current_store = store(request)
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
    task = current_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    _require_task_read_role(user, task)
    if task["status"] != "completed":
        raise api_error(409, "TASK_STATE_INVALID", "Only completed tasks can be exported")

    trace_id = get_trace_id(request)
    return PlainTextResponse(
        _render_markdown(current_store, task),
        media_type="text/markdown",
        headers={"X-Trace-Id": trace_id},
    )
