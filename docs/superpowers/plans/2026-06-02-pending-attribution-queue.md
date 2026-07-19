# Pending Attribution Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real database-backed pending attribution queue so imported or collected records that cannot be mapped to product/module/requirement are visible, auditable, and resolvable instead of being dropped, rejected without trace, or counted in product dashboards.

**Architecture:** Keep metric, feedback, and collector-run records in their existing domain tables. Add a separate `pending_attribution_items` business table for unresolved incoming records and expose it through a small API plus DevOps/Insights visibility. Resolving a queue item links it to a real product/module/requirement and optionally records the target business subject that should be created by a later collector adapter; this slice does not implement automatic external collectors or automatic metric creation.

**Tech Stack:** FastAPI, PostgreSQL SQL migrations, in-process `MemoryStore` for tests, React + TypeScript, Ant Design Pro, pytest, Vitest, browser smoke tests on source-run API/Web.

---

## Current Evidence Snapshot

- Current baseline: `fd9e7b1 feat: add collector run tracking`.
- Worktree was clean before this planning document was created.
- PRD requires the R&D operations page to show "待归属数据队列" and AC14/AC20 require unmapped GitLab/user usage/feedback data to enter such a queue.
- Spec module B3/B3.1/B5 states that records which cannot map to product/module must enter a pending attribution queue and not enter product-level dashboard statistics.
- Current code has no `pending_attribution_items` store collection, migration, API, service mapping, or page entry. Existing create endpoints validate product/module context and return validation errors instead of creating a durable queue item.
- Recently implemented `collector_runs` should be reused as optional provenance for queue items, so failed or partial imports can point to the run that produced unmapped records.

## Confirmation Options

The next development slice should be confirmed before implementation.

1. Production-readiness validation only: run Docker/GitLab/model-provider gates and update evidence docs. This does not advance the pending queue.
2. Pending attribution queue (Recommended): implement `pending_attribution_items` table, API, persistence, DevOps page visibility, tests, docs, and browser smoke.
3. Real external collector adapters: connect GitLab/Jenkins/log/usage/feedback ingestion. This should follow option 2 because adapters need a durable place for unmapped records.

## Files

Create:
- `apps/api/app/db/migrations/013_pending_attribution_items.sql`
- `apps/api/tests/test_pending_attribution.py`

Modify:
- `apps/api/app/core/store.py`
- `apps/api/app/core/persistence.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_database_persistence.py`
- `apps/web/src/services/aiBrain.ts`
- `apps/web/src/pages/Devops/index.tsx`
- `apps/web/src/pages/Insights/index.tsx`
- `apps/web/tests/App.test.tsx`
- `docs/01-prd/enterprise-ai-brain/prd.md`
- `docs/02-specs/enterprise-ai-brain/spec.md`
- `docs/02-specs/enterprise-ai-brain/api.md`
- `docs/02-specs/enterprise-ai-brain/test-case.md`
- `docs/changelog.md`

## Data Contract

`pending_attribution_items` records unresolved imported facts, not product metrics.

Allowed `source_type`:

```text
gitlab_daily_code_metric | jenkins_release | online_log_metric | user_usage_metric | user_feedback | iteration_plan_suggestion
```

Allowed `status`:

```text
pending | resolved | ignored
```

Allowed `resolution_action`:

```text
link_existing_context | ignore_as_noise
```

Minimal API shape:

```json
{
  "id": "pending_attr_001",
  "source_type": "user_feedback",
  "source_system": "feedback-api",
  "collector_run_id": "collector_run_001",
  "raw_subject_id": "feedback-ext-42",
  "summary": "Cannot map module code search-v2 to known product module.",
  "raw_payload": {
    "external_product_key": "rd-platform",
    "module_hint": "search-v2",
    "content": "Search returns stale results."
  },
  "suggested_product_id": null,
  "suggested_module_code": "search",
  "confidence": 0.44,
  "status": "pending",
  "resolution_action": null,
  "resolved_product_id": null,
  "resolved_module_code": null,
  "resolved_requirement_id": null,
  "resolved_subject_type": null,
  "resolved_subject_id": null,
  "resolved_by": null,
  "resolved_at": null,
  "created_by": "user_admin",
  "created_at": "2026-06-02T05:30:00Z",
  "updated_at": "2026-06-02T05:30:00Z"
}
```

## Task 1: Backend Red Tests

**Files:**
- Create: `apps/api/tests/test_pending_attribution.py`
- Modify: `apps/api/tests/test_database_persistence.py`

- [ ] **Step 1: Add failing API tests**

Create `apps/api/tests/test_pending_attribution.py` with tests covering empty list, create, resolve, ignore, audit, invalid context, and permissions:

```python
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import auth_headers, create_product

client = TestClient(app)


def test_pending_attribution_items_are_real_empty_lists_without_placeholders():
    headers = auth_headers()

    response = client.get("/api/attribution/pending-items", headers=headers)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body == {"items": [], "total": 0}


def test_pending_attribution_create_resolve_filter_and_audit():
    headers = auth_headers()
    product = create_product(headers)

    created = client.post(
        "/api/attribution/pending-items",
        json={
            "source_type": "user_feedback",
            "source_system": "feedback-api",
            "raw_subject_id": "feedback-ext-42",
            "summary": "Cannot map module search-v2",
            "raw_payload": {"module_hint": "search-v2"},
            "suggested_module_code": "search",
            "confidence": 0.44,
        },
        headers=headers,
    )
    assert created.status_code == 200
    item = created.json()["data"]
    assert item["id"].startswith("pending_attr_")
    assert item["status"] == "pending"
    assert item["resolved_product_id"] is None

    resolved = client.post(
        f"/api/attribution/pending-items/{item['id']}/resolve",
        json={
            "resolution_action": "link_existing_context",
            "resolved_product_id": product["id"],
            "resolved_module_code": "core",
            "resolution_note": "Mapped by product owner",
        },
        headers=headers,
    )
    assert resolved.status_code == 200
    resolved_item = resolved.json()["data"]
    assert resolved_item["status"] == "resolved"
    assert resolved_item["resolved_product_id"] == product["id"]
    assert resolved_item["resolved_by"] == "user_admin"
    assert resolved_item["resolved_at"]

    listed = client.get(
        f"/api/attribution/pending-items?status=resolved&source_type=user_feedback&resolved_product_id={product['id']}",
        headers=headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == item["id"]

    audit = client.get(
        f"/api/audit/events?subject_type=pending_attribution_item&subject_id={item['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert {event["event_type"] for event in audit} == {
        "pending_attribution.created",
        "pending_attribution.resolved",
    }


def test_pending_attribution_ignore_and_state_permissions():
    headers = auth_headers()
    viewer_headers = auth_headers(username="viewer@example.com", password="viewer123")

    forbidden = client.post(
        "/api/attribution/pending-items",
        json={
            "source_type": "gitlab_daily_code_metric",
            "source_system": "gitlab",
            "summary": "Unknown repository",
        },
        headers=viewer_headers,
    )
    assert forbidden.status_code == 403

    created = client.post(
        "/api/attribution/pending-items",
        json={
            "source_type": "gitlab_daily_code_metric",
            "source_system": "gitlab",
            "summary": "Unknown repository",
            "raw_payload": {"repository_path": "unknown/repo"},
        },
        headers=headers,
    ).json()["data"]

    ignored = client.post(
        f"/api/attribution/pending-items/{created['id']}/resolve",
        json={"resolution_action": "ignore_as_noise", "resolution_note": "Test import noise"},
        headers=headers,
    )
    assert ignored.status_code == 200
    assert ignored.json()["data"]["status"] == "ignored"

    second_resolution = client.post(
        f"/api/attribution/pending-items/{created['id']}/resolve",
        json={"resolution_action": "ignore_as_noise"},
        headers=headers,
    )
    assert second_resolution.status_code == 409
    assert second_resolution.json()["detail"]["code"] == "PENDING_ATTRIBUTION_STATE_INVALID"
```

- [ ] **Step 2: Add failing persistence test**

In `apps/api/tests/test_database_persistence.py`, extend the fake repository with `load_pending_attribution` and `save_pending_attribution`, then add:

```python
def test_pending_attribution_items_are_persisted_through_fine_grained_repository_payload():
    repository = FakeRepository()
    store = PersistentMemoryStore.from_repository(repository)
    now = "2026-06-02T05:30:00+00:00"
    store.pending_attribution_items["pending_attr_001"] = {
        "id": "pending_attr_001",
        "source_type": "user_feedback",
        "source_system": "feedback-api",
        "collector_run_id": None,
        "raw_subject_id": "feedback-ext-42",
        "summary": "Cannot map module",
        "raw_payload": {"module_hint": "search-v2"},
        "suggested_product_id": None,
        "suggested_module_code": "search",
        "confidence": 0.44,
        "status": "pending",
        "resolution_action": None,
        "resolution_note": None,
        "resolved_product_id": None,
        "resolved_module_code": None,
        "resolved_requirement_id": None,
        "resolved_subject_type": None,
        "resolved_subject_id": None,
        "resolved_by": None,
        "resolved_at": None,
        "created_by": "user_admin",
        "created_at": now,
        "updated_at": now,
    }

    store.persist()

    assert repository.saved_pending_attribution["pending_attribution_items"]["pending_attr_001"][
        "source_type"
    ] == "user_feedback"
```

- [ ] **Step 3: Run red tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_pending_attribution.py tests/test_database_persistence.py::test_pending_attribution_items_are_persisted_through_fine_grained_repository_payload
```

Expected before implementation: failures because `/api/attribution/pending-items` and store persistence do not exist.

## Task 2: Database and Persistence

**Files:**
- Create: `apps/api/app/db/migrations/013_pending_attribution_items.sql`
- Modify: `apps/api/app/core/store.py`
- Modify: `apps/api/app/core/persistence.py`

- [ ] **Step 1: Add SQL migration**

Create `apps/api/app/db/migrations/013_pending_attribution_items.sql`:

```sql
CREATE TABLE IF NOT EXISTS pending_attribution_items (
  id text PRIMARY KEY,
  source_type text NOT NULL,
  source_system text NOT NULL,
  collector_run_id text REFERENCES collector_runs(id) ON DELETE SET NULL,
  raw_subject_id text,
  summary text NOT NULL,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  suggested_product_id text REFERENCES products(id) ON DELETE SET NULL,
  suggested_module_code text,
  confidence numeric(5,4),
  status text NOT NULL DEFAULT 'pending',
  resolution_action text,
  resolution_note text,
  resolved_product_id text REFERENCES products(id) ON DELETE SET NULL,
  resolved_module_code text,
  resolved_requirement_id text REFERENCES requirements(id) ON DELETE SET NULL,
  resolved_subject_type text,
  resolved_subject_id text,
  resolved_by text REFERENCES users(id) ON DELETE SET NULL,
  resolved_at timestamptz,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_pending_attribution_source_type
    CHECK (
      source_type IN (
        'gitlab_daily_code_metric',
        'jenkins_release',
        'online_log_metric',
        'user_usage_metric',
        'user_feedback',
        'iteration_plan_suggestion'
      )
    ),
  CONSTRAINT ck_pending_attribution_status
    CHECK (status IN ('pending', 'resolved', 'ignored')),
  CONSTRAINT ck_pending_attribution_resolution_action
    CHECK (
      resolution_action IS NULL
      OR resolution_action IN ('link_existing_context', 'ignore_as_noise')
    ),
  CONSTRAINT ck_pending_attribution_source_system
    CHECK (length(trim(source_system)) > 0),
  CONSTRAINT ck_pending_attribution_summary
    CHECK (length(trim(summary)) > 0),
  CONSTRAINT ck_pending_attribution_confidence
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  CONSTRAINT ck_pending_attribution_terminal_resolution
    CHECK (
      (status = 'pending' AND resolved_at IS NULL AND resolved_by IS NULL)
      OR (status IN ('resolved', 'ignored') AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_pending_attribution_status_created
  ON pending_attribution_items (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pending_attribution_source_created
  ON pending_attribution_items (source_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pending_attribution_resolved_product
  ON pending_attribution_items (resolved_product_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_pending_attribution_collector_run
  ON pending_attribution_items (collector_run_id);
```

- [ ] **Step 2: Add store field**

In `apps/api/app/core/store.py`, add:

```python
pending_attribution_items: dict[str, dict[str, Any]] = field(default_factory=dict)
```

and clear it in `reset()`:

```python
self.pending_attribution_items.clear()
```

- [ ] **Step 3: Add persistence helpers**

In `apps/api/app/core/persistence.py`, add `PENDING_ATTRIBUTION_FIELDS = ["pending_attribution_items"]`, include it in `COLLECTION_FIELDS`, add repository load/save helpers mirroring `COLLECTOR_RUN_FIELDS`, sync the `pending_attr` counter, and drop stale context only when referenced products/requirements no longer exist.

Add PostgreSQL methods:

```python
def load_pending_attribution(self) -> dict[str, Any]:
    with self._connect() as connection:
        with connection.cursor() as cursor:
            items = self._load_pending_attribution_items(cursor)
    return {"pending_attribution_items": items}


def save_pending_attribution(self, payload: dict[str, Any]) -> None:
    items = payload.get("pending_attribution_items", {})
    with self._connect() as connection:
        with connection.cursor() as cursor:
            self._delete_missing(cursor, "pending_attribution_items", items)
            self._upsert_pending_attribution_items(cursor, items)
```

- [ ] **Step 4: Run persistence tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_database_persistence.py::test_pending_attribution_items_are_persisted_through_fine_grained_repository_payload
```

Expected after implementation: pass.

## Task 3: Backend API

**Files:**
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_pending_attribution.py`

- [ ] **Step 1: Add request models**

Add:

```python
PENDING_ATTRIBUTION_SOURCE_TYPES = COLLECTOR_TYPES
PENDING_ATTRIBUTION_STATUSES = {"ignored", "pending", "resolved"}
PENDING_ATTRIBUTION_RESOLUTION_ACTIONS = {"ignore_as_noise", "link_existing_context"}


class PendingAttributionRequest(BaseModel):
    collector_run_id: str | None = None
    confidence: float | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    raw_subject_id: str | None = None
    source_system: str
    source_type: str
    suggested_module_code: str | None = None
    suggested_product_id: str | None = None
    summary: str


class PendingAttributionResolveRequest(BaseModel):
    resolution_action: str
    resolution_note: str | None = None
    resolved_module_code: str | None = None
    resolved_product_id: str | None = None
    resolved_requirement_id: str | None = None
    resolved_subject_id: str | None = None
    resolved_subject_type: str | None = None
```

- [ ] **Step 2: Add validation helpers**

Add helpers that:
- require `product_owner`, `rd_owner`, or `admin` for create/resolve;
- validate `source_type`, `status`, `resolution_action`;
- ensure `source_system` and `summary` are non-empty;
- ensure `confidence` is `0..1` when present;
- ensure `collector_run_id` points to an existing collector run when present;
- ensure suggested and resolved product ids point to active products when present;
- ensure resolved module belongs to resolved product when present;
- ensure resolved requirement belongs to resolved product when present;
- forbid resolving an item whose status is no longer `pending`;
- require `resolved_product_id` for `link_existing_context`;
- require no resolved context for `ignore_as_noise`.

- [ ] **Step 3: Add endpoints**

Add:

```http
GET /api/attribution/pending-items
POST /api/attribution/pending-items
POST /api/attribution/pending-items/{item_id}/resolve
```

Sorting:

```python
items.sort(
    key=lambda item: (
        item.get("created_at") or "",
        item.get("updated_at") or "",
        item["id"],
    ),
    reverse=True,
)
```

Audit events:

```text
pending_attribution.created
pending_attribution.resolved
pending_attribution.ignored
```

- [ ] **Step 4: Run backend tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_pending_attribution.py
uv run pytest
uv run ruff check .
```

Expected: all tests and lint pass.

## Task 4: Frontend API and UI

**Files:**
- Modify: `apps/web/src/services/aiBrain.ts`
- Modify: `apps/web/src/pages/Devops/index.tsx`
- Modify: `apps/web/src/pages/Insights/index.tsx`
- Test: `apps/web/tests/App.test.tsx`

- [ ] **Step 1: Add service types and methods**

Add `PendingAttributionItem`, `PendingAttributionCreatePayload`, and `PendingAttributionResolvePayload` in `apps/web/src/services/aiBrain.ts`, plus:

```ts
export async function fetchPendingAttributionItems(): Promise<PendingAttributionItem[]>
export async function createPendingAttributionItem(
  payload: PendingAttributionCreatePayload,
): Promise<PendingAttributionItem>
export async function resolvePendingAttributionItem(
  itemId: string,
  payload: PendingAttributionResolvePayload,
): Promise<PendingAttributionItem>
```

- [ ] **Step 2: Add DevOps table**

In `apps/web/src/pages/Devops/index.tsx`, add a `ProTable` titled `待归属数据队列` below `采集运行记录`.

Columns:
- 队列 ID
- 来源类型
- 来源系统
- 原始主体 ID
- 摘要
- 建议产品
- 建议模块
- 置信度
- 状态
- 创建时间
- 操作

Actions:
- pending item: `归属处理`, opens modal.
- resolved/ignored item: action column shows `-`.

Resolve modal fields:
- 处理方式: `link_existing_context` or `ignore_as_noise`
- 归属产品
- 归属模块
- 关联需求
- 关联主体类型
- 关联主体 ID
- 处理说明

- [ ] **Step 3: Add Insights visibility**

In `apps/web/src/pages/Insights/index.tsx`, add a compact section or tab showing pending attribution items filtered to `user_usage_metric` and `user_feedback` source types. Keep DevOps as the owner of all-source resolution.

- [ ] **Step 4: Add frontend tests**

In `apps/web/tests/App.test.tsx`, add tests that:
- DevOps page loads `/api/attribution/pending-items` and shows real empty state without placeholder rows.
- DevOps page resolves a pending item by posting `resolution_action: "link_existing_context"`.
- DevOps page ignores a pending item by posting `resolution_action: "ignore_as_noise"`.

- [ ] **Step 5: Run frontend verification**

Run:

```bash
cd apps/web
npm test
npm run build
```

Expected: all frontend tests pass and build succeeds.

## Task 5: Docs, SQL Apply, Browser Smoke, Commit

**Files:**
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Update docs**

Document:
- `pending_attribution_items` table and migration `013_pending_attribution_items.sql`;
- API contract for `GET/POST /api/attribution/pending-items` and resolve action;
- DevOps and Insights page behavior;
- no placeholder data and no automatic metric creation;
- audit events and role permissions.

- [x] **Step 2: Apply SQL to existing local DB**

Rebuild/restart the API so its entrypoint applies the migration without clearing
volumes, then verify the table from PostgreSQL:

```bash
docker compose up -d --build api
docker compose exec -T postgres psql -U ai_brain -d ai_brain -c "SELECT to_regclass('public.pending_attribution_items');"
```

Expected: `public.pending_attribution_items`. Application migrations are owned by
the API image/entrypoint for both fresh and existing volumes; PostgreSQL initdb
must not mount or execute `apps/api/app/db/migrations`.

- [x] **Step 3: Browser smoke**

Use source-run API/Web:
- API: `http://127.0.0.1:8000`
- Web: `http://127.0.0.1:5173`

Smoke path:
1. Log in with `admin@example.com / admin123`.
2. Open `/governance/devops`.
3. Confirm `待归属数据队列` renders.
4. Create a pending item through API or page-supported action.
5. Resolve it to an existing product.
6. Reload page and confirm status remains `resolved`.
7. Confirm console has no relevant errors and no placeholder rows are shown.

- [x] **Step 4: Final verification**

Run:

```bash
cd apps/api && uv run pytest
cd apps/api && uv run ruff check .
cd apps/web && npm test
cd apps/web && npm run build
git diff --check
```

Expected:
- backend test count increases from 140;
- frontend test count increases from 50;
- build succeeds;
- diff check succeeds.

- [x] **Step 5: Commit and push**

Run:

```bash
git add apps/api/app/core/store.py apps/api/app/core/persistence.py apps/api/app/main.py apps/api/app/db/migrations/013_pending_attribution_items.sql apps/api/tests/test_pending_attribution.py apps/api/tests/test_database_persistence.py apps/web/src/services/aiBrain.ts apps/web/src/pages/Devops/index.tsx apps/web/src/pages/Insights/index.tsx apps/web/tests/App.test.tsx docs/01-prd/enterprise-ai-brain/prd.md docs/02-specs/enterprise-ai-brain/spec.md docs/02-specs/enterprise-ai-brain/api.md docs/02-specs/enterprise-ai-brain/test-case.md docs/changelog.md docs/superpowers/plans/2026-06-02-pending-attribution-queue.md
git commit -m "feat: add pending attribution queue"
git push origin master
```

## Self-Review

- Spec coverage: This plan covers PRD page requirement 9, AC14, AC20, spec B3/B3.1/B5 pending attribution rules, API additions, database persistence, audit, DevOps/Insights visibility, SQL migration, tests, browser smoke, and commit/push.
- Boundary preserved: This plan does not implement real external collectors, automatic metric creation, or real external writeback. It only gives those future adapters a durable queue for unmapped records.
- No demo data: Empty API responses remain `items: []` and `total: 0`; frontend must not create placeholder rows.
- Confirmation status: Executed after user confirmed option 2 on 2026-06-02.
