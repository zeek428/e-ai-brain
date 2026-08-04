from __future__ import annotations

from collections.abc import Callable
from typing import Any


def active_scopes_for_user(
    connect: Callable[[], Any],
    user_id: str,
) -> list[dict[str, Any]]:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT scope_type, scope_id, access_level
                FROM user_scope_grants
                WHERE user_id = %s AND status = 'active'
                ORDER BY scope_type, scope_id, access_level
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
    return [
        {"scope_type": scope_type, "scope_id": scope_id, "access_level": access_level}
        for scope_type, scope_id, access_level in rows
    ]
