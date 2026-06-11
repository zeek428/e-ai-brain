# 系统概览

## 业务背景

AI Brain 是企业 AI 大脑平台。v1 以产品研发大脑为样板，第一期跑通研发需求从提交、审批、产品详细设计、技术方案、内部 GitLab MR 预览和 diff 快照、内部 GitLab MR 代码 Review、人工确认、内部报告归档到知识沉淀的最小闭环；自动化测试、发布上线评估、上线后分析和完整 Bug 管理按后续阶段扩展。系统通过软件研发全流程感知把需求、设计、代码、测试、发布和线上反馈纳入同一产品上下文，并提供 AI 助手聊天工作台，基于脱敏系统上下文回答 AI Brain 配置、需求任务、代码仓库、模型网关状态和项目开发进展问题。

详细产品范围以项目级 PRD 为准：[enterprise-ai-brain/prd.md](../../01-prd/enterprise-ai-brain/prd.md)。

## 系统架构图

```text
用户浏览器
  │
  ▼
React + TypeScript 工作台（基于 Ant Design Pro 模板）
  │
  ▼
FastAPI 模块化单体
  ├─ auth：本地账号、角色、权限
  ├─ brain_app：业务大脑配置
  ├─ assistant：AI Brain 系统问答和项目进展助手
  ├─ product_config：产品、版本、模块、Git 资源和相关系统
  ├─ requirement：需求台账、审批和生成 AI 任务
  ├─ ai_task：AI 任务生命周期
  ├─ graph_runtime：LangGraph 运行、检查点和恢复
  ├─ review：人工确认
  ├─ knowledge：文档导入、chunk、检索和沉淀
  ├─ long_memory：GBrain 长期记忆、混合检索和知识图谱
  ├─ model_gateway：OpenAI-compatible 模型调用
  ├─ plugin_management：插件、连接、动作和调用日志
  ├─ scheduled_jobs：定时作业定义、运行实例和 AI/插件装配快照
  ├─ code_inspection：周期性代码仓库巡检报告、finding、Bug 派生和通知反馈
  ├─ devops_metrics：GitLab、Jenkins 和线上日志指标采集
  ├─ gitlab_review：内部 GitLab MR 元信息、diff 快照和 Review 报告归档
  ├─ code_review_executor：可插拔代码 Review 执行器
  ├─ user_insights：用户使用和用户反馈采集
  ├─ iteration_planning：AI 迭代规划建议
  ├─ lifecycle_context：研发上下文图谱和风险信号
  ├─ bug：AI 自动测试和人工测试 Bug 闭环
  ├─ dashboard：首页 IT 团队看板聚合
  ├─ integration：模拟 Issue 回写
  ├─ audit：审计事件
  └─ export：Markdown 方案导出
  │
  ├─ PostgreSQL + pgvector
  ├─ Redis
  └─ GBrain（长期记忆 / 知识图谱）
```

## 核心模块

| 模块 | 职责 | 技术栈 |
|------|------|--------|
| web | 团队看板、AI 助手、任务中心/任务管理、产品管理、需求管理、Bug 管理、研发运营看板、用户洞察、知识中心、审计与运行 | React + TypeScript + Ant Design Pro |
| api | JSON API、认证、产品配置、需求审批、任务管理、Bug 管理、研发运营指标和模块化领域逻辑 | FastAPI + Python |
| assistant | 基于服务端脱敏系统上下文回答 AI Brain 系统信息、项目进展、产品、任务、Git 仓库和模型网关状态问题 | FastAPI + 模型网关 Chat |
| product_config | 产品、版本、模块、Git 资源、内部 GitLab 项目绑定和相关系统主数据 | PostgreSQL |
| requirement | 需求台账、审批、驳回、关闭和审批后生成 AI 任务 | PostgreSQL |
| ai_task | AI 任务类型、生命周期、状态流转和任务详情 | PostgreSQL + LangGraph |
| graph_runtime | 研发大脑 LangGraph 节点、中断、恢复 | LangGraph |
| knowledge | Markdown 导入、向量/关键词混合检索、权限过滤 | PostgreSQL + pgvector |
| long_memory | 长期记忆、答案合成、知识图谱和多跳查询 | GBrain |
| model_gateway | 聊天/embedding 模型统一入口 | OpenAI-compatible API |
| plugin_management | 三方系统插件、连接、动作、请求配置、试运行和调用日志 | PostgreSQL + HTTP/MCP HTTP |
| scheduled_jobs | 采集、AI 分析、插件动作调用、代码仓库巡检、迭代建议和看板刷新调度 | PostgreSQL + Redis/worker |
| code_inspection | 定期扫描仓库质量、安全和规范问题，按提交人沉淀代码巡检报告、finding 明细、严重问题 Bug 去重和通知反馈 | PostgreSQL + 插件扫描服务 |
| devops_metrics | GitLab 提交与代码质量、Jenkins 发布、线上运行日志指标采集和归属映射 | PostgreSQL + 定时采集器 |
| gitlab_review | 内部 GitLab MR 元信息、changes 只读读取、diff 快照、Review 报告归档和不回写 GitLab 约束 | GitLab API + PostgreSQL |
| code_review_executor | 可插拔代码 Review 执行器，一期默认对接 Claude Code `code-review` skill | Claude Code skill adapter |
| user_insights | 用户使用数据、用户反馈、归属映射和聚合分析 | PostgreSQL + 定时采集器 |
| iteration_planning | AI 迭代规划建议、证据链聚合和人工确认 | PostgreSQL + 模型网关 |
| lifecycle_context | 软件研发全流程上下文图谱、上下游追溯、风险信号和影响范围分析 | PostgreSQL |
| bug | AI 自动测试 Bug、人工登记 Bug、分派、修复、验证、关闭和重复归并 | PostgreSQL |
| dashboard | 首页 IT 团队看板和研发运营看板的产品级指标聚合 | PostgreSQL / Redis |
| integration | v1 模拟 Issue 回写 | PostgreSQL |
| audit | 操作和 AI 执行轨迹 | PostgreSQL |

## 数据流向

```text
提交研发需求
→ 创建 requirement 并等待审批
→ 审批通过后生成 ai_task，固化 task_type、requirement_snapshot 和 product_context
→ 启动 graph_run
→ 检索 knowledge_chunks
→ 可选查询 GBrain 长期记忆和知识图谱
→ 按 task_type 生成产品详细设计、技术方案、内部 GitLab MR Review 报告、开发计划、测试分析、发布评估或上线后分析
→ 创建 human_reviews
→ 人工确认后恢复 Graph
→ 生成 mock_issues / code_review_reports / Bug / Markdown / knowledge_deposits
→ lifecycle_context 写入需求、任务、提交、Review、测试、Bug、发布、日志和知识之间的关系边
→ lifecycle_context 归集需求变更、设计缺口、代码质量、Review、测试、Bug、发布和线上异常风险信号
→ GitLab、Jenkins、线上日志通过真实登记/导入或定时采集映射产品归属
→ 代码仓库巡检定时作业通过插件扫描质量/安全/规范 finding，按提交人写入代码巡检报告，严重问题去重派生 Bug，并记录邮件/钉钉机器人通知反馈
→ 用户使用数据和用户反馈定时采集并映射产品、模块、功能和用户群体
→ iteration_planning 结合需求池、Bug、线上日志、发布记录、用户使用和用户反馈生成迭代规划建议
→ AI 自动测试和人工测试登记 Bug，关联产品、任务、提交、发布或日志
→ 首页 IT 团队看板聚合需求、研发进展、Bug、代码质量、发布、线上健康、用户洞察、用户反馈和迭代规划建议
→ AI 助手读取脱敏系统上下文并通过模型网关 Chat 回答系统状态和项目进展问题
→ 写入 audit_events
```

## 关键设计决策

| 决策项 | 结论 | 维护文档 |
|--------|------|----------|
| v1 系统形态 | 模块化单体 | [技术规格](../enterprise-ai-brain/spec.md) |
| 业务主体 | 产品、需求、AI 任务、Bug、知识中心、研发度量/看板和用户洞察（含迭代规划建议）是一等主体或独立运营视图 | [PRD](../../01-prd/enterprise-ai-brain/prd.md) 和 [技术规格](../enterprise-ai-brain/spec.md) |
| 需求任务关系 | 需求审批后生成 AI 任务，任务保存需求快照和产品上下文 | [技术规格](../enterprise-ai-brain/spec.md) |
| AI 任务类型 | v1 MVP 覆盖产品详细设计、技术方案和内部 GitLab MR 代码 Review；后续扩展开发计划、自动化测试、发布评估和上线后分析，统一使用 task_type、状态机、人工确认和审计 | [技术规格](../enterprise-ai-brain/spec.md) |
| 全流程感知 | 需求、设计、代码、Review、测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识和审计通过 lifecycle_context 串联，支持上下游追溯和风险定位 | [技术规格](../enterprise-ai-brain/spec.md) |
| 研发运营数据 | GitLab、Jenkins、线上日志、用户使用、用户反馈、迭代规划建议和 Bug 均按产品/版本/模块归属聚合，支撑首页 IT 团队看板 | [技术规格](../enterprise-ai-brain/spec.md) |
| 代码仓库巡检 | 定时作业通过插件扫描仓库质量/安全/规范问题，结果进入代码巡检报告表并保留提交人维度，严重问题可去重创建 `code_inspection` 来源 Bug，并记录邮件/钉钉机器人通知反馈 | [PRD](../../01-prd/enterprise-ai-brain/prd.md)、[技术规格](../enterprise-ai-brain/spec.md) 和 [API 文档](../enterprise-ai-brain/api.md) |
| AI 编排 | LangGraph | [技术规格](../enterprise-ai-brain/spec.md) |
| 数据存储 | PostgreSQL + pgvector + Redis | [技术规格](../enterprise-ai-brain/spec.md) |
| 知识检索 | PostgreSQL + pgvector 权限过滤，GBrain 提供长期记忆、混合检索和知识图谱补充 | [技术规格](../enterprise-ai-brain/spec.md) |
| 模型接入 | 模型网关，不直连业务代码 | [API 文档](../enterprise-ai-brain/api.md) 和 [技术规格](../enterprise-ai-brain/spec.md) |
| AI 助手 | 助手只通过模型网关 Chat 接入，服务端注入脱敏系统上下文，模型日志仅记录 `purpose=assistant_chat` 元数据 | [API 文档](../enterprise-ai-brain/api.md)、[技术规格](../enterprise-ai-brain/spec.md) 和 [测试用例](../enterprise-ai-brain/test-case.md) |
| 部署 | v1 Docker Compose | [部署 Runbook](../../05-runbooks/deployment.md) |

## 部署架构

```text
Docker Compose
  ├─ web：React 工作台
  ├─ api：FastAPI 服务
  ├─ postgres：PostgreSQL + pgvector
  └─ redis：缓存/队列
```

API 容器启动入口会在服务启动前按顺序执行 `apps/api/app/db/migrations/*.sql`，用于升级已有数据库卷；数据库结构或种子数据变更不得依赖清空 volume。PostgreSQL 服务使用同主版本 pgvector 镜像，避免已有 PG18 数据目录被错误挂载到 PG16。

## 外部依赖

| 服务 | 用途 |
|------|------|
| GBrain | 长期记忆、混合检索、答案合成和知识图谱。 |
| OpenAI-compatible 模型服务 | chat completion 和 embedding。 |
| 本地 GitLab | v1 MVP 拉取 Merge Request 元信息和 diff 快照用于内部代码 Review；v1.2 再采集提交、Merge Request、代码变更量、质量评分和风险摘要，按产品 Git 资源归属。 |
| Jenkins | v1 采集 job、build、部署环境、发布版本、触发人、耗时、状态和失败原因。 |
| 线上运行日志源 | v1 可登记/导入真实聚合指标，后续接入自动采集；聚合错误率、P95 延迟、核心业务事件、top errors 和异常趋势。 |
| 用户使用和反馈数据源 | v1 聚合活跃、功能访问、关键路径转化、异常退出、低使用功能和反馈趋势。 |
| 未来 GitHub/Jira/飞书等系统 | v1 仅预留适配器，默认使用模拟 Issue。 |

## 安全架构

- v1 使用本地账号 + Bearer Token。
- 写操作和任务访问需要鉴权。
- 知识检索必须在数据库查询层完成权限过滤。
- 模型调用日志默认不保存完整 prompt 和输出。
- AI 助手问答使用服务端生成的脱敏 `system_context`；模型调用日志不保存完整用户问题、系统上下文、助手回答或 API Key。
- 所有写操作、AI 高影响动作和研发运营采集结果写入审计事件或运行记录。
- GitLab MR 代码 Review 只读取授权产品 Git 资源和 Merge Request，报告归档在 AI Brain 内部，不回写 GitLab 评论、审批状态或分支变更。
- GitLab、Jenkins 和线上日志登记/导入或采集失败时保留失败原因，不得生成兜底指标；自动采集接入后保留最后成功时间和待归属状态。

## 扩展性设计

v1 不拆微服务，但模块边界保留未来提取点：`graph-runtime-worker`、`knowledge-service`、`long-memory-service`、`model-gateway-service`、`gitlab-review-service`、`code-review-executor-service`、`devops-metrics-worker`、`user-insights-worker`、`iteration-planning-service`、`bug-service`、`dashboard-service`、`integration-service`。

---
最后更新: 2026-06-02
