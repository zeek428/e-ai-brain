from app.core.db import DatabaseConnectionPool


class FakeConnection:
    def __init__(self) -> None:
        self.autocommit = True
        self.closed = False
        self.commits = 0
        self.rollbacks = 0

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_database_connection_pool_reuses_released_connection():
    created: list[FakeConnection] = []

    def factory() -> FakeConnection:
        connection = FakeConnection()
        created.append(connection)
        return connection

    pool = DatabaseConnectionPool(factory=factory, max_size=1)

    with pool.connection(autocommit=True) as first:
        assert first.autocommit is True
    with pool.connection(autocommit=True) as second:
        assert second.autocommit is True

    assert first is second
    assert created == [first]
    assert first.closed is False

    pool.close()
    assert first.closed is True


def test_database_connection_pool_replaces_closed_connection():
    created: list[FakeConnection] = []

    def factory() -> FakeConnection:
        connection = FakeConnection()
        created.append(connection)
        return connection

    pool = DatabaseConnectionPool(factory=factory, max_size=1)

    with pool.connection() as first:
        pass
    first.close()
    with pool.connection() as second:
        pass

    assert second is not first
    assert created == [first, second]
