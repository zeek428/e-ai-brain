from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.api.deps import api_error
from app.services.plugins import (
    create_plugin_action_response,
    create_plugin_connection_response,
)
from app.services.scheduled_jobs import (
    AI_REQUIRED_SCHEDULED_JOB_TYPES,
    SCHEDULED_JOB_EXECUTION_MODES,
    SCHEDULED_JOB_SCHEDULE_TYPES,
    SCHEDULED_JOB_TYPES,
    create_scheduled_job_response,
    effective_scheduled_job_execution_mode,
    effective_scheduled_job_type,
    run_scheduled_job_response,
)

ASSISTANT_ACTION_DRAFT_STATUSES = {
    "cancelled",
    "confirmed",
    "expired",
    "failed",
    "pending",
}
ASSISTANT_ACTION_RUN_STATUSES = {"failed", "succeeded"}
ASSISTANT_DRAFT_ACTIONS = {
    "create_analysis_draft",
    "create_plugin_action",
    "create_plugin_connection",
    "create_scheduled_job",
}
SCHEDULED_JOB_DEFAULTS = {
    "agent_id": None,
    "config_json": {},
    "cron_expression": None,
    "enabled": True,
    "execution_mode": "deterministic",
    "interval_seconds": None,
    "knowledge_document_ids": [],
    "lock_ttl_seconds": 900,
    "max_retry_count": 0,
    "model_gateway_config_id": None,
    "plugin_action_id": None,
    "plugin_action_ids": [],
    "plugin_connection_id": None,
    "plugin_connection_ids": [],
    "plugin_input_mapping": {},
    "plugin_output_mapping": {},
    "product_id": None,
    "result_actions": [],
    "schedule_type": "manual",
    "skill_ids": [],
    "source_system": "ai-assistant",
    "timeout_seconds": 600,
    "timezone": "Asia/Shanghai",
}
PLUGIN_CONNECTION_DEFAULTS = {
    "auth_config": {},
    "auth_type": "none",
    "environment": "default",
    "max_retries": 0,
    "request_config": {},
    "status": "active",
    "timeout_seconds": 30,
}
PLUGIN_ACTION_DEFAULTS = {
    "action_type": "http_request",
    "connection_id": None,
    "description": None,
    "input_schema": {},
    "output_schema": {},
    "request_config": {},
    "requires_human_review": False,
    "result_mapping": {},
    "status": "active",
}


def create_assistant_action_draft_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    action = ensure_draft_action(payload.action)
    now = now_iso()
    metadata_json = deepcopy(getattr(payload, "metadata_json", {}) or {})
    expires_at = _draft_expires_at(payload, metadata_json=metadata_json)
    draft = {
        "action": action,
        "cancel_reason": None,
        "cancelled_at": None,
        "cancelled_by": None,
        "client_draft_id": getattr(payload, "client_draft_id", None),
        "confirmed_at": None,
        "confirmed_by": None,
        "created_at": now,
        "created_by": user["id"],
        "expires_at": expires_at,
        "id": current_store.new_id("assistant_action_draft"),
        "metadata_json": metadata_json,
        "payload": deepcopy(payload.payload),
        "result_run_id": None,
        "risk_level": getattr(payload, "risk_level", None) or "medium",
        "source_message_id": getattr(payload, "source_message_id", None),
        "status": "pending",
        "title": ensure_non_blank(payload.title, "title"),
        "updated_at": now,
    }
    current_store.assistant_action_drafts[draft["id"]] = draft
    audit_event = current_store.audit(
        event_type="assistant_action_draft.created",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={
            "action": draft["action"],
            "risk_level": draft["risk_level"],
            "title": draft["title"],
        },
    )
    save_assistant_action_records(current_store, draft=draft, audit_events=[audit_event])
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    return public_assistant_action_draft(draft, current_store=current_store)


def get_assistant_action_draft_response(
    *,
    current_store: Any,
    draft_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    return public_assistant_action_draft(draft, current_store=current_store)


def confirm_assistant_action_draft_response(
    *,
    current_store: Any,
    draft_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    if draft.get("status") == "expired":
        raise api_error(409, "DRAFT_EXPIRED", "Assistant action draft has expired")
    if draft.get("status") != "pending":
        raise api_error(409, "DRAFT_NOT_PENDING", "Assistant action draft is not pending")
    preview = assistant_action_draft_preview(current_store, draft)
    if preview["validation"]["status"] == "blocked":
        raise api_error(409, "DRAFT_PRECHECK_FAILED", "Assistant action draft precheck failed")

    result_type, result_id, result = execute_assistant_action_draft(
        current_store,
        draft=draft,
        user=user,
    )
    now = now_iso()
    run = {
        "action": draft["action"],
        "created_at": now,
        "draft_id": draft["id"],
        "error_code": None,
        "error_message": None,
        "executed_by": user["id"],
        "finished_at": now,
        "id": current_store.new_id("assistant_action_run"),
        "result": deepcopy(result),
        "result_id": result_id,
        "result_type": result_type,
        "started_at": now,
        "status": "succeeded",
        "updated_at": now,
    }
    current_store.assistant_action_runs[run["id"]] = run
    draft.update(
        {
            "confirmed_at": now,
            "confirmed_by": user["id"],
            "result_run_id": run["id"],
            "status": "confirmed",
            "updated_at": now,
        }
    )
    current_store.assistant_action_drafts[draft["id"]] = draft
    audit_event = current_store.audit(
        event_type="assistant_action_draft.confirmed",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={
            "action": draft["action"],
            "result_id": result_id,
            "result_type": result_type,
            "run_id": run["id"],
            **_assistant_action_confirm_audit_extras(result),
        },
    )
    save_assistant_action_records(
        current_store,
        draft=draft,
        run=run,
        audit_events=[audit_event],
    )
    return {
        "draft": public_assistant_action_draft(draft, current_store=current_store),
        "run": public_assistant_action_run(run),
    }


def cancel_assistant_action_draft_response(
    *,
    current_store: Any,
    draft_id: str,
    reason: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    if draft.get("status") == "expired":
        raise api_error(409, "DRAFT_EXPIRED", "Assistant action draft has expired")
    if draft.get("status") != "pending":
        raise api_error(409, "DRAFT_NOT_PENDING", "Assistant action draft is not pending")
    now = now_iso()
    draft.update(
        {
            "cancel_reason": (reason or "").strip() or None,
            "cancelled_at": now,
            "cancelled_by": user["id"],
            "status": "cancelled",
            "updated_at": now,
        }
    )
    current_store.assistant_action_drafts[draft["id"]] = draft
    audit_event = current_store.audit(
        event_type="assistant_action_draft.cancelled",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={"reason": draft.get("cancel_reason")},
    )
    save_assistant_action_records(current_store, draft=draft, audit_events=[audit_event])
    return public_assistant_action_draft(draft, current_store=current_store)


def persist_assistant_action_drafts_from_tool_results(
    current_store: Any,
    *,
    source_message_id: str,
    tool_results: list[dict[str, Any]],
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    for tool_result in tool_results:
        if tool_result.get("tool") != "assistant.action_draft":
            continue
        for item in tool_result.get("items") or []:
            if not isinstance(item, dict):
                continue
            if item.get("requires_confirmation") is not True:
                continue
            if item.get("action") not in ASSISTANT_DRAFT_ACTIONS:
                continue
            client_draft_id = str(item.get("draft_id") or "").strip() or None
            draft = create_assistant_action_draft_response(
                current_store=current_store,
                payload=SimpleNamespace(
                    action=item["action"],
                    client_draft_id=client_draft_id,
                    metadata_json={
                        "intent": tool_result.get("intent"),
                        "source": "assistant_tool_result",
                        "tool": tool_result.get("tool"),
                    },
                    payload=deepcopy(item.get("payload") or {}),
                    risk_level=item.get("risk_level") or "medium",
                    source_message_id=source_message_id,
                    title=item.get("title") or item["action"],
                ),
                user=user,
            )
            item["client_draft_id"] = client_draft_id
            item["draft_id"] = draft["id"]
            item["preview"] = draft.get("preview")
            item["server_draft_id"] = draft["id"]
            item["status"] = draft["status"]
    return tool_results


def execute_assistant_action_draft(
    current_store: Any,
    *,
    draft: dict[str, Any],
    user: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    action = draft["action"]
    payload = deepcopy(draft.get("payload") or {})
    if action == "create_scheduled_job":
        payload = with_defaults(SCHEDULED_JOB_DEFAULTS, payload)
        config_json = dict(payload.get("config_json") or {})
        config_json["assistant_draft"] = {
            "draft_id": draft["id"],
            "source": "ai_assistant",
            "title": draft["title"],
        }
        payload["config_json"] = config_json
        result = create_scheduled_job_response(
            current_store=current_store,
            payload=SimpleNamespace(**payload),
            user=user,
        )
        if _assistant_run_once_after_confirm_requested(payload):
            scheduled_job_run = run_scheduled_job_response(
                current_store=current_store,
                job_id=str(result["id"]),
                source_run_id=None,
                trigger_type="manual",
                user=user,
            )
            result = {
                **result,
                "scheduled_job_run": scheduled_job_run,
            }
        return "scheduled_job", str(result["id"]), result
    if action == "create_plugin_connection":
        payload = with_defaults(PLUGIN_CONNECTION_DEFAULTS, payload)
        result = create_plugin_connection_response(
            current_store=current_store,
            payload=SimpleNamespace(**payload),
            user=user,
        )
        return "plugin_connection", str(result["id"]), result
    if action == "create_plugin_action":
        payload = with_defaults(PLUGIN_ACTION_DEFAULTS, payload)
        result = create_plugin_action_response(
            current_store=current_store,
            payload=SimpleNamespace(**payload),
            user=user,
        )
        return "plugin_action", str(result["id"]), result
    if action == "create_analysis_draft":
        result = {
            **payload,
            "source_draft_id": draft["id"],
            "status": "confirmed",
            "title": draft["title"],
        }
        return "assistant_analysis", draft["id"], result
    raise api_error(400, "UNSUPPORTED_DRAFT_ACTION", "Unsupported assistant draft action")


def _assistant_run_once_after_confirm_requested(payload: dict[str, Any]) -> bool:
    config_json = payload.get("config_json")
    if not isinstance(config_json, dict):
        return False
    request = config_json.get("assistant_run_once_request")
    return isinstance(request, dict) and request.get("requested") is True


def _assistant_action_confirm_audit_extras(result: dict[str, Any]) -> dict[str, Any]:
    scheduled_job_run = result.get("scheduled_job_run")
    if not isinstance(scheduled_job_run, dict):
        return {}
    run_id = str(scheduled_job_run.get("id") or "").strip()
    if not run_id:
        return {}
    return {"scheduled_job_run_id": run_id}


def get_assistant_action_draft(
    current_store: Any,
    *,
    draft_id: str,
) -> dict[str, Any]:
    repository = assistant_action_repository(current_store)
    get_draft = getattr(repository, "get_assistant_action_draft", None)
    if callable(get_draft):
        draft = get_draft(draft_id=draft_id)
    else:
        draft = getattr(current_store, "assistant_action_drafts", {}).get(draft_id)
    if draft is None:
        raise api_error(404, "NOT_FOUND", "Assistant action draft not found")
    return dict(draft)


def refresh_assistant_action_draft_expiry(
    current_store: Any,
    draft: dict[str, Any],
) -> dict[str, Any]:
    if draft.get("status") != "pending" or not _draft_is_expired(draft):
        return draft
    ensure_action_collections(current_store)
    now = now_iso()
    draft = {
        **draft,
        "status": "expired",
        "updated_at": now,
    }
    current_store.assistant_action_drafts[draft["id"]] = draft
    audit_event = current_store.audit(
        event_type="assistant_action_draft.expired",
        actor_id="system",
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={
            "action": draft.get("action"),
            "expires_at": _draft_expires_at_value(draft),
            "title": draft.get("title"),
        },
    )
    save_assistant_action_records(current_store, draft=draft, audit_events=[audit_event])
    return draft


def save_assistant_action_records(
    current_store: Any,
    *,
    draft: dict[str, Any],
    audit_events: list[dict[str, Any]],
    run: dict[str, Any] | None = None,
) -> None:
    repository = assistant_action_repository(current_store)
    save_records = getattr(repository, "save_assistant_action_records", None)
    if callable(save_records):
        save_records(draft=draft, run=run, audit_events=audit_events)


def assistant_action_repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def ensure_action_collections(current_store: Any) -> None:
    if not hasattr(current_store, "assistant_action_drafts"):
        current_store.assistant_action_drafts = {}
    if not hasattr(current_store, "assistant_action_runs"):
        current_store.assistant_action_runs = {}


def ensure_draft_action(action: str) -> str:
    normalized = ensure_non_blank(action, "action")
    if normalized not in ASSISTANT_DRAFT_ACTIONS:
        raise api_error(400, "UNSUPPORTED_DRAFT_ACTION", "Unsupported assistant draft action")
    return normalized


def ensure_draft_access(draft: dict[str, Any], *, user: dict[str, Any]) -> None:
    if "admin" in set(user.get("roles") or []):
        return
    if draft.get("created_by") == user.get("id"):
        return
    raise api_error(404, "NOT_FOUND", "Assistant action draft not found")


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def with_defaults(defaults: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults)
    merged.update(deepcopy(payload))
    return merged


def _draft_expires_at(payload: Any, *, metadata_json: dict[str, Any]) -> str | None:
    value = getattr(payload, "expires_at", None) or metadata_json.get("expires_at")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _draft_expires_at_value(draft: dict[str, Any]) -> str | None:
    metadata_json = (
        draft.get("metadata_json") if isinstance(draft.get("metadata_json"), dict) else {}
    )
    value = draft.get("expires_at") or metadata_json.get("expires_at")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _draft_is_expired(draft: dict[str, Any]) -> bool:
    expires_at = _parse_draft_datetime(_draft_expires_at_value(draft))
    if expires_at is None:
        return False
    return expires_at <= datetime.now(UTC)


def _parse_draft_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def assistant_action_draft_preview(
    current_store: Any,
    draft: dict[str, Any],
) -> dict[str, Any]:
    action = draft["action"]
    if action == "create_scheduled_job":
        return _scheduled_job_draft_preview(current_store, draft)
    if action == "create_plugin_connection":
        return _generic_create_draft_preview(
            draft,
            diff_fields=[
                ("name", "名称"),
                ("plugin_id", "插件"),
                ("endpoint_url", "Endpoint"),
                ("environment", "环境"),
                ("auth_type", "认证"),
                ("status", "状态"),
            ],
            required_fields=["name", "plugin_id", "endpoint_url"],
            resource_type="plugin_connection",
        )
    if action == "create_plugin_action":
        preview = _generic_create_draft_preview(
            draft,
            diff_fields=[
                ("name", "名称"),
                ("code", "编码"),
                ("plugin_id", "插件"),
                ("connection_id", "连接"),
                ("action_type", "动作类型"),
                ("request_config.method", "请求方法"),
                ("request_config.path", "请求路径"),
                ("result_mapping.write_target", "写入目标"),
            ],
            required_fields=["name", "code", "plugin_id", "action_type"],
            resource_type="plugin_action",
        )
        _append_plugin_action_validation(current_store, draft, preview)
        return preview
    if action == "create_analysis_draft":
        return _generic_create_draft_preview(
            draft,
            diff_fields=[
                ("title", "标题"),
                ("analysis_type", "分析类型"),
                ("source_module", "来源模块"),
                ("summary", "摘要指标"),
                ("findings", "风险/治理项"),
            ],
            required_fields=["title", "analysis_type"],
            resource_type="assistant_analysis",
        )
    return _generic_create_draft_preview(
        draft,
        diff_fields=[],
        required_fields=[],
        resource_type=action,
    )


def _scheduled_job_draft_preview(
    current_store: Any,
    draft: dict[str, Any],
) -> dict[str, Any]:
    payload = with_defaults(SCHEDULED_JOB_DEFAULTS, draft.get("payload") or {})
    job_type = effective_scheduled_job_type(payload)
    execution_mode = effective_scheduled_job_execution_mode(payload, job_type)
    payload["job_type"] = job_type
    payload["execution_mode"] = execution_mode
    preview = _generic_create_draft_preview(
        {"action": draft["action"], "payload": payload},
        diff_fields=[
            ("name", "名称"),
            ("job_type", "作业类型"),
            ("schedule_type", "调度类型"),
            ("cron_expression", "Cron 表达式"),
            ("interval_seconds", "间隔秒数"),
            ("execution_mode", "执行模式"),
            ("plugin_connection_id", "数据连接"),
            ("plugin_action_id", "结果动作"),
            ("model_gateway_config_id", "AI 模型"),
            ("agent_id", "AI角色"),
            ("skill_ids", "Skills"),
            ("enabled", "启用"),
        ],
        required_fields=["name", "job_type", "schedule_type"],
        resource_type="scheduled_job",
    )
    validation = preview["validation"]
    _validate_enum(validation, "job_type", job_type, SCHEDULED_JOB_TYPES)
    _validate_enum(validation, "execution_mode", execution_mode, SCHEDULED_JOB_EXECUTION_MODES)
    schedule_type = payload.get("schedule_type")
    _validate_enum(validation, "schedule_type", schedule_type, SCHEDULED_JOB_SCHEDULE_TYPES)
    if schedule_type == "cron" and not payload.get("cron_expression"):
        _add_issue(validation, "cron_expression", "error", "cron_expression is required")
    if schedule_type == "interval":
        interval_seconds = payload.get("interval_seconds")
        if not isinstance(interval_seconds, int) or interval_seconds <= 0:
            _add_issue(validation, "interval_seconds", "error", "interval_seconds is required")
    _append_scheduled_job_reference_validation(current_store, payload, validation)
    _finalize_validation(validation)
    return preview


def _append_scheduled_job_reference_validation(
    current_store: Any,
    payload: dict[str, Any],
    validation: dict[str, Any],
) -> None:
    job_type = effective_scheduled_job_type(payload)
    execution_mode = effective_scheduled_job_execution_mode(payload, job_type)
    plugin_action_ids = _string_ids(
        payload.get("plugin_action_ids") or payload.get("plugin_action_id")
    )
    plugin_connection_ids = _string_ids(
        payload.get("plugin_connection_ids") or payload.get("plugin_connection_id")
    )
    if not plugin_action_ids and job_type in {
        "code_repository_inspection",
        "online_log_ai_analysis",
        "user_feedback_insight_extract",
    }:
        _add_issue(
            validation,
            "plugin_action_id",
            "error",
            f"{job_type} requires plugin_action_id",
        )
    for action_id in plugin_action_ids:
        _validate_collection_ref(
            current_store.plugin_actions,
            action_id,
            field="plugin_action_id",
            label="Plugin action",
            validation=validation,
        )
    for connection_id in plugin_connection_ids:
        _validate_collection_ref(
            current_store.plugin_connections,
            connection_id,
            field="plugin_connection_id",
            label="Plugin connection",
            validation=validation,
        )
    ai_processing_job = (
        execution_mode in {"ai_assisted", "ai_generated"}
        or job_type in AI_REQUIRED_SCHEDULED_JOB_TYPES
    )
    if not ai_processing_job:
        return
    agent_id = payload.get("agent_id")
    if not agent_id:
        _add_issue(validation, "agent_id", "error", "AI job requires agent_id")
    else:
        _validate_collection_ref(
            current_store.ai_agents,
            str(agent_id),
            field="agent_id",
            label="AI agent",
            validation=validation,
        )
    skill_ids = _string_ids(payload.get("skill_ids"))
    if not skill_ids:
        _add_issue(validation, "skill_ids", "error", "AI processing job requires skill_ids")
    for skill_id in skill_ids:
        _validate_collection_ref(
            current_store.ai_skills,
            skill_id,
            field="skill_ids",
            label="AI skill",
            validation=validation,
        )
    model_gateway_config_id = payload.get("model_gateway_config_id")
    if job_type in AI_REQUIRED_SCHEDULED_JOB_TYPES and not model_gateway_config_id:
        _add_issue(
            validation,
            "model_gateway_config_id",
            "error",
            "AI processing job requires model_gateway_config_id",
        )
    elif model_gateway_config_id:
        _validate_collection_ref(
            current_store.model_gateway_configs,
            str(model_gateway_config_id),
            field="model_gateway_config_id",
            label="Model gateway config",
            validation=validation,
        )


def _append_plugin_action_validation(
    current_store: Any,
    draft: dict[str, Any],
    preview: dict[str, Any],
) -> None:
    payload = draft.get("payload") or {}
    connection_id = payload.get("connection_id")
    if connection_id:
        _validate_collection_ref(
            current_store.plugin_connections,
            str(connection_id),
            field="connection_id",
            label="Plugin connection",
            validation=preview["validation"],
        )
    _finalize_validation(preview["validation"])


def _generic_create_draft_preview(
    draft: dict[str, Any],
    *,
    diff_fields: list[tuple[str, str]],
    required_fields: list[str],
    resource_type: str,
) -> dict[str, Any]:
    payload = draft.get("payload") or {}
    validation = {"issues": [], "status": "passed"}
    for field in required_fields:
        if _nested_value(payload, field) in (None, "", []):
            _add_issue(validation, field, "error", f"{field} is required")
    preview = {
        "diffs": [
            {
                "change_type": "create",
                "current": None,
                "field": field,
                "label": label,
                "proposed": deepcopy(value),
            }
            for field, label in diff_fields
            if (value := _nested_value(payload, field)) not in (None, "", [])
        ],
        "target": {
            "operation": "create",
            "resource_id": None,
            "resource_type": resource_type,
        },
        "validation": validation,
    }
    _finalize_validation(validation)
    return preview


def _validate_collection_ref(
    collection: dict[str, dict[str, Any]],
    item_id: str,
    *,
    field: str,
    label: str,
    validation: dict[str, Any],
) -> None:
    item = collection.get(item_id)
    if item is None:
        _add_issue(validation, field, "error", f"{label} not found: {item_id}")
        return
    if item.get("status") and item.get("status") != "active":
        _add_issue(validation, field, "error", f"{label} is inactive: {item_id}")


def _validate_enum(
    validation: dict[str, Any],
    field: str,
    value: Any,
    allowed_values: set[str],
) -> None:
    if value not in allowed_values:
        _add_issue(validation, field, "error", f"Unsupported {field}")


def _add_issue(
    validation: dict[str, Any],
    field: str,
    severity: str,
    message: str,
) -> None:
    validation.setdefault("issues", []).append(
        {
            "field": field,
            "message": message,
            "severity": severity,
        }
    )


def _finalize_validation(validation: dict[str, Any]) -> None:
    issues = validation.get("issues") or []
    if any(issue.get("severity") == "error" for issue in issues):
        validation["status"] = "blocked"
    elif issues:
        validation["status"] = "warning"
    else:
        validation["status"] = "passed"


def _nested_value(payload: dict[str, Any], field: str) -> Any:
    value: Any = payload
    for part in field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _string_ids(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    result = []
    for item in values:
        item_id = str(item).strip()
        if item_id:
            result.append(item_id)
    return result


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def public_assistant_action_draft(
    draft: dict[str, Any],
    *,
    current_store: Any,
) -> dict[str, Any]:
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    public = {
        "action": draft["action"],
        "cancel_reason": draft.get("cancel_reason"),
        "cancelled_at": draft.get("cancelled_at"),
        "cancelled_by": draft.get("cancelled_by"),
        "client_draft_id": draft.get("client_draft_id"),
        "confirmed_at": draft.get("confirmed_at"),
        "confirmed_by": draft.get("confirmed_by"),
        "created_at": draft["created_at"],
        "created_by": draft["created_by"],
        "expires_at": _draft_expires_at_value(draft),
        "id": draft["id"],
        "metadata_json": deepcopy(draft.get("metadata_json") or {}),
        "payload": deepcopy(draft.get("payload") or {}),
        "result_run_id": draft.get("result_run_id"),
        "risk_level": draft.get("risk_level", "medium"),
        "source_message_id": draft.get("source_message_id"),
        "status": draft["status"],
        "title": draft["title"],
        "updated_at": draft["updated_at"],
    }
    public["preview"] = assistant_action_draft_preview(current_store, draft)
    return {key: value for key, value in public.items() if value is not None}


def public_assistant_action_run(run: dict[str, Any]) -> dict[str, Any]:
    public = {
        "action": run["action"],
        "created_at": run["created_at"],
        "draft_id": run["draft_id"],
        "error_code": run.get("error_code"),
        "error_message": run.get("error_message"),
        "executed_by": run["executed_by"],
        "finished_at": run.get("finished_at"),
        "id": run["id"],
        "result": deepcopy(run.get("result") or {}),
        "result_id": run.get("result_id"),
        "result_type": run.get("result_type"),
        "started_at": run.get("started_at"),
        "status": run["status"],
        "updated_at": run["updated_at"],
    }
    return {key: value for key, value in public.items() if value is not None}
