from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from copy import deepcopy
from typing import Any


class MockWritebackReadRepository:
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

    def load_mock_writebacks(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                writebacks = self._load_mock_writebacks(cursor)
        return {"mock_writebacks": writebacks}

    def save_mock_writebacks(self, payload: dict[str, Any]) -> None:
        issues = self.mock_issue_rows(payload.get("mock_writebacks", {}))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is None:
                    raise RuntimeError("Mock writeback delete callback is not configured")
                self._delete_missing(cursor, "mock_issues", issues)
                self.upsert_mock_issues(cursor, issues)

    def save_mock_writeback_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        issues = self.mock_issue_rows({"current": record})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_mock_issues(cursor, issues)
                if audit_event is not None:
                    if self._upsert_audit_events is None:
                        raise RuntimeError("Audit upsert callback is not configured")
                    self._upsert_audit_events(cursor, [audit_event])

    def _load_mock_writebacks(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, source_task_id, title, status, idempotency_key, payload,
                   created_at, updated_at
            FROM mock_issues
            ORDER BY created_at, id
            """
        )
        writebacks: dict[str, dict[str, Any]] = {}
        for row in cursor.fetchall():
            issue_payload = dict(row[5] or {})
            issue = {
                **issue_payload,
                "id": row[0],
                "source_task_id": row[1],
                "status": row[3],
                "title": row[2],
            }
            if row[6] is not None:
                issue["created_at"] = row[6].isoformat()
            if row[7] is not None:
                issue["updated_at"] = row[7].isoformat()
            idempotency_key = row[4]
            writeback = writebacks.setdefault(
                idempotency_key,
                {
                    "idempotency_key": idempotency_key,
                    "issues": [],
                    "status": "completed",
                    "task_id": row[1],
                },
            )
            writeback["issues"].append(issue)
        return writebacks

    def mock_issue_rows(
        self,
        writebacks: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        rows = {}
        for fallback_key, writeback in writebacks.items():
            idempotency_key = writeback.get("idempotency_key") or fallback_key
            task_id = writeback.get("task_id")
            for issue in writeback.get("issues", []):
                issue_id = issue.get("id")
                source_task_id = issue.get("source_task_id") or task_id
                if not issue_id or not source_task_id:
                    continue
                rows[str(issue_id)] = {
                    "id": str(issue_id),
                    "idempotency_key": idempotency_key,
                    "payload": deepcopy(issue),
                    "source_task_id": source_task_id,
                    "status": issue.get("status", "open"),
                    "title": issue["title"],
                }
        return rows

    def upsert_mock_issues(
        self,
        cursor,
        issues: dict[str, dict[str, Any]],
    ) -> None:
        for issue in issues.values():
            cursor.execute(
                """
                INSERT INTO mock_issues (
                  id, source_task_id, title, status, idempotency_key, payload,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::jsonb, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  source_task_id = EXCLUDED.source_task_id,
                  title = EXCLUDED.title,
                  status = EXCLUDED.status,
                  idempotency_key = EXCLUDED.idempotency_key,
                  payload = EXCLUDED.payload,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    issue["id"],
                    issue["source_task_id"],
                    issue["title"],
                    issue.get("status", "open"),
                    issue["idempotency_key"],
                    json.dumps(issue.get("payload", {}), ensure_ascii=False),
                    issue.get("payload", {}).get("created_at"),
                    issue.get("payload", {}).get("updated_at")
                    or issue.get("payload", {}).get("created_at"),
                ),
            )
