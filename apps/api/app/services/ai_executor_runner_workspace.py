from __future__ import annotations

import posixpath
import re
from datetime import UTC, datetime
from typing import Any

from app.services.operational_records import record_audit_event

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def normalize_workspace_root(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text == "*":
        return "*"
    normalized = posixpath.normpath(text.replace("\\", "/"))
    if normalized == ".":
        return ""
    if _WINDOWS_DRIVE_RE.match(normalized):
        normalized = normalized[0].lower() + normalized[1:]
    return normalized


def _is_same_or_child(workspace_root: str, allowed_root: str) -> bool:
    if workspace_root == allowed_root:
        return True
    if allowed_root == "/":
        return workspace_root.startswith("/")
    prefix = allowed_root.rstrip("/") + "/"
    return workspace_root.startswith(prefix)


def workspace_match_detail(
    runner: dict[str, Any],
    workspace_root: Any,
) -> dict[str, Any]:
    normalized_workspace = normalize_workspace_root(workspace_root)
    normalized_roots = [
        root
        for root in (
            normalize_workspace_root(root) for root in (runner.get("workspace_roots") or [])
        )
        if root
    ]
    if not normalized_workspace:
        return {
            "allowed": False,
            "matched_root": None,
            "reason": "workspace_root_required",
            "workspace_root": workspace_root,
            "workspace_roots": normalized_roots,
        }
    if not normalized_roots or "*" in normalized_roots:
        return {
            "allowed": True,
            "matched_root": "*",
            "reason": "wildcard_allowed",
            "workspace_root": normalized_workspace,
            "workspace_roots": normalized_roots or ["*"],
        }
    for allowed_root in normalized_roots:
        if _is_same_or_child(normalized_workspace, allowed_root):
            return {
                "allowed": True,
                "matched_root": allowed_root,
                "reason": "matched_workspace_root",
                "workspace_root": normalized_workspace,
                "workspace_roots": normalized_roots,
            }
    return {
        "allowed": False,
        "matched_root": None,
        "reason": "outside_workspace_roots",
        "workspace_root": normalized_workspace,
        "workspace_roots": normalized_roots,
    }


def workspace_root_allowed(runner: dict[str, Any], workspace_root: Any) -> bool:
    return bool(workspace_match_detail(runner, workspace_root).get("allowed"))


def reject_ai_executor_task_workspace(
    current_store: Any,
    *,
    append_task_logs: Any,
    persist_record: Any,
    runner: dict[str, Any],
    sync_ai_task: Any,
    sync_scheduled_run: Any,
    task: dict[str, Any],
    workspace_match: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    message = "Task workspace root is outside the runner workspace whitelist"
    updated_task = {
        **task,
        "error_code": "AI_EXECUTOR_WORKSPACE_NOT_ALLOWED",
        "error_message": message,
        "finished_at": now,
        "logs": append_task_logs(
            task,
            [
                {
                    "level": "error",
                    "message": (
                        f"{message}: {workspace_match.get('workspace_root')} not in "
                        f"{workspace_match.get('workspace_roots')}"
                    ),
                    "timestamp": now,
                }
            ],
        ),
        "status": "failed",
        "updated_at": now,
    }
    runner_id = str(runner.get("id") or "")
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.workspace_rejected",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task["id"],
        payload={
            "runner_id": runner.get("id"),
            "workspace_root": workspace_match.get("workspace_root"),
            "workspace_roots": workspace_match.get("workspace_roots"),
        },
    )
    persist_record(
        current_store,
        "save_ai_executor_task_record",
        updated_task,
        audit_event=audit_event,
    )
    sync_scheduled_run(current_store, task=updated_task, runner_id=runner_id)
    sync_ai_task(current_store, task=updated_task, runner_id=runner_id)
    return updated_task
