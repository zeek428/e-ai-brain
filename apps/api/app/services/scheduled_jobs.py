from __future__ import annotations

import os
import threading
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.api.deps import api_error
from app.services.code_inspections import (
    execute_code_inspection_result_actions,
    sync_product_git_repository_store,
    validate_code_inspection_result_actions,
)
from app.services.iteration_planning import create_iteration_suggestions_response
from app.services.native_code_scanner import (
    NATIVE_CODE_SCAN_MODE,
    code_inspection_uses_native_scan,
    run_native_code_scan,
)
from app.services.operational_records import record_audit_event
from app.services.plugin_result_mapping import (
    records_imported_from_mapping,
    result_write_preview,
)
from app.services.plugins import (
    invoke_plugin_action_response,
    resolve_plugin_snapshot,
)
from app.services.scheduled_job_access import (
    require_admin,
    require_scheduled_job_runner,
    scheduled_job_matches_product_scope,
    scheduled_job_plugin_invocation_user,
)
from app.services.scheduled_job_ai_processing import (
    run_scheduled_job_ai_processing,
    skill_output_mapping_contract,
    skill_codes_for_job,
    validate_knowledge_document_ids,
    validate_skill_output_mapping_contract,
)
from app.services.scheduled_job_audit import (
    scheduled_job_audit_payload,
    scheduled_job_run_audit_payload,
)
from app.services.scheduled_job_catalog import (
    AI_REQUIRED_SCHEDULED_JOB_TYPES,
    scheduled_job_type_allows_create,
    scheduled_job_type_definition,
    scheduled_job_type_is_runnable,
)
from app.services.scheduled_job_common import ensure_enum, ensure_non_blank
from app.services.scheduled_job_config import (
    effective_scheduled_job_execution_mode,
    effective_scheduled_job_type,
    next_run_at,
    scheduled_job_config_with_code_inspection_defaults,
    scheduled_job_config_with_multi_refs,
    scheduled_job_data_connection_policy,
    scheduled_job_with_multi_refs,
)
from app.services.scheduled_job_constants import (
    SCHEDULED_JOB_RUN_TERMINAL_STATUSES,
    SCHEDULED_JOB_RUN_TRIGGER_TYPES,
)
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_native_scan import (
    execute_native_multi_code_inspection_summary,
    native_code_scan_repository_ids,
)
from app.services.scheduled_job_native_scan import (
    queued_native_scan_result_summary as native_scan_result_summary,
)
from app.services.scheduled_job_read_models import (
    list_scheduled_job_runs_response,
    list_scheduled_jobs_response,
    public_scheduled_job_run,
)
from app.services.scheduled_job_ref_validation import validate_job_refs, validate_plugin_refs
from app.services.scheduled_job_refs import (
    payload_field,
    scheduled_job_multi_ids,
)
from app.services.scheduled_job_runtime import (
    exception_error_code_and_message,
    resolve_plugin_input_mapping,
)
from app.services.scheduled_job_store import (
    delete_memory_record as _delete_memory_record,
)
from app.services.scheduled_job_store import (
    persist_record,
    snapshot,
    sync_ai_agent_store,
    sync_ai_skill_store,
    sync_reference_store,
    sync_scheduled_job_run_store,
    sync_scheduled_job_store,
)
from app.services.scheduled_job_store import (
    put_memory_record as _put_memory_record,
)
from app.services.scheduled_job_store import (
    read_memory_dict as _read_memory_dict,
)
from app.services.scheduled_job_templates import STANDARD_WIZARD_STEPS
from app.services.scheduled_job_user_feedback import (
    resolve_job_plugin_output_mapping,
    run_user_feedback_insight_extract_job,
)
from app.services.skill_packages import load_skill_package_snapshot

__all__ = [
    "list_scheduled_job_runs_response",
    "list_scheduled_jobs_response",
    "public_scheduled_job_run",
]


def scheduled_job_template_from_run_response(
    *,
    current_store: Any,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_run_store(current_store)
    run = _read_memory_dict(current_store, "scheduled_job_runs").get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job run not found")
    if run.get("status") != "succeeded":
        raise api_error(
            409,
            "SCHEDULED_JOB_RUN_NOT_SUCCESSFUL",
            "Only successful scheduled job runs can generate templates",
        )
    config = dict(run.get("config_snapshot") or {})
    job_name = str(config.get("name") or run.get("scheduled_job_id") or run_id)
    payload_keys = (
        "agent_id",
        "config_json",
        "cron_expression",
        "enabled",
        "execution_mode",
        "interval_seconds",
        "job_type",
        "knowledge_document_ids",
        "lock_ttl_seconds",
        "max_retry_count",
        "model_gateway_config_id",
        "plugin_action_id",
        "plugin_action_ids",
        "plugin_connection_id",
        "plugin_connection_ids",
        "plugin_input_mapping",
        "plugin_output_mapping",
        "product_id",
        "result_actions",
        "schedule_type",
        "skill_ids",
        "source_system",
        "timeout_seconds",
        "timezone",
    )
    payload_defaults = {
        key: config.get(key)
        for key in payload_keys
        if key in config and config.get(key) is not None
    }
    source = {
        "source_id": run_id,
        "source_type": "scheduled_job_run",
        "title": job_name,
    }
    config_json = dict(payload_defaults.get("config_json") or {})
    config_json["template_source"] = source
    payload_defaults["config_json"] = config_json
    payload_defaults["enabled"] = True
    payload_defaults["name"] = f"{job_name} 模板"
    return {
        "category": str(config.get("job_type") or "generated"),
        "code": f"generated_from_{run_id}",
        "description": f"由成功运行 {run_id} 反向生成，可作为新增定时作业模板。",
        "name": f"{job_name} 模板",
        "payload_defaults": payload_defaults,
        "recommended_scenarios": ["成功运行复用", "配置模板化", "快速创建同类任务"],
        "resource_selectors": {},
        "source_run_id": run_id,
        "template_version": "generated-v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    }


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
    ensure_scheduled_job_type_available_for_create(job_type)
    (
        plugin_action_id,
        plugin_connection_id,
        plugin_action_ids,
        plugin_connection_ids,
    ) = validate_plugin_refs(current_store, payload)
    result_actions = validate_code_inspection_result_actions(
        payload.result_actions if job_type == "code_repository_inspection" else [],
    )
    knowledge_document_ids = validate_knowledge_document_ids(
        current_store,
        payload.knowledge_document_ids,
        user=user,
    )
    config_json = scheduled_job_config_with_code_inspection_defaults(
        current_store,
        config_json=payload.config_json,
        job_type=job_type,
        product_id=payload.product_id,
    )
    now = datetime.now(UTC).isoformat()
    job_id = current_store.new_id("scheduled_job")
    job = {
        "agent_id": agent_id,
        "config_json": scheduled_job_config_with_multi_refs(
            config_json,
            plugin_action_ids=plugin_action_ids,
            plugin_connection_ids=plugin_connection_ids,
        ),
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
        "plugin_action_ids": plugin_action_ids,
        "plugin_connection_id": plugin_connection_id,
        "plugin_connection_ids": plugin_connection_ids,
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
    _put_memory_record(current_store, "scheduled_jobs", job)
    audit_event = record_audit_event(
        current_store,
        event_type="scheduled_job.created",
        actor_id=user["id"],
        subject_type="scheduled_job",
        subject_id=job_id,
        payload=scheduled_job_audit_payload(job),
    )
    persist_record(
        current_store,
        "save_scheduled_job_record",
        job,
        audit_event=audit_event,
    )
    return scheduled_job_with_multi_refs(job)


def dry_run_scheduled_job_response(
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
    ensure_scheduled_job_type_available_for_create(job_type)
    (
        plugin_action_id,
        plugin_connection_id,
        plugin_action_ids,
        plugin_connection_ids,
    ) = validate_plugin_refs(current_store, payload)
    config_json = scheduled_job_config_with_code_inspection_defaults(
        current_store,
        config_json=payload.config_json,
        job_type=job_type,
        product_id=payload.product_id,
    )
    job = {
        "agent_id": agent_id,
        "config_json": scheduled_job_config_with_multi_refs(
            config_json,
            plugin_action_ids=plugin_action_ids,
            plugin_connection_ids=plugin_connection_ids,
        ),
        "execution_mode": execution_mode,
        "id": current_store.new_id("scheduled_job_dry_run"),
        "job_type": job_type,
        "knowledge_document_ids": validate_knowledge_document_ids(
            current_store,
            payload.knowledge_document_ids,
            user=user,
        ),
        "model_gateway_config_id": model_gateway_config_id,
        "name": ensure_non_blank(payload.name, "name"),
        "plugin_action_id": plugin_action_id,
        "plugin_action_ids": plugin_action_ids,
        "plugin_connection_id": plugin_connection_id,
        "plugin_connection_ids": plugin_connection_ids,
        "plugin_input_mapping": payload.plugin_input_mapping,
        "plugin_output_mapping": payload.plugin_output_mapping,
        "product_id": payload.product_id,
        "skill_ids": skill_ids,
        "source_system": payload.source_system,
        "timezone": payload.timezone,
    }
    resolved_input_mapping = resolve_plugin_input_mapping(
        payload.plugin_input_mapping or {},
        job,
    )
    if code_inspection_uses_native_scan(job):
        resolved_input_mapping = {
            "branch": config_json.get("branch"),
            "repository_id": config_json.get("repository_id"),
            "scan_mode": NATIVE_CODE_SCAN_MODE,
        }
        plugin_summary = run_native_code_scan(
            current_store,
            job=job,
            run_id=job["id"],
            user=user,
        )
    else:
        plugin_summary, _plugin_summaries = invoke_job_data_connections(
            current_store,
            job=job,
            resolved_plugin_input_mapping=resolved_input_mapping,
            run_id=job["id"],
            trigger_type="dry_run",
            user=user,
        )
    output_mapping = resolve_job_plugin_output_mapping(current_store, job)
    if plugin_summary is not None and code_inspection_uses_native_scan(job):
        native_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
        native_findings = native_json.get("findings") if isinstance(native_json, dict) else []
        records_imported = len(native_findings) if isinstance(native_findings, list) else 0
    else:
        records_imported = (
            JobExecutionEngine.plugin_records_imported_from_result(plugin_summary, output_mapping)
            if plugin_summary is not None
            else 0
        )
    will_call_model_gateway = JobExecutionEngine.uses_ai_processing(
        job,
        ai_required_job_types=AI_REQUIRED_SCHEDULED_JOB_TYPES,
    )
    output_schema = {}
    mapping_contract = {
        "checked_paths": [],
        "invalid_fields": [],
        "output_schema": {},
        "status": "not_required",
    }
    mapping_status = "not_required"
    if will_call_model_gateway:
        mapping_contract = skill_output_mapping_contract(
            current_store,
            job=job,
            output_mapping=output_mapping,
        )
        output_schema = validate_skill_output_mapping_contract(
            current_store,
            job=job,
            output_mapping=output_mapping,
        )
        mapping_status = mapping_contract["status"]
    response_summary = plugin_summary.get("response_summary") if plugin_summary else {}
    result_actions = []
    for action_id in plugin_action_ids:
        action = _read_memory_dict(current_store, "plugin_actions").get(action_id) or {}
        action_mapping = action.get("result_mapping") if isinstance(action, dict) else {}
        mapping = action_mapping if isinstance(action_mapping, dict) else {}
        preview = result_write_preview(response_summary or {}, mapping or output_mapping)
        result_actions.append(
            {
                "action_code": action.get("code"),
                "action_id": action_id,
                "action_name": action.get("name"),
                "write_preview": preview,
                "write_target": (mapping or output_mapping).get(
                    "write_target",
                    "scheduled_job_result",
                ),
                "write_target_label": preview.get("write_target_label"),
            },
        )
    data_node = (
        JobExecutionEngine.data_connection_execution_node(
            job=job,
            plugin_summary=plugin_summary,
            records_imported=records_imported,
            resolved_plugin_input_mapping=resolved_input_mapping,
        )
        if plugin_summary is not None
        else {"label": "数据连接获取内容", "records_imported": 0, "status": "not_configured"}
    )
    return {
        "job_type": job_type,
        "status": (
            "succeeded"
            if plugin_summary is None or plugin_summary.get("status") == "succeeded"
            else "failed"
        ),
        "stages": {
            "ai_processing": {
                "agent_id": agent_id,
                "mapping_contract": mapping_contract,
                "mapping_status": mapping_status,
                "model_gateway_config_id": model_gateway_config_id,
                "output_schema": output_schema,
                "skill_ids": skill_ids,
                "will_call_model_gateway": will_call_model_gateway,
            },
            "data_connection": data_node,
            "result_actions": result_actions,
        },
    }


def patch_scheduled_job_response(
    *,
    current_store: Any,
    job_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_store(current_store)
    job = _read_memory_dict(current_store, "scheduled_jobs").get(job_id)
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
    (
        plugin_action_id,
        plugin_connection_id,
        plugin_action_ids,
        plugin_connection_ids,
    ) = validate_plugin_refs(current_store, draft)
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
    updates["plugin_action_ids"] = plugin_action_ids
    updates["plugin_connection_id"] = plugin_connection_id
    updates["plugin_connection_ids"] = plugin_connection_ids
    config_json = scheduled_job_config_with_code_inspection_defaults(
        current_store,
        config_json=payload_field(draft, "config_json", {}),
        job_type=job_type,
        product_id=payload_field(draft, "product_id"),
    )
    updates["config_json"] = scheduled_job_config_with_multi_refs(
        config_json,
        plugin_action_ids=plugin_action_ids,
        plugin_connection_ids=plugin_connection_ids,
    )
    updates["result_actions"] = result_actions
    if {"schedule_type", "interval_seconds", "cron_expression"} & updates.keys():
        updates["next_run_at"] = next_run_at(draft)
    if "enabled" in updates:
        updates["status"] = "active" if updates["enabled"] else "disabled"
    job = {**job, **updates, "updated_at": datetime.now(UTC).isoformat()}
    _put_memory_record(current_store, "scheduled_jobs", job)
    audit_event = record_audit_event(
        current_store,
        event_type="scheduled_job.updated",
        actor_id=user["id"],
        subject_type="scheduled_job",
        subject_id=job_id,
        payload=scheduled_job_audit_payload(job),
    )
    persist_record(
        current_store,
        "save_scheduled_job_record",
        job,
        audit_event=audit_event,
    )
    return scheduled_job_with_multi_refs(job)


def delete_scheduled_job_response(
    *,
    current_store: Any,
    job_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_store(current_store)
    job = _read_memory_dict(current_store, "scheduled_jobs").get(job_id)
    if job is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    _delete_memory_record(current_store, "scheduled_jobs", job_id)
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
    agent = (
        _read_memory_dict(current_store, "ai_agents").get(job.get("agent_id"))
        if job.get("agent_id")
        else None
    )
    skills = []
    for skill_id in job.get("skill_ids", []):
        skill = dict(_read_memory_dict(current_store, "ai_skills")[skill_id])
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
    _put_memory_record(current_store, "collector_runs", collector_run)
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
    collector_status = (
        "succeeded"
        if status == "succeeded"
        else "cancelled"
        if status == "cancelled"
        else "failed"
    )
    updated = {
        **collector_run,
        "error_message": error_message,
        "finished_at": now,
        "records_imported": records_imported,
        "status": collector_status,
        "updated_at": now,
    }
    _put_memory_record(current_store, "collector_runs", updated)
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


def cancelled_scheduled_job_run_if_requested(
    current_store: Any,
    *,
    collector_run: dict[str, Any],
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    latest_run = _read_memory_dict(current_store, "scheduled_job_runs").get(run_id)
    if latest_run is None or latest_run.get("status") != "cancelled":
        return None
    complete_collector_run(
        current_store,
        collector_run=collector_run,
        error_message="Scheduled job run was cancelled",
        records_imported=0,
        status="cancelled",
        user=user,
    )
    return public_scheduled_job_run(latest_run, current_store=current_store)


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


def plugin_summary_from_log(current_store: Any, plugin_log: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": plugin_log.get("action_id"),
        "connection_environment": (
            _read_memory_dict(current_store, "plugin_connections").get(
                plugin_log.get("connection_id"),
            )
            or {}
        ).get("environment"),
        "connection_id": plugin_log.get("connection_id"),
        "error_code": plugin_log.get("error_code"),
        "error_message": plugin_log.get("error_message"),
        "invocation_log_id": plugin_log["id"],
        "latency_ms": plugin_log.get("latency_ms"),
        "request_summary": plugin_log.get("request_summary") or {},
        "response_summary": plugin_log.get("response_summary") or {},
        "status": plugin_log["status"],
    }


def invoke_job_data_connections(
    current_store: Any,
    *,
    job: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    run_id: str,
    trigger_type: str,
    user: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not job.get("plugin_action_id"):
        return None, []
    connection_ids = scheduled_job_multi_ids(
        job,
        "plugin_connection_ids",
        "plugin_connection_id",
    )
    if not connection_ids and job.get("plugin_connection_id"):
        connection_ids = [str(job["plugin_connection_id"])]
    policy = scheduled_job_data_connection_policy(job)
    summaries: list[dict[str, Any]] = []
    for connection_id in connection_ids or [None]:
        job_config = job.get("config_json") or {}
        linked_scheduled_job_id = None if trigger_type == "dry_run" else job["id"]
        linked_scheduled_job_run_id = None if trigger_type == "dry_run" else run_id
        plugin_log = invoke_plugin_action_response(
            action_id=job["plugin_action_id"],
            connection_id=connection_id,
            current_store=current_store,
            input_payload={
                "branch": resolved_plugin_input_mapping.get("branch") or job_config.get("branch"),
                "config": job.get("config_json") or {},
                "input_mapping": resolved_plugin_input_mapping,
                "job_id": job["id"],
                "product_id": job.get("product_id"),
                "repository_id": (
                    resolved_plugin_input_mapping.get("repository_id")
                    or job_config.get("repository_id")
                ),
                "timezone": job.get("timezone") or "UTC",
            },
            raise_on_failed=False,
            scheduled_job_id=linked_scheduled_job_id,
            scheduled_job_run_id=linked_scheduled_job_run_id,
            trigger_type=trigger_type,
            user=scheduled_job_plugin_invocation_user(user),
        )
        summary = plugin_summary_from_log(current_store, plugin_log)
        summaries.append(summary)
        if summary["status"] != "succeeded" and policy["failure_policy"] == "fail_fast":
            break
    merged = JobExecutionEngine.merged_plugin_summary(
        summaries,
        failure_policy=policy["failure_policy"],
        merge_strategy=policy["merge_strategy"],
        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
    )
    return merged, summaries


def scheduled_job_uses_async_worker(job: dict[str, Any]) -> bool:
    if job.get("job_type") != "code_repository_inspection":
        return False
    if not code_inspection_uses_native_scan(job):
        return False
    config = job.get("config_json") or {}
    return config.get("async_execution") is not False


def queued_native_scan_result_summary(
    current_store: Any,
    *,
    job: dict[str, Any],
) -> dict[str, Any]:
    job_config = job.get("config_json") or {}
    repository_id = job_config.get("repository_id")
    sync_product_git_repository_store(current_store, job.get("product_id"))
    repository = (
        _read_memory_dict(current_store, "product_git_repositories").get(str(repository_id))
        or {}
    )
    return native_scan_result_summary(
        job=job,
        repository=repository,
        skill_codes=skill_codes_for_job(current_store, job),
    )


def scheduled_job_async_worker_disabled() -> bool:
    return str(os.getenv("SCHEDULED_JOB_ASYNC_WORKER_DISABLED") or "").lower() in {
        "1",
        "true",
        "yes",
    }


def _scheduled_job_worker_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        **user,
        "id": user.get("id") or "system_scheduled_job_worker",
        "roles": list(set(user.get("roles") or []) | {"admin"}),
    }


def enqueue_scheduled_job_run_worker(
    current_store: Any,
    *,
    run_id: str,
    user: dict[str, Any],
) -> None:
    if scheduled_job_async_worker_disabled():
        return
    worker_user = _scheduled_job_worker_user(user)
    thread = threading.Thread(
        target=execute_queued_scheduled_job_run_response,
        kwargs={"current_store": current_store, "run_id": run_id, "user": worker_user},
        name=f"scheduled-job-worker-{run_id}",
        daemon=True,
    )
    thread.start()


def execute_queued_scheduled_job_run_response(
    *,
    current_store: Any,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_store(current_store)
    sync_ai_agent_store(current_store)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    sync_scheduled_job_run_store(current_store)
    run = _read_memory_dict(current_store, "scheduled_job_runs").get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job run not found")
    if run.get("status") in SCHEDULED_JOB_RUN_TERMINAL_STATUSES:
        raise api_error(409, "SCHEDULED_JOB_RUN_STATE_INVALID", "Terminal run cannot be executed")
    if run.get("status") != "queued":
        raise api_error(409, "SCHEDULED_JOB_RUN_STATE_INVALID", "Only queued runs can be executed")
    job = _read_memory_dict(current_store, "scheduled_jobs").get(run.get("scheduled_job_id"))
    if job is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    if not scheduled_job_uses_async_worker(job):
        raise api_error(400, "VALIDATION_ERROR", "Scheduled job run is not async native code scan")
    if not job.get("enabled"):
        raise api_error(409, "SCHEDULED_JOB_DISABLED", "Scheduled job is disabled")

    now = datetime.now(UTC).isoformat()
    collector_run = _read_memory_dict(current_store, "collector_runs").get(
        run.get("collector_run_id"),
    )
    if collector_run is None:
        collector_run = create_collector_run_for_job(
            current_store,
            job=job,
            run_id=run_id,
            status="running",
            user=user,
        )
        run["collector_run_id"] = collector_run["id"]
    run = {
        **run,
        "result_summary": queued_native_scan_result_summary(current_store, job=job),
        "started_at": now,
        "status": "running",
        "updated_at": now,
    }
    _put_memory_record(current_store, "scheduled_job_runs", run)
    persist_record(current_store, "save_scheduled_job_run_record", run)

    plugin_summary = None
    plugin_output_mapping: dict[str, Any] = {}
    records_imported = 0
    resolved_plugin_input_mapping: dict[str, Any] = {}
    try:
        native_repository_ids = native_code_scan_repository_ids(job)
        if len(native_repository_ids) > 1:
            result_summary, records_imported = execute_native_multi_code_inspection_summary(
                current_store,
                collector_run_id=collector_run["id"],
                job=job,
                repository_ids=native_repository_ids,
                run_id=run_id,
                skill_codes=skill_codes_for_job(current_store, job),
                user=user,
            )
            cancelled_run = cancelled_scheduled_job_run_if_requested(
                current_store,
                collector_run=collector_run,
                run_id=run_id,
                user=user,
            )
            if cancelled_run is not None:
                return cancelled_run
            status = "succeeded"
            error_code = None
            error_message = None
            raise StopIteration
        job_config = job.get("config_json") or {}
        resolved_plugin_input_mapping = {
            "branch": job_config.get("branch"),
            "repository_id": job_config.get("repository_id"),
            "scan_mode": NATIVE_CODE_SCAN_MODE,
        }
        plugin_summary = run_native_code_scan(
            current_store,
            job=job,
            run_id=run_id,
            user=user,
        )
        cancelled_run = cancelled_scheduled_job_run_if_requested(
            current_store,
            collector_run=collector_run,
            run_id=run_id,
            user=user,
        )
        if cancelled_run is not None:
            return cancelled_run
        if plugin_summary.get("status") != "succeeded":
            raise api_error(
                502,
                "PLUGIN_ACTION_FAILED",
                "Code repository inspection plugin action failed",
            )
        plugin_output_mapping = resolve_job_plugin_output_mapping(current_store, job)
        source_response_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
        if not isinstance(source_response_json, dict):
            source_response_json = {}
        source_findings = source_response_json.get("findings")
        source_finding_count = len(source_findings) if isinstance(source_findings, list) else 0
        ai_processing = None
        effective_plugin_summary = plugin_summary
        if JobExecutionEngine.uses_ai_processing(
            job,
            ai_required_job_types=AI_REQUIRED_SCHEDULED_JOB_TYPES,
        ):
            ai_processing = run_scheduled_job_ai_processing(
                current_store,
                job=job,
                output_mapping=plugin_output_mapping,
                source_response_json=source_response_json,
                source_row_count=source_finding_count,
                user=user,
            )
            effective_plugin_summary = (
                JobExecutionEngine.code_inspection_plugin_summary_for_ai_output(
                    plugin_summary,
                    ai_processing=ai_processing,
                )
            )
        inspection_result = execute_code_inspection_result_actions(
            current_store,
            collector_run_id=collector_run["id"],
            job=job,
            plugin_summary=effective_plugin_summary,
            result_actions=job.get("result_actions") or [],
            run_id=run_id,
            user=user,
        )
        report = inspection_result["report"]
        records_imported = int(inspection_result["finding_count"])
        skill_processing_node = JobExecutionEngine.code_inspection_skill_processing_node(
            ai_processing=ai_processing,
            job=job,
            output_mapping=plugin_output_mapping,
            skill_codes=skill_codes_for_job(current_store, job),
            source_finding_count=source_finding_count,
        )
        result_action_node = JobExecutionEngine.code_inspection_result_action_node(
            inspection_result=inspection_result,
            report=report,
        )
        native_scan_summary = (plugin_summary.get("response_summary") or {}).get("native_scan")
        result_summary = {
            "bug_ids": inspection_result["bug_ids"],
            "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
            "execution_nodes": {
                "bug_creation": {
                    "created_bug_ids": inspection_result["bug_ids"],
                    "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
                    "label": "严重问题自动创建 Bug",
                    "records_imported": len(inspection_result["bug_ids"]),
                    "status": "succeeded",
                },
                "task_creation": {
                    "created_task_ids": inspection_result.get("task_ids") or [],
                    "label": "严重问题自动创建整改任务",
                    "records_imported": len(inspection_result.get("task_ids") or []),
                    "status": "succeeded",
                },
                "code_inspection_report": {
                    "finding_count": report["finding_count"],
                    "label": "代码巡检报告写入结果",
                    "report_id": report["id"],
                    "risk_level": report["risk_level"],
                    "severe_finding_count": report["severe_finding_count"],
                    "status": "succeeded",
                },
                "data_connection": JobExecutionEngine.data_connection_execution_node(
                    job=job,
                    plugin_summary=plugin_summary,
                    records_imported=source_finding_count,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                ),
                "native_scan": {
                    **(native_scan_summary if isinstance(native_scan_summary, dict) else {}),
                    "label": "本地完整代码静态扫描",
                    "records_imported": source_finding_count,
                    "scan_mode": NATIVE_CODE_SCAN_MODE,
                    "status": "succeeded",
                },
                "notifications": {
                    "created_notification_ids": inspection_result["notification_ids"],
                    "label": "问题消息通知",
                    "records_imported": len(inspection_result["notification_ids"]),
                    "status": "succeeded",
                },
                "result_action": result_action_node,
                "result_actions": inspection_result["action_results"],
                "skill_processing": skill_processing_node,
            },
            "finding_count": report["finding_count"],
            "notification_ids": inspection_result["notification_ids"],
            "plugin": effective_plugin_summary,
            "processing": {
                "async_worker": True,
                "model_gateway_called": ai_processing is not None,
                "skill_codes": skill_codes_for_job(current_store, job),
                "skill_ids": list(job.get("skill_ids", [])),
            },
            "report_id": report["id"],
            "result_actions": inspection_result["result_actions"],
            "risk_level": report["risk_level"],
            "severe_finding_count": report["severe_finding_count"],
            "task_ids": inspection_result.get("task_ids") or [],
        }
        status = "succeeded"
        error_code = None
        error_message = None
    except StopIteration:
        pass
    except Exception as exc:
        status = "failed"
        error_code, error_message = exception_error_code_and_message(exc)
        result_summary = {
            "execution_nodes": {
                "native_scan": {
                    "error_code": error_code,
                    "error_message": error_message,
                    "label": "本地完整代码静态扫描",
                    "records_imported": 0,
                    "scan_mode": NATIVE_CODE_SCAN_MODE,
                    "status": "failed",
                },
                "result_action": {
                    "label": "结果动作反馈内容",
                    "records_imported": 0,
                    "status": "not_run",
                    "write_target": "code_inspection_reports",
                },
            },
            "plugin": plugin_summary,
            "processing": {
                "async_worker": True,
                "error_code": error_code,
                "error_message": error_message,
                "model_gateway_called": False,
                "skill_codes": skill_codes_for_job(current_store, job),
                "skill_ids": list(job.get("skill_ids", [])),
            },
            "write_target": "code_inspection_reports",
        }
        records_imported = 0

    finished_at = datetime.now(UTC).isoformat()
    updated_at = datetime.now(UTC).isoformat()
    run = {
        **run,
        "error_code": error_code,
        "error_message": error_message,
        "finished_at": finished_at,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": status,
        "updated_at": updated_at,
    }
    _put_memory_record(current_store, "scheduled_job_runs", run)
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
        "updated_at": updated_at,
    }
    _put_memory_record(current_store, "scheduled_jobs", job_update)
    persist_record(current_store, "save_scheduled_job_record", job_update)
    persist_record(current_store, "save_scheduled_job_run_record", run)
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{status}",
        actor_id=user["id"],
        subject_type="scheduled_job_run",
        subject_id=run_id,
        payload=scheduled_job_run_audit_payload(job=job, run=run),
    )
    persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
        audit_event=audit_event,
    )
    return public_scheduled_job_run(run, current_store=current_store)


def run_scheduled_job_response(
    *,
    current_store: Any,
    job_id: str,
    source_run_id: str | None,
    trigger_type: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_scheduled_job_runner(user)
    ensure_enum(trigger_type, SCHEDULED_JOB_RUN_TRIGGER_TYPES, "scheduled job run trigger_type")
    sync_scheduled_job_store(current_store)
    sync_ai_agent_store(current_store)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    job = _read_memory_dict(current_store, "scheduled_jobs").get(job_id)
    if job is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    if not scheduled_job_matches_product_scope(job, user):
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    source_run = None
    if source_run_id:
        sync_scheduled_job_run_store(current_store, scheduled_job_id=job_id)
        source_run = _read_memory_dict(current_store, "scheduled_job_runs").get(source_run_id)
        if source_run is None:
            raise api_error(404, "NOT_FOUND", "Source scheduled job run not found")
        if source_run.get("scheduled_job_id") != job_id:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "source_run_id must belong to the scheduled job",
            )
        if trigger_type != "manual_rerun":
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "source_run_id is only supported for manual_rerun",
            )
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
    ensure_scheduled_job_type_runnable(str(job["job_type"]))
    native_code_inspection = (
        job["job_type"] == "code_repository_inspection"
        and code_inspection_uses_native_scan(job)
    )
    native_repository_ids = (
        native_code_scan_repository_ids(job) if native_code_inspection else []
    )
    native_multi_inspection = native_code_inspection and len(native_repository_ids) > 1
    use_async_worker = scheduled_job_uses_async_worker(job)
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
        "result_summary": (
            queued_native_scan_result_summary(current_store, job=job) if use_async_worker else {}
        ),
        "scheduled_for": now,
        "scheduled_job_id": job_id,
        "source_run_id": source_run.get("id") if source_run else None,
        "started_at": None if use_async_worker else now,
        "status": "queued" if use_async_worker else "running",
        "trigger_type": trigger_type,
        "updated_at": now,
    }
    _put_memory_record(current_store, "scheduled_job_runs", run)
    collector_run = create_collector_run_for_job(
        current_store,
        job=job,
        run_id=run_id,
        status=run["status"],
        user=user,
    )
    run["collector_run_id"] = collector_run["id"]
    persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
    )
    if use_async_worker:
        audit_event = record_audit_event(
            current_store,
            event_type="scheduled_job_run.queued",
            actor_id=user["id"],
            subject_type="scheduled_job_run",
            subject_id=run_id,
            payload=scheduled_job_run_audit_payload(job=job, run=run),
        )
        persist_record(
            current_store,
            "save_scheduled_job_run_record",
            run,
            audit_event=audit_event,
        )
        enqueue_scheduled_job_run_worker(current_store, run_id=run_id, user=user)
        return public_scheduled_job_run(run, current_store=current_store)
    plugin_summary = None
    plugin_output_mapping: dict[str, Any] = {}
    plugin_records_imported = 0
    resolved_plugin_input_mapping: dict[str, Any] = {}
    try:
        handled_job = False
        if native_multi_inspection:
            result_summary, records_imported = execute_native_multi_code_inspection_summary(
                current_store,
                collector_run_id=collector_run["id"],
                job=job,
                repository_ids=native_repository_ids,
                run_id=run_id,
                skill_codes=skill_codes_for_job(current_store, job),
                user=user,
            )
            handled_job = True
        elif native_code_inspection:
            job_config = job.get("config_json") or {}
            resolved_plugin_input_mapping = {
                "branch": job_config.get("branch"),
                "repository_id": job_config.get("repository_id"),
                "scan_mode": NATIVE_CODE_SCAN_MODE,
            }
            plugin_summary = run_native_code_scan(
                current_store,
                job=job,
                run_id=run_id,
                user=user,
            )
            plugin_output_mapping = resolve_job_plugin_output_mapping(current_store, job)
            native_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
            native_findings = native_json.get("findings") if isinstance(native_json, dict) else []
            plugin_records_imported = (
                len(native_findings) if isinstance(native_findings, list) else 0
            )
        elif job.get("plugin_action_id"):
            resolved_plugin_input_mapping = resolve_plugin_input_mapping(
                job.get("plugin_input_mapping") or {},
                job,
            )
            plugin_summary, _plugin_summaries = invoke_job_data_connections(
                current_store,
                job=job,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                run_id=run_id,
                trigger_type=trigger_type,
                user=user,
            )
            plugin_output_mapping = resolve_job_plugin_output_mapping(current_store, job)
            if plugin_summary is not None:
                plugin_records_imported = (
                    JobExecutionEngine.plugin_records_imported_from_result(
                        plugin_summary,
                        plugin_output_mapping,
                    )
                )
                run["plugin_invocation_log_id"] = plugin_summary.get("invocation_log_id")
                if plugin_summary.get("status") == "failed":
                    raise api_error(
                        502,
                        plugin_summary.get("error_code") or "PLUGIN_ACTION_FAILED",
                        plugin_summary.get("error_message")
                        or "Scheduled job data connection failed",
                    )
        if handled_job:
            pass
        elif job["job_type"] == "iteration_plan_suggestion_generate":
            result_summary, records_imported = run_iteration_plan_job(
                current_store,
                job=job,
                user=user,
            )
            if plugin_summary is not None:
                result_summary = {
                    **result_summary,
                    "execution_nodes": JobExecutionEngine.plugin_action_execution_nodes(
                        job=job,
                        plugin_output_mapping=plugin_output_mapping,
                        plugin_records_imported=plugin_records_imported,
                        plugin_summary=plugin_summary,
                        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                        skill_codes=skill_codes_for_job(current_store, job),
                    ),
                    "plugin": plugin_summary,
                }
                records_imported += plugin_records_imported
        elif job["job_type"] == "plugin_action_invoke" and plugin_summary is not None:
            result_summary = {
                "execution_nodes": JobExecutionEngine.plugin_action_execution_nodes(
                    job=job,
                    plugin_output_mapping=plugin_output_mapping,
                    plugin_records_imported=plugin_records_imported,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    skill_codes=skill_codes_for_job(current_store, job),
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
            source_response_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
            if not isinstance(source_response_json, dict):
                source_response_json = {}
            code_inspection_output_mapping = resolve_job_plugin_output_mapping(current_store, job)
            if native_code_inspection:
                source_findings = source_response_json.get("findings")
                source_finding_count = (
                    len(source_findings) if isinstance(source_findings, list) else 0
                )
            else:
                source_finding_count = records_imported_from_mapping(
                    plugin_summary.get("response_summary") or {},
                    {
                        "records_imported_path": code_inspection_output_mapping.get(
                            "findings_path",
                        )
                        or code_inspection_output_mapping.get("records_imported_path")
                    },
                )
            ai_processing = None
            effective_plugin_summary = plugin_summary
            if JobExecutionEngine.uses_ai_processing(
                job,
                ai_required_job_types=AI_REQUIRED_SCHEDULED_JOB_TYPES,
            ):
                ai_processing = run_scheduled_job_ai_processing(
                    current_store,
                    job=job,
                    output_mapping=code_inspection_output_mapping,
                    source_response_json=source_response_json,
                    source_row_count=source_finding_count,
                    user=user,
                )
                effective_plugin_summary = (
                    JobExecutionEngine.code_inspection_plugin_summary_for_ai_output(
                        plugin_summary,
                        ai_processing=ai_processing,
                    )
                )
            inspection_result = execute_code_inspection_result_actions(
                current_store,
                collector_run_id=collector_run["id"],
                job=job,
                plugin_summary=effective_plugin_summary,
                result_actions=job.get("result_actions") or [],
                run_id=run_id,
                user=user,
            )
            report = inspection_result["report"]
            records_imported = int(inspection_result["finding_count"])
            skill_processing_node = (
                JobExecutionEngine.code_inspection_skill_processing_node(
                    ai_processing=ai_processing,
                    job=job,
                    output_mapping=code_inspection_output_mapping,
                    skill_codes=skill_codes_for_job(current_store, job),
                    source_finding_count=source_finding_count,
                )
            )
            result_action_node = JobExecutionEngine.code_inspection_result_action_node(
                inspection_result=inspection_result,
                report=report,
            )
            native_scan_summary = (
                (plugin_summary.get("response_summary") or {}).get("native_scan")
                if native_code_inspection
                else None
            )
            result_summary = {
                "bug_ids": inspection_result["bug_ids"],
                "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
                "execution_nodes": {
                    "bug_creation": {
                        "created_bug_ids": inspection_result["bug_ids"],
                        "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
                        "label": "严重问题自动创建 Bug",
                        "records_imported": len(inspection_result["bug_ids"]),
                        "status": "succeeded",
                    },
                    "task_creation": {
                        "created_task_ids": inspection_result.get("task_ids") or [],
                        "label": "严重问题自动创建整改任务",
                        "records_imported": len(inspection_result.get("task_ids") or []),
                        "status": "succeeded",
                    },
                    "code_inspection_report": {
                        "finding_count": report["finding_count"],
                        "label": "代码巡检报告写入结果",
                        "report_id": report["id"],
                        "risk_level": report["risk_level"],
                        "severe_finding_count": report["severe_finding_count"],
                        "status": "succeeded",
                    },
                    "data_connection": JobExecutionEngine.data_connection_execution_node(
                        job=job,
                        plugin_summary=plugin_summary,
                        records_imported=source_finding_count,
                        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    ),
                    **(
                        {
                            "native_scan": {
                                **(
                                    native_scan_summary
                                    if isinstance(native_scan_summary, dict)
                                    else {}
                                ),
                                "label": "本地完整代码静态扫描",
                                "records_imported": source_finding_count,
                                "scan_mode": NATIVE_CODE_SCAN_MODE,
                                "status": "succeeded",
                            },
                        }
                        if native_code_inspection
                        else {}
                    ),
                    "notifications": {
                        "created_notification_ids": inspection_result["notification_ids"],
                        "label": "问题消息通知",
                        "records_imported": len(inspection_result["notification_ids"]),
                        "status": "succeeded",
                    },
                    "result_action": result_action_node,
                    "result_actions": inspection_result["action_results"],
                    "skill_processing": skill_processing_node,
                },
                "finding_count": report["finding_count"],
                "notification_ids": inspection_result["notification_ids"],
                "plugin": effective_plugin_summary,
                "processing": {
                    "model_gateway_called": ai_processing is not None,
                    "skill_codes": skill_codes_for_job(current_store, job),
                    "skill_ids": list(job.get("skill_ids", [])),
                },
                "report_id": report["id"],
                "result_actions": inspection_result["result_actions"],
                "risk_level": report["risk_level"],
                "severe_finding_count": report["severe_finding_count"],
                "task_ids": inspection_result.get("task_ids") or [],
            }
        else:
            result_summary = {"message": "No handler implemented"}
            if plugin_summary is not None:
                result_summary["plugin"] = plugin_summary
                result_summary["execution_nodes"] = (
                    JobExecutionEngine.plugin_action_execution_nodes(
                    job=job,
                    plugin_output_mapping=plugin_output_mapping,
                    plugin_records_imported=plugin_records_imported,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    skill_codes=skill_codes_for_job(current_store, job),
                    )
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
                    "data_connection": JobExecutionEngine.data_connection_execution_node(
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
        elif job["job_type"] == "code_repository_inspection" and plugin_summary is not None:
            code_inspection_output_mapping = resolve_job_plugin_output_mapping(current_store, job)
            source_finding_count = records_imported_from_mapping(
                plugin_summary.get("response_summary") or {},
                {
                    "records_imported_path": code_inspection_output_mapping.get(
                        "findings_path",
                    )
                    or code_inspection_output_mapping.get("records_imported_path")
                },
            )
            result_summary = {
                "execution_nodes": {
                    "data_connection": JobExecutionEngine.data_connection_execution_node(
                        job=job,
                        plugin_summary=plugin_summary,
                        records_imported=source_finding_count,
                        resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    ),
                    "result_action": {
                        "label": "结果动作反馈内容",
                        "records_imported": 0,
                        "status": "not_run",
                        "write_target": "code_inspection_reports",
                    },
                    "skill_processing": {
                        "error_code": error_code,
                        "error_message": error_message,
                        "label": "Skill 处理后内容",
                        "model_gateway_called": JobExecutionEngine.uses_ai_processing(
                            job,
                            ai_required_job_types=AI_REQUIRED_SCHEDULED_JOB_TYPES,
                        ),
                        "model_gateway_config_id": job.get("model_gateway_config_id"),
                        "note": "数据连接已完成，但代码巡检 AI 处理或结果写入失败。",
                        "processing_mode": "model_gateway_json_transform"
                        if JobExecutionEngine.uses_ai_processing(
                            job,
                            ai_required_job_types=AI_REQUIRED_SCHEDULED_JOB_TYPES,
                        )
                        else "plugin_structured_output",
                        "skill_codes": skill_codes_for_job(current_store, job),
                        "skill_ids": list(job.get("skill_ids", [])),
                        "status": "failed",
                    },
                },
                "plugin": plugin_summary,
                "processing": {
                    "error_code": error_code,
                    "error_message": error_message,
                    "model_gateway_called": JobExecutionEngine.uses_ai_processing(
                        job,
                        ai_required_job_types=AI_REQUIRED_SCHEDULED_JOB_TYPES,
                    ),
                    "skill_codes": skill_codes_for_job(current_store, job),
                    "skill_ids": list(job.get("skill_ids", [])),
                },
                "write_target": "code_inspection_reports",
            }
        elif plugin_summary is not None:
            result_summary = {
                "execution_nodes": JobExecutionEngine.plugin_action_execution_nodes(
                    job=job,
                    plugin_output_mapping=plugin_output_mapping,
                    plugin_records_imported=plugin_records_imported,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    skill_codes=skill_codes_for_job(current_store, job),
                ),
                "plugin": plugin_summary,
            }
        records_imported = 0
    if status == "succeeded" and JobExecutionEngine.has_pending_runner(plugin_summary):
        status = "running"
    finished_at = None if status == "running" else datetime.now(UTC).isoformat()
    updated_at = datetime.now(UTC).isoformat()
    run = {
        **run,
        "error_code": error_code,
        "error_message": error_message,
        "finished_at": finished_at,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": status,
        "updated_at": updated_at,
    }
    _put_memory_record(current_store, "scheduled_job_runs", run)
    if status in SCHEDULED_JOB_RUN_TERMINAL_STATUSES:
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
        "last_run_at": finished_at or updated_at,
        "last_success_at": finished_at if status == "succeeded" else job.get("last_success_at"),
        "updated_at": updated_at,
    }
    _put_memory_record(current_store, "scheduled_jobs", job_update)
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
        payload=scheduled_job_run_audit_payload(job=job, run=run),
    )
    persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
        audit_event=audit_event,
    )
    return public_scheduled_job_run(run, current_store=current_store)


def cancel_scheduled_job_run_response(
    *,
    current_store: Any,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_scheduled_job_run_store(current_store)
    run = _read_memory_dict(current_store, "scheduled_job_runs").get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job run not found")
    if run["status"] in SCHEDULED_JOB_RUN_TERMINAL_STATUSES:
        raise api_error(409, "SCHEDULED_JOB_RUN_STATE_INVALID", "Terminal run cannot be cancelled")
    now = datetime.now(UTC).isoformat()
    run = {**run, "finished_at": now, "status": "cancelled", "updated_at": now}
    _put_memory_record(current_store, "scheduled_job_runs", run)
    collector_run_id = run.get("collector_run_id")
    collector_run = (
        _read_memory_dict(current_store, "collector_runs").get(collector_run_id)
        if collector_run_id
        else None
    )
    if collector_run is not None and collector_run.get("status") not in {
        "cancelled",
        "failed",
        "succeeded",
    }:
        complete_collector_run(
            current_store,
            collector_run=collector_run,
            error_message="Scheduled job run was cancelled",
            records_imported=0,
            status="cancelled",
            user=user,
        )
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
