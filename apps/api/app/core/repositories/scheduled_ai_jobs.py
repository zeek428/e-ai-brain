from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

SCHEDULED_JOB_SELECT = """
id, name, job_type, source_system, product_id, schedule_type,
cron_expression, interval_seconds, timezone, enabled,
execution_mode, agent_id, skill_ids, model_gateway_config_id,
config_json, max_retry_count, timeout_seconds, lock_ttl_seconds,
status, next_run_at, last_run_at, last_success_at, last_failure_at,
last_error_message, created_by, created_at, updated_at,
plugin_action_id, plugin_connection_id, plugin_input_mapping,
plugin_output_mapping, knowledge_document_ids, result_actions
"""

SCHEDULED_JOB_SORT_COLUMNS = {
    "created_at": "created_at",
    "enabled": "enabled",
    "job_type": "job_type",
    "last_failure_at": "last_failure_at",
    "last_run_at": "last_run_at",
    "last_success_at": "last_success_at",
    "name": "lower(name)",
    "next_run_at": "next_run_at",
    "status": "status",
    "updated_at": "updated_at",
}

SCHEDULED_JOB_RUN_SELECT = """
run.id, run.scheduled_job_id, run.collector_run_id, run.source_run_id,
run.trigger_type, run.status,
run.scheduled_for, run.started_at, run.finished_at, run.records_imported,
run.error_code, run.error_message, run.config_snapshot,
run.resolved_agent_snapshot, run.resolved_skill_snapshots,
run.resolved_prompt_snapshot, run.tool_policy_snapshot, run.result_summary,
run.created_at, run.updated_at, run.resolved_plugin_snapshot,
run.plugin_invocation_log_id, run.assistant_action_run_id,
run.assistant_action_draft_id, run.assistant_source_message_id,
run.triggered_by_assistant,
job.name AS scheduled_job_name
"""

SCHEDULED_JOB_RUN_SORT_COLUMNS = {
    "created_at": "run.created_at",
    "finished_at": "run.finished_at",
    "records_imported": "run.records_imported",
    "started_at": "run.started_at",
    "status": "run.status",
    "trigger_type": "run.trigger_type",
    "updated_at": "run.updated_at",
}

AI_SKILL_SELECT = """
id, code, name, version, description, prompt_template,
input_schema, output_schema, allowed_tools, required_context,
source_type, package_uri, package_checksum, package_entry,
package_files, package_size_bytes, manifest, risk_level,
requires_human_review, status, created_by, created_at, updated_at
"""

AI_SKILL_SORT_COLUMNS = {
    "code": "lower(code)",
    "created_at": "created_at",
    "name": "lower(name)",
    "requires_human_review": "requires_human_review",
    "risk_level": "risk_level",
    "source_type": "source_type",
    "status": "status",
    "updated_at": "updated_at",
    "version": "version",
}

AI_AGENT_SELECT = """
id, brain_app_id, code, name, description, model_gateway_config_id,
system_prompt, default_skill_ids, tool_policy, execution_policy,
source_type, package_uri, package_checksum, package_entry, package_files,
package_size_bytes, manifest, status, created_by, created_at, updated_at
"""

AI_AGENT_SORT_COLUMNS = {
    "brain_app_id": "brain_app_id",
    "code": "lower(code)",
    "created_at": "created_at",
    "model_gateway_config_id": "model_gateway_config_id",
    "name": "lower(name)",
    "source_type": "source_type",
    "status": "status",
    "updated_at": "updated_at",
}


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
                    SELECT {AI_SKILL_SELECT}
                    FROM ai_skills
                    {where}
                    ORDER BY code ASC, version ASC, id ASC
                    """,
                    tuple(params),
                )
                return [self._skill_from_row(row) for row in cursor.fetchall()]

    def count_ai_skills(
        self,
        *,
        code: str | None = None,
        keyword: str | None = None,
        requires_human_review: bool | None = None,
        risk_level: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._skill_where(
            {
                "code": code,
                "requires_human_review": requires_human_review,
                "risk_level": risk_level,
                "source_type": source_type,
                "status": status,
            },
            keyword=keyword,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT count(*) FROM ai_skills {where}", tuple(params))
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_ai_skills_page(
        self,
        *,
        code: str | None = None,
        keyword: str | None = None,
        limit: int,
        offset: int,
        requires_human_review: bool | None = None,
        risk_level: str | None = None,
        sort_by: str,
        sort_order: str,
        source_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._skill_where(
            {
                "code": code,
                "requires_human_review": requires_human_review,
                "risk_level": risk_level,
                "source_type": source_type,
                "status": status,
            },
            keyword=keyword,
        )
        sort_column = AI_SKILL_SORT_COLUMNS.get(sort_by, "updated_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {AI_SKILL_SELECT}
                    FROM ai_skills
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
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
                    SELECT {AI_AGENT_SELECT}
                    FROM ai_agents
                    {where}
                    ORDER BY brain_app_id ASC, code ASC, id ASC
                    """,
                    tuple(params),
                )
                return [self._agent_from_row(row) for row in cursor.fetchall()]

    def count_ai_agents(
        self,
        *,
        brain_app_id: str | None = None,
        keyword: str | None = None,
        model_gateway_config_id: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._agent_where(
            {
                "brain_app_id": brain_app_id,
                "model_gateway_config_id": model_gateway_config_id,
                "status": status,
            },
            keyword=keyword,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT count(*) FROM ai_agents {where}", tuple(params))
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_ai_agents_page(
        self,
        *,
        brain_app_id: str | None = None,
        keyword: str | None = None,
        limit: int,
        model_gateway_config_id: str | None = None,
        offset: int,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._agent_where(
            {
                "brain_app_id": brain_app_id,
                "model_gateway_config_id": model_gateway_config_id,
                "status": status,
            },
            keyword=keyword,
        )
        sort_column = AI_AGENT_SORT_COLUMNS.get(sort_by, "updated_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {AI_AGENT_SELECT}
                    FROM ai_agents
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
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
                    SELECT {SCHEDULED_JOB_SELECT}
                    FROM scheduled_jobs
                    {where}
                    ORDER BY next_run_at DESC NULLS LAST, id DESC
                    """,
                    tuple(params),
                )
                return [self._job_from_row(row) for row in cursor.fetchall()]

    def count_scheduled_jobs(
        self,
        *,
        enabled: bool | None = None,
        job_type: str | None = None,
        keyword: str | None = None,
        name: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        source_system: str | None = None,
        status: str | None = None,
    ) -> int:
        where, params = self._job_where(
            {
                "enabled": enabled,
                "job_type": job_type,
                "product_id": product_id,
                "source_system": source_system,
                "status": status,
            },
            keyword=keyword,
            name=name,
            product_scope_ids=product_scope_ids,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT count(*) FROM scheduled_jobs {where}", tuple(params))
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_scheduled_jobs_page(
        self,
        *,
        enabled: bool | None = None,
        job_type: str | None = None,
        keyword: str | None = None,
        limit: int,
        name: str | None = None,
        offset: int,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        sort_by: str,
        sort_order: str,
        source_system: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._job_where(
            {
                "enabled": enabled,
                "job_type": job_type,
                "product_id": product_id,
                "source_system": source_system,
                "status": status,
            },
            keyword=keyword,
            name=name,
            product_scope_ids=product_scope_ids,
        )
        sort_column = SCHEDULED_JOB_SORT_COLUMNS.get(sort_by, "next_run_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {SCHEDULED_JOB_SELECT}
                    FROM scheduled_jobs
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
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
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_scheduled_jobs(cursor, {job["id"]: job})
                self._upsert_audit(cursor, audit_event)

    def delete_scheduled_job_record(
        self,
        job_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM scheduled_jobs WHERE id = %s", (job_id,))
                self._upsert_audit(cursor, audit_event)

    def list_scheduled_job_runs(
        self,
        *,
        run_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where({"scheduled_job_id": scheduled_job_id, "status": status})
        normalized_run_ids = [
            str(run_id).strip()
            for run_id in (run_ids or [])
            if str(run_id).strip()
        ]
        if normalized_run_ids:
            run_id_clause = "id = ANY(%s)"
            if where:
                where = f"{where} AND {run_id_clause}"
            else:
                where = f"WHERE {run_id_clause}"
            params.append(normalized_run_ids)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, scheduled_job_id, collector_run_id, source_run_id,
                           trigger_type, status,
                           scheduled_for, started_at, finished_at, records_imported,
                           error_code, error_message, config_snapshot,
                           resolved_agent_snapshot, resolved_skill_snapshots,
                           resolved_prompt_snapshot, tool_policy_snapshot, result_summary,
                           created_at, updated_at, resolved_plugin_snapshot,
                           plugin_invocation_log_id, assistant_action_run_id,
                           assistant_action_draft_id, assistant_source_message_id,
                           triggered_by_assistant
                    FROM scheduled_job_runs
                    {where}
                    ORDER BY started_at DESC NULLS LAST, id DESC
                    """,
                    tuple(params),
                )
                return [self._run_from_row(row) for row in cursor.fetchall()]

    def count_scheduled_job_runs(
        self,
        *,
        product_scope_ids: list[str] | None = None,
        run_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        status: str | None = None,
    ) -> int:
        join_clause, where, params = self._run_where(
            product_scope_ids=product_scope_ids,
            run_ids=run_ids,
            scheduled_job_id=scheduled_job_id,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM scheduled_job_runs run {join_clause} {where}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_scheduled_job_runs_page(
        self,
        *,
        limit: int,
        offset: int,
        product_scope_ids: list[str] | None = None,
        run_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        join_clause, where, params = self._run_where(
            product_scope_ids=product_scope_ids,
            run_ids=run_ids,
            scheduled_job_id=scheduled_job_id,
            status=status,
        )
        sort_column = SCHEDULED_JOB_RUN_SORT_COLUMNS.get(sort_by, "run.started_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {SCHEDULED_JOB_RUN_SELECT}
                    FROM scheduled_job_runs run
                    {join_clause or "LEFT JOIN scheduled_jobs job ON job.id = run.scheduled_job_id"}
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, run.id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [self._run_from_row(row) for row in cursor.fetchall()]

    def list_assistant_scoped_scheduled_job_runs(
        self,
        *,
        action_draft_ids: list[str],
        action_run_ids: list[str],
        message_ids: list[str],
        referenced_run_ids: list[str],
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        predicates: list[str] = []
        params: list[Any] = []

        def add_in_predicate(column: str, values: list[str]) -> None:
            unique_values = sorted({str(value) for value in values if str(value).strip()})
            if not unique_values:
                return
            placeholders = ", ".join(["%s"] * len(unique_values))
            predicates.append(f"{column} IN ({placeholders})")
            params.extend(unique_values)

        add_in_predicate("id", referenced_run_ids)
        add_in_predicate("source_run_id", referenced_run_ids)
        add_in_predicate("assistant_action_run_id", action_run_ids)
        add_in_predicate("assistant_action_draft_id", action_draft_ids)
        if message_ids:
            unique_message_ids = sorted({str(value) for value in message_ids if str(value).strip()})
            if unique_message_ids:
                placeholders = ", ".join(["%s"] * len(unique_message_ids))
                predicates.append(
                    "(triggered_by_assistant IS TRUE "
                    f"AND assistant_source_message_id IN ({placeholders}))"
                )
                params.extend(unique_message_ids)

        if not predicates:
            return []

        final_filter = ""
        if since:
            final_filter = """
            WHERE GREATEST(
                    COALESCE(started_at, '-infinity'::timestamptz),
                    COALESCE(created_at, '-infinity'::timestamptz),
                    COALESCE(updated_at, '-infinity'::timestamptz)
                  ) >= %s::timestamptz
            """
            params.append(since)

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    WITH RECURSIVE run_edges AS (
                      SELECT source_run_id AS from_id, id AS to_id
                      FROM scheduled_job_runs
                      WHERE trigger_type = 'manual_rerun'
                        AND source_run_id IS NOT NULL
                      UNION
                      SELECT id AS from_id, source_run_id AS to_id
                      FROM scheduled_job_runs
                      WHERE source_run_id IS NOT NULL
                    ),
                    scoped_run_ids AS (
                      SELECT id
                      FROM scheduled_job_runs
                      WHERE {" OR ".join(predicates)}
                      UNION
                      SELECT edge.to_id
                      FROM scoped_run_ids scoped
                      JOIN run_edges edge
                        ON edge.from_id = scoped.id
                    ),
                    scoped_runs AS (
                      SELECT run.id, run.scheduled_job_id, run.collector_run_id, run.source_run_id,
                             run.trigger_type, run.status,
                             run.scheduled_for, run.started_at, run.finished_at,
                             run.records_imported,
                             run.error_code, run.error_message, run.config_snapshot,
                             run.resolved_agent_snapshot, run.resolved_skill_snapshots,
                             run.resolved_prompt_snapshot, run.tool_policy_snapshot,
                             run.result_summary,
                             run.created_at, run.updated_at, run.resolved_plugin_snapshot,
                             run.plugin_invocation_log_id, run.assistant_action_run_id,
                             run.assistant_action_draft_id, run.assistant_source_message_id,
                             run.triggered_by_assistant
                      FROM scheduled_job_runs run
                      JOIN scoped_run_ids scoped
                        ON scoped.id = run.id
                    )
                    SELECT DISTINCT ON (id)
                           id, scheduled_job_id, collector_run_id, source_run_id,
                           trigger_type, status,
                           scheduled_for, started_at, finished_at, records_imported,
                           error_code, error_message, config_snapshot,
                           resolved_agent_snapshot, resolved_skill_snapshots,
                           resolved_prompt_snapshot, tool_policy_snapshot, result_summary,
                           created_at, updated_at, resolved_plugin_snapshot,
                           plugin_invocation_log_id, assistant_action_run_id,
                           assistant_action_draft_id, assistant_source_message_id,
                           triggered_by_assistant
                    FROM scoped_runs
                    {final_filter}
                    ORDER BY id, started_at DESC NULLS LAST, updated_at DESC
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
        with self._connect(autocommit=False) as connection:
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
                  source_type, package_uri, package_checksum, package_entry, package_files,
                  package_size_bytes, manifest, status, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s, %s, %s, %s, %s::jsonb,
                  %s, %s::jsonb, %s, %s, COALESCE(%s::timestamptz, now()),
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
                  source_type = EXCLUDED.source_type,
                  package_uri = EXCLUDED.package_uri,
                  package_checksum = EXCLUDED.package_checksum,
                  package_entry = EXCLUDED.package_entry,
                  package_files = EXCLUDED.package_files,
                  package_size_bytes = EXCLUDED.package_size_bytes,
                  manifest = EXCLUDED.manifest,
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
                    agent.get("source_type", "inline"),
                    agent.get("package_uri"),
                    agent.get("package_checksum"),
                    agent.get("package_entry"),
                    _json(agent.get("package_files"), []),
                    agent.get("package_size_bytes", 0),
                    _json(agent.get("manifest"), {}),
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
                  plugin_output_mapping, knowledge_document_ids, result_actions
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s, %s::jsonb, %s, %s::jsonb,
                  %s, %s, %s, %s,
                  %s::timestamptz, %s::timestamptz, %s::timestamptz,
                  %s::timestamptz, %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s, %s, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s::jsonb
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
                  result_actions = EXCLUDED.result_actions,
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
                    _json(job.get("result_actions"), []),
                ),
            )

    def upsert_scheduled_job_runs(self, cursor, runs: dict[str, dict[str, Any]]) -> None:
        for run in runs.values():
            cursor.execute(
                """
                INSERT INTO scheduled_job_runs (
                  id, scheduled_job_id, collector_run_id, source_run_id, trigger_type, status,
                  scheduled_for, started_at, finished_at, records_imported,
                  error_code, error_message, config_snapshot, resolved_agent_snapshot,
                  resolved_skill_snapshots, resolved_prompt_snapshot, tool_policy_snapshot,
                  result_summary, created_at, updated_at, resolved_plugin_snapshot,
                  plugin_invocation_log_id, assistant_action_run_id,
                  assistant_action_draft_id, assistant_source_message_id,
                  triggered_by_assistant
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s::timestamptz, %s::timestamptz, %s::timestamptz, %s,
                  %s, %s, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s::jsonb, %s::jsonb,
                  %s::jsonb, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s::jsonb, %s,
                  %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  scheduled_job_id = EXCLUDED.scheduled_job_id,
                  collector_run_id = EXCLUDED.collector_run_id,
                  source_run_id = EXCLUDED.source_run_id,
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
                  assistant_action_run_id = EXCLUDED.assistant_action_run_id,
                  assistant_action_draft_id = EXCLUDED.assistant_action_draft_id,
                  assistant_source_message_id = EXCLUDED.assistant_source_message_id,
                  triggered_by_assistant = EXCLUDED.triggered_by_assistant,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    run["id"],
                    run["scheduled_job_id"],
                    run.get("collector_run_id"),
                    run.get("source_run_id"),
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
                    run.get("assistant_action_run_id"),
                    run.get("assistant_action_draft_id"),
                    run.get("assistant_source_message_id"),
                    bool(run.get("triggered_by_assistant")),
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

    def _job_where(
        self,
        values: dict[str, Any],
        *,
        keyword: str | None,
        name: str | None,
        product_scope_ids: list[str] | None = None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in values.items():
            if value is None:
                continue
            clauses.append(f"{field} = %s")
            params.append(value)
        normalized_name = str(name or "").strip().lower()
        if product_scope_ids is not None:
            normalized_scope_ids = sorted(
                {str(product_id) for product_id in product_scope_ids if str(product_id).strip()}
            )
            if normalized_scope_ids:
                clauses.append("product_id = ANY(%s)")
                params.append(normalized_scope_ids)
            else:
                clauses.append("FALSE")
        if normalized_name:
            clauses.append("lower(name) LIKE %s")
            params.append(f"%{normalized_name}%")
        normalized_keyword = str(keyword or "").strip().lower()
        if normalized_keyword:
            probe = f"%{normalized_keyword}%"
            clauses.append(
                "("
                "lower(id) LIKE %s OR lower(name) LIKE %s OR lower(job_type) LIKE %s "
                "OR lower(source_system) LIKE %s OR lower(COALESCE(product_id, '')) LIKE %s"
                ")"
            )
            params.extend([probe, probe, probe, probe, probe])
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _skill_where(
        self,
        values: dict[str, Any],
        *,
        keyword: str | None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in values.items():
            if value is None:
                continue
            clauses.append(f"{field} = %s")
            params.append(value)
        normalized_keyword = str(keyword or "").strip().lower()
        if normalized_keyword:
            probe = f"%{normalized_keyword}%"
            clauses.append(
                "("
                "lower(id) LIKE %s OR lower(code) LIKE %s OR lower(name) LIKE %s "
                "OR lower(version) LIKE %s OR lower(description) LIKE %s "
                "OR lower(prompt_template) LIKE %s OR lower(source_type) LIKE %s "
                "OR lower(risk_level) LIKE %s"
                ")"
            )
            params.extend([probe, probe, probe, probe, probe, probe, probe, probe])
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _agent_where(
        self,
        values: dict[str, Any],
        *,
        keyword: str | None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in values.items():
            if value is None:
                continue
            clauses.append(f"{field} = %s")
            params.append(value)
        normalized_keyword = str(keyword or "").strip().lower()
        if normalized_keyword:
            probe = f"%{normalized_keyword}%"
            clauses.append(
                "("
                "lower(id) LIKE %s OR lower(brain_app_id) LIKE %s OR lower(code) LIKE %s "
                "OR lower(name) LIKE %s OR lower(description) LIKE %s "
                "OR lower(model_gateway_config_id) LIKE %s OR lower(system_prompt) LIKE %s"
                ")"
            )
            params.extend([probe, probe, probe, probe, probe, probe, probe])
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _run_where(
        self,
        *,
        product_scope_ids: list[str] | None,
        run_ids: list[str] | None,
        scheduled_job_id: str | None,
        status: str | None,
    ) -> tuple[str, str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        join_clause = ""
        if scheduled_job_id is not None:
            clauses.append("run.scheduled_job_id = %s")
            params.append(scheduled_job_id)
        if status is not None:
            clauses.append("run.status = %s")
            params.append(status)
        normalized_run_ids = sorted(
            {str(run_id).strip() for run_id in (run_ids or []) if str(run_id).strip()}
        )
        if normalized_run_ids:
            clauses.append("run.id = ANY(%s)")
            params.append(normalized_run_ids)
        if product_scope_ids is not None:
            normalized_scope_ids = sorted(
                {str(product_id) for product_id in product_scope_ids if str(product_id).strip()}
            )
            join_clause = "JOIN scheduled_jobs job ON job.id = run.scheduled_job_id"
            if normalized_scope_ids:
                clauses.append("job.product_id = ANY(%s)")
                params.append(normalized_scope_ids)
            else:
                clauses.append("FALSE")
        return join_clause, (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

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
            "source_type": row[10],
            "package_uri": row[11],
            "package_checksum": row[12],
            "package_entry": row[13],
            "package_files": row[14] or [],
            "package_size_bytes": row[15],
            "manifest": row[16] or {},
            "status": row[17],
            "created_by": row[18],
            "created_at": row[19].isoformat() if row[19] else None,
            "updated_at": row[20].isoformat() if row[20] else None,
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
            "result_actions": row[32] or [],
        }

    def _run_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "scheduled_job_id": row[1],
            "collector_run_id": row[2],
            "source_run_id": row[3],
            "trigger_type": row[4],
            "status": row[5],
            "scheduled_for": row[6].isoformat() if row[6] else None,
            "started_at": row[7].isoformat() if row[7] else None,
            "finished_at": row[8].isoformat() if row[8] else None,
            "records_imported": row[9],
            "error_code": row[10],
            "error_message": row[11],
            "config_snapshot": row[12] or {},
            "resolved_agent_snapshot": row[13] or {},
            "resolved_skill_snapshots": row[14] or [],
            "resolved_prompt_snapshot": row[15] or {},
            "tool_policy_snapshot": row[16] or {},
            "result_summary": row[17] or {},
            "created_at": row[18].isoformat() if row[18] else None,
            "updated_at": row[19].isoformat() if row[19] else None,
            "resolved_plugin_snapshot": row[20] or {},
            "plugin_invocation_log_id": row[21],
            "assistant_action_run_id": row[22],
            "assistant_action_draft_id": row[23],
            "assistant_source_message_id": row[24],
            "triggered_by_assistant": bool(row[25]),
            "scheduled_job_name": row[26] if len(row) > 26 else None,
        }
