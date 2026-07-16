# 需求交付与研发任务 API

> API 分册。覆盖需求、AI 任务、人工确认、回写与导出。主入口见 [../api.md](../api.md)。

## v2.0 需求驱动研发协同契约

产品需求是研发协同唯一入口。调用顺序为：创建需求 → 正式评估 → 规划版本归组 → 创建协作运行 → 执行工作项/审核/返工 → 质量门禁与远程 Git 提交 → 按策略停在 `ready_for_release` 或经人工确认进入部署。默认不部署时，产品版本保持 `ready_for_release`，协作运行进入 `completed`，并记录 `completion_reason=ready_for_release`。

### 正式需求评估与版本归组

```http
POST /api/requirements/{requirement_id}/assessments
GET /api/requirements/{requirement_id}/assessments/latest
POST /api/requirement-assessments/{assessment_id}/opinions
POST /api/requirement-assessments/{assessment_id}/answers
POST /api/requirement-assessments/{assessment_id}/decisions
```

创建评估时服务端按业务大脑、产品和稳定需求字段解析唯一 active 统一研发执行策略，普通请求不能传入 `strategy_id` 覆盖匹配。只有同时具备 `delivery.rd_executor_policies.manage` 和 `delivery.requirement_assessments.decide` 的人工覆盖请求可以提交候选策略，并仍须通过匹配、单调收紧、风险和审计校验。响应包含 `assessment_id/status/requirement_revision/strategy_snapshot_id/completeness/risk/effort/dependencies/acceptance_criteria/version_candidates/recommended_action/deterministic_checks`。LLM 提供结构化建议，服务端校验 Schema、风险下限、权限和版本兼容性。状态统一为 `draft | evaluating | waiting_human | needs_info | rework_required | accepted | deferred | rejected | failed | cancelled`。

`opinions` 只允许已分配的真人评估者或受控 AI 评估执行单元按岗位输出契约提交；`answers` 由需求负责人补充事实并创建新的需求/评估版本；`decisions` 请求体包含 `decision=accept|reject|request_more_info|request_rework|defer`、`comment` 和 `version` 乐观锁。`accepted` 后需求原子进入 `approved`，服务端再按 `iteration_config` 选择兼容 `planning` 版本。唯一合格候选可自动归组；候选并列、高风险新建版本或人工覆盖时创建 `decision_request`，需求保持 `approved`。组版成功后写入 `selected_version_id/version_created/grouping_reason` 并进入 `planned`。非 accepted 或未完成组版状态不得创建协作运行。

同一 `requirement_revision + strategy_snapshot_id` 的进行中或成功评估幂等复用；需求发生实质修改后必须创建新评估，旧评估只作历史证据。

### 统一研发执行策略

```http
GET  /api/delivery/rd-task-executor-policies
POST /api/delivery/rd-task-executor-policies
GET  /api/delivery/rd-task-executor-policies/{policy_id}
PATCH /api/delivery/rd-task-executor-policies/{policy_id}
DELETE /api/delivery/rd-task-executor-policies/{policy_id}
POST /api/delivery/rd-task-executor-policies/{policy_id}/validate
```

原入口原位升级，不接受旧版单任务匹配写契约，也不提供任何旧/新双模式字段。策略主体必须包含：

```json
{
  "name": "默认产品研发交付策略",
  "brain_app_id": "rd_brain",
  "product_id": "product_001",
  "status": "active",
  "matching_config": {},
  "assessment_config": {},
  "iteration_config": {},
  "team_config": {},
  "autonomy_config": {},
  "quality_gate_config": {},
  "git_config": {},
  "deployment_config": {"mode": "disabled"},
  "delivery_target": "ready_for_release",
  "role_bindings": [
    {"role_code": "developer", "actor_mode": "ai", "actor_selector": {"ai_employee_ids": ["ai_employee_dev_01"]}, "executor_profile_id": "executor_codex_01"},
    {"role_code": "tester", "actor_mode": "ai", "actor_selector": {"ai_employee_ids": ["ai_employee_test_01"]}, "executor_profile_id": "executor_test_01"}
  ]
}
```

`delivery_target` 允许 `ready_for_release | deployed`，默认 `ready_for_release`；`deployed` 仍须通过现有发布评估、资源预检和人工确认。保存及激活前整体校验岗位、执行器、预算、门禁、Git 与风险配置。运行时冻结策略快照；策略缺失或无效返回 `RD_EXECUTION_POLICY_REQUIRED/INVALID`，不得走策略外执行路径。

评估后策略复核最多自动单调收紧两轮：只允许降低自动化、收紧风险/权限/工具/仓库/预算、增加门禁或必需岗位、或把 `deployed` 改为 `ready_for_release`。新增必需评估岗位必须补齐兼容意见；不可比较或可能扩大边界返回 `RD_POLICY_HUMAN_DECISION_REQUIRED`，超过两轮返回 `RD_POLICY_RESOLUTION_LIMIT`。

### 研发岗位、执行器与协作运行

```http
GET/POST/PATCH /api/delivery/rd-roles
GET/POST/PATCH /api/delivery/rd-ai-employees
GET/POST/PATCH /api/delivery/rd-executor-profiles
POST           /api/product-versions/{version_id}/collaboration-runs
GET            /api/requirements/{requirement_id}/collaboration-run
GET            /api/delivery/rd-collaboration-runs/{run_id}
GET            /api/delivery/rd-collaboration-runs/{run_id}/work-items
POST           /api/delivery/rd-work-items/{work_item_id}/claim
POST           /api/delivery/rd-work-items/{work_item_id}/submit
POST           /api/delivery/rd-work-items/{work_item_id}/review
POST           /api/delivery/decision-requests/{decision_request_id}/decide
```

`rd-roles` 管理独立于系统 RBAC 的动态研发岗位；`rd-ai-employees` 管理独立于执行器的稳定 AI 数字员工身份、能力标签和人格版本；`rd-executor-profiles` 管理模型/Runner 运行能力。协作席位通过 `subject_type=ai_employee|human_user` 绑定 AI 数字员工或真人账号，AI 席位另行冻结 `executor_profile_id`。P0 真人选择只接受显式 `user_ids`，AI 选择只接受显式 `ai_employee_ids`，且调用时仍校验状态、系统权限或服务身份、产品范围、工作项席位和策略绑定。产品版本是协作聚合根：同一版本最多一个非终态运行。创建运行要求版本为 `planning`、至少包含一条 `planned` 需求、纳入需求最新评估均为 accepted，服务端锁定版本并冻结范围、策略、需求、岗位、员工和执行器快照，然后推进版本为 `active`。需求 GET 端点只定位所属版本运行，不创建第二个运行。

权限点分别为 `delivery.rd_roles.manage`、`delivery.rd_ai_employees.manage`、`delivery.rd_executor_profiles.manage`、`delivery.requirement_assessments.read/decide`、`delivery.rd_collaboration.read/plan/work` 和 `delivery.decision_requests.decide`；策略继续使用 `delivery.rd_executor_policies.manage`，部署继续使用现有部署权限。岗位、员工档案或席位不会自动授予这些权限。

工作项包含 `owner_seat_id/dependencies/input_contract/output_contract/acceptance_criteria/risk_level/status/resume_state/suspended_attempt_id/ai_task_id/reviewer_seat_id/idempotency_key`。依赖满足后才能进入 `ready`，无依赖项可并行；审核或质量门禁失败保留原 attempt，同范围返工进入 `rework_required` 并在下一次领取时创建新 attempt，范围/依赖/负责人变化则创建新计划版本和替代工作项。`blocked/awaiting_human` 保存平台冻结的恢复目标和解除条件；问题解除或决策完成后只能回到校验后的 `ready/running/rework_required/cancelled`。高风险、超权限、冲突、预算超限、门禁失败或部署边界创建 `decision_requests` 并暂停受影响分支。详情响应聚合 DAG、租约、AI 任务/Runner、审核、返工、门禁、Git、预算和角色反馈。

集成工作项通过 Outbox 推送版本开发分支或创建/更新 MR/PR，并保存 repository/provider、工作分支、版本开发分支、目标分支、local/remote commit SHA、MR/PR ID 和状态、Outbox ID、执行身份、时间、对账状态与质量证据。`ready_for_release` 完成判定只验证每个必需仓库已有对账成功的远程证据，不在完成接口内临时执行 push。默认策略下产品版本进入 `ready_for_release`，协作运行随后进入 `completed` 并返回 `completion_reason=ready_for_release`；版本不进入部署或发布状态。

### 一次性升级控制

```http
GET  /api/system/rd-collaboration-upgrade/preflight
POST /api/system/rd-collaboration-upgrade/maintenance-fence
POST /api/system/rd-collaboration-upgrade/cutover
```

仅系统管理员可调用。围栏请求包含 `enabled/reason/version/expected_schema_version/health_marker`。启用后研发 approve/reject/direct-generate、AI 任务 start/retry、策略/协作写入和 Runner 新领取返回 `423 RD_UPGRADE_MAINTENANCE`，定时作业运行不受影响。cutover 只有在 preflight 无阻断、备份确认、Schema 109 已应用且围栏启用时执行策略转换、旧 draft 取消和 Schema v2 激活；新应用健康标记成功后才允许执行清理迁移 110。

解除围栏必须同时满足 Schema v2 已激活、迁移 110 已成功、v2 API 与协同 Worker 图版本一致、健康标记有效、v2 评估/协作写入冒烟检查通过。解除后新写路径恢复，旧 approve/generate/batch-delivery-advance/AI-task-create/start 写路径仍返回迁移错误。预检、健康、清理、Worker 或冒烟检查任一步失败都保持围栏并允许幂等重试。

### 需求管理

新增需求：

```http
POST /api/requirements
```

请求体：

```json
{
  "title": "支持企业知识库导入 Markdown",
  "priority": "P1",
  "source": "business_department",
  "input": {
    "background": "团队知识散落在 Markdown 文档中",
    "business_goal": "导入后可被研发大脑检索引用",
    "current_problem": "资料分散，需求评审时难以复用历史结论。",
    "product_id": "product_001",
    "version_id": "version_001",
    "module_codes": ["knowledge"],
    "expected_release_date": "2026-06-30"
  }
}
```

规则：

- 新增后状态为 `submitted`。
- 需求支持 `draft | submitted | approved | planned | designing | ready_for_dev | developing | code_reviewing | testing | ready_for_release | deploying | released | accepted | rejected | deferred | cancelled | closed` 生命周期。
- `source` 表示需求来源，允许 `business_department | product_planning | user_feedback | internal_research | other`，默认 `business_department`；列表支持按 `source` 筛选和排序。
- `input.product_id` 必填且必须指向启用产品；`input.version_id` 可选，填写时只能指向同产品 `planning` 版本并作为评估/组版候选，不能绕过评估直接排期。
- v2.0 不再通过独立 approve/reject 操作先改变需求状态；正式评估 accepted 后需求进入 `approved`，评估 deferred/rejected 分别推进需求为 `deferred/rejected`。
- 评估通过后系统优先归入兼容 `planning` 版本，无合适版本才创建新规划版本并进入 `planned`。旧 approve/reject 调用在没有相应评估决策时返回 `REQUIREMENT_ASSESSMENT_REQUIRED`。
- 批量分配负责人调用 `POST /api/requirements/batch-assign-owner`；批量排期只用于有权限人员调整自动组版结果且目标必须是 `planning`。`batch-advance-status` 只保留在既无活动协作运行、也不存在非终态工作项时批量取消/关闭，任何交付状态目标返回 `RD_COLLABORATION_REQUIRED`；`batch-generate-tasks` 固定返回同一错误。
- v2.0 只有最新评估为 `accepted` 且已归入 `planning` 版本的需求可以创建协作运行；底层 AI 任务由协作工作项生成，不允许绕过评估直接批量生成研发任务。
- 生成产品详细设计任务后需求状态进入 `designing`，后续 AI 任务创建和人工确认会继续推进到 `ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released` 或 `accepted`。需求仍保留原始输入和审批结论。
- 关闭需求后不得再生成新 AI 任务。
- 删除需求仅允许未生成 AI 任务的记录；已有 `task_ids` 时返回 `409 RESOURCE_IN_USE`，并在错误详情中返回 `related_counts.ai_tasks` 与 `related_total`，供前端展示占用数量和处理建议。

旧版直接生成任务接口在 v2.0 升级后停用；以下请求体仅用于识别旧客户端并返回 `RD_COLLABORATION_REQUIRED`，调用方应先完成评估和组版，再使用 `POST /api/product-versions/{version_id}/collaboration-runs`：

```json
{
  "task_type": "product_detail_design"
}
```

规则：研发协作编排服务根据工作项类型创建 `product_detail_design`、`technical_solution`、`code_review` 等底层 AI 任务；人和外部客户端不得直接选择 `task_type` 绕过正式评估、版本归组、岗位和策略快照。

其他旧入口同步适配：Bug `promote-ai-task`、代码巡检整改结果动作和 AI 助手 `create_rd_task` 只幂等创建或关联正式需求并返回 `requirement_id/assessment_url`，不返回可启动 `ai_task_id`。定时作业的定义、调度、锁、重试、AI角色/Skill 快照和运行历史不变；代码巡检结果动作的写入目标改为需求交付适配，不由定时作业引擎创建协作运行。

批量排期请求：

```http
POST /api/requirements/batch-schedule
```

请求体：

```json
{
  "product_id": "product_001",
  "version_id": "version_202606",
  "requirement_ids": ["requirement_001", "requirement_002"],
  "reason": "归集到 2026-06 迭代"
}
```

规则：

- 仅 `product_owner`、`rd_owner` 或 `admin` 可调用。
- 该接口仅用于有权限人员调整自动归组结果；`product_id` 必须为启用产品，`version_id` 必须属于该产品且状态为 `planning`，并记录调整前后版本、原因和操作者。不得把新需求直接排入已开发或测试版本。
- `approved` 需求池需求和 `planned` 已排期需求只有在目标版本重新通过策略、容量、仓库范围、交付终点、硬依赖和互斥约束后才能更新为目标 `version_id` 并保持/进入 `planned`；人工操作不能绕过硬条件。
- 缺失、重复、跨产品、硬条件不兼容或已进入设计/开发/评审/测试/发布/验收等交付阶段的需求不更新，进入 `skipped` 明细；候选争议或高风险覆盖创建 `decision_request` 并保持原状态；目标产品或目标版本非法时整个请求返回错误。
- 成功请求以追加/upsert 方式记录一条 `requirement.batch_scheduled` 审计事件，subject 为 `requirement_batch`；每条实际更新的需求另记录 `requirement.updated`，payload 包含 `batch_id`、来源版本、目标版本和 reason；不得通过覆盖式审计快照保存删除历史批次审计。

响应体：

```json
{
  "data": {
    "batch_id": "requirement_batch_001",
    "product_id": "product_001",
    "version_id": "version_202606",
    "updated_count": 2,
    "skipped_count": 1,
    "updated": [
      {
        "id": "requirement_001",
        "status": "planned",
        "version_id": "version_202606"
      }
    ],
    "skipped": [
      {
        "id": "requirement_003",
        "code": "REQUIREMENT_STATE_INVALID",
        "message": "Only requirement pool or planned requirements can be scheduled"
      }
    ]
  },
  "trace_id": "trace_xxx"
}
```

批量分配负责人请求：

```http
POST /api/requirements/batch-assign-owner
```

请求体：

```json
{
  "assignee": "rd_owner@example.com",
  "requirement_ids": ["requirement_001", "requirement_002"],
  "reason": "调整研发负责人"
}
```

规则：

- 仅 `product_owner`、`rd_owner` 或 `admin` 可调用。
- `assignee` 必须为非空字符串，表示需求负责人账号、姓名或组织内约定标识；新增需求默认使用创建人作为 `assignee`。
- 非 `closed`、非 `cancelled` 需求可批量更新负责人，需求状态不变化。
- 缺失、重复、已关闭或已取消需求不更新，进入 `skipped` 明细；合法项继续处理，不因部分跳过回滚整个批次。
- 成功请求记录一条 `requirement.batch_owner_assigned` 审计事件，subject 为 `requirement_owner_batch`；每条实际更新的需求另记录 `requirement.updated`，payload 包含 `batch_id`、`from_assignee`、`assignee` 和 reason。

响应体：

```json
{
  "data": {
    "batch_id": "requirement_owner_batch_001",
    "assignee": "rd_owner@example.com",
    "reason": "调整研发负责人",
    "updated_count": 2,
    "skipped_count": 1,
    "updated": [
      {
        "id": "requirement_001",
        "status": "planned",
        "assignee": "rd_owner@example.com"
      }
    ],
    "skipped": [
      {
        "id": "requirement_003",
        "code": "REQUIREMENT_STATE_INVALID",
        "message": "Closed or cancelled requirements cannot be assigned"
      }
    ]
  },
  "trace_id": "trace_xxx"
}
```

批量状态管理兼容请求：

```http
POST /api/requirements/batch-advance-status
```

请求体：

```json
{
  "target_status": "closed",
  "requirement_ids": ["requirement_001", "requirement_002"],
  "reason": "需求已撤销，批量关闭"
}
```

规则：

- 仅 `product_owner`、`rd_owner` 或 `admin` 可调用，且 `reason` 必填。
- v2.0 只允许 `target_status=cancelled|closed` 的管理动作；目标为 `planned/designing/ready_for_dev/developing/code_reviewing/testing/ready_for_release/deploying/released/accepted/deferred` 时整个请求返回 `409 RD_COLLABORATION_REQUIRED`，不更新任何需求。
- 存在活动协作运行、非终态工作项或不可取消的外部副作用时，相关需求进入 `skipped` 并返回明确阻断引用；关闭前必须满足无未完成工作项和无待决 decision request。
- 合法取消/关闭不修改产品、迭代版本、负责人或历史任务引用；重复、缺失或已终态需求进入 `skipped`，其他合法项继续处理。
- 成功请求记录 `requirement.batch_cancelled` 或 `requirement.batch_closed` 审计事件；每条实际更新的需求另记录 `requirement.updated`，payload 包含 `batch_id`、`from_status`、`to_status` 和 reason。

响应体：

```json
{
  "data": {
    "batch_id": "requirement_status_batch_001",
    "target_status": "closed",
    "reason": "需求已撤销，批量关闭",
    "updated_count": 2,
    "skipped_count": 1,
    "updated": [
      {
        "id": "requirement_001",
        "status": "closed"
      }
    ],
    "skipped": [
      {
        "id": "requirement_003",
        "code": "REQUIREMENT_STATE_INVALID",
        "message": "Requirement has active collaboration work and cannot be closed"
      }
    ]
  },
  "trace_id": "trace_xxx"
}
```

旧批量生成任务请求：

```http
POST /api/requirements/batch-generate-tasks
```

请求体：

```json
{
  "product_id": "product_001",
  "requirement_ids": ["requirement_001", "requirement_002"],
  "reason": "批量进入产品详细设计"
}
```

规则：v2.0 固定返回 `409 RD_COLLABORATION_REQUIRED`，不创建任务、不推进需求状态；响应给出需要先完成评估、组版并启动版本协作的处理入口。历史成功响应仅作为旧审计数据保留，不再属于写契约。

兼容错误响应：

```json
{
  "data": {
    "code": "RD_COLLABORATION_REQUIRED",
    "message": "Complete assessment and start the product-version collaboration run",
    "next_action": "open_requirement_assessment"
  },
  "trace_id": "trace_xxx"
}
```

### AI 任务

支持的 `task_type`：

| task_type | 说明 |
|-----------|------|
| `product_detail_design` | 产品详细设计。 |
| `technical_solution` | 技术方案设计。 |
| `development_planning` | 代码开发辅助。 |
| `code_review` | GitLab MR / GitHub PR 代码 Review。 |
| `automated_testing` | 自动化测试。 |
| `release_readiness` | 发布上线评估。 |
| `post_release_analysis` | 上线后分析。 |
| `bug_fix` | 历史 Bug 修复任务类型，只读兼容；v2.0 Bug 先创建或关联正式需求，实际修复 AI 任务由协作工作项创建。 |

兼容创建任务端点（v2.0 外部禁用）：

```http
POST /api/ai-tasks
```

历史请求格式仅用于旧审计和迁移诊断；外部调用不会执行：

```json
{
  "task_type": "technical_solution",
  "title": "技术方案：支持企业知识库导入 Markdown",
  "requirement_id": "requirement_001",
  "input": {
    "product_detail_design_task_id": "task_design_001"
  }
}
```

`code_review` 任务请求体示例：

```json
{
  "task_type": "code_review",
  "title": "Review MR !42: 知识导入",
  "requirement_id": "requirement_001",
  "input": {
    "gitlab_mr_snapshot_id": "mr_snapshot_001"
  }
}
```

`development_planning` 和 `automated_testing` 任务请求体示例：

```json
{
  "task_type": "development_planning",
  "title": "开发计划：知识导入",
  "requirement_id": "requirement_001",
  "input": {
    "technical_solution_task_id": "task_tech_001"
  }
}
```

`release_readiness` 任务请求体示例：

```json
{
  "task_type": "release_readiness",
  "title": "发布评估：知识导入",
  "requirement_id": "requirement_001",
  "input": {
    "technical_solution_task_id": "task_tech_001"
  }
}
```

`post_release_analysis` 任务请求体示例：

```json
{
  "task_type": "post_release_analysis",
  "title": "上线后分析：知识导入",
  "requirement_id": "requirement_001",
  "input": {
    "release_readiness_task_id": "task_release_001"
  }
}
```

规则：

- 真人、前端、插件和其他外部客户端调用固定返回 `409 RD_COLLABORATION_REQUIRED`，不创建任务、不推进需求状态。
- 版本协作编排器不调用该 HTTP 路由，而调用内部 `create_ai_task_for_work_item(collaboration_run_id, work_item_id)` 领域服务。内部命令强制关联协作运行和工作项，并从冻结工作项和策略快照解析需求、产品、版本、岗位、AI 数字员工、执行器、Git 资源和上下文。
- 内部创建要求需求处于协作交付状态、工作项可派发且所有依赖满足；成功后追加任务到 `task_ids`。需求阶段只能由工作项、审核和门禁投影服务推进，不能由调用方提交 `task_type` 直接改变。
- `task_type = technical_solution` 时，`input.product_detail_design_task_id` 必须指向同一需求、同一产品版本下已完成的 `product_detail_design` 任务。
- `task_type = development_planning`、`automated_testing` 或 `release_readiness` 时，`input.technical_solution_task_id` 必须指向同一需求、同一产品版本下已完成的 `technical_solution` 任务；否则返回 `TECHNICAL_SOLUTION_NOT_CONFIRMED` 或上下文不匹配错误。`release_readiness` 创建时会把源技术方案输出、同产品/版本/需求 Bug、Jenkins 发布记录、线上日志指标和 GitLab 每日代码指标写入 `input_json` 快照；无记录时保存真实空数组。
- `task_type = post_release_analysis` 时，`input.release_readiness_task_id` 必须指向同一需求、同一产品版本下已完成的 `release_readiness` 任务；否则返回 `RELEASE_READINESS_NOT_CONFIRMED` 或上下文不匹配错误。创建时会把源发布评估输出、Jenkins 发布记录、线上日志指标和同产品/版本/需求 Bug 写入 `input_json` 快照；无记录时保存真实空数组。
- `task_type = code_review` 时，`input.gitlab_mr_snapshot_id` 必填；该字段是兼容名，可引用 GitLab MR 或 GitHub PR 快照。快照必须先通过 MR/PR 预览与快照接口生成，并且当前用户必须对快照所属产品 Git 资源具备 Review 权限。
- 后端创建 code_review 任务时只引用已有不可变快照，不在任务创建接口中重复拉取 MR/PR diff。
- code_review 任务只归档 AI Brain 内部 Review 报告，不向 GitLab/GitHub 回写评论、审批状态、request changes、合并状态或分支变更。
- `automated_testing` 任务进入人工确认前不会登记 Bug；人工确认 `approve` 或 `edit-approve` 后，输出中的 `bug_suggestions` 才会生成 `source=ai_auto_test` 的 Bug 记录。
- `post_release_analysis` 任务进入人工确认前不会登记 Bug；人工确认 `approve` 或 `edit-approve` 后，输出中的 `bug_suggestions` 才会生成 `source=ai_post_release` 的 Bug 记录，并记录 `bug.created` 与 `post_release_analysis.bugs_created` 审计事件。
- 前端、真人和外部客户端不调用该兼容端点；产品详细设计和后续任务均由版本协作工作项通过内部领域服务创建。

外部兼容响应：

```json
{
  "data": {
    "code": "RD_COLLABORATION_REQUIRED",
    "message": "Start work through the product-version collaboration run",
    "next_action": "open_rd_collaboration"
  },
  "trace_id": "trace_003"
}
```

任务列表：

```http
GET /api/ai-tasks?status=waiting_review&task_type=code_review&product_id=product_001&created_from=2026-06-01T00:00:00Z&created_to=2026-06-02T23:59:59Z&page=1&page_size=20
```

可按 `status`、`task_type`、`product_id`、`requirement_id`、`created_from`、`created_to`、`keyword` 和 `created_by` 查询；创建时间范围基于任务 `created_at`，缺少创建时间的历史任务不会命中时间段筛选。`page` 从 1 开始，`page_size` 默认 10、最大 100。
列表只返回当前用户有权读取的任务摘要，包括 `product_name`、`created_at` 和 `updated_at`，不返回 `requirement_snapshot`、`product_context`、`input_json` 或 `output_json` 等任务内部上下文。响应 `data` 包含 `items`、`total`、`page` 和 `page_size`，任务管理页必须将筛选和分页条件传到后端，不再先拉全量任务后本地过滤。

兼容启动任务端点（v2.0 外部禁用）：

```http
POST /api/ai-tasks/{task_id}/start
```

历史请求格式仅用于迁移诊断：

```json
{
  "collaboration_run_id": "rd_run_001",
  "work_item_id": "rd_work_item_001",
  "reason": "协作编排服务派发就绪工作项"
}
```

真人、前端、插件和其他外部客户端调用固定返回 `409 RD_COLLABORATION_REQUIRED`。版本协作编排器调用内部 `dispatch_ai_task_for_work_item(collaboration_run_id, work_item_id)` 领域服务；任务必须绑定协作运行和工作项，并使用运行冻结的策略、岗位席位、AI 数字员工与执行器快照。内部服务校验工作项为 `ready`、依赖已满足、席位和执行器可用、预算未耗尽后，创建关联 `ai_executor_tasks(ai_task_id=<task_id>)` 或策略声明的模型执行，任务进入 `running/current_step=waiting_ai_executor`。上下文清单包含需求评估、需求/版本、工作项输入输出契约、仓库/分支、知识版本、验收标准、权限和截断摘要，不包含 Git、插件或模型密钥。

编码 Runner 成功只会推进到 `quality_gate_running`，平台另建 verifier Runner 任务执行服务端受控的测试、类型检查、lint、凭据/依赖/静态扫描、CI 和变更范围检查。`code_change_review_mode=manual_review` 在门禁结束后进入 `waiting_review`；`auto_commit` 也只有在门禁通过、至少一份独立证据、风险不高于阈值且未命中迁移/受保护路径时才自动创建已通过 Review 并请求 Runner `merge`。其余情况降级为人工确认。`autonomy_mode=autonomous_loop` 会在门禁失败且仍可重试、轮次/时长/Token/费用预算充足时，携带失败证据创建下一轮；预算耗尽、安全阻断或人工接管停止继续派发。失败、取消、超时、拒绝或不可恢复门禁失败会按隔离工作区语义 `discard`。

策略、岗位绑定、执行器档案、权限或协作上下文缺失时返回 `RD_EXECUTION_POLICY_REQUIRED`、`RD_ROLE_ASSIGNMENT_REQUIRED`、`RD_EXECUTOR_UNAVAILABLE` 或 `RD_WORK_ITEM_NOT_READY`，并保持工作项阻断；不再回退到策略外模型网关、code-review executor 或确定性本地输出。测试环境需要确定性执行时必须通过测试专用依赖注入替换执行器，不对生产 API 暴露绕过统一策略的 `execution_mode`。
外部兼容响应与创建端点一致，返回 `RD_COLLABORATION_REQUIRED`。任务类型对应的真人职责只决定工作项审核或决策权限，不授予直接启动 AI 任务的权限。以下是内部领域服务在任务进入待审核时写入的业务结果示例，不是该 HTTP 兼容端点的成功响应：

```json
{
  "data": {
    "id": "task_001",
    "status": "waiting_review",
    "review_id": "review_001"
  },
  "trace_id": "trace_004"
}
```

内部领域服务按统一研发执行策略成功派发时，典型业务结果为：

```json
{
  "data": {
    "id": "task_001",
    "status": "running",
    "current_step": "waiting_ai_executor",
    "executor_policy_id": "rd_executor_policy_001",
    "executor_task_id": "ai_executor_task_001",
    "runner_id": "ai_executor_runner_001"
  },
  "trace_id": "trace_004"
}
```

如果模型网关或 code_review 执行器失败，响应为：

```json
{
  "data": {
    "id": "task_001",
    "status": "failed",
    "error_code": "MODEL_GATEWAY_FAILED | CODE_REVIEW_EXECUTOR_FAILED"
  },
  "trace_id": "trace_005"
}
```

任务详情：

```http
GET /api/ai-tasks/{task_id}
```

响应包含 `task_type`、`input`、`output`、`output_summary`、`current_step`、`pending_review`、`reviews`、`mock_issues`、`knowledge_deposits`、`execution_context_manifest`、`agent_loop` 和 `quality_gate`。`output_summary` 是用于任务详情和待确认界面的可读摘要；当 Runner 回写结果只包含 `output_preview` 时，服务端会优先提取 Codex 最终报告段，完整原始执行结果仍保留在 `output`。

- `execution_context_manifest` 返回版本、内容哈希、需求/Bug 引用、仓库/分支、知识文档/chunk/版本与召回原因、验收标准、权限快照、检索与截断摘要。
- `agent_loop` 返回循环状态、当前/最大轮次、时长/Token/费用预算、停止原因和 `iterations[]`；每轮包含编码/verifier 任务、门禁、计划、修改摘要、测试证据、失败分析和验证结论。
- `quality_gate` 返回最新门禁策略快照、状态、风险、独立证据数、阻断原因和 `checks[]`；检查项只返回结构化证据摘要，不返回完整日志或凭据。

通过需求生成的任务必须在 `input` 中包含：

- `task_type`: AI 任务类型，例如 `product_detail_design`、`technical_solution`、`development_planning`、`code_review`、`automated_testing`、`release_readiness` 或 `post_release_analysis`。
- `requirement_id`: 来源需求 ID。
- `requirement_snapshot`: 任务生成时的需求标题、优先级、背景、目标、约束和审批结论快照。
- `product_context`: 任务生成时的产品、版本、模块和 Git 资源上下文快照。
- `gitlab_mr_snapshot`: `code_review` 任务的兼容命名输入快照，可来自 GitLab MR 或 GitHub PR，包括 provider、project_id 或 project_path、mr_iid/PR number、标题、作者、source/target branch、commit sha 或 diff refs、变更文件摘要、diff 存储引用、Web URL 和快照时间。

请求人工接管自治循环：

```http
POST /api/ai-tasks/{task_id}/agent-loop/takeover
Content-Type: application/json

{"reason": "门禁连续失败，转人工定位环境问题"}
```

要求任务执行权限和产品 scope。仅存在运行中自治循环的任务可接管；服务端先取消仍在运行的编码/verifier Runner 任务，再把循环和任务推进到人工接管/待确认状态，记录接管人、原因和审计。重复或已终结循环返回明确状态错误，不会再次派发下一轮。

补充信息：

```http
POST /api/ai-tasks/{task_id}/more-info
```

请求体：

```json
{
  "answers": [
    {
      "question_id": "q_001",
      "answer": "v1 仅支持 Markdown 文档导入。"
    }
  ],
  "comment": "已补充范围边界"
}
```

响应：

```json
{
  "data": {
    "id": "task_001",
    "status": "draft"
  },
  "trace_id": "trace_006"
}
```

补充信息提交后任务回到 `draft` 并写入协作事件，由协作编排器按原工作项、`resume_state` 和 LangGraph thread 内部恢复；前端或真人不得再次调用 `/start`。任务管理页面在待确认弹窗中提供“要求补充”操作，成功后关闭待确认弹窗并刷新列表；`waiting_more_info` 任务在单一“操作”弹窗中提供“提交补充信息”操作，不展示前端兜底数据。

取消任务：

```http
POST /api/ai-tasks/{task_id}/cancel
```

批量取消任务：

```http
POST /api/ai-tasks/batch-cancel
```

请求体：

```json
{
  "task_ids": ["task_001", "task_002"],
  "reason": "需求范围调整，取消未完成任务"
}
```

`draft`、`running`、`waiting_more_info`、`waiting_review` 和 `writing_back` 任务可取消；`completed`、`failed`、`cancelled` 等终态任务、重复任务 ID 和不存在的任务进入 `skipped`，不阻塞同批次其他合法任务。成功任务会同步取消待处理 Review，并写入逐任务 `ai_task.cancelled` 审计；批次完成后写入 `ai_task.batch_cancelled` 审计。

响应：

```json
{
  "data": {
    "batch_id": "ai_task_cancel_batch_001",
    "reason": "需求范围调整，取消未完成任务",
    "updated": [
      {
        "id": "task_001",
        "status": "cancelled"
      }
    ],
    "updated_count": 1,
    "skipped": [
      {
        "id": "task_002",
        "code": "TASK_STATE_INVALID",
        "message": "Task cannot be cancelled from current status"
      }
    ],
    "skipped_count": 1
  },
  "trace_id": "trace_006b"
}
```

兼容批量重试任务端点（v2.0 外部禁用）：

```http
POST /api/ai-tasks/batch-retry
```

真人、前端、插件和其他外部客户端调用固定返回 `409 RD_COLLABORATION_REQUIRED`，不重试任务。可恢复失败由工作项调度器检查原 attempt、策略、预算和风险后调用内部 retry，并把结果投影到工作项和协作事件。

兼容响应：

```json
{
  "data": {
    "code": "RD_COLLABORATION_REQUIRED",
    "message": "Retry the failed attempt through its collaboration work item",
    "next_action": "open_rd_work_item"
  },
  "trace_id": "trace_006c"
}
```

### 人工确认

待确认和详情：

```http
GET /api/reviews/pending
GET /api/reviews/{review_id}
```

采纳：

```http
POST /api/reviews/{review_id}/approve
```

请求体可为空；提供时支持：

```json
{
  "version": 1,
  "comment": "确认进入下一阶段"
}
```

修改后采纳：

```http
POST /api/reviews/{review_id}/edit-approve
```

```json
{
  "version": 1,
  "edited_content": {
    "scope": "只支持 Markdown 文档导入和检索"
  },
  "comment": "收窄 v1 范围"
}
```

驳回重跑和要求补充信息：

```http
POST /api/reviews/{review_id}/reject
POST /api/reviews/{review_id}/request-more-info
```

统一响应：

```json
{
  "data": {
    "id": "task_001",
    "review_id": "review_001",
    "status": "waiting_review"
  },
  "trace_id": "trace_007"
}
```

`status` 是处理后的任务状态。

### 回写与导出

查询回写结果不会产生写副作用。未生成时返回 `status=not_written` 和空 `issues`：

```http
GET /api/writeback/results/{task_id}
```

响应：

```json
{
  "data": {
    "task_id": "task_001",
    "status": "not_written",
    "idempotency_key": "mock_issue:task_001",
    "issues": []
  },
  "trace_id": "trace_009"
}
```

显式生成或复用模拟 Issue：

```http
POST /api/writeback/results/{task_id}
```

响应：

```json
{
  "data": {
    "task_id": "task_001",
    "status": "completed",
    "idempotency_key": "mock_issue:task_001",
    "issues": [
      {
        "id": "mock_issue_001",
        "title": "产品详细设计：支持 Markdown 知识导入",
        "source_task_id": "task_001",
        "status": "open"
      }
    ]
  },
  "trace_id": "trace_010"
}
```

重复 POST 返回相同 `idempotency_key` 和同一组 `issues`，不会创建重复 Issue。

导出 Markdown：

```http
GET /api/export/tasks/{task_id}/markdown
```

响应类型：`text/markdown; charset=utf-8`。

规则：

- 仅允许导出 `completed` 状态任务；未完成任务返回 `TASK_STATE_INVALID`。
- 导出权限与 AI 任务读取权限一致：`product_detail_design` 和 `technical_solution` 仅允许 `product_owner`/`rd_owner`/`admin`，`code_review` 仅允许 `reviewer`/`rd_owner`/`admin`。
- 响应通过 `X-Trace-Id` 头关联本次导出请求。
