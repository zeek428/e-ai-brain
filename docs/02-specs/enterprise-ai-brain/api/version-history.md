# API 文档版本历史

> 从 [../api.md](../api.md) 拆出。主 API 文档只保留分册索引；历史版本记录在此归档。

## 版本历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.1.561 | 2026-07-09 | 系统健康告警通知 outbox 新增投递接口，支持站内、SMTP 邮件、Webhook/钉钉 URL 投递和失败重试，回写 attempts、last_error、sent_at 与脱敏投递摘要 | Codex |
| v1.1.560 | 2026-07-09 | 钉钉官方 MCP 新增/编辑连接改为实例级 `StreamableHttp URL`，服务端保存时自动提取 URL Key 并清理旧网关 query | Codex |
| v1.1.559 | 2026-07-09 | 系统健康告警订阅新增通知 outbox，`GET /api/system/health` 返回最近通知记录和待投递数量，订阅 scope 支持按 source/component/owner 匹配 | Codex |
| v1.1.558 | 2026-07-09 | 审计与运行页面接入 `GET /api/audit/events/export`，按当前筛选和排序导出最近 1000 条脱敏 CSV 摘要记录 | Codex |
| v1.1.557 | 2026-07-09 | `PATCH /api/system/settings` 对邮件发送敏感配置变更要求 `high_risk_confirmation`，缺少确认返回 `SENSITIVE_CONFIG_CONFIRMATION_REQUIRED` | Codex |
| v1.1.556 | 2026-07-09 | 系统健康 `ai_executor_ops` 返回最近活跃任务、操作目标计数和失败任务摘要，支撑健康页直接超时扫描、取消和重试 Runner 任务 | Codex |
| v1.1.555 | 2026-07-09 | 权限诊断新增用户菜单视角预览 `GET /api/system/permissions/menu-preview`，角色保存前风险预检新增 `POST /api/system/roles/{role_id}/risk-precheck` 并阻断菜单权限缺口 | Codex |
| v1.1.554 | 2026-07-09 | 产品接入完整度评分纳入真实健康信号，返回插件失败数、权限范围状态、可检索文档数和 recent_health_check 摘要 | Codex |
| v1.1.553 | 2026-07-09 | 系统健康新增告警规则 CRUD 和管理员周报生成接口，告警中心返回规则摘要和命中规则元数据 | Codex |
| v1.1.552 | 2026-07-09 | 系统健康新增告警 incident/订阅处理接口、安全审计治理快照，知识中心新增质量事件、反馈和引用点击接口，审计事件新增 CSV 导出 | Codex |
| v1.1.551 | 2026-07-08 | 研发执行器策略页面新增命中提示和新增/编辑命中预览，按产品专属优先、priority 升序和策略 ID 兜底展示冲突风险 | Codex |
| v1.1.550 | 2026-07-08 | 研发执行器策略新增 `code_change_review_mode`：默认人工确认，配置 `auto_commit` 时 Runner 成功后自动通过 Review 并请求 merge 隔离 worktree | Codex |
| v1.1.549 | 2026-07-08 | 研发执行器策略新增入口移除历史 `code_inspection_remediation` 选项，代码巡检 finding 经 Bug 确认后统一按 `bug_fix` 推进 AI Task | Codex |
| v1.1.548 | 2026-07-08 | 研发任务命中研发执行器策略下发 Runner 时新增 `input_payload.knowledge_references[]`，并把同产品/同版本可读知识中心片段追加到执行器 instruction | Codex |
| v1.1.547 | 2026-07-05 | 定时作业 `send_notification` 邮件渠道正式运行接入系统邮件发送配置，使用系统发件箱向动作收件人投递并在邮件通知记录中返回投递状态和 Message-ID | Codex |
| v1.1.546 | 2026-07-04 | 插件管理 API 新增钉钉授权向导/治理/观测/业务模板市场字段、`discover-tools` 动态能力发现接口和 `plugin-observability` 健康看板接口 | Codex |
| v1.1.545 | 2026-07-04 | 插件管理 API 新增钉钉官方 MCP P0 标准插件，支持 `mcp_streamable_http`、`url_key` 鉴权、P0 动作模板风险分层和 URL Key 脱敏 | Codex |
| v1.1.544 | 2026-07-03 | `PATCH /api/product-git-repositories/{repo_id}` 支持编辑 Project Path 显式覆盖；仅修改 Remote URL 且未提交 Project Path 时重新推导仓库路径 | Codex |
| v1.1.543 | 2026-07-03 | `GET /api/system/scheduled-job-runs` 响应项补充 `scheduled_job_name`，运行记录列表优先展示作业名称而非作业 ID | Codex |
| v1.1.542 | 2026-07-03 | `GET/PATCH /api/system/settings` 扩展 `email_delivery` 发信配置并新增 `POST /api/system/settings/email/test`，SMTP 密码仅写入不回显，审计只记录配置状态 | Codex |
| v1.1.541 | 2026-07-03 | GitLab 官方连接改为 Endpoint + Token 凭据连接，GitLab 地址仅作为可选默认项目参数，未填写时不落空 `project_id/project_path` | Codex |
| v1.1.540 | 2026-07-03 | GitHub 官方连接改为 Token 必填、仓库地址可选；未填写仓库地址时不落空 `owner/repo`，代码巡检继续使用产品代码库 Remote URL | Codex |
| v1.1.539 | 2026-07-03 | 本地完整代码巡检可保存可选 GitHub/GitLab 凭据连接，并在 clone/fetch 时优先使用任务绑定连接 token，代码 URL 继续来自产品代码库 | Codex |
| v1.1.538 | 2026-07-03 | 新增 `GET/PATCH /api/system/settings`，系统管理统一维护系统管理员邮箱，写入 `system_settings` 并记录 `system.settings.updated` 审计 | Codex |
| v1.1.537 | 2026-07-03 | 代码巡检作业请求可省略仓库 ID 以按产品扫描全部 active 代码仓库，运行摘要返回按仓库扫描、AI 处理、写入和 Worker 重试明细 | Codex |
| v1.1.536 | 2026-07-03 | 产品 Git 资源配置默认使用 `remote_url`，后端从可解析 Remote URL 推导 `project_path`，Project Path 不再作为前端必填项 | Codex |
| v1.1.535 | 2026-07-03 | `DELETE /api/requirements/{requirement_id}` 在需求已有 AI 任务时返回 `related_counts.ai_tasks/related_total`，前端需展示中文占用处理提示 | Codex |
| v1.1.534 | 2026-07-03 | 新增 `GET /api/bugs/images/preview`，已上传 Bug 图片通过受 `bug.read` 权限保护的后端代理预览 | Codex |
| v1.1.533 | 2026-07-03 | 新增 `POST /api/bugs/images/upload`，Bug 图片证据写入 MinIO/S3-compatible 对象存储后以元数据关联到 evidence | Codex |
| v1.1.532 | 2026-07-02 | 定时作业 `config_json.ai_executor` 支持选择系统默认执行器或本地 Runner；本地 Runner 可不传模型网关，完成回写后继续结果动作 | Codex |
| v1.1.531 | 2026-07-02 | 样例复用 `reuse_wizard` 新增进度字段，连接测试、动作试运行和 dry-run 页面展示“已就绪步骤 / 总步骤” | Codex |
| v1.1.530 | 2026-07-02 | AI 执行器 Runner `readiness_summary` 新增 `sandbox_permission_boundary` 控制项和安装包心跳安全元数据 | Codex |
| v1.1.529 | 2026-07-02 | 新增 `POST /api/system/plugin-actions/{action_id}/ai-executor-approval`，将高风险审批快照写回动作配置 | Codex |
| v1.1.528 | 2026-07-02 | 动作试运行失败态 `scheduled_job_dry_run_seed` 只能作为排障向导，前端需按 `reuse_wizard` 禁止生成作业草稿 | Codex |
| v1.1.527 | 2026-07-02 | AI 执行器 Runner 高风险阻断响应新增 `approval_request`，并记录 `ai_executor_task.approval_requested` 审计事件 | Codex |
| v1.1.526 | 2026-07-02 | `plugin_action_invoke` 在 AI 执行模式下正式运行会调用 Skill/模型，并以 AI 输出执行通用结果动作 | Codex |
| v1.1.525 | 2026-07-02 | AI 执行器任务 `timeout-scan` 响应新增扫描摘要和下一步动作，便于页面与调度排障展示 | Codex |
| v1.1.524 | 2026-07-02 | 定时作业 dry-run 识别 `config_json.sample_reuse.response_summary` 样例模式，复用动作试运行响应并跳过第三方数据连接调用 | Codex |
| v1.1.523 | 2026-07-02 | Trace DAG AI 处理节点级复跑 POST 支持复用来源数据连接响应快照重新调用模型，并跳过下游动作写入 | Codex |
| v1.1.522 | 2026-07-02 | Trace DAG 通用结果动作节点级复跑 POST 支持复用来源 AI 输出快照生成独立 `manual_rerun` 结果写入记录 | Codex |
| v1.1.521 | 2026-07-02 | Trace DAG 数据连接节点级复跑 POST 在预检 ready 时创建独立 `manual_rerun` 运行记录，仅重新执行数据连接并跳过下游 AI/动作 | Codex |
| v1.1.520 | 2026-07-02 | AI 执行器 Runner 高风险指令支持 `ai_executor_approval` 审批快照契约，未审批阻断、已审批入队并审计 | Codex |
| v1.1.519 | 2026-07-02 | Agent/Skill 文件包允许 `scripts/` 脚本资产落盘并返回运行边界，非 scripts 目录可执行脚本继续拒绝 | Codex |
| v1.1.518 | 2026-07-02 | AI角色新增 `POST /api/system/ai-agents/upload` Agent 文件包上传契约，响应补充文件包来源和运行边界 | Codex |
| v1.1.517 | 2026-07-02 | Trace DAG 节点复跑预检新增 `execution_policy/next_actions`，返回保护态说明、推荐整条复跑和待补齐控制项 | Codex |
| v1.1.516 | 2026-07-02 | AI 执行器 Runner 列表响应新增 `readiness_summary`，返回运行就绪控制项、状态摘要和阻断/关注计数 | Codex |
| v1.1.515 | 2026-07-02 | Trace DAG 节点复跑预检补齐结构化 `rerun_controls/control_summary`，`missing_controls` 仅返回未满足控制项 | Codex |
| v1.1.514 | 2026-07-02 | AI 执行器 Runner 列表响应新增 `queue_summary`，返回任务状态计数、可用槽位和最近失败摘要 | Codex |
| v1.1.513 | 2026-07-02 | Trace DAG 节点级复跑新增只读预检接口，返回快照预览、缺失控制项、阻断原因和整条复跑回退请求 | Codex |
| v1.1.512 | 2026-07-02 | 连接测试、动作试运行和定时作业 dry-run 的样例复用响应统一返回 `reuse_wizard`，明确当前步骤、下一步动作、缺失项和向导步骤状态 | Codex |
| v1.1.511 | 2026-07-02 | 定时作业 Trace DAG 新增节点级复跑受保护 API，返回快照状态、阻断原因、审计事件和整条运行复跑替代请求 | Codex |
| v1.1.510 | 2026-07-02 | AI 执行器 Runner 代理改为执行过程中流式追加 stdout/stderr 日志，并在安装包配置中声明无 shell 执行与 stdin 指令传递策略 | Codex |
| v1.1.509 | 2026-07-02 | AI 执行器 Runner 安装包内置 `runner_agent.py` 轮询代理，任务完成回写保留已追加日志 | Codex |
| v1.1.508 | 2026-07-02 | AI 执行器 Runner 工作区白名单在派发和认领阶段双重校验，支持白名单目录子路径并对越界任务返回 `AI_EXECUTOR_WORKSPACE_NOT_ALLOWED` | Codex |
| v1.1.507 | 2026-07-02 | 动作试运行支持 `sample_response_summary` 样例预览模式，连接测试 JSON 响应可直接进入动作写入预览 | Codex |
| v1.1.506 | 2026-07-02 | 插件连接测试返回 `scheduled_job_sample_seed`，将连接测试样例纳入“连接样例 -> 动作试运行 -> 定时作业 dry-run”复用链路 | Codex |
| v1.1.505 | 2026-07-02 | Trace DAG 节点补齐 `rerun_plan/snapshot_status` 受保护复跑计划；动作试运行返回 `scheduled_job_dry_run_seed` 并可生成定时作业草稿；AI Skill 响应返回运行边界 | Codex |
| v1.1.504 | 2026-07-02 | 定时作业运行 `result_summary.trace_graph.nodes[]` 补齐 `stage/stage_label/debug_actions/rerun_supported/rerun_hint`，用于运行详情节点复制、阶段识别和复跑边界提示 | Codex |
| v1.1.503 | 2026-07-02 | 定时作业 catalog 返回 `generic_result_actions[]`，通用 AI 分析作业支持结果保存/通知动作写入预览，并收紧多连接同插件校验 | Codex |
| v1.1.502 | 2026-07-02 | 插件执行调用类定时作业成功响应摘要返回 `job_type` 与“插件执行调用完成”，不再暴露旧占位文案 | Codex |
| v1.1.501 | 2026-07-02 | 定时作业 `SKILL_OUTPUT_SCHEMA_INVALID` 失败摘要补齐 `model_log_id`，用于区分模型未调用和模型输出契约失败 | Codex |
| v1.1.500 | 2026-07-02 | 定时作业运行时模型输出不符合 Skill 输出 Schema 类型或必填字段时返回 `SKILL_OUTPUT_SCHEMA_INVALID`，动作节点不执行 | Codex |
| v1.1.499 | 2026-07-02 | 定时作业 dry-run 的 `output_preview` 对未声明 item schema 的常见业务数组返回结构化样例记录，便于动作写入预览展示样例 | Codex |
| v1.1.498 | 2026-07-02 | 定时作业 dry-run AI 场景返回 `output_preview/source`，动作写入预览改用 Skill 输出 Schema 样例并标记 `write_preview_source` | Codex |
| v1.1.497 | 2026-07-02 | 定时作业运行 API、AI 助手诊断和运行健康补齐多节点诊断口径：连接失败时 AI 节点明确未开始，多连接/多动作摘要和动作写入统计按明细聚合 | Codex |
| v1.1.496 | 2026-07-02 | 定时作业多数据连接运行按 `data_connections.failure_policy` 落地：`continue_on_error` 保留失败连接节点并继续后续连接，`fail_fast` 失败运行仍返回数据连接和 Trace 排障明细 | Codex |
| v1.1.495 | 2026-07-02 | 用户反馈洞察定时作业多结果动作按 `result_actions.failure_policy` 执行，默认 `continue_on_error` 时失败动作进入运行节点、Trace DAG 和结果写入记录，后续动作继续执行 | Codex |
| v1.1.494 | 2026-07-02 | 定时作业运行 `result_summary.trace_graph` 展开多数据连接和多结果动作节点，节点输入输出携带连接、动作和写入反馈摘要 | Codex |
| v1.1.493 | 2026-07-02 | 定时作业 dry-run `stages.ai_processing` 增加 `mapping_contract`，Skill 输出 Schema 契约校验支持与动作映射一致的 JSONPath 子集 | Codex |
| v1.1.492 | 2026-07-02 | 动作 `result_mapping` JSONPath 子集支持 `$` 根、点路径、bracket key、数组下标和 `[*]` 通配，动作试运行、dry-run 与运行结果写入预览统一解析 | Codex |
| v1.1.491 | 2026-07-01 | 定时作业 Catalog `job_types[]` 新增 `allow_create/runnable/unavailable_reason`，创建/试运行和手动运行分别返回 `SCHEDULED_JOB_TYPE_UNAVAILABLE` 与 `SCHEDULED_JOB_TYPE_NOT_RUNNABLE` 拦截已登记但未闭环类型 | Codex |
| v1.1.490 | 2026-07-01 | 结果写入记录 API 从定时作业 `execution_nodes.result_actions[]` 逐条派生记录，旧 `result_action` 作为兼容回退 | Codex |
| v1.1.489 | 2026-07-01 | 内部数据源 API 契约移除用户可选 `product_scope`，读取按业务源权限和当前用户产品范围过滤并返回 `access_issues/schemas.access_status`；定时作业配置页不再消费连接环境筛选 | Codex |
| v1.1.488 | 2026-07-01 | AI 助手定时作业草案确认前统一归一化插件连接、动作和 Skill 引用数组，空值跳过且重复 ID 保留首次出现 | Codex |
| v1.1.487 | 2026-07-01 | 内部数据源 `source_types` 服务端保序去重，连接测试、请求预览和动作读取响应使用去重后的源列表 | Codex |
| v1.1.486 | 2026-07-01 | 内部数据源连接测试与动作读取按 `source_types` 裁剪残留 `source_filters`，响应过滤摘要只返回实际生效源条件 | Codex |
| v1.1.485 | 2026-07-01 | 内部数据源连接 schema 字段新增 `visible_when_source_types`，前端按源数据选择联动展示按源过滤字段并跳过隐藏字段提交 | Codex |
| v1.1.484 | 2026-07-01 | 内部数据源连接 `source_types` 选项和默认值统一由服务端源数据注册表生成，插件市场 schema 与读取默认值保持同源 | Codex |
| v1.1.483 | 2026-07-01 | AI 助手动作入口 `create_plugin_action` 用户侧统一返回“新建动作/新增动作”，`插件动作` 仅作为兼容别名继续识别 | Codex |
| v1.1.482 | 2026-07-01 | 内部数据源连接 schema 明确返回按源过滤可视化字段，常用需求和 Bug 过滤直接写入 `request_config.query.source_filters` | Codex |
| v1.1.481 | 2026-07-01 | 内部数据源 detail 受保护字段明确要求 `system.internal_data_source.detail` 权限，可通过角色管理授权 | Codex |
| v1.1.480 | 2026-07-01 | 内部数据源 API 补充注册表字段白名单、按源 `source_filters` 和响应 `schemas` 契约 | Codex |
| v1.1.479 | 2026-07-01 | `POST /api/assistant/chat` 对定时作业运行转业务草案意图返回 `scheduled_job_run_business_draft` 工具结果并持久化 `create_analysis_draft` 草案 | Codex |
| v1.1.478 | 2026-07-01 | 定时作业运行详情“转业务草案”菜单复用助手深链，支持用户洞察、需求和 Bug 草案，不新增后端接口 | Codex |
| v1.1.477 | 2026-07-01 | 定时作业运行详情新增“转洞察草案”前端深链契约，复用 `/assistant?reference_type=scheduled_job_run&reference_id=...&prompt=...`，不新增后端接口 | Codex |
| v1.1.476 | 2026-07-01 | 定时作业运行详情页面新增“导出 JSON”前端契约，基于现有运行记录和结果写入记录响应导出运行记录、执行节点、展示标签和快照，不新增后端接口 | Codex |
| v1.1.475 | 2026-07-01 | 插件管理 API 新增官方内部数据源插件契约：`protocol=internal_read_model`、`action_type=internal_query`，连接 schema 支持多选内部源数据，连接测试返回 `INTERNAL_READ` 预览与各源行数 | Codex |
| v1.1.474 | 2026-07-01 | `GET /api/insights/items` 新增 `product_id` 查询参数，用户洞察聚合列表可按所属产品在 SQL read model 层过滤 | Codex |
| v1.1.473 | 2026-06-30 | `GET /api/system/result-write-records` 带分页时改为 PostgreSQL 派生 read model 聚合定时作业运行和独立插件调用日志，产品 scope、筛选、排序和 count/page 下推 | Codex |
| v1.1.472 | 2026-06-30 | `GET /api/product-versions/{version_id}/dashboard` 新增 `evidence_coverage`，统一返回版本证据覆盖评分、证据域状态和阻断/缺口摘要 | Codex |
| v1.1.471 | 2026-06-30 | `GET /api/insights/user-feedback` 补齐分页查询契约：带 `page/page_size` 时优先走用户反馈 count/page read model，支持 `summary_only` 摘要模式和 `query/performance` 观测 | Codex |
| v1.1.470 | 2026-06-30 | `GET /api/assistant/action-drafts` 和草案详情响应新增统一确认决策字段：列表返回 `decision_*` 与 `can_confirm`，详情返回 `governance.decision` | Codex |
| v1.1.469 | 2026-06-30 | `GET /api/product-versions/{version_id}/dashboard` 新增 `delivery_stage_overview`，后端统一输出交付阶段总览供版本总览、AI 助手和回归脚本复用 | Codex |
| v1.1.468 | 2026-06-30 | `GET /api/product-versions/{version_id}/dashboard` 新增 `governance_conclusion`，后端统一输出版本治理结论供版本总览、AI 助手和回归脚本复用 | Codex |
| v1.1.467 | 2026-06-30 | 知识中心索引健康前端展示升级为解析状态、Chunk/Embedding、检索与权限三段治理摘要，健康问题操作明确区分补向量、重试索引、查看分块和导入任务 | Codex |
| v1.1.466 | 2026-06-30 | `POST /api/assistant/chat` 对迭代版本阻塞/下一步行动问题使用确定性 `assistant.iteration` 工具结果，复用版本总览治理上下文并在历史消息保留安全摘要 | Codex |
| v1.1.465 | 2026-06-30 | `GET /api/product-versions/{version_id}/dashboard` 新增后端 `next_actions`，按阻塞优先级返回前三个版本治理建议及全链路主体，供版本总览、AI 助手和回归脚本复用 | Codex |
| v1.1.464 | 2026-06-30 | `GET /api/system/roles/{role_id}` 新增 `access_preview`，返回单角色可见菜单、操作权限、范围分组和菜单权限缺口/高风险诊断 | Codex |
| v1.1.463 | 2026-06-30 | 迭代版本总览交付链路总览需基于 dashboard 既有响应为各阶段生成直接处理入口，无需新增接口字段 | Codex |
| v1.1.462 | 2026-06-30 | 代码巡检治理概览前端需基于 dashboard 既有响应派生“代码巡检治理结论”，首屏说明治理优先级、主要风险和下一步动作 | Codex |
| v1.1.461 | 2026-06-30 | 迭代版本总览前端需基于 dashboard 既有响应派生“版本治理结论”，首屏说明版本是否可推进、主要风险和下一步动作 | Codex |
| v1.1.460 | 2026-06-30 | 迭代版本总览前端摘要需消费 `branch_quality_governance` 与 summary 分支质量治理计数，首屏展示待治理分支、门禁失败、待审批忽略和到期风险 | Codex |
| v1.1.459 | 2026-06-30 | 知识索引健康前端必须展示 `status_counts` 文档状态分布与 Chunk/Embedding 覆盖率，避免只看摘要数量无法判断解析进度 | Codex |
| v1.1.458 | 2026-06-30 | `GET /api/product-versions/{version_id}/dashboard` 的 `branch_quality_governance` 补齐 finding 级 suppression 治理计数，summary 返回活跃严重、误报忽略、接受风险、过期接受风险和待审批忽略统计 | Codex |
| v1.1.457 | 2026-06-30 | `GET /api/product-versions/{version_id}/dashboard` 新增 `branch_quality_governance` 和 summary 分支治理计数，版本总览可直接查看分支巡检、门禁、Bug/整改覆盖和最近报告 | Codex |
| v1.1.456 | 2026-06-30 | `GET /api/product-versions/{version_id}/dashboard` 在 PostgreSQL 运行时改为版本范围专用 read model，响应字段不变，避免先加载全量 task workflow source rows 后服务层过滤 | Codex |
| v1.1.455 | 2026-06-30 | 代码巡检治理概览新增 `governance_pressure`，聚合待闭环提交人、缺 Bug、缺整改任务、门禁失败、待审批忽略和到期接受风险，供页面顶部治理压力总览展示 | Codex |
| v1.1.454 | 2026-06-30 | 新增 `POST /api/system/ai-executor-tasks/{task_id}/retry`，管理员可重试 `cancelled/failed/timed_out/dead_letter` 的 AI 执行器任务并保留来源、原因和审计链路 | Codex |
| v1.1.453 | 2026-06-29 | 迭代版本驾驶舱知识沉淀明细补齐知识文档索引健康元数据，summary 返回可检索和向量就绪沉淀数 | Codex |
| v1.1.452 | 2026-06-29 | 迭代版本驾驶舱聚合版本内任务知识沉淀，summary 返回 `knowledge_deposits`，明细按 `knowledge.read` 子权限降级隐藏 | Codex |
| v1.1.451 | 2026-06-29 | GitLab MR 预览支持显式 `fixture://gitlab` 回归源，仅用于真实全链路脚本的本地可控 Code Review 门禁，不替代生产 GitLab/GitHub 只读 API 配置 | Codex |
| v1.1.450 | 2026-06-29 | 代码巡检 suppression 申请支持 `accepted_risk` 责任人和到期时间，缺少 `expires_at` 返回 `ACCEPTED_RISK_EXPIRY_REQUIRED`，详情和 dashboard 返回过期接受风险计数 | Codex |
| v1.1.449 | 2026-06-29 | 迭代版本驾驶舱 blockers 返回 `action_label/action_target_type/action_target_id/resolution_hint`，前端阻塞项表展示解除条件和处理入口 | Codex |
| v1.1.448 | 2026-06-29 | 代码巡检报告和详情响应明确返回增量扫描快照字段 `incremental_from_commit`、`incremental_file_count` 与 `is_full_scan`，前端详情需展示扫描范围和增量基线 | Codex |
| v1.1.447 | 2026-06-29 | 明确真实全链路回归脚本需在知识沉淀采纳后调用 `GET /api/knowledge/index-health` 和 `POST /api/knowledge/search`，验证索引健康与检索可用性 | Codex |
| v1.1.446 | 2026-06-29 | 新增 `GET /api/knowledge/index-health`，按当前用户 `knowledge.read` 权限、知识空间 scope 和筛选条件聚合全量索引健康、chunk/embedding 覆盖、导入任务状态和可操作健康问题，响应包含 `query/performance` | Codex |
| v1.1.445 | 2026-06-28 | AI 执行器任务超时扫描新增租约重派和死信队列响应：任务状态支持 `dead_letter`，`POST /api/system/ai-executor-tasks/timeout-scan` 返回 `requeued_task_ids/dead_letter_task_ids/timed_out_task_ids`，认领和日志追加会维护 `request_config.reliability` 租约元数据 | Codex |
| v1.1.444 | 2026-06-28 | 角色管理页面新增权限与范围预览，复用 `GET /api/system/permissions/matrix` 响应中的 `rows/scopes/high_risk_permission_codes/missing_menu_permission_codes` 展示范围覆盖和授权风险；API 契约无需新增端点 | Codex |
| v1.1.443 | 2026-06-28 | 知识中心页面新增索引健康视图：最初复用 `GET /api/knowledge/documents` 分页响应中的 `index_status`、`active_chunk_set_id`、`index_error` 和 `vector_index_error` 展示当前页健康汇总；v1.1.446 已升级为独立后端健康端点 | Codex |
| v1.1.442 | 2026-06-28 | `GET /api/governance/code-inspections/{report_id}` 详情响应新增 `governance_summary`，返回闭环状态、严重问题 Bug/整改任务覆盖、待审批忽略、已接受风险和治理待办；前端报告详情展示治理闭环与整改任务链接 | Codex |
| v1.1.441 | 2026-06-28 | AI 动作草案详情响应新增 `governance` 治理摘要，草案任务台列表行补充影响对象、权限状态、审计事件数、失败次数和重试次数；详情页需展示风险、影响、权限、执行前后差异、失败重试和审计链路 | Codex |
| v1.1.440 | 2026-06-28 | `POST /api/ai-tasks/{task_id}/start` 支持管理员显式 `execution_mode=deterministic` 验收模式，跳过研发执行器策略和模型网关并记录审计；统一 full-chain 在需求归属版本时可按版本分支配置匹配代码巡检报告；AI 助手引用解析补齐 `product_version` 和仓储上下文中的代码巡检报告 | Codex |
| v1.1.439 | 2026-06-28 | 新增 `GET /api/product-versions/{version_id}/dashboard`，迭代版本页可查看需求、任务、Bug、代码分支、代码巡检、发布记录、状态推进影响和阻塞项聚合；接口要求 `product.read` 并按产品 scope 校验，Bug 和代码巡检明细按对应 read 权限降级隐藏 | Codex |
| v1.1.438 | 2026-06-28 | 新增 `POST /api/assistant/action-drafts/{draft_id}/retry`，失败草案可重新打开为待确认状态，保留失败历史、清空失败 run 绑定并记录 `assistant_action_draft.retry_requested` 审计；重新确认前不写入业务配置 | Codex |
| v1.1.437 | 2026-06-28 | `GET /api/system/ai-executor-runners` 补齐 AI 执行器 Runner 主表远程分页契约：带 `page/page_size` 时支持 `executor_type/keyword/protocol/status` 筛选、白名单排序和 `query/performance` 观测；插件管理执行器页主表默认请求服务端分页结果 | Codex |
| v1.1.436 | 2026-06-28 | `GET /api/system/model-gateway-configs` 分页查询生产路径收口：带 `page/page_size` 时优先调用模型网关配置 count/page read model，筛选和排序下推到 PostgreSQL，避免先全量读取配置后服务层切片 | Codex |
| v1.1.435 | 2026-06-28 | `GET /api/model-gateway/logs` 补齐模型调用日志远程分页契约：带 `page/page_size` 时支持 `ai_task_id/purpose/status` 筛选、白名单排序和 `query/performance` 观测；模型网关页最近调用日志表默认请求服务端分页结果 | Codex |
| v1.1.434 | 2026-06-28 | `GET /api/assistant/role-quick-task-configs` 补齐 AI 助手角色快捷任务配置远程分页契约：带 `page/page_size` 时支持搜索、任务启停状态、分组启停状态、角色、权限、企业、草案模板、模板版本筛选、白名单排序和 `query/performance` 观测；角色快捷任务配置页主表改为请求服务端分页结果 | Codex |
| v1.1.433 | 2026-06-28 | `GET /api/assistant/action-reference-configs` 补齐 AI 助手 @ 能力配置远程分页契约：带 `page/page_size` 时支持搜索、启停状态、角色、权限、企业、模板版本筛选、白名单排序和 `query/performance` 观测；@ 能力配置页主表改为请求服务端分页结果 | Codex |
| v1.1.432 | 2026-06-28 | `GET /api/system/menus` 补齐菜单管理远程分页契约：带 `page/page_size` 时支持菜单、父级、路由、权限点、类型、状态筛选、白名单排序和 `query/performance` 观测；菜单管理页主表改为请求服务端分页结果 | Codex |
| v1.1.431 | 2026-06-28 | `GET /api/reviews/pending` 补齐任务中心待确认 Review 子列表远程分页契约：支持 `ai_task_id/page/page_size/sort_by/sort_order`，返回 `query/performance`，任务确认弹窗可按 AI 任务精准查询 | Codex |
| v1.1.430 | 2026-06-28 | 统一需求全链路入口支持版本代码分支配置主体：`product_version_branch_config` / `branch_config` 可解析回同版本需求链路，迭代版本分支列表和 AI 助手引用按该主体生成 `/delivery/full-chain` 深链 | Codex |
| v1.1.429 | 2026-06-28 | 需求全链路响应补齐执行诊断证据：`execution_traces[]`、`summary.execution_traces` 和 `type=execution_trace` 时间线事件返回脱敏 Trace 摘要，前端阶段明细按 `source_id + source_type` 跳转执行诊断中心 | Codex |
| v1.1.428 | 2026-06-28 | `GET /api/system/result-write-records` 补齐可选分页、排序和查询性能观测，带 `page/page_size` 时返回 `query/performance` 元数据 | Codex |
| v1.1.427 | 2026-06-28 | 结果写入记录排障 API 补齐产品范围：`GET /api/system/result-write-records` 通过 `scheduled_job_id` 或 `scheduled_job_run_id` 解析产品并按当前用户产品 scope 过滤，scope 外记录不返回 | Codex |
| v1.1.426 | 2026-06-28 | 插件调用日志排障 API 补齐产品范围：`GET /api/system/plugin-invocation-logs` 通过定时作业或运行实例解析产品并按当前用户产品 scope 过滤，PostgreSQL 分页 read model 下推 `product_scope_ids` | Codex |
| v1.1.425 | 2026-06-28 | 统一需求全链路入口支持执行诊断主体：`scheduled_job_run`、`plugin_invocation_log`、`ai_executor_task`、`model_gateway_log` 和 `execution_trace` 可通过 Trace 关联 ID、节点 AI 任务、代码巡检报告或审计事件解析回需求链路 | Codex |
| v1.1.424 | 2026-06-28 | 系统管理接口权限点收口：`/api/users` 改为校验 `system.users.manage`，模型网关配置与日志改为校验 `system.model_gateway.manage`，审计事件查询改为校验 `audit.read`，不再把固定 admin 角色作为唯一入口 | Codex |
| v1.1.423 | 2026-06-28 | `GET /api/assistant/action-drafts` 草案任务台 read model 补齐 `validation_status` 数据库侧筛选，分页请求不再因校验状态过滤退回服务层全量草案读取 | Codex |
| v1.1.422 | 2026-06-28 | 产品主体、迭代版本和版本分支配置接口权限与产品范围收口：读接口校验 `product.read` 并按产品 scope 过滤或隐藏，写接口校验 `product.manage`，scope 外返回 404，产品与版本 SQL read model 下推 `product_scope_ids` | Codex |
| v1.1.421 | 2026-06-28 | 产品模块接口权限与产品范围收口：列表校验 `product.read`，创建/更新/删除校验 `product.manage`，嵌套产品和单模块资源均按当前用户产品 scope 校验，scope 外返回 404 | Codex |
| v1.1.420 | 2026-06-28 | 相关系统接口权限与产品范围收口：列表校验 `product.read`，创建/更新/删除校验 `product.manage`，列表按当前用户产品 scope 过滤，指定或变更到 scope 外产品返回 404 | Codex |
| v1.1.419 | 2026-06-28 | 产品 Git 仓库接口权限与产品范围收口：列表校验 `product.read`，创建/更新/删除校验 `product.manage`，嵌套产品和单仓库资源均按当前用户产品 scope 校验，scope 外返回 404 | Codex |
| v1.1.418 | 2026-06-28 | AI 执行器任务管理产品范围收口：`GET /api/system/ai-executor-tasks`、日志查询、取消和超时扫描按当前用户产品 scope 过滤，PostgreSQL 分页 read model 下推 `product_scope_ids` | Codex |
| v1.1.417 | 2026-06-28 | 知识沉淀候选审核接口权限收口：`GET/POST /api/knowledge/deposits...` 统一校验 `knowledge.deposit.decide` 权限点，具备自定义审核权限的角色可访问，单纯 `knowledge.read` 不可审核候选 | Codex |
| v1.1.416 | 2026-06-28 | `GET /api/system/roles` 生产查询路径收口：PostgreSQL 运行时分页请求必须优先调用角色 summary count/page read model，支持现有筛选和排序白名单，不得先全量 `list_roles()` 后本地分页 | Codex |
| v1.1.415 | 2026-06-28 | `GET /api/knowledge/deposits` 补齐远程分页契约：支持 `page/page_size/sort_by/sort_order`，按状态过滤知识沉淀候选，并返回 `query/performance` 观测 | Codex |
| v1.1.414 | 2026-06-28 | `GET /api/system/plugin-invocation-logs` 补齐远程分页契约：支持 `page/page_size/sort_by/sort_order`，按动作、定时作业、运行实例和状态过滤，并返回 `query/performance` 观测 | Codex |
| v1.1.413 | 2026-06-28 | `GET /api/system/ai-executor-tasks` 补齐远程分页契约：支持 `page/page_size/sort_by/sort_order`，按研发 AI 任务、Runner、定时作业运行和任务状态过滤，并返回 `query/performance` 观测 | Codex |
| v1.1.412 | 2026-06-27 | 核心管理列表读权限与产品 scope 收口：`GET /api/requirements`、`GET /api/bugs`、`GET /api/knowledge/documents`、`GET /api/governance/code-inspections` 分别校验 `requirement.read`、`bug.read`、`knowledge.read`、`code_inspection.read`，需求/Bug/代码巡检列表按产品 scope 过滤 | Codex |
| v1.1.411 | 2026-06-27 | `GET /api/assistant/reference-candidates` 裸 `@` 默认候选顺序收紧：优先保留知识文档、需求、研发任务、定时作业、运行记录、插件动作、插件连接、AI 角色和 Skill，执行诊断来源仍可引用但不挤占常用对象首屏 | Codex |
| v1.1.410 | 2026-06-27 | `GET /api/knowledge/documents` 补齐知识中心主列表远程分页契约：带 `page/page_size` 时在 PostgreSQL read model 侧完成权限过滤、关键字、空间、目录、类型、索引状态、权限角色筛选、白名单排序，并返回 `query/performance` 观测 | Codex |
| v1.1.409 | 2026-06-27 | `GET /api/system/ai-skills` 与 `GET /api/system/ai-agents` 补齐远程分页契约：带 `page/page_size` 时支持关键字、状态和专项筛选、白名单排序，并返回 `query/performance` 观测；AI 能力配置页默认请求服务端分页结果 | Codex |
| v1.1.408 | 2026-06-27 | `GET /api/system/scheduled-job-runs` 补齐远程分页契约：支持 `page/page_size/sort_by/sort_order`、运行 ID、作业 ID、状态和产品 scope 过滤，定时作业页面运行记录页签默认请求服务端分页结果并展示可排序开始/完成时间 | Codex |
| v1.1.407 | 2026-06-27 | 插件管理连接和动作页签已接入分页读模型：页面主表默认调用 `GET /api/system/plugin-connections` 与 `GET /api/system/plugin-actions` 的 `page/page_size/sort_by/sort_order` 查询，不再以旧全量返回做主表分页和排序 | Codex |
| v1.1.406 | 2026-06-27 | AI 助手引用候选支持执行诊断来源类型：`assistant_chat_run`、`assistant_message`、`model_gateway_log`、`plugin_invocation_log`、`ai_executor_task`、`ai_executor_runner`、`code_inspection_report`、`audit_event` 等可通过 `GET /api/assistant/reference-candidates?type=&query=` 解析为脱敏引用；助手深链 `/assistant?reference_type=&reference_id=&prompt=` 会带入问题和上下文，解析和最终引用注入均要求执行诊断读权限 | Codex |
| v1.1.405 | 2026-06-27 | `GET /api/assistant/action-drafts` PostgreSQL 运行态改为优先使用草案任务台 read model 完成当前用户、动作、状态、时间、关键词、排序和分页查询，并返回状态/采纳/处理/修改率汇总与性能观测 | Codex |
| v1.1.404 | 2026-06-27 | AI 助手引用对可解析交付主体新增“全链路”入口；`/api/lifecycle/full-chain` 接受 `iteration_version` 作为 `product_version` 兼容别名并沿用产品 scope 校验 | Codex |
| v1.1.403 | 2026-06-27 | 需求全链路响应补齐 `branch_configs` 与 `audit_events`，阶段摘要和时间线覆盖版本级代码分支配置、主体审计事件 | Codex |
| v1.1.402 | 2026-06-27 | `GET /api/delivery/rd-task-executor-policies` 补齐服务端分页、筛选、排序和 `query/performance` 观测；需求全链路接口统一校验 `requirement.read/task.read/workspace.read` 与产品 scope | Codex |
| v1.1.401 | 2026-06-27 | 新增 `GET /api/lifecycle/full-chain` 统一主体入口，支持从 Bug、迭代版本和代码巡检报告解析到需求全链路，并在响应中返回 `anchor` 与 `code_inspection_reports` | Codex |
| v1.1.400 | 2026-06-27 | 执行诊断列表新增 `refresh=true` 强制刷新参数；默认列表优先读取已有 `execution_trace_snapshots` 快照，避免普通分页查询同步重建全量 Trace 导致慢查询 | Codex |
| v1.1.399 | 2026-06-26 | 代码巡检治理概览新增 `quality_gate_violations[]`，按门禁指标或规则聚合失败原因、严重级别、触发次数、报告数、实际值/阈值和最近报告摘要 | Codex |
| v1.1.398 | 2026-06-26 | 执行诊断列表和详情响应补充 `diagnostic_nodes[]`，服务端从异常/运行中节点派生安全摘要，避免前端和 AI 助手自行解析完整节点 metadata | Codex |
| v1.1.397 | 2026-06-26 | 执行诊断查询语义澄清：`source_type` 是来源类型，可筛选根或节点来源；前端筛选项展示为“来源类型”，不再称为“根类型” | Codex |
| v1.1.396 | 2026-06-26 | 执行诊断深链契约收紧：前端和文档示例统一使用 `source_id + source_type` 定位来源节点，避免仅按 ID 下钻造成跨来源歧义 | Codex |
| v1.1.395 | 2026-06-26 | `GET /api/system/roles` 补齐管理列表查询契约，支持 `page/page_size`、角色、分类、业务角色、可见入口、权限点、状态、白名单排序和 `query/performance` 观测；角色管理页改为调用远程分页接口 | Codex |
| v1.1.394 | 2026-06-24 | 执行诊断快照刷新收口为单事务：`execution_trace_snapshots` 的 upsert 与过期快照删除必须原子提交，避免列表/详情读到半刷新诊断链路 | Codex |
| v1.1.393 | 2026-06-24 | 执行诊断 `source_type` 新增 `ai_executor_runner`，Runner 节点会随 AI 执行器任务进入同一 Trace，可按 Runner ID 过滤或下钻排查接单、心跳和工作区配置 | Codex |
| v1.1.392 | 2026-06-24 | 执行诊断模型网关日志链路补齐审计吸附：`model_gateway_log` Trace 会关联 subject、payload 或 ai_task 指向的审计事件，`source_id=audit_event_id` 可反查同一模型调用链路 | Codex |
| v1.1.391 | 2026-06-24 | 插件连接和插件动作列表新增可选远程分页契约：带 `page/page_size` 时支持关键字、插件、状态、环境筛选和白名单排序，并返回 query/performance 观测信息 | Codex |
| v1.1.390 | 2026-06-24 | 执行诊断 `source_type` 新增 `result_write_record`，定时作业和插件调用链路聚合结果写入记录，可按写入记录 ID 反查“是否真正写入报告/反馈/通知” | Codex |
| v1.1.389 | 2026-06-24 | 代码巡检 finding 新增误报忽略审批 API：支持提交 suppression 申请、审批通过或驳回，详情返回审批状态并同步报告 suppression 统计和审计事件 | Codex |
| v1.1.388 | 2026-06-24 | 代码巡检治理概览新增 `rule_governance`，聚合最近报告规则/扫描器版本、版本分布、suppression 总量和过滤原因分布，用于页面展示规则包漂移与误报/已接受风险治理状态 | Codex |
| v1.1.387 | 2026-06-24 | 执行诊断 `source_type` 新增 `assistant_message` 节点类型，AI 助手运行链路可按用户消息或助手消息 ID 通过 `source_id` 精准定位，供草案任务台来源链路跳转使用 | Codex |
| v1.1.386 | 2026-06-24 | 新增 `GET /api/system/permissions/diagnostics`，按用户、菜单路径、权限点和数据范围返回允许/阻断解释，用于角色管理页用户权限排障 | Codex |
| v1.1.385 | 2026-06-24 | 新增 `GET /api/system/scheduled-job-catalog`，返回服务端作业类型、必填规则、调度/执行模式、连接环境和代码巡检选项，供定时作业页面和助手草案复用 | Codex |
| v1.1.384 | 2026-06-24 | 执行诊断列表新增 `source_id` 查询参数，支持按任一链路节点来源 ID 精准定位；前端 `/governance/execution-traces?source_id=...` 命中唯一链路时自动打开详情 | Codex |
| v1.1.383 | 2026-06-23 | 执行诊断 API 的 `source_type` 新增 `assistant_chat_run`，AI 助手聊天运行可作为链路根节点关联模型网关日志与审计事件 | Codex |
| v1.1.382 | 2026-06-23 | 代码巡检治理概览 `sla` 补充整改任务覆盖率、已派生任务数、未派生任务数和最早未派生时间，页面展示整改任务覆盖率 | Codex |
| v1.1.381 | 2026-06-23 | 代码巡检治理概览 `trend[]` 补充质量门禁通过、失败、跳过和未知计数，运营治理 / 代码巡检页面展示质量门禁趋势 | Codex |
| v1.1.380 | 2026-06-23 | 新增 `GET /api/system/permissions/matrix` 只读 RBAC 策略矩阵接口，返回角色权限、菜单入口、数据范围、高风险权限和菜单权限缺口诊断，角色管理页用于权限审计和排障 | Codex |
| v1.1.379 | 2026-06-23 | 执行诊断 API 在 PostgreSQL 模式下新增 `execution_trace_snapshots` 快照读模型，列表和详情优先读取可重建快照并保留测试 fallback | Codex |
| v1.1.378 | 2026-06-23 | 新增 AI 助手草案任务台列表 API：`GET /api/assistant/action-drafts` 支持当前用户草案分页、筛选、排序、状态汇总、采纳率、处理率和用户修改率，用于 `/assistant/drafts` 工作台闭环 | Codex |
| v1.1.377 | 2026-06-23 | 新增执行诊断 API：`GET /api/governance/execution-traces` 和详情接口按运行根聚合定时作业、插件、AI 执行器、模型网关、代码巡检和审计节点，并统一脱敏元数据 | Codex |
| v1.1.376 | 2026-06-21 | AI 助手效果指标补齐产品/角色/时间段/动作过滤、每日趋势、草案类型趋势和 `/api/assistant/metrics/export` 导出契约；助手页面样式迁移到页面级 scoped CSS | Codex |
| v1.1.375 | 2026-06-21 | AI 助手会话列表新增 cursor/limit 分页响应，历史草案工具结果输出安全白名单和敏感字段脱敏，指标明细按 limit 下推返回 | Codex |
| v1.1.374 | 2026-06-21 | 研发执行器策略任务类型选项口径补齐：PRD/原型/产品详细设计、技术方案、代码实现/开发计划、代码评审、自动化测试、代码整改、发布上线评估和上线后分析均可在策略配置中选择 | Codex |
| v1.1.373 | 2026-06-21 | 研发执行器策略 API 新增：需求交付策略只匹配插件管理下 Codex/Claude Code/OpenClaw Runner，不装配 Agent/Skill；AI 任务启动命中策略后返回 `executor_task_id/runner_id`，AI 执行器任务列表支持按 `ai_task_id` 反查 | Codex |
| v1.1.372 | 2026-06-20 | AI 助手运行状态接口补齐 self-check `checks[]` 与 `ready`，效果指标返回查看埋点口径说明；会话列表可按命令签名折叠重复命令，并新增系统管理侧 `@` 能力配置页与真实页面 smoke 覆盖 | Codex |
| v1.1.371 | 2026-06-20 | AI 助手 @ 动作候选新增运营配置 API 和 `assistant_action_reference_configs` 表；效果指标新增时间窗口参数与 `/metrics/details` 明细钻取接口 | Codex |
| v1.1.370 | 2026-06-20 | AI 助手聊天新增 `assistant_chat_runs` 运行生命周期、消息状态字段和服务端取消接口，停止生成可审计追踪 | Codex |
| v1.1.369 | 2026-06-19 | AI 助手动作候选选择后改为保留 `@动作名` 命令前缀并承接用户正文，不再用候选 prompt 覆盖输入 | Codex |
| v1.1.368 | 2026-06-19 | AI 助手 @ 候选补齐 `assistant_action` 动作项，支持按关键词搜索新建需求/Bug/插件/定时作业/知识/AI 能力配置入口，前端选择后只回填指令不注入上下文 | Codex |
| v1.1.367 | 2026-06-19 | AI 助手草案支持表单编辑后 PATCH payload 再确认，确认接口补齐重复提交幂等返回；运营类 @ 候选按产品 scope 过滤，角色快捷任务配置补齐前端管理入口 | Codex |
| v1.1.366 | 2026-06-19 | AI 助手角色快捷任务补齐运营配置 API、企业/模板/灰度过滤和审计；效果指标拆分草案详情/深链查看并输出定时作业运行归因分布 | Codex |
| v1.1.365 | 2026-06-18 | AI 助手补齐草案详情查看埋点、定时作业运行助手归因、角色快捷任务 DB 配置和结构化引用严格优先契约 | Codex |
| v1.1.364 | 2026-06-18 | AI 助手效果指标失败修复率契约收紧为仅统计成功 `manual_rerun`；草案处理率公式补回 expired | Codex |
| v1.1.363 | 2026-06-18 | AI 助手 run-once 契约补齐：定时作业管理权限用户可获得缺失作业草案，前端需展示无运行记录时的未执行原因卡 | Codex |
| v1.1.362 | 2026-06-18 | AI 助手插件连接/动作草案确认权限拆分：使用插件管理权限而不是仅限 admin 角色 | Codex |
| v1.1.361 | 2026-06-18 | AI 助手动作草案确认权限拆分：AI Skill / AI角色草案使用 AI 能力管理权限，定时作业草案继续使用定时作业管理权限 | Codex |
| v1.1.360 | 2026-06-18 | AI 助手 `create_analysis_draft` 工具项补充五步 `wizard_steps`，分析草案卡片可显示配置向导 | Codex |
| v1.1.359 | 2026-06-18 | AI 助手 run-once 契约补充：周反馈官方作业消歧先于停用或非洞察的精确同名作业 | Codex |
| v1.1.358 | 2026-06-18 | AI 助手运行诊断前端契约补充：三段状态需展示为“是否成功”的用户可读判断 | Codex |
| v1.1.357 | 2026-06-18 | AI 助手草案模板市场 `wizard_steps` 收敛为五步闭环流程，知识引用不再作为单独模板步骤 | Codex |
| v1.1.356 | 2026-06-17 | 对齐 AI 助手效果指标前端展示名：知识引用命中率与接口字段保持一致 | Codex |
| v1.1.355 | 2026-06-17 | AI 助手新增草案修改标记接口，并细化周反馈 run-once 官方作业消歧评分契约 | Codex |
| v1.1.354 | 2026-06-17 | AI 助手动作草案详情响应补充 `wizard_steps[]`，用于深链和历史草案卡片恢复配置向导 | Codex |
| v1.1.353 | 2026-06-17 | AI 助手 run-once 前端契约补充：运行状态未变化但 `execution_nodes` 更新时也必须刷新进度卡片 | Codex |
| v1.1.352 | 2026-06-17 | AI 助手引用候选和解析契约补充 `knowledge_space` / `knowledge_folder`，按权限注入范围内有限 chunk | Codex |
| v1.1.351 | 2026-06-17 | AI 助手引用候选搜索契约补充：定时作业类型词不再优先匹配运行记录，运行/失败词才优先匹配 `scheduled_job_run` | Codex |
| v1.1.350 | 2026-06-17 | AI 助手前端 `@` 候选标签契约补充：`ai_task` 显示“研发任务”，`ai_skill` 显示“Skill” | Codex |
| v1.1.349 | 2026-06-17 | AI 助手 `@` 默认候选补齐 `plugin_connection`，管理员裸 `@` 可见插件连接配置引用 | Codex |
| v1.1.348 | 2026-06-17 | AI 助手 run-once 前端契约补充：点击发送或按 Enter 时用当前 @ 文本按 `type=scheduled_job` 补查引用候选 | Codex |
| v1.1.347 | 2026-06-17 | AI 助手聊天契约新增 `assistant.plugin_connection_diagnostic`，用于不调用模型网关解释最近插件连接失败测试 | Codex |
| v1.1.346 | 2026-06-17 | AI 助手 run-once 运行卡片前端契约补充：running/queued 轮询结果需从 `execution_nodes` 展示当前执行进度 | Codex |
| v1.1.345 | 2026-06-17 | AI 助手运行诊断前端契约补充：诊断阶段需展示安全的关联日志 ID，便于追踪模型日志和插件调用日志 | Codex |
| v1.1.344 | 2026-06-17 | AI 助手前端契约补充：引用候选可在本次上下文查看摘要，run-once 定时作业草案确认按钮展示“确认并执行一次” | Codex |
| v1.1.343 | 2026-06-17 | AI 助手定时作业草案配置向导前端契约补充：需前置配置或阻塞步骤可一键回填生成前置草案提示 | Codex |
| v1.1.342 | 2026-06-17 | AI 助手动作草案终态前端契约补充：已取消、已过期或失败草案不得再应用到配置表单 | Codex |
| v1.1.341 | 2026-06-17 | AI 助手 `@` 默认候选未指定类型时按引用类型均衡合并，前端裸 `@` 请求足量候选以展示知识、业务对象和管理员运维对象 | Codex |
| v1.1.340 | 2026-06-17 | AI 助手周反馈、邮件摘要和线上日志异常定时作业草案项统一返回 `wizard_steps[]`，前端可直接展示配置向导闭环 | Codex |
| v1.1.339 | 2026-06-17 | AI 助手 `assistant.action_draft` 定时作业草案项补充 `wizard_steps` 配置向导状态，`@定时作业 执行一次` 语义匹配多个相似任务时优先唯一启用且 active 的可执行任务 | Codex |
| v1.1.338 | 2026-06-17 | AI 助手动作草案支持 `create_ai_skill`/`create_ai_agent`，代码巡检 AI 草案可返回、确认并解析 AI 能力前置草案 | Codex |
| v1.1.337 | 2026-06-17 | AI 助手引用候选/解析 API 支持 `knowledge_chunk`，可只注入用户显式选中的知识片段 | Codex |
| v1.1.336 | 2026-06-17 | AI 助手动作草案前端契约补充当前页详情查看，run-once 工具结果补充前端轮询运行状态追踪 | Codex |
| v1.1.335 | 2026-06-17 | AI 助手 `assistant.task_creation_guide` 的 `suggestions` 与五类任务向导项保持一致 | Codex |
| v1.1.334 | 2026-06-17 | AI 助手 run-once 草案确认响应中的 `scheduled_job_run` 被前端用于展示本次运行追踪入口 | Codex |
| v1.1.333 | 2026-06-17 | AI 助手带 run-once 标记的定时作业草案确认后返回创建作业和本次手动运行记录 | Codex |
| v1.1.332 | 2026-06-17 | AI 助手 `@周反馈洞察 执行一次` 未命中已配置作业时返回可确认定时作业草案，不再停在找不到引用 | Codex |
| v1.1.331 | 2026-06-17 | AI 助手已引用 `scheduled_job_run` 时，失败诊断和上次成功对比支持短追问触发 | Codex |
| v1.1.330 | 2026-06-17 | AI 助手工作台侧栏按需消费 `/api/assistant/metrics`，展示当前用户草案闭环、引用和运行效果指标 | Codex |
| v1.1.329 | 2026-06-17 | AI 助手聊天新增 `scheduled_job_run_repair_draft`，可从失败运行生成可确认的结果动作修复草案 | Codex |
| v1.1.328 | 2026-06-17 | AI 助手 `@定时作业 执行一次` API 契约补充完整 @ 名称精确匹配优先，并覆盖错误自动候选引用 | Codex |
| v1.1.327 | 2026-06-17 | AI 助手聊天新增 `assistant.scheduled_job_run_comparison` 工具结果，对比当前运行和同作业上次成功运行差异 | Codex |
| v1.1.326 | 2026-06-17 | AI 助手 `assistant.scheduled_job_diagnostic` 结果动作段补充结果写入记录 ID、写入目标和写入状态 | Codex |
| v1.1.325 | 2026-06-17 | AI 助手动作草案支持 `expires_at` 与 `expired` 状态，确认过期草案返回 `DRAFT_EXPIRED`，指标返回过期草案数量 | Codex |
| v1.1.324 | 2026-06-17 | AI 助手聊天支持线上日志异常分析模板生成 `online_log_anomaly_job_draft`，返回可确认的 AI 定时作业服务端草案 | Codex |
| v1.1.323 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 对 AI 类长任务改为先返回运行中记录，后台继续完成用户反馈洞察等执行链路 | Codex |
| v1.1.322 | 2026-06-17 | AI 助手动作草案支持 `create_analysis_draft`，发布风险分析和知识库巡检可确认生成 `assistant_analysis` 追踪结果 | Codex |
| v1.1.321 | 2026-06-17 | AI 助手聊天支持邮件摘要模板生成 `email_digest_job_draft`，返回可确认的邮件收取定时作业服务端草案 | Codex |
| v1.1.320 | 2026-06-17 | AI 助手 API 新增 `/api/assistant/draft-templates`，返回按角色过滤的官方草案模板市场目录 | Codex |
| v1.1.319 | 2026-06-17 | AI 助手效果指标补齐 `scheduled_job_run_*`、`failed_run_*` 和 `knowledge_reference_hit_*` 字段 | Codex |
| v1.1.318 | 2026-06-17 | AI 助手 API 新增 `/api/assistant/metrics` 当前用户效果指标，返回草案采纳率、用户修改率、动作运行成功率和显式引用使用率 | Codex |
| v1.1.317 | 2026-06-16 | AI 执行器 API 新增管理员侧测试接口，返回系统默认执行器或本地 Runner 健康诊断 | Codex |
| v1.1.316 | 2026-06-16 | 插件连接页面契约补充“保存并测试”：客户端保存连接后复用响应 ID 调用现有测试接口 | Codex |
| v1.1.315 | 2026-06-16 | Runner 安装包公共文件新增 START_STOP.md，按目标系统说明启动、停止、状态、重启和禁用自启命令 | Codex |
| v1.1.314 | 2026-06-16 | AI 执行器 Runner 安装包下载支持 `target_os/arch/install_mode`，按 Linux、macOS、Windows、Docker 和通用手动安装返回系统专属 ZIP | Codex |
| v1.1.313 | 2026-06-16 | AI 执行器 Runner API 增加 Codex/Claude Code/Hermes/OpenClaw 命令配置和 Runner 安装包下载接口 | Codex |
| v1.1.312 | 2026-06-16 | 代码巡检 API 明确 native 扫描私有仓库凭据来源和 AI 后处理保留扫描快照字段 | Codex |
| v1.1.311 | 2026-06-16 | 代码巡检 API 明确 native 扫描外部引擎执行状态、coverage_warning 语义和取消运行不写报告 | Codex |
| v1.1.310 | 2026-06-16 | 代码巡检 API 补充 baseline/已接受风险、质量门禁、多仓库运行汇总、报告详情 scan_summary 和上次扫描对比字段 | Codex |
| v1.1.309 | 2026-06-16 | 定时作业 API 补充本地代码扫描异步运行、固定工作区快照字段、规则/忽略/增量配置和详情报告快照字段 | Codex |
| v1.1.308 | 2026-06-15 | 定时作业 API 补充代码巡检 `scan_mode`：`native_full_scan` 可不传插件动作/连接，运行摘要和报告返回本地扫描覆盖率元数据 | Codex |
| v1.1.307 | 2026-06-15 | 定时作业 API 补充代码巡检仓库和扫描分支契约：`code_repository_inspection` 使用 `config_json.repository_id/branch`，分支缺失时服务端取仓库默认分支，运行插件输入和 AI 上下文携带分支 | Codex |
| v1.1.306 | 2026-06-15 | AI 助手引用候选/解析扩展定时作业、运行记录、插件动作、AI角色和 Skill；聊天工具结果新增 `assistant.scheduled_job_diagnostic` 运行失败诊断 | Codex |
| v1.1.305 | 2026-06-14 | AI 助手 API 落地显式知识引用和服务端动作草案：聊天请求支持 `references`，新增引用候选/解析接口和 `/api/assistant/action-drafts` 创建、查询、确认、取消接口 | Codex |
| v1.1.304 | 2026-06-14 | MaxCompute 从官方标准插件与官方动作模板目录移除，历史官方 MaxCompute 插件自动降级为普通 HTTP 插件；连接编辑不再展示项目与表配置 schema | Codex |
| v1.1.303 | 2026-06-14 | GitLab 官方连接表单改为单字段“GitLab 地址”，支持本地自建 GitLab 项目 URL，保存时自动同步 `endpoint_url` 并解析 `request_config.query.project_id/project_path/api_version`，用户不再手工填写 Project ID / Group ID / API 版本 | Codex |
| v1.1.302 | 2026-06-14 | GitHub 官方连接表单改为单字段“仓库地址”，支持 HTTPS、SSH 和 `owner/repo` 简写，前端与后端自动解析并保存 `request_config.query.owner/repo`，用户不再手工拆分 Owner 和仓库名 | Codex |
| v1.1.301 | 2026-06-14 | GitHub 官方连接认证收口：官方模板不再预填假 `token_ref`，新增/编辑 GitHub 连接必须填写 Bearer Token 或平台可解析的密钥引用；本地联调可直填 GitHub PAT，生产建议使用 `vault/...` 或 `env:...` 引用 | Codex |
| v1.1.300 | 2026-06-14 | 插件连接表单优化：官方 `connection_schema` 字段作为业务配置优先展示，GitHub/GitLab 仓库项目字段不再要求用户在高级 Params 中猜填；插件动作路径支持从合并后的连接/动作参数解析 `{{owner}}`、`{{repo}}`、`{{project_id}}` 等模板变量 | Codex |
| v1.1.299 | 2026-06-14 | 任务编排平台 API 增强：`/api/system/scheduled-jobs/dry-run` 返回数据连接、AI 契约和结果写入预览；作业运行按 `config_json.orchestration` 执行多连接合并策略；Skill 输出 Schema 与动作映射运行前校验；插件市场返回模板版本状态，新增 `/api/system/plugins/{plugin_id}/copy` 复制官方插件为自定义插件 | Codex |
| v1.1.298 | 2026-06-14 | 系统 RBAC API 扩展菜单管理：新增菜单资源创建、编辑、删除、启停和重排序接口，`system.menus.manage` 作为写权限，系统菜单删除返回保护错误 | Codex |
| v1.1.297 | 2026-06-14 | 定时作业 API 增加多连接/多动作字段：`POST/PATCH /api/system/scheduled-jobs` 接收 `plugin_connection_ids` / `plugin_action_ids`，响应和模板快照保留完整数组，旧 `plugin_connection_id` / `plugin_action_id` 继续返回第一项 | Codex |
| v1.1.296 | 2026-06-14 | 定时作业 API/页面契约补充：配置页按“数据连接 → AI执行 → 动作 → 调度”分区展示，列表合并展示“数据连接 / AI执行 / 动作 / 调度”，运行详情按“运行链路”展示数据连接获取、AI执行处理和动作反馈 | Codex |
| v1.1.295 | 2026-06-14 | 定时作业 API/页面契约补充：新增/编辑页连续展示调度方式、Cron 和间隔秒数，`source_system` 仍随 payload 保存但作为内部来源标识隐藏显示 | Codex |
| v1.1.294 | 2026-06-14 | API 文档同步 AI角色用户侧命名：`/api/system/ai-agents` 和 `agent_id` 字段保持不变，页面标签、定时作业草案和运行详情统一展示为 AI角色 | Codex |
| v1.1.293 | 2026-06-14 | 定时作业 API 同步系统默认执行器：AI 执行器仓库任务模板默认返回 `config_json.ai_executor`，运行摘要 `runner_execution` 透传 `model_gateway_called/model_gateway_log_id/result_json` | Codex |
| v1.1.292 | 2026-06-14 | AI 执行器 API 增加系统默认执行器契约：`GET /api/system/ai-executor-runners` 返回只读 `ai_executor_runner_system_default`，插件市场和动作模板默认 `executor_type=model_gateway`，动作调用可直接走系统默认模型 | Codex |
| v1.1.291 | 2026-06-14 | 插件管理 API 文案契约收口：动作资源的页面标签、删除占用提示、市场数量和模板入口统一展示为“动作”，AI 执行器 Runner 不改名 | Codex |
| v1.1.290 | 2026-06-14 | 导航与插件日志归属调整：研发任务入口迁至 `/delivery/rd-tasks`，插件调用日志保留排障 API 但由定时作业运行详情消费，插件管理不展示独立日志页签 | Codex |
| v1.1.289 | 2026-06-13 | Runner 增加 Token 轮换、任务日志/取消/超时控制；定时作业成功运行可反向生成模板，运行详情返回 Trace DAG | Codex |
| v1.1.288 | 2026-06-13 | 插件市场返回官方连接 schema，定时作业模板返回向导步骤，Runner 返回健康状态/启动命令，代码巡检支持创建整改任务并在运行节点展示 | Codex |
| v1.1.287 | 2026-06-13 | 新增 AI 执行器 Runner 管理、心跳、认领和完成回写接口；`ai_executor` 支持 `runner_polling` 与 OpenClaw | Codex |
| v1.1.286 | 2026-06-13 | `GET /api/system/result-write-records` 增加 `scheduled_job_run_id` 过滤，并明确由定时作业运行详情消费 | Codex |
| v1.1.285 | 2026-06-13 | 新增 `GET /api/system/result-write-records`，通用查看邮件通知等结果写入反馈并支持未来写入目标扩展 | Codex |
| v1.1.284 | 2026-06-13 | 插件市场和动作模板接口补充 `ai_executor` 官方插件、邮件收取模板和邮箱 SMTP/IMAP/POP3 收发连接参数 | Codex |
| v1.1.283 | 2026-06-13 | `/api/system/plugin-marketplace` 返回官方连接模板 `connection_defaults` 与 `connection_template_version`，供插件页和 AI 助手生成连接配置 | Codex |
| v1.1.282 | 2026-06-13 | 新增 `GET /api/system/scheduled-job-templates`，返回官方定时作业模板包、默认 payload、资源选择规则和模板版本 | Codex |
| v1.1.281 | 2026-06-13 | 新增 `GET /api/system/scheduled-job-runs/observability`，返回定时作业运行健康概览、失败原因、最近失败和慢运行 | Codex |
| v1.1.280 | 2026-06-13 | 定时作业运行节点摘要补充请求方法、URL、响应状态、耗时和业务记录 ID；插件连接测试历史可展开回放完整请求响应 | Codex |
| v1.1.279 | 2026-06-13 | 新增 `GET /api/governance/code-inspections/dashboard`，代码巡检按当前筛选返回趋势、规则、排行和严重问题 SLA | Codex |
| v1.1.278 | 2026-06-13 | 新增 `GET /api/system/result-write-targets`，动作表单和写入预览按服务端注册表解析目标、默认映射和字段 | Codex |
| v1.1.277 | 2026-06-13 | 插件连接测试响应补充 `test_history`、`action_template_draft`、`repair_suggestions`，连接列表返回最近测试回放记录 | Codex |
| v1.1.276 | 2026-06-13 | 动作模板接口返回 `template_version`，`assistant.action_draft` 动作草案补充 `template_code/template_version` 来源信息 | Codex |
| v1.1.275 | 2026-06-13 | 新增动作模板目录接口，前端按服务端模板动态生成动作配置 | Codex |
| v1.1.274 | 2026-06-13 | 插件连接测试后更新连接 `last_test_summary`，连接列表返回最近测试摘要 | Codex |
| v1.1.273 | 2026-06-13 | 定时作业复跑响应和运行列表新增 `source_run_summary`，供详情页展示来源运行对比 | Codex |
| v1.1.272 | 2026-06-12 | 定时作业运行摘要复用动作 `write_preview`，邮件通知结果动作返回投递 ID、状态和收件人摘要 | Codex |
| v1.1.271 | 2026-06-12 | `assistant.action_draft` 邮箱通知动作草案使用 `email_notifications` 映射并展示中文写入目标 | Codex |
| v1.1.270 | 2026-06-12 | 动作 `result_mapping.write_target` 补充 `email_notifications`，试运行写入预览返回邮件投递字段 | Codex |
| v1.1.269 | 2026-06-12 | 定时作业页面支持 `?tab=runs&run_id=` 深链打开运行详情，代码巡检详情来源作业/来源运行改为可跳转链接 | Codex |
| v1.1.268 | 2026-06-12 | 代码巡检报告列表/详情补充 `plugin_connection_id` 和 `plugin_action_id`，页面展示来源链路用于排障追踪 | Codex |
| v1.1.267 | 2026-06-12 | `assistant.action_draft` 草案组补充前置解析契约，保存连接/动作草案后后续草案可回填真实资源 ID | Codex |
| v1.1.266 | 2026-06-12 | `assistant.action_draft` 代码巡检作业缺少前置配置时返回连接、动作和作业草案组，并在作业 payload 标记前置草案 ID | Codex |
| v1.1.265 | 2026-06-12 | `assistant.action_draft` 新增 `create_plugin_connection` 草案，可生成 GitHub/GitLab/邮箱连接配置并带入插件管理新增连接表单 | Codex |
| v1.1.264 | 2026-06-12 | 采集运行记录 `collector_type` 枚举补齐定时作业运行类型，并要求数据库约束与接口校验一致 | Codex |
| v1.1.263 | 2026-06-12 | 定时作业 `template_source` 增加前端可视化约定，列表、复制弹窗和运行详情展示来源 | Codex |
| v1.1.262 | 2026-06-12 | 定时作业复制模板化约定 `config_json.template_source`，创建/更新审计 payload 返回来源 | Codex |
| v1.1.261 | 2026-06-12 | 插件连接测试 `request_summary` 新增 `original_request_config`，用于排查保存值与最终请求值差异 | Codex |
| v1.1.260 | 2026-06-12 | 插件连接测试 `request_summary` 新增 `variable_resolutions` 和解析时区，页面可展示系统变量解析明细 | Codex |
| v1.1.259 | 2026-06-12 | 定时作业运行接口 `manual_rerun` 可携带 `source_run_id`，运行实例和审计 payload 返回复跑来源 | Codex |
| v1.1.258 | 2026-06-12 | `assistant.action_draft` 新增 `create_plugin_action` 草案，可生成 GitHub/GitLab 代码巡检和邮箱通知动作配置 | Codex |
| v1.1.257 | 2026-06-12 | 动作试运行补充 `plugin_action.trial_succeeded/failed` 审计事件，记录轻量治理上下文但不生成正式调用日志 | Codex |
| v1.1.256 | 2026-06-12 | 官方插件市场消费侧补充动作模板入口，前端可根据 `action_templates` 从市场项直接打开对应动作模板 | Codex |
| v1.1.255 | 2026-06-12 | `assistant.action_draft` 生成代码巡检草案时可按用户意图带出 `ai_generated`、模型网关、Agent 和 Skill 字段 | Codex |
| v1.1.254 | 2026-06-12 | 定时作业运行终态审计 payload 扩展 AI 装配、动作、连接环境、知识引用和结果写入目标轻量字段 | Codex |
| v1.1.253 | 2026-06-12 | `code_repository_inspection` 在 `ai_assisted/ai_generated` 执行模式下必须调用模型网关处理插件扫描结果，运行摘要返回 `skill_processing` 和 `result_action` 三段式节点 | Codex |
| v1.1.252 | 2026-06-12 | `GET /api/system/plugin-connections` 新增 `environment` 查询参数并校验连接环境枚举，支持插件连接列表按环境筛选 | Codex |
| v1.1.251 | 2026-06-12 | 插件管理新增 `GET /api/system/plugin-marketplace` 官方插件市场接口，返回标准插件推荐场景、动作模板、安装状态和连接/动作数量 | Codex |
| v1.1.250 | 2026-06-12 | 定时作业运行终态审计 payload 补充 `trigger_type/status/records_imported/collector_run_id/plugin_invocation_log_id/product_id` 等上下文 | Codex |
| v1.1.249 | 2026-06-12 | 定时作业运行接口新增可选 `trigger_type` 请求体，支持 `manual`、`manual_rerun` 和 `scheduler` 触发语义 | Codex |
| v1.1.248 | 2026-06-12 | 插件连接测试 `request_summary` 新增 `curl_command`，用于页面展示可复制复现命令 | Codex |
| v1.1.247 | 2026-06-12 | AI 助手草案保存为定时作业后，`scheduled_job.created/updated` 审计 payload 输出草案 ID、来源和标题 | Codex |
| v1.1.246 | 2026-06-12 | AI 助手定时作业草案可带入新增作业表单，提交时保留草案中的动态变量映射和结果动作 | Codex |
| v1.1.245 | 2026-06-12 | AI 助手页面展示 `assistant.action_draft` 定时作业草案卡片，聊天响应/历史消息的 `tool_results` 不再只作为隐藏 JSON | Codex |
| v1.1.244 | 2026-06-12 | AI 助手聊天工具结果新增 `assistant.action_draft`，可返回周反馈洞察和代码巡检定时作业创建草案且确认前不写入业务表 | Codex |
| v1.1.243 | 2026-06-12 | 动作试运行响应补充 `write_preview`，前端弹窗展示写入目标、预计写入数量、候选数量和样例数据 | Codex |
| v1.1.242 | 2026-06-12 | 代码巡检定时作业运行时应用动作/作业输出 `result_mapping`，支持从嵌套响应或 `$` 根数组提取巡检报告字段 | Codex |
| v1.1.241 | 2026-06-12 | 动作页面补充 GitHub/GitLab 代码巡检场景模板，默认生成官方插件请求配置和代码巡检报告映射 | Codex |
| v1.1.240 | 2026-06-12 | 定时作业运行记录补充复跑契约：前端可从运行记录基于 `scheduled_job_id` 复用作业运行接口并展示新运行详情 | Codex |
| v1.1.239 | 2026-06-11 | 收紧 AI 类型定时作业 API 校验，补充运行详情三段节点和连接测试请求调试台响应展示要求 | Codex |
| v1.1.238 | 2026-06-11 | 动作 `result_mapping.write_target` 补充 `code_inspection_reports`，页面提供代码巡检报告 JSONPath 可视化配置 | Codex |
| v1.1.237 | 2026-06-11 | 代码巡检 API 增加提交人维度、`committer` 筛选、产品范围读取控制、severity mapping、严重 finding Bug 去重和结果动作状态摘要 | Codex |
| v1.1.236 | 2026-06-11 | 新增代码仓库巡检 API：`code_repository_inspection` 定时作业支持 `result_actions` 多结果动作，运行写入代码巡检报告、严重问题建 Bug 和通知记录，并提供运营治理代码巡检列表/详情接口 | Codex |
| v1.1.235 | 2026-06-11 | 新增 AI 助手工作台升级目标 API：`@` 引用候选/解析、聊天显式引用、动作草案、确认执行和取消草案 | Codex |
| v1.1.234 | 2026-06-11 | 补充插件删除 API：插件、连接、动作支持 DELETE；若仍被连接、动作、定时作业或调用日志引用则返回 409 并提示使用清单 | Codex |
| v1.1.233 | 2026-06-11 | 补充定时作业维护 API：列表页必须提供编辑和删除入口，后端支持 `DELETE /api/system/scheduled-jobs/{job_id}` 并写入删除审计 | Codex |
| v1.1.231 | 2026-06-11 | 补充插件维护 API 契约：插件、连接、动作均支持按 ID PATCH 编辑，连接/动作编辑保留历史 `***` 占位对应的原始密钥并继续支持 Params/Headers 可视化配置 | Codex |
| v1.1.232 | 2026-06-11 | 明确定时作业插件链路 API 语义：数据连接负责取数，Skill 负责分析处理，结果动作通过 `result_mapping.write_target` 声明写入目标；作业 `plugin_output_mapping` 为空时复用动作结果映射 | Codex |
| v1.1.230 | 2026-06-11 | 知识导入可靠性收口：worker 增加数据库租约 claim，目录归档按整棵子树生效，解析资产按 bucket/object_key 幂等 upsert，chunk set 保留索引状态用于回滚恢复 | Codex |
| v1.1.228 | 2026-06-11 | OCR JSON 知识导入的 chunk metadata 补充页内图片数量、表格数量和图片引用，前端 chunk 预览同步展示图片来源 | Codex |
| v1.1.227 | 2026-06-11 | 知识导入新增 `regex_section` 分块策略，可按 Markdown/章节/Section 分隔符切分并在 chunk metadata 写入分段标题和切分规则 | Codex |
| v1.1.226 | 2026-06-11 | 知识 chunk 版本化数据库约束收口：移除旧 `document_id/chunk_index` 唯一约束，新增 `document_id/chunk_set_id/chunk_index` 唯一索引以支持历史 chunk set 共存 | Codex |
| v1.1.225 | 2026-06-11 | 知识导入 worker 补偿扫描 queued 任务时沿用导入任务 `created_by` 作为写入归属，避免后台任务创建 chunk set 时违反用户外键 | Codex |
| v1.1.224 | 2026-06-11 | 知识导入解析产物拆分增强：`ocr_json` / `table_json` 解析器除生成 Markdown 外，还沉淀结构化资产并向 chunk metadata 写入页码、表格列和来源资产引用；worker 周期性补偿扫描 queued 任务 | Codex |
| v1.1.223 | 2026-06-11 | 知识导入任务新增应用内后台 worker/队列契约：上传、重解析和 retry 自动入队，补充 worker 状态接口和 run 运维补偿语义 | Codex |
| v1.1.222 | 2026-06-11 | 知识导入任务补充 run/retry/cancel、重解析、chunk set 预览/激活、父子分块 source 和目录批量整理契约 | Codex |
| v1.1.221 | 2026-06-10 | 知识中心新增知识空间、空间成员、目录、MinIO/S3 资产上传、导入任务和 asset preview API 契约，检索和列表支持空间/目录过滤 | Codex |
| v1.1.220 | 2026-06-10 | 补充 `user_feedback_insight_extract` 定时作业契约：可绑定 MaxCompute/MCP 动作，从 `insights_path` 映射读取洞察并写入用户反馈洞察表 | Codex |
| v1.1.232 | 2026-06-11 | 插件连接调试契约改为明文展示：连接响应、测试诊断、动作请求预览和插件调用日志返回真实 auth/request/header 值，不再因 `***` 占位提前拦截请求 | Codex |
| v1.1.231 | 2026-06-11 | 增强插件连接测试诊断契约：返回最终 URL、query、headers、Header 来源、`***` 占位检测和远端响应摘要，认证配置里的同名认证 Header 优先于 Params/Headers 表格值 | Codex |
| v1.1.230 | 2026-06-11 | 补充插件连接级请求配置契约：连接保存公共 `request_config.query/headers`，连接测试、动作预览和实际调用与动作配置合并 | Codex |
| v1.1.229 | 2026-06-11 | 补充插件配置体验优化契约：连接测试返回诊断步骤，动作支持试运行和映射命中，系统变量提供预览接口，定时作业插件输入映射默认表格化且 JSON 作为高级入口 | Codex |
| v1.1.233 | 2026-06-11 | 插件管理 API 补充 GitLab/GitHub 官方标准插件：列表返回 `is_system=true`，PATCH/DELETE 官方插件返回 409，连接维护平台参数 | Codex |
| v1.1.234 | 2026-06-11 | 插件管理 API 补充邮箱官方标准插件：列表返回 `email` 官方插件，连接维护邮件网关/API 认证、Header 和默认邮件参数 | Codex |
| v1.1.219 | 2026-06-10 | 新增插件管理 API：补充插件、连接、动作、调用日志、动作手动调用，以及定时作业引用动作的请求/响应字段 | Codex |
| v1.1.218 | 2026-06-10 | 新增定时系统作业和 AI 能力配置目标 API：补充 Agent、Skill、定时作业、运行实例、手动触发、取消、AI 配置快照和审计契约 | Codex |
| v1.1.217 | 2026-06-09 | 迭代版本新增代码分支配置 API，支持按版本维护多代码库基准分支、开发分支、状态和创建来源 | Codex |
| v1.1.216 | 2026-06-09 | Task 3 新增最小可用系统 RBAC API：权限点/菜单/角色治理、用户角色/范围授权和用户有效权限查询；角色变更写入 `role_change_events` 与 `audit_events` | Codex |
| v1.1.215 | 2026-06-07 | RBAC API 演进说明确认外部身份绑定：SSO 用户必须映射到系统 users.id，目标态新增 external identity 绑定接口，未绑定身份不授予默认权限 | Codex |
| v1.1.214 | 2026-06-07 | RBAC API 演进说明确认组织/部门、产品成员和知识空间：目标态新增部门、产品成员和知识空间接口，产品范围由产品管理页成员配置，知识检索按知识空间授权过滤 | Codex |
| v1.1.213 | 2026-06-07 | RBAC API 演进说明补充菜单权限：目标态新增菜单资源目录和角色菜单授权接口，`/api/auth/me` 返回 `menu_tree` 供左侧导航按授权渲染 | Codex |
| v1.1.212 | 2026-06-07 | RBAC API 演进说明补充研发交付扩展预置角色，后续角色目录将包含开发工程师、测试负责人、测试人员和发布负责人等系统模板 | Codex |
| v1.1.211 | 2026-06-07 | 补充系统权限管理 RBAC 重设计的 API 演进说明，明确 `/api/auth/roles` 作为兼容角色目录保留，目标角色治理接口迁移到 `/api/system/roles`、`/api/system/permissions` 和用户授权接口 | Codex |
| v1.1.210 | 2026-06-07 | 研发运营页面更名为日志监控，前端只保留 GitLab、Jenkins 和线上日志指标入口；采集运行和待归属数据 API 保留为历史兼容能力但不再作为当前页面功能入口 | Codex |
| v1.1.209 | 2026-06-07 | 需求 API 新增 `source` 来源字段与筛选排序；用户反馈新增转需求接口，转需求后同步反馈关联需求和 `linked` 状态 | Codex |
| v1.1.208 | 2026-06-07 | Code Review 报告响应新增只读 `writeback_template`，提供可人工复制到 GitLab MR / GitHub PR 评论区的 Markdown 结论模板；系统仍不自动回写远端 | Codex |
| v1.1.207 | 2026-06-07 | AI 助手聊天响应和历史消息新增 `tool_results`：后端在模型调用前按用户问题生成 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等 read-model 工具结果，模型请求携带 `system_context.tool_results`，助手消息 metadata 持久化工具结果与引用链接 | Codex |
| v1.1.206 | 2026-06-06 | GitLab MR / GitHub PR 预览响应新增 `permission_diagnostics`，快照响应新增 `previous_snapshot`、`diff_change_summary` 和 `snapshot_reused`，用于代码 Review 权限诊断、PR 刷新/重试和 diff 快照对比 | Codex |
| v1.1.205 | 2026-06-06 | `GET /api/system/model-gateway-configs` 增强为模型网关配置管理列表接口，支持 `page/page_size/sort_by/sort_order/name/provider/status/is_default/default_chat_model/default_embedding_model/embedding_connection_mode`，分页响应返回 `query/performance` 观测元数据，未传分页参数时保留原全量配置列表兼容契约 | Codex |
| v1.1.204 | 2026-06-06 | `GET /api/auth/roles` 增强为角色管理只读列表接口，支持 `page/page_size/sort_by/sort_order/role/category/business_role/menu_scope/permission/status`，分页响应返回 `query/performance` 观测元数据，未传分页参数时保留原角色目录全量列表兼容契约 | Codex |
| v1.1.203 | 2026-06-06 | `GET /api/users` 增强为用户管理 SQL/read model 列表接口，支持 `page/page_size/sort_by/sort_order/username/display_name/role/status`，分页响应返回 `query/performance` 观测元数据，未传分页参数时保留原全量列表兼容契约 | Codex |
| v1.1.202 | 2026-06-06 | 前端管理列表统一表格规范增强，角色、DevOps 列表展示与详情承载优化；管理列表 API 查询、分页、排序、筛选和性能响应契约不变 | Codex |
| v1.1.201 | 2026-06-06 | 生命周期上下文和看板快照写入 SQL 实现归入 LifecycleDashboardReadRepository，lifecycle context、dashboard source rows、缓存和 DB-first 恢复响应契约保持不变 | Codex |
| v1.1.200 | 2026-06-06 | 采集运行和待归属队列写入 SQL 实现归入 OperationalCollectionReadRepository，collector run、pending attribution 创建/处理和 DB-first 恢复响应契约保持不变 | Codex |
| v1.1.199 | 2026-06-06 | 用户洞察写入 SQL 实现归入 UserInsightReadRepository，用户反馈、使用指标、迭代建议生成/决策、转需求和统一用户洞察列表 DB-first 恢复响应契约保持不变 | Codex |
| v1.1.198 | 2026-06-06 | DevOps 指标写入 SQL 实现归入 DevopsReadRepository，GitLab daily、Jenkins release、线上日志创建和统一运营列表 DB-first 恢复响应契约保持不变 | Codex |
| v1.1.197 | 2026-06-06 | 知识写入 SQL 实现归入 KnowledgeReadRepository，知识文档创建/重建/删除、知识沉淀采纳/驳回、Embedding 兼容和 DB-first 恢复响应契约保持不变 | Codex |
| v1.1.196 | 2026-06-06 | Bug 写入 SQL 实现归入 BugReadRepository，Bug 登记、批量更新、修改、删除、重复缺陷引用修正和 DB-first 恢复响应契约保持不变 | Codex |
| v1.1.195 | 2026-06-06 | 任务运行态写入 SQL 实现归入 TaskReadRepository，Graph Run、Graph Checkpoint、Human Review、任务启动和 Review 决策响应契约保持不变 | Codex |
| v1.1.194 | 2026-06-06 | AI 任务主表写入 SQL 实现归入 TaskReadRepository，任务创建、启动、批量重试/取消、任务列表和 DB-first 恢复响应契约保持不变 | Codex |
| v1.1.193 | 2026-06-06 | 需求台账写入 SQL 实现归入 RequirementReadRepository，需求创建、修改、删除、批量排期/负责人/推进状态/生成任务和 DB-first 恢复响应契约保持不变 | Codex |
| v1.1.192 | 2026-06-06 | 产品配置写入 SQL 实现归入 ProductConfigReadRepository，产品、迭代版本、产品模块、产品 Git 仓库、相关系统的创建/修改/删除 API 响应契约保持不变 | Codex |
| v1.1.191 | 2026-06-06 | 审计事件保存和写入 SQL 实现归入 AuditReadRepository，审计事件列表、审计追加、跨域高影响动作审计和 DB-first 恢复契约保持不变 | Codex |
| v1.1.190 | 2026-06-06 | GitLab MR / GitHub PR 兼容快照和代码评审报告写入 SQL 实现归入 GitReviewReadRepository，MR/PR 快照、代码评审报告确认归档和 DB-first 恢复契约保持不变 | Codex |
| v1.1.189 | 2026-06-06 | 模拟 Issue 写回行转换和写入 SQL 实现归入 MockWritebackReadRepository，`POST /api/writeback/mock-issues` 幂等写回、任务详情聚合和 DB-first 恢复契约保持不变 | Codex |
| v1.1.188 | 2026-06-06 | AI 助手会话和消息写入 SQL 实现归入 AssistantChatReadRepository，助手聊天、会话列表、会话消息和用户级历史隔离 API 响应契约保持不变 | Codex |
| v1.1.187 | 2026-06-06 | 模型网关配置/日志写入 SQL 实现归入 ModelGatewayReadRepository，模型网关配置创建/修改/删除、测试日志和任务模型调用日志 API 响应契约保持不变 | Codex |
| v1.1.186 | 2026-06-06 | AI 任务详情、启动/取消/补充信息、Graph Run、Review 决策、Markdown 导出和模拟写回相关 legacy main 实现副本移除，API 继续由 tasks、export、writeback、code_review_reports routers 和对应 services 提供，响应契约保持不变 | Codex |
| v1.1.185 | 2026-06-06 | 模型网关和代码评审 executor legacy main helper 副本移除，模型网关配置/测试/调用日志、AI 任务启动和代码评审任务继续由 model_gateway 与 ai_tasks services 提供响应契约 | Codex |
| v1.1.184 | 2026-06-06 | 看板、DevOps 统一列表和用户洞察统一列表 legacy main 投影 helper 副本移除，相关 API 继续由 dashboard、devops_metrics 和 user_insights routers/services 提供，响应契约保持不变 | Codex |
| v1.1.183 | 2026-06-06 | 采集运行、待归属处理和 DevOps 明细 legacy main helper 副本移除，collectors、attribution 和 devops_metrics routers/services 继续提供列表、创建、更新和校验响应契约 | Codex |
| v1.1.182 | 2026-06-06 | 需求全链路 legacy main helper 副本移除，`GET /api/requirements/{requirement_id}/full-chain` 继续由 requirements router/service 提供，链路摘要、阶段实体、时间线和权限过滤响应契约保持不变 | Codex |
| v1.1.181 | 2026-06-06 | 知识中心 legacy main helper 副本移除，知识文档、沉淀候选和检索 API 继续由 knowledge router/services 提供，权限过滤、Embedding 兜底和 DB-first stale runtime 响应契约保持不变 | Codex |
| v1.1.180 | 2026-06-06 | 生命周期上下文 legacy main helper 副本移除，`GET /api/lifecycle/context` 继续由 lifecycle router/service 提供，响应、风险信号、source rows 和看板契约保持不变 | Codex |
| v1.1.179 | 2026-06-06 | 业务大脑配置恢复读取实现归入 BrainAppReadRepository，`GET /api/brain-apps` 和 PostgreSQL 运行时 rd_brain 配置读取契约保持不变 | Codex |
| v1.1.178 | 2026-06-06 | 知识中心恢复读取实现归入 KnowledgeReadRepository，知识文档、chunk、沉淀恢复数据与知识列表、沉淀候选和检索 SQL read model API 契约保持不变 | Codex |
| v1.1.177 | 2026-06-06 | Bug 恢复读取实现归入 BugReadRepository，Bug 恢复数据、版本归属和 Bug 管理列表 SQL read model API 的分页/筛选/排序契约保持不变 | Codex |
| v1.1.176 | 2026-06-06 | AI 任务和 workflow runtime 恢复读取实现归入 TaskReadRepository，AI 任务、Graph Run、Checkpoint、Human Review 恢复数据与任务/待 Review 列表 SQL read model API 契约保持不变 | Codex |
| v1.1.175 | 2026-06-06 | 需求台账恢复读取实现归入 RequirementReadRepository，需求恢复数据、负责人字段和需求列表 SQL read model API 的分页/筛选/排序契约保持不变 | Codex |
| v1.1.174 | 2026-06-06 | 产品配置恢复读取实现归入 ProductConfigReadRepository，产品、迭代版本、模块、Git 仓库和相关系统恢复数据与产品/版本列表 SQL read model API 契约保持不变 | Codex |
| v1.1.173 | 2026-06-06 | AI 助手会话和消息恢复读取实现归入 AssistantChatReadRepository，`GET /api/assistant/conversations`、会话消息查询和 DB-first 历史恢复响应契约保持不变 | Codex |
| v1.1.172 | 2026-06-06 | 用户洞察原始数据读取实现归入 UserInsightReadRepository，使用指标、用户反馈、迭代建议/决策和统一用户洞察列表 API 的筛选/排序/看板聚合契约保持不变 | Codex |
| v1.1.171 | 2026-06-06 | DevOps 原始指标读取实现归入 DevopsReadRepository，GitLab 每日指标、Jenkins 发布记录、线上日志指标和统一运营列表 API 的筛选/排序/看板聚合契约保持不变 | Codex |
| v1.1.170 | 2026-06-06 | 生命周期上下文和首页看板读取实现抽取为 LifecycleDashboardReadRepository，`GET /api/lifecycle/context` 与 `GET /api/dashboard/it-team` 的 DB source rows、缓存和响应契约保持不变 | Codex |
| v1.1.169 | 2026-06-06 | 模拟 Issue 写回恢复读取实现抽取为 MockWritebackReadRepository，`POST /api/writeback/mock-issues` 的幂等写回、任务详情聚合和 DB-first 恢复读取契约保持不变 | Codex |
| v1.1.168 | 2026-06-06 | GitLab MR / GitHub PR 兼容快照和代码评审报告读取实现抽取为 GitReviewReadRepository，快照复用、代码评审任务创建、报告确认归档和恢复读取契约保持不变 | Codex |
| v1.1.167 | 2026-06-06 | 采集运行和待归属队列读取 API 的 PostgreSQL 查询实现抽取为 OperationalCollectionReadRepository，`GET /api/collectors/runs` 与 `GET /api/attribution/pending-items` 的筛选、排序和真实空集合契约保持不变 | Codex |
| v1.1.166 | 2026-06-06 | 审计事件读取 API 的 PostgreSQL 查询实现抽取为 AuditReadRepository，`GET /api/audit/events` 的 ai_task/主体/操作者/事件类型/时间过滤、sequence 排序、分页和 query/performance 响应契约保持不变 | Codex |
| v1.1.165 | 2026-06-06 | 模型网关配置和模型调用日志读取 API 的 PostgreSQL 查询实现抽取为 ModelGatewayReadRepository，配置脱敏、默认模型/Embedding 配置字段、日志 purpose/status/task 过滤和排序契约保持不变 | Codex |
| v1.1.164 | 2026-06-06 | AI 助手会话历史读取 API 的 PostgreSQL 查询实现抽取为 AssistantChatReadRepository，`GET /api/assistant/conversations` 和会话消息查询的用户级隔离、排序和 references 响应契约保持不变 | Codex |
| v1.1.163 | 2026-06-06 | 知识中心读取 API 的 PostgreSQL 查询实现抽取为 KnowledgeReadRepository，`GET /api/knowledge/documents`、沉淀候选、知识搜索和向量可读性检查响应契约保持不变 | Codex |
| v1.1.162 | 2026-06-06 | GitHub/GitLab 代码评审、用户洞察/迭代规划和生命周期上下文 API 的服务化实现完成遗留副本清理，main.py 不再保留对应 provider/校验/快照/read model 旧 helper，外部 API 响应契约保持不变 | Codex |
| v1.1.161 | 2026-06-06 | 生命周期上下文 API 移除对 legacy main 的回调，改由 lifecycle_context service 承接上下游追踪、风险信号、缺失上下文、read model 读取和 lifecycle edge/risk 保存契约 | Codex |
| v1.1.160 | 2026-06-06 | GitLab MR 与 GitHub PR 预览/列表/快照 API 移除对 legacy main 的回调，改由 git_review service 承接 provider 读取、diff 风险摘要、快照限制校验、审计和 DB-first 保存契约 | Codex |
| v1.1.159 | 2026-06-06 | 用户洞察与迭代规划 API 移除对 legacy main 的回调，使用指标、用户反馈、迭代建议和建议决策改由 user_insights service 承接列表读取、校验、审计和 DB-first 保存契约 | Codex |
| v1.1.158 | 2026-06-06 | DevOps 指标明细 API 移除对 legacy main 的回调，GitLab/Jenkins/线上日志明细读写改由 operational_records service 承接列表读取、校验、审计和 DB-first 保存契约 | Codex |
| v1.1.157 | 2026-06-06 | 采集运行和待归属 API 移除对 legacy main 的回调，改由 operational_records service 承接列表读取、创建/更新/解决状态机、审计和 DB-first 保存契约 | Codex |
| v1.1.156 | 2026-06-06 | AI 任务创建 API 移除对 legacy main 的回调，`POST /api/ai-tasks` 改由 ai_tasks service 承接各任务类型前置校验、上下文补充、需求状态推进、审计和 DB-first 保存契约 | Codex |
| v1.1.155 | 2026-06-06 | AI 任务批量重试 API 移除对 legacy main 的回调，改由 ai_tasks service 承接可重试失败任务恢复、仍失败明细、skipped 明细、批次审计和 DB-first 保存契约 | Codex |
| v1.1.154 | 2026-06-06 | Review 决策 API 移除对 legacy main 的回调，`approve/edit-approve/reject/request-more-info` 改由 ai_tasks service 承接状态校验、任务状态推进、Graph checkpoint、知识沉淀/Bug/Code Review 报告保存和审计契约 | Codex |
| v1.1.153 | 2026-06-06 | AI 任务启动 API 移除对 legacy main 的回调，`POST /api/ai-tasks/{task_id}/start` 直接调用 ai_tasks service，启动、失败重试、模型日志、Human Review、Graph Run/Checkpoint、Code Review 报告和 DB-first 保存响应契约保持不变 | Codex |
| v1.1.152 | 2026-06-06 | AI 任务启动 API 的核心业务逻辑下沉到 ai_tasks service，保持状态校验、失败任务重试、模型失败日志、Human Review、Graph Run/Checkpoint、Code Review 报告和 DB-first 保存响应契约不变；main.py 暂保留薄委托 | Codex |
| v1.1.151 | 2026-06-06 | AI 任务启动依赖的模型网关任务调用 helper 下沉到 model_gateway service，保持模型调用、失败日志、重试失败注入和 token/latency 元数据契约不变，为 start_ai_task API 后续移除 legacy main 回调做准备 | Codex |
| v1.1.150 | 2026-06-06 | AI 任务批量取消 API 移除对 legacy main 的回调，改由 ai_tasks service 承接重复/不存在/终态 skipped 明细、逐任务取消、pending Review 取消、Graph Run 取消 checkpoint、逐任务审计、批次审计和 DB-first 保存契约 | Codex |
| v1.1.149 | 2026-06-06 | AI 任务取消和补充信息提交 API 移除对 legacy main 的回调，改由 ai_tasks service 承接任务工作流写上下文、Graph Run 取消 checkpoint、pending Review 取消、more_info_answers 追加、审计事件和 DB-first 任务状态保存契约 | Codex |
| v1.1.148 | 2026-06-06 | Graph Run 列表、待确认 Review 列表和 Review 详情 API 移除对 legacy main 的回调，改由 ai_tasks service 承接任务工作流只读上下文、pending Review SQL 摘要读取和任务读权限过滤契约 | Codex |
| v1.1.147 | 2026-06-06 | AI 任务详情 API 移除对 legacy main 的回调，改由 ai_tasks service 承接任务工作流只读上下文、详情投影、Review/Graph Run/知识沉淀/Mock Issue 聚合和读权限校验契约 | Codex |
| v1.1.146 | 2026-06-06 | 批量推进需求状态 API 移除对 legacy main 的回调，改由 requirements service 承接目标状态校验、版本归属保护、状态机 skipped 明细、DB-first 保存和批次审计契约；requirements router 已整体不再回调 legacy main | Codex |
| v1.1.145 | 2026-06-06 | 批量排期需求 API 移除对 legacy main 的回调，改由 requirements service 承接产品/版本校验、可排期状态校验、skipped 明细、DB-first 保存和批次审计契约 | Codex |
| v1.1.144 | 2026-06-06 | 批量分配需求负责人 API 移除对 legacy main 的回调，改由 requirements service 承接负责人校验、skipped 明细、逐需求更新、DB-first 保存和批次审计契约 | Codex |
| v1.1.143 | 2026-06-06 | 批量需求生成产品详细设计任务 API 移除对 legacy main 的回调，改由 requirements service 承接批量校验、skipped 明细、逐任务创建、DB-first 保存和批次审计契约 | Codex |
| v1.1.142 | 2026-06-06 | 单条需求生成产品详细设计任务 API 移除对 legacy main 的回调，改由 requirements service 承接需求 planned 校验、AI task 创建、DB-first 同事务保存和审计契约 | Codex |
| v1.1.141 | 2026-06-06 | 需求审批、驳回和关闭 API 移除对 legacy main 的回调，改由 requirements service 承接状态机、活跃任务保护、DB-first 保存和审计契约 | Codex |
| v1.1.140 | 2026-06-06 | 需求修改和删除 API 移除对 legacy main 的回调，改由 requirements service 承接状态校验、上下文校验、DB-first 保存/删除和审计契约 | Codex |
| v1.1.139 | 2026-06-06 | 需求创建 API 移除对 legacy main 的回调，改由 requirements service 承接写权限、上下文校验、DB-first 保存和审计契约 | Codex |
| v1.1.138 | 2026-06-06 | 需求详情和需求全链路 API 移除对 legacy main 的回调，改由 requirements service 承接详情读取、链路实体聚合和时间线响应契约 | Codex |
| v1.1.137 | 2026-06-06 | 研发运营统一列表 API 移除对 legacy main 的回调，改由 devops_metrics service 承接 SQL read model 查询、fallback 拼装和 query/performance 观测契约 | Codex |
| v1.1.136 | 2026-06-06 | 用户洞察统一列表 API 移除对 legacy main 的回调，改由 user_insights service 承接 SQL read model 查询、fallback 拼装和 query/performance 观测契约 | Codex |
| v1.1.135 | 2026-06-06 | AI 任务列表 API 移除对 legacy main 的回调，改由 ai_tasks service 承接 SQL read model 查询、权限范围、时间过滤和 query/performance 观测契约 | Codex |
| v1.1.134 | 2026-06-06 | 需求列表 API 移除对 legacy main 的回调，改由 requirements service 承接 SQL read model 查询、兼容 fallback 和 query/performance 观测契约 | Codex |
| v1.1.133 | 2026-06-06 | Bug 列表 API 移除对 legacy main 的回调，改由 bugs service 承接 SQL read model 查询、兼容 fallback 和 query/performance 观测契约 | Codex |
| v1.1.132 | 2026-06-06 | Bug 创建、批量更新、修改和删除 API 移除对 legacy main 的回调，改由 bugs router 调用 bugs service 保持状态机、DB-first 写入和审计契约 | Codex |
| v1.1.131 | 2026-06-06 | 知识文档更新、重建索引和删除 API 移除对 legacy main 的回调，改由 knowledge router 调用 service 保持索引状态、沉淀解除关联和 DB-first 审计契约 | Codex |
| v1.1.130 | 2026-06-06 | 知识文档创建 API 移除对 legacy main 的回调，改由 knowledge router 调用 knowledge service 保持参数校验、索引、模型日志和 DB-first 审计契约 | Codex |
| v1.1.129 | 2026-06-06 | 知识沉淀采纳/驳回 API 移除对 legacy main 的回调，改由 knowledge router 调用 knowledge_deposits service 保持状态校验、索引和 DB-first 审计契约 | Codex |
| v1.1.128 | 2026-06-06 | 知识搜索 API 移除对 legacy main 的回调，改由 knowledge router 调用 knowledge_search service 保持权限过滤、关键词兜底和向量兼容排序契约 | Codex |
| v1.1.127 | 2026-06-06 | 知识沉淀候选列表 API 移除对 legacy main 的回调，改由 knowledge router 调用 knowledge_deposits service 保持 repository-first 读取和状态过滤契约 | Codex |
| v1.1.126 | 2026-06-06 | 知识文档列表 API 移除对 legacy main 的回调，改由 knowledge router 调用 knowledge_documents service 保持 repository-first 读取、排序分页和性能观测契约 | Codex |
| v1.1.125 | 2026-06-06 | 模拟 Issue 写回 API 移除对 legacy main 的回调，改由 writeback router 调用 mock_writeback service 保持完成态校验、幂等写入和 DB-first 审计契约 | Codex |
| v1.1.124 | 2026-06-06 | 审计事件列表 API 移除对 legacy main 的回调，改由 audit router 调用 audit_events service 保持过滤、排序、分页和性能观测契约 | Codex |
| v1.1.123 | 2026-06-06 | 代码评审报告读取 API 移除对 legacy main 的回调，改由 code_review_reports router 调用 code_review_report service | Codex |
| v1.1.122 | 2026-06-06 | Markdown 导出 API 移除对 legacy main 的回调，改由 export router 调用任务工作流上下文和 markdown_export service | Codex |
| v1.1.121 | 2026-06-06 | 需求批量推进状态补充版本归属校验，进入交付链路状态前未排期需求返回 `REQUIREMENT_VERSION_REQUIRED` skipped 明细 | Codex |
| v1.1.120 | 2026-06-05 | 新增 `POST /api/requirements/batch-advance-status`，支持需求管理按研发流程批量推进状态并返回 updated/skipped 明细 | Codex |
| v1.1.119 | 2026-06-05 | 新增 `POST /api/requirements/batch-assign-owner`，支持需求管理批量分配负责人并返回 updated/skipped 明细 | Codex |
| v1.1.118 | 2026-06-05 | 新增 `POST /api/ai-tasks/batch-retry`，支持任务管理批量重试模型网关和代码评审执行器失败任务并返回 retried/updated/skipped 明细 | Codex |
| v1.1.117 | 2026-06-05 | AI 助手聊天响应和历史消息新增 `references`，服务端按 read context 生成可跳转来源链接并持久化到消息 metadata | Codex |
| v1.1.116 | 2026-06-05 | 新增 `POST /api/ai-tasks/batch-cancel`，支持任务管理多选批量取消并返回 updated/skipped 明细 | Codex |
| v1.1.115 | 2026-06-05 | 核心管理列表 `performance` 元数据新增 `p95_target_ms`，并按 requirements/ai_tasks/bugs/user_insights/devops_operational_metrics 返回列表级 P95 目标 | Codex |
| v1.1.114 | 2026-06-05 | 研发运营统一列表 SQL read model 查询迁移到独立 DevopsReadRepository，`GET /api/devops/operational-metrics` 分页、筛选、排序和查询观测契约保持不变 | Codex |
| v1.1.113 | 2026-06-05 | 用户洞察统一列表 SQL read model 查询迁移到独立 UserInsightReadRepository，`GET /api/insights/items` 分页、筛选、排序和查询观测契约保持不变 | Codex |
| v1.1.112 | 2026-06-05 | Bug 管理 SQL read model 查询迁移到独立 BugReadRepository，`GET /api/bugs` 分页、筛选、排序和版本展示响应契约保持不变 | Codex |
| v1.1.111 | 2026-06-05 | AI 任务 SQL read model 查询迁移到独立 TaskReadRepository，`GET /api/ai-tasks` 分页、筛选、排序、读权限范围和待 Review 摘要契约保持不变 | Codex |
| v1.1.110 | 2026-06-05 | 需求管理 SQL read model 查询迁移到独立 RequirementReadRepository，`GET /api/requirements` 分页、筛选、排序和响应契约保持不变 | Codex |
| v1.1.109 | 2026-06-05 | 产品与迭代版本 SQL read model 查询迁移到独立 ProductConfigReadRepository，API 查询契约保持不变 | Codex |
| v1.1.108 | 2026-06-05 | 采集运行、待归属处理和生命周期上下文 API 收口到独立 collectors、attribution、lifecycle router，并保留采集审计、归属决策和上下游风险上下文查询契约 | Codex |
| v1.1.107 | 2026-06-05 | Markdown 导出 API 收口到独立 export router，并保留完成任务导出、权限校验、X-Trace-Id 和 text/markdown 响应契约 | Codex |
| v1.1.106 | 2026-06-05 | 写回结果、代码评审报告和审计事件 API 收口到独立 writeback、code_review_reports、audit router，并保留模拟 Issue 幂等写入、报告读取和审计列表查询契约 | Codex |
| v1.1.105 | 2026-06-05 | 用户洞察与迭代建议 API 收口到独立 user_insights router，并保留用户洞察统一列表查询观测契约 | Codex |
| v1.1.104 | 2026-06-05 | 研发运营指标 API 收口到独立 devops_metrics router，并保留运营统一列表查询观测契约 | Codex |
| v1.1.103 | 2026-06-05 | 知识中心 API 收口到独立 knowledge router，并补充端点单一路由归属契约 | Codex |
| v1.1.102 | 2026-06-05 | 首页 IT 团队看板补充短 TTL 缓存、强制刷新参数、缓存元数据和慢查询日志契约 | Codex |
| v1.1.101 | 2026-06-05 | 管理主列表响应元数据补齐列表名和慢查询日志约束，发布就绪门禁支持真实浏览器页面 smoke | Codex |
| v1.0.0 | 2026-05-27 | 基于设计文档生成项目级 API 文档 | Claude |
| v1.0.1 | 2026-05-27 | 对齐当前 FastAPI 实现，补充产品配置和平台配置接口 | Codex |
| v1.0.2 | 2026-05-28 | 补充主体生命周期、需求任务快照、知识索引状态和主体级审计查询约定 | Claude |
| v1.0.3 | 2026-05-29 | 补充 GitLab、线上日志、Jenkins、首页看板和 Bug 管理 API 约定 | Claude |
| v1.0.4 | 2026-05-29 | 补充研发全链路 AI 任务类型和 task_type 契约 | Claude |
| v1.0.5 | 2026-05-29 | 补充软件研发全流程感知 API 约定 | Claude |
| v1.0.6 | 2026-05-29 | 补充用户洞察、用户反馈和 AI 迭代规划建议 API 约定 | Claude |
| v1.0.7 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 纳入 v1 MVP，补充 MR 预览、diff 快照、Review 报告查询和不回写 GitLab 的错误语义 | Claude |
| v1.1.0 | 2026-05-29 | 对齐 PRD v1.1.0 和 Spec v1.1.0，补充 MVP 角色映射，修正内部 GitLab Git 资源示例和阶段边界 | Claude |
| v1.1.1 | 2026-05-29 | 修复产品评审问题：将 GitLab 预览和 diff 快照前置到 MVP-A，清理 MVP 角色口径，统一 health trace_id、占位接口和阶段边界 | Claude |
| v1.1.2 | 2026-05-30 | 将 Bug 管理 GET/POST/PATCH 从占位升级为 v1.1 基础接口，补充状态流转、重复归并和审计约束 | Codex |
| v1.1.3 | 2026-05-30 | 对齐当前实现的 PostgreSQL 登录用户表、用户管理接口和 SQL 迁移驱动持久化 | Codex |
| v1.1.4 | 2026-05-30 | 补齐当前管理主体 CRUD 契约，新增产品子资源、需求、知识文档、Bug 和用户删除/更新接口说明 | Codex |
| v1.1.5 | 2026-05-31 | 对齐真实删除语义、主数据唯一性校验和需求审批/任务确认前端主链路接口使用 | Codex |
| v1.1.6 | 2026-05-31 | 补齐审计事件按操作者和创建时间范围过滤，并对齐审计列表详情与链路追踪操作 | Codex |
| v1.1.7 | 2026-05-31 | 对齐 MVP-B code_review 执行器失败错误语义，结构化报告生成失败返回专用错误码和审计事件 | Codex |
| v1.1.8 | 2026-05-31 | 补齐 GitLab MR diff 超限失败审计，记录实际大小、限制和关联上下文 | Codex |
| v1.1.9 | 2026-05-31 | 补齐 GitLab MR 变更文件数限制，超限时拒绝快照并记录审计指标 | Codex |
| v1.1.10 | 2026-05-31 | 补齐 GitLab MR 单文件 diff 行数限制，超限时拒绝快照并记录文件指标 | Codex |
| v1.1.11 | 2026-05-31 | 明确 MVP 用户角色目录、角色查询接口、用户管理角色选择和 SQL 角色字典 | Codex |
| v1.1.12 | 2026-05-31 | 将产品、版本、模块和 Git 资源同步到 PostgreSQL 结构表，推进业务主体细粒度持久化 | Codex |
| v1.1.13 | 2026-05-31 | 将需求台账同步到 PostgreSQL `requirements` 结构表，支持从结构表恢复需求和计数器 | Codex |
| v1.1.14 | 2026-05-31 | 将 AI 任务核心字段同步到 PostgreSQL `ai_tasks` 结构表，支持从结构表恢复任务和计数器 | Codex |
| v1.1.15 | 2026-05-31 | 将人工确认、Graph Run 和检查点同步到 PostgreSQL 结构表，支持任务启动后的流程状态恢复 | Codex |
| v1.1.16 | 2026-05-31 | 细化角色目录响应字段，补充职责、数据范围、决策范围和前端固定角色选择约束 | Codex |
| v1.1.17 | 2026-05-31 | 将知识文档、知识沉淀候选和审计事件同步到 PostgreSQL 结构表，减少快照兜底范围 | Codex |
| v1.1.18 | 2026-05-31 | 将 Bug 管理记录同步到 PostgreSQL `bugs` 结构表，支持从结构表恢复列表和计数器 | Codex |
| v1.1.19 | 2026-05-31 | 将模型网关配置和调用元数据日志同步到 PostgreSQL 结构表，支持任务启动后恢复默认配置和日志计数器 | Codex |
| v1.1.20 | 2026-05-31 | 明确系统管理角色管理入口，角色目录只读来自 `/api/auth/roles`，用户和知识权限不得录入未定义角色 | Codex |
| v1.1.21 | 2026-05-31 | 将 GitLab MR 快照和 Code Review 报告同步到 PostgreSQL 结构表，支持证据链恢复和任务反链回填 | Codex |
| v1.1.22 | 2026-05-31 | 将模拟 Issue 回写同步到 PostgreSQL `mock_issues` 结构表，支持幂等结果恢复 | Codex |
| v1.1.23 | 2026-05-31 | 将相关系统同步到 PostgreSQL `related_systems` 结构表，纳入产品配置恢复范围 | Codex |
| v1.1.24 | 2026-05-31 | 移除 AI 任务启动本地输出 fallback，无模型网关配置时明确失败，不再生成伪输出 | Codex |
| v1.1.25 | 2026-05-31 | 知识检索升级为权限过滤后的 chunk 级结果，并将 `knowledge_chunks` 纳入结构表持久化 | Codex |
| v1.1.26 | 2026-05-31 | 生命周期视图和首页看板聚合按任务读权限过滤，避免聚合接口泄露无权任务或 Review | Codex |
| v1.1.27 | 2026-05-31 | 明确角色业务映射、菜单范围、限制边界，并补充知识索引失败原因与重试接口 | Codex |
| v1.1.28 | 2026-06-01 | 生命周期视图支持从审计主体、Review、Code Review 报告、MR 快照、模拟 Issue 和知识沉淀精准追踪上下文 | Codex |
| v1.1.29 | 2026-06-01 | 知识检索不再为缺失 chunk 的 indexed 文档合成结果，索引不一致时返回真实空结果 | Codex |
| v1.1.30 | 2026-06-01 | GitLab MR diff 快照按 repository_id + snapshot_hash 复用已有快照，并记录复用审计事件 | Codex |
| v1.1.31 | 2026-06-01 | 低层 AI 任务创建同步回写需求任务引用，并拒绝已关闭或未审批需求继续创建任务 | Codex |
| v1.1.32 | 2026-06-01 | 模型网关配置入口拒绝非 OpenAI-compatible provider，避免无效配置延迟到任务启动才失败 | Codex |
| v1.1.33 | 2026-06-01 | 知识索引接入 OpenAI-compatible embeddings，chunk 写入 pgvector embedding，检索按权限过滤后进行向量排序 | Codex |
| v1.1.34 | 2026-06-01 | 将用户反馈从空集合入口升级为真实登记、筛选、状态更新和 PostgreSQL 结构表持久化 | Codex |
| v1.1.35 | 2026-06-01 | 将迭代规划建议升级为基于真实反馈/Bug 证据生成、确认和可选转需求的 PostgreSQL 持久化闭环 | Codex |
| v1.1.36 | 2026-06-01 | 将用户使用指标从空集合入口升级为真实登记、筛选、审计和 PostgreSQL 结构表持久化 | Codex |
| v1.1.37 | 2026-06-01 | 将 GitLab 每日代码指标从空集合入口升级为真实登记、筛选、审计和 PostgreSQL 结构表持久化 | Codex |
| v1.1.38 | 2026-06-01 | 将 Jenkins 发布记录从空集合入口升级为真实登记、筛选、审计和 PostgreSQL 结构表持久化 | Codex |
| v1.1.39 | 2026-06-01 | 将线上运行日志指标从空集合入口升级为真实登记、筛选、审计和 PostgreSQL 结构表持久化 | Codex |
| v1.1.40 | 2026-06-01 | 补齐 development_planning 和 automated_testing 低层任务创建、人工确认门禁和自动化测试 Bug 建议入库契约 | Codex |
| v1.1.41 | 2026-06-01 | 补齐 release_readiness 和 post_release_analysis 低层任务创建、真实上下文快照、人工确认和上线后 Bug 建议入库契约 | Codex |
| v1.1.42 | 2026-06-01 | 明确知识文档可绑定产品归属，首页 IT 团队看板按产品过滤知识文档和审计事件 | Codex |
| v1.1.43 | 2026-06-02 | 对齐 Bug 管理工作台完整生命周期字段，前端登记和编辑复现步骤、证据 JSON、重复归并和只读来源展示 | Codex |
| v1.1.44 | 2026-06-02 | 首页 IT 团队看板扩展 Bug、DevOps、线上日志、用户洞察和迭代规划真实聚合，并约定产品/时间范围下钻上下文 | Codex |
| v1.1.45 | 2026-06-02 | 生命周期上下文扩展真实 Bug、GitLab/Jenkins/线上日志、用户使用、用户反馈和迭代建议证据主体及风险来源契约 | Codex |
| v1.1.46 | 2026-06-02 | 新增采集运行记录 GET/POST/PATCH API、状态约束、审计事件和 `collector_runs` 结构表契约 | Codex |
| v1.1.47 | 2026-06-02 | 新增待归属数据队列查询、登记、归属/忽略 API、状态约束、审计事件和 `pending_attribution_items` 持久化契约 | Codex |
| v1.1.48 | 2026-06-02 | 明确 code_review 任务通过可插拔 `code_review_executor` 边界执行，默认适配 Claude Code `code-review` skill 命令，执行器成功/失败均写入专用审计事件 | Codex |
| v1.1.49 | 2026-06-02 | 明确相关系统可绑定产品归属并进入任务产品上下文，补齐需求详情、关闭和 Graph Run 查询接口清单 | Codex |
| v1.1.50 | 2026-06-02 | AI 任务启动接入真实 LangGraph StateGraph，Graph Run 返回 runtime、node_path 和 checkpoint runtime 元数据 | Codex |
| v1.1.51 | 2026-06-02 | 新增长期记忆 GBrain 状态接口，未配置时返回 `not_configured`，配置后只返回脱敏能力状态 | Codex |
| v1.1.52 | 2026-06-02 | 模型网关配置新增测试检测接口，使用临时 OpenAI-compatible 参数调用 chat/completions 与 embeddings 并返回脱敏结果，不保存密钥或模型日志 | Codex |
| v1.1.53 | 2026-06-02 | 模型网关测试检测新增 `test_target`，支持仅测试 Chat 以兼容 ChatGPT OAuth 类上游，同时保留 Embedding 检测和跳过状态 | Codex |
| v1.1.54 | 2026-06-02 | AI 任务列表新增创建时间范围过滤，并在摘要返回产品名、创建时间和更新时间，支撑任务管理页按所属产品和时间段查询 | Codex |
| v1.1.55 | 2026-06-02 | 所有 PostgreSQL 结构表统一补齐 `created_at` 与 `updated_at` 标准时间字段，并通过 `018_standard_timestamps.sql` 升级既有环境 | Codex |
| v1.1.56 | 2026-06-02 | 产品 Git 资源支持 `github` provider，新增 GitHub PR 预览、PR diff 快照和本地直填凭据解析契约 | Codex |
| v1.1.57 | 2026-06-02 | 新增 AI 助手聊天接口，基于当前 AI Brain 系统上下文和模型网关回答产品、任务、进展和配置问题 | Codex |
| v1.1.58 | 2026-06-03 | 全链路真实用例复跑后补齐产品详情、GitHub PR 列表、持久化模型网关健康检查和模型失败任务重试契约 | Codex |
| v1.1.59 | 2026-06-03 | 全链路 GitHub PR 复跑后补齐 code-review 外部命令缺失时自动使用模型网关适配器、Review payload 和输出规范化的启动契约 | Codex |
| v1.1.60 | 2026-06-03 | AI 助手聊天记录按用户级保存，新增会话列表、会话消息查询 API 与 `assistant_conversations` / `assistant_messages` 结构表 | Codex |
| v1.1.61 | 2026-06-03 | 知识索引支持 `text_indexed` 关键词兜底和 `vector_indexed` 向量增强，检索结果返回 `retrieval_mode` | Codex |
| v1.1.62 | 2026-06-03 | 模型网关拆分 Chat 与 Embedding 能力配置，Embedding 支持禁用、复用 Chat 或单独连接，并按向量来源元数据过滤语义检索 | Codex |
| v1.1.63 | 2026-06-03 | 需求创建允许不指定迭代版本，新增需求交付/迭代版本管理口径，并将需求接口状态更新为需求池、排期和研发交付流程 | Codex |
| v1.1.64 | 2026-06-03 | DB-first 迁移补齐任务运行态/Review/回写/导出 repository 读路径和 Mock Writeback handler 级写入契约 | Codex |
| v1.1.65 | 2026-06-03 | DB-first 迁移补齐知识沉淀候选列表 repository-first 读取和状态过滤契约 | Codex |
| v1.1.66 | 2026-06-03 | DB-first 迁移补齐知识检索 repository-first 候选查询、权限过滤和关键词下推契约 | Codex |
| v1.1.67 | 2026-06-03 | DB-first 迁移补齐知识沉淀审核写接口 repository 当前记录读取契约 | Codex |
| v1.1.68 | 2026-06-03 | DB-first 迁移补齐生命周期上下文 repository source rows 聚合和 handler 级写回契约 | Codex |
| v1.1.69 | 2026-06-03 | DB-first 迁移补齐首页 IT 团队看板 repository source rows 聚合和单条 snapshot 写入契约 | Codex |
| v1.1.70 | 2026-06-03 | DB-first 迁移补齐需求/任务详情、Graph Run、Review、回写、Code Review 报告和 Markdown 导出的 task workflow source rows 读取契约 | Codex |
| v1.1.71 | 2026-06-03 | DB-first 迁移补齐任务启动、取消、补充信息和 Review 决策写路径的 task workflow source rows 请求上下文契约 | Codex |
| v1.1.72 | 2026-06-03 | DB-first 迁移将 PostgreSQL 启动运行层切换为轻量 PostgresRuntimeStore repository 容器 | Codex |
| v1.1.73 | 2026-06-03 | DB-first 迁移补齐产品配置、需求/任务创建和 Bug 写路径在 PostgresRuntimeStore 空启动容器下的 source rows 上下文契约 | Codex |
| v1.1.74 | 2026-06-03 | DB-first 迁移补齐运营采集、用户洞察和迭代规划写路径在 PostgresRuntimeStore 空启动容器下的 source rows 上下文契约 | Codex |
| v1.1.75 | 2026-06-03 | DB-first 迁移补齐模型网关配置和 AI 助手聊天写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文契约 | Codex |
| v1.1.76 | 2026-06-03 | DB-first 迁移补齐知识文档和知识沉淀写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文契约 | Codex |
| v1.1.77 | 2026-06-03 | DB-first 迁移补齐 GitLab/GitHub PR/MR 预览、列表和快照写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文契约 | Codex |
| v1.1.78 | 2026-06-03 | DB-first 迁移移除生产 read snapshot 恢复 fallback，补齐业务大脑只读、知识沉淀驳回和 Mock Writeback 生成的 repository/source rows 契约 | Codex |
| v1.1.79 | 2026-06-03 | DB-first 迁移将生命周期上下文 source rows 从 MemoryStore 投影替换为专用 LifecycleContextReadModel | Codex |
| v1.1.80 | 2026-06-03 | DB-first 迁移明确只读缓存允许边界，并将产品配置、模型网关、助手、需求、任务创建和 Bug 写接口进一步收敛为直接 repository records/payloads | Codex |
| v1.1.81 | 2026-06-04 | 新增需求批量排期接口，支持需求管理批量排期和迭代版本页归集需求入口 | Codex |
| v1.1.82 | 2026-06-04 | 明确需求批量排期可选择未归档 planning 版本，并修正批次审计为追加保存而非覆盖式快照保存 | Codex |
| v1.1.83 | 2026-06-04 | 新增迭代版本状态推进接口，支持影响预览、需求状态同步、阻塞项和直接状态 PATCH 拦截 | Codex |
| v1.1.84 | 2026-06-04 | Bug 列表支持迭代版本过滤并返回版本编码和名称投影 | Codex |
| v1.1.85 | 2026-06-04 | 调整迭代版本推进到测试中时的需求同步规则，已进入交付链路需求统一推进到 testing | Codex |
| v1.1.86 | 2026-06-04 | 明确 Bug 管理登记弹窗目标版本使用同产品未归档版本选项，支持 testing/released 版本缺陷归属 | Codex |
| v1.1.87 | 2026-06-04 | 新增研发运营和用户洞察统一聚合列表接口，前端主列表改为服务端分页、排序和筛选 | Codex |
| v1.1.88 | 2026-06-04 | 新增需求全链路详情接口，一次返回需求、迭代版本、任务、Review、PR/MR 快照、代码评审、Bug、发布和知识沉淀时间线 | Codex |
| v1.1.89 | 2026-06-04 | 新增 Bug 批量处理接口，支持多选批量更新状态、严重级别或处理人并记录批次审计 | Codex |
| v1.1.90 | 2026-06-05 | AI 助手系统上下文新增迭代进度、待确认 Review、Bug 分布、代码评审结论和知识沉淀摘要 | Codex |
| v1.1.91 | 2026-06-05 | GitLab MR / GitHub PR 预览响应新增 diff 文件树、风险摘要和 Review Checklist，用于任务中心创建 Code Review 前确认变更范围 | Codex |
| v1.1.92 | 2026-06-05 | 需求全链路详情中的 PR/MR 快照证据展示复用风险摘要、diff 文件树和 Review Checklist 字段 | Codex |
| v1.1.93 | 2026-06-05 | 新增需求批量生成任务接口，支持同产品已排期需求批量生成产品详细设计任务并记录批次审计 | Codex |
| v1.1.94 | 2026-06-05 | `/api/insights/items` 在 PostgreSQL 运行时改为 SQL read model 聚合查询，并补充用户洞察排序过滤索引 | Codex |
| v1.1.96 | 2026-06-05 | `/api/devops/operational-metrics` 在 PostgreSQL 运行时改为 SQL read model 聚合查询，并补充研发运营排序过滤索引 | Codex |
| v1.1.97 | 2026-06-05 | 明确首页看板允许 PostgreSQL source rows + Python 聚合，管理主列表仍要求服务端分页、排序和筛选 | Codex |
| v1.1.98 | 2026-06-05 | 核心管理主列表响应新增 `query/performance` 观测元数据，发布门禁新增 Web shell 和核心列表检查 | Codex |
| v1.1.99 | 2026-06-05 | `/api/requirements` 与 `/api/bugs` 在 PostgreSQL 运行时改为 SQL read model 查询，筛选、排序和分页由数据库完成 | Codex |
| v1.1.100 | 2026-06-05 | `/api/products` 与 `/api/product-versions` 在 PostgreSQL 运行时改为 SQL read model 查询，筛选、排序和分页由数据库完成 | Codex |

---

## 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.1.230 | 2026-06-11 | 知识导入可靠性收口：worker 数据库租约、目录子树归档、资产幂等 upsert 和 chunk set 索引状态回滚。 |
| v1.1.222 | 2026-06-11 | 知识导入任务新增 run/retry/cancel、重解析、chunk set 预览/激活、父子分块 source 和目录批量整理契约。 |
| v1.1.221 | 2026-06-10 | 知识中心新增知识空间、目录、MinIO/S3 资产上传、导入任务、chunk set 和资产预览契约。 |
| v1.1.97 | 2026-06-05 | 明确首页看板允许 PostgreSQL source rows + Python 聚合，管理主列表仍要求服务端分页、排序和筛选。 |
| v1.1.93 | 2026-06-05 | 新增需求批量生成任务接口，支持同产品已排期需求批量生成产品详细设计任务并记录批次审计。 |
| v1.1.92 | 2026-06-05 | 需求全链路详情中的 PR/MR 快照证据展示复用风险摘要、diff 文件树和 Review Checklist 字段。 |
| v1.1.91 | 2026-06-05 | GitLab MR / GitHub PR 预览新增 diff 文件树、风险摘要和 Review Checklist 字段，任务中心创建 Code Review 前展示变更范围和检查项。 |
| v1.1.63 | 2026-06-03 | 需求创建允许不指定迭代版本，排期后才能生成 AI 任务，接口状态改为需求池和研发交付状态机。 |
| v1.1.57 | 2026-06-02 | 新增 AI 助手聊天接口和 `/api/assistant/chat` 契约，基于脱敏系统上下文回答 AI Brain 系统信息与项目进展问题。 |
| v1.1.56 | 2026-06-02 | 产品 Git 资源支持 GitHub provider，新增 GitHub PR 预览、PR diff 快照和本地直填凭据解析契约。 |
| v1.1.55 | 2026-06-02 | 所有 PostgreSQL 结构表统一补齐 `created_at`/`updated_at`，并新增 `018_standard_timestamps.sql` 作为既有环境迁移脚本。 |
| v1.1.54 | 2026-06-02 | AI 任务列表新增 `created_from`/`created_to` 查询和摘要时间字段，任务管理页可按所属产品与时间段筛选。 |
| v1.1.50 | 2026-06-02 | AI 任务启动接入真实 LangGraph StateGraph，Graph Run 返回 runtime、node_path 和 checkpoint runtime 元数据。 |
| v1.1.49 | 2026-06-02 | 相关系统支持绑定产品归属，产品配置页可维护相关系统，任务产品上下文只纳入同产品启用相关系统；接口清单补齐需求详情、关闭和 Graph Run 查询。 |
| v1.1.47 | 2026-06-02 | 新增待归属数据队列 API、状态约束、审计事件和 `pending_attribution_items` 持久化契约。 |
| v1.1.46 | 2026-06-02 | 新增采集运行记录 API、状态约束、审计事件和 `collector_runs` 持久化契约。 |
| v1.1.43 | 2026-06-02 | Bug 管理工作台对齐完整生命周期字段，支持复现步骤、证据 JSON、重复归并和只读来源展示。 |
| v1.1.42 | 2026-06-01 | 首页 IT 团队看板按产品过滤知识文档和审计事件。 |
| v1.1.41 | 2026-06-01 | 发布评估和上线后分析任务支持从已确认上游任务创建、保存真实上下文快照、人工确认，并将上线后 Bug 建议写入 `ai_post_release` 来源 Bug。 |
| v1.1.39 | 2026-06-01 | 线上运行日志指标接口支持真实登记、筛选、审计和 `online_log_metrics` PostgreSQL 持久化。 |
| v1.1.38 | 2026-06-01 | Jenkins 发布记录接口支持真实登记、筛选、审计和 `jenkins_release_records` PostgreSQL 持久化。 |
| v1.1.37 | 2026-06-01 | GitLab 每日代码指标接口支持真实登记、筛选、审计和 `gitlab_daily_code_metrics` PostgreSQL 持久化。 |
| v1.1.36 | 2026-06-01 | 用户使用指标接口支持真实登记、筛选、审计和 `user_usage_metrics` PostgreSQL 持久化。 |
| v1.1.35 | 2026-06-01 | 迭代规划建议接口支持基于真实反馈/Bug 证据生成、人工确认、可选转需求和 PostgreSQL 持久化。 |
| v1.1.34 | 2026-06-01 | 用户反馈接口支持真实登记、筛选、状态更新和 `user_feedback` PostgreSQL 持久化。 |
| v1.1.29 | 2026-06-01 | 知识检索不再为缺失 chunk 的 indexed 文档合成结果，索引不一致时返回真实空结果。 |
| v1.1.30 | 2026-06-01 | GitLab MR diff 快照按 repository_id + snapshot_hash 复用已有快照，并记录复用审计事件。 |
| v1.1.28 | 2026-06-01 | 生命周期视图支持从审计主体、Review、Code Review 报告、MR 快照、模拟 Issue 和知识沉淀精准追踪上下文。 |
| v1.1.27 | 2026-05-31 | 角色目录补充业务角色、可见入口和限制边界；知识文档索引失败保留 `index_error` 并支持重试。 |
| v1.1.26 | 2026-05-31 | 生命周期视图和首页看板聚合按任务读权限过滤，避免聚合接口泄露无权任务或 Review。 |
| v1.1.25 | 2026-05-31 | 知识检索升级为权限过滤后的 chunk 级结果，并将 `knowledge_chunks` 纳入结构表持久化。 |
| v1.1.24 | 2026-05-31 | 移除 AI 任务启动本地输出 fallback，无模型网关配置时明确失败，不再生成伪输出。 |
| v1.1.23 | 2026-05-31 | 将相关系统同步到 PostgreSQL `related_systems` 结构表，纳入产品配置恢复范围。 |
| v1.1.22 | 2026-05-31 | 将模拟 Issue 回写同步到 PostgreSQL `mock_issues` 结构表，支持幂等结果恢复。 |
| v1.1.21 | 2026-05-31 | 将 GitLab MR 快照和 Code Review 报告同步到 PostgreSQL 结构表，支持证据链恢复和任务反链回填。 |
| v1.1.12 | 2026-05-31 | 将产品、版本、模块和 Git 资源同步到 PostgreSQL 结构表，推进业务主体细粒度持久化。 |
| v1.1.11 | 2026-05-31 | 明确 MVP 用户角色目录、角色查询接口、用户管理角色选择和 SQL 角色字典。 |
| v1.1.3 | 2026-05-30 | 对齐 PostgreSQL 登录用户表、用户管理接口和 SQL 迁移驱动持久化。 |
| v1.1.2 | 2026-05-30 | 将 Bug 管理 GET/POST/PATCH 从占位升级为 v1.1 基础接口。 |
| v1.1.1 | 2026-05-29 | 将 GitLab 预览和 diff 快照前置到 MVP-A，清理 MVP 角色口径，统一 health trace_id、占位接口和阶段边界。 |
| v1.1.0 | 2026-05-29 | 对齐 PRD/Spec v1.1.0，补充 MVP 角色映射，修正内部 GitLab Git 资源示例和阶段边界。 |
| v1.0.7 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 纳入 v1 MVP，补充 MR 预览、diff 快照、Review 报告查询和不回写 GitLab 的错误语义。 |
| v1.0.6 | 2026-05-29 | 补充用户洞察、用户反馈和 AI 迭代规划建议 API 约定。 |
| v1.0.5 | 2026-05-29 | 补充软件研发全流程感知 API 约定。 |
| v1.0.4 | 2026-05-29 | 补充研发全链路 AI 任务类型和 task_type 契约。 |
| v1.0.3 | 2026-05-29 | 补充 GitLab、线上日志、Jenkins、首页看板和 Bug 管理 API 约定。 |
| v1.0.2 | 2026-05-28 | 补充主体生命周期、需求任务快照、知识索引状态和主体级审计查询约定。 |
| v1.0.1 | 2026-05-27 | 对齐当前实现，修正登录字段、任务输入字段、Markdown 导出、审计查询和配置接口。 |
| v1.0.0 | 2026-05-27 | 初始版本 |

---
最后更新: 2026-06-10
