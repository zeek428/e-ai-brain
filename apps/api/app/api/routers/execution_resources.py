from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.execution_resource_grants import (
    create_execution_resource_grant_response,
    list_execution_resource_grants_response,
    update_execution_resource_grant_response,
)

router = APIRouter()


class ExecutionResourceGrantCreate(BaseModel):
    product_id: str
    environment: str = "prod"
    resource_type: str
    resource_id: str
    target_code: str | None = None


class ExecutionResourceGrantUpdate(BaseModel):
    version: int
    status: str


@router.get("/api/system/execution-resources")
def list_execution_resources(
    request: Request,
    product_id: str | None = None,
    environment: str | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = list_execution_resource_grants_response(
        current_store=store(request),
        environment=environment,
        product_id=product_id,
        resource_type=resource_type,
        status=status,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.post("/api/system/execution-resources")
def create_execution_resource(
    payload: ExecutionResourceGrantCreate,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = create_execution_resource_grant_response(
        current_store=store(request),
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))


@router.put("/api/system/execution-resources/{grant_id}")
def update_execution_resource(
    grant_id: str,
    payload: ExecutionResourceGrantUpdate,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    result = update_execution_resource_grant_response(
        current_store=store(request),
        grant_id=grant_id,
        payload=payload,
        user=user,
    )
    return envelope(result, get_trace_id(request))
