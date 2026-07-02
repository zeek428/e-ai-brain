from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services.plugins import (
    ensure_active_connection,
    ensure_active_plugin,
    ensure_active_plugin_action,
)
from app.services.scheduled_job_ai_capabilities import (
    ensure_active_model_gateway,
    ensure_active_skills,
)
from app.services.scheduled_job_ai_executor import (
    scheduled_job_ai_executor_requires_model_gateway,
    validate_scheduled_job_ai_executor_config,
)
from app.services.scheduled_job_catalog import (
    AI_REQUIRED_SCHEDULED_JOB_TYPES,
    PLUGIN_RESOURCE_REQUIRED_SCHEDULED_JOB_TYPES,
    SCHEDULED_JOB_EXECUTION_MODES,
    SCHEDULED_JOB_SCHEDULE_TYPES,
    SCHEDULED_JOB_TYPES,
)
from app.services.scheduled_job_common import ensure_enum
from app.services.scheduled_job_config import (
    effective_scheduled_job_execution_mode,
    effective_scheduled_job_type,
    scheduled_job_uses_native_code_inspection,
    validate_product,
)
from app.services.scheduled_job_refs import normalized_string_ids, scheduled_job_multi_ids
from app.services.scheduled_job_store import (
    read_memory_dict,
    sync_ai_agent_store,
    sync_ai_skill_store,
    sync_reference_store,
)


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
    skill_ids = normalized_string_ids(payload.skill_ids)
    model_gateway_config_id = payload.model_gateway_config_id
    ai_required_job = job_type in AI_REQUIRED_SCHEDULED_JOB_TYPES
    ai_processing_job = execution_mode in {"ai_assisted", "ai_generated"} or ai_required_job
    if ai_processing_job:
        if agent_id is None:
            raise api_error(400, "AI_AGENT_REQUIRED", "AI job requires agent_id")
        agent = read_memory_dict(current_store, "ai_agents").get(agent_id)
        if agent is None:
            raise api_error(404, "NOT_FOUND", "AI agent not found")
        if agent.get("status") != "active":
            raise api_error(400, "AI_AGENT_INACTIVE", "AI agent is inactive")
        if not skill_ids:
            raise api_error(400, "AI_SKILL_REQUIRED", "AI processing job requires skill_ids")
        ensure_active_skills(current_store, skill_ids)
        validate_scheduled_job_ai_executor_config(
            current_store,
            payload,
            ai_processing_job=True,
        )
        if scheduled_job_ai_executor_requires_model_gateway(payload):
            model_gateway_config_id = ensure_active_model_gateway(
                current_store,
                model_gateway_config_id or agent.get("model_gateway_config_id"),
            )
            if ai_required_job and model_gateway_config_id is None:
                raise api_error(
                    400,
                    "MODEL_GATEWAY_CONFIG_REQUIRED",
                    "AI processing job requires model_gateway_config_id",
                )
        elif model_gateway_config_id or agent.get("model_gateway_config_id"):
            model_gateway_config_id = ensure_active_model_gateway(
                current_store,
                model_gateway_config_id or agent.get("model_gateway_config_id"),
            )
    return agent_id, skill_ids, model_gateway_config_id, job_type, execution_mode


def validate_plugin_refs(
    current_store: Any,
    payload: Any,
) -> tuple[str | None, str | None, list[str], list[str]]:
    native_code_inspection = scheduled_job_uses_native_code_inspection(payload)
    action_ids = scheduled_job_multi_ids(payload, "plugin_action_ids", "plugin_action_id")
    connection_ids = scheduled_job_multi_ids(
        payload,
        "plugin_connection_ids",
        "plugin_connection_id",
    )
    if native_code_inspection:
        return None, None, [], []
    action_id = action_ids[0] if action_ids else None
    connection_id = connection_ids[0] if connection_ids else None
    if action_id is None:
        if connection_ids:
            raise api_error(
                400,
                "PLUGIN_ACTION_REQUIRED",
                "plugin_connection_ids requires plugin_action_ids",
            )
        job_type = effective_scheduled_job_type(payload)
        if job_type in PLUGIN_RESOURCE_REQUIRED_SCHEDULED_JOB_TYPES:
            raise api_error(
                400,
                "PLUGIN_ACTION_REQUIRED",
                f"{job_type} requires plugin_action_id",
            )
        return None, None, [], []
    plugin, connection, _ = ensure_active_plugin_action(
        current_store,
        action_id,
        connection_id=connection_id,
    )
    resolved_connection_id = str(connection["id"])
    connection_ids = normalized_string_ids([resolved_connection_id, *connection_ids])

    for extra_action_id in action_ids[1:]:
        action = read_memory_dict(current_store, "plugin_actions").get(extra_action_id)
        if action is None:
            raise api_error(404, "NOT_FOUND", "Plugin action not found")
        if action.get("status") != "active":
            raise api_error(400, "PLUGIN_ACTION_INACTIVE", "Plugin action is inactive")
        ensure_active_plugin(current_store, str(action["plugin_id"]))
    for extra_connection_id in connection_ids[1:]:
        ensure_active_connection(current_store, extra_connection_id, plugin_id=str(plugin["id"]))
    return action_id, resolved_connection_id, action_ids, connection_ids
