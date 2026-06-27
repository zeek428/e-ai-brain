# AI 助手与草案工作台

> 来源：../spec.md 与 ../assistant-workbench-upgrade-design.md。本文承接 AI 助手聊天、草案和效果指标的业务域规格导航。

## 职责边界

- AI 助手是研发和系统配置动作的统一入口，不只回答问题，还生成需要用户确认的配置草案。
- 聊天历史按用户隔离，消息、引用、工具结果和模型调用元数据必须持久化。
- 高影响动作必须先生成 `assistant_action_draft`，确认前不得写真实业务配置。

## 关键数据

- `assistant_conversations`、`assistant_messages`
- `assistant_action_drafts`、`assistant_role_quick_tasks`、`assistant_action_reference_configs`
- `assistant_chat_runs`、`model_gateway_logs`

## 关键 API 与页面

- AI 助手聊天：`/assistant`
- 草案任务台：`/assistant/drafts`
- 引用候选：`/assistant/action-references`
- @ 能力配置：`/system/assistant-action-references`
- 关键接口：`POST /api/assistant/chat`、`GET /api/assistant/conversations`、`GET /api/assistant/action-drafts`、`POST /api/assistant/action-drafts/{draft_id}/confirm`

## 当前落地要求

- 助手回答系统问题时先使用 read-model 工具生成 `tool_results`，覆盖产品、迭代、需求、任务、Review、Bug、代码评审、模型网关和执行诊断。
- 裸 `@` 默认引用候选必须优先保留知识文档、需求、研发任务、定时作业、运行记录、插件动作、插件连接、AI 角色和 Skill；执行诊断来源在具备权限时仍可引用，但不得挤占这些常用对象的首屏均衡展示。
- 执行诊断来源深链进入助手时必须同时带入 `prompt` 和可解析引用上下文；`assistant_chat_run`、`assistant_message`、`model_gateway_log`、`plugin_invocation_log`、`ai_executor_task`、`ai_executor_runner`、`code_inspection_report`、`audit_event` 等来源类型仅在用户具备 `diagnostics.execution_traces.read` 或系统管理员权限时可解析和注入。
- 每次助手聊天运行写入 `assistant_chat_runs` 后，可在执行诊断中心按 `assistant_chat_run` 查看模型网关日志和审计事件链路；用户消息和助手消息仅以 `assistant_message` 节点形式暴露 ID、角色、会话和 run 归属，草案任务台使用 `source_message_id` 跳转来源链路；助手运行状态最近失败和运行诊断卡片中的 `model_gateway_log`、`plugin_invocation_log` 与 `scheduled_job_run` ID 必须跳转统一执行诊断中心；运行状态检测时间必须使用全局统一展示时区和 `YYYY-MM-DD HH:mm` 格式，不得直接使用浏览器本地 `toLocaleTimeString()`；诊断元数据不得包含完整对话、Prompt 或知识正文。
- 聊天运行开始、完成、取消、失败和模型网关调用审计属于 DB-first 写路径：服务层不得直接写 `current_store.assistant_chat_runs` 或调用 `current_store.audit()`，也不得通过 `current_store.audit_events` 切片收集本次审计。聊天运行、会话、消息、模型日志和审计必须通过 `save_assistant_chat_records` 统一写入，MemoryStore 仅作为测试 fallback，PostgreSQL 运行态使用 repository 事务提交。
- 草案卡片必须展示风险、差异、前置依赖、预检状态和确认/取消入口。
- 草案创建、确认、失败、取消、修改、查看和过期属于 DB-first 写路径：服务层不得直接写 `current_store.assistant_action_drafts`、`current_store.assistant_action_runs` 或调用 `current_store.audit()`；助手触发定时作业运行归因不得直接写 `current_store.scheduled_job_runs`。草案、动作运行和审计必须通过 `save_assistant_action_records` 统一写入，MemoryStore 仅作为测试 fallback，PostgreSQL 运行态使用 repository 事务提交。
- 助手历史、动作引用配置和角色快捷任务配置同属 DB-first 收口范围：会话/消息测试 fallback 通过 helper 写入，动作引用配置和快捷任务配置的创建、更新、启停、灰度和删除不得直接调用 `current_store.audit()` 或写配置集合，必须通过 repository 单记录写入或 MemoryStore fallback 同步审计。
- @ 能力配置页必须复用统一管理列表底座，支持标题/关键词/角色/权限/URL 搜索、启停状态筛选、角色筛选、批量启停、横向滚动、表格设置、刷新和本地筛选视图保存；新增/编辑、灰度、删除和审计跳转继续消费 `/api/assistant/action-reference-configs` 系列管理 API，不得在前端维护硬编码动作清单。
- 草案任务台必须支持待确认、失败、已采纳、已修改筛选，并展示采纳率、处理率、用户修改率、继续编辑入口和来源链路入口；列表与详情弹窗的“继续编辑”统一按草案 ID 生成 `/assistant?draft_id=...`，助手页按 `draft_id` 加载草案卡，来源链路继续独立跳转执行诊断。草案任务台列表必须透传远程分页 `performance` 元数据，由统一列表底座展示查询耗时和慢查询提示；PostgreSQL 运行态优先使用草案分页 read model 完成当前用户、动作、状态、时间、关键词、排序和分页，不得读取当前用户全量草案后再分页，实时预检 `validation_status` 筛选可保留服务层兼容路径。摘要指标条、详情弹窗和草案状态/风险/校验展示 helper 必须保持组件化，分别由 `AssistantDraftSummaryStrip`、`AssistantDraftDetailModal` 和 `assistantDraftWorkbenchPresentation` 承接；助手页草案卡中的配置向导、步骤状态、前置草案提示和手动调整入口由 `AssistantDraftWizardBlock` 承接，应用前预检、字段差异、校验问题和修复动作入口由 `AssistantDraftPreviewBlock` 与 `assistantDraftPreviewHelpers` 承接，助手页草案详情弹窗由 `AssistantDraftDetailModal` 承接，页面主文件只保留远程查询、确认/取消和详情打开编排。
- 前端主页面按 hooks 和组件拆分，消息气泡、草案卡、引用选择、运行状态和 Composer 保持独立边界。

## 验收映射

- 详细验收见 [../test-case.md](../test-case.md) 的 AI 助手用例和 [../assistant-workbench-upgrade-design.md](../assistant-workbench-upgrade-design.md)。
