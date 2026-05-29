# Docs Production-Readiness Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the AI Brain documentation set so PRD, spec, API, tests, and runbooks are traceable, production-readiness aware, and implementation-ready.

**Architecture:** This is a documentation-only repair. Keep the existing documentation source-of-truth hierarchy, add missing details in place, and update indexes/changelog last after validation.

**Tech Stack:** Markdown documentation under `docs/`; validation with Python scripts, grep, and Markdown link checks.

---

## File Structure

- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
  - Owns test traceability, phase labels, and detailed acceptance test cases.
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md`
  - Owns product scope and links to implementation guidance.
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
  - Owns technical schema, state machine, action matrices, and implementation constraints.
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
  - Owns API contracts and endpoint error semantics.
- Modify: `docs/05-runbooks/deployment.md`
  - Owns environment-specific deployment and release gates.
- Modify: `docs/05-runbooks/monitoring.md`
  - Owns SLOs, alerts, logs, and observability requirements.
- Modify: `docs/05-runbooks/incident-response.md`
  - Owns incident roles, RTO/RPO, escalation, and recovery procedures.
- Modify: `docs/README.md`
  - Owns reader entry points and implementation order.
- Modify: `docs/VERSIONS.md`
  - Owns documentation version summary.
- Modify: `docs/changelog.md`
  - Owns release notes for this documentation repair.

---

### Task 1: Add test phase labels and missing detailed test cases

**Files:**
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md:72-105`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md:315-417`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md:785-834`

- [ ] **Step 1: Update the summary table schema**

Add a `适用阶段` column to the test summary table at `docs/02-specs/enterprise-ai-brain/test-case.md:76-101`.

Use these exact phase values:

```markdown
| MVP | v1 MVP mandatory closed-loop behavior |
| MVP 占位 | v1 MVP requires visible entry, empty state, or disabled state only |
| v1.1 | v1.1 complete capability |
| v1.2 | v1.2 complete capability |
| 生产就绪 | production-readiness validation gate |
```

Update the table header to:

```markdown
| 用例编号 | 用例名称 | 优先级 | 适用阶段 | 前置条件 | 测试步骤 | 预期结果 | 自动化 |
|----------|----------|--------|----------|----------|----------|----------|--------|
```

- [ ] **Step 2: Assign phases to each summary row**

Use this mapping:

```markdown
TC-AIBRAIN-TASK-FUNC-001: MVP
TC-AIBRAIN-GRAPH-FUNC-002: MVP
TC-AIBRAIN-REVIEW-FUNC-003: MVP
TC-AIBRAIN-OUTPUT-FUNC-004: MVP
TC-AIBRAIN-KNOWLEDGE-FUNC-005: MVP
TC-AIBRAIN-AUDIT-API-006: MVP
TC-AIBRAIN-DEPLOY-FUNC-007: 生产就绪
TC-AIBRAIN-CONFIG-API-008: MVP
TC-AIBRAIN-CONFIG-API-009: MVP
TC-AIBRAIN-FLOW-FUNC-010: MVP
TC-AIBRAIN-REQ-FUNC-011: MVP
TC-AIBRAIN-KNOWLEDGE-FUNC-012: MVP
TC-AIBRAIN-AUDIT-API-013: MVP
TC-AIBRAIN-DEVOPS-FUNC-014: v1.1
TC-AIBRAIN-OPS-FUNC-015: v1.2
TC-AIBRAIN-RELEASE-FUNC-016: v1.2
TC-AIBRAIN-DASHBOARD-FUNC-017: MVP 占位 / v1.2
TC-AIBRAIN-BUG-FUNC-018: MVP 占位 / v1.1
TC-AIBRAIN-TASK-FUNC-020: v1.1 / v1.2
TC-AIBRAIN-REVIEW-FUNC-019: v1.1
TC-AIBRAIN-REVIEW-FUNC-023: MVP
TC-AIBRAIN-REVIEW-FUNC-024: v1.2
TC-AIBRAIN-FLOW-FUNC-021: MVP / v1.2
TC-AIBRAIN-PLANNING-FUNC-022: MVP 占位 / v1.2
```

- [ ] **Step 3: Add detailed missing sections**

Add detailed sections for these five test IDs using the same table format as existing detailed cases: `TC-AIBRAIN-AUDIT-API-006`, `TC-AIBRAIN-DEPLOY-FUNC-007`, `TC-AIBRAIN-CONFIG-API-008`, `TC-AIBRAIN-CONFIG-API-009`, and `TC-AIBRAIN-AUDIT-API-013`. Each section must include `适用阶段`,前置条件,测试步骤,预期结果, and `状态: 待测试`.

- [ ] **Step 4: Run test traceability verification**

Run:

```bash
python3 - <<'PY'
import re
from pathlib import Path
prd=Path('docs/01-prd/enterprise-ai-brain/prd.md').read_text()
tc=Path('docs/02-specs/enterprise-ai-brain/test-case.md').read_text()
ids=[]
for x in re.findall(r'TC-AIBRAIN-[A-Z]+-[A-Z]+-\d+', prd):
    if x not in ids:
        ids.append(x)
missing=[x for x in ids if f'### {x}' not in tc]
print('PRD mapped test ids:', len(ids))
print('Missing detailed test sections:', missing)
raise SystemExit(1 if missing else 0)
PY
```

Expected: `Missing detailed test sections: []`.

---

### Task 2: Fix broken links and add implementation reader path

**Files:**
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:587-592`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md:693-698`
- Modify: `docs/README.md:17-70`

- [ ] **Step 1: Replace broken PRD and spec links**

Replace both `../../03-guides/solution-review-and-business-flow.html` links with `../../03-guides/ai-development-workflow.md`.

- [ ] **Step 2: Add implementation shortest path to README**

Add after `## 推荐阅读顺序`:

```markdown
## 实现者最短路径

1. 先阅读 PRD 的 v1 交付边界、验收标准和阶段计划，明确 MVP、v1.1、v1.2 与生产就绪门禁的差异。
2. 再阅读技术规格中的 P0 数据表字段、状态机动作矩阵和模块边界，先落地需求、AI 任务、人工确认、知识、审计和内部 GitLab MR Code Review 闭环。
3. 然后按 API 文档实现认证、产品配置、需求、AI 任务、人工确认、知识中心、GitLab MR 快照、code_review 报告和审计查询接口。
4. 前端页面优先实现产品配置、需求管理、任务中心、人工确认台、知识中心、审计与运行入口；Bug、研发运营、用户洞察和完整首页看板可按文档标记先做 MVP 占位或空状态。
5. 测试按 `test-case.md` 的 P0/MVP 用例先跑通，再补 v1.1、v1.2 和生产就绪用例。
6. 发布前执行部署、监控和故障响应 runbook 中的生产就绪门禁，尤其是密钥掩码、GitLab 只读边界、数据库迁移、备份恢复和审计可追踪。
```

- [ ] **Step 3: Run non-template link check**

Run the non-template Markdown link script from the design spec validation plan. Expected: `missing link count: 0`.

---

### Task 3: Add P0 schema and state-machine action matrices

**Files:**
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md:196-310`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md:529-585`

- [ ] **Step 1: Add `### P0 字段级 Schema` after core table structure**

Include field-level tables for `requirements`, `ai_tasks`, `human_reviews`, `gitlab_mr_snapshots`, `code_review_reports`, `knowledge_documents`, `knowledge_chunks`, and `audit_events`. Each table must define field name, logical type, requiredness, constraints, and notes.

- [ ] **Step 2: Add `### 状态机动作矩阵` after state transitions**

Include action matrices for Requirement, AI Task, Human Review, Knowledge Document, and GitLab MR Snapshot / Code Review Report. Each matrix must include current state, action, target state, role, idempotency/conflict rule, and audit event.

- [ ] **Step 3: Check spec headings**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
text=Path('docs/02-specs/enterprise-ai-brain/spec.md').read_text()
required=['### P0 字段级 Schema','### 状态机动作矩阵','#### requirements','#### AI Task']
missing=[x for x in required if x not in text]
print('missing headings:', missing)
raise SystemExit(1 if missing else 0)
PY
```

Expected: `missing headings: []`.

---

### Task 4: Add API error semantics

**Files:**
- Modify: `docs/02-specs/enterprise-ai-brain/api.md:1354-1383`

- [ ] **Step 1: Add `## 核心接口错误语义` before `## 错误码`**

Add a table covering AI task create/start/detail, review actions, GitLab MR preview/snapshot, code-review report, knowledge import/search/deposit review, model gateway configs, and audit query. Each row must define HTTP status, error code, retryability, audit requirement, and frontend handling guidance.

- [ ] **Step 2: Add missing error codes**

Ensure `PRODUCT_VERSION_ARCHIVED`, `MODEL_GATEWAY_CONFIG_INVALID`, and `DEVOPS_SOURCE_UNAVAILABLE` exist in the error code table.

- [ ] **Step 3: Check API error section exists**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
text=Path('docs/02-specs/enterprise-ai-brain/api.md').read_text()
required=['## 核心接口错误语义','PRODUCT_VERSION_ARCHIVED','MODEL_GATEWAY_CONFIG_INVALID','DEVOPS_SOURCE_UNAVAILABLE']
missing=[x for x in required if x not in text]
print('missing api terms:', missing)
raise SystemExit(1 if missing else 0)
PY
```

Expected: `missing api terms: []`.

---

### Task 5: Upgrade production-aware runbooks

**Files:**
- Modify: `docs/05-runbooks/deployment.md`
- Modify: `docs/05-runbooks/monitoring.md`
- Modify: `docs/05-runbooks/incident-response.md`

- [ ] **Step 1: Update deployment runbook**

Add environment matrix, release go/no-go checklist, staging/production rollback requirements, and backup/restore gates.

- [ ] **Step 2: Update monitoring runbook**

Add SLO targets, production alert thresholds, severity mapping, and traceability expectations.

- [ ] **Step 3: Update incident-response runbook**

Add incident roles, RTO/RPO targets, database migration incident handling, secret exposure handling, and GitLab writeback boundary incident handling.

- [ ] **Step 4: Check runbook terms**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
checks={
'docs/05-runbooks/deployment.md':['## 环境定位','## 发布准入门禁','### 备份恢复门禁'],
'docs/05-runbooks/monitoring.md':['## SLO 目标','### 生产告警阈值'],
'docs/05-runbooks/incident-response.md':['## 角色与升级','## RTO / RPO 目标','### GitLab 回写边界违反'],
}
missing=[]
for path,terms in checks.items():
    text=Path(path).read_text()
    for term in terms:
        if term not in text:
            missing.append((path,term))
print('missing runbook terms:', missing)
raise SystemExit(1 if missing else 0)
PY
```

Expected: `missing runbook terms: []`.

---

### Task 6: Update indexes, version, and changelog

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/VERSIONS.md`
- Modify: `docs/changelog.md`

- [ ] **Step 1: Update README runbook statement**

Add that deployment, monitoring, and incident runbooks record local, staging, and production-readiness gates, and that actual implementation state must be verified from code and validation results.

- [ ] **Step 2: Update VERSIONS current version**

Change current version from `v1.0.10-docs` to `v1.0.11-docs` and mention detailed tests, fixed links, P0 schema, state matrices, API error semantics, and production-readiness runbooks.

- [ ] **Step 3: Update changelog Unreleased**

Add Added/Changed/Fixed entries for this documentation repair.

- [ ] **Step 4: Check version and changelog terms**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
checks={
'docs/VERSIONS.md':['v1.0.11-docs','P0 字段级 schema'],
'docs/changelog.md':['核心接口错误语义','详细测试用例','GitLab 只读边界事故处理'],
'docs/README.md':['实现者最短路径','production-readiness 门禁'],
}
missing=[]
for path,terms in checks.items():
    text=Path(path).read_text()
    for term in terms:
        if term not in text:
            missing.append((path,term))
print('missing index terms:', missing)
raise SystemExit(1 if missing else 0)
PY
```

Expected: `missing index terms: []`.

---

### Task 7: Final validation pass

**Files:**
- Validate all modified docs.

- [ ] **Step 1: Verify PRD acceptance mappings all have detailed test sections**

Run the traceability script from Task 1.

Expected: `Missing detailed test sections: []`.

- [ ] **Step 2: Verify non-template Markdown links resolve**

Run the link script from Task 2.

Expected: `missing link count: 0`.

- [ ] **Step 3: Scan touched files for unresolved placeholders**

Run:

```bash
grep -nE 'TODO|TBD|待补|implement later|placeholder|\{feature\}|\{[^}]+\}' \
  docs/01-prd/enterprise-ai-brain/prd.md \
  docs/02-specs/enterprise-ai-brain/spec.md \
  docs/02-specs/enterprise-ai-brain/api.md \
  docs/02-specs/enterprise-ai-brain/test-case.md \
  docs/05-runbooks/deployment.md \
  docs/05-runbooks/monitoring.md \
  docs/05-runbooks/incident-response.md \
  docs/README.md \
  docs/VERSIONS.md \
  docs/changelog.md || true
```

Expected: No unresolved placeholder hits. Curly-brace hits are acceptable only for literal API path parameters such as `{task_id}`.

- [ ] **Step 4: Verify phase labels exist**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
text=Path('docs/02-specs/enterprise-ai-brain/test-case.md').read_text()
required=['MVP 占位','v1.1','v1.2','生产就绪']
missing=[x for x in required if x not in text]
print('missing phase labels:', missing)
raise SystemExit(1 if missing else 0)
PY
```

Expected: `missing phase labels: []`.

- [ ] **Step 5: Report actual validation outputs**

Do not claim the repair is complete unless all validation commands pass.
