# 研发运营、定时作业与代码巡检 API

> API 分册。覆盖研发运营数据、定时作业、GitLab/Jenkins/线上日志指标、代码巡检和质量治理。主入口见 [../api.md](../api.md)，分册组索引见 [quality-operations-and-insights.md](quality-operations-and-insights.md)。

### 研发与运营数据

GitLab 每日提交和代码质量：

```http
GET /api/devops/gitlab/daily-code-metrics?product_id=product_001&date=2026-05-28
```

当前实现支持按产品、仓库和日期筛选真实登记或导入的 GitLab 每日指标；无指标时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "gitlab_metric_001",
        "product_id": "product_001",
        "repository_id": "repo_001",
        "metric_date": "2026-05-28",
        "commit_count": 18,
        "active_author_count": 5,
        "merge_request_count": 3,
        "changed_files": 42,
        "additions": 860,
        "deletions": 210,
        "quality_score": 86,
        "risk_count": 2,
        "author_metrics": [
          {"author": "alice", "commit_count": 7, "additions": 360, "deletions": 80, "review_issue_count": 1}
        ],
        "status": "collected",
        "source_channel": "manual",
        "created_by": "user_admin",
        "created_at": "2026-05-28T20:10:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_011"
}
```

产品负责人、研发负责人或管理员可登记真实聚合指标：

```http
POST /api/devops/gitlab/daily-code-metrics
Content-Type: application/json

{
  "product_id": "product_001",
  "repository_id": "repo_001",
  "metric_date": "2026-05-28",
  "commit_count": 18,
  "active_author_count": 5,
  "merge_request_count": 3,
  "changed_files": 42,
  "additions": 860,
  "deletions": 210,
  "quality_score": 86,
  "risk_count": 2,
  "author_metrics": [
    {"author": "alice", "commit_count": 7, "additions": 360, "deletions": 80, "review_issue_count": 1}
  ],
  "status": "collected",
  "source_channel": "manual"
}
```

服务端校验产品和 GitLab 仓库处于 active 状态且仓库归属该产品，计数字段不得为负数，`quality_score` 范围为 0-100；写入 `gitlab_daily_code_metrics` 后记录 `gitlab_daily_code_metric.created` 审计事件。

Jenkins 发布记录：

```http
GET /api/devops/jenkins/releases?product_id=product_001&version_id=version_001
```

当前实现支持按产品、版本、状态和环境筛选真实登记或导入的 Jenkins 发布记录；无记录时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "jenkins_release_001",
        "product_id": "product_001",
        "version_id": "version_001",
        "job_name": "rd-brain-deploy",
        "build_id": "build-20260601-001",
        "build_number": 128,
        "environment": "prod",
        "status": "success",
        "trigger_actor": "release-bot",
        "commit_sha": "8f6b7c1",
        "duration_seconds": 420,
        "started_at": "2026-06-01T12:20:00Z",
        "deployed_at": "2026-06-01T12:27:00Z",
        "source_channel": "manual_import",
        "created_by": "user_admin",
        "created_at": "2026-06-01T12:30:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_012"
}
```

产品负责人、研发负责人或管理员可登记真实发布记录：

```http
POST /api/devops/jenkins/releases
Content-Type: application/json

{
  "product_id": "product_001",
  "version_id": "version_001",
  "job_name": "rd-brain-deploy",
  "build_id": "build-20260601-001",
  "build_number": 128,
  "environment": "prod",
  "status": "success",
  "trigger_actor": "release-bot",
  "commit_sha": "8f6b7c1",
  "duration_seconds": 420,
  "started_at": "2026-06-01T12:20:00Z",
  "deployed_at": "2026-06-01T12:27:00Z",
  "source_channel": "manual_import"
}
```

服务端校验产品处于 active 状态且版本归属该产品，archived 版本不得登记发布记录；`deployment_request_id` 可选，传入时必须属于同一产品和版本；`status` 只能为 `success`、`failed`、`running` 或 `canceled`，构建编号和耗时不得为负数，部署时间不得早于开始时间；写入 `jenkins_release_records` 后记录 `jenkins_release.created` 审计事件。

运维部署方案：

```http
GET /api/devops/deployment-schemes?product_id=product_001&environment=prod&status=active&page=1&page_size=20&sort_by=updated_at&sort_order=desc
GET /api/devops/deployment-runner-targets?product_id=product_001&environment=prod&method=docker
GET /api/devops/deployment-jenkins-connections?product_id=product_001&environment=prod
POST /api/devops/deployment-jenkins-connections/connection_jenkins/connectivity-probe
```

部署方案列表要求 `deployment.read`，并按用户产品 scope 过滤。传入 `page/page_size` 时通过 PostgreSQL read model 完成 `product_id/environment/deployment_method/status/name` 筛选、count/page 和白名单排序，返回 `page/page_size/total/query_time_ms`；`sort_by` 支持 `code/name/environment/deployment_method/is_default/status/updated_at`。不传分页仅保留旧下拉兼容。

Runner 目标和 Jenkins 候选接口只允许具备 `deployment.scheme.manage` 的用户访问，并同时应用 `execution_resource_grants`：非全局用户只看到当前产品、环境已授权且 active 的资源。Runner 目标只返回具备 `deployment` capability、部署信任域、心跳健康且上报目标摘要的 Runner；每项返回 `connectivity_probe_status/connectivity_probe_checked_at`，只有平台记录的成功探测、且探测配置指纹仍与 Runner 当前本地目标一致时才返回 `ready=true`。探测有效期按环境、部署风险和方案的 `preflight_config.connectivity_probe_max_age_seconds` 取更严格值。Jenkins Job 预检使用该 POST 接口提交 `product_id/environment/jenkins_job_name`，服务端请求 Jenkins API 和 Job 只读端点并保存短期证据。所有响应不包含 SSH 私钥、主机密码、known_hosts 内容、Docker 本地路径或 `auth_config`。

具备 `deployment.scheme.manage` 的发布负责人或管理员可创建、修改和删除方案：

```http
POST /api/devops/deployment-schemes
Content-Type: application/json

{
  "product_id": "product_001",
  "code": "prod-docker",
  "name": "生产 Docker 部署",
  "environment": "prod",
  "deployment_method": "docker",
  "runner_id": "ai_executor_runner_003",
  "target_code": "production-compose",
  "timeout_seconds": 1800,
  "config": {},
  "is_default": true,
  "status": "active"
}
```

`deployment_method` 允许 `manual`、`ssh`、`docker`、`jenkins`，服务端固定映射为 `manual`、`runner`、`runner`、`integration` 执行通道。方案扩展字段包括 `rollout_strategy=all_at_once|canary|batch|blue_green`、`wave_config`、`preflight_config`、`health_check_config`、`rollback_config` 和 `window_enforcement=strict|warn|disabled`；`preflight_config.connectivity_probe_max_age_seconds` 可将探测有效期收紧为 60 至 3600 秒。配置值只能引用受控 Target/Job 和结构化参数，不能提交任意 Shell、主机或凭据。SSH/Docker 必须引用具备部署能力、已授权且已上报同方法目标的 Runner；启动部署时还必须要求该目标有平台记录的近期成功真实探测，且本地目标配置指纹未变，不能由心跳或 Runner 上报伪造。Jenkins 必须引用已授权 active 连接并提供部署 Job；启动前需要同连接与 Job 的近期成功预检，可选健康检查/回滚 Job。同产品、同环境最多一个 active 默认方案。修改使用 `PATCH /api/devops/deployment-schemes/{scheme_id}` 并提交当前 `version` 做乐观锁；切换默认方案时旧默认方案同步递增版本，当前 active 默认方案必须先设置替代默认方案才能停用、取消默认或迁移环境；仍被部署单引用的方案禁止删除。

运维部署单：

```http
GET /api/devops/deployments?product_id=product_001&version_id=version_001&status=deploying&environment=prod&page=1&page_size=20&sort_by=updated_at&sort_order=desc
POST /api/devops/deployments/deployment_request_001/connectivity-probe
GET /api/devops/deployments/deployment_request_001/connectivity-probe
GET /api/devops/deployments/deployment_request_001/connectivity-probe/logs
```

自动部署单可在启动前调用 `connectivity-probe`。Runner 方式返回受控探测任务，并通过 GET 返回排队或运行状态、剩余等待秒数、建议下次查询时间、失败分类、安全重试条件和部署单范围的日志链接；Jenkins 方式同步返回 API/Job 预检结果。只有 `ready=true` 时才可继续调用 `start`；前端“探测并启动”会展示过程和 Runner 日志，并在成功后自动执行该动作。Runner 探测超时、失败、取消或配置变化后才允许重新发起，活动任务会被复用，避免并发重复探测。

发布候选的强制集成门禁复用既有非生产 Jenkins 验收 Job：`.github/workflows/nonproduction-jenkins-acceptance.yml` 只创建平台部署记录、预检、触发并同步该 Job，不创建或重配部署环境。隔离 SSH、Docker、Jenkins Compose 环境仅用于可选的 `deployment_protocol_regression` 协议回归。

当前实现支持按产品、版本、状态、环境和标题筛选部署单，在 PostgreSQL 层完成 count/page 与 `created_at/environment/risk_level/status/title/updated_at` 白名单排序，并返回 `page/page_size/total/query_time_ms`、关联需求范围和当前页最近执行记录：

```json
{
  "data": {
    "items": [
      {
        "id": "deployment_request_001",
        "product_id": "product_001",
        "version_id": "version_001",
        "title": "生产部署",
        "environment": "prod",
        "status": "pending_ops",
        "deployment_scheme_id": "deployment_scheme_001",
        "deployment_method": "docker",
        "executor_channel": "runner",
        "requirement_ids": ["requirement_001"],
        "risk_level": "medium",
        "rollback_plan": "回滚到上一稳定版本",
        "gate_summary": {
          "blocking_bug_count": 0,
          "requirement_count": 1,
          "status": "ready"
        },
        "runs": []
      }
    ],
    "total": 1
  },
  "trace_id": "trace_012_deploy"
}
```

具备 `deployment.create` 的产品负责人、研发负责人或发布负责人可从测试完成或待发布需求发起部署：

```http
POST /api/devops/deployments
Content-Type: application/json

{
  "product_id": "product_001",
  "version_id": "version_001",
  "deployment_scheme_id": "deployment_scheme_001",
  "title": "生产部署",
  "requirement_ids": ["requirement_001"],
  "environment": "prod",
  "risk_level": "medium",
  "release_branch": "release/2026.07",
  "commit_sha": "8f6b7c1",
  "artifact_version": "2026.07.09-1",
  "deploy_window_start": "2026-07-09T13:00:00Z",
  "deploy_window_end": "2026-07-09T14:00:00Z",
  "rollback_plan": "回滚到上一稳定版本"
}
```

服务端校验方案属于同产品和环境且处于 active，产品和版本归属正确，需求必须处于 `testing` 或 `ready_for_release`，同版本不存在未关闭 blocker/critical Bug；如传入 `release_readiness_task_id`，必须是同产品版本下已完成的 `release_readiness` 任务。未显式传方案时只允许解析同产品、同环境的 active 默认方案。创建成功后写入 `deployment_requests` 和 `deployment_request_requirements`，并固化 `scheme_snapshot`；后续修改方案不会改变既有部署单。初始状态为 `pending_ops`，同时记录 `deployment_request.created` 审计事件。

具备 `deployment.execute` 的发布负责人或运维人员可启动部署，执行方式完全取自部署单方案快照，客户端无需再指定执行器：

```http
POST /api/devops/deployments/deployment_request_001/start
Content-Type: application/json

{}
```

启动前会执行只读预检并创建前置质量门禁：严格模式必须处于 `deploy_window_start/end` 内，产品/版本/方案快照仍有效，Commit、制品版本和 `artifact_digest` 完整，阻塞 Bug/发布评估通过，回滚配置存在，Runner/Jenkins 就绪且产品环境授权仍 active。任何阻断都会保持 `pending_ops` 并返回结构化阻断项。

启动通过后，部署单、首波 `deployment_runs`、`deployment_run_steps`、关联需求状态、审计和 `execution_outbox_events` 在同一数据库事务提交。API 不直接等待 Runner/Jenkins；execution worker 按幂等键认领派发。执行矩阵如下：

| 部署方式 | 启动行为 | 结果来源 |
| --- | --- | --- |
| 人工 | run 直接进入 `running` | 人工调用 complete 登记 |
| SSH / Docker | Outbox 创建 `executor_type=deployment` 的 Runner task，run 进入 `queued` | Runner 日志和完成回写自动同步 |
| Jenkins | Outbox 使用方案中的连接、Job 和参数触发构建 | Webhook 优先，后台同步器轮询补偿，也可手工 sync |

只有人工部署使用完成接口：

```http
POST /api/devops/deployments/deployment_request_001/complete
Content-Type: application/json

{
  "status": "success",
  "external_build_id": "build-20260709-001"
}
```

`status=success` 时部署单进入 `succeeded`，部署运行进入 `success`，关联需求进入 `released`；`status=failed` 或 `rolled_back` 时部署单进入失败或回滚状态，关联需求回到 `ready_for_release`，并创建来源为 `deployment_failure` 的 Bug。SSH/Docker/Jenkins 终态使用同一收口逻辑，但由执行通道回写触发，客户端不能人工伪造自动部署成功。

灰度、分批和蓝绿策略按 `wave_config` 创建波次。每波部署后由 Worker 创建验证步骤，健康检查和冒烟检查通过才创建下一波；失败时按 `rollback_config.auto_on_failure/auto_risk_threshold` 选择自动回滚或 `waiting_takeover`。回滚使用独立运行：

```http
POST /api/devops/deployments/deployment_request_001/rollback
Content-Type: application/json

{"reason": "健康检查失败，回滚到上一稳定制品"}
```

SSH/Docker 使用 Runner 本地目标固定回滚能力，Jenkins 使用方案快照中的 rollback Job；平台不接收任意回滚命令。回滚成功进入 `rolled_back`，回滚失败进入 `failed` 并保留人工接管提示。

部署详情：

```http
GET /api/devops/deployments/deployment_request_001
```

响应聚合部署单、需求、方案快照、质量门禁、发布波次、所有 deploy/verify/rollback runs、步骤证据、健康状态、回滚关联、派发 Outbox 和脱敏审计事件，供前端详情抽屉直接展示。

统一运行观测接口：

```http
GET /api/devops/deployments/deployment_request_001/runs/deployment_run_001/logs
POST /api/devops/deployments/deployment_request_001/runs/deployment_run_001/sync
```

日志接口要求 `deployment.read` 并按产品 scope 校验：Runner 返回逐条执行日志，Jenkins 和人工运行返回脱敏状态日志。`sync` 只用于 Jenkins 且要求 `deployment.execute`，用于立即同步队列、构建和取消结果；后台 `deployment_sync_worker` 也会按 `next_sync_at` 持续处理未终结 Jenkins run。

Jenkins 连接在启动前再次校验；不可用时部署单保持 `pending_ops`。外部触发失败、缺少 Queue Location，或 Queue/Build URL 与配置的 Jenkins endpoint 不同源时，本次 run 和部署单进入可重试 `failed`，需求保持待发布，失败摘要只保存异常类型；系统不会向不同源 URL 转发 Jenkins Basic Auth 凭据。具备 `deployment.cancel` 的用户可调用 `POST /api/devops/deployments/{deployment_request_id}/cancel`。待执行或人工部署可直接进入 `cancelled`；运行中的 Runner/Jenkins 部署先进入 `cancelling` 并向外部通道发出取消请求，只有 Runner/Jenkins 确认终态后才进入 `cancelled`，关联需求随后回到 `ready_for_release`。Jenkins 取消请求发送失败时恢复 `deploying`，记录脱敏告警日志并允许重试取消。

执行资源授权：

```http
GET /api/system/execution-resources?product_id=product_001&environment=prod&resource_type=runner_target&status=active
POST /api/system/execution-resources
PUT /api/system/execution-resources/{grant_id}
```

创建请求包含 `product_id/environment/resource_type=runner_target|jenkins_connection/resource_id/target_code`；Runner Target 必须填写目标编码。创建和更新要求全局管理员或 `system.settings.manage`，更新提交当前 `version` 与 `status=active|disabled`，版本不匹配返回 `RESOURCE_VERSION_CONFLICT`。列表允许发布负责人按产品 scope 查看，不能返回资源凭据或 Runner 本地配置。

外部事件 Inbox：

```http
POST /api/integrations/webhooks/{provider}/{connection_id}
GET /api/system/external-events?provider=github&status=failed&page=1&page_size=20
POST /api/system/external-events/{event_id}/retry
```

Provider 支持 GitHub、GitLab、Jenkins 和受控可观测性来源。Webhook 根据连接中的 Secret 引用校验签名/专用 Token，每次请求（包括重复 Delivery）都必须先验签；以 Provider Delivery ID 幂等写入 `external_event_inbox` 并返回不包含 payload 的 `202` 确认。相同 Delivery ID 只有在 payload hash、事件类型和连接均一致时才视为重复，否则返回 `409 WEBHOOK_DELIVERY_CONFLICT` 并写审计。保存 payload 前执行字段白名单、大小限制和密钥脱敏。Worker 使用租约投影 PR/MR/CI、Jenkins、Prometheus/OpenTelemetry/Sentry 或用户行为事实；重放同一 Delivery 不得重复写质量证据或发布状态。事件列表要求管理员、`audit.read`、`system.health.read` 或 `system.plugins.manage`；只公开脱敏 context。仅 `failed/dead_letter` 可重试，其他状态返回 `EXTERNAL_EVENT_RETRY_INVALID`。

GitHub/GitLab 评论、Review、request changes 和 merge 使用内部 `git_writeback_requested` Outbox 契约。连接必须显式声明对应 `write_permissions`，仓库必须属于同产品；merge 还必须引用 `passed`、无阻断且至少一份独立证据的质量门禁。幂等键相同的写回只保留一条 Outbox，Worker 执行前会再次校验连接、仓库和门禁，凭据仅在执行时从 `env:`/Vault 引用解析。

研发运营统一聚合列表：

```http
GET /api/devops/operational-metrics?category=Jenkins%20发布&name=deploy&status=success&page=1&page_size=10&sort_by=updated_at&sort_order=desc
```

该接口面向运营治理列表聚合 GitLab 每日代码指标、Jenkins 发布记录、运维部署单和线上运行日志指标，返回统一行字段 `category`、`name`、`value`、`status`、`updated_at` 以及原始上下文字段；运维部署行必须额外保留 `deployment_method`、`executor_channel` 和 `deployment_scheme_id`，供页面准确展示执行方式和操作。支持 `category` 精确筛选、`exclude_category` 精确排除、`name` 文本筛选、`status` 精确筛选、`page/page_size` 服务端分页，`sort_by` 支持 `category/id/name/status/updated_at/value`，`sort_order` 支持 `asc/desc`。PostgreSQL 运行时必须通过 repository SQL read model 聚合查询四类来源，并在 SQL 层完成筛选、排序和分页；MemoryStore 仅保留为测试 helper fallback。日志监控使用 `exclude_category=运维部署`，独立运维部署页面使用 `category=运维部署`；两者不在前端拉全量后本地拼装、排序或分页，登记弹窗仍使用各原始 POST 接口写入真实指标或部署单。服务端必须同时执行类别权限收窄：仅具备 `deployment.read` 时强制限定 `category=运维部署`，仅具备 `devops.read` 时强制排除运维部署，显式查询无权类别返回 `403 FORBIDDEN`。

线上运行日志运营指标：

```http
GET /api/ops/online-log-metrics?product_id=product_001&module_code=checkout&environment=prod&from=2026-06-01T00:00:00Z&to=2026-06-01T01:00:00Z
```

当前实现支持按产品、模块、环境和时间窗口筛选真实登记或导入的线上运行日志聚合指标；无记录时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "online_log_metric_001",
        "product_id": "product_001",
        "module_code": "checkout",
        "environment": "prod",
        "window_start": "2026-06-01T00:00:00Z",
        "window_end": "2026-06-01T01:00:00Z",
        "request_count": 2400,
        "error_count": 12,
        "error_rate": 0.005,
        "p95_latency_ms": 318.5,
        "p99_latency_ms": 640.25,
        "core_event_count": 240,
        "top_errors": [
          {
            "message": "PaymentTimeout",
            "count": 7
          }
        ],
        "anomaly_summary": "checkout error spike after release",
        "status": "collected",
        "source_channel": "manual_import",
        "created_by": "user_admin",
        "created_at": "2026-06-01T01:05:00Z",
        "updated_at": "2026-06-01T01:05:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_013"
}
```

产品负责人、研发负责人或管理员可登记真实线上运行日志聚合指标：

```http
POST /api/ops/online-log-metrics
Content-Type: application/json

{
  "product_id": "product_001",
  "module_code": "checkout",
  "environment": "prod",
  "window_start": "2026-06-01T00:00:00Z",
  "window_end": "2026-06-01T01:00:00Z",
  "request_count": 2400,
  "error_count": 12,
  "p95_latency_ms": 318.5,
  "p99_latency_ms": 640.25,
  "core_event_count": 240,
  "top_errors": [
    {
      "message": "PaymentTimeout",
      "count": 7
    }
  ],
  "anomaly_summary": "checkout error spike after release",
  "status": "collected",
  "source_channel": "manual_import"
}
```

服务端校验产品处于 active 状态，`module_code` 如传入必须属于该产品且模块 active，时间窗口必须满足 `window_end > window_start`；请求数、错误数、核心事件数和延迟不得为负数，错误数不得大于请求数，`status` 只能为 `collected`、`partial` 或 `failed`。`error_rate` 由服务端按 `error_count / request_count` 计算；记录写入 `online_log_metrics` 后记录 `online_log_metric.created` 审计事件。外部线上日志自动采集器仍属后续增强，当前入口用于导入或手工登记真实聚合指标，不生成测试兜底行。

采集运行记录：

```http
GET /api/collectors/runs?collector_type=gitlab_daily_code_metric&product_id=product_001&status=running
```

返回真实采集运行台账；无记录时返回 `items: []` 和 `total: 0`，不返回示例运行：

```json
{
  "data": {
    "items": [
      {
        "id": "collector_run_001",
        "collector_type": "gitlab_daily_code_metric",
        "product_id": "product_001",
        "source_system": "gitlab",
        "status": "running",
        "started_at": "2026-06-01T08:00:00Z",
        "finished_at": null,
        "records_imported": 0,
        "error_message": null,
        "payload_summary": {
          "repository_path": "rd/platform-api"
        },
        "created_by": "user_admin",
        "created_at": "2026-06-01T08:00:00Z",
        "updated_at": "2026-06-01T08:00:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_014"
}
```

产品负责人、研发负责人或管理员可登记运行：

```http
POST /api/collectors/runs
Content-Type: application/json

{
  "collector_type": "gitlab_daily_code_metric",
  "product_id": "product_001",
  "source_system": "gitlab",
  "status": "running",
  "records_imported": 0,
  "payload_summary": {
    "repository_path": "rd/platform-api"
  }
}
```

运行完成或取消时更新状态：

```http
PATCH /api/collectors/runs/collector_run_001
Content-Type: application/json

{
  "status": "succeeded",
  "records_imported": 3
}
```

`collector_type` 只允许 `code_inspection`、`dashboard_snapshot_refresh`、`gitlab_daily_code_metric`、`jenkins_release`、`lifecycle_context_refresh`、`online_log_metric`、`pending_attribution_retry`、`plugin_action_invoke`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；`status` 只允许 `running`、`succeeded`、`failed`、`cancelled`。接口校验、`collector_runs.ck_collector_run_type` 数据库约束和定时作业 `create_collector_run_for_job` 产出的类型必须保持一致，避免 dashboard/lifecycle/plugin/pending 等作业运行时写入采集记录失败。`product_id` 如传入必须指向 active 产品；`source_system` 必须非空；`records_imported` 不得为负数；`failed` 必须提供非空 `error_message`；`succeeded / failed / cancelled` 为终态，不得再转回 `running` 或其他状态。创建和更新分别写入 `collector_run.created` 与 `collector_run.updated` 审计事件。采集运行记录只记录采集尝试和结果，不自动写入 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议业务数据。

AI 能力配置：

```http
GET /api/system/ai-skills?status=active&code=iteration_planning
GET /api/system/ai-agents?brain_app_id=rd_brain&status=active
POST /api/system/ai-skills
POST /api/system/ai-skills/upload?code=iteration_planning&name=迭代规划&version=1.0.0
PATCH /api/system/ai-skills/skill_001
POST /api/system/ai-agents
POST /api/system/ai-agents/upload?code=feedback_agent&name=反馈分析角色&version=1.0.0
PATCH /api/system/ai-agents/agent_001
```

Skill 配置至少包含 `code`、`name`、`version`、`input_schema`、`output_schema`、`prompt_template`、`allowed_tools`、`required_context`、`risk_level`、`requires_human_review` 和 `status`。`POST /api/system/ai-skills/upload` 用于上传 zip Skill 文件包，body 为 `application/zip` 原始二进制，query 参数提供 `code`、`name`、`version`、`status`、`risk_level` 和 `requires_human_review`；服务端校验 `skill.yaml` / `SKILL.md`、文件类型白名单、路径安全、包大小和 checksum，允许 `.md/.txt/.yaml/.yml/.json` 普通文件和 `scripts/` 下的 `.py/.sh/.ps1/.js/.ts` 脚本资产，非 `scripts/` 目录的可执行脚本返回 `INVALID_SKILL_PACKAGE`，响应返回 `source_type=package`、`package_uri`、`package_checksum`、`package_entry`、`package_files`、`package_size_bytes`、`manifest` 和 `runtime_capabilities`，脚本只展示为 `disabled_pending_sandbox` 且不会自动执行。AI角色（Agent）配置至少包含 `code`、`name`、`brain_app_id`、`model_gateway_config_id`、`system_prompt`、`default_skill_ids`、`execution_policy`、`tool_policy` 和 `status`。`POST /api/system/ai-agents/upload` 用于上传 zip Agent 文件包，body 为 `application/zip` 原始二进制，query 参数提供 `brain_app_id`、`code`、`name`、`version`、`status`、可选 `model_gateway_config_id` 和可重复 `default_skill_ids`；服务端校验 `agent.yaml` / `AGENT.md`、文件类型白名单、路径安全、包大小和 checksum，脚本资产同样只允许位于 `scripts/` 目录，`AGENT.md` 作为 `system_prompt`，响应返回 `source_type=package`、`package_uri`、`package_checksum`、`package_entry`、`package_files`、`package_size_bytes`、`manifest` 和 `runtime_capabilities`。只有管理员可创建和修改 AI角色/Skill；响应不得包含模型密钥、外部系统 token 或凭据明文。配置创建、修改、启用、停用和包上传分别写入 `ai_skill.created` / `ai_skill.updated` / `ai_skill.package_uploaded` / `ai_agent.created` / `ai_agent.updated` / `ai_agent.package_uploaded` 审计事件。

定时系统作业：

```http
GET /api/system/scheduled-job-catalog
GET /api/system/scheduled-jobs?job_type=iteration_plan_suggestion_generate&enabled=true
POST /api/system/scheduled-jobs
PATCH /api/system/scheduled-jobs/scheduled_job_001
POST /api/system/scheduled-jobs/scheduled_job_001/run
GET /api/system/scheduled-job-runs?scheduled_job_id=scheduled_job_001&status=failed
POST /api/system/scheduled-job-runs/scheduled_job_run_001/cancel
```

`GET /api/system/scheduled-job-catalog` 是定时作业配置的服务端注册中心，要求 `system.scheduled_jobs.manage` 或 `system.scheduled_jobs.run`。响应字段包括：`job_types[]`（`value/label/category/default_execution_mode/requires_product/requires_plugin_resource/requires_ai_assembly/allow_create/runnable/unavailable_reason`）、`required_job_types.product/plugin_resource/ai_processing`、`execution_modes[]`、`schedule_types[]`、`connection_environments[]`，以及 `code_inspection.native_scan_mode/default_scan_mode/scan_modes/scanner_engines/builtin_rules/ignore_rules/result_actions/severity_thresholds/default_result_actions` 和 `generic_result_actions[]`。`generic_result_actions[]` 至少包含 `save_scheduled_job_result`、`send_notification`、`create_requirements` 与 `sync_dingtalk_document`；其中 `create_requirements` 与 `sync_dingtalk_document` 仅用于 AI 模式下的 `plugin_action_invoke` 作业，典型场景包括同步钉钉文档、用户洞察转需求、运营周报归档和巡检摘要沉淀。前端新增/编辑弹窗、AI 助手定时作业草案和测试 mock 必须以该响应为首选来源；新增入口只展示 `allow_create=true` 且 `runnable=true` 的类型，`allow_create=false` 或 `runnable=false` 的类型仅用于历史作业标签、兼容读取和内部迁移。只有接口不可用时才允许使用本地静态选项降级，且降级不得覆盖服务端校验。

`POST /api/system/scheduled-jobs` 和 `POST /api/system/scheduled-jobs/dry-run` 对已登记但 `allow_create=false` 的 `job_type` 返回 `400 SCHEDULED_JOB_TYPE_UNAVAILABLE`，错误消息使用 catalog 的 `unavailable_reason`；未知 `job_type` 继续走通用枚举校验返回 `VALIDATION_ERROR`。`POST /api/system/scheduled-jobs/{job_id}/run` 对 `runnable=false` 的历史作业返回 `400 SCHEDULED_JOB_TYPE_NOT_RUNNABLE`，不得创建伪成功运行记录，也不得落 collector run 或插件调用日志。

`GET /api/system/scheduled-jobs` 支持 `page/page_size/sort_by/sort_order` 服务端分页排序，`page_size` 最大 100，`sort_order` 为 `asc|desc`，`sort_by` 允许 `next_run_at/created_at/updated_at/name/job_type/status/enabled/last_run_at/last_success_at/last_failure_at`；筛选参数包括 `enabled`、`job_type`、`status`、`product_id`、`source_system`、`name` 和 `keyword`。传入分页参数时生产路径必须通过 PostgreSQL read model 返回 `items/page/page_size/total/query/performance`，避免前端全量拉取后本地过滤；未传分页参数时保留旧 `items/total` 全量返回兼容，但不作为新增管理页面默认读路径。

`GET /api/system/scheduled-job-runs` 支持 `page/page_size/sort_by/sort_order` 服务端分页排序，`page_size` 最大 100，`sort_order` 为 `asc|desc`，`sort_by` 允许 `started_at/finished_at/created_at/updated_at/status/trigger_type/records_imported`；筛选参数包括 `run_id`（可重复传多个）、`scheduled_job_id` 和 `status`。传入分页参数时生产路径必须通过 PostgreSQL read model 返回 `items/page/page_size/total/query/performance`，并按当前用户产品 scope 通过运行所属作业过滤；未传分页参数时保留旧 `items/total` 全量返回兼容，用于助手按 runId 拉运行详情或旧测试 helper，不作为定时作业页面运行记录主表默认读路径。

当 `user_feedback_insight_extract`、`code_repository_inspection` 等 AI 链路作业在数据连接阶段失败并且尚未进入模型处理时，运行响应必须把 `result_summary.execution_nodes.skill_processing.status` 设为 `not_run`，`model_gateway_called=false`，`processing_mode=not_started`，并在 note 中说明“数据连接失败，AI 大模型处理未开始”；不得因为作业类型需要 AI 就把未开始的阶段标记为 `failed/model_gateway_called=true`。当 `result_summary.execution_nodes.data_connection.items[]` 存在时，运行详情和助手诊断必须返回连接总数、成功数、失败数、失败连接摘要和关联插件日志 ID。

创建定时作业示例：

```json
{
  "name": "每周生成 AI 迭代规划建议",
  "job_type": "iteration_plan_suggestion_generate",
  "enabled": true,
  "schedule_type": "cron",
  "cron_expression": "0 9 * * MON",
  "timezone": "Asia/Shanghai",
  "product_id": "product_001",
  "source_system": "ai-brain",
  "execution_mode": "ai_generated",
  "agent_id": "agent_iteration_planner",
  "skill_ids": ["skill_usage_analysis", "skill_feedback_summary", "skill_iteration_planning"],
  "knowledge_document_ids": ["knowledge_doc_001"],
  "model_gateway_config_id": "model_gateway_config_001",
  "config_json": {
    "planning_cycle": "weekly",
    "evidence_window_days": 14,
    "min_evidence_count": 3
  },
  "max_retry_count": 2,
  "timeout_seconds": 600,
  "lock_ttl_seconds": 900
}
```

`job_type` 首批允许 `gitlab_daily_code_metric_collect`、`jenkins_release_collect`、`online_log_metric_collect`、`user_usage_metric_collect`、`user_feedback_collect`、`user_feedback_insight_extract`、`code_repository_inspection`、`online_log_ai_analysis`、`iteration_plan_suggestion_generate`、`dashboard_snapshot_refresh`、`lifecycle_context_refresh`、`plugin_action_invoke` 和 `pending_attribution_retry`。`execution_mode` 只允许 `deterministic`、`ai_assisted`、`ai_generated`，前端用户侧标签为“AI执行”，其中 `deterministic` 展示为“不调用 AI”。`user_feedback_collect` 表示仅取数采集，不执行平台 Skill/大模型处理；若用户反馈作业同时配置动作、AI 模型、AI角色或 Skills，后端必须按兼容规则归一为 `user_feedback_insight_extract` 并使用 `ai_generated`，避免配置了 AI 链路却静默直通。`iteration_plan_suggestion_generate`、`online_log_ai_analysis` 和 `user_feedback_insight_extract` 属于 AI 必选链路作业，服务端即使收到 `deterministic` 也必须按有效 `ai_generated` 校验并要求 active AI角色（Agent）、作业显式提交的 active Skills 和 active 模型网关（可取 AI角色默认模型网关或作业覆盖项）；缺失时分别返回 `AI_AGENT_REQUIRED`、`AI_SKILL_REQUIRED` 或 `MODEL_GATEWAY_CONFIG_REQUIRED`，后端不得使用 AI角色默认 Skill 兜底空 `skill_ids`。`plugin_action_invoke` 在 `deterministic` 下仍可作为普通取数/执行调用；在 `ai_assisted/ai_generated` 下必须同样要求 active AI角色、显式 Skills 和 active 模型网关，正式运行时先调用 Skill/模型处理数据连接响应，再以 AI 输出执行通用结果动作。`plugin_connection_ids` 和 `plugin_action_ids` 分别表示按顺序配置的多个数据连接和多个动作；服务端会保存到 `config_json.orchestration` 并在响应顶层展开，`plugin_connection_id` 和 `plugin_action_id` 仍取第一项，用于兼容当前动作调用、来源链路和旧客户端；多个数据连接必须归属主 `plugin_action_id` 所在插件，否则返回 `400 PLUGIN_CONNECTION_MISMATCH`。例外：`code_repository_inspection + config_json.scan_mode=native_full_scan` 不要求 `plugin_action_id/plugin_action_ids`，`plugin_connection_id/plugin_connection_ids` 可为空，也可绑定 active GitHub/GitLab 凭据连接供 clone/fetch 读取 token。`knowledge_document_ids` 为可选知识引用；配置后运行时必须先按当前用户权限读取可检索知识 chunk，并以 `knowledge_references` 注入 AI角色/Skill 模型请求上下文。`result_actions` 为可选结果写入动作列表；`code_repository_inspection` 使用该字段按顺序执行 `write_code_inspection_report`、`create_bug_for_severe_findings`、`create_task_for_severe_findings`、`send_notification` 等处理，并通过 `config_json.repository_id/branch` 指定扫描仓库和扫描分支；`online_log_ai_analysis` 使用该字段执行 `save_scheduled_job_result` 或 `send_notification` 通用结果动作；AI 模式下的 `plugin_action_invoke` 还支持 `create_requirements` 与 `sync_dingtalk_document`，前者从 AI 输出的 `requirements` 数组创建需求管理记录，后者调用钉钉文档更新动作把 `dingtalk_markdown` 或模板渲染内容写入指定文档，运行结果通过 `feedback.write_preview` 和结果写入记录展示写入目标、写入数量、需求 ID、钉钉文档 ID、主题、投递状态和样例。指定 `model_gateway_config_id` 时覆盖 AI角色默认模型网关，但仍必须指向 active 模型网关配置。`cron_expression` 和 `interval_seconds` 按 `schedule_type` 二选一，前端必须紧跟调度方式展示；`source_system` 为内部来源标识，模板或默认值写入 payload，但新增/编辑表单不展示给用户填写；`timezone` 默认 `Asia/Shanghai`。作业创建、修改、启停、手动触发、从运行记录复跑和取消必须写入审计；从现有作业或运行记录快照复制出的新增请求可携带 `config_json.template_source={source_type,source_id,title}`，服务端在 `scheduled_job.created/updated` 审计 payload 中返回 `template_source`，用于追踪作业模板来源；前端必须在复制弹窗、作业列表和运行详情中展示 `template_source`，避免来源仅存在于高级 JSON 或审计里。运行接口 `trigger_type` 允许 `manual`、`manual_rerun` 和 `scheduler`，未传默认 `manual`，非法值返回 `400 VALIDATION_ERROR`；运行记录复跑不新增专用 API，前端读取运行记录的 `scheduled_job_id` 后调用 `POST /api/system/scheduled-jobs/{job_id}/run` 并传入 `{"trigger_type":"manual_rerun","source_run_id":"<历史运行 ID>"}`，成功后展示返回的新运行实例详情；若携带 `source_run_id`，服务端必须校验来源运行存在、属于同一作业且触发类型为 `manual_rerun`，响应和后续运行列表必须返回轻量 `source_run_summary` 便于对比来源运行与本次运行。运行终态审计事件 `scheduled_job_run.succeeded/failed` 的 payload 必须包含 `scheduled_job_id`、可选 `source_run_id`、`job_type`、`product_id`、`status`、`trigger_type`、`records_imported`、`collector_run_id`、可选 `plugin_invocation_log_id` 和 `error_code`，并在存在对应配置时补充 `execution_mode`、`agent_id`、`skill_ids`、`model_gateway_config_id`、`model_gateway_called`、`knowledge_document_ids`、`plugin_code`、`plugin_action_id`、`plugin_action_ids`、`plugin_action_code`、`plugin_connection_id`、`plugin_connection_ids`、`plugin_connection_environment`、`result_action_types` 和 `result_write_target`，用于区分普通手动运行、复跑、调度触发、AI 装配、多环境连接和结果写入目标；审计 payload 不保存完整请求响应、Prompt、模型输出或密钥。

定时作业链路按“数据来源 -> AI执行处理 -> 动作写入/通知”理解：作业定义中 `plugin_connection_ids` 表示按顺序配置的数据来源连接，`execution_mode/model_gateway_config_id/agent_id/skill_ids/knowledge_document_ids` 共同组成 AI执行配置，`plugin_action_ids` 表示数据来源阶段使用的读取/取数动作模板，`plugin_input_mapping` 表示运行时传给连接/动作的输入参数。页面支持两类数据来源：直接取数连接（例如用户反馈、AI 客服聊天记录、HTTP API）和授权连接 + 读取动作（例如钉钉文档 MCP、GitHub、GitLab、邮箱）；后者会在 `config_json.orchestration.data_source_mode=authorized_read_action` 中记录来源方式，并把具体对象参数保存到 `plugin_input_mapping`。`plugin_connection_id` / `plugin_action_id` 是第一项兼容字段。`plugin_output_mapping` 是作业级覆盖项；为空时运行时复用动作模板的 `result_mapping`。插件输出映射第一阶段支持 `records_imported_path` 这类摘要字段映射和 `write_target` 写入目标，JSONPath 子集支持 `$` 根、点路径、`['key']` / `["key"]` bracket key、数组下标和 `[*]` 通配，动作试运行、定时作业 dry-run、正式运行写入预览和结果写入记录必须复用同一解析口径。真实业务入库仍必须通过对应业务 service 完成；通用结果写入或通知动作使用 `result_actions` 表达。

`plugin_input_mapping`、插件连接 `request_config.query/headers` 和动作 `request_config.query/headers` 支持动态时间 token，保存配置时保留语义 token，运行实例触发时按作业 `timezone` 解析。首批 token 包括 `{{current_date}}` / `{{date}}`（输出 `YYYYMMDD`）、`{{date_iso}}`（输出 `YYYY-MM-DD`）、`{{now}}`、`{{today.start}}`、`{{today.end}}`、`{{yesterday.start}}`、`{{yesterday.end}}`、`{{last_7_days.start}}`、`{{last_7_days.end}}`、`{{last_full_week.start}}` 和 `{{last_full_week.end}}`；日期和时间 token 支持简单天数偏移表达式，例如 `{{current_date-7}}` 表示当前日期前 7 天、`{{today.start-7}}` 表示今天零点前 7 天。历史值 `last_monday_00:00:00` 与 `this_monday_00:00:00` 兼容解析为上一完整自然周起止时间。前端配置默认以官方 `connection_schema` 字段作为业务配置展示，例如 GitHub 连接展示可选“仓库地址”，仅在用户填写时自动解析 `owner/repo`，未填写时只保存 Token/Headers，不落空仓库参数；GitLab 连接展示可选“GitLab 地址”，仅在用户填写时自动解析 Endpoint、`project_id` 与 `project_path`，未填写时只保存 Endpoint/Token，不落空项目参数；schema 管理字段保存到 `request_config.query/headers`，但不重复出现在高级 Params 表格。高级 Params/Headers 仅用于补充额外 API query/header，并在高级模式中提供 JSON 同步和反向应用，避免要求业务用户手写复杂 JSON。连接配置作为公共默认值，动作配置作为具体接口覆盖项；同名 query/header 由动作覆盖连接。动作 `request_config.path` 中的 `{{owner}}`、`{{repo}}`、`{{project_id}}`、`{{api_version}}` 等非时间模板变量可从合并后的连接 query、动作 query 和运行输入中的标量值解析，用于 GitHub/GitLab 官方动作路径。

`config_json.ai_executor` 是定时作业 AI 处理阶段的执行器配置。未传时服务端按系统默认执行器补齐 `{runner_id:"ai_executor_runner_system_default", executor_type:"model_gateway"}`；该模式要求可解析 active 模型网关，并在 `skill_processing.runner_execution` 中返回 `model_gateway_called/model_gateway_log_id/result_json`。当 `runner_id` 指向本地 Runner 且 `executor_type` 为 `codex`、`claude`、`hermes` 或 `openclaw` 时，创建/修改/试运行仍必须校验 active AI角色和作业显式 Skills，但允许不传 `model_gateway_config_id`；正式运行在数据连接完成后创建 `ai_executor_task`，任务 `request_config.scheduled_job_ai_execution.stage=ai_processing`，冻结数据连接响应、知识引用、Skill 输出契约和动作映射。运行记录在 Runner `queued/claimed/running` 期间保持 `status=running`，`execution_nodes.skill_processing.status=waiting_runner`，Runner 成功完成后服务端按完成 payload 中的 `result/parsed_output/output_preview` 解析 AI 输出、执行 Skill Schema 校验并继续结果动作；Runner 失败、取消、超时或死信时运行失败，动作节点标记为 `not_run`，并在 `runner_execution` 保留任务 ID、工作区、日志和错误。

平台模型网关 AI 处理在构造模型请求前会对数据连接响应做有界压缩：大数组按 head/middle/tail 采样，默认最多 80 行，每个字段默认最多 360 字符；完整数据连接响应仍保留在运行记录的数据连接节点，压缩仅影响发送给模型的 `data_connection_response`。发生压缩时，运行摘要 `execution_nodes.skill_processing.input.source_compaction` 返回 `compacted/max_source_sample_rows/max_source_field_chars/sampled_lists/source_row_count`，便于排障确认模型实际看到的样本范围。模型调用失败时，`execution_nodes.skill_processing` 和 `result_summary.processing` 会透出 `model_log_id/model_gateway_config_id/model/provider/latency_ms/failure_detail/source_compaction`，但不保存完整 Prompt、密钥或认证 Header。

`GET /api/system/scheduled-job-runs/observability` 的动作写入口径必须优先消费 `result_summary.execution_nodes.result_actions[]`：`action_write_runs` 按每个动作节点计数，`action_write_success_runs` 按每个动作节点状态统计，`write_target_distribution` 按每个动作节点的写入目标聚合；旧运行缺少 `result_actions[]` 时才回退兼容字段 `result_action`。这样同一运行配置多个邮件通知、用户洞察写入或代码巡检写入动作时，健康概览不会只统计第一个动作。

MaxCompute 每周用户反馈场景使用 `job_type=user_feedback_insight_extract`，数据连接作为普通 HTTP 插件连接保存 endpoint、认证和公共 Params/Headers，结果写入动作通常为 `action_type=http_request` 的自定义 HTTP 动作；请求时间参数优先在连接/动作 Params 中配置，作业级 `plugin_input_mapping` 仅作为兼容和高级覆盖。作业必须选择 `model_gateway_config_id`、`agent_id` 和 `skill_ids`，页面展示为 AI 模型、AI角色和 Skills，可选选择知识引用文档。动作 `result_mapping` 默认包含 `write_target=user_feedback_insights`、`insights_path`、`records_imported_path` 和 `rows_path`，作业 `plugin_output_mapping` 仅用于覆盖。运行顺序为数据连接取数、读取知识引用、模型网关按 AI角色/Skill 处理为结构化 JSON、结果写入。运行成功后 `records_imported` 为实际新增洞察数，`result_summary.plugin.response_summary.json.row_count` 保留源表读取行数摘要；`result_summary.execution_nodes` 必须按 `data_connection`、`skill_processing`、`result_action` 三段保存数据连接获取内容、Skill 处理内容和结果写入反馈内容。`skill_processing.model_gateway_called=true`，并包含 `model_gateway_config_id`、`model_log_id`、`processing_mode=model_gateway_json_transform`、`input.knowledge_references` 和模型输出 JSON 摘要。

代码仓库巡检场景使用 `job_type=code_repository_inspection`。创建或修改请求必须携带 `product_id`；`config_json.repository_id`、`config_json.repository_ids` 和 `config_json.branch` 均为高级可选项，省略仓库 ID 时服务端按产品下 active 且 `repo_type=code` 的 Git 仓库自动展开扫描，省略分支时按每个仓库 `default_branch` 兜底；显式传 `repository_id/repository_ids` 时仅扫描指定仓库。新增作业类型、服务端模板目录和 AI 助手草案默认给出 `execution_mode=ai_assisted`，并按资源选择器带出系统默认模型网关、代码审查 AI角色和代码巡检 Skill；页面提交前不得为产品级默认扫描自动写入第一仓库 ID。用户显式切换确定性执行或表达“不调用 AI、纯扫描、只扫描、静态扫描”时才使用 `deterministic`。`native_full_scan` 使用平台内置本地扫描器，`sync_existing_alerts` 和 `trigger_platform_scan` 使用 `plugin_connection_id` / `plugin_action_id` 调用仓库扫描器、SonarQube、SAST 或自建质量扫描服务。运行时插件输入顶层携带实际 `repository_id/branch`，AI 处理上下文携带 `configured_repository_id/configured_repository_ids/configured_branch`。插件响应推荐返回 `repository_id`、`branch`、`commit_sha`、`risk_level`、`summary` 和 `findings[]`；若响应未返回 `branch`，报告写入使用作业分支或仓库默认分支兜底。每个 finding 至少包含 `rule_id`、`category`、`severity`、`title`、`description`、`file_path`、`line_number` 和 `recommendation`，并推荐包含 `committer_name`、`committer_email`、`committer_username`。动作 `request_config.severity_mapping` 或作业 `config_json.severity_mapping` 可把外部扫描器等级映射为平台 `info/low/medium/high/critical`。示例 `result_actions`：

补充约定：代码巡检作业模板选择默认 AI 资源时，AI角色优先匹配编码 `code-reviewer`，Skill 优先匹配“代码分析skill”或编码 `code_analysis_skill`；找不到时再兼容旧 `code_reviewer`、`code_inspection_agent`、`code_inspection_analysis` 和 `code_review`。

当 `config_json.scan_mode=native_full_scan` 时，服务端使用内置扫描器在 `CODE_SCAN_WORKDIR` 下维护 `mirrors/` 仓库缓存，并按 repository + branch + commit checkout 到单次运行目录；HTTP(S) 私有仓库 clone/fetch 仍使用产品 Git 仓库 `remote_url`，token 解析顺序为：任务绑定且 provider 匹配的 active GitHub/GitLab 插件连接、产品 Git 仓库 `credential_ref`、provider 级环境变量。插件连接仅作为凭据来源读取 `auth_config.token_ref/secret_ref/token/access_token/api_key` 或授权类 header，不要求连接里维护仓库 URL；API 响应、运行摘要、报告和错误信息不得返回 token 或带凭据 remote_url。扫描 `config_json.scan_rules`，按 `ignore_dirs` / `ignore_rules` 过滤目录和规则，按 `severity_threshold`、`baseline_fingerprints`、`accepted_risk_fingerprints` 和 `ignored_finding_fingerprints` 过滤低级别、历史、已接受或单条忽略问题，按 `incremental_from_commit` 做增量文件扫描，并通过 git blame 回填提交人。该模式不要求 `plugin_action_id/plugin_action_ids`；`plugin_connection_id/plugin_connection_ids` 可传 `null` 或空数组，也可保存 GitHub/GitLab 凭据连接，保存后同步写入 `config_json.orchestration.plugin_connection_ids`。`repository_ids` 可一次绑定多个同产品仓库并生成多份报告，`repository_id/repository_ids` 均为空时按产品所有 active 代码仓库生成多份报告。未传 `scan_mode` 时按 `sync_existing_alerts` 兼容旧插件模式。默认运行先返回 queued，再由后台 worker 执行；运行成功后 `plugin_invocation_log_id` 为空，`result_summary.execution_nodes.native_scan` 返回 `repository_id/branch/commit_sha/files_scanned/lines_scanned/finding_count/scanner_name/scanner_version/rules_version/remote_url_hash/remote_url_summary/artifact_ref/checkout_path_retained/scan_started_at/scan_finished_at/incremental_from_commit/incremental_file_count/suppression_summary/suppressed_finding_count/quality_gate/scan_profile`，多仓库运行必须同时返回 `execution_nodes.native_scan.items[]`；`execution_nodes.data_connection.processing_mode=native_full_scan`；多仓库运行还返回 `report_ids/report_count/reports_by_repository/repository_execution`。报告额外返回同名快照字段，以及 `scan_mode/scanner_name/is_full_scan/incremental_from_commit/incremental_file_count/files_scanned/lines_scanned/rules_loaded/coverage_warning/suppressed_finding_count/suppression_summary/quality_gate/scan_profile/previous_report_id/previous_comparison`；当 `ai_assisted/ai_generated` 对 native 扫描结果做模型归一化时，模型输出可覆盖 `risk_level/summary/findings`，但上述 native 快照字段必须以扫描源结果为准。`GET /api/governance/code-inspections/{report_id}` 额外返回 `scan_summary.coverage/rule_distribution/file_distribution/committer_distribution/quality_gate/previous_comparison/scan_profile/suppression_summary` 和 `governance_summary`，其中 `scan_summary.coverage` 必须包含 `is_full_scan/incremental_from_commit/incremental_file_count/files_scanned/lines_scanned/suppressed_finding_count`，`governance_summary` 以 high/critical 且未审批忽略的 finding 为有效严重问题，计算 Bug 覆盖率、整改任务覆盖率、待审批忽略、已接受风险和治理待办。`scanner_engines` 可声明 `builtin/gitleaks/semgrep/trivy/npm/pip-audit/dependency-check`，已安装外部引擎会执行并解析 JSON 输出，结果归一为 `scanner_name=<engine>` 的 finding；未安装、超时或输出不可解析时写入 `coverage_warning`，并在 `scan_profile.external_scanner_status` 返回 `configured/executed/skipped/failed` 以及可选原因映射后继续内置扫描。异步运行被取消时，取消接口返回 `status=cancelled`，后台 worker 检测到取消后不得写入代码巡检报告或覆盖取消终态。内置规则当前包括 `secrets.hardcoded_credential` 和 `metadata.internal_address_exposure`，finding 原始证据必须脱敏，不得保存明文密钥。

代码巡检运行详情按仓库暴露三段链路：`result_summary.execution_nodes.native_scan.items[]` 为每仓 clone/scan 输出，`result_summary.execution_nodes.skill_processing.items[]` 为每仓 AI 归一化结果和模型日志，`result_summary.execution_nodes.result_action.items[]` 为每仓报告、Bug、整改任务或通知写入反馈；`result_summary.repository_execution.<repository_id>` 聚合每仓 `scan_status/ai_status/write_status/report_id/finding_count/commit_sha`。异步 Worker 遇到 clone、checkout 或 scan 临时失败时按作业 `max_retry_count` 重试，摘要在 `result_summary.processing.worker_attempts`、`worker_retry_count` 和 `worker_retry_errors[]` 中返回尝试次数和失败明细。代码巡检 AI 输出契约未由 Skill 声明时，服务端使用默认 Schema 校验 `summary/risk_level/findings[]`，模型输出不符合 Schema 时返回 `SKILL_OUTPUT_SCHEMA_INVALID` 并停止结果动作。

代码巡检 finding 支持误报忽略和风险接受审批闭环。`GET /api/governance/code-inspections/{report_id}` 的 `findings[]` 返回 `suppression_status`（`none/pending/approved/rejected`）、`suppression_reason`、`suppression_note`、`suppression_owner`、`suppression_expires_at`、`suppression_requested_by`、`suppression_requested_at`、`suppression_reviewed_by` 和 `suppression_reviewed_at`。提交忽略申请使用 `POST /api/governance/code-inspections/{report_id}/findings/{finding_id}/suppression-request`，请求体为 `{"reason":"false_positive","note":"..."}`；风险接受请求体为 `{"reason":"accepted_risk","owner":"security_owner","expires_at":"2026-07-01T00:00:00+08:00","note":"..."}`。`reason` 允许 `false_positive`、`accepted_risk`、`baseline`、`ignored` 和 `other`；`reason=accepted_risk` 缺少 `expires_at` 时返回 `422 ACCEPTED_RISK_EXPIRY_REQUIRED`，非法日期返回 `422 INVALID_DATETIME`。审批使用 `POST /api/governance/code-inspections/{report_id}/findings/{finding_id}/suppression-review`，请求体为 `{"decision":"approve|reject","note":"..."}`。只有 `pending` 状态允许审批，重复审批返回 409；批准后报告 `suppressed_finding_count` 加 1，并按原因累加 `suppression_summary`，治理概览的 suppression 分布同步变化；已批准但过期的 `accepted_risk` 不再视为有效 suppression，并在详情 `governance_summary`、dashboard `rule_governance` 和 `committer_governance` 中计入 `expired_accepted_risk_count`。申请、批准和驳回必须分别写入 `code_inspection_finding_suppression.requested/approved/rejected` 审计事件，审计 payload 保留责任人和到期时间但不保存敏感凭据。

```json
[
  {"type": "write_code_inspection_report"},
  {"type": "create_bug_for_severe_findings", "severity_threshold": "critical"},
  {"type": "create_task_for_severe_findings", "severity_threshold": "high"},
  {
    "type": "send_notification",
    "channels": ["email", "dingtalk"],
    "recipients": ["quality@example.com"],
    "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=..."
  }
]
```

运行成功后必须创建 `code_inspection_reports` 和 `code_inspection_findings`；报告返回 `scheduled_job_id`、`scheduled_job_run_id`、`plugin_connection_id`、`plugin_action_id`、`plugin_invocation_log_id`、`committer_count`、`committer_summary` 和 `created_task_ids`，finding 返回 `committer_name`、`committer_email`、`committer_username` 和 `created_task_id`，列表接口可用 `committer` 按姓名、邮箱或用户名过滤。达到阈值的问题可创建 `source=code_inspection` 的 Bug，并把 `code_inspection_report_id`、`code_inspection_finding_id`、规则、文件、行号、提交人和 `finding_fingerprint` 写入 Bug evidence；同一仓库、分支、规则、文件、行号和提交人的开放 Bug 不重复创建，运行摘要在 `bug_creation.deduplicated_bug_ids` 返回复用的 Bug。`create_task_for_severe_findings` 作为历史兼容动作不再直接创建研发任务，而是复用同一 Bug 创建/去重链路并返回 `status=deferred_to_bug_confirmation`、`created_task_ids=[]` 和 `deferred_to=bug_confirmation`；用户需在 Bug 确认后通过“AI处理”推进 `task_type=bug_fix` 的 AI Task。通知动作写入 `code_inspection_notifications`，第一阶段只记录邮件/钉钉机器人等发送目标和反馈摘要，不要求实际发出外部网络请求。运行摘要必须包含 `execution_nodes.data_connection`、`code_inspection_report`、`bug_creation`、`task_creation`、`notifications` 和 `result_actions`，方便运行详情按“取数/扫描、写报告、派生 Bug/任务、通知反馈、结果写入状态”查看；运营治理 / 代码巡检详情必须固定展示来源作业、来源运行、数据连接、结果写入动作和插件调用，便于从报告反查定时作业配置与动作执行上下文。

运行实例响应必须包含 `scheduled_job_id`、`collector_run_id`、可选 `source_run_id`、`trigger_type`、`scheduled_for`、`status`、`started_at`、`finished_at`、`records_imported`、`error_code`、`error_message`、`result_summary`、`config_snapshot`、`resolved_agent_snapshot`、`resolved_skill_snapshots`、`resolved_prompt_snapshot`、`tool_policy_snapshot`、`resolved_plugin_snapshot` 和 `plugin_invocation_log_id`；复跑运行若来源存在，还必须返回 `source_run_summary`，字段包括来源运行 `id/status/trigger_type/records_imported/error_code/started_at/finished_at/latency_ms`。任务中心 / 定时作业页面必须支持 `?tab=runs&run_id=<运行 ID>` 深链，加载运行记录后自动切换运行记录页签并打开目标运行详情；若存在 `source_run_summary`，详情页展示“复跑对比”，对比来源运行和本次运行的状态、导入数与来源错误码。`result_summary.execution_nodes.data_connection` 应包含连接 ID、连接环境、明文请求摘要、解析后的输入映射、插件响应摘要、源数据数量、请求方法、请求 URL、HTTP 响应状态和耗时；`runner_execution` 仅在 AI 执行器 Runner 场景出现，应包含 executor type、Runner ID、任务 ID、工作区、任务状态、日志和结果 JSON，Runner 未终态时运行实例保持 `running`；`skill_processing` 应包含 Skill 配置、是否调用模型网关、处理输入、知识引用数量、处理输出、候选结果数量和模型日志 ID；`result_action` 应包含写入目标、写入数量、生成 ID、报告 ID、Bug/任务/通知数量和动作反馈，并复用动作执行 `write_preview`；`task_creation` 在代码巡检历史动作延期到 Bug 确认时返回 `status=deferred_to_bug_confirmation`、`created_task_ids=[]` 和对应 Bug ID；当写入目标为 `email_notifications` 时，`result_action.feedback` 至少返回 `delivery_id`、`delivery_status`、`subject`、`sample_records` 和 `write_preview`，页面摘要展示中文写入目标、投递 ID、投递状态和收件人。运行响应应补齐 `result_summary.trace_graph`，DAG 节点按数据连接、Runner 执行、Skill/AI 处理、结果写入、业务写入、Bug/任务/通知等执行顺序展示 `input/output/duration_ms/retry_count/error`；运行详情可从成功运行调用 `POST /api/system/scheduled-job-runs/{run_id}/template` 反向生成作业模板草稿。模型日志仍只记录 provider、model、purpose、tokens、latency、status 和错误元数据，不保存完整 prompt 或完整输出。插件调用日志按管理员调试场景保存并返回明文请求/响应摘要，便于排查三方系统连接和结果写入问题。`POST /run` 仅创建一次运行实例并进入 `queued/running`，不得直接返回伪造业务结果。

待归属数据队列：

```http
GET /api/attribution/pending-items?status=pending&source_type=user_feedback
```

响应返回 `pending_attribution_items` 结构表中的真实队列项；没有数据时返回 `items: []` 和 `total: 0`，不返回示例队列项：

```json
{
  "data": {
    "items": [
      {
        "id": "pending_attr_001",
        "source_type": "user_feedback",
        "source_system": "feedback-api",
        "collector_run_id": "collector_run_001",
        "raw_subject_id": "feedback-ext-7788",
        "summary": "无法映射到产品的登录失败反馈",
        "raw_payload": {
          "channel": "support"
        },
        "suggested_product_id": null,
        "suggested_module_code": null,
        "confidence": 0.62,
        "status": "pending",
        "resolution_action": null,
        "resolution_note": null,
        "resolved_product_id": null,
        "resolved_module_code": null,
        "resolved_requirement_id": null,
        "resolved_subject_type": null,
        "resolved_subject_id": null,
        "resolved_by": null,
        "resolved_at": null,
        "created_by": "user_admin",
        "created_at": "2026-06-02T08:00:00Z",
        "updated_at": "2026-06-02T08:00:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_015"
}
```

产品负责人、研发负责人或管理员可登记待归属项：

```http
POST /api/attribution/pending-items
Content-Type: application/json

{
  "source_type": "user_feedback",
  "source_system": "feedback-api",
  "collector_run_id": "collector_run_001",
  "raw_subject_id": "feedback-ext-7788",
  "summary": "无法映射到产品的登录失败反馈",
  "raw_payload": {
    "channel": "support",
    "message": "login failed after release"
  },
  "suggested_product_id": null,
  "suggested_module_code": null,
  "confidence": 0.62
}
```

将队列项归属到已有上下文：

```http
POST /api/attribution/pending-items/pending_attr_001/resolve
Content-Type: application/json

{
  "resolution_action": "link_existing_context",
  "resolved_product_id": "product_001",
  "resolved_module_code": "login",
  "resolved_requirement_id": "req_001",
  "resolved_subject_type": "user_feedback",
  "resolved_subject_id": "feedback_001",
  "resolution_note": "已确认属于登录模块反馈"
}
```

忽略噪声数据：

```http
POST /api/attribution/pending-items/pending_attr_002/resolve
Content-Type: application/json

{
  "resolution_action": "ignore_as_noise",
  "resolution_note": "重复导入且无业务归属"
}
```

`source_type` 只允许 `gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；`status` 只允许 `pending`、`resolved`、`ignored`；`resolution_action` 只允许 `link_existing_context` 或 `ignore_as_noise`。`collector_run_id` 如传入必须存在；建议产品和归属产品必须为 active；建议模块和归属模块必须属于对应产品；归属需求必须属于归属产品。`link_existing_context` 必须提交 `resolved_product_id`，可选提交模块、需求或目标业务主体；`ignore_as_noise` 不允许提交任何归属上下文字段。队列项一旦 `resolved` 或 `ignored` 即为终态，重复处理返回 `409 PENDING_ATTRIBUTION_STATE_INVALID`。创建、归属和忽略分别写入 `pending_attribution.created`、`pending_attribution.resolved`、`pending_attribution.ignored` 审计事件。队列处理只记录人工归属结果，不自动生成 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议/需求等业务数据。
