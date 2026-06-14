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
from app.services.scheduled_jobs import create_scheduled_job_response

ASSISTANT_ACTION_DRAFT_STATUSES = {"cancelled", "confirmed", "failed", "pending"}
ASSISTANT_ACTION_RUN_STATUSES = {"failed", "succeeded"}
ASSISTANT_DRAFT_ACTIONS = {
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
        "id": current_store.new_id("assistant_action_draft"),
        "metadata_json": deepcopy(getattr(payload, "metadata_json", {}) or {}),
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
    return public_assistant_action_draft(draft)


def get_assistant_action_draft_response(
    *,
    current_store: Any,
    draft_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    return public_assistant_action_draft(draft)


def confirm_assistant_action_draft_response(
    *,
    current_store: Any,
    draft_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    if draft.get("status") != "pending":
        raise api_error(409, "DRAFT_NOT_PENDING", "Assistant action draft is not pending")

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
        },
    )
    save_assistant_action_records(
        current_store,
        draft=draft,
        run=run,
        audit_events=[audit_event],
    )
    return {
        "draft": public_assistant_action_draft(draft),
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
    return public_assistant_action_draft(draft)


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
    raise api_error(400, "UNSUPPORTED_DRAFT_ACTION", "Unsupported assistant draft action")


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


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def public_assistant_action_draft(draft: dict[str, Any]) -> dict[str, Any]:
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
