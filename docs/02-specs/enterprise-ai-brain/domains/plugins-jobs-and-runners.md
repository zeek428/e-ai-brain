# 插件、定时作业与执行器

> 来源：../spec.md。本文承接插件管理、定时作业、Runner 和研发执行器策略的业务域规格导航。

## 职责边界

- 插件定义外部系统能力，连接维护环境、Endpoint、认证和公共参数，动作定义请求、变量和结果映射。
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
- 关键接口见 [../api.md](../api.md) 的 plugin、scheduled jobs、AI executor runner 和 RD executor policy 章节。

## 当前落地要求

- 插件页主文件只保留插件、连接、动作和 Runner 编排；插件定义弹窗、插件市场表格、插件表格、连接表格、动作表格、连接新增/编辑弹窗、动作新增/编辑弹窗、连接表单字段、Runner 新增/编辑弹窗、Runner 表单字段、Runner 表格、连接/Runner 诊断展示、系统变量全集、Runner 日志、Runner Token 轮换提示/确认和动作试运行弹窗都应保持组件化；连接/动作/Runner 表单 payload、请求预览、结果映射、schema 回填和助手草案回填统一由 `pluginFormTransformHelpers` 维护，不得继续散落在页面主文件。
- 定时作业页主文件只保留作业配置、运行列表和详情编排；表单分区使用 `ScheduledJobFormSection`，基础信息字段收口到 `ScheduledJobBasicInfoSection`，执行链路预览收口到 `ScheduledJobOrchestrationFlow`，数据连接选择收口到 `ScheduledJobDataConnectionSection`，代码巡检作业的代码仓库配置收口到 `ScheduledJobCodeRepositorySection`，AI 模型、AI角色、Skills 和知识引用字段收口到 `ScheduledJobAiExecutionSection`，写入策略和代码巡检结果动作编辑器收口到 `ScheduledJobActionConfigSection`，调度方式、Cron 表达式和固定间隔字段收口到 `ScheduledJobScheduleConfigSection`，试运行结果与 JSON 预览收口到 `ScheduledJobDryRunResultPanel` 和 `ScheduledJobJsonPreview`，运行详情弹窗收口到 `ScheduledJobRunDetailModal`，运行详情的结果写入记录收口到 `ScheduledJobRunResultWriteRecords`。
- 定时作业运行详情必须优先展示数据连接、AI 执行、结果动作和 Runner 执行链路，失败运行提供修复草案和复跑对比。
- Runner 安装包按操作系统区分，并包含启动、停止、状态查看和卸载说明。
- 连接、动作、Runner 的测试接口只返回脱敏诊断，不泄露 token、API key、完整请求体或完整响应。

## 验收映射

- 详细验收见 [../test-case.md](../test-case.md) 的插件管理、定时作业、Runner 和研发执行器策略用例。
