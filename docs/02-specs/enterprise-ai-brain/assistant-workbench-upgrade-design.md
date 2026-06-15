# AI 助手工作台升级整体方案

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.2 |
| 日期 | 2026-06-15 |
| 文档状态 | Draft |

## 背景与目标

当前 AI 助手已经具备聊天、模型网关调用、服务端 read-model 工具结果、会话历史和可跳转引用能力；系统也已有知识中心、AI 能力配置、插件管理和定时作业配置。下一阶段目标是把这些能力从分散后台页面收束到 AI 助手工作台，让用户可以在同一个对话里通过 `@` 显式引用业务对象、知识库、插件、AI 能力和定时任务，并在助理内完成配置草案、确认执行和结果追踪。

本次升级不是新增一个独立自动化引擎，而是在现有模块之上增加助理编排层。业务事实源仍是 PostgreSQL 结构表；模型调用仍必须通过 `model_gateway`；知识检索仍必须在数据库查询层做权限过滤；插件调用、定时作业运行和配置写入仍复用现有 service、审计和权限边界。

目标能力：

- `@` 引用：在聊天输入中通过 `@产品`、`@需求`、`@任务`、`@Bug`、`@知识库/文档`、`@插件/动作`、`@AI Agent/Skill`、`@定时任务` 等显式带入上下文。
- 知识库引入：用户可选择知识空间、目录、文档或 chunk 范围，助理按权限检索并把有限知识片段注入模型上下文。
- 助理内配置：用户可在对话里创建或修改 AI 能力、插件连接/动作、定时作业配置，助理生成可审阅配置草案和差异。
- 定时任务执行：用户可在对话中手动触发现有作业、创建新作业、查看运行结果和错误摘要。
- 安全确认：所有写配置、触发外部调用、执行业务写入和删除/停用动作都必须先生成草案，再由有权限用户显式确认。

## 现有基础

已存在的可复用能力：

- `assistant_chat`：聊天校验、模型网关调用、会话/消息持久化、模型日志和审计。
- `assistant_references`：产品、需求、任务、Review、Bug、代码评审和知识沉淀候选引用。
- `assistant_tools`：delivery progress、pending reviews、code review、iteration、bugs、model gateway 等确定性 read-model 工具。
- `knowledge`：知识空间、目录、文档、chunk set、chunk、导入任务、权限过滤检索和知识沉淀。
- `scheduled_jobs`：`ai_skills`、`ai_agents`、`scheduled_jobs`、`scheduled_job_runs`、知识引用、插件动作、模型网关和运行快照。
- `plugins`：HTTP/MCP 插件、连接、动作、动态参数、试运行、调用日志和删除保护。
- `model_gateway`：OpenAI-compatible Chat/Embedding 配置、连接测试、模型调用日志和密钥脱敏。

关键缺口与当前落地状态：

- P0 已落地 `knowledge_document` 显式引用协议：前端通过 `@` 提交 `references`，后端提供候选、解析、权限校验和限量知识 chunk 注入。
- P0 已落地服务端动作草案：聊天返回的 `assistant.action_draft` 可持久化为 `assistant_action_drafts`，并通过确认/取消 API 执行或关闭。
- P0 已落地插件连接、动作和定时作业三类创建草案确认闭环；AI 能力配置、作业运行、删除/停用按后续切片扩展。
- P1 首个切片已落地显式引用扩展和运行诊断：管理员可通过 `@` 引用定时作业、运行记录、插件动作、AI角色和 Skill，普通用户被候选/解析双重过滤；围绕失败运行追问时返回 `assistant.scheduled_job_diagnostic`，按数据连接、AI 处理和结果动作三段解释失败位置。

## 目标交互

### 1. 引用知识并问答

用户输入：

```text
@知识空间:研发规范 @文档:代码Review规则 帮我根据这些规则检查最近的 code_review 待确认项。
```

工作流：

1. 前端 `@` 选择器把所选对象写入消息 `references`。
2. 后端解析引用并校验当前用户读权限。
3. 知识引用按空间/目录/文档/chunk 范围取可检索 chunk，限制数量和字符数。
4. 助手工具读取待确认 Review / code review read model。
5. 模型只接收脱敏后的上下文、工具结果和知识片段。
6. 回复展示引用来源和可跳转链接，消息 metadata 持久化解析后的引用与工具结果。

### 2. 在助理内创建定时任务

用户输入：

```text
帮我每周一 9 点从 @插件动作:MaxCompute用户反馈 拉取上周反馈，用 @Agent:用户洞察分析 和 @Skill:反馈总结 生成洞察，引用 @文档:反馈分类标准，写入用户洞察。
```

工作流：

1. 助理解析插件动作、Agent、Skill、知识文档和调度意图。
2. 生成 `scheduled_job` 草案，包含 `job_type=user_feedback_insight_extract`、cron、timezone、插件动作、模型网关、Agent、Skills、知识引用和输出映射。
3. 前端展示配置草案表单和差异摘要，用户可编辑字段。
4. 用户点击确认后，后端复用 `create_scheduled_job_response` 写入结构表和审计。
5. 助手回复作业 ID、下次运行时间和跳转链接。

### 3. 手动触发并追踪作业

用户输入：

```text
运行 @定时任务:每周用户反馈洞察，并告诉我本次写入了什么。
```

工作流：

1. 助理生成 `scheduled_job.run` 动作草案。
2. 用户确认后复用 `run_scheduled_job_response` 创建运行实例。
3. 助手返回运行实例 ID；若同步完成则展示三段执行节点摘要，否则展示运行中状态和查看链接。
4. 用户可继续追问该运行实例，助理读取 `scheduled_job_runs` 和插件调用日志摘要。

## 架构方案

```text
AssistantPage
  ├─ Chat Input with @ Mention Resolver
  ├─ Reference Chips / Context Drawer
  ├─ Action Draft Panel
  └─ Run Result Panel
        │
        ▼
assistant router
  ├─ chat
  ├─ reference candidates / resolve
  ├─ action draft / confirm / cancel
  └─ run status projection
        │
        ▼
assistant orchestration services
  ├─ reference resolver
  ├─ knowledge context builder
  ├─ deterministic read-model tools
  ├─ action planner
  ├─ action guard / confirmation
  └─ action dispatcher
        │
        ├─ knowledge services
        ├─ scheduled_jobs services
        ├─ plugins services
        ├─ model_gateway services
        ├─ ai task / requirement read models
        └─ audit / repository layer
```

新增助理编排层只做编排和授权前置，不直接写业务表。真正写入必须通过已有领域 service 完成，保证校验、审计、DB-first 写路径和错误语义一致。

## 引用协议

前端输入中的 `@` 是用户体验；后端接收结构化引用，避免依赖自然语言字符串解析。

建议消息请求扩展：

```json
{
  "message": "帮我基于这些知识总结待确认风险",
  "conversation_id": "conversation_001",
  "product_id": "product_001",
  "references": [
    {
      "type": "knowledge_document",
      "id": "knowledge_doc_001"
    },
    {
      "type": "scheduled_job",
      "id": "scheduled_job_001"
    }
  ],
  "context": {
    "source": "assistant-page"
  }
}
```

首批引用类型：

| 类型 | 说明 | 权限 |
|------|------|------|
| `product` | 产品上下文 | 产品读范围 |
| `iteration_version` | 迭代版本 | 产品读范围 |
| `requirement` | 需求 | 需求读范围 |
| `ai_task` | AI 任务 | 任务读范围 |
| `human_review` | 人工确认 | 任务读范围 |
| `bug` | 缺陷 | Bug 读范围 |
| `code_review_report` | 代码评审报告 | 任务读范围 |
| `knowledge_space` | 知识空间 | 知识空间成员或管理员 |
| `knowledge_folder` | 知识目录 | 知识空间成员或管理员 |
| `knowledge_document` | 知识文档 | 知识文档可读 |
| `knowledge_chunk` | 知识片段 | 知识文档可读 |
| `model_gateway_config` | 模型配置摘要 | `system.model_gateway.manage` 或脱敏只读 |
| `ai_agent` | AI Agent | `system.scheduled_jobs.manage` |
| `ai_skill` | AI Skill | `system.scheduled_jobs.manage` |
| `integration_plugin` | 插件定义 | `system.plugins.manage` |
| `plugin_connection` | 插件连接 | `system.plugins.manage` |
| `plugin_action` | 插件动作 | `system.plugins.manage` |
| `scheduled_job` | 定时作业 | `system.scheduled_jobs.manage` |
| `scheduled_job_run` | 作业运行实例 | `system.scheduled_jobs.manage` |

引用解析返回统一结构：

```json
{
  "items": [
    {
      "type": "knowledge_document",
      "id": "knowledge_doc_001",
      "title": "反馈分类标准",
      "url": "/assets/knowledge?document_id=knowledge_doc_001",
      "status": "resolved",
      "metadata": {
        "knowledge_space_id": "knowledge_space_001",
        "index_status": "vector_indexed"
      }
    }
  ],
  "errors": []
}
```

未授权或不存在的引用不得进入模型上下文；响应中返回结构化错误供前端提示。

## 知识库引入

知识引入遵守“显式范围 + 权限过滤 + 限量上下文”：

- 文档级引用：按文档 ID 查可读 chunk，跳过 parent chunk，按 chunk 顺序或语义相关度取前 N 条。
- 空间/目录级引用：必须结合用户问题做检索，不能把整个空间全部注入。
- chunk 级引用：直接注入指定 chunk 的脱敏内容和来源。
- 每次聊天默认最多注入 8 个 chunk、每个 chunk 最多 1200 字符；超过限制时返回截断说明。
- 注入内容只进入模型请求，不写入 `model_gateway_logs`；消息 metadata 只保存引用 ID、标题、chunk ID 和摘要，不保存完整知识正文。
- 如果知识文档处于 `index_failed`、`queued`、`parsing` 等不可检索状态，助理应提示用户先完成索引或更换文档。

## 助理动作草案

为支持助理内配置和执行，需要新增待确认动作草案：

| 表 | 说明 |
|----|------|
| `assistant_action_drafts` | 保存助理生成的待确认动作、目标类型、请求 payload、diff、风险等级、状态、过期时间和创建人。 |
| `assistant_action_runs` | 保存草案确认后的执行结果、调用的领域 service、目标 subject、结果摘要、错误码和关联审计事件。 |

草案状态：

```text
pending | confirmed | cancelled | failed
```

动作类型：

| 动作类型 | 说明 | 确认要求 |
|----------|------|----------|
| `assistant.chat` | 纯问答 | 无 |
| `assistant.knowledge_search` | 知识检索 | 无 |
| `ai_skill.create/update` | 创建或修改 Skill | 管理员确认 |
| `ai_agent.create/update` | 创建或修改 Agent | 管理员确认 |
| `plugin.create/update` | 创建或修改插件定义 | 管理员确认 |
| `plugin_connection.create/update/test` | 管理或测试插件连接 | 管理员确认；测试外部系统需确认 |
| `plugin_action.create/update/trial` | 管理或试运行插件动作 | 管理员确认；试运行需确认 |
| `scheduled_job.create/update/delete` | 管理定时作业 | 管理员确认；删除需二次确认 |
| `scheduled_job.run/cancel` | 手动运行或取消作业 | 管理员确认 |

删除、停用、外部调用和会写入业务表的动作必须展示影响摘要。助理不得把模型生成的 payload 直接提交到业务 service。

## 助理内配置体验

前端工作台建议采用三栏布局：

- 左侧：会话历史、常用入口、最近引用。
- 中间：聊天区，支持 `@` 引用、引用 chip、回复引用链接和操作卡片。
- 右侧：上下文与动作面板，展示已选引用、知识片段摘要、配置草案、diff、确认按钮和运行结果。

配置草案使用现有后台页面字段模型，不另造一套隐藏配置：

- AI 能力配置：Agent、Skill、模型网关、默认 Skill、工具策略和执行策略。
- 插件管理：插件定义、连接认证、公共 Params/Headers、动作请求、结果映射和试运行。
- 定时任务：数据连接、AI 模型、Agent、Skills、知识引用、结果动作、调度计划、重试、超时和启停。

助理生成草案后必须允许用户编辑关键字段；确认后返回创建/修改后的实体链接，并建议跳转到原管理页查看完整配置。

## 权限与安全

- `@` 候选必须按当前用户权限过滤；前端不展示无权对象，后端仍强制校验。
- 配置写入第一阶段仅允许 `admin`；后续可拆分为 `system.plugins.manage`、`system.scheduled_jobs.manage`、`system.model_gateway.manage` 等权限点。
- 模型请求不得包含 API Key、Bearer Token、Basic 密码、Git 凭据、插件连接密钥或完整外部响应。
- 插件调用日志可为管理员调试返回明文请求摘要，但传给模型的上下文必须使用脱敏摘要。
- 知识检索必须在 repository/query 层做权限过滤，不能先查全量再由模型判断。
- 高风险动作必须写审计事件，payload 记录动作类型、草案 ID、目标 subject、确认用户和结果，不记录密钥或完整 prompt。
- 定时任务创建和运行仍必须保存 Agent、Skill、模型网关、Prompt、工具策略、插件和知识引用快照，保证运行结果可追溯。

## API 目标

已落地与目标接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/assistant/reference-candidates` | 按 query/type/product_id 返回当前用户可引用对象。 |
| POST | `/api/assistant/references/resolve` | 解析并校验结构化引用，返回可进入上下文的引用快照。 |
| POST | `/api/assistant/chat` | 扩展 `references` 字段，聊天时注入显式引用和知识上下文。 |
| POST | `/api/assistant/action-drafts` | 创建待确认动作草案。 |
| GET | `/api/assistant/action-drafts/{draft_id}` | 查询草案详情、风险、状态和可执行权限。 |
| POST | `/api/assistant/action-drafts/{draft_id}/confirm` | 确认执行草案，调度到对应领域 service。 |
| POST | `/api/assistant/action-drafts/{draft_id}/cancel` | 取消草案。 |

已存在接口继续作为实际执行边界：

- `/api/system/ai-skills`
- `/api/system/ai-agents`
- `/api/system/plugins`
- `/api/system/plugin-connections`
- `/api/system/plugin-actions`
- `/api/system/scheduled-jobs`
- `/api/system/scheduled-jobs/{job_id}/run`
- `/api/system/scheduled-job-runs`
- `/api/knowledge/search`

## 实施阶段

### Phase 1：显式 `@` 引用和知识注入

- 前端聊天输入支持 `@` 搜索和引用 chip。
- 后端新增 reference candidates / resolve。
- `POST /api/assistant/chat` 支持 `references`。
- 聊天上下文支持知识文档/chunk 注入和引用持久化。
- 测试覆盖权限过滤、不可检索知识、引用去重和历史消息恢复。

### Phase 2：助理动作草案

- 新增 `assistant_action_drafts` / `assistant_action_runs`。
- 支持 AI Agent/Skill、插件连接/动作、定时作业的创建/修改草案。
- 前端右侧面板展示草案、diff、风险和确认。
- 确认后复用现有 service 写入和审计。

### Phase 3：定时任务运行与结果追踪

- 助理内手动触发/取消定时任务。
- 回复中展示运行实例、状态、三段执行节点摘要和错误信息。
- 支持围绕 `@scheduled_job_run` 继续追问运行结果。

### Phase 4：配置治理与模板化

- 建立常用任务模板，如 MaxCompute 用户反馈洞察、线上日志 AI 分析、迭代规划建议。
- 支持从历史成功作业复制配置。
- 引入更细粒度 RBAC，把配置权限从 admin 拆到系统权限点和产品范围。

## 验收标准

- 用户在 AI 助手输入 `@` 时只能看到自己有权读取或管理的对象。
- 用户选择知识文档后，聊天响应能引用该文档，模型日志不保存完整知识正文。
- 用户请求创建定时任务时，系统只生成草案，不会在未确认时写入 `scheduled_jobs`。
- 用户确认草案后，写入结果与直接调用现有后台接口一致，并产生审计事件。
- 用户从助理手动运行定时任务后，可在对话中看到运行实例 ID、状态和运行详情链接。
- 无权限用户不能通过自然语言绕过插件、模型网关、定时任务或知识权限。
- 删除/停用/外部调用类动作必须有影响摘要和显式确认。

## 非目标

- 不允许助理绕过现有 service 直接写数据库。
- 不在模型日志中保存完整 prompt、完整模型输出、密钥或大段知识正文。
- 不让模型直接决定是否执行外部副作用；模型只能生成草案和建议。
- 不在第一阶段实现任意代码执行、任意 SQL 执行或未注册插件能力。
