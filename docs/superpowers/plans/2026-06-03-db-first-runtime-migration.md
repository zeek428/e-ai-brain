# DB-First Runtime Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the production `MemoryStore` runtime layer so every production API reads and writes PostgreSQL through repository/query services.

**Architecture:** Keep `MemoryStore` only under `APP_ENV=test/testing/pytest` as a pure test helper. In `PERSISTENCE_MODE=postgres`, FastAPI handlers must use DB-backed repositories directly; request completion must not call a global `current_store.persist()` to copy process memory into PostgreSQL. Migration is split by domain so each commit leaves the app runnable.

**Tech Stack:** FastAPI, Python 3.12, psycopg, PostgreSQL, pgvector, pytest, ruff, React/TypeScript frontend.

---

## File Structure

- `apps/api/app/main.py`: route wiring, dependency helpers, temporary store guards while routes are migrated.
- `apps/api/app/core/persistence.py`: current structured table loaders/upserts; add DB-first repository methods here first, then split into domain files after behavior is stable.
- `apps/api/app/core/store.py`: keep only as test helper; no new production behavior should be added here.
- `apps/api/app/db/migrations/*.sql`: add DB-owned ID counter and any missing structure needed before route migration.
- `apps/api/tests/test_foundation.py`: runtime-mode and guardrail tests.
- `apps/api/tests/test_database_persistence.py`: repository and Postgres-style persistence tests.
- `docs/02-specs/enterprise-ai-brain/spec.md`: source-of-truth architecture and migration status.
- `docs/02-specs/enterprise-ai-brain/api.md`: API persistence semantics.
- `docs/02-specs/enterprise-ai-brain/test-case.md`: acceptance coverage.
- `docs/changelog.md`: migration notes per commit.

## Migration Rule

Production routes are considered migrated only when all are true:

- The route does not mutate `current_store.<collection>` in `PERSISTENCE_MODE=postgres`.
- The route's read path uses a repository/SQL query or an explicitly named DB-backed read model.
- The route's write path persists inside the same handler/service call, with related audit/writeback rows in the same transaction when needed.
- The route has at least one test that would fail if data only lived in process memory.
- The docs record whether the module is fully DB-first or still transitional.

## Task 1: Runtime Guardrails And Inventory

**Files:**
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_foundation.py`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Write failing tests for production guardrails**

Add tests that assert non-test postgres mode must not rely on request-end `PersistentMemoryStore.persist()` as the production synchronization boundary. Start with a narrow helper test instead of breaking every route at once:

```python
def test_postgres_runtime_reports_db_first_migration_mode(monkeypatch):
    from app.core.config import Settings
    from app.main import _runtime_data_access_mode

    settings = Settings(
        app_env="local",
        persistence_mode="postgres",
        database_url="postgresql://ai_brain:password@postgres:5432/ai_brain",
    )

    assert _runtime_data_access_mode(settings) == "db_first_migration"
```

- [x] **Step 2: Run the failing test**

Run:

```bash
cd apps/api
uv run pytest tests/test_foundation.py::test_postgres_runtime_reports_db_first_migration_mode -q
```

Expected: fail because `_runtime_data_access_mode` does not exist.

- [x] **Step 3: Implement the smallest helper and expose migration status in health**

Add `_runtime_data_access_mode(settings)` in `apps/api/app/main.py`:

```python
def _runtime_data_access_mode(runtime_settings=settings) -> str:
    if runtime_settings.persistence_mode == "memory":
        return "memory_test_helper"
    return "db_first_migration"
```

Include the returned value in `/health` as `data_access_mode`.

- [x] **Step 4: Run tests and API health check**

Run:

```bash
cd apps/api
uv run pytest tests/test_foundation.py::test_postgres_runtime_reports_db_first_migration_mode -q
uv run ruff check app tests
curl -sS http://127.0.0.1:8000/health
```

Expected: test and ruff pass; health returns `data_access_mode=db_first_migration` after API restart.

- [x] **Step 5: Update docs and changelog**

Document that the runtime is in DB-first migration mode and that `PersistentMemoryStore.persist()` is transitional debt, not an acceptable production endpoint pattern.

## Task 2: DB-Owned ID Generation

**Files:**
- Create: `apps/api/app/db/migrations/023_db_first_id_counters.sql`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/tests/test_database_persistence.py`

- [x] **Step 1: Write failing repository tests**

Add a test proving ID allocation survives independent store/repository instances and does not rely on process memory counters.

```python
def test_postgres_repository_allocates_ids_without_memory_counters():
    repository = InMemoryDbFirstCounterRepository()

    assert repository.next_id("requirement") == "requirement_001"
    assert repository.next_id("requirement") == "requirement_002"
```

- [x] **Step 2: Add `id_counters` migration**

Create:

```sql
CREATE TABLE IF NOT EXISTS id_counters (
  prefix text PRIMARY KEY,
  next_value integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
```

- [x] **Step 3: Add `PostgresSnapshotRepository.next_id(prefix)`**

Use `SELECT ... FOR UPDATE` inside one transaction. If a prefix does not exist, seed from the current maximum numeric suffix in the matching structure table before returning the next ID.

- [x] **Step 4: Run focused tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_database_persistence.py -q
uv run ruff check app tests
```

Expected: pass.

## Task 3: Product Configuration DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_product_system_config.py`
- Modify: `apps/api/tests/test_database_persistence.py`

- [ ] **Step 1: Add failing tests for direct product writes**

Tests must create, patch, and delete product/version/module/Git repository/related system records, then rebuild an empty application store from DB and prove the API data came from tables, not process memory.

- [ ] **Step 2: Add repository methods**

Add DB methods for product config:

- `list_products(active_only=False)`
- `get_product(product_id)`
- `create_product(payload, actor_id)`
- `update_product(product_id, updates, actor_id)`
- `delete_product(product_id, actor_id)`
- equivalent version/module/repository/system methods

- [ ] **Step 3: Route postgres mode through repository**

In each product config handler, use `_postgres_snapshot_repository(current_store)` and execute direct DB methods when available. Keep MemoryStore fallback only for tests.

- [ ] **Step 4: Remove request-end persistence dependence for product config**

Product config writes must be durable before the handler returns. Tests must fail if `trace_middleware` persistence is disabled.

## Task 4: Requirement Ledger DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_requirement_lifecycle.py`
- Modify: `apps/api/tests/test_database_persistence.py`

- [ ] **Step 1: Add failing tests for direct requirement writes**

Cover create, approve, reject, close, patch, delete, and version assignment.

- [ ] **Step 2: Add repository methods**

Add DB methods for:

- `create_requirement`
- `update_requirement`
- `delete_requirement`
- `transition_requirement`
- `append_requirement_task_id`

- [ ] **Step 3: Move audit into the same transaction**

Requirement state changes and corresponding audit events must commit together.

## Task 5: AI Task And Workflow DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_graph_runtime.py`
- Modify: `apps/api/tests/test_review_actions.py`
- Modify: `apps/api/tests/test_database_persistence.py`

- [ ] **Step 1: Add failing tests for task generation and graph writes**

Generate a task, start it, create graph run/checkpoint/review, approve review, restart API state, and assert all state comes from `ai_tasks`, `graph_runs`, `graph_checkpoints`, and `human_reviews`.

- [ ] **Step 2: Add task/workflow transaction methods**

Task creation must update requirement `task_ids`, create task row, and audit in one transaction.

- [ ] **Step 3: Remove task writeback through `current_store.ai_tasks[...]` in postgres mode**

MemoryStore fallback remains only for test mode.

## Task 6: Knowledge, Audit, Assistant, And Code Review DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_knowledge_governance.py`
- Modify: `apps/api/tests/test_assistant_chat.py`
- Modify: `apps/api/tests/test_code_review_report.py`

- [ ] **Step 1: Move knowledge document/chunk/deposit writes to repository transactions**
- [ ] **Step 2: Move assistant conversation/message writes to repository transactions**
- [ ] **Step 3: Move MR/PR snapshots and code review reports to repository transactions**
- [ ] **Step 4: Ensure permission filtering happens in SQL for knowledge and assistant history**

## Task 7: DevOps, Insights, Planning, Bugs, Lifecycle, Dashboard DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: corresponding tests under `apps/api/tests/`

- [ ] **Step 1: Convert Bug CRUD to DB-first**
- [ ] **Step 2: Convert collector, pending attribution, GitLab/Jenkins/online metrics to DB-first**
- [ ] **Step 3: Convert user usage, user feedback, and iteration planning to DB-first**
- [ ] **Step 4: Convert lifecycle context and dashboard to SQL/materialized read models**

## Task 8: Remove Production PersistentMemoryStore

**Files:**
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/store.py`
- Modify: `apps/api/tests/conftest.py`
- Modify: docs and changelog

- [ ] **Step 1: Change `build_store()`**

In postgres mode, `build_store()` must return a DB runtime dependency container, not `PersistentMemoryStore`.

- [ ] **Step 2: Remove global request-end persistence**

Delete the middleware branch:

```python
if request.url.path.startswith("/api/") and hasattr(current_store, "persist"):
    current_store.persist()
```

- [ ] **Step 3: Delete `app_state_snapshots` production fallback usage**

Keep migrations non-destructive, but stop using `app_state_snapshots` for business runtime state in postgres mode.

- [ ] **Step 4: Run full verification**

Run:

```bash
cd apps/api
uv run ruff check app tests
uv run pytest
cd ../web
npm test
npm run build
```

Expected: all pass.

## Completion Criteria

- No production route uses MemoryStore as source of truth.
- No production route depends on request-end `persist()`.
- `MemoryStore` is only imported by tests or explicitly test-only helpers.
- `/health` exposes commit/runtime/data access mode so old-process issues are visible.
- Docs no longer describe `app_state_snapshots` as a production fallback.
