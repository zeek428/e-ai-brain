#!/bin/sh
set -eu

python - <<'PY'
from pathlib import Path
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

for attempt in range(30):
    try:
        with psycopg.connect(database_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                for path in sorted(migration_dir.glob("*.sql")):
                    if path.name in startup_excluded_migrations:
                        continue
                    cursor.execute(path.read_text())
        break
    except psycopg.OperationalError:
        if attempt == 29:
            raise
        time.sleep(1)
PY

exec "$@"
