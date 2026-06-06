from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.devops_metrics import list_operational_metrics_response
from app.services.operational_gitlab_metrics import (
    create_gitlab_metric_response,
    list_gitlab_metrics_response,
)
from app.services.operational_jenkins_releases import (
    create_jenkins_release_response,
    list_jenkins_releases_response,
)
from app.services.operational_online_logs import (
    create_online_log_metric_response,
    list_online_log_metrics_response,
)

router = APIRouter(tags=["devops-metrics"])


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


@router.get("/api/devops/operational-metrics")
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
    started_at = getattr(request.state, "started_at", None)
    payload = list_operational_metrics_response(
        category=category,
        current_store=store(request),
        name=name,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at if isinstance(started_at, float) else perf_counter(),
        status=status,
        trace_id=get_trace_id(request),
    )
    return envelope(payload, get_trace_id(request))


@router.get("/api/devops/gitlab/daily-code-metrics")
def gitlab_metrics(
    request: Request,
    product_id: str | None = None,
    repository_id: str | None = None,
    date: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_gitlab_metrics_response(
        current_store=store(request),
        date=date,
        product_id=product_id,
        repository_id=repository_id,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/devops/gitlab/daily-code-metrics")
def create_gitlab_metric(
    payload: GitlabDailyCodeMetricRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    metric = create_gitlab_metric_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(metric, get_trace_id(request))


@router.get("/api/devops/jenkins/releases")
def jenkins_releases(
    request: Request,
    product_id: str | None = None,
    version_id: str | None = None,
    status: str | None = None,
    environment: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_jenkins_releases_response(
        current_store=store(request),
        environment=environment,
        product_id=product_id,
        status=status,
        version_id=version_id,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/devops/jenkins/releases")
def create_jenkins_release(
    payload: JenkinsReleaseRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    release = create_jenkins_release_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(release, get_trace_id(request))


@router.get("/api/ops/online-log-metrics")
def online_log_metrics(
    request: Request,
    product_id: str | None = None,
    module_code: str | None = None,
    environment: str | None = None,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_online_log_metrics_response(
        current_store=store(request),
        environment=environment,
        from_=from_,
        module_code=module_code,
        product_id=product_id,
        to=to,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/ops/online-log-metrics")
def create_online_log_metric(
    payload: OnlineLogMetricRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    metric = create_online_log_metric_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(metric, get_trace_id(request))
