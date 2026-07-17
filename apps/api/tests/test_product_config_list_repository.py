from contextlib import contextmanager
from datetime import UTC, date, datetime

from app.core.repositories.product_config_lists import ProductConfigListRepository


class _Cursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def execute(self, _query: str, _params: tuple[object, ...]) -> None:
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    @contextmanager
    def cursor(self):  # type: ignore[no-untyped-def]
        yield self._cursor


def test_product_version_list_serializes_postgres_like_string_timestamps():
    cursor = _Cursor(
        [
            (
                "version_001",
                "product_001",
                "2026.07",
                "R&D collaboration",
                "Requirement adapter delivery",
                "planning",
                "2026-07-01",
                date(2026, 7, 31),
                3,
                "AI-BRAIN",
                "AI Brain",
                "2026-07-01T08:00:00+00:00",
                datetime(2026, 7, 2, 9, 30, tzinfo=UTC),
            )
        ]
    )

    @contextmanager
    def connect():  # type: ignore[no-untyped-def]
        yield _Connection(cursor)

    item = ProductConfigListRepository(connect).list_product_version_summaries_page()[0]

    assert item == {
        "code": "2026.07",
        "created_at": "2026-07-01T08:00:00+00:00",
        "description": "Requirement adapter delivery",
        "id": "version_001",
        "name": "R&D collaboration",
        "product_code": "AI-BRAIN",
        "product_id": "product_001",
        "product_name": "AI Brain",
        "release_date": "2026-07-31",
        "scope_version": 3,
        "start_date": "2026-07-01",
        "status": "planning",
        "updated_at": "2026-07-02T09:30:00+00:00",
    }
