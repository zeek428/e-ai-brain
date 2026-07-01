# 插件、定时作业与执行器

> 来源：../spec.md。本文承接插件管理、定时作业、Runner 和研发执行器策略的业务域规格导航。

## 职责边界

- 插件定义外部系统能力，连接维护 Endpoint、认证、公共参数和后台环境元数据，动作定义请求、变量和结果映射。
- 定时作业负责将插件、AI 能力、知识和结果动作编排为可追踪的运行记录。
- AI 执行器 Runner 负责 Codex、Claude Code、Hermes、OpenClaw 等本机或受控环境执行，不直接暴露业务密钥。
- 研发执行器策略位于需求交付域，只引用插件管理中的 Runner 资源。

## 关键数据

- `plugins`、`plugin_connections`、`plugin_actions`、`plugin_invocation_logs`
- `scheduled_jobs`、`scheduled_job_runs`、`collector_runs`、`result_write_records`
- `ai_executor_runners`、`ai_executor_tasks`、`rd_task_executor_policies`

## 关键 API 与页面

- 插件管理：`/system/plugins`，兼容导航入口 `/tasks/plugins`
- 定时作业：`/tasks/scheduled-jobs`
- 研发执行器策略：`/delivery/rd-executor-policies`
- 定时作业配置注册中心：`GET /api/system/scheduled-job-catalog`
- 关键接口见 [../api.md](../api.md) 的 plugin、scheduled jobs、AI executor runner 和 RD executor policy 章节。

## 当前落地要求

- 插件页主文件只保留插件、连接、动作和 Runner 编排；插件市场、插件、连接、执行器和动作五个页签装配收口到 `PluginManagementTabs`，Runner Token/日志、插件、执行器、连接、动作和动作试运行弹窗组装配收口到 `PluginManagementModals`，插件定义弹窗、插件市场表格、插件表格、连接表格、动作表格、连接新增/编辑弹窗、动作新增/编辑弹窗、连接表单字段、Runner 新增/编辑弹窗、Runner 表单字段、Runner 表格、连接/Runner 诊断展示、连接测试诊断弹窗、Runner 日志、Runner Token 轮换提示/确认和动作试运行弹窗都应保持组件化；插件管理页不再常驻展示系统变量预览或通用调用链路说明，系统变量选项由 `pluginSystemVariableOptions` 统一维护并给连接/动作弹窗复用，变量解析结果通过连接测试诊断查看；任务编排链路说明应放在定时作业配置或运行详情语境中。动作新增/编辑弹窗应以连接为主要选择项，隐藏插件字段并由连接或场景模板推导 `plugin_id`；连接环境属于后台元数据，不作为插件管理连接弹窗、列表筛选、列表列或动作连接下拉的主展示字段；连接/动作/Runner 表单 payload、请求预览、结果映射、schema 回填和助手草案回填统一由 `pluginFormTransformHelpers` 维护，不得继续散落在页面主文件。
- 定时作业页主文件只保留作业配置、运行列表和详情编排；作业配置与运行记录页签装配收口到 `ScheduledJobManagementTabs`，新增/编辑作业弹窗外壳、模板来源提示、作业模板选择、编排预览和表单分区装配收口到 `ScheduledJobFormModal`，表单分区使用 `ScheduledJobFormSection`，基础信息字段收口到 `ScheduledJobBasicInfoSection`，执行链路预览收口到 `ScheduledJobOrchestrationFlow`，数据连接选择收口到 `ScheduledJobDataConnectionSection`，代码巡检作业的代码仓库配置收口到 `ScheduledJobCodeRepositorySection`，AI 模型、AI角色、Skills 和知识引用字段收口到 `ScheduledJobAiExecutionSection`，写入策略和代码巡检结果动作编辑器收口到 `ScheduledJobActionConfigSection`，调度方式、Cron 表达式和固定间隔字段收口到 `ScheduledJobScheduleConfigSection`，试运行结果与 JSON 预览收口到 `ScheduledJobDryRunResultPanel` 和 `ScheduledJobJsonPreview`，作业配置表格收口到 `ScheduledJobConfigTable`，运行记录和运行观测概览收口到 `ScheduledJobRunTable`，运行详情弹窗收口到 `ScheduledJobRunDetailModal`，运行详情的结果写入记录收口到 `ScheduledJobRunResultWriteRecords`；Catalog 派生出的选项映射、必填校验、默认结果动作和结果动作标签格式化统一由 `useScheduledJobCatalogOptions` 维护；模板 payload 解析、助手草案回填、配置归一化和路由参数解析统一由 `scheduledJobFormTransformHelpers` 维护，不得继续散落在页面主文件。
- 作业类型、必填资源规则、执行/调度枚举、连接环境和代码巡检扫描/规则/结果动作选项由服务端 `ScheduledJobCatalog` 输出，新增/编辑弹窗、运行草案和测试 mock 必须优先消费 `GET /api/system/scheduled-job-catalog`；`scheduledJobFormTransformHelpers` 内的静态选项仅作为接口不可用时的降级，不作为扩展任务类型的权威来源。
- 定时作业配置和运行记录列表是管理型列表，分页、排序和筛选必须优先走 PostgreSQL read model；`GET /api/system/scheduled-jobs` 传入 `page/page_size` 时按名称、关键字、产品、来源、类型、启停、状态过滤并返回 `query/performance` 观测信息；`GET /api/system/scheduled-job-runs` 传入 `page/page_size` 时按运行 ID、作业 ID、状态和产品 scope 过滤，并支持开始/完成时间、状态、触发方式和导入数排序；MemoryStore 全量读取只允许作为旧客户端、助手按 runId 拉详情和测试 helper 兼容。
- 定时作业运行观测同样属于产品范围受控读接口；`GET /api/system/scheduled-job-runs/observability` 允许 `system.scheduled_jobs.manage` 或 `system.scheduled_jobs.run` 访问，但健康汇总、状态/作业类型/触发/写入目标分布、失败原因、最近失败和慢运行都必须先按当前用户产品 scope 过滤运行记录，不能因为是聚合指标而绕过产品范围。
- AI 能力配置的 AI角色和 Skill 页签也是管理型配置列表；`GET /api/system/ai-agents` 与 `GET /api/system/ai-skills` 传入 `page/page_size` 时必须优先走 PostgreSQL read model 完成关键字、状态和专项筛选，以及白名单排序，并返回 `query/performance` 观测信息；未带分页的全量返回仅用于定时作业下拉、助手草案回填和测试 helper 兼容。
- 插件连接和动作配置列表也是管理型配置列表；`GET /api/system/plugin-connections` 与 `GET /api/system/plugin-actions` 传入 `page/page_size` 时必须优先走 PostgreSQL read model 完成关键字、插件、状态和后台连接环境筛选，以及白名单排序，并返回 `query/performance` 观测信息；插件管理页面默认不展示连接环境筛选和环境列；未带分页的全量返回仅用于旧插件页下拉、模板回填和测试 helper 兼容。
- 内部数据源连接表单只展示业务源数据、字段模式、时间窗口、通用过滤和按源过滤字段；需求状态/优先级、Bug 状态/严重级别等常用过滤必须以可视化字段维护并写入 `request_config.query.source_filters`，并按已选 `source_types` 联动展示，取消对应源数据后隐藏过滤不得继续提交；高级过滤 JSON 仅作为更细粒度过滤补充，不应把常用过滤引导回手写 JSON。
- 插件调用日志虽不作为插件管理独立页签展示，但仍是定时作业运行、结果写入记录和执行诊断的排障兼容列表；`GET /api/system/plugin-invocation-logs` 传入 `page/page_size` 时必须优先走 PostgreSQL read model 完成 `action_id/scheduled_job_id/scheduled_job_run_id/status` 筛选、白名单排序和 count/page 查询，并返回 `query/performance` 观测信息；分页和未分页兼容路径都必须通过关联 `scheduled_job_id` 或 `scheduled_job_run_id` 解析定时作业产品并按当前用户产品 scope 过滤，避免插件管理权限用户跨产品查看运行日志；未带分页的全量返回仅用于旧下钻、单次排障和测试 helper。
- 结果写入记录虽由定时作业运行和动作调用日志派生，但仍属于产品范围受控排障数据；`GET /api/system/result-write-records` 必须通过 `scheduled_job_id` 或 `scheduled_job_run_id` 解析定时作业产品并按当前用户产品 scope 过滤，scope 外写入记录不返回且不计入 total；带 `page/page_size` 时必须直接从 PostgreSQL 派生 read model 聚合定时作业运行和无运行归属的插件调用日志，完成 count/page、筛选和白名单排序，并返回 `query/performance`，不得先同步全量运行和调用日志到 MemoryStore 后再分页；未带分页时仅作为运行详情、助手诊断、执行诊断和测试 helper 兼容；无产品归属的独立动作调用写入记录仅对全局产品范围用户可见。
- 多数据连接失败策略必须在运行层落地：默认 `failure_policy=fail_fast` 时首个失败连接中断后续连接，但失败运行仍保留数据连接失败节点和 Trace；`failure_policy=continue_on_error` 时失败连接进入 `data_connection.items[]` 与 Trace DAG，后续连接继续执行，成功响应按合并策略进入后续 AI执行或动作。
- 多结果动作失败策略必须在运行层落地：`result_summary.result_action_policy` 记录本次运行采用的动作编排策略；默认 `failure_policy=continue_on_error` 时，单个结果动作映射或写入失败要写入 `execution_nodes.result_actions[]`、Trace DAG 和通用结果写入记录，并继续执行后续动作；配置 `failure_policy=fail_fast` 时保持失败即中断。
- AI 执行器任务列表也是 Runner 运维管理列表；`GET /api/system/ai-executor-tasks` 传入 `page/page_size` 时必须优先走 PostgreSQL read model 完成 `ai_task_id/runner_id/scheduled_job_run_id/status` 筛选、白名单排序和 count/page 查询，并返回 `query/performance` 观测信息；任务状态包含 `queued/claimed/running/succeeded/failed/cancelled/timed_out/dead_letter`，其中 `dead_letter` 表示任务租约多次过期后不再自动重派；任务列表、日志查询、取消和超时扫描必须按当前用户产品 scope 过滤，服务端通过定时作业、运行快照或研发任务解析 Runner 任务产品归属，scope 外任务按 404 处理；未带分页的全量返回仅用于 Runner 日志弹窗、单任务兼容和测试 helper。
- 插件定义、连接、动作、调用日志和 Runner 任务关联属于 DB-first 写路径；标准插件同步、插件新增/复制/编辑/删除、连接新增/编辑/删除/测试、动作新增/编辑/删除、动作调用日志写入不得直接操作 `current_store` 插件集合，MemoryStore 仅作为测试 fallback 并由插件集合 helper 维护，PostgreSQL 运行态通过插件 repository 单记录方法与审计事件提交。
- 定时作业配置、AI Skill/Agent、采集运行和定时作业运行记录同属 DB-first 写路径；作业新增/编辑/删除、运行排队/执行/取消、采集运行创建/完成和作业最近运行状态更新不得直接写 `current_store` 作业集合，MemoryStore 仅作为测试 fallback 并由定时作业集合 helper 维护，PostgreSQL 运行态通过 scheduled job repository 单记录方法与审计事件提交。
- AI 执行器 Runner 服务不得在生产路径直接写 `current_store` 的 Runner、Runner 任务、插件调用日志、定时作业运行、定时作业、采集运行、AI 任务或人审集合；状态同步、日志追加、任务领取、租约刷新、租约过期重派、死信、取消、超时和完成回写必须通过单记录 helper 写入，MemoryStore 只作为测试 fallback，PostgreSQL 运行态通过 repository 单记录方法写库。Runner/任务/插件调用/定时作业/采集运行单记录写入和审计事件必须在同一数据库事务中提交。任务认领时服务端在 `request_config.reliability` 中写入 `lease_started_at/lease_expires_at/lease_timeout_seconds/max_reclaim_count`，Runner 追加日志视为心跳续租；`timeout-scan` 先处理租约过期，未超过 `max_reclaim_count` 时重置为 `queued` 并累加 `reclaim_count`，超过后进入 `dead_letter` 并同步上游失败态。
- Runner 任务取消与人工重试必须纳入真实回归：运行中任务取消后写入 `AI_EXECUTOR_TASK_CANCELLED` 和 warning 日志，重试复制执行上下文生成新的 `queued` 任务并写入 `retry_of_task_id/retry_history` 和 `ai_executor_task.retry_requested` 审计；重试任务必须能被 Runner 再次认领并完成，已成功任务重复重试必须返回 `AI_EXECUTOR_TASK_NOT_RETRYABLE`。
- 研发执行器策略的新增、编辑、删除、策略刷新和按需补齐产品/代码库资源缓存不得直接写 `current_store.rd_task_executor_policies` / `current_store.products` / `current_store.product_git_repositories`；PostgreSQL 运行态通过 rd_task_executor_policy repository 写入策略与审计，MemoryStore 仅作为测试 fallback 并由策略保存/删除和资源缓存 helper 维护。
- 研发执行器策略页属于管理型配置列表，必须复用统一管理列表底座，支持策略名称、任务类型、执行器、产品和状态筛选，以及横向滚动、列设置、刷新和本地筛选视图保存；新增/编辑弹窗仍不得出现 AI角色、Skill 或模型网关字段。
- 定时作业运行详情必须优先展示数据连接、AI 执行、结果动作和 Runner 执行链路，失败运行提供修复草案和复跑对比。
- 插件管理 Runner 执行日志弹窗必须提供任务诊断、Runner 诊断和来源运行诊断入口，分别按 `ai_executor_task`、`ai_executor_runner` 和 `scheduled_job_run` 来源 ID 跳转统一执行诊断中心，便于排查 Runner 未接单、任务失败或来源作业异常。
- AI 执行器 Runner 列表必须展示服务端标准化 `health_alert`，覆盖 `never_connected`、`runner_heartbeat_timeout`、`runner_offline` 和 `runner_disabled` 等原因，直接给出脱敏问题说明和建议动作，避免只能通过测试弹窗排查心跳异常。
- Runner 安装包按操作系统区分，并包含启动、停止、状态查看和卸载说明。
- 连接、动作、Runner 的测试接口只返回脱敏诊断，不泄露 token、API key、完整请求体或完整响应。

## 验收映射

- 详细验收见 [../test-case.md](../test-case.md) 的插件管理、定时作业、Runner 和研发执行器策略用例。
