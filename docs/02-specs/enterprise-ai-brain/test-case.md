# 企业 AI 大脑平台测试用例

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.47 |
| 适用系统版本 | ≥ v1.0.0 |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0.0 | 2026-05-27 | 基于 PRD 和技术规格生成项目级测试用例 | Claude |
| v1.0.1 | 2026-05-27 | 对齐当前 API 契约，补充产品上下文和配置接口测试 | Codex |
| v1.0.2 | 2026-05-28 | 补充四个主体独立维护、需求任务解耦、知识中心运营和主体级审计测试 | Claude |
| v1.0.3 | 2026-05-29 | 补充 GitLab、线上日志、Jenkins、首页看板和 Bug 管理测试用例 | Claude |
| v1.0.4 | 2026-05-29 | 补充研发全链路 AI 任务类型测试覆盖 | Claude |
| v1.0.5 | 2026-05-29 | 补充软件研发全流程感知测试用例 | Claude |
| v1.0.6 | 2026-05-29 | 对齐 PRD 阶段边界，拆分人工确认门禁测试并更新全流程感知编号 | Claude |
| v1.0.7 | 2026-05-29 | 补充用户使用洞察、用户反馈收集和 AI 迭代规划建议测试用例 | Claude |
| v1.0.8 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 纳入 v1 MVP，新增 MR diff 快照、code-review 执行器、人工确认和不回写 GitLab 的 P0 测试 | Claude |
| v1.0.9 | 2026-05-29 | 修正 v1 MVP 与 v1.1/v1.2 测试验收口径，明确 MVP 占位入口和后续完整闭环能力的测试边界 | Claude |
| v1.1.0 | 2026-05-29 | 对齐 PRD v1.1.0，补充 MVP-A/B/C 验收切片，修正 GitLab 每日指标采集阶段归属 | Claude |
| v1.1.1 | 2026-05-29 | 修复产品评审问题：将 GitLab 预览和 diff 快照前置到 MVP-A，拆分 AC4/AC21 测试，改为阶段 + 阶段内优先级口径 | Claude |
| v1.1.2 | 2026-05-30 | 将 Bug 管理基础接口纳入 v1.1 自动化验收，覆盖登记、筛选、状态机、重复归并、权限和审计 | Codex |
| v1.1.3 | 2026-05-31 | 补充审计按操作者和时间范围过滤，以及审计列表详情、链路追踪页面验收 | Codex |
| v1.1.4 | 2026-05-31 | 补充 code_review 执行器失败专用错误码和审计断言 | Codex |
| v1.1.5 | 2026-05-31 | 补充 GitLab MR diff 超限失败审计验收 | Codex |
| v1.1.6 | 2026-05-31 | 补充 GitLab MR 变更文件数超限验收 | Codex |
| v1.1.7 | 2026-05-31 | 补充 GitLab MR 单文件 diff 行数超限验收 | Codex |
| v1.1.8 | 2026-05-31 | 补充 MVP 角色目录接口、用户管理角色固定选择和 SQL 角色字典验收 | Codex |
| v1.1.9 | 2026-05-31 | 补充产品配置写入 PostgreSQL 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.10 | 2026-05-31 | 补充需求台账写入 PostgreSQL `requirements` 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.11 | 2026-05-31 | 补充 AI 任务写入 PostgreSQL `ai_tasks` 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.12 | 2026-05-31 | 补充人工确认、Graph Run 和检查点写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.13 | 2026-05-31 | 补充角色目录职责、数据范围、决策范围和前端角色目录加载验收 | Codex |
| v1.1.14 | 2026-05-31 | 补充知识文档、知识沉淀候选和审计事件写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.15 | 2026-05-31 | 补充 Bug 管理写入 PostgreSQL `bugs` 结构表并可恢复的持久化验收 | Codex |
| v1.1.16 | 2026-05-31 | 补充模型网关配置和调用元数据日志写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.17 | 2026-05-31 | 补充 GitLab MR 快照和 Code Review 报告写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.18 | 2026-05-31 | 补充模拟 Issue 回写写入 PostgreSQL `mock_issues` 结构表并可恢复的持久化验收 | Codex |
| v1.1.19 | 2026-05-31 | 补充相关系统写入 PostgreSQL `related_systems` 结构表并可恢复的持久化验收 | Codex |
| v1.1.20 | 2026-05-31 | 补充角色业务映射、可见入口、限制边界和知识索引失败重试验收 | Codex |
| v1.1.21 | 2026-06-01 | 补充生命周期从审计主体、Review、报告、模拟 Issue 和知识沉淀起点追踪验收 | Codex |
| v1.1.22 | 2026-06-01 | 补充知识检索不得为缺失 chunk 的 indexed 文档合成兜底结果的验收 | Codex |
| v1.1.23 | 2026-06-01 | 补充 GitLab MR 相同 diff 快照复用和审计验收 | Codex |
| v1.1.24 | 2026-06-01 | 补充迭代规划建议基于真实反馈/Bug 证据生成、确认和可选转需求的自动化验收 | Codex |
| v1.1.25 | 2026-06-01 | 补充用户使用指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.26 | 2026-06-01 | 补充 GitLab 每日代码指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.27 | 2026-06-01 | 补充 Jenkins 发布记录真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.28 | 2026-06-01 | 补充线上运行日志指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.29 | 2026-06-01 | 补充开发计划和自动化测试任务从已确认技术方案创建、人工确认和 AI 自动测试 Bug 入库验收 | Codex |
| v1.1.30 | 2026-06-01 | 补充发布评估和上线后分析任务从已确认上游任务创建、人工确认和 AI 上线后 Bug 入库验收 | Codex |
| v1.1.31 | 2026-06-01 | 补充首页 IT 团队看板产品筛选页面验收和前端服务查询参数验收 | Codex |
| v1.1.32 | 2026-06-01 | 补充首页 IT 团队看板按产品过滤知识文档和审计事件验收 | Codex |
| v1.1.33 | 2026-06-02 | 补充 Bug 管理工作台复现步骤、证据 JSON、重复归并和来源只读展示自动化验收 | Codex |
| v1.1.34 | 2026-06-02 | 对账 MVP 详细测试用例状态，将已有自动化覆盖的待测试项标为已覆盖，并保留生产就绪和 v1.2 待验范围 | Codex |
| v1.1.35 | 2026-06-02 | 补充首页 IT 团队看板 Bug、DevOps、线上日志、用户洞察和迭代规划聚合及产品/时间范围下钻验收 | Codex |
| v1.1.36 | 2026-06-02 | 补充生命周期 v1.2 真实证据主体、风险信号和动态缺失上下文自动化验收 | Codex |
| v1.1.37 | 2026-06-02 | 补充采集运行记录 API、持久化、审计和研发运营页面自动化验收 | Codex |
| v1.1.38 | 2026-06-02 | 补充待归属数据队列登记、归属/忽略、持久化、审计和前端页面自动化验收 | Codex |
| v1.1.39 | 2026-06-02 | 补充 AI 任务启动由真实 LangGraph StateGraph 驱动并持久化 runtime/node_path 的验收 | Codex |
| v1.1.40 | 2026-06-02 | 补充 GBrain 长期记忆连接器配置状态和密钥脱敏验收 | Codex |
| v1.1.41 | 2026-06-02 | 补充 GitHub provider、GitHub PR 预览和 diff 快照验收 | Codex |
| v1.1.42 | 2026-06-02 | 补充 AI 助手聊天工作台和系统进展问答验收 | Codex |
| v1.1.43 | 2026-06-03 | 记录 AI 助手真实需求全链路复跑结果，并补充 GitHub PR 列表、健康检查和失败任务重试验收 | Codex |
| v1.1.44 | 2026-06-03 | 记录 AI Brain GitHub PR 复跑卡点，补充 code-review 外部命令缺失时复用模型网关、携带 Review 上下文并规范化输出的回归验收 | Codex |
| v1.1.45 | 2026-06-03 | 补充 Embedding 不可用时文本索引兜底和补向量索引验收 | Codex |
| v1.1.46 | 2026-06-03 | 补充 Chat-only 模型网关、单独 Embedding 连接和向量兼容过滤验收 | Codex |
| v1.1.47 | 2026-06-03 | 补充新增需求可不指定迭代版本、需求池排期和需求交付/迭代版本页面验收 | Codex |

---

## 测试用例规范

### 用例编号规则

```text
TC-AIBRAIN-{模块}-{类型}-{序号}

模块:
- PRODUCT: 产品主数据
- REQUIREMENT: 需求管理
- TASK: AI 任务和任务类型
- GRAPH: LangGraph 工作流
- REVIEW: 人工确认
- KNOWLEDGE: 知识检索与沉淀
- OUTPUT: 模拟回写和导出
- AUDIT: 审计
- AUTH: 认证与角色
- DEPLOY: 部署
- CONFIG: 产品、相关系统和模型网关配置
- FLOW: 端到端业务流程和软件研发全流程感知
- DEVOPS: GitLab 代码质量和 Jenkins 发布数据
- OPS: 线上运行日志和运营状态
- BUG: Bug 管理
- DASHBOARD: 首页 IT 团队看板
- PLANNING: 用户使用洞察、用户反馈和 AI 迭代规划
- ATTRIBUTION: 待归属数据队列
- ASSISTANT: AI 助手和系统问答

类型:
- FUNC: 功能测试
- BOUND: 边界测试
- ERR: 异常测试
- API: 接口测试
- PERF: 性能测试
```

### 用例优先级

测试优先级必须和发布阶段一起解读，避免 v1.2 的 P1 用例阻塞 v1 MVP 发布。

| 字段 | 说明 |
|------|------|
| 适用阶段 | MVP-A、MVP-B、MVP-C、v1.1、v1.2 或 MVP 空状态。 |
| 阶段内优先级 | 当前适用阶段内的 P0/P1/P2/P3。 |

| 阶段内优先级 | 说明 | 通过要求 |
|--------------|------|----------|
| P0 | 当前阶段核心闭环，阻塞该阶段发布 | 当前阶段必须 100% 通过 |
| P1 | 当前阶段重要能力，影响演示和验收 | 当前阶段必须 100% 通过 |
| P2 | 当前阶段一般能力，影响体验 | 当前阶段 ≥ 95% 通过 |
| P3 | 当前阶段边缘场景 | 当前阶段 ≥ 90% 通过 |

---

## MVP 验收切片

v1 MVP 测试按 MVP-A/B/C 三个切片分批执行；三个切片全部通过后才视为 v1 MVP 完整通过。

| 切片 | 阻塞用例 | 验收重点 |
|------|----------|----------|
| MVP-A 基础 + Git 输入闭环 | TC-AIBRAIN-TASK-FUNC-001、TC-AIBRAIN-GRAPH-FUNC-002、TC-AIBRAIN-REVIEW-FUNC-003 中产品详细设计/技术方案部分、TC-AIBRAIN-OUTPUT-FUNC-004A、TC-AIBRAIN-DEPLOY-FUNC-007、TC-AIBRAIN-CONFIG-API-008、TC-AIBRAIN-REQ-FUNC-011、TC-AIBRAIN-REVIEW-FUNC-023A | 需求审批、产品详细设计、技术方案、人工确认、Markdown 导出、基础审计、GitLab/GitHub 只读绑定、MR/PR 预览和 diff 快照可跑通。 |
| MVP-B Git Review 闭环 | TC-AIBRAIN-REVIEW-FUNC-023B、TC-AIBRAIN-REVIEW-API-023C、TC-AIBRAIN-REVIEW-FUNC-003 中 code_review 部分、TC-AIBRAIN-AUDIT-API-006、TC-AIBRAIN-AUDIT-API-013 | 基于 MVP-A 的 MR/PR 快照生成 code_review 报告、人工确认、内部归档和结构表恢复可跑通，且不回写 GitLab/GitHub。 |
| MVP-C 知识与治理闭环 | TC-AIBRAIN-KNOWLEDGE-FUNC-005、TC-AIBRAIN-OUTPUT-FUNC-004B、TC-AIBRAIN-OUTPUT-API-004D、TC-AIBRAIN-OUTPUT-FUNC-004C、TC-AIBRAIN-FLOW-FUNC-010、TC-AIBRAIN-KNOWLEDGE-FUNC-012 | 知识导入、权限过滤检索、知识沉淀审核、模拟 Issue、模拟 Issue 结构表恢复、真实空状态入口和主体级治理可跑通。 |

### 模块：AI 任务与工作流闭环

| 用例编号 | 用例名称 | 优先级 | 适用阶段 | 前置条件 | 测试步骤 | 预期结果 | 自动化 |
|----------|----------|--------|----------|----------|----------|----------|--------|
| TC-AIBRAIN-TASK-FUNC-001 | 创建并启动产品详细设计 AI 任务 | P0 | MVP | 用户已登录，存在 `rd_brain`、已排期需求和未归档迭代版本 | 1. 创建 product_detail_design 任务 2. 启动任务 3. 查询详情 | 任务从 draft 进入 waiting_review，并返回 review_id 和 task_type | 是 |
| TC-AIBRAIN-TASK-API-001B | AI 任务 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在已排期需求 | 1. 从需求生成产品详细设计任务 2. 查询 PostgreSQL `ai_tasks` 表 3. 启动或取消任务使状态变化 4. 重启 API 后重新查询任务列表 | `ai_tasks` 保存默认 `rd_brain` 归属、任务类型、标题、状态、需求快照、产品上下文、输入输出、当前步骤和创建人；API 重启后仍能从结构表恢复任务和 `task` 计数器，Review/Graph 运行态由对应结构表恢复并回填任务关联 | 是 |
| TC-AIBRAIN-GRAPH-FUNC-002 | 信息不足时中断并补充后恢复 | P0 | MVP | 模型返回信息不足判断 | 1. 启动任务 2. 触发 waiting_more_info 3. 提交 answers 4. 再次 start | 任务回到 draft 后再次启动，继续运行到下一节点 | 是 |
| TC-AIBRAIN-GRAPH-API-002B | 人工确认和 Graph 运行态 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在 draft AI 任务 | 1. 启动任务进入 waiting_review 2. 查询 `human_reviews`、`graph_runs`、`graph_checkpoints` 表 3. 审批 Review 4. 重启 API 后查询任务详情、pending reviews 和 graph runs | Review 内容、版本、状态、Graph Run 状态、`runtime=langgraph`、`node_path`、checkpoint 和 state_snapshot 写入结构表；审批后 Review 与 Graph Run 状态同步更新；API 重启后任务详情仍能恢复 review_ids、graph_run_ids、checkpoint_id、runtime 和节点路径 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-003 | MVP 产品详细设计、技术方案和 Git Review 人工确认门禁 | P0 | MVP | 任务运行到产品详细设计、技术方案或 code_review 报告确认点 | 1. 查询 pending review 2. 不确认并观察后续阶段 3. approve 4. 查询任务 | 未确认前不进入下一阶段或归档，确认后恢复 graph | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004A | MVP-A Markdown 导出 | P0 | MVP-A | 产品详细设计或技术方案已确认 | 1. GET Markdown 导出接口 2. 检查内容 3. 使用无任务读权限角色重试 | 返回 `text/markdown` 方案内容，并可关联 trace_id；无任务读权限角色返回 403 | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004B | MVP-C 模拟 Issue 幂等生成 | P0 | MVP-C | 任务已确认并进入输出阶段 | 1. GET 查询未写回状态 2. POST 显式生成回写 3. 重复 POST 4. GET 查询结果 | 生成 mock issues，重复触发不产生重复结果，GET 不产生写副作用 | 是 |
| TC-AIBRAIN-OUTPUT-API-004D | 模拟 Issue 回写 PostgreSQL 结构表持久化 | P1 | MVP-C | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在已完成 AI 任务 | 1. POST `/api/writeback/results/{task_id}` 生成模拟 Issue 2. 查询 PostgreSQL `mock_issues` 表 3. 重启 API 后 GET 同一任务回写结果 4. 查询生命周期上下文 | `mock_issues` 保存 source_task_id、title、status、idempotency_key 和 payload；API 重启后仍能按幂等键恢复结果、`mock_issue` 计数器和生命周期关系，旧快照中引用缺失任务的回写不会重新入结构表 | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004C | MVP-C 知识沉淀候选审核 | P0 | MVP-C | 任务已产生可沉淀内容 | 1. 查询知识候选 2. 批准或拒绝 | 返回 pending deposits，审核后状态正确流转 | 是 |
| TC-AIBRAIN-KNOWLEDGE-FUNC-005 | 知识检索权限过滤和来源引用 | P0 | MVP | 存在不同权限文档 | 1. 以用户 A 检索 2. 以用户 B 检索 | 仅返回有权限文档，结果包含来源字段 | 是 |
| TC-AIBRAIN-AUDIT-API-006 | 写操作和 AI 关键动作产生审计事件 | P1 | MVP | 已执行任务闭环 | 1. 查询 audit events 2. 按 ai_task_id 过滤 | 创建、启动、确认、回写均有审计记录 | 是 |
| TC-AIBRAIN-DEPLOY-FUNC-007 | Docker Compose 本地栈健康检查 | P1 | 生产就绪 | Docker 可用 | 1. 启动 compose 2. 请求 /health 3. 检查 postgres/redis | web/api/db/redis 服务正常，生产就绪门禁可验证 | 脚本已提供；目标环境待通过 |
| TC-AIBRAIN-CONFIG-API-008 | 产品、迭代版本、模块和 Git 资源配置 | P1 | MVP | admin 已登录 | 1. 进入产品管理配置弹窗和需求交付/迭代版本页面 2. 创建/更新配置 3. 查询 active_only 列表 | 配置可维护，任务可引用产品迭代版本上下文；Git 凭据不在页面或 API 响应中明文展示 | 是 |
| TC-AIBRAIN-CONFIG-API-008B | 产品配置 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动 | 1. 创建产品、版本、模块、Git 资源和相关系统 2. 查询 PostgreSQL 对应结构表 3. 重启 API 后重新查询接口 | `products`、`product_versions`、`product_modules`、`product_git_repositories`、`related_systems` 有对应记录；API 重启后仍能从结构表恢复产品配置和 `system` 计数器 | 是 |
| TC-AIBRAIN-CONFIG-API-009 | 平台模型网关配置 | P1 | MVP | admin 已登录 | 1. 进入系统管理/模型网关 2. 创建默认模型配置 3. 查询列表 | 页面和 API 只返回 `api_key_configured`，不泄露明文 API Key | 是 |
| TC-AIBRAIN-CONFIG-API-009B | 模型网关 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动 | 1. 创建默认 OpenAI-compatible 模型网关配置 2. 启动 AI 任务产生模型调用日志 3. 查询 PostgreSQL `model_gateway_configs` 和 `model_gateway_logs` 表 4. 重启 API 后查询模型网关列表和模型日志 | 配置、默认标记、密钥配置状态、模型、超时、重试和调用元数据写入结构表；API 响应不泄露 API Key；API 重启后仍能恢复默认配置、日志列表和 `model_gateway_config`/`model_log` 计数器 | 是 |
| TC-AIBRAIN-ASSISTANT-FUNC-027 | AI 助手系统问答 | P1 | MVP | 已配置 active/default Chat 模型网关，系统存在产品、需求、AI 任务或 Git 配置 | 1. 进入 AI 助手 2. 询问 AI Brain 项目进展 3. 查询模型调用日志 | 助手基于服务端系统上下文回答产品、任务、Git 仓库和模型网关状态；日志仅记录 `purpose=assistant_chat` 元数据，不保存完整问题或回答 | 是 |
| TC-AIBRAIN-FLOW-FUNC-010 | MVP 业务主体独立入口和真实空状态可用 | P0 | MVP | 用户已登录且具备相应角色，至少存在产品、需求、AI 任务和知识文档基础数据 | 1. 进入首页 IT 团队看板 2. 进入产品管理 3. 进入需求管理 4. 进入任务中心 5. 进入 Bug 管理 6. 进入研发运营看板 7. 进入用户洞察/迭代规划 8. 进入知识中心 9. 进入审计与运行 | MVP 必交主体可独立查看或维护；未接入真实采集器的入口展示空状态或禁用态，不返回示例数据、占位统计或伪造结果 | 是 |
| TC-AIBRAIN-REQ-FUNC-011 | 需求审批与任务执行解耦 | P0 | MVP | 存在已批准需求 | 1. 生成 AI 任务 2. 修改产品配置 3. 查询任务详情 | 需求保留审批状态，任务保留生成时 requirement_snapshot 和 product_context | 是 |
| TC-AIBRAIN-REQ-API-011B | 需求台账 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动且存在产品，可选存在迭代版本 | 1. 创建未排期需求 2. 审批、排期或生成任务使需求状态变化 3. 查询 PostgreSQL `requirements` 表 4. 重启 API 后重新查询需求列表 | 需求标题、内容、产品、可选版本、状态、审批备注和 `task_ids` 写入 `requirements`；API 重启后仍能从结构表恢复需求和 `requirement` 计数器 | 是 |
| TC-AIBRAIN-REQ-FUNC-011C | 新增需求可不指定迭代版本并后续排期 | P0 | MVP | 用户已登录，存在启用产品和未归档迭代版本 | 1. 新增需求不选择版本 2. 审批需求 3. 未排期时生成任务 4. 补充迭代版本 5. 再生成任务 | 新需求为 `submitted`，审批后未排期为 `approved`，未排期生成任务返回状态错误；补充版本后为 `planned` 并可生成产品详细设计任务，需求进入 `designing` | 是 |
| TC-AIBRAIN-KNOWLEDGE-FUNC-012 | 知识中心独立运营 | P0 | MVP | 知识维护者已登录 | 1. 导入文档 2. 查看索引状态 3. 检索 4. 审核沉淀 | 知识中心可独立导入、索引、检索、审核和处理失败 | 是 |
| TC-AIBRAIN-AUDIT-API-013 | 主体级审计查询 | P1 | MVP | 已产生产品、需求、任务、知识操作 | 1. 按 subject_type 查询 2. 按 subject_id 查询 3. 按 actor_id 和 created_from/created_to 查询 4. 在审计列表打开详情和链路追踪 | 返回对应主体、操作者和时间范围内的关键写操作；页面弹窗展示审计载荷和生命周期上下文 | 是 |
| TC-AIBRAIN-KNOWLEDGE-API-013B | 知识与审计 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在知识维护者和至少一个可沉淀任务 | 1. 创建/更新/删除知识文档 2. 审核知识沉淀候选 3. 查询 PostgreSQL `knowledge_documents`、`knowledge_deposits`、`audit_events` 表 4. 重启 API 后重新查询知识中心和审计列表 | 知识文档、权限角色、标签、索引状态、沉淀状态、关联入库文档、驳回原因和审计事件写入结构表；`audit_events.id` 支持字符串 ID，`sequence` 可恢复审计计数器；API 重启后知识和审计不依赖快照兜底数据 | 是 |
| TC-AIBRAIN-KNOWLEDGE-API-013C | GBrain 长期记忆连接器状态 | P1 | MVP-C | 用户已登录 | 1. 未配置 `GBRAIN_BASE_URL` / `GBRAIN_API_KEY` 时查询 `/api/long-memory/status` 2. 配置两项后重启 API 并再次查询 | 未配置时返回 `status=not_configured`、`fallback_retriever=postgres_pgvector` 和空能力列表；配置后返回 `configured` 和能力列表；响应不包含 GBrain URL、API Key 或密钥片段 | 是 |
| TC-AIBRAIN-AUTH-API-024 | MVP 角色目录和用户管理角色选择 | P1 | MVP | admin 已登录 | 1. 调用 `/api/auth/roles` 2. 进入系统管理/用户管理并打开角色目录 3. 新增用户时打开角色字段 4. 进入知识中心导入文档并打开权限角色字段 5. 尝试提交未定义角色 | 接口返回 6 个明确角色、业务角色映射、职责、数据范围、决策范围、可见入口、限制边界、权限点和排序；用户管理和知识权限配置均从接口加载固定多选；后端拒绝目录外角色并返回 `VALIDATION_ERROR`；`role_definitions` 迁移脚本可重复执行 | 是 |
| TC-AIBRAIN-DEVOPS-FUNC-014 | GitLab 代码质量与提交统计 | P1 | v1.2 | 产品已绑定 GitLab Git 资源 | 1. 采集每日提交 2. 采集代码质量 3. 按产品和人员查询 | 返回按产品、仓库、人员聚合的提交情况和质量结果 | 是 |
| TC-AIBRAIN-OPS-FUNC-015 | 线上运行日志运营分析 | P1 | v1.1 / v1.2 | 产品和模块已存在；可手工导入真实聚合指标 | 1. 登记线上日志指标 2. 按产品、模块、环境、时间窗口查询 3. 校验错误率和审计 | 返回按产品、模块、环境、时间窗口的运营状态指标，并写入审计和结构表 | 是 |
| TC-AIBRAIN-RELEASE-FUNC-016 | Jenkins 发布数据登记与查询 | P1 | v1.1 / v1.2 | 产品和版本已存在 | 1. 登记发布记录 2. 查询产品发布历史 | 返回构建状态、部署环境、失败原因并写入审计和结构表 | 是 |
| TC-AIBRAIN-DEVOPS-FUNC-023 | 采集运行记录登记与更新 | P1 | v1.2 | 产品已存在；需要追踪 DevOps 或用户洞察采集尝试 | 1. 查询空运行列表 2. 登记运行 3. 标记成功/失败/取消 4. 检查审计和持久化 5. 在研发运营页面登记和结束运行 | 返回真实运行台账；终态不可回退；failed 必须有错误说明；不自动生成指标数据 | 是 |
| TC-AIBRAIN-ATTRIBUTION-FUNC-024 | 待归属数据队列登记与处理 | P1 | v1.2 | 产品已存在；存在无法映射产品/模块/需求的采集或导入样本 | 1. 查询空队列 2. 登记待归属项 3. 归属到产品上下文 4. 忽略噪声 5. 检查审计和持久化 6. 在 DevOps/Insights 页面查看和处理 | 返回真实队列；pending/resolved/ignored 状态正确；终态不可重复处理；不自动生成指标或反馈数据 | 是 |
| TC-AIBRAIN-DASHBOARD-FUNC-017 | 首页 IT 团队看板 MVP 聚合与 v1.2 完整下钻 | P1 | MVP / v1.2 | MVP 至少存在产品、需求、AI 任务、知识和审计数据；v1.2 另存在 Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议数据 | 1. 打开首页 2. 按产品筛选 3. 下钻明细 | MVP 展示真实需求、研发进展、知识沉淀和审计摘要；v1.2 扩展 Bug、线上系统健康、核心业务运行、用户使用趋势、用户反馈趋势、AI 迭代规划建议摘要和发布状态 | 是 |
| TC-AIBRAIN-BUG-FUNC-018 | v1.1 Bug 管理基础闭环 | P1 | v1.1 | 存在 AI 自动测试和人工测试输入 | 1. AI 自动测试登记 Bug 2. 人工登记 Bug 3. 分派修复 4. 验证关闭 | Bug 按产品归属，来源正确，状态完整流转；重复 Bug 不进入开放队列；写操作产生审计事件 | 是 |
| TC-AIBRAIN-BUG-API-018B | Bug 管理 PostgreSQL 结构表持久化 | P1 | v1.1 | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在产品、版本和模块 | 1. 创建 Bug 2. 修改状态、负责人、复现步骤和证据 3. 合并重复 Bug 4. 查询 PostgreSQL `bugs` 表 5. 重启 API 后重新查询 Bug 列表 | `bugs` 保存产品、版本、模块、来源、严重级别、状态、负责人、关联任务/需求、复现步骤、证据和重复归并关系；API 重启后仍能从结构表恢复 Bug 列表和 `bug` 计数器 | 是 |
| TC-AIBRAIN-TASK-FUNC-020 | 研发全链路 AI 任务类型覆盖 | P1 | v1.1 / v1.2 | 已存在产品、已排期需求、已确认产品详细设计、已确认技术方案、已确认发布评估、代码 diff、测试结果、Jenkins 发布记录和线上日志样本 | 1. 创建当前已实现 task_type 任务 2. 启动并查询详情 3. 检查输出结构和 input_json 真实上下文快照 | 每类任务均保留 task_type、产品上下文、人工确认点和对应输出结构；自动化覆盖 development_planning、automated_testing、release_readiness 与 post_release_analysis | 是 |
| TC-AIBRAIN-REVIEW-FUNC-019 | v1.1 研发扩展任务人工确认门禁 | P1 | v1.1 | 开发计划或自动化测试任务运行到确认点 | 1. 查询 pending review 2. 不确认并观察后续阶段 3. approve 4. 查询任务和 Bug 列表 | 开发计划和自动化测试结论未确认前不进入下一阶段或回写；自动化测试确认后生成 `ai_auto_test` Bug | 是 |
| TC-AIBRAIN-REVIEW-FUNC-023A | MVP-A GitLab MR / GitHub PR 预览和 diff 快照 | P0 | MVP-A | 产品已绑定 GitLab 或 GitHub 代码库，存在已排期需求、已确认技术方案和可访问 MR/PR | 1. 预览 MR/PR 2. 拉取 diff 快照 3. 查询快照摘要 | 返回变更元信息、snapshot_id、diff_size_bytes、diff_limit 和 created_at；快照不受后续远端变更静默影响 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-023B | MVP-B GitLab MR / GitHub PR Code Review 报告闭环 | P0 | MVP-B | 已存在 MVP-A MR/PR diff 快照，code-review 执行器可用 | 1. 创建 code_review 任务 2. 启动任务 3. 生成 Review 报告 4. 人工确认 5. 查询远端变更和审计 | 报告只归档到 AI Brain，不回写 GitLab/GitHub 评论、审批状态或分支变更 | 是 |
| TC-AIBRAIN-REVIEW-API-023C | GitLab MR / GitHub PR 快照和 Code Review 报告 PostgreSQL 结构表持久化 | P1 | MVP-B | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，已完成技术方案并存在 MR/PR 快照 | 1. 生成 MR/PR diff 快照 2. 创建并启动 code_review 任务生成报告 3. 查询 PostgreSQL `gitlab_mr_snapshots` 和 `code_review_reports` 表 4. 重启 API 后查询任务详情、生命周期上下文和报告接口 | 兼容快照和 Review 报告写入结构表；报告保留 task_id、snapshot_id、executor、risk_level、findings、review_id、归档状态和不回写标记；API 重启后能恢复 `snapshot`/`report` 计数器并回填任务 `code_review_report_id` | 是 |
| TC-AIBRAIN-REVIEW-FUNC-024 | v1.2 发布和上线后分析人工确认门禁 | P1 | v1.2 | 发布上线评估或上线后分析任务运行到确认点 | 1. 查询 pending review 2. 不确认并观察后续处理 3. approve 或 edited_approve 4. 查询结果和 `ai_post_release` Bug | 发布建议、风险处理、知识沉淀和上线后 Bug 入库必须等待人工确认 | 是 |
| TC-AIBRAIN-FLOW-FUNC-021 | 软件研发全流程感知 | P1 | MVP / v1.2 | 存在 MVP 关联数据；v1.2 完整追溯测试另需提交、Review、测试、Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议关联数据 | 1. 以需求查询 MVP 感知视图 2. 查看上下游 3. 查看风险信号 4. 从人工确认、Code Review 报告、模拟 Issue、知识沉淀和审计事件起点查询 5. 用 v1.2 数据下钻到关联主体 | MVP 至少返回需求到产品详细设计、技术方案、代码 Review、人工确认、模拟 Issue、知识沉淀和审计事件，并且从 MVP 证据主体回到对应任务链路；v1.2 返回完整上下文链路、风险来源、影响范围和下一步建议 | 是 |
| TC-AIBRAIN-PLANNING-FUNC-022 | 用户洞察与 AI 迭代规划 | P1 | MVP / v1.2 | 存在产品规划、需求池、用户反馈、Bug；v1.2 另存在用户使用数据、线上日志、发布记录和研发投入样本 | 1. 聚合使用指标 2. 收集用户反馈 3. 生成迭代规划建议 4. 检查未自动创建正式需求/变更路线图 5. 产品负责人确认后转需求 | MVP 基于真实用户反馈和 Bug 返回可追溯的迭代建议；AI 未经确认不自动创建正式需求或调整路线图/排期；v1.2 扩展用户使用、线上日志和发布证据 | 是 |

---

## 详细测试用例

### TC-AIBRAIN-TASK-FUNC-001: 创建并启动产品详细设计 AI 任务

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-001 |
| 用例名称 | 创建并启动产品详细设计 AI 任务 |
| 优先级 | P0 |
| 模块 | TASK |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 用户已通过本地账号登录并持有 Bearer Token。
2. 系统存在启用状态的 `rd_brain`。
3. 系统存在启用产品、未归档迭代版本和状态为 `planned` 的已排期需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/ai-tasks` 创建任务 | 返回 `data.id`，状态为 `draft`。 |
| 2 | POST `/api/ai-tasks/{id}/start` | 返回 `review_id`，任务进入 `waiting_review`，或模型失败时进入 `failed` 并记录错误码。 |
| 3 | 对 `current_step=model_gateway_failed` 的失败任务再次 POST `/api/ai-tasks/{id}/start` | 使用同一 task_id 重试模型调用；成功时进入 `waiting_review`，审计包含 `ai_task.retry_started`。 |
| 4 | GET `/api/ai-tasks/{id}` | 返回任务详情、当前状态和 trace_id。 |

**测试数据**:
```json
{
  "brain_app_code": "rd_brain",
  "task_type": "product_detail_design",
  "title": "支持 Markdown 知识导入",
  "input": {
    "background": "知识散落在 Markdown 中",
    "goal": "导入后可检索引用",
    "product_id": "product_001",
    "version_id": "version_001",
    "module_codes": ["knowledge"]
  }
}
```

**预期结果**:
1. API 响应使用 `{data, trace_id}` envelope。
2. 创建和启动操作均写入审计事件。
3. 任务详情返回 `task_type = product_detail_design`。

**状态**: 已自动化覆盖。后端证据见 `apps/api/tests/test_mvp_a_flow.py::test_requirement_to_product_detail_design_human_review_flow`、`apps/api/tests/test_graph_runtime.py::test_ai_task_graph_is_compiled_by_langgraph`、`apps/api/tests/test_graph_runtime.py::test_starting_task_creates_graph_run_checkpoint_and_task_detail_projection`；模型网关失败和同任务重试路径见 `apps/api/tests/test_model_gateway.py`。

---

### TC-AIBRAIN-GRAPH-FUNC-002: 信息不足时中断并补充后恢复

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-GRAPH-FUNC-002 |
| 用例名称 | 信息不足时中断并补充后恢复 |
| 优先级 | P0 |
| 模块 | GRAPH |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. AI 任务已启动。
2. 测试模型或夹具可让 `is_information_enough` 返回不足。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 等待任务运行到信息评估节点 | 任务状态变为 `waiting_more_info`。 |
| 2 | GET 任务详情 | 返回 clarifying questions。 |
| 3 | POST `/api/ai-tasks/{id}/more-info` | 任务回到 `draft`，补充信息写入 input。 |
| 4 | POST `/api/ai-tasks/{id}/start` | 任务继续运行到下一确认点或完成。 |
| 5 | 在任务管理待确认弹窗点击“要求补充”，再在任务操作弹窗提交补充说明 | 页面分别调用真实 `/api/reviews/{id}/request-more-info` 和 `/api/ai-tasks/{id}/more-info`，任务状态从 `waiting_more_info` 回到 `draft`。 |

**测试数据**:
```json
{
  "answers": [
    {
      "question_id": "q_001",
      "answer": "v1 仅支持 Markdown 文档导入。"
    }
  ]
}
```

**预期结果**:
1. 中断前后 Graph State 不丢失。
2. 补充信息作为审计事件记录。

**状态**: 已自动化覆盖。后端状态流转见 `apps/api/tests/test_review_actions.py::test_reject_and_request_more_info_move_task_to_documented_states`，前端任务弹窗补充信息链路见 `apps/web/tests/App.test.tsx::requests and submits more information from task management dialogs`。

---

### TC-AIBRAIN-REVIEW-FUNC-003: MVP 产品详细设计和技术方案人工确认门禁

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-003 |
| 用例名称 | MVP 产品详细设计和技术方案人工确认门禁 |
| 优先级 | P0 |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 任务已运行到任一 review 阶段。
2. 当前用户具备确认权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/ai-tasks/{id}` | 返回 pending review。 |
| 2 | 不提交确认并等待 | 后续阶段不会执行。 |
| 3 | POST `/api/reviews/{id}/approve` | review 状态变为 `approved`。 |
| 4 | 查询任务详情 | 任务恢复 running 或进入下一确认阶段。 |

**测试数据**:
```json
{
  "version": 1,
  "comment": "确认通过"
}
```

**预期结果**:
1. 产品详细设计和技术方案等 MVP 高影响 AI 产出均有人工确认点。
2. version 不匹配时返回 `REVIEW_VERSION_CONFLICT`。

**状态**: 已自动化覆盖。产品详细设计、技术方案和 Code Review 人工确认门禁分别见 `apps/api/tests/test_mvp_a_flow.py`、`apps/api/tests/test_technical_solution_export.py`、`apps/api/tests/test_code_review_report.py` 与 `apps/web/tests/App.test.tsx` 任务操作弹窗用例。

---

### TC-AIBRAIN-OUTPUT-FUNC-004A/B/C: Markdown、模拟 Issue 和知识候选

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-OUTPUT-FUNC-004A / 004B / 004C |
| 用例名称 | Markdown 导出、模拟 Issue 幂等生成和知识沉淀候选审核 |
| 阶段内优先级 | P0 |
| 模块 | OUTPUT |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 产品详细设计、技术方案或代码 Review 报告已确认。
2. Graph 运行到导出、模拟回写或知识沉淀候选生成阶段。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | MVP-A: GET `/api/export/tasks/{task_id}/markdown` | 返回 `text/markdown` 方案内容，并通过 Header 或日志关联 `trace_id`。 |
| 2 | MVP-C: 在任务中心打开已完成任务的“模拟 Issue”弹窗，GET `/api/writeback/results/{task_id}` | 未写回时页面展示 `not_written`/未写回、幂等键和空 issues，不创建 mock issue。 |
| 3 | MVP-C: 在弹窗中点击生成，POST `/api/writeback/results/{task_id}` | 页面展示模拟 Issue、`completed`/已生成和 idempotency_key。 |
| 4 | MVP-C: 重复 POST 模拟输出 | 不产生重复 mock issue。 |
| 5 | MVP-C: 在知识中心打开“沉淀审核”弹窗查询知识沉淀候选 | 返回 pending deposits。 |
| 6 | MVP-C: 批准或拒绝知识沉淀候选 | 候选状态正确流转，未批准内容不进入正式知识库。 |

**预期结果**:
1. MVP-A 只阻塞 Markdown 导出。
2. MVP-C 阻塞模拟 Issue 幂等生成和知识沉淀候选审核。
3. mock_issues 幂等键唯一，knowledge_deposits 按 `ai_task_id + deposit_type + content_hash` 去重。

**状态**: 已自动化覆盖。Markdown 导出见 `apps/api/tests/test_technical_solution_export.py`；模拟 Issue 幂等和知识沉淀审核见 `apps/api/tests/test_knowledge_governance.py` 与 `apps/web/tests/App.test.tsx::sends MVP-C writeback and knowledge deposit mutations to backend APIs`。

---

### TC-AIBRAIN-KNOWLEDGE-FUNC-005: 知识检索权限过滤和来源引用

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-KNOWLEDGE-FUNC-005 |
| 用例名称 | 知识检索权限过滤和来源引用 |
| 优先级 | P0 |
| 模块 | KNOWLEDGE |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 知识库中存在公开文档和受限文档。
2. 用户 A 有受限文档权限，用户 B 无权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 用户 A POST `/api/knowledge/search` | 返回公开和授权受限 chunk。 |
| 2 | 用户 B 使用相同 query 检索 | 不返回无权限受限 chunk。 |
| 3 | 检查每条结果 | 包含文档 id、title、snippet、source 或等价来源字段。 |
| 4 | 将 indexed 文档的 chunk 行清空后再次检索 | 返回空结果，不用整篇文档合成 `*_chunk_001` 兜底来源。 |
| 5 | 在知识中心打开“知识检索”弹窗并输入同一 query | 页面调用真实 `/api/knowledge/search`，展示可访问结果标题、来源和内容摘要；无结果时展示空状态。 |

**测试数据**:
```json
{
  "brain_app_code": "rd_brain",
  "query": "需求评估规则",
  "filters": {},
  "top_k": 5
}
```

**预期结果**:
1. 权限过滤在数据库查询层完成。
2. AI 输出引用知识时可追溯到真实存在的 chunk 来源。
3. 索引状态与 chunk 行不一致时暴露真实空结果，不返回合成数据。

**状态**: 已自动化覆盖。权限过滤、来源引用、embedding 排序和无兜底结果见 `apps/api/tests/test_knowledge_governance.py`；前端检索弹窗见 `apps/web/tests/App.test.tsx::opens knowledge search and shows permission-filtered sources`。

---

### TC-AIBRAIN-AUDIT-API-006: 写操作和 AI 关键动作产生审计事件

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-AUDIT-API-006 |
| 用例名称 | 写操作和 AI 关键动作产生审计事件 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | AUDIT |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 用户已登录并具备创建需求、启动 AI 任务和处理人工确认的权限。
2. 系统已完成一次从需求审批到 AI 任务人工确认的最小闭环。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建需求并提交审批 | 写入 `requirement.created` 或等价审计事件。 |
| 2 | 审批需求并生成 AI 任务 | 写入 `requirement.approved` 和 `ai_task.created` 审计事件。 |
| 3 | 启动 AI 任务并进入人工确认 | 写入 `ai_task.started` 和 `review.created` 审计事件。 |
| 4 | approve 人工确认 | 写入 `review.submitted` 审计事件，包含 review_id、task_id 和 actor_id。 |
| 5 | GET `/api/audit/events?ai_task_id={task_id}` | 返回上述任务相关审计事件，按 created_at 倒序或稳定排序返回。 |

**预期结果**:
1. 创建、审批、启动、人工确认等写操作均可追踪。
2. 审计事件包含主体类型、主体 ID、操作者、事件类型和发生时间。
3. API 响应包含 `trace_id`，但审计表不要求持久化完整 `trace_id`。

**状态**: 已自动化覆盖。任务闭环审计见 `apps/api/tests/test_mvp_a_flow.py`，主体/操作者/时间过滤见 `apps/api/tests/test_security_boundaries.py::test_audit_events_filter_by_actor_and_time_range`，持久化写入见 `apps/api/tests/test_database_persistence.py`。

---

### TC-AIBRAIN-DEPLOY-FUNC-007: Docker Compose 本地栈与生产就绪门禁健康检查

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DEPLOY-FUNC-007 |
| 用例名称 | Docker Compose 本地栈与生产就绪门禁健康检查 |
| 优先级 | P1 |
| 适用阶段 | 生产就绪 |
| 模块 | DEPLOYMENT |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. Docker 可用。
2. `.env` 已配置本地运行所需变量。
3. PostgreSQL、Redis、模型网关配置和内部 GitLab 只读凭据引用均按部署 runbook 准备。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 运行 `docker compose config --quiet` | Compose 配置校验通过。 |
| 2 | 运行 `docker compose up -d --build` | web、api、postgres、redis 服务启动。 |
| 3 | GET `/health` | 返回 API、数据库、Redis、模型网关配置状态和 trace_id；存在持久化 active/default 模型网关且已配置密钥时返回 `model_gateway=configured`。 |
| 4 | 验证 PostgreSQL 扩展 | `pgvector` 和 `pgcrypto` 可用。 |
| 5 | 调用模型网关配置查询 | 只返回密钥掩码或 configured 标记，不返回明文。 |
| 6 | 调用 GitLab MR preview 和 snapshot | 只读链路可用，不产生 GitLab 评论、审批、request changes、合并或分支变更。 |

**预期结果**:
1. 本地栈健康检查通过。
2. 生产就绪门禁覆盖配置、凭据、数据库扩展和 GitLab 只读边界。
3. 任一门禁失败时不得宣称环境可发布。

**状态**: 已提供可执行生产就绪门禁脚本 `scripts/production_readiness_check.py`，脚本覆盖 Docker Compose、pgvector/pgcrypto、Redis、模型网关配置脱敏和 GitLab 只读 preview/snapshot；健康检查读取持久化默认模型网关配置的回归见 `apps/api/tests/test_foundation.py`；真实目标环境仍必须执行并通过脚本，不能以本地 API/Web 单元测试替代。

---

### TC-AIBRAIN-CONFIG-API-008: 产品、版本、模块和 Git 资源配置

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-CONFIG-API-008 |
| 用例名称 | 产品、迭代版本、模块和 Git 资源配置 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | PRODUCT_CONFIG |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. admin 用户已登录。
2. 系统已存在业务大脑 `rd_brain`。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/products` 创建产品 | 返回产品 ID，状态为 active。 |
| 2 | 在需求交付/迭代版本页面或 POST `/api/products/{product_id}/versions` 创建迭代版本 | 返回版本 ID，版本归属该产品。 |
| 3 | POST `/api/products/{product_id}/modules` 创建模块 | 返回模块 code，模块归属该产品。 |
| 4 | 在产品管理页面点击“配置”维护模块和 Git 资源，并进入需求交付/迭代版本页面维护版本 | 页面显示真实模块、Git 资源和迭代版本列表，新增后刷新真实 API 数据。 |
| 5 | POST `/api/products/{product_id}/git-repositories` 绑定内部 GitLab 只读资源 | 返回 repository_id 和 `credential_ref_configured`，不返回凭据引用或明文 token。 |
| 6 | GET `/api/products/{product_id}/versions?active_only=true` | 不返回 archived 版本。 |
| 7 | 使用 archived 版本排期需求或创建任务 | 返回 `PRODUCT_VERSION_ARCHIVED` 或 `VALIDATION_ERROR`。 |

**预期结果**:
1. 产品、迭代版本、模块、Git 资源可独立维护，迭代版本主入口位于需求交付菜单。
2. 新需求可暂不选择版本；排期和 AI 任务只能引用有效产品与未归档迭代版本。
3. 写操作产生审计事件。
4. 页面列表只显示 Git 凭据“已配置/未配置”状态，不回显 `credential_ref`。

**状态**: 自动化与 Docker 页面回归通过

---

### TC-AIBRAIN-CONFIG-API-009: 平台模型网关配置

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-CONFIG-API-009 |
| 用例名称 | 平台模型网关配置 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | MODEL_GATEWAY |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. admin 用户已登录。
2. 系统允许通过环境变量或密钥管理系统提供模型 API Key。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 进入系统管理 / 模型网关页面 | 展示模型网关配置管理列表，风格与其他管理列表一致。 |
| 2 | 在页面新增默认模型配置并填写 API Key | POST `/api/system/model-gateway-configs`，返回 config_id、provider、默认模型和 active 状态。 |
| 3 | GET `/api/system/model-gateway-configs` 或刷新页面 | 返回并展示 `api_key_configured=true`，不返回也不渲染明文 API Key、密钥前缀或后缀。 |
| 4 | 在页面编辑配置但 API Key 留空 | PATCH `/api/system/model-gateway-configs/{config_id}` 不携带 `api_key`，服务端保留现有密钥。 |
| 5 | PATCH `/api/system/model-gateway-configs/{config_id}` 禁用配置 | 配置变为 inactive，新任务不能选择该配置。 |
| 6 | 使用 active/default 且已配置 API Key 的 OpenAI-compatible 配置启动任务 | 后端调用 `{base_url}/chat/completions`，请求带 Bearer Token 和 `response_format={"type":"json_object"}`；任务输出使用 provider JSON，模型日志记录 provider/model/tokens/config_id/status，不记录 prompt、完整输出或 API Key。 |
| 7 | 使用缺失密钥或无效 provider 响应启动任务 | 返回 `MODEL_GATEWAY_CONFIG_INVALID` 或 `MODEL_GATEWAY_FAILED`，任务进入 `failed`，不静默完成或回退本地输出。 |

**预期结果**:
1. 系统管理下模型网关配置可维护。
2. 页面、API 响应和日志不泄露模型 API Key。
3. 配置变更、模型调用成功和模型调用失败均产生可追踪事件。

**状态**: 已自动化覆盖。配置 CRUD、密钥脱敏、provider 校验和模型日志见 `apps/api/tests/test_product_system_config.py`、`apps/api/tests/test_model_gateway.py` 与 `apps/api/tests/test_database_persistence.py`；前端配置表单见 `apps/web/tests/App.test.tsx::manages model gateway configs without exposing api keys`。

---

### TC-AIBRAIN-ASSISTANT-FUNC-027: AI 助手系统问答

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-ASSISTANT-FUNC-027 |
| 用例名称 | AI 助手系统问答 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | ASSISTANT |
| 创建人 | Codex |
| 创建日期 | 2026-06-02 |

**前置条件**:
1. 用户已登录，并具备 `admin`、`product_owner`、`rd_owner`、`reviewer` 或 `knowledge_owner` 角色。
2. 系统已配置 active/default OpenAI-compatible Chat 模型网关；该入口不要求 Embedding 可用。
3. 系统存在真实产品、需求、AI 任务、Git 仓库或模型网关配置数据。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 进入 `/assistant` AI 助手页面 | 页面展示快速问题、上下文标签、聊天消息区和输入框。 |
| 2 | 点击“项目进展”或输入“AI Brain 项目现在开发到哪里了？” | 前端调用 `POST /api/assistant/chat`，请求包含用户问题和可选 conversation_id/product_id。 |
| 3 | 服务端处理助手请求 | 服务端生成脱敏 `system_context`，包含产品、需求数量、AI 任务数量、最新需求/任务、Git 仓库和模型网关状态，并注入模型网关 Chat 请求。 |
| 4 | 模型返回回答 | API 返回 assistant 消息、suggestions、model、latency_ms 和 conversation_id，页面渲染回答和建议按钮。 |
| 5 | GET `/api/assistant/conversations` | 返回当前登录用户的最近对话，包含 conversation_id、标题、消息数和最后消息时间。 |
| 6 | GET `/api/assistant/conversations/{conversation_id}/messages` | 返回该会话的 user/assistant 消息；其他用户读取同一 conversation_id 返回 404。 |
| 7 | GET `/api/model-gateway/logs?purpose=assistant_chat` | 返回助手模型调用元数据，包含 provider、model、tokens、latency、status 和 config_id，不包含完整用户问题、系统上下文、助手回答或 API Key。 |
| 8 | 模型网关未配置或调用失败 | API 返回 `MODEL_GATEWAY_CONFIG_INVALID` 或 `ASSISTANT_CHAT_FAILED`，页面展示错误消息并保留用户输入上下文。 |

**预期结果**:
1. AI 助手可以回答 AI Brain 系统配置、产品、需求、任务、Git 仓库和项目开发进展相关问题。
2. 助手聊天只依赖 Chat 模型网关，不因上游不支持 Embedding 而阻断。
3. 聊天历史按用户保存并隔离，前端可展示最近对话并打开历史消息。
4. 模型日志和审计事件只记录脱敏元数据，不能保存完整 prompt、完整输出或密钥。

**状态**: 已自动化覆盖。后端系统上下文注入、模型日志脱敏和助手审计见 `apps/api/tests/test_assistant_chat.py`；前端聊天页面和服务请求映射见 `apps/web/tests/App.test.tsx`。

---

## 主体独立维护测试用例

### TC-AIBRAIN-FLOW-FUNC-010: MVP 业务主体独立入口和真实空状态可用

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-FLOW-FUNC-010 |
| 用例名称 | MVP 业务主体独立入口和真实空状态可用 |
| 优先级 | P0 |
| 模块 | FLOW |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 用户已登录。
2. 系统至少存在产品、需求、AI 任务、知识文档和审计基础数据；Bug 管理、用户反馈、用户使用指标和迭代规划建议可加载真实列表或真实空列表，研发运营看板在 MVP 可没有业务数据。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 进入首页 IT 团队看板 | MVP 可展示需求、研发进展、知识沉淀和审计摘要；尚未接入真实采集器的线上系统健康和发布能力展示空状态或禁用态；GitLab 每日指标、用户使用指标、用户反馈和迭代规划建议来自真实结构表，不返回示例数据或伪造统计。 |
| 2 | 进入产品管理 | 可以查看和维护产品、版本、模块和 Git 资源。 |
| 3 | 进入需求管理 | 可以查看需求列表、需求详情和审批状态。 |
| 4 | 进入任务中心 | 可以查看 AI 任务列表；任务类型展示业务中文标签；列表行内仅展示单一“操作”入口，启动产品详细设计任务、确认 Review 输出、从已确认产品详细设计创建技术方案任务、对已完成技术方案执行 Markdown 导出等动作均在上方摘要、下方纵向操作的任务操作弹窗中完成。 |
| 5 | 进入 Bug 管理 | v1.1 可展示真实 Bug 列表、权限校验和真实空列表；登记、分派、验证、关闭和重复归并按 TC-AIBRAIN-BUG-FUNC-018 验收。 |
| 6 | 进入研发运营看板 | MVP 可展示真实接口空状态；GitLab、Jenkins 与线上日志支持真实登记/导入和查询，外部自动采集和完整下钻按 v1.2 验收。 |
| 7 | 进入用户洞察/迭代规划 | MVP 可展示真实用户反馈、用户使用指标和迭代规划建议列表；无反馈/Bug 证据时生成建议返回真实空集合；无使用指标时返回真实空集合。 |
| 8 | 进入知识中心 | 可以查看知识文档、检索、索引状态和沉淀审核。 |
| 9 | 进入审计与运行 | 可以查看审计事件、运行记录、健康检查和失败排查信息。 |

**预期结果**:
1. 产品、需求、AI 任务、知识中心和审计与运行在 MVP 可独立查看或维护。
2. Bug 管理、用户反馈、用户使用指标和迭代规划建议使用真实 API 或真实空列表；研发运营看板等后续阶段入口在 MVP 不误导为已完成能力，不返回示例数据或占位统计。
3. 用户不需要进入 AI 任务详情页才能维护产品、需求、知识或查看审计运行信息。

**状态**: 已自动化覆盖。管理入口、真实空状态和无本地示例行见 `apps/web/tests/App.test.tsx::renders management modules as query filters with table lists`、`apps/web/tests/App.test.tsx::renders dashboard and operation pages without placeholder data`、`apps/web/tests/App.test.tsx::shows backend load failures without local example rows`；外部采集器完整闭环仍按后续用例推进。

---

### TC-AIBRAIN-REQ-FUNC-011: 需求审批与任务执行解耦

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011 |
| 用例名称 | 需求审批与任务执行解耦 |
| 优先级 | P0 |
| 模块 | REQUIREMENT |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 存在启用产品和未归档迭代版本。
2. 存在状态为 `planned` 的已排期需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/requirements/{id}/generate-task` | 返回 task_id，需求状态变为 `designing`。 |
| 2 | PATCH 产品、版本或模块名称 | 产品配置更新成功。 |
| 3 | GET `/api/ai-tasks/{task_id}` | 返回生成时的 `requirement_snapshot` 和 `product_context`，不被后续配置修改覆盖。 |
| 4 | GET `/api/requirements/{id}` | 需求仍保留原始输入、审批结论和任务引用。 |

**预期结果**:
1. 需求是业务审批对象，任务是 AI 执行对象。
2. 历史任务解释依赖生成时快照，而不是实时主数据。

**状态**: 已自动化覆盖。需求审批、任务生成、快照保留和后续任务引用见 `apps/api/tests/test_mvp_a_flow.py`、`apps/api/tests/test_requirement_lifecycle.py` 与 `apps/api/tests/test_technical_solution_export.py`。

---

### TC-AIBRAIN-REQ-FUNC-011C: 新增需求可不指定迭代版本并后续排期

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011C |
| 用例名称 | 新增需求可不指定迭代版本并后续排期 |
| 优先级 | P0 |
| 模块 | REQUIREMENT |
| 创建人 | Codex |
| 创建日期 | 2026-06-03 |

**前置条件**:
1. 用户已登录并具备需求创建、审批和任务生成权限。
2. 系统存在启用产品和同产品未归档迭代版本。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/requirements`，只传产品、不传 `version_id` | 需求创建成功，状态为 `submitted`，`version_id=null`。 |
| 2 | POST `/api/requirements/{id}/approve` | 需求进入 `approved` 需求池，仍未排期。 |
| 3 | POST `/api/requirements/{id}/generate-task` | 返回 `409 REQUIREMENT_STATE_INVALID`，提示只能对已排期需求生成任务。 |
| 4 | PATCH `/api/requirements/{id}`，补充未归档 `version_id` | 需求进入 `planned`，可在需求列表看到迭代版本名称。 |
| 5 | POST `/api/requirements/{id}/generate-task` | 返回 draft 产品详细设计任务，需求状态进入 `designing` 并追加 `task_ids`。 |

**预期结果**:
1. 需求池和迭代排期解耦，新增需求阶段不强迫选择版本。
2. 只有已排期需求能进入 AI 任务交付，避免任务缺少版本上下文。

**状态**: 已自动化覆盖。见 `apps/api/tests/test_requirement_lifecycle.py::test_requirement_can_start_in_backlog_and_be_planned_into_iteration_version` 与 `apps/web/tests/App.test.tsx` 路由/表单用例。

---

### TC-AIBRAIN-KNOWLEDGE-FUNC-012: 知识中心独立运营

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-KNOWLEDGE-FUNC-012 |
| 用例名称 | 知识中心独立运营 |
| 优先级 | P0 |
| 模块 | KNOWLEDGE |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 知识维护者已登录。
2. 系统存在可导入的 Markdown 测试文档。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/knowledge/documents` | 文档创建成功；Embedding 可用时进入 `vector_indexed`，不可用但文本切片成功时进入 `text_indexed`。 |
| 2 | GET `/api/knowledge/documents?index_status=text_indexed` 或 `vector_indexed` | 可按索引状态查询。 |
| 3 | POST `/api/knowledge/search` | 仅返回有权限的知识结果；文本兜底结果 `retrieval_mode=keyword`，向量结果 `retrieval_mode=vector`。 |
| 4 | 审核知识沉淀候选 | 可批准或拒绝，状态正确流转。 |
| 5 | 模拟 Embedding 不可用后调用 `POST /api/knowledge/documents/{document_id}/retry-index` | 文档先保持 `text_indexed` 且关键词检索可用；Embedding 恢复后重试升级为 `vector_indexed`。 |

**预期结果**:
1. 知识中心不依赖 AI 任务完成也可以主动导入和检索。
2. 知识沉淀必须审核后才能进入正式知识库。

**状态**: 已自动化覆盖。知识导入、索引、检索、沉淀审核和失败重试见 `apps/api/tests/test_knowledge_governance.py` 与 `apps/web/tests/App.test.tsx` 知识中心用例。

---

### TC-AIBRAIN-AUDIT-API-013: 主体级审计查询

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-AUDIT-API-013 |
| 用例名称 | 主体级审计查询 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | AUDIT |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 系统已产生产品、需求、AI 任务、知识文档和人工确认相关审计事件。
2. 当前用户具备查看对应主体审计事件的权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/audit/events?subject_type=requirement&subject_id={requirement_id}` | 只返回该需求相关事件。 |
| 2 | GET `/api/audit/events?subject_type=ai_task&subject_id={task_id}` | 返回任务创建、启动、确认、回写相关事件。 |
| 3 | GET `/api/audit/events?subject_type=knowledge_document&subject_id={document_id}` | 返回导入、索引、权限变更或沉淀审核事件。 |
| 4 | GET `/api/audit/events?actor_id={user_id}&created_from={start}&created_to={end}` | 只返回该操作者在时间范围内的审计事件。 |
| 5 | 在审计与运行列表点击“详情” | 弹窗展示事件类型、主体、AI 任务、操作者、发生时间和 payload。 |
| 6 | 在审计与运行列表点击“链路追踪” | 优先以审计主体查询生命周期上下游、风险信号和缺失上下文。 |
| 7 | 使用无权限用户查询主体审计事件 | 返回 403 或空结果，不泄露主体存在性。 |
| 8 | 使用不存在的 subject_id 查询 | 返回空列表，不报 500。 |

**预期结果**:
1. 审计事件可按主体类型、主体 ID、操作者和创建时间范围过滤。
2. 审计详情和链路追踪均从真实接口数据渲染，不展示兜底示例数据。
3. 主体级查询遵守同一权限边界。
4. 无结果和无权限场景语义明确。

**状态**: 已自动化覆盖。主体、操作者、时间过滤见 `apps/api/tests/test_security_boundaries.py::test_audit_events_filter_by_actor_and_time_range`，审计详情和生命周期追踪入口见 `apps/web/tests/App.test.tsx::opens real audit detail and lifecycle trace actions from audit rows`。

---

## 研发运营与 Bug 管理测试用例

### TC-AIBRAIN-DEVOPS-FUNC-014: GitLab 代码质量与提交统计

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DEVOPS-FUNC-014 |
| 用例名称 | GitLab 代码质量与提交统计 |
| 优先级 | P1 |
| 模块 | DEVOPS |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 产品已绑定状态为 `active` 的 GitLab Git 资源。
2. GitLab 每日指标登记/导入数据包含提交、作者、Merge Request、代码变更量和代码质量审核结果。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 产品负责人、研发负责人或管理员调用 `POST /api/devops/gitlab/daily-code-metrics` 登记每日 GitLab 指标 | 提交、作者、MR、变更量和质量风险写入 `gitlab_daily_code_metrics`。 |
| 2 | GET `/api/devops/gitlab/daily-code-metrics?product_id=product_001&date=2026-05-29` | 返回产品、仓库、日期、提交数量、活跃作者数、质量评分和风险数量。 |
| 3 | 按人员查看作者聚合 | 返回每位作者的提交数、变更行数和代码审核问题数。 |
| 4 | 使用不属于该产品或 inactive 的仓库登记指标 | 返回参数错误，不写入产品级统计。 |

**预期结果**:
1. GitLab 指标必须通过 `product_git_repositories` 归属产品。
2. 产品级统计不混入未归属仓库数据。
3. 指标登记记录 `gitlab_daily_code_metric.created` 审计事件；外部自动采集器接入后仍不得绕过产品归属校验。

**状态**: 已自动化覆盖基础登记、筛选、审计和持久化；外部自动采集器接入后补充采集运行记录验收。

---

### TC-AIBRAIN-OPS-FUNC-015: 线上运行日志运营分析

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-OPS-FUNC-015 |
| 用例名称 | 线上运行日志运营分析 |
| 优先级 | P1 |
| 模块 | OPS |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 系统存在 active 产品，且可选存在 active 产品模块。
2. 有来自线上运行日志采集器、监控平台或人工导入的真实聚合指标，包含请求数、错误数、接口耗时、核心业务事件和 Top Errors。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | `POST /api/ops/online-log-metrics` 登记指定产品、模块、环境和时间窗口的真实聚合指标 | 返回 `online_log_metric_*`，服务端按错误数/请求数计算 `error_rate`，写入 `online_log_metrics` 并记录 `online_log_metric.created` 审计事件。 |
| 2 | GET `/api/ops/online-log-metrics?product_id=product_001&module_code=checkout&environment=prod&from=2026-06-01T00:00:00Z&to=2026-06-01T01:00:00Z` | 返回产品、模块、环境、时间窗口、请求数、错误数、错误率、延迟、核心业务事件和 top_errors。 |
| 3 | 按模块、环境或时间窗口过滤指标 | 仅返回匹配条件的日志聚合结果；没有记录时返回真实空集合。 |
| 4 | 使用 reviewer 角色、无效模块、反向时间窗口或负数指标登记 | 返回 `FORBIDDEN` 或 `VALIDATION_ERROR`/`NOT_FOUND`，不得写入指标或生成兜底数据。 |

**预期结果**:
1. 线上运行日志指标支持按产品、模块、环境和时间窗口查询。
2. 登记写操作必须校验角色、产品/模块归属、时间窗口和计数字段，并记录审计。
3. 核心业务事件和系统健康指标可被首页看板复用；外部自动采集器未接入时也不得生成伪造指标。

**状态**: 已自动化覆盖基础登记、查询、权限、校验和持久化；外部自动采集器端到端按 v1.2 后续补充。

---

### TC-AIBRAIN-RELEASE-FUNC-016: Jenkins 发布数据登记与查询

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-RELEASE-FUNC-016 |
| 用例名称 | Jenkins 发布数据登记与查询 |
| 优先级 | P1 |
| 模块 | DEVOPS |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 产品和版本已存在，且产品处于 active 状态、版本未归档。
2. 当前用户具备产品负责人、研发负责人或管理员角色。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/devops/jenkins/releases` 登记成功发布记录 | job、build_id、状态、环境、版本、触发人、耗时和提交号被记录，并写入 `jenkins_release.created` 审计事件。 |
| 2 | GET `/api/devops/jenkins/releases?product_id=product_001&version_id=version_001` | 返回产品版本下的发布记录列表。 |
| 3 | 按 `status=success` 和 `environment=prod` 查询发布 | 返回最近成功部署时间、环境和构建 ID。 |
| 4 | 登记失败发布并查询 `status=failed` | 返回失败原因，不覆盖最近成功发布信息。 |

**预期结果**:
1. Jenkins 发布记录必须按产品和版本归属。
2. 发布失败原因可用于首页看板风险摘要。
3. 发布记录可关联 GitLab 提交、需求、AI 任务或线上日志事件。
4. 记录必须持久化到 `jenkins_release_records`，无记录时返回真实空集合，不生成兜底数据。
5. archived 版本不得继续登记发布记录。

**状态**: 已自动化覆盖基础登记、筛选、审计和持久化；外部自动采集器接入后补充采集运行记录验收。

---

### TC-AIBRAIN-DEVOPS-FUNC-023: 采集运行记录登记与更新

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DEVOPS-FUNC-023 |
| 用例名称 | 采集运行记录登记与更新 |
| 优先级 | P1 |
| 模块 | DEVOPS |
| 创建人 | Codex |
| 创建日期 | 2026-06-02 |

**前置条件**:
1. 产品已存在且处于 active 状态。
2. 当前用户具备产品负责人、研发负责人或管理员角色；另准备 reviewer/viewer 角色用于越权验证。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/collectors/runs` | 无数据时返回 `items=[]`、`total=0`，不返回示例采集运行。 |
| 2 | POST `/api/collectors/runs` 登记 `gitlab_daily_code_metric` 运行 | 返回 `collector_run_*`，写入 `collector_runs`，并记录 `collector_run.created` 审计事件。 |
| 3 | PATCH `/api/collectors/runs/{run_id}` 标记 `succeeded` 并设置 `records_imported` | 自动补齐 `finished_at`，记录 `collector_run.updated` 审计事件。 |
| 4 | PATCH 已终态运行回 `running` | 返回 `COLLECTOR_RUN_STATE_INVALID`。 |
| 5 | 登记或更新 `failed` 但不提供 `error_message` | 返回 `VALIDATION_ERROR`。 |
| 6 | reviewer/viewer 尝试 POST/PATCH | 返回 `FORBIDDEN`。 |
| 7 | 在研发运营页面打开“采集运行记录”，登记运行并标记成功 | 页面调用 `/api/collectors/runs`，刷新后仍展示真实持久化运行记录。 |

**预期结果**:
1. 采集运行记录只记录采集尝试和结果，不自动生成 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议数据。
2. `collector_runs` 可从 PostgreSQL 结构表恢复，`collector_run` 计数器可延续。
3. 运行列表支持按采集类型、产品、状态和来源系统筛选。

**状态**: 已自动化覆盖 API、权限、审计、持久化和前端页面操作；见 `apps/api/tests/test_collector_runs.py`、`apps/api/tests/test_database_persistence.py::test_collector_runs_are_persisted_through_fine_grained_repository_payload` 和 `apps/web/tests/App.test.tsx` collector run 用例。

---

### TC-AIBRAIN-ATTRIBUTION-FUNC-024: 待归属数据队列登记与处理

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-ATTRIBUTION-FUNC-024 |
| 用例名称 | 待归属数据队列登记与处理 |
| 优先级 | P1 |
| 模块 | ATTRIBUTION |
| 创建人 | Codex |
| 创建日期 | 2026-06-02 |

**前置条件**:
1. 系统存在 active 产品，可选存在产品模块和需求。
2. 当前用户具备产品负责人、研发负责人或管理员角色；另准备 reviewer/viewer 角色用于越权验证。
3. 可选存在 `collector_runs` 记录，用于验证采集运行来源追踪。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/attribution/pending-items` | 无数据时返回 `items=[]`、`total=0`，不返回示例待归属项。 |
| 2 | POST `/api/attribution/pending-items` 登记 `user_feedback` 待归属项 | 返回 `pending_attr_*`，状态为 `pending`，写入 `pending_attribution_items`，并记录 `pending_attribution.created` 审计事件。 |
| 3 | GET 按 `source_type/status/collector_run_id` 筛选 | 仅返回匹配的真实队列项。 |
| 4 | POST `/api/attribution/pending-items/{item_id}/resolve`，`resolution_action=link_existing_context` | 状态变为 `resolved`，保存 resolved_product/module/requirement/subject 字段，并记录 `pending_attribution.resolved` 审计事件。 |
| 5 | POST 另一个队列项，`resolution_action=ignore_as_noise` | 状态变为 `ignored`，不允许携带归属上下文字段，并记录 `pending_attribution.ignored` 审计事件。 |
| 6 | 对 `resolved` 或 `ignored` 项再次 resolve | 返回 `PENDING_ATTRIBUTION_STATE_INVALID`。 |
| 7 | reviewer/viewer 尝试 POST 或 resolve | 返回 `FORBIDDEN`。 |
| 8 | 在研发运营页面打开“待归属数据队列”，归属或忽略队列项 | 页面调用真实接口，处理后刷新列表，不生成任何指标或反馈行。 |
| 9 | 在用户洞察/迭代规划页面查看待归属使用/反馈数据 | 页面只读展示 `user_usage_metric` 和 `user_feedback` 来源待归属项。 |

**预期结果**:
1. 待归属队列只记录无法自动映射的真实导入事实和人工处理结果。
2. 处理动作不自动生成 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议/需求等业务数据。
3. `pending_attribution_items` 可从 PostgreSQL 结构表恢复，`pending_attr` 计数器可延续。

**状态**: 已自动化覆盖 API、权限、审计、持久化和前端页面操作；见 `apps/api/tests/test_pending_attribution.py`、`apps/api/tests/test_database_persistence.py::test_pending_attribution_items_are_persisted_through_fine_grained_repository_payload` 和 `apps/web/tests/App.test.tsx` 待归属队列用例。

---

### TC-AIBRAIN-DASHBOARD-FUNC-017: 首页 IT 团队看板

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DASHBOARD-FUNC-017 |
| 用例名称 | 首页 IT 团队看板 |
| 优先级 | P1 |
| 模块 | DASHBOARD |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 系统存在需求、AI 任务、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈、AI 迭代规划建议和知识沉淀统计数据。
2. 用户具备查看首页 IT 团队看板权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开首页 IT 团队看板 | 展示真实需求、研发进展、待确认 Review、知识沉淀、审计、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈和迭代建议摘要。 |
| 2 | GET `/api/dashboard/it-team?product_id=product_001&time_range=7d` | 返回同一产品维度下的需求、任务、Review、知识、审计、Bug、DevOps、线上日志和用户洞察聚合指标，其他产品数据不计入当前产品，运营类指标按可解析时间窗口过滤。 |
| 3 | 按产品和时间范围切换筛选 | 看板所有卡片同步切换产品归属和时间范围。 |
| 4 | 从 Bug、研发运营、用户洞察或审计卡片下钻 | 跳转到对应主体列表或明细，并保留产品和时间范围上下文。 |

**预期结果**:
1. 首页只展示聚合和风险摘要，明细下钻到对应主体页面。
2. 看板指标来源可追溯到需求、任务、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件。
3. 无数据产品展示空状态，不报 500。

**状态**: 已自动化覆盖。后端聚合见 `apps/api/tests/test_empty_collections.py::test_dashboard_it_team_returns_real_mvp_aggregate_without_fake_rows`；前端产品/时间筛选、运营卡片和下钻链接见 `apps/web/tests/App.test.tsx::renders dashboard and operation pages without placeholder data`、`apps/web/tests/App.test.tsx::reloads the dashboard with a selected product filter` 与 `apps/web/tests/App.test.tsx::fetches the dashboard with product and time range query parameters`。

---

### TC-AIBRAIN-BUG-FUNC-018: Bug 管理基础闭环

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-BUG-FUNC-018 |
| 用例名称 | Bug 管理基础闭环 |
| 优先级 | P1 |
| 模块 | BUG |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 存在启用产品、版本和模块。
2. 存在 AI 自动测试执行结果和人工测试登记输入。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/bugs`，source=`ai_auto_test` 且不带 reproduce_steps | Bug 创建成功，来源为 AI 自动测试，状态为 `needs_info`。 |
| 2 | POST `/api/bugs`，source=`manual_test` | Bug 创建成功，来源为人工测试。 |
| 3 | PATCH `/api/bugs/{id}` 补充复现步骤并分派处理人 | 状态按 `needs_info -> triaged -> assigned` 或 `open -> assigned` 合法流转。 |
| 4 | PATCH `/api/bugs/{id}` 标记 fixed/verified/closed | Bug 完成修复、验证和关闭。 |
| 5 | 创建重复 Bug 并设置 duplicate_of_bug_id | 重复 Bug 关联主 Bug，不重复进入修复队列。 |
| 6 | 在 Bug 管理工作台编辑 Bug | 弹窗展示后端返回的复现步骤、证据 JSON、重复归并和只读来源；保存时 PATCH `reproduce_steps`、`evidence`、`duplicate_of_bug_id`、状态和处理人，不生成本地兜底数据。 |
| 7 | 使用无写权限角色 POST `/api/bugs` | 返回 `FORBIDDEN`，不创建 Bug。 |

**预期结果**:
1. Bug 必须归属产品，可关联版本、模块、需求、任务、提交、发布或线上日志事件。
2. AI 自动测试和人工测试登记来源可区分。
3. Bug 状态流转、重复归并和越权拦截写入或保留可追溯审计语义。

**状态**: 已自动化覆盖 API 状态机、PostgreSQL 持久化和前端 Bug 工作台字段闭环；仍需在集成环境补充真实测试组织角色。

---

### TC-AIBRAIN-TASK-FUNC-020: 研发全链路 AI 任务类型覆盖

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-020 |
| 用例名称 | 研发全链路 AI 任务类型覆盖 |
| 优先级 | P1 |
| 模块 | TASK |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 存在已排期需求、产品上下文、代码 diff、测试结果、Jenkins 发布记录和线上日志样本。
2. 当前用户具备创建和启动 AI 任务权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 从已确认产品详细设计创建 `technical_solution`，再从已确认技术方案创建 `development_planning` | 均返回 `task_type`，并保留需求快照和产品上下文。 |
| 2 | 创建 `code_review` 任务并传入 MR/PR diff 快照 | 输出结构化 Review 报告、风险等级、文件/行号、修改建议和执行器元数据。 |
| 3 | 从已确认技术方案创建并启动 `automated_testing` 任务 | 输出测试分析和 Bug 建议；未确认前不创建 Bug，确认后生成来源为 `ai_auto_test` 的 Bug 记录。 |
| 4 | 从已确认技术方案创建并启动 `release_readiness` 任务 | input 包含源技术方案、Bug、Jenkins 发布记录、线上日志指标和 GitLab 每日代码指标真实快照；输出上线检查清单、发布风险评估和回滚建议。 |
| 5 | 从已确认发布评估创建并启动 `post_release_analysis` 任务 | input 包含源发布评估、发布记录、线上日志和 Bug 真实快照；输出上线后健康报告、异常趋势和疑似回归 Bug。 |

**预期结果**:
1. 已实现任务类型复用统一任务状态机、人工确认、审计和详情查询能力；`release_readiness` 和 `post_release_analysis` 已纳入当前自动化切片。
2. v1 系列不自动改代码、不自动提交 PR、不自动部署上线。
3. 自动化测试和上线后分析产生的 Bug 必须进入 Bug 管理闭环。

**状态**: development_planning / automated_testing / release_readiness / post_release_analysis 自动化通过。2026-06-03 使用 AI 助手聊天界面真实需求复跑时，`task_066` development_planning 完成，`task_067` automated_testing 首次模型失败后以 `task_068` 完成，`task_070` release_readiness 在同任务重试能力上线后可重新触发但上游模型仍失败，post_release_analysis 因缺少已完成发布评估未继续；该批次用于验证失败重试和外部模型稳定性风险。

---

### TC-AIBRAIN-REVIEW-FUNC-019: v1.1 研发扩展任务人工确认门禁

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-019 |
| 用例名称 | v1.1 研发扩展任务人工确认门禁 |
| 优先级 | P1 |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. `development_planning` 或 `automated_testing` 任务已运行到确认点。
2. 当前用户具备对应任务类型的确认权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/ai-tasks/{id}` | 返回 pending review 和 task_type。 |
| 2 | 不提交确认并等待 | 开发计划或自动化测试结论不进入下一阶段或回写。 |
| 3 | POST `/api/reviews/{id}/approve` | review 状态变为 `approved`。 |
| 4 | 查询任务详情；若为 `automated_testing`，查询 `/api/bugs?source=ai_auto_test` | 任务完成；自动化测试输出的 Bug 建议已转为真实 Bug 记录并关联需求和任务。 |

**预期结果**:
1. v1.1 研发扩展任务的高影响结论均受人工确认门禁保护。
2. 自动化测试任务生成 Bug 建议时，进入 Bug 管理前保留产品归属和复现信息要求。

**状态**: 自动化通过

---

### TC-AIBRAIN-REVIEW-FUNC-024: v1.2 发布和上线后分析人工确认门禁

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-024 |
| 用例名称 | v1.2 发布和上线后分析人工确认门禁 |
| 优先级 | P1 |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. `release_readiness` 或 `post_release_analysis` 任务已运行到确认点。
2. 当前用户具备发布负责人、运营负责人或研发负责人确认权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/ai-tasks/{id}` | 返回 pending review、风险结论和建议动作。 |
| 2 | 不提交确认并等待 | 发布建议采纳、风险处理或知识沉淀流程不继续。 |
| 3 | POST `/api/reviews/{id}/approve` 或 `/edit-approve` | 保存人工确认或人工修改后的确认内容。 |
| 4 | 查询任务结果；若为 `post_release_analysis`，查询 `/api/bugs?source=ai_post_release` | 任务基于确认后的内容完成；上线后分析输出的 Bug 建议已转为真实 Bug 记录并关联需求和任务。 |

**预期结果**:
1. 发布上线评估和上线后分析不能绕过人工确认。
2. 系统只给出风险判断和建议，不自动部署上线；上线后疑似回归进入 Bug 管理闭环。

**状态**: 自动化通过

---

### TC-AIBRAIN-REVIEW-FUNC-023A: MVP-A GitLab MR / GitHub PR 预览和 diff 快照

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-023A |
| 用例名称 | MVP-A GitLab MR / GitHub PR 预览和 diff 快照 |
| 阶段内优先级 | P0 |
| 适用阶段 | MVP-A |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 产品已绑定 GitLab/GitHub 代码库；GitLab 提供可解析的 `remote_url` 或 `GITLAB_BASE_URL`，GitHub 提供 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`，并通过环境变量、服务端密钥引用或本地直填只读 token 提供凭据；当前用户具备该产品和 MR/PR 的 Review 权限。
2. 存在已排期需求、已确认产品详细设计和已确认技术方案。
3. 远端存在可访问 Merge Request 或 Pull Request，且 diff 未超过 v1 MVP 限制。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GitHub 仓库 GET `/api/devops/github/pull-requests/{repository_id}?state=all&limit=20` | 返回当前凭据可访问 PR 列表、分支、作者、更新时间和 `writeback_allowed=false`；无 PR 时返回真实空集合。 |
| 2 | GET GitLab `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview` 或 GitHub `/api/devops/github/pull-requests/{repository_id}/{pr_number}/preview` | 返回 MR/PR 标题、作者、source/head branch、target/base branch、changed_file_count、diff_refs 和 web_url。 |
| 3 | POST GitLab `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot` 或 GitHub `/api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot` | 返回 snapshot_id、diff_size_bytes、diff_limit 和 created_at；快照不受后续 MR/PR 变更静默影响。 |
| 4 | 再次拉取相同 diff | 返回已有 snapshot_id，不重复写入 `gitlab_mr_snapshots`，并记录 `gitlab_mr.snapshot_reused` 或 `github_pr.snapshot_reused` 审计事件。 |
| 5 | 输入超过 diff 字节数、变更文件数或单文件 diff 行数限制的 MR/PR | 返回 `GITLAB_MR_DIFF_TOO_LARGE`，不得静默截断后继续；审计包含 `*.snapshot_failed`、`diff_size_bytes`、`diff_limit_bytes`、`changed_file_count`、`changed_file_limit`、`file_diff_line_count` 或 `file_diff_line_limit`。 |
| 6 | 移除 GitLab/GitHub base URL 或只读 token 后重试 preview | 返回 provider 对应的配置或凭据错误，不得生成本地假 MR/PR。 |

**预期结果**:
1. MVP-A 已具备 GitLab/GitHub 只读输入依赖。
2. MR/PR 快照是后续 code_review 任务的唯一输入来源。
3. 系统不得向 GitLab/GitHub 回写评论、审批状态、request changes、合并状态或分支变更。
4. diff 字节数、变更文件数或单文件 diff 行数超限失败必须留下可审计指标，便于判断拆分 MR/PR 或调整限制。

**状态**: 已自动化覆盖。GitLab MR 预览、只读快照、相同 diff 复用和超限错误见 `apps/api/tests/test_gitlab_snapshot.py`；GitHub PR 列表、预览、只读快照和 code_review 任务创建见 `apps/api/tests/test_github_snapshot.py`；需真实企业 GitLab/GitHub 凭据的端到端环境仍按生产就绪门禁验证。2026-06-03 使用产品 `product_118` / 仓库 `repo_024` 复跑时创建 GitHub PR #1，AI Brain 成功读取 PR 列表、预览最新 head `2e14a7f` 的 35 个变更文件并生成 `snapshot_006`。

---

### TC-AIBRAIN-REVIEW-FUNC-023B: MVP-B GitLab MR / GitHub PR Code Review 报告闭环

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-023B |
| 用例名称 | MVP-B GitLab MR / GitHub PR Code Review 报告闭环 |
| 阶段内优先级 | P0 |
| 适用阶段 | MVP-B |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 已存在已确认的 `technical_solution` 任务和产品 GitLab/GitHub 只读资源绑定。
2. code-review 执行器默认适配 Claude Code `code-review` skill；本地联调未配置外部执行器命令但存在可用 Chat 模型网关时，应通过 `model_gateway` 适配器生成结构化 Review 报告。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在任务中心基于已完成 `technical_solution` 选择产品 GitLab/GitHub 代码库并预览 MR/PR | 页面展示 MR/PR 标题、作者、分支、变更文件数和“不回写远端”提示。 |
| 2 | 生成 MR/PR diff 快照并 POST `/api/ai-tasks` 创建 `task_type=code_review` 任务 | 任务为 `draft`，input 包含 requirement_snapshot、product_context 和 gitlab_mr_snapshot 兼容引用。 |
| 3 | POST `/api/ai-tasks/{id}/start` | 调用 code-review 执行器，任务进入 `waiting_review`，返回 pending review。 |
| 4 | 在任务中心查看 Code Review 报告或 GET `/api/ai-tasks/{id}/code-review-report` | 返回 summary、risk_level、findings、文件/行号、建议、confidence、executor metadata 和 human_review。 |
| 5 | POST `/api/reviews/{id}/approve` 或 `edit-approve` | Review 报告归档到 AI Brain 内部，任务继续或完成。 |
| 6 | 查询远端 MR/PR | 未新增评论，未改变审批状态、request changes、合并状态或分支。 |
| 7 | GET `/api/audit/events?ai_task_id={id}` | 返回执行器调用、报告生成、人工确认和归档审计事件。 |
| 8 | 保持默认 `claude_code_skill` 但不配置外部命令，同时保留 active/default Chat 模型网关 | 任务通过 `model_gateway` 适配器进入 `waiting_review`，prompt 携带 MR/PR 快照和技术方案；报告包含 executor metadata，审计包含 `model_gateway.called` 和 `code_review.executor_called`。 |
| 9 | 让 code-review 执行器返回非法结构或调用失败 | 返回 `CODE_REVIEW_EXECUTOR_FAILED`，任务为 `failed`，`current_step=code_review_executor_failed`，审计包含 `code_review.executor_failed` 和 `ai_task.failed`。 |
| 10 | 修复执行器或上游模型后再次 POST `/api/ai-tasks/{id}/start` | 同一任务可重新进入执行器调用；成功时进入 `waiting_review`，并记录 `ai_task.retry_started` 审计事件。 |

**预期结果**:
1. v1 MVP 可以基于 GitLab MR / GitHub PR diff 快照生成结构化 Review 报告。
2. Review 报告必须经过人工确认后才能归档为正式结论。
3. 系统不得向 GitLab/GitHub 回写评论、审批状态、request changes、合并状态或分支变更。
4. 执行器失败时返回 `CODE_REVIEW_EXECUTOR_FAILED`，停留在可排查的失败步骤并写入审计；修复配置后可用同一任务重试，避免复制新任务导致链路割裂。

**状态**: 已自动化覆盖。Code Review 报告生成、确认归档、编辑确认、执行器失败语义，以及外部执行器命令缺失时复用模型网关的本地联调路径见 `apps/api/tests/test_code_review_report.py`；真实执行器/模型 provider 端到端按生产就绪门禁验证。2026-06-03 使用 AI Brain GitHub PR #1 最新 head 复跑时，`task_072` 基于 `snapshot_006` 生成 `report_006`，人工确认后任务完成且报告归档，GitHub issue comments、review comments 和 reviews 均为 0。

---

### TC-AIBRAIN-FLOW-FUNC-021: 软件研发全流程感知

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-FLOW-FUNC-021 |
| 用例名称 | 软件研发全流程感知 |
| 优先级 | P1 |
| 模块 | FLOW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 存在 MVP 数据：已排期需求、产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、知识沉淀和审计事件。
2. v1.2 扩展测试需要额外准备提交、自动化测试结果、Bug、Jenkins 发布记录、线上日志、用户使用、用户反馈和迭代规划建议关联数据。
3. 上述数据均可映射到同一产品、版本、模块或需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 以 MVP 数据查询感知视图 | 返回需求下游产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、模拟 Issue、知识沉淀和审计事件。 |
| 2 | 从感知视图下钻到任务或审计事件 | 保留产品、版本、模块、需求和时间范围上下文。 |
| 3 | 分别以 `human_review`、`code_review_report`、`mock_issue`、`knowledge_deposit` 和 `audit_event` 作为起点查询 | 返回对应任务的上游需求、下游证据和风险信号，不混入同产品下无关任务。 |
| 4 | 使用不支持的 `subject_type` 查询 | 返回 `VALIDATION_ERROR`，不得退化为全量任务结果。 |
| 5 | 以 v1.2 数据查询感知视图 | 返回提交、Review、测试、Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议等扩展关系。 |
| 6 | 注入无法归属产品的提交 | 进入待归属队列，不参与需求级风险结论；队列登记和处理按 `TC-AIBRAIN-ATTRIBUTION-FUNC-024` 验证。 |

**预期结果**:
1. 全流程感知在 v1 MVP 至少支持从需求查看下游产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、模拟 Issue、知识沉淀和审计事件。
2. 全流程感知在 v1 MVP 可以从人工确认、Code Review 报告、MR 快照、模拟 Issue、知识沉淀、审计事件和 Bug 等证据主体回到对应任务链路。
3. v1.2 扩展后可以从任一主体追溯上游依据和下游影响。
4. 风险信号必须包含来源主体、影响摘要和处理建议。
5. 上下游链路缺失时明确标识缺口，不把缺失上下文当作无风险。

**状态**: 已自动化覆盖 MVP 与 v1.2 真实证据主体链路追踪。MVP 需求下游、人工确认、Code Review 报告、模拟 Issue、知识沉淀和审计起点见 `apps/api/tests/test_lifecycle_context.py` 与 `apps/web/tests/App.test.tsx::opens real audit detail and lifecycle trace actions from audit rows`；v1.2 Bug、GitLab 每日代码指标、Jenkins 发布记录、线上日志指标、用户使用指标、用户反馈、迭代规划建议、动态 `missing_context` 和风险来源断言见 `apps/api/tests/test_lifecycle_context.py::test_lifecycle_context_links_v1_2_evidence_and_dynamic_missing_context`、`apps/api/tests/test_lifecycle_context.py::test_lifecycle_context_reports_missing_v1_2_context_dynamically` 以及 `apps/web/tests/App.test.tsx::opens real audit detail and lifecycle trace actions from audit rows`；生命周期边/风险信号和首页看板快照物化持久化见 `apps/api/tests/test_lifecycle_context.py::test_lifecycle_context_and_dashboard_queries_materialize_persistent_records` 与 `apps/api/tests/test_database_persistence.py::test_lifecycle_context_and_dashboard_snapshots_persist_through_fine_grained_repository`。

---

### TC-AIBRAIN-PLANNING-FUNC-022: 用户使用洞察与 AI 迭代规划

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-PLANNING-FUNC-022 |
| 用例名称 | 用户使用洞察与 AI 迭代规划 |
| 优先级 | P1 |
| 模块 | PLANNING |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 存在产品规划、需求池、Bug、线上日志、发布记录和研发投入样本。
2. 已通过 API、页面或采集器导入实际业务系统用户使用数据和用户反馈样本。
3. 用户具备产品负责人或 IT 管理者权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 聚合产品用户使用指标 | 返回活跃用户、功能访问、关键路径转化、停留、异常退出和低使用功能。 |
| 2 | 收集并查询用户反馈 | 返回满意度、问题反馈、改进建议、投诉、来源渠道、标签和关联模块。 |
| 3 | 触发 AI 迭代规划建议生成 | 返回下阶段优先迭代需求建议清单，状态为 `suggested`，不创建新 requirement。 |
| 4 | 查看建议详情 | 每条建议包含推荐理由、用户证据、业务价值、风险信号、依赖条件、预估研发投入和建议优先级。 |
| 5 | 模拟使用数据不足或反馈样本过少 | 建议标识证据不足，不给出确定性排序。 |
| 6 | 查询需求列表和产品规划 | 未出现由 AI 建议自动创建的新需求、路线图变更或迭代排期变更。 |
| 7 | 产品负责人确认采纳并选择转正式需求 | 建议状态变为 `converted_to_requirement`，并返回人工确认后创建的 requirement_id。 |

**预期结果**:
1. MVP 阶段用户使用指标、用户反馈和 AI 迭代规划建议均来自真实结构表；AI 迭代规划建议可追溯到真实用户反馈和 Bug，v1.2 扩展到产品规划、需求、用户使用指标、线上日志和发布记录。
2. AI 只生成建议，不自动创建正式需求、不自动变更路线图、不自动调整迭代排期。
3. 只有产品负责人或等价权限确认采纳后，建议才能转为正式需求或进入迭代计划。
4. 无法归属产品或模块的使用数据和反馈进入待归属队列，登记、归属和忽略处理由 `TC-AIBRAIN-ATTRIBUTION-FUNC-024` 覆盖。

**状态**: 已自动化覆盖用户使用指标登记/查询、用户反馈、待归属用户使用/反馈只读可见性和迭代规划基础闭环；外部采集器和模型驱动规划仍属后续增强。

---

## 边界测试用例

| 用例编号 | 边界类型 | 测试数据 | 预期结果 |
|----------|----------|----------|----------|
| TC-AIBRAIN-TASK-BOUND-001 | 空标题 | `title = ""` | 返回 `VALIDATION_ERROR`。 |
| TC-AIBRAIN-KNOWLEDGE-BOUND-002 | top_k 超过上限 | `top_k = 1000` | 按最大允许值截断或返回校验错误。 |
| TC-AIBRAIN-REVIEW-BOUND-003 | 重复确认 | 同一 review 连续 approve 两次 | 第二次返回状态错误或版本冲突。 |
| TC-AIBRAIN-AUDIT-BOUND-004 | 空审计结果 | 不存在的 ai_task_id | 返回空列表，不报 500。 |

---

## 异常测试用例

| 用例编号 | 异常类型 | 触发条件 | 预期结果 |
|----------|----------|----------|----------|
| TC-AIBRAIN-AUTH-ERR-001 | 未授权 | 无 Bearer Token 调用写接口 | 返回 `UNAUTHORIZED`。 |
| TC-AIBRAIN-TASK-ERR-002 | 非法状态 | completed 任务再次 start | 返回 `TASK_STATE_INVALID`。 |
| TC-AIBRAIN-REVIEW-ERR-003 | 版本冲突 | 使用过期 version 确认 | 返回 `REVIEW_VERSION_CONFLICT`。 |
| TC-AIBRAIN-GRAPH-ERR-004 | 模型失败 | 模型网关返回错误 | 任务进入 failed 或可重试状态，记录审计。 |
| TC-AIBRAIN-KNOWLEDGE-ERR-005 | embedding 维度不匹配 | embedding 写入 pgvector 失败 | 文档保持 `text_indexed`，记录 `vector_index_error`，关键词检索仍返回带来源结果。 |
| TC-AIBRAIN-KNOWLEDGE-ERR-006 | 知识索引失败 | 文档内容无法切片，或非 `index_failed`/`text_indexed` 文档调用 retry-index | 基础文本索引失败时文档进入 `index_failed` 并保留失败原因；状态不匹配返回 `KNOWLEDGE_INDEX_STATE_INVALID`。 |

---

## API 测试用例

| 用例编号 | 接口 | 场景 | 预期结果 |
|----------|------|------|----------|
| TC-AIBRAIN-TASK-API-001 | POST /api/ai-tasks | 正常创建 `product_detail_design` 任务 | 201/200，返回 task id 和 task_type。 |
| TC-AIBRAIN-TASK-API-002 | GET /api/ai-tasks/{id} | 查询无权限任务 | 403 或 404。 |
| TC-AIBRAIN-TASK-API-019 | POST /api/ai-tasks | 创建七类研发全链路 task_type | 均返回对应 task_type，非法类型返回 `VALIDATION_ERROR`。 |
| TC-AIBRAIN-REVIEW-API-003 | POST /api/reviews/{id}/edit-approve | 修改后采纳 | 保存 edited_content 并恢复 graph。 |
| TC-AIBRAIN-KNOWLEDGE-API-004 | POST /api/knowledge/search | 正常检索 | 返回 items，包含 title、snippet、source。 |
| TC-AIBRAIN-OUTPUT-API-005 | GET /api/export/tasks/{task_id}/markdown | MVP-A 导出方案 | 返回 `text/markdown`，并通过 Header 或日志关联 trace_id。 |
| TC-AIBRAIN-AUDIT-API-006 | GET /api/audit/events?ai_task_id={id} | 按任务查询 | 返回 items，最多 120 条。 |
| TC-AIBRAIN-AUDIT-API-013 | GET /api/audit/events?subject_type={type}&subject_id={id} | 按主体查询 | 返回指定主体的审计事件。 |
| TC-AIBRAIN-DEVOPS-API-014 | GET/POST /api/devops/gitlab/daily-code-metrics | 登记和查询 GitLab 每日指标 | 仅产品负责人、研发负责人或管理员可登记；产品和 GitLab 仓库归属校验通过后写入 `gitlab_daily_code_metrics` 并记录审计；GET 按产品、仓库和日期返回真实记录，无数据时返回空集合。 |
| TC-AIBRAIN-DEVOPS-API-023 | GET/POST/PATCH /api/collectors/runs | 查询、登记和更新采集运行记录 | GET 返回真实运行台账；POST/PATCH 仅产品负责人、研发负责人或管理员可写，写入 `collector_runs` 并记录 `collector_run.created/updated`；failed 必须有错误说明，终态不可回退。 |
| TC-AIBRAIN-OPS-API-015 | GET/POST /api/ops/online-log-metrics | 登记和查询线上运行日志指标 | 仅产品负责人、研发负责人或管理员可登记；产品和模块归属校验通过后写入 `online_log_metrics` 并记录审计；GET 按产品、模块、环境和时间窗口返回真实记录，无数据时返回空集合。 |
| TC-AIBRAIN-RELEASE-API-016 | GET/POST /api/devops/jenkins/releases | 登记和查询 Jenkins 发布 | 返回发布状态、失败原因，写入 `jenkins_release_records` 并记录审计。 |
| TC-AIBRAIN-DASHBOARD-API-017 | GET /api/dashboard/it-team | 查询首页 IT 团队看板 | 返回需求、研发、Bug、线上系统、核心业务和发布统计。 |
| TC-AIBRAIN-LIFECYCLE-API-021 | GET /api/lifecycle/context | 查询软件研发全流程感知 | 返回上下游关系、风险信号、影响摘要和建议；MVP 证据主体起点只返回对应任务链路。 |
| TC-AIBRAIN-PLANNING-API-026 | GET/POST /api/insights/usage-metrics | 登记和查询用户使用指标 | 仅产品负责人、研发负责人或管理员可登记；计数和比率校验通过后写入 `user_usage_metrics` 并记录审计；GET 按产品、模块、功能、用户群体和时间范围返回真实记录，无数据时返回空集合。 |
| TC-AIBRAIN-PLANNING-API-022 | GET/POST /api/planning/iteration-suggestions | 查询或生成 AI 迭代规划建议 | 基于真实用户反馈和 Bug 证据返回建议清单、优先级、证据链、价值、风险、依赖和投入评估；无证据时返回空集合；生成阶段不自动创建正式需求或调整路线图/排期。 |
| TC-AIBRAIN-PLANNING-API-023 | POST /api/planning/iteration-suggestions/{suggestion_id}/decide | 产品负责人确认迭代规划建议 | accepted/edited_accepted 且 `convert_to_requirement=true` 后才允许转正式需求，未确认时保持 suggested 状态。 |
| TC-AIBRAIN-BUG-API-018 | GET/POST/PATCH /api/bugs | Bug 查询、登记和状态更新 | 支持 AI 自动测试、AI 上线后分析和人工测试来源，状态正确流转；前端工作台保存复现步骤、证据 JSON、重复归并和只读来源展示。 |
| TC-AIBRAIN-AUTH-API-024 | GET /api/auth/roles + POST/PATCH /api/users | 查询角色目录并按目录维护用户角色 | 返回 `admin/product_owner/rd_owner/reviewer/knowledge_owner/viewer` 六个角色及业务角色映射、职责、数据范围、决策范围、可见入口和限制边界；未知角色返回 `VALIDATION_ERROR`。 |
| TC-AIBRAIN-KNOWLEDGE-API-025 | POST /api/knowledge/documents/{document_id}/retry-index | 重试失败知识文档索引或补建向量索引 | `index_failed` 文档可重建文本/向量索引，`text_indexed` 文档可补建向量索引；成功后进入 `text_indexed` 或 `vector_indexed`，状态不匹配返回 `KNOWLEDGE_INDEX_STATE_INVALID`。 |
| TC-AIBRAIN-ASSISTANT-API-027 | POST /api/assistant/chat + GET /api/assistant/conversations | AI 助手系统问答与历史 | 基于服务端注入的脱敏系统上下文和 Chat 模型网关返回助手回答；按当前用户保存会话和消息，其他用户不可读取；模型日志只记录 `purpose=assistant_chat` 元数据，不保存完整问题或回答。 |
| TC-AIBRAIN-CONFIG-API-008 | GET/POST/PATCH 产品配置接口 | 配置产品上下文 | 返回 items 或配置详情，写操作产生审计。 |
| TC-AIBRAIN-CONFIG-API-009 | GET/POST/PATCH /api/system/model-gateway-configs | 配置平台模型网关 | 返回 api_key_configured 和 embedding_api_key_configured，不返回明文或密钥片段；Embedding 支持 disabled/reuse_chat/custom，Chat-only 配置可保存并驱动 AI 任务，custom Embedding 连接用于知识向量索引。 |

---

## 性能测试用例

| 用例编号 | 指标 | 测试方式 | 目标 |
|----------|------|----------|------|
| TC-AIBRAIN-TASK-PERF-001 | 任务详情接口 | 并发查询任务详情 | P95 < 500ms。 |
| TC-AIBRAIN-KNOWLEDGE-PERF-002 | 知识检索 | 1000 个 chunk 数据集执行 top_k 检索 | P95 < 1s。 |
| TC-AIBRAIN-AUDIT-PERF-003 | 审计查询 | 按 ai_task_id 查询 | P95 < 500ms。 |
| TC-AIBRAIN-DASHBOARD-PERF-004 | 首页 IT 团队看板 | 读取 30 天产品指标快照 | P95 < 800ms。 |
| TC-AIBRAIN-OPS-PERF-005 | 线上运行日志指标查询 | 按产品和环境查询 24 小时窗口 | P95 < 1s。 |
| TC-AIBRAIN-LIFECYCLE-PERF-006 | 软件研发全流程感知查询 | 从需求查询两跳上下游和风险信号 | P95 < 1s。 |
| TC-AIBRAIN-PLANNING-PERF-007 | 用户洞察和迭代规划查询 | 读取 30 天产品使用、反馈和规划建议聚合快照 | P95 < 800ms。 |

---

## 测试执行记录

### 执行汇总

| 批次 | 执行日期 | 执行人 | 用例总数 | 通过 | 失败 | 阻塞 | 通过率 |
|------|----------|--------|----------|------|------|------|--------|
| 1 | 2026-05-29 |  | 待执行统计 |  |  |  |  |

### 缺陷追踪

| 缺陷编号 | 关联用例 | 缺陷描述 | 严重程度 | 状态 | 修复版本 |
|----------|----------|----------|----------|------|----------|
|  |  |  |  |  |  |

---
最后更新: 2026-06-02
