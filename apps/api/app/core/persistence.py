from __future__ import annotations

from copy import deepcopy
from time import sleep
from typing import Any, Protocol

from app.core.store import MemoryStore

STATE_KEY = "memory_store"
COLLECTION_FIELDS = [
    "products",
    "product_versions",
    "product_modules",
    "product_git_repositories",
    "related_systems",
    "model_gateway_configs",
    "model_gateway_logs",
    "gitlab_mr_snapshots",
    "code_review_reports",
    "knowledge_documents",
    "knowledge_deposits",
    "mock_writebacks",
    "bugs",
    "requirements",
    "ai_tasks",
    "graph_runs",
    "graph_checkpoints",
    "human_reviews",
    "audit_events",
    "counters",
]


class SnapshotRepository(Protocol):
    def load(self) -> dict[str, Any] | None: ...

    def save(self, payload: dict[str, Any]) -> None: ...


class PersistentMemoryStore(MemoryStore):
    def __init__(self, repository: SnapshotRepository) -> None:
        super().__init__()
        self.repository = repository

    @classmethod
    def from_repository(cls, repository: SnapshotRepository) -> PersistentMemoryStore:
        store = cls(repository)
        payload = repository.load()
        if payload:
            store.load_payload(payload)
        return store

    def to_payload(self) -> dict[str, Any]:
        return {field: deepcopy(getattr(self, field)) for field in COLLECTION_FIELDS}

    def load_payload(self, payload: dict[str, Any]) -> None:
        self.reset()
        for field in COLLECTION_FIELDS:
            if field in payload:
                setattr(self, field, deepcopy(payload[field]))

    def persist(self) -> None:
        self.repository.save(self.to_payload())


class PostgresSnapshotRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        import psycopg

        last_error: Exception | None = None
        for _ in range(20):
            try:
                return psycopg.connect(self.database_url, autocommit=True)
            except psycopg.OperationalError as exc:
                last_error = exc
                sleep(0.5)
        raise last_error or RuntimeError("PostgreSQL connection failed")

    def load(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM app_state_snapshots WHERE key = %s",
                    (STATE_KEY,),
                )
                row = cursor.fetchone()
        return row[0] if row else None

    def save(self, payload: dict[str, Any]) -> None:
        import json

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
