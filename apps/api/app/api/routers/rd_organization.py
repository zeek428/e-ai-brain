from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.rd_ai_employees import (
    create_rd_ai_employee_response,
    list_rd_ai_employees_response,
    patch_rd_ai_employee_response,
)
from app.services.rd_executor_profiles import (
    create_rd_executor_profile_response,
    list_rd_executor_profiles_response,
    patch_rd_executor_profile_response,
)
from app.services.rd_role_definitions import (
    create_rd_role_response,
    list_rd_roles_response,
    patch_rd_role_response,
)

router = APIRouter(tags=["rd_organization"])


class RdRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain_app_id: str = "rd_brain"
    code: str
    name: str
    capabilities: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    maximum_risk_level: str = "medium"
    assignable_subject_types: list[str] = Field(
        default_factory=lambda: ["human_user", "ai_employee"]
    )
    status: str = "active"


class RdRolePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain_app_id: str | None = None
    code: str | None = None
    name: str | None = None
    capabilities: list[str] | None = None
    responsibilities: list[str] | None = None
    maximum_risk_level: str | None = None
    assignable_subject_types: list[str] | None = None
    status: str | None = None


class RdAiEmployeeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain_app_id: str = "rd_brain"
    code: str
    name: str
    capability_tags: list[str] = Field(default_factory=list)
    persona_version: int = 1
    persona_json: dict[str, Any] = Field(default_factory=dict)
    work_style_version: int = 1
    work_style_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class RdAiEmployeePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain_app_id: str | None = None
    code: str | None = None
    name: str | None = None
    capability_tags: list[str] | None = None
    persona_version: int | None = None
    persona_json: dict[str, Any] | None = None
    work_style_version: int | None = None
    work_style_json: dict[str, Any] | None = None
    status: str | None = None


class RdExecutorProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain_app_id: str = "rd_brain"
    code: str
    name: str
    executor_type: str
    runner_id: str | None = None
    model_gateway_config_id: str | None = None
    credential_ref: str | None = None
    workspace_capabilities: dict[str, Any] = Field(default_factory=dict)
    max_concurrency: int = 1
    supported_role_codes: list[str] = Field(default_factory=list)
    health_status: str = "unknown"
    status: str = "active"


class RdExecutorProfilePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain_app_id: str | None = None
    code: str | None = None
    name: str | None = None
    executor_type: str | None = None
    runner_id: str | None = None
    model_gateway_config_id: str | None = None
    credential_ref: str | None = None
    workspace_capabilities: dict[str, Any] | None = None
    max_concurrency: int | None = None
    supported_role_codes: list[str] | None = None
    health_status: str | None = None
    status: str | None = None


@router.get("/api/delivery/rd-roles")
def list_rd_roles(
    request: Request,
    brain_app_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_rd_roles_response(
            current_store=store(request), user=user, brain_app_id=brain_app_id, status=status
        ),
        get_trace_id(request),
    )


@router.post("/api/delivery/rd-roles")
def create_rd_role(
    request: Request, payload: RdRoleRequest, user: dict[str, Any] = CurrentUser
) -> dict[str, Any]:
    return envelope(
        create_rd_role_response(
            current_store=store(request), payload=payload.model_dump(), user=user
        ),
        get_trace_id(request),
    )


@router.patch("/api/delivery/rd-roles/{role_id}")
def patch_rd_role(
    role_id: str, request: Request, payload: RdRolePatchRequest, user: dict[str, Any] = CurrentUser
) -> dict[str, Any]:
    return envelope(
        patch_rd_role_response(
            current_store=store(request),
            role_id=role_id,
            payload=payload.model_dump(exclude_unset=True),
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/delivery/rd-ai-employees")
def list_rd_ai_employees(
    request: Request,
    brain_app_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_rd_ai_employees_response(
            current_store=store(request), user=user, brain_app_id=brain_app_id, status=status
        ),
        get_trace_id(request),
    )


@router.post("/api/delivery/rd-ai-employees")
def create_rd_ai_employee(
    request: Request, payload: RdAiEmployeeRequest, user: dict[str, Any] = CurrentUser
) -> dict[str, Any]:
    return envelope(
        create_rd_ai_employee_response(
            current_store=store(request), payload=payload.model_dump(), user=user
        ),
        get_trace_id(request),
    )


@router.patch("/api/delivery/rd-ai-employees/{employee_id}")
def patch_rd_ai_employee(
    employee_id: str,
    request: Request,
    payload: RdAiEmployeePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_rd_ai_employee_response(
            current_store=store(request),
            employee_id=employee_id,
            payload=payload.model_dump(exclude_unset=True),
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/delivery/rd-executor-profiles")
def list_rd_executor_profiles(
    request: Request,
    brain_app_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_rd_executor_profiles_response(
            current_store=store(request), user=user, brain_app_id=brain_app_id, status=status
        ),
        get_trace_id(request),
    )


@router.post("/api/delivery/rd-executor-profiles")
def create_rd_executor_profile(
    request: Request, payload: RdExecutorProfileRequest, user: dict[str, Any] = CurrentUser
) -> dict[str, Any]:
    return envelope(
        create_rd_executor_profile_response(
            current_store=store(request), payload=payload.model_dump(), user=user
        ),
        get_trace_id(request),
    )


@router.patch("/api/delivery/rd-executor-profiles/{profile_id}")
def patch_rd_executor_profile(
    profile_id: str,
    request: Request,
    payload: RdExecutorProfilePatchRequest,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_rd_executor_profile_response(
            current_store=store(request),
            profile_id=profile_id,
            payload=payload.model_dump(exclude_unset=True),
            user=user,
        ),
        get_trace_id(request),
    )
