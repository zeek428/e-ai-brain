# 企业 AI 大脑平台技术规格

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.268 |
| 适用系统版本 | ≥ v1.0.0 |
| 文档状态 | Approved |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.1.268 | 2026-06-10 | 知识管理第一阶段实现落地：知识空间、目录、MinIO/S3-compatible 资产、导入任务、chunk set、上传预览和空间权限过滤进入当前架构 | Codex |
| v1.1.267 | 2026-06-10 | 新增知识管理升级设计：明确知识空间、目录、文档、MinIO 资产、导入任务、解析器适配、父子分块、权限过滤和分阶段实施边界 | Codex |
| v1.1.266 | 2026-06-10 | 补充 MaxCompute 用户反馈洞察抽取实现：`user_feedback_insight_extract` 定时作业消费插件返回 `$.insights` 并通过用户反馈 service 写入，插件动作页面支持场景模板和高级 JSON 编辑 | Codex |
| v1.1.276 | 2026-06-11 | 补充插件配置体验优化：连接测试诊断报告、系统变量预览、动作请求预览/试运行、可视化参数与 JSON 双向同步、定时作业插件输入映射表格化 | Codex |
| v1.1.265 | 2026-06-10 | 新增插件管理第一阶段实现：补充 `integration_plugins`、`plugin_connections`、`plugin_actions`、`plugin_invocation_logs` 数据模型，定时作业可通过插件动作调用 HTTP/MCP HTTP 集成并保存插件快照、调用日志和审计 | Codex |
| v1.1.264 | 2026-06-10 | 新增定时系统作业与 AI 能力装配设计：补充 `ai_skills`、`ai_agents`、`scheduled_jobs`、`scheduled_job_runs` 数据模型，明确定时采集、AI 分析、Agent/Skill 快照、锁租约、审计和人工确认边界 | Codex |
| v1.1.263 | 2026-06-09 | 迭代版本新增版本级代码分支配置，`product_version_branch_configs` 结构表与 API 支持维护多仓库基准分支、开发分支、状态和来源 | Codex |
| v1.1.262 | 2026-06-09 | RBAC 重设计评审完成后新增开发实施计划，明确数据库迁移、授权服务、系统角色 API、动态菜单、部门、产品成员、知识空间和业务接口权限迁移的分阶段开发顺序 | Codex |
| v1.1.261 | 2026-06-07 | RBAC 重设计确认外部 SSO 身份映射原则：外部用户必须绑定到系统 users.id 后才能获得部门、角色、产品成员和知识空间授权，SSO 不直接下发权限 | Codex |
| v1.1.260 | 2026-06-07 | RBAC 重设计确认组织/部门、产品成员和知识空间决策：人员归属部门，产品范围由产品管理页成员配置维护，知识权限使用独立知识空间，高危权限由系统管理员配置并审计 | Codex |
| v1.1.259 | 2026-06-07 | RBAC 重设计补充菜单权限与左侧导航：角色可配置功能菜单，用户登录后返回 menu_tree，前端左侧按授权菜单渲染，后端仍按权限点和数据范围强制校验 | Codex |
| v1.1.258 | 2026-06-07 | RBAC 重设计补充研发交付扩展预置角色：开发工程师、测试负责人、测试人员和发布负责人，明确测试 Bug 登记/验证、自动化测试确认和发布评估权限边界 | Codex |
| v1.1.257 | 2026-06-07 | 新增系统权限管理 RBAC 重设计文档，明确角色 CRUD、权限点、用户角色关系、数据范围授权、审计和从固定六角色模型迁移的目标方案 | Codex |
| v1.1.256 | 2026-06-07 | 研发运营看板更名为日志监控，前端页面仅保留 GitLab、Jenkins 和线上日志指标；采集运行记录与待归属数据队列降为历史兼容 API，不再作为当前页面功能入口 | Codex |
| v1.1.255 | 2026-06-07 | 用户洞察新增用户反馈转需求闭环，需求新增来源字段并支持来源筛选/排序；用户洞察页面移除手工登记使用指标和生成迭代建议入口，聚焦反馈详情、处理和转需求 | Codex |
| v1.1.254 | 2026-06-07 | Code Review 报告新增只读 Review 结论回写模板，任务中心报告弹窗展示可复制 Markdown 模板，用于人工贴回 GitLab MR / GitHub PR；系统继续保持只读 Review 流程，不自动远端回写 | Codex |
| v1.1.253 | 2026-06-07 | AI 助手从系统上下文摘要回答升级为后端工具化查询：聊天前按用户问题生成 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等 read-model 工具结果，模型优先依据 `system_context.tool_results` 回答，助手消息 metadata 持久化 `tool_results` 和引用链接 | Codex |
| v1.1.252 | 2026-06-06 | Code Review 报告弹窗新增需求全链路跳转入口，报告可从任务中心直接回到对应需求的完整交付链路，补齐 Review 报告到需求全链路的闭环追踪 | Codex |
| v1.1.251 | 2026-06-06 | GitHub PR / GitLab MR 代码 Review 闭环增强：预览返回权限诊断，快照响应返回上一快照引用、diff 新增/修改/删除对比和复用标记，任务中心展示快照结果用于 PR 刷新、重试和配置排查 | Codex |
| v1.1.250 | 2026-06-06 | persistence.py 大文件拆分继续收口：任务启动、Review 决策和任务状态更新的跨表写事务下沉到 TaskReadRepository，PostgresSnapshotRepository 只保留公开方法委托和跨域回调装配 | Codex |
| v1.1.249 | 2026-06-06 | persistence.py 大文件拆分继续收口：删除需求和任务运行态私有 upsert 兼容入口，跨域事务直接调用 RequirementReadRepository 和 TaskReadRepository 的领域 upsert 方法 | Codex |
| v1.1.248 | 2026-06-06 | persistence.py 大文件拆分继续收口：删除仅测试引用的产品配置私有 upsert 兼容入口，产品配置写入边界统一通过 ProductConfigReadRepository 的公开保存方法验证 | Codex |
| v1.1.247 | 2026-06-06 | persistence.py 大文件拆分继续收口：删除未引用的知识沉淀 row 转换旧副本，并将通用 delete_missing/delete_missing_ids 表维护 helper 抽取到 TableMaintenanceRepository，PostgresSnapshotRepository 仅保留回调委托入口 | Codex |
| v1.1.246 | 2026-06-06 | persistence.py 大文件拆分继续收口：数据库发号器和历史 app_state_snapshots 读写抽取到 SystemStateRepository，PostgresSnapshotRepository 仅保留 next_id/load/save 委托入口 | Codex |
| v1.1.245 | 2026-06-06 | persistence.py 大文件拆分继续收口：产品详情、产品版本、产品模块、产品 Git 仓库和相关系统读取 SQL 下沉到 ProductConfigReadRepository，PostgresSnapshotRepository 仅保留产品配置读取委托入口 | Codex |
| v1.1.244 | 2026-06-06 | 管理列表统一表格规范继续增强：ManagementListPage 增加稳定根样式入口，统一约束工具栏换行、表格单元格换行和右固定操作列不换行，降低需求、角色、用户洞察、DevOps 等宽表页面在中等视口下变形风险 | Codex |
| v1.1.243 | 2026-06-06 | 需求管理列表布局优化：固定更宽业务列、操作列收敛为“全链路 + 更多”、详情页入口进入更多菜单，并将表格横向滚动宽度提高到 1600，降低中等宽度页面列挤压 | Codex |
| v1.1.242 | 2026-06-06 | persistence.py 大文件拆分继续收口：PersistentMemoryStore 测试兼容层抽取到 persistent_memory_store，persistence.py 保留兼容 re-export 并继续收窄为 PostgreSQL snapshot repository 实现 | Codex |
| v1.1.241 | 2026-06-06 | persistence.py 大文件拆分继续收口：生产 PostgreSQL 运行时容器 PostgresRuntimeStore 抽取到 persistence_runtime，main.py 直接从 runtime 模块装配，persistence.py 保留兼容 re-export 和 snapshot repository 实现 | Codex |
| v1.1.240 | 2026-06-06 | persistence.py 大文件拆分继续收口：snapshot payload/load/save、集合合并、上下文清理、counter 同步和恢复链路 helper 抽取到 persistence_payloads，persistence.py 继续收窄为运行时 store 与 PostgreSQL repository 实现 | Codex |
| v1.1.239 | 2026-06-06 | persistence.py 大文件拆分继续收口：仓储 Protocol、集合字段常量和 snapshot contract 抽取到 persistence_contracts，persistence.py 聚焦 payload helper、运行时 store 和 PostgreSQL repository 实现 | Codex |
| v1.1.238 | 2026-06-06 | 后端大文件拆分继续收口：main.py 删除剩余 repository/source-store/save legacy helper，收敛为 FastAPI 装配、启动运行时、middleware 和异常处理入口；任务工作流 PostgreSQL source context 下沉到 task_workflow_context 且不继承 MemoryStore | Codex |
| v1.1.237 | 2026-06-06 | 管理列表统一表格规范继续增强：自定义渲染列默认包裹稳定单元格容器，长文本、Tag 和 Space 组合不得撑开宽表或造成角色/用户洞察/DevOps 等页面变形 | Codex |
| v1.1.236 | 2026-06-06 | 需求全链路详情新增版本内多需求对比，在需求归属迭代版本时展示同版本需求数量、状态分布和当前需求位置，便于版本级交付验收 | Codex |
| v1.1.235 | 2026-06-06 | 需求全链路详情新增“导出链路报告”能力，前端基于同一 full-chain read model 生成 Markdown 报告，覆盖需求、产品、迭代版本、阶段实体摘要和时间线，便于真实迭代测试留痕 | Codex |
| v1.1.234 | 2026-06-06 | 需求全链路详情时间线新增类型筛选，支持在同一需求链路内按需求、AI 任务、Review、代码评审、Bug、发布和知识沉淀等事件类型聚焦查看，并显示筛选后事件数量 | Codex |
| v1.1.233 | 2026-06-06 | 模型网关配置列表纳入服务端分页/筛选/排序和查询性能观测：`GET /api/system/model-gateway-configs` 在分页模式下返回 `query/performance`，支持配置名、provider、状态、默认配置、Chat/Embedding 模型和 Embedding 连接模式筛选；前端模型网关页接入远程列表模式 | Codex |
| v1.1.232 | 2026-06-06 | 角色管理列表纳入服务端分页/筛选/排序和查询性能观测：`GET /api/auth/roles` 在分页模式下返回 `query/performance`，支持角色、分类、业务角色、可见入口、权限点和状态筛选；前端角色页接入远程列表模式 | Codex |
| v1.1.231 | 2026-06-06 | 任务管理待确认 Review 子表纳入统一表格规范：固定布局、横向滚动、摘要省略和操作列右固定，降低确认按钮拥挤和弹窗列宽变形风险；任务批量重试/取消现有状态机与回归验证保持不变 | Codex |
| v1.1.230 | 2026-06-06 | 用户管理列表纳入管理类服务端分页/筛选/排序和查询性能观测：`GET /api/users` 支持用户名、显示名、角色、状态筛选，PostgreSQL 运行时优先由 users SQL read model 返回分页结果；前端用户管理页接入远程列表模式和角色下拉筛选 | Codex |
| v1.1.229 | 2026-06-06 | 管理列表统一表格规范继续推进：ManagementListPage 默认固定布局、按显示列宽计算横向滚动、默认长文本省略和操作列右固定；角色、DevOps 采集运行/待归属列表补齐固定列宽、横向滚动和详情承载，降低列宽变形风险 | Codex |
| v1.1.228 | 2026-06-06 | persistence.py 大文件拆分继续推进：生命周期上下文 edge/risk 和首页看板快照保存/写入 SQL upsert 归入 LifecycleDashboardReadRepository，PostgresSnapshotRepository 保留生命周期/看板写入委托入口 | Codex |
| v1.1.227 | 2026-06-06 | persistence.py 大文件拆分继续推进：采集运行和待归属队列保存、单记录保存和写入 SQL upsert 归入 OperationalCollectionReadRepository，PostgresSnapshotRepository 保留采集/归属写入委托入口和审计回调 | Codex |
| v1.1.226 | 2026-06-06 | persistence.py 大文件拆分继续推进：用户反馈、用户使用指标、迭代建议和迭代决策保存/写入 SQL upsert 归入 UserInsightReadRepository，PostgresSnapshotRepository 保留用户洞察写入委托入口和审计/需求回调 | Codex |
| v1.1.225 | 2026-06-06 | persistence.py 大文件拆分继续推进：GitLab daily、Jenkins release 和线上日志指标保存、单记录保存和写入 SQL upsert 归入 DevopsReadRepository，PostgresSnapshotRepository 保留 DevOps 写入委托入口和审计回调 | Codex |
| v1.1.224 | 2026-06-06 | persistence.py 大文件拆分继续推进：知识文档、知识 chunk、知识沉淀保存/删除、引用清理和写入 SQL upsert 归入 KnowledgeReadRepository，PostgresSnapshotRepository 保留知识写入委托入口和审计/模型日志回调 | Codex |
| v1.1.223 | 2026-06-06 | persistence.py 大文件拆分继续推进：Bug 保存、单记录保存/删除、重复缺陷引用清理和 bugs 写入 SQL upsert 归入 BugReadRepository，PostgresSnapshotRepository 保留 Bug 写入委托入口 | Codex |
| v1.1.222 | 2026-06-06 | persistence.py 大文件拆分继续推进：Graph Run、Graph Checkpoint 和 Human Review 运行态保存/upsert 归入 TaskReadRepository，PostgresSnapshotRepository 保留任务运行态写入委托入口 | Codex |
| v1.1.221 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 任务主表保存和 ai_tasks 写入 SQL upsert 归入 TaskReadRepository，PostgresSnapshotRepository 保留任务写入委托入口和 Review/Graph 跨域事务回调 | Codex |
| v1.1.220 | 2026-06-06 | persistence.py 大文件拆分继续推进：需求台账保存、单记录保存/删除和 requirements 写入 SQL upsert 归入 RequirementReadRepository，PostgresSnapshotRepository 保留需求写入委托入口和跨域事务回调 | Codex |
| v1.1.219 | 2026-06-06 | persistence.py 大文件拆分继续推进：产品、迭代版本、产品模块、产品 Git 仓库和相关系统写入 SQL upsert 归入 ProductConfigReadRepository，PostgresSnapshotRepository 保留产品配置写入委托入口和审计回调 | Codex |
| v1.1.218 | 2026-06-06 | persistence.py 大文件拆分继续推进：审计事件保存和 audit_events 写入 SQL upsert 归入 AuditReadRepository，PostgresSnapshotRepository 保留审计写入委托入口和跨域审计回调 | Codex |
| v1.1.217 | 2026-06-06 | persistence.py 大文件拆分继续推进：GitLab MR / GitHub PR 兼容快照和代码评审报告写入 SQL upsert 归入 GitReviewReadRepository，PostgresSnapshotRepository 保留 Git review 写入委托入口和审计回调 | Codex |
| v1.1.216 | 2026-06-06 | persistence.py 大文件拆分继续推进：模拟 Issue 写回行转换和 mock_issues 写入 SQL upsert 归入 MockWritebackReadRepository，PostgresSnapshotRepository 保留写回写入委托入口和审计回调 | Codex |
| v1.1.215 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 助手会话/消息写入 SQL upsert 归入 AssistantChatReadRepository，PostgresSnapshotRepository 保留助手历史写入委托入口和跨域模型日志/审计回调 | Codex |
| v1.1.214 | 2026-06-06 | persistence.py 大文件拆分继续推进：模型网关配置/日志写入 SQL upsert 归入 ModelGatewayReadRepository，PostgresSnapshotRepository 保留写入委托入口和跨域模型日志薄委托 | Codex |
| v1.1.213 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中任务工作流、Review 决策、Graph checkpoint、知识沉淀/Bug 建议生成和 Markdown 导出旧实现副本，相关契约继续由 ai_tasks、markdown_export、mock_writeback 和代码评审服务承接 | Codex |
| v1.1.212 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 model_gateway 和 ai_tasks services 承接的 OpenAI-compatible chat/embedding、模型日志、token 估算和代码评审 executor 旧 helper 副本 | Codex |
| v1.1.211 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 dashboard_metrics、devops_metrics 和 user_insights services 承接的看板产品归属过滤、DevOps 统一列表和用户洞察统一列表投影旧 helper 副本 | Codex |
| v1.1.210 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 operational_records service 承接的采集运行、待归属处理、GitLab/Jenkins/线上日志指标校验旧 helper 副本，保持 DevOps 明细、采集和归属 API 契约不变 | Codex |
| v1.1.209 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 requirements service 承接的需求全链路 payload/时间线旧 helper 副本，保持需求详情、全链路聚合、任务读权限和 DB-first stale runtime 契约不变 | Codex |
| v1.1.208 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 knowledge_documents、knowledge_search 和 knowledge_deposits services 承接的知识索引/检索旧 helper 副本，保持知识 API、Embedding 兜底、权限过滤和 DB-first stale runtime 契约不变 | Codex |
| v1.1.207 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 lifecycle_context service 承接的生命周期上下文旧 helper 副本，保留生命周期 API、dashboard source rows 和审计产品过滤契约不变 | Codex |
| v1.1.206 | 2026-06-06 | persistence.py 大文件拆分继续推进：业务大脑配置恢复读取 SQL 查询归入 BrainAppReadRepository，PostgresSnapshotRepository 仅保留委托入口，保持 rd_brain 只读配置和 PostgreSQL 运行时契约不变 | Codex |
| v1.1.205 | 2026-06-06 | persistence.py 大文件拆分继续推进：知识文档、知识 chunk 和知识沉淀恢复读取 SQL 查询归入 KnowledgeReadRepository，保持知识恢复、知识列表/检索 read model 和 DB-first stale runtime 契约不变 | Codex |
| v1.1.204 | 2026-06-06 | persistence.py 大文件拆分继续推进：Bug 恢复读取 SQL 查询归入 BugReadRepository，保持 Bug 恢复、Bug 管理列表 SQL read model、版本归属和 DB-first 兼容契约不变 | Codex |
| v1.1.203 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 任务、Graph Run、Graph Checkpoint 和 Human Review 恢复读取 SQL 查询归入 TaskReadRepository，保持任务/Review/Graph 恢复、任务列表 SQL read model 和 DB-first 兼容契约不变 | Codex |
| v1.1.202 | 2026-06-06 | persistence.py 大文件拆分继续推进：需求台账恢复读取 SQL 查询归入 RequirementReadRepository，保持需求恢复、需求列表 SQL read model、负责人字段和 DB-first 兼容契约不变 | Codex |
| v1.1.201 | 2026-06-06 | persistence.py 大文件拆分继续推进：产品、迭代版本、产品模块、产品 Git 仓库和相关系统恢复读取 SQL 查询归入 ProductConfigReadRepository，保持产品配置恢复、列表 SQL read model 和 DB-first 兼容契约不变 | Codex |
| v1.1.200 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 助手会话和消息恢复读取 SQL 查询归入 AssistantChatReadRepository，保持用户级历史隔离、消息 references 和 DB-first 恢复契约不变 | Codex |
| v1.1.199 | 2026-06-06 | persistence.py 大文件拆分继续推进：用户使用指标、用户反馈和迭代规划建议/决策恢复/列表读取 SQL 查询归入 UserInsightReadRepository，保持用户洞察统一列表、看板 source rows 和助手上下文契约不变 | Codex |
| v1.1.198 | 2026-06-06 | persistence.py 大文件拆分继续推进：GitLab daily、Jenkins release 和线上日志原始指标恢复/列表读取 SQL 查询归入 DevopsReadRepository，保持 DevOps 明细和看板 source rows 契约不变 | Codex |
| v1.1.197 | 2026-06-06 | persistence.py 大文件拆分继续推进：生命周期上下文和首页看板快照/source rows 读取与组装抽取为 LifecycleDashboardReadRepository，保持 DB 派生看板、权限过滤和慢查询缓存契约不变 | Codex |
| v1.1.196 | 2026-06-06 | persistence.py 大文件拆分继续推进：模拟 Issue 写回恢复读取 SQL 查询抽取为 MockWritebackReadRepository，保持幂等 key 聚合、Issue payload 投影和恢复读取契约不变 | Codex |
| v1.1.195 | 2026-06-06 | persistence.py 大文件拆分继续推进：GitLab MR / GitHub PR 兼容快照和代码评审报告恢复读取 SQL 查询抽取为 GitReviewReadRepository，保持快照、报告、任务链接和恢复计数器契约不变 | Codex |
| v1.1.194 | 2026-06-06 | persistence.py 大文件拆分继续推进：采集运行和待归属队列恢复快照/列表读取 SQL 查询抽取为 OperationalCollectionReadRepository，保持列表过滤、真实空集合和 DB-first stale runtime 契约不变 | Codex |
| v1.1.193 | 2026-06-06 | persistence.py 大文件拆分继续推进：审计事件恢复快照和审计列表读取 SQL 查询抽取为独立 AuditReadRepository，保持主体/操作者/时间过滤、sequence 排序和 query/performance 观测契约不变 | Codex |
| v1.1.192 | 2026-06-06 | persistence.py 大文件拆分继续推进：模型网关配置列表和模型调用日志列表读取 SQL 查询抽取为独立 ModelGatewayReadRepository，保持配置脱敏、日志过滤和排序响应契约不变 | Codex |
| v1.1.191 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 助手会话列表和会话消息读取 SQL 查询抽取为独立 AssistantChatReadRepository，保持用户级历史隔离和消息 references 响应契约不变 | Codex |
| v1.1.190 | 2026-06-06 | persistence.py 大文件拆分继续推进：知识文档列表、知识沉淀列表/详情、可读向量 chunk 检查和知识 chunk 搜索 SQL 查询抽取为独立 KnowledgeReadRepository，PostgresSnapshotRepository 仅保留委托入口 | Codex |
| v1.1.189 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已迁往 git_review、user_insights 和 lifecycle_context service 的 GitHub/GitLab 预览/快照、用户洞察/迭代规划和生命周期 read model 遗留实现副本，保留现有 API 契约与回归测试 | Codex |
| v1.1.188 | 2026-06-06 | 生命周期上下文 handler 移除 legacy main 回调，上下游实体追踪、v1.2 证据匹配、风险信号、缺失上下文和 lifecycle edge/risk materialize 收口到 lifecycle_context service | Codex |
| v1.1.187 | 2026-06-06 | GitLab MR 与 GitHub PR 预览/列表/快照 handler 移除 legacy main 回调，provider API 读取、diff 风险摘要、快照限制校验、审计和 DB-first 保存收口到 git_review service | Codex |
| v1.1.186 | 2026-06-06 | 用户洞察与迭代规划 handler 移除 legacy main 回调，使用指标、用户反馈、迭代建议和建议决策的列表查询、状态机校验、上下文校验、审计和 DB-first 保存收口到 user_insights service | Codex |
| v1.1.185 | 2026-06-06 | DevOps 指标明细 handler 移除 legacy main 回调，GitLab 每日代码指标、Jenkins 发布记录和线上日志指标的列表查询、上下文校验、指标校验、审计和 DB-first 保存收口到 operational_records service | Codex |
| v1.1.184 | 2026-06-06 | 采集运行与待归属处理 handler 移除 legacy main 回调，collector run 和 pending attribution 的列表查询、状态机校验、上下文校验、审计和 DB-first 保存收口到 operational_records service | Codex |
| v1.1.183 | 2026-06-06 | AI 任务创建 handler 移除 legacy main 回调，技术方案/后续任务/发布准备/发布后分析/代码评审上下文校验、产品上下文快照、需求状态推进、审计和 DB-first 保存收口到 ai_tasks service；tasks router 已整体不再回调 legacy main | Codex |
| v1.1.182 | 2026-06-06 | AI 任务批量重试 handler 移除 legacy main 回调，重复/不存在/不可重试 skipped、失败重试复用 start service、失败仍可解释返回、批次审计和 repository 保存收口到 ai_tasks service | Codex |
| v1.1.181 | 2026-06-06 | Review 决策 handler 移除 legacy main 回调，审批、编辑后审批、驳回和补充信息请求的状态机、需求推进、Bug 建议生成、知识沉淀、Graph checkpoint、Code Review 报告确认和 DB-first 保存契约收口到 ai_tasks service | Codex |
| v1.1.180 | 2026-06-06 | AI 任务启动 handler 移除 legacy main 回调，`POST /api/ai-tasks/{task_id}/start` 直接调用 ai_tasks service；模型网关失败注入测试改为 patch model_gateway service opener，启动、失败重试、Graph Run、Code Review 报告和 DB-first 保存契约保持不变 | Codex |
| v1.1.179 | 2026-06-06 | AI 任务启动业务逻辑下沉到 ai_tasks service，模型调用失败/配置失败、Code Review 执行器失败、Human Review 创建、Graph Run/Checkpoint 创建、Code Review 报告生成和 DB-first 保存契约保持不变；main.py 暂保留薄委托以兼容现有 opener 注入 | Codex |
| v1.1.178 | 2026-06-06 | AI 任务启动依赖的模型网关任务调用 helper 从 main.py 下沉到 model_gateway service，保留 URL opener 注入以兼容失败重试测试，为 start_ai_task 后续迁移到 ai_tasks service 做准备 | Codex |
| v1.1.177 | 2026-06-06 | AI 任务批量取消 handler 移除 legacy main 回调，重复/不存在/终态 skipped 明细、逐任务取消、pending Review 取消、Graph Run 取消 checkpoint、逐任务审计、批次审计和 repository 保存收口到 ai_tasks service | Codex |
| v1.1.176 | 2026-06-06 | AI 任务取消和补充信息提交 handler 移除 legacy main 回调，任务工作流写上下文、Graph Run 取消 checkpoint、pending Review 取消、more_info_answers 追加、审计事件和任务状态 repository 保存收口到 ai_tasks service | Codex |
| v1.1.175 | 2026-06-06 | Graph Run 列表、待确认 Review 列表和 Review 详情 handler 移除 legacy main 回调，任务工作流只读上下文、pending Review SQL 摘要仓储、Review 详情投影和任务读权限校验收口到 ai_tasks service | Codex |
| v1.1.174 | 2026-06-06 | AI 任务详情 handler 移除 legacy main 回调，任务工作流只读上下文、任务详情投影、Review/Graph Run/知识沉淀/Mock Issue 聚合和任务读权限校验收口到 ai_tasks service | Codex |
| v1.1.173 | 2026-06-06 | 批量推进需求状态 handler 移除 legacy main 回调，目标状态校验、版本归属保护、状态机 skipped 明细、逐需求审计、批次审计和 repository 保存收口到 requirements service，requirements router 已整体不再回调 legacy main | Codex |
| v1.1.172 | 2026-06-06 | 批量排期需求 handler 移除 legacy main 回调，产品/版本校验、可排期状态校验、skipped 明细、逐需求审计、批次审计和 repository 保存收口到 requirements service | Codex |
| v1.1.171 | 2026-06-06 | 批量分配需求负责人 handler 移除 legacy main 回调，负责人校验、skipped 明细、逐需求审计、批次审计和 repository 保存收口到 requirements service | Codex |
| v1.1.170 | 2026-06-06 | 批量需求生成产品详细设计任务 handler 移除 legacy main 回调，批量校验、skipped 明细、逐任务创建、批次审计和 repository 保存收口到 requirements service | Codex |
| v1.1.169 | 2026-06-06 | 单条需求生成产品详细设计任务 handler 移除 legacy main 回调，产品上下文快照、需求状态推进、AI task 创建、审计事件和同事务 repository 保存收口到 requirements service | Codex |
| v1.1.168 | 2026-06-06 | 需求审批、驳回和关闭 handler 移除 legacy main 回调，状态机校验、活跃任务保护、审计事件和 repository 精细保存收口到 requirements service | Codex |
| v1.1.167 | 2026-06-06 | 需求修改和删除 handler 移除 legacy main 回调，状态保护、产品/版本/模块校验、审计事件、repository 精细保存和删除收口到 requirements service | Codex |
| v1.1.166 | 2026-06-06 | 需求创建 handler 移除 legacy main 回调，写权限、产品/版本/模块校验、审计事件和 repository 精细保存收口到 requirements service | Codex |
| v1.1.165 | 2026-06-06 | 需求详情和需求全链路读 handler 移除 legacy main 回调，任务工作流只读上下文、链路实体聚合和时间线组装收口到 requirements service | Codex |
| v1.1.164 | 2026-06-06 | 研发运营统一列表 handler 移除 legacy main 回调，SQL read model、GitLab/Jenkins/线上日志 fallback 和查询观测收口到 devops_metrics service | Codex |
| v1.1.163 | 2026-06-06 | 用户洞察统一列表 handler 移除 legacy main 回调，SQL read model、使用趋势/反馈/迭代建议 fallback 和查询观测收口到 user_insights service | Codex |
| v1.1.162 | 2026-06-06 | AI 任务列表 handler 移除 legacy main 回调，任务 SQL read model、权限范围、时间过滤、兼容 fallback 和查询观测收口到 ai_tasks service | Codex |
| v1.1.161 | 2026-06-06 | 需求列表 handler 移除 legacy main 回调，SQL read model 分页筛选排序、兼容 fallback 投影和查询观测收口到 requirements service | Codex |
| v1.1.160 | 2026-06-06 | Bug 列表 handler 移除 legacy main 回调，SQL read model 分页筛选排序、兼容 fallback 投影和查询观测收口到 bugs service | Codex |
| v1.1.159 | 2026-06-06 | Bug 创建、批量更新、修改和删除 handler 移除 legacy main 回调，写权限、上下文校验、状态机、审计和 repository 保存收口到 bugs service | Codex |
| v1.1.158 | 2026-06-06 | 知识文档更新、重建索引和删除 handler 移除 legacy main 回调，状态校验、chunk 重建、沉淀解除关联、审计和 repository 保存收口到 knowledge service | Codex |
| v1.1.157 | 2026-06-06 | 知识文档创建 handler 移除 legacy main 回调，标题/内容/角色/产品校验、chunk 索引、模型日志、审计和 repository 保存收口到 knowledge service | Codex |
| v1.1.156 | 2026-06-06 | 知识沉淀采纳/驳回 handler 移除 legacy main 回调，状态校验、文档生成、索引、审计和 repository 保存收口到 knowledge_deposits service | Codex |
| v1.1.155 | 2026-06-06 | 知识搜索 handler 移除 legacy main 回调，repository-first 候选、关键词兜底、向量兼容过滤和响应投影收口到 knowledge_search service | Codex |
| v1.1.154 | 2026-06-06 | 知识沉淀候选列表 handler 移除 legacy main 回调，repository-first 读取和状态过滤收口到 knowledge_deposits service | Codex |
| v1.1.153 | 2026-06-06 | 知识文档列表 handler 移除 legacy main 回调，repository-first 列表查询、权限过滤、排序分页和性能观测收口到 knowledge_documents service | Codex |
| v1.1.152 | 2026-06-06 | 模拟 Issue 写回 router 移除 legacy main 回调，幂等写回、审计和 repository 保存收口到 mock_writeback service | Codex |
| v1.1.151 | 2026-06-06 | 审计事件列表 router 移除 legacy main 回调，筛选、排序、分页和性能观测收口到 audit_events service | Codex |
| v1.1.150 | 2026-06-06 | 代码评审报告读取 router 移除 legacy main 回调，报告关联和任务读权限校验下沉到 code_review_report service | Codex |
| v1.1.149 | 2026-06-06 | Markdown 导出 router 移除 legacy main 回调，任务工作流只读上下文和 Markdown 渲染下沉到 service | Codex |
| v1.1.148 | 2026-06-06 | 需求、任务和 Bug 批量操作结果统一使用 ManagementBatchResultModal 展示批次号、成功数、跳过数和明细 | Codex |
| v1.1.147 | 2026-06-06 | 任务管理批量取消和批量重试完成后展示批次号、成功数、仍失败和 skipped 明细，补齐任务批量操作可解释性 | Codex |
| v1.1.146 | 2026-06-06 | 需求批量排期、分配负责人、推进状态和生成任务完成后展示批次号、成功数和 skipped 明细，提升批量操作可解释性 | Codex |
| v1.1.145 | 2026-06-06 | 需求批量推进状态补充迭代版本归属保护，进入交付链路状态前必须先排期，避免全链路断链 | Codex |
| v1.1.144 | 2026-06-05 | 需求管理新增批量推进状态，按研发流程前进路径逐条校验并记录 requirement.batch_status_advanced 审计 | Codex |
| v1.1.143 | 2026-06-05 | 需求管理新增批量分配负责人，需求台账补充 assignee 字段，批量接口逐条校验需求状态并记录批次级与逐需求审计 | Codex |
| v1.1.142 | 2026-06-05 | 任务管理新增多选批量重试，复用单任务失败重试状态机，支持模型网关和代码评审执行器失败任务批量恢复并记录审计 | Codex |
| v1.1.141 | 2026-06-05 | AI 助手回答新增服务端引用候选与消息 references 持久化，支持从回答跳转到产品、迭代、需求、任务、Review、Bug、代码评审和知识沉淀 | Codex |
| v1.1.140 | 2026-06-05 | 任务管理新增多选批量取消，批量接口逐条校验任务状态并写入批次级与逐任务审计 | Codex |
| v1.1.139 | 2026-06-05 | 需求全链路详情新增按阶段分组的可展开明细区，并为需求、迭代、任务、Review、PR/代码评审、Bug、发布和知识沉淀提供管理页跳转入口 | Codex |
| v1.1.138 | 2026-06-05 | 前端管理主列表统一补齐普通列默认最小宽度和更宽的右侧固定操作列，减少角色、用户洞察、DevOps、任务和 Bug 等宽表页面挤压变形 | Codex |
| v1.1.137 | 2026-06-05 | 发布验证流程固化为 `scripts/release_smoke.sh` 固定入口，默认执行重建容器、生产就绪 API 门禁和真实浏览器页面 smoke | Codex |
| v1.1.136 | 2026-06-05 | 核心管理列表性能观测新增按列表名解析的 P95 目标，响应 `performance` 返回 `p95_target_ms`，慢查询日志同步记录目标值 | Codex |
| v1.1.135 | 2026-06-05 | 研发运营统一列表 SQL read model 从 persistence.py 抽取为独立 DevopsReadRepository，PostgresSnapshotRepository 仅保留统一列表委托入口 | Codex |
| v1.1.134 | 2026-06-05 | 用户洞察统一列表 SQL read model 从 persistence.py 抽取为独立 UserInsightReadRepository，PostgresSnapshotRepository 仅保留统一列表委托入口 | Codex |
| v1.1.133 | 2026-06-05 | Bug 管理 SQL read model 从 persistence.py 抽取为独立 BugReadRepository，PostgresSnapshotRepository 仅保留 Bug 列表 count/list 委托入口 | Codex |
| v1.1.132 | 2026-06-05 | AI 任务 SQL read model 和待 Review 摘要查询从 persistence.py 抽取为独立 TaskReadRepository，PostgresSnapshotRepository 仅保留任务列表与待确认列表委托入口 | Codex |
| v1.1.131 | 2026-06-05 | 需求管理 SQL read model 从 persistence.py 抽取为独立 RequirementReadRepository，PostgresSnapshotRepository 仅保留需求列表 count/list 委托入口 | Codex |
| v1.1.130 | 2026-06-05 | 产品配置 SQL read model 从 persistence.py 抽取为独立 ProductConfigReadRepository，PostgresSnapshotRepository 仅保留委托入口 | Codex |
| v1.1.129 | 2026-06-05 | 采集运行、待归属处理和生命周期上下文 API 从 main.py 迁移为独立 collectors、attribution、lifecycle router，main.py 不再承载业务 @app 路由 | Codex |
| v1.1.128 | 2026-06-05 | Markdown 导出 API 从 main.py 迁移为独立 export router，并保留任务读取权限、完成态校验和 text/markdown 响应契约 | Codex |
| v1.1.127 | 2026-06-05 | 写回结果、代码评审报告和审计事件 API 从 main.py 迁移为独立 writeback、code_review_reports、audit router，并保留 DB-first 写入与列表观测契约 | Codex |
| v1.1.126 | 2026-06-05 | 用户洞察与迭代建议 API 从 main.py 迁移为独立 user_insights router，并保留 SQL/read model 列表和查询观测契约 | Codex |
| v1.1.125 | 2026-06-05 | 研发运营指标 API 从 main.py 迁移为独立 devops_metrics router，并保留 SQL/read model 列表和查询观测契约 | Codex |
| v1.1.124 | 2026-06-05 | 知识中心 API 从 main.py 迁移为独立 knowledge router，并补充单一路由归属约束 | Codex |
| v1.1.123 | 2026-06-05 | AI 任务列表与创建 handler 从 main.py 下沉到 tasks router，进一步收敛任务 API 领域边界 | Codex |
| v1.1.122 | 2026-06-05 | AI 任务与 Review API 入口迁移为独立 tasks router，并补充单一路由归属约束 | Codex |
| v1.1.121 | 2026-06-05 | 需求交付 API 从 main.py 迁移为独立 requirements router，并补充单一路由归属约束 | Codex |
| v1.1.120 | 2026-06-05 | Bug 管理 API 从 main.py 迁移为独立 bugs router，并补充单一路由归属约束 | Codex |
| v1.1.119 | 2026-06-05 | GitLab MR / GitHub PR 预览、列表和快照 API 从 main.py 迁移为独立 git_review router，并补充单一路由归属约束 | Codex |
| v1.1.118 | 2026-06-05 | 业务大脑只读 API 从 main.py 迁移为独立 brain_apps router，repository-first 读取逻辑收口到 brain_apps service | Codex |
| v1.1.117 | 2026-06-05 | 模型网关配置与日志 API 从 main.py 迁移为独立 model_gateway router，配置校验、连接测试和运行时 URL/Embedding helper 收口到 model_gateway service | Codex |
| v1.1.116 | 2026-06-05 | 相关系统 API 从 main.py 迁移为独立 related_systems router，产品配置域 router 拆分完成 | Codex |
| v1.1.115 | 2026-06-05 | 产品 Git 仓库 API 从 main.py 迁移为独立 product_git_repositories router，并保留 provider 校验与凭据脱敏契约 | Codex |
| v1.1.114 | 2026-06-05 | 产品模块 API 从 main.py 迁移为独立 product_modules router，并复用产品配置共享上下文 service | Codex |
| v1.1.113 | 2026-06-05 | 迭代版本 API 从 main.py 迁移为独立 product_versions router，并抽取产品配置共享上下文 service | Codex |
| v1.1.112 | 2026-06-05 | 产品主体 CRUD API 从 main.py 迁移为独立 products router 并补充路由边界约束 | Codex |
| v1.1.111 | 2026-06-05 | 用户管理 API 从 main.py 迁移为独立 users router 并补充路由边界约束 | Codex |
| v1.1.110 | 2026-06-05 | 平台健康检查与长期记忆状态 API 从 main.py 迁移为独立 platform router 和 platform status service | Codex |
| v1.1.109 | 2026-06-05 | 认证与角色目录 API 从 main.py 迁移为独立 auth router 并补充路由边界约束 | Codex |
| v1.1.108 | 2026-06-05 | 首页 IT 团队看板 API 从 main.py 迁移为独立 dashboard router 并补充路由边界约束 | Codex |
| v1.1.107 | 2026-06-05 | AI 助手 API 从 main.py 迁移为独立 assistant router | Codex |
| v1.1.106 | 2026-06-05 | API 通用错误封装、当前用户依赖、store 获取和角色校验拆分为共享 deps 模块 | Codex |
| v1.1.105 | 2026-06-05 | AI 助手聊天工作流、会话读写和错误边界拆分为独立 assistant chat service | Codex |
| v1.1.104 | 2026-06-05 | AI 助手系统上下文与消息投影拆分为独立 assistant context service | Codex |
| v1.1.103 | 2026-06-05 | 首页 IT 团队看板指标聚合拆分为独立 service，Web shell 与登录页品牌统一为 Enterprise AI Brain | Codex |
| v1.1.102 | 2026-06-05 | 首页 IT 团队看板补充短 TTL 缓存、强制刷新、缓存元数据和慢查询日志设计 | Codex |
| v1.1.101 | 2026-06-05 | 发布就绪门禁新增浏览器页面 smoke 脚本，管理主列表查询观测补齐列表名和慢查询日志 | Codex |
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
| v1.1.16 | 2026-05-31 | 推进模型网关配置和调用元数据日志细粒度 PostgreSQL 持久化 | Codex |
| v1.1.17 | 2026-05-31 | 系统管理新增只读角色管理入口，明确 MVP 六类角色定义、职责、范围和不可自由创建角色约束 | Codex |
| v1.1.18 | 2026-05-31 | 推进 GitLab MR 快照和 Code Review 报告细粒度 PostgreSQL 持久化 | Codex |
| v1.1.19 | 2026-05-31 | 推进模拟 Issue 回写细粒度 PostgreSQL 持久化，写入 `mock_issues` 并支持恢复幂等结果 | Codex |
| v1.1.20 | 2026-05-31 | 推进相关系统细粒度 PostgreSQL 持久化，纳入产品配置结构表恢复范围 | Codex |
| v1.1.21 | 2026-05-31 | 移除 AI 任务启动本地输出 fallback，缺少模型网关时任务明确失败 | Codex |
| v1.1.22 | 2026-05-31 | 将知识检索升级为 chunk 级权限过滤结果，并持久化 `knowledge_chunks` | Codex |
| v1.1.23 | 2026-05-31 | 补齐生命周期视图和首页看板任务聚合的任务读权限过滤 | Codex |
| v1.1.24 | 2026-05-31 | 明确角色业务映射、可见入口和限制边界，并补齐知识索引失败原因与重试契约 | Codex |
| v1.1.25 | 2026-06-01 | 补齐生命周期上下文从审计主体和 MVP 证据主体精准解析到任务链路的实现约束 | Codex |
| v1.1.26 | 2026-06-01 | 明确低层 AI 任务创建必须回写需求任务引用并遵守需求关闭状态边界 | Codex |
| v1.1.27 | 2026-06-01 | 收敛模型网关 provider 配置边界，非 OpenAI-compatible provider 在配置入口拒绝 | Codex |
| v1.1.28 | 2026-06-01 | 增加可重复执行的 pgvector HNSW 索引迁移，补齐知识 chunk 向量检索索引基础设施 | Codex |
| v1.1.29 | 2026-06-01 | 知识索引接入 OpenAI-compatible embeddings，检索按权限过滤后的 chunk embedding 做向量排序 | Codex |
| v1.1.30 | 2026-06-01 | 将用户反馈升级为真实业务主体，支持登记、筛选、状态处理、审计和 `user_feedback` PostgreSQL 持久化 | Codex |
| v1.1.31 | 2026-06-01 | 将迭代规划建议升级为基于真实反馈/Bug 证据生成、确认、可选转需求和 PostgreSQL 持久化 | Codex |
| v1.1.32 | 2026-06-01 | 将用户使用指标升级为真实业务主体，支持登记、筛选、审计和 `user_usage_metrics` PostgreSQL 持久化 | Codex |
| v1.1.33 | 2026-06-01 | 将 GitLab 每日代码指标升级为真实业务主体，支持登记、筛选、审计和 `gitlab_daily_code_metrics` PostgreSQL 持久化 | Codex |
| v1.1.34 | 2026-06-01 | 将 Jenkins 发布记录升级为真实业务主体，支持登记、筛选、审计和 `jenkins_release_records` PostgreSQL 持久化 | Codex |
| v1.1.35 | 2026-06-01 | 将线上运行日志指标升级为真实业务主体，支持登记、筛选、审计和 `online_log_metrics` PostgreSQL 持久化 | Codex |
| v1.1.36 | 2026-06-01 | 补齐 development_planning 和 automated_testing 基础闭环，自动化测试确认后生成 AI 自动测试 Bug 记录 | Codex |
| v1.1.37 | 2026-06-01 | 补齐 release_readiness 和 post_release_analysis 基础闭环，发布评估保存真实发布/日志/缺陷上下文，上线后分析确认后生成 AI 上线后 Bug 记录 | Codex |
| v1.1.38 | 2026-06-01 | 首页 IT 团队看板按产品过滤知识文档和审计事件，知识文档支持产品归属上下文 | Codex |
| v1.1.39 | 2026-06-02 | 生命周期上下文接入 v1.2 真实证据主体，动态标识缺失上下文并归集跨阶段风险信号 | Codex |
| v1.1.40 | 2026-06-02 | 新增采集运行记录结构表、API、审计和研发运营页面入口，作为外部采集器接入前的真实运行台账 | Codex |
| v1.1.41 | 2026-06-02 | 新增待归属数据队列结构表、API、审计和 DevOps 处理入口 | Codex |
| v1.1.42 | 2026-06-02 | 模型网关配置新增测试检测能力，临时调用 OpenAI-compatible Chat 与 Embedding 接口并返回脱敏状态，不保存密钥或模型日志 | Codex |
| v1.1.43 | 2026-06-02 | 模型网关测试检测支持 `test_target=chat`，允许 ChatGPT OAuth 类上游仅验证 Chat 能力并将 Embedding 标记为跳过 | Codex |
| v1.1.44 | 2026-06-02 | 任务管理列表支持按所属产品和创建时间段筛选，AI 任务摘要返回产品名与时间字段 | Codex |
| v1.1.45 | 2026-06-02 | 所有 PostgreSQL 结构表统一补齐 `created_at` 和 `updated_at` 标准时间字段，并新增迁移门禁测试 | Codex |
| v1.1.46 | 2026-06-02 | 产品 Git 资源扩展 GitHub provider，支持 GitHub PR 预览、diff 快照和凭据解析 | Codex |
| v1.1.47 | 2026-06-02 | 新增 AI 助手聊天工作台和 `/api/assistant/chat`，基于系统上下文回答 AI Brain 配置与开发进展问题 | Codex |
| v1.1.48 | 2026-06-03 | 基于 AI 助手真实需求复跑补齐 GitHub PR 列表、产品详情、模型网关健康检查和失败任务重试能力 | Codex |
| v1.1.49 | 2026-06-03 | 基于 AI Brain GitHub PR 复跑补齐 code-review 外部命令缺失时复用模型网关的执行器策略，并强化模型网关 Review payload 与输出规范化 | Codex |
| v1.1.50 | 2026-06-03 | AI 助手聊天记录按用户级持久化，补齐会话列表、消息查询和结构表恢复契约 | Codex |
| v1.1.51 | 2026-06-03 | 知识索引新增文本兜底状态 `text_indexed` 和向量增强状态 `vector_indexed`，Embedding 不可用时仍支持关键词检索 | Codex |
| v1.1.52 | 2026-06-03 | 模型网关拆分 Chat 与 Embedding 能力，Embedding 可禁用、复用 Chat 或单独配置，检索按向量元数据判断兼容性 | Codex |
| v1.1.53 | 2026-06-03 | 需求新增支持不指定迭代版本，需求交付新增迭代版本管理入口，并将需求状态机扩展为需求池、排期、设计、开发、评审、测试、发布和验收流程 | Codex |
| v1.1.54 | 2026-06-03 | DB-first 迁移补齐任务运行态/Review/回写/导出 repository 读路径和 Mock Writeback handler 级写入约束 | Codex |
| v1.1.55 | 2026-06-03 | DB-first 迁移补齐知识沉淀候选列表 repository-first 读取和状态过滤约束 | Codex |
| v1.1.56 | 2026-06-03 | DB-first 迁移补齐知识检索 repository-first 候选查询、权限过滤和关键词下推约束 | Codex |
| v1.1.57 | 2026-06-03 | DB-first 迁移补齐知识沉淀审核写接口 repository 当前记录读取约束 | Codex |
| v1.1.58 | 2026-06-03 | DB-first 迁移补齐生命周期上下文 repository source rows 聚合和过渡读侧容器边界 | Codex |
| v1.1.59 | 2026-06-03 | DB-first 迁移补齐首页 IT 团队看板 repository source rows 聚合和单条 snapshot 写入边界 | Codex |
| v1.1.60 | 2026-06-03 | DB-first 迁移补齐任务/Review/导出 task workflow source rows 读取边界，减少 repository read snapshot 依赖 | Codex |
| v1.1.61 | 2026-06-03 | DB-first 迁移补齐任务启动、取消、补充信息和 Review 决策写路径的请求级 source rows 上下文边界 | Codex |
| v1.1.62 | 2026-06-03 | DB-first 迁移将 PostgreSQL 启动运行层切换为轻量 PostgresRuntimeStore repository 容器 | Codex |
| v1.1.63 | 2026-06-03 | DB-first 迁移补齐产品配置、需求/任务创建和 Bug 写路径在 PostgresRuntimeStore 空启动容器下的 source rows 上下文边界 | Codex |
| v1.1.64 | 2026-06-03 | DB-first 迁移补齐运营采集、用户洞察和迭代规划写路径在 PostgresRuntimeStore 空启动容器下的 source rows 上下文边界 | Codex |
| v1.1.65 | 2026-06-03 | DB-first 迁移补齐模型网关配置和 AI 助手聊天写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文边界 | Codex |
| v1.1.66 | 2026-06-03 | DB-first 迁移补齐知识文档和知识沉淀写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文边界 | Codex |
| v1.1.67 | 2026-06-03 | DB-first 迁移补齐 GitLab/GitHub PR/MR 预览、列表和快照写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文边界 | Codex |
| v1.1.68 | 2026-06-03 | DB-first 迁移移除生产 read snapshot 恢复 fallback，补齐业务大脑只读、知识沉淀驳回和 Mock Writeback 生成的 repository/source rows 边界 | Codex |
| v1.1.69 | 2026-06-03 | DB-first 迁移将生命周期上下文 source rows 从 MemoryStore 投影替换为专用 LifecycleContextReadModel | Codex |
| v1.1.70 | 2026-06-03 | DB-first 迁移明确只读缓存允许边界，并将产品配置、模型网关、助手、需求、任务创建和 Bug 写路径进一步收敛为直接 repository records/payloads | Codex |
| v1.1.71 | 2026-06-04 | 增加前端和用户可见流程提交前的真实网页界面验证门禁 | Codex |
| v1.1.72 | 2026-06-04 | 新增需求批量排期接口、需求管理批量排期入口和迭代版本页归集需求入口，并补齐审计规则 | Codex |
| v1.1.73 | 2026-06-04 | 真实网页验收发现 planning 迭代版本无法从需求页选择，修正为需求页读取未归档版本并以追加方式保存批次审计 | Codex |
| v1.1.74 | 2026-06-04 | 新增迭代版本状态推进能力，支持规划中、开发中、测试中、已发布主状态和需求状态同步预览/审计 | Codex |
| v1.1.75 | 2026-06-04 | 需求管理页新增迭代版本查询条件，基于需求列表版本投影过滤需求范围 | Codex |
| v1.1.76 | 2026-06-04 | Bug 管理列表新增迭代版本展示和查询条件，Bug 列表返回版本投影并支持版本过滤 | Codex |
| v1.1.77 | 2026-06-04 | 调整迭代版本开发中推进测试中规则，版本内已进入交付链路的需求统一同步到测试中 | Codex |
| v1.1.78 | 2026-06-04 | Bug 登记目标版本选择改为同产品未归档迭代版本，支持测试中和已发布版本缺陷归属 | Codex |
| v1.1.79 | 2026-06-04 | 用户洞察页面移除无操作的待归属使用/反馈只读区，待归属队列统一收口到研发运营处理入口 | Codex |
| v1.1.80 | 2026-06-04 | 前端日期/时间登记字段统一使用 Ant Design DatePicker，并保持 API 日期字符串契约 | Codex |
| v1.1.81 | 2026-06-04 | Bug 管理列表新增创建时间展示，便于按登记先后追踪缺陷 | Codex |
| v1.1.82 | 2026-06-04 | 需求管理列表时间列从更新时间调整为创建时间，便于按提交先后查看需求 | Codex |
| v1.1.83 | 2026-06-04 | 用户洞察列表固定列宽、操作列右侧固定并新增详情弹窗，避免长反馈内容撑开页面 | Codex |
| v1.1.84 | 2026-06-04 | 用户洞察和研发运营主列表改为统一服务端聚合接口分页、排序和筛选 | Codex |
| v1.1.85 | 2026-06-04 | 新增需求全链路详情读模型和需求管理页入口，按需求聚合研发全流程时间线 | Codex |
| v1.1.86 | 2026-06-04 | Bug 管理新增多选批量处理，支持批量更新状态、严重级别或处理人并写入批次审计 | Codex |
| v1.1.87 | 2026-06-05 | AI 助手上下文增强为可回答迭代进度、阻塞需求、待确认 Review、代码评审结论和 Bug 分布 | Codex |
| v1.1.88 | 2026-06-05 | GitLab MR / GitHub PR 预览增强为 Review 准备视图，提供 diff 文件树、风险摘要和 Review Checklist | Codex |
| v1.1.89 | 2026-06-05 | 需求全链路详情页展示 PR/MR 证据，包括快照风险摘要、diff 文件树和 Review Checklist | Codex |
| v1.1.90 | 2026-06-05 | 角色管理列表改为摘要化展示，职责、数据范围、限制边界和权限明细收口到详情弹窗 | Codex |
| v1.1.91 | 2026-06-05 | 需求管理新增批量生成任务入口和接口，同产品已排期需求可批量生成产品详细设计任务并记录批次审计 | Codex |
| v1.1.92 | 2026-06-05 | 需求全链路详情页新增阶段进度视图，按需求、迭代、任务、Review、PR/代码评审、Bug、发布和知识沉淀展示链路覆盖状态 | Codex |
| v1.1.93 | 2026-06-05 | 需求全链路新增可直达详情页路由，列表保留弹窗快查并提供详情页入口，便于刷新、分享和跨模块跳转 | Codex |
| v1.1.94 | 2026-06-05 | 用户洞察统一列表沉淀为 PostgreSQL SQL read model，并补充排序过滤索引 | Codex |
| v1.1.95 | 2026-06-05 | 需求全链路详情弹窗摘要和阶段进度改为响应式布局，阶段与时间线状态展示中文业务状态，避免长标题或版本名撑宽裁切 | Codex |
| v1.1.96 | 2026-06-05 | 研发运营统一列表沉淀为 PostgreSQL SQL read model，并补充排序过滤索引 | Codex |
| v1.1.97 | 2026-06-05 | 明确团队看板可基于 PostgreSQL source rows 进行 Python 聚合，管理列表必须优先 SQL/read model 分页排序筛选 | Codex |
| v1.1.99 | 2026-06-05 | 需求管理和 Bug 管理列表在 PostgreSQL 运行时切换为 SQL read model，筛选、排序和分页在数据库层完成 | Codex |
| v1.1.100 | 2026-06-05 | 产品管理和迭代版本列表在 PostgreSQL 运行时切换为 SQL read model，筛选、排序和分页在数据库层完成 | Codex |

---

## 概述

企业 AI 大脑平台 v1 系列采用基于 Ant Design Pro 模板的 React + TypeScript 前端、FastAPI 后端、LangGraph 工作流、PostgreSQL + pgvector 知识存储、Redis 缓存/队列、GBrain 长期记忆层和 OpenAI-compatible 模型网关，先以模块化单体跑通产品研发大脑从需求审批到产品详细设计、技术方案、GitLab MR / GitHub PR 代码 Review、人工确认、内部报告归档和知识沉淀的 MVP 闭环，并通过研发上下文图谱感知需求、设计、代码、测试、发布、线上反馈、用户使用和用户反馈之间的关联与风险。AI 助手工作台已接入模型网关 Chat 能力，聊天前由后端按用户问题生成 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等确定性 read-model 工具结果，模型优先依据 `system_context.tool_results` 回答 AI Brain 产品配置、需求/任务进展、迭代、Git 仓库、代码评审和模型网关状态问题；助手服务同时生成产品、迭代、需求、任务、Review、Bug、代码评审和知识沉淀引用候选，回答消息持久化 `references` 与 `tool_results` 并在前端展示可跳转来源链接。GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属数据队列、基于反馈/Bug 的迭代规划建议、开发计划、自动化测试、发布上线评估、上线后分析基础闭环和生命周期 v1.2 真实证据扩展已进入当前实现；外部自动采集器和真实外部系统双向写回按后续阶段确认后推进。后续定时采集、AI 日志分析、AI 迭代建议和看板刷新统一通过 `scheduled_jobs` 调度定义、`scheduled_job_runs` 运行实例、`collector_runs` 采集台账和 `ai_agents` / `ai_skills` 能力装配完成，每次运行必须保存解析后的 Agent、Skill、模型网关、Prompt、输出 Schema、工具策略和上下文范围快照。

## 设计决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| 系统形态 | 模块化单体 | v1 需要快速闭环和低运维复杂度，保留未来拆分服务边界。 |
| AI 编排 | LangGraph | 支持状态化 Graph、检查点、人机中断和恢复。 |
| 知识检索 | PostgreSQL + pgvector + GBrain | v1 业务知识库使用 PostgreSQL + pgvector；长期记忆和公司大脑能力引入 GBrain 的混合检索、答案合成和知识图谱。 |
| 模型接入 | 模型网关 + OpenAI-compatible API | 业务模块不直接依赖供应商 SDK，便于治理、审计和替换模型。 |
| 回写集成 | 模拟 Issue 优先 | v1 演示闭环，不引入真实外部系统副作用。 |
| 部署方式 | Docker Compose | 满足本地演示和早期部署，避免过早引入 Kubernetes。 |
| 业务主体 | 产品、需求、AI 任务、Bug、知识中心、研发运营指标和用户洞察（含迭代规划建议）作为一等主体或独立运营视图 | 避免任务详情页包办主数据、审批、执行、缺陷、知识治理和产品迭代决策，保证长期可维护。 |
| AI 任务类型 | 研发全链路 task_type | v1 MVP 覆盖产品详细设计、技术方案和 GitLab MR / GitHub PR 代码 Review；后续扩展代码开发辅助、自动化测试、发布上线评估和上线后分析，统一使用状态机、人工确认、审计和回写机制。 |
| Git Code Review 输入 | GitLab MR 或 GitHub PR 元信息、diff 文件树、风险摘要、Review Checklist、diff 快照、可插拔 code-review 执行器、结构化报告和内部归档 | GitLab/GitHub 只读 API + Claude Code `code-review` skill 适配器 |
| 需求任务关系 | 引用 + 快照 | 需求保存业务事实和审批状态，任务保存生成时的需求快照和产品上下文，避免历史任务被后续主数据变更影响。 |
| 研发运营数据 | 产品归属聚合 | GitLab、Jenkins、线上运行日志、Bug、用户使用、用户反馈和首页看板均按产品/版本/模块归属汇总，支撑 IT 团队运营分析和产品迭代规划。 |
| 用户洞察与迭代规划 | AI 建议 + 人工确认 | AI 可以基于产品规划、需求池、使用数据、反馈、Bug、线上日志、发布记录和研发投入生成优先级建议；用户反馈也可经产品负责人、研发负责人或管理员直接转为正式需求，需求来源和反馈关联必须留痕。 |
| 全流程感知 | 研发上下文图谱 | 将需求、产品详细设计、技术方案、代码提交、代码 Review、自动化测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件以产品/版本/模块/需求/任务为主线串联，支持跨阶段追溯和风险感知。 |

## 实施切片

v1 MVP 技术交付按 MVP-A/B/C 切片推进，三个切片全部通过后才视为 v1 MVP 完整完成：

| 切片 | 技术重点 | 涉及模块 | 主要验证 |
|------|----------|----------|----------|
| MVP-A 基础 + Git 输入闭环 | 基础工程、认证、产品配置、GitLab/GitHub 只读接入、MR/PR 预览、diff 快照、需求审批、产品详细设计、技术方案、人工确认、Markdown 导出和基础审计 | auth, product_config, git_review, requirement, ai_task, graph_runtime, review, model_gateway, audit, export | 跑通需求到确认方案的闭环，并能在技术方案后基于授权 MR/PR 生成不可变输入快照 |
| MVP-B Git Review 闭环 | code_review 任务、执行器调用、结构化报告、人工确认、内部归档、diff 超限和执行器失败处理 | code_review_executor, ai_task, graph_runtime, review, audit, git_review | 基于 MVP-A 生成的不可变 MR/PR 快照生成可审计 Review 报告，且不产生远端写副作用 |
| MVP-C 知识与治理闭环 | 知识导入、索引状态、权限过滤检索、知识沉淀候选审核、模拟 Issue 幂等生成、主体级审计和真实空数据入口 | knowledge, long_memory, integration, audit, dashboard | 任务产出可沉淀、检索有权限过滤；未接入采集器的接口返回空集合，不提供伪造统计数据 |

MVP-A 可以在自动化测试中使用受控模型夹具，但运行时必须配置 OpenAI-compatible 模型网关或环境模型网关，不得生成本地 fallback 输出；同时必须具备 GitLab/GitHub 只读集成依赖，至少支持授权仓库绑定、MR/PR 预览和不可变 diff 快照。MVP-B 在此基础上引入 code-review 执行器、正式报告生成、人工确认和内部归档。MVP-B 必须补齐执行器失败、diff 过大和不回写 GitLab/GitHub 的错误语义；MVP-C 补齐知识治理后，MVP 才能对外宣称具备完整闭环。

当前源码实现状态：Docker 本地栈默认以 `PERSISTENCE_MODE=postgres` 启动，登录账号读取 PostgreSQL `users` 表，管理员可通过系统管理下的用户管理维护用户，通过角色管理只读查看系统角色定义，并可在模型网关配置页维护和测试 OpenAI-compatible 配置；用户角色已收敛为 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 六个 MVP 可分配角色，后端通过 `/api/auth/roles` 暴露角色目录，并返回业务角色映射、职责、数据范围、决策范围、可见入口、限制边界、权限点、是否可分配和排序信息；角色管理列表只展示角色、业务角色、职责与范围摘要、可见入口、权限数量和状态，完整定位、职责、数据范围、决策范围、限制边界和权限点通过详情弹窗查看，用户管理和知识权限选择必须从同一接口加载固定目录，不能自由创建或录入未定义角色。

产品配置、需求台账、AI 任务、人工确认、Graph 运行态、GitLab MR / GitHub PR 兼容快照、Code Review 报告、知识文档、知识 chunk、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属数据队列、迭代规划建议/确认、模拟 Issue 回写、模型网关配置、模型调用元数据、AI 助手会话和助手消息已开始细粒度持久化：产品、版本、模块、Git 资源、相关系统、需求、AI 任务核心字段、Review、Graph Run、Checkpoint、GitLab MR / GitHub PR 兼容快照、Code Review 报告、知识文档、知识 chunk、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属队列项、迭代规划建议、迭代规划确认、模拟 Issue 回写、模型网关配置、模型调用元数据、助手会话和助手消息会同步写入 `products`、`product_versions`、`product_modules`、`product_git_repositories`、`related_systems`、`requirements`、`ai_tasks`、`human_reviews`、`graph_runs`、`graph_checkpoints`、`gitlab_mr_snapshots`、`code_review_reports`、`knowledge_documents`、`knowledge_chunks`、`knowledge_deposits`、`audit_events`、`bugs`、`gitlab_daily_code_metrics`、`jenkins_release_records`、`online_log_metrics`、`user_feedback`、`user_usage_metrics`、`collector_runs`、`pending_attribution_items`、`iteration_plan_suggestions`、`iteration_plan_decisions`、`mock_issues`、`model_gateway_configs`、`model_gateway_logs`、`assistant_conversations`、`assistant_messages`。`app_state_snapshots` 仅作为历史迁移表保留，不再作为生产业务状态恢复源或请求结束写入目标。`PERSISTENCE_MODE` 默认值为 `postgres`；除 `APP_ENV=test/testing/pytest` 外，后端启动时配置 `PERSISTENCE_MODE=memory` 必须 fail fast，纯 `MemoryStore` 仅作为测试 helper；PostgreSQL 运行时 `build_store()` 返回轻量 `PostgresRuntimeStore(repository)`，不再通过 `PersistentMemoryStore.from_repository(repository)` 启动恢复业务集合。PostgreSQL source rows 使用非 `MemoryStore` 的 repository request context；只读缓存/read model 可作为性能优化保留，但必须由 PostgreSQL 派生、可重建，且不得作为写接口事实源。所有 PostgreSQL 结构表必须包含 `created_at timestamptz NOT NULL DEFAULT now()` 和 `updated_at timestamptz NOT NULL DEFAULT now()` 标准字段；业务写入或结构仓储 upsert 应保留新增时间并在发生修改时维护修改时间，迁移测试会阻止缺少任一字段的新表进入代码库。AI 任务启动路径已由真实 LangGraph `StateGraph` 编译和执行，当前 MVP 节点路径为 `retrieve_context -> generate_task_output -> interrupt_for_human_review`，运行记录会保存 `runtime`、`node_path` 和 checkpoint 内的 `graph_runtime` 元数据。

DB-first 迁移状态：上述结构化持久化不代表所有 API 已经直连数据库。当前生产目标是继续删除所有把 `current_store.<collection>` 当作数据源或写入目标的剩余路径，改为所有读接口走 SQL/repository/read model、所有写接口在 handler/service 内事务化直写 PostgreSQL 并同步审计。`/health` 必须返回 `data_access_mode`，当前迁移期取值为 `db_first_migration`；当 `PERSISTENCE_MODE=memory` 且处于测试环境时取值为 `memory_test_helper`。PostgreSQL 启动运行层已从 `PersistentMemoryStore.from_repository(repository)` 切换为 `PostgresRuntimeStore(repository)`，不再启动恢复业务集合；请求结束全局 `persist()` 已从 API middleware 移除，任何 API 请求都不再通过请求结束同步进程内 store。API 通用依赖位于 `app.api.deps`，集中提供 `api_error`、`store`、`CurrentUser/get_current_user` 和 `require_roles`，后续独立 router 必须使用该共享依赖，不得反向 import `main.py` 获取认证或错误封装。产品配置写接口已开始按 handler 级别调用 repository 单记录写入/删除方法，覆盖产品、迭代版本、模块、Git 资源和相关系统，并通过禁用请求结束 `persist()` 的重建测试验证写入不依赖全局同步；产品配置核心 GET 接口已在 repository 可用时优先读取 SQL/repository，包括产品列表/详情、指定产品的版本、模块、Git 资源和关联系统，并通过运行态 store 过期测试验证不依赖进程内集合。需求台账的纯需求写接口已用同样方式覆盖创建、修改、审批、驳回、关闭和删除，并把对应审计事件随单条需求记录写入；从需求生成产品详细设计 AI 任务已通过 repository 在同一事务中写入需求 `task_ids`/状态、AI 任务记录和 `ai_task.created` 审计事件。后续任务创建也已在同一事务中写入需求 `task_ids`/状态、AI 任务记录和 `ai_task.created` 审计事件；需求列表、需求详情、AI 任务详情、Graph Run 列表、待确认 Review、Review 详情、模拟回写结果、Code Review 报告和 Markdown 导出在 PostgreSQL 运行时会优先读取 task workflow repository source rows，运行态 store 过期时仍能返回结构表详情、任务运行态、确认态、回写结果和导出内容。任务启动成功路径已写入 AI task、模型调用日志、Human Review、Graph Run、Checkpoint 和启动审计事件；任务启动失败路径已写入 failed task、可选模型失败日志、`ai_task.retry_started` 和失败审计事件；Review approve/edit-approve/reject/request-more-info 主路径已写入完成态或中断态 task、review、graph/checkpoint、需求状态、知识沉淀候选、可选 Bug/Code Review 报告和审计事件；cancel/submit-more-info 已写入 AI task、待确认 Review、Graph Run/Checkpoint 和审计事件；Mock Writeback 生成接口已在 handler 返回前写入 `mock_issues` 和 `mock_issue.written` 审计事件。知识文档创建/更新/索引重试/删除、知识 chunk 重建、知识沉淀采纳/拒绝和对应审计事件已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 knowledge source rows 恢复产品、知识文档、chunk、沉淀和模型网关上下文，同步索引期间可选模型日志；知识文档列表、知识沉淀候选列表和知识检索候选 chunk 已在 repository 可用时优先读取 SQL/repository，权限角色、关键字、文档类型、索引状态、沉淀状态和 chunk 权限等过滤在查询层执行，chunk_count 由结构表聚合返回；知识检索保留现有关键词兜底和兼容向量排序，但候选集不再来自进程内知识集合；知识沉淀 approve/reject 写接口优先从 repository 读取当前沉淀记录，运行态 store 过期时仍能写回沉淀、文档、chunk、模型日志和审计事件。AI 助手聊天成功路径已在 handler 返回前写入会话、用户消息、助手消息、模型日志和审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 assistant source rows 恢复当前用户会话、消息、产品任务摘要和模型网关上下文；模型调用失败路径写入失败模型日志和审计事件；助手会话列表和消息列表已在 repository 可用时优先读取 SQL/repository，并按当前 `user_id` 在查询层隔离历史记录。GitHub PR 列表、GitLab MR / GitHub PR 预览审计以及快照成功、复用和失败审计已在 handler 返回前写入 repository；Code Review 报告生成/确认已随任务启动和 Review 决策事务写入。Bug 创建、修改和删除已在 handler 返回前写入 `bugs` 与对应审计事件，删除前会清空指向该 Bug 的重复归并引用；Bug 列表已在 repository 可用时优先读取 SQL/repository，产品、状态、严重级别和来源过滤在查询层执行。采集运行创建/更新、待归属队列创建/处理、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标创建已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品、仓库、版本、模块、采集运行和待归属当前记录；采集运行、待归属队列、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标列表已在 repository 可用时优先读取 SQL/repository，采集类型、来源系统、产品、仓库、版本、状态、环境、日期和时间范围等过滤在查询层执行。用户使用指标创建、用户反馈创建/处理、迭代建议生成和迭代建议决策已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 insight source rows 校验产品、版本、模块、反馈、Bug 和迭代建议当前记录；用户使用指标、用户反馈和迭代建议列表已在 repository 可用时优先读取 SQL/repository，产品、模块、功能、用户群体、时间范围、状态、创建人和规划周期等过滤在查询层执行；迭代建议转需求时会在同一 repository 调用内写入新需求、建议、决策和完整审计事件。模型网关配置创建、修改、删除和连接测试审计已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 model gateway source rows 恢复当前配置和调用日志上下文；模型网关配置列表和模型调用日志列表已在 repository 可用时优先读取 SQL/repository，并通过运行态 store 过期测试验证配置列表、密钥脱敏状态和日志筛选不依赖进程内集合。审计列表已在 repository 可用时优先读取 SQL/repository，actor、event_type、ai_task、subject 和时间范围过滤在查询层执行。生命周期上下文查询生成的 edges/risks 和首页看板生成的 dashboard snapshot 已在 handler 返回前写入 repository；在 PostgreSQL 运行时，首页看板和生命周期上下文聚合前都会直接读取 repository source rows，不再依赖 repository read snapshot 聚合；首页看板通过 `save_dashboard_metric_snapshot_record` 单条写入当前产品/时间窗口快照，生命周期上下文通过 `save_lifecycle_context` 写回生成的 edges/risks。管理列表类型接口必须优先在 SQL/repository/read model 层完成分页、排序和筛选；返回分页响应时必须附带 `query.name`、生效筛选、分页、排序和 `performance.duration_ms/result_count/total/slow`，当接口耗时超过阈值时记录 `slow_list_query` 日志，后续 P95 目标和页面慢问题以这些元数据、trace_id 与数据库慢查询日志联合定位；首页团队看板、生命周期上下文等汇总视图可以基于 PostgreSQL source rows 在 Python 中聚合，只要读取来源可重建、权限过滤和产品/时间窗口过滤清晰，且不得把聚合容器作为写入事实源。首页团队看板允许使用由 PostgreSQL source rows 派生的短 TTL 只读缓存，缓存 key 必须包含 repository 身份、产品、时间窗口和用户角色集合，响应必须回显 `metadata.dashboard_cache`，`refresh=true` 必须强制重建；当看板接口耗时超过阈值时记录 `slow_dashboard_query`，用于和列表 `slow_list_query` 一起定位慢页面。后续 DB-first 切片继续迁移尚未结构化仓储化的业务域。新增生产接口不得把 `current_store.<collection>` 作为数据源或写入目标；如必须临时保留，应在迁移计划中标注模块、风险和退出条件。

`main.py` 只允许保留 FastAPI app 创建、运行时 store/user repository 构建、middleware、异常处理、CORS 与 router 注册，不得再新增业务 helper、repository source-store 组装或结构表保存委托。任务工作流 source rows 的只读/写入上下文由 `app.services.task_workflow_context` 维护；PostgreSQL repository-backed source context 必须是非 `MemoryStore` 对象，仅暴露业务服务需要的集合、`new_id`、`snapshot` 和 `audit` 能力，避免 DB-first 运行时再次退回进程内 MemoryStore 兼容层。持久化层的集合字段常量、`SnapshotRepository` 和各领域仓储 Protocol 由 `app.core.persistence_contracts` 统一维护；snapshot payload/load/save、集合合并、上下文清理、counter 同步和恢复链路 helper 由 `app.core.persistence_payloads` 维护；测试兼容层 `PersistentMemoryStore` 由 `app.core.persistent_memory_store` 维护，只允许用于测试或历史恢复验证；生产 PostgreSQL 运行时容器 `PostgresRuntimeStore` 由 `app.core.persistence_runtime` 维护，`main.py` 必须直接从该 runtime 模块装配；`app.core.persistence` 只能继续承载兼容 re-export 和 PostgreSQL snapshot repository 实现，后续拆分不得把协议定义、snapshot helper、测试兼容 store 或生产 runtime 实现重新堆回 snapshot repository 文件。

认证与角色目录 API 已收口到独立 `app.api.routers.auth`：`/api/auth/login`、`/api/auth/me`、`/api/auth/logout` 和 `/api/auth/roles` 仍保持原有 URL、鉴权依赖、trace envelope 和角色目录返回契约；router 只依赖 `app.api.deps`、用户仓储、角色目录与安全工具，不得反向 import `main.py`。路由边界测试必须保证这些 auth 端点只有单一 router 归属，避免后续拆分时出现重复注册或回退到 `main.py`。

用户管理 API 已收口到独立 `app.api.routers.users`：`GET/POST /api/users` 和 `PATCH/DELETE /api/users/{user_id}` 仍保持原有管理员权限、用户仓储、角色目录校验、状态校验、错误码和 trace envelope 契约；用户新增/修改时角色必须来自 MVP 可分配角色目录，不能自由录入未定义角色。路由边界测试必须保证用户管理端点只有单一 router 归属，避免系统管理 CRUD 回退到 `main.py`。

产品主体 CRUD API 已收口到独立 `app.api.routers.products`：`GET/POST /api/products` 和 `GET/PATCH/DELETE /api/products/{product_id}` 仍保持原有产品负责人权限、产品编码唯一性、SQL read model 分页筛选排序、`query/performance` 观测元数据、repository-first 读取、handler 级 repository 写入、删除前业务依赖校验和无业务依赖时级联清理版本/模块/Git 资源/相关系统配置的契约。迭代版本 API 已收口到独立 `app.api.routers.product_versions`：`GET /api/product-versions`、`GET/POST /api/products/{product_id}/versions`、`POST /api/product-versions/{version_id}/advance-status` 和 `PATCH/DELETE /api/product-versions/{version_id}` 保持 SQL read model 分页筛选排序、产品内版本编码唯一、版本状态专用推进、需求状态同步、阻塞校验、repository-first 读取、handler 级版本/需求/审计写入和删除依赖校验契约。产品模块 API 已收口到独立 `app.api.routers.product_modules`：`GET/POST /api/products/{product_id}/modules` 和 `PATCH/DELETE /api/product-modules/{module_id}` 保持产品负责人权限、产品内模块编码唯一、repository-first 读取、handler 级模块/审计写入和删除前需求/任务/Bug 依赖校验契约。产品 Git 仓库 API 已收口到独立 `app.api.routers.product_git_repositories`：`GET/POST /api/products/{product_id}/git-repositories` 和 `PATCH/DELETE /api/product-git-repositories/{repo_id}` 保持产品负责人/研发负责人读取权限、产品负责人写权限、GitLab/GitHub provider 绑定校验、repository-first 读取、handler 级 Git 资源/审计写入和 `credential_ref_configured` 脱敏响应契约。相关系统 API 已收口到独立 `app.api.routers.related_systems`：`GET/POST /api/system/related-systems` 和 `PATCH/DELETE /api/system/related-systems/{system_id}` 保持产品负责人写权限、可选产品归属校验、全局系统编码唯一、repository-first 读取和 handler 级相关系统/审计写入契约。产品主体、迭代版本、产品模块、产品 Git 仓库和相关系统 router 共用 `app.services.product_config_context` 承载产品配置 source rows、repository 上下文、唯一性校验、审计事件构造和单记录写入/删除；产品配置域端点已完成 router 收口。路由边界测试必须保证产品主体、迭代版本、产品模块、产品 Git 仓库和相关系统端点只有单一 router 归属。

平台状态 API 已收口到独立 `app.api.routers.platform`，平台健康检查、TCP 依赖探测、运行数据访问模式、模型网关健康状态和 GBrain 长期记忆脱敏状态由 `app.services.platform_status` 统一构造。`/health` 保持免登录访问并返回 `status/postgres/redis/model_gateway/chat_gateway/embedding_gateway/data_access_mode/long_memory/trace_id`；`/api/long-memory/status` 保持登录访问并返回 GBrain 是否配置、能力列表和 `postgres_pgvector` 兜底检索器，不返回 URL、API Key 或密钥片段。路由边界测试必须保证这两个平台状态端点只有单一 router 归属。

模型网关列表只显示 `api_key_configured`，不显示明文密钥或密钥片段。配置测试接口使用临时参数调用 OpenAI-compatible `/chat/completions` 和 `/embeddings`，返回 Chat/Embedding 成功状态、模型、延迟、embedding 维度、跳过状态和错误码；测试范围支持 `chat_and_embedding`、`chat` 和 `embedding`，其中 `chat` 只验证 Chat 并把 Embedding 标记为 `skipped`，适配 ChatGPT OAuth 类不提供 `/embeddings` 的上游。测试不得保存配置或密钥，不写入模型调用日志，审计只记录 provider、测试范围和测试状态。存在 active/default 且已配置 API Key 的 OpenAI-compatible 模型网关时，非 code_review 任务启动会通过 `/chat/completions` 调用真实 provider 并要求返回 JSON 对象；AI 助手通过 `/api/assistant/chat` 调用同一 Chat 边界，服务端会通过 `app.services.assistant_tools` 先按用户问题生成 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等确定性 read-model 工具结果，再通过 `app.services.assistant_context` 注入当前产品、需求、AI 任务、Git 仓库、迭代进度、待确认 Review、代码评审结论、Bug 分布、知识沉淀、模型网关状态摘要和工具结果，使其能回答 AI Brain 系统信息和项目进展问题；助手 API 已收口到 `app.api.routers.assistant`，聊天工作流由 `app.services.assistant_chat` 统一处理工具结果生成、模型调用、会话创建/续写、用户级历史隔离、成功/失败模型日志、审计事件和错误码映射，router 只保留权限、request store 和响应封装入口；助手完整对话按登录用户保存到 `assistant_conversations` 和 `assistant_messages`，助手消息 metadata 持久化 `references` 与 `tool_results`，历史查询只返回本人会话，模型调用日志仍只保存脱敏元数据；知识索引会先生成文本 chunk，随后在 Embedding 可用时通过 `/embeddings` 写入 `knowledge_chunks.embedding`，检索只有存在当前用户可读向量 chunk 时才生成 query embedding；模型调用日志只记录 provider、model、purpose、tokens、latency、status、error 和配置 id，不记录 prompt、完整输出或密钥，其中助手调用使用 `purpose=assistant_chat`。模型网关配置缺失密钥时非 code_review 任务进入 `failed` 并返回 `MODEL_GATEWAY_CONFIG_INVALID`；非 code_review 任务 provider 调用失败返回 `MODEL_GATEWAY_FAILED`。code_review 任务已接入独立 `code_review_executor` 边界，默认 `CODE_REVIEW_EXECUTOR_TYPE=claude_code_skill`、`CODE_REVIEW_EXECUTOR_NAME=code-review`，由 `CODE_REVIEW_EXECUTOR_COMMAND` 指向外部命令适配器，输入 JSON 通过 stdin 提供，输出 JSON 通过 stdout 返回；测试或兼容环境可显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 复用模型网关适配器；若默认外部执行器命令为空且存在 active/default 模型网关或环境模型网关，系统会通过同一执行器边界自动改用 `model_gateway` 适配器，模型 prompt 必须携带 MR/PR 快照、已确认技术方案、需求快照和产品上下文，并将常见 Review 输出字段如 `overall`、`score` 规范化为 `risk_level` 与 executor metadata，避免本地全链路测试额外依赖外部命令。执行器调用成功写入 `code_review.executor_called` 审计事件；配置缺失、调用失败、超时、响应解析或结构化报告校验失败返回 `CODE_REVIEW_EXECUTOR_FAILED`，任务停在 `code_review_executor_failed` 并写入 `code_review.executor_failed` 审计事件，不得静默回退成本地输出。

产品配置、需求、知识文档、Bug、用户管理、用户反馈和模型网关配置已具备当前管理页所需 CRUD 能力；产品支持详情查询，便于从产品上下文进入配置和全链路脚本校验；用户使用指标和线上运行日志指标已具备真实登记和查询能力。产品管理页面通过“配置”弹窗维护模块、Git 资源和相关系统，需求交付菜单下的“迭代版本”页面集中维护 `product_versions`；`GET /api/product-versions` 批量返回版本及所属产品投影，需求列表返回 `product_code`、`product_name`、`version_code`、`version_name`、`assignee` 和 `created_at`，需求管理页基于该投影支持按迭代版本名、编码或“未排期”过滤需求范围，并在列表展示创建时间而不是更新时间；Bug 列表返回 `version_code`、`version_name` 并支持按 `version_id` 查询，Bug 管理页展示迭代版本列并可按版本名、编码或“未关联”过滤缺陷范围，登记 Bug 的目标版本下拉读取同产品未归档版本，允许选择 `planning`、`active`、`testing` 或 `released` 版本并过滤 `archived`，列表支持勾选多条 Bug 后批量更新状态、严重级别或处理人，批量接口逐条校验状态机并返回 updated/skipped 明细，记录 `bug.batch_updated` 与逐条 `bug.updated` 审计，任务列表在 PostgreSQL 模式通过 SQL join 返回产品名，前端产品管理、需求列表、Bug 列表、迭代版本和产品上下文下拉不再逐产品串行拉取版本。新增需求只强制选择产品，`version_id` 可为空，默认负责人 `assignee` 为创建人，审批后进入需求池，排入规划中或开发中迭代版本后才允许生成 AI 任务；需求管理页支持勾选同产品 `approved/planned` 需求后批量排期，迭代版本页支持从规划中或开发中版本行归集同产品需求池/已排期需求，批量排期接口返回 updated/skipped 明细并记录批量级与单需求审计；需求管理页还支持勾选非关闭/非取消需求批量分配负责人，批量分配接口更新 `requirements.assignee`、返回 updated/skipped 明细，并记录 `requirement.batch_owner_assigned` 与逐需求 `requirement.updated` 审计；需求管理页还支持勾选同产品 `planned` 需求批量生成产品详细设计任务，批量生成任务接口返回 generated/skipped 明细，合法需求进入 `designing` 并记录 `requirement.batch_tasks_generated` 与逐任务 `ai_task.created` 审计；迭代版本页在任意版本状态下都提供当前版本需求清单只读查看，避免测试中版本无法回看范围。迭代版本主状态为 `planning / active / testing / released`，`archived` 仅作为历史归档状态；版本状态变更必须走 `advance-status` 专用动作，先返回影响预览，再将符合条件的需求同步推进到 `ready_for_dev`、`testing` 或 `released` 并记录 `product_version.status_advanced` 与逐需求 `requirement.updated` 审计；其中 `active -> testing` 必须把版本内 `approved/planned/ready_for_dev/designing/developing/code_reviewing` 等已进入交付链路的需求统一推进到 `testing`，避免版本阶段和需求阶段不一致。Git 资源可选择 `gitlab` 或 `github` provider，相关系统可绑定 `product_id`，生成任务产品上下文时只纳入同产品且启用的相关系统；Git 凭据仅在新增/编辑时提交，列表只展示 `credential_ref_configured` 对应的配置状态，不回显凭据引用或 token。知识中心已具备独立导入、列表、文本 chunk 索引、Embedding 可用时的向量索引、权限过滤后的关键词/向量混合检索、索引错误展示、`index_failed` 重试、`text_indexed` 补向量索引和沉淀审核入口；主动导入知识文档可选绑定 `product_id`，任务沉淀采纳的知识文档可从沉淀任务回溯产品归属。任务中心已具备真实产品详细设计启动、Review 确认、技术方案任务创建、开发计划任务创建、自动化测试任务创建、发布评估任务创建、上线后分析任务创建、Markdown 导出和多选批量取消入口；任务管理列表摘要返回产品名、创建时间和更新时间，并支持按所属产品与创建时间段筛选；批量取消接口逐条校验任务状态，合法任务进入 `cancelled`，重复、缺失或终态任务返回 skipped 明细，并记录 `ai_task.batch_cancelled` 与逐任务 `ai_task.cancelled` 审计；模型网关或 code-review 执行器临时失败时，停在 `model_gateway_failed` 或 `code_review_executor_failed` 的任务可用原 task_id 重试，避免为同一阶段复制新任务导致链路割裂；AI 任务创建和人工确认会把需求推进到 `designing`、`ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released` 或 `accepted` 等研发状态；`automated_testing` 任务的 `bug_suggestions` 在人工确认后会写入 `bugs`，来源为 `ai_auto_test`；`post_release_analysis` 任务的 `bug_suggestions` 在人工确认后会写入 `bugs`，来源为 `ai_post_release`，并保留产品、版本、需求和任务关联；日志监控已具备 GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标登记与筛选入口；用户洞察页已具备真实用户反馈登记、用户使用指标登记与筛选、固定列宽列表、详情弹窗、迭代建议生成、确认和可选转需求入口，用户反馈创建人可为任意已登录用户，状态处理、指标登记和迭代建议操作需 `product_owner`、`rd_owner` 或 `admin`。

需求管理页支持勾选需求批量推进状态。目标状态必须符合研发流程前进路径，合法需求状态更新并记录 `requirement.batch_status_advanced` 与逐条 `requirement.updated` 审计；终态、重复、缺失或不符合路径的需求进入 skipped 明细，不回滚同批次合法项。批量推进到 `planned`、`ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released`、`accepted` 等交付链路状态时，需求必须已归属迭代版本；未排期需求必须先通过批量排期或编辑归入版本，避免需求全链路缺少版本节点。需求批量排期、批量分配负责人、批量推进状态和批量生成任务完成后，前端必须展示结果弹窗，包含批次号、成功数、跳过数以及每条 skipped 的需求 ID、错误码和原因，避免用户只能从 toast 猜测哪些项未处理。

迭代版本阶段流转、需求同步影响计算和阻塞规则由 `app.services.version_status` domain service 承载，接口 handler 只负责权限、审计、repository 写入和响应拼装；后续版本状态规则调整应优先修改该服务并补充 service 层单测。

任务失败恢复必须复用单任务启动状态机：只有 `status=failed` 且 `current_step` 为 `model_gateway_failed` 或 `code_review_executor_failed` 的任务允许重试。任务管理批量重试接口逐条校验任务状态，合法任务调用同一 `/start` 逻辑；成功进入待确认的任务返回 `updated`，已尝试但模型网关或代码评审执行器仍失败的任务返回 `retried` 并携带错误码，不可重试、重复或不存在的任务返回 `skipped`。批次级审计事件为 `ai_task.batch_retried`，逐任务重试沿用 `ai_task.retry_started`。任务管理批量取消和批量重试完成后，前端必须展示结果弹窗；取消结果展示批次号、取消数、跳过数和 skipped 明细，重试结果展示批次号、重试数、成功数、仍失败数、失败错误码/错误信息和 skipped 明细，避免用户只能从 toast 推断任务是否恢复成功。

Bug 来源、严重级别、状态机、初始状态和产品/版本/模块/需求/任务/重复缺陷上下文校验由 `app.services.bug_lifecycle` domain service 承载，Bug 创建、单条更新和批量处理 handler 只负责权限、审计、repository 写入和响应拼装；后续 Bug 状态规则调整应优先修改该服务并补充 service 层单测。Bug 管理批量处理完成后，前端必须与需求、任务批量操作共用结果弹窗展示批次号、更新数、跳过数和每条 skipped 的 Bug ID、错误码和原因，避免用户只能从 toast 判断哪些缺陷未处理。

需求批量排期的目标版本选择应与后端校验一致：需求管理页读取该产品全部版本并仅保留 `planning`/`active`，过滤 `testing`、`released` 和 `archived`；批量接口必须以追加/upsert 方式保存 `requirement.batch_scheduled` 审计事件，不能使用覆盖式审计快照保存导致历史批次审计被删除。

研发运营统一列表和用户洞察统一列表在 PostgreSQL 运行时均使用 repository SQL read model 聚合查询，分别对 GitLab/Jenkins/线上日志以及用户使用/用户反馈/迭代建议来源在 SQL 层完成筛选、排序和分页；接口层 MemoryStore 拼装仅保留为测试 helper fallback，不作为生产主列表数据路径。

产品管理列表在 PostgreSQL 运行时使用 `products` + 当前版本 lateral 投影 + 模块计数 SQL read model 查询，`active_only/code/name/owner_team/status` 筛选、当前版本/模块数投影、列表排序和分页必须在数据库层完成；产品详情、配置弹窗和单产品版本/模块/Git 资源下拉仍可使用轻量 repository 查询。迭代版本列表在 PostgreSQL 运行时使用 `product_versions` + `products` 的 SQL read model 查询，`active_only/code/name/product/product_id/status` 筛选、所属产品投影、列表排序和分页必须在数据库层完成。需求管理列表在 PostgreSQL 运行时使用 `requirements` + `products` + `product_versions` 的 SQL read model 查询，`priority/product/product_id/status/title/version/version_id` 筛选、列表排序和分页必须在数据库层完成；接口层仅补充 `query/performance` 观测元数据。需求详情、需求全链路、AI 任务运行态、Review、回写结果和 Markdown 导出仍可使用 task workflow source rows 聚合上下文，但不得作为需求列表页的全量加载替代。Bug 管理列表在 PostgreSQL 运行时使用 `bugs` + `product_versions` 的 SQL read model 查询，`module/product_id/severity/source/status/title/version/version_id` 筛选、列表排序和分页必须在数据库层完成；旧 `list_bugs` 仅作为兼容 fallback，不得作为生产主列表的全量加载路径。

审计与运行页面支持查看真实审计详情，并从审计主体优先发起生命周期链路追踪。生命周期视图、需求全链路详情和首页 IT 团队看板的 AI 任务、待确认 Review、知识沉淀和风险信号聚合会先按任务类型读权限过滤，不能通过聚合接口绕过任务详情权限。生命周期上下文已支持从真实 Bug、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户使用指标、用户反馈和迭代规划建议起点回溯同产品/版本/模块任务链路，并把这些真实证据写入 downstream 关系；缺少对应证据时返回动态 `missing_context`，不合成兜底关系。需求全链路详情由 `GET /api/requirements/{requirement_id}/full-chain` 承载，面向需求管理页一次返回需求、产品、迭代版本、AI 任务、Review、GitLab MR / GitHub PR 兼容快照、Code Review 报告、Bug、Jenkins 发布和知识沉淀候选，并生成按发生时间排序的页面时间线；前端在需求管理页保留弹窗快查，同时提供隐藏菜单路由 `/delivery/requirements/{requirement_id}/full-chain` 作为可刷新、可复制链接的独立详情页，两者共用同一阶段进度、阶段明细、时间线、PR/MR 快照风险摘要、diff 文件树和 Review Checklist 展示组件；时间线支持按事件类型筛选并展示筛选后/总事件数，便于在复杂需求链路中聚焦查看 Review、代码评审、Bug、发布或知识沉淀；阶段明细必须按需求、迭代版本、AI 任务、Review、PR/代码评审、Bug、发布和知识沉淀分组展示可展开实体清单，并提供跳转到对应管理页的实体链接，不得再多接口拼装该详情。首页 IT 团队看板已基于真实产品、需求、AI 任务、待确认 Review、知识和审计数据返回 MVP 聚合摘要；传入 `product_id` 时，知识文档和审计事件也必须按产品归属过滤，不能把其他产品的知识或审计计数混入当前产品；看板属于汇总型视图，允许在读取 PostgreSQL source rows 后由 Python 做跨主体聚合和展示计算，后续优化以慢查询证据、缓存快照和权限边界为依据，不强制先改成 SQL/物化 read model。产品、需求、迭代版本、Bug、任务、知识文档、审计事件、研发运营指标和用户洞察主列表均已通过后端接口承载分页、排序和筛选，前端主列表不得再拉全量数据后本地拼装；核心管理主列表响应同时返回 `query` 与 `performance` 元数据，记录生效筛选、分页、排序、响应耗时、返回条数、总数和慢查询阈值，作为页面慢问题定位依据；其中用户洞察统一列表在 PostgreSQL 运行时由 repository SQL read model 通过 `UNION ALL` 聚合用户使用指标、用户反馈和迭代建议，并在 SQL 层执行 `category/summary/status` 筛选、`category/id/owner/status/summary/updated_at` 排序和分页，不再由接口层拉三类全量数据后合并。前端管理主列表通过统一 `ManagementListPage` 兜底固定布局、横向滚动、文本省略、普通列默认 160px 稳定宽度和右侧固定操作列；操作列默认 220px，避免详情、编辑、删除、生成任务等行内动作挤压，页面仍可按业务宽度显式覆盖；模型网关配置、用户和角色等低数据量子表可暂保留独立列表接口或本地过滤，但不得作为管理主列表的多接口聚合替代。GitLab MR / GitHub PR 预览和 diff 快照已接入只读 API：GitLab 产品 Git 资源需提供可解析的 `remote_url` 或 `GITLAB_BASE_URL`，GitHub 产品 Git 资源需提供 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`，GitHub Enterprise 可通过 `GITHUB_BASE_URL` 指定 API base；凭据引用推荐使用环境变量或服务端密钥引用，本地联调可直填只读 token，系统只读取变更元信息、文件摘要、diff 文件树、风险摘要和 Review Checklist，不回写 GitLab/GitHub；任务中心创建 Code Review 前必须展示这些预览信息，帮助确认 MR/PR 变更范围和重点检查项。日志监控页面保留 GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标登记/查询，不依赖前端示例数据；外部自动采集器尚未接入。无记录时返回真实空集合，不提供前端本地兜底行或后端伪造统计数据；采集运行记录和待归属数据队列仅作为历史兼容 API/结构表保留，不再作为当前前端功能入口。

管理列表自定义渲染列必须与普通文本列遵守同一布局约束：`ManagementListPage` 默认包裹稳定单元格容器，限制 Tag、Space、Typography 和状态摘要组合的最大宽度并启用省略，避免角色职责、用户反馈摘要、DevOps payload、任务标题或 Bug 标题过长时撑开宽表、挤压右侧操作列或破坏横向滚动。

需求全链路详情必须提供“导出链路报告”操作，基于同一个 full-chain payload 在前端生成 Markdown 报告，包含需求、产品、迭代版本、阶段实体摘要和完整时间线，用于真实迭代验收、代码 Review 和测试留痕。

需求全链路详情在需求已归属迭代版本时必须展示“版本内需求对比”，通过需求列表 SQL read model 按 `version_id` 读取同版本需求摘要，展示同版本需求总数、状态分布和当前需求位置；该对比区只作为只读辅助视图，加载失败不得影响主 full-chain 链路展示。

当前补充实现：迭代规划建议已作为真实业务主体接入 `iteration_plan_suggestions` 与 `iteration_plan_decisions`。生成接口只基于真实用户反馈和 Bug 证据生成建议；无证据时返回空集合，不生成占位建议。确认接口支持采纳、修改后采纳、驳回和显式转需求，只有确认且 `convert_to_requirement=true` 时才创建真实 `requirements` 记录，需求来源为 `product_planning`。用户反馈也支持从洞察列表直接转需求，转需求事务同时写入 `requirements`、更新 `user_feedback.related_requirement_id/status/product_id` 并记录审计，需求来源为 `user_feedback`。

用户使用指标已作为真实业务主体接入 `user_usage_metrics`。产品负责人、研发负责人或管理员可以登记真实聚合指标，系统按产品、模块、功能、用户群体和时间窗口筛选查询，并记录 `usage_metric.created` 审计事件；无指标时返回真实空集合，不生成兜底数据。

GitLab 每日代码指标已作为真实业务主体接入 `gitlab_daily_code_metrics`。产品负责人、研发负责人或管理员可以按产品和 active GitLab 仓库登记真实聚合指标，系统按产品、仓库和日期筛选查询，并记录 `gitlab_daily_code_metric.created` 审计事件；无指标时返回真实空集合，不生成兜底数据。

Jenkins 发布记录已作为真实业务主体接入 `jenkins_release_records`。产品负责人、研发负责人或管理员可以按产品版本登记真实发布记录，系统按产品、版本、状态和环境筛选查询，并记录 `jenkins_release.created` 审计事件；无记录时返回真实空集合，不生成兜底数据。

线上运行日志指标已作为真实业务主体接入 `online_log_metrics`。产品负责人、研发负责人或管理员可以按产品、模块、环境和时间窗口登记真实聚合指标，系统计算错误率、保存延迟和核心业务事件，并记录 `online_log_metric.created` 审计事件；无记录时返回真实空集合，不生成兜底数据。外部线上日志自动采集器仍属后续增强，当前入口用于手工登记或导入真实聚合数据。

采集运行记录已作为真实业务主体接入 `collector_runs`。产品负责人、研发负责人或管理员可以登记 GitLab、Jenkins、线上日志、用户使用、用户反馈和迭代建议相关采集运行，系统记录采集类型、产品归属、来源系统、运行状态、开始/结束时间、导入数量、错误说明和 payload 摘要，并记录 `collector_run.created` / `collector_run.updated` 审计事件；运行记录用于追踪导入尝试，不自动生成任何指标或反馈数据。外部自动采集器接入后应复用该台账记录每次执行。

待归属数据队列已作为历史兼容业务主体接入 `pending_attribution_items`。当前前端不再提供待归属数据队列入口；已有 API 和结构表保留用于兼容历史数据和后续外部集成，队列处理仍不得自动创建指标、反馈、需求或迭代建议。

研发扩展任务当前支持从已完成 `technical_solution` 创建 `development_planning`、`automated_testing` 和 `release_readiness`，并从已完成 `release_readiness` 创建 `post_release_analysis`。这些任务复用模型网关、Graph Run、人工确认和知识沉淀候选机制；未确认前不产生下游副作用。发布评估任务创建时会保存源技术方案、同产品/版本/需求 Bug、Jenkins 发布记录、线上日志指标和 GitLab 每日代码指标快照；上线后分析任务创建时会保存源发布评估、发布记录、线上日志和 Bug 快照。自动化测试任务确认后把模型输出中的 Bug 建议转换为 `ai_auto_test` 来源 Bug，并记录 `bug.created` 与 `automated_testing.bugs_created` 审计事件；上线后分析任务确认后把模型输出中的 Bug 建议转换为 `ai_post_release` 来源 Bug，并记录 `bug.created` 与 `post_release_analysis.bugs_created` 审计事件。

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
| product_config | 产品、版本、版本级代码分支、模块、Git 资源配置、相关系统配置、GitLab/GitHub 仓库绑定和凭据引用 | products, product_versions, product_version_branch_configs, product_modules, product_git_repositories, related_systems |
| requirement | 需求台账、审批和任务生成入口 | requirements, product_config, ai_task |
| ai_task | AI 任务生命周期、任务类型、状态流转、任务详情 | graph_runtime, audit |
| graph_runtime | LangGraph 编译、启动、中断、检查点、恢复 | ai_task, review, model_gateway, code_review_executor |
| review | 人工确认、修改采纳、拒绝、补充信息 | human_reviews |
| knowledge | 文档导入、chunk、embedding、检索、权限过滤 | pgvector, model_gateway |
| long_memory | GBrain 长期记忆、混合检索、答案合成、知识图谱连接器 | knowledge, model_gateway |
| model_gateway | 聊天和 embedding 调用、超时、重试、使用量记录 | 外部模型服务 |
| git_review | GitLab MR / GitHub PR 元信息和 diff 拉取、输入快照、报告归档 | product_config, ai_task, audit |
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
| 用户洞察 | user_insights, iteration_planning | 用户使用数据、用户反馈、AI 迭代规划建议和采纳追踪 | 关联产品规划、需求池、Bug、线上日志、发布记录和研发投入；AI 只生成建议，正式转需求或进入迭代计划前必须由产品负责人确认 |
| 研发上下文图谱 | lifecycle_context | 需求、设计、方案、代码、Review、测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识和审计的跨阶段关系 | 以产品、版本、模块、需求和 AI 任务为主线，支持全流程感知、影响分析和风险定位 |

### PRD 草案与产品详细设计实现边界

需求审批前的轻量需求评估或 PRD 草案预览不是独立 `task_type`，不要求单独 Graph 节点持久化正式产物。正式产品产物由审批后创建的 `product_detail_design` 任务生成，并在 `human_reviews` 中由产品负责人确认。`technical_solution`、`code_review`、Markdown 导出和知识沉淀均应引用已确认的 `product_detail_design` 输出或其快照，避免直接依赖未审批需求草稿。Markdown 导出由独立 `export` router 调用 `task_workflow_context` 和 `markdown_export` service 完成任务工作流只读上下文投影、任务读取权限校验、完成态校验和 Markdown 渲染，不得反向调用 `main.py` 中的 legacy handler/helper。代码评审报告读取由独立 `code_review_reports` router 调用 `task_workflow_context` 和 `code_review_report` service 完成任务上下文读取、任务读权限校验、报告关联校验和报告返回，不得反向调用 `main.py` 中的 legacy handler/helper。

| task_type | 说明 | 主要输入 | 主要输出 | 关键确认点 |
|-----------|------|----------|----------|------------|
| `product_detail_design` | 产品详细设计 | 已排期需求、产品上下文、历史知识、业务规则 | 详细 PRD、交互说明、页面字段、业务规则、验收标准 | 产品负责人确认 |
| `technical_solution` | 技术方案设计 | 产品详细设计、系统架构、代码仓库上下文、技术规范 | 技术方案、模块边界、接口设计、数据模型、风险依赖 | 研发负责人确认 |
| `development_planning` | 代码开发辅助 | 技术方案、任务拆解、代码仓库上下文 | 开发任务清单、代码变更建议、实现步骤、待修改文件建议 | 研发负责人确认 |
| `code_review` | GitLab MR / GitHub PR 代码 Review | MR/PR 元信息和 diff 快照、关联需求、技术方案、产品上下文、项目规范 | 结构化 Review 报告、问题清单、风险等级、文件/行号、修改建议、执行器元数据 | Reviewer 确认 |
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

开发工程师、测试负责人、测试人员和发布负责人的写权限按 RBAC 目标态作为研发交付扩展预置角色补齐；MVP 当前实现仍由 `product_owner`、`rd_owner`、`reviewer`、`admin` 等角色兼容承载相关动作。
角色定义的运行时来源是后端角色目录常量，持久化字典为 PostgreSQL `role_definitions` 表；每个角色必须同时声明业务角色映射 `business_roles`、可见入口 `menu_scope` 和限制边界 `limitations`，用于角色管理、用户管理角色目录和知识权限配置的一致展示。`users.roles` 和知识 `permission_roles` 只允许引用该目录中的角色 code。系统管理/角色管理页面必须从 `/api/auth/roles` 只读展示角色定义；用户管理页面和知识权限配置必须从同一接口加载固定多选控件，不能让管理员自由输入或创建未定义角色。

后续系统权限管理按 [RBAC 重设计](rbac-redesign.md) 演进，开发执行以 [RBAC Redesign Implementation Plan](../../superpowers/plans/2026-06-09-rbac-redesign-implementation.md) 为任务级计划：固定六角色保留为 MVP 兼容预置角色模板，并新增 `developer`、`test_owner`、`tester`、`release_owner` 等研发交付扩展预置角色；角色管理从只读目录升级为角色 CRUD，并支持配置功能菜单；用户登录后后端返回 `menu_tree`，前端左侧菜单按授权菜单渲染；v1.2 引入组织/部门维度，人员归属部门，产品负责人和研发负责人等产品范围由产品管理页成员配置维护，知识权限使用独立知识空间承载产品研发和文档资料；外部 SSO 身份必须绑定到系统 `users.id` 后才参与授权计算，SSO 不直接下发角色、部门或范围；高危权限不引入双人审批流，由系统管理员配置并写入审计；业务接口逐步从角色 code 判断迁移为权限点和数据范围校验，角色、权限、菜单、部门、产品成员、知识空间、用户授权和范围授权均以 PostgreSQL 结构表为事实源。

React 工作台应提供十个主入口，而不是只围绕任务详情组织全部能力：

| 主入口 | 目标用户 | 页面能力 |
|--------|----------|----------|
| 首页 IT 团队看板 | 管理者、产品负责人、研发负责人、平台运营 | 需求总览、研发进展、Bug 趋势、线上系统健康、核心业务运行、用户使用趋势、用户反馈趋势、AI 迭代规划建议摘要、发布状态 |
| 产品管理 | admin, 产品负责人 | 产品列表、详情、版本、模块、Git 资源和相关系统维护 |
| 需求管理 | product_owner, rd_owner | 需求列表、创建时间展示、新增需求、需求详情、审批、驳回、批量分配负责人、批量推进状态、批量排期/归集需求、批量生成任务、生成任务、关闭 |
| 任务中心 | rd_owner, 产品/研发/测试/发布负责人 | 任务列表、任务详情、任务类型筛选、待确认弹窗、GitLab MR / GitHub PR 选择、diff 快照、Review 报告、Review 报告确认、自动化测试、发布上线评估、上线后分析、回写结果、Markdown 导出 |
| Bug 管理 | 测试负责人、研发负责人、产品负责人 | AI 自动测试 Bug、人工登记 Bug、创建时间展示、分派、修复、验证、关闭、重复归并 |
| 日志监控 | IT 管理者、研发负责人、平台运营 | GitLab 提交与代码质量、Jenkins 发布记录和线上日志指标；不展示采集运行记录和待归属数据队列 |
| 用户洞察 | 产品负责人、IT 管理者、研发负责人 | 用户反馈列表、详情弹窗、固定列宽列表、右侧固定操作列、反馈处理和转需求入口；使用指标登记与迭代建议生成不作为用户洞察页面主动作 |
| 知识中心 | 知识维护者、研发负责人 | 文档导入、索引状态、知识检索、沉淀审核、权限和标签维护；第一阶段已按 [知识管理升级设计](knowledge-management-design.md) 引入空间、目录、MinIO/S3-compatible 资产、导入任务和 chunk set，后续继续演进解析器、父子分块和质量治理 |
| 审计与运行 | admin, 平台运营 | 审计事件、运行记录、健康检查和失败排查 |
| 系统管理 | admin | 用户管理、角色管理、模型网关配置；角色管理只读展示固定角色目录，模型网关页面只展示 API Key 是否已配置，新增或编辑时可提交密钥，编辑留空表示保留服务端现有密钥 |

任务中心不得依赖前端一键演示数据。MVP-A 的正式页面操作链路为：需求管理审批并生成 `product_detail_design` 任务，任务中心启动任务并通过待确认弹窗确认输出；如人工确认要求补充信息，页面调用 `/api/reviews/{review_id}/request-more-info` 将任务退回 `waiting_more_info`，再通过任务操作弹窗提交 `/api/ai-tasks/{task_id}/more-info` 使任务回到 `draft` 后重新启动。确认通过后可基于已确认产品详细设计创建 `technical_solution` 任务，确认后导出 Markdown。任务列表行内只保留单一“操作”入口，启动、确认、要求补充、提交补充、生成技术方案、导出、创建 Code Review、模拟 Issue 和查看报告均在弹窗内触发；任务操作弹窗采用上方任务摘要、下方纵向操作的结构，不得恢复左右分栏确认台或列表横向堆叠操作按钮，并保持与其他管理页一致的查询表格风格。已完成技术方案可继续通过任务中心选择产品 GitLab/GitHub 代码库；GitHub 仓库应先通过 PR 列表接口展示可访问 PR，用户选择后再预览 PR、生成 diff 快照并创建 `code_review` 任务；GitLab 仍可通过 MR IID 预览和快照进入 Review。Review 报告在内部页面查看和人工确认，仍不得回写 GitLab/GitHub。MVP-C 的任务列表应提供已完成任务的模拟 Issue 查询/生成入口，知识中心应提供沉淀候选审核入口，二者均调用真实后端接口且不得展示兜底示例数据。所有新增或编辑弹窗中涉及日期/时间登记的字段必须使用 Ant Design DatePicker；产品/迭代版本日期以 `YYYY-MM-DD` 保存，GitLab 指标日期以 `YYYY-MM-DD` 保存，用户使用、线上日志和 Jenkins 发布时间以 `YYYY-MM-DDTHH:mm:ssZ` 保存，前端不得再使用普通文本框承载这些时间选择。

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
  │          ├── product_version_branch_configs >── product_git_repositories
  │          ├── product_modules
  │          ├── product_git_repositories
  │          ├── gitlab_daily_code_metrics
  │          ├── jenkins_release_records
  │          ├── online_log_metrics
  │          ├── user_usage_metrics
  │          ├── user_feedback
  │          ├── collector_runs
  │          ├── scheduled_jobs
  │          ├── scheduled_job_runs
  │          ├── pending_attribution_items
  │          ├── iteration_plan_suggestions
  │          ├── iteration_plan_decisions
  │          ├── lifecycle_context_edges
  │          ├── lifecycle_risk_signals
  │          ├── bugs
  │          └── dashboard_metric_snapshots
  │
  ├── related_systems
  ├── model_gateway_configs
  ├── ai_agents
  └── ai_skills

knowledge_spaces ──< knowledge_documents ──< knowledge_chunk_sets ──< knowledge_chunks
knowledge_documents ──< knowledge_assets
knowledge_documents ──< knowledge_import_jobs
knowledge_spaces ──< knowledge_folders
assistant_conversations ──< assistant_messages

requirements ──< ai_tasks
```

### 核心表结构

| 表名 | 说明 | 关键约束 |
|------|------|----------|
| role_definitions | 系统角色字典 | `code` 主键；记录 `category`、`business_roles`、`responsibilities`、`data_scope`、`decision_scope`、`menu_scope`、`limitations`、`permissions`、`is_assignable` 和 `sort_order`；MVP 可分配角色为 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer`。 |
| users | 本地用户和角色 | email 唯一。 |
| brain_apps | 业务大脑配置 | `code` 唯一，v1 默认 `rd_brain`。 |
| products | 产品配置 | `code` 唯一，提交需求必须选择启用产品。 |
| product_versions | 产品迭代版本 | 同一产品内 `code` 唯一，在需求交付菜单集中维护；主状态为 `planning / active / testing / released`，`archived` 仅用于历史归档；仅 `planning / active` 可用于需求排期或新开发任务。 |
| product_version_branch_configs | 迭代版本代码分支配置 | 归属于产品迭代版本和产品 Git 资源；同一版本同一仓库只允许一条分支配置，记录 `base_branch`、`working_branch`、`branch_status`、`creation_source` 和说明；用于让开发任务、PR/MR 快照和代码 Review 继承版本级代码上下文。 |
| product_modules | 产品模块 | 同一产品内 `code` 唯一，模块可选。 |
| product_git_repositories | 产品 Git 资源 | 记录代码、文档、PRD、测试仓库上下文；GitLab 资源需保存 project_id 或 project_path，GitHub 资源需保存 owner/repo 形式 project_path 或可解析 remote_url，同时保存 provider、默认分支、凭据引用和启用状态。 |
| requirements | 需求实体 | 状态为 `draft / submitted / approved / planned / designing / ready_for_dev / developing / code_reviewing / testing / ready_for_release / released / accepted / rejected / deferred / cancelled / closed`；`source` 记录需求来源，覆盖业务部门、产品规划、用户反馈、内部调研和其他；`version_id` 可为空，未排期需求不能生成 AI 任务。历史 `pending_approval` 和 `task_created` 在运行时分别兼容为 `submitted` 和 `designing`。 |
| related_systems | 相关系统配置 | `code` 唯一，可写入任务输入上下文。 |
| model_gateway_configs | 平台模型网关配置 | 支持一个默认启用配置，API 响应只返回 API Key 是否已配置，不返回明文或密钥片段。 |
| model_gateway_logs | 模型调用日志 | 只记录 provider、model、purpose、tokens、latency、status、error 等元数据，不保存完整 prompt 或完整输出。 |
| ai_skills | AI 能力包配置 | 记录 `code`、`version`、输入/输出 schema、prompt_template、allowed_tools、required_context、risk_level、requires_human_review 和状态；Skill 不保存密钥。 |
| ai_agents | AI 执行角色配置 | 记录业务大脑、默认模型网关、system_prompt、默认 Skill、执行策略、工具策略和状态；Agent 只能引用模型网关或凭据引用，不直接保存外部系统 token。 |
| integration_plugins | 集成插件定义 | 记录插件 `code`、`name`、`protocol=http/mcp_http/mcp_stdio`、`category`、risk_level 和状态；`category` 必须使用约定枚举 `general/data_warehouse/devops/issue_tracking/observability/knowledge_base/collaboration/ai_service/business_system`，前端以选择项维护，后端拒绝自由文本；第一阶段 HTTP 与 MCP HTTP 可执行，MCP stdio 仅允许登记配置，真实执行需等待命令隔离方案。 |
| plugin_connections | 插件连接配置 | 记录插件归属、环境、endpoint_url、auth_type、auth_config、超时、重试和状态；`environment` 必须使用约定枚举 `default/dev/test/staging/prod/sandbox`，前端以选择项维护，后端拒绝自由文本；新增连接时认证配置默认按 `none/bearer/api_key_header/basic` 展示 Token、Header 或 Basic 字段并生成 `auth_config`，JSON 仅作为高级修改入口且可反向同步到可视化字段；连接列表提供测试入口，测试 endpoint 可达性和认证配置并写入审计，测试结果必须包含 endpoint、协议、认证、HTTP 请求或 MCP `tools/list` 诊断步骤和脱敏请求摘要；API 响应必须对 token、secret、password、api_key 等字段脱敏，数据库不得把插件连接当成业务数据源。 |
| plugin_actions | 插件动作配置 | 记录插件、默认连接、action_type=http_request/mcp_tool、输入/输出 schema、request_config、result_mapping、requires_human_review 和状态；前端新增 HTTP 动作时默认以 Params/Headers 表格维护 `request_config.query` 和 `request_config.headers`，参数值支持 `{{current_date}}`、`{{current_date-7}}` 等系统变量表达式，高级 JSON 只用于精修完整 request_config，且必须支持可视化表格与 JSON 双向同步；动作配置页展示请求预览，动作列表支持试运行并返回请求预览、响应摘要和 `result_mapping` 命中情况；定时任务引用动作，Skill 只消费动作输出。 |
| plugin_invocation_logs | 插件调用日志 | 记录插件、连接、动作、定时作业/运行实例、触发方式、状态、请求摘要、响应摘要、耗时、错误和 trace_id；日志只保存摘要，不保存完整敏感请求。 |
| assistant_conversations | AI 助手会话 | 按 `user_id` 归属当前登录用户，记录可选 `product_id`、标题、消息数、最后消息时间和标准时间字段；会话列表只返回本人记录。 |
| assistant_messages | AI 助手消息 | 关联 `assistant_conversations`，记录 user/assistant 角色、消息内容、可选模型和建议；会话详情只允许本人读取。 |
| ai_tasks | 用户可见 AI 任务 | 状态必须匹配统一任务状态机；`task_type` 标识产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估或上线后分析；`input_json` 保存需求快照、产品上下文、启动参数和 MR/PR Review 输入快照引用。 |
| gitlab_mr_snapshots | MR/PR 兼容输入快照 | 记录 source_provider、repository_id、project_id 或 project_path、mr_iid/PR number、title、author、source/target branch、base/head sha、diff_refs、changed_files_summary、diff_storage_ref、diff_size_bytes、snapshot_hash、requirement_id、technical_solution_task_id、created_by、created_at 和 updated_at；快照不可变，重新 Review 必须创建新快照。 |
| code_review_reports | 代码 Review 报告 | 记录 task_id、MR/PR 快照、执行器元数据、summary、risk_level、findings、人工确认状态和内部归档时间；v1 MVP 不回写 GitLab/GitHub。 |
| graph_runs | LangGraph 运行记录 | 保存 runtime、节点路径、checkpoint 和 state snapshot 引用。 |
| human_reviews | 人工确认记录 | `version` 用于乐观锁。 |
| knowledge_spaces | 知识空间 | 当前知识权限和业务边界，绑定 owner、空间成员和后续产品/部门范围；新上传文档按空间权限读取。 |
| knowledge_folders | 知识目录 | 当前空间内信息架构，继承空间权限，不引入目录级 ACL。 |
| knowledge_documents | 知识文档 | 记录来源、权限和索引状态，支持主动导入、索引失败重试、归档、知识空间归属和可选目录归属。 |
| knowledge_assets | 知识文件资产 | 对象存储元数据投影，MinIO/S3-compatible 存储保存原始文件和解析产物，PostgreSQL 保存资产元数据、权限归属和审计上下文。 |
| knowledge_import_jobs | 知识导入任务 | 当前记录上传、解析、分块和向量化结果；后续扩展异步转换、失败重试和进度细分。 |
| knowledge_chunk_sets | 知识分块版本 | 一次解析/分块/Embedding 版本，文档通过 active chunk set 控制当前检索版本。 |
| knowledge_chunks | 知识切片 | embedding 维度必须匹配配置模型。 |
| mock_issues | 模拟回写 Issue | idempotency key 唯一。 |
| knowledge_deposits | 知识沉淀候选 | `ai_task_id + deposit_type + content_hash` 去重。 |
| audit_events | 审计事件 | 记录任务、主体类型、主体 ID、事件类型、操作者、事件载荷、写入序号和创建时间。 |
| gitlab_daily_code_metrics | GitLab 每日代码指标 | 按 product_id、repository_id、metric_date 聚合提交、人员、质量和风险摘要。 |
| jenkins_release_records | Jenkins 发布记录 | 按 product_id、version_id、job_name、build_id 记录构建、部署、失败原因和触发人。 |
| online_log_metrics | 线上运行日志指标 | 按 product_id、module_code、environment、time_window 聚合错误率、延迟和核心业务事件。 |
| user_usage_metrics | 用户使用指标 | 按 product_id、module_code、feature_code、user_segment、time_window 聚合活跃、访问、转化、停留、异常退出和低使用功能。 |
| user_feedback | 用户反馈记录 | 记录来源渠道、反馈类型、满意度或情绪倾向、标签、关联产品模块、创建人、处理状态和可选关联需求；转需求后状态同步为 `linked`。 |
| collector_runs | 采集运行记录 | 记录 collector_type、product_id、source_system、status、started_at、finished_at、records_imported、error_message 和 payload_summary；终态不可回到 running，failed 必须有错误说明。 |
| scheduled_jobs | 定时系统作业定义 | 记录 job_type、schedule_type、cron_expression/interval_seconds、timezone、enabled、product_id、source_system、config_json、execution_mode、agent_id、skill_ids、model_gateway_config_id、plugin_action_id、plugin_connection_id、plugin_input_mapping、plugin_output_mapping、重试/超时/锁租约和 next_run_at；`plugin_input_mapping` 支持 `{{current_date}}`、`{{current_date-7}}`、`{{last_full_week.start}}` 等动态时间 token，运行时按作业 timezone 解析；前端默认以参数表格配置插件输入映射，JSON 只作为高级修改入口并支持表格/JSON 双向同步。 |
| scheduled_job_runs | 定时系统作业运行实例 | 记录 scheduled_job_id、collector_run_id、触发方式、计划时间、运行状态、锁租约、导入数量、错误信息、result_summary、config_snapshot、resolved_agent_snapshot、resolved_skill_snapshots、resolved_prompt_snapshot、tool_policy_snapshot、resolved_plugin_snapshot 和 plugin_invocation_log_id。 |
| pending_attribution_items | 待归属数据队列 | 记录 source_type、source_system、collector_run_id、raw_subject_id、summary、raw_payload、建议归属、confidence、status、resolution_action、resolved_*、created_by 和 resolved_by；pending / resolved / ignored 三态，处理不自动生成业务数据。 |
| iteration_plan_suggestions | AI 迭代规划建议 | 记录规划周期、建议需求、推荐理由、证据链、业务价值、风险信号、依赖条件、预估研发投入、建议优先级和置信度。 |
| iteration_plan_decisions | 迭代规划确认记录 | 记录产品负责人对建议的采纳、修改后采纳或驳回决定，可关联转化后的正式需求。 |
| lifecycle_context_edges | 研发上下文关系边 | 记录 source_subject 与 target_subject 的关系、置信度、来源模块和时间，用于跨阶段追溯。 |
| lifecycle_risk_signals | 全流程风险信号 | 记录需求变更、设计缺口、代码质量、Review、测试、Bug、发布和线上异常等风险信号。 |
| bugs | Bug 记录 | 来源为 `ai_auto_test / ai_post_release / manual_test`，状态流转覆盖分派、修复、验证和关闭。 |
| dashboard_metric_snapshots | 首页看板快照 | 保存按产品、时间窗口聚合的需求、研发进展、Bug、发布和线上运行统计。 |

### P0 字段级 Schema

以下字段级 schema 是实现、API DTO、迁移规划和测试夹具的逻辑基线，不替代实际 migration。

#### requirements

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| brain_app_id | string | 是 | 关联业务大脑，例如 `rd_brain`。 |
| product_id | string | 是 | 关联产品。 |
| version_id | string | 否 | 关联 `planning` 或 `active` 产品迭代版本；新增需求可为空，排期后进入 `planned` 并允许生成 AI 任务。 |
| module_code | string | 否 | 关联产品模块。 |
| title | string | 是 | 非空，建议 1-120 字。 |
| description | text | 是 | 原始需求描述。 |
| status | enum | 是 | `draft`、`submitted`、`approved`、`planned`、`designing`、`ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released`、`accepted`、`rejected`、`deferred`、`cancelled`、`closed`。 |
| priority | enum/string | 否 | 业务优先级。 |
| source | enum/string | 是 | 需求来源：`business_department`、`product_planning`、`user_feedback`、`internal_research`、`other`。默认 `business_department`；用户反馈转需求固定为 `user_feedback`，迭代规划建议转需求固定为 `product_planning`。 |
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
| brain_app_id | string | 是 | 业务大脑归属，v1 默认 `rd_brain`，由需求归属继承。 |
| requirement_id | string | 否 | 来源需求，可为空以支持独立任务。 |
| task_type | enum | 是 | `product_detail_design`、`technical_solution`、`development_planning`、`code_review`、`automated_testing`、`release_readiness`、`post_release_analysis`。 |
| title | string | 是 | 非空。 |
| status | enum | 是 | `draft`、`running`、`waiting_more_info`、`waiting_review`、`writing_back`、`completed`、`failed`、`cancelled`。 |
| product_id | string | 是 | 产品归属。 |
| version_id | string | 否 | 任务创建时的迭代版本归属；结构表允许为空以兼容独立任务和历史数据，需求交付链路必须先排期到 `planning` 或 `active` 迭代版本。 |
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
| index_status | enum | 是 | `importing`、`pending_index`、`text_indexed`、`vector_indexed`、`indexed`、`index_failed`、`archived`；`indexed` 为历史兼容状态。 |
| index_error | text | 否 | 文本索引失败或兼容展示用错误摘要；Embedding 失败但文本索引成功时可同 `vector_index_error`。 |
| vector_index_error | text | 否 | 向量索引失败摘要；不阻断 `text_indexed` 检索。 |
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
| embedding | vector | 否 | pgvector，维度与 embedding 模型配置一致；`text_indexed` chunk 可为空。 |
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
| source_subject_type/source_subject_id | 来源主体，例如 requirement、ai_task、gitlab_mr_snapshot、code_review_report、human_review、bug、gitlab_daily_code_metric、jenkins_release、online_log_metric、user_usage_metric、user_feedback、iteration_plan_suggestion、knowledge_deposit、audit_event。 |
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

API envelope 的 `trace_id` 用于请求追踪，不作为当前审计事件字段持久化。主体级审计字段用于跨产品、需求、任务和知识中心追踪关键写操作。`/api/audit/events` 至少支持按 `ai_task_id`、`subject_type`、`subject_id`、`event_type`、`actor_id`、`created_from` 和 `created_to` 组合过滤；页面链路追踪应优先使用审计主体，缺少主体时才回退到关联 AI 任务。审计事件列表由独立 `audit` router 调用 `audit_events` service 完成 repository-first 查询、兼容内存过滤、排序、分页和 `query/performance` 观测元数据，不得反向调用 `main.py` 中的 legacy helper。

### 索引设计

| 表名 | 索引名 | 字段 | 类型 | 用途说明 |
|------|--------|------|------|----------|
| requirements | idx_requirements_status | status | 普通索引 | 需求列表状态过滤。 |
| requirements | idx_requirements_product_id | product_id | 普通索引 | 按产品查询需求。 |
| requirements | idx_requirements_created_at | created_at | 普通索引 | 按创建时间倒序查询。 |
| requirements | idx_requirements_source_created | source, created_at | 普通索引 | 按需求来源筛选并按创建时间排序。 |
| ai_tasks | idx_ai_tasks_status | status | 普通索引 | 任务列表状态过滤。 |
| ai_tasks | idx_ai_tasks_task_type | task_type | 普通索引 | 按 AI 任务类型筛选任务列表。 |
| ai_tasks | idx_ai_tasks_created_at_coalesced | COALESCE(created_at, updated_at) | 表达式索引 | 任务列表按创建时间范围筛选和倒序分页。 |
| ai_tasks | idx_ai_tasks_created_by | created_by | 普通索引 | 任务列表按创建人/负责人查询。 |
| ai_tasks | idx_ai_tasks_brain_app | brain_app_id | 普通索引 | 按业务大脑查询任务。 |
| graph_runs | idx_graph_runs_task | ai_task_id | 普通索引 | 查询任务运行记录。 |
| human_reviews | idx_human_reviews_task | ai_task_id | 普通索引 | 查询任务确认点。 |
| human_reviews | idx_human_reviews_status_task_created | status, ai_task_id, created_at | 组合索引 | 待确认列表 SQL 直查。 |
| knowledge_chunks | idx_knowledge_chunks_embedding | embedding | vector index | 向量相似度检索。 |
| mock_issues | uk_mock_issues_idempotency | idempotency_key | 唯一索引 | 防重复回写。 |
| knowledge_deposits | uk_knowledge_deposit_hash | ai_task_id, deposit_type, content_hash | 唯一索引 | 防重复沉淀。 |
| audit_events | idx_audit_events_ai_task_id | ai_task_id | 普通索引 | 按任务查询审计事件。 |
| audit_events | idx_audit_events_event_type | event_type | 普通索引 | 按事件类型排查。 |
| audit_events | idx_audit_events_created_at | created_at | 普通索引 | 按时间倒序查询。 |
| gitlab_daily_code_metrics | idx_gitlab_daily_metrics_product_date | product_id, metric_date | 普通索引 | 首页看板按产品查询提交与质量趋势。 |
| jenkins_release_records | idx_jenkins_release_product_time | product_id, deployed_at | 普通索引 | 查询产品发布历史。 |
| online_log_metrics | idx_online_log_product_window | product_id, environment, window_start | 普通索引 | 查询线上运行趋势。 |
| user_usage_metrics | idx_user_usage_product_window | product_id, module_code, feature_code, window_start | 普通索引 | 查询产品、模块和功能使用趋势。 |
| user_feedback | idx_user_feedback_product_status | product_id, status, created_at | 普通索引 | 查询用户反馈处理状态和趋势。 |
| collector_runs | idx_collector_runs_type_started | collector_type, started_at | 普通索引 | 查询某类采集器最近运行。 |
| collector_runs | idx_collector_runs_product_started | product_id, started_at | 普通索引 | 查询产品相关采集运行。 |
| collector_runs | idx_collector_runs_status | status, started_at | 普通索引 | 查询运行中或失败的采集记录。 |
| pending_attribution_items | idx_pending_attribution_status_created | status, created_at | 普通索引 | 查询待处理、已处理或已忽略队列项。 |
| pending_attribution_items | idx_pending_attribution_source_created | source_type, created_at | 普通索引 | 查询某类来源的待归属数据。 |
| pending_attribution_items | idx_pending_attribution_resolved_product | resolved_product_id, updated_at | 普通索引 | 查询已归属到某产品的处理结果。 |
| pending_attribution_items | idx_pending_attribution_collector_run | collector_run_id | 普通索引 | 从采集运行追踪其产生的待归属项。 |
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
| assistant_conversations | idx_assistant_conversations_user_updated | user_id, updated_at | 普通索引 | 查询当前用户最近助手会话。 |
| assistant_messages | idx_assistant_messages_conversation_created | conversation_id, created_at | 普通索引 | 按会话时间顺序读取助手消息。 |

### 数据迁移

首个初始化脚本位于 `apps/api/app/db/migrations/001_init.sql`，负责 pgvector 扩展和核心表初始化。后续迁移按模块追加，例如 `002_persistence_users.sql` 补齐用户表种子数据和历史 `app_state_snapshots` 快照表，`003_role_definitions.sql` 补齐角色字典，`004_knowledge_audit_persistence.sql` 让已有环境的 `audit_events.id` 支持字符串审计 ID 并补齐 `sequence`，`005_knowledge_vector_index.sql` 为 `knowledge_chunks.embedding` 增加 pgvector HNSW cosine 索引，`006_user_feedback.sql` 补齐用户反馈结构表，`007_iteration_planning.sql` 补齐迭代规划建议和确认结构表，`008_user_usage_metrics.sql` 补齐用户使用指标结构表，`009_devops_gitlab_metrics.sql` 补齐 GitLab 每日代码指标结构表，`010_devops_jenkins_releases.sql` 补齐 Jenkins 发布记录结构表，`011_ops_online_log_metrics.sql` 补齐线上运行日志指标结构表，`012_collector_runs.sql` 补齐采集运行记录结构表，`013_pending_attribution_items.sql` 补齐待归属数据队列结构表，`014_related_system_product_context.sql` 补齐相关系统产品归属列和产品状态查询索引，`015_lifecycle_dashboard_persistence.sql` 补齐生命周期边摘要、风险上下文字段和首页看板快照结构表，`016_brain_app_task_attribution.sql` 补齐需求与 AI 任务的默认 `rd_brain` 归属、`idx_ai_tasks_brain_app` 查询索引和当前 MVP 任务类型配置，`017_langgraph_runtime_metadata.sql` 补齐 Graph Run 的 `runtime` 与 `node_path` 元数据列，`018_standard_timestamps.sql` 补齐所有历史结构表的 `created_at` 与 `updated_at` 标准时间字段，`019_assistant_chat_history.sql` 补齐 AI 助手会话和消息结构表，`020_knowledge_text_index_fallback.sql` 补齐知识文档向量索引错误字段并将历史 `indexed` 状态升级为 `vector_indexed`，`021_model_gateway_embedding_capability.sql` 补齐模型网关 Embedding 连接模式、独立凭据和向量维度字段，`022_optional_requirement_version.sql` 将需求和 AI 任务版本字段改为可空，并把历史 `pending_approval` / `task_created` 需求状态迁移为 `submitted` / `designing`，`023_db_first_id_counters.sql` 新增 `id_counters` 作为 DB-first 迁移期的数据库发号表，`024_task_query_performance.sql` 补齐任务管理远程筛选分页和待确认直查所需索引，`030_requirement_source.sql` 补齐需求来源字段和来源/创建时间查询索引。当前业务大脑只读配置、产品、版本、模块、Git 资源、相关系统、需求、AI 任务、Review、Graph Run、Checkpoint、GitLab MR 快照、Code Review 报告、知识文档、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属队列、迭代规划建议/确认、生命周期上下文边、生命周期风险信号、首页看板快照、模拟 Issue 回写、模型网关配置、模型调用元数据、AI 助手会话和助手消息会同步到对应结构表，启动恢复只读取结构表，不再从 `app_state_snapshots` 恢复业务集合；外部线上日志自动采集器仍按后续切片接入。已有环境必须通过可重复执行的 SQL 迁移脚本升级，不得通过清空 PostgreSQL 数据卷绕过迁移问题；PostgreSQL 镜像升级必须保持和数据目录相同的主版本，例如现有 PG18 数据卷使用 PG18 + pgvector 镜像，不能直接切到 PG16；回滚脚本不得破坏生产数据。

`035_scheduled_ai_jobs.sql` 补齐 `ai_skills`、`ai_agents`、`scheduled_jobs` 和 `scheduled_job_runs` 结构表，包含运行状态、作业类型、执行模式、启停、due job、锁租约、产品归属、时间窗口、Agent/Skill 引用和配置快照 JSONB 字段；所有新增表仍必须包含 `created_at` 与 `updated_at` 标准字段，并通过 repository/source rows 读取，不得回退到 `app_state_snapshots`。

---

## API 设计

详见 [api.md](./api.md)。

### 接口清单

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 健康检查 | GET | /health | API 存活检查，并基于持久化默认模型网关或环境变量返回模型网关配置状态。 |
| 长期记忆状态 | GET | /api/long-memory/status | 查询 GBrain 长期记忆连接器配置状态和可用能力，不返回密钥。 |
| 业务大脑列表 | GET | /api/brain-apps | 查询可用业务大脑；列表和详情端点由 `app.api.routers.brain_apps` 单一路由承载，repository-first 读取逻辑由 `app.services.brain_apps` 维护。 |
| 产品列表 | GET | /api/products | 查询产品配置，支持服务端分页、排序和筛选；主表响应行包含当前版本与模块数聚合字段，前端无需额外拉取全量版本/模块列表拼装。 |
| 产品维护 | POST/PATCH/DELETE | /api/products, /api/products/{product_id} | 管理产品，产品编码唯一；删除前校验需求、AI 任务和 Bug 业务依赖，无业务依赖时级联清理版本、模块和 Git 资源配置。 |
| 迭代版本 | GET/POST/PATCH/DELETE | /api/products/{product_id}/versions, /api/product-versions/{version_id} | 管理产品迭代版本，前端主入口位于需求交付/迭代版本；同一产品内版本编码唯一，删除前校验需求、AI 任务和 Bug 依赖。 |
| 迭代版本代码分支 | GET/POST/PATCH/DELETE | /api/product-versions/{version_id}/branch-configs, /api/product-version-branch-configs/{branch_config_id} | 在迭代版本下维护版本级代码分支；同一版本可关联多个产品 Git 资源，同一仓库只能配置一条版本分支；仓库必须和版本属于同一产品。 |
| 产品模块 | GET/POST/PATCH/DELETE | /api/products/{product_id}/modules, /api/product-modules/{module_id} | 管理产品模块，同一产品内模块编码唯一，删除前校验需求、AI 任务和 Bug 依赖。 |
| 产品 Git 资源 | GET/POST/PATCH/DELETE | /api/products/{product_id}/git-repositories, /api/product-git-repositories/{repo_id} | 管理产品仓库资源。 |
| 相关系统 | GET/POST/PATCH/DELETE | /api/system/related-systems, /api/system/related-systems/{system_id} | 管理相关系统配置，可按 `product_id` 过滤并写入任务产品上下文。 |
| 模型网关配置 | GET/POST/PATCH/DELETE/POST(test) | /api/system/model-gateway-configs, /api/system/model-gateway-configs/test, /api/system/model-gateway-configs/{config_id} | 管理平台默认模型网关，并使用临时参数检测连接；端点由 `app.api.routers.model_gateway` 单一路由承载。 |
| 模型调用日志 | GET | /api/model-gateway/logs | 查询模型调用元数据，不返回完整 prompt、输出或密钥；端点由 `app.api.routers.model_gateway` 单一路由承载。 |
| AI 助手会话列表 | GET | /api/assistant/conversations | 返回当前登录用户最近助手会话。 |
| AI 助手会话消息 | GET | /api/assistant/conversations/{conversation_id}/messages | 返回当前登录用户指定会话消息，不允许跨用户读取。 |
| AI 助手聊天 | POST | /api/assistant/chat | 基于当前 AI Brain 系统上下文和模型网关 Chat 能力回答产品、迭代进度、任务、阻塞需求、待确认 Review、代码评审结论、Bug 分布、知识沉淀、Git 仓库和模型网关状态问题，并按用户保存会话历史。 |
| 需求列表 | GET | /api/requirements | 查询需求台账；端点由 `app.api.routers.requirements` 单一路由承载，列表优先使用 SQL read model 分页、筛选、排序和查询观测。 |
| 需求详情 | GET | /api/requirements/{id} | 查询单条需求详情和任务引用；端点由 `app.api.routers.requirements` 单一路由承载。 |
| 需求维护 | POST/PATCH/DELETE | /api/requirements, /api/requirements/{id} | 创建、更新待审批/已驳回需求，删除未生成任务的需求；端点由 `app.api.routers.requirements` 单一路由承载。 |
| 需求批量分配负责人 | POST | /api/requirements/batch-assign-owner | 为非关闭/非取消需求批量更新 `assignee`，逐条返回 updated/skipped 明细并记录批次级与逐需求审计；端点由 `app.api.routers.requirements` 单一路由承载。静态路径必须先于 `/api/requirements/{id}` 动态路由注册。 |
| 需求批量推进状态 | POST | /api/requirements/batch-advance-status | 按研发流程前进路径批量推进需求状态，逐条返回 updated/skipped 明细并记录批次级与逐需求审计；进入交付链路状态前要求需求已归属迭代版本，未排期项返回 skipped；端点由 `app.api.routers.requirements` 单一路由承载。静态路径必须先于 `/api/requirements/{id}` 动态路由注册。 |
| 迭代版本状态推进 | POST | /api/product-versions/{version_id}/advance-status | 预览并推进版本状态，按版本阶段同步可推进需求状态，阻塞项返回风险明细。 |
| 需求批量排期 | POST | /api/requirements/batch-schedule | 将同产品 `approved/planned` 需求批量归集到 `planning/active` 迭代版本；合法需求更新为 `planned`，不合规需求返回 skipped 明细；端点由 `app.api.routers.requirements` 单一路由承载。静态路径必须先于 `/api/requirements/{id}` 动态路由注册。 |
| 需求批量生成任务 | POST | /api/requirements/batch-generate-tasks | 将同产品 `planned` 需求批量生成 draft 产品详细设计任务；合法需求进入 `designing` 并追加 `task_ids`，不合规需求返回 skipped 明细并记录 `requirement.batch_tasks_generated`；端点由 `app.api.routers.requirements` 单一路由承载。静态路径必须先于 `/api/requirements/{id}` 动态路由注册。 |
| 需求审批 | POST | /api/requirements/{id}/approve, /api/requirements/{id}/reject | 审批通过或驳回需求；端点由 `app.api.routers.requirements` 单一路由承载。 |
| 需求关闭 | POST | /api/requirements/{id}/close | 关闭无需继续推进的需求；端点由 `app.api.routers.requirements` 单一路由承载。 |
| 生成 AI 任务 | POST | /api/requirements/{id}/generate-task | 需求排期到有效迭代版本后基于需求实体生成 AI 任务；端点由 `app.api.routers.requirements` 单一路由承载。 |
| 创建 AI 任务 | POST | /api/ai-tasks | 低层任务创建接口，前端默认通过需求实体生成；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 启动 AI 任务 | POST | /api/ai-tasks/{id}/start | 启动 LangGraph；`model_gateway_failed` 或 `code_review_executor_failed` 的失败任务可同 task_id 重试；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 任务列表 | GET | /api/ai-tasks | 查询任务列表；端点由 `app.api.routers.tasks` 单一路由承载，列表优先使用 SQL read model 分页、筛选、排序和查询观测。 |
| 任务详情 | GET | /api/ai-tasks/{id} | 查询任务状态、结果和确认点；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 补充信息 | POST | /api/ai-tasks/{id}/more-info | 提交补充信息并将任务回到 `draft`；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 取消任务 | POST | /api/ai-tasks/{id}/cancel | 取消任务并关闭待确认；端点由 `app.api.routers.tasks` 单一路由承载。 |
| Graph Run 列表 | GET | /api/graph-runs | 查询 AI 任务关联的 Graph 运行记录；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 待确认列表 | GET | /api/reviews/pending | 查询当前待确认项；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 确认详情 | GET | /api/reviews/{id} | 查询确认详情；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 确认处理 | POST | /api/reviews/{id}/approve | 采纳 AI 输出；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 修改后采纳 | POST | /api/reviews/{id}/edit-approve | 使用人工修改继续；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 驳回重跑 | POST | /api/reviews/{id}/reject | 标记为失败，等待人工重新启动；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 要求补充信息 | POST | /api/reviews/{id}/request-more-info | 将任务退回补充信息状态；端点由 `app.api.routers.tasks` 单一路由承载。 |
| 知识文档 | GET/POST/PATCH/DELETE | /api/knowledge/documents, /api/knowledge/documents/{document_id} | 查询、导入、更新和删除知识文档。 |
| 知识索引重试 | POST | /api/knowledge/documents/{document_id}/retry-index | 对 `index_failed` 重建索引，或对 `text_indexed` 补建向量索引。 |
| 知识搜索 | POST | /api/knowledge/search | 权限过滤后的混合检索。 |
| 知识沉淀 | GET/POST | /api/knowledge/deposits, /api/knowledge/deposits/{deposit_id}/approve, /api/knowledge/deposits/{deposit_id}/reject | 查询、采纳或驳回知识候选。 |
| Markdown 导出 | GET | /api/export/tasks/{task_id}/markdown | 导出已完成任务方案，权限与任务读取权限一致。 |
| 审计事件 | GET | /api/audit/events | 查询审计事件。 |
| GitLab 代码质量 | GET/POST | /api/devops/gitlab/daily-code-metrics | 登记或查询按产品归属的每日提交和代码质量。 |
| 研发运营指标列表 | GET | /api/devops/operational-metrics | 聚合 GitLab 指标、Jenkins 发布和线上日志，支持服务端分页、排序和筛选。 |
| GitLab MR 预览 | GET | /api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview | 读取 GitLab MR 标题、作者、分支、变更文件数、diff refs 和只读权限诊断；端点由 `app.api.routers.git_review` 单一路由承载。 |
| GitLab MR diff 快照 | POST | /api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot | 拉取 MR 元信息和 diff，生成 code_review 任务输入快照，并在响应中返回上一快照引用、diff 对比摘要和复用标记；端点由 `app.api.routers.git_review` 单一路由承载。 |
| GitHub PR 列表 | GET | /api/devops/github/pull-requests/{repository_id} | 使用产品 GitHub 凭据列出可访问 PR，支持 state 和 limit；端点由 `app.api.routers.git_review` 单一路由承载。 |
| GitHub PR 预览 | GET | /api/devops/github/pull-requests/{repository_id}/{pr_number}/preview | 读取 GitHub PR 标题、作者、分支、变更文件数、文件摘要和只读权限诊断；端点由 `app.api.routers.git_review` 单一路由承载。 |
| GitHub PR diff 快照 | POST | /api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot | 拉取 PR 元信息和文件摘要，生成 code_review 任务输入快照，并在响应中返回上一快照引用、diff 对比摘要和复用标记；端点由 `app.api.routers.git_review` 单一路由承载。 |
| Code Review 报告 | GET | /api/ai-tasks/{id}/code-review-report | 查询 GitLab MR / GitHub PR 代码 Review 报告、执行器信息、确认状态和只读 Review 结论回写模板。 |
| Jenkins 发布 | GET/POST | /api/devops/jenkins/releases | 登记或查询按产品和版本归属的发布记录。 |
| 线上运行日志 | GET/POST | /api/ops/online-log-metrics | 登记或查询按产品、模块、环境和时间窗口归属的线上运行日志指标。 |
| 采集运行记录 | GET/POST/PATCH | /api/collectors/runs, /api/collectors/runs/{run_id} | 历史兼容 API：查询、登记和结束 DevOps/洞察采集运行台账，不自动生成指标；当前前端不提供入口。 |
| AI 能力配置 | GET/POST/PATCH | /api/system/ai-skills, /api/system/ai-agents | 管理 Agent、Skill、默认模型网关、工具策略、Prompt 模板、输入/输出 Schema 和启停状态；配置变更必须审计，密钥不在配置中保存。 |
| 插件管理 | GET/POST/PATCH/POST(invoke/trial) | /api/system/plugins, /api/system/plugin-connections, /api/system/plugin-connections/{connection_id}/test, /api/system/plugin-system-variables, /api/system/plugin-actions, /api/system/plugin-actions/{action_id}/invoke, /api/system/plugin-actions/{action_id}/trial, /api/system/plugin-invocation-logs | 管理 HTTP/MCP HTTP 插件、三方系统连接、动作配置和调用日志；连接密钥脱敏，连接测试返回诊断步骤，动作支持请求预览和试运行，配置和调用必须审计。 |
| 定时系统作业 | GET/POST/PATCH/POST(run) | /api/system/scheduled-jobs, /api/system/scheduled-jobs/{job_id}, /api/system/scheduled-jobs/{job_id}/run | 管理采集、AI 分析、插件动作调用、迭代建议、看板刷新等作业计划；支持手动触发、启停、重试策略、插件动作和 AI Agent/Skill 装配。 |
| 定时作业运行 | GET/POST(cancel) | /api/system/scheduled-job-runs, /api/system/scheduled-job-runs/{run_id}/cancel | 查询定时作业运行实例、AI 配置快照、collector run 关联、结果摘要和失败原因；运行中作业可由管理员取消。 |
| 待归属数据队列 | GET/POST/POST | /api/attribution/pending-items, /api/attribution/pending-items/{item_id}/resolve | 历史兼容 API：查询、登记、归属或忽略无法映射产品/模块/需求的数据，不自动生成业务指标；当前前端不提供入口。 |
| Bug 管理 | GET/POST/PATCH/DELETE | /api/bugs, /api/bugs/batch-update, /api/bugs/{bug_id} | 查询、登记、批量处理、更新和删除 Bug；端点由 `app.api.routers.bugs` 单一路由承载，列表优先使用 SQL read model 分页、筛选、排序和查询观测。 |
| 需求全链路 | GET | /api/requirements/{requirement_id}/full-chain | 需求级聚合时间线，返回需求到发布和知识沉淀的关联主体。 |
| 全流程感知 | GET | /api/lifecycle/context | 查询研发上下文关系、上下游影响和风险信号。 |
| 首页看板 | GET | /api/dashboard/it-team | 查询 IT 团队首页指标。 |
| 用户洞察列表 | GET | /api/insights/items | 聚合用户使用、用户反馈和迭代建议，支持服务端分页、排序和筛选。 |
| 用户反馈转需求 | POST | /api/insights/user-feedback/{feedback_id}/convert-requirement | 将已登记用户反馈转为正式需求，需求来源为 `user_feedback`，并同步反馈归属产品、关联需求和 `linked` 状态。 |
| 用户使用指标 | GET/POST | /api/insights/usage-metrics | 查询或登记产品、模块、功能和用户群体维度的真实使用趋势。 |
| 用户反馈 | GET/POST/PATCH | /api/insights/user-feedback, /api/insights/user-feedback/{feedback_id} | 查询、登记和更新用户反馈。 |
| 迭代规划建议 | GET/POST | /api/planning/iteration-suggestions | 查询或生成 AI 迭代规划建议。 |
| 迭代规划确认 | POST | /api/planning/iteration-suggestions/{suggestion_id}/decide | 产品负责人确认、修改后采纳或驳回迭代规划建议。 |

---

## 实现细节

### 模块 A: graph_runtime

**职责**: 管理研发大脑 Graph 的生命周期。

**核心逻辑**:
```text
MVP 当前 LangGraph 节点路径:
retrieve_context
→ generate_task_output
→ interrupt_for_human_review

完整目标路径:
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

**核心规则**:
- 知识文档创建、内容更新、权限更新和沉淀采纳会先重建文本 chunk；如 Embedding 网关的 OpenAI-compatible `/embeddings` 可用，则生成 `knowledge_chunks.embedding` 并进入 `vector_indexed`。模型网关配置通过 `embedding_connection_mode=disabled|reuse_chat|custom` 明确 Chat 与 Embedding 能力边界，Chat-only 配置不得阻断 AI 助手或任务生成。
- Embedding 维度必须等于 `VECTOR_DIMENSION`；provider 失败或维度异常时文档保持 `text_indexed`，保留 `vector_index_error`，关键词检索仍可用；只有无法切片等基础索引失败才进入 `index_failed`。
- 检索必须先过滤用户无权读取的文档和 chunk，再对有 embedding 且 `embedding_config_id`、`embedding_model`、`embedding_dimension` 兼容的 chunk 使用 cosine 相似度排序；没有可读兼容向量 chunk 时不得额外混用旧模型向量，直接关键词检索。返回结果包含 `retrieval_mode`，向量命中包含 `score`，关键词命中 `score=null`。
- 模型调用日志以 `purpose=knowledge_embedding` 记录 provider、model、tokens、latency 和状态，不记录完整知识正文或查询文本。

### 模块 B2: long_memory

**职责**: 对接 GBrain 作为长期记忆和公司大脑层，提供跨任务、跨来源的混合检索、答案合成和知识图谱查询能力。

**边界规则**:
- v1 业务知识文档、权限、chunk 和沉淀审核仍以本项目 `knowledge` 模块和 PostgreSQL 为准。
- GBrain 不替代产品、需求、AI 任务、人工确认和审计等业务数据库。
- MVP-A 不阻塞于 GBrain 部署；未配置 GBrain 时 `GET /api/long-memory/status` 返回明确的 `not_configured` 能力状态，Graph 继续使用 PostgreSQL + pgvector 知识检索。
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

**职责**: 采集和聚合本地 GitLab、Jenkins 和线上运行日志数据，按产品、版本、模块和时间窗口形成研发运营指标，并记录每次采集或导入运行。

**核心规则**:
- GitLab 数据按 `product_git_repositories` 归属到产品，统计每日提交、人员提交情况、Merge Request、代码变更量和代码质量审核摘要。
- Jenkins 发布数据按产品和版本归属，记录 job、build_id、部署环境、发布版本、触发人、耗时、状态和失败原因。
- 线上运行日志按产品、模块、环境和时间窗口聚合，记录错误率、接口延迟、核心业务事件数量、Top Errors 和异常趋势；当前实现允许产品负责人、研发负责人或管理员手工登记或导入真实聚合指标，写入 `online_log_metrics` 并记录审计。
- 采集运行记录写入 `collector_runs`，支持 `running / succeeded / failed / cancelled`；运行记录只描述采集尝试，不自动写入 `gitlab_daily_code_metrics`、`jenkins_release_records`、`online_log_metrics`、`user_usage_metrics`、`user_feedback` 或 `iteration_plan_suggestions`。
- 无法映射产品归属的数据写入 `pending_attribution_items`，支持 `pending / resolved / ignored`，处理结果不进入产品级看板统计，也不自动写入指标或反馈主体。

### 模块 B3.S: scheduled_jobs

**职责**: 管理系统后台定时作业，用统一调度、锁租约、运行实例、采集台账和审计机制触发研发运营采集、用户洞察采集、AI 日志分析、AI 迭代建议、看板刷新和生命周期风险刷新。

**核心规则**:
- `scheduled_jobs` 是调度定义，`scheduled_job_runs` 是每次执行实例，`collector_runs` 是采集/导入台账；定时作业不得直接绕过现有业务 service 写表。
- `job_type` 首批支持 `gitlab_daily_code_metric_collect`、`jenkins_release_collect`、`online_log_metric_collect`、`user_usage_metric_collect`、`user_feedback_collect`、`user_feedback_insight_extract`、`online_log_ai_analysis`、`iteration_plan_suggestion_generate`、`dashboard_snapshot_refresh`、`lifecycle_context_refresh`、`plugin_action_invoke` 和 `pending_attribution_retry`。
- `execution_mode` 分为 `deterministic`、`ai_assisted`、`ai_generated`：确定性作业可写真实指标；AI 辅助作业可写摘要、风险信号或看板派生结果；AI 生成作业只能写候选建议或待确认结果。
- 调度 worker 每分钟或按配置 tick，查询 `enabled=true AND next_run_at <= now()` 的作业，并通过数据库行级更新设置 `lease_owner` / `lease_expires_at` 抢占执行权；锁过期后其他 worker 可接管，已创建的运行实例不得被覆盖。
- 每次运行必须冻结 `config_snapshot`；AI 作业还必须冻结 Agent、Skill、模型网关、Prompt 模板、输出 Schema、工具策略和上下文范围快照，避免配置修改影响历史可追溯性。
- `user_feedback_insight_extract` 必须绑定插件动作，默认从插件响应 `$.insights` 读取 AI 提炼后的洞察项，通过用户反馈 service 写入用户洞察表；`records_imported` 记录实际写入洞察数，源表行数只进入 `result_summary.source_row_count`。
- 运行状态为 `queued / running / succeeded / failed / skipped / cancelled`；失败可按 `max_retry_count` 生成新的运行实例，不能把失败实例改写成成功历史。
- `scheduled_job_runs.collector_run_id` 关联 `collector_runs`，用于继续兼容现有采集台账、审计和运行排查；AI 纯分析类作业也应写 collector run 或等价审计摘要，以便统一追踪。

**组件边界**:
| 组件 | 职责 |
|------|------|
| `ScheduledJobScheduler` | 计算 due jobs、抢占锁、创建运行实例、计算 `next_run_at`。 |
| `ScheduledJobRunner` | 装配运行上下文、创建/更新 collector run、调用 handler、处理重试和超时。 |
| `ScheduledJobHandler` | 每类 job 的业务执行器，复用现有 DevOps、用户洞察、迭代规划、看板和生命周期 service。 |
| `AIExecutionConfigResolver` | 解析 Agent、Skill、模型网关和作业覆盖项，生成不可变运行快照。 |
| `SkillOrchestrator` | 合并 agent system prompt、skill prompt、工具结果和 expected output schema，调用模型网关前做脱敏和限长，输出后做 schema 校验。 |

**安全与副作用**:
- Agent/Skill 不得保存密钥；外部系统访问通过产品 Git 资源、相关系统或服务端凭据引用完成，默认只读。
- AI 作业不得自动创建正式需求、关闭 Bug、变更发布状态、远端写回 GitLab/GitHub/Jenkins 或修改产品路线图。
- 低置信度或无法归属的数据进入 `pending_attribution_items`，不进入产品级看板结论。
- 所有配置变更、手动触发、运行开始、运行成功、运行失败、取消和重试必须写入 `audit_events`。

### 模块 B3.A: ai_capabilities

**职责**: 维护 AI Agent、Skill 和默认装配策略，为 AI 任务执行器和定时 AI 作业提供统一能力配置。

**核心规则**:
- Skill 表示能力包，包含输入/输出 schema、prompt_template、allowed_tools、required_context、risk_level、requires_human_review、版本和启停状态；第一阶段支持表单 Skill 和 zip 文件包 Skill 两种来源。
- Skill 文件包通过 `POST /api/system/ai-skills/upload` 上传，HTTP body 为 `application/zip`，query 中传 `code/name/version/status/risk_level/requires_human_review`；包内必须包含 `skill.yaml` 或 `SKILL.md`，服务端只允许 `.md/.txt/.yaml/.yml/.json` 文件，禁止路径穿越、绝对路径和超限文件。
- 上传后的 Skill 文件保存到服务端本地 Skill 存储目录，数据库 `ai_skills` 保存 `source_type`、`package_uri`、`package_checksum`、`package_entry`、`package_files`、`package_size_bytes` 和 `manifest`；运行时按 URI 读取本地文件并写入 `resolved_skill_snapshots.package_snapshot`，历史解释以运行快照为准。
- Agent 表示执行角色，包含所属业务大脑、默认模型网关、system_prompt、默认 Skill、执行策略、工具策略和启停状态；第一阶段 Agent 只通过页面表单维护，不支持 Agent 文件包上传。
- 定时作业、AI 任务类型和后续业务大脑配置均只引用已启用 Agent/Skill；运行时必须解析成快照，不直接读取可变配置作为历史解释依据。
- 高风险 Skill 必须 `requires_human_review=true` 或只写候选结果；正式业务状态变更必须走现有人审或决策流。
- 管理员可以维护 Agent/Skill；产品负责人和研发负责人只能在业务允许范围内选择已启用配置，不能修改系统提示词、工具权限或模型网关密钥。

### 模块 B3.0: git_review

**职责**: 支撑 v1 MVP GitLab MR / GitHub PR 代码 Review 闭环，读取 MR/PR 元信息和 diff 摘要，生成不可变输入快照，并归档经人工确认的 Review 报告。

Git Review API 入口已收口到独立 `app.api.routers.git_review`：GitLab MR 预览/快照、GitHub PR 列表/预览/快照保持原权限、只读远端访问、handler 级审计写入、DB-first source rows 恢复和 diff 超限失败语义；底层 provider helper、diff 摘要和快照创建逻辑仍作为后续 service 深拆对象保留兼容边界。

**核心规则**:
- 只能读取产品已绑定且当前用户有权限的 GitLab 项目/MR 或 GitHub 仓库/PR。
- MR/PR 快照至少保存 provider、project_id 或 project_path、mr_iid/PR number、标题、作者、source/target branch、commit sha 或 diff refs、变更文件摘要、diff 内容或存储引用、Web URL 和快照时间。
- MR/PR 快照一经生成不得被远端后续变更静默覆盖；重新 Review 必须重新拉取并记录新的运行或快照。
- 同一 repository_id 和 snapshot_hash 不应重复入库；重复拉取相同 diff 时可返回已有 snapshot_id，并写入可追踪审计事件。
- v1 MVP 不向 GitLab/GitHub 回写评论、审批状态、request changes、合并状态或分支变更。
- GitLab/GitHub 仓库未绑定、MR/PR 不存在、权限不足、diff 过大、API 超时或限流时，任务进入 `failed` 或 `waiting_more_info` 并保留可操作错误原因。

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
| 适配器 | 默认使用 `claude_code_skill`，执行器名称为 `code-review`；运行时通过 `CODE_REVIEW_EXECUTOR_COMMAND` 配置命令，命令从 stdin 读取输入 JSON、向 stdout 写出报告 JSON。显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 时复用模型网关适配器；当默认外部命令为空且已有 active/default 或环境模型网关时，本地联调可自动改用 `model_gateway` 适配器。 |
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
- Bug 来源为 `ai_auto_test | ai_post_release | manual_test`。
- Bug 必须归属产品，可选关联版本、模块、需求、AI 任务、GitLab 提交、Jenkins 发布或线上日志事件。
- 重复 Bug 通过 `duplicate_of_bug_id` 关联到主 Bug，不重复进入修复队列。
- AI 自动测试登记但缺少复现信息时应保留待确认标记，等待测试负责人补充。
- Bug 管理 API 入口已收口到独立 `app.api.routers.bugs`，保持原登记、批量处理、状态机校验、DB-first 写入、SQL read model 列表和审计语义；生命周期枚举、初始状态和上下文校验由 `app.services.bug_lifecycle` 维护。
- 当前 v1.1 基础实现使用 `product_owner`、`rd_owner`、`admin` 写权限完成登记和状态更新；RBAC 目标态由 `tester` 承接授权范围内的人工测试 Bug 登记和修复验证，由 `test_owner` 承接自动化测试确认和质量门禁。

### 模块 B5: lifecycle_context

**职责**: 建立软件研发全流程上下文图谱，串联需求、设计、方案、代码、Review、测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件，提供上游依据、下游影响、风险信号和下一步建议。

**核心规则**:
- 所有关系边必须记录来源主体、目标主体、关系类型、产品归属、来源模块和观测时间。
- 自动归因关系必须记录置信度，低置信度关系进入待确认或待归属状态。
- 风险信号必须保留来源主体和影响摘要，不得只在看板中展示无法追溯的聚合数字。
- 当前实现会在 PostgreSQL 运行时读取 repository source rows，再把 `/api/lifecycle/context` 计算出的上下游关系边和风险信号同步到 `lifecycle_context_edges` 与 `lifecycle_risk_signals`；API 响应仍返回当前查询范围内的真实关系和真实空状态。
- MVP 查询必须支持从 `product`、`requirement`、`ai_task`、`human_review`、`code_review_report`、`gitlab_mr_snapshot`、`mock_issue`、`knowledge_deposit`、`audit_event` 和 `bug` 解析到对应需求或任务链路；审计主体无法解析时返回空关系或明确错误，不得退化为全量任务。
- 后续阶段查询扩展到发布、提交、自动化测试、线上日志、用户反馈、用户使用指标或迭代规划建议等任一主体向上游和下游追溯。

### 模块 B6: dashboard

**职责**: 为首页 IT 团队看板提供按产品聚合的需求、研发进展、Bug、线上系统健康、核心业务运行、用户使用、用户反馈、AI 迭代规划建议摘要和发布状态统计。

**核心规则**:
- 看板默认按产品聚合，支持按时间窗口、环境、产品和模块筛选。
- 看板指标来自需求、AI 任务、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀、审计事件和 lifecycle_context 风险信号。
- `/api/dashboard/it-team` 由独立 `app.api.routers.dashboard` 提供，router 只负责权限、request store、缓存和响应封装入口；当前实现会在 PostgreSQL 运行时直接读取 repository source rows，指标计算由 `app.services.dashboard_metrics` 按产品、权限和时间窗口组装，并通过单条 repository 写入把产品与时间窗口聚合结果同步到 `dashboard_metric_snapshots`，用于后续首页读取、运营复核和趋势分析。
- 看板可以使用短 TTL 只读缓存降低重复查询压力，默认 TTL 由 `DASHBOARD_CACHE_TTL_SECONDS` 控制；`refresh=true` 必须清除当前查询维度缓存并重新读取 source rows。响应 `metadata.dashboard_cache` 回显缓存启用、命中、生成时间、年龄、剩余 TTL、耗时和慢查询阈值；超过 `DASHBOARD_SLOW_THRESHOLD_MS` 时记录 `slow_dashboard_query`。
- 首页只展示聚合和风险摘要，明细下钻到对应主体页面。

### 模块 C: model_gateway

**职责**: 统一模型调用入口，支持聊天和 embedding。

**核心规则**:
- MVP 仅支持 `openai_compatible` provider，配置入口必须拒绝目录外 provider。
- 模型网关配置、连接测试和日志查询端点由 `app.api.routers.model_gateway` 承载；配置脱敏、Chat/Embedding 连接测试、默认配置选择、Embedding runtime config、URL 归一化和响应解析由 `app.services.model_gateway` 维护，`main.py` 只在 AI 任务/知识索引运行时复用 service helper。
- 配置测试接口必须只使用临时参数调用 `/chat/completions` 和/或 `/embeddings`；支持仅测试 Chat，未测能力必须返回 `skipped`，不得持久化配置、密钥或模型调用日志，响应和审计只保留脱敏状态。
- 结构化输出必须要求 JSON 并做 schema 校验。
- 调用前进行基础敏感信息过滤。
- 日志记录 provider、model、purpose、tokens、latency、status、error，不默认记录完整 prompt。

---

## 状态管理

**状态结构**:
```text
Requirement: draft | submitted | approved | planned | designing | ready_for_dev | developing | code_reviewing | testing | ready_for_release | released | accepted | rejected | deferred | cancelled | closed
Product: active | inactive
Product version: planning | active | testing | released | archived
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
draft → submitted → approved → planned → designing → ready_for_dev
ready_for_dev → developing → code_reviewing → testing → ready_for_release → released → accepted
submitted → rejected → closed
approved/planned/交付中状态 → closed（无未完成任务时）
planned/交付中状态 → 交付中状态（继续创建满足前置依赖的关联任务）

AI task:
draft → running → waiting_more_info → draft → running
running → waiting_review → running
running → writing_back → completed
running/waiting_* → failed/cancelled

AI task type:
product_detail_design | technical_solution | development_planning | code_review | automated_testing | release_readiness | post_release_analysis

Knowledge document:
importing → pending_index → indexed
importing/pending_index/indexed → index_failed
index_failed → indexed（重试成功）或 index_failed（重试失败并更新 index_error）
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

#### Product Version

| 当前状态 | 动作 | 目标状态 | 角色 | 幂等/冲突规则 | 审计事件 |
|----------|------|----------|------|----------------|----------|
| planning | advance_status | active | 产品负责人/研发负责人 | 必须先生成影响预览；`approved/planned` 需求自动推进到 `ready_for_dev`，直接 PATCH 修改状态返回 `PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED`。 | product_version.status_advanced / requirement.updated |
| active | advance_status | testing | 产品负责人/研发负责人 | `approved/planned/ready_for_dev/designing/developing/code_reviewing` 等已进入交付链路的版本内需求自动推进到 `testing`；`draft/submitted` 等未完成审批入池状态进入阻塞明细，非强制推进返回 `PRODUCT_VERSION_STATUS_BLOCKED`，强制推进保留阻塞需求原状态并记录风险。 | product_version.status_advanced / requirement.updated |
| testing | advance_status | released | 产品负责人/研发负责人 | `testing/ready_for_release` 需求自动推进到 `released`；仍处于设计、开发、评审等未完成状态的需求必须先延期、取消、关闭或验收处理，否则阻止发布，`force=true` 不绕过发布阻塞。 | product_version.status_advanced / requirement.updated |
| released | archive | archived | 产品负责人/管理员 | 归档仅作为历史管理动作，不作为主交付状态；已发布或已终止需求保持不变，未完成需求作为风险项；归档后不可用于排期或新任务。 | product_version.status_advanced |

#### Requirement

| 当前状态 | 动作 | 目标状态 | 角色 | 幂等/冲突规则 | 审计事件 |
|----------|------|----------|------|----------------|----------|
| draft | submit | submitted | rd_owner | 重复提交保持 `submitted` 或返回状态错误。 | requirement.submitted |
| submitted | approve | approved / planned | 产品负责人/审批人 | 未选择迭代版本时进入 `approved` 需求池；已选择有效迭代版本时进入 `planned`。已审批后重复 approve 返回状态错误。 | requirement.approved |
| submitted | reject | rejected | 产品负责人/审批人 | 必须提供 rejection_reason。 | requirement.rejected |
| approved | schedule_iteration | planned | 产品负责人/研发负责人 | 必须绑定同产品 `planning/active` 迭代版本；清空版本则回到 `approved` 需求池。 | requirement.updated |
| draft / submitted / approved / planned / 交付中状态 / rejected / deferred / accepted | batch_assign_owner | 原状态不变 | 产品负责人/研发负责人 | 非关闭、非取消需求允许批量更新 `assignee`；缺失、重复、已关闭或已取消需求进入 skipped 明细。 | requirement.batch_owner_assigned / requirement.updated |
| approved / planned / ready_for_dev / designing / developing / code_reviewing / testing / ready_for_release / released | batch_advance_status | 按目标状态 | 产品负责人/研发负责人 | 只能按研发流程向前推进到允许目标；推进到交付链路状态时必须已归属迭代版本；终态、重复、缺失、未排期或不符合路径需求进入 skipped 明细，不回滚合法项。 | requirement.batch_status_advanced / requirement.updated |
| approved / planned | batch_schedule_iteration | planned | 产品负责人/研发负责人 | 批量请求必须指定同产品 `planning/active` 迭代版本；只更新 `approved/planned` 需求，跨产品、缺失或已进入交付阶段的需求进入 skipped 明细。 | requirement.batch_scheduled / requirement.updated |
| approved / planned | version_advanced_to_active | ready_for_dev | 产品负责人/研发负责人 | 由迭代版本从 `planning` 推进到 `active` 触发；已经更靠后的需求不回退。 | product_version.status_advanced / requirement.updated |
| approved / planned / ready_for_dev / designing / developing / code_reviewing | version_advanced_to_testing | testing | 产品负责人/研发负责人 | 由迭代版本从 `active` 推进到 `testing` 触发；版本内已进入交付链路的需求统一同步到测试中，未完成审批入池的需求进入阻塞/风险明细。 | product_version.status_advanced / requirement.updated |
| testing / ready_for_release | version_advanced_to_released | released | 产品负责人/研发负责人 | 由迭代版本从 `testing` 推进到 `released` 触发；未完成需求阻止发布。 | product_version.status_advanced / requirement.updated |
| planned | create_product_detail_design | designing | rd_owner | 只有已排期需求可以生成产品详细设计任务；每个任务必须保存独立快照。 | ai_task.created |
| designing | product_detail_design_confirmed / create_technical_solution | ready_for_dev | Reviewer / rd_owner | 产品详细设计确认后可创建技术方案；历史 `task_created` 兼容映射为 `designing`。 | review.submitted / ai_task.created |
| ready_for_dev | create_development_planning | developing | rd_owner | 必须存在同需求、同产品版本下已确认技术方案。 | ai_task.created |
| developing | create_code_review | code_reviewing | rd_owner/Reviewer | 必须存在同需求、同产品版本下 PR/MR diff 快照。 | ai_task.created |
| code_reviewing | code_review_confirmed / create_automated_testing | testing | Reviewer / rd_owner | code_review 报告确认后进入测试阶段。 | review.submitted / ai_task.created |
| testing | automated_testing_confirmed | ready_for_release | Reviewer | 自动化测试确认后可生成 Bug，并进入待发布。 | review.submitted |
| ready_for_release | release_readiness_confirmed | released | Reviewer | 发布评估确认后进入已发布。 | review.submitted |
| released | post_release_analysis_confirmed | accepted | Reviewer | 上线后分析确认后进入验收完成。 | review.submitted |
| approved/planned/交付中状态/rejected | close | closed | rd_owner | 未完成任务存在时不允许关闭或需二次确认。 | requirement.closed |

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
| importing | import_complete | pending_index | knowledge_owner/rd_owner/system | 导入失败进入 index_failed 并保存错误。 | knowledge.imported |
| pending_index | index_text | text_indexed | system | 文本切片成功即可进入；Embedding 不可用时保存 vector_index_error。 | knowledge.indexed |
| text_indexed | build_vector | vector_indexed/text_indexed | knowledge_owner/rd_owner/system | 可重复补向量；失败时继续保留文本索引。 | knowledge_document.index_retried |
| pending_index | index_vector | vector_indexed | system | Embedding 成功时写入 chunk embedding。 | knowledge.indexed |
| pending_index | index_failed | index_failed | system | 仅文本切片等基础索引失败进入，保存 index_error。 | knowledge.index_failed |
| index_failed | retry_index | text_indexed/vector_indexed/index_failed | knowledge_owner/rd_owner | 重试前清理旧 chunk；文本成功即可检索，向量成功后升级。 | knowledge_document.index_retried |
| text_indexed/vector_indexed/indexed | archive | archived | knowledge_owner/rd_owner | archived 文档不参与检索。 | knowledge.archived |

#### GitLab MR Snapshot and Code Review Report

| 当前状态 | 动作 | 目标状态 | 角色 | 幂等/冲突规则 | 审计事件 |
|----------|------|----------|------|----------------|----------|
| no_snapshot | preview_mr | previewed | Reviewer | 只读，不保存完整 diff。 | gitlab_mr.previewed |
| previewed | create_snapshot | snapshotted | Reviewer | 每次快照生成不可变 snapshot_hash。 | gitlab_mr.snapshotted |
| previewed | create_snapshot_too_large | failed | Reviewer | 不创建快照，记录 diff_size_bytes、diff_limit_bytes、changed_file_count、changed_file_limit、file_diff_line_count 和 file_diff_line_limit。 | gitlab_mr.snapshot_failed |
| snapshotted | create_code_review_task | report_pending | Reviewer | code_review 任务只引用已有快照。 | ai_task.created |
| report_pending | executor_success | pending_human_review | system | 输出必须通过 schema 校验。 | code_review.generated |
| report_pending | executor_failed | failed | system | 记录 executor 错误和 retryable。 | code_review.executor_failed |
| pending_human_review | confirm_report | confirmed | Reviewer | 确认后只归档 AI Brain 内部报告，不回写 GitLab/GitHub。 | code_review.confirmed |

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
→ 按 task_type 生成详细设计、技术方案、开发计划、GitLab MR / GitHub PR Review 报告、测试分析、发布评估或上线后分析
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
- 覆盖状态机、角色目录、权限判断、响应 envelope、幂等 key 生成、知识切片、模型 gateway schema 校验、GitLab MR / GitHub PR 输入校验、diff 大小限制、Review 报告 schema 校验、凭据掩码和迭代规划建议排序规则。
- 目标覆盖率: 80%。

### 集成测试
- 覆盖 FastAPI 路由、PostgreSQL 迁移、角色字典、pgvector 检索、Redis 依赖、人工确认恢复流程、GitLab MR / GitHub PR 预览与快照、code_review 任务创建、code-review 执行器调用、报告归档、用户洞察聚合和迭代规划确认流程。

### E2E 测试
- v1 MVP 覆盖“产品配置 → GitLab/GitHub 代码库绑定 → 新增需求 → 审批通过 → 生成产品详细设计任务 → 人工确认 → 技术方案任务 → 选择 MR/PR → 拉取 diff 快照 → 生成 code_review 报告 → 人工确认并内部归档 → 知识沉淀审核 → 审计可查”的黄金路径。
- v1.2 扩展覆盖“用户洞察采集 → AI 迭代规划建议 → 产品负责人确认 → 转正式需求”的产品迭代路径。
- 自动化测试、发布评估和上线后分析按后续阶段补充 E2E。

### 提交前真实网页界面验证门禁
- 凡修改 `apps/web`、前端路由/菜单、页面可见文案、交互流程、API 响应字段映射、查询聚合或会影响页面展示的后端接口，提交代码前必须在真实运行的 Web 页面完成界面验证，不能只依赖单元测试、接口测试或代码审查结论。
- 验证环境应使用当前本地或测试环境真实服务：前端访问实际 `http://127.0.0.1:5173` 或目标部署地址，API 使用 PostgreSQL 运行时；必要时重启前端服务并清理过期 Umi/MFSU 缓存，避免旧 bundle 或旧端口造成误判。
- 验证内容至少包括：目标 URL 和页面标题正确、页面不是空白壳、无框架错误覆盖层、控制台无本次变更引入的错误、目标菜单/按钮/表格/弹窗或主流程可见且状态符合预期、旧文案或旧交互不再出现。
- 涉及写操作的页面必须实际操作到确认后的可观察状态，并校验 API 数据刷新、错误提示、权限边界或审计入口；涉及只读页面时至少验证筛选、真实空状态或关键列表字段。
- 提交前记录验证证据：访问 URL、登录角色、验证页面/交互、通过结果、相关命令或浏览器检查结论。实际网页验证未通过时不得提交代码。

### 测试用例

测试用例数量和优先级分布以 [test-case.md](./test-case.md) 为准，技术规格不重复维护统计数字，避免清单和规格漂移。

---

## 性能考量

| 指标 | 目标 | 实现方式 |
|------|------|----------|
| 常规 API 响应 | P95 < 500ms | 分页、索引、避免同步模型调用阻塞。 |
| 核心管理主列表 | 需求/任务/Bug P95 < 300ms；用户洞察 P95 < 400ms；研发运营 P95 < 500ms | `query/performance` 观测元数据返回 `p95_target_ms`，慢于目标时 `slow=true` 并记录 `slow_list_query`。 |
| 知识检索 | P95 < 1s | top_k 限制、向量索引、权限过滤下推。 |
| AI 工作流 | 长任务异步 | Graph run 状态持久化，前端轮询或后续 SSE。 |
| 审计查询 | P95 < 500ms | ai_task_id、event_type、created_at 索引。 |
| 首页看板 | P95 < 800ms | 读取聚合快照，避免实时跨域聚合。 |
| 用户洞察查询 | P95 < 800ms | 使用 SQL read model、产品/模块/功能/时间窗口索引、更新时间排序索引和聚合快照。 |
| 迭代规划生成 | 异步任务 | 证据聚合与模型调用异步执行，前端查询建议状态。 |

**性能优化点**:
- 对任务列表、审计列表、知识检索、研发运营指标、用户洞察和迭代规划建议列表使用分页和 top_k 限制；用户洞察和研发运营页面主列表必须使用统一聚合接口进行服务端分页、排序和筛选。
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
| Git 凭据泄漏 | 产品 Git 资源只保存凭据引用或本地联调 token，API 响应只返回是否已配置凭据，不向 code-review 执行器传递 token。 |
| Git 回写副作用 | v1 MVP code_review 只归档 AI Brain 内部报告，不调用 GitLab/GitHub 评论、审批、request changes、合并或分支变更 API。 |
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
| MR/PR diff 过大或拉取失败 | code_review 任务无法生成报告 | 设置 diff 大小限制和可操作错误提示，允许拆分变更或重试，不静默截断。 |
| code-review 执行器不可用 | Review 报告生成失败 | 记录执行器错误、trace_id 和 retryable 状态，支持重跑或切换执行器。 |

---

## 关联文档

- PRD: [01-prd/enterprise-ai-brain/prd.md](../../01-prd/enterprise-ai-brain/prd.md)
- API: [api.md](./api.md)
- 测试用例: [test-case.md](./test-case.md)
- 整体方案评审与业务流程: [03-guides/ai-development-workflow.md](../../03-guides/ai-development-workflow.md)

---
最后更新: 2026-06-05
