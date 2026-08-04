# R&D Collaboration E2E Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable v2.0 regression path that proves a real requirement can reach trusted remote-Git delivery and `ready_for_release` through AI collaboration, while preserving human gates and never deploying.

**Architecture:** Keep fast API/state-machine regression separate from side-effecting validation. Shared Python fixture helpers create version-scoped collaboration data; a simulated Runner protocol keeps fast suites deterministic, while an explicit `rd-delivery-e2e` suite binds an already-running Codex Runner to a real repository and waits on durable states. A Playwright smoke script validates that the same run is operable from the version dashboard, collaboration workbench, task confirmation UI, and role-experience page.

**Tech Stack:** Python 3.11, FastAPI public APIs, PostgreSQL-backed runtime, execution Worker, Codex Runner protocol, pytest, Ruff, React 19, TypeScript, Vitest, Playwright, Git provider webhook/Inbox reconciliation.

## Global Constraints

- Product defect fixes stay on the current development branch; Runner-generated test changes use only `rd/<run-id>/<work-item-id>` isolated branches.
- The frozen policy must use `delivery_target=ready_for_release`; no test calls a deployment endpoint, creates a deployment record, merges a branch, rebases, resets, or modifies a protected branch.
- Remote evidence is valid only after Runner push plus persisted signature-verified provider Inbox reconciliation; user-supplied SHA values are never accepted as trusted evidence.
- The real Runner suite is opt-in as `--suite rd-delivery-e2e` and is excluded from `all-targeted`.
- Low/medium AI work auto-dispatches through Worker state; high/critical work pauses for a human decision.
- Poll durable API state with bounded deadlines and diagnostic snapshots; do not use fixed sleeps as completion evidence.
- Preserve run, work-item, attempt, worktree, Runner, gate, review, outbox, reconciliation, and audit records after failures.
- Credentials and Runner tokens come from environment variables or credential references and must not appear in JSON reports, console output, screenshots, source files, or commits.
- P1 role-experience verification begins only after the P0 delivery suite passes.
- Existing uncommitted changes in `TaskDetailModal.tsx`, `TaskCenter/index.tsx`, `TaskCenterPage.test.tsx`, `full_chain_regression_rd_collaboration.py`, and `full_chain_regression_runner.py` must be inspected and preserved; do not overwrite or discard them.

---

## File Map

| File | Responsibility |
| --- | --- |
| `scripts/full_chain_regression_rd_fixture.py` | Reusable v2 requirement assessment, grouping, policy, run, DAG, polling, and review fixture helpers. |
| `scripts/full_chain_regression_rd_runner_protocol.py` | Deterministic simulated Runner protocol for fast suites; never performs real Git push. |
| `scripts/full_chain_regression_rd_delivery_e2e.py` | Opt-in real Runner and trusted remote-delivery orchestration, fault scenarios, evidence assertions, and report steps. |
| `scripts/full_chain_regression.py` | CLI registration, suite dispatch, report fields, and legacy full regression cutover. |
| `scripts/full_chain_regression_suites.py` | Coverage declaration without adding the side-effect suite to default targeted runs. |
| `scripts/full_chain_regression_rd_collaboration.py` | Fast public control-plane suite using the shared v2 fixture. |
| `scripts/full_chain_regression_assistant_qa.py` | Assistant fixture migrated away from legacy requirement/task endpoints. |
| `apps/api/app/services/ai_executor_runner_rd_completion.py` | Creates v2 Runner completion Reviews and code-review artifacts. |
| `apps/api/app/services/ai_executor_runner_persistence.py` | Persists Runner-projected task, Review and code-review report records atomically. |
| `apps/api/app/services/task_persistence_helpers.py` | Shared task-state persistence contract with optional code-review report. |
| `apps/api/app/core/repositories/tasks.py` | PostgreSQL transaction for task, Review, report and audit records. |
| `apps/api/tests/test_full_chain_rd_collaboration_regression.py` | Contract tests for fixture reuse, suite registration, endpoint cutover, and report redaction. |
| `apps/api/tests/test_rd_delivery_e2e_harness.py` | Unit tests for E2E configuration, safety checks, polling, state assertions, and fault sequencing. |
| `apps/web/scripts/rd-collaboration-smoke.mjs` | Real-browser workflow assertions and masked screenshots for a supplied version/run/task. |
| `apps/web/package.json` | Checked-in command for the R&D collaboration browser smoke. |
| `apps/web/tests/TaskCenterPage.test.tsx` | Review-entry behavior for v2 tasks. |
| `apps/web/tests/IterationVersionsPage.test.tsx` | Version-dashboard action to continue a real collaboration run. |
| `apps/web/tests/RdCollaborationPage.test.tsx` | Human decision and cancelled-work-item recovery behavior. |
| `apps/web/tests/RdRoleExperiencesPage.test.tsx` | Independent role-experience decision behavior. |
| `docs/08-help/delivery.md` | User-facing explanation of test-branch delivery, human gates, and no-deployment boundary if UI behavior changes. |
| `docs/changelog.md` | Records regression and user-flow changes once implementation is verified. |

---

### Task 1: Extract the reusable v2 collaboration fixture

**Files:**
- Create: `scripts/full_chain_regression_rd_fixture.py`
- Modify: `scripts/full_chain_regression_rd_collaboration.py`
- Test: `apps/api/tests/test_full_chain_rd_collaboration_regression.py`

**Interfaces:**
- Consumes: an authenticated-compatible `ApiClient` exposing `get(path, query=None)` and `post(path, body=None, extra_headers=None)`.
- Produces:
  - `RdFixtureSpec(marker, product_id, repository_id, role_bindings, required_role_codes, work_items, dependencies, policy_overrides)`
  - `RdFixtureResult(product_id, version_id, requirement_id, assessment_id, strategy_snapshot_id, run_id, work_items, scope_version)`
  - `create_rd_fixture(client, *, owner_user_id: str, spec: RdFixtureSpec) -> RdFixtureResult`
  - `wait_for_value(fetch, predicate, timeout_seconds, description) -> Any`
  - `complete_and_review_human_work_item(client, marker, work_item) -> dict[str, Any]`

- [ ] **Step 1: Write failing fixture contract tests**

Add tests which import the new module, construct the dataclasses, and assert that a fake client observes the canonical sequence:

```python
def test_v2_fixture_uses_assessment_grouping_and_collaboration_run() -> None:
    paths = fixture_module_paths_for_minimal_run()

    assert paths == [
        "/api/requirements",
        "/api/requirements/requirement-1/assessments",
        "/api/requirement-assessments/assessment-1/opinions",
        "/api/requirements/requirement-1/assessments/latest",
        "/api/requirement-assessments/assessment-1/decisions",
        "/api/product-versions/version-1/collaboration-runs",
        "/api/delivery/rd-collaboration-runs/run-1/plan",
    ]
    assert all("/approve" not in path for path in paths)
    assert all("generate-task" not in path for path in paths)
```

- [ ] **Step 2: Run the new tests and verify the missing-module failure**

Run:

```bash
cd apps/api
uv run pytest tests/test_full_chain_rd_collaboration_regression.py -q
```

Expected: FAIL because `full_chain_regression_rd_fixture.py` does not exist.

- [ ] **Step 3: Implement the fixture dataclasses and bounded polling**

Use immutable dataclasses and monotonic deadlines:

```python
@dataclass(frozen=True)
class RdFixtureResult:
    assessment_id: str
    product_id: str
    requirement_id: str
    run_id: str
    scope_version: int
    strategy_snapshot_id: str
    version_id: str
    work_items: tuple[dict[str, Any], ...]


def wait_for_value(fetch, predicate, *, timeout_seconds: float, description: str):
    deadline = time.monotonic() + timeout_seconds
    last_value = None
    while time.monotonic() < deadline:
        last_value = fetch()
        if predicate(last_value):
            return last_value
        time.sleep(min(0.5, max(0.05, deadline - time.monotonic())))
    raise AssertionError(f"{description} timed out; last_value={_safe_summary(last_value)}")
```

`_safe_summary` must retain IDs, statuses, versions and error codes while removing keys containing `token`, `secret`, `credential`, `authorization`, or `cookie`.

- [ ] **Step 4: Move the existing assessment/grouping/run/DAG logic into the helper**

Keep these invariants in the helper:

```python
assert assessment["initial_strategy_snapshot_id"]
assert grouping["status"] == "planned"
assert grouping["version"]["id"] == version_id
assert run["strategy_snapshot_kind"] == "version_resolved"
assert run["delivery_target"] == "ready_for_release"
```

Do not add fallback calls to `/api/requirements/{id}/approve`, `/generate-task`, or `/api/ai-tasks/{id}/start`.

- [ ] **Step 5: Refactor the existing `rd-collaboration` suite to consume the helper**

The fast suite must still stop at `verifying` after human claim/submit/review and must still report `deployment=not_requested`.

- [ ] **Step 6: Run focused tests and Ruff**

Run:

```bash
cd apps/api
uv run pytest tests/test_full_chain_rd_collaboration_regression.py -q
uv run ruff check ../../scripts/full_chain_regression_rd_fixture.py ../../scripts/full_chain_regression_rd_collaboration.py tests/test_full_chain_rd_collaboration_regression.py
```

Expected: all tests pass and Ruff reports no findings.

- [ ] **Step 7: Commit the fixture extraction**

```bash
git add scripts/full_chain_regression_rd_fixture.py scripts/full_chain_regression_rd_collaboration.py apps/api/tests/test_full_chain_rd_collaboration_regression.py
git commit -m "test: extract rd collaboration v2 fixtures"
```

---

### Task 2: Add a deterministic simulated Runner protocol for fast suites

**Files:**
- Create: `scripts/full_chain_regression_rd_runner_protocol.py`
- Modify: `scripts/full_chain_regression_rd_fixture.py`
- Test: `apps/api/tests/test_full_chain_rd_collaboration_regression.py`

**Interfaces:**
- Consumes: a fixture whose owner seat is `ai_employee`, an ephemeral polling Runner token, and a human reviewer session.
- Produces:
  - `SimulatedRunnerSession(runner_id, runner_headers, executor_profile_id, ai_employee_id)`
  - `SimulatedAiResult(ai_task_id, attempt_id, review_id, runner_task_ids, work_item)`
  - `create_simulated_runner_session(client, marker, workspace_root, role_codes)`
  - `complete_ai_work_item_via_runner_protocol(client, session, run_id, work_item_id, reviewer_client, timeout_seconds)`

- [ ] **Step 1: Write failing tests for protocol ordering and redaction**

```python
def test_simulated_runner_completes_v2_task_without_git_side_effects() -> None:
    result = simulate_protocol_fixture()

    assert result.work_item["status"] == "completed"
    assert result.ai_task_id == "task-1"
    assert result.runner_task_ids == ("runner-task-1",)
    assert result.review_id == "review-1"
    assert "git_delivery" not in result.runner_result
```

Add a second test asserting that the Runner token appears only in request headers and never in `StepResult.detail` or JSON report content.

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
cd apps/api
uv run pytest tests/test_full_chain_rd_collaboration_regression.py -q
```

Expected: FAIL because the protocol helper is missing.

- [ ] **Step 3: Implement ephemeral Runner/profile/AI employee setup**

Create the Runner through `/api/system/ai-executor-runners`, then create an AI employee and executor profile through `/api/delivery/rd-ai-employees` and `/api/delivery/rd-executor-profiles`. Freeze the policy binding as:

```python
{
    "actor_mode": "ai",
    "candidate_ai_employee_ids": [session.ai_employee_id],
    "primary_executor_profile_id": session.executor_profile_id,
    "role_code": role_code,
    "status": "active",
}
```

Use a reviewer binding with `actor_mode=human` and a different user ID.

- [ ] **Step 4: Implement Runner claim, log, completion and human review**

For non-code work such as `product_detail_design`, complete the claimed Runner task with:

```python
{
    "logs": [{"level": "info", "message": "deterministic v2 regression completed"}],
    "result_json": {"summary": "deterministic v2 regression output"},
    "runner_id": session.runner_id,
    "status": "succeeded",
}
```

Poll the AI task until `waiting_review`, query its pending Review, approve it with the independent reviewer, and assert the collaboration work item becomes `completed`.

- [ ] **Step 5: Add implementation-work-item quality-gate protocol**

When `task_kind=quality_gate` is queued, claim and complete it from a verification-trust Runner session. Assert the work item reaches `reviewing` only after the quality gate succeeds, then approve it through the work-item/Review contract already used by the product.

- [ ] **Step 6: Run protocol tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_full_chain_rd_collaboration_regression.py tests/test_rd_work_item_execution.py -q
uv run ruff check ../../scripts/full_chain_regression_rd_runner_protocol.py ../../scripts/full_chain_regression_rd_fixture.py
```

Expected: both files pass; no trusted Git delivery record is created by the simulated protocol.

- [ ] **Step 7: Commit the simulated protocol**

```bash
git add scripts/full_chain_regression_rd_runner_protocol.py scripts/full_chain_regression_rd_fixture.py apps/api/tests/test_full_chain_rd_collaboration_regression.py
git commit -m "test: add simulated v2 runner protocol"
```

---

### Task 3: Persist code-review artifacts from v2 Runner completion

**Files:**
- Modify: `apps/api/app/services/ai_executor_runner_rd_completion.py`
- Modify: `apps/api/app/services/ai_executor_runner_persistence.py`
- Modify: `apps/api/app/services/task_persistence_helpers.py`
- Modify: `apps/api/app/core/repositories/tasks.py`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Test: `apps/api/tests/test_rd_work_item_execution.py`
- Test: `apps/api/tests/test_requirement_task_persistence.py`

**Interfaces:**
- Consumes a v2 `code_review` AI task, Runner output containing `summary`, `risk_level` and `findings`, and the pending human Review created by `move_ai_task_to_executor_review(...)`.
- Produces `code_review_report` in the same durable task/review transaction and sets both `task.code_review_report_id` and `report.review_id`.
- Extends `_persist_task_state_records(..., code_review_report: dict[str, Any] | None = None)` and `save_task_state_records(..., code_review_report: dict[str, Any] | None = None)` consistently through Runner helper, service helper, repository protocol, facade and PostgreSQL repository.

- [ ] **Step 1: Write a failing v2 Runner code-review persistence test**

```python
def test_v2_code_review_runner_completion_persists_report_with_pending_review() -> None:
    store = _ai_work_item_store(task_type="code_review")
    dispatch = dispatch_ai_task_for_work_item(
        store,
        collaboration_run_id="run-1",
        work_item_id="work-1",
    )
    runner_task = store.ai_executor_tasks[dispatch["runner_task"]["id"]]
    runner_task.update(
        {
            "result_json": {
                "findings": [],
                "risk_level": "low",
                "summary": "No blocking findings",
            },
            "status": "succeeded",
        }
    )

    _sync_runner_completion_to_ai_task(store, task=runner_task, runner_id="runner-frozen")

    task = store.ai_tasks[dispatch["task"]["id"]]
    report = store.code_review_reports[task["code_review_report_id"]]
    review = store.human_reviews[task["review_ids"][0]]
    assert task["status"] == "waiting_review"
    assert report["review_id"] == review["id"]
    assert report["status"] == "pending"
```

Add a repository test that reloads task, Review and report from PostgreSQL-backed persistence and checks the same IDs.

- [ ] **Step 2: Run the tests and verify the report is currently missing**

Run:

```bash
cd apps/api
uv run pytest tests/test_rd_work_item_execution.py tests/test_requirement_task_persistence.py -q
```

Expected: the new test fails because v2 Runner completion currently persists the task and Review without materializing a code-review report.

- [ ] **Step 3: Extend the task-state persistence transaction**

Add the optional `code_review_report` parameter to both Runner and shared service helpers and every declared/concrete `save_task_state_records` signature. The MemoryStore branch writes the same report to `code_review_reports`. In `TaskReadRepository.save_task_state_records`, upsert the report inside the same database transaction:

```python
if code_review_report is not None:
    self._require_callback(self._upsert_code_review_reports, "code review report upsert")
    self._upsert_code_review_reports(
        cursor,
        {code_review_report["id"]: code_review_report},
    )
```

- [ ] **Step 4: Materialize the report before persisting the pending Review**

In `move_ai_task_to_executor_review`, after allocating/reusing the Review ID, call the existing `create_code_review_report(...)` for `task_type=code_review`, link its `review_id`, set `updated_task["code_review_report_id"]`, and pass it to `_persist_task_state_records`. MemoryStore and repository-backed paths must produce the same IDs and status.

- [ ] **Step 5: Verify independent approval confirms the report**

Extend the test to approve the pending Review and assert:

```python
assert store.code_review_reports[report["id"]]["status"] == "confirmed"
assert store.rd_work_items["work-1"]["status"] == "completed"
```

- [ ] **Step 6: Run focused backend tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_rd_work_item_execution.py tests/test_requirement_task_persistence.py tests/test_code_review_executor.py -q
uv run ruff check app/services/ai_executor_runner_rd_completion.py app/services/ai_executor_runner_persistence.py app/services/task_persistence_helpers.py app/core/repositories/tasks.py app/core/persistence.py app/core/persistence_contracts.py
```

Expected: all tests pass and no repository signature diverges.

- [ ] **Step 7: Commit the v2 artifact projection**

```bash
git add apps/api/app/services/ai_executor_runner_rd_completion.py apps/api/app/services/ai_executor_runner_persistence.py apps/api/app/services/task_persistence_helpers.py apps/api/app/core/repositories/tasks.py apps/api/app/core/persistence.py apps/api/app/core/persistence_contracts.py apps/api/tests/test_rd_work_item_execution.py apps/api/tests/test_requirement_task_persistence.py
git commit -m "fix: persist v2 runner code review artifacts"
```

---

### Task 4: Cut legacy regression suites over to the v2 collaboration path

**Files:**
- Modify: `scripts/full_chain_regression.py`
- Modify: `scripts/full_chain_regression_assistant_qa.py`
- Modify: `scripts/full_chain_regression_suites.py`
- Test: `apps/api/tests/test_full_chain_rd_collaboration_regression.py`

**Interfaces:**
- Consumes: `create_rd_fixture(...)` and `complete_ai_work_item_via_runner_protocol(...)` from Tasks 1 and 2.
- Produces: legacy-named `full`, `version-dashboard`, and `assistant-qa` suites with no v2-forbidden endpoint usage.

- [ ] **Step 1: Add a source-level guard test for forbidden calls**

```python
@pytest.mark.parametrize(
    "relative_path",
    [
        "scripts/full_chain_regression.py",
        "scripts/full_chain_regression_assistant_qa.py",
    ],
)
def test_v2_regressions_do_not_call_legacy_task_entrypoints(relative_path: str) -> None:
    source = (REPOSITORY_ROOT / relative_path).read_text()
    assert "/api/requirements/{requirement['id']}/approve" not in source
    assert "/generate-task" not in source
```

Also assert no external test client directly creates or starts an AI task.

- [ ] **Step 2: Run the guard and verify it fails against current scripts**

Run:

```bash
cd apps/api
uv run pytest tests/test_full_chain_rd_collaboration_regression.py -q
```

Expected: FAIL and identify the current legacy endpoint strings.

- [ ] **Step 3: Migrate the full regression requirement/task segment**

Replace:

```text
approve -> batch-schedule -> generate-task -> start -> review approve
```

with:

```text
assessment -> role opinions -> accept/group -> collaboration run
-> AI-owned product_detail_design work item -> simulated Runner
-> human Review approval
```

Carry the returned `ai_task_id` into knowledge-deposit, Bug, lifecycle, dashboard and audit assertions. Keep the user-feedback-to-requirement link as the upstream origin.

- [ ] **Step 4: Migrate version-dashboard and assistant fixtures**

For version dashboard, use one DAG with explicit task types:

```python
[
    {
        "id": "design",
        "work_item_type": "product_detail_design",
        "risk_level": "low",
    },
    {
        "id": "solution",
        "work_item_type": "technical_solution",
        "risk_level": "low",
    },
    {
        "id": "review",
        "work_item_type": "code_review",
        "risk_level": "high",
    },
]
```

After the technical-solution Review completes, create the existing MR snapshot with its generated `technical_solution_task_id` while the high-risk code-review item is paused for dispatch approval. Then approve dispatch, run the code-review task, and use its generated task/report IDs for existing MR snapshot, Bug and dashboard assertions. For assistant QA, use one completed v2 `product_detail_design` work item and retain the existing deterministic assistant questions and version references.

- [ ] **Step 5: Update suite coverage descriptions**

Keep `full` at all declared objective domains. Update help text so it states that AI tasks are created internally by v2 collaboration. Do not mark the real remote side-effect suite as part of `all-targeted`.

- [ ] **Step 6: Run all fast regression tests and local targeted suites**

Run:

```bash
cd apps/api
uv run pytest tests/test_full_chain_rd_collaboration_regression.py -q
cd ../..
FULL_CHAIN_USERNAME=admin@example.com FULL_CHAIN_PASSWORD=admin123 python scripts/full_chain_regression.py --suite rd-collaboration
FULL_CHAIN_USERNAME=admin@example.com FULL_CHAIN_PASSWORD=admin123 python scripts/full_chain_regression.py --suite version-dashboard
FULL_CHAIN_USERNAME=admin@example.com FULL_CHAIN_PASSWORD=admin123 python scripts/full_chain_regression.py --suite assistant-qa
FULL_CHAIN_USERNAME=admin@example.com FULL_CHAIN_PASSWORD=admin123 python scripts/full_chain_regression.py --suite full
```

Expected: all commands pass; server logs contain no `RD_COLLABORATION_REQUIRED` or `REQUIREMENT_ASSESSMENT_REQUIRED` response from these suites.

- [ ] **Step 7: Commit the regression cutover**

```bash
git add scripts/full_chain_regression.py scripts/full_chain_regression_assistant_qa.py scripts/full_chain_regression_suites.py apps/api/tests/test_full_chain_rd_collaboration_regression.py
git commit -m "test: migrate full regression to rd collaboration"
```

---

### Task 5: Implement the opt-in real Runner delivery suite

**Files:**
- Create: `scripts/full_chain_regression_rd_delivery_e2e.py`
- Modify: `scripts/full_chain_regression.py`
- Modify: `scripts/full_chain_regression_suites.py`
- Create: `apps/api/tests/test_rd_delivery_e2e_harness.py`

**Interfaces:**
- Consumes environment variables:
  - `RD_E2E_PRODUCT_ID`
  - `RD_E2E_REPOSITORY_ID`
  - `RD_E2E_RUNNER_ID`
  - `RD_E2E_EXECUTOR_PROFILE_ID`
  - `RD_E2E_AI_DEVELOPER_ID`
  - `RD_E2E_AI_TESTER_ID`
  - `RD_E2E_REVIEWER_USERNAME`
  - `RD_E2E_REVIEWER_PASSWORD`
  - `RD_E2E_TIMEOUT_SECONDS` with default `2400`
- Produces:
  - suite `rd-delivery-e2e`
  - `RdDeliveryE2EConfig.from_env()`
  - `validate_rd_delivery_e2e(client, owner_username, owner_password, config) -> list[StepResult]`
  - JSON report steps containing product/version/requirement/run/work-item/task/gate/delivery IDs and statuses, but no credentials.

- [ ] **Step 1: Write failing configuration and safety tests**

```python
def test_real_e2e_rejects_missing_or_unsafe_configuration(monkeypatch) -> None:
    monkeypatch.delenv("RD_E2E_RUNNER_ID", raising=False)
    with pytest.raises(RegressionError, match="RD_E2E_RUNNER_ID"):
        RdDeliveryE2EConfig.from_env()

    unsafe = valid_config(repository_default_branch="main", delivery_target="deployed")
    with pytest.raises(RegressionError, match="ready_for_release"):
        validate_safety_boundary(unsafe)
```

Add tests that reject owner/reviewer identity equality and any configured branch outside `rd/*`.

- [ ] **Step 2: Run the harness test and verify the missing-module failure**

Run:

```bash
cd apps/api
uv run pytest tests/test_rd_delivery_e2e_harness.py -q
```

Expected: FAIL because the E2E module does not exist.

- [ ] **Step 3: Implement preflight checks**

The preflight must verify:

```python
assert runner["status"] == "active"
assert runner["health_status"] == "online"
assert "codex" in runner["executor_types"]
assert profile["runner_id"] == runner["id"]
assert profile["status"] == "active"
assert repository["product_id"] == config.product_id
assert policy_payload["delivery_target"] == "ready_for_release"
```

Also query Worker heartbeat evidence and fail before creating a requirement when no recent Worker heartbeat exists.

- [ ] **Step 4: Create the real test requirement, policy and DAG**

Create a unique planning version tagged `e2e`, then submit and accept a low-risk requirement whose implementation instruction is restricted to:

```text
Create docs/e2e/rd-collaboration-<run-id>.md containing requirement_id,
run_id, trace_id, and acceptance criteria. Do not modify application code,
dependencies, CI, deployment files, protected branches, or secrets.
```

Plan:

```python
dependencies = [
    ("implement_e2e_artifact", "verify_e2e_artifact"),
]
```

`implement_e2e_artifact` uses type `implementation`; `verify_e2e_artifact` uses the supported `automated_testing` type and owns the integration/test delivery evidence. Both declare the frozen repository resource; the implementation item restricts write scope to the one E2E document path. Do not create an `integration` AI work item because it is not a supported underlying AI task type.

- [ ] **Step 5: Wait for the real Runner and independent quality gate**

Poll work items and task detail until:

```python
implementation.status == "reviewing"
implementation_gate.status == "passed"
implementation_runner_task.status == "succeeded"
implementation_runner_task.workspace_root
```

Approve with the independent reviewer, then assert the dependent automated-testing item is dispatched automatically by the Worker without a client start call.

- [ ] **Step 6: Validate real Git push and provider reconciliation**

Require both implementation/coding and automated-testing/integration delivery records. For every required record assert:

```python
assert delivery["working_branch"] == f"rd/{run_id}/{delivery['work_item_id']}"
assert delivery["local_commit_sha"]
assert delivery["remote_commit_sha"] == delivery["local_commit_sha"]
assert delivery["verified_at"]
assert reconciliation["status"] == "verified"
```

The suite must only observe these facts; it must not post a caller-supplied remote SHA or fabricated callback.

- [ ] **Step 7: Assert ready-for-release and no deployment**

Require:

```python
assert final_run["status"] == "completed"
assert final_run["completion_reason"] == "ready_for_release"
assert final_version["status"] == "ready_for_release"
assert dashboard["deployments"] == []
```

Also inspect audit summaries and fail if this run has any `deployment_request.created`, `deployment.run.started`, or deployment-completed event.

- [ ] **Step 8: Register the explicit suite without default inclusion**

Add `rd-delivery-e2e` to CLI choices and `REGRESSION_SUITE_DOMAINS`, but not to `REGRESSION_TARGETED_SUITE_NAMES`.

- [ ] **Step 9: Run unit checks without performing the remote side effect**

Run:

```bash
cd apps/api
uv run pytest tests/test_rd_delivery_e2e_harness.py tests/test_rd_collaboration_delivery.py tests/test_rd_work_item_execution.py -q
uv run ruff check ../../scripts/full_chain_regression_rd_delivery_e2e.py ../../scripts/full_chain_regression.py tests/test_rd_delivery_e2e_harness.py
```

Expected: all unit checks pass. Do not run `--suite rd-delivery-e2e` in this step.

- [ ] **Step 10: Commit the real E2E harness**

```bash
git add scripts/full_chain_regression_rd_delivery_e2e.py scripts/full_chain_regression.py scripts/full_chain_regression_suites.py apps/api/tests/test_rd_delivery_e2e_harness.py
git commit -m "test: add real rd delivery e2e suite"
```

---

### Task 6: Add cancellation, timeout, rework and high-risk governance scenarios

**Files:**
- Modify: `scripts/full_chain_regression_rd_delivery_e2e.py`
- Modify: `scripts/full_chain_regression.py`
- Modify: `apps/api/tests/test_rd_delivery_e2e_harness.py`

**Interfaces:**
- Consumes the Task 5 configuration and fixture.
- Produces CLI `--rd-e2e-scenario` choices:
  - `happy-path`
  - `quality-rework`
  - `cancel-resume`
  - `timeout-recovery`
  - `high-risk-dispatch`
- Produces `attempt_chain` evidence with immutable attempt numbers and Runner task IDs.

- [ ] **Step 1: Write failing scenario-state tests**

```python
def test_cancel_resume_requires_terminal_cancel_and_new_attempt() -> None:
    timeline = run_cancel_resume_fixture()

    assert timeline.work_item_statuses == (
        "running",
        "cancel_requested",
        "cancelled",
        "rework_required",
        "running",
    )
    assert timeline.attempt_numbers == (1, 2)
    assert timeline.late_result_fenced is True
```

Add equivalent assertions for `quality_gate_failed → rework_required`, `timed_out → waiting_human → ready`, and `high risk → waiting_human → approved dispatch`.

- [ ] **Step 2: Run harness tests and verify the scenario functions are missing**

Run:

```bash
cd apps/api
uv run pytest tests/test_rd_delivery_e2e_harness.py -q
```

Expected: FAIL on undefined scenario runners.

- [ ] **Step 3: Implement `quality-rework`**

Let the first quality-gate Runner result fail, assert the first attempt and evidence are retained, then allow Worker dispatch of attempt 2. The second attempt must pass and require independent review.

- [ ] **Step 4: Implement `cancel-resume`**

Cancel through `/api/delivery/rd-work-items/{id}/cancel`, wait for Runner-confirmed terminal `cancelled`, submit a recorded late-result probe that must be fenced, then resume through `/api/delivery/rd-work-items/{id}/resume`. Do not call AI-task cancel or retry endpoints for the v2 task.

- [ ] **Step 5: Implement `timeout-recovery`**

Use a test policy with `max_iterations=1` and a bounded low timeout only for the dedicated fault fixture. Assert the decision type is `runner_timeout_recovery`, option `retry_after_human_confirmation` restores the frozen `resume_state`, the worktree identifier is unchanged, and attempt 2 is new.

- [ ] **Step 6: Implement `high-risk-dispatch`**

Use risk `high`, assert no Runner task exists before the human decision, select `approve_dispatch`, then assert Worker creates exactly one Runner task.

- [ ] **Step 7: Run focused backend tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_rd_delivery_e2e_harness.py tests/test_rd_collaboration_auto_dispatch.py tests/test_rd_work_item_execution.py -q
uv run ruff check ../../scripts/full_chain_regression_rd_delivery_e2e.py tests/test_rd_delivery_e2e_harness.py
```

Expected: all scenario tests pass and replay checks show no duplicate tasks or attempts.

- [ ] **Step 8: Commit governance scenarios**

```bash
git add scripts/full_chain_regression_rd_delivery_e2e.py scripts/full_chain_regression.py apps/api/tests/test_rd_delivery_e2e_harness.py
git commit -m "test: cover rd delivery recovery scenarios"
```

---

### Task 7: Validate real browser operations and confirmation entry points

**Files:**
- Create: `apps/web/scripts/rd-collaboration-smoke.mjs`
- Modify: `scripts/full_chain_regression_rd_delivery_e2e.py`
- Modify: `apps/web/package.json`
- Modify: `apps/web/tests/TaskCenterPage.test.tsx`
- Modify: `apps/web/tests/IterationVersionsPage.test.tsx`
- Modify: `apps/web/tests/RdCollaborationPage.test.tsx`
- Test: `apps/web/tests/VersionDashboardCollaborationPanel.test.tsx`

**Interfaces:**
- Consumes `RD_E2E_VERSION_ID`, `RD_E2E_RUN_ID`, `RD_E2E_TASK_ID`, local Web/API URLs, reviewer credentials, and `RD_E2E_REVIEW_CHANNEL=api|browser`.
- Produces screenshots and `browser-evidence.json` under `RD_E2E_ARTIFACT_DIR`; values are masked before writing.
- Produces a browser review adapter which the Python E2E orchestrator invokes at a pending Review or high-risk decision when `RD_E2E_REVIEW_CHANNEL=browser`; the Python process resumes only after the browser action is durably visible through the API.

- [ ] **Step 1: Add failing component tests for the required actions**

Assert:

```typescript
expect(screen.getByRole('button', { name: '继续研发协同' })).toBeEnabled();
expect(screen.getByRole('button', { name: '处理待确认' })).toBeEnabled();
expect(screen.getByRole('button', { name: '确认通过' })).toBeEnabled();
```

For v2 tasks, assert direct start, cancel and batch retry actions are absent and the UI directs users to the collaboration work item.

- [ ] **Step 2: Run focused Vitest tests**

Run:

```bash
cd apps/web
npm test -- --run tests/TaskCenterPage.test.tsx tests/IterationVersionsPage.test.tsx tests/RdCollaborationPage.test.tsx tests/VersionDashboardCollaborationPanel.test.tsx
```

Expected: tests expose any remaining missing or hidden confirmation entry.

- [ ] **Step 3: Reconcile the existing TaskCenter changes with test expectations**

Preserve the current pending-review action work in `TaskDetailModal.tsx` and `TaskCenter/index.tsx`. The detail modal must show `处理待确认`, opening the pending Review list for that task; `确认通过` must submit the current Review version and refresh task detail and list state.

- [ ] **Step 4: Implement the Playwright smoke**

The script must:

1. solve the login math challenge;
2. open `/delivery/versions`, locate the supplied version, and open its dashboard;
3. assert the `研发协同` card, status, work-item counts and `继续研发协同` action;
4. follow the action to `/delivery/rd-collaboration?run_id=<id>`;
5. assert the DAG, frozen strategy and `不提供部署操作` boundary;
6. open `/delivery/rd-tasks?task_id=<id>`, open task detail, and assert the pending-review action;
7. when the supplied fixture is at a human decision, select the configured safe option once and verify the state refresh;
8. capture masked screenshots and fail on page errors, console errors, blank content or API 4xx/5xx responses.

- [ ] **Step 5: Connect the browser review channel to the Python orchestrator**

When `RD_E2E_REVIEW_CHANNEL=browser`, `validate_rd_delivery_e2e(...)` must invoke the checked-in browser smoke at the pending gate with only these non-secret identifiers:

```text
RD_E2E_VERSION_ID
RD_E2E_RUN_ID
RD_E2E_TASK_ID
RD_E2E_DECISION_REQUEST_ID
```

Reviewer credentials remain inherited process environment values. After the browser command exits successfully, poll the Review/decision and work-item versions before allowing Worker progression. With `api`, retain the API reviewer path for headless automation.

- [ ] **Step 6: Add the checked-in browser command**

Add:

```json
"test:e2e:rd-collaboration": "node scripts/rd-collaboration-smoke.mjs"
```

to `apps/web/package.json`.

- [ ] **Step 7: Run unit, type and browser validation**

Run:

```bash
cd apps/web
npm test -- --run tests/TaskCenterPage.test.tsx tests/IterationVersionsPage.test.tsx tests/RdCollaborationPage.test.tsx tests/VersionDashboardCollaborationPanel.test.tsx
npm run typecheck
npm run test:e2e:rd-collaboration
```

Expected: component tests pass; real pages render and the permitted confirmation action succeeds once.

- [ ] **Step 8: Commit browser coverage**

```bash
git add scripts/full_chain_regression_rd_delivery_e2e.py apps/web/scripts/rd-collaboration-smoke.mjs apps/web/package.json apps/web/tests/TaskCenterPage.test.tsx apps/web/tests/IterationVersionsPage.test.tsx apps/web/tests/RdCollaborationPage.test.tsx apps/web/src/pages/TaskCenter/components/TaskDetailModal.tsx apps/web/src/pages/TaskCenter/index.tsx
git commit -m "test: verify rd collaboration browser flow"
```

---

### Task 8: Verify role-experience governance and controlled reuse

**Files:**
- Modify: `scripts/full_chain_regression_rd_delivery_e2e.py`
- Modify: `scripts/full_chain_regression.py`
- Modify: `apps/api/tests/test_rd_delivery_e2e_harness.py`
- Modify: `apps/web/tests/RdRoleExperiencesPage.test.tsx`

**Interfaces:**
- Consumes P0 run feedback IDs, `RD_ROLE_EXPERIENCE_ENABLED=true`, a distinct experience reviewer, and a second compatible collaboration run.
- Produces CLI scenario `experience-reuse` and evidence containing experience ID/version/source IDs and the second run’s injected experience references.

- [ ] **Step 1: Write failing API harness tests**

```python
def test_experience_reuse_requires_independent_approval_and_trust_match() -> None:
    evidence = run_experience_fixture()

    assert evidence.pending_status == "pending"
    assert evidence.approved_status == "approved"
    assert evidence.source_feedback_ids
    assert evidence.second_run_reference_ids == (evidence.experience_id,)
    assert evidence.mismatched_run_reference_ids == ()
```

- [ ] **Step 2: Run experience tests and verify the scenario is missing**

Run:

```bash
cd apps/api
RD_ROLE_EXPERIENCE_ENABLED=true uv run pytest tests/test_rd_delivery_e2e_harness.py tests/test_rd_role_experiences.py -q
```

Expected: FAIL on the new harness scenario before implementation.

- [ ] **Step 3: Implement candidate lookup and independent decision**

Query:

```text
GET /api/delivery/rd-role-experiences?evidence_subject_id=<work-item-id>&status=pending
POST /api/delivery/rd-role-experiences/<id>/decide
```

Approve with `{decision: "approve", version, idempotency_key, comment}` from an identity that is neither a source producer nor a producer role.

- [ ] **Step 4: Start a second compatible run and assert frozen reuse**

Enable `experience_reuse_config` with a minimum confidence, maximum one item, exact repository/tool trust domains and `same_policy_version`. Assert the plan/seat context references the approved experience ID and evidence IDs. Create one mismatched trust-domain run and assert zero injected references.

- [ ] **Step 5: Verify the experience page**

Extend `RdRoleExperiencesPage.test.tsx` to assert pending, approved and retired labels, source-evidence visibility, version lock, and independent-review error presentation.

- [ ] **Step 6: Run backend and frontend experience tests**

Run:

```bash
cd apps/api
RD_ROLE_EXPERIENCE_ENABLED=true uv run pytest tests/test_rd_delivery_e2e_harness.py tests/test_rd_role_experiences.py -q
cd ../web
npm test -- --run tests/RdRoleExperiencesPage.test.tsx
```

Expected: approved experience is reused only in the compatible run.

- [ ] **Step 7: Commit experience E2E coverage**

```bash
git add scripts/full_chain_regression_rd_delivery_e2e.py scripts/full_chain_regression.py apps/api/tests/test_rd_delivery_e2e_harness.py apps/web/tests/RdRoleExperiencesPage.test.tsx
git commit -m "test: verify controlled rd experience reuse"
```

---

### Task 9: Execute the real P0 chain, document evidence, and run final gates

> **Sequencing ruling (2026-07-28):** Task 8's causal P1 reuse assertion
> runs after this task has produced a real P0 source run and immutable feedback.
> The source candidate must be found by its actual feedback producer subject
> (or an explicit expected experience ID), never by treating a work-item ID as
> `evidence_subject_id`. Its compatible and trust-mismatched successor runs
> must be created after independent approval through the public collaboration
> APIs; pre-created runs are not evidence of causal frozen reuse. The prior
> Task 8 coverage commit remains local and unpushed until this repair is made.

**Files:**
- Modify: `docs/08-help/delivery.md`
- Modify: `docs/changelog.md`
- Modify: `docs/superpowers/plans/2026-07-26-rd-collaboration-e2e-test.md` only to check completed boxes and record the final evidence directory.

**Interfaces:**
- Consumes all prior tasks and a healthy local PostgreSQL/API/Web/Worker/Runner stack.
- Produces a machine-readable report, masked browser evidence, remote test branch, final test summary, and no deployment record.

- [ ] **Step 1: Run fast automated gates**

Run:

```bash
cd apps/api
uv run pytest tests/test_full_chain_rd_collaboration_regression.py tests/test_rd_delivery_e2e_harness.py tests/test_rd_collaboration_delivery.py tests/test_rd_collaboration_auto_dispatch.py tests/test_rd_work_item_execution.py tests/test_rd_role_experiences.py -q
uv run ruff check ../../scripts/full_chain_regression.py ../../scripts/full_chain_regression_rd_fixture.py ../../scripts/full_chain_regression_rd_runner_protocol.py ../../scripts/full_chain_regression_rd_delivery_e2e.py
cd ../web
npm test -- --run tests/TaskCenterPage.test.tsx tests/IterationVersionsPage.test.tsx tests/RdCollaborationPage.test.tsx tests/VersionDashboardCollaborationPanel.test.tsx tests/RdRoleExperiencesPage.test.tsx
npm run typecheck
npm run build
```

Expected: all commands pass.

- [ ] **Step 2: Verify live service preconditions**

Check API health, Web render, Worker heartbeat and selected Runner heartbeat. Record IDs and statuses in the E2E report; do not print tokens or credential references.

- [ ] **Step 3: Run the real happy path exactly once**

Run:

```bash
FULL_CHAIN_USERNAME=admin@example.com \
FULL_CHAIN_PASSWORD=admin123 \
FULL_CHAIN_JSON_OUTPUT=/private/tmp/e-ai-brain-rd-e2e/happy-path.json \
RD_E2E_REVIEW_CHANNEL=browser \
python scripts/full_chain_regression.py \
  --suite rd-delivery-e2e \
  --rd-e2e-scenario happy-path
```

Supply all `RD_E2E_*` variables through the process environment. Expected: the orchestrator pauses at each configured human gate only long enough for the checked-in browser smoke to perform the permitted action; report status is `passed`, remote `rd/<run>/<work-item>` branches are reconciled, the run completes for `ready_for_release`, and deployment count is zero.

- [ ] **Step 4: Run the required recovery scenarios**

Run `quality-rework`, `cancel-resume`, `timeout-recovery`, and `high-risk-dispatch` as separate runs with separate JSON output files. A failed scenario remains preserved and is repaired through its work item; do not delete and recreate its records.

- [ ] **Step 5: Re-run read-only browser validation against the completed happy-path IDs**

Run:

```bash
cd apps/web
RD_E2E_ARTIFACT_DIR=/private/tmp/e-ai-brain-rd-e2e/browser \
npm run test:e2e:rd-collaboration
```

Expected: version dashboard, collaboration DAG, completed Review state and no-deployment notice render without relevant runtime or console errors. The state-changing confirmation was already exercised by the browser review channel in Step 3.

- [ ] **Step 6: Run P1 experience reuse after P0 passes**

Run the `experience-reuse` scenario with `RD_ROLE_EXPERIENCE_ENABLED=true`. Preserve both the source run and compatible second run IDs.

- [ ] **Step 7: Update help and changelog from verified behavior**

Document:

- low/medium automatic dispatch and high-risk human dispatch;
- the native `rd/<run>/<work-item>` test branch;
- task-detail confirmation entry;
- cancel/resume and timeout recovery;
- `ready_for_release` as the no-deployment endpoint;
- role-experience independent approval and controlled reuse.

Use only screenshots captured from the real local UI and mask tokens, private URLs and personal information.

- [ ] **Step 8: Run documentation and repository hygiene checks**

Run:

```bash
cd apps/web
npm run help:check
cd ../..
git diff --check
git status --short
```

Expected: help asset references are valid, no whitespace errors exist, and only intended files remain modified.

- [ ] **Step 9: Commit final documentation**

```bash
git add docs/08-help/delivery.md docs/changelog.md docs/superpowers/plans/2026-07-26-rd-collaboration-e2e-test.md
git commit -m "docs: record rd collaboration e2e verification"
```

- [ ] **Step 10: Final completion gate**

Do not report “full-chain passed” unless all of these are present in the final evidence:

```text
requirement assessment accepted
version grouping and immutable policy snapshot
AI Runner implementation and test attempts
independent quality gates and human reviews
coding and integration remote SHA reconciliation
run completed with completion_reason=ready_for_release
product version status=ready_for_release
deployment records=0
browser confirmation entry verified
```

Report P1 experience reuse separately from the P0 delivery result.
