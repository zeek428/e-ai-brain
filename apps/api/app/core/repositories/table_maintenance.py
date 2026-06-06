from __future__ import annotations

from typing import Any


class TableMaintenanceRepository:
    def delete_missing(
        self,
        cursor,
        table_name: str,
        items: dict[str, dict[str, Any]],
    ) -> None:
        if not items:
            cursor.execute(f"DELETE FROM {table_name}")  # noqa: S608
            return
        placeholders = ", ".join(["%s"] * len(items))
        cursor.execute(
            f"DELETE FROM {table_name} WHERE id NOT IN ({placeholders})",  # noqa: S608
            tuple(items.keys()),
        )

    def delete_missing_ids(self, cursor, table_name: str, item_ids: list[str]) -> None:
        if not item_ids:
            cursor.execute(f"DELETE FROM {table_name}")  # noqa: S608
            return
        placeholders = ", ".join(["%s"] * len(item_ids))
        cursor.execute(
            f"DELETE FROM {table_name} WHERE id NOT IN ({placeholders})",  # noqa: S608
            tuple(item_ids),
        )
