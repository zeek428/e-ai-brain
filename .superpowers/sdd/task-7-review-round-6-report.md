# Task 7 review remediation, round 6 report

## Outcome

Automatic PostgreSQL dispatch now carries the durable candidate reservation's
work-item version and due-time observation through to the final execution
bundle. The bundle locks the work item and enforces both bindings before any
task, Runner, attempt, event, or audit artifact can be committed.

If another worker records retry backoff after the candidate was reserved, the
stale worker receives a version/reservation conflict and reports the candidate
as skipped. It cannot dispatch early or clear the newer retry count, safe error
code, or `next_dispatch_at`. Direct Task 6 dispatch remains compatible: callers
without an automatic reservation continue to use the command's existing
current-version compare-and-set and Runner-safety approval fences.

No migration was required because the binding uses the existing durable work
item `version` and `next_dispatch_at` fields.

## TDD evidence

The real PostgreSQL two-worker regression was added before production changes:

```bash
cd apps/api
uv run pytest \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_stale_reserved_worker_cannot_bypass_new_retry_backoff \
  -q
```

RED result: `1 failed`. Worker B reserved version N and paused at a barrier;
worker A then recorded retry backoff as version N+1. After release, worker B
incorrectly dispatched the work item, so the expected empty dispatched-ID list
contained the work-item ID.

GREEN result after the binding/fence change: `1 passed in 0.42s`.

The regression also proves that:

- worker A's retry result remains durable across reconstructed
  `PostgresRuntimeStore` instances;
- worker B returns the candidate in `skipped_work_item_ids` without surfacing a
  thread error;
- no task, Runner task, execution context, loop, budget, or attempt artifact is
  visible before the due time;
- the retry fields remain byte-for-byte unchanged through the stale execution
  and an early restarted sweep;
- a restarted sweep at the exact due time dispatches successfully and only
  then clears the retry fields.

## Implementation

- Durable reservation polling now uses one explicit UTC observation timestamp
  for both candidate selection and execution authorization.
- Reserved candidate pages pass their exact row version and observation time
  into `dispatch_ai_task_for_work_item`; MemoryStore and non-reservation callers
  receive no new arguments.
- The PostgreSQL execution bundle checks the locked row's exact reserved
  version and due state, and repeats both predicates on the final atomic work
  item update that clears retry state.
- `RD_VERSION_CONFLICT` and `RD_DISPATCH_RESERVATION_STALE` are treated as stale
  automatic candidates, preserving retry counts and cursor continuation rather
  than recording another fault.
- Fair global/per-run cursor reservation and the Task 6 Runner approval proof,
  expiry revalidation, capacity, and transaction fences are unchanged.

## Verification

Focused retry, Runner-safety, and fair-reservation gate:

```text
19 passed, 95 deselected in 5.56s
```

Full backend suite:

```text
1628 passed, 4 skipped, 1 deselected in 90.22s
```

Changed-file Ruff lint passed, and Ruff formatting reports all six changed
Python files formatted. Scoped `git diff --check` returned no findings.

## Scope

This commit contains only Task 7 code, the PostgreSQL regression, and this
report. Existing controller-owned changelog and planning/specification files in
the worktree were not modified or staged.
