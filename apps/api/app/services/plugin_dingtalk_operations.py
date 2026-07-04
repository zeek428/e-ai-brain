from __future__ import annotations

import json
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib.request import Request, urlopen

from app.api.deps import api_error
from app.services.connection_diagnostics import ConnectionDiagnosticsService
from app.services.operational_records import record_audit_event
from app.services.plugin_constants import MCP_HTTP_PROTOCOLS
from app.services.plugin_invocation_runtime import (
    _build_headers_with_sources,
    _dict_config_section,
    _query_with_url_key,
    _url_with_query,
    resolve_connection_request_config,
)
from app.services.plugin_projection import (
    public_invocation_log,
    redact_plugin_request_summary,
)
from app.services.plugin_store_helpers import (
    _put_memory_record,
    _read_memory_dict,
    _read_memory_record,
    ensure_standard_plugins,
    persist_record,
    require_admin,
    sync_plugin_connection_store,
    sync_plugin_dependency_store,
    sync_plugin_store,
)
from app.services.plugin_templates import standard_plugin_action_templates


def _connection_plugin(
    current_store: Any,
    connection: dict[str, Any],
) -> dict[str, Any] | None:
    plugin_id = str(connection.get("plugin_id") or "")
    return _read_memory_record(current_store, "integration_plugins", plugin_id)


def _json_rpc_tools(response_json: dict[str, Any]) -> list[dict[str, Any]]:
    result = response_json.get("result")
    tools = result.get("tools") if isinstance(result, dict) else response_json.get("tools")
    if not isinstance(tools, list):
        return []
    normalized: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "").strip()
        if not name:
            continue
        schema = tool.get("inputSchema")
        if not isinstance(schema, dict):
            schema = tool.get("input_schema")
        normalized.append(
            {
                "description": tool.get("description"),
                "input_schema": schema if isinstance(schema, dict) else {},
                "name": name,
            },
        )
    return sorted(normalized, key=lambda item: item["name"])


def _known_mcp_tools_for_plugin(plugin_code: str) -> dict[str, dict[str, Any]]:
    known_tools: dict[str, dict[str, Any]] = {}
    for template in standard_plugin_action_templates():
        if template.get("plugin_code") != plugin_code:
            continue
        request_config = template.get("request_config")
        if not isinstance(request_config, dict):
            continue
        tool_name = str(request_config.get("tool_name") or "").strip()
        if not tool_name:
            continue
        tool_schema = request_config.get("tool_schema")
        known_tools[tool_name] = tool_schema if isinstance(tool_schema, dict) else {}
    return known_tools


def discover_plugin_connection_tools_response(
    *,
    connection_id: str,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_connection_store(current_store)
    sync_plugin_store(current_store)
    connection = _read_memory_record(current_store, "plugin_connections", connection_id)
    if connection is None:
        raise api_error(404, "NOT_FOUND", "Plugin connection not found")
    plugin = _connection_plugin(current_store, connection)
    if plugin is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    if plugin.get("protocol") not in MCP_HTTP_PROTOCOLS:
        raise api_error(
            400,
            "PLUGIN_PROTOCOL_UNSUPPORTED",
            "Tool discovery only supports MCP HTTP protocols",
        )

    request_config = resolve_connection_request_config(connection, now=datetime.now(UTC))
    request_query = _dict_config_section(request_config.get("query"))
    network_query = _query_with_url_key(connection, request_query)
    summary_query = _query_with_url_key(connection, request_query, mask=True)
    network_request_url = _url_with_query(str(connection.get("endpoint_url") or ""), network_query)
    summary_request_url = _url_with_query(str(connection.get("endpoint_url") or ""), summary_query)
    request_body = {
        "id": f"connection_discovery_{connection_id}",
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
    }
    request_headers, header_sources = _build_headers_with_sources(
        connection,
        {"request_config": {}},
    )
    request_headers = {
        **request_headers,
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    header_sources = {
        **header_sources,
        "Accept": "system.default",
        "Content-Type": "system.default",
    }
    start = perf_counter()
    request = Request(
        network_request_url,
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    timeout = min(int(connection.get("timeout_seconds") or 10), 10)
    with urlopen(request, timeout=timeout) as response:
        body_preview = response.read(8192).decode("utf-8", errors="replace")
        response_summary: dict[str, Any] = {
            "body_preview": body_preview,
            "status_code": getattr(response, "status", None),
        }
        parsed_json = ConnectionDiagnosticsService.json_from_body_preview(body_preview)
        if parsed_json is not None:
            response_summary["json"] = parsed_json
    parsed_response = response_summary.get("json")
    tools = _json_rpc_tools(parsed_response if isinstance(parsed_response, dict) else {})
    discovered_by_name = {tool["name"]: tool for tool in tools}
    known_tools = _known_mcp_tools_for_plugin(str(plugin.get("code") or ""))
    new_tools = sorted(set(discovered_by_name) - set(known_tools))
    missing_tools = sorted(set(known_tools) - set(discovered_by_name))
    schema_changed_tools = sorted(
        tool_name
        for tool_name in set(known_tools) & set(discovered_by_name)
        if known_tools[tool_name]
        and discovered_by_name[tool_name].get("input_schema") != known_tools[tool_name]
    )
    suggestions = _tool_drift_suggestions(
        missing_tools=missing_tools,
        new_tools=new_tools,
        schema_changed_tools=schema_changed_tools,
    )
    status = (
        "drift_detected"
        if new_tools or missing_tools or schema_changed_tools
        else "succeeded"
    )
    request_summary = {
        "body": request_body,
        "header_sources": header_sources,
        "headers": request_headers,
        "method": "POST",
        "protocol": plugin.get("protocol"),
        "query": summary_query,
        "request_config": request_config,
        "url": summary_request_url,
    }
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "connection_id": connection_id,
        "discovered_tools": tools,
        "known_tools": sorted(known_tools),
        "latency_ms": int((perf_counter() - start) * 1000),
        "missing_tools": missing_tools,
        "new_tools": new_tools,
        "plugin_id": plugin["id"],
        "request_summary": redact_plugin_request_summary(request_summary),
        "response_summary": response_summary,
        "schema_changed_tools": schema_changed_tools,
        "status": status,
        "suggestions": suggestions,
        "tool_count": len(tools),
    }
    _save_discovery_summary(
        connection=connection,
        connection_id=connection_id,
        current_store=current_store,
        missing_tools=missing_tools,
        new_tools=new_tools,
        plugin=plugin,
        result=result,
        schema_changed_tools=schema_changed_tools,
        status=status,
        user=user,
    )
    return result


def _tool_drift_suggestions(
    *,
    missing_tools: list[str],
    new_tools: list[str],
    schema_changed_tools: list[str],
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    suggestions.extend(
        {
            "detail": f"新增工具 {tool_name} 可生成动作模板并进入人工确认。",
            "tool_name": tool_name,
            "type": "suggest_action_template",
        }
        for tool_name in new_tools
    )
    suggestions.extend(
        {
            "detail": f"内置动作模板依赖的工具 {tool_name} 已下线或不可见。",
            "tool_name": tool_name,
            "type": "warn_disable_action",
        }
        for tool_name in missing_tools
    )
    suggestions.extend(
        {
            "detail": f"工具 {tool_name} 参数 schema 已变化，请复核动作输入。",
            "tool_name": tool_name,
            "type": "mark_needs_review",
        }
        for tool_name in schema_changed_tools
    )
    return suggestions


def _save_discovery_summary(
    *,
    connection: dict[str, Any],
    connection_id: str,
    current_store: Any,
    missing_tools: list[str],
    new_tools: list[str],
    plugin: dict[str, Any],
    result: dict[str, Any],
    schema_changed_tools: list[str],
    status: str,
    user: dict[str, Any],
) -> None:
    updated_connection = {
        **connection,
        "last_discovery_summary": {
            "checked_at": result["checked_at"],
            "missing_tools": missing_tools,
            "new_tools": new_tools,
            "schema_changed_tools": schema_changed_tools,
            "status": status,
            "tool_count": result["tool_count"],
        },
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _put_memory_record(current_store, "plugin_connections", updated_connection)
    audit_event = record_audit_event(
        current_store,
        event_type=f"plugin_connection.discovery_{status}",
        actor_id=user["id"],
        subject_type="plugin_connection",
        subject_id=connection_id,
        payload={
            "missing_tool_count": len(missing_tools),
            "new_tool_count": len(new_tools),
            "plugin_id": plugin["id"],
            "schema_changed_tool_count": len(schema_changed_tools),
            "status": status,
        },
    )
    persist_record(
        current_store,
        "save_plugin_connection_record",
        updated_connection,
        audit_event=audit_event,
    )


def _percentile_95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * 0.95))
    return ordered[index]


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def plugin_observability_response(
    *,
    current_store: Any,
    provider: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_dependency_store(current_store)
    ensure_standard_plugins(current_store)
    normalized_provider = str(provider or "dingtalk")
    if normalized_provider != "dingtalk":
        raise api_error(400, "PLUGIN_PROVIDER_UNSUPPORTED", "Only dingtalk provider is supported")
    plugins_by_id = {
        str(plugin.get("id")): plugin
        for plugin in _read_memory_dict(current_store, "integration_plugins").values()
    }
    dingtalk_plugin_ids = {
        plugin_id
        for plugin_id, plugin in plugins_by_id.items()
        if str(plugin.get("code") or "").startswith("dingtalk_")
    }
    actions_by_id = {
        str(action.get("id")): action
        for action in _read_memory_dict(current_store, "plugin_actions").values()
    }
    connections = [
        connection
        for connection in _read_memory_dict(current_store, "plugin_connections").values()
        if str(connection.get("plugin_id") or "") in dingtalk_plugin_ids
    ]
    logs = [
        public_invocation_log(log)
        for log in _read_memory_dict(current_store, "plugin_invocation_logs").values()
        if str(log.get("plugin_id") or "") in dingtalk_plugin_ids
    ]
    return {
        **_observability_activity(logs=logs, actions_by_id=actions_by_id),
        "connection_health": [
            {
                "connection_id": connection.get("id"),
                "connection_name": connection.get("name"),
                "last_test_summary": connection.get("last_test_summary"),
                "status": connection.get("status"),
            }
            for connection in connections
        ],
        "key_expiry_alerts": _key_expiry_alerts(connections),
        "provider": normalized_provider,
    }


def _observability_activity(
    *,
    actions_by_id: dict[str, dict[str, Any]],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(logs)
    succeeded = len([log for log in logs if log.get("status") == "succeeded"])
    failed = len([log for log in logs if log.get("status") == "failed"])
    latencies = [
        int(log["latency_ms"])
        for log in logs
        if isinstance(log.get("latency_ms"), int)
    ]
    failure_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for log in logs:
        if log.get("status") == "failed":
            reason = str(log.get("error_code") or log.get("error_message") or "unknown")
            failure_counts[reason] = failure_counts.get(reason, 0) + 1
        action = actions_by_id.get(str(log.get("action_id") or ""))
        action_code = str(action.get("code") if action else log.get("action_id") or "unknown")
        action_counts[action_code] = action_counts.get(action_code, 0) + 1
    recent_replays = sorted(
        logs,
        key=lambda log: str(log.get("created_at") or ""),
        reverse=True,
    )[:10]
    return {
        "action_trend": [
            {"action_code": action_code, "count": count}
            for action_code, count in sorted(
                action_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "failure_reason_distribution": [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                failure_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "redacted_recent_replays": [
            {
                "action_id": log.get("action_id"),
                "created_at": log.get("created_at"),
                "request_preview": (
                    log.get("request_summary", {}).get("request_preview")
                    if isinstance(log.get("request_summary"), dict)
                    else None
                ),
                "status": log.get("status"),
                "trace_id": log.get("trace_id"),
            }
            for log in recent_replays
        ],
        "summary": {
            "average_latency_ms": int(sum(latencies) / len(latencies)) if latencies else None,
            "failed_invocations": failed,
            "latency_p95_ms": _percentile_95(latencies),
            "success_rate": round(succeeded / total, 4) if total else None,
            "succeeded_invocations": succeeded,
            "total_invocations": total,
        },
    }


def _key_expiry_alerts(connections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    alerts: list[dict[str, Any]] = []
    for connection in connections:
        auth_config = (
            connection.get("auth_config")
            if isinstance(connection.get("auth_config"), dict)
            else {}
        )
        expires_at = _parse_datetime(auth_config.get("key_expires_at"))
        if expires_at is None:
            continue
        expires_at_utc = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
        days_left = (expires_at_utc - now).days
        alerts.append(
            {
                "connection_id": connection.get("id"),
                "connection_name": connection.get("name"),
                "days_left": days_left,
                "expires_at": expires_at_utc.isoformat(),
                "severity": "warning" if days_left >= 0 else "expired",
            },
        )
    return alerts
