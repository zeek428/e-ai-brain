from __future__ import annotations

from app.api.deps import api_error
from app.services.scheduled_job_catalog import (
    AI_REQUIRED_SCHEDULED_JOB_TYPES,
    scheduled_job_type_allows_create,
    scheduled_job_type_definition,
    scheduled_job_type_is_runnable,
)


def scheduled_job_uses_ai_processing_config(job_type: str, execution_mode: str) -> bool:
    return (
        execution_mode in {"ai_assisted", "ai_generated"}
        or job_type in AI_REQUIRED_SCHEDULED_JOB_TYPES
    )


def ensure_scheduled_job_type_available_for_create(job_type: str) -> None:
    if scheduled_job_type_allows_create(job_type):
        return
    definition = scheduled_job_type_definition(job_type) or {}
    raise api_error(
        400,
        "SCHEDULED_JOB_TYPE_UNAVAILABLE",
        str(
            definition.get("unavailable_reason")
            or "Scheduled job type is not available for manual creation",
        ),
    )


def ensure_scheduled_job_type_runnable(job_type: str) -> None:
    if scheduled_job_type_is_runnable(job_type):
        return
    definition = scheduled_job_type_definition(job_type) or {}
    raise api_error(
        400,
        "SCHEDULED_JOB_TYPE_NOT_RUNNABLE",
        str(
            definition.get("unavailable_reason")
            or "Scheduled job type does not have a completed runtime handler",
        ),
    )
