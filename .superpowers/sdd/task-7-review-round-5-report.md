# Task 7 review remediation, round 5 report

## Outcome

Automatic R&D dispatch now retains one absolute examined-candidate budget per
sweep while durably continuing after previously examined work and rotating
across collaboration runs. PostgreSQL reserves the bounded page and advances
the global/per-run cursors in one transaction under a locked singleton row, so
restarts and concurrent workers cannot reset or race the scan position.

Dependency retrieval is successor-scoped before predecessor hydration. A page
of `N` candidates issues one run-scoped dependency query containing only those
successor IDs, rather than loading the run's complete dependency graph.

Migration 124 adds the durable cursor tables and a partial page index ordered
by run, normalized due time, normalized priority, and ID. PostgreSQL first
selects at most the remaining budget in that index order, then the service
processes only the bounded page in deterministic priority/ID order.

## TDD evidence

The first focused RED run contained two expected failures:

- the scheduler called the run-wide dependency reader instead of the new
  successor-scoped reader;
- a second `limit=1` sweep restarted at the same blocked row instead of
  reaching the next run.

The PostgreSQL RED run then failed because
`reserve_due_rd_dispatch_candidates` and migration 124 did not yet exist.

After the implementation, the focused scheduler, dispatch, PostgreSQL work
item execution, repository, migration, restart/concurrency, and plan tests
passed:

```bash
cd apps/api
uv run pytest \
  tests/test_rd_work_item_scheduler.py \
  tests/test_rd_collaboration_auto_dispatch.py \
  tests/test_rd_work_item_execution_postgres.py \
  tests/test_rd_collaboration_repository.py::test_repository_lists_only_due_dispatch_candidates_in_plan_priority_id_order \
  tests/test_rd_collaboration_repository.py::test_repository_priority_sorts_only_within_the_bounded_due_page \
  tests/test_rd_collaboration_repository.py::test_repository_reserves_fair_dispatch_pages_across_restart_and_workers \
  tests/test_rd_collaboration_repository.py::test_due_dispatch_page_uses_bounded_due_index_before_priority_sort \
  tests/test_requirement_driven_rd_schema_postgres.py::test_migration_123_adds_durable_dispatch_retry_controls \
  tests/test_requirement_driven_rd_schema_postgres.py::test_migration_124_adds_durable_dispatch_cursor_and_page_index \
  -q
```

Result before the final added capacity-continuation case: `107 passed in
27.43s`. The capacity regression also passed independently.

## Correctness and performance details

- Every reserved row consumes the sweep budget, including dependency-blocked,
  non-AI, deferred, retryable, and stale rows.
- A persisted global run cursor gives later runs the next turn; a persisted
  due-time/priority/ID cursor continues within each run. Exhausted cursors wrap
  once, so newly inserted earlier rows are eventually revisited.
- Cursor reservation is serialized in PostgreSQL. Execution authorization and
  writes remain owned by the existing compare-and-set/idempotent dispatch
  command, preserving the Task 6 safety fences and retry behavior.
- Missing or cross-run predecessors remain absent from the run-scoped
  hydration result and therefore fail closed.
- The large-run regression inserts 10,000 candidates and runs `EXPLAIN
  (ANALYZE, BUFFERS, FORMAT JSON)` against the exact production page SQL. It
  asserts `idx_rd_work_items_dispatch_due_page` feeds the `Limit`, with 10
  actual index rows and 10 actual limit rows.
- MemoryStore follows the same absolute budget, due-order cursor, wrap, and
  run-rotation semantics. It is test-only and still materializes all matching
  fixture rows before its in-process bounded sort; no claim is made that it
  avoids fixture materialization.

## Verification

Full backend suite:

```bash
cd apps/api
uv run pytest -q
```

Result: `1627 passed, 4 skipped, 1 deselected in 89.79s`.

Changed-file Ruff lint and format checks passed. `git diff --check` returned no
findings.

## Scope

This commit contains only the dispatch repository/contract/service changes,
migration 124, focused regressions, and this report. Controller-owned changelog
and planning/specification files already present in the worktree were not
modified or staged.
