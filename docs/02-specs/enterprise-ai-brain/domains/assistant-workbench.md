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
- 关键接口：`POST /api/assistant/chat`、`GET /api/assistant/conversations`、`GET /api/assistant/action-drafts`、`POST /api/assistant/action-drafts/{draft_id}/confirm`

## 当前落地要求

- 助手回答系统问题时先使用 read-model 工具生成 `tool_results`，覆盖产品、迭代、需求、任务、Review、Bug、代码评审、模型网关和执行诊断。
- 每次助手聊天运行写入 `assistant_chat_runs` 后，可在执行诊断中心按 `assistant_chat_run` 查看模型网关日志和审计事件链路；用户消息和助手消息仅以 `assistant_message` 节点形式暴露 ID、角色、会话和 run 归属，草案任务台使用 `source_message_id` 跳转来源链路；诊断元数据不得包含完整对话、Prompt 或知识正文。
- 聊天运行开始、完成、取消、失败和模型网关调用审计属于 DB-first 写路径：服务层不得直接写 `current_store.assistant_chat_runs` 或调用 `current_store.audit()`，也不得通过 `current_store.audit_events` 切片收集本次审计。聊天运行、会话、消息、模型日志和审计必须通过 `save_assistant_chat_records` 统一写入，MemoryStore 仅作为测试 fallback，PostgreSQL 运行态使用 repository 事务提交。
- 草案卡片必须展示风险、差异、前置依赖、预检状态和确认/取消入口。
- 草案创建、确认、失败、取消、修改、查看和过期属于 DB-first 写路径：服务层不得直接写 `current_store.assistant_action_drafts`、`current_store.assistant_action_runs` 或调用 `current_store.audit()`；助手触发定时作业运行归因不得直接写 `current_store.scheduled_job_runs`。草案、动作运行和审计必须通过 `save_assistant_action_records` 统一写入，MemoryStore 仅作为测试 fallback，PostgreSQL 运行态使用 repository 事务提交。
- 草案任务台必须支持待确认、失败、已采纳、已修改筛选，并展示采纳率、处理率、用户修改率、继续编辑入口和来源链路入口；列表与详情弹窗的“继续编辑”统一按草案 ID 生成 `/assistant?draft_id=...`，助手页按 `draft_id` 加载草案卡，来源链路继续独立跳转执行诊断。
- 前端主页面按 hooks 和组件拆分，消息气泡、草案卡、引用选择、运行状态和 Composer 保持独立边界。

## 验收映射

- 详细验收见 [../test-case.md](../test-case.md) 的 AI 助手用例和 [../assistant-workbench-upgrade-design.md](../assistant-workbench-upgrade-design.md)。
