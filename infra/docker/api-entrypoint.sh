#!/bin/sh
set -eu

python - <<'PY'
from pathlib import Path
from hashlib import sha256
import os
import time

import psycopg

database_url = os.environ["DATABASE_URL"]
migration_dir = Path(os.environ.get("API_MIGRATION_DIR", "/app/app/db/migrations"))
startup_excluded_migrations = {
    "121_requirement_driven_rd_cutover.sql",
    "125_rd_dispatch_due_index.sql",
    "126_rd_dispatch_page_index.sql",
    "127_rd_active_run_dispatch_index.sql",
    "128_rd_dependency_successor_index.sql",
}
migration_lock_key = "schema-migrations:ordinary-additive"


def migration_checksum(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()

for attempt in range(30):
    try:
        with psycopg.connect(database_url, autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (migration_lock_key,))
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_schema_migrations (
                      filename text PRIMARY KEY,
                      checksum text NOT NULL,
                      applied_at timestamptz NOT NULL DEFAULT now()
                    )
                    """
                )
                # The session-level advisory lock survives this commit.  Make
                # the ledger relation durable before processing individual
                # migration transactions.
                connection.commit()
                for path in sorted(migration_dir.glob("*.sql")):
                    if path.name in startup_excluded_migrations:
                        continue
                    checksum = migration_checksum(path)
                    cursor.execute(
                        "SELECT checksum FROM app_schema_migrations WHERE filename = %s",
                        (path.name,),
                    )
                    existing = cursor.fetchone()
                    if existing is not None:
                        if str(existing[0]) != checksum:
                            raise RuntimeError(
                                f"migration checksum mismatch: {path.name}; "
                                "create a new migration instead of modifying an applied file"
                            )
                        continue
                    cursor.execute(path.read_text())
                    cursor.execute(
                        "INSERT INTO app_schema_migrations (filename, checksum) VALUES (%s, %s)",
                        (path.name, checksum),
                    )
                    # Ordinary migration SQL and its ledger row are one
                    # durable unit.  Commit per file so a later failure does
                    # not hold earlier DDL locks or replay prior migrations.
                    connection.commit()
        break
    except psycopg.OperationalError:
        if attempt == 29:
            raise
        time.sleep(1)
PY

exec "$@"
