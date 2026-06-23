# 质量、运营与洞察

> 来源：../spec.md。本文承接代码巡检、执行诊断、Bug、用户洞察、生命周期上下文和团队看板的业务域规格导航。

## 职责边界

- 执行诊断统一追踪定时作业、插件调用、Runner、AI 助手运行、模型网关、代码巡检和审计事件。
- 代码巡检从“生成报告”升级为质量治理闭环，覆盖本地完整扫描、质量门禁、baseline、Bug/任务派生和趋势分析。
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

- 执行诊断列表和详情优先读取 `execution_trace_snapshots`，短 TTL 内可复用快照降低重复查询开销；详情未命中关联 ID 时必须强制刷新后再返回 404，节点元数据必须脱敏；列表支持 `source_id` 按任一节点来源 ID 精准定位，前端深链命中唯一链路时自动打开详情；详情需汇总失败/运行中节点，提供来源 ID 深链和“问 AI”入口。
- AI 助手聊天运行可作为执行诊断根节点，关联模型网关日志和审计事件；详情只展示排障元数据，不展示完整对话、Prompt 或知识正文。
- 代码巡检本地完整扫描需记录仓库、分支、提交、提交人、规则版本、扫描覆盖、质量门禁和 suppression 摘要。
- 代码巡检治理概览必须展示质量门禁趋势，按日期聚合通过、失败、跳过和未知门禁数，便于判断规则升级或仓库质量门禁是否持续恶化。
- 代码巡检严重问题 SLA 必须同时展示 Bug 覆盖率和整改任务覆盖率，未关联 Bug 或未派生整改任务的严重 finding 要暴露数量和最早时间。
- 严重代码巡检 finding 可派生 Bug 或整改任务，并通过 fingerprint 去重。
- 用户洞察列表固定列宽、服务端筛选和详情查看保持稳定，优质反馈可转需求。

## 验收映射

- 详细验收见 [../test-cases/devops-quality-and-insights.md](../test-cases/devops-quality-and-insights.md)。
