# GitLab Code Review MVP PRD Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the enterprise AI Brain PRD so v1 MVP includes internal GitLab Merge Request code review with a pluggable code-review executor, human confirmation, internal report archive, and no GitLab writeback.

**Architecture:** This is a documentation-only change scoped to `docs/01-prd/enterprise-ai-brain/prd.md`. It moves the `code_review` task from v1.1 into v1 MVP, defines the GitLab MR review flow, tightens scope exclusions, updates acceptance criteria, and keeps automated testing in v1.1.

**Tech Stack:** Markdown documentation, existing PRD structure, approved design at `docs/superpowers/specs/2026-05-29-gitlab-code-review-mvp-design.md`.

---

## File Structure

- Modify: `docs/01-prd/enterprise-ai-brain/prd.md`
  - Version metadata and history.
  - v1 delivery boundary table.
  - user stories and detailed scenarios.
  - v1 MVP / v1.1 scope bullets.
  - task type table and orchestration rules.
  - functional rules, interaction design, acceptance criteria, telemetry events, and rollout plan.
- No new PRD companion files.
- No code, tests, or runtime files are changed in this plan.

---

### Task 1: Update PRD version metadata and v1 boundary

**Files:**
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:7-23`
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:37-43`

- [ ] **Step 1: Update PRD version number**

Change the version info table from:

```markdown
| 功能版本 | v1.0.8 |
```

to:

```markdown
| 功能版本 | v1.0.9 |
```

- [ ] **Step 2: Add version history row**

Insert this row after the `v1.0.8` row:

```markdown
| v1.0.9 | 2026-05-29 | 将内部 GitLab Merge Request 代码 Review 提前纳入 v1 MVP，明确可插拔 code-review 执行器、人工确认、内部报告归档和不回写 GitLab 的一期边界 | Claude |
```

- [ ] **Step 3: Update v1 MVP delivery boundary row**

Replace the existing v1 MVP row with:

```markdown
| v1 MVP | 跑通可演示的研发大脑核心闭环 | 本地账号、产品/版本/模块配置、内部 GitLab 项目绑定、需求审批、产品详细设计任务、技术方案任务、内部 GitLab MR 代码 Review 任务、人工确认、知识检索、知识沉淀候选审核、模拟 Issue、Markdown 导出、代码 Review 报告内部归档、审计、Docker Compose 健康检查 | GitLab/Jenkins/线上日志真实运营采集、GitLab MR 评论或审批回写、自动化测试、完整 Bug 生命周期、全主体双向流程感知、上线后分析 |
```

- [ ] **Step 4: Update v1.1 row to remove code review first-delivery scope**

Replace the existing v1.1 row with:

```markdown
| v1.1 研发任务扩展 | 补齐研发执行阶段辅助 | 开发计划、自动化测试任务、AI 自动测试 Bug 建议、代码 Review 执行器扩展能力 | 发布风险自动聚合、线上日志趋势分析 |
```

- [ ] **Step 5: Verify boundary language**

Run:

```bash
grep -n "v1 MVP\|v1.1 研发任务扩展\|v1.0.9" docs/01-prd/enterprise-ai-brain/prd.md
```

Expected output includes `v1.0.9`, a v1 MVP row containing `内部 GitLab MR 代码 Review 任务`, and a v1.1 row that does not list `代码 Review` as a first-delivery task.

---

### Task 2: Update users, stories, and detailed business scenario

**Files:**
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:47-56`
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:112-117`
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:160-188`

- [ ] **Step 1: Update R&D owner goal wording**

Replace the `研发负责人` row in the target users table with:

```markdown
| 研发负责人 | 把确认后的需求转化为可执行研发方案，并基于内部 GitLab Merge Request 获得可审计的 AI 代码 Review 报告 | 技术方案、风险依赖、开发计划、MR Review 结论、发布上线评估 |
```

- [ ] **Step 2: Replace the R&D AI task user story**

Replace the user story beginning with `作为研发负责人` and containing `我希望 AI 任务能够覆盖产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试和发布上线评估` with:

```markdown
作为研发负责人
我希望 AI 任务在 v1 MVP 中能基于内部 GitLab Merge Request diff、已确认需求和技术方案生成代码 Review 报告
以便在不回写 GitLab 的前提下，先获得可审计、可人工确认、可归档的代码质量和风险建议。
```

- [ ] **Step 3: Update detailed scenario step 2**

Replace step 2 with:

```markdown
2. 产品负责人或管理员在产品管理中维护产品、版本、模块和内部 GitLab 项目绑定；归档版本不能用于新需求，未绑定或无权限的 GitLab 项目不能用于 v1 MVP 代码 Review 任务。
```

- [ ] **Step 4: Update detailed scenario step 13**

Replace step 13 with:

```markdown
13. v1 MVP 代码 Review 任务基于内部 GitLab Merge Request 元信息和 diff 快照、需求快照、技术方案和产品上下文，调用可插拔 code-review 执行器生成结构化 Review 报告；一期默认执行器对接 Claude Code `code-review` skill。
```

- [ ] **Step 5: Insert a new scenario step after current step 13**

Insert this new step immediately after the updated code review step, then renumber following steps manually:

```markdown
14. Review 报告包含摘要、整体风险等级、问题清单、严重程度、文件路径、行号或范围、问题分类、修改建议、置信度和执行器元数据，进入人工确认后只能在 AI Brain 内部归档，不回写 GitLab 评论、审批状态或合并状态。
```

- [ ] **Step 6: Update scenario wording for confirmed outputs**

After renumbering, replace the step that says `负责人确认关键 AI 产出后，系统生成模拟 Issue、Markdown 方案、Review 结论、Bug 或发布评估结果。` with:

```markdown
负责人确认关键 AI 产出后，系统生成模拟 Issue、Markdown 方案、内部代码 Review 报告归档、Bug 或发布评估结果；v1 MVP 的代码 Review 只归档 AI Brain 内部报告和人工确认结论。
```

- [ ] **Step 7: Verify scenario contains the new flow**

Run:

```bash
grep -n "内部 GitLab Merge Request\|code-review 执行器\|不回写 GitLab\|内部代码 Review 报告归档" docs/01-prd/enterprise-ai-brain/prd.md
```

Expected output includes at least four matching lines.

---

### Task 3: Update PRD scope and task type definitions

**Files:**
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:196-237`
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:254-291`

- [ ] **Step 1: Replace MVP task type scope bullet**

Replace:

```markdown
- MVP AI 任务类型覆盖产品详细设计和技术方案。
```

with:

```markdown
- MVP AI 任务类型覆盖产品详细设计、技术方案和内部 GitLab MR 代码 Review。
```

- [ ] **Step 2: Add MVP GitLab code review scope bullets**

Insert these bullets after the MVP task type bullet:

```markdown
- 内部 GitLab Merge Request 元信息和 diff 拉取，生成本次 Review 的不可变输入快照。
- 可插拔 code-review 执行器，一期默认对接 Claude Code `code-review` skill，输出结构化 Review 报告。
- 代码 Review 报告人工确认、修改后采纳、驳回重跑、要求补充信息和内部归档。
```

- [ ] **Step 3: Replace v1.1 task type bullet**

Replace:

```markdown
- AI 任务类型扩展到代码开发辅助、代码 Review 和自动化测试。
```

with:

```markdown
- AI 任务类型扩展到代码开发辅助和自动化测试，并增强 code-review 执行器的可替换能力。
```

- [ ] **Step 4: Add explicit out-of-scope GitLab writeback bullet**

Insert this bullet in `Out of Scope` after `自动修改代码、自动提交 PR、自动部署上线。`:

```markdown
- v1 MVP 不向 GitLab 回写 Review 评论、审批状态、request changes、合并状态或分支变更。
```

- [ ] **Step 5: Update 功能点 2 description**

Replace the sentence:

```markdown
**描述**: 在需求审批通过后，AI 任务按业务阶段提供产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估和上线后分析能力。v1 MVP 仅要求产品详细设计和技术方案任务闭环；其他任务类型为 v1.1 或 v1.2 扩展能力。
```

with:

```markdown
**描述**: 在需求审批通过后，AI 任务按业务阶段提供产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估和上线后分析能力。v1 MVP 要求产品详细设计、技术方案和内部 GitLab MR 代码 Review 任务闭环；开发计划、自动化测试、发布上线评估和上线后分析为后续扩展能力。
```

- [ ] **Step 6: Update code_review row in task type table**

Replace the `code_review` task row with:

```markdown
| `code_review` | 内部 GitLab MR 元信息和 diff 快照、关联需求、技术方案、产品上下文、项目规范 | 结构化 Review 报告、问题清单、风险等级、文件/行号、修改建议、执行器元数据 | Reviewer 确认 Review 报告 | v1 MVP | 是 |
```

- [ ] **Step 7: Update automated_testing row phase remains v1.1**

Verify this row still says `v1.1` and `否`:

```markdown
| `automated_testing` | PRD、验收标准、技术方案、已有测试用例 | 测试用例建议、自动化测试脚本建议、测试结果分析、Bug 登记建议 | 测试负责人确认测试结论 | v1.1 | 否 |
```

- [ ] **Step 8: Update code_review orchestration row**

Replace the `code_review` orchestration row with:

```markdown
| `code_review` | 研发负责人或 Reviewer 选择内部 GitLab Merge Request 后创建 | 已确认技术方案、产品 GitLab 项目绑定、MR 元信息和 diff 快照 | v1 MVP |
```

- [ ] **Step 9: Update MVP chain paragraph**

Replace:

```markdown
`product_detail_design` 和 `technical_solution` 构成 v1 MVP 的串行核心链路；其他任务类型是同一需求或产品上下文下的独立阶段任务，可在满足前置输入后单独创建，不要求由最初需求审批流一次性自动生成。
```

with:

```markdown
`product_detail_design`、`technical_solution` 和 `code_review` 构成 v1 MVP 的最小研发闭环；`code_review` 需要基于已确认技术方案和内部 GitLab MR diff 快照单独创建，不要求由最初需求审批流一次性自动生成。其他任务类型是同一需求或产品上下文下的独立阶段任务，可在满足前置输入后单独创建。
```

- [ ] **Step 10: Add code review rules**

Insert these bullets after `高影响 AI 产出必须进入人工确认点后才能继续下一阶段或进入回写。`:

```markdown
- v1 MVP 代码 Review 任务必须通过产品绑定的内部 GitLab 项目读取 Merge Request 元信息和 diff，并保存不可变输入快照。
- code-review 执行器必须是可插拔边界，一期默认对接 Claude Code `code-review` skill；报告进入人工确认后才能归档为正式 Review 结论。
- v1 MVP 代码 Review 的 `writing_back` 仅表示 AI Brain 内部报告归档，不得回写 GitLab 评论、审批状态、request changes、合并状态或分支变更。
```

- [ ] **Step 11: Add code review exception handling**

Insert these bullets before `回写、Review、测试或发布评估失败可查询失败原因并重试。`:

```markdown
- GitLab 项目未绑定、MR 不存在、权限不足、MR diff 过大、GitLab API 超时或限流时，任务进入 `failed` 或 `waiting_more_info`，并展示可操作错误原因。
- code-review 执行器失败时记录执行器类型、错误码、trace_id、失败阶段和是否可重试。
```

- [ ] **Step 12: Verify task type table and scope**

Run:

```bash
grep -n "MVP AI 任务类型覆盖\|code_review.*v1 MVP\|code-review 执行器\|不得回写 GitLab" docs/01-prd/enterprise-ai-brain/prd.md
```

Expected output includes the new MVP scope bullet, `code_review` table row, executor rules, and no-GitLab-writeback rule.

---

### Task 4: Update interaction design, acceptance criteria, telemetry, and rollout plan

**Files:**
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:407-456`
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:458-508`
- Modify: `docs/01-prd/enterprise-ai-brain/prd.md:522-565`

- [ ] **Step 1: Add code review sub-pages under task center**

Under `│  ├─ 代码 Review`, add these child lines with matching indentation:

```markdown
│  │  ├─ GitLab MR 选择
│  │  ├─ MR diff 快照
│  │  ├─ Review 报告
│  │  └─ Review 报告确认
```

- [ ] **Step 2: Update key interaction item 1**

Replace key interaction item 1 with:

```markdown
1. 任务详情页展示需求、任务类型、AI 中间结果、检索证据、内部 GitLab MR diff 快照、代码/测试/发布相关上下文、风险、Review 报告和审计轨迹。
```

- [ ] **Step 3: Insert key interaction for code review task**

Insert this item after current key interaction item 4 and renumber following items:

```markdown
5. 代码 Review 任务创建时必须选择已绑定且有权限的内部 GitLab 项目和 Merge Request；任务详情展示 MR 元信息、diff 快照、执行器信息、结构化 Review 报告、人工确认状态和内部归档结果。
```

- [ ] **Step 4: Update AC3a**

Replace AC3a with:

```markdown
- [ ] AC3a: v1 MVP 中产品详细设计、技术方案和内部 GitLab MR 代码 Review 报告等高影响 AI 产出必须经过人工确认后才能进入下一阶段或归档。
```

- [ ] **Step 5: Update AC3b**

Replace AC3b with:

```markdown
- [ ] AC3b: v1.1 中开发计划和自动化测试结论必须经过人工确认后才能进入下一阶段或回写。
```

- [ ] **Step 6: Add new AC21 for GitLab MR code review**

Add this acceptance criterion after AC20:

```markdown
- [ ] AC21: v1 MVP 支持基于内部 GitLab Merge Request 拉取 MR 元信息和 diff 快照，调用可插拔 code-review 执行器生成结构化 Review 报告，并在人工确认后仅归档到 AI Brain 内部；系统不得向 GitLab 回写评论、审批状态、request changes、合并状态或分支变更。
```

- [ ] **Step 7: Add AC21 mapping row**

Add this row after the AC20 mapping row:

```markdown
| AC21 | 内部 GitLab MR 代码 Review 闭环 | TC-AIBRAIN-REVIEW-FUNC-023 | P0 |
```

- [ ] **Step 8: Add telemetry event for MR diff snapshot**

Insert after `ai_task_reviewed`:

```markdown
| gitlab_mr_diff_snapshotted | 内部 GitLab MR 元信息和 diff 快照拉取完成 | task_id, product_id, repository_id, project_id, mr_iid, changed_file_count, diff_ref |
```

- [ ] **Step 9: Add telemetry event for review report archived**

Insert after `gitlab_mr_diff_snapshotted`:

```markdown
| code_review_report_archived | 代码 Review 报告经人工确认后归档 | task_id, review_id, risk_level, finding_count, executor_type, executor_name |
```

- [ ] **Step 10: Update phase two rollout scope**

Replace phase two scope with:

```markdown
- 范围: 需求审批、产品详细设计任务、技术方案任务、内部 GitLab MR 代码 Review 任务、LangGraph 运行、人工确认、知识检索、知识沉淀审核、模拟回写、Markdown 导出、代码 Review 报告内部归档、审计。
```

- [ ] **Step 11: Update phase two blocking acceptance**

Replace phase two blocking acceptance with:

```markdown
- 阻塞验收: AC1、AC2、AC3a、AC4、AC5、AC6、AC10、AC11、AC12、AC13、AC21。
```

- [ ] **Step 12: Update phase three rollout scope**

Replace phase three scope with:

```markdown
- 范围: 开发计划、自动化测试任务、AI 自动测试 Bug 建议、code-review 执行器扩展能力和运行审计体验增强。
```

- [ ] **Step 13: Verify acceptance and rollout updates**

Run:

```bash
grep -n "AC21\|TC-AIBRAIN-REVIEW-FUNC-023\|gitlab_mr_diff_snapshotted\|code_review_report_archived\|阶段二：v1 MVP 核心闭环\|阶段三：v1.1" docs/01-prd/enterprise-ai-brain/prd.md
```

Expected output includes AC21, its mapping, both telemetry events, and updated rollout sections.

---

### Task 5: Final PRD consistency checks

**Files:**
- Verify: `docs/01-prd/enterprise-ai-brain/prd.md`

- [ ] **Step 1: Check code review is no longer positioned as v1.1 first delivery**

Run:

```bash
grep -n "代码 Review.*v1.1\|code_review.*v1.1\|AC3b.*代码 Review" docs/01-prd/enterprise-ai-brain/prd.md
```

Expected: no output.

- [ ] **Step 2: Check automated testing remains in v1.1**

Run:

```bash
grep -n "automated_testing.*v1.1\|自动化测试.*v1.1\|AC3b.*自动化测试" docs/01-prd/enterprise-ai-brain/prd.md
```

Expected: output includes the automated testing task row and AC3b.

- [ ] **Step 3: Check no GitLab writeback is allowed in MVP**

Run:

```bash
grep -n "不向 GitLab 回写\|不得回写 GitLab\|不回写 GitLab" docs/01-prd/enterprise-ai-brain/prd.md
```

Expected: output includes out-of-scope, task rules, and AC21.

- [ ] **Step 4: Check line references to design source are not required**

Run:

```bash
grep -n "superpowers/specs\|GitLab Code Review MVP Design" docs/01-prd/enterprise-ai-brain/prd.md
```

Expected: no output. The PRD should stand alone as product source of truth.

- [ ] **Step 5: Report PRD update completion**

When all checks match expected output, report that `docs/01-prd/enterprise-ai-brain/prd.md` is updated and note that API/spec/test-case docs still need follow-up alignment in separate tasks.

---

## Self-Review

Spec coverage:
- v1 MVP GitLab MR code review scope: covered by Tasks 1, 3, and 4.
- Automated testing remains later: covered by Tasks 1, 3, and 5.
- Pluggable code-review executor defaulting to Claude Code `code-review` skill: covered by Task 3.
- Human confirmation and internal archive only: covered by Tasks 3 and 4.
- No GitLab writeback: covered by Tasks 3, 4, and 5.
- Error handling, audit, and telemetry: covered by Tasks 3 and 4.

Placeholder scan:
- No TBD, TODO, placeholder, or “implement later” instructions remain.

Type/name consistency:
- Uses `code_review`, `automated_testing`, `AC21`, and `TC-AIBRAIN-REVIEW-FUNC-023` consistently.
- Keeps `v1 MVP`, `v1.1`, and `v1.2` boundaries aligned with the approved design.
