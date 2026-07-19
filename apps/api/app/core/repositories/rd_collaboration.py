from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from typing import Any

from psycopg import sql
from psycopg.types.json import Jsonb

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

_DUE_ORDER_SQL = "COALESCE(next_dispatch_at, '-infinity'::timestamptz)"
_DISPATCH_PRIORITY_SQL = "(CASE WHEN priority = 0 THEN 100 ELSE priority END)"
_DUE_DISPATCH_PAGE_SQL = f"""
    SELECT *
    FROM rd_work_items
    WHERE collaboration_run_id = %s
      AND status IN ('ready', 'rework_required')
      AND {_DUE_ORDER_SQL} <= %s
      {{after_predicate}}
    ORDER BY {_DUE_ORDER_SQL}, {_DISPATCH_PRIORITY_SQL}, id
    LIMIT %s
"""


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

    def get_rd_collaboration_upgrade_state(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_collaboration_upgrade_state", record_id)

    def update_rd_collaboration_upgrade_state(
        self, *, expected_version: int, changes: dict[str, Any]
    ) -> dict[str, Any]:
        """Persist the maintenance fence with optimistic locking.

        Upgrade state is a durable, single-row control-plane fact; do not fall
        back to the request-local runtime store in PostgreSQL mode.
        """
        json_fields = (
            "advisory_preflight_json",
            "locked_preflight_json",
            "active_counts_json",
            "smoke_test_json",
            "fence_release_evidence",
        )
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT version FROM rd_collaboration_upgrade_state WHERE id = %s FOR UPDATE",
                    (str(changes["id"]),),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RdCollaborationRepositoryError(
                        "NOT_FOUND", "R&D collaboration upgrade state does not exist"
                    )
                current_version = int(row[0])
                if current_version != expected_version:
                    raise RdCollaborationVersionConflictError(current_version)
                assignments = [
                    "fence_mode = %s",
                    "schema_version = %s",
                    "fence_reason = %s",
                    "advisory_preflight_json = %s",
                    "locked_preflight_json = %s",
                    "active_counts_json = %s",
                    "backup_marker = %s",
                    "cutover_started_at = %s",
                    "cleanup_started_at = %s",
                    "cleanup_completed_at = %s",
                    "v2_api_version = %s",
                    "v2_worker_version = %s",
                    "v2_graph_version = %s",
                    "health_marker = %s",
                    "smoke_test_json = %s",
                    "abort_reason = %s",
                    "abort_actor_id = %s",
                    "aborted_at = %s",
                    "fence_released_at = %s",
                    "fence_release_evidence = %s",
                    "version = version + 1",
                    "updated_at = now()",
                ]
                values: list[Any] = [
                    changes.get("fence_mode"),
                    changes.get("schema_version"),
                    changes.get("fence_reason"),
                    *[Jsonb(changes.get(field) or {}) for field in json_fields[:3]],
                    changes.get("backup_marker"),
                    changes.get("cutover_started_at"),
                    changes.get("cleanup_started_at"),
                    changes.get("cleanup_completed_at"),
                    changes.get("v2_api_version"),
                    changes.get("v2_worker_version"),
                    changes.get("v2_graph_version"),
                    changes.get("health_marker"),
                    Jsonb(changes.get("smoke_test_json") or {}),
                    changes.get("abort_reason"),
                    changes.get("abort_actor_id"),
                    changes.get("aborted_at"),
                    changes.get("fence_released_at"),
                    Jsonb(changes.get("fence_release_evidence") or {}),
                    str(changes["id"]),
                    expected_version,
                ]
                cursor.execute(
                    f"""
                    UPDATE rd_collaboration_upgrade_state
                    SET {", ".join(assignments)}
                    WHERE id = %s AND version = %s
                    RETURNING *
                    """,
                    values,
                )
                saved = _row_dict(cursor, cursor.fetchone())
                if saved is None:
                    raise RdCollaborationVersionConflictError(current_version)
            connection.commit()
        return saved

    def get_rd_role_definition(self, record_id: str) -> dict[str, Any] | None:
        return self._get("rd_role_definitions", record_id)

    def get_assessment_candidate_user(self, user_id: str) -> dict[str, Any] | None:
        """Load a candidate with the same authorization facts used for role qualification."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, roles
                    FROM users WHERE id = %s AND status = 'active'
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                candidate_id, legacy_roles = row
                cursor.execute(
                    """
                    SELECT DISTINCT permission_code
                    FROM user_roles ur
                    JOIN role_permissions rp ON rp.role_id = ur.role_id
                    WHERE ur.user_id = %s AND ur.status = 'active'
                    """,
                    (user_id,),
                )
                permissions = [item[0] for item in cursor.fetchall()]
                cursor.execute(
                    """
                    SELECT scope_type, scope_id, access_level
                    FROM user_scope_grants
                    WHERE user_id = %s AND status = 'active'
                      AND (expires_at IS NULL OR expires_at > now())
                    """,
                    (user_id,),
                )
                scopes = [
                    {"scope_type": item[0], "scope_id": item[1], "access_level": item[2]}
                    for item in cursor.fetchall()
                ]
        return {
            "id": candidate_id,
            "roles": list(legacy_roles or []),
            "permissions": permissions,
            "scope_summary": scopes,
        }

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

    def get_ai_executor_approval_request(self, record_id: str) -> dict[str, Any] | None:
        return self._get("ai_executor_approval_requests", record_id)

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

    def list_rd_collaboration_task_executor_policies(
        self,
        *,
        brain_app_id: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List the versioned collaboration contract without shadowing the legacy list."""
        return self._list(
            "rd_task_executor_policies",
            filters={
                key: value
                for key, value in {
                    "brain_app_id": brain_app_id,
                    "product_id": product_id,
                    "status": status,
                }.items()
                if value is not None
            },
            order_by=("brain_app_id", "product_id", "policy_version", "id"),
        )

    def list_rd_collaboration_default_task_executor_policies(
        self,
        *,
        brain_app_id: str,
        status: str = "active",
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM rd_task_executor_policies
                    WHERE brain_app_id = %s AND product_id IS NULL AND status = %s
                    ORDER BY policy_version, id
                    """,
                    (brain_app_id, status),
                )
                return [
                    row
                    for item in cursor.fetchall()
                    if (row := _row_dict(cursor, item)) is not None
                ]

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

    def list_rd_product_version_requirement_provenance(
        self, product_version_id: str
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_product_version_requirement_provenance",
            filters={"product_version_id": product_version_id},
            order_by=("requirement_id",),
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

    def list_requirement_assessments_for_final_snapshot(
        self,
        snapshot_id: str,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM requirement_assessments WHERE final_strategy_snapshot_id = %s",
                    (snapshot_id,),
                )
                return [
                    row
                    for item in cursor.fetchall()
                    if (row := _row_dict(cursor, item)) is not None
                ]

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

    def get_requirement_assessment_execution(self, record_id: str) -> dict[str, Any] | None:
        return self._get("requirement_assessment_executions", record_id)

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

    def list_rd_scope_change_requests(
        self,
        *,
        product_version_id: str | None = None,
        source_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_scope_change_requests",
            filters={
                key: value
                for key, value in {
                    "product_version_id": product_version_id,
                    "source_run_id": source_run_id,
                    "status": status,
                }.items()
                if value is not None
            },
            order_by=("product_version_id", "created_at", "id"),
        )

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

    def list_rd_work_items_by_ids(
        self,
        collaboration_run_id: str,
        work_item_ids: list[str],
    ) -> list[dict[str, Any]]:
        if not work_item_ids:
            return []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM rd_work_items
                    WHERE collaboration_run_id = %s
                      AND id = ANY(%s)
                    ORDER BY id
                    """,
                    (collaboration_run_id, work_item_ids),
                )
                return [
                    row
                    for item in cursor.fetchall()
                    if (row := _row_dict(cursor, item)) is not None
                ]

    def list_due_rd_work_items(
        self,
        collaboration_run_id: str,
        *,
        limit: int | None = None,
        after: tuple[datetime | None, int, str] | None = None,
        due_at: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Load only due automatic-dispatch candidates from PostgreSQL.

        Keep the due predicate and page order aligned with the partial index
        from migration 124. Dependency eligibility remains a scheduler concern
        because it spans multiple work-item rows.
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if limit is not None or after is not None:
                    observed_at = due_at or datetime.now(UTC)
                    if observed_at.tzinfo is None:
                        observed_at = observed_at.replace(tzinfo=UTC)
                    page = self._list_due_rd_work_item_page_cursor(
                        cursor,
                        collaboration_run_id=collaboration_run_id,
                        limit=limit or 50,
                        after=after,
                        due_at=observed_at,
                    )
                    return sorted(
                        page,
                        key=lambda item: (
                            int(item.get("priority") or 100),
                            str(item["id"]),
                        ),
                    )
                cursor.execute(
                    """
                    SELECT *
                    FROM rd_work_items
                    WHERE collaboration_run_id = %s
                      AND status IN ('ready', 'rework_required')
                      AND (next_dispatch_at IS NULL OR next_dispatch_at <= CURRENT_TIMESTAMP)
                    ORDER BY plan_version, priority, id
                    """,
                    (collaboration_run_id,),
                )
                return [
                    row
                    for item in cursor.fetchall()
                    if (row := _row_dict(cursor, item)) is not None
                ]

    @staticmethod
    def _list_due_rd_work_item_page_cursor(
        cursor: Any,
        *,
        collaboration_run_id: str,
        limit: int,
        after: tuple[datetime | None, int, str] | None,
        due_at: datetime,
    ) -> list[dict[str, Any]]:
        params: list[Any] = [collaboration_run_id, due_at]
        after_predicate = ""
        if after is not None:
            after_predicate = f"""
              AND (
                {_DUE_ORDER_SQL} > COALESCE(%s, '-infinity'::timestamptz)
                OR (
                  {_DUE_ORDER_SQL} = COALESCE(%s, '-infinity'::timestamptz)
                  AND {_DISPATCH_PRIORITY_SQL} > %s
                )
                OR (
                  {_DUE_ORDER_SQL} = COALESCE(%s, '-infinity'::timestamptz)
                  AND {_DISPATCH_PRIORITY_SQL} = %s
                  AND id > %s
                )
              )
            """
            params.extend((after[0], after[0], after[1], after[0], after[1], after[2]))
        params.append(limit)
        cursor.execute(
            _DUE_DISPATCH_PAGE_SQL.format(after_predicate=after_predicate),
            tuple(params),
        )
        return [row for item in cursor.fetchall() if (row := _row_dict(cursor, item)) is not None]

    def reserve_due_rd_dispatch_candidates(
        self,
        *,
        limit: int,
        due_at: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Atomically reserve a bounded, restart-safe round-robin candidate page."""
        if limit <= 0:
            return []
        observed_at = due_at or datetime.now(UTC)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        reserved: list[dict[str, Any]] = []
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rd_dispatch_sweep_cursors (id)
                    VALUES ('automatic_dispatch')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
                cursor.execute(
                    """
                    SELECT last_run_id
                    FROM rd_dispatch_sweep_cursors
                    WHERE id = 'automatic_dispatch'
                    FOR UPDATE
                    """
                )
                last_run_row = cursor.fetchone()
                last_run_id = str(last_run_row[0]) if last_run_row and last_run_row[0] else None
                cursor.execute(
                    """
                    SELECT id
                    FROM rd_collaboration_runs
                    WHERE status IN ('running', 'integrating', 'verifying')
                    ORDER BY id
                    """
                )
                run_ids = [str(row[0]) for row in cursor.fetchall()]
                if last_run_id in run_ids:
                    split = run_ids.index(last_run_id) + 1
                    run_ids = run_ids[split:] + run_ids[:split]

                last_examined_run_id = last_run_id
                for run_id in run_ids:
                    remaining = limit - len(reserved)
                    if remaining <= 0:
                        break
                    cursor.execute(
                        """
                        SELECT cursor_next_dispatch_at, cursor_priority, cursor_work_item_id
                        FROM rd_dispatch_run_cursors
                        WHERE collaboration_run_id = %s
                        """,
                        (run_id,),
                    )
                    cursor_row = cursor.fetchone()
                    after = (
                        (cursor_row[0], int(cursor_row[1]), str(cursor_row[2]))
                        if cursor_row is not None
                        else None
                    )
                    page = self._list_due_rd_work_item_page_cursor(
                        cursor,
                        collaboration_run_id=run_id,
                        limit=remaining,
                        after=after,
                        due_at=observed_at,
                    )
                    if not page and after is not None:
                        page = self._list_due_rd_work_item_page_cursor(
                            cursor,
                            collaboration_run_id=run_id,
                            limit=remaining,
                            after=None,
                            due_at=observed_at,
                        )
                    if page:
                        last_item = page[-1]
                        cursor.execute(
                            """
                            INSERT INTO rd_dispatch_run_cursors (
                              collaboration_run_id, cursor_next_dispatch_at,
                              cursor_priority, cursor_work_item_id
                            ) VALUES (%s, %s, %s, %s)
                            ON CONFLICT (collaboration_run_id) DO UPDATE SET
                              cursor_next_dispatch_at = EXCLUDED.cursor_next_dispatch_at,
                              cursor_priority = EXCLUDED.cursor_priority,
                              cursor_work_item_id = EXCLUDED.cursor_work_item_id,
                              version = rd_dispatch_run_cursors.version + 1,
                              updated_at = now()
                            """,
                            (
                                run_id,
                                last_item.get("next_dispatch_at"),
                                int(last_item.get("priority") or 100),
                                str(last_item["id"]),
                            ),
                        )
                        reserved.extend(
                            sorted(
                                page,
                                key=lambda item: (
                                    int(item.get("priority") or 100),
                                    str(item["id"]),
                                ),
                            )
                        )
                    last_examined_run_id = run_id
                cursor.execute(
                    """
                    UPDATE rd_dispatch_sweep_cursors
                    SET last_run_id = %s, version = version + 1, updated_at = now()
                    WHERE id = 'automatic_dispatch'
                    """,
                    (last_examined_run_id,),
                )
            connection.commit()
        return reserved

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

    def list_rd_work_item_dependencies_for_successors(
        self,
        collaboration_run_id: str,
        successor_work_item_ids: list[str],
    ) -> list[dict[str, Any]]:
        if not successor_work_item_ids:
            return []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM rd_work_item_dependencies
                    WHERE collaboration_run_id = %s
                      AND successor_work_item_id = ANY(%s)
                    ORDER BY successor_work_item_id, predecessor_work_item_id, id
                    """,
                    (collaboration_run_id, successor_work_item_ids),
                )
                return [
                    row
                    for item in cursor.fetchall()
                    if (row := _row_dict(cursor, item)) is not None
                ]

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

    def get_rd_role_experience_record_scoped(
        self,
        record_id: str,
        *,
        product_scope_ids: list[str] | None,
        brain_app_ids: list[str] | None,
    ) -> dict[str, Any] | None:
        """Load an experience only when both caller-owned scopes match in SQL."""
        clauses = ["experience.id = %s"]
        params: list[Any] = [record_id]
        if product_scope_ids is not None:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text("
                "experience.product_scope) p WHERE NOT p = ANY(%s))"
            )
            params.append(product_scope_ids)
        if brain_app_ids is not None:
            clauses.append("experience.brain_app_id = ANY(%s)")
            params.append(brain_app_ids)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT experience.* FROM rd_role_experience_records experience WHERE "
                    + " AND ".join(clauses),
                    tuple(params),
                )
                return _row_dict(cursor, cursor.fetchone())

    def list_rd_role_experience_records(
        self,
        experience_key: str,
    ) -> list[dict[str, Any]]:
        return self._list(
            "rd_role_experience_records",
            filters={"experience_key": experience_key},
            order_by=("version", "id"),
        )

    def list_rd_role_experience_records_page(
        self,
        *,
        filters: dict[str, Any],
        product_scope_ids: list[str] | None,
        page: int,
        page_size: int,
        brain_app_ids: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Filter experience in PostgreSQL before any source metadata is read."""
        clauses: list[str] = []
        params: list[Any] = []
        for field in (
            "brain_app_id",
            "role_code",
            "work_item_type",
            "scenario",
            "status",
            "version",
        ):
            if filters.get(field) is not None:
                clauses.append(f"experience.{field} = %s")
                params.append(filters[field])
        if filters.get("product_id"):
            clauses.append("experience.product_scope @> jsonb_build_array(%s::text)")
            params.append(filters["product_id"])
        if product_scope_ids is not None:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text("
                "experience.product_scope) p WHERE NOT p = ANY(%s))"
            )
            params.append(product_scope_ids)
        if brain_app_ids is not None:
            clauses.append("experience.brain_app_id = ANY(%s)")
            params.append(brain_app_ids)
        if filters.get("risk_level"):
            clauses.append("experience.risk_scope ->> 'maximum' = %s")
            params.append(filters["risk_level"])
        if filters.get("repository_trust_domain"):
            clauses.append("experience.repository_trust_domains @> jsonb_build_array(%s::text)")
            params.append(filters["repository_trust_domain"])
        if filters.get("tool_trust_domain"):
            clauses.append("experience.tool_trust_domains @> jsonb_build_array(%s::text)")
            params.append(filters["tool_trust_domain"])
        if filters.get("minimum_confidence") is not None:
            clauses.append("experience.confidence >= %s")
            params.append(filters["minimum_confidence"])
        if filters.get("evidence_subject_id"):
            clauses.append(
                "EXISTS (SELECT 1 FROM rd_role_experience_sources source "
                "JOIN role_feedback_records feedback "
                "ON feedback.id = source.role_feedback_record_id "
                "WHERE source.experience_id = experience.id AND "
                "(feedback.producer_subject_id = %s OR feedback.human_user_id = %s "
                "OR feedback.ai_employee_id = %s))"
            )
            params.extend([filters["evidence_subject_id"]] * 3)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM rd_role_experience_records experience{where}",
                    tuple(params),
                )
                total = int(cursor.fetchone()[0])
                cursor.execute(
                    f"SELECT experience.* FROM rd_role_experience_records experience{where} "
                    "ORDER BY experience.confidence DESC, experience.id ASC LIMIT %s OFFSET %s",
                    tuple(params + [page_size, (page - 1) * page_size]),
                )
                return (
                    [
                        row
                        for item in cursor.fetchall()
                        if (row := _row_dict(cursor, item)) is not None
                    ],
                    total,
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
