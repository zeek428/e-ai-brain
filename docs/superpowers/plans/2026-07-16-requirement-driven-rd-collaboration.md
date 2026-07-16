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
- P0 human assignment uses explicit user IDs; team pools, calendars, and capacity-based automatic selection are not inferred.
- Requirement `batch-advance-status` may only cancel/close when no active collaboration work exists; all delivery targets and external AI-task create/start/batch-retry calls return `RD_COLLABORATION_REQUIRED`.
- `blocked/awaiting_human` work items persist a platform-controlled `resume_state`; clients cannot choose arbitrary recovery states.
- Default delivery leaves the product version at `ready_for_release` and completes the collaboration run with `completion_reason=ready_for_release`.
- Coding success is not completion; independent quality evidence and reviewer separation are mandatory.
- All new production behavior starts with a failing test and follows red-green-refactor.
- Do not deploy. Completion for this development branch is tests, browser validation, documentation, commit, and remote push.
- Use additive schema migration before implementation and a maintenance-fenced destructive cutover only after preflight; there is still one runtime rule after activation.
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
- Produces: active source-of-truth requirements and exact names used by migrations, APIs, services, tests, and pages in Tasks 2-14.
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
- Produces: `rd_role_definitions`, `rd_ai_employees`, `rd_executor_profiles`, `rd_task_executor_policy_role_bindings`, `requirement_assessments`, `requirement_assessment_opinions`, `rd_collaboration_runs`, `rd_run_seats`, `rd_role_sessions`, `rd_work_items`, `rd_work_item_dependencies`, `rd_work_item_attempts`, `rd_collaboration_events`, `decision_requests`, `role_feedback_records`, and `rd_collaboration_upgrade_state`.
- Produces: generalized graph subjects, policy/version references, version delivery statuses, work-item linkage on `ai_tasks`, and `rd_collaboration_upgrade_state` maintenance/cutover metadata.

- [ ] **Step 1: Write failing migration-contract tests**

```python
def test_requirement_driven_collaboration_migration_is_registered():
    migrations = registered_migration_names()
    assert "109_requirement_driven_rd_collaboration.sql" in migrations


def test_new_collaboration_tables_have_standard_timestamps(migration_sql):
    for table in ("rd_role_definitions", "rd_ai_employees", "requirement_assessments", "rd_work_items"):
        assert_table_has_created_and_updated_at(migration_sql, table)
```

- [ ] **Step 2: Run the test and confirm red**

Run: `cd apps/api && uv run pytest tests/test_requirement_driven_rd_schema.py tests/test_persistence_repository_boundaries.py -q`

Expected: FAIL because migration 109 and new collections are absent.

- [ ] **Step 3: Add normalized tables, constraints, indexes, and compatibility-safe columns**

Migration 109 is additive only: create canonical tables and indexes including stable AI employee identity, add work-item `resume_state`/suspension metadata and collaboration `completion_reason`, add nullable graph/version/task links, seed permission definitions including `delivery.rd_ai_employees.manage`, and add cutover-state metadata. It must not convert policies, cancel tasks, change API behavior, or remove old columns; those actions happen only after maintenance fencing and preflight in Task 14.

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
- Produces: list/get/save methods for roles, AI digital employees, executor profiles, unified policies and bindings, assessments/opinions, collaboration runs, seats, sessions, work items/dependencies/attempts/events, decisions, and feedback.
- Produces: `save_assessment_bundle`, `assign_requirement_to_version`, `claim_ready_work_item`, `save_work_item_attempt_bundle`, and `apply_decision_bundle` transaction methods.

- [ ] **Step 1: Write failing repository transaction tests**

```python
def test_claim_ready_work_item_is_atomic(repository, ready_work_item):
    first = repository.claim_ready_work_item(ready_work_item["id"], lease_owner="worker-a")
    second = repository.claim_ready_work_item(ready_work_item["id"], lease_owner="worker-b")
    assert first["lease_owner"] == "worker-a"
    assert second is None
```

Cover optimistic decisions, DAG edge uniqueness, plan-version uniqueness, assessment-version uniqueness, AI employee/executor identity separation, work-item suspension/resume atomicity, and requirement/version assignment idempotency.

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
- API remains `/api/delivery/rd-task-executor-policies` but accepts one strategy payload with `name`, `brain_app_id`, `product_id`, `status`, `matching_config`, `assessment_config`, `iteration_config`, `delivery_target`, `team_config`, `autonomy_config`, `quality_gate_config`, `git_config`, `deployment_config`, and `role_bindings`.

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

Keep each service focused. Initial resolution uses stable requirement fields only. Final resolution implements the design's explicit monotonic comparator: only less automation, tighter risk/permission/tool/repository/budget limits, more gates/roles, or `deployed -> ready_for_release` are automatically stronger. Incomparable or expanding changes return `RD_POLICY_HUMAN_DECISION_REQUIRED`; more than two strengthening rounds return `RD_POLICY_RESOLUTION_LIMIT`. Work-item resolution requires exactly one active role binding.

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

Human seats must use explicit `user_ids` in P0 and pass existing RBAC, product scope, collaboration permission, and seat-state checks. AI seats use explicit `ai_employee_ids` for actor identity and a separate executor profile for service identity, trust domain, tool policy, and execution-resource grants. Employee records store stable identity/capability/persona metadata but no secrets or permissions. Seed and test the canonical permission matrix, including `delivery.rd_ai_employees.manage`.

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
    assert assessment["initial_policy_snapshot"]["id"] == "policy_product"
    assert assessment["status"] == "evaluating"
```

Cover assigned human/AI opinion authorization, answer-created revisions, `accept/reject/request_more_info/request_rework/defer`, `waiting_human/needs_info/rework_required/accepted/deferred/rejected`, risk floor, at most two monotonic policy-strengthening rounds, required-opinion completion after strengthening, incomparable policies, human conflict, ordinary callers being unable to supply arbitrary `strategy_id`, and idempotent repeated start.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_requirement_assessments.py -q`

- [ ] **Step 3: Implement assessment orchestration**

Create one opinion request per required role. Assessment AI tasks are internal execution units authorized by the initial policy and are the only pre-accepted exception to normal work-item task creation; they cannot create code, Git, or deployment side effects. Opinions require the assigned actor; answers create a new requirement/assessment revision; decisions accept only the five canonical actions and use optimistic locking. Finalization requires all mandatory compatible opinions, stores evidence/confidence/cost/actor/executor attribution, and atomically advances `submitted + accepted` to `approved`. Existing standalone approve/reject endpoints cannot bypass this transition, and public callers cannot override policy resolution with arbitrary strategy IDs.

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

Cover no candidate, high-risk new-version confirmation, tied candidates requiring human decision while the requirement remains `approved`, capacity, policy mismatch, concurrent replay, manual batch scheduling rechecking all hard constraints, and refusal to mutate active/testing versions.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_requirement_iteration_grouping.py tests/test_iteration_version_status_flow.py -q`

- [ ] **Step 3: Implement deterministic grouping and new states**

Use a transaction lock on requirement and candidate versions. Accepted assessment atomically advances the requirement to `approved`; successful assignment advances it to `planned`. Tied candidates and high-risk new-version creation produce a decision request without prematurely setting `planned`. Manual `batch-schedule` is not a bypass: it rechecks strategy, capacity, repository, delivery-target, and hard-dependency compatibility and only accepts `planning` versions. Add `ready_for_release/deploying` version transitions, keep `ready_for_release` distinct from `released`, and reject automatic additions once a version is active or its scope is frozen.

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
- Modify: `apps/web/src/pages/Requirements/index.tsx`
- Modify: `apps/web/src/services/bugClient.ts`
- Modify: `apps/web/src/services/requirementClient.ts`
- Create: `apps/api/tests/test_rd_requirement_entry_adapters.py`
- Modify: `apps/web/tests/RequirementsPage.test.tsx`

**Interfaces:**
- Produces: `create_or_link_rd_requirement(store, *, source_type, source_id, product_id, evidence, actor_id) -> dict` with an idempotency key by source object and open requirement.
- Retires delivery-state batch advancement and public task create/start in addition to direct task creation from requirement, Bug, code-inspection, and assistant entry points, while leaving scheduled-job definition and execution semantics unchanged.

- [ ] **Step 1: Write failing bypass tests**

```python
def test_bug_promotion_creates_requirement_not_ai_task(client, bug, rd_owner_headers):
    response = client.post(f"/api/bugs/{bug['id']}/promote-ai-task", headers=rd_owner_headers)
    assert response.status_code == 200
    assert response.json()["data"]["requirement_id"]
    assert response.json()["data"].get("ai_task_id") is None
```

Also assert requirement `generate-task/batch-generate-tasks` return `RD_COLLABORATION_REQUIRED`; `batch-advance-status` rejects every delivery target and only permits safe cancel/close; public `POST /api/ai-tasks`, `/api/ai-tasks/{id}/start`, and `/api/ai-tasks/batch-retry` reject human/external callers; code-inspection remediation writes a requirement linked to the finding/report; assistant `create_rd_task` creates a requirement draft; duplicate adapters reuse the open requirement; and the Requirements/Task pages have no direct-generate, direct-start, batch-retry, or delivery-state advance controls.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_requirement_entry_adapters.py -q && cd ../../apps/web && npm test -- RequirementsPage.test.tsx`

Expected: FAIL because current services and UI still create AI tasks directly.

- [ ] **Step 3: Implement one requirement adapter and compatibility responses**

Route every legacy source through `create_or_link_rd_requirement`. Preserve source evidence and audit linkage. Return compatibility errors from public task create/start and delivery-state batch advancement; expose `create_ai_task_for_work_item` and `dispatch_ai_task_for_work_item` only as internal services for Task 11. Do not change `scheduled_jobs/scheduled_job_runs`, locking, retry, Agent/Skill snapshots, or scheduler behavior; only the code-inspection result write target changes from direct task to requirement.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: route rd work through requirements`.

### Task 9: Implement Work-Item DAG, Seats, Decisions, Rework, and Feedback

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
- Produces: `POST /api/product-versions/{version_id}/collaboration-runs`, `GET /api/requirements/{requirement_id}/collaboration-run`, run detail, plan/replan, work-item claim/complete/block, review/rework, event, and `POST /api/delivery/decision-requests/{id}/decide` APIs.
- Produces: `validate_work_item_plan`, `ready_work_items`, `claim_work_item`, `suspend_work_item`, `resume_work_item`, `complete_attempt`, and `apply_decision`.

- [ ] **Step 1: Write failing DAG and scheduling tests**

```python
def test_scheduler_does_not_release_item_before_dependencies_are_approved(store):
    items = ready_work_items(store, collaboration_run_id="run-1")
    assert "integration-item" not in {item["id"] for item in items}
```

Cover cycles, acceptance coverage, reviewer separation, capacity, leases, rework attempts, plan versions, stale decisions, no-progress escalation, distinct AI employee/executor attribution, and platform-controlled recovery from `blocked/awaiting_human`.

Also cover one non-terminal run per version, concurrent idempotent start, scope freeze at start, all included requirements having accepted assessments, and range changes producing a new plan version plus decision request.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_runtime.py tests/test_rd_work_item_scheduler.py -q`

- [ ] **Step 3: Implement deterministic control plane**

LLM plans are JSON proposals only. The product version is the aggregate root: lock it during start, freeze requirement and repository scope, move it from `planning` to `active`, and return the same run for duplicate starts. Persist each plan version and validate scope, permissions, budgets, dependencies, role availability, and review separation before activation. AI seats freeze both employee and executor identities. Suspending an item persists `resume_state`, attempt, decision/event, and release conditions; only the scheduler or decision service may move `blocked/awaiting_human` to validated `ready/running/rework_required/cancelled` states.

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
```

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_graph_runtime.py tests/test_workflow_runtime_persistence.py tests/test_rd_collaboration_graph.py -q`

- [ ] **Step 3: Add the official PostgreSQL checkpoint dependency and adapters**

Compile both graph types with a Checkpointer. Tests use a fresh in-memory saver; PostgreSQL runtime uses the configured checkpoint connection. Domain state, Inbox event, audit, and Outbox commit atomically through the collaboration repository; Checkpointer persistence is a separate execution-cursor commit. Every resumed node re-reads domain state and emits idempotent commands, so either checkpoint/domain partial failure is safely retryable. Checkpoint incompatibility fails closed to human takeover.

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
- Produces: internal-only `create_ai_task_for_work_item` and `dispatch_ai_task_for_work_item`, completion event projection, independent review creation, and rework attempt dispatch.
- Consumes: frozen role binding, execution context manifest, Agent Loop, Runner, quality gates, and work-item scheduler.

- [ ] **Step 1: Write failing execution integration tests**

Assert an AI work item creates one linked AI task through the internal service, freezes separate AI employee and executor IDs, uses only the frozen executor, coding success enters verification, passed review approves the work item, failed gate enters `rework_required` with the original attempt preserved, and duplicate Runner completion is idempotent. Also assert public task create/start cannot invoke these services.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_work_item_execution.py tests/test_quality_gates.py tests/test_rd_task_executor_policies.py -q`

- [ ] **Step 3: Implement integration without changing scheduled jobs**

Project Runner and review results into collaboration events through Outbox; never let scheduled-job execution create collaboration state directly.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command, then commit `feat: execute rd collaboration work items`.

### Task 12: Integrate Policy-Controlled Delivery and Feedback Attribution

**Files:**
- Modify: `apps/api/app/services/product_version_release_readiness.py`
- Modify: `apps/api/app/services/operational_deployments.py`
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
- Produces: `record_version_git_delivery`, `verify_version_git_delivery`, `complete_collaboration_at_ready_for_release`, and `enter_policy_controlled_deployment`; default completion leaves the version at `ready_for_release` and writes run `status=completed/completion_reason=ready_for_release`.
- Produces: role/actor/executor/attempt feedback records and governed experience candidates.

- [ ] **Step 1: Write failing delivery-boundary tests**

Assert the integration work item pushes through Outbox and stores repository/branch/local SHA/remote SHA/MR-PR/outbox/reconciliation evidence. `ready_for_release` only verifies this evidence and creates no push or deployment request; missing or mismatched remote evidence blocks completion. Default completion leaves the product version at `ready_for_release`, completes the run with `completion_reason=ready_for_release`, and creates no deployment request. `deployed` creates a request only after readiness, scope, approval, and rollback gates and completes with `completion_reason=deployed`.

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_delivery.py tests/test_rd_feedback_attribution.py -q`

- [ ] **Step 3: Implement delivery and attribution projections**

Reuse existing trusted delivery records, deployment requests/runs, reconciliation, and Outbox. Experience records separately persist role/seat plus `human_user_id` or `ai_employee_id`, executor profile, attempt, and strategy snapshot. They remain candidates until governance approval and cannot mutate live policy automatically.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command and existing deployment tests, then commit `feat: complete policy-controlled rd delivery`.

### Task 13: Upgrade the Web Workbench

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
- Consumes: Tasks 4-12 APIs.
- Produces: one unified policy editor, AI digital employee catalog, assessment review, grouping explanation, collaboration DAG/board, role seats, work-item attempts, blockers, and human decisions.

- [ ] **Step 1: Write failing user-flow tests**

Test unified policy editing without old executor fields, separate AI employee/executor selection, full assessment opinion/answer/decision actions, existing-version grouping rationale, absence of delivery-state batch advancement and public task-start controls, work-item review/rework/recovery, RBAC read-only states, and deployment-disabled completion with version/run status separation.

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

### Task 14: Add Maintenance Fence, Upgrade Preflight, and Cutover Validation

**Files:**
- Create: `apps/api/app/db/migrations/110_requirement_driven_rd_cutover.sql`
- Create: `apps/api/app/services/rd_collaboration_migration.py`
- Create: `apps/api/app/services/rd_maintenance_fence.py`
- Create: `apps/api/app/api/routers/rd_migration.py`
- Create: `scripts/rd_collaboration_upgrade_check.py`
- Create: `scripts/rd_collaboration_cutover.py`
- Create: `apps/api/tests/test_rd_collaboration_migration.py`
- Create: `apps/api/tests/test_rd_maintenance_fence.py`

**Interfaces:**
- Produces: read-only preflight, maintenance-fence enable/disable, deterministic policy-conversion preview, and an admin-only cutover command that refuses active tasks, active Agent Loops, active Runner tasks, policy conflicts, missing roles, or invalid resources.
- Produces: migration 110 as the final cleanup contract; it runs only after cutover sets `rd_collaboration_schema_version=2` and records the new-application health marker.

- [ ] **Step 1: Write failing preflight tests**

```python
def test_upgrade_preflight_blocks_active_ai_task(store):
    report = build_upgrade_preflight(store)
    assert report["ready"] is False
    assert report["blockers"][0]["code"] == "RD_UPGRADE_ACTIVE_TASKS"


def test_maintenance_fence_blocks_rd_writes_but_not_scheduled_jobs(client, admin_headers):
    enable_rd_fence(client, admin_headers)
    assert start_ai_task(client, admin_headers).status_code == 423
    assert run_scheduled_job(client, admin_headers).status_code != 423


def test_destructive_cleanup_is_not_in_automatic_migration_registry():
    assert "110_requirement_driven_rd_cutover.sql" not in registered_migration_names()


def test_fence_can_open_only_after_v2_workers_and_smoke_write_are_healthy(client, admin_headers):
    response = disable_rd_fence(client, admin_headers)
    assert response.status_code == 409
    mark_cleanup_worker_and_smoke_checks_successful()
    assert disable_rd_fence(client, admin_headers).status_code == 200
    assert start_v2_assessment(client, admin_headers).status_code != 423
    assert legacy_generate_task(client, admin_headers).status_code == 409
```

- [ ] **Step 2: Verify red**

Run: `cd apps/api && uv run pytest tests/test_rd_collaboration_migration.py tests/test_rd_maintenance_fence.py -q`

- [ ] **Step 3: Implement maintenance-fenced preflight and one-way cutover**

The API and scripts never deploy. Enable the fence before preflight; block requirement approval/rejection/direct task generation, AI task start/retry, policy writes, collaboration writes, and Runner claims while leaving scheduled jobs unchanged. Convert policies and cancel legacy drafts only after blockers are zero. Set Schema v2, start the new application with old columns still present, validate health, then record the health marker. Migration 110 is destructive and must be executed explicitly by `rd_collaboration_cutover.py cleanup` as one SQL transaction after that marker; do not register it in the automatic additive compatibility runner. After cleanup, resume v2 workers, verify worker/schema/graph-version equality, execute v2 assessment and collaboration write smoke tests, and only then disable the fence with the expected schema version and health marker. Any failure keeps maintenance enabled and retryable. After release, v2 writes succeed while all legacy write paths remain rejected.

- [ ] **Step 4: Verify green and commit**

Run the Step 2 command plus `python scripts/rd_collaboration_upgrade_check.py --help` and `python scripts/rd_collaboration_cutover.py --help`, then commit `feat: validate rd collaboration cutover`.

### Task 15: Update Help, Regression Coverage, Browser Evidence, and Remote Branch

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

Cover requirement submission; assigned opinions, answers, and all assessment decisions; compatible planning-version selection; two requirements sharing one version run; policy snapshot; distinct AI employee/executor identity; collaboration DAG; blocked/human-wait recovery; internal AI work-item execution and retry; independent review; rework; reconciled remote branch/commit evidence; product version `ready_for_release`; run `completed/completion_reason=ready_for_release`; deployment-disabled stop; and actor/executor feedback attribution. Also verify Bug/code-inspection/assistant legacy entry adapters create requirements rather than AI tasks, delivery-state batch advancement and public AI-task create/start/batch-retry are rejected, maintenance-fence release restores only v2 writes, and a representative scheduled job retains its pre-upgrade definition, schedule, Agent/Skill snapshot, and run semantics.

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

- Every approved design section maps to Tasks 1-15.
- Unified policy has one API and one page; Task 2 only adds compatible schema, Task 4 rejects old writes, and Task 14 removes old fields after maintenance-fenced cutover.
- Requirement assessment resolves policy before and after AI evaluation in Tasks 4 and 6.
- Version grouping is deterministic and idempotent in Task 7.
- Direct R&D entry bypasses are converted to requirement adapters in Task 8.
- Public delivery-state batch advancement and AI-task create/start bypasses are rejected in Task 8; internal work-item services are integrated in Task 11.
- Human/AI roles, persistent AI employee identity, executor separation, RBAC separation, seats, sessions, DAG, review, recovery, rework, decisions, and attribution are covered by Tasks 5, 9, 11, and 12.
- Existing LangGraph is reused and upgraded with a PostgreSQL Checkpointer in Task 10; domain state and event Inbox remain the consistency source.
- Scheduled-job engine behavior is explicitly unchanged in Global Constraints, Tasks 8, 11, 14, and 15.
- Delivery leaves the version at `ready_for_release` and completes the run with `completion_reason=ready_for_release` by default; deployment is entered only through policy in Task 12, after remote Git evidence is recorded.
- Additive schema, maintenance fence, zero-active-task preflight, policy conversion, draft cancellation, one-way activation, cleanup, v2 Worker/smoke verification, and safe fence release are covered by Tasks 2 and 14.
- No implementation step contains an unresolved placeholder.
