# Task 6 review remediation, round 3 report

## Outcome

Both review-round-3 findings against `fb7096b4c` are fixed.

- PostgreSQL work-item dispatch now carries the frozen Runner-safety approval
  request and decision from preflight into the execution bundle. The bundle
  locks the work item, frozen decision, and canonical approval request in one
  transaction before persisting the AI task, Runner task, attempt, execution
  context, Agent Loop, budget ledger, event, or audits.
- Final mutation revalidates the reserved approval identity; work-item,
  attempt, and renewal binding; authentic collaboration source; Runner and
  executor binding; exact approval-request snapshot; exact blocked operations;
  exact frozen evidence, options, option hash, and recommendation; approved
  decision and selected option; exact canonical approval snapshot; and current
  expiry using PostgreSQL wall-clock time.
- A Runner task that claims a reserved collaboration safety approval without
  both canonical provenance records now fails closed with the stable bounded
  `RD_DECISION_REQUIRED` error. Expired or mutated provenance between preflight
  and final persistence rolls back the whole execution bundle.
- Runner-safety recommendation validation now requires the complete canonical
  object at memory decision resolution, PostgreSQL decision resolution,
  preflight dispatch, and final PostgreSQL dispatch. Missing or modified
  `action` and unexpected fields are rejected.

Valid initial and renewal approval flows remain dispatchable. Error responses
and durable evidence contain only stable safety metadata; no prompt, token,
workspace path, or exception detail was added.

## TDD RED evidence

The first focused PostgreSQL tests were written before the production changes:

```bash
cd apps/api
uv run pytest tests/test_rd_work_item_execution_postgres.py \
  -k 'full_canonical_recommendation or reserved_approval_claim_without_provenance or revalidates_approval_expiry_after_preflight_before_commit' -q
```

Result: exit code 1, `5 failed, 26 deselected`.

- Three crafted recommendation variants were wrongly approved: missing
  `action`, modified `action`, and an unexpected field.
- A reserved Runner approval claim without bundle provenance persisted.
- An approval expired between preflight and final persistence still committed
  the execution bundle.

The stronger row-lock expiry regression was then added before changing the
database-time predicate:

```bash
uv run pytest \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_dispatch_rejects_approval_that_expires_while_waiting_for_its_row_lock -q
```

Result: exit code 1, `1 failed`. Transaction-scoped `now()` remained earlier
than an approval that expired while dispatch waited on its PostgreSQL row lock,
so the invalid bundle committed.

## GREEN and regression evidence

The expanded focused provenance and interleaving gate passed:

```bash
uv run pytest tests/test_rd_work_item_execution_postgres.py \
  -k 'full_canonical_recommendation or reserved_approval_claim_without_provenance or revalidates_runner_safety_after_preflight_before_commit' -q
```

Result: `6 passed, 26 deselected`.

The real PostgreSQL lock-wait expiry regression passed after using database
wall-clock time at final validation:

```bash
uv run pytest \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_dispatch_rejects_approval_that_expires_while_waiting_for_its_row_lock -q
```

Result: `1 passed`.

Valid initial approval, valid renewal, rejection, crafted-record fences, and
the new final-commit regressions all passed:

```bash
uv run pytest tests/test_rd_work_item_execution_postgres.py -k 'runner_safety' -q
```

Result: `9 passed, 24 deselected`.

Adjacent work-item, command-transaction, auto-dispatch, and plugin approval
tests passed:

```bash
uv run pytest \
  tests/test_rd_work_item_execution_postgres.py \
  tests/test_rd_collaboration_command_transactions.py \
  tests/test_rd_collaboration_auto_dispatch.py \
  tests/test_plugin_management.py -q
```

Result before the final added lock-wait case: `143 passed`.

Final static and full backend verification:

```bash
uv run ruff format --check \
  app/core/persistence_contracts.py \
  app/core/repositories/rd_collaboration_shared.py \
  app/core/repositories/rd_collaboration_work_writes.py \
  app/services/rd_collaboration_decisions.py \
  app/services/rd_dispatch_fault_decision.py \
  app/services/task_start_execution.py \
  tests/test_rd_collaboration_command_transactions.py \
  tests/test_rd_work_item_execution_postgres.py
uv run ruff check <same files>
uv run pytest -q
git diff --check
```

Results: `8 files already formatted`; `All checks passed!`;
`1575 passed, 4 skipped, 1 deselected`; and diff check exited 0.

## Scope

Changed backend code and tests only, plus this required report. Existing
controller-owned changelog, plan, and design changes were preserved and are
excluded from this remediation commit.
