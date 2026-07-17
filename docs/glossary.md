# 术语表

## A

### ADR
Architecture Decision Record，架构决策记录。用于记录项目中重要的架构决策及其背景、理由和后果。

### API
Application Programming Interface，应用程序编程接口。定义了软件组件之间交互的方式。

### AI Task
AI 任务。AI Brain 中承载产品详细设计、技术方案、代码 Review、自动化测试、发布评估或上线后分析的底层可执行任务实体。v2.0 中研发 AI 任务只能由协作编排器通过内部领域服务为工作项创建、派发、恢复和取消；公开创建、启动、批量重试和取消接口不再是研发协作入口。

### AI Digital Employee
AI 数字员工。可跨版本识别的持久化员工主体，保存稳定身份、所属业务大脑、能力标签和人格/工作风格版本。它与研发岗位、执行器相互独立：岗位定义职责，员工表示承担者，执行器提供模型或 Runner 运行能力。

### Ant Design Pro
React 后台工作台模板。AI Brain v1 前端工程以其布局、菜单、权限和页面脚手架为起点，但运行时必须保持本仓库独立安装、构建和部署。

## B

### Bearer Token
一种身份验证令牌，持有者可以使用该令牌访问受保护的资源。

## C

### Collaboration Run
研发协作运行。以产品版本为根聚合并包含一组已评估需求；同一版本同一时刻最多一个活动运行。启动时把同一 policy ID/version 的多需求 final/effective 快照按 merge operator 确定性收紧为唯一 version_resolved 快照，并用不可变运行范围逐条冻结需求修订、评估、最终快照、验收标准和仓库范围；数据库保证范围与策略来源完全一致。运行进入人工等待时保存原阶段、决策请求和暂停时间，处理后按冻结阶段恢复。failed/cancelled 运行不可重开，restart 只能创建引用最近终态运行的新 generation，旧工作项、attempt 和证据保持不可变。

### Command Idempotency Record
研发命令幂等记录。为评估、协作启动、终态运行 restart、领取、提交、审核、人工决策、决策补充答案、工作项取消和经验审核保存命令类型、聚合主体、幂等键、规范化请求哈希、结果引用和脱敏完整响应快照；与领域写入同事务提交，相同键不同摘要必须冲突。领取 token 单独保存在可擦除的限时加密 replay-secret 记录中，仅在原租约有效期内返回同一 attempt/token，到期擦除密文后旧键固定失败。

### CI/CD
Continuous Integration / Continuous Deployment，持续集成/持续部署。自动化代码集成、测试和部署的实践。

### Code Review Executor
代码 Review 执行器。AI Brain 中用于把内部 GitLab MR diff、需求摘要、技术方案和项目规范转成结构化 Review 报告的可插拔边界，一期默认适配 Claude Code `code-review` skill。

## D

### DDD
Domain-Driven Design，领域驱动设计。一种软件开发方法，强调业务领域建模。

## E

### E2E
End-to-End，端到端测试。验证完整系统流程的测试类型。

## G

### GBrain
长期记忆和公司大脑层。AI Brain 使用 GBrain 作为补充检索、答案合成和知识图谱能力，不替代 PostgreSQL 中的产品、需求、任务、审计和权限数据。

## J

### JWT
JSON Web Token，一种用于身份验证的令牌标准。

## L

### LangGraph
用于 AI 工作流编排的状态图框架。AI Brain 用它管理任务图和版本级协作图，并通过 PostgreSQL Checkpointer 保存真实检查点、人机中断和恢复状态；领域服务仍拥有状态迁移最终控制权。

### Lifecycle Context
研发上下文图谱。用于串联需求、设计、方案、代码、Review、测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件。

## M

### Microservices
微服务。一种架构风格，将应用拆分为小型、独立的服务。

### Model Gateway
模型网关。AI Brain 中统一承载 chat 和 embedding 模型调用的边界，业务模块不得直接依赖供应商 SDK。

## P

### PR
Pull Request，拉取请求。代码合并请求，用于代码审查和讨论。

### PRD
Product Requirements Document，产品需求文档。描述产品功能需求的文档。

### pgvector
PostgreSQL 向量扩展。AI Brain v1 用它在 PostgreSQL 中存储 embedding 并执行向量检索。

### Planning Version
规划版本。状态为 `planning` 的产品版本，可接收评估通过的需求。系统优先将需求归入兼容规划版本，只有不存在合适候选时才创建新版本。

## Q

### QPS
Queries Per Second，每秒查询数。衡量系统处理能力的指标。

## R

### R&D Decision Request
研发决策请求。工作项遇到高风险、超权限、预算超限、冲突、门禁失败或部署边界时创建的持久化人工决策记录。选项冻结 outcome、主体状态映射、输入 Schema 与影响预览，服务端按映射执行；要求补充信息时进入 `waiting_more_info`，通过 answers 子资源形成新版本后再决策。请求还冻结 expires_at、超时策略和升级对象；默认到期后主体继续暂停，系统幂等创建后继升级请求，不自动批准或恢复。

### R&D Executor Profile
研发执行器档案。描述模型或 Runner、工作区能力、并发、可承担岗位和健康状态，不保存 AI 员工身份或密钥明文；策略快照把它与本次 AI 员工席位绑定。

### R&D Role
研发岗位。独立于系统 RBAC 的动态组织角色，用于定义产品、项目、开发、测试、文档、运营、安全等职责与能力；协作席位由 AI 数字员工或真人账号承担，AI 席位另行绑定执行器。

### R&D Role Experience
岗位经验。P1 由 P0 不可变岗位反馈证据生成的版本化经验记录，状态为 `pending/approved/rejected/retired`。反馈证据分别冻结被归因执行主体与实际 producer subject/role/seat，审核人通过所有来源关系与任一生产者隔离，不能用被评价对象替代生产者判断。只有平台能力标志和运行冻结的 `experience_reuse_config` 同时允许，并通过权限、业务大脑、产品、岗位、工作项、场景、风险、仓库/工具信任域、最低置信度、最大时效、容量和策略兼容校验的 approved 版本，才能以带证据引用的只读上下文进入后续协作；不能直接修改 active 策略、预算、权限或质量门禁。

### R&D Execution Policy
统一研发执行策略。原研发执行器策略原位升级后的一套规则，统一控制需求评估、版本归组、岗位、岗位执行器、预算、质量门禁、Git、经验复用、风险和交付终点；不存在旧/新双模式、评估/版本显式策略覆盖或策略外自动回退。主记录以 `policy_version` 乐观锁更新，同产品最多一个 active 产品策略、同业务大脑最多一个 active 默认策略，产品策略优先。

### R&D Scope Version
研发范围版本。持久化在 `product_versions.scope_version` 的单调递增版本号；需求成员/修订/验收、final 策略快照、仓库、分支等协作冻结输入在无活动运行时变化会原子递增，协作启动/restart 必须提交当前值。某 generation 启动后范围完全冻结，普通变更入口返回 `RD_SCOPE_FROZEN`；进入 `ready_for_release/deploying` 前只能通过带期望 scope/generation 和类型化 operations 的受控范围请求，由人工决策原子终结旧运行、应用范围并仅递增一次，再用返回的 `terminal_run_id` 创建新 generation。进入待发布或部署阶段后只能创建必带来源运行、延续/替代时可带旧需求血缘的后续需求并进入新的 planning 版本，过期请求不能静默扩大或缩小范围。

### 受控范围变更（Scope Change Request）

协作运行启动后的唯一范围调整命令。请求保存来源运行、期望范围版本/代次、类型化 operations、规范化哈希和人工决策；批准时在一个事务内终结旧运行、全量应用或全量回滚、递增一次 `scope_version`，拒绝时恢复旧运行原阶段。它不是第二套组版入口，也不能修改待发布后的原版本。

### Ready for Release
待发布。产品版本已完成开发、测试、独立质量门禁和策略要求的远程代码提交，但尚未执行部署的状态。待发布目标下协作运行以 `completed(completion_reason=ready_for_release)` 结束；部署目标下协作运行保持非终态 `ready_for_release`，直到部署成功后以 deployed 原因完成。

### rd_brain
研发大脑。AI Brain v1 默认业务大脑，用于把研发需求转化为可确认、可回写、可沉淀的研发任务闭环。

## S

### SLO
Service Level Objective，服务等级目标。定义服务性能目标的指标。

### SLA
Service Level Agreement，服务等级协议。服务提供者与用户之间的正式协议。

## T

### TDD
Test-Driven Development，测试驱动开发。先写测试再写实现的开发方式。

### Test Case
测试用例。描述测试输入、执行条件和预期结果的文档，用于验证软件功能是否符合需求。

### Strategy Snapshot
策略快照。独立持久化的不可变统一研发执行策略事实，包含策略版本、父快照、快照类型、解析上下文与轮次、Schema、内容哈希和完整规范化 payload。base 使用 revision 0 且无父节点；assessment_resolved 引用同策略版本父节点并只允许 revision 1–2，没有收紧差异时评估 final/effective 复用 base；version_resolved 在协作启动时确定性合并同版本全部需求 final/effective，并用不可变来源关系逐条追溯 requirement/assessment，且来源集合必须与运行需求范围完全一致。评估、岗位意见、协作运行、反馈和经验来源通过限制删除的外键引用；数据库拒绝更新/删除快照及来源，不能由当前策略重算覆盖。

### Maintenance Fence
维护围栏。一次性升级使用 `disabled/draining/cutover_locked` 三阶段持久化状态；draining 阻止新增研发写入和 Runner 新领取，但允许在途收敛与管理员受控取消，且在 Schema v2 激活和 cleanup 开始前可以审计化中止。零活动和备份后进入 cutover_locked，此后不得恢复旧运行时，只能向前重试；不影响现有定时作业。

### AC
Acceptance Criteria，验收标准。定义用户故事完成的条件，是测试用例设计的依据。

## U

### Unit Test
单元测试。对软件中最小可测试单元进行验证的测试类型。

## W

### Work Item
工作项。协作运行中带负责人席位、输入输出契约、验收标准、风险、依赖和审核人的最小交付单元；无依赖项可并行，审核失败时通过新返工项保留证据链。

---

## 缩写对照

| 缩写 | 全称 | 中文 |
|------|------|------|
| AC | Acceptance Criteria | 验收标准 |
| AI Task | AI Task | AI 任务 |
| API | Application Programming Interface | 应用程序编程接口 |
| ADR | Architecture Decision Record | 架构决策记录 |
| CI/CD | Continuous Integration/Deployment | 持续集成/部署 |
| E2E | End-to-End | 端到端 |
| JWT | JSON Web Token | JSON 网络令牌 |
| PR | Pull Request | 拉取请求 |
| PRD | Product Requirements Document | 产品需求文档 |
| QPS | Queries Per Second | 每秒查询数 |
| SLA | Service Level Agreement | 服务等级协议 |
| SLO | Service Level Objective | 服务等级目标 |
| TDD | Test-Driven Development | 测试驱动开发 |
| TC | Test Case | 测试用例 |

---
最后更新: 2026-05-29
