# Task 6 review fixes report

## Outcome

Both P1 findings against `6f2465d9c` are fixed.

- Generic Runner approval endpoints now reject records whose frozen
  `approval_request.source` is `rd_collaboration_work_item` with the stable,
  bounded error `RD_COLLABORATION_APPROVAL_DECISION_REQUIRED`. The dedicated
  approval-request endpoint and the plugin-action approval endpoint both fence
  the record before any approval, action, audit, or repository write. Generic
  non-RD Runner approvals retain their existing behavior.
- An expired approved collaboration snapshot now creates a distinct immutable
  renewal record for the same not-yet-created attempt. The first renewal uses
  `rd-runner-safety:<work-item-id>:attempt:<attempt-no>:renewal:1`; the renewal
  number is also frozen in the approval request. Decision, collaboration event,
  audit event, command record, and idempotency identities use the same suffix,
  so restart/concurrent replay is deterministic and does not collide with the
  historical gate.
- Dispatch selects the latest contiguous approval identity. Before renewed
  approval, it creates no AI task, Runner task, work-item attempt, context
  manifest, Agent Loop record, or budget ledger. After the frozen decision
  approves the renewal, the bounded one-hour snapshot passes Runner safety and
  attempt 1 dispatches with only the renewal approval attached.

The original expired approval record remains unchanged. PostgreSQL remains the
production source of truth; the existing MemoryStore fallback is used only by
test fixtures.

## Atomicity and safety

The renewal gate reuses the existing idempotent PostgreSQL command transaction:
the pending approval request, frozen decision, work-item pause, collaboration
event, and audit event commit together. The frozen decision transaction already
updates the approval request, decision, and work item together for approval or
rejection. Generic endpoints now stop before either collaboration approval state
transition can occur.

Renewal durable evidence contains only stable IDs, attempt/renewal numbers,
blocked-operation codes, policy version, actor IDs, and bounded timestamps. The
tests assert that customer tokens, prompts/instructions, and workspace paths do
not appear in approval records, decisions, events, audits, or worker outcomes.

## TDD RED evidence

Before production changes:

```bash
cd apps/api
uv run pytest \
  tests/test_plugin_management.py::test_generic_ai_executor_approval_rejects_rd_collaboration_gate \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_expired_runner_safety_approval_renews_without_dispatch_artifacts -q
```

Result: exit code 1, `2 failed in 0.84s`.

- Generic approval returned HTTP 200 instead of the required 409 fence.
- The expired approval path produced no `:renewal:1` record.

The plugin-action bypass test was then added with its production fence removed:

```bash
uv run pytest \
  tests/test_plugin_management.py::test_plugin_action_approval_cannot_bypass_rd_collaboration_gate -q
```

Result: exit code 1, `1 failed in 0.33s`; the bypass returned HTTP 200.

## GREEN and regression evidence

Focused P1 tests:

```bash
uv run pytest \
  tests/test_plugin_management.py::test_generic_ai_executor_approval_rejects_rd_collaboration_gate \
  tests/test_rd_work_item_execution_postgres.py::test_postgres_expired_runner_safety_approval_renews_without_dispatch_artifacts -q
```

Result: `2 passed in 0.80s`.

Generic fences and existing non-RD Runner behavior:

```bash
uv run pytest tests/test_plugin_management.py -q
```

Result: `73 passed in 1.55s`.

Collaboration dispatch, PostgreSQL work-item execution, command transaction,
MemoryStore production-usage audit, and delivery regressions:

```bash
uv run pytest \
  tests/test_rd_collaboration_auto_dispatch.py \
  tests/test_rd_work_item_execution_postgres.py \
  tests/test_rd_collaboration_command_transactions.py \
  tests/test_memory_store_usage_audit.py \
  tests/test_rd_collaboration_delivery.py -q
```

Result: `75 passed in 15.79s`.

Repository decision regressions:

```bash
uv run pytest \
  tests/test_rd_collaboration_repository.py \
  tests/test_rd_collaboration_repository_hardening.py \
  -k 'decision and not assessment' -q
```

Result: `11 passed, 74 deselected in 3.15s`.

Static checks:

```bash
uv run ruff check \
  app/services/ai_executor_runner_approvals.py \
  app/services/rd_dispatch_fault_decision.py \
  app/services/task_start_execution.py \
  tests/test_plugin_management.py \
  tests/test_rd_work_item_execution_postgres.py
git diff --check
```

Result: `All checks passed!`; diff check exited 0.

## Scope

Changed production code and tests only, plus this required evidence report.
Controller-owned documentation and changelog changes already present in the
worktree were not modified or included.
