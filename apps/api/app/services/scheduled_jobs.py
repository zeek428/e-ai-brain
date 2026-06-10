from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.deps import api_error, require_roles
from app.services.dynamic_parameters import (
    dynamic_time_parameters,
    resolve_dynamic_parameter_value,
)
from app.services.iteration_planning import create_iteration_suggestions_response
from app.services.operational_records import record_audit_event, save_single_repository_record
from app.services.plugins import (
    ensure_active_plugin_action,
    invoke_plugin_action_response,
    json_path_value,
    records_imported_from_mapping,
    resolve_plugin_snapshot,
)
from app.services.skill_packages import load_skill_package_snapshot, store_skill_package
from app.services.user_feedback import (
    USER_FEEDBACK_SENTIMENTS,
    USER_FEEDBACK_TYPES,
    create_user_feedback_response,
)

AI_SKILL_STATUSES = {"active", "draft", "disabled"}
AI_AGENT_STATUSES = {"active", "disabled"}
SCHEDULED_JOB_TYPES = {
    "dashboard_snapshot_refresh",
    "gitlab_daily_code_metric_collect",
    "iteration_plan_suggestion_generate",
    "jenkins_release_collect",
    "lifecycle_context_refresh",
    "online_log_ai_analysis",
    "online_log_metric_collect",
    "pending_attribution_retry",
    "plugin_action_invoke",
    "user_feedback_collect",
    "user_feedback_insight_extract",
    "user_usage_metric_collect",
}
SCHEDULED_JOB_EXECUTION_MODES = {"ai_assisted", "ai_generated", "deterministic"}
SCHEDULED_JOB_SCHEDULE_TYPES = {"cron", "interval", "manual"}
SCHEDULED_JOB_RUN_STATUSES = {"cancelled", "failed", "queued", "running", "skipped", "succeeded"}
SCHEDULED_JOB_RUN_TERMINAL_STATUSES = {"cancelled", "failed", "skipped", "succeeded"}


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is None or value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def require_admin(user: dict[str, Any]) -> None:
    require_roles(user, {"admin"})


def scheduled_job_timezone(job: dict[str, Any]) -> ZoneInfo:
    timezone_name = str(job.get("timezone") or "UTC")
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported timezone: {timezone_name}") from None


def resolve_plugin_input_mapping(
    mapping: dict[str, Any],
    job: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    return resolve_dynamic_parameter_value(
        mapping,
        dynamic_time_parameters(now=now, timezone=scheduled_job_timezone(job)),
        now=now,
        timezone=scheduled_job_timezone(job),
    )


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def scheduled_jobs_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    required_methods = (
        "list_ai_agents",
        "list_ai_skills",
        "list_scheduled_job_runs",
        "list_scheduled_jobs",
    )
    if all(callable(getattr(repository, method_name, None)) for method_name in required_methods):
        return repository
    return None


def replace_collection(
    current_store: Any,
    collection_name: str,
    items: list[dict[str, Any]],
) -> None:
    setattr(
        current_store,
        collection_name,
        {str(item["id"]): dict(item) for item in items if item.get("id") is not None},
    )


def sync_ai_skill_store(
    current_store: Any,
    *,
    code: str | None = None,
    status: str | None = None,
) -> None:
    repository = scheduled_jobs_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "ai_skills",
        repository.list_ai_skills(code=code, status=status),
    )


def sync_ai_agent_store(
    current_store: Any,
    *,
    brain_app_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = scheduled_jobs_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "ai_agents",
        repository.list_ai_agents(brain_app_id=brain_app_id, status=status),
    )


def sync_scheduled_job_store(
    current_store: Any,
    *,
    enabled: bool | None = None,
    job_type: str | None = None,
    status: str | None = None,
) -> None:
    repository = scheduled_jobs_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "scheduled_jobs",
        repository.list_scheduled_jobs(enabled=enabled, job_type=job_type, status=status),
    )


def sync_scheduled_job_run_store(
    current_store: Any,
    *,
    scheduled_job_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = scheduled_jobs_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "scheduled_job_runs",
        repository.list_scheduled_job_runs(scheduled_job_id=scheduled_job_id, status=status),
    )


def sync_reference_store(current_store: Any) -> None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return
    list_products = getattr(repository, "list_products", None)
    if callable(list_products):
        replace_collection(current_store, "products", list_products(active_only=False))
    list_model_gateway_configs = getattr(repository, "list_model_gateway_configs", None)
    if callable(list_model_gateway_configs):
        replace_collection(
            current_store,
            "model_gateway_configs",
            list_model_gateway_configs(),
        )


def persist_record(
    current_store: Any,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    save_single_repository_record(
        current_store,
        method_name,
        record,
        audit_event=audit_event,
    )


def snapshot(current_store: Any, value: Any) -> Any:
    snapshot_fn = getattr(current_store, "snapshot", None)
    if callable(snapshot_fn) and isinstance(value, dict):
        return snapshot_fn(value)
    if isinstance(value, dict):
        return {key: snapshot(current_store, item) for key, item in value.items()}
    if isinstance(value, list):
        return [snapshot(current_store, item) for item in value]
    return value


def public_skill(skill: dict[str, Any]) -> dict[str, Any]:
    return dict(skill)


def public_agent(agent: dict[str, Any]) -> dict[str, Any]:
    return dict(agent)


def list_ai_skills_response(
    *,
    code: str | None,
    current_store: Any,
    status: str | None,
) -> dict[str, Any]:
    if status is not None:
        ensure_enum(status, AI_SKILL_STATUSES, "status")
    sync_ai_skill_store(current_store, code=code, status=status)
    items = []
    for skill in current_store.ai_skills.values():
        if code is not None and skill.get("code") != code:
            continue
        if status is not None and skill.get("status") != status:
            continue
        items.append(public_skill(skill))
    items.sort(key=lambda item: (item.get("code") or "", item.get("version") or "", item["id"]))
    return {"items": items, "total": len(items)}


def create_ai_skill_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    ensure_enum(payload.status, AI_SKILL_STATUSES, "status")
    now = datetime.now(UTC).isoformat()
    skill_id = current_store.new_id("skill")
    skill = {
        "allowed_tools": payload.allowed_tools,
        "code": ensure_non_blank(payload.code, "code"),
        "created_at": now,
        "created_by": user["id"],
        "description": payload.description,
        "id": skill_id,
        "input_schema": payload.input_schema,
        "name": ensure_non_blank(payload.name, "name"),
        "output_schema": payload.output_schema,
        "manifest": {},
        "package_checksum": None,
        "package_entry": None,
        "package_files": [],
        "package_size_bytes": 0,
        "package_uri": None,
        "prompt_template": ensure_non_blank(payload.prompt_template, "prompt_template"),
        "required_context": payload.required_context,
        "requires_human_review": payload.requires_human_review,
        "risk_level": payload.risk_level,
        "source_type": "inline",
        "status": payload.status,
        "updated_at": now,
        "version": payload.version,
    }
    current_store.ai_skills[skill_id] = skill
    audit_event = record_audit_event(
        current_store,
        event_type="ai_skill.created",
        actor_id=user["id"],
        subject_type="ai_skill",
        subject_id=skill_id,
        payload={"code": skill["code"], "status": skill["status"]},
    )
    persist_record(
        current_store,
        "save_ai_skill_record",
        skill,
        audit_event=audit_event,
    )
    return public_skill(skill)


def create_ai_skill_package_response(
    *,
    code: str,
    current_store: Any,
    name: str,
    package_bytes: bytes,
    requires_human_review: bool,
    risk_level: str,
    status: str,
    user: dict[str, Any],
    version: str,
) -> dict[str, Any]:
    require_admin(user)
    ensure_enum(status, AI_SKILL_STATUSES, "status")
    now = datetime.now(UTC).isoformat()
    skill_code = ensure_non_blank(code, "code")
    skill_version = ensure_non_blank(version, "version")
    skill_id = current_store.new_id("skill")
    stored_package = store_skill_package(
        package_bytes=package_bytes,
        skill_code=skill_code,
        skill_id=skill_id,
        version=skill_version,
    )
    manifest = dict(stored_package.manifest)
    skill_name = ensure_non_blank(str(manifest.get("name") or name), "name")
    skill = {
        "allowed_tools": list(manifest.get("allowed_tools") or []),
        "code": str(manifest.get("code") or skill_code),
        "created_at": now,
        "created_by": user["id"],
        "description": manifest.get("description"),
        "id": skill_id,
        "input_schema": {},
        "manifest": manifest,
        "name": skill_name,
        "output_schema": {},
        "package_checksum": stored_package.checksum,
        "package_entry": stored_package.entry,
        "package_files": stored_package.files,
        "package_size_bytes": stored_package.size_bytes,
        "package_uri": stored_package.package_uri,
        "prompt_template": stored_package.entry_content,
        "required_context": list(manifest.get("required_context") or []),
        "requires_human_review": bool(
            manifest.get("requires_human_review", requires_human_review),
        ),
        "risk_level": str(manifest.get("risk_level") or risk_level),
        "source_type": "package",
        "status": status,
        "updated_at": now,
        "version": str(manifest.get("version") or skill_version),
    }
    current_store.ai_skills[skill_id] = skill
    audit_event = record_audit_event(
        current_store,
        event_type="ai_skill.package_uploaded",
        actor_id=user["id"],
        subject_type="ai_skill",
        subject_id=skill_id,
        payload={
            "checksum": skill["package_checksum"],
            "code": skill["code"],
            "file_count": len(skill["package_files"]),
            "status": skill["status"],
        },
    )
    persist_record(
        current_store,
        "save_ai_skill_record",
        skill,
        audit_event=audit_event,
    )
    return public_skill(skill)


def patch_ai_skill_response(
    *,
    current_store: Any,
    payload: Any,
    skill_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_ai_skill_store(current_store)
    skill = current_store.ai_skills.get(skill_id)
    if skill is None:
        raise api_error(404, "NOT_FOUND", "AI skill not found")
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates:
        ensure_enum(updates["status"], AI_SKILL_STATUSES, "status")
    for key in ("code", "name", "prompt_template"):
        if key in updates:
            updates[key] = ensure_non_blank(updates[key], key)
    skill = {**skill, **updates, "updated_at": datetime.now(UTC).isoformat()}
    current_store.ai_skills[skill_id] = skill
    audit_event = record_audit_event(
        current_store,
        event_type="ai_skill.updated",
        actor_id=user["id"],
        subject_type="ai_skill",
        subject_id=skill_id,
        payload={"code": skill["code"], "status": skill["status"]},
    )
    persist_record(
        current_store,
        "save_ai_skill_record",
        skill,
        audit_event=audit_event,
    )
    return public_skill(skill)


def list_ai_agents_response(
    *,
    brain_app_id: str | None,
    current_store: Any,
    status: str | None,
) -> dict[str, Any]:
    if status is not None:
        ensure_enum(status, AI_AGENT_STATUSES, "status")
    sync_ai_agent_store(current_store, brain_app_id=brain_app_id, status=status)
    items = []
    for agent in current_store.ai_agents.values():
        if brain_app_id is not None and agent.get("brain_app_id") != brain_app_id:
            continue
        if status is not None and agent.get("status") != status:
            continue
        items.append(public_agent(agent))
    items.sort(
        key=lambda item: (item.get("brain_app_id") or "", item.get("code") or "", item["id"]),
    )
    return {"items": items, "total": len(items)}


def ensure_active_model_gateway(current_store: Any, config_id: str | None) -> str | None:
    if config_id is None:
        return None
    sync_reference_store(current_store)
    config = current_store.model_gateway_configs.get(config_id)
    if config is None:
        raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    if config.get("status") != "active":
        raise api_error(400, "MODEL_GATEWAY_CONFIG_INACTIVE", "Model gateway config is inactive")
    return config_id


def ensure_active_skills(current_store: Any, skill_ids: list[str]) -> list[str]:
    sync_ai_skill_store(current_store)
    for skill_id in skill_ids:
        skill = current_store.ai_skills.get(skill_id)
        if skill is None:
            raise api_error(404, "NOT_FOUND", "AI skill not found")
        if skill.get("status") != "active":
            raise api_error(400, "AI_SKILL_INACTIVE", "AI skill is inactive")
    return skill_ids


def create_ai_agent_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    ensure_enum(payload.status, AI_AGENT_STATUSES, "status")
    ensure_active_model_gateway(current_store, payload.model_gateway_config_id)
    ensure_active_skills(current_store, payload.default_skill_ids)
    now = datetime.now(UTC).isoformat()
    agent_id = current_store.new_id("agent")
    agent = {
        "brain_app_id": ensure_non_blank(payload.brain_app_id, "brain_app_id"),
        "code": ensure_non_blank(payload.code, "code"),
        "created_at": now,
        "created_by": user["id"],
        "default_skill_ids": list(payload.default_skill_ids),
        "description": payload.description,
        "execution_policy": payload.execution_policy,
        "id": agent_id,
        "model_gateway_config_id": payload.model_gateway_config_id,
        "name": ensure_non_blank(payload.name, "name"),
        "status": payload.status,
        "system_prompt": ensure_non_blank(payload.system_prompt, "system_prompt"),
        "tool_policy": payload.tool_policy,
        "updated_at": now,
    }
    current_store.ai_agents[agent_id] = agent
    audit_event = record_audit_event(
        current_store,
        event_type="ai_agent.created",
        actor_id=user["id"],
        subject_type="ai_agent",
        subject_id=agent_id,
        payload={"code": agent["code"], "status": agent["status"]},
    )
    persist_record(
        current_store,
        "save_ai_agent_record",
        agent,
        audit_event=audit_event,
    )
    return public_agent(agent)


def patch_ai_agent_response(
    *,
    agent_id: str,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_ai_agent_store(current_store)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    agent = current_store.ai_agents.get(agent_id)
    if agent is None:
        raise api_error(404, "NOT_FOUND", "AI agent not found")
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates:
        ensure_enum(updates["status"], AI_AGENT_STATUSES, "status")
    if "model_gateway_config_id" in updates:
        ensure_active_model_gateway(current_store, updates["model_gateway_config_id"])
    if "default_skill_ids" in updates:
        ensure_active_skills(current_store, updates["default_skill_ids"])
    for key in ("brain_app_id", "code", "name", "system_prompt"):
        if key in updates:
            updates[key] = ensure_non_blank(updates[key], key)
    agent = {**agent, **updates, "updated_at": datetime.now(UTC).isoformat()}
    current_store.ai_agents[agent_id] = agent
    audit_event = record_audit_event(
        current_store,
        event_type="ai_agent.updated",
        actor_id=user["id"],
        subject_type="ai_agent",
        subject_id=agent_id,
        payload={"code": agent["code"], "status": agent["status"]},
    )
    persist_record(
        current_store,
        "save_ai_agent_record",
        agent,
        audit_event=audit_event,
    )
    return public_agent(agent)


def validate_product(current_store: Any, product_id: str | None) -> None:
    if product_id is None:
        return
    sync_reference_store(current_store)
    product = current_store.products.get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product.get("status") != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")


def next_run_at(payload: Any) -> str | None:
    now = datetime.now(UTC)
    if payload.schedule_type == "manual":
        return None
    if payload.schedule_type == "interval":
        if payload.interval_seconds is None or payload.interval_seconds <= 0:
            raise api_error(400, "VALIDATION_ERROR", "interval_seconds is required")
        return (now + timedelta(seconds=payload.interval_seconds)).isoformat()
    if not payload.cron_expression:
        raise api_error(400, "VALIDATION_ERROR", "cron_expression is required")
    return now.isoformat()


def validate_job_refs(current_store: Any, payload: Any) -> tuple[str | None, list[str], str | None]:
    ensure_enum(payload.job_type, SCHEDULED_JOB_TYPES, "job_type")
    ensure_enum(payload.execution_mode, SCHEDULED_JOB_EXECUTION_MODES, "execution_mode")
    ensure_enum(payload.schedule_type, SCHEDULED_JOB_SCHEDULE_TYPES, "schedule_type")
    sync_ai_agent_store(current_store)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    validate_product(current_store, payload.product_id)
    agent_id = payload.agent_id
    skill_ids = list(payload.skill_ids)
    model_gateway_config_id = payload.model_gateway_config_id
    plugin_backed_ai_job = (
        payload.job_type == "user_feedback_insight_extract"
        and getattr(payload, "plugin_action_id", None) is not None
    )
    if plugin_backed_ai_job and model_gateway_config_id is not None:
        model_gateway_config_id = ensure_active_model_gateway(
            current_store,
            model_gateway_config_id,
        )
    if payload.execution_mode in {"ai_assisted", "ai_generated"} and not plugin_backed_ai_job:
        if agent_id is None:
            raise api_error(400, "AI_AGENT_REQUIRED", "AI job requires agent_id")
        agent = current_store.ai_agents.get(agent_id)
        if agent is None:
            raise api_error(404, "NOT_FOUND", "AI agent not found")
        if agent.get("status") != "active":
            raise api_error(400, "AI_AGENT_INACTIVE", "AI agent is inactive")
        if not skill_ids:
            skill_ids = list(agent.get("default_skill_ids") or [])
        ensure_active_skills(current_store, skill_ids)
        model_gateway_config_id = ensure_active_model_gateway(
            current_store,
            model_gateway_config_id or agent.get("model_gateway_config_id"),
        )
    return agent_id, skill_ids, model_gateway_config_id


def validate_plugin_refs(current_store: Any, payload: Any) -> tuple[str | None, str | None]:
    action_id = getattr(payload, "plugin_action_id", None)
    connection_id = getattr(payload, "plugin_connection_id", None)
    if action_id is None:
        if connection_id is not None:
            raise api_error(
                400,
                "PLUGIN_ACTION_REQUIRED",
                "plugin_connection_id requires plugin_action_id",
            )
        if getattr(payload, "job_type", None) == "user_feedback_insight_extract":
            raise api_error(
                400,
                "PLUGIN_ACTION_REQUIRED",
                "user_feedback_insight_extract requires plugin_action_id",
            )
        return None, None
    _, connection, _ = ensure_active_plugin_action(
        current_store,
        action_id,
        connection_id=connection_id,
    )
    return action_id, connection["id"]


def list_scheduled_jobs_response(
    *,
    current_store: Any,
    enabled: bool | None,
    job_type: str | None,
    status: str | None,
) -> dict[str, Any]:
    if job_type is not None:
        ensure_enum(job_type, SCHEDULED_JOB_TYPES, "job_type")
    sync_scheduled_job_store(
        current_store,
        enabled=enabled,
        job_type=job_type,
        status=status,
    )
    items = []
    for job in current_store.scheduled_jobs.values():
        if enabled is not None and job.get("enabled") is not enabled:
            continue
        if job_type is not None and job.get("job_type") != job_type:
            continue
        if status is not None and job.get("status") != status:
            continue
        items.append(dict(job))
    items.sort(key=lambda item: (item.get("next_run_at") or "", item["id"]), reverse=True)
    return {"items": items, "total": len(items)}


def create_scheduled_job_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    agent_id, skill_ids, model_gateway_config_id = validate_job_refs(current_store, payload)
    plugin_action_id, plugin_connection_id = validate_plugin_refs(current_store, payload)
    now = datetime.now(UTC).isoformat()
    job_id = current_store.new_id("scheduled_job")
    job = {
        "agent_id": agent_id,
        "config_json": payload.config_json,
        "created_at": now,
        "created_by": user["id"],
        "cron_expression": payload.cron_expression,
        "enabled": payload.enabled,
        "execution_mode": payload.execution_mode,
        "id": job_id,
        "interval_seconds": payload.interval_seconds,
        "job_type": payload.job_type,
        "last_error_message": None,
        "last_failure_at": None,
        "last_run_at": None,
        "last_success_at": None,
        "lock_ttl_seconds": payload.lock_ttl_seconds,
        "max_retry_count": payload.max_retry_count,
        "model_gateway_config_id": model_gateway_config_id,
        "name": ensure_non_blank(payload.name, "name"),
        "next_run_at": next_run_at(payload),
        "plugin_action_id": plugin_action_id,
        "plugin_connection_id": plugin_connection_id,
        "plugin_input_mapping": payload.plugin_input_mapping,
        "plugin_output_mapping": payload.plugin_output_mapping,
        "product_id": payload.product_id,
        "schedule_type": payload.schedule_type,
        "skill_ids": skill_ids,
        "source_system": ensure_non_blank(payload.source_system, "source_system"),
        "status": "active" if payload.enabled else "disabled",
        "timeout_seconds": payload.timeout_seconds,
        "timezone": payload.timezone,
        "updated_at": now,
    }
    current_store.scheduled_jobs[job_id] = job
    audit_event = record_audit_event(
        current_store,
        event_type="scheduled_job.created",
        actor_id=user["id"],
        subject_type="scheduled_job",
        subject_id=job_id,
        payload={"job_type": job["job_type"], "enabled": job["enabled"]},
    )
    persist_record(
        current_store,
        "save_scheduled_job_record",
        job,
        audit_event=audit_event,
    )
    return dict(job)


def patch_scheduled_job_response(
    *,
    current_store: Any,
    job_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_store(current_store)
    job = current_store.scheduled_jobs.get(job_id)
    if job is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    updates = payload.model_dump(exclude_unset=True)
    draft = SimpleNamespace(**{**job, **updates})
    agent_id, skill_ids, model_gateway_config_id = validate_job_refs(current_store, draft)
    plugin_action_id, plugin_connection_id = validate_plugin_refs(current_store, draft)
    if "name" in updates:
        updates["name"] = ensure_non_blank(updates["name"], "name")
    if "source_system" in updates:
        updates["source_system"] = ensure_non_blank(updates["source_system"], "source_system")
    updates["agent_id"] = agent_id
    updates["skill_ids"] = skill_ids
    updates["model_gateway_config_id"] = model_gateway_config_id
    updates["plugin_action_id"] = plugin_action_id
    updates["plugin_connection_id"] = plugin_connection_id
    if {"schedule_type", "interval_seconds", "cron_expression"} & updates.keys():
        updates["next_run_at"] = next_run_at(draft)
    if "enabled" in updates:
        updates["status"] = "active" if updates["enabled"] else "disabled"
    job = {**job, **updates, "updated_at": datetime.now(UTC).isoformat()}
    current_store.scheduled_jobs[job_id] = job
    audit_event = record_audit_event(
        current_store,
        event_type="scheduled_job.updated",
        actor_id=user["id"],
        subject_type="scheduled_job",
        subject_id=job_id,
        payload={"job_type": job["job_type"], "enabled": job["enabled"]},
    )
    persist_record(
        current_store,
        "save_scheduled_job_record",
        job,
        audit_event=audit_event,
    )
    return dict(job)


def resolve_ai_snapshots(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    agent = current_store.ai_agents.get(job.get("agent_id")) if job.get("agent_id") else None
    skills = []
    for skill_id in job.get("skill_ids", []):
        skill = dict(current_store.ai_skills[skill_id])
        package_snapshot = load_skill_package_snapshot(skill)
        if package_snapshot is not None:
            skill["package_snapshot"] = package_snapshot
        skills.append(skill)
    return {
        "resolved_agent_snapshot": snapshot(current_store, agent or {}),
        "resolved_prompt_snapshot": {
            "agent_system_prompt": (agent or {}).get("system_prompt"),
            "skill_prompt_templates": [
                {"code": skill["code"], "prompt_template": skill.get("prompt_template")}
                for skill in skills
            ],
        },
        "resolved_skill_snapshots": snapshot(current_store, skills),
        "tool_policy_snapshot": snapshot(current_store, (agent or {}).get("tool_policy") or {}),
    }


def resolve_job_snapshots(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    snapshots = resolve_ai_snapshots(current_store, job)
    snapshots["resolved_plugin_snapshot"] = resolve_plugin_snapshot(
        current_store,
        action_id=job.get("plugin_action_id"),
        connection_id=job.get("plugin_connection_id"),
    )
    return snapshots


def create_collector_run_for_job(
    current_store: Any,
    *,
    job: dict[str, Any],
    run_id: str,
    status: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    collector_run_id = current_store.new_id("collector_run")
    collector_type = {
        "iteration_plan_suggestion_generate": "iteration_plan_suggestion",
        "online_log_ai_analysis": "online_log_metric",
    }.get(job["job_type"], job["job_type"].removesuffix("_collect"))
    collector_run = {
        "collector_type": collector_type,
        "created_at": now,
        "created_by": user["id"],
        "error_message": None,
        "finished_at": now if status in SCHEDULED_JOB_RUN_TERMINAL_STATUSES else None,
        "id": collector_run_id,
        "payload_summary": {"scheduled_job_id": job["id"], "scheduled_job_run_id": run_id},
        "product_id": job.get("product_id"),
        "records_imported": 0,
        "source_system": job["source_system"],
        "started_at": now,
        "status": "running",
        "updated_at": now,
    }
    current_store.collector_runs[collector_run_id] = collector_run
    audit_event = record_audit_event(
        current_store,
        event_type="collector_run.created",
        actor_id=user["id"],
        subject_type="collector_run",
        subject_id=collector_run_id,
        payload={"collector_type": collector_type, "scheduled_job_id": job["id"]},
    )
    persist_record(
        current_store,
        "save_collector_run_record",
        collector_run,
        audit_event=audit_event,
    )
    return collector_run


def complete_collector_run(
    current_store: Any,
    *,
    collector_run: dict[str, Any],
    error_message: str | None,
    records_imported: int,
    status: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    collector_status = "succeeded" if status == "succeeded" else "failed"
    updated = {
        **collector_run,
        "error_message": error_message,
        "finished_at": now,
        "records_imported": records_imported,
        "status": collector_status,
        "updated_at": now,
    }
    current_store.collector_runs[collector_run["id"]] = updated
    audit_event = record_audit_event(
        current_store,
        event_type="collector_run.updated",
        actor_id=user["id"],
        subject_type="collector_run",
        subject_id=collector_run["id"],
        payload={"records_imported": records_imported, "status": collector_status},
    )
    persist_record(
        current_store,
        "save_collector_run_record",
        updated,
        audit_event=audit_event,
    )
    return updated


def run_iteration_plan_job(
    current_store: Any,
    *,
    job: dict[str, Any],
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    config = job.get("config_json") or {}
    payload = SimpleNamespace(
        constraints=config.get("constraints") or {},
        include_evidence=config.get("include_evidence", True),
        module_codes=config.get("module_codes") or [],
        planning_cycle=ensure_non_blank(
            config.get("planning_cycle") or "scheduled",
            "planning_cycle",
        ),
        product_id=job.get("product_id"),
        version_id=config.get("version_id"),
    )
    result = create_iteration_suggestions_response(
        current_store=current_store,
        payload=payload,
        user=user,
    )
    suggestion = result["items"][0] if result["items"] else None
    summary = {
        "evidence_count": len(suggestion.get("evidence", [])) if suggestion else 0,
        "suggestion_id": suggestion["id"] if suggestion else None,
        "suggestions_created": result["total"],
    }
    return summary, result["total"]


def normalized_insight_enum(value: Any, allowed_values: set[str], fallback: str) -> str:
    if isinstance(value, str) and value in allowed_values:
        return value
    return fallback


def run_user_feedback_insight_extract_job(
    current_store: Any,
    *,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    mapping = job.get("plugin_output_mapping") or {}
    response_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
    insights = json_path_value(response_json, str(mapping.get("insights_path") or "$.insights"))
    if insights is None:
        insights = []
    if not isinstance(insights, list):
        raise api_error(400, "PLUGIN_RESULT_INVALID", "Mapped insights result must be a list")

    created_ids: list[str] = []
    skipped = 0
    for insight in insights:
        if not isinstance(insight, dict) or not str(insight.get("content") or "").strip():
            skipped += 1
            continue
        product_id = insight.get("product_id") or job.get("product_id")
        if not isinstance(product_id, str) or not product_id:
            skipped += 1
            continue
        feature_code = insight.get("feature_code")
        module_code = insight.get("module_code")
        related_requirement_id = insight.get("related_requirement_id")
        payload = SimpleNamespace(
            content=str(insight["content"]),
            feature_code=feature_code if isinstance(feature_code, str) else None,
            feedback_type=normalized_insight_enum(
                insight.get("feedback_type"),
                USER_FEEDBACK_TYPES,
                "improvement",
            ),
            module_code=module_code if isinstance(module_code, str) else None,
            product_id=product_id,
            related_requirement_id=related_requirement_id
            if isinstance(related_requirement_id, str)
            else None,
            satisfaction_score=insight.get("satisfaction_score")
            if isinstance(insight.get("satisfaction_score"), int)
            else None,
            sentiment=normalized_insight_enum(
                insight.get("sentiment"),
                USER_FEEDBACK_SENTIMENTS,
                "neutral",
            ),
            source_channel=str(insight.get("source_channel") or "maxcompute_weekly_ai"),
            tags=insight.get("tags") if isinstance(insight.get("tags"), list) else [],
        )
        created = create_user_feedback_response(
            current_store=current_store,
            payload=payload,
            user=user,
        )
        created_ids.append(created["id"])

    summary = {
        "insight_ids": created_ids,
        "insights_created": len(created_ids),
        "plugin": plugin_summary,
        "skipped_insights": skipped,
        "source_row_count": records_imported_from_mapping(
            plugin_summary.get("response_summary") or {},
            {"records_imported_path": mapping.get("records_imported_path")},
        ),
    }
    return summary, len(created_ids)


def run_scheduled_job_response(
    *,
    current_store: Any,
    job_id: str,
    trigger_type: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_store(current_store)
    sync_ai_agent_store(current_store)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    job = current_store.scheduled_jobs.get(job_id)
    if job is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    if not job.get("enabled"):
        raise api_error(409, "SCHEDULED_JOB_DISABLED", "Scheduled job is disabled")
    run_id = current_store.new_id("scheduled_job_run")
    now = datetime.now(UTC).isoformat()
    snapshots = resolve_job_snapshots(current_store, job)
    run = {
        **snapshots,
        "collector_run_id": None,
        "config_snapshot": snapshot(current_store, job),
        "created_at": now,
        "error_code": None,
        "error_message": None,
        "finished_at": None,
        "id": run_id,
        "plugin_invocation_log_id": None,
        "records_imported": 0,
        "result_summary": {},
        "scheduled_for": now,
        "scheduled_job_id": job_id,
        "started_at": now,
        "status": "running",
        "trigger_type": trigger_type,
        "updated_at": now,
    }
    current_store.scheduled_job_runs[run_id] = run
    collector_run = create_collector_run_for_job(
        current_store,
        job=job,
        run_id=run_id,
        status="running",
        user=user,
    )
    run["collector_run_id"] = collector_run["id"]
    persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
    )
    try:
        plugin_summary = None
        plugin_records_imported = 0
        if job.get("plugin_action_id"):
            resolved_plugin_input_mapping = resolve_plugin_input_mapping(
                job.get("plugin_input_mapping") or {},
                job,
            )
            plugin_log = invoke_plugin_action_response(
                action_id=job["plugin_action_id"],
                connection_id=job.get("plugin_connection_id"),
                current_store=current_store,
                input_payload={
                    "config": job.get("config_json") or {},
                    "input_mapping": resolved_plugin_input_mapping,
                    "job_id": job["id"],
                    "product_id": job.get("product_id"),
                    "timezone": job.get("timezone") or "UTC",
                },
                scheduled_job_id=job_id,
                scheduled_job_run_id=run_id,
                trigger_type=trigger_type,
                user=user,
            )
            plugin_summary = {
                "invocation_log_id": plugin_log["id"],
                "response_summary": plugin_log.get("response_summary") or {},
                "status": plugin_log["status"],
            }
            plugin_records_imported = records_imported_from_mapping(
                plugin_log.get("response_summary") or {},
                job.get("plugin_output_mapping") or {},
            )
            run["plugin_invocation_log_id"] = plugin_log["id"]
        if job["job_type"] == "iteration_plan_suggestion_generate":
            result_summary, records_imported = run_iteration_plan_job(
                current_store,
                job=job,
                user=user,
            )
            if plugin_summary is not None:
                result_summary = {**result_summary, "plugin": plugin_summary}
                records_imported += plugin_records_imported
        elif job["job_type"] == "plugin_action_invoke" and plugin_summary is not None:
            result_summary = {"plugin": plugin_summary}
            records_imported = plugin_records_imported
        elif job["job_type"] == "user_feedback_insight_extract" and plugin_summary is not None:
            result_summary, records_imported = run_user_feedback_insight_extract_job(
                current_store,
                job=job,
                plugin_summary=plugin_summary,
                user=user,
            )
        else:
            result_summary = {"message": "No handler implemented"}
            if plugin_summary is not None:
                result_summary["plugin"] = plugin_summary
            records_imported = plugin_records_imported
        status = "succeeded"
        error_code = None
        error_message = None
    except Exception as exc:
        status = "failed"
        error_code = exc.__class__.__name__
        error_message = str(exc)
        result_summary = {}
        records_imported = 0
    finished_at = datetime.now(UTC).isoformat()
    run = {
        **run,
        "error_code": error_code,
        "error_message": error_message,
        "finished_at": finished_at,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": status,
        "updated_at": finished_at,
    }
    current_store.scheduled_job_runs[run_id] = run
    complete_collector_run(
        current_store,
        collector_run=collector_run,
        error_message=error_message,
        records_imported=records_imported,
        status=status,
        user=user,
    )
    job_update = {
        **job,
        "last_error_message": error_message,
        "last_failure_at": finished_at if status == "failed" else job.get("last_failure_at"),
        "last_run_at": finished_at,
        "last_success_at": finished_at if status == "succeeded" else job.get("last_success_at"),
        "updated_at": finished_at,
    }
    current_store.scheduled_jobs[job_id] = job_update
    persist_record(
        current_store,
        "save_scheduled_job_record",
        job_update,
    )
    persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
    )
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{status}",
        actor_id=user["id"],
        subject_type="scheduled_job_run",
        subject_id=run_id,
        payload={"job_type": job["job_type"], "scheduled_job_id": job_id},
    )
    persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
        audit_event=audit_event,
    )
    return dict(run)


def list_scheduled_job_runs_response(
    *,
    current_store: Any,
    scheduled_job_id: str | None,
    status: str | None,
) -> dict[str, Any]:
    if status is not None:
        ensure_enum(status, SCHEDULED_JOB_RUN_STATUSES, "status")
    sync_scheduled_job_run_store(
        current_store,
        scheduled_job_id=scheduled_job_id,
        status=status,
    )
    items = []
    for run in current_store.scheduled_job_runs.values():
        if scheduled_job_id is not None and run.get("scheduled_job_id") != scheduled_job_id:
            continue
        if status is not None and run.get("status") != status:
            continue
        items.append(dict(run))
    items.sort(key=lambda item: (item.get("started_at") or "", item["id"]), reverse=True)
    return {"items": items, "total": len(items)}


def cancel_scheduled_job_run_response(
    *,
    current_store: Any,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_run_store(current_store)
    run = current_store.scheduled_job_runs.get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job run not found")
    if run["status"] in SCHEDULED_JOB_RUN_TERMINAL_STATUSES:
        raise api_error(409, "SCHEDULED_JOB_RUN_STATE_INVALID", "Terminal run cannot be cancelled")
    now = datetime.now(UTC).isoformat()
    run = {**run, "finished_at": now, "status": "cancelled", "updated_at": now}
    current_store.scheduled_job_runs[run_id] = run
    audit_event = record_audit_event(
        current_store,
        event_type="scheduled_job_run.cancelled",
        actor_id=user["id"],
        subject_type="scheduled_job_run",
        subject_id=run_id,
    )
    persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
        audit_event=audit_event,
    )
    return dict(run)
