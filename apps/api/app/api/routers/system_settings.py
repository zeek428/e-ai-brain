from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, require_permissions, store
from app.core.trace import envelope, get_trace_id
from app.services.system_settings import (
    system_settings_response,
    update_system_settings_response,
)

router = APIRouter(tags=["system_settings"])
SYSTEM_SETTINGS_MANAGE_PERMISSION = "system.settings.manage"


class SystemSettingsPatchRequest(BaseModel):
    admin_email: str | None = None


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
            trace_id=trace_id,
        ),
        trace_id,
    )
