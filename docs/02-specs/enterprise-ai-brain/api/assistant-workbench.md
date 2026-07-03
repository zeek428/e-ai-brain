# AI 助手与草案工作台 API

> API 分册。覆盖 AI 助手聊天、引用候选、动作草案、草案模板、助手效果指标和会话历史。主入口见 [../api.md](../api.md)，分册组索引见 [system-governance-and-platform.md](system-governance-and-platform.md)。

### AI 助手聊天

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

助手请求会向模型网关注入服务端生成的 `system_context`，包含当前产品、需求数量、任务数量、最新需求/任务、Git 仓库和默认模型网关配置状态。服务端还会基于用户问题和 read context 生成 `tool_results` 与 `reference_candidates`：`tool_results` 可覆盖 `assistant.delivery_progress`、`assistant.pending_reviews`、`assistant.code_review`、`assistant.iteration`、`assistant.bugs`、`assistant.model_gateway`、`assistant.action_draft`、`assistant.task_creation_guide`、`assistant.scheduled_job_diagnostic` 和 `assistant.plugin_connection_diagnostic`，其中明确询问迭代版本阻塞、下一步行动、版本总览或发布准备时，服务端应直接走 `assistant-deterministic` 确定性回答，不依赖 Chat 模型网关；`assistant.iteration` 工具项除版本需求/任务/Bug 计数外，还必须在当前用户有权限时复用 `GET /api/product-versions/{version_id}/dashboard` 的治理摘要，返回 `blocker_count`、`blockers_by_source`、`dashboard_url`、前三个 `next_actions[]`、`delivery_stage_overview[]` 和 `status_impact`，让助手回答版本阻塞、下一步行动或发布准备问题时与版本总览一致；`reference_candidates` 可覆盖命令面板型 `assistant_action`，以及引用类 `product`、`iteration_version`、`requirement`、`ai_task`、`human_review`、`bug`、`code_review_report`、`knowledge_deposit`、`knowledge_space`、`knowledge_folder`、`knowledge_document`、`knowledge_chunk`，以及管理员、`system.admin` 或对应管理权限可见的 `scheduled_job`、`scheduled_job_run`、`plugin_action`、`plugin_connection`、`ai_agent`、`ai_skill`。引用候选 query 识别类型词时，`新建/新增/创建` 可匹配 `assistant_action`，`定时作业/定时任务` 优先匹配 `scheduled_job`，`运行记录/失败` 优先匹配 `scheduled_job_run`，`知识空间/知识目录` 分别匹配 `knowledge_space` / `knowledge_folder`，避免用户在创建配置、执行一次、失败诊断或知识范围引用前选到错误上下文。若模型未返回有效引用，则优先使用工具结果中的引用兜底，再使用服务端候选引用兜底。`system_context` 只进入模型请求，不写入模型日志；`tool_results` 会随助手消息 metadata 持久化并在聊天响应/历史消息中返回；模型日志以 `purpose=assistant_chat` 记录 provider、model、tokens、latency、status 和 error 等元数据。每次聊天请求都会创建或复用 `assistant_chat_runs` 运行记录，状态为 `running/succeeded/cancelled/failed`；用户消息先按同一 `run_id` 写入 `pending`，成功后用户消息和助手消息置为 `completed`，取消时置为 `cancelled`，失败时写入 `failed/error_code`。`client_request_id` 用于客户端重试、停止生成和审计关联，未传时默认等同 `run_id`。成功审计事件为 `assistant.chat_completed`，取消审计事件为 `assistant.chat_cancelled`，失败审计事件为 `assistant.chat_failed`。

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

当用户泛化发送“新增任务/创建任务/我要建任务”但没有说明任务类型时，`/api/assistant/chat` 必须返回 `tool=assistant.task_creation_guide` 的确定性工具结果，不调用模型网关。`tool_results[0].items[]` 和响应顶层 `suggestions` 必须同时覆盖六类入口：研发任务、定时作业、AI能力配置、动作、代码巡检和反馈洞察；建议文案固定为 `新增研发任务`、`新增定时作业`、`新增AI能力配置`、`新增动作`、`配置代码巡检定时作业`、`配置每周用户反馈洞察定时作业`，便于前端同时展示任务类型卡片和可点击建议按钮；`插件动作` 仅作为旧输入别名继续识别，响应展示不得再返回旧标签。

当管理员询问“插件连接为什么失败/连接失败怎么修/插件连接诊断”且没有创建草案意图时，`/api/assistant/chat` 必须返回 `tool=assistant.plugin_connection_diagnostic` 的确定性工具结果，不调用模型网关。工具项按最近失败或最近测试的插件连接返回 `connection_config/latest_test/repair_suggestions` 三段诊断，字段可包含连接 ID、名称、插件名、环境、endpoint、最近测试状态、失败步骤、错误码、错误信息和结构化修复建议；不得返回 `auth_config`、完整认证 Header、完整请求体或密钥。前端必须展示“插件连接诊断”卡片，并可把 `plugin_connection` 引用加入“本次上下文”继续追问。

显式引用由前端 `@` 选择器提交到聊天请求的可选 `references` 字段，后端不从自然语言中猜测 ID。服务端必须先解析引用、校验当前用户权限和可读状态，再构造脱敏上下文。`knowledge_document` 候选和解析只返回当前用户可读、索引状态可检索的知识文档；聊天时按权限读取有限数量的知识 chunk，注入 `system_context.selected_references` 和 `system_context.knowledge_context`。`knowledge_chunk` 候选和解析只返回当前用户可读、所属文档可检索的知识片段，聊天时只注入被显式选中的单个片段。`scheduled_job`、`scheduled_job_run`、`plugin_action`、`plugin_connection`、`ai_agent` 和 `ai_skill` 属于受控运维配置引用，候选和解析必须要求管理员、`system.admin` 或对象类型对应的管理/执行权限：定时作业和运行记录要求 `system.scheduled_jobs.manage` 或 `system.scheduled_jobs.run`，插件连接和动作要求 `system.plugins.manage`，AI角色和 Skill 要求 `system.ai_capabilities.manage`；定时作业和运行记录还必须按当前用户 `scope_summary` 中的产品 scope 过滤，拥有产品级 scope 的用户不得看到其他产品作业或运行。无对应权限或 scope 时候选返回空集合，解析返回 `404 REFERENCE_NOT_FOUND`。`assistant_action` 属于命令面板动作入口，不属于可解析上下文引用；候选优先读取 `assistant_action_reference_configs`，按 `enabled`、角色、权限、企业、模板版本和 `rollout_json` 灰度策略过滤；同 `action_key` 的配置可覆盖或禁用默认动作，新增 `action_key` 可扩展自定义动作，没有任何配置记录时回退内置默认目录。默认动作覆盖 `新建需求`、`新建 Bug`、`新建插件连接`、`新建动作`、`新建定时作业`、`新建知识文档/导入任务` 和 `新建 AI 能力配置`，并携带 `action/prompt/summary/source_module=动作/permission_label=可执行`；`插件动作` 作为 `create_plugin_action` 的兼容搜索别名保留，但候选标题、Prompt 和建议按钮必须展示为“动作”。前端选择 `assistant_action` 后必须用候选标题生成输入框头部命令前缀（例如 `@新建需求 `、`@新建定时作业 `），并把用户已在当前 `@` 片段之后输入的正文承接在前缀之后；候选 `prompt` 只作为动作说明和草案提示来源，不得直接覆盖用户输入。选择动作后必须关闭候选面板，不得加入本次上下文、不得写入最近引用、不得提交到 `references[]` 或 `/api/assistant/references/resolve`。前端引用类型标签必须把 `assistant_action` 显示为“动作”，把 `plugin_action` 显示为“动作”，把 `ai_task` 显示为“研发任务”，把 `ai_skill` 显示为“Skill”，并在候选分组、类型 Tag、已选引用 Chip 和本次上下文摘要中保持一致。未指定 `type` 的默认候选按引用类型均衡合并，后端在满足 `limit` 的前提下优先为动作入口、知识文档/片段、需求、研发任务、定时作业、运行记录、动作、插件连接、AI角色和 Skill 等类型各返回至少一个可用候选，避免单一类型挤占整个面板；指定 `type` 且查询词为空时，应先按目标类型取足候选再截断，不得被全局默认类型顺序提前截断；`limit` 上限仍为 20，前端裸 `@` 应请求足够数量的默认候选。前端对 `@... 执行一次` 这类 run-once 命令，在候选仍加载或用户直接按 Enter/点击发送时，必须用当前 `@` 文本追加一次 `type=scheduled_job` 候选查询，把可用定时作业引用随 `/api/assistant/chat` 一起提交；查询失败时后端显式 @ 名称解析仍可兜底。未授权、不可读、不可检索或不存在的引用不得进入模型上下文。模型日志继续只保存调用元数据，不保存完整知识正文、完整 prompt、插件密钥或外部系统 token。

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

前端诊断卡片必须把三个阶段分别展示为“数据连接是否成功”“AI处理是否成功”“结果动作是否写入成功”，并将阶段状态转换为成功、失败、执行中、排队中、有告警或已跳过等用户可读判断。各阶段的 `log_id` 只表示安全日志元数据 ID，前端诊断卡片必须展示为“关联日志：<log_id>”，用于继续追踪模型日志或插件调用日志；不得展示完整插件请求/响应、模型 Prompt、模型输出或密钥。多数据连接运行的 `data_connection` 段可额外返回 `connection_count/successful_count/failed_count/log_ids/failed_items`，用于定位哪个连接失败；多结果动作运行的 `result_action` 段可额外返回 `action_count/successful_count/failed_count/write_targets/log_ids/failed_actions/result_write_records`，用于判断同一次运行是否部分写入成功。`result_action` 段的结果写入字段来自与 `/api/system/result-write-records?scheduled_job_run_id=<run_id>` 同源的派生读模型，只返回记录 ID、状态、写入目标和标签等排障元数据。

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

当聊天消息显式引用 `scheduled_job_run` 且问题包含“转洞察草案/转需求草案/转 Bug 草案/业务草案”等意图时，响应中的 `message.tool_results[]` 会包含 `tool=assistant.action_draft`、`intent=scheduled_job_run_business_draft`。草案项使用 `action=create_analysis_draft`，`client_draft_id=assistant_draft_<user_insight|requirement|bug>_<scheduled_job_run_id>`；payload 至少包含 `analysis_type`、`source_module=scheduled_jobs`、`source_reference`、`summary.run_id/scheduled_job_id/run_status/records_imported/result_write_target/result_write_record_id` 和 `findings[]` 节点摘要。服务端会把该工具项持久化为 `assistant_action_drafts`；确认后 `run.result_type=assistant_analysis`，只归档助手分析结果，不直接写入用户洞察、需求或 Bug 表。

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

助理动作草案已通过服务端持久化表和确认接口落地。`assistant.action_draft` 工具结果仍随聊天响应返回，前端助手页渲染为待确认配置草案卡片；服务端会把可支持的 `items[]` 转存为 `assistant_action_drafts` 记录，并在对应工具项上追加 `server_draft_id`、`client_draft_id` 和 `status`。工具项携带的 `wizard_steps[]` 必须写入草案元数据，并由 `GET /api/assistant/action-drafts/{draft_id}` 原样返回，供 `/assistant?draft_id=...` 深链和历史草案卡片恢复配置向导、步骤状态、摘要和依赖关系。支持的动作包括 `create_rd_task`、`create_ai_skill`、`create_ai_agent`、`create_scheduled_job`、`create_plugin_connection`、`create_plugin_action` 和 `create_analysis_draft`；可由 `assistant_tools` 构造的草案必须在模型调用前确定性返回，模型网关未配置时也不应阻塞草案生成。草案预检和确认权限必须按动作拆分：`create_plugin_connection` 和 `create_plugin_action` 要求管理员、`system.admin` 或 `system.plugins.manage`，`create_ai_skill` 和 `create_ai_agent` 要求管理员、`system.admin` 或 `system.ai_capabilities.manage`，`create_scheduled_job` 要求管理员、`system.admin` 或 `system.scheduled_jobs.manage`。状态为 `pending`、`confirmed`、`cancelled`、`expired` 或 `failed`。创建草案可携带顶层 `expires_at`，也兼容 `metadata_json.expires_at`；服务端读取、确认、取消、修改或更新 payload 前会把已过期且仍为 `pending` 的草案转为 `expired` 并写入 `assistant_action_draft.expired` 审计。确认前不得写入 `ai_tasks`、`ai_skills`、`ai_agents`、`scheduled_jobs`、`plugin_connections`、`plugin_actions` 或触发外部调用；分析类草案确认前也不得生成最终分析结果。前端点击“应用到表单”后，用户在任务中心/插件管理表单内编辑并保存时，必须先调用 `PATCH /api/assistant/action-drafts/{draft_id}` 提交最终 payload 和 `modified_fields`，再调用 confirm；不得直接调用领域创建接口绕过草案生命周期。PATCH 和修改指标接口仅允许 pending 草案，终态草案返回 `DRAFT_NOT_PENDING`。failed 草案可通过 `POST /api/assistant/action-drafts/{draft_id}/retry` 重新打开为 pending，服务端必须把当前失败信息追加到 `metadata_json.failure_history`，递增 `retry_count`，记录重试原因和操作者，清空当前 `result_run_id`，并写入 `assistant_action_draft.retry_requested` 审计；重新打开不会写入领域资源，仍需后续显式 confirm。confirm 对已 confirmed 且已有成功动作运行的重复提交必须幂等返回同一 run；数据库层应保证同一草案最多一条成功 run。前端点击“查看详情”或通过 `/assistant?draft_id=...` 深链加载草案时，必须调用 `POST /api/assistant/action-drafts/{draft_id}/view`，请求体可带 `{ "surface": "detail_modal" | "deeplink" }`；服务端在草案 `metadata_json` 写入 `viewed_at`、`detail_viewed_at`、`last_viewed_at`、`view_count`、`viewed_by` 和 `last_view_surface`，记录 `assistant_action_draft.viewed` 审计并返回刷新后的草案。前端随后在当前对话页展示草案状态、动作、风险等级、payload JSON、字段差异和校验问题。

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

PostgreSQL 运行态必须在 `assistant_action_drafts` read model 中完成当前用户、动作、状态、`validation_status`、创建时间、关键词、排序和分页过滤，不得因校验状态筛选回退到全量草案读取后服务层切片。

响应在通用列表字段外返回 `summary`，包括 `draft_total`、`status_counts`、`validation_counts`、`risk_counts`、`permission_counts`、`governance_counts`、`decision_counts`、`confirm_ready_count`、`confirm_blocked_count`、`adoption_rate=confirmed/total`、`resolution_rate=(confirmed+cancelled+expired+failed)/total`、`user_modified_count` 和 `user_modified_rate`。`governance_counts` 至少包含 `high_risk`、`permission_blocked`、`permission_warning`、`validation_blocked`、`validation_warning`、`failed`、`retry_total`、`audit_events`、`permission_issues` 和 `validation_issues`，用于草案任务台顶部集中展示确认治理压力。`decision_counts` 按 `ready/warning/blocked/failed/expired/terminal/unknown` 聚合，`confirm_ready_count=ready+warning`，`confirm_blocked_count=blocked+failed+expired`。列表行包含 `source_link=/assistant?draft_id=<id>`、`view_count`、`modified_field_count`、`validation_issue_count`、`wizard_step_count`、`result_status/result_type/result_id`、`impact_operation/impact_resource_type/impact_changed_field_count`、`permission_status/permission_issue_count`、`audit_event_count/latest_audit_event_type`、`failure_count/retry_count`、`decision_status/decision_label/decision_reason/decision_next_action/can_confirm` 等任务台字段；敏感 payload 仍只能通过详情接口按现有脱敏规则查看。详情响应的 `governance` 必须包含 `decision`、`risk`、`impact`、`permissions`、`diff`、`retries` 和 `audit` 七段，供前端确认前集中展示可确认状态、原因、下一步、风险等级、影响对象、权限校验、执行前后差异、失败重试和审计链路。

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

`confirm` 只接受仍处于 `pending` 的草案。若草案 `expires_at <= now()`，服务端先将其置为 `expired` 并返回 `409 DRAFT_EXPIRED`，不得调用领域 service、不得创建 `assistant_action_runs` 或业务资源。确认时必须先按 `payload.assistant_prerequisite_draft_ids` 读取同创建人的已确认前置草案运行结果，把 `ai_skill/ai_agent/plugin_connection/plugin_action` 真实资源 ID 回填到当前草案的 `default_skill_ids`、`agent_id`、`skill_ids`、`connection_id`、`plugin_connection_id(s)` 或 `plugin_action_id(s)` 并重新预检，再走对应领域 service 或助手运行记录执行器：`create_rd_task` 仅支持从 `planned` 且尚无关联任务的需求生成 `product_detail_design` AI 研发任务，预检必须校验 `requirement_id`、产品、版本、需求状态和重复任务，确认后复用需求生成任务 service 写入 `ai_tasks` 并推进需求状态；`create_ai_skill` 以 AI 能力管理权限调用 AI 能力配置 service 写入 `ai_skills`；`create_ai_agent` 以 AI 能力管理权限调用 AI 能力配置 service 写入 `ai_agents`，并重新校验 `brain_app_id`、`model_gateway_config_id` 和 `default_skill_ids`；`create_scheduled_job` 以定时作业管理权限调用 scheduled_jobs service 并把 `config_json.assistant_draft` 写入作业配置；若草案 payload 携带 `config_json.assistant_run_once_request.requested=true`，服务端创建作业后还会触发一次 `manual` 运行，并把公开运行记录嵌入 `run.result.scheduled_job_run`，同时把该运行写入 `assistant_action_run_id`、`assistant_action_draft_id`、`assistant_source_message_id` 和 `triggered_by_assistant=true` 归因字段；`create_plugin_connection` 以插件管理权限调用插件连接 service，`create_plugin_action` 以插件管理权限调用动作 service，`create_analysis_draft` 不写业务配置表，只生成 `assistant_action_runs.result_type=assistant_analysis` 的可追踪结果。确认成功返回 `{"draft": ..., "run": ...}`，`run.result_type/result_id/result` 指向创建出的领域资源或助手分析结果；确认失败不得绕过对应 service/执行器。取消接口只把 `pending` 草案置为 `cancelled` 并记录原因，不产生领域写入；取消过期草案同样返回 `DRAFT_EXPIRED`。`view` 接口接受 `{ "surface": "detail_modal" | "deeplink" }`，只更新草案查看元数据和 `assistant_action_draft.viewed` 审计，不确认草案、不写领域资源；`modification` 接口接受 `{ "modified_fields": ["name", "cron_expression"], "user_modified": true }`，在草案 `metadata_json` 中写入去重后的 `modified_fields`、`user_modified`、`modified_at` 和 `modified_by`，并记录 `assistant_action_draft.modified` 审计事件；该接口不改变草案状态、不确认草案、不写入领域资源，用于前端应用草案后保存前记录用户实际调整字段，支撑 `/api/assistant/metrics` 的用户修改率。`retry` 接口只接受 `failed` 草案，过期草案返回 `DRAFT_EXPIRED`，非 failed 返回 `DRAFT_NOT_FAILED`；重新打开后草案回到 pending，保留失败历史和重试元数据，仍需 confirm 才能写入业务配置。前端只能对 `pending` 草案展示确认、取消或应用到配置表单入口；`cancelled`、`expired` 等终态草案只能查看详情、查看草案和重新生成，`failed` 草案还可展示“重新打开”入口，避免绕过服务端草案生命周期。草案创建、确认、取消、查看、修改、过期和重试分别写入 `assistant_action_draft.created`、`assistant_action_draft.confirmed`、`assistant_action_draft.cancelled`、`assistant_action_draft.viewed`、`assistant_action_draft.modified`、`assistant_action_draft.expired` 和 `assistant_action_draft.retry_requested` 审计事件。

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

历史消息中的 `tool_results` 是展示用安全视图，不等同于原始运行载荷。`assistant.action_draft` 历史项只返回草案展示所需字段和动作白名单内的有限 payload 字段；`assistant.iteration` 历史项只保留版本 ID/标题/状态、需求/任务计数、`blocker_count`、`blockers_by_source`、`dashboard_url`、`next_actions`、`delivery_stage_overview` 和 `status_impact` 等版本治理摘要，不保留原始 dashboard 明细载荷；`api_key`、`auth_config`、`Authorization`、token、password、secret、cookie、private key 等敏感字段必须递归脱敏或移除。若 `preview.diffs[]` 的字段名、路径或标签命中敏感信息，`current`、`previous`、`proposed`、`default`、`value` 等值必须返回 `"***"`，不得在历史恢复、深链加载或模型上下文中泄露密钥和 Header 明文。
