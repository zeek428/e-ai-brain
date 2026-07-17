from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

MODEL_GATEWAY_CONFIG_SORT_EXPRESSIONS = {
    "base_url": "base_url",
    "default_chat_model": "default_chat_model",
    "default_embedding_model": "default_embedding_model",
    "embedding_connection_mode": "embedding_connection_mode",
    "id": "id",
    "is_default": "is_default",
    "name": "name",
    "provider": "provider",
    "status": "status",
}
MODEL_GATEWAY_LOG_SORT_EXPRESSIONS = {
    "ai_task_id": "ai_task_id",
    "created_at": "created_at",
    "id": "id",
    "latency_ms": "latency_ms",
    "model": "model",
    "provider": "provider",
    "purpose": "purpose",
    "status": "status",
}


class ModelGatewayReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        delete_missing_ids: Callable[[Any, str, list[str]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing
        self._delete_missing_ids = delete_missing_ids
        self._upsert_audit_events = upsert_audit_events

    def load_model_gateway(self) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                configs = self._load_model_gateway_configs(cursor)
                logs = self._load_model_gateway_logs(cursor)
        return {
            "model_gateway_configs": configs,
            "model_gateway_logs": logs,
        }

    def list_model_gateway_configs(self) -> list[dict[str, Any]]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                configs = self._load_model_gateway_configs(cursor)
        return [configs[config_id] for config_id in sorted(configs)]

    def count_model_gateway_configs(
        self,
        *,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
        embedding_connection_mode: str | None = None,
        is_default: bool | None = None,
        name: str | None = None,
        provider: str | None = None,
        status: str | None = None,
    ) -> int:
        where_clause, params = self._model_gateway_config_filter_sql(
            default_chat_model=default_chat_model,
            default_embedding_model=default_embedding_model,
            embedding_connection_mode=embedding_connection_mode,
            is_default=is_default,
            name=name,
            provider=provider,
            status=status,
        )
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT count(*)
                    FROM model_gateway_configs
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_model_gateway_configs_page(
        self,
        *,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
        embedding_connection_mode: str | None = None,
        is_default: bool | None = None,
        limit: int,
        name: str | None = None,
        offset: int,
        provider: str | None = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause, params = self._model_gateway_config_filter_sql(
            default_chat_model=default_chat_model,
            default_embedding_model=default_embedding_model,
            embedding_connection_mode=embedding_connection_mode,
            is_default=is_default,
            name=name,
            provider=provider,
            status=status,
        )
        sort_expression = MODEL_GATEWAY_CONFIG_SORT_EXPRESSIONS.get(sort_by, "name")
        direction = "ASC" if sort_order == "asc" else "DESC"
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, name, provider, base_url, api_key_ref, default_chat_model,
                           default_embedding_model, timeout_seconds, max_retries, status,
                           is_default, created_at, updated_at, embedding_connection_mode,
                           embedding_base_url, embedding_api_key_ref, embedding_dimension
                    FROM model_gateway_configs
                    {where_clause}
                    ORDER BY {sort_expression} {direction}, id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    (*params, limit, offset),
                )
                configs = self._model_gateway_configs_from_rows(cursor.fetchall())
        return [configs[config_id] for config_id in configs]

    def _model_gateway_config_filter_sql(
        self,
        *,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
        embedding_connection_mode: str | None = None,
        is_default: bool | None = None,
        name: str | None = None,
        provider: str | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if name:
            value = f"%{name.lower()}%"
            where_clauses.append(
                "(lower(id) LIKE %s OR lower(name) LIKE %s OR lower(base_url) LIKE %s)"
            )
            params.extend([value, value, value])
        if default_chat_model:
            where_clauses.append("lower(default_chat_model) LIKE %s")
            params.append(f"%{default_chat_model.lower()}%")
        if default_embedding_model:
            where_clauses.append("lower(COALESCE(default_embedding_model, '')) LIKE %s")
            params.append(f"%{default_embedding_model.lower()}%")
        if provider:
            where_clauses.append("provider = %s")
            params.append(provider)
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        if embedding_connection_mode:
            where_clauses.append("embedding_connection_mode = %s")
            params.append(embedding_connection_mode)
        if is_default is not None:
            where_clauses.append("is_default = %s")
            params.append(is_default)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_clause, params

    def get_model_gateway_config(self, config_id: str) -> dict[str, Any] | None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, provider, base_url, api_key_ref, default_chat_model,
                           default_embedding_model, timeout_seconds, max_retries, status,
                           is_default, created_at, updated_at, embedding_connection_mode,
                           embedding_base_url, embedding_api_key_ref, embedding_dimension
                    FROM model_gateway_configs
                    WHERE id = %s
                    """,
                    (config_id,),
                )
                configs = self._model_gateway_configs_from_rows(cursor.fetchall())
        return configs.get(config_id)

    def list_model_gateway_logs(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause, params = self._model_gateway_log_filter_sql(
            ai_task_id=ai_task_id,
            purpose=purpose,
            status=status,
        )
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, ai_task_id, provider, model, purpose, tokens, latency_ms,
                           status, error, model_gateway_config_id, created_at, updated_at,
                           executor_profile_id, product_id, requirement_revision,
                           strategy_snapshot_id, ai_executor_task_id,
                           requirement_assessment_execution_id
                    FROM model_gateway_logs
                    {where_clause}
                    ORDER BY created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return self._model_gateway_logs_from_rows(cursor.fetchall())

    def count_model_gateway_logs(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> int:
        where_clause, params = self._model_gateway_log_filter_sql(
            ai_task_id=ai_task_id,
            purpose=purpose,
            status=status,
        )
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT count(*)
                    FROM model_gateway_logs
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_model_gateway_logs_page(
        self,
        *,
        ai_task_id: str | None = None,
        limit: int,
        offset: int,
        purpose: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause, params = self._model_gateway_log_filter_sql(
            ai_task_id=ai_task_id,
            purpose=purpose,
            status=status,
        )
        sort_expression = MODEL_GATEWAY_LOG_SORT_EXPRESSIONS.get(sort_by, "created_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, ai_task_id, provider, model, purpose, tokens, latency_ms,
                           status, error, model_gateway_config_id, created_at, updated_at,
                           executor_profile_id, product_id, requirement_revision,
                           strategy_snapshot_id, ai_executor_task_id,
                           requirement_assessment_execution_id
                    FROM model_gateway_logs
                    {where_clause}
                    ORDER BY {sort_expression} {direction}, id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    (*params, limit, offset),
                )
                return self._model_gateway_logs_from_rows(cursor.fetchall())

    def _model_gateway_log_filter_sql(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if ai_task_id is not None:
            where_clauses.append("ai_task_id = %s")
            params.append(ai_task_id)
        if purpose is not None:
            where_clauses.append("purpose = %s")
            params.append(purpose)
        if status is not None:
            where_clauses.append("status = %s")
            params.append(status)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_clause, params

    def save_model_gateway(self, payload: dict[str, Any]) -> None:
        configs = payload.get("model_gateway_configs", {})
        logs = payload.get("model_gateway_logs", [])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing_model_gateway_rows(cursor, configs=configs, logs=logs)
                self._upsert_model_gateway_configs(cursor, configs)
                self.upsert_model_gateway_logs(cursor, logs)

    def save_model_gateway_records(
        self,
        payload: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        configs = payload.get("model_gateway_configs", {})
        logs = payload.get("model_gateway_logs", [])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing_model_gateway_rows(cursor, configs=configs, logs=logs)
                self._upsert_model_gateway_configs(cursor, configs)
                self.upsert_model_gateway_logs(cursor, logs)
                if audit_event is not None:
                    if self._upsert_audit_events is None:
                        raise RuntimeError("Audit upsert callback is not configured")
                    self._upsert_audit_events(cursor, [audit_event])

    def upsert_model_gateway_config_record(
        self,
        config: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._upsert_model_gateway_config(cursor, config, reset_other_defaults=True)
                if audit_event is not None:
                    if self._upsert_audit_events is None:
                        raise RuntimeError("Audit upsert callback is not configured")
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_model_gateway_config_record(
        self,
        config_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM model_gateway_configs WHERE id = %s", (config_id,))
                if audit_event is not None:
                    if self._upsert_audit_events is None:
                        raise RuntimeError("Audit upsert callback is not configured")
                    self._upsert_audit_events(cursor, [audit_event])

    def _load_model_gateway_configs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
                    SELECT id, name, provider, base_url, api_key_ref, default_chat_model,
                           default_embedding_model, timeout_seconds, max_retries, status,
                           is_default, created_at, updated_at, embedding_connection_mode,
                           embedding_base_url, embedding_api_key_ref, embedding_dimension
                    FROM model_gateway_configs
                    ORDER BY id
            """
        )
        return self._model_gateway_configs_from_rows(cursor.fetchall())

    def _model_gateway_configs_from_rows(self, rows: list[Any]) -> dict[str, dict[str, Any]]:
        configs = {}
        for row in rows:
            config = {
                "api_key": row[4],
                "base_url": row[3],
                "created_at": row[11].isoformat() if row[11] else None,
                "default_chat_model": row[5],
                "default_embedding_model": row[6],
                "embedding_api_key": row[15],
                "embedding_base_url": row[14],
                "embedding_connection_mode": row[13],
                "embedding_dimension": row[16],
                "id": row[0],
                "is_default": row[10],
                "max_retries": row[8],
                "name": row[1],
                "provider": row[2],
                "status": row[9],
                "timeout_seconds": row[7],
                "updated_at": row[12].isoformat() if row[12] else None,
            }
            for optional_key in (
                "api_key",
                "created_at",
                "default_embedding_model",
                "embedding_api_key",
                "embedding_base_url",
                "embedding_connection_mode",
                "embedding_dimension",
                "updated_at",
            ):
                if config[optional_key] is None:
                    config.pop(optional_key)
            configs[row[0]] = config
        return configs

    def _load_model_gateway_logs(self, cursor) -> list[dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, provider, model, purpose, tokens, latency_ms,
                   status, error, model_gateway_config_id, created_at, updated_at,
                   executor_profile_id, product_id, requirement_revision, strategy_snapshot_id,
                   ai_executor_task_id, requirement_assessment_execution_id
            FROM model_gateway_logs
            ORDER BY created_at, id
            """
        )
        return self._model_gateway_logs_from_rows(cursor.fetchall())

    def _model_gateway_logs_from_rows(self, rows: list[Any]) -> list[dict[str, Any]]:
        logs = []
        for row in rows:
            log = {
                "ai_task_id": row[1],
                "created_at": row[10].isoformat() if row[10] else None,
                "error": row[8],
                "id": row[0],
                "latency_ms": row[6],
                "model": row[3],
                "model_gateway_config_id": row[9],
                "provider": row[2],
                "purpose": row[4],
                "status": row[7],
                "tokens": dict(row[5] or {}),
                "updated_at": row[11].isoformat() if row[11] else None,
                "executor_profile_id": row[12],
                "product_id": row[13],
                "requirement_revision": row[14],
                "strategy_snapshot_id": row[15],
                "ai_executor_task_id": row[16],
                "requirement_assessment_execution_id": row[17],
            }
            for optional_key in (
                "ai_task_id",
                "created_at",
                "error",
                "model_gateway_config_id",
                "executor_profile_id",
                "product_id",
                "requirement_revision",
                "strategy_snapshot_id",
                "ai_executor_task_id",
                "requirement_assessment_execution_id",
                "updated_at",
            ):
                if log[optional_key] is None:
                    log.pop(optional_key)
            logs.append(log)
        return logs

    def _delete_missing_model_gateway_rows(
        self,
        cursor,
        *,
        configs: dict[str, dict[str, Any]],
        logs: list[dict[str, Any]],
    ) -> None:
        if self._delete_missing_ids is None or self._delete_missing is None:
            raise RuntimeError("Model gateway delete callbacks are not configured")
        self._delete_missing_ids(
            cursor,
            "model_gateway_logs",
            [str(log["id"]) for log in logs if log.get("id")],
        )
        self._delete_missing(cursor, "model_gateway_configs", configs)

    def _upsert_model_gateway_configs(
        self,
        cursor,
        configs: dict[str, dict[str, Any]],
    ) -> None:
        cursor.execute("UPDATE model_gateway_configs SET is_default = false")
        for config in configs.values():
            self._upsert_model_gateway_config(cursor, config)

    def _upsert_model_gateway_config(
        self,
        cursor,
        config: dict[str, Any],
        *,
        reset_other_defaults: bool = False,
    ) -> None:
        if reset_other_defaults and config.get("is_default"):
            cursor.execute(
                "UPDATE model_gateway_configs SET is_default = false WHERE id <> %s",
                (config["id"],),
            )
        created_at = config.get("created_at")
        updated_at = config.get("updated_at") or created_at
        cursor.execute(
            """
            INSERT INTO model_gateway_configs (
              id, name, provider, base_url, api_key_ref, default_chat_model,
              default_embedding_model, embedding_connection_mode, embedding_base_url,
              embedding_api_key_ref, embedding_dimension, timeout_seconds, max_retries, status,
              is_default, created_at, updated_at
            )
            VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              COALESCE(%s::timestamptz, now()),
              COALESCE(%s::timestamptz, now())
            )
            ON CONFLICT (id) DO UPDATE SET
              name = EXCLUDED.name,
              provider = EXCLUDED.provider,
              base_url = EXCLUDED.base_url,
              api_key_ref = EXCLUDED.api_key_ref,
              default_chat_model = EXCLUDED.default_chat_model,
              default_embedding_model = EXCLUDED.default_embedding_model,
              embedding_connection_mode = EXCLUDED.embedding_connection_mode,
              embedding_base_url = EXCLUDED.embedding_base_url,
              embedding_api_key_ref = EXCLUDED.embedding_api_key_ref,
              embedding_dimension = EXCLUDED.embedding_dimension,
              timeout_seconds = EXCLUDED.timeout_seconds,
              max_retries = EXCLUDED.max_retries,
              status = EXCLUDED.status,
              is_default = EXCLUDED.is_default,
              updated_at = EXCLUDED.updated_at
            """,
            (
                config["id"],
                config["name"],
                config.get("provider", "openai_compatible"),
                config["base_url"],
                config.get("api_key"),
                config["default_chat_model"],
                config.get("default_embedding_model"),
                config.get("embedding_connection_mode", "reuse_chat"),
                config.get("embedding_base_url"),
                config.get("embedding_api_key"),
                config.get("embedding_dimension"),
                config.get("timeout_seconds", 60),
                config.get("max_retries", 1),
                config.get("status", "active"),
                config.get("is_default", False),
                created_at,
                updated_at,
            ),
        )

    def upsert_model_gateway_logs(self, cursor, logs: list[dict[str, Any]]) -> None:
        for log in logs:
            created_at = log.get("created_at")
            updated_at = log.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO model_gateway_logs (
                  id, ai_task_id, provider, model, purpose, tokens, latency_ms,
                  status, error, model_gateway_config_id, executor_profile_id,
                  product_id, requirement_revision, strategy_snapshot_id, ai_executor_task_id,
                  requirement_assessment_execution_id, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  provider = EXCLUDED.provider,
                  model = EXCLUDED.model,
                  purpose = EXCLUDED.purpose,
                  tokens = EXCLUDED.tokens,
                  latency_ms = EXCLUDED.latency_ms,
                  status = EXCLUDED.status,
                  error = EXCLUDED.error,
                  model_gateway_config_id = EXCLUDED.model_gateway_config_id,
                  executor_profile_id = EXCLUDED.executor_profile_id,
                  product_id = EXCLUDED.product_id,
                  requirement_revision = EXCLUDED.requirement_revision,
                  strategy_snapshot_id = EXCLUDED.strategy_snapshot_id,
                  ai_executor_task_id = EXCLUDED.ai_executor_task_id,
                  requirement_assessment_execution_id =
                    EXCLUDED.requirement_assessment_execution_id,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    log["id"],
                    log.get("ai_task_id"),
                    log["provider"],
                    log["model"],
                    log["purpose"],
                    json.dumps(log.get("tokens", {}), ensure_ascii=False),
                    log.get("latency_ms", 0),
                    log["status"],
                    log.get("error"),
                    log.get("model_gateway_config_id"),
                    log.get("executor_profile_id"),
                    log.get("product_id"),
                    log.get("requirement_revision"),
                    log.get("strategy_snapshot_id"),
                    log.get("ai_executor_task_id"),
                    log.get("requirement_assessment_execution_id"),
                    created_at,
                    updated_at,
                ),
            )
