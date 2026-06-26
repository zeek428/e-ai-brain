# 质量、运营与洞察

> 来源：../spec.md。本文承接代码巡检、执行诊断、Bug、用户洞察、生命周期上下文和团队看板的业务域规格导航。

## 职责边界

- 执行诊断统一追踪定时作业、插件调用、Runner、AI 助手运行、模型网关、代码巡检和审计事件。
- 代码巡检从“生成报告”升级为质量治理闭环，覆盖本地完整扫描、质量门禁、baseline、误报忽略审批、Bug/任务派生和趋势分析。
- Bug 管理维护人工、自动化测试、代码巡检和发布后分析产生的问题生命周期。
- 用户洞察将用户反馈转需求，反馈状态随需求归属和处理动作同步。
- 团队看板可以在 Python 中做聚合，但来源必须是 PostgreSQL source rows 或可重建只读缓存。

## 关键数据

- `execution_trace_snapshots`
- `code_inspection_reports`、`code_inspection_findings`、`code_inspection_notifications`
- `bugs`、`user_feedback`、`user_usage_metrics`、`iteration_plan_suggestions`
- `lifecycle_context_edges`、`lifecycle_risk_signals`、`dashboard_metric_snapshots`

## 关键 API 与页面

- 执行诊断：`/governance/execution-traces`
- 代码巡检：`/governance/code-inspections`
- 用户洞察：`/governance/insights`
- Bug 管理：`/governance/bugs`
- 团队看板：首页工作台

## 当前落地要求

- 执行诊断列表和详情优先读取 `execution_trace_snapshots`，快照刷新必须在单个数据库事务中完成 upsert 与过期快照删除，短 TTL 内可复用快照降低重复查询开销；详情未命中关联 ID 时必须强制刷新后再返回 404，节点元数据必须脱敏；列表支持 `source_id` 按任一节点来源 ID 精准定位，前端深链命中唯一链路时自动打开详情；AI 助手草案、AI 助手运行状态最近失败、AI 助手运行诊断卡片、定时作业运行详情、代码巡检报告详情和插件管理 Runner 执行日志通过统一 `ExecutionTraceLink` 生成深链，代码巡检详情需提供巡检报告、来源运行和插件调用三个诊断入口，Runner 日志需提供任务诊断、Runner 诊断和来源运行诊断入口；Runner 节点支持按 `source_type=ai_executor_runner` 和 Runner ID 下钻，任务节点通过 `assigned_runner` 边关联 Runner，节点只展示心跳、协议、工作区、健康状态和 token 是否配置，不暴露 `token_hash`；模型网关日志需吸附通过 subject、payload 或 `ai_task_id` 指向它的审计事件，按审计 ID 下钻应回到同一条模型调用链路；详情需汇总失败/运行中节点，提供来源 ID 深链和“问 AI”入口。
- 模型网关配置页必须展示最近模型调用日志，只返回和展示日志 ID、用途、模型、状态、耗时、Token 摘要、关联任务、错误摘要和创建时间等脱敏元数据；每条日志必须按 `source_type=model_gateway_log` 和日志 ID 提供统一执行诊断入口，不展示完整 Prompt、输出正文或密钥。
- 首页团队看板允许 Python 聚合，但输入必须来自 PostgreSQL source rows 或可重建只读缓存；看板快照写入优先调用 `save_dashboard_metric_snapshot_record`，MemoryStore 仅作为测试 fallback，通过 helper 写入 `dashboard_metric_snapshots` 并保留稳定快照 ID 与首次创建时间。
- AI 助手聊天运行可作为执行诊断根节点，关联用户消息、助手消息、模型网关日志和审计事件；`source_id` 支持按 `assistant_message_id` 反查整条助手运行链路，详情只展示排障元数据，不展示完整对话、Prompt 或知识正文。
- 代码巡检报告列表必须优先走 PostgreSQL read model，在数据库层完成产品 scope、仓库、风险、状态、摘要、提交人、排序和分页；MemoryStore 仅作为测试和降级路径。
- 代码巡检报告、finding、通知、误报忽略审批和整改任务派生属于 DB-first 写路径：服务层不得直接写 `current_store.code_inspection_*` 或 `current_store.ai_tasks`；MemoryStore fallback 由 `persist_code_inspection_records` / `persist_ai_task_record` 承接，PostgreSQL 运行态的报告、finding、通知和审计必须在同一数据库事务中提交。
- 代码巡检本地完整扫描需记录仓库、分支、提交、提交人、规则版本、扫描覆盖、质量门禁和 suppression 摘要。
- 代码巡检报告详情中的 finding 可提交误报/忽略申请，审批状态按 `none/pending/approved/rejected` 流转；审批通过后同步报告 suppression 统计、规则治理概览和审计事件，不能只在前端隐藏问题。
- 代码巡检治理概览必须展示规则包与误报治理，包含最近报告规则/扫描器版本、版本不一致提示、规则/扫描器版本分布、suppression 总量和 baseline/已接受风险/忽略项/严重级别阈值等过滤原因分布。
- 代码巡检治理概览必须展示质量门禁趋势，按日期聚合通过、失败、跳过和未知门禁数，便于判断规则升级或仓库质量门禁是否持续恶化。
- 代码巡检严重问题 SLA 必须同时展示 Bug 覆盖率和整改任务覆盖率，未关联 Bug 或未派生整改任务的严重 finding 要暴露数量和最早时间。
- 严重代码巡检 finding 可派生 Bug 或整改任务，并通过 fingerprint 去重。
- Bug 创建、批量更新、编辑和删除属于 DB-first 写路径：服务层不得直接调用 `current_store.audit()` 或写 `current_store.bugs`；MemoryStore fallback 由 `save_bug_record` / `delete_bug_record` 承接，PostgreSQL 运行态的 Bug 单记录写入、删除和审计必须在同一数据库事务中提交。
- 用户洞察列表固定列宽、服务端筛选和详情查看保持稳定，优质反馈可转需求。
- 用户使用指标创建属于 DB-first 写路径：服务层不得直接写 `current_store.user_usage_metrics`；MemoryStore 测试 fallback 由 `save_user_usage_metric_record` 写入指标，PostgreSQL 运行态通过同名 repository 单记录写入指标和审计事件。
- 用户洞察域通用审计 helper 在轻量上下文 fallback 中必须通过审计事件列表 helper 写入，不得直接 append `current_store.audit_events`；repository 运行态的审计事件由用户反馈、使用指标或迭代规划写入 helper 显式携带提交。
- 用户反馈创建、更新和转需求必须通过用户洞察写入 helper 承接；反馈单记录由 `save_user_feedback_record` 写入，转需求由 `save_user_feedback_requirement_conversion` 同步提交需求、反馈 linked 状态和审计事件。PostgreSQL 运行态更新/转需求必须按反馈 ID 从 repository 读取源记录，不得依赖运行时 `MemoryStore.user_feedback` 全量集合；MemoryStore 仅作为测试 fallback。
- 迭代规划建议生成、建议决策和建议转需求属于 DB-first 写路径：服务层不得直接写 `current_store.requirements`、`current_store.iteration_plan_suggestions` 或 `current_store.iteration_plan_decisions`，也不得通过 `audit_events` 切片拼装本次审计；MemoryStore fallback 由 `persist_iteration_suggestion_record` / `persist_iteration_decision_records` 承接，PostgreSQL 运行态建议、决策、转需求和审计必须在同一数据库事务中提交。

## 验收映射

- 详细验收见 [../test-cases/devops-quality-and-insights.md](../test-cases/devops-quality-and-insights.md)。
