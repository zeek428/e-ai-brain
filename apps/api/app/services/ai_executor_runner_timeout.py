from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.ai_executor_runner_constants import AI_EXECUTOR_TASK_TERMINAL_STATUSES
from app.services.ai_executor_runner_task_context import (
    _ai_executor_task_visible_to_user,
    _datetime_value,
    _task_public,
)
from app.services.ai_executor_runners import (
    _append_task_logs,
    _ensure_admin,
    _persist_record,
    _read_collection,
    _sync_runner_completion_to_ai_task,
    _sync_runner_completion_to_scheduled_run,
    sync_ai_executor_task_store,
)
from app.services.ai_executor_task_reliability import (
    apply_task_dead_letter,
    apply_task_lease_requeue,
    should_dead_letter_after_lease,
    task_lease_expired,
)
from app.services.operational_records import record_audit_event
from app.services.product_scope import product_scope_filter


def timeout_ai_executor_tasks_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    now = _datetime_value(getattr(payload, "now", None)) or datetime.now(UTC)
    task_product_scope_ids = product_scope_filter(user)
    sync_ai_executor_task_store(current_store, product_scope_ids=task_product_scope_ids)
    dead_lettered: list[dict[str, Any]] = []
    requeued: list[dict[str, Any]] = []
    timed_out: list[dict[str, Any]] = []
    for task in list(_read_collection(current_store, "ai_executor_tasks").values()):
        if task_product_scope_ids is not None and not _ai_executor_task_visible_to_user(
            current_store,
            task=task,
            user=user,
        ):
            continue
        if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
            continue
        if task_lease_expired(task, now=now):
            updated_task = _expire_task_lease(current_store, now=now, task=task, user=user)
            if updated_task.get("status") == "dead_letter":
                dead_lettered.append(updated_task)
            else:
                requeued.append(updated_task)
            continue
        reference_at = (
            _datetime_value(task.get("claimed_at"))
            or _datetime_value(task.get("updated_at"))
            or _datetime_value(task.get("created_at"))
            or now
        )
        timeout_seconds = int(task.get("timeout_seconds") or 1800)
        if (now - reference_at).total_seconds() < timeout_seconds:
            continue
        timed_out.append(_timeout_task(current_store, now=now, task=task, user=user))
    summary = timeout_scan_summary(
        dead_lettered=dead_lettered,
        now=now,
        requeued=requeued,
        timed_out=timed_out,
    )
    return {
        "dead_letter_task_ids": [task["id"] for task in dead_lettered],
        "next_actions": timeout_scan_next_actions(
            dead_lettered=dead_lettered,
            requeued=requeued,
            timed_out=timed_out,
        ),
        "requeued_task_ids": [task["id"] for task in requeued],
        "summary": summary,
        "timed_out_task_ids": [task["id"] for task in timed_out],
        "tasks": [_task_public(task) for task in [*timed_out, *requeued, *dead_lettered]],
    }


def _expire_task_lease(
    current_store: Any,
    *,
    now: datetime,
    task: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    now_iso = now.isoformat()
    reason = "AI executor task lease expired"
    if should_dead_letter_after_lease(task):
        updated_task = apply_task_dead_letter(task, now=now, reason=reason)
        return _persist_timeout_task(
            current_store,
            event_type="ai_executor_task.dead_lettered",
            log_level="error",
            log_message="Task moved to dead letter after lease expired",
            payload={"runner_id": updated_task.get("runner_id"), "reason": reason},
            task=updated_task,
            timestamp=now_iso,
            user=user,
        )

    updated_task = apply_task_lease_requeue(task, now=now, reason=reason)
    return _persist_timeout_task(
        current_store,
        event_type="ai_executor_task.lease_requeued",
        log_level="warning",
        log_message="Task lease expired; requeued for another claim",
        payload={"runner_id": updated_task.get("runner_id"), "reason": reason},
        task=updated_task,
        timestamp=now_iso,
        user=user,
    )


def _timeout_task(
    current_store: Any,
    *,
    now: datetime,
    task: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    now_iso = now.isoformat()
    timeout_seconds = int(task.get("timeout_seconds") or 1800)
    updated_task = {
        **task,
        "error_code": "AI_EXECUTOR_TASK_TIMEOUT",
        "error_message": f"AI executor task timed out after {timeout_seconds}s",
        "finished_at": now_iso,
        "status": "timed_out",
        "updated_at": now_iso,
    }
    return _persist_timeout_task(
        current_store,
        event_type="ai_executor_task.timed_out",
        log_level="error",
        log_message=f"Task timed out after {timeout_seconds}s",
        payload={"runner_id": updated_task.get("runner_id"), "timeout_seconds": timeout_seconds},
        task=updated_task,
        timestamp=now_iso,
        user=user,
    )


def _persist_timeout_task(
    current_store: Any,
    *,
    event_type: str,
    log_level: str,
    log_message: str,
    payload: dict[str, Any],
    task: dict[str, Any],
    timestamp: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    updated_task = {
        **task,
        "logs": _append_task_logs(
            task,
            [{"level": log_level, "message": log_message, "timestamp": timestamp}],
        ),
    }
    audit_event = record_audit_event(
        current_store,
        event_type=event_type,
        actor_id=user["id"],
        subject_type="ai_executor_task",
        subject_id=updated_task["id"],
        payload=payload,
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        updated_task,
        audit_event=audit_event,
    )
    runner_id = str(updated_task.get("runner_id") or user["id"])
    _sync_runner_completion_to_scheduled_run(current_store, task=updated_task, runner_id=runner_id)
    _sync_runner_completion_to_ai_task(current_store, task=updated_task, runner_id=runner_id)
    return updated_task


def timeout_scan_summary(
    *,
    dead_lettered: list[dict[str, Any]],
    now: datetime,
    requeued: list[dict[str, Any]],
    timed_out: list[dict[str, Any]],
) -> dict[str, Any]:
    manual_attention_required = bool(dead_lettered or timed_out)
    if manual_attention_required:
        status = "attention_required"
        message = "发现需要人工处理的 Runner 任务，请查看死信或超时任务日志。"
    elif requeued:
        status = "requeued"
        message = "已将租约过期任务重派回队列，等待 Runner 重新认领。"
    else:
        status = "no_changes"
        message = "未发现需要处理的 Runner 超时或租约过期任务。"
    return {
        "dead_letter_count": len(dead_lettered),
        "manual_attention_required": manual_attention_required,
        "message": message,
        "requeued_count": len(requeued),
        "scanned_at": now.isoformat(),
        "status": status,
        "timed_out_count": len(timed_out),
        "total_affected": len(dead_lettered) + len(requeued) + len(timed_out),
    }


def timeout_scan_next_actions(
    *,
    dead_lettered: list[dict[str, Any]],
    requeued: list[dict[str, Any]],
    timed_out: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if requeued:
        actions.append(
            {
                "description": "重派任务已回到 queued，在线 Runner 会在后续轮询中重新认领。",
                "key": "watch_requeued_tasks",
                "label": "等待 Runner 重新认领",
                "severity": "info",
                "task_ids": [task["id"] for task in requeued],
            },
        )
    if dead_lettered:
        actions.append(
            {
                "description": "死信任务已超过最大重派次数，需要查看日志、修复 Runner 或手动重试。",
                "key": "inspect_dead_letter_tasks",
                "label": "查看死信任务日志",
                "severity": "error",
                "task_ids": [task["id"] for task in dead_lettered],
            },
        )
    if timed_out:
        actions.append(
            {
                "description": "超时任务已熔断为 timed_out，请检查执行器日志后决定是否重试。",
                "key": "review_timed_out_tasks",
                "label": "检查超时任务",
                "severity": "warning",
                "task_ids": [task["id"] for task in timed_out],
            },
        )
    if not actions:
        actions.append(
            {
                "description": "当前没有需要重派、死信或熔断的 Runner 任务。",
                "key": "no_action_required",
                "label": "无需处理",
                "severity": "success",
                "task_ids": [],
            },
        )
    return actions
