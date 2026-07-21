# 技术栈选型

## 选型原则

1. v2.0 在 v1 交付基础上优先跑通“产品需求 → 正式评估 → 规划版本归组 → 统一策略与岗位组队 → 工作项 DAG 并行 → 审核返工/人类决策 → 开发测试与远程代码提交 → 待发布”的闭环；部署由策略显式开启并复用现有人工门禁。
2. 优先选择团队易理解、可本地部署、可替换的技术组件。
3. AI、知识检索、外部集成保留清晰抽象边界，避免业务代码直连供应商或外部系统。
4. AI 助手是工作台内的系统问答入口，仍复用模型网关 Chat 边界和服务端脱敏上下文，不引入独立模型 SDK 或绕过审计的前端直连。

## 技术栈总览

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| 前端框架 | React + TypeScript + Ant Design Pro | 待锁定 | 以 Ant Design Pro 模板作为前端工程基础，适合构建后台工作台式交互，包括任务中心、看板和 AI 助手聊天工作台。 |
| 前端组件框架 | Ant Design | ^6.4.3 | 默认使用 Ant Design 组件、主题 token 和交互规范，避免重复自造基础 UI。 |
| 后端框架 | FastAPI + Python | 待锁定 | 与 AI/LangGraph 生态契合，开发效率高。 |
| AI 编排 | LangGraph + `langgraph-checkpoint-postgres` | 与锁文件一致 | 任务图和版本级协作图使用 PostgreSQL Checkpointer 保存 thread/checkpoint/pending writes；领域表与事件 Inbox 是业务事实源，领域状态/审计/Outbox 同事务，Checkpoint 独立保存游标并通过幂等命令恢复。 |
| 数据库 | PostgreSQL + pgvector | 待锁定 | 同时承载结构化数据和 v1 向量检索。 |
| 缓存/队列 | Redis | 待锁定 | 支持临时状态、短期缓存和后续队列化。 |
| 事务消息 | PostgreSQL Outbox / Inbox | 内置 | 业务状态、审计与外部派发意图原子提交；Webhook 幂等接收后由独立 Worker 投影。 |
| 研发协作调度 | PostgreSQL DAG + lease/幂等键 | 内置 | 工作项、依赖、岗位、真人/AI 数字员工席位、员工与执行器快照、审核返工、阻塞恢复、决策和预算均为持久业务状态；多 Worker 通过数据库租约安全并行。 |
| 对象存储 | MinIO / S3-compatible | 待锁定 | 保存知识原始文件、OCR/版面/表格解析产物和受保护预览资产。 |
| 容器化 | Docker Compose | Compose v2 | 满足本地开发和 v1 演示部署。 |
| GitLab API | 内部 GitLab MR 元信息和 diff 快照 | v1 MVP 用于代码 Review 输入；只读授权 MR，不回写评论或审批状态。 |
| 长期记忆 / 公司大脑 | GBrain | 待锁定 | 作为长期记忆层，提供混合检索、答案合成、知识图谱和 MCP/CLI 接入能力。 |
| 模型协议 | OpenAI-compatible API | 由供应商决定 | 降低模型供应商耦合；AI 助手只依赖 Chat 能力，知识索引和检索才依赖 Embedding。 |

## 前端技术栈

### 框架选型

| 候选方案 | 优点 | 缺点 | 结论 |
|----------|------|------|------|
| React + TypeScript + Ant Design Pro | 生态成熟、适合复杂工作台、类型约束好，并自带后台布局、路由、菜单、权限和脚手架约定 | 需要控制模板裁剪范围，避免引入不需要的示例页面和重型依赖 | 采用 |
| React + TypeScript 自建工程 | 生态成熟、灵活 | 需要自行组织路由、布局、菜单、权限和页面脚手架 | 不采用 |
| Vue | 上手快 | 当前设计默认 React | 不采用 |

### 工程模板约束

前端工程默认基于 Ant Design Pro 模板搭建，模板来源为 `https://github.com/ant-design/ant-design-pro`。当前 `apps/web` 应按 Umi Max / Ant Design Pro 工程结构运行，保留后台工作台能力，包括基础布局、路由、菜单、权限入口、请求封装和页面脚手架；同时删除与 AI Brain 无关的示例页面、mock 数据和演示业务逻辑。

约束：

- Ant Design Pro 作为工程模板和后台信息架构起点；项目应复制或初始化为本仓库自己的 `apps/web` 工程，并通过 `@umijs/max`、`@ant-design/pro-components`、`antd` 等 npm 依赖独立安装、构建和部署。
- `apps/web` 启动和构建脚本必须使用 `max dev`、`max build`；不得用 Vite 自建根入口、自定义 sidebar 或纯 `antd` 壳子替代 Ant Design Pro。
- 前端布局应保留顶部 Header，菜单采用左侧单栏多级模式，不把一级菜单拆到顶部导航。团队看板作为独立一级菜单；需求交付承载需求、迭代、研发任务等研发交付入口；任务中心承载 AI 能力配置、定时作业和插件管理；产品资产、运营治理按业务域组织二级菜单并全部在左侧展开/收起。
- 保留模板中有价值的 Layout、菜单、权限和请求约定，但业务模型、API 类型和页面内容以本项目 PRD/API 文档为准。
- 前端服务层按“请求基础设施 + 认证客户端 + 领域客户端”拆分；`apps/web/src/services/apiClient.ts` 统一维护 API base URL、请求 envelope、错误解析、401 回调和远程列表参数拼装，`apps/web/src/services/authClient.ts` 统一维护访问令牌、当前用户缓存、登录/退出和 401 跳转，`apps/web/src/services/dashboardClient.ts` 维护团队看板读模型映射与查询，`apps/web/src/services/productContextClient.ts` 维护产品/迭代版本选择上下文分页拉取和页面可选版本过滤，`apps/web/src/services/productVersionDashboardClient.ts` 维护迭代版本驾驶舱响应映射与总览查询，`apps/web/src/services/lifecycleClient.ts` 维护需求 full-chain 与生命周期主体 full-chain 响应映射、查询和深链生成，`apps/web/src/services/diagnosticsClient.ts` 维护审计列表、执行诊断列表/详情和生命周期上下文查询，`apps/web/src/services/userInsightsClient.ts` 维护用户洞察、用户反馈、反馈转需求和迭代建议请求，`apps/web/src/services/codeInspectionClient.ts` 维护代码巡检列表、治理看板、详情和误报忽略审批请求，`apps/web/src/services/assistantDraftClient.ts` 维护 AI 动作草案本地状态、草案任务台查询、确认、取消、重试、查看和修改标记请求，`services/aiBrain.ts` 继续作为兼容导出入口并逐步按领域拆分业务 client，避免新增能力继续堆入单一大文件。
- 初始化后应在本仓库锁定 package manager、依赖版本、启动脚本、构建脚本和测试脚本。
- 不保留模板自带示例账号、示例接口、mock 数据作为正式业务逻辑。

### 组件框架约束

前端默认使用 Ant Design Pro 提供的后台工程结构，并使用 Ant Design 作为 UI 组件框架。新页面、新表单、新列表、新弹窗、新导航和状态展示应优先采用 `@ant-design/pro-components` 与 `antd` 官方组件，并通过 `ConfigProvider` 主题 token、组件 token 和局部 className 完成视觉定制。

约束：

- 默认从 npm 包 `antd` 引入组件，不依赖本机 `/Users/zeek/source/ant-design` 源码目录作为运行时路径。
- 后台页面容器、查询表格、详情卡片、统计卡片和工作台区块优先使用 `PageContainer`、`ProTable`、`ProCard`、`StatisticCard` 等 ProComponents。
- 产品、需求、Bug、知识和审计等台账型入口默认参考 Ant Design Pro `list/table-list`，使用 `PageContainer` 面包屑 + `ProTable` 内建查询表单、表格标题、工具栏、分页和行选择能力，并要求查询动作真实更新列表结果。
- AI 助手聊天工作台是可用的业务页面，不是营销说明页；页面应使用 Ant Design / ProComponents 组织聊天消息、快速问题、上下文标签、输入框、模型状态和错误提示。
- 业务页面默认关闭 `PageContainer` 顶部标题、状态标签和说明文案，避免页面头部重复展示菜单名称、API 状态和长说明；必要上下文应放在表格标题、卡片标题或业务控件内。
- 本地 Ant Design 工程目录只作为源码参考、样式评估或版本对照来源；`ai-brain` 项目后续应能独立构建、运行和部署。
- 只有当 Ant Design 没有合适组件，或业务交互需要明显定制时，才新增自定义组件；自定义组件也应尽量复用 Ant Design 的 token、布局节奏和交互状态。
- 不用全局 CSS 大面积覆盖 Ant Design 内部选择器；优先使用主题 token、组件 props 和小范围样式封装。

### 状态管理

v1 先使用轻量状态管理和服务端状态查询，重点保证任务状态、确认点和审计信息展示清晰。是否引入专门状态库由前端实现阶段决定。

## 后端技术栈

### 语言选型

| 候选方案 | 优点 | 缺点 | 结论 |
|----------|------|------|------|
| Python | AI 生态成熟，LangGraph/FastAPI 集成自然 | 类型约束弱于编译型语言 | 采用 |
| Node.js | 前后端语言统一 | LangGraph/Python AI 生态不是最短路径 | 不采用 |

### 框架选型

| 候选方案 | 优点 | 缺点 | 结论 |
|----------|------|------|------|
| FastAPI | 类型友好、OpenAPI 支持好、异步能力成熟 | 需要规范模块边界 | 采用 |
| Django | 全功能框架 | v1 模块化 API 和 AI 工作流不需要完整后台框架 | 不采用 |

### AI 助手后端边界

AI 助手通过 FastAPI 暴露 `/api/assistant/chat`，服务端负责收集并脱敏当前产品、需求、AI 任务、Git 仓库和模型网关状态摘要，然后通过模型网关 Chat 能力生成回答。前端不得直接把模型 API Key 或完整系统快照发送给外部 provider；模型调用日志只记录 provider、model、purpose、tokens、latency、status、error 和配置 id 等元数据，其中助手调用使用 `purpose=assistant_chat`。

ChatGPT OAuth 类上游或 Sub2API 只提供 Chat 能力时，AI 助手仍可工作；Embedding 不可用只影响知识索引、知识检索向量排序和长期记忆相关能力，不阻断助手问答。

## 数据存储

### 主数据库

| 候选方案 | 优点 | 缺点 | 结论 |
|----------|------|------|------|
| PostgreSQL + pgvector | 结构化数据、事务、权限过滤和向量检索可放在同一数据库 | 大规模向量检索能力有限 | v1 采用 |
| 独立向量库 | 检索能力强 | 增加基础设施和权限同步复杂度 | v1 不采用 |

### 缓存方案

| 候选方案 | 优点 | 缺点 | 结论 |
|----------|------|------|------|
| Redis | 简单成熟，适合缓存和队列 | 需要注意缓存一致性 | 采用 |
| 仅数据库 | 架构更少 | 不适合临时状态和队列演进 | 不采用 |

## 长期记忆与公司大脑

v1 的业务知识库仍以 PostgreSQL + pgvector 承载结构化权限过滤、知识文档、知识切片和任务沉淀。长期记忆/公司大脑能力约定引入 GBrain，项目地址为 `https://github.com/garrytan/gbrain`。

### GBrain 定位

GBrain 用于提供跨任务、跨来源的长期记忆层，重点能力包括：

- 混合检索：向量检索、关键词检索、RRF、reranker 和来源权重组合。
- 答案合成：基于检索结果生成带引用的综合回答，并指出知识缺口。
- 知识图谱：从页面、实体和链接中形成 typed edges，支持图遍历和多跳查询。
- MCP/CLI 接入：可作为外部 brain 服务接入 AI agent 或平台运维流程。

### 集成边界

- GBrain 不替代 v1 业务数据库；产品、需求、AI 任务、人工确认、审计事件仍由本项目 FastAPI + PostgreSQL 管理。
- GBrain 作为长期记忆和公司脑补充层，可用于导入跨项目文档、会议、决策、历史经验和团队知识。
- 平台知识中心可以在后续版本增加 GBrain 连接器，把经过权限校验的知识源同步到 GBrain，或从 GBrain 查询长期记忆结果。
- 所有进入业务工作流的 GBrain 检索结果仍需保留来源引用，并遵守本项目权限过滤和审计要求。

## 基础设施

### 部署方案

| 候选方案 | 优点 | 缺点 | 结论 |
|----------|------|------|------|
| Docker Compose | 本地和 v1 演示简单直接 | 不适合大规模生产编排 | v1 采用 |
| Kubernetes | 扩展和治理能力强 | v1 复杂度过高 | 后续评估 |

### 执行 Worker

Docker Compose 中的 `execution-worker` 独立认领 PostgreSQL Outbox/Inbox，负责 Runner/Jenkins/Git Provider 派发、外部事件投影、部署健康验证和回滚。生产环境关闭 API 进程内兼容 worker，避免多进程重复执行外部副作用。

Docker Compose 中的 PostgreSQL/pgvector 镜像不包含应用迁移，也不从 `/docker-entrypoint-initdb.d` 执行 `apps/api/app/db/migrations`。普通迁移只由 API 镜像打包的迁移目录与 `api-entrypoint.sh` 执行；PostgreSQL advisory lock 覆盖完整扫描，每个未登记文件与其 `app_schema_migrations` 校验和账本记录独立原子提交。校验和不一致会阻止启动。121 显式 cleanup 和 125-128 运行时 concurrent compatibility 是仅有例外。

### 监控方案

v1 先确保应用日志、健康检查、审计事件和 Outbox/Inbox 积压指标可用；Prometheus、OpenTelemetry 和 Sentry 可通过签名事件入口接入，Grafana 或云厂商监控作为展示层。

## 相关决策记录

当前技术决策以 [项目级技术规格](../enterprise-ai-brain/spec.md) 为准。需要正式 ADR 时，从 [ADR 模板](../../04-decisions/0000-template.md) 创建编号文档。

---
最后更新: 2026-07-11
