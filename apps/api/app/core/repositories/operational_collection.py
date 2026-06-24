from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class OperationalCollectionReadRepository:
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

    def save_collector_runs(self, payload: dict[str, Any]) -> None:
        runs = payload.get("collector_runs", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "collector_runs", runs)
                self.upsert_collector_runs(cursor, runs)

    def save_collector_run_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_collector_runs(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_pending_attribution(self, payload: dict[str, Any]) -> None:
        items = payload.get("pending_attribution_items", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "pending_attribution_items", items)
                self.upsert_pending_attribution_items(cursor, items)

    def save_pending_attribution_item_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_pending_attribution_items(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def upsert_collector_runs(
        self,
        cursor,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        for run in runs.values():
            created_at = run.get("created_at")
            updated_at = run.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO collector_runs (
                  id, collector_type, product_id, status, source_system,
                  started_at, finished_at, records_imported, error_message,
                  payload_summary, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), %s::timestamptz,
                  %s, %s, %s::jsonb, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  collector_type = EXCLUDED.collector_type,
                  product_id = EXCLUDED.product_id,
                  status = EXCLUDED.status,
                  source_system = EXCLUDED.source_system,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  records_imported = EXCLUDED.records_imported,
                  error_message = EXCLUDED.error_message,
                  payload_summary = EXCLUDED.payload_summary,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    run["id"],
                    run["collector_type"],
                    run.get("product_id"),
                    run.get("status", "running"),
                    run["source_system"],
                    run.get("started_at"),
                    run.get("finished_at"),
                    run.get("records_imported", 0),
                    run.get("error_message"),
                    json.dumps(run.get("payload_summary", {}), ensure_ascii=False),
                    run.get("created_by"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_pending_attribution_items(
        self,
        cursor,
        items: dict[str, dict[str, Any]],
    ) -> None:
        for item in items.values():
            created_at = item.get("created_at")
            updated_at = item.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO pending_attribution_items (
                  id, source_type, source_system, collector_run_id, raw_subject_id,
                  summary, raw_payload, suggested_product_id, suggested_module_code,
                  confidence, status, resolution_action, resolution_note,
                  resolved_product_id, resolved_module_code, resolved_requirement_id,
                  resolved_subject_type, resolved_subject_id, resolved_by, resolved_at,
                  created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s::jsonb, %s, %s,
                  %s, %s, %s, %s,
                  %s, %s, %s,
                  %s, %s, %s, %s::timestamptz,
                  %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  source_type = EXCLUDED.source_type,
                  source_system = EXCLUDED.source_system,
                  collector_run_id = EXCLUDED.collector_run_id,
                  raw_subject_id = EXCLUDED.raw_subject_id,
                  summary = EXCLUDED.summary,
                  raw_payload = EXCLUDED.raw_payload,
                  suggested_product_id = EXCLUDED.suggested_product_id,
                  suggested_module_code = EXCLUDED.suggested_module_code,
                  confidence = EXCLUDED.confidence,
                  status = EXCLUDED.status,
                  resolution_action = EXCLUDED.resolution_action,
                  resolution_note = EXCLUDED.resolution_note,
                  resolved_product_id = EXCLUDED.resolved_product_id,
                  resolved_module_code = EXCLUDED.resolved_module_code,
                  resolved_requirement_id = EXCLUDED.resolved_requirement_id,
                  resolved_subject_type = EXCLUDED.resolved_subject_type,
                  resolved_subject_id = EXCLUDED.resolved_subject_id,
                  resolved_by = EXCLUDED.resolved_by,
                  resolved_at = EXCLUDED.resolved_at,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    item["id"],
                    item["source_type"],
                    item["source_system"],
                    item.get("collector_run_id"),
                    item.get("raw_subject_id"),
                    item["summary"],
                    json.dumps(item.get("raw_payload", {}), ensure_ascii=False),
                    item.get("suggested_product_id"),
                    item.get("suggested_module_code"),
                    item.get("confidence"),
                    item.get("status", "pending"),
                    item.get("resolution_action"),
                    item.get("resolution_note"),
                    item.get("resolved_product_id"),
                    item.get("resolved_module_code"),
                    item.get("resolved_requirement_id"),
                    item.get("resolved_subject_type"),
                    item.get("resolved_subject_id"),
                    item.get("resolved_by"),
                    item.get("resolved_at"),
                    item.get("created_by"),
                    created_at,
                    updated_at,
                ),
            )

    def load_collector_runs(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                runs = self._load_collector_runs(cursor)
        return {"collector_runs": runs}

    def list_collector_runs(
        self,
        *,
        collector_type: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        source_system: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if collector_type is not None:
            where_clauses.append("collector_type = %s")
            params.append(collector_type)
        if product_id is not None:
            where_clauses.append("product_id = %s")
            params.append(product_id)
        if status is not None:
            where_clauses.append("status = %s")
            params.append(status)
        if source_system is not None:
            where_clauses.append("source_system = %s")
            params.append(source_system)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, collector_type, product_id, status, source_system,
                           started_at, finished_at, records_imported, error_message,
                           payload_summary, created_by, created_at, updated_at
                    FROM collector_runs
                    {where_clause}
                    ORDER BY started_at DESC,
                             COALESCE(updated_at, created_at) DESC,
                             id DESC
                    """,
                    tuple(params),
                )
                return self._collector_runs_from_rows(cursor.fetchall())

    def load_pending_attribution(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                items = self._load_pending_attribution_items(cursor)
        return {"pending_attribution_items": items}

    def list_pending_attribution_items(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        resolved_product_id: str | None = None,
        collector_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if source_type is not None:
            where_clauses.append("source_type = %s")
            params.append(source_type)
        if status is not None:
            where_clauses.append("status = %s")
            params.append(status)
        if resolved_product_id is not None:
            where_clauses.append("resolved_product_id = %s")
            params.append(resolved_product_id)
        if collector_run_id is not None:
            where_clauses.append("collector_run_id = %s")
            params.append(collector_run_id)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, source_type, source_system, collector_run_id, raw_subject_id,
                           summary, raw_payload, suggested_product_id, suggested_module_code,
                           confidence, status, resolution_action, resolution_note,
                           resolved_product_id, resolved_module_code, resolved_requirement_id,
                           resolved_subject_type, resolved_subject_id, resolved_by, resolved_at,
                           created_by, created_at, updated_at
                    FROM pending_attribution_items
                    {where_clause}
                    ORDER BY created_at DESC,
                             COALESCE(updated_at, created_at) DESC,
                             id DESC
                    """,
                    tuple(params),
                )
                return self._pending_attribution_items_from_rows(cursor.fetchall())

    def _load_collector_runs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, collector_type, product_id, status, source_system,
                   started_at, finished_at, records_imported, error_message,
                   payload_summary, created_by, created_at, updated_at
            FROM collector_runs
            ORDER BY started_at, id
            """
        )
        return {run["id"]: run for run in self._collector_runs_from_rows(cursor.fetchall())}

    def _collector_runs_from_rows(self, rows: list[Any]) -> list[dict[str, Any]]:
        items = []
        for row in rows:
            payload_summary = row[9] or {}
            if isinstance(payload_summary, str):
                payload_summary = json.loads(payload_summary)
            items.append(
                {
                    "collector_type": row[1],
                    "created_at": row[11].isoformat() if row[11] else None,
                    "created_by": row[10],
                    "error_message": row[8],
                    "finished_at": row[6].isoformat() if row[6] else None,
                    "id": row[0],
                    "payload_summary": payload_summary,
                    "product_id": row[2],
                    "records_imported": row[7],
                    "source_system": row[4],
                    "started_at": row[5].isoformat() if row[5] else None,
                    "status": row[3],
                    "updated_at": row[12].isoformat() if row[12] else None,
                }
            )
        return items

    def _load_pending_attribution_items(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, source_type, source_system, collector_run_id, raw_subject_id,
                   summary, raw_payload, suggested_product_id, suggested_module_code,
                   confidence, status, resolution_action, resolution_note,
                   resolved_product_id, resolved_module_code, resolved_requirement_id,
                   resolved_subject_type, resolved_subject_id, resolved_by, resolved_at,
                   created_by, created_at, updated_at
            FROM pending_attribution_items
            ORDER BY created_at, id
            """
        )
        return {
            item["id"]: item
            for item in self._pending_attribution_items_from_rows(cursor.fetchall())
        }

    def _pending_attribution_items_from_rows(self, rows: list[Any]) -> list[dict[str, Any]]:
        items = []
        for row in rows:
            raw_payload = row[6] or {}
            if isinstance(raw_payload, str):
                raw_payload = json.loads(raw_payload)
            items.append(
                {
                    "collector_run_id": row[3],
                    "confidence": float(row[9]) if row[9] is not None else None,
                    "created_at": row[21].isoformat() if row[21] else None,
                    "created_by": row[20],
                    "id": row[0],
                    "raw_payload": raw_payload,
                    "raw_subject_id": row[4],
                    "resolution_action": row[11],
                    "resolution_note": row[12],
                    "resolved_at": row[19].isoformat() if row[19] else None,
                    "resolved_by": row[18],
                    "resolved_module_code": row[14],
                    "resolved_product_id": row[13],
                    "resolved_requirement_id": row[15],
                    "resolved_subject_id": row[17],
                    "resolved_subject_type": row[16],
                    "source_system": row[2],
                    "source_type": row[1],
                    "status": row[10],
                    "suggested_module_code": row[8],
                    "suggested_product_id": row[7],
                    "summary": row[5],
                    "updated_at": row[22].isoformat() if row[22] else None,
                }
            )
        return items
