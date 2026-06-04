from __future__ import annotations

from copy import deepcopy
from time import sleep
from typing import Any

from app.core.db import DatabaseConnectionPool
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
