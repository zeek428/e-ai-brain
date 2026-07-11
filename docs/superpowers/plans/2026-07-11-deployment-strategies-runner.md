# Deployment Strategies and Runner Execution Plan

> **For Codex:** Follow this plan task by task. Keep existing uncommitted work intact. Do not commit or push unless explicitly requested.

**Goal:** Add governed deployment schemes for manual, SSH, Docker, and Jenkins deployment, with SSH and Docker executed by an isolated local AI Brain Runner.

**Architecture:** A deployment request selects a versioned deployment scheme. Manual schemes retain the current human completion flow. SSH and Docker schemes enqueue a deployment-capable runner task that executes only preconfigured local targets. Jenkins schemes invoke an official plugin connection and are reconciled by a leased background sync worker. Requests and run records store non-secret immutable snapshots for auditability.

**Tech Stack:** FastAPI, PostgreSQL migrations and repositories, React + TypeScript + Ant Design, generated local runner package, pytest, Vitest, real browser validation.

## Guardrails

- Never store SSH private keys, remote host credentials, or Docker endpoint credentials in PostgreSQL, API responses, browser state, logs, or deployment snapshots.
- A runner heartbeat may expose target code, name, method, and readiness only.
- SSH and Docker deployments must use a preconfigured target code, not arbitrary user-entered commands.
- Retain a cancelling state until the runner or Jenkins confirms cancellation.
- Preserve all current dirty worktree changes outside the touched implementation surface.
- Update help documentation and real screenshots for visible workflow changes.

## Task 1: Persist Deployment Schemes and Execution Metadata

**Files:**
- Create: apps/api/app/db/migrations/101_deployment_strategies.sql
- Modify: apps/api/app/core/persistence.py
- Modify: apps/api/app/core/persistence_contracts.py
- Modify: apps/api/app/core/repositories/devops.py
- Modify: apps/api/app/core/repositories/devops_writes.py
- Modify: apps/api/tests/test_persistence_repository_boundaries.py
- Create: apps/api/tests/test_deployment_strategy_repository.py

**Step 1: Write failing repository tests**

Cover:
- creating and listing product-scoped deployment schemes;
- one active default per product and environment;
- immutable non-secret scheme snapshots on deployment requests;
- run fields for method, runner task id, external queue/build URLs, sync lease, and idempotency key;
- ai executor task association with a deployment run and cancel_requested status.

**Step 2: Run tests to verify red state**

Run:
~~~bash
cd apps/api && uv run pytest tests/test_deployment_strategy_repository.py tests/test_persistence_repository_boundaries.py -q
~~~

Expected: failures because tables, repository methods, and proxy contracts do not exist.

**Step 3: Implement minimal persistence support**

Add deployment_schemes and deployment_run execution columns. Add deployment_run_id and cancel_requested support to ai_executor_tasks. Add indexes for product environment default lookup, active runs, and sync leasing. Add repository read/write methods and expose them through PostgresSnapshotRepository contracts. Register the migration in the persistence migration list.

**Step 4: Run focused tests**

Run the Task 1 command again.

Expected: PASS.

**Step 5: Commit**

Do not commit automatically in this dirty working tree. When requested, use:
~~~bash
git add apps/api/app/db/migrations/101_deployment_strategies.sql apps/api/app/core/persistence.py apps/api/app/core/persistence_contracts.py apps/api/app/core/repositories/devops.py apps/api/app/core/repositories/devops_writes.py apps/api/tests/test_persistence_repository_boundaries.py apps/api/tests/test_deployment_strategy_repository.py
git commit -m "feat: persist deployment schemes and execution metadata"
~~~

## Task 2: Add Deployment Scheme APIs, Permissions, and Defaults

**Files:**
- Modify: apps/api/app/services/operational_deployments.py
- Modify: apps/api/app/api/routers/devops_metrics.py
- Modify: apps/api/app/core/roles.py
- Modify: apps/api/app/core/repositories/authorization.py
- Modify: apps/api/app/services/products.py
- Modify: apps/api/tests/test_operational_deployments.py
- Create: apps/api/tests/test_deployment_schemes_api.py
- Modify: docs/02-specs/enterprise-ai-brain/api.md
- Modify: docs/02-specs/enterprise-ai-brain/spec.md

**Step 1: Write failing API and service tests**

Cover:
- CRUD endpoints for product-scoped deployment schemes;
- optimistic version validation;
- automatic default manual scheme creation for a new product and migration backfill;
- permission deployment.scheme.manage granted to system admin and release owner;
- referenced schemes reject physical deletion;
- product scope enforcement for list, read, mutation, and deployment request selection.

**Step 2: Run tests to verify red state**

Run:
~~~bash
cd apps/api && uv run pytest tests/test_deployment_schemes_api.py tests/test_operational_deployments.py -q
~~~

Expected: failures because routes and scheme resolution do not exist.

**Step 3: Implement the API contract**

Expose:
- GET and POST /api/devops/deployment-schemes
- GET, PATCH, and DELETE /api/devops/deployment-schemes/{scheme_id}
- GET /api/devops/deployment-runner-targets?runner_id=&method=

Validate method/channel combinations:
- manual uses manual channel and no runner or integration binding;
- ssh and docker use runner channel, runner_id, and target_code;
- jenkins uses integration channel, connection and job binding.

Create a default manual scheme for every product. Add permission checks, product scope checks, immutable snapshot construction, audit events, and documented error responses.

**Step 4: Run focused tests**

Run the Task 2 command again.

Expected: PASS.

**Step 5: Commit**

Do not commit automatically. When requested:
~~~bash
git add apps/api/app/services/operational_deployments.py apps/api/app/api/routers/devops_metrics.py apps/api/app/core/roles.py apps/api/app/core/repositories/authorization.py apps/api/app/services/products.py apps/api/tests/test_deployment_schemes_api.py apps/api/tests/test_operational_deployments.py docs/02-specs/enterprise-ai-brain/api.md docs/02-specs/enterprise-ai-brain/spec.md
git commit -m "feat: manage product deployment schemes"
~~~

## Task 3: Bind Deployment Requests to Schemes and Make State Transitions Safe

**Files:**
- Modify: apps/api/app/services/operational_deployments.py
- Modify: apps/api/app/api/routers/devops_metrics.py
- Modify: apps/api/app/services/ai_executor_runners.py
- Modify: apps/api/tests/test_operational_deployments.py
- Create: apps/api/tests/test_deployment_request_execution.py

**Step 1: Write failing behavior tests**

Cover:
- an existing caller without scheme_id resolves the product environment default;
- create request freezes a non-secret scheme snapshot;
- manual start retains manual execution;
- runner and Jenkins starts use distinct channels;
- duplicate start is idempotent;
- cancel becomes cancelling and does not falsely mark cancelled;
- runner success, failure, timeout, and cancellation update deployment request, run, requirement, and Bug lifecycle consistently.

**Step 2: Run tests to verify red state**

Run:
~~~bash
cd apps/api && uv run pytest tests/test_deployment_request_execution.py tests/test_operational_deployments.py -q
~~~

Expected: failures because all deployment requests currently use the manual executor flow.

**Step 3: Implement orchestration**

Resolve and freeze the scheme during request creation. Add explicit execution channel branching. Add a shared deployment-run completion function that atomically updates run, request, related lifecycle state, audit record, and human review state as appropriate. Add idempotency keys and cancellation semantics that remain cancelling until externally confirmed.

**Step 4: Run focused tests**

Run the Task 3 command again.

Expected: PASS.

**Step 5: Commit**

Do not commit automatically. When requested:
~~~bash
git add apps/api/app/services/operational_deployments.py apps/api/app/api/routers/devops_metrics.py apps/api/app/services/ai_executor_runners.py apps/api/tests/test_deployment_request_execution.py apps/api/tests/test_operational_deployments.py
git commit -m "feat: execute deployments through selected schemes"
~~~

## Task 4: Add Deployment Capability and Local Target Discovery to the Runner

**Files:**
- Modify: apps/api/app/services/ai_executor_runner_constants.py
- Modify: apps/api/app/services/ai_executor_runners.py
- Modify: apps/api/app/services/ai_executor_runner_packages.py
- Modify: apps/web/src/pages/Plugins/components/pluginRunnerHelpers.ts
- Modify: apps/web/src/pages/Plugins/components/PluginRunnerFormFields.tsx
- Modify: apps/api/tests/test_ai_executor_runner_packages.py
- Create: apps/api/tests/test_deployment_runner_capability.py
- Modify: apps/web/tests/PluginsPage.test.tsx
- Modify: docs/02-specs/enterprise-ai-brain/spec.md

**Step 1: Write failing tests**

Cover:
- deployment is a separate runner capability and cannot be granted through AI executor types;
- an R&D execution policy cannot select deployment capability;
- target listing includes only heartbeat-published metadata;
- generated runner config includes optional deployment_targets without secret platform persistence;
- UI can enable deployment capability and show runner target metadata.

**Step 2: Run tests to verify red state**

Run:
~~~bash
cd apps/api && uv run pytest tests/test_deployment_runner_capability.py tests/test_ai_executor_runner_packages.py -q
cd apps/web && npm test -- PluginsPage.test.tsx
~~~

Expected: failures because runner registration and generated package only support AI executor types.

**Step 3: Implement capability and heartbeat changes**

Add deployment to a capability collection distinct from AI_EXECUTOR_TYPES. Extend runner registration, heartbeat normalization, availability lookup, and generated config parsing. In the generated runner, parse local deployment_targets and heartbeat only code, display name, method, and ready status. Add frontend runner configuration support without exposing target secret fields.

**Step 4: Run focused tests**

Run the Task 4 commands again.

Expected: PASS.

**Step 5: Commit**

Do not commit automatically. When requested:
~~~bash
git add apps/api/app/services/ai_executor_runner_constants.py apps/api/app/services/ai_executor_runners.py apps/api/app/services/ai_executor_runner_packages.py apps/web/src/pages/Plugins/components/pluginRunnerHelpers.ts apps/web/src/pages/Plugins/components/PluginRunnerFormFields.tsx apps/api/tests/test_ai_executor_runner_packages.py apps/api/tests/test_deployment_runner_capability.py apps/web/tests/PluginsPage.test.tsx docs/02-specs/enterprise-ai-brain/spec.md
git commit -m "feat: add runner deployment capability"
~~~

## Task 5: Execute SSH and Docker Deployments Through the Local Runner

**Files:**
- Modify: apps/api/app/services/ai_executor_runner_packages.py
- Modify: apps/api/app/services/ai_executor_runners.py
- Modify: apps/api/app/services/operational_deployments.py
- Create: apps/api/tests/test_runner_deployment_execution.py
- Modify: apps/api/tests/test_ai_executor_runner_packages.py
- Modify: docs/02-specs/enterprise-ai-brain/test-case.md
- Modify: docs/08-help/README.md

**Step 1: Write failing tests**

Cover:
- SSH command uses argv mode, BatchMode, StrictHostKeyChecking, known_hosts, fixed remote command, and JSON stdin;
- Docker command uses a fixed target working directory, compose files, project, services, optional pull, and no arbitrary browser command;
- process output is redacted, streamed, and persisted as deployment run logs;
- a cancel request terminates the local process and reports cancelled completion;
- runner failure propagates error summary without leaking host paths or secrets.

**Step 2: Run tests to verify red state**

Run:
~~~bash
cd apps/api && uv run pytest tests/test_runner_deployment_execution.py tests/test_ai_executor_runner_packages.py -q
~~~

Expected: failures because the runner currently launches only generic AI executor processes.

**Step 3: Implement deployment execution modes**

Extend the generated runner task dispatcher for deployment tasks. Resolve the local target by code. Build safe SSH and Docker argv lists from local-only target configuration. Stream sanitized output in bounded chunks. Honor cancellation by terminating the child process, then send terminal cancelled completion. Update backend claim and completion routes to link the runner task to its deployment run.

**Step 4: Run focused tests**

Run the Task 5 command again.

Expected: PASS.

**Step 5: Commit**

Do not commit automatically. When requested:
~~~bash
git add apps/api/app/services/ai_executor_runner_packages.py apps/api/app/services/ai_executor_runners.py apps/api/app/services/operational_deployments.py apps/api/tests/test_runner_deployment_execution.py apps/api/tests/test_ai_executor_runner_packages.py docs/02-specs/enterprise-ai-brain/test-case.md docs/08-help/README.md
git commit -m "feat: run SSH and Docker deployments locally"
~~~

## Task 6: Add Jenkins Connection, Trigger, Sync, and Cancel Support

**Files:**
- Modify: apps/api/app/services/plugin_constants.py
- Modify: apps/api/app/services/plugin_templates.py
- Modify: apps/api/app/services/plugin_connection_config.py
- Modify: apps/api/app/services/plugin_invocation_runtime.py
- Modify: apps/api/app/main.py
- Modify: apps/api/app/services/operational_deployments.py
- Create: apps/api/app/services/deployment_sync_worker.py
- Create: apps/api/tests/test_jenkins_deployments.py
- Modify: apps/api/tests/test_plugin_management.py
- Modify: docs/02-specs/enterprise-ai-brain/api.md
- Modify: docs/02-specs/enterprise-ai-brain/spec.md

**Step 1: Write failing integration tests**

Cover:
- Jenkins official plugin template and Basic authentication references;
- trigger uses buildWithParameters and stores queue URL;
- queue polling resolves a build URL and build polling maps terminal states;
- the background worker claims due runs with a lease and exponential backoff;
- manual sync endpoint uses the same reconciliation logic;
- cancel invokes Jenkins and leaves the run cancelling until external confirmation;
- auth headers and logs never reveal user API token values.

**Step 2: Run tests to verify red state**

Run:
~~~bash
cd apps/api && uv run pytest tests/test_jenkins_deployments.py tests/test_plugin_management.py -q
~~~

Expected: failures because Jenkins templates, Basic authentication handling, and deployment sync worker do not exist.

**Step 3: Implement Jenkins execution**

Add a Jenkins plugin template and reference-only Basic auth support. Trigger builds through the plugin runtime, persist queue/build metadata, and create a leased background worker started and stopped from FastAPI lifespan. Add API sync and cancel operations that reuse the same service logic. Record masked invocation audit data and retry schedule metadata.

**Step 4: Run focused tests**

Run the Task 6 command again.

Expected: PASS.

**Step 5: Commit**

Do not commit automatically. When requested:
~~~bash
git add apps/api/app/services/plugin_constants.py apps/api/app/services/plugin_templates.py apps/api/app/services/plugin_connection_config.py apps/api/app/services/plugin_invocation_runtime.py apps/api/app/main.py apps/api/app/services/operational_deployments.py apps/api/app/services/deployment_sync_worker.py apps/api/tests/test_jenkins_deployments.py apps/api/tests/test_plugin_management.py docs/02-specs/enterprise-ai-brain/api.md docs/02-specs/enterprise-ai-brain/spec.md
git commit -m "feat: integrate Jenkins deployment execution"
~~~

## Task 7: Deliver the Deployment Scheme Workbench and Validate the User Flow

**Files:**
- Modify: apps/web/src/pages/Deployments/index.tsx
- Modify: apps/web/src/services/devopsOperationsClient.ts
- Modify: apps/web/tests/OperationalInsightsPages.test.tsx
- Create: apps/web/tests/DeploymentSchemesPage.test.tsx
- Modify: docs/08-help/README.md
- Create or modify: docs/08-help/deployment-guide.md
- Create or modify: docs/08-help/assets/screenshots/help-deployment-schemes.png
- Modify: docs/changelog.md

**Step 1: Write failing frontend tests**

Cover:
- tabs for deployment requests and deployment schemes;
- method-specific scheme form fields;
- default scheme display and optimistic version conflict feedback;
- runner target selection after runner choice;
- Jenkins connection, job, and parameter inputs;
- request creation default selection;
- execution channel and frozen scheme summary;
- logs drawer, Jenkins sync action, and cancelling state rendering.

**Step 2: Run tests to verify red state**

Run:
~~~bash
cd apps/web && npm test -- DeploymentSchemesPage.test.tsx OperationalInsightsPages.test.tsx
~~~

Expected: failures because the page currently supports manual deployment requests only.

**Step 3: Implement the workbench**

Extend the Deployments page with deployment request and deployment scheme tabs. Use Ant Design table, drawer, form, select, tag, modal, and alert patterns already used by the project. Keep action controls on one stable line. Bind new APIs, add actionable error messages, and preserve existing manual operation flows.

**Step 4: Update help and screenshots**

Document the four methods, target configuration boundaries, runner requirements, Jenkins sync behavior, cancellation semantics, and the no-secret policy. Capture real browser screenshots with sensitive values masked.

**Step 5: Run automated verification**

Run:
~~~bash
cd apps/api && uv run pytest tests/test_deployment_strategy_repository.py tests/test_deployment_schemes_api.py tests/test_deployment_request_execution.py tests/test_deployment_runner_capability.py tests/test_runner_deployment_execution.py tests/test_jenkins_deployments.py tests/test_operational_deployments.py tests/test_plugin_management.py tests/test_ai_executor_runner_packages.py tests/test_persistence_repository_boundaries.py -q
cd apps/web && npm test -- DeploymentSchemesPage.test.tsx OperationalInsightsPages.test.tsx PluginsPage.test.tsx
cd apps/web && npm run typecheck
cd apps/web && npm run build
npm run help:check
~~~

Expected: PASS.

**Step 6: Run real browser validation**

Start the PostgreSQL-backed API and web applications. Log in using an authorized release owner role. Verify:
- menu path 运营治理 / 运维部署;
- deployment scheme CRUD and dynamic fields;
- manual request creation/start/complete;
- runner target selection without secret exposure;
- Jenkins state display and sync/cancel controls;
- no console or network errors;
- help route and refreshed screenshots.

Record the URL, role, checked pages, and result in the final summary.

**Step 7: Commit**

Do not commit automatically. When requested:
~~~bash
git add apps/web/src/pages/Deployments/index.tsx apps/web/src/services/devopsOperationsClient.ts apps/web/tests/DeploymentSchemesPage.test.tsx apps/web/tests/OperationalInsightsPages.test.tsx docs/08-help/README.md docs/08-help/deployment-guide.md docs/08-help/assets/screenshots/help-deployment-schemes.png docs/changelog.md
git commit -m "feat: add governed deployment workbench"
~~~

## Final Verification

Run:
~~~bash
cd apps/api && uv run pytest
cd apps/web && npm test -- --run
cd apps/web && npm run typecheck
cd apps/web && npm run build
npm run help:check
~~~

Then run the real browser validation described in Task 7. Review git diff and ensure no secrets, generated artifacts, or unrelated dirty changes are included in any future commit.
