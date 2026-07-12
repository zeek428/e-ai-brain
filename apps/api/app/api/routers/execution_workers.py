from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, require_any_permission_or_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.execution_worker_observability import execution_operations_overview

router = APIRouter(tags=["execution-workers"])


@router.get("/api/system/execution-operations-overview")
def get_execution_operations_overview(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"system.settings.manage"}, {"admin"})
    return envelope(execution_operations_overview(store(request)), get_trace_id(request))
