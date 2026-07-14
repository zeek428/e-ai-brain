from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, api_error, require_any_permission_or_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.devops_metrics import list_operational_metrics_response
from app.services.operational_deployments import (
    cancel_deployment_request_response,
    complete_deployment_request_response,
    create_deployment_request_response,
    create_deployment_scheme_response,
    delete_deployment_scheme_response,
    deployment_connectivity_probe_logs_response,
    deployment_connectivity_probe_response,
    deployment_connectivity_probe_status_response,
    get_deployment_request_detail_response,
    get_deployment_run_logs_response,
    get_deployment_scheme_response,
    list_deployment_jenkins_connections_response,
    list_deployment_requests_response,
    list_deployment_runner_targets_response,
    list_deployment_schemes_response,
    probe_deployment_jenkins_connection_response,
    rollback_deployment_request_response,
    start_deployment_request_response,
    sync_jenkins_deployment_response,
    update_deployment_scheme_response,
)
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
from app.services.product_scope import require_product_scope
from app.services.production_change_controls import (
    approve_production_change,
    production_deployment_control,
    set_release_freeze,
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
    deployment_request_id: str | None = None


class DeploymentRequestCreate(BaseModel):
    product_id: str
    version_id: str
    deployment_scheme_id: str | None = None
    title: str
    requirement_ids: list[str] = Field(default_factory=list)
    environment: str = "prod"
    deploy_window_start: str | None = None
    deploy_window_end: str | None = None
    release_branch: str | None = None
    commit_sha: str | None = None
    artifact_version: str | None = None
    artifact_digest: str | None = None
    release_readiness_task_id: str | None = None
    rollback_plan: str | None = None
    risk_level: str = "medium"
    assigned_ops_user: str | None = None


class DeploymentSchemeCreate(BaseModel):
    product_id: str
    code: str
    name: str
    environment: str = "prod"
    deployment_method: str = "manual"
    runner_id: str | None = None
    target_code: str | None = None
    jenkins_connection_id: str | None = None
    jenkins_job_name: str | None = None
    timeout_seconds: int = Field(default=1800, ge=30, le=86400)
    config: dict[str, Any] = Field(default_factory=dict)
    rollout_strategy: str = "all_at_once"
    wave_config: dict[str, Any] = Field(default_factory=dict)
    preflight_config: dict[str, Any] = Field(default_factory=dict)
    health_check_config: dict[str, Any] = Field(default_factory=dict)
    rollback_config: dict[str, Any] = Field(default_factory=dict)
    window_enforcement: str | None = None
    is_default: bool = False
    status: str = "active"


class DeploymentSchemeUpdate(BaseModel):
    version: int = Field(ge=1)
    code: str | None = None
    name: str | None = None
    environment: str | None = None
    deployment_method: str | None = None
    runner_id: str | None = None
    target_code: str | None = None
    jenkins_connection_id: str | None = None
    jenkins_job_name: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=30, le=86400)
    config: dict[str, Any] | None = None
    rollout_strategy: str | None = None
    wave_config: dict[str, Any] | None = None
    preflight_config: dict[str, Any] | None = None
    health_check_config: dict[str, Any] | None = None
    rollback_config: dict[str, Any] | None = None
    window_enforcement: str | None = None
    is_default: bool | None = None
    status: str | None = None


class DeploymentStartRequest(BaseModel):
    executor_type: str | None = "manual"
    external_job_name: str | None = None
    external_build_id: str | None = None
    log_url: str | None = None


class DeploymentJenkinsConnectionProbeRequest(BaseModel):
    product_id: str
    environment: str
    jenkins_job_name: str


class ProductionChangeApprovalRequest(BaseModel):
    decision: str = "approved"
    role_code: str


class ReleaseFreezeRequest(BaseModel):
    product_id: str
    status: str = "active"


class DeploymentCompleteRequest(BaseModel):
    status: str = "success"
    failure_reason: str | None = None
    finished_at: str | None = None
    executor_type: str | None = "manual"
    external_job_name: str | None = None
    external_build_id: str | None = None
    log_url: str | None = None


class DeploymentCancelRequest(BaseModel):
    reason: str | None = None


class DeploymentRollbackRequest(BaseModel):
    reason: str


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
    exclude_category: str | None = None,
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
        exclude_category=exclude_category,
        name=name,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at if isinstance(started_at, float) else perf_counter(),
        status=status,
        trace_id=get_trace_id(request),
        user=user,
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


@router.get("/api/devops/deployments")
def deployment_requests(
    request: Request,
    product_id: str | None = None,
    version_id: str | None = None,
    status: str | None = None,
    environment: str | None = None,
    title: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_deployment_requests_response(
        current_store=store(request),
        environment=environment,
        page=page,
        page_size=page_size,
        product_id=product_id,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
        title=title,
        user=user,
        version_id=version_id,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployments/{deployment_request_id}")
def deployment_request_detail(
    deployment_request_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = get_deployment_request_detail_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployment-schemes")
def deployment_schemes(
    request: Request,
    product_id: str | None = None,
    environment: str | None = None,
    deployment_method: str | None = None,
    status: str | None = None,
    name: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_deployment_schemes_response(
        current_store=store(request),
        deployment_method=deployment_method,
        environment=environment,
        name=name,
        page=page,
        page_size=page_size,
        product_id=product_id,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployment-runner-targets")
def deployment_runner_targets(
    request: Request,
    product_id: str | None = None,
    environment: str | None = None,
    runner_id: str | None = None,
    method: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_deployment_runner_targets_response(
        current_store=store(request),
        environment=environment,
        method=method,
        product_id=product_id,
        runner_id=runner_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployment-jenkins-connections")
def deployment_jenkins_connections(
    request: Request,
    product_id: str | None = None,
    environment: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_deployment_jenkins_connections_response(
        current_store=store(request),
        environment=environment,
        product_id=product_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/devops/deployment-jenkins-connections/{connection_id}/connectivity-probe")
def deployment_jenkins_connection_probe(
    connection_id: str,
    payload: DeploymentJenkinsConnectionProbeRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = probe_deployment_jenkins_connection_response(
        connection_id=connection_id,
        current_store=store(request),
        environment=payload.environment,
        job_name=payload.jenkins_job_name,
        product_id=payload.product_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/devops/deployment-schemes")
def create_deployment_scheme(
    payload: DeploymentSchemeCreate,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = create_deployment_scheme_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployment-schemes/{scheme_id}")
def get_deployment_scheme(
    scheme_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = get_deployment_scheme_response(
        current_store=store(request),
        scheme_id=scheme_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.patch("/api/devops/deployment-schemes/{scheme_id}")
def update_deployment_scheme(
    scheme_id: str,
    payload: DeploymentSchemeUpdate,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = update_deployment_scheme_response(
        current_store=store(request),
        payload=payload,
        scheme_id=scheme_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.delete("/api/devops/deployment-schemes/{scheme_id}")
def delete_deployment_scheme(
    scheme_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = delete_deployment_scheme_response(
        current_store=store(request),
        scheme_id=scheme_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/devops/deployments")
def create_deployment_request(
    payload: DeploymentRequestCreate,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    deployment = create_deployment_request_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(deployment, get_trace_id(request))


@router.post("/api/devops/deployments/{deployment_request_id}/start")
def start_deployment_request(
    deployment_request_id: str,
    payload: DeploymentStartRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    deployment = start_deployment_request_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        payload=payload,
        user=user,
    )
    return envelope(deployment, get_trace_id(request))


@router.post("/api/devops/deployments/{deployment_request_id}/connectivity-probe")
def deployment_connectivity_probe(
    deployment_request_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = deployment_connectivity_probe_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployments/{deployment_request_id}/connectivity-probe")
def deployment_connectivity_probe_status(
    deployment_request_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = deployment_connectivity_probe_status_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployments/{deployment_request_id}/connectivity-probe/logs")
def deployment_connectivity_probe_logs(
    deployment_request_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = deployment_connectivity_probe_logs_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployments/{deployment_request_id}/production-change-control")
def get_production_change_control(
    deployment_request_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    control = production_deployment_control(store(request), deployment_id=deployment_request_id)
    if control is None:
        return envelope(None, get_trace_id(request))
    require_product_scope(user, control["product_id"])
    return envelope(control, get_trace_id(request))


@router.post("/api/devops/deployments/{deployment_request_id}/production-change-control/approve")
def approve_production_change_control(
    deployment_request_id: str,
    payload: ProductionChangeApprovalRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    control = production_deployment_control(store(request), deployment_id=deployment_request_id)
    if control is None:
        raise api_error(404, "NOT_FOUND", "Production change control not found")
    require_product_scope(user, control["product_id"])
    require_any_permission_or_roles(user, {"deployment.execute"}, {"release_owner", "test_owner"})
    approval = approve_production_change(
        store(request),
        control_id=control["id"],
        decision=payload.decision,
        role_code=payload.role_code,
        user_id=user["id"],
        user_roles=set(user.get("roles") or []),
    )
    return envelope(approval, get_trace_id(request))


@router.post("/api/devops/release-freezes")
def update_release_freeze(
    payload: ReleaseFreezeRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_product_scope(user, payload.product_id)
    require_any_permission_or_roles(user, {"deployment.execute"}, {"release_owner"})
    freeze = set_release_freeze(
        store(request),
        created_by=user["id"],
        product_id=payload.product_id,
        status=payload.status,
    )
    return envelope(freeze, get_trace_id(request))


@router.post("/api/devops/deployments/{deployment_request_id}/complete")
def complete_deployment_request(
    deployment_request_id: str,
    payload: DeploymentCompleteRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    deployment = complete_deployment_request_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        payload=payload,
        user=user,
    )
    return envelope(deployment, get_trace_id(request))


@router.post("/api/devops/deployments/{deployment_request_id}/cancel")
def cancel_deployment_request(
    deployment_request_id: str,
    payload: DeploymentCancelRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    deployment = cancel_deployment_request_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        payload=payload,
        user=user,
    )
    return envelope(deployment, get_trace_id(request))


@router.post("/api/devops/deployments/{deployment_request_id}/rollback")
def rollback_deployment_request(
    deployment_request_id: str,
    payload: DeploymentRollbackRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    deployment = rollback_deployment_request_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        payload=payload,
        user=user,
    )
    return envelope(deployment, get_trace_id(request))


@router.post("/api/devops/deployments/{deployment_request_id}/runs/{deployment_run_id}/sync")
def sync_deployment_run(
    deployment_request_id: str,
    deployment_run_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = sync_jenkins_deployment_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        deployment_run_id=deployment_run_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.get("/api/devops/deployments/{deployment_request_id}/runs/{deployment_run_id}/logs")
def deployment_run_logs(
    deployment_request_id: str,
    deployment_run_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = get_deployment_run_logs_response(
        current_store=store(request),
        deployment_request_id=deployment_request_id,
        deployment_run_id=deployment_run_id,
        user=user,
    )
    return envelope(result, get_trace_id(request))


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
