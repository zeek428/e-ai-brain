# 生命周期、看板与执行诊断 API

> API 分册。覆盖软件研发全流程感知、首页 IT 团队看板和执行诊断。主入口见 [../api.md](../api.md)，分册组索引见 [quality-operations-and-insights.md](quality-operations-and-insights.md)。

### 软件研发全流程感知

```http
GET /api/lifecycle/context?subject_type=requirement&subject_id=requirement_001&direction=both&include_risks=true
```

查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| subject_type | string | 起点主体类型。当前支持 `product`、`requirement`、`ai_task`、`human_review`、`code_review_report`、`gitlab_mr_snapshot`、`mock_issue`、`knowledge_deposit`、`audit_event`、`bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；未支持类型必须返回 `VALIDATION_ERROR`。 |
| subject_id | string | 起点主体 ID。 |
| product_id | string | 可选，按产品过滤。 |
| version_id | string | 可选，按版本过滤。 |
| module_code | string | 可选，按模块过滤。 |
| direction | string | `upstream | downstream | both`，默认 `both`。 |
| include_risks | boolean | 是否返回风险信号，默认 true。 |

权限规则：当起点是 `ai_task` 时，读取权限与 AI 任务详情一致；当起点是需求、产品或可解析到任务的审计/证据主体时，返回的下游任务、人工确认、报告、知识沉淀、模拟 Issue、真实运营证据和风险信号必须先过滤掉当前用户无权读取的任务链路。

持久化规则：PostgreSQL 运行时聚合前直接读取 repository source rows；接口会把当前查询范围内计算出的上下游关系边同步到 `lifecycle_context_edges`，把风险信号同步到 `lifecycle_risk_signals`；无关系或无风险时保持真实空集合，不生成兜底记录。

统一需求全链路入口：

```http
GET /api/lifecycle/full-chain?subject_type=bug&subject_id=bug_001
```

查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| subject_type | string | 链路入口主体类型。当前支持 `requirement`、`bug`、`product_version`/`iteration_version`、`product_version_branch_config`/`branch_config`、`code_inspection_report`、`knowledge_deposit`、`audit_event`，以及执行诊断主体 `scheduled_job_run`、`plugin_invocation_log`、`ai_executor_task`、`model_gateway_log`、`execution_trace` 等可通过 Trace `related_ids`、节点 `metadata.ai_task_id`、代码巡检报告或审计事件解析到任务/需求的主体；未支持类型返回 `VALIDATION_ERROR` 或明确的未找到错误。 |
| subject_id | string | 链路入口主体 ID。 |

响应规则：接口先校验当前用户具备 `requirement.read`、`task.read` 或 `workspace.read` 任一读权限，并按入口主体可解析出的 `product_id` 校验产品 scope；缺少读权限返回 403，产品 scope 不匹配返回 404。校验通过后解析入口主体到需求 ID，再复用 `/api/requirements/{requirement_id}/full-chain` 的同一响应结构，并额外返回 `anchor={subject_type,subject_id,resolved_requirement_id}`；前端必须展示入口主体和已解析需求 ID，避免用户从 Bug、迭代版本、版本代码分支配置、代码巡检、AI 助手或执行诊断入口进入后丢失上下文。当入口为 `product_version_branch_config` 或 `branch_config` 时，服务端按分支配置所属版本解析同版本最新需求链路，分支不存在返回 404，同版本无需求返回 `NO_REQUIREMENT_CONTEXT`。当代码巡检报告的 `created_task_ids` 或 `created_bug_ids` 命中当前需求链路内任务/Bug 时，响应 `code_inspection_reports[]` 和 `summary.code_inspection_reports` 必须包含对应报告，时间线增加 `type=code_inspection_report` 事件；需求归属迭代版本且版本存在分支配置时，若代码巡检报告的 `repository_id` 与 `branch` 命中该版本分支配置的代码库和工作分支，也必须纳入同一需求链路。需求归属迭代版本时，响应还必须返回该版本的 `branch_configs[]`、`summary.branch_configs` 和 `type=branch_config` 时间线事件；和需求、迭代版本、AI 任务、Review、PR/MR 快照、代码评审、代码巡检、Bug、发布或知识沉淀直接相关的审计事件以脱敏 `audit_events[]`、`summary.audit_events` 和 `type=audit_event` 时间线事件返回，不暴露审计 payload。与链路主体、审计事件或链路内 AI 任务相关的执行诊断以 `execution_traces[]`、`summary.execution_traces` 和 `type=execution_trace` 时间线事件返回，只暴露 Trace ID、根来源、状态、标题/摘要、节点计数、失败节点数、运行中节点数、耗时和时间字段，不返回完整节点 metadata 或敏感调用参数；前端阶段明细必须按 `source_id=<trace.root_id || trace.id>&source_type=<trace.root_type>` 跳转执行诊断中心。前端统一使用 `/delivery/full-chain?subject_type=<type>&subject_id=<id>` 深链承载 Bug、迭代版本、版本代码分支配置、代码巡检和执行诊断入口。

响应摘要：

```json
{
  "data": {
    "subject": {
      "type": "requirement",
      "id": "requirement_001"
    },
    "upstream": [],
    "downstream": [
      {
        "subject_type": "ai_task",
        "subject_id": "task_001",
        "relation_type": "generates",
        "summary": "产品详细设计任务",
        "confidence": 1.0
      }
    ],
    "risk_signals": [
      {
        "risk_type": "critical_bug_open",
        "severity": "critical",
        "source_subject_type": "bug",
        "source_subject_id": "bug_001",
        "impact_summary": "阻塞当前版本发布",
        "recommendation": "先完成修复和验证再进入发布评估"
      }
    ],
    "missing_context": [
      "automated_testing",
      "gitlab_daily_code_metric",
      "jenkins_release",
      "online_log_metric",
      "user_usage_metric",
      "user_feedback",
      "iteration_plan_suggestion"
    ],
    "summary": {
      "downstream_count": 1,
      "missing_context_count": 7,
      "risk_count": 1,
      "upstream_count": 0
    }
  },
  "trace_id": "trace_015"
}
```

### 首页 IT 团队看板

```http
GET /api/dashboard/it-team?product_id=product_001&time_range=7d
```

当前实现返回真实聚合指标，来源于产品、需求、AI 任务、待确认 Review、知识文档、知识沉淀、审计事件、Bug、GitLab 每日指标、Jenkins 发布、线上日志、用户使用、用户反馈和迭代规划建议；PostgreSQL 运行时聚合前直接读取 repository source rows，不再通过 repository read snapshot 承载看板聚合；首页看板属于汇总型视图，允许在 Python 中完成跨主体聚合和展示计算，不强制改为 SQL/物化 read model，但读取来源必须来自 PostgreSQL 派生数据且不得作为写入事实源；其中 AI 任务、待确认 Review 和知识沉淀计数、列表必须先按任务读权限过滤，`product_id` 存在时所有可归属主体必须按产品归属过滤，`time_range` 存在时运营类指标按可解析的日期或时间窗口过滤，并把当前产品/时间窗口聚合结果通过单条 repository 写入同步到 `dashboard_metric_snapshots`。

PostgreSQL 运行时默认启用短 TTL 看板缓存，TTL 由 `DASHBOARD_CACHE_TTL_SECONDS` 控制，默认 30 秒；`DASHBOARD_CACHE_TTL_SECONDS<=0` 时禁用缓存。`GET /api/dashboard/it-team?...&refresh=true` 会清除当前用户角色、产品和时间窗口对应的缓存并重新读取 source rows、重建 snapshot。响应 `data.metadata.dashboard_cache` 必须返回缓存是否启用、是否命中、生成时间、缓存年龄、剩余 TTL、本次接口耗时、慢查询阈值和慢查询标记；接口耗时超过 `DASHBOARD_SLOW_THRESHOLD_MS` 时记录 `slow_dashboard_query` 日志。无数据时返回真实 0 和空数组，不生成占位统计：

```json
{
  "data": {
    "summary": {
      "active_products": 1,
      "requirements": 2,
      "ai_tasks": 1,
      "pending_reviews": 1,
      "knowledge_documents": 1,
      "knowledge_deposits": 0,
      "audit_events": 10,
      "bugs": 1,
      "open_bugs": 1,
      "high_severity_bugs": 1,
      "gitlab_commits": 7,
      "jenkins_releases": 1,
      "online_errors": 12,
      "usage_events": 120,
      "user_feedback": 1,
      "iteration_suggestions": 1
    },
    "bug_status_counts": [
      {"status": "open", "count": 1}
    ],
    "latest_high_severity_bugs": [],
    "gitlab_daily_summary": {
      "metric_count": 1,
      "commit_count": 7,
      "merge_request_count": 2,
      "changed_files": 8,
      "risk_count": 1,
      "average_quality_score": 88.5
    },
    "jenkins_release_status_counts": [
      {"status": "failed", "count": 1}
    ],
    "online_log_summary": {
      "metric_count": 1,
      "request_count": 2400,
      "error_count": 12,
      "error_rate": 0.005,
      "max_p95_latency_ms": 318.5,
      "max_p99_latency_ms": 640.25
    },
    "usage_metric_summary": {
      "metric_count": 1,
      "active_users": 42,
      "event_count": 120,
      "conversion_count": 15,
      "error_count": 2
    },
    "user_feedback_status_counts": [
      {"status": "open", "count": 1}
    ],
    "iteration_suggestion_status_counts": [
      {"status": "suggested", "count": 1}
    ],
    "requirement_status_counts": [
      {"status": "submitted", "count": 1},
      {"status": "designing", "count": 1}
    ],
    "task_status_counts": [
      {"status": "waiting_review", "count": 1}
    ],
    "latest_tasks": [],
    "pending_reviews": [],
    "recent_knowledge_documents": [],
    "recent_audit_events": [],
    "metadata": {
      "dashboard_cache": {
        "age_ms": 0,
        "cache_enabled": true,
        "cache_hit": false,
        "duration_ms": 42,
        "expires_in_ms": 30000,
        "generated_at": "2026-06-05T10:00:00+00:00",
        "slow": false,
        "slow_threshold_ms": 500,
        "ttl_seconds": 30
      }
    },
    "time_range": "7d"
  },
  "trace_id": "trace_014"
}
```

### 执行诊断

```http
GET /api/governance/execution-traces?keyword=scheduled_job_run_001&source_type=scheduled_job_run&status=failed&page=1&page_size=10&sort_by=started_at&sort_order=desc
GET /api/governance/execution-traces?refresh=true&page=1&page_size=10
GET /api/governance/execution-traces?source_id=model_gateway_log_001&source_type=model_gateway_log
GET /api/governance/execution-traces/{trace_id}
```

权限：需要 `diagnostics.execution_traces.read`。当前默认授予 `admin`，用于跨定时作业、插件、AI 执行器、AI 助手运行、模型和审计的管理员级排障。

链路聚合规则：模型网关日志可作为独立根节点，也可作为定时作业、插件调用、Runner 或 AI 助手运行的子节点；审计事件若通过 `subject_id`、payload 中的 `model_gateway_log_id` / `model_log_id`，或相同 `ai_task_id` 指向模型调用，会吸附到同一条模型调用 Trace。按对应审计事件 ID 作为 `source_id` 或详情 `{trace_id}` 查询时，应返回该模型调用链路，避免同一模型失败同时显示为孤立审计 Trace 和孤立模型 Trace。

Runner 聚合规则：`ai_executor_task.runner_id` 必须解析为 `ai_executor_runner` 节点并与任务节点通过 `assigned_runner` 边相连；若 Runner 记录不存在，仍需生成带 `missing_runner_record` 元数据的占位节点保留 Runner ID，便于排查任务为什么没有被正确接单。Runner 节点只返回名称、协议、执行器类型、工作区、心跳时间、超时时间、并发、健康状态和 token 是否配置，不返回 `token_hash` 或安装包密钥。

列表查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| keyword | string | 按链路 ID、根 ID、根类型、标题、摘要或关联 ID 搜索。 |
| source_id | string | 按任一链路节点来源 ID 精准定位，例如 `scheduled_job_run`、`scheduled_job_stage`、`plugin_invocation_log`、`ai_executor_runner`、`ai_executor_task`、`assistant_chat_run`、`model_gateway_log`、`code_inspection_report`、`result_write_record` 或 `audit_event` 的 ID；前端深链必须同时携带 `source_type`，命中唯一记录时自动打开详情。 |
| source_type | enum | 来源类型，可是根类型或任一节点类型；前端筛选文案统一展示为“来源类型”：`scheduled_job_run`、`scheduled_job_stage`、`plugin_invocation_log`、`ai_executor_runner`、`ai_executor_task`、`assistant_chat_run`、`assistant_message`、`model_gateway_log`、`code_inspection_report`、`result_write_record`、`audit_event`。 |
| status | enum | 聚合状态：`succeeded`、`failed`、`running`、`queued`、`partial`、`skipped`、`cancelled`、`unknown`。 |
| created_from / created_to | ISO datetime | 按链路开始时间或更新时间过滤，未带时区时按 UTC 处理。 |
| refresh | boolean | 可选。`true` 时先同步重建 `execution_trace_snapshots` 再分页返回，适用于页面刷新按钮或排障时主动拉最新链路；默认 `false`，列表优先读取已有快照，避免普通分页查询被全量 Trace 重建阻塞。 |
| sort_by | enum | `started_at`、`updated_at`、`duration_ms`、`node_count`、`failed_node_count`、`root_type`、`status`、`id`。 |
| sort_order | enum | `asc` 或 `desc`。 |
| page / page_size | number | 页码与每页数量，`page_size` 最大 100。 |

响应示例：

```json
{
  "data": {
    "items": [
      {
        "id": "scheduled_job_run_001",
        "root_id": "scheduled_job_run_001",
        "root_type": "scheduled_job_run",
        "title": "定时作业运行 scheduled_job_run_001",
        "summary": "代码仓库质量安全规范巡检完成。",
        "status": "succeeded",
        "started_at": "2026-06-20T01:00:00+00:00",
        "updated_at": "2026-06-20T01:00:08+00:00",
        "duration_ms": 8000,
        "node_count": 8,
        "failed_node_count": 0,
        "running_node_count": 0,
        "diagnostic_nodes": [],
        "related_ids": {
          "plugin_invocation_log": ["plugin_invocation_log_001"],
          "ai_executor_runner": ["ai_executor_runner_001"],
          "ai_executor_task": ["ai_executor_task_001"],
          "model_gateway_log": ["model_gateway_log_001"],
          "code_inspection_report": ["code_inspection_report_001"],
          "result_write_record": ["result_write_record_scheduled_job_run_001"],
          "audit_event": ["audit_001"]
        }
      }
    ],
    "total": 1
  },
  "trace_id": "trace_010"
}
```

详情响应在列表字段基础上返回：

- `diagnostic_nodes[]`：从 `nodes[]` 派生的诊断摘要，最多返回 5 个失败、取消、运行中或排队节点；只包含 `id/source_type/source_id/label/status/summary/error_message/error_code/started_at/finished_at/duration_ms` 等安全字段，不返回 `metadata`，供列表、详情顶部诊断建议和 AI 助手共享。
- `nodes[]`：包含 `id/source_type/source_id/label/status/summary/error_message/started_at/finished_at/duration_ms/metadata`。
- `edges[]`：包含 `from/to/label`，用于展示调用、派发、写报告、审计等依赖关系。

规则：

- 详情 `trace_id` 可传链路根 ID，也可传任一关联对象 ID 或节点 `source_id`；服务端会返回同一条聚合链路。
- `assistant_chat_run` 链路根来自 `assistant_chat_runs`，详情节点只展示运行状态、会话/消息 ID、用户、产品和引用数量等排障元数据，不返回完整用户提问、助手回复、Prompt 或知识正文。
- `result_write_record` 是从定时作业运行或独立插件调用派生的可重建写入记录节点，不是新的事实源；详情元数据仅展示写入目标、状态、导入数、预览摘要和安全反馈，用于判断运行是否真正写入报告、用户反馈、通知等产物。
- `diagnostic_nodes` 是响应层派生摘要，不是新的业务事实源；当链路无失败、取消、运行中或排队节点时返回空数组。
- 聚合来源是现有结构表或 repository source rows；PostgreSQL 运行时会在单个数据库事务中刷新可重建的 `execution_trace_snapshots` 只读快照并优先从该表分页/过滤/排序读取。列表和已命中详情可在短 TTL 内复用快照；详情未命中时必须强制重建一次快照再判定 404。该表不是新的业务事实源，也不在查询时写审计。
- 元数据返回前必须按敏感键脱敏，包含但不限于 `token`、`api_key`、`authorization`、`password`、`secret`、`cookie`；敏感值统一替换为 `<redacted>`。
- 无匹配链路返回 `404 EXECUTION_TRACE_NOT_FOUND`；非法枚举或时间格式返回 `400 VALIDATION_ERROR`。

---
