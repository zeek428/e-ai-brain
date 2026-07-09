from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, require_any_permission, require_permissions, store
from app.core.config import get_settings
from app.core.trace import envelope, get_trace_id
from app.services.platform_status import health_payload, long_memory_status_payload
from app.services.system_health import (
    admin_weekly_report_response,
    list_system_alert_rules_response,
    save_system_alert_rule_response,
    save_system_alert_subscription_response,
    system_health_report,
    update_system_alert_incident_response,
    update_system_alert_rule_response,
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


class SystemAlertRuleRequest(BaseModel):
    name: str | None = None
    source: str | None = "system_check"
    component: str | None = None
    severity_min: str = "medium"
    owner: str | None = None
    notification_scope: str | None = "global"
    condition_json: dict[str, Any] | None = None
    enabled: bool = True


class SystemAlertRulePatchRequest(BaseModel):
    name: str | None = None
    source: str | None = None
    component: str | None = None
    severity_min: str | None = None
    owner: str | None = None
    notification_scope: str | None = None
    condition_json: dict[str, Any] | None = None
    enabled: bool | None = None


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


@router.get("/api/system/alerts/rules")
def list_system_alert_rules(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.alerts.manage"})
    return list_system_alert_rules_response(
        current_store=store(request),
        trace_id=get_trace_id(request),
    )


@router.post("/api/system/alerts/rules")
def create_system_alert_rule(
    request: Request,
    payload: SystemAlertRuleRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.alerts.manage"})
    return save_system_alert_rule_response(
        condition_json=payload.condition_json,
        component=payload.component,
        current_store=store(request),
        enabled=payload.enabled,
        name=payload.name,
        notification_scope=payload.notification_scope,
        owner=payload.owner,
        severity_min=payload.severity_min,
        source=payload.source,
        trace_id=get_trace_id(request),
        user=user,
    )


@router.patch("/api/system/alerts/rules/{rule_id}")
def patch_system_alert_rule(
    rule_id: str,
    request: Request,
    payload: SystemAlertRulePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {"system.alerts.manage"})
    return update_system_alert_rule_response(
        condition_json=payload.condition_json,
        component=payload.component,
        current_store=store(request),
        enabled=payload.enabled,
        name=payload.name,
        notification_scope=payload.notification_scope,
        owner=payload.owner,
        rule_id=rule_id,
        severity_min=payload.severity_min,
        source=payload.source,
        trace_id=get_trace_id(request),
        user=user,
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


@router.get("/api/system/admin-weekly-report")
def get_admin_weekly_report(
    request: Request,
    days: int = 7,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission(user, {"system.alerts.manage", "audit.read", "system.settings.manage"})
    trace_id = get_trace_id(request)
    return admin_weekly_report_response(
        current_store=store(request),
        days=days,
        request=request,
        settings=settings,
        trace_id=trace_id,
        user=user,
    )
