# Final PostgreSQL init migration-boundary report

## Scope

- Base: `e241a63d82eb09bd83b589ef6c267f7b46fa4ab9`
- Fix the fresh-volume path that exposed the complete application migration directory to
  PostgreSQL `/docker-entrypoint-initdb.d`.
- Keep ordinary and excluded/concurrent migration behavior under the API migration control
  plane.
- Code/infra/tests only; no product documentation or changelog changes.

## TDD evidence

### RED

Added `apps/api/tests/test_docker_migration_boundary.py` before changing Compose.

Command:

```bash
cd apps/api
uv run pytest tests/test_docker_migration_boundary.py -q
```

Result: `1 failed, 1 passed`. The failure identified the existing bind mount:

```text
./apps/api/app/db/migrations:/docker-entrypoint-initdb.d:ro
```

### GREEN

Removed that bind mount from the PostgreSQL service. The PostgreSQL image still installs the
pgvector extension files, while the API image continues to copy `apps/api/app` to `/app/app`.

Focused command:

```bash
cd apps/api
uv run pytest \
  tests/test_docker_migration_boundary.py \
  tests/test_api_entrypoint.py \
  tests/test_persistence_repository_boundaries.py -q
```

Result: `60 passed`.

The focused coverage proves:

- PostgreSQL Compose/init image configuration does not expose application migrations to
  `initdb.d`, so neither migration 121 nor migrations 125-128 have a fresh-volume bypass.
- the API Dockerfile packages the migration directory at the API entrypoint default path;
- API startup runs ordinary additions while excluding migration 121 and migrations 125-128;
- the repository compatibility path owns migrations 125-128 and applies them through the
  concurrent-index helper.

## Verification

### Compose model

```bash
docker compose config --no-env-resolution --quiet
docker compose config --no-env-resolution --format json
```

Result: valid configuration. The resolved PostgreSQL volumes contain only
`postgres_data:/var/lib/postgresql/data`; there is no `/docker-entrypoint-initdb.d` target.

### Real API image contents

Built `infra/docker/api.Dockerfile` as `e-ai-brain-api:postgres-init-boundary-test` and ran a
container filesystem assertion for:

- `/app/app/db/migrations/001_init.sql`
- `/app/app/db/migrations/121_requirement_driven_rd_cutover.sql`
- `/app/app/db/migrations/125_rd_dispatch_due_index.sql`
- `/app/app/db/migrations/126_rd_dispatch_page_index.sql`
- `/app/app/db/migrations/127_rd_active_run_dispatch_index.sql`
- `/app/app/db/migrations/128_rd_dependency_successor_index.sql`

Result: exit `0`; the image contains all `128` SQL migration files.

### Backend suite

```bash
cd apps/api
uv run ruff check tests/test_docker_migration_boundary.py
uv run pytest
```

Result: Ruff passed; `1642 passed, 4 skipped, 1 deselected`.
