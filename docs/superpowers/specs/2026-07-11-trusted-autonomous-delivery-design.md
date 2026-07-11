# 可信自治交付与多模态检索设计

## 目标

在现有 Agent 自治循环、质量门禁、Outbox/Inbox、运维部署和多模态解析能力之上，建立可独立验证、可执行验收、可双人复核、可对账、可运营、可预算控制以及支持以图搜图的研发交付闭环。

本设计按三个可独立验证的实现阶段交付，最终在同一功能分支合并推送：

1. P0 可信交付：验证器信任域、签名证明、验收测试计划、生产双人复核和外部结果对账。
2. P1 自治运行治理：执行 Worker 控制台、队列与死信治理、预算预占、无进展熔断和成本统计。
3. P1/P2 知识与技术债：原生图片/区域 Embedding、以图搜图、精确引用与反馈、Starlette/httpx 和 Ant Design 弃用警告收敛。

## 不变约束

- PostgreSQL 是所有业务状态、证明、审批、预算和队列状态的唯一事实源；Redis 不承载不可恢复的业务写入。
- MinIO/S3 仅保存原始资产、解析资产、SBOM 和制品引用；业务元数据、哈希、权限和生命周期状态写入 PostgreSQL。
- 所有模型调用必须经 `model_gateway`，Runner 私钥和外部 Provider 密钥只能保存在 Runner 本地或 `env:`/Vault 引用中。
- 编码、验证、部署、Git 写回和外部对账都必须保留产品 scope、操作者、策略版本、上下文版本和审计事件。
- 不允许 API 进程以全局内存模拟生产 Worker；本地单进程模式只能作为显式测试兼容。
- 高风险生产动作必须 fail closed：证据、审批、签名、资源授权或窗口任一缺失时不可继续。

## 阶段一：可信交付

### 验证器信任域与证明

`ai_executor_runners` 增加以下只读注册字段：

| 字段 | 说明 |
|---|---|
| `trust_domain` | `coding`、`verification` 或 `deployment`；一个 Runner 只能属于一个域。 |
| `trust_boundary_id` | 表示主机、密钥和运维归属的隔离边界。编码和验证 Runner 不得相同。 |
| `attestation_public_key` | 用于验证 Ed25519 执行证明；只保存公钥。 |
| `attestation_key_fingerprint` | 公钥指纹，展示和审计使用。 |
| `attestation_status` | `pending`、`active`、`revoked`；非 active Runner 不能承担自动验证或生产部署。 |

研发执行器策略增加 `verification_trust_policy`。默认值为 `separate_runner_and_boundary`，要求 verifier 与 coding Runner 的 `id`、`trust_domain`、`trust_boundary_id` 都不相同。只有管理员可以配置受限的开发环境兼容模式，生产环境和 `auto_commit` 永远不允许该兼容模式。

新增 `execution_attestations`：

| 字段 | 说明 |
|---|---|
| `id`、`subject_type`、`subject_id` | 可关联 Runner 任务、质量门禁、验收运行、部署运行或对账动作。 |
| `runner_id`、`trust_domain`、`trust_boundary_id` | 证明主体和隔离域。 |
| `payload_json`、`payload_sha256` | 规范化载荷及其哈希。载荷包含上下文、基准/结果 Commit、制品摘要、门禁目录版本、测试摘要、日志摘要和时间。 |
| `signature`、`public_key_fingerprint` | Runner 生成的 Ed25519 签名和公钥指纹。 |
| `verification_status`、`verified_at`、`verification_error` | 平台签名校验结论。 |

Runner 接到编码、verifier、验收、部署或回滚任务时，必须把规范化证明随结果上报。平台服务端校验签名、Runner 注册状态、任务/Commit/制品关联及信任域后，才允许此证据成为质量门禁或部署放行依据。签名无效、载荷哈希不符、签名密钥已撤销、验证器与编码器同边界，都使门禁进入 `blocked`，并写入审计。

### 可执行验收测试计划

新增以下关系：

```text
requirement
  -> acceptance_test_plan
  -> acceptance_test_case
  -> acceptance_test_run
  -> execution_attestation / quality_gate_run / artifact
```

`acceptance_test_plans` 绑定产品、需求、版本、任务和计划版本。状态为 `draft`、`active`、`superseded`、`archived`。计划激活后生成不可变 `plan_snapshot_json`，后续研发任务和发布门禁只使用该快照。

`acceptance_test_cases` 保存 `criterion_ref`、标题、前置条件、执行方式（`automated`、`manual`）、命令目录引用、风险级别、覆盖目标、Flaky 策略和排序。每条需求验收标准必须至少关联一个 active case；未映射时不允许进入自动合入或生产部署。

`acceptance_test_runs` 保存 case、计划快照、任务、Commit、制品、Runner 任务、状态、摘要、覆盖率、失败指纹、重试计数、证据和证明引用。状态为 `queued`、`running`、`passed`、`failed`、`flaky`、`blocked`、`cancelled`。

自动验收失败时，若执行器策略允许自治重试且预算充足，失败 case、失败指纹和签名证据进入下一轮 Agent 上下文。相同 case、相同 Commit/测试输入在最近三次运行中出现至少一次通过与一次失败时，标记 `flaky`；Flaky case 阻断自动放行，必须由测试负责人确认隔离、修复或降级。

质量门禁新增 `acceptance_coverage` 检查：确认计划完整性、必需 case 已通过、覆盖率满足策略阈值、不存在 Flaky/blocked case，以及 case 的证明均由可接受 verifier 信任域生成。

### 生产双人复核、制品和冻结

新增 `production_change_controls`，按产品/环境/风险等级配置：

- `approval_mode`：`single`、`maker_checker`、`dual_control`。
- `required_roles`：生产高风险默认 `release_owner` 和 `ops_owner`。
- `artifact_attestation_required`、`sbom_required`、`freeze_policy_required`。
- `emergency_change_permission`：冻结期内唯一允许进入审批的额外权限。

`deployment_approvals` 每条保存部署单、审批阶段、审批人、角色快照、版本、决定、理由和时间。生产 `dual_control` 要求两名不同用户、不同角色的有效批准；发起人不得批准自己的部署。审批人失去产品 scope、角色或审批版本过期时，批准自动失效。

`release_artifacts` 保存制品名称、版本、SHA-256、SBOM object ref、SBOM 哈希、签名证明、来源 Commit、生成时间和保留状态。生产部署启动前必须匹配目标 Commit 和已验证证明。

`release_freeze_windows` 保存产品/环境、开始结束、原因、创建人和 `active` 状态。冻结期内非紧急部署直接返回 `RELEASE_FREEZE_ACTIVE`；紧急部署需要显式权限、原因和双人复核。

### 外部结果对账

扩展 Outbox 及其 action receipt 状态机：

```text
pending -> dispatched -> succeeded | failed
                    -> unknown -> reconciling -> succeeded | failed | manual_reconciliation
```

Provider 网络超时、连接中断或远端已收到但未回传确认时，不得重新派发原动作，而是写入 `unknown` 和包含 Provider 操作键、Commit、构建号或 Runner 任务号的 `reconciliation_json`。Worker 只认领 `unknown/reconciling` 进行只读 Provider 查询；查询确认后收敛为终态，超过策略阈值则变为 `manual_reconciliation`。

系统管理员或具有对应执行权限的用户只能触发“重新对账”或提交有审计的人工结果，不能将 unknown 直接标记为成功。若 Provider 不支持查询，UI 必须明确显示“需人工核验”，不暴露盲目重试按钮。

## 阶段二：自治运行治理

### Worker 控制台与队列可观测性

新增 `execution_worker_heartbeats`，由独立 Worker 每个轮询周期更新：实例 ID、版本、职责、启动时间、心跳时间、当前 claim 数、累计处理数、最近错误和配置摘要。Worker 未在 `3 * poll_interval` 内上报时显示为 `stale`。

新增聚合 read model `execution_operations_overview`，按产品 scope 返回 Outbox、Inbox、验收、对账和死信的待处理数、最早等待时间、租约超时数、P50/P95 消费延迟、失败率、重试趋势和最近错误类别。只返回脱敏摘要，不返回 Provider 密钥、完整 payload 或 Runner 输出。

新增“系统管理 / 执行 Worker”页面，包含：

- Worker 健康表：心跳、职责、版本、当前 claim、最近错误和过期状态。
- 队列概览：按产品、Provider、动作、环境和时间筛选的积压、延迟、失败和死信趋势。
- 操作台：对账、允许重试、转人工；所有操作使用现有权限和产品 scope，写入审计。

### 预算、无进展与熔断

新增 `agent_budget_ledgers`，记录 `product`、`task`、`policy` 三种范围的 `reserved`、`consumed`、`released` Token/费用/时长、周期、阈值和当前余额。任务进入自治模式前必须原子预占最大额度；每轮使用后原子结算；终止、人工接管、取消或完成时释放未使用预算。

新增 `agent_loop_circuit_breakers`，保存任务、状态、触发类型、失败指纹、连续次数、无进展次数、触发轮次、恢复人和恢复理由。以下任一条件触发熔断：

- 连续两轮相同失败指纹。
- 连续三轮必需验收项、质量门禁或测试状态无改善。
- 预算、Token、费用或最大运行时长耗尽。
- 验证证据不可信、检测到受保护路径或策略明确要求人工处理。

熔断后的任务进入 `waiting_human_takeover`，不允许自治 Worker 再次创建编码任务。只有具备任务执行权限且在产品 scope 内的人员可以恢复；恢复必须选择“调整预算”“修改验收计划”“更新策略”或“人工确认风险”之一，并留下理由。

新增产品、策略、Runner 和任务维度的成本 read model，展示 Token、金额、轮次、成功率、人工接管率、熔断率及 80%/100% 预算阈值告警。预算配置、阈值告警、熔断和恢复都写入审计。

## 阶段三：原生多模态检索与技术债收敛

### 图片和区域检索

新增 `knowledge_visual_embeddings`：

| 字段 | 说明 |
|---|---|
| `knowledge_document_id`、`document_version_id`、`asset_id` | 绑定权限主体和不可变文档版本。 |
| `page_number`、`bounding_box`、`region_kind` | 指向整图、PDF 页、图表、表格或 OCR/版面区域。 |
| `content_hash`、`embedding_model`、`embedding_dimension`、`embedding` | 版本化视觉向量及兼容性信息。 |
| `processing_profile_id`、`provider_metadata` | 生成来源和脱敏 Provider 元数据。 |
| `status`、`created_at` | `ready`、`failed`、`superseded` 和生命周期时间。 |

多模态处理 Profile 新增 `image_embedding` 能力。Provider 接口接收对象存储受控读取流或短期内部引用，返回图片/区域向量及可选区域标注；不得把长期公开 URL 或对象存储凭据传给前端或 Provider。解析失败不会覆盖当前 active 版本，失败信息写入导入任务和质量事件。

新增 `POST /api/knowledge/search/visual`。请求可含文字、单张查询图片或两者；查询图片仅保存为短期临时资产，过期自动清理。服务端先在数据库查询层应用知识空间权限和文档版本过滤，再执行文本向量、视觉向量和关键词候选检索，最后按策略重排。响应返回已鉴权的 preview token、document/version/asset/page/region、模态、相似度、Provider 和引用信息。

知识中心搜索弹窗增加本地选择/粘贴图片、图片缩略图、图文模式、区域高亮、定位预览和“相关/不相关/区域错误”反馈。AI 任务上下文和知识问答的引用扩展为 `asset_id/page_number/bounding_box`，确保回答可定位到具体图表或图片区域。

### 测试与前端技术债

后端测试 HTTP 客户端收敛到一个 `httpx.ASGITransport` 兼容工厂，去除 Starlette TestClient 对旧 httpx 路径的弃用告警，保持现有同步测试调用方行为稳定。不得只通过忽略 warning 或全局过滤 warning 来掩盖问题。

前端将废弃 Ant Design 属性替换为当前组件 API，例如 `Alert.message` 改为 `Alert.title`。Vitest 配置把 React/Ant Design 的 `console.warn/error` 中已知弃用警告视为失败，确保新增代码不会重新引入。

## API、权限与审计

新增 API 按下列权限和产品 scope 执行：

| API 类别 | 主要权限 |
|---|---|
| 信任域、证明和生产控制策略维护 | `system.settings.manage` |
| 验收计划和 Case 维护 | `requirement.manage` 或产品测试职责权限 |
| 验收运行和质量证据查看 | `task.read`、`quality.read` 且产品 scope 匹配 |
| 对账、死信重试和转人工 | 对应动作执行权限及产品 scope；系统级队列列表额外要求 `system.health.read` 或 `audit.read` |
| 预算策略维护 | `system.settings.manage`；成本查看按产品 scope |
| 生产审批 | 发布/运维职责与 `deployment.execute`；发起人隔离由服务端强制 |
| 视觉检索和反馈 | `knowledge.read`/`knowledge.manage` 和知识空间权限 |

所有创建、更新、签名验证、审批、拒绝、冻结、对账、死信处理、预算预占/释放、熔断/恢复、视觉检索及反馈都必须写审计事件，并返回 `trace_id`。

## 失败语义

- 不存在可用且隔离的 verifier Runner：`VERIFIER_TRUST_DOMAIN_UNAVAILABLE`。
- 执行证明签名、哈希或注册状态不符合：`EXECUTION_ATTESTATION_INVALID`。
- 验收标准未覆盖、存在 failed/flaky/blocked case：`ACCEPTANCE_GATE_BLOCKED`。
- 生产审批不满足、审批人与发起人相同、证据过期：`PRODUCTION_APPROVAL_BLOCKED`。
- 冻结窗口阻断：`RELEASE_FREEZE_ACTIVE`。
- 外部结果不确定：`EXTERNAL_OPERATION_RECONCILIATION_REQUIRED`。
- 预算无法预占或已耗尽：`AGENT_BUDGET_EXHAUSTED`。
- 循环熔断：`AGENT_LOOP_CIRCUIT_OPEN`。
- 图片检索没有有效 Profile 或向量：`VISUAL_SEARCH_UNAVAILABLE`。

## 验收与测试策略

每项新业务行为先添加失败的后端或前端测试，再写最小实现。测试至少覆盖：

1. 相同信任边界的 verifier 被拒绝；不同边界且有效签名的证明可以放行。
2. 错误签名、撤销密钥、证明与 Commit/制品不匹配均阻断自动合入。
3. 每条需求验收项都有 active case；case 失败进入下一轮；Flaky case 阻断自动放行。
4. 生产部署发起人不能审批；双角色审批、SBOM、签名和冻结窗口均满足时才可启动。
5. 外部超时进入 unknown；对账确认后进入终态；无法确认时只能人工处理。
6. Worker 心跳过期、租约超时、死信和重试趋势可被 scope 过滤后正确显示。
7. 预算预占、结算、释放、80%/100% 告警、重复失败熔断和人工恢复的原子性。
8. 图片上传/粘贴、视觉向量、按知识权限过滤、以图搜图、区域引用、旧版本回退和反馈。
9. 后端完整 pytest、Ruff；前端 TypeScript、Lint、Vitest、生产构建；真实 PostgreSQL API + Worker + Web 页面验收。

## 非目标

- 不引入第三方 CI/CD SaaS 或 Kubernetes 控制器。
- 不把 Runner 私钥、SSH 私钥、SBOM 正文、外部 payload 或模型完整输出写入审计或前端响应。
- 不在无视觉 Embedding Profile 的环境中伪造以图搜图结果；应返回明确不可用状态。
- 不允许人工直接编辑质量门禁、签名证明、预算账本或已完成外部动作的终态。
