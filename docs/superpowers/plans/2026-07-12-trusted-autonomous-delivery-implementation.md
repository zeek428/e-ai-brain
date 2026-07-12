# 可信自治交付与多模态检索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可信自动研发、可执行验收、生产双人复核、外部对账、Worker 运维、预算熔断与原生视觉检索。

**Architecture:** 在既有 PostgreSQL 质量门禁、Agent Loop、Outbox/Inbox 与知识版本模型上新增受限状态和签名证据。安全结论在服务端按 scope、策略和不可变记录计算，页面只显示 read model。

**Tech Stack:** FastAPI、Pydantic、PostgreSQL/pgvector、React + TypeScript + Ant Design Pro、pytest、Vitest、MinIO/S3。

## Global Constraints

- PostgreSQL 是证明、审批、预算、队列和视觉向量的唯一事实源。
- 不保存或返回 Runner 私钥、外部密钥、完整 Provider payload、完整模型输出或 SBOM 正文。
- 自动合入和生产部署 fail closed；缺少隔离 verifier、签名、验收、审批、窗口、制品或资源授权必须阻断。
- 所有接口做产品 scope、知识空间权限、动作权限、审计和 `trace_id` 校验。
- 每段生产代码先有失败测试，再写最小实现。
- SQL 迁移幂等；MemoryStore 仅作测试 helper。

---

### Task 1: Runner 信任域与执行证明

**Files:**
- Create: `apps/api/app/db/migrations/106_trusted_execution_attestations.sql`
- Create: `apps/api/app/services/execution_attestations.py`
- Modify: `apps/api/app/services/ai_executor_runners.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Modify: `apps/api/app/core/repositories/execution_governance.py`
- Modify: `apps/api/app/core/repositories/execution_governance_writes.py`
- Test: `apps/api/tests/test_execution_attestations.py`

**Interfaces:**
- Produces: `verify_execution_attestation(current_store, *, runner_task, required_trust_domain, coding_runner_task=None) -> dict[str, Any]`.

- [ ] Write a failing test for a verifier sharing the coding trust boundary.

```python
def test_same_boundary_verifier_is_blocked(store):
    result = verify_execution_attestation(
        store,
        runner_task=create_signed_runner_task(store, runner_id="verify", trust_boundary_id="host-a"),
        coding_runner_task=create_runner_task(store, runner_id="code", trust_boundary_id="host-a"),
        required_trust_domain="verification",
    )
    assert result["error_code"] == "VERIFIER_TRUST_DOMAIN_UNAVAILABLE"
```

- [ ] Run `cd apps/api && uv run pytest tests/test_execution_attestations.py -q`; confirm the missing verifier/proof behavior fails.
- [ ] Add Runner fields `trust_domain`, `trust_boundary_id`, `attestation_public_key`, `attestation_key_fingerprint`, `attestation_status`, and an `execution_attestations` table with canonical payload hash, Ed25519 signature, verification status and redacted error code.
- [ ] Implement:

```python
def verify_execution_attestation(current_store, *, runner_task, required_trust_domain, coding_runner_task=None):
    runner = get_registered_runner(current_store, runner_task["runner_id"])
    if runner["trust_domain"] != required_trust_domain or same_boundary(runner, coding_runner_task):
        return blocked_attestation("VERIFIER_TRUST_DOMAIN_UNAVAILABLE")
    return verify_ed25519_payload_and_persist(current_store, runner, runner_task)
```

- [ ] Re-run the focused test, then commit `feat: verify runner execution attestations`.

### Task 2: 信任域质量门禁与自动合入

**Files:**
- Modify: `apps/api/app/services/quality_gates.py`
- Modify: `apps/api/app/services/agent_autonomy.py`
- Modify: `apps/api/app/services/rd_task_executor_policies.py`
- Modify: `apps/api/app/api/routers/tasks.py`
- Test: `apps/api/tests/test_quality_gates.py`
- Test: `apps/api/tests/test_rd_task_executor_policies.py`

**Interfaces:**
- Consumes: Task 1 attestation result.
- Produces: `verification_trust_policy` and attestation-aware `quality_gate_allows_auto_merge`.

- [ ] Write a failing test asserting that a passed gate with `verifier_trust_isolated=False` cannot auto merge.
- [ ] Run `cd apps/api && uv run pytest tests/test_quality_gates.py tests/test_rd_task_executor_policies.py -q`; confirm failure.
- [ ] Extend gate run records with `verified_attestation_count` and `verifier_trust_isolated`; require `separate_runner_and_boundary` for `auto_commit` and production-facing policies.

```python
def quality_gate_allows_auto_merge(run):
    return bool(
        run.get("status") == "passed"
        and run.get("verified_attestation_count", 0) >= 1
        and run.get("verifier_trust_isolated") is True
        and not run.get("manual_review_required")
    )
```

- [ ] Re-run the focused tests, then commit `feat: enforce verifier trust isolation`.

### Task 3: 可执行验收计划与 Flaky 门禁

**Files:**
- Create: `apps/api/app/services/acceptance_test_plans.py`
- Create: `apps/api/app/api/routers/acceptance_tests.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Modify: `apps/api/app/core/repositories/execution_governance.py`
- Modify: `apps/api/app/core/repositories/execution_governance_writes.py`
- Modify: `apps/api/app/services/quality_gates.py`
- Modify: `apps/api/app/services/agent_autonomy.py`
- Test: `apps/api/tests/test_acceptance_test_plans.py`

**Interfaces:**
- Produces: active plan snapshots, cases, runs and `evaluate_acceptance_coverage(current_store, *, ai_task)`.

- [ ] Write failing tests for an unmapped requirement criterion and contradictory pass/fail runs for the same case and Commit.

```python
def test_unmapped_criterion_blocks_gate(store):
    result = evaluate_acceptance_coverage(store, ai_task=task_with_acceptance_criteria(store, ["可导出审批结果"]))
    assert result["blocked_reasons"] == ["ACCEPTANCE_GATE_BLOCKED"]
```

- [ ] Run `cd apps/api && uv run pytest tests/test_acceptance_test_plans.py -q`; confirm missing plan/case APIs fail.
- [ ] Add plan/case/run tables and immutable active `plan_snapshot_json`; map runs to Commit, artifact, verifier task and proof. Mark a case `flaky` on conflicting result history for identical case/Commit/input and block automatic release.

```python
def evaluate_acceptance_coverage(current_store, *, ai_task):
    plan = active_acceptance_plan(current_store, requirement_id=ai_task["requirement_id"])
    cases = list_acceptance_cases(current_store, plan_id=plan["id"]) if plan else []
    return coverage_result(ai_task, cases)
```

- [ ] Re-run acceptance and quality-gate tests, then commit `feat: add executable acceptance test plans`.

### Task 4: 生产双人复核、制品证明与外部结果对账

**Files:**
- Create: `apps/api/app/services/production_change_controls.py`
- Create: `apps/api/app/services/external_operation_reconciliation.py`
- Modify: `apps/api/app/services/operational_deployments.py`
- Modify: `apps/api/app/services/git_provider_writeback.py`
- Modify: `apps/api/app/services/deployment_sync_worker.py`
- Modify: `apps/api/app/workers/execution_worker.py`
- Modify: `apps/api/app/api/routers/devops_metrics.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Modify: `apps/api/app/core/repositories/execution_governance.py`
- Modify: `apps/api/app/core/repositories/execution_governance_writes.py`
- Test: `apps/api/tests/test_production_change_controls.py`
- Test: `apps/api/tests/test_external_operation_reconciliation.py`

**Interfaces:**
- Produces: production approval/freeze/artifact APIs, `deployment_can_start`, and `reconcile_external_operations`.

- [ ] Write failing tests proving a creator cannot approve their own dual-control production deployment and an unknown Git action is queried rather than re-dispatched.
- [ ] Run `cd apps/api && uv run pytest tests/test_production_change_controls.py tests/test_external_operation_reconciliation.py -q`; confirm failure.
- [ ] Add control, approval, artifact and freeze tables. Extend receipts to `unknown`, `reconciling`, `manual_reconciliation`; unknown actions only receive read-only provider reconciliation.

```python
def deployment_can_start(control, approvals):
    people = {item["user_id"] for item in approvals if item["decision"] == "approved"}
    roles = {item["role_code"] for item in approvals if item["decision"] == "approved"}
    return set(control["required_roles"]) <= roles and len(people) >= 2
```

- [ ] Re-run deployment/writeback focused tests, then commit `feat: govern production approvals and reconciliation`.

### Task 5: Worker 心跳、队列 read model 与控制台

**Files:**
- Create: `apps/api/app/services/execution_worker_observability.py`
- Create: `apps/api/app/api/routers/execution_workers.py`
- Create: `apps/web/src/pages/ExecutionWorkers/index.tsx`
- Create: `apps/web/src/services/executionWorkerClient.ts`
- Modify: `apps/api/app/workers/execution_worker.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Modify: `apps/api/app/core/repositories/execution_governance.py`
- Modify: `apps/api/app/core/repositories/execution_governance_writes.py`
- Modify: `apps/api/app/core/repositories/authorization_defaults.py`
- Modify: `apps/web/config/routes.ts`
- Test: `apps/api/tests/test_execution_worker_observability.py`
- Test: `apps/web/tests/ExecutionWorkersPage.test.tsx`

**Interfaces:**
- Produces: `GET /api/system/execution-workers`, `GET /api/system/execution-operations-overview` and scoped remediation actions.

- [ ] Write failing backend and frontend tests for stale heartbeats and hidden-product queue rows.
- [ ] Run the focused pytest/Vitest commands; confirm the endpoint and page fail to resolve.
- [ ] Add heartbeat persistence on every Worker iteration, SQL aggregation for queue age/lease timeout/P50/P95/failure/retry/dead-letter, and a dense system page with product scoped filters.

```python
def record_execution_worker_heartbeat(current_store, *, worker_id, counts):
    save_execution_worker_heartbeat(current_store, {"worker_id": worker_id, "claimed_count": sum(counts.values())})
```

- [ ] Re-run the focused tests, then commit `feat: add execution worker operations console`.

### Task 6: Agent 预算账本和无进展熔断

**Files:**
- Create: `apps/api/app/services/agent_budget_governance.py`
- Modify: `apps/api/app/services/agent_autonomy.py`
- Modify: `apps/api/app/services/task_agent_governance.py`
- Modify: `apps/api/app/services/task_read_details.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Modify: `apps/api/app/core/repositories/execution_governance.py`
- Modify: `apps/api/app/core/repositories/execution_governance_writes.py`
- Modify: `apps/api/app/api/routers/tasks.py`
- Test: `apps/api/tests/test_agent_budget_governance.py`
- Test: `apps/api/tests/test_task_agent_governance.py`

**Interfaces:**
- Produces: atomic reserve/settle/release operations and `evaluate_agent_circuit_breaker(iterations)`.

- [ ] Write failing tests for reserve/release accounting and two identical failure fingerprints.
- [ ] Run `cd apps/api && uv run pytest tests/test_agent_budget_governance.py tests/test_task_agent_governance.py -q`; confirm failure.
- [ ] Add durable budget ledgers and circuit records. Reserve policy maximums on loop creation, settle coding/verifier usage, release remainder at terminal state, and require an authorized recovery action/reason before restart.

```python
def evaluate_agent_circuit_breaker(iterations):
    recent = [item.get("failure_fingerprint") for item in iterations[-2:]]
    return "AGENT_LOOP_CIRCUIT_OPEN" if len(recent) == 2 and recent[0] and recent[0] == recent[1] else None
```

- [ ] Re-run focused autonomy tests, then commit `feat: govern agent budgets and circuit breakers`.

### Task 7: 视觉 Embedding、以图搜图和区域引用

**Files:**
- Create: `apps/api/app/services/knowledge_visual_search.py`
- Modify: `apps/api/app/services/knowledge_multimodal.py`
- Modify: `apps/api/app/services/knowledge_management.py`
- Modify: `apps/api/app/services/knowledge_search.py`
- Modify: `apps/api/app/services/knowledge_multimodal_governance.py`
- Modify: `apps/api/app/api/routers/knowledge.py`
- Modify: `apps/api/app/core/persistence_contracts.py`
- Modify: `apps/api/app/core/repositories/knowledge.py`
- Modify: `apps/api/app/core/repositories/knowledge_writes.py`
- Test: `apps/api/tests/test_knowledge_visual_search.py`

**Interfaces:**
- Produces: `POST /api/knowledge/search/visual` and asset/page/bounding-box citations.

- [ ] Write a failing test that a visually similar hidden-space asset never appears in results.
- [ ] Run `cd apps/api && uv run pytest tests/test_knowledge_visual_search.py -q`; confirm the visual endpoint is absent.
- [ ] Add versioned `knowledge_visual_embeddings`; only active `image_embedding` profiles generate vectors. Query image bytes become a short-lived private asset, and repository search applies knowledge scope before scoring.

```python
def visual_search_response(*, current_store, user, query_embedding, knowledge_space_id=None):
    rows = visual_repository(current_store).search_knowledge_visual_embeddings(
        **knowledge_repository_access_args(user), knowledge_space_id=knowledge_space_id, query_embedding=query_embedding
    )
    return envelope({"items": rerank_visual_candidates(rows)}, trace_id)
```

- [ ] Re-run visual and multimodal governance tests, then commit `feat: add visual knowledge retrieval`.

### Task 8: 任务、部署、Worker 与视觉检索前端

**Files:**
- Create: `apps/web/src/components/ExecutionAttestationPanel/index.tsx`
- Create: `apps/web/src/components/AcceptanceTestPlanPanel/index.tsx`
- Create: `apps/web/src/pages/Knowledge/components/VisualSearchPanel.tsx`
- Modify: `apps/web/src/pages/Requirements/index.tsx`
- Modify: `apps/web/src/pages/TaskCenter/components/TaskDetailModal.tsx`
- Modify: `apps/web/src/pages/Deployments/DeploymentDetailDrawer.tsx`
- Modify: `apps/web/src/pages/Knowledge/components/KnowledgeWorkbenchPanels.tsx`
- Modify: `apps/web/src/pages/Knowledge/index.tsx`
- Modify: `apps/web/src/services/taskCenterClient.ts`
- Modify: `apps/web/src/services/managementClient.ts`
- Modify: `apps/web/src/services/devopsOperationsClient.ts`
- Modify: `apps/web/src/services/knowledgeClient.ts`
- Test: `apps/web/tests/TrustedDeliveryGovernancePage.test.tsx`
- Test: `apps/web/tests/KnowledgeVisualSearch.test.tsx`

**Interfaces:**
- Consumes: Tasks 1-7 APIs.
- Produces: evidence/acceptance/approval/reconciliation panels and pasted-image visual search.

- [ ] Write failing UI tests for invalid proof display and pasted image region citation.
- [ ] Run `cd apps/web && npm test -- TrustedDeliveryGovernancePage.test.tsx KnowledgeVisualSearch.test.tsx`; confirm failure.
- [ ] Implement a requirement-row "验收计划" entry for creating/activating cases, compact task/deployment evidence panels, and image paste/select flow.

```tsx
<ExecutionAttestationPanel attestation={task.executionAttestation} />
<AcceptanceTestPlanPanel plan={task.acceptanceTestPlan} />
<VisualSearchPanel onSearch={searchKnowledgeVisually} />
```

- [ ] Show reconcile/retry only as tooltip-backed icon actions; disable retry for `manual_reconciliation`; never render raw payload/signature/object-storage URL.
- [ ] Re-run focused UI tests, then commit `feat: expose trusted delivery governance`.

### Task 9: Starlette/httpx 和 Ant Design 弃用收敛

**Files:**
- Create: `apps/api/tests/http_client.py`
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/uv.lock`
- Modify: affected `apps/web/src/**/*.tsx`
- Modify: `apps/web/vitest.config.ts`
- Test: `apps/api/tests/test_http_client_compatibility.py`
- Test: `apps/web/tests/DeprecatedApiWarnings.test.tsx`

**Interfaces:**
- Produces: ASGI transport client factory and deprecated-warning regression guard.

- [ ] Write a failing test asserting the shared HTTP client has no Starlette deprecation warning.
- [ ] Run its pytest target; confirm current `fastapi.testclient` import emits `StarletteDeprecationWarning`.
- [ ] Add Starlette's supported `httpx2` package, export the compatible `TestClient` through `apps/api/tests/http_client.py`, replace direct FastAPI `TestClient` imports, replace deprecated props such as `Alert.message` with `Alert.title`, and make Vitest fail on new Ant Design deprecation warnings.

```python
from starlette.testclient import TestClient

def asgi_client(app):
    return TestClient(app)
```

- [ ] Re-run backend/front-end warning tests, then commit `chore: remove test and component deprecations`.

### Task 10: 文档、真实页面验收与推送

**Files:**
- Modify: `README.md`
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/02-specs/enterprise-ai-brain/api/*.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-cases/*.md`
- Modify: `docs/08-help/tasks-and-governance.md`
- Modify: `docs/08-help/assets-and-knowledge.md`
- Modify: `docs/08-help/system-admin.md`
- Modify: `docs/changelog.md`

- [ ] Update contracts, help and masked screenshots for proof, acceptance/Flaky, maker-checker, reconciliation, Worker metrics, budget/circuit and visual search.
- [ ] Run `cd apps/api && uv run ruff check app tests && uv run pytest`; require exit 0.
- [ ] Run `cd apps/web && npm run typecheck && npm run lint && npm test -- --run && npm run build && npm run help:check:strict`; require exit 0 and no deprecated warnings.
- [ ] Run PostgreSQL-backed API, Worker and web acceptance for task proof, acceptance plan, production approval/reconciliation, Worker console and pasted-image visual search on desktop/mobile.
- [ ] Commit the completed feature and run `git push origin codex/autonomous-delivery-governance`.

## Plan Self-Review

- Tasks 1-4 cover every P0 item; Tasks 5-6 cover Worker and Agent P1 governance; Tasks 7-9 cover visual search and P2 cleanup; Task 10 covers documentation and end-to-end evidence.
- Every planned behavior has an assigned implementation task and verification command.
- Attestations feed quality gates; gates and acceptance feed Agent/deployment control; Worker read models consume durable action state; visual citations reuse document-version and knowledge-space identifiers.
