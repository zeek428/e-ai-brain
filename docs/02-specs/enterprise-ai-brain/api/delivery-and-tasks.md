# 需求交付与研发任务 API

> API 分册。覆盖需求、AI 任务、人工确认、回写与导出。主入口见 [../api.md](../api.md)。

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
- 删除需求仅允许未生成 AI 任务的记录；已有 `task_ids` 时返回 `409 RESOURCE_IN_USE`，并在错误详情中返回 `related_counts.ai_tasks` 与 `related_total`，供前端展示占用数量和处理建议。

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
| `bug_fix` | Bug 修复自动化任务，由 Bug 管理 `promote-ai-task` 接口创建并可直接进入研发执行器策略。 |

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

可选请求体：

```json
{
  "execution_mode": "model_gateway | deterministic",
  "reason": "本次全链路回归使用确定性输出，避免外部模型网关波动"
}
```

当前实现会先匹配 active 研发执行器策略：若命中 `rd_task_executor_policies`，任务不会装配 Agent/Skill，也不会走模型网关，而是创建关联 `ai_executor_tasks(ai_task_id=<task_id>)`，把任务置为 `running/current_step=waiting_ai_executor`，并返回 `executor_policy_id/executor_task_id/runner_id`；后续由插件管理下的 Codex、Claude Code 或 OpenClaw Runner 认领执行。策略 `code_change_review_mode` 默认为 `manual_review`，成功回写后任务进入 `waiting_review/current_step=executor_completed` 并创建待确认 Review；配置为 `auto_commit` 时，成功回写后系统自动创建已通过 Review、完成任务确认副作用，并向 Runner 下发隔离工作区 `merge` 决策。失败/取消/超时进入 `failed` 或 `cancelled`，隔离工作区仍按失败、取消或拒绝语义丢弃。命中研发执行器策略时，服务端会按任务 `product_id/version_id` 查询当前用户可读、已索引且同产品的知识中心片段，写入 Runner `input_payload.knowledge_references[]`，并在实际下发给执行器的 `instruction` 中追加“产品知识中心上下文”；有版本归属时，版本不匹配的文档不会进入上下文，产品级未绑定版本的文档可作为通用参考。未命中研发执行器策略时，当前实现会同步运行到下一个人工确认点或失败状态。`draft` 任务可启动；已失败且 `current_step` 为 `model_gateway_failed`、`code_review_executor_failed` 或 `executor_failed` 的任务可用同一 `task_id` 再次调用 start 重试，并记录 `ai_task.retry_started` 审计事件。非 code_review 任务若存在 active/default 的 OpenAI-compatible 模型网关配置且已配置 API Key，启动时调用 `{base_url}/chat/completions` 并要求 `response_format={"type":"json_object"}`；若没有结构化默认配置但设置了 `MODEL_GATEWAY_BASE_URL` 和 `MODEL_GATEWAY_API_KEY`，则使用环境模型网关。缺少可用模型网关或 active/default 配置缺失 API Key 返回 `MODEL_GATEWAY_CONFIG_INVALID`；provider 调用、响应解析或网络失败返回 `MODEL_GATEWAY_FAILED`。code_review 任务通过 `code_review_executor` 执行：默认 `claude_code_skill/code-review` 命令适配器由 `CODE_REVIEW_EXECUTOR_COMMAND` 配置，输入 JSON 通过 stdin 提供，输出必须是包含 `summary`、`risk_level` 和 `findings` 的 JSON 对象，系统会补齐并持久化 executor 元数据；显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 时复用模型网关适配器；默认外部命令为空且存在 active/default 或环境模型网关时，系统会自动使用 `model_gateway` 适配器，并以 MR/PR 快照、技术方案、需求和产品上下文作为 Review 输入。执行器配置缺失、调用失败、超时、响应解析或结构化报告校验失败返回 `CODE_REVIEW_EXECUTOR_FAILED`。这些失败都会把任务置为 `failed`；使用模型网关适配器时保留模型调用元数据日志；任务启动不得生成本地 fallback 输出。
`execution_mode` 为空或 `model_gateway` 时保持上述生产默认路径；显式 `deterministic` 仅允许管理员用于本地/验收回归，会跳过研发执行器策略匹配和模型网关，必须写入 `ai_task.deterministic_execution_used` 审计事件并记录 `reason`，不会创建模型调用日志，也不会作为模型网关失败时的自动兜底。
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

响应包含 `task_type`、`input`、`output`、`output_summary`、`current_step`、`pending_review`、`reviews`、`mock_issues` 和 `knowledge_deposits`。`output_summary` 是用于任务详情和待确认界面的可读摘要；当 Runner 回写结果只包含 `output_preview` 时，服务端会优先提取 Codex 最终报告段，完整原始执行结果仍保留在 `output`。通过需求生成的任务必须在 `input` 中包含：

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
