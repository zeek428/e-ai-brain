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


class RdCollaborationPolicyWriteMixin:
    def delete_unified_rd_policy(
        self,
        policy_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        def operation(cursor: Any) -> None:
            cursor.execute(
                "SELECT id FROM rd_task_executor_policies WHERE id = %s FOR UPDATE",
                (policy_id,),
            )
            if cursor.fetchone() is None:
                return
            cursor.execute(
                "SELECT 1 FROM rd_task_executor_policy_snapshots WHERE policy_id = %s LIMIT 1",
                (policy_id,),
            )
            if cursor.fetchone() is not None:
                raise RdCollaborationRepositoryError(
                    "RD_POLICY_IN_USE", "policy has immutable snapshots"
                )
            cursor.execute(
                "DELETE FROM rd_task_executor_policy_role_bindings WHERE policy_id = %s",
                (policy_id,),
            )
            try:
                cursor.execute("DELETE FROM rd_task_executor_policies WHERE id = %s", (policy_id,))
            except Exception as exc:
                raise RdCollaborationRepositoryError(
                    "RD_POLICY_IN_USE", "policy is referenced by immutable records"
                ) from exc
            if audit_event is not None:
                if self._upsert_audit_events is None:
                    raise RuntimeError("audit persistence callback is not configured")
                self._upsert_audit_events(cursor, [audit_event])

        self._in_transaction(operation)

    def save_unified_rd_policy(
        self,
        record: dict[str, Any],
        *,
        role_bindings: list[dict[str, Any]],
        expected_policy_version: int | None = None,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: self._save_unified_rd_policy_cursor(
                cursor,
                record,
                role_bindings=role_bindings,
                expected_policy_version=expected_policy_version,
                audit_event=audit_event,
            )
        )

    def _save_unified_rd_policy_cursor(
        self,
        cursor: Any,
        record: dict[str, Any],
        *,
        role_bindings: list[dict[str, Any]],
        expected_policy_version: int | None,
        audit_event: dict[str, Any] | None,
    ) -> dict[str, Any]:
        persisted = self._save_rd_task_executor_policy_record_cursor(
            cursor,
            record,
            expected_policy_version=expected_policy_version,
            audit_event=audit_event,
        )
        cursor.execute(
            "DELETE FROM rd_task_executor_policy_role_bindings WHERE policy_id = %s",
            (persisted["id"],),
        )
        for binding in role_bindings:
            self._save_simple_cursor(
                cursor,
                "rd_task_executor_policy_role_bindings",
                {
                    "id": binding["id"],
                    "policy_id": persisted["id"],
                    "role_code": binding["role_code"],
                    "actor_mode": binding["actor_mode"],
                    "candidate_human_user_ids": binding.get("candidate_human_user_ids", []),
                    "candidate_ai_employee_ids": binding.get("candidate_ai_employee_ids", []),
                    "primary_executor_profile_id": binding.get("primary_executor_profile_id"),
                    "fallback_executor_profile_ids": [],
                    "repository_trust_domains": binding.get("repository_trust_domains", []),
                    "tool_trust_domains": binding.get("tool_trust_domains", []),
                    "context_config": binding.get("context_config", {}),
                    "tool_config": binding.get("tool_config", {}),
                    "budget_config": binding.get("budget_config", {}),
                    "reviewer_role_codes": binding.get("reviewer_role_codes", []),
                    "required_permissions": binding.get("required_permissions", []),
                    "status": binding.get("status", "active"),
                },
            )
        return persisted

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

    def save_rd_task_executor_policy_record(
        self,
        record: dict[str, Any],
        *,
        expected_policy_version: int | None = None,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: self._save_rd_task_executor_policy_record_cursor(
                cursor,
                record,
                expected_policy_version=expected_policy_version,
                audit_event=audit_event,
            )
        )

    def _save_rd_task_executor_policy_record_cursor(
        self,
        cursor: Any,
        record: dict[str, Any],
        *,
        expected_policy_version: int | None = None,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with nullcontext():
            with nullcontext(cursor) as cursor:
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
        return self._in_transaction(
            lambda cursor: self._freeze_base_policy_snapshot_cursor(cursor, snapshot)
        )

    def _freeze_base_policy_snapshot_cursor(
        self,
        cursor: Any,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        if snapshot.get("snapshot_kind") != "base":
            raise ValueError("base snapshot must use snapshot_kind=base")
        with nullcontext():
            with nullcontext(cursor) as cursor:
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
        return self._in_transaction(
            lambda cursor: self._derive_assessment_policy_snapshot_cursor(
                cursor,
                base_snapshot_id=base_snapshot_id,
                snapshot=snapshot,
            )
        )

    def _derive_assessment_policy_snapshot_cursor(
        self,
        cursor: Any,
        *,
        base_snapshot_id: str,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        with nullcontext():
            with nullcontext(cursor) as cursor:
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
            "product_id",
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
            "version",
            "opinion_round",
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
            "actor_id",
            "candidate_human_user_ids",
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
        return self._in_transaction(
            lambda cursor: self._save_assessment_bundle_cursor(
                cursor,
                assessment=assessment,
                opinions=opinions,
                snapshots=snapshots,
            )
        )

    def _save_assessment_bundle_cursor(
        self,
        cursor: Any,
        *,
        assessment: dict[str, Any],
        opinions: list[dict[str, Any]],
        snapshots: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        with nullcontext():
            with nullcontext(cursor) as cursor:
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
        return self._in_transaction(
            lambda cursor: self._merge_version_policy_snapshot_with_sources_cursor(
                cursor,
                snapshot=snapshot,
                sources=sources,
            )
        )

    def _merge_version_policy_snapshot_with_sources_cursor(
        self,
        cursor: Any,
        *,
        snapshot: dict[str, Any],
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if snapshot.get("snapshot_kind") != "version_resolved":
            raise ValueError("version merge must persist a version_resolved snapshot")
        with nullcontext():
            with nullcontext(cursor) as cursor:
                persisted = self._insert_snapshot(cursor, snapshot)
                for source in sorted(sources, key=lambda item: str(item["requirement_id"])):
                    self._insert_snapshot_source(
                        cursor,
                        {**source, "snapshot_id": persisted["id"]},
                    )
                return persisted
