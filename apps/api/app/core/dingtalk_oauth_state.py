from __future__ import annotations

import secrets
from copy import deepcopy
from time import sleep
from time import time as now_timestamp
from typing import Any

from app.core.db import DatabaseConnectionPool


class MemoryDingTalkOAuthStateRepository:
    def __init__(self) -> None:
        self.states: dict[str, dict[str, Any]] = {}
        self.tickets: dict[str, dict[str, Any]] = {}

    def create_state(
        self,
        *,
        expires_in_seconds: int,
        purpose: str,
        redirect: str,
        user_id: str | None = None,
    ) -> str:
        self._cleanup_expired()
        state = secrets.token_urlsafe(32)
        self.states[state] = {
            "expires_at": now_timestamp() + expires_in_seconds,
            "purpose": purpose,
            "redirect": redirect,
            "user_id": user_id,
        }
        return state

    def consume_state(self, *, purpose: str, state: str | None) -> dict[str, Any] | None:
        if not state:
            return None
        payload = self.states.pop(state, None)
        if payload is None or payload.get("purpose") != purpose:
            return None
        if float(payload.get("expires_at", 0)) <= now_timestamp():
            return None
        return deepcopy(payload)

    def create_ticket(
        self,
        *,
        expires_in_seconds: int,
        redirect: str,
        user_id: str,
    ) -> str:
        self._cleanup_expired()
        ticket = secrets.token_urlsafe(32)
        self.tickets[ticket] = {
            "expires_at": now_timestamp() + expires_in_seconds,
            "redirect": redirect,
            "user_id": user_id,
        }
        return ticket

    def consume_ticket(self, ticket: str) -> dict[str, Any] | None:
        if not ticket:
            return None
        payload = self.tickets.pop(ticket, None)
        if payload is None:
            return None
        if float(payload.get("expires_at", 0)) <= now_timestamp():
            return None
        return deepcopy(payload)

    def _cleanup_expired(self) -> None:
        current_time = now_timestamp()
        self.states = {
            state: payload
            for state, payload in self.states.items()
            if float(payload.get("expires_at", 0)) > current_time
        }
        self.tickets = {
            ticket: payload
            for ticket, payload in self.tickets.items()
            if float(payload.get("expires_at", 0)) > current_time
        }


class PostgresDingTalkOAuthStateRepository:
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

    def create_state(
        self,
        *,
        expires_in_seconds: int,
        purpose: str,
        redirect: str,
        user_id: str | None = None,
    ) -> str:
        state = secrets.token_urlsafe(32)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_expired(cursor)
                cursor.execute(
                    """
                    INSERT INTO dingtalk_oauth_ephemeral_states (
                      id, state_type, purpose, redirect_path, user_id, expires_at
                    )
                    VALUES (
                      %s, 'oauth_state', %s, %s, %s, now() + (%s * interval '1 second')
                    )
                    """,
                    (state, purpose, redirect, user_id, expires_in_seconds),
                )
        return state

    def consume_state(self, *, purpose: str, state: str | None) -> dict[str, Any] | None:
        if not state:
            return None
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM dingtalk_oauth_ephemeral_states
                    WHERE id = %s
                      AND state_type = 'oauth_state'
                      AND purpose = %s
                      AND expires_at > now()
                    RETURNING purpose, redirect_path, user_id
                    """,
                    (state, purpose),
                )
                row = cursor.fetchone()
        return _payload_from_row(row)

    def create_ticket(
        self,
        *,
        expires_in_seconds: int,
        redirect: str,
        user_id: str,
    ) -> str:
        ticket = secrets.token_urlsafe(32)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_expired(cursor)
                cursor.execute(
                    """
                    INSERT INTO dingtalk_oauth_ephemeral_states (
                      id, state_type, purpose, redirect_path, user_id, expires_at
                    )
                    VALUES (
                      %s, 'login_ticket', 'login', %s, %s, now() + (%s * interval '1 second')
                    )
                    """,
                    (ticket, redirect, user_id, expires_in_seconds),
                )
        return ticket

    def consume_ticket(self, ticket: str) -> dict[str, Any] | None:
        if not ticket:
            return None
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM dingtalk_oauth_ephemeral_states
                    WHERE id = %s
                      AND state_type = 'login_ticket'
                      AND expires_at > now()
                    RETURNING purpose, redirect_path, user_id
                    """,
                    (ticket,),
                )
                row = cursor.fetchone()
        return _payload_from_row(row)

    def _delete_expired(self, cursor: Any) -> None:
        cursor.execute(
            """
            DELETE FROM dingtalk_oauth_ephemeral_states
            WHERE expires_at <= now()
            """
        )


def _payload_from_row(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    purpose, redirect, user_id = row
    return {
        "purpose": purpose,
        "redirect": redirect,
        "user_id": user_id,
    }
