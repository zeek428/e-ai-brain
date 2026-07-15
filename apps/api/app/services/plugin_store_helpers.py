from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_permissions
from app.services.operational_records import save_single_repository_record
from app.services.plugin_constants import (
    DEPRECATED_STANDARD_PLUGIN_CODES,
    MASKED_SECRET_PLACEHOLDER,
)
from app.services.plugin_projection import latest_standard_plugin_template_version
from app.services.plugin_templates import (
    STANDARD_PLUGINS,
    SYSTEM_INTERNAL_DATA_SOURCE_ACTION_ID,
    SYSTEM_INTERNAL_DATA_SOURCE_CONNECTION_ID,
    SYSTEM_INTERNAL_DATA_SOURCE_INPUT_SCHEMA,
    plugin_action_payload_from_template,
    plugin_action_template_for_plugin_code,
    plugin_connection_payload_from_template,
)


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def _read_memory_record(
    current_store: Any,
    collection_name: str,
    record_id: str | None,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    item = _read_memory_dict(current_store, collection_name).get(str(record_id))
    return item if isinstance(item, dict) else None


def _put_memory_record(
    current_store: Any,
    collection_name: str,
    record: dict[str, Any],
) -> None:
    _memory_dict(current_store, collection_name)[str(record["id"])] = record


def _delete_memory_record(current_store: Any, collection_name: str, record_id: str) -> None:
    _memory_dict(current_store, collection_name).pop(record_id, None)


def require_admin(user: dict[str, Any]) -> None:
    require_permissions(user, {"system.plugins.manage"})


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
    product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
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


def sync_result_write_record_store(current_store: Any) -> None:
    sync_plugin_dependency_store(current_store)
    repository = getattr(current_store, "repository", None)
    list_scheduled_job_runs = getattr(repository, "list_scheduled_job_runs", None)
    if callable(list_scheduled_job_runs):
        replace_collection(
            current_store,
            "scheduled_job_runs",
            list_scheduled_job_runs(scheduled_job_id=None, status=None),
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


def persist_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    append_audit_event = getattr(repository, "append_audit_event", None)
    if callable(append_audit_event):
        append_audit_event(audit_event)


def ensure_standard_plugins(current_store: Any) -> None:
    now = datetime.now(UTC).isoformat()
    for plugin in list(_read_memory_dict(current_store, "integration_plugins").values()):
        if str(plugin.get("code")) in DEPRECATED_STANDARD_PLUGIN_CODES:
            description = str(plugin.get("description") or "")
            if "官方标准" in description:
                description = description.replace("官方标准", "普通 HTTP ")
            elif description.startswith("普通 HTTP阿里云"):
                description = description.replace("普通 HTTP阿里云", "普通 HTTP 阿里云", 1)
            protocol = plugin.get("protocol", "http")
            normalized_protocol = "http" if protocol == "mcp_http" else protocol
            if (
                not plugin.get("is_system")
                and description == plugin.get("description")
                and normalized_protocol == protocol
            ):
                continue
            demoted_plugin = {
                **plugin,
                "description": description,
                "is_system": False,
                "protocol": normalized_protocol,
                "updated_at": now,
            }
            _put_memory_record(current_store, "integration_plugins", demoted_plugin)
            persist_record(current_store, "save_plugin_record", demoted_plugin)
    existing_by_code = {
        str(plugin.get("code")): plugin
        for plugin in _read_memory_dict(current_store, "integration_plugins").values()
    }
    for template in STANDARD_PLUGINS:
        existing = existing_by_code.get(template["code"])
        standard_record = {
            **template,
            "template_version": latest_standard_plugin_template_version(str(template["code"])),
        }
        if existing and all(existing.get(key) == value for key, value in standard_record.items()):
            continue
        plugin = {
            **standard_record,
            "created_at": existing.get("created_at") if existing else now,
            "created_by": existing.get("created_by") if existing else "system",
            "updated_at": now,
            **({"id": existing["id"]} if existing else {}),
        }
        _put_memory_record(current_store, "integration_plugins", plugin)
        if existing and existing.get("id") != plugin["id"]:
            _delete_memory_record(current_store, "integration_plugins", existing["id"])
        persist_record(current_store, "save_plugin_record", plugin)


def ensure_standard_internal_data_source_resources(current_store: Any) -> None:
    """Provision the zero-configuration internal data source for scheduled jobs."""
    plugins_by_code = {
        str(plugin.get("code")): plugin
        for plugin in _read_memory_dict(current_store, "integration_plugins").values()
    }
    plugin = plugins_by_code.get("internal_data_source")
    if plugin is None:
        return

    plugin_id = str(plugin["id"])
    sync_plugin_connection_store(current_store, plugin_id=plugin_id)
    connection = _read_memory_record(
        current_store,
        "plugin_connections",
        SYSTEM_INTERNAL_DATA_SOURCE_CONNECTION_ID,
    )
    now = datetime.now(UTC).isoformat()
    if connection is None:
        connection = {
            **plugin_connection_payload_from_template(
                "internal_data_source",
                plugin_id=plugin_id,
            ),
            "created_at": now,
            "created_by": "system",
            "id": SYSTEM_INTERNAL_DATA_SOURCE_CONNECTION_ID,
            "updated_at": now,
        }
        _put_memory_record(current_store, "plugin_connections", connection)
        persist_record(current_store, "save_plugin_connection_record", connection)

    sync_plugin_action_store(current_store, plugin_id=plugin_id)
    action = _read_memory_record(
        current_store,
        "plugin_actions",
        SYSTEM_INTERNAL_DATA_SOURCE_ACTION_ID,
    )
    if action is not None:
        return
    action_template = plugin_action_template_for_plugin_code("internal_data_source")
    if action_template is None:
        return
    action = {
        **plugin_action_payload_from_template(
            action_template,
            connection_id=str(connection["id"]),
            plugin_id=plugin_id,
        ),
        "created_at": now,
        "created_by": "system",
        "description": action_template.get("description"),
        "id": SYSTEM_INTERNAL_DATA_SOURCE_ACTION_ID,
        "input_schema": SYSTEM_INTERNAL_DATA_SOURCE_INPUT_SCHEMA,
        "output_schema": {},
        "updated_at": now,
    }
    _put_memory_record(current_store, "plugin_actions", action)
    persist_record(current_store, "save_plugin_action_record", action)


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
