# Task 7 P2 review fixes report

## Outcome

Both P2 review findings against `6f8db6d33` are fixed.

- `RdCollaborationReadRepository.list_due_rd_work_items` now performs the migration-123-aligned PostgreSQL candidate scan. It filters to `ready` and `rework_required`, compares `next_dispatch_at` to `CURRENT_TIMESTAMP`, and retains deterministic `plan_version`, `priority`, and `id` ordering. The scheduler still performs dependency checks after loading those candidates.
- Normal production auto-dispatch polling now reaches that repository query; explicit `now` values remain a deterministic test seam. MemoryStore callers and explicit scheduler callers normalize naive datetimes to UTC before due comparisons.

## TDD RED evidence

Before production changes:

```bash
cd apps/api
uv run pytest tests/test_rd_work_item_scheduler.py::test_scheduler_normalizes_naive_now_to_utc_for_memory_store_due_checks tests/test_rd_work_item_scheduler.py::test_scheduler_uses_repository_due_candidates_before_dependency_checks -q
```

Result: `2 failed in 0.05s`.

- The MemoryStore case raised `TypeError: can't compare offset-naive and offset-aware datetimes`.
- The scheduler ignored a repository exposing only the due-candidate query and returned no candidate.

The repository behavior test was then added before its implementation; its first execution failed because `list_due_rd_work_items` did not exist.

## GREEN and regression evidence

```bash
cd apps/api
uv run pytest tests/test_rd_work_item_scheduler.py::test_scheduler_normalizes_naive_now_to_utc_for_memory_store_due_checks tests/test_rd_work_item_scheduler.py::test_scheduler_uses_repository_due_candidates_before_dependency_checks tests/test_rd_collaboration_repository.py::test_repository_lists_only_due_dispatch_candidates_in_plan_priority_id_order -q
```

Result: `3 passed in 0.35s`.

```bash
uv run pytest tests/test_rd_work_item_scheduler.py tests/test_rd_collaboration_auto_dispatch.py -q
```

Result: `29 passed in 0.03s`.

```bash
uv run pytest tests/test_rd_work_item_execution_postgres.py::test_postgres_auto_dispatch_persists_backoff_across_restarts_and_escalates_fourth_fault tests/test_rd_work_item_execution_postgres.py::test_postgres_successful_dispatch_atomically_clears_retry_state tests/test_rd_collaboration_repository.py::test_repository_lists_only_due_dispatch_candidates_in_plan_priority_id_order -q
```

Result: `3 passed in 0.88s`.

```bash
uv run --group dev ruff check app/core/repositories/rd_collaboration.py app/services/rd_work_item_scheduler.py app/services/rd_collaboration_auto_dispatch.py tests/test_rd_work_item_scheduler.py tests/test_rd_collaboration_repository.py
uv run --group dev ruff format --check app/core/repositories/rd_collaboration.py app/services/rd_work_item_scheduler.py app/services/rd_collaboration_auto_dispatch.py tests/test_rd_work_item_scheduler.py tests/test_rd_collaboration_repository.py
git diff --check
```

Result: all checks passed.

## Scope

Changed repository, scheduler, auto-dispatch, and focused tests only, plus this requested report. Existing controller documentation/changelog changes in the worktree were not modified or included.
