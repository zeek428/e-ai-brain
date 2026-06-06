from __future__ import annotations

from app.core.persistence_contracts import SnapshotRepository
from app.core.store import MemoryStore


class PostgresRuntimeStore(MemoryStore):
    """Runtime dependency container for PostgreSQL mode.

    This intentionally does not hydrate business collections from PostgreSQL.
    Routes in postgres mode should read and write through repository/query
    helpers; the inherited MemoryStore collections exist only as temporary
    request-local scratch space while the DB-first migration is completed.
    """

    def __init__(self, repository: SnapshotRepository) -> None:
        super().__init__()
        self.repository = repository

    def new_id(self, prefix: str) -> str:
        next_id = getattr(self.repository, "next_id", None)
        if not callable(next_id):
            return super().new_id(prefix)
        allocated_id = next_id(prefix)
        suffix = allocated_id.removeprefix(f"{prefix}_")
        if suffix.isdigit():
            self.counters[prefix] = max(self.counters.get(prefix, 0), int(suffix))
        return allocated_id

    def persist(self) -> None:
        return None
