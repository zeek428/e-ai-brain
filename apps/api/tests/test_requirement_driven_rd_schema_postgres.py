from __future__ import annotations

import os
import time
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, Queue
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from app.core.persistence import PostgresSnapshotRepository

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations"
MIGRATION_109 = MIGRATIONS_DIR / "109_requirement_driven_rd_collaboration.sql"
MIGRATION_116 = MIGRATIONS_DIR / "116_rd_trusted_delivery_evidence.sql"
MIGRATION_117 = MIGRATIONS_DIR / "117_rd_external_callback_facts.sql"
MIGRATION_123 = MIGRATIONS_DIR / "123_rd_dispatch_retry_controls.sql"
MIGRATION_124 = MIGRATIONS_DIR / "124_rd_dispatch_fair_cursor.sql"
MIGRATION_125 = MIGRATIONS_DIR / "125_rd_dispatch_due_index.sql"
MIGRATION_126 = MIGRATIONS_DIR / "126_rd_dispatch_page_index.sql"
MIGRATION_127 = MIGRATIONS_DIR / "127_rd_active_run_dispatch_index.sql"
MIGRATION_128 = MIGRATIONS_DIR / "128_rd_dependency_successor_index.sql"
DEFAULT_POSTGRES_ADMIN_URL = "postgresql://ai_brain:ai_brain_password@127.0.0.1:5432/postgres"


@pytest.fixture(scope="session")
def postgres_admin_url() -> str:
    database_url = os.getenv(
        "AI_BRAIN_TEST_POSTGRES_ADMIN_URL",
        DEFAULT_POSTGRES_ADMIN_URL,
    )
    try:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute("SELECT 1")
    except psycopg.OperationalError as exc:
        pytest.skip(
            f"real PostgreSQL is required for collaboration schema integration tests: {exc}"
        )
    return database_url


def _database_url(admin_url: str, database_name: str) -> str:
    return str(psycopg.conninfo.make_conninfo(admin_url, dbname=database_name))


@contextmanager
def _temporary_database(admin_url: str) -> Iterator[str]:
    database_name = f"ai_brain_rd_collab_{uuid4().hex}"
    with psycopg.connect(admin_url, autocommit=True) as admin_connection:
        admin_connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )
    try:
        yield _database_url(admin_url, database_name)
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin_connection:
            admin_connection.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                (database_name,),
            )
            admin_connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
            )


def _apply_migration(connection: psycopg.Connection, migration_path: Path) -> None:
    connection.execute(migration_path.read_text(encoding="utf-8"))


def _apply_historical_migrations(
    database_url: str,
    *,
    through: int,
) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            migration_number = int(migration_path.name.split("_", 1)[0])
            if migration_number > through:
                break
            _apply_migration(connection, migration_path)


def _seed_collaboration_scope(
    connection: psycopg.Connection,
    *,
    prefix: str,
    run_status: str = "running",
    snapshot_context_version_id: str | None = None,
    snapshot_context_scope_version: int = 1,
    run_product_id: str | None = None,
) -> dict[str, str]:
    ids = {
        "product": f"{prefix}-product",
        "version": f"{prefix}-version",
        "policy": f"{prefix}-policy",
        "base_snapshot": f"{prefix}-snapshot-base",
        "requirement": f"{prefix}-requirement",
        "assessment": f"{prefix}-assessment",
        "version_snapshot": f"{prefix}-snapshot-version",
        "source": f"{prefix}-source",
        "run": f"{prefix}-run",
        "run_requirement": f"{prefix}-run-requirement",
    }
    context_version_id = snapshot_context_version_id or ids["version"]
    effective_run_product_id = run_product_id or ids["product"]
    connection.execute(
        "INSERT INTO products (id, code, name) VALUES (%s, %s, %s)",
        (ids["product"], f"{prefix}-code", f"{prefix} product"),
    )
    if effective_run_product_id != ids["product"]:
        connection.execute(
            "INSERT INTO products (id, code, name) VALUES (%s, %s, %s)",
            (
                effective_run_product_id,
                f"{prefix}-run-product-code",
                f"{prefix} run product",
            ),
        )
    connection.execute(
        """
        INSERT INTO product_versions (id, product_id, code, name, status, scope_version)
        VALUES (%s, %s, %s, %s, 'active', 1)
        """,
        (ids["version"], ids["product"], f"{prefix}-v1", f"{prefix} v1"),
    )
    if snapshot_context_version_id is not None and snapshot_context_version_id != ids["version"]:
        connection.execute(
            """
            INSERT INTO product_versions (id, product_id, code, name, status, scope_version)
            VALUES (%s, %s, %s, %s, 'active', 1)
            """,
            (
                snapshot_context_version_id,
                ids["product"],
                f"{prefix}-context-v1",
                f"{prefix} context v1",
            ),
        )
    connection.execute(
        """
        INSERT INTO rd_task_executor_policies (
          id, name, brain_app_id, product_id, task_type,
          executor_type, instruction_template, status
        )
        VALUES (%s, %s, 'rd_brain', %s, 'code_change', 'codex', 'seed', 'active')
        """,
        (ids["policy"], f"{prefix} policy", ids["product"]),
    )
    connection.execute(
        """
        INSERT INTO rd_task_executor_policy_snapshots (
          id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
          resolution_context_key, resolution_revision, schema_version,
          content_hash, payload_json, created_by
        )
        VALUES (%s, %s, 1, NULL, 'base', %s, 0, 1, %s, '{}'::jsonb, 'user_admin')
        """,
        (
            ids["base_snapshot"],
            ids["policy"],
            f"policy:{ids['policy']}:version:1",
            f"{prefix}-base-hash",
        ),
    )
    connection.execute(
        """
        INSERT INTO requirements (
          id, brain_app_id, title, product_id, version_id, description,
          priority, source, status, created_by
        )
        VALUES (%s, 'rd_brain', %s, %s, %s, 'seed', 'P1',
                'business_department', 'approved', 'user_admin')
        """,
        (
            ids["requirement"],
            f"{prefix} requirement",
            ids["product"],
            ids["version"],
        ),
    )
    has_assessment_product_id = connection.execute(
        """
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.columns
          WHERE table_schema = 'public'
            AND table_name = 'requirement_assessments'
            AND column_name = 'product_id'
        )
        """
    ).fetchone()[0]
    if has_assessment_product_id:
        connection.execute(
            """
            INSERT INTO requirement_assessments (
              id, requirement_id, product_id, requirement_revision,
              initial_strategy_snapshot_id, final_strategy_snapshot_id,
              strategy_snapshot_id, status, created_by
            )
            VALUES (%s, %s, %s, 1, %s, %s, %s, 'accepted', 'user_admin')
            """,
            (
                ids["assessment"],
                ids["requirement"],
                ids["product"],
                ids["base_snapshot"],
                ids["base_snapshot"],
                ids["base_snapshot"],
            ),
        )
    else:
        connection.execute(
            """
            INSERT INTO requirement_assessments (
              id, requirement_id, requirement_revision,
              initial_strategy_snapshot_id, final_strategy_snapshot_id,
              strategy_snapshot_id, status, created_by
            )
            VALUES (%s, %s, 1, %s, %s, %s, 'accepted', 'user_admin')
            """,
            (
                ids["assessment"],
                ids["requirement"],
                ids["base_snapshot"],
                ids["base_snapshot"],
                ids["base_snapshot"],
            ),
        )
    connection.execute(
        """
        INSERT INTO rd_task_executor_policy_snapshots (
          id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
          resolution_context_key, resolution_revision, schema_version,
          content_hash, payload_json, created_by
        )
        VALUES (%s, %s, 1, %s, 'version_resolved', %s, 1, 1,
                %s, '{}'::jsonb, 'user_admin')
        """,
        (
            ids["version_snapshot"],
            ids["policy"],
            ids["base_snapshot"],
            f"version:{context_version_id}:scope:{snapshot_context_scope_version}",
            f"{prefix}-version-hash",
        ),
    )
    connection.execute(
        """
        INSERT INTO rd_task_executor_policy_snapshot_sources (
          id, snapshot_id, source_snapshot_id, requirement_id, assessment_id
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            ids["source"],
            ids["version_snapshot"],
            ids["base_snapshot"],
            ids["requirement"],
            ids["assessment"],
        ),
    )
    connection.execute(
        """
        INSERT INTO rd_collaboration_runs (
          id, brain_app_id, product_id, product_version_id, strategy_snapshot_id,
          run_generation, scope_version, status, graph_version, created_by
        )
        VALUES (%s, 'rd_brain', %s, %s, %s, 1, 1, %s, 'v1', 'user_admin')
        """,
        (
            ids["run"],
            effective_run_product_id,
            ids["version"],
            ids["version_snapshot"],
            run_status,
        ),
    )
    connection.execute(
        """
        INSERT INTO rd_collaboration_run_requirements (
          id, collaboration_run_id, requirement_id, requirement_revision,
          assessment_id, final_strategy_snapshot_id,
          acceptance_criteria_hash, repository_scope_hash
        )
        VALUES (%s, %s, %s, 1, %s, %s, %s, %s)
        """,
        (
            ids["run_requirement"],
            ids["run"],
            ids["requirement"],
            ids["assessment"],
            ids["base_snapshot"],
            f"{prefix}-acceptance-hash",
            f"{prefix}-repository-hash",
        ),
    )
    return ids


def _seed_assessment_inputs(
    connection: psycopg.Connection,
    *,
    prefix: str,
) -> dict[str, str]:
    ids = {
        "product": f"{prefix}-product",
        "version": f"{prefix}-version",
        "policy": f"{prefix}-policy",
        "alternate_policy": f"{prefix}-policy-alternate",
        "base_snapshot": f"{prefix}-snapshot-base",
        "alternate_base_snapshot": f"{prefix}-snapshot-base-alternate",
        "requirement": f"{prefix}-requirement",
        "alternate_requirement": f"{prefix}-requirement-alternate",
        "assessment": f"{prefix}-assessment",
    }
    connection.execute(
        "INSERT INTO products (id, code, name) VALUES (%s, %s, %s)",
        (ids["product"], f"{prefix}-code", f"{prefix} product"),
    )
    connection.execute(
        """
        INSERT INTO product_versions (id, product_id, code, name, status, scope_version)
        VALUES (%s, %s, %s, %s, 'active', 1)
        """,
        (ids["version"], ids["product"], f"{prefix}-v1", f"{prefix} v1"),
    )
    connection.execute(
        """
        INSERT INTO rd_task_executor_policies (
          id, name, brain_app_id, product_id, task_type,
          executor_type, instruction_template, status
        )
        VALUES (%s, %s, 'rd_brain', %s, 'code_change', 'codex', 'seed', 'active')
        """,
        (ids["policy"], f"{prefix} policy", ids["product"]),
    )
    connection.execute(
        """
        INSERT INTO rd_task_executor_policies (
          id, name, brain_app_id, product_id, task_type,
          executor_type, instruction_template, status
        )
        VALUES (%s, %s, 'rd_brain', %s, 'automated_testing',
                'codex', 'seed alternate', 'active')
        """,
        (ids["alternate_policy"], f"{prefix} alternate policy", ids["product"]),
    )
    for suffix, policy_id, snapshot_id in (
        ("base", ids["policy"], ids["base_snapshot"]),
        ("alternate", ids["alternate_policy"], ids["alternate_base_snapshot"]),
    ):
        connection.execute(
            """
            INSERT INTO rd_task_executor_policy_snapshots (
              id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
              resolution_context_key, resolution_revision, schema_version,
              content_hash, payload_json, created_by
            )
            VALUES (%s, %s, 1, NULL, 'base', %s, 0, 1, %s, %s::jsonb, 'user_admin')
            """,
            (
                snapshot_id,
                policy_id,
                f"policy:{policy_id}:version:1",
                f"{prefix}-{suffix}-hash",
                f'{{"variant":"{suffix}"}}',
            ),
        )
    for suffix, requirement_id in (
        ("main", ids["requirement"]),
        ("alternate", ids["alternate_requirement"]),
    ):
        connection.execute(
            """
            INSERT INTO requirements (
              id, brain_app_id, title, product_id, version_id, description,
              priority, source, status, created_by
            )
            VALUES (%s, 'rd_brain', %s, %s, %s, 'seed', 'P1',
                    'business_department', 'approved', 'user_admin')
            """,
            (
                requirement_id,
                f"{prefix} {suffix} requirement",
                ids["product"],
                ids["version"],
            ),
        )
    return ids


def _seed_feedback_context(
    connection: psycopg.Connection,
    *,
    prefix: str,
) -> dict[str, str]:
    ids = _seed_collaboration_scope(connection, prefix=prefix)
    ids.update(
        {
            "ai_employee": f"{prefix}-ai-employee",
            "alternate_ai_employee": f"{prefix}-ai-employee-alternate",
            "executor_profile": f"{prefix}-executor-profile",
            "human_seat": f"{prefix}-human-seat",
            "ai_seat": f"{prefix}-ai-seat",
            "event": f"{prefix}-event",
        }
    )
    connection.execute(
        """
        INSERT INTO rd_ai_employees (id, brain_app_id, code, name)
        VALUES (%s, 'rd_brain', %s, %s), (%s, 'rd_brain', %s, %s)
        """,
        (
            ids["ai_employee"],
            f"{prefix}-ai",
            f"{prefix} AI",
            ids["alternate_ai_employee"],
            f"{prefix}-ai-alternate",
            f"{prefix} alternate AI",
        ),
    )
    connection.execute(
        """
        INSERT INTO rd_executor_profiles (
          id, brain_app_id, code, name, executor_type
        )
        VALUES (%s, 'rd_brain', %s, %s, 'codex')
        """,
        (
            ids["executor_profile"],
            f"{prefix}-executor",
            f"{prefix} executor",
        ),
    )
    connection.execute(
        """
        INSERT INTO rd_run_seats (
          id, collaboration_run_id, role_code, subject_type, human_user_id
        )
        VALUES (%s, %s, 'reviewer', 'human_user', 'user_admin')
        """,
        (ids["human_seat"], ids["run"]),
    )
    connection.execute(
        """
        INSERT INTO rd_run_seats (
          id, collaboration_run_id, role_code, subject_type,
          ai_employee_id, executor_profile_id
        )
        VALUES (%s, %s, 'engineer', 'ai_employee', %s, %s)
        """,
        (
            ids["ai_seat"],
            ids["run"],
            ids["ai_employee"],
            ids["executor_profile"],
        ),
    )
    connection.execute(
        """
        INSERT INTO rd_collaboration_events (
          id, collaboration_run_id, event_type, event_key, subject_type, subject_id
        )
        VALUES (%s, %s, 'feedback.created', %s, 'collaboration_run', %s)
        """,
        (ids["event"], ids["run"], f"{prefix}-event-key", ids["run"]),
    )
    return ids


def _insert_feedback(
    connection: psycopg.Connection,
    *,
    ids: dict[str, str],
    feedback_id: str,
    producer_subject_type: str,
    producer_subject_id: str,
    producer_role_code: str | None = None,
    producer_seat_id: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO role_feedback_records (
          id, brain_app_id, product_id, collaboration_run_id,
          feedback_kind, source_event_id, feedback_fingerprint,
          role_code, seat_id, human_user_id, strategy_snapshot_id,
          producer_subject_type, producer_subject_id,
          producer_role_code, producer_seat_id
        )
        VALUES (
          %s, 'rd_brain', %s, %s, 'review', %s, %s,
          'reviewer', %s, 'user_admin', %s, %s, %s, %s, %s
        )
        """,
        (
            feedback_id,
            ids["product"],
            ids["run"],
            ids["event"],
            f"{feedback_id}-fingerprint",
            ids["human_seat"],
            ids["version_snapshot"],
            producer_subject_type,
            producer_subject_id,
            producer_role_code,
            producer_seat_id,
        ),
    )


def _execute_bounded_worker_statement(
    database_url: str,
    *,
    statement: str | sql.Composable,
    params: tuple[object, ...],
    backend_pids: Queue[int],
) -> str:
    try:
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            connection.execute("SET LOCAL lock_timeout = '5s'")
            connection.execute("SET LOCAL statement_timeout = '8s'")
            backend_pid = connection.execute("SELECT pg_backend_pid()").fetchone()
            assert backend_pid is not None
            backend_pids.put(backend_pid[0])
            connection.execute(statement, params)
    except psycopg.Error as exc:
        return str(exc)
    return "completed"


def _wait_for_postgres_lock(
    database_url: str,
    *,
    backend_pid: int,
    worker_future: Future[str],
    timeout_seconds: float = 3.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_activity: tuple[object, ...] | None = None
    with psycopg.connect(
        database_url,
        autocommit=True,
        connect_timeout=5,
    ) as observer:
        observer.execute("SET statement_timeout = '2s'")
        while time.monotonic() < deadline:
            last_activity = observer.execute(
                """
                SELECT wait_event_type, wait_event, state
                FROM pg_stat_activity
                WHERE pid = %s
                """,
                (backend_pid,),
            ).fetchone()
            if last_activity is not None and last_activity[0] == "Lock":
                return
            if worker_future.done():
                worker_result = worker_future.result()
                raise AssertionError(
                    "worker completed before entering a PostgreSQL lock wait: "
                    f"result={worker_result!r}, last_activity={last_activity!r}"
                )
            time.sleep(0.02)
    raise AssertionError(
        "worker did not enter a PostgreSQL lock wait before the bounded deadline: "
        f"backend_pid={backend_pid}, last_activity={last_activity!r}"
    )


def _execute_after_observed_lock_wait(
    database_url: str,
    *,
    lock_holding_connection: psycopg.Connection,
    statement: str | sql.Composable,
    params: tuple[object, ...],
) -> str:
    backend_pids: Queue[int] = Queue(maxsize=1)
    executor = ThreadPoolExecutor(max_workers=1)
    worker_future = executor.submit(
        _execute_bounded_worker_statement,
        database_url,
        statement=statement,
        params=params,
        backend_pids=backend_pids,
    )
    try:
        try:
            backend_pid = backend_pids.get(timeout=2)
        except Empty as exc:
            raise AssertionError("worker did not publish its PostgreSQL backend pid") from exc
        _wait_for_postgres_lock(
            database_url,
            backend_pid=backend_pid,
            worker_future=worker_future,
        )
        lock_holding_connection.commit()
        lock_holding_connection.close()
        return worker_future.result(timeout=10)
    finally:
        if not lock_holding_connection.closed:
            try:
                lock_holding_connection.rollback()
            except psycopg.Error:
                pass
            finally:
                lock_holding_connection.close()
        if not worker_future.done():
            try:
                worker_future.result(timeout=10)
            except Exception:
                pass
        executor.shutdown(wait=worker_future.done(), cancel_futures=True)


def test_fresh_historical_migration_chain_reaches_109_and_109_replays(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url, autocommit=True) as connection:
            _apply_migration(connection, MIGRATION_109)
            migration_objects = connection.execute(
                """
                SELECT
                  to_regclass('public.rd_collaboration_runs')::text,
                  to_regclass('public.rd_task_executor_policy_snapshots')::text
                """
            ).fetchone()

        assert migration_objects == (
            "rd_collaboration_runs",
            "rd_task_executor_policy_snapshots",
        )


def test_migration_116_allows_ready_for_release_for_version_and_run(
    postgres_admin_url: str,
) -> None:
    """The durable delivery transition must be legal in a freshly upgraded DB."""
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=115)
        # The run's version-resolved policy source trigger is deferred, so seed
        # its immutable source coverage and the target-state transition in one
        # real PostgreSQL transaction.
        with psycopg.connect(database_url) as connection:
            _apply_migration(connection, MIGRATION_116)
            ids = _seed_collaboration_scope(connection, prefix="ready-status", run_status="running")
            connection.execute(
                "UPDATE product_versions SET status = 'ready_for_release' WHERE id = %s",
                (ids["version"],),
            )
            connection.execute(
                "UPDATE rd_collaboration_runs SET status = 'ready_for_release' WHERE id = %s",
                (ids["run"],),
            )
            persisted = connection.execute(
                """
                SELECT version.status, run.status
                FROM product_versions version
                JOIN rd_collaboration_runs run ON run.product_version_id = version.id
                WHERE run.id = %s
                """,
                (ids["run"],),
            ).fetchone()

    assert persisted == ("ready_for_release", "ready_for_release")


def test_migration_117_keeps_verified_callback_facts_immutable(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=116)
        with psycopg.connect(database_url) as connection:
            _apply_migration(connection, MIGRATION_117)
            connection.execute(
                """
                INSERT INTO external_event_inbox (
                  id, provider, event_type, delivery_id, signature_status,
                  payload_hash, payload_json
                ) VALUES (
                  'callback-fact-1', 'gitlab', 'Push Hook', 'provider-event-1', 'verified',
                  'sha256:callback-fact', '{"_context":{"repository_ref":"rd/1"}}'::jsonb
                )
                """
            )
            connection.execute(
                "UPDATE external_event_inbox SET status = 'completed' WHERE id = 'callback-fact-1'"
            )
            with pytest.raises(psycopg.errors.RaiseException, match="callback fact is immutable"):
                connection.execute(
                    """
                    UPDATE external_event_inbox
                    SET payload_json = '{"_context":{"repository_ref":"main"}}'::jsonb
                    WHERE id = 'callback-fact-1'
                    """
                )
            connection.rollback()


def test_migration_123_adds_durable_dispatch_retry_controls(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=122)
        with psycopg.connect(database_url, autocommit=True) as connection:
            _apply_migration(connection, MIGRATION_123)
            columns = connection.execute(
                """
                SELECT column_name, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'rd_work_items'
                  AND column_name IN (
                    'dispatch_failure_count',
                    'last_dispatch_error_code',
                    'next_dispatch_at'
                  )
                ORDER BY column_name
                """
            ).fetchall()
            _apply_migration(connection, MIGRATION_125)
            indexes = connection.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'rd_work_items'
                  AND indexname = 'idx_rd_work_items_dispatch_due'
                """
            ).fetchall()
        with psycopg.connect(database_url) as connection:
            ids = _seed_collaboration_scope(connection, prefix="dispatch-retry-controls")
            with pytest.raises(psycopg.errors.CheckViolation):
                connection.execute(
                    """
                    INSERT INTO rd_work_items (
                      id, collaboration_run_id, plan_version, work_item_type,
                      title, objective, status, idempotency_key,
                      dispatch_failure_count
                    ) VALUES (
                      'dispatch-retry-controls-negative', %s, 1, 'implementation',
                      'negative retry count', 'must be rejected', 'ready',
                      'dispatch-retry-controls-negative', -1
                    )
                    """,
                    (ids["run"],),
                )

    assert columns == [
        ("dispatch_failure_count", "0", "NO"),
        ("last_dispatch_error_code", None, "YES"),
        ("next_dispatch_at", None, "YES"),
    ]
    assert len(indexes) == 1
    assert "next_dispatch_at" in indexes[0][1]
    assert "status" in indexes[0][1]
    entrypoint_source = (
        Path(__file__).resolve().parents[3] / "infra" / "docker" / "api-entrypoint.sh"
    ).read_text(encoding="utf-8")
    assert 'for path in sorted(migration_dir.glob("*.sql")):' in entrypoint_source
    assert "123_rd_dispatch_retry_controls.sql" not in entrypoint_source


def test_migration_123_repeat_does_not_replace_constraints_or_wait_for_table_lock(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=122)
        with psycopg.connect(database_url, autocommit=True) as connection:
            _apply_migration(connection, MIGRATION_123)
            before = connection.execute(
                """
                SELECT conname, oid, convalidated
                FROM pg_constraint
                WHERE conrelid = 'rd_work_items'::regclass
                  AND conname IN (
                    'ck_rd_work_items_dispatch_failure_count',
                    'ck_rd_work_items_dispatch_error_code'
                  )
                ORDER BY conname
                """
            ).fetchall()

        with psycopg.connect(database_url) as blocker:
            blocker.execute("LOCK TABLE rd_work_items IN ACCESS SHARE MODE")
            with psycopg.connect(database_url, autocommit=True) as retry:
                retry.execute("SET lock_timeout = '250ms'")
                _apply_migration(retry, MIGRATION_123)
                after = retry.execute(
                    """
                    SELECT conname, oid, convalidated
                    FROM pg_constraint
                    WHERE conrelid = 'rd_work_items'::regclass
                      AND conname IN (
                        'ck_rd_work_items_dispatch_failure_count',
                        'ck_rd_work_items_dispatch_error_code'
                      )
                    ORDER BY conname
                    """
                ).fetchall()

    assert before == after
    assert len(after) == 2
    assert all(row[2] for row in after)


def test_dispatch_scaling_indexes_are_transaction_compatible(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=124)
        with psycopg.connect(database_url) as connection:
            for migration in (MIGRATION_125, MIGRATION_126, MIGRATION_127, MIGRATION_128):
                _apply_migration(connection, migration)
            connection.commit()
            indexes = connection.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN (
                    'idx_rd_work_items_dispatch_due',
                    'idx_rd_work_items_dispatch_due_page',
                    'idx_rd_collaboration_runs_status_id',
                    'idx_rd_work_item_dependencies_successor'
                  )
                ORDER BY indexname
                """
            ).fetchall()

    assert [row[0] for row in indexes] == [
        "idx_rd_collaboration_runs_status_id",
        "idx_rd_work_item_dependencies_successor",
        "idx_rd_work_items_dispatch_due",
        "idx_rd_work_items_dispatch_due_page",
    ]
    definitions = {name: definition for name, definition in indexes}
    assert "(status, id)" in definitions["idx_rd_collaboration_runs_status_id"]
    assert (
        "(collaboration_run_id, successor_work_item_id, predecessor_work_item_id, id)"
        in definitions["idx_rd_work_item_dependencies_successor"]
    )


def test_runtime_dispatch_index_upgrade_is_valid_and_one_time(
    postgres_admin_url: str,
) -> None:
    migrations = (
        (MIGRATION_125.name, "idx_rd_work_items_dispatch_due"),
        (MIGRATION_126.name, "idx_rd_work_items_dispatch_due_page"),
        (MIGRATION_127.name, "idx_rd_collaboration_runs_status_id"),
        (MIGRATION_128.name, "idx_rd_work_item_dependencies_successor"),
    )
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=124)
        repository = PostgresSnapshotRepository(database_url)
        try:
            with repository._connect(autocommit=True) as connection:
                for filename, index_name in migrations:
                    repository._ensure_concurrent_index_migration(
                        connection,
                        filename,
                        index_name,
                    )
                before = connection.execute(
                    """
                    SELECT index_class.relname, index_class.oid,
                           index_state.indisvalid, index_state.indisready
                    FROM pg_class AS index_class
                    JOIN pg_namespace AS index_namespace
                      ON index_namespace.oid = index_class.relnamespace
                    JOIN pg_index AS index_state
                      ON index_state.indexrelid = index_class.oid
                    WHERE index_namespace.nspname = 'public'
                      AND index_class.relname = ANY(%s)
                    ORDER BY index_class.relname
                    """,
                    ([index_name for _, index_name in migrations],),
                ).fetchall()
                for filename, index_name in migrations:
                    repository._ensure_concurrent_index_migration(
                        connection,
                        filename,
                        index_name,
                    )
                after = connection.execute(
                    """
                    SELECT index_class.relname, index_class.oid,
                           index_state.indisvalid, index_state.indisready
                    FROM pg_class AS index_class
                    JOIN pg_namespace AS index_namespace
                      ON index_namespace.oid = index_class.relnamespace
                    JOIN pg_index AS index_state
                      ON index_state.indexrelid = index_class.oid
                    WHERE index_namespace.nspname = 'public'
                      AND index_class.relname = ANY(%s)
                    ORDER BY index_class.relname
                    """,
                    ([index_name for _, index_name in migrations],),
                ).fetchall()
        finally:
            repository._pool.close()

    assert before == after
    assert len(after) == 4
    assert all(row[2:] == (True, True) for row in after)


def test_migration_124_adds_durable_dispatch_cursor_and_page_index(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=123)
        with psycopg.connect(database_url, autocommit=True) as connection:
            _apply_migration(connection, MIGRATION_124)
            _apply_migration(connection, MIGRATION_126)
            tables = connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('rd_dispatch_sweep_cursors', 'rd_dispatch_run_cursors')
                ORDER BY table_name
                """
            ).fetchall()
            indexes = connection.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_rd_work_items_dispatch_due_page'
                """
            ).fetchall()

    assert tables == [("rd_dispatch_run_cursors",), ("rd_dispatch_sweep_cursors",)]
    assert len(indexes) == 1
    assert "COALESCE(next_dispatch_at" in indexes[0][1]
    assert "CASE" in indexes[0][1]
    entrypoint_source = (
        Path(__file__).resolve().parents[3] / "infra" / "docker" / "api-entrypoint.sh"
    ).read_text(encoding="utf-8")
    assert 'for path in sorted(migration_dir.glob("*.sql")):' in entrypoint_source
    assert "124_rd_dispatch_fair_cursor.sql" not in entrypoint_source


def test_migration_109_normalizes_rows_from_previous_operation_constraint(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as connection:
            ids = _seed_collaboration_scope(connection, prefix="legacy-operation-replay")
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()
            connection.autocommit = True
            connection.execute(
                """
                INSERT INTO product_git_repositories (
                  id, product_id, git_provider, name, remote_url, default_branch
                )
                VALUES (
                  'legacy-operation-repository', %s, 'gitlab', 'Legacy operation repo',
                  'https://git.example.com/legacy/operation.git', 'main'
                )
                """,
                (ids["product"],),
            )
            connection.execute(
                """
                INSERT INTO decision_requests (
                  id, brain_app_id, product_id, subject_type, subject_id,
                  decision_type, options_json, options_hash, status,
                  expires_at, created_by
                )
                VALUES (
                  'legacy-operation-decision', 'rd_brain', %s,
                  'rd_scope_change_request', 'legacy-operation-request',
                  'scope_change', '[]'::jsonb, 'legacy-options', 'pending',
                  now() + interval '1 hour', 'user_admin'
                )
                """,
                (ids["product"],),
            )
            connection.execute(
                """
                INSERT INTO rd_scope_change_requests (
                  id, product_version_id, request_id, source_run_id,
                  source_run_state, expected_scope_version,
                  expected_run_generation, operations_json, operations_hash,
                  reason, status, decision_request_id, requested_by
                )
                VALUES (
                  'legacy-operation-request', %s, 'legacy-operation-key', %s,
                  'running', 1, 1, '[]'::jsonb, 'legacy-operations',
                  'legacy operation rows', 'pending_decision',
                  'legacy-operation-decision', 'user_admin'
                )
                """,
                (ids["version"], ids["run"]),
            )
            connection.execute(
                "ALTER TABLE rd_scope_change_request_operations "
                "DROP CONSTRAINT ck_rd_scope_change_operation_fields"
            )
            connection.execute(
                """
                ALTER TABLE rd_scope_change_request_operations
                ADD CONSTRAINT ck_rd_scope_change_operation_fields CHECK (
                  (
                    op = 'remove_requirement'
                    AND requirement_id IS NOT NULL AND requirement_revision IS NULL
                    AND assessment_id IS NULL AND final_strategy_snapshot_id IS NULL
                    AND repository_id IS NULL AND branch_config_version IS NULL
                    AND base_commit_sha IS NULL AND destination IS NULL
                  ) OR (
                    op = 'update_repository_baseline'
                    AND requirement_id IS NULL AND requirement_revision IS NULL
                    AND assessment_id IS NULL AND final_strategy_snapshot_id IS NULL
                    AND repository_id IS NOT NULL AND branch_config_version IS NOT NULL
                    AND base_commit_sha IS NOT NULL AND destination IS NOT NULL
                  )
                )
                """
            )
            connection.execute(
                """
                INSERT INTO rd_scope_change_request_operations (
                  id, scope_change_request_id, position, op, requirement_id
                )
                VALUES (
                  'legacy-remove-operation', 'legacy-operation-request', 0,
                  'remove_requirement', %s
                )
                """,
                (ids["requirement"],),
            )
            connection.execute(
                """
                INSERT INTO rd_scope_change_request_operations (
                  id, scope_change_request_id, position, op, repository_id,
                  branch_config_version, base_commit_sha, destination
                )
                VALUES (
                  'legacy-baseline-operation', 'legacy-operation-request', 1,
                  'update_repository_baseline', 'legacy-operation-repository',
                  1, 'abc123', 'legacy-branch'
                )
                """
            )

            _apply_migration(connection, MIGRATION_109)

            normalized = connection.execute(
                """
                SELECT id, destination
                FROM rd_scope_change_request_operations
                WHERE scope_change_request_id = 'legacy-operation-request'
                ORDER BY position
                """
            ).fetchall()
            assert normalized == [
                ("legacy-remove-operation", "approved_pool"),
                ("legacy-baseline-operation", None),
            ]
            with pytest.raises(psycopg.errors.CheckViolation):
                connection.execute(
                    """
                    INSERT INTO rd_scope_change_request_operations (
                      id, scope_change_request_id, position, op, requirement_id,
                      destination
                    )
                    VALUES (
                      'invalid-null-remove-operation', 'legacy-operation-request', 2,
                      'remove_requirement', %s, NULL
                    )
                    """,
                    (ids["requirement"],),
                )


def test_lock_wait_helper_rejects_slow_non_locking_worker_and_cleans_up(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        lock_holding_connection = psycopg.connect(database_url)
        lock_holding_connection.execute("SELECT 1")

        with pytest.raises(AssertionError, match="PostgreSQL lock wait"):
            _execute_after_observed_lock_wait(
                database_url,
                lock_holding_connection=lock_holding_connection,
                statement="SELECT pg_sleep(0.5)",
                params=(),
            )

        assert lock_holding_connection.closed
        with psycopg.connect(database_url) as verification_connection:
            other_session_count = verification_connection.execute(
                """
                SELECT count(*)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND pid <> pg_backend_pid()
                """
            ).fetchone()

        assert other_session_count == (0,)


def test_migration_109_preserves_legacy_multiple_active_task_type_policies(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=108)

        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(
                """
                INSERT INTO products (id, code, name)
                VALUES ('product-legacy', 'LEGACY', 'Legacy')
                """
            )
            connection.execute(
                """
                INSERT INTO rd_task_executor_policies (
                  id, name, brain_app_id, product_id, task_type,
                  executor_type, instruction_template, status
                )
                VALUES
                  ('policy-product-code', 'Product code', 'rd_brain', 'product-legacy',
                   'code_change', 'codex', 'code', 'active'),
                  ('policy-product-test', 'Product test', 'rd_brain', 'product-legacy',
                   'automated_testing', 'codex', 'test', 'active'),
                  ('policy-default-code', 'Default code', 'rd_brain', NULL,
                   'code_change', 'codex', 'code', 'active'),
                  ('policy-default-test', 'Default test', 'rd_brain', NULL,
                   'automated_testing', 'codex', 'test', 'active')
                """
            )

            _apply_migration(connection, MIGRATION_109)

            connection.execute(
                """
                INSERT INTO rd_task_executor_policies (
                  id, name, brain_app_id, product_id, task_type,
                  executor_type, instruction_template, status
                )
                VALUES (
                  'policy-product-review', 'Product review', 'rd_brain', 'product-legacy',
                  'code_review', 'codex', 'review', 'active'
                )
                """
            )
            active_policy_count = connection.execute(
                """
                SELECT count(*)
                FROM rd_task_executor_policies
                WHERE brain_app_id = 'rd_brain' AND status = 'active'
                """
            ).fetchone()

        assert active_policy_count == (5,)


def test_snapshot_freezes_policy_version_without_blocking_policy_increment(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(
                """
                INSERT INTO rd_task_executor_policies (
                  id, name, brain_app_id, product_id, task_type,
                  executor_type, instruction_template, status
                )
                VALUES (
                  'policy-versioned', 'Versioned', 'rd_brain', NULL, 'code_change',
                  'codex', 'versioned', 'active'
                )
                """
            )

            with pytest.raises(psycopg.Error):
                connection.execute(
                    """
                    INSERT INTO rd_task_executor_policy_snapshots (
                      id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
                      resolution_context_key, resolution_revision, schema_version,
                      content_hash, payload_json, created_by
                    )
                    VALUES (
                      'snapshot-invalid-v2', 'policy-versioned', 2, NULL, 'base',
                      'policy:policy-versioned:version:2', 0, 1,
                      'hash-invalid-v2', '{}'::jsonb, 'user_admin'
                    )
                    """
                )

            connection.execute(
                """
                INSERT INTO rd_task_executor_policy_snapshots (
                  id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
                  resolution_context_key, resolution_revision, schema_version,
                  content_hash, payload_json, created_by
                )
                VALUES (
                  'snapshot-v1', 'policy-versioned', 1, NULL, 'base',
                  'policy:policy-versioned:version:1', 0, 1,
                  'hash-v1', '{}'::jsonb, 'user_admin'
                )
                """
            )

            connection.execute(
                """
                UPDATE rd_task_executor_policies
                SET policy_version = 2
                WHERE id = 'policy-versioned'
                """
            )
            connection.execute(
                """
                INSERT INTO rd_task_executor_policy_snapshots (
                  id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
                  resolution_context_key, resolution_revision, schema_version,
                  content_hash, payload_json, created_by
                )
                VALUES (
                  'snapshot-v2', 'policy-versioned', 2, NULL, 'base',
                  'policy:policy-versioned:version:2', 0, 1,
                  'hash-v2', '{}'::jsonb, 'user_admin'
                )
                """
            )
            frozen_versions = connection.execute(
                """
                SELECT id, policy_version
                FROM rd_task_executor_policy_snapshots
                WHERE policy_id = 'policy-versioned'
                ORDER BY policy_version
                """
            ).fetchall()

        assert frozen_versions == [("snapshot-v1", 1), ("snapshot-v2", 2)]


@pytest.mark.parametrize("terminal_status", ["failed", "cancelled"])
def test_failed_and_cancelled_collaboration_runs_reject_every_update(
    postgres_admin_url: str,
    terminal_status: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            ids = _seed_collaboration_scope(
                connection,
                prefix=f"terminal-{terminal_status}",
                run_status=terminal_status,
            )
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

            with pytest.raises(psycopg.errors.RaiseException, match="terminal"):
                connection.execute(
                    """
                    UPDATE rd_collaboration_runs
                    SET completion_reason = 'must remain frozen'
                    WHERE id = %s
                    """,
                    (ids["run"],),
                )


@pytest.mark.parametrize(
    ("case", "context_suffix", "resolution_revision"),
    [
        ("wrong_context", "other-assessment", 1),
        ("wrong_root", "expected", 1),
        ("skipped_revision", "expected", 2),
    ],
)
def test_assessment_snapshot_is_bound_to_assessment_context_root_and_revision_chain(
    postgres_admin_url: str,
    case: str,
    context_suffix: str,
    resolution_revision: int,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            ids = _seed_assessment_inputs(connection, prefix=f"assessment-{case}")
            derived_snapshot_id = f"assessment-{case}-derived"
            derived_policy_id = ids["alternate_policy"] if case == "wrong_root" else ids["policy"]
            parent_snapshot_id = (
                ids["alternate_base_snapshot"] if case == "wrong_root" else ids["base_snapshot"]
            )
            context_assessment_id = (
                ids["assessment"] if context_suffix == "expected" else context_suffix
            )
            connection.execute(
                """
                INSERT INTO rd_task_executor_policy_snapshots (
                  id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
                  resolution_context_key, resolution_revision, schema_version,
                  content_hash, payload_json, created_by
                )
                VALUES (%s, %s, 1, %s, 'assessment_resolved', %s, %s, 1,
                        %s, '{}'::jsonb, 'user_admin')
                """,
                (
                    derived_snapshot_id,
                    derived_policy_id,
                    parent_snapshot_id,
                    f"assessment:{context_assessment_id}",
                    resolution_revision,
                    f"assessment-{case}-derived-hash",
                ),
            )
            connection.execute(
                """
                INSERT INTO requirement_assessments (
                  id, requirement_id, requirement_revision,
                  initial_strategy_snapshot_id, final_strategy_snapshot_id,
                  strategy_snapshot_id, status, created_by
                )
                VALUES (%s, %s, 1, %s, %s, %s, 'accepted', 'user_admin')
                """,
                (
                    ids["assessment"],
                    ids["requirement"],
                    ids["base_snapshot"],
                    derived_snapshot_id,
                    derived_snapshot_id,
                ),
            )

            with pytest.raises(psycopg.errors.RaiseException, match="assessment snapshot"):
                connection.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.parametrize("case", ["wrong_version_context", "wrong_product_ownership"])
def test_collaboration_run_snapshot_matches_version_scope_and_current_ownership(
    postgres_admin_url: str,
    case: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            prefix = f"run-context-{case}"
            _seed_collaboration_scope(
                connection,
                prefix=prefix,
                snapshot_context_version_id=(
                    f"{prefix}-other-version" if case == "wrong_version_context" else None
                ),
                run_product_id=(
                    f"{prefix}-other-product" if case == "wrong_product_ownership" else None
                ),
            )

            with pytest.raises(psycopg.errors.RaiseException, match="collaboration run"):
                connection.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.parametrize("snapshot_scope_version", [1, 2])
def test_version_resolved_snapshot_requires_current_scope_and_source_coverage(
    postgres_admin_url: str,
    snapshot_scope_version: int,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            prefix = f"orphan-version-snapshot-{snapshot_scope_version}"
            ids = _seed_assessment_inputs(connection, prefix=prefix)
            connection.execute(
                """
                INSERT INTO rd_task_executor_policy_snapshots (
                  id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
                  resolution_context_key, resolution_revision, schema_version,
                  content_hash, payload_json, created_by
                )
                VALUES (
                  %s, %s, 1, %s, 'version_resolved',
                  %s, 1, 1, %s, '{}'::jsonb, 'user_admin'
                )
                """,
                (
                    f"{prefix}-target",
                    ids["policy"],
                    ids["base_snapshot"],
                    f"version:{ids['version']}:scope:{snapshot_scope_version}",
                    f"{prefix}-hash",
                ),
            )

            with pytest.raises(psycopg.errors.RaiseException, match="version_resolved snapshot"):
                connection.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.parametrize(
    "mutation",
    ["status", "requirement_id", "requirement_revision", "strategy_snapshots"],
)
def test_assessment_provenance_cannot_change_after_scope_sources_reference_it(
    postgres_admin_url: str,
    mutation: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            prefix = f"assessment-provenance-{mutation}"
            ids = _seed_collaboration_scope(connection, prefix=prefix)
            alternate_requirement_id = f"{prefix}-alternate-requirement"
            alternate_policy_id = f"{prefix}-alternate-policy"
            alternate_snapshot_id = f"{prefix}-alternate-snapshot"
            connection.execute(
                """
                INSERT INTO requirements (
                  id, brain_app_id, title, product_id, version_id, description,
                  priority, source, status, created_by
                )
                VALUES (%s, 'rd_brain', 'alternate', %s, %s, 'alternate', 'P1',
                        'business_department', 'approved', 'user_admin')
                """,
                (alternate_requirement_id, ids["product"], ids["version"]),
            )
            connection.execute(
                """
                INSERT INTO rd_task_executor_policies (
                  id, name, brain_app_id, product_id, task_type,
                  executor_type, instruction_template, status
                )
                VALUES (%s, 'alternate', 'rd_brain', %s, 'automated_testing',
                        'codex', 'alternate', 'active')
                """,
                (alternate_policy_id, ids["product"]),
            )
            connection.execute(
                """
                INSERT INTO rd_task_executor_policy_snapshots (
                  id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
                  resolution_context_key, resolution_revision, schema_version,
                  content_hash, payload_json, created_by
                )
                VALUES (%s, %s, 1, NULL, 'base', %s, 0, 1,
                        %s, '{}'::jsonb, 'user_admin')
                """,
                (
                    alternate_snapshot_id,
                    alternate_policy_id,
                    f"policy:{alternate_policy_id}:version:1",
                    f"{prefix}-alternate-hash",
                ),
            )
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

            statements: dict[str, tuple[str, tuple[object, ...]]] = {
                "status": ("status = %s", ("rejected",)),
                "requirement_id": (
                    "requirement_id = %s",
                    (alternate_requirement_id,),
                ),
                "requirement_revision": (
                    "requirement_revision = %s",
                    (2,),
                ),
                "strategy_snapshots": (
                    "final_strategy_snapshot_id = %s, strategy_snapshot_id = %s",
                    (alternate_snapshot_id, alternate_snapshot_id),
                ),
            }
            set_clause, params = statements[mutation]
            with pytest.raises(psycopg.errors.RaiseException, match="assessment provenance"):
                connection.execute(
                    sql.SQL("UPDATE requirement_assessments SET {} WHERE id = %s").format(
                        sql.SQL(set_clause)
                    ),
                    (*params, ids["assessment"]),
                )
                connection.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.parametrize(
    "producer_case",
    ["mismatched_human", "mismatched_ai", "service_with_seat"],
)
def test_feedback_producer_must_be_the_subject_owned_by_the_producer_seat(
    postgres_admin_url: str,
    producer_case: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            prefix = f"feedback-producer-{producer_case}"
            ids = _seed_feedback_context(connection, prefix=prefix)
            producer_values = {
                "mismatched_human": (
                    "human_user",
                    "user_reviewer",
                    "reviewer",
                    ids["human_seat"],
                ),
                "mismatched_ai": (
                    "ai_employee",
                    ids["alternate_ai_employee"],
                    "engineer",
                    ids["ai_seat"],
                ),
                "service_with_seat": (
                    "service",
                    "quality_gate",
                    "reviewer",
                    ids["human_seat"],
                ),
            }
            producer_type, producer_id, producer_role, producer_seat = producer_values[
                producer_case
            ]
            _insert_feedback(
                connection,
                ids=ids,
                feedback_id=f"{prefix}-feedback",
                producer_subject_type=producer_type,
                producer_subject_id=producer_id,
                producer_role_code=producer_role,
                producer_seat_id=producer_seat,
            )

            with pytest.raises(psycopg.errors.RaiseException, match="producer seat subject"):
                connection.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.parametrize(
    "mutation",
    ["collaboration_run_id", "role_code", "subject_type", "subject_id"],
)
def test_feedback_referenced_seat_run_role_and_subject_identity_is_immutable(
    postgres_admin_url: str,
    mutation: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            prefix = f"feedback-seat-freeze-{mutation}"
            ids = _seed_feedback_context(connection, prefix=prefix)
            other_ids = _seed_collaboration_scope(connection, prefix=f"{prefix}-other-run")
            _insert_feedback(
                connection,
                ids=ids,
                feedback_id=f"{prefix}-feedback",
                producer_subject_type="human_user",
                producer_subject_id="user_admin",
                producer_role_code="reviewer",
                producer_seat_id=ids["human_seat"],
            )
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

            statements: dict[str, tuple[str, tuple[object, ...]]] = {
                "collaboration_run_id": (
                    "collaboration_run_id = %s",
                    (other_ids["run"],),
                ),
                "role_code": ("role_code = %s", ("architect",)),
                "subject_type": (
                    "subject_type = 'ai_employee', human_user_id = NULL, "
                    "ai_employee_id = %s, executor_profile_id = %s",
                    (ids["ai_employee"], ids["executor_profile"]),
                ),
                "subject_id": ("human_user_id = %s", ("user_reviewer",)),
            }
            set_clause, params = statements[mutation]
            with pytest.raises(
                psycopg.errors.RaiseException,
                match="feedback-referenced seat identity",
            ):
                connection.execute(
                    sql.SQL("UPDATE rd_run_seats SET {} WHERE id = %s").format(sql.SQL(set_clause)),
                    (*params, ids["human_seat"]),
                )


@pytest.mark.parametrize("producer_type", ["human_user", "ai_employee"])
def test_feedback_polymorphic_producer_cannot_be_deleted(
    postgres_admin_url: str,
    producer_type: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            prefix = f"feedback-producer-delete-{producer_type}"
            ids = _seed_feedback_context(connection, prefix=prefix)
            if producer_type == "human_user":
                producer_id = f"{prefix}-user"
                connection.execute(
                    """
                    INSERT INTO users (id, email, display_name, password_hash)
                    VALUES (%s, %s, 'feedback producer', 'test-hash')
                    """,
                    (producer_id, f"{producer_id}@example.com"),
                )
            else:
                producer_id = ids["alternate_ai_employee"]
            _insert_feedback(
                connection,
                ids=ids,
                feedback_id=f"{prefix}-feedback",
                producer_subject_type=producer_type,
                producer_subject_id=producer_id,
            )
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

            producer_table = (
                sql.Identifier("users")
                if producer_type == "human_user"
                else sql.Identifier("rd_ai_employees")
            )
            with pytest.raises(psycopg.errors.RaiseException, match="feedback producer"):
                connection.execute(
                    sql.SQL("DELETE FROM {} WHERE id = %s").format(producer_table),
                    (producer_id,),
                )


def test_feedback_producer_seat_delete_remains_restricted(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)

        with psycopg.connect(database_url) as connection:
            ids = _seed_feedback_context(connection, prefix="feedback-seat-delete")
            _insert_feedback(
                connection,
                ids=ids,
                feedback_id="feedback-seat-delete-feedback",
                producer_subject_type="human_user",
                producer_subject_id="user_admin",
                producer_role_code="reviewer",
                producer_seat_id=ids["human_seat"],
            )
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

            with pytest.raises(psycopg.errors.RestrictViolation):
                connection.execute(
                    "DELETE FROM rd_run_seats WHERE id = %s",
                    (ids["human_seat"],),
                )


def test_assessment_source_insert_cannot_race_accepted_provenance_change(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as setup_connection:
            ids = _seed_assessment_inputs(setup_connection, prefix="assessment-write-skew")
            setup_connection.execute(
                """
                INSERT INTO requirement_assessments (
                  id, requirement_id, requirement_revision,
                  initial_strategy_snapshot_id, final_strategy_snapshot_id,
                  strategy_snapshot_id, status, created_by
                )
                VALUES (%s, %s, 1, %s, %s, %s, 'accepted', 'user_admin')
                """,
                (
                    ids["assessment"],
                    ids["requirement"],
                    ids["base_snapshot"],
                    ids["base_snapshot"],
                    ids["base_snapshot"],
                ),
            )
            setup_connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

        with psycopg.connect(database_url) as source_connection:
            source_connection.execute(
                """
                INSERT INTO rd_task_executor_policy_snapshots (
                  id, policy_id, policy_version, parent_snapshot_id, snapshot_kind,
                  resolution_context_key, resolution_revision, schema_version,
                  content_hash, payload_json, created_by
                )
                VALUES (
                  'assessment-write-skew-version-snapshot', %s, 1, %s,
                  'version_resolved', %s, 1, 1,
                  'assessment-write-skew-version-hash', '{}'::jsonb, 'user_admin'
                )
                """,
                (
                    ids["policy"],
                    ids["base_snapshot"],
                    f"version:{ids['version']}:scope:1",
                ),
            )
            source_connection.execute(
                """
                INSERT INTO rd_task_executor_policy_snapshot_sources (
                  id, snapshot_id, source_snapshot_id, requirement_id, assessment_id
                )
                VALUES (
                  'assessment-write-skew-source',
                  'assessment-write-skew-version-snapshot', %s, %s, %s
                )
                """,
                (
                    ids["base_snapshot"],
                    ids["requirement"],
                    ids["assessment"],
                ),
            )
            source_connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            source_connection.execute(
                """
                SELECT id
                FROM requirement_assessments
                WHERE id = %s
                FOR UPDATE
                """,
                (ids["assessment"],),
            )

            assessment_result = _execute_after_observed_lock_wait(
                database_url,
                lock_holding_connection=source_connection,
                statement="""
                    UPDATE requirement_assessments
                    SET status = 'rejected'
                    WHERE id = %s
                """,
                params=(ids["assessment"],),
            )

        assert "accepted assessment provenance" in assessment_result

        with psycopg.connect(database_url) as verification_connection:
            state = verification_connection.execute(
                """
                SELECT assessment.status, count(source.id)
                FROM requirement_assessments assessment
                LEFT JOIN rd_task_executor_policy_snapshot_sources source
                  ON source.assessment_id = assessment.id
                WHERE assessment.id = %s
                GROUP BY assessment.status
                """,
                (ids["assessment"],),
            ).fetchone()

        assert state == ("accepted", 1)


@pytest.mark.parametrize(
    "mutation",
    [
        "status",
        "requirement_revision",
        "initial_strategy_snapshot_id",
        "final_strategy_snapshot_id",
        "strategy_snapshot_id",
    ],
)
def test_accepted_assessment_provenance_is_unconditionally_immutable(
    postgres_admin_url: str,
    mutation: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as connection:
            ids = _seed_assessment_inputs(connection, prefix=f"accepted-freeze-{mutation}")
            connection.execute(
                """
                INSERT INTO requirement_assessments (
                  id, requirement_id, requirement_revision,
                  initial_strategy_snapshot_id, final_strategy_snapshot_id,
                  strategy_snapshot_id, status, created_by
                )
                VALUES (%s, %s, 1, %s, %s, %s, 'accepted', 'user_admin')
                """,
                (
                    ids["assessment"],
                    ids["requirement"],
                    ids["base_snapshot"],
                    ids["base_snapshot"],
                    ids["base_snapshot"],
                ),
            )
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

            statements: dict[str, tuple[str, object]] = {
                "status": ("status = %s", "rejected"),
                "requirement_revision": ("requirement_revision = %s", 2),
                "initial_strategy_snapshot_id": (
                    "initial_strategy_snapshot_id = %s",
                    ids["alternate_base_snapshot"],
                ),
                "final_strategy_snapshot_id": (
                    "final_strategy_snapshot_id = %s",
                    ids["alternate_base_snapshot"],
                ),
                "strategy_snapshot_id": (
                    "strategy_snapshot_id = %s",
                    ids["alternate_base_snapshot"],
                ),
            }
            set_clause, value = statements[mutation]
            with pytest.raises(
                psycopg.errors.RaiseException,
                match="accepted assessment provenance",
            ):
                connection.execute(
                    sql.SQL("UPDATE requirement_assessments SET {} WHERE id = %s").format(
                        sql.SQL(set_clause)
                    ),
                    (value, ids["assessment"]),
                )


@pytest.mark.parametrize("producer_type", ["human_user", "ai_employee"])
def test_feedback_insert_serializes_with_polymorphic_producer_delete(
    postgres_admin_url: str,
    producer_type: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as setup_connection:
            prefix = f"feedback-delete-race-{producer_type}"
            ids = _seed_feedback_context(setup_connection, prefix=prefix)
            if producer_type == "human_user":
                producer_id = f"{prefix}-user"
                producer_table = "users"
                setup_connection.execute(
                    """
                    INSERT INTO users (id, email, display_name, password_hash)
                    VALUES (%s, %s, 'feedback race producer', 'test-hash')
                    """,
                    (producer_id, f"{producer_id}@example.com"),
                )
            else:
                producer_id = ids["alternate_ai_employee"]
                producer_table = "rd_ai_employees"
            setup_connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

        with psycopg.connect(database_url) as feedback_connection:
            _insert_feedback(
                feedback_connection,
                ids=ids,
                feedback_id=f"{prefix}-feedback",
                producer_subject_type=producer_type,
                producer_subject_id=producer_id,
            )
            feedback_connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

            delete_result = _execute_after_observed_lock_wait(
                database_url,
                lock_holding_connection=feedback_connection,
                statement=sql.SQL("DELETE FROM {} WHERE id = %s").format(
                    sql.Identifier(producer_table)
                ),
                params=(producer_id,),
            )

        assert "feedback producer identity cannot be changed or deleted" in delete_result
        with psycopg.connect(database_url) as verification_connection:
            producer_count = verification_connection.execute(
                sql.SQL("SELECT count(*) FROM {} WHERE id = %s").format(
                    sql.Identifier(producer_table)
                ),
                (producer_id,),
            ).fetchone()
            feedback_count = verification_connection.execute(
                "SELECT count(*) FROM role_feedback_records WHERE id = %s",
                (f"{prefix}-feedback",),
            ).fetchone()

        assert producer_count == (1,)
        assert feedback_count == (1,)


def test_feedback_insert_cannot_race_run_seat_identity_update(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as setup_connection:
            ids = _seed_feedback_context(setup_connection, prefix="feedback-seat-race")
            setup_connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

        with psycopg.connect(database_url) as feedback_connection:
            _insert_feedback(
                feedback_connection,
                ids=ids,
                feedback_id="feedback-seat-race-feedback",
                producer_subject_type="human_user",
                producer_subject_id="user_admin",
                producer_role_code="reviewer",
                producer_seat_id=ids["human_seat"],
            )
            feedback_connection.execute("SET CONSTRAINTS ALL IMMEDIATE")

            update_result = _execute_after_observed_lock_wait(
                database_url,
                lock_holding_connection=feedback_connection,
                statement="UPDATE rd_run_seats SET role_code = 'architect' WHERE id = %s",
                params=(ids["human_seat"],),
            )

        assert "seat identity" in update_result

        with psycopg.connect(database_url) as verification_connection:
            seat_role = verification_connection.execute(
                "SELECT role_code FROM rd_run_seats WHERE id = %s",
                (ids["human_seat"],),
            ).fetchone()

        assert seat_role == ("reviewer",)


@pytest.mark.parametrize(
    "mutation",
    ["collaboration_run_id", "role_code", "subject_type", "subject_id"],
)
def test_run_seat_identity_is_immutable_from_creation(
    postgres_admin_url: str,
    mutation: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as connection:
            prefix = f"seat-created-freeze-{mutation}"
            ids = _seed_feedback_context(connection, prefix=prefix)
            other_ids = _seed_collaboration_scope(connection, prefix=f"{prefix}-other")
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

            statements: dict[str, tuple[str, tuple[object, ...]]] = {
                "collaboration_run_id": (
                    "collaboration_run_id = %s",
                    (other_ids["run"],),
                ),
                "role_code": ("role_code = %s", ("architect",)),
                "subject_type": (
                    "subject_type = 'ai_employee', human_user_id = NULL, "
                    "ai_employee_id = %s, executor_profile_id = %s",
                    (ids["ai_employee"], ids["executor_profile"]),
                ),
                "subject_id": ("human_user_id = %s", ("user_reviewer",)),
            }
            set_clause, params = statements[mutation]
            with pytest.raises(psycopg.errors.RaiseException, match="seat identity"):
                connection.execute(
                    sql.SQL("UPDATE rd_run_seats SET {} WHERE id = %s").format(sql.SQL(set_clause)),
                    (*params, ids["human_seat"]),
                )


def test_historical_run_update_uses_frozen_snapshot_ownership(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as connection:
            ids = _seed_collaboration_scope(connection, prefix="historical-run")
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

            connection.execute(
                """
                INSERT INTO products (id, code, name)
                VALUES ('historical-run-new-product', 'historical-run-new', 'New owner')
                """
            )
            connection.execute(
                """
                UPDATE rd_task_executor_policies
                SET product_id = 'historical-run-new-product'
                WHERE id = %s
                """,
                (ids["policy"],),
            )
            connection.commit()

            connection.execute(
                """
                UPDATE rd_collaboration_runs
                SET status = 'integrating'
                WHERE id = %s
                """,
                (ids["run"],),
            )
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()

        with psycopg.connect(database_url) as verification_connection:
            state = verification_connection.execute(
                """
                SELECT run.status, run.product_id, policy.product_id
                FROM rd_collaboration_runs run
                JOIN rd_task_executor_policy_snapshots snapshot
                  ON snapshot.id = run.strategy_snapshot_id
                JOIN rd_task_executor_policies policy ON policy.id = snapshot.policy_id
                WHERE run.id = %s
                """,
                (ids["run"],),
            ).fetchone()

        assert state == (
            "integrating",
            ids["product"],
            "historical-run-new-product",
        )


@pytest.mark.parametrize("policy_version", [0, -1])
def test_policy_version_must_be_positive(
    postgres_admin_url: str,
    policy_version: int,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url, autocommit=True) as connection:
            with pytest.raises(psycopg.errors.CheckViolation):
                connection.execute(
                    """
                    INSERT INTO rd_task_executor_policies (
                      id, name, brain_app_id, task_type, executor_type,
                      instruction_template, status, policy_version
                    )
                    VALUES (
                      %s, 'Invalid version', 'rd_brain', 'code_change', 'codex',
                      'invalid', 'active', %s
                    )
                    """,
                    (f"policy-version-{policy_version}", policy_version),
                )


def test_policy_version_is_monotonic_but_equal_legacy_update_is_allowed(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute(
                """
                INSERT INTO rd_task_executor_policies (
                  id, name, brain_app_id, task_type, executor_type,
                  instruction_template, status, policy_version
                )
                VALUES (
                  'policy-monotonic', 'Monotonic', 'rd_brain', 'code_change',
                  'codex', 'monotonic', 'active', 1
                )
                """
            )
            connection.execute(
                """
                UPDATE rd_task_executor_policies
                SET policy_version = 1
                WHERE id = 'policy-monotonic'
                """
            )
            connection.execute(
                """
                UPDATE rd_task_executor_policies
                SET policy_version = 2
                WHERE id = 'policy-monotonic'
                """
            )

            with pytest.raises(psycopg.errors.RaiseException, match="cannot decrease"):
                connection.execute(
                    """
                    UPDATE rd_task_executor_policies
                    SET policy_version = 1
                    WHERE id = 'policy-monotonic'
                    """
                )

            stored_version = connection.execute(
                """
                SELECT policy_version
                FROM rd_task_executor_policies
                WHERE id = 'policy-monotonic'
                """
            ).fetchone()

        assert stored_version == (2,)


def test_task3_repository_versions_support_real_optimistic_updates(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as connection:
            ids = _seed_collaboration_scope(connection, prefix="task3-repository-version")
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()
            connection.autocommit = True
            connection.execute(
                """
                INSERT INTO rd_work_items (
                  id, collaboration_run_id, plan_version, work_item_type,
                  title, objective, status, idempotency_key, version
                )
                VALUES (
                  'task3-version-work', %s, 1, 'implementation',
                  'Versioned work', 'Prove optimistic update', 'ready',
                  'task3-version-work', 1
                )
                """,
                (ids["run"],),
            )
            first_work_update = connection.execute(
                """
                UPDATE rd_work_items
                SET status = 'claimed', version = version + 1, updated_at = now()
                WHERE id = 'task3-version-work' AND version = 1
                RETURNING version
                """
            ).fetchone()
            stale_work_update = connection.execute(
                """
                UPDATE rd_work_items
                SET status = 'running', version = version + 1, updated_at = now()
                WHERE id = 'task3-version-work' AND version = 1
                RETURNING version
                """
            ).fetchone()

            connection.execute(
                """
                INSERT INTO product_git_repositories (
                  id, product_id, name, default_branch
                )
                VALUES ('task3-version-repository', %s, 'Task 3 repository', 'main')
                """,
                (ids["product"],),
            )
            connection.execute(
                """
                INSERT INTO product_version_branch_configs (
                  id, product_id, version_id, repository_id, working_branch,
                  branch_config_version, base_commit_sha
                )
                VALUES (
                  'task3-version-branch', %s, %s, 'task3-version-repository',
                  'version/task3', 1, 'base-1'
                )
                """,
                (ids["product"], ids["version"]),
            )
            first_branch_update = connection.execute(
                """
                UPDATE product_version_branch_configs
                SET base_commit_sha = 'base-2',
                    branch_config_version = branch_config_version + 1,
                    updated_at = now()
                WHERE id = 'task3-version-branch' AND branch_config_version = 1
                RETURNING branch_config_version, base_commit_sha
                """
            ).fetchone()
            stale_branch_update = connection.execute(
                """
                UPDATE product_version_branch_configs
                SET base_commit_sha = 'stale',
                    branch_config_version = branch_config_version + 1,
                    updated_at = now()
                WHERE id = 'task3-version-branch' AND branch_config_version = 1
                RETURNING branch_config_version
                """
            ).fetchone()

            with pytest.raises(psycopg.errors.CheckViolation):
                connection.execute(
                    """
                    UPDATE rd_work_items
                    SET version = 0
                    WHERE id = 'task3-version-work'
                    """
                )
            with pytest.raises(psycopg.errors.CheckViolation):
                connection.execute(
                    """
                    UPDATE product_version_branch_configs
                    SET branch_config_version = 0
                    WHERE id = 'task3-version-branch'
                    """
                )

        assert first_work_update == (2,)
        assert stale_work_update is None
        assert first_branch_update == (2, "base-2")
        assert stale_branch_update is None


def test_scope_change_operation_check_accepts_approved_typed_destinations(
    postgres_admin_url: str,
) -> None:
    with _temporary_database(postgres_admin_url) as database_url:
        _apply_historical_migrations(database_url, through=109)
        with psycopg.connect(database_url) as connection:
            ids = _seed_collaboration_scope(connection, prefix="typed-scope-operation")
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            connection.commit()
            connection.execute(
                """
                INSERT INTO product_git_repositories (id, product_id, name)
                VALUES ('typed-scope-repository', %s, 'Typed scope repository')
                """,
                (ids["product"],),
            )
            connection.execute(
                """
                INSERT INTO decision_requests (
                  id, brain_app_id, product_id, subject_type, subject_id,
                  decision_type, options_hash, expires_at, created_by
                )
                VALUES (
                  'typed-scope-decision', 'rd_brain', %s,
                  'rd_scope_change_request', 'typed-scope-request',
                  'scope_change', 'typed-options', now() + interval '1 hour',
                  'user_admin'
                )
                """,
                (ids["product"],),
            )
            connection.execute(
                """
                INSERT INTO rd_scope_change_requests (
                  id, product_version_id, request_id, source_run_id,
                  source_run_state, expected_scope_version,
                  expected_run_generation, operations_json, operations_hash,
                  reason, decision_request_id, requested_by
                )
                VALUES (
                  'typed-scope-request', %s, 'typed-scope-key', %s,
                  'running', 1, 1, '[]'::jsonb, 'typed-operations',
                  'verify typed operations', 'typed-scope-decision', 'user_admin'
                )
                """,
                (ids["version"], ids["run"]),
            )
            connection.execute(
                """
                INSERT INTO rd_scope_change_request_operations (
                  id, scope_change_request_id, position, op,
                  requirement_id, destination
                )
                VALUES (
                  'typed-remove', 'typed-scope-request', 0,
                  'remove_requirement', %s, 'approved_pool'
                )
                """,
                (ids["requirement"],),
            )
            connection.execute(
                """
                INSERT INTO rd_scope_change_request_operations (
                  id, scope_change_request_id, position, op,
                  repository_id, branch_config_version, base_commit_sha
                )
                VALUES (
                  'typed-baseline', 'typed-scope-request', 1,
                  'update_repository_baseline', 'typed-scope-repository', 2, 'base-2'
                )
                """
            )
            connection.commit()

        with psycopg.connect(database_url) as verification:
            operations = verification.execute(
                """
                SELECT op, destination
                FROM rd_scope_change_request_operations
                WHERE scope_change_request_id = 'typed-scope-request'
                ORDER BY position
                """
            ).fetchall()

        assert operations == [
            ("remove_requirement", "approved_pool"),
            ("update_repository_baseline", None),
        ]
