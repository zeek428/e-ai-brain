from __future__ import annotations

import json
import re
import shlex
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse

from app.services.result_write_targets import result_write_target_default_mapping


class ConnectionDiagnosticsService:
    """Build connection test diagnostics, replay payloads, and repair hints."""

    TEST_HISTORY_LIMIT = 5

    @staticmethod
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

    @staticmethod
    def test_summary(result: dict[str, Any]) -> dict[str, Any]:
        failed_step = next(
            (
                step.get("name")
                for step in result.get("diagnostics") or []
                if isinstance(step, dict) and step.get("status") == "failed"
            ),
            None,
        )
        response_summary = result.get("response_summary") or {}
        return {
            "checked_at": result.get("checked_at"),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
            "failed_step": failed_step,
            "latency_ms": result.get("latency_ms"),
            "mocked": result.get("mocked", False),
            "response_status_code": response_summary.get("status_code"),
            "status": result.get("status"),
        }

    @staticmethod
    def action_template_draft(
        connection: dict[str, Any],
        plugin: dict[str, Any],
        request_summary: dict[str, Any],
    ) -> dict[str, Any]:
        if plugin.get("protocol") == "internal_read_model":
            return {
                "action_type": "internal_query",
                "code": "query_internal_business_data",
                "connection_id": connection["id"],
                "description": "由内部数据源连接测试生成，运行时按连接配置只读读取内部业务数据。",
                "name": f"{connection['name']} 读取内部业务数据",
                "plugin_id": plugin["id"],
                "request_config": {"tool_name": "internal_data_source.query"},
                "requires_human_review": False,
                "result_mapping": result_write_target_default_mapping("scheduled_job_result"),
                "status": "draft",
            }
        original_request_config = (
            request_summary.get("original_request_config")
            if isinstance(request_summary.get("original_request_config"), dict)
            else {}
        )
        request_url = str(
            request_summary.get("url")
            or connection.get("endpoint_url")
            or "",
        )
        parsed_url = urlparse(request_url)
        request_config: dict[str, Any] = {
            **original_request_config,
            "method": str(request_summary.get("method") or "GET").upper(),
            "path": parsed_url.path or "/",
        }
        if "query" not in request_config and isinstance(request_summary.get("query"), dict):
            request_config["query"] = request_summary["query"]
        return {
            "action_type": "http_request",
            "code": ConnectionDiagnosticsService._connection_test_action_code(connection, plugin),
            "connection_id": connection["id"],
            "description": (
                "由连接测试请求回放生成，请确认请求路径、Params、Headers "
                "和结果映射后保存。"
            ),
            "name": f"{connection['name']} 请求动作",
            "plugin_id": plugin["id"],
            "request_config": request_config,
            "requires_human_review": False,
            "result_mapping": result_write_target_default_mapping("scheduled_job_result"),
            "status": "draft",
        }

    @staticmethod
    def repair_suggestions(result: dict[str, Any]) -> list[dict[str, str]]:
        suggestions: list[dict[str, str]] = []
        request_summary = (
            result.get("request_summary")
            if isinstance(result.get("request_summary"), dict)
            else {}
        )
        placeholder_headers = request_summary.get("masked_placeholder_headers")
        if isinstance(placeholder_headers, list) and placeholder_headers:
            suggestions.append(
                {
                    "code": "masked_header_placeholder",
                    "detail": (
                        "最终请求 Header 仍包含 *** 占位，请填写真实 Header 值，"
                        "或把 Authorization/API Key 放到认证配置中统一生成。"
                    ),
                    "title": "替换脱敏 Header 占位",
                },
            )
        response_summary = (
            result.get("response_summary")
            if isinstance(result.get("response_summary"), dict)
            else {}
        )
        status_code = response_summary.get("status_code")
        if status_code == 400:
            suggestions.append(
                {
                    "code": "http_400_request_parameters",
                    "detail": (
                        "远端返回 HTTP 400，优先检查 Params、Headers、动态日期分区"
                        "和请求路径是否符合第三方接口要求。"
                    ),
                    "title": "检查请求参数和日期分区",
                },
            )
        elif status_code in {401, 403}:
            suggestions.append(
                {
                    "code": "http_authentication_failed",
                    "detail": (
                        "远端返回认证或授权错误，请检查认证方式、Token/API Key、"
                        "Header 名和目标环境权限。"
                    ),
                    "title": "检查认证配置",
                },
            )
        variable_resolutions = request_summary.get("variable_resolutions")
        if isinstance(variable_resolutions, list) and any(
            isinstance(item, dict) and item.get("status") != "resolved"
            for item in variable_resolutions
        ):
            suggestions.append(
                {
                    "code": "dynamic_variable_unresolved",
                    "detail": "存在未成功解析的动态变量，请检查变量名称、偏移写法和作业时区。",
                    "title": "检查动态变量表达式",
                },
            )
        if result.get("status") == "failed" and not suggestions:
            suggestions.append(
                {
                    "code": "inspect_request_replay",
                    "detail": (
                        "请对比请求回放中的最终 URL、Params、Headers、Body 和远端响应，"
                        "确认第三方接口是否可用。"
                    ),
                    "title": "对比请求回放",
                },
            )
        return suggestions

    @staticmethod
    def append_test_history(
        connection: dict[str, Any],
        result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        current_history = connection.get("test_history")
        if not isinstance(current_history, list):
            current_history = []
        return [
            ConnectionDiagnosticsService.test_history_entry(result),
            *[entry for entry in current_history if isinstance(entry, dict)],
        ][: ConnectionDiagnosticsService.TEST_HISTORY_LIMIT]

    @staticmethod
    def test_history_entry(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "action_template_draft": result.get("action_template_draft"),
            "checked_at": result.get("checked_at"),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
            "latency_ms": result.get("latency_ms"),
            "repair_suggestions": result.get("repair_suggestions") or [],
            "request_summary": result.get("request_summary") or {},
            "response_summary": result.get("response_summary") or {},
            "status": result.get("status"),
        }

    @staticmethod
    def curl_command_from_request_summary(request_summary: dict[str, Any]) -> str:
        method = str(request_summary.get("method") or "GET")
        url = str(request_summary.get("url") or "")
        headers = request_summary.get("headers")
        body = request_summary.get("body")
        parts = ["curl", "-X", method]
        if isinstance(headers, dict):
            for header_name in sorted(headers):
                header_value = headers[header_name]
                parts.extend(["-H", f"{header_name}: {header_value}"])
        if body is not None:
            parts.extend(["--data-raw", json.dumps(body, ensure_ascii=False)])
        parts.append(url)
        return " ".join(shlex.quote(str(part)) for part in parts)

    @staticmethod
    def response_summary_from_http_error(exc: HTTPError) -> dict[str, Any]:
        body = exc.read(2048).decode("utf-8", errors="replace")
        return {
            "body_preview": body,
            "reason": getattr(exc, "reason", None),
            "status_code": exc.code,
        }

    @staticmethod
    def _slug_fragment(value: Any) -> str:
        words = re.findall(r"[A-Za-z0-9]+", str(value or "").lower())
        return "_".join(words)

    @staticmethod
    def _connection_test_action_code(connection: dict[str, Any], plugin: dict[str, Any]) -> str:
        environment = ConnectionDiagnosticsService._slug_fragment(connection.get("environment"))
        name = ConnectionDiagnosticsService._slug_fragment(connection.get("name"))
        plugin_code = ConnectionDiagnosticsService._slug_fragment(plugin.get("code"))
        suffix = "_".join(part for part in [environment, name or plugin_code or "request"] if part)
        return f"test_{suffix}"[:80]
