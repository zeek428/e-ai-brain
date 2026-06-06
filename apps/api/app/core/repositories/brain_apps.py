from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class BrainAppReadRepository:
    def __init__(self, connect: Callable[..., AbstractContextManager[Any]]) -> None:
        self._connect = connect

    def load_brain_apps(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, code, name, description, status, config, created_at, updated_at
                    FROM brain_apps
                    ORDER BY code
                    """
                )
                brain_apps = {
                    row[0]: {
                        "code": row[1],
                        "config": dict(row[5] or {}),
                        "created_at": row[6].isoformat() if row[6] else None,
                        "description": row[3],
                        "id": row[0],
                        "name": row[2],
                        "status": row[4],
                        "updated_at": row[7].isoformat() if row[7] else None,
                    }
                    for row in cursor.fetchall()
                }
        return {"brain_apps": brain_apps}
