# 变更日志

所有重要的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 初始化 `apps/api` FastAPI 后端、`apps/web` Ant Design Pro 工作台、Docker Compose、本地环境示例、Dockerfile 和 PostgreSQL 初始化迁移脚本。
- 后端实现本地账号认证、trace_id envelope、健康检查、产品配置、需求审批、AI 任务、人审确认、Markdown 导出、GitLab MR 预览与 diff 快照、内部 Code Review 报告、知识检索/沉淀、模拟 Issue 幂等和审计查询的 MVP 骨架。
- 产品与平台配置补齐查询、局部更新、active_only 过滤、相关系统、模型网关配置、默认模型网关唯一性和 API key 脱敏响应。
- 需求管理补齐列表、详情、按产品/状态过滤、驳回、关闭、任务引用和 inactive 产品拦截。
- 知识沉淀补齐驳回接口、驳回原因、状态过滤和审计事件。
- AI 任务启动补齐 graph_run/checkpoint 记录、任务详情运行投影和 graph run 查询接口，为后续 LangGraph 持久化接入预留数据边界。
- AI 任务启动改为经由最小模型网关边界生成本地 fallback 输出，并记录不含完整 prompt/output 的模型调用元数据日志。
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
- 新增后端 pytest 覆盖基础健康/认证、MVP-A 需求到详细设计、技术方案导出、GitLab MR 快照、Code Review 报告和知识治理闭环。
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
- 产品配置开始细粒度 PostgreSQL 持久化，产品、版本、模块和 Git 资源会同步写入 `products`、`product_versions`、`product_modules`、`product_git_repositories`，并在 API 启动时从结构表恢复。
- 需求台账开始细粒度 PostgreSQL 持久化，需求创建、审批、驳回、关闭和任务引用会同步写入 `requirements`，并在 API 启动时从结构表恢复。
- AI 任务开始细粒度 PostgreSQL 持久化，任务类型、标题、状态、需求快照、产品上下文、输入输出和当前步骤会同步写入 `ai_tasks`，并在 API 启动时从结构表恢复。
- 人工确认和 Graph 运行态开始细粒度 PostgreSQL 持久化，`human_reviews`、`graph_runs`、`graph_checkpoints` 会记录 Review 决策、运行状态、检查点和 state snapshot，并在 API 启动时回填任务运行关联。
- 后端补齐当前管理主体 CRUD：产品及版本/模块/Git 资源、相关系统、模型网关配置、需求、知识文档、Bug 和用户均支持新增/更新/删除，删除前保留依赖占用校验和审计记录。
- 前端产品管理、需求管理、Bug 管理、知识中心和用户管理新增真实表单弹窗、编辑按钮、删除按钮和接口刷新逻辑，不再停留在列表 demo。
- 新增“系统管理”一级菜单，并将“用户管理”作为其二级菜单；`/users` 旧入口重定向到 `/system/users`。
- 系统管理新增“模型网关”二级菜单，支持模型网关配置列表、新增、编辑和删除；列表只展示 API Key 是否已配置，编辑留空不覆盖服务端密钥。
- 产品管理新增“配置”弹窗，可维护产品版本、模块和 Git 资源；Git 凭据引用只在提交时发送，列表仅显示已配置状态，不回显凭据引用或 token。
- 研发运营看板和用户洞察/迭代规划页面改为读取真实 API 聚合列表；后端未接入采集器时返回空集合，不再返回 placeholder 状态或伪造统计数据。
- 首页 IT 团队看板从静态欢迎页升级为真实 MVP 聚合视图，展示产品、需求、AI 任务、待确认 Review、知识沉淀和审计摘要。
- 需求管理页面新增审批通过、驳回和生成产品详细设计任务操作；任务中心新增启动 draft 任务和确认待 Review 输出的主链路操作。
- 前端运行时用户信息改为从登录响应或 `/api/auth/me` 读取，右上角不再硬编码管理员姓名。
- 任务中心新增基于已完成产品详细设计创建技术方案任务，以及已完成技术方案 Markdown 导出预览入口。
- 任务中心新增基于已完成技术方案选择产品 GitLab 仓库、预览 MR、生成 diff 快照、创建 `code_review` 任务和查看内部 Code Review 报告的真实 API 链路。
- 任务管理页面改为与需求管理等页面一致的管理列表风格，移除阶段卡片和左右并排确认台，待确认项改为工具栏或行操作弹窗处理。
- 任务中心新增已完成任务的模拟 Issue 查询/生成弹窗；知识中心新增知识沉淀候选审核弹窗，支持批准入库和拒绝，补齐 MVP-C 页面操作闭环。
- 任务管理列表行内操作收敛为单一“操作”入口，启动、确认、生成方案、导出、Code Review、模拟 Issue 和查看报告统一在任务操作弹窗中触发，避免横向堆叠按钮。
- 知识中心新增真实知识检索弹窗，调用 `/api/knowledge/search` 展示权限过滤后的知识来源和内容摘要，不展示兜底示例结果。
- 任务管理补齐 MVP-A 补充信息闭环，可在待确认弹窗要求补充，并在 `waiting_more_info` 任务操作弹窗提交补充内容使任务回到草稿。
- 任务管理操作弹窗改为上方任务摘要、下方纵向操作的弹出结构，并将列表中的任务类型展示为业务中文标签，避免左右分栏式操作区。
- 任务管理操作弹窗标题收敛为固定“任务操作”，长任务名保留在摘要区展示，避免弹窗标题区拥挤并保持与需求管理等管理弹窗一致。
- 任务管理创建 Code Review 的参数区改为弹窗内纵向表单，并清理旧任务中心左右分栏样式遗留，保持与需求管理等管理页一致。
- GitLab MR 预览和 diff 快照改为读取真实 GitLab 只读 API；产品 Git 资源需配置可解析的 `remote_url` 或 `GITLAB_BASE_URL` 以及只读 token 凭据引用，缺失配置时返回明确错误，不再静默生成本地假 MR。
- GitLab MR diff、变更文件数或单文件 diff 行数超限时记录 `gitlab_mr.snapshot_failed` 审计事件，保留实际 diff 大小、文件数、单文件行数、限制和关联需求/技术方案任务。
- 明确 MVP 用户角色目录，新增 `/api/auth/roles` 角色查询接口、PostgreSQL `role_definitions` 可重复迁移脚本，并将用户管理角色录入改为固定多选。
- 角色目录补齐职责、数据范围、决策范围、权限点、可分配状态和排序信息；用户管理和知识权限配置均从后端角色目录加载固定选项，不再依赖前端静态角色定义或自由文本录入。
- AI 任务启动接入 active/default OpenAI-compatible 模型网关配置，调用真实 `/chat/completions` 并解析 JSON 输出；模型日志只记录脱敏元数据，缺失密钥或 provider 调用失败时任务进入 failed，不再静默回退本地输出。
- Code Review 执行器失败语义补齐：结构化报告生成失败返回 `CODE_REVIEW_EXECUTOR_FAILED`，任务停在 `code_review_executor_failed` 并记录 `code_review.executor_failed` 审计事件。
- 审计与运行列表新增真实详情弹窗和生命周期链路追踪操作，可从审计主体查看上下游、风险信号和缺失上下文。

### Changed
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
- 文档补充当前源码状态：Docker 本地栈默认使用 PostgreSQL 用户表和运行状态快照持久化，`MemoryStore` 保留为测试/fallback；真实 GitLab 和模型调用仍需后续接入。
- 前端管理列表改为使用显式 `ai_brain_access_token` 登录态，不再在浏览器代码中内置 admin 登录凭据；API 失败时展示错误提示和 trace_id，不再回退到示例数据。
- 所有管理列表和任务中心移除前端本地兜底行，加载中不闪现样例数据，错误或无数据时保持空表。
- API 和技术规格对齐当前 CRUD 完成状态，补充删除接口、依赖占用错误语义和系统管理菜单位置。
- 产品、需求和 Bug 页面改为基于真实产品/版本上下文操作：新增产品默认创建 `v1` 版本，新增需求和登记 Bug 使用产品/版本下拉选择，不再要求用户手填数据库 ID。
- 后端管理接口补充产品编码、产品版本编码、产品模块编码、相关系统编码唯一性校验，以及用户角色、状态和主数据状态枚举校验；产品版本和模块删除会同时校验 AI 任务占用。
- `/api/audit/events` 补齐 `actor_id`、`created_from` 和 `created_to` 过滤，审计排查可以按操作者和时间范围组合查询。

### Deprecated
- `docs/design/` 不再作为后续版本迭代的维护目录。

### Removed
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
- 修复 Git 仓库响应暴露 `credential_ref`、模型网关响应暴露 API key 片段以及初始化迁移字段与运行时对象不一致的问题。
- 修复真实页面操作中新建需求、登记 Bug 因产品/版本/模块上下文不一致导致提交失败的问题；产品删除允许无业务依赖时级联清理版本、模块和 Git 资源配置，仍会阻止已有需求、任务或 Bug 的产品删除。
- 修复 PostgreSQL 用户删除接口仅停用但列表仍展示的问题，用户管理页面“删除”操作现在会从用户表移除非当前用户。
- 修复保存成功后 CRUD 弹窗等待列表刷新完成才关闭的问题，页面操作现在会先关闭弹窗并异步刷新列表。
- 修复 API/技术规格中用户删除和产品删除语义与当前实现不一致的问题。
- 修复前端收到 `TOKEN_EXPIRED` 等 401 认证错误后仍停留在业务页的问题，现在会清理本地登录态并跳转登录页。
- 修复 Markdown 导出接口未复用 AI 任务读取权限的问题，产品详细设计和技术方案导出不再对无关角色开放。
- 修复登录后 ProLayout 右上角用户标题仍可能停留在“未登录”的问题，登录态保存和退出会即时通知布局刷新。

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
