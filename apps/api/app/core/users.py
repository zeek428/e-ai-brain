from __future__ import annotations

from copy import deepcopy
from time import sleep
from typing import Any

from app.core.db import DatabaseConnectionPool
from app.core.listing import list_text_matches, sort_list_items
from app.core.security import hash_password

ADMIN_PASSWORD_HASH = (
    "pbkdf2_sha256$210000$admin-local-salt$"
    "KntdecyMHyH2xHE5T1MpTcNqUSw77BzqFUHEEHh6IcI"
)
REVIEWER_PASSWORD_HASH = (
    "pbkdf2_sha256$210000$reviewer-local-salt$"
    "2y8_7B-H676ivrW5jN7hGbvcmzq55VeL1RhrqRlZyXA"
)

SEEDED_USERS = {
    "admin@example.com": {
        "display_name": "AI Brain Admin",
        "id": "user_admin",
        "password_hash": ADMIN_PASSWORD_HASH,
        "roles": ["admin"],
        "status": "active",
        "username": "admin@example.com",
    },
    "reviewer@example.com": {
        "display_name": "AI Brain Reviewer",
        "id": "user_reviewer",
        "password_hash": REVIEWER_PASSWORD_HASH,
        "roles": ["reviewer"],
        "status": "active",
        "username": "reviewer@example.com",
    },
}


class MemoryUserRepository:
    def __init__(self, users: dict[str, dict[str, Any]] | None = None) -> None:
        self.users = deepcopy(users or {})

    @classmethod
    def seeded(cls) -> MemoryUserRepository:
        return cls(SEEDED_USERS)

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        user = self.users.get(username)
        if user is None or user.get("status") != "active":
            return None
        return deepcopy(user)

    def list_users(self) -> list[dict[str, Any]]:
        return [self._public_user(user) for user in self.users.values()]

    def list_user_summaries(
        self,
        *,
        display_name: str | None = None,
        page: int = 1,
        page_size: int = 10,
        role: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
        status: str | None = None,
        username: str | None = None,
    ) -> dict[str, Any]:
        items = [
            item
            for item in self.list_users()
            if list_text_matches(item, username, ("username",))
            and list_text_matches(item, display_name, ("display_name",))
            and (not status or item.get("status") == status)
            and (not role or role in item.get("roles", []))
        ]
        sorted_items = sort_list_items(
            items,
            allowed_fields={"created_at", "display_name", "id", "status", "username"},
            default_sort_by="username",
            sort_by=sort_by,
            sort_order=sort_order,
        )
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "items": sorted_items[start:end],
            "page": page,
            "page_size": page_size,
            "total": len(sorted_items),
        }

    def create_user(
        self,
        *,
        display_name: str,
        password: str,
        roles: list[str],
        status: str,
        username: str,
    ) -> dict[str, Any]:
        if username in self.users:
            raise ValueError("user_exists")
        user = {
            "display_name": display_name,
            "id": f"user_{len(self.users) + 1:03d}",
            "password_hash": hash_password(password),
            "roles": roles,
            "status": status,
            "username": username,
        }
        self.users[username] = user
        return self._public_user(user)

    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        user = next((item for item in self.users.values() if item["id"] == user_id), None)
        if user is None:
            return None
        if "display_name" in updates:
            user["display_name"] = updates["display_name"]
        if "roles" in updates:
            user["roles"] = updates["roles"]
        if "status" in updates:
            user["status"] = updates["status"]
        if "password" in updates:
            user["password_hash"] = hash_password(updates["password"])
        return self._public_user(user)

    def delete_user(self, user_id: str) -> bool:
        username = next(
            (key for key, user in self.users.items() if user["id"] == user_id),
            None,
        )
        if username is None:
            return False
        del self.users[username]
        return True

    def _public_user(self, user: dict[str, Any]) -> dict[str, Any]:
        return {
            "display_name": user["display_name"],
            "id": user["id"],
            "roles": list(user["roles"]),
            "status": user.get("status", "active"),
            "username": user["username"],
        }


class PostgresUserRepository:
    def __init__(self, database_url: str, *, pool_max_size: int = 5) -> None:
        self.database_url = database_url
        self._pool = DatabaseConnectionPool(
            factory=self._open_connection,
            max_size=pool_max_size,
        )

    def _open_connection(self):
        import psycopg

        last_error: Exception | None = None
        for _ in range(20):
            try:
                return psycopg.connect(self.database_url)
            except psycopg.OperationalError as exc:
                last_error = exc
                sleep(0.5)
        raise last_error or RuntimeError("PostgreSQL connection failed")

    def _connect(self):
        return self._pool.connection(autocommit=True)

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, email, display_name, roles, password_hash, status
                    FROM users
                    WHERE email = %s AND status = 'active'
                    """,
                    (username,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        user_id, email, display_name, roles, password_hash, status = row
        return {
            "display_name": display_name,
            "id": user_id,
            "password_hash": password_hash,
            "roles": list(roles),
            "status": status,
            "username": email,
        }

    def list_users(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, email, display_name, roles, status
                    FROM users
                    ORDER BY created_at DESC, email ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            {
                "display_name": display_name,
                "id": user_id,
                "roles": list(roles),
                "status": status,
                "username": email,
            }
            for user_id, email, display_name, roles, status in rows
        ]

    def list_user_summaries(
        self,
        *,
        display_name: str | None = None,
        page: int = 1,
        page_size: int = 10,
        role: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
        status: str | None = None,
        username: str | None = None,
    ) -> dict[str, Any]:
        sort_columns = {
            "created_at": "created_at",
            "display_name": "display_name",
            "id": "id",
            "status": "status",
            "username": "email",
        }
        resolved_sort_by = sort_columns.get(sort_by or "created_at")
        if resolved_sort_by is None:
            from app.core.listing import api_validation_error

            raise api_validation_error("Unsupported sort_by")
        if sort_order not in {"asc", "desc"}:
            from app.core.listing import api_validation_error

            raise api_validation_error("Unsupported sort_order")

        filters: list[str] = []
        values: list[Any] = []
        if username:
            filters.append("email ILIKE %s")
            values.append(f"%{username}%")
        if display_name:
            filters.append("display_name ILIKE %s")
            values.append(f"%{display_name}%")
        if status:
            filters.append("status = %s")
            values.append(status)
        if role:
            filters.append("roles ? %s")
            values.append(role)
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
        offset = max(page - 1, 0) * page_size
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT count(*)
                    FROM users
                    {where_sql}
                    """,
                    values,
                )
                total = int(cursor.fetchone()[0])
                cursor.execute(
                    f"""
                    SELECT id, email, display_name, roles, status
                    FROM users
                    {where_sql}
                    ORDER BY {resolved_sort_by} {sort_order.upper()}, email ASC
                    LIMIT %s OFFSET %s
                    """,
                    [*values, page_size, offset],
                )
                rows = cursor.fetchall()
        return {
            "items": [
                {
                    "display_name": display_name_value,
                    "id": user_id,
                    "roles": list(roles),
                    "status": status_value,
                    "username": email,
                }
                for user_id, email, display_name_value, roles, status_value in rows
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def create_user(
        self,
        *,
        display_name: str,
        password: str,
        roles: list[str],
        status: str,
        username: str,
    ) -> dict[str, Any]:
        user_id = f"user_{username.replace('@', '_').replace('.', '_')}"
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (id, email, display_name, roles, password_hash, status)
                        VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                        """,
                        (
                            user_id,
                            username,
                            display_name,
                            _json_dumps(roles),
                            hash_password(password),
                            status,
                        ),
                    )
        except Exception as exc:
            if getattr(exc, "sqlstate", "") == "23505":
                raise ValueError("user_exists") from exc
            raise
        return {
            "display_name": display_name,
            "id": user_id,
            "roles": roles,
            "status": status,
            "username": username,
        }

    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = next((user for user in self.list_users() if user["id"] == user_id), None)
        if current is None:
            return None
        fields: list[str] = []
        values: list[Any] = []
        if "display_name" in updates:
            fields.append("display_name = %s")
            values.append(updates["display_name"])
        if "roles" in updates:
            fields.append("roles = %s::jsonb")
            values.append(_json_dumps(updates["roles"]))
        if "status" in updates:
            fields.append("status = %s")
            values.append(updates["status"])
        if "password" in updates:
            fields.append("password_hash = %s")
            values.append(hash_password(updates["password"]))
        if fields:
            values.append(user_id)
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE users SET {', '.join(fields)}, updated_at = now() WHERE id = %s",
                        values,
                    )
        return next((user for user in self.list_users() if user["id"] == user_id), None)

    def delete_user(self, user_id: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM users WHERE id = %s",
                    (user_id,),
                )
                return cursor.rowcount > 0


def _json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)
