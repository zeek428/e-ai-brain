from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.persistence_fields import ID_COUNTER_SOURCE_TABLES, STATE_KEY


class SystemStateRepository:
    def __init__(self, connect: Callable[..., AbstractContextManager[Any]]) -> None:
        self._connect = connect

    def next_id(self, prefix: str) -> str:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute("LOCK TABLE id_counters IN EXCLUSIVE MODE")
                cursor.execute(
                    "SELECT next_value FROM id_counters WHERE prefix = %s",
                    (prefix,),
                )
                row = cursor.fetchone()
                if row is None:
                    used_value = self._max_existing_id_suffix(cursor, prefix) + 1
                    cursor.execute(
                        """
                        INSERT INTO id_counters (prefix, next_value)
                        VALUES (%s, %s)
                        """,
                        (prefix, used_value + 1),
                    )
                else:
                    used_value = int(row[0])
                    cursor.execute(
                        """
                        UPDATE id_counters
                        SET next_value = %s, updated_at = now()
                        WHERE prefix = %s
                        """,
                        (used_value + 1, prefix),
                    )
        return f"{prefix}_{used_value:03d}"

    def load_snapshot(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM app_state_snapshots WHERE key = %s",
                    (STATE_KEY,),
                )
                row = cursor.fetchone()
        return row[0] if row else None

    def save_snapshot(self, payload: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_state_snapshots (key, payload, updated_at)
                    VALUES (%s, %s::jsonb, now())
                    ON CONFLICT (key) DO UPDATE SET
                      payload = EXCLUDED.payload,
                      updated_at = now()
                    """,
                    (STATE_KEY, json.dumps(payload, ensure_ascii=False)),
                )

    def _max_existing_id_suffix(self, cursor, prefix: str) -> int:
        marker = f"{prefix}_"
        max_value = 0
        for table_name in ID_COUNTER_SOURCE_TABLES:
            cursor.execute(
                f"SELECT id FROM {table_name} WHERE id LIKE %s",
                (f"{marker}%",),
            )
            for row in cursor.fetchall():
                item_id = str(row[0])
                suffix = item_id.removeprefix(marker)
                if suffix.isdigit():
                    max_value = max(max_value, int(suffix))
        return max_value
