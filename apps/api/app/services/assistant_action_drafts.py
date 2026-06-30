from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException

from app.api.deps import api_error
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.trace import envelope
from app.services.assistant_action_draft_common import (
    AI_AGENT_DEFAULTS,
    AI_SKILL_DEFAULTS,
    ASSISTANT_ACTION_DRAFT_SORT_FIELDS,
    ASSISTANT_ACTION_DRAFT_STATUSES,
    ASSISTANT_ACTION_DRAFT_VALIDATION_STATUSES,
    ASSISTANT_DRAFT_ACTIONS,
    PLUGIN_ACTION_DEFAULTS,
    PLUGIN_CONNECTION_DEFAULTS,
    RD_TASK_DEFAULTS,
    SCHEDULED_JOB_DEFAULTS,
    assistant_action_draft_decision,
    ensure_draft_action,
    ensure_non_blank,
    valid_cron_expression,
    with_defaults,
)
from app.services.assistant_action_draft_workbench import (
    assistant_action_draft_workbench_item,
    assistant_action_draft_workbench_summary,
)
from app.services.plugins import (
    create_plugin_action_response,
    create_plugin_connection_response,
    sync_plugin_action_store,
    sync_plugin_connection_store,
)
from app.services.requirements import (
    generate_requirement_task_result,
    requirement_write_store,
)
from app.services.scheduled_job_ai_capabilities import (
    create_ai_agent_response,
    create_ai_skill_response,
)
from app.services.scheduled_jobs import (
    AI_REQUIRED_SCHEDULED_JOB_TYPES,
    SCHEDULED_JOB_EXECUTION_MODES,
    SCHEDULED_JOB_SCHEDULE_TYPES,
    SCHEDULED_JOB_TYPES,
    create_scheduled_job_response,
    effective_scheduled_job_execution_mode,
    effective_scheduled_job_type,
    persist_record,
    run_scheduled_job_response,
    sync_ai_agent_store,
    sync_ai_skill_store,
    sync_reference_store,
)
from app.services.version_status import canonical_requirement_status


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
    audit_event = assistant_action_audit_event(
        current_store,
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
    return public_assistant_action_draft(draft, current_store=current_store, user=user)


def get_assistant_action_draft_response(
    *,
    current_store: Any,
    draft_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    return public_assistant_action_draft(draft, current_store=current_store, user=user)


def list_assistant_action_drafts_response(
    *,
    action: str | None,
    created_from: str | None,
    created_to: str | None,
    current_store: Any,
    keyword: str | None,
    page: int | None,
    page_size: int | None,
    sort_by: str | None,
    sort_order: str,
    started_at: float | None,
    status: str | None,
    trace_id: str,
    user: dict[str, Any],
    validation_status: str | None,
) -> dict[str, Any]:
    ensure_list_enum(action, ASSISTANT_DRAFT_ACTIONS, "action")
    ensure_list_enum(status, ASSISTANT_ACTION_DRAFT_STATUSES, "status")
    ensure_list_enum(
        validation_status,
        ASSISTANT_ACTION_DRAFT_VALIDATION_STATUSES,
        "validation_status",
    )
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_list_enum(sort_by, ASSISTANT_ACTION_DRAFT_SORT_FIELDS, "sort_by")

    resolved_sort_by = sort_by or "updated_at"
    repository = assistant_action_repository(current_store)
    list_workbench_page = getattr(
        repository,
        "list_assistant_action_draft_workbench_page",
        None,
    )
    if callable(list_workbench_page):
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        page_payload = list_workbench_page(
            action=action,
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            status=status,
            user_id=user["id"],
            validation_status=validation_status,
        )
        items = [
            assistant_action_draft_workbench_item(
                public_assistant_action_draft(
                    draft,
                    current_store=current_store,
                    user=user,
                )
            )
            for draft in (page_payload.get("items") or [])
            if isinstance(draft, dict)
        ]
        data = add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": int(page_payload.get("total") or 0),
            },
            filters={
                "action": action,
                "created_from": created_from,
                "created_to": created_to,
                "keyword": keyword,
                "status": status,
                "validation_status": validation_status,
            },
            list_name="assistant_action_drafts",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
        data["summary"] = page_payload.get("summary") or assistant_action_draft_workbench_summary(
            items
        )
        return envelope(data, trace_id)

    from_at = _parse_draft_datetime(created_from)
    to_at = _parse_draft_datetime(created_to)
    visible_drafts = [
        assistant_action_draft_workbench_item(
            public_assistant_action_draft(
                draft,
                current_store=current_store,
                user=user,
            )
        )
        for draft in list_user_assistant_action_drafts(current_store, user=user)
    ]
    if action:
        visible_drafts = [draft for draft in visible_drafts if draft["action"] == action]
    if status:
        visible_drafts = [draft for draft in visible_drafts if draft["status"] == status]
    if validation_status:
        visible_drafts = [
            draft for draft in visible_drafts if draft["validation_status"] == validation_status
        ]
    if from_at or to_at:
        visible_drafts = [
            draft
            for draft in visible_drafts
            if _assistant_draft_within_time_range(
                draft.get("created_at") or draft.get("updated_at"),
                from_at,
                to_at,
            )
        ]
    visible_drafts = [
        draft
        for draft in visible_drafts
        if list_text_matches(
            draft,
            keyword,
            (
                "action",
                "id",
                "result_id",
                "result_type",
                "source_message_id",
                "status",
                "title",
                "validation_status",
            ),
        )
    ]
    visible_drafts = sort_list_items(
        visible_drafts,
        allowed_fields=ASSISTANT_ACTION_DRAFT_SORT_FIELDS,
        default_sort_by="updated_at",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    response = paginated_list_payload(
        visible_drafts,
        filters={
            "action": action,
            "created_from": created_from,
            "created_to": created_to,
            "keyword": keyword,
            "status": status,
            "validation_status": validation_status,
        },
        list_name="assistant_action_drafts",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )
    response["data"]["summary"] = assistant_action_draft_workbench_summary(visible_drafts)
    return response


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
    existing_run = _assistant_existing_successful_run(current_store, draft)
    if draft.get("status") == "confirmed" and existing_run is not None:
        return {
            "draft": public_assistant_action_draft(
                draft,
                current_store=current_store,
                user=user,
            ),
            "run": public_assistant_action_run(existing_run),
        }
    if draft.get("status") != "pending":
        raise api_error(409, "DRAFT_NOT_PENDING", "Assistant action draft is not pending")
    effective_draft = _draft_with_resolved_prerequisites(current_store, draft)
    preview = assistant_action_draft_preview(current_store, effective_draft, user=user)
    if preview["validation"]["status"] == "blocked":
        _fail_assistant_action_draft(
            current_store,
            draft=draft,
            error_code="DRAFT_PRECHECK_FAILED",
            error_message="Assistant action draft precheck failed",
            user=user,
        )
        raise api_error(409, "DRAFT_PRECHECK_FAILED", "Assistant action draft precheck failed")

    try:
        result_type, result_id, result = execute_assistant_action_draft(
            current_store,
            draft=effective_draft,
            user=user,
        )
    except HTTPException as exc:
        error_code, error_message = _http_exception_code_and_message(exc)
        _fail_assistant_action_draft(
            current_store,
            draft=draft,
            error_code=error_code,
            error_message=error_message,
            user=user,
        )
        raise
    except Exception as exc:
        error_message = str(exc) or "Assistant action draft confirmation failed"
        _fail_assistant_action_draft(
            current_store,
            draft=draft,
            error_code="DRAFT_CONFIRM_FAILED",
            error_message=error_message,
            user=user,
        )
        raise api_error(500, "DRAFT_CONFIRM_FAILED", error_message) from exc
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
    _attach_assistant_run_attribution_to_scheduled_job_run(
        current_store,
        action_run=run,
        draft=draft,
        result=result,
    )
    draft.update(
        {
            "confirmed_at": now,
            "confirmed_by": user["id"],
            "result_run_id": run["id"],
            "status": "confirmed",
            "updated_at": now,
        }
    )
    audit_event = assistant_action_audit_event(
        current_store,
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
        "draft": public_assistant_action_draft(
            draft,
            current_store=current_store,
            user=user,
        ),
        "run": public_assistant_action_run(run),
    }


def _fail_assistant_action_draft(
    current_store: Any,
    *,
    draft: dict[str, Any],
    error_code: str,
    error_message: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    now = now_iso()
    metadata_json = deepcopy(draft.get("metadata_json") or {})
    metadata_json["failure"] = {
        "code": error_code,
        "message": error_message,
    }
    metadata_json["failed_at"] = now
    metadata_json["failed_by"] = user["id"]
    run = {
        "action": draft["action"],
        "created_at": now,
        "draft_id": draft["id"],
        "error_code": error_code,
        "error_message": error_message,
        "executed_by": user["id"],
        "finished_at": now,
        "id": current_store.new_id("assistant_action_run"),
        "result": {},
        "result_id": None,
        "result_type": None,
        "started_at": now,
        "status": "failed",
        "updated_at": now,
    }
    draft.update(
        {
            "metadata_json": metadata_json,
            "result_run_id": run["id"],
            "status": "failed",
            "updated_at": now,
        }
    )
    audit_event = assistant_action_audit_event(
        current_store,
        event_type="assistant_action_draft.failed",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={
            "action": draft["action"],
            "error_code": error_code,
            "error_message": error_message,
            "run_id": run["id"],
        },
    )
    save_assistant_action_records(
        current_store,
        draft=draft,
        run=run,
        audit_events=[audit_event],
    )
    return draft


def _http_exception_code_and_message(exc: HTTPException) -> tuple[str, str]:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or exc.status_code)
        message = str(detail.get("message") or code)
        return code, message
    message = str(detail or "Assistant action draft confirmation failed")
    return str(exc.status_code), message


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
    audit_event = assistant_action_audit_event(
        current_store,
        event_type="assistant_action_draft.cancelled",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={"reason": draft.get("cancel_reason")},
    )
    save_assistant_action_records(current_store, draft=draft, audit_events=[audit_event])
    return public_assistant_action_draft(draft, current_store=current_store, user=user)


def retry_assistant_action_draft_response(
    *,
    current_store: Any,
    draft_id: str,
    reason: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    if _draft_is_expired(draft):
        raise api_error(409, "DRAFT_EXPIRED", "Assistant action draft has expired")
    if draft.get("status") != "failed":
        raise api_error(409, "DRAFT_NOT_FAILED", "Assistant action draft is not failed")
    now = now_iso()
    previous_run_id = draft.get("result_run_id")
    metadata_json = deepcopy(draft.get("metadata_json") or {})
    failure_history = metadata_json.get("failure_history")
    if not isinstance(failure_history, list):
        failure_history = []
    failure = metadata_json.get("failure")
    if isinstance(failure, dict) or metadata_json.get("failed_at") or previous_run_id:
        failure_history.append(
            {
                "failed_at": metadata_json.get("failed_at"),
                "failed_by": metadata_json.get("failed_by"),
                "failure": deepcopy(failure) if isinstance(failure, dict) else None,
                "run_id": previous_run_id,
            }
        )
    metadata_json["failure_history"] = failure_history
    metadata_json["retry_count"] = _safe_int(metadata_json.get("retry_count")) + 1
    metadata_json["retry_reason"] = (reason or "").strip() or None
    metadata_json["retry_requested_at"] = now
    metadata_json["retry_requested_by"] = user["id"]
    metadata_json.pop("failure", None)
    metadata_json.pop("failed_at", None)
    metadata_json.pop("failed_by", None)
    draft.update(
        {
            "metadata_json": metadata_json,
            "result_run_id": None,
            "status": "pending",
            "updated_at": now,
        }
    )
    audit_event = assistant_action_audit_event(
        current_store,
        event_type="assistant_action_draft.retry_requested",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={
            "action": draft["action"],
            "previous_run_id": previous_run_id,
            "reason": metadata_json.get("retry_reason"),
            "retry_count": metadata_json["retry_count"],
        },
    )
    save_assistant_action_records(current_store, draft=draft, audit_events=[audit_event])
    return public_assistant_action_draft(draft, current_store=current_store, user=user)


def mark_assistant_action_draft_modified_response(
    *,
    current_store: Any,
    draft_id: str,
    modified_fields: list[str],
    user: dict[str, Any],
    user_modified: bool = True,
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    _ensure_pending_draft_for_edit(draft)
    now = now_iso()
    cleaned_fields = _clean_modified_fields(modified_fields)
    metadata_json = deepcopy(draft.get("metadata_json") or {})
    metadata_json["user_modified"] = bool(user_modified or cleaned_fields)
    if cleaned_fields:
        metadata_json["modified_fields"] = cleaned_fields
    metadata_json["modified_at"] = now
    metadata_json["modified_by"] = user["id"]
    draft.update(
        {
            "metadata_json": metadata_json,
            "updated_at": now,
        }
    )
    audit_event = assistant_action_audit_event(
        current_store,
        event_type="assistant_action_draft.modified",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={
            "modified_field_count": len(cleaned_fields),
            "modified_fields": cleaned_fields,
        },
    )
    save_assistant_action_records(current_store, draft=draft, audit_events=[audit_event])
    return public_assistant_action_draft(draft, current_store=current_store, user=user)


def patch_assistant_action_draft_response(
    *,
    current_store: Any,
    draft_id: str,
    modified_fields: list[str],
    payload: dict[str, Any],
    user: dict[str, Any],
    user_modified: bool = True,
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    _ensure_pending_draft_for_edit(draft)
    now = now_iso()
    cleaned_fields = _clean_modified_fields(modified_fields)
    metadata_json = deepcopy(draft.get("metadata_json") or {})
    metadata_json["user_modified"] = bool(user_modified and cleaned_fields)
    if cleaned_fields:
        metadata_json["modified_fields"] = cleaned_fields
    else:
        metadata_json.pop("modified_fields", None)
    metadata_json["modified_at"] = now
    metadata_json["modified_by"] = user["id"]
    draft.update(
        {
            "metadata_json": metadata_json,
            "payload": deepcopy(payload or {}),
            "updated_at": now,
        }
    )
    audit_event = assistant_action_audit_event(
        current_store,
        event_type="assistant_action_draft.updated",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={
            "modified_field_count": len(cleaned_fields),
            "modified_fields": cleaned_fields,
            "payload_keys": sorted(str(key) for key in (payload or {}).keys()),
        },
    )
    save_assistant_action_records(current_store, draft=draft, audit_events=[audit_event])
    return public_assistant_action_draft(draft, current_store=current_store, user=user)


def mark_assistant_action_draft_viewed_response(
    *,
    current_store: Any,
    draft_id: str,
    surface: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_action_collections(current_store)
    draft = get_assistant_action_draft(current_store, draft_id=draft_id)
    ensure_draft_access(draft, user=user)
    draft = refresh_assistant_action_draft_expiry(current_store, draft)
    now = now_iso()
    metadata_json = deepcopy(draft.get("metadata_json") or {})
    view_count = _safe_int(metadata_json.get("view_count")) + 1
    view_surface = _clean_view_surface(surface)
    if not metadata_json.get("viewed_at"):
        metadata_json["viewed_at"] = now
    if view_surface == "detail_modal":
        metadata_json["detail_viewed_at"] = now
    elif view_surface == "deeplink":
        metadata_json["deeplink_viewed_at"] = now
    metadata_json["last_viewed_at"] = now
    metadata_json["last_view_surface"] = view_surface
    metadata_json["view_count"] = view_count
    metadata_json["viewed_by"] = user["id"]
    draft.update(
        {
            "metadata_json": metadata_json,
            "updated_at": now,
        }
    )
    audit_event = assistant_action_audit_event(
        current_store,
        event_type="assistant_action_draft.viewed",
        actor_id=user["id"],
        subject_type="assistant_action_draft",
        subject_id=draft["id"],
        payload={
            "surface": metadata_json["last_view_surface"],
            "view_count": view_count,
        },
    )
    save_assistant_action_records(current_store, draft=draft, audit_events=[audit_event])
    return public_assistant_action_draft(draft, current_store=current_store, user=user)


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
            metadata_json = {
                "intent": tool_result.get("intent"),
                "source": "assistant_tool_result",
                "tool": tool_result.get("tool"),
            }
            if isinstance(item.get("wizard_steps"), list):
                metadata_json["wizard_steps"] = deepcopy(item["wizard_steps"])
            if isinstance(item.get("source_resource"), dict):
                metadata_json["source_resource"] = deepcopy(item["source_resource"])
            draft = create_assistant_action_draft_response(
                current_store=current_store,
                payload=SimpleNamespace(
                    action=item["action"],
                    client_draft_id=client_draft_id,
                    metadata_json=metadata_json,
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
    if action == "create_rd_task":
        payload = with_defaults(RD_TASK_DEFAULTS, payload)
        requirement_id = ensure_non_blank(
            str(payload.get("requirement_id") or ""),
            "requirement_id",
        )
        task_type = str(payload.get("task_type") or "product_detail_design")
        if task_type != "product_detail_design":
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "Only product_detail_design rd task drafts are supported",
            )
        result = generate_requirement_task_result(
            current_store=requirement_write_store(current_store),
            requirement_id=requirement_id,
            user=user,
        )
        result = {
            **result,
            "source_draft_id": draft["id"],
            "title": payload.get("title") or draft["title"],
        }
        return "ai_task", str(result["task_id"]), result
    if action == "create_ai_skill":
        payload = with_defaults(AI_SKILL_DEFAULTS, payload)
        result = create_ai_skill_response(
            current_store=current_store,
            payload=SimpleNamespace(**payload),
            user=user,
        )
        return "ai_skill", str(result["id"]), result
    if action == "create_ai_agent":
        payload = with_defaults(AI_AGENT_DEFAULTS, payload)
        result = create_ai_agent_response(
            current_store=current_store,
            payload=SimpleNamespace(**payload),
            user=user,
        )
        return "ai_agent", str(result["id"]), result
    if action == "create_analysis_draft":
        result = {
            **payload,
            "source_draft_id": draft["id"],
            "status": "confirmed",
            "title": draft["title"],
        }
        return "assistant_analysis", draft["id"], result
    raise api_error(400, "UNSUPPORTED_DRAFT_ACTION", "Unsupported assistant draft action")


def _draft_with_resolved_prerequisites(
    current_store: Any,
    draft: dict[str, Any],
) -> dict[str, Any]:
    payload = deepcopy(draft.get("payload") or {})
    prerequisite_ids = _string_ids(payload.get("assistant_prerequisite_draft_ids"))
    if not prerequisite_ids:
        return draft
    resolutions = _assistant_prerequisite_resolutions(
        current_store,
        draft=draft,
        prerequisite_ids=prerequisite_ids,
    )
    if not resolutions:
        return draft

    action = draft["action"]
    for resolution in resolutions:
        result_type = resolution["result_type"]
        result_id = resolution["result_id"]
        if action == "create_ai_agent" and result_type == "ai_skill":
            _append_payload_list_id(
                payload,
                "default_skill_ids",
                result_id,
                prerequisite_ids=prerequisite_ids,
            )
        elif action == "create_plugin_action" and result_type == "plugin_connection":
            _set_payload_scalar_id(
                payload,
                "connection_id",
                result_id,
                prerequisite_ids=prerequisite_ids,
            )
        elif action == "create_scheduled_job":
            if result_type == "plugin_connection":
                _set_payload_scalar_id(
                    payload,
                    "plugin_connection_id",
                    result_id,
                    prerequisite_ids=prerequisite_ids,
                )
                _append_payload_list_id(
                    payload,
                    "plugin_connection_ids",
                    result_id,
                    prerequisite_ids=prerequisite_ids,
                )
            elif result_type == "plugin_action":
                _set_payload_scalar_id(
                    payload,
                    "plugin_action_id",
                    result_id,
                    prerequisite_ids=prerequisite_ids,
                )
                _append_payload_list_id(
                    payload,
                    "plugin_action_ids",
                    result_id,
                    prerequisite_ids=prerequisite_ids,
                )
            elif result_type == "ai_agent":
                _set_payload_scalar_id(
                    payload,
                    "agent_id",
                    result_id,
                    prerequisite_ids=prerequisite_ids,
                )
            elif result_type == "ai_skill":
                _append_payload_list_id(
                    payload,
                    "skill_ids",
                    result_id,
                    prerequisite_ids=prerequisite_ids,
                )

    if payload == (draft.get("payload") or {}):
        return draft
    effective_draft = deepcopy(draft)
    effective_draft["payload"] = payload
    return effective_draft


def _assistant_prerequisite_resolutions(
    current_store: Any,
    *,
    draft: dict[str, Any],
    prerequisite_ids: list[str],
) -> list[dict[str, str]]:
    draft_items = _assistant_prerequisite_draft_items(
        current_store,
        draft=draft,
        prerequisite_ids=prerequisite_ids,
    )
    drafts_by_id = {str(item.get("id")): item for item in draft_items if item.get("id")}
    drafts_by_client_id = {
        str(item.get("client_draft_id")): item
        for item in draft_items
        if item.get("client_draft_id")
    }
    runs_by_id = _assistant_action_runs_by_id(current_store)
    resolutions: list[dict[str, str]] = []
    for prerequisite_id in prerequisite_ids:
        prerequisite = drafts_by_id.get(prerequisite_id) or drafts_by_client_id.get(prerequisite_id)
        if not prerequisite or prerequisite.get("status") != "confirmed":
            continue
        if prerequisite.get("created_by") != draft.get("created_by"):
            continue
        run = runs_by_id.get(str(prerequisite.get("result_run_id") or ""))
        if not run or run.get("status") != "succeeded":
            continue
        result_type = str(run.get("result_type") or "").strip()
        result_id = str(run.get("result_id") or "").strip()
        if result_type and result_id:
            resolutions.append({"result_id": result_id, "result_type": result_type})
    return resolutions


def _assistant_prerequisite_draft_items(
    current_store: Any,
    *,
    draft: dict[str, Any],
    prerequisite_ids: list[str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def append(item: dict[str, Any] | None) -> None:
        if not isinstance(item, dict):
            return
        item_id = str(item.get("id") or "").strip()
        if item_id and item_id in seen_ids:
            return
        if item_id:
            seen_ids.add(item_id)
        items.append(item)

    for item in getattr(current_store, "assistant_action_drafts", {}).values():
        append(item)

    repository = assistant_action_repository(current_store)
    user_id = str(draft.get("created_by") or "").strip()
    list_drafts = getattr(repository, "list_assistant_action_drafts", None)
    if callable(list_drafts) and user_id:
        for item in list_drafts(user_id=user_id) or []:
            append(item)

    get_draft = getattr(repository, "get_assistant_action_draft", None)
    if callable(get_draft):
        known_lookup_keys = {
            str(item.get("id") or "").strip() for item in items if item.get("id")
        } | {
            str(item.get("client_draft_id") or "").strip()
            for item in items
            if item.get("client_draft_id")
        }
        for prerequisite_id in prerequisite_ids:
            if prerequisite_id in known_lookup_keys:
                continue
            append(get_draft(draft_id=prerequisite_id))

    return items


def _assistant_action_runs_by_id(current_store: Any) -> dict[str, dict[str, Any]]:
    runs_by_id = {
        str(run_id): run
        for run_id, run in getattr(current_store, "assistant_action_runs", {}).items()
        if isinstance(run, dict)
    }
    repository = assistant_action_repository(current_store)
    load_chat = getattr(repository, "load_assistant_chat", None)
    if not callable(load_chat):
        return runs_by_id
    payload = load_chat() or {}
    for run_id, run in (payload.get("assistant_action_runs") or {}).items():
        if isinstance(run, dict):
            runs_by_id.setdefault(str(run.get("id") or run_id), run)
    return runs_by_id


def _set_payload_scalar_id(
    payload: dict[str, Any],
    field: str,
    result_id: str,
    *,
    prerequisite_ids: list[str],
) -> None:
    current_value = str(payload.get(field) or "").strip()
    if not current_value or current_value in prerequisite_ids:
        payload[field] = result_id


def _append_payload_list_id(
    payload: dict[str, Any],
    field: str,
    result_id: str,
    *,
    prerequisite_ids: list[str],
) -> None:
    existing = [
        item_id for item_id in _string_ids(payload.get(field)) if item_id not in prerequisite_ids
    ]
    if result_id not in existing:
        existing.append(result_id)
    payload[field] = existing


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


def _attach_assistant_run_attribution_to_scheduled_job_run(
    current_store: Any,
    *,
    action_run: dict[str, Any],
    draft: dict[str, Any],
    result: dict[str, Any],
) -> None:
    scheduled_job_run = result.get("scheduled_job_run")
    if not isinstance(scheduled_job_run, dict):
        return
    scheduled_job_run_id = str(scheduled_job_run.get("id") or "").strip()
    if not scheduled_job_run_id:
        return
    run_record = _memory_collection(current_store, "scheduled_job_runs").get(scheduled_job_run_id)
    if not isinstance(run_record, dict):
        run_record = dict(scheduled_job_run)
    now = now_iso()
    attribution = {
        "assistant_action_draft_id": draft["id"],
        "assistant_action_run_id": action_run["id"],
        "assistant_source_message_id": draft.get("source_message_id"),
        "triggered_by_assistant": True,
    }
    run_record = {
        **run_record,
        **attribution,
        "updated_at": now,
    }
    if assistant_action_repository(current_store) is None:
        _memory_collection(current_store, "scheduled_job_runs")[scheduled_job_run_id] = run_record
    result["scheduled_job_run"] = {
        **scheduled_job_run,
        **attribution,
        "updated_at": now,
    }
    action_run["result"] = deepcopy(result)
    persist_record(current_store, "save_scheduled_job_run_record", run_record)


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


def list_user_assistant_action_drafts(
    current_store: Any,
    *,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    repository = assistant_action_repository(current_store)
    list_drafts = getattr(repository, "list_assistant_action_drafts", None)
    if callable(list_drafts):
        return [dict(draft) for draft in (list_drafts(user_id=user["id"]) or [])]
    drafts = getattr(current_store, "assistant_action_drafts", {})
    return [
        dict(draft)
        for draft in drafts.values()
        if isinstance(draft, dict) and draft.get("created_by") == user["id"]
    ]


def _assistant_draft_within_time_range(
    value: Any,
    from_at: datetime | None,
    to_at: datetime | None,
) -> bool:
    if not value:
        return False
    try:
        parsed = _parse_draft_datetime(str(value))
    except Exception:
        return False
    if parsed is None:
        return False
    if from_at and parsed < from_at:
        return False
    if to_at and parsed > to_at:
        return False
    return True


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
    audit_event = assistant_action_audit_event(
        current_store,
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
        return
    _memory_collection(current_store, "assistant_action_drafts")[draft["id"]] = draft
    if run is not None:
        _memory_collection(current_store, "assistant_action_runs")[run["id"]] = run
    _memory_audit_events(current_store).extend(audit_events)


def assistant_action_audit_event(
    current_store: Any,
    *,
    actor_id: str,
    event_type: str,
    subject_id: str,
    subject_type: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": len(_memory_audit_events(current_store)) + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }


def assistant_action_repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, Any]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _memory_collection(current_store: Any, collection_name: str) -> dict[str, Any]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_audit_events(current_store: Any) -> list[dict[str, Any]]:
    collection_name = "audit_events"
    audit_events = getattr(current_store, collection_name, None)
    if not isinstance(audit_events, list):
        audit_events = []
        setattr(current_store, collection_name, audit_events)
    return audit_events


def _clean_modified_fields(modified_fields: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for field in modified_fields:
        value = str(field).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def _clean_view_surface(surface: str | None) -> str:
    value = str(surface or "").strip()
    if not value:
        return "detail_modal"
    return value[:64]


def _ensure_pending_draft_for_edit(draft: dict[str, Any]) -> None:
    if draft.get("status") == "expired":
        raise api_error(409, "DRAFT_EXPIRED", "Assistant action draft has expired")
    if draft.get("status") != "pending":
        raise api_error(409, "DRAFT_NOT_PENDING", "Assistant action draft is not pending")


def _assistant_existing_successful_run(
    current_store: Any,
    draft: dict[str, Any],
) -> dict[str, Any] | None:
    run_id = str(draft.get("result_run_id") or "").strip()
    if run_id:
        run = _assistant_action_runs_by_id(current_store).get(run_id)
        if run and run.get("status") == "succeeded":
            return run
    for run in _assistant_action_runs_by_id(current_store).values():
        if run.get("draft_id") == draft.get("id") and run.get("status") == "succeeded":
            return run
    return None


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def ensure_action_collections(current_store: Any) -> None:
    _memory_collection(current_store, "assistant_action_drafts")
    _memory_collection(current_store, "assistant_action_runs")


def ensure_draft_access(draft: dict[str, Any], *, user: dict[str, Any]) -> None:
    if "admin" in set(user.get("roles") or []):
        return
    if draft.get("created_by") == user.get("id"):
        return
    raise api_error(404, "NOT_FOUND", "Assistant action draft not found")


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
    *,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _sync_assistant_draft_reference_store(current_store)
    action = draft["action"]
    if action == "create_scheduled_job":
        return _with_action_permission_preview(
            _scheduled_job_draft_preview(current_store, draft),
            action=action,
            user=user,
        )
    if action == "create_plugin_connection":
        return _with_action_permission_preview(
            _generic_create_draft_preview(
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
            ),
            action=action,
            user=user,
        )
    if action == "create_plugin_action":
        source_resource = _draft_source_resource(
            draft,
            expected_type="plugin_action",
        )
        source_action = _draft_source_plugin_action(
            current_store,
            source_resource=source_resource,
        )
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
            source_payload=source_action,
            source_resource=source_resource,
        )
        _append_plugin_action_validation(current_store, draft, preview)
        return _with_action_permission_preview(preview, action=action, user=user)
    if action == "create_rd_task":
        return _with_action_permission_preview(
            _rd_task_draft_preview(current_store, draft),
            action=action,
            user=user,
        )
    if action == "create_ai_skill":
        return _with_action_permission_preview(
            _generic_create_draft_preview(
                draft,
                diff_fields=[
                    ("name", "名称"),
                    ("code", "编码"),
                    ("prompt_template", "Prompt 模板"),
                    ("required_context", "上下文"),
                    ("risk_level", "风险等级"),
                    ("status", "状态"),
                ],
                required_fields=["name", "code", "prompt_template"],
                resource_type="ai_skill",
            ),
            action=action,
            user=user,
        )
    if action == "create_ai_agent":
        preview = _generic_create_draft_preview(
            draft,
            diff_fields=[
                ("name", "名称"),
                ("code", "编码"),
                ("brain_app_id", "业务大脑"),
                ("model_gateway_config_id", "AI 模型"),
                ("default_skill_ids", "默认 Skills"),
                ("system_prompt", "系统 Prompt"),
                ("status", "状态"),
            ],
            required_fields=["name", "code", "brain_app_id", "system_prompt"],
            resource_type="ai_agent",
        )
        _append_ai_agent_validation(current_store, draft, preview)
        return _with_action_permission_preview(preview, action=action, user=user)
    if action == "create_analysis_draft":
        return _with_action_permission_preview(
            _generic_create_draft_preview(
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
            ),
            action=action,
            user=user,
        )
    return _with_action_permission_preview(
        _generic_create_draft_preview(
            draft,
            diff_fields=[],
            required_fields=[],
            resource_type=action,
        ),
        action=action,
        user=user,
    )


def _sync_assistant_draft_reference_store(current_store: Any) -> None:
    sync_reference_store(current_store)
    sync_ai_skill_store(current_store)
    sync_ai_agent_store(current_store)
    sync_plugin_connection_store(current_store)
    sync_plugin_action_store(current_store)


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
    if schedule_type == "cron":
        cron_expression = str(payload.get("cron_expression") or "").strip()
        if not cron_expression:
            _add_issue(validation, "cron_expression", "error", "cron_expression is required")
        elif not valid_cron_expression(cron_expression):
            _add_issue(
                validation,
                "cron_expression",
                "error",
                "Invalid cron_expression",
            )
    if schedule_type == "interval":
        interval_seconds = payload.get("interval_seconds")
        if not isinstance(interval_seconds, int) or interval_seconds <= 0:
            _add_issue(validation, "interval_seconds", "error", "interval_seconds is required")
    _append_scheduled_job_reference_validation(current_store, payload, validation)
    _finalize_validation(validation)
    return preview


def _rd_task_draft_preview(
    current_store: Any,
    draft: dict[str, Any],
) -> dict[str, Any]:
    payload = with_defaults(RD_TASK_DEFAULTS, draft.get("payload") or {})
    preview = _generic_create_draft_preview(
        {"action": draft["action"], "payload": payload},
        diff_fields=[
            ("requirement_id", "需求"),
            ("task_type", "任务类型"),
            ("title", "标题"),
            ("input.owner_role", "负责人角色"),
            ("input.acceptance_criteria", "验收标准"),
        ],
        required_fields=["requirement_id", "task_type"],
        resource_type="ai_task",
    )
    validation = preview["validation"]
    task_type = str(payload.get("task_type") or "product_detail_design")
    if task_type != "product_detail_design":
        _add_issue(
            validation,
            "task_type",
            "error",
            "Only product_detail_design rd task drafts are supported",
        )
    requirement_id = str(payload.get("requirement_id") or "").strip()
    if not requirement_id:
        _finalize_validation(validation)
        return preview
    requirement = _read_memory_dict(current_store, "requirements").get(requirement_id)
    if requirement is None:
        _add_issue(
            validation,
            "requirement_id",
            "error",
            f"Requirement not found: {requirement_id}",
        )
        _finalize_validation(validation)
        return preview
    if canonical_requirement_status(requirement.get("status")) != "planned":
        _add_issue(
            validation,
            "requirement_id",
            "error",
            "Requirement must be planned before creating an rd task",
        )
    if requirement.get("task_ids"):
        _add_issue(
            validation,
            "requirement_id",
            "error",
            "Requirement already has linked tasks",
        )
    product_id = str(requirement.get("product_id") or "").strip()
    products = _read_memory_dict(current_store, "products")
    if not product_id or product_id not in products:
        _add_issue(
            validation,
            "product_id",
            "error",
            "Requirement product is missing or inactive",
        )
    else:
        product = products[product_id]
        if product.get("status") and product.get("status") != "active":
            _add_issue(
                validation,
                "product_id",
                "error",
                "Requirement product is inactive",
            )
    version_id = str(requirement.get("version_id") or "").strip()
    if not version_id or version_id not in _read_memory_dict(current_store, "product_versions"):
        _add_issue(
            validation,
            "version_id",
            "error",
            "Planned requirement must have a version before creating an rd task",
        )
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
            _read_memory_dict(current_store, "plugin_actions"),
            action_id,
            field="plugin_action_id",
            label="Plugin action",
            validation=validation,
        )
    for connection_id in plugin_connection_ids:
        _validate_plugin_connection_ref(
            current_store,
            connection_id,
            field="plugin_connection_id",
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
            _read_memory_dict(current_store, "ai_agents"),
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
            _read_memory_dict(current_store, "ai_skills"),
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
            _read_memory_dict(current_store, "model_gateway_configs"),
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
        _validate_plugin_connection_ref(
            current_store,
            str(connection_id),
            field="connection_id",
            validation=preview["validation"],
        )
    _finalize_validation(preview["validation"])


def _append_ai_agent_validation(
    current_store: Any,
    draft: dict[str, Any],
    preview: dict[str, Any],
) -> None:
    payload = draft.get("payload") or {}
    model_gateway_config_id = payload.get("model_gateway_config_id")
    if model_gateway_config_id:
        _validate_collection_ref(
            _read_memory_dict(current_store, "model_gateway_configs"),
            str(model_gateway_config_id),
            field="model_gateway_config_id",
            label="Model gateway config",
            validation=preview["validation"],
        )
    for skill_id in _string_ids(payload.get("default_skill_ids")):
        _validate_collection_ref(
            _read_memory_dict(current_store, "ai_skills"),
            skill_id,
            field="default_skill_ids",
            label="AI skill",
            validation=preview["validation"],
        )
    _finalize_validation(preview["validation"])


def _with_action_permission_preview(
    preview: dict[str, Any],
    *,
    action: str,
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    _append_action_permission_validation(preview["validation"], action=action, user=user)
    _finalize_validation(preview["validation"])
    return preview


def _append_action_permission_validation(
    validation: dict[str, Any],
    *,
    action: str,
    user: dict[str, Any] | None,
) -> None:
    if user is None:
        return
    if action in {"create_ai_agent", "create_ai_skill"}:
        if not _user_has_permission(user, "system.ai_capabilities.manage"):
            _add_issue(
                validation,
                "permission",
                "error",
                "system.ai_capabilities.manage is required to confirm this draft",
            )
        return
    if action == "create_scheduled_job":
        if not _user_has_permission(user, "system.scheduled_jobs.manage"):
            _add_issue(
                validation,
                "permission",
                "error",
                "system.scheduled_jobs.manage is required to confirm this draft",
            )
        return
    if action in {"create_plugin_action", "create_plugin_connection"}:
        if not _user_has_permission(user, "system.plugins.manage"):
            _add_issue(
                validation,
                "permission",
                "error",
                "system.plugins.manage is required to confirm this draft",
            )
        return
    if action == "create_rd_task":
        roles = set(user.get("roles") or [])
        if "admin" not in roles and not roles.intersection({"product_owner", "rd_owner"}):
            _add_issue(
                validation,
                "permission",
                "error",
                "product_owner or rd_owner role is required to confirm this draft",
            )


def _user_has_permission(user: dict[str, Any], permission: str) -> bool:
    roles = set(user.get("roles") or [])
    permissions = set(user.get("permissions") or [])
    return "admin" in roles or "system.admin" in permissions or permission in permissions


def _generic_create_draft_preview(
    draft: dict[str, Any],
    *,
    diff_fields: list[tuple[str, str]],
    required_fields: list[str],
    resource_type: str,
    source_payload: dict[str, Any] | None = None,
    source_resource: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = draft.get("payload") or {}
    validation = {"issues": [], "status": "passed"}
    for field in required_fields:
        if _nested_value(payload, field) in (None, "", []):
            _add_issue(validation, field, "error", f"{field} is required")
    diffs = []
    for field, label in diff_fields:
        proposed = _nested_value(payload, field)
        if proposed in (None, "", []):
            continue
        current = _nested_value(source_payload, field) if source_payload else None
        if source_payload is not None and current == proposed:
            continue
        change_type = (
            "update" if source_payload is not None and current not in (None, "", []) else "create"
        )
        diffs.append(
            {
                "change_type": change_type,
                "current": deepcopy(current),
                "field": field,
                "label": label,
                "proposed": deepcopy(proposed),
            }
        )
    target = {
        "operation": "create",
        "resource_id": None,
        "resource_type": resource_type,
    }
    if source_resource:
        target["source_resource"] = _preview_source_resource(source_resource)
    preview = {
        "diffs": diffs,
        "target": target,
        "validation": validation,
    }
    _finalize_validation(validation)
    return preview


def _draft_source_resource(
    draft: dict[str, Any],
    *,
    expected_type: str,
) -> dict[str, Any] | None:
    metadata_json = (
        draft.get("metadata_json") if isinstance(draft.get("metadata_json"), dict) else {}
    )
    source_resource = metadata_json.get("source_resource")
    if not isinstance(source_resource, dict):
        return None
    if str(source_resource.get("type") or "") != expected_type:
        return None
    if not str(source_resource.get("id") or "").strip():
        return None
    return source_resource


def _draft_source_plugin_action(
    current_store: Any,
    *,
    source_resource: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not source_resource:
        return None
    action_id = str(source_resource.get("id") or "").strip()
    return _read_memory_dict(current_store, "plugin_actions").get(action_id)


def _preview_source_resource(source_resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource_id": str(source_resource.get("id") or ""),
        "resource_type": str(source_resource.get("type") or ""),
        "title": str(source_resource.get("title") or source_resource.get("id") or ""),
    }


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


def _validate_plugin_connection_ref(
    current_store: Any,
    item_id: str,
    *,
    field: str,
    validation: dict[str, Any],
) -> None:
    item = _read_memory_dict(current_store, "plugin_connections").get(item_id)
    if item is None:
        _add_issue(validation, field, "error", f"Plugin connection not found: {item_id}")
        return
    if item.get("status") and item.get("status") != "active":
        _add_issue(validation, field, "error", f"Plugin connection is inactive: {item_id}")
        return
    last_test_summary = item.get("last_test_summary")
    if not isinstance(last_test_summary, dict):
        return
    if str(last_test_summary.get("status") or "").lower() not in {"failed", "error"}:
        return
    failure_message = (
        str(last_test_summary.get("error_message") or "").strip()
        or str(last_test_summary.get("error_code") or "").strip()
        or "unknown error"
    )
    _add_issue(
        validation,
        field,
        "error",
        f"Plugin connection last test failed: {failure_message}",
        repair_action={
            "action": "open_plugin_connection_test",
            "field": field,
            "label": "打开连接测试",
            "resource_id": item_id,
            "resource_type": "plugin_connection",
        },
    )


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
    *,
    repair_action: dict[str, Any] | None = None,
) -> None:
    issue = {
        "field": field,
        "message": message,
        "severity": severity,
    }
    resolved_repair_action = repair_action or _default_repair_action(field)
    if resolved_repair_action is not None:
        issue["repair_action"] = resolved_repair_action
    validation.setdefault("issues", []).append(issue)


def _default_repair_action(field: str) -> dict[str, Any] | None:
    if field in {"cron_expression", "interval_seconds"}:
        return {
            "action": "edit_field",
            "field": field,
            "label": "修正 Cron 表达式" if field == "cron_expression" else "修正间隔时间",
        }
    if field in {"plugin_action_id", "plugin_action_ids"}:
        return {
            "action": "generate_plugin_action_draft",
            "field": field,
            "label": "生成结果动作草案",
        }
    if field in {"plugin_connection_id", "plugin_connection_ids", "connection_id"}:
        return {
            "action": "generate_connection_draft",
            "field": field,
            "label": "生成连接草案",
        }
    if field == "model_gateway_config_id":
        return {
            "action": "select_model_gateway",
            "field": field,
            "label": "选择模型网关",
        }
    if field == "agent_id":
        return {
            "action": "generate_ai_agent_draft",
            "field": field,
            "label": "生成AI角色草案",
        }
    if field == "skill_ids":
        return {
            "action": "generate_ai_skill_draft",
            "field": field,
            "label": "生成Skill草案",
        }
    if field == "permission":
        return {
            "action": "request_permission",
            "field": field,
            "label": "申请权限",
        }
    return None


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


def _assistant_action_required_permissions(action: str) -> list[str]:
    if action in {"create_ai_agent", "create_ai_skill"}:
        return ["system.ai_capabilities.manage"]
    if action == "create_scheduled_job":
        return ["system.scheduled_jobs.manage"]
    if action in {"create_plugin_action", "create_plugin_connection"}:
        return ["system.plugins.manage"]
    if action == "create_rd_task":
        return ["role:product_owner_or_rd_owner"]
    return []


def _assistant_action_missing_permissions(
    *,
    action: str,
    required_permissions: list[str],
    user: dict[str, Any] | None,
) -> list[str]:
    if user is None:
        return []
    if action == "create_rd_task":
        roles = set(user.get("roles") or [])
        if "admin" in roles or roles.intersection({"product_owner", "rd_owner"}):
            return []
        return required_permissions
    return [
        permission
        for permission in required_permissions
        if not _user_has_permission(user, permission)
    ]


def _assistant_action_draft_audit_events(
    current_store: Any,
    *,
    draft_id: str,
) -> list[dict[str, Any]]:
    repository = assistant_action_repository(current_store)
    list_events = getattr(repository, "list_audit_events", None)
    if callable(list_events):
        try:
            events = list_events(
                ai_task_id=None,
                actor_id=None,
                created_from=None,
                created_to=None,
                event_type=None,
                subject_id=draft_id,
                subject_type="assistant_action_draft",
            )
        except TypeError:
            events = list_events(
                subject_id=draft_id,
                subject_type="assistant_action_draft",
            )
    else:
        events = [
            event
            for event in _memory_audit_events(current_store)
            if event.get("subject_type") == "assistant_action_draft"
            and event.get("subject_id") == draft_id
        ]
    return sorted(
        [dict(event) for event in events or [] if isinstance(event, dict)],
        key=lambda item: (
            str(item.get("created_at") or ""),
            _safe_int(item.get("sequence")),
            str(item.get("id") or ""),
        ),
    )


def _assistant_action_draft_governance(
    current_store: Any,
    draft: dict[str, Any],
    *,
    preview: dict[str, Any],
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata_json = (
        draft.get("metadata_json")
        if isinstance(draft.get("metadata_json"), dict)
        else {}
    )
    validation = preview.get("validation") if isinstance(preview.get("validation"), dict) else {}
    validation_issues = (
        validation.get("issues") if isinstance(validation.get("issues"), list) else []
    )
    permission_issues = [
        dict(issue)
        for issue in validation_issues
        if isinstance(issue, dict) and str(issue.get("field") or "") == "permission"
    ]
    required_permissions = _assistant_action_required_permissions(str(draft.get("action") or ""))
    missing_permissions = _assistant_action_missing_permissions(
        action=str(draft.get("action") or ""),
        required_permissions=required_permissions,
        user=user,
    )
    permission_status = "blocked" if missing_permissions or permission_issues else "passed"
    target = preview.get("target") if isinstance(preview.get("target"), dict) else {}
    diffs = preview.get("diffs") if isinstance(preview.get("diffs"), list) else []
    payload = draft.get("payload") if isinstance(draft.get("payload"), dict) else {}
    normalized_diffs = [
        {
            "change_type": str(diff.get("change_type") or ""),
            "field": str(diff.get("field") or ""),
            "label": str(diff.get("label") or diff.get("field") or ""),
        }
        for diff in diffs
        if isinstance(diff, dict)
    ]
    failure_history = metadata_json.get("failure_history")
    if not isinstance(failure_history, list):
        failure_history = []
    current_failure = metadata_json.get("failure")
    failure_sources = list(failure_history)
    if isinstance(current_failure, dict):
        failure_sources.append({"failure": current_failure})
    last_failure = failure_sources[-1] if failure_sources else {}
    last_failure_payload = (
        last_failure.get("failure") if isinstance(last_failure.get("failure"), dict) else {}
    )
    audit_events = _assistant_action_draft_audit_events(
        current_store,
        draft_id=str(draft.get("id") or ""),
    )
    latest_event = audit_events[-1] if audit_events else {}
    audit_snapshot = {
        "event_count": len(audit_events),
        "event_types": sorted(
            {
                str(event.get("event_type") or "")
                for event in audit_events
                if str(event.get("event_type") or "")
            }
        ),
        "latest_actor_id": latest_event.get("actor_id"),
        "latest_event_at": latest_event.get("created_at"),
        "latest_event_id": latest_event.get("id"),
        "latest_event_type": latest_event.get("event_type"),
    }
    retry_snapshot = {
        "can_retry": draft.get("status") == "failed",
        "failure_count": len(failure_sources),
        "last_failure_code": last_failure_payload.get("code"),
        "last_failure_message": last_failure_payload.get("message"),
        "retry_count": _safe_int(metadata_json.get("retry_count")),
        "retry_reason": metadata_json.get("retry_reason"),
    }
    risk_level = str(draft.get("risk_level") or "medium")
    validation_status = str(validation.get("status") or "unknown")
    permission_issue_count = len(permission_issues) + len(missing_permissions)
    decision = assistant_action_draft_decision(
        audit_event_count=audit_snapshot["event_count"],
        draft=draft,
        last_failure_payload=last_failure_payload,
        missing_permissions=missing_permissions,
        permission_issue_count=permission_issue_count,
        permission_status=permission_status,
        risk_level=risk_level,
        validation_issue_count=len(validation_issues),
        validation_status=validation_status,
    )
    return {
        "audit": audit_snapshot,
        "decision": decision,
        "diff": {
            "changed_fields": normalized_diffs,
            "count": len(normalized_diffs),
        },
        "impact": {
            "changed_field_count": len(normalized_diffs),
            "operation": target.get("operation") or "create",
            "payload_field_count": len(payload),
            "resource_id": target.get("resource_id"),
            "resource_type": target.get("resource_type") or draft.get("action"),
            "source_resource": target.get("source_resource"),
        },
        "permissions": {
            "issue_count": permission_issue_count,
            "issues": permission_issues,
            "missing_permissions": missing_permissions,
            "required_permissions": required_permissions,
            "status": permission_status,
        },
        "retries": retry_snapshot,
        "risk": {
            "level": risk_level,
            "reason": metadata_json.get("risk_reason"),
        },
    }


def public_assistant_action_draft(
    draft: dict[str, Any],
    *,
    current_store: Any,
    user: dict[str, Any] | None = None,
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
    wizard_steps = public["metadata_json"].get("wizard_steps")
    if isinstance(wizard_steps, list):
        public["wizard_steps"] = deepcopy(wizard_steps)
    result_run = _assistant_public_result_run(current_store, draft)
    if result_run is not None:
        public["result_run"] = result_run
    preview_draft = _draft_with_resolved_prerequisites(current_store, draft)
    preview = assistant_action_draft_preview(
        current_store,
        preview_draft,
        user=user,
    )
    public["preview"] = preview
    public["governance"] = _assistant_action_draft_governance(
        current_store,
        draft,
        preview=preview,
        user=user,
    )
    return {key: value for key, value in public.items() if value is not None}


def _assistant_public_result_run(
    current_store: Any,
    draft: dict[str, Any],
) -> dict[str, Any] | None:
    run_id = str(draft.get("result_run_id") or "").strip()
    if not run_id:
        return None
    run = _assistant_action_runs_by_id(current_store).get(run_id)
    if not run:
        return None
    return public_assistant_action_run(run)


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
