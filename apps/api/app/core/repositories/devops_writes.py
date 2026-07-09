from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class DevopsWriteRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing
        self._upsert_audit_events = upsert_audit_events

    def save_gitlab_daily_code_metrics(self, payload: dict[str, Any]) -> None:
        metrics = payload.get("gitlab_daily_code_metrics", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "gitlab_daily_code_metrics", metrics)
                self.upsert_gitlab_daily_code_metrics(cursor, metrics)

    def save_gitlab_daily_code_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_gitlab_daily_code_metrics(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_jenkins_release_records(self, payload: dict[str, Any]) -> None:
        releases = payload.get("jenkins_release_records", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "jenkins_release_records", releases)
                self.upsert_jenkins_release_records(cursor, releases)

    def save_jenkins_release_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_jenkins_release_records(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_deployment_request_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_deployment_requests(cursor, {record["id"]: record})
                if audit_events and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, audit_events)

    def save_deployment_run_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_deployment_runs(cursor, {record["id"]: record})
                if audit_events and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, audit_events)

    def save_online_log_metrics(self, payload: dict[str, Any]) -> None:
        metrics = payload.get("online_log_metrics", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "online_log_metrics", metrics)
                self.upsert_online_log_metrics(cursor, metrics)

    def save_online_log_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_online_log_metrics(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def upsert_gitlab_daily_code_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        for metric in metrics.values():
            created_at = metric.get("created_at")
            updated_at = metric.get("updated_at") or created_at
            collected_at = metric.get("collected_at") or created_at
            cursor.execute(
                """
                INSERT INTO gitlab_daily_code_metrics (
                  id, product_id, repository_id, metric_date, commit_count,
                  active_author_count, merge_request_count, changed_files,
                  additions, deletions, quality_score, risk_count,
                  author_metrics, status, source_channel, collected_at,
                  created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::date, %s,
                  %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  repository_id = EXCLUDED.repository_id,
                  metric_date = EXCLUDED.metric_date,
                  commit_count = EXCLUDED.commit_count,
                  active_author_count = EXCLUDED.active_author_count,
                  merge_request_count = EXCLUDED.merge_request_count,
                  changed_files = EXCLUDED.changed_files,
                  additions = EXCLUDED.additions,
                  deletions = EXCLUDED.deletions,
                  quality_score = EXCLUDED.quality_score,
                  risk_count = EXCLUDED.risk_count,
                  author_metrics = EXCLUDED.author_metrics,
                  status = EXCLUDED.status,
                  source_channel = EXCLUDED.source_channel,
                  collected_at = EXCLUDED.collected_at,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    metric["id"],
                    metric["product_id"],
                    metric["repository_id"],
                    metric["metric_date"],
                    metric.get("commit_count", 0),
                    metric.get("active_author_count", 0),
                    metric.get("merge_request_count", 0),
                    metric.get("changed_files", 0),
                    metric.get("additions", 0),
                    metric.get("deletions", 0),
                    metric.get("quality_score"),
                    metric.get("risk_count", 0),
                    json.dumps(metric.get("author_metrics", []), ensure_ascii=False),
                    metric.get("status", "collected"),
                    metric.get("source_channel"),
                    collected_at,
                    metric["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def upsert_jenkins_release_records(
        self,
        cursor,
        releases: dict[str, dict[str, Any]],
    ) -> None:
        for release in releases.values():
            created_at = release.get("created_at")
            updated_at = release.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO jenkins_release_records (
                  id, product_id, version_id, job_name, build_id, build_number,
                  environment, status, trigger_actor, commit_sha, duration_seconds,
                  started_at, deployed_at, failure_reason, source_channel,
                  deployment_request_id,
                  created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s::timestamptz, %s::timestamptz, %s, %s,
                  %s, %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  job_name = EXCLUDED.job_name,
                  build_id = EXCLUDED.build_id,
                  build_number = EXCLUDED.build_number,
                  environment = EXCLUDED.environment,
                  status = EXCLUDED.status,
                  trigger_actor = EXCLUDED.trigger_actor,
                  commit_sha = EXCLUDED.commit_sha,
                  duration_seconds = EXCLUDED.duration_seconds,
                  started_at = EXCLUDED.started_at,
                  deployed_at = EXCLUDED.deployed_at,
                  failure_reason = EXCLUDED.failure_reason,
                  source_channel = EXCLUDED.source_channel,
                  deployment_request_id = EXCLUDED.deployment_request_id,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    release["id"],
                    release["product_id"],
                    release["version_id"],
                    release["job_name"],
                    release["build_id"],
                    release.get("build_number"),
                    release.get("environment", "prod"),
                    release.get("status", "success"),
                    release.get("trigger_actor"),
                    release.get("commit_sha"),
                    release.get("duration_seconds"),
                    release.get("started_at"),
                    release.get("deployed_at"),
                    release.get("failure_reason"),
                    release.get("source_channel"),
                    release.get("deployment_request_id"),
                    release["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def upsert_deployment_requests(
        self,
        cursor,
        deployment_requests: dict[str, dict[str, Any]],
    ) -> None:
        for deployment_request in deployment_requests.values():
            created_at = deployment_request.get("created_at")
            updated_at = deployment_request.get("updated_at") or created_at
            requirement_ids = [
                str(requirement_id)
                for requirement_id in deployment_request.get("requirement_ids", [])
                if requirement_id
            ]
            cursor.execute(
                """
                INSERT INTO deployment_requests (
                  id, product_id, version_id, title, environment, status,
                  deploy_window_start, deploy_window_end, release_branch, commit_sha,
                  artifact_version, release_readiness_task_id, rollback_plan, risk_level,
                  gate_summary, assigned_ops_user, approved_by, started_at, finished_at,
                  failure_reason, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s::timestamptz, %s::timestamptz, %s, %s,
                  %s, %s, %s, %s,
                  %s::jsonb, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  title = EXCLUDED.title,
                  environment = EXCLUDED.environment,
                  status = EXCLUDED.status,
                  deploy_window_start = EXCLUDED.deploy_window_start,
                  deploy_window_end = EXCLUDED.deploy_window_end,
                  release_branch = EXCLUDED.release_branch,
                  commit_sha = EXCLUDED.commit_sha,
                  artifact_version = EXCLUDED.artifact_version,
                  release_readiness_task_id = EXCLUDED.release_readiness_task_id,
                  rollback_plan = EXCLUDED.rollback_plan,
                  risk_level = EXCLUDED.risk_level,
                  gate_summary = EXCLUDED.gate_summary,
                  assigned_ops_user = EXCLUDED.assigned_ops_user,
                  approved_by = EXCLUDED.approved_by,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  failure_reason = EXCLUDED.failure_reason,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    deployment_request["id"],
                    deployment_request["product_id"],
                    deployment_request["version_id"],
                    deployment_request["title"],
                    deployment_request.get("environment", "prod"),
                    deployment_request.get("status", "pending_ops"),
                    deployment_request.get("deploy_window_start"),
                    deployment_request.get("deploy_window_end"),
                    deployment_request.get("release_branch"),
                    deployment_request.get("commit_sha"),
                    deployment_request.get("artifact_version"),
                    deployment_request.get("release_readiness_task_id"),
                    deployment_request.get("rollback_plan"),
                    deployment_request.get("risk_level", "medium"),
                    json.dumps(deployment_request.get("gate_summary", {}), ensure_ascii=False),
                    deployment_request.get("assigned_ops_user"),
                    deployment_request.get("approved_by"),
                    deployment_request.get("started_at"),
                    deployment_request.get("finished_at"),
                    deployment_request.get("failure_reason"),
                    deployment_request["created_by"],
                    created_at,
                    updated_at,
                ),
            )
            cursor.execute(
                "DELETE FROM deployment_request_requirements WHERE deployment_request_id = %s",
                (deployment_request["id"],),
            )
            for requirement_id in requirement_ids:
                cursor.execute(
                    """
                    INSERT INTO deployment_request_requirements (
                      deployment_request_id, requirement_id, created_at, updated_at
                    )
                    VALUES (%s, %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()))
                    ON CONFLICT (deployment_request_id, requirement_id) DO UPDATE SET
                      updated_at = EXCLUDED.updated_at
                    """,
                    (
                        deployment_request["id"],
                        requirement_id,
                        created_at,
                        updated_at,
                    ),
                )

    def upsert_deployment_runs(
        self,
        cursor,
        deployment_runs: dict[str, dict[str, Any]],
    ) -> None:
        for deployment_run in deployment_runs.values():
            created_at = deployment_run.get("created_at")
            updated_at = deployment_run.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO deployment_runs (
                  id, deployment_request_id, executor_type, external_job_name,
                  external_build_id, status, log_url, started_at, finished_at,
                  failure_reason, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s,
                  %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  deployment_request_id = EXCLUDED.deployment_request_id,
                  executor_type = EXCLUDED.executor_type,
                  external_job_name = EXCLUDED.external_job_name,
                  external_build_id = EXCLUDED.external_build_id,
                  status = EXCLUDED.status,
                  log_url = EXCLUDED.log_url,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  failure_reason = EXCLUDED.failure_reason,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    deployment_run["id"],
                    deployment_run["deployment_request_id"],
                    deployment_run.get("executor_type", "manual"),
                    deployment_run.get("external_job_name"),
                    deployment_run.get("external_build_id"),
                    deployment_run.get("status", "running"),
                    deployment_run.get("log_url"),
                    deployment_run.get("started_at"),
                    deployment_run.get("finished_at"),
                    deployment_run.get("failure_reason"),
                    deployment_run["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def upsert_online_log_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        for metric in metrics.values():
            created_at = metric.get("created_at")
            updated_at = metric.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO online_log_metrics (
                  id, product_id, module_code, environment, window_start, window_end,
                  request_count, error_count, error_rate, p95_latency_ms,
                  p99_latency_ms, core_event_count, top_errors, anomaly_summary,
                  status, source_channel, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s,
                  %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  module_code = EXCLUDED.module_code,
                  environment = EXCLUDED.environment,
                  window_start = EXCLUDED.window_start,
                  window_end = EXCLUDED.window_end,
                  request_count = EXCLUDED.request_count,
                  error_count = EXCLUDED.error_count,
                  error_rate = EXCLUDED.error_rate,
                  p95_latency_ms = EXCLUDED.p95_latency_ms,
                  p99_latency_ms = EXCLUDED.p99_latency_ms,
                  core_event_count = EXCLUDED.core_event_count,
                  top_errors = EXCLUDED.top_errors,
                  anomaly_summary = EXCLUDED.anomaly_summary,
                  status = EXCLUDED.status,
                  source_channel = EXCLUDED.source_channel,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    metric["id"],
                    metric["product_id"],
                    metric.get("module_code"),
                    metric.get("environment", "prod"),
                    metric["window_start"],
                    metric["window_end"],
                    metric.get("request_count", 0),
                    metric.get("error_count", 0),
                    metric.get("error_rate"),
                    metric.get("p95_latency_ms"),
                    metric.get("p99_latency_ms"),
                    metric.get("core_event_count", 0),
                    json.dumps(metric.get("top_errors", []), ensure_ascii=False),
                    metric.get("anomaly_summary"),
                    metric.get("status", "collected"),
                    metric.get("source_channel"),
                    metric["created_by"],
                    created_at,
                    updated_at,
                ),
            )
