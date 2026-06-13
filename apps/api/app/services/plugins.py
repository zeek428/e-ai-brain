from __future__ import annotations

import json
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.deps import api_error, require_roles
from app.services.connection_diagnostics import ConnectionDiagnosticsService
from app.services.dynamic_parameters import (
    dynamic_parameter_preview,
    dynamic_parameter_resolution_trace,
    dynamic_time_parameters,
    resolve_dynamic_parameter_value,
)
from app.services.operational_records import record_audit_event, save_single_repository_record
from app.services.plugin_templates import (
    STANDARD_PLUGIN_CONNECTION_TEMPLATE_VERSION,
    STANDARD_PLUGIN_MARKETPLACE_METADATA,
    STANDARD_PLUGINS,
    standard_plugin_action_templates,
    standard_plugin_connection_defaults,
)
from app.services.result_write_targets import (
    result_write_target_default_mapping,
    result_write_target_label,
    result_write_targets,
)

PLUGIN_PROTOCOLS = {"http", "mcp_http", "mcp_stdio"}
PLUGIN_CATEGORIES = {
    "ai_service",
    "business_system",
    "collaboration",
    "data_warehouse",
    "devops",
    "general",
    "issue_tracking",
    "knowledge_base",
    "observability",
}
PLUGIN_STATUSES = {"active", "disabled", "draft"}
PLUGIN_AUTH_TYPES = {"none", "bearer", "api_key_header", "basic"}
PLUGIN_ACTION_TYPES = {"http_request", "mcp_tool"}
PLUGIN_CONNECTION_ENVIRONMENTS = {"default", "dev", "test", "staging", "prod", "sandbox"}
PLUGIN_INVOCATION_STATUSES = {"failed", "succeeded"}
MASKED_SECRET_PLACEHOLDER = "***"


def require_admin(user: dict[str, Any]) -> None:
    require_roles(user, {"admin"})


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is None or value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def replace_collection(
    current_store: Any,
    collection_name: str,
    items: list[dict[str, Any]],
) -> None:
    setattr(
        current_store,
        collection_name,
        {str(item["id"]): dict(item) for item in items if item.get("id") is not None},
    )


def plugin_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    required_methods = (
        "list_plugin_actions",
        "list_plugin_connections",
        "list_plugin_invocation_logs",
        "list_plugins",
    )
    if all(callable(getattr(repository, method_name, None)) for method_name in required_methods):
        return repository
    return None


def sync_plugin_store(
    current_store: Any,
    *,
    protocol: str | None = None,
    status: str | None = None,
) -> None:
    repository = plugin_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "integration_plugins",
        repository.list_plugins(protocol=protocol, status=status),
    )


def sync_plugin_connection_store(
    current_store: Any,
    *,
    environment: str | None = None,
    plugin_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = plugin_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "plugin_connections",
        repository.list_plugin_connections(
            environment=environment,
            plugin_id=plugin_id,
            status=status,
        ),
    )


def sync_plugin_action_store(
    current_store: Any,
    *,
    plugin_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = plugin_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "plugin_actions",
        repository.list_plugin_actions(plugin_id=plugin_id, status=status),
    )


def sync_plugin_invocation_log_store(
    current_store: Any,
    *,
    action_id: str | None = None,
    scheduled_job_id: str | None = None,
    scheduled_job_run_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = plugin_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "plugin_invocation_logs",
        repository.list_plugin_invocation_logs(
            action_id=action_id,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        ),
    )


def sync_plugin_dependency_store(current_store: Any) -> None:
    sync_plugin_store(current_store)
    sync_plugin_connection_store(current_store)
    sync_plugin_action_store(current_store)
    sync_plugin_invocation_log_store(current_store)
    repository = getattr(current_store, "repository", None)
    list_scheduled_jobs = getattr(repository, "list_scheduled_jobs", None)
    if callable(list_scheduled_jobs):
        replace_collection(current_store, "scheduled_jobs", list_scheduled_jobs())


def persist_record(
    current_store: Any,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    save_single_repository_record(
        current_store,
        method_name,
        record,
        audit_event=audit_event,
    )


def persist_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    append_audit_event = getattr(repository, "append_audit_event", None)
    if callable(append_audit_event):
        append_audit_event(audit_event)


def ensure_standard_plugins(current_store: Any) -> None:
    now = datetime.now(UTC).isoformat()
    existing_by_code = {
        str(plugin.get("code")): plugin
        for plugin in current_store.integration_plugins.values()
    }
    for template in STANDARD_PLUGINS:
        existing = existing_by_code.get(template["code"])
        if existing and all(existing.get(key) == value for key, value in template.items()):
            continue
        plugin = {
            **template,
            "created_at": existing.get("created_at") if existing else now,
            "created_by": existing.get("created_by") if existing else "system",
            "updated_at": now,
            **({"id": existing["id"]} if existing else {}),
        }
        current_store.integration_plugins[plugin["id"]] = plugin
        if existing and existing.get("id") != plugin["id"]:
            current_store.integration_plugins.pop(existing["id"], None)
        persist_record(current_store, "save_plugin_record", plugin)


def ensure_plugin_mutable(plugin: dict[str, Any]) -> None:
    if plugin.get("is_system"):
        message = (
            f"插件「{plugin['name']}」是官方标准插件，不能修改或删除。"
            "请在连接里维护 endpoint、认证和参数配置。"
        )
        raise api_error(
            409,
            "PLUGIN_STANDARD_PLUGIN_LOCKED",
            message,
        )


def merge_masked_config(existing: Any, incoming: Any) -> Any:
    if incoming == MASKED_SECRET_PLACEHOLDER:
        return existing
    if isinstance(existing, dict) and isinstance(incoming, dict):
        merged = dict(existing)
        for key, value in incoming.items():
            merged[key] = merge_masked_config(existing.get(key), value)
        return merged
    if isinstance(existing, list) and isinstance(incoming, list):
        return [
            merge_masked_config(existing[index], value) if index < len(existing) else value
            for index, value in enumerate(incoming)
        ]
    return incoming


def compact_preview_value(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= 200 else f"{value[:200]}..."
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)[:200]
    return value if len(encoded) <= 400 else f"{encoded[:400]}..."


def _is_masked_secret_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.strip() == MASKED_SECRET_PLACEHOLDER


def _header_key(headers: dict[str, Any], header_name: str) -> str | None:
    normalized = header_name.lower()
    for key in headers:
        if str(key).lower() == normalized:
            return str(key)
    return None


def _set_header(
    headers: dict[str, Any],
    sources: dict[str, str],
    header_name: str,
    value: Any,
    source: str,
) -> None:
    existing_key = _header_key(headers, header_name)
    if existing_key is not None and existing_key != header_name:
        headers.pop(existing_key, None)
        sources.pop(existing_key, None)
    headers[header_name] = str(value)
    sources[header_name] = source


def public_plugin(plugin: dict[str, Any]) -> dict[str, Any]:
    return dict(plugin)


def public_connection(connection: dict[str, Any]) -> dict[str, Any]:
    return dict(connection)


def public_action(action: dict[str, Any]) -> dict[str, Any]:
    return dict(action)


def public_invocation_log(log: dict[str, Any]) -> dict[str, Any]:
    return dict(log)


def usage_names(items: list[dict[str, Any]], *, limit: int = 3) -> str:
    names = [str(item.get("name") or item.get("code") or item.get("id")) for item in items[:limit]]
    suffix = f" 等 {len(items)} 个" if len(items) > limit else f" {len(items)} 个"
    return f"{'、'.join(names)}{suffix}" if names else f"{len(items)} 个"


def usage_summary(usages: dict[str, list[dict[str, Any]]]) -> str:
    labels = {
        "actions": "动作",
        "connections": "连接",
        "logs": "调用日志",
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


def plugin_delete_usages(current_store: Any, plugin_id: str) -> dict[str, list[dict[str, Any]]]:
    connections = [
        connection
        for connection in current_store.plugin_connections.values()
        if connection.get("plugin_id") == plugin_id
    ]
    actions = [
        action
        for action in current_store.plugin_actions.values()
        if action.get("plugin_id") == plugin_id
    ]
    connection_ids = {connection["id"] for connection in connections}
    action_ids = {action["id"] for action in actions}
    scheduled_jobs = [
        job
        for job in getattr(current_store, "scheduled_jobs", {}).values()
        if job.get("plugin_action_id") in action_ids
        or job.get("plugin_connection_id") in connection_ids
    ]
    logs = [
        log
        for log in current_store.plugin_invocation_logs.values()
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
        for action in current_store.plugin_actions.values()
        if action.get("connection_id") == connection_id
    ]
    scheduled_jobs = [
        job
        for job in getattr(current_store, "scheduled_jobs", {}).values()
        if job.get("plugin_connection_id") == connection_id
    ]
    logs = [
        log
        for log in current_store.plugin_invocation_logs.values()
        if log.get("connection_id") == connection_id
    ]
    return {"actions": actions, "scheduled_jobs": scheduled_jobs, "logs": logs}


def action_delete_usages(current_store: Any, action_id: str) -> dict[str, list[dict[str, Any]]]:
    scheduled_jobs = [
        job
        for job in getattr(current_store, "scheduled_jobs", {}).values()
        if job.get("plugin_action_id") == action_id
    ]
    logs = [
        log
        for log in current_store.plugin_invocation_logs.values()
        if log.get("action_id") == action_id
    ]
    return {"scheduled_jobs": scheduled_jobs, "logs": logs}


def list_plugins_response(
    *,
    current_store: Any,
    protocol: str | None,
    status: str | None,
) -> dict[str, Any]:
    if protocol is not None:
        ensure_enum(protocol, PLUGIN_PROTOCOLS, "protocol")
    if status is not None:
        ensure_enum(status, PLUGIN_STATUSES, "status")
    sync_plugin_store(current_store, protocol=protocol, status=status)
    ensure_standard_plugins(current_store)
    items = []
    for plugin in current_store.integration_plugins.values():
        if protocol is not None and plugin.get("protocol") != protocol:
            continue
        if status is not None and plugin.get("status") != status:
            continue
        items.append(public_plugin(plugin))
    items.sort(key=lambda item: (item.get("code") or "", item["id"]))
    return {"items": items, "total": len(items)}


def list_plugin_marketplace_response(
    *,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_dependency_store(current_store)
    ensure_standard_plugins(current_store)
    connections = list(current_store.plugin_connections.values())
    actions = list(current_store.plugin_actions.values())
    plugins_by_code = {
        str(plugin.get("code")): plugin
        for plugin in current_store.integration_plugins.values()
    }
    items: list[dict[str, Any]] = []
    for template in STANDARD_PLUGINS:
        plugin = plugins_by_code.get(str(template["code"]))
        plugin_id = plugin.get("id") if plugin else template["id"]
        metadata = STANDARD_PLUGIN_MARKETPLACE_METADATA.get(str(template["code"]), {})
        plugin_connections = [
            connection for connection in connections if connection.get("plugin_id") == plugin_id
        ]
        plugin_actions = [action for action in actions if action.get("plugin_id") == plugin_id]
        items.append(
            {
                "action_count": len(plugin_actions),
                "action_templates": metadata.get("action_templates", []),
                "category": template["category"],
                "code": template["code"],
                "connection_defaults": standard_plugin_connection_defaults(str(template["code"])),
                "connection_count": len(plugin_connections),
                "connection_template_version": STANDARD_PLUGIN_CONNECTION_TEMPLATE_VERSION,
                "description": template["description"],
                "id": f"marketplace_{template['code']}",
                "installed": plugin is not None,
                "is_system": True,
                "name": template["name"],
                "plugin_id": plugin_id if plugin is not None else None,
                "protocol": template["protocol"],
                "publisher": metadata.get("publisher", "AI Brain 官方"),
                "recommended_scenarios": metadata.get("recommended_scenarios", []),
                "risk_level": template["risk_level"],
                "status": plugin.get("status") if plugin else "not_installed",
                "summary": metadata.get("summary") or template["description"],
            },
        )
    items.sort(key=lambda item: (item["category"], item["code"]))
    return {"items": items, "total": len(items)}


def list_plugin_action_templates_response(
    *,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_store(current_store)
    ensure_standard_plugins(current_store)
    plugins_by_code = {
        str(plugin.get("code")): plugin
        for plugin in current_store.integration_plugins.values()
    }
    items = []
    for template in standard_plugin_action_templates():
        plugin = plugins_by_code.get(str(template["plugin_code"]))
        items.append(
            {
                **template,
                "plugin_id": plugin.get("id") if plugin else None,
            },
        )
    items.sort(key=lambda item: (str(item.get("plugin_code")), str(item.get("code"))))
    return {"items": items, "total": len(items)}


def list_result_write_targets_response(
    *,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    items = result_write_targets()
    return {"items": items, "total": len(items)}


def create_plugin_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_store(current_store)
    ensure_standard_plugins(current_store)
    ensure_enum(payload.category or "general", PLUGIN_CATEGORIES, "category")
    ensure_enum(payload.protocol, PLUGIN_PROTOCOLS, "protocol")
    ensure_enum(payload.status, PLUGIN_STATUSES, "status")
    now = datetime.now(UTC).isoformat()
    plugin_id = current_store.new_id("plugin")
    plugin = {
        "category": ensure_non_blank(payload.category or "general", "category"),
        "code": ensure_non_blank(payload.code, "code"),
        "created_at": now,
        "created_by": user["id"],
        "description": payload.description,
        "id": plugin_id,
        "is_system": False,
        "name": ensure_non_blank(payload.name, "name"),
        "protocol": payload.protocol,
        "risk_level": payload.risk_level,
        "status": payload.status,
        "updated_at": now,
    }
    current_store.integration_plugins[plugin_id] = plugin
    audit_event = record_audit_event(
        current_store,
        event_type="plugin.created",
        actor_id=user["id"],
        subject_type="plugin",
        subject_id=plugin_id,
        payload={
            "code": plugin["code"],
            "protocol": plugin["protocol"],
            "status": plugin["status"],
        },
    )
    persist_record(current_store, "save_plugin_record", plugin, audit_event=audit_event)
    return public_plugin(plugin)


def patch_plugin_response(
    *,
    current_store: Any,
    payload: Any,
    plugin_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_store(current_store)
    plugin = current_store.integration_plugins.get(plugin_id)
    if plugin is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    ensure_plugin_mutable(plugin)
    updates = payload.model_dump(exclude_unset=True)
    if "protocol" in updates:
        ensure_enum(updates["protocol"], PLUGIN_PROTOCOLS, "protocol")
    if "category" in updates:
        ensure_enum(updates["category"], PLUGIN_CATEGORIES, "category")
    if "status" in updates:
        ensure_enum(updates["status"], PLUGIN_STATUSES, "status")
    for key in ("category", "code", "name"):
        if key in updates:
            updates[key] = ensure_non_blank(updates[key], key)
    plugin = {**plugin, **updates, "updated_at": datetime.now(UTC).isoformat()}
    current_store.integration_plugins[plugin_id] = plugin
    audit_event = record_audit_event(
        current_store,
        event_type="plugin.updated",
        actor_id=user["id"],
        subject_type="plugin",
        subject_id=plugin_id,
        payload={"code": plugin["code"], "status": plugin["status"]},
    )
    persist_record(current_store, "save_plugin_record", plugin, audit_event=audit_event)
    return public_plugin(plugin)


def delete_plugin_response(
    *,
    current_store: Any,
    plugin_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_dependency_store(current_store)
    plugin = current_store.integration_plugins.get(plugin_id)
    if plugin is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    ensure_plugin_mutable(plugin)
    ensure_not_used_for_delete(
        plugin_delete_usages(current_store, plugin_id),
        object_label=f"插件「{plugin['name']}」",
    )
    current_store.integration_plugins.pop(plugin_id, None)
    audit_event = record_audit_event(
        current_store,
        event_type="plugin.deleted",
        actor_id=user["id"],
        subject_type="plugin",
        subject_id=plugin_id,
        payload={"code": plugin["code"], "name": plugin["name"]},
    )
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_plugin_record", None)
    if callable(delete_record):
        delete_record(plugin_id, audit_event=audit_event)
    return {"deleted": True, "id": plugin_id}


def ensure_active_plugin(current_store: Any, plugin_id: str) -> dict[str, Any]:
    sync_plugin_store(current_store)
    ensure_standard_plugins(current_store)
    plugin = current_store.integration_plugins.get(plugin_id)
    if plugin is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    if plugin.get("status") != "active":
        raise api_error(400, "PLUGIN_INACTIVE", "Plugin is inactive")
    return plugin


def list_plugin_connections_response(
    *,
    current_store: Any,
    environment: str | None,
    plugin_id: str | None,
    status: str | None,
) -> dict[str, Any]:
    if environment is not None:
        ensure_enum(environment, PLUGIN_CONNECTION_ENVIRONMENTS, "environment")
    if status is not None:
        ensure_enum(status, PLUGIN_STATUSES, "status")
    sync_plugin_connection_store(
        current_store,
        environment=environment,
        plugin_id=plugin_id,
        status=status,
    )
    items = []
    for connection in current_store.plugin_connections.values():
        if environment is not None and connection.get("environment") != environment:
            continue
        if plugin_id is not None and connection.get("plugin_id") != plugin_id:
            continue
        if status is not None and connection.get("status") != status:
            continue
        items.append(public_connection(connection))
    items.sort(
        key=lambda item: (item.get("plugin_id") or "", item.get("environment") or "", item["id"]),
    )
    return {"items": items, "total": len(items)}


def create_plugin_connection_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    ensure_active_plugin(current_store, payload.plugin_id)
    ensure_enum(payload.auth_type, PLUGIN_AUTH_TYPES, "auth_type")
    ensure_enum(payload.environment or "default", PLUGIN_CONNECTION_ENVIRONMENTS, "environment")
    ensure_enum(payload.status, PLUGIN_STATUSES, "status")
    now = datetime.now(UTC).isoformat()
    connection_id = current_store.new_id("plugin_connection")
    connection = {
        "auth_config": payload.auth_config,
        "auth_type": payload.auth_type,
        "created_at": now,
        "created_by": user["id"],
        "endpoint_url": ensure_non_blank(payload.endpoint_url, "endpoint_url"),
        "environment": ensure_non_blank(payload.environment or "default", "environment"),
        "id": connection_id,
        "max_retries": payload.max_retries,
        "name": ensure_non_blank(payload.name, "name"),
        "plugin_id": payload.plugin_id,
        "request_config": payload.request_config,
        "status": payload.status,
        "timeout_seconds": payload.timeout_seconds,
        "updated_at": now,
    }
    current_store.plugin_connections[connection_id] = connection
    audit_event = record_audit_event(
        current_store,
        event_type="plugin_connection.created",
        actor_id=user["id"],
        subject_type="plugin_connection",
        subject_id=connection_id,
        payload={"plugin_id": payload.plugin_id, "status": connection["status"]},
    )
    persist_record(
        current_store,
        "save_plugin_connection_record",
        connection,
        audit_event=audit_event,
    )
    return public_connection(connection)


def patch_plugin_connection_response(
    *,
    connection_id: str,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_connection_store(current_store)
    connection = current_store.plugin_connections.get(connection_id)
    if connection is None:
        raise api_error(404, "NOT_FOUND", "Plugin connection not found")
    updates = payload.model_dump(exclude_unset=True)
    if "plugin_id" in updates:
        ensure_active_plugin(current_store, updates["plugin_id"])
    if "auth_type" in updates:
        ensure_enum(updates["auth_type"], PLUGIN_AUTH_TYPES, "auth_type")
    if "environment" in updates:
        ensure_enum(updates["environment"], PLUGIN_CONNECTION_ENVIRONMENTS, "environment")
    if "status" in updates:
        ensure_enum(updates["status"], PLUGIN_STATUSES, "status")
    for key in ("endpoint_url", "environment", "name"):
        if key in updates:
            updates[key] = ensure_non_blank(updates[key], key)
    if "auth_config" in updates:
        updates["auth_config"] = merge_masked_config(
            connection.get("auth_config") or {},
            updates["auth_config"] or {},
        )
    if "request_config" in updates:
        updates["request_config"] = merge_masked_config(
            connection.get("request_config") or {},
            updates["request_config"] or {},
        )
    connection = {**connection, **updates, "updated_at": datetime.now(UTC).isoformat()}
    current_store.plugin_connections[connection_id] = connection
    audit_event = record_audit_event(
        current_store,
        event_type="plugin_connection.updated",
        actor_id=user["id"],
        subject_type="plugin_connection",
        subject_id=connection_id,
        payload={"plugin_id": connection["plugin_id"], "status": connection["status"]},
    )
    persist_record(
        current_store,
        "save_plugin_connection_record",
        connection,
        audit_event=audit_event,
    )
    return public_connection(connection)


def delete_plugin_connection_response(
    *,
    connection_id: str,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_dependency_store(current_store)
    connection = current_store.plugin_connections.get(connection_id)
    if connection is None:
        raise api_error(404, "NOT_FOUND", "Plugin connection not found")
    ensure_not_used_for_delete(
        connection_delete_usages(current_store, connection_id),
        object_label=f"连接「{connection['name']}」",
    )
    current_store.plugin_connections.pop(connection_id, None)
    audit_event = record_audit_event(
        current_store,
        event_type="plugin_connection.deleted",
        actor_id=user["id"],
        subject_type="plugin_connection",
        subject_id=connection_id,
        payload={"name": connection["name"], "plugin_id": connection["plugin_id"]},
    )
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_plugin_connection_record", None)
    if callable(delete_record):
        delete_record(connection_id, audit_event=audit_event)
    return {"deleted": True, "id": connection_id}


def test_plugin_connection_response(
    *,
    connection_id: str,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_connection_store(current_store)
    sync_plugin_store(current_store)
    connection = current_store.plugin_connections.get(connection_id)
    if connection is None:
        raise api_error(404, "NOT_FOUND", "Plugin connection not found")
    plugin = current_store.integration_plugins.get(connection.get("plugin_id"))
    if plugin is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    start = perf_counter()
    diagnostics: list[dict[str, Any]] = []
    status = "succeeded"
    error_code = None
    error_message = None
    mocked = False
    parsed_endpoint = urlparse(str(connection.get("endpoint_url") or ""))
    diagnostics.append(
        ConnectionDiagnosticsService.diagnostic_step(
            "endpoint_configured",
            detail=parsed_endpoint.netloc or parsed_endpoint.path or "未配置 Endpoint",
            status="succeeded" if connection.get("endpoint_url") else "failed",
        ),
    )
    diagnostics.append(
        ConnectionDiagnosticsService.diagnostic_step(
            "protocol_supported",
            detail=str(plugin.get("protocol")),
            status="failed" if plugin.get("protocol") == "mcp_stdio" else "succeeded",
        ),
    )
    auth_type = str(connection.get("auth_type") or "none")
    auth_config = connection.get("auth_config") or {}
    resolution_now = datetime.now(UTC)
    request_config = resolve_connection_request_config(connection, now=resolution_now)
    variable_resolutions, variable_timezone = connection_request_variable_resolutions(
        connection,
        now=resolution_now,
    )
    request_query = _dict_config_section(request_config.get("query"))
    request_method = "POST" if plugin.get("protocol") == "mcp_http" else "GET"
    request_url = _url_with_query(str(connection.get("endpoint_url") or ""), request_query)
    request_body: dict[str, Any] | None = None
    request_headers, header_sources = _build_headers_with_sources(
        connection,
        {"request_config": {}},
    )
    if plugin.get("protocol") == "mcp_http":
        request_body = {
            "id": f"connection_test_{connection_id}",
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
        }
        request_headers = {**request_headers, "Content-Type": "application/json"}
        header_sources = {**header_sources, "Content-Type": "system.default"}
    masked_placeholder_headers = [
        header_name
        for header_name, header_value in request_headers.items()
        if _is_masked_secret_placeholder(header_value)
    ]
    response_summary: dict[str, Any] = {}
    diagnostics.append(
        ConnectionDiagnosticsService.diagnostic_step(
            "auth_configured",
            detail=auth_type,
            status="warning" if auth_type != "none" and not auth_config else "succeeded",
        ),
    )
    try:
        if "mock_test_response" in auth_config:
            mocked = True
            diagnostics.append(
                ConnectionDiagnosticsService.diagnostic_step(
                    "network_request",
                    detail="使用 mock_test_response，未发起真实网络请求",
                    status="mocked",
                ),
            )
        elif plugin.get("protocol") == "mcp_stdio":
            raise api_error(
                400,
                "PLUGIN_PROTOCOL_UNSUPPORTED",
                "mcp_stdio connection test requires isolated command execution and is not enabled",
            )
        elif plugin.get("protocol") == "mcp_http":
            step_start = perf_counter()
            request = Request(
                request_url,
                data=json.dumps(request_body or {}, ensure_ascii=False).encode("utf-8"),
                headers=request_headers,
                method=request_method,
            )
            timeout = min(int(connection.get("timeout_seconds") or 10), 10)
            with urlopen(request, timeout=timeout) as response:
                body_preview = response.read(2048).decode("utf-8", errors="replace")
                response_summary = {
                    "body_preview": body_preview,
                    "status_code": getattr(response, "status", None),
                }
                diagnostics.append(
                    ConnectionDiagnosticsService.diagnostic_step(
                        "mcp_tools_list",
                        detail="tools/list 调用完成",
                        latency_ms=int((perf_counter() - step_start) * 1000),
                        status_code=getattr(response, "status", None),
                    ),
                )
        else:
            step_start = perf_counter()
            request = Request(
                request_url,
                headers=request_headers,
                method=request_method,
            )
            timeout = min(int(connection.get("timeout_seconds") or 10), 10)
            with urlopen(request, timeout=timeout) as response:
                body_preview = response.read(2048).decode("utf-8", errors="replace")
                response_summary = {
                    "body_preview": body_preview,
                    "status_code": getattr(response, "status", None),
                }
                diagnostics.append(
                    ConnectionDiagnosticsService.diagnostic_step(
                        "network_request",
                        detail="HTTP GET 调用完成",
                        latency_ms=int((perf_counter() - step_start) * 1000),
                        status_code=getattr(response, "status", None),
                    ),
                )
    except HTTPError as exc:
        status = "failed"
        error_code = exc.__class__.__name__
        error_message = str(exc)
        response_summary = ConnectionDiagnosticsService.response_summary_from_http_error(exc)
        diagnostics.append(
            ConnectionDiagnosticsService.diagnostic_step(
                "network_request" if plugin.get("protocol") != "mcp_http" else "mcp_tools_list",
                detail=error_message,
                status="failed",
                error_code=error_code,
                status_code=exc.code,
            ),
        )
    except Exception as exc:
        status = "failed"
        error_code = exc.__class__.__name__
        error_message = str(exc)
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            error_code = exc.detail.get("code", error_code)
            error_message = exc.detail.get("message", error_message)
        diagnostics.append(
            ConnectionDiagnosticsService.diagnostic_step(
                "network_request" if plugin.get("protocol") != "mcp_http" else "mcp_tools_list",
                detail=error_message,
                status="failed",
                error_code=error_code,
            ),
        )
    latency_ms = int((perf_counter() - start) * 1000)
    request_summary = {
        "auth_config": auth_config,
        "auth_type": auth_type,
        "body": request_body,
        "header_sources": header_sources,
        "headers": request_headers,
        "host": parsed_endpoint.netloc,
        "masked_placeholder_headers": masked_placeholder_headers,
        "method": request_method,
        "original_request_config": connection.get("request_config") or {},
        "protocol": plugin.get("protocol"),
        "query": request_query,
        "request_config": request_config,
        "scheme": parsed_endpoint.scheme,
        "url": request_url,
        "variable_resolution_timezone": variable_timezone,
        "variable_resolutions": variable_resolutions,
    }
    request_summary["curl_command"] = (
        ConnectionDiagnosticsService.curl_command_from_request_summary(request_summary)
    )
    action_template_draft = ConnectionDiagnosticsService.action_template_draft(
        connection,
        plugin,
        request_summary,
    )
    result = {
        "action_template_draft": action_template_draft,
        "checked_at": datetime.now(UTC).isoformat(),
        "connection_id": connection_id,
        "diagnostics": diagnostics,
        "endpoint_url": connection.get("endpoint_url"),
        "environment": connection.get("environment"),
        "error_code": error_code,
        "error_message": error_message,
        "latency_ms": latency_ms,
        "mocked": mocked,
        "plugin_id": plugin["id"],
        "protocol": plugin.get("protocol"),
        "request_summary": request_summary,
        "response_summary": response_summary,
        "status": status,
    }
    result["repair_suggestions"] = ConnectionDiagnosticsService.repair_suggestions(result)
    test_history = ConnectionDiagnosticsService.append_test_history(connection, result)
    result["test_history"] = test_history
    last_test_summary = ConnectionDiagnosticsService.test_summary(result)
    connection = {
        **connection,
        "last_test_summary": last_test_summary,
        "test_history": test_history,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    current_store.plugin_connections[connection_id] = connection
    audit_event = record_audit_event(
        current_store,
        event_type=f"plugin_connection.test_{status}",
        actor_id=user["id"],
        subject_type="plugin_connection",
        subject_id=connection_id,
        payload={
            "environment": connection.get("environment"),
            "plugin_id": plugin["id"],
            "protocol": plugin.get("protocol"),
            "status": status,
        },
    )
    persist_record(
        current_store,
        "save_plugin_connection_record",
        connection,
        audit_event=audit_event,
    )
    return result


def ensure_active_connection(
    current_store: Any,
    connection_id: str | None,
    *,
    plugin_id: str | None = None,
) -> dict[str, Any] | None:
    if connection_id is None:
        return None
    sync_plugin_connection_store(current_store)
    connection = current_store.plugin_connections.get(connection_id)
    if connection is None:
        raise api_error(404, "NOT_FOUND", "Plugin connection not found")
    if plugin_id is not None and connection.get("plugin_id") != plugin_id:
        raise api_error(
            400,
            "PLUGIN_CONNECTION_MISMATCH",
            "Plugin connection does not belong to plugin",
        )
    if connection.get("status") != "active":
        raise api_error(400, "PLUGIN_CONNECTION_INACTIVE", "Plugin connection is inactive")
    return connection


def list_plugin_actions_response(
    *,
    current_store: Any,
    plugin_id: str | None,
    status: str | None,
) -> dict[str, Any]:
    if status is not None:
        ensure_enum(status, PLUGIN_STATUSES, "status")
    sync_plugin_action_store(current_store, plugin_id=plugin_id, status=status)
    items = []
    for action in current_store.plugin_actions.values():
        if plugin_id is not None and action.get("plugin_id") != plugin_id:
            continue
        if status is not None and action.get("status") != status:
            continue
        items.append(public_action(action))
    items.sort(key=lambda item: (item.get("plugin_id") or "", item.get("code") or "", item["id"]))
    return {"items": items, "total": len(items)}


def create_plugin_action_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    ensure_active_plugin(current_store, payload.plugin_id)
    ensure_active_connection(current_store, payload.connection_id, plugin_id=payload.plugin_id)
    ensure_enum(payload.action_type, PLUGIN_ACTION_TYPES, "action_type")
    ensure_enum(payload.status, PLUGIN_STATUSES, "status")
    now = datetime.now(UTC).isoformat()
    action_id = current_store.new_id("plugin_action")
    action = {
        "action_type": payload.action_type,
        "code": ensure_non_blank(payload.code, "code"),
        "connection_id": payload.connection_id,
        "created_at": now,
        "created_by": user["id"],
        "description": payload.description,
        "id": action_id,
        "input_schema": payload.input_schema,
        "name": ensure_non_blank(payload.name, "name"),
        "output_schema": payload.output_schema,
        "plugin_id": payload.plugin_id,
        "request_config": payload.request_config,
        "requires_human_review": payload.requires_human_review,
        "result_mapping": payload.result_mapping,
        "status": payload.status,
        "updated_at": now,
    }
    current_store.plugin_actions[action_id] = action
    audit_event = record_audit_event(
        current_store,
        event_type="plugin_action.created",
        actor_id=user["id"],
        subject_type="plugin_action",
        subject_id=action_id,
        payload={
            "code": action["code"],
            "plugin_id": action["plugin_id"],
            "status": action["status"],
        },
    )
    persist_record(
        current_store,
        "save_plugin_action_record",
        action,
        audit_event=audit_event,
    )
    return public_action(action)


def patch_plugin_action_response(
    *,
    action_id: str,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_action_store(current_store)
    action = current_store.plugin_actions.get(action_id)
    if action is None:
        raise api_error(404, "NOT_FOUND", "Plugin action not found")
    updates = payload.model_dump(exclude_unset=True)
    plugin_id = updates.get("plugin_id", action["plugin_id"])
    if "plugin_id" in updates:
        ensure_active_plugin(current_store, plugin_id)
    if "connection_id" in updates:
        ensure_active_connection(current_store, updates["connection_id"], plugin_id=plugin_id)
    if "action_type" in updates:
        ensure_enum(updates["action_type"], PLUGIN_ACTION_TYPES, "action_type")
    if "status" in updates:
        ensure_enum(updates["status"], PLUGIN_STATUSES, "status")
    for key in ("code", "name"):
        if key in updates:
            updates[key] = ensure_non_blank(updates[key], key)
    if "request_config" in updates:
        updates["request_config"] = merge_masked_config(
            action.get("request_config") or {},
            updates["request_config"] or {},
        )
    action = {**action, **updates, "updated_at": datetime.now(UTC).isoformat()}
    current_store.plugin_actions[action_id] = action
    audit_event = record_audit_event(
        current_store,
        event_type="plugin_action.updated",
        actor_id=user["id"],
        subject_type="plugin_action",
        subject_id=action_id,
        payload={
            "code": action["code"],
            "plugin_id": action["plugin_id"],
            "status": action["status"],
        },
    )
    persist_record(
        current_store,
        "save_plugin_action_record",
        action,
        audit_event=audit_event,
    )
    return public_action(action)


def delete_plugin_action_response(
    *,
    action_id: str,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_dependency_store(current_store)
    action = current_store.plugin_actions.get(action_id)
    if action is None:
        raise api_error(404, "NOT_FOUND", "Plugin action not found")
    ensure_not_used_for_delete(
        action_delete_usages(current_store, action_id),
        object_label=f"动作「{action['name']}」",
    )
    current_store.plugin_actions.pop(action_id, None)
    audit_event = record_audit_event(
        current_store,
        event_type="plugin_action.deleted",
        actor_id=user["id"],
        subject_type="plugin_action",
        subject_id=action_id,
        payload={"code": action["code"], "name": action["name"], "plugin_id": action["plugin_id"]},
    )
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_plugin_action_record", None)
    if callable(delete_record):
        delete_record(action_id, audit_event=audit_event)
    return {"deleted": True, "id": action_id}


def ensure_active_plugin_action(
    current_store: Any,
    action_id: str | None,
    *,
    connection_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if action_id is None:
        raise api_error(400, "PLUGIN_ACTION_REQUIRED", "plugin_action_id is required")
    sync_plugin_action_store(current_store)
    action = current_store.plugin_actions.get(action_id)
    if action is None:
        raise api_error(404, "NOT_FOUND", "Plugin action not found")
    if action.get("status") != "active":
        raise api_error(400, "PLUGIN_ACTION_INACTIVE", "Plugin action is inactive")
    plugin = ensure_active_plugin(current_store, action["plugin_id"])
    connection = ensure_active_connection(
        current_store,
        connection_id or action.get("connection_id"),
        plugin_id=plugin["id"],
    )
    if connection is None:
        raise api_error(400, "PLUGIN_CONNECTION_REQUIRED", "Plugin action requires connection")
    return plugin, connection, action


def resolve_plugin_snapshot(
    current_store: Any,
    *,
    action_id: str | None,
    connection_id: str | None = None,
) -> dict[str, Any]:
    if action_id is None:
        return {}
    plugin, connection, action = ensure_active_plugin_action(
        current_store,
        action_id,
        connection_id=connection_id,
    )
    return {
        "action": public_action(action),
        "connection": public_connection(connection),
        "plugin": public_plugin(plugin),
    }


def json_path_value(payload: Any, path: str | None) -> Any:
    if path == "$":
        return payload
    if not path or not path.startswith("$."):
        return None
    current = payload
    for part in path[2:].split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def records_imported_from_mapping(response_summary: dict[str, Any], mapping: dict[str, Any]) -> int:
    value = json_path_value(response_summary.get("json"), mapping.get("records_imported_path"))
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, list):
        return len(value)
    return 0


def plugin_invocation_timezone(input_payload: dict[str, Any] | None) -> ZoneInfo:
    payload = input_payload or {}
    timezone_name = str(
        payload.get("timezone")
        or (payload.get("config") or {}).get("timezone")
        or "UTC",
    )
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def resolve_action_request_config(
    action: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    timezone = plugin_invocation_timezone(input_payload)
    return resolve_dynamic_parameter_value(
        action.get("request_config") or {},
        dynamic_time_parameters(now=now, timezone=timezone),
        now=now,
        timezone=timezone,
    )


def resolve_connection_request_config(
    connection: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    timezone = plugin_invocation_timezone(input_payload)
    return resolve_dynamic_parameter_value(
        connection.get("request_config") or {},
        dynamic_time_parameters(now=now, timezone=timezone),
        now=now,
        timezone=timezone,
    )


def connection_request_variable_resolutions(
    connection: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], str]:
    timezone = plugin_invocation_timezone(input_payload)
    return (
        dynamic_parameter_resolution_trace(
            connection.get("request_config") or {},
            dynamic_time_parameters(now=now, timezone=timezone),
            now=now,
            timezone=timezone,
        ),
        str(timezone),
    )


def _dict_config_section(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _url_with_query(url: str, query: dict[str, Any]) -> str:
    if not query:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(query)}"


def resolve_plugin_request_config(
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    connection_config = resolve_connection_request_config(connection, input_payload, now=now)
    action_config = resolve_action_request_config(action, input_payload, now=now)
    merged = {**connection_config, **action_config}

    connection_query = _dict_config_section(connection_config.get("query"))
    action_query = _dict_config_section(action_config.get("query"))
    if connection_query or action_query:
        merged["query"] = {**connection_query, **action_query}

    connection_headers = _dict_config_section(connection_config.get("headers"))
    action_headers = _dict_config_section(action_config.get("headers"))
    if connection_headers or action_headers:
        merged["headers"] = {**connection_headers, **action_headers}

    return merged


def _build_headers(
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    headers, _ = _build_headers_with_sources(connection, action, input_payload)
    return headers


def _build_headers_with_sources(
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    request_config = resolve_plugin_request_config(connection, action, input_payload)
    headers = dict(request_config.get("headers") or {})
    sources = {str(key): "request_config.headers" for key in headers}
    auth_config = connection.get("auth_config") or {}
    if connection.get("auth_type") == "bearer" and auth_config.get("token_ref"):
        _set_header(
            headers,
            sources,
            "Authorization",
            f"Bearer {auth_config['token_ref']}",
            "auth_config.bearer",
        )
    if connection.get("auth_type") == "api_key_header":
        header_name = auth_config.get("header_name") or "X-API-Key"
        secret_ref = auth_config.get("secret_ref")
        if secret_ref:
            _set_header(
                headers,
                sources,
                str(header_name),
                str(secret_ref),
                "auth_config.api_key_header",
            )
    string_headers = {str(key): str(value) for key, value in headers.items()}
    return string_headers, {
        str(key): sources.get(str(key), "request_config.headers") for key in string_headers
    }


def _invoke_http(
    plugin: dict[str, Any],
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    request_config = resolve_plugin_request_config(connection, action, input_payload)
    if "mock_response_json" in request_config:
        return {"json": request_config["mock_response_json"], "mocked": True}
    method = str(request_config.get("method") or "GET").upper()
    path = str(request_config.get("path") or "")
    url = urljoin(connection["endpoint_url"].rstrip("/") + "/", path.lstrip("/"))
    query = _dict_config_section(request_config.get("query"))
    url = _url_with_query(url, query)
    body = input_payload if method not in {"GET", "HEAD"} else None
    request_body = (
        json.dumps(body or {}, ensure_ascii=False).encode("utf-8")
        if body is not None
        else None
    )
    request = Request(
        url,
        data=request_body,
        headers={
            **_build_headers(connection, action, input_payload),
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urlopen(request, timeout=connection.get("timeout_seconds", 30)) as response:
        raw = response.read().decode("utf-8")
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {"text": raw[:1000]}
    return {"json": parsed, "mocked": False}


def _invoke_mcp_http(
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    request_config = resolve_plugin_request_config(connection, action, input_payload)
    if "mock_response_json" in request_config:
        return {"json": request_config["mock_response_json"], "mocked": True}
    tool_name = ensure_non_blank(request_config.get("tool_name"), "tool_name")
    url = _url_with_query(
        str(connection["endpoint_url"]),
        _dict_config_section(request_config.get("query")),
    )
    request = Request(
        url,
        data=json.dumps(
            {
                "id": action["id"],
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"arguments": input_payload, "name": tool_name},
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            **_build_headers(connection, action, input_payload),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=connection.get("timeout_seconds", 30)) as response:
        raw = response.read().decode("utf-8")
    return {"json": json.loads(raw) if raw else {}, "mocked": False}


def _invoke_action(
    plugin: dict[str, Any],
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    if plugin["protocol"] == "mcp_stdio":
        raise api_error(
            400,
            "PLUGIN_PROTOCOL_UNSUPPORTED",
            "mcp_stdio invocation requires isolated command execution and is not enabled",
        )
    if plugin["protocol"] == "mcp_http":
        return _invoke_mcp_http(connection, action, input_payload)
    return _invoke_http(plugin, connection, action, input_payload)


def plugin_action_request_preview(
    plugin: dict[str, Any],
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    request_config = resolve_plugin_request_config(connection, action, input_payload)
    headers = _build_headers(connection, action, input_payload)
    if plugin["protocol"] == "mcp_http":
        query = _dict_config_section(request_config.get("query"))
        endpoint_url = str(connection.get("endpoint_url") or "")
        return {
            "arguments": input_payload,
            "endpoint_url": endpoint_url,
            "headers": headers,
            "jsonrpc_method": "tools/call",
            "method": "POST",
            "protocol": plugin["protocol"],
            "query": query,
            "tool_name": request_config.get("tool_name"),
            "url": _url_with_query(endpoint_url, query),
        }
    method = str(request_config.get("method") or "GET").upper()
    path = str(request_config.get("path") or "")
    url = urljoin(str(connection.get("endpoint_url", "")).rstrip("/") + "/", path.lstrip("/"))
    query = _dict_config_section(request_config.get("query"))
    url = _url_with_query(url, query)
    return {
        "body": input_payload if method not in {"GET", "HEAD"} else None,
        "headers": headers,
        "method": method,
        "path": path,
        "protocol": plugin["protocol"],
        "query": query,
        "url": url,
    }


def result_mapping_hits(
    response_summary: dict[str, Any],
    mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for key, path in mapping.items():
        if not isinstance(path, str) or not (path == "$" or path.startswith("$.")):
            continue
        value = json_path_value(response_summary.get("json"), path)
        hits.append(
            {
                "key": key,
                "matched": value is not None,
                "path": path,
                "value_preview": compact_preview_value(value),
            },
        )
    return hits


def result_write_preview(
    response_summary: dict[str, Any],
    mapping: dict[str, Any],
) -> dict[str, Any]:
    write_target = str(mapping.get("write_target") or "scheduled_job_result")
    default_mapping = result_write_target_default_mapping(write_target)
    raw_json = response_summary.get("json")
    write_target_label = result_write_target_label(write_target)

    if write_target == "code_inspection_reports":
        findings = json_path_value(
            raw_json,
            str(mapping.get("findings_path") or default_mapping.get("findings_path")),
        )
        sample_records = findings[:3] if isinstance(findings, list) else []
        report_preview = {
            "branch": json_path_value(
                raw_json,
                str(mapping.get("branch_path") or default_mapping.get("branch_path")),
            ),
            "commit_sha": json_path_value(
                raw_json,
                str(mapping.get("commit_sha_path") or default_mapping.get("commit_sha_path")),
            ),
            "repository_id": json_path_value(
                raw_json,
                str(
                    mapping.get("repository_id_path")
                    or default_mapping.get("repository_id_path"),
                ),
            ),
            "risk_level": json_path_value(
                raw_json,
                str(mapping.get("risk_level_path") or default_mapping.get("risk_level_path")),
            ),
            "summary": json_path_value(
                raw_json,
                str(mapping.get("summary_path") or default_mapping.get("summary_path")),
            ),
        }
        return {
            "candidate_count": len(findings) if isinstance(findings, list) else 0,
            "records_imported": len(findings) if isinstance(findings, list) else 0,
            "report_preview": {
                key: compact_preview_value(value)
                for key, value in report_preview.items()
                if value is not None
            },
            "sample_records": [compact_preview_value(record) for record in sample_records],
            "write_target": write_target,
            "write_target_label": write_target_label,
        }

    if write_target == "user_feedback_insights":
        insights = json_path_value(
            raw_json,
            str(mapping.get("insights_path") or default_mapping.get("insights_path")),
        )
        rows = json_path_value(
            raw_json,
            str(mapping.get("rows_path") or default_mapping.get("rows_path")),
        )
        sample_records = insights[:3] if isinstance(insights, list) else []
        return {
            "candidate_count": len(insights) if isinstance(insights, list) else 0,
            "records_imported": records_imported_from_mapping(response_summary, mapping),
            "sample_records": [compact_preview_value(record) for record in sample_records],
            "source_row_count": len(rows) if isinstance(rows, list) else None,
            "write_target": write_target,
            "write_target_label": write_target_label,
        }

    if write_target == "email_notifications":
        recipients = json_path_value(
            raw_json,
            str(mapping.get("recipients_path") or default_mapping.get("recipients_path")),
        )
        sample_records = recipients[:3] if isinstance(recipients, list) else []
        if not sample_records and recipients is not None:
            sample_records = [recipients]
        delivery_id = json_path_value(
            raw_json,
            str(mapping.get("delivery_id_path") or default_mapping.get("delivery_id_path")),
        )
        delivery_status = json_path_value(
            raw_json,
            str(
                mapping.get("delivery_status_path")
                or default_mapping.get("delivery_status_path"),
            ),
        )
        subject = json_path_value(
            raw_json,
            str(mapping.get("subject_path") or default_mapping.get("subject_path")),
        )
        records_imported = records_imported_from_mapping(response_summary, mapping)
        if records_imported == 0 and (delivery_id is not None or delivery_status is not None):
            records_imported = 1
        candidate_count = len(recipients) if isinstance(recipients, list) else 0
        if candidate_count == 0 and recipients:
            candidate_count = 1
        return {
            "candidate_count": candidate_count,
            "delivery_id": compact_preview_value(delivery_id),
            "delivery_status": compact_preview_value(delivery_status),
            "records_imported": records_imported,
            "sample_records": [compact_preview_value(record) for record in sample_records],
            "subject": compact_preview_value(subject),
            "write_target": write_target,
            "write_target_label": write_target_label,
        }

    preview_value = json_path_value(raw_json, mapping.get("records_imported_path"))
    sample_records = preview_value[:3] if isinstance(preview_value, list) else []
    return {
        "candidate_count": len(preview_value) if isinstance(preview_value, list) else 0,
        "preview_value": compact_preview_value(preview_value),
        "records_imported": records_imported_from_mapping(response_summary, mapping),
        "sample_records": [compact_preview_value(record) for record in sample_records],
        "write_target": write_target,
        "write_target_label": write_target_label,
    }


def trial_plugin_action_response(
    *,
    action_id: str,
    connection_id: str | None,
    current_store: Any,
    input_payload: dict[str, Any] | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    plugin, connection, action = ensure_active_plugin_action(
        current_store,
        action_id,
        connection_id=connection_id,
    )
    payload = input_payload or {}
    start = perf_counter()
    response_summary: dict[str, Any] = {}
    error_code = None
    error_message = None
    status = "succeeded"
    request_preview = plugin_action_request_preview(plugin, connection, action, payload)
    try:
        response_summary = _invoke_action(plugin, connection, action, payload)
    except Exception as exc:
        status = "failed"
        error_code = exc.__class__.__name__
        error_message = str(exc)
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            error_code = exc.detail.get("code", error_code)
            error_message = exc.detail.get("message", error_message)
    latency_ms = int((perf_counter() - start) * 1000)
    mapping_hits = result_mapping_hits(response_summary, action.get("result_mapping") or {})
    write_preview = result_write_preview(
        response_summary,
        action.get("result_mapping") or {},
    )
    audit_event = record_audit_event(
        current_store,
        event_type=f"plugin_action.trial_{status}",
        actor_id=user["id"],
        subject_type="plugin_action",
        subject_id=action["id"],
        payload={
            "action_code": action.get("code"),
            "action_id": action["id"],
            "connection_environment": connection.get("environment"),
            "connection_id": connection["id"],
            "error_code": error_code,
            "input_keys": sorted(payload.keys()),
            "latency_ms": latency_ms,
            "plugin_code": plugin.get("code"),
            "plugin_id": plugin["id"],
            "status": status,
            "write_target": (action.get("result_mapping") or {}).get(
                "write_target",
                "scheduled_job_result",
            ),
        },
    )
    persist_audit_event(current_store, audit_event)
    return {
        "action_id": action["id"],
        "connection_id": connection["id"],
        "error_code": error_code,
        "error_message": error_message,
        "latency_ms": latency_ms,
        "mapping_hits": mapping_hits,
        "plugin_id": plugin["id"],
        "request_preview": request_preview,
        "response_summary": response_summary,
        "status": status,
        "write_preview": write_preview,
    }


def plugin_system_variables_response(
    *,
    timezone_name: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    resolved_timezone_name = timezone_name or "UTC"
    try:
        timezone = ZoneInfo(resolved_timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported timezone") from exc
    return {
        "items": dynamic_parameter_preview(timezone=timezone),
        "timezone": resolved_timezone_name,
    }


def invoke_plugin_action_response(
    *,
    action_id: str,
    connection_id: str | None = None,
    current_store: Any,
    input_payload: dict[str, Any] | None = None,
    scheduled_job_id: str | None = None,
    scheduled_job_run_id: str | None = None,
    trace_id: str | None = None,
    trigger_type: str = "manual",
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    plugin, connection, action = ensure_active_plugin_action(
        current_store,
        action_id,
        connection_id=connection_id,
    )
    start = perf_counter()
    response_summary: dict[str, Any] = {}
    error_code = None
    error_message = None
    status = "succeeded"
    try:
        response_summary = _invoke_action(plugin, connection, action, input_payload or {})
    except Exception as exc:
        status = "failed"
        error_code = exc.__class__.__name__
        error_message = str(exc)
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            error_code = exc.detail.get("code", error_code)
            error_message = exc.detail.get("message", error_message)
    latency_ms = int((perf_counter() - start) * 1000)
    now = datetime.now(UTC).isoformat()
    log_id = current_store.new_id("plugin_invocation_log")
    request_summary = {
        "action_code": action["code"],
        "input_keys": sorted((input_payload or {}).keys()),
        "plugin_code": plugin["code"],
        "protocol": plugin["protocol"],
        "request_preview": plugin_action_request_preview(
            plugin,
            connection,
            action,
            input_payload or {},
        ),
    }
    log = {
        "action_id": action["id"],
        "connection_id": connection["id"],
        "created_at": now,
        "created_by": user["id"],
        "error_code": error_code,
        "error_message": error_message,
        "id": log_id,
        "latency_ms": latency_ms,
        "plugin_id": plugin["id"],
        "request_summary": request_summary,
        "response_summary": response_summary,
        "scheduled_job_id": scheduled_job_id,
        "scheduled_job_run_id": scheduled_job_run_id,
        "status": status,
        "trace_id": trace_id,
        "trigger_type": trigger_type,
        "updated_at": now,
    }
    current_store.plugin_invocation_logs[log_id] = log
    audit_event = record_audit_event(
        current_store,
        event_type=f"plugin_action.invoke_{status}",
        actor_id=user["id"],
        subject_type="plugin_invocation_log",
        subject_id=log_id,
        payload={
            "action_id": action["id"],
            "plugin_id": plugin["id"],
            "scheduled_job_id": scheduled_job_id,
            "status": status,
        },
    )
    persist_record(
        current_store,
        "save_plugin_invocation_log_record",
        log,
        audit_event=audit_event,
    )
    if status == "failed":
        raise api_error(
            502,
            error_code or "PLUGIN_INVOCATION_FAILED",
            error_message or "Plugin invocation failed",
        )
    return public_invocation_log(log)


def list_plugin_invocation_logs_response(
    *,
    action_id: str | None,
    current_store: Any,
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    status: str | None,
) -> dict[str, Any]:
    if status is not None:
        ensure_enum(status, PLUGIN_INVOCATION_STATUSES, "status")
    sync_plugin_invocation_log_store(
        current_store,
        action_id=action_id,
        scheduled_job_id=scheduled_job_id,
        scheduled_job_run_id=scheduled_job_run_id,
        status=status,
    )
    items = []
    for log in current_store.plugin_invocation_logs.values():
        if action_id is not None and log.get("action_id") != action_id:
            continue
        if scheduled_job_id is not None and log.get("scheduled_job_id") != scheduled_job_id:
            continue
        if (
            scheduled_job_run_id is not None
            and log.get("scheduled_job_run_id") != scheduled_job_run_id
        ):
            continue
        if status is not None and log.get("status") != status:
            continue
        items.append(public_invocation_log(log))
    items.sort(key=lambda item: (item.get("created_at") or "", item["id"]), reverse=True)
    return {"items": items, "total": len(items)}
