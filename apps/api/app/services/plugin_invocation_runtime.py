from __future__ import annotations

import base64
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.deps import api_error
from app.services.ai_executor_runners import (
    AI_EXECUTOR_TYPES,
    SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
    create_ai_executor_task,
    find_available_runner,
)
from app.services.dynamic_parameters import (
    dynamic_parameter_resolution_trace,
    dynamic_time_parameters,
    resolve_dynamic_parameter_value,
)
from app.services.internal_data_sources import (
    INTERNAL_DATA_SOURCE_PROTOCOL,
    internal_data_source_request_preview,
    read_internal_data_source,
)
from app.services.model_gateway import (
    ModelGatewayCallError,
    ModelGatewayConfigError,
    call_model_gateway_for_task,
    save_model_gateway_records,
)
from app.services.plugin_constants import AI_EXECUTOR_RUNNER_PROTOCOLS, MCP_HTTP_PROTOCOLS
from app.services.plugin_store_helpers import _set_header, ensure_non_blank

DINGTALK_DOCUMENT_WRITE_TARGET = "dingtalk_document"
DINGTALK_DOCUMENT_LEGACY_UPDATE_TOOL_NAME = "doc.update_document_content"
DINGTALK_DOCUMENT_UPDATE_TOOL_NAME = "update_document"
DINGTALK_AITABLE_RECORDS_WRITE_TARGET = "dingtalk_aitable_records"
DINGTALK_AITABLE_CREATE_RECORDS_TOOL_NAME = "create_records"
DINGTALK_AITABLE_LEGACY_CREATE_RECORDS_TOOL_NAMES = {"aitable.create_records"}


def _call_model_gateway_for_task(current_store: Any, *, task: dict[str, Any]) -> tuple[Any, Any]:
    plugin_services = sys.modules.get("app.services.plugins")
    caller = getattr(plugin_services, "call_model_gateway_for_task", call_model_gateway_for_task)
    return caller(current_store, task=task)


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


def _url_key_query_parameters(
    connection: dict[str, Any],
    *,
    mask: bool = False,
) -> dict[str, str]:
    if connection.get("auth_type") != "url_key":
        return {}
    auth_config = connection.get("auth_config") or {}
    query_key = str(auth_config.get("query_key") or "key").strip() or "key"
    secret_ref = (
        auth_config.get("secret_ref")
        or auth_config.get("token_ref")
        or auth_config.get("url_key")
    )
    if not secret_ref:
        return {}
    return {query_key: "***" if mask else str(secret_ref)}


def _query_with_url_key(
    connection: dict[str, Any],
    query: dict[str, Any],
    *,
    mask: bool = False,
) -> dict[str, Any]:
    url_key_query = _url_key_query_parameters(connection, mask=mask)
    if not url_key_query:
        return dict(query)
    return {**query, **url_key_query}


def _mcp_headers(
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    return {
        **_build_headers(connection, action, input_payload),
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }


def dingtalk_document_id_from_url(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return stripped
    parsed = urlparse(stripped)
    if not parsed.scheme or not parsed.netloc:
        return stripped
    query = parse_qs(parsed.query)
    for key in ("base_id", "baseId", "document_id", "doc_id", "docKey", "dentryUuid", "node_id"):
        if query.get(key):
            return query[key][0]
    segments = [unquote(segment) for segment in parsed.path.split("/") if segment]
    for marker in ("nodes", "node"):
        if marker in segments:
            index = segments.index(marker)
            if index + 1 < len(segments):
                return segments[index + 1]
    return stripped


def _mcp_arguments(
    request_config: dict[str, Any],
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    configured_arguments = _dict_config_section(request_config.get("arguments"))
    arguments = {**configured_arguments, **input_payload}
    if "document_id" in arguments:
        arguments["document_id"] = dingtalk_document_id_from_url(arguments["document_id"])
    if "nodeId" in arguments:
        arguments["nodeId"] = dingtalk_document_id_from_url(arguments["nodeId"])
    if request_config.get("tool_name") == DINGTALK_DOCUMENT_UPDATE_TOOL_NAME:
        if "nodeId" not in arguments and arguments.get("document_id"):
            arguments["nodeId"] = dingtalk_document_id_from_url(arguments["document_id"])
        if "markdown" not in arguments and arguments.get("content"):
            arguments["markdown"] = arguments["content"]
        if arguments.get("markdown") and not arguments.get("format"):
            arguments["format"] = "markdown"
        arguments.pop("document_id", None)
        arguments.pop("content", None)
    if request_config.get("tool_name") == DINGTALK_AITABLE_CREATE_RECORDS_TOOL_NAME:
        if "baseId" not in arguments and arguments.get("base_id"):
            arguments["baseId"] = arguments.get("base_id")
        if "baseId" in arguments:
            arguments["baseId"] = dingtalk_document_id_from_url(arguments["baseId"])
        if "tableId" not in arguments and arguments.get("table_id"):
            arguments["tableId"] = arguments.get("table_id")
        if "records" not in arguments and arguments.get("record"):
            arguments["records"] = [arguments.get("record")]
        if "records" in arguments:
            arguments["records"] = _dingtalk_aitable_records_from_value(arguments["records"])
        arguments.pop("base_id", None)
        arguments.pop("table_id", None)
        arguments.pop("record", None)
    return arguments


def _scalar_template_parameters(*sources: dict[str, Any] | None) -> dict[str, str]:
    parameters: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if isinstance(value, str | int | float | bool):
                parameters[str(key)] = str(value)
    return parameters


def _non_blank_string(value: Any) -> str:
    return str(value).strip() if isinstance(value, str) else ""


def _apply_dingtalk_document_write_defaults(
    action: dict[str, Any],
    request_config: dict[str, Any],
) -> dict[str, Any]:
    result_mapping = _dict_config_section(action.get("result_mapping"))
    if result_mapping.get("write_target") != DINGTALK_DOCUMENT_WRITE_TARGET:
        return request_config
    if action.get("action_type") != "mcp_tool":
        return request_config

    normalized = dict(request_config)
    configured_tool_name = _non_blank_string(normalized.get("tool_name"))
    if (
        not configured_tool_name
        or configured_tool_name == DINGTALK_DOCUMENT_LEGACY_UPDATE_TOOL_NAME
    ):
        normalized["tool_name"] = DINGTALK_DOCUMENT_UPDATE_TOOL_NAME

    mcp = _dict_config_section(normalized.get("mcp"))
    if not _non_blank_string(mcp.get("provider")):
        mcp["provider"] = "dingtalk"
    if not _non_blank_string(mcp.get("server_name")):
        mcp["server_name"] = "doc"
    normalized["mcp"] = mcp

    arguments = _dict_config_section(normalized.get("arguments"))
    if arguments.get("document_id") and not arguments.get("nodeId"):
        arguments["nodeId"] = arguments.get("document_id")
    if arguments.get("content") and not arguments.get("markdown"):
        arguments["markdown"] = arguments.get("content")
    mapping_argument_defaults = {
        "format": "markdown",
        "markdown": result_mapping.get("content_template"),
        "mode": result_mapping.get("write_mode"),
        "nodeId": result_mapping.get("document_id"),
    }
    for key, value in mapping_argument_defaults.items():
        if key not in arguments and value not in (None, ""):
            arguments[key] = value
    arguments.pop("document_id", None)
    arguments.pop("content", None)
    if arguments:
        normalized["arguments"] = arguments
    return normalized


def _dingtalk_aitable_records_from_value(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped[0] in "[{":
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return value
            return _dingtalk_aitable_records_from_value(parsed)
        return value
    if isinstance(value, dict):
        nested_records = value.get("records")
        if isinstance(nested_records, list):
            return nested_records
        if isinstance(value.get("cells"), dict):
            return [value]
        return [value]
    return value


def _apply_dingtalk_aitable_record_write_defaults(
    action: dict[str, Any],
    request_config: dict[str, Any],
    connection_request_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result_mapping = _dict_config_section(action.get("result_mapping"))
    if result_mapping.get("write_target") != DINGTALK_AITABLE_RECORDS_WRITE_TARGET:
        return request_config
    if action.get("action_type") != "mcp_tool":
        return request_config

    normalized = dict(request_config)
    configured_tool_name = _non_blank_string(normalized.get("tool_name"))
    if (
        not configured_tool_name
        or configured_tool_name in DINGTALK_AITABLE_LEGACY_CREATE_RECORDS_TOOL_NAMES
    ):
        normalized["tool_name"] = DINGTALK_AITABLE_CREATE_RECORDS_TOOL_NAME

    mcp = _dict_config_section(normalized.get("mcp"))
    if not _non_blank_string(mcp.get("provider")):
        mcp["provider"] = "dingtalk"
    if not _non_blank_string(mcp.get("server_name")):
        mcp["server_name"] = "aitable"
    normalized["mcp"] = mcp

    arguments = _dict_config_section(normalized.get("arguments"))
    connection_config = _dict_config_section(connection_request_config)
    connection_base_id = _non_blank_string(connection_config.get("base_id"))
    if not connection_base_id:
        connection_base_id = _non_blank_string(
            _dict_config_section(connection_config.get("query")).get("base_id")
        )
    connection_base_id = dingtalk_document_id_from_url(connection_base_id)
    result_mapping_base_id = dingtalk_document_id_from_url(result_mapping.get("base_id"))
    mapping_argument_defaults = {
        "baseId": connection_base_id or result_mapping_base_id,
        "records": result_mapping.get("records_template"),
        "tableId": result_mapping.get("table_id"),
    }
    for key, value in mapping_argument_defaults.items():
        if key == "baseId" and connection_base_id:
            arguments[key] = connection_base_id
            continue
        if key not in arguments and value not in (None, ""):
            arguments[key] = value
    if "records" in arguments:
        arguments["records"] = _dingtalk_aitable_records_from_value(arguments["records"])
    if "baseId" in arguments:
        arguments["baseId"] = dingtalk_document_id_from_url(arguments["baseId"])
    arguments.pop("base_id", None)
    arguments.pop("table_id", None)
    if arguments:
        normalized["arguments"] = arguments
    return normalized


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
    merged_query: dict[str, Any] = {}
    if connection_query or action_query:
        merged_query = {**connection_query, **action_query}
        merged["query"] = merged_query

    connection_headers = _dict_config_section(connection_config.get("headers"))
    action_headers = _dict_config_section(action_config.get("headers"))
    if connection_headers or action_headers:
        merged["headers"] = {**connection_headers, **action_headers}

    merged = _apply_dingtalk_document_write_defaults(action, merged)
    merged = _apply_dingtalk_aitable_record_write_defaults(
        action,
        merged,
        connection_config,
    )
    timezone = plugin_invocation_timezone(input_payload)
    return resolve_dynamic_parameter_value(
        merged,
        _scalar_template_parameters(input_payload, merged_query),
        now=now,
        timezone=timezone,
    )


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
    if connection.get("auth_type") == "basic":
        username = str(auth_config.get("username") or "").strip()
        password_ref = str(auth_config.get("password_ref") or "").strip()
        password = (
            os.getenv(password_ref.removeprefix("env:"), "")
            if password_ref.startswith("env:")
            else ""
        )
        if username and password:
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
            _set_header(
                headers,
                sources,
                "Authorization",
                f"Basic {encoded}",
                "auth_config.basic",
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
    query = _query_with_url_key(connection, query)
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
        _query_with_url_key(
            connection,
            _dict_config_section(request_config.get("query")),
        ),
    )
    request = Request(
        url,
        data=json.dumps(
            {
                "id": action["id"],
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "arguments": _mcp_arguments(request_config, input_payload),
                    "name": tool_name,
                },
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers=_mcp_headers(connection, action, input_payload),
        method="POST",
    )
    with urlopen(request, timeout=connection.get("timeout_seconds", 30)) as response:
        raw = response.read().decode("utf-8")
    return {"json": json.loads(raw) if raw else {}, "mocked": False}


def _config_value(config: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in config:
        return config.get(key)
    query = config.get("query") if isinstance(config.get("query"), dict) else {}
    return query.get(key, default)


def _invoke_system_default_model_gateway_executor(
    current_store: Any,
    *,
    action: dict[str, Any],
    connection: dict[str, Any],
    input_payload: dict[str, Any],
    instruction: str,
    request_config: dict[str, Any],
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    timeout_seconds: int,
    user: dict[str, Any],
    workspace_root: str,
) -> tuple[dict[str, Any], str | None]:
    task_id = current_store.new_id("ai_executor_task")
    task = {
        "action_id": action.get("id"),
        "connection_id": connection.get("id"),
        "created_by": user["id"],
        "id": task_id,
        "input_json": {
            "expected_output_schema": {
                "details": "object | array | string, optional",
                "result": "object | array | string, optional",
                "summary": "string",
            },
            "input_payload": input_payload,
            "instruction": instruction,
            "request_config": request_config,
            "scheduled_job_id": scheduled_job_id,
            "scheduled_job_run_id": scheduled_job_run_id,
            "timeout_seconds": timeout_seconds,
            "workspace_root": workspace_root,
        },
        "product_context": {},
        "requirement_snapshot": {},
        "task_type": "ai_executor_instruction",
        "title": action.get("name") or "系统默认执行器指令",
    }
    try:
        result_json, model_log = _call_model_gateway_for_task(current_store, task=task)
        save_model_gateway_records(current_store)
    except ModelGatewayConfigError as exc:
        raise api_error(
            400,
            "MODEL_GATEWAY_CONFIG_REQUIRED",
            str(exc),
        ) from exc
    except ModelGatewayCallError as exc:
        save_model_gateway_records(current_store)
        raise api_error(
            502,
            "MODEL_GATEWAY_CALL_FAILED",
            "System default executor model gateway request failed",
        ) from exc

    model_log_id = model_log.get("id") if isinstance(model_log, dict) else None
    runner_summary = {
        "executor_type": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
        "finished_at": datetime.now(UTC).isoformat(),
        "model_gateway_called": True,
        "model_gateway_log_id": model_log_id,
        "result_json": result_json,
        "runner_id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
        "runner_task_id": None,
        "status": "succeeded",
        "workspace_root": workspace_root,
    }
    return {
        "json": {
            **runner_summary,
            "result_json": result_json,
        },
        "mocked": False,
        "runner": runner_summary,
    }, None


def _invoke_ai_executor_runner(
    current_store: Any,
    *,
    action: dict[str, Any],
    connection: dict[str, Any],
    input_payload: dict[str, Any],
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    user: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    request_config = resolve_plugin_request_config(connection, action, input_payload)
    mock_response = _config_value(request_config, "mock_response_json")
    if isinstance(mock_response, dict):
        return {
            "json": mock_response,
            "mocked": True,
            "runner": {"status": "mocked"},
        }, None

    requested_runner_id = str(_config_value(request_config, "runner_id", "") or "").strip() or None
    raw_executor_type = _config_value(request_config, "executor_type")
    default_executor_type = (
        SYSTEM_DEFAULT_AI_EXECUTOR_TYPE
        if requested_runner_id == SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID
        else "codex"
    )
    executor_type = str(raw_executor_type or default_executor_type).lower()
    if executor_type not in AI_EXECUTOR_TYPES:
        raise api_error(400, "AI_EXECUTOR_TYPE_UNSUPPORTED", "Unsupported AI executor type")
    workspace_root = ensure_non_blank(
        str(_config_value(request_config, "workspace_root", "") or ""),
        "workspace_root",
    )
    instruction = str(
        _config_value(request_config, "instruction")
        or input_payload.get("instruction")
        or input_payload.get("prompt")
        or "",
    ).strip()
    if not instruction:
        raise api_error(400, "AI_EXECUTOR_INSTRUCTION_REQUIRED", "instruction is required")
    timeout_seconds = int(
        _config_value(request_config, "instruction_timeout_seconds")
        or _config_value(request_config, "timeout_seconds")
        or connection.get("timeout_seconds")
        or 1800,
    )
    if executor_type == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE:
        return _invoke_system_default_model_gateway_executor(
            current_store,
            action=action,
            connection=connection,
            input_payload=input_payload,
            instruction=instruction,
            request_config=request_config,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            timeout_seconds=timeout_seconds,
            user=user,
            workspace_root=workspace_root,
        )
    runner = find_available_runner(
        current_store,
        executor_type=executor_type,
        runner_id=requested_runner_id,
        workspace_root=workspace_root,
    )
    task = create_ai_executor_task(
        current_store,
        action_id=action.get("id"),
        connection_id=connection.get("id"),
        created_by=user["id"],
        executor_type=executor_type,
        input_payload=input_payload,
        instruction=instruction,
        plugin_invocation_log_id=None,
        request_config=request_config,
        runner_id=runner["id"],
        scheduled_job_id=scheduled_job_id,
        scheduled_job_run_id=scheduled_job_run_id,
        timeout_seconds=timeout_seconds,
        workspace_root=workspace_root,
    )
    return {
        "json": {
            "executor_type": executor_type,
            "runner_id": runner["id"],
            "runner_task_id": task["id"],
            "status": "queued",
            "workspace_root": workspace_root,
        },
        "mocked": False,
        "runner": {
            "executor_type": executor_type,
            "runner_id": runner["id"],
            "runner_task_id": task["id"],
            "status": "queued",
            "workspace_root": workspace_root,
        },
    }, task["id"]


def _invoke_action(
    plugin: dict[str, Any],
    connection: dict[str, Any],
    action: dict[str, Any],
    input_payload: dict[str, Any],
    *,
    current_store: Any | None = None,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if plugin["protocol"] == INTERNAL_DATA_SOURCE_PROTOCOL:
        if current_store is None or user is None:
            raise api_error(
                400,
                "INTERNAL_DATA_SOURCE_CONTEXT_REQUIRED",
                "Internal data source invocation requires store and user context",
            )
        request_config = resolve_plugin_request_config(connection, action, input_payload)
        return {
            "json": read_internal_data_source(
                current_store=current_store,
                input_payload=input_payload,
                request_config=request_config,
                user=user,
            ),
            "mocked": False,
        }
    if plugin["protocol"] == "mcp_stdio":
        raise api_error(
            400,
            "PLUGIN_PROTOCOL_UNSUPPORTED",
            "mcp_stdio invocation requires isolated command execution and is not enabled",
        )
    if plugin["protocol"] in MCP_HTTP_PROTOCOLS:
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
    if plugin["protocol"] in AI_EXECUTOR_RUNNER_PROTOCOLS or (
        plugin.get("code") == "ai_executor" and plugin["protocol"] == "mcp_stdio"
    ):
        executor_type = _config_value(request_config, "executor_type", "codex")
        runner_id = _config_value(request_config, "runner_id")
        if (
            executor_type == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE
            or runner_id == SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID
        ):
            return {
                "arguments": input_payload,
                "endpoint_url": connection.get("endpoint_url"),
                "executor_type": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
                "instruction_timeout_seconds": _config_value(
                    request_config,
                    "instruction_timeout_seconds",
                    _config_value(request_config, "timeout_seconds"),
                ),
                "method": "MODEL_GATEWAY_CHAT",
                "protocol": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
                "runner_id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
                "tool_name": request_config.get("tool_name"),
                "workspace_root": _config_value(request_config, "workspace_root"),
            }
        return {
            "arguments": input_payload,
            "endpoint_url": connection.get("endpoint_url"),
            "executor_type": executor_type,
            "instruction_timeout_seconds": _config_value(
                request_config,
                "instruction_timeout_seconds",
                _config_value(request_config, "timeout_seconds"),
            ),
            "method": "RUNNER_CLAIM",
            "protocol": plugin["protocol"],
            "runner_id": runner_id,
            "tool_name": request_config.get("tool_name"),
            "workspace_root": _config_value(request_config, "workspace_root"),
        }
    if plugin["protocol"] in MCP_HTTP_PROTOCOLS:
        arguments = _mcp_arguments(request_config, input_payload)
        query = _query_with_url_key(
            connection,
            _dict_config_section(request_config.get("query")),
            mask=True,
        )
        endpoint_url = str(connection.get("endpoint_url") or "")
        return {
            "arguments": arguments,
            "endpoint_url": endpoint_url,
            "headers": headers,
            "jsonrpc_method": "tools/call",
            "method": "POST",
            "protocol": plugin["protocol"],
            "query": query,
            "tool_name": request_config.get("tool_name"),
            "url": _url_with_query(endpoint_url, query),
        }
    if plugin["protocol"] == INTERNAL_DATA_SOURCE_PROTOCOL:
        return internal_data_source_request_preview(
            connection=connection,
            input_payload=input_payload,
            request_config=request_config,
        )
    method = str(request_config.get("method") or "GET").upper()
    path = str(request_config.get("path") or "")
    url = urljoin(str(connection.get("endpoint_url", "")).rstrip("/") + "/", path.lstrip("/"))
    query = _dict_config_section(request_config.get("query"))
    query = _query_with_url_key(connection, query, mask=True)
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
