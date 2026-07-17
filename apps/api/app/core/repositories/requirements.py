from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.rd_collaboration_shared import (
    RdCollaborationRepositoryError,
    RdCollaborationVersionConflictError,
)
from app.core.store import DEFAULT_BRAIN_APP_ID


def _cursor_row(cursor: Any, row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        getattr(description, "name", description[0]): value
        for description, value in zip(cursor.description, row, strict=True)
    }


class RequirementReadRepository:
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

    def load_requirements(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                requirements = self._load_requirements(cursor)
        return {"requirements": requirements}

    def save_requirements(self, payload: dict[str, Any]) -> None:
        requirements = payload.get("requirements", {})
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "requirements", requirements)
                self.upsert_requirements(cursor, requirements)

    def save_requirement_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_requirements(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_requirement_record(
        self,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM requirements WHERE id = %s", (record_id,))
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def update_requirement_assessment(
        self,
        assessment: dict[str, Any],
        *,
        expected_version: int,
        audit_event: dict[str, Any] | None = None,
        requirement: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Lock and advance assessment state, optionally advancing its requirement atomically."""
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT version FROM requirement_assessments WHERE id = %s FOR UPDATE",
                    (assessment["id"],),
                )
                row = cursor.fetchone()
                current_version = int(row[0]) if row is not None else None
                if current_version is None:
                    raise KeyError(assessment["id"])
                if current_version != expected_version:
                    raise RdCollaborationVersionConflictError(current_version)
                values = {
                    "status": assessment.get("status"),
                    "final_strategy_snapshot_id": assessment.get("final_strategy_snapshot_id"),
                    "strategy_snapshot_id": assessment.get("strategy_snapshot_id"),
                    "structured_assessment": json.dumps(
                        assessment.get("structured_assessment", {})
                    ),
                    "risk_summary": json.dumps(assessment.get("risk_summary", {})),
                    "dependency_summary": json.dumps(assessment.get("dependency_summary", [])),
                    "effort_estimate": json.dumps(assessment.get("effort_estimate", {})),
                    "llm_suggestion": json.dumps(assessment.get("llm_suggestion", {})),
                    "deterministic_validation": json.dumps(
                        assessment.get("deterministic_validation", {})
                    ),
                    "decided_by": assessment.get("decided_by"),
                    "decided_at": assessment.get("decided_at"),
                    "opinion_round": assessment.get("opinion_round", 1),
                    "decision_action": assessment.get("decision_action"),
                    "decision_comment": assessment.get("decision_comment"),
                    "proposed_policy_json": json.dumps(assessment.get("proposed_policy_json", {})),
                    "proposed_risk_level": assessment.get("proposed_risk_level"),
                    "assessment_outcome": assessment.get("assessment_outcome"),
                    "assessment_evidence": json.dumps(assessment.get("assessment_evidence", [])),
                }
                cursor.execute(
                    """
                    UPDATE requirement_assessments SET
                      status = %s, final_strategy_snapshot_id = %s, strategy_snapshot_id = %s,
                      structured_assessment = %s::jsonb, risk_summary = %s::jsonb,
                      dependency_summary = %s::jsonb, effort_estimate = %s::jsonb,
                      llm_suggestion = %s::jsonb, deterministic_validation = %s::jsonb,
                      decided_by = %s, decided_at = %s::timestamptz, opinion_round = %s,
                      decision_action = %s, decision_comment = %s,
                      proposed_policy_json = %s::jsonb, proposed_risk_level = %s,
                      assessment_outcome = %s, assessment_evidence = %s::jsonb,
                      version = version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (*values.values(), assessment["id"]),
                )
                saved = _cursor_row(cursor, cursor.fetchone())
                if requirement is not None:
                    cursor.execute(
                        """
                        UPDATE requirements SET status = %s, updated_at = now()
                        WHERE id = %s AND status = 'submitted'
                        RETURNING id
                        """,
                        (requirement["status"], requirement["id"]),
                    )
                    if cursor.fetchone() is None:
                        raise RdCollaborationRepositoryError(
                            "REQUIREMENT_STATE_INVALID",
                            "Requirement must still be submitted for assessment finalization",
                        )
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])
                return saved or assessment

    def update_requirement_assessment_opinion(self, opinion: dict[str, Any]) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE requirement_assessment_opinions opinion SET
                      conclusion_json = %s::jsonb, evidence_refs = %s::jsonb,
                      confidence = %s, risk_summary = %s::jsonb, cost_summary = %s::jsonb,
                      actor_id = %s, policy_proposal_json = %s::jsonb,
                      outcome_code = %s, risk_level = %s, updated_at = now()
                    FROM requirement_assessments assessment
                    WHERE opinion.id = %s
                      AND assessment.id = opinion.assessment_id
                      AND assessment.opinion_round = opinion.opinion_round
                      AND assessment.strategy_snapshot_id = opinion.strategy_snapshot_id
                      AND opinion.assigned_subject_type = 'human_user'
                      AND opinion.assigned_user_id = %s
                      AND opinion.conclusion_json = '{}'::jsonb
                    RETURNING opinion.*
                    """,
                    (
                        json.dumps(opinion.get("conclusion_json", {})),
                        json.dumps(opinion.get("evidence_refs", [])),
                        opinion.get("confidence"),
                        json.dumps(opinion.get("risk_summary", {})),
                        json.dumps(opinion.get("cost_summary", {})),
                        opinion.get("actor_id"),
                        json.dumps(opinion.get("policy_proposal_json", {})),
                        opinion.get("outcome_code"),
                        opinion.get("risk_level"),
                        opinion["id"],
                        opinion.get("actor_id"),
                    ),
                )
                saved = _cursor_row(cursor, cursor.fetchone())
                if saved is None:
                    raise RdCollaborationRepositoryError(
                        "ASSESSMENT_OPINION_CONFLICT",
                        "Opinion is stale, unassigned, completed, or outside the current "
                        "snapshot round",
                    )
                return saved

    def submit_assessment_answers(
        self,
        *,
        assessment_id: str,
        expected_version: int,
        answers: dict[str, Any],
        actor_id: str,
    ) -> dict[str, Any]:
        """Advance requirement and assessment revisions together, then reopen all opinions."""
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM requirement_assessments WHERE id = %s FOR UPDATE",
                    (assessment_id,),
                )
                assessment = _cursor_row(cursor, cursor.fetchone())
                if assessment is None:
                    raise KeyError(assessment_id)
                if int(assessment.get("version") or 1) != expected_version:
                    raise RdCollaborationVersionConflictError(assessment.get("version"))
                cursor.execute(
                    """
                    UPDATE requirements
                    SET assessment_revision = assessment_revision + 1, updated_at = now()
                    WHERE id = %s RETURNING assessment_revision
                    """,
                    (assessment["requirement_id"],),
                )
                requirement_row = cursor.fetchone()
                if requirement_row is None:
                    raise KeyError(assessment["requirement_id"])
                next_revision = int(requirement_row[0])
                next_round = int(assessment.get("opinion_round") or 1) + 1
                cursor.execute(
                    """
                    INSERT INTO requirement_assessment_answer_revisions (
                      id, assessment_id, requirement_id, requirement_revision, opinion_round,
                      answers_json, actor_id
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        f"{assessment_id}:answer:{next_revision}",
                        assessment_id,
                        assessment["requirement_id"],
                        next_revision,
                        next_round,
                        json.dumps(answers),
                        actor_id,
                    ),
                )
                cursor.execute(
                    """
                    SELECT * FROM requirement_assessment_opinions
                    WHERE assessment_id = %s AND opinion_round = %s
                    ORDER BY role_code, id
                    """,
                    (assessment_id, next_round - 1),
                )
                prior_opinions = [_cursor_row(cursor, row) for row in cursor.fetchall()]
                for prior in prior_opinions:
                    if prior is None:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO requirement_assessment_opinions (
                          id, assessment_id, role_code, ai_employee_id, executor_profile_id,
                          input_revision, strategy_snapshot_id, opinion_round, conclusion_json,
                          evidence_refs, risk_summary, cost_summary, candidate_human_user_ids
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '{}'::jsonb, '[]'::jsonb,
                                  '{}'::jsonb, '{}'::jsonb, %s::jsonb)
                        """,
                        (
                            f"{assessment_id}:opinion:{prior['role_code']}:{next_round}",
                            assessment_id,
                            prior["role_code"],
                            prior.get("ai_employee_id"),
                            prior.get("executor_profile_id"),
                            next_revision,
                            assessment["final_strategy_snapshot_id"],
                            next_round,
                            json.dumps(prior.get("candidate_human_user_ids") or []),
                        ),
                    )
                structured = dict(assessment.get("structured_assessment") or {})
                structured["answers"] = answers
                structured["answers_actor_id"] = actor_id
                cursor.execute(
                    """
                    UPDATE requirement_assessments SET
                      requirement_revision = %s, opinion_round = %s, status = 'evaluating',
                      structured_assessment = %s::jsonb, version = version + 1, updated_at = now()
                    WHERE id = %s RETURNING *
                    """,
                    (next_revision, next_round, json.dumps(structured), assessment_id),
                )
                return _cursor_row(cursor, cursor.fetchone()) or assessment

    def get_requirement_assessment_command(
        self, *, assessment_id: str, operation: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM requirement_assessment_commands
                    WHERE assessment_id = %s AND operation = %s AND idempotency_key = %s
                    """,
                    (assessment_id, operation, idempotency_key),
                )
                return _cursor_row(cursor, cursor.fetchone())

    def save_requirement_assessment_command(self, command: dict[str, Any]) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO requirement_assessment_commands (
                      id, assessment_id, operation, idempotency_key, request_hash,
                      response_snapshot, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (assessment_id, operation, idempotency_key) DO NOTHING
                    RETURNING *
                    """,
                    (
                        command["id"],
                        command["assessment_id"],
                        command["operation"],
                        command["idempotency_key"],
                        command["request_hash"],
                        json.dumps(command["response_snapshot"], default=str),
                        command["created_by"],
                    ),
                )
                saved = _cursor_row(cursor, cursor.fetchone())
                if saved is not None:
                    return saved
                cursor.execute(
                    """
                    SELECT * FROM requirement_assessment_commands
                    WHERE assessment_id = %s AND operation = %s AND idempotency_key = %s
                    """,
                    (command["assessment_id"], command["operation"], command["idempotency_key"]),
                )
                return _cursor_row(cursor, cursor.fetchone()) or command

    def upsert_requirements(self, cursor, requirements: dict[str, dict[str, Any]]) -> None:
        for requirement in requirements.values():
            created_at = requirement.get("created_at")
            updated_at = requirement.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO requirements (
                  id, brain_app_id, title, product_id, version_id, module_code,
                  description, priority, source,
                  status, created_by, assignee, approval_comment, rejection_reason, task_ids,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  brain_app_id = EXCLUDED.brain_app_id,
                  title = EXCLUDED.title,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  description = EXCLUDED.description,
                  priority = EXCLUDED.priority,
                  source = EXCLUDED.source,
                  status = EXCLUDED.status,
                  created_by = EXCLUDED.created_by,
                  assignee = EXCLUDED.assignee,
                  approval_comment = EXCLUDED.approval_comment,
                  rejection_reason = EXCLUDED.rejection_reason,
                  task_ids = EXCLUDED.task_ids,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    requirement["id"],
                    requirement.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
                    requirement["title"],
                    requirement["product_id"],
                    requirement["version_id"],
                    requirement.get("module_code"),
                    requirement["content"],
                    requirement.get("priority", "P1"),
                    requirement.get("source", "business_department"),
                    requirement.get("status", "submitted"),
                    requirement["created_by"],
                    requirement.get("assignee"),
                    requirement.get("approval_comment"),
                    requirement.get("rejection_reason"),
                    json.dumps(requirement.get("task_ids", []), ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def _requirement_summary_where(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        title: str | None = None,
        source: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if priority is not None:
            where_clauses.append("r.priority = %s")
            params.append(priority)
        if product is not None:
            product_pattern = f"%{product}%"
            where_clauses.append("(p.code ILIKE %s OR p.name ILIKE %s OR r.product_id ILIKE %s)")
            params.extend([product_pattern, product_pattern, product_pattern])
        if product_id is not None:
            where_clauses.append("r.product_id = %s")
            params.append(product_id)
        if product_scope_ids is not None:
            if product_scope_ids:
                where_clauses.append("r.product_id = ANY(%s)")
                params.append(product_scope_ids)
            else:
                where_clauses.append("FALSE")
        if status is not None:
            where_clauses.append(
                """
                CASE r.status
                    WHEN 'pending_approval' THEN 'submitted'
                    WHEN 'task_created' THEN 'designing'
                    ELSE r.status
                END = %s
                """
            )
            params.append(status)
        if title is not None:
            title_pattern = f"%{title}%"
            where_clauses.append("(r.title ILIKE %s OR r.id ILIKE %s)")
            params.extend([title_pattern, title_pattern])
        if source is not None:
            where_clauses.append("r.source = %s")
            params.append(source)
        if version is not None:
            version_pattern = f"%{version}%"
            where_clauses.append("(v.code ILIKE %s OR v.name ILIKE %s OR r.version_id ILIKE %s)")
            params.extend([version_pattern, version_pattern, version_pattern])
        if version_id is not None:
            where_clauses.append("r.version_id = %s")
            params.append(version_id)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_clause, params

    def count_requirement_summaries(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        title: str | None = None,
        source: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> int:
        where_clause, params = self._requirement_summary_where(
            priority=priority,
            product=product,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            status=status,
            title=title,
            source=source,
            version=version,
            version_id=version_id,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM requirements r
                    JOIN products p ON p.id = r.product_id
                    LEFT JOIN product_versions v ON v.id = r.version_id
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_requirement_summaries(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        title: str | None = None,
        source: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        where_clause, params = self._requirement_summary_where(
            priority=priority,
            product=product,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            status=status,
            title=title,
            source=source,
            version=version,
            version_id=version_id,
        )
        sort_columns = {
            "created_at": "r.created_at",
            "id": "r.id",
            "priority": "r.priority",
            "product_code": "p.code",
            "product_name": "p.name",
            "status": "r.status",
            "source": "r.source",
            "assignee": "r.assignee",
            "title": "r.title",
            "updated_at": "COALESCE(r.updated_at, r.created_at)",
            "version_code": "v.code",
            "version_name": "v.name",
        }
        order_column = sort_columns.get(sort_by, sort_columns["created_at"])
        order_direction = "ASC" if sort_order == "asc" else "DESC"
        paging_clause = ""
        if limit is not None:
            paging_clause += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            paging_clause += " OFFSET %s"
            params.append(offset)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT r.id, r.brain_app_id, r.title, r.product_id, r.version_id,
                           r.module_code, r.description, r.priority, r.status, r.created_by,
                           r.approval_comment, r.rejection_reason, r.task_ids,
                           r.created_at, r.updated_at, p.code, p.name, v.code, v.name,
                           r.assignee, r.source
                    FROM requirements r
                    JOIN products p ON p.id = r.product_id
                    LEFT JOIN product_versions v ON v.id = r.version_id
                    {where_clause}
                    ORDER BY {order_column} {order_direction}, r.id ASC
                    {paging_clause}
                    """,
                    tuple(params),
                )
                requirements = []
                for row in cursor.fetchall():
                    requirement = {
                        "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                        "content": row[6],
                        "created_at": row[13].isoformat() if row[13] else None,
                        "created_by": row[9],
                        "assignee": row[19],
                        "id": row[0],
                        "module_code": row[5],
                        "priority": row[7],
                        "product_code": row[15],
                        "product_id": row[3],
                        "product_name": row[16],
                        "status": row[8],
                        "source": row[20] or "business_department",
                        "task_ids": list(row[12] or []),
                        "title": row[2],
                        "updated_at": row[14].isoformat() if row[14] else None,
                        "version_code": row[17],
                        "version_id": row[4],
                        "version_name": row[18],
                    }
                    if row[10] is not None:
                        requirement["approval_comment"] = row[10]
                    if row[11] is not None:
                        requirement["rejection_reason"] = row[11]
                    requirements.append(requirement)
                return requirements

    def _load_requirements(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, brain_app_id, title, product_id, version_id, module_code,
                   description, priority,
                   status, created_by, approval_comment, rejection_reason, task_ids,
                   assignee, source,
                   created_at, updated_at, assessment_revision
            FROM requirements
            ORDER BY created_at DESC, id
            """
        )
        requirements = {}
        for row in cursor.fetchall():
            requirement = _requirement_from_row(row)
            if row[10] is not None:
                requirement["approval_comment"] = row[10]
            if row[11] is not None:
                requirement["rejection_reason"] = row[11]
            requirements[row[0]] = requirement
        return requirements


def _requirement_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "assessment_revision": int(row[17] or 1),
        "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
        "content": row[6],
        "created_at": row[15].isoformat() if row[15] else None,
        "created_by": row[9],
        "assignee": row[13],
        "id": row[0],
        "module_code": row[5],
        "priority": row[7],
        "product_id": row[3],
        "status": row[8],
        "source": row[14] or "business_department",
        "task_ids": list(row[12] or []),
        "title": row[2],
        "updated_at": row[16].isoformat() if row[16] else None,
        "version_id": row[4],
    }
