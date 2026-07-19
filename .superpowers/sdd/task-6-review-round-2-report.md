# Task 6 review remediation, round 2 report

## Outcome

Both P1 findings against `9c8ea4185` are fixed.

- Generic approval handling recognizes the exact reserved identity family
  `rd-runner-safety:<work-item>:attempt:<n>[:renewal:<n>]` independently of
  caller-supplied `source`. The approval-request endpoint, plugin-action
  endpoint, generic pending-request helper, and generic mark-approved helper
  all fail with the bounded
  `RD_COLLABORATION_APPROVAL_DECISION_REQUIRED` response before mutating
  collaboration-owned state.
- PostgreSQL generic approval persistence now uses one transaction for the
  approval request, optional plugin action, and audit events. Its approval-row
  `INSERT ... ON CONFLICT DO UPDATE` condition rejects both reserved IDs and
  rows whose persisted or incoming request source is
  `rd_collaboration_work_item`. A collaboration request committed after an
  earlier service check therefore causes the whole generic bundle to roll
  back, including the plugin action and audits.
- Collaboration approval and dispatch validate deterministic work-item,
  attempt, and renewal identity; authentic source; policy version; exact
  blocked operations; exact decision ID, type, subject, selected option,
  recommendation, and evidence; and the canonical hash of the frozen option
  set. The decision transaction performs the same provenance checks before it
  can approve or reject the request.
- Renewal decisions now include the renewal number in their safe frozen
  evidence. A valid renewal remains transactionally approvable and dispatches
  attempt 1 with only its bounded approval snapshot.

PostgreSQL remains the production source of truth. Memory-store updates occur
only in the test fallback or after a successful repository transaction. Error
responses and durable evidence contain stable IDs/codes/metadata only; no
prompt, token, workspace path, or exception detail was added.

## TDD RED evidence

The tests were written before production changes. After correcting test setup
only, the focused command was:

```bash
cd apps/api
uv run pytest \
  tests/test_plugin_management.py::test_generic_approval_rejects_reserved_rd_identity_without_source \
  tests/test_plugin_management.py::test_plugin_action_approval_cannot_preseed_reserved_rd_identity_without_source \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_dispatch_rejects_preseeded_reserved_approval_without_frozen_decision \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_plugin_approval_rechecks_collaboration_source_at_final_mutation -q
```

Result: exit code 1, `5 failed`.

- Both source-less public generic approval calls returned HTTP 200.
- Both crafted approved PostgreSQL records dispatched without a frozen
  decision (one omitted source; one claimed collaboration source).
- The simulated post-check collaboration insert reached generic mutation
  rather than returning the collaboration-decision fence.

## GREEN and regression evidence

The same focused command after implementation produced:

```text
5 passed in 1.04s
```

Generic non-RD approval plus valid initial/renewal decision and dispatch
checks:

```bash
uv run pytest tests/test_plugin_management.py -k 'approval' -q
uv run pytest tests/test_rd_collaboration_auto_dispatch.py -k 'runner_safety' -q
uv run pytest tests/test_rd_work_item_execution_postgres.py -k 'runner_safety' -q
```

Results: `5 passed, 70 deselected`; `3 passed, 13 deselected`; and
`4 passed, 22 deselected`.

Broader adjacent gate:

```bash
uv run ruff format --check \
  app/core/persistence.py \
  app/core/repositories/plugins.py \
  app/core/repositories/rd_collaboration_work_writes.py \
  app/services/ai_executor_runner_approvals.py \
  app/services/rd_collaboration_decisions.py \
  app/services/rd_dispatch_fault_decision.py \
  app/services/task_start_execution.py \
  tests/test_plugin_management.py \
  tests/test_rd_work_item_execution_postgres.py
uv run ruff check <same files>
uv run pytest \
  tests/test_plugin_management.py \
  tests/test_rd_collaboration_auto_dispatch.py \
  tests/test_rd_work_item_execution_postgres.py \
  tests/test_rd_collaboration_command_transactions.py \
  tests/test_memory_store_usage_audit.py -q
```

Results: `9 files already formatted`; `All checks passed!`; and
`142 passed in 16.11s`.

Repository decision regression gate:

```bash
uv run pytest \
  tests/test_rd_collaboration_repository.py \
  tests/test_rd_collaboration_repository_hardening.py \
  -k 'decision and not assessment' -q
git diff --check
```

Results: `11 passed, 74 deselected in 2.80s`; diff check exited 0.

## Scope

Changed backend code and tests only, plus this required report. Existing
controller-owned `docs/changelog.md`, plan, and design changes were preserved
and are excluded from this remediation commit.
