from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from copy import deepcopy
from typing import Any


class BugReadRepository:
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

    def load_bugs(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                bugs = self._load_bugs(cursor)
        return {"bugs": bugs}

    def save_bugs(self, payload: dict[str, Any]) -> None:
        bugs = self.clean_bug_references(payload.get("bugs", {}))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.clear_dangling_bug_duplicates(cursor, bugs)
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "bugs", bugs)
                self.upsert_bugs(cursor, bugs)

    def save_bug_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_bugs(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_bug_record(
        self,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE bugs
                    SET duplicate_of_bug_id = NULL, updated_at = now()
                    WHERE duplicate_of_bug_id = %s
                    """,
                    (record_id,),
                )
                cursor.execute("DELETE FROM bugs WHERE id = %s", (record_id,))
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def clean_bug_references(
        self,
        bugs: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        cleaned = deepcopy(bugs)
        for bug_id, bug in cleaned.items():
            duplicate_of_bug_id = bug.get("duplicate_of_bug_id")
            if duplicate_of_bug_id == bug_id or duplicate_of_bug_id not in cleaned:
                bug["duplicate_of_bug_id"] = None
        return cleaned

    def clear_dangling_bug_duplicates(
        self,
        cursor,
        bugs: dict[str, dict[str, Any]],
    ) -> None:
        if not bugs:
            cursor.execute("UPDATE bugs SET duplicate_of_bug_id = NULL")
            return
        placeholders = ", ".join(["%s"] * len(bugs))
        cursor.execute(
            f"""
            UPDATE bugs
            SET duplicate_of_bug_id = NULL
            WHERE duplicate_of_bug_id IS NOT NULL
              AND duplicate_of_bug_id NOT IN ({placeholders})
            """,  # noqa: S608
            tuple(bugs.keys()),
        )

    def upsert_bugs(self, cursor, bugs: dict[str, dict[str, Any]]) -> None:
        for bug in bugs.values():
            created_at = bug.get("created_at")
            updated_at = bug.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO bugs (
                  id, product_id, version_id, module_code, source, title, severity,
                  description, status, assignee, related_task_id, requirement_id,
                  reproduce_steps, evidence, duplicate_of_bug_id, created_by,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s::jsonb, NULL, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  source = EXCLUDED.source,
                  title = EXCLUDED.title,
                  severity = EXCLUDED.severity,
                  description = EXCLUDED.description,
                  status = EXCLUDED.status,
                  assignee = EXCLUDED.assignee,
                  related_task_id = EXCLUDED.related_task_id,
                  requirement_id = EXCLUDED.requirement_id,
                  reproduce_steps = EXCLUDED.reproduce_steps,
                  evidence = EXCLUDED.evidence,
                  duplicate_of_bug_id = NULL,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    bug["id"],
                    bug["product_id"],
                    bug.get("version_id"),
                    bug.get("module_code"),
                    bug["source"],
                    bug["title"],
                    bug["severity"],
                    bug["description"],
                    bug.get("status", "open"),
                    bug.get("assignee"),
                    bug.get("related_task_id"),
                    bug.get("requirement_id"),
                    json.dumps(bug.get("reproduce_steps", []), ensure_ascii=False),
                    json.dumps(bug.get("evidence", {}), ensure_ascii=False),
                    bug["created_by"],
                    created_at,
                    updated_at,
                ),
            )
        for bug in bugs.values():
            duplicate_of_bug_id = bug.get("duplicate_of_bug_id")
            if duplicate_of_bug_id:
                cursor.execute(
                    """
                    UPDATE bugs
                    SET duplicate_of_bug_id = %s, updated_at = COALESCE(%s::timestamptz, updated_at)
                    WHERE id = %s
                    """,
                    (duplicate_of_bug_id, bug.get("updated_at"), bug["id"]),
                )

    def _bug_summary_where(
        self,
        *,
        module: str | None = None,
        product_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if module is not None:
            where_clauses.append("b.module_code ILIKE %s")
            params.append(f"%{module}%")
        if product_id is not None:
            where_clauses.append("b.product_id = %s")
            params.append(product_id)
        if severity is not None:
            where_clauses.append("b.severity = %s")
            params.append(severity)
        if source is not None:
            where_clauses.append("b.source = %s")
            params.append(source)
        if status is not None:
            where_clauses.append("b.status = %s")
            params.append(status)
        if title is not None:
            title_pattern = f"%{title}%"
            where_clauses.append("(b.title ILIKE %s OR b.id ILIKE %s)")
            params.extend([title_pattern, title_pattern])
        if version is not None:
            version_pattern = f"%{version}%"
            where_clauses.append("(v.code ILIKE %s OR v.name ILIKE %s OR b.version_id ILIKE %s)")
            params.extend([version_pattern, version_pattern, version_pattern])
        if version_id is not None:
            where_clauses.append("b.version_id = %s")
            params.append(version_id)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_clause, params

    def count_bug_summaries(
        self,
        *,
        module: str | None = None,
        product_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> int:
        where_clause, params = self._bug_summary_where(
            module=module,
            product_id=product_id,
            severity=severity,
            source=source,
            status=status,
            title=title,
            version=version,
            version_id=version_id,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM bugs b
                    LEFT JOIN product_versions v ON v.id = b.version_id
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_bug_summaries(
        self,
        *,
        module: str | None = None,
        product_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        where_clause, params = self._bug_summary_where(
            module=module,
            product_id=product_id,
            severity=severity,
            source=source,
            status=status,
            title=title,
            version=version,
            version_id=version_id,
        )
        sort_columns = {
            "assignee": "b.assignee",
            "created_at": "b.created_at",
            "id": "b.id",
            "module_code": "b.module_code",
            "severity": "b.severity",
            "source": "b.source",
            "status": "b.status",
            "title": "b.title",
            "updated_at": "COALESCE(b.updated_at, b.created_at)",
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
                    SELECT b.id, b.product_id, b.version_id, b.module_code, b.source, b.title,
                           b.severity, b.description, b.status, b.assignee, b.related_task_id,
                           b.requirement_id, b.reproduce_steps, b.evidence, b.duplicate_of_bug_id,
                           b.created_by, b.created_at, b.updated_at, v.code, v.name
                    FROM bugs b
                    LEFT JOIN product_versions v ON v.id = b.version_id
                    {where_clause}
                    ORDER BY {order_column} {order_direction}, b.id ASC
                    {paging_clause}
                    """,
                    tuple(params),
                )
                bugs = []
                for row in cursor.fetchall():
                    bug = _bug_from_row(row)
                    bug["version_code"] = row[18]
                    bug["version_name"] = row[19]
                    for optional_key in ("version_code", "version_name"):
                        if bug[optional_key] is None:
                            bug.pop(optional_key)
                    bugs.append(bug)
                return bugs

    def _load_bugs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, version_id, module_code, source, title, severity,
                   description, status, assignee, related_task_id, requirement_id,
                   reproduce_steps, evidence, duplicate_of_bug_id, created_by,
                   created_at, updated_at
            FROM bugs
            ORDER BY created_at, id
            """
        )
        return {row[0]: _bug_from_row(row) for row in cursor.fetchall()}


def _bug_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    bug = {
        "assignee": row[9],
        "created_at": row[16].isoformat() if row[16] else None,
        "created_by": row[15],
        "description": row[7],
        "duplicate_of_bug_id": row[14],
        "evidence": dict(row[13] or {}),
        "id": row[0],
        "module_code": row[3],
        "product_id": row[1],
        "related_task_id": row[10],
        "reproduce_steps": list(row[12] or []),
        "requirement_id": row[11],
        "severity": row[6],
        "source": row[4],
        "status": row[8],
        "title": row[5],
        "updated_at": row[17].isoformat() if row[17] else None,
        "version_id": row[2],
    }
    for optional_key in (
        "assignee",
        "created_at",
        "duplicate_of_bug_id",
        "module_code",
        "related_task_id",
        "requirement_id",
        "updated_at",
        "version_id",
    ):
        if bug[optional_key] is None:
            bug.pop(optional_key)
    return bug
