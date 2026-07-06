# 用户洞察、迭代建议与 Bug API

> API 分册。覆盖用户洞察、用户反馈、用户使用指标、迭代规划建议和 Bug 管理。主入口见 [../api.md](../api.md)，分册组索引见 [quality-operations-and-insights.md](quality-operations-and-insights.md)。

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
GET /api/insights/items?category=用户反馈&product_id=product_001&summary=迭代版本&status=open&page=1&page_size=10&sort_by=updated_at&sort_order=desc
```

该接口面向用户洞察主列表聚合用户使用指标、用户反馈和 AI 迭代规划建议，返回统一行字段 `category`、`summary`、`owner`、`status`、`updated_at`、`product_id`、`version_id`、`module_code`、`feature_code`，并保留 `feedback_type`、`confidence_level`、`planning_cycle`、`priority` 和 `converted_requirement_id` 等上下文。支持 `category` 精确筛选，`product_id` 所属产品精确筛选，`summary` 文本筛选，`status` 精确筛选，`page/page_size` 服务端分页，`sort_by` 支持 `category/id/owner/status/summary/updated_at`，`sort_order` 支持 `asc/desc`。PostgreSQL 运行时必须通过 repository SQL read model 聚合查询三类来源，并在 SQL 层完成筛选、排序和分页；MemoryStore 仅保留为测试 helper fallback。前端用户洞察主列表必须调用该接口，不再并发拉取使用指标、反馈和迭代建议三个原始接口后本地拼装、排序或分页；登记、处理和决策仍使用对应原始写接口。

反馈状态支持：`open | triaged | linked | resolved | archived`。`POST /api/insights/user-feedback` 允许任意已登录用户登记真实反馈；`PATCH /api/insights/user-feedback/{feedback_id}` 仅允许 `product_owner`、`rd_owner` 或 `admin` 更新状态、标签、情绪、评分和处理备注；GET 支持按 `product_id`、`module_code`、`feature_code`、`status` 和 `created_by` 筛选。GET 传入 `page` 或 `page_size` 时必须返回 `items/page/page_size/total/query/performance`，PostgreSQL 运行态优先调用用户反馈 count/page read model，不得先读取全部反馈后在接口层切片；`summary_only=true` 时列表行 `content` 仅返回 240 字摘要，避免用户洞察和调试列表被超长反馈拖慢。未传分页参数时保留旧 `items/total` 全量返回兼容历史调用，但不作为新增列表页面默认读取方式。反馈写入 `user_feedback` 结构表，并记录 `user_feedback.created` / `user_feedback.updated` 审计事件。

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
POST /api/bugs/images/upload
GET /api/bugs/images/preview?bucket=ai-brain-knowledge&object_key=bugs%2Fevidence%2Fuser_admin%2F2026-07-03%2Fd7b7aa...%2Ffailure.png&mime_type=image%2Fpng
POST /api/bugs/batch-update
POST /api/bugs/{bug_id}/promote-ai-task
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

列表接口必须先校验 `bug.read`，并按当前用户产品 scope 过滤；PostgreSQL 运行态必须在 Bug SQL read model 中完成筛选、排序和分页，不得回退为接口层全量过滤。列表响应中的每条 Bug 除 `product_id`、`version_id` 外，还返回 `version_code`、`version_name` 作为页面展示投影；未关联版本时这两个字段为空。

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

推进 AI 任务请求体：

```json
{
  "auto_start": true,
  "title": "Bug 修复：知识检索权限过滤异常"
}
```

`POST /api/bugs/{bug_id}/promote-ai-task` 要求 Bug 写权限。接口会基于 Bug 的产品、版本、模块、复现步骤、证据和可选需求上下文创建 `task_type=bug_fix` 的 AI Task，并把 Bug 快照写入 `input_json.bug`；同时在 Bug 的 `evidence.ai_task_automation` 中记录 `latest_task_id` 和历史 `task_ids`。`auto_start=true` 时，创建后立即复用 `POST /api/ai-tasks/{task_id}/start` 的现有执行链路；若存在 active 的 `bug_fix` 研发执行器策略，则任务进入 `running/current_step=waiting_ai_executor` 并创建 `ai_executor_task` 交由 Runner 认领。重复 Bug、已关闭 Bug 或已有未结束自动化任务的 Bug 返回 `409 BUG_STATE_INVALID` 或 `409 BUG_AI_TASK_IN_PROGRESS`。接口写入 `ai_task.created` 与 `bug.ai_task_promoted` 审计事件。

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
    "test_run_id": "test_run_001",
    "images": [
      {
        "id": "bug_image_d7b7aa0f3f31a2b1",
        "bucket": "ai-brain-knowledge",
        "object_key": "bugs/evidence/user_admin/2026-07-03/d7b7aa.../failure.png",
        "content_hash": "d7b7aa...",
        "filename": "failure.png",
        "mime_type": "image/png",
        "size_bytes": 204800,
        "source": "file_picker",
        "storage_provider": "minio",
        "uploaded_at": "2026-07-03T08:00:00+00:00",
        "uploaded_by": "user_admin"
      }
    ]
  }
}
```

图片证据上传请求体：

```json
{
  "filename": "failure.png",
  "mime_type": "image/png",
  "source": "file_picker",
  "content_base64": "<base64>"
}
```

`POST /api/bugs/images/upload` 要求 Bug 写权限，仅接受 `image/png`、`image/jpeg`、`image/gif`、`image/webp`，单张最大 10MB。生产环境通过 `OBJECT_STORAGE_PROVIDER=minio` 写入 MinIO/S3-compatible bucket，响应返回 `id`、`storage_provider`、`bucket`、`object_key`、`content_hash`、`filename`、`mime_type`、`size_bytes`、`source`、`uploaded_at` 和 `uploaded_by`。登记或编辑 Bug 时前端将这些对象引用写入 `evidence.images[]`，不得把图片二进制或 data URL 写入 `bugs.evidence`。

`GET /api/bugs/images/preview` 要求 `bug.read`，通过 query 传入上传响应中的 `bucket`、`object_key` 和 `mime_type`。服务端只允许读取当前配置 bucket 下 `bugs/evidence/` 前缀且 MIME 属于图片白名单的对象，返回对应图片二进制和 `Content-Type`；对象不存在返回 `404 NOT_FOUND`，bucket、前缀或 MIME 非法返回 `400 VALIDATION_ERROR`。前端应使用该接口生成本地 Blob URL 预览图片，不得直接暴露 MinIO URL。

状态和枚举：

- 来源：`ai_auto_test | ai_post_release | code_inspection | manual_test`。
- 状态：`open | triaged | needs_info | assigned | fixed | verified | closed | reopened`。
- 严重程度：`blocker | critical | major | minor`。
- AI 自动测试来源缺少 `reproduce_steps` 时初始状态为 `needs_info`；人工登记或带复现步骤的 Bug 初始状态为 `open`。
- 提交 `duplicate_of_bug_id` 时重复 Bug 初始状态为 `closed`，并保留主 Bug 关联，避免重复进入修复队列。
- 状态更新必须符合状态机约束，非法跨越返回 `BUG_STATE_INVALID`；创建和更新均写入 `bug.created` 或 `bug.updated` 审计事件。
- Bug 管理工作台必须从真实 `/api/bugs` 响应映射 `version_code`、`version_name`、`reproduce_steps`、`evidence`、`duplicate_of_bug_id`、`requirement_id` 和 `related_task_id`；列表展示迭代版本并支持按版本名、编码或未关联状态过滤；登记弹窗允许录入复现步骤、对象型证据 JSON、关联需求和关联任务，目标版本选项读取同产品未归档迭代版本，支持 `planning`、`active`、`testing` 和 `released`，过滤 `archived`；登记和编辑弹窗支持本地多选图片与剪贴板粘贴图片，保存前先调用 `/api/bugs/images/upload` 获得 MinIO 对象引用并写入 `evidence.images[]`，已上传图片点击后调用 `/api/bugs/images/preview` 预览；编辑弹窗允许维护复现步骤、证据 JSON、状态、处理人和重复归并，重复归并候选仅展示同产品 Bug，来源只读展示，不允许把 AI 自动测试或上线后分析来源在前端改写为人工来源；列表勾选多条 Bug 后可打开“批量处理”，调用 `/api/bugs/batch-update` 更新状态、严重级别或处理人，并展示批量结果；具备 Bug 管理权限的用户可在行操作中将未关闭 Bug 推进为 `bug_fix` AI Task 并自动启动，viewer 只读用户不得展示该操作。
