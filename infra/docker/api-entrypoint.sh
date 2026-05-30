#!/bin/sh
set -eu

python - <<'PY'
from pathlib import Path
import os
import time

import psycopg

database_url = os.environ["DATABASE_URL"]
migration_dir = Path("/app/app/db/migrations")

for attempt in range(30):
    try:
        with psycopg.connect(database_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                for path in sorted(migration_dir.glob("*.sql")):
                    cursor.execute(path.read_text())
        break
    except psycopg.OperationalError:
        if attempt == 29:
            raise
        time.sleep(1)
PY

exec "$@"
