from __future__ import annotations

from copy import deepcopy
from time import sleep
from typing import Any
from uuid import uuid4

from app.core.db import DatabaseConnectionPool


class MemoryExternalIdentityRepository:
    def __init__(self) -> None:
        self.identities: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"external_identity_{self._counter:03d}"

    def find_active(self, provider: str, provider_subject: str) -> dict[str, Any] | None:
        for identity in self.identities.values():
            if (
                identity["provider"] == provider
                and identity["provider_subject"] == provider_subject
                and identity.get("status") == "active"
            ):
                return deepcopy(identity)
        return None

    def find_active_by_user(self, provider: str, user_id: str) -> dict[str, Any] | None:
        for identity in self.identities.values():
            if (
                identity["provider"] == provider
                and identity["user_id"] == user_id
                and identity.get("status") == "active"
            ):
                return deepcopy(identity)
        return None

    def upsert_identity(
        self,
        *,
        provider: str,
        provider_subject: str,
        profile: dict[str, Any],
        replace_existing_user_identity: bool = False,
        user_id: str,
    ) -> dict[str, Any]:
        active_identity = self.find_active(provider, provider_subject)
        if active_identity is not None and active_identity["user_id"] != user_id:
            raise ValueError("identity_conflict")
        active_user_identity = self.find_active_by_user(provider, user_id)
        if (
            active_user_identity is not None
            and active_user_identity["provider_subject"] != provider_subject
        ):
            if not replace_existing_user_identity:
                raise ValueError("user_identity_exists")
            self.identities[active_user_identity["id"]]["status"] = "unbound"
        existing_id = next(
            (
                identity_id
                for identity_id, identity in self.identities.items()
                if identity["provider"] == provider
                and identity["provider_subject"] == provider_subject
            ),
            None,
        )
        identity_id = existing_id or self._next_id()
        identity = {
            "avatar_url": profile.get("avatar_url"),
            "corp_id": profile.get("corp_id"),
            "corp_name": profile.get("corp_name"),
            "display_name": profile.get("display_name"),
            "email": profile.get("email"),
            "id": identity_id,
            "open_id": profile.get("open_id"),
            "provider": provider,
            "provider_subject": provider_subject,
            "status": "active",
            "union_id": profile.get("union_id"),
            "user_id": user_id,
        }
        self.identities[identity_id] = identity
        return deepcopy(identity)

    def unbind(self, *, provider: str, user_id: str) -> bool:
        identity = self.find_active_by_user(provider, user_id)
        if identity is None:
            return False
        self.identities[identity["id"]]["status"] = "unbound"
        return True

    def find_by_id(self, identity_id: str) -> dict[str, Any] | None:
        identity = self.identities.get(identity_id)
        return deepcopy(identity) if identity is not None else None

    def list_identities(
        self,
        *,
        provider: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            deepcopy(identity)
            for identity in self.identities.values()
            if (provider is None or identity.get("provider") == provider)
            and (status is None or identity.get("status") == status)
            and (user_id is None or identity.get("user_id") == user_id)
        ]

    def unbind_by_id(self, identity_id: str) -> bool:
        identity = self.identities.get(identity_id)
        if identity is None or identity.get("status") != "active":
            return False
        identity["status"] = "unbound"
        return True


class PostgresExternalIdentityRepository:
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

    def find_active(self, provider: str, provider_subject: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, provider, provider_subject, union_id, open_id,
                           corp_id, corp_name, display_name, email, avatar_url, status
                    FROM user_external_identities
                    WHERE provider = %s AND provider_subject = %s AND status = 'active'
                    """,
                    (provider, provider_subject),
                )
                row = cursor.fetchone()
        return self._identity_from_row(row)

    def find_active_by_user(self, provider: str, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, provider, provider_subject, union_id, open_id,
                           corp_id, corp_name, display_name, email, avatar_url, status
                    FROM user_external_identities
                    WHERE provider = %s AND user_id = %s AND status = 'active'
                    """,
                    (provider, user_id),
                )
                row = cursor.fetchone()
        return self._identity_from_row(row)

    def upsert_identity(
        self,
        *,
        provider: str,
        provider_subject: str,
        profile: dict[str, Any],
        replace_existing_user_identity: bool = False,
        user_id: str,
    ) -> dict[str, Any]:
        identity_id = f"external_identity_{uuid4().hex}"
        with self._pool.connection(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, provider, provider_subject, union_id, open_id,
                           corp_id, corp_name, display_name, email, avatar_url, status
                    FROM user_external_identities
                    WHERE provider = %s AND provider_subject = %s AND status = 'active'
                    FOR UPDATE
                    """,
                    (provider, provider_subject),
                )
                active_identity = self._identity_from_row(cursor.fetchone())
                if active_identity is not None and active_identity["user_id"] != user_id:
                    raise ValueError("identity_conflict")
                cursor.execute(
                    """
                    SELECT id, user_id, provider, provider_subject, union_id, open_id,
                           corp_id, corp_name, display_name, email, avatar_url, status
                    FROM user_external_identities
                    WHERE provider = %s AND user_id = %s AND status = 'active'
                    FOR UPDATE
                    """,
                    (provider, user_id),
                )
                active_user_identity = self._identity_from_row(cursor.fetchone())
                if (
                    active_user_identity is not None
                    and active_user_identity["provider_subject"] != provider_subject
                ):
                    if not replace_existing_user_identity:
                        raise ValueError("user_identity_exists")
                    cursor.execute(
                        """
                        UPDATE user_external_identities
                        SET status = 'unbound', updated_at = now()
                        WHERE id = %s
                        """,
                        (active_user_identity["id"],),
                    )
                try:
                    cursor.execute(
                        """
                        INSERT INTO user_external_identities (
                          id, user_id, provider, provider_subject, union_id, open_id,
                          corp_id, corp_name, display_name, email, avatar_url, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
                        ON CONFLICT (provider, provider_subject) DO UPDATE SET
                          user_id = EXCLUDED.user_id,
                          union_id = EXCLUDED.union_id,
                          open_id = EXCLUDED.open_id,
                          corp_id = EXCLUDED.corp_id,
                          corp_name = EXCLUDED.corp_name,
                          display_name = EXCLUDED.display_name,
                          email = EXCLUDED.email,
                          avatar_url = EXCLUDED.avatar_url,
                          status = 'active',
                          updated_at = now()
                        WHERE user_external_identities.user_id = EXCLUDED.user_id
                           OR user_external_identities.status <> 'active'
                        RETURNING id, user_id, provider, provider_subject, union_id, open_id,
                                  corp_id, corp_name, display_name, email, avatar_url, status
                        """,
                        (
                            identity_id,
                            user_id,
                            provider,
                            provider_subject,
                            profile.get("union_id"),
                            profile.get("open_id"),
                            profile.get("corp_id"),
                            profile.get("corp_name"),
                            profile.get("display_name"),
                            profile.get("email"),
                            profile.get("avatar_url"),
                        ),
                    )
                except Exception as exc:
                    if getattr(exc, "sqlstate", "") == "23505":
                        raise ValueError("user_identity_exists") from exc
                    raise
                row = cursor.fetchone()
        identity = self._identity_from_row(row)
        if identity is None:
            raise ValueError("identity_conflict")
        return identity

    def unbind(self, *, provider: str, user_id: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE user_external_identities
                    SET status = 'unbound', updated_at = now()
                    WHERE provider = %s AND user_id = %s AND status = 'active'
                    """,
                    (provider, user_id),
                )
                return cursor.rowcount > 0

    def find_by_id(self, identity_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, user_id, provider, provider_subject, union_id, open_id,
                           corp_id, corp_name, display_name, email, avatar_url, status
                    FROM user_external_identities
                    WHERE id = %s
                    """,
                    (identity_id,),
                )
                row = cursor.fetchone()
        return self._identity_from_row(row)

    def list_identities(
        self,
        *,
        provider: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        filters: list[str] = []
        values: list[Any] = []
        if provider:
            filters.append("provider = %s")
            values.append(provider)
        if status:
            filters.append("status = %s")
            values.append(status)
        if user_id:
            filters.append("user_id = %s")
            values.append(user_id)
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, user_id, provider, provider_subject, union_id, open_id,
                           corp_id, corp_name, display_name, email, avatar_url, status
                    FROM user_external_identities
                    {where_sql}
                    ORDER BY updated_at DESC, id ASC
                    """,
                    values,
                )
                rows = cursor.fetchall()
        return [
            identity
            for identity in (self._identity_from_row(row) for row in rows)
            if identity is not None
        ]

    def unbind_by_id(self, identity_id: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE user_external_identities
                    SET status = 'unbound', updated_at = now()
                    WHERE id = %s AND status = 'active'
                    """,
                    (identity_id,),
                )
                return cursor.rowcount > 0

    def _identity_from_row(self, row: Any | None) -> dict[str, Any] | None:
        if row is None:
            return None
        (
            identity_id,
            user_id,
            provider,
            provider_subject,
            union_id,
            open_id,
            corp_id,
            corp_name,
            display_name,
            email,
            avatar_url,
            status,
        ) = row
        return {
            "avatar_url": avatar_url,
            "corp_id": corp_id,
            "corp_name": corp_name,
            "display_name": display_name,
            "email": email,
            "id": identity_id,
            "open_id": open_id,
            "provider": provider,
            "provider_subject": provider_subject,
            "status": status,
            "union_id": union_id,
            "user_id": user_id,
        }
