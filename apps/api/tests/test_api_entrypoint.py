from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_api_entrypoint_runs_only_ordinary_additive_migrations(tmp_path: Path) -> None:
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    expected_sql = [
        "SELECT 'ordinary-before-cutover';",
        "SELECT 'ordinary-after-cutover';",
        "SELECT 'ordinary-after-dispatch-indexes';",
    ]
    migrations = {
        "120_before.sql": expected_sql[0],
        "121_requirement_driven_rd_cutover.sql": "SELECT 'destructive-cutover';",
        "122_after.sql": expected_sql[1],
        "125_rd_dispatch_due_index.sql": "SELECT 'blocking-index-125';",
        "126_rd_dispatch_page_index.sql": "SELECT 'blocking-index-126';",
        "127_rd_active_run_dispatch_index.sql": "SELECT 'blocking-index-127';",
        "128_rd_dependency_successor_index.sql": "SELECT 'blocking-index-128';",
        "129_after.sql": expected_sql[2],
    }
    for filename, sql in migrations.items():
        (migration_dir / filename).write_text(sql, encoding="utf-8")

    module_dir = tmp_path / "fake-python"
    module_dir.mkdir()
    (module_dir / "psycopg.py").write_text(
        """
import os


class OperationalError(Exception):
    pass


class _Cursor:
    def __init__(self):
        self._row = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        normalized = sql.strip()
        self._row = None
        if normalized.startswith("SELECT checksum FROM app_schema_migrations"):
            filename = params[0]
            ledger_path = os.environ["ENTRYPOINT_LEDGER"]
            if os.path.exists(ledger_path):
                with open(ledger_path, encoding="utf-8") as stream:
                    for line in stream:
                        stored_filename, checksum = line.rstrip("\\n").split(":", 1)
                        if stored_filename == filename:
                            self._row = (checksum,)
                            return
        elif normalized.startswith("INSERT INTO app_schema_migrations"):
            with open(os.environ["ENTRYPOINT_LEDGER"], "a", encoding="utf-8") as stream:
                stream.write(f"{params[0]}:{params[1]}\\n")
        if normalized.startswith("SELECT 'ordinary"):
            with open(os.environ["ENTRYPOINT_SQL_LOG"], "a", encoding="utf-8") as stream:
                stream.write(normalized + "\\n")
        if (
            "app_schema_migrations" in normalized
            or "pg_advisory_lock" in normalized
            or "pg_advisory_unlock" in normalized
        ):
            with open(os.environ["ENTRYPOINT_CONTROL_LOG"], "a", encoding="utf-8") as stream:
                stream.write(normalized + "\\n")

    def fetchone(self):
        return self._row


class _Connection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return _Cursor()

    def commit(self):
        with open(os.environ["ENTRYPOINT_CONTROL_LOG"], "a", encoding="utf-8") as stream:
            stream.write("COMMIT\\n")


def connect(_database_url, *, autocommit):
    assert autocommit is False
    return _Connection()
""".strip(),
        encoding="utf-8",
    )
    sql_log = tmp_path / "executed.sql"
    control_log = tmp_path / "control.sql"
    ledger = tmp_path / "migration-ledger.txt"
    entrypoint = Path(__file__).parents[3] / "infra" / "docker" / "api-entrypoint.sh"
    environment = {
        **os.environ,
        "API_MIGRATION_DIR": str(migration_dir),
        "DATABASE_URL": "postgresql://entrypoint-test",
        "ENTRYPOINT_SQL_LOG": str(sql_log),
        "ENTRYPOINT_CONTROL_LOG": str(control_log),
        "ENTRYPOINT_LEDGER": str(ledger),
        "PYTHONPATH": str(module_dir),
    }

    subprocess.run(
        ["/bin/sh", str(entrypoint), "/usr/bin/true"],
        check=True,
        env=environment,
    )
    subprocess.run(
        ["/bin/sh", str(entrypoint), "/usr/bin/true"],
        check=True,
        env=environment,
    )

    assert sql_log.read_text(encoding="utf-8").splitlines() == expected_sql
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == len(expected_sql)
    controls = control_log.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS app_schema_migrations" in controls
    assert "pg_advisory_lock" in controls
    assert "INSERT INTO app_schema_migrations" in controls
    # The ledger table is committed once on each startup.  Every newly applied
    # migration then commits its SQL together with its individual ledger row,
    # while the session advisory lock remains held across the whole scan.
    assert controls.count("COMMIT") == len(expected_sql) + 2

    (migration_dir / "120_before.sql").write_text("SELECT 'changed';", encoding="utf-8")
    mismatch = subprocess.run(
        ["/bin/sh", str(entrypoint), "/usr/bin/true"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert mismatch.returncode != 0
    assert "migration checksum mismatch: 120_before.sql" in mismatch.stderr
