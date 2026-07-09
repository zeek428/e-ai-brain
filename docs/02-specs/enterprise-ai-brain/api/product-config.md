# 产品配置 API

> API 分册。覆盖产品、迭代版本、模块、Git 仓库、相关系统归属、版本分支和版本驾驶舱。主入口见 [../api.md](../api.md)，分册组索引见 [system-governance-and-platform.md](system-governance-and-platform.md)。

### 产品配置

查询接口都支持 `active_only=true|false`：

```http
GET /api/products?active_only=true
GET /api/products/{product_id}/members
GET /api/products/{product_id}/member-candidates
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
PUT /api/products/{product_id}/members
POST /api/products/{product_id}/versions
PATCH /api/product-versions/{version_id}
POST /api/product-versions/{version_id}/advance-status
GET /api/product-versions/{version_id}/dashboard
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

产品成员维护接口：

```http
GET /api/products/{product_id}/members
GET /api/products/{product_id}/member-candidates
PUT /api/products/{product_id}/members
```

`GET /api/products/{product_id}/members` 要求 `product.member.read`，并按当前用户产品 scope 校验产品可见性，响应返回 `revision` 用于后续并发保存校验；`GET /api/products/{product_id}/member-candidates` 和 `PUT /api/products/{product_id}/members` 要求 `product.member.manage`，仅允许具备当前产品管理范围的用户维护。全局产品管理员可以直接查看成员候选列表，产品范围内的成员管理员必须通过 `keyword` 搜索候选人且关键字至少 2 个字符，避免无条件暴露全量用户目录。产品成员保存采用整体替换语义，后端会把成员职责派生为产品 scope 和对应权限，并记录 `product.members.updated` 审计事件；当请求携带 `expected_revision` 且与当前成员列表不一致时返回 `409 PRODUCT_MEMBERS_CONFLICT`。

产品成员保存请求：

```json
{
  "expected_revision": "6f6f6b7c...",
  "members": [
    {
      "user_id": "user_001",
      "member_role": "product_owner",
      "scope_type": "product",
      "scope_id": "*"
    },
    {
      "user_id": "user_002",
      "member_role": "developer",
      "scope_type": "product",
      "scope_id": "*"
    }
  ]
}
```

成员职责由服务端返回中文展示名，当前支持产品经理、研发负责人、开发工程师、测试负责人、测试人员、运维/发布负责人和观察者；前端不得直接向业务用户展示 `member_role` 编码。

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
- `git_provider` 支持 `gitlab` 和 `github`。产品配置默认填写 `remote_url`，后端会从可解析的 HTTPS/SSH Remote URL 推导 `project_path`；GitLab 绑定也可显式提供 `project_id` 或 `project_path` 覆盖，GitHub 绑定也可显式提供 `project_path=owner/repo`。编辑 Git 资源时，显式提交 `project_path` 表示手工覆盖；仅修改 `remote_url` 且未提交 `project_path` 时，后端重新从新的 Remote URL 推导 `project_path`。
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

迭代版本驾驶舱请求：

```http
GET /api/product-versions/version_001/dashboard
```

响应按版本聚合交付健康：

```json
{
  "data": {
    "version": {
      "id": "version_001",
      "code": "2026-06",
      "name": "2026-06 迭代",
      "product_id": "product_001",
      "product_name": "AI Brain",
      "status": "active"
    },
    "summary": {
      "requirements": 7,
      "tasks": 3,
      "branch_configs": 2,
      "branch_quality_action_required": 1,
      "branch_quality_accepted_risks": 1,
      "branch_quality_active_severe_findings": 2,
      "branch_quality_expired_accepted_risks": 1,
      "branch_quality_false_positives": 1,
      "branch_quality_pending_scan": 0,
      "branch_quality_pending_suppressions": 1,
      "bugs": 4,
      "open_bugs": 2,
      "severe_bugs": 1,
      "code_inspection_reports": 1,
      "severe_code_inspection_reports": 1,
      "code_review_reports": 1,
      "pending_code_review_reports": 1,
      "knowledge_deposits": 1,
      "searchable_knowledge_deposits": 1,
      "vectorized_knowledge_deposits": 0,
      "releases": 1,
      "blockers": 3
    },
    "status_impact": {
      "target_status": "testing",
      "updated_requirements": [],
      "blocked_requirements": [],
      "unchanged_requirements": []
    },
    "blockers": [
      {
        "source_type": "bug",
        "id": "bug_001",
        "title": "发布阻塞 Bug",
        "severity": "high",
        "reason": "critical Bug 仍未关闭",
        "action_label": "处理 Bug",
        "action_target_type": "bug",
        "action_target_id": "bug_001",
        "resolution_hint": "修复、验证并关闭 blocker/critical Bug 后解除发布阻塞。"
      }
    ],
    "next_actions": [
      {
        "priority": 1,
        "source_type": "bug",
        "source_label": "Bug",
        "id": "bug_001",
        "title": "发布阻塞 Bug",
        "severity": "high",
        "reason": "critical Bug 仍未关闭",
        "action_label": "处理 Bug",
        "action_target_type": "bug",
        "action_target_id": "bug_001",
        "resolution_hint": "修复、验证并关闭 blocker/critical Bug 后解除发布阻塞。",
        "full_chain_subject_type": "bug",
        "full_chain_subject_id": "bug_001"
      }
    ],
    "branch_quality_governance": [
      {
        "id": "branch_config_001",
        "branch_config_id": "branch_config_001",
        "repository_id": "repo_001",
        "repository_name": "AI Brain API",
        "branch": "release/2026-06",
        "status": "action_required",
        "report_count": 1,
        "finding_count": 8,
        "severe_finding_count": 2,
        "active_severe_finding_count": 2,
        "created_bug_count": 2,
        "created_task_count": 1,
        "uncovered_severe_bug_count": 0,
        "uncovered_severe_task_count": 1,
        "false_positive_count": 1,
        "accepted_risk_count": 1,
        "expired_accepted_risk_count": 1,
        "suppressed_finding_count": 2,
        "pending_suppression_count": 1,
        "quality_gate_failed_report_count": 1,
        "quality_gate_violation_count": 2,
        "latest_report_id": "code_inspection_report_001",
        "latest_report_summary": "质量门禁失败",
        "latest_report_time": "2026-06-04T09:30:00+00:00"
      }
    ],
    "knowledge_deposits": [
      {
        "id": "deposit_001",
        "title": "版本发布准入知识沉淀",
        "status": "approved",
        "ai_task_id": "task_001",
        "task_title": "版本发布准入自动化",
        "knowledge_document_id": "knowledge_001",
        "knowledge_document_title": "版本发布准入知识文档",
        "knowledge_index_status": "text_indexed",
        "knowledge_retrieval_mode": "keyword",
        "knowledge_chunk_count": 4,
        "knowledge_embedding_chunk_count": 0,
        "knowledge_index_error": "Embedding 网关未配置，已降级为关键词检索。",
        "updated_at": "2026-06-04T09:40:00+00:00"
      }
    ],
    "governance_conclusion": {
      "title": "版本治理结论",
      "value": "版本暂不建议推进",
      "level": "error",
      "detail": "当前版本有 3 个发布阻塞项，未关闭 Bug 1 个，门禁失败 1 份，状态推进阻塞需求 0 条。",
      "risks": ["发布阻塞 3", "未关闭 Bug 1", "门禁失败 1"],
      "next_action": "先处理阻塞队列中的 Bug、发布记录和分支问题，再重新查看推进影响。"
    },
    "delivery_stage_overview": [
      {
        "key": "requirements",
        "title": "需求范围",
        "value": "范围可推进",
        "detail": "7 条需求 · 可推进",
        "level": "success",
        "action_label": "查看需求",
        "action_target_type": "requirements",
        "action_target_id": "version_001",
        "full_chain_subject_type": null,
        "full_chain_subject_id": null
      }
    ],
    "access_issues": []
  },
  "trace_id": "trace_xxx"
}
```

规则：接口要求 `product.read`，并在聚合前按版本归属产品校验当前用户产品 scope；scope 外返回 404。`requirements/tasks/branch_configs/releases/status_impact` 随 `product.read` 返回；`bugs` 和 `bug_status_counts` 仅在用户具备 `bug.read` 时返回，否则在 `access_issues` 中声明隐藏；`code_inspection_reports` 和 `branch_quality_governance` 仅在具备 `code_inspection.read` 时返回，否则同样降级隐藏；`knowledge_deposits` 仅在具备 `knowledge.read` 时返回，否则在 `access_issues` 中声明隐藏。知识沉淀明细只暴露沉淀 ID、标题、状态、来源任务、关联知识文档、知识文档标题、索引状态、chunk 数、embedding chunk 数、检索模式、索引错误摘要和更新时间，不返回知识正文；`knowledge_retrieval_mode=keyword` 表示关键词兜底，`hybrid` 表示向量与关键词可混合检索，`unavailable` 表示当前沉淀不可检索。summary 中 `searchable_knowledge_deposits` 统计可关键词或混合检索的沉淀，`vectorized_knowledge_deposits` 统计混合检索沉淀；`branch_quality_action_required` 统计存在门禁失败、活跃严重问题、过期接受风险、待审批忽略或严重问题缺 Bug/整改覆盖的版本分支，`branch_quality_pending_scan` 统计已配置但暂无巡检报告的版本分支，`branch_quality_active_severe_findings`、`branch_quality_false_positives`、`branch_quality_accepted_risks`、`branch_quality_expired_accepted_risks` 和 `branch_quality_pending_suppressions` 按分支报告 finding 聚合治理计数。`blockers` 聚合需求推进阻塞、未关闭严重 Bug、高风险或质量门禁失败的代码巡检报告、失败发布记录，以及进入测试或发布前不满足要求的版本分支状态；每条 blocker 必须返回处理动作、目标主体和解除条件，前端将其映射为需求、Bug、代码巡检、版本分支或发布记录处理入口。`next_actions` 由后端按 blockers 的严重级别、来源类型、标题和目标 ID 排序后截取前三条，必须返回 `priority/source_label/full_chain_subject_type/full_chain_subject_id`，供版本总览首屏、AI 助手问答和真实全链路回归脚本复用同一处理建议；无阻塞时返回空数组。`governance_conclusion` 由后端基于 summary、blockers、分支质量治理和 `status_impact` 统一生成，返回 `title/value/level/detail/risks/next_action`，供版本总览、AI 助手和回归脚本复用；前端仅在旧响应缺失该字段时基于 dashboard 本地兜底推导。`delivery_stage_overview` 由后端生成，固定返回 `requirements/tasks/branches/inspections/code-reviews/bugs/knowledge-deposits/releases/status-impact` 九类阶段，每项包含 `key/title/value/detail/level`，可处理阶段包含 `action_label/action_target_type/action_target_id`，并在可追踪时返回 `full_chain_subject_type/full_chain_subject_id`；版本总览、AI 助手和回归脚本必须优先复用该字段，旧响应缺失时才允许前端本地兜底推导。`evidence_coverage` 由后端生成，固定覆盖同九类证据域，返回 `covered_domains/gap_domains/blocking_domains/total_domains/score/level/summary/domains[]`；`domains[]` 每项包含 `key/title/value/detail/level/status/action_label/action_target_type/action_target_id`，缺少 `bug.read`、`code_inspection.read` 或 `knowledge.read` 时对应域返回 `status=inaccessible`，用于首屏证据覆盖和权限缺口提示。前端迭代版本页“驾驶舱”弹窗必须优先展示 summary、版本治理结论、证据覆盖、交付健康摘要、status impact 和 blockers，再展示可读明细表；summary 指标区必须展示待治理分支、门禁失败、待审批忽略和到期风险；交付链路总览必须基于后端 `delivery_stage_overview` 展示阶段处理入口，直接跳转需求、首个任务或产品任务列表、版本分支、代码巡检、代码评审、版本 Bug、知识沉淀、发布记录或触发状态推进；交付健康摘要基于阻塞项、严重 Bug/巡检、分支创建状态、分支质量治理、代码巡检风险、知识沉淀可检索状态和发布失败记录派生发布准入、质量风险、代码分支、代码巡检、知识沉淀和发布流水线结论，代码巡检结论必须直接说明门禁失败、待审批忽略和到期风险。
