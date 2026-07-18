from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, require_any_permission_or_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.rd_collaboration_migration import (
    begin_cutover,
    build_upgrade_preflight,
    record_cutover_health,
)
from app.services.rd_maintenance_fence import get_rd_maintenance_state, set_rd_maintenance_fence
from app.services.rd_work_item_scheduler import cancel_work_item

router = APIRouter(tags=["rd-collaboration-migration"])


class MaintenanceFenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_schema_version: int | None = Field(default=None, ge=1)
    expected_version: int = Field(gt=0)
    mode: Literal["disabled", "draining"]
    reason: str = Field(min_length=1, max_length=500)


class CutoverLockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["lock"]
    backup_marker: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(gt=0)
    v2_api_version: str = Field(min_length=1, max_length=100)
    v2_graph_version: str = Field(min_length=1, max_length=100)
    v2_worker_version: str = Field(min_length=1, max_length=100)


class CutoverHealthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["record_health"]
    expected_version: int = Field(gt=0)
    health_marker: str = Field(min_length=1, max_length=500)
    smoke_test: dict[str, Any]
    v2_api_version: str = Field(min_length=1, max_length=100)
    v2_graph_version: str = Field(min_length=1, max_length=100)
    v2_worker_version: str = Field(min_length=1, max_length=100)


class DrainCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)
    version: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=255)


def _admin(user: dict[str, Any]) -> None:
    require_any_permission_or_roles(user, {"system.settings.manage"}, {"admin"})


@router.get("/api/system/rd-collaboration-upgrade/preflight")
def upgrade_preflight(request: Request, user: dict[str, Any] = CurrentUser) -> dict[str, Any]:
    _admin(user)
    state = get_rd_maintenance_state(store(request))
    return envelope(
        {"state": state, "report": build_upgrade_preflight(store(request))},
        get_trace_id(request),
    )


@router.post("/api/system/rd-collaboration-upgrade/maintenance-fence")
def maintenance_fence(
    request: Request,
    payload: MaintenanceFenceRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _admin(user)
    return envelope(
        set_rd_maintenance_fence(
            store(request),
            mode=payload.mode,
            actor_id=str(user["id"]),
            expected_version=payload.expected_version,
            reason=payload.reason,
            expected_schema_version=payload.expected_schema_version,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/rd-collaboration-upgrade/drain-cancel/{work_item_id}")
def drain_cancel_work_item(
    work_item_id: str,
    request: Request,
    payload: DrainCancelRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    """Allow an administrator to drain an existing work item, never to start one."""
    _admin(user)
    result = cancel_work_item(
        store(request),
        work_item_id=work_item_id,
        reason=payload.reason,
        actor=user,
        version=payload.version,
        idempotency_key=payload.idempotency_key,
        maintenance_drain_cancel=True,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/system/rd-collaboration-upgrade/cutover")
def cutover(
    request: Request,
    payload: CutoverLockRequest | CutoverHealthRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    _admin(user)
    current_store = store(request)
    if payload.action == "lock":
        result = begin_cutover(
            current_store,
            actor_id=str(user["id"]),
            backup_marker=payload.backup_marker,
            expected_version=payload.expected_version,
            v2_api_version=payload.v2_api_version,
            v2_graph_version=payload.v2_graph_version,
            v2_worker_version=payload.v2_worker_version,
        )
    else:
        result = record_cutover_health(
            current_store,
            actor_id=str(user["id"]),
            expected_version=payload.expected_version,
            health_marker=payload.health_marker,
            smoke_test=payload.smoke_test,
            v2_api_version=payload.v2_api_version,
            v2_graph_version=payload.v2_graph_version,
            v2_worker_version=payload.v2_worker_version,
        )
    return envelope(result, get_trace_id(request))
