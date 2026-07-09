from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, require_any_permission, require_permissions, store
from app.core.config import get_settings
from app.core.trace import envelope, get_trace_id
from app.services.platform_status import health_payload, long_memory_status_payload
from app.services.system_health import (
    save_system_alert_subscription_response,
    system_health_report,
    update_system_alert_incident_response,
)

settings = get_settings()
router = APIRouter(tags=["platform"])


class SystemAlertIncidentPatchRequest(BaseModel):
    status: str | None = None
    owner: str | None = None
    close_reason: str | None = None
    postmortem: str | None = None


class SystemAlertSubscriptionRequest(BaseModel):
    channel: str
    target: str
    severity_min: str = "medium"
    scope: str | None = "global"
    enabled: bool = True


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    return health_payload(
        current_store=store(request),
        settings=settings,
        trace_id=get_trace_id(request),
    )


@router.get("/api/long-memory/status")
def get_long_memory_status(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(long_memory_status_payload(settings), get_trace_id(request))


@router.get("/api/system/health")
def get_system_health(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission(
        user,
        {"system.health.read", "system.settings.manage", "system.roles.read"},
    )
    trace_id = get_trace_id(request)
    return envelope(
        system_health_report(
            current_store=store(request),
            request=request,
            settings=settings,
            trace_id=trace_id,
            user=user,
        ),
        trace_id,
    )


@router.patch("/api/system/alerts/{alert_id}")
def patch_system_alert_incident(
    alert_id: str,
    request: Request,
    payload: SystemAlertIncidentPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.alerts.manage"})
    return update_system_alert_incident_response(
        alert_id=alert_id,
        close_reason=payload.close_reason,
        current_store=store(request),
        owner=payload.owner,
        postmortem=payload.postmortem,
        status=payload.status,
        trace_id=get_trace_id(request),
        user=user,
    )


@router.post("/api/system/alerts/subscriptions")
def create_system_alert_subscription(
    request: Request,
    payload: SystemAlertSubscriptionRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.alerts.manage"})
    return save_system_alert_subscription_response(
        channel=payload.channel,
        current_store=store(request),
        enabled=payload.enabled,
        scope=payload.scope,
        severity_min=payload.severity_min,
        target=payload.target,
        trace_id=get_trace_id(request),
        user=user,
    )
