# AI Brain 2.0 产品需求驱动的研发协同设计

## 文档状态

- 状态：已按最终 Review 结论收口，Ready for Development
- 日期：2026-07-16
- 适用范围：AI Brain 2.0 研发任务
- 不影响范围：现有定时作业定义、调度、锁、重试、AI角色/Skill 装配和运行历史；代码巡检“创建整改任务”结果动作仅把业务写入目标改为正式需求

## 背景

AI Brain 当前已经具备产品、迭代版本、需求、AI 任务、研发执行器策略、Runner、Agent 自治循环、质量门禁、人工确认、Git 写回和运维部署等基础能力，但当前主链路仍以单个 `ai_task` 为执行中心，需求审批前的评估仅作为轻量预览，研发执行器策略也主要解决“某类任务交给哪个工程 Runner”。

AI Brain 2.0 需要把研发任务升级为由产品需求驱动的混合团队协同：真人与 AI 数字员工共同占据岗位，系统把复杂目标拆为带负责人、审核人和依赖关系的工作项，支持并行、交接、审核、返工、人工升级和经验沉淀。研发可以在开发测试完成后结束，也可以继续推进部署，具体由版本采用的研发执行策略决定。

本设计是对当前研发流程的 2.0 一次性升级方案，不保留新旧研发规则并行。后续实施时同步更新项目级 PRD、技术规格、API、测试用例、帮助文档和变更记录。

## 已确认的产品决策

1. 产品需求是研发任务的唯一业务起点。
   Bug、代码巡检整改、用户反馈和线上异常如果需要进入研发，也必须先创建或关联正式产品需求，再进入同一评估与组版流程。
2. 需求必须先完成评估，评估通过后才能进入迭代规划。
3. 评估通过的需求优先组合到同产品的规划中版本；没有合适版本时再创建新的规划中版本。
4. 研发协同只作用于研发任务；现有定时作业引擎不变，已有直接创建研发任务的结果动作通过需求适配器改为创建或关联需求。
5. LLM 负责语义理解、拆解、评估、方案和建议；确定性协同引擎负责状态、调度、依赖、权限、预算、幂等和门禁；高风险或越权问题交给真人。
6. 岗位与员工分离。岗位可以动态增加，岗位上的员工可以是真人账号、AI 数字员工或混合候选池。
7. 每个 AI 岗位使用的执行器由研发执行策略配置决定，LLM 不得绕过策略自行更换执行器。
   这里的研发执行策略是对现有“研发执行器策略”的 2.0 原位升级，不新增并列策略入口。
8. 是否推进部署由研发执行策略决定；高风险和生产部署仍受不可降级的人工确认与质量门禁约束。
9. 研发成果至少可交付到开发测试完成、代码推送到远程研发分支；不允许未经授权自动修改受保护分支。
10. 任务反馈必须尽量归因到具体岗位、员工、执行器、工作项和尝试，为后续策略优化和经验沉淀提供依据。

## 规范化领域契约

本节是数据库、API、服务、测试和页面必须共同使用的唯一命名口径；后文出现的概念均以本节为准。

### 业务流程顺序

```text
requirement.submitted
-> requirement_assessment.evaluating
-> accepted（自动或人工决策）
-> requirement.approved
-> 自动/人工确认组入 planning 版本
-> requirement.planned
-> 以 product_version 为根创建 rd_collaboration_run
```

原需求 `approve/reject/generate-task/batch-generate-tasks` 不能继续作为绕过评估的业务入口。高风险需求的人工批准或拒绝通过评估决策完成；评估 accepted 后由领域服务原子推进需求为 `approved`，组版成功后推进为 `planned`。

### 表和聚合命名

- 评估：`requirement_assessments`、`requirement_assessment_opinions`。
- 策略与组织：`rd_task_executor_policies`、`rd_task_executor_policy_role_bindings`、`rd_task_executor_policy_snapshots`、`rd_role_definitions`、`rd_ai_employees`、`rd_executor_profiles`。
- 协作：`rd_collaboration_runs`、`rd_scope_change_requests`、`rd_scope_change_request_operations`、`rd_run_seats`、`rd_role_sessions`、`rd_work_items`、`rd_work_item_dependencies`、`rd_work_item_attempts`、`rd_collaboration_events`。
- 人工决策与经验：`decision_requests`、`rd_command_idempotency_records`、`role_feedback_records`、`rd_role_experience_records`、`rd_role_experience_sources`。
- 升级：`rd_collaboration_upgrade_state`。
- 版本是协作聚合根：同一产品版本同一时刻最多一个非终态 `rd_collaboration_run`；一个运行包含版本冻结范围内的多条需求。

### 规范状态

```text
requirement_assessment:
draft | evaluating | waiting_human | needs_info | rework_required |
accepted | deferred | rejected | failed | cancelled

rd_collaboration_run:
draft | planning | running | integrating | verifying | waiting_human |
ready_for_release | deploying | completed | failed | cancelled

rd_scope_change_request:
pending_decision | applied | rejected

rd_work_item:
queued | waiting_dependencies | ready | running | blocked | awaiting_human |
awaiting_review | rework_required | approved | failed | cancelled

decision_request:
pending | waiting_more_info | approved | rejected | expired | cancelled

rd_role_experience_record:
pending | approved | rejected | retired
```

领取租约不是单独业务状态；原子领取成功后工作项从 `ready` 进入 `running` 并保存 lease。返工不得覆盖原 attempt：同一范围内的返工从 `rework_required` 回到 `ready` 并在下次领取时创建新 attempt；需要改变目标、依赖或负责人时创建新 `plan_version` 和替代工作项。

### 规范 API 根路径

- 评估：`POST /api/requirements/{requirement_id}/assessments`、`GET .../assessments/latest`、`POST /api/requirement-assessments/{assessment_id}/opinions|answers|decisions`。
- 研发组织：`GET/POST/PATCH /api/delivery/rd-roles|rd-ai-employees|rd-executor-profiles`。
- 版本协作：`POST /api/product-versions/{version_id}/collaboration-runs`、`POST /api/product-versions/{version_id}/collaboration-runs/restart`、`POST /api/product-versions/{version_id}/scope-change-requests`、`GET /api/delivery/rd-scope-change-requests/{scope_change_request_id}`、`GET /api/delivery/rd-collaboration-runs/{run_id}`。
- 需求只读定位：`GET /api/requirements/{requirement_id}/collaboration-run`，返回需求所属版本的活动或最近运行，不创建运行。
- 工作项：`GET /api/delivery/rd-collaboration-runs/{run_id}/work-items` 以及 `/api/delivery/rd-work-items/{work_item_id}/claim|submit|review|cancel`。
- 决策：`POST /api/delivery/decision-requests/{decision_request_id}/decide|answers`。
- P1 经验：`GET /api/delivery/rd-role-experiences`、`GET /api/delivery/rd-role-experiences/{experience_id}`、`POST /api/delivery/rd-role-experiences/{experience_id}/decide`。
- 升级：`GET /api/system/rd-collaboration-upgrade/preflight`、`POST .../maintenance-fence`、`POST .../cutover`。

公开的需求批量状态推进、AI 任务创建、启动、取消和批量重试接口不再是 v2 交付入口。`batch-advance-status` 对 `planned/designing/ready_for_dev/developing/code_reviewing/testing/ready_for_release/deploying/released/accepted` 等交付状态统一返回 `RD_COLLABORATION_REQUIRED`；它只保留在既无活动协作运行、也不存在非终态工作项时批量 `cancelled/closed` 的管理用途。外部调用 `POST /api/ai-tasks`、`/api/ai-tasks/{id}/start` 或 `/api/ai-tasks/batch-retry` 同样返回 `RD_COLLABORATION_REQUIRED`。`POST /api/ai-tasks/{id}/cancel` 和 `/api/ai-tasks/batch-cancel` 一旦命中关联 `collaboration_run_id/work_item_id` 的 v2 任务，整次请求返回 `RD_COLLABORATION_REQUIRED` 且不得部分取消；取消只能由工作项取消或人工决策领域服务原子推进任务、Review、attempt、工作项和运行。协作编排器直接调用内部领域服务创建、派发、恢复和取消关联工作项的 AI 任务，不通过真人角色或公开 HTTP 绕行。

### 统一策略写契约

策略 API 只接受一套顶层配置：`name/brain_app_id/product_id/status/matching_config/assessment_config/iteration_config/delivery_target/team_config/autonomy_config/quality_gate_config/git_config/experience_reuse_config/deployment_config/role_bindings`。主记录增加服务端维护的 `policy_version`，创建为 1；PATCH 必须提交乐观锁 `expected_policy_version`，运行解释发生任何变化后递增并返回新版本。`role_bindings[]` 是岗位绑定数组；数据库保存到 `rd_task_executor_policy_role_bindings`。同一业务大脑/产品最多一条 active 产品策略，同一业务大脑最多一条 `product_id=null` active 默认策略；产品策略优先，多个候选直接阻断。不再使用旧顶层 `task_type/executor_type/runner_id`，也不并存 `version_grouping_config`、`required_roles`、`role_executor_bindings` 等第二套同义字段。

## 目标

- 建立从需求评估、迭代组版、产品设计、技术方案、开发、审核、测试到可选部署的完整研发协同链路。
- 让简单、低风险且证据充分的工作自动推进，让高风险、越权、低置信度或存在冲突的工作进入人工决策。
- 让多个 AI 与真人岗位围绕同一版本并行协作，同时保证依赖、隔离、审核和集成可控。
- 通过版本化研发执行策略统一控制团队编制、岗位执行器、预算、质量门禁、Git 交付和部署终点。
- 复用现有 `ai_tasks`、Runner、Agent Loop、质量门禁、人工确认、Outbox 和部署治理能力，避免重建执行底座。
- 保存计划、执行、审核、返工、决策、证据和经验的完整审计链。

## 非目标

- 不改变现有 `scheduled_jobs` 和 `scheduled_job_runs` 的领域模型及运行流程；代码巡检整改结果仅通过需求适配器改变目标业务对象。
- 不允许 LLM 直接修改业务状态、权限、预算、仓库边界或部署范围。
- 不允许编码 Agent 审核自己的产物，也不把 Runner 自报成功视为独立质量证据。
- 不要求所有需求都单独创建迭代版本。
- 不允许研发执行策略绕过平台安全底线、生产审批、受保护分支和部署资源授权。
- 不在本设计阶段实现代码或改变当前线上行为。

## 确定方案

保留现有研发执行策略的产品概念、菜单、权限和 API 根路径，直接改造 `rd_task_executor_policies`。升级后的每条策略都使用同一种新模型：主记录负责匹配范围、版本目标、需求评估、自动化边界、团队编制、质量门禁、Git 和部署规则；岗位绑定、策略版本和快照子表负责岗位到执行器、Runner、模板和预算。

现有记录一次性转换为新结构：原 `task_type/executor/runner/指令模板` 数据转入岗位执行器绑定，新主策略补齐需求评估、组版、生命周期、团队、Git 和部署规则，旧顶层字段随后删除。历史任务中已经冻结的执行快照仅作为审计事实保留，不再参与策略解析；迁移完成后所有新启动任务和版本只执行新规则。

## 总体架构

```text
产品需求
  -> 需求完整性校验
  -> 按产品、需求类型和优先级解析初始研发执行策略
  -> 多岗位需求评估
  -> 按最终风险和所需能力复核研发执行策略
  -> 评估决策
       accepted       -> 迭代候选池
       needs_info     -> 等待补充后重评
       rework_required-> 修改需求后重评
       deferred       -> 延期池
       rejected       -> 关闭或保留记录
  -> 迭代规划
       优先匹配规划中版本
       无合适版本 -> 创建规划中版本
  -> 冻结研发执行策略快照
  -> 研发协同运行
       产品设计 -> 技术方案 -> 开发计划
       -> 并行开发 -> 独立 Review -> 集成 -> 测试 -> 发布就绪门禁
  -> delivery_target
       ready_for_release -> 产品版本停在待发布；协作运行 completed(reason=ready_for_release)，不创建部署任务
       deployed          -> 协作运行停在 ready_for_release -> 部署申请 -> 审批/门禁 -> 部署 -> 验证 -> completed(reason=deployed)
  -> 反馈归因与经验候选
```

### 控制层分工

| 控制层 | 负责 | 不负责 |
|---|---|---|
| LLM 岗位 | 理解需求、语义评估、拆解工作项、依赖建议、方案、总结、重规划建议 | 直接改状态、授予权限、突破预算、选择策略外执行器、放行高风险动作 |
| 确定性协同引擎 | 状态机、DAG 校验、调度、租约、并发、权限、风险下限、幂等、预算、门禁、事件和审计 | 代替产品负责人做业务价值取舍 |
| 真人 | 范围、优先级、高风险、越权、预算扩展、低置信度、冲突和生产动作决策 | 承担所有低风险日常推进 |
| Runner 与工具 | 执行代码、测试、文档、扫描、Git 和受控部署动作 | 自行改变工作范围或宣称独立验证通过 |

LLM 的输出始终是结构化提案。命令处理器完成 Schema、权限、版本、状态和策略校验后，才能将提案转化为正式业务状态。

## 领域边界

### requirement_assessment

负责需求评估运行、岗位意见、证据、评分、决策结果和重评版本。评估运行拥有独立状态，不直接扩张现有需求状态枚举；需求列表通过读模型展示当前评估阶段。它不生成正式研发代码任务，也不直接执行部署。

### iteration_planning

负责把评估通过的需求优先组合到规划中版本，没有合适版本时提出或创建新的规划中版本。它不修改已经冻结或交付中的版本范围。

### rd_task_executor_policy

这是现有研发执行策略的 2.0 形态，继续负责任务到执行器的匹配，并扩展负责版本级生命周期终点、岗位编制、岗位执行器、自治预算、质量门禁、Git 规则、部署模式和人工确认规则。

### rd_role_definition

负责研发业务岗位定义，例如产品经理、技术负责人、前端开发、后端开发、测试、文档、集成和运维。研发岗位与系统 RBAC 角色是两个独立概念：岗位描述职责、能力、交付物和审核关系；系统 RBAC 角色继续控制真人账号的菜单、操作权限和数据范围。新增研发岗位不会自动创建系统权限或扩大任何真人账号权限。

### rd_ai_employee

负责 AI 数字员工的持久化身份、名称、所属业务大脑、能力标签、人格/工作风格版本、状态和跨运行经验归因。AI 数字员工不是执行器：同一员工可以在不同策略快照中使用不同的授权执行器，同一执行器也可以服务多个员工。策略决定某次运行实际使用的执行器、工具、预算和信任域；员工身份只描述“谁在承担工作”，不能自行带来权限或覆盖策略。

### rd_collaboration

负责研发协同运行、工作项 DAG、岗位分配、领取租约、交接、审核、返工、阻塞、重规划和完成判定。

### ai_task_execution

沿用现有 `ai_tasks`、Agent Loop、Runner 和质量门禁完成单个 AI 工作项的实际执行。该领域不决定版本是否部署。

### deployment_orchestration

复用现有部署申请、质量门禁、部署 Runner、健康检查和回滚能力。只有研发执行策略允许时才能从研发协同进入该领域。

### scheduled_jobs

保持现有定时作业边界。定时作业可以继续共享模型网关或 Runner 基础设施，但不创建研发协同运行、不参与需求评估和迭代组版，也不读取研发执行策略。

## 原工作流引擎复用

2.0 不新建另一套工作流引擎，继续使用现有 LangGraph 运行时、Graph Run、Checkpoint、人工中断恢复、Agent Loop、Runner 和质量门禁。新增的是运行在原引擎之上的版本级协同图和确定性调度能力。

### 版本级协同图

在现有 LangGraph 运行时中新增 `rd_collaboration_graph`，负责版本研发主阶段：

```text
plan_work_items
-> validate_plan
-> dispatch_ready_items
-> wait_work_item_events
-> integrate
-> record_ready_for_release_evidence
-> finalize_ready_for_release_target
-> completed_at_ready_for_release OR wait_at_ready_for_deployment
```

协同图只推进阶段和生成命令，不把所有并行工作塞进单个 LLM 上下文。工作项、依赖、席位、租约、尝试和事件仍持久化在 PostgreSQL，由确定性调度器计算可运行节点；当工作项完成、阻塞、返工或人工决策返回时，以事件唤醒原 LangGraph 运行并从 Checkpoint 恢复。

### 工作项执行图

每个 AI 工作项继续创建现有 `ai_task`，复用当前任务启动、上下文检索、输出生成、人工确认和恢复流程。编码类工作项继续复用 Agent Loop 的计划、执行、验证、反思和重试，以及现有 Runner、执行上下文、预算和独立质量门禁。

### 运行态和持久化复用

- 现有 `graph_runs/graph_checkpoints` 抽象扩展为可关联 `ai_task` 或 `rd_collaboration_run`，并保存图定义、图版本、稳定 `thread_id` 和业务主体；已有任务运行记录继续可查询。
- 现有 `human_reviews` 继续处理单个任务产物审核。
- 跨工作项的组版、范围、权限、预算、重组和部署决策使用 `decision_requests`，决策结果通过原工作流中断/恢复机制继续运行。
- 现有 Graph Run 的节点路径、当前步骤、状态快照、运行状态和审计继续保留。
- 现有 Agent Loop、质量门禁、Runner 租约、Outbox 和人工接管机制不重复实现。

### 持久化 Checkpointer 升级

当前单任务图是同步固定图，Checkpoint 主要由业务服务写入。2.0 复用 LangGraph 技术栈，但必须把运行能力升级为 PostgreSQL 持久化 Checkpointer 和真实的 interrupt/resume：

- `ai_task_graph` 和 `rd_collaboration_graph` 编译时统一装配 PostgreSQL Checkpointer。
- 每个 Graph Run 使用稳定 `thread_id`，Checkpoint 按图版本和业务主体隔离。
- 等待人工、工作项、Runner、质量门禁或部署结果时执行真实中断，不用进程内等待或轮询保持上下文。
- 人工决策和协同事件携带幂等事件 ID，先写入持久化 Inbox/`rd_collaboration_events`，再通过 Outbox 唤醒 Graph Run，并从最后成功 Checkpoint 恢复。
- PostgreSQL 领域表和事件 Inbox 是业务事实源。消费事件、推进业务状态、审计和待派发 Outbox 在领域事务中原子提交；官方 Checkpointer 可以使用独立连接提交执行游标，不宣称与领域事务跨连接原子提交。
- Graph 节点每次恢复都重新读取领域状态，只提交带幂等键的领域命令。若业务事务已成功而 Checkpoint 写入失败，重复恢复会读取已完成命令并安全前进；若 Checkpoint 已写而业务命令失败，事件仍保持可重试且节点不会把 Checkpoint 当作业务完成证据。
- 同一事件 ID、领域命令幂等键和 Outbox 幂等键形成三层去重；重复事件只返回已有结果，不重复派发 Runner、Git 或部署副作用。
- Checkpoint 恢复失败、图版本不兼容或事件缺失时进入人工接管，不允许从头静默重跑。

### 不直接复用的部分

当前 `ai_task_graph` 是面向单任务的固定线性图，不能单独表达版本级动态工作项 DAG、多人席位、并行依赖和重规划。因此保留它作为工作项执行图，同时在同一 LangGraph 工作流引擎内新增版本级协同图，而不是强行把整个版本伪装成一个超大 `ai_task`。

定时作业调度引擎不参与上述复用，继续走现有独立路径。

## 需求评估

### 评估前置校验

系统先确定性检查：

- 产品、模块、需求标题和描述存在。
- 业务目标、范围、非目标和验收标准达到最低完整度。
- 创建者具备产品范围权限。
- 外部引用和附件可访问且不越权。
- 同产品中是否存在明显重复需求。

校验失败时不调用多个评估 Agent 空转，而是创建信息补充请求。

校验通过后、调用评估岗位前，系统先解析初始研发执行策略。初始匹配只能使用业务大脑、产品、需求来源或类型、人工填写的优先级等稳定输入，不能依赖尚未产生的 AI 风险、置信度或工作量结论。初始策略快照决定参与评估的岗位、岗位执行器、评估 Schema、预算、自动通过阈值和人工门禁；未命中策略时需求停在待配置状态。

### 多岗位评估

| 岗位 | 必须输出的结构化意见 |
|---|---|
| 产品经理 | 用户价值、业务目标、范围、验收完整度、建议优先级 |
| 技术负责人 | 技术可行性、影响系统、依赖、技术风险、粗粒度工作量 |
| 开发岗位 | 改动模块、实现复杂度、并行机会、仓库和环境要求 |
| 测试岗位 | 可测试性、验收覆盖、测试数据、环境和自动化可行性 |
| 项目负责人 | 周期、容量、岗位需求、版本建议和交付风险 |
| 运维岗位 | 仅在候选策略可能部署时评估部署、观测和回滚要求 |

每个岗位意见保存 `role_code`、`actor_id`、`executor_profile_id`、输入上下文版本、结论、证据、置信度、风险、耗时和成本，避免只保存合并后的自然语言总结。

### 评估决策

需求记录在评估期间保持 `submitted`，评估运行使用独立状态：

```text
requirement_assessment:
draft -> evaluating -> accepted | waiting_human | needs_info | rework_required | deferred | rejected | failed
evaluating -> waiting_human -> accepted | needs_info | rework_required | deferred | rejected
needs_info/rework_required -> evaluating（创建新评估版本）

requirement:
submitted + assessment.accepted -> approved
submitted + assessment.deferred -> deferred
submitted + assessment.rejected -> rejected
approved + iteration assignment -> planned
```

评估接口职责必须完整且互斥：`opinions` 由被分配的真人评估者或受控 AI 评估执行单元提交结构化岗位意见；`answers` 由需求负责人补充事实并触发新的需求/评估版本；`decisions` 只接受 `accept/reject/request_more_info/request_rework/defer`，使用乐观锁并分别映射到规范评估状态。评估请求 Schema 不定义 `strategy_id`，任何账号都不能在评估命令内改写匹配结果。需要调整策略时，有策略管理权限的用户必须先更新统一产品策略或业务大脑默认策略、形成新 `policy_version`，再重新评估受影响需求；人工决策可以选择“修改统一策略后重评”，但不能携带候选策略直接继续当前评估。

需求页面可以通过 `evaluation_gate_status` 读模型展示“评估中、待人工、待补充、需修改、已通过、已延期、已拒绝”，但不能把这些投影误写回 `requirements.status`。现有直接 approve/reject 操作在 2.0 页面移除；对应旧 API 返回迁移提示，人工业务决策统一写入评估和 `decision_requests`。

简单、低风险、置信度和完整度达到策略阈值的需求可以自动进入 `accepted`。以下情况必须人工决策：

- 风险为 `high/critical`。
- 涉及敏感数据、权限、资金、合规、生产环境或不可逆迁移。
- 岗位意见冲突超过策略阈值。
- AI 置信度不足。
- 建议拒绝、关键延期或显著改变原始范围。
- 预计投入超过策略预算。

最终风险取确定性规则风险下限与 LLM 语义风险的较高值，LLM 不得降低规则风险。

评估意见形成后，系统使用最终风险、所需能力、仓库范围、预计投入和交付约束再次解析并校验策略。策略复核采用单调收紧规则：

- 仍命中原策略时，将其作为迭代规划候选策略。
- 自动切换只允许降低自动化程度、降低风险阈值、收紧权限/仓库/工具范围、增加门禁或必需岗位、缩短自治预算、把部署终点从 `deployed` 收紧为 `ready_for_release`；反向变化一律不是自动收紧。
- 更严格策略新增必需评估岗位时创建同一评估版本的新意见轮次，补齐意见后再次复核；最多自动收紧两轮，超过两轮进入人工决策，避免策略循环。
- 两条策略在不同维度各有松紧时视为不可比较；多个策略冲突，或变化涉及扩大权限、提高自动化程度、提高预算、减少门禁或从待发布改为部署时，必须交给真人确认。
- 已有岗位意见只有在输入上下文版本、输出 Schema 和岗位职责仍兼容时才能复用，否则必须重评。
- 不允许根据 LLM 结论自动降级风险、放宽权限或改用更宽松策略。

## 迭代版本组合规则

### 硬性候选条件

只有同时满足以下条件的版本才是候选：

- 与需求属于同一产品。
- 版本状态为 `planning`。
- 尚未冻结范围或启动研发协同运行。
- 版本采用的研发执行策略与需求所需能力兼容。
- 版本目标时间、仓库范围和交付终点不冲突。
- 加入需求后不超过策略配置的容量硬上限。
- 不违反需求依赖和互斥约束。

### 候选评分

迭代规划 LLM 可以对候选版本给出语义建议，确定性引擎按可解释评分排序：

- 目标时间匹配度。
- 业务主题和模块聚合度。
- 与已排期需求的依赖亲和度。
- 优先级和版本目标一致性。
- 剩余容量。
- 仓库、环境和交付策略一致性。

### 组合决策

1. 存在唯一合格候选且评分达到策略阈值时，自动加入该规划中版本。
2. 多个候选分数接近、存在范围争议或超过软容量时，交给产品负责人选择。
3. 没有合格候选时，根据产品版本命名规则生成新的 `planning` 版本。
4. 高风险或重大需求即使没有候选，创建新版本前也必须人工确认。
5. 组版操作使用需求 ID、评估版本和规划周期生成幂等键，并对需求和候选版本加事务锁，避免并发重复排期或重复建版。
6. 已经进入 `active/testing/ready_for_release/deploying` 的版本不能由自动组版追加范围；存在非终态协作运行时范围完全冻结。运行仍在 `draft/planning/running/integrating/verifying/waiting_human` 时，变更只能通过受控 scope-change 请求和人工决策原子终结旧运行、应用类型化 operations 并递增一次 scope，再由显式 restart 创建新 generation；已进入 `ready_for_release/deploying` 时不得回退或 restart，变更必须创建后续需求并进入新的 planning 版本。

评估 `accepted` 只保证需求进入 `approved`。若候选并列、高风险新建版本或人工调整版本归组尚未决策，需求保持 `approved` 并关联 `decision_request`；只有版本选择或新建决策成功后才进入 `planned`，不能把“评估通过”误写成“组版已完成”。

需求评估通过后使用复核完成的研发执行策略。已有规划中版本只有在版本内全部需求解析到同一 `policy_id/policy_version`，且各需求 final 快照可按版本合并规则确定性收紧时才参与评分。负责人不能在版本上选择任意策略；需要调整时只能通过统一策略 API 修改 active 产品策略或业务大脑默认策略、形成新 `policy_version`，再重新评估受影响需求。研发协同正式启动后，版本级策略快照冻结。

### 版本级协作聚合与范围冻结

- `product_version` 是协作聚合根，版本可包含多条评估通过并已排期的需求；不为每条需求分别创建版本级运行。
- `product_versions.scope_version bigint NOT NULL DEFAULT 1` 是范围并发事实源。只有在无非终态运行时，需求加入、移除、改派，纳入需求修订/验收标准/final-effective 策略快照变化，以及冻结仓库/分支基线变化才能在版本行锁事务中接受并递增；展示字段修改不递增。版本列表/详情、归组结果、范围预览和冲突响应都返回当前值。
- 启动入口是 `POST /api/product-versions/{version_id}/collaboration-runs`。服务端对版本加事务锁，并以“版本 ID + 范围版本 + 不可变策略快照 ID”生成幂等键，同时校验快照哈希；并发重复启动返回同一活动运行。
- 启动前必须校验版本仍为 `planning`、至少包含一条 `planned` 需求、版本内所有纳入需求的最新评估均为 accepted、策略和岗位资源完整。
- 启动时先校验所有需求 final/effective 快照属于同一 `policy_id/policy_version`，再由确定性合并器生成 `snapshot_kind=version_resolved` 的运行级快照：允许清单取交集、禁止项/必需岗位/门禁/人工确认点取并集、自动化/风险/超时等上限取更严格值、任一来源要求 `ready_for_release` 时版本终点即为 `ready_for_release`；预算按基础运行总上限和各需求预算清单共同冻结。`experience_reuse_config` 的 enabled 取 AND、最低置信度取最大、条数/Token/时效上限取最小、仓库/工具信任域取交集、策略兼容级别取最严格规则、独立审核取 OR。Schema 中未声明 merge operator 的字段必须完全相同，不可比较或冲突时创建决策请求并阻止启动；选项只允许拆分/移出需求、修改统一策略后重新评估或取消，不能人工提交任意 merged payload/版本显式策略。`rd_task_executor_policy_snapshot_sources` 按 requirement 唯一地关联版本快照与每个 assessment final/effective 快照，不能用单 parent 冒充多来源。
- 启动时在同一事务创建不可变 `rd_collaboration_run_requirements`，逐条冻结 `requirement_id/requirement_revision/assessment_id/final_strategy_snapshot_id/acceptance_criteria_hash/repository_scope_hash`；同时冻结 `scope_version`、仓库基线、`version_resolved` 策略快照和岗位编制，并把版本推进为 `active`。延迟约束触发器要求运行范围非空、source count 等于范围行数、两组 requirement 集合无缺失无多余且 assessment/snapshot 逐条一致。自动组版从此不再向该版本追加需求。
- 运行中普通入口新增/移除需求、切换需求修订/验收/final 快照或改变仓库分支都命中 `RD_SCOPE_FROZEN`，不能只创建新 `plan_version` 或原地替换范围。待发布前唯一变更入口为 `POST /api/product-versions/{version_id}/scope-change-requests`：请求携带 `request_id/expected_scope_version/expected_run_generation/source_run_id/reason/operations`，operations 只允许增删需求、替换需求快照、更新仓库基线的类型化引用。服务端先验证提议范围，再写 `rd_scope_change_requests(status=pending_decision, source_run_state=当前状态)` 并展示范围、依赖、预算、分支和门禁影响；running/integrating/verifying 使用运行 waiting_human 暂停字段，draft/planning 由 pending 请求围栏继续调度，failed/cancelled 不改变终态，已有其他 waiting_human 决策时拒绝覆盖。同版本最多一个待决请求。
- 批准范围变更时，决策服务在同一锁事务中重校验 scope/generation/hash，先按旧 generation 撤销租约/replay secret，终结全部非终态工作项、attempt、pending Review 和关联 AI task，取消未派发 Outbox，并为已派发 Runner/Git 动作写取消/对账 Outbox；再终结旧运行为 `cancelled(scope_change)`、应用全部 operations、仅递增一次产品 `scope_version`、保存 `applied_scope_version`，返回 `terminal_run_id` 供调用方显式 restart 新 generation。部分失败整体回滚，迟到回写只进审计/对账，新代次使用隔离 worktree/分支。拒绝时只按运行保存的 `resume_state` 恢复由本请求暂停的原阶段，范围和版本不变。已进入 `ready_for_release/deploying/released` 或 ready-target 已完成时不创建范围请求，只允许通过标准需求接口创建必带 `source_collaboration_run_id`、可选 `supersedes_requirement_id` 的后续需求并进入新 planning 版本；旧需求、旧运行和交付证据保持不可变。
- 运行进入 `failed/cancelled` 后终态不可重开，产品版本保持失败时的 `active/testing` 阶段。显式 `POST .../collaboration-runs/restart` 仅在旧运行是同版本最近一代、没有活动运行、当前 scope/policy/repository/roles/budget 重新校验通过时，创建 `run_generation+1`、`supersedes_run_id=旧运行` 的新运行、新范围行和新计划。只允许把与当前范围、策略、commit 和门禁仍兼容的 approved 历史证据作为只读输入复用；未完成工作、attempt 和租约必须新建，旧运行不更新。
- 需求详情只定位其所属版本的活动或最近协作运行，不能用需求接口创建第二个版本级运行。

### 新版本最低内容

- 产品、版本编号、名称和目标。
- 纳入需求和明确非目标。
- 预计开始、测试和交付时间。
- 版本验收标准。
- 仓库、目标基线和分支规则。
- 从需求评估只读汇总出的统一 `policy_id/policy_version` 和可合并性结论；版本不能配置显式策略，正式 `version_resolved` 快照在研发协同启动时冻结。
- 所需岗位编制、容量和风险摘要。
- `delivery_target`。

## 研发执行策略

### 现有策略的 2.0 主配置

现有 `rd_task_executor_policies` 原位升级，所有策略使用统一 Schema，并增加以下版本级配置：

| 配置组 | 核心内容 |
|---|---|
| 匹配范围 | 业务大脑、产品、需求类型、风险、优先级、版本类型、优先级和状态 |
| 需求评估 | 必需评估岗位、自动通过阈值、冲突阈值、人工门禁 |
| 迭代组版 | 容量、候选评分阈值、是否允许自动建版、版本命名规则 |
| 生命周期 | `delivery_target=ready_for_release/deployed` |
| 团队编制 | 必需岗位、可选岗位、审核隔离、动态增岗规则 |
| 自治治理 | 最大轮次、时长、Token、费用、无进展阈值和人工接管 |
| 质量门禁 | 设计、开发、合并前、测试、部署前和部署后门禁 |
| Git 交付 | 仓库、分支模板、提交方式、PR/MR、受保护分支和推送权限 |
| 经验复用 | `enabled`、最低置信度、策略兼容级别、最大条数/上下文 Token/时效、仓库/工具信任域和独立审核要求 |
| 部署 | 模式、环境、资源、窗口、审批、验证和回滚规则 |

策略匹配优先级固定为：产品专属 active 策略 > 业务大脑 active 默认策略。版本不保存、不接受显式策略覆盖。确定主策略后，再按工作项岗位和任务类型选择该策略下唯一有效的岗位执行器绑定。出现多个 active 主策略或同一岗位同时命中多个绑定时，不得随机选择，应阻断并提示配置冲突。

产品如果没有命中可用研发执行策略，或者策略缺少当前工作项所需的岗位执行器绑定，必须阻断组版确认或协同启动并提示配置，不得静默使用策略外的模型网关或执行器。

`experience_reuse_config` 默认 `enabled=false`。P1 只有在平台 `RD_ROLE_EXPERIENCE_ENABLED` 和运行冻结配置同时开启时才检索经验；P0 允许配置缺省并规范化为安全默认值。空仓库/工具信任域按 deny-all；`same_policy_version` 要求来源与当前策略 ID/version 相同，`same_policy_schema` 仍限定同业务大脑、同产品、同 schema_version 且经验约束不宽于当前策略。来源生产者隔离始终生效；`require_independent_reviewer=true` 时额外要求审核岗位/席位与所有来源岗位/席位分离。多需求合并必须使用上文保守 operator，不能因任一需求放宽置信度、信任域、时效、容量或策略兼容边界。

### 研发执行器档案

岗位绑定引用统一的研发执行器档案，而不是把岗位等同于某种 Runner。执行器档案至少支持：

| 执行类别 | 适用岗位 | 典型底座 |
|---|---|---|
| `semantic` | 产品经理、项目负责人、文档员工 | 模型网关或受控通用 Agent Runtime |
| `coding` | 前端、后端、数据、集成员工 | Codex、Claude Code、OpenClaw Runner |
| `verification` | Reviewer、测试、安全审核 | 独立 verifier Runner、CI、扫描器 |
| `deployment` | 运维、发布员工 | 受控 Deployment Runner 或 Jenkins |

执行器档案保存执行类别、Runner 或模型配置引用、健康要求、信任域、允许工具、上下文边界、凭据引用方式和默认预算，但不保存明文密钥。它服务研发岗位，不复用定时作业的 AI角色/Skill 装配语义。

### AI 数字员工档案

`rd_ai_employees` 保存可跨版本识别的 AI 员工主体，至少包含 `brain_app_id/code/name/status/capability_tags/persona_version/profile_summary`。它不保存 Runner、模型密钥或执行权限。策略的岗位绑定声明允许承担岗位的 AI 员工候选和本次使用的执行器档案；协作启动后，席位同时冻结 `ai_employee_id` 与 `executor_profile_id`，从而分别回答“谁完成了工作”和“使用什么运行能力完成”。

### 岗位执行器绑定

新增现有策略的子表 `rd_task_executor_policy_role_bindings`，建议包含：

| 字段 | 说明 |
|---|---|
| `role_definition_id/role_code` | 关联独立研发岗位定义并冻结岗位编码；不引用系统 RBAC 角色主键 |
| `actor_mode` | `ai/human/hybrid` |
| `actor_selector` | P0 指定真人用户 ID、AI 数字员工 ID，或明确的 human-first/ai-first 顺序；团队候选池和容量自动选人后置 |
| `executor_profile_id` | AI 岗位主执行器配置 |
| `fallback_executor_profile_ids` | 有序备用执行器，仅按策略使用 |
| `runner_id/trust_domain` | Runner 与编码、验证、部署信任域 |
| `instruction_template/output_contract` | 岗位指令与结构化输出 |
| `context_scope/tool_policy` | 可读取上下文和可使用工具 |
| `budget` | 岗位级时长、轮次、Token 和费用上限 |
| `reviewer_role_code` | 默认审核岗位 |
| `required_system_permissions` | 真人承担岗位所需的系统权限条件，只用于校验，不自动授权 |
| `permissions` | AI 席位可执行的受控动作，不直接包含密钥 |

岗位定义职责，员工承担岗位，执行器为 AI 员工提供运行能力。LLM 只可在策略声明的岗位范围和员工候选中建议负责人；协同引擎分别解析 AI 员工身份与本次执行器。真人账号被分配到席位前必须同时通过系统 RBAC 权限和产品数据范围校验；研发岗位本身不产生授权。AI 数字员工通过受控服务身份、执行器资源授权和工具策略获得最小权限，员工档案本身不产生授权。

`actor_mode=human` 时执行器为空，P0 通过 `actor_selector.user_ids` 从显式用户列表中选择，并逐人校验系统权限和产品范围；`actor_mode=ai` 时通过 `actor_selector.ai_employee_ids` 选择 active AI 数字员工，再使用岗位绑定中的 `executor_profile_id`；`actor_mode=hybrid` 时必须明确 human-first 或 ai-first。若存在多个合格真人，P0 由项目负责人确认具体席位，不基于尚未建设的排班或容量数据自动选人。团队、岗位资格目录、可用日历和容量自动调度放到 P2。最终席位同时冻结员工主体和执行器，不能因账号、岗位、员工或策略配置变化而丢失历史解释。

执行器不可用时按策略备用顺序重试。无可用备用执行器、超过等待时间或信任域不满足时，工作项进入阻塞并转真人，不允许 LLM 临时选择未授权执行器。

### 系统权限矩阵

研发岗位不授予权限；以下系统权限与产品数据范围共同决定真人可见和可执行能力：

| 权限 | 能力边界 |
|---|---|
| `delivery.rd_executor_policies.manage` | 管理统一研发执行策略；启用部署还需现有部署治理权限 |
| `delivery.rd_roles.manage` | 管理研发岗位定义，不创建系统角色或授权 |
| `delivery.rd_ai_employees.manage` | 管理 AI 数字员工身份、能力和人格版本，不配置密钥或直接授权 |
| `delivery.rd_executor_profiles.manage` | 管理 AI 执行器档案、健康与资源引用，不读取密钥明文 |
| `delivery.requirement_assessments.read` | 读取授权产品的评估、意见和证据 |
| `delivery.requirement_assessments.decide` | 处理评估、补充、延期和拒绝决策 |
| `delivery.rd_collaboration.read` | 读取授权产品的协作运行、工作项和证据 |
| `delivery.rd_collaboration.plan` | 启动/restart 运行、非范围重规划、分配席位和提交范围变更决策提案；不能原地改活动运行范围 |
| `delivery.rd_collaboration.work` | 领取、提交或审核本人席位允许的工作项 |
| `delivery.decision_requests.decide` | 处理非部署类跨主体决策；部署决策继续使用现有部署权限 |
| `delivery.decision_requests.answer` | 提交本人被请求的决策补充信息；仍需业务大脑/产品范围并命中请求冻结的 answer_actor_selector |
| `delivery.rd_role_experiences.read` | 按产品范围查询岗位经验候选、审核历史和证据引用 |
| `delivery.rd_role_experiences.decide` | 批准、拒绝或退役岗位经验；必须满足产品范围、自审隔离和乐观锁 |

所有写接口必须同时检查权限、产品 scope、运行席位和当前状态。默认管理员拥有全部新增权限；其他系统角色通过现有角色管理显式授权，不因岗位分配自动获得权限。

### 策略快照

版本启动研发协同前冻结不可变策略快照，至少包含：

- 策略 ID、版本和内容哈希。
- 生命周期终点和部署模式。
- 岗位编制、AI 数字员工候选及执行器映射。
- Runner、信任域、工作区和仓库权限。
- 指令模板、输出契约和上下文范围。
- 自动化、风险、预算、重试和熔断规则。
- 质量门禁、Git 和部署规则。

快照必须独立持久化到 `rd_task_executor_policy_snapshots`，不能只把可变策略 JSON 复制到运行表。快照字段至少包含 `id/policy_id/policy_version/parent_snapshot_id/snapshot_kind/resolution_context_key/resolution_revision/schema_version/content_hash/payload_json/created_by/created_at`；除 base 的 parent 外身份和内容字段均为 NOT NULL。`payload_json` 保存已经完成默认值展开、岗位绑定解析和安全收紧后的完整规范化配置。基础冻结使用 `snapshot_kind=base`、稳定的策略版本 context key、`resolution_revision=0` 和空 parent；评估只有实际发生自动收紧时，才使用 `snapshot_kind=assessment_resolved`、`resolution_context_key=assessment:{assessment_id}` 和 1–2 轮修订创建 parent 非空的派生记录，父链校验策略 ID/版本一致。没有任何收紧差异时 `final_strategy_snapshot_id/strategy_snapshot_id` 直接等于 initial base，不创建空派生快照。

协作运行始终引用单独的 `snapshot_kind=version_resolved` 快照，使用 `resolution_context_key=version:{version_id}:scope:{scope_version}`、`resolution_revision=1` 并以同策略版本 base 快照作为 parent。它的多需求来源不能塞进单一 parent 链，而由 `rd_task_executor_policy_snapshot_sources(snapshot_id, source_snapshot_id, requirement_id, assessment_id)` 逐条关联每个需求的 final/effective 快照；同一 requirement 只能出现一次，但多个需求允许共同引用同一个无收紧差异的 base/final 快照，因此不能对 `snapshot_id + source_snapshot_id` 建唯一约束。来源必须与目标使用相同 `policy_id/policy_version`。单需求运行也生成 version_resolved 快照，保证运行解释和来源模型一致。确定性合并结果相同则按快照身份/哈希幂等复用，不同哈希冲突；任何来源变化只能在无非终态运行时接受并先递增 `scope_version`，形成新的 context key，活动 generation 期间固定返回 `RD_SCOPE_FROZEN`。

唯一键为 `policy_id + policy_version + snapshot_kind + resolution_context_key + resolution_revision`，并为 `content_hash` 建索引；NOT NULL 和行内 kind-specific CHECK 防止 PostgreSQL NULL 绕过唯一性：base 为 parent null/revision 0，assessment_resolved 为 parent 非空/revision 1..2，version_resolved 为 parent 非空/revision 1。启动事务同时持久化不可变 `rd_collaboration_run_requirements`，每行冻结需求修订、accepted assessment、final/effective snapshot、验收标准哈希和仓库范围哈希。跨表集合完整性由 `DEFERRABLE INITIALLY DEFERRED` constraint trigger 在提交时校验：运行范围至少一条、source count 与范围行数相等、两组 requirement 无缺失/多余、assessment 与 final/effective snapshot 逐条对应且同策略版本。相同快照身份和哈希的并发冻结幂等返回同一记录，相同身份出现不同哈希则冲突。数据库 BEFORE UPDATE/DELETE 触发器拒绝改变快照、来源关系和运行范围行，运行角色只授予 INSERT/SELECT；`policy_id`、`parent_snapshot_id`、来源关系和全部消费者外键均使用 `ON DELETE RESTRICT`。策略已有快照时 DELETE 返回 `RD_POLICY_IN_USE`，只能停用。策略停用或后续版本发布不能改变历史快照解释。

需求评估分别保存 `initial_strategy_snapshot_id/final_strategy_snapshot_id/strategy_snapshot_id`，岗位意见保存产生意见时的 `strategy_snapshot_id`，协作运行只引用 version_resolved 快照并通过来源关系追溯全部需求 final 快照，`role_feedback_records` 引用产生反馈的运行快照，经验候选引用生成时生效快照；多来源经验通过 `rd_role_experience_sources` 逐条关联反馈记录与其快照，不以 JSON 数组代替外键。评估、协作运行和经验检索都必须从快照表读取，不得回读当前策略拼装历史上下文；快照 Schema 已不兼容时失败关闭并返回人工迁移决策，不能静默重算。

策略管理页面后续修改只影响新的协同运行。运行中版本需要变更策略时先展示差异、影响工作项和迁移结果并进入人工决策；不能替换当前运行快照，运行未进入 `ready_for_release/deploying` 时，批准后必须终结旧运行，再以新的 `scope_version`、version_resolved 快照和 generation restart；已进入待发布/部署阶段则只能进入新 planning 版本。

新建策略的安全默认值为 `delivery_target=ready_for_release` 和 `deployment.mode=disabled`。只有具备研发策略管理与部署治理权限的用户才能启用部署、修改岗位权限、提高预算、放宽自动化阈值或调整受保护分支规则；这些配置变更必须记录差异和审计事件。

## 研发协同运行

### 运行和工作项

```text
rd_collaboration_run
  -> work_item DAG
       -> assignment/claim
       -> attempt
       -> handoff
       -> independent review
       -> approved OR rework attempt
  -> integration
  -> release readiness
  -> optional deployment
```

建议新增：

- `rd_role_definitions`：独立研发岗位、职责、能力标签、交付物、审核关系、状态和版本；不承载系统 RBAC 授权。
- `rd_ai_employees`：跨运行稳定的 AI 数字员工身份、能力标签、人格版本和状态；不承载执行器凭据或权限。
- `rd_task_executor_policy_snapshots`：不可变 base/派生策略快照、父链、解析上下文/轮次、Schema、内容哈希和完整规范化 payload；评估、意见、协作运行、反馈和经验共同引用。
- `rd_task_executor_policy_snapshot_sources`：version_resolved 快照与每条需求 final/effective 快照的不可变关系，保存 requirement/assessment 来源和 `created_at` 并强制同一策略版本。
- `rd_collaboration_runs`：版本级协同运行和策略快照引用，保存 `run_generation/supersedes_run_id` 与运行级暂停恢复元数据；终态不可重开。
- `rd_collaboration_run_requirements`：运行内逐需求不可变范围，冻结需求修订、accepted assessment、final/effective snapshot、验收标准和仓库范围哈希，并与策略来源逐条完全对应。
- `rd_run_seats`：本次运行的岗位席位、真人用户或 AI 数字员工、执行器和容量快照；AI 席位分别保存员工 ID 与执行器 ID。
- `rd_role_sessions`：席位在本次运行内的连续上下文、交接摘要和恢复游标；业务状态仍以工作项和事件表为准。
- `rd_work_items`：工作项、负责人岗位、审核岗位、交付物、验收标准和状态。
- `rd_work_item_dependencies`：依赖边和依赖类型。
- `rd_work_item_attempts`：执行、失败和返工尝试。
- `rd_collaboration_events`：分配、问题、阻塞、交接、审核、返工和升级事件。
- `rd_scope_change_requests`：受控范围变更命令、类型化 operations、规范化哈希、来源 generation、唯一人工决策和应用后的 scope_version。
- `rd_scope_change_request_operations`：按 position 固定的不可变类型化操作行，以真实外键引用需求、评估、策略快照和仓库；父表 JSON 仅作命令快照。
- `decision_requests`：面向真人的通用信息、权限、范围、风险和部署决策，冻结到期时间、超时策略和升级对象。
- `rd_command_idempotency_records`：评估、启动/restart、范围变更、领取、提交、审核、决策、决策补充答案、工作项取消和经验审核的请求哈希、幂等键、结果引用与脱敏响应快照。
- `rd_command_replay_secrets`：仅为 claim 有效期内幂等重放保存加密租约 token；到期后擦除密文并保留 scrub 审计时间，不承担业务幂等事实。
- `role_feedback_records`：不可变工作项反馈和归因证据，分别固定运行、反馈类型、来源事件、被归因的业务大脑、产品、岗位、席位、真人/AI 员工、执行器、工作项、attempt、策略快照，以及实际反馈生产者的 subject type/id、岗位和席位；规范化 fingerprint 与运行组成数据库唯一键。
- `rd_role_experience_records`：由反馈聚合形成的版本化经验候选、审核状态、证据引用和受控检索范围。
- `rd_role_experience_sources`：经验版本与原始反馈及各自策略快照之间的关系表。

管理员可以在设计阶段增加岗位定义，并在策略中配置对应执行器和权限，这是 P0 能力。运行中由 LLM 建议临时增岗或重组团队时，必须生成组织变更提案，校验职责、权限、预算和审核隔离后形成新运行快照；自动重组优化放到后续阶段。

`decision_requests` 使用版本号进行乐观锁，`plan_version` 为 `NOT NULL DEFAULT 0`，并用“主体、决策类型、计划版本”形成业务幂等约束。同一主体和计划版本只能有一个 `pending/waiting_more_info` 有效请求，过期或被新计划替代的决策不能继续推进状态。每个 `options[]` 必须冻结 `code/label/outcome/subject_transition/requires_comment/input_schema/effect_preview`；decide 的可选结构化 `input` 必须通过所选 Schema，服务端按 `outcome` 执行确定性状态映射，客户端和 LLM 不得提交任意目标状态。选择 `request_more_info` 时请求进入 `waiting_more_info`，请求同时冻结 `answer_actor_selector` 和答案 Schema；只有具备 answer 权限、业务大脑/产品范围并命中 selector 的主体可通过 answers 子资源补充信息，形成新版本后才可再次决策。

每个活动决策还必须冻结 `expires_at/timeout_policy/escalation_target_selector/escalation_level`。默认 `timeout_policy=escalate_keep_paused`：内部协作维护 Worker 以数据库时间扫描到期请求，在一个事务内把原请求置为 `expired`、记录 `expired_at/expiry_event_id`，保持主体暂停，并幂等创建或复用指向升级对象的后继请求后切换主体引用。到期不得自动批准、拒绝或恢复主体；重复扫描和 Worker 重启只能得到一个过期事件和一个活动后继请求，没有合格升级人时保留暂停并告警管理员。过期原请求的 decide/answer 固定拒绝。

运行从 `running/integrating/verifying` 进入 `waiting_human` 时，必须在同一事务写入 `rd_collaboration_runs.resume_state`、`suspended_decision_request_id` 和 `suspended_at`；`resume_state` 只能是暂停前的三个阶段之一。决策服务使用运行 `version` 乐观锁校验待决请求仍有效，再按冻结值恢复；恢复成功后清空三个暂停字段。客户端不能在决策请求中传入运行恢复状态，过期、已替代或与当前暂停请求不一致的决策不得恢复运行。

工作项进入 `blocked/awaiting_human` 时必须保存 `resume_state`、触发事件、关联 decision request、暂停 attempt 和解除条件。资源、权限或依赖问题解除后，`blocked` 只能回到校验后的 `ready` 或进入 `cancelled`；一般人工决策通过后，`awaiting_human` 按冻结目标进入 `running/rework_required/cancelled`。取消决策是例外：请求取消时旧租约已撤销、attempt 标记 `suspended_for_decision` 并发出 Runner 取消 Outbox；若决定继续，旧 attempt/lease 不复活，工作项重新校验后进入 `ready`，由下一次 claim 创建新 attempt/lease。不得由客户端任意指定恢复状态。

工作项取消统一通过 `POST /api/delivery/rd-work-items/{id}/cancel`，请求包含 `reason/version/idempotency_key`。低风险且不扩大影响面的取消由工作项领域服务直接原子更新工作项、attempt、Review 和运行聚合，并以 Outbox 请求 Runner 取消；高风险或影响必需交付的取消先安全暂停、撤销租约、挂起 attempt、发出 Runner 取消 Outbox，再创建决策请求并返回 `202`。Runner 的迟到完成结果按已撤销租约隔离为审计证据，不得复活工作项。v2 协作任务的公开 AI 任务取消接口始终返回 `RD_COLLABORATION_REQUIRED`。

### 工作项拆解与校验

项目负责人 LLM 生成结构化工作项方案，包含负责人岗位、审核岗位、依赖、交付物、验收标准、风险和所需能力。确定性校验器检查：

- Schema 完整且无 DAG 环。
- 每条版本验收标准至少有工作项和测试用例覆盖。
- 必需岗位存在且策略有可用员工或升级路径。
- 执行人与审核人满足职责隔离。
- 工作项没有扩大版本、仓库、分支和权限边界。
- 并行工作项没有无法隔离的工作区或文件冲突。
- 总预算不超过版本策略。

校验失败可在限定次数内让 LLM 修正；仍不能通过时创建人工决策请求。

工作项图必须有独立 `plan_version`。重规划不能原地删除已执行或已审核工作项，而是创建新计划版本，把旧项标记为保留、取消或被替代，并记录变更原因、提出者、批准者、受影响依赖和预算差异。只要需求/仓库范围和 version_resolved 策略不变，冻结策略内允许的负责人、依赖、席位和预算重排可按风险自动或人工生效；任何新增需求/仓库范围、放宽岗位/权限/预算、替换策略快照或改变部署目标的提案都不能在当前 generation 生效；待发布前必须终结后 restart，进入 `ready_for_release/deploying` 后必须进入新 planning 版本。

数据库必须同时提供以下并发与幂等约束：同一 `requirement_id + requirement_revision + initial_strategy_snapshot_id` 只能有一个进行中或成功评估，不能因最终快照切换而释放唯一键；同一产品版本只能有一个非终态协作运行；同一主体、决策类型和计划版本只能有一个 `pending/waiting_more_info` 决策请求；同一计划版本的前置工作项、后置工作项和依赖类型不能重复；同一运行内 `work_item.idempotency_key` 唯一；同一工作项的 `attempt_no` 和 attempt `idempotency_key` 分别唯一。

评估、启动/restart、claim、submit、review、decision、decision answer、工作项 cancel 和经验审核命令统一在 `rd_command_idempotency_records` 保存 `command_type/aggregate_type/aggregate_id/idempotency_key/request_hash/result_type/result_id/http_status/response_hash/response_json/created_at`，并对 `command_type + aggregate_type + aggregate_id + idempotency_key` 建唯一约束；领域状态与脱敏、不可变的完整业务成功响应快照同事务提交，`response_hash` 排除每次请求的 `trace_id` 和派生 `idempotent_replay`，重放返回相同业务响应、设置重放标志并生成新 `trace_id`。除 claim 外记录无 TTL/`expires_at`，聚合终态也不能重新使用旧键。claim 成功只在原租约有效期内允许重放：不可变 `response_json` 仅保存 secret 引用，`rd_command_replay_secrets` 以 `command_record_id` 唯一关联 `secret_ciphertext/key_id/expires_at/scrubbed_at/created_at/updated_at`；到期清理事务必须把密文置空并记录 `scrubbed_at`，之后固定返回 `RD_WORK_ITEM_LEASE_EXPIRED`，不得用旧键创建新 attempt。幂等记录只允许随整聚合的批准归档/清理处理。运行代际对非空 `supersedes_run_id` 建唯一约束，决策升级对非空 `supersedes_decision_request_id` 建唯一约束，防止并发生成多个直接后继。运行暂停还必须使用外键和 CHECK 约束保证：`suspended_decision_request_id` 引用有效决策请求；只有 `status=waiting_human` 时 `resume_state/suspended_decision_request_id/suspended_at` 三者同时非空；`resume_state` 只能是 `running/integrating/verifying`；其他状态三者必须同时为空。领域服务仍须在事务内加锁和校验状态，不能只依赖前端去重。

### 调度

只有依赖已通过、员工可用、权限有效、预算充足、工作区准备完成且无资源冲突的工作项才能进入 `ready`。AI 工作项由调度器原子领取；真人工作项进入个人待办，可接受、转交或拒绝。

并行编码使用独立 worktree 和分支。多个工作项触碰相同高冲突文件时，调度器串行化或创建显式集成工作项。集成人负责合并和冲突处理，普通开发 Agent 不直接覆盖其他工作项成果。

### 协作事件

跨岗位协作使用结构化事件：

- `assignment`
- `question`
- `blocker`
- `handoff`
- `review_request`
- `review_result`
- `rework_request`
- `decision_request`
- `decision`
- `replan_proposal`

LLM 生成和理解内容，协同引擎负责路由、持久化、唤醒、幂等和审计。交接必须包含产物引用、关键决策、验证证据、已知风险、未解决问题和建议下一步。

### 审核和返工

- 开发者不能审核自己的成果。
- 编码 Runner 自报成功只能触发独立质量门禁，不能直接完成工作项。
- 客观检查由测试、CI、扫描和独立 verifier 提供证据。
- 语义质量由独立审核岗位判断。
- 审核结果为 `approved/rework_required/rejected`；必需项被拒绝或风险升级时另建运行级重规划/终止决策请求，不引入 `escalated` 私有状态。
- 返工创建新的 attempt，关联原结果和审核意见，不覆盖历史。
- 反复出现相同失败指纹或无有效进展时触发熔断，转人工接管。

### Git 集成与远程交付证据

- 每个编码工作项使用独立 worktree 和工作分支；普通开发席位只能推送策略允许的工作分支，不能直接修改受保护分支。
- 显式集成工作项负责把已审核工作项合入版本开发分支，执行最终冲突处理和版本级测试，并通过事务 Outbox 发起远程 push 或创建/更新 MR/PR。
- Git 副作用完成后保存可信交付记录，至少包含 `repository_id`、provider、工作/集成/目标分支、commit SHA、remote commit SHA、MR/PR ID 与状态、Outbox ID、执行器/服务身份、推送时间、对账状态和质量证据引用。
- `record_ready_for_release_evidence` 只验证远程分支或 MR/PR 的实际状态、不可变 commit SHA、版本验收覆盖和质量门禁，不临时执行 push；`finalize_ready_for_release_target` 再按冻结交付目标决定完成运行或保持非终态待部署。
- 外部返回不确定时先按 repository + branch + commit SHA 对账；确认远端不存在后才幂等重试，不能盲目重复推送。
- `ready_for_release` 要求所有必需仓库都有成功且已对账的可信交付记录。策略要求 MR/PR 时必须达到策略声明的 open/approved/merged 状态；默认不要求合入受保护主分支。

### 状态模型

研发协同运行：

```text
draft -> planning -> running -> integrating -> verifying
running/integrating/verifying -> waiting_human（冻结运行级恢复字段）-> 原阶段
verifying -> ready_for_release
ready_for_release -> completed（仅策略目标为待发布；completion_reason=ready_for_release，产品版本保持 ready_for_release）
ready_for_release -> deploying -> completed（策略部署成功；completion_reason=deployed）
draft/planning/running/integrating/verifying/waiting_human -> failed | cancelled（终态不可重开并清空暂停恢复字段；产品版本保持失败时的 active/testing 阶段。ready_for_release/deploying 的部署失败或回滚返回 ready_for_release）
failed | cancelled -> 新建 run_generation+1 的 draft（仅显式 restart；新运行 supersedes 旧运行，旧记录不变）
```

工作项：

```text
queued -> waiting_dependencies -> ready -> running -> awaiting_review -> approved
running -> blocked | awaiting_human
blocked -> ready | cancelled（解除条件重新校验通过后）
awaiting_human -> running | ready | rework_required | cancelled（一般决策按冻结目标恢复；取消被拒绝/选择继续时因旧租约已撤销，只能重新校验到 ready 并由新 claim 创建 attempt/lease）
running/awaiting_review -> rework_required（质量门禁或审核失败，且同范围可返工）
awaiting_review -> rework_required -> ready
任意非终态 -> failed | cancelled
```

## 可选部署

本章属于 P1。`RD_COLLABORATION_DEPLOYMENT_ENABLED=false` 时，后端拒绝创建或激活 `delivery_target=deployed` 的策略，前端不展示部署扩展入口；P0 协作、反馈和 `ready_for_release` 验收不得依赖本章实现。

### 生命周期终点

- `ready_for_release`：产品版本状态，表示开发、独立审核和测试完成，代码已推送远程研发分支。统一发布就绪服务先固化证据；策略目标为待发布时，协作运行随后写为 `completed(completion_reason=ready_for_release)`，不创建部署任务。
- `deployed`：统一发布就绪服务只把产品版本和协作运行推进到 `ready_for_release`；P1 再创建部署申请，运行经 `deploying` 完成受控部署和部署后验证，成功后写 `completed(completion_reason=deployed)`。

为了让不部署的版本也能正常闭环，产品版本状态建议从当前状态扩展为：

```text
planning -> active -> testing -> ready_for_release -> deploying -> released -> archived
```

研发协同完成与产品正式发布是两个不同事实。待发布目标下，产品版本停在 `ready_for_release`，协作运行使用 `completed + completion_reason` 表达执行已经结束；部署目标下，运行在 `ready_for_release` 仍是非终态，不能被 P0 完成函数提前关闭。两种情况都不能在部署成功前解释为“已经发布”。

### 部署模式

| 模式 | 行为 |
|---|---|
| `disabled` | 不创建部署申请，只能与 `delivery_target=ready_for_release` 搭配 |
| `request_only` | 创建部署申请，由真人运维接单和执行 |
| `approval_then_execute` | 审批和门禁通过后交给部署执行器 |
| `gated_auto` | 受控环境中门禁通过后自动执行，仍受风险下限约束 |

`delivery_target=deployed` 时部署模式不得为 `disabled`。生产、高风险、数据库迁移、权限安全变化、缺少回滚方案或存在门禁豁免时必须人工确认，即使策略配置为 `gated_auto` 也不能绕过。

部署进入现有 `deployment_requests/deployment_runs` 领域，并继续复用资源授权、窗口、预检、健康检查、回滚和 Outbox。LLM 负责部署方案、风险解释和异常建议，策略决定是否允许进入部署，门禁决定是否具备条件，真人决定不可自动放行的高风险动作。

## 问题处理机制

| 问题 | 判断主体 | 处理方式 |
|---|---|---|
| 需求信息不足 | 规则完整性检查 + LLM | 创建信息补充请求，补充后生成新评估版本 |
| 岗位意见冲突 | 协同引擎按阈值判断 | LLM 汇总争议，交真人决策 |
| 无合适规划中版本 | 组版引擎 | 提议或创建新的规划中版本 |
| 多个版本都合适 | 评分引擎 | 分差足够则自动选择，否则交产品负责人 |
| 依赖未完成 | 调度器 | 等待，不启动下游工作项 |
| 测试或质量门禁失败 | verifier/CI/扫描 | 创建携带证据的返工 attempt |
| 执行器不可用 | 调度器 | 按策略备用链切换，仍不可用则人工接管 |
| Agent 超时 | 租约与超时规则 | 回收租约，重派或失败 |
| 多次无有效进展 | 熔断器 | 停止自动循环并转人工 |
| 人工决策到期 | 协作维护 Worker | 原请求置为 expired，主体保持暂停，幂等升级到后继决策请求；不自动批准 |
| 协作运行失败或取消 | 协作编排器 | 原运行终态保留；重新校验后显式创建引用旧运行的新 generation，不复活旧 attempt/lease |
| 文件或分支冲突 | 冲突检测与集成人 | 串行化或创建集成/冲突工作项 |
| 权限不足或超出范围 | 权限策略 | fail closed，创建授权或范围决策请求 |
| Git 外部结果不确定 | Outbox 和对账 | 查询远程状态后幂等重试，不盲目重复推送 |
| 策略需中途变更 | 项目负责人提议 | 生成新快照和影响分析，必要时人工批准 |
| 部署失败 | 部署编排器 | 按策略回滚或进入人工接管 |

## 现有能力衔接

### `requirements` 和 `product_versions`

需求增加评估状态投影或关联最新评估结果。版本继续作为需求排期和研发交付主聚合，增加只读派生的当前策略/快照摘要投影和必要的 `ready_for_release/deploying` 状态；`product_versions` 不保存可写 `strategy_id/snapshot_id` 覆盖，真实运行策略只由产品策略优先、业务大脑默认策略兜底的统一解析规则和协作运行的 version_resolved 快照确定。

### `ai_tasks`

`ai_tasks` 继续作为 AI 执行单元。版本级协同运行不是一个超大 AI 任务，`rd_collaboration_run` 才是版本研发协同的根聚合。P0 为每个需要 AI 执行的工作项创建一个内部 `ai_task`，通过 `collaboration_run_id/work_item_id` 关联，以复用当前一个任务一个活动 Agent Loop 的约束；真人工作项不必创建空 AI 任务。用户任务中心可以聚合展示这些执行单元，但不能把单个内部任务误报为版本整体完成。

### `rd_task_executor_policies`

现有表直接改造为唯一研发执行策略主表，不新增模式字段或并列主策略。迁移程序把当前任务类型、执行器、Runner、工作区、指令模板和输出契约转入岗位绑定，并为主策略补齐版本目标、需求评估、组版、团队、Git 和部署安全默认配置。完成校验后删除不再属于主策略的旧顶层执行器字段。

管理入口继续使用现有菜单、`delivery.rd_executor_policies.manage` 权限和 `/api/delivery/rd-task-executor-policies` API 根路径。API 合同直接升级为需求评估、组版、生命周期、岗位绑定、Git 和部署配置，不继续返回或接收旧顶层执行器字段；前端与 API 在同一版本同步切换，只展示统一的新策略结构。

### `human_reviews`

任务产物审核继续使用现有人工确认。计划、范围、权限、组版、重组和部署等跨主体决策使用通用 `decision_requests`，避免把所有决策伪装成 AI 任务产物 Review。

### `quality_gate`、Runner 和 Agent Loop

继续复用现有自治循环、独立质量门禁、执行上下文、信任域、预算、熔断和 Runner 可靠性能力。岗位绑定只选择已经注册、健康、授权且满足信任域的执行器资源。

### `scheduled_jobs`

不增加研发协同字段，不改变配置和运行路径。定时作业的 AI角色、Skill 和执行器装配仍按现有逻辑运行，不能因为某个定时作业产出了需求就自动进入研发；产出的需求必须独立提交并经过需求评估。

Bug、代码巡检、用户反馈、线上异常和定时分析的研发建议统一通过“创建或关联需求”的适配入口进入 2.0。原始对象继续作为需求证据和上下文，不直接绕过需求评估创建协同工作项。

### 现有研发入口适配

| 现有入口 | 2.0 行为 |
|---|---|
| 需求 `generate-task/batch-generate-tasks` | 停止直接创建 AI 任务；返回 `RD_COLLABORATION_REQUIRED` 和评估/版本协作入口，前端移除按钮 |
| 需求 `batch-advance-status` | 对研发交付状态返回 `RD_COLLABORATION_REQUIRED`；仅保留既无活动协作运行、也不存在非终态工作项时批量取消/关闭的管理用途，前端移除交付状态选择 |
| 需求 `approve/reject` | 不再独立改变评估结论；引导到评估决策，旧调用在无 accepted 评估时返回 `REQUIREMENT_ASSESSMENT_REQUIRED` |
| `POST /api/ai-tasks`、`POST /api/ai-tasks/{id}/start` | 外部和真人调用返回 `RD_COLLABORATION_REQUIRED`；协作编排器调用内部领域服务创建和派发工作项 AI 任务 |
| `POST /api/ai-tasks/batch-retry` | 外部和真人调用返回 `RD_COLLABORATION_REQUIRED`；失败恢复由工作项调度器按 attempt、预算、策略和风险内部处理 |
| `POST /api/ai-tasks/{id}/cancel`、`POST /api/ai-tasks/batch-cancel` | 命中任一 v2 协作任务时整次请求返回 `RD_COLLABORATION_REQUIRED` 且不部分取消；工作项取消/人工决策服务原子更新任务、Review、attempt、工作项和运行 |
| Bug `promote-ai-task` | 按 Bug + 产品 + 开放状态幂等创建或关联正式需求，返回 requirement_id 和评估入口 |
| 代码巡检整改入口 | 兼容结果动作改为幂等创建或关联整改需求，finding/report 作为证据；不直接创建 `code_inspection_remediation` AI 任务 |
| AI 助手 `create_rd_task` | 原动作 key 在迁移期映射为“创建研发需求草案”，确认后只写需求，不创建 AI 任务；新版展示名改为 `create_requirement` |
| 用户反馈、线上异常和定时分析建议 | 继续通过现有转需求或新增适配服务创建需求，之后必须评估 |

“定时作业不变”特指 `scheduled_jobs/scheduled_job_runs` 的定义、调度、锁、重试、AI角色/Skill 装配和历史运行解释不变。代码巡检结果动作的业务写入目标从“直接研发任务”改为“正式需求”属于需求交付域适配；定时作业引擎本身不创建协作运行，也不自动启动评估。

## 页面与操作面

### 需求评估

展示需求完整度、多岗位意见、冲突、证据、风险、置信度、评估版本和最终决策。人工可以补充信息、修改后重评、接受、延期或拒绝。

### 迭代版本

展示需求为何被组合进当前版本、候选版本评分、容量、依赖、研发执行策略、岗位编制、协同进度、风险、质量证据和交付终点。新版本创建时展示自动命名和策略命中依据。

### 研发执行策略

原位升级当前研发执行策略，使每条策略统一包含需求评估、组版、团队编制、岗位执行器、预算、质量门禁、Git 和部署配置，并提供命中预览、岗位资源可用性检查、冲突提示和版本影响预览。页面不提供模式选择。

### 研发协同工作台

按工作项 DAG、看板和岗位视角展示依赖、负责人、审核人、当前尝试、阻塞、交接、门禁、预算和人工决策。真人账号只看到有权限的产品、版本和工作项。

### 人工决策中心

统一处理信息补充、范围变更、组版选择、权限申请、预算扩展、风险确认、策略迁移和部署审批。决策必须显示影响范围、证据、建议、可选动作和超时结果。

### 岗位经验治理

本能力属于 P1；`RD_ROLE_EXPERIENCE_ENABLED=false` 时不生成候选、不开放管理端点、不注入后续上下文，但 P0 不可变反馈照常保存。

按业务大脑、产品、岗位、工作项类型、场景、风险、仓库/工具信任域、最低置信度、状态、版本和证据主体查询经验候选，展示来源反馈、策略快照、置信度、适用范围和版本差异；服务端先执行调用者业务大脑与产品权限过滤，有权限且不是任一来源反馈生产者的审核人可以批准、拒绝或退役。页面同时展示哪些 approved 经验已被后续协作检索引用及当时冻结的 `experience_reuse_config`，但不提供直接修改 active 策略的操作。

## 安全与一致性不变量

- PostgreSQL 是需求评估、组版、策略快照、协同状态、决策和反馈的唯一事实源。
- LLM 输出不能直接落成状态变更，必须经过命令处理器和策略校验。
- 工作项领取、组版、预算预占、状态推进和审计必须按一致性需要在同一事务完成。
- 外部 Git、Runner 和部署动作通过 Outbox 派发并使用幂等键。
- 策略变更不追溯影响运行中版本，除非显式创建和批准新快照。
- 最终风险不能低于确定性规则计算结果。
- 执行、审核和部署信任域按现有可信交付规则隔离。
- 经验不能因单次结果直接晋升为全局规则，必须满足样本、证据和人工治理要求。

## 反馈归因和经验沉淀

每次工作项和审核至少记录：

- 版本、需求、工作项、尝试和产物。
- 负责人岗位、员工稳定 ID、员工类型、执行器和 Runner；AI 员工必须分别记录 `ai_employee_id` 与 `executor_profile_id`。
- 审核岗位、审核人和独立证据。
- 计划时间、实际时间、Token、费用和重试。
- 成功、失败、返工、阻塞和人工介入原因。
- 适用的策略版本和上下文版本。

系统从重复成功模式、常见失败指纹、有效审核意见和人类决策中生成经验候选。`role_feedback_records` 保留不可变原始证据并固定 `brain_app_id/product_id/collaboration_run_id/feedback_kind/source_event_id/role_code/seat_id/human_user_id|ai_employee_id/executor_profile_id/work_item_id/attempt_id/strategy_snapshot_id`；另以 `producer_subject_type=human_user|ai_employee|service/producer_subject_id/producer_role_code/producer_seat_id` 冻结实际产生反馈的主体，不能从被归因对象反推。反馈必须由同一运行的持久化协作事件驱动，`(collaboration_run_id,source_event_id)` 复合外键拒绝跨运行事件；fingerprint 覆盖运行代次、来源事件、反馈类型、归因主体、工作项/attempt 和策略快照，数据库唯一约束 `(collaboration_run_id, feedback_fingerprint)`；Graph 恢复、事件重放和并发消费者幂等返回原记录。聚合器按岗位、场景、风险和证据指纹去重后创建 `rd_role_experience_records(status=pending)`。经验候选至少保存 `experience_key/version/brain_app_id/product_scope/role_code/work_item_type/scenario/risk_scope/repository_trust_domains/tool_trust_domains/content/evidence_refs/strategy_snapshot_id/confidence/status/review_version`；`strategy_snapshot_id` 是候选生成时实际生效快照的外键，`rd_role_experience_sources` 逐条保存源反馈和其策略快照外键，API 再聚合为 `source_strategy_snapshot_ids`。审核时通过来源关系聚合所有 producer subject/role/seat 实施隔离。新内容必须创建新版本，不能覆盖已经审核的版本。

经验状态机为 `pending -> approved | rejected`、`approved -> retired`；已拒绝或已退役记录不可重新激活，只能从既有证据创建新版本。审核人必须具备 `delivery.rd_role_experiences.decide` 和产品范围，且不能是任一来源反馈的生产者；决策使用 `review_version` 乐观锁并保存意见、决策人和审计事件。管理页面和查询 API 支持按岗位、产品、场景、状态、版本和证据主体筛选。

后续协作只有在 `RD_ROLE_EXPERIENCE_ENABLED=true` 且 version_resolved 快照的 `experience_reuse_config.enabled=true` 时才检索 `approved` 且未退役的经验，并同时匹配调用者权限、业务大脑、产品范围、岗位、工作项类型、场景、风险上限、工具/仓库信任域、最低置信度、最大时效和策略兼容级别。过滤后按确定性相关度/置信度排序，并受 `max_items/max_context_tokens` 双重上限约束。检索结果以带经验 ID、版本和证据引用的只读上下文注入岗位会话；低置信度、超时效、跨业务大脑、跨产品、权限不匹配或与当前策略冲突的经验不得进入自动执行 Prompt。经验可以产生 Playbook 或策略变更建议，但不能直接修改 active 策略、放宽权限、跳过门禁或替代不可变策略快照。

## 验收标准

1. 未完成需求评估的需求不能进入迭代版本或创建研发协同运行。
2. 评估通过的需求优先加入合格的规划中版本；无合格版本时只创建一个新规划中版本，不发生并发重复排期。
3. 每个版本启动时保存不可变研发执行策略快照和逐需求运行范围；两者来源按 requirement 完全一致且不可更新/删除，多条无收紧需求可各保留来源边并共同引用同一 base 快照。
4. AI 岗位只能使用快照允许的执行器、Runner、工具和权限。
5. 工作项 DAG 不允许环，依赖未通过时下游不能启动。
6. 执行者不能审核自己的产物，编码 Runner 成功不能替代独立质量门禁。
7. 返工保留原尝试、审核意见和证据，不覆盖历史。
8. 低风险任务可按策略自动推进；高风险、越权和低置信度任务进入人工决策。
9. `delivery_target=ready_for_release` 时，测试通过并推送远程研发分支后产品版本进入 `ready_for_release`，协作运行进入 `completed(completion_reason=ready_for_release)`，不创建部署任务。
10. `delivery_target=deployed` 时，可信待发布证据完成后协作运行保持非终态 `ready_for_release`；只有部署门禁、权限和审批满足后才能进入 `deploying`，P0 完成函数不能提前关闭。
11. 每次结果能够追溯到岗位、员工、执行器、策略、上下文和证据。
12. 现有定时作业的 API、配置、调度、运行和历史解释不因本功能改变。
13. Bug、代码巡检整改、用户反馈和线上异常不能绕过产品需求直接启动 2.0 研发协同。
14. 未命中研发执行策略必须显式阻断，不得使用策略外执行路径。
15. 真人和 AI 席位、执行器及角色会话能够在恢复后保持一致，工作项业务状态不依赖会话内存。
16. 版本级协同图和单工作项执行图均运行在原 LangGraph 工作流引擎上，使用 PostgreSQL Checkpointer、稳定 `thread_id` 和真实 interrupt/resume 在事件或人工决策后恢复；定时作业引擎不参与该流程。
17. 需求评估前必须先解析初始策略，评估后必须按最终风险复核策略；任何自动变更都不能降低风险、扩大权限或提高自动化程度。
18. 研发岗位与系统 RBAC 角色相互独立；新增岗位或安排席位不能自动授予真人账号权限或扩大数据范围。
19. 一次性升级进入 `draining` 后必须等待活动研发任务、Agent Loop、Runner lease 和协作命令归零；不支持把运行中旧任务直接转换为新协同工作项。
20. 同一产品版本同一时刻最多一个非终态协作运行；并发启动返回同一运行，需求接口不能创建第二个版本运行。
21. Bug、代码巡检、AI 助手和旧需求生成任务入口只创建或关联正式需求，不直接创建可启动研发 AI 任务。
22. 策略复核最多自动单调收紧两轮；新增必需岗位必须补齐兼容意见，不可比较或可能放宽边界的策略变化进入人工决策。
23. 领域状态与事件 Inbox 是恢复事实源；Checkpoint 独立提交失败后重复恢复不得重复状态迁移、Runner、Git 或部署副作用。
24. 真人写操作同时通过系统权限、产品范围、运行席位和状态校验；岗位定义或席位分配本身不产生授权。
25. 版本进入 `ready_for_release` 前，每个必需仓库都存在与远端对账成功的分支、commit SHA 和 MR/PR（如策略要求）可信交付记录；完成判定不临时执行 push。
26. 破坏性切换前必须先完成围栏外只读预检，再经 `draining` 收敛到零活动并进入 `cutover_locked` 通过锁内预检；新版健康验证前不删除旧字段，进入 cutover_locked 后不重新开放旧写路径。
27. 需求批量状态接口不能推进任何研发交付状态，公开 AI 任务创建/启动/批量重试/取消接口不能由真人或外部客户端绕过协作运行。
28. AI 数字员工拥有独立于岗位和执行器的稳定身份；AI 席位、反馈和经验同时记录 `ai_employee_id` 与 `executor_profile_id`。
29. `blocked/awaiting_human` 工作项保存由平台冻结的恢复目标；问题解除或决策完成后只能按状态机恢复、返工或取消。
30. 切换成功、清理完成和 v2 Worker 健康验证后才能解除维护围栏；解除后 v2 写路径可用、旧写路径仍永久拒绝。只有尚未激活 Schema v2 且 cleanup 未开始的 draining 阶段允许审计化中止。
31. generation 启动后范围冻结，活动运行期间普通范围变化返回 `RD_SCOPE_FROZEN`；failed/cancelled 运行不可重开。待发布前范围变化必须通过唯一 scope-change 请求和人工决策，批准事务按旧 generation 原子撤销租约、收敛非终态子任务与外部 Outbox、围栏迟到回写、终结旧运行、应用全部 operations、仅递增一次 scope，并由显式 restart 创建引用 `terminal_run_id` 的新 generation；拒绝只恢复该请求暂停的原阶段。进入 `ready_for_release/deploying` 后只创建带来源血缘的后续需求并进入新 planning 版本，旧运行、工作项、attempt 和证据保持不可变。
32. 决策到期不得自动批准或恢复主体；默认保持暂停并幂等创建后继升级请求，重复扫描不产生重复事件或活动请求。
33. 评估请求不接受 `strategy_id`；策略调整只能通过统一策略版本更新后重新评估。
34. 岗位反馈分别冻结被归因主体与实际 producer subject/role/seat；经验审核人通过全部来源关系与任一生产者隔离，经验注入必须同时通过平台标志和冻结 `experience_reuse_config` 的置信度、容量、时效、策略兼容及信任域限制。

## 成功指标

- 直接任务旁路数：通过旧入口绕过评估创建的研发 AI 任务数，目标恒为 0。
- 重复组版/运行数：同一评估版本重复排期、同一版本存在多个活动协作运行的数量，目标恒为 0。
- 远程交付证据覆盖率：进入 `ready_for_release` 的必需仓库中具有已对账可信交付记录的比例，目标 100%。
- 高风险绕过数：高/严重风险未经过必需人工决策而推进的次数，目标恒为 0。
- 角色反馈归因覆盖率：完成或失败工作项中同时具备岗位、员工/执行器、attempt 和策略快照归因的比例，目标 100%。
- 自动组版成功率 = 自动加入已有规划版本的 accepted 需求数 / 可自动决策的 accepted 需求数；人工改派率单独统计，试点后设置优化目标。
- 需求评估补充信息率、重评率、人工推翻率，工作项平均返工次数、熔断率、执行器可用率/切换率/超时率、单位工作项成本和需求到待发布周期在首个试点版本建立基线，第二个版本再设改善目标，避免无历史样本时伪造阈值。
- 定时作业回归变化数：升级前后同一作业定义、调度、Agent/Skill 快照和运行语义的非预期差异数，目标恒为 0；代码巡检结果动作转需求属于已声明的需求交付适配，单独验收。

## 分阶段实施建议

### P0：需求评估、协作开发测试和可信远程交付

- 需求评估运行、岗位意见和人工决策。
- 优先加入规划中版本、无候选自动建版及并发幂等。
- 原有研发执行策略 2.0 升级、岗位执行器绑定和策略快照。
- 可扩展岗位定义、AI 数字员工、运行席位、研发执行器档案和角色连续会话。
- 研发协同运行、工作项 DAG、结构化事件和通用决策请求。
- 不可变逐需求运行范围、决策超时升级，以及 failed/cancelled 后创建新 generation 的基础恢复。
- 复用子 `ai_task`、Runner、Agent Loop 和质量门禁。
- v2 任务取消防绕行，以及按岗位、主体、执行器、attempt 和策略快照记录不可变基础反馈证据。
- 最小 worktree/工作分支隔离、显式集成工作项、远程 push 或 MR/PR Outbox、版本级集成测试和不可变交付证据。
- 产品版本 `ready_for_release` 与协作运行 `completed(completion_reason=ready_for_release)` 共同构成不部署时的完整研发终点。

### P1：高级并行、经验治理和可选部署

- 高级文件冲突预测、容量感知并行调度、跨仓库集成优化和复杂失败恢复。
- 基于 P0 不可变岗位反馈证据和统一策略中的安全默认 `experience_reuse_config`，增加经验聚合、候选审核生命周期、管理页面和后续协作受控检索。
- 按策略接入 `request_only/approval_then_execute/gated_auto` 部署。
- 运行中策略变更的差异评估与后继 generation 迁移、备用执行器和人工接管。

### P2：组织与策略优化

- 岗位与员工绩效证据、成本和质量画像。
- 从已批准经验生成岗位 Playbook 和策略优化建议。
- 运行中动态增岗建议、受控团队重组和基于容量的自动优化；设计阶段新增岗位已在 P0 支持。
- 基于历史交付效果的策略推荐，但仍不自动修改生产策略。

## 一次性升级迁移

- 不使用产品级 Feature Flag 维持两套研发运行规则。数据库可以分两次迁移以保证安全，但只有一个明确的业务激活点，激活后旧流程立即不可写。
- 第一阶段是非破坏性扩展：创建包括 `rd_ai_employees` 在内的新表、索引、权限和可空关联字段，不删除旧列、不改变旧应用运行；同时完成新版 API、服务、前端和数据转换程序的开发验证。
- 迁移预检先在围栏外以只读方式执行，生成活动任务、活动 Agent Loop/Runner、策略归并冲突、缺失岗位、失效 Runner、仓库、工作区、权限和历史草案报告，作为进入维护窗口的建议依据，不改变写路径。
- 发布窗口把持久化围栏从 `disabled` 推进到 `draining`：阻止新的需求 approve/reject/generate-task、AI 任务 start/retry、策略/协作/经验写入和 Runner 新领取；允许已领取工作提交终态回写、在途事务收敛，管理员可通过 drain 服务受控取消并审计。定时作业不进入该围栏。
- 等待活动 AI task、Agent Loop、Runner lease 和协作命令归零并写入数据库备份标记，再原子推进到 `cutover_locked` 并重跑锁内预检。任一 P0 阻断存在时不得执行切换。只有仍处于 draining、Schema v2 未激活且 cleanup 未开始时，才可带 `reason/version` 中止为 disabled；进入 cutover_locked 后不得恢复旧写路径，只能向前修复。
- 按业务大脑、产品和仓库范围整理现有策略，把旧任务类型执行配置转换为统一策略和岗位绑定；无法唯一归并或缺少必需岗位的策略标记为 `invalid`，补齐前不能启动研发。
- 为迁移后的策略写入安全默认值：`delivery_target=ready_for_release`、部署禁用、人工审核、预算上限和独立质量门禁。
- `cutover_locked` 切换事务执行最终数据校验、取消 draft 旧 AI 任务、写迁移审计、启用 v2 契约并设置 `rd_collaboration_schema_version=2`。切换成功后新应用只读写新规则，旧应用不得重新接入。
- 新应用在旧字段仍存在但不再读取的状态下启动；健康检查、策略解析、评估和只读页面验证通过后记录健康标记，再由显式 cutover cleanup 命令以单事务执行清理迁移，删除旧顶层字段和约束。破坏性清理不接入启动时自动 additive migration runner。清理失败不回退业务规则，但保持维护状态并允许修复后重试；不能重新开放旧写路径。
- 清理成功后按顺序恢复 v2 协同 Worker、验证 Worker/Schema/图版本一致、执行 v2 需求评估与协作写入冒烟检查，再以健康标记和 Schema 版本作前置条件把围栏从 `cutover_locked` 置为 `disabled`。解除围栏只开放 v2 写路径，旧请求继续返回迁移错误；任一步失败都保持 `cutover_locked` 并可幂等向前重试。
- 已完成任务和历史运行不重算，其冻结快照只用于审计。现有 `draft` AI 任务统一标记为 `cancelled/superseded_by_v2_migration`，来源需求重新进入正式评估；历史失败任务如需继续处理也必须从来源需求进入协作。
- 现有未启动需求必须先完成正式需求评估；规划中版本补齐新策略引用后才能启动研发协同。
- 当前定时作业及历史运行不迁移、不重算、不写入研发协同表。

## OpenOPC 思路的吸收边界

本设计吸收组织设计与运行分离、岗位/席位/执行者分离、工作项依赖图、执行/委派/审核/集成/返工动作、人工升级和员工反馈归因等思路。AI Brain 的业务状态继续由 PostgreSQL、事务、Outbox 和审计体系承载，不复制文件通信或把角色会话当作业务事实源。
