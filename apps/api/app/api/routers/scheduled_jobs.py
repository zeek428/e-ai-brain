from __future__ import annotations

from time import perf_counter
from typing import Annotated, Any

from fastapi import APIRouter, Body, Query, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.scheduled_job_catalog import list_scheduled_job_catalog_response
from app.services.scheduled_job_observability import scheduled_job_run_observability_response
from app.services.scheduled_job_templates import list_scheduled_job_templates_response
from app.services.scheduled_jobs import (
    cancel_scheduled_job_run_response,
    create_ai_agent_response,
    create_ai_skill_package_response,
    create_ai_skill_response,
    create_scheduled_job_response,
    delete_scheduled_job_response,
    dry_run_scheduled_job_response,
    list_ai_agents_response,
    list_ai_skills_response,
    list_scheduled_job_runs_response,
    list_scheduled_jobs_response,
    patch_ai_agent_response,
    patch_ai_skill_response,
    patch_scheduled_job_response,
    run_scheduled_job_response,
    scheduled_job_template_from_run_response,
)

router = APIRouter(tags=["scheduled-jobs"])


class AiSkillRequest(BaseModel):
    allowed_tools: list[str] = Field(default_factory=list)
    code: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    name: str
    output_schema: dict[str, Any] = Field(default_factory=dict)
    prompt_template: str
    required_context: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    risk_level: str = "medium"
    status: str = "active"
    version: str = "1.0.0"


class AiSkillPatchRequest(BaseModel):
    allowed_tools: list[str] | None = None
    code: str | None = None
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    name: str | None = None
    output_schema: dict[str, Any] | None = None
    prompt_template: str | None = None
    required_context: list[str] | None = None
    requires_human_review: bool | None = None
    risk_level: str | None = None
    status: str | None = None
    version: str | None = None


class AiAgentRequest(BaseModel):
    brain_app_id: str = "rd_brain"
    code: str
    default_skill_ids: list[str] = Field(default_factory=list)
    description: str | None = None
    execution_policy: dict[str, Any] = Field(default_factory=dict)
    model_gateway_config_id: str | None = None
    name: str
    status: str = "active"
    system_prompt: str
    tool_policy: dict[str, Any] = Field(default_factory=dict)


class AiAgentPatchRequest(BaseModel):
    brain_app_id: str | None = None
    code: str | None = None
    default_skill_ids: list[str] | None = None
    description: str | None = None
    execution_policy: dict[str, Any] | None = None
    model_gateway_config_id: str | None = None
    name: str | None = None
    status: str | None = None
    system_prompt: str | None = None
    tool_policy: dict[str, Any] | None = None


class ScheduledJobRequest(BaseModel):
    agent_id: str | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)
    cron_expression: str | None = None
    enabled: bool = True
    execution_mode: str = "deterministic"
    interval_seconds: int | None = None
    job_type: str
    knowledge_document_ids: list[str] = Field(default_factory=list)
    lock_ttl_seconds: int = 900
    max_retry_count: int = 0
    model_gateway_config_id: str | None = None
    name: str
    plugin_action_id: str | None = None
    plugin_action_ids: list[str] = Field(default_factory=list)
    plugin_connection_id: str | None = None
    plugin_connection_ids: list[str] = Field(default_factory=list)
    plugin_input_mapping: dict[str, Any] = Field(default_factory=dict)
    plugin_output_mapping: dict[str, Any] = Field(default_factory=dict)
    product_id: str | None = None
    result_actions: list[dict[str, Any]] = Field(default_factory=list)
    schedule_type: str = "manual"
    skill_ids: list[str] = Field(default_factory=list)
    source_system: str = "ai-brain"
    timeout_seconds: int = 600
    timezone: str = "Asia/Shanghai"


class ScheduledJobPatchRequest(BaseModel):
    agent_id: str | None = None
    config_json: dict[str, Any] | None = None
    cron_expression: str | None = None
    enabled: bool | None = None
    execution_mode: str | None = None
    interval_seconds: int | None = None
    job_type: str | None = None
    knowledge_document_ids: list[str] | None = None
    lock_ttl_seconds: int | None = None
    max_retry_count: int | None = None
    model_gateway_config_id: str | None = None
    name: str | None = None
    plugin_action_id: str | None = None
    plugin_action_ids: list[str] | None = None
    plugin_connection_id: str | None = None
    plugin_connection_ids: list[str] | None = None
    plugin_input_mapping: dict[str, Any] | None = None
    plugin_output_mapping: dict[str, Any] | None = None
    product_id: str | None = None
    result_actions: list[dict[str, Any]] | None = None
    schedule_type: str | None = None
    skill_ids: list[str] | None = None
    source_system: str | None = None
    timeout_seconds: int | None = None
    timezone: str | None = None


class ScheduledJobRunRequest(BaseModel):
    source_run_id: str | None = None
    trigger_type: str = "manual"


@router.get("/api/system/ai-skills")
def list_ai_skills(
    request: Request,
    code: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_ai_skills_response(code=code, current_store=store(request), status=status),
        get_trace_id(request),
    )


@router.post("/api/system/ai-skills")
def create_ai_skill(
    payload: AiSkillRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_ai_skill_response(current_store=store(request), payload=payload, user=user),
        get_trace_id(request),
    )


@router.post("/api/system/ai-skills/upload")
def upload_ai_skill_package(
    request: Request,
    package_bytes: bytes = Body(..., media_type="application/zip"),
    code: str = Query(...),
    name: str = Query(...),
    requires_human_review: bool = Query(False),
    risk_level: str = Query("medium"),
    status: str = Query("active"),
    user: dict[str, Any] = CurrentUser,
    version: str = Query("1.0.0"),
) -> dict[str, Any]:
    return envelope(
        create_ai_skill_package_response(
            code=code,
            current_store=store(request),
            name=name,
            package_bytes=package_bytes,
            requires_human_review=requires_human_review,
            risk_level=risk_level,
            status=status,
            user=user,
            version=version,
        ),
        get_trace_id(request),
    )


@router.patch("/api/system/ai-skills/{skill_id}")
def patch_ai_skill(
    payload: AiSkillPatchRequest,
    request: Request,
    skill_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_ai_skill_response(
            current_store=store(request),
            payload=payload,
            skill_id=skill_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/ai-agents")
def list_ai_agents(
    request: Request,
    brain_app_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_ai_agents_response(
            brain_app_id=brain_app_id,
            current_store=store(request),
            status=status,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/ai-agents")
def create_ai_agent(
    payload: AiAgentRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_ai_agent_response(current_store=store(request), payload=payload, user=user),
        get_trace_id(request),
    )


@router.patch("/api/system/ai-agents/{agent_id}")
def patch_ai_agent(
    agent_id: str,
    payload: AiAgentPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_ai_agent_response(
            agent_id=agent_id,
            current_store=store(request),
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/scheduled-jobs")
def list_scheduled_jobs(
    request: Request,
    enabled: bool | None = None,
    job_type: str | None = None,
    keyword: str | None = None,
    name: str | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    product_id: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    source_system: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_scheduled_jobs_response(
            current_store=store(request),
            enabled=enabled,
            job_type=job_type,
            keyword=keyword,
            name=name,
            page=page,
            page_size=page_size,
            product_id=product_id,
            sort_by=sort_by,
            sort_order=sort_order,
            source_system=source_system,
            started_at=perf_counter(),
            status=status,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/scheduled-job-templates")
def list_scheduled_job_templates(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_scheduled_job_templates_response(current_store=store(request), user=user),
        get_trace_id(request),
    )


@router.get("/api/system/scheduled-job-catalog")
def list_scheduled_job_catalog(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_scheduled_job_catalog_response(user=user),
        get_trace_id(request),
    )


@router.post("/api/system/scheduled-jobs")
def create_scheduled_job(
    payload: ScheduledJobRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        create_scheduled_job_response(current_store=store(request), payload=payload, user=user),
        get_trace_id(request),
    )


@router.post("/api/system/scheduled-jobs/dry-run")
def dry_run_scheduled_job(
    payload: ScheduledJobRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        dry_run_scheduled_job_response(current_store=store(request), payload=payload, user=user),
        get_trace_id(request),
    )


@router.patch("/api/system/scheduled-jobs/{job_id}")
def patch_scheduled_job(
    job_id: str,
    payload: ScheduledJobPatchRequest,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        patch_scheduled_job_response(
            current_store=store(request),
            job_id=job_id,
            payload=payload,
            user=user,
        ),
        get_trace_id(request),
    )


@router.delete("/api/system/scheduled-jobs/{job_id}")
def delete_scheduled_job(
    job_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        delete_scheduled_job_response(
            current_store=store(request),
            job_id=job_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/scheduled-jobs/{job_id}/run")
def run_scheduled_job(
    job_id: str,
    request: Request,
    payload: ScheduledJobRunRequest | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        run_scheduled_job_response(
            current_store=store(request),
            job_id=job_id,
            source_run_id=(payload.source_run_id if payload else None),
            trigger_type=(payload.trigger_type if payload else "manual"),
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/scheduled-job-runs")
def list_scheduled_job_runs(
    request: Request,
    run_id: Annotated[list[str] | None, Query()] = None,
    scheduled_job_id: str | None = None,
    status: str | None = None,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        list_scheduled_job_runs_response(
            current_store=store(request),
            run_ids=run_id,
            scheduled_job_id=scheduled_job_id,
            status=status,
            user=user,
        ),
        get_trace_id(request),
    )


@router.get("/api/system/scheduled-job-runs/observability")
def scheduled_job_run_observability(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        scheduled_job_run_observability_response(current_store=store(request), user=user),
        get_trace_id(request),
    )


@router.post("/api/system/scheduled-job-runs/{run_id}/template")
def scheduled_job_run_template(
    request: Request,
    run_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        scheduled_job_template_from_run_response(
            current_store=store(request),
            run_id=run_id,
            user=user,
        ),
        get_trace_id(request),
    )


@router.post("/api/system/scheduled-job-runs/{run_id}/cancel")
def cancel_scheduled_job_run(
    request: Request,
    run_id: str,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        cancel_scheduled_job_run_response(
            current_store=store(request),
            run_id=run_id,
            user=user,
        ),
        get_trace_id(request),
    )
