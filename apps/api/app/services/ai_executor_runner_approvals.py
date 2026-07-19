from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any

from app.api.deps import api_error, require_permissions
from app.core.listing import add_list_observability, sort_list_items
from app.services.ai_executor_runner_safety import RUNNER_SAFETY_POLICY_VERSION
from app.services.operational_records import record_audit_event, save_single_repository_record
from app.services.plugin_projection import public_action
from app.services.plugin_store_helpers import (
    _put_memory_record,
    _read_memory_record,
    ensure_non_blank,
    persist_record,
    require_admin,
    sync_plugin_action_store,
)

AI_EXECUTOR_APPROVAL_REQUEST_STATUSES = {"approved", "expired", "pending", "rejected"}
AI_EXECUTOR_APPROVAL_REQUEST_SORT_FIELDS = {
    "approved_at",
    "created_at",
    "executor_type",
    "id",
    "requested_at",
    "risk_level",
    "runner_id",
    "status",
    "updated_at",
}


def _ensure_admin(user: dict[str, Any]) -> None:
    require_permissions(user, {"system.plugins.manage"})


def _ensure_enum(value: str | None, allowed_values: set[str], field: str) -> str:
    text = str(value or "").strip()
    if not text or text not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")
    return text


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    required = (
        "list_ai_executor_approval_requests",
        "save_ai_executor_approval_request_record",
    )
    if all(callable(getattr(repository, method_name, None)) for method_name in required):
        return repository
    return None


def _persist_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    _memory_dict(current_store, "ai_executor_approval_requests")[record["id"]] = record
    save_single_repository_record(
        current_store,
        "save_ai_executor_approval_request_record",
        record,
        audit_event=audit_event,
    )


def sync_ai_executor_approval_request_store(
    current_store: Any,
    *,
    action_id: str | None = None,
    runner_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = _repository(current_store)
    if repository is None:
        return
    records = repository.list_ai_executor_approval_requests(
        action_id=action_id,
        runner_id=runner_id,
        status=status,
    )
    collection_name = "ai_executor_approval_requests"
    setattr(
        current_store,
        collection_name,
        {str(record["id"]): dict(record) for record in records if record.get("id")},
    )


def save_pending_ai_executor_approval_request(
    current_store: Any,
    *,
    approval_request: dict[str, Any],
    requested_by: str,
    safety_snapshot: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    approval_request_id = str(approval_request.get("approval_request_id") or "").strip()
    if not approval_request_id:
        raise api_error(400, "VALIDATION_ERROR", "approval_request_id is required")
    existing = _read_memory_dict(
        current_store,
        "ai_executor_approval_requests",
    ).get(approval_request_id)
    record = {
        **(existing or {}),
        "action_id": approval_request.get("action_id"),
        "ai_task_id": approval_request.get("ai_task_id"),
        "approval": safety_snapshot.get("approval") or {},
        "approval_request": approval_request,
        "blocked_operations": safety_snapshot.get("blocked_operations") or [],
        "connection_id": approval_request.get("connection_id"),
        "created_at": (existing or {}).get("created_at") or now,
        "executor_type": approval_request.get("executor_type"),
        "id": approval_request_id,
        "requested_at": (existing or {}).get("requested_at") or now,
        "requested_by": (existing or {}).get("requested_by") or requested_by,
        "risk_level": safety_snapshot.get("risk_level") or "high",
        "runner_id": approval_request.get("runner_id"),
        "scheduled_job_id": approval_request.get("scheduled_job_id"),
        "scheduled_job_run_id": approval_request.get("scheduled_job_run_id"),
        "status": (existing or {}).get("status") or "pending",
        "updated_at": now,
        "workspace_root": approval_request.get("workspace_root") or "",
    }
    if not record["executor_type"]:
        raise api_error(400, "VALIDATION_ERROR", "executor_type is required")
    if not record["workspace_root"]:
        raise api_error(400, "VALIDATION_ERROR", "workspace_root is required")
    _persist_record(current_store, record)
    return record


def _parse_expires_at(value: str | None) -> str:
    if not value:
        return (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", "Invalid expires_at") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    parsed = parsed.astimezone(UTC)
    if parsed <= datetime.now(UTC):
        raise api_error(400, "VALIDATION_ERROR", "expires_at must be in the future")
    return parsed.isoformat()


def approval_operations_from_request(
    *,
    approval_request: dict[str, Any] | None,
    approved_operations: list[str] | None,
) -> list[str]:
    request_operations = (
        approval_request.get("blocked_operations")
        if isinstance(approval_request, dict)
        else None
    )
    raw_operations = approved_operations or request_operations or []
    operations = sorted({str(item).strip() for item in raw_operations if str(item).strip()})
    if not operations:
        raise api_error(400, "VALIDATION_ERROR", "approved_operations is required")
    return operations


def build_ai_executor_approval_snapshot(
    *,
    approval_id: str,
    approval_request: dict[str, Any] | None,
    approved_by: str,
    approved_operations: list[str] | None,
    expires_at: str | None,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "approval_id": approval_id,
        "approval_request_id": (
            approval_request.get("approval_request_id")
            if isinstance(approval_request, dict)
            else None
        ),
        "approved": True,
        "approved_at": datetime.now(UTC).isoformat(),
        "approved_by": approved_by,
        "approved_operations": approval_operations_from_request(
            approval_request=approval_request,
            approved_operations=approved_operations,
        ),
        "expires_at": _parse_expires_at(expires_at),
        "mode": "platform_human_approval",
        "policy_version": RUNNER_SAFETY_POLICY_VERSION,
        "reason": reason,
    }


def mark_ai_executor_approval_request_approved(
    current_store: Any,
    *,
    approval: dict[str, Any],
    approval_request: dict[str, Any] | None,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    approval_request_id = approval.get("approval_request_id")
    if not approval_request_id:
        return None
    sync_ai_executor_approval_request_store(current_store)
    existing = _read_memory_dict(
        current_store,
        "ai_executor_approval_requests",
    ).get(str(approval_request_id))
    if existing is None and isinstance(approval_request, dict):
        existing = {
            "action_id": approval_request.get("action_id"),
            "ai_task_id": approval_request.get("ai_task_id"),
            "approval_request": approval_request,
            "blocked_operations": approval_request.get("blocked_operations") or [],
            "connection_id": approval_request.get("connection_id"),
            "created_at": approval["approved_at"],
            "executor_type": approval_request.get("executor_type"),
            "id": approval_request_id,
            "requested_at": approval["approved_at"],
            "requested_by": user["id"],
            "risk_level": "high",
            "runner_id": approval_request.get("runner_id"),
            "scheduled_job_id": approval_request.get("scheduled_job_id"),
            "scheduled_job_run_id": approval_request.get("scheduled_job_run_id"),
            "workspace_root": approval_request.get("workspace_root") or "",
        }
    if existing is None:
        return None
    record = {
        **existing,
        "approval": approval,
        "approved_at": approval["approved_at"],
        "approved_by": user["id"],
        "expires_at": approval["expires_at"],
        "reason": approval.get("reason"),
        "status": "approved",
        "updated_at": approval["approved_at"],
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_approval_request.approved",
        actor_id=user["id"],
        subject_type="ai_executor_approval_request",
        subject_id=str(approval_request_id),
        payload={
            "approval_id": approval["approval_id"],
            "approved_operations": approval["approved_operations"],
            "expires_at": approval["expires_at"],
            "runner_id": record.get("runner_id"),
            "scheduled_job_id": record.get("scheduled_job_id"),
            "scheduled_job_run_id": record.get("scheduled_job_run_id"),
        },
    )
    _persist_record(current_store, record, audit_event=audit_event)
    return record


def list_ai_executor_approval_requests_response(
    *,
    action_id: str | None = None,
    current_store: Any,
    page: int | None = None,
    page_size: int | None = None,
    runner_id: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None = None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if status is not None:
        _ensure_enum(status, AI_EXECUTOR_APPROVAL_REQUEST_STATUSES, "status")
    if sort_by is not None:
        _ensure_enum(sort_by, AI_EXECUTOR_APPROVAL_REQUEST_SORT_FIELDS, "sort_by")
    sort_order = _ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "updated_at"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    with_pagination = page is not None or page_size is not None
    repository = getattr(current_store, "repository", None)
    count_page = getattr(repository, "count_ai_executor_approval_requests", None)
    list_page = getattr(repository, "list_ai_executor_approval_requests_page", None)
    filters = {"action_id": action_id, "runner_id": runner_id, "status": status}
    if with_pagination and callable(count_page) and callable(list_page):
        total = count_page(**filters)
        items = list_page(
            **filters,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_approval_requests",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at or perf_counter(),
        )
    sync_ai_executor_approval_request_store(
        current_store,
        action_id=action_id,
        runner_id=runner_id,
        status=status,
    )
    items = []
    for item in _read_memory_dict(current_store, "ai_executor_approval_requests").values():
        if action_id is not None and item.get("action_id") != action_id:
            continue
        if runner_id is not None and item.get("runner_id") != runner_id:
            continue
        if status is not None and item.get("status") != status:
            continue
        items.append(dict(item))
    items = sort_list_items(
        items,
        allowed_fields=AI_EXECUTOR_APPROVAL_REQUEST_SORT_FIELDS,
        default_sort_by="updated_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    page_items = items
    if with_pagination:
        start = (resolved_page - 1) * resolved_page_size
        page_items = items[start : start + resolved_page_size]
    return add_list_observability(
        {
            "items": page_items,
            "page": resolved_page,
            "page_size": resolved_page_size,
            "total": len(items),
        },
        filters=filters,
        list_name="ai_executor_approval_requests",
        page=resolved_page,
        page_size=resolved_page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=started_at or perf_counter(),
    )


def _approval_request_payload(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _reject_rd_collaboration_generic_approval(value: Any) -> None:
    record = value if isinstance(value, dict) else {}
    request_snapshot = record.get("approval_request")
    if not isinstance(request_snapshot, dict):
        request_snapshot = record
    if request_snapshot.get("source") == "rd_collaboration_work_item":
        raise api_error(
            409,
            "RD_COLLABORATION_APPROVAL_DECISION_REQUIRED",
            "Collaboration approval must be resolved through its frozen decision",
        )


def approve_plugin_action_ai_executor_response(
    *,
    action_id: str,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_action_store(current_store)
    action = _read_memory_record(current_store, "plugin_actions", action_id)
    if action is None:
        raise api_error(404, "NOT_FOUND", "Plugin action not found")

    approval_request = _approval_request_payload(getattr(payload, "approval_request", None))
    _reject_rd_collaboration_generic_approval(approval_request)
    approval_request_id = str((approval_request or {}).get("approval_request_id") or "").strip()
    if approval_request_id:
        sync_ai_executor_approval_request_store(current_store)
        _reject_rd_collaboration_generic_approval(
            _read_memory_record(
                current_store,
                "ai_executor_approval_requests",
                approval_request_id,
            )
        )
    approval_id = (
        ensure_non_blank(getattr(payload, "approval_id", None), "approval_id")
        if getattr(payload, "approval_id", None)
        else current_store.new_id("ai_executor_approval")
    )
    approval = build_ai_executor_approval_snapshot(
        approval_id=approval_id,
        approval_request=approval_request,
        approved_by=user["id"],
        approved_operations=getattr(payload, "approved_operations", None),
        expires_at=getattr(payload, "expires_at", None),
        reason=getattr(payload, "reason", None),
    )
    request_config = {
        **dict(action.get("request_config") or {}),
        "ai_executor_approval": approval,
    }
    action = {
        **action,
        "request_config": request_config,
        "requires_human_review": True,
        "updated_at": approval["approved_at"],
    }
    _put_memory_record(current_store, "plugin_actions", action)
    audit_event = record_audit_event(
        current_store,
        event_type="plugin_action.ai_executor_approved",
        actor_id=user["id"],
        subject_type="plugin_action",
        subject_id=action_id,
        payload={
            "approval_id": approval["approval_id"],
            "approval_request_id": approval["approval_request_id"],
            "approved_operations": approval["approved_operations"],
            "expires_at": approval["expires_at"],
            "plugin_id": action["plugin_id"],
            "reason": approval.get("reason"),
        },
    )
    persist_record(
        current_store,
        "save_plugin_action_record",
        action,
        audit_event=audit_event,
    )
    mark_ai_executor_approval_request_approved(
        current_store,
        approval=approval,
        approval_request=approval_request,
        user=user,
    )
    return {"action": public_action(action), "approval": approval}


def approve_ai_executor_approval_request_response(
    *,
    approval_request_id: str,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_ai_executor_approval_request_store(current_store)
    approval_request_record = _read_memory_record(
        current_store,
        "ai_executor_approval_requests",
        approval_request_id,
    )
    if approval_request_record is None:
        raise api_error(404, "NOT_FOUND", "AI executor approval request not found")
    _reject_rd_collaboration_generic_approval(approval_request_record)
    if approval_request_record.get("status") == "approved":
        return {
            "action": None,
            "approval": approval_request_record.get("approval") or {},
            "approval_request": approval_request_record,
        }

    approval_id = (
        ensure_non_blank(getattr(payload, "approval_id", None), "approval_id")
        if getattr(payload, "approval_id", None)
        else current_store.new_id("ai_executor_approval")
    )
    request_snapshot = _approval_request_payload(approval_request_record.get("approval_request"))
    approval = build_ai_executor_approval_snapshot(
        approval_id=approval_id,
        approval_request=request_snapshot,
        approved_by=user["id"],
        approved_operations=getattr(payload, "approved_operations", None),
        expires_at=getattr(payload, "expires_at", None),
        reason=getattr(payload, "reason", None),
    )
    updated_request = mark_ai_executor_approval_request_approved(
        current_store,
        approval=approval,
        approval_request=request_snapshot,
        user=user,
    )

    action_payload = None
    action_id = approval_request_record.get("action_id")
    if action_id:
        sync_plugin_action_store(current_store)
        action = _read_memory_record(current_store, "plugin_actions", str(action_id))
        if action is not None:
            request_config = {
                **dict(action.get("request_config") or {}),
                "ai_executor_approval": approval,
            }
            action = {
                **action,
                "request_config": request_config,
                "requires_human_review": True,
                "updated_at": approval["approved_at"],
            }
            _put_memory_record(current_store, "plugin_actions", action)
            audit_event = record_audit_event(
                current_store,
                event_type="plugin_action.ai_executor_approved",
                actor_id=user["id"],
                subject_type="plugin_action",
                subject_id=str(action_id),
                payload={
                    "approval_id": approval["approval_id"],
                    "approval_request_id": approval["approval_request_id"],
                    "approved_operations": approval["approved_operations"],
                    "expires_at": approval["expires_at"],
                    "plugin_id": action["plugin_id"],
                    "reason": approval.get("reason"),
                    "source": "ai_executor_approval_request",
                },
            )
            persist_record(
                current_store,
                "save_plugin_action_record",
                action,
                audit_event=audit_event,
            )
            action_payload = public_action(action)

    return {
        "action": action_payload,
        "approval": approval,
        "approval_request": updated_request or approval_request_record,
    }
