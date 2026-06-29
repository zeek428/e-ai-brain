from __future__ import annotations

from typing import Any

from app.services.plugin_templates import STANDARD_PLUGIN_CONNECTION_TEMPLATE_VERSION


def latest_standard_plugin_template_version(plugin_code: str | None = None) -> str:
    return STANDARD_PLUGIN_CONNECTION_TEMPLATE_VERSION


def plugin_version_metadata(plugin: dict[str, Any]) -> dict[str, Any]:
    latest_version = latest_standard_plugin_template_version(str(plugin.get("code") or ""))
    template_version = str(plugin.get("template_version") or latest_version)
    if plugin.get("is_system"):
        version_status = "latest" if template_version == latest_version else "upgrade_available"
        upgrade_available = version_status == "upgrade_available"
    elif plugin.get("source_plugin_id") or plugin.get("source_plugin_code"):
        version_status = "custom"
        upgrade_available = False
    else:
        version_status = "custom"
        upgrade_available = False
    return {
        "latest_template_version": latest_version,
        "template_version": template_version,
        "upgrade_available": upgrade_available,
        "version_status": version_status,
    }


def public_plugin(plugin: dict[str, Any]) -> dict[str, Any]:
    return {**plugin, **plugin_version_metadata(plugin)}


def public_connection(connection: dict[str, Any]) -> dict[str, Any]:
    return dict(connection)


def public_action(action: dict[str, Any]) -> dict[str, Any]:
    return dict(action)


def public_invocation_log(log: dict[str, Any]) -> dict[str, Any]:
    item = dict(log)
    item["request_summary"] = redact_plugin_request_summary(item.get("request_summary"))
    return item


def is_sensitive_request_key(key: str) -> bool:
    normalized = key.lower().replace("_", "-")
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "cookie",
            "password",
            "private-token",
            "secret",
            "token",
            "x-api-key",
        )
    )


def redact_plugin_request_summary(value: Any) -> Any:
    if isinstance(value, list):
        return [redact_plugin_request_summary(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if is_sensitive_request_key(key_text):
                redacted[key_text] = "***"
            else:
                redacted[key_text] = redact_plugin_request_summary(item)
        return redacted
    return value
