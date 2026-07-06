# 审计与错误语义 API

> API 分册。覆盖审计事件、核心接口错误语义和错误码。主入口见 [../api.md](../api.md)。

### 审计事件

```http
GET /api/audit/events?ai_task_id=task_001
GET /api/audit/events?subject_type=requirement&subject_id=requirement_001
GET /api/audit/events?event_type=review.submitted
GET /api/audit/events?actor_id=user_admin&created_from=2026-05-31T00:00:00Z&created_to=2026-05-31T23:59:59Z
```

权限：要求 `audit.read`；管理员、`system.admin` 或通过角色授予 `audit.read` 的用户可访问，未授权用户返回 `403 FORBIDDEN`。

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

## 核心接口错误语义

| 接口/动作 | HTTP 状态 | 错误码 | 可重试 | 审计要求 | 前端处理建议 |
|-----------|-----------|--------|--------|----------|--------------|
| POST `/api/auth/login` | 400/401 | LOGIN_CHALLENGE_REQUIRED / LOGIN_CHALLENGE_INVALID | 是 | 不记录用户填写答案；可记录失败摘要和 trace_id。 | 自动刷新数字校验题，提示用户重新填写后再登录。 |
| POST `/api/auth/login-challenge` | 200/503 | LOGIN_CHALLENGE_UNAVAILABLE | 是 | 不记录答案明文或 hash。 | 展示安全校验生成失败，允许刷新重试。 |
| GET `/api/auth/dingtalk/start` | 503 | DINGTALK_LOGIN_NOT_CONFIGURED | 否 | 记录可选，不记录 redirect 明文以外的敏感字段。 | 隐藏或禁用钉钉登录入口，提示管理员配置认证提供方。 |
| GET `/api/auth/dingtalk/callback` | 302 回前端错误页 | DINGTALK_STATE_INVALID / DINGTALK_AUTH_DENIED / DINGTALK_CODE_MISSING / DINGTALK_UPSTREAM_ERROR / DINGTALK_PROFILE_INCOMPLETE | 视错误而定 | 成功记录 `dingtalk_login.succeeded`；失败可按安全策略记录摘要，不保存 auth code、access token 或 refresh token。 | 回到登录页或回调页展示错误，允许重新发起钉钉登录。 |
| GET `/api/auth/dingtalk/callback` | 302 回前端错误页 | DINGTALK_CORP_NOT_ALLOWED / DINGTALK_ACCOUNT_NOT_BOUND / DINGTALK_ACCOUNT_PENDING_APPROVAL / DINGTALK_ACCOUNT_INACTIVE / EXTERNAL_IDENTITY_CONFLICT | 否 | 自动开户成功记录 `dingtalk_account.provisioned`；拒绝只保存 corp_id 等非敏感摘要。 | 展示企业不允许、未绑定、待审批、账号停用或绑定冲突的明确提示。 |
| POST `/api/auth/dingtalk/exchange-ticket` | 401 | DINGTALK_TICKET_INVALID | 否 | 记录失败摘要可选；不得记录 ticket 明文。 | 回到登录页重新发起钉钉登录。 |
| POST `/api/auth/dingtalk/bind/start` / bind callback | 302/409 | EXTERNAL_IDENTITY_CONFLICT | 否 | 绑定成功记录 `dingtalk_account.bound`，解绑成功记录 `dingtalk_account.unbound`；冲突不返回被占用用户敏感信息。 | 提示该钉钉账号已绑定其它 AI Brain 账号，联系管理员处理。 |
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
| DINGTALK_LOGIN_NOT_CONFIGURED | 钉钉登录未启用或未配置完整。 |
| DINGTALK_STATE_INVALID | 钉钉 OAuth state 缺失、过期、不匹配或已使用。 |
| DINGTALK_AUTH_DENIED | 用户在钉钉授权页拒绝授权或钉钉返回授权错误。 |
| DINGTALK_CODE_MISSING | 钉钉 OAuth callback 缺少授权码。 |
| DINGTALK_UPSTREAM_ERROR | 钉钉 token 或用户信息接口调用失败。 |
| DINGTALK_PROFILE_INCOMPLETE | 钉钉用户信息缺少可绑定的外部主体标识。 |
| DINGTALK_CORP_NOT_ALLOWED | 钉钉企业不在 AI Brain 允许登录的 corp 白名单中。 |
| DINGTALK_ACCOUNT_NOT_BOUND | 钉钉身份未绑定 AI Brain 用户，且未启用自动开户。 |
| DINGTALK_ACCOUNT_PENDING_APPROVAL | 钉钉身份登录申请等待管理员审批。 |
| DINGTALK_ACCOUNT_INACTIVE | 钉钉身份绑定的 AI Brain 用户已停用。 |
| EXTERNAL_IDENTITY_CONFLICT | 同一个外部身份已经绑定其它 AI Brain 用户。 |
| DINGTALK_TICKET_INVALID | 一次性登录 ticket 缺失、过期、无效或已使用。 |
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
