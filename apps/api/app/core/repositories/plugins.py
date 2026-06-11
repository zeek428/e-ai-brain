from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


def _json(value: Any, default: Any) -> str:
    if value is None:
        value = default
    return json.dumps(value, ensure_ascii=False)


class PluginReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._upsert_audit_events = upsert_audit_events

    def list_plugins(
        self,
        *,
        protocol: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where({"protocol": protocol, "status": status})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, code, name, description, protocol, category, risk_level,
                           status, created_by, created_at, updated_at
                    FROM integration_plugins
                    {where}
                    ORDER BY code ASC, id ASC
                    """,
                    tuple(params),
                )
                return [self._plugin_from_row(row) for row in cursor.fetchall()]

    def save_plugin_record(
        self,
        plugin: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_plugins(cursor, {plugin["id"]: plugin})
                self._upsert_audit(cursor, audit_event)

    def delete_plugin_record(
        self,
        plugin_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM integration_plugins WHERE id = %s", (plugin_id,))
                self._upsert_audit(cursor, audit_event)

    def list_plugin_connections(
        self,
        *,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where({"plugin_id": plugin_id, "status": status})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, plugin_id, name, environment, endpoint_url, auth_type,
                           auth_config, request_config, timeout_seconds, max_retries, status,
                           created_by, created_at, updated_at
                    FROM plugin_connections
                    {where}
                    ORDER BY plugin_id ASC, environment ASC, id ASC
                    """,
                    tuple(params),
                )
                return [self._connection_from_row(row) for row in cursor.fetchall()]

    def save_plugin_connection_record(
        self,
        connection: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection_obj:
            with connection_obj.cursor() as cursor:
                self.upsert_plugin_connections(cursor, {connection["id"]: connection})
                self._upsert_audit(cursor, audit_event)

    def delete_plugin_connection_record(
        self,
        connection_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM plugin_connections WHERE id = %s", (connection_id,))
                self._upsert_audit(cursor, audit_event)

    def list_plugin_actions(
        self,
        *,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where({"plugin_id": plugin_id, "status": status})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, plugin_id, connection_id, code, name, description, action_type,
                           input_schema, output_schema, request_config, result_mapping,
                           requires_human_review, status, created_by, created_at, updated_at
                    FROM plugin_actions
                    {where}
                    ORDER BY plugin_id ASC, code ASC, id ASC
                    """,
                    tuple(params),
                )
                return [self._action_from_row(row) for row in cursor.fetchall()]

    def save_plugin_action_record(
        self,
        action: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_plugin_actions(cursor, {action["id"]: action})
                self._upsert_audit(cursor, audit_event)

    def delete_plugin_action_record(
        self,
        action_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM plugin_actions WHERE id = %s", (action_id,))
                self._upsert_audit(cursor, audit_event)

    def list_plugin_invocation_logs(
        self,
        *,
        action_id: str | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where(
            {
                "action_id": action_id,
                "scheduled_job_id": scheduled_job_id,
                "scheduled_job_run_id": scheduled_job_run_id,
                "status": status,
            },
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, plugin_id, connection_id, action_id, scheduled_job_id,
                           scheduled_job_run_id, trigger_type, status, request_summary,
                           response_summary, latency_ms, error_code, error_message,
                           trace_id, created_by, created_at, updated_at
                    FROM plugin_invocation_logs
                    {where}
                    ORDER BY created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._invocation_log_from_row(row) for row in cursor.fetchall()]

    def save_plugin_invocation_log_record(
        self,
        log: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_plugin_invocation_logs(cursor, {log["id"]: log})
                self._upsert_audit(cursor, audit_event)

    def upsert_plugins(self, cursor, plugins: dict[str, dict[str, Any]]) -> None:
        for plugin in plugins.values():
            cursor.execute(
                """
                INSERT INTO integration_plugins (
                  id, code, name, description, protocol, category, risk_level,
                  status, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  protocol = EXCLUDED.protocol,
                  category = EXCLUDED.category,
                  risk_level = EXCLUDED.risk_level,
                  status = EXCLUDED.status,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    plugin["id"],
                    plugin["code"],
                    plugin["name"],
                    plugin.get("description"),
                    plugin["protocol"],
                    plugin.get("category", "general"),
                    plugin.get("risk_level", "medium"),
                    plugin.get("status", "active"),
                    plugin.get("created_by"),
                    plugin.get("created_at"),
                    plugin.get("updated_at") or plugin.get("created_at"),
                ),
            )

    def upsert_plugin_connections(
        self,
        cursor,
        connections: dict[str, dict[str, Any]],
    ) -> None:
        for connection in connections.values():
            cursor.execute(
                """
                INSERT INTO plugin_connections (
                  id, plugin_id, name, environment, endpoint_url, auth_type, auth_config,
                  request_config, timeout_seconds, max_retries, status, created_by, created_at,
                  updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s::jsonb,
                  %s::jsonb, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  plugin_id = EXCLUDED.plugin_id,
                  name = EXCLUDED.name,
                  environment = EXCLUDED.environment,
                  endpoint_url = EXCLUDED.endpoint_url,
                  auth_type = EXCLUDED.auth_type,
                  auth_config = EXCLUDED.auth_config,
                  request_config = EXCLUDED.request_config,
                  timeout_seconds = EXCLUDED.timeout_seconds,
                  max_retries = EXCLUDED.max_retries,
                  status = EXCLUDED.status,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    connection["id"],
                    connection["plugin_id"],
                    connection["name"],
                    connection.get("environment", "default"),
                    connection["endpoint_url"],
                    connection.get("auth_type", "none"),
                    _json(connection.get("auth_config"), {}),
                    _json(connection.get("request_config"), {}),
                    connection.get("timeout_seconds", 30),
                    connection.get("max_retries", 0),
                    connection.get("status", "active"),
                    connection.get("created_by"),
                    connection.get("created_at"),
                    connection.get("updated_at") or connection.get("created_at"),
                ),
            )

    def upsert_plugin_actions(self, cursor, actions: dict[str, dict[str, Any]]) -> None:
        for action in actions.values():
            cursor.execute(
                """
                INSERT INTO plugin_actions (
                  id, plugin_id, connection_id, code, name, description, action_type,
                  input_schema, output_schema, request_config, result_mapping,
                  requires_human_review, status, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s, %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  plugin_id = EXCLUDED.plugin_id,
                  connection_id = EXCLUDED.connection_id,
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  action_type = EXCLUDED.action_type,
                  input_schema = EXCLUDED.input_schema,
                  output_schema = EXCLUDED.output_schema,
                  request_config = EXCLUDED.request_config,
                  result_mapping = EXCLUDED.result_mapping,
                  requires_human_review = EXCLUDED.requires_human_review,
                  status = EXCLUDED.status,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    action["id"],
                    action["plugin_id"],
                    action.get("connection_id"),
                    action["code"],
                    action["name"],
                    action.get("description"),
                    action["action_type"],
                    _json(action.get("input_schema"), {}),
                    _json(action.get("output_schema"), {}),
                    _json(action.get("request_config"), {}),
                    _json(action.get("result_mapping"), {}),
                    action.get("requires_human_review", False),
                    action.get("status", "active"),
                    action.get("created_by"),
                    action.get("created_at"),
                    action.get("updated_at") or action.get("created_at"),
                ),
            )

    def upsert_plugin_invocation_logs(self, cursor, logs: dict[str, dict[str, Any]]) -> None:
        for log in logs.values():
            cursor.execute(
                """
                INSERT INTO plugin_invocation_logs (
                  id, plugin_id, connection_id, action_id, scheduled_job_id,
                  scheduled_job_run_id, trigger_type, status, request_summary,
                  response_summary, latency_ms, error_code, error_message,
                  trace_id, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s, %s, %s::jsonb,
                  %s::jsonb, %s, %s, %s,
                  %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  plugin_id = EXCLUDED.plugin_id,
                  connection_id = EXCLUDED.connection_id,
                  action_id = EXCLUDED.action_id,
                  scheduled_job_id = EXCLUDED.scheduled_job_id,
                  scheduled_job_run_id = EXCLUDED.scheduled_job_run_id,
                  trigger_type = EXCLUDED.trigger_type,
                  status = EXCLUDED.status,
                  request_summary = EXCLUDED.request_summary,
                  response_summary = EXCLUDED.response_summary,
                  latency_ms = EXCLUDED.latency_ms,
                  error_code = EXCLUDED.error_code,
                  error_message = EXCLUDED.error_message,
                  trace_id = EXCLUDED.trace_id,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    log["id"],
                    log["plugin_id"],
                    log.get("connection_id"),
                    log["action_id"],
                    log.get("scheduled_job_id"),
                    log.get("scheduled_job_run_id"),
                    log.get("trigger_type", "manual"),
                    log["status"],
                    _json(log.get("request_summary"), {}),
                    _json(log.get("response_summary"), {}),
                    log.get("latency_ms", 0),
                    log.get("error_code"),
                    log.get("error_message"),
                    log.get("trace_id"),
                    log.get("created_by"),
                    log.get("created_at"),
                    log.get("updated_at") or log.get("created_at"),
                ),
            )

    def _upsert_audit(self, cursor, audit_event: dict[str, Any] | None) -> None:
        if audit_event is not None and self._upsert_audit_events is not None:
            self._upsert_audit_events(cursor, [audit_event])

    def _where(self, values: dict[str, Any]) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in values.items():
            if value is None:
                continue
            clauses.append(f"{field} = %s")
            params.append(value)
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _plugin_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "code": row[1],
            "name": row[2],
            "description": row[3],
            "protocol": row[4],
            "category": row[5],
            "risk_level": row[6],
            "status": row[7],
            "created_by": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
        }

    def _connection_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "plugin_id": row[1],
            "name": row[2],
            "environment": row[3],
            "endpoint_url": row[4],
            "auth_type": row[5],
            "auth_config": row[6] or {},
            "request_config": row[7] or {},
            "timeout_seconds": row[8],
            "max_retries": row[9],
            "status": row[10],
            "created_by": row[11],
            "created_at": row[12].isoformat() if row[12] else None,
            "updated_at": row[13].isoformat() if row[13] else None,
        }

    def _action_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "plugin_id": row[1],
            "connection_id": row[2],
            "code": row[3],
            "name": row[4],
            "description": row[5],
            "action_type": row[6],
            "input_schema": row[7] or {},
            "output_schema": row[8] or {},
            "request_config": row[9] or {},
            "result_mapping": row[10] or {},
            "requires_human_review": row[11],
            "status": row[12],
            "created_by": row[13],
            "created_at": row[14].isoformat() if row[14] else None,
            "updated_at": row[15].isoformat() if row[15] else None,
        }

    def _invocation_log_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "plugin_id": row[1],
            "connection_id": row[2],
            "action_id": row[3],
            "scheduled_job_id": row[4],
            "scheduled_job_run_id": row[5],
            "trigger_type": row[6],
            "status": row[7],
            "request_summary": row[8] or {},
            "response_summary": row[9] or {},
            "latency_ms": row[10],
            "error_code": row[11],
            "error_message": row[12],
            "trace_id": row[13],
            "created_by": row[14],
            "created_at": row[15].isoformat() if row[15] else None,
            "updated_at": row[16].isoformat() if row[16] else None,
        }
