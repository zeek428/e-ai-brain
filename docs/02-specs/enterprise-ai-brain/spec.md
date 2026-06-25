# 企业 AI 大脑平台技术规格

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.568 |
| 适用系统版本 | ≥ v1.0.0 |
| 文档状态 | Approved |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.1.568 | 2026-06-25 | 产品配置上下文需求/审计 helper DB-first fallback 写入收口：需求单记录 fallback 不再直接写 `current_store.requirements`，审计 helper 不再直接调用 `current_store.audit()`；统一通过需求集合 helper 和审计方法引用/事件列表 helper 操作测试集合，PostgreSQL 运行态继续由 repository 单记录写入和调用方事务提交审计 | Codex |
| v1.1.567 | 2026-06-25 | 用户反馈 DB-first fallback 写入收口：反馈创建、编辑和转需求不再直接写 `current_store.user_feedback` / `current_store.requirements`；反馈单记录通过 `save_user_feedback_record` 写入 repository 或 MemoryStore 测试集合，转需求通过 `save_user_feedback_requirement_conversion` 同步提交需求、反馈 linked 状态和审计事件 | Codex |
| v1.1.566 | 2026-06-25 | 用户洞察审计 helper DB-first fallback 收口：`record_audit_event` 在轻量上下文无 `audit()` 方法时不再直接 append `current_store.audit_events`，统一通过审计事件列表 helper 写入测试集合；普通 MemoryStore 继续走 `audit()`，repository 运行态审计事件继续由对应业务写入 helper 携带提交 | Codex |
| v1.1.565 | 2026-06-25 | 用户使用指标 DB-first fallback 写入收口：使用指标创建不再由调用方直接写 `current_store.user_usage_metrics`，统一通过 `save_user_usage_metric_record` 在 repository 单记录写入或 MemoryStore 测试 fallback 中保存指标；审计事件继续随 repository 写入或测试 fallback 提交 | Codex |
| v1.1.564 | 2026-06-25 | 运营记录审计 helper DB-first fallback 收口：`record_audit_event` 在轻量上下文无 `audit()` 方法时不再直接 append `current_store.audit_events`，统一通过审计事件列表 helper 写入 MemoryStore 测试集合；普通 MemoryStore 继续走 `audit()`，repository 写入仍由调用方事务携带审计事件提交 | Codex |
| v1.1.563 | 2026-06-25 | 模型网关配置与日志 DB-first fallback 写入收口：测试 fallback 的配置替换不再直接赋值 `current_store.model_gateway_configs`，模型调用日志不再直接 append `current_store.model_gateway_logs`；统一通过模型网关配置集合和日志集合 helper 更新 MemoryStore 测试集合，PostgreSQL 运行态继续由模型网关 repository 和调用方事务持久化配置、日志和审计 | Codex |
| v1.1.562 | 2026-06-25 | Mock Issue 写回 DB-first fallback 写入收口：写回结果创建不再先直接写 `current_store.mock_writebacks`，审计不再调用 `current_store.audit()`；统一由 `save_mock_writeback_record` 在 repository 事务或 MemoryStore 测试 fallback 中写入写回结果和审计事件，repository 运行态同步刷新本地读缓存以保持幂等重复提交 | Codex |
| v1.1.561 | 2026-06-25 | 研发执行器策略 DB-first fallback 写入收口：策略列表刷新、策略新增/编辑/删除以及按需补齐产品/代码库资源缓存不再直接写 `current_store.rd_task_executor_policies` / `current_store.products` / `current_store.product_git_repositories`；统一通过策略保存/删除和资源缓存 helper 操作 MemoryStore 测试集合，PostgreSQL 运行态继续通过 rd_task_executor_policy repository 写入策略和审计 | Codex |
| v1.1.560 | 2026-06-25 | 需求主流程 DB-first fallback 写入收口：需求创建、编辑、删除、审批、拒绝、关闭、批量分配、批量排期、批量推进和产品详细设计任务生成不再在调用方直接写 `current_store.requirements` / `current_store.ai_tasks` 或调用 `current_store.audit()`；统一通过需求保存、删除、任务联动和审计 helper 写入 MemoryStore 测试集合或 repository，PostgreSQL 运行态继续使用单记录/联动写入事务 | Codex |
| v1.1.559 | 2026-06-24 | 生命周期上下文与风险信号 MemoryStore fallback 写入收口：上下文边和风险信号刷新不再直接写 `current_store.lifecycle_context_edges` / `current_store.lifecycle_risk_signals`，统一通过锚点替换和风险范围替换 helper 操作测试集合；PostgreSQL 运行态继续由 lifecycle_context repository 持久化刷新结果 | Codex |
| v1.1.558 | 2026-06-24 | 知识空间配置 MemoryStore fallback 写入收口：知识空间、空间成员和文件夹新增/更新不再直接写 `current_store.knowledge_spaces` / `current_store.knowledge_space_members` / `current_store.knowledge_folders`，统一通过空间、成员替换和文件夹 helper 操作测试集合；PostgreSQL 运行态继续由知识 payload repository 持久化空间配置 | Codex |
| v1.1.557 | 2026-06-24 | 知识导入结构化产物 MemoryStore fallback 写入收口：导入解析生成的知识资产、chunk set 和 chunks 不再直接写 `current_store.knowledge_assets` / `current_store.knowledge_chunk_sets` / `current_store.knowledge_chunks`，统一通过资产、chunk set 和 chunk helper 操作测试集合；PostgreSQL 运行态继续由知识 payload repository 持久化结构化产物 | Codex |
| v1.1.556 | 2026-06-24 | 知识文档主流程 MemoryStore fallback 写入收口：上传、导入运行、失败标记、索引完成、重试、取消、chunk set 激活、重新解析和批量移动链路不再直接写 `current_store.knowledge_documents`，统一通过只写文档的 `put_knowledge_document_to_memory` helper 操作测试集合，避免误用会清理 chunks 的文档应用 helper | Codex |
| v1.1.555 | 2026-06-24 | 知识导入任务主流程 MemoryStore fallback 写入收口：上传、运行、失败标记、完成、重试、取消和重新解析链路不再直接写 `current_store.knowledge_import_jobs`，统一通过 import job helper 操作测试集合；PostgreSQL 运行态继续由知识 payload repository 持久化导入任务状态 | Codex |
| v1.1.554 | 2026-06-24 | 知识导入 worker claim MemoryStore fallback 写入收口：worker 本地 claim 不再直接写 `current_store.knowledge_import_jobs`，统一通过 import job helper 操作测试集合；repository 运行态继续优先使用 `claim_knowledge_import_job` 租约 | Codex |
| v1.1.553 | 2026-06-24 | 知识 chunk set MemoryStore fallback 写入收口：知识空间文档创建、编辑和重试索引中的 chunk set building/active 状态不再直接写 `current_store.knowledge_chunk_sets`，统一通过显式 chunk set helper 操作测试集合；PostgreSQL 运行态继续由知识文档 repository 写入和 `persist_knowledge_structure` 持久化结构化知识 payload | Codex |
| v1.1.552 | 2026-06-24 | 知识文档 MemoryStore fallback 写入收口：`clear_knowledge_chunks`、`apply_knowledge_document_to_memory` 和知识文档删除 fallback 不再直接写 `current_store.knowledge_documents` / `current_store.knowledge_chunks` / `current_store.knowledge_deposits`，统一通过显式 `_memory_collection` helper 操作测试集合，保持 PostgreSQL 运行态写入由 repository 承接 | Codex |
| v1.1.551 | 2026-06-24 | 知识域审计 helper DB-first 收口：`record_audit_event` 不再调用 `current_store.audit()`；repository 运行态只生成待写审计事件，MemoryStore 测试 fallback 通过显式审计事件列表 helper 追加并去重，保持知识文档和知识沉淀写路径由 repository/fallback helper 承接 | Codex |
| v1.1.550 | 2026-06-24 | 知识沉淀决策 DB-first 写路径收口：知识沉淀采纳/拒绝不再在决策服务层直接写 `current_store.knowledge_deposits`；统一通过 `save_knowledge_deposit_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态沉淀、可选知识文档、chunks、模型日志和审计使用同一数据库事务提交 | Codex |
| v1.1.549 | 2026-06-24 | 首页看板快照 DB-first fallback 收口：`sync_dashboard_metric_snapshot` 不再直接写 `current_store.dashboard_metric_snapshots`，统一优先调用 `save_dashboard_metric_snapshot_record`，仅在 MemoryStore 测试 fallback 中通过 helper 写入快照集合，保持 PostgreSQL 运行态看板快照单条 repository 写入和短 TTL 只读缓存语义 | Codex |
| v1.1.548 | 2026-06-24 | 迭代规划 DB-first 写路径收口：迭代建议生成、建议决策和建议转需求不再在服务层直接写 `current_store.requirements`、`current_store.iteration_plan_suggestions`、`current_store.iteration_plan_decisions` 或通过 `audit_events` 切片收集审计；统一通过 `persist_iteration_suggestion_record` / `persist_iteration_decision_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态建议、决策、转需求和审计使用同一数据库事务提交 | Codex |
| v1.1.547 | 2026-06-24 | Git Review 快照 DB-first 写路径收口：GitLab MR / GitHub PR 快照成功、复用和失败审计不再在服务层直接写 `current_store.gitlab_mr_snapshots` 或追加 `current_store.audit_events`；统一通过 `save_git_review_snapshot_record` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态快照和审计使用同一数据库事务提交 | Codex |
| v1.1.546 | 2026-06-24 | 代码巡检 DB-first 写路径收口：巡检报告、finding、通知、误报忽略审批和整改任务派生不再在生产服务层直接写 `current_store.code_inspection_*` 或 `current_store.ai_tasks`；统一通过 `persist_code_inspection_records` / `persist_ai_task_record` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态的巡检报告、finding、通知和审计使用同一数据库事务提交 | Codex |
| v1.1.545 | 2026-06-24 | Bug 管理 DB-first 收口：Bug 创建、批量更新、编辑和删除不再直接调用 `current_store.audit()` 或写 `current_store.bugs`，统一通过 `save_bug_record` / `delete_bug_record` 写入 MemoryStore fallback 或 repository；Bug 单记录写入、删除和审计在 PostgreSQL 运行态使用同一数据库事务 | Codex |
| v1.1.544 | 2026-06-24 | AI 助手历史与配置 DB-first 收口：会话/消息测试 fallback 写入改为 helper 访问，助手动作引用配置和角色快捷任务配置不再调用 `current_store.audit()` 或直接写配置集合，统一通过 repository 单记录写入或 MemoryStore fallback 写入配置和审计 | Codex |
| v1.1.543 | 2026-06-24 | AI 助手聊天 DB-first 收口：`assistant_chat` 服务移除聊天运行完成、取消、失败和模型网关审计链路中的直接 `current_store` 写入，不再通过 `current_store.audit_events` 切片收集本次审计；聊天运行、会话、消息、模型日志和审计统一通过 `save_assistant_chat_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态使用数据库事务提交；助手触发定时作业运行归因同步通过 repository 写回 | Codex |
| v1.1.542 | 2026-06-24 | AI 助手草案 DB-first 收口：`assistant_action_drafts` 服务移除草案、动作运行和助手触发定时作业运行归因链路中的直接 `current_store` 写入，不再调用 `current_store.audit()` 生成草案审计；草案、动作运行和审计统一通过 `save_assistant_action_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态使用数据库事务提交 | Codex |
| v1.1.541 | 2026-06-24 | DB-first 兼容层继续收口：AI 执行器 Runner 服务移除 Runner、任务、插件调用、定时作业运行、采集运行和 AI 任务状态同步中的直接 `current_store` 写入，统一通过单记录 helper 写入 MemoryStore 测试 fallback 或 repository；相关单记录写入与审计事件使用数据库事务 | Codex |
| v1.1.540 | 2026-06-24 | 产品配置 DB-first 收口继续推进：迭代版本和版本代码分支配置路由移除直接 `current_store` 写入，统一通过单记录 helper 写入 MemoryStore 测试 fallback 或 repository；需求单记录写入/删除与审计事件开始使用数据库事务 | Codex |
| v1.1.539 | 2026-06-24 | 产品配置 DB-first 收口继续推进：产品、产品模块、产品 Git 仓库和相关系统路由移除直接 `current_store` 写入，统一通过产品配置单记录 helper 写入 MemoryStore 测试 fallback 或 repository，并把产品配置单记录写入/删除与审计收口为数据库事务 | Codex |
| v1.1.538 | 2026-06-24 | 执行诊断中心稳定性增强：`execution_trace_snapshots` 刷新必须在单个数据库事务中完成 upsert 与过期快照删除，避免诊断读模型出现半刷新状态 | Codex |
| v1.1.537 | 2026-06-24 | 模型网关配置 DB-first 收口：配置 create/patch/delete 新增 repository 单记录读取、upsert 和 delete，默认配置切换与审计随单条记录写入，不再通过整包 `model_gateway_configs/model_gateway_logs` payload 同步配置变更 | Codex |
| v1.1.536 | 2026-06-24 | DB-first 剩余兼容层专项扫描工具化：新增 `scripts/audit_memory_store_usage.py`，按读路径、写路径和 helper 对 `current_store.*` 残留分级输出，用于后续收口和发布前审计 | Codex |
| v1.1.535 | 2026-06-24 | 产品配置 DB-first 收口继续推进：迭代版本、产品模块、产品 Git 仓库和相关系统 create 使用 repository 单记录产品存在性校验、同产品列表或 code 单查冲突校验，不再为子资源创建预加载全量产品配置集合 | Codex |
| v1.1.534 | 2026-06-24 | 产品配置 DB-first 收口继续推进：迭代版本 patch/delete 使用 repository 单记录读取，同产品版本 code 冲突和需求/任务/Bug/分支配置引用检查不再预加载全量产品配置及业务集合 | Codex |
| v1.1.533 | 2026-06-24 | 产品配置 DB-first 收口继续推进：产品模块 delete 使用 repository 单记录读取和跨需求/任务/Bug 的 EXISTS 引用检查，删除不再预加载全量产品配置及业务集合 | Codex |
| v1.1.532 | 2026-06-24 | 产品配置 DB-first 收口继续推进：产品模块 patch 新增 repository 单记录读取与轻量写上下文，模块编码冲突校验仅读取同产品模块列表，避免为单条模块编辑预加载全量产品配置集合 | Codex |
| v1.1.531 | 2026-06-24 | 产品配置 DB-first 收口继续推进：迭代版本代码分支配置 patch/delete 新增 repository 单记录读取与轻量写上下文，避免为单条版本分支配置操作预加载全量产品配置集合 | Codex |
| v1.1.530 | 2026-06-24 | 产品配置 DB-first 收口继续推进：产品 Git 仓库和相关系统 patch/delete 新增 repository 单记录读取与轻量写上下文，避免为单条子资源操作预加载全量产品配置集合 | Codex |
| v1.1.529 | 2026-06-24 | 用户洞察 DB-first 收口：用户反馈更新和转需求链路新增 repository 按 ID 读取，服务层使用反馈专用写上下文，避免依赖运行时 MemoryStore 全量反馈集合 | Codex |
| v1.1.528 | 2026-06-24 | 管理主列表统一支持本地筛选视图：`ManagementListPage` 通过页面级 `viewStorageKey` 保存、应用、删除当前筛选与排序组合，需求、任务、迭代版本、Bug、用户洞察、代码巡检、执行诊断、草案任务台、产品资产和系统管理列表统一接入 | Codex |
| v1.1.527 | 2026-06-24 | 执行诊断中心补齐 Runner 节点：`ai_executor_task.runner_id` 解析为 `ai_executor_runner` 节点并支持按 Runner source_type/source_id 过滤，节点展示心跳、协议、工作区和健康状态且不暴露 token hash | Codex |
| v1.1.526 | 2026-06-24 | 执行诊断中心补齐模型网关日志审计吸附：独立 `model_gateway_log` Trace 会关联 subject、payload 或 ai_task 指向的审计事件，按审计 ID 下钻回到同一模型调用链路并避免重复孤立审计 Trace | Codex |
| v1.1.525 | 2026-06-24 | 插件连接和动作配置列表接入可选 PostgreSQL 分页读路径：带 `page/page_size` 时按关键字、插件、状态和环境筛选并返回 query/performance，未分页保留旧全量兼容 | Codex |
| v1.1.524 | 2026-06-24 | 执行诊断中心补齐定时作业阶段节点过滤：`scheduled_job_stage` 纳入 source_type 枚举和前端筛选，下钻可按 `scheduled_job_run_id:stage_id` 精准定位运行阶段链路 | Codex |
| v1.1.523 | 2026-06-24 | 定时作业配置列表接入 PostgreSQL read model 分页：`GET /api/system/scheduled-jobs` 支持名称、关键字、产品、来源、类型、启停、状态筛选和服务端排序，旧全量返回仅作为兼容路径 | Codex |
| v1.1.522 | 2026-06-24 | 执行诊断中心纳入结果写入记录节点：定时作业运行和插件调用链路自动派生 `result_write_record`，可按写入记录 ID 反查同一条 Trace 并确认产物写入状态 | Codex |
| v1.1.521 | 2026-06-24 | 代码巡检 finding 新增误报忽略审批闭环：报告详情展示逐条审批状态，支持提交忽略申请和批准/驳回，审批通过同步 suppression 统计与审计事件 | Codex |
| v1.1.520 | 2026-06-24 | 代码巡检治理概览新增规则包与误报治理聚合：dashboard 返回 `rule_governance`，页面展示最近报告规则/扫描器版本、版本不一致提示、规则/扫描器版本分布、suppression 总量和过滤原因分布 | Codex |
| v1.1.519 | 2026-06-24 | AI 助手草案任务台继续编辑入口收敛：列表与详情弹窗统一根据草案 ID 生成 `/assistant?draft_id=...` 深链，不再依赖后端来源链接字段；进入助手后复用既有草案深链加载草案卡，来源链路仍独立跳转执行诊断 | Codex |
| v1.1.518 | 2026-06-24 | 执行诊断入口继续统一：前端新增可复用 `ExecutionTraceLink`，AI 助手草案、定时作业运行详情和代码巡检报告详情统一生成 `/governance/execution-traces?source_id=...&source_type=...` 深链，代码巡检详情同时提供巡检报告、来源运行和插件调用诊断入口 | Codex |
| v1.1.517 | 2026-06-24 | 执行诊断中心补齐 AI 助手消息来源链路：`assistant_chat_run` Trace 增加用户消息和助手消息节点，`source_id` 可按 `assistant_message_id` 定位链路；草案任务台新增“来源链路”入口，从草案 `source_message_id` 跳转统一执行诊断 | Codex |
| v1.1.516 | 2026-06-24 | 插件管理前端连接/Runner 测试诊断弹窗继续组件化：连接测试状态、占位 Header 阻断提示、诊断检查项、请求调试台和远端响应预览统一收口到 `PluginDiagnostics`，主页面只保留测试触发、列表状态更新和提示消息编排 | Codex |
| v1.1.515 | 2026-06-24 | 系统角色治理新增用户权限诊断：`GET /api/system/permissions/diagnostics` 可按用户、菜单路径、权限点和数据范围解释允许/阻断原因，角色管理页新增只读诊断工具用于排查某用户为什么能看或不能看 | Codex |
| v1.1.514 | 2026-06-24 | 定时作业前端 Catalog 派生逻辑继续组件化：服务端 catalog 的选项映射、必填校验、默认结果动作和标签格式化抽到 `useScheduledJobCatalogOptions`，主页面只保留 catalog 状态与业务编排 | Codex |
| v1.1.513 | 2026-06-24 | 定时作业新增服务端 catalog/注册中心：作业类型、执行方式、调度方式、连接环境、代码巡检扫描/规则/结果动作和必填规则由 `/api/system/scheduled-job-catalog` 返回，前端新增/编辑弹窗优先使用服务端配置并保留静态降级 | Codex |
| v1.1.512 | 2026-06-24 | 定时作业前端表单转换继续组件化：作业类型选项、扫描配置选项、模板 payload 解析、助手草案回填、配置归一化和路由参数解析抽到 `scheduledJobFormTransformHelpers`，主页面继续收敛为作业配置、运行列表和详情编排 | Codex |
| v1.1.511 | 2026-06-24 | 插件管理前端表单转换继续组件化：连接/动作/Runner 表单 payload、请求预览、结果映射、schema 回填和助手草案回填抽到 `pluginFormTransformHelpers`，主页面只保留插件、连接、动作和 Runner 编排 | Codex |
| v1.1.510 | 2026-06-24 | 执行诊断详情补齐排障建议：详情顶部汇总失败、取消、运行中或排队节点，提供来源 ID 深链和“问 AI”入口，帮助从统一 Trace 直接进入后续诊断 | Codex |
| v1.1.509 | 2026-06-24 | 执行诊断中心补齐来源 ID 深链定位：列表支持 `source_id` 按任一节点来源 ID 精准过滤，前端 URL 命中唯一链路时自动打开详情，便于从定时作业、插件、Runner、模型网关、代码巡检和 AI 助手跳转排障 | Codex |
| v1.1.508 | 2026-06-23 | 定时作业前端运行详情弹窗继续组件化：运行结果详情的 footer、基础信息、运行链路、Trace DAG、结果写入记录和 JSON 预览收口到 `ScheduledJobRunDetailModal`，主页面只保留选中运行、关闭、复制配置和模板生成编排 | Codex |
| v1.1.507 | 2026-06-23 | 插件管理前端 Runner 新增/编辑弹窗继续组件化：Runner Modal/Form 外壳和目标系统联动逻辑抽到 `PluginRunnerModal`，主页面只保留 Runner 表单打开、提交和刷新编排 | Codex |
| v1.1.506 | 2026-06-23 | 插件管理前端 Runner Token 轮换提示和确认弹窗继续组件化：轮换成功提示与确认弹窗收口到 `PluginUtilityModals`，主页面只保留 Runner 轮换状态和提交编排 | Codex |
| v1.1.505 | 2026-06-23 | 插件管理前端插件定义弹窗继续组件化：插件名称、编码、协议、分类、风险等级、状态和说明字段抽到 `PluginModal`，主页面只保留插件表单打开、校验和提交编排 | Codex |
| v1.1.504 | 2026-06-23 | 执行诊断快照读模型增加短 TTL 复用与详情未命中强制刷新：列表/已有详情在短时间内复用 `execution_trace_snapshots`，新链路详情查不到时立即重建快照，降低诊断页重复查询开销且保持钻取可见性 | Codex |
| v1.1.503 | 2026-06-23 | 定时作业前端基础信息继续组件化：新增/编辑作业的名称、作业类型、所属产品和启用字段抽到 `ScheduledJobBasicInfoSection`，主页面只保留作业类型默认配置和产品切换联动编排 | Codex |
| v1.1.502 | 2026-06-23 | 定时作业前端代码仓库配置继续组件化：代码巡检作业的扫描方式、仓库/分支、扫描引擎、规则、baseline、已接受风险和质量门禁字段抽到 `ScheduledJobCodeRepositorySection`，主页面只保留扫描模式默认值和仓库变更编排 | Codex |
| v1.1.501 | 2026-06-23 | 插件管理前端动作编辑弹窗继续组件化：动作新增/编辑表单、结果写入映射字段、请求预览和高级 JSON 字段抽到 `PluginActionModal`，主页面只保留动作表单状态、场景默认值和提交编排 | Codex |
| v1.1.500 | 2026-06-23 | 插件管理前端连接编辑弹窗继续组件化：连接新增/编辑表单、认证 JSON、请求 JSON、schema 字段和“保存并测试”入口抽到 `PluginConnectionModal`，主页面只保留连接表单状态、默认值和提交/测试编排 | Codex |
| v1.1.499 | 2026-06-23 | 插件管理前端连接与动作列表继续组件化：环境筛选、连接测试入口、动作写入目标展示、试运行/运行/删除操作抽到 `PluginConnectionTable` 与 `PluginActionTable`，主页面只保留插件业务事件编排 | Codex |
| v1.1.498 | 2026-06-23 | 插件管理前端插件市场继续组件化：官方插件市场表格、schema 展开、推荐场景、动作模板和配置入口抽到 `PluginMarketplaceTable`，主页面只保留市场动作事件编排 | Codex |
| v1.1.497 | 2026-06-23 | 插件管理前端插件列表继续组件化：插件表格、官方插件复制、编辑/删除操作和分类/版本标签 helper 抽到 `PluginTable` 与 `pluginCatalogHelpers`，主页面只保留插件事件编排 | Codex |
| v1.1.496 | 2026-06-23 | 插件管理前端 Runner 表格继续组件化：执行器列表、展开启动命令、健康状态、Token 状态和操作列抽到 `PluginRunnerTable`，主页面只保留 Runner 事件编排 | Codex |
| v1.1.495 | 2026-06-23 | 插件管理前端 Runner 测试诊断继续组件化：执行器状态摘要、诊断检查项表格和健康状态展示抽到 `RunnerTestDiagnosticsContent`，主页面只保留测试触发和弹窗编排 | Codex |
| v1.1.494 | 2026-06-23 | 定时作业前端执行链路预览继续组件化：配置向导 Steps、编排节点卡片和默认向导步骤抽到 `ScheduledJobOrchestrationFlow`，主页面只保留节点数据构造 | Codex |
| v1.1.493 | 2026-06-23 | 定时作业前端运行详情继续组件化：结果写入记录表格、展开 JSON 预览、来源/状态/摘要展示抽到 `ScheduledJobRunResultWriteRecords`，主页面只保留运行详情编排 | Codex |
| v1.1.492 | 2026-06-23 | 定时作业前端试运行结果继续组件化：JSON 预览抽到 `ScheduledJobJsonPreview`，全链路试运行结果面板抽到 `ScheduledJobDryRunResultPanel`，主页面保留试运行状态与提交编排 | Codex |
| v1.1.491 | 2026-06-23 | 定时作业前端调度配置继续组件化：调度方式、Cron 表达式和固定间隔字段抽到 `ScheduledJobScheduleConfigSection`，主页面只保留表单段落编排 | Codex |
| v1.1.490 | 2026-06-23 | 定时作业前端结果动作编辑器继续组件化：写入策略选择、代码巡检结果动作列表、严重级别和通知动作字段抽到 `ScheduledJobActionConfigSection`，主页面保留插件动作数据和提交编排 | Codex |
| v1.1.489 | 2026-06-23 | 定时作业前端数据连接选择器继续组件化：连接环境筛选、数据连接多选、native full scan 禁用提示和插件资源校验抽到 `ScheduledJobDataConnectionSection`，主页面保留筛选数据与自动匹配动作编排 | Codex |
| v1.1.488 | 2026-06-23 | 定时作业前端表单继续按配置域减重：通用表单分区抽到 `ScheduledJobFormSection`，AI 模型、AI角色、Skills 和知识引用字段抽到 `ScheduledJobAiExecutionSection`，主页面保留作业编排和提交逻辑 | Codex |
| v1.1.487 | 2026-06-23 | 执行诊断中心补齐 AI 助手聊天运行链路：`assistant_chat_runs` 可作为 ExecutionTrace 根类型，关联模型网关日志和审计事件并统一脱敏展示 | Codex |
| v1.1.486 | 2026-06-23 | 代码巡检治理概览 SLA 补齐整改任务覆盖口径：严重 finding 同时统计 Bug 关联和整改任务派生覆盖率，页面展示整改任务覆盖率和未派生任务摘要 | Codex |
| v1.1.485 | 2026-06-23 | 代码巡检治理概览补齐质量门禁趋势：后端 dashboard trend 按日期聚合通过、失败、跳过和未知门禁数，前端概览新增“质量门禁趋势”表 | Codex |
| v1.1.484 | 2026-06-23 | 技术规格启动按业务域拆分：新增 `domains/` 索引和需求交付、AI 助手、插件定时作业执行器、质量运营洞察、系统治理 RBAC 平台配置五个域文档，主规格保留跨域原则和导航 | Codex |
| v1.1.483 | 2026-06-23 | 插件管理前端继续按工具弹窗边界减重：系统变量全集、Runner 执行日志和动作试运行弹窗抽到 `PluginUtilityModals`，主页面保留插件、连接、动作和 Runner 状态编排 | Codex |
| v1.1.482 | 2026-06-23 | 系统角色治理新增只读 RBAC 策略矩阵：后端按角色聚合权限点、菜单入口、数据范围、高风险权限和菜单权限缺口，角色管理页展示“权限审计矩阵”用于排查入口可见但接口无权等授权问题 | Codex |
| v1.1.481 | 2026-06-23 | 定时作业前端继续按运行页签边界减重：运行健康概览、最近失败和慢运行表格抽到 `ScheduledJobRunObservabilityOverview`，主页面保留作业/运行编排逻辑 | Codex |
| v1.1.480 | 2026-06-23 | 执行诊断中心新增 PostgreSQL 持久化读模型：统一链路构建后刷新 `execution_trace_snapshots`，列表和详情优先读取快照分页，保留 MemoryStore 测试 fallback | Codex |
| v1.1.479 | 2026-06-23 | 执行诊断中心前端详情继续按组件边界减重：链路概要、关联对象、节点表、关系表和元数据预览抽到 `ExecutionTraceDetailContent`，为后续 Trace DAG 钻取和诊断建议扩展预留稳定边界 | Codex |
| v1.1.478 | 2026-06-23 | 插件管理前端 Runner 配置继续减重：执行器协议、命令、目标系统、安装模式、工作区白名单和 Token 字段抽到 `PluginRunnerFormFields`，Runner 选项与安装包 helper 独立为 `pluginRunnerHelpers` | Codex |
| v1.1.477 | 2026-06-23 | 插件管理前端连接表单继续减重：请求参数行、连接 schema 字段、GitHub/GitLab 地址校验抽到 `PluginConnectionFormFields` 与 `pluginConnectionAddressHelpers`，主页面保留插件、连接和动作编排逻辑 | Codex |
| v1.1.476 | 2026-06-23 | 插件管理前端继续按诊断边界减重：连接测试请求调试台、市场连接 schema 展示、最近测试摘要、试运行写入预览和状态颜色 helper 抽到 `PluginDiagnostics`，主页面聚焦插件、连接、动作和 Runner 编排 | Codex |
| v1.1.475 | 2026-06-23 | 定时作业前端运行详情继续按组件边界减重：运行链路、Trace DAG、模板来源和复跑对比抽到 `ScheduledJobRunTraceDetails`，执行节点 helper 独立维护，主页面聚焦作业列表、表单和运行详情编排 | Codex |
| v1.1.474 | 2026-06-23 | AI 助手前端主页面继续按组件边界减重：消息气泡、草案工具结果、运行诊断、插件连接诊断和运行对比卡片收口到 `AssistantMessageBubble`，共享消息 helper 独立维护，主页面聚焦会话、Composer 和面板编排 | Codex |
| v1.1.473 | 2026-06-23 | 新增 AI 助手草案任务台：`/assistant/drafts` 按当前用户汇总待确认、失败、已采纳和已修改草案，支持来源深链、详情埋点、继续编辑、确认和取消，并以列表 API 输出采纳率、处理率和用户修改率 | Codex |
| v1.1.472 | 2026-06-23 | 新增运营治理“执行诊断”中心：按运行根聚合定时作业运行、插件调用、AI 执行器任务、模型网关日志、代码巡检报告和审计事件，统一展示节点、边、状态、耗时和脱敏元数据 | Codex |
| v1.1.471 | 2026-06-21 | AI 助手历史列表补齐 cursor 分页与加载更多，历史消息草案工具结果按动作白名单脱敏，指标明细按 limit 下推，草案深链自动滚动到可视区域 | Codex |
| v1.1.470 | 2026-06-21 | 研发执行器策略任务类型下拉按研发流程补齐：展示 PRD/原型/产品详细设计、技术方案、代码实现/开发计划、代码评审、自动化测试、代码整改、发布上线评估和上线后分析，并与现有 `task_type` 匹配口径保持一致 | Codex |
| v1.1.469 | 2026-06-21 | 新增研发执行器策略设计与实现口径：研发任务可按任务类型、产品和优先级匹配 Codex、Claude Code、OpenClaw Runner；该策略只引用插件管理下的 AI 执行器，不装配 Agent/Skill，Runner 完成后回写 AI 任务并进入人工确认 | Codex |
| v1.1.468 | 2026-06-20 | 前端展示型时间统一按 `Asia/Shanghai` 转换后端 UTC 时间，覆盖管理列表、代码巡检、定时作业下次运行/运行详情、Runner 和助手引用等页面，避免少显示 8 小时或直接暴露 ISO 原文 | Codex |
| v1.1.467 | 2026-06-20 | AI 助手补齐运行环境自检引导、效果指标查看口径校准、历史命令会话签名折叠、@ 能力后台配置页和真实页面 smoke 验证 | Codex |
| v1.1.466 | 2026-06-20 | AI 助手 @ 动作候选配置化：新增 `assistant_action_reference_configs` 表、管理 API、灰度/启停/排序/模板版本和审计；效果指标补齐明细钻取 | Codex |
| v1.1.465 | 2026-06-20 | AI 助手新增聊天运行表、消息生命周期字段和服务端取消链路，停止生成后可持久化、审计和历史追踪 | Codex |
| v1.1.464 | 2026-06-19 | AI 助手动作候选选择后保留 `@动作名` 命令前缀并承接用户正文，避免候选 prompt 覆盖输入 | Codex |
| v1.1.463 | 2026-06-19 | AI 助手 @ 候选新增动作入口类型，支持 `@新建` 搜索新建需求/Bug/插件/定时作业/知识/AI 能力配置并回填指令 | Codex |
| v1.1.462 | 2026-06-19 | AI 助手草案表单应用改为服务端 PATCH+confirm 闭环，确认幂等和终态修改保护落地；运营引用候选按产品 scope 收敛，角色快捷任务补齐前端配置入口 | Codex |
| v1.1.461 | 2026-06-18 | AI 助手补齐草案详情查看服务端埋点、定时作业运行助手归因、角色快捷任务配置表和结构化引用严格优先 | Codex |
| v1.1.460 | 2026-06-18 | AI 助手失败运行修复草案补齐来源配置和 current/proposed 字段差异追踪 | Codex |
| v1.1.459 | 2026-06-18 | AI 助手草案模板市场首批六类模板均改为可生成草案，依赖缺失走前置草案闭环 | Codex |
| v1.1.458 | 2026-06-18 | AI 助手定时作业执行权限拆分为 `system.scheduled_jobs.run`，业务角色可执行一次但不能管理作业配置 | Codex |
| v1.1.457 | 2026-06-18 | AI 助手测试/发布角色“发布风险”快捷任务改为草案优先，回填发布风险分析草案提示 | Codex |
| v1.1.456 | 2026-06-18 | AI 助手管理员“AI能力”快捷任务改为草案优先，直接回填新增 AI能力配置向导提示 | Codex |
| v1.1.455 | 2026-06-18 | AI 助手泛化新增任务向导补齐 AI 能力配置入口，用户可先选择 Skill / AI角色草案路径再生成具体能力配置 | Codex |
| v1.1.454 | 2026-06-18 | AI 助手 @ 候选空态补齐定时作业新增和草案生成入口，避免用户误以为 @ 功能无响应 | Codex |
| v1.1.453 | 2026-06-18 | AI 助手对无定时作业管理权限用户输入 `@... 执行一次` 增加发送前权限提示，明确本次不会直接执行 | Codex |
| v1.1.452 | 2026-06-18 | AI 助手产品角色快捷任务改为草案优先，反馈洞察回填周反馈洞察定时作业草案提示，版本风险回填发布风险分析草案提示 | Codex |
| v1.1.451 | 2026-06-18 | AI 助手 @ 定时作业执行一次在等待外部 AI 执行器时返回 `progress_text`，运行卡片明确展示“等待 AI 执行器接单”，避免误判为未执行 | Codex |
| v1.1.450 | 2026-06-18 | AI 助手运行诊断补齐数据连接阶段插件调用日志追踪，三段诊断均可回溯安全日志元数据 | Codex |
| v1.1.449 | 2026-06-18 | AI 助手 @ 候选搜索态保留键盘操作提示，避免输入关键词后用户不知道仍可上下选择并回车添加 | Codex |
| v1.1.448 | 2026-06-18 | AI 助手效果指标失败修复率收紧为仅统计成功 `manual_rerun`，普通调度成功不得误算为修复 | Codex |
| v1.1.447 | 2026-06-18 | AI 助手 run-once 权限闭环补齐：定时作业管理员未命中现成作业时也生成待确认草案，前端展示未执行原因状态卡 | Codex |
| v1.1.446 | 2026-06-18 | AI 助手插件连接/动作草案确认改用插件管理权限，和 @ 插件候选专项授权保持一致 | Codex |
| v1.1.445 | 2026-06-18 | AI 助手 AI 能力草案确认改用 AI 能力管理权限，避免误依赖定时作业管理权限 | Codex |
| v1.1.444 | 2026-06-18 | AI 助手新增任务向导和研发任务草案统一使用“数据来源、AI处理、结果动作、调度策略、确认执行”五步闭环 | Codex |
| v1.1.443 | 2026-06-18 | AI 助手 @ 运维候选权限标签改为显示专项授权来源，避免非 admin 用户被误标为管理员可引用 | Codex |
| v1.1.442 | 2026-06-18 | AI 助手分析类草案补齐 `wizard_steps`，发布风险和知识库巡检卡片展示统一五步闭环 | Codex |
| v1.1.441 | 2026-06-18 | AI 助手周反馈 run-once 消歧补强：停用或非洞察的精确同名作业不得拦截官方周反馈洞察执行 | Codex |
| v1.1.440 | 2026-06-18 | AI 助手运行诊断卡片显式展示“数据连接是否成功 / AI处理是否成功 / 结果动作是否写入成功”三段判断 | Codex |
| v1.1.439 | 2026-06-18 | AI 助手草案模板市场流程收敛为“数据来源、AI处理、结果动作、调度策略、确认执行”五步，知识引用纳入 AI 处理上下文 | Codex |
| v1.1.438 | 2026-06-17 | 对齐 AI 助手效果指标展示口径：前端主指标显示为知识引用命中率 | Codex |
| v1.1.437 | 2026-06-17 | AI 助手周反馈 `@... 执行一次` 消歧改为按官方模板、作业类型和名称语义评分；草案用户修改率接入服务端修改标记 API | Codex |
| v1.1.436 | 2026-06-17 | AI 助手服务端草案详情保留并返回 `wizard_steps`，深链草案卡片不丢配置向导和依赖关系 | Codex |
| v1.1.435 | 2026-06-17 | AI 助手 `/assistant?draft_id=...` 深链加载服务端草案，复用草案卡片展示状态、预检、确认/取消和追踪入口 | Codex |
| v1.1.434 | 2026-06-17 | AI 助手 `@` 候选面板显性化权限、来源、更新时间和摘要；无匹配候选时保持面板可见并提示换词或检查权限 | Codex |
| v1.1.433 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 无执行权限时返回明确 `permission_denied` 工具结果；具备 `system.scheduled_jobs.manage` 的用户可通过显式 @ 命令触发定时作业 | Codex |
| v1.1.432 | 2026-06-17 | AI 助手执行一次运行卡片轮询增强，状态仍为 running 但执行节点摘要更新时也刷新进度 | Codex |
| v1.1.431 | 2026-06-17 | AI 助手显式知识引用补齐知识空间和知识目录，按权限限量注入范围内 chunk | Codex |
| v1.1.430 | 2026-06-17 | AI 助手 `@` 候选类型词搜索收敛，定时作业优先作业定义，运行记录/失败优先运行实例 | Codex |
| v1.1.429 | 2026-06-17 | AI 助手 `@` 候选显示口径对齐，`ai_task` 展示为“研发任务”，`ai_skill` 展示为“Skill” | Codex |
| v1.1.428 | 2026-06-17 | AI 助手裸 `@` 默认候选补齐插件连接，默认上下文候选覆盖插件动作、插件连接、AI角色和 Skill | Codex |
| v1.1.427 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 前端提交路径增强，点击发送或按 Enter 时按 `type=scheduled_job` 补查引用再提交 | Codex |
| v1.1.426 | 2026-06-17 | AI 助手新增插件连接失败诊断工具结果，按连接配置、最近测试和修复建议解释连接失败且不调用模型网关 | Codex |
| v1.1.425 | 2026-06-17 | AI 助手执行一次运行卡片新增当前执行节点说明，展示正在等待数据连接、AI执行器、AI处理或结果动作 | Codex |
| v1.1.424 | 2026-06-17 | AI 助手效果指标的草案类型拆分新增处理率展示，帮助定位不同草案类型的待确认卡点 | Codex |
| v1.1.423 | 2026-06-17 | AI 助手草案配置向导每个步骤新增“AI生成<步骤>草案”回填入口，ready/pending 步骤也可由 AI 调整草案 | Codex |
| v1.1.422 | 2026-06-17 | AI 助手从运行详情链接带入 `scheduled_job_run` 时，在“本次上下文”常驻展示引用解析中、已带入或失败状态 | Codex |
| v1.1.421 | 2026-06-17 | AI 助手配置向导每步补齐“手动调整”入口，数据来源/结果动作跳插件管理，AI处理跳 AI 能力配置，调度/确认跳定时作业配置 | Codex |
| v1.1.420 | 2026-06-17 | AI 助手草案确认失败后前端草案卡片显式进入“失败”状态，不再停留在待确认并仅依赖 toast 提示 | Codex |
| v1.1.419 | 2026-06-17 | AI 助手运行记录卡片补齐“问这次运行 / 生成修复草案 / 对比上次成功”快捷追问，直接携带当前运行引用进入诊断闭环 | Codex |
| v1.1.418 | 2026-06-17 | AI 助手执行一次运行卡片在轮询到终态后显式展示“已刷新到最新状态”，避免初始 running 文案让用户误以为未执行 | Codex |
| v1.1.417 | 2026-06-17 | AI 助手“本次上下文”区域改为常驻展示，未选择引用时明确显示 0 个显式引用、0 个知识 chunk 和未注入知识正文 | Codex |
| v1.1.416 | 2026-06-17 | AI 助手后端访问白名单补齐 `test_owner`、`tester`、`release_owner`，避免测试/发布角色看到快捷入口但调用助手 API 被拒 | Codex |
| v1.1.415 | 2026-06-17 | AI 助手 `@提取每周用户反馈有价值信息 执行一次` 在多个相近 active 周反馈作业下优先执行官方周反馈洞察作业，避免命令退回草案 | Codex |
| v1.1.414 | 2026-06-17 | AI 助手测试快捷任务扩展到测试负责人、测试人员和发布负责人，补齐角色化入口覆盖面 | Codex |
| v1.1.413 | 2026-06-17 | AI 助手运行诊断卡片展示各阶段关联日志 ID，让 AI 处理和结果动作可从对话继续追踪到模型/插件日志 | Codex |
| v1.1.412 | 2026-06-17 | AI 助手本次上下文新增显式“查看摘要”弹窗，run-once 定时作业草案卡片明确“确认并执行一次”闭环提示 | Codex |
| v1.1.411 | 2026-06-17 | AI 助手草案配置向导对需前置配置或阻塞步骤提供“生成前置草案”回填入口，让缺连接、缺动作、缺 AI 能力可继续闭环 | Codex |
| v1.1.410 | 2026-06-17 | AI 助手效果指标面板新增运行追踪和引用追踪分子分母展示，让作业成功率、失败修复率和引用命中率可解释 | Codex |
| v1.1.409 | 2026-06-17 | AI 助手效果指标面板新增草案状态和草案类型拆分，便于追踪待确认、已应用、已取消等草案闭环分布 | Codex |
| v1.1.408 | 2026-06-17 | AI 助手运行诊断和运行对比卡片新增就地后续追问入口，可直接带运行引用生成修复草案、对比上次成功或继续诊断 | Codex |
| v1.1.407 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 识别 TTL 内已有运行中记录并等待新运行可追踪后返回，避免重复触发后仍像未执行 | Codex |
| v1.1.406 | 2026-06-17 | 定时作业失败运行详情新增 AI 快捷追问入口，可一键携带运行引用生成修复草案或对比上次成功运行 | Codex |
| v1.1.405 | 2026-06-17 | AI 助手前端草案卡片按 `draft_id/server_draft_id/client_draft_id` 归一化追踪 ID，避免服务端草案字段差异导致卡片消失或无法跳转 | Codex |
| v1.1.404 | 2026-06-17 | AI 助手发送 `@定时作业 执行一次` 前补齐当前 @ 候选兜底解析，定时作业运行详情消费 `result_write_record_id` 深链并自动展开目标写入记录 | Codex |
| v1.1.403 | 2026-06-17 | AI 助手运行诊断卡片把结果动作段的结果写入记录 ID 链接到定时作业运行详情，增强失败排障追踪闭环 | Codex |
| v1.1.402 | 2026-06-17 | AI 助手“本次上下文”对超出后端注入上限的知识文档显示“最多 8 个知识 chunk 按权限注入”，避免误导用户以为整篇文档全量进入模型 | Codex |
| v1.1.401 | 2026-06-17 | AI 助手终态草案前端收紧：已取消、已过期或失败草案不得再应用到配置表单，只能查看详情或重新生成 | Codex |
| v1.1.400 | 2026-06-17 | AI 助手裸 `@` 默认候选按引用类型均衡返回，避免知识文档数量过多时挤掉需求、AI任务、定时作业、运行记录、动作、AI角色和 Skill | Codex |
| v1.1.399 | 2026-06-17 | AI 助手周反馈、邮件摘要和线上日志异常定时作业草案统一返回 `wizard_steps` 配置向导状态，让数据来源、AI处理、结果动作、调度和确认闭环可追踪 | Codex |
| v1.1.398 | 2026-06-17 | AI 助手代码巡检定时作业草案新增显式 `wizard_steps` 配置向导状态，并增强 `@定时作业 执行一次` 对相似历史任务的可执行作业消歧 | Codex |
| v1.1.397 | 2026-06-17 | AI 助手代码巡检草案补齐 AI Skill/AI角色前置草案，草案生成可确定性返回并支持确认写入 AI 能力配置和解析前置草案资源 | Codex |
| v1.1.396 | 2026-06-17 | AI 助手显式知识引用从文档级补齐到知识 chunk 级，支持 @ 候选、解析和只注入被选中片段 | Codex |
| v1.1.395 | 2026-06-17 | AI 助手执行一次运行记录在聊天气泡内展示状态追踪，并补齐草案详情弹窗展示 payload、字段差异和校验问题 | Codex |
| v1.1.394 | 2026-06-17 | AI 助手“新增任务”向导的建议入口补齐研发任务、定时作业、插件动作、代码巡检和反馈洞察五类任务 | Codex |
| v1.1.393 | 2026-06-17 | AI 助手 run-once 定时作业草案确认后，前端草案卡片展示创建作业和本次运行记录两个追踪入口 | Codex |
| v1.1.392 | 2026-06-17 | AI 助手带“执行一次”意图的定时作业草案确认后会自动触发一次手动运行，并在确认结果和审计中返回运行记录 | Codex |
| v1.1.391 | 2026-06-17 | AI 助手 `@周反馈洞察 执行一次` 未命中已配置作业时，自动生成可确认的周反馈定时作业草案，避免命令无闭环 | Codex |
| v1.1.390 | 2026-06-17 | AI 助手围绕已引用运行记录的失败诊断和上次成功对比支持短追问，无需再次写出“任务/作业/运行”关键词 | Codex |
| v1.1.389 | 2026-06-17 | AI 助手工作台侧栏接入当前用户效果指标，按需展示草案、引用、运行成功和失败修复指标 | Codex |
| v1.1.388 | 2026-06-17 | AI 助手支持围绕失败定时作业运行生成结果动作修复草案，确认前仅写入服务端草案 | Codex |
| v1.1.387 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 优先使用完整 @ 名称精确命中，避免相近作业或前端自动候选引用导致不执行或执行错作业 | Codex |
| v1.1.386 | 2026-06-17 | AI 助手支持围绕一次定时作业运行追问“和上次成功有什么不同”，返回运行对比工具结果和前端对比卡片 | Codex |
| v1.1.385 | 2026-06-17 | AI 助手运行失败诊断接入结果写入记录，结果动作段返回写入目标、写入状态和记录 ID | Codex |
| v1.1.384 | 2026-06-17 | AI 助手服务端草案补齐 `expired` 生命周期、过期预检和效果指标过期草案口径 | Codex |
| v1.1.383 | 2026-06-17 | AI 助手草案模板市场的线上日志异常分析模板接入真实定时作业草案生成链路，并复用服务端定时作业模板目录 | Codex |
| v1.1.382 | 2026-06-17 | AI 助手手动触发 AI 类定时作业时先返回运行中记录，避免聊天请求等待完整外部取数、模型处理和结果写入 | Codex |
| v1.1.381 | 2026-06-17 | AI 助手新增分析类服务端草案，发布风险分析和知识库巡检可生成、确认并追踪助手分析结果 | Codex |
| v1.1.380 | 2026-06-17 | AI 助手邮件摘要草案接入真实定时作业生成链路，聊天可生成绑定邮件收取动作和邮箱连接的服务端草案 | Codex |
| v1.1.379 | 2026-06-17 | AI 助手新增服务端草案模板市场目录，前端侧栏可按模板回填草案提示并显示角色、依赖、流程和接入状态 | Codex |
| v1.1.378 | 2026-06-17 | AI 助手效果指标补齐定时作业运行成功率、失败复跑修复率和知识引用命中率口径 | Codex |
| v1.1.377 | 2026-06-17 | AI 助手新增效果指标接口，按当前用户统计草案采纳、用户修改、动作运行成功和显式引用使用情况 | Codex |
| v1.1.376 | 2026-06-16 | AI 执行器列表新增测试诊断能力，管理员可检测系统默认执行器和本地 Runner 健康项并写入审计 | Codex |
| v1.1.375 | 2026-06-16 | 插件连接新增“保存并测试”交互，连接弹窗保存成功后复用返回连接 ID 调用现有测试诊断接口 | Codex |
| v1.1.374 | 2026-06-16 | AI 执行器 Runner 安装包补充 START_STOP.md 启停说明，明确页面停用与本机进程停止的边界 | Codex |
| v1.1.373 | 2026-06-16 | AI 执行器 Runner 安装包按 Linux、macOS、Windows、Docker 和通用手动安装拆分资产，并在 Runner 元数据中保存目标系统、CPU 架构和安装模式 | Codex |
| v1.1.372 | 2026-06-16 | AI 执行器 Runner 增加远程安装包和 Skill 分发契约，配置 Codex、Claude Code、Hermes、OpenClaw 命令参数并通过 ZIP 下载 | Codex |
| v1.1.371 | 2026-06-16 | 代码巡检 native 扫描支持产品仓库 credential_ref 的 Git askpass 拉取，并在 AI 后处理后保留扫描快照元数据 | Codex |
| v1.1.370 | 2026-06-16 | 代码巡检 native 扫描补充外部引擎实际执行/解析、scan_profile 引擎状态和异步取消保护 | Codex |
| v1.1.369 | 2026-06-16 | 代码巡检报告增强 baseline/质量门禁、多仓库批量扫描、详情聚合、上次扫描对比和对应持久化字段 | Codex |
| v1.1.368 | 2026-06-16 | 代码巡检本地扫描升级为固定工作区 + mirror 缓存 + 运行快照 + 异步 worker；补充规则配置、忽略机制、增量扫描和报告详情快照字段 | Codex |
| v1.1.367 | 2026-06-15 | 代码巡检支持本地完整静态扫描：`native_full_scan` 作业可 clone 产品 Git 仓库、按分支扫描内置规则、记录扫描覆盖率并回填提交人 | Codex |
| v1.1.366 | 2026-06-15 | 代码巡检作业新增显式扫描分支契约：作业按产品 Git 仓库维护 `config_json.repository_id/branch`，未填写分支时默认取仓库 `default_branch`，插件输入和 AI 上下文同步携带分支 | Codex |
| v1.1.365 | 2026-06-15 | 代码巡检仓库绑定和插件调用日志脱敏修复：AI 输出 GitLab project_path 时优先映射到产品 Git 仓库，模型上下文注入配置仓库 ID，插件调用日志 request_summary 落库与返回均脱敏敏感 Header | Codex |
| v1.1.364 | 2026-06-15 | AI 助手显式引用扩展到定时作业、运行记录、插件动作、AI角色和 Skill，并新增定时作业运行失败三段诊断工具结果 | Codex |
| v1.1.363 | 2026-06-14 | AI 助手工作台 P0 能力落地：`@` 知识文档显式引用、引用候选/解析接口、知识 chunk 注入、服务端动作草案持久化和确认/取消闭环 | Codex |
| v1.1.362 | 2026-06-14 | MaxCompute 不再作为官方标准插件和官方动作模板维护；历史官方 MaxCompute 自动降级为普通 HTTP 插件，连接编辑仅保留通用配置 | Codex |
| v1.1.361 | 2026-06-14 | GitLab 官方连接支持本地项目地址单字段配置：页面填写 GitLab 地址，系统自动同步 endpoint 并解析 project_id/project_path，Project ID / Group ID / API 版本不再作为用户手填字段 | Codex |
| v1.1.360 | 2026-06-14 | 系统菜单管理落地：`menu_resources` 由数据库维护菜单元数据、排序、启停和页面访问权限点，系统管理新增菜单管理页；前端仍以静态路由注册表限制可加载页面组件 | Codex |
| v1.1.359 | 2026-06-14 | 定时作业多连接/多动作配置契约：前端表单和列表支持多选展示，后端接收 `plugin_connection_ids` / `plugin_action_ids` 并持久化到 `config_json.orchestration`，旧单字段保留第一项兼容现有运行入口 | Codex |
| v1.1.358 | 2026-06-14 | 定时作业页面配置链路收口：新增/编辑表单按基础信息、数据连接、AI执行、动作和调度分区，列表合并展示“数据连接 / AI执行 / 动作”，运行详情展示运行链路 | Codex |
| v1.1.357 | 2026-06-14 | 定时作业表单调度配置优化：`schedule_type`、`cron_expression`、`interval_seconds` 连续展示，`source_system` 改为模板/审计内部标识并隐藏提交 | Codex |
| v1.1.356 | 2026-06-14 | AI 能力配置用户侧命名调整为“AI角色”：前端、定时作业、AI 助手草案和文档展示统一使用 AI角色，后端继续保留 `ai_agents` / `agent_id` / `resolved_agent_snapshot` 技术契约 | Codex |
| v1.1.355 | 2026-06-14 | 定时作业同步系统默认执行器：AI 执行器仓库任务模板默认携带 `config_json.ai_executor`，前端保存保留模板 JSON，运行节点透传 `model_gateway_log_id` 和执行结果摘要 | Codex |
| v1.1.354 | 2026-06-14 | AI 执行器新增系统默认执行器：`model_gateway` 作为平台托管执行器类型，列表只读展示 `ai_executor_runner_system_default`，动作调用可直接走系统默认模型并返回执行结果；本地 Runner 仍用于 Codex/Claude/Hermes/OpenClaw | Codex |
| v1.1.353 | 2026-06-14 | 插件管理用户侧命名统一为“动作”，配置页、市场统计、删除占用提示和模板说明不再使用“执行”代指动作；AI 执行器概念保持独立 | Codex |
| v1.1.352 | 2026-06-14 | 导航与插件日志边界调整：研发任务菜单归入需求交付，任务中心聚焦配置和定时作业；插件管理移除独立调用日志页签，调用日志在定时作业运行详情体现 | Codex |
| v1.1.351 | 2026-06-13 | Runner 控制补齐 Token 轮换、任务日志、取消和超时熔断；成功运行可反向生成模板，运行详情新增 Trace DAG | Codex |
| v1.1.350 | 2026-06-13 | 任务编排平台升级：官方插件连接 schema、定时作业向导模板、Runner 健康/启动命令和代码巡检整改任务闭环纳入规格 | Codex |
| v1.1.349 | 2026-06-13 | AI 执行器 Runner 数据模型与轮询协议落地，支持 OpenClaw，Runner 完成回写会更新插件日志、定时作业运行和执行器节点 | Codex |
| v1.1.348 | 2026-06-13 | 结果写入记录读模型归入定时作业运行详情，支持按 `scheduled_job_run_id` 精确查看单次运行写入反馈 | Codex |
| v1.1.347 | 2026-06-13 | 新增通用结果写入记录读模型和插件管理结果记录页签，支持按 `write_target` 查看邮件通知及未来扩展目标反馈 | Codex |
| v1.1.346 | 2026-06-13 | 官方插件模板补充 AI 执行器和邮箱收发能力：`ai_executor` 提供 Codex/Claude/Hermes/OpenClaw Runner 连接契约，邮箱模板补齐 SMTP/IMAP/POP3/API 参数和邮件收取动作 | Codex |
| v1.1.345 | 2026-06-13 | 官方插件连接模板收口到 `plugin_templates` 服务端目录，插件市场返回 `connection_defaults/connection_template_version`，页面和助手共用连接草案 payload | Codex |
| v1.1.344 | 2026-06-13 | 定时作业模板市场化收口：新增 `scheduled_job_templates` 服务端目录，页面和助手复用模板包的默认 payload、资源选择规则和版本 | Codex |
| v1.1.343 | 2026-06-13 | 后端定时作业模块继续收口：执行期节点追踪、插件写入预览、代码巡检节点摘要和 AI 处理判断迁移到独立 `scheduled_job_execution_engine` service | Codex |
| v1.1.342 | 2026-06-13 | 后端助手模块继续收口：插件连接、动作、定时作业和代码巡检配置草案构造迁移到独立 `assistant_draft_builder` service | Codex |
| v1.1.341 | 2026-06-13 | 后端插件模块继续收口：连接测试诊断、请求回放、动作草案、修复建议和测试历史构造迁移到独立 `connection_diagnostics` service | Codex |
| v1.1.340 | 2026-06-13 | AI 助手动作草案展示收口到结果写入目标注册表，中文写入目标标签不再由前端本地映射维护 | Codex |
| v1.1.339 | 2026-06-13 | 后端模块收口：定时作业运行可观测性聚合迁移到独立 `scheduled_job_observability` service，避免继续堆入执行服务 | Codex |
| v1.1.338 | 2026-06-13 | 定时作业运行记录新增运行健康概览接口和页面摘要，聚合成功率、失败原因、耗时、AI/Token/插件调用和动作写入成功率 | Codex |
| v1.1.337 | 2026-06-13 | 定时作业运行节点摘要补齐请求方法、URL、HTTP 状态、耗时和业务记录 ID；插件连接测试历史支持展开查看完整请求响应和动作模板草案 | Codex |
| v1.1.336 | 2026-06-13 | 动作模板唯一来源补齐：前端和助手去除官方动作硬编码兜底，模板缺失时不生成可保存动作 | Codex |
| v1.1.335 | 2026-06-13 | 代码巡检治理概览新增聚合接口和页面概览，按当前筛选展示趋势、规则、排行和严重问题 SLA | Codex |
| v1.1.334 | 2026-06-13 | 新增结果写入目标注册表模块，动作表单和写入预览统一使用服务端目标定义、默认映射和可视化字段 | Codex |
| v1.1.333 | 2026-06-13 | 插件连接测试增加 `test_history`、动作模板草案、失败修复建议和变量解析前后差异展示，形成请求回放台 | Codex |
| v1.1.332 | 2026-06-13 | 定时作业表单新增四段式编排视图，基于表单选择实时展示数据连接、AI 处理、知识引用和结果动作状态，并在数据连接节点调用连接测试 | Codex |
| v1.1.331 | 2026-06-13 | 动作模板目录收口为 `plugin_templates` 深模块，模板返回 `template_version`，AI 助手动作草案复用同一模板目录生成 payload | Codex |
| v1.1.330 | 2026-06-13 | 动作模板目录服务端化，前端新增动作表单按模板动态回填请求配置和结果映射 | Codex |
| v1.1.329 | 2026-06-13 | 插件连接测试结果沉淀为 `last_test_summary`，连接列表展示最近测试状态、耗时和错误码 | Codex |
| v1.1.328 | 2026-06-13 | 定时作业复跑运行投影补充 `source_run_summary`，详情页展示来源运行与本次运行对比摘要 | Codex |
| v1.1.327 | 2026-06-12 | 定时作业正式运行复用动作写入预览，邮件通知结果动作在运行详情展示投递 ID、状态和收件人 | Codex |
| v1.1.326 | 2026-06-12 | AI 助手邮箱通知动作草案同步使用 `email_notifications` 映射，草案卡片按中文展示写入目标 | Codex |
| v1.1.325 | 2026-06-12 | 动作补充 `email_notifications` 写入目标，邮箱通知模板和试运行预览展示投递反馈字段 | Codex |
| v1.1.324 | 2026-06-12 | 代码巡检来源链路增加页面跳转：报告详情可跳转来源作业和来源运行，定时作业页支持 `run_id` 深链打开运行详情 | Codex |
| v1.1.323 | 2026-06-12 | 代码巡检报告补充动作和数据连接来源字段，详情页展示来源作业、运行、连接、动作和插件调用链路 | Codex |
| v1.1.322 | 2026-06-12 | AI 助手草案组前端增加临时解析映射，连接/动作保存后可自动回填后续动作/作业草案的真实 ID | Codex |
| v1.1.321 | 2026-06-12 | AI 助手代码巡检配置草案组增强：缺少官方连接或动作时返回连接、动作和作业三类待确认草案 | Codex |
| v1.1.320 | 2026-06-12 | AI 助手新增官方插件连接草案，支持生成 GitHub/GitLab/邮箱 `create_plugin_connection` payload 并带入插件管理新增连接表单 | Codex |
| v1.1.319 | 2026-06-12 | 采集运行记录约束补齐定时作业运行类型，避免 dashboard/lifecycle/plugin/pending 等作业运行写入 `collector_runs` 时触发旧库约束错误 | Codex |
| v1.1.318 | 2026-06-12 | 定时作业模板来源可视化：作业列表、复制弹窗和运行详情展示 `template_source` | Codex |
| v1.1.317 | 2026-06-12 | 定时作业新增模板化复制：可从作业或运行快照生成新作业草稿，并审计 `template_source` | Codex |
| v1.1.316 | 2026-06-12 | 插件连接测试 request_summary 增加原始请求配置，动态变量解析区块无变量时也显示空状态 | Codex |
| v1.1.315 | 2026-06-12 | 插件连接测试 request_summary 增加动态变量解析明细，前端请求调试台展示表达式、偏移和解析值 | Codex |
| v1.1.314 | 2026-06-12 | 定时作业运行记录复跑补充 `source_run_id`，运行实例、页面详情和终态审计均可追踪来源运行 | Codex |
| v1.1.313 | 2026-06-12 | AI 助手新增官方动作草案，支持生成 GitHub/GitLab 代码巡检和邮箱通知 `create_plugin_action` payload 并带入插件管理表单 | Codex |
| v1.1.312 | 2026-06-12 | 动作试运行补充 `plugin_action.trial_*` 审计事件，保存动作、连接环境、写入目标和状态等轻量上下文 | Codex |
| v1.1.311 | 2026-06-12 | 官方插件市场前端补充动作模板入口，GitHub/GitLab/邮箱市场项可直接创建对应官方动作模板 | Codex |
| v1.1.310 | 2026-06-12 | AI 助手代码巡检定时作业草案支持按用户意图生成 AI 执行模式，并在草案卡片展示模型、Agent 和 Skill 装配 | Codex |
| v1.1.309 | 2026-06-12 | 定时作业运行终态审计继续补齐 AI、插件、连接环境、知识引用和结果写入目标轻量上下文，支持多环境排障与治理追踪 | Codex |
| v1.1.308 | 2026-06-12 | 定时作业前端 AI 装配校验按执行模式触发，非固定 AI 作业切换为 `ai_assisted/ai_generated` 时也必须选择模型、Agent 和 Skill | Codex |
| v1.1.307 | 2026-06-12 | 定时作业表单增加连接环境筛选，按 `default/dev/test/staging/prod/sandbox` 过滤数据连接选项，筛选值不进入作业配置 | Codex |
| v1.1.306 | 2026-06-12 | 代码巡检定时作业支持 AI 执行模式：模型先归一化插件扫描结果，再由结果动作写入代码巡检报告，运行详情保留三段式节点 | Codex |
| v1.1.305 | 2026-06-12 | 插件连接列表和 API 支持按环境筛选，后端校验 `default/dev/test/staging/prod/sandbox` 枚举并在查询层过滤 | Codex |
| v1.1.304 | 2026-06-12 | 插件管理新增官方插件市场只读目录：展示标准插件推荐场景、动作模板、安装状态和运行配置数量，并引导创建连接 | Codex |
| v1.1.303 | 2026-06-12 | 定时作业运行终态审计 payload 补充触发方式、运行状态、导入数量、collector run、插件调用和产品上下文 | Codex |
| v1.1.302 | 2026-06-12 | 定时作业运行触发方式收敛为 `manual/manual_rerun/scheduler` 枚举，复跑写入 `manual_rerun` 便于审计和排障 | Codex |
| v1.1.301 | 2026-06-12 | 插件连接测试 `request_summary` 新增可复制 cURL，页面请求调试台展示完整复现命令 | Codex |
| v1.1.300 | 2026-06-12 | 定时作业保存 AI 助手草案来源时，将草案 ID、来源和标题写入作业配置与 `scheduled_job.created/updated` 审计 payload | Codex |
| v1.1.299 | 2026-06-12 | AI 助手定时作业草案可传递到任务中心新增作业表单，用户确认保存时保留草案映射 | Codex |
| v1.1.298 | 2026-06-12 | AI 助手页面消费 `assistant.action_draft` 工具结果，以待确认配置草案卡片展示定时作业核心配置 | Codex |
| v1.1.297 | 2026-06-12 | AI 助手工具结果新增定时作业配置草案：周反馈洞察和代码巡检请求返回 `assistant.action_draft`，确认前不写 `scheduled_jobs` | Codex |
| v1.1.296 | 2026-06-12 | 定时作业新增场景模板：周反馈洞察和代码巡检模板自动带出连接、AI 能力、调度、动态变量映射和结果动作 | Codex |
| v1.1.295 | 2026-06-12 | 动作补充邮箱通知发送场景模板，自动带出官方邮箱插件、邮件发送路径、Content-Type 和默认通知参数 | Codex |
| v1.1.294 | 2026-06-12 | 动作试运行响应和页面补充 `write_preview`，展示结果动作写入目标、候选数量和样例数据 | Codex |
| v1.1.293 | 2026-06-12 | 代码巡检报告写入支持运行时应用动作 `result_mapping`，可从嵌套响应或 `$` 根数组提取 finding | Codex |
| v1.1.292 | 2026-06-12 | 动作补充 GitHub/GitLab 代码巡检场景模板，自动带出官方插件、请求路径、默认 Params 和巡检报告映射 | Codex |
| v1.1.291 | 2026-06-12 | 定时作业运行记录增加复跑入口：运行记录操作列可基于原作业重新触发并展示新运行详情 | Codex |
| v1.1.290 | 2026-06-11 | 收紧定时 AI 作业校验并增强前端可观测性：AI 类型作业强制 Agent/Skill/模型网关，运行详情展示三段执行链路卡片，连接测试展示请求调试台 | Codex |
| v1.1.289 | 2026-06-11 | 动作结果写入目标补充 `code_inspection_reports`，新增代码巡检报告 JSONPath 可视化字段 | Codex |
| v1.1.288 | 2026-06-11 | 代码巡检结果新增提交人维度、产品范围读取控制、扫描器 severity mapping、严重问题 Bug 去重和结果动作状态摘要 | Codex |
| v1.1.287 | 2026-06-11 | 同步代码仓库巡检技术规格：`code_repository_inspection` 定时作业支持多结果动作，写入代码巡检报告、自动创建严重问题 Bug 并记录邮件/钉钉通知反馈 | Codex |
| v1.1.286 | 2026-06-11 | 新增 AI 助手工作台升级整体方案：通过 `@` 显式引用知识库、业务对象、插件、AI 能力和定时任务，并在助理内生成可确认的配置/动作草案 | Codex |
| v1.1.285 | 2026-06-11 | 定时作业配置和执行链路校正：表单按数据连接、AI 模型、Agent、Skills、结果动作排序，用户反馈洞察抽取必须经过模型网关处理后再执行结果动作 | Codex |
| v1.1.284 | 2026-06-11 | 定时作业运行结果详情补齐三段核心节点：数据连接获取内容、Skill 处理内容、结果动作反馈内容，并在 Skill 节点展示模型调用状态 | Codex |
| v1.1.283 | 2026-06-11 | 定时作业运行记录增强：列表提供运行结果详情入口，手动触发后展示本次结果摘要、插件调用、Skill/Prompt 快照、作业配置快照和错误信息 | Codex |
| v1.1.282 | 2026-06-11 | 插件管理删除闭环增强：插件、连接和动作列表提供删除入口，删除前提示使用清单；后端在被连接、动作、定时作业或调用日志引用时返回 409 | Codex |
| v1.1.281 | 2026-06-11 | 定时作业维护闭环增强：作业列表提供编辑和删除入口，编辑回填调度/插件/AI 装配配置，删除通过 DELETE 接口写入审计 | Codex |
| v1.1.278 | 2026-06-11 | 插件管理维护闭环增强：插件、连接和动作列表提供编辑入口，PATCH 编辑保留服务端脱敏密钥，连接/动作 Params 与 Headers 可继续可视化维护 | Codex |
| v1.1.279 | 2026-06-11 | 明确插件任务链路为数据连接取数、Skill 分析处理、结果动作写入；动作 `result_mapping.write_target` 提供可视化写入目标，定时作业输出映射为空时复用动作结果映射 | Codex |
| v1.1.280 | 2026-06-11 | 补充动作写入目标表单联动：前端必须按 `write_target` 动态展示对应 JSONPath 字段，并与高级 `result_mapping` JSON 双向同步 | Codex |
| v1.1.277 | 2026-06-11 | 知识管理可靠性增强：导入 worker 使用 PostgreSQL 租约 claim，目录归档按子树生效，资产按 bucket/object_key 幂等 upsert，chunk set 保存索引状态用于回滚 | Codex |
| v1.1.275 | 2026-06-11 | OCR JSON chunk 来源元数据补齐页内图片数量、表格数量和图片引用，知识中心 chunk 预览展示图片来源 | Codex |
| v1.1.274 | 2026-06-11 | 知识导入新增 regex_section 正则分块策略，按结构分隔符切分并保留分段标题和切分规则元数据 | Codex |
| v1.1.273 | 2026-06-11 | 知识中心导入任务弹窗展示后台 worker 状态，chunk 预览展示 OCR/Table 页码、表格和来源资产元数据 | Codex |
| v1.1.272 | 2026-06-11 | 知识 chunk 版本化约束收口：数据库移除旧单文档 chunk_index 唯一约束，改为按 chunk set 维度约束 chunk 序号 | Codex |
| v1.1.271 | 2026-06-11 | 知识导入 worker 补偿扫描 queued 任务时使用导入任务创建人执行写入，确保 chunk set 创建人、审计归属和 PostgreSQL 用户外键一致 | Codex |
| v1.1.270 | 2026-06-11 | 知识导入解析产物拆分增强：OCR JSON / Table JSON 生成结构化 sidecar 资产和 parsed Markdown，并把页码/表格来源写入 chunk metadata | Codex |
| v1.1.269 | 2026-06-11 | 知识导入任务补齐应用内后台 worker/队列：上传、重解析和重试自动入队，启动时补偿 queued 任务，并保留 run 作为运维补偿入口 | Codex |
| v1.1.268 | 2026-06-10 | 知识管理第一阶段实现落地：知识空间、目录、MinIO/S3-compatible 资产、导入任务、chunk set、上传预览和空间权限过滤进入当前架构 | Codex |
| v1.1.267 | 2026-06-10 | 新增知识管理升级设计：明确知识空间、目录、文档、MinIO 资产、导入任务、解析器适配、父子分块、权限过滤和分阶段实施边界 | Codex |
| v1.1.266 | 2026-06-10 | 补充 MaxCompute 用户反馈洞察抽取实现：`user_feedback_insight_extract` 定时作业消费插件返回 `$.insights` 并通过用户反馈 service 写入，动作页面支持场景模板和高级 JSON 编辑 | Codex |
| v1.1.278 | 2026-06-11 | 增强插件连接测试诊断：完整展示最终请求 URL、query、headers 明文值、Header 来源和远端响应摘要，对 `***` 占位做诊断标记并明确认证 Header 优先级 | Codex |
| v1.1.277 | 2026-06-11 | 补充插件连接级请求配置：`plugin_connections.request_config` 保存公共 Params/Headers，运行时与动作 `request_config` 合并且动作覆盖同名 query/header | Codex |
| v1.1.276 | 2026-06-11 | 补充插件配置体验优化：连接测试诊断报告、系统变量预览、动作请求预览/试运行、可视化参数与 JSON 双向同步、定时作业插件输入映射表格化 | Codex |
| v1.1.265 | 2026-06-10 | 新增插件管理第一阶段实现：补充 `integration_plugins`、`plugin_connections`、`plugin_actions`、`plugin_invocation_logs` 数据模型，定时作业可通过动作调用 HTTP/MCP HTTP 集成并保存插件快照、调用日志和审计 | Codex |
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

企业 AI 大脑平台 v1 系列采用基于 Ant Design Pro 模板的 React + TypeScript 前端、FastAPI 后端、LangGraph 工作流、PostgreSQL + pgvector 知识存储、Redis 缓存/队列、GBrain 长期记忆层和 OpenAI-compatible 模型网关，先以模块化单体跑通产品研发大脑从需求审批到产品详细设计、技术方案、GitLab MR / GitHub PR 代码 Review、人工确认、内部报告归档和知识沉淀的 MVP 闭环，并通过研发上下文图谱感知需求、设计、代码、测试、发布、线上反馈、用户使用和用户反馈之间的关联与风险。AI 助手工作台已接入模型网关 Chat 能力，聊天前由后端按用户问题生成 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等确定性 read-model 工具结果，模型优先依据 `system_context.tool_results` 回答 AI Brain 产品配置、需求/任务进展、迭代、Git 仓库、代码评审和模型网关状态问题；助手服务同时生成产品、迭代、需求、任务、Review、Bug、代码评审和知识沉淀引用候选，回答消息持久化 `references` 与 `tool_results` 并在前端展示可跳转来源链接。GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属数据队列、基于反馈/Bug 的迭代规划建议、开发计划、自动化测试、发布上线评估、上线后分析基础闭环、代码仓库质量/安全/规范巡检和生命周期 v1.2 真实证据扩展已进入当前实现；外部自动采集器和真实外部系统双向写回按后续阶段确认后推进。后续定时采集、AI 日志分析、AI 迭代建议、代码仓库巡检和看板刷新统一通过 `scheduled_jobs` 调度定义、`scheduled_job_runs` 运行实例、`collector_runs` 采集台账和 `ai_agents` / `ai_skills` 能力装配完成，用户侧将 `ai_agents` 展示为“AI角色”，每次运行必须保存解析后的 AI角色（Agent）、Skill、模型网关、Prompt、输出 Schema、工具策略和上下文范围快照；其中 `code_repository_inspection` 可通过内置本地扫描器或动作调用 GitLab/GitHub/SonarQube/SAST、自建扫描服务，按 `result_actions` 依次写入代码巡检报告、派生严重问题 Bug，并记录邮件、钉钉机器人等通知反馈。需求交付下的研发执行器策略与定时作业 AI 装配分离：策略只引用插件管理下的 Codex、Claude Code、OpenClaw Runner、仓库工作区和指令模板，不使用 Agent/Skill。定时作业定义支持多数据连接与多动作配置，完整数组保存在 `config_json.orchestration.plugin_connection_ids` 和 `config_json.orchestration.plugin_action_ids`，响应同时展开为顶层数组字段；`plugin_connection_id` / `plugin_action_id` 仍作为第一项兼容字段供现有执行入口、报表来源链路和旧客户端消费。

## AI 助手工作台升级

AI 助手正在从只读问答页升级为统一工作台。整体目标仍详见 [AI 助手工作台升级整体方案](assistant-workbench-upgrade-design.md)：用户可在输入框通过 `@` 显式引用产品、需求、AI 任务、Bug、知识空间/目录/文档/chunk、插件、动作、AI角色/Skill、模型网关配置、定时作业和运行实例；后端必须先解析引用、校验权限、构造脱敏上下文，再进入模型网关调用或动作草案生成。知识库引入遵守显式范围、权限过滤和限量注入，完整知识正文不得写入模型日志。

当前 P0 已落地 `knowledge_space`、`knowledge_folder`、`knowledge_document` 和 `knowledge_chunk` 显式引用：前端在 AI 助手输入框输入 `@` 后调用 `/api/assistant/reference-candidates` 拉取当前用户可读且可检索的知识空间、知识目录、知识文档与知识片段候选。聊天框上方“本次上下文”区域必须常驻展示；未选择显式引用时显示 `0 个显式引用`、`0 个知识 chunk 注入模型`、`未注入知识正文` 和“仅使用系统上下文和当前会话”，避免用户误以为隐藏区域代表上下文不可控；选择引用后展示引用类型、来源模块、权限状态、更新时间、知识 chunk 注入状态和轻量摘要，并提供“查看摘要”弹窗，仅展示引用类型、来源、权限、更新时间、注入口径和摘要元数据，不展示完整知识正文；引用同时随 `/api/assistant/chat.references` 提交结构化 ID。管理员输入“定时作业/定时任务”等类型词时，候选优先返回 `scheduled_job` 作业定义；输入“运行记录/失败”等执行结果词时，候选优先返回 `scheduled_job_run` 运行实例，避免配置对象和执行结果混淆。当知识空间、知识目录或文档候选 `chunk_count` 超过后端上下文注入上限时，前端必须显示“最多 8 个知识 chunk 将按权限注入模型”，不得用范围内总 chunk 数暗示整篇空间、目录或文档会全量进入模型。后端通过 `/api/assistant/references/resolve` 和聊天前解析流程校验引用，未授权、不可读、不可检索或不存在的知识空间/目录/文档/片段返回 `REFERENCE_NOT_FOUND`，不得进入模型上下文。引用知识空间或知识目录时，聊天调用会按权限读取该范围内已索引文档的有限数量知识 chunk 写入 `system_context.knowledge_context`；引用文档时，聊天调用会按权限读取有限数量的知识 chunk；引用具体 `knowledge_chunk` 时只注入被选中的单个片段，避免整篇文档或整个知识空间被误带入上下文。助手消息只持久化引用元数据和工具结果，模型日志继续只记录 provider、model、purpose、tokens、latency、status 和 error 等脱敏元数据，不保存完整知识正文。

显式引用候选已继续扩展到研发业务对象、受控运维配置对象和命令面板动作入口：所有助手用户可按产品上下文引用 `product`、`iteration_version`、`requirement`、`ai_task`、`human_review`、`bug`、`code_review_report`、`knowledge_deposit`、可读 `knowledge_space`、可读 `knowledge_folder`、可读 `knowledge_document` 和可读 `knowledge_chunk`；运维配置引用按对象类型要求管理员、`system.admin` 或对应专项权限：`scheduled_job` / `scheduled_job_run` 需要 `system.scheduled_jobs.run` 或 `system.scheduled_jobs.manage`，`plugin_action` / `plugin_connection` 需要 `system.plugins.manage`，`ai_agent` / `ai_skill` 需要 `system.ai_capabilities.manage`。`assistant_action` 是非上下文引用的动作入口，输入 `@新建`、`@新增` 或 `@创建` 时，后端按当前用户角色与专项权限返回“新建需求”“新建 Bug”“新建插件连接”“新建插件动作”“新建定时作业”“新建知识文档/导入任务”“新建 AI 能力配置”等候选，候选携带可编辑 `prompt` 作为动作说明和草案提示来源；前端点击后必须在输入框头部保留由候选标题生成的 `@动作名` 命令前缀（例如 `@新建需求 `），并把用户已在当前 `@` 片段之后输入的正文承接在前缀后，不得用候选 `prompt` 覆盖用户输入。动作候选选择后只关闭候选面板，不加入“本次上下文”、不写入最近引用、不提交 `references[]`。定时作业和运行记录候选还必须按当前用户 `scope_summary` 中的产品范围过滤：管理员、`system.admin`、全局 scope 或历史无 scope 用户可见全局候选；只有产品级 scope 的用户只可见对应产品的作业和运行，避免具备执行权限但跨产品看到不属于自己范围的运营对象。候选项 `permission_label` 必须显示实际授权来源：管理员或 `system.admin` 显示“管理员可引用”，通过专项权限开放的运维候选显示“定时作业执行权限可引用”“定时作业管理权限可引用”“插件管理权限可引用”或“AI能力管理权限可引用”，动作入口显示“可执行”，不得统一误标为“管理员可引用”。前端 `@` 查询不再固定为知识文档类型，会展示引用类型标签并提交 `{type,id}`；用户侧标签必须把 `assistant_action` 展示为“动作”、`ai_task` 展示为“研发任务”、`ai_skill` 展示为“Skill”，避免与泛化任务或 AI 能力配置页入口混淆；输入裸 `@` 或未指定 `type` 拉取默认候选时，前端必须请求足够数量的候选，后端必须按类型均衡合并默认候选，优先保证动作入口、知识空间、知识目录、知识文档、需求、研发任务、定时作业、运行记录、插件动作、插件连接、AI角色和 Skill 等类型都有机会展示，避免知识文档数量过多时挤掉可执行对象。候选面板无匹配项时必须继续保持可见，并提供可操作下一步；对 `@... 执行一次` 这类定时作业手动运行场景，空态必须明确“没有找到可执行的定时作业引用”，同时提供跳转任务中心新增定时作业和让 AI 生成可确认任务草案的入口，避免用户把空候选误解为 @ 功能无响应。已选择或发送过的引用会记录为本地“最近使用”，但仅在该对象仍出现在当前后端候选结果中时置顶展示，不能绕过后端权限过滤；动作入口不进入最近引用。后端候选和解析都按当前用户权限过滤，未授权用户提交配置/运行类结构化引用时返回空候选或 `REFERENCE_NOT_FOUND`；显式 `@定时作业名称 执行一次` 命令可由管理员、`system.admin`、`system.scheduled_jobs.run` 或 `system.scheduled_jobs.manage` 权限用户触发，缺少权限时必须返回 `assistant.scheduled_job_run summary.status=permission_denied`，说明需要 `system.scheduled_jobs.run` 定时作业执行权限，不得伪装成未找到唯一匹配作业。

`assistant_action` 默认并入候选时必须满足 query 包含“新建/新增/创建/配置”等动作触发词，或客户端显式传入 `type=assistant_action`。裸 `@`、`@定时作业`、`@运行记录` 等对象引用查询应继续优先展示已有对象，避免动作入口抢占引用路径。

AI 助手侧栏提供“草案模板市场”显式入口，前端点击后调用 `GET /api/assistant/draft-templates` 拉取服务端目录，不在页面硬编码模板。模板目录按当前用户角色过滤，管理员可见全部；每个模板返回 `code/name/category/description/prompt/roles/source_module/draft_action/target_resource/dependencies/wizard_steps/template_version/available`。首批模板覆盖周反馈洞察、代码巡检、邮件摘要、发布风险分析、知识库巡检和线上日志异常分析；其中发布风险分析模板必须对产品负责人、评审人、测试负责人、测试人员和发布负责人可见，与角色快捷入口中的“发布风险”保持一致。模板市场 `wizard_steps` 必须统一为“数据来源、AI处理、结果动作、调度策略、确认执行”五步；知识引用作为 AI 处理阶段的可选上下文说明和依赖元数据展示，不作为单独流程步骤，避免用户在模板市场、任务引导和草案卡片之间看到不同闭环流程。首批六类官方模板均必须返回 `available=true`，前端全部显示“可生成草案”并允许点击使用；依赖缺失由后续草案向导或前置草案链处理，不得再以“暂未完整接入”禁用模板。前端以模板卡片展示依赖和流程，点击模板只回填聊天输入框，由用户确认发送后再生成草案或分析，不直接写配置或触发外部动作。

AI 助手侧栏提供角色化快捷任务入口，后端优先从 `assistant_role_quick_tasks` 配置表读取任务组和任务项，按当前登录用户角色、任务启用状态、权限、企业、模板版本、`rollout_json` 灰度策略和排序返回；只有配置表没有任何记录时才使用内置默认目录作为兼容兜底，若配置存在但当前用户被企业/版本/灰度过滤掉，则不回退默认目录。配置表支持 `enterprise_id`、`group_roles`、`permissions`、`template_version`、`rollout_json`、`enabled` 和排序字段，管理员可通过 `/api/assistant/role-quick-task-configs` 新增/编辑配置，通过 `/status` 启停任务项或任务组，通过 `/rollout` 调整企业、模板版本和灰度策略；每次创建、更新、启停、灰度调整和删除必须写入 `assistant_role_quick_task.*` 审计事件。默认目录中 `product_owner` 看到产品快捷任务（需求进展、反馈洞察、版本风险），`rd_owner` 看到研发快捷任务（任务阻塞、代码巡检、缺陷修复），`reviewer`、`test_owner`、`tester`、`release_owner` 看到测试快捷任务（测试缺陷、自动化测试、发布风险），`admin` 看到管理员快捷任务（插件连接、AI能力、定时作业、运行失败）。产品快捷任务中的“反馈洞察”必须回填周反馈洞察定时作业草案提示，“版本风险”必须回填发布风险分析草案提示，让产品入口默认进入草案生成闭环而不是普通问答；测试/发布角色快捷任务中的“发布风险”也必须回填发布风险分析草案提示，复用同一 `create_analysis_draft` 路径；管理员快捷任务中的“AI能力”必须回填“我要新增 AI能力配置”，触发新增任务向导中的 AI能力配置路径，避免仍停留在检查配置的普通问答；“需求进展”仍可回填产品视角进展分析提示。后端助手 API 访问白名单必须同步包含 `reviewer/test_owner/tester/release_owner` 等测试与发布交付角色，避免页面入口可见但 `/api/assistant/conversations`、`/api/assistant/chat` 等接口返回角色拒绝；高权限运维引用仍按独立规则限制，仅管理员、`system.admin` 或对应专项权限用户可通过候选/结构化引用解析定时作业、运行记录、插件动作、插件连接、AI角色和 Skill，其中定时作业与运行记录允许 `system.scheduled_jobs.run` 或 `system.scheduled_jobs.manage`；显式 `@定时作业名称 执行一次` 允许具备 `system.scheduled_jobs.run` 或 `system.scheduled_jobs.manage` 的用户触发。快捷任务只回填聊天输入框，不自动发送、不直接写配置或触发外部动作；无匹配角色时不展示角色任务组。

AI 助手 `@` 动作候选入口同样必须服务端配置化。`assistant_action_reference_configs` 记录 `assistant_action` 候选的 `action_key/title/summary/prompt/url/aliases/roles/permissions/enabled/sort_order/template_version/enterprise_id/rollout_json`；后端候选查询优先读取该表并按角色、权限、启用状态、企业、模板版本、灰度和排序过滤。同一 `action_key` 的配置可覆盖或禁用默认动作，也可新增自定义动作；没有任何配置记录时回退内置默认候选，保证旧环境可用。具备 `assistant.action_references.manage` 权限的用户可通过 `/api/assistant/action-reference-configs` 新增、编辑、启停、调整灰度或删除配置，每次写入 `assistant_action_reference_config.*` 审计事件，不得只依赖 `admin` 角色硬编码。系统管理提供 `/system/assistant-action-references` 页面，支持搜索、分页、启停筛选、角色筛选、批量启停、配置启停、排序、角色、权限、关键词、企业、模板版本、灰度和审计跳转；页面必须只消费管理 API，不再从前端常量维护运营入口。前端 `+` 菜单和输入框 `@` 候选都只消费 `/api/assistant/reference-candidates?type=assistant_action` 返回结果，不得再硬编码动作清单。用户从输入框 `@` 候选选择已有定时作业时，输入框必须保留可继续编辑的 `@作业名称 ` 命令前缀，并同步把该作业作为结构化引用加入“本次上下文”，方便继续输入“执行一次”且避免同名作业误执行。

AI 助手页面必须在进入时调用 `GET /api/assistant/runtime-status` 获取运行环境自检。接口返回 `ready`、`mode` 和 `checks[]`；每个检查项包含 `key/status/label/detail/remediation/action_label/action_url/required/severity`，覆盖 PostgreSQL、Redis、模型网关、Embedding 网关和 GBrain 长期记忆。`ready` 只代表必需检查项可用，GBrain 长期记忆、模型网关和 Embedding 属于增强能力，未配置时不得让核心助手入口被判定为不可用。对话页默认不展开模型网关、Embedding 和 GBrain 等增强能力未配置明细，仅在 PostgreSQL、Redis 等必需依赖异常时显示轻量提醒和修复入口；确定性草案、引用解析、运行诊断等不依赖模型的能力仍可使用，开放式问答受限信息可在模型网关配置、系统状态或错误反馈中说明。

AI 助手最近对话必须支持服务端分页。`GET /api/assistant/conversations` 接受 `limit` 与 `cursor`，默认返回最新一页并带 `next_cursor`；前端侧栏首屏只展示当前页，存在 `next_cursor` 时提供“加载更多”，避免重复命令或大量历史把角色快捷任务和更多能力挤出首屏。折叠重复会话时，分页游标必须基于服务端真实排序窗口中的最后一条原始会话，而不是折叠后的最后一条，避免下一页重复或漏数据。历史消息接口返回 `assistant.action_draft` 工具结果时只允许保留渲染所需安全字段：草案 ID、标题、动作、状态、风险、有限 payload 字段、预检摘要和向导元数据；`api_key`、`auth_config`、`Authorization`、token、password、secret、cookie、private key 等敏感字段以及 preview diff 中敏感字段的 current/proposed 必须脱敏，不得因历史恢复草案而把密钥、Header 或外部请求明文暴露到前端、模型上下文或日志。

AI 助手效果指标明细必须按 `limit` 在服务端下推并只返回当前页脱敏元数据；服务端可继续计算同一筛选范围下的 `total`，但不得为了展示前 50 条而完整构造所有历史草案、运行或消息明细。前端草案卡片的次要操作（应用到表单、打开草案链接、重新生成）默认收纳到“更多”菜单，确认、取消、查看详情和资源追踪保留为主要动作；`/assistant?draft_id=...` 深链加载成功后必须滚动到草案链接状态区域，避免草案被输入框或长消息遮挡。运行状态提醒必须提供手动“重新检测”，并在窗口重新聚焦时刷新必需依赖状态，避免 Redis/PostgreSQL 修复后页面仍停留在旧错误提示。GitHub/GitLab 等语义相近的插件连接或动作草案若无法从用户文本唯一确定提供方，助手必须生成需要用户补齐 provider 的待确认草案或向导提示，不得静默默认到某一提供方。

当用户围绕一次 `scheduled_job_run` 追问“为什么失败/如何诊断”时，助手在模型调用前生成 `assistant.scheduled_job_diagnostic` 工具结果。若用户已经显式引用了 `scheduled_job_run`，后续短追问如“为什么这次失败？”也必须按该引用补足运行上下文，不要求再次出现“任务/作业/运行”关键词。诊断结果按 `data_connection`、`ai_processing`、`result_action` 三段输出状态、摘要、错误信息和关联日志 ID，来源可包括 `scheduled_job_runs.result_summary.execution_nodes`、`plugin_invocation_logs`、`model_gateway_logs` 和从运行结果派生的 `result_write_records`。数据连接段必须优先读取 `execution_nodes.data_connection.plugin_invocation_log_id`，结果动作段必须优先读取 `execution_nodes.result_action.plugin_invocation_log_id`，避免同一次运行存在取数和写入两条插件日志时只能追踪到其中一条。前端诊断卡片必须把三段状态显式呈现为“数据连接是否成功”“AI处理是否成功”“结果动作是否写入成功”的判断，并把 `succeeded/failed/running/queued/warning/skipped` 转成用户可读结果，避免用户只看到状态 Tag 后仍需要自己判断链路是否闭环；前端诊断卡片还必须在对应阶段展示安全的 `log_id`（如模型日志 ID 或插件调用日志 ID），帮助用户从对话继续追到具体日志元数据；结果动作段还必须返回 `result_write_record_id/result_write_status/result_write_target/result_write_target_label` 等安全元数据，帮助用户确认写入目标是否成功；前端诊断卡片必须把 `result_write_record_id` 链接到对应定时作业运行详情并携带写入记录 ID，定时作业页面接收 `result_write_record_id` 后必须自动打开运行详情并展开该结果写入记录，便于继续查看结果写入反馈。诊断卡片还必须提供“生成修复草案”和“对比上次成功”后续追问按钮；AI 助手内的运行记录卡片也必须提供“问这次运行”“生成修复草案”“对比上次成功”快捷追问。用户点击这些入口后，前端必须把当前 `scheduled_job_run` 重新加入“本次上下文”并回填带 `@运行记录标题` 的追问，避免用户手工复制运行 ID；若入口通过 `/assistant?reference_type=scheduled_job_run&reference_id=<run_id>&prompt=<prompt>` 打开，助手页“本次上下文”必须常驻展示该链接引用的解析状态，包括解析中、已从链接带入运行记录或引用不存在/无权限，避免只依赖临时 toast。该工具结果会随助手消息 metadata 持久化并进入模型上下文；完整插件请求/响应、Prompt、模型输出、密钥和外部系统 token 不进入模型日志。

当用户围绕已引用的 `scheduled_job_run` 继续追问“和上次成功有什么不同/对比上次成功/差异”时，助手在模型调用前生成 `assistant.scheduled_job_run_comparison` 工具结果。若用户已经显式引用运行记录，短追问“和上次成功有什么不同？”也必须命中该工具。服务端必须按同一 `scheduled_job_id` 找到该运行之前最近一次 `succeeded` 运行作为 baseline，返回当前运行、baseline 运行、状态/导入数/耗时/错误信息和三段执行节点差异；结果动作差异同样只返回写入状态、写入目标和摘要等安全元数据。前端助手气泡必须以“运行对比”卡片展示当前运行、上次成功运行和差异列表，并提供“生成修复草案”和“继续诊断”按钮，点击后带当前运行引用继续追问。

当用户围绕已引用的失败 `scheduled_job_run` 继续追问“这次失败怎么修/帮我生成修复草案/repair draft”时，助手在模型调用前生成 `assistant.action_draft` 工具结果，`intent=scheduled_job_run_repair_draft`。该工具只生成可确认的 `create_plugin_action` 服务端草案，来源字段从失败运行的 `execution_nodes.result_action`、关联 `plugin_invocation_logs` 和原插件动作配置中提取：`plugin_id`、`connection_id`、`action_type`、安全的 `request_config.method/path` 与 `result_mapping.write_target`。草案工具项必须带 `source_resource` 指向原插件动作，并持久化到服务端草案 `metadata_json.source_resource`；草案详情 `preview.target.source_resource` 必须显示来源插件动作，`preview.diffs` 必须把原动作当前值和修复草案建议值做 current/proposed 对比，帮助用户确认修复草案和当前配置的差异。草案标题应指明是原结果动作的修复草案，`client_draft_id` 应包含来源运行 ID，确认前不得修改原动作、创建真实插件动作或触发外部调用；工具结果和模型上下文不得包含完整插件请求/响应、Prompt、模型输出或密钥。

当用户在 AI 助手中通过结构化引用或显式 `@定时作业名称` 发送“执行一次/立即执行/run once”等命令时，助手必须复用定时作业手动运行链路并返回 `assistant.scheduled_job_run` 工具结果。只要请求携带结构化 `references[]` 中的 `scheduled_job`，后端必须进入 strict reference 模式并以该引用为用户主动选择的执行对象；文本 `@...` 仅在没有结构化作业引用时作为兜底解析，不得覆盖用户已选择的结构化引用。结构化引用指向停用、不可运行、无权限或不存在作业时，仍按权限和可执行状态返回明确错误或草案兜底，不得偷偷改成文本中相似的官方周反馈作业。没有结构化作业引用时，显式 `@` 文本应按完整名称、标题、编码或 ID 精确命中优先；当语义上存在多个相近作业时，只要完整 @ 名称唯一精确匹配一个作业就必须执行该作业；若 `@提取每周用户反馈有价值信息 执行一次` 等周反馈洞察别名语义命中多个 active 周反馈相关作业，后端必须优先选择官方周反馈洞察作业（例如 `code=weekly_feedback_insight`、`job_type=user_feedback_insight_extract`、`config_json.assistant_template.code=weekly_feedback_insight` 或 `source_system=aliyun-maxcompute`），避免被周反馈同步、历史分析等相近作业拖回草案。若用户缺少 `system.scheduled_jobs.run`、`system.scheduled_jobs.manage`、`system.admin` 或管理员角色，显式 @ 执行命令必须确定性返回 `assistant.scheduled_job_run`，`summary.status=permission_denied`，并在回复中说明需要 `system.scheduled_jobs.run` 定时作业执行权限，不得返回“没有找到唯一匹配”这类误导性原因。若同一作业已有 `queued/running` 运行且尚未超过作业 `lock_ttl_seconds`，助手不得重复启动后台执行，而应直接返回该运行记录、当前状态和详情链接；超过 TTL 的悬挂运行不得阻断新的“执行一次”命令。若显式 @ 已尝试解析但没有唯一可执行作业，且文本命中周反馈洞察场景，助手不得把命令交给普通模型闲聊，而应确定性返回 `assistant.action_draft intent=scheduled_job_draft`，生成 `assistant_draft_weekly_feedback_insight` 服务端草案，并在 payload 的 `config_json.assistant_run_once_request` 标记本次“执行一次”意图；确认前不得创建作业或触发外部调用。前端收到该类 run-once 草案时，草案卡片必须显示“确认后执行一次”，说明文案必须写明“确认后会立即执行一次”，确认按钮必须展示为“确认并执行一次”，让用户清楚当前命令还在等待草案确认。用户确认该类草案后，服务端必须先复用 scheduled_jobs service 创建作业，再复用手动运行链路触发一次 `manual` 运行；`assistant_action_runs.result` 必须保留创建出的作业并嵌入 `scheduled_job_run`，确认审计 payload 必须记录 `scheduled_job_run_id`，且新建运行必须持久化 `assistant_action_run_id`、`assistant_action_draft_id`、`assistant_source_message_id` 和 `triggered_by_assistant=true`，便于应用后继续跳转、诊断和按助手动作归因指标。前端草案卡片在确认成功后必须同时展示“打开定时作业”和“打开本次运行”，本次运行链接应携带 `job_id` 与 `run_id`，让用户不需要再去运行列表里搜索刚触发的执行记录。对 `user_feedback_insight_extract`、`online_log_ai_analysis`、`iteration_plan_suggestion_generate` 等 AI 类长链路作业，助手不得阻塞等待完整外部取数、模型处理和结果写入结束；运行记录创建、关联 `collector_run_id` 且在 repository 上下文中可读回并进入 `running/queued` 后即可返回 run ID、状态、详情链接和引用，后台继续完成作业，保证用户能立刻看到“已触发”并可继续追踪。若运行摘要里的 `execution_nodes.runner_execution.status` 为 `queued/claimed/running`，后端 `assistant.scheduled_job_run.items[]/summary` 必须返回用户可读的 `progress_text`，例如“等待 AI 执行器接单：openclaw / runner_task_id”，助手回复也必须附带同一等待说明。前端助手气泡必须把 `assistant.scheduled_job_run.items[]/summary` 渲染为运行记录卡片，展示运行状态、触发方式、导入记录、`progress_text` 和运行详情入口；若初始状态为 `running/queued`，客户端按 `scheduled_job_id` 轮询运行列表并在终态自动更新为成功、失败或取消，避免用户误以为命令没有执行；若运行状态仍为 `running/queued`，但轮询结果的 `result_summary.execution_nodes` 从空摘要变为数据连接、AI 执行器、AI 处理或结果动作节点，前端也必须刷新卡片并展示当前“执行进度”，不得只在状态变化时更新。

run-once 周反馈洞察兜底草案必须和执行权限保持一致：管理员、`system.admin`、`system.scheduled_jobs.run` 或 `system.scheduled_jobs.manage` 用户都可在未命中现成作业时得到待确认服务端草案，缺少权限才返回 `permission_denied`。当前端检测到输入包含 `@... 执行一次/立即执行/run once` 等定时作业手动运行意图，且当前用户缺少管理员、`system.admin`、`system.scheduled_jobs.run` 或 `system.scheduled_jobs.manage` 权限时，必须在发送前展示“执行权限提示”，明确当前账号没有执行定时作业权限、本次不会直接执行，并提示所需权限 `system.scheduled_jobs.run`。若 `assistant.scheduled_job_run` 没有 `run_id/items[]`，但 `summary.status` 为 `permission_denied`、`needs_scheduled_job_reference`、`needs_single_reference` 或 `failed`，前端必须展示“执行状态”卡片，明确说明本次尚未执行、所需权限或运行未创建原因。

run-once 命令未命中可执行作业而进入草案路径时，助手回复和前端草案卡片必须显式展示“尚未执行”。该提示只用于 `pending` 草案，确认成功后应由“已应用”“打开定时作业”和“打开本次运行”状态接管，避免用户把待确认草案误判为已经触发运行。

助理内的研发任务、AI 能力配置、插件管理配置、定时任务配置和分析类输出必须以“动作草案 -> 用户确认 -> 领域 service/助手运行记录执行”的方式实现。模型只能生成配置草案、差异摘要和建议，不能直接写 `ai_tasks`、`ai_skills`、`ai_agents`、`integration_plugins`、`plugin_connections`、`plugin_actions`、`scheduled_jobs` 或触发外部调用。当前首批草案仍由聊天前的确定性工具结果生成 `assistant.action_draft`，包括 `create_rd_task`、`create_ai_skill`、`create_ai_agent`、`create_scheduled_job`、`create_plugin_connection`、`create_plugin_action` 和 `create_analysis_draft` 七类动作；当用户请求的配置草案可由 `assistant_tools` 确定性构造时，即使模型网关未配置也应先返回 `assistant.action_draft`，避免草案生成停在普通闲聊或模型不可用错误。草案预检和确认的权限边界必须按动作类型拆分：`create_plugin_connection` / `create_plugin_action` 要求管理员、`system.admin` 或 `system.plugins.manage`，`create_ai_skill` / `create_ai_agent` 要求管理员、`system.admin` 或 `system.ai_capabilities.manage`，`create_scheduled_job` 要求管理员、`system.admin` 或 `system.scheduled_jobs.manage`，手动 `run_scheduled_job` 和助手 run-once 仅要求管理员、`system.admin`、`system.scheduled_jobs.run` 或 `system.scheduled_jobs.manage`，不得用定时作业管理权限拦截 AI 能力草案，也不得用 admin 角色要求拦截已授予插件管理权限的插件草案。`create_rd_task` 仅支持基于显式 `@需求` 或唯一可判定的已规划需求生成 `product_detail_design` 研发任务草案，确认前预检 `requirement_id`、产品、版本、需求状态和重复任务，确认后复用需求生成任务 service 写入 `ai_tasks` 并推进需求状态。服务端在聊天响应阶段把可支持的工具项持久化为 `assistant_action_drafts`，并在工具项上追加 `server_draft_id`、`client_draft_id` 和 `status`；工具项携带的 `wizard_steps[]` 必须保存到草案元数据，并由 `GET /api/assistant/action-drafts/{draft_id}` 返回，避免草案脱离原聊天消息后丢失配置向导和依赖关系。前端助手页必须按 `draft_id`、`server_draft_id`、`client_draft_id` 的顺序归一化草案追踪 ID；历史消息或兼容响应只有 `server_draft_id` 时仍要展示草案卡片、确认/取消入口和“查看草案”链接，不得让服务端草案从对话中消失。前端助手页还必须支持 `/assistant?draft_id=<draft_id>` 深链：页面加载时调用 `GET /api/assistant/action-drafts/{draft_id}`，随后调用 `POST /api/assistant/action-drafts/{draft_id}/view` 并传入 `surface=deeplink`，展示“草案链接状态”的解析中、已加载或加载失败状态；已加载草案必须复用同一草案卡片展示状态、预检、向导、确认/取消、查看详情、重新生成和资源追踪入口，不依赖原始聊天会话仍在当前列表中；确认或取消成功后，深链卡片必须同步刷新为服务端返回的新状态和资源链接。前端助手页据此展示“查看详情”“确认创建”“取消”和“重新生成”，其中点击“查看详情”必须先调用 `POST /api/assistant/action-drafts/{draft_id}/view` 并传入 `surface=detail_modal`，再在当前对话页展示草案状态、动作、风险等级、payload JSON、应用前字段差异和校验问题，不要求用户跳转到新页面才能核对草案；草案配置向导中状态为 `needs_prerequisite` 或 `blocked` 的步骤必须提供“生成<步骤>前置草案”入口，点击后把草案标题、步骤名称和依赖项回填到聊天输入框，继续生成连接、动作、AI Skill 或 AI角色等前置草案；用户从草案卡进入定时作业、插件连接或插件动作表单并编辑后，表单保存必须先调用 `PATCH /api/assistant/action-drafts/{draft_id}` 提交最终 payload 与字段差异，再调用 confirm，由服务端统一创建领域资源、动作运行和审计，不得直接调用领域创建接口绕过草案生命周期；PATCH 和修改标记只允许 `pending` 草案，终态草案必须返回 `DRAFT_NOT_PENDING` 或 `DRAFT_EXPIRED`。确认接口返回校验、权限、引用失效或服务端错误时，前端草案卡片必须显式切换为“失败”状态，避免用户只看到临时 toast 后卡片仍显示待确认；确认接口对已 confirmed 且存在成功 action run 的重复提交必须幂等返回同一 run，并通过成功 run 的草案级唯一约束避免双击或重复 POST 产生重复资源；只有 `pending` 草案允许“应用到表单”或继续确认，`cancelled`、`expired`、`failed` 等终态草案不得再应用到定时作业、插件连接或插件动作表单，只能查看详情、查看草案或重新生成。

带有 `preview.target.source_resource` 的草案详情必须展示“对比来源”和来源配置标题；对应 `preview.diffs` 中的 `current` 必须来自该来源配置的安全字段，`proposed` 来自草案 payload，帮助用户在确认前判断修复草案或派生草案相对当前配置的真实变化。

草案状态为 `pending`、`confirmed`、`cancelled`、`expired` 或 `failed`，确认执行记录写入 `assistant_action_runs`。草案可携带 `expires_at`，服务端读取、确认或取消前必须将已过期且仍处于 `pending` 的草案自动置为 `expired`，写入 `assistant_action_draft.expired` 审计；过期草案确认或取消返回 `DRAFT_EXPIRED`，不得写领域表。`POST /api/assistant/action-drafts/{draft_id}/view` 只记录当前用户查看草案详情或深链加载，不改变草案状态、不写领域表；服务端必须在 `metadata_json` 写入 `viewed_at`、`detail_viewed_at`、`last_viewed_at`、`view_count`、`viewed_by` 和 `last_view_surface`，写入 `assistant_action_draft.viewed` 审计，并返回刷新后的草案，供效果漏斗统计真实“查看详情”。`POST /api/assistant/action-drafts/{draft_id}/confirm` 只接受仍处于 `pending` 的草案，并先按 `payload.assistant_prerequisite_draft_ids` 读取同创建人的已确认前置草案运行结果，把 `ai_skill/ai_agent/plugin_connection/plugin_action` 真实资源 ID 回填到当前草案的 `default_skill_ids`、`agent_id`、`skill_ids`、`connection_id`、`plugin_connection_id(s)` 或 `plugin_action_id(s)` 后重新预检，再走对应领域 service 或助手运行记录执行器：AI Skill 草案以 AI 能力管理权限调用 AI 能力配置 service 写入 `ai_skills`；AI角色草案以 AI 能力管理权限调用 AI 能力配置 service 写入 `ai_agents` 并重新校验模型网关和默认 Skill 引用；定时作业草案以定时作业管理权限调用 scheduled_jobs service，保存时把 `config_json.assistant_draft` 写入作业配置；若定时作业草案携带 `config_json.assistant_run_once_request.requested=true`，确认后还必须立刻触发一次 `manual` 运行并把公开运行记录嵌入 `assistant_action_runs.result.scheduled_job_run`，且运行记录必须持久化 `assistant_action_run_id`、`assistant_action_draft_id`、`assistant_source_message_id` 和 `triggered_by_assistant=true`；插件连接草案以插件管理权限调用插件连接 service；动作草案以插件管理权限调用动作 service；分析类草案不写业务配置表，只在 `assistant_action_runs.result` 中保存 `assistant_analysis` 摘要和 `source_draft_id`。确认成功写入 `assistant_action_draft.confirmed` 审计并返回领域资源或助手分析结果 ID 和运行记录；取消写入 `assistant_action_draft.cancelled`，不产生业务写入。后续删除、停用、插件试运行、定时作业运行、AI 能力配置创建/修改等高影响动作继续沿用同一确认模型，确认后仍复用现有 service 校验、repository 写入、审计事件和运行快照。

`/assistant/drafts` 是 AI 助手草案能力的稳定工作台。页面只消费 `GET /api/assistant/action-drafts` 的当前用户 read model，默认按 `updated_at desc` 展示草案标题、类型、状态、校验、风险、查看次数、修改字段数、最近更新时间和结果资源摘要；支持按关键词、草案类型、草案状态、校验状态和创建时间筛选。顶部汇总展示待确认草案、失败草案、已采纳草案、采纳率、处理率和用户修改率。点击“详情”必须调用 `POST /api/assistant/action-drafts/{draft_id}/view` 写入 `surface=detail_modal` 后展示 payload、校验问题和来源消息；“继续编辑”跳转 `/assistant?draft_id=<id>` 复用深链草案卡；`pending` 草案可在任务台直接确认或取消，其它终态只能查看和继续追踪。任务台不得跨用户展示草案，不得直接读取聊天历史 payload 拼装列表，也不得绕过草案 confirm/cancel 接口写领域资源。

助手效果指标由 `GET /api/assistant/metrics` 提供，只统计当前登录用户可归属的助手草案、动作运行、定时作业运行和助手消息。指标包括草案总数、待确认/已确认/已取消/已过期/失败数、草案采纳率、草案处理率、用户修改率、动作运行成功率、定时作业运行成功率、失败复跑修复率、用户消息显式引用使用率、引用总数、知识引用数、知识引用命中率、草案查看拆分和定时作业运行归因分布；知识引用统计口径覆盖 `knowledge_space`、`knowledge_folder`、`knowledge_document` 和 `knowledge_chunk`，不得漏计已被允许注入上下文的知识目录引用；`drafts_by_action` 按动作类型拆分草案状态。AI 助手工作台侧栏提供“助手效果指标”入口，用户按需加载后展示草案生成数、草案确认率、用户修改率、`@` 引用使用率、作业运行成功率、失败修复率和知识引用命中率，并同步展示草案状态分布（待确认、已应用、已取消、已过期、失败）、草案类型拆分（总数、待确认、已应用、已取消、处理率）、效果漏斗（查看草案、查看详情、深链打开）、运行追踪分子分母（作业运行成功/失败/总数、失败运行已修复/失败总数、助手触发/显式引用/复跑链归因来源）和引用追踪分子分母（已引用用户消息/用户消息总数、知识命中/知识请求/知识引用数），用于追踪草案闭环、定位哪类草案卡住，并解释运行成功率、失败修复率和知识引用命中率。草案类型处理率按 `(total - pending_count) / total` 计算，仅用于前端解释当前类型是否还卡在待确认；用户修改率只依据草案元数据中的 `user_modified=true` 或 `modified_fields` 非空计算，避免根据模型自然语言猜测；草案查看漏斗优先依据 `POST /api/assistant/action-drafts/{draft_id}/view` 写入的 `viewed_at/detail_viewed_at/deeplink_viewed_at/last_viewed_at/view_count`，其中 `draft_tracked_viewed_count` 表示有真实查看埋点的草案数，`draft_detail_viewed_count` 只统计详情弹窗，`draft_deeplink_viewed_count` 只统计深链加载。为兼容埋点上线前的历史数据，`draft_viewed_count` 采用有效查看口径：真实查看埋点、已确认/取消/失败、存在用户修改或已产生动作运行的草案都可计为被有效查看；`draft_inferred_viewed_count` 单独展示仅由历史行为推断的数量，响应 `instrumentation.notes[]/view_metrics` 必须说明真实埋点与历史推断口径，避免运营误读为没人看草案。失败复跑修复率按“失败运行被成功 `manual_rerun` 通过 `source_run_id` 引用”的比例计算，非 `manual_rerun` 的成功运行即使携带 `source_run_id` 也不得计入修复；知识引用命中率按“用户在同一会话显式引用的知识对象，后续助手回复也引用该知识对象”的比例计算。PostgreSQL 运行态优先读取助手 repository/read model；定时作业运行指标只能统计 `triggered_by_assistant=true` 且携带 `assistant_action_run_id`、`assistant_action_draft_id` 或 `assistant_source_message_id` 的运行、用户消息显式引用的具体 `scheduled_job_run`，以及这些运行通过 `source_run_id` 形成的复跑链，不得按“助手创建或引用过的 scheduled_job”把该作业后续所有 scheduler/manual 运行都计入助手成功率；响应必须返回 `scheduled_job_run_attribution.items[]`，按助手触发、显式引用和复跑链解释运行成功率分母来源；模型日志仍只记录元数据，不保存完整对话正文、知识正文或草案 payload。

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
| 代码仓库巡检 | 定时作业 + 插件扫描 + 多结果动作 | 面向仓库质量/安全/规范的周期性治理，不绑定单个 MR/PR；扫描结果写入代码巡检报告表，严重 finding 可自动创建 `code_inspection` 来源 Bug，并记录邮件/钉钉通知反馈。 |
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

产品配置、需求台账、AI 任务、人工确认、Graph 运行态、GitLab MR / GitHub PR 兼容快照、Code Review 报告、知识文档、知识 chunk、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属数据队列、迭代规划建议/确认、模拟 Issue 回写、模型网关配置、模型调用元数据、AI 助手会话、助手消息、助手动作草案、助手动作运行、助手角色快捷任务和助手动作候选配置已开始细粒度持久化：产品、版本、模块、Git 资源、相关系统、需求、AI 任务核心字段、Review、Graph Run、Checkpoint、GitLab MR / GitHub PR 兼容快照、Code Review 报告、知识文档、知识 chunk、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属队列项、迭代规划建议、迭代规划确认、模拟 Issue 回写、模型网关配置、模型调用元数据、助手会话、助手消息、助手动作草案、助手动作运行、助手角色快捷任务和助手动作候选配置会同步写入 `products`、`product_versions`、`product_modules`、`product_git_repositories`、`related_systems`、`requirements`、`ai_tasks`、`human_reviews`、`graph_runs`、`graph_checkpoints`、`gitlab_mr_snapshots`、`code_review_reports`、`knowledge_documents`、`knowledge_chunks`、`knowledge_deposits`、`audit_events`、`bugs`、`gitlab_daily_code_metrics`、`jenkins_release_records`、`online_log_metrics`、`user_feedback`、`user_usage_metrics`、`collector_runs`、`pending_attribution_items`、`iteration_plan_suggestions`、`iteration_plan_decisions`、`mock_issues`、`model_gateway_configs`、`model_gateway_logs`、`assistant_conversations`、`assistant_messages`、`assistant_action_drafts`、`assistant_action_runs`、`assistant_role_quick_tasks`、`assistant_action_reference_configs`。`app_state_snapshots` 仅作为历史迁移表保留，不再作为生产业务状态恢复源或请求结束写入目标。`PERSISTENCE_MODE` 默认值为 `postgres`；除 `APP_ENV=test/testing/pytest` 外，后端启动时配置 `PERSISTENCE_MODE=memory` 必须 fail fast，纯 `MemoryStore` 仅作为测试 helper；PostgreSQL 运行时 `build_store()` 返回轻量 `PostgresRuntimeStore(repository)`，不再通过 `PersistentMemoryStore.from_repository(repository)` 启动恢复业务集合。PostgreSQL source rows 使用非 `MemoryStore` 的 repository request context；只读缓存/read model 可作为性能优化保留，但必须由 PostgreSQL 派生、可重建，且不得作为写接口事实源。所有 PostgreSQL 结构表必须包含 `created_at timestamptz NOT NULL DEFAULT now()` 和 `updated_at timestamptz NOT NULL DEFAULT now()` 标准字段；业务写入或结构仓储 upsert 应保留新增时间并在发生修改时维护修改时间，迁移测试会阻止缺少任一字段的新表进入代码库。AI 任务启动路径已由真实 LangGraph `StateGraph` 编译和执行，当前 MVP 节点路径为 `retrieve_context -> generate_task_output -> interrupt_for_human_review`，运行记录会保存 `runtime`、`node_path` 和 checkpoint 内的 `graph_runtime` 元数据。

AI 助手聊天运行同样属于 DB-first 业务状态：`assistant_chat_runs` 记录每次 `/api/assistant/chat` 的运行生命周期，`assistant_messages` 记录同一 `run_id/client_request_id` 下 user 与 assistant 消息的 `pending/completed/cancelled/failed` 状态。停止生成通过 `POST /api/assistant/chat-runs/{run_id}/cancel` 写入取消状态和审计事件，刷新历史后仍可追踪本次中断，而不是仅依赖前端 AbortController 临时态。

DB-first 迁移状态：上述结构化持久化不代表所有 API 已经直连数据库。当前生产目标是继续删除所有把 `current_store.<collection>` 当作数据源或写入目标的剩余路径，改为所有读接口走 SQL/repository/read model、所有写接口在 handler/service 内事务化直写 PostgreSQL 并同步审计。`/health` 必须返回 `data_access_mode`，当前迁移期取值为 `db_first_migration`；当 `PERSISTENCE_MODE=memory` 且处于测试环境时取值为 `memory_test_helper`。PostgreSQL 启动运行层已从 `PersistentMemoryStore.from_repository(repository)` 切换为 `PostgresRuntimeStore(repository)`，不再启动恢复业务集合；请求结束全局 `persist()` 已从 API middleware 移除，任何 API 请求都不再通过请求结束同步进程内 store。API 通用依赖位于 `app.api.deps`，集中提供 `api_error`、`store`、`CurrentUser/get_current_user` 和 `require_roles`，后续独立 router 必须使用该共享依赖，不得反向 import `main.py` 获取认证或错误封装。产品配置写接口已开始按 handler 级别调用 repository 单记录写入/删除方法，覆盖产品、迭代版本、模块、Git 资源和相关系统，并通过禁用请求结束 `persist()` 的重建测试验证写入不依赖全局同步；产品配置核心 GET 接口已在 repository 可用时优先读取 SQL/repository，包括产品列表/详情、指定产品的版本、模块、Git 资源和关联系统，并通过运行态 store 过期测试验证不依赖进程内集合。需求台账的纯需求写接口已用同样方式覆盖创建、修改、审批、驳回、关闭和删除，并把对应审计事件随单条需求记录写入；从需求生成产品详细设计 AI 任务已通过 repository 在同一事务中写入需求 `task_ids`/状态、AI 任务记录和 `ai_task.created` 审计事件。后续任务创建也已在同一事务中写入需求 `task_ids`/状态、AI 任务记录和 `ai_task.created` 审计事件；需求列表、需求详情、AI 任务详情、Graph Run 列表、待确认 Review、Review 详情、模拟回写结果、Code Review 报告和 Markdown 导出在 PostgreSQL 运行时会优先读取 task workflow repository source rows，运行态 store 过期时仍能返回结构表详情、任务运行态、确认态、回写结果和导出内容。任务启动成功路径已写入 AI task、模型调用日志、Human Review、Graph Run、Checkpoint 和启动审计事件；任务启动失败路径已写入 failed task、可选模型失败日志、`ai_task.retry_started` 和失败审计事件；Review approve/edit-approve/reject/request-more-info 主路径已写入完成态或中断态 task、review、graph/checkpoint、需求状态、知识沉淀候选、可选 Bug/Code Review 报告和审计事件；cancel/submit-more-info 已写入 AI task、待确认 Review、Graph Run/Checkpoint 和审计事件；Mock Writeback 生成接口已在 handler 返回前写入 `mock_issues` 和 `mock_issue.written` 审计事件。知识文档创建/更新/索引重试/删除、知识 chunk 重建、知识沉淀采纳/拒绝和对应审计事件已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 knowledge source rows 恢复产品、知识文档、chunk、沉淀和模型网关上下文，同步索引期间可选模型日志；知识文档列表、知识沉淀候选列表和知识检索候选 chunk 已在 repository 可用时优先读取 SQL/repository，权限角色、关键字、文档类型、索引状态、沉淀状态和 chunk 权限等过滤在查询层执行，chunk_count 由结构表聚合返回；知识检索保留现有关键词兜底和兼容向量排序，但候选集不再来自进程内知识集合；知识沉淀 approve/reject 写接口优先从 repository 读取当前沉淀记录，运行态 store 过期时仍能写回沉淀、文档、chunk、模型日志和审计事件。AI 助手聊天成功路径已在 handler 返回前写入会话、用户消息、助手消息、模型日志和审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 assistant source rows 恢复当前用户会话、消息、产品任务摘要和模型网关上下文；模型调用失败路径写入失败模型日志和审计事件；助手会话列表和消息列表已在 repository 可用时优先读取 SQL/repository，并按当前 `user_id` 在查询层隔离历史记录。GitHub PR 列表、GitLab MR / GitHub PR 预览审计以及快照成功、复用和失败审计已在 handler 返回前写入 repository；Code Review 报告生成/确认已随任务启动和 Review 决策事务写入。Bug 创建、修改和删除已在 handler 返回前写入 `bugs` 与对应审计事件，删除前会清空指向该 Bug 的重复归并引用；Bug 列表已在 repository 可用时优先读取 SQL/repository，产品、状态、严重级别和来源过滤在查询层执行。采集运行创建/更新、待归属队列创建/处理、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标创建已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品、仓库、版本、模块、采集运行和待归属当前记录；采集运行、待归属队列、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标列表已在 repository 可用时优先读取 SQL/repository，采集类型、来源系统、产品、仓库、版本、状态、环境、日期和时间范围等过滤在查询层执行。用户使用指标创建、用户反馈创建/处理、迭代建议生成和迭代建议决策已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 insight source rows 校验产品、版本、模块、反馈、Bug 和迭代建议当前记录；用户使用指标、用户反馈和迭代建议列表已在 repository 可用时优先读取 SQL/repository，产品、模块、功能、用户群体、时间范围、状态、创建人和规划周期等过滤在查询层执行；迭代建议转需求时会在同一 repository 调用内写入新需求、建议、决策和完整审计事件。模型网关配置创建、修改、删除和连接测试审计已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 model gateway source rows 恢复当前配置和调用日志上下文；模型网关配置列表和模型调用日志列表已在 repository 可用时优先读取 SQL/repository，并通过运行态 store 过期测试验证配置列表、密钥脱敏状态和日志筛选不依赖进程内集合。审计列表已在 repository 可用时优先读取 SQL/repository，actor、event_type、ai_task、subject 和时间范围过滤在查询层执行。生命周期上下文查询生成的 edges/risks 和首页看板生成的 dashboard snapshot 已在 handler 返回前写入 repository；在 PostgreSQL 运行时，首页看板和生命周期上下文聚合前都会直接读取 repository source rows，不再依赖 repository read snapshot 聚合；首页看板通过 `save_dashboard_metric_snapshot_record` 单条写入当前产品/时间窗口快照，生命周期上下文通过 `save_lifecycle_context` 写回生成的 edges/risks。管理列表类型接口必须优先在 SQL/repository/read model 层完成分页、排序和筛选；返回分页响应时必须附带 `query.name`、生效筛选、分页、排序和 `performance.duration_ms/result_count/total/slow`，当接口耗时超过阈值时记录 `slow_list_query` 日志，后续 P95 目标和页面慢问题以这些元数据、trace_id 与数据库慢查询日志联合定位；首页团队看板、生命周期上下文等汇总视图可以基于 PostgreSQL source rows 在 Python 中聚合，只要读取来源可重建、权限过滤和产品/时间窗口过滤清晰，且不得把聚合容器作为写入事实源。首页团队看板允许使用由 PostgreSQL source rows 派生的短 TTL 只读缓存，缓存 key 必须包含 repository 身份、产品、时间窗口和用户角色集合，响应必须回显 `metadata.dashboard_cache`，`refresh=true` 必须强制重建；当看板接口耗时超过阈值时记录 `slow_dashboard_query`，用于和列表 `slow_list_query` 一起定位慢页面。后续 DB-first 切片继续迁移尚未结构化仓储化的业务域。新增生产接口不得把 `current_store.<collection>` 作为数据源或写入目标；如必须临时保留，应在迁移计划中标注模块、风险和退出条件。

`main.py` 只允许保留 FastAPI app 创建、运行时 store/user repository 构建、middleware、异常处理、CORS 与 router 注册，不得再新增业务 helper、repository source-store 组装或结构表保存委托。任务工作流 source rows 的只读/写入上下文由 `app.services.task_workflow_context` 维护；PostgreSQL repository-backed source context 必须是非 `MemoryStore` 对象，仅暴露业务服务需要的集合、`new_id`、`snapshot` 和 `audit` 能力，避免 DB-first 运行时再次退回进程内 MemoryStore 兼容层。持久化层的集合字段常量、`SnapshotRepository` 和各领域仓储 Protocol 由 `app.core.persistence_contracts` 统一维护；snapshot payload/load/save、集合合并、上下文清理、counter 同步和恢复链路 helper 由 `app.core.persistence_payloads` 维护；测试兼容层 `PersistentMemoryStore` 由 `app.core.persistent_memory_store` 维护，只允许用于测试或历史恢复验证；生产 PostgreSQL 运行时容器 `PostgresRuntimeStore` 由 `app.core.persistence_runtime` 维护，`main.py` 必须直接从该 runtime 模块装配；`app.core.persistence` 只能继续承载兼容 re-export 和 PostgreSQL snapshot repository 实现，后续拆分不得把协议定义、snapshot helper、测试兼容 store 或生产 runtime 实现重新堆回 snapshot repository 文件。

认证与角色目录 API 已收口到独立 `app.api.routers.auth`：`/api/auth/login`、`/api/auth/me`、`/api/auth/logout` 和 `/api/auth/roles` 仍保持原有 URL、鉴权依赖、trace envelope 和角色目录返回契约；router 只依赖 `app.api.deps`、用户仓储、角色目录与安全工具，不得反向 import `main.py`。路由边界测试必须保证这些 auth 端点只有单一 router 归属，避免后续拆分时出现重复注册或回退到 `main.py`。

用户管理 API 已收口到独立 `app.api.routers.users`：`GET/POST /api/users` 和 `PATCH/DELETE /api/users/{user_id}` 仍保持原有管理员权限、用户仓储、角色目录校验、状态校验、错误码和 trace envelope 契约；用户新增/修改时角色必须来自 MVP 可分配角色目录，不能自由录入未定义角色。路由边界测试必须保证用户管理端点只有单一 router 归属，避免系统管理 CRUD 回退到 `main.py`。

产品主体 CRUD API 已收口到独立 `app.api.routers.products`：`GET/POST /api/products` 和 `GET/PATCH/DELETE /api/products/{product_id}` 仍保持原有产品负责人权限、产品编码唯一性、SQL read model 分页筛选排序、`query/performance` 观测元数据、repository-first 读取、handler 级 repository 写入、删除前业务依赖校验和无业务依赖时级联清理版本/模块/Git 资源/相关系统配置的契约。迭代版本 API 已收口到独立 `app.api.routers.product_versions`：`GET /api/product-versions`、`GET/POST /api/products/{product_id}/versions`、`POST /api/product-versions/{version_id}/advance-status` 和 `PATCH/DELETE /api/product-versions/{version_id}` 保持 SQL read model 分页筛选排序、产品内版本编码唯一、版本状态专用推进、需求状态同步、阻塞校验、repository-first 读取、handler 级版本/需求/审计写入和删除依赖校验契约。产品模块 API 已收口到独立 `app.api.routers.product_modules`：`GET/POST /api/products/{product_id}/modules` 和 `PATCH/DELETE /api/product-modules/{module_id}` 保持产品负责人权限、产品内模块编码唯一、repository-first 读取、handler 级模块/审计写入和删除前需求/任务/Bug 依赖校验契约。产品 Git 仓库 API 已收口到独立 `app.api.routers.product_git_repositories`：`GET/POST /api/products/{product_id}/git-repositories` 和 `PATCH/DELETE /api/product-git-repositories/{repo_id}` 保持产品负责人/研发负责人读取权限、产品负责人写权限、GitLab/GitHub provider 绑定校验、repository-first 读取、handler 级 Git 资源/审计写入和 `credential_ref_configured` 脱敏响应契约。相关系统 API 已收口到独立 `app.api.routers.related_systems`：`GET/POST /api/system/related-systems` 和 `PATCH/DELETE /api/system/related-systems/{system_id}` 保持产品负责人写权限、可选产品归属校验、全局系统编码唯一、repository-first 读取和 handler 级相关系统/审计写入契约。产品主体、迭代版本、产品模块、产品 Git 仓库和相关系统 router 共用 `app.services.product_config_context` 承载产品配置 source rows、repository 上下文、唯一性校验、审计事件构造和单记录写入/删除；产品配置域端点已完成 router 收口。路由边界测试必须保证产品主体、迭代版本、产品模块、产品 Git 仓库和相关系统端点只有单一 router 归属。

平台状态 API 已收口到独立 `app.api.routers.platform`，平台健康检查、TCP 依赖探测、运行数据访问模式、模型网关健康状态和 GBrain 长期记忆脱敏状态由 `app.services.platform_status` 统一构造。`/health` 保持免登录访问并返回 `status/postgres/redis/model_gateway/chat_gateway/embedding_gateway/data_access_mode/long_memory/trace_id`；`/api/long-memory/status` 保持登录访问并返回 GBrain 是否配置、能力列表和 `postgres_pgvector` 兜底检索器，不返回 URL、API Key 或密钥片段。路由边界测试必须保证这两个平台状态端点只有单一 router 归属。

模型网关列表只显示 `api_key_configured`，不显示明文密钥或密钥片段。配置测试接口使用临时参数调用 OpenAI-compatible `/chat/completions` 和 `/embeddings`，返回 Chat/Embedding 成功状态、模型、延迟、embedding 维度、跳过状态和错误码；测试范围支持 `chat_and_embedding`、`chat` 和 `embedding`，其中 `chat` 只验证 Chat 并把 Embedding 标记为 `skipped`，适配 ChatGPT OAuth 类不提供 `/embeddings` 的上游。测试不得保存配置或密钥，不写入模型调用日志，审计只记录 provider、测试范围和测试状态。存在 active/default 且已配置 API Key 的 OpenAI-compatible 模型网关时，非 code_review 任务启动会通过 `/chat/completions` 调用真实 provider 并要求返回 JSON 对象；AI 助手通过 `/api/assistant/chat` 调用同一 Chat 边界，服务端会通过 `app.services.assistant_tools` 先按用户问题生成 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等确定性 read-model 工具结果，再通过 `app.services.assistant_context` 注入当前产品、需求、AI 任务、Git 仓库、迭代进度、待确认 Review、代码评审结论、Bug 分布、知识沉淀、模型网关状态摘要和工具结果，使其能回答 AI Brain 系统信息和项目进展问题；助手 API 已收口到 `app.api.routers.assistant`，聊天工作流由 `app.services.assistant_chat` 统一处理工具结果生成、模型调用、会话创建/续写、用户级历史隔离、成功/失败模型日志、审计事件和错误码映射，router 只保留权限、request store 和响应封装入口；助手完整对话按登录用户保存到 `assistant_conversations` 和 `assistant_messages`，助手消息 metadata 持久化 `references` 与 `tool_results`，历史查询只返回本人会话；显式知识文档引用会在模型请求前解析为 `selected_references` 和限量 `knowledge_context`，服务端动作草案保存到 `assistant_action_drafts`，确认/取消和执行结果写入 `assistant_action_runs` 与审计事件；模型调用日志仍只保存脱敏元数据；知识索引会先生成文本 chunk，随后在 Embedding 可用时通过 `/embeddings` 写入 `knowledge_chunks.embedding`，检索只有存在当前用户可读向量 chunk 时才生成 query embedding；模型调用日志只记录 provider、model、purpose、tokens、latency、status、error 和配置 id，不记录 prompt、完整输出或密钥，其中助手调用使用 `purpose=assistant_chat`。模型网关配置缺失密钥时非 code_review 任务进入 `failed` 并返回 `MODEL_GATEWAY_CONFIG_INVALID`；非 code_review 任务 provider 调用失败返回 `MODEL_GATEWAY_FAILED`。code_review 任务已接入独立 `code_review_executor` 边界，默认 `CODE_REVIEW_EXECUTOR_TYPE=claude_code_skill`、`CODE_REVIEW_EXECUTOR_NAME=code-review`，由 `CODE_REVIEW_EXECUTOR_COMMAND` 指向外部命令适配器，输入 JSON 通过 stdin 提供，输出 JSON 通过 stdout 返回；测试或兼容环境可显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 复用模型网关适配器；若默认外部执行器命令为空且存在 active/default 模型网关或环境模型网关，系统会通过同一执行器边界自动改用 `model_gateway` 适配器，模型 prompt 必须携带 MR/PR 快照、已确认技术方案、需求快照和产品上下文，并将常见 Review 输出字段如 `overall`、`score` 规范化为 `risk_level` 与 executor metadata，避免本地全链路测试额外依赖外部命令。执行器调用成功写入 `code_review.executor_called` 审计事件；配置缺失、调用失败、超时、响应解析或结构化报告校验失败返回 `CODE_REVIEW_EXECUTOR_FAILED`，任务停在 `code_review_executor_failed` 并写入 `code_review.executor_failed` 审计事件，不得静默回退成本地输出。

产品配置、需求、知识文档、Bug、用户管理、用户反馈和模型网关配置已具备当前管理页所需 CRUD 能力；产品支持详情查询，便于从产品上下文进入配置和全链路脚本校验；用户使用指标和线上运行日志指标已具备真实登记和查询能力。产品管理页面通过“配置”弹窗维护模块、Git 资源和相关系统，需求交付菜单下的“迭代版本”页面集中维护 `product_versions`；`GET /api/product-versions` 批量返回版本及所属产品投影，需求列表返回 `product_code`、`product_name`、`version_code`、`version_name`、`assignee` 和 `created_at`，需求管理页基于该投影支持按迭代版本名、编码或“未排期”过滤需求范围，并在列表展示创建时间而不是更新时间；Bug 列表返回 `version_code`、`version_name` 并支持按 `version_id` 查询，Bug 管理页展示迭代版本列并可按版本名、编码或“未关联”过滤缺陷范围，登记 Bug 的目标版本下拉读取同产品未归档版本，允许选择 `planning`、`active`、`testing` 或 `released` 版本并过滤 `archived`，列表支持勾选多条 Bug 后批量更新状态、严重级别或处理人，批量接口逐条校验状态机并返回 updated/skipped 明细，记录 `bug.batch_updated` 与逐条 `bug.updated` 审计，任务列表在 PostgreSQL 模式通过 SQL join 返回产品名，前端产品管理、需求列表、Bug 列表、迭代版本和产品上下文下拉不再逐产品串行拉取版本。新增需求只强制选择产品，`version_id` 可为空，默认负责人 `assignee` 为创建人，审批后进入需求池，排入规划中或开发中迭代版本后才允许生成 AI 任务；需求管理页支持勾选同产品 `approved/planned` 需求后批量排期，迭代版本页支持从规划中或开发中版本行归集同产品需求池/已排期需求，批量排期接口返回 updated/skipped 明细并记录批量级与单需求审计；需求管理页还支持勾选非关闭/非取消需求批量分配负责人，批量分配接口更新 `requirements.assignee`、返回 updated/skipped 明细，并记录 `requirement.batch_owner_assigned` 与逐需求 `requirement.updated` 审计；需求管理页还支持勾选同产品 `planned` 需求批量生成产品详细设计任务，批量生成任务接口返回 generated/skipped 明细，合法需求进入 `designing` 并记录 `requirement.batch_tasks_generated` 与逐任务 `ai_task.created` 审计；迭代版本页在任意版本状态下都提供当前版本需求清单只读查看，避免测试中版本无法回看范围。迭代版本主状态为 `planning / active / testing / released`，`archived` 仅作为历史归档状态；版本状态变更必须走 `advance-status` 专用动作，先返回影响预览，再将符合条件的需求同步推进到 `ready_for_dev`、`testing` 或 `released` 并记录 `product_version.status_advanced` 与逐需求 `requirement.updated` 审计；其中 `active -> testing` 必须把版本内 `approved/planned/ready_for_dev/designing/developing/code_reviewing` 等已进入交付链路的需求统一推进到 `testing`，避免版本阶段和需求阶段不一致。Git 资源可选择 `gitlab` 或 `github` provider，相关系统可绑定 `product_id`，生成任务产品上下文时只纳入同产品且启用的相关系统；Git 凭据仅在新增/编辑时提交，列表只展示 `credential_ref_configured` 对应的配置状态，不回显凭据引用或 token。知识中心已具备独立导入、列表、文本 chunk 索引、Embedding 可用时的向量索引、权限过滤后的关键词/向量混合检索、索引错误展示、`index_failed` 重试、`text_indexed` 补向量索引和沉淀审核入口；主动导入知识文档可选绑定 `product_id`，任务沉淀采纳的知识文档可从沉淀任务回溯产品归属。任务中心已具备真实产品详细设计启动、Review 确认、技术方案任务创建、开发计划任务创建、自动化测试任务创建、发布评估任务创建、上线后分析任务创建、Markdown 导出和多选批量取消入口；任务管理列表摘要返回产品名、创建时间和更新时间，并支持按所属产品与创建时间段筛选；批量取消接口逐条校验任务状态，合法任务进入 `cancelled`，重复、缺失或终态任务返回 skipped 明细，并记录 `ai_task.batch_cancelled` 与逐任务 `ai_task.cancelled` 审计；模型网关或 code-review 执行器临时失败时，停在 `model_gateway_failed` 或 `code_review_executor_failed` 的任务可用原 task_id 重试，避免为同一阶段复制新任务导致链路割裂；AI 任务创建和人工确认会把需求推进到 `designing`、`ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released` 或 `accepted` 等研发状态；`automated_testing` 任务的 `bug_suggestions` 在人工确认后会写入 `bugs`，来源为 `ai_auto_test`；`post_release_analysis` 任务的 `bug_suggestions` 在人工确认后会写入 `bugs`，来源为 `ai_post_release`，并保留产品、版本、需求和任务关联；日志监控已具备 GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标登记与筛选入口；用户洞察页已具备真实用户反馈登记、用户使用指标登记与筛选、固定列宽列表、详情弹窗、迭代建议生成、确认和可选转需求入口，用户反馈创建人可为任意已登录用户，状态处理、指标登记和迭代建议操作需 `product_owner`、`rd_owner` 或 `admin`。

需求管理页支持勾选需求批量推进状态。目标状态必须符合研发流程前进路径，合法需求状态更新并记录 `requirement.batch_status_advanced` 与逐条 `requirement.updated` 审计；终态、重复、缺失或不符合路径的需求进入 skipped 明细，不回滚同批次合法项。批量推进到 `planned`、`ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released`、`accepted` 等交付链路状态时，需求必须已归属迭代版本；未排期需求必须先通过批量排期或编辑归入版本，避免需求全链路缺少版本节点。需求批量排期、批量分配负责人、批量推进状态和批量生成任务完成后，前端必须展示结果弹窗，包含批次号、成功数、跳过数以及每条 skipped 的需求 ID、错误码和原因，避免用户只能从 toast 猜测哪些项未处理。

迭代版本阶段流转、需求同步影响计算和阻塞规则由 `app.services.version_status` domain service 承载，接口 handler 只负责权限、审计、repository 写入和响应拼装；后续版本状态规则调整应优先修改该服务并补充 service 层单测。

任务失败恢复必须复用单任务启动状态机：只有 `status=failed` 且 `current_step` 为 `model_gateway_failed` 或 `code_review_executor_failed` 的任务允许重试。任务管理批量重试接口逐条校验任务状态，合法任务调用同一 `/start` 逻辑；成功进入待确认的任务返回 `updated`，已尝试但模型网关或代码评审执行器仍失败的任务返回 `retried` 并携带错误码，不可重试、重复或不存在的任务返回 `skipped`。批次级审计事件为 `ai_task.batch_retried`，逐任务重试沿用 `ai_task.retry_started`。任务管理批量取消和批量重试完成后，前端必须展示结果弹窗；取消结果展示批次号、取消数、跳过数和 skipped 明细，重试结果展示批次号、重试数、成功数、仍失败数、失败错误码/错误信息和 skipped 明细，避免用户只能从 toast 推断任务是否恢复成功。

Bug 来源、严重级别、状态机、初始状态和产品/版本/模块/需求/任务/重复缺陷上下文校验由 `app.services.bug_lifecycle` domain service 承载，Bug 创建、单条更新和批量处理 handler 只负责权限、审计、repository 写入和响应拼装；后续 Bug 状态规则调整应优先修改该服务并补充 service 层单测。Bug 管理批量处理完成后，前端必须与需求、任务批量操作共用结果弹窗展示批次号、更新数、跳过数和每条 skipped 的 Bug ID、错误码和原因，避免用户只能从 toast 判断哪些缺陷未处理。

需求批量排期的目标版本选择应与后端校验一致：需求管理页读取该产品全部版本并仅保留 `planning`/`active`，过滤 `testing`、`released` 和 `archived`；批量接口必须以追加/upsert 方式保存 `requirement.batch_scheduled` 审计事件，不能使用覆盖式审计快照保存导致历史批次审计被删除。

研发运营统一列表和用户洞察统一列表在 PostgreSQL 运行时均使用 repository SQL read model 聚合查询，分别对 GitLab/Jenkins/线上日志以及用户使用/用户反馈/迭代建议来源在 SQL 层完成筛选、排序和分页；接口层 MemoryStore 拼装仅保留为测试 helper fallback，不作为生产主列表数据路径。

产品管理列表在 PostgreSQL 运行时使用 `products` + 当前版本 lateral 投影 + 模块计数 SQL read model 查询，`active_only/code/name/owner_team/status` 筛选、当前版本/模块数投影、列表排序和分页必须在数据库层完成；产品详情、配置弹窗和单产品版本/模块/Git 资源下拉仍可使用轻量 repository 查询。迭代版本列表在 PostgreSQL 运行时使用 `product_versions` + `products` 的 SQL read model 查询，`active_only/code/name/product/product_id/status` 筛选、所属产品投影、列表排序和分页必须在数据库层完成。需求管理列表在 PostgreSQL 运行时使用 `requirements` + `products` + `product_versions` 的 SQL read model 查询，`priority/product/product_id/status/title/version/version_id` 筛选、列表排序和分页必须在数据库层完成；接口层仅补充 `query/performance` 观测元数据。需求详情、需求全链路、AI 任务运行态、Review、回写结果和 Markdown 导出仍可使用 task workflow source rows 聚合上下文，但不得作为需求列表页的全量加载替代。Bug 管理列表在 PostgreSQL 运行时使用 `bugs` + `product_versions` 的 SQL read model 查询，`module/product_id/severity/source/status/title/version/version_id` 筛选、列表排序和分页必须在数据库层完成；旧 `list_bugs` 仅作为兼容 fallback，不得作为生产主列表的全量加载路径。

审计与运行页面支持查看真实审计详情，并从审计主体优先发起生命周期链路追踪。执行诊断中心位于运营治理菜单，要求 `diagnostics.execution_traces.read` 权限，按运行根聚合 `scheduled_job_runs`、`plugin_invocation_logs`、`ai_executor_runners`、`ai_executor_tasks`、`model_gateway_logs`、`code_inspection_reports`、派生 `result_write_records` 和 `audit_events`，统一构建链路节点、依赖边、状态、耗时、关联 ID 和脱敏元数据；PostgreSQL 运行时会在单个数据库事务中刷新可重建的 `execution_trace_snapshots` 只读 read model，列表和详情优先从快照表分页、过滤和排序读取，MemoryStore 路径仅作为测试 helper fallback；列表支持 `source_id` 按任一节点来源 ID 精准定位，`/governance/execution-traces?source_id=...` 命中唯一链路时前端自动打开详情，用于从定时作业、插件调用、Runner、模型网关日志、代码巡检报告、结果写入记录、AI 助手运行或审计事件快速跳转排障；`ai_executor_task.runner_id` 必须解析为 `ai_executor_runner` 节点并通过 `assigned_runner` 边关联，Runner 节点只展示名称、协议、执行器类型、工作区、心跳、超时、并发、健康状态和 token 是否配置，缺少 Runner 记录时保留带 `missing_runner_record` 的占位节点，不能暴露 `token_hash`；模型网关日志会吸附通过 `subject_id`、payload `model_gateway_log_id` / `model_log_id` 或相同 `ai_task_id` 指向它的审计事件，按审计事件 ID 下钻应回到同一条模型调用链路，避免重复生成孤立模型 Trace 和孤立审计 Trace；`result_write_record` 节点只从定时作业运行或独立插件调用读模型派生，用于确认报告、用户反馈、通知等产物是否真正写入，不作为新的写入事实源；详情必须汇总失败、取消、运行中或排队节点，提供来源 ID 深链和“问 AI”入口，成功链路展示无失败节点提示；该表不是新的业务写入事实源，敏感键如 `token/api_key/authorization/password/secret/cookie` 必须在响应前替换为 `<redacted>`。生命周期视图、需求全链路详情和首页 IT 团队看板的 AI 任务、待确认 Review、知识沉淀和风险信号聚合会先按任务类型读权限过滤，不能通过聚合接口绕过任务详情权限。生命周期上下文已支持从真实 Bug、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户使用指标、用户反馈和迭代规划建议起点回溯同产品/版本/模块任务链路，并把这些真实证据写入 downstream 关系；缺少对应证据时返回动态 `missing_context`，不合成兜底关系。需求全链路详情由 `GET /api/requirements/{requirement_id}/full-chain` 承载，面向需求管理页一次返回需求、产品、迭代版本、AI 任务、Review、GitLab MR / GitHub PR 兼容快照、Code Review 报告、Bug、Jenkins 发布和知识沉淀候选，并生成按发生时间排序的页面时间线；前端在需求管理页保留弹窗快查，同时提供隐藏菜单路由 `/delivery/requirements/{requirement_id}/full-chain` 作为可刷新、可复制链接的独立详情页，两者共用同一阶段进度、阶段明细、时间线、PR/MR 快照风险摘要、diff 文件树和 Review Checklist 展示组件；时间线支持按事件类型筛选并展示筛选后/总事件数，便于在复杂需求链路中聚焦查看 Review、代码评审、Bug、发布或知识沉淀；阶段明细必须按需求、迭代版本、AI 任务、Review、PR/代码评审、Bug、发布和知识沉淀分组展示可展开实体清单，并提供跳转到对应管理页的实体链接，不得再多接口拼装该详情。首页 IT 团队看板已基于真实产品、需求、AI 任务、待确认 Review、知识和审计数据返回 MVP 聚合摘要；传入 `product_id` 时，知识文档和审计事件也必须按产品归属过滤，不能把其他产品的知识或审计计数混入当前产品；看板属于汇总型视图，允许在读取 PostgreSQL source rows 后由 Python 做跨主体聚合和展示计算，后续优化以慢查询证据、缓存快照和权限边界为依据，不强制先改成 SQL/物化 read model。产品、需求、迭代版本、Bug、任务、知识文档、审计事件、研发运营指标和用户洞察主列表均已通过后端接口承载分页、排序和筛选，前端主列表不得再拉全量数据后本地拼装；核心管理主列表响应同时返回 `query` 与 `performance` 元数据，记录生效筛选、分页、排序、响应耗时、返回条数、总数和慢查询阈值，作为页面慢问题定位依据；其中用户洞察统一列表在 PostgreSQL 运行时由 repository SQL read model 通过 `UNION ALL` 聚合用户使用指标、用户反馈和迭代建议，并在 SQL 层执行 `category/summary/status` 筛选、`category/id/owner/status/summary/updated_at` 排序和分页，不再由接口层拉三类全量数据后合并。前端管理主列表通过统一 `ManagementListPage` 兜底固定布局、横向滚动、文本省略、普通列默认 160px 稳定宽度和右侧固定操作列；操作列默认 220px，避免详情、编辑、删除、生成任务等行内动作挤压；页面级 `viewStorageKey` 启用本地筛选视图后，可保存、应用和删除当前筛选与排序组合，作为个人浏览器偏好，不作为业务事实源或跨用户配置；页面仍可按业务宽度显式覆盖；模型网关配置、用户和角色等低数据量子表可暂保留独立列表接口或本地过滤，但不得作为管理主列表的多接口聚合替代。GitLab MR / GitHub PR 预览和 diff 快照已接入只读 API：GitLab 产品 Git 资源需提供可解析的 `remote_url` 或 `GITLAB_BASE_URL`，GitHub 产品 Git 资源需提供 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`，GitHub Enterprise 可通过 `GITHUB_BASE_URL` 指定 API base；凭据引用推荐使用环境变量或服务端密钥引用，本地联调可直填只读 token，系统只读取变更元信息、文件摘要、diff 文件树、风险摘要和 Review Checklist，不回写 GitLab/GitHub；任务中心创建 Code Review 前必须展示这些预览信息，帮助确认 MR/PR 变更范围和重点检查项。日志监控页面保留 GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标登记/查询，不依赖前端示例数据；外部自动采集器尚未接入。无记录时返回真实空集合，不提供前端本地兜底行或后端伪造统计数据；采集运行记录和待归属数据队列仅作为历史兼容 API/结构表保留，不再作为当前前端功能入口。

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
  ├─ plugin_management
  ├─ scheduled_jobs
  ├─ code_inspection
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
| plugin_management | 插件、连接、动作配置和连接测试诊断；调用日志由定时作业运行详情统一展示 | integration_plugins, plugin_connections, plugin_actions, plugin_invocation_logs, audit |
| scheduled_jobs | 定时作业定义、运行实例、锁租约、AI/插件装配快照和结果动作调度 | ai_agents, ai_skills, model_gateway, plugin_management, collector_runs, audit |
| code_inspection | 周期性代码仓库质量/安全/规范巡检报告、finding 归档、严重问题派生 Bug、通知反馈和治理概览 | scheduled_jobs, plugin_management, product_config, bug, audit |
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
| 代码巡检 | code_inspection, scheduled_jobs | 周期性代码仓库质量、安全和规范巡检，按提交人沉淀报告、finding、通知反馈、严重问题 Bug、整改任务和治理概览 | 基于产品 Git 资源和插件扫描动作生成，关联产品、仓库、提交人、定时作业运行、Bug、整改任务和通知记录；治理概览从报告、finding、质量门禁、Bug 关联状态和整改任务派生状态聚合趋势、规则、仓库/分支/提交人排行和严重问题 SLA |
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
角色定义的运行时来源是后端角色目录常量，持久化字典为 PostgreSQL `role_definitions` 表；每个角色必须同时声明业务角色映射 `business_roles`、可见入口 `menu_scope` 和限制边界 `limitations`，用于角色管理、用户管理角色目录和知识权限配置的一致展示。`users.roles` 和知识 `permission_roles` 只允许引用该目录中的角色 code。系统管理/角色管理页面必须从 `/api/auth/roles` 只读展示角色定义；用户管理页面和知识权限配置必须从同一接口加载固定多选控件，不能让管理员自由输入或创建未定义角色。系统管理/菜单管理页面维护 PostgreSQL `menu_resources`，可编辑菜单名称、父级、路由路径、图标、排序、状态和页面访问权限点；数据库菜单只控制左侧导航元数据、可见性和权限映射，前端页面组件仍必须存在于静态路由注册表，不能让数据库任意 path 动态加载未注册组件。

后续系统权限管理按 [RBAC 重设计](rbac-redesign.md) 演进，开发执行以 [RBAC Redesign Implementation Plan](../../superpowers/plans/2026-06-09-rbac-redesign-implementation.md) 为任务级计划：固定六角色保留为 MVP 兼容预置角色模板，并新增 `developer`、`test_owner`、`tester`、`release_owner` 等研发交付扩展预置角色；角色管理从只读目录升级为角色 CRUD，并支持配置功能菜单；用户登录后后端返回 `menu_tree`，前端左侧菜单按授权菜单渲染；v1.2 引入组织/部门维度，人员归属部门，产品负责人和研发负责人等产品范围由产品管理页成员配置维护，知识权限使用独立知识空间承载产品研发和文档资料；外部 SSO 身份必须绑定到系统 `users.id` 后才参与授权计算，SSO 不直接下发角色、部门或范围；高危权限不引入双人审批流，由系统管理员配置并写入审计；业务接口逐步从角色 code 判断迁移为权限点和数据范围校验，角色、权限、菜单、部门、产品成员、知识空间、用户授权和范围授权均以 PostgreSQL 结构表为事实源。

React 工作台应提供十个主入口，而不是只围绕任务详情组织全部能力：

| 主入口 | 目标用户 | 页面能力 |
|--------|----------|----------|
| 首页 IT 团队看板 | 管理者、产品负责人、研发负责人、平台运营 | 需求总览、研发进展、Bug 趋势、线上系统健康、核心业务运行、用户使用趋势、用户反馈趋势、AI 迭代规划建议摘要、发布状态 |
| 产品管理 | admin, 产品负责人 | 产品列表、详情、版本、模块、Git 资源和相关系统维护 |
| 需求管理 | product_owner, rd_owner | 需求列表、创建时间展示、新增需求、需求详情、审批、驳回、批量分配负责人、批量推进状态、批量排期/归集需求、批量生成任务、生成任务、关闭 |
| 任务中心 | rd_owner, 产品/研发/测试/发布负责人 | 任务列表、任务详情、任务类型筛选、待确认弹窗、GitLab MR / GitHub PR 选择、diff 快照、Review 报告、Review 报告确认、自动化测试、发布上线评估、上线后分析、AI 能力配置、定时作业、插件管理、回写结果、Markdown 导出 |
| Bug 管理 | 测试负责人、研发负责人、产品负责人 | AI 自动测试 Bug、人工登记 Bug、创建时间展示、分派、修复、验证、关闭、重复归并 |
| 日志监控 | IT 管理者、研发负责人、平台运营 | GitLab 提交与代码质量、Jenkins 发布记录和线上日志指标；不展示采集运行记录和待归属数据队列 |
| 用户洞察 | 产品负责人、IT 管理者、研发负责人 | 用户反馈列表、详情弹窗、固定列宽列表、右侧固定操作列、反馈处理和转需求入口；使用指标登记与迭代建议生成不作为用户洞察页面主动作 |
| 知识中心 | 知识维护者、研发负责人 | 文档导入、索引状态、知识检索、沉淀审核、权限和标签维护；第一阶段已按 [知识管理升级设计](knowledge-management-design.md) 引入空间、目录、MinIO/S3-compatible 资产、导入任务和 chunk set，后续继续演进解析器、父子分块和质量治理 |
| 审计与运行 | admin, 平台运营 | 审计事件、运行记录、健康检查和失败排查 |
| 系统管理 | admin | 用户管理、角色管理、菜单管理、模型网关配置；菜单管理维护 `menu_resources`、排序、启停和 `required_permissions`，角色管理配置角色可见菜单和权限点，模型网关页面只展示 API Key 是否已配置，新增或编辑时可提交密钥，编辑留空表示保留服务端现有密钥；AI 能力配置、定时作业和插件管理归入任务中心菜单 |

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
assistant_conversations ──< assistant_chat_runs

requirements ──< ai_tasks
```

### 核心表结构

| 表名 | 说明 | 关键约束 |
|------|------|----------|
| role_definitions | 系统角色字典 | `code` 主键；记录 `category`、`business_roles`、`responsibilities`、`data_scope`、`decision_scope`、`menu_scope`、`limitations`、`permissions`、`is_assignable` 和 `sort_order`；MVP 可分配角色为 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer`。 |
| permissions | 系统权限点目录 | `code` 主键，记录权限名称、分类、风险等级、状态和是否系统内置；接口鉴权以权限点为安全边界。 |
| menu_resources | 左侧菜单资源 | `code` 主键，记录 `name/path/parent_code/menu_type/icon/sort_order/required_permissions/status/is_system`；只维护导航和路由权限元数据，页面组件加载仍受前端静态路由约束。 |
| role_permissions | 角色权限授权 | `role_id + permission_code` 唯一，整体替换授权时写入审计。 |
| role_menu_grants | 角色菜单授权 | `role_id + menu_code` 唯一，控制 `/api/auth/me.menu_tree` 和左侧导航可见性，不能替代后端接口权限校验。 |
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
| integration_plugins | 集成插件定义 | 记录插件 `code`、`name`、`protocol=http/mcp_http/mcp_stdio/runner_polling/runner_websocket`、`category`、risk_level、`is_system` 和状态；`category` 必须使用约定枚举 `general/data_warehouse/devops/issue_tracking/observability/knowledge_base/collaboration/ai_service/business_system`，前端以选择项维护，后端拒绝自由文本；非官方插件列表必须提供编辑和删除入口，允许维护名称、分类、协议、风险等级、状态和说明；`gitlab`、`github`、`email`、`ai_executor` 作为 `is_system=true` 官方标准插件由系统种子维护，页面展示官方标准标签且不提供编辑/删除，后端 PATCH/DELETE 返回 409；插件管理提供官方插件市场只读目录，服务端根据标准插件种子和当前运行配置返回发布方、简介、推荐场景、连接模板版本、连接默认 payload、动作模板、安装状态、插件 ID、连接数和动作数，前端可从市场项引导新增连接或直接创建对应官方动作模板，但不得修改官方插件定义；新增连接表单和 AI 助手连接草案必须复用服务端 `connection_defaults`，不得在前端或助手中另行硬编码 GitHub/GitLab/邮箱/AI 执行器默认 endpoint、认证或 Params/Headers；邮箱连接默认覆盖邮件网关/API endpoint、SMTP/IMAP/POP3 收发参数、默认发件人/收件人和轮询时间窗口；AI 执行器连接默认覆盖 `runner_polling`、`executor_type=codex`、`supported_executor_types=codex/claude/hermes/openclaw`、`runner_id`、workspace、超时和结果回写地址；AI 执行器 Runner 配置页需提供 Codex、Claude Code、Hermes、OpenClaw 命令参数、目标系统、CPU 架构、安装模式和工作区白名单，并可下载按目标系统区分的安装包：公共文件包含 env、manifest、runner_config、START_STOP.md 启停说明和 AI Brain Runner Skill，START_STOP.md 必须说明启动、停止、状态查看、重启、禁用自启以及页面停用不等于本机进程退出；Linux/macOS/Windows/Docker/通用手动安装分别包含对应启动脚本或服务模板；安装包不得包含反推 token，只能使用 `<runner_token>` 占位；执行器列表需提供测试入口，诊断系统默认执行器托管状态，或本地/远程 Runner 注册状态、Token、执行器类型、endpoint 与心跳。删除前必须检查下级连接、动作、定时作业和调用日志，被使用时返回 409 并提示使用清单；第一阶段 HTTP、MCP HTTP 与 Runner 轮询可执行，MCP stdio 仅允许登记配置；AI 执行器真实执行必须经 Runner 隔离、授权和审计。 |
| plugin_connections | 插件连接配置 | 记录插件归属、环境、endpoint_url、auth_type、auth_config、request_config、超时、重试、状态、`last_test_summary` 和 `test_history`；`environment` 必须使用约定枚举 `default/dev/test/staging/prod/sandbox`，前端以选择项维护，后端拒绝自由文本，连接列表和 `GET /api/system/plugin-connections` 必须支持按环境筛选并在仓储查询层过滤，便于维护多环境实例；新增和编辑连接时认证配置默认按 `none/bearer/api_key_header/basic` 展示 Token、Header 或 Basic 字段并生成 `auth_config`，JSON 仅作为高级修改入口且可反向同步到可视化字段；选择 GitLab 官方插件时默认 endpoint 为 `http://gitlab.local`、认证为 `api_key_header`、Header 名为 `PRIVATE-TOKEN`，并提供“GitLab 地址”业务字段，支持本地自建 GitLab 项目 URL，保存时自动同步 endpoint_url 并解析 `api_version/project_id/project_path/group_id` 到 `request_config.query`；选择 GitHub 官方插件时默认 endpoint 为 `https://api.github.com`、认证为 Bearer Token，并提供 `Accept`、`X-GitHub-Api-Version` Headers 和“仓库地址”业务字段，保存时自动解析 `owner/repo` 到 `request_config.query`；选择邮箱官方插件时默认 endpoint 为 `https://mail-gateway.example.com/api`、认证为 `api_key_header`、Header 名为 `Authorization`，并提供 `Content-Type=application/json` Header 和 `mail_provider/default_from/default_to/subject_template` Params；连接级公共 Params/Headers 默认以表格维护并生成 `request_config.query` 和 `request_config.headers`，高级请求 JSON 仅用于精修且可反向同步；连接列表提供环境筛选、编辑、测试、最近测试摘要和删除入口，测试 endpoint 可达性、认证和连接级 Params/Headers 配置并写入审计，测试结果必须包含 endpoint、协议、认证、HTTP 请求或 MCP `tools/list` 诊断步骤，并在请求调试台展示最终 URL、解析后的 query、headers 明文值、Header 来源、原始请求配置、动态变量解析区块、可复制 cURL、完整请求 JSON 和远端响应摘要；测试完成后服务端必须把轻量 `last_test_summary={checked_at,status,latency_ms,error_code,error_message,failed_step,response_status_code,mocked}` 保存到连接记录，并将最近 N 次测试快照保存到 `test_history`，列表展示状态、耗时和错误码/失败步骤；当次测试响应必须返回 `action_template_draft` 和 `repair_suggestions`，请求回放台展示最近测试记录、变量解析前/解析后差异，并支持复制当次请求为动作草案；完整请求响应只保留在当次诊断弹窗和调用日志摘要里；动态变量解析区块即使无变量也展示空状态提示；删除前必须检查动作、定时作业和调用日志引用，被使用时返回 409 并提示使用清单；认证配置生成的 Authorization/API Key 等同名认证 Header 优先于 Params/Headers 表格值，若最终请求仍包含 `***` 占位必须明文展示并在诊断中标记，便于判断是否误填；运行时先解析连接级动态变量，再与动作 `request_config` 合并，同名 query/header 由动作覆盖；管理员调试场景响应按配置明文展示 token、secret、password、api_key、Authorization 等字段，PATCH 编辑收到历史占位 `***` 时必须保留服务端原始密钥值，数据库不得把插件连接当成业务数据源。 |
| plugin_actions | 动作配置 | 记录插件、默认连接、action_type=http_request/mcp_tool、输入/输出 schema、request_config、result_mapping、requires_human_review 和状态；前端新增和编辑 HTTP 动作时默认以 Params/Headers 表格维护 `request_config.query` 和 `request_config.headers`，参数值支持 `{{current_date}}`、`{{current_date-7}}` 等系统变量表达式，高级 JSON 只用于精修完整 request_config，且必须支持可视化表格与 JSON 双向同步；动作配置页展示请求预览、结果写入目标和高级 `result_mapping`，结果写入目标必须来自服务端 `result_write_targets` 注册表，注册表返回 `code/label/form_label/description/default_result_mapping/mapping_fields/supported_job_types`，前端按 `mapping_fields` 动态渲染 JSONPath 字段并在目标切换时写入注册表默认映射；首批目标包括 `scheduled_job_result`、`user_feedback_insights`、`code_inspection_reports` 和 `email_notifications`，其中用户洞察表目标展示洞察列表、源表行数和原始行列表路径，代码巡检报告目标展示仓库 ID、分支、提交 SHA、风险级别、摘要和 finding 列表路径，邮件通知记录目标展示收件人、主题、投递状态和消息 ID 路径，定时作业结果目标展示可选导入数量路径；定时作业运行详情通过 `/api/system/result-write-records?scheduled_job_run_id=<run_id>` 读取单次运行的通用结果写入读模型，读模型从正式定时作业运行的 `execution_nodes.result_action` 和无运行归属的动作调用日志聚合记录，字段包含 `write_target/write_target_label/status/source_type/scheduled_job_id/scheduled_job_run_id/plugin_action_id/plugin_invocation_log_id/records_imported/summary_fields/preview/feedback`，同时保留 `write_target/status/scheduled_job_id/plugin_action_id` 等筛选能力供排障使用；`email_notifications` 记录在摘要中展示 `subject/delivery_status/delivery_id/sample_records`，未知未来目标按目标 code 作为标签并保留通用 `preview/feedback` JSON；插件管理只展示插件、连接和动作配置，不展示独立调用日志页签；插件调用日志统一在定时作业运行详情和结果写入记录中体现。新增动作必须从服务端 `plugin-action-templates` 目录读取 GitHub 代码巡检、GitLab 代码巡检、邮箱通知发送、邮件收取和 AI 执行器场景模板，模板返回 `code/name/plugin_code/plugin_id/action_type/default_code/default_name/request_config/result_mapping/form_defaults/template_version`，前端按 `plugin_code` 解析当前实例的插件 ID 和默认连接，并动态回填请求路径、Params、Headers、结果映射和目标字段；GitHub/GitLab 模板默认使用代码扫描或 vulnerability findings 请求路径、默认 Params 和注册表中的 `code_inspection_reports` 映射，邮箱模板默认使用官方邮箱插件、`/messages/send`、`Content-Type=application/json`、收件人/主题/正文模板参数和注册表中的 `email_notifications` 映射，管理员仍可在可视化字段和高级 JSON 中调整；MaxCompute 通过普通 HTTP 插件连接和自定义 HTTP 动作配置，不作为官方动作模板强制展示；代码巡检写入报告时必须按动作或作业输出 `result_mapping` 提取 `repository_id/branch/commit_sha/risk_level/summary/findings`，JSONPath 支持 `$` 根节点以承接根数组响应；动作列表支持编辑、删除、试运行并返回请求预览、响应摘要、`result_mapping` 命中情况和 `write_preview` 写入预览，写入预览需通过同一注册表解析目标标签和默认路径，展示目标、预计写入数、候选数量、预览值、报告字段、邮件投递字段或样例记录；每次试运行必须写入 `plugin_action.trial_succeeded/failed` 审计事件，payload 仅记录插件、动作、连接、连接环境、输入字段名、写入目标、状态、耗时和错误码，不保存完整请求响应、输入 payload 或密钥；删除前必须检查定时作业和调用日志引用，被使用时返回 409 并提示使用清单；PATCH 编辑收到脱敏占位 `***` 时必须保留服务端原始敏感值；AI 助手动作草案必须复用同一模板目录生成 payload，并携带 `template_code/template_version` 用于确认来源；助手草案卡片展示 `result_mapping.write_target` 时也必须按 `/api/system/result-write-targets` 的 `form_label/label` 解析，不得维护前端本地写入目标文案表；在定时作业业务语义中，连接负责取数、Skill 负责分析处理、动作负责把处理结果送到目标位置。 |
| plugin_invocation_logs | 插件调用日志 | 记录插件、连接、动作、定时作业/运行实例、触发方式、状态、请求摘要、响应摘要、耗时、错误和 trace_id；日志只保存摘要，不保存完整敏感请求，`request_summary.request_preview.headers` 中的 Authorization、PRIVATE-TOKEN、Token、API Key、Cookie、Password、Secret 等敏感值必须在落库前和 API 返回前统一替换为 `***`。 |
| assistant_conversations | AI 助手会话 | 按 `user_id` 归属当前登录用户，记录可选 `product_id`、标题、消息数、最后消息时间、`command_signature`、内部 `source_message_hash`、`context_scope` 和标准时间字段；会话列表只返回本人记录，重复命令展示优先按 `command_signature + context_scope` 折叠，不删除真实历史。 |
| assistant_messages | AI 助手消息 | 关联 `assistant_conversations`，记录 user/assistant 角色、消息内容、可选模型、建议、`run_id`、`client_request_id`、`status=pending/completed/cancelled/failed`、取消/完成/失败时间和错误码；会话详情只允许本人读取，历史消息必须保留取消和失败状态，避免刷新后丢失停止生成结果。 |
| assistant_chat_runs | AI 助手聊天运行 | 记录单次聊天请求的 `user_id`、`conversation_id`、用户消息/助手消息 ID、`client_request_id`、`status=running/succeeded/cancelled/failed`、取消原因、取消人、取消/完成时间、错误码和元数据；停止生成接口只允许取消当前用户自己的运行，服务端在模型调用前后检查运行状态，已取消时不得写入模型完成结果。 |
| assistant_action_drafts | AI 助手动作草案 | 记录聊天生成或显式创建的 `create_rd_task`、`create_scheduled_job`、`create_plugin_connection`、`create_plugin_action`、`create_analysis_draft` 草案，包含用户、来源消息、客户端草案 ID、payload、风险、状态、`expires_at` 和确认/取消信息；确认前不写领域表或最终分析结果，过期 pending 草案自动转为 `expired`；用户打开详情或深链加载时通过查看接口写入 `metadata_json.viewed_at/detail_viewed_at/deeplink_viewed_at/last_viewed_at/view_count/viewed_by/last_view_surface`，供效果漏斗区分真实查看详情和深链打开；用户把草案应用到表单后保存时，客户端通过草案 payload 更新接口写入最终 payload、`metadata_json.user_modified/modified_fields/modified_at/modified_by` 和更新审计，再调用 confirm，供助手效果指标统计用户修改率并避免绕过服务端草案生命周期。 |
| assistant_action_runs | AI 助手动作执行记录 | 关联 `assistant_action_drafts`，记录确认执行的 action、执行人、状态、领域资源类型/ID、结果摘要和错误信息；同一草案最多一条成功执行记录，重复 confirm 已成功草案时返回既有 run。 |
| assistant_role_quick_tasks | AI 助手角色快捷任务配置 | 记录角色快捷任务组和任务项配置，包含 `enterprise_id`、`group_key/group_label/group_roles/group_enabled/group_sort_order`、`task_key/title/prompt/permissions/analytics_key/target_draft_type/enabled/sort_order/template_version/rollout_json/metadata_json/created_by/updated_by`；后端按角色、权限、启用状态、企业、模板版本、灰度和排序过滤，支持后台新增、编辑、灰度、启停、删除和审计。 |
| assistant_action_reference_configs | AI 助手 @ 动作候选配置 | 记录 `assistant_action` 候选项配置，包含 `enterprise_id`、`action_key/title/summary/prompt/url/aliases/roles/permissions/enabled/sort_order/template_version/rollout_json/metadata_json/created_by/updated_by`；后端按角色、权限、启用状态、企业、模板版本、灰度和排序过滤，同 `action_key` 配置可覆盖或禁用默认动作，支持后台新增、编辑、灰度、启停、删除和审计。 |
| ai_tasks | 用户可见 AI 任务 | 状态必须匹配统一任务状态机；`task_type` 标识产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估或上线后分析；`input_json` 保存需求快照、产品上下文、启动参数、MR/PR Review 输入快照引用和命中的研发执行器快照。 |
| rd_task_executor_policies | 研发执行器策略 | 按业务大脑、产品、任务类型和优先级匹配 Codex、Claude Code、OpenClaw 等工程执行器；策略只引用插件管理下的 AI 执行器 Runner、产品 Git 仓库、工作区、分支、指令模板、输出契约和超时，不引用 Agent/Skill。 |
| gitlab_mr_snapshots | MR/PR 兼容输入快照 | 记录 source_provider、repository_id、project_id 或 project_path、mr_iid/PR number、title、author、source/target branch、base/head sha、diff_refs、changed_files_summary、diff_storage_ref、diff_size_bytes、snapshot_hash、requirement_id、technical_solution_task_id、created_by、created_at 和 updated_at；快照不可变，重新 Review 必须创建新快照。 |
| code_review_reports | 代码 Review 报告 | 记录 task_id、MR/PR 快照、执行器元数据、summary、risk_level、findings、人工确认状态和内部归档时间；v1 MVP 不回写 GitLab/GitHub。 |
| code_inspection_reports | 代码仓库巡检报告 | 记录 product_id、repository_id、repository 快照、scheduled_job_id、scheduled_job_run_id、collector_run_id、plugin_invocation_log_id、plugin_action_id、plugin_connection_id、branch、commit_sha、scan_mode、scanner_name、scanner_version、rules_version、is_full_scan、files_scanned、lines_scanned、rules_loaded、coverage_warning、remote_url_summary、remote_url_hash、artifact_ref、checkout_path、checkout_path_retained、scan_started_at、scan_finished_at、suppressed_finding_count、suppression_summary、quality_gate、scan_profile、previous_report_id、previous_comparison、summary、risk_level、finding_count、severe_finding_count、committer_count、committer_summary、status、result_actions、created_bug_ids、created_task_ids 和 notification_ids；用于运营治理 / 代码巡检列表和详情，详情页必须展示来源作业、来源运行、数据连接/本地扫描模式、扫描快照、扫描摘要、规则命中分布、文件维度问题、质量门禁、baseline/已接受风险过滤数、结果写入动作和插件调用链路，并支持从来源作业/来源运行跳转到任务中心 / 定时作业。 |
| code_inspection_findings | 代码仓库巡检问题 | 关联 code_inspection_report，记录 rule_id、category、severity、title、description、file_path、line_number、committer_name、committer_email、committer_username、recommendation、raw、created_bug_id、created_task_id、suppression_status、suppression_reason、suppression_note、suppression_requested_by/at 和 suppression_reviewed_by/at；严重问题可派生 `source=code_inspection` Bug，也可生成 `task_type=code_inspection_remediation` 的 AI 任务用于整改闭环；误报或已接受风险需通过 pending -> approved/rejected 审批闭环后才计入报告 suppression 治理统计。 |
| code_inspection_notifications | 代码巡检通知反馈 | 关联 code_inspection_report，记录 channel、target、status、message、request_config 和 response_summary；第一阶段记录邮件、钉钉机器人等通知动作和反馈，不直接要求外部网络发送成功。 |
| graph_runs | LangGraph 运行记录 | 保存 runtime、节点路径、checkpoint 和 state snapshot 引用。 |
| human_reviews | 人工确认记录 | `version` 用于乐观锁。 |
| knowledge_spaces | 知识空间 | 当前知识权限和业务边界，绑定 owner、空间成员和后续产品/部门范围；新上传文档按空间权限读取。 |
| knowledge_folders | 知识目录 | 当前空间内信息架构，继承空间权限，不引入目录级 ACL；父目录归档后子树整体视为不可用，列表、上传和批量移动都不得继续引用归档子树。 |
| knowledge_documents | 知识文档 | 记录来源、权限和索引状态，支持主动导入、索引失败重试、归档、知识空间归属和可选目录归属。 |
| knowledge_assets | 知识文件资产 | 对象存储元数据投影，MinIO/S3-compatible 存储保存原始文件和解析产物，PostgreSQL 保存资产元数据、权限归属和审计上下文；`bucket + object_key` 唯一并作为半成功重试的幂等边界。 |
| knowledge_import_jobs | 知识导入任务 | 当前记录上传、解析、分块和向量化结果；`locked_by`、`locked_until` 和 `attempt_count` 作为 worker 数据库租约字段，防止多实例重复消费 queued 任务。 |
| knowledge_chunk_sets | 知识分块版本 | 一次解析/分块/Embedding 版本，文档通过 active chunk set 控制当前检索版本；保存 `index_status` 和 `vector_index_error`，历史版本激活时据此恢复文档索引状态。 |
| knowledge_chunks | 知识切片 | embedding 维度必须匹配配置模型。 |
| mock_issues | 模拟回写 Issue | idempotency key 唯一。 |
| knowledge_deposits | 知识沉淀候选 | `ai_task_id + deposit_type + content_hash` 去重。 |
| audit_events | 审计事件 | 记录任务、主体类型、主体 ID、事件类型、操作者、事件载荷、写入序号和创建时间。 |
| execution_trace_snapshots | 执行诊断链路快照 | 可重建的只读诊断 read model，记录链路根对象、状态、开始/更新时间、耗时、节点/失败/运行中数量、关联 ID、节点、边和 source fingerprint；PostgreSQL 运行时由 ExecutionTraceBuilder 刷新写入，列表和详情优先从该表分页/过滤/排序读取，不作为定时作业、插件、Runner、模型网关、代码巡检或审计的事实源。 |
| gitlab_daily_code_metrics | GitLab 每日代码指标 | 按 product_id、repository_id、metric_date 聚合提交、人员、质量和风险摘要。 |
| jenkins_release_records | Jenkins 发布记录 | 按 product_id、version_id、job_name、build_id 记录构建、部署、失败原因和触发人。 |
| online_log_metrics | 线上运行日志指标 | 按 product_id、module_code、environment、time_window 聚合错误率、延迟和核心业务事件。 |
| user_usage_metrics | 用户使用指标 | 按 product_id、module_code、feature_code、user_segment、time_window 聚合活跃、访问、转化、停留、异常退出和低使用功能。 |
| user_feedback | 用户反馈记录 | 记录来源渠道、反馈类型、满意度或情绪倾向、标签、关联产品模块、创建人、处理状态和可选关联需求；转需求后状态同步为 `linked`。 |
| collector_runs | 采集运行记录 | 记录 collector_type、product_id、source_system、status、started_at、finished_at、records_imported、error_message 和 payload_summary；`collector_type` 除 DevOps/反馈采集外还必须覆盖定时作业运行产生的 `code_inspection`、`dashboard_snapshot_refresh`、`lifecycle_context_refresh`、`plugin_action_invoke` 和 `pending_attribution_retry`；终态不可回到 running，failed 必须有错误说明。 |
| scheduled_jobs | 定时系统作业定义 | 记录 job_type、schedule_type、cron_expression/interval_seconds、timezone、enabled、product_id、source_system、config_json、execution_mode、agent_id、skill_ids、knowledge_document_ids、model_gateway_config_id、plugin_action_id、plugin_connection_id、plugin_input_mapping、plugin_output_mapping、result_actions、重试/超时/锁租约和 next_run_at；`plugin_connection_id` 在页面语义中作为数据连接，`agent_id` 在页面语义中作为 AI角色，`skill_ids` 作为分析处理能力，`knowledge_document_ids` 作为可选知识引用，`plugin_action_id` 作为动作模板，`source_system` 仅作为模板和审计来源标识；代码巡检作业应在 `config_json.repository_id` 固定平台产品 Git 仓库 ID，并在 `config_json.branch` 固定本次扫描分支，未填写时由后端取同仓库 `default_branch` 兜底；运行时插件输入顶层携带 `repository_id/branch`，AI 执行模式会把 `configured_repository_id/configured_branch` 注入模型上下文，写巡检报告时若扫描器或模型返回 GitLab/GitHub project_path、remote_url 或 project_id，后端必须先映射到同产品 `product_git_repositories.id`，匹配不到时再使用 `config_json.repository_id`；新增/编辑作业弹窗顶部必须根据当前表单值实时派生“数据连接、AI执行、动作、运行记录”执行链路，每段展示是否必填、已配置/待配置/可选状态和核心资源名称，数据连接节点提供“测试数据连接”按钮并展示最近一次测试状态、耗时和请求摘要；新增/编辑表单必须按“基础信息、数据连接配置、代码仓库配置、AI执行配置、动作配置、调度配置”分区展示，`code_repository_inspection` 需展示“扫描方式”“代码仓库”和“扫描分支”，`execution_mode` 用户侧标签为“AI执行”，`deterministic` 展示为“不调用 AI”；新增作业页的场景模板必须来自服务端 `scheduled-job-templates` 目录，模板返回 `code/name/category/description/payload_defaults/resource_selectors/template_version/wizard_steps`，前端只按模板目录渲染选项，按 `wizard_steps` 展示向导步骤但把 `ai_processing/result_write` 映射为“AI执行/动作”，按 `payload_defaults` 回填作业名称、cron、AI执行方式、作业类型、动态变量映射、`config_json`、来源标识和动作，按 `resource_selectors` 从当前产品、动作、连接、AI 模型、AI角色、Skill 和知识文档中选择默认资源；首批模板包括 `每周用户反馈洞察抽取`、`代码仓库质量 / 安全 / 规范巡检`、`邮件摘要收取`、`线上日志异常分析`、`GitLab MR AI 审查` 和 `AI 执行器仓库任务`，周反馈和线上日志异常模板默认走 AI/Skill 分析，线上日志模板默认写入 `job_type=online_log_ai_analysis`、`plugin_input_mapping.window_start={{current_date}}`、`plugin_input_mapping.window_end={{now}}` 和通知类 `result_actions`，代码巡检模板默认写入 `config_json.scan_mode=native_full_scan` 和 `scan_rules`，并带出写巡检报告、严重问题建 Bug、严重问题建整改任务、邮件通知等 `result_actions`，AI 执行器仓库任务模板默认写入 `config_json.ai_executor={executor_type:model_gateway,runner_id:ai_executor_runner_system_default,runner_label:系统默认执行器}`；AI 助手生成定时作业草案时也必须复用同一模板目录的默认 payload，避免页面和助手各自维护模板配置；从 AI 助手草案创建作业时，前端必须把草案来源写入 `config_json.assistant_draft`，后端审计摘要通过 `scheduled_job_audit_payload` 输出 `assistant_draft.draft_id/source/title`；从现有作业或运行快照复制为新作业时，前端只打开新增作业草稿，不直接写库，复制弹窗展示来源作业或运行快照，确认保存后把来源写入 `config_json.template_source.source_type/source_id/title`，后端审计摘要输出 `template_source`，作业列表和运行详情必须可见模板来源；前端新增/编辑保存时也必须对 AI 类型作业 `user_feedback_insight_extract/online_log_ai_analysis/iteration_plan_suggestion_generate` 校验 AI 模型、AI角色和 Skills，避免缺失 AI 装配的作业进入后端；后端对所有 AI 执行类作业同样要求作业自身 `skill_ids` 非空，不得用 AI角色 `default_skill_ids` 代替空 Skills 请求；`result_actions` 用于 `code_repository_inspection` 等作业声明写报告、建 Bug、建整改任务、通知等后续处理；`plugin_input_mapping` 支持 `{{current_date}}`、`{{current_date-7}}`、`{{last_full_week.start}}`、`{{now}}` 等动态时间 token，运行时按作业 timezone 解析；作业创建表单必须把调度方式、Cron 表达式和间隔秒数连续放在同一“调度配置”区域，隐藏连接输入参数、输出覆盖 JSON 和 `source_system` 来源标识，保留模板默认值和后端运行时解析；`plugin_output_mapping` 仅作为作业级覆盖，留空时复用动作模板 `result_mapping`；正式运行时必须复用动作写入预览生成 `execution_nodes.result_action.feedback.write_preview`，`email_notifications` 目标还要在运行详情摘要中展示投递 ID、投递状态和收件人；列表必须以“数据连接 / AI执行 / 动作 / 调度”为主列，AI执行列合并展示执行方式、模型、AI角色和 Skill 数量，动作列合并展示动作模板和结果动作；列表必须提供编辑、复制和删除入口，编辑回填现有调度、AI 装配和插件映射配置，复制生成新增草稿，删除写入 `scheduled_job.deleted` 审计。 |
| scheduled_job_runs | 定时系统作业运行实例 | 记录 scheduled_job_id、collector_run_id、source_run_id、触发方式、计划时间、运行状态、锁租约、导入数量、错误信息、result_summary、config_snapshot、resolved_agent_snapshot、resolved_skill_snapshots、resolved_prompt_snapshot、tool_policy_snapshot、resolved_plugin_snapshot、plugin_invocation_log_id，以及助手归因字段 `assistant_action_run_id/assistant_action_draft_id/assistant_source_message_id/triggered_by_assistant`；`trigger_type` 只允许 `manual`、`manual_rerun` 和 `scheduler`，其中运行记录复跑必须写入 `manual_rerun` 并记录来源运行 `source_run_id`，不得覆盖旧运行实例；由 AI 助手确认草案或聊天 run-once 直接触发的运行必须写入助手归因字段，普通 scheduler 后续运行不得仅因同一作业曾由助手创建就被归入助手指标；运行列表和运行创建响应在存在来源运行时投影轻量 `source_run_summary`，只包含来源运行 ID、状态、触发方式、导入数量、错误码、开始/结束时间和耗时，供页面对比本次复跑结果，不复制完整 result_summary、请求响应、Prompt、模型输出或密钥；`result_summary.trace_graph={nodes,edges}` 是运行 Trace DAG 读模型，节点必须包含 `id/label/status/duration_ms/retry_count/error/input/output`，用于展示数据连接、AI 执行器执行、AI执行处理、动作反馈和业务副作用节点；系统默认执行器节点必须保留 `executor_type=model_gateway`、`runner_id=ai_executor_runner_system_default`、`model_gateway_called`、`model_gateway_log_id` 和 `result_json`，本地 Runner 节点继续保留任务 ID、工作区和日志；任务中心 / 定时作业页面支持 `?tab=runs&run_id=<运行 ID>` 深链，加载运行记录后自动打开对应运行详情，供代码巡检报告和其他业务结果反查执行链路；成功运行详情可反向生成作业模板草稿，来源写入 `config_json.template_source`；运行记录页签通过聚合接口展示运行健康概览，按真实运行实例统计总运行数、成功率、失败率、平均耗时、平均导入数、AI 调用次数、模型 Token 总量、插件调用次数、动作写入成功率、状态/类型/触发方式/写入目标分布、失败原因、最近失败和慢运行；Token 仅来自匹配 `skill_processing.model_log_id` 的模型日志元数据，不读取完整 Prompt 或输出；终态 `scheduled_job_run.succeeded/failed` 审计 payload 必须输出 `scheduled_job_id/source_run_id/job_type/product_id/status/trigger_type/records_imported/collector_run_id/plugin_invocation_log_id/error_code` 等排障字段，且在存在对应配置时补充 `execution_mode/agent_id/skill_ids/model_gateway_config_id/model_gateway_called/knowledge_document_ids/plugin_code/plugin_action_id/plugin_action_code/plugin_connection_id/plugin_connection_environment/result_action_types/result_write_target` 等轻量上下文，不保存完整请求响应、Prompt、模型输出或密钥。 |
| pending_attribution_items | 待归属数据队列 | 记录 source_type、source_system、collector_run_id、raw_subject_id、summary、raw_payload、建议归属、confidence、status、resolution_action、resolved_*、created_by 和 resolved_by；pending / resolved / ignored 三态，处理不自动生成业务数据。 |
| iteration_plan_suggestions | AI 迭代规划建议 | 记录规划周期、建议需求、推荐理由、证据链、业务价值、风险信号、依赖条件、预估研发投入、建议优先级和置信度。 |
| iteration_plan_decisions | 迭代规划确认记录 | 记录产品负责人对建议的采纳、修改后采纳或驳回决定，可关联转化后的正式需求。 |
| lifecycle_context_edges | 研发上下文关系边 | 记录 source_subject 与 target_subject 的关系、置信度、来源模块和时间，用于跨阶段追溯。 |
| lifecycle_risk_signals | 全流程风险信号 | 记录需求变更、设计缺口、代码质量、Review、测试、Bug、发布和线上异常等风险信号。 |
| bugs | Bug 记录 | 来源为 `ai_auto_test / ai_post_release / manual_test / code_inspection`，状态流转覆盖分派、修复、验证和关闭；`code_inspection` 来源 Bug 必须在 evidence 中保留报告、finding、规则、文件和行号。 |
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

#### knowledge_import_jobs

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| document_id | string | 是 | 关联知识文档。 |
| source_asset_id | string | 是 | 关联原始资产。 |
| status | enum | 是 | `queued`、`parsing`、`chunking`、`completed`、`failed`、`cancelled`。 |
| locked_by | text | 否 | 获取任务租约的 worker ID；仅用于并发控制，不作为业务状态。 |
| locked_until | datetime | 否 | 租约过期时间；过期后其他 worker 可重新 claim。 |
| attempt_count | integer | 是 | worker claim 次数，用于观察重试和重复消费风险。 |
| created_by | string | 是 | 导入发起人；补偿扫描 queued 任务时继续作为解析资产、chunk set 和 chunk 写入归属。 |

#### knowledge_chunk_sets

| 字段 | 类型 | 必填 | 约束与说明 |
|------|------|------|------------|
| id | uuid/string | 是 | 主键。 |
| document_id | string | 是 | 关联知识文档。 |
| status | enum | 是 | `building`、`active`、`archived`、`failed`。 |
| index_status | enum | 否 | 该版本完成时对应的文档索引状态，历史版本激活时用于恢复文档状态。 |
| vector_index_error | text | 否 | 该版本的向量索引错误摘要；文本索引成功但向量失败时可保留。 |
| embedding_model | text | 否 | 该版本 chunk embedding 使用的模型。 |
| activated_at | datetime | 否 | 成为 active 版本的时间。 |

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
| rd_task_executor_policies | idx_rd_task_executor_policies_match | brain_app_id, product_id, task_type, status, priority | 组合索引 | 启动研发任务时按业务大脑、产品和任务类型匹配 active 执行器策略。 |
| ai_executor_tasks | idx_ai_executor_tasks_ai_task | ai_task_id, created_at | 组合索引 | 从研发任务反查 Runner 执行任务。 |
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
| code_inspection_reports | idx_code_inspection_reports_product | product_id, created_at | 普通索引 | 查询产品下代码巡检报告。 |
| code_inspection_reports | idx_code_inspection_reports_repository | repository_id, created_at | 普通索引 | 查询某仓库历史巡检报告。 |
| code_inspection_reports | idx_code_inspection_reports_risk | risk_level, created_at | 普通索引 | 按风险级别筛选巡检报告。 |
| code_inspection_reports | idx_code_inspection_reports_committer_count | committer_count, created_at | 普通索引 | 按提交人数辅助排序巡检报告。 |
| code_inspection_findings | idx_code_inspection_findings_report | report_id, severity | 普通索引 | 查询报告下 finding 并按严重级别排序。 |
| code_inspection_findings | idx_code_inspection_findings_committer_email | committer_email | 普通索引 | 按提交人邮箱筛选巡检问题和报告。 |
| code_inspection_findings | idx_code_inspection_findings_report_committer | report_id, committer_email | 普通索引 | 查询报告内某提交人的 finding。 |
| code_inspection_notifications | idx_code_inspection_notifications_report | report_id, created_at | 普通索引 | 查询报告关联通知反馈。 |
| bugs | idx_bugs_product_status | product_id, status | 普通索引 | 查询产品 Bug 状态分布。 |
| bugs | idx_bugs_source | source | 普通索引 | 区分 AI 自动测试、上线后分析、代码巡检和人工测试来源。 |
| dashboard_metric_snapshots | idx_dashboard_product_window | product_id, window_start, window_end | 普通索引 | 首页看板读取产品快照。 |
| lifecycle_context_edges | idx_lifecycle_edges_source | source_subject_type, source_subject_id | 普通索引 | 从任一主体查下游关联。 |
| lifecycle_context_edges | idx_lifecycle_edges_target | target_subject_type, target_subject_id | 普通索引 | 从任一主体查上游依据。 |
| lifecycle_risk_signals | idx_lifecycle_risk_product | product_id, severity, observed_at | 普通索引 | 首页看板和全流程感知视图读取风险。 |
| assistant_conversations | idx_assistant_conversations_user_updated | user_id, updated_at | 普通索引 | 查询当前用户最近助手会话。 |
| assistant_conversations | idx_assistant_conversations_command_signature | user_id, command_signature, context_scope, updated_at WHERE command_signature IS NOT NULL | 部分索引 | 按命令签名和上下文折叠重复助手命令会话。 |
| assistant_messages | idx_assistant_messages_conversation_created | conversation_id, created_at | 普通索引 | 按会话时间顺序读取助手消息。 |
| assistant_chat_runs | idx_assistant_chat_runs_user_status | user_id, status, updated_at | 普通索引 | 查询当前用户运行中、已取消或失败的助手聊天运行。 |
| assistant_chat_runs | idx_assistant_chat_runs_client_request | user_id, client_request_id | 普通索引 | 按客户端请求 ID 关联停止生成、重试和审计。 |
| assistant_action_drafts | idx_assistant_action_drafts_user_status | user_id, status, updated_at | 普通索引 | 查询当前用户待确认或历史草案。 |
| assistant_action_drafts | idx_assistant_action_drafts_source_message | source_message_id | 普通索引 | 从助手消息追踪草案来源。 |
| assistant_action_drafts | idx_assistant_action_drafts_expires_at | expires_at WHERE status='pending' | 部分索引 | 扫描或读取待确认草案时快速识别已过期草案。 |
| assistant_action_runs | idx_assistant_action_runs_successful_draft_unique | draft_id WHERE status='succeeded' | 部分唯一索引 | 防止同一草案重复确认产生多条成功执行记录。 |
| assistant_action_runs | idx_assistant_action_runs_draft | draft_id, created_at | 普通索引 | 查询草案确认执行记录。 |
| scheduled_job_runs | idx_scheduled_job_runs_assistant_action_run | assistant_action_run_id WHERE NOT NULL | 部分索引 | 按助手确认动作追踪定时作业运行。 |
| scheduled_job_runs | idx_scheduled_job_runs_assistant_draft | assistant_action_draft_id WHERE NOT NULL | 部分索引 | 按助手草案追踪定时作业运行。 |
| scheduled_job_runs | idx_scheduled_job_runs_assistant_message | assistant_source_message_id WHERE NOT NULL | 部分索引 | 按助手消息追踪直接触发的定时作业运行。 |
| scheduled_job_runs | idx_scheduled_job_runs_triggered_by_assistant | triggered_by_assistant, started_at | 普通索引 | 统计助手触发运行成功率和失败修复链。 |
| assistant_role_quick_tasks | idx_assistant_role_quick_tasks_group | group_key, group_sort_order, sort_order | 普通索引 | 按任务组和排序读取角色快捷任务配置。 |
| assistant_action_reference_configs | idx_assistant_action_reference_configs_order | sort_order, action_key | 普通索引 | 按排序读取 `@` 动作候选配置。 |
| assistant_action_reference_configs | idx_assistant_action_reference_configs_enterprise | enterprise_id WHERE NOT NULL | 部分索引 | 按企业读取动作候选配置。 |
| assistant_action_reference_configs | idx_assistant_action_reference_configs_scope_unique | COALESCE(enterprise_id,''), action_key, COALESCE(template_version,'') | 唯一索引 | 防止同一企业/动作/模板版本重复配置。 |

### 数据迁移

首个初始化脚本位于 `apps/api/app/db/migrations/001_init.sql`，负责 pgvector 扩展和核心表初始化。后续迁移按模块追加，例如 `002_persistence_users.sql` 补齐用户表种子数据和历史 `app_state_snapshots` 快照表，`003_role_definitions.sql` 补齐角色字典，`004_knowledge_audit_persistence.sql` 让已有环境的 `audit_events.id` 支持字符串审计 ID 并补齐 `sequence`，`005_knowledge_vector_index.sql` 为 `knowledge_chunks.embedding` 增加 pgvector HNSW cosine 索引，`006_user_feedback.sql` 补齐用户反馈结构表，`007_iteration_planning.sql` 补齐迭代规划建议和确认结构表，`008_user_usage_metrics.sql` 补齐用户使用指标结构表，`009_devops_gitlab_metrics.sql` 补齐 GitLab 每日代码指标结构表，`010_devops_jenkins_releases.sql` 补齐 Jenkins 发布记录结构表，`011_ops_online_log_metrics.sql` 补齐线上运行日志指标结构表，`012_collector_runs.sql` 补齐采集运行记录结构表，`013_pending_attribution_items.sql` 补齐待归属数据队列结构表，`014_related_system_product_context.sql` 补齐相关系统产品归属列和产品状态查询索引，`015_lifecycle_dashboard_persistence.sql` 补齐生命周期边摘要、风险上下文字段和首页看板快照结构表，`016_brain_app_task_attribution.sql` 补齐需求与 AI 任务的默认 `rd_brain` 归属、`idx_ai_tasks_brain_app` 查询索引和当前 MVP 任务类型配置，`017_langgraph_runtime_metadata.sql` 补齐 Graph Run 的 `runtime` 与 `node_path` 元数据列，`018_standard_timestamps.sql` 补齐所有历史结构表的 `created_at` 与 `updated_at` 标准时间字段，`019_assistant_chat_history.sql` 补齐 AI 助手会话和消息结构表，`020_knowledge_text_index_fallback.sql` 补齐知识文档向量索引错误字段并将历史 `indexed` 状态升级为 `vector_indexed`，`021_model_gateway_embedding_capability.sql` 补齐模型网关 Embedding 连接模式、独立凭据和向量维度字段，`022_optional_requirement_version.sql` 将需求和 AI 任务版本字段改为可空，并把历史 `pending_approval` / `task_created` 需求状态迁移为 `submitted` / `designing`，`023_db_first_id_counters.sql` 新增 `id_counters` 作为 DB-first 迁移期的数据库发号表，`024_task_query_performance.sql` 补齐任务管理远程筛选分页和待确认直查所需索引，`030_requirement_source.sql` 补齐需求来源字段和来源/创建时间查询索引。当前业务大脑只读配置、产品、版本、模块、Git 资源、相关系统、需求、AI 任务、Review、Graph Run、Checkpoint、GitLab MR 快照、Code Review 报告、知识文档、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属队列、迭代规划建议/确认、生命周期上下文边、生命周期风险信号、首页看板快照、模拟 Issue 回写、模型网关配置、模型调用元数据、AI 助手会话和助手消息会同步到对应结构表，启动恢复只读取结构表，不再从 `app_state_snapshots` 恢复业务集合；外部线上日志自动采集器仍按后续切片接入。已有环境必须通过可重复执行的 SQL 迁移脚本升级，不得通过清空 PostgreSQL 数据卷绕过迁移问题；PostgreSQL 镜像升级必须保持和数据目录相同的主版本，例如现有 PG18 数据卷使用 PG18 + pgvector 镜像，不能直接切到 PG16；回滚脚本不得破坏生产数据。

`031_rbac_foundation.sql` 创建或补齐 `permissions`、`menu_resources`、`role_permissions`、`role_menu_grants`、`user_roles`、`role_scope_grants` 和角色变更事件等 RBAC 结构，并种子化系统菜单、权限点和 admin 授权；`053_menu_management.sql` 为既有环境追加系统管理 / 菜单管理入口与 `system.menus.read/manage` 权限，确保旧库升级后无需清空数据卷即可进入菜单管理页。

RBAC 策略矩阵为只读聚合能力，不新增生产写表；服务端基于 `permissions`、`roles`、`role_permissions`、`menu_resources`、`role_menu_grants` 和 `role_scope_grants` 实时构建角色矩阵，输出每个角色的权限点数量、菜单入口数量、数据范围摘要、高风险权限和“菜单已授权但缺少所需权限点”的诊断项。角色管理页面必须优先展示该矩阵摘要，用于排查菜单可见、接口不可用、范围未配置和高危权限授权等问题；角色授权写入仍通过角色权限、角色菜单和角色范围接口完成。

`035_scheduled_ai_jobs.sql` 补齐 `ai_skills`、`ai_agents`、`scheduled_jobs` 和 `scheduled_job_runs` 结构表，包含运行状态、作业类型、执行模式、启停、due job、锁租约、产品归属、时间窗口、AI角色（Agent）/Skill 引用和配置快照 JSONB 字段；`044_scheduled_job_run_source.sql` 为既有库补充 `scheduled_job_runs.source_run_id` 与查询索引，用于追踪复跑来源；`045_scheduled_job_collector_types.sql` 重新收敛 `collector_runs.collector_type` 约束，补齐 `code_inspection`、`dashboard_snapshot_refresh`、`lifecycle_context_refresh`、`plugin_action_invoke` 和 `pending_attribution_retry` 等定时作业运行类型，避免旧库运行新作业时在 collector run 写入阶段 500；所有新增表仍必须包含 `created_at` 与 `updated_at` 标准字段，并通过 repository/source rows 读取，不得回退到 `app_state_snapshots`。

`061_assistant_metrics_and_role_quick_tasks.sql` 为 `scheduled_job_runs` 增加 `assistant_action_run_id`、`assistant_action_draft_id`、`assistant_source_message_id` 和 `triggered_by_assistant`，用于把助手触发运行和普通调度运行拆开归因；该迁移同时创建 `assistant_role_quick_tasks` 配置表，包含企业、模板版本、灰度 JSON、创建人和更新人字段，并创建企业、任务组排序和企业/任务/版本唯一索引，支持角色快捷任务按配置、启停、企业、版本和灰度读取。

`063_assistant_chat_runs.sql` 创建 `assistant_chat_runs` 表，并为 `assistant_messages` 追加 `status`、`client_request_id`、`run_id`、`cancelled_at`、`completed_at`、`failed_at` 和 `error_code` 字段；`assistant_messages.status` 必须通过数据库 CHECK 约束限制为 `pending/completed/cancelled/failed`，用于支持服务端取消生成、消息生命周期追踪和历史可恢复状态。

`064_assistant_action_reference_configs.sql` 创建 `assistant_action_reference_configs` 表，包含企业、动作 key、标题、摘要、提示、URL、别名、角色、权限、启停、排序、模板版本、灰度 JSON、创建人和更新人字段，并 seed 首批官方 `assistant_action` 默认候选；迁移只在默认记录缺失时插入，不覆盖后续运营修改。

`065_assistant_operability_improvements.sql` 为 `assistant_conversations` 增加 `command_signature`、`source_message_hash` 和 `context_scope`，并补充命令签名索引，用于最近对话按重复命令折叠但保留真实历史；同时新增 `assistant.action_references.manage` 权限和系统管理菜单 `/system/assistant-action-references`，供管理员运营 `@` 能力入口。

`041_code_inspection_governance.sql` 补齐代码仓库巡检治理结构：为 `scheduled_jobs` 增加 `result_actions` JSONB 字段，创建 `code_inspection_reports`、`code_inspection_findings` 和 `code_inspection_notifications`，并补充 `code_inspection.read` 权限、运营治理 / 代码巡检菜单和角色授权。该迁移用于 `code_repository_inspection` 作业落地，不得把巡检报告只保存在插件调用日志或运行摘要中。

`042_code_inspection_committer_dimension.sql` 为代码巡检报告增加 `committer_count` 和 `committer_summary`，为 finding 增加 `committer_name`、`committer_email`、`committer_username`，补充提交人索引，并把菜单/权限显示名称从“代码审查”收窄为“代码巡检”。

`043_official_devops_plugins.sql` 为 `integration_plugins` 增加 `is_system` 字段，并种子化 `gitlab`、`github`、`email`、`ai_executor` 官方标准插件；官方插件定义由系统维护，用户只能新增连接配置 endpoint、认证和 Params/Headers，不能修改或删除插件定义。`ai_executor` 默认协议为 `runner_polling`，表示必须通过隔离 Runner 承接 Codex/Claude/Hermes/OpenClaw 等执行器，不能在 Web/API 进程中直接执行本机命令。

`049_ai_executor_runners.sql` 补齐 AI 执行器 Runner 运行时结构：`ai_executor_runners` 保存 Runner 名称、协议、endpoint、支持执行器类型、工作区白名单、Token hash、心跳超时、并发和状态；`ai_executor_tasks` 保存下发给 Runner 的指令、工作区、输入 payload、请求配置、执行结果、日志、状态、插件调用日志、定时作业和运行关联。该迁移同时放开插件协议枚举，允许 `runner_polling` 与 `runner_websocket`。Runner 通过心跳、认领和完成回写接口更新任务状态；完成回写必须同步更新插件调用日志、`scheduled_job_runs.result_summary.execution_nodes.runner_execution`、结果动作反馈、collector run 和作业最近运行状态。

`066_rd_task_executor_policies.sql` 新增 `rd_task_executor_policies`，并为 `ai_executor_tasks` 补齐可空 `ai_task_id` 反链。研发任务启动时先按任务类型、产品和优先级解析 active 策略；命中策略后只向插件管理下的 Codex、Claude Code 或 OpenClaw Runner 投递工程执行任务，不装配 Agent/Skill。Runner 认领、追加日志、完成、取消或超时回写时必须同步 `ai_tasks.input_json.executor/output_json.executor`、任务状态和审计；成功结果进入 `waiting_review` 并创建待确认 `human_reviews`，失败或超时进入可排障失败态。

`050_code_inspection_remediation_tasks.sql` 为代码巡检闭环补齐整改任务反链：`code_inspection_reports.created_task_ids` 保存本次巡检派生的整改 AI 任务 ID 列表，`code_inspection_findings.created_task_id` 反向关联具体 finding 派生任务。该迁移配合 `create_task_for_severe_findings` 结果写入动作使用，任务写入 `ai_tasks` 并保留报告、finding、仓库、文件、行号、规则和修复建议上下文。

`055_code_inspection_native_scan.sql` 为 `code_inspection_reports` 增加 `scan_mode`、`scanner_name`、`is_full_scan`、`files_scanned`、`lines_scanned`、`rules_loaded` 和 `coverage_warning`，用于区分本地完整扫描、外部告警同步和平台触发扫描，并让报告详情可展示扫描覆盖率与规则版本。

`056_code_inspection_scan_snapshot.sql` 为 `code_inspection_reports` 增加 `artifact_ref`、`checkout_path`、`checkout_path_retained`、`remote_url_hash`、`remote_url_summary`、`scan_started_at`、`scan_finished_at`、`scanner_version`、`rules_version`、`suppressed_finding_count`、`suppression_summary`、`quality_gate`、`scan_profile`、`previous_report_id` 和 `previous_comparison`，用于追踪每次本地扫描实际使用的代码快照、脱敏远端摘要、扫描/规则版本、baseline/忽略过滤、质量门禁结果和同仓同分支上次扫描对比。

`070_code_inspection_suppression_approval.sql` 为 `code_inspection_findings` 增加 suppression 审批字段和 `none/pending/approved/rejected` 状态约束，并建立 `idx_code_inspection_findings_suppression_status` 索引。该迁移用于将“误报/忽略”从配置级过滤扩展到报告详情逐条治理，申请、批准和驳回必须写入审计事件，批准后同步回写报告级 `suppressed_finding_count` 与 `suppression_summary`。

`051_ai_executor_runner_controls.sql` 为 `ai_executor_runners` 增加 `token_version` 和 `token_rotated_at`，支持管理员轮换 Runner token、页面展示 Token 版本和最近轮换时间；Runner 任务日志、取消和超时熔断复用 `ai_executor_tasks.logs/status/error_*` 字段并同步关联定时作业运行。

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
| AI 助手聊天 | POST | /api/assistant/chat | 基于当前 AI Brain 系统上下文和模型网关 Chat 能力回答产品、迭代进度、任务、阻塞需求、待确认 Review、代码评审结论、Bug 分布、知识沉淀、Git 仓库和模型网关状态问题，并按用户保存会话历史；对“新增任务”等泛化创建意图可直接返回 `assistant.task_creation_guide` 确定性工具结果，澄清研发任务、定时作业、AI能力配置、插件动作、代码巡检和反馈洞察等任务类型，前端按草案优先向导展示，所有任务项 `wizard_steps` 必须统一为“数据来源、AI处理、结果动作、调度策略、确认执行”，响应 `suggestions` 必须同步提供这六类任务入口；泛化“新增 AI能力配置/AI角色/Skill”必须先返回任务类型向导，明确场景后的“新增代码巡检 AI能力配置草案”才进入 Skill / AI角色服务端草案生成；对“插件连接为什么失败/连接失败怎么修”等诊断意图可直接返回 `assistant.plugin_connection_diagnostic` 确定性工具结果，按连接配置、最近测试和修复建议解释失败原因；确定性识别必须返回 `message.intent` 元数据，工具结果可在顶层带 `intent_code/intent_confidence/required_refs`，不得把识别字段写入既有业务 `summary`。 |
| AI 助手运行状态 | GET | /api/assistant/runtime-status | 返回助手运行环境自检，包含 `ready`、`mode`、模型网关、Embedding、Redis、长期记忆和 `checks[]` 修复建议；检查项区分 `required/severity`，前端据此展示规则能力模式、必需/增强能力和配置入口。 |
| AI 助手聊天运行 | GET/POST(cancel) | /api/assistant/chat-runs, /api/assistant/chat-runs/{run_id}/cancel | 按当前用户查询 `running/cancelled/failed/succeeded` 聊天运行，用于页面刷新后恢复未完成生成和最近停止记录；取消接口必须写入 `assistant_chat_runs` 与关联 `assistant_messages` 终态，并尽量中断仍在等待的模型网关请求，避免已取消回复后续落库覆盖。 |
| AI 助手角色快捷任务 | GET | /api/assistant/role-quick-tasks | 返回当前用户可见的角色快捷任务组，后端优先读取 `assistant_role_quick_tasks` 配置表并按角色、权限、启用状态、企业、模板版本、灰度和 `sort_order` 过滤；仅配置表为空时回退内置默认目录，前端只渲染返回结果并回填 `prompt`，不得硬编码产品、研发、测试、知识或管理员快捷入口。 |
| AI 助手角色快捷任务配置 | GET/POST/PATCH/DELETE | /api/assistant/role-quick-task-configs | 管理员运营角色快捷任务配置，支持新增、编辑、删除、查看全部配置；写入 `assistant_role_quick_task.created/updated/deleted` 审计。 |
| AI 助手角色快捷任务启停 | POST | /api/assistant/role-quick-task-configs/{config_id}/status | 管理员启用或停用任务项/任务组，写入 `assistant_role_quick_task.status_changed` 审计。 |
| AI 助手角色快捷任务灰度 | PUT | /api/assistant/role-quick-task-configs/{config_id}/rollout | 管理员调整 `enterprise_id/template_version/rollout_json`，用于企业、模板版本、用户/角色白名单、时间窗和百分比灰度过滤，写入 `assistant_role_quick_task.rollout_changed` 审计。 |
| AI 助手 @ 能力配置 | GET/POST/PATCH/DELETE | /api/assistant/action-reference-configs | 具备 `assistant.action_references.manage` 权限的用户维护输入框 `@` 和 `+` 菜单里的动作入口，支持启停、排序、权限、角色、企业、模板版本、灰度和审计；系统管理页为 `/system/assistant-action-references`。 |
| AI 助手 @ 能力启停/灰度 | POST/PUT | /api/assistant/action-reference-configs/{config_id}/status, /api/assistant/action-reference-configs/{config_id}/rollout | 具备 `assistant.action_references.manage` 权限的用户启停动作入口或调整企业、模板版本、灰度策略，写入 `assistant_action_reference_config.status_changed/rollout_changed` 审计。 |

AI 助手前端发送包含 `执行一次/立即运行` 等意图的 `@定时作业` 命令时，若用户在候选请求返回前点击发送或按 Enter，客户端必须在提交 `/api/assistant/chat` 前用当前 `@` 文本按 `type=scheduled_job` 补查一次引用候选，并把唯一可用的 `scheduled_job` 引用随请求提交；候选补查失败时仍允许后端显式 @ 名称解析兜底。后端必须优先使用请求中的结构化 `references[]` 作为可控上下文，文本 `@...执行一次` 只作为无结构化作业引用时的兜底解析；若结构化定时作业引用不可运行，必须返回明确的不可执行、权限不足或草案兜底结果，不得被文本别名或官方周反馈消歧覆盖。后端解析无结构化作业引用的 `@提取每周用户反馈有价值信息 执行一次` 等周反馈命令时，必须按官方模板标记、`job_type=user_feedback_insight_extract`、名称中的用户反馈/洞察/提取/每周语义和可执行状态评分，`source_system=aliyun-maxcompute` 只能作为弱辅助信号；分数唯一最高且 `enabled=true/status=active` 时执行官方周反馈洞察作业，无法区分时要求用户点选或生成草案。`@` 引用候选面板必须分组展示候选，并在每个候选项中显式展示引用类型、权限状态、来源模块、更新时间和轻量摘要；候选加载完成但无匹配对象时，面板不得静默消失，必须提示用户更换关键词或检查访问权限。对 AI 类长链路作业，聊天响应可先返回 `running/queued` 运行记录，但前端运行卡片必须持续轮询同一运行，running/queued 期间从 `result_summary.execution_nodes` 提取当前未完成节点并展示“执行进度：数据连接/AI 执行器/AI处理/结果动作（状态）”，即使运行状态仍是 `running/queued`、只更新了执行节点摘要，也必须刷新卡片；终态后显示最新状态、导入记录，并额外标注“已刷新到最新状态：成功/失败”，避免气泡初始 `running` 文案让用户误以为命令没有真正执行。

AI 助手聊天生成必须以 `assistant_chat_runs` 作为服务端运行真相：前端刷新或重新进入页面时通过 `GET /api/assistant/chat-runs?status=running,cancelled` 恢复未完成或最近停止的生成，并允许用户打开所属会话继续处理；用户点击停止或发送停止类命令时，服务端必须先写入运行取消状态，再尝试中断模型网关请求，后续模型返回不得把已取消消息改写为完成态。`GET /api/assistant/metrics` 必须把聊天运行成功率、取消率、失败率、平均耗时和模型失败率纳入助手效果指标，且只按当前登录用户归因。
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
| 启动 AI 任务 | POST | /api/ai-tasks/{id}/start | 启动研发任务；若命中 active 研发执行器策略，则创建 `ai_executor_tasks` 并返回 `executor_task_id/runner_id`，任务进入 `running/waiting_ai_executor`，Runner 完成后回写待确认结果；未命中策略时沿用 LangGraph/模型网关或 code_review executor 路径；`model_gateway_failed`、`code_review_executor_failed` 或 `executor_failed` 的失败任务可同 task_id 重试；端点由 `app.api.routers.tasks` 单一路由承载。 |
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
| 代码巡检报告 | GET | /api/governance/code-inspections, /api/governance/code-inspections/{report_id} | 查询周期性代码仓库巡检报告列表和详情，列表优先使用 PostgreSQL read model 完成产品 scope、仓库、风险、状态、摘要、提交人筛选以及排序分页，返回仓库、分支、提交人、风险级别、finding 统计、问题明细和通知反馈；端点由 `app.api.routers.code_inspections` 单一路由承载。 |
| Jenkins 发布 | GET/POST | /api/devops/jenkins/releases | 登记或查询按产品和版本归属的发布记录。 |
| 线上运行日志 | GET/POST | /api/ops/online-log-metrics | 登记或查询按产品、模块、环境和时间窗口归属的线上运行日志指标。 |
| 采集运行记录 | GET/POST/PATCH | /api/collectors/runs, /api/collectors/runs/{run_id} | 历史兼容 API：查询、登记和结束 DevOps/洞察采集运行台账，不自动生成指标；当前前端不提供入口。 |
| AI 能力配置 | GET/POST/PATCH | /api/system/ai-skills, /api/system/ai-agents | 管理 AI角色（Agent）、Skill、默认模型网关、工具策略、Prompt 模板、输入/输出 Schema 和启停状态；配置变更必须审计，密钥不在配置中保存。 |
| 研发执行器策略 | GET/POST/PATCH/DELETE | /api/delivery/rd-task-executor-policies, /api/delivery/rd-task-executor-policies/{policy_id} | 管理需求交付下研发任务到工程执行器的匹配策略；策略只允许选择 Codex、Claude Code、OpenClaw 执行器类型和插件管理下的本地/远程 Runner，可选绑定产品、产品 Git 仓库、分支、工作区、指令模板、输出契约、超时、优先级和状态，不允许配置 Agent/Skill；任务类型配置覆盖 PRD/原型/产品详细设计、技术方案、代码实现/开发计划、代码评审、自动化测试、代码整改、发布上线评估和上线后分析；创建、修改和删除必须写入审计。 |
| 插件管理 | GET/POST/PATCH/DELETE/POST(invoke/trial/copy) | /api/system/plugin-marketplace, /api/system/plugins, /api/system/plugins/{plugin_id}/copy, /api/system/plugin-connections, /api/system/plugin-connections/{connection_id}/test, /api/system/plugin-system-variables, /api/system/plugin-actions, /api/system/plugin-actions/{action_id}/invoke, /api/system/plugin-actions/{action_id}/trial, /api/system/result-write-targets, /api/system/plugin-invocation-logs, /api/system/ai-executor-runners, /api/system/ai-executor-runners/{runner_id}/test, /api/system/ai-executor-runners/{runner_id}/install-package, /api/system/ai-executor-runners/{runner_id}/rotate-token, /api/system/ai-executor-tasks/claim, /api/system/ai-executor-tasks/{task_id}/complete, /api/system/ai-executor-tasks/{task_id}/logs, /api/system/ai-executor-tasks/{task_id}/cancel, /api/system/ai-executor-tasks/timeout-scan | 管理 HTTP/MCP HTTP/MCP stdio/Runner 插件、三方系统连接、动作配置和 AI 执行器；插件管理页面不展示独立调用日志页签，插件调用日志由定时作业运行详情和结果写入记录统一消费，`/api/system/plugin-invocation-logs` 保留为运行排障兼容 API；官方插件市场只读展示 GitLab/GitHub/邮箱/AI 执行器标准插件的简介、推荐场景、`connection_defaults/connection_template_version/connection_schema`、动作模板、安装状态、模板版本状态和连接/动作数量，并可引导新增连接、直接创建官方动作模板或复制为自定义插件；`connection_schema` 是页面动态表单契约，按 section/field 声明字段 label、path、type、required、options 和是否支持系统变量，JSON 仅作为高级修改；非官方插件、连接和动作新增后必须可编辑、可删除维护；GitLab/GitHub/邮箱/AI 执行器作为官方标准插件返回 `is_system=true`，不能修改或删除，实例 endpoint、认证和平台参数在连接里维护；MaxCompute 作为普通 HTTP 插件/连接维护，历史官方 MaxCompute 需自动降级为 `is_system=false/protocol=http`，编辑连接时不展示“项目与表配置”官方 schema；官方插件可通过 copy 接口生成 `is_system=false/source_plugin_id/template_version/version_status=custom` 的自定义插件，用于企业私有扩展，源官方插件保持只读；邮箱连接模板覆盖发送和收取参数，AI 执行器模板默认使用系统默认执行器 `ai_executor_runner_system_default`、`executor_type=model_gateway` 和 `model-gateway://default`，由平台默认模型网关直接执行指令；如需 Codex/Claude/Hermes/OpenClaw，本地 Runner 连接可改选对应执行器类型、Runner、工作区和回写地址；执行器列表必须只读展示系统默认执行器，`health_status=managed`、无需 Token/心跳/启动命令，不允许编辑、删除或轮换 Token；本地 Runner 列表继续展示 `health_status`、`heartbeat_age_seconds`、可复制 `setup_command`、Token 版本、最近轮换时间、最近任务状态和按目标系统生成的安装包下载入口，便于本地 Runner 注册和运维；执行器列表每行提供“测试”入口，展示系统托管或 Runner 注册、Token、类型、endpoint、心跳诊断；管理员可轮换本地 Runner Token、查看任务日志、取消运行中任务并触发超时熔断；连接列表支持 `environment/plugin_id/status` 查询筛选，环境只接受 `default/dev/test/staging/prod/sandbox`；删除前必须提示使用清单，后端对被引用资源返回 409；连接密钥脱敏，PATCH 编辑不得用脱敏占位覆盖真实密钥；连接测试返回诊断步骤、原始与最终请求摘要、可复制 cURL、`variable_resolutions` 动态变量解析明细、`test_history` 最近记录、`action_template_draft` 动作草案和 `repair_suggestions` 修复建议，动作支持请求预览和试运行；配置和调用必须审计。 |
| 定时系统作业 | GET/POST/PATCH/DELETE/POST(run/dry-run) | /api/system/scheduled-jobs, /api/system/scheduled-jobs/dry-run, /api/system/scheduled-jobs/{job_id}, /api/system/scheduled-jobs/{job_id}/run | 管理采集、AI 分析、动作调用、迭代建议、看板刷新等作业计划；支持手动触发、从运行记录复跑、编辑、删除、启停、重试策略、动作和 AI角色/Skill 装配；新增/编辑配置可先执行 dry-run 预览数据连接、AI 契约校验和写入策略；删除作业定义时必须写审计。 |
| 定时作业运行 | GET/POST(cancel/template) | /api/system/scheduled-job-runs, /api/system/scheduled-job-runs/observability, /api/system/scheduled-job-runs/{run_id}/cancel, /api/system/scheduled-job-runs/{run_id}/template | 查询定时作业运行实例、AI 配置快照、collector run 关联、结果摘要和失败原因；运行可观测性接口聚合成功率、失败率、平均耗时、AI/Token/插件调用、动作写入成功率、失败原因、最近失败和慢运行，供运行记录页签顶部概览展示；前端运行记录必须提供详情、复跑和“问 AI”入口，详情展示作业类型、AI执行、AI 模型、AI角色、Skills、运行链路、结果摘要、插件调用、Skill/Prompt 快照、作业配置快照、Trace DAG 和错误信息，复跑使用记录中的 `scheduled_job_id` 调用作业运行接口并传入 `trigger_type=manual_rerun` 与 `source_run_id=<当前运行 ID>` 后打开新运行详情；失败运行详情必须额外提供“生成修复草案”和“对比上次成功”快捷入口，跳转 AI 助手时携带 `reference_type=scheduled_job_run`、`reference_id=<当前运行 ID>` 和对应 prompt，让用户不需要手工复制运行 ID；若响应包含 `source_run_summary`，详情页必须展示“复跑对比”，对比来源运行与本次运行的状态、导入数和错误码；成功运行可生成新作业模板草稿，保留运行来源；手动触发或复跑期间必须显示执行中状态并禁用重复触发；运行中作业可由管理员取消。 |
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
- 导入 worker 必须通过 repository 原子 claim queued 任务并写入锁租约，成功、失败、取消和 retry 都要释放锁；重解析失败不得归档旧 active chunk set，历史 chunk set 激活时按版本保存的 `index_status` 恢复文档状态。
- 目录归档按子树生效，归档父目录下的子目录不得继续出现在目录树，也不得作为上传、创建子目录或批量移动目标。
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
- 定时作业配置列表属于管理型列表，`GET /api/system/scheduled-jobs` 必须优先走 PostgreSQL read model 完成名称/关键字、产品、来源系统、作业类型、启停和状态筛选，以及 `next_run_at/created_at/updated_at/name/job_type/status/enabled/last_*` 服务端排序与分页；未带分页参数的全量返回仅作为旧客户端和测试 helper 兼容，不能作为新增页面默认读路径。
- `job_type` 首批支持 `gitlab_daily_code_metric_collect`、`jenkins_release_collect`、`online_log_metric_collect`、`user_usage_metric_collect`、`user_feedback_collect`、`user_feedback_insight_extract`、`code_repository_inspection`、`online_log_ai_analysis`、`iteration_plan_suggestion_generate`、`dashboard_snapshot_refresh`、`lifecycle_context_refresh`、`plugin_action_invoke` 和 `pending_attribution_retry`。
- 作业类型、执行方式、调度方式、连接环境、代码巡检扫描方式、扫描引擎、内置规则、忽略规则、结果动作、严重级别阈值和作业必填规则以 `ScheduledJobCatalog` 服务端注册中心为准，通过 `GET /api/system/scheduled-job-catalog` 输出给任务中心页面和 AI 助手草案；前端 `scheduledJobFormTransformHelpers` 中的静态常量只能作为接口不可用时的降级，不得作为新增作业类型或规则扩展的权威来源。
- `execution_mode` 分为 `deterministic`、`ai_assisted`、`ai_generated`：确定性作业可写真实指标；AI 辅助作业可写摘要、风险信号或看板派生结果；AI 生成作业只能写候选建议或待确认结果。前端和服务端都必须按执行模式识别 AI 装配要求，任一作业选择 `ai_assisted` 或 `ai_generated` 时均需 active AI 模型、AI角色和 Skill。
- `iteration_plan_suggestion_generate`、`online_log_ai_analysis` 和 `user_feedback_insight_extract` 属于 AI 必选链路作业，服务端创建/修改时必须把有效执行模式归一为 `ai_generated`，并要求 active AI角色（Agent）、active Skill（可来自 AI角色默认 Skill）和 active 模型网关（可来自 AI角色默认模型网关或作业覆盖项）。
- 调度 worker 每分钟或按配置 tick，查询 `enabled=true AND next_run_at <= now()` 的作业，并通过数据库行级更新设置 `lease_owner` / `lease_expires_at` 抢占执行权；锁过期后其他 worker 可接管，已创建的运行实例不得被覆盖。
- 每次运行必须冻结 `config_snapshot`；AI 作业还必须冻结 AI角色（Agent）、Skill、模型网关、Prompt 模板、输出 Schema、工具策略和上下文范围快照，避免配置修改影响历史可追溯性。
- `user_feedback_insight_extract` 必须绑定数据连接、AI 模型、AI角色、Skills 和写入策略。页面允许配置多个数据连接和多个写入策略，配置顺序由 `plugin_connection_ids` / `plugin_action_ids` 表达；服务端保存默认编排策略到 `config_json.orchestration`，数据连接默认 `mode=sequential/failure_policy=fail_fast/merge_strategy=append_json_arrays`，结果写入默认 `mode=sequential/failure_policy=continue_on_error`。运行顺序固定为：先按连接顺序调用同一取数动作并合并 JSON 数组/rows/items 响应，任何连接失败且策略为 `fail_fast` 时终止；若配置 `knowledge_document_ids`，再按当前用户权限获取可检索知识 chunk 并注入 Skill 输入；随后通过平台模型网关按 AI角色系统提示、Skill Prompt 和知识引用将源数据处理为结果动作需要的结构化 JSON；最后按写入策略顺序根据动作 `result_mapping.write_target` 执行业务写入，单个写入失败按策略记录并继续或终止。当写入目标为 `user_feedback_insights` 时通过用户反馈 service 写入用户洞察表，`records_imported` 记录实际写入洞察数，源表行数只进入 `result_summary.source_row_count`。作业未配置 `plugin_output_mapping` 时复用动作 `result_mapping`。运行摘要必须通过 `result_summary.execution_nodes.data_connection.connection_count/successful_count/failed_count/items` 和 `result_summary.execution_nodes.skill_processing.model_gateway_called=true`、`model_log_id`、`processing_mode=model_gateway_json_transform`、`input.knowledge_references` 和处理输入/输出如实记录链路节点。
- Skill 必须声明输入/输出 Schema；定时作业运行和 dry-run 在调用模型前先合并所选 Skill 的输出 Schema，并校验写入策略 `result_mapping` 引用的 JSONPath 是否能由 Schema 支撑。模型返回 JSON 后还必须校验必填输出字段，缺失时运行失败或进入待人工确认，不得把不符合契约的内容直接写入业务表。
- 定时作业新增和编辑表单必须提供连接环境筛选，环境枚举与插件连接保持一致：`default/dev/test/staging/prod/sandbox`。筛选只影响数据连接下拉展示和模板回填，不作为 `scheduled_jobs` 字段提交；切换环境时若当前已选连接中存在不属于该环境的项，前端应从多选值中移除不匹配连接并同步第一项兼容字段。
- 前端运行详情必须先渲染三段执行链路卡片：`data_connection` 展示数据连接获取状态，`skill_processing` 展示模型是否调用、处理模式和模型日志，`result_action` 展示写入目标和写入反馈；当作业通过 AI 执行器执行时，还必须在数据连接后条件展示 `runner_execution` 节点，系统默认执行器展示 executor type、执行器实例、模型日志和结果摘要，本地 Codex/Claude/Hermes/OpenClaw Runner 继续展示任务 ID、工作区、状态、完成时间、日志条数和结果 JSON。原始 `execution_nodes`、插件快照、Skill 快照、Prompt 快照和作业配置快照继续作为高级 JSON 展示。
- `code_repository_inspection` 必须绑定产品、产品 Git 仓库和扫描分支；插件扫描模式还必须绑定数据连接和插件扫描动作。作业 `config_json.repository_id` 指向同产品单个 `product_git_repositories.id`，`config_json.repository_ids` 可指向同产品多个仓库并在一次运行中逐仓生成独立报告；`config_json.branch` 保存本次扫描分支，前端新增/编辑时应展示“代码仓库”“批量代码仓库”和“扫描分支”，仓库默认带出 `default_branch`，后端创建、修改和试运行也必须在分支缺失时用仓库 `default_branch` 兜底。插件响应推荐包含 `repository_id`、`branch`、`commit_sha`、`risk_level`、`summary` 和 `findings[]`；运行时插件输入顶层携带 `repository_id/branch`，自定义动作可直接通过 `{{repository_id}}` / `{{branch}}` 使用，若扫描器未返回 branch，报告写入以作业分支或仓库默认分支兜底。确定性执行直接使用插件扫描结构化输出或内置本地扫描结构化输出；当执行模式为 `ai_assisted` 或 `ai_generated` 时，服务端必须按 active AI角色、Skill 和模型网关调用平台模型，把扫描结果转换为巡检报告可消费的 `repository_id/branch/commit_sha/risk_level/summary/findings` JSON，模型上下文必须提供 `configured_repository_id/configured_branch`，模型输出再进入结果写入；若源数据来自 `native_full_scan`，AI 输出只能覆盖风险、摘要和 finding 等业务结果，`scan_mode/scanner_name/scanner_version/rules_version/files_scanned/lines_scanned/artifact_ref/remote_url_summary/remote_url_hash/quality_gate/scan_started_at/scan_finished_at` 等扫描快照字段必须从 native 结果继承。每个 finding 应包含 `committer_name`、`committer_email` 或 `committer_username`，服务端写入报告 `committer_summary` 并支持按提交人筛选。扫描器可在动作执行或作业配置中声明 `severity_mapping`，把 Sonar/SAST/GitHub 等外部等级归一为 `info/low/medium/high/critical`。本地扫描 finding 必须生成稳定 fingerprint，作业可通过 `config_json.baseline_fingerprints`、`accepted_risk_fingerprints`、`ignored_finding_fingerprints` 和严重级别阈值过滤历史问题、已接受风险、单条忽略项和低级别问题，过滤数写入 `suppression_summary`；报告详情允许对单条 finding 提交误报或忽略申请，状态按 `none -> pending -> approved/rejected` 流转，只有审批通过才回写报告 `suppressed_finding_count` 和对应 `suppression_summary` 原因计数；`config_json.quality_gate` 可声明 critical/high/medium/total 上限，运行和报告记录 `quality_gate.status/violations/counts`。作业通过 `result_actions` 支持多个结果写入动作，默认顺序为 `write_code_inspection_report`、`create_bug_for_severe_findings`、`create_task_for_severe_findings` 和 `send_notification`；写报告必须落到 `code_inspection_reports/code_inspection_findings`，严重 finding 按阈值创建 `source=code_inspection` Bug，同一仓库、分支、规则、文件、行号和提交人的开放 Bug 通过 fingerprint 去重；达到整改阈值的问题也可创建 `task_type=code_inspection_remediation` AI 任务，任务 input 保留报告、finding、仓库、文件、行号、规则、严重级别和修复建议，并回填 `code_inspection_reports.created_task_ids` 与 `code_inspection_findings.created_task_id`；通知动作写入 `code_inspection_notifications` 并记录邮件、钉钉机器人等目标和反馈摘要。运行摘要必须包含 `execution_nodes.data_connection`、`skill_processing`、`result_action`、`code_inspection_report`、`bug_creation`、`task_creation`、`notifications` 和 `result_actions`；多仓库运行还必须返回 `report_ids`、`report_count` 和 `reports_by_repository`。AI 执行时 `skill_processing.model_gateway_called=true` 并记录 `model_log_id`，确定性执行时该节点明确标记 `plugin_structured_output` 或 `native_full_scan`，用于运行详情展示扫描取数、AI/Skill 处理、报告写入、Bug 派生、整改任务派生、通知反馈和每个结果写入状态。运营治理 / 代码巡检概览接口按列表同源筛选和权限范围聚合 `summary/trend/rule_distribution/repository_ranking/branch_ranking/committer_ranking/sla/rule_governance`，其中 SLA 同时以严重 finding 是否已关联 Bug、是否已派生整改任务衡量闭环覆盖率，返回 Bug 覆盖率、整改任务覆盖率、未覆盖/未派生数量和最早未处理时间，规则治理返回版本分布和 suppression 分布，页面在报告列表上方展示；报告详情接口额外返回 `scan_summary.coverage/rule_distribution/file_distribution/committer_distribution/quality_gate/previous_comparison/scan_profile/suppression_summary` 供页面直接展示，并在 finding 列表展示忽略审批状态与治理操作。
- 运行状态为 `queued / running / succeeded / failed / skipped / cancelled`；失败可按 `max_retry_count` 生成新的运行实例，不能把失败实例改写成成功历史。
- `scheduled_job_runs.collector_run_id` 关联 `collector_runs`，用于继续兼容现有采集台账、审计和运行排查；AI 纯分析类作业也应写 collector run 或等价审计摘要，以便统一追踪。

**组件边界**:
| 组件 | 职责 |
|------|------|
| `ScheduledJobScheduler` | 计算 due jobs、抢占锁、创建运行实例、计算 `next_run_at`。 |
| `ScheduledJobRunner` | 装配运行上下文、创建/更新 collector run、调用 handler、处理重试和超时。 |
| `ScheduledJobHandler` | 每类 job 的业务执行器，复用现有 DevOps、用户洞察、迭代规划、看板和生命周期 service。 |
| `ScheduledJobTemplateCatalog` | 提供官方定时作业模板目录，声明模板版本、默认 payload、推荐场景和资源选择规则；任务中心页面与 AI 助手草案共用该目录生成周反馈洞察、代码巡检和邮件摘要作业配置。 |
| `ScheduledJobCatalog` | 提供作业配置注册中心，声明作业类型、必填资源规则、执行/调度枚举、连接环境和代码巡检扫描/规则/结果动作选项；定时作业 service 复用该 catalog 做后端校验，前端仅消费 catalog 渲染选项和校验提示。 |
| `ScheduledJobExecutionEngine` | 构造执行期节点追踪和摘要，包括数据连接、Skill/AI 处理、结果动作、代码巡检报告写入、插件写入预览和是否需要 AI 处理判断；作业运行事务、审计和持久化仍由定时作业服务编排。 |
| `AiExecutorRunnerService` | 管理系统默认执行器与隔离 Runner：系统默认执行器 `ai_executor_runner_system_default` 使用 `model_gateway` 执行类型，直接调用平台默认 AI 大模型并返回结构化执行结果，不参与 Runner Token、心跳或任务认领；本地 Runner 负责注册、心跳、Token 校验和轮换、任务队列、OpenClaw/Codex/Claude/Hermes 执行类型校验、任务认领、日志追加、管理员取消、超时熔断和完成回写；管理员侧测试接口只读取 Runner 配置与健康投影，返回诊断项并写轻量审计，不下发真实任务；完成回写不得执行外部命令，只更新任务状态、插件日志、定时作业运行、collector run 和作业最近运行字段。 |
| `ScheduledJobObservabilityService` | 聚合运行健康概览、失败原因、慢运行和 AI/插件/动作写入指标；只读取运行实例、作业定义和模型日志元数据，不参与作业执行。 |
| `ConnectionDiagnosticsService` | 构造插件连接测试诊断步骤、请求回放 cURL、动作模板草案、失败修复建议、最近测试历史和轻量测试摘要；真实网络请求、审计和连接记录持久化仍由插件服务编排。 |
| `AssistantDraftBuilder` | 构造 AI 助手确认式配置草案，包括研发任务、AI Skill、AI角色、插件连接、动作、每周反馈洞察作业、代码巡检作业、邮件摘要收取作业和分析类草案；研发任务草案使用 `create_rd_task`，优先从显式 `@需求` 解析 `requirement_id`，只生成 `product_detail_design` 任务草案，并同样返回“数据来源、AI处理、结果动作、调度策略、确认执行”五步 `wizard_steps[]`，其中调度策略为 `skipped`，用于说明研发任务是一次性确认动作；复用插件连接默认模板、动作模板目录和定时作业模板目录，代码巡检 AI 模式在缺少可用代码巡检 Skill 或 AI角色时必须先生成 `create_ai_skill` / `create_ai_agent` 前置草案，再生成依赖前置草案的 `create_scheduled_job`；所有助手生成的 `create_scheduled_job` 草案必须返回 `wizard_steps[]`，按数据来源、AI处理、结果动作、调度策略、确认执行给出 `ready/needs_prerequisite/pending/skipped/blocked` 状态、摘要和依赖，确定性插件任务的 AI处理步骤展示为 `skipped`，前端对 `needs_prerequisite/blocked` 步骤提供生成前置草案提示回填入口；配置向导每个步骤还必须提供“AI生成<步骤>草案”和“手动调整<步骤>”入口，ready/pending/skipped 步骤也可一键回填 AI 调整提示，数据来源和结果动作手动跳转任务中心 / 插件管理，AI处理跳转 AI 能力配置，调度策略和确认执行跳转任务中心 / 定时作业，让用户可在 AI 生成草案与人工调整之间切换；邮件摘要意图必须使用 `scheduled_job_templates.email_digest` 默认 payload，并绑定可用 `receive_email_messages` 动作和同插件邮箱连接生成 `create_scheduled_job` 草案；发布风险分析和知识库巡检生成 `create_analysis_draft`，草案同样返回“数据来源、AI处理、结果动作、调度策略、确认执行”五步 `wizard_steps[]`，其中调度策略为 `skipped`，确认后只生成可追踪 `assistant_analysis` 结果，不写业务配置表；`assistant_tools` 保留意图识别、读模型工具、插件连接失败诊断和结果汇总；泛化“新增任务”或未指定场景的“新增 AI能力配置”由 AI 助手确定性返回任务类型向导，引导用户选择草案路径后再生成具体配置，建议按钮与向导卡片均覆盖研发任务、定时作业、AI能力配置、插件动作、代码巡检和反馈洞察，且每个任务项都使用统一五步闭环；插件连接失败诊断必须只读取 `last_test_summary/test_history.repair_suggestions` 等脱敏摘要，不注入认证配置、完整 Header、完整请求体或密钥。 |
| `AIExecutionConfigResolver` | 解析 AI角色（Agent）、Skill、模型网关和作业覆盖项，生成不可变运行快照。 |
| `SkillOrchestrator` | 合并 agent system prompt、skill prompt、工具结果和 expected output schema，调用模型网关前做脱敏和限长，输出后做 schema 校验。 |

**安全与副作用**:
- AI角色/Skill 不得保存密钥；外部系统访问通过产品 Git 资源、相关系统或服务端凭据引用完成，默认只读。
- AI 作业不得自动创建正式需求、关闭 Bug、变更发布状态、远端写回 GitLab/GitHub/Jenkins 或修改产品路线图。
- 低置信度或无法归属的数据进入 `pending_attribution_items`，不进入产品级看板结论。
- 所有配置变更、手动触发、运行开始、运行成功、运行失败、取消和重试必须写入 `audit_events`。

### 模块 B3.R: rd_task_executor_policies

**职责**: 维护需求交付下研发任务到工程执行器的匹配策略。执行器资源仍在插件管理 / AI 执行器中维护，研发执行器策略只定义“哪类研发任务在什么产品、仓库和工作区下使用哪个 Runner 和指令模板”。

**核心规则**:
- 研发执行器策略只允许选择 Codex、Claude Code、OpenClaw 三类工程执行器和插件管理下 active Runner；不装配 AI角色（Agent）、Skill 或模型网关。Agent/Skill 仍只服务定时作业、用户洞察、日志分析、反馈提炼、知识巡检等平台内 AI 处理。
- 页面任务类型下拉必须覆盖研发流程常用阶段：PRD / 原型 / 产品详细设计（`product_detail_design`）、技术方案设计（`technical_solution`）、代码实现 / 开发计划（`development_planning`）、代码评审（`code_review`）、自动化测试（`automated_testing`）、代码整改（`code_inspection_remediation`）、发布上线评估（`release_readiness`）和上线后分析（`post_release_analysis`）。其中 PRD 与原型当前随产品详细设计任务产出，代码实现当前沿用开发计划任务的执行策略匹配值。
- 策略匹配优先级为：同任务类型下产品专属策略优先于全局策略，随后按 `priority` 升序匹配；未命中策略的研发任务继续沿用现有模型网关 / code_review executor 路径。
- 策略可选绑定 `product_id`、`repository_id`、`branch`，必须配置 `workspace_root`、`instruction_template`、`output_contract`、`timeout_seconds` 和 `status`。`workspace_root` 必须落在 Runner 的 `workspace_roots` 白名单内。
- 研发任务启动时先解析 active 策略；命中后创建 `ai_executor_tasks(ai_task_id=当前任务)`，任务状态进入 `running`，`current_step=waiting_ai_executor`，并在 `input_json.executor` 冻结策略 ID、执行器类型、Runner、Runner 任务 ID 和工作区。
- Runner 认领、追加日志、完成、取消或超时回写时，服务端同步 `ai_tasks`：运行中保持 `running/waiting_ai_executor`；成功时写入 `output_json.executor/result`、生成 `human_reviews(pending)` 并进入 `waiting_review`；失败、取消或超时写入错误码和错误信息，任务进入 `failed/cancelled`。
- 执行器输入只包含研发任务摘要、需求快照、产品上下文、仓库/分支和输出契约，不下发产品 Git 凭据、插件连接密钥、模型网关密钥或 Agent/Skill 配置。Runner 可在受控工作区中使用本机 Codex/Claude Code/OpenClaw 完成工程分析或生成补丁草案，但业务终态仍必须经过 AI Brain 人工确认。
- 页面入口位于需求交付 / 研发执行器策略；插件管理 / AI 执行器继续维护 Runner 本体、Token、心跳、安装包、日志和健康检测。

### 模块 B3.C: code_inspection

**职责**: 承载运营治理下的代码仓库巡检报告，面向仓库质量、安全和规范问题提供报告列表、finding 明细、通知反馈和严重问题 Bug 派生。

**核心规则**:
- `code_repository_inspection` 支持两类取数模式：`config_json.scan_mode=native_full_scan` 为平台内置本地完整扫描，服务端根据产品 Git 仓库 `remote_url` 在 `CODE_SCAN_WORKDIR` 下维护 `mirrors/` 裸仓库缓存，并按 repository + branch + commit 在 `checkouts/` 创建单次运行工作副本；HTTP(S) 私有仓库必须优先使用同仓库 `credential_ref` 解析出的只读 token，通过临时 `GIT_ASKPASS` 注入 `git clone/fetch`，未配置仓库凭据时再读取 provider 级环境变量（GitLab: `GITLAB_READONLY_TOKEN/GITLAB_TOKEN`，GitHub: `GITHUB_READONLY_TOKEN/GITHUB_TOKEN`，通用: `GIT_READONLY_TOKEN/GIT_TOKEN`），凭据不得写入 remote_url、运行摘要、报告或错误信息。默认点击运行先创建 `scheduled_job_run(status=queued)`，后台 worker 再执行 clone/fetch、checkout、scan 和报告写入，显式 `config_json.async_execution=false` 时可用于测试/调试同步执行。成功扫描默认只保留 mirror，不保留 checkout；失败 checkout 按 `CODE_SCAN_FAILED_CHECKOUT_RETENTION_DAYS` 短期保留，后台清理按保留天数和 `CODE_SCAN_MAX_CHECKOUT_BYTES` 控制磁盘。扫描器 checkout `config_json.branch` 或仓库 `default_branch`，按 `config_json.scan_rules` 执行内置规则，按 `config_json.ignore_dirs` 和 `config_json.ignore_rules` 忽略目录或规则，按 `config_json.severity_threshold`、`baseline_fingerprints`、`accepted_risk_fingerprints` 和 `ignored_finding_fingerprints` 过滤低级别、历史、已接受或单条忽略问题，按 `config_json.incremental_from_commit` 只扫描增量变更文件，并通过 `git blame --line-porcelain` 回填 finding 提交人；`config_json.scanner_engines` 可声明 `builtin/gitleaks/semgrep/trivy/npm/pip-audit/dependency-check` 等引擎，已安装的外部引擎必须执行并解析标准 JSON 输出，归一为平台 finding，未安装、超时或输出不可解析时写入 `coverage_warning` 与 `scan_profile.external_scanner_status.skipped/failed` 后继续内置扫描。`config_json.quality_gate` 记录质量门禁上限和违规项；`config_json.repository_ids` 可让一个作业逐仓扫描多个同产品仓库并生成多份报告。该模式不要求 `plugin_connection_id/plugin_action_id`，运行摘要必须包含 `execution_nodes.native_scan`，节点记录 repository_id、branch、commit_sha、remote_url_hash、remote_url_summary、artifact_ref、checkout_path_retained、scan_started_at、scan_finished_at、scanner_version、rules_version、增量基线、增量文件数、suppression_summary、quality_gate 和 scan_profile；`execution_nodes.data_connection.processing_mode=native_full_scan`。异步运行被取消后，worker 必须在写报告前检查取消终态，不得覆盖为成功或继续创建报告。`sync_existing_alerts` 和 `trigger_platform_scan` 继续使用插件连接/动作对接 GitHub/GitLab/SonarQube/SAST 或自建扫描服务。内置扫描器当前规则集包括 `secrets.hardcoded_credential` 和 `metadata.internal_address_exposure`，输出仍归一为 `repository_id/branch/commit_sha/risk_level/summary/findings`，不得把原始密钥明文写入报告。
- 代码巡检报告来源于 `code_repository_inspection` 定时作业，不替代单个 MR/PR 的 `code_review` 人工确认报告；前者是周期性治理，后者是交付链路评审。
- 巡检结果必须保存到 `code_inspection_reports` 和 `code_inspection_findings`，不得只保存在 `scheduled_job_runs.result_summary` 或 `plugin_invocation_logs.response_summary`。
- `risk_level` 可由插件响应提供；缺失时按 findings 中最高 severity 推导。外部 severity 先按动作或作业 `severity_mapping` 归一，`severe_finding_count` 当前按 `high/critical` 统计，用于列表风险扫描。
- `create_bug_for_severe_findings` 只针对达到阈值的 finding 创建 Bug，Bug `source=code_inspection`，evidence 必须包含 report_id、finding_id、rule_id、file_path、line_number、branch、commit_sha、committer_* 和 finding_fingerprint；同一开放 fingerprint 不重复创建 Bug，而是把新 finding 关联到已有 Bug。
- `send_notification` 第一阶段只记录通知动作和反馈摘要，支持 `email`、`dingtalk` 和 `webhook` channel；真实外部发送能力可在通知服务落地后复用同一表结构，不得在巡检 service 中硬编码第三方 SDK。
- 列表和详情接口位于 `/api/governance/code-inspections`，需要 `code_inspection.read` 权限，并按当前用户产品 scope 过滤；前端入口归属运营治理 / 代码巡检，支持按提交人、风险级别、状态和摘要筛选。

### 模块 B3.A: ai_capabilities

**职责**: 维护 AI角色（Agent）、Skill 和默认装配策略，为定时 AI 作业、用户洞察、日志分析、知识巡检等平台内 AI 处理提供统一能力配置。

**核心规则**:
- Skill 表示能力包，包含输入/输出 schema、prompt_template、allowed_tools、required_context、risk_level、requires_human_review、版本和启停状态；第一阶段支持表单 Skill 和 zip 文件包 Skill 两种来源。
- Skill 文件包通过 `POST /api/system/ai-skills/upload` 上传，HTTP body 为 `application/zip`，query 中传 `code/name/version/status/risk_level/requires_human_review`；包内必须包含 `skill.yaml` 或 `SKILL.md`，服务端只允许 `.md/.txt/.yaml/.yml/.json` 文件，禁止路径穿越、绝对路径和超限文件。
- 上传后的 Skill 文件保存到服务端本地 Skill 存储目录，数据库 `ai_skills` 保存 `source_type`、`package_uri`、`package_checksum`、`package_entry`、`package_files`、`package_size_bytes` 和 `manifest`；运行时按 URI 读取本地文件并写入 `resolved_skill_snapshots.package_snapshot`，历史解释以运行快照为准。
- AI角色（Agent）表示执行角色，包含所属业务大脑、默认模型网关、system_prompt、默认 Skill、执行策略、工具策略和启停状态；第一阶段 AI角色只通过页面表单维护，不支持 Agent 文件包上传。
- 定时作业和后续业务大脑配置只引用已启用 AI角色/Skill；运行时必须解析成快照，不直接读取可变配置作为历史解释依据。需求交付下直接使用 Codex、Claude Code、OpenClaw 的研发执行器策略不引用 Agent/Skill。
- 高风险 Skill 必须 `requires_human_review=true` 或只写候选结果；正式业务状态变更必须走现有人审或决策流。
- 管理员可以维护 AI角色/Skill；产品负责人和研发负责人只能在业务允许范围内选择已启用配置，不能修改系统提示词、工具权限或模型网关密钥。

### 模块 B3.0: git_review

**职责**: 支撑 v1 MVP GitLab MR / GitHub PR 代码 Review 闭环，读取 MR/PR 元信息和 diff 摘要，生成不可变输入快照，并归档经人工确认的 Review 报告。

Git Review API 入口已收口到独立 `app.api.routers.git_review`：GitLab MR 预览/快照、GitHub PR 列表/预览/快照保持原权限、只读远端访问、handler 级审计写入、DB-first source rows 恢复和 diff 超限失败语义；底层 provider helper、diff 摘要和快照创建逻辑仍作为后续 service 深拆对象保留兼容边界。

**核心规则**:
- 只能读取产品已绑定且当前用户有权限的 GitLab 项目/MR 或 GitHub 仓库/PR。
- MR/PR 快照成功、复用和失败审计属于 DB-first 写路径：服务层不得直接写 `current_store.gitlab_mr_snapshots` 或追加 `current_store.audit_events`；MemoryStore fallback 由 `save_git_review_snapshot_record` 承接，PostgreSQL 运行态快照和审计必须在同一数据库事务中提交。
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
→ code_repository_inspection 定时作业通过插件扫描仓库质量/安全/规范 finding，写入 code_inspection 报告，严重问题派生 Bug，并记录通知反馈
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
- 业务域规格索引: [domains/README.md](./domains/README.md)
- 整体方案评审与业务流程: [03-guides/ai-development-workflow.md](../../03-guides/ai-development-workflow.md)

---
最后更新: 2026-06-23
