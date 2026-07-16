# 边界、异常、API、性能与执行记录

> 来源：../test-case.md。该文件按业务域承接详细测试用例，主入口保留索引与通用规范。

## 边界测试用例

| 用例编号 | 边界类型 | 测试数据 | 预期结果 |
|----------|----------|----------|----------|
| TC-AIBRAIN-TASK-BOUND-001 | 空标题 | `title = ""` | 返回 `VALIDATION_ERROR`。 |
| TC-AIBRAIN-KNOWLEDGE-BOUND-002 | top_k 超过上限 | `top_k = 1000` | 按最大允许值截断或返回校验错误。 |
| TC-AIBRAIN-REVIEW-BOUND-003 | 重复确认 | 同一 review 连续 approve 两次 | 第二次返回状态错误或版本冲突。 |
| TC-AIBRAIN-AUDIT-BOUND-004 | 空审计结果 | 不存在的 ai_task_id | 返回空列表，不报 500。 |

---

## 异常测试用例

| 用例编号 | 异常类型 | 触发条件 | 预期结果 |
|----------|----------|----------|----------|
| TC-AIBRAIN-AUTH-ERR-001 | 未授权 | 无 Bearer Token 调用写接口 | 返回 `UNAUTHORIZED`。 |
| TC-AIBRAIN-TASK-ERR-002 | 绕过研发协作 | 人工或公开调用方直接创建、启动或批量重试研发 AI 任务 | 返回 `RD_COLLABORATION_REQUIRED`，不创建执行实例、不改变任务或工作项状态，并记录被拒绝的绕过尝试。 |
| TC-AIBRAIN-REVIEW-ERR-003 | 版本冲突 | 使用过期 version 确认 | 返回 `REVIEW_VERSION_CONFLICT`。 |
| TC-AIBRAIN-GRAPH-ERR-004 | 模型失败 | 模型网关返回错误 | 任务进入 failed 或可重试状态，记录审计。 |
| TC-AIBRAIN-KNOWLEDGE-ERR-005 | embedding 维度不匹配 | embedding 写入 pgvector 失败 | 文档保持 `text_indexed`，记录 `vector_index_error`，关键词检索仍返回带来源结果。 |
| TC-AIBRAIN-KNOWLEDGE-ERR-006 | 知识索引失败 | 文档内容无法切片，或非 `index_failed`/`text_indexed` 文档调用 retry-index | 基础文本索引失败时文档进入 `index_failed` 并保留失败原因；状态不匹配返回 `KNOWLEDGE_INDEX_STATE_INVALID`。 |

---

## API 测试用例

| 用例编号 | 接口 | 场景 | 预期结果 |
|----------|------|------|----------|
| TC-AIBRAIN-TASK-API-001 | POST /api/ai-tasks | 人工或公开调用方直接创建研发任务 | 返回 409 `RD_COLLABORATION_REQUIRED`；研发任务只能由协作运行针对已就绪工作项调用内部服务 `create_ai_task_for_work_item` 创建；不产生成功创建审计。 |
| TC-AIBRAIN-TASK-API-002 | GET /api/ai-tasks/{id} | 查询无权限任务 | 403 或 404；端点由 `app.api.routers.tasks` 单一路由注册。 |
| TC-AIBRAIN-TASK-API-019 | POST /api/ai-tasks | 尝试直接创建任一研发全链路 task_type | 所有研发任务类型统一返回 409 `RD_COLLABORATION_REQUIRED`；任务类型由工作项模板和冻结策略确定，公开接口不得覆盖。 |
| TC-AIBRAIN-TASK-API-020C | POST /api/ai-tasks/batch-cancel | 批量取消任务 | 合法未完成任务进入 `cancelled`；终态、重复和不存在任务返回 skipped；写入 `ai_task.batch_cancelled` 和逐任务 `ai_task.cancelled` 审计；端点由 `app.api.routers.tasks` 单一路由注册。 |
| TC-AIBRAIN-TASK-API-020D | POST /api/ai-tasks/batch-retry | 人工批量重试研发任务 | 返回 409 `RD_COLLABORATION_REQUIRED`；失败恢复由工作项调度器按 attempt、幂等键和策略重试上限执行，人工只能处理对应 decision request 或重置工作项。 |
| TC-AIBRAIN-REVIEW-API-003 | POST /api/reviews/{id}/edit-approve | 修改后采纳 | 保存 edited_content 并恢复 graph；端点由 `app.api.routers.tasks` 单一路由注册。 |
| TC-AIBRAIN-KNOWLEDGE-API-004 | POST /api/knowledge/search | 正常检索 | 返回 items，包含 title、snippet、source。 |
| TC-AIBRAIN-OUTPUT-API-005 | GET /api/export/tasks/{task_id}/markdown | MVP-A 导出方案 | 返回 `text/markdown`，并通过 Header 或日志关联 trace_id。 |
| TC-AIBRAIN-AUDIT-API-006 | GET /api/audit/events?ai_task_id={id} | 按任务查询 | 返回 items，最多 120 条；响应包含查询和性能观测元数据，audit router 不回调 legacy main。 |
| TC-AIBRAIN-AUDIT-API-013 | GET /api/audit/events?subject_type={type}&subject_id={id} | 按主体查询 | 返回指定主体的审计事件；支持服务端筛选、排序、分页和非法排序字段校验。 |
| TC-AIBRAIN-CONFIG-API-008D | POST /api/product-versions/{version_id}/advance-status | 版本状态推进 | 支持 preview_only 影响预览；确认推进后按版本阶段同步需求状态；阻塞项返回稳定错误码；普通 PATCH 改状态返回 `PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED`。 |
| TC-AIBRAIN-CONFIG-FUNC-008E | GET/POST/PATCH/DELETE /api/product-versions/{version_id}/branch-configs | 迭代版本代码分支配置 | 同一版本可维护多个代码库分支；同一版本同一仓库只允许一条配置；仓库必须属于同产品；分支配置写入 `product_version_branch_configs` 并记录审计。 |
| TC-AIBRAIN-REQ-API-011E | POST /api/requirements/batch-schedule | 人工批量调整规划版本归组 | 仅已接受评估、目标为 `planning` 且产品、容量、仓库、交付终点和依赖硬条件全部兼容的需求进入 `planned`；不兼容项 skipped，高风险或候选争议项保持原状态并创建 decision request；写入归组决策与逐需求审计。 |
| TC-AIBRAIN-REQ-API-011F | POST /api/requirements/batch-generate-tasks | 尝试绕过协作运行批量生成任务 | 返回 409 `RD_COLLABORATION_REQUIRED`；不创建任务、不推进需求状态、不写成功审计，页面不提供该操作入口。 |
| TC-AIBRAIN-REQ-API-011G | POST /api/requirements/batch-assign-owner | 多需求批量分配负责人 | 非关闭/非取消需求更新 `assignee` 且状态不变化；关闭、取消、重复和不存在需求返回 skipped；写入 `requirement.batch_owner_assigned` 和逐条 `requirement.updated` 审计；端点由 `app.api.routers.requirements` 单一路由注册。 |
| TC-AIBRAIN-REQ-API-011H | POST /api/requirements/batch-advance-status | 尝试批量推进研发交付状态 | 任何交付目标状态均返回 409 `RD_COLLABORATION_REQUIRED`；仅既无活动协作运行、也不存在非终态工作项的需求可按安全规则批量 `cancelled/closed`，且不得写入 `requirement.batch_status_advanced` 成功审计。 |
| TC-AIBRAIN-DEVOPS-API-014 | GET/POST /api/devops/gitlab/daily-code-metrics | 登记和查询 GitLab 每日指标 | 仅产品负责人、研发负责人或管理员可登记；产品和 GitLab 仓库归属校验通过后写入 `gitlab_daily_code_metrics` 并记录审计；GET 按产品、仓库和日期返回真实记录，无数据时返回空集合。 |
| TC-AIBRAIN-DEVOPS-API-023 | GET/POST/PATCH /api/collectors/runs | 查询、登记和更新采集运行记录 | GET 返回真实运行台账；POST/PATCH 仅产品负责人、研发负责人或管理员可写，写入 `collector_runs` 并记录 `collector_run.created/updated`；failed 必须有错误说明，终态不可回退。 |
| TC-AIBRAIN-OPS-API-015 | GET/POST /api/ops/online-log-metrics | 登记和查询线上运行日志指标 | 仅产品负责人、研发负责人或管理员可登记；产品和模块归属校验通过后写入 `online_log_metrics` 并记录审计；GET 按产品、模块、环境和时间窗口返回真实记录，无数据时返回空集合。 |
| TC-AIBRAIN-RELEASE-API-016 | GET/POST /api/devops/jenkins/releases | 登记和查询 Jenkins 发布 | 返回发布状态、失败原因，写入 `jenkins_release_records` 并记录审计。 |
| TC-AIBRAIN-DASHBOARD-API-017 | GET /api/dashboard/it-team | 查询首页 IT 团队看板 | 返回需求、研发、Bug、线上系统、核心业务和发布统计。 |
| TC-AIBRAIN-LIFECYCLE-API-021 | GET /api/lifecycle/context | 查询软件研发全流程感知 | 返回上下游关系、风险信号、影响摘要和建议；MVP 证据主体起点只返回对应任务链路。 |
| TC-AIBRAIN-PLANNING-API-026 | GET/POST /api/insights/usage-metrics | 登记和查询用户使用指标 | 仅产品负责人、研发负责人或管理员可登记；计数和比率校验通过后写入 `user_usage_metrics` 并记录审计；GET 按产品、模块、功能、用户群体和时间范围返回真实记录，无数据时返回空集合。 |
| TC-AIBRAIN-PLANNING-API-022 | GET/POST /api/planning/iteration-suggestions | 查询或生成 AI 迭代规划建议 | 基于真实用户反馈和 Bug 证据返回建议清单、优先级、证据链、价值、风险、依赖和投入评估；无证据时返回空集合；生成阶段不自动创建正式需求或调整路线图/排期。 |
| TC-AIBRAIN-PLANNING-API-023 | POST /api/planning/iteration-suggestions/{suggestion_id}/decide | 产品负责人确认迭代规划建议 | accepted/edited_accepted 且 `convert_to_requirement=true` 后才允许转正式需求，未确认时保持 suggested 状态。 |
| TC-AIBRAIN-BUG-API-018 | GET/POST/PATCH /api/bugs, POST /api/bugs/batch-update | Bug 查询、登记、状态更新和批量处理 | 支持按产品、迭代版本、状态、严重级别和来源查询，列表返回版本编码/名称；支持 AI 自动测试、AI 上线后分析和人工测试来源，状态正确流转；批量接口返回 updated/skipped 明细并写入批次审计；Bug 管理端点由 `app.api.routers.bugs` 单一路由注册；前端工作台展示迭代版本并保存复现步骤、证据 JSON、重复归并和只读来源展示。 |
| TC-AIBRAIN-AUTH-API-024 | GET /api/auth/roles + POST/PATCH /api/users | 查询角色目录并按目录维护用户角色 | 返回 `admin/product_owner/rd_owner/reviewer/knowledge_owner/viewer` 六个角色及业务角色映射、职责、数据范围、决策范围、可见入口和限制边界；`/api/auth/*` 认证和角色目录端点由 `app.api.routers.auth` 单一路由注册；`/api/users` 用户管理端点由 `app.api.routers.users` 单一路由注册；未知角色返回 `VALIDATION_ERROR`。 |
| TC-AIBRAIN-KNOWLEDGE-API-025 | POST /api/knowledge/documents/{document_id}/retry-index | 重试失败知识文档索引或补建向量索引 | `index_failed` 文档可重建文本/向量索引，`text_indexed` 文档可补建向量索引；成功后进入 `text_indexed` 或 `vector_indexed`，状态不匹配返回 `KNOWLEDGE_INDEX_STATE_INVALID`。 |
| TC-AIBRAIN-ASSISTANT-API-027 | POST /api/assistant/chat + GET /api/assistant/conversations | AI 助手系统问答与历史 | 基于服务端注入的脱敏系统上下文和 Chat 模型网关返回助手回答，系统上下文覆盖产品、迭代进度、阻塞需求、待确认 Review、代码评审结论、Bug 分布、知识沉淀、Git 仓库和模型网关状态；聊天响应和历史 assistant 消息返回 references 来源链接；按当前用户保存会话和消息，其他用户不可读取；模型日志只记录 `purpose=assistant_chat` 元数据，不保存完整问题或回答。 |
| TC-AIBRAIN-ASSISTANT-API-027B | GET /api/assistant/action-drafts + POST /api/assistant/action-drafts/{draft_id}/view | AI 助手草案任务台 | 当前用户可分页筛选自己的动作草案，PostgreSQL 运行态优先由草案任务台 read model 完成当前用户、动作、状态、时间、关键词、排序和分页；列表返回状态、预检、查看次数、修改字段数、结果资源和 summary；页面基于 summary 和当前页行展示权限阻断、校验阻断、失败重试、高风险和审计缺口治理优先队列，并给出代表草案处理入口；详情查看写入 view 元数据和审计；确认/取消仍走草案生命周期接口，不从聊天历史或前端缓存拼装主列表。 |
| TC-AIBRAIN-CONFIG-API-008 | GET/POST/PATCH 产品配置接口 | 配置产品上下文 | 返回 items 或配置详情，写操作产生审计；业务大脑只读端点由 `app.api.routers.brain_apps` 单一路由注册；产品主体 CRUD 端点由 `app.api.routers.products` 单一路由注册；迭代版本端点由 `app.api.routers.product_versions` 单一路由注册；产品模块端点由 `app.api.routers.product_modules` 单一路由注册；产品 Git 仓库端点由 `app.api.routers.product_git_repositories` 单一路由注册；相关系统端点由 `app.api.routers.related_systems` 单一路由注册。 |
| TC-AIBRAIN-CONFIG-API-009 | GET/POST/PATCH /api/system/model-gateway-configs | 配置平台模型网关 | 返回 api_key_configured 和 embedding_api_key_configured，不返回明文或密钥片段；Embedding 支持 disabled/reuse_chat/custom，Chat-only 配置可保存并驱动 AI 任务，custom Embedding 连接用于知识向量索引；配置和日志端点由 `app.api.routers.model_gateway` 单一路由注册，配置测试与运行时 helper 由 `app.services.model_gateway` 维护。 |

---

## 性能测试用例

| 用例编号 | 指标 | 测试方式 | 目标 |
|----------|------|----------|------|
| TC-AIBRAIN-TASK-PERF-001 | 任务详情接口 | 并发查询任务详情 | P95 < 500ms。 |
| TC-AIBRAIN-KNOWLEDGE-PERF-002 | 知识检索 | 1000 个 chunk 数据集执行 top_k 检索 | P95 < 1s。 |
| TC-AIBRAIN-AUDIT-PERF-003 | 审计查询 | 按 ai_task_id 查询 | P95 < 500ms。 |
| TC-AIBRAIN-DASHBOARD-PERF-004 | 首页 IT 团队看板 | 读取 30 天产品指标快照 | P95 < 800ms。 |
| TC-AIBRAIN-OPS-PERF-005 | 线上运行日志指标查询 | 按产品和环境查询 24 小时窗口 | P95 < 1s。 |
| TC-AIBRAIN-LIFECYCLE-PERF-006 | 软件研发全流程感知查询 | 从需求查询两跳上下游和风险信号 | P95 < 1s。 |
| TC-AIBRAIN-PLANNING-PERF-007 | 用户洞察和迭代规划查询 | 读取 30 天产品使用、反馈和规划建议聚合快照；用户洞察主列表在 PostgreSQL 运行时使用 SQL read model 和更新时间排序索引。 | P95 < 800ms。 |

---

## 测试执行记录

### 执行汇总

| 批次 | 执行日期 | 执行人 | 用例总数 | 通过 | 失败 | 阻塞 | 通过率 |
|------|----------|--------|----------|------|------|------|--------|
| 1 | 2026-05-29 |  | 待执行统计 |  |  |  |  |

### 缺陷追踪

| 缺陷编号 | 关联用例 | 缺陷描述 | 严重程度 | 状态 | 修复版本 |
|----------|----------|----------|----------|------|----------|
|  |  |  |  |  |  |

---
最后更新: 2026-06-05
