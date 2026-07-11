# Autonomous Delivery Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build independently verified Agent development loops and production-safe deployment orchestration, then add product-scoped resources, event integrations, deployment observability, and multimodal knowledge processing.

**Architecture:** Quality gates, Agent loops, context manifests, Outbox/Inbox, and resource grants are separate persisted domains. Coding Runner success advances to verification instead of merge. Deployment and Git side effects are emitted transactionally and executed by a dedicated worker. Existing APIs remain compatible while new list and detail contracts become the management-page source.

**Tech Stack:** FastAPI, PostgreSQL, Redis-compatible worker coordination, React + TypeScript + Ant Design Pro, local AI Brain Runner, GitHub/GitLab/Jenkins webhooks, MinIO, OpenAI-compatible embeddings, pytest, Vitest, real browser validation.

## Global Constraints

- Never store or return real credentials, private keys, complete environment variables, or unredacted provider payloads.
- Runner coding success is not independent quality evidence and cannot directly authorize merge.
- Every management read and mutation must enforce product scope in the backend.
- All external side effects must have a stable idempotency key and an audit event.
- Production deployment windows default to strict enforcement for newly created schemes.
- High-risk, protected-path, permission, secret, migration, and production configuration changes require human review.
- Keep manual deployment, manual review, and manual metric import compatibility.
- Update project specs, API docs, test cases, help content, screenshots, and changelog with visible behavior.

---

### Task 1: Persist Governance Primitives

**Files:**
- Create: `apps/api/app/db/migrations/102_autonomous_delivery_governance.sql`
- Modify: `apps/api/app/core/persistence.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Create: `apps/api/app/core/repositories/execution_governance.py`
- Create: `apps/api/app/core/repositories/execution_governance_writes.py`
- Modify: `apps/api/app/core/repositories/__init__.py`
- Modify: `apps/api/tests/test_persistence_repository_boundaries.py`
- Create: `apps/api/tests/test_execution_governance_repository.py`

**Interfaces:**
- Produces: repository methods for quality policies/runs/checks, loop runs/iterations, context manifests, Outbox/Inbox, resource grants, deployment steps, knowledge versions/profiles/feedback.
- Produces: `claim_execution_outbox_events`, `claim_external_event_inbox`, optimistic save methods, and transaction bundles.

- [ ] **Step 1: Write failing migration and repository tests**

Cover unique keys, product scope, optimistic versions, JSON normalization, lease claiming with `SKIP LOCKED`, Outbox idempotency, Inbox delivery deduplication, and deployment transaction rollback.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_execution_governance_repository.py tests/test_persistence_repository_boundaries.py -q`

Expected: missing migration tables and repository methods.

- [ ] **Step 3: Add migration and focused repositories**

Use the exact entities and state constraints from `docs/superpowers/specs/2026-07-11-autonomous-delivery-governance-design.md`. Keep read and write modules below 800 lines by splitting schema projections from transaction bundles.

- [ ] **Step 4: Verify focused tests**

Run the Step 2 command and expect all tests to pass.

### Task 2: Add Execution Context Manifests

**Files:**
- Create: `apps/api/app/services/execution_context_manifests.py`
- Modify: `apps/api/app/services/rd_task_executor_policies.py`
- Modify: `apps/api/app/services/ai_executor_task_creation.py`
- Modify: `apps/api/app/services/task_details.py`
- Create: `apps/api/tests/test_execution_context_manifests.py`
- Modify: `apps/api/tests/test_rd_task_executor_policies.py`

**Interfaces:**
- Produces: `build_execution_context_manifest(current_store, *, task, user) -> dict[str, Any]`.
- Produces: `execution_context_manifest_response(current_store, *, subject_type, subject_id, user) -> dict[str, Any]`.
- Consumes: product-scoped requirement, Bug, repository, code-inspection, knowledge and acceptance data.

- [ ] **Step 1: Write failing manifest tests**

Assert deterministic version/hash, permission-filtered knowledge references, retrieval reasons, truncation summaries, acceptance criteria, no full secrets, and product-scope rejection.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_execution_context_manifests.py tests/test_rd_task_executor_policies.py -q`.

- [ ] **Step 3: Implement and inject manifests**

Replace ad hoc Runner context construction with manifest references while retaining compact compatibility fields in `input_payload`. Persist the manifest before creating the Runner task.

- [ ] **Step 4: Verify focused tests**

Run the Step 2 command and expect all tests to pass.

### Task 3: Implement Independent Quality Gates

**Files:**
- Create: `apps/api/app/services/quality_gate_catalog.py`
- Create: `apps/api/app/services/quality_gates.py`
- Create: `apps/api/app/api/routers/quality_gates.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/roles.py`
- Modify: `apps/api/app/core/repositories/authorization_defaults.py`
- Modify: `apps/api/app/services/ai_executor_runner_constants.py`
- Modify: `apps/api/app/services/ai_executor_runners.py`
- Modify: `apps/api/app/services/ai_executor_runner_packages.py`
- Create: `apps/api/tests/test_quality_gates.py`
- Create: `apps/api/tests/test_quality_gate_runner.py`

**Interfaces:**
- Produces: `create_quality_gate_run`, `record_quality_gate_check`, `evaluate_quality_gate_run`, `queue_platform_verifier_task`.
- Produces: `quality_gate` Runner capability that executes only local verifier Catalog codes.
- Consumes: context manifest, task risk, diff summary, CI evidence, platform scans, human override.

- [ ] **Step 1: Write failing policy and evaluation tests**

Test that coding Runner success is insufficient; independent evidence is mandatory; protected paths and migrations require review; diff thresholds block; CI/scan/verifier evidence passes only when all required checks succeed.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_quality_gates.py tests/test_quality_gate_runner.py -q`.

- [ ] **Step 3: Implement policy matching and verifier dispatch**

Add service-side Catalog codes and generated Runner verifier configuration. The verifier receives a worktree isolation reference and check codes, not arbitrary commands. Persist bounded structured evidence and sanitized logs.

- [ ] **Step 4: Route coding completion into verification**

Change `_complete_ai_task_with_auto_commit_if_configured` so it cannot call `mark_ai_executor_workspace_isolation_decision(action="merge")` until the linked gate is `passed`. Missing policy or evidence degrades to manual review.

- [ ] **Step 5: Verify focused tests**

Run the Step 2 command and existing Runner/policy tests.

### Task 4: Implement Agent Autonomous Loops

**Files:**
- Create: `apps/api/app/services/agent_loop_controls.py`
- Create: `apps/api/app/services/agent_loops.py`
- Create: `apps/api/app/api/routers/agent_loops.py`
- Modify: `apps/api/app/services/rd_task_executor_policies.py`
- Modify: `apps/api/app/services/ai_executor_runners.py`
- Modify: `apps/api/app/services/task_start_execution.py`
- Modify: `apps/api/app/api/routers/tasks.py`
- Create: `apps/api/tests/test_agent_loops.py`
- Modify: `apps/api/tests/test_rd_task_executor_policies.py`

**Interfaces:**
- Produces: `start_agent_loop`, `advance_agent_loop_from_coding_result`, `advance_agent_loop_from_gate`, `stop_agent_loop`.
- Consumes: context manifest, quality gate policy, Runner task results and budgets.
- Produces: next Runner task instruction containing previous failed checks and bounded evidence.

- [ ] **Step 1: Write failing state-machine tests**

Cover plan/execute/verify/reflect/retry, successful convergence, manual takeover, max iterations, duration, token/cost budget, safety block, idempotent duplicate completion, and optimistic concurrency.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_agent_loops.py tests/test_rd_task_executor_policies.py -q`.

- [ ] **Step 3: Extend executor policy contract**

Add `autonomy_mode=single_pass|autonomous_loop`, `max_iterations`, `max_duration_seconds`, optional budgets, `quality_gate_policy_id`, and risk auto-merge threshold. Default existing policies to single pass/manual review.

- [ ] **Step 4: Implement loop transitions and Runner integration**

Coding success creates a gate; failed gate with remaining budget creates a reflecting iteration and next coding task; passed gate enters manual review or governed auto merge; budget and safety conditions stop deterministically.

- [ ] **Step 5: Verify focused tests**

Run the Step 2 command and task workflow regression tests.

### Task 5: Make Deployment Dispatch Transactional

**Files:**
- Create: `apps/api/app/services/execution_outbox.py`
- Create: `apps/api/app/workers/execution_worker.py`
- Create: `apps/api/app/workers/__main__.py`
- Modify: `apps/api/app/services/operational_deployments.py`
- Modify: `apps/api/app/services/jenkins_deployments.py`
- Modify: `apps/api/app/services/deployment_sync_worker.py`
- Modify: `docker-compose.yml`
- Create: `apps/api/tests/test_execution_outbox.py`
- Modify: `apps/api/tests/test_deployment_request_execution.py`

**Interfaces:**
- Produces: `create_deployment_dispatch_transaction(...)` repository operation.
- Produces: Outbox handlers for `runner_task_dispatch`, `jenkins_trigger`, `deployment_verify`, `deployment_rollback`, and `git_writeback`.

- [ ] **Step 1: Write failing atomicity and idempotency tests**

Inject failures after each write and assert no partial deployment state commits. Replay Outbox events and assert one external dispatch. Verify lease expiry and dead-letter transitions.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_execution_outbox.py tests/test_deployment_request_execution.py -q`.

- [ ] **Step 3: Replace direct side effects with Outbox events**

Start/cancel/rollback APIs commit business rows, steps, audit, and Outbox together. Worker handlers perform side effects and write idempotent completion events.

- [ ] **Step 4: Add dedicated worker runtime**

Add a Compose worker service and environment switch disabling API-embedded production synchronization. Preserve a synchronous test helper.

- [ ] **Step 5: Verify focused tests**

Run the Step 2 command and `docker compose config --quiet`.

### Task 6: Add Deployment Safety, Rollouts, Health, and Rollback

**Files:**
- Create: `apps/api/app/services/deployment_preflight.py`
- Create: `apps/api/app/services/deployment_rollouts.py`
- Create: `apps/api/app/services/deployment_health.py`
- Create: `apps/api/app/services/deployment_rollback.py`
- Modify: `apps/api/app/services/operational_deployments.py`
- Modify: `apps/api/app/services/ai_executor_runner_packages.py`
- Modify: `apps/api/app/services/jenkins_deployments.py`
- Modify: `apps/api/app/api/routers/devops_metrics.py`
- Create: `apps/api/tests/test_deployment_safety.py`
- Create: `apps/api/tests/test_deployment_rollouts.py`
- Create: `apps/api/tests/test_deployment_rollback.py`

**Interfaces:**
- Produces: preflight result, rollout wave plan, health verdict, rollback request and human-takeover transition.
- Consumes: pre/post deployment quality policies and authorized deployment resources.

- [ ] **Step 1: Write failing production safety tests**

Test strict windows, artifact/Commit validation, Runner readiness, gate requirements, all-at-once/canary/batch/blue-green waves, post-deploy health, automatic rollback threshold, manual takeover, and rollback failure incident creation.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_deployment_safety.py tests/test_deployment_rollouts.py tests/test_deployment_rollback.py -q`.

- [ ] **Step 3: Implement safe orchestration**

Create explicit deployment steps and operation-specific runs. Add fixed SSH/Docker rollback and health actions to local Target configuration. Add Jenkins rollback and health Job bindings.

- [ ] **Step 4: Verify focused tests**

Run the Step 2 command plus existing deployment and Jenkins tests.

### Task 7: Scope Execution Resources by Product and Environment

**Files:**
- Create: `apps/api/app/services/execution_resource_grants.py`
- Create: `apps/api/app/api/routers/execution_resources.py`
- Modify: `apps/api/app/services/operational_deployments.py`
- Modify: `apps/api/app/core/roles.py`
- Modify: `apps/api/app/core/repositories/authorization_defaults.py`
- Create: `apps/api/tests/test_execution_resource_grants.py`
- Modify: `apps/api/tests/test_deployment_schemes_api.py`

**Interfaces:**
- Produces: grant CRUD and `require_execution_resource_grant`.
- Consumes: global Runner Target/Jenkins resources and product/environment scope.

- [ ] **Step 1: Write failing visibility and binding tests**

Assert product managers see only authorized targets/connections, cannot bind cross-product resources, and administrators can grant/revoke with optimistic locking and audit.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_execution_resource_grants.py tests/test_deployment_schemes_api.py -q`.

- [ ] **Step 3: Implement grants and enforce every read/write path**

Filter candidate APIs and validate scheme create/update/start against active grants. Existing bindings continue only through migration-created grants.

- [ ] **Step 4: Verify focused tests**

Run the Step 2 command.

### Task 8: Ingest External Events and Perform Git Writeback

**Files:**
- Create: `apps/api/app/services/external_event_inbox.py`
- Create: `apps/api/app/services/external_event_signatures.py`
- Create: `apps/api/app/services/external_event_projectors.py`
- Create: `apps/api/app/services/git_provider_writeback.py`
- Create: `apps/api/app/api/routers/external_events.py`
- Modify: `apps/api/app/services/plugin_templates.py`
- Modify: `apps/api/app/workers/execution_worker.py`
- Create: `apps/api/tests/test_external_event_inbox.py`
- Create: `apps/api/tests/test_git_ci_events.py`
- Create: `apps/api/tests/test_observability_events.py`
- Create: `apps/api/tests/test_git_writeback.py`

**Interfaces:**
- Produces: signed webhook endpoints and idempotent projectors.
- Produces: Outbox GitHub/GitLab comment, request-changes, approval, merge actions.
- Consumes: plugin connection secret references and product repository mapping.

- [ ] **Step 1: Write failing signature, replay, projection and writeback tests**

Cover GitHub/GitLab/Jenkins signatures, duplicate Delivery IDs, CI evidence projection, Jenkins callback convergence, telemetry/user-event aggregation, product mapping failures, writeback authorization and redaction.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_external_event_inbox.py tests/test_git_ci_events.py tests/test_observability_events.py tests/test_git_writeback.py -q`.

- [ ] **Step 3: Implement Inbox and projectors**

Persist a sanitized provider payload, then project to quality checks, deployments, metrics and user insights. Keep current manual APIs.

- [ ] **Step 4: Implement idempotent Git writeback**

Use provider-specific API clients through plugin connections and Outbox. Never merge without the quality and permission snapshot attached to the event.

- [ ] **Step 5: Verify focused tests**

Run the Step 2 command.

### Task 9: Add Deployment Read Models and Detail UI

**Files:**
- Create: `apps/api/app/core/deployment_read_model.py`
- Modify: `apps/api/app/api/routers/devops_metrics.py`
- Modify: `apps/api/app/services/operational_deployments.py`
- Modify: `apps/web/src/services/devopsOperationsClient.ts`
- Modify: `apps/web/src/pages/Deployments/index.tsx`
- Create: `apps/web/src/pages/Deployments/DeploymentDetailDrawer.tsx`
- Modify: `apps/web/src/pages/Deployments/DeploymentSchemePanel.tsx`
- Create: `apps/api/tests/test_deployment_read_model.py`
- Modify: `apps/web/tests/OperationalInsightsPages.test.tsx`

**Interfaces:**
- Produces: paged request/scheme APIs with query/performance metadata and a complete deployment detail endpoint.

- [ ] **Step 1: Write failing SQL paging and UI tests**

Cover filters, whitelisted sort, product scope, stable pagination, detail steps/gates/approvals/runs/health/rollback/audit, empty/error states, permission-hidden actions and mobile layout.

- [ ] **Step 2: Verify red state**

Run backend read-model tests and `cd apps/web && npm test -- OperationalInsightsPages.test.tsx`.

- [ ] **Step 3: Implement read model and split the page**

Move detail and scheme responsibilities into focused components. Keep each new frontend file below 600 lines and remove the legacy all-record fetch from the management table.

- [ ] **Step 4: Verify focused tests**

Run the Step 2 commands, frontend lint and typecheck.

### Task 10: Add Agent Loop, Gate, Context, Resource, and Event UI

**Files:**
- Modify: `apps/web/src/pages/RdExecutorPolicies/index.tsx`
- Modify: `apps/web/src/pages/TaskCenter/index.tsx`
- Create: `apps/web/src/components/AgentLoopTimeline/index.tsx`
- Create: `apps/web/src/components/QualityGatePanel/index.tsx`
- Create: `apps/web/src/components/ExecutionContextManifest/index.tsx`
- Create: `apps/web/src/pages/ExecutionResources/index.tsx`
- Modify: `apps/web/src/pages/Plugins/index.tsx`
- Modify: `apps/web/src/pages/SystemHealth/index.tsx`
- Modify: `apps/web/config/routes.ts`
- Modify: `apps/web/src/services/aiBrain.ts`
- Create: `apps/web/tests/AgentGovernancePages.test.tsx`

**Interfaces:**
- Consumes: Tasks 2, 3, 4, 7 and 8 API contracts.

- [ ] **Step 1: Write failing interaction and permission tests**

Cover policy controls, loop timeline, stop/takeover, gate evidence, context manifest, resource grants, webhook health, retry, dead letters, readable Chinese labels and product scope.

- [ ] **Step 2: Verify red state**

Run: `cd apps/web && npm test -- AgentGovernancePages.test.tsx`.

- [ ] **Step 3: Implement focused components and pages**

Do not expose raw JSON as the primary experience. Structured payload remains available only in diagnostic expansion panels.

- [ ] **Step 4: Verify focused tests**

Run targeted tests, lint and typecheck.

### Task 11: Add Knowledge Processing Profiles and Multimodal Retrieval

**Files:**
- Create: `apps/api/app/services/knowledge_processing_profiles.py`
- Create: `apps/api/app/services/knowledge_document_versions.py`
- Create: `apps/api/app/services/knowledge_processor_adapters.py`
- Create: `apps/api/app/services/knowledge_multimodal_search.py`
- Modify: `apps/api/app/services/knowledge_import_worker.py`
- Modify: `apps/api/app/services/knowledge_search.py`
- Modify: `apps/api/app/api/routers/knowledge.py`
- Modify: `apps/web/src/pages/Knowledge/index.tsx`
- Create: `apps/api/tests/test_knowledge_processing_profiles.py`
- Create: `apps/api/tests/test_knowledge_multimodal_search.py`
- Modify: `apps/web/tests/KnowledgePage.test.tsx`

**Interfaces:**
- Produces: Provider adapter contract for OCR, layout, table and multimodal embedding.
- Produces: version-aware retrieval with freshness and citation feedback ranking.

- [ ] **Step 1: Write failing adapter, version and retrieval tests**

Use an in-process fake Provider to cover PDF page images, OCR blocks, bounding boxes, tables, asset references, multimodal embeddings, version activation, stale detection, permission filtering and citation feedback.

- [ ] **Step 2: Verify red state**

Run: `cd apps/api && uv run pytest tests/test_knowledge_processing_profiles.py tests/test_knowledge_multimodal_search.py -q` and the Knowledge frontend test.

- [ ] **Step 3: Implement Provider boundary and versioned assets**

Credentials use existing secret references. MinIO remains the binary source. Failed stages are independently retryable and do not destroy the previous active version.

- [ ] **Step 4: Implement hybrid multimodal ranking and UI**

Merge text/vector/multimodal candidates after database permission filtering. Display page, region, table, version, age and feedback state.

- [ ] **Step 5: Verify focused tests**

Run the Step 2 commands.

### Task 12: Documentation, Full Verification, and Release

**Files:**
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/08-help/tasks-and-governance.md`
- Modify: `docs/08-help/delivery.md`
- Modify: `docs/08-help/assets-and-knowledge.md`
- Modify: `docs/changelog.md`
- Update: `docs/08-help/assets/screenshots/`
- Update: `apps/web/public/help/screenshots/`

- [ ] **Step 1: Complete requirement-to-test audit**

Map every P0/P1 requirement to an automated test and real runtime check. Missing evidence means the requirement remains incomplete.

- [ ] **Step 2: Run full verification**

Run backend pytest and changed-file Ruff; frontend tests, lint, typecheck, build and strict help check; Compose config; migration replay; secret scan; diff check.

- [ ] **Step 3: Run real integration acceptance**

Use PostgreSQL-backed API, Worker, web app, MinIO and fake external Provider servers. Verify desktop/mobile UI, autonomous retry, blocked auto merge, successful gate merge request, strict deployment window, rollout health failure, rollback, webhook replay, product resource isolation and multimodal document retrieval.

- [ ] **Step 4: Review, commit, merge and push**

Review staged diff for unrelated changes and credentials. Commit coherent implementation history, merge the feature branch to `master`, rerun critical smoke checks, and push `origin/master`.
