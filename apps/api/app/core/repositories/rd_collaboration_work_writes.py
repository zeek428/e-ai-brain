from __future__ import annotations

# Aggregate modules intentionally share one serialization/transaction vocabulary.
# ruff: noqa: F401
from collections.abc import Callable, Iterable, Sequence
from contextlib import nullcontext
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from app.core.repositories.rd_collaboration_shared import (
    POLICY_COLUMNS,
    TABLE_COLUMNS,
    RdCollaborationRepositoryError,
    RdCollaborationTransaction,
    RdCollaborationVersionConflictError,
    _adapt,
    _canonical_hash,
    _canonical_scope_operations,
    _response_hash,
    _row_dict,
)


class RdCollaborationWorkWriteMixin:
    def save_rd_run_seat_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_run_seats", record)

    def save_rd_role_session_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_role_sessions", record)

    def save_rd_work_item_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: self._save_rd_work_item_record_cursor(cursor, record)
        )

    def _save_rd_work_item_record_cursor(
        self,
        cursor: Any,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        persisted = self._insert_record(
            cursor,
            "rd_work_items",
            record,
            update_on_conflict=False,
        )
        self._assert_immutable_replay(
            existing=persisted,
            incoming=record,
            fields=TABLE_COLUMNS["rd_work_items"],
            message="work item id is bound to different immutable creation data",
            work_item_id=record["id"],
        )
        return persisted

    def save_rd_work_item_dependency_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._save_simple("rd_work_item_dependencies", record)

    def save_rd_work_item_plan_bundle(
        self,
        *,
        collaboration_run_id: str,
        expected_run_version: int,
        work_items: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: self._save_rd_work_item_plan_bundle_cursor(
                cursor,
                collaboration_run_id=collaboration_run_id,
                expected_run_version=expected_run_version,
                work_items=work_items,
                dependencies=dependencies,
            )
        )

    def _save_rd_work_item_plan_bundle_cursor(
        self,
        cursor: Any,
        *,
        collaboration_run_id: str,
        expected_run_version: int,
        work_items: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cursor.execute(
            "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
            (collaboration_run_id,),
        )
        run = _row_dict(cursor, cursor.fetchone())
        if run is None or run["status"] not in {"draft", "planning", "running"}:
            raise RdCollaborationRepositoryError(
                "RD_WORK_ITEM_STATE_INVALID", "collaboration run cannot accept a work-item plan"
            )
        if int(run["version"]) != int(expected_run_version):
            raise RdCollaborationVersionConflictError(int(run["version"]))
        plan_version = int(run["plan_version"]) + 1
        if any(int(item.get("plan_version") or -1) != plan_version for item in work_items) or any(
            int(dependency.get("plan_version") or -1) != plan_version for dependency in dependencies
        ):
            raise RdCollaborationRepositoryError(
                "RD_PLAN_INVALID", "work item plan version does not match the locked run"
            )
        ids = {str(item["id"]) for item in work_items}
        if len(ids) != len(work_items) or any(
            dependency.get("predecessor_work_item_id") not in ids
            or dependency.get("successor_work_item_id") not in ids
            for dependency in dependencies
        ):
            raise RdCollaborationRepositoryError(
                "RD_PLAN_INVALID", "work-item dependency escapes the immutable plan"
            )
        persisted_items = [
            self._save_rd_work_item_record_cursor(cursor, item)
            for item in sorted(work_items, key=lambda item: str(item["id"]))
        ]
        persisted_dependencies = [
            self._save_simple_cursor(cursor, "rd_work_item_dependencies", dependency)
            for dependency in sorted(dependencies, key=lambda item: str(item["id"]))
        ]
        cursor.execute(
            """
            UPDATE rd_collaboration_runs
            SET plan_version = %s,
                status = CASE WHEN status IN ('draft', 'planning') THEN 'running' ELSE status END,
                version = version + 1, updated_at = now()
            WHERE id = %s AND version = %s
            RETURNING *
            """,
            (plan_version, collaboration_run_id, expected_run_version),
        )
        persisted_run = _row_dict(cursor, cursor.fetchone())
        if persisted_run is None:
            raise RdCollaborationVersionConflictError(int(run["version"]))
        return {
            "run": persisted_run,
            "work_items": persisted_items,
            "dependencies": persisted_dependencies,
        }

    def save_rd_collaboration_event_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._in_transaction(lambda cursor: self._insert_event_cursor(cursor, record))

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
        self._assert_immutable_replay(
            existing=existing,
            incoming=record,
            fields=(
                "id",
                "brain_app_id",
                "product_id",
                "subject_type",
                "subject_id",
                "decision_type",
                "plan_version",
                "recommendation_json",
                "decision_actor_selector",
                "answer_actor_selector",
                "answer_schema",
                "expires_at",
                "timeout_policy",
                "escalation_target_selector",
                "escalation_level",
                "supersedes_decision_request_id",
                "created_by",
                "created_at",
            ),
            message="decision request id is bound to different immutable provenance",
            decision_request_id=record["id"],
        )
        return existing

    def save_decision_request_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._in_transaction(lambda cursor: self._insert_decision_request(cursor, record))

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
                return self._claim_ready_work_item_cursor(
                    cursor,
                    work_item_id,
                    lease_owner=lease_owner,
                    lease_seconds=lease_seconds,
                    expected_version=expected_version,
                    attempt=attempt,
                )

    def _claim_ready_work_item_cursor(
        self,
        cursor: Any,
        work_item_id: str,
        *,
        lease_owner: str,
        lease_seconds: int = 900,
        expected_version: int | None = None,
        attempt: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if lease_seconds < 60 or lease_seconds > 1800:
            raise ValueError("lease_seconds must be between 60 and 1800")
        # Canonical lock order is run -> work item -> attempt/decision.
        cursor.execute(
            """
            SELECT run.*
            FROM rd_collaboration_runs run
            JOIN rd_work_items item ON item.collaboration_run_id = run.id
            WHERE item.id = %s
            FOR UPDATE OF run
            """,
            (work_item_id,),
        )
        run = _row_dict(cursor, cursor.fetchone())
        if run is None or run["status"] != "running":
            return None
        params: list[Any] = [work_item_id]
        version_clause = ""
        if expected_version is not None:
            version_clause = "AND item.version = %s"
            params.append(expected_version)
        cursor.execute(
            f"""
            SELECT item.*
            FROM rd_work_items item
            WHERE item.id = %s
              AND item.status = 'ready'
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
            """,  # noqa: S608
            tuple(params),
        )
        candidate = _row_dict(cursor, cursor.fetchone())
        if candidate is None:
            return None
        cursor.execute(
            """
            UPDATE rd_work_items
            SET status = 'claimed', lease_owner = %s,
                lease_expires_at = now() + (%s * interval '1 second'),
                version = version + 1, updated_at = now()
            WHERE id = %s AND status = 'ready' AND version = %s
            RETURNING *
            """,
            (lease_owner, lease_seconds, work_item_id, candidate["version"]),
        )
        claimed = _row_dict(cursor, cursor.fetchone())
        if claimed is None:
            return None
        persisted_attempt: dict[str, Any] | None = None
        if attempt is not None:
            if attempt.get("work_item_id") != work_item_id:
                raise self._idempotency_conflict(
                    "attempt belongs to a different work item",
                    work_item_id=work_item_id,
                    attempt_id=attempt.get("id"),
                )
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
            FOR UPDATE
            """,
            (attempt["work_item_id"], attempt["idempotency_key"]),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError("attempt replay lookup failed")
        immutable_fields = (
            "id",
            "work_item_id",
            "attempt_no",
            "idempotency_key",
            "lease_id",
            "lease_token_hash",
            "executor_profile_id",
            "input_json",
        )
        self._assert_immutable_replay(
            existing=existing,
            incoming=attempt,
            fields=immutable_fields,
            message="attempt idempotency key is bound to different immutable identity",
            attempt_id=attempt.get("id"),
        )
        mutable_fields = (
            "status",
            "result_json",
            "failure_json",
            "rework_evidence",
            "started_at",
            "completed_at",
        )
        updates = [field for field in mutable_fields if field in attempt]
        if updates:
            cursor.execute(
                sql.SQL(
                    "UPDATE rd_work_item_attempts SET {assignments}, updated_at = now() "
                    "WHERE id = %s RETURNING *"
                ).format(
                    assignments=sql.SQL(", ").join(
                        sql.SQL("{} = %s").format(sql.Identifier(field)) for field in updates
                    )
                ),
                tuple(_adapt(attempt[field], field) for field in updates) + (existing["id"],),
            )
            updated = _row_dict(cursor, cursor.fetchone())
            if updated is None:
                raise RuntimeError("attempt replay update failed")
            return updated
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
        return self._in_transaction(
            lambda cursor: self._save_work_item_attempt_bundle_cursor(
                cursor,
                work_item_id=work_item_id,
                expected_statuses=expected_statuses,
                next_status=next_status,
                attempt=attempt,
                expected_version=expected_version,
                event=event,
            )
        )

    def _save_work_item_attempt_bundle_cursor(
        self,
        cursor: Any,
        *,
        work_item_id: str,
        expected_statuses: list[str],
        next_status: str,
        attempt: dict[str, Any],
        expected_version: int | None = None,
        event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with nullcontext():
            with nullcontext(cursor) as cursor:
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
                if attempt.get("work_item_id") != work_item_id:
                    raise self._idempotency_conflict(
                        "attempt belongs to a different work item",
                        work_item_id=work_item_id,
                        attempt_id=attempt.get("id"),
                    )
                persisted_attempt = self._insert_attempt(cursor, attempt)
                cursor.execute(
                    """
                    UPDATE rd_work_items
                    SET status = %s, version = version + 1, updated_at = now()
                    WHERE id = %s AND version = %s AND status = ANY(%s)
                    RETURNING *
                    """,
                    (
                        next_status,
                        work_item_id,
                        work_item["version"],
                        list(expected_statuses),
                    ),
                )
                persisted_work_item = _row_dict(cursor, cursor.fetchone())
                if persisted_work_item is not None and next_status == "completed":
                    self._promote_dependency_satisfied_successors_cursor(
                        cursor,
                        predecessor_work_item_id=work_item_id,
                    )
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

    @staticmethod
    def _promote_dependency_satisfied_successors_cursor(
        cursor: Any,
        *,
        predecessor_work_item_id: str,
    ) -> None:
        """Make completed predecessor edges and their now-runnable successors durable.

        The review transition owns this mutation so a read-side DAG check cannot
        leave an otherwise valid successor permanently blocked.  The update is
        deliberately conditional: only a completed predecessor satisfies an
        edge, and every incoming edge must be satisfied (or explicitly waived)
        before a blocked successor becomes ready.
        """
        cursor.execute(
            """
            UPDATE rd_work_item_dependencies
            SET status = 'satisfied', satisfied_at = COALESCE(satisfied_at, now()),
                updated_at = now()
            WHERE predecessor_work_item_id = %s AND status = 'pending'
            """,
            (predecessor_work_item_id,),
        )
        cursor.execute(
            """
            UPDATE rd_work_items AS successor
            SET status = 'ready', version = version + 1, updated_at = now()
            WHERE successor.status = 'blocked'
              AND EXISTS (
                SELECT 1
                FROM rd_work_item_dependencies direct_dependency
                WHERE direct_dependency.successor_work_item_id = successor.id
                  AND direct_dependency.predecessor_work_item_id = %s
              )
              AND NOT EXISTS (
                SELECT 1
                FROM rd_work_item_dependencies dependency
                WHERE dependency.successor_work_item_id = successor.id
                  AND dependency.status = 'pending'
              )
            """,
            (predecessor_work_item_id,),
        )

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
        return self._in_transaction(
            lambda cursor: self._cancel_work_item_bundle_cursor(
                cursor,
                work_item_id=work_item_id,
                expected_version=expected_version,
                high_risk=high_risk,
                decision_request=decision_request,
                event=event,
            )
        )

    def _cancel_work_item_bundle_cursor(
        self,
        cursor: Any,
        *,
        work_item_id: str,
        expected_version: int,
        high_risk: bool,
        decision_request: dict[str, Any] | None = None,
        event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with nullcontext():
            with nullcontext(cursor) as cursor:
                cursor.execute(
                    "SELECT collaboration_run_id FROM rd_work_items WHERE id = %s",
                    (work_item_id,),
                )
                identity = cursor.fetchone()
                if identity is None:
                    raise RdCollaborationRepositoryError(
                        "RD_WORK_ITEM_STATE_INVALID",
                        "work item does not exist",
                    )
                cursor.execute(
                    "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                    (identity[0],),
                )
                run = _row_dict(cursor, cursor.fetchone())
                cursor.execute(
                    "SELECT * FROM rd_work_items WHERE id = %s FOR UPDATE",
                    (work_item_id,),
                )
                work_item = _row_dict(cursor, cursor.fetchone())
                if (
                    run is None
                    or work_item is None
                    or work_item["status"]
                    in {
                        "completed",
                        "failed",
                        "cancelled",
                    }
                ):
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
                persisted_work_item = None
                if high_risk:
                    if decision_request is None:
                        raise RdCollaborationRepositoryError(
                            "RD_DECISION_REQUIRED",
                            "high-risk cancellation requires a decision request",
                        )
                    cursor.execute("SELECT now() < %s", (decision_request.get("expires_at"),))
                    if (
                        decision_request.get("brain_app_id", "rd_brain") != run["brain_app_id"]
                        or decision_request.get("product_id") != run["product_id"]
                        or decision_request.get("subject_type") != "rd_work_item"
                        or decision_request.get("subject_id") != work_item_id
                        or decision_request.get("status", "pending") != "pending"
                        or not bool(cursor.fetchone()[0])
                    ):
                        raise RdCollaborationRepositoryError(
                            "RD_DECISION_REQUIRED",
                            "cancellation decision is not bound to the work item and product",
                        )
                    persisted_decision = self._insert_decision_request(cursor, decision_request)
                    self._cancel_linked_delivery_cursor(
                        cursor,
                        run_id=str(run["id"]),
                        work_item_id=work_item_id,
                        reason="work_item_cancellation_pending_decision",
                    )
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
                    persisted_work_item = _row_dict(cursor, cursor.fetchone())
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
                    self._cancel_linked_delivery_cursor(
                        cursor,
                        run_id=str(run["id"]),
                        work_item_id=work_item_id,
                        reason="work_item_cancelled",
                    )
                persisted_event = self._insert_event_cursor(cursor, event) if event else None
                if persisted_work_item is None:
                    raise RuntimeError("work item cancellation did not return a row")
                return {
                    "work_item": persisted_work_item,
                    "attempt": attempt,
                    "decision_request": persisted_decision,
                    "event": persisted_event,
                }

    def _cancel_linked_delivery_cursor(
        self,
        cursor: Any,
        *,
        run_id: str,
        work_item_id: str,
        reason: str,
    ) -> None:
        """Fence every linked delivery write and request external reconciliation.

        A cancelled work item is not sufficient when a runner has already
        dispatched an AI task or a review is pending.  The terminal task state
        and cancelled review reject late transitions locally; durable outbox
        commands make the runner/Git side converge even when an external
        operation was already in flight.
        """
        cursor.execute(
            "SELECT id FROM ai_tasks WHERE work_item_id = %s ORDER BY id FOR UPDATE",
            (work_item_id,),
        )
        task_ids = [str(row[0]) for row in cursor.fetchall()]
        cursor.execute(
            "SELECT id FROM rd_work_item_attempts WHERE work_item_id = %s ORDER BY id FOR UPDATE",
            (work_item_id,),
        )
        attempt_ids = [str(row[0]) for row in cursor.fetchall()]
        if task_ids:
            cursor.execute(
                """
                UPDATE human_reviews
                SET status = 'cancelled', decision_reason = %s,
                    decided_at = COALESCE(decided_at, now()), updated_at = now()
                WHERE ai_task_id = ANY(%s) AND status = 'pending'
                """,
                (reason, task_ids),
            )
            cursor.execute(
                """
                UPDATE ai_tasks
                SET status = 'cancelled', error_code = 'RD_WORK_ITEM_CANCELLED',
                    error_message = %s, updated_at = now()
                WHERE id = ANY(%s) AND status NOT IN ('completed', 'failed', 'cancelled')
                """,
                (reason, task_ids),
            )
        aggregate_ids = [work_item_id, *attempt_ids, *task_ids]
        cursor.execute(
            """
            UPDATE execution_outbox_events
            SET status = 'cancelled', lease_owner = NULL, lease_until = NULL, updated_at = now()
            WHERE aggregate_id = ANY(%s) AND status IN ('pending', 'failed')
            """,
            (aggregate_ids,),
        )
        cursor.execute(
            """
            SELECT * FROM execution_outbox_events
            WHERE aggregate_id = ANY(%s) AND status IN ('processing', 'completed', 'dead_letter')
            ORDER BY id FOR UPDATE
            """,
            (aggregate_ids,),
        )
        source_outbox_rows = [
            source for row in cursor.fetchall() if (source := _row_dict(cursor, row)) is not None
        ]
        transaction = RdCollaborationTransaction(self, cursor)
        transaction.save_outbox_event(
            {
                "id": f"outbox:work-item:{work_item_id}:cancel",
                "aggregate_type": "rd_work_item",
                "aggregate_id": work_item_id,
                "event_type": "rd.work_item.cancel_runner",
                "idempotency_key": f"work-item:{work_item_id}:cancel",
                "payload_json": {
                    "reason": reason,
                    "collaboration_run_id": run_id,
                    "ai_task_ids": task_ids,
                    "attempt_ids": attempt_ids,
                },
            }
        )
        for source in source_outbox_rows:
            transaction.save_outbox_event(
                {
                    "id": f"outbox:work-item:{work_item_id}:reconcile:{source['id']}",
                    "aggregate_type": source["aggregate_type"],
                    "aggregate_id": source["aggregate_id"],
                    "event_type": "rd.work_item.reconcile_cancellation",
                    "idempotency_key": (f"work-item:{work_item_id}:reconcile:{source['id']}"),
                    "payload_json": {
                        "work_item_id": work_item_id,
                        "source_outbox_id": source["id"],
                        "source_status": source["status"],
                    },
                }
            )

    def suspend_collaboration_run(
        self,
        *,
        collaboration_run_id: str,
        decision_request_id: str,
        expected_version: int,
    ) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: self._suspend_collaboration_run_cursor(
                cursor,
                collaboration_run_id=collaboration_run_id,
                decision_request_id=decision_request_id,
                expected_version=expected_version,
            )
        )

    def _suspend_collaboration_run_cursor(
        self,
        cursor: Any,
        *,
        collaboration_run_id: str,
        decision_request_id: str,
        expected_version: int,
    ) -> dict[str, Any]:
        with nullcontext():
            with nullcontext(cursor) as cursor:
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
                    "SELECT * FROM decision_requests WHERE id = %s FOR UPDATE",
                    (decision_request_id,),
                )
                decision = _row_dict(cursor, cursor.fetchone())
                if (
                    decision is None
                    or decision["brain_app_id"] != run["brain_app_id"]
                    or decision["product_id"] != run["product_id"]
                    or decision["subject_type"] != "rd_collaboration_run"
                    or decision["subject_id"] != run["id"]
                    or decision["status"] != "pending"
                ):
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "decision request is not bound to the collaboration run",
                    )
                cursor.execute("SELECT now() < %s", (decision["expires_at"],))
                if not bool(cursor.fetchone()[0]):
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "decision request is expired",
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

    def _lock_decision_subject(
        self,
        cursor: Any,
        decision_request_id: str,
    ) -> tuple[
        dict[str, Any] | None,
        dict[str, Any] | None,
        dict[str, Any] | None,
    ]:
        """Lock every decision aggregate in run -> work item -> decision order."""
        cursor.execute(
            "SELECT * FROM decision_requests WHERE id = %s",
            (decision_request_id,),
        )
        identity = _row_dict(cursor, cursor.fetchone())
        if identity is None:
            return None, None, None
        bound_run: dict[str, Any] | None = None
        bound_work_item: dict[str, Any] | None = None
        if identity["subject_type"] == "rd_collaboration_run":
            cursor.execute(
                "SELECT * FROM rd_collaboration_runs WHERE id = %s FOR UPDATE",
                (identity["subject_id"],),
            )
            bound_run = _row_dict(cursor, cursor.fetchone())
        elif identity["subject_type"] == "rd_work_item":
            cursor.execute(
                """
                SELECT run.*
                FROM rd_collaboration_runs run
                JOIN rd_work_items item ON item.collaboration_run_id = run.id
                WHERE item.id = %s
                FOR UPDATE OF run
                """,
                (identity["subject_id"],),
            )
            bound_run = _row_dict(cursor, cursor.fetchone())
            cursor.execute(
                "SELECT * FROM rd_work_items WHERE id = %s FOR UPDATE",
                (identity["subject_id"],),
            )
            bound_work_item = _row_dict(cursor, cursor.fetchone())
        else:
            raise RdCollaborationRepositoryError(
                "RD_DECISION_REQUIRED",
                "decision subject type is not supported by this bundle",
            )
        if (
            bound_run is None
            or identity["brain_app_id"] != bound_run["brain_app_id"]
            or identity["product_id"] != bound_run["product_id"]
        ):
            raise RdCollaborationRepositoryError(
                "RD_DECISION_REQUIRED",
                "decision request is not bound to its frozen subject and product",
            )
        cursor.execute(
            "SELECT * FROM decision_requests WHERE id = %s FOR UPDATE",
            (decision_request_id,),
        )
        decision = _row_dict(cursor, cursor.fetchone())
        return decision, bound_run, bound_work_item

    def apply_decision_bundle(
        self,
        *,
        decision_request_id: str,
        selected_option_code: str,
        input_json: Any,
        comment: str | None,
        decided_by: str,
        expected_version: int,
        actor_role_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: self._apply_decision_bundle_cursor(
                cursor,
                decision_request_id=decision_request_id,
                selected_option_code=selected_option_code,
                input_json=input_json,
                comment=comment,
                decided_by=decided_by,
                actor_role_codes=actor_role_codes or [],
                expected_version=expected_version,
            )
        )

    def _apply_decision_bundle_cursor(
        self,
        cursor: Any,
        *,
        decision_request_id: str,
        selected_option_code: str,
        input_json: Any,
        comment: str | None,
        decided_by: str,
        actor_role_codes: list[str],
        expected_version: int,
    ) -> dict[str, Any]:
        with nullcontext():
            with nullcontext(cursor) as cursor:
                decision, bound_run, bound_work_item = self._lock_decision_subject(
                    cursor,
                    decision_request_id,
                )
                if decision is None:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_EXPIRED",
                        "decision request does not exist",
                    )
                if bound_run is None:
                    raise RuntimeError("decision subject lock did not return a run")
                if int(decision["version"]) != int(expected_version):
                    raise RdCollaborationVersionConflictError(int(decision["version"]))
                if decision["status"] not in {"pending", "waiting_more_info"}:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_EXPIRED",
                        "decision request is no longer active",
                    )
                selector = decision.get("decision_actor_selector") or {}
                if selector and not self._selector_matches(
                    selector,
                    actor_id=decided_by,
                    actor_role_codes=actor_role_codes,
                    actor_seat_ids=self._actor_run_seat_ids_cursor(
                        cursor, run_id=str(bound_run["id"]), actor_id=decided_by
                    ),
                ):
                    raise RdCollaborationRepositoryError(
                        "PERMISSION_DENIED",
                        "decision actor does not match the frozen selector",
                    )
                if (
                    bound_work_item is None
                    and bound_run["suspended_decision_request_id"] != decision_request_id
                ) or (
                    bound_work_item is not None
                    and bound_work_item["suspended_decision_request_id"] != decision_request_id
                ):
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "decision request is no longer bound to its frozen subject",
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
                run = bound_run if bound_work_item is None else None
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
                work_item = bound_work_item
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
                    if work_item is not None and target_status == "cancelled":
                        self._cancel_linked_delivery_cursor(
                            cursor,
                            run_id=str(bound_run["id"]),
                            work_item_id=str(work_item["id"]),
                            reason="decision_approved_work_item_cancellation",
                        )
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

    @staticmethod
    def _actor_run_seat_ids_cursor(cursor: Any, *, run_id: str, actor_id: str) -> list[str]:
        cursor.execute(
            """
            SELECT id FROM rd_run_seats
            WHERE collaboration_run_id = %s AND status = 'active'
              AND (human_user_id = %s OR ai_employee_id = %s)
            ORDER BY id
            """,
            (run_id, actor_id, actor_id),
        )
        return [str(row[0]) for row in cursor.fetchall()]

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
        return self._in_transaction(
            lambda cursor: self._answer_decision_request_cursor(
                cursor,
                decision_request_id=decision_request_id,
                expected_version=expected_version,
                actor_id=actor_id,
                actor_role_codes=actor_role_codes,
                actor_seat_ids=actor_seat_ids,
                answer_json=answer_json,
                evidence_json=evidence_json,
                options_json=options_json,
                options_hash=options_hash,
            )
        )

    def _answer_decision_request_cursor(
        self,
        cursor: Any,
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
        with nullcontext():
            with nullcontext(cursor) as cursor:
                decision, bound_run, bound_work_item = self._lock_decision_subject(
                    cursor,
                    decision_request_id,
                )
                if (
                    decision is None
                    or bound_run is None
                    or (
                        bound_work_item is None
                        and bound_run["suspended_decision_request_id"] != decision_request_id
                    )
                    or (
                        bound_work_item is not None
                        and bound_work_item["suspended_decision_request_id"] != decision_request_id
                    )
                ):
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "decision answer is not bound to its frozen subject and product",
                    )
                if decision["status"] != "waiting_more_info":
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
                        _canonical_hash(options_json),
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
        return self._in_transaction(
            lambda cursor: self._expire_and_escalate_decision_request_cursor(
                cursor,
                decision_request_id=decision_request_id,
                successor_request=successor_request,
                expiry_event=expiry_event,
            )
        )

    def _expire_and_escalate_decision_request_cursor(
        self,
        cursor: Any,
        *,
        decision_request_id: str,
        successor_request: dict[str, Any],
        expiry_event: dict[str, Any],
    ) -> dict[str, Any] | None:
        with nullcontext():
            with nullcontext(cursor) as cursor:
                decision, bound_run, bound_work_item = self._lock_decision_subject(
                    cursor,
                    decision_request_id,
                )
                if decision is None:
                    return None
                if bound_run is None:
                    raise RuntimeError("decision subject lock did not return a run")
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
                if (
                    bound_work_item is None
                    and bound_run["suspended_decision_request_id"] != decision_request_id
                ) or (
                    bound_work_item is not None
                    and bound_work_item["suspended_decision_request_id"] != decision_request_id
                ):
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "decision expiry is no longer bound to its frozen subject",
                    )
                cursor.execute("SELECT now() >= %s", (decision["expires_at"],))
                if not bool(cursor.fetchone()[0]):
                    return None
                successor_valid = (
                    successor_request.get("brain_app_id") == decision["brain_app_id"]
                    and successor_request.get("product_id") == decision["product_id"]
                    and successor_request.get("subject_type") == decision["subject_type"]
                    and successor_request.get("subject_id") == decision["subject_id"]
                    and successor_request.get("decision_type") == decision["decision_type"]
                    and int(successor_request.get("plan_version", -1))
                    == int(decision["plan_version"])
                    and successor_request.get("supersedes_decision_request_id")
                    == decision_request_id
                    and int(successor_request.get("escalation_level", -1))
                    == int(decision["escalation_level"]) + 1
                    and successor_request.get("status", "pending") == "pending"
                    and expiry_event.get("subject_type") == "decision_request"
                    and expiry_event.get("subject_id") == decision_request_id
                    and expiry_event.get("collaboration_run_id") == bound_run["id"]
                )
                if not successor_valid:
                    raise RdCollaborationRepositoryError(
                        "RD_DECISION_REQUIRED",
                        "successor decision does not preserve expiry provenance",
                    )
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
                if bound_work_item is None:
                    cursor.execute(
                        """
                        UPDATE rd_collaboration_runs
                        SET suspended_decision_request_id = %s,
                            version = version + 1, updated_at = now()
                        WHERE id = %s AND suspended_decision_request_id = %s
                        """,
                        (successor["id"], bound_run["id"], decision_request_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE rd_work_items
                        SET suspended_decision_request_id = %s,
                            version = version + 1, updated_at = now()
                        WHERE id = %s AND suspended_decision_request_id = %s
                        """,
                        (successor["id"], bound_work_item["id"], decision_request_id),
                    )
                return {
                    "expired_request": expired,
                    "successor_request": successor,
                    "expiry_event": event,
                }
