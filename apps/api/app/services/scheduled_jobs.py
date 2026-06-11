from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.deps import api_error, require_roles
from app.services.code_inspections import (
    execute_code_inspection_result_actions,
    validate_code_inspection_result_actions,
)
from app.services.dynamic_parameters import (
    dynamic_time_parameters,
    resolve_dynamic_parameter_value,
)
from app.services.iteration_planning import create_iteration_suggestions_response
from app.services.knowledge_documents import (
    knowledge_document_chunks,
    knowledge_query_repository,
    knowledge_repository_access_args,
)
from app.services.knowledge_search import KNOWLEDGE_SEARCHABLE_STATUSES
from app.services.model_gateway_config_context import (
    save_model_gateway_records,
)
from app.services.model_gateway_logging import (
    estimate_tokens,
    model_gateway_log,
    openai_usage_tokens,
)
from app.services.model_gateway_runtime import model_gateway_chat_completions_url
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
    "code_repository_inspection",
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
USER_FEEDBACK_INSIGHT_WRITE_TARGETS = {"scheduled_job_result", "user_feedback_insights"}


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


def exception_error_code_and_message(exc: Exception) -> tuple[str, str]:
    error_code = exc.__class__.__name__
    error_message = str(exc)
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        error_code = str(detail.get("code") or error_code)
        error_message = str(detail.get("message") or error_message)
    return error_code, error_message


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


def payload_field(payload: Any, name: str, default: Any = None) -> Any:
    if isinstance(payload, dict):
        return payload.get(name, default)
    return getattr(payload, name, default)


def normalized_knowledge_document_ids(value: Any) -> list[str]:
    if value is None:
        return []
    ids = value if isinstance(value, list) else []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in ids:
        if not isinstance(item, str):
            raise api_error(400, "VALIDATION_ERROR", "knowledge_document_ids must be strings")
        document_id = item.strip()
        if not document_id:
            continue
        if document_id in seen:
            continue
        seen.add(document_id)
        normalized.append(document_id)
    return normalized


def readable_knowledge_documents_by_id(
    current_store: Any,
    *,
    document_ids: list[str],
    user: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not document_ids:
        return {}
    requested = set(document_ids)
    repository = knowledge_query_repository(current_store)
    if repository is not None:
        documents = repository.list_knowledge_documents(
            **knowledge_repository_access_args(user),
        )
    else:
        from app.services.knowledge_management import document_is_readable

        documents = [
            document
            for document in current_store.knowledge_documents.values()
            if document_is_readable(current_store, user, document)
        ]
    return {
        document["id"]: dict(document)
        for document in documents
        if document.get("id") in requested
    }


def validate_knowledge_document_ids(
    current_store: Any,
    document_ids: list[str],
    *,
    user: dict[str, Any],
) -> list[str]:
    normalized = normalized_knowledge_document_ids(document_ids)
    if not normalized:
        return []
    documents_by_id = readable_knowledge_documents_by_id(
        current_store,
        document_ids=normalized,
        user=user,
    )
    missing = [document_id for document_id in normalized if document_id not in documents_by_id]
    if missing:
        raise api_error(
            404,
            "KNOWLEDGE_DOCUMENT_NOT_FOUND",
            f"Knowledge document not found or not readable: {', '.join(missing)}",
        )
    unsearchable = [
        document_id
        for document_id in normalized
        if documents_by_id[document_id].get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES
    ]
    if unsearchable:
        raise api_error(
            400,
            "KNOWLEDGE_DOCUMENT_NOT_SEARCHABLE",
            f"Knowledge document is not searchable: {', '.join(unsearchable)}",
        )
    return normalized


def effective_scheduled_job_type(payload: Any) -> str:
    job_type = str(payload_field(payload, "job_type") or "")
    skill_ids = list(payload_field(payload, "skill_ids", []) or [])
    if (
        job_type == "user_feedback_collect"
        and payload_field(payload, "plugin_action_id") is not None
        and (
            payload_field(payload, "agent_id") is not None
            or payload_field(payload, "model_gateway_config_id") is not None
            or bool(skill_ids)
        )
    ):
        return "user_feedback_insight_extract"
    return job_type


def effective_scheduled_job_execution_mode(payload: Any, job_type: str) -> str:
    if job_type == "user_feedback_insight_extract":
        return "ai_generated"
    return str(payload_field(payload, "execution_mode") or "deterministic")


def validate_job_refs(
    current_store: Any,
    payload: Any,
) -> tuple[str | None, list[str], str | None, str, str]:
    job_type = effective_scheduled_job_type(payload)
    execution_mode = effective_scheduled_job_execution_mode(payload, job_type)
    ensure_enum(job_type, SCHEDULED_JOB_TYPES, "job_type")
    ensure_enum(execution_mode, SCHEDULED_JOB_EXECUTION_MODES, "execution_mode")
    ensure_enum(payload.schedule_type, SCHEDULED_JOB_SCHEDULE_TYPES, "schedule_type")
    sync_ai_agent_store(current_store)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    validate_product(current_store, payload.product_id)
    agent_id = payload.agent_id
    skill_ids = list(payload.skill_ids)
    model_gateway_config_id = payload.model_gateway_config_id
    plugin_backed_ai_job = job_type == "user_feedback_insight_extract"
    ai_processing_job = (
        execution_mode in {"ai_assisted", "ai_generated"}
        or plugin_backed_ai_job
    )
    if ai_processing_job:
        if agent_id is None:
            raise api_error(400, "AI_AGENT_REQUIRED", "AI job requires agent_id")
        agent = current_store.ai_agents.get(agent_id)
        if agent is None:
            raise api_error(404, "NOT_FOUND", "AI agent not found")
        if agent.get("status") != "active":
            raise api_error(400, "AI_AGENT_INACTIVE", "AI agent is inactive")
        if not skill_ids and not plugin_backed_ai_job:
            skill_ids = list(agent.get("default_skill_ids") or [])
        if plugin_backed_ai_job and not skill_ids:
            raise api_error(400, "AI_SKILL_REQUIRED", "AI processing job requires skill_ids")
        ensure_active_skills(current_store, skill_ids)
        if plugin_backed_ai_job and model_gateway_config_id is None:
            raise api_error(
                400,
                "MODEL_GATEWAY_CONFIG_REQUIRED",
                "AI processing job requires model_gateway_config_id",
            )
        model_gateway_config_id = ensure_active_model_gateway(
            current_store,
            model_gateway_config_id or agent.get("model_gateway_config_id"),
        )
    return agent_id, skill_ids, model_gateway_config_id, job_type, execution_mode


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
        if effective_scheduled_job_type(payload) == "user_feedback_insight_extract":
            raise api_error(
                400,
                "PLUGIN_ACTION_REQUIRED",
                "user_feedback_insight_extract requires plugin_action_id",
            )
        if effective_scheduled_job_type(payload) == "code_repository_inspection":
            raise api_error(
                400,
                "PLUGIN_ACTION_REQUIRED",
                "code_repository_inspection requires plugin_action_id",
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
    (
        agent_id,
        skill_ids,
        model_gateway_config_id,
        job_type,
        execution_mode,
    ) = validate_job_refs(current_store, payload)
    plugin_action_id, plugin_connection_id = validate_plugin_refs(current_store, payload)
    result_actions = validate_code_inspection_result_actions(
        payload.result_actions if job_type == "code_repository_inspection" else [],
    )
    knowledge_document_ids = validate_knowledge_document_ids(
        current_store,
        payload.knowledge_document_ids,
        user=user,
    )
    now = datetime.now(UTC).isoformat()
    job_id = current_store.new_id("scheduled_job")
    job = {
        "agent_id": agent_id,
        "config_json": payload.config_json,
        "created_at": now,
        "created_by": user["id"],
        "cron_expression": payload.cron_expression,
        "enabled": payload.enabled,
        "execution_mode": execution_mode,
        "id": job_id,
        "interval_seconds": payload.interval_seconds,
        "job_type": job_type,
        "knowledge_document_ids": knowledge_document_ids,
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
        "result_actions": result_actions,
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
    (
        agent_id,
        skill_ids,
        model_gateway_config_id,
        job_type,
        execution_mode,
    ) = validate_job_refs(current_store, draft)
    plugin_action_id, plugin_connection_id = validate_plugin_refs(current_store, draft)
    draft_result_actions = (
        payload_field(draft, "result_actions", [])
        if job_type == "code_repository_inspection"
        else []
    )
    result_actions = validate_code_inspection_result_actions(draft_result_actions)
    knowledge_document_ids = validate_knowledge_document_ids(
        current_store,
        payload_field(draft, "knowledge_document_ids", []),
        user=user,
    )
    if "name" in updates:
        updates["name"] = ensure_non_blank(updates["name"], "name")
    if "source_system" in updates:
        updates["source_system"] = ensure_non_blank(updates["source_system"], "source_system")
    updates["agent_id"] = agent_id
    updates["skill_ids"] = skill_ids
    updates["model_gateway_config_id"] = model_gateway_config_id
    updates["job_type"] = job_type
    updates["knowledge_document_ids"] = knowledge_document_ids
    updates["execution_mode"] = execution_mode
    updates["plugin_action_id"] = plugin_action_id
    updates["plugin_connection_id"] = plugin_connection_id
    updates["result_actions"] = result_actions
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


def delete_scheduled_job_response(
    *,
    current_store: Any,
    job_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_store(current_store)
    job = current_store.scheduled_jobs.get(job_id)
    if job is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    current_store.scheduled_jobs.pop(job_id, None)
    audit_event = record_audit_event(
        current_store,
        event_type="scheduled_job.deleted",
        actor_id=user["id"],
        subject_type="scheduled_job",
        subject_id=job_id,
        payload={"job_type": job["job_type"], "name": job["name"]},
    )
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_scheduled_job_record", None)
    if callable(delete_record):
        delete_record(job_id, audit_event=audit_event)
    return {"deleted": True, "id": job_id}


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
        "code_repository_inspection": "code_inspection",
        "iteration_plan_suggestion_generate": "iteration_plan_suggestion",
        "online_log_ai_analysis": "online_log_metric",
        "user_feedback_insight_extract": "user_feedback",
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


def resolve_job_plugin_output_mapping(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    job_mapping = job.get("plugin_output_mapping") or {}
    if job_mapping:
        return job_mapping
    action_id = job.get("plugin_action_id")
    if not action_id:
        return {}
    action = current_store.plugin_actions.get(action_id) or {}
    action_mapping = action.get("result_mapping") or {}
    return dict(action_mapping) if isinstance(action_mapping, dict) else {}


def skill_codes_for_job(current_store: Any, job: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for skill_id in job.get("skill_ids", []):
        skill = current_store.ai_skills.get(skill_id)
        if skill is not None and skill.get("code"):
            codes.append(str(skill["code"]))
    return codes


def selected_model_gateway_config(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    sync_reference_store(current_store)
    config_id = job.get("model_gateway_config_id")
    config = current_store.model_gateway_configs.get(config_id) if config_id else None
    if config is None:
        raise api_error(400, "MODEL_GATEWAY_CONFIG_REQUIRED", "AI model config is required")
    if config.get("status") != "active":
        raise api_error(400, "MODEL_GATEWAY_CONFIG_INACTIVE", "Model gateway config is inactive")
    if config.get("provider") != "openai_compatible":
        raise api_error(
            400,
            "MODEL_GATEWAY_PROVIDER_UNSUPPORTED",
            "Model gateway provider is not supported",
        )
    if not config.get("api_key"):
        raise api_error(
            400,
            "MODEL_GATEWAY_CONFIG_INVALID",
            "Model gateway config is missing api_key",
        )
    return config


def scheduled_job_knowledge_references(
    current_store: Any,
    *,
    job: dict[str, Any],
    user: dict[str, Any],
    max_content_chars: int = 1200,
    max_chunks: int = 8,
) -> list[dict[str, Any]]:
    document_ids = normalized_knowledge_document_ids(job.get("knowledge_document_ids") or [])
    if not document_ids:
        return []
    document_order = {document_id: index for index, document_id in enumerate(document_ids)}
    repository = knowledge_query_repository(current_store)
    candidates: list[dict[str, Any]]
    if repository is not None:
        candidates = repository.search_knowledge_chunks(
            **knowledge_repository_access_args(user),
            query=None,
        )
    else:
        documents_by_id = readable_knowledge_documents_by_id(
            current_store,
            document_ids=document_ids,
            user=user,
        )
        candidates = []
        for document_id in document_ids:
            document = documents_by_id.get(document_id)
            if document is None:
                continue
            if document.get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES:
                continue
            for chunk in knowledge_document_chunks(current_store, document_id):
                candidates.append({"chunk": chunk, "document": document})

    references: list[dict[str, Any]] = []
    for candidate in candidates:
        document = candidate.get("document") or {}
        chunk = candidate.get("chunk") or {}
        document_id = document.get("id")
        if document_id not in document_order:
            continue
        if chunk.get("metadata", {}).get("chunk_role") == "parent":
            continue
        content = str(chunk.get("content") or "").strip()
        if not content:
            continue
        references.append(
            {
                "chunk_id": chunk.get("id"),
                "chunk_index": chunk.get("chunk_index"),
                "content": content[:max_content_chars],
                "document_id": document_id,
                "title": document.get("title"),
            }
        )
    references.sort(
        key=lambda item: (
            document_order.get(str(item.get("document_id")), 999999),
            int(item.get("chunk_index") or 0),
            str(item.get("chunk_id") or ""),
        )
    )
    return references[:max_chunks]


def model_json_content(response_payload: dict[str, Any]) -> dict[str, Any]:
    content = response_payload["choices"][0]["message"]["content"]
    if isinstance(content, dict):
        return content
    text = str(content).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Model output must be a JSON object")
    return parsed


def scheduled_job_ai_messages(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    source_response_json: dict[str, Any],
    source_row_count: int,
    knowledge_references: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    agent = current_store.ai_agents.get(job.get("agent_id")) if job.get("agent_id") else None
    skill_prompts = []
    for skill_id in job.get("skill_ids", []):
        skill = current_store.ai_skills.get(skill_id)
        if skill is not None:
            prompt = skill.get("prompt_template") or skill.get("description") or skill.get("name")
            if prompt:
                skill_prompts.append(
                    {
                        "code": skill.get("code"),
                        "prompt": prompt,
                    },
                )
    output_contract = {
        "insights_path": str(output_mapping.get("insights_path") or "$.insights"),
        "records_imported_path": str(output_mapping.get("records_imported_path") or "$.row_count"),
        "write_target": output_mapping.get("write_target") or "user_feedback_insights",
    }
    system_prompt = (
        (agent or {}).get("system_prompt")
        or "你是企业 AI 大脑的数据分析助手，负责把数据连接返回的原始数据整理为结果动作需要的 JSON。"
    )
    user_payload = {
        "instructions": [
            "分析 data_connection_response 中的数据，提取有价值的信息。",
            "必须只返回 JSON 对象，不要返回 Markdown。",
            (
                "返回 JSON 必须包含 insights 数组；每个 insight 至少包含 "
                "content、feedback_type、sentiment、source_channel 和 tags。"
            ),
            "如果源数据已有可用洞察，也要校验、清洗并输出为结果动作可消费的结构。",
        ],
        "job": {
            "id": job.get("id"),
            "job_type": job.get("job_type"),
            "product_id": job.get("product_id"),
            "source_system": job.get("source_system"),
            "timezone": job.get("timezone"),
        },
        "output_contract": output_contract,
        "skill_prompts": skill_prompts,
        "source_row_count": source_row_count,
        "data_connection_response": source_response_json,
    }
    if knowledge_references:
        user_payload["knowledge_references"] = knowledge_references
    return [
        {"role": "system", "content": str(system_prompt)},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
    ]


def run_scheduled_job_ai_processing(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    source_response_json: dict[str, Any],
    source_row_count: int,
    user: dict[str, Any],
) -> dict[str, Any]:
    config = selected_model_gateway_config(current_store, job)
    knowledge_references = scheduled_job_knowledge_references(
        current_store,
        job=job,
        user=user,
    )
    messages = scheduled_job_ai_messages(
        current_store,
        job=job,
        knowledge_references=knowledge_references,
        output_mapping=output_mapping,
        source_response_json=source_response_json,
        source_row_count=source_row_count,
    )
    body = {
        "messages": messages,
        "model": config["default_chat_model"],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    request = UrlRequest(
        model_gateway_chat_completions_url(config["base_url"]),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = perf_counter()
    try:
        with urlopen(request, timeout=int(config.get("timeout_seconds") or 60)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        output_json = model_json_content(response_payload)
        latency_ms = int((perf_counter() - started) * 1000)
        model_log = model_gateway_log(
            current_store,
            provider=config["provider"],
            model=config["default_chat_model"],
            config_id=config["id"],
            tokens=openai_usage_tokens(
                response_payload.get("usage"),
                messages=messages,
                output=output_json,
            ),
            latency_ms=latency_ms,
            status="succeeded",
            purpose="scheduled_job_ai_processing",
        )
    except (
        AttributeError,
        HTTPError,
        URLError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        model_log = model_gateway_log(
            current_store,
            provider=str(config.get("provider") or "openai_compatible"),
            model=str(config.get("default_chat_model") or ""),
            config_id=config.get("id"),
            tokens={
                "completion": 0,
                "prompt": estimate_tokens(messages),
                "total": estimate_tokens(messages),
            },
            latency_ms=latency_ms,
            status="failed",
            purpose="scheduled_job_ai_processing",
            error="Scheduled job AI processing failed",
        )
        audit_event = record_audit_event(
            current_store,
            event_type="model_gateway.called",
            actor_id=user["id"],
            subject_type="model_gateway_log",
            subject_id=model_log["id"],
            payload={
                "model": model_log["model"],
                "model_log_id": model_log["id"],
                "provider": model_log["provider"],
                "purpose": model_log["purpose"],
                "scheduled_job_id": job["id"],
                "status": model_log["status"],
            },
        )
        save_model_gateway_records(current_store, audit_event=audit_event)
        raise api_error(
            502,
            "MODEL_GATEWAY_CALL_FAILED",
            "Scheduled job AI processing failed",
        ) from exc

    audit_event = record_audit_event(
        current_store,
        event_type="model_gateway.called",
        actor_id=user["id"],
        subject_type="model_gateway_log",
        subject_id=model_log["id"],
        payload={
            "model": model_log["model"],
            "model_log_id": model_log["id"],
            "provider": model_log["provider"],
            "purpose": model_log["purpose"],
            "scheduled_job_id": job["id"],
            "status": model_log["status"],
        },
    )
    save_model_gateway_records(current_store, audit_event=audit_event)
    return {
        "knowledge_references": knowledge_references,
        "model_gateway_config_id": config["id"],
        "model_log_id": model_log["id"],
        "model": config["default_chat_model"],
        "output_json": output_json,
        "provider": config["provider"],
        "status": "succeeded",
        "tokens": model_log["tokens"],
    }


def build_data_connection_execution_node(
    *,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    records_imported: int,
    resolved_plugin_input_mapping: dict[str, Any],
) -> dict[str, Any]:
    return {
        "action_id": plugin_summary.get("action_id") or job.get("plugin_action_id"),
        "connection_id": plugin_summary.get("connection_id") or job.get("plugin_connection_id"),
        "input_mapping": resolved_plugin_input_mapping,
        "label": "数据连接获取内容",
        "plugin_invocation_log_id": plugin_summary.get("invocation_log_id"),
        "records_imported": records_imported,
        "request_summary": plugin_summary.get("request_summary") or {},
        "response_summary": plugin_summary.get("response_summary") or {},
        "status": plugin_summary.get("status") or "unknown",
    }


def build_plugin_action_execution_nodes(
    current_store: Any,
    *,
    job: dict[str, Any],
    plugin_output_mapping: dict[str, Any],
    plugin_records_imported: int,
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
) -> dict[str, Any]:
    skill_ids = list(job.get("skill_ids", []))
    return {
        "data_connection": build_data_connection_execution_node(
            job=job,
            plugin_summary=plugin_summary,
            records_imported=plugin_records_imported,
            resolved_plugin_input_mapping=resolved_plugin_input_mapping,
        ),
        "result_action": {
            "action_id": plugin_summary.get("action_id") or job.get("plugin_action_id"),
            "feedback": {
                "plugin_invocation_log_id": plugin_summary.get("invocation_log_id"),
                "records_imported": plugin_records_imported,
                "response_summary": plugin_summary.get("response_summary") or {},
            },
            "label": "结果动作反馈内容",
            "records_imported": plugin_records_imported,
            "status": plugin_summary.get("status") or "unknown",
            "write_target": plugin_output_mapping.get("write_target") or "scheduled_job_result",
        },
        "skill_processing": {
            "label": "Skill 处理后内容",
            "model_gateway_called": False,
            "note": "当前作业类型未执行平台 Skill/大模型处理，结果直接来自插件动作。",
            "processing_mode": "plugin_structured_output",
            "skill_codes": skill_codes_for_job(current_store, job),
            "skill_ids": skill_ids,
            "status": "not_configured" if not skill_ids else "not_run",
        },
    }


def run_user_feedback_insight_extract_job(
    current_store: Any,
    *,
    job: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    mapping = resolve_job_plugin_output_mapping(current_store, job)
    write_target = str(mapping.get("write_target") or "user_feedback_insights")
    if write_target not in USER_FEEDBACK_INSIGHT_WRITE_TARGETS:
        raise api_error(
            400,
            "PLUGIN_WRITE_TARGET_UNSUPPORTED",
            f"Unsupported write_target for user_feedback_insight_extract: {write_target}",
        )
    source_response_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
    if not isinstance(source_response_json, dict):
        source_response_json = {}
    source_row_count = records_imported_from_mapping(
        plugin_summary.get("response_summary") or {},
        {"records_imported_path": mapping.get("records_imported_path")},
    )
    ai_processing = run_scheduled_job_ai_processing(
        current_store,
        job=job,
        output_mapping=mapping,
        source_response_json=source_response_json,
        source_row_count=source_row_count,
        user=user,
    )
    processed_json = ai_processing["output_json"]
    insights = json_path_value(processed_json, str(mapping.get("insights_path") or "$.insights"))
    if insights is None:
        insights = []
    if not isinstance(insights, list):
        raise api_error(400, "PLUGIN_RESULT_INVALID", "Mapped insights result must be a list")

    created_ids: list[str] = []
    skipped = 0
    if write_target == "user_feedback_insights":
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

    skill_ids = list(job.get("skill_ids", []))
    skill_codes = skill_codes_for_job(current_store, job)
    summary = {
        "execution_nodes": {
            "data_connection": build_data_connection_execution_node(
                job=job,
                plugin_summary=plugin_summary,
                records_imported=source_row_count,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            ),
            "result_action": {
                "action_id": plugin_summary.get("action_id") or job.get("plugin_action_id"),
                "created_ids": created_ids,
                "feedback": {
                    "created_ids": created_ids,
                    "records_imported": len(created_ids),
                    "skipped_insights": skipped,
                    "stored_in_run_result": write_target == "scheduled_job_result",
                    "write_target": write_target,
                },
                "label": "结果动作反馈内容",
                "records_imported": len(created_ids),
                "skipped_insights": skipped,
                "status": "succeeded",
                "write_target": write_target,
            },
            "skill_processing": {
                "input": {
                    "insights_path": str(mapping.get("insights_path") or "$.insights"),
                    "knowledge_references": ai_processing.get("knowledge_references") or [],
                    "source_row_count": source_row_count,
                },
                "label": "Skill 处理后内容",
                "model_gateway_called": True,
                "model_gateway_config_id": ai_processing["model_gateway_config_id"],
                "model_log_id": ai_processing["model_log_id"],
                "note": "数据连接返回内容已通过平台 AI 大模型处理为结果动作可消费的结构化 JSON。",
                "output": {
                    "candidate_count": len(insights),
                    "insights": insights,
                    "insights_created": len(created_ids),
                    "processed_json": processed_json,
                    "skipped_insights": skipped,
                },
                "processing_mode": "model_gateway_json_transform",
                "skill_codes": skill_codes,
                "skill_ids": skill_ids,
                "status": ai_processing["status"],
            },
        },
        "insight_ids": created_ids,
        "insights_created": len(created_ids),
        "plugin": plugin_summary,
        "processing": {
            "skill_ids": skill_ids,
            "skill_codes": skill_codes,
        },
        "skipped_insights": skipped,
        "source_row_count": source_row_count,
        "write_target": write_target,
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
    effective_job_type = effective_scheduled_job_type(job)
    effective_execution_mode = effective_scheduled_job_execution_mode(job, effective_job_type)
    if (
        effective_job_type != job.get("job_type")
        or effective_execution_mode != job.get("execution_mode")
    ):
        job = {
            **job,
            "execution_mode": effective_execution_mode,
            "job_type": effective_job_type,
        }
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
    plugin_summary = None
    plugin_output_mapping: dict[str, Any] = {}
    plugin_records_imported = 0
    resolved_plugin_input_mapping: dict[str, Any] = {}
    try:
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
                "action_id": plugin_log.get("action_id"),
                "connection_id": plugin_log.get("connection_id"),
                "invocation_log_id": plugin_log["id"],
                "request_summary": plugin_log.get("request_summary") or {},
                "response_summary": plugin_log.get("response_summary") or {},
                "status": plugin_log["status"],
            }
            plugin_output_mapping = resolve_job_plugin_output_mapping(current_store, job)
            plugin_records_imported = records_imported_from_mapping(
                plugin_log.get("response_summary") or {},
                plugin_output_mapping,
            )
            run["plugin_invocation_log_id"] = plugin_log["id"]
        if job["job_type"] == "iteration_plan_suggestion_generate":
            result_summary, records_imported = run_iteration_plan_job(
                current_store,
                job=job,
                user=user,
            )
            if plugin_summary is not None:
                result_summary = {
                    **result_summary,
                    "execution_nodes": build_plugin_action_execution_nodes(
                        current_store,
                        job=job,
                        plugin_output_mapping=plugin_output_mapping,
                        plugin_records_imported=plugin_records_imported,
                        plugin_summary=plugin_summary,
                        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    ),
                    "plugin": plugin_summary,
                }
                records_imported += plugin_records_imported
        elif job["job_type"] == "plugin_action_invoke" and plugin_summary is not None:
            result_summary = {
                "execution_nodes": build_plugin_action_execution_nodes(
                    current_store,
                    job=job,
                    plugin_output_mapping=plugin_output_mapping,
                    plugin_records_imported=plugin_records_imported,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                ),
                "plugin": plugin_summary,
            }
            records_imported = plugin_records_imported
        elif job["job_type"] == "user_feedback_insight_extract" and plugin_summary is not None:
            result_summary, records_imported = run_user_feedback_insight_extract_job(
                current_store,
                job=job,
                plugin_summary=plugin_summary,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                user=user,
            )
        elif job["job_type"] == "code_repository_inspection" and plugin_summary is not None:
            if plugin_summary.get("status") != "succeeded":
                raise api_error(
                    502,
                    "PLUGIN_ACTION_FAILED",
                    "Code repository inspection plugin action failed",
                )
            inspection_result = execute_code_inspection_result_actions(
                current_store,
                collector_run_id=collector_run["id"],
                job=job,
                plugin_summary=plugin_summary,
                result_actions=job.get("result_actions") or [],
                run_id=run_id,
                user=user,
            )
            report = inspection_result["report"]
            records_imported = int(inspection_result["finding_count"])
            result_summary = {
                "bug_ids": inspection_result["bug_ids"],
                "execution_nodes": {
                    "bug_creation": {
                        "created_bug_ids": inspection_result["bug_ids"],
                        "label": "严重问题自动创建 Bug",
                        "records_imported": len(inspection_result["bug_ids"]),
                        "status": "succeeded",
                    },
                    "code_inspection_report": {
                        "finding_count": report["finding_count"],
                        "label": "代码审查表写入结果",
                        "report_id": report["id"],
                        "risk_level": report["risk_level"],
                        "severe_finding_count": report["severe_finding_count"],
                        "status": "succeeded",
                    },
                    "data_connection": build_data_connection_execution_node(
                        job=job,
                        plugin_summary=plugin_summary,
                        records_imported=records_imported,
                        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    ),
                    "notifications": {
                        "created_notification_ids": inspection_result["notification_ids"],
                        "label": "问题消息通知",
                        "records_imported": len(inspection_result["notification_ids"]),
                        "status": "succeeded",
                    },
                },
                "finding_count": report["finding_count"],
                "notification_ids": inspection_result["notification_ids"],
                "plugin": plugin_summary,
                "report_id": report["id"],
                "result_actions": inspection_result["result_actions"],
                "risk_level": report["risk_level"],
                "severe_finding_count": report["severe_finding_count"],
            }
        else:
            result_summary = {"message": "No handler implemented"}
            if plugin_summary is not None:
                result_summary["plugin"] = plugin_summary
                result_summary["execution_nodes"] = build_plugin_action_execution_nodes(
                    current_store,
                    job=job,
                    plugin_output_mapping=plugin_output_mapping,
                    plugin_records_imported=plugin_records_imported,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                )
            records_imported = plugin_records_imported
        status = "succeeded"
        error_code = None
        error_message = None
    except Exception as exc:
        status = "failed"
        error_code, error_message = exception_error_code_and_message(exc)
        result_summary = {}
        if job["job_type"] == "user_feedback_insight_extract" and plugin_summary is not None:
            source_row_count = records_imported_from_mapping(
                plugin_summary.get("response_summary") or {},
                {"records_imported_path": plugin_output_mapping.get("records_imported_path")},
            )
            result_summary = {
                "execution_nodes": {
                    "data_connection": build_data_connection_execution_node(
                        job=job,
                        plugin_summary=plugin_summary,
                        records_imported=source_row_count,
                        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    ),
                    "result_action": {
                        "label": "结果动作反馈内容",
                        "records_imported": 0,
                        "status": "not_run",
                        "write_target": plugin_output_mapping.get("write_target")
                        or "user_feedback_insights",
                    },
                    "skill_processing": {
                        "error_code": error_code,
                        "error_message": error_message,
                        "label": "Skill 处理后内容",
                        "model_gateway_called": True,
                        "model_gateway_config_id": job.get("model_gateway_config_id"),
                        "note": "数据连接已完成，但平台 AI 大模型处理失败。",
                        "processing_mode": "model_gateway_json_transform",
                        "skill_codes": skill_codes_for_job(current_store, job),
                        "skill_ids": list(job.get("skill_ids", [])),
                        "status": "failed",
                    },
                },
                "plugin": plugin_summary,
                "processing": {
                    "error_code": error_code,
                    "error_message": error_message,
                    "model_gateway_called": True,
                    "skill_codes": skill_codes_for_job(current_store, job),
                    "skill_ids": list(job.get("skill_ids", [])),
                },
                "write_target": plugin_output_mapping.get("write_target")
                or "user_feedback_insights",
            }
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
