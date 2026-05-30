from __future__ import annotations

import hashlib
import json
import socket
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.persistence import PersistentMemoryStore, PostgresSnapshotRepository
from app.core.security import TokenError, create_access_token, parse_access_token, verify_password
from app.core.store import MemoryStore
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BRAIN_APPS = {
    "rd_brain": {
        "id": "rd_brain",
        "code": "rd_brain",
        "name": "研发大脑",
        "status": "active",
        "description": "把研发需求转成可确认、可回写、可沉淀的任务方案。",
        "config": {
            "default_task_types": ["product_detail_design", "technical_solution", "code_review"],
        },
    }
}

BUG_SOURCES = {"ai_auto_test", "manual_test"}
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
    status: str = "active"
    display_order: int = 0


class RelatedSystemPatchRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    owner_team: str | None = None
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


class RequirementRequest(BaseModel):
    title: str
    product_id: str
    version_id: str
    module_code: str | None = None
    content: str
    priority: str = "P1"


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
    permission_roles: list[str] = Field(default_factory=lambda: ["admin"])
    tags: list[str] = Field(default_factory=list)


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


def _payload_updates(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


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


def _model_gateway_metadata(
    current_store: MemoryStore,
) -> tuple[str, str, str | None]:
    config = _default_model_gateway_config(current_store)
    if config:
        return config["provider"], config["default_chat_model"], config["id"]
    if settings.model_gateway_status == "configured":
        return (
            "openai_compatible",
            settings.model_gateway_default_chat_model,
            None,
        )
    return "local_fallback", f"local-{settings.model_gateway_default_chat_model}", None


def _call_model_gateway_for_task(
    current_store: MemoryStore,
    *,
    task: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider, model, config_id = _model_gateway_metadata(current_store)
    started = perf_counter()
    output = _local_task_output(task)
    latency_ms = int((perf_counter() - started) * 1000)
    prompt_tokens = _estimate_tokens(
        {
            "task_type": task["task_type"],
            "requirement_id": task["requirement_id"],
            "product_id": task["product_id"],
        }
    )
    completion_tokens = _estimate_tokens(output)
    log = {
        "id": current_store.new_id("model_log"),
        "ai_task_id": task["id"],
        "provider": provider,
        "model": model,
        "purpose": task["task_type"],
        "tokens": {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens,
        },
        "latency_ms": latency_ms,
        "status": "succeeded",
        "error": None,
        "model_gateway_config_id": config_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    current_store.model_gateway_logs.append(log)
    return output, log


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


def _seeded_users_enabled() -> bool:
    return settings.allow_seeded_users or settings.app_env in {"local", "test", "development"}


@app.post("/api/auth/login")
def login(request: Request, payload: LoginRequest) -> dict[str, Any]:
    if (
        settings.persistence_mode != "postgres"
        and payload.username in SEEDED_USERS
        and not _seeded_users_enabled()
    ):
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
    try:
        created = request.app.state.user_repository.create_user(
            display_name=payload.display_name,
            password=payload.password,
            roles=payload.roles,
            status=payload.status,
            username=payload.username,
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
    updated = request.app.state.user_repository.update_user(
        user_id,
        payload.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise api_error(404, "NOT_FOUND", "User not found")
    return envelope(updated, get_trace_id(request))


@app.get("/api/brain-apps")
def list_brain_apps(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    items = sorted(BRAIN_APPS.values(), key=lambda item: item["code"])
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.get("/api/brain-apps/{brain_app_id}")
def get_brain_app(
    brain_app_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    brain_app = BRAIN_APPS.get(brain_app_id)
    if brain_app is None:
        brain_app = next(
            (item for item in BRAIN_APPS.values() if item["id"] == brain_app_id),
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
    product_id = current_store.new_id("product")
    code = payload.code or product_id
    product = {
        "id": product_id,
        "code": code,
        "name": payload.name,
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
    product.update(_payload_updates(payload))
    current_store.audit(
        event_type="product.updated",
        actor_id=user["id"],
        subject_type="product",
        subject_id=product_id,
    )
    return envelope(product, get_trace_id(request))


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
    version_id = current_store.new_id("version")
    version = {
        "id": version_id,
        "product_id": product_id,
        "code": payload.code or version_id,
        "name": payload.name,
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
    version.update(_payload_updates(payload))
    current_store.audit(
        event_type="product_version.updated",
        actor_id=user["id"],
        subject_type="product_version",
        subject_id=version_id,
    )
    return envelope(version, get_trace_id(request))


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
    module_id = current_store.new_id("module")
    module = {
        "id": module_id,
        "product_id": product_id,
        "code": payload.code or module_id,
        "name": payload.name,
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
    module.update(_payload_updates(payload))
    current_store.audit(
        event_type="product_module.updated",
        actor_id=user["id"],
        subject_type="product_module",
        subject_id=module_id,
    )
    return envelope(module, get_trace_id(request))


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
    if payload.git_provider != "gitlab":
        raise api_error(400, "VALIDATION_ERROR", "v1 MVP only supports GitLab bindings")
    if not payload.project_id and not payload.project_path:
        raise api_error(400, "VALIDATION_ERROR", "GitLab project_id or project_path is required")

    repository_id = current_store.new_id("repo")
    repository = {
        "id": repository_id,
        "product_id": product_id,
        "repo_type": payload.repo_type,
        "name": payload.name,
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


@app.get("/api/system/related-systems")
def list_related_systems(
    request: Request,
    active_only: bool = False,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    items = sorted(
        current_store.related_systems.values(),
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
    system_id = current_store.new_id("system")
    related_system = {
        "id": system_id,
        "code": payload.code or system_id,
        "name": payload.name,
        "description": payload.description,
        "owner_team": payload.owner_team,
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
    related_system.update(_payload_updates(payload))
    current_store.audit(
        event_type="related_system.updated",
        actor_id=user["id"],
        subject_type="related_system",
        subject_id=system_id,
    )
    return envelope(related_system, get_trace_id(request))


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


@app.post("/api/system/model-gateway-configs")
def create_model_gateway_config(
    request: Request,
    payload: ModelGatewayConfigRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = store(request)
    config_id = current_store.new_id("model_gateway_config")
    config = {
        "id": config_id,
        "name": payload.name,
        "provider": payload.provider,
        "base_url": payload.base_url,
        "api_key": payload.api_key,
        "default_chat_model": payload.default_chat_model,
        "default_embedding_model": payload.default_embedding_model,
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

    requirement_id = current_store.new_id("requirement")
    requirement = {
        "id": requirement_id,
        "title": payload.title,
        "product_id": payload.product_id,
        "version_id": payload.version_id,
        "module_code": payload.module_code,
        "content": payload.content,
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
    return {
        "product": current_store.snapshot(product),
        "version": current_store.snapshot(version),
        "module": current_store.snapshot(module) if module else None,
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

    task_id = current_store.new_id("task")
    task = {
        "id": task_id,
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
        payload={"task_type": "product_detail_design"},
    )
    return envelope(
        {"task_id": task_id, "task_type": task["task_type"], "task_status": task["status"]},
        get_trace_id(request),
    )


def _local_task_output(task: dict[str, Any]) -> dict[str, Any]:
    requirement = task["requirement_snapshot"]
    if task["task_type"] == "product_detail_design":
        return {
            "kind": "product_detail_design",
            "summary": f"围绕“{requirement['title']}”形成产品详细设计。",
            "user_value": requirement["content"],
            "acceptance_points": [
                "需求已审批并固化快照",
                "产出等待人工确认",
                "确认后可作为技术方案输入",
            ],
        }
    if task["task_type"] == "technical_solution":
        return {
            "kind": "technical_solution",
            "summary": f"围绕“{requirement['title']}”形成 FastAPI 模块化单体技术方案。",
            "architecture": [
                "通过 product_config、requirement、ai_task、review 和 audit 模块形成 MVP-A 主链路",
                "所有模型调用保留在 model_gateway 边界内",
                "高影响 AI 输出进入 human_reviews 后等待确认",
            ],
            "implementation_notes": [
                "任务保留 requirement_snapshot 和 product_context",
                "技术方案引用已确认产品详细设计任务",
                "Markdown 导出只使用已确认输出",
            ],
        }
    if task["task_type"] == "code_review":
        return {
            "kind": "code_review_report",
            "summary": "MR diff 存在一处高风险实现集中度问题，建议拆分并补充边界测试。",
            "risk_level": "medium",
            "findings": [
                {
                    "severity": "high",
                    "file_path": "apps/api/app/main.py",
                    "line_start": 120,
                    "line_end": 168,
                    "category": "maintainability",
                    "message": "接口编排和状态更新集中在单一模块，后续扩展时容易引入回归。",
                    "suggestion": "抽取领域服务并为状态机动作补充单元测试。",
                    "confidence": 0.82,
                }
            ],
            "executor": {
                "executor_type": "local_fallback",
                "executor_name": "deterministic-code-review",
                "retryable": False,
            },
        }
    return {"kind": task["task_type"], "summary": "Local fallback output"}


def _mock_gitlab_preview(repository: dict[str, Any], mr_iid: int) -> dict[str, Any]:
    project_path = repository.get("project_path") or f"project-{repository.get('project_id')}"
    return {
        "repository_id": repository["id"],
        "project_id": repository.get("project_id"),
        "project_path": project_path,
        "mr_iid": mr_iid,
        "title": f"Review MR !{mr_iid}: AI Brain MVP",
        "author": {"username": "developer", "name": "Developer"},
        "source_branch": f"feature/mvp-{mr_iid}",
        "target_branch": "main",
        "base_sha": f"base{mr_iid:04d}",
        "head_sha": f"head{mr_iid:04d}",
        "diff_refs": {"base_sha": f"base{mr_iid:04d}", "head_sha": f"head{mr_iid:04d}"},
        "changed_file_count": 2,
        "changed_files_summary": [
            {"path": "apps/api/app/main.py", "additions": 120, "deletions": 8},
            {"path": "apps/web/src/App.tsx", "additions": 80, "deletions": 4},
        ],
        "web_url": f"https://gitlab.local/{project_path}/-/merge_requests/{mr_iid}",
        "writeback_allowed": False,
    }


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
    preview = _mock_gitlab_preview(repository, mr_iid)
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

    preview = _mock_gitlab_preview(repository, mr_iid)
    diff_payload = _diff_payload(preview)
    diff_size_bytes = len(diff_payload.encode())
    diff_limit_bytes = 204_800
    if diff_size_bytes > diff_limit_bytes:
        raise api_error(413, "GITLAB_MR_DIFF_TOO_LARGE", "MR diff exceeds configured limit")

    snapshot_hash = hashlib.sha256(diff_payload.encode()).hexdigest()
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
    items.sort(key=lambda item: item["id"])
    return envelope(
        {"items": [_task_summary_projection(item) for item in items], "total": len(items)},
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

    task_id = current_store.new_id("task")
    task = {
        "id": task_id,
        "task_type": payload.task_type,
        "title": payload.title,
        "status": "draft",
        "requirement_id": requirement["id"],
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "module_code": requirement.get("module_code"),
        "requirement_snapshot": current_store.snapshot(requirement),
        "product_context": _product_context(current_store, requirement),
        "input_json": current_store.snapshot(payload.input),
        "output_json": None,
        "review_ids": [],
        "graph_run_ids": [],
        "current_step": "draft",
        "created_by": user["id"],
    }
    current_store.ai_tasks[task_id] = task
    current_store.audit(
        event_type="ai_task.created",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
        payload={"task_type": payload.task_type},
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
    checkpoint = {
        "id": checkpoint_id,
        "graph_run_id": graph_run["id"],
        "ai_task_id": task["id"],
        "current_step": current_step,
        "state_snapshot": current_store.snapshot(state_snapshot),
        "created_at": datetime.now(UTC).isoformat(),
    }
    current_store.graph_checkpoints[checkpoint_id] = checkpoint
    graph_run["checkpoint_id"] = checkpoint_id
    graph_run["current_step"] = current_step
    graph_run["state_snapshot"] = current_store.snapshot(state_snapshot)
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
    graph_run = {
        "id": graph_run_id,
        "ai_task_id": task["id"],
        "task_type": task["task_type"],
        "status": "interrupted",
        "current_step": "interrupt_for_human_review",
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
        current_step="interrupt_for_human_review",
        state_snapshot={
            "task_status": task["status"],
            "task_type": task["task_type"],
            "review_id": review_id,
            "output_kind": task["output_json"].get("kind"),
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


def _task_summary_projection(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task["id"],
        "task_type": task["task_type"],
        "title": task["title"],
        "status": task["status"],
        "requirement_id": task["requirement_id"],
        "product_id": task["product_id"],
        "version_id": task["version_id"],
        "module_code": task.get("module_code"),
        "current_step": task.get("current_step"),
        "created_by": task.get("created_by"),
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

    task["output_json"], model_log = _call_model_gateway_for_task(current_store, task=task)
    task["status"] = "waiting_review"
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
    task["output_json"] = {**task["output_json"], **edited_content}
    review["status"] = "edited_approved"
    review["edited_content"] = edited_content
    review["decided_by"] = user["id"]
    task["status"] = "completed"
    _confirm_code_review_report(current_store, task)
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
        payload={"decision": "edited_approved"},
    )
    return envelope(
        {"review_status": review["status"], "task_status": task["status"]},
        get_trace_id(request),
    )


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
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@app.post("/api/knowledge/documents")
def create_knowledge_document(
    request: Request,
    payload: KnowledgeDocumentRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"knowledge_owner", "rd_owner"})
    current_store = store(request)
    document_id = current_store.new_id("knowledge")
    document = {
        "id": document_id,
        "title": payload.title,
        "content": payload.content,
        "doc_type": payload.doc_type,
        "permission_roles": payload.permission_roles,
        "tags": payload.tags,
        "index_status": "indexed",
        "created_by": user["id"],
    }
    current_store.knowledge_documents[document_id] = document
    current_store.audit(
        event_type="knowledge_document.created",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    return envelope(document, get_trace_id(request))


@app.post("/api/knowledge/search")
def search_knowledge(
    request: Request,
    payload: KnowledgeSearchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    query = payload.query.lower()
    items = []
    for document in current_store.knowledge_documents.values():
        if not _user_can_read_roles(user, document["permission_roles"]):
            continue
        haystack = f"{document['title']} {document['content']}".lower()
        if query not in haystack:
            continue
        items.append(
            {
                "document_id": document["id"],
                "title": document["title"],
                "content": document["content"],
                "source": {"doc_type": document["doc_type"], "title": document["title"]},
            }
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
    subject_type: str | None = None,
    subject_id: str | None = None,
    event_type: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _require_roles(user, {"admin"})
    current_store = store(request)
    items = list(current_store.audit_events)
    if event_type:
        items = [item for item in items if item.get("event_type") == event_type]
    if ai_task_id:
        items = [item for item in items if item.get("ai_task_id") == ai_task_id]
    if subject_type:
        items = [item for item in items if item.get("subject_type") == subject_type]
    if subject_id:
        items = [item for item in items if item.get("subject_id") == subject_id]
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


def placeholder_payload(available_phase: str) -> dict[str, Any]:
    return {
        "status": "placeholder",
        "available_phase": available_phase,
        "message": "该入口在 MVP 阶段仅提供占位，不返回伪造统计数据。",
        "items": [],
    }


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


def _tasks_for_lifecycle_subject(
    current_store: MemoryStore,
    *,
    subject_type: str | None,
    subject_id: str | None,
    product_id: str | None,
    version_id: str | None,
    module_code: str | None,
) -> list[dict[str, Any]]:
    if subject_type == "requirement":
        requirement = current_store.requirements.get(str(subject_id))
        if requirement is None:
            raise api_error(404, "NOT_FOUND", "Requirement not found")
        tasks = [
            task
            for task in current_store.ai_tasks.values()
            if task.get("requirement_id") == subject_id
        ]
    elif subject_type == "ai_task":
        task = current_store.ai_tasks.get(str(subject_id))
        if task is None:
            raise api_error(404, "NOT_FOUND", "AI task not found")
        tasks = [task]
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
    if subject_type == "requirement":
        requirement = current_store.requirements.get(str(subject_id))
        if requirement is None:
            raise api_error(404, "NOT_FOUND", "Requirement not found")
        return {"type": "requirement", "id": subject_id, "product_id": requirement["product_id"]}
    if subject_type == "ai_task":
        task = current_store.ai_tasks.get(str(subject_id))
        if task is None:
            raise api_error(404, "NOT_FOUND", "AI task not found")
        return {"type": "ai_task", "id": subject_id, "product_id": task["product_id"]}
    return {"type": "product", "id": product_id, "product_id": product_id}


def _lifecycle_upstream(
    current_store: MemoryStore,
    *,
    subject_type: str | None,
    subject_id: str | None,
) -> list[dict[str, Any]]:
    if subject_type != "ai_task":
        return []
    task = current_store.ai_tasks[str(subject_id)]
    requirement = current_store.requirements.get(task["requirement_id"])
    if requirement is None:
        return []
    return [
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
    ]


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
    return signals


@app.get("/api/dashboard/it-team")
def dashboard_placeholder(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(placeholder_payload("MVP 占位 / v1.2"), get_trace_id(request))


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
        "title": payload.title,
        "severity": payload.severity,
        "description": payload.description,
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


@app.get("/api/devops/gitlab/daily-code-metrics")
def gitlab_metrics_placeholder(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(placeholder_payload("MVP 占位 / v1.2"), get_trace_id(request))


@app.get("/api/devops/jenkins/releases")
def jenkins_releases_placeholder(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(placeholder_payload("MVP 占位 / v1.2"), get_trace_id(request))


@app.get("/api/ops/online-log-metrics")
def online_log_metrics_placeholder(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(placeholder_payload("MVP 占位 / v1.2"), get_trace_id(request))


@app.get("/api/insights/usage-metrics")
def usage_metrics_placeholder(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(placeholder_payload("MVP 占位 / v1.2"), get_trace_id(request))


@app.get("/api/insights/user-feedback")
def user_feedback_placeholder(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(placeholder_payload("MVP 占位 / v1.2"), get_trace_id(request))


@app.get("/api/planning/iteration-suggestions")
def iteration_suggestions_placeholder(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(placeholder_payload("MVP 占位 / v1.2"), get_trace_id(request))


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
    upstream = (
        _lifecycle_upstream(current_store, subject_type=subject_type, subject_id=subject_id)
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
    missing_context = [
        "automated_testing",
        "bug",
        "release",
        "online_log",
        "usage_metric",
        "user_feedback",
        "iteration_planning",
    ]

    return envelope(
        {
            "status": "available",
            "subject": _lifecycle_subject(
                current_store,
                subject_type=subject_type,
                subject_id=subject_id,
                product_id=product_id,
            ),
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
    if task["status"] != "completed":
        raise api_error(409, "TASK_STATE_INVALID", "Only completed tasks can be exported")

    trace_id = get_trace_id(request)
    return PlainTextResponse(
        _render_markdown(current_store, task),
        media_type="text/markdown",
        headers={"X-Trace-Id": trace_id},
    )
