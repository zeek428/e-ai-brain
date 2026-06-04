# 变更日志

所有重要的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 需求管理新增多选“批量排期”，迭代版本页新增“归集需求”入口，后端新增 `/api/requirements/batch-schedule`，支持将同产品需求池/已排期需求快速归集到未归档迭代版本，并记录批量级与逐需求审计。
- 真实网页验收修复需求页批量排期目标版本只显示 active 的问题：现在可选择 planning/active 等未归档版本并过滤 archived；批次审计改为追加保存，避免覆盖历史 `requirement.batch_scheduled` 审计。
- 测试流程新增提交前真实网页界面验证门禁：影响前端或用户可见页面的改动，必须在真实 Web 页面完成 URL/标题、非空渲染、目标交互、旧文案消失和控制台健康检查，通过后才能提交代码。
- 任务管理查询性能优化：API 增加 PostgreSQL 连接复用，`GET /api/ai-tasks` 支持 `keyword`、`created_by`、`page`、`page_size` 远程查询分页，任务管理页仅对任务列表启用远程筛选分页；`GET /api/reviews/pending` 改为 SQL 直查待确认摘要，避免加载任务工作流全量兼容快照。
- DB-first 迁移继续收敛知识、任务运行态、运营采集、用户洞察和迭代规划写接口：PostgreSQL 路径现在构造明确 records/payloads 直接调用 repository，新增记录不再依赖请求态集合充当写入事实源；MemoryStore 集合写入仅保留为测试 helper fallback。
- DB-first 迁移补齐任务工作流写路径的请求级 repository source rows 上下文，任务启动、取消、补充信息和 Review approve/edit-approve/reject/request-more-info 在全局运行时 store 过期时仍可读取结构表源数据并在 handler 返回前写回 PostgreSQL。
- DB-first 迁移补齐任务工作流 repository source rows 读取入口，PostgreSQL 运行时需求详情、AI 任务详情、Graph Run 列表、待确认 Review、Review 详情、模拟回写结果、Code Review 报告和 Markdown 导出不再通过 repository read snapshot 承载读取。
- DB-first 迁移补齐生命周期上下文 repository source rows 聚合入口，PostgreSQL 运行时 `/api/lifecycle/context` 不再通过 repository read snapshot 承载聚合，并通过 repository 写回生成的 lifecycle edges/risks。
- DB-first 迁移补齐首页 IT 团队看板 repository source rows 聚合入口，PostgreSQL 运行时 `/api/dashboard/it-team` 不再通过 repository read snapshot 承载聚合，并通过单条 repository 写入保存 dashboard snapshot。
- DB-first 迁移将 PostgreSQL 启动运行层从 `PersistentMemoryStore.from_repository(...)` 替换为轻量 `PostgresRuntimeStore(repository)`，启动不再恢复业务集合；`MemoryStore` 仅保留为测试 helper，PostgreSQL source rows 使用非 `MemoryStore` 的 `_RepositoryRequestContext`。
- DB-first 迁移补齐产品配置写接口、需求/任务创建写接口和 Bug 写接口在 `PostgresRuntimeStore` 空启动容器下的 repository source rows 上下文，避免产品、版本、模块、需求、任务和 Bug 校验依赖启动时内存集合。
- DB-first 迁移补齐运营采集、待归属、DevOps 指标、线上日志、用户使用、用户反馈和迭代规划写接口在 `PostgresRuntimeStore` 空启动容器下的 repository source rows 上下文，并将需求列表切到 task workflow source rows 读取。
- DB-first 迁移补齐模型网关配置写接口和 AI 助手聊天写接口在 `PostgresRuntimeStore` 空启动容器下的 repository source rows 上下文，配置修改/删除和继续用户会话不再依赖启动时内存集合。
- DB-first 迁移补齐知识文档创建/修改/重试/删除和知识沉淀采纳/拒绝写接口在 `PostgresRuntimeStore` 空启动容器下的 repository source rows 上下文，索引重建和沉淀审核不再依赖启动时内存集合。
- DB-first 迁移移除生产 read snapshot 恢复 fallback，`main.py` 不再通过 `PersistentMemoryStore.from_repository(...)` 反灌 repository payload；业务大脑只读接口改为 repository-first 读取 `brain_apps`，知识沉淀驳回和 Mock Writeback 生成改为 source rows 写上下文。
- DB-first 迁移将生命周期上下文 source rows 从 `MemoryStore()` 投影替换为专用 `LifecycleContextReadModel`，保留现有链路/风险算法的同时去除该聚合路径的 MemoryStore 中间层语义。
- DB-first 迁移进一步收敛写接口边界：产品配置、模型网关配置/测试和 AI 助手聊天在 PostgreSQL 路径构造明确 records/payloads 后直接调用 repository 写入；只读缓存/read model 可保留为 PostgreSQL 派生、可重建的性能优化，但不得作为写入事实源。
- 新增 `/api/product-versions` 批量版本列表接口，返回版本及所属产品投影；需求列表同步返回产品/迭代版本展示字段，任务列表在 PostgreSQL 模式通过 SQL join 返回产品名并支持产品和创建时间段筛选。
- DB-first 迁移补齐任务运行态、Review、模拟回写、Code Review 报告和 Markdown 导出读快照；Mock Writeback 生成在 handler 返回前写入 `mock_issues` 和 `mock_issue.written` 审计事件，不依赖请求结束全局 persist。
- DB-first 迁移补齐知识沉淀候选列表 repository-first 读取，`status` 过滤进入查询层，运行态 store 过期时仍从结构表返回沉淀候选。
- DB-first 迁移补齐知识检索 repository-first 候选查询，文档权限、chunk 权限、可检索状态和关键词过滤进入查询层，保留关键词兜底和兼容向量排序。
- DB-first 迁移补齐知识沉淀 approve/reject 写接口的 repository 当前记录读取，运行态 store 过期时仍能完成审核并写回结构表与审计事件。
- 需求创建支持不指定迭代版本，审批后先进入需求池，排期到未归档迭代版本后才能生成 AI 任务；需求交付新增“迭代版本”页面，需求状态按设计、开发、代码评审、测试、发布和验收流程推进。
- 模型网关配置拆分 Chat 与 Embedding 能力：Embedding 可禁用、复用 Chat 连接或单独配置 baseURL/API Key，知识向量 chunk 记录 embedding_config_id/model/dimension，检索只比较兼容向量并保留关键词兜底。
- 知识索引新增文本兜底模式：Embedding 不可用时仍保存文本 chunk 并进入 `text_indexed`，知识检索以关键词模式返回可访问结果；Embedding 恢复后可通过重试升级为 `vector_indexed`。
- AI 助手聊天记录按登录用户保存，新增 `/api/assistant/conversations` 与 `/api/assistant/conversations/{conversation_id}/messages`，前端侧栏展示最近对话并可打开历史消息；新增 `019_assistant_chat_history.sql` 和 `assistant_conversations` / `assistant_messages` 结构表。
- AI Brain GitHub PR 真实复跑后补齐 code_review 本地联调策略：默认外部执行器命令为空且模型网关可用时，代码 Review 任务自动通过 `model_gateway` 适配器生成结构化报告，Review prompt 携带 MR/PR 快照和技术方案，并保留模型调用审计。
- 全链路真实用例复跑后新增 GitHub PR 列表接口 `/api/devops/github/pull-requests/{repository_id}`，支持基于产品 GitHub 凭据列出可访问 PR，避免代码 Review 创建前必须手工猜 PR 编号。
- 产品配置补齐 `GET /api/products/{product_id}` 详情接口，便于从产品管理进入配置或全链路脚本校验时直接读取产品主体。
- AI 任务启动支持对 `model_gateway_failed` 和 `code_review_executor_failed` 的失败任务使用同一 `task_id` 原地重试，并记录 `ai_task.retry_started` 审计事件。
- 新增 AI 助手聊天工作台和 `/api/assistant/chat`，基于模型网关 Chat 能力与服务端脱敏系统上下文回答 AI Brain 产品配置、需求任务、Git 仓库、模型网关状态和项目开发进展问题；模型调用日志仅记录 `purpose=assistant_chat` 元数据。
- 产品 Git 资源支持选择 GitHub provider，任务中心可基于 GitHub PR 预览和 diff 快照创建 `code_review` 任务；凭据解析支持环境变量、服务端密钥引用和本地联调直填只读 token，API 响应仍不回显凭据。
- 所有 PostgreSQL 结构表统一补齐 `created_at` 和 `updated_at` 标准时间字段，新增 `018_standard_timestamps.sql` 迁移脚本和表定义门禁测试，防止后续新表漏字段。
- 任务管理页面新增“所属产品”和“时间段”查询条件，AI 任务列表摘要同步返回产品名、创建时间和更新时间，并支持 `created_from`/`created_to` 后端过滤。
- 模型网关配置页新增“测试连接”能力，后端新增 `/api/system/model-gateway-configs/test`，使用临时 OpenAI-compatible 参数检测 Chat 与 Embedding 连通性，返回脱敏状态且不保存密钥或模型调用日志。
- 模型网关测试连接新增测试范围选择，支持仅测试 Chat，并在未测试 Embedding 时返回 `skipped`，便于接入 ChatGPT OAuth 类不提供 `/embeddings` 的 Sub2API 上游。
- 将前端左侧一级入口从 `欢迎` 更名为 `团队看板`，保留 `/welcome` 兼容路径，并同步架构与编码规范文档中的菜单命名。
- 新增 `/api/long-memory/status`，未配置 GBrain 时返回明确 `not_configured` 能力状态，配置后只暴露脱敏配置状态和能力列表，不泄露密钥。
- AI 任务启动接入真实 LangGraph `StateGraph` 运行内核，Graph Run 记录新增 `runtime=langgraph`、节点路径和 `graph_runtime` checkpoint 元数据；新增 `017_langgraph_runtime_metadata.sql` 以 SQL 脚本升级既有 PostgreSQL 环境。
- 业务大脑配置收口为只读真实配置读取，`/api/brain-apps` 从运行时/`brain_apps` 加载默认 `rd_brain`；新增 `016_brain_app_task_attribution.sql`，补齐需求与 AI 任务的默认业务脑归属、`ai_tasks.brain_app_id` 和查询索引。
- 生命周期上下文边、风险信号和首页 IT 团队看板快照开始细粒度 PostgreSQL 持久化，新增 `015_lifecycle_dashboard_persistence.sql`，`/api/lifecycle/context` 与 `/api/dashboard/it-team` 会同步真实计算结果到结构表。
- 产品配置弹窗新增“相关系统”维护入口，相关系统支持绑定产品归属、按产品过滤，并进入生成任务时的产品上下文快照。
- 任务中心任务操作弹窗新增“查看详情”入口，前端调用真实 `GET /api/ai-tasks/{task_id}` 详情接口并展示产品、版本、模块、需求、Graph Run 和输出内容。
- 任务中心待确认弹窗补齐“修改后通过”和“拒绝”决策入口，前端调用真实 Review `edit-approve`/`reject` API，完善高影响 AI 产出人工门禁体验。
- 同步项目级文档的 MVP 真实系统状态说明，明确前端入口不得展示示例数据或占位统计，并将生产就绪门禁状态更新为脚本已提供、目标环境待通过。
- 初始化 `apps/api` FastAPI 后端、`apps/web` Ant Design Pro 工作台、Docker Compose、本地环境示例、Dockerfile 和 PostgreSQL 初始化迁移脚本。
- 后端实现本地账号认证、trace_id envelope、健康检查、产品配置、需求审批、AI 任务、人审确认、Markdown 导出、GitLab MR / GitHub PR 预览与 diff 快照、内部 Code Review 报告、知识检索/沉淀、模拟 Issue 幂等和审计查询的 MVP 骨架。
- 产品与平台配置补齐查询、局部更新、active_only 过滤、相关系统、模型网关配置、默认模型网关唯一性和 API key 脱敏响应。
- 需求管理补齐列表、详情、按产品/状态过滤、驳回、关闭、任务引用和 inactive 产品拦截。
- 知识沉淀补齐驳回接口、驳回原因、状态过滤和审计事件。
- AI 任务启动补齐 graph_run/checkpoint 记录、任务详情运行投影和 graph run 查询接口，并由真实 LangGraph 运行内核驱动当前人工确认中断路径。
- AI 任务启动改为经由模型网关边界生成任务输出，并记录不含完整 prompt/output 的模型调用元数据日志。
- `/api/lifecycle/context` 从占位升级为 MVP 全流程感知视图，可从需求聚合下游任务、人工确认、GitLab MR 快照、Code Review 报告、模拟 Issue、知识沉淀、审计事件和 Review 风险信号。
- `/api/bugs` 从占位升级为 v1.1 基础 Bug 管理接口，支持查询筛选、AI 自动测试和人工测试登记、状态流转、重复归并、权限校验和审计事件。
- React 工作台任务中心接入真实 `/api/ai-tasks` 列表，不再从前端创建演示产品、演示需求或演示任务。
- 前端补齐 ESLint 9 flat config、React/TypeScript lint 依赖、favicon 和移动端表格内部滚动适配。
- React 工作台左侧导航新增可见页面切换反馈，已实现入口展示真实 API 列表或真实空状态。
- 前端工程迁移到 Umi Max / Ant Design Pro 结构，新增 `.umirc.ts`、`config/routes.ts`、`src/app.tsx`、ProLayout 运行时配置和 ProComponents 页面骨架。
- 产品管理、需求管理、Bug 管理、知识中心和审计与运行页面改为参考 Ant Design Pro `list/table-list` 的 `PageContainer` 面包屑 + `ProTable` 内建查询表格形态，并支持本地查询筛选。
- 产品管理、需求管理、Bug 管理、知识中心和审计与运行页面从后端列表 API 加载真实数据；接口不可用时显示错误和空表，不再展示本地示例行。
- 产品管理、需求管理、Bug 管理、知识中心和审计与运行页面面包屑移除 `欢迎` 前缀，仅保留业务域和当前页面。
- 业务页面统一关闭 `PageContainer` 顶部标题、状态标签和说明文案，使列表页和工作台页只保留主体表格、卡片和操作区。
- 导航保留顶部 Header，并调整为左侧单栏多级菜单；首页改为 IT 团队看板，任务中心作为一级菜单并新增任务管理二级菜单，需求交付、产品资产、运营治理承载二级菜单。
- Docker 本地开发环境固定为独立 `e-ai-brain` 项目名，并补充 `.dockerignore` 降低构建上下文体积。
- 新增后端 pytest 覆盖基础健康/认证、MVP-A 需求到详细设计、技术方案导出、GitLab MR / GitHub PR 快照、Code Review 报告和知识治理闭环。
- 新增并多轮优化面向管理层和非技术人员的 HTML 方案说明，概述 AI Brain v1 业务价值、AI 赋能机制、核心闭环、总体架构、MVP-A/B/C 实施路线、阶段边界和治理要点。
- 扩展 HTML 方案说明中的企业级平台视角，补充多业务模块大脑、企业总AI大脑、技术组件可更替性和项目风险重点 review。
- 综合修订 HTML 方案说明的术语一致性、风险应对表达、管理层可读性和代码样式展示，补齐企业总AI大脑与多业务模块大脑表述。
- 新增 P0 字段级 schema、状态机动作矩阵和核心接口错误语义，降低实现阶段二次解释成本。
- 新增缺失的审计、部署、产品配置、模型网关配置和主体级审计详细测试用例。
- 扩展部署、监控和故障响应 runbook，补充 staging/production-readiness 门禁、SLO、RTO/RPO、备份恢复、密钥轮换和 GitLab 只读边界事故处理。
- 项目级 API 文档补充产品、版本、模块、Git 资源、相关系统和模型网关配置接口。
- 新增需求实体、需求审批状态流转和审批后生成 AI 任务接口。
- 补充 GitLab 代码质量、线上运行日志、Jenkins 发布、首页 IT 团队看板和 Bug 管理的 PRD、技术规格、API、测试用例和评审指南覆盖。
- 扩展 AI 任务为产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估和上线后分析七类研发全链路任务。
- PRD 增加 MVP 成功指标，覆盖需求到产品详细设计耗时、技术方案采纳率、Code Review 报告采纳率、高风险问题有效率、知识沉淀复用率和审计可追踪率。
- 补齐 `/api/brain-apps`、`GET /api/ai-tasks`、`POST /api/ai-tasks/{task_id}/cancel`、`GET /api/reviews/{review_id}`、`GET /api/knowledge/documents` 和显式 `POST /api/writeback/results/{task_id}` 契约。
- PostgreSQL 初始化迁移补齐 users、brain_apps、ai_tasks、human_reviews、GitLab MR 快照、Code Review 报告、知识文档/切片/沉淀和 mock_issues 等 MVP 核心表。
- PostgreSQL 初始化迁移新增 `bugs` 表和按产品状态、来源查询的索引，为后续持久化仓储切换预留结构。
- 后端新增 PostgreSQL 用户仓储、用户管理接口和 `app_state_snapshots` JSONB 快照持久化，Docker 本地栈默认从数据库读取登录用户并保存业务运行状态。
- 新增 `002_persistence_users.sql` 可重复迁移脚本和 API 启动迁移入口，已有数据库卷通过 SQL 脚本升级，不再需要清空 volume。
- PostgreSQL 服务默认切换到本地项目镜像别名 `e-ai-brain-postgres-pgvector:0.8.2-pg18-trixie`，对应官方 `pgvector/pgvector:0.8.2-pg18-trixie`，并保留本地 PG18 + pgvector 构建 Dockerfile 作为网络受限 fallback，避免已有 PostgreSQL 18 数据卷被误切到 PG16 镜像。
- PostgreSQL 迁移新增 `005_knowledge_vector_index.sql`，为 `knowledge_chunks.embedding` 创建 pgvector HNSW cosine 索引，补齐向量检索索引基础设施。
- 产品配置开始细粒度 PostgreSQL 持久化，产品、版本、模块和 Git 资源会同步写入 `products`、`product_versions`、`product_modules`、`product_git_repositories`，并在 API 启动时从结构表恢复。
- 相关系统开始细粒度 PostgreSQL 持久化，纳入产品配置仓储并同步写入 `related_systems`，API 启动时恢复相关系统和 `system` 计数器。
- 需求台账开始细粒度 PostgreSQL 持久化，需求创建、审批、驳回、关闭和任务引用会同步写入 `requirements`，并在 API 启动时从结构表恢复。
- AI 任务开始细粒度 PostgreSQL 持久化，任务类型、标题、状态、需求快照、产品上下文、输入输出和当前步骤会同步写入 `ai_tasks`，并在 API 启动时从结构表恢复。
- 人工确认和 Graph 运行态开始细粒度 PostgreSQL 持久化，`human_reviews`、`graph_runs`、`graph_checkpoints` 会记录 Review 决策、运行状态、检查点和 state snapshot，并在 API 启动时回填任务运行关联。
- 知识文档、知识沉淀候选和审计事件开始细粒度 PostgreSQL 持久化，`knowledge_documents`、`knowledge_deposits`、`audit_events` 会记录知识治理和主体级审计数据，并在 API 启动时从结构表恢复。
- Bug 管理开始细粒度 PostgreSQL 持久化，`bugs` 会记录来源、严重级别、状态流转、负责人、复现步骤、证据和重复归并关系，并在 API 启动时从结构表恢复。
- 模型网关配置和调用元数据日志开始细粒度 PostgreSQL 持久化，`model_gateway_configs`、`model_gateway_logs` 会记录默认配置、密钥配置状态和脱敏调用元数据，并在 API 启动时恢复默认模型网关和日志计数器。
- GitLab MR 快照和 Code Review 报告开始细粒度 PostgreSQL 持久化，`gitlab_mr_snapshots`、`code_review_reports` 会记录 MVP-B 证据链并在 API 启动时恢复报告反链和计数器。
- 模拟 Issue 回写开始细粒度 PostgreSQL 持久化，`mock_issues` 会记录幂等键、来源任务、Issue 标题、状态和 payload，并在 API 启动时恢复回写结果与 `mock_issue` 计数器。
- 知识检索升级为 chunk 级命中结果，文档创建、更新和知识沉淀采纳会生成 `knowledge_chunks`，搜索返回 `chunk_id`、`chunk_index` 和来源引用，并在返回前完成角色权限过滤。
- 知识索引接入 OpenAI-compatible `/embeddings`，chunk embedding 写入 `knowledge_chunks.embedding`，搜索先权限过滤再按 query/chunk embedding cosine 相似度排序并返回 `score`，模型日志仅记录脱敏元数据。
- 后端补齐当前管理主体 CRUD：产品及版本/模块/Git 资源、相关系统、模型网关配置、需求、知识文档、Bug 和用户均支持新增/更新/删除，删除前保留依赖占用校验和审计记录。
- 前端产品管理、需求管理、Bug 管理、知识中心和用户管理新增真实表单弹窗、编辑按钮、删除按钮和接口刷新逻辑，不再停留在列表 demo。
- Bug 管理工作台补齐真实生命周期字段，登记和编辑弹窗支持复现步骤、对象型证据 JSON、重复归并、关联需求/任务和只读来源展示，并将字段保存到 `/api/bugs`。
- 新增“系统管理”一级菜单，并将“用户管理”作为其二级菜单；`/users` 旧入口重定向到 `/system/users`。
- 系统管理新增“模型网关”二级菜单，支持模型网关配置列表、新增、编辑和删除；列表只展示 API Key 是否已配置，编辑留空不覆盖服务端密钥。
- 产品管理新增“配置”弹窗，可维护产品版本、模块和 Git 资源；Git 凭据引用只在提交时发送，列表仅显示已配置状态，不回显凭据引用或 token。
- 研发运营看板和用户洞察页面改为读取真实 API 聚合列表；后端未接入采集器时返回空集合，不再返回 placeholder 状态或伪造统计数据。
- 用户反馈从空集合入口升级为真实业务主体，支持登记、筛选、状态处理、审计记录和 `user_feedback` PostgreSQL 结构表持久化。
- 迭代规划建议从空集合入口升级为真实业务主体，基于用户反馈和 Bug 证据生成建议，支持人工确认、可选转需求、审计记录和 PostgreSQL 结构表持久化。
- 用户使用指标从空集合入口升级为真实业务主体，支持登记、筛选、审计记录和 `user_usage_metrics` PostgreSQL 结构表持久化。
- GitLab 每日代码指标从空集合入口升级为真实业务主体，支持按产品 GitLab 仓库登记、筛选、审计记录和 `gitlab_daily_code_metrics` PostgreSQL 结构表持久化。
- Jenkins 发布记录从空集合入口升级为真实业务主体，支持按产品版本登记、筛选、审计记录和 `jenkins_release_records` PostgreSQL 结构表持久化。
- 线上运行日志指标从空集合入口升级为真实业务主体，支持按产品、模块、环境和时间窗口登记、筛选、审计记录和 `online_log_metrics` PostgreSQL 结构表持久化。
- 采集运行记录升级为真实业务主体，新增 `/api/collectors/runs` 查询、登记和状态更新接口、`collector_runs` PostgreSQL 结构表、审计事件和研发运营页面操作入口，不自动生成指标数据。
- 待归属数据队列升级为真实业务主体，新增 `/api/attribution/pending-items` 查询、登记和处理接口、`pending_attribution_items` PostgreSQL 结构表、审计事件、DevOps 处理弹窗和用户洞察只读可见性；队列处理不自动生成指标或反馈数据。
- Code Review 报告生成接入独立 `code_review_executor` 边界，默认适配 Claude Code `code-review` skill 命令，支持显式 `model_gateway` 适配器，并记录 `code_review.executor_called` / `code_review.executor_failed` 审计事件。
- 新增 `scripts/production_readiness_check.py` 发布门禁脚本，自动检查 Docker Compose、API health、Redis、PostgreSQL pgvector/pgcrypto、模型网关脱敏配置和 GitLab MR 只读 preview/snapshot。
- 首页 IT 团队看板从静态欢迎页升级为真实 MVP 聚合视图，展示产品、需求、AI 任务、待确认 Review、知识沉淀和审计摘要。
- 首页 IT 团队看板新增真实产品筛选控件，页面会从产品配置接口加载产品列表，并按 `product_id` 重新拉取看板聚合数据。
- 首页 IT 团队看板产品筛选补齐后端归属过滤，知识文档和审计事件不再把其他产品的数据混入当前产品聚合；知识文档支持可选 `product_id` 归属上下文。
- 首页 IT 团队看板扩展真实运营聚合和下钻，展示 Bug、GitLab 指标、Jenkins 发布、线上日志、用户使用、用户反馈和迭代建议摘要，并在跳转 Bug、研发运营、用户洞察和审计页面时保留产品与时间范围上下文。
- 需求管理页面新增审批通过、驳回和生成产品详细设计任务操作；任务中心新增启动 draft 任务和确认待 Review 输出的主链路操作。
- 前端运行时用户信息改为从登录响应或 `/api/auth/me` 读取，右上角不再硬编码管理员姓名。
- 任务中心新增基于已完成产品详细设计创建技术方案任务，以及已完成技术方案 Markdown 导出预览入口。
- 任务中心新增基于已完成技术方案选择产品 GitLab/GitHub 代码库、预览 MR/PR、生成 diff 快照、创建 `code_review` 任务和查看内部 Code Review 报告的真实 API 链路。
- 任务管理页面改为与需求管理等页面一致的管理列表风格，移除阶段卡片和左右并排确认台，待确认项改为工具栏或行操作弹窗处理。
- 任务中心新增已完成任务的模拟 Issue 查询/生成弹窗；知识中心新增知识沉淀候选审核弹窗，支持批准入库和拒绝，补齐 MVP-C 页面操作闭环。
- 任务管理列表行内操作收敛为单一“操作”入口，启动、确认、生成方案、导出、Code Review、模拟 Issue 和查看报告统一在任务操作弹窗中触发，避免横向堆叠按钮。
- 知识中心新增真实知识检索弹窗，调用 `/api/knowledge/search` 展示权限过滤后的知识来源和内容摘要，不展示兜底示例结果。
- 任务管理补齐 MVP-A 补充信息闭环，可在待确认弹窗要求补充，并在 `waiting_more_info` 任务操作弹窗提交补充内容使任务回到草稿。
- 任务管理操作弹窗改为上方任务摘要、下方纵向操作的弹出结构，并将列表中的任务类型展示为业务中文标签，避免左右分栏式操作区。
- 任务管理操作弹窗标题收敛为固定“任务操作”，长任务名保留在摘要区展示，避免弹窗标题区拥挤并保持与需求管理等管理弹窗一致。
- 任务管理创建 Code Review 的参数区改为弹窗内纵向表单，并清理旧任务中心左右分栏样式遗留，保持与需求管理等管理页一致。
- 任务中心新增从已确认技术方案创建开发计划和自动化测试任务的真实入口；自动化测试任务人工确认后会把 `bug_suggestions` 转为 `ai_auto_test` 来源 Bug 记录。
- 任务中心新增从已确认技术方案创建发布评估、从已确认发布评估创建上线后分析的真实入口；发布评估保存真实 Bug、Jenkins、线上日志和 GitLab 指标上下文，上线后分析人工确认后会把 `bug_suggestions` 转为 `ai_post_release` 来源 Bug 记录。
- GitLab MR 预览和 diff 快照改为读取真实 GitLab 只读 API；产品 Git 资源需配置可解析的 `remote_url` 或 `GITLAB_BASE_URL` 以及只读 token 凭据引用，缺失配置时返回明确错误，不再静默生成本地假 MR。
- GitLab MR diff、变更文件数或单文件 diff 行数超限时记录 `gitlab_mr.snapshot_failed` 审计事件，保留实际 diff 大小、文件数、单文件行数、限制和关联需求/技术方案任务。
- GitLab MR diff 快照现在按 `repository_id + snapshot_hash` 复用已有快照，重复拉取相同 diff 不重复入库，并记录 `gitlab_mr.snapshot_reused` 审计事件。
- 低层 AI 任务创建会同步把技术方案和 Code Review 等后续任务追加到需求 `task_ids`，需求关闭、未审批或已驳回后返回状态错误，不再绕过需求状态机。
- 生命周期链路追踪扩展到真实 Bug、GitLab 每日代码指标、Jenkins 发布记录、线上日志指标、用户使用指标、用户反馈和迭代规划建议证据主体，并动态返回缺失上下文和来源明确的跨阶段风险信号。
- 明确 MVP 用户角色目录，新增 `/api/auth/roles` 角色查询接口、PostgreSQL `role_definitions` 可重复迁移脚本，并将用户管理角色录入改为固定多选。
- 角色目录补齐职责、数据范围、决策范围、权限点、可分配状态和排序信息；用户管理和知识权限配置均从后端角色目录加载固定选项，不再依赖前端静态角色定义或自由文本录入。
- 系统管理新增“角色管理”二级菜单，只读展示后端角色目录、职责、数据范围、决策范围和权限点，明确 MVP 不自由创建未定义角色。
- 角色目录补齐业务角色映射、可见入口和限制边界，角色管理和用户管理角色目录同步展示。
- 知识文档索引失败保留 `index_error` 并支持 `/api/knowledge/documents/{document_id}/retry-index` 重试，前端显示失败原因和重试操作。
- AI 任务启动接入 active/default OpenAI-compatible 模型网关配置，调用真实 `/chat/completions` 并解析 JSON 输出；模型日志只记录脱敏元数据，缺失密钥或 provider 调用失败时任务进入 failed，不再静默回退本地输出。
- 模型网关配置新增 provider 固定目录校验，新增或编辑时只允许 `openai_compatible`，避免错误 provider 保存为默认配置后污染任务执行。
- Code Review 执行器失败语义补齐：结构化报告生成失败返回 `CODE_REVIEW_EXECUTOR_FAILED`，任务停在 `code_review_executor_failed` 并记录 `code_review.executor_failed` 审计事件。
- 审计与运行列表新增真实详情弹窗和生命周期链路追踪操作，可从审计主体查看上下游、风险信号和缺失上下文。

### Changed
- 前端运营治理菜单将“用户洞察/迭代规划”展示名收敛为“用户洞察”，页面内继续保留使用趋势、用户反馈和迭代建议能力，文档以“用户洞察（含迭代规划建议）”说明领域边界。
- `PERSISTENCE_MODE` 默认值改为 `postgres`；非测试环境配置 `memory` 会 fail fast，`MemoryStore` 降级为 `APP_ENV=test/testing/pytest` 下的测试 helper。
- 前端产品管理、需求列表、迭代版本和产品上下文下拉改用批量版本接口与后端聚合字段，移除逐产品拉取版本导致的 N+1 页面查询。
- `/health` 的 `model_gateway` 状态改为优先读取持久化 active/default 模型网关配置，避免运行时模型网关可用但健康检查仍显示 `not_configured`。
- `/health` 新增 `data_access_mode`，在 PostgreSQL 运行时返回 `db_first_migration`，明确当前仍处于移除生产 `MemoryStore` 中间层的迁移期。
- 新增 `023_db_first_id_counters.sql` 和 PostgreSQL repository 发号能力，过渡期 `PersistentMemoryStore.new_id()` 在 repository 支持时优先委托数据库分配 ID，不再只依赖进程内 counter。
- 产品配置写接口新增 handler 级 repository 单记录写入/删除，覆盖产品、迭代版本、模块、Git 资源和相关系统；产品删除同步清理归属该产品的相关系统，避免遗留孤儿配置；新增禁用请求结束 `persist()` 后重建 store 的回归测试，验证这些写入不依赖全局同步。
- 产品配置核心 GET 接口改为 repository-first 读取，覆盖产品列表/详情、指定产品的版本、模块、Git 资源和关联系统；新增运行态 store 过期回归测试，验证页面查询不再依赖进程内产品配置集合。
- 用户使用指标、用户反馈和迭代建议列表改为 repository-first 读取，在 PostgreSQL 运行时由 SQL/repository 执行筛选和排序；新增运行态 store 过期回归测试，验证用户洞察和迭代规划页面查询不依赖进程内集合。
- 采集运行、待归属队列、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标列表改为 repository-first 读取，在 PostgreSQL 运行时由 SQL/repository 执行筛选和排序；新增运行态 store 过期回归测试，验证研发运营页面查询不依赖进程内集合。
- 需求台账新增 handler 级 repository 单记录写入/删除，覆盖需求创建、修改、审批、驳回、关闭和删除。
- 从需求生成产品详细设计 AI 任务新增 repository 事务写入，需求 `task_ids`/状态、AI task 和 `ai_task.created` 审计事件在 handler 返回前一并持久化。
- 后续 AI 任务创建新增 repository 事务写入，技术方案、开发计划、自动化测试、发布评估、上线后分析和 Code Review 任务创建会同步需求 `task_ids`/状态、AI task 和 `ai_task.created` 审计事件。
- 需求详情和 AI 任务详情改为在 PostgreSQL 运行时优先读取 task workflow repository source rows，运行态 store 过期时仍能返回结构表详情数据。
- 任务启动成功路径新增 repository 事务写入，AI task、模型调用日志、Human Review、Graph Run、Checkpoint 和启动审计事件在 handler 返回前一并持久化，并推进任务和 Review 的标准时间字段。
- 任务启动失败路径新增 repository 事务写入，模型配置失败、模型调用失败和 Code Review executor 失败会在返回错误前持久化 failed task、可选模型失败日志、`ai_task.retry_started` 和失败审计事件。
- Review approve/edit-approve 主路径新增 repository 事务写入，完成态 task/review/graph/checkpoint、需求状态、知识沉淀候选、可选 Bug/Code Review 报告和审计事件在 handler 返回前一并持久化，并记录 Review 决策时间与任务修改时间。
- Review reject 与 request-more-info 主路径新增 repository 事务写入，失败或等待补充状态、Review 决策字段、Graph Run/Checkpoint 和审计事件在 handler 返回前一并持久化。
- AI 任务 cancel 与 submit-more-info 新增 repository 状态写入，取消任务、取消待确认 Review、Graph Run/Checkpoint 状态和补充信息回到 draft 的任务输入在 handler 返回前一并持久化。
- 知识文档和知识沉淀审核新增 repository 事务写入，文档创建/更新/索引重试/删除、chunk 重建、沉淀采纳/拒绝、索引模型日志和审计事件在 handler 返回前一并持久化。
- 知识文档列表改为 repository-first 读取，权限角色、关键字、文档类型和索引状态过滤进入 SQL/repository 查询层，`chunk_count` 从结构表聚合返回。
- AI 助手聊天新增 repository 事务写入，成功路径会同步会话、用户消息、助手消息、模型日志和审计事件，模型调用失败会同步 failed 模型日志和审计事件。
- AI 助手会话列表和消息列表改为 repository-first 读取，按当前用户 `user_id` 在查询层隔离历史记录，运行态 store 过期时仍能返回本人会话和消息。
- GitLab MR / GitHub PR 快照新增 repository 单记录写入，快照成功、同 diff 复用和 diff 超限失败审计在 handler 返回前持久化；Code Review 报告生成/确认继续随任务启动和 Review 决策事务写入。
- GitHub PR 列表、GitLab MR 预览和 GitHub PR 预览的审计事件新增 handler 级 repository 写入，避免移除请求结束全局 `persist()` 后这些 GET 审计只停留在进程内 store。
- Bug 管理新增 repository 单记录写入/删除，Bug 创建、修改、删除和对应审计事件在 handler 返回前持久化，删除前清空指向被删 Bug 的重复归并引用。
- Bug 列表改为 repository-first 读取，产品、状态、严重级别和来源过滤进入 SQL/repository 查询层，运行态 store 过期时仍从结构表返回 Bug 数据。
- 采集运行、待归属队列、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标新增 repository 单记录写入，创建/更新/处理记录及审计事件在 handler 返回前持久化。
- 用户使用指标、用户反馈和迭代规划新增 repository 写入，反馈处理、建议生成、决策和转需求会在 handler 返回前持久化；转需求时同步写入新需求、建议、决策和完整审计事件。
- 生命周期上下文查询和首页 IT 团队看板新增 handler 级物化记录写入，查询生成的 lifecycle edges/risks 与 dashboard snapshot 在返回前写入 PostgreSQL 结构表；聚合读取全面 SQL/read model 化仍在迁移计划中。
- 生命周期上下文和首页 IT 团队看板读接口在 PostgreSQL 运行时改为读取 repository source rows，避免依赖全局运行时 store 的已缓存集合；新增运行时 store 过期场景的 source-row 回归测试。
- 请求结束全局 `persist()` 已从 API middleware 移除，所有 API 请求都不再通过请求结束同步进程内 store；模型网关配置创建、修改、删除和连接测试审计新增 handler 级 repository 写入，防止移除全局同步后丢失配置或审计。
- 模型网关配置列表和模型调用日志列表改为 repository-first 读取，运行态 store 过期时仍从结构表返回配置、脱敏状态和按 purpose/status/task 过滤后的模型日志。
- 审计列表改为 repository-first 读取，actor、event_type、ai_task、subject 和时间范围过滤进入 SQL/repository 查询层，运行态 store 过期时仍从结构表返回审计数据。
- PostgreSQL 运行时不再从 `app_state_snapshots` 恢复业务集合，手动 `PersistentMemoryStore.persist()` 也不再写入 app_state JSONB 快照；历史表保留用于非破坏性迁移兼容。
- 测试用例清单增加适用阶段口径，区分 MVP 必交、MVP 空状态、v1.1、v1.2 和生产就绪验证。
- 文档入口增加实现者最短路径，明确 P0 表、API、页面、测试和 runbook 的推荐落地顺序。
- 前端提交需求入口调整为需求管理查询表格，新增需求和配置类表单统一使用弹窗。
- 文档维护源切换为项目级 PRD/spec/API/test-case，`docs/design/` 转为历史归档。
- API 和测试用例文档对齐当前实现，包括登录字段、任务输入字段、Markdown 导出和审计查询参数。
- 统一补充信息后的状态契约：`waiting_more_info` 提交补充后回到 `draft`，再次启动后继续运行。
- 统一审计事件字段、健康检查枚举和 AI Brain 业务域示例。
- PRD 增加产品配置和模型网关配置验收标准。
- PRD 和测试用例对齐 v1 系列分阶段交付边界，拆分 MVP、v1.1、v1.2 人工确认门禁验收。
- PRD 和测试用例补充实际业务系统用户使用数据、用户反馈收集和 AI 主动迭代规划建议能力。
- 技术规格同步用户洞察/迭代规划模块、数据表、接口清单、状态流转、数据流、安全和风险设计。
- API 文档补充用户使用指标、用户反馈、AI 迭代规划建议、规划确认和相关错误码。
- 测试用例补充 AI 迭代规划建议不得自动创建正式需求、变更路线图或调整排期的断言。
- PRD、技术规格、API、测试用例、架构摘要和技术栈同步将内部 GitLab MR 代码 Review 提前纳入 v1 MVP，补充 MR 预览、diff 快照、可插拔 code-review 执行器、人工确认、内部报告归档和不回写 GitLab 的阶段边界。
- MVP-A/B/C 阶段边界调整为 MVP-A 包含内部 GitLab 只读绑定、MR 预览和 diff 快照，MVP-B 专注 code_review 执行器、正式 Review 报告和内部归档，MVP-C 专注知识治理和模拟 Issue。
- 部署 runbook 补充模型网关、内部 GitLab MR 预览、diff 快照和 code-review 执行器的 MVP 验证步骤。
- 前端框架约束升级为严格 Ant Design Pro：新增页面、导航、表格、卡片和工作台布局必须优先使用 Umi Max、ProLayout、ProComponents 与 antd，禁止回退到 Vite 自建壳子或手写全局导航。
- 模拟 Issue 写回从 GET 隐式写副作用改为 POST 显式生成；GET 只查询现有结果，未写回时返回 `not_written`。
- 早期文档补充源码状态：Docker 本地栈默认使用 PostgreSQL 用户表和运行状态快照持久化，`MemoryStore` 保留为测试/fallback；后续 GitLab/GitHub、模型网关和 DB-first 迁移记录已替代该阶段口径。
- 前端管理列表改为使用显式 `ai_brain_access_token` 登录态，不再在浏览器代码中内置 admin 登录凭据；API 失败时展示错误提示和 trace_id，不再回退到示例数据。
- 所有管理列表和任务中心移除前端本地兜底行，加载中不闪现样例数据，错误或无数据时保持空表。
- API 和技术规格对齐当前 CRUD 完成状态，补充删除接口、依赖占用错误语义和系统管理菜单位置。
- 产品、需求和 Bug 页面改为基于真实产品/版本上下文操作：新增产品默认创建 `v1` 版本，新增需求和登记 Bug 使用产品/版本下拉选择，不再要求用户手填数据库 ID。
- 后端管理接口补充产品编码、产品版本编码、产品模块编码、相关系统编码唯一性校验，以及用户角色、状态和主数据状态枚举校验；产品版本和模块删除会同时校验 AI 任务占用。
- `/api/audit/events` 补齐 `actor_id`、`created_from` 和 `created_to` 过滤，审计排查可以按操作者和时间范围组合查询。
- `/health` 的模型网关未配置状态从 `local_fallback` 调整为 `not_configured`，与任务启动不生成本地输出的运行语义保持一致。

### Deprecated
- `docs/design/` 不再作为后续版本迭代的维护目录。

### Removed
- 移除早期 MVP-A 后端长链路冒烟测试 `apps/api/tests/test_mvp_a_flow.py`，该覆盖已由需求生命周期、Graph Runtime、Review、审计和 DB-first 持久化拆分测试承接，并同步更新测试用例文档的自动化证据映射。
- 移除已合并到规范化本地开发指南的 `docs/development/local-environment.md`。

### Fixed
- 修复 PRD 和技术规格中指向不存在业务流程 HTML 的相对链接。
- 修复从快照持久化切换到结构表时，结构化产品表不完整导致历史需求引用产品外键失败的问题；加载结构表时保留快照中的旧主体并在下一次持久化迁移到结构表。
- 修复 PRD、技术规格、架构摘要、技术栈、测试用例和 CLAUDE 指令中业务入口数量、用户洞察/迭代规划模块、看板指标、Requirement 状态枚举、已删除 docs/design 引用和无效文档链接的不一致。
- 修复 AC10 用户洞察/迭代规划入口遗漏、Bug 管理阶段验收边界、需求到 AI 任务一对多关系和首页看板依赖项不一致。
- 修复测试用例中 v1 MVP 空状态入口与 v1.1/v1.2 完整闭环能力混用的问题。
- 修复跨阶段 P0/P1 口径混用问题，测试用例改为“适用阶段 + 阶段内优先级”，避免 v1.2 用例阻塞 MVP 发布。
- 修复 API 角色表出现 MVP 未实现 `member`/`tester` 写权限的问题，统一到 MVP 六类系统角色并标注 v1.1/v1.2 扩展。
- 修复 `/health` trace_id 约定、Requirement `task_created` 多任务语义、审计主体字段必填口径和 GBrain MVP 可选边界不一致。
- 补齐技术规格中 `gitlab_mr_snapshots` 表、MR 快照幂等索引、code-review 执行器超时、schema 校验和审计约束。
- 修复 README 对 v1 MVP 范围描述偏旧、测试规范工具链过泛和部署 runbook 验证项不足的问题。
- 合并单独维护的本地环境说明到规范化本地开发指南。
- 修复技术规格工作台入口表仍引用非 MVP 系统角色 `member` 的问题，需求管理入口对齐 `product_owner` 和 `rd_owner`。
- 修复 Docker 容器内 `/health` 仍探测 `127.0.0.1` 导致 Postgres/Redis 健康状态误报的问题，改为从连接 URL 解析依赖端点。
- 修复 `code_review` 报告在修改后采纳时未归档的问题，`approve` 和 `edit-approve` 均会确认报告并写入 `archived_at`。
- 修复 GitLab MR 快照和 `code_review` 任务缺少产品、需求、技术方案上下文一致性校验的问题。
- 修复补充信息状态可直接重新启动任务的问题，必须先提交 `/api/ai-tasks/{task_id}/more-info` 回到 `draft`。
- 修复 API 文档登录字段、错误 trace_id 结构、MR 快照响应字段和后续阶段写接口状态与当前实现不一致的问题。
- 修复 `technical_solution` 可复用其他需求产品详细设计任务的问题，新增需求、产品和版本一致性校验。
- 修复任务列表、任务详情、Review 详情、待确认列表和 graph run 查询缺少任务类型读权限过滤的问题。
- 修复生命周期视图和首页 IT 团队看板可通过聚合结果暴露无权 AI 任务、待确认 Review 和风险信号的问题，聚合前统一按任务读权限过滤。
- 修复 Git 仓库响应暴露 `credential_ref`、模型网关响应暴露 API key 片段以及初始化迁移字段与运行时对象不一致的问题。
- 修复真实页面操作中新建需求、登记 Bug 因产品/版本/模块上下文不一致导致提交失败的问题；产品删除允许无业务依赖时级联清理版本、模块和 Git 资源配置，仍会阻止已有需求、任务或 Bug 的产品删除。
- 修复 PostgreSQL 用户删除接口仅停用但列表仍展示的问题，用户管理页面“删除”操作现在会从用户表移除非当前用户。
- 修复保存成功后 CRUD 弹窗等待列表刷新完成才关闭的问题，页面操作现在会先关闭弹窗并异步刷新列表。
- 修复知识中心索引状态仍混用旧 `failed` 状态的问题，统一为 `index_failed`、`importing`、`pending_index`、`indexed` 和 `archived`。
- 修复 API/技术规格中用户删除和产品删除语义与当前实现不一致的问题。
- 修复前端收到 `TOKEN_EXPIRED` 等 401 认证错误后仍停留在业务页的问题，现在会清理本地登录态并跳转登录页。
- 修复 Markdown 导出接口未复用 AI 任务读取权限的问题，产品详细设计和技术方案导出不再对无关角色开放。
- 修复登录后 ProLayout 右上角用户标题仍可能停留在“未登录”的问题，登录态保存和退出会即时通知布局刷新。
- 修复历史 `app_state_snapshots` 中残留 GitLab MR 快照引用已删除 Git 仓库时，结构化持久化触发外键错误并导致登录等请求返回 500 的问题；恢复和保存前会清理无效 GitLab Review 记录。
- 修复生命周期链路追踪对 `human_review`、`code_review_report`、`gitlab_mr_snapshot`、`mock_issue`、`knowledge_deposit`、`audit_event` 和 `bug` 等审计主体退化为产品级结果的问题，现在会解析到对应任务链路，未知主体类型返回明确校验错误。
- 修复知识检索在 `indexed` 文档缺失 chunk 行时合成整篇文档结果的问题；现在只返回真实存在的 `knowledge_chunks`，索引不一致时保持空结果。

### Security
- 后端 MVP 骨架补充轻量角色边界：产品/需求维护、GitLab MR 只读预览、Review 决策、知识治理、模拟写回和审计查询按系统角色收敛，并覆盖 403 测试。
- 补充内部 GitLab MR 快照、code-review 执行器、用户反馈/使用数据采集失败和不可归属数据的审计要求。
- 明确 MR diff、用户反馈和使用数据进入模型前必须脱敏、限长，且 GitLab token 不得传给 code-review 执行器。
- 非本地环境默认禁用内置种子账号登录，除非显式开启受控的 `ALLOW_SEEDED_USERS=true`。
- 非本地环境的内置种子账号禁用逻辑统一覆盖 PostgreSQL 和 Memory 两种持久化模式。

---

## [1.0.0] - 2026-05-27

### Added
- 初始版本发布
- 核心功能实现

### Changed
-

### Fixed
-

---

## [0.1.0] - 2026-05-27

### Added
- 项目初始化

---

[Unreleased]: https://github.com/zeek428/e-ai-brain/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/zeek428/e-ai-brain/releases/tag/v1.0.0
[0.1.0]: https://github.com/zeek428/e-ai-brain/releases/tag/v0.1.0
