from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


def _json(value: Any, default: Any) -> str:
    if value is None:
        value = default
    return json.dumps(value, ensure_ascii=False)


class ScheduledAiJobReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._upsert_audit_events = upsert_audit_events

    def list_ai_skills(
        self,
        *,
        code: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where({"code": code, "status": status})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, code, name, version, description, prompt_template,
                           input_schema, output_schema, allowed_tools, required_context,
                           source_type, package_uri, package_checksum, package_entry,
                           package_files, package_size_bytes, manifest, risk_level,
                           requires_human_review, status, created_by, created_at, updated_at
                    FROM ai_skills
                    {where}
                    ORDER BY code ASC, version ASC, id ASC
                    """,
                    tuple(params),
                )
                return [self._skill_from_row(row) for row in cursor.fetchall()]

    def save_ai_skill_record(
        self,
        skill: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_skills(cursor, {skill["id"]: skill})
                self._upsert_audit(cursor, audit_event)

    def list_ai_agents(
        self,
        *,
        brain_app_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where({"brain_app_id": brain_app_id, "status": status})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, brain_app_id, code, name, description, model_gateway_config_id,
                           system_prompt, default_skill_ids, tool_policy, execution_policy,
                           status, created_by, created_at, updated_at
                    FROM ai_agents
                    {where}
                    ORDER BY brain_app_id ASC, code ASC, id ASC
                    """,
                    tuple(params),
                )
                return [self._agent_from_row(row) for row in cursor.fetchall()]

    def save_ai_agent_record(
        self,
        agent: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_agents(cursor, {agent["id"]: agent})
                self._upsert_audit(cursor, audit_event)

    def list_scheduled_jobs(
        self,
        *,
        enabled: bool | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where({"enabled": enabled, "job_type": job_type, "status": status})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, name, job_type, source_system, product_id, schedule_type,
                           cron_expression, interval_seconds, timezone, enabled,
                           execution_mode, agent_id, skill_ids, model_gateway_config_id,
                           config_json, max_retry_count, timeout_seconds, lock_ttl_seconds,
                           status, next_run_at, last_run_at, last_success_at, last_failure_at,
                           last_error_message, created_by, created_at, updated_at,
                           plugin_action_id, plugin_connection_id, plugin_input_mapping,
                           plugin_output_mapping, knowledge_document_ids
                    FROM scheduled_jobs
                    {where}
                    ORDER BY next_run_at DESC NULLS LAST, id DESC
                    """,
                    tuple(params),
                )
                return [self._job_from_row(row) for row in cursor.fetchall()]

    def save_scheduled_job_record(
        self,
        job: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_scheduled_jobs(cursor, {job["id"]: job})
                self._upsert_audit(cursor, audit_event)

    def delete_scheduled_job_record(
        self,
        job_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM scheduled_jobs WHERE id = %s", (job_id,))
                self._upsert_audit(cursor, audit_event)

    def list_scheduled_job_runs(
        self,
        *,
        scheduled_job_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where({"scheduled_job_id": scheduled_job_id, "status": status})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, scheduled_job_id, collector_run_id, trigger_type, status,
                           scheduled_for, started_at, finished_at, records_imported,
                           error_code, error_message, config_snapshot,
                           resolved_agent_snapshot, resolved_skill_snapshots,
                           resolved_prompt_snapshot, tool_policy_snapshot, result_summary,
                           created_at, updated_at, resolved_plugin_snapshot,
                           plugin_invocation_log_id
                    FROM scheduled_job_runs
                    {where}
                    ORDER BY started_at DESC NULLS LAST, id DESC
                    """,
                    tuple(params),
                )
                return [self._run_from_row(row) for row in cursor.fetchall()]

    def save_scheduled_job_run_record(
        self,
        run: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_scheduled_job_runs(cursor, {run["id"]: run})
                self._upsert_audit(cursor, audit_event)

    def upsert_ai_skills(self, cursor, skills: dict[str, dict[str, Any]]) -> None:
        for skill in skills.values():
            cursor.execute(
                """
                INSERT INTO ai_skills (
                  id, code, name, version, description, prompt_template, input_schema,
                  output_schema, allowed_tools, required_context, source_type, package_uri,
                  package_checksum, package_entry, package_files, package_size_bytes, manifest,
                  risk_level, requires_human_review, status, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s::jsonb,
                  %s::jsonb, %s::jsonb, %s::jsonb, %s, %s,
                  %s, %s, %s::jsonb, %s, %s::jsonb,
                  %s, %s, %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  version = EXCLUDED.version,
                  description = EXCLUDED.description,
                  prompt_template = EXCLUDED.prompt_template,
                  input_schema = EXCLUDED.input_schema,
                  output_schema = EXCLUDED.output_schema,
                  allowed_tools = EXCLUDED.allowed_tools,
                  required_context = EXCLUDED.required_context,
                  source_type = EXCLUDED.source_type,
                  package_uri = EXCLUDED.package_uri,
                  package_checksum = EXCLUDED.package_checksum,
                  package_entry = EXCLUDED.package_entry,
                  package_files = EXCLUDED.package_files,
                  package_size_bytes = EXCLUDED.package_size_bytes,
                  manifest = EXCLUDED.manifest,
                  risk_level = EXCLUDED.risk_level,
                  requires_human_review = EXCLUDED.requires_human_review,
                  status = EXCLUDED.status,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    skill["id"],
                    skill["code"],
                    skill["name"],
                    skill.get("version", "1.0.0"),
                    skill.get("description"),
                    skill["prompt_template"],
                    _json(skill.get("input_schema"), {}),
                    _json(skill.get("output_schema"), {}),
                    _json(skill.get("allowed_tools"), []),
                    _json(skill.get("required_context"), []),
                    skill.get("source_type", "inline"),
                    skill.get("package_uri"),
                    skill.get("package_checksum"),
                    skill.get("package_entry"),
                    _json(skill.get("package_files"), []),
                    skill.get("package_size_bytes", 0),
                    _json(skill.get("manifest"), {}),
                    skill.get("risk_level", "medium"),
                    skill.get("requires_human_review", False),
                    skill.get("status", "draft"),
                    skill.get("created_by"),
                    skill.get("created_at"),
                    skill.get("updated_at") or skill.get("created_at"),
                ),
            )

    def upsert_ai_agents(self, cursor, agents: dict[str, dict[str, Any]]) -> None:
        for agent in agents.values():
            cursor.execute(
                """
                INSERT INTO ai_agents (
                  id, brain_app_id, code, name, description, model_gateway_config_id,
                  system_prompt, default_skill_ids, tool_policy, execution_policy,
                  status, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  brain_app_id = EXCLUDED.brain_app_id,
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  model_gateway_config_id = EXCLUDED.model_gateway_config_id,
                  system_prompt = EXCLUDED.system_prompt,
                  default_skill_ids = EXCLUDED.default_skill_ids,
                  tool_policy = EXCLUDED.tool_policy,
                  execution_policy = EXCLUDED.execution_policy,
                  status = EXCLUDED.status,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    agent["id"],
                    agent.get("brain_app_id", "rd_brain"),
                    agent["code"],
                    agent["name"],
                    agent.get("description"),
                    agent.get("model_gateway_config_id"),
                    agent["system_prompt"],
                    _json(agent.get("default_skill_ids"), []),
                    _json(agent.get("tool_policy"), {}),
                    _json(agent.get("execution_policy"), {}),
                    agent.get("status", "active"),
                    agent.get("created_by"),
                    agent.get("created_at"),
                    agent.get("updated_at") or agent.get("created_at"),
                ),
            )

    def upsert_scheduled_jobs(self, cursor, jobs: dict[str, dict[str, Any]]) -> None:
        for job in jobs.values():
            cursor.execute(
                """
                INSERT INTO scheduled_jobs (
                  id, name, job_type, source_system, product_id, schedule_type,
                  cron_expression, interval_seconds, timezone, enabled, execution_mode,
                  agent_id, skill_ids, model_gateway_config_id, config_json,
                  max_retry_count, timeout_seconds, lock_ttl_seconds, status,
                  next_run_at, last_run_at, last_success_at, last_failure_at,
                  last_error_message, created_by, created_at, updated_at,
                  plugin_action_id, plugin_connection_id, plugin_input_mapping,
                  plugin_output_mapping, knowledge_document_ids
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s, %s::jsonb, %s, %s::jsonb,
                  %s, %s, %s, %s,
                  %s::timestamptz, %s::timestamptz, %s::timestamptz,
                  %s::timestamptz, %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s, %s, %s::jsonb, %s::jsonb, %s::jsonb
                )
                ON CONFLICT (id) DO UPDATE SET
                  name = EXCLUDED.name,
                  job_type = EXCLUDED.job_type,
                  source_system = EXCLUDED.source_system,
                  product_id = EXCLUDED.product_id,
                  schedule_type = EXCLUDED.schedule_type,
                  cron_expression = EXCLUDED.cron_expression,
                  interval_seconds = EXCLUDED.interval_seconds,
                  timezone = EXCLUDED.timezone,
                  enabled = EXCLUDED.enabled,
                  execution_mode = EXCLUDED.execution_mode,
                  agent_id = EXCLUDED.agent_id,
                  skill_ids = EXCLUDED.skill_ids,
                  model_gateway_config_id = EXCLUDED.model_gateway_config_id,
                  config_json = EXCLUDED.config_json,
                  max_retry_count = EXCLUDED.max_retry_count,
                  timeout_seconds = EXCLUDED.timeout_seconds,
                  lock_ttl_seconds = EXCLUDED.lock_ttl_seconds,
                  status = EXCLUDED.status,
                  next_run_at = EXCLUDED.next_run_at,
                  last_run_at = EXCLUDED.last_run_at,
                  last_success_at = EXCLUDED.last_success_at,
                  last_failure_at = EXCLUDED.last_failure_at,
                  last_error_message = EXCLUDED.last_error_message,
                  plugin_action_id = EXCLUDED.plugin_action_id,
                  plugin_connection_id = EXCLUDED.plugin_connection_id,
                  plugin_input_mapping = EXCLUDED.plugin_input_mapping,
                  plugin_output_mapping = EXCLUDED.plugin_output_mapping,
                  knowledge_document_ids = EXCLUDED.knowledge_document_ids,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    job["id"],
                    job["name"],
                    job["job_type"],
                    job["source_system"],
                    job.get("product_id"),
                    job["schedule_type"],
                    job.get("cron_expression"),
                    job.get("interval_seconds"),
                    job.get("timezone", "Asia/Shanghai"),
                    job.get("enabled", True),
                    job["execution_mode"],
                    job.get("agent_id"),
                    _json(job.get("skill_ids"), []),
                    job.get("model_gateway_config_id"),
                    _json(job.get("config_json"), {}),
                    job.get("max_retry_count", 0),
                    job.get("timeout_seconds", 600),
                    job.get("lock_ttl_seconds", 900),
                    job.get("status", "active"),
                    job.get("next_run_at"),
                    job.get("last_run_at"),
                    job.get("last_success_at"),
                    job.get("last_failure_at"),
                    job.get("last_error_message"),
                    job.get("created_by"),
                    job.get("created_at"),
                    job.get("updated_at") or job.get("created_at"),
                    job.get("plugin_action_id"),
                    job.get("plugin_connection_id"),
                    _json(job.get("plugin_input_mapping"), {}),
                    _json(job.get("plugin_output_mapping"), {}),
                    _json(job.get("knowledge_document_ids"), []),
                ),
            )

    def upsert_scheduled_job_runs(self, cursor, runs: dict[str, dict[str, Any]]) -> None:
        for run in runs.values():
            cursor.execute(
                """
                INSERT INTO scheduled_job_runs (
                  id, scheduled_job_id, collector_run_id, trigger_type, status,
                  scheduled_for, started_at, finished_at, records_imported,
                  error_code, error_message, config_snapshot, resolved_agent_snapshot,
                  resolved_skill_snapshots, resolved_prompt_snapshot, tool_policy_snapshot,
                  result_summary, created_at, updated_at, resolved_plugin_snapshot,
                  plugin_invocation_log_id
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s::timestamptz, %s::timestamptz, %s::timestamptz, %s,
                  %s, %s, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s::jsonb, %s::jsonb,
                  %s::jsonb, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s::jsonb, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  scheduled_job_id = EXCLUDED.scheduled_job_id,
                  collector_run_id = EXCLUDED.collector_run_id,
                  trigger_type = EXCLUDED.trigger_type,
                  status = EXCLUDED.status,
                  scheduled_for = EXCLUDED.scheduled_for,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  records_imported = EXCLUDED.records_imported,
                  error_code = EXCLUDED.error_code,
                  error_message = EXCLUDED.error_message,
                  config_snapshot = EXCLUDED.config_snapshot,
                  resolved_agent_snapshot = EXCLUDED.resolved_agent_snapshot,
                  resolved_skill_snapshots = EXCLUDED.resolved_skill_snapshots,
                  resolved_prompt_snapshot = EXCLUDED.resolved_prompt_snapshot,
                  tool_policy_snapshot = EXCLUDED.tool_policy_snapshot,
                  result_summary = EXCLUDED.result_summary,
                  resolved_plugin_snapshot = EXCLUDED.resolved_plugin_snapshot,
                  plugin_invocation_log_id = EXCLUDED.plugin_invocation_log_id,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    run["id"],
                    run["scheduled_job_id"],
                    run.get("collector_run_id"),
                    run.get("trigger_type", "manual"),
                    run.get("status", "queued"),
                    run.get("scheduled_for"),
                    run.get("started_at"),
                    run.get("finished_at"),
                    run.get("records_imported", 0),
                    run.get("error_code"),
                    run.get("error_message"),
                    _json(run.get("config_snapshot"), {}),
                    _json(run.get("resolved_agent_snapshot"), {}),
                    _json(run.get("resolved_skill_snapshots"), []),
                    _json(run.get("resolved_prompt_snapshot"), {}),
                    _json(run.get("tool_policy_snapshot"), {}),
                    _json(run.get("result_summary"), {}),
                    run.get("created_at"),
                    run.get("updated_at") or run.get("created_at"),
                    _json(run.get("resolved_plugin_snapshot"), {}),
                    run.get("plugin_invocation_log_id"),
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

    def _skill_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "code": row[1],
            "name": row[2],
            "version": row[3],
            "description": row[4],
            "prompt_template": row[5],
            "input_schema": row[6] or {},
            "output_schema": row[7] or {},
            "allowed_tools": row[8] or [],
            "required_context": row[9] or [],
            "source_type": row[10],
            "package_uri": row[11],
            "package_checksum": row[12],
            "package_entry": row[13],
            "package_files": row[14] or [],
            "package_size_bytes": row[15],
            "manifest": row[16] or {},
            "risk_level": row[17],
            "requires_human_review": row[18],
            "status": row[19],
            "created_by": row[20],
            "created_at": row[21].isoformat() if row[21] else None,
            "updated_at": row[22].isoformat() if row[22] else None,
        }

    def _agent_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "brain_app_id": row[1],
            "code": row[2],
            "name": row[3],
            "description": row[4],
            "model_gateway_config_id": row[5],
            "system_prompt": row[6],
            "default_skill_ids": row[7] or [],
            "tool_policy": row[8] or {},
            "execution_policy": row[9] or {},
            "status": row[10],
            "created_by": row[11],
            "created_at": row[12].isoformat() if row[12] else None,
            "updated_at": row[13].isoformat() if row[13] else None,
        }

    def _job_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "name": row[1],
            "job_type": row[2],
            "source_system": row[3],
            "product_id": row[4],
            "schedule_type": row[5],
            "cron_expression": row[6],
            "interval_seconds": row[7],
            "timezone": row[8],
            "enabled": row[9],
            "execution_mode": row[10],
            "agent_id": row[11],
            "skill_ids": row[12] or [],
            "model_gateway_config_id": row[13],
            "config_json": row[14] or {},
            "max_retry_count": row[15],
            "timeout_seconds": row[16],
            "lock_ttl_seconds": row[17],
            "status": row[18],
            "next_run_at": row[19].isoformat() if row[19] else None,
            "last_run_at": row[20].isoformat() if row[20] else None,
            "last_success_at": row[21].isoformat() if row[21] else None,
            "last_failure_at": row[22].isoformat() if row[22] else None,
            "last_error_message": row[23],
            "created_by": row[24],
            "created_at": row[25].isoformat() if row[25] else None,
            "updated_at": row[26].isoformat() if row[26] else None,
            "plugin_action_id": row[27],
            "plugin_connection_id": row[28],
            "plugin_input_mapping": row[29] or {},
            "plugin_output_mapping": row[30] or {},
            "knowledge_document_ids": row[31] or [],
        }

    def _run_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "scheduled_job_id": row[1],
            "collector_run_id": row[2],
            "trigger_type": row[3],
            "status": row[4],
            "scheduled_for": row[5].isoformat() if row[5] else None,
            "started_at": row[6].isoformat() if row[6] else None,
            "finished_at": row[7].isoformat() if row[7] else None,
            "records_imported": row[8],
            "error_code": row[9],
            "error_message": row[10],
            "config_snapshot": row[11] or {},
            "resolved_agent_snapshot": row[12] or {},
            "resolved_skill_snapshots": row[13] or [],
            "resolved_prompt_snapshot": row[14] or {},
            "tool_policy_snapshot": row[15] or {},
            "result_summary": row[16] or {},
            "created_at": row[17].isoformat() if row[17] else None,
            "updated_at": row[18].isoformat() if row[18] else None,
            "resolved_plugin_snapshot": row[19] or {},
            "plugin_invocation_log_id": row[20],
        }
