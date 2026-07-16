from __future__ import annotations

from typing import Any

from app.services.internal_data_sources import INTERNAL_DATA_SOURCE_PROTOCOL
from app.services.plugin_constants import MCP_HTTP_PROTOCOLS


def connection_test_request_parts(
    *,
    connection_id: str,
    plugin_protocol: str | None,
    request_config: dict[str, Any],
    request_headers: dict[str, str],
    header_sources: dict[str, str],
) -> tuple[bool, str, dict[str, Any] | None, dict[str, str], dict[str, str]]:
    """Build a connection-test request while preserving explicit HTTP configuration."""
    is_mcp_http_protocol = plugin_protocol in MCP_HTTP_PROTOCOLS
    if plugin_protocol == INTERNAL_DATA_SOURCE_PROTOCOL:
        request_method = "INTERNAL_READ"
    elif is_mcp_http_protocol:
        request_method = "POST"
    else:
        request_method = str(request_config.get("method") or "GET").upper()

    request_body: dict[str, Any] | None = None
    if is_mcp_http_protocol:
        request_body = {
            "id": f"connection_test_{connection_id}",
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
        }
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
    elif request_method not in {"GET", "HEAD"} and isinstance(request_config.get("body"), dict):
        request_body = request_config["body"]
        if not any(name.lower() == "content-type" for name in request_headers):
            request_headers = {**request_headers, "Content-Type": "application/json"}
            header_sources = {**header_sources, "Content-Type": "system.default"}

    return is_mcp_http_protocol, request_method, request_body, request_headers, header_sources
