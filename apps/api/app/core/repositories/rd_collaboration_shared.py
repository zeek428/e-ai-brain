from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from contextlib import AbstractContextManager
from copy import deepcopy
from typing import Any

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
    "autonomy_mode",
    "max_iterations",
    "max_duration_seconds",
    "token_budget",
    "cost_budget",
    "quality_gate_policy_id",
    "auto_merge_risk_threshold",
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


SCOPE_OPERATION_FIELDS: dict[str, tuple[str, ...]] = {
    "add_requirement": (
        "requirement_id",
        "requirement_revision",
        "assessment_id",
        "final_strategy_snapshot_id",
    ),
    "remove_requirement": ("requirement_id", "destination"),
    "replace_requirement_snapshot": (
        "requirement_id",
        "requirement_revision",
        "assessment_id",
        "final_strategy_snapshot_id",
    ),
    "update_repository_baseline": (
        "repository_id",
        "branch_config_version",
        "base_commit_sha",
    ),
}


def _canonical_scope_operations(operations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for position, operation in enumerate(operations):
        kind = str(operation.get("op") or "")
        fields = SCOPE_OPERATION_FIELDS.get(kind)
        if fields is None:
            raise RdCollaborationRepositoryError(
                "RD_SCOPE_CHANGE_INVALID",
                "scope change operation kind is invalid",
                details={"operation_index": position, "field": "op"},
            )
        missing = [field for field in fields if operation.get(field) is None]
        if missing:
            raise RdCollaborationRepositoryError(
                "RD_SCOPE_CHANGE_INVALID",
                "scope change operation is missing required fields",
                details={"operation_index": position, "field": missing[0]},
            )
        if kind == "remove_requirement" and operation.get("destination") != "approved_pool":
            raise RdCollaborationRepositoryError(
                "RD_SCOPE_CHANGE_INVALID",
                "removed requirements must return to the approved pool",
                details={"operation_index": position, "field": "destination"},
            )
        canonical.append(
            {
                "position": position,
                "op": kind,
                **{field: operation[field] for field in fields},
            }
        )
    return canonical


class RdCollaborationTransaction:
    """One cursor shared by a command and every collaboration side effect."""

    def __init__(self, repository: Any, cursor: Any) -> None:
        self._repository = repository
        self.cursor = cursor

    def __getattr__(self, name: str) -> Any:
        # Keep raw cursor operations available to existing command callbacks while
        # giving orchestrators explicit cursor-level domain methods.
        return getattr(self.cursor, name)

    def claim_ready_work_item(
        self,
        work_item_id: str,
        *,
        lease_owner: str,
        lease_seconds: int = 900,
        expected_version: int | None = None,
        attempt: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self._repository._claim_ready_work_item_cursor(
            self.cursor,
            work_item_id,
            lease_owner=lease_owner,
            lease_seconds=lease_seconds,
            expected_version=expected_version,
            attempt=attempt,
        )

    def save_collaboration_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return self._repository._insert_event_cursor(self.cursor, event)

    def save_outbox_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self.cursor.execute(
            """
            INSERT INTO execution_outbox_events (
              id, aggregate_type, aggregate_id, event_type,
              idempotency_key, payload_json, status, available_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s,
                    COALESCE(%s::timestamptz, now()))
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING *
            """,
            (
                event["id"],
                event["aggregate_type"],
                event["aggregate_id"],
                event["event_type"],
                event["idempotency_key"],
                Jsonb(event.get("payload_json", {})),
                event.get("status", "pending"),
                event.get("available_at"),
            ),
        )
        persisted = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if persisted is not None:
            return persisted
        self.cursor.execute(
            "SELECT * FROM execution_outbox_events WHERE idempotency_key = %s",
            (event["idempotency_key"],),
        )
        existing = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if existing is None:
            raise RuntimeError("outbox replay lookup failed")
        for field in ("aggregate_type", "aggregate_id", "event_type", "payload_json"):
            expected = event.get(field, {} if field == "payload_json" else None)
            if existing[field] != expected:
                raise self._repository._idempotency_conflict(
                    "outbox idempotency key is bound to different provenance",
                    field=field,
                )
        return existing

    def save_audit_event(self, event: dict[str, Any]) -> None:
        callback: Callable[[Any, list[dict[str, Any]]], None] | None = (
            self._repository._upsert_audit_events
        )
        if callback is None:
            raise RuntimeError("audit persistence callback is not configured")
        callback(self.cursor, [event])


class RdCollaborationWriteBase:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._upsert_audit_events = upsert_audit_events

    @staticmethod
    def _row(*, cursor: Any, row: Sequence[Any] | None) -> dict[str, Any] | None:
        return _row_dict(cursor, row)

    @staticmethod
    def _idempotency_conflict(message: str, **details: Any) -> RdCollaborationRepositoryError:
        return RdCollaborationRepositoryError(
            "RD_IDEMPOTENCY_CONFLICT",
            message,
            details=details,
        )

    def _assert_immutable_replay(
        self,
        *,
        existing: dict[str, Any],
        incoming: dict[str, Any],
        fields: Iterable[str],
        message: str,
        **details: Any,
    ) -> None:
        """Reject an idempotent replay that changes immutable creation data."""
        for field in fields:
            if field in incoming and existing[field] != incoming[field]:
                raise self._idempotency_conflict(message, field=field, **details)

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
