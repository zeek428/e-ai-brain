# 需求交付与研发任务 API

> API 分册。覆盖需求、AI 任务、人工确认、回写与导出。主入口见 [../api.md](../api.md)。

## v2.0 需求驱动研发协同契约

产品需求是研发协同唯一入口。调用顺序为：创建需求 → 正式评估 → 规划版本归组 → 创建协作运行 → 执行工作项/审核/返工 → 质量门禁与远程 Git 提交 → 按策略停在 `ready_for_release` 或经人工确认进入部署。默认不部署时，产品版本保持 `ready_for_release`，协作运行进入 `completed`，并记录 `completion_reason=ready_for_release`。

阶段边界：P0 覆盖需求评估、版本归组、协作开发测试、工作项取消、基础反馈归因和可信远程交付，并以 `ready_for_release` 为终点；岗位经验审核/复用和可选部署属于 P1。本分册同时描述 P0 与 P1 契约，P1 小节会显式标注，不能据此把 P1 当作 P0 阻塞项。

### 正式需求评估与版本归组

```http
POST /api/requirements/{requirement_id}/assessments
GET /api/requirements/{requirement_id}/assessments/latest
POST /api/requirement-assessments/{assessment_id}/opinions
POST /api/requirement-assessments/{assessment_id}/answers
POST /api/requirement-assessments/{assessment_id}/decisions
```

创建评估时服务端按业务大脑、产品和稳定需求字段解析唯一 active 统一研发执行策略；请求 Schema 不定义 `strategy_id`，即使调用者同时具备策略管理和评估决策权限也不得在评估命令内覆盖。请求体包含 `request_id`、`requirement_revision` 和可选 `reason`；`request_id` 在当前需求内幂等，`requirement_revision` 必须等于服务端最新修订。需要改变策略时，用户必须先通过统一策略 API 更新产品策略或业务大脑默认策略，形成新的 `policy_version`，再基于最新需求修订重新评估；评估决策本身不能携带候选策略。响应包含 `assessment_id/status/requirement_revision/initial_strategy_snapshot_id/final_strategy_snapshot_id/strategy_snapshot_id/completeness/risk/effort/dependencies/acceptance_criteria/version_candidates/recommended_action/deterministic_checks/version`，其中 `strategy_snapshot_id` 始终等于当前实际生效的快照（完成复核后等于 `final_strategy_snapshot_id`）。LLM 提供结构化建议，服务端校验 Schema、风险下限、权限和版本兼容性。状态统一为 `draft | evaluating | waiting_human | needs_info | rework_required | accepted | deferred | rejected | failed | cancelled`。

`opinions` 只允许已分配的真人评估者或受控 AI 评估执行单元按岗位输出契约提交；`answers` 由需求负责人补充事实并创建新的需求/评估版本；`decisions` 请求体包含 `decision=accept|reject|request_more_info|request_rework|defer`、`comment` 和 `version` 乐观锁。`accepted` 后需求原子进入 `approved`，服务端再按 `iteration_config` 选择兼容 `planning` 版本。唯一合格候选可自动归组；候选并列、高风险新建版本或人工调整版本归组时创建 `decision_request`，需求保持 `approved`。组版成功后写入 `selected_version_id/version_created/grouping_reason` 并进入 `planned`。非 accepted 或未完成组版状态不得创建协作运行。

同一 `requirement_revision + initial_strategy_snapshot_id` 的进行中或成功评估幂等复用；评估复核从初始快照派生最终快照时不改变该稳定业务键。若复核没有产生任何安全收紧差异，`final_strategy_snapshot_id = initial_strategy_snapshot_id`，当前 `strategy_snapshot_id` 也继续指向 base 快照，不创建空的 `assessment_resolved` 记录；只有 payload 实际变化时才创建 revision 1–2 派生快照。`requirement_id + request_id` 通过统一命令幂等记录约束，相同请求摘要返回原评估，不同摘要返回 `RD_IDEMPOTENCY_CONFLICT`。需求发生实质修改后必须创建新评估，旧评估只作历史证据。

### 统一研发执行策略

```http
GET  /api/delivery/rd-task-executor-policies
POST /api/delivery/rd-task-executor-policies
GET  /api/delivery/rd-task-executor-policies/{policy_id}
PATCH /api/delivery/rd-task-executor-policies/{policy_id}
DELETE /api/delivery/rd-task-executor-policies/{policy_id}
POST /api/delivery/rd-task-executor-policies/{policy_id}/validate
```

原入口原位升级，不接受旧版单任务匹配写契约，也不提供任何旧/新双模式字段。策略主记录增加服务端维护的 `policy_version` 乐观锁版本，创建时为 1；PATCH 请求必须提交 `expected_policy_version`，任何影响运行解释的字段或状态变更成功后原子递增，响应返回新的 `policy_version`。同一 `brain_app_id + product_id` 最多一条 active 产品策略，同一业务大脑最多一条 `product_id=null` 的 active 默认策略；解析时产品策略优先，未命中才使用默认策略，多个候选一律返回配置冲突而不按隐式优先级猜测。策略主体必须包含：

PATCH 请求使用 `{"expected_policy_version":3,"changes":{...}}`；响应至少返回 `policy={id,policy_version,status,brain_app_id,product_id,...}` 和 `trace_id`。过期版本返回 `409 RD_VERSION_CONFLICT` 并携带 `current_policy_version`，不得应用部分字段；active 唯一约束冲突返回 `409 RD_EXECUTION_POLICY_INVALID`。

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
  "experience_reuse_config": {
    "enabled": false,
    "min_confidence": 0.85,
    "policy_compatibility": "same_policy_version",
    "max_items": 5,
    "max_context_tokens": 4000,
    "max_age_days": 180,
    "repository_trust_domains": [],
    "tool_trust_domains": [],
    "require_independent_reviewer": true
  },
  "deployment_config": {"mode": "disabled"},
  "delivery_target": "ready_for_release",
  "role_bindings": [
    {"role_code": "developer", "actor_mode": "ai", "actor_selector": {"ai_employee_ids": ["ai_employee_dev_01"]}, "executor_profile_id": "executor_codex_01"},
    {"role_code": "tester", "actor_mode": "ai", "actor_selector": {"ai_employee_ids": ["ai_employee_test_01"]}, "executor_profile_id": "executor_test_01"}
  ]
}
```

`delivery_target` 允许 `ready_for_release | deployed`，默认 `ready_for_release`；P1 能力标志 `RD_COLLABORATION_DEPLOYMENT_ENABLED` 关闭时，创建、激活或重新启用 `deployed` 策略返回 `RD_COLLABORATION_DEPLOYMENT_DISABLED`。关闭后仅允许将已启用的 deployed 策略安全停用，不能新建“禁用的 deployed 策略”作为绕过路径；P0 策略和工作台不依赖部署代码。标志开启后，`deployed` 仍须通过现有发布评估、资源预检和人工确认。`experience_reuse_config` 属于同一策略 Schema；P0 或 P1 能力标志关闭时允许省略并规范化为上述安全默认值，只有 `RD_ROLE_EXPERIENCE_ENABLED=true` 且冻结配置 `enabled=true` 才允许注入经验。字段约束为 `min_confidence 0..1`、正整数 `max_items/max_context_tokens/max_age_days`、显式信任域数组和默认必须为 true 的独立审核；空信任域表示 deny-all，不解释为通配。`policy_compatibility` 支持 `same_policy_version | same_policy_schema`，默认前者：前者要求经验来源与当前运行的 `policy_id/policy_version` 完全相同；后者仍要求同业务大脑、同产品和相同 `schema_version`，且经验约束不能比当前冻结策略更宽，禁止跨产品复用。审核人与任一来源反馈生产者的隔离始终强制；`require_independent_reviewer=true` 还要求审核岗位/席位与所有来源岗位/席位分离，false 仅取消这层组织隔离，不能允许来源生产者自审。多需求合并时 `enabled` 取 AND、`min_confidence` 取最大、容量/时效上限取最小、信任域取交集、兼容规则取更严格值，`require_independent_reviewer` 取 OR。保存及激活前整体校验岗位、执行器、预算、门禁、Git、经验复用与风险配置。运行时把规范化策略独立冻结到 `rd_task_executor_policy_snapshots`，字段为 `id/policy_id/policy_version/parent_snapshot_id/snapshot_kind/resolution_context_key/resolution_revision/schema_version/content_hash/payload_json/created_by/created_at`。除 `parent_snapshot_id` 仅允许 base 为空外，其余身份、Schema、哈希和 payload 字段均为 NOT NULL。基础快照使用 `snapshot_kind=base/resolution_context_key=policy:{policy_id}:version:{policy_version}/resolution_revision=0/parent_snapshot_id=null`；评估自动收紧生成 `snapshot_kind=assessment_resolved` 的派生快照，以 `assessment:{assessment_id}` 作为 context key、以 1–2 作为收紧轮次，并要求 parent 非空且父子策略 ID/版本一致。协作启动再生成 `snapshot_kind=version_resolved/resolution_context_key=version:{version_id}:scope:{scope_version}/resolution_revision=1` 的运行快照，以同策略版本 base 为 parent，并通过 `rd_task_executor_policy_snapshot_sources` 按 requirement 唯一地关联每个需求的 final/effective 快照。唯一键为 `policy_id + policy_version + snapshot_kind + resolution_context_key + resolution_revision`；相同身份和哈希幂等复用、不同哈希冲突，不同评估可安全产生不同 final payload，但必须先确定性合并为单一 version_resolved payload 才能启动运行。

快照表由数据库触发器拒绝 UPDATE/DELETE，应用运行角色只授予 INSERT/SELECT；`policy_id`、父快照和所有消费者外键使用 `ON DELETE RESTRICT`。行内 kind-specific CHECK 要求 base parent 为空/revision 0，assessment_resolved parent 非空/revision 1..2，version_resolved parent 非空/revision 1。来源关系只按 `snapshot_id + requirement_id` 唯一；不同需求允许共同引用同一个 final/effective base 快照，不能对 `snapshot_id + source_snapshot_id` 建唯一约束。由于集合完整性和跨表同策略版本不能由 CHECK 实现，使用 `DEFERRABLE INITIALLY DEFERRED` constraint trigger 在协作启动事务提交时校验：运行不可变需求范围非空；每条范围行恰有一个同 requirement 的来源；来源无多余 requirement；source_count 等于范围行数；目标/来源策略 ID/版本一致；requirement revision、accepted assessment 和 final/effective snapshot 对应。来源关系和运行范围行均禁止 UPDATE/DELETE。策略 DELETE 在存在任何快照时返回 `409 RD_POLICY_IN_USE`，应改用停用。评估的 initial/final/effective 字段、岗位意见、协作运行、岗位反馈、经验候选及经验来源关联表都必须使用真实外键；运行只能引用 version_resolved 快照。策略缺失或无效返回 `RD_EXECUTION_POLICY_REQUIRED/INVALID`，快照缺失、哈希不一致或 Schema 无法读取返回 `RD_POLICY_SNAPSHOT_INVALID`，不得走策略外执行路径或用当前策略重算历史。

评估后策略复核最多自动单调收紧两轮：只允许降低自动化、收紧风险/权限/工具/仓库/预算、增加门禁或必需岗位、或把 `deployed` 改为 `ready_for_release`。新增必需评估岗位必须补齐兼容意见；不可比较或可能扩大边界返回 `RD_POLICY_HUMAN_DECISION_REQUIRED`，超过两轮返回 `RD_POLICY_RESOLUTION_LIMIT`。

### 研发岗位、执行器与协作运行

```http
GET/POST/PATCH /api/delivery/rd-roles
GET/POST/PATCH /api/delivery/rd-ai-employees
GET/POST/PATCH /api/delivery/rd-executor-profiles
POST           /api/product-versions/{version_id}/collaboration-runs
POST           /api/product-versions/{version_id}/collaboration-runs/restart
POST           /api/product-versions/{version_id}/scope-change-requests
GET            /api/delivery/rd-scope-change-requests/{scope_change_request_id}
GET            /api/requirements/{requirement_id}/collaboration-run
GET            /api/delivery/rd-collaboration-runs/{run_id}
GET            /api/delivery/rd-collaboration-runs/{run_id}/work-items
POST           /api/delivery/rd-work-items/{work_item_id}/claim
POST           /api/delivery/rd-work-items/{work_item_id}/submit
POST           /api/delivery/rd-work-items/{work_item_id}/review
POST           /api/delivery/rd-work-items/{work_item_id}/cancel
POST           /api/delivery/decision-requests/{decision_request_id}/decide
POST           /api/delivery/decision-requests/{decision_request_id}/answers
```

`rd-roles` 管理独立于系统 RBAC 的动态研发岗位；`rd-ai-employees` 管理独立于执行器的稳定 AI 数字员工身份、能力标签和人格版本；`rd-executor-profiles` 管理模型/Runner 运行能力。协作席位通过 `subject_type=ai_employee|human_user` 绑定 AI 数字员工或真人账号，AI 席位另行冻结 `executor_profile_id`。P0 真人选择只接受显式 `user_ids`，AI 选择只接受显式 `ai_employee_ids`，且调用时仍校验状态、系统权限或服务身份、产品范围、工作项席位和策略绑定。产品版本是协作聚合根：同一版本最多一个非终态运行。首次创建要求版本为 `planning`、至少包含一条 `planned` 需求、纳入需求最新评估均为 accepted，服务端锁定版本并冻结范围、策略、需求、岗位、员工和执行器快照，然后推进版本为 `active`。失败或取消的运行保持终态不可变；版本保持失败发生时的 `active|testing` 阶段，只能通过 restart 命令创建新一代运行。需求 GET 端点只定位所属版本活动或最近运行，不创建第二个运行。

权限点分别为 `delivery.rd_roles.manage`、`delivery.rd_ai_employees.manage`、`delivery.rd_executor_profiles.manage`、`delivery.requirement_assessments.read/decide`、`delivery.rd_collaboration.read/plan/work`、`delivery.decision_requests.decide/answer` 和 `delivery.rd_role_experiences.read/decide`；策略继续使用 `delivery.rd_executor_policies.manage`，部署继续使用现有部署权限。岗位、员工档案或席位不会自动授予这些权限。

工作项包含 `owner_seat_id/dependencies/input_contract/output_contract/acceptance_criteria/risk_level/status/resume_state/suspended_attempt_id/ai_task_id/reviewer_seat_id/idempotency_key`。依赖满足后才能进入 `ready`，无依赖项可并行；审核或质量门禁失败保留原 attempt，同范围返工进入 `rework_required` 并在下一次领取时创建新 attempt，范围/依赖/负责人变化则创建新计划版本和替代工作项。`blocked/awaiting_human` 保存平台冻结的恢复目标和解除条件；问题解除或决策完成后只能回到校验后的 `ready/running/rework_required/cancelled`。高风险、超权限、冲突、预算超限、门禁失败或部署边界创建 `decision_requests` 并暂停受影响分支。详情响应聚合 DAG、租约、AI 任务/Runner、审核、返工、门禁、Git、预算和角色反馈。

#### 创建协作运行

```http
POST /api/product-versions/{version_id}/collaboration-runs
```

请求体：

```json
{
  "request_id": "req-start-version-001",
  "scope_version": 7,
  "reason": "启动 2.0.0 研发协作"
}
```

`scope_version` 必须等于版本当前需求范围版本。服务端事务锁定产品版本，验证全部纳入需求最新评估为 `accepted` 且 final/effective 快照属于同一 `policy_id/policy_version`，再按策略 Schema 声明的 merge operator 确定性生成 version_resolved 快照：允许集取交集、禁止项/必需岗位/门禁/人工确认点取并集、上限取更严格值、任一来源要求 `ready_for_release` 时版本终点即为 `ready_for_release`，预算保存基础运行总上限及逐需求清单，经验复用配置按本章保守合并规则生成；未声明 merge operator 的字段必须一致。不可比较或冲突返回 `RD_VERSION_POLICY_MERGE_REQUIRED` 并创建决策请求，不启动运行；冻结 options 只能是拆分/移出需求、通过统一产品/默认策略 API 修改后重新评估、或取消启动，不能提交任意合并 payload 或版本显式策略。服务端为每条纳入需求写入不可变 `rd_collaboration_run_requirements`，冻结 `requirement_id/requirement_revision/assessment_id/final_strategy_snapshot_id/acceptance_criteria_hash/repository_scope_hash`，同时写入按 requirement 唯一的策略来源边；延迟约束在提交前保证两组集合逐条完全相等。服务端另行冻结仓库基线和岗位席位；以 `version_id + scope_version + version_resolved_snapshot_id` 作为业务幂等约束，并以 `product_version_id + request_id` 保存命令幂等记录。并发重复请求返回同一活动运行；同一 request ID 使用不同摘要返回 `RD_IDEMPOTENCY_CONFLICT`，同一版本存在不同范围或快照的活动运行时返回冲突。

`scope_version` 的事实源是 `product_versions.scope_version bigint NOT NULL DEFAULT 1`。规划版本的需求加入、移除、改派，纳入需求修订/验收标准或 final/effective 策略快照变化，以及影响冻结输入的版本仓库或分支基线变化，必须在同一版本行锁事务中递增该值；普通字段展示修改不递增。协作启动后，只要版本存在非终态运行，普通范围写接口都返回 `409 RD_SCOPE_FROZEN`，不能修改运行范围行、version_resolved 来源或 `scope_version`；唯一受控入口是下述 `scope-change-requests` 命令。产品版本一旦进入 `ready_for_release|deploying|released`，即使 ready-target 运行已 completed 也冻结原版本并返回 `resolution=new_planning_version`。不改变范围的重规划只递增运行 `plan_version`。版本列表/详情、需求归组结果、范围变更预览及 `RD_SCOPE_VERSION_CONFLICT.details.current_scope_version` 都必须返回当前值，客户端不得自行计算。

响应核心字段：

```json
{
  "data": {
    "id": "rd_run_001",
    "request_id": "req-start-version-001",
    "product_version_id": "version_001",
    "run_generation": 1,
    "supersedes_run_id": null,
    "scope_version": 7,
    "plan_version": 1,
    "strategy_snapshot_id": "rd_policy_snapshot_version_001_scope_7",
    "strategy_snapshot_kind": "version_resolved",
    "strategy_snapshot_hash": "sha256:...",
    "strategy_source_count": 2,
    "status": "planning",
    "resume_state": null,
    "suspended_decision_request_id": null,
    "suspended_at": null,
    "version": 1,
    "idempotent_replay": false
  },
  "trace_id": "trace_rd_start_001"
}
```

#### 受控调整协作范围

```http
POST /api/product-versions/{version_id}/scope-change-requests
GET  /api/delivery/rd-scope-change-requests/{scope_change_request_id}
```

请求体：

```json
{
  "request_id": "scope-change:version_001:8",
  "expected_scope_version": 7,
  "expected_run_generation": 1,
  "source_run_id": "rd_run_001",
  "reason": "新增已完成评估的合规整改需求",
  "operations": [
    {
      "op": "add_requirement",
      "requirement_id": "requirement_003",
      "requirement_revision": 2,
      "assessment_id": "assessment_003",
      "final_strategy_snapshot_id": "rd_policy_snapshot_assessment_003"
    },
    {
      "op": "remove_requirement",
      "requirement_id": "requirement_002",
      "destination": "approved_pool"
    },
    {
      "op": "update_repository_baseline",
      "repository_id": "repository_001",
      "branch_config_version": 4,
      "base_commit_sha": "0123456789abcdef"
    }
  ]
}
```

`operations` 只接受 `add_requirement | remove_requirement | replace_requirement_snapshot | update_repository_baseline` 四类类型化引用，不接受任意合并 payload。新增或替换需求必须引用同产品、最新 accepted 评估、明确需求修订和 final/effective 快照；服务端对提议范围执行与首次启动相同的策略合并、容量、依赖、仓库和交付终点校验。`request_id` 映射为命令幂等键；相同键与相同规范化 operations 哈希返回同一请求，相同键不同哈希返回 `RD_IDEMPOTENCY_CONFLICT`。服务端同时比较 `expected_scope_version` 和 `expected_run_generation`，任一过期都不创建决策或修改范围。

| op | 必填字段 | 应用语义 |
|---|---|---|
| `add_requirement` | `requirement_id/requirement_revision/assessment_id/final_strategy_snapshot_id` | 要求需求当前为同产品 approved、未被其他活动版本占用；批准后绑定当前版本并进入 planned。 |
| `remove_requirement` | `requirement_id/destination=approved_pool` | 要求需求仍属于当前版本且尚未形成新 generation；批准后解除版本绑定并回到 approved 池。 |
| `replace_requirement_snapshot` | `requirement_id/requirement_revision/assessment_id/final_strategy_snapshot_id` | 要求引用该需求修订的最新 accepted 评估；批准后替换版本范围事实，但不修改历史运行范围。 |
| `update_repository_baseline` | `repository_id/branch_config_version/base_commit_sha` | 要求仓库属于同产品且分支配置版本匹配；批准后替换版本冻结基线。 |

服务端把规范化数组同时保存为父请求 `operations_json/operations_hash` 和不可变 `rd_scope_change_request_operations` 类型化子行；子行按 position 唯一并以真实外键引用 requirement、assessment、snapshot 和 repository，从而保证删除限制与审计，不能只依赖 JSON 中的 ID。

创建请求需要 `delivery.rd_collaboration.plan`、产品范围和来源运行可见性；处理决策需要 `delivery.decision_requests.decide`、冻结决策人选择器和同一产品范围。LLM 只能生成 operations 提议，不能以服务身份自批；实际批准仍由人工账号完成并写审计。

当版本尚未进入待发布阶段时，创建命令在一个事务中锁定版本和来源运行，写入 `rd_scope_change_requests(status=pending_decision, source_run_state=当前状态)` 与唯一决策请求。决策固定使用 `subject_type=rd_scope_change_request/subject_id=范围请求 ID/decision_type=scope_change/plan_version=来源运行当前 plan_version`，冻结 `approve_apply_and_restart` 与 `reject_keep_current_scope` 两个 option 及其状态映射；LLM 和客户端不能提交第三种目标状态。来源运行处于 `running|integrating|verifying` 时原子暂停为 `waiting_human` 并把原阶段保存到运行 `resume_state`；处于 `draft|planning` 时不伪造非法 resume_state，而由 pending 范围请求作为调度围栏，禁止运行继续推进；已经 `failed|cancelled` 时只保存待决请求，不重复改变终态。来源运行已因其他决策处于 `waiting_human` 时返回 `RD_SCOPE_FROZEN`，details 包含现有 `decision_request_id` 和 `next_action=resolve_existing_decision`，不得覆盖原暂停字段。接口返回 `202`，核心字段为 `scope_change_request_id/status/decision_request_id/source_run_id/source_run_state/current_scope_version/restart_required=false`，此时不得终结运行、递增范围版本或写入部分 operations。

```json
{
  "data": {
    "scope_change_request_id": "scope_change_001",
    "request_id": "scope-change:version_001:8",
    "status": "pending_decision",
    "decision_request_id": "decision_scope_change_001",
    "source_run_id": "rd_run_001",
    "source_run_state": "running",
    "expected_run_generation": 1,
    "current_scope_version": 7,
    "operations_hash": "sha256:...",
    "restart_required": false,
    "idempotent_replay": false
  },
  "trace_id": "trace_scope_change_001"
}
```

人工选择批准时，决策服务调用同一领域事务：重新锁定版本、范围变更请求、来源运行和当前范围，复核 generation/scope/operations 哈希；先以来源 `run_generation` 为围栏收敛旧代次，再应用范围。收敛必须原子撤销全部活动租约和 replay secret，把旧运行全部非终态工作项、当前 attempt、pending Review 和关联 AI task 推进到 cancelled 并记录 `scope_change` 原因，取消尚未派发的 Runner/Git Outbox，针对已派发 Runner 写 cancellation Outbox，对已派发或状态未知的 Git/Runner 动作写待对账记录；已批准工作项和已落地 Git 证据保持历史不可变。随后把尚未终态的来源运行终结为 `cancelled(completion_reason=scope_change)`、清除运行暂停字段，按 operations 更新产品版本范围，仅递增一次 `product_versions.scope_version`，并把请求推进为 `applied`、保存 `applied_scope_version/applied_at`。领域状态、围栏、取消/对账 Outbox、事件、审计和范围应用必须同事务提交；任一步失败整体回滚，不得出现 cancelled run 下仍可领取或回写的子任务。

外部 Runner 的物理停止和外部 Git 对账由 Worker 异步完成，但旧代次的租约、generation token 和工作区均已失效；任何迟到 submit、Review、Runner completion、Git callback 或 Outbox 回写只能保存为审计/对账证据，不能推进旧运行或新 generation。restart 为新 generation 创建新的工作项、attempt、lease 和隔离 worktree/分支，不能复用被取消执行上下文。响应返回 `terminal_run_id/applied_scope_version/restart_required=true`，调用方随后显式提交 restart，并把 `terminal_run_id` 与新 `scope_version` 带入。人工拒绝把请求推进为 `rejected`；若来源运行由该请求从 running/integrating/verifying 暂停，则按冻结的 `resume_state` 恢复并清空暂停字段；draft/planning 或已终态来源保持原状态。范围和 `scope_version` 均不变。来源运行已经 `failed|cancelled` 时仍须经过上述受控决策，但批准事务不重复终结运行；仍须确认旧代次不存在可回写租约或未围栏副作用后才应用范围。

范围变更决策沿用通用 decide 请求体和乐观锁。批准时其 `data` 除通用 `decision_request/affected_subject/idempotent_replay` 外固定返回：

```json
{
  "scope_change_request": {
    "id": "scope_change_001",
    "status": "applied",
    "operations_hash": "sha256:...",
    "applied_scope_version": 8,
    "applied_at": "2026-07-17T10:30:00Z"
  },
  "terminal_run_id": "rd_run_001",
  "run": {"id": "rd_run_001", "status": "cancelled", "completion_reason": "scope_change", "version": 12},
  "restart_required": true,
  "next_state": "applied"
}
```

拒绝时返回 `scope_change_request.status=rejected`、`applied_scope_version=null`、`terminal_run_id=null`、`restart_required=false`，以及保持或恢复后的完整 run/version；不得返回 applied 状态的部分字段。

同一产品版本最多一条 `pending_decision` 范围变更请求。任一校验失败、并发决策失败或 operations 部分失败都整体回滚；不同请求并发时，只有锁内仍匹配当前 scope/generation 的请求可以应用。GET 返回原始 operations、规范化哈希、状态、决策、来源/终态运行和应用版本，不能用于直接修改请求。

当版本或来源运行已经达到 `ready_for_release|deploying|released`，或 ready-target 运行已 `completed` 时，POST 不创建范围变更请求，返回 `409 RD_SCOPE_FROZEN`，details 固定包含 `resolution=new_planning_version` 和 `next_action=create_followup_requirement`。调用方应通过标准 `POST /api/requirements` 创建带来源关系的后续需求；旧版本、旧需求、旧运行和交付证据保持不可变。

#### 重启失败或取消的协作运行

```http
POST /api/product-versions/{version_id}/collaboration-runs/restart
```

请求体：

```json
{
  "request_id": "req-restart-version-001-generation-2",
  "terminal_run_id": "rd_run_001",
  "scope_version": 7,
  "reason": "执行器恢复后重新规划未完成工作"
}
```

restart 仅允许产品版本为 `active|testing`、指定运行属于该版本且状态为 `failed|cancelled`、指定运行是当前最近一代、同版本不存在非终态运行时执行。服务端锁定版本和旧运行，重新校验当前 `scope_version`、accepted 评估、策略快照、仓库基线、岗位/执行器可用性和预算；然后创建 `run_generation=旧值+1`、`supersedes_run_id=terminal_run_id` 的新运行及新的不可变运行需求范围。旧运行、计划、工作项、attempt、决策和证据不更新。只有已批准且产物与当前范围、策略、commit 和门禁仍兼容的历史结果可以带原证据引用转化为新计划中的已满足输入；所有未完成、运行中、暂停或无法验证的工作都创建新的工作项/attempt，不能复活旧租约。若范围已变化，只能在旧运行终态且无活动运行后先更新产品版本并递增 `scope_version`，再提交新值；restart 不隐式吸收变化。

restart 使用 `product_version_id + request_id` 持久化命令幂等，成功响应与创建接口相同并额外返回 `run_generation/supersedes_run_id/reused_evidence_refs`。并发相同请求幂等返回同一新运行。过期 `scope_version` 返回 `RD_SCOPE_VERSION_CONFLICT`；策略合并失败返回 `RD_VERSION_POLICY_MERGE_REQUIRED`；快照损坏返回 `RD_POLICY_SNAPSHOT_INVALID`；指定运行不属于该版本、非最近终态、版本不在 active/testing、已有活动运行或资源重新校验失败返回 `RD_RUN_RESTART_NOT_ALLOWED`。任何失败都不得修改旧运行或创建部分新计划。

#### 领取工作项

```http
POST /api/delivery/rd-work-items/{work_item_id}/claim
```

请求体：

```json
{
  "expected_version": 3,
  "lease_seconds": 900,
  "idempotency_key": "claim:rd_work_item_001:seat_dev_001:1"
}
```

`lease_seconds` 允许 60–1800 秒。服务端校验工作项为 `ready`、依赖已批准、调用主体匹配席位、执行器/权限/预算仍有效，再原子创建 attempt、写入 lease 并把工作项推进到 `running`。相同幂等键和摘要返回原 claim；版本不匹配、已有有效租约或席位不匹配时不修改状态。成功或幂等重放响应：

```json
{
  "data": {
    "work_item": {"id": "rd_work_item_001", "status": "running", "version": 4},
    "attempt": {"id": "rd_attempt_001", "attempt_no": 1, "status": "running"},
    "lease_token": "lease-secret",
    "lease_expires_at": "2026-07-16T12:15:00Z",
    "lease_holder": {"seat_id": "seat_dev_001", "subject_type": "ai_employee", "subject_id": "ai_employee_dev_01"},
    "strategy_snapshot_id": "rd_policy_snapshot_001",
    "run": {"id": "rd_run_001", "status": "running", "version": 7},
    "next_state": "running",
    "idempotent_replay": false
  },
  "trace_id": "trace_rd_claim_001"
}
```

claim 是永久命令幂等中的限时响应例外：租约有效期内，相同键和摘要从 `rd_command_replay_secrets` 解密并返回同一 lease 成功响应；该表以 `command_record_id` 唯一关联，保存 `secret_ciphertext/key_id/expires_at/scrubbed_at/created_at/updated_at`。到期清理必须把密文置空并记录 `scrubbed_at`；此后固定返回 `RD_WORK_ITEM_LEASE_EXPIRED`，但保留不可变幂等记录且绝不创建新 attempt。审计、通用响应快照和日志不得记录明文。要重新领取必须等待调度器把工作项重新推进为可领取状态，并使用新的幂等键和工作项版本。

#### 提交工作项结果

```http
POST /api/delivery/rd-work-items/{work_item_id}/submit
```

请求体：

```json
{
  "attempt_id": "rd_attempt_001",
  "lease_token": "lease-secret",
  "version": 4,
  "idempotency_key": "submit:rd_attempt_001:result-v1",
  "output": {
    "summary": "完成订单幂等改造",
    "artifacts": [{"type": "commit", "sha": "abc1234"}]
  },
  "evidence": {
    "tests": [{"name": "payment idempotency", "status": "passed"}],
    "logs": []
  }
}
```

服务端校验 attempt 属于当前工作项、租约未过期且 token/holder 匹配，输出满足冻结 `output_contract`，证据满足最小门禁，然后原子结束 attempt 并进入 `awaiting_review` 或策略允许的下一确定性状态。相同 `attempt_id + idempotency_key` 返回原结果；同一 attempt 不同 payload 返回 `RD_IDEMPOTENCY_CONFLICT`。

```json
{
  "data": {
    "work_item": {"id": "rd_work_item_001", "status": "awaiting_review", "version": 5},
    "attempt": {"id": "rd_attempt_001", "status": "submitted", "output_ref": "rd_output_001", "evidence_ref": "rd_evidence_001"},
    "next_state": "awaiting_review",
    "run": {"id": "rd_run_001", "status": "running", "version": 8},
    "idempotent_replay": false
  },
  "trace_id": "trace_rd_submit_001"
}
```

#### 审核工作项

```http
POST /api/delivery/rd-work-items/{work_item_id}/review
```

请求体：

```json
{
  "decision": "approve",
  "comment": "实现和证据满足验收标准",
  "version": 5,
  "idempotency_key": "review:rd_work_item_001:v5:approve"
}
```

`decision` 允许 `approve | request_rework | reject`。调用者必须属于冻结 reviewer 席位且不能是当前 attempt 执行主体；`version` 为工作项乐观锁。`approve` 推进为 `approved`；`request_rework` 必须有 comment，保留原 attempt 并推进为 `rework_required`，下一次 claim 创建新 attempt；`reject` 明确推进工作项为 `failed`、当前 attempt 为 `rejected`，必需工作项被拒绝时运行原子进入 `waiting_human` 并创建“重规划或终止”决策请求，不能隐式映射为 cancelled 或返工。

```json
{
  "data": {
    "work_item": {"id": "rd_work_item_001", "status": "approved", "version": 6},
    "attempt": {"id": "rd_attempt_001", "status": "approved"},
    "review": {"decision": "approve", "comment": "实现和证据满足验收标准", "version": 1},
    "next_state": "approved",
    "run": {"id": "rd_run_001", "status": "running", "version": 9},
    "decision_request_id": null,
    "idempotent_replay": false
  },
  "trace_id": "trace_rd_review_001"
}
```

#### 取消工作项

```http
POST /api/delivery/rd-work-items/{work_item_id}/cancel
```

请求体：

```json
{
  "reason": "需求范围调整，停止当前实现",
  "version": 6,
  "idempotency_key": "cancel:rd_work_item_001:v6:scope-change"
}
```

调用者必须具备 `delivery.rd_collaboration.plan` 和产品范围；协作编排器使用内部服务身份调用同一领域命令。低风险、无已启动下游且策略允许直接取消时，服务端在一个数据库事务内校验工作项/运行版本，撤销数据库租约，关闭当前 attempt，取消 pending Review 和关联 AI task，把工作项推进为 `cancelled`，重算依赖和运行状态，并写入 Runner cancellation Outbox、协作事件和审计。物理 Runner 停止由 Outbox Worker 异步执行；被撤销租约的迟到完成回写必须拒绝，不能复活工作项。

高风险、已有运行中下游、会扩大取消范围或策略要求人工确认时，不直接完成取消，但必须先安全暂停执行：同一事务把工作项置为 `awaiting_human`、撤销活动租约、把当前 attempt 标记为 `suspended_for_decision`，并写 Runner cancellation Outbox；迟到结果同样隔离。人工批准取消后再原子完成取消；人工拒绝取消或选择继续时，旧 attempt/lease 不复活，服务端重新校验权限、依赖、预算和工作区后把工作项推进到 `ready`，下一次 claim 使用新版本、新幂等键、新 attempt 和新 lease。返回 `202`、decision request 和暂停 Outbox。成功或幂等重放响应返回 `work_item/attempt/ai_task/review/run/dependency_recalculation/runner_cancellation_outbox_id/decision_request/next_state/idempotent_replay/trace_id`。终态项返回 `RD_WORK_ITEM_STATE_INVALID`，版本冲突返回 `RD_VERSION_CONFLICT`，需要人工决策但无法创建请求时返回 `RD_DECISION_REQUIRED`；事务任一步失败不得留下部分取消。

#### 处理人工决策

```http
POST /api/delivery/decision-requests/{decision_request_id}/decide
```

请求体：

```json
{
  "selected_option": "continue_with_restricted_scope",
  "input": {"included_modules": ["payments"]},
  "comment": "仅保留支付模块改造",
  "version": 2,
  "idempotency_key": "decision:decision_001:v2:restricted"
}
```

选项必须来自冻结 `options[]`。每项固定包含 `code/label/outcome/subject_transition/requires_comment/input_schema/effect_preview`：`outcome` 只允许 `approve | reject | request_more_info`，`subject_transition` 是平台已校验的目标状态或领域命令，客户端不能另传恢复状态；可选 `input` 必须严格通过所选 option 的 `input_schema`，不需要参数时 `input_schema` 为空对象且请求不得夹带字段。选择 approve/reject 后，决策请求分别进入 `approved/rejected` 并原子应用主体迁移；选择 request_more_info 后进入 `waiting_more_info`，主体继续保持暂停，不能提前恢复。选择“取消工作”这类业务选项时，option 自身使用 `outcome=approve/subject_transition=cancelled`；决策请求的 `cancelled` 仅表示请求被撤销或替代，不表示批准取消主体。活动请求响应必须同时返回 `expires_at/timeout_policy/escalation_target_selector/escalation_level`，客户端只展示服务端时间，不自行判定或推进过期。

调用者须具备 `delivery.decision_requests.decide`、产品范围和请求指定决策资格。处理协作运行暂停时，服务端同时校验 `rd_collaboration_runs.suspended_decision_request_id` 和运行版本，按冻结 option 和运行自己的 `resume_state` 恢复 `running/integrating/verifying`、返工、失败或取消，并在恢复时清空 `resume_state/suspended_decision_request_id/suspended_at`；客户端不能提交恢复阶段。已过期、已替代或不再绑定当前暂停聚合的请求返回稳定冲突错误。

决策请求创建时必须冻结 `expires_at`、`timeout_policy` 和 `escalation_target_selector`。P0 默认且允许的超时策略为 `escalate_keep_paused`：内部协作维护 Worker 使用数据库时间扫描 `pending/waiting_more_info`，在同一事务将到期请求标记为 `expired`、写入 `expired_at/expiry_event_id`，保持受影响主体暂停，并按升级 selector 幂等创建或复用 `escalation_level+1` 的后继决策请求，再把主体的当前决策引用原子切换到后继请求。它不得选择任何业务 option、不得自动批准或恢复主体。重复扫描、Worker 重启和并发扫描只产生一个 expiry event 和一个活动后继请求；没有可用升级对象时保留主体暂停并创建管理员告警。到期边界按 `database_now >= expires_at`；旧请求的 decide/answer 固定返回 `RD_DECISION_EXPIRED`。

```json
{
  "data": {
    "decision_request": {
      "id": "decision_001",
      "status": "approved",
      "selected_option": "continue_with_restricted_scope",
      "expires_at": "2026-07-17T12:00:00Z",
      "timeout_policy": "escalate_keep_paused",
      "escalation_target_selector": {"role_codes": ["rd_owner"]},
      "escalation_level": 0,
      "expired_at": null,
      "supersedes_decision_request_id": null,
      "version": 3
    },
    "affected_subject": {"type": "rd_collaboration_run", "id": "rd_run_001"},
    "run": {"id": "rd_run_001", "status": "integrating", "version": 11, "resume_state": null, "suspended_decision_request_id": null, "suspended_at": null},
    "next_state": "integrating",
    "idempotent_replay": false
  },
  "trace_id": "trace_rd_decision_001"
}
```

补充信息使用：

```http
POST /api/delivery/decision-requests/{decision_request_id}/answers
```

请求体包含 `answer/evidence/version/idempotency_key`。每个决策请求冻结 `answer_actor_selector`（明确用户、运行席位或业务角色）和所需信息 Schema；调用者必须具备 `delivery.decision_requests.answer`、业务大脑/产品范围并命中 selector，决策人权限不能替代被请求人的答复资格。仅 `waiting_more_info` 可提交；服务端校验答案 Schema、保存补充证据、重新校验并生成新 options/version 后回到 `pending`，仍不恢复主体。成功或幂等重放返回 `decision_request={id,status=pending,version,options,options_hash,expires_at,timeout_policy,escalation_target_selector,escalation_level}`、`affected_subject`、`next_state=pending`、`idempotent_replay` 和 `trace_id`；版本冲突、过期请求或同键不同摘要均不得写入部分答案或新 options。`decision_requests.plan_version` 为 NOT NULL，组版前或无协作计划的决策使用 0；待决唯一约束覆盖 `pending/waiting_more_info`，避免 NULL 让同一问题产生多个活动请求。

#### 岗位经验查询与审核（P1）

仅在 `RD_ROLE_EXPERIENCE_ENABLED=true` 时注册/开放本节端点；标志关闭时 P0 不生成经验候选、不注入经验上下文，基础反馈仍正常落库。

```http
GET  /api/delivery/rd-role-experiences?role_code=developer&product_id=product_001&status=approved&page=1&page_size=20
GET  /api/delivery/rd-role-experiences/{experience_id}
POST /api/delivery/rd-role-experiences/{experience_id}/decide
```

列表需要 `delivery.rd_role_experiences.read`，并在查询层按当前用户产品范围和业务大脑范围过滤；支持 `brain_app_id/product_id/role_code/work_item_type/scenario/risk_level/repository_trust_domain/tool_trust_domain/status/min_confidence/page/page_size`。返回 `experience_key/version/brain_app_id/role_code/product_scope/work_item_type/scenario/risk_scope/repository_trust_domains/tool_trust_domains/content/evidence_refs/strategy_snapshot_id/source_strategy_snapshot_ids/confidence/status/review_version`；`strategy_snapshot_id` 是候选生成时实际生效快照。决策请求体为：

```json
{
  "decision": "approve",
  "comment": "已验证三次交付均有效",
  "version": 1,
  "idempotency_key": "experience:exp_001:v1:approve"
}
```

`decision` 允许 `approve | reject | retire`；调用者需要 `delivery.rd_role_experiences.decide`、产品和业务大脑范围。服务端必须通过 `rd_role_experience_sources` 读取每条不可变 `role_feedback_records.producer_subject_type/producer_subject_id/producer_role_code/producer_seat_id`，拒绝审核者匹配任一来源生产者；不能拿反馈归因的执行对象代替生产者。冻结配置要求独立审核时，还拒绝与任一非空 producer role/seat 相同的审核岗位/席位。后续协作只有在 `RD_ROLE_EXPERIENCE_ENABLED=true` 且 version_resolved 快照的 `experience_reuse_config.enabled=true` 时才执行检索；结果只返回 `approved` 且未退役、置信度达到 `min_confidence` 的经验，并逐项校验业务大脑、产品、岗位、工作项类型、场景、风险上限、仓库/工具信任域、当前用户数据权限、`policy_compatibility` 和 `max_age_days`。过滤完成后按确定性排序截断到 `max_items/max_context_tokens`，每项保留经验 ID、版本和证据引用；跨产品、跨业务大脑、低置信度、超时效、信任域不匹配、策略不兼容或权限不足的记录必须在查询层排除，不能仅在 Prompt 拼装时过滤。响应中的经验引用不能直接改变策略、预算、权限或门禁。

成功或幂等重放返回 `experience.id/status/review_version`、`review.decision/comment/reviewer_id`、`next_state/idempotent_replay` 和 `trace_id`。请求字段 `version` 对应持久化的 `review_version`；同一幂等键不同摘要返回 `RD_IDEMPOTENCY_CONFLICT`。

#### 命令幂等与通用响应语义

评估创建、协作启动、协作 restart、范围变更请求、claim、submit、review、decision、decision answer、工作项取消和经验审核都在业务写事务内写入 `rd_command_idempotency_records`，固定保存 `command_type/aggregate_type/aggregate_id/idempotency_key/request_hash/result_type/result_id/http_status/response_hash/response_json/created_at`，唯一键为 `command_type + aggregate_type + aggregate_id + idempotency_key`。`response_json` 是完成命令时的不可变脱敏业务响应快照，`response_hash` 对排除每次请求 `trace_id` 和派生 `idempotent_replay` 标志后的规范化响应计算；后续不得从已经变化的聚合对象重新拼装“原响应”。密钥和大体积产物不进入该字段。claim 的 `response_json` 只保存稳定 secret 引用；真实 `lease_token` 位于上述可擦除 replay secret 表，有效期内解密回填同一 token。评估、启动、restart 和范围变更的 `request_id` 分别映射为该表的 `idempotency_key`；除上文 claim 到期例外外，重放返回保存的原 HTTP 状态和业务响应，服务端在返回副本上设置 `idempotent_replay=true` 并生成本次 `trace_id`；不同 `request_hash` 必须冲突。不可变命令记录不设置 TTL 或 `expires_at`，不能因决策请求或聚合终态而允许同一键重新执行；仅可随依法批准的整聚合归档/清理一起处理。领域表上的活动运行、运行 generation、评估、范围变更、attempt 和依赖唯一约束仍保留，用于抵御不同幂等键下的并发写入。

上述写接口成功均返回 `data + trace_id`；除租约过期的 claim 例外外，幂等重放保持原 HTTP 成功码并把响应快照中的 `idempotent_replay` 置为 true。错误统一复用公共 FastAPI envelope `{detail:{code,message,details,trace_id}}`，当前版本等领域字段放入 `detail.details`；不得改用 data/error envelope，也不得创建 attempt、Review、决策结果、经验版本或领域事件等部分写入。

#### 并发、租约和错误语义

所有下表错误都使用公共 `detail` envelope。`detail.details.retryable` 明确客户端能否原请求重试，`detail.details.next_action` 给出解除条件；涉及乐观锁、范围或运行代次时同时返回 `current_version/current_scope_version/current_run_generation`。`retryable=false` 表示必须先修改配置、输入或完成人工决策，不表示错误可忽略；任何失败都不得推进工作项、创建 attempt 或写入部分领域状态。

| HTTP | 错误码 | 语义 |
|---|---|---|
| 409 | `RD_SCOPE_VERSION_CONFLICT` | 启动、restart 或范围变更时提交的 scope 版本已过期；`details` 返回 `current_scope_version/retryable=false/next_action=reload_version_scope`，不自动扩大范围、不创建决策。 |
| 409 | `RD_RUN_GENERATION_CONFLICT` | 范围变更的 `expected_run_generation` 已过期或来源运行不是当前最近代；`details` 返回 `current_run_generation/retryable=false/next_action=reload_collaboration_run`，不创建决策。 |
| 409 | `RD_SCOPE_FROZEN` | 产品版本存在非终态协作运行，或版本已进入 `ready_for_release|deploying|released`，需求/修订/验收/策略快照/仓库或分支范围不可原地变更；`details.retryable=false`。待发布前普通入口返回 `next_action=create_scope_change_request`；已有其他 waiting_human 决策时返回其 ID 和 `next_action=resolve_existing_decision`；已处于待发布边界时返回 `resolution=new_planning_version/next_action=create_followup_requirement`。 |
| 422 | `RD_SCOPE_CHANGE_INVALID` | 范围 operations 的类型、引用、accepted 评估、策略合并、依赖、仓库或交付终点校验失败；`details` 返回 `operation_index/field/issues/retryable=false/next_action=revise_scope_change`，不创建部分请求或修改范围。 |
| 409 | `RD_ACTIVE_RUN_CONFLICT` | 同一产品版本已有范围或策略快照不同的非终态运行。 |
| 409 | `RD_RUN_RESTART_NOT_ALLOWED` | restart 的版本状态、失败来源、最近代次、无活动运行或资源可用前置条件不满足；旧运行保持不变。范围、策略合并和快照问题分别使用专用错误码。 |
| 409 | `RD_VERSION_POLICY_MERGE_REQUIRED` | 多需求 final/effective 快照不属于同一策略版本、字段不可比较或确定性合并失败；返回冲突字段和决策请求。 |
| 409 | `RD_VERSION_CONFLICT` | 策略 PATCH、claim/submit/review/cancel/decision/decision answer/经验审核的乐观锁版本不匹配。 |
| 409 | `RD_WORK_ITEM_NOT_READY` | 依赖、席位、权限、预算或工作区条件未满足，不能领取。 |
| 409 | `RD_WORK_ITEM_LEASE_HELD` | 工作项已有未过期租约；返回 holder 摘要和过期时间。 |
| 409 | `RD_WORK_ITEM_LEASE_EXPIRED` | claim 重放或 submit 使用的租约已过期、已回收或 token 不匹配，不创建新 attempt、不接受迟到结果。 |
| 409 | `RD_WORK_ITEM_STATE_INVALID` | 工作项已终态或当前状态不允许取消、提交或审核。 |
| 409 | `RD_DECISION_REQUIRED` | 当前工作项操作必须转人工决策，但决策请求未成功创建。 |
| 409 | `RD_DECISION_EXPIRED` | 决策请求已过期、已替代或不再绑定当前暂停聚合。 |
| 422 | `RD_DECISION_INPUT_INVALID` | decide 的 input 或 answers 的 answer/evidence 不满足冻结 Schema；返回字段级问题且不写部分状态。 |
| 409 | `RD_IDEMPOTENCY_CONFLICT` | 同一幂等键对应不同请求摘要。 |
| 409 | `RD_EXECUTION_POLICY_REQUIRED` | 产品/业务大脑缺少唯一 active 研发执行策略；`details` 返回 `product_id/brain_app_id/missing_policy_scope/retryable=false/next_action=configure_execution_policy`，工作项保持阻断且不创建 attempt。 |
| 409 | `RD_EXECUTION_POLICY_INVALID` | 策略 Schema、岗位/执行器绑定或 active 唯一规则不满足。 |
| 409 | `RD_ROLE_ASSIGNMENT_REQUIRED` | 冻结策略要求的岗位没有可用席位；`details` 返回 `missing_role_codes/eligible_subjects/retryable=false/next_action=assign_role_seat`，工作项保持阻断且不创建 attempt。 |
| 503 | `RD_EXECUTOR_UNAVAILABLE` | 已绑定执行器暂时不健康、无容量或 Runner 不可达；`details` 返回 `executor_profile_id/retryable=true/retry_after_seconds/next_action=retry_after_health_check`，不消费 attempt、不推进工作项。 |
| 409 | `RD_POLICY_HUMAN_DECISION_REQUIRED` | 需求评估的岗位意见或策略自动收紧存在不可确定解决的冲突；评估保持 `waiting_human`，`details` 返回 `decision_request_id/conflict_fields/retryable=false/next_action=resolve_policy_decision`。 |
| 409 | `RD_POLICY_RESOLUTION_LIMIT` | 策略自动收紧达到轮次上限仍不一致；评估保持 `waiting_human`，`details` 返回 `resolution_round/max_resolution_rounds/decision_request_id/retryable=false/next_action=resolve_policy_decision`。 |
| 409 | `RD_POLICY_IN_USE` | 策略已有不可变快照或运行引用，不能删除；可将策略停用。 |
| 409 | `RD_POLICY_SNAPSHOT_INVALID` | 快照缺失、内容哈希不一致或 `schema_version` 不受支持；失败关闭并要求人工迁移。 |
| 409 | `RD_COLLABORATION_DEPLOYMENT_DISABLED` | P1 协作部署能力标志关闭时创建、激活或重启 deployed 策略，或带协作运行创建部署单。 |
| 409 | `RD_DELIVERY_EVIDENCE_INCOMPLETE` | 协作运行不是带可信交付证据的 deployed-target `ready_for_release` 边界，或启动时该边界已失效。 |
| 409 | `RD_DEPLOYMENT_SCOPE_MISMATCH` | 部署单产品、版本或需求集合与协作运行冻结范围不完全一致。 |
| 409 | `RD_COLLABORATION_REQUIRED` | v2 研发写入被旧需求推进或公开 AI 任务创建/启动/重试/取消入口调用；`details` 固定返回 `entrypoint/retryable=false/next_action`，并按资源阶段返回可空的 `requirement_id/assessment_url/version_id/collaboration_run_id/work_item_id`。尚未评估或组版时 run/work-item 允许为 null，next_action 指向评估或版本协作；已关联任务时必须返回 run/work-item 并指向工作项命令。任务、Review、attempt、工作项和运行均不修改。 |
| 423 | `RD_UPGRADE_MAINTENANCE` | 研发写命令在 draining/cutover_locked 期间被围栏阻止；返回当前 mode/version，定时作业不使用此错误。 |
| 409 | `RD_UPGRADE_STATE_INVALID` | 围栏转换、cutover 或最终解除的活动量、备份、Schema、健康、cleanup、Worker 或冒烟前置条件不满足。 |
| 409 | `RD_UPGRADE_ABORT_NOT_ALLOWED` | 围栏已进入 `cutover_locked`、Schema v2 已激活或 cleanup 已开始，禁止回到旧写路径。 |
| 403 | `PERMISSION_DENIED` | 系统权限、产品范围、席位或审核隔离不满足。 |

集成工作项通过 Outbox 推送版本开发分支或创建/更新 MR/PR，并保存 repository/provider、工作分支、版本开发分支、目标分支、local/remote commit SHA、MR/PR ID 和状态、Outbox ID、执行身份、时间、对账状态与质量证据。`record_ready_for_release_evidence` 只验证每个必需仓库已有对账成功的远程证据，不在完成接口内临时执行 push，并把产品版本推进到 `ready_for_release`。随后 `finalize_ready_for_release_target` 按冻结策略分支：`delivery_target=ready_for_release` 时把运行推进为 `completed(completion_reason=ready_for_release)`；`delivery_target=deployed` 时运行保持非终态 `ready_for_release`，等待 P1 部署域继续推进，不写 `completion_reason`、不创建部署单。P0 能力标志关闭时 deployed 策略不能存在，因此 P0 测试只覆盖第一分支，但完成服务不得无条件关闭运行。

#### P1 策略控制的可选部署边界

只有版本已具备上述可信交付证据、协作运行处于 `ready_for_release`、策略快照明确 `delivery_target=deployed`、现有部署资源/权限/回滚/质量门禁均通过且人工发布确认完成时，才可在既有 `POST /api/devops/deployments` 请求中携带可选 `collaboration_run_id`。服务端必须在创建和启动时分别校验 P1 开关、运行的产品/版本、冻结需求集合、可信证据 ID/哈希和运行状态；创建时把运行外键和证据关联写入部署单门禁摘要及审计，启动时将部署请求/运行/步骤/Outbox/需求变更与协作运行、产品版本进入 `deploying` 放在同一持久化事务。客户端、LLM 或协作器都不能跳过已有 `deployment.create`、`deployment.execute`、产品范围和人工门禁。默认不携带该字段的 P0 部署流程不变，本分册不新增第二套部署接口。拒绝、失败、取消或回滚不抹除 P0 交付事实，版本保持或返回 `ready_for_release`，运行也回到 `ready_for_release` 等待处理；部署成功后运行进入 `completed(completion_reason=deployed)`。

### 一次性升级控制

```http
GET  /api/system/rd-collaboration-upgrade/preflight
POST /api/system/rd-collaboration-upgrade/maintenance-fence
POST /api/system/rd-collaboration-upgrade/cutover
```

维护围栏请求体：

```json
{
  "mode": "draining",
  "reason": "研发协同 2.0 契约切换",
  "version": 3,
  "expected_schema_version": 1,
  "health_marker": null
}
```

仅系统管理员可调用。`preflight` 是围栏外可重复执行的只读建议检查，不改变写路径。围栏请求使用 `mode=disabled|draining|cutover_locked`、`reason`、`version`、`expected_schema_version` 和可选 `health_marker`，不再使用模糊布尔 `enabled`。从 `disabled` 进入 `draining` 后，需求 approve/reject/direct-generate、AI 任务 start/retry、策略/协作/经验写入和 Runner 新领取返回 `423 RD_UPGRADE_MAINTENANCE`；已领取工作可提交终态回写，在途事务可以收敛，系统管理员可通过专用 drain 服务受控取消并记录审计，普通任务 cancel 仍被围栏阻断；定时作业运行不受影响。待活动 AI task、Agent Loop、Runner lease 和协作命令归零并生成备份标记后，服务端原子把围栏推进到 `cutover_locked`，随后重新执行锁内 preflight。cutover 只有在锁内 preflight 无阻断、备份确认、Schema 109 已应用且围栏为 `cutover_locked` 时执行策略转换、旧 draft 取消和 Schema v2 激活；新应用健康标记成功后才允许执行清理迁移 110。

在 `draining` 且 `rd_collaboration_schema_version < 2`、cleanup 尚未开始时，管理员可通过同一 maintenance-fence 端点提交 `mode=disabled/reason/version` 中止窗口；服务端乐观锁更新、写入 abort 审计并恢复旧写路径。围栏 `version` 过期统一返回 `RD_VERSION_CONFLICT`；其他转换或前置条件不满足返回 `RD_UPGRADE_STATE_INVALID`。进入 `cutover_locked`、Schema v2 已激活或 cleanup 已开始后，任何提前降级到 `disabled` 都返回 `409 RD_UPGRADE_ABORT_NOT_ALLOWED`，只能修复后向前重试。最终解除围栏同样使用 `mode=disabled`，但必须同时满足 Schema v2 已激活、迁移 110 已成功、v2 API 与协同 Worker 图版本一致、健康标记有效、v2 评估/协作写入冒烟检查通过。解除后新写路径恢复，旧 approve/generate/batch-delivery-advance/AI-task-create/start 写路径仍返回迁移错误。锁内预检、健康、清理、Worker 或冒烟检查任一步失败都保持 `cutover_locked` 并允许幂等重试。

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
  "supersedes_requirement_id": null,
  "source_collaboration_run_id": null,
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
- 待发布后的范围变化使用同一接口创建后续需求，并必填 `source_collaboration_run_id`；若是既有需求的延续或替代，再填写 `supersedes_requirement_id`。已填写的引用必须属于同产品，来源运行必须已达到待发布边界，且 supersedes 不得在缺少来源运行时单独出现；服务端保存真实外键和来源审计，旧需求、旧版本、旧运行与交付证据均不修改。后续需求仍从 `submitted` 开始独立评估，`input.version_id` 只能是新的 planning 候选，不能继承原需求 accepted 结论或直接加入旧版本。
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
  "detail": {
    "code": "RD_COLLABORATION_REQUIRED",
    "message": "Complete assessment and start the product-version collaboration run",
    "details": {
      "entrypoint": "requirement.batch-generate-tasks",
      "requirement_id": null,
      "assessment_url": "/delivery/requirements/assessment",
      "version_id": null,
      "collaboration_run_id": null,
      "work_item_id": null,
      "retryable": false,
      "next_action": "open_requirement_assessment"
    },
    "trace_id": "trace_xxx"
  }
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
  "detail": {
    "code": "RD_COLLABORATION_REQUIRED",
    "message": "Start work through the product-version collaboration run",
    "details": {
      "entrypoint": "ai_task.create",
      "requirement_id": "requirement_001",
      "assessment_url": "/delivery/requirements/requirement_001/assessment",
      "version_id": "version_001",
      "collaboration_run_id": null,
      "work_item_id": null,
      "retryable": false,
      "next_action": "open_rd_collaboration"
    },
    "trace_id": "trace_003"
  }
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

公开取消只保留给未关联 v2 协作工作项的历史任务。单个任务一旦存在 `collaboration_run_id` 或 `work_item_id`，返回 `409 RD_COLLABORATION_REQUIRED`，响应给出 `collaboration_run_id/work_item_id` 和工作项取消或人工决策入口，任务、Review、attempt、工作项和运行均不改变。批量请求只要命中一个 v2 协作任务，整批返回 `409 RD_COLLABORATION_REQUIRED`，不得取消其余历史任务形成部分成功；调用方须拆分历史任务或改走协作入口。

非协作历史任务仍允许取消 `draft`、`running`、`waiting_more_info`、`waiting_review` 和 `writing_back`；`completed`、`failed`、`cancelled` 等终态任务、重复任务 ID 和不存在的任务进入 `skipped`。成功任务同步取消待处理 Review，并写入逐任务 `ai_task.cancelled` 审计；批次完成后写入 `ai_task.batch_cancelled` 审计。

v2 协作任务的取消由工作项取消命令或人工决策服务处理，必须在同一数据库事务：校验工作项和运行版本，停止/回收 Runner 租约，关闭当前 attempt，取消 pending Review 和 AI task，推进工作项为 `cancelled`，重新计算下游依赖和运行是否需要 `waiting_human/failed/cancelled`，写入协作事件和审计。任一步失败则全部回滚。

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
  "detail": {
    "code": "RD_COLLABORATION_REQUIRED",
    "message": "Retry the failed attempt through its collaboration work item",
    "details": {
      "entrypoint": "ai_task.batch-retry",
      "requirement_id": "requirement_001",
      "assessment_url": null,
      "version_id": "version_001",
      "collaboration_run_id": "rd_run_001",
      "work_item_id": "rd_work_item_001",
      "retryable": false,
      "next_action": "open_rd_work_item"
    },
    "trace_id": "trace_006c"
  }
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
