# P1 Parallel Conflict and Capacity Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Complete the P1 R&D-collaboration scope by preventing conflicting parallel writes and by dispatching AI work only while its frozen run seat has capacity.

**Architecture:** Work-item plans carry explicit repository-scoped write claims. A deterministic analyzer finds unordered write collisions, records evidence, and adds a stable finish-to-start dependency so a collision cannot run concurrently. Every run seat freezes capacity from its unified policy binding; dispatch locks the seat and checks capacity in the same PostgreSQL transaction that creates the task, attempt, Runner row, event, and audit records. The version overview exposes the result without creating another delivery entry point.

**Tech Stack:** FastAPI, PostgreSQL, Python 3.11, React + TypeScript, Vitest, pytest.

## Global Constraints

- LLMs may propose file/resource claims, but platform code decides collisions, dependency edges, capacity, state transitions, and external dispatch.
- Runs, policy snapshots, seats, work items, dependencies, and evidence stay immutable after persistence.
- The default endpoint remains `ready_for_release`; this work must not create, trigger, or run deployments.
- Existing scheduled-job definitions, scheduling, Agent/Skill snapshots, and runtime semantics remain unchanged.
- PostgreSQL is the durable source of truth; `MemoryStore` support exists only for tests.
- Tests must be written and observed failing before each production behavior is added.

---

### Task 1: Deterministic P1 parallel resource-conflict analysis

**Files:**
- Create: `apps/api/app/services/rd_parallel_conflicts.py`
- Modify: `apps/api/app/services/rd_collaboration_planning.py`
- Test: `apps/api/tests/test_rd_parallel_conflicts.py`
- Test: `apps/api/tests/test_rd_collaboration_plan_generation.py`

**Interfaces:**
- Consumes: proposed `work_items[]`, required non-empty `resource_claims[]` for code-mutating `implementation` items, and `dependencies[]`.
- Produces: `analyze_parallel_resource_conflicts(proposal) -> dict[str, Any]` with canonical work items, collision evidence, and deterministic `finish_to_start` serialization dependencies.
- Persists: `input_contract.resource_claims` and `release_conditions.parallel_resource_conflicts`.

- [x] **Step 1: Write the failing tests**

```python
def test_parallel_write_claims_are_serialized_deterministically() -> None:
    result = analyze_parallel_resource_conflicts({
        "work_items": [
            {"id": "a", "priority": 20, "resource_claims": [{"repository_id": "repo", "path": "src/api/users.py", "mode": "write"}]},
            {"id": "b", "priority": 10, "resource_claims": [{"repository_id": "repo", "path": "src/api", "mode": "write"}]},
        ],
        "dependencies": [],
    })
    assert result["dependencies"] == [{
        "predecessor_work_item_id": "b",
        "successor_work_item_id": "a",
        "dependency_type": "finish_to_start",
        "source": "parallel_resource_conflict",
    }]
    assert result["parallel_resource_conflicts"][0]["repository_id"] == "repo"


def test_ordered_or_read_only_claims_do_not_add_a_serialization_edge() -> None:
    result = analyze_parallel_resource_conflicts({
        "work_items": [
            {"id": "a", "resource_claims": [{"repository_id": "repo", "path": "src/a.py", "mode": "read"}]},
            {"id": "b", "resource_claims": [{"repository_id": "repo", "path": "src/a.py", "mode": "write"}]},
        ],
        "dependencies": [],
    })
    assert result["dependencies"] == []
    assert result["parallel_resource_conflicts"] == []
```

- [x] **Step 2: Run the tests and verify RED**

Run: `cd apps/api && uv run pytest tests/test_rd_parallel_conflicts.py -q`

Expected: import failure for `rd_parallel_conflicts` because the analyzer does not exist.

- [x] **Step 3: Add the minimal deterministic analyzer**

```python
def analyze_parallel_resource_conflicts(proposal: dict[str, Any]) -> dict[str, Any]:
    """Canonicalise explicit claims and serialize only unordered write collisions."""
    # reject empty, absolute, and parent-traversal paths
    # compute transitive reachability from supplied dependencies
    # collisions require same repository, at least one write, and equal/prefix paths
    # choose predecessor by (priority, id), add one canonical finish-to-start edge
```

Require every `implementation` item to declare at least one repository-scoped write claim; missing claims reject the model plan before persistence. Call the analyzer before `validate_work_item_plan()`. Merge non-duplicate generated edges, rerun DAG validation, and store the canonical claims plus collision evidence in the durable JSON contracts.

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `cd apps/api && uv run pytest tests/test_rd_parallel_conflicts.py tests/test_rd_collaboration_plan_generation.py -q`

Expected: selected tests pass, including generated plans that store collision evidence and serialized dependencies.

- [x] **Step 5: Commit the isolated behavior**

```bash
git add apps/api/app/services/rd_parallel_conflicts.py apps/api/app/services/rd_collaboration_planning.py apps/api/tests/test_rd_parallel_conflicts.py apps/api/tests/test_rd_collaboration_plan_generation.py
git commit -m "feat: serialize conflicting rd work items"
```

### Task 2: Freeze seat capacity and enforce it atomically at dispatch

**Files:**
- Modify: `apps/api/app/services/rd_policy_validation.py`
- Modify: `apps/api/app/services/rd_collaboration_planning.py`
- Modify: `apps/api/app/services/task_start_execution.py`
- Modify: `apps/api/app/core/repositories/rd_collaboration_work_writes.py`
- Modify: `apps/api/app/services/rd_collaboration_auto_dispatch.py`
- Test: `apps/api/tests/test_rd_collaboration_auto_dispatch.py`
- Test: `apps/api/tests/test_rd_work_item_execution_postgres.py`

**Interfaces:**
- Consumes: `role_bindings[].capacity`, default `1`, bounded to a positive integer.
- Produces: immutable `rd_run_seats.capacity` and `RD_SEAT_CAPACITY_EXHAUSTED` when that seat already owns capacity-count running items.
- Produces: `capacity_deferred_work_item_ids` from automatic dispatch, distinct from errors and high-risk approvals.

- [x] **Step 1: Write the failing tests**

```python
def test_auto_dispatch_defers_a_ready_ai_item_when_frozen_seat_is_full() -> None:
    store = seeded_store_with_two_ready_ai_items(seat_capacity=1)
    result = dispatch_ready_ai_work_items(store)
    assert result["dispatched_work_item_ids"] == ["work-first"]
    assert result["capacity_deferred_work_item_ids"] == ["work-second"]
    assert store.rd_work_items["work-second"]["status"] == "ready"


def test_postgres_dispatch_capacity_check_is_atomic() -> None:
    repository, ids = seeded_postgres_run_with_two_ready_items(seat_capacity=1)
    dispatch(ids["first"])
    with pytest.raises(RdCollaborationRepositoryError, match="RD_SEAT_CAPACITY_EXHAUSTED"):
        dispatch(ids["second"])
    assert repository.get_rd_work_item(ids["second"])["status"] == "ready"
```

- [x] **Step 2: Run the tests and verify RED**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_auto_dispatch.py tests/test_rd_work_item_execution_postgres.py -q`

Expected: the current dispatcher starts both ready items because it ignores frozen seat capacity.

- [x] **Step 3: Add validation and an atomic guard**

```python
# policy validation
capacity = binding.get("capacity", 1)
if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
    raise PolicyValidationError("RD_EXECUTION_POLICY_INVALID", "role_bindings.capacity must be a positive integer")
binding["capacity"] = capacity

# inside the existing dispatch transaction
cursor.execute("SELECT * FROM rd_run_seats WHERE id = %s FOR UPDATE", (work_item["owner_seat_id"],))
seat = _row_dict(cursor, cursor.fetchone())
cursor.execute("SELECT count(*) FROM rd_work_items WHERE owner_seat_id = %s AND status = 'running'", (seat["id"],))
if int(cursor.fetchone()[0]) >= int(seat["capacity"]):
    raise RdCollaborationRepositoryError("RD_SEAT_CAPACITY_EXHAUSTED", "frozen run seat is at capacity")
```

Use the same predicate in the test-only MemoryStore path. A capacity defer preserves `ready` and retries later; awaiting review does not consume executor capacity.

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_auto_dispatch.py tests/test_rd_work_item_execution_postgres.py tests/test_rd_policy_validation.py -q`

Expected: selected tests pass, the transaction preserves the second item as `ready`, and capacity two permits two items.

- [x] **Step 5: Commit the isolated behavior**

```bash
git add apps/api/app/services/rd_policy_validation.py apps/api/app/services/rd_collaboration_planning.py apps/api/app/services/task_start_execution.py apps/api/app/core/repositories/rd_collaboration_work_writes.py apps/api/app/services/rd_collaboration_auto_dispatch.py apps/api/tests/test_rd_collaboration_auto_dispatch.py apps/api/tests/test_rd_work_item_execution_postgres.py
git commit -m "feat: enforce rd collaboration seat capacity"
```

### Task 3: Expose P1 evidence and align documentation

**Files:**
- Modify: `apps/api/app/services/product_version_rd_collaboration_overview.py`
- Modify: `apps/api/app/core/product_version_dashboard_read_model.py`
- Modify: `apps/web/src/services/productVersionDashboardClient.ts`
- Modify: `apps/web/src/pages/IterationVersions/components/VersionDashboardCollaborationPanel.tsx`
- Test: `apps/web/tests/VersionDashboardCollaborationPanel.test.tsx`
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/api/delivery-and-tasks.md`
- Modify: `docs/08-help/delivery.md`
- Modify: `docs/superpowers/specs/2026-07-16-requirement-driven-rd-collaboration-design.md`
- Modify: `docs/changelog.md`

**Interfaces:** dashboard `rd_collaboration.capacity = { frozen, used, available }` and `parallel_conflict_count`; no deployment action is added.

- [x] **Step 1: Write the failing UI test**

```tsx
it('shows frozen capacity and serialized-conflict evidence in the version overview', () => {
  render(<VersionDashboardCollaborationPanel overview={{
    ...activeOverview,
    capacity: { frozen: 2, used: 1, available: 1 },
    parallelConflictCount: 1,
  }} onAction={vi.fn()} />);
  expect(screen.getByText('可用 AI 席位：1 / 2')).toBeInTheDocument();
  expect(screen.getByText('已串行化资源冲突：1')).toBeInTheDocument();
});
```

- [x] **Step 2: Run the test and verify RED**

Run: `cd apps/web && npm test -- --run tests/VersionDashboardCollaborationPanel.test.tsx`

Expected: new capacity/conflict text is absent.

- [x] **Step 3: Implement the read model and panel**

Aggregate frozen seat capacity and `running` occupancy from the active run, count stored conflict annotations, and render the values in the existing total-overview collaboration panel. Do not add a second start form or deployment button.

- [x] **Step 4: Update documentation**

Describe P1 resource claims, deterministic collision serialization, frozen capacity and safe retry. Replace the contradictory P2 classification in the design document, while leaving cross-repository optimisation and calendar/team-pool selection as later scope.

- [x] **Step 5: Run focused tests and verify GREEN**

Run: `cd apps/web && npm test -- --run tests/VersionDashboardCollaborationPanel.test.tsx tests/IterationVersionsPage.test.tsx && npm run lint && npm run typecheck && npm run help:check:strict`

Expected: all commands exit 0.

### Task 4: Completion verification and delivery

**Files:**
- Modify: `docs/08-help/assets/screenshots/help-rd-collaboration.png` (real local UI screenshot only)

- [x] **Step 1: Run the backend P0/P1 suite**

Run: `cd apps/api && uv run pytest -q && uv run ruff check app/services/rd_parallel_conflicts.py app/services/rd_collaboration_planning.py app/services/rd_collaboration_auto_dispatch.py app/services/task_start_execution.py app/core/repositories/rd_collaboration_work_writes.py`

Expected: suite and lint exit 0.

- [x] **Step 2: Validate the local UI**

Open `http://127.0.0.1:5173/delivery/versions` with a product-scoped administrator. Open a version's “总览” and verify its collaboration summary, start/continue/restart, capacity/conflict evidence, and absence of deployment action or browser-console error. Capture a masked real local screenshot.

- [x] **Step 3: Final checks, commit, and push**

```bash
git diff --check
git add -A
git commit -m "feat: complete p1 rd collaboration scheduling"
git push origin codex/rd-collaboration-v2
```

## Self-Review

- **Spec coverage:** Task 1 provides collision detection and serialization. Task 2 freezes and atomically enforces capacity. Task 3 presents the evidence and removes the P1/P2 contradiction. Task 4 verifies the full branch, real UI, documentation, and remote delivery.
- **Placeholder scan:** No production behavior is deferred to an unspecified task.
- **Type consistency:** `resource_claims`, `parallel_resource_conflicts`, `capacity`, and `capacity_deferred_work_item_ids` are named consistently across code, tests, API, UI, and docs.
