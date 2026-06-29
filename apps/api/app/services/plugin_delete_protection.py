from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services.scheduled_job_refs import scheduled_job_multi_ids


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if isinstance(collection, dict):
        return collection
    return {}


def usage_names(items: list[dict[str, Any]], *, limit: int = 3) -> str:
    names = [str(item.get("name") or item.get("code") or item.get("id")) for item in items[:limit]]
    suffix = f" 等 {len(items)} 个" if len(items) > limit else f" {len(items)} 个"
    return f"{'、'.join(names)}{suffix}" if names else f"{len(items)} 个"


def usage_summary(usages: dict[str, list[dict[str, Any]]]) -> str:
    labels = {
        "actions": "动作",
        "connections": "连接",
        "logs": "定时作业调用记录",
        "scheduled_jobs": "定时作业",
    }
    parts = [
        f"{labels[key]}：{usage_names(items)}"
        for key, items in usages.items()
        if items
    ]
    return "；".join(parts)


def ensure_not_used_for_delete(
    usages: dict[str, list[dict[str, Any]]],
    *,
    object_label: str,
) -> None:
    summary = usage_summary(usages)
    if not summary:
        return
    raise api_error(
        409,
        "PLUGIN_RESOURCE_IN_USE",
        f"{object_label}正在被使用，不能删除。{summary}。请先解除引用、删除下级配置，或将其停用。",
    )


def _scheduled_job_references_any(
    job: dict[str, Any],
    *,
    action_ids: set[str] | None = None,
    connection_ids: set[str] | None = None,
) -> bool:
    if action_ids:
        referenced_action_ids = set(
            scheduled_job_multi_ids(job, "plugin_action_ids", "plugin_action_id"),
        )
        if referenced_action_ids & action_ids:
            return True
    if connection_ids:
        referenced_connection_ids = set(
            scheduled_job_multi_ids(job, "plugin_connection_ids", "plugin_connection_id"),
        )
        if referenced_connection_ids & connection_ids:
            return True
    return False


def plugin_delete_usages(current_store: Any, plugin_id: str) -> dict[str, list[dict[str, Any]]]:
    connections = [
        connection
        for connection in _read_memory_dict(current_store, "plugin_connections").values()
        if connection.get("plugin_id") == plugin_id
    ]
    actions = [
        action
        for action in _read_memory_dict(current_store, "plugin_actions").values()
        if action.get("plugin_id") == plugin_id
    ]
    connection_ids = {connection["id"] for connection in connections}
    action_ids = {action["id"] for action in actions}
    scheduled_jobs = [
        job
        for job in _read_memory_dict(current_store, "scheduled_jobs").values()
        if _scheduled_job_references_any(
            job,
            action_ids=action_ids,
            connection_ids=connection_ids,
        )
    ]
    logs = [
        log
        for log in _read_memory_dict(current_store, "plugin_invocation_logs").values()
        if log.get("plugin_id") == plugin_id
        or log.get("action_id") in action_ids
        or log.get("connection_id") in connection_ids
    ]
    return {
        "connections": connections,
        "actions": actions,
        "scheduled_jobs": scheduled_jobs,
        "logs": logs,
    }


def connection_delete_usages(
    current_store: Any,
    connection_id: str,
) -> dict[str, list[dict[str, Any]]]:
    actions = [
        action
        for action in _read_memory_dict(current_store, "plugin_actions").values()
        if action.get("connection_id") == connection_id
    ]
    scheduled_jobs = [
        job
        for job in _read_memory_dict(current_store, "scheduled_jobs").values()
        if _scheduled_job_references_any(job, connection_ids={connection_id})
    ]
    logs = [
        log
        for log in _read_memory_dict(current_store, "plugin_invocation_logs").values()
        if log.get("connection_id") == connection_id
    ]
    return {"actions": actions, "scheduled_jobs": scheduled_jobs, "logs": logs}


def action_delete_usages(current_store: Any, action_id: str) -> dict[str, list[dict[str, Any]]]:
    scheduled_jobs = [
        job
        for job in _read_memory_dict(current_store, "scheduled_jobs").values()
        if _scheduled_job_references_any(job, action_ids={action_id})
    ]
    logs = [
        log
        for log in _read_memory_dict(current_store, "plugin_invocation_logs").values()
        if log.get("action_id") == action_id
    ]
    return {"scheduled_jobs": scheduled_jobs, "logs": logs}
