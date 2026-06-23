# 企业 AI 大脑平台 API 文档

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.381 |
| 适用系统版本 | ≥ v1.0.0 |
| 文档状态 | Approved |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
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

## 概述

本文档定义企业 AI 大脑平台 v1 系列的 API 契约。后续版本直接维护本文档。

API 面向 React 工作台，覆盖认证、业务大脑、AI 助手、产品上下文、研发全链路 AI 任务、GitLab MR / GitHub PR 代码 Review、软件研发全流程感知、人工确认、Bug 管理、知识中心、模型网关配置、GitLab 代码质量、线上运行日志、Jenkins 发布、用户使用洞察、用户反馈、AI 迭代规划建议、首页 IT 团队看板、模拟回写、Markdown 导出和审计查询。

当前源码实现说明：MVP 骨架已实现认证、AI 助手、产品/需求/任务/Review/知识/审计/导出/GitLab MR 与 GitHub PR 只读预览、diff 快照、code_review 报告闭环。AI 助手通过模型网关 Chat 能力回答 AI Brain 系统相关问题，请求会携带脱敏系统上下文摘要，包括产品、迭代版本进度、需求、AI 任务、待确认 Review、最近代码评审结论、Bug 分布、高风险 Bug、知识沉淀、Git 仓库和模型网关配置状态；服务端会先按用户问题生成 `tool_results`，覆盖 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等 read-model 工具结果，并和 `reference_candidates` 一起注入模型请求。聊天响应和历史消息返回 `references` 与 `tool_results`，用于跳转到产品、迭代、需求、任务、Review、Bug、代码评审报告或知识沉淀并解释回答依据。模型日志只记录 `purpose=assistant_chat` 元数据，不保存完整用户消息、系统上下文或助手回答；完整对话内容按当前登录用户写入助手会话与消息结构表，并且历史查询只返回本人会话。产品配置、需求、知识文档、Bug、用户管理、用户反馈和模型网关配置已具备当前管理页所需 CRUD 能力，删除接口会对已被需求、任务或关联资源占用的主体返回 `RESOURCE_IN_USE`；用户使用指标已具备真实登记和查询能力。MVP 明确定义 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 六个可分配角色，`GET /api/auth/roles` 返回角色目录、业务角色映射、职责、数据范围、决策范围、可见入口、限制边界、权限点和排序信息，系统管理下的角色管理页面只读展示该目录，用户管理和知识权限配置只能从该目录选择角色，不得自由创建或录入未定义角色。

产品管理页面可维护产品、模块、Git 资源和产品相关系统；需求交付下的迭代版本页面维护 `product_versions`，用于需求排期和任务版本上下文。`GET /api/product-versions` 支持批量查询版本并返回 `product_code`、`product_name` 投影，`active_only=true` 只返回 active 版本；`GET /api/requirements` 返回需求主体同时带 `product_code`、`product_name`、`version_code`、`version_name` 和 `assignee`；`POST /api/requirements/batch-assign-owner` 支持将非关闭/非取消需求批量分配负责人，并返回 updated/skipped 明细；`POST /api/requirements/batch-schedule` 支持将多条同产品 `approved/planned` 需求批量归集到 `planning` 或 `active` 迭代版本，并返回 updated/skipped 明细；`POST /api/requirements/batch-generate-tasks` 支持将多条同产品 `planned` 需求批量生成产品详细设计任务，并返回 generated/skipped 明细；`GET /api/ai-tasks` 在 PostgreSQL 模式按产品表 SQL join 返回 `product_name`，并支持 `product_id`、`created_from`、`created_to` 等筛选；`POST /api/ai-tasks/batch-cancel` 支持任务管理多选批量取消，逐条校验任务状态并返回 updated/skipped 明细；`POST /api/ai-tasks/batch-retry` 支持任务管理多选批量重试，逐条校验失败步骤并返回 retried/updated/skipped 明细。产品、版本、模块、Git 资源、相关系统、需求台账、AI 任务核心字段、人工确认、Graph Run、检查点、GitLab MR 快照、Code Review 报告、知识文档、知识 chunk、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属数据队列、迭代规划建议/确认、模拟 Issue 回写、模型网关配置、模型调用元数据、AI 助手会话和助手消息会同步写入 PostgreSQL 结构表 `products`、`product_versions`、`product_modules`、`product_git_repositories`、`related_systems`、`requirements`、`ai_tasks`、`human_reviews`、`graph_runs`、`graph_checkpoints`、`gitlab_mr_snapshots`、`code_review_reports`、`knowledge_documents`、`knowledge_chunks`、`knowledge_deposits`、`audit_events`、`bugs`、`gitlab_daily_code_metrics`、`jenkins_release_records`、`online_log_metrics`、`user_feedback`、`user_usage_metrics`、`collector_runs`、`pending_attribution_items`、`iteration_plan_suggestions`、`iteration_plan_decisions`、`mock_issues`、`model_gateway_configs`、`model_gateway_logs`、`assistant_conversations`、`assistant_messages`。所有 PostgreSQL 结构表必须包含 `created_at` 与 `updated_at` 标准时间字段；新增表必须在建表 SQL 中定义这两个字段，既有环境通过 `018_standard_timestamps.sql` 可重复迁移补齐。Git 资源列表只展示凭据是否已配置，不返回凭据引用或 token 明文。

知识文档创建、更新和知识沉淀采纳会同步重建文本 chunk，并在 active/default OpenAI-compatible 模型网关或环境模型网关支持 `/embeddings` 时生成 `knowledge_chunks.embedding`；Embedding 不可用时文档进入 `text_indexed`，保留 `vector_index_error`/兼容 `index_error`，关键词检索继续可用；Embedding 成功时进入 `vector_indexed`，历史 `indexed` 仅作为兼容状态读取；知识文档可选绑定 `product_id` 作为产品归属上下文，首页 IT 团队看板按产品筛选时只统计该产品归属或该产品任务沉淀产生的知识文档；基础文本索引失败才进入 `index_failed`、保留 `index_error` 并清理旧 chunk，`/api/knowledge/documents/{document_id}/retry-index` 可重建失败索引或将 `text_indexed` 补建为向量索引；`/api/knowledge/search` 先按文档和 chunk 权限过滤，再对有 embedding 的 chunk 执行向量排序并返回真实存在的 chunk 内容、`chunk_id`、`chunk_index`、`retrieval_mode`、`score` 和来源引用，没有可读向量 chunk 时不调用 query embedding 并直接走关键词检索，不返回无权限 chunk，也不为缺失 chunk 的 indexed 文档合成整篇文档结果。GitLab MR 预览和快照读取产品 Git 资源的 `remote_url` 或 `GITLAB_BASE_URL`，GitHub PR 列表、预览和快照读取 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`，并通过环境变量、服务端密钥引用或本地直填只读 token 解析凭据；MR/PR 预览响应除基础元信息外，还返回 `changed_files_summary`、`diff_file_tree`、`risk_summary` 和 `review_checklist`，任务中心创建 Code Review 前据此展示变更范围、风险摘要和人工检查项；缺少 provider 地址、仓库路径或凭据时返回明确错误，不生成本地假 MR/PR。

模型网关配置可在系统管理页面维护，列表和响应只返回 `api_key_configured`，不返回明文密钥、前缀或后缀；配置页支持“测试连接”，调用 `/api/system/model-gateway-configs/test` 使用当前表单参数临时检测 provider `/chat/completions` 与 `/embeddings`，并可通过 `test_target=chat` 仅检测 Chat，适配 ChatGPT OAuth 类不提供 Embedding 的上游；测试不保存配置或密钥，不写入 `model_gateway_logs`，响应仅包含脱敏状态、模型、延迟、embedding 维度、跳过状态和错误码。active/default 且已配置密钥的 OpenAI-compatible 配置会在非 code_review 任务启动时调用 provider `/chat/completions`；知识索引先构建文本 chunk，只有补建向量索引和存在可读向量 chunk 的查询排序会调用 provider `/embeddings`，未配置结构化默认模型网关时可使用 `MODEL_GATEWAY_BASE_URL` 与 `MODEL_GATEWAY_API_KEY` 指向的环境模型网关；调用日志只保存脱敏元数据。缺少可用模型网关、配置缺失密钥或 provider 调用失败时，非 code_review 任务进入 `failed` 并返回 `MODEL_GATEWAY_CONFIG_INVALID` 或 `MODEL_GATEWAY_FAILED`。code_review 任务必须通过可插拔 `code_review_executor` 边界生成报告，默认 `CODE_REVIEW_EXECUTOR_TYPE=claude_code_skill`、`CODE_REVIEW_EXECUTOR_NAME=code-review`，由 `CODE_REVIEW_EXECUTOR_COMMAND` 指定外部命令适配器，输入 JSON 走 stdin，输出 JSON 走 stdout；测试或兼容环境可显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 复用模型网关适配器；默认外部命令为空且存在 active/default 或环境模型网关时，启动会自动通过 `model_gateway` 适配器生成报告，prompt 携带 MR/PR 快照、技术方案、需求和产品上下文，并将常见 Review 输出字段规范化为 AI Brain 报告 schema。执行器调用成功写入 `code_review.executor_called`，执行器配置、调用、解析或结构化校验失败进入 `failed`，返回 `CODE_REVIEW_EXECUTOR_FAILED` 并写入 `code_review.executor_failed` 审计事件。任务启动不会静默生成本地输出。

任务中心已通过真实接口支持启动产品详细设计、确认 Review、基于已确认产品详细设计创建技术方案任务、基于已确认技术方案创建 `development_planning`、`automated_testing` 和 `release_readiness` 任务，基于已确认发布评估创建 `post_release_analysis` 任务，并对已完成技术方案导出 Markdown。需求创建允许 `version_id` 为空，审批后进入 `approved` 需求池；排入 `planning` 或 `active` 迭代版本后进入 `planned`，才能生成产品详细设计任务。AI 任务启动会通过真实 LangGraph `StateGraph` 运行当前 MVP 路径 `retrieve_context -> generate_task_output -> interrupt_for_human_review`，Graph Run 响应和结构表会保留 `runtime=langgraph`、`node_path` 以及 checkpoint `graph_runtime` 元数据。`automated_testing` 输出经人工确认后，可将 `bug_suggestions` 写入 `bugs`，来源为 `ai_auto_test`；`post_release_analysis` 输出经人工确认后，可将 `bug_suggestions` 写入 `bugs`，来源为 `ai_post_release`，两者均关联产品、版本、需求和 AI 任务。GitLab 每日代码指标可通过 `/api/devops/gitlab/daily-code-metrics` 登记和筛选真实产品仓库维度指标，Jenkins 发布记录可通过 `/api/devops/jenkins/releases` 登记和筛选真实产品版本维度发布记录，线上运行日志指标可通过 `/api/ops/online-log-metrics` 登记和筛选真实产品/模块/环境/时间窗口聚合指标；采集运行记录和待归属数据队列 API 保留为历史兼容能力，当前前端不再提供入口；用户反馈可通过 `/api/insights/user-feedback` 登记、筛选和更新状态，用户使用指标可通过 `/api/insights/usage-metrics` 登记和筛选真实聚合指标；写操作均记录审计。审计与运行页面从真实 `/api/audit/events` 加载列表，行操作提供事件详情和基于审计主体优先的生命周期链路追踪；审计列表在 repository 可用时优先读取 SQL/repository，actor、event_type、ai_task、subject 和时间范围过滤在查询层执行。生命周期上下文已支持从 `bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback` 和 `iteration_plan_suggestion` 起点回溯同产品/版本/模块任务链路，并对未关闭严重 Bug、GitLab 风险、Jenkins 失败、线上高错误率、负面反馈和低置信度迭代建议返回来源明确的风险信号。首页 IT 团队看板已聚合真实产品、需求、AI 任务、待确认 Review、知识文档、知识沉淀、审计、Bug、GitLab 指标、Jenkins 发布、线上日志、用户使用、用户反馈和迭代规划摘要；传入 `product_id` 时，所有可归属主体必须按产品归属过滤，不展示其他产品的数据；传入 `time_range` 时，运营类指标按可解析的日期或时间窗口过滤；看板属于汇总型视图，允许基于 PostgreSQL source rows 由 Python 做跨主体聚合和展示计算。PostgreSQL 运行时看板响应带短 TTL 缓存元数据 `metadata.dashboard_cache`，默认 TTL 由 `DASHBOARD_CACHE_TTL_SECONDS` 控制，`refresh=true` 可强制绕过缓存并重建快照；接口耗时超过 `DASHBOARD_SLOW_THRESHOLD_MS` 时记录 `slow_dashboard_query` 日志。看板下钻到 Bug、研发运营、用户洞察和审计页面时保留产品和时间范围上下文。Docker 本地栈默认以 `PERSISTENCE_MODE=postgres` 运行，登录账号读取 PostgreSQL `users` 表，管理员可通过系统管理下的用户管理维护用户，并通过角色管理查看固定角色定义；`PERSISTENCE_MODE` 未设置时默认 `postgres`，非测试环境显式配置 `memory` 会启动失败；测试环境可继续用 MemoryStore helper 运行纯业务/接口单测。当前生产数据访问仍处于 DB-first 迁移期，`/health` 返回 `data_access_mode=db_first_migration`；PostgreSQL 启动使用轻量 `PostgresRuntimeStore` repository 容器，不再通过 `PersistentMemoryStore.from_repository(...)` 启动恢复业务集合；生产读路径不再通过 repository read snapshot 反灌 `PersistentMemoryStore`，缺少已声明的 repository/source rows 能力时只能使用测试 helper 或显式迁移后的查询路径；业务大脑列表和详情已在 PostgreSQL 运行时读取 `brain_apps` repository payload。产品配置写接口已在 handler 返回前把产品、版本、模块、Git 资源、相关系统和对应审计事件写入 repository，不依赖请求结束 `PersistentMemoryStore.persist()`；产品配置核心 GET 接口已在 repository 可用时优先读取 SQL/repository，包括产品列表/详情、指定产品的版本、模块、Git 资源和关联系统，并通过运行态 store 过期测试验证不依赖进程内集合；需求创建、修改、审批、驳回、关闭和删除也已在 handler 返回前写入需求记录及审计事件；从需求生成产品详细设计 AI 任务和后续任务创建已在同一 repository 事务中写入需求 `task_ids`/状态、AI task 和 `ai_task.created` 审计事件；需求列表、需求详情、AI 任务详情、Graph Run 列表、待确认 Review、Review 详情、模拟回写结果、Code Review 报告和 Markdown 导出在 PostgreSQL 运行时会优先读取 task workflow repository source rows；任务启动成功路径已写入 AI task、模型调用日志、Human Review、Graph Run、Checkpoint 和启动审计事件；任务启动失败路径已写入 failed task、可选模型失败日志、`ai_task.retry_started` 和失败审计事件；Review approve/edit-approve/reject/request-more-info 主路径已写入完成态或中断态 task/review/graph/checkpoint、需求状态、知识沉淀候选、可选 Bug/Code Review 报告和审计事件；cancel/submit-more-info 已写入 AI task、待确认 Review、Graph Run/Checkpoint 和审计事件；Mock Writeback 生成接口已在 handler 返回前写入 `mock_issues` 与 `mock_issue.written` 审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 task workflow source rows 恢复已完成任务和已有幂等回写结果；知识文档创建/更新/索引重试/删除、知识 chunk 重建、知识沉淀采纳/拒绝和对应审计事件已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 knowledge source rows 恢复产品、知识文档、chunk、沉淀和模型网关上下文，同步索引期间可选模型日志；AI 助手聊天成功路径已在 handler 返回前写入会话、用户消息、助手消息、模型日志和审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 assistant source rows 恢复当前用户会话、消息、产品任务摘要和模型网关上下文；模型调用失败路径写入失败模型日志和审计事件；GitHub PR 列表、GitLab MR / GitHub PR 预览审计以及快照成功、复用和失败审计已在 handler 返回前写入 repository，Code Review 报告生成/确认已随任务启动和 Review 决策事务写入；Bug 创建、修改和删除已在 handler 返回前写入 `bugs` 与对应审计事件，删除前会清空指向被删 Bug 的重复归并引用；采集运行创建/更新、待归属队列创建/处理、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标创建已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品、仓库、版本、模块、采集运行和待归属当前记录；用户使用指标创建、用户反馈创建/处理、迭代建议生成和迭代建议决策已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 insight source rows 校验产品、版本、模块、反馈、Bug 和迭代建议当前记录；用户使用指标、用户反馈和迭代建议列表已在 repository 可用时优先读取 SQL/repository，产品、模块、功能、用户群体、时间范围、状态、创建人和规划周期等过滤在查询层执行；迭代建议转需求时会在同一 repository 调用内写入新需求、建议、决策和完整审计事件；模型网关配置创建、修改、删除和连接测试审计已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 model gateway source rows 恢复当前配置和调用日志上下文；生命周期上下文查询生成的 edges/risks 和首页看板生成的 dashboard snapshot 已在 handler 返回前写入 repository，且这两个读接口在 PostgreSQL 运行时会读取 repository source rows；生命周期上下文 source rows 使用专用 `LifecycleContextReadModel` 承载，不再实例化 `MemoryStore` 作为聚合中间层；请求结束全局 `persist()` 已从 API middleware 移除，任何 API 请求都不再通过请求结束同步进程内 store；`app_state_snapshots` 仅作为历史迁移表保留，不再作为生产恢复源或写入目标；管理主列表必须优先在 SQL/repository/read model 层完成分页、排序和筛选，汇总型视图可基于 PostgreSQL source rows 聚合但不得作为写入事实源。外部 DevOps 自动采集器和用户行为自动采集器尚未接入；线上日志可手工登记或导入真实聚合指标，无记录时返回真实空集合，不提供占位状态或伪造统计数据；迭代规划建议已支持基于真实反馈与 Bug 证据的生成、确认和可选转需求。日志监控页面当前只展示和登记 GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标。

当前补充实现：`POST /api/planning/iteration-suggestions` 已基于库内真实 `user_feedback` 与 `bugs` 证据生成迭代建议；无证据时返回真实空集合，不生成占位建议。`POST /api/planning/iteration-suggestions/{suggestion_id}/decide` 支持产品负责人、研发负责人或管理员确认采纳、修改后采纳或驳回；只有 `accepted` / `edited_accepted` 且 `convert_to_requirement=true` 时才创建真实 `requirements` 记录。建议与确认分别写入 `iteration_plan_suggestions` 和 `iteration_plan_decisions`，并记录 `iteration_suggestion.generated` / `iteration_suggestion.decided` 审计事件。

DB-first 迁移补充：`app_state_snapshots` 仅作为历史迁移表保留，当前 PostgreSQL 运行时启动恢复只读取结构表，不再从 app_state JSONB 快照恢复业务集合；手动 `PersistentMemoryStore.persist()` 也不再写入 app_state JSONB 快照。

需求列表 DB-first 补充：`GET /api/requirements` 属于管理主列表，PostgreSQL 运行时必须通过需求台账 SQL read model 完成 `priority/product/product_id/source/status/title/version/version_id` 筛选、`created_at/id/priority/product_code/product_name/source/status/title/updated_at/version_code/version_name` 排序和 `page/page_size` 分页；不得为列表页先加载 task workflow source rows 再由接口层本地过滤或切片。需求详情、需求全链路、任务运行态、Review、回写和导出仍可读取 task workflow source rows 聚合上下文。

Bug 列表 DB-first 补充：`GET /api/bugs` 属于管理主列表，PostgreSQL 运行时必须通过 Bug SQL read model 完成 `module/product_id/severity/source/status/title/version/version_id` 筛选、`assignee/created_at/id/module_code/severity/source/status/title/updated_at/version_code/version_name` 排序和 `page/page_size` 分页；不得为列表页先加载全部 Bug 记录再由接口层本地过滤、排序或切片。

产品和迭代版本列表 DB-first 补充：`GET /api/products` 属于管理主列表，PostgreSQL 运行时必须通过产品 SQL read model 完成 `active_only/code/name/owner_team/status` 筛选、当前版本与模块数投影、列表排序和 `page/page_size` 分页；`GET /api/product-versions` 必须通过迭代版本 SQL read model 完成 `active_only/code/name/product/product_id/status` 筛选、所属产品投影、列表排序和分页。产品详情、产品上下文下拉和单产品版本/模块/Git 资源配置接口仍可使用对应轻量 repository 查询。

用户使用指标当前支持通过 `POST /api/insights/usage-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/insights/usage-metrics` 按产品、模块、功能、用户群体和时间范围筛选；记录写入 `user_usage_metrics`，并记录 `usage_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

GitLab 每日代码指标当前支持通过 `POST /api/devops/gitlab/daily-code-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/devops/gitlab/daily-code-metrics` 按产品、仓库和日期筛选；记录写入 `gitlab_daily_code_metrics`，并记录 `gitlab_daily_code_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

Jenkins 发布记录当前支持通过 `POST /api/devops/jenkins/releases` 手工登记或导入真实发布记录，通过 `GET /api/devops/jenkins/releases` 按产品、版本、状态和环境筛选；记录写入 `jenkins_release_records`，并记录 `jenkins_release.created` 审计事件。无记录时返回真实空集合，不生成兜底数据。

线上运行日志指标当前支持通过 `POST /api/ops/online-log-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/ops/online-log-metrics` 按产品、模块、环境和时间窗口筛选；记录写入 `online_log_metrics`，并记录 `online_log_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

生命周期视图和首页 IT 团队看板的 AI 任务、待确认 Review、知识沉淀和风险信号聚合必须先按任务类型读权限过滤，不能通过聚合接口绕过任务详情权限。

`/api/lifecycle/context` 当前支持的真实起点主体包括 `product`、`requirement`、`ai_task`、`human_review`、`code_review_report`、`gitlab_mr_snapshot`、`mock_issue`、`knowledge_deposit`、`audit_event`、`bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback` 和 `iteration_plan_suggestion`。审计列表发起链路追踪时，后端必须先把审计主体解析到对应需求、AI 任务或可归属证据链路；不支持的 `subject_type` 返回 `VALIDATION_ERROR`，不得退化为全量任务或伪造关系。

## 认证方式

- 方式: 本地账号登录 + Bearer Token。
- Header: `Authorization: Bearer <token>`。
- 除 `/health` 和 `/api/auth/login` 外，所有 `/api/*` 接口都需要 Bearer Token。

### 获取 Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"<redacted>"}'
```

## 公共约定

### 成功响应

大多数 JSON API 返回 envelope：

```json
{
  "data": {},
  "trace_id": "trace_001"
}
```

例外：

- `GET /health` 直接返回健康状态 JSON，并在响应体中包含 `trace_id`；它不使用 `{data, trace_id}` envelope。
- `GET /api/export/tasks/{task_id}/markdown` 返回 `text/markdown` 纯文本，并通过响应 Header 或日志关联 `trace_id`。

### 错误响应

业务错误返回 FastAPI `detail`，并在响应体中保留 `trace_id` 便于排查：

```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "message": "需求必须选择有效产品；生成 AI 任务前必须排入有效迭代版本",
    "trace_id": "trace_001"
  }
}
```

未改造完成的框架级异常也必须在响应 Header 或日志中关联同一 `trace_id`。

### 分页参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| page | int | 1 | 页码。当前主要用于任务列表。 |
| page_size | int | 10 | 每页数量，最大 100。 |

### 角色要求

| 能力 | 最低角色 |
|------|----------|
| 查询健康检查 | 无需登录 |
| 登录 | 无需登录 |
| 读取业务/任务/知识/产品配置 | viewer |
| 创建需求、补充信息、取消自己创建或参与的任务 | product_owner 或 rd_owner；creator policy 由实现按产品归属和参与关系收敛 |
| 审批需求、确认产品详细设计、采纳迭代规划建议 | product_owner |
| 创建和启动 AI 任务、确认技术方案 | rd_owner |
| 创建 GitLab MR / GitHub PR 预览和 diff 快照、创建 code_review 任务、确认 Review 报告 | reviewer 或 rd_owner |
| 审核知识沉淀 | knowledge_owner 或 rd_owner |
| 登记、分派、验证或关闭 Bug | 当前实现为 product_owner、rd_owner 或 admin；RBAC 目标态由 tester/test_owner 按产品、版本或模块范围承接 |
| 维护产品、相关系统、模型网关配置、用户账号 | admin |

MVP 系统角色以 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 为主；当前实现中 Bug 登记和状态更新先复用 `product_owner`、`rd_owner`、`admin`。RBAC 目标态会新增 `developer`、`test_owner`、`tester`、`release_owner` 等研发交付扩展预置角色，其中测试人员负责授权范围内的人工测试 Bug 登记和修复验证，测试负责人负责自动化测试确认和质量门禁。接口鉴权还需要结合产品归属、任务参与关系和主体权限。

| 角色 code | 中文名称 | 主要职责 | 数据范围 | 决策范围 |
|-----------|----------|----------|----------|----------|
| `admin` | 系统管理员 | 用户、角色、模型网关、审计与系统级配置管理 | 全平台系统配置、审计事件和授权业务数据 | 账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍 |
| `product_owner` | 产品负责人 | 产品配置、版本模块、需求审批、任务生成、产品侧交付闭环和 Bug 管理 | 所负责产品、版本和模块下的需求、AI 任务、Bug、知识引用和看板摘要 | 需求审批、产品详细设计确认、迭代规划采纳和产品侧优先级决策 |
| `rd_owner` | 研发负责人 | 研发任务启动、技术方案确认、Code Review 任务创建、Bug 处理和研发知识沉淀 | 授权产品下的 AI 任务、技术方案、GitLab/GitHub 只读快照、Bug 和研发知识 | 技术方案确认、研发任务推进、Bug 处理和研发知识沉淀决策 |
| `reviewer` | 评审负责人 | 高影响 AI 输出、需求分析、设计方案和 GitLab MR / GitHub PR Code Review 的人工确认 | 分配给评审人的 AI 任务、Review 检查点、MR/PR 只读快照和评审报告 | 对高影响 AI 输出执行批准、修改后批准、拒绝或要求补充信息 |
| `knowledge_owner` | 知识负责人 | 知识文档导入、权限角色维护、知识检索治理和知识沉淀审核 | 知识文档、chunk、检索结果、权限角色和知识沉淀候选 | 知识导入、权限配置、索引治理和沉淀候选审核 |
| `viewer` | 查看者 | 查看有权限访问的工作台数据、任务结果、知识和看板摘要 | 授权范围内的列表、详情、任务结果、知识检索结果和看板摘要 | 无写入或审批决策权限 |

### 主体级 API 约定

产品、需求、AI 任务、Bug、知识中心、研发运营指标/看板和用户洞察（含迭代规划建议）是独立业务主体或独立运营视图。API 设计应遵循以下约定：

- 产品接口维护长期主数据，仅 `planning` 和 `active` 版本可用于新需求排期；`testing`、`released` 和 `archived` 不得用于新需求或新开发任务。
- 需求接口维护业务事实和审批状态，生成任务时必须把需求快照写入任务输入。
- AI 任务接口维护任务类型、执行状态、人工确认、回写、导出和运行结果，不承担产品主数据维护。
- GitLab MR / GitHub PR 代码 Review 接口只读取授权变更元信息和 diff 快照，生成 AI Brain 内部 Review 报告，不提供远端评论、审批、request changes、合并或分支变更回写能力。
- 知识接口支持独立导入、索引状态查询、权限过滤检索、索引失败重试和沉淀审核。
- Bug 接口支持 AI 自动测试和人工测试两类来源的登记、分派、修复、验证、关闭和重复归并。
- DevOps/运营接口按产品归属暴露 GitLab 每日代码质量、Jenkins 发布、线上运行日志、用户使用、用户反馈、迭代规划建议和首页 IT 团队看板指标；首页看板中的任务、待确认 Review 和知识沉淀聚合必须先按任务读权限过滤。
- 全流程感知接口按产品、版本、模块、需求、AI 任务或任一主体查询上下文关系、上下游影响和风险信号；返回下游任务、Review、报告、沉淀和风险信号前必须先按任务读权限过滤。
- 审计接口支持按 `ai_task_id`、`subject_type`、`subject_id`、`event_type`、`actor_id` 和创建时间范围过滤。
- 迭代规划建议接口只生成建议和采纳记录，不能绕过产品负责人确认自动创建正式需求或调整迭代排期。

---

## 接口清单

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Health | GET | `/health` | 健康检查。 |
| Long Memory | GET | `/api/long-memory/status` | 查询 GBrain 长期记忆连接器配置状态和可用能力。 |
| Auth | POST | `/api/auth/login` | 登录。 |
| Auth | GET | `/api/auth/me` | 当前用户。 |
| Auth | POST | `/api/auth/logout` | 前端退出登录辅助接口。 |
| Auth | GET | `/api/auth/roles` | 查询 MVP 可分配用户角色目录。 |
| User | GET | `/api/users` | 管理员查询用户列表。 |
| User | POST | `/api/users` | 管理员创建用户。 |
| User | PATCH | `/api/users/{user_id}` | 管理员更新用户姓名、角色、状态或密码。 |
| User | DELETE | `/api/users/{user_id}` | 管理员删除非当前登录用户；PostgreSQL 模式下从用户表移除该账号。 |
| User Authorization | GET | `/api/users/{user_id}/permissions` | 查询用户有效角色、权限点、菜单和数据范围。 |
| User Authorization | PUT | `/api/users/{user_id}/roles` | 系统管理员维护用户角色授权。 |
| User Authorization | PUT | `/api/users/{user_id}/scopes` | 系统管理员维护用户直接数据范围授权。 |
| System RBAC | GET | `/api/system/permissions` | 查询权限点目录。 |
| System RBAC | GET | `/api/system/menus` | 查询菜单资源目录。 |
| System RBAC | POST | `/api/system/menus` | 创建非系统菜单资源。 |
| System RBAC | PUT | `/api/system/menus/reorder` | 批量更新菜单排序。 |
| System RBAC | PATCH | `/api/system/menus/{menu_code}` | 更新菜单名称、父级、路由、图标、状态和访问权限点。 |
| System RBAC | DELETE | `/api/system/menus/{menu_code}` | 删除非系统且无子菜单的菜单资源。 |
| System RBAC | POST | `/api/system/menus/{menu_code}/disable` | 停用菜单资源。 |
| System RBAC | POST | `/api/system/menus/{menu_code}/enable` | 启用菜单资源。 |
| System RBAC | GET | `/api/system/roles` | 查询系统角色列表。 |
| System RBAC | POST | `/api/system/roles` | 创建非系统角色。 |
| System RBAC | POST | `/api/system/roles/{role_id}/copy` | 从现有角色复制角色、权限、菜单和范围。 |
| System RBAC | GET | `/api/system/roles/{role_id}` | 查询角色详情。 |
| System RBAC | PATCH | `/api/system/roles/{role_id}` | 更新角色基础信息。 |
| System RBAC | POST | `/api/system/roles/{role_id}/disable` | 停用非系统角色；系统角色返回 `SYSTEM_ROLE_PROTECTED`。 |
| System RBAC | POST | `/api/system/roles/{role_id}/enable` | 启用角色。 |
| System RBAC | PUT | `/api/system/roles/{role_id}/permissions` | 替换角色权限点授权。 |
| System RBAC | PUT | `/api/system/roles/{role_id}/menus` | 替换角色菜单授权。 |
| System RBAC | PUT | `/api/system/roles/{role_id}/scopes` | 替换角色数据范围授权。 |
| Brain App | GET | `/api/brain-apps` | 业务大脑列表。 |
| Brain App | GET | `/api/brain-apps/{brain_app_id}` | 业务大脑详情。 |
| Product | GET | `/api/products` | 产品列表。 |
| Product | GET | `/api/products/{product_id}` | 产品详情。 |
| Product | POST | `/api/products` | 创建产品。 |
| Product | PATCH | `/api/products/{product_id}` | 更新产品。 |
| Product | DELETE | `/api/products/{product_id}` | 删除未被需求、AI 任务或 Bug 占用的产品；无业务依赖时级联清理该产品的版本、模块和 Git 资源配置。 |
| Product Version | GET | `/api/products/{product_id}/versions` | 产品迭代版本列表，前端主入口位于需求交付/迭代版本。 |
| Product Version | POST | `/api/products/{product_id}/versions` | 创建产品迭代版本。 |
| Product Version | PATCH | `/api/product-versions/{version_id}` | 更新产品迭代版本非状态字段；状态变更必须走推进接口。 |
| Product Version | POST | `/api/product-versions/{version_id}/advance-status` | 预览或推进迭代版本状态，并同步符合条件的需求状态。 |
| Product Version | DELETE | `/api/product-versions/{version_id}` | 删除未被需求、AI 任务或 Bug 占用的产品迭代版本。 |
| Product Version Branch | GET | `/api/product-versions/{version_id}/branch-configs` | 查询指定迭代版本的代码分支配置。 |
| Product Version Branch | POST | `/api/product-versions/{version_id}/branch-configs` | 为指定迭代版本新增代码分支配置。 |
| Product Version Branch | PATCH | `/api/product-version-branch-configs/{branch_config_id}` | 更新版本代码分支的基准分支、开发分支、状态、来源或说明。 |
| Product Version Branch | DELETE | `/api/product-version-branch-configs/{branch_config_id}` | 删除版本代码分支配置。 |
| Product Module | GET | `/api/products/{product_id}/modules` | 产品模块列表。 |
| Product Module | POST | `/api/products/{product_id}/modules` | 创建产品模块。 |
| Product Module | PATCH | `/api/product-modules/{module_id}` | 更新产品模块。 |
| Product Module | DELETE | `/api/product-modules/{module_id}` | 删除未被需求、AI 任务或 Bug 占用的产品模块。 |
| Product Git | GET | `/api/products/{product_id}/git-repositories` | 产品 Git 资源列表。 |
| Product Git | POST | `/api/products/{product_id}/git-repositories` | 创建产品 Git 资源。 |
| Product Git | PATCH | `/api/product-git-repositories/{repo_id}` | 更新产品 Git 资源。 |
| Product Git | DELETE | `/api/product-git-repositories/{repo_id}` | 删除产品 Git 资源配置。 |
| System | GET | `/api/system/related-systems` | 相关系统列表，支持 `active_only` 和 `product_id` 过滤。 |
| System | POST | `/api/system/related-systems` | 创建相关系统。 |
| System | PATCH | `/api/system/related-systems/{system_id}` | 更新相关系统。 |
| System | DELETE | `/api/system/related-systems/{system_id}` | 删除相关系统配置。 |
| System | GET | `/api/system/model-gateway-configs` | 模型网关配置列表。 |
| System | POST | `/api/system/model-gateway-configs/test` | 使用临时参数测试模型网关 Chat 与 Embedding 连通性，不保存配置或密钥。 |
| System | POST | `/api/system/model-gateway-configs` | 创建模型网关配置。 |
| System | PATCH | `/api/system/model-gateway-configs/{config_id}` | 更新模型网关配置。 |
| System | DELETE | `/api/system/model-gateway-configs/{config_id}` | 删除模型网关配置。 |
| System | GET | `/api/model-gateway/logs` | 查询模型调用元数据日志，不返回完整 prompt 或输出。 |
| Assistant | GET | `/api/assistant/conversations` | 查询当前登录用户的 AI 助手会话列表。 |
| Assistant | GET | `/api/assistant/conversations/{conversation_id}/messages` | 查询当前登录用户某个 AI 助手会话的消息记录。 |
| Assistant | POST | `/api/assistant/chat` | AI 助手问答，基于当前 AI Brain 系统上下文和模型网关 Chat 能力回答产品、任务、项目进展和配置问题；确定性意图返回 `message.intent={intent_code,confidence,summary,required_refs}`，工具结果顶层可带 `intent_code/intent_confidence/required_refs`，`summary` 保持业务摘要；请求中的结构化 `references[]` 优先进入上下文，文本 `@...执行一次` 仅在没有结构化作业引用时兜底解析，官方周反馈洞察消歧不得覆盖用户已选择的结构化引用。 |
| Assistant | GET | `/api/assistant/runtime-status` | 查询当前助手运行环境自检状态；响应返回 `ready`、`mode`、模型/Embedding/Redis/GBrain 状态和 `checks[]`，每个检查项包含 `key/status/label/detail/remediation/action_label/action_url/required/severity`。前端默认仅在必需依赖异常时展示轻量提醒和修复入口，增强能力未配置不在对话页展开诊断。 |
| Assistant | GET | `/api/assistant/role-quick-tasks` | 查询当前用户可见的 AI 助手角色快捷任务组，后端优先读取 `assistant_role_quick_tasks` 配置表并按角色、权限、启用状态、企业、模板版本和 `rollout_json` 灰度策略过滤；仅当没有任何配置记录时才回退内置默认目录，前端不得再硬编码角色入口。 |
| Assistant | GET | `/api/assistant/role-quick-task-configs` | 管理员查询全部 AI 助手角色快捷任务配置记录，包含企业、任务组、角色、权限、启停、模板版本、灰度策略和审计元数据。 |
| Assistant | POST | `/api/assistant/role-quick-task-configs` | 管理员新增角色快捷任务配置，写入 `assistant_role_quick_task.created` 审计。 |
| Assistant | PATCH | `/api/assistant/role-quick-task-configs/{config_id}` | 管理员编辑角色快捷任务配置，写入 `assistant_role_quick_task.updated` 审计。 |
| Assistant | POST | `/api/assistant/role-quick-task-configs/{config_id}/status` | 管理员启用/停用任务项或任务组，写入 `assistant_role_quick_task.status_changed` 审计。 |
| Assistant | PUT | `/api/assistant/role-quick-task-configs/{config_id}/rollout` | 管理员调整企业、模板版本和 `rollout_json` 灰度策略，写入 `assistant_role_quick_task.rollout_changed` 审计。 |
| Assistant | GET | `/api/assistant/action-reference-configs` | 具备 `assistant.action_references.manage` 权限的用户查询 `@` 动作候选配置，包含动作 key、标题、别名、角色、权限、启停、排序、企业、模板版本、灰度策略和审计元数据。 |
| Assistant | POST | `/api/assistant/action-reference-configs` | 具备 `assistant.action_references.manage` 权限的用户新增 `assistant_action` 候选配置，写入 `assistant_action_reference_config.created` 审计。 |
| Assistant | PATCH | `/api/assistant/action-reference-configs/{config_id}` | 具备 `assistant.action_references.manage` 权限的用户编辑 `assistant_action` 候选配置，写入 `assistant_action_reference_config.updated` 审计。 |
| Assistant | POST | `/api/assistant/action-reference-configs/{config_id}/status` | 具备 `assistant.action_references.manage` 权限的用户启用或停用 `assistant_action` 候选配置，写入 `assistant_action_reference_config.status_changed` 审计。 |
| Assistant | PUT | `/api/assistant/action-reference-configs/{config_id}/rollout` | 具备 `assistant.action_references.manage` 权限的用户调整企业、模板版本和 `rollout_json` 灰度策略，写入 `assistant_action_reference_config.rollout_changed` 审计。 |
| Assistant | DELETE | `/api/assistant/action-reference-configs/{config_id}` | 具备 `assistant.action_references.manage` 权限的用户删除 `assistant_action` 候选配置，写入 `assistant_action_reference_config.deleted` 审计。 |
| Assistant | GET | `/api/assistant/draft-templates` | 查询当前用户可见的 AI 助手草案模板市场目录；返回周反馈洞察、代码巡检、邮件摘要、发布风险分析、知识库巡检和线上日志异常分析模板的提示、角色、依赖、流程和接入状态。 |
| Assistant | GET | `/api/assistant/reference-candidates` | 按 query/type/product_id 返回当前用户可通过 `@` 使用的候选；覆盖引用类业务对象、可读知识空间/知识目录/知识文档/知识片段、管理员或专项权限可见的定时作业/运行/插件动作/插件连接/AI角色/Skill，以及 `assistant_action` 动作入口；运营类定时作业和运行记录必须再按当前用户产品 scope 过滤，未指定 type 的默认候选按类型均衡合并。 |
| Assistant | POST | `/api/assistant/references/resolve` | 解析并校验显式引用，返回可进入上下文的脱敏引用快照和限量知识上下文。 |
| Assistant | POST | `/api/assistant/action-drafts` | 创建 AI 助手动作草案，支持研发任务、AI Skill、AI角色、定时作业、插件连接、动作配置和分析草案。 |
| Assistant | GET | `/api/assistant/action-drafts` | 查询当前登录用户草案任务台列表，支持 `action/status/validation_status/keyword/created_from/created_to/page/page_size/sort_by/sort_order`，返回草案行、分页元数据和状态/采纳/处理/修改率汇总。 |
| Assistant | GET | `/api/assistant/action-drafts/{draft_id}` | 查询当前用户动作草案详情；`preview.validation.issues[]` 可返回 `repair_action={action,label,field,resource_type,resource_id}`，用于前端展示修正字段、生成前置草案或打开连接测试等操作。 |
| Assistant | PATCH | `/api/assistant/action-drafts/{draft_id}` | 在 pending 草案确认前更新草案 payload，并写入 `modified_fields/user_modified/modified_at/modified_by` 元数据和 `assistant_action_draft.updated` 审计；表单页从助手草案进入后保存必须走该接口再调用 confirm，不得直接绕过服务端草案生命周期创建领域对象。 |
| Assistant | POST | `/api/assistant/action-drafts/{draft_id}/view` | 记录当前用户查看草案详情或深链加载草案，`surface=detail_modal` 写入 `detail_viewed_at`，`surface=deeplink` 写入 `deeplink_viewed_at`，并统一写入 `viewed_at/last_viewed_at/view_count/viewed_by/last_view_surface` 和 `assistant_action_draft.viewed` 审计，用于区分“查看详情”和“深链打开”。 |
| Assistant | POST | `/api/assistant/action-drafts/{draft_id}/confirm` | 确认 pending 草案并调度到对应领域 service；已 confirmed 且存在成功 `assistant_action_run` 的重复提交必须幂等返回同一 run，不得重复创建作业、插件连接或动作。 |
| Assistant | POST | `/api/assistant/action-drafts/{draft_id}/cancel` | 取消 pending 草案，不产生领域写入。 |
| Assistant | POST | `/api/assistant/action-drafts/{draft_id}/modification` | 标记当前用户对草案应用后的字段修改，写入用户修改率指标元数据；仅 pending 草案可写，confirmed/cancelled/expired/failed 返回 `409 DRAFT_NOT_PENDING` 或 `DRAFT_EXPIRED`。 |
| Assistant | GET | `/api/assistant/chat-runs` | 查询当前登录用户的助手聊天运行记录，支持 `status=running,cancelled,failed,succeeded` 和 `limit`，用于刷新后恢复未完成生成、展示最近停止记录和继续打开所属会话。 |
| Assistant | POST | `/api/assistant/chat-runs/{run_id}/cancel` | 取消当前登录用户的助手聊天运行；服务端写入运行与消息取消状态，并尽量中断仍在等待的模型网关请求，已终止或不存在运行返回幂等/明确错误语义。 |
| Assistant | GET | `/api/assistant/metrics` | 查询当前登录用户的 AI 助手效果指标，支持 `window_days/date_from/date_to/product_id/role/action` 过滤；返回草案采纳、运行成功、用户修改、显式引用使用、AI 生成质量、`funnel.stages[]`、`dimensions.products[]/roles[]`、`trends.daily[]/drafts_by_action_daily[]` 和 `instrumentation`。 |
| Assistant | GET | `/api/assistant/metrics/details` | 按 `metric`、`window_days/date_from/date_to/product_id/role/action` 和 `limit` 返回当前用户指标明细列表，支持从草案生成、草案状态、动作运行、聊天运行、定时作业运行、失败修复、引用使用和知识命中钻取到脱敏来源记录。 |
| Assistant | GET | `/api/assistant/metrics/export` | 按同一指标过滤口径导出助手效果指标，`format=csv` 返回 `content/content_type/filename`，`format=json` 返回结构化指标 payload；导出不得包含完整对话正文、知识正文、密钥、Header、完整 Prompt 或外部调用明文。 |
| Requirement | GET | `/api/requirements` | 需求列表。 |
| Requirement | POST | `/api/requirements` | 新增待审批需求。 |
| Requirement | POST | `/api/requirements/batch-assign-owner` | 批量分配需求负责人。 |
| Requirement | POST | `/api/requirements/batch-advance-status` | 按研发流程批量推进需求状态。 |
| Requirement | POST | `/api/requirements/batch-schedule` | 批量归集同产品需求到迭代版本。 |
| Requirement | POST | `/api/requirements/batch-generate-tasks` | 批量为同产品已排期需求生成产品详细设计任务。 |
| Requirement | GET | `/api/requirements/{requirement_id}` | 需求详情。 |
| Requirement | GET | `/api/requirements/{requirement_id}/full-chain` | 需求全链路详情，按时间线聚合需求、迭代版本、AI 任务、Review、PR/MR 快照、代码评审、Bug、发布和知识沉淀；`git_snapshots` 可包含风险摘要、diff 文件树和 Review Checklist。 |
| Requirement | PATCH | `/api/requirements/{requirement_id}` | 更新待审批或已驳回需求。 |
| Requirement | DELETE | `/api/requirements/{requirement_id}` | 删除未生成任务的需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/approve` | 审批通过需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/reject` | 驳回需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/close` | 关闭需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/generate-task` | 需求排期后生成 AI 任务。 |
| AI Task | GET | `/api/ai-tasks` | 任务列表，支持按状态、任务类型、产品、需求、创建时间、关键词、创建人筛选，并返回分页结果。 |
| AI Task | POST | `/api/ai-tasks` | 低层任务创建接口。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/start` | 启动任务；停在 `model_gateway_failed` 或 `code_review_executor_failed` 的失败任务可用同一 task_id 重试。 |
| AI Task | GET | `/api/ai-tasks/{task_id}` | 任务详情；PostgreSQL 运行时读取 task workflow source rows，并返回脱敏产品上下文、输入输出、待确认 Review、Review 列表、Graph Run、知识沉淀和 Mock Issue 回写状态。 |
| AI Task | GET/POST/PATCH/DELETE | `/api/delivery/rd-task-executor-policies`, `/api/delivery/rd-task-executor-policies/{policy_id}` | 管理研发执行器策略；按任务类型、产品和优先级匹配插件管理下的 Codex、Claude Code 或 OpenClaw Runner，不接收 Agent/Skill/模型网关字段。前端任务类型选项覆盖 PRD/原型/产品详细设计（`product_detail_design`）、技术方案设计（`technical_solution`）、代码实现/开发计划（`development_planning`）、代码评审（`code_review`）、自动化测试（`automated_testing`）、代码整改（`code_inspection_remediation`）、发布上线评估（`release_readiness`）和上线后分析（`post_release_analysis`）。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/more-info` | 提交补充信息。 |
| AI Task | POST | `/api/ai-tasks/batch-cancel` | 批量取消任务，逐条校验状态并返回 updated/skipped 明细。 |
| AI Task | POST | `/api/ai-tasks/batch-retry` | 批量重试失败任务，逐条校验 `model_gateway_failed` / `code_review_executor_failed` 并返回 retried/updated/skipped 明细。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/cancel` | 取消任务。 |
| Graph Runtime | GET | `/api/graph-runs` | Graph Run 列表，支持按 `task_id` 查询任务运行态；返回 `runtime`、`node_path`、`checkpoint_id` 和 `state_snapshot.graph_runtime`，并按任务读权限过滤。 |
| Review | GET | `/api/reviews/pending` | 待确认列表；PostgreSQL 运行时优先通过待确认 Review SQL 摘要查询，并按任务读权限范围过滤。 |
| Review | GET | `/api/reviews/{review_id}` | 确认详情；读取 task workflow source rows 并返回关联 AI 任务快照，必须先校验任务读权限。 |
| Review | POST | `/api/reviews/{review_id}/approve` | 原样采纳。 |
| Review | POST | `/api/reviews/{review_id}/edit-approve` | 修改后采纳。 |
| Review | POST | `/api/reviews/{review_id}/reject` | 驳回重跑。 |
| Review | POST | `/api/reviews/{review_id}/request-more-info` | 要求补充信息。 |
| Knowledge | GET | `/api/knowledge/documents` | 知识文档列表。 |
| Knowledge | POST | `/api/knowledge/documents` | 导入知识文档。 |
| Knowledge | GET | `/api/knowledge/spaces` | 查询当前用户可访问的知识空间。 |
| Knowledge | POST | `/api/knowledge/spaces` | 创建知识空间。 |
| Knowledge | PUT | `/api/knowledge/spaces/{space_id}/members` | 维护知识空间成员。 |
| Knowledge | GET | `/api/knowledge/spaces/{space_id}/folders` | 查询知识空间目录。 |
| Knowledge | POST | `/api/knowledge/spaces/{space_id}/folders` | 创建知识空间目录。 |
| Knowledge | PATCH | `/api/knowledge/folders/{folder_id}` | 重命名、移动、排序或归档目录。 |
| Knowledge | POST | `/api/knowledge/documents/upload` | 上传文件到对象存储并创建知识文档、原始资产和 queued 导入任务。 |
| Knowledge | GET | `/api/knowledge/documents/{document_id}/assets` | 按文档查询可访问知识资产。 |
| Knowledge | GET | `/api/knowledge/assets/{asset_id}/preview` | 鉴权后预览知识资产内容。 |
| Knowledge | GET | `/api/knowledge/import-jobs` | 查询可访问知识导入任务，支持按知识空间、文档和状态过滤。 |
| Knowledge | POST | `/api/knowledge/import-jobs/{job_id}/run` | 运行 queued/failed 导入任务，生成解析资产、chunk set 和 chunk。 |
| Knowledge | POST | `/api/knowledge/import-jobs/{job_id}/retry` | 重试 failed/cancelled 导入任务，不重复创建文档。 |
| Knowledge | POST | `/api/knowledge/import-jobs/{job_id}/cancel` | 取消 queued/uploaded/failed 导入任务。 |
| Knowledge | PATCH | `/api/knowledge/documents/{document_id}` | 更新知识文档元数据、内容、权限角色、标签或索引状态。 |
| Knowledge | DELETE | `/api/knowledge/documents/{document_id}` | 删除知识文档。 |
| Knowledge | POST | `/api/knowledge/documents/{document_id}/retry-index` | 重试失败知识文档索引。 |
| Knowledge | GET | `/api/knowledge/documents/{document_id}/chunk-sets` | 查询文档分块版本，支持回滚前检查解析器、策略、状态和 chunk 数。 |
| Knowledge | GET | `/api/knowledge/documents/{document_id}/chunks` | 预览指定 chunk set 的 chunk，返回父子关系和标题层级元数据。 |
| Knowledge | POST | `/api/knowledge/documents/{document_id}/chunk-sets/{chunk_set_id}/activate` | 激活历史 chunk set 并归档其他版本。 |
| Knowledge | POST | `/api/knowledge/documents/{document_id}/reparse` | 基于原始资产创建新的 queued 重解析任务。 |
| Knowledge | POST | `/api/knowledge/documents/batch-move` | 批量移动知识文档目录，返回 updated/skipped 明细。 |
| Knowledge | POST | `/api/knowledge/search` | 知识检索。 |
| Knowledge | GET | `/api/knowledge/deposits` | 知识沉淀候选列表。 |
| Knowledge | POST | `/api/knowledge/deposits/{deposit_id}/approve` | 采纳知识沉淀。 |
| Knowledge | POST | `/api/knowledge/deposits/{deposit_id}/reject` | 驳回知识沉淀。 |
| Output | GET | `/api/writeback/results/{task_id}` | 查询模拟回写结果。 |
| Output | POST | `/api/writeback/results/{task_id}` | 显式生成或复用模拟回写结果，使用幂等键避免重复 Issue。 |
| Output | GET | `/api/export/tasks/{task_id}/markdown` | 导出 Markdown 方案。 |
| Audit | GET | `/api/audit/events` | 查询审计事件。 |
| DevOps | GET | `/api/devops/gitlab/daily-code-metrics` | 查询真实 GitLab 每日提交和代码质量审核结果。 |
| DevOps | POST | `/api/devops/gitlab/daily-code-metrics` | 登记真实 GitLab 每日提交和代码质量审核结果。 |
| DevOps | GET | `/api/devops/operational-metrics` | 查询研发运营统一聚合列表，支持服务端分页、排序和筛选。 |
| Collectors | GET | `/api/collectors/runs` | 查询 DevOps/洞察采集运行记录。 |
| Collectors | POST | `/api/collectors/runs` | 登记一次真实采集或导入运行。 |
| Collectors | PATCH | `/api/collectors/runs/{run_id}` | 更新采集运行状态、导入数量、错误说明或摘要。 |
| AI Capability | GET | `/api/system/ai-skills` | 查询 Skill 配置列表。 |
| AI Capability | POST | `/api/system/ai-skills` | 创建 Skill 配置。 |
| AI Capability | POST | `/api/system/ai-skills/upload` | 上传 zip Skill 文件包，服务端校验后保存本地文件并创建 package 类型 Skill。 |
| AI Capability | PATCH | `/api/system/ai-skills/{skill_id}` | 更新 Skill Prompt、Schema、工具策略或启停状态。 |
| AI Capability | GET | `/api/system/ai-agents` | 查询 AI角色（Agent）配置列表；接口路径和 `agent_id` 字段保持兼容。 |
| AI Capability | POST | `/api/system/ai-agents` | 创建 AI角色（Agent）配置。 |
| AI Capability | PATCH | `/api/system/ai-agents/{agent_id}` | 更新 AI角色（Agent）模型网关、默认 Skill、系统提示词、执行策略或启停状态。 |
| Plugins | GET | `/api/system/plugin-marketplace` | 查询官方插件市场只读目录；返回 GitLab/GitHub/邮箱/AI 执行器标准插件的 `publisher/summary/recommended_scenarios/connection_defaults/connection_template_version/connection_schema/action_templates/installed/plugin_id/connection_count/action_count/template_version/latest_template_version/version_status/upgrade_available`，其中 `connection_defaults` 是可直接带入新增连接表单和 AI 助手连接草案的默认 payload，包含 `auth_type/auth_config/endpoint_url/environment/request_config/status/timeout_seconds/max_retries/name`；`version_status=latest/custom/upgrade_available` 用于前端展示模板状态，官方插件默认 `latest`；`connection_schema.sections[].fields[]` 声明官方插件连接可视化表单字段，包括 `key/label/path/type/required/options/supports_system_variables/description/managed_query_keys`，JSON 仅作为高级修改；MaxCompute 不再作为官方标准插件返回，历史官方 MaxCompute 插件会降级为普通 HTTP 插件，连接编辑只展示通用 Endpoint、认证、Params/Headers 和高级 JSON；GitLab 默认连接提供“GitLab 地址”字段，支持本地自建 GitLab 项目 URL 并自动同步 Endpoint 与项目路径；邮箱默认参数覆盖邮件网关/API endpoint、SMTP/IMAP/POP3 收发主机端口、默认发件人/收件人和 `poll_since` 时间窗口；AI 执行器默认参数覆盖 `model-gateway://default` endpoint、`executor_type=model_gateway`、`runner_id=ai_executor_runner_system_default`、`supported_executor_types=model_gateway/codex/claude/hermes/openclaw`、workspace、超时和结果回写地址，本地 Runner 场景可改选 codex/claude/hermes/openclaw；前端可据此引导新增连接或打开 GitHub/GitLab/邮箱/AI 执行器官方动作模板，并在响应前确保官方插件种子存在。 |
| Plugins | POST | `/api/system/plugins/{plugin_id}/copy` | 将官方标准插件复制为自定义插件；请求可传 `code/name/description/category/protocol/risk_level/status`，不传时默认使用源插件生成副本名称和自定义编码；响应返回普通 `PluginRecord`，包含 `is_system=false/source_plugin_id/source_plugin_code/template_version/version_status=custom`。复制后的插件可编辑删除，源官方插件仍不可修改删除；`code` 必须唯一，冲突返回 409。 |
| Plugins | GET | `/api/system/plugin-action-templates` | 查询官方动作场景模板目录；返回 GitHub 代码巡检、GitLab 代码巡检、邮箱通知发送、邮件收取、AI 执行器下达指令和执行器结果同步等模板，每个模板包含 `code/name/plugin_code/plugin_id/action_type/default_code/default_name/request_config/result_mapping/form_defaults/template_version`。MaxCompute 当前通过普通 HTTP 插件/连接和自定义动作维护，不作为官方动作模板返回。前端新增动作表单必须使用该目录动态生成场景选项，并按模板回填请求配置、Params/Headers、结果写入目标和 JSONPath 映射；AI 助手生成动作草案时必须携带 `template_code/template_version`；若服务端模板缺失，前端和 AI 助手只能提示模板缺失或要求刷新模板目录，不得硬编码生成官方动作兜底。 |
| Plugins | GET | `/api/system/result-write-targets` | 查询结果写入目标注册表；返回 `items[]`，每项包含 `code/label/form_label/description/default_result_mapping/mapping_fields/supported_job_types`。首批目标为 `scheduled_job_result`、`user_feedback_insights`、`code_inspection_reports`、`email_notifications`；前端动作表单必须使用 `form_label` 生成下拉选项，使用 `default_result_mapping` 生成目标切换默认 JSON，使用 `mapping_fields[]` 动态渲染 JSONPath 字段；动作模板、试运行 `write_preview` 和运行详情目标标签应复用同一注册表定义。 |
| Scheduler | GET | `/api/system/result-write-records` | 查询通用结果写入记录读模型；支持 `scheduled_job_run_id`、`scheduled_job_id`、`write_target`、`status`、`plugin_action_id` 查询参数。定时作业运行详情必须使用 `scheduled_job_run_id` 精确查询当前运行的最终写入反馈，避免同一作业多次运行混在一起。响应 `items[]` 由正式定时作业运行 `result_summary.execution_nodes.result_action` 以及未归属定时运行的动作调用日志聚合生成，每条包含 `id/write_target/write_target_label/status/source_type/scheduled_job_id/scheduled_job_name/scheduled_job_run_id/plugin_action_id/plugin_connection_id/plugin_invocation_log_id/records_imported/summary_fields/preview/feedback/created_at/updated_at`。`email_notifications` 的 `summary_fields` 返回 `subject/delivery_status/delivery_id/sample_records` 便于页面直接展示邮件主题、投递状态、消息 ID 和收件人摘要；未知未来写入目标允许按目标 code 查询并保留通用 `preview/feedback` JSON，不要求新增目标专属页面。 |
| Plugins | GET | `/api/system/plugins` | 查询集成插件定义；系统会确保 `gitlab`、`github`、`email`、`ai_executor` 官方标准插件存在并返回 `is_system=true`。 |
| Plugins | POST | `/api/system/plugins` | 创建自定义 HTTP/MCP 插件定义；`category` 必须使用约定枚举 `general/data_warehouse/devops/issue_tracking/observability/knowledge_base/collaboration/ai_service/business_system`，新建插件默认 `is_system=false`。 |
| Plugins | PATCH | `/api/system/plugins/{plugin_id}` | 更新自定义插件名称、分类、协议、风险等级或状态；分类必须使用插件分类枚举，不允许自由文本；官方标准插件返回 `409 PLUGIN_STANDARD_PLUGIN_LOCKED`。 |
| Plugins | DELETE | `/api/system/plugins/{plugin_id}` | 删除未被使用的自定义插件；官方标准插件返回 `409 PLUGIN_STANDARD_PLUGIN_LOCKED`；若存在下级连接、动作、定时作业或调用日志引用，返回 `409 PLUGIN_RESOURCE_IN_USE` 并提示使用清单。 |
| Plugins | GET/POST/PATCH/DELETE | `/api/system/plugin-connections`, `/api/system/plugin-connections/{connection_id}` | 管理插件连接配置；`GET /api/system/plugin-connections` 支持 `environment`、`plugin_id`、`status` 查询参数，`environment` 必须使用约定枚举 `default/dev/test/staging/prod/sandbox`，非法环境返回 `400 VALIDATION_ERROR`；列表响应返回连接最近测试摘要 `last_test_summary` 和最近测试回放记录 `test_history[]`，用于展示最近测试状态、耗时、错误码、失败步骤、远端响应状态码、请求 URL 和变量解析前后差异；连接认证默认按 `none/bearer/api_key_header/basic` 展示 Token、Header 或 Basic 字段并生成 `auth_config`，JSON 仅作为高级修改入口；连接级公共 Params/Headers 默认通过表格维护并生成 `request_config.query/headers`，高级请求 JSON 仅作为精修入口；GitLab 连接通过 `api_key_header`、`PRIVATE-TOKEN` 和“GitLab 地址”维护本地自建 GitLab 项目，地址支持 `http://gitlab.local/acme/ai-brain.git`、`http://192.168.1.10:8080/acme/ai-brain.git` 或 SSH 地址，保存时自动同步 `endpoint_url` 并解析为 `request_config.query.api_version=v4/project_id/project_path/group_id`，不保存临时 `gitlab_project_url`；GitHub 连接通过 Bearer Token、`Accept`、`X-GitHub-Api-Version` 和“仓库地址”维护平台参数，仓库地址支持 `https://github.com/acme/ai-brain.git`、`git@github.com:acme/ai-brain.git` 或 `acme/ai-brain`，保存时自动解析为 `request_config.query.owner/repo`，不保存临时 `repository_url`；GitHub 官方连接提交时 `auth_type` 必须为 `bearer` 且 `auth_config.token_ref` 必填，本地联调可填 GitHub Personal Access Token，生产建议填平台可解析的 `vault/github/token` 或 `env:GITHUB_TOKEN` 引用；邮箱连接通过邮件网关/API endpoint、`Authorization`、`Content-Type=application/json`、`send_protocol/receive_protocol/smtp_host/smtp_port/imap_host/imap_port/pop3_host/pop3_port/mailbox_folder/poll_since/default_from/default_to/subject_template` 维护收取和发送参数，AI 执行器连接通过 `runner_polling` endpoint、`runner_id`、`executor_type`、`workspace_root`、`instruction_timeout_seconds` 和 `result_callback_url` 维护受控 Runner 参数；响应按管理员调试场景明文返回 `auth_config` 和 `request_config`，便于定位三方连接问题；编辑时若提交历史 `***` 占位，服务端仍保留原始密钥值，避免旧页面回填覆盖真实配置；删除连接前必须确认未被动作、定时作业或调用日志引用，否则返回 409。 |
| Plugins | POST | `/api/system/plugin-connections/{connection_id}/test` | 测试插件连接 endpoint 可达性、认证和连接级 Params/Headers 配置，返回 `status/latency_ms/error_message/request_summary/response_summary/diagnostics[]/action_template_draft/repair_suggestions/test_history[]` 等结构化结果并写入审计；测试完成后同时更新连接 `last_test_summary={checked_at,status,latency_ms,error_code,error_message,failed_step,response_status_code,mocked}` 和最近 N 次 `test_history`，每条历史至少保留 `checked_at/status/latency_ms/error_message/request_summary/response_summary/action_template_draft/repair_suggestions`，便于连接列表关闭弹窗后继续排障；`action_template_draft` 使用当次连接、插件和原始请求配置生成 `create_plugin_action` 可用草案，前端可一键复制到新增动作表单；`repair_suggestions[]` 至少包含 `code/title/description`，用于在 HTTP 400、占位 Header、网络失败等场景给出可操作修复建议；`request_summary` 必须包含最终 `url/query/headers/header_sources/masked_placeholder_headers/curl_command/original_request_config/request_config/variable_resolutions/variable_resolution_timezone` 并明文展示实际请求值，前端以请求调试台/请求回放台展示最终请求 URL、Header 来源、原始请求配置、动态变量解析前后差异、可复制 cURL、完整请求 JSON 和远端响应信息；最近测试记录必须可展开查看历史完整请求 JSON、历史远端响应信息、历史修复建议和历史动作模板草案；`variable_resolutions[]` 每项至少包含 `path/expression/token/name/offset_days/resolved_value/resolved_text/status`，用于说明 `{{current_date-7}}` 等系统变量如何变成最终请求参数；无动态变量时前端也展示动态变量解析区块和空状态提示；认证配置生成的同名认证 Header 优先于 Params/Headers 表格值；若最终请求仍包含 `***`，服务端应把它作为用户配置的明文值发出，同时在 `masked_placeholder_headers` 标记，便于判断是否误填；HTTP 400/500 等远端错误需在 `response_summary` 中保留状态码和响应片段。 |
| Plugins | UI | 插件连接保存并测试 | 页面新增/编辑连接弹窗的“保存并测试”不新增后端端点；客户端必须先调用 `POST /api/system/plugin-connections` 或 `PATCH /api/system/plugin-connections/{connection_id}` 保存连接，再使用响应中的 `id` 调用 `POST /api/system/plugin-connections/{connection_id}/test`，并展示连接测试诊断和请求调试台；测试失败不回滚已保存配置。 |
| Plugins | GET | `/api/system/plugin-system-variables` | 查询系统变量预览；支持 `timezone` 参数，返回 `{{current_date}}`、`{{current_date-7}}`、`{{last_full_week.start}}` 等表达式、说明和当前解析值。 |
| Plugins | GET/POST/PATCH/DELETE | `/api/system/plugin-actions`, `/api/system/plugin-actions/{action_id}` | 管理动作，动作可绑定 HTTP 请求、MCP tool 或 Runner 指令；HTTP 请求动作新增和编辑默认通过可视化 Params/Headers 维护 `request_config.query` 与 `request_config.headers`，可在参数值中选择 `{{current_date}}`、`{{current_date-7}}` 等系统变量表达式，JSON 仅作为高级修改入口；页面必须支持可视化表格与 JSON 双向同步，并提供明文请求预览和结果写入目标；`result_mapping.write_target` 的标签、默认映射和可视化字段来自 `/api/system/result-write-targets`，首批支持 `scheduled_job_result`、`user_feedback_insights`、`code_inspection_reports` 与 `email_notifications`；选择 `email_notifications` 时可视化字段包含 `recipients_path`、`subject_path`、`delivery_status_path` 和 `delivery_id_path`；官方场景模板至少包含 GitHub 代码巡检、GitLab 代码巡检、邮箱通知发送、邮件收取、AI 执行器下达指令和执行器结果同步，GitHub/GitLab 模板自动填充官方插件、HTTP 请求路径、默认 Params 和代码巡检报告 JSONPath 映射，邮箱发送模板自动填充官方邮箱插件、`POST /messages/send`、默认邮件 Params/Headers 和邮件通知记录 JSONPath 映射，邮件收取模板自动填充 `/messages/search` 和 `folder/since/subject_keyword` 参数，AI 执行器模板自动填充 `ai_executor.run_instruction` 或 `ai_executor.sync_result` MCP tool，并通过 Runner 队列下发 `codex/claude/hermes/openclaw` 指令；MaxCompute 使用普通 HTTP 插件连接和自定义 HTTP 动作配置，不作为官方动作模板强制出现；真实执行必须接入隔离 Runner，不得在 Web/API 进程中直接执行本机命令；代码巡检作业运行时按 `plugin_output_mapping` 或动作 `result_mapping` 提取仓库、分支、提交、风险、摘要和 finding 列表，JSONPath 支持 `$` 根节点；编辑时若提交历史 `***` 占位，服务端必须保留原始敏感值；删除动作前必须确认未被定时作业或调用日志引用，否则返回 409。 |
| Plugins | POST | `/api/system/plugin-actions/{action_id}/invoke` | 管理员手动调用一次动作并写入调用日志。 |
| Plugins | POST | `/api/system/plugin-actions/{action_id}/trial` | 管理员试运行一次动作；可临时覆盖连接和输入 payload，返回 `request_preview/response_summary/mapping_hits/write_preview/status/latency_ms/error_message`，不作为正式定时作业调用日志；每次试运行写入 `plugin_action.trial_succeeded/failed` 审计事件，payload 只包含插件、动作、连接、连接环境、输入字段名、写入目标、状态、耗时和错误码等轻量上下文；`write_preview` 包含 `write_target/write_target_label/records_imported/candidate_count/sample_records/preview_value/report_preview/source_row_count` 等字段，`email_notifications` 目标还返回 `delivery_id/delivery_status/subject`，用于页面展示结果动作将写入哪里、预计写入多少和样例数据。 |
| Plugins | GET | `/api/system/plugin-invocation-logs` | 查询动作调用日志；该接口供定时作业运行详情、结果记录和运行排障使用，插件管理页面不展示独立调用日志页签。 |
| Plugins | GET/POST/PATCH/DELETE | `/api/system/ai-executor-runners`, `/api/system/ai-executor-runners/{runner_id}` | 管理 AI 执行器。`GET /api/system/ai-executor-runners` 始终返回平台托管的系统默认执行器 `ai_executor_runner_system_default`，字段包含 `protocol=model_gateway`、`endpoint_url=model-gateway://default`、`executor_types=["model_gateway"]`、`health_status=managed`、`token_configured=false` 和无需启动本地 Runner 的 `setup_command`；该记录只读，PATCH、DELETE、rotate-token、heartbeat、claim 均返回 `409 AI_EXECUTOR_SYSTEM_RUNNER_LOCKED` 或不可用错误。管理员创建本地 Runner 时提交 `name/protocol/endpoint_url/executor_types/workspace_roots/heartbeat_timeout_seconds/max_concurrent_tasks/status/metadata/runner_token`，`executor_types` 支持 `codex/claude/hermes/openclaw`，页面标签分别展示为 Codex、Claude Code、Hermes、OpenClaw；`metadata.executor_commands` 保存各执行器本机命令模板，例如 `codex --dangerously-bypass-approvals-and-sandbox`、`claude`、`hermes`、`openclaw`；`metadata.target_os=linux|macos|windows|docker|manual`、`metadata.package_arch=amd64|arm64|universal`、`metadata.install_mode=systemd|shell|launchd|service|powershell|docker|manual` 用于安装包默认生成参数，下载接口显式 query 可覆盖；`protocol` 支持 `runner_polling/runner_websocket/mcp_http/mcp_stdio`。响应不返回 `token_hash`，仅返回 `token_configured`，创建和 rotate-token 时只返回一次性 `runner_token`。列表和详情额外返回 `health_status`、`heartbeat_age_seconds`、`setup_command`、`token_version`、`token_rotated_at`、`latest_task_id` 和 `latest_task_status`，用于页面展示本地 Runner 在线状态、本地启动配置、Token 版本和最近任务状态。删除本地 Runner 前必须确认没有 queued/claimed/running 任务，否则返回 `409 AI_EXECUTOR_RUNNER_IN_USE`。 |
| Plugins | POST | `/api/system/ai-executor-runners/{runner_id}/test` | 管理员测试 AI 执行器健康状态。系统默认执行器返回 `status=succeeded`、`health_status=managed` 和 `system_managed/executor_types` 诊断；本地或远程 Runner 检查注册状态、Token 是否配置、执行器类型、endpoint 和心跳，返回 `diagnostics[]`、`latency_ms`、`checked_at`、脱敏 `runner` 投影和整体 `status=succeeded/failed`。测试只读取配置和健康投影，不下发真实任务，不返回 token/hash，并写入 `ai_executor_runner.tested` 轻量审计事件。 |
| Plugins | GET | `/api/system/ai-executor-runners/{runner_id}/install-package?target_os=&arch=&install_mode=` | 下载 Runner 安装包 ZIP。仅管理员可下载本地 Runner 安装包，系统默认执行器返回锁定错误。`target_os` 支持 `linux/macos/windows/docker/manual`，`arch` 支持 `amd64/arm64/universal`，`install_mode` 按目标系统校验：Linux 支持 `systemd/shell`，macOS 支持 `launchd/shell`，Windows 支持 `service/powershell`，Docker 固定 `docker`，通用手动固定 `manual`；未传时使用 Runner `metadata.target_os/package_arch/install_mode`，不兼容组合回退到该系统默认安装模式。响应 `Content-Type=application/zip`，`Content-Disposition` 使用 `ai-brain-runner-<runner_id>-<target_os>-<arch>-<install_mode>.zip`；包内公共文件包含 `README.md`、`START_STOP.md`、`ai-brain-runner.env`、`manifest.json`、`runner_config.json` 和 `skills/ai-brain-runner/SKILL.md`，其中 `START_STOP.md` 必须按目标系统说明启动、停止、状态查看、重启、禁用自启以及 AI Brain 页面停用不等于关闭本机进程。Linux 包含 `install.sh` 与可选 `systemd/ai-brain-runner.service`；macOS 包含 `install.sh` 与可选 `launchd/com.ai-brain.runner.plist`；Windows 包含 `install.ps1` 与可选 `windows/ai-brain-runner-service.xml`；Docker 包含 `Dockerfile` 和 `docker-compose.runner.yml`；通用手动包包含 `scripts/start-runner.sh` 和 `scripts/start-runner.ps1`。安装包写入 Runner ID、AI Brain 地址、支持的执行器、工作区白名单、命令模板、目标系统、架构和安装模式；由于服务端只保存 token hash，包内 `AI_BRAIN_RUNNER_TOKEN` 必须使用 `<runner_token>` 占位，用户需填入创建或轮换时返回的一次性 token。 |
| Plugins | POST | `/api/system/ai-executor-runners/{runner_id}/rotate-token` | 管理员轮换 Runner token；请求可传 `runner_token`，未传则服务端生成新 token。成功后 `token_version` 递增、`token_rotated_at` 更新，响应只返回本次一次性明文 token，旧 token 立即失效。 |
| Plugins | POST | `/api/system/ai-executor-runners/{runner_id}/heartbeat` | Runner 心跳接口。调用方必须通过 `X-Runner-Token` 或 Bearer Token 提交 Runner token；请求体可带 `metadata`，服务端更新 `last_heartbeat_at/status/metadata` 并返回脱敏 Runner 信息。 |
| Plugins | GET | `/api/system/ai-executor-tasks?ai_task_id=&runner_id=&scheduled_job_run_id=&status=` | 管理员查询 AI 执行器任务列表；支持按研发 AI 任务、Runner、定时作业运行和任务状态过滤，研发任务详情可通过 `ai_task_id` 反查关联 Runner 执行任务。 |
| Plugins | POST | `/api/system/ai-executor-tasks/claim` | Runner 认领任务接口。调用方必须携带 Runner token，并提交 `runner_id` 和可选 `executor_type`；服务端只返回该 Runner 支持且处于 `queued` 的最早任务，任务进入 `claimed`，响应包含 `instruction/workspace_root/input_payload/request_config/timeout_seconds/scheduled_job_run_id/ai_task_id` 等执行上下文。 |
| Plugins | POST | `/api/system/ai-executor-tasks/{task_id}/complete` | Runner 完成回写接口。调用方必须携带 Runner token，并提交 `runner_id/status/result_json/logs/error_code/error_message`；`status` 支持 `running/succeeded/failed/cancelled/timed_out`，完成回写会更新 `ai_executor_tasks`，并同步插件调用日志、定时作业运行的 `runner_execution` 节点、结果动作反馈、collector run 和作业最近运行状态。 |
| Plugins | GET/POST | `/api/system/ai-executor-tasks/{task_id}/logs` | 查询或追加 AI 执行器任务日志。Runner 追加日志时必须携带 Runner token 和 `runner_id`，服务端按时间顺序保留日志行并同步任务 `updated_at`；管理员查询返回 `task_id/status/logs[]`，页面可作为流式日志查看的轮询数据源。 |
| Plugins | POST | `/api/system/ai-executor-tasks/{task_id}/cancel` | 管理员取消 queued/claimed/running 的 AI 执行器任务；响应更新任务状态为 `cancelled`，并同步插件调用日志和关联定时作业运行摘要。 |
| Plugins | POST | `/api/system/ai-executor-tasks/timeout-scan` | 管理员或后台调度触发 AI 执行器任务超时扫描；请求可带 `now` 和 `limit`，服务端把超过 `timeout_seconds` 的 claimed/running 任务熔断为 `timed_out` 并同步关联运行状态。 |
| Scheduler | GET | `/api/system/scheduled-jobs` | 查询定时系统作业定义；响应项返回 `plugin_connection_ids` / `plugin_action_ids` 完整数组，若历史数据只有旧单字段则服务端展开为单元素数组，`plugin_connection_id` / `plugin_action_id` 继续作为第一项兼容字段。 |
| Scheduler | GET | `/api/system/scheduled-job-templates` | 查询官方定时作业模板包；返回每周用户反馈洞察、代码仓库质量/安全/规范巡检、邮件摘要收取、GitLab MR AI 审查、AI 执行器仓库任务等模板的 `code/name/category/description/publisher/recommended_scenarios/payload_defaults/resource_selectors/template_version/available_resource_counts/wizard_steps`。`wizard_steps` 用于前端展示任务创建向导，至少覆盖数据连接、AI 处理、知识引用、结果写入和调度，前端用户侧展示时必须把 AI 处理映射为“AI执行”、把结果写入映射为“动作”。AI 执行器仓库任务模板必须在 `payload_defaults.config_json.ai_executor` 返回 `executor_type=model_gateway`、`runner_id=ai_executor_runner_system_default` 和 `runner_label=系统默认执行器`。前端新增作业模板下拉必须使用该目录渲染，按 `payload_defaults` 回填 cron、AI执行方式、作业类型、动态变量映射、`config_json`、`source_system` 内部来源标识和动作，按 `resource_selectors` 从当前产品、动作、连接、模型、AI角色、Skill 和知识文档中选择默认资源；新增/编辑表单按“基础信息、数据连接配置、AI执行配置、动作配置、调度配置”分区，只展示“调度配置”中的调度方式、Cron 表达式和间隔秒数，`source_system` 不作为用户输入项暴露；作业配置列表主列按“数据连接 / AI执行 / 动作 / 调度”合并展示；AI 助手定时作业草案也必须复用同一目录的默认 payload，避免作业模板散落在页面和助手硬编码中。 |
| Scheduler | POST | `/api/system/scheduled-jobs` | 创建采集、AI 分析、动作调用、迭代建议或看板刷新作业；请求可传 `plugin_connection_ids` / `plugin_action_ids` 表达多个数据连接和动作，服务端去重保序并写入 `config_json.orchestration`。默认 `orchestration.data_connections={mode:sequential,failure_policy:fail_fast,merge_strategy:append_json_arrays}`，默认 `orchestration.result_actions={mode:sequential,failure_policy:continue_on_error}`；旧 `plugin_connection_id` / `plugin_action_id` 自动取数组第一项兼容旧客户端。`code_repository_inspection` 应通过 `config_json.repository_id` 指定产品 Git 仓库，并通过 `config_json.branch` 指定扫描分支；分支为空时服务端按仓库 `default_branch` 补齐，响应返回归一化后的 `config_json.branch`。AI 执行类作业必须显式提交非空 `skill_ids`，服务端不使用 AI角色 `default_skill_ids` 兜底；缺少时返回 `400 AI_SKILL_REQUIRED`。 |
| Scheduler | PATCH | `/api/system/scheduled-jobs/{job_id}` | 更新作业计划、启停、动作、AI 装配、重试和超时策略；支持更新 `plugin_connection_ids` / `plugin_action_ids`，响应与列表均返回完整数组和第一项兼容字段。代码巡检作业更新 `config_json.repository_id/branch` 时必须校验仓库属于同一产品；分支为空时继续按仓库默认分支补齐。 |
| Scheduler | DELETE | `/api/system/scheduled-jobs/{job_id}` | 删除定时作业定义并写入 `scheduled_job.deleted` 审计；当前物理删除遵循数据库外键约束处理关联运行实例，运行历史归档后续通过软删除设计单独演进。 |
| Scheduler | POST | `/api/system/scheduled-jobs/dry-run` | 对尚未保存或正在编辑的作业配置执行全链路试运行预览；请求体与创建作业 payload 一致但不落库，不更新作业最近运行状态。响应返回 `status/job_type/stages`，其中 `stages.data_connection` 展示连接请求与样例数据摘要，`stages.ai_processing` 展示是否会调用模型、AI角色/模型/Skill、Skill 输出 Schema 和动作映射契约校验结果，`stages.result_actions[]` 展示写入目标、写入策略和预计写入数量。若 Skill 输出 Schema 与动作 `result_mapping` 不兼容，必须在 dry-run 阶段返回失败或映射错误，不应进入模型调用。 |
| Scheduler | POST | `/api/system/scheduled-jobs/{job_id}/run` | 触发一次作业运行；请求体可选 `{ "trigger_type": "manual" }`，允许 `manual`、`manual_rerun`、`scheduler`，未传默认 `manual`，运行记录复跑必须传 `manual_rerun`，并可携带 `source_run_id` 记录来源运行；复跑成功响应在来源运行存在时返回 `source_run_summary` 轻量摘要，便于立即打开新详情对比。`code_repository_inspection + config_json.scan_mode=native_full_scan` 默认异步执行，响应先返回同一个 `scheduled_job_run(status=queued, started_at=null, finished_at=null)`，`result_summary.execution_nodes.native_scan.status=queued`；后台 worker 执行后由 `GET /api/system/scheduled-job-runs` 轮询到 succeeded/failed。显式 `config_json.async_execution=false` 时可同步执行，用于测试或小仓库调试。多仓库本地扫描可在 `config_json.repository_ids` 传多个同产品仓库 ID，运行成功返回 `report_ids/report_count/reports_by_repository` 汇总。 |
| Scheduler | GET | `/api/system/scheduled-job-runs` | 查询定时作业运行实例、配置快照、collector run 关联和结果摘要；复跑运行若有 `source_run_id`，响应项返回 `source_run_summary={id,status,trigger_type,records_imported,error_code,started_at,finished_at,latency_ms}`，不复制完整 result_summary；运行摘要优先通过 `result_summary.execution_nodes.data_connection`、`skill_processing`、`result_action` 展示数据连接获取、AI执行处理和动作反馈。`data_connection` 节点必须保留 `request_method/request_url/response_status_code/latency_ms/request_summary/response_summary/records_imported` 等摘要字段，便于页面无需展开完整 JSON 即可看到请求、响应、行数和耗时；当动作通过 AI 执行器下发任务时，响应还必须包含 `runner_execution={executor_type,runner_id,runner_task_id,workspace_root,status,finished_at,logs,result_json,error_code,error_message,model_gateway_called,model_gateway_log_id}`；系统默认执行器使用 `executor_type=model_gateway`、`runner_id=ai_executor_runner_system_default`，直接返回 `result_json`、`model_gateway_called=true` 和 `model_gateway_log_id`，本地 Runner queued/claimed/running 期间运行保持 `status=running`，Runner 完成回写后才更新为终态。`result_action` 节点必须保留写入目标、写入数量、生成记录 ID、业务反馈摘要或 `runner_result`。`result_summary.trace_graph={nodes,edges}` 作为运行 Trace DAG 的标准读模型，节点包含 `id/label/status/duration_ms/retry_count/error/input/output`，用于页面定位每个运行节点的输入、输出、耗时、重试和错误。`code_repository_inspection` 在 `ai_assisted/ai_generated` AI执行方式下必须调用模型网关归一化插件扫描结果，`skill_processing.model_gateway_called=true` 且包含 `model_log_id`，模型输出再进入代码巡检报告写入。 |
| Scheduler | GET | `/api/system/scheduled-job-runs/observability` | 查询定时作业运行健康概览；响应包含 `summary={total_runs,succeeded_runs,failed_runs,running_runs,cancelled_runs,success_rate,failure_rate,average_latency_ms,average_records_imported,model_gateway_called_runs,model_gateway_token_total,plugin_invocation_runs,action_write_runs,action_write_success_runs,action_write_success_rate}`，以及 `status_distribution/job_type_distribution/trigger_type_distribution/write_target_distribution/error_distribution/recent_failures/slow_runs`。Token 汇总仅读取模型日志 `tokens.total` 等元数据；最近失败和慢运行只返回运行 ID、作业 ID/名称、状态、耗时、错误码/错误信息和导入数，不返回完整请求响应、Prompt、模型输出或密钥。 |
| Scheduler | POST | `/api/system/scheduled-job-runs/{run_id}/cancel` | 取消仍处于 queued/running 的运行实例。 |
| Scheduler | POST | `/api/system/scheduled-job-runs/{run_id}/template` | 从一次成功运行反向生成定时作业模板草稿。仅管理员可用，非 succeeded 运行返回 `409 SCHEDULED_JOB_RUN_TEMPLATE_SOURCE_INVALID`；响应包含 `code/name/template_version/wizard_steps/payload_defaults/source_run_id`，其中 `payload_defaults` 来自运行 `config_snapshot` 并写入 `config_json.template_source={source_type: scheduled_job_run, source_id, title}`，前端可直接打开新增作业弹窗供用户确认保存。 |
| Governance | GET | `/api/governance/code-inspections/dashboard` | 查询代码巡检治理概览，支持与列表一致的产品、仓库、提交人、风险级别、状态和标题筛选，并按当前用户产品 scope 过滤；响应返回 `summary`、`trend`、`rule_distribution`、`repository_ranking`、`branch_ranking`、`committer_ranking`、`severity_distribution`、`risk_distribution` 和 `sla`。`trend[]` 按日期返回报告数、问题数、严重问题数、Bug 数以及 `quality_gate_passed_count/failed_count/skipped_count/unknown_count`，用于展示质量门禁趋势、规则维度统计、仓库/分支/提交人排行和严重问题 Bug 覆盖 SLA。 |
| Governance | GET | `/api/governance/code-inspections` | 查询定期代码仓库巡检报告列表，支持产品、仓库、提交人、风险级别、状态、分页和排序，并按当前用户产品 scope 过滤；报告项返回 `scheduled_job_id`、`scheduled_job_run_id`、`plugin_connection_id`、`plugin_action_id` 和 `plugin_invocation_log_id`，用于定位来源作业、运行、连接、动作和插件调用。 |
| Governance | GET | `/api/governance/code-inspections/{report_id}` | 查询单次代码巡检报告详情，返回报告、finding 列表和通知记录；详情报告必须包含来源链路字段，前端在详情弹窗固定展示，并把 `scheduled_job_id`、`scheduled_job_run_id` 渲染为跳转到任务中心 / 定时作业的链接。本地扫描报告还必须返回并展示 `remote_url_summary`、`remote_url_hash`、`artifact_ref`、`checkout_path`、`checkout_path_retained`、`scan_started_at`、`scan_finished_at`、`scanner_version` 和 `rules_version`，用于审计本次扫描实际代码快照。 |
| Attribution | GET | `/api/attribution/pending-items` | 查询待归属数据队列。 |
| Attribution | POST | `/api/attribution/pending-items` | 登记无法映射产品、模块、需求或导入主体的真实数据。 |
| Attribution | POST | `/api/attribution/pending-items/{item_id}/resolve` | 将待归属项归属到已有上下文或忽略为噪声。 |
| GitLab Review | GET | `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview` | 预览内部 GitLab MR 元信息。 |
| GitLab Review | POST | `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot` | 拉取 MR 元信息和 diff，生成 code_review 输入快照。 |
| GitHub Review | GET | `/api/devops/github/pull-requests/{repository_id}` | 列出产品 GitHub 仓库可访问 PR，支持 `state` 和 `limit`。 |
| GitHub Review | GET | `/api/devops/github/pull-requests/{repository_id}/{pr_number}/preview` | 预览 GitHub PR 元信息。 |
| GitHub Review | POST | `/api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot` | 拉取 PR 元信息和 diff 摘要，生成 code_review 输入快照。 |
| Code Review | GET | `/api/ai-tasks/{task_id}/code-review-report` | 查询 GitLab MR / GitHub PR 代码 Review 报告、执行器信息、确认状态和只读回写模板。 |
| DevOps | GET | `/api/devops/jenkins/releases` | 查询 Jenkins 发布记录。 |
| DevOps | POST | `/api/devops/jenkins/releases` | 登记真实 Jenkins 发布记录。 |
| Ops | GET | `/api/ops/online-log-metrics` | 查询线上运行日志运营指标。 |
| Ops | POST | `/api/ops/online-log-metrics` | 登记真实线上运行日志聚合指标。 |
| Bug | GET | `/api/bugs` | 查询 Bug 列表，支持产品、迭代版本、状态、严重程度和来源过滤。 |
| Bug | POST | `/api/bugs` | v1.1 基础接口，登记 AI 自动测试或人工测试 Bug。 |
| Bug | POST | `/api/bugs/batch-update` | 批量更新 Bug 状态、严重级别或处理人，返回 updated/skipped 明细并写入批次审计。 |
| Bug | PATCH | `/api/bugs/{bug_id}` | v1.1 基础接口，更新 Bug 状态、分派人、复现信息或重复归并关系。 |
| Bug | DELETE | `/api/bugs/{bug_id}` | 删除 Bug 记录。 |
| Lifecycle | GET | `/api/lifecycle/context` | 查询软件研发全流程上下文关系、上下游影响和风险信号。 |
| Dashboard | GET | `/api/dashboard/it-team` | 查询首页 IT 团队看板。 |
| Insights | GET | `/api/insights/items` | 查询用户洞察统一聚合列表，支持服务端分页、排序和筛选。 |
| Insights | GET | `/api/insights/usage-metrics` | 查询真实用户使用指标。 |
| Insights | POST | `/api/insights/usage-metrics` | 登记真实用户使用指标。 |
| Insights | GET | `/api/insights/user-feedback` | 查询用户反馈列表。 |
| Insights | POST | `/api/insights/user-feedback` | 登记真实用户反馈。 |
| Insights | PATCH | `/api/insights/user-feedback/{feedback_id}` | 更新用户反馈状态和处理信息。 |
| Insights | POST | `/api/insights/user-feedback/{feedback_id}/convert-requirement` | 将用户反馈转为正式需求，并同步反馈状态为 `linked`。 |
| Planning | GET | `/api/planning/iteration-suggestions` | 查询 AI 迭代规划建议。 |
| Planning | POST | `/api/planning/iteration-suggestions` | 基于真实反馈和 Bug 证据生成 AI 迭代规划建议。 |
| Planning | POST | `/api/planning/iteration-suggestions/{suggestion_id}/decide` | 确认、修改后采纳或驳回迭代规划建议。 |

---

## 核心接口详情

### 管理主列表响应元数据

产品、迭代版本、需求、AI 任务、Bug、研发运营统一列表和用户洞察统一列表等管理主列表在分页响应中返回 `query` 与 `performance` 元数据：

```json
{
  "data": {
    "items": [],
    "page": 1,
    "page_size": 10,
    "total": 0,
    "query": {
      "filters": {
        "status": "testing"
      },
      "name": "requirements",
      "page": 1,
      "page_size": 10,
      "sort_by": "created_at",
      "sort_order": "desc"
    },
    "performance": {
      "duration_ms": 12,
      "p95_target_ms": 300,
      "result_count": 0,
      "slow": false,
      "slow_threshold_ms": 300,
      "total": 0
    }
  },
  "trace_id": "trace_xxx"
}
```

`query.name` 标识列表接口归属，`query.filters` 只回显实际生效的非空筛选条件；`performance.duration_ms` 记录本次接口处理耗时，`result_count` 记录当前页返回条数，`total` 记录筛选后的总数。`performance.p95_target_ms` 是列表级 P95 目标，当前核心目标为 `requirements/ai_tasks/bugs=300ms`、`user_insights=400ms`、`devops_operational_metrics=500ms`；默认 `slow_threshold_ms` 使用该目标值。接口耗时超过 `slow_threshold_ms` 时后端记录 `slow_list_query` 日志并包含 `p95_target_ms`，页面性能排查应优先结合 `trace_id`、`query`、`performance`、`slow_list_query` 和数据库慢查询日志定位。

### 健康检查

```http
GET /health
```

响应：

```json
{
  "status": "ok",
  "postgres": "ok",
  "redis": "ok",
  "model_gateway": "not_configured",
  "long_memory": "not_configured",
  "trace_id": "trace_health_001"
}
```

`status` 在 PostgreSQL 或 Redis 异常时为 `degraded`。`model_gateway` 优先根据持久化 active/default 模型网关配置判断，配置缺失时回退到 `MODEL_GATEWAY_BASE_URL` / `MODEL_GATEWAY_API_KEY` 环境变量。

字段枚举：

| 字段 | 当前取值 |
|------|----------|
| status | `ok` 或 `degraded` |
| postgres | `ok` 或 `error` |
| redis | `ok` 或 `error` |
| model_gateway | `configured` 或 `not_configured` |
| long_memory | `configured` 或 `not_configured` |

### 长期记忆状态

```http
GET /api/long-memory/status
```

响应：

```json
{
  "data": {
    "api_key_configured": false,
    "base_url_configured": false,
    "capabilities": [],
    "connector": "gbrain",
    "fallback_retriever": "postgres_pgvector",
    "status": "not_configured"
  },
  "trace_id": "trace_long_memory_001"
}
```

配置 `GBRAIN_BASE_URL` 和 `GBRAIN_API_KEY` 后，`status` 返回 `configured`，`capabilities` 返回 `hybrid_retrieval`、`answer_synthesis`、`knowledge_graph`；响应不得返回 GBrain URL、API Key 或密钥片段。

### 登录

```http
POST /api/auth/login
```

当前 MVP 内置种子账号仅用于 `APP_ENV=local|test|development` 的本地验证；非本地环境默认拒绝种子账号登录，除非显式设置受控的 `ALLOW_SEEDED_USERS=true`。

请求体：

```json
{
  "username": "admin@example.com",
  "password": "<redacted>"
}
```

响应：

```json
{
  "data": {
    "access_token": "<redacted>",
    "token_type": "bearer",
    "expires_in": 28800,
    "user": {
      "id": "user_admin",
      "username": "admin@example.com",
      "display_name": "AI Brain Admin",
      "roles": ["admin"]
    }
  },
  "trace_id": "trace_001"
}
```

### 角色目录

```http
GET /api/auth/roles
```

该接口返回当前 MVP 可分配的系统角色目录，供用户管理页面、知识权限选择、权限说明和外部集成统一引用。`POST /api/users`、`PATCH /api/users/{user_id}` 和知识 `permission_roles` 字段只能使用该目录中的 `code`。

v1.2 目标态按 [RBAC 重设计](rbac-redesign.md) 演进：`GET /api/auth/roles` 作为 active/assignable 角色目录兼容接口保留；角色治理、权限点目录、角色权限矩阵、角色菜单授权、角色数据范围和用户授权管理迁移到 `/api/system/roles`、`/api/system/permissions`、`/api/system/menus`、`/api/users/{user_id}/roles`、`/api/users/{user_id}/permissions` 与 `/api/users/{user_id}/scopes`。组织/部门通过 `/api/system/departments` 管理，外部身份通过 `/api/system/external-identities` 绑定到系统 `users.id`，产品成员通过 `/api/products/{product_id}/members` 在产品管理页维护，知识空间通过 `/api/knowledge/spaces` 管理并作为知识检索权限边界。`/api/auth/me` 目标态返回 `menu_tree` 和 `route_permissions`，前端左侧菜单按 `menu_tree` 渲染。业务接口后续应校验权限点和数据范围，不再直接依赖角色 code，也不能把菜单隐藏作为安全边界；未绑定系统用户 ID 的 SSO 身份不得获得默认角色、部门或范围。目标角色目录除 MVP 六个兼容角色外，还应提供 `developer`、`test_owner`、`tester`、`release_owner` 等研发交付扩展预置角色模板。

### 系统 RBAC API

Task 3 提供最小可用角色治理接口，用于系统管理员维护角色、角色权限点、角色菜单、角色数据范围以及用户授权。`GET /api/system/menus` 允许具备 `system.menus.read`、`system.menus.manage` 或历史兼容 `system.roles.manage` 的用户读取；菜单资源写接口要求 `system.menus.manage`；角色治理接口要求 `system.roles.manage`；`/api/users/{user_id}/permissions`、`/api/users/{user_id}/roles` 和 `/api/users/{user_id}/scopes` 要求 `system.users.manage`。非授权用户返回 `403 FORBIDDEN`。系统角色（尤其 `admin`）当前不可停用，系统菜单当前不可删除；角色和菜单变更写入 `role_change_events` / `audit_events` 或对应菜单变更审计事件。`admin` 是内置超级管理员角色：有效权限和可见菜单运行时按所有 active 权限点与菜单资源动态展开，不依赖角色权限/菜单配置，角色页无需额外维护 admin 的权限矩阵。

`GET /api/system/permissions/matrix` 为只读策略矩阵接口，允许 `system.roles.read` 或 `system.roles.manage` 访问。响应聚合 `roles`、`permissions`、`menus`、`rows` 和 `summary`：每个 `rows[]` 项按角色返回 `permission_count`、`granted_permission_codes`、`high_risk_permission_codes`、`menu_count`、`granted_menu_codes`、`required_permission_codes`、`missing_menu_permission_codes`、`scope_summary`、`scopes` 和 `diagnostics`。当角色被授权某菜单但缺少该菜单 `required_permissions` 时，`diagnostics` 必须包含 `menu_permission_gap`；当角色包含高风险权限时，必须包含 `high_risk_permission`。该接口不写入数据，角色管理页用于权限审计、范围检查和授权缺口排障。

角色详情响应统一返回：

```json
{
  "id": "role_delivery_operator",
  "code": "delivery_operator",
  "name": "Delivery Operator",
  "description": "Can operate delivery queues.",
  "category": "delivery",
  "is_system": false,
  "is_assignable": true,
  "status": "active",
  "sort_order": 110,
  "permission_codes": ["bug.read", "task.read"],
  "menu_codes": ["task", "task.center"],
  "scopes": [
    {"scope_type": "product", "scope_id": "product_alpha", "access_level": "write"}
  ]
}
```

请求体约定：

- `POST /api/system/menus`：`code`、`name` 必填，`path`、`parent_code`、`menu_type=group|page|hidden_page`、`icon`、`sort_order`、`required_permissions`、`status=active|inactive` 可选。数据库菜单只维护导航元数据与权限映射，前端仍只加载静态路由注册表中存在的页面组件。
- `PATCH /api/system/menus/{menu_code}`：可更新 `name`、`path`、`parent_code`、`menu_type`、`icon`、`sort_order`、`required_permissions`、`status`，`code` 不可改。
- `PUT /api/system/menus/reorder`：`{"items": [{"code": "system.menus", "sort_order": 63}]}`，只更新排序并返回更新后的菜单资源列表。
- `POST /api/system/roles`：`code`、`name` 必填，`description`、`category`、`is_assignable`、`sort_order` 可选。
- `POST /api/system/roles/{role_id}/copy`：`code` 必填，`name`、`description` 可选，权限、菜单和范围从源角色复制。
- `PATCH /api/system/roles/{role_id}`：可更新 `name`、`description`、`category`、`is_assignable`、`sort_order`。
- `PUT /api/system/roles/{role_id}/permissions`：`{"permission_codes": ["task.read"]}`，整体替换角色权限。
- `PUT /api/system/roles/{role_id}/menus`：`{"menu_codes": ["task", "task.center"]}`，整体替换角色菜单授权。
- `PUT /api/system/roles/{role_id}/scopes` 与 `PUT /api/users/{user_id}/scopes`：`{"scopes": [{"scope_type": "product", "scope_id": "product_alpha", "access_level": "write"}]}`，整体替换范围授权。
- `PUT /api/users/{user_id}/roles`：`{"role_codes": ["developer"]}`，整体替换用户角色授权。

新增错误码：

| 错误码 | HTTP | 说明 |
|------|------|------|
| `ROLE_CODE_EXISTS` | 409 | 角色 `code` 已存在。 |
| `MENU_CODE_EXISTS` | 409 | 菜单 `code` 已存在。 |
| `MENU_HAS_CHILDREN` | 409 | 菜单存在子菜单，不允许直接删除。 |
| `MENU_PARENT_NOT_FOUND` | 400 | 指定父级菜单不存在或不可用。 |
| `SYSTEM_ROLE_PROTECTED` | 409 | 系统角色不可执行当前破坏性操作，当前主要用于拒绝停用系统角色。 |
| `SYSTEM_MENU_PROTECTED` | 409 | 系统菜单不可删除。 |
| `UNSUPPORTED_MENU_STATUS` | 400 | 菜单状态不是 `active` 或 `inactive`。 |
| `UNSUPPORTED_MENU_TYPE` | 400 | 菜单类型不是 `group`、`page` 或 `hidden_page`。 |
| `UNSUPPORTED_PERMISSION` | 400 | 请求包含不存在或不可用的权限点。 |
| `UNSUPPORTED_MENU` | 400 | 请求包含不存在或不可用的菜单资源。 |
| `INVALID_SCOPE` | 400 | 数据范围类型、范围 ID 或访问级别非法。 |

响应：

```json
{
  "data": {
    "items": [
      {
        "code": "admin",
        "name": "系统管理员",
        "description": "负责用户、角色、模型网关、审计与系统级配置管理。",
        "category": "system",
        "business_roles": ["平台管理员"],
        "responsibilities": [
          "管理本地用户账号、状态和角色分配。",
          "维护 OpenAI-compatible 模型网关配置。",
          "查看审计与运行状态，处理系统级异常。"
        ],
        "data_scope": "全平台系统配置、审计事件和授权业务数据。",
        "decision_scope": "账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍。",
        "menu_scope": ["系统管理", "审计与运行", "产品资产", "需求交付", "任务中心"],
        "limitations": [
          "不代替产品负责人、研发负责人或评审负责人做业务最终决策。",
          "所有系统配置、用户和模型网关变更必须写入审计。"
        ],
        "permissions": ["system.users.manage", "system.model_gateway.manage", "audit.read", "workspace.read", "workspace.write"],
        "is_assignable": true,
        "sort_order": 10,
        "status": "active"
      }
    ],
    "total": 6
  },
  "trace_id": "trace_002"
}
```

### 业务大脑

业务大脑 v1 MVP 只提供只读配置读取，默认从 `brain_apps` 表加载 `rd_brain`；不提供业务大脑新增、编辑、停用或系统管理页面 CRUD。

```http
GET /api/brain-apps
GET /api/brain-apps/{brain_app_id}
```

列表响应：

```json
{
  "data": {
    "items": [
      {
        "id": "rd_brain",
        "code": "rd_brain",
        "name": "研发大脑",
        "status": "active",
        "description": "把研发需求转成可确认、可回写、可沉淀的任务方案。",
        "config": {
          "default_task_types": [
            "product_detail_design",
            "technical_solution",
            "development_planning",
            "automated_testing",
            "release_readiness",
            "post_release_analysis",
            "code_review"
          ]
        }
      }
    ]
  },
  "trace_id": "trace_002"
}
```

### 产品配置

查询接口都支持 `active_only=true|false`：

```http
GET /api/products?active_only=true
GET /api/products/{product_id}/versions?active_only=true
GET /api/products/{product_id}/modules?active_only=true
GET /api/products/{product_id}/git-repositories?active_only=true
```

产品列表主表还支持 `code/name/owner_team/status/page/page_size/sort_by/sort_order`；响应行包含
`current_version_code`、`current_version_name` 和 `module_count`，由服务端聚合产品版本与模块结构表，前端产品列表不得再为主表展示额外拉取全量版本或模块列表。

维护接口：

```http
POST /api/products
PATCH /api/products/{product_id}
POST /api/products/{product_id}/versions
PATCH /api/product-versions/{version_id}
POST /api/product-versions/{version_id}/advance-status
DELETE /api/product-versions/{version_id}
GET /api/product-versions/{version_id}/branch-configs
POST /api/product-versions/{version_id}/branch-configs
PATCH /api/product-version-branch-configs/{branch_config_id}
DELETE /api/product-version-branch-configs/{branch_config_id}
POST /api/products/{product_id}/modules
PATCH /api/product-modules/{module_id}
DELETE /api/product-modules/{module_id}
POST /api/products/{product_id}/git-repositories
PATCH /api/product-git-repositories/{repo_id}
DELETE /api/product-git-repositories/{repo_id}
```

产品请求体：

```json
{
  "code": "ai_brain",
  "name": "AI Brain",
  "description": "企业 AI 大脑平台",
  "owner_team": "rd",
  "status": "active",
  "display_order": 100
}
```

版本请求体：

```json
{
  "code": "v1",
  "name": "v1.0",
  "description": "第一版闭环",
  "status": "active",
  "start_date": "2026-05-01",
  "release_date": "2026-05-31"
}
```

模块请求体：

```json
{
  "code": "knowledge",
  "name": "知识中心",
  "description": "文档导入、检索和沉淀",
  "owner_team": "rd",
  "status": "active",
  "display_order": 100
}
```

Git 资源请求体：

```json
{
  "repo_type": "code",
  "name": "ai-brain-api",
  "remote_url": "https://gitlab.internal/rd/ai-brain-api.git",
  "git_provider": "gitlab",
  "project_id": "123",
  "project_path": "rd/ai-brain-api",
  "credential_ref": "secret://gitlab/ai-brain-readonly-token",
  "default_branch": "main",
  "root_path": "/",
  "status": "active"
}
```

约束：

- 产品和模块状态：`active | inactive`。
- 版本主状态：`planning | active | testing | released`；`archived` 仅作为历史归档状态。
- Git 资源类型：`code | docs | prd | test`。
- Git 资源状态：`active | inactive`。
- `git_provider` 支持 `gitlab` 和 `github`。GitLab 绑定需提供 `project_id` 或 `project_path`；GitHub 绑定需提供 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`。
- `credential_ref` 推荐使用 `env:GITLAB_READONLY_TOKEN`、`env:GITHUB_READONLY_TOKEN` 或服务端密钥引用；本地联调可直填只读 token，API 响应仍只返回 `credential_ref_configured`，不返回密钥引用或明文 token。
- 前端产品配置弹窗可提交 `credential_ref`，编辑时留空表示保留服务端已有凭据；列表只显示“已配置/未配置”状态。
- 仅 `planning` 和 `active` 版本可用于新需求排期；`testing`、`released` 和 `archived` 版本不可用于新需求或新开发任务，历史任务继续使用生成时保存的产品上下文快照。
- `PATCH /api/product-versions/{version_id}` 不允许改变 `status`；状态推进必须调用 `POST /api/product-versions/{version_id}/advance-status`，否则返回 `PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED`。

迭代版本状态推进请求：

```http
POST /api/product-versions/version_001/advance-status
```

请求体：

```json
{
  "target_status": "testing",
  "reason": "进入系统测试",
  "force": false,
  "preview_only": false
}
```

规则：

- `preview_only=true` 只返回影响预览，不修改版本或需求。
- `planning -> active`：`approved/planned` 需求同步推进到 `ready_for_dev`。
- `active -> testing`：`approved/planned/ready_for_dev/designing/developing/code_reviewing` 等已进入交付链路的版本内需求同步推进到 `testing`；`draft/submitted` 等未完成审批入池状态进入阻塞明细，未设置 `force=true` 时返回 `PRODUCT_VERSION_STATUS_BLOCKED`，强制推进时版本进入测试中但阻塞需求保持原状态。
- `testing -> released`：`testing/ready_for_release` 需求同步推进到 `released`；仍处于设计、开发、评审等未完成状态的需求必须先延期、取消或关闭，`force=true` 不绕过发布阻塞。
- `released -> archived`：归档仅作为历史管理动作；`released/accepted/deferred/cancelled/closed/rejected` 需求保持不变，未完成需求作为归档风险项。
- 成功推进记录 `product_version.status_advanced` 审计事件；每条被同步推进的需求另记录 `requirement.updated`，payload 包含版本状态来源、目标、原因和需求状态来源/目标。

迭代版本代码分支请求：

```http
POST /api/product-versions/version_001/branch-configs
```

```json
{
  "repository_id": "repo_001",
  "base_branch": "main",
  "working_branch": "release/2026-06",
  "branch_status": "active",
  "creation_source": "manual",
  "description": "2026-06 版本前后端共用开发分支"
}
```

响应会返回仓库展示投影：

```json
{
  "data": {
    "id": "version_branch_001",
    "product_id": "product_001",
    "version_id": "version_001",
    "repository_id": "repo_001",
    "repository_name": "AI Brain Web",
    "repository_provider": "github",
    "repository_path": "zeek428/e-ai-brain",
    "repository_default_branch": "main",
    "base_branch": "main",
    "working_branch": "release/2026-06",
    "branch_status": "active",
    "creation_source": "manual",
    "description": "2026-06 版本前后端共用开发分支"
  },
  "trace_id": "trace_xxx"
}
```

`repository_id` 必须指向同产品 Git 资源；同一 `version_id + repository_id` 只能存在一条配置。`branch_status` 可取 `not_created / active / testing / merged / released / archived`，`creation_source` 可取 `manual / ai_task / github_sync / gitlab_sync`。

### 平台配置

相关系统：

```http
GET /api/system/related-systems?active_only=true&product_id=product_rd
POST /api/system/related-systems
PATCH /api/system/related-systems/{system_id}
```

请求体：

```json
{
  "code": "knowledge",
  "name": "知识中心",
  "description": "文档导入、检索和知识沉淀",
  "owner_team": "rd",
  "product_id": "product_rd",
  "status": "active",
  "display_order": 100
}
```

模型网关配置：

```http
GET /api/system/model-gateway-configs?page=1&page_size=10&sort_by=name&sort_order=asc
POST /api/system/model-gateway-configs/test
POST /api/system/model-gateway-configs
PATCH /api/system/model-gateway-configs/{config_id}
DELETE /api/system/model-gateway-configs/{config_id}
```

`GET /api/system/model-gateway-configs` 未传 `page/page_size` 时保留原全量列表兼容响应；分页模式支持 `name`、`provider`、`status`、`is_default`、`default_chat_model`、`default_embedding_model`、`embedding_connection_mode` 筛选，支持按 `name/provider/status/is_default/base_url/default_chat_model/default_embedding_model/embedding_connection_mode/id` 排序，并返回 `query` 与 `performance` 元数据用于定位模型网关配置页查询耗时。

请求体：

```json
{
  "name": "默认模型网关",
  "provider": "openai_compatible",
  "base_url": "https://api.example.com/v1",
  "api_key": "<redacted>",
  "default_chat_model": "chat-model",
  "default_embedding_model": "embedding-model",
  "embedding_connection_mode": "reuse_chat",
  "embedding_base_url": null,
  "embedding_api_key": null,
  "embedding_dimension": 1536,
  "timeout_seconds": 60,
  "max_retries": 1,
  "status": "active",
  "is_default": true
}
```

响应不会返回明文 `api_key`、`embedding_api_key`、密钥前缀或后缀，只返回 `api_key_configured` 和 `embedding_api_key_configured`。`embedding_connection_mode` 可取 `disabled`、`reuse_chat` 或 `custom`：`disabled` 表示仅启用 Chat 能力，`reuse_chat` 使用 Chat 的 `base_url/api_key` 调用 `/embeddings`，`custom` 使用 `embedding_base_url/embedding_api_key` 调用 `/embeddings`。`default_embedding_model` 在 `disabled` 模式可为空；`embedding_dimension` 当前必须等于系统 `VECTOR_DIMENSION`。
`provider` 目前仅允许 `openai_compatible`；新增或编辑提交其他 provider 返回 `400 VALIDATION_ERROR`，不得保存为 active/default 配置。

测试检测：

```http
POST /api/system/model-gateway-configs/test
```

请求体使用模型网关配置字段，可选传入 `config_id`。编辑已有配置时，如果请求体不含 `api_key` 且 `config_id` 对应配置已保存密钥，则使用服务端已有密钥完成本次 Chat 测试；`embedding_connection_mode=custom` 且请求体不含 `embedding_api_key` 时，可复用已有配置中的服务端 Embedding 密钥。新增配置测试必须显式提交所需密钥。`test_target` 默认为 `chat_and_embedding`，可取 `chat_and_embedding`、`chat` 或 `embedding`；当 `test_target=chat` 或 `embedding_connection_mode=disabled` 时不要求 `default_embedding_model`，Embedding 段返回 `status=skipped`。

```json
{
  "config_id": "model_config_default",
  "name": "默认模型网关",
  "provider": "openai_compatible",
  "base_url": "https://api.example.com/v1",
  "api_key": "<redacted>",
  "default_chat_model": "chat-model",
  "default_embedding_model": "embedding-model",
  "embedding_connection_mode": "custom",
  "embedding_base_url": "https://embedding.example.com/v1",
  "embedding_api_key": "<redacted>",
  "embedding_dimension": 1536,
  "timeout_seconds": 60,
  "max_retries": 1,
  "status": "active",
  "is_default": true,
  "test_target": "chat_and_embedding"
}
```

成功或 provider 调用失败都返回脱敏检测结果；整体 `ok=false` 时前端应展示失败段和 `error_code`，不把本次测试自动保存为配置。

```json
{
  "ok": true,
  "chat": {
    "ok": true,
    "status": "succeeded",
    "model": "chat-model",
    "latency_ms": 18
  },
  "embedding": {
    "ok": true,
    "status": "succeeded",
    "model": "embedding-model",
    "latency_ms": 12,
    "dimension": 1536
  },
  "test_target": "chat_and_embedding"
}
```

仅测试 Chat 的响应示例：

```json
{
  "ok": true,
  "chat": {
    "ok": true,
    "status": "succeeded",
    "model": "codex-auto-review",
    "latency_ms": 18
  },
  "embedding": {
    "ok": true,
    "status": "skipped",
    "model": ""
  },
  "test_target": "chat"
}
```

测试接口会按 `test_target` 临时调用 `{base_url}/chat/completions` 和/或 Embedding 连接对应的 `/embeddings`，但不得持久化配置、密钥或写入 `model_gateway_logs`；只写入 `model_gateway_config.tested` 审计事件，载荷包含 provider、测试范围和测试状态，不包含密钥、完整 prompt 或完整输出。`test_target=chat` 只证明 Chat 能力可用，不代表知识索引、知识检索或长期记忆 embedding 能力可用。健康检查继续返回兼容字段 `model_gateway`，并额外返回 `chat_gateway` 与 `embedding_gateway`，Embedding 可为 `configured`、`disabled`、`failed` 或 `not_configured`。

模型调用日志：

```http
GET /api/model-gateway/logs?ai_task_id=task_001&status=succeeded
```

模型调用日志只返回 `provider`、`model`、`purpose`、`tokens`、`latency_ms`、`status`、`error`、`created_at` 和 `model_gateway_config_id` 等元数据，不返回完整 prompt、完整模型输出或密钥。

AI 助手聊天：

```http
POST /api/assistant/chat
```

请求体：

```json
{
  "conversation_id": "conversation_001",
  "client_request_id": "assistant_chat_run_202606200001",
  "message": "AI Brain 项目现在开发到哪里了？",
  "product_id": "product_001",
  "run_id": "assistant_chat_run_202606200001",
  "references": [
    {"type": "knowledge_document", "id": "knowledge_doc_001"}
  ],
  "context": {
    "source": "assistant-page"
  }
}
```

响应：

```json
{
  "conversation_id": "conversation_001",
  "message": {
    "id": "assistant_message_001",
    "role": "assistant",
    "run_id": "assistant_chat_run_202606200001",
    "status": "completed",
    "content": "当前已完成 GitHub PR Review 支持，正在推进 AI 助手聊天界面。",
    "references": [
      {
        "id": "requirement_084",
        "type": "requirement",
        "title": "AI 助手历史记录迭代",
        "url": "/delivery/requirements?requirement_id=requirement_084"
      }
    ],
    "tool_results": [
      {
        "tool": "assistant.delivery_progress",
        "intent": "delivery_progress",
        "summary": {
          "requirements_total": 7,
          "tasks_total": 3
        },
        "items": [
          {
            "id": "requirement_084",
            "title": "AI 助手历史记录迭代",
            "status": "testing",
            "url": "/delivery/requirements?requirement_id=requirement_084"
          }
        ],
        "references": [
          {
            "id": "requirement_084",
            "type": "requirement",
            "title": "AI 助手历史记录迭代",
            "url": "/delivery/requirements?requirement_id=requirement_084"
          }
        ]
      }
    ]
  },
  "run": {
    "id": "assistant_chat_run_202606200001",
    "conversation_id": "conversation_001",
    "status": "succeeded",
    "started_at": "2026-06-20T09:00:00+00:00",
    "finished_at": "2026-06-20T09:00:02+00:00"
  },
  "run_id": "assistant_chat_run_202606200001",
  "status": "succeeded",
  "model": "codex-auto-review",
  "latency_ms": 358,
  "suggestions": ["查看任务中心", "检查 GitHub PR"]
}
```

助手请求会向模型网关注入服务端生成的 `system_context`，包含当前产品、需求数量、任务数量、最新需求/任务、Git 仓库和默认模型网关配置状态。服务端还会基于用户问题和 read context 生成 `tool_results` 与 `reference_candidates`：`tool_results` 可覆盖 `assistant.delivery_progress`、`assistant.pending_reviews`、`assistant.code_review`、`assistant.iteration`、`assistant.bugs`、`assistant.model_gateway`、`assistant.action_draft`、`assistant.task_creation_guide`、`assistant.scheduled_job_diagnostic` 和 `assistant.plugin_connection_diagnostic`，`reference_candidates` 可覆盖命令面板型 `assistant_action`，以及引用类 `product`、`iteration_version`、`requirement`、`ai_task`、`human_review`、`bug`、`code_review_report`、`knowledge_deposit`、`knowledge_space`、`knowledge_folder`、`knowledge_document`、`knowledge_chunk`，以及管理员、`system.admin` 或对应管理权限可见的 `scheduled_job`、`scheduled_job_run`、`plugin_action`、`plugin_connection`、`ai_agent`、`ai_skill`。引用候选 query 识别类型词时，`新建/新增/创建` 可匹配 `assistant_action`，`定时作业/定时任务` 优先匹配 `scheduled_job`，`运行记录/失败` 优先匹配 `scheduled_job_run`，`知识空间/知识目录` 分别匹配 `knowledge_space` / `knowledge_folder`，避免用户在创建配置、执行一次、失败诊断或知识范围引用前选到错误上下文。若模型未返回有效引用，则优先使用工具结果中的引用兜底，再使用服务端候选引用兜底。`system_context` 只进入模型请求，不写入模型日志；`tool_results` 会随助手消息 metadata 持久化并在聊天响应/历史消息中返回；模型日志以 `purpose=assistant_chat` 记录 provider、model、tokens、latency、status 和 error 等元数据。每次聊天请求都会创建或复用 `assistant_chat_runs` 运行记录，状态为 `running/succeeded/cancelled/failed`；用户消息先按同一 `run_id` 写入 `pending`，成功后用户消息和助手消息置为 `completed`，取消时置为 `cancelled`，失败时写入 `failed/error_code`。`client_request_id` 用于客户端重试、停止生成和审计关联，未传时默认等同 `run_id`。成功审计事件为 `assistant.chat_completed`，取消审计事件为 `assistant.chat_cancelled`，失败审计事件为 `assistant.chat_failed`。

停止生成：

```http
POST /api/assistant/chat-runs/{run_id}/cancel
```

请求体：

```json
{
  "reason": "user_cancelled"
}
```

响应：

```json
{
  "id": "assistant_chat_run_202606200001",
  "conversation_id": "conversation_001",
  "status": "cancelled",
  "cancel_reason": "user_cancelled",
  "cancelled_at": "2026-06-20T09:00:01+00:00"
}
```

取消接口只允许当前用户取消自己的聊天运行；若运行已成功或失败，接口返回当前终态，不反向修改已完成消息。服务端在进入模型调用前和模型返回后都会检查 `assistant_chat_runs.status`，若已取消则不把模型结果写入历史，而是持久化一条 `cancelled` 状态的助手消息，便于刷新历史后仍能看到“已停止生成”的真实状态。

当用户泛化发送“新增任务/创建任务/我要建任务”但没有说明任务类型时，`/api/assistant/chat` 必须返回 `tool=assistant.task_creation_guide` 的确定性工具结果，不调用模型网关。`tool_results[0].items[]` 和响应顶层 `suggestions` 必须同时覆盖五类入口：研发任务、定时作业、插件动作、代码巡检和反馈洞察；建议文案固定为 `新增研发任务`、`新增定时作业`、`新增插件动作`、`配置代码巡检定时作业`、`配置每周用户反馈洞察定时作业`，便于前端同时展示任务类型卡片和可点击建议按钮。

当管理员询问“插件连接为什么失败/连接失败怎么修/插件连接诊断”且没有创建草案意图时，`/api/assistant/chat` 必须返回 `tool=assistant.plugin_connection_diagnostic` 的确定性工具结果，不调用模型网关。工具项按最近失败或最近测试的插件连接返回 `connection_config/latest_test/repair_suggestions` 三段诊断，字段可包含连接 ID、名称、插件名、环境、endpoint、最近测试状态、失败步骤、错误码、错误信息和结构化修复建议；不得返回 `auth_config`、完整认证 Header、完整请求体或密钥。前端必须展示“插件连接诊断”卡片，并可把 `plugin_connection` 引用加入“本次上下文”继续追问。

显式引用由前端 `@` 选择器提交到聊天请求的可选 `references` 字段，后端不从自然语言中猜测 ID。服务端必须先解析引用、校验当前用户权限和可读状态，再构造脱敏上下文。`knowledge_document` 候选和解析只返回当前用户可读、索引状态可检索的知识文档；聊天时按权限读取有限数量的知识 chunk，注入 `system_context.selected_references` 和 `system_context.knowledge_context`。`knowledge_chunk` 候选和解析只返回当前用户可读、所属文档可检索的知识片段，聊天时只注入被显式选中的单个片段。`scheduled_job`、`scheduled_job_run`、`plugin_action`、`plugin_connection`、`ai_agent` 和 `ai_skill` 属于受控运维配置引用，候选和解析必须要求管理员、`system.admin` 或对象类型对应的管理/执行权限：定时作业和运行记录要求 `system.scheduled_jobs.manage` 或 `system.scheduled_jobs.run`，插件连接和插件动作要求 `system.plugins.manage`，AI角色和 Skill 要求 `system.ai_capabilities.manage`；定时作业和运行记录还必须按当前用户 `scope_summary` 中的产品 scope 过滤，拥有产品级 scope 的用户不得看到其他产品作业或运行。无对应权限或 scope 时候选返回空集合，解析返回 `404 REFERENCE_NOT_FOUND`。`assistant_action` 属于命令面板动作入口，不属于可解析上下文引用；候选优先读取 `assistant_action_reference_configs`，按 `enabled`、角色、权限、企业、模板版本和 `rollout_json` 灰度策略过滤；同 `action_key` 的配置可覆盖或禁用默认动作，新增 `action_key` 可扩展自定义动作，没有任何配置记录时回退内置默认目录。默认动作覆盖 `新建需求`、`新建 Bug`、`新建插件连接`、`新建插件动作`、`新建定时作业`、`新建知识文档/导入任务` 和 `新建 AI 能力配置`，并携带 `action/prompt/summary/source_module=动作/permission_label=可执行`。前端选择 `assistant_action` 后必须用候选标题生成输入框头部命令前缀（例如 `@新建需求 `、`@新建定时作业 `），并把用户已在当前 `@` 片段之后输入的正文承接在前缀之后；候选 `prompt` 只作为动作说明和草案提示来源，不得直接覆盖用户输入。选择动作后必须关闭候选面板，不得加入本次上下文、不得写入最近引用、不得提交到 `references[]` 或 `/api/assistant/references/resolve`。前端引用类型标签必须把 `assistant_action` 显示为“动作”，把 `ai_task` 显示为“研发任务”，把 `ai_skill` 显示为“Skill”，并在候选分组、类型 Tag、已选引用 Chip 和本次上下文摘要中保持一致。未指定 `type` 的默认候选按引用类型均衡合并，后端在满足 `limit` 的前提下优先为动作入口、知识文档/片段、需求、研发任务、定时作业、运行记录、插件动作、插件连接、AI角色和 Skill 等类型各返回至少一个可用候选，避免单一类型挤占整个面板；指定 `type` 且查询词为空时，应先按目标类型取足候选再截断，不得被全局默认类型顺序提前截断；`limit` 上限仍为 20，前端裸 `@` 应请求足够数量的默认候选。前端对 `@... 执行一次` 这类 run-once 命令，在候选仍加载或用户直接按 Enter/点击发送时，必须用当前 `@` 文本追加一次 `type=scheduled_job` 候选查询，把可用定时作业引用随 `/api/assistant/chat` 一起提交；查询失败时后端显式 @ 名称解析仍可兜底。未授权、不可读、不可检索或不存在的引用不得进入模型上下文。模型日志继续只保存调用元数据，不保存完整知识正文、完整 prompt、插件密钥或外部系统 token。

补充约定：`assistant_action` 仅在 query 包含“新建/新增/创建/配置”等动作触发词，或客户端显式传入 `type=assistant_action` 时并入默认候选；裸 `@` 和仅包含“定时作业/运行记录/知识文档”等对象类型词的查询，应继续优先返回已有对象引用，避免“新建定时作业”抢占“引用已有定时作业”的路径。

`@` 引用候选：

```http
GET /api/assistant/reference-candidates?query=反馈&product_id=product_001&limit=10
```

响应：

```json
{
  "items": [
    {
      "id": "knowledge_doc_001",
      "type": "knowledge_document",
      "title": "反馈分类标准",
      "url": "/knowledge/documents?document_id=knowledge_doc_001",
      "chunk_count": 12,
      "index_status": "vector_indexed",
      "source_module": "知识库",
      "permission_label": "可引用",
      "updated_at": "2026-06-14T08:00:00+00:00",
      "summary": "用于判断反馈类别、严重度和后续转需求规则。"
    },
    {
      "id": "knowledge_chunk_001",
      "type": "knowledge_chunk",
      "title": "反馈分类标准 #1",
      "url": "/knowledge/documents?document_id=knowledge_doc_001&chunk_id=knowledge_chunk_001",
      "chunk_count": 1,
      "chunk_index": 0,
      "document_id": "knowledge_doc_001",
      "source_module": "知识库",
      "permission_label": "可引用",
      "updated_at": "2026-06-14T08:00:00+00:00",
      "summary": "只用于模型上下文的这个片段摘要。"
    },
    {
      "id": "scheduled_job_run_001",
      "type": "scheduled_job_run",
      "title": "每周反馈洞察定时作业 / failed",
      "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_001"
    },
    {
      "id": "create_scheduled_job",
      "type": "assistant_action",
      "action": "create_scheduled_job",
      "title": "新建定时作业",
      "url": "/tasks/scheduled-jobs",
      "source_module": "动作",
      "permission_label": "可执行",
      "prompt": "请帮我生成定时作业配置草案，并说明数据来源、AI处理、结果动作和调度策略。",
      "summary": "生成可确认的定时作业草案。"
    }
  ],
  "total": 4
}
```

`type` 仍可选传，用于限定候选类型；不传时按权限返回混合候选。管理员可得到配置/运行类候选和动作入口，普通用户只能得到业务对象、可读知识文档、可读知识片段以及其角色允许的动作入口。候选可携带 `source_module`、`permission_label`、`updated_at` 和轻量 `summary`，供前端“本次上下文”展示来源、权限、更新时间、知识 chunk 注入状态和引用摘要；`assistant_action` 额外携带 `action` 和 `prompt`，供前端构造 `@动作名` 命令前缀和草案提示，不进入“本次上下文”。前端可提供“查看摘要”弹窗，但只能展示引用类型、来源、权限、更新时间、注入口径和摘要元数据，不得展示完整知识正文；模型日志不得保存完整知识正文。

当聊天消息显式引用 `scheduled_job_run` 且问题包含失败、原因、诊断或排查意图时，响应中的 `message.tool_results[]` 会包含；因为引用本身已经提供运行上下文，短追问“为什么这次失败？”也必须触发该工具，不要求文本再次出现“任务/作业/run”等词：

```json
{
  "tool": "assistant.scheduled_job_diagnostic",
  "intent": "scheduled_job_diagnostic",
  "summary": {"run_count": 1, "failed_count": 1},
  "items": [
    {
      "id": "scheduled_job_run_001",
      "scheduled_job_id": "scheduled_job_001",
      "status": "failed",
      "title": "每周反馈洞察定时作业 / failed",
      "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_001",
      "stages": [
        {"stage": "data_connection", "status": "succeeded", "summary": "读取 128 条反馈", "error_message": null, "log_id": null},
        {"stage": "ai_processing", "status": "succeeded", "summary": "生成 6 条洞察", "error_message": null, "log_id": "model_gateway_log_001"},
        {"stage": "result_action", "status": "failed", "summary": "写入反馈洞察表失败", "error_code": "RESULT_WRITE_FAILED", "error_message": "HTTP 500", "log_id": "plugin_invocation_log_001", "result_write_record_id": "result_write_record_scheduled_job_run_001", "result_write_status": "failed", "result_write_target": "user_feedback_insights", "result_write_target_label": "用户洞察表"}
      ]
    }
  ],
  "references": [
    {"type": "scheduled_job_run", "id": "scheduled_job_run_001", "title": "每周反馈洞察定时作业 / failed", "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_001"}
  ]
}
```

前端诊断卡片必须把三个阶段分别展示为“数据连接是否成功”“AI处理是否成功”“结果动作是否写入成功”，并将阶段状态转换为成功、失败、执行中、排队中、有告警或已跳过等用户可读判断。各阶段的 `log_id` 只表示安全日志元数据 ID，前端诊断卡片必须展示为“关联日志：<log_id>”，用于继续追踪模型日志或插件调用日志；不得展示完整插件请求/响应、模型 Prompt、模型输出或密钥。`result_action` 段的结果写入字段来自与 `/api/system/result-write-records?scheduled_job_run_id=<run_id>` 同源的派生读模型，只返回记录 ID、状态、写入目标和标签等排障元数据。

当聊天消息显式引用 `scheduled_job_run` 且问题包含“和上次成功有什么不同/对比/差异”意图时，响应中的 `message.tool_results[]` 会包含；短追问“和上次成功有什么不同？”应直接使用已引用运行记录：

```json
{
  "tool": "assistant.scheduled_job_run_comparison",
  "intent": "scheduled_job_run_comparison",
  "summary": {"comparison_count": 1, "baseline_found_count": 1},
  "items": [
    {
      "id": "scheduled_job_run_002",
      "scheduled_job_id": "scheduled_job_001",
      "title": "每周反馈洞察定时作业 / failed",
      "url": "/tasks/scheduled-jobs?run_id=scheduled_job_run_002",
      "current_run": {"id": "scheduled_job_run_002", "status": "failed", "records_imported": 128, "duration_ms": 4200, "error_message": "结果写入动作返回 500"},
      "baseline_run": {"id": "scheduled_job_run_001", "status": "succeeded", "records_imported": 120, "duration_ms": 3600, "error_message": null},
      "differences": [
        {"field": "status", "baseline": "succeeded", "current": "failed"},
        {"field": "stage.result_action", "stage": "result_action", "baseline_status": "succeeded", "current_status": "failed", "baseline_summary": "写入反馈洞察表成功。", "current_summary": "写入反馈洞察表失败。", "baseline_result_write_status": "succeeded", "current_result_write_status": "failed"}
      ]
    }
  ]
}
```

该工具只对比同一 `scheduled_job_id` 下当前运行之前最近一次 `succeeded` 运行；无 baseline 时 `baseline_run=null` 且 differences 标记 `baseline_run` 缺失。响应不得包含完整插件请求/响应、模型 Prompt、模型输出或密钥。

当聊天消息显式引用失败的 `scheduled_job_run` 且问题包含“怎么修/修复草案/repair draft”等意图时，响应中的 `message.tool_results[]` 会包含 `tool=assistant.action_draft`、`intent=scheduled_job_run_repair_draft`。草案项使用 `action=create_plugin_action`，`client_draft_id=assistant_draft_repair_<scheduled_job_run_id>`，payload 从失败运行的结果动作节点、关联插件调用日志和原插件动作配置中提取安全字段，至少包含 `plugin_id`、`connection_id`、`action_type`、`code`、`name`、`request_config.method/path`、`result_mapping.write_target` 和 `status=active`。服务端会把该工具项持久化为 `assistant_action_drafts`，并返回 `server_draft_id/status/preview`；确认前不得创建真实插件动作、修改原动作或触发外部调用。工具结果、草案元数据和模型日志不得保存完整插件请求/响应、Prompt、模型输出或密钥。

引用解析：

```http
POST /api/assistant/references/resolve
```

请求：

```json
{
  "references": [
    {"type": "knowledge_chunk", "id": "knowledge_chunk_001"}
  ],
  "product_id": "product_001"
}
```

响应：

```json
{
  "items": [
    {
      "id": "knowledge_chunk_001",
      "type": "knowledge_chunk",
      "title": "反馈分类标准 #1",
      "url": "/knowledge/documents?document_id=knowledge_doc_001&chunk_id=knowledge_chunk_001"
    }
  ],
  "knowledge_context": [
    {
      "document_id": "knowledge_doc_001",
      "document_title": "反馈分类标准",
      "chunk_id": "knowledge_chunk_001",
      "chunk_index": 0,
      "content": "用于模型上下文的有限 chunk 文本",
      "source": {
        "doc_type": "manual",
        "knowledge_space_id": null
      }
    }
  ],
  "total": 1
}
```

助理动作草案已通过服务端持久化表和确认接口落地。`assistant.action_draft` 工具结果仍随聊天响应返回，前端助手页渲染为待确认配置草案卡片；服务端会把可支持的 `items[]` 转存为 `assistant_action_drafts` 记录，并在对应工具项上追加 `server_draft_id`、`client_draft_id` 和 `status`。工具项携带的 `wizard_steps[]` 必须写入草案元数据，并由 `GET /api/assistant/action-drafts/{draft_id}` 原样返回，供 `/assistant?draft_id=...` 深链和历史草案卡片恢复配置向导、步骤状态、摘要和依赖关系。支持的动作包括 `create_rd_task`、`create_ai_skill`、`create_ai_agent`、`create_scheduled_job`、`create_plugin_connection`、`create_plugin_action` 和 `create_analysis_draft`；可由 `assistant_tools` 构造的草案必须在模型调用前确定性返回，模型网关未配置时也不应阻塞草案生成。草案预检和确认权限必须按动作拆分：`create_plugin_connection` 和 `create_plugin_action` 要求管理员、`system.admin` 或 `system.plugins.manage`，`create_ai_skill` 和 `create_ai_agent` 要求管理员、`system.admin` 或 `system.ai_capabilities.manage`，`create_scheduled_job` 要求管理员、`system.admin` 或 `system.scheduled_jobs.manage`。状态为 `pending`、`confirmed`、`cancelled`、`expired` 或 `failed`。创建草案可携带顶层 `expires_at`，也兼容 `metadata_json.expires_at`；服务端读取、确认、取消、修改或更新 payload 前会把已过期且仍为 `pending` 的草案转为 `expired` 并写入 `assistant_action_draft.expired` 审计。确认前不得写入 `ai_tasks`、`ai_skills`、`ai_agents`、`scheduled_jobs`、`plugin_connections`、`plugin_actions` 或触发外部调用；分析类草案确认前也不得生成最终分析结果。前端点击“应用到表单”后，用户在任务中心/插件管理表单内编辑并保存时，必须先调用 `PATCH /api/assistant/action-drafts/{draft_id}` 提交最终 payload 和 `modified_fields`，再调用 confirm；不得直接调用领域创建接口绕过草案生命周期。PATCH 和修改指标接口仅允许 pending 草案，终态草案返回 `DRAFT_NOT_PENDING`。confirm 对已 confirmed 且已有成功动作运行的重复提交必须幂等返回同一 run；数据库层应保证同一草案最多一条成功 run。前端点击“查看详情”或通过 `/assistant?draft_id=...` 深链加载草案时，必须调用 `POST /api/assistant/action-drafts/{draft_id}/view`，请求体可带 `{ "surface": "detail_modal" | "deeplink" }`；服务端在草案 `metadata_json` 写入 `viewed_at`、`detail_viewed_at`、`last_viewed_at`、`view_count`、`viewed_by` 和 `last_view_surface`，记录 `assistant_action_draft.viewed` 审计并返回刷新后的草案。前端随后在当前对话页展示草案状态、动作、风险等级、payload JSON、字段差异和校验问题。

当聊天消息要求配置代码巡检定时作业且明确要求 AI/大模型分析扫描结果时，服务端必须生成 `intent=code_inspection_setup_draft` 的 `assistant.action_draft`。若系统缺少可用代码巡检 Skill 或 AI角色，`items[]` 应按 `create_ai_skill`、`create_ai_agent`、`create_scheduled_job` 顺序返回前置草案和最终作业草案；AI角色草案通过 `payload.assistant_prerequisite_draft_ids` 依赖 Skill 草案，定时作业草案通过同字段依赖 Skill/AI角色草案。最终 `create_scheduled_job` 草案项必须包含 `wizard_steps[]`，每项包含 `key/title/status/summary/depends_on`，用于显式展示数据来源、AI处理、结果动作、调度策略、确认执行的就绪状态和前置依赖；前端必须对 `status=needs_prerequisite/blocked` 的步骤展示“生成<步骤>前置草案”入口，点击后将草案标题、步骤名称和 `depends_on` 回填为新的助手输入，继续生成连接、动作、AI Skill 或 AI角色等前置草案。`create_ai_skill` payload 至少包含 `name/code/prompt_template/required_context/risk_level/status`；`create_ai_agent` payload 至少包含 `name/code/brain_app_id/model_gateway_config_id/default_skill_ids/system_prompt/status`。前端必须把这两类草案展示为 AI 能力配置草案，确认前不提供“应用到定时作业表单”，确认后返回 `ai_skill` 或 `ai_agent` 资源入口。

当聊天消息通过结构化 `scheduled_job` 引用或显式 `@定时作业名称` 并包含“执行一次/立即执行/run once”等意图时，助手确定性调用定时作业手动运行链路并返回 `tool=assistant.scheduled_job_run`。只要请求携带了结构化 `references[]` 中的 `scheduled_job`，后端必须进入 strict reference 模式并以该引用为用户主动选择的执行对象；文本 `@...` 仅用于没有结构化作业引用时的兜底解析，不得覆盖用户已选择的结构化引用。结构化引用指向停用、不可运行、无权限或不存在作业时，仍按权限和可执行状态返回明确错误或草案兜底，不得偷偷改成文本中相似的官方周反馈作业。没有结构化作业引用时，通用作业按完整 @ 文本的作业名称、标题、编码或 ID 精确命中优先，语义匹配出现多个相近作业但存在唯一精确命中时执行该精确作业；若没有唯一精确命中但语义匹配中只有一个 `enabled=true/status=active` 的可执行作业，则执行该可执行作业，避免历史停用相似任务导致命令退回草案。周反馈命令消歧仅在无结构化作业引用时生效，必须先按官方模板 `assistant_template.code=weekly_feedback_insight`、`job_type=user_feedback_insight_extract`、名称中的用户反馈/洞察/提取/每周语义和可执行状态评分，`source_system=aliyun-maxcompute` 只能作为弱辅助信号。若显式 @ 已尝试解析但没有唯一可执行作业，且文本命中“提取每周用户反馈有价值信息/周反馈洞察”等场景，聊天响应必须返回 `tool=assistant.action_draft`、`intent=scheduled_job_draft`，草案项 `client_draft_id=assistant_draft_weekly_feedback_insight/action=create_scheduled_job`，并在草案 payload 的 `config_json.assistant_run_once_request` 写入 `{"requested": true, "source_message": "<原始消息>"}`；服务端会持久化该草案并返回 `server_draft_id/status/preview`，但确认前不得创建真实作业或触发外部调用。客户端遇到该 run-once 草案时，草案卡片必须显示“确认后执行一次”，确认说明写明“确认后会立即执行一次”，按钮文案为“确认并执行一次”。用户确认带该 run-once 标记的草案后，`POST /api/assistant/action-drafts/{draft_id}/confirm` 的 `run.result_type` 仍为 `scheduled_job`，`run.result` 返回创建出的定时作业，并额外包含 `scheduled_job_run` 公开运行记录；`assistant_action_draft.confirmed` 审计 payload 同步包含 `scheduled_job_run_id`。客户端必须消费 `run.result.scheduled_job_run.id`，在草案卡确认成功状态中展示本次运行深链，例如 `/tasks/scheduled-jobs?job_id=<job_id>&run_id=<run_id>`。对于 `user_feedback_insight_extract`、`online_log_ai_analysis`、`iteration_plan_suggestion_generate` 这类 AI 处理链路较长的作业，聊天接口不得等待完整外部取数、模型处理和结果写入结束；后端在运行记录进入 `running` 或 `queued` 后立即返回运行 ID、状态、详情链接和引用，后台继续完成作业，用户可围绕该 `scheduled_job_run` 继续追问或在任务中心查看最终结果。前端收到 `assistant.scheduled_job_run.items[]/summary` 后必须展示运行记录卡；当状态为 `running/queued` 时，客户端复用 `GET /api/system/scheduled-job-runs?scheduled_job_id=<scheduled_job_id>` 查询同一运行 ID 并刷新状态、导入记录、错误信息和 `result_summary.execution_nodes`，从未完成节点中展示“执行进度：数据连接/AI 执行器/AI处理/结果动作（状态）”；即使 `status` 仍是 `running/queued`，只要 `result_summary.execution_nodes`、`plugin_invocation_log_id` 或 `updated_at` 等追踪字段发生变化，也必须刷新运行卡片；终态后停止轮询；该追踪不需要新增助手 API。

run-once 草案兜底与执行权限一致：管理员、`system.admin`、`system.scheduled_jobs.run` 或 `system.scheduled_jobs.manage` 用户在未命中唯一可执行周反馈洞察作业时都应收到待确认服务端草案，缺少权限才返回 `assistant.scheduled_job_run summary.status=permission_denied`。当前端收到 `assistant.scheduled_job_run` 且没有 `run_id/items[]` 时，若 `summary.status` 为 `permission_denied`、`needs_scheduled_job_reference`、`needs_single_reference` 或 `failed`，必须展示“执行状态”卡片，说明本次尚未执行、所需权限或运行未创建原因。

当聊天消息包含“邮件摘要”“邮件收取”“邮箱摘要”“email digest”等意图，并明确要求生成定时作业草案时，`message.tool_results[]` 必须返回 `tool=assistant.action_draft`、`intent=email_digest_job_draft`。草案项 `client_draft_id=assistant_draft_email_digest`、`action=create_scheduled_job`、`title=邮件摘要收取`，payload 复用 `scheduled_job_templates.email_digest` 默认值，至少包含 `job_type=plugin_action_invoke`、`execution_mode=deterministic`、`schedule_type=cron`、`cron_expression=0 8 * * MON-FRI`、`source_system=email`、`plugin_input_mapping.poll_since={{current_date-1}}`，并在存在可用 `receive_email_messages` 动作和同插件邮箱连接时写入 `plugin_action_id` 与 `plugin_connection_id`。草案项必须包含 `wizard_steps[]`，展示数据来源 ready、AI处理 skipped、结果动作 ready、调度策略 ready 和确认执行 pending。该草案同样会持久化为 `assistant_action_drafts`，确认前不创建真实定时作业。

当聊天消息包含“线上日志异常”“日志异常”“online log anomaly”等意图，并明确要求生成定时作业草案时，`message.tool_results[]` 必须返回 `tool=assistant.action_draft`、`intent=online_log_anomaly_job_draft`。草案项 `client_draft_id=assistant_draft_online_log_anomaly_analysis`、`action=create_scheduled_job`、`title=线上日志异常分析`，payload 复用 `scheduled_job_templates.online_log_anomaly_analysis` 默认值，至少包含 `job_type=online_log_ai_analysis`、`execution_mode=ai_generated`、`schedule_type=cron`、`cron_expression=*/30 * * * *`、`source_system=online-log`、`plugin_input_mapping.window_start={{current_date}}`、`plugin_input_mapping.window_end={{now}}`、`result_actions[].type=send_notification`，并在存在可用线上日志动作、同插件连接、active AI角色、active Skill 和 active 模型网关时写入 `plugin_action_id`、`plugin_connection_id`、`agent_id`、`skill_ids` 与 `model_gateway_config_id`。草案项必须包含 `wizard_steps[]`，展示数据来源、AI处理、结果动作、调度策略和确认执行各步骤状态与摘要。该草案同样会持久化为 `assistant_action_drafts`，确认前不创建真实定时作业；草案预览必须提前校验 AI 装配和动作/连接引用。

当聊天消息包含“发布风险分析/版本风险”或“知识库巡检/知识治理”等意图，并明确要求生成草案时，`message.tool_results[]` 必须返回 `tool=assistant.action_draft`，其中发布风险使用 `intent=release_risk_analysis_draft`、`client_draft_id=assistant_draft_release_risk_analysis`，知识库巡检使用 `intent=knowledge_base_inspection_draft`、`client_draft_id=assistant_draft_knowledge_base_inspection`。草案项 `action=create_analysis_draft`，payload 至少包含 `analysis_type`、`title`、`source_module`、`summary` 和 `findings[]`；草案项必须包含 `wizard_steps[]`，统一展示“数据来源、AI处理、结果动作、调度策略、确认执行”五步，其中调度策略状态为 `skipped` 且说明一次性分析草案不创建定时调度，前端分析草案卡片必须展示“配置向导”。确认该草案不会写入业务配置表，而是创建一条 `assistant_action_runs` 记录，`run.result_type=assistant_analysis`、`run.result_id=<draft_id>`，`run.result` 保存确认后的分析摘要、治理项和 `source_draft_id`，便于草案卡片展示“已应用”和后续追踪。

助理动作草案接口：

```http
POST /api/assistant/action-drafts
GET /api/assistant/action-drafts
GET /api/assistant/action-drafts/{draft_id}
PATCH /api/assistant/action-drafts/{draft_id}
POST /api/assistant/action-drafts/{draft_id}/view
POST /api/assistant/action-drafts/{draft_id}/confirm
POST /api/assistant/action-drafts/{draft_id}/cancel
POST /api/assistant/action-drafts/{draft_id}/modification
```

草案任务台列表只返回当前登录用户创建的草案。查询参数支持：

- `action`: `create_rd_task`、`create_ai_skill`、`create_ai_agent`、`create_scheduled_job`、`create_plugin_connection`、`create_plugin_action` 或 `create_analysis_draft`。
- `status`: `pending`、`confirmed`、`cancelled`、`expired` 或 `failed`。
- `validation_status`: `passed`、`warning`、`blocked` 或 `unknown`，来自草案预检结果。
- `keyword`: 匹配草案标题、ID、动作、状态、来源消息和结果资源。
- `created_from` / `created_to`: ISO 日期或时间，按草案创建时间过滤。
- `page` / `page_size` / `sort_by` / `sort_order`: 管理列表统一分页、排序参数，默认按 `updated_at desc`。

响应在通用列表字段外返回 `summary`，包括 `draft_total`、`status_counts`、`validation_counts`、`adoption_rate=confirmed/total`、`resolution_rate=(confirmed+cancelled+expired+failed)/total`、`user_modified_count` 和 `user_modified_rate`。列表行包含 `source_link=/assistant?draft_id=<id>`、`view_count`、`modified_field_count`、`validation_issue_count`、`wizard_step_count`、`result_status/result_type/result_id` 等任务台字段；敏感 payload 仍只能通过详情接口按现有脱敏规则查看。

创建草案请求：

```json
{
  "conversation_id": "conversation_001",
  "source_message_id": "assistant_message_001",
  "client_draft_id": "draft_weekly_feedback",
  "action": "create_scheduled_job",
  "title": "每周用户反馈洞察",
  "risk_level": "high",
  "payload": {
    "name": "每周用户反馈洞察",
    "job_type": "user_feedback_insight_extract",
    "schedule_type": "cron",
    "cron_expression": "0 9 * * MON",
    "timezone": "Asia/Shanghai",
    "knowledge_document_ids": ["knowledge_doc_001"],
    "execution_mode": "ai_generated"
  },
  "metadata_json": {
    "references": [{"type": "knowledge_document", "id": "knowledge_doc_001"}]
  },
  "expires_at": "2026-06-15T18:00:00+08:00"
}
```

草案响应：

```json
{
  "id": "assistant_action_draft_001",
  "client_draft_id": "draft_weekly_feedback",
  "action": "create_scheduled_job",
  "title": "每周用户反馈洞察",
  "risk_level": "high",
  "status": "pending",
  "expires_at": "2026-06-15T18:00:00+08:00",
  "payload": {
    "name": "每周用户反馈洞察",
    "job_type": "user_feedback_insight_extract"
  },
  "metadata_json": {
    "references": [{"type": "knowledge_document", "id": "knowledge_doc_001"}]
  },
  "wizard_steps": [
    {
      "depends_on": [],
      "key": "data_source",
      "status": "ready",
      "summary": "已选择用户反馈数据来源",
      "title": "数据来源"
    },
    {
      "depends_on": ["data_source"],
      "key": "ai_processing",
      "status": "needs_prerequisite",
      "summary": "需要选择 AI角色、Skill 和模型网关",
      "title": "AI处理"
    },
    {
      "depends_on": ["data_source", "ai_processing"],
      "key": "confirm",
      "status": "pending",
      "summary": "确认后创建定时作业",
      "title": "确认执行"
    }
  ],
  "created_by": "user_admin",
  "created_at": "2026-06-14T09:00:00+08:00",
  "updated_at": "2026-06-14T09:00:00+08:00"
}
```

`confirm` 只接受仍处于 `pending` 的草案。若草案 `expires_at <= now()`，服务端先将其置为 `expired` 并返回 `409 DRAFT_EXPIRED`，不得调用领域 service、不得创建 `assistant_action_runs` 或业务资源。确认时必须先按 `payload.assistant_prerequisite_draft_ids` 读取同创建人的已确认前置草案运行结果，把 `ai_skill/ai_agent/plugin_connection/plugin_action` 真实资源 ID 回填到当前草案的 `default_skill_ids`、`agent_id`、`skill_ids`、`connection_id`、`plugin_connection_id(s)` 或 `plugin_action_id(s)` 并重新预检，再走对应领域 service 或助手运行记录执行器：`create_rd_task` 仅支持从 `planned` 且尚无关联任务的需求生成 `product_detail_design` AI 研发任务，预检必须校验 `requirement_id`、产品、版本、需求状态和重复任务，确认后复用需求生成任务 service 写入 `ai_tasks` 并推进需求状态；`create_ai_skill` 以 AI 能力管理权限调用 AI 能力配置 service 写入 `ai_skills`；`create_ai_agent` 以 AI 能力管理权限调用 AI 能力配置 service 写入 `ai_agents`，并重新校验 `brain_app_id`、`model_gateway_config_id` 和 `default_skill_ids`；`create_scheduled_job` 以定时作业管理权限调用 scheduled_jobs service 并把 `config_json.assistant_draft` 写入作业配置；若草案 payload 携带 `config_json.assistant_run_once_request.requested=true`，服务端创建作业后还会触发一次 `manual` 运行，并把公开运行记录嵌入 `run.result.scheduled_job_run`，同时把该运行写入 `assistant_action_run_id`、`assistant_action_draft_id`、`assistant_source_message_id` 和 `triggered_by_assistant=true` 归因字段；`create_plugin_connection` 以插件管理权限调用插件连接 service，`create_plugin_action` 以插件管理权限调用动作 service，`create_analysis_draft` 不写业务配置表，只生成 `assistant_action_runs.result_type=assistant_analysis` 的可追踪结果。确认成功返回 `{"draft": ..., "run": ...}`，`run.result_type/result_id/result` 指向创建出的领域资源或助手分析结果；确认失败不得绕过对应 service/执行器。取消接口只把 `pending` 草案置为 `cancelled` 并记录原因，不产生领域写入；取消过期草案同样返回 `DRAFT_EXPIRED`。`view` 接口接受 `{ "surface": "detail_modal" | "deeplink" }`，只更新草案查看元数据和 `assistant_action_draft.viewed` 审计，不确认草案、不写领域资源；`modification` 接口接受 `{ "modified_fields": ["name", "cron_expression"], "user_modified": true }`，在草案 `metadata_json` 中写入去重后的 `modified_fields`、`user_modified`、`modified_at` 和 `modified_by`，并记录 `assistant_action_draft.modified` 审计事件；该接口不改变草案状态、不确认草案、不写入领域资源，用于前端应用草案后保存前记录用户实际调整字段，支撑 `/api/assistant/metrics` 的用户修改率。前端只能对 `pending` 草案展示确认、取消或应用到配置表单入口；`cancelled`、`expired`、`failed` 等终态草案只能查看详情、查看草案和重新生成，避免绕过服务端草案生命周期。草案创建、确认、取消、查看、修改和过期分别写入 `assistant_action_draft.created`、`assistant_action_draft.confirmed`、`assistant_action_draft.cancelled`、`assistant_action_draft.viewed`、`assistant_action_draft.modified` 和 `assistant_action_draft.expired` 审计事件。

AI 助手草案模板市场：

```http
GET /api/assistant/draft-templates
```

响应：

```json
{
  "data": {
    "items": [
      {
        "available": true,
        "category": "insights",
        "code": "weekly_feedback_insight",
        "dependencies": ["用户反馈数据连接", "反馈洞察 Skill", "用户洞察写入动作"],
        "description": "按周提取用户反馈高价值信息，生成可确认的定时作业草案。",
        "draft_action": "create_scheduled_job",
        "name": "周反馈洞察",
        "prompt": "请帮我生成每周用户反馈洞察定时作业草案，配置数据来源、AI处理、结果动作和调度策略，并在确认后执行一次。",
        "roles": ["product_owner", "admin"],
        "source_module": "用户洞察",
        "target_resource": "scheduled_job",
        "template_version": "v1",
        "wizard_steps": ["数据来源", "AI处理", "结果动作", "调度策略", "确认执行"]
      }
    ],
    "total": 6
  },
  "trace_id": "trace_..."
}
```

模板目录按当前用户角色过滤；管理员可见全部模板。`available=false` 表示模板已进入市场但尚未完整接入直接草案生成链路，前端必须展示状态并禁用直接使用或提示继续补齐依赖；`weekly_feedback_insight`、`code_inspection`、`email_digest`、`online_log_anomaly_analysis`、`release_risk_analysis` 和 `knowledge_base_inspection` 属于已接入草案生成链路的可用模板。模板点击只回填聊天输入框，不直接确认草案、写配置或触发外部动作。

AI 助手效果指标：

```http
GET /api/assistant/metrics?window_days=30&product_id=product_alpha&role=admin&action=create_scheduled_job
```

响应：

```json
	{
	  "data": {
	    "dimensions": {
	      "products": [
	        {
	          "product_id": "product_alpha",
	          "draft_total": 4,
	          "draft_confirmed_count": 3,
	          "message_total": 12,
	          "chat_run_total": 5,
	          "scheduled_job_run_total": 4,
	          "scheduled_job_run_succeeded_count": 3,
	          "scheduled_job_run_failed_count": 1,
	          "draft_adoption_rate": 0.75,
	          "scheduled_job_run_success_rate": 0.75
	        }
	      ],
	      "roles": [
	        {
	          "role": "admin",
	          "draft_total": 5,
	          "message_total": 18,
	          "chat_run_total": 6,
	          "scheduled_job_run_total": 8
	        }
	      ]
	    },
	    "drafts_by_action": [
      {
        "action": "create_scheduled_job",
        "cancelled_count": 0,
        "confirmed_count": 3,
        "expired_count": 0,
        "failed_count": 0,
        "pending_count": 1,
        "total": 4
      }
	    ],
	    "filters": {
	      "action": "create_scheduled_job",
	      "date_from": null,
	      "date_to": null,
	      "product_id": "product_alpha",
	      "role": "admin",
	      "window_days": 30
	    },
	    "summary": {
      "action_run_failed_count": 1,
      "action_run_succeeded_count": 3,
      "action_run_success_rate": 0.75,
      "action_run_total": 4,
      "draft_adoption_rate": 0.6,
      "draft_cancelled_count": 1,
      "draft_confirmed_count": 3,
      "draft_expired_count": 0,
      "draft_failed_count": 0,
      "draft_inferred_viewed_count": 1,
      "draft_pending_count": 1,
      "draft_resolution_rate": 0.8,
      "draft_tracked_viewed_count": 2,
      "draft_total": 5,
      "draft_user_modified_count": 2,
      "draft_user_modified_rate": 0.4,
      "draft_viewed_count": 3,
      "failed_run_repair_rate": 0.5,
      "failed_run_repaired_count": 1,
      "failed_run_total": 2,
      "knowledge_reference_count": 6,
      "knowledge_reference_hit_count": 3,
      "knowledge_reference_hit_rate": 0.75,
      "knowledge_reference_request_count": 4,
      "message_total": 18,
      "reference_total": 10,
      "reference_usage_rate": 0.5,
      "referenced_user_message_count": 4,
      "scheduled_job_run_failed_count": 2,
      "scheduled_job_run_succeeded_count": 6,
      "scheduled_job_run_success_rate": 0.75,
      "scheduled_job_run_total": 8,
      "user_message_total": 8
	    },
	    "trends": {
	      "daily": [
	        {
	          "day": "2026-06-21",
	          "draft_total": 2,
	          "draft_confirmed_count": 1,
	          "message_total": 4,
	          "chat_run_total": 2,
	          "chat_run_succeeded_count": 2,
	          "chat_run_failed_count": 0,
	          "scheduled_job_run_total": 1,
	          "scheduled_job_run_succeeded_count": 1,
	          "scheduled_job_run_failed_count": 0
	        }
	      ],
	      "drafts_by_action_daily": [
	        {
	          "day": "2026-06-21",
	          "action": "create_scheduled_job",
	          "total": 2,
	          "pending_count": 1,
	          "confirmed_count": 1,
	          "cancelled_count": 0,
	          "expired_count": 0,
	          "failed_count": 0
	        }
	      ]
	    },
	    "instrumentation": {
      "notes": [
        {
          "code": "DRAFT_VIEW_TRACKING_ROLLOUT",
          "message": "草案查看指标同时展示上线后埋点和历史推断口径。",
          "severity": "info"
        }
      ],
      "view_metrics": {
        "draft_inferred_viewed_count": 1,
        "draft_tracked_viewed_count": 2,
        "draft_viewed_count": 3
      }
    }
  },
  "trace_id": "trace_..."
}
```

该接口只返回当前登录用户范围内的助手效果数据，`window_days` 可选，范围为 1 到 365；`date_from/date_to` 可传 ISO 日期或时间并与 `window_days` 共同收敛时间窗口；`product_id` 按草案 payload、消息 context、运行 result/config 等可识别产品字段过滤；`role` 只能查询当前用户已有角色，非管理员查询其它角色返回空口径；`action` 按草案 action 过滤。草案采纳率为 `confirmed / draft_total`，草案处理率为 `(confirmed + cancelled + expired + failed) / draft_total`，动作运行成功率为 `succeeded / action_run_total`，定时作业运行成功率为 `scheduled_job_run_succeeded_count / scheduled_job_run_total`，失败修复率为“失败运行被成功 `manual_rerun` 通过 `source_run_id` 引用”的比例，非 `manual_rerun` 的成功运行即使携带 `source_run_id` 也不得计入修复；显式引用使用率为 `带 references 的用户消息 / 用户消息总数`。定时作业运行指标不得按“助手创建或引用过的作业 ID”把该作业后续所有调度运行都归入助手，只能统计 `scheduled_job_runs.triggered_by_assistant=true` 且携带 `assistant_action_run_id`、`assistant_action_draft_id` 或 `assistant_source_message_id` 的运行、用户消息显式引用的具体 `scheduled_job_run`，以及这些运行通过 `source_run_id` 形成的复跑链；响应必须同时返回 `scheduled_job_run_attribution.items[]`，按“助手触发、显式引用、复跑链”解释成功率分母来源。知识引用命中率为“用户在同一会话显式引用的知识对象，后续助手回复也引用该知识对象”的比例；用户修改率只依据草案元数据 `user_modified=true` 或 `modified_fields` 非空统计，前端从助手草案带入定时作业表单并保存时，若最终 payload 与草案初始 payload 在受跟踪字段上有差异，必须先调用 `POST /api/assistant/action-drafts/{draft_id}/modification` 写入该元数据；草案查看漏斗优先依据 `POST /api/assistant/action-drafts/{draft_id}/view` 写入的查看元数据统计，其中 `draft_detail_viewed_count` 只统计 `detail_viewed_at`，`draft_deeplink_viewed_count` 只统计 `deeplink_viewed_at`，`draft_tracked_viewed_count` 表示有真实查看埋点的草案数。为避免历史草案在埋点上线前全部显示为 0，`draft_viewed_count` 采用有效查看口径：真实查看埋点、已确认/取消/失败、存在用户修改或已产生动作运行的草案都计为被有效查看；`draft_inferred_viewed_count` 单独展示其中仅由历史行为推断的数量，`instrumentation.notes[]` 必须说明该口径。`dimensions.products[]` 用于定位不同产品的草案闭环和运行成功率，`dimensions.roles[]` 用于解释当前用户角色口径下的使用情况；`trends.daily[]` 和 `trends.drafts_by_action_daily[]` 用于观察时间段内采纳和草案类型变化。AI 助手工作台侧栏可按需调用该接口展示草案生成数、草案确认率、用户修改率、`@` 引用使用率、作业运行成功率、失败修复率和知识引用命中率，并展示草案状态、草案类型、作业运行成功/失败/总数、失败运行已修复/失败总数、运行归因来源、产品维度、角色维度、趋势和导出入口，便于解释关键比率和定位闭环卡点。接口不返回完整提示词、完整回复、知识正文、密钥或外部调用明文。

指标明细钻取：

```http
GET /api/assistant/metrics/details?metric=draft_total&window_days=30&limit=50
```

响应：

```json
{
  "data": {
    "items": [
      {
        "id": "assistant_action_draft_001",
        "type": "draft",
        "title": "周反馈洞察草案",
        "status": "pending",
        "action": "create_scheduled_job",
        "description": "create_scheduled_job · pending",
        "url": "/assistant?draft_id=assistant_action_draft_001",
        "created_at": "2026-06-20T08:00:00+00:00",
        "updated_at": "2026-06-20T08:00:00+00:00"
      }
    ],
    "metric": "draft_total",
    "title": "草案生成",
    "total": 1,
    "window": {
      "days": 30,
      "label": "最近 30 天"
    }
  },
  "trace_id": "trace_..."
}
```

`metric` 只允许按服务端白名单映射到草案、动作运行、聊天运行、定时作业运行、失败修复、消息引用或知识引用明细；`limit` 范围 1-100，默认 50。明细和 `/api/assistant/metrics` 使用同一套当前用户、`window_days/date_from/date_to/product_id/role/action` 过滤和定时作业助手归因规则；服务端必须按 `limit` 下推构造明细列表，只返回当前页 `items`，同时用同一筛选口径返回匹配 `total`，不得为了展示少量明细而完整展开所有历史记录。响应仅返回脱敏来源元数据和站内入口，不返回完整 prompt、助手完整回复、知识正文、密钥、Header 或外部调用明文。

指标导出：

```http
GET /api/assistant/metrics/export?format=csv&window_days=30&product_id=product_alpha
```

响应：

```json
{
  "data": {
    "content": "section,key,label,value\nsummary,draft_total,草案生成,5\n",
    "content_type": "text/csv",
    "filename": "assistant_metrics.csv",
    "format": "csv"
  },
  "trace_id": "trace_..."
}
```

`format=csv` 用于前端下载，导出 summary、草案类型拆分、产品维度和角色维度；`format=json` 返回与 `/api/assistant/metrics` 同口径结构化 payload。导出接口必须复用 metrics 的权限、时间、产品、角色、动作过滤和脱敏规则。

`conversation_id` 可为空，服务端会创建新会话；也可传入已有会话 ID 继续对话。若传入的会话 ID 已存在但不属于当前用户，接口返回 404；若 ID 不存在，则按当前用户创建该会话以兼容客户端预分配 ID。成功问答会按当前登录用户保存一条 user 消息和一条 assistant 消息，保存内容不进入 `model_gateway_logs`。

当前用户会话列表：

```http
GET /api/assistant/conversations?collapse=true&limit=50&cursor=2026-06-20T03%3A01%3A00%2B00%3A00%7Cconversation_003
```

响应：

```json
{
  "items": [
    {
      "id": "conversation_001",
      "title": "AI Brain 项目现在开发到哪里了？",
      "command_signature": "assistant-command:7d7e...",
      "context_scope": "product:product_001",
      "product_id": "product_001",
      "message_count": 2,
      "last_message_at": "2026-06-03T09:00:00+00:00",
      "created_at": "2026-06-03T09:00:00+00:00",
      "updated_at": "2026-06-03T09:00:00+00:00"
    }
  ],
  "limit": 50,
  "next_cursor": "2026-06-20T03:01:00+00:00|conversation_003",
  "total": 1
}
```

会话列表用于左侧最近对话展示。`collapse` 默认为 `true`，`limit` 范围 1-100，`cursor` 使用上一页 `next_cursor` 原样传回；服务端按 `last_message_at/updated_at desc, id asc` 排序分页。存在下一页时返回 `next_cursor`，不存在时返回 `null` 或省略；`total` 表示本页返回条数，不代表全量历史总数。服务端保存命令式输入时可在内部记录 `source_message_hash`，但公开响应只返回可用于分组解释的 `command_signature` 与 `context_scope`；前端应按返回列表展示，提供“加载更多”，不自行删除历史。对于 `@...执行一次`、`@新建需求 ...` 等重复命令，会话折叠优先使用 `command_signature + context_scope`，避免只按标题合并导致不同产品、不同上下文的同名命令被误折叠；折叠后的分页游标仍必须来自原始排序窗口，避免翻页重复或漏会话。

当前用户会话消息：

```http
GET /api/assistant/conversations/{conversation_id}/messages
```

响应：

```json
{
  "items": [
    {
      "id": "assistant_message_001",
      "role": "user",
      "content": "AI Brain 项目现在开发到哪里了？",
      "run_id": "assistant_chat_run_202606200001",
      "client_request_id": "assistant_chat_run_202606200001",
      "status": "completed"
    },
    {
      "id": "assistant_message_002",
      "role": "assistant",
      "content": "当前已支持按用户保存聊天历史。",
      "run_id": "assistant_chat_run_202606200001",
      "status": "completed",
      "model": "codex-auto-review",
      "references": [
        {
          "id": "task_api",
          "type": "ai_task",
          "title": "AI 助手任务",
          "url": "/delivery/rd-tasks?task_id=task_api"
        }
      ],
      "tool_results": [
        {
          "tool": "assistant.delivery_progress",
          "intent": "delivery_progress",
          "summary": {
            "requirements_total": 1,
            "tasks_total": 1
          },
          "items": []
        }
      ],
      "suggestions": ["查看任务中心"]
    }
  ],
  "total": 2
}
```

历史消息中的 `tool_results` 是展示用安全视图，不等同于原始运行载荷。`assistant.action_draft` 历史项只返回草案展示所需字段和动作白名单内的有限 payload 字段；`api_key`、`auth_config`、`Authorization`、token、password、secret、cookie、private key 等敏感字段必须递归脱敏或移除。若 `preview.diffs[]` 的字段名、路径或标签命中敏感信息，`current`、`previous`、`proposed`、`default`、`value` 等值必须返回 `"***"`，不得在历史恢复、深链加载或模型上下文中泄露密钥和 Header 明文。

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
- 需求支持 `draft | submitted | approved | planned | designing | ready_for_dev | developing | code_reviewing | testing | ready_for_release | released | accepted | rejected | deferred | cancelled | closed` 生命周期；历史 `pending_approval` 和 `task_created` 分别兼容为 `submitted` 和 `designing`。
- `source` 表示需求来源，允许 `business_department | product_planning | user_feedback | internal_research | other`，默认 `business_department`；列表支持按 `source` 筛选和排序。
- `input.product_id` 必填且必须指向启用产品；`input.version_id` 可选，填写时必须指向同产品 `planning` 或 `active` 迭代版本。
- 审批通过调用 `POST /api/requirements/{requirement_id}/approve`。
- 审批通过但未选择迭代版本时进入 `approved` 需求池；已选择或后续补充有效迭代版本时进入 `planned`。
- 批量分配负责人调用 `POST /api/requirements/batch-assign-owner`，批量推进状态调用 `POST /api/requirements/batch-advance-status`，批量排期调用 `POST /api/requirements/batch-schedule`，批量生成任务调用 `POST /api/requirements/batch-generate-tasks`；静态路由必须先于 `/api/requirements/{requirement_id}` 注册，避免被动态详情路由吞掉。
- 只有 `planned` 需求可以调用 `POST /api/requirements/{requirement_id}/generate-task` 或被批量生成任务接口处理。
- 生成产品详细设计任务后需求状态进入 `designing`，后续 AI 任务创建和人工确认会继续推进到 `ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released` 或 `accepted`。需求仍保留原始输入和审批结论。
- 关闭需求后不得再生成新 AI 任务。

生成任务请求体：

```json
{
  "task_type": "product_detail_design"
}
```

规则：

- `task_type` 可选，默认生成 `product_detail_design` 任务。
- v1 MVP 的需求审批流默认只通过该接口生成产品详细设计任务；技术方案任务在产品详细设计确认后生成。
- `code_review` 任务需要已确认技术方案和 GitLab MR / GitHub PR diff 快照，默认通过变更预览/快照流程和低层 `POST /api/ai-tasks` 创建，不由需求审批流一次性自动生成。

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
- `product_id` 必须为启用产品，`version_id` 必须属于该产品且状态为 `planning` 或 `active`；需求管理页目标版本下拉应读取产品版本并过滤 `testing`、`released` 和 `archived`。
- `approved` 需求池需求和 `planned` 已排期需求可以批量更新为目标 `version_id`，状态统一为 `planned`。
- 缺失、重复、跨产品或已进入设计/开发/评审/测试/发布/验收等交付阶段的需求不更新，进入 `skipped` 明细；目标产品或目标版本非法时整个请求返回错误。
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

批量推进状态请求：

```http
POST /api/requirements/batch-advance-status
```

请求体：

```json
{
  "target_status": "ready_for_dev",
  "requirement_ids": ["requirement_001", "requirement_002"],
  "reason": "批量推进到待开发"
}
```

规则：

- 仅 `product_owner`、`rd_owner` 或 `admin` 可调用。
- `target_status` 必须是研发流程允许的前进目标，例如 `planned`、`ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released`、`accepted`、`deferred`、`cancelled` 或 `closed`。
- 只允许从当前状态按配置的研发路径向前推进；终态、重复、缺失或不符合路径的需求不更新，进入 `skipped` 明细。
- 推进到 `planned`、`ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released` 或 `accepted` 等交付链路状态时，需求必须已有 `version_id`；未排期需求返回 `REQUIREMENT_VERSION_REQUIRED`，提示先批量排期或编辑归入版本。
- 批量推进不修改产品、迭代版本、负责人或任务引用；合法项继续处理，不因部分跳过回滚整个批次。
- 成功请求记录一条 `requirement.batch_status_advanced` 审计事件，subject 为 `requirement_status_batch`；每条实际更新的需求另记录 `requirement.updated`，payload 包含 `batch_id`、`from_status`、`to_status` 和 reason。

响应体：

```json
{
  "data": {
    "batch_id": "requirement_status_batch_001",
    "target_status": "ready_for_dev",
    "reason": "批量推进到待开发",
    "updated_count": 2,
    "skipped_count": 1,
    "updated": [
      {
        "id": "requirement_001",
        "status": "ready_for_dev"
      }
    ],
    "skipped": [
      {
        "id": "requirement_003",
        "code": "REQUIREMENT_STATE_INVALID",
        "message": "Requirement cannot be advanced to target status"
      }
    ]
  },
  "trace_id": "trace_xxx"
}
```

批量生成任务请求：

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

规则：

- 仅 `product_owner`、`rd_owner` 或 `admin` 可调用。
- `product_id` 必须为启用产品；请求内需求必须属于该产品且状态为 `planned`。
- 每条合法需求生成一个 draft `product_detail_design` AI 任务，需求 `task_ids` 追加新任务 ID，状态进入 `designing`。
- 缺失、重复、跨产品或非 `planned` 需求不生成任务，进入 `skipped` 明细；合法项继续处理，不因部分跳过回滚整个批次。
- 成功请求记录一条 `requirement.batch_tasks_generated` 审计事件，subject 为 `requirement_task_batch`；每个生成任务沿用 `ai_task.created` 审计，payload 带 `batch_id`、operation 和 reason。

响应体：

```json
{
  "data": {
    "batch_id": "requirement_task_batch_001",
    "product_id": "product_001",
    "reason": "批量进入产品详细设计",
    "generated_count": 2,
    "skipped_count": 1,
    "generated": [
      {
        "requirement_id": "requirement_001",
        "task_id": "task_001",
        "task_status": "draft",
        "task_type": "product_detail_design"
      }
    ],
    "skipped": [
      {
        "id": "requirement_003",
        "code": "REQUIREMENT_STATE_INVALID",
        "message": "Only planned requirements can generate tasks"
      }
    ]
  },
  "trace_id": "trace_xxx"
}
```

生成任务响应：

```json
{
  "data": {
    "id": "requirement_001",
    "status": "designing",
    "task_id": "task_001",
    "task_status": "draft"
  },
  "trace_id": "trace_003"
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

创建任务：

```http
POST /api/ai-tasks
```

请求体：

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

- `title` 必填。
- `requirement_id` 必填，后端从需求解析产品、版本、模块、Git 资源和相关系统上下文并写入任务快照。
- 需求必须已进入交付状态：`planned`、`designing`、`ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release` 或 `released`；创建成功后追加任务到 `task_ids`，并按任务类型推进需求状态。`closed`、`submitted`、`approved`、`rejected` 等状态返回 `409 REQUIREMENT_STATE_INVALID`。
- `task_type = technical_solution` 时，`input.product_detail_design_task_id` 必须指向同一需求、同一产品版本下已完成的 `product_detail_design` 任务。
- `task_type = development_planning`、`automated_testing` 或 `release_readiness` 时，`input.technical_solution_task_id` 必须指向同一需求、同一产品版本下已完成的 `technical_solution` 任务；否则返回 `TECHNICAL_SOLUTION_NOT_CONFIRMED` 或上下文不匹配错误。`release_readiness` 创建时会把源技术方案输出、同产品/版本/需求 Bug、Jenkins 发布记录、线上日志指标和 GitLab 每日代码指标写入 `input_json` 快照；无记录时保存真实空数组。
- `task_type = post_release_analysis` 时，`input.release_readiness_task_id` 必须指向同一需求、同一产品版本下已完成的 `release_readiness` 任务；否则返回 `RELEASE_READINESS_NOT_CONFIRMED` 或上下文不匹配错误。创建时会把源发布评估输出、Jenkins 发布记录、线上日志指标和同产品/版本/需求 Bug 写入 `input_json` 快照；无记录时保存真实空数组。
- `task_type = code_review` 时，`input.gitlab_mr_snapshot_id` 必填；该字段是兼容名，可引用 GitLab MR 或 GitHub PR 快照。快照必须先通过 MR/PR 预览与快照接口生成，并且当前用户必须对快照所属产品 Git 资源具备 Review 权限。
- 后端创建 code_review 任务时只引用已有不可变快照，不在任务创建接口中重复拉取 MR/PR diff。
- code_review 任务只归档 AI Brain 内部 Review 报告，不向 GitLab/GitHub 回写评论、审批状态、request changes、合并状态或分支变更。
- `automated_testing` 任务进入人工确认前不会登记 Bug；人工确认 `approve` 或 `edit-approve` 后，输出中的 `bug_suggestions` 才会生成 `source=ai_auto_test` 的 Bug 记录。
- `post_release_analysis` 任务进入人工确认前不会登记 Bug；人工确认 `approve` 或 `edit-approve` 后，输出中的 `bug_suggestions` 才会生成 `source=ai_post_release` 的 Bug 记录，并记录 `bug.created` 与 `post_release_analysis.bugs_created` 审计事件。
- 前端默认通过已排期需求的 `generate-task` 创建产品详细设计任务，后续阶段才直接调用该低层接口。

响应：

```json
{
  "data": {
    "id": "task_001",
    "status": "draft"
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

启动任务：

```http
POST /api/ai-tasks/{task_id}/start
```

当前实现会先匹配 active 研发执行器策略：若命中 `rd_task_executor_policies`，任务不会装配 Agent/Skill，也不会走模型网关，而是创建关联 `ai_executor_tasks(ai_task_id=<task_id>)`，把任务置为 `running/current_step=waiting_ai_executor`，并返回 `executor_policy_id/executor_task_id/runner_id`；后续由插件管理下的 Codex、Claude Code 或 OpenClaw Runner 认领执行，成功回写后任务进入 `waiting_review/current_step=executor_completed` 并创建待确认 Review，失败/取消/超时进入 `failed` 或 `cancelled`。未命中研发执行器策略时，当前实现会同步运行到下一个人工确认点或失败状态。`draft` 任务可启动；已失败且 `current_step` 为 `model_gateway_failed`、`code_review_executor_failed` 或 `executor_failed` 的任务可用同一 `task_id` 再次调用 start 重试，并记录 `ai_task.retry_started` 审计事件。非 code_review 任务若存在 active/default 的 OpenAI-compatible 模型网关配置且已配置 API Key，启动时调用 `{base_url}/chat/completions` 并要求 `response_format={"type":"json_object"}`；若没有结构化默认配置但设置了 `MODEL_GATEWAY_BASE_URL` 和 `MODEL_GATEWAY_API_KEY`，则使用环境模型网关。缺少可用模型网关或 active/default 配置缺失 API Key 返回 `MODEL_GATEWAY_CONFIG_INVALID`；provider 调用、响应解析或网络失败返回 `MODEL_GATEWAY_FAILED`。code_review 任务通过 `code_review_executor` 执行：默认 `claude_code_skill/code-review` 命令适配器由 `CODE_REVIEW_EXECUTOR_COMMAND` 配置，输入 JSON 通过 stdin 提供，输出必须是包含 `summary`、`risk_level` 和 `findings` 的 JSON 对象，系统会补齐并持久化 executor 元数据；显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 时复用模型网关适配器；默认外部命令为空且存在 active/default 或环境模型网关时，系统会自动使用 `model_gateway` 适配器，并以 MR/PR 快照、技术方案、需求和产品上下文作为 Review 输入。执行器配置缺失、调用失败、超时、响应解析或结构化报告校验失败返回 `CODE_REVIEW_EXECUTOR_FAILED`。这些失败都会把任务置为 `failed`；使用模型网关适配器时保留模型调用元数据日志；任务启动不得生成本地 fallback 输出。
典型响应：
启动权限按任务类型收敛：`product_detail_design` 和 `technical_solution` 仅允许 `product_owner`/`rd_owner`，`code_review` 仅允许 `reviewer`/`rd_owner`；`admin` 可执行全部本地管理操作。

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

命中研发执行器策略时，典型响应为：

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

响应包含 `task_type`、`input`、`output`、`current_step`、`pending_review`、`reviews`、`mock_issues` 和 `knowledge_deposits`。通过需求生成的任务必须在 `input` 中包含：

- `task_type`: AI 任务类型，例如 `product_detail_design`、`technical_solution`、`development_planning`、`code_review`、`automated_testing`、`release_readiness` 或 `post_release_analysis`。
- `requirement_id`: 来源需求 ID。
- `requirement_snapshot`: 任务生成时的需求标题、优先级、背景、目标、约束和审批结论快照。
- `product_context`: 任务生成时的产品、版本、模块和 Git 资源上下文快照。
- `gitlab_mr_snapshot`: `code_review` 任务的兼容命名输入快照，可来自 GitLab MR 或 GitHub PR，包括 provider、project_id 或 project_path、mr_iid/PR number、标题、作者、source/target branch、commit sha 或 diff refs、变更文件摘要、diff 存储引用、Web URL 和快照时间。

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

补充信息提交后任务回到 `draft`，前端或调用方应再次调用 `/start` 继续运行。任务管理页面在待确认弹窗中提供“要求补充”操作，成功后关闭待确认弹窗并刷新列表；`waiting_more_info` 任务在单一“操作”弹窗中提供“提交补充信息”操作，不展示前端兜底数据。

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

批量重试任务：

```http
POST /api/ai-tasks/batch-retry
```

请求体：

```json
{
  "task_ids": ["task_failed_001", "task_failed_002"],
  "reason": "模型网关恢复后批量重试"
}
```

仅 `status=failed` 且 `current_step` 为 `model_gateway_failed` 或 `code_review_executor_failed` 的任务可重试。合法任务复用单任务 `/start` 状态机；成功进入待确认的任务同时出现在 `retried` 和 `updated`，已尝试但模型网关或代码评审执行器仍失败的任务出现在 `retried` 并携带错误码，不可重试、重复或不存在的任务进入 `skipped`。接口写入批次级 `ai_task.batch_retried` 审计，逐任务重试沿用 `ai_task.retry_started`。

响应：

```json
{
  "data": {
    "batch_id": "ai_task_retry_batch_001",
    "reason": "模型网关恢复后批量重试",
    "retried": [
      {
        "id": "task_failed_001",
        "status": "waiting_review",
        "review_id": "review_001",
        "current_step": "interrupt_for_human_review"
      }
    ],
    "retried_count": 1,
    "updated": [
      {
        "id": "task_failed_001",
        "status": "waiting_review",
        "review_id": "review_001",
        "current_step": "interrupt_for_human_review"
      }
    ],
    "updated_count": 1,
    "skipped": [
      {
        "id": "task_done_001",
        "code": "TASK_STATE_INVALID",
        "message": "Task cannot be retried from current status"
      }
    ],
    "skipped_count": 1
  },
  "trace_id": "trace_006c"
}
```

### GitLab MR / GitHub PR 代码 Review

MR 预览：

```http
GET /api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview
```

GitHub PR 列表：

```http
GET /api/devops/github/pull-requests/{repository_id}?state=open&limit=20
```

响应：

```json
{
  "data": {
    "items": [
      {
        "repository_id": "repo_001",
        "project_path": "owner/repo",
        "number": 3,
        "title": "feat: add assistant chat",
        "author": {
          "username": "alice",
          "name": "alice"
        },
        "state": "open",
        "source_branch": "feature/assistant-chat",
        "target_branch": "main",
        "base_sha": "abc123",
        "head_sha": "def456",
        "created_at": "2026-06-03T08:00:00Z",
        "updated_at": "2026-06-03T09:00:00Z",
        "web_url": "https://github.com/owner/repo/pull/3",
        "writeback_allowed": false
      }
    ],
    "total": 1
  },
  "trace_id": "trace_github_list_001"
}
```

`state` 可取 `open`、`closed` 或 `all`，`limit` 范围为 1-100；接口使用产品 GitHub 代码库配置中的 `project_path` 或 `remote_url` 解析 `owner/repo`，并通过只读凭据调用 GitHub API。无可访问 PR 时返回真实空集合；该接口只用于选择 Review 输入，不回写 GitHub。

GitHub PR 预览：

```http
GET /api/devops/github/pull-requests/{repository_id}/{pr_number}/preview
```

响应：

```json
{
  "data": {
    "repository_id": "repo_001",
    "project_path": "owner/repo",
    "mr_iid": 3,
    "title": "feat: add knowledge import",
    "author": "alice",
    "source_branch": "feature/knowledge-import",
    "target_branch": "main",
    "changed_file_count": 8,
    "changed_files_summary": [
      {
        "path": "apps/api/app/main.py",
        "additions": 12,
        "deletions": 3
      }
    ],
    "diff_file_tree": [
      {
        "path": "apps",
        "file_count": 3,
        "additions": 42,
        "deletions": 8
      }
    ],
    "risk_summary": {
      "file_count": 8,
      "largest_file": {
        "path": "apps/api/app/main.py",
        "additions": 12,
        "deletions": 3,
        "line_count": 15
      },
      "risk_level": "low",
      "total_additions": 42,
      "total_deletions": 8,
      "total_changed_lines": 50
    },
    "review_checklist": [
      "确认变更文件归属目标需求和技术方案范围",
      "确认测试覆盖包含主要路径、边界场景和回归风险"
    ],
    "permission_diagnostics": {
      "provider": "github",
      "base_url_configured": true,
      "repository_path_configured": true,
      "credential_ref_configured": true,
      "token_available": true,
      "writeback_allowed": false,
      "writeback_reason": "read_only_review_flow"
    },
    "diff_refs": {
      "base_sha": "abc123",
      "head_sha": "def456"
    },
    "web_url": "https://github.com/owner/repo/pull/3"
  },
  "trace_id": "trace_github_preview_001"
}
```

MR/PR diff 快照是 code_review 任务的唯一输入快照来源。MVP-A 必须支持 GitLab/GitHub 只读仓库绑定、变更预览和 diff 快照生成；MVP-B 在快照基础上创建正式 `code_review` 任务并生成 Review 报告。任务中心前端应先读取产品 Git 资源，再根据 provider 预览 MR 或 PR、展示文件树、变更明细、风险摘要、Review Checklist 和 `permission_diagnostics`，确认后生成快照，最后用兼容字段 `gitlab_mr_snapshot_id` 创建 `code_review` 任务；任务创建接口不得静默重新拉取或覆盖已有快照。后端通过 GitLab API 读取 `GET /api/v4/projects/{project}/merge_requests/{iid}` 和 `.../{iid}/changes`，其中 `project` 来自产品 Git 资源的 `project_path` 或 `project_id`。GitHub API 读取 `GET /repos/{owner}/{repo}/pulls/{number}` 和 `.../files?per_page=100`，其中 `owner/repo` 来自 `project_path` 或 `remote_url`。`remote_url` 用于推导 GitLab base URL 或 GitHub Enterprise base URL，也可由 `GITLAB_BASE_URL` / `GITHUB_BASE_URL` 提供；`credential_ref` 推荐使用环境变量或服务端密钥引用，本地联调可直填只读 token，响应不得返回凭据值。预览响应的 `permission_diagnostics` 只暴露 base URL、仓库路径、凭据引用和 token 可用性等布尔诊断，不返回 token。快照响应会返回 `previous_snapshot`、`diff_change_summary` 和 `snapshot_reused`，用于比较同一 repository + MR/PR number 的上一轮快照。同一 `repository_id + snapshot_hash` 已存在时，快照接口返回已有 snapshot 并记录 `gitlab_mr.snapshot_reused` 或 `github_pr.snapshot_reused`，不得重复入库。MR/PR diff、变更文件数或单文件 diff 行数超过限制时返回 `GITLAB_MR_DIFF_TOO_LARGE`，不创建快照，并记录对应 provider 的 `*.snapshot_failed` 审计事件，payload 包含 `diff_size_bytes`、`diff_limit_bytes`、`changed_file_count`、`changed_file_limit`、`file_diff_line_count`、`file_diff_line_limit`、`file_path`、`mr_iid`、`requirement_id` 和 `technical_solution_task_id`。

生成 MR diff 快照：

```http
POST /api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot
```

生成 GitHub PR diff 快照：

```http
POST /api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot
```

请求体：

```json
{
  "requirement_id": "requirement_001",
  "technical_solution_task_id": "task_tech_001"
}
```

响应：

```json
{
  "data": {
    "id": "mr_snapshot_001",
    "repository_id": "repo_001",
    "mr_iid": 42,
    "changed_file_count": 8,
    "diff_change_summary": {
      "added_files_count": 1,
      "modified_files_count": 2,
      "removed_files_count": 0,
      "added_files": ["apps/web/src/pages/TaskCenter/index.tsx"],
      "modified_files": ["apps/api/app/services/git_review.py"],
      "removed_files": []
    },
    "diff_size_bytes": 48000,
    "diff_limit_bytes": 204800,
    "previous_snapshot": {
      "id": "mr_snapshot_previous",
      "head_sha": "old456",
      "created_at": "2026-05-29T09:00:00Z"
    },
    "snapshot_reused": false,
    "created_at": "2026-05-29T10:00:00Z"
  },
  "trace_id": "trace_gitlab_002"
}
```

查询 Review 报告：

```http
GET /api/ai-tasks/{task_id}/code-review-report
```

响应：

```json
{
  "data": {
    "task_id": "task_review_001",
    "gitlab_mr_snapshot_id": "mr_snapshot_001",
    "executor": {
      "type": "claude_code_skill",
      "name": "code-review"
    },
    "summary": "发现 2 个高风险问题和 3 个中风险问题。",
    "risk_level": "high",
    "findings": [
      {
        "severity": "high",
        "category": "security",
        "file_path": "apps/api/app/routes/import.py",
        "line": 87,
        "message": "文件路径未经过边界校验。",
        "suggestion": "在保存前校验路径位于允许目录内。",
        "confidence": 0.87
      }
    ],
    "human_review": {
      "review_id": "review_001",
      "status": "pending",
      "version": 1
    },
    "archived_at": null,
    "writeback_template": {
      "format": "markdown",
      "title": "AI Brain Code Review: high risk",
      "writeback_allowed": false,
      "writeback_reason": "read_only_review_flow",
      "body": "## AI Brain Code Review 结论\n\n- 报告 ID：report_001\n- 风险等级：high\n- 远端回写：未自动回写，请人工确认后粘贴到 PR/MR 评论区。\n\n### 摘要\n发现 2 个高风险问题和 3 个中风险问题。"
    }
  },
  "trace_id": "trace_review_001"
}
```

`writeback_template` 是只读 Markdown 模板，用于人工复制到 GitLab MR / GitHub PR 评论区；AI Brain 不自动调用远端评论、审批或分支变更接口，`writeback_allowed=false` 必须保持。

约束：

- MR diff 快照不可被 GitLab 后续变更静默覆盖；重新 Review 必须创建新快照或新运行记录。
- PR diff 快照不可被 GitHub 后续变更静默覆盖；重新 Review 必须创建新快照或新运行记录。
- 重复拉取相同仓库的相同 diff 时返回已有快照，并通过 `gitlab_mr.snapshot_reused` 或 `github_pr.snapshot_reused` 保留审计痕迹。
- Review 报告经人工确认或修改后采纳后才可归档为正式结论。
- v1 MVP 不提供 GitLab/GitHub 评论、审批状态、request changes、合并状态或分支变更回写接口。
- 首页 IT 团队看板返回当前业务数据聚合，不返回空集合占位；研发运营看板等未接入真实采集器的接口返回空集合响应，响应必须包含 `items` 和 `total`，不得返回占位状态或伪造统计数据。用户使用指标、用户反馈和迭代规划建议已进入真实业务实现，不再使用空集合替代业务数据。

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

### 知识中心

知识空间和目录：

```http
POST /api/knowledge/spaces
```

```json
{
  "code": "payment",
  "name": "支付知识空间",
  "description": "支付产品研发、排障和运营知识"
}
```

```http
PUT /api/knowledge/spaces/{space_id}/members
GET /api/knowledge/spaces/{space_id}/folders
POST /api/knowledge/spaces/{space_id}/folders
PATCH /api/knowledge/folders/{folder_id}
```

空间成员角色支持 `reader`、`contributor`、`maintainer` 和 `admin`。空间是知识访问边界；目录只承担空间内组织结构，不作为独立安全边界。`PATCH /api/knowledge/folders/{folder_id}` 支持 `name`、`parent_folder_id`、`sort_order` 和 `status=active|archived`，移动目录时必须拒绝跨空间、移动到自身或移动到子孙目录。目录归档按整棵子树生效：父目录归档后，子目录在目录列表中不可见，且不得继续作为新建子目录、上传文档或批量移动文档的目标目录。

导入文档：

```http
POST /api/knowledge/documents
```

```json
{
  "title": "研发需求拆解模板",
  "doc_type": "system",
  "product_id": "product_001",
  "knowledge_space_id": "knowledge_space_001",
  "folder_id": "knowledge_folder_001",
  "content": "# 研发需求拆解模板...",
  "tags": ["研发流程", "任务拆解"],
  "permission_roles": ["rd_owner", "knowledge_owner"]
}
```

上传文件导入：

```http
POST /api/knowledge/documents/upload
```

```json
{
  "knowledge_space_id": "knowledge_space_001",
  "folder_id": "knowledge_folder_001",
  "title": "支付失败排查",
  "filename": "payment-runbook.md",
  "mime_type": "text/markdown",
  "content_base64": "IyDmlK/ku5jlpLHotKUuLi4=",
  "doc_type": "runbook",
  "tags": ["payment", "runbook"],
  "parser_engine": "markdown",
  "chunk_strategy": "parent_child"
}
```

上传接口把原始文件写入配置的 S3-compatible 对象存储，默认私有化部署使用 MinIO；业务事实写入 PostgreSQL 的 `knowledge_documents`、`knowledge_assets` 和 `knowledge_import_jobs`。上传成功后文档进入 `importing`，`active_chunk_set_id` 为空，导入任务进入 `queued`，不会在请求内同步生成 chunk set；应用内 `knowledge_import_worker` 默认在非测试环境启用并自动消费 queued 任务，启动和空闲轮询时都会补偿扫描 repository 中遗漏的 queued 任务，补偿运行沿用导入任务 `created_by` 作为写入归属，确保 `knowledge_chunk_sets.created_by` 仍引用真实系统用户；`APP_ENV=test/testing/pytest` 默认关闭以保持单测可控。响应返回 `document`、原始 `asset` 和 `import_job`。文档资产通过 `GET /api/knowledge/documents/{document_id}/assets` 查询，导入任务通过 `GET /api/knowledge/import-jobs?knowledge_space_id=...&document_id=...&status=...` 查询，两者均先按知识空间或文档读权限过滤。对象预览必须通过 `GET /api/knowledge/assets/{asset_id}/preview` 鉴权代理，不向前端暴露永久对象存储 URL。

导入任务操作：

```http
POST /api/knowledge/import-jobs/{job_id}/run
POST /api/knowledge/import-jobs/{job_id}/retry
POST /api/knowledge/import-jobs/{job_id}/cancel
GET /api/knowledge/import-worker/status
```

后台 worker 会先通过 PostgreSQL repository 对 queued 任务执行原子 claim，写入 `locked_by`、`locked_until` 并递增 `attempt_count`；只有获取租约的 worker 才能继续解析，任务完成、失败、取消或 retry 时必须清理锁字段。worker 会读取原始资产，按 `parser_engine` 生成独立 `parsed_markdown` 资产，再写入新的 `knowledge_chunk_sets` 和 `knowledge_chunks`；成功后切换文档 `active_chunk_set_id`，旧 active chunk set 归档。数据库唯一性以 `document_id + chunk_set_id + chunk_index` 为边界，允许同一文档的历史 chunk set 与当前 chunk set 保留相同 chunk 序号。`ocr_json` 和 `table_json` 解析器会额外写入结构化 `ocr_json` / `table_json` sidecar 资产，`parsed_markdown.metadata.structured_asset_ids` 指向这些结构化资产，chunk metadata 会补充 `page_number`、`image_count`、`image_refs`、`table_count`、`table_index`、`columns`、`source_kind`、`source_asset_type` 和 `structured_asset_id`；`regex_section` 分块会按 Markdown 标题、分隔线、中文章节和英文 Section/Chapter 标记切分，并在 chunk metadata 写入 `chunk_role=regex_section`、`section_title` 和 `split_pattern`；解析资产按 `bucket/object_key` 幂等 upsert，半成功重试不得重复创建同一对象资产。`run` 保留为测试、运维补偿和 worker 关闭场景下的手动触发入口。当前支持 `plain_text`、`markdown`、`pdf_text`、`ocr_json`、`table_json` 解析器和 `simple_text`、`parent_child`、`regex_section` 分块策略。`retry` 只把 failed/cancelled 任务重置为 `queued` 并在 worker 可用时重新入队，不得重复创建文档或原始资产；`cancel` 只能取消 queued/uploaded/failed 任务，状态不允许时返回 `IMPORT_JOB_STATE_INVALID`。`GET /api/knowledge/import-worker/status` 需要管理员或知识维护权限，返回 `enabled/running/worker_id/pending_count/active_job_id/queued_job_ids/processed_count/failed_count`，用于页面或运维检查后台队列状态。可通过 `KNOWLEDGE_IMPORT_WORKER_ENABLED`、`KNOWLEDGE_IMPORT_WORKER_POLL_INTERVAL_SECONDS` 和 `KNOWLEDGE_IMPORT_WORKER_LOCK_TTL_SECONDS` 调整 worker。

分块版本与重解析：

```http
GET /api/knowledge/documents/{document_id}/chunk-sets
GET /api/knowledge/documents/{document_id}/chunks?chunk_set_id=knowledge_chunk_set_001
POST /api/knowledge/documents/{document_id}/chunk-sets/{chunk_set_id}/activate
POST /api/knowledge/documents/{document_id}/reparse
POST /api/knowledge/documents/batch-move
```

`chunk-sets` 返回文档所有分块版本的解析器、分块策略、chunk 数、状态、激活时间、`index_status` 和 `vector_index_error`；`chunks` 返回指定版本的 chunk 内容、`parent_chunk_id` 和 `metadata.chunk_role/heading/section_index/section_title/split_pattern`。`activate` 将历史版本设为 active、归档同文档其他版本，并按目标 chunk set 保存的索引状态恢复文档 `index_status`，不能只根据是否存在 embedding_model 猜测状态；`reparse` 基于原始资产创建新的 queued 导入任务并在 worker 可用时自动处理，只有导入任务成功后才切换 active，失败的新 chunk set 保持 `failed` 且旧 active 继续可检索。`batch-move` 接收 `document_ids` 与 `folder_id`，逐条校验写权限并返回 `updated` 和 `skipped`。

查询文档：

```http
GET /api/knowledge/documents?keyword=研发&knowledge_space_id=knowledge_space_001&folder_id=knowledge_folder_001&doc_type=system&index_status=text_indexed
```

知识文档索引状态支持：`importing | pending_index | text_indexed | vector_indexed | indexed | index_failed | archived`，其中 `indexed` 为历史兼容状态。Embedding 不可用但文本 chunk 成功时进入 `text_indexed`，响应包含 `vector_index_error` 和兼容展示用 `index_error`；基础文本索引失败时进入 `index_failed`。

重试失败索引：

```http
POST /api/knowledge/documents/{document_id}/retry-index
```

`index_failed` 和 `text_indexed` 文档允许重试；重试会清理旧 chunk、重新切片并尝试补建向量。Embedding 成功后进入 `vector_indexed`，Embedding 仍不可用时保持 `text_indexed`，状态不匹配时返回 `KNOWLEDGE_INDEX_STATE_INVALID`。

检索知识：

```http
POST /api/knowledge/search
```

```json
{
  "query": "需求评估规则",
  "top_k": 5,
  "knowledge_space_id": "knowledge_space_001"
}
```

当前响应：

```json
{
  "data": {
    "items": [
      {
        "chunk_id": "doc_001_chunk_001",
        "chunk_index": 1,
        "document_id": "doc_001",
        "title": "研发需求拆解模板",
        "content": "研发需求拆解应包含背景、业务目标...",
        "retrieval_mode": "vector",
        "score": 0.8421,
        "source": {
          "asset_id": "knowledge_asset_001",
          "chunk_id": "doc_001_chunk_001",
          "chunk_set_id": "knowledge_chunk_set_001",
          "doc_type": "manual",
          "folder_id": "knowledge_folder_001",
          "knowledge_space_id": "knowledge_space_001",
          "parent_chunk_id": "doc_001_parent_001",
          "parent_content": "# 研发需求拆解\n研发需求拆解应包含背景、业务目标...",
          "title": "研发需求拆解模板"
        }
      }
    ],
    "total": 1
  },
  "trace_id": "trace_008"
}
```

前端知识中心提供“知识检索”弹窗，提交真实 `/api/knowledge/search` 请求并展示可访问结果的标题、来源、召回模式和内容摘要；后端返回 chunk 级命中结果，权限过滤必须在返回 chunk 前完成。存在可读向量 chunk 且 Embedding 网关可用时查询文本会生成 embedding，并只和 `embedding_config_id`、`embedding_model`、`embedding_dimension` 兼容的 chunk 计算 cosine 相似度，返回 `score` 与 `retrieval_mode=vector`；不兼容、缺失或仅文本索引可用时按关键词检索返回 `retrieval_mode=keyword` 且 `score=null`。启用 `parent_child` 时父块不作为直接命中结果返回，子块命中会在 `source.parent_chunk_id` 和 `source.parent_content` 中补充父块上下文；OCR/Table 导入的命中 chunk metadata 可包含页码、图片数量、图片引用、表格数量、表格序号、列名和结构化解析资产引用。无结果时展示真实空状态，不回退到示例数据。

知识沉淀：

```http
GET /api/knowledge/deposits?status=pending
POST /api/knowledge/deposits/{deposit_id}/approve
POST /api/knowledge/deposits/{deposit_id}/reject
```

采纳请求体：

```json
{
  "title": "需求评估决策案例",
  "content": "修改后的知识内容",
  "tags": ["需求评估", "风险"],
  "permission_level": "rd"
}
```

### 研发与运营数据

GitLab 每日提交和代码质量：

```http
GET /api/devops/gitlab/daily-code-metrics?product_id=product_001&date=2026-05-28
```

当前实现支持按产品、仓库和日期筛选真实登记或导入的 GitLab 每日指标；无指标时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "gitlab_metric_001",
        "product_id": "product_001",
        "repository_id": "repo_001",
        "metric_date": "2026-05-28",
        "commit_count": 18,
        "active_author_count": 5,
        "merge_request_count": 3,
        "changed_files": 42,
        "additions": 860,
        "deletions": 210,
        "quality_score": 86,
        "risk_count": 2,
        "author_metrics": [
          {"author": "alice", "commit_count": 7, "additions": 360, "deletions": 80, "review_issue_count": 1}
        ],
        "status": "collected",
        "source_channel": "manual",
        "created_by": "user_admin",
        "created_at": "2026-05-28T20:10:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_011"
}
```

产品负责人、研发负责人或管理员可登记真实聚合指标：

```http
POST /api/devops/gitlab/daily-code-metrics
Content-Type: application/json

{
  "product_id": "product_001",
  "repository_id": "repo_001",
  "metric_date": "2026-05-28",
  "commit_count": 18,
  "active_author_count": 5,
  "merge_request_count": 3,
  "changed_files": 42,
  "additions": 860,
  "deletions": 210,
  "quality_score": 86,
  "risk_count": 2,
  "author_metrics": [
    {"author": "alice", "commit_count": 7, "additions": 360, "deletions": 80, "review_issue_count": 1}
  ],
  "status": "collected",
  "source_channel": "manual"
}
```

服务端校验产品和 GitLab 仓库处于 active 状态且仓库归属该产品，计数字段不得为负数，`quality_score` 范围为 0-100；写入 `gitlab_daily_code_metrics` 后记录 `gitlab_daily_code_metric.created` 审计事件。

Jenkins 发布记录：

```http
GET /api/devops/jenkins/releases?product_id=product_001&version_id=version_001
```

当前实现支持按产品、版本、状态和环境筛选真实登记或导入的 Jenkins 发布记录；无记录时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "jenkins_release_001",
        "product_id": "product_001",
        "version_id": "version_001",
        "job_name": "rd-brain-deploy",
        "build_id": "build-20260601-001",
        "build_number": 128,
        "environment": "prod",
        "status": "success",
        "trigger_actor": "release-bot",
        "commit_sha": "8f6b7c1",
        "duration_seconds": 420,
        "started_at": "2026-06-01T12:20:00Z",
        "deployed_at": "2026-06-01T12:27:00Z",
        "source_channel": "manual_import",
        "created_by": "user_admin",
        "created_at": "2026-06-01T12:30:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_012"
}
```

产品负责人、研发负责人或管理员可登记真实发布记录：

```http
POST /api/devops/jenkins/releases
Content-Type: application/json

{
  "product_id": "product_001",
  "version_id": "version_001",
  "job_name": "rd-brain-deploy",
  "build_id": "build-20260601-001",
  "build_number": 128,
  "environment": "prod",
  "status": "success",
  "trigger_actor": "release-bot",
  "commit_sha": "8f6b7c1",
  "duration_seconds": 420,
  "started_at": "2026-06-01T12:20:00Z",
  "deployed_at": "2026-06-01T12:27:00Z",
  "source_channel": "manual_import"
}
```

服务端校验产品处于 active 状态且版本归属该产品，archived 版本不得登记发布记录；`status` 只能为 `success`、`failed`、`running` 或 `canceled`，构建编号和耗时不得为负数，部署时间不得早于开始时间；写入 `jenkins_release_records` 后记录 `jenkins_release.created` 审计事件。

研发运营统一聚合列表：

```http
GET /api/devops/operational-metrics?category=Jenkins%20发布&name=deploy&status=success&page=1&page_size=10&sort_by=updated_at&sort_order=desc
```

该接口面向研发运营主列表聚合 GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标，返回统一行字段 `category`、`name`、`value`、`status`、`updated_at` 以及原始上下文字段。支持 `category` 精确筛选，`name` 文本筛选，`status` 精确筛选，`page/page_size` 服务端分页，`sort_by` 支持 `category/id/name/status/updated_at/value`，`sort_order` 支持 `asc/desc`。PostgreSQL 运行时必须通过 repository SQL read model 聚合查询三类来源，并在 SQL 层完成筛选、排序和分页；MemoryStore 仅保留为测试 helper fallback。前端研发运营指标主列表必须调用该接口，不再并发拉取三类原始接口后本地拼装、排序或分页；登记弹窗仍使用各原始 POST 接口写入真实指标。

线上运行日志运营指标：

```http
GET /api/ops/online-log-metrics?product_id=product_001&module_code=checkout&environment=prod&from=2026-06-01T00:00:00Z&to=2026-06-01T01:00:00Z
```

当前实现支持按产品、模块、环境和时间窗口筛选真实登记或导入的线上运行日志聚合指标；无记录时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "online_log_metric_001",
        "product_id": "product_001",
        "module_code": "checkout",
        "environment": "prod",
        "window_start": "2026-06-01T00:00:00Z",
        "window_end": "2026-06-01T01:00:00Z",
        "request_count": 2400,
        "error_count": 12,
        "error_rate": 0.005,
        "p95_latency_ms": 318.5,
        "p99_latency_ms": 640.25,
        "core_event_count": 240,
        "top_errors": [
          {
            "message": "PaymentTimeout",
            "count": 7
          }
        ],
        "anomaly_summary": "checkout error spike after release",
        "status": "collected",
        "source_channel": "manual_import",
        "created_by": "user_admin",
        "created_at": "2026-06-01T01:05:00Z",
        "updated_at": "2026-06-01T01:05:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_013"
}
```

产品负责人、研发负责人或管理员可登记真实线上运行日志聚合指标：

```http
POST /api/ops/online-log-metrics
Content-Type: application/json

{
  "product_id": "product_001",
  "module_code": "checkout",
  "environment": "prod",
  "window_start": "2026-06-01T00:00:00Z",
  "window_end": "2026-06-01T01:00:00Z",
  "request_count": 2400,
  "error_count": 12,
  "p95_latency_ms": 318.5,
  "p99_latency_ms": 640.25,
  "core_event_count": 240,
  "top_errors": [
    {
      "message": "PaymentTimeout",
      "count": 7
    }
  ],
  "anomaly_summary": "checkout error spike after release",
  "status": "collected",
  "source_channel": "manual_import"
}
```

服务端校验产品处于 active 状态，`module_code` 如传入必须属于该产品且模块 active，时间窗口必须满足 `window_end > window_start`；请求数、错误数、核心事件数和延迟不得为负数，错误数不得大于请求数，`status` 只能为 `collected`、`partial` 或 `failed`。`error_rate` 由服务端按 `error_count / request_count` 计算；记录写入 `online_log_metrics` 后记录 `online_log_metric.created` 审计事件。外部线上日志自动采集器仍属后续增强，当前入口用于导入或手工登记真实聚合指标，不生成测试兜底行。

采集运行记录：

```http
GET /api/collectors/runs?collector_type=gitlab_daily_code_metric&product_id=product_001&status=running
```

返回真实采集运行台账；无记录时返回 `items: []` 和 `total: 0`，不返回示例运行：

```json
{
  "data": {
    "items": [
      {
        "id": "collector_run_001",
        "collector_type": "gitlab_daily_code_metric",
        "product_id": "product_001",
        "source_system": "gitlab",
        "status": "running",
        "started_at": "2026-06-01T08:00:00Z",
        "finished_at": null,
        "records_imported": 0,
        "error_message": null,
        "payload_summary": {
          "repository_path": "rd/platform-api"
        },
        "created_by": "user_admin",
        "created_at": "2026-06-01T08:00:00Z",
        "updated_at": "2026-06-01T08:00:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_014"
}
```

产品负责人、研发负责人或管理员可登记运行：

```http
POST /api/collectors/runs
Content-Type: application/json

{
  "collector_type": "gitlab_daily_code_metric",
  "product_id": "product_001",
  "source_system": "gitlab",
  "status": "running",
  "records_imported": 0,
  "payload_summary": {
    "repository_path": "rd/platform-api"
  }
}
```

运行完成或取消时更新状态：

```http
PATCH /api/collectors/runs/collector_run_001
Content-Type: application/json

{
  "status": "succeeded",
  "records_imported": 3
}
```

`collector_type` 只允许 `code_inspection`、`dashboard_snapshot_refresh`、`gitlab_daily_code_metric`、`jenkins_release`、`lifecycle_context_refresh`、`online_log_metric`、`pending_attribution_retry`、`plugin_action_invoke`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；`status` 只允许 `running`、`succeeded`、`failed`、`cancelled`。接口校验、`collector_runs.ck_collector_run_type` 数据库约束和定时作业 `create_collector_run_for_job` 产出的类型必须保持一致，避免 dashboard/lifecycle/plugin/pending 等作业运行时写入采集记录失败。`product_id` 如传入必须指向 active 产品；`source_system` 必须非空；`records_imported` 不得为负数；`failed` 必须提供非空 `error_message`；`succeeded / failed / cancelled` 为终态，不得再转回 `running` 或其他状态。创建和更新分别写入 `collector_run.created` 与 `collector_run.updated` 审计事件。采集运行记录只记录采集尝试和结果，不自动写入 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议业务数据。

AI 能力配置：

```http
GET /api/system/ai-skills?status=active&code=iteration_planning
GET /api/system/ai-agents?brain_app_id=rd_brain&status=active
POST /api/system/ai-skills
POST /api/system/ai-skills/upload?code=iteration_planning&name=迭代规划&version=1.0.0
PATCH /api/system/ai-skills/skill_001
POST /api/system/ai-agents
PATCH /api/system/ai-agents/agent_001
```

Skill 配置至少包含 `code`、`name`、`version`、`input_schema`、`output_schema`、`prompt_template`、`allowed_tools`、`required_context`、`risk_level`、`requires_human_review` 和 `status`。`POST /api/system/ai-skills/upload` 用于上传 zip Skill 文件包，body 为 `application/zip` 原始二进制，query 参数提供 `code`、`name`、`version`、`status`、`risk_level` 和 `requires_human_review`；服务端校验 `skill.yaml` / `SKILL.md`、文件类型白名单、路径安全、包大小和 checksum，响应返回 `source_type=package`、`package_uri`、`package_checksum`、`package_entry`、`package_files`、`package_size_bytes` 和 `manifest`。AI角色（Agent）配置至少包含 `code`、`name`、`brain_app_id`、`model_gateway_config_id`、`system_prompt`、`default_skill_ids`、`execution_policy`、`tool_policy` 和 `status`；第一阶段 AI角色只支持表单配置，不上传 Agent 文件包。只有管理员可创建和修改 AI角色/Skill；响应不得包含模型密钥、外部系统 token 或凭据明文。配置创建、修改、启用、停用和包上传分别写入 `ai_skill.created` / `ai_skill.updated` / `ai_skill.package_uploaded` / `ai_agent.created` / `ai_agent.updated` 审计事件。

定时系统作业：

```http
GET /api/system/scheduled-jobs?job_type=iteration_plan_suggestion_generate&enabled=true
POST /api/system/scheduled-jobs
PATCH /api/system/scheduled-jobs/scheduled_job_001
POST /api/system/scheduled-jobs/scheduled_job_001/run
GET /api/system/scheduled-job-runs?scheduled_job_id=scheduled_job_001&status=failed
POST /api/system/scheduled-job-runs/scheduled_job_run_001/cancel
```

创建定时作业示例：

```json
{
  "name": "每周生成 AI 迭代规划建议",
  "job_type": "iteration_plan_suggestion_generate",
  "enabled": true,
  "schedule_type": "cron",
  "cron_expression": "0 9 * * MON",
  "timezone": "Asia/Shanghai",
  "product_id": "product_001",
  "source_system": "ai-brain",
  "execution_mode": "ai_generated",
  "agent_id": "agent_iteration_planner",
  "skill_ids": ["skill_usage_analysis", "skill_feedback_summary", "skill_iteration_planning"],
  "knowledge_document_ids": ["knowledge_doc_001"],
  "model_gateway_config_id": "model_gateway_config_001",
  "config_json": {
    "planning_cycle": "weekly",
    "evidence_window_days": 14,
    "min_evidence_count": 3
  },
  "max_retry_count": 2,
  "timeout_seconds": 600,
  "lock_ttl_seconds": 900
}
```

`job_type` 首批允许 `gitlab_daily_code_metric_collect`、`jenkins_release_collect`、`online_log_metric_collect`、`user_usage_metric_collect`、`user_feedback_collect`、`user_feedback_insight_extract`、`code_repository_inspection`、`online_log_ai_analysis`、`iteration_plan_suggestion_generate`、`dashboard_snapshot_refresh`、`lifecycle_context_refresh`、`plugin_action_invoke` 和 `pending_attribution_retry`。`execution_mode` 只允许 `deterministic`、`ai_assisted`、`ai_generated`，前端用户侧标签为“AI执行”，其中 `deterministic` 展示为“不调用 AI”。`user_feedback_collect` 表示仅取数采集，不执行平台 Skill/大模型处理；若用户反馈作业同时配置动作、AI 模型、AI角色或 Skills，后端必须按兼容规则归一为 `user_feedback_insight_extract` 并使用 `ai_generated`，避免配置了 AI 链路却静默直通。`iteration_plan_suggestion_generate`、`online_log_ai_analysis` 和 `user_feedback_insight_extract` 属于 AI 必选链路作业，服务端即使收到 `deterministic` 也必须按有效 `ai_generated` 校验并要求 active AI角色（Agent）、active Skills（可取 AI角色默认 Skill）和 active 模型网关（可取 AI角色默认模型网关或作业覆盖项）；缺失时分别返回 `AI_AGENT_REQUIRED`、`AI_SKILL_REQUIRED` 或 `MODEL_GATEWAY_CONFIG_REQUIRED`。`plugin_connection_ids` 和 `plugin_action_ids` 分别表示按顺序配置的多个数据连接和多个动作；服务端会保存到 `config_json.orchestration` 并在响应顶层展开，`plugin_connection_id` 和 `plugin_action_id` 仍取第一项，用于兼容当前动作调用、来源链路和旧客户端。`knowledge_document_ids` 为可选知识引用；配置后运行时必须先按当前用户权限读取可检索知识 chunk，并以 `knowledge_references` 注入 AI角色/Skill 模型请求上下文。`result_actions` 为可选结果写入动作列表；`code_repository_inspection` 使用该字段按顺序执行 `write_code_inspection_report`、`create_bug_for_severe_findings`、`create_task_for_severe_findings`、`send_notification` 等处理，并通过 `config_json.repository_id/branch` 指定扫描仓库和扫描分支。指定 `model_gateway_config_id` 时覆盖 AI角色默认模型网关，但仍必须指向 active 模型网关配置。`cron_expression` 和 `interval_seconds` 按 `schedule_type` 二选一，前端必须紧跟调度方式展示；`source_system` 为内部来源标识，模板或默认值写入 payload，但新增/编辑表单不展示给用户填写；`timezone` 默认 `Asia/Shanghai`。作业创建、修改、启停、手动触发、从运行记录复跑和取消必须写入审计；从现有作业或运行记录快照复制出的新增请求可携带 `config_json.template_source={source_type,source_id,title}`，服务端在 `scheduled_job.created/updated` 审计 payload 中返回 `template_source`，用于追踪作业模板来源；前端必须在复制弹窗、作业列表和运行详情中展示 `template_source`，避免来源仅存在于高级 JSON 或审计里。运行接口 `trigger_type` 允许 `manual`、`manual_rerun` 和 `scheduler`，未传默认 `manual`，非法值返回 `400 VALIDATION_ERROR`；运行记录复跑不新增专用 API，前端读取运行记录的 `scheduled_job_id` 后调用 `POST /api/system/scheduled-jobs/{job_id}/run` 并传入 `{"trigger_type":"manual_rerun","source_run_id":"<历史运行 ID>"}`，成功后展示返回的新运行实例详情；若携带 `source_run_id`，服务端必须校验来源运行存在、属于同一作业且触发类型为 `manual_rerun`，响应和后续运行列表必须返回轻量 `source_run_summary` 便于对比来源运行与本次运行。运行终态审计事件 `scheduled_job_run.succeeded/failed` 的 payload 必须包含 `scheduled_job_id`、可选 `source_run_id`、`job_type`、`product_id`、`status`、`trigger_type`、`records_imported`、`collector_run_id`、可选 `plugin_invocation_log_id` 和 `error_code`，并在存在对应配置时补充 `execution_mode`、`agent_id`、`skill_ids`、`model_gateway_config_id`、`model_gateway_called`、`knowledge_document_ids`、`plugin_code`、`plugin_action_id`、`plugin_action_ids`、`plugin_action_code`、`plugin_connection_id`、`plugin_connection_ids`、`plugin_connection_environment`、`result_action_types` 和 `result_write_target`，用于区分普通手动运行、复跑、调度触发、AI 装配、多环境连接和结果写入目标；审计 payload 不保存完整请求响应、Prompt、模型输出或密钥。

定时作业链路按“数据连接取数 -> AI执行处理 -> 动作写入/通知”理解：作业定义中 `plugin_connection_ids` 表示按顺序配置的数据连接，`execution_mode/model_gateway_config_id/agent_id/skill_ids/knowledge_document_ids` 共同组成 AI执行配置，`plugin_action_ids` 表示按顺序配置的动作模板，`plugin_input_mapping` 表示运行时传给连接/动作的输入参数。`plugin_connection_id` / `plugin_action_id` 是第一项兼容字段。`plugin_output_mapping` 是作业级覆盖项；为空时运行时复用动作模板的 `result_mapping`。插件输出映射第一阶段支持 `records_imported_path` 这类摘要字段映射和 `write_target` 写入目标，真实业务入库仍必须通过对应业务 service 完成。

`plugin_input_mapping`、插件连接 `request_config.query/headers` 和动作 `request_config.query/headers` 支持动态时间 token，保存配置时保留语义 token，运行实例触发时按作业 `timezone` 解析。首批 token 包括 `{{current_date}}` / `{{date}}`（输出 `YYYYMMDD`）、`{{date_iso}}`（输出 `YYYY-MM-DD`）、`{{now}}`、`{{today.start}}`、`{{today.end}}`、`{{yesterday.start}}`、`{{yesterday.end}}`、`{{last_7_days.start}}`、`{{last_7_days.end}}`、`{{last_full_week.start}}` 和 `{{last_full_week.end}}`；日期和时间 token 支持简单天数偏移表达式，例如 `{{current_date-7}}` 表示当前日期前 7 天、`{{today.start-7}}` 表示今天零点前 7 天。历史值 `last_monday_00:00:00` 与 `this_monday_00:00:00` 兼容解析为上一完整自然周起止时间。前端配置默认以官方 `connection_schema` 字段作为业务配置展示，例如 GitHub 连接展示“仓库地址”并自动解析 `owner/repo`，GitLab 连接展示“GitLab 地址”并自动解析 Endpoint、`project_id` 与 `project_path`；schema 管理字段保存到 `request_config.query/headers`，但不重复出现在高级 Params 表格。高级 Params/Headers 仅用于补充额外 API query/header，并在高级模式中提供 JSON 同步和反向应用，避免要求业务用户手写复杂 JSON。连接配置作为公共默认值，动作配置作为具体接口覆盖项；同名 query/header 由动作覆盖连接。动作 `request_config.path` 中的 `{{owner}}`、`{{repo}}`、`{{project_id}}`、`{{api_version}}` 等非时间模板变量可从合并后的连接 query、动作 query 和运行输入中的标量值解析，用于 GitHub/GitLab 官方动作路径。

MaxCompute 每周用户反馈场景使用 `job_type=user_feedback_insight_extract`，数据连接作为普通 HTTP 插件连接保存 endpoint、认证和公共 Params/Headers，结果写入动作通常为 `action_type=http_request` 的自定义 HTTP 动作；请求时间参数优先在连接/动作 Params 中配置，作业级 `plugin_input_mapping` 仅作为兼容和高级覆盖。作业必须选择 `model_gateway_config_id`、`agent_id` 和 `skill_ids`，页面展示为 AI 模型、AI角色和 Skills，可选选择知识引用文档。动作 `result_mapping` 默认包含 `write_target=user_feedback_insights`、`insights_path`、`records_imported_path` 和 `rows_path`，作业 `plugin_output_mapping` 仅用于覆盖。运行顺序为数据连接取数、读取知识引用、模型网关按 AI角色/Skill 处理为结构化 JSON、结果写入。运行成功后 `records_imported` 为实际新增洞察数，`result_summary.plugin.response_summary.json.row_count` 保留源表读取行数摘要；`result_summary.execution_nodes` 必须按 `data_connection`、`skill_processing`、`result_action` 三段保存数据连接获取内容、Skill 处理内容和结果写入反馈内容。`skill_processing.model_gateway_called=true`，并包含 `model_gateway_config_id`、`model_log_id`、`processing_mode=model_gateway_json_transform`、`input.knowledge_references` 和模型输出 JSON 摘要。

代码仓库巡检场景使用 `job_type=code_repository_inspection`，通过 `config_json.repository_id` 绑定产品 Git 仓库，通过 `config_json.branch` 指定扫描分支；`native_full_scan` 使用平台内置本地扫描器，`sync_existing_alerts` 和 `trigger_platform_scan` 使用 `plugin_connection_id` / `plugin_action_id` 调用仓库扫描器、SonarQube、SAST 或自建质量扫描服务。若请求未传 `config_json.branch`，服务端创建、更新和 dry-run 会按仓库 `default_branch` 补齐；运行时插件输入顶层携带 `repository_id/branch`，AI 处理上下文携带 `configured_repository_id/configured_branch`。插件响应推荐返回 `repository_id`、`branch`、`commit_sha`、`risk_level`、`summary` 和 `findings[]`；若响应未返回 `branch`，报告写入使用作业分支或仓库默认分支兜底。每个 finding 至少包含 `rule_id`、`category`、`severity`、`title`、`description`、`file_path`、`line_number` 和 `recommendation`，并推荐包含 `committer_name`、`committer_email`、`committer_username`。动作 `request_config.severity_mapping` 或作业 `config_json.severity_mapping` 可把外部扫描器等级映射为平台 `info/low/medium/high/critical`。示例 `result_actions`：

当 `config_json.scan_mode=native_full_scan` 时，服务端使用内置扫描器在 `CODE_SCAN_WORKDIR` 下维护 `mirrors/` 仓库缓存，并按 repository + branch + commit checkout 到单次运行目录；HTTP(S) 私有仓库使用产品 Git 仓库 `credential_ref` 或 provider 级环境变量 token 通过临时 Git askpass 执行 clone/fetch，API 响应、运行摘要、报告和错误信息不得返回 token 或带凭据 remote_url；扫描 `config_json.scan_rules`，按 `ignore_dirs` / `ignore_rules` 过滤目录和规则，按 `severity_threshold`、`baseline_fingerprints`、`accepted_risk_fingerprints` 和 `ignored_finding_fingerprints` 过滤低级别、历史、已接受或单条忽略问题，按 `incremental_from_commit` 做增量文件扫描，并通过 git blame 回填提交人。该模式不要求 `plugin_connection_id` / `plugin_action_id`，保存请求可传 `null` 或空数组清空插件字段；`repository_ids` 可一次绑定多个同产品仓库并生成多份报告。未传 `scan_mode` 时按 `sync_existing_alerts` 兼容旧插件模式。默认运行先返回 queued，再由后台 worker 执行；运行成功后 `plugin_invocation_log_id` 为空，`result_summary.execution_nodes.native_scan` 返回 `repository_id/branch/commit_sha/files_scanned/lines_scanned/finding_count/scanner_name/scanner_version/rules_version/remote_url_hash/remote_url_summary/artifact_ref/checkout_path_retained/scan_started_at/scan_finished_at/incremental_from_commit/incremental_file_count/suppression_summary/suppressed_finding_count/quality_gate/scan_profile`，`execution_nodes.data_connection.processing_mode=native_full_scan`；多仓库运行还返回 `report_ids/report_count/reports_by_repository`。报告额外返回同名快照字段，以及 `scan_mode/scanner_name/is_full_scan/files_scanned/lines_scanned/rules_loaded/coverage_warning/suppressed_finding_count/suppression_summary/quality_gate/scan_profile/previous_report_id/previous_comparison`；当 `ai_assisted/ai_generated` 对 native 扫描结果做模型归一化时，模型输出可覆盖 `risk_level/summary/findings`，但上述 native 快照字段必须以扫描源结果为准。`GET /api/governance/code-inspections/{report_id}` 额外返回 `scan_summary.coverage/rule_distribution/file_distribution/committer_distribution/quality_gate/previous_comparison/scan_profile/suppression_summary`。`scanner_engines` 可声明 `builtin/gitleaks/semgrep/trivy/npm/pip-audit/dependency-check`，已安装外部引擎会执行并解析 JSON 输出，结果归一为 `scanner_name=<engine>` 的 finding；未安装、超时或输出不可解析时写入 `coverage_warning`，并在 `scan_profile.external_scanner_status` 返回 `configured/executed/skipped/failed` 以及可选原因映射后继续内置扫描。异步运行被取消时，取消接口返回 `status=cancelled`，后台 worker 检测到取消后不得写入代码巡检报告或覆盖取消终态。内置规则当前包括 `secrets.hardcoded_credential` 和 `metadata.internal_address_exposure`，finding 原始证据必须脱敏，不得保存明文密钥。

```json
[
  {"type": "write_code_inspection_report"},
  {"type": "create_bug_for_severe_findings", "severity_threshold": "critical"},
  {"type": "create_task_for_severe_findings", "severity_threshold": "high"},
  {
    "type": "send_notification",
    "channels": ["email", "dingtalk"],
    "recipients": ["quality@example.com"],
    "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=..."
  }
]
```

运行成功后必须创建 `code_inspection_reports` 和 `code_inspection_findings`；报告返回 `scheduled_job_id`、`scheduled_job_run_id`、`plugin_connection_id`、`plugin_action_id`、`plugin_invocation_log_id`、`committer_count`、`committer_summary` 和 `created_task_ids`，finding 返回 `committer_name`、`committer_email`、`committer_username` 和 `created_task_id`，列表接口可用 `committer` 按姓名、邮箱或用户名过滤。达到阈值的问题可创建 `source=code_inspection` 的 Bug，并把 `code_inspection_report_id`、`code_inspection_finding_id`、规则、文件、行号、提交人和 `finding_fingerprint` 写入 Bug evidence；同一仓库、分支、规则、文件、行号和提交人的开放 Bug 不重复创建，运行摘要在 `bug_creation.deduplicated_bug_ids` 返回复用的 Bug。`create_task_for_severe_findings` 会创建 `task_type=code_inspection_remediation` 的 AI 任务，任务 input 保存报告、finding、仓库、文件、行号、规则、严重级别和修复建议，运行摘要在 `task_creation.created_task_ids` 返回任务 ID。通知动作写入 `code_inspection_notifications`，第一阶段只记录邮件/钉钉机器人等发送目标和反馈摘要，不要求实际发出外部网络请求。运行摘要必须包含 `execution_nodes.data_connection`、`code_inspection_report`、`bug_creation`、`task_creation`、`notifications` 和 `result_actions`，方便运行详情按“取数/扫描、写报告、派生 Bug/任务、通知反馈、结果写入状态”查看；运营治理 / 代码巡检详情必须固定展示来源作业、来源运行、数据连接、结果写入动作和插件调用，便于从报告反查定时作业配置与动作执行上下文。

运行实例响应必须包含 `scheduled_job_id`、`collector_run_id`、可选 `source_run_id`、`trigger_type`、`scheduled_for`、`status`、`started_at`、`finished_at`、`records_imported`、`error_code`、`error_message`、`result_summary`、`config_snapshot`、`resolved_agent_snapshot`、`resolved_skill_snapshots`、`resolved_prompt_snapshot`、`tool_policy_snapshot`、`resolved_plugin_snapshot` 和 `plugin_invocation_log_id`；复跑运行若来源存在，还必须返回 `source_run_summary`，字段包括来源运行 `id/status/trigger_type/records_imported/error_code/started_at/finished_at/latency_ms`。任务中心 / 定时作业页面必须支持 `?tab=runs&run_id=<运行 ID>` 深链，加载运行记录后自动切换运行记录页签并打开目标运行详情；若存在 `source_run_summary`，详情页展示“复跑对比”，对比来源运行和本次运行的状态、导入数与来源错误码。`result_summary.execution_nodes.data_connection` 应包含连接 ID、连接环境、明文请求摘要、解析后的输入映射、插件响应摘要、源数据数量、请求方法、请求 URL、HTTP 响应状态和耗时；`runner_execution` 仅在 AI 执行器 Runner 场景出现，应包含 executor type、Runner ID、任务 ID、工作区、任务状态、日志和结果 JSON，Runner 未终态时运行实例保持 `running`；`skill_processing` 应包含 Skill 配置、是否调用模型网关、处理输入、知识引用数量、处理输出、候选结果数量和模型日志 ID；`result_action` 应包含写入目标、写入数量、生成 ID、报告 ID、Bug/任务/通知数量和动作反馈，并复用动作执行 `write_preview`；`task_creation` 应在代码巡检创建整改任务时返回 `created_task_ids`、`records_imported` 和状态；当写入目标为 `email_notifications` 时，`result_action.feedback` 至少返回 `delivery_id`、`delivery_status`、`subject`、`sample_records` 和 `write_preview`，页面摘要展示中文写入目标、投递 ID、投递状态和收件人。运行响应应补齐 `result_summary.trace_graph`，DAG 节点按数据连接、Runner 执行、Skill/AI 处理、结果写入、业务写入、Bug/任务/通知等执行顺序展示 `input/output/duration_ms/retry_count/error`；运行详情可从成功运行调用 `POST /api/system/scheduled-job-runs/{run_id}/template` 反向生成作业模板草稿。模型日志仍只记录 provider、model、purpose、tokens、latency、status 和错误元数据，不保存完整 prompt 或完整输出。插件调用日志按管理员调试场景保存并返回明文请求/响应摘要，便于排查三方系统连接和结果写入问题。`POST /run` 仅创建一次运行实例并进入 `queued/running`，不得直接返回伪造业务结果。

待归属数据队列：

```http
GET /api/attribution/pending-items?status=pending&source_type=user_feedback
```

响应返回 `pending_attribution_items` 结构表中的真实队列项；没有数据时返回 `items: []` 和 `total: 0`，不返回示例队列项：

```json
{
  "data": {
    "items": [
      {
        "id": "pending_attr_001",
        "source_type": "user_feedback",
        "source_system": "feedback-api",
        "collector_run_id": "collector_run_001",
        "raw_subject_id": "feedback-ext-7788",
        "summary": "无法映射到产品的登录失败反馈",
        "raw_payload": {
          "channel": "support"
        },
        "suggested_product_id": null,
        "suggested_module_code": null,
        "confidence": 0.62,
        "status": "pending",
        "resolution_action": null,
        "resolution_note": null,
        "resolved_product_id": null,
        "resolved_module_code": null,
        "resolved_requirement_id": null,
        "resolved_subject_type": null,
        "resolved_subject_id": null,
        "resolved_by": null,
        "resolved_at": null,
        "created_by": "user_admin",
        "created_at": "2026-06-02T08:00:00Z",
        "updated_at": "2026-06-02T08:00:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_015"
}
```

产品负责人、研发负责人或管理员可登记待归属项：

```http
POST /api/attribution/pending-items
Content-Type: application/json

{
  "source_type": "user_feedback",
  "source_system": "feedback-api",
  "collector_run_id": "collector_run_001",
  "raw_subject_id": "feedback-ext-7788",
  "summary": "无法映射到产品的登录失败反馈",
  "raw_payload": {
    "channel": "support",
    "message": "login failed after release"
  },
  "suggested_product_id": null,
  "suggested_module_code": null,
  "confidence": 0.62
}
```

将队列项归属到已有上下文：

```http
POST /api/attribution/pending-items/pending_attr_001/resolve
Content-Type: application/json

{
  "resolution_action": "link_existing_context",
  "resolved_product_id": "product_001",
  "resolved_module_code": "login",
  "resolved_requirement_id": "req_001",
  "resolved_subject_type": "user_feedback",
  "resolved_subject_id": "feedback_001",
  "resolution_note": "已确认属于登录模块反馈"
}
```

忽略噪声数据：

```http
POST /api/attribution/pending-items/pending_attr_002/resolve
Content-Type: application/json

{
  "resolution_action": "ignore_as_noise",
  "resolution_note": "重复导入且无业务归属"
}
```

`source_type` 只允许 `gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；`status` 只允许 `pending`、`resolved`、`ignored`；`resolution_action` 只允许 `link_existing_context` 或 `ignore_as_noise`。`collector_run_id` 如传入必须存在；建议产品和归属产品必须为 active；建议模块和归属模块必须属于对应产品；归属需求必须属于归属产品。`link_existing_context` 必须提交 `resolved_product_id`，可选提交模块、需求或目标业务主体；`ignore_as_noise` 不允许提交任何归属上下文字段。队列项一旦 `resolved` 或 `ignored` 即为终态，重复处理返回 `409 PENDING_ATTRIBUTION_STATE_INVALID`。创建、归属和忽略分别写入 `pending_attribution.created`、`pending_attribution.resolved`、`pending_attribution.ignored` 审计事件。队列处理只记录人工归属结果，不自动生成 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议/需求等业务数据。

### 用户洞察（含迭代规划建议）

用户使用指标：

```http
GET /api/insights/usage-metrics?product_id=product_001&module_code=knowledge&feature_code=search&user_segment=rd&from=2026-05-01T00:00:00Z&to=2026-05-28T23:59:59Z
```

查询响应返回 `user_usage_metrics` 结构表中的真实记录；没有数据时返回真实空集合，不返回伪造使用指标：

```json
{
  "data": {
    "items": [],
    "total": 0
  },
  "trace_id": "trace_016"
}
```

登记使用指标：

```http
POST /api/insights/usage-metrics
```

```json
{
  "product_id": "product_001",
  "module_code": "knowledge",
  "feature_code": "search",
  "user_segment": "rd",
  "window_start": "2026-06-01T00:00:00Z",
  "window_end": "2026-06-01T01:00:00Z",
  "active_users": 32,
  "event_count": 128,
  "conversion_count": 21,
  "conversion_rate": 0.164,
  "avg_duration_seconds": 43.5,
  "bounce_rate": 0.18,
  "error_count": 2,
  "source_channel": "manual_import"
}
```

`POST /api/insights/usage-metrics` 仅允许 `product_owner`、`rd_owner` 或 `admin` 登记真实聚合指标；`product_id` 必须指向 active 产品，`module_code` 如传入必须属于该产品，时间窗口必须满足 `window_end > window_start`，计数类字段必须非负，转化率和跳出率必须在 `0..1`。写入 `user_usage_metrics` 结构表，并记录 `usage_metric.created` 审计事件。外部用户行为自动采集器仍属后续增强；当前入口用于导入或手工登记真实指标，不生成测试兜底行。

用户反馈查询和登记：

```http
GET /api/insights/user-feedback?product_id=product_001&module_code=knowledge&status=open&page=1&page_size=20
POST /api/insights/user-feedback
PATCH /api/insights/user-feedback/{feedback_id}
POST /api/insights/user-feedback/{feedback_id}/convert-requirement
```

登记请求体：

```json
{
  "product_id": "product_001",
  "module_code": "knowledge",
  "feature_code": "search",
  "source_channel": "in_app",
  "feedback_type": "improvement",
  "sentiment": "negative",
  "satisfaction_score": 2,
  "content": "知识检索结果经常找不到最近的方案。",
  "tags": ["search", "relevance"],
  "related_requirement_id": "requirement_001"
}
```

用户洞察统一聚合列表：

```http
GET /api/insights/items?category=用户反馈&summary=迭代版本&status=open&page=1&page_size=10&sort_by=updated_at&sort_order=desc
```

该接口面向用户洞察主列表聚合用户使用指标、用户反馈和 AI 迭代规划建议，返回统一行字段 `category`、`summary`、`owner`、`status`、`updated_at`、`product_id`、`version_id`、`module_code`、`feature_code`，并保留 `feedback_type`、`confidence_level`、`planning_cycle`、`priority` 和 `converted_requirement_id` 等上下文。支持 `category` 精确筛选，`summary` 文本筛选，`status` 精确筛选，`page/page_size` 服务端分页，`sort_by` 支持 `category/id/owner/status/summary/updated_at`，`sort_order` 支持 `asc/desc`。PostgreSQL 运行时必须通过 repository SQL read model 聚合查询三类来源，并在 SQL 层完成筛选、排序和分页；MemoryStore 仅保留为测试 helper fallback。前端用户洞察主列表必须调用该接口，不再并发拉取使用指标、反馈和迭代建议三个原始接口后本地拼装、排序或分页；登记、处理和决策仍使用对应原始写接口。

反馈状态支持：`open | triaged | linked | resolved | archived`。`POST /api/insights/user-feedback` 允许任意已登录用户登记真实反馈；`PATCH /api/insights/user-feedback/{feedback_id}` 仅允许 `product_owner`、`rd_owner` 或 `admin` 更新状态、标签、情绪、评分和处理备注；GET 支持按 `product_id`、`module_code`、`feature_code`、`status` 和 `created_by` 筛选。反馈写入 `user_feedback` 结构表，并记录 `user_feedback.created` / `user_feedback.updated` 审计事件。

反馈转需求请求体：

```json
{
  "product_id": "product_001",
  "version_id": "version_001",
  "module_code": "knowledge",
  "title": "提升知识检索相关性",
  "content": "用户反馈知识检索结果经常找不到最近方案，需要优化召回和排序。",
  "priority": "P1",
  "triage_note": "已确认纳入需求池"
}
```

`POST /api/insights/user-feedback/{feedback_id}/convert-requirement` 仅允许 `product_owner`、`rd_owner` 或 `admin` 操作；`product_id` 必须指向 active 产品，`version_id` 可为空但填写时必须属于同产品，`module_code` 如填写必须属于同产品。接口在同一事务内创建 `requirements` 记录、写入 `source=user_feedback`、更新反馈 `product_id/related_requirement_id/status=linked/triage_note`，并记录 `requirement.created` 与 `user_feedback.linked_requirement` 审计事件。已关联需求的反馈重复转需求返回 409。

迭代规划建议查询和生成：

```http
GET /api/planning/iteration-suggestions?product_id=product_001&planning_cycle=2026Q3&status=suggested
POST /api/planning/iteration-suggestions
```

生成请求体：

```json
{
  "product_id": "product_001",
  "planning_cycle": "2026Q3",
  "version_id": "version_002",
  "module_codes": ["knowledge"],
  "include_evidence": true,
  "constraints": {
    "max_suggestions": 10,
    "available_engineering_capacity": "medium"
  }
}
```

响应摘要：

```json
{
  "data": {
    "items": [
      {
        "id": "suggestion_001",
        "product_id": "product_001",
        "planning_cycle": "2026Q3",
        "title": "提升知识检索相关性",
        "status": "suggested",
        "priority": "P1",
        "priority_score": 86,
        "confidence_level": "medium",
        "recommendation_reason": "用户反馈集中在检索不准，且搜索功能访问量高但转化下降。",
        "business_value": "提升研发人员复用历史方案的效率。",
        "risk_signals": ["conversion_drop", "negative_feedback_spike"],
        "dependencies": ["embedding 模型评估", "索引质量分析"],
        "estimated_effort": "medium",
        "evidence": [
          {
            "subject_type": "user_feedback",
            "subject_id": "feedback_001",
            "summary": "检索结果不相关"
          },
          {
            "subject_type": "bug",
            "subject_id": "bug_001",
            "summary": "搜索排序返回过期方案"
          }
        ]
      }
    ]
  },
  "trace_id": "trace_017"
}
```

迭代规划确认：

```http
POST /api/planning/iteration-suggestions/{suggestion_id}/decide
```

请求体：

```json
{
  "decision": "edited_accepted",
  "edited_title": "优化知识检索召回与排序",
  "edited_scope": "优先处理 Markdown 文档检索相关性，不扩展新文档类型。",
  "comment": "采纳为下阶段 P1 需求",
  "convert_to_requirement": true
}
```

响应摘要：

```json
{
  "data": {
    "id": "suggestion_001",
    "status": "converted_to_requirement",
    "decision": "edited_accepted",
    "converted_requirement_id": "requirement_099"
  },
  "trace_id": "trace_018"
}
```

规则：

- 迭代规划建议状态支持 `draft | suggested | accepted | edited_accepted | rejected | converted_to_requirement`。
- 当前实现中 `POST /api/planning/iteration-suggestions` 基于真实用户反馈和 Bug 证据生成建议；无证据时返回空集合，不生成占位建议，不自动创建正式需求。
- 只有 `product_owner`、`rd_owner` 或 `admin` 可以生成建议和调用 decide 接口。
- 只有 `accepted` 或 `edited_accepted` 且 `convert_to_requirement=true` 时，系统才可以创建正式需求。
- 使用数据不足或反馈样本过少时，响应必须标识 `confidence_level = low` 或等价证据不足字段。

### Bug 管理

查询和登记：

```http
GET /api/bugs?product_id=product_001&version_id=version_001&status=open
POST /api/bugs
POST /api/bugs/batch-update
PATCH /api/bugs/{bug_id}
```

查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| product_id | string | 可选，按产品过滤。 |
| version_id | string | 可选，按迭代版本过滤。 |
| status | string | 可选，按 Bug 状态过滤。 |
| severity | string | 可选，按严重程度过滤。 |
| source | string | 可选，按来源过滤。 |

列表响应中的每条 Bug 除 `product_id`、`version_id` 外，还返回 `version_code`、`version_name` 作为页面展示投影；未关联版本时这两个字段为空。

批量处理请求体：

```json
{
  "bug_ids": ["bug_001", "bug_002"],
  "status": "triaged",
  "severity": "major",
  "assignee": "qa@example.com",
  "reason": "批量分诊给 QA"
}
```

`status`、`severity`、`assignee` 至少提供一个；`status` 仍逐条校验 Bug 状态机，非法状态流转、重复 ID 或不存在的 Bug 不阻塞其他合法记录，而是进入 `skipped` 明细。成功更新的 Bug 写入逐条 `bug.updated` 审计，批次写入 `bug.batch_updated` 审计，响应返回 `batch_id`、`updated_count`、`skipped_count`、`updated` 和 `skipped`。

登记请求体：

```json
{
  "product_id": "product_001",
  "version_id": "version_001",
  "module_code": "knowledge",
  "source": "ai_auto_test",
  "title": "知识检索权限过滤异常",
  "severity": "critical",
  "description": "AI 自动测试发现 viewer 能看到 rd 权限 chunk。",
  "related_task_id": "task_001",
  "reproduce_steps": ["使用 viewer 登录", "搜索受限关键词"],
  "evidence": {
    "test_run_id": "test_run_001"
  }
}
```

状态和枚举：

- 来源：`ai_auto_test | ai_post_release | manual_test`。
- 状态：`open | triaged | needs_info | assigned | fixed | verified | closed | reopened`。
- 严重程度：`blocker | critical | major | minor`。
- AI 自动测试来源缺少 `reproduce_steps` 时初始状态为 `needs_info`；人工登记或带复现步骤的 Bug 初始状态为 `open`。
- 提交 `duplicate_of_bug_id` 时重复 Bug 初始状态为 `closed`，并保留主 Bug 关联，避免重复进入修复队列。
- 状态更新必须符合状态机约束，非法跨越返回 `BUG_STATE_INVALID`；创建和更新均写入 `bug.created` 或 `bug.updated` 审计事件。
- Bug 管理工作台必须从真实 `/api/bugs` 响应映射 `version_code`、`version_name`、`reproduce_steps`、`evidence`、`duplicate_of_bug_id`、`requirement_id` 和 `related_task_id`；列表展示迭代版本并支持按版本名、编码或未关联状态过滤；登记弹窗允许录入复现步骤、对象型证据 JSON、关联需求和关联任务，目标版本选项读取同产品未归档迭代版本，支持 `planning`、`active`、`testing` 和 `released`，过滤 `archived`；编辑弹窗允许维护复现步骤、证据 JSON、状态、处理人和重复归并，重复归并候选仅展示同产品 Bug，来源只读展示，不允许把 AI 自动测试或上线后分析来源在前端改写为人工来源；列表勾选多条 Bug 后可打开“批量处理”，调用 `/api/bugs/batch-update` 更新状态、严重级别或处理人，并展示批量结果。

### 软件研发全流程感知

```http
GET /api/lifecycle/context?subject_type=requirement&subject_id=requirement_001&direction=both&include_risks=true
```

查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| subject_type | string | 起点主体类型。当前支持 `product`、`requirement`、`ai_task`、`human_review`、`code_review_report`、`gitlab_mr_snapshot`、`mock_issue`、`knowledge_deposit`、`audit_event`、`bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；未支持类型必须返回 `VALIDATION_ERROR`。 |
| subject_id | string | 起点主体 ID。 |
| product_id | string | 可选，按产品过滤。 |
| version_id | string | 可选，按版本过滤。 |
| module_code | string | 可选，按模块过滤。 |
| direction | string | `upstream | downstream | both`，默认 `both`。 |
| include_risks | boolean | 是否返回风险信号，默认 true。 |

权限规则：当起点是 `ai_task` 时，读取权限与 AI 任务详情一致；当起点是需求、产品或可解析到任务的审计/证据主体时，返回的下游任务、人工确认、报告、知识沉淀、模拟 Issue、真实运营证据和风险信号必须先过滤掉当前用户无权读取的任务链路。

持久化规则：PostgreSQL 运行时聚合前直接读取 repository source rows；接口会把当前查询范围内计算出的上下游关系边同步到 `lifecycle_context_edges`，把风险信号同步到 `lifecycle_risk_signals`；无关系或无风险时保持真实空集合，不生成兜底记录。

响应摘要：

```json
{
  "data": {
    "subject": {
      "type": "requirement",
      "id": "requirement_001"
    },
    "upstream": [],
    "downstream": [
      {
        "subject_type": "ai_task",
        "subject_id": "task_001",
        "relation_type": "generates",
        "summary": "产品详细设计任务",
        "confidence": 1.0
      }
    ],
    "risk_signals": [
      {
        "risk_type": "critical_bug_open",
        "severity": "critical",
        "source_subject_type": "bug",
        "source_subject_id": "bug_001",
        "impact_summary": "阻塞当前版本发布",
        "recommendation": "先完成修复和验证再进入发布评估"
      }
    ],
    "missing_context": [
      "automated_testing",
      "gitlab_daily_code_metric",
      "jenkins_release",
      "online_log_metric",
      "user_usage_metric",
      "user_feedback",
      "iteration_plan_suggestion"
    ],
    "summary": {
      "downstream_count": 1,
      "missing_context_count": 7,
      "risk_count": 1,
      "upstream_count": 0
    }
  },
  "trace_id": "trace_015"
}
```

### 首页 IT 团队看板

```http
GET /api/dashboard/it-team?product_id=product_001&time_range=7d
```

当前实现返回真实聚合指标，来源于产品、需求、AI 任务、待确认 Review、知识文档、知识沉淀、审计事件、Bug、GitLab 每日指标、Jenkins 发布、线上日志、用户使用、用户反馈和迭代规划建议；PostgreSQL 运行时聚合前直接读取 repository source rows，不再通过 repository read snapshot 承载看板聚合；首页看板属于汇总型视图，允许在 Python 中完成跨主体聚合和展示计算，不强制改为 SQL/物化 read model，但读取来源必须来自 PostgreSQL 派生数据且不得作为写入事实源；其中 AI 任务、待确认 Review 和知识沉淀计数、列表必须先按任务读权限过滤，`product_id` 存在时所有可归属主体必须按产品归属过滤，`time_range` 存在时运营类指标按可解析的日期或时间窗口过滤，并把当前产品/时间窗口聚合结果通过单条 repository 写入同步到 `dashboard_metric_snapshots`。

PostgreSQL 运行时默认启用短 TTL 看板缓存，TTL 由 `DASHBOARD_CACHE_TTL_SECONDS` 控制，默认 30 秒；`DASHBOARD_CACHE_TTL_SECONDS<=0` 时禁用缓存。`GET /api/dashboard/it-team?...&refresh=true` 会清除当前用户角色、产品和时间窗口对应的缓存并重新读取 source rows、重建 snapshot。响应 `data.metadata.dashboard_cache` 必须返回缓存是否启用、是否命中、生成时间、缓存年龄、剩余 TTL、本次接口耗时、慢查询阈值和慢查询标记；接口耗时超过 `DASHBOARD_SLOW_THRESHOLD_MS` 时记录 `slow_dashboard_query` 日志。无数据时返回真实 0 和空数组，不生成占位统计：

```json
{
  "data": {
    "summary": {
      "active_products": 1,
      "requirements": 2,
      "ai_tasks": 1,
      "pending_reviews": 1,
      "knowledge_documents": 1,
      "knowledge_deposits": 0,
      "audit_events": 10,
      "bugs": 1,
      "open_bugs": 1,
      "high_severity_bugs": 1,
      "gitlab_commits": 7,
      "jenkins_releases": 1,
      "online_errors": 12,
      "usage_events": 120,
      "user_feedback": 1,
      "iteration_suggestions": 1
    },
    "bug_status_counts": [
      {"status": "open", "count": 1}
    ],
    "latest_high_severity_bugs": [],
    "gitlab_daily_summary": {
      "metric_count": 1,
      "commit_count": 7,
      "merge_request_count": 2,
      "changed_files": 8,
      "risk_count": 1,
      "average_quality_score": 88.5
    },
    "jenkins_release_status_counts": [
      {"status": "failed", "count": 1}
    ],
    "online_log_summary": {
      "metric_count": 1,
      "request_count": 2400,
      "error_count": 12,
      "error_rate": 0.005,
      "max_p95_latency_ms": 318.5,
      "max_p99_latency_ms": 640.25
    },
    "usage_metric_summary": {
      "metric_count": 1,
      "active_users": 42,
      "event_count": 120,
      "conversion_count": 15,
      "error_count": 2
    },
    "user_feedback_status_counts": [
      {"status": "open", "count": 1}
    ],
    "iteration_suggestion_status_counts": [
      {"status": "suggested", "count": 1}
    ],
    "requirement_status_counts": [
      {"status": "submitted", "count": 1},
      {"status": "designing", "count": 1}
    ],
    "task_status_counts": [
      {"status": "waiting_review", "count": 1}
    ],
    "latest_tasks": [],
    "pending_reviews": [],
    "recent_knowledge_documents": [],
    "recent_audit_events": [],
    "metadata": {
      "dashboard_cache": {
        "age_ms": 0,
        "cache_enabled": true,
        "cache_hit": false,
        "duration_ms": 42,
        "expires_in_ms": 30000,
        "generated_at": "2026-06-05T10:00:00+00:00",
        "slow": false,
        "slow_threshold_ms": 500,
        "ttl_seconds": 30
      }
    },
    "time_range": "7d"
  },
  "trace_id": "trace_014"
}
```

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

### 审计事件

```http
GET /api/audit/events?ai_task_id=task_001
GET /api/audit/events?subject_type=requirement&subject_id=requirement_001
GET /api/audit/events?event_type=review.submitted
GET /api/audit/events?actor_id=user_admin&created_from=2026-05-31T00:00:00Z&created_to=2026-05-31T23:59:59Z
```

查询参数建议：

| 参数 | 类型 | 说明 |
|------|------|------|
| ai_task_id | string | 按 AI 任务过滤。 |
| subject_type | string | 按主体类型过滤，例如 `product`、`requirement`、`ai_task`、`knowledge_document`、`knowledge_deposit`、`user_feedback`、`iteration_plan_suggestion`。 |
| subject_id | string | 按主体 ID 过滤。 |
| event_type | string | 按事件类型过滤。 |
| actor_id | string | 按操作者 ID 过滤。 |
| created_from / created_to | ISO datetime | 按创建时间范围过滤，未带时区时按 UTC 处理。 |

响应：

```json
{
  "data": {
    "items": [
      {
        "id": "audit_001",
        "ai_task_id": "task_001",
        "event_type": "review.submitted",
        "subject_type": "review",
        "subject_id": "review_001",
        "actor_id": "user_001",
        "payload": {
          "review_id": "review_001",
          "action": "approved"
        },
        "sequence": 1,
        "created_at": "2026-05-27T10:00:00Z"
      }
    ]
  },
  "trace_id": "trace_010"
}
```

当前实现按 `sequence DESC` 返回事件。审计列表行内“详情”展示事件主体、操作者、时间和载荷；“链路追踪”优先以 `subject_type + subject_id` 查询 `/api/lifecycle/context`，无可追踪主体时再使用 `ai_task_id` 兜底。

### 执行诊断

```http
GET /api/governance/execution-traces?keyword=scheduled_job_run_001&source_type=scheduled_job_run&status=failed&page=1&page_size=10&sort_by=started_at&sort_order=desc
GET /api/governance/execution-traces/{trace_id}
```

权限：需要 `diagnostics.execution_traces.read`。当前默认授予 `admin`，用于跨定时作业、插件、AI 执行器、模型和审计的管理员级排障。

列表查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| keyword | string | 按链路 ID、根 ID、根类型、标题、摘要或关联 ID 搜索。 |
| source_type | enum | 根类型：`scheduled_job_run`、`plugin_invocation_log`、`ai_executor_task`、`model_gateway_log`、`code_inspection_report`、`audit_event`。 |
| status | enum | 聚合状态：`succeeded`、`failed`、`running`、`queued`、`partial`、`skipped`、`cancelled`、`unknown`。 |
| created_from / created_to | ISO datetime | 按链路开始时间或更新时间过滤，未带时区时按 UTC 处理。 |
| sort_by | enum | `started_at`、`updated_at`、`duration_ms`、`node_count`、`failed_node_count`、`root_type`、`status`、`id`。 |
| sort_order | enum | `asc` 或 `desc`。 |
| page / page_size | number | 页码与每页数量，`page_size` 最大 100。 |

响应示例：

```json
{
  "data": {
    "items": [
      {
        "id": "scheduled_job_run_001",
        "root_id": "scheduled_job_run_001",
        "root_type": "scheduled_job_run",
        "title": "定时作业运行 scheduled_job_run_001",
        "summary": "代码仓库质量安全规范巡检完成。",
        "status": "succeeded",
        "started_at": "2026-06-20T01:00:00+00:00",
        "updated_at": "2026-06-20T01:00:08+00:00",
        "duration_ms": 8000,
        "node_count": 8,
        "failed_node_count": 0,
        "running_node_count": 0,
        "related_ids": {
          "plugin_invocation_log": ["plugin_invocation_log_001"],
          "ai_executor_task": ["ai_executor_task_001"],
          "model_gateway_log": ["model_gateway_log_001"],
          "code_inspection_report": ["code_inspection_report_001"],
          "audit_event": ["audit_001"]
        }
      }
    ],
    "total": 1
  },
  "trace_id": "trace_010"
}
```

详情响应在列表字段基础上返回：

- `nodes[]`：包含 `id/source_type/source_id/label/status/summary/error_message/started_at/finished_at/duration_ms/metadata`。
- `edges[]`：包含 `from/to/label`，用于展示调用、派发、写报告、审计等依赖关系。

规则：

- 详情 `trace_id` 可传链路根 ID，也可传任一关联对象 ID 或节点 `source_id`；服务端会返回同一条聚合链路。
- 聚合来源是现有结构表或 repository source rows；PostgreSQL 运行时会刷新可重建的 `execution_trace_snapshots` 只读快照并优先从该表分页/过滤/排序读取。该表不是新的业务事实源，也不在查询时写审计。
- 元数据返回前必须按敏感键脱敏，包含但不限于 `token`、`api_key`、`authorization`、`password`、`secret`、`cookie`；敏感值统一替换为 `<redacted>`。
- 无匹配链路返回 `404 EXECUTION_TRACE_NOT_FOUND`；非法枚举或时间格式返回 `400 VALIDATION_ERROR`。

---

## 核心接口错误语义

| 接口/动作 | HTTP 状态 | 错误码 | 可重试 | 审计要求 | 前端处理建议 |
|-----------|-----------|--------|--------|----------|--------------|
| POST `/api/ai-tasks` 创建任务 | 400 | VALIDATION_ERROR / PRODUCT_VERSION_ARCHIVED | 否 | 写入校验失败审计可选，成功必须审计。 | 标出无效字段或提示选择有效产品版本。 |
| POST `/api/ai-tasks/{task_id}/start` | 409 | TASK_STATE_INVALID | 否 | 记录启动失败和当前状态。 | 刷新任务详情并禁用不可用动作。 |
| POST `/api/ai-tasks/{task_id}/start` | 400 | MODEL_GATEWAY_CONFIG_INVALID | 否 | 记录任务失败和配置缺陷，不记录密钥明文。 | 提示管理员补齐 active/default 模型网关密钥或配置。 |
| POST `/api/ai-tasks/{task_id}/start` | 502/503 | MODEL_GATEWAY_FAILED | 是 | 记录模型网关失败、provider、model、purpose 和 trace_id。 | 展示可重试提示，不展示完整 prompt 或输出。 |
| POST `/api/system/model-gateway-configs/test` | 400 | MODEL_GATEWAY_CONFIG_INVALID / VALIDATION_ERROR | 否 | 记录可选；不得记录密钥明文。 | 提示补齐 base_url、API Key、Chat 模型和 Embedding 模型。 |
| POST `/api/system/model-gateway-configs/test` | 200 | `ok=false`，检测段返回 MODEL_GATEWAY_CHAT_FAILED / MODEL_GATEWAY_EMBEDDING_FAILED | 是 | 写入 `model_gateway_config.tested`，只记录 provider 和测试状态。 | 展示失败段、模型和错误码，不自动保存配置。 |
| GET `/api/ai-tasks/{task_id}` | 403/404 | FORBIDDEN / NOT_FOUND | 否 | 无权限访问不写高频审计，安全审计可采样记录。 | 显示无权限或不存在，不泄露敏感主体。 |
| POST `/api/reviews/{review_id}/approve` | 409 | REVIEW_VERSION_CONFLICT | 是，刷新后重试 | 记录冲突事件和提交 version。 | 提示确认内容已变化，刷新后重新决策。 |
| POST `/api/reviews/{review_id}/edit-approve` | 400/409 | VALIDATION_ERROR / REVIEW_VERSION_CONFLICT | 视错误而定 | 成功和冲突均记录。 | 保留用户编辑内容，刷新后允许重新提交。 |
| POST `/api/reviews/{review_id}/reject` | 400 | VALIDATION_ERROR | 否 | 成功必须记录 rejection reason。 | 要求填写驳回原因。 |
| POST `/api/reviews/{review_id}/request-more-info` | 400 | VALIDATION_ERROR | 否 | 成功必须记录补充问题。 | 要求填写明确问题。 |
| GET GitLab MR preview | 400/404/502/503 | VALIDATION_ERROR / NOT_FOUND / DEVOPS_SOURCE_UNAVAILABLE | 视上游错误而定 | 成功预览记录 `gitlab_mr.previewed`；失败不要求审计，可按安全策略采样记录。 | 提示检查项目绑定、MR IID、只读凭据和上游可用性。 |
| GET GitHub PR preview | 400/404/502/503 | VALIDATION_ERROR / NOT_FOUND / DEVOPS_SOURCE_UNAVAILABLE | 视上游错误而定 | 成功预览记录 `github_pr.previewed`；失败不要求审计，可按安全策略采样记录。 | 提示检查仓库绑定、PR number、只读凭据和上游可用性。 |
| POST GitLab MR snapshot | 413 | GITLAB_MR_DIFF_TOO_LARGE | 否 | 记录 `gitlab_mr.snapshot_failed`，包含 diff_size_bytes、changed_file_count、file_diff_line_count 和限制。 | 提示拆分 MR 或缩小范围。 |
| POST GitHub PR snapshot | 413 | GITLAB_MR_DIFF_TOO_LARGE | 否 | 记录 `github_pr.snapshot_failed`，包含 diff_size_bytes、changed_file_count、file_diff_line_count 和限制。 | 提示拆分 PR 或缩小范围。 |
| POST GitLab MR / GitHub PR snapshot | 502/503 | DEVOPS_SOURCE_UNAVAILABLE | 是 | 上游不可用不保证审计；diff 超限类失败必须记录 `*.snapshot_failed`。 | 提示稍后重试，保留 MR/PR 输入。 |
| GET `/api/ai-tasks/{task_id}/code-review-report` | 404 | NOT_FOUND | 否 | 不要求审计。 | 显示报告尚未生成或不存在。 |
| code-review 执行器生成报告 | 502/503 | CODE_REVIEW_EXECUTOR_FAILED | 是 | 记录 executor_type、executor_name、阶段和 retryable。 | 显示执行器失败，可重跑或联系管理员。 |
| POST `/api/knowledge/documents` | 400 | VALIDATION_ERROR | 否 | 成功和失败均记录文档来源。 | 标出文件类型、大小或权限错误。 |
| POST `/api/knowledge/search` | 400 | VALIDATION_ERROR | 否 | 可记录 query_hash，不记录原始敏感 query。 | 提示 query 或 top_k 无效。 |
| POST `/api/knowledge/search` | 200 | 无 | 不适用 | 不记录完整 query，记录 result_count 和 latency。 | 无结果时显示空状态，不暗示系统错误。 |
| POST `/api/knowledge/import-jobs/{job_id}/run` | 409 | IMPORT_JOB_STATE_INVALID | 否 | 记录状态冲突和当前任务状态。 | 刷新导入任务列表，只对 queued/failed 任务展示运行。 |
| POST `/api/knowledge/import-jobs/{job_id}/retry` | 409 | IMPORT_JOB_STATE_INVALID | 否 | 记录状态冲突和当前任务状态。 | 只对 failed/cancelled 任务展示重试。 |
| POST `/api/knowledge/import-jobs/{job_id}/cancel` | 409 | IMPORT_JOB_STATE_INVALID | 否 | 记录状态冲突和当前任务状态。 | 只对 queued/uploaded/failed 任务展示取消。 |
| POST `/api/knowledge/documents/{document_id}/chunk-sets/{chunk_set_id}/activate` | 404/409 | NOT_FOUND / KNOWLEDGE_CHUNK_SET_STATE_INVALID | 否 | 记录激活失败和目标 chunk set。 | 刷新分块版本，只有同文档可用版本允许激活。 |
| POST `/api/knowledge/documents/batch-move` | 403/404 | FORBIDDEN / NOT_FOUND | 否 | 成功必须记录批量移动审计；逐条跳过写入 skipped 明细。 | 展示移动成功数量和无权限/不存在跳过项。 |
| POST `/api/knowledge/documents/{document_id}/retry-index` | 409 | KNOWLEDGE_INDEX_STATE_INVALID | 否 | 记录状态冲突。 | 刷新文档状态；只有索引失败时显示重试。 |
| PATCH knowledge deposit review | 409 | KNOWLEDGE_DEPOSIT_STATE_INVALID | 否 | 记录重复审核或状态冲突。 | 刷新候选状态。 |
| GET/POST model gateway configs | 403 | FORBIDDEN | 否 | 记录越权管理尝试。 | 提示需要 admin 权限。 |
| POST model gateway configs | 400 | VALIDATION_ERROR / MODEL_GATEWAY_CONFIG_INVALID | 否 | 记录配置失败，不记录密钥明文。 | 标出 provider、base_url 或 model 配置错误。 |
| GET `/api/audit/events` | 403 | FORBIDDEN | 否 | 安全审计可采样记录。 | 提示无权限查看审计。 |
| GET `/api/audit/events` | 200 | 无 | 不适用 | 查询本身不强制审计。 | 无结果返回空列表。 |
| GET `/api/governance/execution-traces` | 400/403/404 | VALIDATION_ERROR / FORBIDDEN / EXECUTION_TRACE_NOT_FOUND | 否 | 查询本身不强制审计；响应必须脱敏元数据。 | 列表显示空状态或无权限提示；详情不存在时提示刷新运行来源。 |
| PATCH `/api/collectors/runs/{run_id}` | 409 | COLLECTOR_RUN_STATE_INVALID | 否 | 记录已成功的创建或更新审计；非法状态流转不要求写入业务审计。 | 刷新采集运行列表并禁用终态行操作。 |
| POST `/api/attribution/pending-items/{item_id}/resolve` | 409 | PENDING_ATTRIBUTION_STATE_INVALID | 否 | 非法重复处理不要求写入业务审计；成功归属或忽略必须记录审计。 | 刷新待归属队列，并禁用已归属或已忽略项的处理入口。 |

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| VALIDATION_ERROR | 请求参数错误。 |
| UNAUTHORIZED | 未登录、账号密码错误或 Token 无效。 |
| TOKEN_EXPIRED | Token 已过期。 |
| FORBIDDEN | 角色权限不足。 |
| NOT_FOUND | 资源不存在。 |
| PRODUCT_VERSION_NOT_SCHEDULABLE | 目标迭代版本不是 `planning` 或 `active`，不能用于新需求排期。 |
| PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED | 迭代版本状态变更必须走状态推进接口，不能通过普通 PATCH 修改。 |
| PRODUCT_VERSION_STATUS_BLOCKED | 迭代版本推进存在阻塞需求，必须处理阻塞项或在允许的阶段强制推进。 |
| PRODUCT_VERSION_STATUS_INVALID | 迭代版本状态或推进路径非法。 |
| VERSION_BRANCH_REPOSITORY_EXISTS | 同一迭代版本和代码库已经存在分支配置。 |
| VERSION_BRANCH_REPOSITORY_PRODUCT_MISMATCH | 分支配置选择的代码库与迭代版本不属于同一产品。 |
| REQUIREMENT_STATE_INVALID | 当前需求状态不允许该操作。 |
| TASK_STATE_INVALID | 当前任务状态不允许该操作。 |
| TECHNICAL_SOLUTION_NOT_CONFIRMED | 研发扩展任务缺少同需求、同产品版本下已完成技术方案。 |
| RELEASE_READINESS_NOT_CONFIRMED | 上线后分析任务缺少同需求、同产品版本下已完成发布评估。 |
| REVIEW_VERSION_CONFLICT | 人工确认版本冲突。 |
| MODEL_GATEWAY_FAILED | 模型网关调用失败并导致任务失败。 |
| KNOWLEDGE_DEPOSIT_STATE_INVALID | 知识沉淀候选状态不允许该操作。 |
| KNOWLEDGE_INDEX_FAILED | 知识文档索引失败。 |
| KNOWLEDGE_INDEX_STATE_INVALID | 知识文档当前索引状态不允许重试。 |
| IMPORT_JOB_STATE_INVALID | 知识导入任务当前状态不允许运行、重试或取消。 |
| KNOWLEDGE_CHUNK_SET_STATE_INVALID | 知识分块版本状态不允许激活或回滚。 |
| BUG_STATE_INVALID | 当前 Bug 状态不允许该操作。 |
| COLLECTOR_RUN_STATE_INVALID | 当前采集运行终态不允许回退或切换状态。 |
| PENDING_ATTRIBUTION_STATE_INVALID | 当前待归属项已经归属或忽略，不允许重复处理。 |
| DEVOPS_SOURCE_UNAVAILABLE | GitLab、GitHub、Jenkins、线上日志、用户使用或用户反馈数据源不可用。 |
| GITLAB_MR_NOT_FOUND | 内部 GitLab Merge Request 不存在或不可访问。 |
| GITHUB_PR_NOT_FOUND | GitHub Pull Request 不存在或不可访问。 |
| GITHUB_CONFIG_INVALID | GitHub 仓库配置缺少可解析的 owner/repo 或 base URL。 |
| GITHUB_CREDENTIAL_UNAVAILABLE | GitHub 只读凭据未配置或无法解析。 |
| GITLAB_MR_DIFF_TOO_LARGE | MR/PR diff 超过 v1 MVP code_review 处理限制，需要拆分变更或缩小范围。 |
| CODE_REVIEW_EXECUTOR_FAILED | code-review 执行器调用失败。 |
| GITLAB_WRITEBACK_NOT_SUPPORTED | v1 MVP 不支持向 GitLab/GitHub 回写评论、审批状态、request changes、合并状态或分支变更。 |
| PRODUCT_MAPPING_REQUIRED | 采集数据缺少产品归属，无法进入产品级统计。 |
| ITERATION_PLAN_EVIDENCE_INSUFFICIENT | 迭代规划建议证据不足，只能生成低置信度建议。 |
| ITERATION_PLAN_STATE_INVALID | 当前迭代规划建议状态不允许确认、驳回或转需求。 |
| ITERATION_PLAN_CONFIRMATION_REQUIRED | AI 建议必须经过产品负责人确认后才能转为正式需求或进入迭代计划。 |
| LIFECYCLE_SUBJECT_REQUIRED | 全流程感知查询缺少 subject_type/subject_id 或 product_id 等查询起点。 |

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
