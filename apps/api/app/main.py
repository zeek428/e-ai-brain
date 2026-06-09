from __future__ import annotations

import logging
from time import perf_counter
from typing import Any
from urllib.request import urlopen  # noqa: F401 - kept for existing test/provider injection hooks

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers.assistant import router as assistant_router
from app.api.routers.attribution import router as attribution_router
from app.api.routers.audit import router as audit_router
from app.api.routers.auth import router as auth_router
from app.api.routers.brain_apps import router as brain_apps_router
from app.api.routers.bugs import router as bugs_router
from app.api.routers.code_review_reports import router as code_review_reports_router
from app.api.routers.collectors import router as collectors_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.devops_metrics import router as devops_metrics_router
from app.api.routers.export import router as export_router
from app.api.routers.git_review import router as git_review_router
from app.api.routers.knowledge import router as knowledge_router
from app.api.routers.lifecycle import router as lifecycle_router
from app.api.routers.model_gateway import router as model_gateway_router
from app.api.routers.platform import router as platform_router
from app.api.routers.product_git_repositories import router as product_git_repositories_router
from app.api.routers.product_modules import router as product_modules_router
from app.api.routers.product_versions import router as product_versions_router
from app.api.routers.products import router as products_router
from app.api.routers.related_systems import router as related_systems_router
from app.api.routers.requirements import router as requirements_router
from app.api.routers.system_rbac import router as system_rbac_router
from app.api.routers.tasks import router as tasks_router
from app.api.routers.user_insights import router as user_insights_router
from app.api.routers.users import router as users_router
from app.api.routers.writeback import router as writeback_router
from app.core.config import get_settings
from app.core.persistence import PostgresSnapshotRepository
from app.core.persistence_runtime import PostgresRuntimeStore
from app.core.repositories.authorization import (
    CompatibilityAuthorizationRepository,
    PostgresAuthorizationRepository,
)
from app.core.store import MemoryStore
from app.core.trace import get_trace_id, new_trace_id
from app.core.users import MemoryUserRepository, PostgresUserRepository

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise AI Brain API", version="0.1.0")


def _is_test_env() -> bool:
    return settings.app_env.lower() in {"test", "testing", "pytest"}


def _ensure_memory_mode_allowed() -> None:
    if settings.persistence_mode == "memory" and not _is_test_env():
        raise RuntimeError("PERSISTENCE_MODE=memory is only allowed when APP_ENV=test")


def build_store() -> MemoryStore:
    if settings.persistence_mode == "postgres":
        repository = PostgresSnapshotRepository(
            settings.database_url,
            ensure_schema_compatibility=not _is_test_env(),
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


def build_authorization_repository() -> (
    CompatibilityAuthorizationRepository | PostgresAuthorizationRepository
):
    if settings.persistence_mode == "postgres":
        return PostgresAuthorizationRepository(
            settings.database_url,
            pool_max_size=settings.database_pool_max_size,
        )
    _ensure_memory_mode_allowed()
    if settings.persistence_mode != "memory":
        raise RuntimeError(f"Unsupported PERSISTENCE_MODE={settings.persistence_mode}")
    return CompatibilityAuthorizationRepository()


app.state.store = build_store()
app.state.user_repository = build_user_repository()
app.state.authorization_repository = build_authorization_repository()
app.state.code_review_executor = None
app.state.dashboard_cache = {}
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(assistant_router)
app.include_router(audit_router)
app.include_router(attribution_router)
app.include_router(auth_router)
app.include_router(brain_apps_router)
app.include_router(bugs_router)
app.include_router(code_review_reports_router)
app.include_router(collectors_router)
app.include_router(dashboard_router)
app.include_router(devops_metrics_router)
app.include_router(export_router)
app.include_router(git_review_router)
app.include_router(knowledge_router)
app.include_router(lifecycle_router)
app.include_router(model_gateway_router)
app.include_router(platform_router)
app.include_router(product_git_repositories_router)
app.include_router(product_modules_router)
app.include_router(product_versions_router)
app.include_router(products_router)
app.include_router(related_systems_router)
app.include_router(requirements_router)
app.include_router(system_rbac_router)
app.include_router(tasks_router)
app.include_router(user_insights_router)
app.include_router(users_router)
app.include_router(writeback_router)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    request.state.trace_id = new_trace_id()
    request.state.started_at = perf_counter()
    response = await call_next(request)
    response.headers["X-Trace-Id"] = request.state.trace_id
    return response


def _request_started_at(request: Request) -> float | None:
    started_at = getattr(request.state, "started_at", None)
    return started_at if isinstance(started_at, float) else None


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
