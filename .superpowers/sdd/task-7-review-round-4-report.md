# Task 7 review remediation, round 4 report

## Outcome

Automatic R&D dispatch now applies one absolute, deterministic candidate scan
budget equal to the dispatch sweep `limit`. The remaining budget is threaded
into the PostgreSQL due-candidate query, and dependency predecessor hydration
is restricted to the candidates returned by that bounded page.

Every examined due row consumes the global sweep budget, including rows that
are dependency-blocked, non-AI-owned, deferred, escalated, retryable, or
otherwise skipped. A low dispatch limit therefore cannot scan or hydrate an
entire large run merely to fill the successful-dispatch count.

## TDD RED evidence

The regression was added before the production change. It exposes 100 due
successors with 100 distinct predecessors through a repository double and
dispatches with `limit=2`:

```bash
cd apps/api
uv run pytest \
  tests/test_rd_collaboration_auto_dispatch.py::test_auto_dispatch_bounds_repository_candidate_and_predecessor_scans \
  -q
```

The RED run failed because the repository recorded `limit=None` instead of
`limit=2`; the pre-fix scheduler also passed all 100 predecessor IDs to the
hydration batch.

After the minimal implementation, the same command passed. The regression
also places a non-AI row first, proving that examined rows consume the scan
budget even when they do not create a dispatch outcome. Only the second row is
dispatched, while the repository receives one two-row candidate page and one
two-ID predecessor batch.

## Implementation

- Added a bounded `ready_work_item_page` scheduler primitive that returns the
  dependency-ready rows, a priority/ID keyset cursor, and the exact number of
  due candidates examined.
- Automatic dispatch maintains one global examined-row counter across sorted
  collaboration runs and passes only the remaining sweep budget into each
  repository scan.
- PostgreSQL due scans accept `limit`, `after`, and an optional deterministic
  `due_at`, use priority/ID keyset ordering for paged dispatch, and retain the
  legacy plan/priority/ID ordering for unpaged direct repository callers.
- Predecessor hydration remains one run-scoped batch and now contains only the
  unique omitted predecessors for the bounded candidate page.
- MemoryStore uses the same due-status, retry-time, priority/ID, and absolute
  scan-budget rules. Explicit `now` calls pass the normalized timestamp into
  PostgreSQL, preserving deterministic direct-now behavior.

Dispatch, defer, escalation, human-review, retry, and stale-skip handling are
unchanged for candidates inside the sweep budget. Missing and cross-run
predecessors continue to fail closed.

## Verification

Affected scheduler, MemoryStore dispatch, full PostgreSQL work-item execution,
and due-candidate repository coverage:

```bash
cd apps/api
uv run pytest \
  tests/test_rd_work_item_scheduler.py \
  tests/test_rd_collaboration_auto_dispatch.py \
  tests/test_rd_work_item_execution_postgres.py \
  tests/test_rd_collaboration_repository.py::test_repository_lists_only_due_dispatch_candidates_in_plan_priority_id_order \
  -q
```

Result: `100 passed in 25.54s`.

Changed-file Ruff lint and format checks passed. `git diff --check` also
returned no findings.

## Scope

Only the dispatcher, scheduler, collaboration repository contract and read
repository, focused regression, and this requested report are included. The
controller-owned changelog and untracked planning/specification files in the
worktree were not modified or staged.
