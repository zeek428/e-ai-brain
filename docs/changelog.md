# 变更日志

所有重要的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 外部执行安全复核补齐：重复 Webhook 仍需先验签且 Delivery 冲突返回 409，公开确认响应不再回显 payload；Git 写回在 Worker 派发前重新校验连接写权限；灰度、分批和蓝绿部署缺少健康证据时不得推进下一波。
- 研发任务新增可治理的 Agent 自治循环：执行器策略支持单次/自治模式、最大轮次、总时长、Token/费用预算和独立质量门禁；任务详情展示每轮计划、修改、验证、失败分析、预算与停止原因，并提供人工接管。
- 自动提交升级为门禁后合入：编码 Runner 成功只推进到平台 verifier，单元测试、类型检查、静态/凭据/依赖扫描、CI、变更范围和受保护路径由独立质量门禁判断；证据不足、迁移或高风险变更自动降级为人工确认。
- AI Task 新增版本化执行上下文清单，冻结需求、Bug、仓库、分支、产品知识版本、召回原因、验收标准、权限和截断信息，任务详情可逐项核对 AI 实际收到的上下文与验收映射。
- 执行副作用新增事务 Outbox/Inbox 和独立 execution worker：部署状态、运行、审计与派发意图原子写入，Runner/Jenkins/Git 写回幂等执行；GitHub/GitLab/Jenkins/Prometheus/OpenTelemetry/Sentry 等事件支持验签、Delivery ID 去重、失败重试和死信治理。
- 系统管理新增“执行资源授权”，把 Runner Target 或 Jenkins Connection 按产品和环境授权；部署方案候选和启动前预检均阻止 scope 外资源，授权状态使用版本冲突保护。
- 运维部署补齐生产安全闭环：严格执行部署窗口与制品/版本/资源/回滚预检，支持全量、灰度、分批、蓝绿发布，部署后健康检查和冒烟验证，SSH/Docker/Jenkins 真实回滚运行，以及失败后的自动回滚或人工接管。
- 运维部署新增结构化详情抽屉，展示方案快照、前置质量门禁、发布波次、部署/验证/回滚运行、步骤证据、健康检查、派发与审计；部署单和部署方案列表均支持服务端分页、筛选、白名单排序和查询耗时观测。
- 知识中心新增版本化多模态治理：支持可插拔 HTTP/MinERU/PaddleOCR/Gotenberg/多模态网关处理 Profile，图片/PDF 的 OCR、版面、表格和图片描述资产，文档版本切换、过期扫描、版本化引用反馈，以及带页码、位置框、模态和 Provider 元数据的检索来源。
- GitHub/GitLab 官方插件模板增加 Webhook Secret、允许事件、产品/版本/环境上下文和受控 PR/MR 写回权限；Jenkins 与可观测性模板增加真实事件接入配置，插件管理可查看外部 Delivery 和重试失败事件。
- 运维部署新增产品级部署方案和四种执行方式：人工部署保留人工结果登记，SSH/Docker 通过具备部署能力的本地 Runner 隔离执行，Jenkins 通过集成连接触发并后台同步；部署单固化方案快照，统一展示日志、取消中状态和外部执行结果，并新增 `deployment.scheme.manage` 权限。
- 运营治理新增独立“运维部署”菜单和 `/governance/deployments` 页面：部署查看、创建、执行和取消按独立权限显示，版本驾驶舱与需求全链路部署入口同步切换；日志监控排除部署单，仅保留 GitLab、Jenkins 和线上日志指标。
- 需求交付新增运维部署环节：测试完成或待发布需求可在运维部署页发起部署单，启动后进入部署中，部署成功推进到已发布，失败或回滚退回待发布并生成部署失败 Bug；迭代版本驾驶舱、全链路、运营统一列表、权限和帮助文档同步展示部署证据。
- 产品管理“配置”弹窗新增成员权限维护：支持查看产品成员、添加或移除产品经理、研发负责人、开发、测试、运维/发布和观察者等产品职责，后端按产品成员派生产品 scope、职责权限和菜单可见性，并记录 `product.members.updated` 审计事件。
- 产品成员权限补齐业务数据范围收口：研发任务、需求详情/写操作、Bug 写操作和待确认 Review 均按产品成员派生的产品 scope 校验；成员候选人对产品范围内管理员改为关键字搜索，并为成员整体保存增加 `revision` 冲突检测，避免并发覆盖。
- 定时作业新增“同步钉钉文档”官方模板：数据来源可读取内部用户洞察、需求、产品、Bug 或其他已配置连接数据，AI 输出 `dingtalk_markdown` 后调用“钉钉文档 - 更新内容”动作同步到钉钉文档；需要转需求时可额外增加“创建需求”结果动作，钉钉文档链接会在执行侧解析为文档节点 ID。
- 定时作业新增/编辑表单将首段配置统一为“数据来源”，支持“直接取数连接”和“授权连接 + 读取动作”两种模式；读取动作会按 Schema 展示参数字段，并将来源方式保存到 `config_json.orchestration.data_source_mode`。
- 定时作业“创建需求”结果动作增加产品范围与幂等保护：候选需求只能写入作业所属产品，同一运行因 Runner 重试或重复回调再次写入时复用已有需求；异步 Runner 完成结果动作时沿用真实任务发起人权限快照，不再伪造管理员身份。
- 系统健康页权限诊断区新增“用户视角预览”入口，可输入用户 ID 查看真实可见入口、阻断入口、缺失权限点和 scope 摘要。
- 产品接入完整度评分新增分项矩阵：系统健康页按主数据、版本、模块、代码仓库、知识、关联系统、插件连接、权限范围和最近健康展示得分、状态、证据和建议。
- 系统健康告警通知 outbox 补齐投递闭环：新增 `POST /api/system/alerts/notifications/dispatch`，支持站内通知、系统 SMTP 邮件、Webhook/钉钉 URL 投递和失败重试，回写 `sent/failed/skipped`、`attempts`、`last_error`、`sent_at` 与脱敏投递摘要，系统健康页新增“投递通知”和“重试失败”操作。
- 帮助中心截图自动化补齐全路由覆盖：前端帮助内容为 24 个业务路由配置 25 张页面截图目标，截图脚本从 `apps/web` 加载 Playwright 并使用本机 Chrome，截图前自动脱敏邮箱、钉钉企业 ID 和 token-like 字符串，`help:check:strict` 可校验截图覆盖、双份一致性和过期状态。
- 系统健康告警订阅新增通知 outbox：新增 `system_alert_notifications` 表，系统健康物化告警时按启用订阅、严重级别和 scope 生成幂等待投递记录，前端展示待通知数量和最近通知目标，便于后续 SMTP/钉钉/webhook 投递器追踪处理状态。
- 系统健康告警处理补齐状态流转时间线：`PATCH /api/system/alerts/{alert_id}` 会向 `metadata.status_history` 追加处理记录，系统健康页处理弹窗展示最近处理时间、状态变化、负责人、关闭原因和复盘状态。
- 系统健康告警订阅补齐管理闭环：新增 `PATCH /api/system/alerts/subscriptions/{subscription_id}`，系统健康页展示已有订阅的渠道、目标、级别和范围，并支持直接启用或停用订阅。
- 系统健康“对象存储同步清理”补齐补偿操作闭环：新增 `POST /api/system/object-storage/cleanup` dry-run/confirmed 接口，系统健康页支持预检并二次确认清理孤儿知识资产对象，删除失败会保留资产记录并返回错误，成功清理写入脱敏审计。
- 帮助中心截图自动化新增覆盖报告和严格门禁：`check_help_center_assets.mjs` 支持 `--json`、`--strict-screenshots` 和截图覆盖率统计，`apps/web` 新增 `help:check`、`help:check:strict`、`help:screenshots:list` 脚本，便于在本地或 CI 中发现缺截图路由。
- 系统健康“安全审计治理”新增治理动作清单：后端按异常密钥引用、直接密钥配置、敏感配置变更、高风险操作、审计导出和管理员周报生成下一步动作，前端在系统健康页直接展示处理建议且不回显密钥值。
- 系统健康“帮助截图自动化与数据归档策略”增强截图覆盖来源：后端从前端帮助中心内容自动派生截图目标，避免新增帮助截图后遗漏系统健康覆盖清单。
- 系统健康“AI 任务执行运维台”新增策略配置矩阵：`ai_executor_ops.strategy_config` 返回任务超时、租约回收、死信阈值、手动重试、手动取消和 Runner 心跳策略的阈值范围、配置来源、可处理状态集合和风险提示，前端同步展示策略配置状态和策略说明。
- 系统健康“帮助截图自动化与数据归档策略”新增只读清理体检：`help_and_retention.cleanup_status` 汇总审计、执行链路、模型日志、作业运行和知识导入任务的超过保留期候选，`object_storage_cleanup` 汇总知识附件孤儿引用、对象信息不完整和清理失败计数，帮助管理员先导出证据再按策略归档或补偿清理。
- 系统健康“知识中心质量闭环”新增治理待办清单：后端返回 `governance_summary` 和 `governance_candidates`，按索引失败、仅关键词索引、无分片和长期未更新识别低质量/过期文档，并给出严重级别、知识空间和建议动作；前端在平台治理运维台直接展示待处理文档。
- 系统健康“钉钉授权生命周期”补齐统一授权主体治理：后端按钉钉 MCP 连接返回个人/系统/应用主体统计、企业名称或 CorpId、URL Key 到期时间、剩余天数、测试状态和边界说明，前端展示授权边界说明和连接级主体清单，便于管理员识别个人授权离职风险、系统授权轮换风险和未声明主体配置。
- 知识中心 RAG 问答前端补齐质量闭环：问答卡片展示引用来源，点击引用会写入引用点击事件，“有用/无用”反馈会关联本次 `quality_event_id` 写入质量事件，用于无结果率、引用点击率和 RAG 引用准确率 proxy 后续运营统计。
- 角色管理权限诊断新增用户菜单视角预览和保存前风险预检：后端新增 `GET /api/system/permissions/menu-preview` 与 `POST /api/system/roles/{role_id}/risk-precheck`，前端可查看目标用户实际可见菜单、阻断入口、scope 对比和自动修复建议，并在菜单权限缺口时阻断保存。
- 系统健康告警中心补齐事件闭环：新增 `system_alert_incidents`、`system_alert_subscriptions`、`knowledge_quality_events` 结构表，`PATCH /api/system/alerts/{alert_id}` 支持认领、处理中、关闭、忽略并记录负责人、关闭原因和复盘，`POST /api/system/alerts/subscriptions` 支持创建告警订阅；系统健康页同步展示告警状态、趋势和订阅摘要。
- 系统告警补齐规则和周报闭环：新增 `system_alert_rules` 表与 `GET/POST/PATCH /api/system/alerts/rules`，告警物化时记录命中规则；新增 `GET /api/system/admin-weekly-report` 生成管理员周报 Markdown，系统健康页可直接查看。
- 知识中心质量闭环新增持久化观测：`POST /api/knowledge/search` 与 `/api/knowledge/rag` 自动记录检索/RAG 质量事件，新增 `/api/knowledge/quality/metrics`、`/api/knowledge/quality/feedback`、`/api/knowledge/quality/citation-click` 支持无结果率、引用点击率、有用/无用反馈和 RAG 引用准确率 proxy 汇总。
- 新增帮助中心维护脚本：`scripts/check_help_center_assets.mjs` 校验帮助文档路由、截图文件和截图过期状态，`scripts/capture_help_screenshots.mjs` 使用 Playwright 按路由刷新帮助截图。
- 审计事件新增 CSV 导出接口 `GET /api/audit/events/export`，复用审计事件筛选条件导出最近 1000 条摘要记录。
- 系统管理“系统健康”升级为平台治理运维台：`GET /api/system/health` 新增 `operations` 聚合，覆盖系统健康告警中心、AI 任务执行运维台、知识中心质量闭环、产品接入完整度评分、权限诊断增强、钉钉授权生命周期管理、帮助截图覆盖和数据归档策略；前端同步展示七块治理视图、评分条、告警列表和运维跳转入口。
- 新增系统管理“系统健康”配置体检中心：后端 `GET /api/system/health` 聚合 PostgreSQL、Redis、pgvector、MinIO/S3、SMTP、钉钉登录、钉钉 MCP、模型网关、知识质量、AI 执行器、定时作业、观测告警和产品初始化状态；前端新增 `/system/health` 页面展示整体状态、优先处理项、分类检查、最近错误和修复建议，并提供执行诊断、权限诊断、模型网关和插件运维快捷入口。
- 产品管理新增“产品接入向导”：按产品主数据、版本模块、Git 资源、知识空间、插件连接、角色范围和系统健康复检串联新产品接入路径；viewer 仅可查看向导，不展示新增入口。
- 新增系统内“帮助中心”页面和顶部/头像菜单入口，支持按模块浏览、关键词搜索、跳转业务功能；同步补齐 `docs/08-help/` 快速开始、业务工作台、需求交付、产品资产、任务治理、系统管理和 FAQ 用户手册。
- 新增 `docs/08-help/` 帮助中心维护入口，定义用户操作手册、截图目录、截图脱敏规范和开发完成后的帮助文档同步检查清单。
- 账号密码登录新增轻量数字安全校验：前端登录页先获取一次性计算题并随用户名密码提交，后端以 PostgreSQL/测试内存仓储保存 TTL 挑战并原子消费；钉钉 OAuth 登录不受影响。
- 知识中心升级为工作台：新增空间/目录导航、RAG 问答入口、引用展示、检索命中详情抽屉和 multipart 文件上传，上传时必须选择知识空间，沉淀采纳也必须显式进入空间。
- 知识检索新增 PostgreSQL 内 Hybrid Search：同一权限过滤下执行 pgvector TopN 与关键词 TopN，并通过 RRF 融合；新增 `POST /api/knowledge/rag` 返回带引用答案和检索/RAG 质量指标。
- 知识上传链路新增安全校验和真实 PDF 解析：支持文件大小、扩展名、MIME、PDF 签名校验，新增 MinIO/S3 预签名上传信息接口和 `pypdf` 文本抽取。
- 首页 IT 团队看板接入真实趋势数据和 Ant Design Charts：后端基于同一批 PostgreSQL source rows 输出交付、风险、工程和用户四类日趋势，前端以专业折线图展示并在测试环境提供文本降级。
- AI 助手最近对话新增删除能力：左侧历史记录可删除单条或折叠重复组，后端校验当前用户归属并清理对应消息、聊天运行和由消息生成的助手草案记录，同时写入删除审计。
- 新增个人中心账号资料维护：登录用户可修改显示名称、邮箱、手机号和登录密码，并可查看、绑定、重新绑定或解绑钉钉账号；已有 AI Brain 账号必须先本地登录再显式绑定钉钉，服务端按钉钉稳定身份写入 `user_external_identities`，资料变更审计仅记录变更字段。
- 新增钉钉登录 P0：支持认证 provider 查询、钉钉 OAuth start/callback、一次性 ticket 换取 AI Brain Token、外部身份绑定表、登录页钉钉入口、回调页和自助绑定/解绑后端接口，并同步设计文档、API 契约和错误语义。
- 钉钉登录 P1 加固：OAuth state 与一次性 login ticket 改为后端仓储持久化并原子消费，新增 PostgreSQL 迁移承载多 worker / 重启场景下的回调状态。
- 补充钉钉登录本地启用配置示例，明确 `GET /api/auth/providers` 与 `DINGTALK_*` 环境变量决定登录页入口展示。
- 文档集按业务域和 API 分册拆分：`api.md` 收敛为 API 入口索引，接口细节迁入 `docs/02-specs/enterprise-ai-brain/api/`；`spec.md` 与 `test-case.md` 的长版本历史迁入 `history/`；拆分前完整 changelog 归档到 [releases/changelog-2026-07-03-pre-split.md](releases/changelog-2026-07-03-pre-split.md)。
- 系统管理“系统设置”页面扩展系统级邮件发送配置：支持维护系统管理员邮箱、发件邮箱、默认发件人、Reply-To、SMTP Host/端口/TLS/用户名、密码或密钥引用，并提供 `POST /api/system/settings/email/test` 测试发送；响应和审计仅记录配置状态，不回显 SMTP 密码。
- 插件市场新增钉钉官方 MCP P0 标准插件：文档、知识库、钉盘、AI 表格、机器人消息和通讯录能力按独立标准插件接入，支持 `mcp_streamable_http`、URL Key 鉴权、P0 动作模板和请求摘要脱敏。
- 钉钉官方 MCP 插件增强授权配置向导、`tools/list` 动态能力发现、高风险动作治理、插件健康看板和 AI Brain 业务场景模板，并新增动态发现与钉钉观测 API。
- 钉钉官方动作模板补充“钉钉文档 - 更新内容”场景，并统一钉钉动作模板名称为“钉钉能力 - 操作”前缀，便于新增动作配置场景检索。
- 结果写入目标新增“钉钉文档”：动作表单可视化配置文档链接或 ID、写入内容和追加/覆盖方式，粘贴 `alidocs.dingtalk.com/i/nodes/...` 链接时自动提取文档节点 ID，并生成 MCP `nodeId/markdown/mode` 参数，无需手工编辑高级 JSON。
- 动作试运行输入改为默认按已保存动作配置执行，并将临时覆盖 JSON 收纳到高级区域；钉钉文档更新动作会直接展示文档 ID、写入方式和写入内容摘要，降低试运行配置门槛。
- 钉钉文档写入动作兼容历史缺少 `request_config.tool_name` 或使用旧别名的配置：运行和试运行时会按 `result_mapping.write_target=dingtalk_document` 自动补齐真实 MCP 工具 `update_document`、钉钉 MCP 信息，并把文档链接/内容转换为 `nodeId`、`markdown`、`mode` 参数，避免出现 `tool_name is required` 或 “not found the specified tool”。
- Bug 管理新增“推进 AI 任务”能力：`POST /api/bugs/{bug_id}/promote-ai-task` 会创建 `bug_fix` AI Task，写入 Bug 自动化任务引用并默认复用研发执行器策略自动启动，前端行操作新增“AI处理”入口。

### Changed
- 系统健康告警中心补齐前端操作闭环：页面支持处理告警状态、填写负责人/关闭原因/复盘记录，新增告警订阅，新增规则并启停已有规则。
- 审计与运行页面新增“导出 CSV”入口，复用当前筛选和排序调用审计导出接口，下载最近 1000 条脱敏摘要记录，便于管理员检索后留档。
- 产品接入完整度评分改为纳入真实健康信号：插件连接会统计失败测试结果，知识文档只按可检索索引计分，并返回 `recent_health_check` 摘要、失败插件数、权限范围状态和可检索文档数。
- 产品接入完整度评分进一步纳入插件连接、产品权限范围和最近健康状态；权限诊断返回保存角色前风险预检、菜单权限缺口自动修复建议、用户视角菜单预览说明和 viewer/read/write/admin scope 对比；钉钉生命周期返回个人/系统/应用授权边界说明和连接授权主体摘要。
- 系统健康页新增安全审计治理卡片，展示敏感配置审批策略、高风险二次确认、密钥引用校验、直接密钥配置数量、审计导出入口和近 7 天管理员周报摘要，全程不回显密钥值。
- 系统设置邮件发送配置变更新增后端强制二次确认：首次配置或修改 SMTP 发信敏感字段时必须携带确认原因，审计只记录字段、配置状态和确认状态，不记录密码、授权码或确认原因全文。
- AI 任务执行运维台新增可处理任务闭环：`GET /api/system/health` 返回最近活跃任务、最近失败任务和可取消/可重试/待扫超时计数，系统健康页可直接执行超时扫描、取消活跃任务或重试失败任务。
- 帮助中心截图自动化增强：截图采集脚本默认从帮助内容自动派生目标并支持 bearer token 登录态，资产检查脚本同步校验前端/Markdown 截图引用、public/docs 双份截图一致性、过期状态和孤儿截图。
- 研发执行器策略列表新增“命中提示”，新增/编辑弹窗新增“命中预览”，可提前看到通用策略、产品专用策略、优先级和同级冲突对最终命中的影响。
- 研发执行器策略新增“代码提交方式”配置：默认保持 AI Task 完成后人工确认，策略设为自动提交时会在 Runner 成功后自动通过 Review 并请求合入隔离 worktree。
- 研发执行器策略新增/编辑入口不再提供“代码巡检整改”任务类型；代码巡检 finding 先进入 Bug，Bug 确认后统一通过“Bug 修复”策略推进 AI Task，历史 `code_inspection_remediation` 仅保留老任务和老策略展示兼容。
- 研发任务命中研发执行器策略下发 Runner 时，会按任务产品/版本注入当前用户可读且已索引的知识中心项目文档片段；Runner `input_payload.knowledge_references` 保留结构化引用，实际执行指令同步追加“产品知识中心上下文”，避免 AI 编码只拿到任务标题而缺少产品文档约束。
- AI 执行器 Runner 包默认启用 Git worktree 隔离：Codex/Claude/Hermes/OpenClaw 在隔离工作区执行，研发任务确认通过后 Runner 才把补丁合入主工作区，拒绝或取消时丢弃隔离结果；确认弹窗同步展示“确认通过/拒绝并丢弃”的操作语义。
- 代码巡检结果动作不再直接创建研发整改任务：默认配置只写代码巡检报告、派生 Bug 和通知；历史 `create_task_for_severe_findings` 动作兼容执行但返回 `deferred_to_bug_confirmation`，需在 Bug 或需求确认后再推进 AI Task。
- 知识中心界面收敛为工作台分区：默认聚焦文档库、空间目录和知识问答，索引健康改为摘要条并将完整治理、导入任务和沉淀审核移入分区页签；列表默认筛选和行操作同步压缩，文档详情改为阅读式页签。
- 系统角色权限模型改为权限点优先、固定角色兼容：需求、任务、AI 助手、知识、代码评审、运营指标等业务入口支持自定义角色通过权限点访问；默认角色、菜单授权和兼容权限目录保持一致。
- 产品数据范围默认策略收紧：非管理员没有显式产品 scope 时返回空范围，只有 `global:*` scope 才视为全局可见；无产品归属的系统定时作业仍可由具备运行权限的用户触发。
- 首页 IT 团队看板优化为管理视图：收敛 13 个平铺指标为交付负载、风险压力、工程活跃和用户声音四个业务域，新增健康结论、治理优先队列和需求/任务/Bug/发布/反馈状态分布图，保留下钻链接和产品/时间筛选。
- DB-first MemoryStore 巡检增强：`audit_memory_store_usage.py` 现在会识别 `setattr(current_store, ...)` 动态写入，并只允许显式白名单中的 PostgreSQL 可重建派生缓存作为 P2。
- 定时作业结果动作 `send_notification` 选择邮件渠道时，正式运行会使用系统设置中的邮件发送配置通过 SMTP 投递到动作收件人，并在运行结果写入记录中展示 `sent` 状态和 Message-ID；代码巡检“发送问题消息通知”同步使用系统发件箱发送邮件。
- 全链路回归脚本在执行前校验真实登录凭据，缺少 `FULL_CHAIN_USERNAME/FULL_CHAIN_PASSWORD` 或 `READINESS_USERNAME/READINESS_PASSWORD` 时会给出清晰失败原因并继续写出 JSON 失败报告。
- 加固运行时安全默认值：`.env.example` 不再默认启用 readiness 种子账号，非本地/非测试环境启动时会拒绝占位或过短 `APP_SECRET_KEY`，并拒绝 `ALLOW_SEEDED_USERS=true`。
- 生产就绪门禁不再接受 `admin@example.com` / `admin123` 内置种子账号凭据，推荐使用 `READINESS_BEARER_TOKEN` 或真实管理员账号。
- 拆分 Bug、产品、需求和任务中心页面的纯 helper 逻辑，页面容器重新回到架构行数预算内。

### Fixed
- 修复运维部署审查发现的边界问题：部署类 Runner 任务按部署单产品 scope 隔离，PostgreSQL 运营列表保留部署方式和执行通道，默认方案切换递增旧方案版本且禁止无替代方案直接停用，Jenkins Queue/Build URL 增加同源校验，版本驾驶舱部署单深链按部署 ID 精确定位。
- 修复“每周AI客服洞察抽取”等 AI 定时作业在数据连接返回大量 rows 时把完整原始数据直接发送给模型网关导致 180 秒超时的问题；AI 处理前会采样压缩模型输入，运行详情保留压缩摘要和模型失败诊断字段。
- 修复钉钉文档 MCP 连接测试使用旧 `/mserver/doc` 默认 Endpoint 导致 404 的问题；新增/编辑连接改为支持直接粘贴钉钉 AI Hub 复制的实例级 `StreamableHttp URL`，服务端自动提取 `key` 并清理旧 query。
- 删除知识文档时同步清理关联 `knowledge_assets` 记录，并通过对象存储适配器尽力删除 MinIO/S3 或本地对象文件；接口返回 `object_cleanup` 说明删除数量和外部对象清理错误。
- 修复钉钉官方 MCP 新增连接弹窗中 URL Key 认证字段排版拥挤的问题，“查询参数名”和“URL Key / 密钥引用”改为响应式网格展示，避免 label、必填标记和说明错位。
- 修复知识中心沉淀审核“全链路”会跳转离开当前工作台的问题，改为页内弹窗展示并保留当前操作上下文。
- 修复定时作业错过执行时间后“下次运行”仍停留在过去时间的问题：Cron/Interval 作业会在列表读取和运行完成后推进到下一次未来时间。
- 修复 Bug 管理列表操作列宽度不足导致“AI处理”“删除”等行操作显示不全。
- 研发任务列表、详情和筛选中的任务类型补齐中文名称，代码巡检整改和 Bug 修复任务不再直接显示 `code_inspection_remediation`、`bug_fix` 编码。
- 代码巡检严重 finding 在确认后推进出的研发整改任务标题现在包含文件路径和行号，任务详情同步展示 Finding、规则、严重级别、描述和修复建议，避免大量 `[Code Inspection Remediation]` 任务无法区分具体代码位置。
- 研发任务详情输出摘要改为优先展示可读 `output_summary`：Runner 仅回写 `output_preview` 时会提取 Codex 最终报告段，避免把完整执行 JSON 和长 diff 直接铺到摘要区。
- 修复账号密码登录数字校验答错后直接展示英文错误码：页面改为中文提示并自动刷新题目、清空旧答案，后端 challenge 错误 message 同步本地化。
- 修复需求全链路详情从暂无需求的迭代版本或版本分支进入时返回 `NO_REQUIREMENT_CONTEXT`：接口改为返回版本级 `empty` 空链路，前端展示“当前版本暂无需求”并保留版本、审计、分支等可用线索。
- 修复用户管理角色编辑与 RBAC 授权表不同步：`/api/users` 创建和编辑角色会同步写入 `user_roles` 授权事实源，并支持分配系统角色管理中新增的可分配自定义角色。
- 增加最后管理员保护：停用、删除或降权用户，以及调整角色状态/权限时，会阻止系统失去最后一个 active `admin` 用户或授权管理入口。
- 清理默认角色边界漂移：viewer 不再继承历史治理类权限，reviewer 不再拥有全局审计读取和审计菜单；新增迁移 `090_role_boundary_cleanup.sql` 用于升级已有数据库。
- 修复后端服务导入链中的插件模板与 AI 执行器循环依赖，避免测试和启动阶段出现 partially initialized module。
- 修复前端 lint 中 Fast Refresh 和 hooks 依赖警告，Runner 超时扫描结果组件拆出独立文件，定时作业 dry-run 逻辑使用稳定 callback。
- 钉钉账号绑定摘要新增企业名称 `corp_name`，个人中心“钉钉账号”卡片优先展示企业名称，并支持 `DINGTALK_CORP_NAME_MAP` 在钉钉未返回名称时按 CorpId 配置展示名。
- 钉钉登录集成补齐账号治理：自动开户用户标记为 SSO-only，本地密码未配置时禁止账号密码登录和自助解绑；用户可在已登录状态首次设置本地密码后再解绑钉钉。
- 钉钉重新绑定改为真实更换当前用户 active 外部身份，绑定冲突、企业白名单、登录失败和解绑锁定风险均返回更清晰的错误码与前端中文提示。
- 系统管理用户列表新增登录方式、钉钉绑定企业和本地密码状态展示，并新增 `/api/system/external-identities` 管理员外部身份查询/解绑接口，支持带审计的强制解绑救援。
- 个人中心账号资料卡片新增只读“登录名”字段，避免仅在页面标题下方展示账号导致用户难以识别当前登录账号。
- 钉钉账号自助绑定失败时，前端会将 `EXTERNAL_IDENTITY_CONFLICT` 等 OAuth 绑定错误码翻译为可理解的中文提示，明确是否为账号已绑定、会话过期或用户取消授权等场景。
- 钉钉未绑定身份自动开户不再直接签发登录态；首次登录只创建待审批 viewer 用户并返回 `DINGTALK_ACCOUNT_PENDING_APPROVAL`，管理员激活后才允许登录。
- 产品配置 Git 资源编辑时，手工修改 Project Path 现在会持久化并回显；只修改 Remote URL 且未手工覆盖 Project Path 时，后端会重新推导仓库路径。
- 定时作业手动触发返回 `queued/running` 运行记录后，前端会立即切到“运行记录”并置顶展示新 run，不再等待全量列表刷新完成。
- 代码巡检报告列表现在由后端标记是否可进入需求全链路；未关联需求上下文的独立巡检报告会禁用“全链路”入口，不再跳转后出现 `NO_REQUIREMENT_CONTEXT` 接口异常。
- 代码巡检页新增产品范围选择和产品列，列表与治理概览会按 `product_id` 联动刷新，并收敛工具栏/表格排版，避免全局视图下页面挤压错位。
- 代码巡检治理概览的分支/提交人待办表格改为固定布局和聚合指标列，长报告摘要在表格内省略和横向滚动，避免表头竖排和内容撑宽。
- 代码巡检治理概览重排为治理结论、核心 KPI 与“治理待办 / 风险分布 / 趋势与规则”分组页签，减少默认视图信息堆叠并改善移动端阅读密度。
- 代码巡检治理概览 review 后进一步压缩移动端 KPI 为双列，并移除页签外层卡片化容器，降低嵌套感和纵向堆叠。
- 代码巡检页进一步压缩治理结论区，将产品范围与刷新合并为顶部操作带，治理压力改为高亮指标网格，风险分布改为 Top 风险列表，并在移动端吸顶治理页签。
- 修复通过局域网 IP 访问本机开发前端时登录失败：前端会按当前访问主机选择局域网 API 地址，本地/开发后端 CORS 默认允许私网前端源预检请求。
- 修复 viewer 角色菜单与接口权限不一致：不再展示空的“任务中心”父菜单和研发任务写操作入口，历史 RBAC 迁移会移除 viewer 的 `task.read` 与任务菜单授权。
- 修复 viewer 角色误显示 AI 助手草案入口：历史 RBAC 迁移会移除 viewer 的 `assistant.chat` 与 `assistant.chat`/`assistant.drafts` 菜单授权，避免点击草案任务台后返回角色拒绝。
- viewer 角色新增产品管理只读入口：默认授予 `product.read` 与 `product.products` 菜单，仅展示产品、版本、模块、Git 资源和相关系统列表，前端隐藏新增、编辑和删除操作。
- 修复 viewer 在 Bug 管理页面仍显示写操作：viewer 只展示 Bug 列表与全链路入口，隐藏登记、编辑、删除、批量处理和行选择，后端补充 viewer 写接口拒绝测试。
- 修复系统设置测试收件人不生效：`test_recipient_email` 现在作为系统设置字段持久化保存，页面不再把系统管理员邮箱自动写入测试收件人，测试发送未显式指定收件人时优先使用已保存测试收件人，再回退系统管理员邮箱，且不再从发件邮箱推导。
- 修复系统设置测试邮件失败排障不稳定：SMTP 网络、SSL 握手、连接重置或超时错误统一返回 `EMAIL_DELIVERY_TEST_FAILED`，避免页面表现为后端 500 或连接异常。
- 优化系统设置测试邮件链路：页面点击“发送测试邮件”会先保存当前表单配置，避免刚输入的 SMTP 安全密码未生效；测试邮件增加唯一主题、Message-ID 和发送时间，SMTP 拒收收件人时不再误报成功。
- 简化系统设置邮件配置页：移除容易误填的“SMTP 密钥引用”输入项，页面仅维护 SMTP 密码/授权码；`smtp_secret_ref` 保留为 API 级高级配置，不再由页面展示或提交。
- 修复公网域名登录误拦截：默认种子密码仍保持禁用，但历史种子用户名已改成真实非默认密码时，可按普通数据库用户登录，不再因用户名命中种子列表直接返回 `DEFAULT_CREDENTIALS_DISABLED`。

## 历史归档

- [拆分前完整 changelog（截至 2026-07-03）](releases/changelog-2026-07-03-pre-split.md)
- API 文档版本历史：[02-specs/enterprise-ai-brain/api/version-history.md](02-specs/enterprise-ai-brain/api/version-history.md)
- 技术规格版本历史：[02-specs/enterprise-ai-brain/history/spec-version-history.md](02-specs/enterprise-ai-brain/history/spec-version-history.md)
- 测试用例版本历史：[02-specs/enterprise-ai-brain/history/test-case-version-history.md](02-specs/enterprise-ai-brain/history/test-case-version-history.md)
