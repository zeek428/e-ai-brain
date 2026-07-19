# Task 7 review remediation, round 3 report

## Outcome

Production due polling now hydrates every unique predecessor omitted by the
indexed due-candidate scan through one collaboration-run-scoped PostgreSQL
batch query. It no longer performs one `get_rd_work_item` query and connection
per predecessor.

The scheduler accepts only requested rows belonging to the current run, so a
missing predecessor or a predecessor from another run still leaves the
successor in `ready` without creating execution artifacts. MemoryStore and
explicit-`now` behavior, deterministic priority/ID ordering, dispatch limits,
dependency semantics, and retry/backoff behavior are unchanged.

## TDD RED evidence

The batch-hydration regression was added before the production change. Its
repository double exposes the scoped batch method and raises if due polling
uses any per-ID getter. The focused RED run failed at the first predecessor:

```bash
cd apps/api
uv run pytest \
  tests/test_rd_work_item_scheduler.py::test_scheduler_batches_omitted_predecessors_for_repository_due_candidates \
  -q
```

```text
FAILED ... AssertionError: due polling must not perform per-predecessor gets
1 failed in 0.05s
```

After the minimal scheduler and repository change, the same test passed.

## Implementation

- Added `list_rd_work_items_by_ids(collaboration_run_id, work_item_ids)` to the
  collaboration repository contract and PostgreSQL read repository.
- The query uses one array-bound ID predicate together with
  `collaboration_run_id = %s`, and returns rows in deterministic ID order.
- Scheduler hydration deduplicates and sorts omitted predecessor IDs, performs
  one batch call, and independently rejects unrequested or cross-run rows.
- Repository-backed polling has no single-row fallback. An unavailable batch
  capability therefore fails closed rather than reintroducing N+1 queries.
- Added a PostgreSQL dispatch regression for a completed cross-run predecessor;
  the prior missing-row regression remains in the affected suite.

## Verification

Affected scheduler, MemoryStore auto-dispatch, full PostgreSQL work-item
execution, and due-candidate repository coverage:

```bash
cd apps/api
uv run pytest \
  tests/test_rd_work_item_scheduler.py \
  tests/test_rd_collaboration_auto_dispatch.py \
  tests/test_rd_work_item_execution_postgres.py \
  tests/test_rd_collaboration_repository.py::test_repository_lists_only_due_dispatch_candidates_in_plan_priority_id_order \
  -q
```

```text
99 passed in 25.66s
```

Changed-file Ruff lint/format checks and `git diff --check` were also run and
returned no findings.

## Scope

Only scheduler/repository code, focused tests, and this requested report are
included. Existing controller-owned documentation changes in the worktree were
not modified or staged.
