from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from queue import Empty, LifoQueue
from threading import Lock
from typing import Generic, TypeVar

ConnectionT = TypeVar("ConnectionT")


class DatabaseConnectionPool(Generic[ConnectionT]):
    def __init__(self, *, factory: Callable[[], ConnectionT], max_size: int = 5) -> None:
        if max_size < 1:
            raise ValueError("max_size must be greater than 0")
        self._available: LifoQueue[ConnectionT] = LifoQueue(maxsize=max_size)
        self._created = 0
        self._factory = factory
        self._lock = Lock()
        self._max_size = max_size
        self._closed = False

    def _acquire(self) -> ConnectionT:
        if self._closed:
            raise RuntimeError("connection pool is closed")
        try:
            connection = self._available.get_nowait()
            if not getattr(connection, "closed", False):
                return connection
            self._discard(connection)
        except Empty:
            pass
        connection = self._create_if_capacity()
        if connection is not None:
            return connection
        while True:
            connection = self._available.get()
            if not getattr(connection, "closed", False):
                return connection
            self._discard(connection)
            connection = self._create_if_capacity()
            if connection is not None:
                return connection

    def _create_if_capacity(self) -> ConnectionT | None:
        with self._lock:
            if self._created >= self._max_size:
                return None
            connection = self._factory()
            self._created += 1
            return connection

    def _release(self, connection: ConnectionT) -> None:
        if self._closed or getattr(connection, "closed", False):
            self._discard(connection)
            return
        try:
            self._available.put_nowait(connection)
        except Exception:
            self._discard(connection)

    def _close_connection(self, connection: ConnectionT) -> None:
        close = getattr(connection, "close", None)
        if callable(close):
            close()

    def _discard(self, connection: ConnectionT) -> None:
        self._close_connection(connection)
        with self._lock:
            self._created = max(0, self._created - 1)

    @contextmanager
    def connection(self, *, autocommit: bool = True) -> Iterator[ConnectionT]:
        connection = self._acquire()
        original_autocommit = getattr(connection, "autocommit", None)
        if original_autocommit is not None:
            connection.autocommit = autocommit
        try:
            yield connection
            if not autocommit:
                commit = getattr(connection, "commit", None)
                if callable(commit):
                    commit()
        except Exception:
            if not autocommit:
                rollback = getattr(connection, "rollback", None)
                if callable(rollback):
                    rollback()
            raise
        finally:
            if original_autocommit is not None:
                connection.autocommit = original_autocommit
            self._release(connection)

    def close(self) -> None:
        self._closed = True
        while True:
            try:
                connection = self._available.get_nowait()
            except Empty:
                break
            self._close_connection(connection)
