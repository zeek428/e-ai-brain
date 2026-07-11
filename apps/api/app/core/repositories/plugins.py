from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


def _json(value: Any, default: Any) -> str:
    if value is None:
        value = default
    return json.dumps(value, ensure_ascii=False)


PLUGIN_CONNECTION_SORT_COLUMNS = {
    "created_at": "pc.created_at",
    "endpoint_url": "lower(pc.endpoint_url)",
    "environment": "pc.environment",
    "id": "pc.id",
    "name": "lower(pc.name)",
    "plugin_id": "pc.plugin_id",
    "status": "pc.status",
    "updated_at": "pc.updated_at",
}

PLUGIN_ACTION_SORT_COLUMNS = {
    "action_type": "action_type",
    "code": "lower(code)",
    "created_at": "created_at",
    "id": "id",
    "name": "lower(name)",
    "plugin_id": "plugin_id",
    "status": "status",
    "updated_at": "updated_at",
}

AI_EXECUTOR_TASK_SORT_COLUMNS = {
    "claimed_at": "claimed_at",
    "created_at": "created_at",
    "executor_type": "executor_type",
    "finished_at": "finished_at",
    "id": "id",
    "runner_id": "runner_id",
    "scheduled_job_run_id": "scheduled_job_run_id",
    "status": "status",
    "updated_at": "updated_at",
}

AI_EXECUTOR_RUNNER_SORT_COLUMNS = {
    "created_at": "created_at",
    "endpoint_url": "lower(endpoint_url)",
    "id": "id",
    "last_heartbeat_at": "last_heartbeat_at",
    "name": "lower(name)",
    "protocol": "protocol",
    "status": "status",
    "updated_at": "updated_at",
}

AI_EXECUTOR_APPROVAL_REQUEST_SORT_COLUMNS = {
    "approved_at": "approved_at",
    "created_at": "created_at",
    "executor_type": "executor_type",
    "id": "id",
    "requested_at": "requested_at",
    "risk_level": "risk_level",
    "runner_id": "runner_id",
    "status": "status",
    "updated_at": "updated_at",
}

PLUGIN_INVOCATION_LOG_SORT_COLUMNS = {
    "action_id": "action_id",
    "connection_id": "connection_id",
    "created_at": "created_at",
    "id": "id",
    "latency_ms": "latency_ms",
    "plugin_id": "plugin_id",
    "scheduled_job_id": "scheduled_job_id",
    "scheduled_job_run_id": "scheduled_job_run_id",
    "status": "status",
    "updated_at": "updated_at",
}

RESULT_WRITE_RECORD_SORT_COLUMNS = {
    "created_at": "created_at",
    "id": "id",
    "plugin_action_id": "plugin_action_id",
    "plugin_invocation_log_id": "plugin_invocation_log_id",
    "records_imported": "records_imported",
    "scheduled_job_id": "scheduled_job_id",
    "scheduled_job_run_id": "scheduled_job_run_id",
    "source_type": "source_type",
    "status": "status",
    "updated_at": "updated_at",
    "write_target": "write_target",
}


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
                           status, is_system, created_by, created_at, updated_at
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
        environment: str | None = None,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._plugin_connection_where(
            environment=environment,
            plugin_id=plugin_id,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT pc.id, pc.plugin_id, pc.name, pc.environment, pc.endpoint_url,
                           pc.auth_type, pc.auth_config, pc.request_config, pc.timeout_seconds,
                           pc.max_retries, pc.status, pc.created_by, pc.created_at, pc.updated_at,
                           pc.last_test_summary, pc.test_history, plugin.name, plugin.code
                    FROM plugin_connections pc
                    LEFT JOIN integration_plugins plugin ON plugin.id = pc.plugin_id
                    {where}
                    ORDER BY pc.plugin_id ASC, pc.environment ASC, pc.id ASC
                    """,
                    tuple(params),
                )
                return [self._connection_from_row(row) for row in cursor.fetchall()]

    def count_plugin_connections(
        self,
        *,
        environment: str | None = None,
        keyword: str | None = None,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._plugin_connection_where(
            environment=environment,
            keyword=keyword,
            plugin_id=plugin_id,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM plugin_connections pc {where}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_plugin_connections_page(
        self,
        *,
        environment: str | None = None,
        keyword: str | None = None,
        limit: int,
        offset: int,
        plugin_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._plugin_connection_where(
            environment=environment,
            keyword=keyword,
            plugin_id=plugin_id,
            status=status,
        )
        sort_column = PLUGIN_CONNECTION_SORT_COLUMNS.get(sort_by, "plugin_id")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT pc.id, pc.plugin_id, pc.name, pc.environment, pc.endpoint_url,
                           pc.auth_type, pc.auth_config, pc.request_config, pc.timeout_seconds,
                           pc.max_retries, pc.status, pc.created_by, pc.created_at, pc.updated_at,
                           pc.last_test_summary, pc.test_history, plugin.name, plugin.code
                    FROM plugin_connections pc
                    LEFT JOIN integration_plugins plugin ON plugin.id = pc.plugin_id
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, pc.id {direction}
                    LIMIT %s OFFSET %s
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

    def count_plugin_actions(
        self,
        *,
        keyword: str | None = None,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._plugin_action_where(
            keyword=keyword,
            plugin_id=plugin_id,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM plugin_actions {where}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_plugin_actions_page(
        self,
        *,
        keyword: str | None = None,
        limit: int,
        offset: int,
        plugin_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._plugin_action_where(
            keyword=keyword,
            plugin_id=plugin_id,
            status=status,
        )
        sort_column = PLUGIN_ACTION_SORT_COLUMNS.get(sort_by, "plugin_id")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, plugin_id, connection_id, code, name, description, action_type,
                           input_schema, output_schema, request_config, result_mapping,
                           requires_human_review, status, created_by, created_at, updated_at
                    FROM plugin_actions
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
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
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._plugin_invocation_log_where(
            action_id=action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
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

    def count_plugin_invocation_logs(
        self,
        *,
        action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._plugin_invocation_log_where(
            action_id=action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM plugin_invocation_logs {where}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_plugin_invocation_logs_page(
        self,
        *,
        action_id: str | None = None,
        limit: int,
        offset: int,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._plugin_invocation_log_where(
            action_id=action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )
        sort_column = PLUGIN_INVOCATION_LOG_SORT_COLUMNS.get(sort_by, "created_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
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
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [self._invocation_log_from_row(row) for row in cursor.fetchall()]

    def count_result_write_records(
        self,
        *,
        plugin_action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
        write_target: str | None = None,
    ) -> int:
        where, params = self._result_write_record_where(
            plugin_action_id=plugin_action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
            write_target=write_target,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    {self._result_write_records_cte()}
                    SELECT count(*) FROM result_write_records
                    {where}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_result_write_records_page(
        self,
        *,
        limit: int,
        offset: int,
        plugin_action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
        write_target: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._result_write_record_where(
            plugin_action_id=plugin_action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
            write_target=write_target,
        )
        sort_column = RESULT_WRITE_RECORD_SORT_COLUMNS.get(sort_by, "created_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    {self._result_write_records_cte()}
                    SELECT id, source_type, scheduled_job_id, scheduled_job_name,
                           scheduled_job_run_id, plugin_action_id,
                           plugin_invocation_log_id, plugin_id, plugin_code,
                           plugin_connection_id, write_target, write_target_label,
                           status, records_imported, feedback, preview,
                           summary_fields, created_at, updated_at
                    FROM result_write_records
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [self._result_write_record_from_row(row) for row in cursor.fetchall()]

    def list_ai_executor_runners(
        self,
        *,
        executor_type: str | None = None,
        keyword: str | None = None,
        protocol: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._ai_executor_runner_where(
            executor_type=executor_type,
            keyword=keyword,
            protocol=protocol,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, name, protocol, endpoint_url, executor_types, workspace_roots,
                           token_hash, heartbeat_timeout_seconds, max_concurrent_tasks, status,
                           last_heartbeat_at, metadata, created_by, created_at, updated_at,
                           token_rotated_at, token_version, capabilities
                    FROM ai_executor_runners
                    {where}
                    ORDER BY updated_at DESC, id ASC
                    """,
                    tuple(params),
                )
                return [self._ai_executor_runner_from_row(row) for row in cursor.fetchall()]

    def count_ai_executor_runners(
        self,
        *,
        executor_type: str | None = None,
        keyword: str | None = None,
        protocol: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._ai_executor_runner_where(
            executor_type=executor_type,
            keyword=keyword,
            protocol=protocol,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM ai_executor_runners {where}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_ai_executor_runners_page(
        self,
        *,
        executor_type: str | None = None,
        keyword: str | None = None,
        limit: int,
        offset: int,
        protocol: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._ai_executor_runner_where(
            executor_type=executor_type,
            keyword=keyword,
            protocol=protocol,
            status=status,
        )
        sort_column = AI_EXECUTOR_RUNNER_SORT_COLUMNS.get(sort_by, "updated_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, name, protocol, endpoint_url, executor_types, workspace_roots,
                           token_hash, heartbeat_timeout_seconds, max_concurrent_tasks, status,
                           last_heartbeat_at, metadata, created_by, created_at, updated_at,
                           token_rotated_at, token_version, capabilities
                    FROM ai_executor_runners
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [self._ai_executor_runner_from_row(row) for row in cursor.fetchall()]

    def save_ai_executor_runner_record(
        self,
        runner: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_executor_runners(cursor, {runner["id"]: runner})
                self._upsert_audit(cursor, audit_event)

    def delete_ai_executor_runner_record(
        self,
        runner_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM ai_executor_runners WHERE id = %s", (runner_id,))
                self._upsert_audit(cursor, audit_event)

    def list_ai_executor_tasks(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        runner_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._ai_executor_task_where(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, runner_id, plugin_invocation_log_id, scheduled_job_id,
                           scheduled_job_run_id, executor_type, instruction, workspace_root,
                           timeout_seconds, input_payload, request_config, result_json, logs,
                           status, error_code, error_message, claimed_at, finished_at,
                           created_by, created_at, updated_at, ai_task_id,
                           deployment_run_id
                    FROM ai_executor_tasks
                    {where}
                    ORDER BY created_at ASC, id ASC
                    """,
                    tuple(params),
                )
                return [self._ai_executor_task_from_row(row) for row in cursor.fetchall()]

    def count_ai_executor_tasks(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        runner_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._ai_executor_task_where(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM ai_executor_tasks {where}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_ai_executor_tasks_page(
        self,
        *,
        ai_task_id: str | None = None,
        limit: int,
        offset: int,
        product_scope_ids: list[str] | None = None,
        runner_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._ai_executor_task_where(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )
        sort_column = AI_EXECUTOR_TASK_SORT_COLUMNS.get(sort_by, "updated_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, runner_id, plugin_invocation_log_id, scheduled_job_id,
                           scheduled_job_run_id, executor_type, instruction, workspace_root,
                           timeout_seconds, input_payload, request_config, result_json, logs,
                           status, error_code, error_message, claimed_at, finished_at,
                           created_by, created_at, updated_at, ai_task_id,
                           deployment_run_id
                    FROM ai_executor_tasks
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [self._ai_executor_task_from_row(row) for row in cursor.fetchall()]

    def save_ai_executor_task_record(
        self,
        task: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_executor_tasks(cursor, {task["id"]: task})
                self._upsert_audit(cursor, audit_event)

    def list_ai_executor_approval_requests(
        self,
        *,
        action_id: str | None = None,
        runner_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where(
            {
                "action_id": action_id,
                "runner_id": runner_id,
                "status": status,
            },
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, action_id, connection_id, runner_id, scheduled_job_id,
                           scheduled_job_run_id, ai_task_id, executor_type, workspace_root,
                           risk_level, blocked_operations, approval_request, approval,
                           status, requested_by, requested_at, approved_by, approved_at,
                           expires_at, reason, created_at, updated_at
                    FROM ai_executor_approval_requests
                    {where}
                    ORDER BY updated_at DESC, id ASC
                    """,
                    tuple(params),
                )
                return [
                    self._ai_executor_approval_request_from_row(row)
                    for row in cursor.fetchall()
                ]

    def count_ai_executor_approval_requests(
        self,
        *,
        action_id: str | None = None,
        runner_id: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._where(
            {
                "action_id": action_id,
                "runner_id": runner_id,
                "status": status,
            },
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM ai_executor_approval_requests {where}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_ai_executor_approval_requests_page(
        self,
        *,
        action_id: str | None = None,
        limit: int,
        offset: int,
        runner_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where(
            {
                "action_id": action_id,
                "runner_id": runner_id,
                "status": status,
            },
        )
        sort_column = AI_EXECUTOR_APPROVAL_REQUEST_SORT_COLUMNS.get(sort_by, "updated_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, action_id, connection_id, runner_id, scheduled_job_id,
                           scheduled_job_run_id, ai_task_id, executor_type, workspace_root,
                           risk_level, blocked_operations, approval_request, approval,
                           status, requested_by, requested_at, approved_by, approved_at,
                           expires_at, reason, created_at, updated_at
                    FROM ai_executor_approval_requests
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [
                    self._ai_executor_approval_request_from_row(row)
                    for row in cursor.fetchall()
                ]

    def save_ai_executor_approval_request_record(
        self,
        approval_request: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_executor_approval_requests(
                    cursor,
                    {approval_request["id"]: approval_request},
                )
                self._upsert_audit(cursor, audit_event)

    def save_plugin_invocation_log_record(
        self,
        log: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_plugin_invocation_logs(cursor, {log["id"]: log})
                self._upsert_audit(cursor, audit_event)

    def upsert_plugins(self, cursor, plugins: dict[str, dict[str, Any]]) -> None:
        for plugin in plugins.values():
            cursor.execute(
                """
                INSERT INTO integration_plugins (
                  id, code, name, description, protocol, category, risk_level,
                  status, is_system, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, COALESCE(%s::timestamptz, now()),
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
                  is_system = EXCLUDED.is_system,
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
                    plugin.get("is_system", False),
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
                  updated_at, last_test_summary, test_history
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s::jsonb,
                  %s::jsonb, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s::jsonb, %s::jsonb
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
                  updated_at = EXCLUDED.updated_at,
                  last_test_summary = EXCLUDED.last_test_summary,
                  test_history = EXCLUDED.test_history
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
                    _json(connection.get("last_test_summary"), {}),
                    _json(connection.get("test_history"), []),
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
                    log.get("plugin_id"),
                    log.get("connection_id"),
                    log.get("action_id"),
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

    def upsert_ai_executor_runners(self, cursor, runners: dict[str, dict[str, Any]]) -> None:
        for runner in runners.values():
            cursor.execute(
                """
                INSERT INTO ai_executor_runners (
                  id, name, protocol, endpoint_url, executor_types, workspace_roots,
                  token_hash, heartbeat_timeout_seconds, max_concurrent_tasks, status,
                  last_heartbeat_at, metadata, created_by, created_at, updated_at,
                  token_rotated_at, token_version, capabilities
                )
                VALUES (
                  %s, %s, %s, %s, %s::jsonb, %s::jsonb,
                  %s, %s, %s, %s,
                  %s::timestamptz, %s::jsonb, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s::timestamptz, %s, %s::jsonb
                )
                ON CONFLICT (id) DO UPDATE SET
                  name = EXCLUDED.name,
                  protocol = EXCLUDED.protocol,
                  endpoint_url = EXCLUDED.endpoint_url,
                  executor_types = EXCLUDED.executor_types,
                  workspace_roots = EXCLUDED.workspace_roots,
                  token_hash = EXCLUDED.token_hash,
                  heartbeat_timeout_seconds = EXCLUDED.heartbeat_timeout_seconds,
                  max_concurrent_tasks = EXCLUDED.max_concurrent_tasks,
                  status = EXCLUDED.status,
                  last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                  metadata = EXCLUDED.metadata,
                  token_rotated_at = EXCLUDED.token_rotated_at,
                  token_version = EXCLUDED.token_version,
                  capabilities = EXCLUDED.capabilities,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    runner["id"],
                    runner["name"],
                    runner.get("protocol", "runner_polling"),
                    runner.get("endpoint_url", "runner://local"),
                    _json(runner.get("executor_types"), []),
                    _json(runner.get("workspace_roots"), []),
                    runner["token_hash"],
                    runner.get("heartbeat_timeout_seconds", 120),
                    runner.get("max_concurrent_tasks", 1),
                    runner.get("status", "active"),
                    runner.get("last_heartbeat_at"),
                    _json(runner.get("metadata"), {}),
                    runner.get("created_by"),
                    runner.get("created_at"),
                    runner.get("updated_at") or runner.get("created_at"),
                    runner.get("token_rotated_at"),
                    runner.get("token_version", 1),
                    _json(runner.get("capabilities"), []),
                ),
            )

    def upsert_ai_executor_tasks(self, cursor, tasks: dict[str, dict[str, Any]]) -> None:
        for task in tasks.values():
            cursor.execute(
                """
                INSERT INTO ai_executor_tasks (
                  id, runner_id, plugin_invocation_log_id, scheduled_job_id,
                  scheduled_job_run_id, executor_type, instruction, workspace_root,
                  timeout_seconds, input_payload, request_config, result_json, logs,
                  status, error_code, error_message, claimed_at, finished_at,
                  created_by, created_at, updated_at, ai_task_id, deployment_run_id
                )
                VALUES (
                  %s, %s, %s, %s,
                  %s, %s, %s, %s,
                  %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  runner_id = EXCLUDED.runner_id,
                  plugin_invocation_log_id = EXCLUDED.plugin_invocation_log_id,
                  scheduled_job_id = EXCLUDED.scheduled_job_id,
                  scheduled_job_run_id = EXCLUDED.scheduled_job_run_id,
                  ai_task_id = EXCLUDED.ai_task_id,
                  deployment_run_id = EXCLUDED.deployment_run_id,
                  executor_type = EXCLUDED.executor_type,
                  instruction = EXCLUDED.instruction,
                  workspace_root = EXCLUDED.workspace_root,
                  timeout_seconds = EXCLUDED.timeout_seconds,
                  input_payload = EXCLUDED.input_payload,
                  request_config = EXCLUDED.request_config,
                  result_json = EXCLUDED.result_json,
                  logs = EXCLUDED.logs,
                  status = EXCLUDED.status,
                  error_code = EXCLUDED.error_code,
                  error_message = EXCLUDED.error_message,
                  claimed_at = EXCLUDED.claimed_at,
                  finished_at = EXCLUDED.finished_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    task["id"],
                    task.get("runner_id"),
                    task.get("plugin_invocation_log_id"),
                    task.get("scheduled_job_id"),
                    task.get("scheduled_job_run_id"),
                    task["executor_type"],
                    task["instruction"],
                    task["workspace_root"],
                    task.get("timeout_seconds", 1800),
                    _json(task.get("input_payload"), {}),
                    _json(task.get("request_config"), {}),
                    _json(task.get("result_json"), {}),
                    _json(task.get("logs"), []),
                    task.get("status", "queued"),
                    task.get("error_code"),
                    task.get("error_message"),
                    task.get("claimed_at"),
                    task.get("finished_at"),
                    task.get("created_by"),
                    task.get("created_at"),
                    task.get("updated_at") or task.get("created_at"),
                    task.get("ai_task_id"),
                    task.get("deployment_run_id"),
                ),
            )

    def upsert_ai_executor_approval_requests(
        self,
        cursor,
        approval_requests: dict[str, dict[str, Any]],
    ) -> None:
        for approval_request in approval_requests.values():
            cursor.execute(
                """
                INSERT INTO ai_executor_approval_requests (
                  id, action_id, connection_id, runner_id, scheduled_job_id,
                  scheduled_job_run_id, ai_task_id, executor_type, workspace_root,
                  risk_level, blocked_operations, approval_request, approval,
                  status, requested_by, requested_at, approved_by, approved_at,
                  expires_at, reason, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s, %s, %s,
                  %s, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s, %s, %s::timestamptz, %s, %s::timestamptz,
                  %s::timestamptz, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  action_id = EXCLUDED.action_id,
                  connection_id = EXCLUDED.connection_id,
                  runner_id = EXCLUDED.runner_id,
                  scheduled_job_id = EXCLUDED.scheduled_job_id,
                  scheduled_job_run_id = EXCLUDED.scheduled_job_run_id,
                  ai_task_id = EXCLUDED.ai_task_id,
                  executor_type = EXCLUDED.executor_type,
                  workspace_root = EXCLUDED.workspace_root,
                  risk_level = EXCLUDED.risk_level,
                  blocked_operations = EXCLUDED.blocked_operations,
                  approval_request = EXCLUDED.approval_request,
                  approval = EXCLUDED.approval,
                  status = EXCLUDED.status,
                  requested_by = EXCLUDED.requested_by,
                  requested_at = EXCLUDED.requested_at,
                  approved_by = EXCLUDED.approved_by,
                  approved_at = EXCLUDED.approved_at,
                  expires_at = EXCLUDED.expires_at,
                  reason = EXCLUDED.reason,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    approval_request["id"],
                    approval_request.get("action_id"),
                    approval_request.get("connection_id"),
                    approval_request.get("runner_id"),
                    approval_request.get("scheduled_job_id"),
                    approval_request.get("scheduled_job_run_id"),
                    approval_request.get("ai_task_id"),
                    approval_request["executor_type"],
                    approval_request["workspace_root"],
                    approval_request.get("risk_level", "high"),
                    _json(approval_request.get("blocked_operations"), []),
                    _json(approval_request.get("approval_request"), {}),
                    _json(approval_request.get("approval"), {}),
                    approval_request.get("status", "pending"),
                    approval_request.get("requested_by"),
                    approval_request.get("requested_at"),
                    approval_request.get("approved_by"),
                    approval_request.get("approved_at"),
                    approval_request.get("expires_at"),
                    approval_request.get("reason"),
                    approval_request.get("created_at"),
                    approval_request.get("updated_at") or approval_request.get("created_at"),
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

    def _plugin_invocation_log_where(
        self,
        *,
        action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        where, params = self._where(
            {
                "action_id": action_id,
                "scheduled_job_id": scheduled_job_id,
                "scheduled_job_run_id": scheduled_job_run_id,
                "status": status,
            },
        )
        clauses = [where.removeprefix("WHERE ")] if where else []
        if product_scope_ids is not None:
            normalized_product_ids = [
                str(product_id)
                for product_id in product_scope_ids
                if str(product_id).strip()
            ]
            if not normalized_product_ids:
                clauses.append("FALSE")
            else:
                clauses.append(
                    """
                    (
                      EXISTS (
                        SELECT 1
                        FROM scheduled_jobs scoped_job
                        WHERE scoped_job.id = plugin_invocation_logs.scheduled_job_id
                          AND scoped_job.product_id = ANY(%s)
                      )
                      OR EXISTS (
                        SELECT 1
                        FROM scheduled_job_runs scoped_run
                        JOIN scheduled_jobs scoped_run_job
                          ON scoped_run_job.id = scoped_run.scheduled_job_id
                        WHERE scoped_run.id = plugin_invocation_logs.scheduled_job_run_id
                          AND scoped_run_job.product_id = ANY(%s)
                      )
                    )
                    """,
                )
                params.extend([normalized_product_ids, normalized_product_ids])
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _result_write_record_where(
        self,
        *,
        plugin_action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
        write_target: str | None = None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in (
            ("plugin_action_id", plugin_action_id),
            ("scheduled_job_id", scheduled_job_id),
            ("scheduled_job_run_id", scheduled_job_run_id),
            ("status", status),
            ("write_target", write_target),
        ):
            if value is not None:
                clauses.append(f"{field} = %s")
                params.append(value)
        if product_scope_ids is not None:
            normalized_product_ids = [
                str(product_id)
                for product_id in product_scope_ids
                if str(product_id).strip()
            ]
            if not normalized_product_ids:
                clauses.append("FALSE")
            else:
                clauses.append("product_id = ANY(%s)")
                params.append(normalized_product_ids)
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _result_write_records_cte(self) -> str:
        return """
        WITH scheduled_result_write_records AS (
          SELECT
            CASE
              WHEN action_node.ordinal <= 1 THEN CONCAT('result_write_record_', run.id)
              ELSE CONCAT('result_write_record_', run.id, '_', action_node.ordinal)
            END AS id,
            'scheduled_job_run'::text AS source_type,
            run.scheduled_job_id,
            job.name AS scheduled_job_name,
            run.id AS scheduled_job_run_id,
            COALESCE(
              NULLIF(result_action ->> 'action_id', ''),
              run.resolved_plugin_snapshot #>> '{action,id}'
            ) AS plugin_action_id,
            COALESCE(
              NULLIF(feedback ->> 'plugin_invocation_log_id', ''),
              run.plugin_invocation_log_id
            ) AS plugin_invocation_log_id,
            run.resolved_plugin_snapshot #>> '{plugin,id}' AS plugin_id,
            run.resolved_plugin_snapshot #>> '{plugin,code}' AS plugin_code,
            COALESCE(
              NULLIF(run.resolved_plugin_snapshot #>> '{connection,id}', ''),
              run.resolved_plugin_snapshot #>> '{action,connection_id}'
            ) AS plugin_connection_id,
            COALESCE(
              NULLIF(result_action ->> 'write_target', ''),
              NULLIF(feedback ->> 'write_target', ''),
              NULLIF(preview ->> 'write_target', ''),
              NULLIF(run.result_summary ->> 'write_target', ''),
              'scheduled_job_result'
            ) AS write_target,
            COALESCE(
              NULLIF(result_action ->> 'write_target_label', ''),
              NULLIF(preview ->> 'write_target_label', '')
            ) AS write_target_label,
            COALESCE(NULLIF(result_action ->> 'status', ''), run.status) AS status,
            CASE
              WHEN COALESCE(
                result_action ->> 'records_imported',
                feedback ->> 'records_imported',
                preview ->> 'records_imported',
                run.records_imported::text,
                '0'
              ) ~ '^-?[0-9]+$'
              THEN COALESCE(
                result_action ->> 'records_imported',
                feedback ->> 'records_imported',
                preview ->> 'records_imported',
                run.records_imported::text,
                '0'
              )::int
              ELSE 0
            END AS records_imported,
            feedback,
            preview,
            jsonb_strip_nulls(
              jsonb_build_object(
                'candidate_count',
                COALESCE(feedback -> 'candidate_count', preview -> 'candidate_count'),
                'delivery_id',
                COALESCE(feedback -> 'delivery_id', preview -> 'delivery_id'),
                'delivery_status',
                COALESCE(feedback -> 'delivery_status', preview -> 'delivery_status'),
                'preview_value',
                COALESCE(feedback -> 'preview_value', preview -> 'preview_value'),
                'report_preview',
                COALESCE(feedback -> 'report_preview', preview -> 'report_preview'),
                'sample_records',
                COALESCE(feedback -> 'sample_records', preview -> 'sample_records'),
                'source_row_count',
                COALESCE(feedback -> 'source_row_count', preview -> 'source_row_count'),
                'subject', COALESCE(feedback -> 'subject', preview -> 'subject')
              )
            ) AS summary_fields,
            COALESCE(run.finished_at, run.started_at, run.created_at) AS created_at,
            COALESCE(run.finished_at, run.updated_at, run.created_at) AS updated_at,
            job.product_id
          FROM scheduled_job_runs run
          LEFT JOIN scheduled_jobs job ON job.id = run.scheduled_job_id
          CROSS JOIN LATERAL (
            SELECT action_item.result_action, action_item.ordinal
            FROM (
              SELECT
                action_value.value AS result_action,
                action_value.ordinality::int AS ordinal
              FROM jsonb_array_elements(
                CASE
                  WHEN jsonb_typeof(
                    run.result_summary #> '{execution_nodes,result_actions}'
                  ) = 'array'
                  THEN run.result_summary #> '{execution_nodes,result_actions}'
                  ELSE '[]'::jsonb
                END
              ) WITH ORDINALITY AS action_value(value, ordinality)
              UNION ALL
              SELECT
                CASE
                  WHEN jsonb_typeof(
                    run.result_summary #> '{execution_nodes,result_action}'
                  ) = 'object'
                  THEN run.result_summary #> '{execution_nodes,result_action}'
                  ELSE '{}'::jsonb
                END AS result_action,
                1 AS ordinal
              WHERE jsonb_typeof(
                  run.result_summary #> '{execution_nodes,result_actions}'
                ) IS DISTINCT FROM 'array'
                OR jsonb_array_length(
                  CASE
                    WHEN jsonb_typeof(
                      run.result_summary #> '{execution_nodes,result_actions}'
                    ) = 'array'
                    THEN run.result_summary #> '{execution_nodes,result_actions}'
                    ELSE '[]'::jsonb
                  END
                ) = 0
            ) action_item
          ) action_node
          CROSS JOIN LATERAL (
            SELECT CASE
              WHEN jsonb_typeof(action_node.result_action -> 'feedback') = 'object'
              THEN action_node.result_action -> 'feedback'
              ELSE '{}'::jsonb
            END AS feedback
          ) feedback_node
          CROSS JOIN LATERAL (
            SELECT CASE
              WHEN jsonb_typeof(feedback_node.feedback -> 'write_preview') = 'object'
              THEN feedback_node.feedback -> 'write_preview'
              ELSE '{}'::jsonb
            END AS preview
          ) preview_node
          WHERE action_node.result_action <> '{}'::jsonb
        ),
        invocation_result_write_records AS (
          SELECT
            CONCAT('result_write_record_', log.id) AS id,
            'plugin_invocation_log'::text AS source_type,
            log.scheduled_job_id,
            job.name AS scheduled_job_name,
            NULL::text AS scheduled_job_run_id,
            log.action_id AS plugin_action_id,
            log.id AS plugin_invocation_log_id,
            log.plugin_id,
            plugin.code AS plugin_code,
            log.connection_id AS plugin_connection_id,
            COALESCE(
              NULLIF(action.result_mapping ->> 'write_target', ''),
              'scheduled_job_result'
            ) AS write_target,
            NULL::text AS write_target_label,
            log.status,
            0::int AS records_imported,
            jsonb_build_object(
              'plugin_invocation_log_id', log.id,
              'response_summary', COALESCE(log.response_summary, '{}'::jsonb),
              'write_preview', jsonb_build_object(
                'write_target',
                COALESCE(
                  NULLIF(action.result_mapping ->> 'write_target', ''),
                  'scheduled_job_result'
                )
              )
            ) AS feedback,
            jsonb_build_object(
              'write_target',
              COALESCE(NULLIF(action.result_mapping ->> 'write_target', ''), 'scheduled_job_result')
            ) AS preview,
            '{}'::jsonb AS summary_fields,
            log.created_at,
            COALESCE(log.updated_at, log.created_at) AS updated_at,
            job.product_id
          FROM plugin_invocation_logs log
          LEFT JOIN plugin_actions action ON action.id = log.action_id
          LEFT JOIN integration_plugins plugin ON plugin.id = log.plugin_id
          LEFT JOIN scheduled_jobs job ON job.id = log.scheduled_job_id
          WHERE log.scheduled_job_run_id IS NULL
        ),
        result_write_records AS (
          SELECT * FROM scheduled_result_write_records
          UNION ALL
          SELECT * FROM invocation_result_write_records
        )
        """

    def _ai_executor_runner_where(
        self,
        *,
        executor_type: str | None = None,
        keyword: str | None = None,
        protocol: str | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        where, params = self._where({"protocol": protocol, "status": status})
        clauses = [where.removeprefix("WHERE ")] if where else []
        normalized_keyword = str(keyword or "").strip().lower()
        if normalized_keyword:
            clauses.append(
                """
                (
                  lower(id) LIKE %s
                  OR lower(name) LIKE %s
                  OR lower(endpoint_url) LIKE %s
                  OR lower(protocol) LIKE %s
                )
                """,
            )
            pattern = f"%{normalized_keyword}%"
            params.extend([pattern, pattern, pattern, pattern])
        normalized_executor_type = str(executor_type or "").strip()
        if normalized_executor_type:
            clauses.append("executor_types ? %s")
            params.append(normalized_executor_type)
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _ai_executor_task_where(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        runner_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        where, params = self._where(
            {
                "ai_task_id": ai_task_id,
                "runner_id": runner_id,
                "scheduled_job_run_id": scheduled_job_run_id,
                "status": status,
            },
        )
        clauses = [where.removeprefix("WHERE ")] if where else []
        if product_scope_ids is not None:
            normalized_product_ids = [
                str(product_id)
                for product_id in product_scope_ids
                if str(product_id).strip()
            ]
            if not normalized_product_ids:
                clauses.append("FALSE")
            else:
                clauses.append(
                    """
                    (
                      EXISTS (
                        SELECT 1
                        FROM scheduled_jobs scoped_job
                        WHERE scoped_job.id = ai_executor_tasks.scheduled_job_id
                          AND scoped_job.product_id = ANY(%s)
                      )
                      OR EXISTS (
                        SELECT 1
                        FROM scheduled_job_runs scoped_run
                        JOIN scheduled_jobs scoped_run_job
                          ON scoped_run_job.id = scoped_run.scheduled_job_id
                        WHERE scoped_run.id = ai_executor_tasks.scheduled_job_run_id
                          AND scoped_run_job.product_id = ANY(%s)
                      )
                      OR EXISTS (
                        SELECT 1
                        FROM ai_tasks scoped_task
                        WHERE scoped_task.id = ai_executor_tasks.ai_task_id
                          AND scoped_task.product_id = ANY(%s)
                      )
                      OR EXISTS (
                        SELECT 1
                        FROM deployment_runs scoped_deployment_run
                        JOIN deployment_requests scoped_deployment
                          ON scoped_deployment.id = scoped_deployment_run.deployment_request_id
                        WHERE scoped_deployment_run.id = ai_executor_tasks.deployment_run_id
                          AND scoped_deployment.product_id = ANY(%s)
                      )
                    )
                    """,
                )
                params.extend(
                    [
                        normalized_product_ids,
                        normalized_product_ids,
                        normalized_product_ids,
                        normalized_product_ids,
                    ],
                )
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _plugin_connection_where(
        self,
        *,
        environment: str | None = None,
        keyword: str | None = None,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        clauses = []
        params: list[Any] = []
        filters = {
            "pc.environment": environment,
            "pc.plugin_id": plugin_id,
            "pc.status": status,
        }
        for column, value in filters.items():
            if value is not None:
                clauses.append(f"{column} = %s")
                params.append(value)
        normalized_keyword = str(keyword or "").strip().lower()
        if normalized_keyword:
            keyword_param = f"%{normalized_keyword}%"
            clauses.append(
                """
                (
                  lower(pc.id) LIKE %s
                  OR lower(pc.plugin_id) LIKE %s
                  OR lower(pc.name) LIKE %s
                  OR lower(pc.environment) LIKE %s
                  OR lower(pc.endpoint_url) LIKE %s
                  OR lower(pc.auth_type) LIKE %s
                  OR lower(pc.status) LIKE %s
                )
                """
            )
            params.extend([keyword_param] * 7)
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _plugin_action_where(
        self,
        *,
        keyword: str | None = None,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        where, params = self._where({"plugin_id": plugin_id, "status": status})
        clauses = [where.removeprefix("WHERE ")] if where else []
        normalized_keyword = str(keyword or "").strip().lower()
        if normalized_keyword:
            keyword_param = f"%{normalized_keyword}%"
            clauses.append(
                """
                (
                  lower(id) LIKE %s
                  OR lower(plugin_id) LIKE %s
                  OR lower(connection_id) LIKE %s
                  OR lower(code) LIKE %s
                  OR lower(name) LIKE %s
                  OR lower(description) LIKE %s
                  OR lower(action_type) LIKE %s
                  OR lower(status) LIKE %s
                )
                """
            )
            params.extend([keyword_param] * 8)
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
            "is_system": bool(row[8]),
            "created_by": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
            "updated_at": row[11].isoformat() if row[11] else None,
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
            "last_test_summary": row[14] or {},
            "test_history": row[15] or [],
            "plugin_name": row[16] if len(row) > 16 else None,
            "plugin_code": row[17] if len(row) > 17 else None,
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

    def _result_write_record_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "source_type": row[1],
            "scheduled_job_id": row[2],
            "scheduled_job_name": row[3],
            "scheduled_job_run_id": row[4],
            "plugin_action_id": row[5],
            "plugin_invocation_log_id": row[6],
            "plugin_id": row[7],
            "plugin_code": row[8],
            "plugin_connection_id": row[9],
            "write_target": row[10],
            "write_target_label": row[11],
            "status": row[12],
            "records_imported": row[13] or 0,
            "feedback": row[14] or {},
            "preview": row[15] or {},
            "summary_fields": row[16] or {},
            "created_at": row[17].isoformat() if row[17] else None,
            "updated_at": row[18].isoformat() if row[18] else None,
        }

    def _ai_executor_runner_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "name": row[1],
            "protocol": row[2],
            "endpoint_url": row[3],
            "executor_types": row[4] or [],
            "workspace_roots": row[5] or [],
            "token_hash": row[6],
            "heartbeat_timeout_seconds": row[7],
            "max_concurrent_tasks": row[8],
            "status": row[9],
            "last_heartbeat_at": row[10].isoformat() if row[10] else None,
            "metadata": row[11] or {},
            "created_by": row[12],
            "created_at": row[13].isoformat() if row[13] else None,
            "updated_at": row[14].isoformat() if row[14] else None,
            "token_rotated_at": row[15].isoformat() if len(row) > 15 and row[15] else None,
            "token_version": row[16] if len(row) > 16 and row[16] is not None else 1,
            "capabilities": row[17] or [] if len(row) > 17 else [],
        }

    def _ai_executor_task_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "runner_id": row[1],
            "plugin_invocation_log_id": row[2],
            "scheduled_job_id": row[3],
            "scheduled_job_run_id": row[4],
            "executor_type": row[5],
            "instruction": row[6],
            "workspace_root": row[7],
            "timeout_seconds": row[8],
            "input_payload": row[9] or {},
            "request_config": row[10] or {},
            "result_json": row[11] or {},
            "logs": row[12] or [],
            "status": row[13],
            "error_code": row[14],
            "error_message": row[15],
            "claimed_at": row[16].isoformat() if row[16] else None,
            "finished_at": row[17].isoformat() if row[17] else None,
            "created_by": row[18],
            "created_at": row[19].isoformat() if row[19] else None,
            "updated_at": row[20].isoformat() if row[20] else None,
            "ai_task_id": row[21] if len(row) > 21 else None,
            "deployment_run_id": row[22] if len(row) > 22 else None,
        }

    def _ai_executor_approval_request_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "action_id": row[1],
            "connection_id": row[2],
            "runner_id": row[3],
            "scheduled_job_id": row[4],
            "scheduled_job_run_id": row[5],
            "ai_task_id": row[6],
            "executor_type": row[7],
            "workspace_root": row[8],
            "risk_level": row[9],
            "blocked_operations": row[10] or [],
            "approval_request": row[11] or {},
            "approval": row[12] or {},
            "status": row[13],
            "requested_by": row[14],
            "requested_at": row[15].isoformat() if row[15] else None,
            "approved_by": row[16],
            "approved_at": row[17].isoformat() if row[17] else None,
            "expires_at": row[18].isoformat() if row[18] else None,
            "reason": row[19],
            "created_at": row[20].isoformat() if row[20] else None,
            "updated_at": row[21].isoformat() if row[21] else None,
        }
