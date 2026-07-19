# Task 6 review remediation, round 5 report

## Outcome

The review-round-5 P1 finding against `9b1bbe2f1` is fixed.

- The final PostgreSQL work-item execution bundle now uses a strict positive
  allowlist for provenance-free Runner execution. The complete safety snapshot
  must exactly match the canonical low-risk `not_required` snapshot, including
  keys, nested values, list contents, and scalar types.
- Canonical matching also requires the absence of a top-level
  `ai_executor_approval` claim. Supplying collaboration provenance with the
  no-approval snapshot remains invalid.
- Every noncanonical snapshot now enters the existing locked collaboration
  approval proof path. Missing, malformed, blocked, approval-related,
  execution-disallowed, and unknown shapes therefore raise
  `RD_DECISION_REQUIRED` before any execution artifact is written.
- Existing canonical initial and renewal approval paths continue to validate
  their exact locked approval-request and decision provenance.

## TDD RED evidence

Direct PostgreSQL bundle regressions were added before the production change:

```bash
cd apps/api
uv run pytest tests/test_rd_work_item_execution_postgres.py \
  -k 'dispatch_bundle_directly' -q
```

Result: exit code 1, `15 failed, 5 passed, 39 deselected`.

- The canonical high-risk blocked snapshot emitted by
  `runner_task_safety_snapshot` committed without collaboration provenance.
- Falsey or malformed top-level fields, including `approval`,
  `approval_request`, `blocked_operations`, `execution_allowed`, `findings`,
  `policy_version`, `required_action`, and `risk_level`, committed instead of
  failing closed.
- Falsey or malformed nested approval fields, including `approved`,
  `approved_operations`, `invalid_reasons`, `missing_fields`,
  `missing_operations`, and `mode`, committed instead of failing closed.
- The exact canonical low-risk snapshot and canonical approved initial and
  renewal paths already passed, establishing the required non-regressions.

## GREEN and regression evidence

The direct final-boundary suite passed after the allowlist change:

```bash
uv run pytest tests/test_rd_work_item_execution_postgres.py \
  -k 'dispatch_bundle_directly' -q
```

Result: `20 passed, 39 deselected`.

The full PostgreSQL work-item execution regression file passed:

```bash
uv run pytest tests/test_rd_work_item_execution_postgres.py -q
```

Result: `59 passed`.

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
`1601 passed, 4 skipped, 1 deselected`.

Each rejecting direct-bundle regression verifies that the work item stays
`ready` and that attempts, AI tasks, Runner tasks, context manifests, Agent
Loop records, and budget ledgers remain absent, preserving transaction rollback
guarantees.

## Scope

Changed backend code and tests only, plus this required report. Existing
controller-owned changelog, plan, and design changes were preserved and are
excluded from this remediation commit.
