# 代码评审与知识中心 API

> API 分册。覆盖 GitLab/GitHub 代码 Review 与知识中心。主入口见 [../api.md](../api.md)。

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

MR/PR diff 快照是 code_review 任务的唯一输入快照来源。MVP-A 必须支持 GitLab/GitHub 只读仓库绑定、变更预览和 diff 快照生成；MVP-B 在快照基础上创建正式 `code_review` 任务并生成 Review 报告。任务中心前端应先读取产品 Git 资源，再根据 provider 预览 MR 或 PR、展示文件树、变更明细、风险摘要、Review Checklist 和 `permission_diagnostics`，确认后生成快照，最后用兼容字段 `gitlab_mr_snapshot_id` 创建 `code_review` 任务；任务创建接口不得静默重新拉取或覆盖已有快照。后端通过 GitLab API 读取 `GET /api/v4/projects/{project}/merge_requests/{iid}` 和 `.../{iid}/changes`，其中 `project` 来自产品 Git 资源的 `project_path` 或 `project_id`；真实全链路回归脚本可显式配置 `remote_url=fixture://gitlab` 作为本地可控 GitLab MR 数据源，用于验证 Code Review 报告聚合门禁，该 fixture scheme 不作为生产 GitLab/GitHub 对接方案。GitHub API 读取 `GET /repos/{owner}/{repo}/pulls/{number}` 和 `.../files?per_page=100`，其中 `owner/repo` 来自 `project_path` 或 `remote_url`。`remote_url` 用于推导 GitLab base URL 或 GitHub Enterprise base URL，也可由 `GITLAB_BASE_URL` / `GITHUB_BASE_URL` 提供；`credential_ref` 推荐使用环境变量或服务端密钥引用，本地联调可直填只读 token，响应不得返回凭据值。预览响应的 `permission_diagnostics` 只暴露 base URL、仓库路径、凭据引用和 token 可用性等布尔诊断，不返回 token。快照响应会返回 `previous_snapshot`、`diff_change_summary` 和 `snapshot_reused`，用于比较同一 repository + MR/PR number 的上一轮快照。同一 `repository_id + snapshot_hash` 已存在时，快照接口返回已有 snapshot 并记录 `gitlab_mr.snapshot_reused` 或 `github_pr.snapshot_reused`，不得重复入库。MR/PR diff、变更文件数或单文件 diff 行数超过限制时返回 `GITLAB_MR_DIFF_TOO_LARGE`，不创建快照，并记录对应 provider 的 `*.snapshot_failed` 审计事件，payload 包含 `diff_size_bytes`、`diff_limit_bytes`、`changed_file_count`、`changed_file_limit`、`file_diff_line_count`、`file_diff_line_limit`、`file_path`、`mr_iid`、`requirement_id` 和 `technical_solution_task_id`。

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

该接口必须先校验 `knowledge.read`，再支持 `keyword`、`knowledge_space_id`、`folder_id`、`doc_type`、`index_status`、`permission_role`、`page`、`page_size`、`sort_by` 和 `sort_order`。`sort_by` 白名单为 `id/title/doc_type/folder_id/index_status/knowledge_space_id/permission_roles/created_at/updated_at`，`sort_order` 只允许 `asc|desc`，`page_size` 最大 100。传入 `page` 或 `page_size` 时，PostgreSQL 运行态必须通过知识文档 read model 在数据库侧完成知识空间权限、角色权限、关键字、空间、目录、类型、索引状态、权限角色筛选和排序分页，并返回 `items/page/page_size/total/query/performance`；未传分页参数时保留旧全量返回兼容用途，不作为知识中心主表默认读路径。

知识文档索引状态支持：`importing | pending_index | text_indexed | vector_indexed | indexed | index_failed | archived`，其中 `indexed` 为历史兼容状态。Embedding 不可用但文本 chunk 成功时进入 `text_indexed`，响应包含 `vector_index_error` 和兼容展示用 `index_error`；基础文本索引失败时进入 `index_failed`。

前端知识中心必须调用 `GET /api/knowledge/index-health` 展示“索引健康”视图，并复用当前筛选条件汇总可检索文档、向量就绪文档、关键词兜底文档、索引失败文档、处理中任务、已生效分块版本数、文档状态分布和 Chunk/Embedding 覆盖率；首屏需展示“解析状态”“Chunk & Embedding”“检索与权限”三段治理摘要，分别说明文档状态、分块/向量覆盖、召回模式、Embedding 模型和权限命中范围。健康问题行必须同时展示文档索引状态和具体处理动作；`index_failed` 行提供重试索引入口，`text_indexed` 行提供补建向量索引入口，缺少 `active_chunk_set_id` 的可检索文档提供分块查看入口，`importing/pending_index` 文档提供导入任务入口。该视图代表服务端按当前用户知识权限和筛选范围聚合的全量健康结果，不得再只用当前分页列表推断全库健康。

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

前端知识中心提供“知识检索”弹窗，提交真实 `/api/knowledge/search` 请求并展示可访问结果的标题、来源、召回模式和内容摘要；后端返回 chunk 级命中结果，权限过滤必须在返回 chunk 前完成。存在可读向量 chunk 且 Embedding 网关可用时查询文本会生成 embedding，并只和 `embedding_config_id`、`embedding_model`、`embedding_dimension` 兼容的 chunk 计算 cosine 相似度，返回 `score` 与 `retrieval_mode=vector`；不兼容、缺失或仅文本索引可用时按关键词检索返回 `retrieval_mode=keyword` 且 `score=null`。启用 `parent_child` 时父块不作为直接命中结果返回，子块命中会在 `source.parent_chunk_id` 和 `source.parent_content` 中补充父块上下文；OCR/Table 导入的命中 chunk metadata 可包含页码、图片数量、图片引用、表格数量、表格序号、列名和结构化解析资产引用。无结果时展示真实空状态，不回退到示例数据。每次搜索会写入 `knowledge_quality_events`，响应 `metrics.quality_event_id` 可用于后续反馈关联。

RAG 问答和质量反馈：

```http
POST /api/knowledge/rag
GET /api/knowledge/quality/metrics
POST /api/knowledge/quality/feedback
POST /api/knowledge/quality/citation-click
```

`POST /api/knowledge/rag` 复用 Hybrid Search 返回 `answer`、`citations[]` 和 `metrics`，其中 `metrics` 包含 `citation_count`、`hit_count`、`latency_ms`、`no_result`、`no_result_rate`、`rag_citation_accuracy_proxy`、`retrieval` 和 `quality_event_id`。`GET /api/knowledge/quality/metrics` 要求 `knowledge.quality.read` 或知识管理权限，支持 `event_type`、`limit` 和 `since_days`，返回最近事件和汇总指标：检索/RAG 查询数、无结果率、引用数、引用点击率、反馈数、有用/无用反馈数和 RAG 引用准确率 proxy。`POST /api/knowledge/quality/feedback` 接收 `related_event_id`、`feedback_value=useful|not_useful|partial|incorrect`、可选 `feedback_comment`、`citation_chunk_id`、`citation_document_id`；`POST /api/knowledge/quality/citation-click` 接收 `related_event_id` 和可选引用 chunk/document ID，用于统计引用点击。质量事件不得保存完整 Prompt、模型输出或密钥。

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
