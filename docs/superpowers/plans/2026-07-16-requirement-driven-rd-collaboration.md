# Requirement-Driven R&D Collaboration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing R&D execution policy and workflow into one requirement-driven human/AI collaboration flow from assessment and iteration planning through development, testing, remote Git delivery, and policy-controlled deployment.

**Architecture:** Keep PostgreSQL as the sole business-state source and reuse the existing LangGraph, AI task, Agent Loop, Runner, quality-gate, Outbox, and deployment foundations. Replace the task-type executor policy contract with one versioned strategy plus role bindings, add requirement assessment and iteration grouping, then add a version-level collaboration graph whose durable work-item DAG is scheduled deterministically.

**Tech Stack:** FastAPI, Python 3.11+, PostgreSQL, LangGraph with PostgreSQL Checkpointer, React 19, TypeScript, Ant Design Pro, pytest, Vitest, Playwright/browser validation.

## Global Constraints

- Product requirement is the only R&D entry; Bug, code inspection, feedback, and online incidents must create or link a requirement first.
- Accepted requirements join a compatible `planning` version first; create a new `planning` version only when none is eligible.
- Upgrade `rd_task_executor_policies` in place; do not expose legacy/new modes or a second policy menu.
- Scheduled jobs, scheduled-job runs, locks, retries, snapshots, Agent/Skill assembly, and history remain unchanged.
- LLM output is a proposal; deterministic services own state, DAG validation, leases, permissions, budgets, idempotency, and risk floors.
- High/critical risk, permission expansion, protected branches, production changes, and policy conflicts require human confirmation.
- New policies default to `delivery_target=ready_for_release` and deployment disabled.
- AI roles use only executor profiles and role bindings frozen in the strategy snapshot.
- R&D role definitions never grant RBAC permissions; human assignment separately checks permissions and product scope.
- Coding success is not completion; independent quality evidence and reviewer separation are mandatory.
- All new production behavior starts with a failing test and follows red-green-refactor.
- Do not deploy. Completion for this development branch is tests, browser validation, documentation, commit, and remote push.
- Known baseline before this plan: backend full suite has 2 unrelated architecture line-budget failures; frontend full suite has 18 unrelated Plugin/ScheduledJobs failures. Focused R&D suites must pass, and final reporting must preserve these baseline failures until separately repaired.

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
- Produces: active source-of-truth requirements and exact names used by migrations, APIs, services, tests, and pages in Tasks 2-12.
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
```

Expected: no active statement permits bypassing assessment or falling back outside the unified policy.

- [ ] **Step 5: Commit**

```bash
git add docs/01-prd docs/02-specs docs/glossary.md
git commit -m "docs: adopt requirement-driven rd collaboration"
```

### Task 2: Add the Unified Collaboration Schema and Direct Migration

**Files:**
- Create: `apps/api/app/db/migrations/109_requirement_driven_rd_collaboration.sql`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/store.py`
- Modify: `apps/api/tests/test_persistence_repository_boundaries.py`
- Create: `apps/api/tests/test_requirement_driven_rd_schema.py`

**Interfaces:**
- Produces: `rd_role_definitions`, `rd_executor_profiles`, `rd_task_executor_policy_role_bindings`, `requirement_assessments`, `requirement_assessment_opinions`, `rd_collaboration_runs`, `rd_run_seats`, `rd_role_sessions`, `rd_work_items`, `rd_work_item_dependencies`, `rd_work_item_attempts`, `rd_collaboration_events`, `decision_requests`, and `role_feedback_records`.
- Produces: generalized graph subjects, policy/version references, version delivery statuses, and work-item linkage on `ai_tasks`.

- [ ] **Step 1: Write failing migration-contract tests**

```python
def test_requirement_driven_collaboration_migration_is_registered():
    migrations = registered_migration_names()
    assert "109_requirement_driven_rd_collaboration.sql" in migrations


def test_new_collaboration_tables_have_standard_timestamps(migration_sql):
    for table in ("rd_role_definitions", "requirement_assessments", "rd_work_items"):
        assert_table_has_created_and_updated_at(migration_sql, table)
```

- [ ] **Step 2: Run the test and confirm red**

Run: `cd apps/api && uv run pytest tests/test_requirement_driven_rd_schema.py tests/test_persistence_repository_boundaries.py -q`

Expected: FAIL because migration 109 and new collections are absent.

- [ ] **Step 3: Add normalized tables, constraints, indexes, and direct policy conversion**

The migration must convert each old task executor row into a strategy plus its first role binding, seed safe defaults, mark incomplete strategies `invalid`, cancel legacy draft AI tasks with `superseded_by_v2_migration`, require zero active tasks before destructive column removal, and retain immutable historical snapshots only for audit.

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
- Produces: list/get/save methods for roles, executor profiles, unified policies and bindings, assessments/opinions, collaboration runs, seats, sessions, work items/dependencies/attempts/events, decisions, and feedback.
- Produces: `save_assessment_bundle`, `assign_requirement_to_version`, `claim_ready_work_item`, `save_work_item_attempt_bundle`, and `apply_decision_bundle` transaction methods.

- [ ] **Step 1: Write failing repository transaction tests**

```python
def test_claim_ready_work_item_is_atomic(repository, ready_work_item):
    first = repository.claim_ready_work_item(ready_work_item["id"], lease_owner="worker-a")
    second = repository.claim_ready_work_item(ready_work_item["id"], lease_owner="worker-b")
    assert first["lease_owner"] == "worker-a"
    assert second is None
```

Cover optimistic decisions, DAG edge uniqueness, plan-version uniqueness, assessment-version uniqueness, and requirement/version assignment idempotency.

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
- Produces: `resolve_work_item_binding(policy_snapshot, *, role_code, task_type) -> dict`.
- API remains `/api/delivery/rd-task-executor-policies` but accepts one strategy payload with `assessment_config`, `iteration_config`, `delivery_target`, `team_config`, `autonomy_config`, `quality_gate_config`, `git_config`, `deployment_config`, and `role_bindings`.

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

Also assert old top-level `task_type/executor_type/runner_id` fields are rejected and no fallback executor is used.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_task_executor_policies.py tests/test_management_list_read_models.py -q`

Expected: FAIL because the API still requires the old per-task fields.

- [ ] **Step 3: Split validation, resolution, persistence, and Runner payload responsibilities**

Keep each service focused. Initial resolution uses stable requirement fields only; final resolution can only retain or strengthen risk and automation boundaries. Work-item resolution requires exactly one active role binding.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: upgrade rd execution policy` with only policy and focused test files.

### Task 5: Add R&D Role Definitions and Executor Profiles

**Files:**
- Create: `apps/api/app/api/routers/rd_organization.py`
- Create: `apps/api/app/services/rd_role_definitions.py`
- Create: `apps/api/app/services/rd_executor_profiles.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_rd_organization.py`

**Interfaces:**
- Produces: CRUD under `/api/delivery/rd-roles` and `/api/delivery/rd-executor-profiles`.
- Produces: `qualify_human_actor(user, *, role_definition, product_id) -> bool` and `qualify_ai_actor(profile, *, role_definition, policy_binding) -> bool`.

- [ ] **Step 1: Write failing RBAC-separation tests**

```python
def test_creating_rd_role_does_not_grant_system_permission(client, admin_headers):
    role = client.post("/api/delivery/rd-roles", headers=admin_headers, json=role_payload()).json()["data"]
    assert role["system_role_id"] is None
    assert "granted_permissions" not in role
```

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_organization.py -q`

- [ ] **Step 3: Implement scoped CRUD and qualification**

Human seats must pass existing RBAC and product scope. AI profiles use service identity, trust domain, tool policy, and execution-resource grants; neither path stores secrets.

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
- Produces: `POST /api/requirements/{id}/assess`, assessment detail, submit-opinion, answer-info, and decision endpoints.
- Produces: `start_requirement_assessment`, `record_assessment_opinion`, `finalize_requirement_assessment`.
- Consumes: initial/final policy resolution from Task 4 and role/executor qualification from Task 5.

- [ ] **Step 1: Write failing assessment state tests**

```python
def test_assessment_resolves_initial_policy_before_ai_roles(client, submitted_requirement):
    response = start_assessment(client, submitted_requirement["id"])
    assessment = response.json()["data"]
    assert assessment["initial_policy_snapshot"]["id"] == "policy_product"
    assert assessment["status"] == "evaluating"
```

Cover needs-info, rework, accepted, deferred, rejected, risk floor, policy strengthening, human conflict, and idempotent repeated start.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_requirement_assessments.py -q`

- [ ] **Step 3: Implement assessment orchestration**

Create one opinion request per required role. AI roles create internal AI tasks using the selected executor binding; human roles create pending decisions. Finalization requires all mandatory opinions and stores evidence, confidence, cost, actor, and executor attribution.

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

- [ ] **Step 1: Write failing grouping tests**

```python
def test_accepted_requirement_prefers_compatible_planning_version(store):
    result = plan_accepted_requirement(store, requirement_id="req-1", assessment_id="assessment-1", actor_id="system")
    assert result["version_id"] == "version-planning-compatible"
    assert result["created_version"] is False
```

Cover no candidate, tied candidates requiring human decision, capacity, policy mismatch, concurrent replay, and refusal to mutate active/testing versions.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_requirement_iteration_grouping.py tests/test_iteration_version_status_flow.py -q`

- [ ] **Step 3: Implement deterministic grouping and new states**

Use a transaction lock on requirement and candidate versions. Add `ready_for_release/deploying` version transitions and keep `ready_for_release` distinct from `released`.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command plus `tests/test_requirement_batch_schedule.py`, then commit `feat: group accepted requirements into iterations`.

### Task 8: Implement Work-Item DAG, Seats, Decisions, Rework, and Feedback

**Files:**
- Create: `apps/api/app/api/routers/rd_collaboration.py`
- Create: `apps/api/app/services/rd_collaboration_planning.py`
- Create: `apps/api/app/services/rd_work_item_scheduler.py`
- Create: `apps/api/app/services/rd_collaboration_decisions.py`
- Create: `apps/api/app/services/rd_feedback_attribution.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_rd_collaboration_runtime.py`
- Create: `apps/api/tests/test_rd_work_item_scheduler.py`

**Interfaces:**
- Produces: collaboration-run start/detail, plan/replan, work-item claim/complete/block, review/rework, event, and decision APIs.
- Produces: `validate_work_item_plan`, `ready_work_items`, `claim_work_item`, `complete_attempt`, and `apply_decision`.

- [ ] **Step 1: Write failing DAG and scheduling tests**

```python
def test_scheduler_does_not_release_item_before_dependencies_are_approved(store):
    items = ready_work_items(store, collaboration_run_id="run-1")
    assert "integration-item" not in {item["id"] for item in items}
```

Cover cycles, acceptance coverage, reviewer separation, capacity, leases, rework attempts, plan versions, stale decisions, and no-progress escalation.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_runtime.py tests/test_rd_work_item_scheduler.py -q`

- [ ] **Step 3: Implement deterministic control plane**

LLM plans are JSON proposals only. Persist each plan version and validate scope, permissions, budgets, dependencies, role availability, and review separation before activation.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: orchestrate rd work item collaboration`.

### Task 9: Upgrade LangGraph to Durable Collaboration and Real Resume

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
```

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_graph_runtime.py tests/test_workflow_runtime_persistence.py tests/test_rd_collaboration_graph.py -q`

- [ ] **Step 3: Add the official PostgreSQL checkpoint dependency and adapters**

Compile both graph types with a Checkpointer. Tests use a fresh in-memory saver; PostgreSQL runtime uses the configured repository connection. Event IDs are deduplicated and checkpoint incompatibility fails closed to human takeover.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: persist rd collaboration graph checkpoints`.

### Task 10: Connect Work Items to Existing AI Tasks, Agent Loop, Runner, and Quality Gates

**Files:**
- Modify: `apps/api/app/services/task_creation.py`
- Modify: `apps/api/app/services/task_start_execution.py`
- Modify: `apps/api/app/services/ai_executor_task_creation.py`
- Modify: `apps/api/app/services/agent_autonomy.py`
- Modify: `apps/api/app/services/ai_executor_runners.py`
- Modify: `apps/api/app/services/quality_gates.py`
- Create: `apps/api/tests/test_rd_work_item_execution.py`

**Interfaces:**
- Produces: `create_ai_task_for_work_item`, completion event projection, independent review creation, and rework attempt dispatch.
- Consumes: frozen role binding, execution context manifest, Agent Loop, Runner, quality gates, and work-item scheduler.

- [ ] **Step 1: Write failing execution integration tests**

Assert an AI work item creates one linked AI task, uses only the frozen role executor, coding success enters verification, passed review approves the work item, failed gate creates rework, and duplicate Runner completion is idempotent.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_work_item_execution.py tests/test_quality_gates.py tests/test_rd_task_executor_policies.py -q`

- [ ] **Step 3: Implement integration without changing scheduled jobs**

Project Runner and review results into collaboration events through Outbox; never let scheduled-job execution create collaboration state directly.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: execute rd collaboration work items`.

### Task 11: Integrate Policy-Controlled Delivery and Feedback Attribution

**Files:**
- Modify: `apps/api/app/services/product_version_release_readiness.py`
- Modify: `apps/api/app/services/operational_deployments.py`
- Modify: `apps/api/app/services/product_version_delivery_overview.py`
- Modify: `apps/api/app/services/lifecycle_context.py`
- Modify: `apps/api/app/services/task_review_artifacts.py`
- Modify: `apps/api/app/services/knowledge_deposits.py`
- Create: `apps/api/tests/test_rd_collaboration_delivery.py`
- Create: `apps/api/tests/test_rd_feedback_attribution.py`

**Interfaces:**
- Produces: `complete_collaboration_at_ready_for_release` and `enter_policy_controlled_deployment`.
- Produces: role/actor/executor/attempt feedback records and governed experience candidates.

- [ ] **Step 1: Write failing delivery-boundary tests**

Assert `ready_for_release` pushes the remote development branch and creates no deployment request, while `deployed` creates a request only after readiness, scope, approval, and rollback gates.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_delivery.py tests/test_rd_feedback_attribution.py -q`

- [ ] **Step 3: Implement delivery and attribution projections**

Reuse existing deployment requests/runs and Outbox. Experience records remain candidates until governance approval and cannot mutate live policy automatically.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command and existing deployment tests, then commit `feat: complete policy-controlled rd delivery`.

### Task 12: Upgrade the Web Workbench

**Files:**
- Refactor: `apps/web/src/pages/RdExecutorPolicies/index.tsx`
- Create: `apps/web/src/pages/RdExecutorPolicies/PolicyRoleBindings.tsx`
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
- Consumes: Tasks 4-11 APIs.
- Produces: one unified policy editor, assessment review, grouping explanation, collaboration DAG/board, role seats, work-item attempts, blockers, and human decisions.

- [ ] **Step 1: Write failing user-flow tests**

Test unified policy editing without old executor fields, requirement assessment decisions, existing-version grouping rationale, work-item review/rework, RBAC read-only states, and deployment-disabled completion.

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

### Task 13: Add Upgrade Preflight and Cutover Validation

**Files:**
- Create: `apps/api/app/services/rd_collaboration_migration.py`
- Create: `apps/api/app/api/routers/rd_migration.py`
- Create: `scripts/rd_collaboration_upgrade_check.py`
- Create: `apps/api/tests/test_rd_collaboration_migration.py`

**Interfaces:**
- Produces: read-only preflight report and an admin-only cutover command that refuses active tasks, active Agent Loops, active Runner tasks, policy conflicts, missing roles, or invalid resources.

- [ ] **Step 1: Write failing preflight tests**

```python
def test_upgrade_preflight_blocks_active_ai_task(store):
    report = build_upgrade_preflight(store)
    assert report["ready"] is False
    assert report["blockers"][0]["code"] == "RD_UPGRADE_ACTIVE_TASKS"
```

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_migration.py -q`

- [ ] **Step 3: Implement deterministic preflight and rollback-safe cutover**

The API and script must never deploy. They validate database state, generate remediation details, and write audit events; destructive migration remains a checked migration transaction.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command and `python scripts/rd_collaboration_upgrade_check.py --help`, then commit `feat: validate rd collaboration upgrade`.

### Task 14: Update Help, Regression Coverage, Browser Evidence, and Remote Branch

**Files:**
- Modify: `docs/08-help/delivery.md`
- Modify: `docs/08-help/tasks-and-governance.md`
- Modify: `docs/08-help/README.md`
- Add/update: `docs/08-help/assets/screenshots/help-requirements.png`
- Add/update: `docs/08-help/assets/screenshots/help-versions.png`
- Add/update: `docs/08-help/assets/screenshots/help-rd-executor-policies.png`
- Add: `docs/08-help/assets/screenshots/help-rd-collaboration.png`
- Modify: `docs/changelog.md`
- Modify: `scripts/full_chain_regression.py`

**Interfaces:**
- Produces: user-facing operation manual, screenshots, full-chain evidence, and final branch handoff.

- [ ] **Step 1: Extend full-chain regression**

Cover requirement submission, assessment, compatible planning-version selection, policy snapshot, collaboration DAG, AI work item, independent review, rework, remote branch evidence, `ready_for_release`, deployment-disabled stop, and audit/feedback attribution.

- [ ] **Step 2: Run focused backend and frontend suites**

Run all new tests plus existing requirement, version, policy, workflow, quality-gate, Runner, and deployment tests. Expected: all focused tests pass.

- [ ] **Step 3: Run full suites and preserve known-baseline accounting**

Run `cd apps/api && uv run pytest` and `cd apps/web && npm test`. Any failure not identical to the recorded baseline blocks completion. Existing baseline failures must be reported until independently fixed.

- [ ] **Step 4: Validate the real PostgreSQL-backed UI**

Start the real stack, log in with `admin`, `product_owner`, `rd_owner`, and `tester` as applicable, and validate `/delivery/requirements`, `/delivery/versions`, `/delivery/rd-executor-policies`, `/delivery/rd-collaboration`, task detail, decisions, and deployment-disabled completion. Confirm non-blank render, exact role permissions, no stale UI, and no console/runtime/network errors.

- [ ] **Step 5: Update help screenshots and docs**

Capture real UI screenshots with secrets and personal data masked. Run `cd apps/web && npm run help:check`.

- [ ] **Step 6: Commit, push, and do not deploy**

Run final diff review, commit remaining docs/tests, and push the current `codex/` branch to origin. Do not create or execute a deployment request.

## Plan Self-Review

- Every approved design section maps to Tasks 1-14.
- Unified policy has one API and one page; old top-level executor fields are removed in Task 2 and rejected in Task 4.
- Requirement assessment resolves policy before and after AI evaluation in Tasks 4 and 6.
- Version grouping is deterministic and idempotent in Task 7.
- Human/AI roles, RBAC separation, seats, sessions, DAG, review, rework, decisions, and attribution are covered by Tasks 5, 8, 10, and 11.
- Existing LangGraph is reused and upgraded with a PostgreSQL Checkpointer in Task 9.
- Scheduled jobs are explicitly unchanged in Global Constraints, Tasks 10 and 14.
- Delivery ends at `ready_for_release` by default and enters deployment only through policy in Task 11.
- Direct migration, zero-active-task preflight, draft cancellation, and cutover validation are covered by Tasks 2 and 13.
- No implementation step contains an unresolved placeholder.
