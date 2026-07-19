# Task 6 review remediation, round 4 report

## Outcome

Both review-round-4 P1 findings against `9b41da494` are fixed.

- The final PostgreSQL work-item execution bundle now treats approved safety
  status, approval-gated execution permission, top-level approval presence,
  nested approval assertions, and supplied collaboration provenance as safety
  claims. These claims fail closed unless they resolve to one reserved
  work-item/attempt/renewal identity with exact locked approval-request and
  decision provenance.
- Arbitrary or nonreserved approval IDs no longer bypass the final mutation
  boundary. The normalized nested `ai_executor_safety.approval` must exactly
  equal the canonical approved snapshot, including its empty validation
  results; added, removed, or changed fields are rejected.
- The bundle retains the locked canonical approval identity and checks
  `expires_at > clock_timestamp()` again after audit persistence, the final
  execution-artifact write. Expiry during a later write raises the stable
  `RD_DECISION_REQUIRED` error and rolls back the entire transaction.
- Valid low-risk dispatch, initial safety approval dispatch, and renewal
  approval dispatch remain supported.

## TDD RED evidence

The PostgreSQL regressions were added before production changes:

```bash
cd apps/api
uv run pytest tests/test_rd_work_item_execution_postgres.py \
  -k 'fails_closed_for_every_runner_safety_claim or approval_expires_during_late_bundle_write' -q
```

Result: exit code 1, `6 failed, 33 deselected`.

- Approved status, approval-gated `execution_allowed`, nonreserved top-level
  approval, nonreserved nested approval, and a mutated canonical nested
  approval all committed instead of failing closed.
- An approval expiring after the late audit write committed the bundle instead
  of rolling it back.

## GREEN and regression evidence

The new final-boundary regressions passed:

```bash
uv run pytest tests/test_rd_work_item_execution_postgres.py \
  -k 'fails_closed_for_every_runner_safety_claim or approval_expires_during_late_bundle_write' -q
```

Result: `6 passed, 33 deselected`.

The broader Runner-safety gate passed, covering valid initial and renewal
dispatches plus the pre-existing mutation and lock-wait races:

```bash
uv run pytest tests/test_rd_work_item_execution_postgres.py -k runner_safety -q
```

Result: `14 passed, 25 deselected`.

Adjacent PostgreSQL work-item, transaction, auto-dispatch, and plugin approval
tests passed:

```bash
uv run pytest \
  tests/test_rd_work_item_execution_postgres.py \
  tests/test_rd_collaboration_command_transactions.py \
  tests/test_rd_collaboration_auto_dispatch.py \
  tests/test_plugin_management.py -q
```

Result: `151 passed`.

Static checks and the full backend suite passed:

```bash
uv run ruff format --check \
  app/core/repositories/rd_collaboration_work_writes.py \
  tests/test_rd_work_item_execution_postgres.py
uv run ruff check \
  app/core/repositories/rd_collaboration_work_writes.py \
  tests/test_rd_work_item_execution_postgres.py
uv run pytest -q
```

Results: `2 files already formatted`; `All checks passed!`;
`1581 passed, 4 skipped, 1 deselected`.

The late-write regression captures every bundle identity, pauses after the
audit insert until wall-clock expiry, and verifies rollback of the AI task,
Runner task, work-item attempt and its idempotency key, context manifest,
Agent Loop run/iterations, budget ledger, collaboration event, audit events,
and work-item state.

## Scope

Changed backend code and tests only, plus this required report. Existing
controller-owned changelog, plan, and design changes were preserved and are
excluded from this remediation commit.
