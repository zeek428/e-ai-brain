from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, require_any_permission_or_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.execution_worker_observability import execution_operations_overview
from app.services.operational_deployments import reconcile_platform_external_operations

router = APIRouter(tags=["execution-workers"])


@router.get("/api/system/execution-operations-overview")
def get_execution_operations_overview(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"system.settings.manage"}, {"admin"})
    return envelope(execution_operations_overview(store(request)), get_trace_id(request))


@router.post("/api/system/execution-operations/reconcile")
def reconcile_execution_operations(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"system.settings.manage"}, {"admin"})
    outcomes = reconcile_platform_external_operations(
        current_store=store(request),
        actor_id=user["id"],
    )
    return envelope({"items": outcomes, "total": len(outcomes)}, get_trace_id(request))
