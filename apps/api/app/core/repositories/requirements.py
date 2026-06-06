from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.store import DEFAULT_BRAIN_APP_ID


class RequirementReadRepository:
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

    def load_requirements(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                requirements = self._load_requirements(cursor)
        return {"requirements": requirements}

    def save_requirements(self, payload: dict[str, Any]) -> None:
        requirements = payload.get("requirements", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "requirements", requirements)
                self.upsert_requirements(cursor, requirements)

    def save_requirement_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_requirements(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_requirement_record(
        self,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM requirements WHERE id = %s", (record_id,))
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def upsert_requirements(self, cursor, requirements: dict[str, dict[str, Any]]) -> None:
        for requirement in requirements.values():
            created_at = requirement.get("created_at")
            updated_at = requirement.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO requirements (
                  id, brain_app_id, title, product_id, version_id, module_code,
                  description, priority,
                  status, created_by, assignee, approval_comment, rejection_reason, task_ids,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  brain_app_id = EXCLUDED.brain_app_id,
                  title = EXCLUDED.title,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  description = EXCLUDED.description,
                  priority = EXCLUDED.priority,
                  status = EXCLUDED.status,
                  created_by = EXCLUDED.created_by,
                  assignee = EXCLUDED.assignee,
                  approval_comment = EXCLUDED.approval_comment,
                  rejection_reason = EXCLUDED.rejection_reason,
                  task_ids = EXCLUDED.task_ids,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    requirement["id"],
                    requirement.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
                    requirement["title"],
                    requirement["product_id"],
                    requirement["version_id"],
                    requirement.get("module_code"),
                    requirement["content"],
                    requirement.get("priority", "P1"),
                    requirement.get("status", "submitted"),
                    requirement["created_by"],
                    requirement.get("assignee"),
                    requirement.get("approval_comment"),
                    requirement.get("rejection_reason"),
                    json.dumps(requirement.get("task_ids", []), ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def _requirement_summary_where(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if priority is not None:
            where_clauses.append("r.priority = %s")
            params.append(priority)
        if product is not None:
            product_pattern = f"%{product}%"
            where_clauses.append("(p.code ILIKE %s OR p.name ILIKE %s OR r.product_id ILIKE %s)")
            params.extend([product_pattern, product_pattern, product_pattern])
        if product_id is not None:
            where_clauses.append("r.product_id = %s")
            params.append(product_id)
        if status is not None:
            where_clauses.append(
                """
                CASE r.status
                    WHEN 'pending_approval' THEN 'submitted'
                    WHEN 'task_created' THEN 'designing'
                    ELSE r.status
                END = %s
                """
            )
            params.append(status)
        if title is not None:
            title_pattern = f"%{title}%"
            where_clauses.append("(r.title ILIKE %s OR r.id ILIKE %s)")
            params.extend([title_pattern, title_pattern])
        if version is not None:
            version_pattern = f"%{version}%"
            where_clauses.append("(v.code ILIKE %s OR v.name ILIKE %s OR r.version_id ILIKE %s)")
            params.extend([version_pattern, version_pattern, version_pattern])
        if version_id is not None:
            where_clauses.append("r.version_id = %s")
            params.append(version_id)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_clause, params

    def count_requirement_summaries(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> int:
        where_clause, params = self._requirement_summary_where(
            priority=priority,
            product=product,
            product_id=product_id,
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
                    FROM requirements r
                    JOIN products p ON p.id = r.product_id
                    LEFT JOIN product_versions v ON v.id = r.version_id
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_requirement_summaries(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        where_clause, params = self._requirement_summary_where(
            priority=priority,
            product=product,
            product_id=product_id,
            status=status,
            title=title,
            version=version,
            version_id=version_id,
        )
        sort_columns = {
            "created_at": "r.created_at",
            "id": "r.id",
            "priority": "r.priority",
            "product_code": "p.code",
            "product_name": "p.name",
            "status": "r.status",
            "assignee": "r.assignee",
            "title": "r.title",
            "updated_at": "COALESCE(r.updated_at, r.created_at)",
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
                    SELECT r.id, r.brain_app_id, r.title, r.product_id, r.version_id,
                           r.module_code, r.description, r.priority, r.status, r.created_by,
                           r.approval_comment, r.rejection_reason, r.task_ids,
                           r.created_at, r.updated_at, p.code, p.name, v.code, v.name,
                           r.assignee
                    FROM requirements r
                    JOIN products p ON p.id = r.product_id
                    LEFT JOIN product_versions v ON v.id = r.version_id
                    {where_clause}
                    ORDER BY {order_column} {order_direction}, r.id ASC
                    {paging_clause}
                    """,
                    tuple(params),
                )
                requirements = []
                for row in cursor.fetchall():
                    requirement = {
                        "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                        "content": row[6],
                        "created_at": row[13].isoformat() if row[13] else None,
                        "created_by": row[9],
                        "assignee": row[19],
                        "id": row[0],
                        "module_code": row[5],
                        "priority": row[7],
                        "product_code": row[15],
                        "product_id": row[3],
                        "product_name": row[16],
                        "status": row[8],
                        "task_ids": list(row[12] or []),
                        "title": row[2],
                        "updated_at": row[14].isoformat() if row[14] else None,
                        "version_code": row[17],
                        "version_id": row[4],
                        "version_name": row[18],
                    }
                    if row[10] is not None:
                        requirement["approval_comment"] = row[10]
                    if row[11] is not None:
                        requirement["rejection_reason"] = row[11]
                    requirements.append(requirement)
                return requirements

    def _load_requirements(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, brain_app_id, title, product_id, version_id, module_code,
                   description, priority,
                   status, created_by, approval_comment, rejection_reason, task_ids,
                   assignee,
                   created_at, updated_at
            FROM requirements
            ORDER BY created_at DESC, id
            """
        )
        requirements = {}
        for row in cursor.fetchall():
            requirement = _requirement_from_row(row)
            if row[10] is not None:
                requirement["approval_comment"] = row[10]
            if row[11] is not None:
                requirement["rejection_reason"] = row[11]
            requirements[row[0]] = requirement
        return requirements


def _requirement_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
        "content": row[6],
        "created_at": row[14].isoformat() if row[14] else None,
        "created_by": row[9],
        "assignee": row[13],
        "id": row[0],
        "module_code": row[5],
        "priority": row[7],
        "product_id": row[3],
        "status": row[8],
        "task_ids": list(row[12] or []),
        "title": row[2],
        "updated_at": row[15].isoformat() if row[15] else None,
        "version_id": row[4],
    }
