# Release Readiness And Post Release Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the v1.2 AI task types `release_readiness` and `post_release_analysis` as real task workflows using existing product, requirement, Bug, Jenkins, GitLab metric, online log, model gateway, review, audit, and task-center infrastructure.

**Architecture:** Keep the FastAPI modular-monolith pattern in `apps/api/app/main.py`, reusing the existing `ai_tasks`, `human_reviews`, `graph_runs`, `graph_checkpoints`, `knowledge_deposits`, and `bugs` persistence. Do not add fallback/demo data. The new tasks are low-level `POST /api/ai-tasks` follow-ups, then use the existing `POST /api/ai-tasks/{task_id}/start` and review endpoints for model execution and human gates.

**Tech Stack:** FastAPI, Pydantic, PostgreSQL-backed `PersistentMemoryStore`, React + TypeScript + Ant Design Pro, Vitest, pytest, ruff.

---

## Current Evidence

- `apps/api/app/main.py` currently accepts `technical_solution`, `development_planning`, `automated_testing`, and `code_review`; unknown task types still raise `VALIDATION_ERROR / Unsupported task_type`.
- `docs/02-specs/enterprise-ai-brain/test-case.md` keeps `release_readiness` and `post_release_analysis` as pending under `TC-AIBRAIN-TASK-FUNC-020` and `TC-AIBRAIN-REVIEW-FUNC-024`.
- Real input data already exists:
  - `bugs` through `/api/bugs`
  - GitLab daily metrics through `/api/devops/gitlab/daily-code-metrics`
  - Jenkins releases through `/api/devops/jenkins/releases`
  - online log metrics through `/api/ops/online-log-metrics`
  - user feedback/usage/iteration evidence through `/api/insights/*` and `/api/planning/*`
- Task Center already has the modal operation pattern and can create follow-up tasks from completed technical-solution tasks.

## Scope

In scope:
- `release_readiness` task creation from a confirmed `technical_solution`.
- `post_release_analysis` task creation from a confirmed `release_readiness`.
- Model-gateway output validation through test fixtures.
- Human review gates for both task types.
- Optional Bug generation from `post_release_analysis.bug_suggestions` after human approval.
- Task Center actions and labels for both new task types.
- Docs/test-case/changelog updates.

Out of scope for this slice:
- External automatic Jenkins/GitLab/log collectors.
- Real GitLab writeback or deployment actions.
- Multi-tenant role expansion beyond current role catalog.
- GBrain long-memory connector.

## Backend Tasks

### Task 1: Add Failing API Tests

**Files:**
- Create: `apps/api/tests/test_release_analysis_task_types.py`
- Modify: `apps/api/tests/conftest.py`

- [x] Write tests proving `release_readiness` can be created from a confirmed `technical_solution`, started, and moved to `waiting_review`.
- [x] Write tests proving `post_release_analysis` can be created from a completed `release_readiness`, started, approved, and converted into post-release Bug records when model output includes `bug_suggestions`.
- [x] Write tests proving missing or unconfirmed source tasks return precise errors:
  - `TECHNICAL_SOLUTION_NOT_CONFIRMED`
  - `RELEASE_READINESS_NOT_CONFIRMED`
- [x] Run:

```bash
cd apps/api
uv run pytest tests/test_release_analysis_task_types.py
```

Expected before implementation: failures at `Unsupported task_type`.

### Task 2: Extend Test Model Gateway Fixtures

**Files:**
- Modify: `apps/api/tests/conftest.py`

- [x] Add fake model outputs:
  - `release_readiness`: `kind`, `summary`, `go_live_decision`, `risk_level`, `checklist`, `risk_assessment`, `rollback_plan`.
  - `post_release_analysis`: `kind`, `summary`, `health_report`, `anomaly_trends`, `optimization_suggestions`, `bug_suggestions`.
- [x] Keep fixture deterministic and JSON-only.

### Task 3: Accept Release Task Creation

**Files:**
- Modify: `apps/api/app/main.py`

- [x] Add constants:
  - `TECHNICAL_SOLUTION_FOLLOWUP_TASK_TYPES = {"development_planning", "automated_testing", "release_readiness"}`
  - `RELEASE_READINESS_FOLLOWUP_TASK_TYPES = {"post_release_analysis"}`
- [x] Add helper `_ensure_confirmed_release_readiness_task(...)`.
- [x] For `release_readiness`, require `input.technical_solution_task_id` to reference a completed `technical_solution` on the same requirement/product/version.
- [x] For `post_release_analysis`, require `input.release_readiness_task_id` to reference a completed `release_readiness` on the same requirement/product/version.
- [x] Keep requirement state check unchanged: only `approved` or `task_created`.
- [x] Keep existing roles unless role catalog is intentionally expanded: `product_owner`, `rd_owner`, and `admin` can create/start/approve non-code-review task types.

### Task 4: Build Real Context Payloads

**Files:**
- Modify: `apps/api/app/main.py`

- [x] Enrich `task["input_json"]` for `release_readiness` with snapshots of:
  - source technical solution task summary/output
  - open/non-closed Bugs for same product/version/requirement
  - Jenkins release records for same product/version
  - online log metrics for same product/module
  - GitLab daily code metrics for same product repositories
- [x] Enrich `task["input_json"]` for `post_release_analysis` with snapshots of:
  - source release-readiness task summary/output
  - Jenkins release records for same product/version
  - online log metrics for same product/module
  - recent Bugs for same product/version/requirement
- [x] Do not synthesize missing records. Empty inputs must be real empty arrays.

### Task 5: Convert Post-Release Bug Suggestions After Approval

**Files:**
- Modify: `apps/api/app/main.py`
- Modify: `apps/web/src/pages/Bugs/index.tsx`
- Modify: `apps/web/src/services/aiBrain.ts`
- Modify docs enum descriptions in `docs/02-specs/enterprise-ai-brain/api.md`

- [x] Add Bug source `ai_post_release` for suspected regression Bugs from post-release analysis.
- [x] Reuse Bug creation shape:
  - `product_id`, `version_id`, `module_code`
  - `related_task_id`
  - `requirement_id`
  - `reproduce_steps`
  - `evidence.generated_by_task_type = "post_release_analysis"`
- [x] Only create these Bugs after `approve` or `edit-approve`.
- [x] Audit with:
  - `bug.created`
  - `post_release_analysis.bugs_created`
- [x] Update Bug page source labels and source select options.

## Frontend Tasks

### Task 6: Add Task Center Actions

**Files:**
- Modify: `apps/web/src/services/aiBrain.ts`
- Modify: `apps/web/src/pages/TaskCenter/index.tsx`
- Modify: `apps/web/tests/App.test.tsx`

- [x] Add task labels:
  - `release_readiness`: `发布评估`
  - `post_release_analysis`: `上线后分析`
- [x] Add service functions:
  - `createReleaseReadinessTask(task)`
  - `createPostReleaseAnalysisTask(task)`
- [x] For completed `technical_solution`, add action `生成发布评估`.
- [x] For completed `release_readiness`, add action `生成上线后分析`.
- [x] Existing `启动任务` and `确认输出` actions should work unchanged.

### Task 7: Add Frontend Service And Page Tests

**Files:**
- Modify: `apps/web/tests/App.test.tsx`

- [x] Assert Task Center operation modal shows `生成发布评估` for completed technical-solution rows.
- [x] Assert Task Center operation modal shows `生成上线后分析` for completed release-readiness rows.
- [x] Assert service request bodies:

```json
{
  "task_type": "release_readiness",
  "title": "发布评估：<source title>",
  "requirement_id": "<requirement id>",
  "input": {
    "technical_solution_task_id": "<task id>"
  }
}
```

```json
{
  "task_type": "post_release_analysis",
  "title": "上线后分析：<source title>",
  "requirement_id": "<requirement id>",
  "input": {
    "release_readiness_task_id": "<task id>"
  }
}
```

## Documentation Tasks

### Task 8: Update Product Docs

**Files:**
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/changelog.md`
- Modify: `AGENTS.md`

- [x] Document the new task creation preconditions.
- [x] Document the post-release Bug source and audit events.
- [x] Mark `TC-AIBRAIN-TASK-FUNC-020` and `TC-AIBRAIN-REVIEW-FUNC-024` as automated for these two task types.
- [x] Keep external collectors and full dashboard/lifecycle v1.2 expansion as separate follow-up slices unless implemented in the same commit.

## Verification

Run all of these before committing:

```bash
cd apps/api
uv run ruff check
uv run pytest tests/test_release_analysis_task_types.py
uv run pytest

cd ../web
npm test
npm run build
```

Browser smoke test on the local code environment:

1. Start local API on `8000` and local Web on `5173`.
2. Use a configured model gateway or a temporary local smoke gateway.
3. Create or find a completed `technical_solution`.
4. In Task Center, generate `release_readiness`.
5. Start and approve it.
6. Generate `post_release_analysis`.
7. Start and approve it.
8. Verify any `bug_suggestions` become `ai_post_release` Bugs.

## Commit

Use one commit after tests and browser smoke pass:

```bash
git add AGENTS.md apps/api/app/main.py apps/api/tests/conftest.py apps/api/tests/test_release_analysis_task_types.py apps/web/src/pages/TaskCenter/index.tsx apps/web/src/services/aiBrain.ts apps/web/tests/App.test.tsx docs/02-specs/enterprise-ai-brain/api.md docs/02-specs/enterprise-ai-brain/spec.md docs/02-specs/enterprise-ai-brain/test-case.md docs/changelog.md
git commit -m "feat: add release analysis task workflows"
git push origin master
```

## Confirmation Needed

Before implementation, confirm this slice exactly:

- Build both `release_readiness` and `post_release_analysis` now.
- Add `ai_post_release` as a new Bug source.
- Keep external automatic collectors, dashboard v1.2 expansion, and lifecycle v1.2 expansion for later confirmed slices.
