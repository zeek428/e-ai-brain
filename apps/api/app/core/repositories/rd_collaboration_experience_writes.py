from __future__ import annotations

# Aggregate modules intentionally share one serialization/transaction vocabulary.
# ruff: noqa: F401
from collections.abc import Callable, Iterable, Sequence
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


class RdCollaborationExperienceWriteMixin:
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
                self._assert_immutable_replay(
                    existing=existing,
                    incoming=record,
                    fields=columns,
                    message="feedback fingerprint is bound to different immutable provenance",
                    collaboration_run_id=record["collaboration_run_id"],
                    feedback_fingerprint=record["feedback_fingerprint"],
                )
                return existing

    def save_rd_role_experience_record(
        self,
        record: dict[str, Any],
        *,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Append a versioned experience candidate and its immutable provenance."""
        if not sources:
            raise RdCollaborationRepositoryError(
                "RD_EXPERIENCE_INVALID",
                "experience candidates require at least one relational feedback source",
            )
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
                    self._assert_immutable_replay(
                        existing=existing,
                        incoming=record,
                        fields=columns,
                        message="experience id is bound to different immutable provenance",
                        experience_id=record["id"],
                    )
                    cursor.execute(
                        """
                        SELECT id, experience_id, role_feedback_record_id,
                               strategy_snapshot_id
                        FROM rd_role_experience_sources
                        WHERE experience_id = %s
                        ORDER BY role_feedback_record_id, id
                        """,
                        (record["id"],),
                    )
                    existing_sources = {
                        (row[0], row[1], row[2], row[3]) for row in cursor.fetchall()
                    }
                    requested_sources = {
                        (
                            source.get("id"),
                            source.get("experience_id"),
                            source.get("role_feedback_record_id"),
                            source.get("strategy_snapshot_id"),
                        )
                        for source in sources
                    }
                    if existing_sources != requested_sources:
                        raise self._idempotency_conflict(
                            "experience replay uses different relational sources",
                            experience_id=record["id"],
                        )
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
                    cursor.execute(
                        """
                        SELECT brain_app_id, product_id, role_code, strategy_snapshot_id
                        FROM role_feedback_records
                        WHERE id = %s
                        FOR KEY SHARE
                        """,
                        (source.get("role_feedback_record_id"),),
                    )
                    feedback = cursor.fetchone()
                    if (
                        feedback is None
                        or feedback[0] != record.get("brain_app_id", "rd_brain")
                        or feedback[1] not in set(record.get("product_scope") or [])
                        or feedback[2] != record.get("role_code")
                        or feedback[3] != source.get("strategy_snapshot_id")
                    ):
                        raise RdCollaborationRepositoryError(
                            "RD_EXPERIENCE_INVALID",
                            "experience source does not match its feedback provenance",
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
