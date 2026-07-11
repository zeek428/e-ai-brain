# Operational Deployment Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent “运营治理 / 运维部署” menu and page while keeping deployment state in the existing deployment APIs and removing deployment management from the log-monitoring page.

**Architecture:** Add a DB-seeded RBAC menu resource guarded by `deployment.read`, create a focused React deployment page that uses the existing paged operational read model plus existing deployment write APIs, and make log monitoring exclude deployment rows at the server query layer. Route all deployment-specific deep links to the new page and gate high-risk UI actions by the current user's permissions.

**Tech Stack:** FastAPI, PostgreSQL repository read model, React 19, TypeScript, Ant Design Pro, Vitest, pytest.

## Global Constraints

- PostgreSQL remains the production source of truth; no new frontend-only or process-memory business state.
- Backend permissions and product scope remain authoritative.
- Deployment menu access requires `deployment.read`.
- Deployment actions require their existing `deployment.create`, `deployment.execute`, or `deployment.cancel` permissions.
- Existing unrelated working-tree changes must be preserved.

---

### Task 1: Seed and verify the deployment menu resource

**Files:**
- Modify: `apps/api/tests/test_rbac_foundation.py`
- Modify: `apps/api/app/core/repositories/authorization_defaults.py`
- Modify: `apps/api/app/core/roles.py`
- Create: `apps/api/app/db/migrations/100_operational_deployment_menu.sql`

**Interfaces:**
- Produces: menu code `governance.deployments`, path `/governance/deployments`, required permission `deployment.read`.

- [ ] Add a failing RBAC test asserting the compatibility resource, default grants, migration seed, and role menu labels.
- [ ] Run `cd apps/api && uv run pytest tests/test_rbac_foundation.py -q` and confirm the new assertion fails because the menu does not exist.
- [ ] Add the compatibility resource, default role grants, role metadata labels, and idempotent SQL migration.
- [ ] Re-run the RBAC test and confirm it passes.

### Task 2: Separate deployment records from log monitoring

**Files:**
- Modify: `apps/api/tests/test_management_list_read_models.py`
- Modify: `apps/api/app/api/routers/devops_metrics.py`
- Modify: `apps/api/app/services/devops_metrics.py`
- Modify: `apps/api/app/core/repositories/devops.py`
- Modify: `apps/web/src/services/devopsOperationsClient.ts`

**Interfaces:**
- Produces: optional `exclude_category` on `GET /api/devops/operational-metrics` and `excludeCategory` in `OperationalMetricListQuery`.

- [ ] Add a failing API test proving `exclude_category=运维部署` removes deployment rows and fixes the paged total.
- [ ] Run the focused backend test and confirm the deployment row is still returned.
- [ ] Thread the exclusion through router, service, repository SQL, and memory fallback.
- [ ] Re-run the focused backend test and existing management-list tests.

### Task 3: Build the independent deployment page

**Files:**
- Modify: `apps/web/tests/OperationalInsightsPages.test.tsx`
- Create: `apps/web/src/pages/Deployments/index.tsx`
- Modify: `apps/web/src/pages/Devops/index.tsx`
- Modify: `apps/web/config/routes.ts`
- Modify: `apps/web/src/services/authClient.ts`
- Modify: `apps/web/src/services/devopsOperationsClient.ts`

**Interfaces:**
- Consumes: `fetchDevopsMetricList`, deployment write APIs, product context APIs, and stored current-user permissions.
- Produces: route component `./Deployments` at `/governance/deployments`.

- [ ] Add a failing frontend test that imports the new page, loads only deployment rows, verifies permission-gated actions, creates a deployment, and confirms log monitoring no longer exposes deployment management.
- [ ] Run `cd apps/web && npm test -- OperationalInsightsPages.test.tsx` and confirm the missing page/behavior fails.
- [ ] Implement the focused deployment page and current-user permission helper; remove deployment forms/actions from `DevopsPage` and pass `excludeCategory` in its list query.
- [ ] Add the frontend route and re-run the focused test.

### Task 4: Update deployment deep links and user documentation

**Files:**
- Modify: `apps/web/src/pages/IterationVersions/components/versionDashboardModel.ts`
- Modify: `apps/web/src/pages/IterationVersions/components/VersionDashboardSummary.tsx`
- Modify: `apps/web/src/pages/IterationVersions/components/VersionDashboardTables.tsx`
- Modify: `apps/web/src/components/RequirementFullChainView/index.tsx`
- Modify: `apps/web/tests/IterationVersionsPage.test.tsx`
- Modify: `apps/web/src/pages/Help/helpContent.ts`
- Modify: `docs/08-help/tasks-and-governance.md`
- Modify: `docs/08-help/delivery.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/02-specs/enterprise-ai-brain/api/devops-quality-and-code-inspection.md`
- Modify: `docs/changelog.md`

**Interfaces:**
- Produces: deployment links under `/governance/deployments`; Jenkins release links remain under `/governance/devops`.

- [ ] Update route assertions first and run the focused version-page tests to confirm old URLs fail.
- [ ] Update deployment-specific links without changing Jenkins release links.
- [ ] Add a separate help-center article and revise delivery/governance instructions.
- [ ] Update the active spec, API contract, acceptance test, and changelog.

### Task 5: Verify the integrated behavior

**Files:**
- Update from real UI when feasible: `docs/08-help/assets/screenshots/help-deployments.png`

**Interfaces:**
- Verifies: menu visibility, page identity, permission-gated buttons, list loading, deployment modal, deep-link routing, and console health.

- [ ] Run focused backend tests, focused frontend tests, `npm run typecheck`, `npm run help:check`, and `git diff --check`.
- [ ] Start the PostgreSQL-backed API and web app using checked-in commands.
- [ ] Log in as an authorized role and verify `/governance/deployments` in the real browser, including one deployment interaction that does not mutate a completed production deployment.
- [ ] Capture the help screenshot with sensitive values masked and re-run help checks.
- [ ] Inspect `git diff` and report unrelated pre-existing changes separately.
