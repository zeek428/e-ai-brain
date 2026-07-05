from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, require_permissions, store
from app.core.trace import envelope, get_trace_id
from app.services.system_settings import (
    system_settings_response,
    test_email_delivery_response,
    update_system_settings_response,
)

router = APIRouter(tags=["system_settings"])
SYSTEM_SETTINGS_MANAGE_PERMISSION = "system.settings.manage"


class EmailDeliveryPatchRequest(BaseModel):
    default_from: str | None = None
    enabled: bool | None = None
    reply_to: str | None = None
    sender_email: str | None = None
    smtp_host: str | None = None
    smtp_password: str | None = None
    smtp_port: int | None = None
    smtp_secret_ref: str | None = None
    smtp_tls: str | None = None
    smtp_username: str | None = None


class SystemSettingsPatchRequest(BaseModel):
    admin_email: str | None = None
    email_delivery: EmailDeliveryPatchRequest | None = None
    test_recipient_email: str | None = None


class SystemEmailTestRequest(BaseModel):
    recipient_email: str | None = None


@router.get("/api/system/settings")
def get_system_settings(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {SYSTEM_SETTINGS_MANAGE_PERMISSION})
    return envelope(
        system_settings_response(store(request)),
        get_trace_id(request),
    )


@router.patch("/api/system/settings")
def update_system_settings(
    request: Request,
    payload: SystemSettingsPatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {SYSTEM_SETTINGS_MANAGE_PERMISSION})
    trace_id = get_trace_id(request)
    actor_id = str(user.get("id") or user.get("username") or "unknown")
    return envelope(
        update_system_settings_response(
            store(request),
            actor_id=actor_id,
            admin_email=payload.admin_email,
            admin_email_provided="admin_email" in payload.model_fields_set,
            email_delivery=(
                payload.email_delivery.model_dump(exclude_unset=True)
                if payload.email_delivery is not None
                else None
            ),
            email_delivery_provided="email_delivery" in payload.model_fields_set,
            test_recipient_email=payload.test_recipient_email,
            test_recipient_email_provided="test_recipient_email" in payload.model_fields_set,
            trace_id=trace_id,
        ),
        trace_id,
    )


@router.post("/api/system/settings/email/test")
def test_email_delivery_settings(
    request: Request,
    payload: SystemEmailTestRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_permissions(user, {SYSTEM_SETTINGS_MANAGE_PERMISSION})
    trace_id = get_trace_id(request)
    actor_id = str(user.get("id") or user.get("username") or "unknown")
    return envelope(
        test_email_delivery_response(
            store(request),
            actor_id=actor_id,
            recipient_email=payload.recipient_email,
        ),
        trace_id,
    )
