# MVP Remaining Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining MVP/v1-series gaps as real database-backed product behavior, without demo data or frontend fallback rows.

**Architecture:** Keep the current FastAPI modular monolith plus Ant Design Pro workbench. Use PostgreSQL-owned business tables and existing service functions first; extend API contracts, tests, and docs before changing UI behavior.

**Tech Stack:** FastAPI, PostgreSQL + pgvector, Redis, React + TypeScript, Ant Design Pro, Vitest, pytest, Chrome browser smoke tests.

---

## Execution Status

This plan is now a historical execution record. The five slices in this file were completed through follow-up commits:

- Task 1 status reconciliation: `3bbdd26 docs: reconcile mvp test coverage status`
- Task 2 Bug management full UI lifecycle: `5e2ac0e feat: complete bug lifecycle UI`
- Task 3 Dashboard v1.2 drilldown: `8cbb818 feat: add dashboard operational drilldowns`
- Task 4 Lifecycle v1.2 evidence expansion: `ff9f6a3 feat: expand lifecycle evidence graph`
- Task 5 Collector run tracking: `fd9e7b1 feat: add collector run tracking`

The next unimplemented MVP/v1-series gap is tracked separately in `docs/superpowers/plans/2026-06-02-pending-attribution-queue.md` and requires explicit user confirmation before implementation.

## Current Evidence Snapshot

- Current pushed baseline: `8ed0f3e docs: plan pending attribution queue`.
- Latest full implementation verification for collector-run tracking: `cd apps/api && uv run pytest` -> `140 passed`; `cd apps/web && npm test` -> `50 passed`; `cd apps/web && npm run build` -> success; browser smoke on `/governance/devops` created and completed `collector_run_002`.
- Current local source services were health checked after the plan update: API `/health` returned `ok`, and Web `http://127.0.0.1:5173/` returned HTTP 200.
- Known implemented real-data areas: authentication, users, roles, product/version/module/Git CRUD, requirements, task workflow, reviews, GitLab MR preview/snapshot, code review reports, knowledge documents/chunks/deposits, mock issue writeback, model gateway config/logs, Bug API/UI lifecycle, DevOps manual metrics, collector run tracking, user feedback, usage metrics, iteration suggestions, lifecycle v1.2 evidence tracing, and dashboard operational drilldowns.

## Confirmation Options

Historical menu. Do not execute these stale options again; they are completed or superseded.

1. Documentation/status reconciliation only: update stale `待测试` statuses where current automated tests already prove completion.
2. Bug management full UI lifecycle (Recommended): complete TC-AIBRAIN-BUG-FUNC-018 from the browser, including reproduce steps, evidence JSON, duplicate merge, and explicit status transitions.
3. Dashboard v1.2 drilldown: add Bug/DevOps/usage/feedback/iteration summary cards and preserve product/time-range context when drilling into subject pages.
4. Lifecycle v1.2 evidence expansion: connect GitLab metrics, Jenkins releases, online logs, usage metrics, user feedback, and iteration suggestions into `/api/lifecycle/context`.
5. External collector run records: introduce explicit collector run APIs for GitLab/Jenkins/online logs/usage imports, with audit events and failure visibility.

## Task 1: Reconcile Stale Test Statuses

**Files:**
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Inspect: `apps/api/tests/*.py`
- Inspect: `apps/web/tests/App.test.tsx`

- [x] **Step 1: Build an evidence table**

  Map each `**状态**: 待测试` case to exact automated tests. Examples already visible:
  - TC-AIBRAIN-TASK-FUNC-001: `apps/api/tests/test_mvp_a_flow.py::test_requirement_to_product_detail_design_human_review_flow`
  - TC-AIBRAIN-KNOWLEDGE-FUNC-005: `apps/api/tests/test_knowledge_governance.py`
  - TC-AIBRAIN-REVIEW-FUNC-023A: `apps/api/tests/test_gitlab_snapshot.py`
  - TC-AIBRAIN-REVIEW-FUNC-023B: `apps/api/tests/test_code_review_report.py`
  - TC-AIBRAIN-FLOW-FUNC-021: `apps/api/tests/test_lifecycle_context.py`

- [x] **Step 2: Run proving tests**

  Run:

  ```bash
  cd apps/api && uv run pytest
  cd apps/web && npm test
  ```

  Expected: all backend and frontend tests pass.

- [x] **Step 3: Update status wording**

  Replace stale `待测试` entries only when exact tests cover the stated behavior. Keep external collector, Docker release gate, full dashboard drilldown, and full lifecycle v1.2 items marked as later-stage or pending.

- [x] **Step 4: Commit**

  ```bash
  git add docs/02-specs/enterprise-ai-brain/test-case.md
  git commit -m "docs: reconcile mvp test coverage status"
  ```

## Task 2: Bug Management Full UI Lifecycle

**Files:**
- Modify: `apps/web/src/data/management.ts`
- Modify: `apps/web/src/services/aiBrain.ts`
- Modify: `apps/web/src/pages/Bugs/index.tsx`
- Modify: `apps/web/tests/App.test.tsx`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Add failing frontend tests**

  Add Vitest coverage proving the Bug page can:
  - create `manual_test` Bugs with reproduce steps and evidence JSON;
  - update status through `triaged -> assigned -> fixed -> verified -> closed`;
  - set `duplicate_of_bug_id` from an existing Bug;
  - show backend validation errors without local fallback rows.

  Run:

  ```bash
  cd apps/web && npm test -- App.test.tsx
  ```

  Expected before implementation: the new tests fail because the page currently only edits title/severity/status/assignee/description and does not expose duplicate/evidence/reproduce fields.

- [x] **Step 2: Extend frontend data mapping**

  Add these fields to `BugRecord` and service mapping:
  - `duplicateOfBugId?: string`
  - `evidence?: Record<string, unknown>`
  - `reproduceSteps?: string[]`
  - `requirementId?: string`
  - `relatedTaskId?: string`

  Preserve existing API payload names when sending mutations:
  - `duplicate_of_bug_id`
  - `evidence`
  - `reproduce_steps`
  - `requirement_id`
  - `related_task_id`

- [x] **Step 3: Complete the Bug modal**

  In `apps/web/src/pages/Bugs/index.tsx`, add:
  - reproduce steps textarea, stored as one non-empty line per step;
  - evidence JSON textarea with JSON array/object validation;
  - duplicate Bug selector populated from current rows, excluding the current Bug;
  - explicit status selector on edit, using the backend status values already supported;
  - source display for AI-created Bugs, while keeping source editable only on create.

- [x] **Step 4: Re-run frontend tests**

  Run:

  ```bash
  cd apps/web && npm test -- App.test.tsx
  cd apps/web && npm test
  cd apps/web && npm run build
  ```

  Expected: all frontend tests pass and production build succeeds.

- [x] **Step 5: Browser smoke**

  Use the running source services:
  - API: `http://127.0.0.1:8000`
  - Web: `http://127.0.0.1:5173`

  Verify in Chrome:
  - open `/delivery/bugs`;
  - create a manual Bug;
  - edit status and assignee;
  - mark another Bug as duplicate;
  - no demo/fallback rows appear after refresh.

- [x] **Step 6: Commit**

  ```bash
  git add apps/web/src/data/management.ts apps/web/src/services/aiBrain.ts apps/web/src/pages/Bugs/index.tsx apps/web/tests/App.test.tsx docs/02-specs/enterprise-ai-brain/api.md docs/02-specs/enterprise-ai-brain/test-case.md docs/changelog.md
  git commit -m "feat: complete bug management lifecycle UI"
  git push origin master
  ```

## Task 3: Dashboard v1.2 Drilldown

**Files:**
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_empty_collections.py`
- Modify: `apps/web/src/pages/Dashboard/index.tsx`
- Modify: `apps/web/src/services/aiBrain.ts`
- Modify: `apps/web/tests/App.test.tsx`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Add backend dashboard fields**

  Extend `GET /api/dashboard/it-team` with product/time-range scoped summaries for:
  - Bug status counts and latest high severity Bugs;
  - GitLab daily metric totals;
  - Jenkins release status counts;
  - online log error/latency summary;
  - user feedback status counts;
  - usage metric summary;
  - iteration suggestion status counts.

- [x] **Step 2: Add drilldown URL contract**

  Preserve `product_id` and `time_range` when navigating to:
  - `/delivery/bugs`
  - `/governance/devops`
  - `/governance/insights`
  - `/governance/audit`

- [x] **Step 3: Add frontend cards**

  Add compact dashboard cards using existing dashboard layout, not nested cards. Cards should show real zeros when no records exist and should never create fake rows.

- [x] **Step 4: Test and commit**

  Run:

  ```bash
  cd apps/api && uv run pytest tests/test_empty_collections.py
  cd apps/web && npm test -- App.test.tsx
  cd apps/web && npm run build
  ```

  Commit with:

  ```bash
  git commit -m "feat: add dashboard operational drilldowns"
  ```

## Task 4: Lifecycle v1.2 Evidence Expansion

**Files:**
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_lifecycle_context.py`
- Modify: `apps/web/src/pages/Audit/index.tsx`
- Modify: `apps/web/tests/App.test.tsx`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Replace static missing context**

  In `/api/lifecycle/context`, compute `missing_context` dynamically from actual absence of matching Bugs, GitLab metrics, Jenkins releases, online logs, usage metrics, feedback, and iteration suggestions.

- [x] **Step 2: Add evidence relations**

  Add upstream/downstream relation builders for:
  - `gitlab_daily_code_metric`
  - `jenkins_release`
  - `online_log_metric`
  - `user_usage_metric`
  - `user_feedback`
  - `iteration_plan_suggestion`

- [x] **Step 3: Add risk signals**

  Produce source-specific risk signals for high risk counts, failed releases, high online error rates, unresolved severe Bugs, negative feedback, and low-confidence iteration suggestions.

- [x] **Step 4: Test and commit**

  Run:

  ```bash
  cd apps/api && uv run pytest tests/test_lifecycle_context.py
  cd apps/api && uv run pytest
  ```

  Commit with:

  ```bash
  git commit -m "feat: expand lifecycle evidence graph"
  ```

## Task 5: External Collector Run Records

**Files:**
- Create: `apps/api/app/db/migrations/012_collector_runs.sql`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_collector_runs.py`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Add `collector_runs` table**

  Store:
  - `id`
  - `collector_type`
  - `product_id`
  - `status`
  - `source_system`
  - `started_at`
  - `finished_at`
  - `records_imported`
  - `error_message`
  - `payload_summary`

- [x] **Step 2: Add APIs**

  Add:
  - `GET /api/collectors/runs`
  - `POST /api/collectors/runs`
  - `PATCH /api/collectors/runs/{run_id}`

  These APIs record real ingestion attempts and audit them. They do not invent metrics; imported metrics still go through the existing GitLab/Jenkins/log/usage endpoints.

- [x] **Step 3: Test and commit**

  Run:

  ```bash
  cd apps/api && uv run pytest tests/test_collector_runs.py
  cd apps/api && uv run pytest
  ```

  Commit with:

  ```bash
  git commit -m "feat: add collector run tracking"
  ```

## Execution Gate

Do not implement any new task from this historical plan. The active next-step candidate is pending attribution queue, documented in `docs/superpowers/plans/2026-06-02-pending-attribution-queue.md`; implementation requires explicit user confirmation.
