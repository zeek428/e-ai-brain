# Task 7 review remediation, round 2 report

## Outcome

The PostgreSQL automatic dispatcher now preserves the indexed due-candidate
scan while resolving dependency predecessors from durable repository rows.
A due successor whose predecessor is completed is dispatched; a predecessor
that is waiting for a human or missing from durable state keeps the successor
ready and creates no execution artifacts.

MemoryStore behavior and explicit `now` scheduling continue to use the full
in-scope work-item collection. Candidate ordering, dispatcher limits, due-time
filtering, and retry/backoff behavior are unchanged.

## TDD RED evidence

The PostgreSQL auto-dispatch regressions were added before the production
change. The focused run produced `1 failed, 2 passed`:

```bash
cd apps/api
uv run pytest \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_auto_dispatches_due_successor_after_completed_predecessor \
  'tests/test_rd_work_item_execution_postgres.py::test_postgres_auto_dispatch_keeps_successor_ready_without_completed_predecessor[waiting]' \
  'tests/test_rd_work_item_execution_postgres.py::test_postgres_auto_dispatch_keeps_successor_ready_without_completed_predecessor[missing]' \
  -q
```

The completed-predecessor case expected the successor ID but received an empty
dispatch list. Both fail-closed controls already remained undispatched.

## Implementation

- `ready_work_items` retains `list_due_rd_work_items` as the production
  candidate source.
- Dependency evaluation builds a separate status map and loads only unique
  predecessor IDs omitted from the candidate scan through
  `get_rd_work_item`.
- Loaded predecessors must belong to the same collaboration run. Missing or
  cross-run rows are not accepted as satisfied dependencies.
- Candidate iteration and final priority/ID sorting remain unchanged.

## Verification

Focused GREEN run after implementation:

```text
3 passed in 0.92s
```

Scheduler and MemoryStore automatic-dispatch regression suites:

```text
29 passed in 0.03s
```

PostgreSQL due-query, retry/backoff, successful retry reset, and new dependency
cases:

```text
6 passed in 1.83s
```

Full PostgreSQL work-item execution module:

```text
67 passed in 24.83s
```

Changed-file Ruff checks, format checks, and `git diff --check` were run before
commit. The final combined affected-suite gate reported `96 passed in 24.93s`,
`All checks passed!`, and `2 files already formatted`; `git diff --check`
returned no findings.

## Scope

Only scheduler code, focused PostgreSQL tests, and this requested report are
included. Existing controller documentation changes in the worktree were not
modified or staged.
