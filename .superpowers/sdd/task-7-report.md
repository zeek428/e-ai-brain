# Task 7 Report: Durable dispatch retry backoff

## Outcome

- Added migration 123 with nonnegative retry count, nullable safe error code,
  nullable due timestamp, and a partial due-scan index for ready/rework work.
- Retryable automatic-dispatch faults now update the locked, still-dispatchable
  work item with a stable safe code and 5/10/20-second backoff.
- The fourth consecutive retryable fault atomically pauses the exact item and
  creates one deterministic frozen `dispatch_fault_resolution` decision.
- Successful MemoryStore and PostgreSQL dispatches clear all retry fields in
  the same work-item transition.
- Future-due items are omitted by the scheduler, while capacity deferrals and
  existing permanent/high-risk/Runner-approval paths remain distinct.

## RED evidence

1. `uv run pytest tests/test_rd_collaboration_auto_dispatch.py -q`
   - Result: `4 failed, 16 passed`.
   - Expected failure: the dispatcher had no deterministic time input and no
     durable retry scheduling, threshold escalation, stale-candidate guard, or
     successful-dispatch clear behavior.
2. `uv run pytest tests/test_requirement_driven_rd_schema_postgres.py::test_migration_123_adds_durable_dispatch_retry_controls -q`
   - Result: `1 failed` with missing
     `123_rd_dispatch_retry_controls.sql`.
3. Focused MemoryStore/PostgreSQL threshold selector test.
   - Result: `1 failed, 1 passed` because the MemoryStore escalation did not
     preserve the frozen reviewer-seat selector.

## GREEN evidence

1. Focused behavior and PostgreSQL integration:
   - `uv run pytest tests/test_rd_collaboration_auto_dispatch.py tests/test_rd_work_item_scheduler.py tests/test_rd_work_item_execution_postgres.py tests/test_requirement_driven_rd_schema_postgres.py -q`
   - Result: `141 passed in 36.41s`.
2. Full backend suite:
   - `uv run pytest -q`
   - Result: `1611 passed, 4 skipped, 1 deselected in 86.93s`.
3. Static and formatting checks for all changed Python files:
   - `uv run ruff check ...`
   - Result: `All checks passed!`
   - `uv run ruff format --check ...`
   - Result: `10 files already formatted`.

## Safety evidence

- MemoryStore and PostgreSQL tests inject secret-bearing exception details and
  prove they are absent from durable work-item/decision/event state and the
  dispatcher result.
- Restart coverage reconstructs `PostgresRuntimeStore` between failures and
  proves the durable due time suppresses early retries.
- Stale-candidate tests change status/version before retry recording and prove
  the retry fields remain untouched.
- Fourth-failure decision identity is deterministic, and repeated sweeps do
  not create a second decision.
