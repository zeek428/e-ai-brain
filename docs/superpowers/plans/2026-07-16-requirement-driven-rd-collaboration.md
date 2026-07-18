# Requirement-Driven R&D Collaboration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing R&D execution policy and workflow into one requirement-driven human/AI collaboration flow from assessment and iteration planning through development, testing, remote Git delivery, and policy-controlled deployment.

**Architecture:** Keep PostgreSQL as the sole business-state source and reuse the existing LangGraph, AI task, Agent Loop, Runner, quality-gate, Outbox, and deployment foundations. Replace the task-type executor policy contract with one versioned strategy plus role bindings, add requirement assessment and iteration grouping, then add a version-level collaboration graph whose durable work-item DAG is scheduled deterministically.

**Tech Stack:** FastAPI, Python 3.11+, PostgreSQL, LangGraph with PostgreSQL Checkpointer, React 19, TypeScript, Ant Design Pro, pytest, Vitest, Playwright/browser validation.

## Global Constraints

- Product requirement is the only R&D entry; Bug, code inspection, feedback, and online incidents must create or link a requirement first.
- Canonical assessment states are `draft/evaluating/waiting_human/needs_info/rework_required/accepted/deferred/rejected/failed/cancelled`; canonical collaboration and work-item states come only from the approved design contract.
- A product version is the collaboration aggregate root; one version can have many requirements but at most one non-terminal collaboration run.
- Accepted requirements join a compatible `planning` version first; create a new `planning` version only when none is eligible.
- Upgrade `rd_task_executor_policies` in place; do not expose legacy/new modes or a second policy menu.
- Scheduled-job definitions, runs, locks, retries, snapshots, Agent/Skill assembly, and history remain unchanged; code-inspection remediation keeps its action alias but writes a requirement instead of a direct AI task.
- LLM output is a proposal; deterministic services own state, DAG validation, leases, permissions, budgets, idempotency, and risk floors.
- High/critical risk, permission expansion, protected branches, production changes, and policy conflicts require human confirmation.
- New policies default to `delivery_target=ready_for_release` and deployment disabled.
- AI roles select explicit AI digital employees plus executor profiles through role bindings frozen in the strategy snapshot; employee identity never replaces executor authorization.
- R&D role definitions never grant RBAC permissions; human assignment separately checks permissions and product scope.
- AI digital employees are persistent actors distinct from role definitions and executor profiles; AI seats freeze both `ai_employee_id` and `executor_profile_id`.
- Every assessment, assessment opinion, collaboration run, feedback record, and governed experience source references an immutable `rd_task_executor_policy_snapshots` row. Base and assessment-resolved snapshots have separate stable identities and a parent chain, so automatic tightening never overwrites a policy version; historical interpretation never rereads the mutable policy.
- Unified policy records have a monotonic `policy_version`; snapshot identity columns are non-null and no-delta assessment finalization reuses the base snapshot.
- `product_versions.scope_version` is the sole requirement-scope concurrency fact and increments atomically with every accepted scope-affecting change, including included final/effective strategy snapshot replacement; active generations reject changes, and ready_for_release/deploying/released versions route them to a new planning version.
- Every run has immutable per-requirement scope rows whose requirement/assessment/final-snapshot set exactly equals the version-resolved source set; database deferred constraints reject missing or extra provenance.
- P0 human assignment uses explicit user IDs; team pools, calendars, and capacity-based automatic selection are not inferred.
- Requirement `batch-advance-status` may only cancel/close when no active collaboration work exists; all delivery targets and external AI-task create/start/batch-retry calls return `RD_COLLABORATION_REQUIRED`. Public single or batch cancel also returns that error when any task is linked to v2 collaboration; work-item cancellation atomically updates task, Review, attempt, work item, and run.
- `blocked/awaiting_human` work items persist a platform-controlled `resume_state`; clients cannot choose arbitrary recovery states.
- Collaboration runs entering `waiting_human` atomically persist `resume_state`, `suspended_decision_request_id`, and `suspended_at`, and resume from `running/integrating/verifying` only through the matching decision request.
- Failed/cancelled runs are immutable; restart creates a new generation referencing the latest terminal run after scope and resource revalidation.
- Decision expiry never auto-approves or resumes work; the subject stays paused while one successor request is idempotently escalated.
- Default delivery leaves the product version at `ready_for_release` and completes the collaboration run with `completion_reason=ready_for_release`; a deployed-target run remains non-terminal `ready_for_release` until P1 deployment succeeds.
- Coding success is not completion; independent quality evidence and reviewer separation are mandatory.
- P0 includes minimum worktree/branch isolation, remote push or MR/PR Outbox, version-level integration tests, reconciliation, and trusted delivery evidence through `ready_for_release`; optional deployment and advanced conflict/capacity optimization are P1.
- Role feedback is immutable P0 evidence. P1 experience candidates use `pending/approved/rejected/retired`, governed query/decision APIs, reviewer separation from every source producer, optimistic locking, full brain/product/work-item/trust-domain filtering, and frozen `experience_reuse_config` capacity/age/policy-scoped retrieval; approved experience never mutates active policy automatically.
- All new production behavior starts with a failing test and follows red-green-refactor.
- Do not deploy. Completion for this development branch is tests, browser validation, documentation, commit, and remote push.
- Use additive schema migration before implementation, advisory preflight while open, `draining` with an early-abort boundary, then irreversible `cutover_locked` for destructive cutover; there is still one runtime rule after activation.
- The previous 2026-07-16 test snapshot is invalid because app-scope files continued changing after capture. No failure allowlist is active. Before implementation begins, stop parallel app edits, capture `HEAD`, `git diff HEAD --binary -- apps`, `git status --porcelain=v1 --untracked-files=all -- apps`, and a path/content hash manifest for every untracked app file twice with identical results, then run the full backend and frontend suites against that frozen snapshot. Any failure blocks implementation; after fixing it, recapture the stable manifests and rerun the full suites.
- Scheduled-job definitions and runtime semantics are an explicit unchanged boundary, so scheduled-job backend/frontend failures can never be accepted as a known baseline or independently ignored; otherwise failures that stop before the run-detail assertions can mask regressions.

---

### Task 1: Synchronize Active Product and Engineering Documents

**Files:**
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/api/delivery-and-tasks.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-cases/requirements-and-tasks.md`
- Modify: `docs/02-specs/architecture/system-overview.md`
- Modify: `docs/02-specs/architecture/tech-stack.md`
- Modify: `docs/glossary.md`

**Interfaces:**
- Produces: active source-of-truth requirements and exact names used by migrations, APIs, services, tests, and pages in Tasks 2-15.
- Consumes: `docs/superpowers/specs/2026-07-16-requirement-driven-rd-collaboration-design.md`.

- [ ] **Step 1: Add the approved 2.0 product decisions to the PRD**

Add observable user stories and acceptance criteria for assessment, auto-grouping, unified policy, human/AI seats, work-item DAG, rework, human escalation, `ready_for_release`, optional deployment, attribution, and unchanged scheduled jobs.

- [ ] **Step 2: Replace the v1 lightweight-assessment and per-task-policy authority in the technical spec**

Document the unified state machines, tables, two-stage policy resolution, PostgreSQL Checkpointer, RBAC separation, migration cutover, and no fallback to policy-external executors.

- [ ] **Step 3: Update API, test-case, architecture, stack, and glossary contracts**

Define the API groups from later tasks and add `langgraph-checkpoint-postgres` to the intended stack.

- [ ] **Step 4: Verify active docs contain no conflicting authority**

Run:

```bash
rg -n "轻量需求评估.*不.*阻塞|task_compat|team_delivery|未命中策略.*沿用" docs/01-prd docs/02-specs docs/glossary.md
rg -n "needs_more_info|waiting_human_decision|rd_role_assignments|rd_decision_requests|rd_role_feedback|/api/requirements/\{[^}]+\}/collaboration-runs" docs/01-prd docs/02-specs docs/glossary.md
rg -n "subject_type=ai_executor|批量推进.*ready_for_release|启动权限按任务类型|生成任务响应" docs/01-prd docs/02-specs docs/glossary.md
```

Expected: no active statement permits bypassing assessment or falling back outside the unified policy, and no non-canonical v2 name or requirement-level collaboration-run creation path remains.

- [ ] **Step 5: Commit**

```bash
git add docs/01-prd docs/02-specs docs/glossary.md
git commit -m "docs: adopt requirement-driven rd collaboration"
```

### Task 2: Add the Additive Unified Collaboration Schema

**Files:**
- Create: `apps/api/app/db/migrations/109_requirement_driven_rd_collaboration.sql`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/store.py`
- Modify: `apps/api/tests/test_persistence_repository_boundaries.py`
- Create: `apps/api/tests/test_requirement_driven_rd_schema.py`

**Interfaces:**
- Produces: `rd_role_definitions`, `rd_ai_employees`, `rd_executor_profiles`, `rd_task_executor_policy_role_bindings`, `rd_task_executor_policy_snapshots`, `rd_task_executor_policy_snapshot_sources`, `requirement_assessments`, `requirement_assessment_opinions`, `rd_collaboration_runs`, `rd_collaboration_run_requirements`, `rd_run_seats`, `rd_role_sessions`, `rd_work_items`, `rd_work_item_dependencies`, `rd_work_item_attempts`, `rd_collaboration_events`, `decision_requests`, `rd_command_idempotency_records`, `rd_command_replay_secrets`, `role_feedback_records`, `rd_role_experience_records`, `rd_role_experience_sources`, and `rd_collaboration_upgrade_state`.
- Produces: generalized graph subjects, policy/version references, version delivery statuses, work-item linkage on `ai_tasks`, and `rd_collaboration_upgrade_state` maintenance/cutover metadata.

- [ ] **Step 1: Write failing migration-contract tests**

```python
def test_requirement_driven_collaboration_migration_is_registered():
    migrations = registered_migration_names()
    assert "109_requirement_driven_rd_collaboration.sql" in migrations


def test_new_collaboration_tables_have_standard_timestamps(migration_sql):
    for table in ("rd_role_definitions", "rd_ai_employees", "requirement_assessments", "rd_work_items", "rd_role_experience_records"):
        assert_table_has_created_and_updated_at(migration_sql, table)


def test_policy_snapshot_is_insert_only_and_has_no_updated_at(migration_sql):
    assert_table_has_columns(
        migration_sql,
        "rd_task_executor_policy_snapshots",
        {"policy_id", "policy_version", "parent_snapshot_id", "snapshot_kind", "resolution_context_key", "resolution_revision", "schema_version", "content_hash", "payload_json", "created_by", "created_at"},
    )
    assert_table_lacks_column(migration_sql, "rd_task_executor_policy_snapshots", "updated_at")
    assert_snapshot_mutation_trigger_rejects_update_and_delete(migration_sql)
    assert_snapshot_identity_columns_are_not_null(migration_sql)
    assert_base_and_derived_snapshot_checks(migration_sql)


def test_run_pause_fields_have_database_invariants(migration_sql):
    assert_fk_on_delete_restrict(migration_sql, "rd_collaboration_runs", "suspended_decision_request_id", "decision_requests")
    assert_waiting_human_pause_check(migration_sql, allowed_resume_states={"running", "integrating", "verifying"})


def test_all_rd_commands_have_persistent_idempotency(migration_sql):
    assert_table_has_columns(
        migration_sql,
        "rd_command_idempotency_records",
        {"command_type", "aggregate_type", "aggregate_id", "idempotency_key", "request_hash", "result_type", "result_id", "http_status", "response_hash", "response_json", "created_at"},
    )
    assert_table_lacks_column(migration_sql, "rd_command_idempotency_records", "expires_at")
    assert_unique_constraint(
        migration_sql,
        "rd_command_idempotency_records",
        ("command_type", "aggregate_type", "aggregate_id", "idempotency_key"),
    )


def test_version_resolved_snapshot_sources_are_deferred_and_immutable(migration_sql):
    assert_unique_constraint(migration_sql, "rd_task_executor_policy_snapshot_sources", ("snapshot_id", "requirement_id"))
    assert_no_unique_constraint(migration_sql, "rd_task_executor_policy_snapshot_sources", ("snapshot_id", "source_snapshot_id"))
    assert_table_has_columns(migration_sql, "rd_task_executor_policy_snapshot_sources", {"snapshot_id", "source_snapshot_id", "requirement_id", "assessment_id", "created_at"})
    assert_table_lacks_column(migration_sql, "rd_task_executor_policy_snapshot_sources", "updated_at")
    assert_deferrable_source_integrity_trigger(migration_sql, minimum_sources=1, same_policy_version=True, exact_run_scope_coverage=True)
    assert_source_mutation_trigger_rejects_update_and_delete(migration_sql)


def test_run_requirement_scope_is_immutable_and_exact(migration_sql):
    assert_table_has_columns(
        migration_sql,
        "rd_collaboration_run_requirements",
        {"collaboration_run_id", "requirement_id", "requirement_revision", "assessment_id", "final_strategy_snapshot_id", "acceptance_criteria_hash", "repository_scope_hash", "created_at"},
    )
    assert_table_lacks_column(migration_sql, "rd_collaboration_run_requirements", "updated_at")
    assert_unique_constraint(migration_sql, "rd_collaboration_run_requirements", ("collaboration_run_id", "requirement_id"))
    assert_run_scope_mutation_trigger_rejects_update_and_delete(migration_sql)


def test_run_generation_decision_expiry_and_fence_phases_are_constrained(migration_sql):
    assert_unique_constraint(migration_sql, "rd_collaboration_runs", ("product_version_id", "run_generation"))
    assert_partial_unique_index(migration_sql, "rd_collaboration_runs", ("supersedes_run_id",), "supersedes_run_id IS NOT NULL")
    assert_fk_on_delete_restrict(migration_sql, "rd_collaboration_runs", "supersedes_run_id", "rd_collaboration_runs")
    assert_decision_expiry_fields_and_due_index(migration_sql)
    assert_partial_unique_index(migration_sql, "decision_requests", ("supersedes_decision_request_id",), "supersedes_decision_request_id IS NOT NULL")
    assert_upgrade_fence_modes(migration_sql, {"disabled", "draining", "cutover_locked"})


def test_feedback_producer_identity_is_distinct_and_immutable(migration_sql):
    assert_table_has_columns(
        migration_sql,
        "role_feedback_records",
        {"collaboration_run_id", "feedback_kind", "source_event_id", "feedback_fingerprint", "producer_subject_type", "producer_subject_id", "producer_role_code", "producer_seat_id", "created_at"},
    )
    assert_columns_not_null(migration_sql, "role_feedback_records", {"collaboration_run_id", "feedback_kind", "source_event_id", "feedback_fingerprint", "producer_subject_type", "producer_subject_id"})
    assert_feedback_producer_type_check(migration_sql, {"human_user", "ai_employee", "service"})
    assert_feedback_producer_subject_resolution_triggers(
        migration_sql,
        human_table="users",
        ai_employee_table="rd_ai_employees",
        service_codes={"collaboration_orchestrator", "quality_gate", "delivery_reconciler", "decision_expiry_worker"},
    )
    assert_feedback_producer_role_seat_pair_check(migration_sql)
    assert_feedback_producer_seat_fk_restrict(migration_sql)
    assert_feedback_producer_seat_role_match_trigger(migration_sql)
    assert_unique_constraint(migration_sql, "rd_collaboration_events", ("collaboration_run_id", "id"))
    assert_composite_fk_on_delete_restrict(
        migration_sql,
        "role_feedback_records",
        ("collaboration_run_id", "source_event_id"),
        "rd_collaboration_events",
        ("collaboration_run_id", "id"),
    )
    assert_unique_constraint(migration_sql, "role_feedback_records", ("collaboration_run_id", "feedback_fingerprint"))
    assert_table_lacks_column(migration_sql, "role_feedback_records", "updated_at")
    assert_feedback_mutation_trigger_rejects_update_and_delete(migration_sql)


def test_scope_change_requests_are_versioned_idempotent_and_single_pending(migration_sql):
    assert_table_has_columns(
        migration_sql,
        "rd_scope_change_requests",
        {"product_version_id", "request_id", "source_run_id", "source_run_state", "expected_scope_version", "expected_run_generation", "operations_json", "operations_hash", "status", "decision_request_id", "applied_scope_version", "requested_by", "applied_at", "created_at", "updated_at"},
    )
    assert_unique_constraint(migration_sql, "rd_scope_change_requests", ("product_version_id", "request_id"))
    assert_partial_unique_index(migration_sql, "rd_scope_change_requests", ("product_version_id",), "status = 'pending_decision'")
    assert_fk_on_delete_restrict(migration_sql, "rd_scope_change_requests", "source_run_id", "rd_collaboration_runs")
    assert_fk_on_delete_restrict(migration_sql, "rd_scope_change_requests", "decision_request_id", "decision_requests")
    assert_scope_change_request_state_checks(migration_sql)
    assert_scope_change_request_proposal_fields_immutable(migration_sql)
    assert_table_has_columns(
        migration_sql,
        "rd_scope_change_request_operations",
        {"scope_change_request_id", "position", "op", "requirement_id", "requirement_revision", "assessment_id", "final_strategy_snapshot_id", "repository_id", "branch_config_version", "base_commit_sha", "destination", "created_at"},
    )
    assert_unique_constraint(migration_sql, "rd_scope_change_request_operations", ("scope_change_request_id", "position"))
    assert_scope_change_operation_kind_checks(migration_sql)
    assert_scope_change_operation_fks_restrict(migration_sql)
    assert_immutable_table_trigger(migration_sql, "rd_scope_change_request_operations")
    assert_table_has_columns(migration_sql, "requirements", {"supersedes_requirement_id", "source_collaboration_run_id"})
    assert_fk_on_delete_restrict(migration_sql, "requirements", "supersedes_requirement_id", "requirements")
    assert_fk_on_delete_restrict(migration_sql, "requirements", "source_collaboration_run_id", "rd_collaboration_runs")
    assert_requirement_supersedes_requires_source_run_check(migration_sql)
    assert_requirement_lineage_same_product_ready_source_trigger(migration_sql)
    assert_index(migration_sql, "requirements", ("supersedes_requirement_id", "source_collaboration_run_id"))


def test_claim_replay_secret_is_expiring_and_scrubbable(migration_sql):
    assert_table_has_columns(migration_sql, "rd_command_replay_secrets", {"command_record_id", "secret_ciphertext", "key_id", "expires_at", "scrubbed_at", "created_at", "updated_at"})
    assert_unique_constraint(migration_sql, "rd_command_replay_secrets", ("command_record_id",))
    assert_expired_secret_scrub_contract(migration_sql)
```

- [ ] **Step 2: Run the test and confirm red**

Run: `cd apps/api && uv run pytest tests/test_requirement_driven_rd_schema.py tests/test_persistence_repository_boundaries.py -q`

Expected: FAIL because migration 109 and new collections are absent.

- [ ] **Step 3: Add normalized tables, constraints, indexes, and compatibility-safe columns**

Migration 109 is additive only: add `rd_task_executor_policies.policy_version bigint NOT NULL DEFAULT 1` and `product_versions.scope_version bigint NOT NULL DEFAULT 1`; add `requirements.supersedes_requirement_id/source_collaboration_run_id`; create canonical tables and indexes including stable AI employee identity, immutable base/assessment_resolved/version_resolved policy snapshots, relational version snapshot sources, immutable run requirement scope, governed `rd_scope_change_requests` plus immutable typed operation rows, permanent command idempotency response records, expiring claim replay secrets, and relational experience sources; add work-item `resume_state`/suspension metadata; add collaboration `run_generation/supersedes_run_id/resume_state/suspended_decision_request_id/suspended_at/completion_reason`; add decision expiry/escalation fields, versioned experience governance fields, and phased fence metadata; add nullable graph/version/task links; seed permission definitions including `delivery.rd_ai_employees.manage`, `delivery.decision_requests.answer`, and `delivery.rd_role_experiences.read/decide`. It must not convert policies, cancel tasks, change API behavior, or remove old columns; active old policies are explicitly converted before draining, old draft tasks are cancelled during draining, and physical cleanup happens only after locked preflight and cutover in Task 14.

Add the exact snapshot identity constraint `policy_id + policy_version + snapshot_kind + resolution_context_key + resolution_revision`, make every identity/content column NOT NULL except base `parent_snapshot_id`, add content-hash index and self-parent FK, and enforce row-local CHECKs for base `policy:{policy_id}:version:{policy_version}`/parent-null/revision-0, assessment_resolved `assessment:{assessment_id}`/parent-present/revision-1..2, and version_resolved `version:{version_id}:scope:{scope_version}`/base-parent/revision-1. Create `rd_task_executor_policy_snapshot_sources(snapshot_id, source_snapshot_id, requirement_id, assessment_id, created_at)` with unique `(snapshot_id,requirement_id)` edges; do not make `(snapshot_id,source_snapshot_id)` unique because multiple no-delta requirements may legitimately share one base/final snapshot. Create immutable `rd_collaboration_run_requirements(collaboration_run_id,requirement_id,requirement_revision,assessment_id,final_strategy_snapshot_id,acceptance_criteria_hash,repository_scope_hash,created_at)` with unique run/requirement rows. A `DEFERRABLE INITIALLY DEFERRED` constraint trigger validates at commit that every run has at least one scope row, source count equals scope count, both requirement sets are exactly equal, and each source uses the same policy ID/version and matching accepted assessment/final snapshot; mutation triggers reject snapshot/source/run-scope UPDATE/DELETE. Runtime-role grants are INSERT/SELECT only; policy and all consumer/source FKs use `ON DELETE RESTRICT`. Required snapshot consumers are `requirement_assessments.initial_strategy_snapshot_id/final_strategy_snapshot_id/strategy_snapshot_id`, `requirement_assessment_opinions.strategy_snapshot_id`, `rd_collaboration_runs.strategy_snapshot_id` (version_resolved only), `rd_collaboration_run_requirements.final_strategy_snapshot_id`, `rd_scope_change_request_operations.final_strategy_snapshot_id`, `role_feedback_records.strategy_snapshot_id`, `rd_role_experience_records.strategy_snapshot_id`, and `rd_role_experience_sources.strategy_snapshot_id`. Immutable snapshots, snapshot sources, run scope, typed scope-change operations, command idempotency rows, and `role_feedback_records` intentionally have only `created_at`; migration guardrails must exempt them from the mutable-table `updated_at` rule. `rd_scope_change_requests` and `rd_command_replay_secrets` are mutable and retain both timestamps.

Add partial unique indexes for one active product policy and one active business-brain default policy, the assessment key on `requirement_id + requirement_revision + initial_strategy_snapshot_id`, one active run per version, unique `(product_version_id,run_generation)`, unique non-null run `supersedes_run_id`, one scope-change request per `(product_version_id,request_id)`, one pending scope-change per version, unique typed operation `(scope_change_request_id,position)`, one active decision per subject/type/non-null plan version across `pending/waiting_more_info`, decision expiry due/event indexes, unique non-null decision `supersedes_decision_request_id`, unique dependency edges, work-item/attempt identities, unique `(collaboration_run_id,feedback_fingerprint)`, experience version/one-approved-version/source-feedback uniqueness, and `rd_command_idempotency_records(command_type, aggregate_type, aggregate_id, idempotency_key)`. Command records store `response_hash/response_json`, have no `expires_at` or TTL, and cannot be reused after aggregate terminal states. Claim retains a permanent record but stores the token only in `rd_command_replay_secrets`, uniquely keyed by command record; expiry cleanup nulls ciphertext and sets `scrubbed_at`, while later replay returns the fixed lease-expired error. Add `suspended_decision_request_id -> decision_requests(id) ON DELETE RESTRICT` and a CHECK requiring all three run suspension fields only for `waiting_human`, with `resume_state IN ('running','integrating','verifying')`. Decision rows freeze `expires_at/timeout_policy/escalation_target_selector/escalation_level` and record `expired_at/expiry_event_id/supersedes_decision_request_id`; upgrade state uses `fence_mode=disabled|draining|cutover_locked`, optimistic version, cleanup markers and abort audit fields. Migration-contract tests must assert exact predicates, checks, deferred trigger behavior, secret scrubbing, grants, and foreign keys.

Create immutable `role_feedback_records` with attributed actor fields, `collaboration_run_id/feedback_kind/source_event_id/feedback_fingerprint`, and mandatory `producer_subject_type/producer_subject_id`; add unique `rd_collaboration_events(collaboration_run_id,id)` and an `ON DELETE RESTRICT` composite feedback FK so an existing event from another run cannot be cited. Add nullable `producer_role_code/producer_seat_id` that become required when the producer acts through a collaboration seat. The polymorphic producer ID is validated by subject-type-specific deferred constraint triggers against the human-user or AI-employee table; `service` is constrained by a database CHECK to the stable codes `collaboration_orchestrator|quality_gate|delivery_reconciler|decision_expiry_worker`. `producer_seat_id` uses `ON DELETE RESTRICT` to `rd_run_seats`, and its frozen role must match the seat. Canonical fingerprint input covers run generation, source event, feedback kind, attributed role/seat/subject, work item/attempt, and strategy snapshot; enforce unique `(collaboration_run_id,feedback_fingerprint)`, database UPDATE/DELETE rejection, and only `created_at` so event replay returns the same record and experience review can join every source to the actual producer rather than infer it from the evaluated actor.

- [ ] **Step 4: Generalize graph subjects and version statuses**

Add `subject_type/subject_id/thread_id/graph_definition/graph_version` to graph runs/checkpoints, add `ready_for_release/deploying` product-version constraints, and add `collaboration_run_id/work_item_id` to AI tasks.

- [ ] **Step 5: Run migration tests green**

Run the Step 2 command.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/db/migrations/109_requirement_driven_rd_collaboration.sql apps/api/app/core/persistence.py apps/api/app/core/store.py apps/api/tests/test_requirement_driven_rd_schema.py apps/api/tests/test_persistence_repository_boundaries.py
git commit -m "feat: add requirement-driven collaboration schema"
```

### Task 3: Add Focused Collaboration Repositories

**Files:**
- Create: `apps/api/app/core/repositories/rd_collaboration.py`
- Create: `apps/api/app/core/repositories/rd_collaboration_writes.py`
- Modify: `apps/api/app/core/repositories/__init__.py`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Create: `apps/api/tests/test_rd_collaboration_repository.py`

**Interfaces:**
- Produces: list/get/save methods for roles, AI digital employees, executor profiles, unified policies/bindings/immutable snapshots/version source edges, assessments/opinions, collaboration runs and immutable run requirement scope, governed scope-change requests, seats, sessions, work items/dependencies/attempts/events, decisions, permanent command idempotency, expiring replay secrets, immutable feedback, governed experiences, and relational experience sources.
- Produces: `freeze_base_policy_snapshot`, `derive_assessment_policy_snapshot`, `merge_version_policy_snapshot_with_sources`, `create_collaboration_run_with_exact_scope`, `restart_terminal_collaboration_run`, `create_scope_change_request`, `apply_scope_change_bundle`, `execute_idempotent_rd_command`, `save_and_scrub_claim_replay_secret`, `save_assessment_bundle`, `assign_requirement_to_version_and_increment_scope`, `claim_ready_work_item`, `save_work_item_attempt_bundle`, `cancel_work_item_bundle`, `suspend_collaboration_run`, `apply_decision_bundle`, `answer_decision_request`, `expire_and_escalate_decision_request`, `save_role_feedback_once`, and `decide_role_experience` transaction methods.

- [ ] **Step 1: Write failing repository transaction tests**

```python
def test_claim_ready_work_item_is_atomic(repository, ready_work_item):
    first = repository.claim_ready_work_item(ready_work_item["id"], lease_owner="worker-a")
    second = repository.claim_ready_work_item(ready_work_item["id"], lease_owner="worker-b")
    assert first["lease_owner"] == "worker-a"
    assert second is None
```

Cover policy PATCH version increments, one active product/default policy, base/assessment_resolved/version_resolved immutable snapshot insert, parent chain, no-tightening assessment base reuse including multiple requirements sharing one base source, deterministic version merge/source edges, exact run-scope/source coverage, deferred source integrity, identity NOT NULL/CHECK, idempotent read and database snapshot/source/run-scope update/delete rejection; product scope-version increments only without a non-terminal run, `RD_SCOPE_FROZEN` during an active generation, concurrent same/different scope-change requests, stale scope/generation, invalid operations, pre-ready pause plus approve/reject, atomic terminalize/change/exactly-once increment/restart, and ready-target completed and ready/deploying changes returning `RD_SCOPE_FROZEN` with `resolution=new_planning_version` and routed to a follow-up requirement in a new planning version; optimistic decisions, structured input validation, answer permission/selector and request-more-info reopening, database-time expiry and idempotent keep-paused escalation; one active run per version, unique run generations, terminal-run immutability and restart to a new generation; DAG edge uniqueness; plan-version uniqueness; assessment revision/initial-snapshot uniqueness; AI employee/executor identity separation; work-item and run-level suspension/resume atomicity plus FK/CHECK violations from `running/integrating/verifying`; immutable feedback with attributed actor distinct from producer subject/role/seat, invalid human/AI/service producer resolution rejected, producer role/seat null-pair or mismatch rejected, cross-run source-event FK rejection, and concurrent Graph/event replay returning one `(run,fingerprint)` record; immutable response-snapshot command idempotency, valid claim token replay and expired secret scrub; work-item/attempt/cancel idempotency including high-risk continue-to-ready/new-attempt; experience version/approval/source uniqueness and reviewer rejection against every joined producer; and requirement/version assignment idempotency.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_repository.py -q`

Expected: FAIL with missing repository classes.

- [ ] **Step 3: Implement read and write repositories**

Use SQL/repository reads and transaction bundles; do not make `MemoryStore` a production source of truth. Use `FOR UPDATE SKIP LOCKED` for claims and optimistic `version` checks for decisions and mutable plans.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then:

```bash
git add apps/api/app/core/repositories apps/api/app/core/persistence.py apps/api/app/core/persistence_contracts.py apps/api/tests/test_rd_collaboration_repository.py
git commit -m "feat: persist rd collaboration state"
```

### Task 4: Upgrade the Existing R&D Execution Policy API

**Files:**
- Modify: `apps/api/app/api/routers/tasks.py`
- Refactor: `apps/api/app/services/rd_task_executor_policies.py`
- Create: `apps/api/app/services/rd_policy_validation.py`
- Create: `apps/api/app/services/rd_policy_resolution.py`
- Modify: `apps/api/app/core/repositories/tasks.py`
- Rewrite: `apps/api/tests/test_rd_task_executor_policies.py`
- Modify: `apps/api/tests/test_management_list_read_models.py`

**Interfaces:**
- Produces: `resolve_initial_rd_policy(store, *, requirement) -> dict`.
- Produces: `resolve_final_rd_policy(store, *, requirement, assessment) -> dict`.
- Produces: version-locked policy create/PATCH with monotonic `policy_version`, `freeze_base_rd_policy_snapshot(store, *, policy, role_bindings, schema_version) -> dict`, `derive_assessment_rd_policy_snapshot(store, *, assessment_id, parent_snapshot_id, resolution_revision, tightened_payload) -> dict`, `merge_version_rd_policy_snapshot(store, *, version_id, scope_version, source_snapshot_ids) -> dict`, no-delta assessment base reuse, version_resolved source persistence, and identity/parent/hash validation on every read.
- Produces: `resolve_work_item_binding(policy_snapshot, *, role_code, task_type) -> dict`.
- API remains `/api/delivery/rd-task-executor-policies` but accepts one strategy payload with `name`, `brain_app_id`, `product_id`, `status`, `matching_config`, `assessment_config`, `iteration_config`, `delivery_target`, `team_config`, `autonomy_config`, `quality_gate_config`, `git_config`, `experience_reuse_config`, `deployment_config`, and `role_bindings`.

- [ ] **Step 1: Write failing unified-policy API tests**

```python
def test_policy_rejects_missing_required_role_binding(client, admin_headers):
    response = client.post(
        "/api/delivery/rd-task-executor-policies",
        headers=admin_headers,
        json=valid_policy_payload(role_bindings=[]),
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "RD_POLICY_REQUIRED_ROLE_MISSING"
```

Also assert old top-level `task_type/executor_type/runner_id` fields, assessment `strategy_id`, and any version-level policy override are rejected; policy changes require a new policy_version and requirement re-evaluation. Assert no fallback executor is used, stale policy PATCH versions conflict, only one active product/default policy is allowed, concurrent identical base/derived/version freezes return one snapshot, no-delta assessment finalization reuses base, and two assessments may derive different final payloads from one policy version without conflict. Cover version merge operators: allowlists intersect, denylists/roles/gates/human points union, upper bounds tighten, ready_for_release dominates deployed, budget preserves the base run cap plus per-requirement allocations, and experience reuse uses enabled AND, confidence max, capacity/age minima, trust-domain intersection, strictest compatibility and reviewer OR. Undeclared/incomparable fields return `RD_VERSION_POLICY_MERGE_REQUIRED` without a run. Assert source edges and immutable run scope cover every included requirement exactly once with no missing/extra rows, are immutable and same-policy-version, historical reads never use the mutable policy, policy DELETE with snapshots returns `RD_POLICY_IN_USE`, and missing/hash-mismatched/unsupported snapshots return `RD_POLICY_SNAPSHOT_INVALID`.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_task_executor_policies.py tests/test_management_list_read_models.py -q`

Expected: FAIL because the API still requires the old per-task fields.

- [ ] **Step 3: Split validation, resolution, persistence, and Runner payload responsibilities**

Keep each service focused. Initial resolution uses stable requirement fields only. Final resolution implements the design's explicit monotonic comparator: only less automation, tighter risk/permission/tool/repository/budget limits, more gates/roles, or `deployed -> ready_for_release` are automatically stronger. Incomparable or expanding assessment changes return `RD_POLICY_HUMAN_DECISION_REQUIRED`; more than two strengthening rounds return `RD_POLICY_RESOLUTION_LIMIT`. Version merge is deterministic and only combines final/effective snapshots from the same policy ID/version using the Schema merge-operator registry; ambiguity creates a decision request and no run. Work-item resolution requires exactly one active role binding.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: upgrade rd execution policy` with only policy and focused test files.

### Task 5: Add R&D Roles, AI Digital Employees, and Executor Profiles

**Files:**
- Create: `apps/api/app/api/routers/rd_organization.py`
- Create: `apps/api/app/services/rd_role_definitions.py`
- Create: `apps/api/app/services/rd_ai_employees.py`
- Create: `apps/api/app/services/rd_executor_profiles.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_rd_organization.py`

**Interfaces:**
- Produces: CRUD under `/api/delivery/rd-roles`, `/api/delivery/rd-ai-employees`, and `/api/delivery/rd-executor-profiles`.
- Produces: `qualify_human_actor(user, *, role_definition, product_id) -> bool` and `qualify_ai_actor(employee, profile, *, role_definition, policy_binding) -> bool`.

- [ ] **Step 1: Write failing RBAC-separation tests**

```python
def test_creating_rd_role_does_not_grant_system_permission(client, admin_headers):
    role = client.post("/api/delivery/rd-roles", headers=admin_headers, json=role_payload()).json()["data"]
    assert role["system_role_id"] is None
    assert "granted_permissions" not in role


def test_human_seat_requires_permission_scope_and_explicit_selector(client, product_owner_headers):
    response = create_human_seat(
        client,
        headers=product_owner_headers,
        actor_selector={"team_id": "implicit-team"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "RD_HUMAN_SELECTOR_INVALID"


def test_ai_employee_identity_is_distinct_from_executor_profile(client, admin_headers):
    employee_a = create_ai_employee(client, admin_headers, code="dev-a")
    employee_b = create_ai_employee(client, admin_headers, code="dev-b")
    seat_a = create_ai_seat(employee_id=employee_a["id"], executor_profile_id="executor-shared")
    seat_b = create_ai_seat(employee_id=employee_b["id"], executor_profile_id="executor-shared")
    assert seat_a["ai_employee_id"] != seat_b["ai_employee_id"]
    assert seat_a["executor_profile_id"] == seat_b["executor_profile_id"]
```

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_organization.py -q`

- [ ] **Step 3: Implement scoped CRUD and qualification**

Human seats must use explicit `user_ids` in P0 and pass existing RBAC, product scope, collaboration permission, and seat-state checks. AI seats use explicit `ai_employee_ids` for actor identity and a separate executor profile for service identity, trust domain, tool policy, and execution-resource grants. Employee records store stable identity/capability/persona metadata but no secrets or permissions. Seed and test the canonical permission matrix, including `delivery.rd_ai_employees.manage` and `delivery.decision_requests.answer`; answer permission never bypasses the request's brain/product scope or frozen `answer_actor_selector`.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: add rd organization catalog`.

### Task 6: Implement Requirement Assessment with Two-Stage Policy Resolution

**Files:**
- Create: `apps/api/app/api/routers/requirement_assessments.py`
- Create: `apps/api/app/services/requirement_assessments.py`
- Create: `apps/api/app/services/requirement_assessment_execution.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/services/requirements.py`
- Modify: `apps/api/app/core/repositories/requirements.py`
- Create: `apps/api/tests/test_requirement_assessments.py`

**Interfaces:**
- Produces: `POST /api/requirements/{id}/assessments`, `GET /api/requirements/{id}/assessments/latest`, and `POST /api/requirement-assessments/{assessment_id}/opinions|answers|decisions`.
- Produces: `start_requirement_assessment`, `record_assessment_opinion`, `submit_assessment_answers`, `decide_requirement_assessment`, and `finalize_requirement_assessment`.
- Consumes: initial/final policy resolution from Task 4 and role/executor qualification from Task 5.

- [ ] **Step 1: Write failing assessment state tests**

```python
def test_assessment_resolves_initial_policy_before_ai_roles(client, submitted_requirement):
    response = start_assessment(client, submitted_requirement["id"])
    assessment = response.json()["data"]
    assert assessment["initial_policy_snapshot"]["snapshot_kind"] == "base"
    assert assessment["initial_policy_snapshot"]["resolution_revision"] == 0
    assert assessment["status"] == "evaluating"
```

Cover assigned human/AI opinion authorization and opinion snapshot FK, answer-created revisions, `accept/reject/request_more_info/request_rework/defer`, `waiting_human/needs_info/rework_required/accepted/deferred/rejected`, risk floor, no-delta final/effective base reuse, at most two monotonic policy-strengthening rounds, base -> assessment_resolved parent chain, required-opinion completion after strengthening, incomparable policies, human conflict, every caller being unable to supply `strategy_id`, policy change through the unified policy API followed by re-evaluation, stable initial-snapshot assessment uniqueness, and persisted request-hash/response-snapshot idempotency.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_requirement_assessments.py -q`

- [ ] **Step 3: Implement assessment orchestration**

Create one opinion request per required role. Assessment AI tasks are internal execution units authorized by the initial policy and are the only pre-accepted exception to normal work-item task creation; they cannot create code, Git, or deployment side effects. Opinions require the assigned actor and persist the snapshot used to produce them; answers create a new requirement/assessment revision; decisions accept only the five canonical actions and use optimistic locking. The assessment request model has no `strategy_id`; even policy managers must update the unified product/default policy to a new policy_version and start a new evaluation rather than inject a candidate strategy. Each automatic tightening round creates an `assessment_resolved` child snapshot for the same policy version and assessment context; it never updates the base snapshot. Finalization requires all mandatory compatible opinions, stores evidence/confidence/cost/actor/executor attribution, and atomically advances `submitted + accepted` to `approved`. Existing standalone approve/reject endpoints cannot bypass this transition.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command plus `tests/test_requirement_lifecycle.py`, then commit `feat: assess requirements before planning`.

### Task 7: Implement Automatic Iteration Grouping and Version Completion States

**Files:**
- Create: `apps/api/app/services/requirement_iteration_planning.py`
- Modify: `apps/api/app/api/routers/requirements.py`
- Modify: `apps/api/app/api/routers/product_versions.py`
- Modify: `apps/api/app/services/version_status.py`
- Modify: `apps/api/app/core/repositories/product_config.py`
- Modify: `apps/api/app/core/repositories/product_config_writes.py`
- Create: `apps/api/tests/test_requirement_iteration_grouping.py`
- Modify: `apps/api/tests/test_iteration_version_status_flow.py`

**Interfaces:**
- Produces: `plan_accepted_requirement(store, *, requirement_id, assessment_id, actor_id) -> dict`.
- Produces: candidate scoring with hard eligibility, deterministic score breakdown, idempotency key, and either an existing version assignment or one new planning version.
- Extends standard requirement creation with required `source_collaboration_run_id` for post-ready follow-ups and optional `supersedes_requirement_id` for continuations/replacements; provided references are validated same-product `ON DELETE RESTRICT` lineage, supersedes cannot appear without the source run, and the follow-up requirement always begins at submitted for a new planning cycle.

- [ ] **Step 1: Write failing grouping tests**

```python
def test_accepted_requirement_prefers_compatible_planning_version(store):
    result = plan_accepted_requirement(store, requirement_id="req-1", assessment_id="assessment-1", actor_id="system")
    assert result["version_id"] == "version-planning-compatible"
    assert result["created_version"] is False
```

Cover no candidate, high-risk new-version confirmation, tied candidates requiring human decision while the requirement remains `approved`, capacity, policy mismatch, different policy ID/version, non-mergeable final snapshots, concurrent replay, manual batch scheduling rechecking all hard constraints, exact `scope_version` increments/returns for membership, revision/acceptance, included final/effective strategy snapshot, repository and branch frozen-input changes, no increment for display-only edits, and refusal to mutate active/testing versions outside controlled range change.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_requirement_iteration_grouping.py tests/test_iteration_version_status_flow.py -q`

- [ ] **Step 3: Implement deterministic grouping and new states**

Use a transaction lock on requirement and candidate versions. Accepted assessment atomically advances the requirement to `approved`; successful assignment advances it to `planned` and compare-and-increments `product_versions.scope_version`. Requirement add/remove/reassign, included revision/acceptance change, included final/effective strategy snapshot replacement, and frozen repository/branch baseline change increment the same field only when no non-terminal collaboration run exists; display-only edits do not. Version list/detail, grouping results and scope conflict responses return it. Candidate versions must have the same resolved policy ID/version and pass a dry-run version merge against all included final/effective snapshots; versions do not store or accept an explicit strategy override. Tied candidates, non-mergeable policies, and high-risk new-version creation produce a `plan_version=0` decision request without prematurely setting `planned`. Manual `batch-schedule` is not a bypass: it rechecks policy merge, capacity, repository, delivery-target, and hard-dependency compatibility and only accepts `planning` versions. Add `ready_for_release/deploying` version transitions and keep `ready_for_release` distinct from `released`. Once a non-terminal run exists, ordinary scope-changing commands return `RD_SCOPE_FROZEN`; only non-scope replanning increments `plan_version`, and Task 9 owns the single governed scope-change command. Once a ready-target run completes or a deployed-target run reaches `ready_for_release/deploying`, the version and delivery evidence must not roll back; scope changes return `RD_SCOPE_FROZEN` with `resolution=new_planning_version`, and standard requirement creation persists required `source_collaboration_run_id` plus optional `supersedes_requirement_id` before independent assessment and grouping into a new planning version.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command plus `tests/test_requirement_batch_schedule.py`, then commit `feat: group accepted requirements into iterations`.

### Task 8: Replace Direct R&D Entry Bypasses with Requirement Adapters

**Files:**
- Modify: `apps/api/app/api/routers/requirements.py`
- Modify: `apps/api/app/api/routers/bugs.py`
- Modify: `apps/api/app/services/bugs.py`
- Modify: `apps/api/app/services/code_inspections.py`
- Modify: `apps/api/app/services/assistant_action_drafts.py`
- Modify: `apps/api/app/services/assistant_chat_intents.py`
- Modify: `apps/api/app/services/task_creation.py`
- Modify: `apps/api/app/services/task_start_execution.py`
- Modify: `apps/api/app/services/task_batch_operations.py`
- Modify: `apps/api/app/services/task_state_transitions.py`
- Modify: `apps/web/src/pages/Requirements/index.tsx`
- Modify: `apps/web/src/pages/CodeInspections/index.tsx`
- Modify: `apps/web/src/services/bugClient.ts`
- Modify: `apps/web/src/services/requirementClient.ts`
- Create: `apps/api/tests/test_rd_requirement_entry_adapters.py`
- Modify: `apps/api/tests/test_code_inspection_governance.py`
- Modify: `apps/web/tests/RequirementsPage.test.tsx`
- Modify: `apps/web/tests/CodeInspectionsPage.test.tsx`

**Interfaces:**
- Produces: `create_or_link_rd_requirement(store, *, source_type, source_id, product_id, evidence, actor_id) -> dict` with an idempotency key by source object and open requirement.
- Retires delivery-state batch advancement and public task create/start/retry/cancel for v2-linked tasks in addition to direct task creation from requirement, Bug, code-inspection, and assistant entry points, while leaving scheduled-job definition and execution semantics unchanged.

- [ ] **Step 1: Write failing bypass tests**

```python
def test_bug_promotion_creates_requirement_not_ai_task(client, bug, rd_owner_headers):
    response = client.post(f"/api/bugs/{bug['id']}/promote-ai-task", headers=rd_owner_headers)
    assert response.status_code == 200
    assert response.json()["data"]["requirement_id"]
    assert response.json()["data"].get("ai_task_id") is None
```

Also assert requirement `generate-task/batch-generate-tasks` return `RD_COLLABORATION_REQUIRED`; `batch-advance-status` rejects every delivery target and only permits safe cancel/close; public `POST /api/ai-tasks`, `/api/ai-tasks/{id}/start`, and `/api/ai-tasks/batch-retry` reject human/external callers; single `/cancel` rejects a v2-linked task; batch cancel containing any v2-linked task rejects the whole batch with no partial historical-task update; code-inspection remediation writes a requirement linked to the finding/report and exposes requirement coverage/links while task fields remain historical read-only; assistant `create_rd_task` creates a requirement draft; duplicate adapters reuse the open requirement; and the Requirements/Task pages have no direct-generate, direct-start, batch-retry, direct-cancel, or delivery-state advance controls for v2 tasks.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_requirement_entry_adapters.py -q && cd ../../apps/web && npm test -- RequirementsPage.test.tsx`

Expected: FAIL because current services and UI still create AI tasks directly.

- [ ] **Step 3: Implement one requirement adapter and compatibility responses**

Route every legacy source through `create_or_link_rd_requirement`. Preserve source evidence and audit linkage. Return compatibility errors from public task create/start/retry and delivery-state batch advancement. For cancel, legacy non-collaboration tasks retain current behavior; any v2-linked task returns `RD_COLLABORATION_REQUIRED`, and a mixed batch fails atomically. Expose create/dispatch/cancel AI-task commands only as internal work-item services for Task 11. Change active code-inspection projections from task coverage/links to `created_requirement_id(s)`, `requirement_coverage_rate`, uncovered requirement counts and requirement links; keep `created_task_id(s)`, `task_creation` and task coverage only as explicitly labeled historical read fields. Do not change `scheduled_jobs/scheduled_job_runs`, locking, retry, Agent/Skill snapshots, or scheduler behavior; only the code-inspection result business target and its read projections change from direct task to requirement.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: route rd work through requirements`.

### Task 9: Implement Work-Item DAG, Seats, Decisions, Rework, and Feedback

**Files:**
- Create: `apps/api/app/api/routers/rd_collaboration.py`
- Create: `apps/api/app/services/rd_collaboration_planning.py`
- Create: `apps/api/app/services/rd_work_item_scheduler.py`
- Create: `apps/api/app/services/rd_collaboration_decisions.py`
- Create: `apps/api/app/services/rd_scope_changes.py`
- Create: `apps/api/app/services/rd_command_replay_secrets.py`
- Create: `apps/api/app/services/rd_feedback_attribution.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_rd_collaboration_runtime.py`
- Create: `apps/api/tests/test_rd_work_item_scheduler.py`

**Interfaces:**
- Produces implementation-level contracts for `POST /api/product-versions/{version_id}/collaboration-runs`, `POST /api/product-versions/{version_id}/collaboration-runs/restart`, `POST /api/product-versions/{version_id}/scope-change-requests`, `GET /api/delivery/rd-scope-change-requests/{id}`, `GET /api/requirements/{requirement_id}/collaboration-run`, run detail, plan/replan, work-item claim/submit/block/review/cancel, event, and decision decide/answers APIs.
- Produces: `validate_work_item_plan`, `ready_work_items`, `claim_work_item`, `scrub_expired_command_replay_secrets`, `suspend_work_item`, `cancel_work_item`, `suspend_collaboration_run`, `resume_work_item`, `resume_collaboration_run`, `restart_terminal_collaboration_run`, `create_scope_change_request`, `apply_scope_change_decision`, `complete_attempt`, `apply_decision`, `answer_decision_request`, and `expire_decision_requests`.

- [ ] **Step 1: Write failing DAG and scheduling tests**

```python
def test_scheduler_does_not_release_item_before_dependencies_are_approved(store):
    items = ready_work_items(store, collaboration_run_id="run-1")
    assert "integration-item" not in {item["id"] for item in items}
```

Cover the exact API fields: start `request_id/scope_version`; restart `request_id/terminal_run_id/scope_version/reason`; scope change `request_id/expected_scope_version/expected_run_generation/source_run_id/reason/operations`; claim `expected_version/lease_seconds/idempotency_key`; submit `attempt_id/lease_token/version/output/evidence/idempotency_key`; review `decision/comment/version/idempotency_key`; cancel `reason/version/idempotency_key`; decision `selected_option/input/comment/version/idempotency_key`; decision answers `answer/evidence/version/idempotency_key`. Start/restart return request/scope/run_generation/supersedes_run_id/version_resolved snapshot kind/hash/source count/idempotent replay; scope change returns request/decision/source run/current or applied scope/terminal run/restart_required/idempotent replay; claim/submit/review/cancel/decision return complete work-item, attempt, run/decision version, `next_state`, `idempotent_replay`, and `trace_id` envelopes. Assert immutable response snapshots reproduce the original business version, `response_hash` excludes per-call `trace_id/idempotent_replay`, replay uses a new trace ID, claim replays the same encrypted token only before lease expiry, expiry scrubs ciphertext and returns the fixed error afterward without a new attempt, and all conflicts perform no partial write. Review mapping is fixed as approve -> approved, request_rework -> rework_required, reject -> failed plus a run-level replan/terminate decision for required items. Decision options freeze `outcome/subject_transition/input_schema`; test required input, extra fields, type mismatch and parameterless options. request_more_info enters `waiting_more_info`; answers require `delivery.decision_requests.answer`, business-brain/product scope and `answer_actor_selector`, then create new options/version and return to pending without resuming the subject. Cover cycles, duplicate dependency edges, acceptance coverage, reviewer separation, capacity, leases, cancellation Outbox/late-result fencing, high-risk cancel suspension and continue-to-ready with a new attempt/lease, rework attempts, plan versions, stale decisions, no-progress escalation, distinct AI employee/executor attribution, and platform-controlled recovery from `blocked/awaiting_human`.

Also cover one non-terminal run per version, concurrent idempotent start, current `product_versions.scope_version` returned by list/detail/grouping/conflict responses, `RD_SCOPE_VERSION_CONFLICT/RD_RUN_GENERATION_CONFLICT/RD_SCOPE_FROZEN/RD_SCOPE_CHANGE_INVALID/RD_ACTIVE_RUN_CONFLICT/RD_VERSION_POLICY_MERGE_REQUIRED/RD_RUN_RESTART_NOT_ALLOWED`, scope freeze at start, all included requirements having accepted assessments, version_resolved deterministic merge and exact immutable run-scope/source provenance, ordinary scope writes rejected while a non-terminal run exists, non-scope plan-version replanning, and the governed scope-change lifecycle. Test same/different request concurrency, stale scope/generation, each allowed and invalid operation, one pending request per version, pause from running/integrating/verifying, draft/planning scheduling fence, conflict with an existing waiting_human decision, and rejection restoring only the phase paused by this request. Approval must atomically revoke every old-generation lease/replay secret; cancel all non-terminal work items/current attempts/pending Reviews/linked AI tasks; cancel undispatched Runner/Git Outbox; write Runner cancellation and dispatched/unknown external-action reconciliation Outbox; terminalize the old run; apply all operations; and increment scope exactly once. Inject a failure at each boundary and assert full rollback; after commit, replay late submit/review/Runner completion/Git callback and assert audit/reconciliation only, with no old/new run transition. Then explicitly restart with returned `terminal_run_id` and assert new work items, attempts, leases and generation-isolated worktrees/branches. Also cover ready-target completed plus ready_for_release/deploying returning frozen/new-planning/follow-up-requirement resolution. Cover one active decision across pending/waiting-more-info including plan version 0, and run-level `waiting_human` recovery from each of `running/integrating/verifying` with `resume_state/suspended_decision_request_id/suspended_at` cleared after success. For failed/cancelled runs, assert the old run is immutable, product version keeps its active/testing phase, restart only targets the latest terminal generation with no active run, concurrent restart is idempotent, stale scope/policy/resources fail with no partial plan, and only revalidated approved evidence may be cited by new work items. For decision expiry, use database-time boundary tests, idempotent/concurrent scans, expired-at/event persistence, subject kept paused, successor escalation assignment, stale decide/answer rejection, and an explicit assertion that no option is auto-approved. Assert the public FastAPI `detail` error envelope and stable HTTP/details/retry/state contract for `RD_EXECUTION_POLICY_REQUIRED`, `RD_ROLE_ASSIGNMENT_REQUIRED`, `RD_EXECUTOR_UNAVAILABLE`, `RD_POLICY_HUMAN_DECISION_REQUIRED`, `RD_POLICY_RESOLUTION_LIMIT`, `RD_COLLABORATION_REQUIRED`, and `RD_SCOPE_CHANGE_INVALID`.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_runtime.py tests/test_rd_work_item_scheduler.py -q`

- [ ] **Step 3: Implement deterministic control plane**

LLM plans are JSON proposals only. The product version is the aggregate root: lock it during start, freeze immutable per-requirement scope and the version_resolved strategy snapshot plus exact sources, move it from `planning` to `active`, and return the same run for duplicate starts. Persist each plan version and validate scope, permissions, budgets, dependencies, role availability, and review separation before activation. Terminal runs never reopen; restart locks the version/latest terminal run and creates a new generation/scope/plan while preserving old rows. The scope-change service accepts only typed references, canonicalizes operations before hashing, and locks version/run/request/decision. `apply_scope_change_bundle` first fences the old run generation, scrubs/revokes leases and replay secrets, terminalizes every non-terminal work item/attempt/Review/AI task, cancels undispatched external Outbox intents, and writes Runner cancellation plus Git/Runner reconciliation Outbox rows. In the same database transaction it terminalizes the run, applies all typed operations, compare-and-increments scope exactly once, saves the applied version, events and audit; any failure rolls back the entire bundle. Provider workers stop/reconcile external actions asynchronously, but late results are checked against terminal run/generation/lease fences and become audit-only evidence. Restart creates generation-isolated worktrees, work items, attempts and leases; reject restores only the persisted valid phase. AI seats freeze both employee and executor identities. Claim stores only a secret reference in the immutable response and writes the encrypted token to the expiring replay-secret table; the scheduled scrubber nulls expired ciphertext and is safe to repeat. Suspending an item persists `resume_state`, attempt, decision/event, and release conditions; suspending a run atomically persists its source phase, decision request, timestamp, and optimistic version. Decision creation freezes expiry/escalation metadata; the collaboration maintenance worker expires and escalates without resuming or approving the subject. Only the scheduler or matching decision service may restore validated item/run states; clients never submit a recovery phase.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: orchestrate rd work item collaboration`.

### Task 10: Upgrade LangGraph to Durable Collaboration and Real Resume

**Files:**
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/uv.lock`
- Create: `apps/api/app/core/graph_checkpointer.py`
- Create: `apps/api/app/core/rd_collaboration_graph.py`
- Refactor: `apps/api/app/core/graph_runtime.py`
- Refactor: `apps/api/app/services/task_graph_runtime.py`
- Create: `apps/api/app/services/rd_collaboration_graph_runtime.py`
- Modify: `apps/api/tests/test_graph_runtime.py`
- Modify: `apps/api/tests/test_workflow_runtime_persistence.py`
- Create: `apps/api/tests/test_rd_collaboration_graph.py`

**Interfaces:**
- Produces: `build_checkpointer(settings)`, `build_ai_task_graph(checkpointer)`, and `build_rd_collaboration_graph(checkpointer)`.
- Produces: stable thread IDs `ai_task:{id}` and `rd_collaboration_run:{id}`.

- [ ] **Step 1: Write failing interrupt/resume tests**

```python
def test_collaboration_graph_resumes_from_persisted_checkpoint(graph, config):
    first = graph.invoke(initial_state(), config=config)
    assert first["current_step"] == "wait_work_item_events"
    resumed = graph.invoke(resume_command(event_id="event-1"), config=config)
    assert resumed["processed_event_ids"] == ["event-1"]


def test_domain_commit_survives_checkpoint_failure_without_duplicate_side_effects(runtime):
    runtime.fail_next_checkpoint_write()
    runtime.handle_event(event_id="event-1")
    runtime.handle_event(event_id="event-1")
    assert runtime.domain_transition_count("event-1") == 1
    assert runtime.outbox_count("event-1") == 1
    assert runtime.role_feedback_count(source_event_id="event-1") == 1
```

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_graph_runtime.py tests/test_workflow_runtime_persistence.py tests/test_rd_collaboration_graph.py -q`

- [ ] **Step 3: Add the official PostgreSQL checkpoint dependency and adapters**

Compile both graph types with a Checkpointer. Tests use a fresh in-memory saver; PostgreSQL runtime uses the configured checkpoint connection. Domain state, Inbox event, audit, Outbox, and feedback source event commit atomically through the collaboration repository; Checkpointer persistence is a separate execution-cursor commit. Every resumed node re-reads domain state and emits idempotent commands; feedback uses `save_role_feedback_once` and the database `(collaboration_run_id,feedback_fingerprint)` unique key, so checkpoint/domain partial failure, concurrent resume and event replay are safely retryable without duplicate feedback. Checkpoint incompatibility fails closed to human takeover.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: persist rd collaboration graph checkpoints`.

### Task 11: Connect Work Items to Existing AI Tasks, Agent Loop, Runner, and Quality Gates

**Files:**
- Modify: `apps/api/app/services/task_creation.py`
- Modify: `apps/api/app/services/task_start_execution.py`
- Modify: `apps/api/app/services/ai_executor_task_creation.py`
- Modify: `apps/api/app/services/agent_autonomy.py`
- Modify: `apps/api/app/services/ai_executor_runners.py`
- Modify: `apps/api/app/services/quality_gates.py`
- Create: `apps/api/tests/test_rd_work_item_execution.py`

**Interfaces:**
- Produces: internal-only `create_ai_task_for_work_item`, `dispatch_ai_task_for_work_item`, and `cancel_ai_task_for_work_item`; public work-item cancel calls the same `cancel_work_item_bundle`, completion/cancellation event projection, independent review creation, and rework attempt dispatch.
- Consumes: frozen role binding, execution context manifest, Agent Loop, Runner, quality gates, and work-item scheduler.

- [ ] **Step 1: Write failing execution integration tests**

Assert an AI work item creates one linked AI task through the internal service, freezes separate AI employee and executor IDs, uses only the frozen executor, coding success enters verification, passed review approves the work item, failed gate enters `rework_required` with the original attempt preserved, and duplicate Runner completion is idempotent. Assert low-risk cancel atomically revokes the lease, closes attempt/Review/task/item, recalculates run/dependencies and writes Runner cancellation Outbox. High-risk cancel must first revoke the lease, mark the attempt suspended, fence late results, write the Runner cancellation Outbox and pause the item before returning a decision request; approving cancel completes the aggregate, while rejecting/continuing revalidates and returns only to ready so a new claim creates a new attempt/lease. Late Runner completion cannot revive either path. Also assert public task create/start/cancel cannot invoke these services directly.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_work_item_execution.py tests/test_quality_gates.py tests/test_rd_task_executor_policies.py -q`

- [ ] **Step 3: Implement integration without changing scheduled jobs**

Project Runner, cancellation and review results into collaboration events through Outbox; physical Runner termination is asynchronous, while database lease revocation and late-result fencing are atomic. Never let scheduled-job execution create collaboration state directly.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: execute rd collaboration work items`.

### Task 12: Deliver the P0 Remote Git, Integration-Test, and Attribution Boundary

**Files:**
- Modify: `apps/api/app/services/product_version_release_readiness.py`
- Modify: `apps/api/app/services/product_version_delivery_overview.py`
- Modify: `apps/api/app/services/lifecycle_context.py`
- Modify: `apps/api/app/services/task_review_artifacts.py`
- Modify: `apps/api/app/services/knowledge_deposits.py`
- Create: `apps/api/app/services/rd_git_delivery.py`
- Modify: `apps/api/app/core/repositories/execution_governance.py`
- Modify: `apps/api/app/core/repositories/execution_governance_writes.py`
- Create: `apps/api/tests/test_rd_collaboration_delivery.py`
- Create: `apps/api/tests/test_rd_feedback_attribution.py`

**Interfaces:**
- Produces: `record_version_git_delivery`, `verify_version_git_delivery`, `record_ready_for_release_evidence`, and `finalize_ready_for_release_target`. Evidence recording always leaves the product version at `ready_for_release`; finalization completes the run only for `delivery_target=ready_for_release`, while a deployed target leaves the run in non-terminal `ready_for_release` for Task 12C.
- Produces immutable brain/product/run/role/seat/actor/executor/work-item/attempt/strategy-snapshot feedback records with `feedback_kind/source_event_id/feedback_fingerprint` for later experience governance.

- [ ] **Step 1: Write failing delivery-boundary tests**

Assert every coding item uses the minimum isolated worktree/branch path, the explicit integration item runs version-level tests, pushes through Outbox, and stores repository/branch/local SHA/remote SHA/MR-PR/outbox/reconciliation/test evidence. `record_ready_for_release_evidence` only verifies this immutable evidence and creates no push or deployment request; missing, stale, or mismatched remote/test evidence blocks completion. With `delivery_target=ready_for_release`, finalization leaves the product version at `ready_for_release`, completes the run with `completion_reason=ready_for_release`, and creates no deployment request. Add a contract test for `delivery_target=deployed` that leaves the version and run at `ready_for_release` with no completion_reason or deployment request; the P0 flag-disabled policy tests still reject creating that strategy, so this branch is a service contract consumed only by Task 12C. For feedback, replay the same persisted source event sequentially and concurrently and assert one row by `(collaboration_run_id,feedback_fingerprint)`; different feedback kinds or attributed subjects must produce distinct rows.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_delivery.py tests/test_rd_feedback_attribution.py -q`

- [ ] **Step 3: Implement delivery and attribution projections**

Reuse existing trusted delivery records, reconciliation, and Outbox. Separate evidence recording from target finalization and branch strictly on the frozen version_resolved `delivery_target`; never unconditionally close the run. Persist immutable `role_feedback_records` with business brain, product, collaboration run, feedback kind, persisted source event, attributed role/seat, attributed `human_user_id` or `ai_employee_id`, executor profile, work item, attempt, strategy snapshot, evidence references, and canonical feedback fingerprint. Compute the fingerprint from run generation, source event, feedback kind, attributed role/seat/subject, work item/attempt, and strategy snapshot, then call `save_role_feedback_once`; rely on the database unique key rather than a read-before-write race. Separately persist the actual feedback producer as `producer_subject_type/producer_subject_id/producer_role_code/producer_seat_id`; enforce subject-type checks and seat FKs, and never infer the producer from the attributed actor. Do not implement deployment in this P0 task and do not inject unreviewed feedback as experience.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: complete trusted rd delivery`.

### Task 12B: Add P1 Governed Role Experience Lifecycle and Reuse

**Files:**
- Create: `apps/api/app/api/routers/rd_role_experiences.py`
- Create: `apps/api/app/services/rd_role_experiences.py`
- Modify: `apps/api/app/core/repositories/rd_collaboration.py`
- Modify: `apps/api/app/core/repositories/rd_collaboration_writes.py`
- Modify: `apps/api/app/services/rd_collaboration_planning.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_rd_role_experiences.py`

**Interfaces:**
- Produces: paged/filterable `GET /api/delivery/rd-role-experiences`, detail GET, and `POST /api/delivery/rd-role-experiences/{id}/decide` with `decision/comment/version/idempotency_key`.
- Produces: `generate_role_experience_candidates`, `decide_role_experience`, and `retrieve_approved_role_experiences`.

- [ ] **Step 1: Write failing lifecycle, authorization, and retrieval tests**

Assert `RD_ROLE_EXPERIENCE_ENABLED=false` leaves P0 feedback and collaboration suites green while experience routes/candidate generation/injection remain disabled. With the P1 flag enabled, cover evidence-fingerprint deduplication, direct experience `strategy_snapshot_id` FK plus each source feedback snapshot FK, immutable versions, `pending -> approved/rejected`, `approved -> retired`, one approved version per experience key, reviewer permission plus business-brain/product scope, rejection when the reviewer produced any source feedback, extra role/seat separation when `require_independent_reviewer=true`, optimistic locking, stable audit events, and paged filters. List/detail queries must support and enforce business brain, product, role, work-item type, scenario, risk, repository/tool trust domain, minimum confidence, status, version, evidence subject, and current-caller permissions in the database query layer. For reuse, require both the platform flag and frozen `experience_reuse_config.enabled`; assert only approved non-retired records matching every scope, min confidence, max age, policy compatibility and trust domain are deterministically truncated by max items/context tokens and returned with experience ID/version/evidence references. Empty trust domains are deny-all; same_policy_version requires exact policy ID/version, while same_policy_schema remains same-brain/product/schema and cannot widen current constraints. Cross-brain/product, low-confidence, expired, trust-domain mismatch, permission-inaccessible, retired, or policy-conflicting experience must not enter the prompt or leak metadata.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_role_experiences.py tests/test_rd_feedback_attribution.py -q`

- [ ] **Step 3: Implement governance without automatic policy mutation**

Keep `role_feedback_records` immutable. Generate versioned `rd_role_experience_records` candidates; approve/reject/retire only through the governed API. Resolve every source feedback producer through relational source rows and reject any matching reviewer subject; when configured, also reject matching producer roles/seats. Inject approved experience as cited read-only context only after deterministic scope checks and frozen-config capacity limits. Experience may create a playbook or policy-change suggestion, but it cannot change active policy, permissions, budget, quality gates, or delivery target.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: govern rd role experience`.

### Task 12C: Add P1 Policy-Controlled Optional Deployment

**Files:**
- Modify: `apps/api/app/services/operational_deployments.py`
- Modify: `apps/api/app/services/product_version_delivery_overview.py`
- Create: `apps/api/tests/test_rd_collaboration_deployment.py`

**Interfaces:**
- Produces: `enter_policy_controlled_deployment` only after Task 12 has recorded trusted `ready_for_release` evidence and left a deployed-target run in non-terminal `ready_for_release`.

- [ ] **Step 1: Write failing optional-deployment boundary tests**

Assert `RD_COLLABORATION_DEPLOYMENT_ENABLED=false` rejects creation/activation of `delivery_target=deployed` without affecting P0 policy/UI/tests. With the P1 flag enabled, `delivery_target=deployed` consumes a run already in `ready_for_release`, creates a request only after readiness, scope, approval, rollback, and resource gates, and advances it to `deploying`. Rejection, failure, or rollback preserves the trusted `ready_for_release` delivery fact and returns/keeps the run there; success alone completes it with `completion_reason=deployed`. Existing deployment Outbox, authorization, and human gates remain authoritative.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_deployment.py tests/test_operational_deployments.py -q`

- [ ] **Step 3: Reuse the existing deployment domain**

Do not create a second deployment engine. Link the collaboration run to existing deployment requests/runs and project their terminal evidence back to the version/run without changing Task 12 remote Git records.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: add optional rd deployment`.

### Task 13A: Upgrade the P0 Web Workbench

**Files:**
- Refactor: `apps/web/src/pages/RdExecutorPolicies/index.tsx`
- Create: `apps/web/src/pages/RdExecutorPolicies/PolicyRoleBindings.tsx`
- Create: `apps/web/src/pages/RdExecutorPolicies/AiEmployeeCatalog.tsx`
- Create: `apps/web/src/pages/Requirements/RequirementAssessmentDrawer.tsx`
- Create: `apps/web/src/pages/IterationVersions/RequirementGroupingPanel.tsx`
- Create: `apps/web/src/pages/RdCollaboration/index.tsx`
- Create: `apps/web/src/pages/RdCollaboration/WorkItemDag.tsx`
- Create: `apps/web/src/pages/RdCollaboration/DecisionPanel.tsx`
- Modify: `apps/web/config/routes.ts`
- Modify: `apps/web/src/services/systemOperationsClient.ts`
- Modify: `apps/web/src/services/requirementClient.ts`
- Create: `apps/web/src/services/rdCollaborationClient.ts`
- Rewrite: `apps/web/tests/RdExecutorPoliciesPage.test.tsx`
- Modify: `apps/web/tests/RequirementsPage.test.tsx`
- Modify: `apps/web/tests/IterationVersionsPage.test.tsx`
- Create: `apps/web/tests/RdCollaborationPage.test.tsx`

**Interfaces:**
- Consumes: Tasks 4-12 P0 APIs only; Task 12B/12C are not prerequisites.
- Produces: one unified policy editor, AI digital employee catalog, assessment review, grouping explanation, collaboration DAG/board, role seats, work-item attempts, blockers, human decisions, immutable feedback attribution, and deployment-disabled `ready_for_release` completion.

- [ ] **Step 1: Write failing user-flow tests**

Test unified policy editing without old executor fields or version-level strategy override, separate AI employee/executor selection, full assessment opinion/answer/decision actions, existing-version grouping and version_resolved rationale/source evidence, absence of delivery-state batch advancement and public task-start/cancel controls, work-item review/rework/recovery, high-risk cancel continue-to-ready/new-attempt behavior, decision input Schema and answer qualification, RBAC read-only states, deployment-disabled completion with version/run status separation, and immutable feedback attribution. When P1 feature flags are disabled, the UI must not expose experience management or allow activating `delivery_target=deployed`.

- [ ] **Step 2: Verify red**

Run: `cd apps/web && npm test -- RdExecutorPoliciesPage.test.tsx RequirementsPage.test.tsx IterationVersionsPage.test.tsx RdCollaborationPage.test.tsx`

- [ ] **Step 3: Implement focused components and clients**

Keep page containers under architecture budgets. Display deterministic evidence and explicit human-decision impact; do not expose secrets, raw prompts, or provider credentials.

- [ ] **Step 4: Verify green, typecheck, lint, and commit**

Run:

```bash
cd apps/web
npm test -- RdExecutorPoliciesPage.test.tsx RequirementsPage.test.tsx IterationVersionsPage.test.tsx RdCollaborationPage.test.tsx
npm run typecheck
npm run lint
```

Then commit `feat: add rd collaboration workbench`.

### Task 13B: Add the P1 Experience and Optional-Deployment Workbench

**Files:**
- Create: `apps/web/src/pages/RdRoleExperiences/index.tsx`
- Create: `apps/web/src/pages/RdCollaboration/DeploymentPanel.tsx`
- Modify: `apps/web/src/pages/RdCollaboration/index.tsx`
- Modify: `apps/web/config/routes.ts`
- Create: `apps/web/src/services/rdRoleExperienceClient.ts`
- Create: `apps/web/tests/RdRoleExperiencesPage.test.tsx`
- Create: `apps/web/tests/RdCollaborationDeploymentPage.test.tsx`

**Interfaces:**
- Consumes: Task 12B and 12C P1 APIs only after their independent feature flags and backend suites are green.
- Produces: governed experience query/review/reuse evidence and a link to the existing deployment domain after P0 readiness; it does not create a second deployment engine.

- [ ] **Step 1: Write failing P1 user-flow tests**

Test experience pending/approved/rejected/retired filters, full brain/product/role/work-item/scenario/risk/trust/confidence scope, reviewer separation and decision/version conflicts. Test that deployed strategy activation is rejected while the P1 deployment flag is off; when enabled, the collaboration page only exposes the existing deployment request flow after P0 `ready_for_release` evidence and required human confirmation.

- [ ] **Step 2: Verify red**

Run: `cd apps/web && npm test -- RdRoleExperiencesPage.test.tsx RdCollaborationDeploymentPage.test.tsx`

- [ ] **Step 3: Implement P1 pages behind independent flags**

Keep P0 routes and tests runnable with both P1 flags disabled. Experience and deployment failures must not make the P0 workbench unavailable.

- [ ] **Step 4: Verify P1 green and commit**

Run the Step 2 command plus `npm run typecheck && npm run lint`, then commit `feat: add rd collaboration p1 workbench`.

### Task 14: Add Maintenance Fence, Upgrade Preflight, and Cutover Validation

**Files:**
- Create: `apps/api/app/db/migrations/121_requirement_driven_rd_cutover.sql`
- Create: `apps/api/app/services/rd_collaboration_migration.py`
- Create: `apps/api/app/services/rd_maintenance_fence.py`
- Create: `apps/api/app/api/routers/rd_migration.py`
- Create: `scripts/rd_collaboration_upgrade_check.py`
- Create: `scripts/rd_collaboration_cutover.py`
- Create: `apps/api/tests/test_rd_collaboration_migration.py`
- Create: `apps/api/tests/test_rd_maintenance_fence.py`

**Interfaces:**
- Produces: read-only advisory and locked preflight, version-locked maintenance-fence transitions `disabled -> draining -> cutover_locked -> disabled`, draining abort, deterministic policy-conversion preview, and an admin-only cutover command that refuses active tasks, active Agent Loops, active Runner tasks, policy conflicts, missing roles, or invalid resources.
- Produces: migration 121 as the final cleanup contract; number 110 is occupied by the additive unified-policy migration, so cleanup keeps its own non-registered sequence number and runs only after cutover sets `rd_collaboration_schema_version=2` and records the new-application health marker.

- [ ] **Step 1: Write failing preflight tests**

```python
def test_upgrade_preflight_blocks_active_ai_task(store):
    report = build_upgrade_preflight(store)
    assert report["ready"] is False
    assert report["blockers"][0]["code"] == "RD_UPGRADE_ACTIVE_TASKS"


def test_maintenance_fence_blocks_rd_writes_but_not_scheduled_jobs(client, admin_headers):
    set_rd_fence(client, admin_headers, mode="draining")
    assert start_ai_task(client, admin_headers).status_code == 423
    assert run_scheduled_job(client, admin_headers).status_code != 423


def test_draining_allows_inflight_completion_and_abort_before_cutover(client, admin_headers):
    set_rd_fence(client, admin_headers, mode="draining")
    assert complete_already_claimed_task(client).status_code == 200
    assert admin_drain_cancel(client, admin_headers).status_code == 200
    assert set_rd_fence(client, admin_headers, mode="disabled", reason="preflight blocker").status_code == 200


def test_cutover_locked_cannot_abort_to_old_runtime(client, admin_headers):
    set_rd_fence(client, admin_headers, mode="draining")
    mark_zero_active_and_backup_complete()
    set_rd_fence(client, admin_headers, mode="cutover_locked")
    response = set_rd_fence(client, admin_headers, mode="disabled", reason="try rollback")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RD_UPGRADE_ABORT_NOT_ALLOWED"


def test_destructive_cleanup_is_not_in_automatic_migration_registry():
    assert "121_requirement_driven_rd_cutover.sql" not in registered_migration_names()


def test_fence_can_open_only_after_v2_workers_and_smoke_write_are_healthy(client, admin_headers):
    response = set_rd_fence(client, admin_headers, mode="disabled")
    assert response.status_code == 409
    mark_cleanup_worker_and_smoke_checks_successful()
    assert set_rd_fence(client, admin_headers, mode="disabled").status_code == 200
    assert start_v2_assessment(client, admin_headers).status_code != 423
    assert legacy_generate_task(client, admin_headers).status_code == 409
```

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_migration.py tests/test_rd_maintenance_fence.py -q`

- [ ] **Step 3: Implement maintenance-fenced preflight and one-way cutover**

The API and scripts never deploy. Run advisory preflight while `fence_mode=disabled`; it returns a deterministic conversion preview and blocks any active policy without a nonempty unified strategy, which an administrator must explicitly complete through the single policy API before draining so the platform never guesses a team or executor mapping. Then enter `draining` with `reason/version`: block new requirement approval/rejection/direct task generation, AI task start/retry, policy/collaboration/experience writes, and Runner claims while leaving scheduled jobs unchanged. Allow already claimed work and in-flight transactions to commit terminal callbacks, and allow only the audited admin drain-cancel service to cancel remaining work. Before Schema v2 activation or cleanup starts, a version-locked draining abort may return to disabled; test that it restores the old write path without changing schema. After active tasks/Agent Loops/Runner leases/collaboration commands reach zero and a backup marker exists, atomically enter `cutover_locked` and rerun locked preflight. From cutover_locked onward, abort to the old runtime is forbidden; failures retry forward. Set Schema v2, start the new application with old columns still present, validate health, then record the health marker. Migration 121 is destructive and must be executed explicitly by `rd_collaboration_cutover.py cleanup` as one SQL transaction after that marker; do not register it in the automatic additive compatibility runner. After cleanup, resume v2 workers, verify worker/schema/graph-version equality, execute v2 assessment and collaboration write smoke tests, and only then set the fence to disabled with the expected schema version and health marker. Any locked failure remains cutover_locked and retryable. After release, v2 writes succeed while all legacy write paths remain rejected.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command plus `python3 scripts/rd_collaboration_upgrade_check.py --help` and `python3 scripts/rd_collaboration_cutover.py --help`, then commit `feat: validate rd collaboration cutover`.

### Task 15: Update Help, Regression Coverage, Browser Evidence, and Remote Branch

**Files:**
- Modify: `docs/08-help/delivery.md`
- Modify: `docs/08-help/tasks-and-governance.md`
- Modify: `docs/08-help/README.md`
- Add/update: `docs/08-help/assets/screenshots/help-requirements.png`
- Add/update: `docs/08-help/assets/screenshots/help-versions.png`
- Add/update: `docs/08-help/assets/screenshots/help-rd-executor-policies.png`
- Add: `docs/08-help/assets/screenshots/help-rd-collaboration.png`
- Add: `docs/08-help/assets/screenshots/help-rd-role-experiences.png`
- Modify: `docs/changelog.md`
- Modify: `scripts/full_chain_regression.py`

**Interfaces:**
- Produces: user-facing operation manual, screenshots, full-chain evidence, and final branch handoff.

- [ ] **Step 1: Extend full-chain regression**

The required P0 chain covers requirement submission; rejection of assessment `strategy_id`; assigned opinions, qualified answers, structured decision input and all assessment decisions; compatible planning-version selection; two requirements with different final payloads deterministically merged into one version_resolved snapshot with immutable exact run-scope/source coverage; immutable policy snapshot/hash/schema references; claim token replay-before-expiry and ciphertext scrub-after-expiry; distinct AI employee/executor identity; collaboration DAG; work-item blocked/human-wait recovery and low/high-risk cancel including continue-to-ready/new-attempt; run-level recovery from `running/integrating/verifying`; database-time decision expiry that keeps the subject paused and creates one successor without auto-approval; failed/cancelled terminal-run restart to a new generation with old evidence immutable; internal AI work-item execution and retry; independent review; rework; version-level integration tests; reconciled remote branch/commit/MR-PR evidence; product version `ready_for_release`; ready-target run `completed/completion_reason=ready_for_release`; deployment-disabled stop; and immutable actor/executor/work-item/attempt/snapshot feedback attribution. It also verifies Bug/code-inspection/assistant legacy entry adapters create requirements rather than AI tasks, delivery-state batch advancement and public AI-task create/start/batch-retry/cancel are rejected, maintenance draining/abort/cutover-locked/release restores only v2 writes, and a representative scheduled job retains its pre-upgrade definition, schedule, Agent/Skill snapshot, and run semantics. A separate P1 extension suite covers experience candidate approval/query/retirement plus frozen-config-bound approved-context reuse, and optional deployment consuming a non-terminal ready_for_release run; P1 failure does not redefine P0 completion, while each released phase must pass its own suite.

- [ ] **Step 2: Run focused backend and frontend suites**

For P0, run Tasks 2-12 and 13A tests plus existing requirement, version, policy, workflow, quality-gate and Runner suites; do not require Task 12B/12C/13B files or deployment/experience feature flags. For a P1 release, separately run Task 12B/12C/13B experience and deployment suites in addition to the already-green P0 gate. Expected: the selected phase's focused suites all pass, and P1 failure never retroactively changes P0 completion evidence.

- [ ] **Step 3: Run full suites and preserve known-baseline accounting**

First verify the frozen HEAD/patch/status/untracked manifests still match the pre-implementation capture. Run `cd apps/api && uv run pytest` and `cd apps/web && npm test`; all suites must pass with no failure allowlist. Any failure blocks completion and requires a fix, stable manifest recapture, and a full rerun; scheduled-job failures are especially non-waivable because that domain is an unchanged boundary.

- [ ] **Step 4: Validate the real PostgreSQL-backed UI**

Start the real stack, log in with `admin`, `product_owner`, `rd_owner`, and `tester` as applicable, and validate the P0 routes `/delivery/requirements`, `/delivery/versions`, `/delivery/rd-executor-policies`, `/delivery/rd-collaboration`, task detail, decisions, qualified answers, cancellation recovery, version-resolved evidence and deployment-disabled completion. Confirm non-blank render, exact role permissions, no stale UI, and no console/runtime/network errors. Only during a P1 release, additionally validate the flagged experience page and existing deployment flow.

- [ ] **Step 5: Update help screenshots and docs**

Capture real UI screenshots with secrets and personal data masked. Run `cd apps/web && npm run help:check`.

- [ ] **Step 6: Commit, push, and do not deploy**

Run final diff review, commit remaining docs/tests, and push the current `codex/` branch to origin. Do not create or execute a deployment request.

## Plan Self-Review

- Every approved design section maps to Tasks 1-15.
- Unified policy has one API and one page; Task 2 only adds compatible schema, Task 4 rejects old writes, and Task 14 clears legacy R&D command records after maintenance-fenced cutover. Physical column compaction requires a separately reviewed retention window.
- Requirement assessment resolves policy before and after AI evaluation in Tasks 4 and 6; no caller can inject `strategy_id`, and policy changes require re-evaluation.
- Version grouping is deterministic and idempotent in Task 7; Tasks 2-4/9 create one version_resolved snapshot plus immutable run requirement scope with deferred-validated exact provenance for every run.
- Direct R&D entry bypasses are converted to requirement adapters in Task 8.
- Public delivery-state batch advancement and AI-task create/start/retry/cancel bypasses are rejected in Task 8; internal work-item services are integrated in Task 11.
- Human/AI roles, persistent AI employee identity, executor separation, RBAC separation, seats, sessions, DAG, review, recovery, rework, structured decisions, qualified answers, decision expiry escalation, terminal-run restart, cancellation-specific ready/new-lease recovery, and attribution are covered by Tasks 2, 3, 5, 9, 11, and 12.
- Immutable `rd_task_executor_policy_snapshots`, version source relations, their foreign keys/deferred constraint triggers, merge operators, hash/schema validation, and uniqueness constraints are covered by Tasks 2-4 and 9.
- Permanent command idempotency and expiring/scrubbable claim replay secrets are separately modeled and tested in Tasks 2, 3, and 9.
- Run-level pause/resume metadata and recovery tests for `running/integrating/verifying` are covered by Tasks 2, 3, 9, and 10.
- Governed experience lifecycle, query/decision APIs, reviewer separation from every source, versions, and frozen `experience_reuse_config` retrieval limits are covered by Tasks 4 and P1 Tasks 12B/13B; P0 Task 13A has no dependency on experience runtime or Task 12C deployment.
- Existing LangGraph is reused and upgraded with a PostgreSQL Checkpointer in Task 10; domain state and event Inbox remain the consistency source.
- Scheduled-job engine behavior is explicitly unchanged in Global Constraints, Tasks 8, 11, 14, and 15.
- P0 delivery in Task 12 includes isolated branches, remote Git Outbox/reconciliation, version-level tests, and trusted evidence. Target finalization completes only ready-for-release runs; deployed-target runs remain non-terminal `ready_for_release` for explicit P1 Task 12C deployment.
- Additive schema, advisory preflight, draining/early abort, zero-active cutover lock, locked preflight, policy conversion, draft cancellation, one-way activation, cleanup, v2 Worker/smoke verification, and safe fence release are covered by Tasks 2 and 14.
- No stale baseline is trusted. Implementation begins only after a stable double-captured HEAD/patch/status/untracked manifest and green scheduled-job suites; any snapshot drift requires recapture before feature work continues.
- No implementation step contains an unresolved placeholder.
