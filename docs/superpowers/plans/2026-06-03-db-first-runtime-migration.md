# DB-First Runtime Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eventually remove the production `MemoryStore` runtime layer so every production API reads and writes PostgreSQL through repository/query services. Current work is an incremental DB-first migration; completed slices must persist through repository calls before handler return, while still-open slices may use the transitional read-model container documented below.

**Architecture:** Non-test `PERSISTENCE_MODE=memory` fails fast, and pure `MemoryStore` remains a test helper. In current `PERSISTENCE_MODE=postgres`, `build_store()` returns `PostgresRuntimeStore(repository)` as a lightweight repository dependency container; it does not restore business collections from `app_state_snapshots` or structure tables. Request completion no longer calls global `current_store.persist()` to copy process memory into PostgreSQL. Read-only caches/read models may be kept for performance when they are derived from PostgreSQL, rebuildable, and never used as write sources of truth. Migration is split by domain so each commit leaves the app runnable while remaining request-scoped projection helpers are replaced by SQL/read-model queries.

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

Production routes are considered fully DB-first only when all are true:

- The route does not mutate `current_store.<collection>` in `PERSISTENCE_MODE=postgres`.
- The route's read path uses a repository/SQL query or an explicitly named DB-backed read model.
- The route's write path persists inside the same handler/service call, with related audit/writeback rows in the same transaction when needed.
- The route has at least one test that would fail if data only lived in process memory.
- The docs record whether the module is fully DB-first or still transitional.

During the transition, a slice can be accepted as handler-level DB-first when it still mutates the in-process collection for compatibility but also writes the authoritative structure-table record and audit event through repository methods before the handler returns. Such slices must remain explicitly marked as transitional until the `current_store` mutation is removed.

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

- [x] **Step 1: Add failing tests for direct product writes**

Tests must create, patch, and delete product/version/module/Git repository/related system records, then rebuild an empty application store from DB and prove the API data came from tables, not process memory.

- [x] **Step 2: Add repository methods**

Add DB methods for product config:

- `list_products(active_only=False)`
- `get_product(product_id)`
- `create_product(payload, actor_id)`
- `update_product(product_id, updates, actor_id)`
- `delete_product(product_id, actor_id)`
- equivalent version/module/repository/system methods

- [x] **Step 3: Route postgres mode through repository**

In each product config handler, use `_postgres_snapshot_repository(current_store)` and execute direct DB methods when available. Keep MemoryStore fallback only for tests.

- [x] **Step 4: Remove request-end persistence dependence for product config**

Product config writes must be durable before the handler returns. Tests must fail if `trace_middleware` persistence is disabled.

Progress 2026-06-03: added `save_product_config_record` / `delete_product_config_record` repository calls for product, version, module, Git repository, and related-system create/update/delete handlers. The new regression disables request-end `persist()` and rebuilds the store from repository payloads to prove product-config writes are durable before handler return.

Progress 2026-06-03: added explicit product-config read repository methods for product list/detail, product versions, modules, Git repositories, and related systems. `GET /api/products`, `GET /api/products/{product_id}`, `GET /api/products/{product_id}/versions`, `GET /api/products/{product_id}/modules`, `GET /api/products/{product_id}/git-repositories`, and `GET /api/system/related-systems` now use repository-first reads when the runtime repository exposes these methods. Added stale-runtime regression `test_product_config_get_routes_use_repository_when_runtime_store_is_stale`.

## Task 4: Requirement Ledger DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_requirement_lifecycle.py`
- Modify: `apps/api/tests/test_database_persistence.py`

- [x] **Step 1: Add failing tests for direct requirement writes**

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

Progress 2026-06-03: added `save_requirement_record` / `delete_requirement_record` repository calls and route-level writes for requirement create, patch/version assignment, approve, reject, close, and delete. The new regression disables request-end `persist()` and rebuilds the store from repository payloads to prove pure requirement writes are durable before handler return. `append_requirement_task_id` is now covered by the AI Task/workflow transaction paths for product-detail-design generation and follow-up task creation.

## Task 5: AI Task And Workflow DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_graph_runtime.py`
- Modify: `apps/api/tests/test_review_actions.py`
- Modify: `apps/api/tests/test_database_persistence.py`

- [x] **Step 1: Add failing tests for task generation and graph writes**

Generate a task, start it, create graph run/checkpoint/review, approve review, restart API state, and assert all state comes from `ai_tasks`, `graph_runs`, `graph_checkpoints`, and `human_reviews`.

Progress 2026-06-03: added failing-then-passing no-persist regressions for task generation, follow-up task creation, task start success/failure, retry failure, Review approve/edit-approve/reject/request-more-info main paths, and cancel/submit-more-info task-state paths. `POST /api/requirements/{id}/generate-task` and `POST /api/ai-tasks` now call `save_requirement_and_ai_task_records` so requirement `task_ids`/status, the new AI task, and `ai_task.created` audit event are written before handler return. Task start success calls `save_task_start_records` to commit the AI task, optional model log, Human Review, Graph Run, Checkpoint, optional Code Review report, and startup audit events together. Task start failure paths call `save_task_state_records` to commit failed task state, optional model failure log, retry_started, and failure audit events before returning 4xx/5xx. Review approve/edit-approve/reject/request-more-info main paths now call `save_review_decision_records` to commit completed/failed/waiting-more-info task and review state, graph/checkpoint state, optional requirement status, optional Code Review report, knowledge deposit candidates, optional AI-created bugs, and audit events together. Cancel/submit-more-info now call `save_task_state_records` to commit task, optional pending review cancellation, optional graph/checkpoint state, and audit events together.

- [x] **Step 2: Add task/workflow transaction methods**

Task creation must update requirement `task_ids`, create task row, and audit in one transaction.

Progress 2026-06-03: added `save_requirement_and_ai_task_records`, `save_task_start_records`, `save_review_decision_records`, and `save_task_state_records`; task generation, follow-up creation, start success/failure, review decisions, cancel, and more-info submit now call these methods before handler return.

Progress 2026-06-03: `GET /api/requirements/{id}` and `GET /api/ai-tasks/{id}` now use a repository-backed read snapshot in PostgreSQL runtime, so stale global runtime `requirements` / `ai_tasks` collections no longer make detail pages 404. Strengthened `test_generate_task_writes_requirement_and_ai_task_without_request_persist` to clear runtime requirements/tasks before detail reads.

Progress 2026-06-03: `GET /api/graph-runs`, `GET /api/reviews/pending`, `GET /api/reviews/{id}`, `GET /api/writeback/results/{task_id}`, `GET /api/ai-tasks/{task_id}/code-review-report`, and `GET /api/export/tasks/{task_id}/markdown` now use a repository-backed read snapshot in PostgreSQL runtime. `POST /api/writeback/results/{task_id}` now writes the mock issue record and `mock_issue.written` audit event through `save_mock_writeback_record` before handler return. Strengthened `test_start_task_writes_review_graph_and_checkpoint_without_request_persist` and added `test_mock_writeback_writes_repository_without_request_persist`.

Progress 2026-06-03: task workflow GET routes moved one step past repository read snapshots. `GET /api/requirements/{id}`, `GET /api/ai-tasks/{id}`, `GET /api/graph-runs`, `GET /api/reviews/pending`, `GET /api/reviews/{id}`, `GET /api/writeback/results/{task_id}`, `GET /api/ai-tasks/{task_id}/code-review-report`, and `GET /api/export/tasks/{task_id}/markdown` now read task workflow repository source rows and build a request-scoped context for existing projections. Stale-runtime regressions now assert `get_task_workflow_source_rows` usage. Full SQL-per-route projection and removal of the production `PersistentMemoryStore` runtime remain open.

Progress 2026-06-03: task workflow write routes now use the same request-scoped source rows context when a repository is available. `POST /api/ai-tasks/{id}/start`, `POST /api/ai-tasks/{id}/cancel`, `POST /api/ai-tasks/{id}/more-info`, and Review approve/edit-approve/reject/request-more-info no longer need the global runtime store collections to be fresh before applying their existing repository transactions. Regressions clear global task/review/graph collections before these writes and assert `get_task_workflow_source_rows` usage. This still preserves a request-scoped projection helper while Task 8 Step 1 remains open.

Progress 2026-06-03: task start no longer writes newly generated Code Review reports, Graph Runs, Graph Checkpoints, or Human Reviews into the repository request context before persistence. These records are built as explicit transaction payloads and passed to `save_task_start_records`; MemoryStore collection writes remain only under the test-helper fallback. Mock Writeback generation now also guards the in-memory idempotency map behind the test-helper fallback and persists the generated row plus audit event directly through `save_mock_writeback_record`.

- [ ] **Step 3: Remove remaining task writeback through `current_store.ai_tasks[...]` in postgres mode**

MemoryStore fallback remains only for test mode.

## Task 6: Knowledge, Audit, Assistant, And Code Review DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_knowledge_governance.py`
- Modify: `apps/api/tests/test_assistant_chat.py`
- Modify: `apps/api/tests/test_code_review_report.py`

- [x] **Step 1: Move knowledge document/chunk/deposit writes to repository transactions**

Progress 2026-06-03: added `save_knowledge_document_records`, `delete_knowledge_document_records`, and `save_knowledge_deposit_records`. Knowledge document create/update/retry/delete and deposit approve/reject now write documents, chunks, deposits, optional embedding model logs, and audit events before handler return. Added no-persist regression `test_knowledge_routes_write_repository_without_request_persist`.

Progress 2026-06-03: knowledge indexing now builds document/chunk payloads directly for repository calls. `POST/PATCH/retry/delete /api/knowledge/documents` and deposit approve/reject no longer require `current_store.knowledge_documents`, `current_store.knowledge_chunks`, or `current_store.knowledge_deposits` to be used as the PostgreSQL write source; those collections are updated only in the MemoryStore test-helper fallback.
- [x] **Step 2: Move assistant conversation/message writes to repository transactions**

Progress 2026-06-03: added `save_assistant_chat_records`. Assistant chat success now writes conversation, user message, assistant message, model log, and audit events before handler return; assistant model-call failure writes failed model log and audit event. Added no-persist regression `test_assistant_chat_writes_repository_without_request_persist`.
- [x] **Step 3: Move MR/PR snapshots and code review reports to repository transactions**

Progress 2026-06-03: added `save_gitlab_review_snapshot_record`. GitLab MR / GitHub PR snapshot success, same-diff reuse audit, and diff-limit failure audit now write before handler return. Code Review report generation and confirmation are covered by task start and review decision transactions. Added no-persist regression `test_gitlab_snapshot_writes_repository_without_request_persist`.
- [x] **Step 4: Ensure permission filtering happens in SQL for knowledge and assistant history**

Progress 2026-06-03: `GET /api/knowledge/documents` now uses repository-first reads when available. PostgreSQL filters permission roles, keyword, document type, and index status in SQL and returns `chunk_count` from `knowledge_chunks` aggregation. Added stale-runtime regression `test_knowledge_document_list_uses_repository_when_runtime_store_is_stale`.

Progress 2026-06-03: `GET /api/knowledge/deposits` now uses repository-first reads when available. PostgreSQL filters deposit `status` in the query layer, and stale global runtime `knowledge_deposits` no longer drives the response. Added stale-runtime regression `test_knowledge_deposit_list_uses_repository_when_runtime_store_is_stale`.

Progress 2026-06-03: `POST /api/knowledge/search` now uses repository-first candidate chunk reads when available. PostgreSQL filters document permission roles, chunk permission roles, searchable document status, and keyword candidates in the query layer; route-level ranking still preserves keyword fallback and compatible-vector scoring semantics. Added stale-runtime regression `test_knowledge_search_uses_repository_when_runtime_store_is_stale`.

Progress 2026-06-03: `POST /api/knowledge/deposits/{id}/approve` and `/reject` now read the current deposit record from repository when available before applying the decision. The no-persist knowledge regression now seeds deposits in repository payload, clears runtime `knowledge_deposits`, and verifies approve/reject still write documents/chunks/deposit state/audit events back to repository.

Progress 2026-06-03: `GET /api/assistant/conversations` and `GET /api/assistant/conversations/{conversation_id}/messages` now use repository-first reads when available. PostgreSQL filters by current `user_id`, and cross-user message reads return 404 before any message data is returned. Added stale-runtime regression `test_assistant_history_uses_repository_when_runtime_store_is_stale`.

## Task 7: DevOps, Insights, Planning, Bugs, Lifecycle, Dashboard DB-First

**Files:**
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Modify: corresponding tests under `apps/api/tests/`

- [x] **Step 1: Convert Bug CRUD to DB-first**

Progress 2026-06-03: added `save_bug_record` and `delete_bug_record`. Bug create/update/delete now write the `bugs` row and audit event before handler return; delete clears duplicate links that point to the removed Bug. Added no-persist regression `test_bug_api_writes_repository_without_request_persist`.
- [x] **Step 2: Convert collector, pending attribution, GitLab/Jenkins/online metrics to DB-first**

Progress 2026-06-03: added single-record repository writes for collector runs, pending attribution items, GitLab daily code metrics, Jenkins release records, and online log metrics. Create/update/resolve operations now persist the business record and audit event before handler return. Added no-persist regression `test_operational_routes_write_repository_without_request_persist`.

Progress 2026-06-03: collector run create/update, pending attribution create/resolve, GitLab daily metric create, Jenkins release create, and online log metric create now guard all request collection mutations behind the MemoryStore test-helper fallback and use `_record_audit_event` plus single-record repository writes for PostgreSQL runtime.

Progress 2026-06-03: collector run, pending attribution, GitLab daily metric, Jenkins release, and online log metric list routes now read repository-first and apply filters/sorting through the SQL/repository boundary in PostgreSQL runtime. Added stale-runtime regression `test_operational_lists_use_repository_when_runtime_store_is_stale`.
- [x] **Step 3: Convert user usage, user feedback, and iteration planning to DB-first**

Progress 2026-06-03: added repository writes for user usage metrics, user feedback, iteration suggestions, and iteration decisions. Feedback handling, suggestion generation, and decision/convert-to-requirement now persist before handler return; conversion writes the new requirement, suggestion, decision, and audit events together. Added no-persist regression `test_insight_planning_routes_write_repository_without_request_persist`.

Progress 2026-06-03: user usage metric create, user feedback create/update, iteration suggestion generation, and iteration decision now guard request collection mutations behind the MemoryStore test-helper fallback. Iteration suggestion conversion returns the new requirement and its audit event as explicit payloads so the repository transaction persists requirement, suggestion, decision, and audit rows together under `PostgresRuntimeStore`.

Progress 2026-06-03: user usage metric, user feedback, and iteration suggestion list routes now read repository-first and apply filters/sorting through the SQL/repository boundary in PostgreSQL runtime. Added stale-runtime regression `test_insight_planning_lists_use_repository_when_runtime_store_is_stale`.
- [ ] **Step 4: Convert lifecycle context and dashboard to SQL/materialized read models**

Progress 2026-06-03: lifecycle context and IT-team dashboard generated materialized records now persist before handler return; added no-persist regression `test_lifecycle_and_dashboard_handlers_write_repository_without_request_persist`. Full SQL/materialized read model aggregation is still pending and this step remains open.

Progress 2026-06-03: lifecycle context and IT-team dashboard read routes now avoid the stale global runtime store in PostgreSQL runtime before aggregating. Added regression `test_lifecycle_and_dashboard_use_repository_source_rows_when_runtime_store_is_stale`. Full SQL/materialized aggregation remains pending.

Review fix 2026-06-03: read snapshot GET routes exposed that request-end global `persist()` could overwrite repository data with stale runtime store collections. Middleware first skipped global `persist()` for GET/HEAD/OPTIONS, then Task 8 removed the request-end `persist()` call for all API requests; handler-level repository writes continue to persist materialized lifecycle/dashboard records. Added regression `test_repository_read_snapshot_get_does_not_persist_stale_runtime_store`.

Progress 2026-06-03: `/api/dashboard/it-team` no longer rebuilds a repository read snapshot before aggregating in PostgreSQL runtime. The route now calls `get_dashboard_it_team_source_rows` to read structure-table source rows through repository methods and writes the current product/time-window snapshot with `save_dashboard_metric_snapshot_record`. The stale-runtime regressions now assert dashboard source-row reads and direct snapshot writes.

Progress 2026-06-03: `/api/lifecycle/context` no longer rebuilds a repository read snapshot before aggregating in PostgreSQL runtime. The route now calls `get_lifecycle_context_source_rows`, builds a request-scoped source context from structure-table rows, and writes generated lifecycle edges/risks back through `save_lifecycle_context`. Full algorithm-level SQL/materialized aggregation still keeps this step open.

Progress 2026-06-03: lifecycle source rows now hydrate a dedicated `LifecycleContextReadModel` instead of `MemoryStore()`. The lifecycle route still reuses the existing relation/risk algorithms, but this removes MemoryStore persistence/counter semantics from the PostgreSQL lifecycle aggregation path while the deeper SQL/materialized read model work remains open.

## Task 8: Remove Production PersistentMemoryStore

**Files:**
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/store.py`
- Modify: `apps/api/tests/conftest.py`
- Modify: docs and changelog

- [x] **Step 1: Change `build_store()`**

In postgres mode, `build_store()` must return a DB runtime dependency container, not `PersistentMemoryStore`.

Progress 2026-06-03: added `PostgresRuntimeStore(repository)` and changed `build_store()` to return it in postgres mode. `_postgres_snapshot_repository()` now resolves the repository from any runtime container, not only `PersistentMemoryStore`. Added `test_build_store_uses_postgres_runtime_container` to ensure postgres startup no longer returns `PersistentMemoryStore` or preloads product/requirement/task collections.

Progress 2026-06-03: product configuration write routes, requirement write routes, generated/follow-up AI task creation, and Bug create/update/delete now rebuild their validation context from repository source rows when running under `PostgresRuntimeStore`. Added regressions for product config writes and requirement/task writes using an empty postgres runtime container, and extended task workflow source rows with related systems, bugs, GitLab metrics, Jenkins releases, and online log metrics used by downstream task contexts.

Progress 2026-06-03: operational write routes (collector runs, pending attribution, GitLab daily metrics, Jenkins releases, online log metrics) and insight/planning write routes (usage metrics, user feedback, iteration suggestions and decisions) now rebuild validation/current-record context from repository source rows when running under an empty `PostgresRuntimeStore`. `GET /api/requirements` now reads task workflow source rows instead of falling back to the global runtime collections. The operational and insight/planning no-persist regressions now run against `PostgresRuntimeStore(repository)`.

Progress 2026-06-03: model gateway config create/update/delete/test audit routes now rebuild config/log context from repository rows under an empty `PostgresRuntimeStore`, and assistant chat now rebuilds current-user conversations/messages plus task workflow/model gateway context before continuing a conversation. Updated regressions cover model gateway create/update/delete and assistant chat continuation using `PostgresRuntimeStore(repository)`.

Progress 2026-06-03: knowledge document create/update/retry/delete and knowledge deposit approve/reject now rebuild product, document, chunk, deposit, and model gateway context from repository rows under an empty `PostgresRuntimeStore`. The knowledge no-persist regression now runs against `PostgresRuntimeStore(repository)`.

Progress 2026-06-03: GitLab MR preview/snapshot and GitHub PR list/preview/snapshot now rebuild product Git binding, requirement, and technical-solution context from repository source rows under an empty `PostgresRuntimeStore`. Added regressions for GitLab snapshot success/reuse/failure audit persistence and GitHub list/preview audit persistence without request-end `persist()`.

Progress 2026-06-03: removed the remaining production read-snapshot fallback from `_repository_read_model_store`; it no longer calls `PersistentMemoryStore.from_repository(repository)`. `GET /api/brain-apps` and `/api/brain-apps/{id}` now read the `brain_apps` repository payload under `PostgresRuntimeStore`. Knowledge deposit reject and Mock Writeback generation now use knowledge/task workflow source rows before applying repository writes.

Progress 2026-06-03: repository source rows now hydrate `_RepositoryRequestContext`, which does not inherit `MemoryStore`; `MemoryStore` remains available only for test helper and explicit test-mode fallback. Product configuration writes, model gateway config writes/tests, and assistant chat persistence now build records/payloads locally and call repository writes instead of mutating repository-backed context collections as the write source.

- [x] **Step 2: Remove global request-end persistence**

Delete the middleware branch:

```python
if request.url.path.startswith("/api/") and hasattr(current_store, "persist"):
    current_store.persist()
```

Progress 2026-06-03: deleted the API middleware request-end `persist()` call entirely. Added regression `test_api_requests_do_not_call_global_request_end_persist`. Removing the global hook exposed model gateway config writes as a missing direct-write path; added `save_model_gateway_records` and wired config create/update/delete/test audit to repository writes. Backend full regression passed after removal.

- [x] **Step 3: Delete `app_state_snapshots` production fallback usage**

Keep migrations non-destructive, but stop using `app_state_snapshots` for business runtime state in postgres mode.

Progress 2026-06-03: `PersistentMemoryStore.from_repository()` no longer reads `repository.load()` / `app_state_snapshots`, and `PersistentMemoryStore.persist()` no longer calls `repository.save(payload)`. Added regressions `test_persistent_store_does_not_restore_business_state_from_app_snapshot_payload` and `test_persistent_store_persist_does_not_write_app_snapshot_payload`. Historical `app_state_snapshots` table remains non-destructively in migrations.

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
