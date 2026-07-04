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
            raise ValueError("user_identity_exists")
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
                           corp_id, display_name, email, avatar_url, status
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
                           corp_id, display_name, email, avatar_url, status
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
            raise ValueError("user_identity_exists")
        identity_id = f"external_identity_{uuid4().hex}"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_external_identities (
                      id, user_id, provider, provider_subject, union_id, open_id,
                      corp_id, display_name, email, avatar_url, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
                    ON CONFLICT (provider, provider_subject) DO UPDATE SET
                      user_id = EXCLUDED.user_id,
                      union_id = EXCLUDED.union_id,
                      open_id = EXCLUDED.open_id,
                      corp_id = EXCLUDED.corp_id,
                      display_name = EXCLUDED.display_name,
                      email = EXCLUDED.email,
                      avatar_url = EXCLUDED.avatar_url,
                      status = 'active',
                      updated_at = now()
                    RETURNING id, user_id, provider, provider_subject, union_id, open_id,
                              corp_id, display_name, email, avatar_url, status
                    """,
                    (
                        identity_id,
                        user_id,
                        provider,
                        provider_subject,
                        profile.get("union_id"),
                        profile.get("open_id"),
                        profile.get("corp_id"),
                        profile.get("display_name"),
                        profile.get("email"),
                        profile.get("avatar_url"),
                    ),
                )
                row = cursor.fetchone()
        identity = self._identity_from_row(row)
        if identity is None:
            raise RuntimeError("external identity upsert returned no row")
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
            display_name,
            email,
            avatar_url,
            status,
        ) = row
        return {
            "avatar_url": avatar_url,
            "corp_id": corp_id,
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
