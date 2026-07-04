# API 公共约定与基础接口

> API 分册。主入口见 [../api.md](../api.md)。

## 概述

本文档定义企业 AI 大脑平台 v1 系列的 API 契约。后续版本直接维护本文档。

API 面向 React 工作台，覆盖认证、业务大脑、AI 助手、产品上下文、研发全链路 AI 任务、GitLab MR / GitHub PR 代码 Review、软件研发全流程感知、人工确认、Bug 管理、知识中心、模型网关配置、GitLab 代码质量、线上运行日志、Jenkins 发布、用户使用洞察、用户反馈、AI 迭代规划建议、首页 IT 团队看板、模拟回写、Markdown 导出和审计查询。

当前源码实现说明：MVP 骨架已实现认证、AI 助手、产品/需求/任务/Review/知识/审计/导出/GitLab MR 与 GitHub PR 只读预览、diff 快照、code_review 报告闭环。AI 助手通过模型网关 Chat 能力回答 AI Brain 系统相关问题，请求会携带脱敏系统上下文摘要，包括产品、迭代版本进度、需求、AI 任务、待确认 Review、最近代码评审结论、Bug 分布、高风险 Bug、知识沉淀、Git 仓库和模型网关配置状态；服务端会先按用户问题生成 `tool_results`，覆盖 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等 read-model 工具结果，并和 `reference_candidates` 一起注入模型请求。聊天响应和历史消息返回 `references` 与 `tool_results`，用于跳转到产品、迭代、需求、任务、Review、Bug、代码评审报告或知识沉淀并解释回答依据；当引用主体可解析为需求交付链路时，前端还必须展示统一“全链路”入口，`iteration_version` 和 `product_version` 引用均按 `/api/lifecycle/full-chain` 的版本主体处理，`code_inspection_report` 引用可从助手仓储上下文解析并进入代码巡检报告详情或统一 full-chain。模型日志只记录 `purpose=assistant_chat` 元数据，不保存完整用户消息、系统上下文或助手回答；完整对话内容按当前登录用户写入助手会话与消息结构表，并且历史查询只返回本人会话。产品配置、需求、知识文档、Bug、用户管理、用户反馈和模型网关配置已具备当前管理页所需 CRUD 能力，删除接口会对已被需求、任务或关联资源占用的主体返回 `RESOURCE_IN_USE`；用户使用指标已具备真实登记和查询能力。MVP 明确定义 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 六个可分配角色，`GET /api/auth/roles` 返回角色目录、业务角色映射、职责、数据范围、决策范围、可见入口、限制边界、权限点和排序信息，系统管理下的角色管理页面只读展示该目录，用户管理和知识权限配置只能从该目录选择角色，不得自由创建或录入未定义角色。

产品管理页面可维护产品、模块、Git 资源和产品相关系统；需求交付下的迭代版本页面维护 `product_versions`，用于需求排期和任务版本上下文。`GET /api/product-versions` 支持批量查询版本并返回 `product_code`、`product_name` 投影，`active_only=true` 只返回 active 版本；`GET /api/requirements` 返回需求主体同时带 `product_code`、`product_name`、`version_code`、`version_name` 和 `assignee`；`POST /api/requirements/batch-assign-owner` 支持将非关闭/非取消需求批量分配负责人，并返回 updated/skipped 明细；`POST /api/requirements/batch-schedule` 支持将多条同产品 `approved/planned` 需求批量归集到 `planning` 或 `active` 迭代版本，并返回 updated/skipped 明细；`POST /api/requirements/batch-generate-tasks` 支持将多条同产品 `planned` 需求批量生成产品详细设计任务，并返回 generated/skipped 明细；`GET /api/ai-tasks` 在 PostgreSQL 模式按产品表 SQL join 返回 `product_name`，并支持 `product_id`、`created_from`、`created_to` 等筛选；`POST /api/ai-tasks/batch-cancel` 支持任务管理多选批量取消，逐条校验任务状态并返回 updated/skipped 明细；`POST /api/ai-tasks/batch-retry` 支持任务管理多选批量重试，逐条校验失败步骤并返回 retried/updated/skipped 明细。产品、版本、模块、Git 资源、相关系统、需求台账、AI 任务核心字段、人工确认、Graph Run、检查点、GitLab MR 快照、Code Review 报告、知识文档、知识 chunk、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属数据队列、迭代规划建议/确认、模拟 Issue 回写、模型网关配置、模型调用元数据、AI 助手会话和助手消息会同步写入 PostgreSQL 结构表 `products`、`product_versions`、`product_modules`、`product_git_repositories`、`related_systems`、`requirements`、`ai_tasks`、`human_reviews`、`graph_runs`、`graph_checkpoints`、`gitlab_mr_snapshots`、`code_review_reports`、`knowledge_documents`、`knowledge_chunks`、`knowledge_deposits`、`audit_events`、`bugs`、`gitlab_daily_code_metrics`、`jenkins_release_records`、`online_log_metrics`、`user_feedback`、`user_usage_metrics`、`collector_runs`、`pending_attribution_items`、`iteration_plan_suggestions`、`iteration_plan_decisions`、`mock_issues`、`model_gateway_configs`、`model_gateway_logs`、`assistant_conversations`、`assistant_messages`。所有 PostgreSQL 结构表必须包含 `created_at` 与 `updated_at` 标准时间字段；新增表必须在建表 SQL 中定义这两个字段，既有环境通过 `018_standard_timestamps.sql` 可重复迁移补齐。Git 资源列表只展示凭据是否已配置，不返回凭据引用或 token 明文。

知识文档创建、更新和知识沉淀采纳会同步重建文本 chunk，并在 active/default OpenAI-compatible 模型网关或环境模型网关支持 `/embeddings` 时生成 `knowledge_chunks.embedding`；Embedding 不可用时文档进入 `text_indexed`，保留 `vector_index_error`/兼容 `index_error`，关键词检索继续可用；Embedding 成功时进入 `vector_indexed`，历史 `indexed` 仅作为兼容状态读取；知识文档可选绑定 `product_id` 作为产品归属上下文，首页 IT 团队看板按产品筛选时只统计该产品归属或该产品任务沉淀产生的知识文档；基础文本索引失败才进入 `index_failed`、保留 `index_error` 并清理旧 chunk，`/api/knowledge/documents/{document_id}/retry-index` 可重建失败索引或将 `text_indexed` 补建为向量索引；`/api/knowledge/search` 先按文档和 chunk 权限过滤，再对有 embedding 的 chunk 执行向量排序并返回真实存在的 chunk 内容、`chunk_id`、`chunk_index`、`retrieval_mode`、`score` 和来源引用，没有可读向量 chunk 时不调用 query embedding 并直接走关键词检索，不返回无权限 chunk，也不为缺失 chunk 的 indexed 文档合成整篇文档结果。GitLab MR 预览和快照读取产品 Git 资源的 `remote_url` 或 `GITLAB_BASE_URL`，GitHub PR 列表、预览和快照读取 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`，并通过环境变量、服务端密钥引用或本地直填只读 token 解析凭据；MR/PR 预览响应除基础元信息外，还返回 `changed_files_summary`、`diff_file_tree`、`risk_summary` 和 `review_checklist`，任务中心创建 Code Review 前据此展示变更范围、风险摘要和人工检查项；缺少 provider 地址、仓库路径或凭据时返回明确错误，不生成本地假 MR/PR。

模型网关配置可由具备 `system.model_gateway.manage` 的用户在系统管理页面维护，不再把固定 admin 角色作为唯一入口；列表和响应只返回 `api_key_configured`，不返回明文密钥、前缀或后缀；配置页支持“测试连接”，调用 `/api/system/model-gateway-configs/test` 使用当前表单参数临时检测 provider `/chat/completions` 与 `/embeddings`，并可通过 `test_target=chat` 仅检测 Chat，适配 ChatGPT OAuth 类不提供 Embedding 的上游；测试不保存配置或密钥，不写入 `model_gateway_logs`，响应仅包含脱敏状态、模型、延迟、embedding 维度、跳过状态和错误码。active/default 且已配置密钥的 OpenAI-compatible 配置会在非 code_review 任务启动时调用 provider `/chat/completions`；知识索引先构建文本 chunk，只有补建向量索引和存在可读向量 chunk 的查询排序会调用 provider `/embeddings`，未配置结构化默认模型网关时可使用 `MODEL_GATEWAY_BASE_URL` 与 `MODEL_GATEWAY_API_KEY` 指向的环境模型网关；调用日志只保存脱敏元数据。缺少可用模型网关、配置缺失密钥或 provider 调用失败时，非 code_review 任务进入 `failed` 并返回 `MODEL_GATEWAY_CONFIG_INVALID` 或 `MODEL_GATEWAY_FAILED`。code_review 任务必须通过可插拔 `code_review_executor` 边界生成报告，默认 `CODE_REVIEW_EXECUTOR_TYPE=claude_code_skill`、`CODE_REVIEW_EXECUTOR_NAME=code-review`，由 `CODE_REVIEW_EXECUTOR_COMMAND` 指定外部命令适配器，输入 JSON 走 stdin，输出 JSON 走 stdout；测试或兼容环境可显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 复用模型网关适配器；默认外部命令为空且存在 active/default 或环境模型网关时，启动会自动通过 `model_gateway` 适配器生成报告，prompt 携带 MR/PR 快照、技术方案、需求和产品上下文，并将常见 Review 输出字段规范化为 AI Brain 报告 schema。执行器调用成功写入 `code_review.executor_called`，执行器配置、调用、解析或结构化校验失败进入 `failed`，返回 `CODE_REVIEW_EXECUTOR_FAILED` 并写入 `code_review.executor_failed` 审计事件。任务启动不会静默生成本地输出。

任务中心已通过真实接口支持启动产品详细设计、确认 Review、基于已确认产品详细设计创建技术方案任务、基于已确认技术方案创建 `development_planning`、`automated_testing` 和 `release_readiness` 任务，基于已确认发布评估创建 `post_release_analysis` 任务，并对已完成技术方案导出 Markdown。需求创建允许 `version_id` 为空，审批后进入 `approved` 需求池；排入 `planning` 或 `active` 迭代版本后进入 `planned`，才能生成产品详细设计任务。AI 任务启动会通过真实 LangGraph `StateGraph` 运行当前 MVP 路径 `retrieve_context -> generate_task_output -> interrupt_for_human_review`，Graph Run 响应和结构表会保留 `runtime=langgraph`、`node_path` 以及 checkpoint `graph_runtime` 元数据。`automated_testing` 输出经人工确认后，可将 `bug_suggestions` 写入 `bugs`，来源为 `ai_auto_test`；`post_release_analysis` 输出经人工确认后，可将 `bug_suggestions` 写入 `bugs`，来源为 `ai_post_release`，两者均关联产品、版本、需求和 AI 任务。GitLab 每日代码指标可通过 `/api/devops/gitlab/daily-code-metrics` 登记和筛选真实产品仓库维度指标，Jenkins 发布记录可通过 `/api/devops/jenkins/releases` 登记和筛选真实产品版本维度发布记录，线上运行日志指标可通过 `/api/ops/online-log-metrics` 登记和筛选真实产品/模块/环境/时间窗口聚合指标；采集运行记录和待归属数据队列 API 保留为历史兼容能力，当前前端不再提供入口；用户反馈可通过 `/api/insights/user-feedback` 登记、筛选和更新状态，用户使用指标可通过 `/api/insights/usage-metrics` 登记和筛选真实聚合指标；写操作均记录审计。审计与运行页面从真实 `/api/audit/events` 加载列表，要求 `audit.read`，行操作提供事件详情和基于审计主体优先的生命周期链路追踪；审计列表在 repository 可用时优先读取 SQL/repository，actor、event_type、ai_task、subject 和时间范围过滤在查询层执行。生命周期上下文已支持从 `bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback` 和 `iteration_plan_suggestion` 起点回溯同产品/版本/模块任务链路，并对未关闭严重 Bug、GitLab 风险、Jenkins 失败、线上高错误率、负面反馈和低置信度迭代建议返回来源明确的风险信号。首页 IT 团队看板已聚合真实产品、需求、AI 任务、待确认 Review、知识文档、知识沉淀、审计、Bug、GitLab 指标、Jenkins 发布、线上日志、用户使用、用户反馈和迭代规划摘要；传入 `product_id` 时，所有可归属主体必须按产品归属过滤，不展示其他产品的数据；传入 `time_range` 时，运营类指标按可解析的日期或时间窗口过滤；看板属于汇总型视图，允许基于 PostgreSQL source rows 由 Python 做跨主体聚合和展示计算。PostgreSQL 运行时看板响应带短 TTL 缓存元数据 `metadata.dashboard_cache`，默认 TTL 由 `DASHBOARD_CACHE_TTL_SECONDS` 控制，`refresh=true` 可强制绕过缓存并重建快照；接口耗时超过 `DASHBOARD_SLOW_THRESHOLD_MS` 时记录 `slow_dashboard_query` 日志。看板下钻到 Bug、研发运营、用户洞察和审计页面时保留产品和时间范围上下文。Docker 本地栈默认以 `PERSISTENCE_MODE=postgres` 运行，登录账号读取 PostgreSQL `users` 表，具备 `system.users.manage` 的用户可通过系统管理下的用户管理维护用户，并通过角色管理查看固定角色定义；`PERSISTENCE_MODE` 未设置时默认 `postgres`，非测试环境显式配置 `memory` 会启动失败；测试环境可继续用 MemoryStore helper 运行纯业务/接口单测。当前生产数据访问仍处于 DB-first 迁移期，`/health` 返回 `data_access_mode=db_first_migration`；PostgreSQL 启动使用轻量 `PostgresRuntimeStore` repository 容器，不再通过 `PersistentMemoryStore.from_repository(...)` 启动恢复业务集合；生产读路径不再通过 repository read snapshot 反灌 `PersistentMemoryStore`，缺少已声明的 repository/source rows 能力时只能使用测试 helper 或显式迁移后的查询路径；业务大脑列表和详情已在 PostgreSQL 运行时读取 `brain_apps` repository payload。产品配置写接口已在 handler 返回前把产品、版本、模块、Git 资源、相关系统和对应审计事件写入 repository，不依赖请求结束 `PersistentMemoryStore.persist()`；产品配置核心 GET 接口已在 repository 可用时优先读取 SQL/repository，包括产品列表/详情、指定产品的版本、模块、Git 资源和关联系统，并通过运行态 store 过期测试验证不依赖进程内集合；需求创建、修改、审批、驳回、关闭和删除也已在 handler 返回前写入需求记录及审计事件；从需求生成产品详细设计 AI 任务和后续任务创建已在同一 repository 事务中写入需求 `task_ids`/状态、AI task 和 `ai_task.created` 审计事件；需求列表、需求详情、AI 任务详情、Graph Run 列表、待确认 Review、Review 详情、模拟回写结果、Code Review 报告和 Markdown 导出在 PostgreSQL 运行时会优先读取 task workflow repository source rows；任务启动成功路径已写入 AI task、模型调用日志、Human Review、Graph Run、Checkpoint 和启动审计事件；任务启动失败路径已写入 failed task、可选模型失败日志、`ai_task.retry_started` 和失败审计事件；Review approve/edit-approve/reject/request-more-info 主路径已写入完成态或中断态 task/review/graph/checkpoint、需求状态、知识沉淀候选、可选 Bug/Code Review 报告和审计事件；cancel/submit-more-info 已写入 AI task、待确认 Review、Graph Run/Checkpoint 和审计事件；Mock Writeback 生成接口已在 handler 返回前写入 `mock_issues` 与 `mock_issue.written` 审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 task workflow source rows 恢复已完成任务和已有幂等回写结果；知识文档创建/更新/索引重试/删除、知识 chunk 重建、知识沉淀采纳/拒绝和对应审计事件已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 knowledge source rows 恢复产品、知识文档、chunk、沉淀和模型网关上下文，同步索引期间可选模型日志；AI 助手聊天成功路径已在 handler 返回前写入会话、用户消息、助手消息、模型日志和审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 assistant source rows 恢复当前用户会话、消息、产品任务摘要和模型网关上下文；模型调用失败路径写入失败模型日志和审计事件；GitHub PR 列表、GitLab MR / GitHub PR 预览审计以及快照成功、复用和失败审计已在 handler 返回前写入 repository，Code Review 报告生成/确认已随任务启动和 Review 决策事务写入；Bug 创建、修改和删除已在 handler 返回前写入 `bugs` 与对应审计事件，删除前会清空指向被删 Bug 的重复归并引用；采集运行创建/更新、待归属队列创建/处理、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标创建已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品、仓库、版本、模块、采集运行和待归属当前记录；用户使用指标创建、用户反馈创建/处理、迭代建议生成和迭代建议决策已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 insight source rows 校验产品、版本、模块、反馈、Bug 和迭代建议当前记录；用户使用指标、用户反馈和迭代建议列表已在 repository 可用时优先读取 SQL/repository，产品、模块、功能、用户群体、时间范围、状态、创建人和规划周期等过滤在查询层执行；迭代建议转需求时会在同一 repository 调用内写入新需求、建议、决策和完整审计事件；模型网关配置创建、修改、删除和连接测试审计已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 model gateway source rows 恢复当前配置和调用日志上下文；生命周期上下文查询生成的 edges/risks 和首页看板生成的 dashboard snapshot 已在 handler 返回前写入 repository，且这两个读接口在 PostgreSQL 运行时会读取 repository source rows；生命周期上下文 source rows 使用专用 `LifecycleContextReadModel` 承载，不再实例化 `MemoryStore` 作为聚合中间层；请求结束全局 `persist()` 已从 API middleware 移除，任何 API 请求都不再通过请求结束同步进程内 store；`app_state_snapshots` 仅作为历史迁移表保留，不再作为生产恢复源或写入目标；管理主列表必须优先在 SQL/repository/read model 层完成分页、排序和筛选，汇总型视图可基于 PostgreSQL source rows 聚合但不得作为写入事实源。外部 DevOps 自动采集器和用户行为自动采集器尚未接入；线上日志可手工登记或导入真实聚合指标，无记录时返回真实空集合，不提供占位状态或伪造统计数据；迭代规划建议已支持基于真实反馈与 Bug 证据的生成、确认和可选转需求。日志监控页面当前只展示和登记 GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标。

当前补充实现：`POST /api/planning/iteration-suggestions` 已基于库内真实 `user_feedback` 与 `bugs` 证据生成迭代建议；无证据时返回真实空集合，不生成占位建议。`POST /api/planning/iteration-suggestions/{suggestion_id}/decide` 支持产品负责人、研发负责人或管理员确认采纳、修改后采纳或驳回；只有 `accepted` / `edited_accepted` 且 `convert_to_requirement=true` 时才创建真实 `requirements` 记录。建议与确认分别写入 `iteration_plan_suggestions` 和 `iteration_plan_decisions`，并记录 `iteration_suggestion.generated` / `iteration_suggestion.decided` 审计事件。

DB-first 迁移补充：`app_state_snapshots` 仅作为历史迁移表保留，当前 PostgreSQL 运行时启动恢复只读取结构表，不再从 app_state JSONB 快照恢复业务集合；手动 `PersistentMemoryStore.persist()` 也不再写入 app_state JSONB 快照。

需求列表 DB-first 补充：`GET /api/requirements` 属于管理主列表，必须先校验 `requirement.read`，并按当前用户产品 scope 收口；PostgreSQL 运行时必须通过需求台账 SQL read model 完成产品 scope、`priority/product/product_id/source/status/title/version/version_id` 筛选、`created_at/id/priority/product_code/product_name/source/status/title/updated_at/version_code/version_name` 排序和 `page/page_size` 分页；不得为列表页先加载 task workflow source rows 再由接口层本地过滤或切片。需求详情、需求全链路、任务运行态、Review、回写和导出仍可读取 task workflow source rows 聚合上下文。

Bug 列表 DB-first 补充：`GET /api/bugs` 属于管理主列表，必须先校验 `bug.read`，并按当前用户产品 scope 收口；PostgreSQL 运行时必须通过 Bug SQL read model 完成产品 scope、`module/product_id/severity/source/status/title/version/version_id` 筛选、`assignee/created_at/id/module_code/severity/source/status/title/updated_at/version_code/version_name` 排序和 `page/page_size` 分页；不得为列表页先加载全部 Bug 记录再由接口层本地过滤、排序或切片。

产品和迭代版本列表 DB-first 补充：`GET /api/products` 属于管理主列表，PostgreSQL 运行时必须通过产品 SQL read model 完成 `active_only/code/name/owner_team/status` 筛选、当前版本与模块数投影、列表排序和 `page/page_size` 分页；`GET /api/product-versions` 必须通过迭代版本 SQL read model 完成 `active_only/code/name/product/product_id/status` 筛选、所属产品投影、列表排序和分页。产品详情、产品上下文下拉和单产品版本/模块/Git 资源配置接口仍可使用对应轻量 repository 查询。

用户使用指标当前支持通过 `POST /api/insights/usage-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/insights/usage-metrics` 按产品、模块、功能、用户群体和时间范围筛选；记录写入 `user_usage_metrics`，并记录 `usage_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

GitLab 每日代码指标当前支持通过 `POST /api/devops/gitlab/daily-code-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/devops/gitlab/daily-code-metrics` 按产品、仓库和日期筛选；记录写入 `gitlab_daily_code_metrics`，并记录 `gitlab_daily_code_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

Jenkins 发布记录当前支持通过 `POST /api/devops/jenkins/releases` 手工登记或导入真实发布记录，通过 `GET /api/devops/jenkins/releases` 按产品、版本、状态和环境筛选；记录写入 `jenkins_release_records`，并记录 `jenkins_release.created` 审计事件。无记录时返回真实空集合，不生成兜底数据。

线上运行日志指标当前支持通过 `POST /api/ops/online-log-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/ops/online-log-metrics` 按产品、模块、环境和时间窗口筛选；记录写入 `online_log_metrics`，并记录 `online_log_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

生命周期视图和首页 IT 团队看板的 AI 任务、待确认 Review、知识沉淀和风险信号聚合必须先按任务类型读权限过滤，不能通过聚合接口绕过任务详情权限。

`/api/lifecycle/context` 当前支持的真实起点主体包括 `product`、`requirement`、`ai_task`、`human_review`、`code_review_report`、`gitlab_mr_snapshot`、`mock_issue`、`knowledge_deposit`、`audit_event`、`bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback` 和 `iteration_plan_suggestion`。审计列表发起链路追踪时，后端必须先把审计主体解析到对应需求、AI 任务或可归属证据链路；不支持的 `subject_type` 返回 `VALIDATION_ERROR`，不得退化为全量任务或伪造关系。

## 认证方式

- 方式: 本地账号登录 + Bearer Token。
- Header: `Authorization: Bearer <token>`。
- 除 `/health`、`/api/auth/login`、`/api/auth/providers`、`/api/auth/dingtalk/start`、`/api/auth/dingtalk/callback` 和 `/api/auth/dingtalk/exchange-ticket` 外，所有 `/api/*` 接口都需要 Bearer Token；`exchange-ticket` 使用服务端生成的一次性登录 ticket 换取 AI Brain Bearer Token。

### 钉钉登录 P0

钉钉登录集成详见 [钉钉登录集成设计](../dingtalk-login-integration-design.md)。当前 P0 已实现登录 provider 查询、钉钉 OAuth start/callback、一次性 ticket 换取 AI Brain Token、用户自助绑定/解绑和 `user_external_identities` 外部身份绑定表。登录页通过 `GET /api/auth/providers` 判断是否展示“钉钉登录”按钮；钉钉 OAuth 回调只用于确认外部身份，登录成功后仍由 AI Brain 后端签发自有 Bearer Token。钉钉 `accessToken/refreshToken`、应用密钥、MCP URL Key 和其它外部凭据不得作为 AI Brain API Bearer Token，也不得返回前端、写入审计 payload 或进入模型上下文。

钉钉登录身份与 AI Brain 用户通过 `user_external_identities` 绑定，业务权限继续以 `users.id`、RBAC 权限点和数据范围为准。未绑定到系统用户的钉钉身份不得获得默认业务权限；若启用 `DINGTALK_AUTO_PROVISION`，默认角色为 `DINGTALK_AUTO_PROVISION_ROLE`，推荐保持 `viewer`，也可通过 `DINGTALK_PENDING_APPROVAL` 创建待审批账号。

### 获取 Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"<redacted>"}'
```

## 公共约定

### 成功响应

大多数 JSON API 返回 envelope：

```json
{
  "data": {},
  "trace_id": "trace_001"
}
```

例外：

- `GET /health` 直接返回健康状态 JSON，并在响应体中包含 `trace_id`；它不使用 `{data, trace_id}` envelope。
- `GET /api/export/tasks/{task_id}/markdown` 返回 `text/markdown` 纯文本，并通过响应 Header 或日志关联 `trace_id`。

### 错误响应

业务错误返回 FastAPI `detail`，并在响应体中保留 `trace_id` 便于排查：

```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "message": "需求必须选择有效产品；生成 AI 任务前必须排入有效迭代版本",
    "trace_id": "trace_001"
  }
}
```

未改造完成的框架级异常也必须在响应 Header 或日志中关联同一 `trace_id`。

### 分页参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| page | int | 1 | 页码。当前主要用于任务列表。 |
| page_size | int | 10 | 每页数量，最大 100。 |

### 角色要求

| 能力 | 最低角色 |
|------|----------|
| 查询健康检查 | 无需登录 |
| 登录 | 无需登录 |
| 读取业务/任务/知识/产品配置 | viewer |
| 创建需求、补充信息、取消自己创建或参与的任务 | product_owner 或 rd_owner；creator policy 由实现按产品归属和参与关系收敛 |
| 审批需求、确认产品详细设计、采纳迭代规划建议 | product_owner |
| 创建和启动 AI 任务、确认技术方案 | rd_owner |
| 创建 GitLab MR / GitHub PR 预览和 diff 快照、创建 code_review 任务、确认 Review 报告 | reviewer 或 rd_owner |
| 审核知识沉淀 | knowledge_owner 或 rd_owner |
| 登记、分派、验证或关闭 Bug | 当前实现为 product_owner、rd_owner 或 admin；RBAC 目标态由 tester/test_owner 按产品、版本或模块范围承接 |
| 维护产品、相关系统、模型网关配置、用户账号 | admin |

MVP 系统角色以 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 为主；当前实现中 Bug 登记和状态更新先复用 `product_owner`、`rd_owner`、`admin`。RBAC 目标态会新增 `developer`、`test_owner`、`tester`、`release_owner` 等研发交付扩展预置角色，其中测试人员负责授权范围内的人工测试 Bug 登记和修复验证，测试负责人负责自动化测试确认和质量门禁。接口鉴权还需要结合产品归属、任务参与关系和主体权限。

| 角色 code | 中文名称 | 主要职责 | 数据范围 | 决策范围 |
|-----------|----------|----------|----------|----------|
| `admin` | 系统管理员 | 用户、角色、模型网关、审计与系统级配置管理 | 全平台系统配置、审计事件和授权业务数据 | 账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍 |
| `product_owner` | 产品负责人 | 产品配置、版本模块、需求审批、任务生成、产品侧交付闭环和 Bug 管理 | 所负责产品、版本和模块下的需求、AI 任务、Bug、知识引用和看板摘要 | 需求审批、产品详细设计确认、迭代规划采纳和产品侧优先级决策 |
| `rd_owner` | 研发负责人 | 研发任务启动、技术方案确认、Code Review 任务创建、Bug 处理和研发知识沉淀 | 授权产品下的 AI 任务、技术方案、GitLab/GitHub 只读快照、Bug 和研发知识 | 技术方案确认、研发任务推进、Bug 处理和研发知识沉淀决策 |
| `reviewer` | 评审负责人 | 高影响 AI 输出、需求分析、设计方案和 GitLab MR / GitHub PR Code Review 的人工确认 | 分配给评审人的 AI 任务、Review 检查点、MR/PR 只读快照和评审报告 | 对高影响 AI 输出执行批准、修改后批准、拒绝或要求补充信息 |
| `knowledge_owner` | 知识负责人 | 知识文档导入、权限角色维护、知识检索治理和知识沉淀审核 | 知识文档、chunk、检索结果、权限角色和知识沉淀候选 | 知识导入、权限配置、索引治理和沉淀候选审核 |
| `viewer` | 查看者 | 查看有权限访问的工作台数据、任务结果、知识和看板摘要 | 授权范围内的列表、详情、任务结果、知识检索结果和看板摘要 | 无写入或审批决策权限 |

### 主体级 API 约定

产品、需求、AI 任务、Bug、知识中心、研发运营指标/看板和用户洞察（含迭代规划建议）是独立业务主体或独立运营视图。API 设计应遵循以下约定：

- 产品接口维护长期主数据，仅 `planning` 和 `active` 版本可用于新需求排期；`testing`、`released` 和 `archived` 不得用于新需求或新开发任务。
- 需求接口维护业务事实和审批状态，生成任务时必须把需求快照写入任务输入。
- AI 任务接口维护任务类型、执行状态、人工确认、回写、导出和运行结果，不承担产品主数据维护。
- GitLab MR / GitHub PR 代码 Review 接口只读取授权变更元信息和 diff 快照，生成 AI Brain 内部 Review 报告，不提供远端评论、审批、request changes、合并或分支变更回写能力。
- 知识接口支持独立导入、索引状态查询、权限过滤检索、索引失败重试和沉淀审核。
- Bug 接口支持 AI 自动测试和人工测试两类来源的登记、分派、修复、验证、关闭和重复归并。
- DevOps/运营接口按产品归属暴露 GitLab 每日代码质量、Jenkins 发布、线上运行日志、用户使用、用户反馈、迭代规划建议和首页 IT 团队看板指标；首页看板中的任务、待确认 Review 和知识沉淀聚合必须先按任务读权限过滤。
- 全流程感知接口按产品、版本、模块、需求、AI 任务或任一主体查询上下文关系、上下游影响和风险信号；返回下游任务、Review、报告、沉淀和风险信号前必须先按任务读权限过滤。
- 审计接口支持按 `ai_task_id`、`subject_type`、`subject_id`、`event_type`、`actor_id` 和创建时间范围过滤。
- 迭代规划建议接口只生成建议和采纳记录，不能绕过产品负责人确认自动创建正式需求或调整迭代排期。

---

## 基础接口详情

### 管理主列表响应元数据

产品、迭代版本、需求、AI 任务、Bug、研发运营统一列表和用户洞察统一列表等管理主列表在分页响应中返回 `query` 与 `performance` 元数据：

```json
{
  "data": {
    "items": [],
    "page": 1,
    "page_size": 10,
    "total": 0,
    "query": {
      "filters": {
        "status": "testing"
      },
      "name": "requirements",
      "page": 1,
      "page_size": 10,
      "sort_by": "created_at",
      "sort_order": "desc"
    },
    "performance": {
      "duration_ms": 12,
      "p95_target_ms": 300,
      "result_count": 0,
      "slow": false,
      "slow_threshold_ms": 300,
      "total": 0
    }
  },
  "trace_id": "trace_xxx"
}
```

`query.name` 标识列表接口归属，`query.filters` 只回显实际生效的非空筛选条件；`performance.duration_ms` 记录本次接口处理耗时，`result_count` 记录当前页返回条数，`total` 记录筛选后的总数。`performance.p95_target_ms` 是列表级 P95 目标，当前核心目标为 `requirements/ai_tasks/bugs=300ms`、`user_insights=400ms`、`devops_operational_metrics=500ms`；默认 `slow_threshold_ms` 使用该目标值。接口耗时超过 `slow_threshold_ms` 时后端记录 `slow_list_query` 日志并包含 `p95_target_ms`，页面性能排查应优先结合 `trace_id`、`query`、`performance`、`slow_list_query` 和数据库慢查询日志定位。

### 健康检查

```http
GET /health
```

响应：

```json
{
  "status": "ok",
  "postgres": "ok",
  "redis": "ok",
  "model_gateway": "not_configured",
  "long_memory": "not_configured",
  "trace_id": "trace_health_001"
}
```

`status` 在 PostgreSQL 或 Redis 异常时为 `degraded`。`model_gateway` 优先根据持久化 active/default 模型网关配置判断，配置缺失时回退到 `MODEL_GATEWAY_BASE_URL` / `MODEL_GATEWAY_API_KEY` 环境变量。

字段枚举：

| 字段 | 当前取值 |
|------|----------|
| status | `ok` 或 `degraded` |
| postgres | `ok` 或 `error` |
| redis | `ok` 或 `error` |
| model_gateway | `configured` 或 `not_configured` |
| long_memory | `configured` 或 `not_configured` |

### 长期记忆状态

```http
GET /api/long-memory/status
```

响应：

```json
{
  "data": {
    "api_key_configured": false,
    "base_url_configured": false,
    "capabilities": [],
    "connector": "gbrain",
    "fallback_retriever": "postgres_pgvector",
    "status": "not_configured"
  },
  "trace_id": "trace_long_memory_001"
}
```

配置 `GBRAIN_BASE_URL` 和 `GBRAIN_API_KEY` 后，`status` 返回 `configured`，`capabilities` 返回 `hybrid_retrieval`、`answer_synthesis`、`knowledge_graph`；响应不得返回 GBrain URL、API Key 或密钥片段。

### 登录

```http
POST /api/auth/login
```

当前 MVP 内置种子账号仅用于 `APP_ENV=local|test|development` 的本地验证；非本地环境默认拒绝种子账号登录，除非显式设置受控的 `ALLOW_SEEDED_USERS=true`。

请求体：

```json
{
  "username": "admin@example.com",
  "password": "<redacted>"
}
```

响应：

```json
{
  "data": {
    "access_token": "<redacted>",
    "token_type": "bearer",
    "expires_in": 28800,
    "user": {
      "id": "user_admin",
      "username": "admin@example.com",
      "display_name": "AI Brain Admin",
      "roles": ["admin"]
    }
  },
  "trace_id": "trace_001"
}
```

### 认证提供方

```http
GET /api/auth/providers
```

返回当前登录页可展示的认证方式。该接口无需登录，响应不得包含任何密钥、corp 白名单明文或内部策略细节。

响应示例：

```json
{
  "data": {
    "local": {
      "enabled": true,
      "display_name": "账号密码登录",
      "start_url": "/api/auth/login"
    },
    "dingtalk": {
      "enabled": true,
      "configured": true,
      "display_name": "钉钉登录",
      "bind_start_url": "/api/auth/dingtalk/bind/start",
      "start_url": "/api/auth/dingtalk/start"
    }
  },
  "trace_id": "trace_auth_provider_001"
}
```

### 钉钉登录

```http
GET /api/auth/dingtalk/start?redirect=/welcome
GET /api/auth/dingtalk/callback?code=<auth_code>&state=<state>
POST /api/auth/dingtalk/exchange-ticket
```

`start` 负责校验站内 `redirect`、生成一次性 OAuth `state` 并跳转钉钉授权页。未完整配置时返回 `503 DINGTALK_LOGIN_NOT_CONFIGURED`。`callback` 负责校验 `state`、使用钉钉授权码换取用户身份、校验企业白名单、查找或创建 AI Brain 用户绑定，并生成一次性 `login_ticket` 后 302 回前端 `/login/dingtalk/callback`。`exchange-ticket` 使用该 ticket 换取 AI Brain Bearer Token，响应结构与本地登录一致。

当前实现 `state` 10 分钟有效，`login_ticket` 5 分钟有效，均只能使用一次。callback 不得把 AI Brain JWT、钉钉 access token 或 refresh token 放入 URL query。

`exchange-ticket` 请求：

```json
{
  "ticket": "<one_time_ticket>"
}
```

成功响应与 `POST /api/auth/login` 保持一致。主要错误码包括 `DINGTALK_LOGIN_NOT_CONFIGURED`、`DINGTALK_STATE_INVALID`、`DINGTALK_AUTH_DENIED`、`DINGTALK_CODE_MISSING`、`DINGTALK_UPSTREAM_ERROR`、`DINGTALK_PROFILE_INCOMPLETE`、`DINGTALK_CORP_NOT_ALLOWED`、`DINGTALK_ACCOUNT_NOT_BOUND`、`DINGTALK_ACCOUNT_PENDING_APPROVAL`、`DINGTALK_ACCOUNT_INACTIVE`、`EXTERNAL_IDENTITY_CONFLICT` 和 `DINGTALK_TICKET_INVALID`。OAuth callback 的失败会通过前端回调页 query 参数展示，`exchange-ticket` 失败返回 JSON API 错误。

### 钉钉账号绑定

```http
POST /api/auth/dingtalk/bind/start
GET /api/auth/dingtalk/bind/callback?code=<auth_code>&state=<state>
POST /api/auth/dingtalk/unbind
```

自助绑定要求当前用户已登录。绑定成功只写入或更新外部身份绑定，不改变用户角色、权限和数据范围。若该钉钉身份已经绑定其它 AI Brain 用户，返回 `409 EXTERNAL_IDENTITY_CONFLICT`。解绑只停用或删除外部身份绑定，不删除 `users` 账号和历史审计 actor。

### 角色目录

```http
GET /api/auth/roles
```

该接口返回当前 MVP 可分配的系统角色目录，供用户管理页面、知识权限选择、权限说明和外部集成统一引用。`POST /api/users`、`PATCH /api/users/{user_id}` 和知识 `permission_roles` 字段只能使用该目录中的 `code`。

v1.2 目标态按 [RBAC 重设计](../rbac-redesign.md) 演进：`GET /api/auth/roles` 作为 active/assignable 角色目录兼容接口保留；角色治理、权限点目录、角色权限矩阵、角色菜单授权、角色数据范围和用户授权管理迁移到 `/api/system/roles`、`/api/system/permissions`、`/api/system/menus`、`/api/users/{user_id}/roles`、`/api/users/{user_id}/permissions` 与 `/api/users/{user_id}/scopes`。组织/部门通过 `/api/system/departments` 管理，外部身份通过 `/api/system/external-identities` 绑定到系统 `users.id`，产品成员通过 `/api/products/{product_id}/members` 在产品管理页维护，知识空间通过 `/api/knowledge/spaces` 管理并作为知识检索权限边界。`/api/auth/me` 目标态返回 `menu_tree` 和 `route_permissions`，前端左侧菜单按 `menu_tree` 渲染。业务接口后续应校验权限点和数据范围，不再直接依赖角色 code，也不能把菜单隐藏作为安全边界；未绑定系统用户 ID 的 SSO 身份不得获得默认角色、部门或范围。目标角色目录除 MVP 六个兼容角色外，还应提供 `developer`、`test_owner`、`tester`、`release_owner` 等研发交付扩展预置角色模板。
