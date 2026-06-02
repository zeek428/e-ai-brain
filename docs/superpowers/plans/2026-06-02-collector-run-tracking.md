# Collector Run Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real collector/import run tracking so GitLab, Jenkins, online-log, usage, and feedback imports have auditable run records without inventing metric data.

**Execution Status:** Confirmed by the user on 2026-06-02, implemented, browser-smoked, verified, and recorded in the final collector-run tracking commit.

**Architecture:** Keep metric records in their existing domain tables and add a separate `collector_runs` business table for ingestion attempts. Backend APIs create/update/query run records, the DevOps page displays them, and audit events record each state change. This is not a real external collector integration yet; it is the durable run ledger needed before connectors are attached.

**Tech Stack:** FastAPI, PostgreSQL SQL migrations, in-process `MemoryStore` for tests, React + TypeScript, Ant Design Pro, pytest, Vitest.

---

## Current Completion Snapshot

Current pushed baseline: `ff9f6a3 feat: expand lifecycle evidence graph`.

Verified current state after collector-run implementation:

- Backend: `cd apps/api && uv run pytest` -> `140 passed, 1 warning`.
- Frontend: `cd apps/web && npm test` -> `50 passed`.
- Frontend build: `cd apps/web && npm run build` -> success.
- Lint: `cd apps/api && uv run ruff check .` -> success.
- Patch hygiene: `git diff --check` -> success.
- Browser smoke: `http://127.0.0.1:5173/governance/devops` logged in, created `collector_run_002`, marked it `succeeded`, reloaded the page, and confirmed the row persisted with no relevant console errors.

Completed items from `docs/superpowers/plans/2026-06-02-mvp-remaining-closure.md`:

- Task 1 status reconciliation: completed in `3bbdd26`.
- Task 2 Bug lifecycle UI: completed in `5e2ac0e`.
- Task 3 Dashboard v1.2 drilldown: completed in `8cbb818`.
- Task 4 Lifecycle v1.2 evidence expansion: completed in `ff9f6a3`.

Remaining explicit gaps from PRD/spec/test-case:

- External collector run records are absent: no `collector_runs` table, API, tests, or UI.
- Unattributed/pending-attribution data queues are specified but not implemented.
- Production-readiness gates still require real Docker/GitLab/model-provider environment validation.
- Real external collectors and external-system writebacks remain later-stage work; do not implement them in this slice.

## Confirmation Options

The user confirmed option 2 before implementation.

1. Production-readiness audit only: run Docker/GitLab/model-provider gate checks and update docs with evidence.
2. Collector run tracking (Recommended): implement `collector_runs` table, API, persistence, audit, tests, and DevOps page visibility.
3. Pending-attribution queue: implement a queue for imported records that cannot map to product/module/requirement.
4. Real external collectors: connect GitLab/Jenkins/log/usage source collectors. This is larger and should follow option 2.
5. External writeback governance: prepare real external-system writeback controls. This is larger and not required before collector ledgers.

## Task 1: Backend Collector Run Tests

**Files:**

- Create: `apps/api/tests/test_collector_runs.py`
- Inspect: `apps/api/tests/test_devops_gitlab_metrics.py`
- Inspect: `apps/api/tests/test_ops_online_log_metrics.py`
- Inspect: `apps/api/tests/test_usage_metrics.py`

- [x] **Step 1: Add failing API tests**

Add tests that prove:

- `GET /api/collectors/runs` returns a real empty list with `total = 0`.
- `POST /api/collectors/runs` creates a product-scoped run and writes `collector_run.created` audit.
- `PATCH /api/collectors/runs/{run_id}` moves `running -> succeeded` and writes `collector_run.updated`.
- `running -> failed` requires a non-empty `error_message`.
- terminal states `succeeded | failed | cancelled` cannot return to `running`.
- viewer cannot create or update run records.

Minimum test shape:

```python
def test_collector_run_create_patch_filter_and_audit():
    headers = auth_headers()
    product = create_product(headers)

    created = client.post(
        "/api/collectors/runs",
        json={
            "collector_type": "gitlab_daily_code_metric",
            "product_id": product["id"],
            "source_system": "gitlab",
            "status": "running",
            "payload_summary": {"repository_path": "rd/api"},
        },
        headers=headers,
    )
    assert created.status_code == 200
    run = created.json()["data"]
    assert run["id"].startswith("collector_run_")
    assert run["records_imported"] == 0

    patched = client.patch(
        f"/api/collectors/runs/{run['id']}",
        json={"status": "succeeded", "records_imported": 3},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["finished_at"]

    listed = client.get(
        f"/api/collectors/runs?collector_type=gitlab_daily_code_metric&product_id={product['id']}",
        headers=headers,
    ).json()["data"]
    assert listed["total"] == 1

    audit = client.get(
        f"/api/audit/events?subject_type=collector_run&subject_id={run['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert {event["event_type"] for event in audit} == {
        "collector_run.created",
        "collector_run.updated",
    }
```

- [x] **Step 2: Run the failing tests**

Run:

```bash
cd apps/api && uv run pytest tests/test_collector_runs.py
```

Expected before implementation: failures because `/api/collectors/runs` does not exist.

## Task 2: Data Model and Persistence

**Files:**

- Create: `apps/api/app/db/migrations/012_collector_runs.sql`
- Modify: `apps/api/app/core/store.py`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/tests/test_database_persistence.py`

- [x] **Step 1: Add SQL migration**

Create `apps/api/app/db/migrations/012_collector_runs.sql`:

```sql
CREATE TABLE IF NOT EXISTS collector_runs (
  id text PRIMARY KEY,
  collector_type text NOT NULL CHECK (
    collector_type IN (
      'gitlab_daily_code_metric',
      'jenkins_release',
      'online_log_metric',
      'user_usage_metric',
      'user_feedback',
      'iteration_plan_suggestion'
    )
  ),
  product_id text REFERENCES products(id) ON DELETE SET NULL,
  status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'cancelled')),
  source_system text NOT NULL,
  started_at timestamptz NOT NULL,
  finished_at timestamptz,
  records_imported integer NOT NULL DEFAULT 0 CHECK (records_imported >= 0),
  error_message text,
  payload_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_collector_runs_type_started
  ON collector_runs (collector_type, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_collector_runs_product_started
  ON collector_runs (product_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_collector_runs_status
  ON collector_runs (status);
```

- [x] **Step 2: Add store field and persistence constants**

In `apps/api/app/core/store.py`, add:

```python
collector_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
```

Clear it in `reset()`.

In `apps/api/app/core/persistence.py`, add `collector_runs` to `COLLECTION_FIELDS`, add `COLLECTOR_RUN_FIELDS`, add a `CollectorRunRepository` protocol, payload helper, load/save helpers, `has_*`, counter sync for prefix `collector_run`, and context cleanup that drops product-bound runs whose product no longer exists.

- [x] **Step 3: Add PostgreSQL load/save methods**

In `PostgresSnapshotRepository`, add:

```python
def load_collector_runs(self) -> dict[str, Any]:
    with self._connect() as connection:
        with connection.cursor() as cursor:
            runs = self._load_collector_runs(cursor)
    return {"collector_runs": runs}

def save_collector_runs(self, payload: dict[str, Any]) -> None:
    runs = payload.get("collector_runs", {})
    with self._connect() as connection:
        with connection.cursor() as cursor:
            self._delete_missing(cursor, "collector_runs", runs)
            self._upsert_collector_runs(cursor, runs)
```

The row loader must return the same field names as API responses:

```python
{
    "collector_type": row["collector_type"],
    "created_at": row["created_at"].isoformat(),
    "created_by": row["created_by"],
    "error_message": row["error_message"],
    "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
    "id": row["id"],
    "payload_summary": row["payload_summary"] or {},
    "product_id": row["product_id"],
    "records_imported": row["records_imported"],
    "source_system": row["source_system"],
    "started_at": row["started_at"].isoformat(),
    "status": row["status"],
    "updated_at": row["updated_at"].isoformat(),
}
```

- [x] **Step 4: Run persistence tests**

Run:

```bash
cd apps/api && uv run pytest tests/test_database_persistence.py
```

Expected after implementation: existing persistence tests pass, plus a new collector-run persistence test proves counter recovery and reload.

## Task 3: Collector Run API

**Files:**

- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_collector_runs.py`

- [x] **Step 1: Add request models and enums**

Add:

```python
COLLECTOR_TYPES = {
    "gitlab_daily_code_metric",
    "jenkins_release",
    "online_log_metric",
    "user_usage_metric",
    "user_feedback",
    "iteration_plan_suggestion",
}
COLLECTOR_RUN_STATUSES = {"running", "succeeded", "failed", "cancelled"}
COLLECTOR_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


class CollectorRunRequest(BaseModel):
    collector_type: str
    error_message: str | None = None
    payload_summary: dict[str, Any] = Field(default_factory=dict)
    product_id: str | None = None
    records_imported: int = 0
    source_system: str
    started_at: str | None = None
    status: str = "running"


class CollectorRunPatchRequest(BaseModel):
    error_message: str | None = None
    finished_at: str | None = None
    payload_summary: dict[str, Any] | None = None
    records_imported: int | None = None
    status: str | None = None
```

- [x] **Step 2: Add validation helpers**

Rules:

- `collector_type` must be in `COLLECTOR_TYPES`.
- `status` must be in `COLLECTOR_RUN_STATUSES`.
- `records_imported` must be non-negative.
- `source_system` must be non-blank.
- `product_id`, when present, must reference an existing product.
- Failed runs must have non-empty `error_message`.
- `running` can become `succeeded`, `failed`, or `cancelled`.
- Terminal states cannot transition to another status.
- `finished_at` is set automatically when a run enters a terminal status and not provided.

- [x] **Step 3: Add endpoints**

Add:

```http
GET /api/collectors/runs
POST /api/collectors/runs
PATCH /api/collectors/runs/{run_id}
```

Filters for `GET`:

- `collector_type`
- `product_id`
- `status`
- `source_system`

Return shape:

```json
{
  "data": {
    "items": [],
    "total": 0
  },
  "trace_id": "trace_001"
}
```

Use `_require_roles(user, {"admin", "product_owner", "rd_owner"})` for create/update. Read requires the normal authenticated user.

- [x] **Step 4: Run collector run tests**

Run:

```bash
cd apps/api && uv run pytest tests/test_collector_runs.py
cd apps/api && uv run pytest
```

Expected: all backend tests pass.

## Task 4: DevOps Page Visibility

**Files:**

- Modify: `apps/web/src/services/aiBrain.ts`
- Modify: `apps/web/src/pages/Devops/index.tsx`
- Modify: `apps/web/tests/App.test.tsx`

- [x] **Step 1: Add service types and mapping**

Add `CollectorRunRecord`, `CollectorRunCreatePayload`, and `CollectorRunPatchPayload`. Map API fields to UI fields:

- `collector_type` -> `collectorType`
- `source_system` -> `sourceSystem`
- `product_id` -> `productId`
- `records_imported` -> `recordsImported`
- `payload_summary` -> `payloadSummary`
- `started_at` -> `startedAt`
- `finished_at` -> `finishedAt`

Add:

```ts
export async function fetchCollectorRuns(): Promise<CollectorRunRecord[]>
export async function createCollectorRun(payload: CollectorRunCreatePayload): Promise<CollectorRunRecord>
export async function updateCollectorRun(runId: string, payload: CollectorRunPatchPayload): Promise<CollectorRunRecord>
```

- [x] **Step 2: Add DevOps run table**

In `apps/web/src/pages/Devops/index.tsx`, add a second `ManagementListPage` section or a compact table band titled `采集运行记录`. It must:

- load from `/api/collectors/runs`;
- show empty state when there are no records;
- expose `登记采集运行` modal;
- allow `running` rows to be marked `succeeded`, `failed`, or `cancelled`;
- not create GitLab/Jenkins/log/usage metrics automatically.

- [x] **Step 3: Add frontend tests**

Extend `apps/web/tests/App.test.tsx` to prove:

- DevOps page calls `/api/collectors/runs`.
- Empty run list renders without demo rows.
- Creating a run posts to `/api/collectors/runs`.
- Completing a run patches `/api/collectors/runs/{run_id}`.

Run:

```bash
cd apps/web && npm test -- App.test.tsx
```

Expected before implementation: tests fail because the UI and service do not exist.

- [x] **Step 4: Run frontend verification**

Run:

```bash
cd apps/web && npm test
cd apps/web && npm run build
```

Expected: all frontend tests and build pass.

## Task 5: Docs, Browser Smoke, Commit

**Files:**

- Modify: `docs/01-prd/enterprise-ai-brain/prd.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Update docs**

Document:

- `collector_runs` data model.
- `GET/POST/PATCH /api/collectors/runs`.
- audit events `collector_run.created` and `collector_run.updated`.
- collector run records do not create metrics by themselves.
- real external source connectors remain a later-stage integration.

- [x] **Step 2: Browser smoke**

With source services:

- API: `http://127.0.0.1:8000`
- Web: `http://127.0.0.1:5173`

Verify:

- login works;
- open `/governance/devops`;
- create a collector run;
- mark it `succeeded`;
- refresh page and confirm the run persists;
- no placeholder rows appear.

- [x] **Step 3: Final verification**

Run:

```bash
cd apps/api && uv run pytest
cd apps/api && uv run ruff check .
cd apps/web && npm test
cd apps/web && npm run build
git diff --check
```

Expected: all pass.

- [x] **Step 4: Commit and push**

Run:

```bash
git add apps/api/app/core/store.py apps/api/app/core/persistence.py apps/api/app/db/migrations/012_collector_runs.sql apps/api/app/main.py apps/api/tests/test_collector_runs.py apps/api/tests/test_database_persistence.py apps/web/src/services/aiBrain.ts apps/web/src/pages/Devops/index.tsx apps/web/tests/App.test.tsx docs/01-prd/enterprise-ai-brain/prd.md docs/02-specs/enterprise-ai-brain/spec.md docs/02-specs/enterprise-ai-brain/api.md docs/02-specs/enterprise-ai-brain/test-case.md docs/changelog.md
git commit -m "feat: add collector run tracking"
git push origin master
```

## Execution Gate

Per project rule, this plan was executed only after confirmation. Option 2, Collector run tracking, is the implemented slice.
