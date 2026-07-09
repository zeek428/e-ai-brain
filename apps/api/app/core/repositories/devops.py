from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.devops_writes import DevopsWriteRepository


class DevopsReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._write_repository = DevopsWriteRepository(
            connect,
            delete_missing=delete_missing,
            upsert_audit_events=upsert_audit_events,
        )

    def save_gitlab_daily_code_metrics(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_gitlab_daily_code_metrics(payload)

    def save_gitlab_daily_code_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.save_gitlab_daily_code_metric_record(
            record,
            audit_event=audit_event,
        )

    def save_jenkins_release_records(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_jenkins_release_records(payload)

    def save_jenkins_release_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.save_jenkins_release_record(record, audit_event=audit_event)

    def save_deployment_request_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self._write_repository.save_deployment_request_record(
            record,
            audit_events=audit_events,
        )

    def save_deployment_run_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self._write_repository.save_deployment_run_record(record, audit_events=audit_events)

    def save_online_log_metrics(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_online_log_metrics(payload)

    def save_online_log_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.save_online_log_metric_record(record, audit_event=audit_event)

    def upsert_gitlab_daily_code_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_gitlab_daily_code_metrics(cursor, metrics)

    def upsert_jenkins_release_records(
        self,
        cursor,
        releases: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_jenkins_release_records(cursor, releases)

    def upsert_deployment_requests(
        self,
        cursor,
        deployment_requests: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_deployment_requests(cursor, deployment_requests)

    def upsert_deployment_runs(
        self,
        cursor,
        deployment_runs: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_deployment_runs(cursor, deployment_runs)

    def upsert_online_log_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_online_log_metrics(cursor, metrics)

    def load_gitlab_daily_code_metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                metrics = self._load_gitlab_daily_code_metrics(cursor)
        return {"gitlab_daily_code_metrics": metrics}

    def list_gitlab_daily_code_metrics(
        self,
        *,
        product_id: str | None = None,
        repository_id: str | None = None,
        metric_date: Any | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("product_id = %s")
            params.append(product_id)
        if repository_id is not None:
            where_clauses.append("repository_id = %s")
            params.append(repository_id)
        if metric_date is not None:
            where_clauses.append("metric_date = %s")
            params.append(metric_date)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, repository_id, metric_date, commit_count,
                           active_author_count, merge_request_count, changed_files,
                           additions, deletions, quality_score, risk_count,
                           author_metrics, status, source_channel, collected_at,
                           created_by, created_at, updated_at
                    FROM gitlab_daily_code_metrics
                    {where_clause}
                    ORDER BY metric_date DESC,
                             COALESCE(updated_at, created_at) DESC,
                             id DESC
                    """,
                    tuple(params),
                )
                return [self._gitlab_metric_from_row(row) for row in cursor.fetchall()]

    def load_jenkins_release_records(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                releases = self._load_jenkins_release_records(cursor)
        return {"jenkins_release_records": releases}

    def load_deployment_requests(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                deployment_requests = self._load_deployment_requests(cursor)
                deployment_runs = self._load_deployment_runs(cursor)
        return {
            "deployment_requests": deployment_requests,
            "deployment_runs": deployment_runs,
        }

    def list_deployment_requests(
        self,
        *,
        environment: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        version_id: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("d.product_id = %s")
            params.append(product_id)
        if version_id is not None:
            where_clauses.append("d.version_id = %s")
            params.append(version_id)
        if status is not None:
            where_clauses.append("d.status = %s")
            params.append(status)
        if environment is not None:
            where_clauses.append("d.environment = %s")
            params.append(environment)
        if product_scope_ids is not None:
            if not product_scope_ids:
                return []
            where_clauses.append("d.product_id = ANY(%s)")
            params.append(product_scope_ids)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT d.id, d.product_id, d.version_id, d.title, d.environment,
                           d.status, d.deploy_window_start, d.deploy_window_end,
                           d.release_branch, d.commit_sha, d.artifact_version,
                           d.release_readiness_task_id, d.rollback_plan, d.risk_level,
                           d.gate_summary, d.assigned_ops_user, d.approved_by,
                           d.started_at, d.finished_at, d.failure_reason, d.created_by,
                           d.created_at, d.updated_at,
                           COALESCE(
                             array_agg(r.requirement_id ORDER BY r.requirement_id)
                               FILTER (WHERE r.requirement_id IS NOT NULL),
                             ARRAY[]::text[]
                           ) AS requirement_ids
                    FROM deployment_requests d
                    LEFT JOIN deployment_request_requirements r
                      ON r.deployment_request_id = d.id
                    {where_clause}
                    GROUP BY d.id
                    ORDER BY COALESCE(d.updated_at, d.created_at) DESC, d.id DESC
                    """,
                    tuple(params),
                )
                return [self._deployment_request_from_row(row) for row in cursor.fetchall()]

    def list_deployment_runs(
        self,
        *,
        deployment_request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause = ""
        params: list[Any] = []
        if deployment_request_id is not None:
            where_clause = "WHERE deployment_request_id = %s"
            params.append(deployment_request_id)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, deployment_request_id, executor_type, external_job_name,
                           external_build_id, status, log_url, started_at, finished_at,
                           failure_reason, created_by, created_at, updated_at
                    FROM deployment_runs
                    {where_clause}
                    ORDER BY COALESCE(started_at, created_at) DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._deployment_run_from_row(row) for row in cursor.fetchall()]

    def list_jenkins_release_records(
        self,
        *,
        product_id: str | None = None,
        version_id: str | None = None,
        status: str | None = None,
        environment: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("product_id = %s")
            params.append(product_id)
        if version_id is not None:
            where_clauses.append("version_id = %s")
            params.append(version_id)
        if status is not None:
            where_clauses.append("status = %s")
            params.append(status)
        if environment is not None:
            where_clauses.append("environment = %s")
            params.append(environment)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                SELECT id, product_id, version_id, job_name, build_id, build_number,
                       environment, status, trigger_actor, commit_sha, duration_seconds,
                       started_at, deployed_at, failure_reason, source_channel,
                       deployment_request_id, created_by, created_at, updated_at
                FROM jenkins_release_records
                {where_clause}
                    ORDER BY COALESCE(deployed_at, created_at) DESC,
                             COALESCE(updated_at, created_at) DESC,
                             id DESC
                    """,
                    tuple(params),
                )
                return [self._jenkins_release_from_row(row) for row in cursor.fetchall()]

    def load_online_log_metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                metrics = self._load_online_log_metrics(cursor)
        return {"online_log_metrics": metrics}

    def list_online_log_metrics(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        environment: str | None = None,
        from_value: Any | None = None,
        to_value: Any | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("product_id = %s")
            params.append(product_id)
        if module_code is not None:
            where_clauses.append("module_code = %s")
            params.append(module_code)
        if environment is not None:
            where_clauses.append("environment = %s")
            params.append(environment)
        if from_value is not None:
            where_clauses.append("window_end >= %s")
            params.append(from_value)
        if to_value is not None:
            where_clauses.append("window_start <= %s")
            params.append(to_value)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, module_code, environment, window_start, window_end,
                           request_count, error_count, error_rate, p95_latency_ms,
                           p99_latency_ms, core_event_count, top_errors, anomaly_summary,
                           status, source_channel, created_by, created_at, updated_at
                    FROM online_log_metrics
                    {where_clause}
                    ORDER BY window_start DESC,
                             COALESCE(updated_at, created_at) DESC,
                             id DESC
                    """,
                    tuple(params),
                )
                return [self._online_log_metric_from_row(row) for row in cursor.fetchall()]

    def list_operational_metric_items(
        self,
        *,
        category: str | None = None,
        name: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        sort_expressions = {
            "category": "LOWER(category)",
            "id": "LOWER(id)",
            "name": "LOWER(name)",
            "status": "LOWER(status)",
            "updated_at": "updated_at",
            "value": "LOWER(value)",
        }
        sort_expression = sort_expressions[sort_by]
        sort_direction = "ASC" if sort_order == "asc" else "DESC"
        base_query = """
            WITH operational_rows AS (
                SELECT 'GitLab 指标'::text AS category,
                       id,
                       repository_id AS name,
                       status,
                       COALESCE(
                           updated_at,
                           created_at,
                           collected_at,
                           metric_date::timestamptz
                       ) AS updated_at,
                       commit_count::text AS value,
                       product_id,
                       NULL::text AS version_id,
                       NULL::text AS module_code,
                       repository_id,
                       NULL::text AS environment,
                       jsonb_strip_nulls(
                           jsonb_build_object(
                               'active_author_count', active_author_count,
                               'additions', additions,
                               'changed_files', changed_files,
                               'collected_at', collected_at,
                               'commit_count', commit_count,
                               'created_at', created_at,
                               'created_by', created_by,
                               'deletions', deletions,
                               'merge_request_count', merge_request_count,
                               'metric_date', metric_date,
                               'product_id', product_id,
                               'quality_score', quality_score,
                               'repository_id', repository_id,
                               'risk_count', risk_count,
                               'source_channel', source_channel,
                               'status', status,
                               'updated_at', updated_at
                           )
                       )::text AS source_payload
                FROM gitlab_daily_code_metrics
                UNION ALL
                SELECT 'Jenkins 发布'::text AS category,
                       id,
                       job_name AS name,
                       status,
                       COALESCE(updated_at, created_at, deployed_at, started_at) AS updated_at,
                       build_id AS value,
                       product_id,
                       version_id,
                       NULL::text AS module_code,
                       NULL::text AS repository_id,
                       environment,
                       jsonb_strip_nulls(
                           jsonb_build_object(
                               'build_id', build_id,
                               'build_number', build_number,
                               'commit_sha', commit_sha,
                               'created_at', created_at,
                               'created_by', created_by,
                               'deployed_at', deployed_at,
                               'duration_seconds', duration_seconds,
                               'environment', environment,
                               'failure_reason', failure_reason,
                               'job_name', job_name,
                               'product_id', product_id,
                               'source_channel', source_channel,
                               'started_at', started_at,
                               'status', status,
                               'trigger_actor', trigger_actor,
                               'updated_at', updated_at,
                               'version_id', version_id
                           )
                       )::text AS source_payload
	                FROM jenkins_release_records
	                UNION ALL
	                SELECT '运维部署'::text AS category,
	                       d.id,
	                       d.title AS name,
	                       d.status,
	                       COALESCE(d.updated_at, d.created_at, d.finished_at, d.started_at) AS updated_at,
	                       COALESCE(d.artifact_version, d.environment) AS value,
	                       d.product_id,
	                       d.version_id,
	                       NULL::text AS module_code,
	                       NULL::text AS repository_id,
	                       d.environment,
	                       jsonb_strip_nulls(
	                           jsonb_build_object(
	                               'approved_by', d.approved_by,
	                               'artifact_version', d.artifact_version,
	                               'assigned_ops_user', d.assigned_ops_user,
	                               'commit_sha', d.commit_sha,
	                               'created_at', d.created_at,
	                               'created_by', d.created_by,
	                               'deploy_window_end', d.deploy_window_end,
	                               'deploy_window_start', d.deploy_window_start,
	                               'environment', d.environment,
	                               'failure_reason', d.failure_reason,
	                               'finished_at', d.finished_at,
	                               'gate_summary', d.gate_summary,
	                               'product_id', d.product_id,
	                               'release_branch', d.release_branch,
	                               'release_readiness_task_id', d.release_readiness_task_id,
	                               'requirement_ids',
	                               COALESCE(
	                                   jsonb_agg(r.requirement_id ORDER BY r.requirement_id)
	                                       FILTER (WHERE r.requirement_id IS NOT NULL),
	                                   '[]'::jsonb
	                               ),
	                               'risk_level', d.risk_level,
	                               'rollback_plan', d.rollback_plan,
	                               'started_at', d.started_at,
	                               'status', d.status,
	                               'title', d.title,
	                               'updated_at', d.updated_at,
	                               'version_id', d.version_id
	                           )
	                       )::text AS source_payload
	                FROM deployment_requests d
	                LEFT JOIN deployment_request_requirements r
	                  ON r.deployment_request_id = d.id
	                GROUP BY d.id
	                UNION ALL
	                SELECT '线上日志'::text AS category,
	                       id,
	                       environment AS name,
                       status,
                       COALESCE(updated_at, created_at, window_start) AS updated_at,
                       error_rate::text AS value,
                       product_id,
                       NULL::text AS version_id,
                       module_code,
                       NULL::text AS repository_id,
                       environment,
                       jsonb_strip_nulls(
                           jsonb_build_object(
                               'anomaly_summary', anomaly_summary,
                               'core_event_count', core_event_count,
                               'created_at', created_at,
                               'created_by', created_by,
                               'environment', environment,
                               'error_count', error_count,
                               'error_rate', error_rate,
                               'module_code', module_code,
                               'p95_latency_ms', p95_latency_ms,
                               'p99_latency_ms', p99_latency_ms,
                               'product_id', product_id,
                               'request_count', request_count,
                               'source_channel', source_channel,
                               'status', status,
                               'updated_at', updated_at,
                               'window_end', window_end,
                               'window_start', window_start
                           )
                       )::text AS source_payload
                FROM online_log_metrics
            )
        """
        where_clauses: list[str] = []
        params: list[Any] = []
        if category is not None:
            where_clauses.append("category = %s")
            params.append(category)
        if status is not None:
            where_clauses.append("status = %s")
            params.append(status)
        if name is not None and name.strip():
            where_clauses.append(
                """
                CONCAT_WS(
                    ' ',
                    name,
                    id,
                    product_id,
                    version_id,
                    module_code,
                    repository_id,
                    environment
                ) ILIKE %s
                """
            )
            params.append(f"%{name.strip()}%")
        if product_scope_ids is not None:
            if not product_scope_ids:
                payload: dict[str, Any] = {"items": [], "total": 0}
                if page is not None or page_size is not None:
                    payload["page"] = page or 1
                    payload["page_size"] = page_size or 10
                return payload
            where_clauses.append("product_id = ANY(%s)")
            params.append(product_scope_ids)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        use_pagination = page is not None or page_size is not None
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        limit_clause = ""
        query_params = list(params)
        if use_pagination:
            limit_clause = "LIMIT %s OFFSET %s"
            query_params.extend([resolved_page_size, (resolved_page - 1) * resolved_page_size])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    {base_query}
                    SELECT COUNT(*)
                    FROM operational_rows
                    {where_clause}
                    """,
                    tuple(params),
                )
                total = int(cursor.fetchone()[0])
                cursor.execute(
                    f"""
                    {base_query}
                    SELECT category, id, name, status, updated_at, value,
                           product_id, version_id, module_code, repository_id,
                           environment, source_payload
                    FROM operational_rows
                    {where_clause}
                    ORDER BY {sort_expression} {sort_direction}, id {sort_direction}
                    {limit_clause}
                    """,
                    tuple(query_params),
                )
                items = []
                for row in cursor.fetchall():
                    source_payload = json.loads(row[11] or "{}")
                    item = {
                        key: value for key, value in source_payload.items() if value is not None
                    }
                    item.update(
                        {
                            "category": row[0],
                            "environment": row[10],
                            "id": row[1],
                            "module_code": row[8],
                            "name": row[2],
                            "product_id": row[6],
                            "repository_id": row[9],
                            "status": row[3],
                            "updated_at": row[4].isoformat() if row[4] else "",
                            "value": row[5],
                            "version_id": row[7],
                        }
                    )
                    items.append({key: value for key, value in item.items() if value is not None})
        payload: dict[str, Any] = {"items": items, "total": total}
        if use_pagination:
            payload["page"] = resolved_page
            payload["page_size"] = resolved_page_size
        return payload

    def _load_gitlab_daily_code_metrics(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, repository_id, metric_date, commit_count,
                   active_author_count, merge_request_count, changed_files,
                   additions, deletions, quality_score, risk_count,
                   author_metrics, status, source_channel, collected_at,
                   created_by, created_at, updated_at
            FROM gitlab_daily_code_metrics
            ORDER BY metric_date, id
            """
        )
        return {row[0]: self._gitlab_metric_from_row(row) for row in cursor.fetchall()}

    def _load_jenkins_release_records(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, version_id, job_name, build_id, build_number,
                   environment, status, trigger_actor, commit_sha, duration_seconds,
                   started_at, deployed_at, failure_reason, source_channel,
                   deployment_request_id, created_by, created_at, updated_at
            FROM jenkins_release_records
            ORDER BY COALESCE(deployed_at, created_at), id
            """
        )
        return {row[0]: self._jenkins_release_from_row(row) for row in cursor.fetchall()}

    def _load_deployment_requests(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT d.id, d.product_id, d.version_id, d.title, d.environment,
                   d.status, d.deploy_window_start, d.deploy_window_end,
                   d.release_branch, d.commit_sha, d.artifact_version,
                   d.release_readiness_task_id, d.rollback_plan, d.risk_level,
                   d.gate_summary, d.assigned_ops_user, d.approved_by,
                   d.started_at, d.finished_at, d.failure_reason, d.created_by,
                   d.created_at, d.updated_at,
                   COALESCE(
                     array_agg(r.requirement_id ORDER BY r.requirement_id)
                       FILTER (WHERE r.requirement_id IS NOT NULL),
                     ARRAY[]::text[]
                   ) AS requirement_ids
            FROM deployment_requests d
            LEFT JOIN deployment_request_requirements r
              ON r.deployment_request_id = d.id
            GROUP BY d.id
            ORDER BY COALESCE(d.updated_at, d.created_at), d.id
            """
        )
        return {row[0]: self._deployment_request_from_row(row) for row in cursor.fetchall()}

    def _load_deployment_runs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, deployment_request_id, executor_type, external_job_name,
                   external_build_id, status, log_url, started_at, finished_at,
                   failure_reason, created_by, created_at, updated_at
            FROM deployment_runs
            ORDER BY COALESCE(started_at, created_at), id
            """
        )
        return {row[0]: self._deployment_run_from_row(row) for row in cursor.fetchall()}

    def _load_online_log_metrics(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, module_code, environment, window_start, window_end,
                   request_count, error_count, error_rate, p95_latency_ms,
                   p99_latency_ms, core_event_count, top_errors, anomaly_summary,
                   status, source_channel, created_by, created_at, updated_at
            FROM online_log_metrics
            ORDER BY window_start, id
            """
        )
        return {row[0]: self._online_log_metric_from_row(row) for row in cursor.fetchall()}

    def _gitlab_metric_from_row(self, row) -> dict[str, Any]:
        author_metrics = row[12] or []
        if isinstance(author_metrics, str):
            author_metrics = json.loads(author_metrics)
        metric = {
            "active_author_count": row[5],
            "additions": row[8],
            "author_metrics": author_metrics,
            "changed_files": row[7],
            "collected_at": row[15].isoformat() if row[15] else None,
            "commit_count": row[4],
            "created_at": row[17].isoformat() if row[17] else None,
            "created_by": row[16],
            "deletions": row[9],
            "id": row[0],
            "merge_request_count": row[6],
            "metric_date": row[3].isoformat() if row[3] else None,
            "product_id": row[1],
            "quality_score": float(row[10]) if row[10] is not None else None,
            "repository_id": row[2],
            "risk_count": row[11],
            "source_channel": row[14],
            "status": row[13],
            "updated_at": row[18].isoformat() if row[18] else None,
        }
        for optional_key in (
            "collected_at",
            "created_at",
            "quality_score",
            "source_channel",
            "updated_at",
        ):
            if metric[optional_key] is None:
                metric.pop(optional_key)
        return metric

    def _jenkins_release_from_row(self, row) -> dict[str, Any]:
        release = {
            "build_id": row[4],
            "build_number": row[5],
            "commit_sha": row[9],
            "created_at": row[17].isoformat() if row[17] else None,
            "created_by": row[16],
            "deployed_at": row[12].isoformat() if row[12] else None,
            "deployment_request_id": row[15],
            "duration_seconds": row[10],
            "environment": row[6],
            "failure_reason": row[13],
            "id": row[0],
            "job_name": row[3],
            "product_id": row[1],
            "source_channel": row[14],
            "started_at": row[11].isoformat() if row[11] else None,
            "status": row[7],
            "trigger_actor": row[8],
            "updated_at": row[18].isoformat() if row[18] else None,
            "version_id": row[2],
        }
        for optional_key in (
            "build_number",
            "commit_sha",
            "created_at",
            "deployed_at",
            "deployment_request_id",
            "duration_seconds",
            "failure_reason",
            "source_channel",
            "started_at",
            "trigger_actor",
            "updated_at",
        ):
            if release[optional_key] is None:
                release.pop(optional_key)
        return release

    def _deployment_request_from_row(self, row) -> dict[str, Any]:
        gate_summary = row[14] or {}
        if isinstance(gate_summary, str):
            gate_summary = json.loads(gate_summary)
        request = {
            "approved_by": row[16],
            "artifact_version": row[10],
            "assigned_ops_user": row[15],
            "commit_sha": row[9],
            "created_at": row[21].isoformat() if row[21] else None,
            "created_by": row[20],
            "deploy_window_end": row[7].isoformat() if row[7] else None,
            "deploy_window_start": row[6].isoformat() if row[6] else None,
            "environment": row[4],
            "failure_reason": row[19],
            "finished_at": row[18].isoformat() if row[18] else None,
            "gate_summary": gate_summary,
            "id": row[0],
            "product_id": row[1],
            "release_branch": row[8],
            "release_readiness_task_id": row[11],
            "requirement_ids": list(row[23] or []),
            "risk_level": row[13],
            "rollback_plan": row[12],
            "started_at": row[17].isoformat() if row[17] else None,
            "status": row[5],
            "title": row[3],
            "updated_at": row[22].isoformat() if row[22] else None,
            "version_id": row[2],
        }
        for optional_key in (
            "approved_by",
            "artifact_version",
            "assigned_ops_user",
            "commit_sha",
            "created_at",
            "deploy_window_end",
            "deploy_window_start",
            "failure_reason",
            "finished_at",
            "release_branch",
            "release_readiness_task_id",
            "rollback_plan",
            "started_at",
            "updated_at",
        ):
            if request[optional_key] is None:
                request.pop(optional_key)
        return request

    def _deployment_run_from_row(self, row) -> dict[str, Any]:
        run = {
            "created_at": row[11].isoformat() if row[11] else None,
            "created_by": row[10],
            "deployment_request_id": row[1],
            "executor_type": row[2],
            "external_build_id": row[4],
            "external_job_name": row[3],
            "failure_reason": row[9],
            "finished_at": row[8].isoformat() if row[8] else None,
            "id": row[0],
            "log_url": row[6],
            "started_at": row[7].isoformat() if row[7] else None,
            "status": row[5],
            "updated_at": row[12].isoformat() if row[12] else None,
        }
        for optional_key in (
            "created_at",
            "external_build_id",
            "external_job_name",
            "failure_reason",
            "finished_at",
            "log_url",
            "started_at",
            "updated_at",
        ):
            if run[optional_key] is None:
                run.pop(optional_key)
        return run

    def _online_log_metric_from_row(self, row) -> dict[str, Any]:
        top_errors = row[12] or []
        if isinstance(top_errors, str):
            top_errors = json.loads(top_errors)
        metric = {
            "anomaly_summary": row[13],
            "core_event_count": row[11],
            "created_at": row[17].isoformat() if row[17] else None,
            "created_by": row[16],
            "environment": row[3],
            "error_count": row[7],
            "error_rate": float(row[8]) if row[8] is not None else None,
            "id": row[0],
            "module_code": row[2],
            "p95_latency_ms": float(row[9]) if row[9] is not None else None,
            "p99_latency_ms": float(row[10]) if row[10] is not None else None,
            "product_id": row[1],
            "request_count": row[6],
            "source_channel": row[15],
            "status": row[14],
            "top_errors": top_errors,
            "updated_at": row[18].isoformat() if row[18] else None,
            "window_end": row[5].isoformat() if row[5] else None,
            "window_start": row[4].isoformat() if row[4] else None,
        }
        for optional_key in (
            "anomaly_summary",
            "created_at",
            "error_rate",
            "module_code",
            "p95_latency_ms",
            "p99_latency_ms",
            "source_channel",
            "updated_at",
        ):
            if metric[optional_key] is None:
                metric.pop(optional_key)
        return metric
