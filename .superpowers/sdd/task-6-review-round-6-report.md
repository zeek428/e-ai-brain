# Task 6 review remediation, round 6 report

## Outcome

The review-round-6 P1 finding against `c52dafe82` is fixed.

- The final PostgreSQL work-item execution transaction now recomputes the
  Runner safety snapshot with the production `runner_task_safety_snapshot`
  helper from the exact `runner_task.instruction` and `request_config` received
  by the bundle.
- The claimed safety snapshot must recursively and type-strictly equal that
  recomputed snapshot before provenance-free low-risk execution is allowed. A
  canonical low-risk snapshot attached to `Run git push` therefore fails
  closed.
- Locked approval-request and decision provenance, canonical approval
  snapshots, safety approval claims, options, evidence, recommendation, and
  blocked-operation lists now use recursive type-strict comparison. Python's
  numeric/boolean equality can no longer make a forged nested approval field
  equal canonical PostgreSQL evidence.
- Canonical low-risk, initial-approval, and renewal-approval dispatches remain
  valid.

## TDD RED evidence

The two direct PostgreSQL bundle regressions were added before the production
change and run independently.

```bash
cd apps/api
uv run pytest \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_dispatch_bundle_rejects_low_risk_snapshot_grafted_onto_high_risk_instruction \
  -vv
```

Result: exit code 1. The bundle accepted the low-risk snapshot grafted onto
`Run git push`; pytest reported `Failed: DID NOT RAISE`.

```bash
uv run pytest \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_dispatch_bundle_rejects_type_coerced_nested_approval_proof \
  -vv
```

Result: exit code 1. The bundle accepted forged nested approval evidence under
Python equality; pytest reported `Failed: DID NOT RAISE`.

After strengthening the nested regression to change canonical
`approval.approved` from boolean `true` to integer `1`, removing only the new
strict provenance comparison reproduced the same RED failure. Restoring the
strict comparison returned the regression to GREEN.

## GREEN and regression evidence

The required rejection paths and preserved valid paths passed together:

```bash
uv run pytest tests/test_rd_work_item_execution_postgres.py \
  -k 'directly_accepts_exact_canonical_low_risk_snapshot or directly_accepts_canonical_initial_approval_proof or directly_accepts_canonical_renewal_approval_proof or grafted_onto_high_risk_instruction or type_coerced_nested_approval_proof' \
  -vv
```

Result: `5 passed, 56 deselected`.

The full in-memory and PostgreSQL work-item execution suites passed:

```bash
uv run pytest \
  tests/test_rd_work_item_execution.py \
  tests/test_rd_work_item_execution_postgres.py -q
```

Result: `72 passed`.

Static checks and the full backend suite passed:

```bash
uv run ruff check \
  app/core/repositories/rd_collaboration_work_writes.py \
  tests/test_rd_work_item_execution_postgres.py
uv run ruff format --check \
  app/core/repositories/rd_collaboration_work_writes.py \
  tests/test_rd_work_item_execution_postgres.py
uv run pytest -q
```

Results: `All checks passed!`; `2 files already formatted`;
`1603 passed, 4 skipped, 1 deselected`.

Both rejecting direct-bundle regressions verify that the work item remains
`ready` and that attempts, AI tasks, Runner tasks, context manifests, Agent
Loop records, Agent Loop iterations, and budget ledgers remain absent. This
proves the final transaction rolls back without partial artifacts.

## Scope

Changed backend code and tests only, plus this required report. Existing
controller-owned changelog, plan, and design changes were preserved and are
excluded from this remediation commit.
