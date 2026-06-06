from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class AuditReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing_ids: Callable[[Any, str, list[str]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing_ids = delete_missing_ids

    def load_audit_events(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                audit_events = self._load_audit_events(cursor)
        return {"audit_events": audit_events}

    def list_audit_events(
        self,
        *,
        ai_task_id: str | None = None,
        actor_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        event_type: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if actor_id is not None:
            where_clauses.append("actor_id = %s")
            params.append(actor_id)
        if event_type is not None:
            where_clauses.append("event_type = %s")
            params.append(event_type)
        if ai_task_id is not None:
            where_clauses.append("ai_task_id = %s")
            params.append(ai_task_id)
        if subject_type is not None:
            where_clauses.append("subject_type = %s")
            params.append(subject_type)
        if subject_id is not None:
            where_clauses.append("subject_id = %s")
            params.append(subject_id)
        if created_from is not None:
            where_clauses.append("created_at >= %s")
            params.append(created_from)
        if created_to is not None:
            where_clauses.append("created_at <= %s")
            params.append(created_to)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id::text, event_type, actor_id, ai_task_id, subject_type,
                           subject_id, payload, sequence, created_at, updated_at
                    FROM audit_events
                    {where_clause}
                    ORDER BY sequence DESC, created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return self._audit_events_from_rows(cursor.fetchall())

    def save_audit_events(self, payload: dict[str, Any]) -> None:
        audit_events = payload.get("audit_events", [])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing_ids is not None:
                    self._delete_missing_ids(
                        cursor,
                        "audit_events",
                        [str(event["id"]) for event in audit_events if event.get("id")],
                    )
                self.upsert_audit_events(cursor, audit_events)

    def append_audit_event(self, audit_event: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_audit_events(cursor, [audit_event])

    def upsert_audit_events(self, cursor, audit_events: list[dict[str, Any]]) -> None:
        for event in audit_events:
            created_at = event.get("created_at")
            updated_at = event.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO audit_events (
                  id, event_type, actor_id, ai_task_id, subject_type, subject_id, payload,
                  sequence, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s::jsonb, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  event_type = EXCLUDED.event_type,
                  actor_id = EXCLUDED.actor_id,
                  ai_task_id = EXCLUDED.ai_task_id,
                  subject_type = EXCLUDED.subject_type,
                  subject_id = EXCLUDED.subject_id,
                  payload = EXCLUDED.payload,
                  sequence = EXCLUDED.sequence,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    event["id"],
                    event["event_type"],
                    event["actor_id"],
                    event.get("ai_task_id"),
                    event.get("subject_type"),
                    event.get("subject_id"),
                    json.dumps(event.get("payload", {}), ensure_ascii=False),
                    event.get("sequence", 0),
                    created_at,
                    updated_at,
                ),
            )

    def _load_audit_events(self, cursor) -> list[dict[str, Any]]:
        cursor.execute(
            """
            SELECT id::text, event_type, actor_id, ai_task_id, subject_type, subject_id,
                   payload, sequence, created_at, updated_at
            FROM audit_events
            ORDER BY sequence, created_at, id
            """
        )
        return self._audit_events_from_rows(cursor.fetchall())

    def _audit_events_from_rows(self, rows: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "actor_id": row[2],
                "ai_task_id": row[3],
                "created_at": row[8].isoformat() if row[8] else None,
                "event_type": row[1],
                "id": row[0],
                "payload": dict(row[6] or {}),
                "sequence": row[7],
                "subject_id": row[5],
                "subject_type": row[4],
                "updated_at": row[9].isoformat() if row[9] else None,
            }
            for row in rows
        ]
