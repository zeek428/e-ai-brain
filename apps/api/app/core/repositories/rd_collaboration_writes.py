from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from contextlib import AbstractContextManager
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb


class RdCollaborationRepositoryError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class RdCollaborationVersionConflictError(RdCollaborationRepositoryError):
    def __init__(self, current_version: int | None) -> None:
        super().__init__(
            "RD_VERSION_CONFLICT",
            "R&D collaboration record version conflict",
            details={"current_version": current_version},
        )
        self.current_version = current_version


JSON_FIELDS = {
    "acceptance_criteria",
    "answer_actor_selector",
    "answer_json",
    "answer_schema",
    "assignable_subject_types",
    "budget_config",
    "budget_json",
    "candidate_ai_employee_ids",
    "candidate_human_user_ids",
    "capabilities",
    "capability_tags",
    "conclusion_json",
    "content",
    "context_config",
    "context_cursor",
    "cost_summary",
    "decision_actor_selector",
    "dependency_summary",
    "deterministic_validation",
    "effort_estimate",
    "escalation_target_selector",
    "evidence_json",
    "evidence_refs",
    "failure_json",
    "fallback_executor_profile_ids",
    "handoff_summary",
    "input_contract",
    "input_json",
    "llm_suggestion",
    "operations_json",
    "options_json",
    "output_contract",
    "payload_json",
    "persona_json",
    "product_scope",
    "recommendation_json",
    "resume_metadata",
    "release_conditions",
    "repository_trust_domains",
    "required_permissions",
    "responsibilities",
    "responsibility_scope",
    "result_json",
    "rework_evidence",
    "reviewer_role_codes",
    "risk_scope",
    "risk_summary",
    "structured_assessment",
    "supported_role_codes",
    "tool_config",
    "tool_trust_domains",
    "workspace_capabilities",
    "work_style_json",
}


TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "rd_role_definitions": (
        "id",
        "brain_app_id",
        "code",
        "name",
        "capabilities",
        "responsibilities",
        "maximum_risk_level",
        "assignable_subject_types",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    ),
    "rd_ai_employees": (
        "id",
        "brain_app_id",
        "code",
        "name",
        "capability_tags",
        "persona_version",
        "persona_json",
        "work_style_version",
        "work_style_json",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    ),
    "rd_executor_profiles": (
        "id",
        "brain_app_id",
        "code",
        "name",
        "executor_type",
        "runner_id",
        "model_gateway_config_id",
        "credential_ref",
        "workspace_capabilities",
        "max_concurrency",
        "supported_role_codes",
        "health_status",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    ),
    "rd_task_executor_policy_role_bindings": (
        "id",
        "policy_id",
        "role_code",
        "actor_mode",
        "candidate_human_user_ids",
        "candidate_ai_employee_ids",
        "primary_executor_profile_id",
        "fallback_executor_profile_ids",
        "repository_trust_domains",
        "tool_trust_domains",
        "context_config",
        "tool_config",
        "budget_config",
        "reviewer_role_codes",
        "required_permissions",
        "status",
        "created_at",
        "updated_at",
    ),
    "rd_run_seats": (
        "id",
        "collaboration_run_id",
        "role_code",
        "subject_type",
        "human_user_id",
        "ai_employee_id",
        "executor_profile_id",
        "responsibility_scope",
        "capacity",
        "status",
        "replaces_seat_id",
        "created_at",
        "updated_at",
    ),
    "rd_role_sessions": (
        "id",
        "collaboration_run_id",
        "seat_id",
        "session_no",
        "handoff_summary",
        "context_cursor",
        "resume_metadata",
        "status",
        "started_at",
        "ended_at",
        "created_at",
        "updated_at",
    ),
    "rd_work_items": (
        "id",
        "collaboration_run_id",
        "plan_version",
        "work_item_type",
        "title",
        "objective",
        "owner_seat_id",
        "input_contract",
        "output_contract",
        "acceptance_criteria",
        "status",
        "resume_state",
        "suspended_attempt_id",
        "suspended_decision_request_id",
        "suspended_at",
        "release_conditions",
        "risk_level",
        "priority",
        "ai_task_id",
        "reviewer_seat_id",
        "lease_owner",
        "lease_expires_at",
        "idempotency_key",
        "version",
        "created_at",
        "updated_at",
    ),
    "rd_work_item_dependencies": (
        "id",
        "collaboration_run_id",
        "plan_version",
        "predecessor_work_item_id",
        "successor_work_item_id",
        "dependency_type",
        "status",
        "satisfied_at",
        "created_at",
        "updated_at",
    ),
    "rd_collaboration_events": (
        "id",
        "collaboration_run_id",
        "event_type",
        "event_key",
        "subject_type",
        "subject_id",
        "payload_json",
        "occurred_at",
        "processed_at",
        "created_at",
        "updated_at",
    ),
}


POLICY_COLUMNS = (
    "id",
    "name",
    "brain_app_id",
    "product_id",
    "task_type",
    "executor_type",
    "runner_id",
    "repository_id",
    "workspace_root",
    "branch",
    "instruction_template",
    "output_contract",
    "timeout_seconds",
    "priority",
    "status",
    "code_change_review_mode",
    "created_by",
    "created_at",
    "updated_at",
)


def _adapt(value: Any, field: str) -> Any:
    if field in JSON_FIELDS and value is not None:
        return Jsonb(value)
    return value


def _row_dict(cursor: Any, row: Sequence[Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        getattr(description, "name", description[0]): value
        for description, value in zip(cursor.description, row, strict=True)
    }


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _response_hash(response: dict[str, Any]) -> str:
    stable = deepcopy(response)
    stable.pop("trace_id", None)
    if isinstance(stable.get("data"), dict):
        stable["data"].pop("idempotent_replay", None)
    stable.pop("idempotent_replay", None)
    return _canonical_hash(stable)


class RdCollaborationWriteRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._upsert_audit_events = upsert_audit_events

    def _insert_record(
        self,
        cursor: Any,
        table_name: str,
        record: dict[str, Any],
        *,
        update_on_conflict: bool,
    ) -> dict[str, Any]:
        allowed = TABLE_COLUMNS[table_name]
        columns = [column for column in allowed if column in record]
        if "id" not in columns:
            raise ValueError(f"{table_name} record requires id")
        assignments = [column for column in columns if column not in {"id", "created_at"}]
        conflict = sql.SQL("DO NOTHING")
        if update_on_conflict and assignments:
            conflict = sql.SQL("DO UPDATE SET {} ").format(
                sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(column),
                        sql.Identifier(column),
                    )
                    for column in assignments
                )
            )
        query = sql.SQL(
            "INSERT INTO {table} ({columns}) VALUES ({values}) "
            "ON CONFLICT (id) {conflict} RETURNING *"
        ).format(
            table=sql.Identifier(table_name),
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            conflict=conflict,
        )
        cursor.execute(query, tuple(_adapt(record[column], column) for column in columns))
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            sql.SQL("SELECT * FROM {} WHERE id = %s").format(sql.Identifier(table_name)),
            (record["id"],),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError(f"failed to persist {table_name} record")
        return existing

    def _save_simple(self, table_name: str, record: dict[str, Any]) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                return self._insert_record(
                    cursor,
                    table_name,
                    record,
                    update_on_conflict=True,
                )

    def save_rd_role_definition_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_role_definitions", record)

    def save_rd_ai_employee_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_ai_employees", record)

    def save_rd_executor_profile_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_executor_profiles", record)

    def save_rd_policy_role_binding_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_task_executor_policy_role_bindings", record)

    def save_rd_task_executor_policy_role_binding_record(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        return self.save_rd_policy_role_binding_record(record)

    def save_rd_run_seat_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_run_seats", record)

    def save_rd_role_session_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_role_sessions", record)

    def save_rd_work_item_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_work_items", record)

    def save_rd_work_item_dependency_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_work_item_dependencies", record)

    def save_rd_collaboration_event_record(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                columns = [
                    column
                    for column in TABLE_COLUMNS["rd_collaboration_events"]
                    if column in record
                ]
                cursor.execute(
                    sql.SQL(
                        "INSERT INTO rd_collaboration_events ({columns}) VALUES ({values}) "
                        "ON CONFLICT (collaboration_run_id, event_key) DO NOTHING RETURNING *"
                    ).format(
                        columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
                        values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                    ),
                    tuple(_adapt(record[column], column) for column in columns),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is not None:
                    return persisted
                cursor.execute(
                    """
                    SELECT * FROM rd_collaboration_events
                    WHERE collaboration_run_id = %s AND event_key = %s
                    """,
                    (record["collaboration_run_id"], record["event_key"]),
                )
                existing = _row_dict(cursor, cursor.fetchone())
                if existing is None:
                    raise RuntimeError("collaboration event replay lookup failed")
                return existing

    def save_rd_task_executor_policy_record(
        self,
        record: dict[str, Any],
        *,
        expected_policy_version: int | None = None,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                brain_app_id = str(record.get("brain_app_id", "rd_brain"))
                product_id = record.get("product_id")
                scope_key = str(product_id) if product_id is not None else "__default__"
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                    (brain_app_id, scope_key),
                )
                cursor.execute(
                    "SELECT * FROM rd_task_executor_policies WHERE id = %s FOR UPDATE",
                    (record["id"],),
                )
                existing = _row_dict(cursor, cursor.fetchone())
                if existing is not None:
                    current_version = int(existing["policy_version"])
                    if (
                        expected_policy_version is not None
                        and current_version != expected_policy_version
                    ):
                        raise RdCollaborationVersionConflictError(current_version)
                    merged = {**existing, **record}
                    next_version = current_version + 1
                else:
                    if expected_policy_version not in (None, 0):
                        raise RdCollaborationVersionConflictError(None)
                    merged = dict(record)
                    next_version = 1
                if merged.get("status", "active") == "active":
                    cursor.execute(
                        """
                        SELECT id
                        FROM rd_task_executor_policies
                        WHERE brain_app_id = %s
                          AND product_id IS NOT DISTINCT FROM %s
                          AND status = 'active'
                          AND id <> %s
                        ORDER BY id
                        LIMIT 1
                        FOR UPDATE
                        """,
                        (brain_app_id, product_id, record["id"]),
                    )
                    duplicate = cursor.fetchone()
                    if duplicate is not None:
                        raise RdCollaborationRepositoryError(
                            "RD_EXECUTION_POLICY_INVALID",
                            "only one active unified policy is allowed for the scope",
                            details={
                                "brain_app_id": brain_app_id,
                                "product_id": product_id,
                                "conflicting_policy_id": duplicate[0],
                            },
                        )
                merged["policy_version"] = next_version
                columns = [column for column in POLICY_COLUMNS if column in merged]
                values = [_adapt(merged[column], column) for column in columns]
                if existing is None:
                    columns.append("policy_version")
                    values.append(next_version)
                    cursor.execute(
                        sql.SQL(
                            "INSERT INTO rd_task_executor_policies ({columns}) "
                            "VALUES ({values}) RETURNING *"
                        ).format(
                            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
                            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                        ),
                        tuple(values),
                    )
                else:
                    update_columns = [column for column in columns if column != "id"]
                    cursor.execute(
                        sql.SQL(
                            "UPDATE rd_task_executor_policies SET {assignments}, "
                            "policy_version = %s, updated_at = now() "
                            "WHERE id = %s RETURNING *"
                        ).format(
                            assignments=sql.SQL(", ").join(
                                sql.SQL("{} = %s").format(sql.Identifier(column))
                                for column in update_columns
                                if column not in {"policy_version", "updated_at"}
                            )
                        ),
                        tuple(
                            _adapt(merged[column], column)
                            for column in update_columns
                            if column not in {"policy_version", "updated_at"}
                        )
                        + (next_version, record["id"]),
                    )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None:
                    raise RuntimeError("policy persistence did not return a row")
                if audit_event is not None:
                    if self._upsert_audit_events is None:
                        raise RuntimeError("audit persistence callback is not configured")
                    self._upsert_audit_events(cursor, [audit_event])
                return persisted

    def _insert_snapshot(self, cursor: Any, snapshot: dict[str, Any]) -> dict[str, Any]:
        cursor.execute(
            """
            SELECT *
            FROM rd_task_executor_policy_snapshots
            WHERE policy_id = %s AND policy_version = %s
              AND snapshot_kind = %s AND resolution_context_key = %s
              AND resolution_revision = %s
            """,
            (
                snapshot["policy_id"],
                snapshot["policy_version"],
                snapshot["snapshot_kind"],
                snapshot["resolution_context_key"],
                snapshot["resolution_revision"],
            ),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is not None:
            if existing["content_hash"] != snapshot["content_hash"]:
                raise RdCollaborationRepositoryError(
                    "RD_POLICY_SNAPSHOT_INVALID",
                    "snapshot identity already exists with a different content hash",
                    details={"snapshot_id": existing["id"]},
                )
            return existing
        columns = (
            "id",
            "policy_id",
            "policy_version",
            "parent_snapshot_id",
            "snapshot_kind",
            "resolution_context_key",
            "resolution_revision",
            "schema_version",
            "content_hash",
            "payload_json",
            "created_by",
            "created_at",
        )
        included = [column for column in columns if column in snapshot]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_task_executor_policy_snapshots ({columns}) "
                "VALUES ({values}) RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(snapshot[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is None:
            raise RuntimeError("snapshot persistence did not return a row")
        return persisted

    def freeze_base_policy_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        if snapshot.get("snapshot_kind") != "base":
            raise ValueError("base snapshot must use snapshot_kind=base")
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM rd_task_executor_policies WHERE id = %s FOR KEY SHARE",
                    (snapshot["policy_id"],),
                )
                return self._insert_snapshot(cursor, snapshot)

    def derive_assessment_policy_snapshot(
        self,
        *,
        base_snapshot_id: str,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM rd_task_executor_policy_snapshots
                    WHERE id = %s FOR KEY SHARE
                    """,
                    (base_snapshot_id,),
                )
                base = _row_dict(cursor, cursor.fetchone())
                if base is None or base["snapshot_kind"] != "base":
                    raise RdCollaborationRepositoryError(
                        "RD_POLICY_SNAPSHOT_INVALID",
                        "assessment base snapshot is missing or invalid",
                    )
                if (
                    snapshot.get("content_hash") == base["content_hash"]
                    or snapshot.get("payload_json") == base["payload_json"]
                ):
                    return base
                if snapshot.get("snapshot_kind") != "assessment_resolved":
                    raise ValueError(
                        "derived assessment snapshot must use snapshot_kind=assessment_resolved"
                    )
                if snapshot.get("parent_snapshot_id") is None:
                    snapshot = {**snapshot, "parent_snapshot_id": base_snapshot_id}
                return self._insert_snapshot(cursor, snapshot)

    def _insert_assessment(
        self,
        cursor: Any,
        assessment: dict[str, Any],
    ) -> dict[str, Any]:
        columns = (
            "id",
            "requirement_id",
            "requirement_revision",
            "initial_strategy_snapshot_id",
            "final_strategy_snapshot_id",
            "strategy_snapshot_id",
            "structured_assessment",
            "completeness_score",
            "risk_summary",
            "dependency_summary",
            "effort_estimate",
            "candidate_version_id",
            "assignment_reason",
            "status",
            "llm_suggestion",
            "deterministic_validation",
            "created_by",
            "decided_by",
            "decided_at",
            "created_at",
            "updated_at",
        )
        included = [column for column in columns if column in assessment]
        cursor.execute(
            sql.SQL(
                "INSERT INTO requirement_assessments ({columns}) VALUES ({values}) "
                "ON CONFLICT (id) DO NOTHING RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(assessment[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            "SELECT * FROM requirement_assessments WHERE id = %s",
            (assessment["id"],),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("assessment persistence did not return a row")
        for field in (
            "requirement_id",
            "requirement_revision",
            "initial_strategy_snapshot_id",
            "final_strategy_snapshot_id",
            "strategy_snapshot_id",
            "status",
        ):
            if field in assessment and existing[field] != assessment[field]:
                raise RdCollaborationRepositoryError(
                    "RD_IDEMPOTENCY_CONFLICT",
                    "assessment id is already bound to different provenance",
                    details={"assessment_id": assessment["id"], "field": field},
                )
        return existing

    def _insert_assessment_opinion(
        self,
        cursor: Any,
        opinion: dict[str, Any],
    ) -> dict[str, Any]:
        columns = (
            "id",
            "assessment_id",
            "role_code",
            "ai_employee_id",
            "executor_profile_id",
            "input_revision",
            "strategy_snapshot_id",
            "opinion_round",
            "conclusion_json",
            "evidence_refs",
            "confidence",
            "risk_summary",
            "cost_summary",
            "created_at",
            "updated_at",
        )
        included = [column for column in columns if column in opinion]
        cursor.execute(
            sql.SQL(
                "INSERT INTO requirement_assessment_opinions ({columns}) "
                "VALUES ({values}) ON CONFLICT (id) DO NOTHING RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(opinion[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            "SELECT * FROM requirement_assessment_opinions WHERE id = %s",
            (opinion["id"],),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("assessment opinion persistence did not return a row")
        return existing

    def save_assessment_bundle(
        self,
        *,
        assessment: dict[str, Any],
        opinions: list[dict[str, Any]],
        snapshots: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                persisted_snapshots = [
                    self._insert_snapshot(cursor, snapshot) for snapshot in (snapshots or [])
                ]
                persisted_assessment = self._insert_assessment(cursor, assessment)
                persisted_opinions = [
                    self._insert_assessment_opinion(cursor, opinion) for opinion in opinions
                ]
                return {
                    "assessment": persisted_assessment,
                    "opinions": persisted_opinions,
                    "snapshots": persisted_snapshots,
                    **persisted_assessment,
                }

    def _insert_snapshot_source(
        self,
        cursor: Any,
        source: dict[str, Any],
    ) -> dict[str, Any]:
        cursor.execute(
            """
            INSERT INTO rd_task_executor_policy_snapshot_sources (
              id, snapshot_id, source_snapshot_id, requirement_id,
              assessment_id, created_at
            )
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()))
            ON CONFLICT (snapshot_id, requirement_id) DO NOTHING
            RETURNING *
            """,
            (
                source["id"],
                source["snapshot_id"],
                source["source_snapshot_id"],
                source["requirement_id"],
                source["assessment_id"],
                source.get("created_at"),
            ),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            """
            SELECT * FROM rd_task_executor_policy_snapshot_sources
            WHERE snapshot_id = %s AND requirement_id = %s
            """,
            (source["snapshot_id"], source["requirement_id"]),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("snapshot source replay lookup failed")
        if (
            existing["source_snapshot_id"] != source["source_snapshot_id"]
            or existing["assessment_id"] != source["assessment_id"]
        ):
            raise RdCollaborationRepositoryError(
                "RD_POLICY_SNAPSHOT_INVALID",
                "snapshot source identity is already bound to different provenance",
            )
        return existing

    def merge_version_policy_snapshot_with_sources(
        self,
        *,
        snapshot: dict[str, Any],
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if snapshot.get("snapshot_kind") != "version_resolved":
            raise ValueError("version merge must persist a version_resolved snapshot")
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                persisted = self._insert_snapshot(cursor, snapshot)
                for source in sorted(sources, key=lambda item: str(item["requirement_id"])):
                    self._insert_snapshot_source(
                        cursor,
                        {**source, "snapshot_id": persisted["id"]},
                    )
                return persisted

    def _insert_run(self, cursor: Any, run: dict[str, Any]) -> dict[str, Any]:
        columns = (
            "id",
            "brain_app_id",
            "product_id",
            "product_version_id",
            "strategy_snapshot_id",
            "run_generation",
            "supersedes_run_id",
            "scope_version",
            "plan_version",
            "status",
            "delivery_target",
            "budget_json",
            "graph_definition",
            "graph_version",
            "resume_state",
            "suspended_decision_request_id",
            "suspended_at",
            "completion_reason",
            "started_at",
            "completed_at",
            "version",
            "created_by",
            "created_at",
            "updated_at",
        )
        included = [column for column in columns if column in run]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_collaboration_runs ({columns}) VALUES ({values}) "
                "ON CONFLICT (id) DO NOTHING RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(run[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute("SELECT * FROM rd_collaboration_runs WHERE id = %s", (run["id"],))
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("collaboration run replay lookup failed")
        for field in (
            "brain_app_id",
            "product_id",
            "product_version_id",
            "strategy_snapshot_id",
            "run_generation",
            "supersedes_run_id",
            "scope_version",
        ):
            if field in run and existing[field] != run[field]:
                raise RdCollaborationRepositoryError(
                    "RD_IDEMPOTENCY_CONFLICT",
                    "run id is already bound to different immutable scope",
                )
        return existing

    def _insert_run_scope(self, cursor: Any, record: dict[str, Any]) -> dict[str, Any]:
        cursor.execute(
            """
            INSERT INTO rd_collaboration_run_requirements (
              id, collaboration_run_id, requirement_id, requirement_revision,
              assessment_id, final_strategy_snapshot_id,
              acceptance_criteria_hash, repository_scope_hash, created_at
            )
            VALUES (
              %s, %s, %s, %s, %s, %s, %s, %s,
              COALESCE(%s::timestamptz, now())
            )
            ON CONFLICT (collaboration_run_id, requirement_id) DO NOTHING
            RETURNING *
            """,
            (
                record["id"],
                record["collaboration_run_id"],
                record["requirement_id"],
                record["requirement_revision"],
                record["assessment_id"],
                record["final_strategy_snapshot_id"],
                record["acceptance_criteria_hash"],
                record["repository_scope_hash"],
                record.get("created_at"),
            ),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            """
            SELECT * FROM rd_collaboration_run_requirements
            WHERE collaboration_run_id = %s AND requirement_id = %s
            """,
            (record["collaboration_run_id"], record["requirement_id"]),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("run scope replay lookup failed")
        return existing

    def create_collaboration_run_with_exact_scope(
        self,
        *,
        run: dict[str, Any],
        scope_rows: list[dict[str, Any]],
        snapshot: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (run["product_version_id"],),
                )
                version = _row_dict(cursor, cursor.fetchone())
                if version is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "product version does not exist",
                    )
                if int(version["scope_version"]) != int(run["scope_version"]):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "scope version is stale",
                        details={"current_scope_version": version["scope_version"]},
                    )
                if snapshot is not None:
                    persisted_snapshot = self._insert_snapshot(cursor, snapshot)
                    for source in sorted(
                        sources or [], key=lambda item: str(item["requirement_id"])
                    ):
                        self._insert_snapshot_source(
                            cursor,
                            {**source, "snapshot_id": persisted_snapshot["id"]},
                        )
                persisted_run = self._insert_run(cursor, run)
                persisted_scope = [
                    self._insert_run_scope(
                        cursor,
                        {**scope, "collaboration_run_id": persisted_run["id"]},
                    )
                    for scope in sorted(
                        scope_rows,
                        key=lambda item: str(item["requirement_id"]),
                    )
                ]
                return {**persisted_run, "run": persisted_run, "scope_rows": persisted_scope}

    def restart_terminal_collaboration_run(
        self,
        *,
        terminal_run_id: str,
        run: dict[str, Any],
        scope_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (run["product_version_id"],),
                )
                version = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                    (terminal_run_id,),
                )
                terminal = _row_dict(cursor, cursor.fetchone())
                if (
                    version is None
                    or terminal is None
                    or terminal["product_version_id"] != run["product_version_id"]
                    or terminal["status"] not in {"failed", "cancelled"}
                    or version["status"] not in {"active", "testing"}
                    or int(terminal["run_generation"]) + 1 != int(run["run_generation"])
                    or run.get("supersedes_run_id") != terminal_run_id
                ):
                    raise RdCollaborationRepositoryError(
                        "RD_RUN_RESTART_NOT_ALLOWED",
                        "terminal collaboration run cannot be restarted",
                    )
                cursor.execute(
                    """
                    SELECT max(run_generation),
                           count(*) FILTER (
                             WHERE status NOT IN ('completed', 'failed', 'cancelled')
                           )
                    FROM rd_collaboration_runs
                    WHERE product_version_id = %s
                    """,
                    (run["product_version_id"],),
                )
                generation_state = cursor.fetchone()
                if (
                    generation_state is None
                    or int(generation_state[0] or 0) != int(terminal["run_generation"])
                    or int(generation_state[1]) != 0
                ):
                    raise RdCollaborationRepositoryError(
                        "RD_RUN_RESTART_NOT_ALLOWED",
                        "terminal run is not the latest generation or an active run exists",
                    )
                persisted = self._insert_run(cursor, run)
                for scope in sorted(scope_rows, key=lambda item: str(item["requirement_id"])):
                    self._insert_run_scope(
                        cursor,
                        {**scope, "collaboration_run_id": persisted["id"]},
                    )
                return persisted

    def assign_requirement_to_version_and_increment_scope(
        self,
        *,
        requirement_id: str,
        product_version_id: str,
        expected_scope_version: int,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (product_version_id,),
                )
                version = _row_dict(cursor, cursor.fetchone())
                if version is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "product version does not exist",
                    )
                cursor.execute(
                    "SELECT * FROM requirements WHERE id = %s FOR UPDATE",
                    (requirement_id,),
                )
                requirement = _row_dict(cursor, cursor.fetchone())
                if requirement is None or requirement["product_id"] != version["product_id"]:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "requirement does not belong to the product version",
                    )
                current_scope = int(version["scope_version"])
                if requirement.get("version_id") == product_version_id:
                    return {**version, "requirement": requirement, "idempotent_replay": True}
                if current_scope != int(expected_scope_version):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "scope version is stale",
                        details={
                            "current_scope_version": current_scope,
                            "retryable": False,
                            "next_action": "reload_version_scope",
                        },
                    )
                if version["status"] in {"ready_for_release", "deploying", "released"}:
                    raise self._ready_scope_frozen()
                cursor.execute(
                    """
                    SELECT id, status, suspended_decision_request_id
                    FROM rd_collaboration_runs
                    WHERE product_version_id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled')
                    ORDER BY run_generation DESC
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (product_version_id,),
                )
                active_run = cursor.fetchone()
                if active_run is not None:
                    details: dict[str, Any] = {
                        "retryable": False,
                        "next_action": "create_scope_change_request",
                    }
                    if active_run[1] == "waiting_human":
                        details.update(
                            {
                                "decision_request_id": active_run[2],
                                "next_action": "resolve_existing_decision",
                            }
                        )
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "product version scope is frozen by an active collaboration run",
                        details=details,
                    )
                if version["status"] != "planning":
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "only a planning product version accepts ordinary scope assignment",
                        details={
                            "retryable": False,
                            "next_action": "create_scope_change_request",
                        },
                    )
                cursor.execute(
                    """
                    UPDATE requirements
                    SET version_id = %s, status = 'planned', updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (product_version_id, requirement_id),
                )
                assigned = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    """
                    UPDATE product_versions
                    SET scope_version = scope_version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (product_version_id,),
                )
                updated_version = _row_dict(cursor, cursor.fetchone())
                if assigned is None or updated_version is None:
                    raise RuntimeError("scope assignment did not return updated rows")
                return {**updated_version, "requirement": assigned, "idempotent_replay": False}

    @staticmethod
    def _ready_scope_frozen() -> RdCollaborationRepositoryError:
        return RdCollaborationRepositoryError(
            "RD_SCOPE_FROZEN",
            "delivered product version scope must move to a new planning version",
            details={
                "retryable": False,
                "resolution": "new_planning_version",
                "next_action": "create_followup_requirement",
            },
        )

    def _insert_decision_request(
        self,
        cursor: Any,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        columns = (
            "id",
            "brain_app_id",
            "product_id",
            "subject_type",
            "subject_id",
            "decision_type",
            "plan_version",
            "options_json",
            "options_hash",
            "evidence_json",
            "recommendation_json",
            "decision_actor_selector",
            "answer_actor_selector",
            "answer_schema",
            "status",
            "selected_option_code",
            "answer_json",
            "decided_by",
            "decided_at",
            "expires_at",
            "timeout_policy",
            "escalation_target_selector",
            "escalation_level",
            "expired_at",
            "expiry_event_id",
            "supersedes_decision_request_id",
            "version",
            "created_by",
            "created_at",
            "updated_at",
        )
        included = [column for column in columns if column in record]
        cursor.execute(
            sql.SQL(
                "INSERT INTO decision_requests ({columns}) VALUES ({values}) "
                "ON CONFLICT (id) DO NOTHING RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(record[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute("SELECT * FROM decision_requests WHERE id = %s", (record["id"],))
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("decision request replay lookup failed")
        return existing

    def save_decision_request_record(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                return self._insert_decision_request(cursor, record)

    @staticmethod
    def _validate_scope_operations(operations: list[dict[str, Any]]) -> None:
        required_fields = {
            "add_requirement": {
                "requirement_id",
                "requirement_revision",
                "assessment_id",
                "final_strategy_snapshot_id",
            },
            "remove_requirement": {"requirement_id", "destination"},
            "replace_requirement_snapshot": {
                "requirement_id",
                "requirement_revision",
                "assessment_id",
                "final_strategy_snapshot_id",
            },
            "update_repository_baseline": {
                "repository_id",
                "branch_config_version",
                "base_commit_sha",
            },
        }
        for index, operation in enumerate(operations):
            kind = operation.get("op")
            required = required_fields.get(str(kind))
            if required is None:
                raise RdCollaborationRepositoryError(
                    "RD_SCOPE_CHANGE_INVALID",
                    "scope change operation kind is invalid",
                    details={"operation_index": index, "field": "op"},
                )
            missing = sorted(field for field in required if operation.get(field) is None)
            if missing:
                raise RdCollaborationRepositoryError(
                    "RD_SCOPE_CHANGE_INVALID",
                    "scope change operation is missing required fields",
                    details={"operation_index": index, "field": missing[0]},
                )

    def _insert_scope_change_request(
        self,
        cursor: Any,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        columns = (
            "id",
            "product_version_id",
            "request_id",
            "source_run_id",
            "source_run_state",
            "expected_scope_version",
            "expected_run_generation",
            "operations_json",
            "operations_hash",
            "reason",
            "status",
            "decision_request_id",
            "applied_scope_version",
            "requested_by",
            "applied_at",
            "created_at",
            "updated_at",
        )
        included = [column for column in columns if column in request]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_scope_change_requests ({columns}) VALUES ({values}) RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(request[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is None:
            raise RuntimeError("scope change request persistence did not return a row")
        return persisted

    def _insert_scope_change_operation(
        self,
        cursor: Any,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        columns = (
            "id",
            "scope_change_request_id",
            "position",
            "op",
            "requirement_id",
            "requirement_revision",
            "assessment_id",
            "final_strategy_snapshot_id",
            "repository_id",
            "branch_config_version",
            "base_commit_sha",
            "destination",
            "created_at",
        )
        included = [column for column in columns if column in record]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_scope_change_request_operations ({columns}) "
                "VALUES ({values}) RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(record[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is None:
            raise RuntimeError("scope change operation persistence did not return a row")
        return persisted

    def create_scope_change_request(
        self,
        *,
        request: dict[str, Any],
        operations: list[dict[str, Any]],
        decision_request: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_scope_operations(operations)
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (request["product_version_id"],),
                )
                version = _row_dict(cursor, cursor.fetchone())
                if version is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "product version does not exist",
                    )
                cursor.execute(
                    "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                    (request["source_run_id"],),
                )
                run = _row_dict(cursor, cursor.fetchone())
                if run is None or run["product_version_id"] != request["product_version_id"]:
                    raise RdCollaborationRepositoryError(
                        "RD_RUN_GENERATION_CONFLICT",
                        "source collaboration run does not belong to the product version",
                    )
                cursor.execute(
                    """
                    SELECT * FROM rd_scope_change_requests
                    WHERE product_version_id = %s AND request_id = %s
                    FOR UPDATE
                    """,
                    (request["product_version_id"], request["request_id"]),
                )
                replay = _row_dict(cursor, cursor.fetchone())
                if replay is not None:
                    if replay["operations_hash"] != request["operations_hash"]:
                        raise RdCollaborationRepositoryError(
                            "RD_IDEMPOTENCY_CONFLICT",
                            "scope request id is already bound to different operations",
                        )
                    return replay
                if version["status"] in {"ready_for_release", "deploying", "released"}:
                    raise self._ready_scope_frozen()
                if (
                    run["status"] == "completed"
                    and run.get("delivery_target") == "ready_for_release"
                ):
                    raise self._ready_scope_frozen()
                if int(version["scope_version"]) != int(request["expected_scope_version"]):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "scope version is stale",
                        details={"current_scope_version": version["scope_version"]},
                    )
                cursor.execute(
                    """
                    SELECT COALESCE(max(run_generation), 0)
                    FROM rd_collaboration_runs
                    WHERE product_version_id = %s
                    """,
                    (request["product_version_id"],),
                )
                current_generation = int(cursor.fetchone()[0])
                if int(run["run_generation"]) != int(
                    request["expected_run_generation"]
                ) or current_generation != int(request["expected_run_generation"]):
                    raise RdCollaborationRepositoryError(
                        "RD_RUN_GENERATION_CONFLICT",
                        "collaboration run generation is stale",
                        details={"current_run_generation": current_generation},
                    )
                if run["status"] == "waiting_human":
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "collaboration run is already paused by another decision",
                        details={
                            "retryable": False,
                            "decision_request_id": run["suspended_decision_request_id"],
                            "next_action": "resolve_existing_decision",
                        },
                    )
                cursor.execute(
                    """
                    SELECT id, decision_request_id
                    FROM rd_scope_change_requests
                    WHERE product_version_id = %s AND status = 'pending_decision'
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (request["product_version_id"],),
                )
                pending = cursor.fetchone()
                if pending is not None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "another scope change decision is already pending",
                        details={
                            "retryable": False,
                            "scope_change_request_id": pending[0],
                            "decision_request_id": pending[1],
                            "next_action": "resolve_existing_decision",
                        },
                    )
                persisted_decision = self._insert_decision_request(cursor, decision_request)
                persisted_request = self._insert_scope_change_request(
                    cursor,
                    {
                        **request,
                        "source_run_state": run["status"],
                        "status": "pending_decision",
                        "decision_request_id": persisted_decision["id"],
                    },
                )
                for index, operation in enumerate(operations):
                    self._insert_scope_change_operation(
                        cursor,
                        {
                            **operation,
                            "scope_change_request_id": persisted_request["id"],
                            "position": operation.get("position", index),
                        },
                    )
                if run["status"] in {"running", "integrating", "verifying"}:
                    cursor.execute(
                        """
                        UPDATE rd_collaboration_runs
                        SET status = 'waiting_human', resume_state = status,
                            suspended_decision_request_id = %s,
                            suspended_at = now(), version = version + 1,
                            updated_at = now()
                        WHERE id = %s
                        """,
                        (persisted_decision["id"], run["id"]),
                    )
                return persisted_request

    def _scope_change_result(
        self,
        cursor: Any,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        cursor.execute(
            "SELECT * FROM product_versions WHERE id = %s",
            (request["product_version_id"],),
        )
        version = _row_dict(cursor, cursor.fetchone())
        cursor.execute(
            "SELECT * FROM rd_collaboration_runs WHERE id = %s",
            (request["source_run_id"],),
        )
        run = _row_dict(cursor, cursor.fetchone())
        cursor.execute(
            "SELECT * FROM decision_requests WHERE id = %s",
            (request["decision_request_id"],),
        )
        decision = _row_dict(cursor, cursor.fetchone())
        return {
            "scope_change_request": request,
            "product_version": version,
            "run": run,
            "decision_request": decision,
            "terminal_run_id": run["id"] if request["status"] == "applied" else None,
            "restart_required": request["status"] == "applied",
        }

    def _apply_scope_operations(
        self,
        cursor: Any,
        *,
        product_id: str,
        product_version_id: str,
        operations: Iterable[dict[str, Any]],
    ) -> None:
        for operation in operations:
            kind = operation["op"]
            if kind in {"add_requirement", "replace_requirement_snapshot"}:
                cursor.execute(
                    """
                    SELECT assessment.id
                    FROM requirement_assessments assessment
                    JOIN requirements requirement
                      ON requirement.id = assessment.requirement_id
                    WHERE assessment.id = %s
                      AND assessment.requirement_id = %s
                      AND assessment.requirement_revision = %s
                      AND assessment.final_strategy_snapshot_id = %s
                      AND assessment.status = 'accepted'
                      AND requirement.product_id = %s
                    FOR KEY SHARE
                    """,
                    (
                        operation["assessment_id"],
                        operation["requirement_id"],
                        operation["requirement_revision"],
                        operation["final_strategy_snapshot_id"],
                        product_id,
                    ),
                )
                if cursor.fetchone() is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "scope operation does not reference the accepted assessment provenance",
                        details={"operation_index": operation["position"]},
                    )
                if kind == "add_requirement":
                    cursor.execute(
                        """
                        UPDATE requirements
                        SET version_id = %s, status = 'planned', updated_at = now()
                        WHERE id = %s
                          AND product_id = %s
                          AND (version_id IS NULL OR version_id = %s)
                        RETURNING id
                        """,
                        (
                            product_version_id,
                            operation["requirement_id"],
                            product_id,
                            product_version_id,
                        ),
                    )
                    if cursor.fetchone() is None:
                        raise RdCollaborationRepositoryError(
                            "RD_SCOPE_CHANGE_INVALID",
                            "requirement cannot be added to this product version",
                            details={"operation_index": operation["position"]},
                        )
            elif kind == "remove_requirement":
                cursor.execute(
                    """
                    UPDATE requirements
                    SET version_id = NULL, status = 'approved', updated_at = now()
                    WHERE id = %s AND product_id = %s AND version_id = %s
                    RETURNING id
                    """,
                    (operation["requirement_id"], product_id, product_version_id),
                )
                if cursor.fetchone() is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "requirement is not in the current product version",
                        details={"operation_index": operation["position"]},
                    )
            elif kind == "update_repository_baseline":
                cursor.execute(
                    """
                    SELECT branch.id, branch.branch_config_version
                    FROM product_version_branch_configs branch
                    JOIN product_git_repositories repository
                      ON repository.id = branch.repository_id
                    WHERE branch.version_id = %s
                      AND branch.repository_id = %s
                      AND branch.product_id = %s
                      AND repository.product_id = %s
                    FOR UPDATE
                    """,
                    (
                        product_version_id,
                        operation["repository_id"],
                        product_id,
                        product_id,
                    ),
                )
                branch = cursor.fetchone()
                if branch is None or int(branch[1]) != int(operation["branch_config_version"]):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "repository baseline branch configuration version is stale",
                        details={"operation_index": operation["position"]},
                    )
                cursor.execute(
                    """
                    UPDATE product_version_branch_configs
                    SET base_commit_sha = %s,
                        branch_config_version = branch_config_version + 1,
                        updated_at = now()
                    WHERE id = %s AND branch_config_version = %s
                    """,
                    (operation["base_commit_sha"], branch[0], operation["branch_config_version"]),
                )

    def apply_scope_change_bundle(
        self,
        *,
        scope_change_request_id: str,
        decision: str,
        decided_by: str,
        expected_decision_version: int,
        cancellation_outbox_events: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if decision not in {"approve", "reject"}:
            raise ValueError("scope change decision must be approve or reject")
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM rd_scope_change_requests WHERE id = %s",
                    (scope_change_request_id,),
                )
                identity = _row_dict(cursor, cursor.fetchone())
                if identity is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "scope change request does not exist",
                    )
                # Global lock order for scope transactions: version -> run -> request -> decision.
                cursor.execute(
                    "SELECT * FROM product_versions WHERE id = %s FOR UPDATE",
                    (identity["product_version_id"],),
                )
                version = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                    (identity["source_run_id"],),
                )
                run = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    "SELECT * FROM rd_scope_change_requests WHERE id = %s FOR UPDATE",
                    (scope_change_request_id,),
                )
                request = _row_dict(cursor, cursor.fetchone())
                if request is None or version is None or run is None:
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_CHANGE_INVALID",
                        "scope change aggregate is incomplete",
                    )
                if request["status"] in {"applied", "rejected"}:
                    return self._scope_change_result(cursor, request)
                cursor.execute(
                    "SELECT * FROM decision_requests WHERE id = %s FOR UPDATE",
                    (request["decision_request_id"],),
                )
                decision_row = _row_dict(cursor, cursor.fetchone())
                if decision_row is None:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "scope change decision request is missing",
                    )
                if int(decision_row["version"]) != int(expected_decision_version):
                    raise RdCollaborationVersionConflictError(int(decision_row["version"]))
                if int(version["scope_version"]) != int(request["expected_scope_version"]) or int(
                    run["run_generation"]
                ) != int(request["expected_run_generation"]):
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_VERSION_CONFLICT",
                        "scope or generation changed before the decision was applied",
                        details={
                            "current_scope_version": version["scope_version"],
                            "current_run_generation": run["run_generation"],
                        },
                    )
                now = datetime.now(UTC)
                if decision == "reject":
                    cursor.execute(
                        """
                        UPDATE decision_requests
                        SET status = 'rejected', selected_option_code = %s,
                            decided_by = %s, decided_at = now(),
                            version = version + 1, updated_at = now()
                        WHERE id = %s
                        """,
                        ("reject_keep_current_scope", decided_by, decision_row["id"]),
                    )
                    cursor.execute(
                        """
                        UPDATE rd_scope_change_requests
                        SET status = 'rejected', updated_at = now()
                        WHERE id = %s
                        RETURNING *
                        """,
                        (request["id"],),
                    )
                    rejected = _row_dict(cursor, cursor.fetchone())
                    if (
                        run["status"] == "waiting_human"
                        and run["suspended_decision_request_id"] == decision_row["id"]
                    ):
                        cursor.execute(
                            """
                            UPDATE rd_collaboration_runs
                            SET status = resume_state, resume_state = NULL,
                                suspended_decision_request_id = NULL,
                                suspended_at = NULL, version = version + 1,
                                updated_at = now()
                            WHERE id = %s
                            """,
                            (run["id"],),
                        )
                    if rejected is None:
                        raise RuntimeError("scope rejection did not return a row")
                    return self._scope_change_result(cursor, rejected)

                cursor.execute(
                    """
                    SELECT * FROM rd_scope_change_request_operations
                    WHERE scope_change_request_id = %s
                    ORDER BY position
                    FOR KEY SHARE
                    """,
                    (request["id"],),
                )
                operations = [_row_dict(cursor, row) for row in cursor.fetchall()]
                cursor.execute(
                    """
                    UPDATE rd_work_item_attempts attempt
                    SET status = 'cancelled', completed_at = COALESCE(completed_at, now()),
                        updated_at = now()
                    FROM rd_work_items item
                    WHERE attempt.work_item_id = item.id
                      AND item.collaboration_run_id = %s
                      AND attempt.status NOT IN ('completed', 'failed', 'cancelled', 'expired')
                    """,
                    (run["id"],),
                )
                cursor.execute(
                    """
                    UPDATE rd_work_items
                    SET status = 'cancelled', lease_owner = NULL, lease_expires_at = NULL,
                        resume_state = NULL, suspended_attempt_id = NULL,
                        suspended_decision_request_id = NULL, suspended_at = NULL,
                        version = version + 1, updated_at = now()
                    WHERE collaboration_run_id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled')
                    """,
                    (run["id"],),
                )
                cursor.execute(
                    """
                    UPDATE human_reviews review
                    SET status = 'cancelled', decision_reason = 'scope_change',
                        decided_by = %s, decided_at = now(), updated_at = now()
                    FROM ai_tasks task
                    WHERE review.ai_task_id = task.id
                      AND task.collaboration_run_id = %s
                      AND review.status = 'pending'
                    """,
                    (decided_by, run["id"]),
                )
                cursor.execute(
                    """
                    UPDATE ai_tasks
                    SET status = 'cancelled', error_code = 'RD_SCOPE_FROZEN',
                        error_message = 'cancelled by approved scope change',
                        updated_at = now()
                    WHERE collaboration_run_id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled')
                    """,
                    (run["id"],),
                )
                cursor.execute(
                    """
                    UPDATE execution_outbox_events
                    SET status = 'cancelled', lease_owner = NULL, lease_until = NULL,
                        updated_at = now()
                    WHERE aggregate_id = %s
                      AND status IN ('pending', 'processing', 'failed')
                    """,
                    (run["id"],),
                )
                for outbox in cancellation_outbox_events or []:
                    cursor.execute(
                        """
                        INSERT INTO execution_outbox_events (
                          id, aggregate_type, aggregate_id, event_type,
                          idempotency_key, payload_json, status, available_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s,
                                COALESCE(%s::timestamptz, now()))
                        ON CONFLICT (idempotency_key) DO NOTHING
                        """,
                        (
                            outbox["id"],
                            outbox["aggregate_type"],
                            outbox["aggregate_id"],
                            outbox["event_type"],
                            outbox["idempotency_key"],
                            Jsonb(outbox.get("payload_json", {})),
                            outbox.get("status", "pending"),
                            outbox.get("available_at"),
                        ),
                    )
                cursor.execute(
                    """
                    UPDATE rd_collaboration_runs
                    SET status = 'cancelled', completion_reason = 'scope_change',
                        completed_at = COALESCE(completed_at, now()),
                        resume_state = NULL, suspended_decision_request_id = NULL,
                        suspended_at = NULL, version = version + 1, updated_at = now()
                    WHERE id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled')
                    """,
                    (run["id"],),
                )
                self._apply_scope_operations(
                    cursor,
                    product_id=run["product_id"],
                    product_version_id=run["product_version_id"],
                    operations=[operation for operation in operations if operation is not None],
                )
                cursor.execute(
                    """
                    UPDATE product_versions
                    SET scope_version = scope_version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING scope_version
                    """,
                    (version["id"],),
                )
                applied_scope_version = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    UPDATE decision_requests
                    SET status = 'approved', selected_option_code = %s,
                        decided_by = %s, decided_at = now(),
                        version = version + 1, updated_at = now()
                    WHERE id = %s
                    """,
                    ("approve_apply_and_restart", decided_by, decision_row["id"]),
                )
                cursor.execute(
                    """
                    UPDATE rd_scope_change_requests
                    SET status = 'applied', applied_scope_version = %s,
                        applied_at = %s, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (applied_scope_version, now, request["id"]),
                )
                applied = _row_dict(cursor, cursor.fetchone())
                if applied is None:
                    raise RuntimeError("scope approval did not return a row")
                return self._scope_change_result(cursor, applied)

    def execute_idempotent_rd_command(
        self,
        *,
        command_type: str,
        aggregate_type: str,
        aggregate_id: str,
        idempotency_key: str,
        request_hash: str,
        operation: Callable[[Any], dict[str, Any]],
        command_record_id: str | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                    (
                        f"{command_type}:{aggregate_type}:{aggregate_id}",
                        idempotency_key,
                    ),
                )
                cursor.execute(
                    """
                    SELECT * FROM rd_command_idempotency_records
                    WHERE command_type = %s AND aggregate_type = %s
                      AND aggregate_id = %s AND idempotency_key = %s
                    """,
                    (command_type, aggregate_type, aggregate_id, idempotency_key),
                )
                existing = _row_dict(cursor, cursor.fetchone())
                if existing is not None:
                    if existing["request_hash"] != request_hash:
                        raise RdCollaborationRepositoryError(
                            "RD_IDEMPOTENCY_CONFLICT",
                            "idempotency key is already bound to a different request hash",
                        )
                    return {
                        "command_record": existing,
                        "http_status": existing["http_status"],
                        "response_json": deepcopy(existing["response_json"]),
                        "idempotent_replay": True,
                    }
                result = operation(cursor)
                response = deepcopy(result["response_json"])
                response_hash = result.get("response_hash") or _response_hash(response)
                record_id = command_record_id or f"rd-command-{uuid4().hex}"
                cursor.execute(
                    """
                    INSERT INTO rd_command_idempotency_records (
                      id, command_type, aggregate_type, aggregate_id,
                      idempotency_key, request_hash, result_type, result_id,
                      http_status, response_hash, response_json, created_at
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      COALESCE(%s::timestamptz, now())
                    )
                    RETURNING *
                    """,
                    (
                        record_id,
                        command_type,
                        aggregate_type,
                        aggregate_id,
                        idempotency_key,
                        request_hash,
                        result["result_type"],
                        result["result_id"],
                        int(result["http_status"]),
                        response_hash,
                        Jsonb(response),
                        result.get("created_at"),
                    ),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None:
                    raise RuntimeError("command idempotency record was not persisted")
                return {
                    "command_record": persisted,
                    "http_status": persisted["http_status"],
                    "response_json": response,
                    "idempotent_replay": False,
                }

    def save_and_scrub_claim_replay_secret(
        self,
        *,
        secret: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                persisted: dict[str, Any] | None = None
                if secret is not None:
                    cursor.execute(
                        """
                        INSERT INTO rd_command_replay_secrets (
                          id, command_record_id, secret_ciphertext, key_id,
                          expires_at, scrubbed_at, created_at, updated_at
                        )
                        VALUES (
                          %s, %s, %s, %s, %s, %s,
                          COALESCE(%s::timestamptz, now()),
                          COALESCE(%s::timestamptz, now())
                        )
                        ON CONFLICT (command_record_id) DO NOTHING
                        RETURNING *
                        """,
                        (
                            secret["id"],
                            secret["command_record_id"],
                            secret.get("secret_ciphertext"),
                            secret["key_id"],
                            secret["expires_at"],
                            secret.get("scrubbed_at"),
                            secret.get("created_at"),
                            secret.get("updated_at") or secret.get("created_at"),
                        ),
                    )
                    persisted = _row_dict(cursor, cursor.fetchone())
                    if persisted is None:
                        cursor.execute(
                            """
                            SELECT * FROM rd_command_replay_secrets
                            WHERE command_record_id = %s
                            """,
                            (secret["command_record_id"],),
                        )
                        persisted = _row_dict(cursor, cursor.fetchone())
                cursor.execute("SELECT scrub_expired_rd_command_replay_secrets()")
                scrubbed_count = int(cursor.fetchone()[0])
                return {"secret": persisted, "scrubbed_count": scrubbed_count}

    def claim_ready_work_item(
        self,
        work_item_id: str,
        *,
        lease_owner: str,
        lease_seconds: int = 900,
        expected_version: int | None = None,
        attempt: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if lease_seconds < 60 or lease_seconds > 1800:
            raise ValueError("lease_seconds must be between 60 and 1800")
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                params: list[Any] = [work_item_id]
                version_clause = ""
                if expected_version is not None:
                    version_clause = "AND item.version = %s"
                    params.append(expected_version)
                params.extend([lease_owner, lease_seconds])
                cursor.execute(
                    f"""
                    WITH candidate AS (
                      SELECT item.id
                      FROM rd_work_items item
                      JOIN rd_collaboration_runs run
                        ON run.id = item.collaboration_run_id
                      WHERE item.id = %s
                        AND item.status = 'ready'
                        AND run.status NOT IN ('completed', 'failed', 'cancelled')
                        {version_clause}
                        AND NOT EXISTS (
                          SELECT 1
                          FROM rd_work_item_dependencies dependency
                          JOIN rd_work_items predecessor
                            ON predecessor.id = dependency.predecessor_work_item_id
                          WHERE dependency.successor_work_item_id = item.id
                            AND dependency.status = 'pending'
                            AND predecessor.status <> 'completed'
                        )
                      FOR UPDATE OF item SKIP LOCKED
                    )
                    UPDATE rd_work_items item
                    SET status = 'claimed', lease_owner = %s,
                        lease_expires_at = now() + (%s * interval '1 second'),
                        version = item.version + 1, updated_at = now()
                    FROM candidate
                    WHERE item.id = candidate.id
                    RETURNING item.*
                    """,  # noqa: S608
                    tuple(params),
                )
                claimed = _row_dict(cursor, cursor.fetchone())
                if claimed is None:
                    return None
                persisted_attempt: dict[str, Any] | None = None
                if attempt is not None:
                    persisted_attempt = self._insert_attempt(cursor, attempt)
                return {**claimed, "work_item": claimed, "attempt": persisted_attempt}

    def _insert_attempt(self, cursor: Any, attempt: dict[str, Any]) -> dict[str, Any]:
        columns = (
            "id",
            "work_item_id",
            "attempt_no",
            "idempotency_key",
            "lease_id",
            "lease_token_hash",
            "status",
            "executor_profile_id",
            "input_json",
            "result_json",
            "failure_json",
            "rework_evidence",
            "claimed_at",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        )
        included = [column for column in columns if column in attempt]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_work_item_attempts ({columns}) VALUES ({values}) "
                "ON CONFLICT (work_item_id, idempotency_key) DO NOTHING RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
            ),
            tuple(_adapt(attempt[column], column) for column in included),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            """
            SELECT * FROM rd_work_item_attempts
            WHERE work_item_id = %s AND idempotency_key = %s
            """,
            (attempt["work_item_id"], attempt["idempotency_key"]),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("attempt replay lookup failed")
        return existing

    def save_work_item_attempt_bundle(
        self,
        *,
        work_item_id: str,
        expected_statuses: list[str],
        next_status: str,
        attempt: dict[str, Any],
        expected_version: int | None = None,
        event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM rd_work_items WHERE id = %s FOR UPDATE",
                    (work_item_id,),
                )
                work_item = _row_dict(cursor, cursor.fetchone())
                if work_item is None or work_item["status"] not in set(expected_statuses):
                    raise RdCollaborationRepositoryError(
                        "RD_WORK_ITEM_STATE_INVALID",
                        "work item is not in an allowed state",
                    )
                if expected_version is not None and int(work_item["version"]) != int(
                    expected_version
                ):
                    raise RdCollaborationVersionConflictError(int(work_item["version"]))
                persisted_attempt = self._insert_attempt(cursor, attempt)
                cursor.execute(
                    """
                    UPDATE rd_work_items
                    SET status = %s, version = version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (next_status, work_item_id),
                )
                persisted_work_item = _row_dict(cursor, cursor.fetchone())
                persisted_event = None
                if event is not None:
                    persisted_event = self._insert_event_cursor(cursor, event)
                if persisted_work_item is None:
                    raise RuntimeError("work item attempt bundle did not update work item")
                return {
                    "work_item": persisted_work_item,
                    "attempt": persisted_attempt,
                    "event": persisted_event,
                }

    def _insert_event_cursor(self, cursor: Any, event: dict[str, Any]) -> dict[str, Any]:
        columns = [column for column in TABLE_COLUMNS["rd_collaboration_events"] if column in event]
        cursor.execute(
            sql.SQL(
                "INSERT INTO rd_collaboration_events ({columns}) VALUES ({values}) "
                "ON CONFLICT (collaboration_run_id, event_key) DO NOTHING RETURNING *"
            ).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
                values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            ),
            tuple(_adapt(event[column], column) for column in columns),
        )
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            """
            SELECT * FROM rd_collaboration_events
            WHERE collaboration_run_id = %s AND event_key = %s
            """,
            (event["collaboration_run_id"], event["event_key"]),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("event replay lookup failed")
        return existing

    def cancel_work_item_bundle(
        self,
        *,
        work_item_id: str,
        expected_version: int,
        high_risk: bool,
        decision_request: dict[str, Any] | None = None,
        event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM rd_work_items WHERE id = %s FOR UPDATE",
                    (work_item_id,),
                )
                work_item = _row_dict(cursor, cursor.fetchone())
                if work_item is None or work_item["status"] in {
                    "completed",
                    "failed",
                    "cancelled",
                }:
                    raise RdCollaborationRepositoryError(
                        "RD_WORK_ITEM_STATE_INVALID",
                        "work item cannot be cancelled from its current state",
                    )
                if int(work_item["version"]) != int(expected_version):
                    raise RdCollaborationVersionConflictError(int(work_item["version"]))
                cursor.execute(
                    """
                    SELECT * FROM rd_work_item_attempts
                    WHERE work_item_id = %s
                      AND status NOT IN ('completed', 'failed', 'cancelled', 'expired')
                    ORDER BY attempt_no DESC
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (work_item_id,),
                )
                attempt = _row_dict(cursor, cursor.fetchone())
                persisted_decision = None
                if high_risk:
                    if decision_request is None:
                        raise RdCollaborationRepositoryError(
                            "RD_DECISION_REQUIRED",
                            "high-risk cancellation requires a decision request",
                        )
                    persisted_decision = self._insert_decision_request(cursor, decision_request)
                    if attempt is not None:
                        cursor.execute(
                            """
                            UPDATE rd_work_item_attempts
                            SET status = 'waiting_human', updated_at = now()
                            WHERE id = %s
                            RETURNING *
                            """,
                            (attempt["id"],),
                        )
                        attempt = _row_dict(cursor, cursor.fetchone())
                    cursor.execute(
                        """
                        UPDATE rd_work_items
                        SET status = 'waiting_human', resume_state = 'ready',
                            suspended_attempt_id = %s,
                            suspended_decision_request_id = %s,
                            suspended_at = now(), lease_owner = NULL,
                            lease_expires_at = NULL, version = version + 1,
                            updated_at = now()
                        WHERE id = %s
                        RETURNING *
                        """,
                        (
                            attempt["id"] if attempt else None,
                            persisted_decision["id"],
                            work_item_id,
                        ),
                    )
                else:
                    if attempt is not None:
                        cursor.execute(
                            """
                            UPDATE rd_work_item_attempts
                            SET status = 'cancelled', completed_at = COALESCE(completed_at, now()),
                                updated_at = now()
                            WHERE id = %s
                            RETURNING *
                            """,
                            (attempt["id"],),
                        )
                        attempt = _row_dict(cursor, cursor.fetchone())
                    cursor.execute(
                        """
                        UPDATE rd_work_items
                        SET status = 'cancelled', lease_owner = NULL,
                            lease_expires_at = NULL, resume_state = NULL,
                            suspended_attempt_id = NULL,
                            suspended_decision_request_id = NULL,
                            suspended_at = NULL, version = version + 1,
                            updated_at = now()
                        WHERE id = %s
                        RETURNING *
                        """,
                        (work_item_id,),
                    )
                persisted_work_item = _row_dict(cursor, cursor.fetchone())
                persisted_event = self._insert_event_cursor(cursor, event) if event else None
                if persisted_work_item is None:
                    raise RuntimeError("work item cancellation did not return a row")
                return {
                    "work_item": persisted_work_item,
                    "attempt": attempt,
                    "decision_request": persisted_decision,
                    "event": persisted_event,
                }

    def suspend_collaboration_run(
        self,
        *,
        collaboration_run_id: str,
        decision_request_id: str,
        expected_version: int,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                    (collaboration_run_id,),
                )
                run = _row_dict(cursor, cursor.fetchone())
                if run is None:
                    raise RdCollaborationRepositoryError(
                        "RD_WORK_ITEM_STATE_INVALID",
                        "collaboration run does not exist",
                    )
                if int(run["version"]) != int(expected_version):
                    raise RdCollaborationVersionConflictError(int(run["version"]))
                if run["status"] == "waiting_human":
                    if run["suspended_decision_request_id"] == decision_request_id:
                        return run
                    raise RdCollaborationRepositoryError(
                        "RD_SCOPE_FROZEN",
                        "collaboration run is already paused",
                    )
                if run["status"] not in {"running", "integrating", "verifying"}:
                    raise RdCollaborationRepositoryError(
                        "RD_WORK_ITEM_STATE_INVALID",
                        "collaboration run cannot be suspended from its current state",
                    )
                cursor.execute(
                    "SELECT id FROM decision_requests WHERE id = %s FOR KEY SHARE",
                    (decision_request_id,),
                )
                if cursor.fetchone() is None:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "decision request does not exist",
                    )
                cursor.execute(
                    """
                    UPDATE rd_collaboration_runs
                    SET status = 'waiting_human', resume_state = %s,
                        suspended_decision_request_id = %s,
                        suspended_at = now(), version = version + 1,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (run["status"], decision_request_id, collaboration_run_id),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None:
                    raise RuntimeError("run suspension did not return a row")
                return persisted

    @staticmethod
    def _matches_schema_type(value: Any, schema_type: str) -> bool:
        checks = {
            "array": lambda item: isinstance(item, list),
            "boolean": lambda item: isinstance(item, bool),
            "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
            "null": lambda item: item is None,
            "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
            "object": lambda item: isinstance(item, dict),
            "string": lambda item: isinstance(item, str),
        }
        check = checks.get(schema_type)
        return bool(check and check(value))

    @classmethod
    def _validate_structured_input(
        cls,
        value: Any,
        schema: dict[str, Any] | None,
        *,
        field: str,
    ) -> None:
        effective = schema or {}
        if not effective:
            if value not in (None, {}):
                raise RdCollaborationRepositoryError(
                    "RD_DECISION_INPUT_INVALID",
                    f"{field} is not allowed for the selected option",
                    details={"field": field},
                )
            return
        schema_type = effective.get("type")
        if schema_type and not cls._matches_schema_type(value, str(schema_type)):
            raise RdCollaborationRepositoryError(
                "RD_DECISION_INPUT_INVALID",
                f"{field} does not match the frozen schema type",
                details={"field": field, "expected_type": schema_type},
            )
        if "enum" in effective and value not in effective["enum"]:
            raise RdCollaborationRepositoryError(
                "RD_DECISION_INPUT_INVALID",
                f"{field} is not one of the frozen enum values",
                details={"field": field},
            )
        if isinstance(value, dict):
            properties = effective.get("properties") or {}
            missing = [key for key in effective.get("required", []) if key not in value]
            extras = [key for key in value if key not in properties]
            if missing or (effective.get("additionalProperties") is False and extras):
                raise RdCollaborationRepositoryError(
                    "RD_DECISION_INPUT_INVALID",
                    f"{field} does not match required frozen fields",
                    details={
                        "field": field,
                        "missing": missing,
                        "additional": extras,
                    },
                )
            for key, item in value.items():
                if key in properties:
                    cls._validate_structured_input(
                        item,
                        properties[key],
                        field=f"{field}.{key}",
                    )
        if isinstance(value, list) and isinstance(effective.get("items"), dict):
            for index, item in enumerate(value):
                cls._validate_structured_input(
                    item,
                    effective["items"],
                    field=f"{field}[{index}]",
                )

    def apply_decision_bundle(
        self,
        *,
        decision_request_id: str,
        selected_option_code: str,
        input_json: Any,
        comment: str | None,
        decided_by: str,
        expected_version: int,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM decision_requests WHERE id = %s FOR UPDATE",
                    (decision_request_id,),
                )
                decision = _row_dict(cursor, cursor.fetchone())
                if decision is None:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_EXPIRED",
                        "decision request does not exist",
                    )
                if int(decision["version"]) != int(expected_version):
                    raise RdCollaborationVersionConflictError(int(decision["version"]))
                if decision["status"] not in {"pending", "waiting_more_info"}:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_EXPIRED",
                        "decision request is no longer active",
                    )
                cursor.execute("SELECT now() >= %s", (decision["expires_at"],))
                if bool(cursor.fetchone()[0]):
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_EXPIRED",
                        "decision request has expired according to database time",
                    )
                option = next(
                    (
                        item
                        for item in decision["options_json"] or []
                        if item.get("code") == selected_option_code
                    ),
                    None,
                )
                if option is None:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_INPUT_INVALID",
                        "selected option is not in the frozen option set",
                        details={"field": "selected_option"},
                    )
                self._validate_structured_input(
                    input_json,
                    option.get("input_schema"),
                    field="input",
                )
                if option.get("requires_comment") and not str(comment or "").strip():
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_INPUT_INVALID",
                        "selected option requires a comment",
                        details={"field": "comment"},
                    )
                outcome = option.get("outcome")
                status_by_outcome = {
                    "approve": "approved",
                    "reject": "rejected",
                    "request_more_info": "waiting_more_info",
                }
                next_status = status_by_outcome.get(str(outcome))
                if next_status is None:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_INPUT_INVALID",
                        "frozen decision outcome is invalid",
                    )
                cursor.execute(
                    """
                    UPDATE decision_requests
                    SET status = %s, selected_option_code = %s,
                        answer_json = %s, decided_by = %s,
                        decided_at = CASE WHEN %s = 'waiting_more_info' THEN NULL ELSE now() END,
                        version = version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        next_status,
                        selected_option_code,
                        Jsonb({"input": input_json, "comment": comment}),
                        decided_by,
                        next_status,
                        decision_request_id,
                    ),
                )
                persisted_decision = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    """
                    SELECT * FROM rd_collaboration_runs
                    WHERE suspended_decision_request_id = %s
                    FOR UPDATE
                    """,
                    (decision_request_id,),
                )
                run = _row_dict(cursor, cursor.fetchone())
                if next_status != "waiting_more_info" and run is not None:
                    transition = option.get("subject_transition")
                    if transition in {"resume", "continue", None}:
                        target_status = run["resume_state"]
                    elif transition in {"cancelled", "failed"}:
                        target_status = transition
                    else:
                        target_status = run["resume_state"]
                    cursor.execute(
                        """
                        UPDATE rd_collaboration_runs
                        SET status = %s, resume_state = NULL,
                            suspended_decision_request_id = NULL,
                            suspended_at = NULL, version = version + 1,
                            completion_reason = CASE
                              WHEN %s IN ('cancelled', 'failed') THEN 'decision'
                              ELSE completion_reason
                            END,
                            completed_at = CASE
                              WHEN %s IN ('cancelled', 'failed') THEN now()
                              ELSE completed_at
                            END,
                            updated_at = now()
                        WHERE id = %s
                        RETURNING *
                        """,
                        (target_status, target_status, target_status, run["id"]),
                    )
                    run = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    """
                    SELECT * FROM rd_work_items
                    WHERE suspended_decision_request_id = %s
                    FOR UPDATE
                    """,
                    (decision_request_id,),
                )
                work_item = _row_dict(cursor, cursor.fetchone())
                suspended_attempt = None
                if next_status != "waiting_more_info" and work_item is not None:
                    transition = option.get("subject_transition")
                    target_status = (
                        transition
                        if transition in {"ready", "completed", "failed", "cancelled"}
                        else work_item["resume_state"]
                    )
                    if work_item["suspended_attempt_id"] is not None:
                        cursor.execute(
                            """
                            SELECT * FROM rd_work_item_attempts
                            WHERE id = %s FOR UPDATE
                            """,
                            (work_item["suspended_attempt_id"],),
                        )
                        suspended_attempt = _row_dict(cursor, cursor.fetchone())
                    if (
                        suspended_attempt is not None
                        and target_status in {"ready", "failed", "cancelled"}
                        and suspended_attempt["status"]
                        not in {"completed", "failed", "cancelled", "expired"}
                    ):
                        cursor.execute(
                            """
                            UPDATE rd_work_item_attempts
                            SET status = 'cancelled',
                                completed_at = COALESCE(completed_at, now()),
                                updated_at = now()
                            WHERE id = %s
                            RETURNING *
                            """,
                            (suspended_attempt["id"],),
                        )
                        suspended_attempt = _row_dict(cursor, cursor.fetchone())
                    cursor.execute(
                        """
                        UPDATE rd_work_items
                        SET status = %s, resume_state = NULL,
                            suspended_attempt_id = NULL,
                            suspended_decision_request_id = NULL,
                            suspended_at = NULL, version = version + 1,
                            updated_at = now()
                        WHERE id = %s
                        RETURNING *
                        """,
                        (target_status, work_item["id"]),
                    )
                    work_item = _row_dict(cursor, cursor.fetchone())
                if persisted_decision is None:
                    raise RuntimeError("decision application did not return a row")
                return {
                    "decision_request": persisted_decision,
                    "run": run,
                    "work_item": work_item,
                    "attempt": suspended_attempt,
                    "next_state": next_status,
                }

    @staticmethod
    def _selector_matches(
        selector: dict[str, Any],
        *,
        actor_id: str,
        actor_role_codes: list[str],
        actor_seat_ids: list[str],
    ) -> bool:
        user_ids = {str(item) for item in selector.get("user_ids", [])}
        role_codes = {str(item) for item in selector.get("role_codes", [])}
        seat_ids = {str(item) for item in selector.get("seat_ids", [])}
        return bool(
            (actor_id in user_ids)
            or role_codes.intersection(actor_role_codes)
            or seat_ids.intersection(actor_seat_ids)
        )

    def answer_decision_request(
        self,
        *,
        decision_request_id: str,
        expected_version: int,
        actor_id: str,
        actor_role_codes: list[str],
        actor_seat_ids: list[str],
        answer_json: Any,
        evidence_json: list[Any],
        options_json: list[dict[str, Any]],
        options_hash: str,
    ) -> dict[str, Any]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM decision_requests WHERE id = %s FOR UPDATE",
                    (decision_request_id,),
                )
                decision = _row_dict(cursor, cursor.fetchone())
                if decision is None or decision["status"] != "waiting_more_info":
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_EXPIRED",
                        "decision request is not waiting for more information",
                    )
                if int(decision["version"]) != int(expected_version):
                    raise RdCollaborationVersionConflictError(int(decision["version"]))
                cursor.execute("SELECT now() >= %s", (decision["expires_at"],))
                if bool(cursor.fetchone()[0]):
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_EXPIRED",
                        "decision request has expired according to database time",
                    )
                if not self._selector_matches(
                    decision["answer_actor_selector"] or {},
                    actor_id=actor_id,
                    actor_role_codes=actor_role_codes,
                    actor_seat_ids=actor_seat_ids,
                ):
                    raise RdCollaborationRepositoryError(
                        "PERMISSION_DENIED",
                        "answer actor does not match the frozen selector",
                    )
                self._validate_structured_input(
                    answer_json,
                    decision["answer_schema"] or {},
                    field="answer",
                )
                combined_evidence = list(decision["evidence_json"] or []) + list(evidence_json)
                cursor.execute(
                    """
                    UPDATE decision_requests
                    SET status = 'pending', answer_json = %s,
                        evidence_json = %s, options_json = %s,
                        options_hash = %s, selected_option_code = NULL,
                        decided_by = NULL, decided_at = NULL,
                        version = version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (
                        Jsonb(answer_json),
                        Jsonb(combined_evidence),
                        Jsonb(options_json),
                        options_hash,
                        decision_request_id,
                    ),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None:
                    raise RuntimeError("decision answer did not return a row")
                return persisted

    def expire_and_escalate_decision_request(
        self,
        *,
        decision_request_id: str,
        successor_request: dict[str, Any],
        expiry_event: dict[str, Any],
    ) -> dict[str, Any] | None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM decision_requests WHERE id = %s FOR UPDATE",
                    (decision_request_id,),
                )
                decision = _row_dict(cursor, cursor.fetchone())
                if decision is None:
                    return None
                if decision["status"] == "expired":
                    cursor.execute(
                        """
                        SELECT * FROM decision_requests
                        WHERE supersedes_decision_request_id = %s
                        """,
                        (decision_request_id,),
                    )
                    successor = _row_dict(cursor, cursor.fetchone())
                    return {
                        "expired_request": decision,
                        "successor_request": successor,
                    }
                if decision["status"] not in {"pending", "waiting_more_info"}:
                    return None
                cursor.execute("SELECT now() >= %s", (decision["expires_at"],))
                if not bool(cursor.fetchone()[0]):
                    return None
                event = self._insert_event_cursor(cursor, expiry_event)
                cursor.execute(
                    """
                    UPDATE decision_requests
                    SET status = 'expired', expired_at = now(),
                        expiry_event_id = %s, version = version + 1,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (event["id"], decision_request_id),
                )
                expired = _row_dict(cursor, cursor.fetchone())
                successor = self._insert_decision_request(cursor, successor_request)
                cursor.execute(
                    """
                    UPDATE rd_collaboration_runs
                    SET suspended_decision_request_id = %s,
                        version = version + 1, updated_at = now()
                    WHERE suspended_decision_request_id = %s
                    """,
                    (successor["id"], decision_request_id),
                )
                cursor.execute(
                    """
                    UPDATE rd_work_items
                    SET suspended_decision_request_id = %s,
                        version = version + 1, updated_at = now()
                    WHERE suspended_decision_request_id = %s
                    """,
                    (successor["id"], decision_request_id),
                )
                return {
                    "expired_request": expired,
                    "successor_request": successor,
                    "expiry_event": event,
                }

    def save_role_feedback_once(self, record: dict[str, Any]) -> dict[str, Any]:
        """Insert one immutable feedback fact per run/fingerprint."""
        columns = (
            "id",
            "brain_app_id",
            "product_id",
            "collaboration_run_id",
            "feedback_kind",
            "source_event_id",
            "feedback_fingerprint",
            "role_code",
            "seat_id",
            "human_user_id",
            "ai_employee_id",
            "executor_profile_id",
            "work_item_id",
            "attempt_id",
            "strategy_snapshot_id",
            "evidence_refs",
            "producer_subject_type",
            "producer_subject_id",
            "producer_role_code",
            "producer_seat_id",
            "created_at",
        )
        included = [column for column in columns if column in record]
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL(
                        "INSERT INTO role_feedback_records ({columns}) VALUES ({values}) "
                        "ON CONFLICT (collaboration_run_id, feedback_fingerprint) "
                        "DO NOTHING RETURNING *"
                    ).format(
                        columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                        values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
                    ),
                    tuple(_adapt(record[column], column) for column in included),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is not None:
                    return persisted
                cursor.execute(
                    """
                    SELECT * FROM role_feedback_records
                    WHERE collaboration_run_id = %s AND feedback_fingerprint = %s
                    """,
                    (record["collaboration_run_id"], record["feedback_fingerprint"]),
                )
                existing = _row_dict(cursor, cursor.fetchone())
                if existing is None:
                    raise RuntimeError("feedback replay lookup failed")
                return existing

    def save_rd_role_experience_record(
        self,
        record: dict[str, Any],
        *,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Append a versioned experience candidate and its immutable provenance."""
        columns = (
            "id",
            "experience_key",
            "version",
            "brain_app_id",
            "product_scope",
            "role_code",
            "work_item_type",
            "scenario",
            "risk_scope",
            "repository_trust_domains",
            "tool_trust_domains",
            "content",
            "evidence_refs",
            "strategy_snapshot_id",
            "confidence",
            "status",
            "review_version",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
        source_columns = (
            "id",
            "experience_id",
            "role_feedback_record_id",
            "strategy_snapshot_id",
            "created_at",
            "updated_at",
        )
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (record["experience_key"],),
                )
                cursor.execute(
                    "SELECT * FROM rd_role_experience_records WHERE id = %s",
                    (record["id"],),
                )
                existing = _row_dict(cursor, cursor.fetchone())
                if existing is not None:
                    return existing
                cursor.execute(
                    """
                    SELECT COALESCE(MAX(version), 0) + 1
                    FROM rd_role_experience_records
                    WHERE experience_key = %s
                    """,
                    (record["experience_key"],),
                )
                version = int(cursor.fetchone()[0])
                candidate = {**record, "version": version}
                included = [column for column in columns if column in candidate]
                cursor.execute(
                    sql.SQL(
                        "INSERT INTO rd_role_experience_records ({columns}) "
                        "VALUES ({values}) RETURNING *"
                    ).format(
                        columns=sql.SQL(", ").join(map(sql.Identifier, included)),
                        values=sql.SQL(", ").join(sql.Placeholder() for _ in included),
                    ),
                    tuple(_adapt(candidate[column], column) for column in included),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None:
                    raise RuntimeError("experience persistence did not return a row")
                for source in sources:
                    if source.get("experience_id") != persisted["id"]:
                        raise RdCollaborationRepositoryError(
                            "RD_EXPERIENCE_INVALID",
                            "experience source must reference the candidate being created",
                        )
                    included_source = [column for column in source_columns if column in source]
                    cursor.execute(
                        sql.SQL(
                            "INSERT INTO rd_role_experience_sources ({columns}) VALUES ({values})"
                        ).format(
                            columns=sql.SQL(", ").join(map(sql.Identifier, included_source)),
                            values=sql.SQL(", ").join(sql.Placeholder() for _ in included_source),
                        ),
                        tuple(_adapt(source[column], column) for column in included_source),
                    )
                return persisted

    def decide_role_experience(
        self,
        *,
        experience_id: str,
        decision: str,
        expected_review_version: int,
        reviewer_subject_type: str,
        reviewer_subject_id: str,
        reviewer_role_code: str | None,
        reviewer_seat_id: str | None,
        require_independent_reviewer: bool,
    ) -> dict[str, Any]:
        status_by_decision = {
            "approve": "approved",
            "reject": "rejected",
            "retire": "retired",
        }
        next_status = status_by_decision.get(decision)
        if next_status is None or reviewer_subject_type != "human_user":
            raise RdCollaborationRepositoryError(
                "RD_EXPERIENCE_INVALID",
                "experience decision and reviewer identity must be valid",
            )
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM rd_role_experience_records
                    WHERE id = %s FOR UPDATE
                    """,
                    (experience_id,),
                )
                experience = _row_dict(cursor, cursor.fetchone())
                if experience is None:
                    raise RdCollaborationRepositoryError(
                        "RD_EXPERIENCE_INVALID",
                        "experience candidate does not exist",
                    )
                current_review_version = int(experience["review_version"])
                if current_review_version != int(expected_review_version):
                    raise RdCollaborationVersionConflictError(current_review_version)
                cursor.execute(
                    """
                    SELECT feedback.producer_subject_type,
                           feedback.producer_subject_id,
                           feedback.producer_role_code,
                           feedback.producer_seat_id
                    FROM rd_role_experience_sources source
                    JOIN role_feedback_records feedback
                      ON feedback.id = source.role_feedback_record_id
                    WHERE source.experience_id = %s
                    """,
                    (experience_id,),
                )
                producers = cursor.fetchall()
                same_subject = any(
                    producer[0] == reviewer_subject_type and producer[1] == reviewer_subject_id
                    for producer in producers
                )
                same_frozen_role_or_seat = require_independent_reviewer and any(
                    (reviewer_role_code is not None and producer[2] == reviewer_role_code)
                    or (reviewer_seat_id is not None and producer[3] == reviewer_seat_id)
                    for producer in producers
                )
                if same_subject or same_frozen_role_or_seat:
                    raise RdCollaborationRepositoryError(
                        "PERMISSION_DENIED",
                        "feedback producer cannot review its derived experience",
                    )
                cursor.execute(
                    """
                    UPDATE rd_role_experience_records
                    SET status = %s, reviewed_by = %s, reviewed_at = now(),
                        review_version = review_version + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (next_status, reviewer_subject_id, experience_id),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None:
                    raise RuntimeError("experience decision did not return a row")
                return persisted
