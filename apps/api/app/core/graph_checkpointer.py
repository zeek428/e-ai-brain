"""Durable LangGraph checkpointer selection.

Business transitions are deliberately *not* stored in the LangGraph checkpoint.
The collaboration repository remains the source of truth for domain state; this
adapter only persists an execution cursor after a domain command has committed.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver


def _is_test_settings(settings: Any) -> bool:
    value = getattr(settings, "is_test_env", False)
    return bool(value() if callable(value) else value)


def build_checkpointer(settings: Any) -> Any:
    """Return a fresh test saver or a PostgreSQL-backed production saver.

    ``PostgresSaver.setup`` owns the official LangGraph checkpoint schema and
    is idempotent.  It is intentionally separate from collaboration-domain
    transactions so a cursor write failure cannot roll back a committed domain
    event (or cause it to be repeated on retry).
    """
    if _is_test_settings(settings):
        return InMemorySaver()
    if str(getattr(settings, "persistence_mode", "")).lower() != "postgres":
        raise RuntimeError("A PostgreSQL LangGraph checkpointer is required outside tests")

    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg import connect
    from psycopg.rows import dict_row

    database_url = str(getattr(settings, "database_url", "")).strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for the LangGraph checkpointer")
    connection = connect(
        database_url,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
    )
    checkpointer = PostgresSaver(connection)
    checkpointer.setup()
    return checkpointer
