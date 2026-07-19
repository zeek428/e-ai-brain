# R&D Collaboration Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make R&D collaboration dispatch atomic, actionable on permanent
faults, strict about implementation write intent, and bounded during decision
creation.

**Architecture:** Build dispatch-only execution artifacts without performing
repository writes, then persist them with the work-item state transition in
one PostgreSQL transaction.  Keep temporary retry outcomes separate from
configuration faults, which pause only their work item and create a frozen
human decision.  Validate plan claims and sweep capacity deterministically
before state changes.

**Tech Stack:** FastAPI, Python 3.11, PostgreSQL, pytest, React/TypeScript
validation tooling.

## Global Constraints

- Production R&D state is PostgreSQL-owned; `MemoryStore` is test-only.
- A collaboration AI task can only be created by internal work-item dispatch.
- High-impact or unrecoverable automation must stop at an explicit human
  decision; P0 must still stop at `ready_for_release` and never deploy.
- All related state, audit events, and idempotency records must commit
  atomically; no retry may create duplicate task, Runner, Agent Loop, or
  budget side effects.
- Frontend/API-visible behavior requires automated and real-browser validation
  before commit.

---

### Task 1: Make dispatch preparation transaction-safe

**Files:**
- Modify: `apps/api/app/services/task_start_execution.py`
- Modify: `apps/api/app/services/rd_task_executor_policies.py`
- Modify: `apps/api/app/services/execution_context_manifests.py`
- Modify: `apps/api/app/services/agent_autonomy.py`
- Modify: `apps/api/app/core/repositories/rd_collaboration_work_writes.py`
- Test: `apps/api/tests/test_rd_work_item_execution_postgres.py`

- [x] Write failing PostgreSQL regressions for a Runner insert failure and a
  concurrent autonomous dispatch.  Assert no execution-context manifest,
  Agent Loop run/iteration, or `agent_budget_ledger` remains for the losing or
  rolled-back task id.
- [x] Run the focused tests and verify the old implementation leaves orphaned
  durable records.
- [x] Extract pure builders for context manifests, Agent Loop bundles, and
  budget records; pass their records into `dispatch_work_item_execution_bundle`
  and upsert them with task, Runner, attempt, event, and audit writes.
- [x] Run the focused tests until they pass, then run the work-item execution
  PostgreSQL test module.

### Task 2: Escalate permanent dispatch faults to humans

**Files:**
- Modify: `apps/api/app/services/rd_collaboration_auto_dispatch.py`
- Modify: `apps/api/app/services/rd_high_risk_dispatch_gate.py` or a focused
  dispatch-fault decision service
- Modify: `apps/api/app/core/repositories/rd_collaboration_work_writes.py`
- Modify: `apps/api/app/workers/execution_worker.py`
- Test: `apps/api/tests/test_rd_collaboration_auto_dispatch.py`
- Test: `apps/api/tests/test_rd_work_item_execution_postgres.py`

- [x] Write failing tests showing a frozen role/snapshot/configuration fault
  pauses the work item, creates one replay-safe human decision, and records a
  classified worker outcome; capacity exhaustion stays `ready` and deferred.
- [x] Run the focused tests and verify permanent faults are currently only
  returned as `skipped`.
- [x] Implement the error classifier and transactional pause/decision command;
  make worker heartbeat counters retain deferred, escalated, and retryable
  outcomes without exposing secrets.
- [x] Run focused MemoryStore and PostgreSQL tests until green.

### Task 3: Enforce write intent and total sweep quota

**Files:**
- Modify: `apps/api/app/services/rd_parallel_conflicts.py`
- Modify: `apps/api/app/services/rd_collaboration_auto_dispatch.py`
- Test: `apps/api/tests/test_rd_parallel_conflicts.py`
- Test: `apps/api/tests/test_rd_collaboration_auto_dispatch.py`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-cases/requirements-and-tasks.md`

- [x] Write failing tests that reject an `implementation` item whose claims
  are all `read`, and prove that a dispatch sweep with a low limit processes no
  more than that many combined dispatch, defer, or decision outcomes.
- [x] Run the focused tests and verify both tests fail against the prior logic.
- [x] Require `any(mode == "write")` for implementation claims and account for
  every examined dispatch candidate before creating a high-risk decision.
- [x] Run focused tests until green and update the source-of-truth spec and
  acceptance case wording.

### Task 4: Verify, document, and deliver

**完成状态（2026-07-19）**：实现、聚焦后端回归和源规格同步已完成；变更不影响前端路由、可见文案、表单或操作流，因此无需更新帮助内容或截图。`docs/changelog.md` 的归并以及最终提交/推送仍由控制任务负责，本子任务不修改或提交它们。

**Files:**
- Modify: `docs/changelog.md`
- Review: `docs/08-help/README.md`

- [x] 运行覆盖派发原子性、审批、退避、候选分页和公平续扫的聚焦后端回归；验证入口见本计划末尾“完成实现与验证依据”。
- [x] 评审帮助中心：本轮无用户可见页面或操作变化，`docs/08-help/README.md` 无需调整。
- [x] 由控制任务合并 `docs/changelog.md`、执行完整前端/浏览器门禁，并完成最终 diff、提交和推送。

### Task 5: Remove transient audit collection from dispatch preparation

**Files:**
- Modify: `apps/api/app/services/rd_task_executor_policies.py`
- Modify: `apps/api/app/services/ai_executor_task_creation.py`
- Modify: `apps/api/app/services/execution_context_manifests.py`
- Test: `apps/api/tests/test_memory_store_usage_audit.py`
- Test: `apps/api/tests/test_rd_work_item_execution_postgres.py`

- [x] Add a failing DB-first audit regression proving that autonomous dispatch
  creates its full durable audit bundle without reading `current_store.audit_events`.
- [x] Return generated audit records directly from manifest, Agent Loop, and
  Runner-task builders; pass their explicit bundle to the existing dispatch
  transaction and remove the transient-store scan.
- [x] Prove rollback still leaves no task, Runner, manifest, Agent Loop,
  budget, or audit record, then run the MemoryStore audit gate.

### Task 6: Close Runner high-risk approval in collaboration dispatch

**Files:**
- Modify: `apps/api/app/services/rd_dispatch_fault_decision.py`
- Modify: `apps/api/app/services/rd_collaboration_auto_dispatch.py`
- Modify: `apps/api/app/services/rd_collaboration_decisions.py`
- Modify: `apps/api/app/services/task_start_execution.py`
- Modify: `apps/api/app/services/rd_task_executor_policies.py`
- Modify: `apps/api/app/core/repositories/rd_collaboration*.py`
- Test: `apps/api/tests/test_rd_collaboration_auto_dispatch.py`
- Test: `apps/api/tests/test_rd_work_item_execution_postgres.py`

- [x] Add failing PostgreSQL tests for an `AI_EXECUTOR_APPROVAL_REQUIRED`
  dispatch: it must pause one item, persist one approval request and one
  decision, and not create a Runner task or attempt.
- [x] On approval, write a bounded immutable approval snapshot covering every
  blocked operation, resume the original work-item state, and permit the next
  dispatch; reject still cancels. Repeated sweeps/restarts must reuse the same
  request identity.
- [x] Keep decision evidence and worker outcome free of workspace paths,
  prompts, tokens, and credentials; run focused MemoryStore and PostgreSQL
  coverage.

### Task 7: Persist retry backoff and threshold escalation

**Files:**
- Create: `apps/api/app/db/migrations/123_rd_dispatch_retry_controls.sql`
- Modify: `apps/api/app/services/rd_collaboration_auto_dispatch.py`
- Modify: `apps/api/app/services/rd_work_item_scheduler.py`
- Modify: `apps/api/app/core/repositories/rd_collaboration*.py`
- Test: `apps/api/tests/test_rd_collaboration_auto_dispatch.py`
- Test: `apps/api/tests/test_rd_work_item_execution_postgres.py`

- [x] Add a failing test that a retryable fault records only its safe code,
  increases failure count, and suppresses dispatch before `next_dispatch_at`.
- [x] Apply 5/10/20-second backoff, clear retry state after successful
  dispatch, and pause/escalate on the fourth consecutive retryable fault.
- [x] Add an index for due retry scans and verify that no raw exception detail
  is durable or returned by Worker observability.

### Task 8: Fence startup migrations and parent-run dispatch races

**Files:**
- Modify: `docker-compose.yml`
- Modify: `infra/docker/api-entrypoint.sh`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/repositories/rd_collaboration_work_writes.py`
- Test: `apps/api/tests/test_docker_migration_boundary.py`
- Test: `apps/api/tests/test_api_entrypoint.py`
- Test: `apps/api/tests/test_persistence_repository_boundaries.py`
- Test: `apps/api/tests/test_rd_work_item_execution_postgres.py`

- [x] Prove the ordinary API entrypoint executes normal additive migrations but
  excludes explicit cleanup migration 121 and large dispatch-index migrations
  125-128.
- [x] Remove the application-migration bind mount from PostgreSQL initdb so a
  fresh volume cannot execute a second migration path. Prove the PostgreSQL
  image contains no application SQL while the API image packages the entrypoint
  default migration path.
- [x] Delegate 125-128 to the non-test API repository compatibility path. Use
  an autocommit connection, one non-blocking PostgreSQL advisory lock, catalog
  validity/readiness checks, and concurrent drop/create; a second startup must
  skip immediately rather than wait for the lock holder.
- [x] In the final dispatch bundle transaction, use an initial non-locking
  parent-ID lookup, then the canonical `rd_collaboration_runs -> rd_work_items`
  row-lock order and post-lock ownership/status/version/due revalidation before
  any execution artifacts are committed. Prove concurrent cancel/suspension
  produces neither SQLSTATE `40P01` nor task, Runner, attempt, event, or audit
  artifacts from a stale reservation.

## 完成实现与验证依据

- **Task 4**：源规格和验收覆盖已同步到 `spec.md` 与
  `test-cases/requirements-and-tasks.md`；本轮不改 UI，帮助中心评审结果为
  无需刷新说明或截图。控制任务已合并 changelog，并完成完整前端/浏览器门禁；
  最终提交和推送作为本计划交付的一部分执行。
- **Task 5**：提交 `af8616938` 将清单、Agent Loop 和 Runner 构造器产生的
  审计记录显式汇入派发 bundle；`d2d37e974` 的事务边界保证任一写入失败回滚。
  验证引用：`test_postgres_dispatch_rolls_back_task_runner_attempt_event_and_audit_together`、
  `test_postgres_autonomous_dispatch_persists_explicit_audit_bundle_without_reading_store_audits`
  与 `test_memory_store_usage_audit.py`。
- **Task 6**：提交 `6f2465d9c`、`9c8ea4185`、`fb7096b4c`、`9b41da494`、
  `c52dafe82` 与 `171c687ee` 完成协作专用 Runner 安全决策、过期续签、通用
  审批围栏、不可变快照和最终事务重验。验证引用：
  `test_postgres_runner_safety_approval_is_atomic_replay_safe_and_dispatchable`、
  `test_postgres_expired_runner_safety_approval_renews_without_dispatch_artifacts`、
  `test_postgres_dispatch_rejects_approval_that_expires_while_waiting_for_its_row_lock`、
  `test_postgres_dispatch_bundle_fails_closed_for_every_runner_safety_claim`。
- **Task 7**：提交 `6f8db6d33` 写入安全退避状态和到期索引；`402e6fa42`、
  `c9587c992`、`adcb2753f`、`6569f638e`、`b86c2dfa6`、`698a86c47` 补齐到期
  候选、批量依赖、有界扫描、可恢复公平游标和 reservation version/due 绑定。
  验证引用：`test_auto_dispatch_persists_safe_retry_backoff_and_suppresses_early_retry`、
  `test_postgres_successful_dispatch_atomically_clears_retry_state`、
  `test_postgres_stale_reserved_worker_cannot_bypass_new_retry_backoff`、
  `test_repository_reserves_fair_dispatch_pages_across_restart_and_workers` 与
  `test_scheduler_batches_omitted_predecessors_for_repository_due_candidates`。
- **Task 8**：提交 `e775507e9` 将四个派发大索引迁移改为 advisory-locked
  concurrent compatibility 路径，提交 `48e82eda2` 让普通 API 启动明确排除
  121/125-128 并在最终派发重验父运行；`4623ddc13` 将最终事务锁序统一为
  `rd_collaboration_runs -> rd_work_items` 并补齐锁后归属/状态/version/due 重验；
  `838a47a8a` 移除 PostgreSQL initdb 的应用迁移挂载，使 API image/entrypoint
  成为全新与存量 volume 的唯一普通迁移控制面，`35010b4c`
  进一步收紧 Compose/PostgreSQL image 无 initdb 入口和 API entrypoint import-order 回归。
  验证引用：
  `test_postgres_initdb_cannot_execute_application_migrations`、
  `test_api_image_packages_migrations_at_entrypoint_default_path`、
  `test_api_entrypoint_runs_only_ordinary_additive_migrations`、
  `test_concurrent_index_compatibility_path_serializes_and_skips_valid_index`、
  `test_concurrent_index_compatibility_path_does_not_wait_for_another_startup`、
  `test_postgres_final_dispatch_and_cancel_use_run_then_work_item_lock_order` 与
  `test_postgres_final_dispatch_waits_for_parent_suspension_without_artifacts`。
