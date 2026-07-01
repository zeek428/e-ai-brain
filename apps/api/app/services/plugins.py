from __future__ import annotations

import json
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.api.deps import api_error
from app.core.listing import add_list_observability, sort_list_items
from app.services.connection_diagnostics import ConnectionDiagnosticsService
from app.services.dynamic_parameters import dynamic_parameter_preview
from app.services.model_gateway import (  # noqa: F401 - re-exported for service tests/imports.
    call_model_gateway_for_task,
)
from app.services.operational_records import record_audit_event, save_single_repository_record
from app.services.plugin_connection_config import (
    ensure_plugin_connection_auth_requirements,
    normalize_github_connection_request_config,
    normalize_gitlab_connection_config,
)
from app.services.plugin_constants import (
    AI_EXECUTOR_RUNNER_PROTOCOLS,
    PLUGIN_ACTION_SORT_FIELDS,
    PLUGIN_ACTION_TYPES,
    PLUGIN_AUTH_TYPES,
    PLUGIN_CATEGORIES,
    PLUGIN_CONNECTION_ENVIRONMENTS,
    PLUGIN_CONNECTION_SORT_FIELDS,
    PLUGIN_INVOCATION_LOG_SORT_FIELDS,
    PLUGIN_INVOCATION_STATUSES,
    PLUGIN_PROTOCOLS,
    PLUGIN_STATUSES,
)
from app.services.plugin_delete_protection import (
    action_delete_usages,
    connection_delete_usages,
    ensure_not_used_for_delete,
    plugin_delete_usages,
)
from app.services.plugin_invocation_runtime import (
    _build_headers_with_sources,
    _dict_config_section,
    _invoke_action,
    _invoke_ai_executor_runner,
    _url_with_query,
    connection_request_variable_resolutions,
    plugin_action_request_preview,
    resolve_action_request_config,  # noqa: F401 - re-exported for existing service tests/imports.
    resolve_connection_request_config,
    resolve_plugin_request_config,  # noqa: F401 - re-exported for existing service tests/imports.
)
from app.services.plugin_projection import (
    latest_standard_plugin_template_version,
    plugin_version_metadata,
    public_action,
    public_connection,
    public_invocation_log,
    public_plugin,
    redact_plugin_request_summary,
)
from app.services.plugin_result_mapping import result_mapping_hits, result_write_preview
from app.services.plugin_result_write_records import (
    RESULT_WRITE_RECORD_SORT_FIELDS,
    RESULT_WRITE_RECORD_STATUSES,
    can_list_result_write_records_from_repository,
    list_result_write_records_payload,
)
from app.services.plugin_store_helpers import (
    _delete_memory_record,
    _is_masked_secret_placeholder,
    _put_memory_record,
    _read_memory_dict,
    _read_memory_record,
    ensure_enum,
    ensure_non_blank,
    ensure_plugin_mutable,
    ensure_standard_plugins,
    merge_masked_config,
    persist_audit_event,
    persist_record,
    plugin_query_repository,
    require_admin,
    sync_plugin_action_store,
    sync_plugin_connection_store,
    sync_plugin_dependency_store,
    sync_plugin_invocation_log_store,
    sync_plugin_store,
    sync_result_write_record_store,
)
from app.services.plugin_templates import (
    STANDARD_PLUGIN_CONNECTION_TEMPLATE_VERSION,
    STANDARD_PLUGIN_MARKETPLACE_METADATA,
    STANDARD_PLUGINS,
    standard_plugin_action_templates,
    standard_plugin_connection_defaults,
    standard_plugin_connection_schema,
)
from app.services.product_scope import product_scope_filter
from app.services.result_write_targets import result_write_targets


def list_plugins_response(
    *,
    current_store: Any,
    protocol: str | None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    if protocol is not None:
        ensure_enum(protocol, PLUGIN_PROTOCOLS, "protocol")
    if status is not None:
        ensure_enum(status, PLUGIN_STATUSES, "status")
    sync_plugin_store(current_store, protocol=protocol, status=status)
    ensure_standard_plugins(current_store)
    items = []
    for plugin in _read_memory_dict(current_store, "integration_plugins").values():
        if protocol is not None and plugin.get("protocol") != protocol:
            continue
        if status is not None and plugin.get("status") != status:
            continue
        items.append(public_plugin(plugin))
    items.sort(key=lambda item: (item.get("code") or "", item["id"]))
    return {"items": items, "total": len(items)}


def _connection_with_plugin_projection(
    current_store: Any,
    connection: dict[str, Any],
) -> dict[str, Any]:
    item = dict(connection)
    if item.get("plugin_name") and item.get("plugin_code"):
        return item
    plugin = _read_memory_record(current_store, "integration_plugins", str(item.get("plugin_id") or ""))
    if plugin is not None:
        item.setdefault("plugin_name", plugin.get("name"))
        item.setdefault("plugin_code", plugin.get("code"))
    return item


def list_plugin_marketplace_response(
    *,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_dependency_store(current_store)
    ensure_standard_plugins(current_store)
    connections = list(_read_memory_dict(current_store, "plugin_connections").values())
    actions = list(_read_memory_dict(current_store, "plugin_actions").values())
    plugins_by_code = {
        str(plugin.get("code")): plugin
        for plugin in _read_memory_dict(current_store, "integration_plugins").values()
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
        version_metadata = plugin_version_metadata(plugin or template)
        items.append(
            {
                "action_count": len(plugin_actions),
                "action_templates": metadata.get("action_templates", []),
                "category": template["category"],
                "code": template["code"],
                "connection_defaults": standard_plugin_connection_defaults(str(template["code"])),
                "connection_schema": standard_plugin_connection_schema(str(template["code"])),
                "connection_count": len(plugin_connections),
                "connection_template_version": STANDARD_PLUGIN_CONNECTION_TEMPLATE_VERSION,
                "description": template["description"],
                "id": f"marketplace_{template['code']}",
                "installed": plugin is not None,
                "is_system": True,
                "latest_template_version": version_metadata["latest_template_version"],
                "name": template["name"],
                "plugin_id": plugin_id if plugin is not None else None,
                "protocol": template["protocol"],
                "publisher": metadata.get("publisher", "AI Brain 官方"),
                "recommended_scenarios": metadata.get("recommended_scenarios", []),
                "risk_level": template["risk_level"],
                "status": plugin.get("status") if plugin else "not_installed",
                "summary": metadata.get("summary") or template["description"],
                "template_version": version_metadata["template_version"],
                "upgrade_available": version_metadata["upgrade_available"],
                "version_status": version_metadata["version_status"],
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
        for plugin in _read_memory_dict(current_store, "integration_plugins").values()
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


def list_result_write_records_response(
    *,
    current_store: Any,
    page: int | None = None,
    page_size: int | None = None,
    plugin_action_id: str | None,
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
    write_target: str | None,
) -> dict[str, Any]:
    require_admin(user)
    if status is not None:
        ensure_enum(status, RESULT_WRITE_RECORD_STATUSES, "status")
    ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_enum(sort_by, RESULT_WRITE_RECORD_SORT_FIELDS, "sort_by")
    if not can_list_result_write_records_from_repository(
        current_store,
        page=page,
        page_size=page_size,
    ):
        sync_result_write_record_store(current_store)
    return list_result_write_records_payload(
        current_store=current_store,
        page=page,
        page_size=page_size,
        plugin_action_id=plugin_action_id,
        scheduled_job_id=scheduled_job_id,
        scheduled_job_run_id=scheduled_job_run_id,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at,
        status=status,
        user=user,
        write_target=write_target,
    )


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
    _put_memory_record(current_store, "integration_plugins", plugin)
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


def copy_plugin_response(
    *,
    current_store: Any,
    payload: Any,
    plugin_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_store(current_store)
    ensure_standard_plugins(current_store)
    source = _read_memory_record(current_store, "integration_plugins", plugin_id)
    if source is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    updates = payload.model_dump(exclude_unset=True)
    base_code = ensure_non_blank(str(source.get("code") or plugin_id), "code")
    code = ensure_non_blank(updates.get("code") or f"{base_code}_custom", "code")
    if any(
        plugin.get("code") == code
        for plugin in _read_memory_dict(current_store, "integration_plugins").values()
    ):
        raise api_error(409, "PLUGIN_CODE_EXISTS", f"Plugin code already exists: {code}")
    name = ensure_non_blank(
        updates.get("name") or f"{source.get('name') or base_code} 副本",
        "name",
    )
    now = datetime.now(UTC).isoformat()
    copied_id = current_store.new_id("plugin")
    copied = {
        "category": ensure_non_blank(
            updates.get("category") or source.get("category") or "general",
            "category",
        ),
        "code": code,
        "created_at": now,
        "created_by": user["id"],
        "description": updates.get("description", source.get("description")),
        "id": copied_id,
        "is_system": False,
        "name": name,
        "protocol": updates.get("protocol") or source.get("protocol") or "http",
        "risk_level": updates.get("risk_level") or source.get("risk_level") or "medium",
        "source_plugin_code": source.get("code"),
        "source_plugin_id": source["id"],
        "status": updates.get("status") or source.get("status") or "active",
        "template_version": source.get("template_version")
        or latest_standard_plugin_template_version(str(source.get("code") or "")),
        "updated_at": now,
    }
    ensure_enum(copied["category"], PLUGIN_CATEGORIES, "category")
    ensure_enum(copied["protocol"], PLUGIN_PROTOCOLS, "protocol")
    ensure_enum(copied["status"], PLUGIN_STATUSES, "status")
    _put_memory_record(current_store, "integration_plugins", copied)
    audit_event = record_audit_event(
        current_store,
        event_type="plugin.copied",
        actor_id=user["id"],
        subject_type="plugin",
        subject_id=copied_id,
        payload={
            "code": copied["code"],
            "source_plugin_id": source["id"],
            "source_plugin_code": source.get("code"),
        },
    )
    persist_record(current_store, "save_plugin_record", copied, audit_event=audit_event)
    return public_plugin(copied)


def patch_plugin_response(
    *,
    current_store: Any,
    payload: Any,
    plugin_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_store(current_store)
    plugin = _read_memory_record(current_store, "integration_plugins", plugin_id)
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
    _put_memory_record(current_store, "integration_plugins", plugin)
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
    plugin = _read_memory_record(current_store, "integration_plugins", plugin_id)
    if plugin is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    ensure_plugin_mutable(plugin)
    ensure_not_used_for_delete(
        plugin_delete_usages(current_store, plugin_id),
        object_label=f"插件「{plugin['name']}」",
    )
    _delete_memory_record(current_store, "integration_plugins", plugin_id)
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
    plugin = _read_memory_record(current_store, "integration_plugins", plugin_id)
    if plugin is None:
        raise api_error(404, "NOT_FOUND", "Plugin not found")
    if plugin.get("status") != "active":
        raise api_error(400, "PLUGIN_INACTIVE", "Plugin is inactive")
    return plugin


def list_plugin_connections_response(
    *,
    current_store: Any,
    environment: str | None,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    plugin_id: str | None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    if environment is not None:
        ensure_enum(environment, PLUGIN_CONNECTION_ENVIRONMENTS, "environment")
    if status is not None:
        ensure_enum(status, PLUGIN_STATUSES, "status")
    ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_enum(sort_by, PLUGIN_CONNECTION_SORT_FIELDS, "sort_by")
    repository = plugin_query_repository(current_store)
    with_pagination = page is not None or page_size is not None
    count_page = getattr(repository, "count_plugin_connections", None)
    list_page = getattr(repository, "list_plugin_connections_page", None)
    resolved_sort_by = sort_by or "plugin_id"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    if with_pagination and callable(count_page) and callable(list_page):
        total = count_page(
            environment=environment,
            keyword=keyword,
            plugin_id=plugin_id,
            status=status,
        )
        items = [
            public_connection(_connection_with_plugin_projection(current_store, connection))
            for connection in list_page(
                environment=environment,
                keyword=keyword,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                plugin_id=plugin_id,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                status=status,
            )
        ]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters={
                "environment": environment,
                "keyword": keyword,
                "plugin_id": plugin_id,
                "status": status,
            },
            list_name="plugin_connections",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    sync_plugin_connection_store(
        current_store,
        environment=environment,
        plugin_id=plugin_id,
        status=status,
    )
    items = []
    for connection in _read_memory_dict(current_store, "plugin_connections").values():
        if environment is not None and connection.get("environment") != environment:
            continue
        if plugin_id is not None and connection.get("plugin_id") != plugin_id:
            continue
        if status is not None and connection.get("status") != status:
            continue
        if keyword is not None:
            keyword_text = str(keyword).strip().lower()
            if keyword_text and keyword_text not in " ".join(
                str(connection.get(field) or "").lower()
                for field in (
                    "id",
                    "plugin_id",
                    "name",
                    "environment",
                    "endpoint_url",
                    "auth_type",
                    "status",
                )
            ):
                continue
        items.append(public_connection(_connection_with_plugin_projection(current_store, connection)))
    if sort_by is None and not with_pagination:
        items.sort(
            key=lambda item: (
                item.get("plugin_id") or "",
                item.get("environment") or "",
                item["id"],
            ),
        )
    else:
        items = sort_list_items(
            items,
            allowed_fields=PLUGIN_CONNECTION_SORT_FIELDS,
            default_sort_by=resolved_sort_by,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    total = len(items)
    if with_pagination:
        start_index = (resolved_page - 1) * resolved_page_size
        items = items[start_index : start_index + resolved_page_size]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters={
                "environment": environment,
                "keyword": keyword,
                "plugin_id": plugin_id,
                "status": status,
            },
            list_name="plugin_connections",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    return {"items": items, "total": total}


def create_plugin_connection_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    plugin = ensure_active_plugin(current_store, payload.plugin_id)
    ensure_enum(payload.auth_type, PLUGIN_AUTH_TYPES, "auth_type")
    ensure_enum(payload.environment or "default", PLUGIN_CONNECTION_ENVIRONMENTS, "environment")
    ensure_enum(payload.status, PLUGIN_STATUSES, "status")
    ensure_plugin_connection_auth_requirements(
        auth_config=payload.auth_config,
        auth_type=payload.auth_type,
        plugin=plugin,
    )
    now = datetime.now(UTC).isoformat()
    connection_id = current_store.new_id("plugin_connection")
    endpoint_url = ensure_non_blank(payload.endpoint_url, "endpoint_url")
    request_config = normalize_github_connection_request_config(payload.request_config, plugin)
    endpoint_url, request_config = normalize_gitlab_connection_config(
        endpoint_url=endpoint_url,
        request_config=request_config,
        plugin=plugin,
    )
    connection = {
        "auth_config": payload.auth_config,
        "auth_type": payload.auth_type,
        "created_at": now,
        "created_by": user["id"],
        "endpoint_url": endpoint_url,
        "environment": ensure_non_blank(payload.environment or "default", "environment"),
        "id": connection_id,
        "max_retries": payload.max_retries,
        "name": ensure_non_blank(payload.name, "name"),
        "plugin_id": payload.plugin_id,
        "request_config": request_config,
        "status": payload.status,
        "timeout_seconds": payload.timeout_seconds,
        "updated_at": now,
    }
    _put_memory_record(current_store, "plugin_connections", connection)
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
    return public_connection(_connection_with_plugin_projection(current_store, connection))


def patch_plugin_connection_response(
    *,
    connection_id: str,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_connection_store(current_store)
    connection = _read_memory_record(current_store, "plugin_connections", connection_id)
    if connection is None:
        raise api_error(404, "NOT_FOUND", "Plugin connection not found")
    updates = payload.model_dump(exclude_unset=True)
    next_plugin = connection.get("plugin_id")
    if "plugin_id" in updates:
        ensure_active_plugin(current_store, updates["plugin_id"])
        next_plugin = updates["plugin_id"]
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
    plugin = ensure_active_plugin(current_store, str(next_plugin))
    connection["request_config"] = normalize_github_connection_request_config(
        connection.get("request_config") or {},
        plugin,
    )
    endpoint_url, request_config = normalize_gitlab_connection_config(
        endpoint_url=str(connection.get("endpoint_url") or ""),
        request_config=connection["request_config"],
        plugin=plugin,
    )
    connection["endpoint_url"] = ensure_non_blank(endpoint_url, "endpoint_url")
    connection["request_config"] = request_config
    ensure_plugin_connection_auth_requirements(
        auth_config=connection.get("auth_config") or {},
        auth_type=str(connection.get("auth_type") or "none"),
        plugin=plugin,
    )
    _put_memory_record(current_store, "plugin_connections", connection)
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
    return public_connection(_connection_with_plugin_projection(current_store, connection))


def delete_plugin_connection_response(
    *,
    connection_id: str,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    sync_plugin_dependency_store(current_store)
    connection = _read_memory_record(current_store, "plugin_connections", connection_id)
    if connection is None:
        raise api_error(404, "NOT_FOUND", "Plugin connection not found")
    ensure_not_used_for_delete(
        connection_delete_usages(current_store, connection_id),
        object_label=f"连接「{connection['name']}」",
    )
    _delete_memory_record(current_store, "plugin_connections", connection_id)
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
    connection = _read_memory_record(current_store, "plugin_connections", connection_id)
    if connection is None:
        raise api_error(404, "NOT_FOUND", "Plugin connection not found")
    plugin = _read_memory_record(
        current_store,
        "integration_plugins",
        connection.get("plugin_id"),
    )
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
    _put_memory_record(current_store, "plugin_connections", connection)
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
    connection = _read_memory_record(current_store, "plugin_connections", connection_id)
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


def resolve_plugin_id_for_action_payload(
    current_store: Any,
    *,
    connection_id: str | None,
    existing_plugin_id: str | None = None,
    plugin_id: str | None = None,
) -> str:
    connection = ensure_active_connection(current_store, connection_id)
    resolved_plugin_id = str(connection["plugin_id"]) if connection is not None else None
    if plugin_id is not None:
        if resolved_plugin_id is not None and resolved_plugin_id != plugin_id:
            raise api_error(
                400,
                "PLUGIN_CONNECTION_MISMATCH",
                "Plugin connection does not belong to plugin",
            )
        resolved_plugin_id = plugin_id
    if resolved_plugin_id is None and existing_plugin_id is not None:
        resolved_plugin_id = existing_plugin_id
    if resolved_plugin_id is None:
        raise api_error(400, "PLUGIN_REQUIRED", "Plugin is required when no connection is selected")
    ensure_active_plugin(current_store, resolved_plugin_id)
    if connection_id is not None:
        ensure_active_connection(current_store, connection_id, plugin_id=resolved_plugin_id)
    return resolved_plugin_id


def list_plugin_actions_response(
    *,
    current_store: Any,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    plugin_id: str | None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    if status is not None:
        ensure_enum(status, PLUGIN_STATUSES, "status")
    ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_enum(sort_by, PLUGIN_ACTION_SORT_FIELDS, "sort_by")
    repository = plugin_query_repository(current_store)
    with_pagination = page is not None or page_size is not None
    count_page = getattr(repository, "count_plugin_actions", None)
    list_page = getattr(repository, "list_plugin_actions_page", None)
    resolved_sort_by = sort_by or "plugin_id"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    if with_pagination and callable(count_page) and callable(list_page):
        total = count_page(keyword=keyword, plugin_id=plugin_id, status=status)
        items = [
            public_action(action)
            for action in list_page(
                keyword=keyword,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                plugin_id=plugin_id,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                status=status,
            )
        ]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters={"keyword": keyword, "plugin_id": plugin_id, "status": status},
            list_name="plugin_actions",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    sync_plugin_action_store(current_store, plugin_id=plugin_id, status=status)
    items = []
    for action in _read_memory_dict(current_store, "plugin_actions").values():
        if plugin_id is not None and action.get("plugin_id") != plugin_id:
            continue
        if status is not None and action.get("status") != status:
            continue
        if keyword is not None:
            keyword_text = str(keyword).strip().lower()
            if keyword_text and keyword_text not in " ".join(
                str(action.get(field) or "").lower()
                for field in (
                    "id",
                    "plugin_id",
                    "connection_id",
                    "code",
                    "name",
                    "description",
                    "action_type",
                    "status",
                )
            ):
                continue
        items.append(public_action(action))
    if sort_by is None and not with_pagination:
        items.sort(
            key=lambda item: (
                item.get("plugin_id") or "",
                item.get("code") or "",
                item["id"],
            ),
        )
    else:
        items = sort_list_items(
            items,
            allowed_fields=PLUGIN_ACTION_SORT_FIELDS,
            default_sort_by=resolved_sort_by,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    total = len(items)
    if with_pagination:
        start_index = (resolved_page - 1) * resolved_page_size
        items = items[start_index : start_index + resolved_page_size]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters={"keyword": keyword, "plugin_id": plugin_id, "status": status},
            list_name="plugin_actions",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    return {"items": items, "total": total}


def create_plugin_action_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    plugin_id = resolve_plugin_id_for_action_payload(
        current_store,
        connection_id=payload.connection_id,
        plugin_id=payload.plugin_id,
    )
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
        "plugin_id": plugin_id,
        "request_config": payload.request_config,
        "requires_human_review": payload.requires_human_review,
        "result_mapping": payload.result_mapping,
        "status": payload.status,
        "updated_at": now,
    }
    _put_memory_record(current_store, "plugin_actions", action)
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
    action = _read_memory_record(current_store, "plugin_actions", action_id)
    if action is None:
        raise api_error(404, "NOT_FOUND", "Plugin action not found")
    updates = payload.model_dump(exclude_unset=True)
    connection_id = updates.get("connection_id", action.get("connection_id"))
    plugin_id = resolve_plugin_id_for_action_payload(
        current_store,
        connection_id=connection_id,
        existing_plugin_id=action["plugin_id"],
        plugin_id=updates.get("plugin_id"),
    )
    updates["plugin_id"] = plugin_id
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
    _put_memory_record(current_store, "plugin_actions", action)
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
    action = _read_memory_record(current_store, "plugin_actions", action_id)
    if action is None:
        raise api_error(404, "NOT_FOUND", "Plugin action not found")
    ensure_not_used_for_delete(
        action_delete_usages(current_store, action_id),
        object_label=f"动作「{action['name']}」",
    )
    _delete_memory_record(current_store, "plugin_actions", action_id)
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
    action = _read_memory_record(current_store, "plugin_actions", action_id)
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
        "connection": public_connection(_connection_with_plugin_projection(current_store, connection)),
        "plugin": public_plugin(plugin),
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
    runner_task_id: str | None = None
    try:
        if plugin["protocol"] in AI_EXECUTOR_RUNNER_PROTOCOLS or (
            plugin.get("code") == "ai_executor" and plugin["protocol"] == "mcp_stdio"
        ):
            response_summary, runner_task_id = _invoke_ai_executor_runner(
                current_store,
                action=action,
                connection=connection,
                input_payload=input_payload or {},
                scheduled_job_id=scheduled_job_id,
                scheduled_job_run_id=scheduled_job_run_id,
                user=user,
            )
        else:
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
    request_preview = plugin_action_request_preview(
        plugin,
        connection,
        action,
        input_payload or {},
    )
    request_summary = {
        "action_code": action["code"],
        "input_keys": sorted((input_payload or {}).keys()),
        "plugin_code": plugin["code"],
        "protocol": plugin["protocol"],
        "request_preview": redact_plugin_request_summary(request_preview),
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
    _put_memory_record(current_store, "plugin_invocation_logs", log)
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
    runner_task = _read_memory_record(current_store, "ai_executor_tasks", runner_task_id)
    if runner_task is not None:
        runner_task = {
            **runner_task,
            "plugin_invocation_log_id": log_id,
            "updated_at": now,
        }
        _put_memory_record(current_store, "ai_executor_tasks", runner_task)
        save_single_repository_record(
            current_store,
            "save_ai_executor_task_record",
            runner_task,
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
    page: int | None = None,
    page_size: int | None = None,
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    if status is not None:
        ensure_enum(status, PLUGIN_INVOCATION_STATUSES, "status")
    ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_enum(sort_by, PLUGIN_INVOCATION_LOG_SORT_FIELDS, "sort_by")
    resolved_sort_by = sort_by or "created_at"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    with_pagination = page is not None or page_size is not None
    scoped_product_ids = product_scope_filter(user)
    filters = {
        "action_id": action_id,
        "product_scope_ids": scoped_product_ids,
        "scheduled_job_id": scheduled_job_id,
        "scheduled_job_run_id": scheduled_job_run_id,
        "status": status,
    }
    repository = plugin_query_repository(current_store)
    count_page = getattr(repository, "count_plugin_invocation_logs", None)
    list_page = getattr(repository, "list_plugin_invocation_logs_page", None)
    if with_pagination and callable(count_page) and callable(list_page):
        total = count_page(**filters)
        items = [
            public_invocation_log(log)
            for log in list_page(
                **filters,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
            )
        ]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="plugin_invocation_logs",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    sync_plugin_invocation_log_store(
        current_store,
        action_id=action_id,
        product_scope_ids=scoped_product_ids,
        scheduled_job_id=scheduled_job_id,
        scheduled_job_run_id=scheduled_job_run_id,
        status=status,
    )
    items = []
    for log in _read_memory_dict(current_store, "plugin_invocation_logs").values():
        if scoped_product_ids is not None:
            job_id = log.get("scheduled_job_id")
            if not job_id and log.get("scheduled_job_run_id"):
                run = _read_memory_record(
                    current_store,
                    "scheduled_job_runs",
                    str(log.get("scheduled_job_run_id")),
                )
                job_id = run.get("scheduled_job_id") if run else None
            job = _read_memory_record(current_store, "scheduled_jobs", str(job_id))
            if job is None or str(job.get("product_id")) not in scoped_product_ids:
                continue
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
    items = sort_list_items(
        items,
        allowed_fields=PLUGIN_INVOCATION_LOG_SORT_FIELDS,
        default_sort_by=resolved_sort_by,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    if with_pagination:
        start_index = (resolved_page - 1) * resolved_page_size
        items = items[start_index : start_index + resolved_page_size]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="plugin_invocation_logs",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    return {"items": items, "total": total}
