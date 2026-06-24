from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


def _json(value: Any, default: Any) -> str:
    if value is None:
        value = default
    return json.dumps(value, ensure_ascii=False)


class ExecutionTraceReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
    ) -> None:
        self._connect = connect

    def refresh_execution_trace_snapshots(self, traces: list[dict[str, Any]]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_execution_trace_snapshots(cursor, traces)
                trace_ids = [str(trace["id"]) for trace in traces if trace.get("id")]
                if trace_ids:
                    cursor.execute(
                        "DELETE FROM execution_trace_snapshots WHERE NOT (id = ANY(%s))",
                        (trace_ids,),
                    )
                else:
                    cursor.execute("DELETE FROM execution_trace_snapshots")

    def count_execution_trace_snapshots(
        self,
        *,
        created_from: Any = None,
        created_to: Any = None,
        keyword: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> int:
        where_clause, params = self._snapshot_where(
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            source_id=source_id,
            source_type=source_type,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM execution_trace_snapshots {where_clause}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_execution_trace_snapshots(
        self,
        *,
        created_from: Any = None,
        created_to: Any = None,
        keyword: str | None = None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        source_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause, params = self._snapshot_where(
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            source_id=source_id,
            source_type=source_type,
            status=status,
        )
        sort_column = self._sort_column(sort_by)
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, root_type, root_id, title, summary, status, started_at,
                           updated_at, duration_ms, node_count, failed_node_count,
                           running_node_count, related_ids, nodes, edges, source_fingerprint,
                           built_at, created_at
                    FROM execution_trace_snapshots
                    {where_clause}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [self._snapshot_from_row(row) for row in cursor.fetchall()]

    def get_execution_trace_snapshot(self, trace_id: str) -> dict[str, Any] | None:
        related_probe = f"%{trace_id}%"
        node_probe = json.dumps([{"source_id": trace_id}], ensure_ascii=False)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, root_type, root_id, title, summary, status, started_at,
                           updated_at, duration_ms, node_count, failed_node_count,
                           running_node_count, related_ids, nodes, edges, source_fingerprint,
                           built_at, created_at
                    FROM execution_trace_snapshots
                    WHERE id = %s
                       OR root_id = %s
                       OR nodes @> %s::jsonb
                       OR related_ids::text LIKE %s
                    ORDER BY started_at DESC NULLS LAST, id DESC
                    LIMIT 1
                    """,
                    (trace_id, trace_id, node_probe, related_probe),
                )
                row = cursor.fetchone()
                return self._snapshot_from_row(row) if row else None

    def upsert_execution_trace_snapshots(self, cursor, traces: list[dict[str, Any]]) -> None:
        for trace in traces:
            cursor.execute(
                """
                INSERT INTO execution_trace_snapshots (
                  id, root_type, root_id, title, summary, status, started_at, updated_at,
                  duration_ms, node_count, failed_node_count, running_node_count,
                  related_ids, nodes, edges, source_fingerprint, built_at, created_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s, now(), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  root_type = EXCLUDED.root_type,
                  root_id = EXCLUDED.root_id,
                  title = EXCLUDED.title,
                  summary = EXCLUDED.summary,
                  status = EXCLUDED.status,
                  started_at = EXCLUDED.started_at,
                  updated_at = EXCLUDED.updated_at,
                  duration_ms = EXCLUDED.duration_ms,
                  node_count = EXCLUDED.node_count,
                  failed_node_count = EXCLUDED.failed_node_count,
                  running_node_count = EXCLUDED.running_node_count,
                  related_ids = EXCLUDED.related_ids,
                  nodes = EXCLUDED.nodes,
                  edges = EXCLUDED.edges,
                  source_fingerprint = EXCLUDED.source_fingerprint,
                  built_at = now()
                """,
                (
                    trace["id"],
                    trace["root_type"],
                    trace["root_id"],
                    trace.get("title") or trace["id"],
                    trace.get("summary") or "",
                    trace.get("status") or "unknown",
                    trace.get("started_at"),
                    trace.get("updated_at"),
                    trace.get("duration_ms"),
                    trace.get("node_count", 0),
                    trace.get("failed_node_count", 0),
                    trace.get("running_node_count", 0),
                    _json(trace.get("related_ids"), {}),
                    _json(trace.get("nodes"), []),
                    _json(trace.get("edges"), []),
                    self._source_fingerprint(trace),
                    trace.get("started_at") or trace.get("updated_at"),
                ),
            )

    def _snapshot_where(
        self,
        *,
        created_from: Any = None,
        created_to: Any = None,
        keyword: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if source_type:
            clauses.append("(root_type = %s OR nodes @> %s::jsonb)")
            params.extend([
                source_type,
                json.dumps([{"source_type": source_type}], ensure_ascii=False),
            ])
        if status:
            clauses.append("status = %s")
            params.append(status)
        normalized_source_id = str(source_id or "").strip()
        if normalized_source_id:
            params.extend(
                [
                    normalized_source_id,
                    normalized_source_id,
                    json.dumps([{"source_id": normalized_source_id}], ensure_ascii=False),
                    normalized_source_id,
                ]
            )
            clauses.append(
                """
                (
                  id = %s
                  OR root_id = %s
                  OR nodes @> %s::jsonb
                  OR EXISTS (
                    SELECT 1
                    FROM jsonb_each(related_ids) AS related(key, value)
                    WHERE related.value @> to_jsonb(ARRAY[%s]::text[])
                  )
                )
                """
            )
        if created_from is not None:
            clauses.append("COALESCE(started_at, updated_at, created_at) >= %s")
            params.append(created_from)
        if created_to is not None:
            clauses.append("COALESCE(started_at, updated_at, created_at) <= %s")
            params.append(created_to)
        normalized_keyword = str(keyword or "").strip()
        if normalized_keyword:
            params.append(f"%{normalized_keyword.lower()}%")
            clauses.append(
                """
                (
                  lower(id) LIKE %s
                  OR lower(root_id) LIKE %s
                  OR lower(root_type) LIKE %s
                  OR lower(title) LIKE %s
                  OR lower(summary) LIKE %s
                  OR lower(related_ids::text) LIKE %s
                )
                """
            )
            params.extend([params[-1]] * 5)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        return where_clause, params

    def _sort_column(self, sort_by: str) -> str:
        sort_columns = {
            "duration_ms": "duration_ms",
            "failed_node_count": "failed_node_count",
            "id": "id",
            "node_count": "node_count",
            "root_type": "root_type",
            "started_at": "started_at",
            "status": "status",
            "updated_at": "updated_at",
        }
        return sort_columns.get(sort_by, "started_at")

    def _snapshot_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "built_at": row[16].isoformat() if row[16] else None,
            "created_at": row[17].isoformat() if row[17] else None,
            "duration_ms": row[8],
            "edges": list(row[14] or []),
            "failed_node_count": row[10],
            "id": row[0],
            "node_count": row[9],
            "nodes": list(row[13] or []),
            "related_ids": dict(row[12] or {}),
            "root_id": row[2],
            "root_type": row[1],
            "running_node_count": row[11],
            "source_fingerprint": row[15],
            "started_at": row[6].isoformat() if row[6] else None,
            "status": row[5],
            "summary": row[4],
            "title": row[3],
            "updated_at": row[7].isoformat() if row[7] else None,
        }

    def _source_fingerprint(self, trace: dict[str, Any]) -> str:
        payload = {
            "edges": trace.get("edges") or [],
            "nodes": trace.get("nodes") or [],
            "related_ids": trace.get("related_ids") or {},
            "status": trace.get("status"),
            "updated_at": trace.get("updated_at"),
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
