# 系统概览

## 业务背景

AI Brain 是企业 AI 大脑平台。v1 建立了产品研发大脑的需求、AI 任务、Runner、质量门禁、代码评审、部署治理、知识和审计基础；v2.0 将产品需求作为研发协同唯一入口，通过正式需求评估、规划版本优先归组、统一研发执行策略和 AI/真人多岗位协作，把复杂目标拆为可并行、可审核、可返工、可升级人类决策的工作项 DAG。默认完成开发、测试、远程代码提交并停在待发布，不自动部署。现有定时作业保持原调度与 Agent/Skill 装配语义。

详细产品范围以项目级 PRD 为准：[enterprise-ai-brain/prd.md](../../01-prd/enterprise-ai-brain/prd.md)。

## 系统架构图

```text
用户浏览器
  │
  ▼
React + TypeScript 工作台（基于 Ant Design Pro 模板）
  │
  ▼
FastAPI 模块化单体
  ├─ auth：本地账号、角色、权限
  ├─ brain_app：业务大脑配置
  ├─ assistant：AI Brain 系统问答和项目进展助手
  ├─ product_config：产品、版本、模块、Git 资源和相关系统
  ├─ requirement：需求台账、审批、正式评估和规划版本归组
  ├─ rd_policy：统一研发执行策略、动态岗位、AI 数字员工和岗位执行器
  ├─ rd_collaboration：版本级协作运行、真人/AI 员工席位、工作项 DAG、审核返工和人类决策
  ├─ ai_task：AI 任务生命周期
  ├─ agent_loop：Agent 自治循环、轮次预算和人工接管
  ├─ quality_gate：研发合并和部署前后的独立质量门禁
  ├─ execution_context：需求、Bug、仓库、知识和验收标准的版本化执行清单
  ├─ graph_runtime：任务图/协作图、PostgreSQL Checkpointer、中断和恢复
  ├─ review：人工确认
  ├─ knowledge：版本化文档、多模态解析、chunk、检索和沉淀
  ├─ long_memory：GBrain 长期记忆、混合检索和知识图谱
  ├─ model_gateway：OpenAI-compatible 模型调用
  ├─ plugin_management：插件、连接、动作配置和连接测试
  ├─ integration_events：Webhook 验签、幂等 Inbox、重试和业务投影
  ├─ execution_resources：产品/环境 Runner Target 与 Jenkins 授权
  ├─ deployment_orchestration：部署预检、波次、健康检查和回滚
  ├─ scheduled_jobs：定时作业定义、运行实例和 AI/插件装配快照
  ├─ code_inspection：周期性代码仓库巡检报告、finding、Bug 派生和通知反馈
  ├─ devops_metrics：GitLab、Jenkins 和线上日志指标采集
  ├─ gitlab_review：内部 GitLab MR 元信息、diff 快照和 Review 报告归档
  ├─ code_review_executor：可插拔代码 Review 执行器
  ├─ user_insights：用户使用和用户反馈采集
  ├─ iteration_planning：AI 迭代规划建议
  ├─ lifecycle_context：研发上下文图谱和风险信号
  ├─ bug：AI 自动测试和人工测试 Bug 闭环
  ├─ dashboard：首页 IT 团队看板聚合
  ├─ integration：模拟 Issue 回写
  ├─ audit：审计事件
  └─ export：Markdown 方案导出
  │
  ├─ PostgreSQL + pgvector
  ├─ Redis
  └─ GBrain（长期记忆 / 知识图谱）
```

独立 execution worker 从 PostgreSQL 认领 Outbox/Inbox，负责 Runner、Jenkins、Git Provider 等外部副作用和部署编排；API 只提交业务状态、审计和派发意图，不在请求事务外直接完成不可恢复的外部调用。

## 核心模块

| 模块 | 职责 | 技术栈 |
|------|------|--------|
| web | 团队看板、AI 助手、任务中心、研发任务、产品管理、需求管理、Bug 管理、研发运营看板、用户洞察、知识中心、审计与运行 | React + TypeScript + Ant Design Pro |
| api | JSON API、认证、产品配置、需求审批、任务管理、Bug 管理、研发运营指标和模块化领域逻辑 | FastAPI + Python |
| assistant | 基于服务端脱敏系统上下文回答 AI Brain 系统信息、项目进展、产品、任务、Git 仓库和模型网关状态问题 | FastAPI + 模型网关 Chat |
| product_config | 产品、版本、模块、Git 资源、内部 GitLab 项目绑定和相关系统主数据 | PostgreSQL |
| requirement | 需求台账、正式评估、补充/决策、规划版本归组、取消和关闭；不直接创建研发 AI 任务 | PostgreSQL |
| rd_policy | 需求评估、版本归组、岗位、AI 数字员工候选、执行器、预算、门禁、Git、风险和交付终点统一策略；`policy_version` 乐观锁控制更新，active 产品策略优先于业务大脑默认策略；不可变 base/assessment_resolved/version_resolved 快照及来源关系保存历史解释 | PostgreSQL |
| rd_collaboration | 版本级运行与不可变逐需求范围、失败/取消后新 generation 恢复、真人/AI 员工岗位席位、工作项 DAG、并行调度、运行/工作项暂停恢复、决策超时升级、审核返工、岗位反馈和经验治理 | PostgreSQL + LangGraph |
| ai_task | AI 任务类型、生命周期、状态流转和任务详情 | PostgreSQL + LangGraph |
| agent_loop / quality_gate | 自治轮次、执行上下文、独立验证证据、预算终止、人工接管和受控自动合入 | PostgreSQL + 隔离 Runner / CI |
| graph_runtime | 研发任务图和版本协作图的节点、持久化检查点、中断与恢复 | LangGraph + PostgreSQL Checkpointer |
| knowledge | 文本/图片/PDF 原始资产、版本化 OCR/版面/表格解析、向量/关键词混合检索、权限与过期治理 | PostgreSQL + pgvector + MinIO/S3 |
| long_memory | 长期记忆、答案合成、知识图谱和多跳查询 | GBrain |
| model_gateway | 聊天/embedding 模型统一入口 | OpenAI-compatible API |
| plugin_management | 三方系统插件、连接、动作配置、请求配置和试运行；调用日志在定时作业运行详情体现 | PostgreSQL + HTTP/MCP HTTP |
| integration_events | GitHub/GitLab、Jenkins、Prometheus/OpenTelemetry/Sentry 等事件验签、Inbox、幂等投影和重试 | PostgreSQL + Webhook |
| deployment_orchestration | 人工/SSH/Docker/Jenkins 部署、窗口预检、灰度/分批/蓝绿发布、健康验证与真实回滚 | PostgreSQL + Outbox worker |
| scheduled_jobs | 采集、AI 分析、动作调用、代码仓库巡检、迭代建议和看板刷新调度 | PostgreSQL + Redis/worker |
| code_inspection | 定期扫描仓库质量、安全和规范问题，按提交人沉淀代码巡检报告、finding 明细、严重问题 Bug 去重和通知反馈 | PostgreSQL + 插件扫描服务 |
| devops_metrics | GitLab 提交与代码质量、Jenkins 发布、线上运行日志指标采集和归属映射 | PostgreSQL + 定时采集器 |
| gitlab_review | 内部 GitLab MR 元信息、changes 只读读取、diff 快照、Review 报告归档和不回写 GitLab 约束 | GitLab API + PostgreSQL |
| code_review_executor | 可插拔代码 Review 执行器，一期默认对接 Claude Code `code-review` skill | Claude Code skill adapter |
| user_insights | 用户使用数据、用户反馈、归属映射和聚合分析 | PostgreSQL + 定时采集器 |
| iteration_planning | AI 迭代规划建议、证据链聚合和人工确认 | PostgreSQL + 模型网关 |
| lifecycle_context | 软件研发全流程上下文图谱、上下游追溯、风险信号和影响范围分析 | PostgreSQL |
| bug | AI 自动测试 Bug、人工登记 Bug、分派、修复、验证、关闭和重复归并 | PostgreSQL |
| dashboard | 首页 IT 团队看板和研发运营看板的产品级指标聚合 | PostgreSQL / Redis |
| integration | v1 模拟 Issue 回写 | PostgreSQL |
| audit | 操作和 AI 执行轨迹 | PostgreSQL |

## 数据流向

```text
提交产品需求
→ 创建 requirement 并完成审批
→ 正式评估需求，LLM 提出建议、确定性服务校验风险/权限/完整度
→ 优先归入兼容 planning 版本，无合适版本才创建新规划版本
→ 冻结统一研发执行策略 base 快照；评估自动收紧按 assessment context/revision 生成父链清晰的 final 派生快照，不修改策略版本
→ 无活动运行时，product_version.scope_version 随已接受的需求成员/修订/验收、仓库、分支等冻结输入变化原子递增；同版本多需求 final/effective 快照须属同一 policy_id/version，并按 merge operator 确定性收紧为唯一 version_resolved 快照，来源逐条关联 requirement/assessment，冲突时不启动
→ 以产品版本为根幂等创建唯一活动 rd_collaboration_run，引用 version_resolved 策略快照；不可变运行需求范围与策略来源逐条完全一致，再冻结岗位、真人/AI 员工、执行器和工作项 DAG
→ generation 启动后普通入口拒绝需求/修订/验收/final 快照/仓库分支范围变化；非范围重规划只更新 plan_version，待发布前范围变化只能通过受控 scope-change 命令和人工决策原子终结旧运行、应用范围并递增一次 scope，再以 terminal_run_id 显式 restart；进入 ready_for_release/deploying 后只能创建带来源血缘的后续需求并进入新 planning 版本
→ 评估、启动、终态运行 restart、领取、提交、审核、决策和工作项取消把幂等键、请求哈希、结果引用及脱敏响应快照与领域状态原子写入；claim token 由独立限时密文记录支持有效期重放并在到期后擦除
→ 并行派发 ready 工作项到 AI 数字员工或真人席位；AI 席位另行冻结执行器
→ AI 工作项复用 ai_task / Agent Loop / Runner，冻结 execution_context_manifest
→ 检索 knowledge_chunks
→ 可选查询 GBrain 长期记忆和知识图谱
→ 按 task_type 生成产品详细设计、技术方案、内部 GitLab MR Review 报告、开发计划、测试分析、发布评估或上线后分析
→ 编码结果进入独立 quality_gate；审核失败创建返工项，高风险/超权限问题创建人类决策请求
→ 人工决策选项冻结 outcome 与主体状态映射；补充信息进入 waiting_more_info 并通过 answers 子资源生成新版本；到期默认保持主体暂停并幂等升级后继请求，绝不自动批准。工作项按冻结 resume_state 恢复/返工/取消，运行按 resume_state/suspended_decision_request_id/suspended_at 从 running/integrating/verifying 恢复；领域状态与 Outbox 原子提交，Checkpoint 独立持久化执行游标
→ failed/cancelled 运行保持不可变，产品版本保留 active/testing 阶段；显式 restart 重新校验后创建引用旧运行的新 generation，不复活旧工作项/attempt/lease
→ P0 反馈把被归因执行主体与实际 producer subject/role/seat 分开写入不可变记录；P1 再生成 pending 经验候选，审核人通过全部来源关系与生产者隔离，只有平台标志与冻结 experience_reuse_config 同时允许且经权限、范围、时效、信任域、置信度、容量和策略校验批准的版本可带证据引用进入后续岗位上下文
→ 生成 mock_issues / code_review_reports / Bug / Markdown / knowledge_deposits
→ lifecycle_context 写入需求、任务、提交、Review、测试、Bug、发布、日志和知识之间的关系边
→ lifecycle_context 归集需求变更、设计缺口、代码质量、Review、测试、Bug、发布和线上异常风险信号
→ GitLab、Jenkins、线上日志通过真实登记/导入或定时采集映射产品归属
→ 代码仓库巡检定时作业通过插件扫描质量/安全/规范 finding，按提交人写入代码巡检报告，严重问题去重派生 Bug 并创建/关联正式整改需求，历史任务字段只读，同时记录邮件/钉钉机器人通知反馈
→ 用户使用数据和用户反馈定时采集并映射产品、模块、功能和用户群体
→ iteration_planning 结合需求池、Bug、线上日志、发布记录、用户使用和用户反馈生成迭代规划建议
→ AI 自动测试和人工测试登记 Bug，关联产品、任务、提交、发布或日志
→ 首页 IT 团队看板聚合需求、研发进展、Bug、代码质量、发布、线上健康、用户洞察、用户反馈和迭代规划建议
→ AI 助手读取脱敏系统上下文并通过模型网关 Chat 回答系统状态和项目进展问题
→ 集成工作项通过 Outbox 推送并对账远程分支/commit/MR-PR 证据；统一固化 ready_for_release 证据后，待发布目标完成运行，部署目标让运行保持非终态 ready_for_release，策略允许且人工确认后才进入部署域
→ 反馈分别归因到岗位、真人用户或 AI 数字员工、执行器和策略版本并写入 audit_events
```

## 关键设计决策

| 决策项 | 结论 | 维护文档 |
|--------|------|----------|
| v1 系统形态 | 模块化单体 | [技术规格](../enterprise-ai-brain/spec.md) |
| 业务主体 | 产品、需求、AI 任务、Bug、知识中心、研发度量/看板和用户洞察（含迭代规划建议）是一等主体或独立运营视图 | [PRD](../../01-prd/enterprise-ai-brain/prd.md) 和 [技术规格](../enterprise-ai-brain/spec.md) |
| 需求任务关系 | 需求评估通过并归入规划版本后创建协作运行；工作项按需生成 AI 任务并保存评估、需求、版本、策略和产品上下文快照 | [技术规格](../enterprise-ai-brain/spec.md) |
| v2 研发入口 | 产品需求先正式评估，再优先归入兼容规划版本；协作工作项按需生成底层 AI 任务 | [PRD](../../01-prd/enterprise-ai-brain/prd.md) 和 [技术规格](../enterprise-ai-brain/spec.md) |
| 入口适配 | Bug、代码巡检、AI 助手和旧生成任务入口只创建或关联需求；交付状态批量推进及公开 AI 任务创建/启动/批量重试固定拒绝；定时作业引擎不创建协作运行 | [技术规格](../enterprise-ai-brain/spec.md) |
| 统一研发策略 | 原研发执行器策略原位升级为一套规则，统一控制岗位、AI 数字员工候选、执行器、预算、门禁、Git、风险和交付终点，不存在双模式或策略外回退 | [技术规格](../enterprise-ai-brain/spec.md) |
| 协作聚合 | 产品版本是根聚合，一个版本可包含多条需求且同一时刻最多一个活动运行，启动时冻结范围和策略 | [技术规格](../enterprise-ai-brain/spec.md) |
| 混合研发团队 | 动态研发岗位独立于系统 RBAC，席位可由持久化 AI 数字员工或真人账号承担；AI 员工与执行器分别冻结，真人操作仍经 RBAC 与产品范围鉴权 | [技术规格](../enterprise-ai-brain/spec.md) |
| AI 任务类型 | v1 MVP 覆盖产品详细设计、技术方案和内部 GitLab MR 代码 Review；后续扩展开发计划、自动化测试、发布评估和上线后分析，统一使用 task_type、状态机、人工确认和审计 | [技术规格](../enterprise-ai-brain/spec.md) |
| 全流程感知 | 需求、设计、代码、Review、测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识和审计通过 lifecycle_context 串联，支持上下游追溯和风险定位 | [技术规格](../enterprise-ai-brain/spec.md) |
| 研发运营数据 | GitLab、Jenkins、线上日志、用户使用、用户反馈、迭代规划建议和 Bug 均按产品/版本/模块归属聚合，支撑首页 IT 团队看板 | [技术规格](../enterprise-ai-brain/spec.md) |
| 代码仓库巡检 | 定时作业通过插件扫描仓库质量/安全/规范问题，结果进入代码巡检报告表并保留提交人维度，严重问题可去重创建 `code_inspection` 来源 Bug，并记录邮件/钉钉机器人通知反馈 | [PRD](../../01-prd/enterprise-ai-brain/prd.md)、[技术规格](../enterprise-ai-brain/spec.md) 和 [API 文档](../enterprise-ai-brain/api.md) |
| AI 编排 | LangGraph 负责任务图和版本协作图，PostgreSQL Checkpointer 负责真实 interrupt/resume；确定性领域服务拥有状态写权限 | [技术规格](../enterprise-ai-brain/spec.md) |
| 恢复一致性 | 领域表和事件 Inbox 是事实源，领域状态/审计/Outbox 同事务；Checkpoint 独立保存执行游标，节点通过幂等命令恢复；阻塞工作项按平台冻结的 resume_state 恢复；最终派发统一按父运行到工作项加锁并拒绝向已暂停运行写入陈旧 reservation | [技术规格](../enterprise-ai-brain/spec.md) |
| Agent 自治执行 | AgentLoopRun 管理执行轮次和预算，质量门禁独立于编码 Runner；自动合入必须具备独立证据，高风险变更转人工确认 | [技术规格](../enterprise-ai-brain/spec.md) |
| 外部副作用 | 业务状态、审计与 Outbox 原子写入，独立 Worker 幂等执行 Runner/Jenkins/Git 写回；Webhook 先进入 Inbox | [技术规格](../enterprise-ai-brain/spec.md) |
| 数据存储 | PostgreSQL + pgvector + Redis | [技术规格](../enterprise-ai-brain/spec.md) |
| 知识检索 | PostgreSQL + pgvector 权限过滤，GBrain 提供长期记忆、混合检索和知识图谱补充 | [技术规格](../enterprise-ai-brain/spec.md) |
| 模型接入 | 模型网关，不直连业务代码 | [API 文档](../enterprise-ai-brain/api.md) 和 [技术规格](../enterprise-ai-brain/spec.md) |
| AI 助手 | 助手只通过模型网关 Chat 接入，服务端注入脱敏系统上下文，模型日志仅记录 `purpose=assistant_chat` 元数据 | [API 文档](../enterprise-ai-brain/api.md)、[技术规格](../enterprise-ai-brain/spec.md) 和 [测试用例](../enterprise-ai-brain/test-case.md) |
| 部署 | v1 Docker Compose | [部署 Runbook](../../05-runbooks/deployment.md) |

## 部署架构

```text
Docker Compose
  ├─ web：React 工作台
  ├─ api：FastAPI 服务
  ├─ execution-worker：Outbox/Inbox、部署编排和外部回写
  ├─ postgres：PostgreSQL + pgvector
  ├─ redis：缓存/队列
  └─ minio：知识原始资产和解析产物
```

PostgreSQL 容器只负责初始化数据目录并提供 PostgreSQL + pgvector；Docker Compose 不把 `apps/api/app/db/migrations` 挂载到 `/docker-entrypoint-initdb.d`，PostgreSQL 镜像也不打包该目录。因此全新 volume 与已有 volume 共用同一条应用迁移路径：API 镜像打包 `/app/app/db/migrations`，`api-entrypoint.sh` 在服务启动前作为普通 additive migration 的唯一控制面。入口使用阻塞 PostgreSQL advisory lock 与 `app_schema_migrations` 持久化账本：仅执行未登记的文件；每个普通 SQL 文件和其文件名/SHA-256 账本记录作为独立原子事务提交，锁覆盖完整扫描，避免后续失败回滚或长时间持有先前迁移的 DDL 锁；已登记文件内容变化会失败退出，要求新增迁移而非篡改历史文件。它明确跳过破坏性的 `121_requirement_driven_rd_cutover.sql` 和四个大索引迁移 `125_rd_dispatch_due_index.sql` 至 `128_rd_dependency_successor_index.sql`。迁移 121 必须先完成围栏外只读预检，经 `draining` 收敛到零活动并进入不可回退旧运行时的 `cutover_locked`，再在健康标记和显式 cleanup 命令下执行。四个派发索引由正常 API 运行时的 repository schema-compatibility 路径接管：使用 autocommit 连接、共享的非阻塞 PostgreSQL advisory lock 和 `CREATE INDEX CONCURRENTLY`，有效索引直接复用，无效索引并发删除后重建，未取得锁的启动实例立即继续而不等待；如果 Worker 早于入口账本创建目标表启动，则安全跳过并由 API 后续初始化补齐。数据库结构或种子数据变更不得依赖清空 volume。PostgreSQL 服务使用同主版本 pgvector 镜像，避免已有 PG18 数据目录被错误挂载到 PG16。

## 外部依赖

| 服务 | 用途 |
|------|------|
| GBrain | 长期记忆、混合检索、答案合成和知识图谱。 |
| OpenAI-compatible 模型服务 | chat completion 和 embedding。 |
| 本地 GitLab | v1 MVP 拉取 Merge Request 元信息和 diff 快照用于内部代码 Review；v1.2 再采集提交、Merge Request、代码变更量、质量评分和风险摘要，按产品 Git 资源归属。 |
| Jenkins | v1 采集 job、build、部署环境、发布版本、触发人、耗时、状态和失败原因。 |
| 线上运行日志源 | v1 可登记/导入真实聚合指标，后续接入自动采集；聚合错误率、P95 延迟、核心业务事件、top errors 和异常趋势。 |
| 用户使用和反馈数据源 | v1 聚合活跃、功能访问、关键路径转化、异常退出、低使用功能和反馈趋势。 |
| 未来 GitHub/Jira/飞书等系统 | v1 仅预留适配器，默认使用模拟 Issue。 |

## 安全架构

- v1 使用本地账号 + Bearer Token。
- 写操作和任务访问需要鉴权。
- 知识检索必须在数据库查询层完成权限过滤。
- 模型调用日志默认不保存完整 prompt 和输出。
- AI 助手问答使用服务端生成的脱敏 `system_context`；模型调用日志不保存完整用户问题、系统上下文、助手回答或 API Key。
- 所有写操作、AI 高影响动作和研发运营采集结果写入审计事件或运行记录。
- GitLab MR 代码 Review 只读取授权产品 Git 资源和 Merge Request，报告归档在 AI Brain 内部，不回写 GitLab 评论、审批状态或分支变更。
- 外部 Webhook 必须验签、按 Delivery ID 幂等、裁剪并脱敏 payload；失败事件可重试或进入死信，不能重复生成质量、发布或运行证据。
- 执行资源按产品和环境授权，产品成员不能枚举或绑定 scope 外 Runner Target / Jenkins Connection。
- 自动合入和生产部署必须执行独立门禁；严格窗口外、制品/回滚信息不完整、健康检查失败或高风险变更不得静默放行。

## 扩展性设计

v1 不拆微服务，但模块边界保留未来提取点：`graph-runtime-worker`、`execution-worker`、`quality-gate-service`、`knowledge-service`、`long-memory-service`、`model-gateway-service`、`gitlab-review-service`、`code-review-executor-service`、`devops-metrics-worker`、`user-insights-worker`、`iteration-planning-service`、`bug-service`、`dashboard-service`、`integration-service`。

---
最后更新: 2026-07-11
