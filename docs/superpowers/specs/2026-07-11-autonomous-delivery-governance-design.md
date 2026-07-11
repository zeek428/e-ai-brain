# 自治研发与生产交付治理设计

## 背景

当前平台已经打通需求、Bug、研发任务、Runner 隔离工作区、人工确认或自动提交、运维部署和审计主链路，但核心执行仍是单次任务模型：研发 Runner 返回成功后，策略为 `auto_commit` 时平台直接发出 `merge` 决策；部署窗口只校验起止顺序；回滚主要记录状态；部署单、运行记录和外部派发分多次持久化；Git/CI、可观测性和用户行为仍以人工登记或轮询为主。

本次迭代将主链路升级为可验证、可重复、可中断、可恢复的自治循环，并让研发合并和生产部署共用质量门禁、上下文清单、事件收件箱、事务 Outbox 和产品资源授权。

## 目标

- Runner 的成功回写不再等同于质量通过，自动合并必须经过平台独立质量门禁。
- 研发任务支持计划、执行、验证、反思和重试循环，达到目标、耗尽预算或触发安全边界后收敛。
- 每轮循环保存目标、上下文版本、变更摘要、测试证据、失败分析、Token/费用和停止原因。
- 部署前执行资源、制品、版本、窗口和门禁预检；部署后执行健康检查和冒烟验证。
- SSH、Docker、Jenkins 支持真实回滚；健康检查失败可按策略自动回滚或转人工接管。
- 支持全量、灰度、分批和蓝绿四种发布策略。
- 部署状态、运行记录、审计事件和外部派发使用同一数据库事务与 Outbox。
- 任务详情展示可检查、可复现的执行上下文清单和需求验收映射。
- Runner Target 和 Jenkins Connection 按产品与环境授权，产品成员不可枚举或使用未授权资源。
- GitHub/GitLab、CI、Jenkins、Prometheus/OpenTelemetry/Sentry 和用户行为通过幂等事件收件箱接入。
- 部署主列表使用 SQL 分页、排序、筛选和查询耗时观测，详情展示完整运行与回滚链路。
- 知识中心接入可插拔 OCR、版面分析、表格解析和多模态检索，并治理版本、过期和引用反馈。

## 非目标

- 不允许页面输入任意 Shell、SSH 主机、Docker 路径或回滚命令。
- 不在 PostgreSQL、API 响应、审计、上下文清单或日志中保存私钥、Token、密码和完整环境变量。
- 不让模型自主扩大产品范围、仓库范围、部署环境或执行资源授权。
- 不以 Runner 自报测试通过作为独立质量证据。
- 不在本期建设 Kubernetes 原生控制器；Kubernetes 可在后续作为新的受控部署 Target 类型接入。

## 总体架构

```text
需求 / Bug / 代码巡检
  -> AI Task
  -> AgentLoopRun
       plan -> execute -> verify -> reflect -> execute ...
       |                        |
       |                        +-> budget/safety stop -> human takeover
       +-> ContextManifest
       +-> Runner coding task in isolated worktree
       +-> QualityGateRun
             policy checks
             platform verifier task
             CI / scan / approval evidence
  -> manual review OR governed auto merge
  -> release readiness
  -> DeploymentRequest
       preflight QualityGateRun
       rollout waves
       deploy -> post-deploy health/smoke
       failure -> rollback OR human takeover
  -> audit / lifecycle / knowledge deposit

External systems
  -> signed webhook / collector
  -> ExternalEventInbox
  -> idempotent projector
  -> quality evidence / metrics / deployment status / user insight

Business transaction
  -> business rows + audit rows + ExecutionOutboxEvent
  -> dedicated worker claims event
  -> Runner / Jenkins / Git provider side effect
```

## 领域边界

### quality_gate

负责质量策略、门禁运行、检查项和证据聚合。它不直接修改代码，也不直接决定产品需求状态。

### agent_loop

负责自治循环状态、轮次、预算、停止原因和下一轮反馈。它通过 Runner 任务执行代码修改，通过 quality_gate 执行验证。

### execution_context

负责冻结执行时的需求、Bug、仓库、分支、知识、验收标准和权限摘要，并生成稳定 `context_version` 与内容哈希。

### deployment_orchestration

负责部署预检、发布波次、执行、健康验证、回滚和人工接管。外部副作用只能通过 Outbox 派发。

### integration_events

负责外部事件验签、幂等入库、处理租约、失败重试、死信和业务投影。

### knowledge_processing

负责解析 Provider、结构化资产、多模态向量、文档版本、过期策略和引用质量反馈。

## 数据模型

### quality_gate_policies

| 字段 | 说明 |
|---|---|
| `id` | 策略编号 |
| `name` | 中文名称 |
| `product_id` | 可空；空表示通用策略 |
| `task_type` | 可空；限制研发任务类型 |
| `phase` | `pre_merge/pre_deploy/post_deploy` |
| `risk_levels` | 适用风险等级数组 |
| `required_checks` | 服务端受控检查定义 |
| `protected_paths` | 命中后必须人工确认的路径模式 |
| `max_changed_files/max_changed_lines` | 自动合并阈值 |
| `required_ci_contexts` | 必须成功的外部 CI Context |
| `minimum_independent_evidence` | 独立证据最小数量，自动合并不得小于 1 |
| `manual_review_on_migration` | 数据库迁移是否强制人工确认 |
| `status/version` | 启停和乐观锁 |

`required_checks` 只允许服务端 Catalog 中的检查类型：`unit_test`、`type_check`、`lint`、`secret_scan`、`dependency_scan`、`static_analysis`、`ci_status`、`artifact_integrity`、`deployment_preflight`、`health_check`、`smoke_test`。命令由 Runner 本机受控 verifier 配置解析，页面不能提交命令文本。

### quality_gate_runs

| 字段 | 说明 |
|---|---|
| `id` | 门禁运行编号 |
| `policy_id/policy_snapshot` | 版本化策略快照 |
| `phase` | 门禁阶段 |
| `subject_type/subject_id` | `ai_task/agent_loop_iteration/deployment_run` |
| `product_id` | 权限和统计归属 |
| `status` | `pending/running/passed/failed/blocked/cancelled` |
| `risk_level` | 本次计算风险 |
| `independent_evidence_count` | 独立证据数量 |
| `started_at/finished_at` | 时间 |
| `summary/blocked_reasons` | 用户可读结论 |

### quality_gate_checks

每个检查保存 `check_type`、`status`、`source`、`required`、`independent`、`evidence_ref`、`command_catalog_code`、`exit_code`、`duration_ms`、`summary`、`details_json` 和时间。`details_json` 只能保存受限结构化摘要，不保存完整日志或凭据。

### agent_loop_runs

| 字段 | 说明 |
|---|---|
| `id/ai_task_id/product_id` | 主体 |
| `objective_json` | 目标与可验证验收标准 |
| `status` | `planning/executing/verifying/reflecting/waiting_review/succeeded/failed/stopped/safety_blocked` |
| `current_iteration/max_iterations` | 轮次预算 |
| `max_duration_seconds` | 总时长预算 |
| `token_budget/cost_budget` | 可空预算 |
| `token_used/cost_used` | 累计用量 |
| `context_manifest_id/context_version` | 冻结上下文 |
| `quality_gate_policy_id` | 合并前门禁 |
| `stop_reason` | 达标、预算、超时、安全、人工停止或不可恢复失败 |
| `version` | 乐观锁 |

### agent_loop_iterations

每轮保存 `iteration_number`、`coding_runner_task_id`、`verifier_runner_task_id`、`quality_gate_run_id`、`status`、`plan_json`、`change_summary`、`test_evidence`、`failure_analysis`、`verification_summary`、`context_version`、`token_usage`、`cost_amount` 和起止时间。同一循环的轮次号唯一。

### execution_context_manifests

保存 `subject_type/subject_id/product_id`、`version`、`content_hash`、`requirement_refs`、`bug_refs`、`repository_ref`、`branch`、`knowledge_refs`、`acceptance_criteria`、`permission_snapshot`、`retrieval_summary`、`truncation_summary` 和创建时间。知识引用只保存文档、Chunk、版本、摘要、召回原因和权限范围，不复制完整文档。

### execution_outbox_events

保存 `aggregate_type/aggregate_id/event_type/idempotency_key/payload_json/status/attempt_count/available_at/lease_owner/lease_until/last_error/created_at/processed_at`。业务事务只写 Outbox；外部 Worker 处理 `runner_task_dispatch`、`jenkins_trigger`、`git_writeback`、`deployment_verify` 和 `deployment_rollback`。

### execution_resource_grants

保存 `product_id/environment/resource_type/resource_id/target_code/status/version`。`resource_type` 首批为 `runner_target` 和 `jenkins_connection`。产品级管理者只能读取和绑定已授权资源；全局管理员负责资源授权。

### external_event_inbox

保存 `provider/event_type/delivery_id/signature_status/payload_hash/payload_json/status/attempt_count/lease_owner/lease_until/error_message/received_at/processed_at`。`provider + delivery_id` 唯一。原始 payload 按 Provider 白名单裁剪并脱敏后保存。

### deployment 扩展字段

- `deployment_schemes.rollout_strategy`：`all_at_once/canary/batch/blue_green`。
- `deployment_schemes.preflight_config/health_check_config/rollback_config`：均为非敏感受控配置。
- `deployment_requests.window_enforcement`：`strict/warn/disabled`，生产环境默认 `strict`。
- `deployment_runs.operation`：`deploy/verify/rollback`。
- `deployment_runs.wave_number/wave_total`：发布波次。
- `deployment_runs.health_status/rollback_run_id`：健康与回滚关联。
- 新增 `deployment_run_steps` 保存预检、部署、健康、冒烟和回滚步骤。

### knowledge 扩展

- `knowledge_document_versions` 保存对象资产、解析配置、内容哈希和生效状态。
- `knowledge_processing_profiles` 保存 OCR、版面、表格和多模态 Provider 引用，不保存凭据。
- `knowledge_assets` 增加 `page_number/bounding_boxes/content_hash/provider_metadata`。
- `knowledge_chunks` 增加 `document_version_id/modality/embedding_model`。
- `knowledge_citation_feedback` 保存引用是否有用、过期和不准确反馈。

## 研发自治状态机

```text
planning
  -> executing
  -> verifying
       passed -> waiting_review OR succeeded(auto merge allowed)
       failed -> reflecting
  -> reflecting
       retryable and budget remains -> executing(next iteration)
       non-retryable -> waiting_review
       budget exhausted -> stopped
       safety violation -> safety_blocked
```

不变量：

- 自动合并只能发生在 `QualityGateRun.status=passed` 且 `independent_evidence_count >= policy.minimum_independent_evidence`。
- `critical/high`、命中受保护路径、数据库迁移、权限/密钥/部署配置变更默认强制人工确认。
- 下一轮必须引用上一轮失败检查和证据，不允许无反馈重复执行同一指令。
- 任何轮次不得扩大初始上下文中的产品、仓库、分支和工作区边界。
- 预算计算失败时按保守策略转人工，不允许继续无限循环。

## 独立质量证据

证据来源分为：

- `runner_coding`：编码 Runner 自报，只能作为辅助证据。
- `platform_verifier`：平台创建的独立 verifier 任务，命令来自服务端 Catalog，可计为独立证据。
- `ci_webhook`：GitHub/GitLab CI 状态，可计为独立证据。
- `platform_scan`：平台静态扫描、凭据扫描、依赖扫描，可计为独立证据。
- `human_approval`：人工确认，可计为独立证据并覆盖需要人工确认的阻断项。

编码 Runner 的 `status=succeeded` 只能推进到 `verifying`，不能直接触发 merge。

## 部署状态机

```text
pending_ops
  -> preflight
       blocked -> pending_ops
       passed -> deploying
  -> deploying(wave 1..N)
  -> verifying
       healthy -> next wave OR succeeded
       unhealthy -> rolling_back OR waiting_takeover
  -> rolling_back
       rollback succeeded -> rolled_back
       rollback failed -> failed + critical incident + human takeover
```

生产部署启动时必须满足：当前时间在严格窗口内；方案和资源授权仍有效；制品版本、Commit SHA 和制品哈希完整；发布评估与阻塞 Bug 门禁通过；Runner/Jenkins 就绪；回滚配置完整；前置 QualityGateRun 通过。

灰度和分批按 `wave_config` 创建多条运行记录；每波完成健康检查后才允许下一波。蓝绿策略要求 `active_slot/target_slot/switch_action/rollback_action` 均来自受控 Target 配置。

## 真实回滚

- SSH Target 本机配置增加固定 `rollback_command`，只接收结构化回滚上下文标准输入。
- Docker Target 增加固定 `rollback_compose_files` 或 `rollback_artifact_resolver`，平台只传目标制品版本。
- Jenkins 方案配置独立 `rollback_job_name`，参数仍使用白名单映射。
- 回滚创建新的 `deployment_run(operation=rollback)`，不得把原部署运行直接改写为已回滚。
- 自动回滚需要策略明确允许，且风险等级不高于策略阈值；否则进入人工接管。

## 事务与 Worker

Repository 增加组合写方法，在同一事务内保存部署单、部署运行、步骤、审计和 Outbox。API 不直接调用 Jenkins 或等待 Runner 派发。独立 Worker 使用 `FOR UPDATE SKIP LOCKED` 认领 Outbox 和 Inbox，按指数退避重试；超过上限进入死信并生成系统告警。

Docker Compose 增加 `worker` 服务。API 内嵌线程仅保留测试兼容，生产配置必须关闭。

## 外部事件与回写

- GitHub/GitLab Webhook：PR/MR 更新、CI Check、Push 和合并事件。
- Jenkins Webhook：Queue、Build、成功、失败和取消；轮询只做补偿。
- Prometheus/OpenTelemetry/Sentry：通过 Collector API 写入指标和异常事件。
- 用户行为：批量事件入口，服务端聚合后写入 `user_usage_metrics`。
- Git 回写：质量门禁结论、Review 评论、request changes 和合并动作通过 Outbox 执行；连接权限和产品仓库归属必须同时满足。

所有入口使用 Provider 签名或专用 Token、Delivery ID 幂等、产品归属解析、字段白名单、速率限制和审计。

## 页面设计

### 研发执行器策略

增加自治模式、最大轮次、总时长、Token/费用预算、质量门禁策略和风险自动合并阈值。命中预览同时展示最终门禁和人工确认原因。

### 研发任务详情

增加“自治循环”“质量门禁”“执行上下文”页签。自治循环按轮次显示计划、修改、验证、失败分析和预算；质量门禁按检查展示来源和证据；上下文清单逐项展示需求、Bug、仓库、知识、验收标准、版本和截断。

### 运维部署

主列表使用服务端分页。详情抽屉展示部署单、方案快照、前置门禁、审批、波次、运行、日志、健康检查、回滚和审计。启动前显示预检结果；窗口外不展示可执行主按钮。部署方案表单增加发布策略、健康检查和回滚配置，但仅选择受控 Catalog 与资源。

### 系统集成

插件管理增加 Webhook 健康、最近 Delivery、失败重试和回写权限。系统健康增加 Outbox/Inbox 堆积、死信、Agent 循环成功率和质量门禁通过率。

### 知识中心

文档详情展示版本、解析 Profile、OCR/版面/表格状态、多模态资产、过期状态和引用反馈。失败步骤可以独立重试。

## 权限

- `quality_gate.read/manage/override`
- `agent_loop.read/manage/stop`
- `execution_context.read`
- `execution_resource.manage`
- `external_event.read/retry`
- `deployment.rollback`
- `knowledge.processing_profile.manage`
- `knowledge.citation_feedback.manage`

所有读取继续执行产品 Scope；只有全局管理员可以把全局执行资源授权给产品。质量门禁覆盖和自动回滚均属于高风险操作，必须写审计理由。

## 可观测性指标

- Agent 循环成功率、平均轮次、预算耗尽率、安全阻断率。
- 质量门禁通过率、按检查失败分布、独立证据覆盖率、误放行复盘数。
- Outbox/Inbox 待处理、重试、死信和处理延迟。
- 部署成功率、平均恢复时间、回滚成功率、窗口违规次数、健康检查失败率。
- 上下文引用命中、截断、过期和用户反馈指标。

## 迁移与兼容

- 现有执行器策略默认 `autonomy_mode=single_pass`、`code_change_review_mode=manual_review`。
- 现有 `auto_commit` 策略迁移后必须绑定默认质量门禁；无法获得独立证据时自动降级为人工确认。
- 现有部署方案默认 `rollout_strategy=all_at_once`、`window_enforcement=warn`；生产环境新方案默认 `strict`。
- 现有部署记录生成兼容步骤投影，但不伪造历史健康检查或回滚执行证据。
- 外部采集手工登记接口继续保留，新增事件接入不改变已有数据事实源。

## 验收标准

- 编码 Runner 返回成功但独立门禁缺失或失败时，不会产生 merge 决策。
- 自治任务可在测试失败后创建下一轮，携带失败证据，并在达标或预算耗尽后收敛。
- 高风险、迁移和受保护路径变更始终进入人工确认。
- API 或 Worker 重启不会丢失部署派发；重复消费不会重复触发外部副作用。
- 严格窗口外不能启动生产部署。
- SSH、Docker、Jenkins 均可执行真实回滚测试替身，并保存独立回滚运行。
- 健康检查失败按策略自动回滚或进入人工接管，不会错误显示成功。
- 产品用户无法查看或绑定未授权 Runner Target/Jenkins Connection。
- 任务详情可完整解释本次 AI 收到什么上下文、遵循什么验收标准、每轮为何继续或停止。
- Git/CI/Jenkins Webhook 重放不会重复生成质量证据、发布记录或状态迁移。
- 部署列表在 PostgreSQL 层分页、排序和筛选，并返回查询观测元数据。
- OCR、版面、表格和多模态 Provider 可通过测试 Provider 完成端到端解析、索引和检索。
- 后端、前端、迁移、Runner、Worker、帮助中心和真实浏览器验收全部通过。
