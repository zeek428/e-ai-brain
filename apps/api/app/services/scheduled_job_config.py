from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.api.deps import api_error
from app.services.code_inspections import sync_product_git_repository_store
from app.services.native_code_scanner import code_inspection_uses_native_scan
from app.services.scheduled_job_catalog import (
    AI_REQUIRED_SCHEDULED_JOB_TYPES,
    CODE_INSPECTION_SCAN_MODES,
    DEFAULT_CODE_INSPECTION_SCAN_MODE,
)
from app.services.scheduled_job_common import ensure_enum
from app.services.scheduled_job_constants import (
    DEFAULT_DATA_CONNECTION_POLICY,
    DEFAULT_RESULT_ACTION_POLICY,
)
from app.services.scheduled_job_refs import (
    payload_field,
    scheduled_job_multi_ids,
    scheduled_job_orchestration_config,
)
from app.services.scheduled_job_store import (
    read_memory_dict,
    sync_reference_store,
)


def validate_product(current_store: Any, product_id: str | None) -> None:
    if product_id is None:
        return
    sync_reference_store(current_store)
    product = read_memory_dict(current_store, "products").get(product_id)
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


def scheduled_job_config_with_multi_refs(
    config_json: Any,
    *,
    plugin_action_ids: list[str],
    plugin_connection_ids: list[str],
) -> dict[str, Any]:
    config = dict(config_json) if isinstance(config_json, dict) else {}
    existing_orchestration = scheduled_job_orchestration_config(config)
    config["orchestration"] = {
        **existing_orchestration,
        "data_connections": {
            **DEFAULT_DATA_CONNECTION_POLICY,
            **(
                existing_orchestration.get("data_connections")
                if isinstance(existing_orchestration.get("data_connections"), dict)
                else {}
            ),
        },
        "plugin_action_ids": list(plugin_action_ids),
        "plugin_connection_ids": list(plugin_connection_ids),
        "result_actions": {
            **DEFAULT_RESULT_ACTION_POLICY,
            **(
                existing_orchestration.get("result_actions")
                if isinstance(existing_orchestration.get("result_actions"), dict)
                else {}
            ),
        },
    }
    return config


def optional_stripped(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def scheduled_job_config_with_code_inspection_defaults(
    current_store: Any,
    *,
    config_json: Any,
    job_type: str,
    product_id: str | None,
) -> dict[str, Any]:
    config = dict(config_json) if isinstance(config_json, dict) else {}
    if job_type != "code_repository_inspection":
        return config

    scan_mode = optional_stripped(config.get("scan_mode")) or DEFAULT_CODE_INSPECTION_SCAN_MODE
    ensure_enum(scan_mode, CODE_INSPECTION_SCAN_MODES, "config_json.scan_mode")
    config["scan_mode"] = scan_mode

    repository_id = optional_stripped(config.get("repository_id"))
    if repository_id is None:
        branch = optional_stripped(config.get("branch"))
        if branch is not None:
            config["branch"] = branch
        return config

    config["repository_id"] = repository_id
    sync_product_git_repository_store(current_store, product_id)
    repository = read_memory_dict(current_store, "product_git_repositories").get(repository_id)
    if repository is None:
        return config
    if product_id and repository.get("product_id") != product_id:
        raise api_error(400, "VALIDATION_ERROR", "Repository does not belong to product")

    branch = optional_stripped(config.get("branch"))
    if branch is None:
        branch = optional_stripped(repository.get("default_branch")) or "main"
    config["branch"] = branch
    return config


def scheduled_job_data_connection_policy(job: dict[str, Any]) -> dict[str, str]:
    policy = scheduled_job_orchestration_config(job.get("config_json") or {}).get(
        "data_connections",
    )
    if not isinstance(policy, dict):
        return dict(DEFAULT_DATA_CONNECTION_POLICY)
    return {
        "failure_policy": str(policy.get("failure_policy") or "fail_fast"),
        "merge_strategy": str(policy.get("merge_strategy") or "append_json_arrays"),
        "mode": str(policy.get("mode") or "sequential"),
    }


def scheduled_job_result_action_policy(job: dict[str, Any]) -> dict[str, str]:
    policy = scheduled_job_orchestration_config(job.get("config_json") or {}).get(
        "result_actions",
    )
    if not isinstance(policy, dict):
        return dict(DEFAULT_RESULT_ACTION_POLICY)
    return {
        "failure_policy": str(policy.get("failure_policy") or "continue_on_error"),
        "mode": str(policy.get("mode") or "sequential"),
    }


def scheduled_job_with_multi_refs(job: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(job)
    plugin_action_ids = scheduled_job_multi_ids(enriched, "plugin_action_ids", "plugin_action_id")
    plugin_connection_ids = scheduled_job_multi_ids(
        enriched,
        "plugin_connection_ids",
        "plugin_connection_id",
    )
    enriched["plugin_action_ids"] = plugin_action_ids
    enriched["plugin_connection_ids"] = plugin_connection_ids
    if plugin_action_ids:
        enriched["plugin_action_id"] = plugin_action_ids[0]
    if plugin_connection_ids:
        enriched["plugin_connection_id"] = plugin_connection_ids[0]
    enriched["config_json"] = scheduled_job_config_with_multi_refs(
        enriched.get("config_json") or {},
        plugin_action_ids=plugin_action_ids,
        plugin_connection_ids=plugin_connection_ids,
    )
    return enriched


def effective_scheduled_job_type(payload: Any) -> str:
    job_type = str(payload_field(payload, "job_type") or "")
    skill_ids = list(payload_field(payload, "skill_ids", []) or [])
    if (
        job_type == "user_feedback_collect"
        and bool(scheduled_job_multi_ids(payload, "plugin_action_ids", "plugin_action_id"))
        and (
            payload_field(payload, "agent_id") is not None
            or payload_field(payload, "model_gateway_config_id") is not None
            or bool(skill_ids)
        )
    ):
        return "user_feedback_insight_extract"
    return job_type


def effective_scheduled_job_execution_mode(payload: Any, job_type: str) -> str:
    if job_type in AI_REQUIRED_SCHEDULED_JOB_TYPES:
        return "ai_generated"
    return str(payload_field(payload, "execution_mode") or "deterministic")


def scheduled_job_uses_native_code_inspection(payload: Any) -> bool:
    return (
        effective_scheduled_job_type(payload) == "code_repository_inspection"
        and code_inspection_uses_native_scan(payload)
    )
