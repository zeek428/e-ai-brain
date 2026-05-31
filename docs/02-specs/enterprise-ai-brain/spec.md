# 企业 AI 大脑平台技术规格

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.15 |
| 适用系统版本 | ≥ v1.0.0 |
| 文档状态 | Approved |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0.0 | 2026-05-27 | 基于设计文档生成项目级技术规格 | Claude |
| v1.0.1 | 2026-05-27 | 切换为项目级文档维护源，补充产品和平台配置实现边界 | Codex |
| v1.0.2 | 2026-05-28 | 补充四个业务主体生命周期、页面信息架构、需求任务快照和主体级审计约束 | Claude |
| v1.0.3 | 2026-05-29 | 补充 GitLab 代码质量、线上日志运营分析、Jenkins 发布数据、首页看板和 Bug 管理技术设计 | Claude |
| v1.0.4 | 2026-05-29 | 扩展 AI 任务类型为产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估和上线后分析 | Claude |
| v1.0.5 | 2026-05-29 | 强化软件研发全流程感知，补充研发上下文图谱、跨阶段追溯和风险信号设计 | Claude |
| v1.0.6 | 2026-05-29 | 补充用户使用洞察、用户反馈收集和 AI 迭代规划建议技术设计 | Claude |
| v1.0.7 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 提前纳入 v1 MVP，补充 diff 快照、可插拔 code-review 执行器、内部报告归档和不回写 GitLab 约束 | Claude |
| v1.0.8 | 2026-05-29 | 补齐 GitLab MR 快照表、索引、执行器调用协议、超时、schema 校验和审计边界 | Claude |
| v1.1.0 | 2026-05-29 | 对齐 PRD v1.1.0，补充 MVP-A/B/C 实施切片、MVP 角色映射、PRD 草案与产品详细设计边界和文档链接修正 | Claude |
| v1.1.1 | 2026-05-29 | 修复产品评审问题：将 GitLab 只读集成前置到 MVP-A，统一阶段优先级、需求多任务语义、GBrain 边界、审计字段和 diff 限制 | Claude |
| v1.1.2 | 2026-05-31 | 对齐真实 CRUD 删除语义、主数据唯一性约束和需求审批到任务确认的前端主链路 | Codex |
| v1.1.3 | 2026-05-31 | 补齐审计查询过滤和审计列表详情、生命周期追踪页面操作约束 | Codex |
| v1.1.4 | 2026-05-31 | 对齐 code_review 执行器失败状态、错误码和审计事件 | Codex |
| v1.1.5 | 2026-05-31 | 补齐 GitLab MR diff 超限失败审计和快照状态机事件 | Codex |
| v1.1.6 | 2026-05-31 | 补齐 GitLab MR 变更文件数限制和审计指标 | Codex |
| v1.1.7 | 2026-05-31 | 补齐 GitLab MR 单文件 diff 行数限制和审计指标 | Codex |
| v1.1.8 | 2026-05-31 | 明确 MVP 用户角色目录、权限边界、角色字典表和用户管理角色选择约束 | Codex |
| v1.1.9 | 2026-05-31 | 推进产品配置细粒度 PostgreSQL 持久化，产品、版本、模块和 Git 资源同步结构表 | Codex |
| v1.1.10 | 2026-05-31 | 推进需求台账细粒度 PostgreSQL 持久化，需求创建、审批和任务引用同步 `requirements` 结构表 | Codex |
| v1.1.11 | 2026-05-31 | 推进 AI 任务细粒度 PostgreSQL 持久化，任务核心字段同步 `ai_tasks` 结构表 | Codex |
| v1.1.12 | 2026-05-31 | 推进人工确认和 Graph 运行态细粒度 PostgreSQL 持久化，Review、Run 和 Checkpoint 同步结构表 | Codex |
| v1.1.13 | 2026-05-31 | 细化 MVP 用户角色定义，补齐职责、数据范围、决策范围和前端角色目录加载约束 | Codex |
| v1.1.14 | 2026-05-31 | 推进知识文档、知识沉淀候选和审计事件细粒度 PostgreSQL 持久化 | Codex |
| v1.1.15 | 2026-05-31 | 推进 Bug 管理细粒度 PostgreSQL 持久化，Bug 记录同步 `bugs` 结构表 | Codex |

---

## 概述

企业 AI 大脑平台 v1 系列采用基于 Ant Design Pro 模板的 React + TypeScript 前端、FastAPI 后端、LangGraph 工作流、PostgreSQL + pgvector 知识存储、Redis 缓存/队列、GBrain 长期记忆层和 OpenAI-compatible 模型网关，先以模块化单体跑通产品研发大脑从需求审批到产品详细设计、技术方案、内部 GitLab MR 代码 Review、人工确认、内部报告归档和知识沉淀的 MVP 闭环，并通过研发上下文图谱感知需求、设计、代码、测试、发布、线上反馈、用户使用和用户反馈之间的关联与风险。用户洞察、迭代规划建议、自动化测试、完整 Bug 闭环、发布上线评估和上线后分析按后续阶段扩展。

## 设计决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| 系统形态 | 模块化单体 | v1 需要快速闭环和低运维复杂度，保留未来拆分服务边界。 |
| AI 编排 | LangGraph | 支持状态化 Graph、检查点、人机中断和恢复。 |
| 知识检索 | PostgreSQL + pgvector + GBrain | v1 业务知识库使用 PostgreSQL + pgvector；长期记忆和公司大脑能力引入 GBrain 的混合检索、答案合成和知识图谱。 |
| 模型接入 | 模型网关 + OpenAI-compatible API | 业务模块不直接依赖供应商 SDK，便于治理、审计和替换模型。 |
| 回写集成 | 模拟 Issue 优先 | v1 演示闭环，不引入真实外部系统副作用。 |
| 部署方式 | Docker Compose | 满足本地演示和早期部署，避免过早引入 Kubernetes。 |
| 业务主体 | 产品、需求、AI 任务、Bug、知识中心、研发运营指标和用户洞察/迭代规划作为一等主体或独立运营视图 | 避免任务详情页包办主数据、审批、执行、缺陷、知识治理和产品迭代决策，保证长期可维护。 |
| AI 任务类型 | 研发全链路 task_type | v1 MVP 覆盖产品详细设计、技术方案和内部 GitLab MR 代码 Review；后续扩展代码开发辅助、自动化测试、发布上线评估和上线后分析，统一使用状态机、人工确认、审计和回写机制。 |
| GitLab MR Code Review | 内部 GitLab MR 元信息和 diff 快照、可插拔 code-review 执行器、结构化报告和内部归档 | GitLab API + Claude Code `code-review` skill 适配器 |
| 需求任务关系 | 引用 + 快照 | 需求保存业务事实和审批状态，任务保存生成时的需求快照和产品上下文，避免历史任务被后续主数据变更影响。 |
| 研发运营数据 | 产品归属聚合 | GitLab、Jenkins、线上运行日志、Bug、用户使用、用户反馈和首页看板均按产品/版本/模块归属汇总，支撑 IT 团队运营分析和产品迭代规划。 |
| 用户洞察与迭代规划 | AI 建议 + 人工确认 | AI 可以基于产品规划、需求池、使用数据、反馈、Bug、线上日志、发布记录和研发投入生成优先级建议，但正式需求或迭代计划必须由产品负责人确认。 |
| 全流程感知 | 研发上下文图谱 | 将需求、产品详细设计、技术方案、代码提交、代码 Review、自动化测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件以产品/版本/模块/需求/任务为主线串联，支持跨阶段追溯和风险感知。 |

## 实施切片

v1 MVP 技术交付按 MVP-A/B/C 切片推进，三个切片全部通过后才视为 v1 MVP 完整完成：

| 切片 | 技术重点 | 涉及模块 | 主要验证 |
|------|----------|----------|----------|
| MVP-A 基础 + GitLab 输入闭环 | 基础工程、认证、产品配置、内部 GitLab 只读接入、MR 预览、MR diff 快照、需求审批、产品详细设计、技术方案、人工确认、Markdown 导出和基础审计 | auth, product_config, gitlab_review, requirement, ai_task, graph_runtime, review, model_gateway, audit, export | 跑通需求到确认方案的闭环，并能在技术方案后基于授权 GitLab MR 生成不可变输入快照 |
| MVP-B GitLab Review 闭环 | code_review 任务、执行器调用、结构化报告、人工确认、内部归档、diff 超限和执行器失败处理 | code_review_executor, ai_task, graph_runtime, review, audit, gitlab_review | 基于 MVP-A 生成的不可变 MR 快照生成可审计 Review 报告，且不产生 GitLab 写副作用 |
| MVP-C 知识与治理闭环 | 知识导入、索引状态、权限过滤检索、知识沉淀候选审核、模拟 Issue 幂等生成、主体级审计和真实空数据入口 | knowledge, long_memory, integration, audit, dashboard | 任务产出可沉淀、检索有权限过滤；未接入采集器的接口返回空集合，不提供伪造统计数据 |

MVP-A 可以先使用受控模型夹具或最小模型网关完成演示，但必须具备内部 GitLab 只读集成依赖，至少支持授权仓库绑定、MR 预览和不可变 diff 快照；MVP-B 在此基础上引入 code-review 执行器、正式报告生成、人工确认和内部归档。MVP-B 必须补齐执行器失败、diff 过大和不回写 GitLab 的错误语义；MVP-C 补齐知识治理后，MVP 才能对外宣称具备完整闭环。

当前源码实现状态：Docker 本地栈默认以 `PERSISTENCE_MODE=postgres` 启动，登录账号读取 PostgreSQL `users` 表，管理员可通过系统管理下的用户管理维护用户，并可在模型网关配置页维护 OpenAI-compatible 配置；用户角色已收敛为 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 六个 MVP 可分配角色，后端通过 `/api/auth/roles` 暴露角色目录，并返回职责、数据范围、决策范围、权限点、是否可分配和排序信息，用户管理和知识权限选择必须从该接口加载固定多选项而非自由文本录入。产品配置、需求台账、AI 任务、人工确认、Graph 运行态、知识文档、知识沉淀候选、审计事件和 Bug 记录已开始细粒度持久化：产品、版本、模块、Git 资源、需求、AI 任务核心字段、Review、Graph Run、Checkpoint、知识文档、知识沉淀候选、审计事件和 Bug 记录会同步写入 `products`、`product_versions`、`product_modules`、`product_git_repositories`、`requirements`、`ai_tasks`、`human_reviews`、`graph_runs`、`graph_checkpoints`、`knowledge_documents`、`knowledge_deposits`、`audit_events`、`bugs`，同时 `app_state_snapshots` 继续作为未完成细粒度迁移主体的兼容持久化兜底。模型网关列表只显示 `api_key_configured`，不显示明文密钥或密钥片段。存在 active/default 且已配置 API Key 的 OpenAI-compatible 模型网关时，任务启动会通过 `/chat/completions` 调用真实 provider 并要求返回 JSON 对象；模型调用日志只记录 provider、model、purpose、tokens、latency、status、error 和配置 id，不记录 prompt、完整输出或密钥。模型网关配置缺失密钥时任务进入 `failed` 并返回 `MODEL_GATEWAY_CONFIG_INVALID`；非 code_review 任务 provider 调用失败返回 `MODEL_GATEWAY_FAILED`；code_review 报告生成阶段 provider 调用、响应解析或结构化报告校验失败返回 `CODE_REVIEW_EXECUTOR_FAILED`，任务停在 `code_review_executor_failed` 并写入 `code_review.executor_failed` 审计事件，不得静默回退成本地输出。产品配置、需求、知识文档、Bug、用户管理和模型网关配置已具备当前管理页所需 CRUD 能力；产品管理页面通过“配置”弹窗维护产品版本、模块和 Git 资源，Git 凭据仅在新增/编辑时提交，列表只展示 `credential_ref_configured` 对应的配置状态，不回显凭据引用或 token。知识中心已具备独立导入、列表、真实权限过滤检索和沉淀审核入口；任务中心已具备真实产品详细设计启动、Review 确认、技术方案任务创建和 Markdown 导出入口；审计与运行页面支持查看真实审计详情，并从审计主体优先发起生命周期链路追踪。首页 IT 团队看板已基于真实产品、需求、AI 任务、待确认 Review、知识和审计数据返回 MVP 聚合摘要。内部 GitLab MR 预览和 diff 快照已接入 GitLab 只读 API：产品 Git 资源需提供可解析的 `remote_url` 或 `GITLAB_BASE_URL`，凭据引用推荐使用 `env:GITLAB_READONLY_TOKEN`，系统只读取 MR 元信息和 changes，不回写 GitLab。进程内 `MemoryStore` 仅用于测试和未配置模型网关时的显式本地开发 fallback；后续阶段应继续把模型调用日志、GitLab/Code Review 归档、模拟写回和后续运营主体替换为细粒度 PostgreSQL 仓储。DevOps/用户洞察采集器尚未接入；对应列表接口返回空集合，不提供前端本地兜底行或后端伪造统计数据。

### 架构图

```text
用户浏览器
  │
  ▼
React Workbench (Ant Design Pro template)
  │ JSON API / Bearer Token
  ▼
FastAPI Modular Monolith
  ├─ auth
  ├─ brain_app
  ├─ product_config
  ├─ ai_task
  ├─ graph_runtime ── LangGraph
  ├─ review
  ├─ knowledge ───── PostgreSQL + pgvector
  ├─ long_memory ─── GBrain hybrid retrieval + knowledge graph
  ├─ model_gateway ─ OpenAI-compatible provider
  ├─ devops_metrics
  ├─ gitlab_review
  ├─ code_review_executor
  ├─ user_insights
  ├─ iteration_planning
  ├─ lifecycle_context
  ├─ bug
  ├─ dashboard
  ├─ integration ─── mock issues
  ├─ audit
  └─ export
  │
  ├─ PostgreSQL
  └─ Redis
```

### 模块划分

| 模块 | 职责 | 依赖 |
|------|------|------|
| auth | 本地账号、登录、Bearer Token、权限判断 | users |
| brain_app | 业务大脑配置和默认研发大脑 | brain_apps |
| product_config | 产品、版本、模块、Git 资源配置、内部 GitLab 项目绑定和凭据引用 | products, product_versions, product_modules, product_git_repositories |
| requirement | 需求台账、审批和任务生成入口 | requirements, product_config, ai_task |
| ai_task | AI 任务生命周期、任务类型、状态流转、任务详情 | graph_runtime, audit |
| graph_runtime | LangGraph 编译、启动、中断、检查点、恢复 | ai_task, review, model_gateway, code_review_executor |
| review | 人工确认、修改采纳、拒绝、补充信息 | human_reviews |
| knowledge | 文档导入、chunk、embedding、检索、权限过滤 | pgvector, model_gateway |
| long_memory | GBrain 长期记忆、混合检索、答案合成、知识图谱连接器 | knowledge, model_gateway |
| model_gateway | 聊天和 embedding 调用、超时、重试、使用量记录 | 外部模型服务 |
| gitlab_review | 内部 GitLab MR 元信息和 diff 拉取、输入快照、报告归档 | product_config, ai_task, audit |
| code_review_executor | 可插拔代码 Review 执行器，一期默认对接 Claude Code `code-review` skill | graph_runtime, audit |
| integration | 模拟 Issue 回写、幂等控制 | mock_issues |
| audit | 写操作和 AI 关键动作审计 | audit_events |
| export | Markdown 方案导出 | ai_task, graph_run |
| devops_metrics | GitLab 提交、代码质量、Jenkins 发布和线上日志指标采集 | product_config, audit |
| user_insights | 实际业务系统用户使用数据和用户反馈采集、归属、聚合和待归属处理 | product_config, audit |
| iteration_planning | AI 迭代规划建议生成、证据链聚合、人工确认和采纳追踪 | product_config, requirement, bug, devops_metrics, user_insights, lifecycle_context, audit, model_gateway |
| lifecycle_context | 研发上下文图谱、跨阶段追溯、风险信号归集和影响范围分析 | requirement, ai_task, devops_metrics, user_insights, iteration_planning, bug, knowledge, audit |
| bug | AI 自动测试和人工测试 Bug 管理 | product_config, ai_task, devops_metrics, lifecycle_context |
| dashboard | 首页 IT 团队看板指标聚合 | requirement, ai_task, bug, devops_metrics, user_insights, iteration_planning, lifecycle_context, knowledge, audit |

---

### 业务主体边界

| 主体 | 所属模块 | 主要职责 | 与其他主体关系 |
|------|----------|----------|----------------|
| 产品 | product_config | 产品、版本、模块、Git 资源和相关系统上下文维护 | 需求必须选择产品和版本；任务生成时固化产品上下文；知识可按产品/系统归类 |
| 需求 | requirement | 业务问题、目标、约束、审批和任务生成入口 | 审批通过后生成 AI 任务；需求保留原始输入和审批结论 |
| AI 任务 | ai_task, graph_runtime, review | AI 执行、任务类型管理、人工确认、回写、导出和运行聚合 | 引用需求并保存生成时快照；按 task_type 产出产品详细设计、技术方案、开发计划、Review 结论、测试分析、发布评估、上线后分析、mock issue、Markdown、Bug 或知识沉淀候选 |
| 知识中心 | knowledge | 文档导入、索引、检索、权限、沉淀审核和治理 | 为任务提供检索上下文；接收任务沉淀候选；可独立运营 |
| Bug | bug | Bug 登记、分派、修复、验证、关闭和重复归并 | 来源包括 AI 自动测试和人工测试；关联产品、版本、模块、需求、任务、GitLab 提交、Jenkins 发布或线上日志 |
| 研发运营指标 | devops_metrics, dashboard | GitLab 代码质量、提交统计、Jenkins 发布、线上日志和首页 IT 团队看板 | 全部按产品归属聚合，为需求、研发进展、Bug 和线上运营分析提供数据 |
| 用户洞察/迭代规划 | user_insights, iteration_planning | 用户使用数据、用户反馈、AI 迭代规划建议和采纳追踪 | 关联产品规划、需求池、Bug、线上日志、发布记录和研发投入；AI 只生成建议，正式转需求或进入迭代计划前必须由产品负责人确认 |
| 研发上下文图谱 | lifecycle_context | 需求、设计、方案、代码、Review、测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识和审计的跨阶段关系 | 以产品、版本、模块、需求和 AI 任务为主线，支持全流程感知、影响分析和风险定位 |

### PRD 草案与产品详细设计实现边界

需求审批前的轻量需求评估或 PRD 草案预览不是独立 `task_type`，不要求单独 Graph 节点持久化正式产物。正式产品产物由审批后创建的 `product_detail_design` 任务生成，并在 `human_reviews` 中由产品负责人确认。`technical_solution`、`code_review`、Markdown 导出和知识沉淀均应引用已确认的 `product_detail_design` 输出或其快照，避免直接依赖未审批需求草稿。

| task_type | 说明 | 主要输入 | 主要输出 | 关键确认点 |
|-----------|------|----------|----------|------------|
| `product_detail_design` | 产品详细设计 | 已审批需求、产品上下文、历史知识、业务规则 | 详细 PRD、交互说明、页面字段、业务规则、验收标准 | 产品负责人确认 |
| `technical_solution` | 技术方案设计 | 产品详细设计、系统架构、代码仓库上下文、技术规范 | 技术方案、模块边界、接口设计、数据模型、风险依赖 | 研发负责人确认 |
| `development_planning` | 代码开发辅助 | 技术方案、任务拆解、代码仓库上下文 | 开发任务清单、代码变更建议、实现步骤、待修改文件建议 | 研发负责人确认 |
| `code_review` | 内部 GitLab MR 代码 Review | 内部 GitLab MR 元信息和 diff 快照、关联需求、技术方案、产品上下文、项目规范 | 结构化 Review 报告、问题清单、风险等级、文件/行号、修改建议、执行器元数据 | Reviewer 确认 |
| `automated_testing` | 自动化测试 | PRD、验收标准、技术方案、已有测试用例 | 测试用例建议、自动化脚本建议、测试结果分析、Bug 登记建议 | 测试负责人确认 |
| `release_readiness` | 发布上线评估 | 需求、代码质量、测试结果、Bug 状态、Jenkins 发布记录、线上日志历史 | 上线检查清单、风险评估、回滚建议、是否可发布结论 | 发布负责人确认 |
| `post_release_analysis` | 上线后分析 | 线上运行日志、核心业务事件、错误率、延迟、发布版本 | 健康报告、异常趋势、疑似回归 Bug、优化建议 | 运营或研发负责人确认 |

---

### MVP 角色映射

MVP 权限模型以系统角色为准，业务角色通过系统角色和产品归属映射到具体按钮权限：

| 系统角色 | 中文名称 | 主要职责 | 数据范围 | 决策范围 |
|----------|----------|----------|----------|----------|
| `admin` | 系统管理员 | 管理用户、角色、模型网关、审计与系统级配置 | 全平台系统配置、审计事件和授权业务数据 | 账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍 |
| `product_owner` | 产品负责人 | 维护产品上下文、审批需求、生成任务、确认产品详细设计和迭代建议 | 所负责产品、版本和模块下的需求、AI 任务、Bug、知识引用和看板摘要 | 需求审批、产品详细设计确认、迭代规划采纳和产品侧优先级决策 |
| `rd_owner` | 研发负责人 | 创建并启动研发 AI 任务、确认技术方案、处理 Bug 和沉淀研发知识 | 授权产品下的 AI 任务、技术方案、GitLab 只读快照、Bug 和研发知识 | 技术方案确认、研发任务推进、Bug 处理和研发知识沉淀决策 |
| `reviewer` | 评审负责人 | 确认产品详细设计、技术方案或代码 Review 报告，在信息不足时要求补充 | 分配给评审人的 AI 任务、Review 检查点、MR 只读快照和评审报告 | 对高影响 AI 输出执行批准、修改后批准、拒绝或要求补充信息 |
| `knowledge_owner` | 知识负责人 | 导入知识文档、维护权限角色、治理索引和审核知识沉淀候选 | 知识文档、chunk、检索结果、权限角色和知识沉淀候选 | 知识导入、权限配置、索引治理和沉淀候选审核 |
| `viewer` | 查看者 | 查看授权范围内的业务数据、任务结果、知识和看板摘要 | 授权范围内的列表、详情、任务结果、知识检索结果和看板摘要 | 无写入或审批决策权限 |

完整 `tester`、发布负责人和 IT 管理者写权限按 v1.1/v1.2 扩展；MVP 阶段不应为了空状态页面提前实现复杂角色体系。
角色定义的运行时来源是后端角色目录常量，持久化字典为 PostgreSQL `role_definitions` 表；`users.roles` 和知识 `permission_roles` 只允许引用该目录中的角色 code。系统管理/用户管理页面和知识权限配置必须从 `/api/auth/roles` 加载固定多选控件，不能让管理员自由输入未定义角色。

React 工作台应提供十个主入口，而不是只围绕任务详情组织全部能力：

| 主入口 | 目标用户 | 页面能力 |
|--------|----------|----------|
| 首页 IT 团队看板 | 管理者、产品负责人、研发负责人、平台运营 | 需求总览、研发进展、Bug 趋势、线上系统健康、核心业务运行、用户使用趋势、用户反馈趋势、AI 迭代规划建议摘要、发布状态 |
| 产品管理 | admin, 产品负责人 | 产品列表、详情、版本、模块、Git 资源和相关系统维护 |
| 需求管理 | product_owner, rd_owner | 需求列表、新增需求、需求详情、审批、驳回、生成任务、关闭 |
| 任务中心 | rd_owner, 产品/研发/测试/发布负责人 | 任务列表、任务详情、任务类型筛选、待确认弹窗、GitLab MR 选择、MR diff 快照、Review 报告、Review 报告确认、自动化测试、发布上线评估、上线后分析、回写结果、Markdown 导出 |
| Bug 管理 | 测试负责人、研发负责人、产品负责人 | AI 自动测试 Bug、人工登记 Bug、分派、修复、验证、关闭、重复归并 |
| 研发运营看板 | IT 管理者、研发负责人、平台运营 | GitLab 提交与代码质量、Jenkins 发布记录、线上日志指标、用户使用分析、用户反馈分析、待归属数据队列 |
| 用户洞察/迭代规划 | 产品负责人、IT 管理者、研发负责人 | 用户使用趋势、用户反馈列表、AI 迭代规划建议、证据链、优先级、采纳/驳回和转需求入口 |
| 知识中心 | 知识维护者、研发负责人 | 文档导入、索引状态、知识检索、沉淀审核、权限和标签维护 |
| 审计与运行 | admin, 平台运营 | 审计事件、运行记录、健康检查和失败排查 |
| 系统管理 | admin | 用户管理、模型网关配置；模型网关页面只展示 API Key 是否已配置，新增或编辑时可提交密钥，编辑留空表示保留服务端现有密钥 |

任务中心不得依赖前端一键演示数据。MVP-A 的正式页面操作链路为：需求管理审批并生成 `product_detail_design` 任务，任务中心启动任务并通过待确认弹窗确认输出；如人工确认要求补充信息，页面调用 `/api/reviews/{review_id}/request-more-info` 将任务退回 `waiting_more_info`，再通过任务操作弹窗提交 `/api/ai-tasks/{task_id}/more-info` 使任务回到 `draft` 后重新启动。确认通过后可基于已确认产品详细设计创建 `technical_solution` 任务，确认后导出 Markdown。任务列表行内只保留单一“操作”入口，启动、确认、要求补充、提交补充、生成技术方案、导出、创建 Code Review、模拟 Issue 和查看报告均在弹窗内触发；任务操作弹窗采用上方任务摘要、下方纵向操作的结构，不得恢复左右分栏确认台或列表横向堆叠操作按钮，并保持与其他管理页一致的查询表格风格。已完成技术方案可继续通过任务中心选择产品 GitLab 仓库、预览 MR、生成 diff 快照并创建 `code_review` 任务；Review 报告在内部页面查看和人工确认，仍不得回写 GitLab。MVP-C 的任务列表应提供已完成任务的模拟 Issue 查询/生成入口，知识中心应提供沉淀候选审核入口，二者均调用真实后端接口且不得展示兜底示例数据。

## 数据库设计

### ER 图

```text
users ──< requirements
  │
  ├── ai_tasks ──> brain_apps
  │          │
  │          ├── graph_runs
  │          ├── human_reviews
  │          ├── mock_issues
  │          ├── knowledge_deposits
  │          └── audit_events
  │
  ├── products ──< product_versions
  │          ├── product_modules
  │          ├── product_git_repositories
  │          ├── gitlab_daily_code_metrics
  │          ├── jenkins_release_records
  │          ├── online_log_metrics
  │          ├── user_usage_metrics
  │          ├── user_feedback_items
  │          ├── iteration_plan_suggestions
  │          ├── iteration_plan_decisions
  │          ├── lifecycle_context_edges
  │          ├── lifecycle_risk_signals
  │          ├── bugs
  │          └── dashboard_metric_snapshots
  │
  ├── related_systems
  └── model_gateway_configs

knowledge_documents ──< knowledge_chunks

requirements ──< ai_tasks
```

### 核心表结构

| 表名 | 说明 | 关键约束 |
|------|------|----------|
| role_definitions | 系统角色字典 | `code` 主键；记录 `category`、`responsibilities`、`data_scope`、`decision_scope`、`permissions`、`is_assignable` 和 `sort_order`；MVP 可分配角色为 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer`。 |
| users | 本地用户和角色 | email 唯一。 |
| brain_apps | 业务大脑配置 | `code` 唯一，v1 默认 `rd_brain`。 |
| products | 产品配置 | `code` 唯一，提交需求必须选择启用产品。 |
| product_versions | 产品版本 | 同一产品内 `code` 唯一，已归档版本不可用于新任务。 |
| product_modules | 产品模块 | 同一产品内 `code` 唯一，模块可选。 |
| product_git_repositories | 产品 Git 资源 | 记录代码、文档、PRD、测试仓库上下文；内部 GitLab 资源需保存 base_url、project_id 或 project_path、默认分支、凭据引用和启用状态。 |
| requirements | 需求实体 | 状态为 `draft / pending_approval / approved / rejected / task_created / closed`；`task_created` 表示已至少创建一个关联任务，不是终态，仍可在满足前置条件时继续创建技术方案、code_review 或后续阶段任务。 |
| related_systems | 相关系统配置 | `code` 唯一，可写入任务输入上下文。 |
| model_gateway_configs | 平台模型网关配置 | 支持一个默认启用配置，API 响应只返回 API Key 是否已配置，不返回明文或密钥片段。 |
| model_gateway_logs | 模型调用日志 | 只记录 provider、model、purpose、tokens、latency、status、error 等元数据，不保存完整 prompt 或完整输出。 |
| ai_tasks | 用户可见 AI 任务 | 状态必须匹配统一任务状态机；`task_type` 标识产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估或上线后分析；`input_json` 保存需求快照、产品上下文、启动参数和内部 GitLab MR Review 输入快照引用。 |
| gitlab_mr_snapshots | 内部 GitLab MR 输入快照 | 记录 repository_id、project_id 或 project_path、mr_iid、title、author、source/target branch、base/head sha、diff_refs、changed_files_summary、diff_storage_ref、diff_size_bytes、snapshot_hash、requirement_id、technical_solution_task_id、created_by 和 created_at；快照不可变，重新 Review 必须创建新快照。 |
| code_review_reports | 代码 Review 报告 | 记录 task_id、GitLab MR 快照、执行器元数据、summary、risk_level、findings、人工确认状态和内部归档时间；v1 MVP 不回写 GitLab。 |
| graph_runs | LangGraph 运行记录 | 保存 checkpoint/state snapshot 引用。 |
| human_reviews | 人工确认记录 | `version` 用于乐观锁。 |
| knowledge_documents | 知识文档 | 记录来源、权限和索引状态，支持主动导入、索引失败重试和归档。 |
| knowledge_chunks | 知识切片 | embedding 维度必须匹配配置模型。 |
| mock_issues | 模拟回写 Issue | idempotency key 唯一。 |
| knowledge_deposits | 知识沉淀候选 | `ai_task_id + deposit_type + content_hash` 去重。 |
| audit_events | 审计事件 | 记录任务、主体类型、主体 ID、事件类型、操作者、事件载荷、写入序号和创建时间。 |
| gitlab_daily_code_metrics | GitLab 每日代码指标 | 按 product_id、repository_id、commit_date 聚合提交、人员、质量和风险摘要。 |
| jenkins_release_records | Jenkins 发布记录 | 按 product_id、version_id、job_name、build_id 记录构建、部署、失败原因和触发人。 |
| online_log_metrics | 线上运行日志指标 | 按 product_id、module_code、environment、time_window 聚合错误率、延迟和核心业务事件。 |
| user_usage_metrics | 用户使用指标 | 按 product_id、module_code、feature_code、user_segment、time_window 聚合活跃、访问、转化、停留、异常退出和低使用功能。 |
| user_feedback_items | 用户反馈记录 | 记录来源渠道、反馈类型、满意度或情绪倾向、标签、关联产品模块和处理状态。 |
| iteration_plan_suggestions | AI 迭代规划建议 | 记录规划周期、建议需求、推荐理由、证据链、业务价值、风险信号、依赖条件、预估研发投入、建议优先级和置信度。 |
| iteration_plan_decisions | 迭代规划确认记录 | 记录产品负责人对建议的采纳、修改后采纳或驳回决定，可关联转化后的正式需求。 |
| lifecycle_context_edges | 研发上下文关系边 | 记录 source_subject 与 target_subject 的关系、置信度、来源模块和时间，用于跨阶段追溯。 |
| lifecycle_risk_signals | 全流程风险信号 | 记录需求变更、设计缺口、代码质量、Review、测试、Bug、发布和线上异常等风险信号。 |
| bugs | Bug 记录 | 来源为 `ai_auto_test / manual_test`，状态流转覆盖分派、修复、验证和关闭。 |
| dashboard_metric_snapshots | 首页看板快照 | 保存按产品、时间窗口聚合的需求、研发进展、Bug、发布和线上运行统计。 |

### P0 字段级 Schema

以下字段级 schema 是实现、API DTO、迁移规划和测试夹具的逻辑基线，不替代实际 migration。

#### requirements

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| brain_app_id | string | 是 | 关联业务大脑，例如 `rd_brain`。 |
| product_id | string | 是 | 关联产品。 |
| version_id | string | 是 | 关联未归档产品版本。 |
| module_code | string | 否 | 关联产品模块。 |
| title | string | 是 | 非空，建议 1-120 字。 |
| description | text | 是 | 原始需求描述。 |
| status | enum | 是 | `draft`、`pending_approval`、`approved`、`rejected`、`task_created`、`closed`。 |
| priority | enum/string | 否 | 业务优先级。 |
| created_by | string | 是 | 创建人用户 ID。 |
| approved_by | string | 否 | 审批人用户 ID。 |
| approved_at | datetime | 否 | ISO 8601。 |
| rejection_reason | text | 否 | rejected 时必填。 |
| created_at | datetime | 是 | ISO 8601。 |
| updated_at | datetime | 是 | ISO 8601。 |

#### ai_tasks

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| requirement_id | string | 否 | 来源需求，可为空以支持独立任务。 |
| task_type | enum | 是 | `product_detail_design`、`technical_solution`、`development_planning`、`code_review`、`automated_testing`、`release_readiness`、`post_release_analysis`。 |
| title | string | 是 | 非空。 |
| status | enum | 是 | `draft`、`running`、`waiting_more_info`、`waiting_review`、`writing_back`、`completed`、`failed`、`cancelled`。 |
| product_id | string | 是 | 产品归属。 |
| version_id | string | 是 | 任务创建时的版本归属。 |
| module_code | string | 否 | 模块归属。 |
| requirement_snapshot | json | 否 | 任务生成时的需求快照。 |
| product_context | json | 是 | 任务生成时的产品上下文。 |
| input_json | json | 是 | 启动参数、MR 快照引用等输入。 |
| output_json | json | 否 | 结构化输出。 |
| current_step | string | 否 | Graph 当前节点。 |
| error_code | string | 否 | failed 时的错误码。 |
| error_message | string | 否 | 可展示错误摘要，不含敏感信息。 |
| created_by | string | 是 | 创建人。 |
| created_at | datetime | 是 | ISO 8601。 |
| updated_at | datetime | 是 | ISO 8601。 |

#### human_reviews

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| ai_task_id | string | 是 | 关联 AI 任务。 |
| review_type | string | 是 | 产品详细设计、技术方案、code_review 报告等确认类型。 |
| status | enum | 是 | `pending`、`approved`、`edited_approved`、`rejected`、`requested_more_info`、`cancelled`。 |
| version | integer | 是 | 乐观锁版本，从 1 开始递增。 |
| original_content | json/text | 是 | AI 原始输出摘要或结构化内容。 |
| edited_content | json/text | 否 | 修改后采纳内容。 |
| decision_reason | text | 否 | 驳回或要求补充信息时必填。 |
| reviewer_id | string | 否 | 处理人。 |
| decided_at | datetime | 否 | ISO 8601。 |
| created_at | datetime | 是 | ISO 8601。 |

#### gitlab_mr_snapshots

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| repository_id | string | 是 | 产品 Git 资源 ID。 |
| product_id | string | 是 | 产品归属。 |
| project_id | string | 否 | GitLab project id。 |
| project_path | string | 否 | project_id 不可用时记录路径。 |
| mr_iid | integer/string | 是 | GitLab MR IID。 |
| title | string | 是 | MR 标题。 |
| author | string | 否 | MR 作者。 |
| source_branch | string | 是 | 来源分支。 |
| target_branch | string | 是 | 目标分支。 |
| base_sha | string | 否 | diff base sha。 |
| head_sha | string | 是 | 快照时 head sha。 |
| diff_refs | json | 否 | GitLab diff refs。 |
| changed_files_summary | json | 是 | 文件数量、扩展名和路径摘要。 |
| diff_storage_ref | string | 是 | diff 内容存储引用，不直接暴露完整 diff。 |
| diff_size_bytes | integer | 是 | 用于上限判断。 |
| snapshot_hash | string | 是 | 快照内容哈希。 |
| created_by | string | 是 | 创建人。 |
| created_at | datetime | 是 | ISO 8601。 |

#### code_review_reports

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| ai_task_id | string | 是 | 关联 code_review 任务。 |
| gitlab_mr_snapshot_id | string | 是 | 关联不可变 MR 快照。 |
| executor_type | string | 是 | 例如 `claude_code_skill`。 |
| executor_name | string | 是 | 例如 `code-review`。 |
| executor_version | string | 否 | 执行器版本或配置摘要。 |
| summary | text | 是 | Review 总结。 |
| risk_level | enum | 是 | `low`、`medium`、`high`、`critical`。 |
| findings | json | 是 | 文件、行号、严重级别、建议。 |
| status | enum | 是 | `draft`、`pending_review`、`confirmed`、`failed`。 |
| archived_at | datetime | 否 | 人工确认后归档时间。 |
| error_code | string | 否 | 执行器失败时记录。 |
| created_at | datetime | 是 | ISO 8601。 |

#### knowledge_documents

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| brain_app_id | string | 是 | 业务大脑归属。 |
| product_id | string | 否 | 产品权限过滤上下文。 |
| version_id | string | 否 | 版本上下文。 |
| title | string | 是 | 文档标题。 |
| source_type | enum/string | 是 | 上传、导入、任务沉淀等来源。 |
| permission_scope | json | 是 | 角色、用户、产品或版本权限。 |
| index_status | enum | 是 | `importing`、`pending_index`、`indexed`、`index_failed`、`archived`。 |
| index_error | text | 否 | 索引失败摘要。 |
| created_by | string | 是 | 创建人。 |
| created_at | datetime | 是 | ISO 8601。 |
| updated_at | datetime | 是 | ISO 8601。 |

#### knowledge_chunks

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| document_id | string | 是 | 关联知识文档。 |
| chunk_index | integer | 是 | 同一文档内递增。 |
| content | text | 是 | 切片内容。 |
| content_hash | string | 是 | 去重和重建索引用。 |
| embedding | vector | 是 | pgvector，维度与 embedding 模型配置一致。 |
| metadata | json | 否 | 页码、标题层级、来源 URL 等。 |
| permission_scope | json | 是 | 查询层权限过滤冗余字段。 |
| created_at | datetime | 是 | ISO 8601。 |

#### audit_events

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | text/string | 是 | 主键，当前实现使用 `audit_001` 形式的稳定字符串 ID。 |
| ai_task_id | string | 否 | 关联任务。 |
| subject_type | string | 是 | `product`、`requirement`、`ai_task`、`review`、`knowledge_document` 等。 |
| subject_id | string | 是 | 主体 ID。 |
| event_type | string | 是 | 例如 `ai_task.created`、`review.submitted`。 |
| actor_id | string | 是 | 操作者 ID 或系统标识。 |
| payload | json | 是 | 事件摘要，不含完整 prompt、模型输出或密钥。 |
| sequence | integer | 是 | 进程内审计事件顺序号，用于列表倒序和计数器恢复。 |
| created_at | datetime | 是 | ISO 8601。 |

### 研发上下文关系与风险信号

`lifecycle_context_edges` 用于表达跨阶段关系，建议字段包括：

| 字段 | 说明 |
|------|------|
| source_subject_type/source_subject_id | 来源主体，例如 requirement、ai_task、git_commit、review、test_run、bug、release、online_log_event、usage_metric、user_feedback、iteration_plan_suggestion、knowledge_deposit。 |
| target_subject_type/target_subject_id | 目标主体。 |
| relation_type | 关系类型，例如 `implements`、`reviews`、`tests`、`blocks`、`released_by`、`caused_by`、`mitigated_by`、`documents`。 |
| product_id/version_id/module_code | 产品归属上下文。 |
| confidence | 自动归因置信度。 |
| source_module | 关系来源模块，例如 requirement、graph_runtime、devops_metrics、bug、audit。 |
| observed_at | 关系观测时间。 |

`lifecycle_risk_signals` 用于表达跨阶段风险，建议字段包括：

| 字段 | 说明 |
|------|------|
| risk_type | 风险类型，例如 requirement_changed、design_gap、quality_drop、review_blocker、test_failed、critical_bug_open、release_failed、online_regression、conversion_drop、low_feature_usage、negative_feedback_spike、weak_requirement_evidence。 |
| severity | blocker、critical、major、minor。 |
| product_id/version_id/module_code | 产品归属上下文。 |
| requirement_id/ai_task_id | 关联需求和任务，可为空。 |
| source_subject_type/source_subject_id | 风险来源主体。 |
| impact_summary | 影响范围摘要。 |
| recommendation | 下一步建议。 |

### 审计事件 Schema

当前审计事件以 `audit_events` 表和 `/api/audit/events` 响应为准：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid/string | 审计事件 ID。 |
| ai_task_id | uuid/string/null | 关联 AI 任务，可为空。 |
| subject_type | string | 被审计主体类型，例如 `product`、`requirement`、`ai_task`、`knowledge_document`、`knowledge_deposit`。无明确业务主体时使用 `system` 或 `runtime` 等显式主体类型。 |
| subject_id | uuid/string | 被审计主体 ID。无明确业务主体时使用稳定的系统主体 ID，例如 `system`、`runtime` 或具体运行记录 ID。 |
| event_type | string | 事件类型，例如 `ai_task.created`、`review.submitted`。 |
| actor_id | string | 操作者 ID 或系统标识。 |
| payload | object | 事件载荷，对应数据库 `payload`。 |
| sequence | integer | 审计事件顺序号。 |
| created_at | timestamptz/string | 创建时间。 |

API envelope 的 `trace_id` 用于请求追踪，不作为当前审计事件字段持久化。主体级审计字段用于跨产品、需求、任务和知识中心追踪关键写操作。`/api/audit/events` 至少支持按 `ai_task_id`、`subject_type`、`subject_id`、`event_type`、`actor_id`、`created_from` 和 `created_to` 组合过滤；页面链路追踪应优先使用审计主体，缺少主体时才回退到关联 AI 任务。

### 索引设计

| 表名 | 索引名 | 字段 | 类型 | 用途说明 |
|------|--------|------|------|----------|
| requirements | idx_requirements_status | status | 普通索引 | 需求列表状态过滤。 |
| requirements | idx_requirements_product_id | product_id | 普通索引 | 按产品查询需求。 |
| requirements | idx_requirements_created_at | created_at | 普通索引 | 按创建时间倒序查询。 |
| ai_tasks | idx_ai_tasks_status | status | 普通索引 | 任务列表状态过滤。 |
| ai_tasks | idx_ai_tasks_task_type | task_type | 普通索引 | 按 AI 任务类型筛选任务列表。 |
| ai_tasks | idx_ai_tasks_brain_app | brain_app_id | 普通索引 | 按业务大脑查询任务。 |
| graph_runs | idx_graph_runs_task | ai_task_id | 普通索引 | 查询任务运行记录。 |
| human_reviews | idx_human_reviews_task | ai_task_id | 普通索引 | 查询任务确认点。 |
| knowledge_chunks | idx_knowledge_chunks_embedding | embedding | vector index | 向量相似度检索。 |
| mock_issues | uk_mock_issues_idempotency | idempotency_key | 唯一索引 | 防重复回写。 |
| knowledge_deposits | uk_knowledge_deposit_hash | ai_task_id, deposit_type, content_hash | 唯一索引 | 防重复沉淀。 |
| audit_events | idx_audit_events_ai_task_id | ai_task_id | 普通索引 | 按任务查询审计事件。 |
| audit_events | idx_audit_events_event_type | event_type | 普通索引 | 按事件类型排查。 |
| audit_events | idx_audit_events_created_at | created_at | 普通索引 | 按时间倒序查询。 |
| gitlab_daily_code_metrics | idx_gitlab_metrics_product_date | product_id, commit_date | 普通索引 | 首页看板按产品查询提交与质量趋势。 |
| jenkins_release_records | idx_jenkins_release_product_time | product_id, deployed_at | 普通索引 | 查询产品发布历史。 |
| online_log_metrics | idx_online_log_product_window | product_id, environment, window_start | 普通索引 | 查询线上运行趋势。 |
| user_usage_metrics | idx_user_usage_product_window | product_id, module_code, feature_code, window_start | 普通索引 | 查询产品、模块和功能使用趋势。 |
| user_feedback_items | idx_user_feedback_product_status | product_id, module_code, status, created_at | 普通索引 | 查询用户反馈处理状态和趋势。 |
| iteration_plan_suggestions | idx_iteration_plan_product_cycle | product_id, planning_cycle, priority_score | 普通索引 | 查询产品下阶段迭代建议。 |
| iteration_plan_decisions | idx_iteration_plan_decision_suggestion | suggestion_id, decided_at | 普通索引 | 查询迭代建议采纳或驳回记录。 |
| gitlab_mr_snapshots | idx_gitlab_mr_snapshots_repo_mr | repository_id, mr_iid, created_at | 普通索引 | 查询同一 MR 的历史 Review 输入快照。 |
| gitlab_mr_snapshots | uk_gitlab_mr_snapshot_hash | repository_id, snapshot_hash | 唯一索引 | 防止同一仓库相同 diff 快照重复入库。 |
| code_review_reports | idx_code_review_reports_task | task_id, archived_at | 普通索引 | 查询任务关联的内部 Review 报告归档。 |
| bugs | idx_bugs_product_status | product_id, status | 普通索引 | 查询产品 Bug 状态分布。 |
| bugs | idx_bugs_source | source | 普通索引 | 区分 AI 自动测试和人工测试来源。 |
| dashboard_metric_snapshots | idx_dashboard_product_window | product_id, window_start, window_end | 普通索引 | 首页看板读取产品快照。 |
| lifecycle_context_edges | idx_lifecycle_edges_source | source_subject_type, source_subject_id | 普通索引 | 从任一主体查下游关联。 |
| lifecycle_context_edges | idx_lifecycle_edges_target | target_subject_type, target_subject_id | 普通索引 | 从任一主体查上游依据。 |
| lifecycle_risk_signals | idx_lifecycle_risk_product | product_id, severity, observed_at | 普通索引 | 首页看板和全流程感知视图读取风险。 |

### 数据迁移

首个初始化脚本位于 `apps/api/app/db/migrations/001_init.sql`，负责 pgvector 扩展和核心表初始化。后续迁移按模块追加，例如 `002_persistence_users.sql` 补齐用户表种子数据和 `app_state_snapshots` 持久化快照表，`003_role_definitions.sql` 补齐角色字典，`004_knowledge_audit_persistence.sql` 让已有环境的 `audit_events.id` 支持字符串审计 ID 并补齐 `sequence`。当前产品、版本、模块、Git 资源、需求、AI 任务、Review、Graph Run、Checkpoint、知识文档、知识沉淀候选、审计事件和 Bug 记录会同步到对应结构表，并在启动时用结构表覆盖快照中的同类集合；模型调用日志、GitLab/Code Review 归档、模拟写回和后续运营主体仍按后续切片逐步替换为细粒度仓储。已有环境必须通过可重复执行的 SQL 迁移脚本升级，不得通过清空 PostgreSQL 数据卷绕过迁移问题；PostgreSQL 镜像升级必须保持和数据目录相同的主版本，例如现有 PG18 数据卷使用 PG18 + pgvector 镜像，不能直接切到 PG16；回滚脚本不得破坏生产数据。

---

## API 设计

详见 [api.md](./api.md)。

### 接口清单

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 健康检查 | GET | /health | API 存活检查。 |
| 业务大脑列表 | GET | /api/brain-apps | 查询可用业务大脑。 |
| 产品列表 | GET | /api/products | 查询产品配置。 |
| 产品维护 | POST/PATCH/DELETE | /api/products, /api/products/{product_id} | 管理产品，产品编码唯一；删除前校验需求、AI 任务和 Bug 业务依赖，无业务依赖时级联清理版本、模块和 Git 资源配置。 |
| 产品版本 | GET/POST/PATCH/DELETE | /api/products/{product_id}/versions, /api/product-versions/{version_id} | 管理产品版本，同一产品内版本编码唯一，删除前校验需求、AI 任务和 Bug 依赖。 |
| 产品模块 | GET/POST/PATCH/DELETE | /api/products/{product_id}/modules, /api/product-modules/{module_id} | 管理产品模块，同一产品内模块编码唯一，删除前校验需求、AI 任务和 Bug 依赖。 |
| 产品 Git 资源 | GET/POST/PATCH/DELETE | /api/products/{product_id}/git-repositories, /api/product-git-repositories/{repo_id} | 管理产品仓库资源。 |
| 相关系统 | GET/POST/PATCH/DELETE | /api/system/related-systems, /api/system/related-systems/{system_id} | 管理相关系统配置。 |
| 模型网关配置 | GET/POST/PATCH/DELETE | /api/system/model-gateway-configs, /api/system/model-gateway-configs/{config_id} | 管理平台默认模型网关。 |
| 模型调用日志 | GET | /api/model-gateway/logs | 查询模型调用元数据，不返回完整 prompt、输出或密钥。 |
| 需求列表 | GET | /api/requirements | 查询需求台账。 |
| 需求维护 | POST/PATCH/DELETE | /api/requirements, /api/requirements/{id} | 创建、更新待审批/已驳回需求，删除未生成任务的需求。 |
| 需求审批 | POST | /api/requirements/{id}/approve, /api/requirements/{id}/reject | 审批通过或驳回需求。 |
| 生成 AI 任务 | POST | /api/requirements/{id}/generate-task | 审批通过后基于需求实体生成 AI 任务。 |
| 创建 AI 任务 | POST | /api/ai-tasks | 低层任务创建接口，前端默认通过需求实体生成。 |
| 启动 AI 任务 | POST | /api/ai-tasks/{id}/start | 启动 LangGraph。 |
| 任务列表 | GET | /api/ai-tasks | 查询任务列表。 |
| 任务详情 | GET | /api/ai-tasks/{id} | 查询任务状态、结果和确认点。 |
| 补充信息 | POST | /api/ai-tasks/{id}/more-info | 提交补充信息并将任务回到 `draft`。 |
| 取消任务 | POST | /api/ai-tasks/{id}/cancel | 取消任务并关闭待确认。 |
| 待确认列表 | GET | /api/reviews/pending | 查询当前待确认项。 |
| 确认详情 | GET | /api/reviews/{id} | 查询确认详情。 |
| 确认处理 | POST | /api/reviews/{id}/approve | 采纳 AI 输出。 |
| 修改后采纳 | POST | /api/reviews/{id}/edit-approve | 使用人工修改继续。 |
| 驳回重跑 | POST | /api/reviews/{id}/reject | 标记为失败，等待人工重新启动。 |
| 要求补充信息 | POST | /api/reviews/{id}/request-more-info | 将任务退回补充信息状态。 |
| 知识文档 | GET/POST/PATCH/DELETE | /api/knowledge/documents, /api/knowledge/documents/{document_id} | 查询、导入、更新和删除知识文档。 |
| 知识搜索 | POST | /api/knowledge/search | 权限过滤后的混合检索。 |
| 知识沉淀 | GET/POST | /api/knowledge/deposits, /api/knowledge/deposits/{deposit_id}/approve, /api/knowledge/deposits/{deposit_id}/reject | 查询、采纳或驳回知识候选。 |
| Markdown 导出 | GET | /api/export/tasks/{task_id}/markdown | 导出已完成任务方案，权限与任务读取权限一致。 |
| 审计事件 | GET | /api/audit/events | 查询审计事件。 |
| GitLab 代码质量 | GET | /api/devops/gitlab/daily-code-metrics | 查询按产品归属的每日提交和代码质量。 |
| GitLab MR 预览 | GET | /api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview | 读取内部 GitLab MR 标题、作者、分支、变更文件数和 diff refs。 |
| GitLab MR diff 快照 | POST | /api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot | 拉取 MR 元信息和 diff，生成 code_review 任务输入快照。 |
| Code Review 报告 | GET | /api/ai-tasks/{id}/code-review-report | 查询内部 GitLab MR 代码 Review 报告、执行器信息和确认状态。 |
| Jenkins 发布 | GET | /api/devops/jenkins/releases | 查询按产品和版本归属的发布记录。 |
| 线上运行日志 | GET | /api/ops/online-log-metrics | 查询产品运营状态、错误率、延迟和核心业务事件。 |
| Bug 管理 | GET/POST/PATCH/DELETE | /api/bugs, /api/bugs/{bug_id} | 查询、登记、更新和删除 Bug。 |
| 全流程感知 | GET | /api/lifecycle/context | 查询研发上下文关系、上下游影响和风险信号。 |
| 首页看板 | GET | /api/dashboard/it-team | 查询 IT 团队首页指标。 |
| 用户使用指标 | GET | /api/insights/usage-metrics | 查询产品、模块、功能和用户群体维度的使用趋势。 |
| 用户反馈 | GET/POST/PATCH | /api/insights/user-feedback, /api/insights/user-feedback/{feedback_id} | 查询、登记和更新用户反馈。 |
| 迭代规划建议 | GET/POST | /api/planning/iteration-suggestions | 查询或生成 AI 迭代规划建议。 |
| 迭代规划确认 | POST | /api/planning/iteration-suggestions/{suggestion_id}/decide | 产品负责人确认、修改后采纳或驳回迭代规划建议。 |

---

## 实现细节

### 模块 A: graph_runtime

**职责**: 管理研发大脑 Graph 的生命周期。

**核心逻辑**:
```text
receive_requirement
→ select_task_type
→ retrieve_context
→ generate_clarifying_questions
→ is_information_enough
→ wait_for_more_info
→ run_task_type_node
→ interrupt_for_human_review
→ writeback_mock_issues_or_results
→ prepare_knowledge_deposits
→ complete_archive

Task type nodes:
product_detail_design
technical_solution
development_planning
code_review
automated_testing
release_readiness
post_release_analysis
```

### 模块 B: knowledge

**职责**: 文档导入、切片、embedding、检索和权限过滤。

**接口定义**:
```text
KnowledgeRetriever.search(query, brain_app_code, user_id, filters, top_k)
```

### 模块 B2: long_memory

**职责**: 对接 GBrain 作为长期记忆和公司大脑层，提供跨任务、跨来源的混合检索、答案合成和知识图谱查询能力。

**边界规则**:
- v1 业务知识文档、权限、chunk 和沉淀审核仍以本项目 `knowledge` 模块和 PostgreSQL 为准。
- GBrain 不替代产品、需求、AI 任务、人工确认和审计等业务数据库。
- MVP-A 不阻塞于 GBrain 部署；未配置 GBrain 时 `long_memory` 返回明确的 `not_configured` 能力状态，Graph 继续使用 PostgreSQL + pgvector 知识检索。
- MVP-C 可把 GBrain 作为可选长期记忆补充层接入；只有在环境明确配置 GBrain 连接器时，任务才查询 GBrain。
- 进入 AI 工作流的 GBrain 结果必须保留来源引用，并经过本项目权限策略校验。
- 后续可通过连接器把授权知识源同步到 GBrain，或在知识检索阶段把 GBrain 作为长期记忆补充召回源。

**建议接口**:
```text
LongMemoryRetriever.search(query, user_id, filters, top_k)
LongMemoryRetriever.think(query, user_id, filters)
LongMemoryGraph.query(entity_or_relation, user_id, filters)
```

### 模块 B3: devops_metrics

**职责**: 采集和聚合本地 GitLab、Jenkins 和线上运行日志数据，按产品、版本、模块和时间窗口形成研发运营指标。

**核心规则**:
- GitLab 数据按 `product_git_repositories` 归属到产品，统计每日提交、人员提交情况、Merge Request、代码变更量和代码质量审核摘要。
- Jenkins 发布数据按产品和版本归属，记录 job、build_id、部署环境、发布版本、触发人、耗时、状态和失败原因。
- 线上运行日志按产品、模块、环境和时间窗口聚合，记录错误率、接口延迟、核心业务事件数量和异常趋势。
- 无法映射产品归属的数据进入待归属队列，不进入产品级看板统计。

### 模块 B3.0: gitlab_review

**职责**: 支撑 v1 MVP 内部 GitLab MR 代码 Review 闭环，读取 MR 元信息和 diff，生成不可变输入快照，并归档经人工确认的 Review 报告。

**核心规则**:
- 只能读取产品已绑定且当前用户有权限的内部 GitLab 项目和 Merge Request。
- MR 快照至少保存 project_id 或 project_path、mr_iid、标题、作者、source/target branch、commit sha 或 diff refs、变更文件摘要、diff 内容或存储引用、GitLab Web URL 和快照时间。
- MR 快照一经生成不得被 GitLab 后续变更静默覆盖；重新 Review 必须重新拉取并记录新的运行或快照。
- 同一 repository_id 和 snapshot_hash 不应重复入库；重复拉取相同 diff 时可返回已有 snapshot_id，并写入可追踪审计事件。
- v1 MVP 不向 GitLab 回写评论、审批状态、request changes、合并状态或分支变更。
- GitLab 项目未绑定、MR 不存在、权限不足、diff 过大、API 超时或限流时，任务进入 `failed` 或 `waiting_more_info` 并保留可操作错误原因。

### 模块 B3.0.1: code_review_executor

**职责**: 提供可插拔代码 Review 执行器边界，一期默认适配 Claude Code `code-review` skill，后续可替换为其他执行器。

**核心规则**:
- 执行器输入只包含 MR diff、需求/技术方案摘要、产品上下文和必要项目规范，不包含 GitLab token、无关仓库内容或用户级隐私数据。
- 执行器输出必须通过结构化 schema 校验，至少包含 summary、overall risk、findings、severity、category、file path、line/range、suggestion、confidence 和 executor metadata。
- 执行器失败时记录 executor_type、executor_name、错误码、trace_id、失败阶段和 retryable 标识。
- Review 报告进入 `human_reviews` 后，只有人工确认或修改后采纳才可归档为正式 Review 结论。

**调用协议**:
| 项目 | 约束 |
|------|------|
| 调用位置 | v1 MVP 可由 `graph_runtime` 同步调用执行器适配器；后续可迁移到 worker，但 API 契约不变。 |
| 输入来源 | 只允许引用 `gitlab_mr_snapshots` 的不可变 diff 快照，以及已确认需求、产品详细设计、技术方案和项目规范摘要。 |
| 输入限制 | 默认限制：单个 MR diff 不超过 200 KB、变更文件数不超过 50、单文件 diff 不超过 2,000 行；超过任一限制返回 `GITLAB_MR_DIFF_TOO_LARGE`，不得静默截断后继续生成正式报告。实现可通过配置收紧或放宽阈值，但 API 必须返回实际限制和当前 diff 指标。 |
| 超时 | 单次执行器调用必须有超时配置；超时后任务进入 `failed` 或可重试失败状态，并记录 `CODE_REVIEW_EXECUTOR_FAILED`。 |
| 输出校验 | 执行器输出必须先做 JSON/schema 校验，再写入 `code_review_reports`；校验失败按执行器失败处理。 |
| 审计 | MR 快照创建、执行器开始、执行器失败、报告生成、人工确认和报告归档都必须写入审计事件。 |
| 副作用 | 执行器不得接收 GitLab token，不得调用 GitLab 写接口，不得修改仓库、分支、MR 评论或审批状态。 |

### 模块 B3.1: user_insights

**职责**: 采集实际业务系统用户使用数据和用户反馈，按产品、模块、功能、用户群体和时间窗口聚合，为产品洞察、全流程感知和迭代规划提供证据。

**核心规则**:
- 用户使用数据至少聚合活跃用户、功能访问、关键路径转化、功能停留、异常退出和低使用功能。
- 用户反馈必须记录来源渠道、反馈类型、满意度或情绪倾向、标签、关联产品模块和处理状态。
- 使用数据和反馈均需保留产品、模块、功能、用户群体和时间窗口上下文；无法归属的数据进入待归属队列。
- 用户级明细不得进入 AI prompt 或看板默认响应，规划和看板默认使用聚合统计或脱敏摘要。

### 模块 B3.2: iteration_planning

**职责**: 基于产品规划、需求池、用户使用、用户反馈、Bug、线上日志、发布记录和研发投入生成 AI 迭代规划建议，并记录产品负责人的确认、修改后采纳或驳回决定。

**核心规则**:
- 每条建议必须包含推荐理由、证据链、业务价值、风险信号、依赖条件、预估研发投入、建议优先级和置信度。
- 证据链可关联需求、Bug、用户反馈、使用指标、线上日志、发布记录和研发度量。
- AI 只能生成建议，不能自动创建正式需求、变更产品路线图或调整迭代排期。
- 正式转为需求或进入迭代计划前，必须生成 `iteration_plan_decision` 并由产品负责人确认。

### 模块 B4: bug

**职责**: 管理 AI 自动测试和人工测试登记的 Bug，支持分派、修复、验证、关闭和重复归并。

**核心规则**:
- Bug 来源为 `ai_auto_test | manual_test`。
- Bug 必须归属产品，可选关联版本、模块、需求、AI 任务、GitLab 提交、Jenkins 发布或线上日志事件。
- 重复 Bug 通过 `duplicate_of_bug_id` 关联到主 Bug，不重复进入修复队列。
- AI 自动测试登记但缺少复现信息时应保留待确认标记，等待测试负责人补充。
- 当前 v1.1 基础实现使用 `product_owner`、`rd_owner`、`admin` 写权限完成登记和状态更新；独立 `tester` 角色随真实测试组织模型接入后再扩展。

### 模块 B5: lifecycle_context

**职责**: 建立软件研发全流程上下文图谱，串联需求、设计、方案、代码、Review、测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件，提供上游依据、下游影响、风险信号和下一步建议。

**核心规则**:
- 所有关系边必须记录来源主体、目标主体、关系类型、产品归属、来源模块和观测时间。
- 自动归因关系必须记录置信度，低置信度关系进入待确认或待归属状态。
- 风险信号必须保留来源主体和影响摘要，不得只在看板中展示无法追溯的聚合数字。
- 查询时支持从需求、AI 任务、Bug、发布、提交、线上日志、用户反馈或迭代规划建议任一主体向上游和下游追溯。

### 模块 B6: dashboard

**职责**: 为首页 IT 团队看板提供按产品聚合的需求、研发进展、Bug、线上系统健康、核心业务运行、用户使用、用户反馈、AI 迭代规划建议摘要和发布状态统计。

**核心规则**:
- 看板默认按产品聚合，支持按时间窗口、环境、产品和模块筛选。
- 看板指标来自需求、AI 任务、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀、审计事件和 lifecycle_context 风险信号。
- 首页只展示聚合和风险摘要，明细下钻到对应主体页面。

### 模块 C: model_gateway

**职责**: 统一模型调用入口，支持聊天和 embedding。

**核心规则**:
- 结构化输出必须要求 JSON 并做 schema 校验。
- 调用前进行基础敏感信息过滤。
- 日志记录 provider、model、purpose、tokens、latency、status、error，不默认记录完整 prompt。

---

## 状态管理

**状态结构**:
```text
Requirement: draft | pending_approval | approved | rejected | task_created | closed
Product: active | inactive
Product version: planning | active | archived
AI task: draft | running | waiting_more_info | waiting_review | writing_back | completed | failed | cancelled
Review: pending | approved | edited_approved | rejected | requested_more_info | cancelled
Knowledge document: importing | pending_index | indexed | index_failed | archived
Knowledge deposit: pending | approved | rejected
Bug: open | triaged | needs_info | assigned | fixed | verified | closed | reopened
Iteration plan suggestion:
draft | suggested | accepted | edited_accepted | rejected | converted_to_requirement
```

**状态流转**:
```text
Requirement:
draft → pending_approval → approved → task_created → closed
pending_approval → rejected → closed
approved → closed
task_created → task_created（继续创建关联任务）

AI task:
draft → running → waiting_more_info → draft → running
running → waiting_review → running
running → writing_back → completed
running/waiting_* → failed/cancelled

AI task type:
product_detail_design | technical_solution | development_planning | code_review | automated_testing | release_readiness | post_release_analysis

Knowledge document:
importing → pending_index → indexed
importing/pending_index → index_failed → pending_index
indexed → archived

Knowledge deposit:
pending → approved
pending → rejected

Bug:
open → triaged → assigned → fixed → verified → closed
open/triaged → needs_info → triaged
fixed/verified → reopened → assigned

Iteration plan suggestion:
draft → suggested → accepted
accepted → converted_to_requirement
suggested → edited_accepted
edited_accepted → converted_to_requirement
suggested → rejected
```

### 状态机动作矩阵

#### Requirement

| 当前状态 | 动作 | 目标状态 | 角色 | 幂等/冲突规则 | 审计事件 |
|----------|------|----------|------|----------------|----------|
| draft | submit | pending_approval | rd_owner | 重复提交保持 pending_approval 或返回状态错误。 | requirement.submitted |
| pending_approval | approve | approved | 产品负责人/审批人 | 已审批后重复 approve 返回状态错误。 | requirement.approved |
| pending_approval | reject | rejected | 产品负责人/审批人 | 必须提供 rejection_reason。 | requirement.rejected |
| approved/task_created | create_ai_task | task_created | rd_owner | 同一需求可创建多个关联任务；`task_created` 表示已至少创建一个任务，不阻止继续创建满足前置依赖的技术方案、code_review 或后续阶段任务。每个任务必须保存独立快照。 | ai_task.created |
| task_created | close | closed | rd_owner | 未完成任务存在时不允许关闭或需二次确认。 | requirement.closed |

#### AI Task

| 当前状态 | 动作 | 目标状态 | 角色 | 幂等/冲突规则 | 审计事件 |
|----------|------|----------|------|----------------|----------|
| draft | start | running | rd_owner/Reviewer | completed、cancelled 不可再次 start。 | ai_task.started |
| running | request_more_info | waiting_more_info | system/ai | 必须保存可操作问题。 | ai_task.more_info_required |
| waiting_more_info | submit_answers | draft | rd_owner | 补充后回到 draft，再次 start 继续运行。 | ai_task.more_info_submitted |
| running | create_review | waiting_review | system/ai | 每个确认点只允许一个 pending review。 | review.created |
| waiting_review | review_approved | running | Reviewer | 需匹配 human_reviews.version。 | review.submitted |
| running | write_back | writing_back | system | 使用 idempotency_key 防重复回写。 | ai_task.writing_back |
| writing_back | complete | completed | system | 重复 complete 保持 completed。 | ai_task.completed |
| running | fail | failed | system | 记录 error_code 和 retryable。 | ai_task.failed |
| draft/running/waiting_more_info/waiting_review | cancel | cancelled | rd_owner/admin | completed 后不可取消。 | ai_task.cancelled |

#### Human Review

| 当前状态 | 动作 | 目标状态 | 角色 | 幂等/冲突规则 | 审计事件 |
|----------|------|----------|------|----------------|----------|
| pending | approve | approved | Reviewer | version 不匹配返回 `REVIEW_VERSION_CONFLICT`。 | review.submitted |
| pending | edit_approve | edited_approved | Reviewer | 必须保存 edited_content。 | review.submitted |
| pending | reject | rejected | Reviewer | 必须保存 decision_reason，任务进入 failed 或 draft 重跑路径。 | review.rejected |
| pending | request_more_info | requested_more_info | Reviewer | 必须保存补充问题，任务进入 waiting_more_info。 | review.more_info_requested |
| pending | cancel | cancelled | system/admin | 任务取消时同步取消 pending review。 | review.cancelled |

#### Knowledge Document

| 当前状态 | 动作 | 目标状态 | 角色 | 幂等/冲突规则 | 审计事件 |
|----------|------|----------|------|----------------|----------|
| importing | import_complete | pending_index | knowledge_maintainer/system | 导入失败进入 index_failed 并保存错误。 | knowledge.imported |
| pending_index | index | indexed | system | embedding 维度不匹配进入 index_failed。 | knowledge.indexed |
| pending_index | index_failed | index_failed | system | 保存 index_error，允许 retry。 | knowledge.index_failed |
| index_failed | retry_index | pending_index | knowledge_maintainer | 重试前保留失败历史。 | knowledge.retry_index |
| indexed | archive | archived | knowledge_maintainer | archived 文档不参与检索。 | knowledge.archived |

#### GitLab MR Snapshot and Code Review Report

| 当前状态 | 动作 | 目标状态 | 角色 | 幂等/冲突规则 | 审计事件 |
|----------|------|----------|------|----------------|----------|
| no_snapshot | preview_mr | previewed | Reviewer | 只读，不保存完整 diff。 | gitlab_mr.previewed |
| previewed | create_snapshot | snapshotted | Reviewer | 每次快照生成不可变 snapshot_hash。 | gitlab_mr.snapshotted |
| previewed | create_snapshot_too_large | failed | Reviewer | 不创建快照，记录 diff_size_bytes、diff_limit_bytes、changed_file_count、changed_file_limit、file_diff_line_count 和 file_diff_line_limit。 | gitlab_mr.snapshot_failed |
| snapshotted | create_code_review_task | report_pending | Reviewer | code_review 任务只引用已有快照。 | ai_task.created |
| report_pending | executor_success | pending_human_review | system | 输出必须通过 schema 校验。 | code_review.generated |
| report_pending | executor_failed | failed | system | 记录 executor 错误和 retryable。 | code_review.executor_failed |
| pending_human_review | confirm_report | confirmed | Reviewer | 确认后只归档 AI Brain 内部报告，不回写 GitLab。 | code_review.confirmed |

---

## 数据流

```text
用户新增需求
→ requirement 持久化
→ requirement 审批通过
→ 生成 ai_task，并保存 task_type、requirement_snapshot 与 product_context
→ graph_run 启动
→ knowledge 检索上下文
→ long_memory 可选补充 GBrain 长期记忆、知识图谱和缺口分析
→ model_gateway 按 task_type 生成结构化结果；code_review 任务先通过 gitlab_review 拉取 MR diff 快照，再调用 code_review_executor
→ review 创建对应阶段人工确认
→ 人工决策恢复 graph
→ 按 task_type 生成详细设计、技术方案、开发计划、内部 GitLab MR Review 报告、测试分析、发布评估或上线后分析
→ mock_issues / code_review_reports / Bug / release_readiness_result / knowledge_deposits 幂等回写、内部归档或生成候选
→ lifecycle_context 写入上下文关系边和风险信号
→ devops_metrics 定时采集 GitLab、Jenkins 和线上运行日志
→ user_insights 定时采集用户使用指标和用户反馈
→ iteration_planning 结合产品规划、需求池、Bug、线上日志、发布记录、研发投入、用户使用和用户反馈生成迭代规划建议
→ 产品负责人确认、修改后采纳或驳回迭代规划建议
→ bug 汇总 AI 自动测试和人工测试登记问题
→ dashboard 聚合需求、研发进展、Bug、发布、线上运行、用户洞察、迭代规划和全流程风险信号
→ audit_events 记录全过程
```

---

## 缓存策略

| 数据类型 | 缓存位置 | Key 格式 | 过期时间 | 更新策略 |
|----------|----------|----------|----------|----------|
| Graph 临时运行上下文 | Redis | graph_run:{id}:state | 24h | checkpoint 写入时更新。 |
| 模型调用幂等结果 | Redis | model_call:{hash} | 10min | 相同请求短期复用。 |
| 知识检索短期结果 | Redis | retrieval:{brain}:{user}:{hash} | 5min | 文档索引更新后失效。 |
| 运营洞察聚合快照 | Redis | insight:{product}:{window}:{hash} | 10min | 用户使用、反馈或规划建议更新后失效。 |

---

## 测试策略

### 单元测试
- 覆盖状态机、角色目录、权限判断、响应 envelope、幂等 key 生成、知识切片、模型 gateway schema 校验、GitLab MR 输入校验、diff 大小限制、Review 报告 schema 校验、凭据掩码和迭代规划建议排序规则。
- 目标覆盖率: 80%。

### 集成测试
- 覆盖 FastAPI 路由、PostgreSQL 迁移、角色字典、pgvector 检索、Redis 依赖、人工确认恢复流程、GitLab MR 预览/拉取、code_review 任务创建、code-review 执行器调用、报告归档、用户洞察聚合和迭代规划确认流程。

### E2E 测试
- v1 MVP 覆盖“产品配置 → 内部 GitLab 项目绑定 → 新增需求 → 审批通过 → 生成产品详细设计任务 → 人工确认 → 技术方案任务 → 选择 GitLab MR → 拉取 diff 快照 → 生成 code_review 报告 → 人工确认并内部归档 → 知识沉淀审核 → 审计可查”的黄金路径。
- v1.2 扩展覆盖“用户洞察采集 → AI 迭代规划建议 → 产品负责人确认 → 转正式需求”的产品迭代路径。
- 自动化测试、发布评估和上线后分析按后续阶段补充 E2E。

### 测试用例

测试用例数量和优先级分布以 [test-case.md](./test-case.md) 为准，技术规格不重复维护统计数字，避免清单和规格漂移。

---

## 性能考量

| 指标 | 目标 | 实现方式 |
|------|------|----------|
| 常规 API 响应 | P95 < 500ms | 分页、索引、避免同步模型调用阻塞。 |
| 知识检索 | P95 < 1s | top_k 限制、向量索引、权限过滤下推。 |
| AI 工作流 | 长任务异步 | Graph run 状态持久化，前端轮询或后续 SSE。 |
| 审计查询 | P95 < 500ms | ai_task_id、event_type、created_at 索引。 |
| 首页看板 | P95 < 800ms | 读取聚合快照，避免实时跨域聚合。 |
| 用户洞察查询 | P95 < 800ms | 使用产品、模块、功能、时间窗口索引和聚合快照。 |
| 迭代规划生成 | 异步任务 | 证据聚合与模型调用异步执行，前端查询建议状态。 |

**性能优化点**:
- 对任务列表、审计列表、知识检索、用户洞察和迭代规划建议列表使用分页和 top_k 限制。
- 将模型调用和迭代规划生成放入异步任务，不阻塞常规 HTTP 请求。

---

## 安全设计

| 风险点 | 防护措施 |
|--------|----------|
| 越权访问任务 | API 层按用户角色和任务参与关系校验。 |
| 越权维护产品/需求 | 主体级写操作按角色校验，并写入主体级审计事件。 |
| 知识越权检索 | 数据库查询层先过滤权限再返回 chunk。 |
| Prompt/输出泄漏 | 模型日志默认只存元数据、摘要或哈希。 |
| 重复回写 | mock_issues 使用唯一幂等键。 |
| 并发确认覆盖 | human_reviews 使用 version 乐观锁。 |
| GitLab 凭据泄漏 | 产品 Git 资源只保存凭据引用或密文，API 响应只返回是否已配置凭据，不向 code-review 执行器传递 token。 |
| GitLab 回写副作用 | v1 MVP code_review 只归档 AI Brain 内部报告，不调用 GitLab 评论、审批、request changes、合并或分支变更 API。 |
| 用户使用明细泄漏 | 看板和 AI 规划默认只使用聚合统计或脱敏摘要，不向模型传递用户级明细。 |
| AI 自动改变迭代计划 | 迭代规划建议必须经产品负责人确认，AI 不自动创建正式需求或调整排期。 |

---

## 风险与回滚

| 风险 | 影响 | 应对 |
|------|------|------|
| 模型输出不稳定 | PRD/任务质量波动 | 使用结构化 JSON、schema 校验和人工确认。 |
| pgvector 维度配置错误 | embedding 写入失败 | 启动时校验 embedding model dimension。 |
| Graph 中断恢复失败 | 任务卡住 | checkpoint 前后持久化，提供 retry/cancel。 |
| 文档与实现漂移 | AI 后续实现误判 | 项目级 PRD/spec/API/test-case 作为唯一维护源，并参考业务流程评审指南保持主体边界一致。 |
| 用户洞察采集归属不准 | 迭代规划建议偏离真实使用 | 使用产品/模块/功能映射表，低置信度数据进入待归属队列。 |
| 用户反馈样本偏差 | 需求优先级被少数反馈放大 | 建议必须展示证据数量、来源分布和置信度，样本不足时标识证据不足。 |
| GitLab MR diff 过大或拉取失败 | code_review 任务无法生成报告 | 设置 diff 大小限制和可操作错误提示，允许拆分 MR 或重试，不静默截断。 |
| code-review 执行器不可用 | Review 报告生成失败 | 记录执行器错误、trace_id 和 retryable 状态，支持重跑或切换执行器。 |

---

## 关联文档

- PRD: [01-prd/enterprise-ai-brain/prd.md](../../01-prd/enterprise-ai-brain/prd.md)
- API: [api.md](./api.md)
- 测试用例: [test-case.md](./test-case.md)
- 整体方案评审与业务流程: [03-guides/ai-development-workflow.md](../../03-guides/ai-development-workflow.md)

---
最后更新: 2026-05-29
