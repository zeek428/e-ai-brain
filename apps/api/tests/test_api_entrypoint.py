from __future__ import annotations

import os
from pathlib import Path
import subprocess


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
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql):
        with open(os.environ["ENTRYPOINT_SQL_LOG"], "a", encoding="utf-8") as stream:
            stream.write(sql.strip() + "\\n")


class _Connection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return _Cursor()


def connect(_database_url, *, autocommit):
    assert autocommit is True
    return _Connection()
""".strip(),
        encoding="utf-8",
    )
    sql_log = tmp_path / "executed.sql"
    entrypoint = Path(__file__).parents[3] / "infra" / "docker" / "api-entrypoint.sh"
    environment = {
        **os.environ,
        "API_MIGRATION_DIR": str(migration_dir),
        "DATABASE_URL": "postgresql://entrypoint-test",
        "ENTRYPOINT_SQL_LOG": str(sql_log),
        "PYTHONPATH": str(module_dir),
    }

    subprocess.run(
        ["/bin/sh", str(entrypoint), "/usr/bin/true"],
        check=True,
        env=environment,
    )

    assert sql_log.read_text(encoding="utf-8").splitlines() == expected_sql
