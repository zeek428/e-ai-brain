from __future__ import annotations

import hashlib
import hmac
import secrets
from copy import deepcopy
from time import sleep
from time import time as now_timestamp
from typing import Any

from app.core.db import DatabaseConnectionPool


def _normalize_answer(answer: str | int | None) -> str:
    return str(answer or "").strip()


def _answer_digest(*, answer: str | int | None, challenge_id: str, secret_key: str) -> str:
    payload = f"{challenge_id}:{_normalize_answer(answer)}".encode()
    return hmac.new(secret_key.encode(), payload, hashlib.sha256).hexdigest()


def _new_math_challenge() -> tuple[str, str]:
    left = secrets.randbelow(9) + 1
    right = secrets.randbelow(9) + 1
    return f"请计算：{left} + {right} = ?", str(left + right)


class MemoryLoginChallengeRepository:
    def __init__(self, *, secret_key: str) -> None:
        self.secret_key = secret_key
        self.challenges: dict[str, dict[str, Any]] = {}

    def create_challenge(self, *, expires_in_seconds: int) -> dict[str, Any]:
        self._cleanup_expired()
        challenge_id = secrets.token_urlsafe(32)
        question, answer = _new_math_challenge()
        self.challenges[challenge_id] = {
            "answer_hash": _answer_digest(
                answer=answer,
                challenge_id=challenge_id,
                secret_key=self.secret_key,
            ),
            "expires_at": now_timestamp() + expires_in_seconds,
            "question": question,
        }
        return {
            "challenge_id": challenge_id,
            "expires_in": expires_in_seconds,
            "question": question,
        }

    def consume_challenge(self, *, answer: str | None, challenge_id: str | None) -> bool:
        if not challenge_id:
            return False
        payload = self.challenges.pop(challenge_id, None)
        if payload is None or float(payload.get("expires_at", 0)) <= now_timestamp():
            return False
        expected_hash = str(payload.get("answer_hash") or "")
        actual_hash = _answer_digest(
            answer=answer,
            challenge_id=challenge_id,
            secret_key=self.secret_key,
        )
        return hmac.compare_digest(expected_hash, actual_hash)

    def _cleanup_expired(self) -> None:
        current_time = now_timestamp()
        self.challenges = {
            challenge_id: deepcopy(payload)
            for challenge_id, payload in self.challenges.items()
            if float(payload.get("expires_at", 0)) > current_time
        }


class PostgresLoginChallengeRepository:
    def __init__(self, database_url: str, *, pool_max_size: int = 5, secret_key: str) -> None:
        self.database_url = database_url
        self.secret_key = secret_key
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

    def create_challenge(self, *, expires_in_seconds: int) -> dict[str, Any]:
        challenge_id = secrets.token_urlsafe(32)
        question, answer = _new_math_challenge()
        answer_hash = _answer_digest(
            answer=answer,
            challenge_id=challenge_id,
            secret_key=self.secret_key,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_expired(cursor)
                cursor.execute(
                    """
                    INSERT INTO auth_login_challenges (
                      id, question, answer_hash, expires_at
                    )
                    VALUES (%s, %s, %s, now() + (%s * interval '1 second'))
                    """,
                    (challenge_id, question, answer_hash, expires_in_seconds),
                )
        return {
            "challenge_id": challenge_id,
            "expires_in": expires_in_seconds,
            "question": question,
        }

    def consume_challenge(self, *, answer: str | None, challenge_id: str | None) -> bool:
        if not challenge_id:
            return False
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM auth_login_challenges
                    WHERE id = %s
                      AND expires_at > now()
                    RETURNING answer_hash
                    """,
                    (challenge_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return False
        expected_hash = str(row[0] or "")
        actual_hash = _answer_digest(
            answer=answer,
            challenge_id=challenge_id,
            secret_key=self.secret_key,
        )
        return hmac.compare_digest(expected_hash, actual_hash)

    def _delete_expired(self, cursor: Any) -> None:
        cursor.execute(
            """
            DELETE FROM auth_login_challenges
            WHERE expires_at <= now()
            """
        )
