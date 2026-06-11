from __future__ import annotations

import json
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.deps import api_error, require_roles
from app.services.dynamic_parameters import (
    dynamic_parameter_preview,
    dynamic_time_parameters,
    resolve_dynamic_parameter_value,
)
from app.services.operational_records import record_audit_event, save_single_repository_record

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
SECRET_KEYS = {
    "api_key",
    "api_key_ref",
    "authorization",
    "password",
    "private-token",
    "secret",
    "secret_ref",
    "token",
    "token_ref",
    "x-api-key",
}


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
    plugin_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = plugin_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "plugin_connections",
        repository.list_plugin_connections(plugin_id=plugin_id, status=status),
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


def mask_secret_config(value: Any) -> Any:
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in SECRET_KEYS:
                masked[key] = "***"
            else:
                masked[key] = mask_secret_config(item)
        return masked
    if isinstance(value, list):
        return [mask_secret_config(item) for item in value]
    return value


def compact_preview_value(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= 200 else f"{value[:200]}..."
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    try:
        encoded = json.dumps(mask_secret_config(value), ensure_ascii=False)
    except TypeError:
        return str(value)[:200]
    return value if len(encoded) <= 400 else f"{encoded[:400]}..."


def diagnostic_step(
    name: str,
    *,
    detail: str | None = None,
    latency_ms: int | None = None,
    status: str = "succeeded",
    **extra: Any,
) -> dict[str, Any]:
    step = {"name": name, "status": status}
    if detail is not None:
        step["detail"] = detail
    if latency_ms is not None:
        step["latency_ms"] = latency_ms
    step.update({key: value for key, value in extra.items() if value is not None})
    return step


def public_plugin(plugin: dict[str, Any]) -> dict[str, Any]:
    return dict(plugin)


def public_connection(connection: dict[str, Any]) -> dict[str, Any]:
    public = dict(connection)
    public["auth_config"] = mask_secret_config(public.get("auth_config") or {})
    return public


def public_action(action: dict[str, Any]) -> dict[str, Any]:
    return dict(action)


def public_invocation_log(log: dict[str, Any]) -> dict[str, Any]:
    public = dict(log)
    public["request_summary"] = mask_secret_config(public.get("request_summary") or {})
    public["response_summary"] = mask_secret_config(public.get("response_summary") or {})
    return public


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
    items = []
    for plugin in current_store.integration_plugins.values():
        if protocol is not None and plugin.get("protocol") != protocol:
            continue
        if status is not None and plugin.get("status") != status:
            continue
        items.append(public_plugin(plugin))
    items.sort(key=lambda item: (item.get("code") or "", item["id"]))
    return {"items": items, "total": len(items)}


def create_plugin_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
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


def ensure_active_plugin(current_store: Any, plugin_id: str) -> dict[str, Any]:
    sync_plugin_store(current_store)
    plugin = current_store.integration_plugins.get(plugin_id)
    if plugin is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    if plugin.get("status") != "active":
        raise api_error(400, "PLUGIN_INACTIVE", "Plugin is inactive")
    return plugin


def list_plugin_connections_response(
    *,
    current_store: Any,
    plugin_id: str | None,
    status: str | None,
) -> dict[str, Any]:
    if status is not None:
        ensure_enum(status, PLUGIN_STATUSES, "status")
    sync_plugin_connection_store(current_store, plugin_id=plugin_id, status=status)
    items = []
    for connection in current_store.plugin_connections.values():
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
        diagnostic_step(
            "endpoint_configured",
            detail=parsed_endpoint.netloc or parsed_endpoint.path or "未配置 Endpoint",
            status="succeeded" if connection.get("endpoint_url") else "failed",
        ),
    )
    diagnostics.append(
        diagnostic_step(
            "protocol_supported",
            detail=str(plugin.get("protocol")),
            status="failed" if plugin.get("protocol") == "mcp_stdio" else "succeeded",
        ),
    )
    auth_type = str(connection.get("auth_type") or "none")
    auth_config = connection.get("auth_config") or {}
    diagnostics.append(
        diagnostic_step(
            "auth_configured",
            detail=auth_type,
            status="warning" if auth_type != "none" and not auth_config else "succeeded",
        ),
    )
    try:
        if "mock_test_response" in auth_config:
            mocked = True
            diagnostics.append(
                diagnostic_step(
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
                connection["endpoint_url"],
                data=json.dumps(
                    {
                        "id": f"connection_test_{connection_id}",
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "params": {},
                    },
                    ensure_ascii=False,
                ).encode("utf-8"),
                headers={
                    **_build_headers(connection, {"request_config": {}}),
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            timeout = min(int(connection.get("timeout_seconds") or 10), 10)
            with urlopen(request, timeout=timeout) as response:
                response.read(512)
                diagnostics.append(
                    diagnostic_step(
                        "mcp_tools_list",
                        detail="tools/list 调用完成",
                        latency_ms=int((perf_counter() - step_start) * 1000),
                        status_code=getattr(response, "status", None),
                    ),
                )
        else:
            step_start = perf_counter()
            request = Request(
                connection["endpoint_url"],
                headers=_build_headers(connection, {"request_config": {}}),
                method="GET",
            )
            timeout = min(int(connection.get("timeout_seconds") or 10), 10)
            with urlopen(request, timeout=timeout) as response:
                response.read(512)
                diagnostics.append(
                    diagnostic_step(
                        "network_request",
                        detail="HTTP GET 调用完成",
                        latency_ms=int((perf_counter() - step_start) * 1000),
                        status_code=getattr(response, "status", None),
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
            diagnostic_step(
                "network_request" if plugin.get("protocol") != "mcp_http" else "mcp_tools_list",
                detail=error_message,
                status="failed",
                error_code=error_code,
            ),
        )
    latency_ms = int((perf_counter() - start) * 1000)
    result = {
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
        "request_summary": {
            "auth_config": mask_secret_config(auth_config),
            "auth_type": auth_type,
            "host": parsed_endpoint.netloc,
            "method": "POST" if plugin.get("protocol") == "mcp_http" else "GET",
            "protocol": plugin.get("protocol"),
            "scheme": parsed_endpoint.scheme,
        },
        "status": status,
    }
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
        {**connection, "updated_at": datetime.now(UTC).isoformat()},
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
    return value if isinstance(value, int) and value >= 0 else 0


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


def _build_headers(
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    headers = dict(resolve_action_request_config(action, input_payload).get("headers") or {})
    auth_config = connection.get("auth_config") or {}
    if connection.get("auth_type") == "bearer" and auth_config.get("token_ref"):
        headers.setdefault("Authorization", f"Bearer {auth_config['token_ref']}")
    if connection.get("auth_type") == "api_key_header":
        header_name = auth_config.get("header_name") or "X-API-Key"
        secret_ref = auth_config.get("secret_ref")
        if secret_ref:
            headers.setdefault(header_name, str(secret_ref))
    return {str(key): str(value) for key, value in headers.items()}


def _invoke_http(
    plugin: dict[str, Any],
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    request_config = resolve_action_request_config(action, input_payload)
    if "mock_response_json" in request_config:
        return {"json": request_config["mock_response_json"], "mocked": True}
    method = str(request_config.get("method") or "GET").upper()
    path = str(request_config.get("path") or "")
    url = urljoin(connection["endpoint_url"].rstrip("/") + "/", path.lstrip("/"))
    query = request_config.get("query") or {}
    if query:
        url = f"{url}?{urlencode(query)}"
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
    request_config = resolve_action_request_config(action, input_payload)
    if "mock_response_json" in request_config:
        return {"json": request_config["mock_response_json"], "mocked": True}
    tool_name = ensure_non_blank(request_config.get("tool_name"), "tool_name")
    request = Request(
        connection["endpoint_url"],
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
    request_config = resolve_action_request_config(action, input_payload)
    headers = mask_secret_config(_build_headers(connection, action, input_payload))
    if plugin["protocol"] == "mcp_http":
        return {
            "arguments": mask_secret_config(input_payload),
            "endpoint_url": connection.get("endpoint_url"),
            "headers": headers,
            "jsonrpc_method": "tools/call",
            "method": "POST",
            "protocol": plugin["protocol"],
            "tool_name": request_config.get("tool_name"),
        }
    method = str(request_config.get("method") or "GET").upper()
    path = str(request_config.get("path") or "")
    url = urljoin(str(connection.get("endpoint_url", "")).rstrip("/") + "/", path.lstrip("/"))
    query = request_config.get("query") or {}
    if query:
        url = f"{url}?{urlencode(query)}"
    return {
        "body": mask_secret_config(input_payload if method not in {"GET", "HEAD"} else None),
        "headers": headers,
        "method": method,
        "path": path,
        "protocol": plugin["protocol"],
        "query": mask_secret_config(query),
        "url": url,
    }


def result_mapping_hits(
    response_summary: dict[str, Any],
    mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for key, path in mapping.items():
        if not isinstance(path, str) or not path.startswith("$."):
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
    return {
        "action_id": action["id"],
        "connection_id": connection["id"],
        "error_code": error_code,
        "error_message": error_message,
        "latency_ms": latency_ms,
        "mapping_hits": result_mapping_hits(response_summary, action.get("result_mapping") or {}),
        "plugin_id": plugin["id"],
        "request_preview": request_preview,
        "response_summary": mask_secret_config(response_summary),
        "status": status,
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
