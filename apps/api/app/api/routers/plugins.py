from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.ai_executor_runners import (
    append_ai_executor_task_logs_response,
    cancel_ai_executor_task_response,
    claim_ai_executor_task_response,
    complete_ai_executor_task_response,
    create_ai_executor_runner_install_package_response,
    create_ai_executor_runner_response,
    delete_ai_executor_runner_response,
    list_ai_executor_runners_response,
    list_ai_executor_task_logs_response,
    list_ai_executor_tasks_response,
    patch_ai_executor_runner_response,
    rotate_ai_executor_runner_token_response,
    runner_heartbeat_response,
    test_ai_executor_runner_response,
    timeout_ai_executor_tasks_response,
)
from app.services.plugins import (
    copy_plugin_response,
    create_plugin_action_response,
    create_plugin_connection_response,
    create_plugin_response,
    delete_plugin_action_response,
    delete_plugin_connection_response,
    delete_plugin_response,
    invoke_plugin_action_response,
    list_plugin_action_templates_response,
    list_plugin_actions_response,
    list_plugin_connections_response,
    list_plugin_invocation_logs_response,
    list_plugin_marketplace_response,
    list_plugins_response,
    list_result_write_records_response,
    list_result_write_targets_response,
    patch_plugin_action_response,
    patch_plugin_connection_response,
    patch_plugin_response,
    plugin_system_variables_response,
    test_plugin_connection_response,
    trial_plugin_action_response,
)

router = APIRouter(tags=["plugins"])


def _request_started_at(request: Request) -> float | None:
    started_at = getattr(request.state, "started_at", None)
    return started_at if isinstance(started_at, float) else None


class PluginRequest(BaseModel):
    category: str = "general"
    code: str
    description: str | None = None
    name: str
    protocol: str = "http"
    risk_level: str = "medium"
    status: str = "active"


class PluginPatchRequest(BaseModel):
    category: str | None = None
    code: str | None = None
    description: str | None = None
    name: str | None = None
    protocol: str | None = None
    risk_level: str | None = None
    status: str | None = None


class PluginCopyRequest(BaseModel):
    category: str | None = None
    code: str | None = None
    description: str | None = None
    name: str | None = None
    protocol: str | None = None
    risk_level: str | None = None
    status: str | None = None


class PluginConnectionRequest(BaseModel):
    auth_config: dict[str, Any] = Field(default_factory=dict)
    auth_type: str = "none"
    endpoint_url: str
    environment: str = "default"
    max_retries: int = 0
    name: str
    plugin_id: str
    request_config: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"
    timeout_seconds: int = 30


class PluginConnectionPatchRequest(BaseModel):
    auth_config: dict[str, Any] | None = None
    auth_type: str | None = None
    endpoint_url: str | None = None
    environment: str | None = None
    max_retries: int | None = None
    name: str | None = None
    plugin_id: str | None = None
    request_config: dict[str, Any] | None = None
    status: str | None = None
    timeout_seconds: int | None = None


class PluginActionRequest(BaseModel):
    action_type: str = "http_request"
    code: str
    connection_id: str | None = None
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    name: str
    output_schema: dict[str, Any] = Field(default_factory=dict)
    plugin_id: str
    request_config: dict[str, Any] = Field(default_factory=dict)
    requires_human_review: bool = False
    result_mapping: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class PluginActionPatchRequest(BaseModel):
    action_type: str | None = None
    code: str | None = None
    connection_id: str | None = None
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    name: str | None = None
    output_schema: dict[str, Any] | None = None
    plugin_id: str | None = None
    request_config: dict[str, Any] | None = None
    requires_human_review: bool | None = None
    result_mapping: dict[str, Any] | None = None
    status: str | None = None


class PluginInvokeRequest(BaseModel):
    connection_id: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    trigger_type: str = "manual"


class PluginActionTrialRequest(BaseModel):
    connection_id: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)


class AiExecutorRunnerRequest(BaseModel):
    endpoint_url: str = "runner://local"
    executor_types: list[str] = Field(default_factory=lambda: ["codex"])
    heartbeat_timeout_seconds: int = 120
    max_concurrent_tasks: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    name: str
    protocol: str = "runner_polling"
    runner_token: str | None = None
    status: str = "active"
    workspace_roots: list[str] = Field(default_factory=list)


class AiExecutorRunnerPatchRequest(BaseModel):
    endpoint_url: str | None = None
    executor_types: list[str] | None = None
    heartbeat_timeout_seconds: int | None = None
    max_concurrent_tasks: int | None = None
    metadata: dict[str, Any] | None = None
    name: str | None = None
    protocol: str | None = None
    runner_token: str | None = None
    status: str | None = None
    workspace_roots: list[str] | None = None


class AiExecutorRunnerHeartbeatRequest(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class AiExecutorRunnerTokenRotateRequest(BaseModel):
    runner_token: str | None = None


class AiExecutorTaskClaimRequest(BaseModel):
    executor_type: str | None = None
    runner_id: str


class AiExecutorTaskLogAppendRequest(BaseModel):
    logs: list[dict[str, Any]] = Field(default_factory=list)
    runner_id: str
    status: str = "running"


class AiExecutorTaskCancelRequest(BaseModel):
    reason: str | None = None


class AiExecutorTaskCompleteRequest(BaseModel):
    error_code: str | None = None
    error_message: str | None = None
    logs: list[dict[str, Any]] = Field(default_factory=list)
    result_json: dict[str, Any] = Field(default_factory=dict)
    runner_id: str
    status: str


class AiExecutorTaskTimeoutScanRequest(BaseModel):
    now: str | None = None


@router.get("/api/system/ai-executor-runners")
def list_ai_executor_runners(
    request: Request,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_ai_executor_runners_response(
            current_store=store(request),
            status=status,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-runners")
def create_ai_executor_runner(
    payload: AiExecutorRunnerRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_ai_executor_runner_response(
            current_store=store(request),
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/ai-executor-runners/{runner_id}/install-package")
def download_ai_executor_runner_install_package(
    request: Request,
    runner_id: str,
    target_os: str | None = Query(default=None),
    arch: str | None = Query(default=None),
    install_mode: str | None = Query(default=None),
    user: dict[str, Any] = CurrentUser,
) -> Response:
    content, filename = create_ai_executor_runner_install_package_response(
        arch=arch,
        current_store=store(request),
        install_mode=install_mode,
        runner_id=runner_id,
        target_os=target_os,
        user=user,
    )
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/api/system/ai-executor-runners/{runner_id}")
def patch_ai_executor_runner(
    payload: AiExecutorRunnerPatchRequest,
    request: Request,
    runner_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_ai_executor_runner_response(
            current_store=store(request),
            payload=payload,
            runner_id=runner_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-runners/{runner_id}/rotate-token")
def rotate_ai_executor_runner_token(
    payload: AiExecutorRunnerTokenRotateRequest,
    request: Request,
    runner_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        rotate_ai_executor_runner_token_response(
            current_store=store(request),
            payload=payload,
            runner_id=runner_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-runners/{runner_id}/test")
def test_ai_executor_runner(
    request: Request,
    runner_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        test_ai_executor_runner_response(
            current_store=store(request),
            runner_id=runner_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.delete("/api/system/ai-executor-runners/{runner_id}")
def delete_ai_executor_runner(
    request: Request,
    runner_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        delete_ai_executor_runner_response(
            current_store=store(request),
            runner_id=runner_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-runners/{runner_id}/heartbeat")
def ai_executor_runner_heartbeat(
    payload: AiExecutorRunnerHeartbeatRequest,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    return envelope(
        runner_heartbeat_response(
            current_store=store(request),
            metadata=payload.metadata,
            request=request,
            runner_id=runner_id,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/ai-executor-tasks")
def list_ai_executor_tasks(
    request: Request,
    ai_task_id: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    runner_id: str | None = Query(default=None),
    scheduled_job_run_id: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    sort_order: str = Query(default="desc"),
    status: str | None = Query(default=None),
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_ai_executor_tasks_response(
            ai_task_id=ai_task_id,
            current_store=store(request),
            page=page,
            page_size=page_size,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            sort_by=sort_by,
            sort_order=sort_order,
            started_at=_request_started_at(request),
            status=status,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/ai-executor-tasks/{task_id}/logs")
def list_ai_executor_task_logs(
    request: Request,
    task_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_ai_executor_task_logs_response(
            current_store=store(request),
            task_id=task_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-tasks/{task_id}/logs")
def append_ai_executor_task_logs(
    payload: AiExecutorTaskLogAppendRequest,
    request: Request,
    task_id: str,
) -> dict[str, Any]:
    return envelope(
        append_ai_executor_task_logs_response(
            current_store=store(request),
            payload=payload,
            request=request,
            task_id=task_id,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-tasks/{task_id}/cancel")
def cancel_ai_executor_task(
    payload: AiExecutorTaskCancelRequest,
    request: Request,
    task_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        cancel_ai_executor_task_response(
            current_store=store(request),
            payload=payload,
            task_id=task_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-tasks/timeout-scan")
def timeout_ai_executor_tasks(
    payload: AiExecutorTaskTimeoutScanRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        timeout_ai_executor_tasks_response(
            current_store=store(request),
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-tasks/claim")
def claim_ai_executor_task(
    payload: AiExecutorTaskClaimRequest,
    request: Request,
) -> dict[str, Any]:
    return envelope(
        claim_ai_executor_task_response(
            current_store=store(request),
            executor_type=payload.executor_type,
            request=request,
            runner_id=payload.runner_id,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-executor-tasks/{task_id}/complete")
def complete_ai_executor_task(
    payload: AiExecutorTaskCompleteRequest,
    request: Request,
    task_id: str,
) -> dict[str, Any]:
    return envelope(
        complete_ai_executor_task_response(
            current_store=store(request),
            payload=payload,
            request=request,
            task_id=task_id,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/plugins")
def list_plugins(
    request: Request,
    protocol: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugins_response(
            current_store=store(request),
            protocol=protocol,
            status=status,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/plugin-marketplace")
def list_plugin_marketplace(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugin_marketplace_response(current_store=store(request), user=user),
        get_trace_id(request),
    )


@router.get("/api/system/plugin-action-templates")
def list_plugin_action_templates(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugin_action_templates_response(current_store=store(request), user=user),
        get_trace_id(request),
    )


@router.get("/api/system/result-write-targets")
def list_result_write_targets(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_result_write_targets_response(current_store=store(request), user=user),
        get_trace_id(request),
    )


@router.get("/api/system/result-write-records")
def list_result_write_records(
    request: Request,
    plugin_action_id: str | None = None,
    scheduled_job_id: str | None = None,
    scheduled_job_run_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
    write_target: str | None = None,
) -> dict[str, Any]:
    return envelope(
        list_result_write_records_response(
            current_store=store(request),
            plugin_action_id=plugin_action_id,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
            user=user,
            write_target=write_target,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/plugins")
def create_plugin(
    payload: PluginRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_plugin_response(current_store=store(request), payload=payload, user=user),
        get_trace_id(request),
    )


@router.post("/api/system/plugins/{plugin_id}/copy")
def copy_plugin(
    payload: PluginCopyRequest,
    plugin_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        copy_plugin_response(
            current_store=store(request),
            payload=payload,
            plugin_id=plugin_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.patch("/api/system/plugins/{plugin_id}")
def patch_plugin(
    payload: PluginPatchRequest,
    plugin_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_plugin_response(
            current_store=store(request),
            payload=payload,
            plugin_id=plugin_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.delete("/api/system/plugins/{plugin_id}")
def delete_plugin(
    plugin_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        delete_plugin_response(
            current_store=store(request),
            plugin_id=plugin_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/plugin-connections")
def list_plugin_connections(
    request: Request,
    environment: str | None = None,
    keyword: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    plugin_id: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugin_connections_response(
            current_store=store(request),
            environment=environment,
            keyword=keyword,
            page=page,
            page_size=page_size,
            plugin_id=plugin_id,
            sort_by=sort_by,
            sort_order=sort_order,
            started_at=_request_started_at(request),
            status=status,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/plugin-connections")
def create_plugin_connection(
    payload: PluginConnectionRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_plugin_connection_response(
            current_store=store(request),
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.patch("/api/system/plugin-connections/{connection_id}")
def patch_plugin_connection(
    connection_id: str,
    payload: PluginConnectionPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_plugin_connection_response(
            connection_id=connection_id,
            current_store=store(request),
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.delete("/api/system/plugin-connections/{connection_id}")
def delete_plugin_connection(
    connection_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        delete_plugin_connection_response(
            connection_id=connection_id,
            current_store=store(request),
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/plugin-connections/{connection_id}/test")
def test_plugin_connection(
    connection_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        test_plugin_connection_response(
            connection_id=connection_id,
            current_store=store(request),
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/plugin-actions")
def list_plugin_actions(
    request: Request,
    keyword: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    plugin_id: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugin_actions_response(
            current_store=store(request),
            keyword=keyword,
            page=page,
            page_size=page_size,
            plugin_id=plugin_id,
            sort_by=sort_by,
            sort_order=sort_order,
            started_at=_request_started_at(request),
            status=status,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/plugin-actions")
def create_plugin_action(
    payload: PluginActionRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_plugin_action_response(current_store=store(request), payload=payload, user=user),
        get_trace_id(request),
    )


@router.patch("/api/system/plugin-actions/{action_id}")
def patch_plugin_action(
    action_id: str,
    payload: PluginActionPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_plugin_action_response(
            action_id=action_id,
            current_store=store(request),
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.delete("/api/system/plugin-actions/{action_id}")
def delete_plugin_action(
    action_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        delete_plugin_action_response(
            action_id=action_id,
            current_store=store(request),
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/plugin-actions/{action_id}/invoke")
def invoke_plugin_action(
    action_id: str,
    payload: PluginInvokeRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        invoke_plugin_action_response(
            action_id=action_id,
            connection_id=payload.connection_id,
            current_store=store(request),
            input_payload=payload.input_payload,
            trace_id=get_trace_id(request),
            trigger_type=payload.trigger_type,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/plugin-actions/{action_id}/trial")
def trial_plugin_action(
    action_id: str,
    payload: PluginActionTrialRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        trial_plugin_action_response(
            action_id=action_id,
            connection_id=payload.connection_id,
            current_store=store(request),
            input_payload=payload.input_payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/plugin-system-variables")
def plugin_system_variables(
    request: Request,
    timezone: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        plugin_system_variables_response(timezone_name=timezone, user=user),
        get_trace_id(request),
    )


@router.get("/api/system/plugin-invocation-logs")
def list_plugin_invocation_logs(
    request: Request,
    action_id: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    scheduled_job_id: str | None = None,
    scheduled_job_run_id: str | None = None,
    sort_by: str | None = Query(default=None),
    sort_order: str = Query(default="desc"),
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugin_invocation_logs_response(
            action_id=action_id,
            current_store=store(request),
            page=page,
            page_size=page_size,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            sort_by=sort_by,
            sort_order=sort_order,
            started_at=_request_started_at(request),
            status=status,
            user=user,
        ),
        get_trace_id(request),
    )
