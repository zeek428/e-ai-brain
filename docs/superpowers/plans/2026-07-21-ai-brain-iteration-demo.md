# AI Brain 功能迭代需求驱动研发协同演示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在真实本地 AI Brain 环境中，用“统一研发执行策略支持维护岗位经验复用的可信域配置，并在研发协同工作项中展示已批准经验的引用与证据”这一产品需求，完成两轮可审计的研发协同演示：第一轮产生真实代码、测试、远程开发分支推送、知识沉淀和岗位经验；第二轮证明仅在可信域、兼容策略和独立审核条件全部满足时复用经批准经验。全程不部署。

**Architecture:** AI Brain 的需求评估为研发流程入口，优先复用兼容的“规划中”迭代版本；协作编排器根据冻结的研发执行策略创建角色工作项和人工门禁；本地 Codex Runner 在 Git worktree 中完成受限范围的实现、测试与文档工作；项目负责人、代码审查人、知识审核人和经验审核人分别在系统中决策。数据库保存运行、策略快照、工作项、评审、知识和经验记录；前端仅将已注入的结构化经验引用可视化，绝不展示未审核的经验正文或绕过后端授权。

**Tech Stack:** React 18、TypeScript、Ant Design Pro、Umi/Max、Vitest；FastAPI、PostgreSQL、Redis、LangGraph；本地 Codex Runner；GitHub `origin`。

## Global Constraints

- 演示目标产品是现有 **AI Brain**（`product_119`），不新建演示产品；目标远程分支固定为 `codex/rd-collaboration-v2`。
- 不修改现有定时作业；不执行部署、发布、环境变更或生产写入。
- 第一轮仅允许改动以下路径：

  ```text
  apps/web/src/pages/RdExecutorPolicies/index.tsx
  apps/web/src/pages/RdCollaboration/WorkItemDag.tsx
  apps/web/src/services/rdCollaborationClient.ts
  apps/web/tests/RdExecutorPoliciesPage.test.tsx
  apps/web/tests/RdCollaborationPage.test.tsx
  docs/08-help/delivery.md
  docs/08-help/assets/screenshots/help-rd-collaboration.png
  docs/changelog.md
  ```

- 每次 Runner 提交或人工推送前必须检查暂存路径；发现范围外的文件、未追踪的敏感文件或不属于本需求的用户改动，立即停止该工作项并交给项目负责人处理。
- 不修改或复用旧的 `task_compat` 策略记录；创建新的统一研发执行策略和其不可变快照。第二轮仅更新第一轮交付得到的策略版本。
- 不通过直接写数据库、伪造执行状态、跳过人工评审或手工构造“已批准经验”来证明流程。诊断查询可以只读执行；所有业务状态都必须由真实 API/UI 流程产生。
- 未达到可信 Runner、最小权限、Git 目标分支、评审人独立性、测试通过和远程推送证据任一条件时，不得进入 `ready_for_release`。

---

## Task 1: 固化演示基线并完成运行前门禁

**Files:**

- Read: `AGENTS.md`
- Read: `docs/superpowers/specs/2026-07-21-ai-brain-iteration-demo-design.md`
- Read: `apps/api/app/services/rd_role_experiences.py`
- Read: `apps/api/app/services/rd_collaboration_planning.py`
- Read: `apps/web/package.json`

- [ ] **Step 1: 记录 Git 与文件范围基线。**

  Run:

  ```bash
  git status --short --branch
  git diff --name-only
  git ls-files --others --exclude-standard
  git remote -v
  git log -1 --format='%H %s'
  ```

  Expected: 当前检出分支是 `codex/rd-collaboration-v2`；没有会被本演示覆盖的用户改动；`origin` 指向配置的 GitHub 仓库。若不满足，记录差异并停止，不用重置或清理命令处理。

- [ ] **Step 2: 验证 API、数据库、前端和执行 Worker 的真实健康状态。**

  Run:

  ```bash
  curl --fail --silent http://127.0.0.1:8000/health
  curl --fail --silent -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5173/delivery/versions
  launchctl print "gui/$(id -u)/com.ai-brain.web"
  docker exec e-ai-brain-postgres psql -U ai_brain -d ai_brain -c "select now();"
  ```

  Expected: `/health` 同时报告 PostgreSQL 和 Redis 为 `ok`；版本页返回 200；前端启动目录和当前根仓库一致；数据库可读。若 5173 仍来自已分离或旧的 worktree，先安全重启开发服务到 `/Users/zeek/source/e-ai-brain/apps/web`，再刷新浏览器确认不是旧 bundle。

- [ ] **Step 3: 验证 Runner、角色权限和远程分支约束。**

  在已登录的真实系统中打开“需求交付 → 研发执行器策略”和“任务中心 → 执行器”，确认：

  1. 至少一个 `runner_polling` 本地 Codex Runner 为 active，心跳新鲜、并发槽位可用，`coding` 信任域可用；
  2. 执行器具备代码、测试、文档工作项所需的最小权限，而不具备部署权限；
  3. AI Brain 的 Git 资源可明确选择 `codex/rd-collaboration-v2`，且不会将提交推向 `master`；
  4. 项目负责人/代码审查人与知识审核人/经验审核人不是同一主体；
  5. API 与 Worker 都启用 `RD_ROLE_EXPERIENCE_ENABLED=true` 后才允许进入经验沉淀环节。

  Expected: 以上五项均有页面或审计证据。任何一项失败只创建/处理人工决策请求，不以配置绕过继续。

- [ ] **Step 4: 记录演示会话证据。**

  创建一条本地演示记录，保存基线 commit、服务健康结果、Runner ID、计划使用的仓库 ID、目标分支、当前用户/角色和开始时间。该记录只存入演示任务的证据字段或审计附件，不写入代码库。

## Task 2: 在系统内创建需求、评估并绑定版本和策略

**Files:**

- Modify through UI/API only: requirement, product-version, repository binding, unified RD policy records
- Read: `docs/01-prd/enterprise-ai-brain/prd.md`
- Read: `docs/02-specs/enterprise-ai-brain/spec.md`
- Read: `docs/02-specs/enterprise-ai-brain/api/delivery-and-tasks.md`

- [ ] **Step 1: 创建真实产品需求。**

  在“需求交付 → 需求管理”创建需求，标题为：

  ```text
  AI Brain：研发执行策略岗位经验可信域配置与协同引用可视化
  ```

  验收标准必须包含：

  1. 统一研发执行策略可维护仓库可信域和工具可信域，写入不可变策略快照；
  2. 只有已批准、未过期、与快照策略兼容、且其证据均落在配置可信域内的岗位经验可被规划器注入；
  3. 工作项 DAG 显示经验 ID、版本和证据数量，不能显示未审核正文；
  4. 更新策略配置、策略 schema/version、权限或目标分支后，旧经验不会继续被静默复用；
  5. 前端单元测试、类型检查、帮助中心资源检查通过，代码经独立审查后仅推送到 `codex/rd-collaboration-v2`；
  6. 不部署，只交付 `ready_for_release` 证据。

- [ ] **Step 2: 在系统中评估需求并处理版本选择。**

  运行需求评估。优先选择一条与“研发协同/执行策略前端改造”范围兼容且状态为“规划中”的 AI Brain 迭代版本；若没有兼容版本，使用系统“创建新版本”动作创建新版本，并将评估结果、需求和版本关联。

  Expected: 版本决策由评估结果持久化；不得以直接 SQL 修改版本状态替代评估。

- [ ] **Step 3: 配置新的统一研发执行策略。**

  在选定版本上创建新策略，明确：

  | 角色 | 执行主体 | 工作范围 |
  | --- | --- | --- |
  | 产品经理 | AI | 验收标准、依赖、风险和可执行计划 |
  | 开发 | AI + 本地 Codex Runner | 仅 Global Constraints 允许的实现与测试路径 |
  | 测试 | AI | 前端单测、类型检查、实际页面回归和证据归档 |
  | 文档 | AI | 帮助中心和变更说明 |
  | 项目负责人 | 人工 | 范围、风险、取消/返工及推进决策 |
  | 代码审查 | 人工 | 合并前代码与远程推送确认 |
  | 知识/经验审核 | 人工且独立 | 知识沉淀和经验候选审核 |

  初始 `experience_reuse_config` 保留启用状态但不配置可信域，确保第一轮不会引用历史经验；设置 `max_context_tokens=2000`、`max_items=5`、`policy_compatibility=same_policy_schema`、`require_independent_reviewer=true`。部署目标固定 `ready_for_release`，禁止 deployment executor。

- [ ] **Step 4: 冻结、检查并保存策略快照证据。**

  启动协作前确认运行返回并持久化 `strategy_snapshot_id`、策略 ID/version/hash/schema_version；核对角色绑定、目标分支、交付目标和经验复用配置与表单一致。若快照缺失、版本不可活动或分支不匹配，停止并重新评估，不创建工作项。

## Task 3: 先写失败测试，再为策略可信域配置实现前端能力

**Files:**

- Modify: `apps/web/tests/RdExecutorPoliciesPage.test.tsx`
- Modify: `apps/web/src/pages/RdExecutorPolicies/index.tsx`

- [ ] **Step 1: 在策略页面测试中写出失败案例。**

  新增测试覆盖创建/编辑策略时：

  ```ts
  expect(createBody.strategy_config.experience_reuse_config).toMatchObject({
    repository_trust_domains: ['repo:ai-brain'],
    tool_trust_domains: ['coding'],
    max_context_tokens: 2000,
    max_items: 5,
    policy_compatibility: 'same_policy_schema',
    require_independent_reviewer: true,
  });
  ```

  同时覆盖读取已有策略配置会回填两个可信域字段。只验证结构化 payload，不让测试依赖展示文案或网络调用顺序。

- [ ] **Step 2: 运行测试并确认它因缺少字段而失败。**

  Run:

  ```bash
  cd apps/web && npm test -- --run tests/RdExecutorPoliciesPage.test.tsx
  ```

  Expected: 新断言失败，失败原因是表单尚未读取/发送可信域，而不是 mock、环境或既有测试故障。

- [ ] **Step 3: 实现可信域表单、回填和 payload 规范化。**

  在 `PolicyFormValues` 增加 `repositoryTrustDomains`、`toolTrustDomains`；在 `initialFormValues()` 从 `strategy_config.experience_reuse_config` 回填；在 `buildPayload()` 写入：

  ```ts
  experience_reuse_config: {
    enabled: true,
    max_context_tokens: 2000,
    max_items: 5,
    policy_compatibility: 'same_policy_schema',
    require_independent_reviewer: true,
    repository_trust_domains: normalizeTrustDomains(values.repositoryTrustDomains),
    tool_trust_domains: normalizeTrustDomains(values.toolTrustDomains),
  }
  ```

  使用 Ant Design 的 tags/select 输入或项目现有等价组件；去除空值、首尾空白和重复项；保留空数组的兼容语义，但在页面说明中明确“两个可信域均配置后才可能发生岗位经验复用”。不要在浏览器端判定经验是否可信。

- [ ] **Step 4: 重新运行策略页面测试。**

  Run:

  ```bash
  cd apps/web && npm test -- --run tests/RdExecutorPoliciesPage.test.tsx
  ```

  Expected: 全部通过；新增测试证明创建、编辑和读取都不会丢失可信域。

## Task 4: 先写失败测试，再让协作 DAG 可解释地展示经验引用

**Files:**

- Modify: `apps/web/tests/RdCollaborationPage.test.tsx`
- Modify: `apps/web/src/services/rdCollaborationClient.ts`
- Modify: `apps/web/src/pages/RdCollaboration/WorkItemDag.tsx`

- [ ] **Step 1: 为后端返回的工作项 contract 写失败的页面测试。**

  在协作页 mock 的工作项中加入：

  ```ts
  input_contract: {
    approved_role_experience_context: [
      { experience_id: 'experience_001', version: 2, evidence_refs: ['knowledge_deposit_001'] },
    ],
  }
  ```

  断言页面能显示“已引用 1 条岗位经验”、`experience_001`、`v2` 和“1 条证据”；另断言没有经验上下文时保持现有卡片布局。

- [ ] **Step 2: 运行协作页面测试并确认失败。**

  Run:

  ```bash
  cd apps/web && npm test -- --run tests/RdCollaborationPage.test.tsx
  ```

  Expected: 新断言因类型或渲染缺失失败。

- [ ] **Step 3: 扩展客户端类型和 DAG 展示。**

  在 `RdWorkItem` 添加可选 `input_contract` 类型；在 `WorkItemDag` 只提取 `approved_role_experience_context` 的经验 ID、版本和 `evidence_refs.length`。在工作项卡片中使用紧凑的、可访问的摘要展示，例如：

  ```tsx
  <Tag color="blue">已引用 {contexts.length} 条岗位经验</Tag>
  ```

  随后逐条显示 `经验 {experience_id} · v{version} · {evidenceCount} 条证据`。缺失/异常数据用 `0 条证据` 降级，不渲染候选经验正文、提示词、秘密或无授权的知识片段。

- [ ] **Step 4: 重新运行页面测试。**

  Run:

  ```bash
  cd apps/web && npm test -- --run tests/RdCollaborationPage.test.tsx
  ```

  Expected: 现有协作页测试和新增的经验引用场景均通过。

## Task 5: 补齐帮助、截图和前端交付验证

**Files:**

- Modify: `docs/08-help/delivery.md`
- Modify: `docs/08-help/assets/screenshots/help-rd-collaboration.png`
- Modify: `docs/changelog.md`

- [ ] **Step 1: 更新用户帮助。**

  在研发执行策略章节说明如何维护仓库/工具可信域、空可信域为何不复用经验、策略版本变更如何使旧经验不再兼容；在研发协同章节说明 DAG 的“已引用岗位经验”摘要、证据数量、人工审核和排障路径。不要把经验正文或内部 ID 写成用户必须手工编辑的配置。

- [ ] **Step 2: 用真实本地页面替换帮助截图。**

  使用已登录的管理员/项目负责人账号打开 `http://127.0.0.1:5173/delivery/rd-collaboration`，确保当前服务来自根仓库的最新 bundle，显示新摘要且不包含 token、密码、个人联系方式、私有域名或敏感业务内容，然后写入上述截图路径。

- [ ] **Step 3: 运行前端自动验证。**

  Run:

  ```bash
  cd apps/web && npm test -- --run tests/RdExecutorPoliciesPage.test.tsx tests/RdCollaborationPage.test.tsx
  cd apps/web && npm run typecheck
  cd apps/web && npm run help:check
  ```

  Expected: 三个命令成功。若已有基线失败，记录测试名称、错误签名和当前 commit，确认新增文件不在失败集合后再继续；不得用失败数量相同来判断通过。

- [ ] **Step 4: 真实浏览器回归。**

  在浏览器分别检查 `/delivery/rd-executor-policies` 和 `/delivery/rd-collaboration`：标题、策略表单、两个可信域字段、DAG 经验摘要、编辑回填、刷新后数据保留、无控制台/网络运行时错误。保存 URL、角色、关键交互和结果到演示证据。

## Task 6: 第一轮真实研发协同——从需求评估到待发布

**Files:**

- Modify through AI Brain UI/API only: requirement assessment, version, run, work items, reviews, evidence

- [ ] **Step 1: 启动协作并审查计划 DAG。**

  从已评估需求的版本总览发起“推进 AI 协同开发”。确认协作运行使用 Task 2 的 `strategy_snapshot_id`，计划包含产品、开发、测试、文档工作项，并明确依赖关系、负责人、尝试次数、幂等键和人工门禁。因初始可信域为空，所有工作项的 `approved_role_experience_context` 都必须为空。

- [ ] **Step 2: 由 AI 角色在授权范围内完成工作项。**

  产品经理先提交实现计划和风险；项目负责人确认后，开发、测试和文档工作项按依赖可并行执行。开发 Runner 只能修改 Global Constraints 白名单路径，测试角色提交实际命令输出，文档角色提交帮助更新。失败工作项必须保留 attempt/evidence，并由项目负责人选择返工、取消或人工处理；不得在 UI 外“补状态”。

- [ ] **Step 3: 人工复核并验证工作区。**

  当所有依赖完成后，独立代码审查人检查 diff 和自动化证据：

  ```bash
  git diff --check
  git diff --name-only
  git diff -- apps/web/src/pages/RdExecutorPolicies/index.tsx apps/web/src/pages/RdCollaboration/WorkItemDag.tsx apps/web/src/services/rdCollaborationClient.ts apps/web/tests/RdExecutorPoliciesPage.test.tsx apps/web/tests/RdCollaborationPage.test.tsx docs/08-help/delivery.md docs/changelog.md
  cd apps/web && npm test -- --run tests/RdExecutorPoliciesPage.test.tsx tests/RdCollaborationPage.test.tsx
  cd apps/web && npm run typecheck
  cd apps/web && npm run help:check
  ```

  Expected: `git diff --check` 无输出，变更路径均在白名单内，验证命令都通过。任何偏差创建返工工作项，禁止由审查人直接修改或越过审查。

- [ ] **Step 4: 提交并只推送远程开发分支。**

  在系统的代码审查/远程推送门禁获得批准后，使用协作运行生成的提交推送到：

  ```bash
  git push origin HEAD:codex/rd-collaboration-v2
  git ls-remote --heads origin codex/rd-collaboration-v2
  ```

  记录 commit SHA、远程 ref、审查 ID 和推送审计事件。不得推送 `master`、不得创建发布标签、不得部署。

- [ ] **Step 5: 收口为待发布，不部署。**

  在版本总览确认协作运行、需求、任务、评审和测试均关联到同一版本；按策略转入 `ready_for_release` 并记录原因“代码已推送、测试和评审通过，等待人工发布决策”。未出现部署运行、Jenkins 发布记录或生产环境写入。

## Task 7: 第一轮知识沉淀与岗位经验审核

**Files:**

- Modify through AI Brain UI/API only: knowledge deposits, role feedback and experience records

- [ ] **Step 1: 生成并审核项目知识沉淀。**

  从完成的需求/任务创建知识沉淀候选，内容包括策略可信域配置模型、前端展示约束、测试命令和远程分支证据。知识审核人确认归属为 AI Brain 项目、关联本次版本和 commit，并批准；记录 knowledge deposit ID、审核 ID 和检索范围。

- [ ] **Step 2: 形成可审核的角色经验候选。**

  使用工作项反馈归因将有效经验沉淀为候选：产品经理的验收/风险模板、开发的受限实现和审查要点、测试的验证证据。每条候选必须绑定角色、策略快照、来源工作项、commit/知识证据、置信度、版本和 trust domain，而不是只写自然语言总结。

- [ ] **Step 3: 由独立经验审核人批准。**

  审核人验证证据在允许范围、来源运行已完成、策略 schema/version 兼容、没有越权内容后，将所需候选由 `pending` 转为 `approved`。记录审核人、批准时间、经验 ID/version 和审计事件；拒绝项保留为 `rejected`，不进入第二轮上下文。

## Task 8: 第二轮真实协同——受控复用已批准岗位经验

**Files:**

- Modify through AI Brain UI/API only: existing unified policy new version, second requirement/version/run/reviews

- [ ] **Step 1: 以第一轮交付结果更新策略版本。**

  编辑第一轮新建的统一策略，配置：

  ```text
  repository_trust_domains = ["repo:ai-brain"]
  tool_trust_domains       = ["coding"]
  ```

  保持 `same_policy_schema`、`require_independent_reviewer=true`、`max_context_tokens=2000` 和 `max_items=5`。保存后重新冻结第二轮运行的策略快照；不得修改第一轮已冻结的快照。

- [ ] **Step 2: 创建小型兼容验证需求并运行评估。**

  创建需求“AI Brain：验证已批准岗位经验在协同规划中的受控引用”，范围只包括读取已批准经验、展示引用摘要和验证不会泄露正文。按同一版本规则评估并进入协作，不允许借此扩大为部署或其他模块改造。

- [ ] **Step 3: 验证规划器注入和 UI 可解释性。**

  在协作 DAG 的相应工作项确认：

  1. 有 `已引用 N 条岗位经验` 摘要；
  2. 每条只显示经验 ID、版本和证据数量；
  3. 所有经验都是 approved 且来自第一轮；
  4. 原始工作项 `input_contract.approved_role_experience_context` 与页面摘要数量相符；
  5. 更新策略版本、清空任一可信域或将经验设为 retired 后，重新规划不会再复用该经验。

  对第 4 项使用授权的协作详情 API/UI 只读核验，并把 trace ID 记录为证据；不得输出经验正文。

- [ ] **Step 4: 完成第二轮审批与收口。**

  第二轮只需验证规划和经验复用门禁；若产生代码变更，仍遵守第一轮白名单、审查、推送和 `ready_for_release` 规则。若不产生代码变更，保留“无需变更”的评审结论、测试证据和协作运行审计，而不是伪造提交。

## Task 9: 汇总证据、复盘和最终验收

**Files:**

- Modify through AI Brain UI/API only: run evidence, role feedback, audit links

- [ ] **Step 1: 建立端到端证据矩阵。**

  为两轮运行整理如下字段：需求 ID、评估 ID、版本 ID、策略快照 ID/hash、协作运行 ID、工作项/attempt ID、人工决策 ID、Runner ID、测试命令及输出摘要、commit SHA、远程 ref、知识沉淀 ID、经验 ID/version、trace ID 和最终状态。

- [ ] **Step 2: 逐项完成验收。**

  必须同时满足：需求评估优先复用版本或有创建新版本理由；工作项有负责人和依赖；并行、审核、返工和人工升级均有真实记录；第一轮已推送开发分支并停在 `ready_for_release`；知识和经验都经独立审核；第二轮仅在可信域和兼容策略下复用 approved 经验；版本总览可作为流程总入口；未发生部署。

- [ ] **Step 3: 做最终范围与安全复核。**

  Run:

  ```bash
  git status --short
  git log --oneline origin/codex/rd-collaboration-v2..HEAD
  git ls-remote --heads origin codex/rd-collaboration-v2
  ```

  Expected: 仅有已审查、已提交的白名单代码/文档变更；远程开发分支包含批准 commit；没有密钥、部署文件、定时作业或范围外改动。将未完成项明确列为遗留项，不能以“演示已完成”掩盖。

