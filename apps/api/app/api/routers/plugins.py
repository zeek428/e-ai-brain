from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.plugins import (
    create_plugin_action_response,
    create_plugin_connection_response,
    create_plugin_response,
    invoke_plugin_action_response,
    list_plugin_actions_response,
    list_plugin_connections_response,
    list_plugin_invocation_logs_response,
    list_plugins_response,
    patch_plugin_action_response,
    patch_plugin_connection_response,
    patch_plugin_response,
    plugin_system_variables_response,
    test_plugin_connection_response,
    trial_plugin_action_response,
)

router = APIRouter(tags=["plugins"])


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


class PluginConnectionRequest(BaseModel):
    auth_config: dict[str, Any] = Field(default_factory=dict)
    auth_type: str = "none"
    endpoint_url: str
    environment: str = "default"
    max_retries: int = 0
    name: str
    plugin_id: str
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


@router.get("/api/system/plugins")
def list_plugins(
    request: Request,
    protocol: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugins_response(current_store=store(request), protocol=protocol, status=status),
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


@router.get("/api/system/plugin-connections")
def list_plugin_connections(
    request: Request,
    plugin_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugin_connections_response(
            current_store=store(request),
            plugin_id=plugin_id,
            status=status,
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
    plugin_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugin_actions_response(
            current_store=store(request),
            plugin_id=plugin_id,
            status=status,
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
    scheduled_job_id: str | None = None,
    scheduled_job_run_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_plugin_invocation_logs_response(
            action_id=action_id,
            current_store=store(request),
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        ),
        get_trace_id(request),
    )
