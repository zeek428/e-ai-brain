from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from typing import Any

from psycopg import sql

from app.core.repositories.rd_collaboration_writes import (
    RdCollaborationRepositoryError,
    RdCollaborationVersionConflictError,
    RdCollaborationWriteRepository,
)

__all__ = [
    "RdCollaborationReadRepository",
    "RdCollaborationRepositoryError",
    "RdCollaborationVersionConflictError",
]


def _row_dict(cursor: Any, row: Sequence[Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        getattr(description, "name", description[0]): value
        for description, value in zip(cursor.description, row, strict=True)
    }


class RdCollaborationReadRepository(RdCollaborationWriteRepository):
    """Focused PostgreSQL repository for requirement-driven collaboration state."""

    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        super().__init__(connect, upsert_audit_events=upsert_audit_events)

    def _get(self, table_name: str, record_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("SELECT * FROM {} WHERE id = %s").format(sql.Identifier(table_name)),
                    (record_id,),
                )
                return _row_dict(cursor, cursor.fetchone())

    def _list(
        self,
        table_name: str,
        *,
        filters: dict[str, Any] | None = None,
        order_by: tuple[str, ...] = ("created_at", "id"),
    ) -> list[dict[str, Any]]:
        effective_filters = filters or {}
        predicates = [
            sql.SQL("{} = %s").format(sql.Identifier(column)) for column in effective_filters
        ]
        where = (
            sql.SQL(" WHERE ") + sql.SQL(" AND ").join(predicates) if predicates else sql.SQL("")
        )
        ordering = sql.SQL(", ").join(map(sql.Identifier, order_by))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("SELECT * FROM {table}{where} ORDER BY {ordering}").format(
                        table=sql.Identifier(table_name),
                        where=where,
                        ordering=ordering,
                    ),
                    tuple(effective_filters.values()),
                )
                return [
                    row
                    for item in cursor.fetchall()
                    if (row := _row_dict(cursor, item)) is not None
                ]

    def get_rd_role_definition(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_role_definitions", record_id)

    def list_rd_role_definitions(
        self,
        *,
        brain_app_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = {
            key: value
            for key, value in {
                "brain_app_id": brain_app_id,
                "status": status,
            }.items()
            if value is not None
        }
        return self._list(
            "rd_role_definitions",
            filters=filters,
            order_by=("brain_app_id", "code", "id"),
        )

    def get_rd_ai_employee(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_ai_employees", record_id)

    def list_rd_ai_employees(
        self,
        *,
        brain_app_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = {
            key: value
            for key, value in {
                "brain_app_id": brain_app_id,
                "status": status,
            }.items()
            if value is not None
        }
        return self._list(
            "rd_ai_employees",
            filters=filters,
            order_by=("brain_app_id", "code", "id"),
        )

    def get_rd_executor_profile(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_executor_profiles", record_id)

    def list_rd_executor_profiles(
        self,
        *,
        brain_app_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = {
            key: value
            for key, value in {
                "brain_app_id": brain_app_id,
                "status": status,
            }.items()
            if value is not None
        }
        return self._list(
            "rd_executor_profiles",
            filters=filters,
            order_by=("brain_app_id", "code", "id"),
        )

    def get_rd_task_executor_policy(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_task_executor_policies", record_id)

    def list_rd_task_executor_policies(
        self,
        *,
        brain_app_id: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = {
            key: value
            for key, value in {
                "brain_app_id": brain_app_id,
                "product_id": product_id,
                "status": status,
            }.items()
            if value is not None
        }
        return self._list(
            "rd_task_executor_policies",
            filters=filters,
            order_by=("brain_app_id", "product_id", "id"),
        )

    def get_rd_policy_role_binding(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_task_executor_policy_role_bindings", record_id)

    def list_rd_policy_role_bindings(self, policy_id: str) -> list[dict[str, Any]]:
        return self._list(
            "rd_task_executor_policy_role_bindings",
            filters={"policy_id": policy_id},
            order_by=("role_code", "id"),
        )

    def get_rd_policy_snapshot(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_task_executor_policy_snapshots", record_id)

    def get_rd_task_executor_policy_snapshot(
        self,
        record_id: str,
    ) -> dict[str, Any] | None:
        return self.get_rd_policy_snapshot(record_id)

    def list_rd_policy_snapshots(self, policy_id: str) -> list[dict[str, Any]]:
        return self._list(
            "rd_task_executor_policy_snapshots",
            filters={"policy_id": policy_id},
            order_by=("policy_version", "snapshot_kind", "resolution_revision", "id"),
        )

    def get_rd_policy_snapshot_source(
        self,
        record_id: str,
    ) -> dict[str, Any] | None:
        return self._get("rd_task_executor_policy_snapshot_sources", record_id)

    def list_rd_policy_snapshot_sources(
        self,
        snapshot_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_task_executor_policy_snapshot_sources",
            filters={"snapshot_id": snapshot_id},
            order_by=("requirement_id", "id"),
        )

    def get_requirement_assessment(self, record_id: str) -> dict[str, Any] | None:
        return self._get("requirement_assessments", record_id)

    def list_requirement_assessments(
        self,
        requirement_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "requirement_assessments",
            filters={"requirement_id": requirement_id},
            order_by=("requirement_revision", "created_at", "id"),
        )

    def get_requirement_assessment_opinion(
        self,
        record_id: str,
    ) -> dict[str, Any] | None:
        return self._get("requirement_assessment_opinions", record_id)

    def list_requirement_assessment_opinions(
        self,
        assessment_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "requirement_assessment_opinions",
            filters={"assessment_id": assessment_id},
            order_by=("opinion_round", "role_code", "id"),
        )

    def get_rd_collaboration_run(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_collaboration_runs", record_id)

    def list_rd_collaboration_runs(
        self,
        *,
        product_version_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = {
            key: value
            for key, value in {
                "product_version_id": product_version_id,
                "status": status,
            }.items()
            if value is not None
        }
        return self._list(
            "rd_collaboration_runs",
            filters=filters,
            order_by=("product_version_id", "run_generation", "id"),
        )

    def list_rd_collaboration_run_requirements(
        self,
        collaboration_run_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_collaboration_run_requirements",
            filters={"collaboration_run_id": collaboration_run_id},
            order_by=("requirement_id", "id"),
        )

    def get_rd_collaboration_run_requirement(
        self,
        record_id: str,
    ) -> dict[str, Any] | None:
        return self._get("rd_collaboration_run_requirements", record_id)

    def get_rd_scope_change_request(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_scope_change_requests", record_id)

    def list_rd_scope_change_request_operations(
        self,
        scope_change_request_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_scope_change_request_operations",
            filters={"scope_change_request_id": scope_change_request_id},
            order_by=("position", "id"),
        )

    def get_rd_scope_change_request_operation(
        self,
        record_id: str,
    ) -> dict[str, Any] | None:
        return self._get("rd_scope_change_request_operations", record_id)

    def get_rd_run_seat(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_run_seats", record_id)

    def list_rd_run_seats(self, collaboration_run_id: str) -> list[dict[str, Any]]:
        return self._list(
            "rd_run_seats",
            filters={"collaboration_run_id": collaboration_run_id},
            order_by=("role_code", "id"),
        )

    def list_rd_role_sessions(self, collaboration_run_id: str) -> list[dict[str, Any]]:
        return self._list(
            "rd_role_sessions",
            filters={"collaboration_run_id": collaboration_run_id},
            order_by=("seat_id", "session_no", "id"),
        )

    def get_rd_role_session(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_role_sessions", record_id)

    def get_rd_work_item(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_work_items", record_id)

    def list_rd_work_items(self, collaboration_run_id: str) -> list[dict[str, Any]]:
        return self._list(
            "rd_work_items",
            filters={"collaboration_run_id": collaboration_run_id},
            order_by=("plan_version", "priority", "id"),
        )

    def get_rd_work_item_dependency(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_work_item_dependencies", record_id)

    def list_rd_work_item_dependencies(
        self,
        collaboration_run_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_work_item_dependencies",
            filters={"collaboration_run_id": collaboration_run_id},
            order_by=("plan_version", "predecessor_work_item_id", "id"),
        )

    def get_rd_work_item_attempt(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_work_item_attempts", record_id)

    def list_rd_work_item_attempts(self, work_item_id: str) -> list[dict[str, Any]]:
        return self._list(
            "rd_work_item_attempts",
            filters={"work_item_id": work_item_id},
            order_by=("attempt_no", "id"),
        )

    def get_decision_request(self, record_id: str) -> dict[str, Any] | None:
        return self._get("decision_requests", record_id)

    def list_decision_requests(
        self,
        *,
        subject_type: str,
        subject_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "decision_requests",
            filters={"subject_type": subject_type, "subject_id": subject_id},
            order_by=("plan_version", "created_at", "id"),
        )

    def get_rd_collaboration_event(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_collaboration_events", record_id)

    def list_rd_collaboration_events(
        self,
        collaboration_run_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_collaboration_events",
            filters={"collaboration_run_id": collaboration_run_id},
            order_by=("occurred_at", "id"),
        )

    def get_rd_command_idempotency_record(
        self,
        record_id: str,
    ) -> dict[str, Any] | None:
        return self._get("rd_command_idempotency_records", record_id)

    def get_valid_claim_replay_secret(
        self,
        command_record_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM rd_command_replay_secrets
                    WHERE command_record_id = %s
                      AND secret_ciphertext IS NOT NULL
                      AND scrubbed_at IS NULL
                      AND expires_at > now()
                    """,
                    (command_record_id,),
                )
                return _row_dict(cursor, cursor.fetchone())

    def list_role_feedback_records(
        self,
        collaboration_run_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "role_feedback_records",
            filters={"collaboration_run_id": collaboration_run_id},
            order_by=("created_at", "id"),
        )

    def get_role_feedback_record(self, record_id: str) -> dict[str, Any] | None:
        return self._get("role_feedback_records", record_id)

    def get_rd_role_experience_record(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_role_experience_records", record_id)

    def list_rd_role_experience_records(
        self,
        experience_key: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_role_experience_records",
            filters={"experience_key": experience_key},
            order_by=("version", "id"),
        )

    def list_rd_role_experience_sources(
        self,
        experience_id: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_role_experience_sources",
            filters={"experience_id": experience_id},
            order_by=("created_at", "id"),
        )

    def get_rd_role_experience_source(
        self,
        record_id: str,
    ) -> dict[str, Any] | None:
        return self._get("rd_role_experience_sources", record_id)
