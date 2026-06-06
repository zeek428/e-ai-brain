# 企业 AI 大脑平台测试用例

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.346 |
| 适用系统版本 | ≥ v1.0.0 |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.1.346 | 2026-06-07 | 后端持久化测试拆分继续推进：将 Bug 结构化持久化、Bug API DB-first 写入和 stale runtime 列表读取回归迁移到独立 test_bug_persistence.py | Codex |
| v1.1.345 | 2026-06-06 | 后端持久化测试拆分继续推进：将 Mock Issue 写回结构化持久化、恢复计数器和陈旧任务引用清理回归迁移到独立 test_mock_writeback_persistence.py | Codex |
| v1.1.344 | 2026-06-06 | 后端持久化测试拆分继续推进：将 GitLab/GitHub Review 快照与代码评审报告结构化持久化、恢复计数器和陈旧引用清理回归迁移到独立 test_git_review_artifacts_persistence.py | Codex |
| v1.1.343 | 2026-06-06 | 后端持久化测试拆分继续推进：将模型网关配置/日志结构化持久化、恢复计数器和配置 API 写入回归迁移到独立 test_model_gateway_persistence.py | Codex |
| v1.1.342 | 2026-06-06 | 后端持久化测试拆分继续推进：将用户仓储登录和用户管理 API 回归迁移到独立 test_user_repository_auth.py | Codex |
| v1.1.341 | 2026-06-06 | 后端持久化测试拆分继续推进：将迭代建议和迭代决策的结构化持久化用例迁移到独立 test_iteration_planning_persistence.py | Codex |
| v1.1.340 | 2026-06-06 | 后端持久化测试拆分继续推进：将用户反馈和用户使用指标的结构化持久化用例迁移到独立 test_user_insights_persistence.py | Codex |
| v1.1.339 | 2026-06-06 | 后端持久化测试拆分继续推进：将 GitLab 日指标、Jenkins 发布记录、线上日志指标和采集运行的结构化持久化用例迁移到独立 test_devops_metrics_persistence.py | Codex |
| v1.1.338 | 2026-06-06 | 后端持久化测试拆分继续推进：将待归属数据 pending attribution 的结构化持久化和陈旧上下文清理用例迁移到独立 test_pending_attribution_persistence.py | Codex |
| v1.1.337 | 2026-06-06 | 前端页面测试拆分继续推进：将需求管理批量排期/生成任务/全链路弹窗回归迁移到独立 RequirementsPage.test.tsx，将迭代版本归集需求/版本需求查看/状态推进影响预览迁移到独立 IterationVersionsPage.test.tsx | Codex |
| v1.1.336 | 2026-06-06 | 前端页面测试拆分继续推进：将任务中心列表、筛选、批量重试/取消、Review 决策、任务操作弹窗、Mock Issue 写回和补充信息回归迁移到独立 TaskCenterPage.test.tsx | Codex |
| v1.1.335 | 2026-06-06 | 前端页面测试拆分继续推进：将产品配置页筛选、错误态、版本/模块/Git 资源/相关系统维护和 GitHub provider 编辑保存回归迁移到独立 ProductsPage.test.tsx | Codex |
| v1.1.334 | 2026-06-06 | 前端测试拆分继续推进：将 Umi 路由注册、登录、鉴权初始化、auth state 事件、过期 token 清理和登出跳转回归迁移到独立 AuthFlow.test.tsx | Codex |
| v1.1.333 | 2026-06-06 | 前端测试拆分继续推进：将管理 CRUD、任务创建、GitLab MR 预览/快照、Code Review 报告和批量排期 service 契约迁移到独立 ManagementCrudServices.test.ts | Codex |
| v1.1.332 | 2026-06-06 | 前端测试拆分继续推进：将 MVP-C mock issue 写回、知识沉淀列表/审批/驳回和知识检索 service 契约迁移到独立 KnowledgeWritebackServices.test.ts | Codex |
| v1.1.331 | 2026-06-06 | 前端测试拆分继续推进：将 Review 补充信息、编辑确认、驳回和任务补充信息提交 service 契约迁移到独立 ReviewServices.test.ts | Codex |
| v1.1.330 | 2026-06-06 | 前端测试拆分继续推进：将模型网关配置 CRUD、Chat-only 连接测试和密钥脱敏 service 契约迁移到独立 ModelGatewayServices.test.ts | Codex |
| v1.1.329 | 2026-06-06 | 前端测试拆分继续推进：将团队看板 product/time-range 查询、active 产品筛选和 GitHub PR preview/snapshot service 契约迁移到独立 DashboardServices.test.ts 与 GitReviewServices.test.ts | Codex |
| v1.1.328 | 2026-06-06 | 前端测试拆分继续推进：将产品版本/模块/Git 仓库/相关系统 service 契约与 Git 凭据脱敏回归迁移到独立 ProductServices.test.ts | Codex |
| v1.1.327 | 2026-06-06 | 前端页面测试拆分继续推进：将模型网关配置新增/编辑、仅 Chat 测试、密钥不回显和编辑不覆盖密钥页面回归迁移到独立 ModelGatewayPage.test.tsx | Codex |
| v1.1.326 | 2026-06-06 | 前端页面测试拆分继续推进：将知识中心沉淀审核、权限检索来源展示和索引失败重试页面回归迁移到独立 KnowledgePage.test.tsx | Codex |
| v1.1.325 | 2026-06-06 | 前端页面测试拆分继续推进：将需求全链路独立详情页直达路由、返回入口、版本内对比和共享展示组件回归迁移到独立 RequirementFullChainPage.test.tsx | Codex |
| v1.1.324 | 2026-06-06 | 后端测试拆分继续推进：将 AI 助手会话/消息结构化持久化与恢复计数器用例迁移到独立 test_assistant_chat_persistence.py | Codex |
| v1.1.323 | 2026-06-06 | 前端页面测试拆分继续推进：将 AI 助手页面、引用链接、用户级会话历史和助手 service 映射用例迁移到独立 AssistantPage.test.tsx | Codex |
| v1.1.322 | 2026-06-06 | 前端页面测试拆分继续推进：将任务中心 Code Review 报告全链路跳转用例迁移到独立 TaskCenterPage.test.tsx，保留 App.test.tsx 作为少量端到端工作台 smoke | Codex |
| v1.1.321 | 2026-06-06 | 补充 Code Review 报告到需求全链路闭环验收：任务中心报告弹窗展示“查看需求全链路”入口，并验证跳转到对应需求 full-chain 详情页 | Codex |
| v1.1.320 | 2026-06-06 | 补充 GitHub PR / GitLab MR 代码 Review 闭环验收：预览返回权限诊断，快照响应返回上一快照引用、diff 对比摘要和复用标记，任务中心展示快照结果用于 PR 刷新/重试排查 | Codex |
| v1.1.319 | 2026-06-06 | PostgreSQL 旧库兼容验收补齐：PostgresSnapshotRepository 启动时执行安全 additive schema patch，补齐历史本地 volume 缺失的 requirements.assignee 字段和索引，避免需求列表与首页看板 SQL read model 在旧库上返回 500；真实页面 smoke 复验 8 个核心路由通过 | Codex |
| v1.1.318 | 2026-06-06 | 测试用例文档按业务域拆分：主 test-case.md 保留版本信息、通用规范、MVP 验收切片和业务域索引，详细用例迁移到 test-cases/core-workflow.md、requirements-and-tasks.md、devops-quality-and-insights.md 与 supporting-matrices.md，降低单文件维护成本 | Codex |
| v1.1.317 | 2026-06-06 | 模型网关 router 拆分继续收口：将模型网关配置列表的筛选、排序、分页、query/performance 观测和模型调用日志 repository-first 读取迁移到 model_gateway_listing，model_gateway router 收窄为配置测试、创建、修改、删除和响应封装编排 | Codex |
| v1.1.316 | 2026-06-06 | 相关系统 router 拆分继续收口：将相关系统列表的 repository-first 读取、产品归属筛选、active_only 过滤和本地兼容排序迁移到 related_system_listing，related_systems router 收窄为相关系统创建、修改、删除和审计保存编排 | Codex |
| v1.1.315 | 2026-06-06 | 产品 Git 仓库 router 拆分继续收口：将单产品 Git 仓库列表的 repository-first 读取、凭据脱敏投影、active_only 过滤、缺失产品校验和本地兼容排序迁移到 product_git_repository_listing，product_git_repositories router 收窄为 GitLab/GitHub 绑定校验和仓库创建、修改、删除编排 | Codex |
| v1.1.314 | 2026-06-06 | 产品模块 router 拆分继续收口：将单产品模块列表的 repository-first 读取、active_only 过滤、缺失产品校验和本地兼容排序迁移到 product_module_listing，product_modules router 收窄为模块创建、修改、删除和依赖保护编排 | Codex |
| v1.1.313 | 2026-06-06 | 产品主体 router 拆分继续收口：将产品列表 SQL read model 探测、当前版本/模块数投影、本地兼容筛选排序分页和 query/performance 观测迁移到 product_listing，products router 收窄为端点装配、产品详情和产品 CRUD 编排 | Codex |
| v1.1.312 | 2026-06-06 | 迭代版本 router 拆分继续收口：将全量迭代版本列表 SQL read model 探测、所属产品投影、本地兼容筛选排序分页和 query/performance 观测迁移到 product_version_listing，product_versions router 收窄为端点装配、单产品版本列表和版本写入/状态推进编排 | Codex |
| v1.1.311 | 2026-06-06 | Bug 管理服务拆分继续收口：将 Bug 列表 SQL read model 探测、摘要投影、本地兼容筛选排序分页和 query/performance 观测迁移到 bug_listing，bugs service 收窄为 Bug 创建、批量更新、修改、删除和审计保存编排 | Codex |
| v1.1.310 | 2026-06-06 | AI 助手聊天服务拆分继续收口：将 repository-backed request context、任务工作流 source rows 恢复、用户级会话/消息 source store 和助手聊天保存委托迁移到 assistant_request_context，assistant_chat 收窄为聊天校验、模型调用、消息写入和审计编排 | Codex |
| v1.1.309 | 2026-06-06 | 模型网关 router 拆分继续收口：将配置连接测试的目标校验、既有配置凭据复用、Chat/Embedding 测试编排和测试审计保存迁移到 model_gateway_config_tests，model_gateway router 收窄为请求模型、鉴权、运行态 store 装配和响应封装 | Codex |
| v1.1.308 | 2026-06-06 | 模型网关服务拆分继续收口：将 Chat/Embedding URL 规范化、连接测试结果构造、Embedding 响应解析和 Embedding context 构造迁移到 model_gateway_runtime，model_gateway 收窄为 OpenAI-compatible 调用、配置选择和测试编排并保留兼容导出 | Codex |
| v1.1.307 | 2026-06-06 | 知识沉淀服务拆分继续收口：将知识内容切分、chunk 构造、文本索引/向量索引状态转换和 Embedding 失败降级逻辑迁移到 knowledge_indexing，knowledge_deposits 收窄为知识文档/沉淀读写编排并保留兼容导出 | Codex |
| v1.1.306 | 2026-06-06 | Git review 服务拆分继续收口：将 GitLab base URL/凭据解析、项目 key 校验、MR 读取、changes 解析和 GitLab API 错误归一化迁移到 git_review_gitlab，git_review 保留 gitlab_request_json/urlopen/gitlab_preview 兼容 wrapper 与审计/快照编排 | Codex |
| v1.1.305 | 2026-06-06 | Git review 服务拆分继续收口：将 GitHub base URL/凭据解析、仓库路径解析、PR 列表读取、PR 预览和 GitHub API 错误归一化迁移到 git_review_github，git_review 保留兼容 wrapper 与审计/快照编排，为后续 PR 刷新、重试和权限诊断增强打基础 | Codex |
| v1.1.304 | 2026-06-06 | 需求交付服务拆分继续收口：将需求列表 SQL read model 入口、需求摘要投影、本地兼容筛选排序分页和查询性能观测响应迁移到 requirement_listing，requirements 收窄为需求写入、编辑、删除和任务生成编排，并保留兼容导出 | Codex |
| v1.1.303 | 2026-06-06 | AI 助手上下文服务拆分继续收口：将引用候选、引用类型偏好、实体跳转路由和引用归一化迁移到 assistant_references，assistant_context 收窄为系统上下文、消息构造和公开投影，并保留兼容导出 | Codex |
| v1.1.302 | 2026-06-06 | persistence_contracts.py 大文件拆分继续收口：将集合字段常量、历史 snapshot collection 清单和 ID counter 来源表迁移到 persistence_fields，persistence_contracts 收窄为 repository Protocol 契约并保留兼容导出 | Codex |
| v1.1.301 | 2026-06-06 | persistence_payloads.py 大文件拆分继续收口：将结构化恢复与保存前的上下文清理、运行态链接同步和默认字段补齐 helper 迁移到 persistence_payload_cleanup，persistence_payloads 收窄为 repository load/save 包装与兼容导出门面 | Codex |
| v1.1.300 | 2026-06-06 | persistence_payloads.py 大文件拆分继续收口：将结构化恢复时的 ID counter 同步 helper 迁移到 persistence_payload_counters，persistence_payloads 继续保留兼容导出并聚焦 repository load/save 包装与上下文清理 | Codex |
| v1.1.299 | 2026-06-06 | persistence_payloads.py 大文件拆分继续收口：将纯 payload 选择/合并 helper 迁移到 persistence_payload_selectors，将结构化 payload 是否存在的检查 helper 迁移到 persistence_payload_checks，保留 persistence_payloads 兼容导出给历史测试兼容层使用 | Codex |
| v1.1.298 | 2026-06-06 | persistence.py 大文件拆分继续收口：将 PostgreSQL snapshot repository 的领域仓储装配、callback bind 和兼容 alias 安装迁移到 persistence_repositories，PostgresSnapshotRepository 聚焦连接池、公开委托接口和连接重试 | Codex |
| v1.1.297 | 2026-06-06 | 用户洞察仓储拆分继续推进：将用户洞察统一列表 SQL CTE、筛选、排序、分页和响应投影迁移到 user_insights_lists repository，UserInsightReadRepository 进一步收窄为单表读取与写入/列表委托入口 | Codex |
| v1.1.296 | 2026-06-06 | 任务仓储拆分继续推进：将 AI 任务、Graph Run、Graph Checkpoint 和 Human Review 的基础保存与 upsert SQL 迁移到 task_writes repository，TaskReadRepository 收窄为任务读取、任务列表 read model 与跨域事务编排入口 | Codex |
| v1.1.295 | 2026-06-06 | 知识仓储拆分继续推进：将知识文档、知识分块和知识沉淀的保存、删除、引用清理、向量 literal 格式化与 upsert SQL 迁移到 knowledge_writes repository，KnowledgeReadRepository 收窄为知识读取、搜索和兼容委托入口 | Codex |
| v1.1.294 | 2026-06-06 | 用户洞察仓储拆分继续推进：将用户反馈、用户使用指标、迭代建议和迭代决策的批量保存、单记录保存、转需求事务与 upsert SQL 迁移到 user_insights_writes repository，UserInsightReadRepository 收窄为洞察读取、统一列表 read model 与兼容委托入口 | Codex |
| v1.1.293 | 2026-06-06 | 研发运营仓储拆分继续推进：将 GitLab 每日代码指标、Jenkins 发布记录和线上日志指标的批量保存、单记录保存与 upsert SQL 迁移到 devops_writes repository，DevopsReadRepository 收窄为运营指标读取、列表 read model 与兼容委托入口 | Codex |
| v1.1.292 | 2026-06-06 | 产品配置仓储拆分继续推进：将产品、迭代版本、模块、Git 仓库和相关系统的批量保存、单记录保存、删除与 upsert SQL 迁移到 product_config_writes repository，ProductConfigReadRepository 进一步收窄为读取门面与兼容委托入口 | Codex |
| v1.1.291 | 2026-06-06 | 产品配置仓储拆分继续推进：将产品和迭代版本管理列表 SQL read model 的 count/list 查询迁移到 product_config_lists repository，ProductConfigReadRepository 收窄为产品配置恢复、详情读取和写入编排 | Codex |
| v1.1.290 | 2026-06-06 | 生命周期上下文服务拆分继续推进：将 lifecycle subject 到任务集合解析、主体产品归属推导、审计/Mock Issue/知识沉淀等主体定位迁移到 lifecycle_subjects service，lifecycle_context.py 收窄为上下游关系构造和响应编排 | Codex |
| v1.1.289 | 2026-06-06 | 模型网关服务拆分继续推进：将任务消息构造、产品上下文脱敏、模型输出 JSON 解析和 Code Review 风险归一化迁移到 model_gateway_task_io service，model_gateway.py 收窄为运行时配置、OpenAI-compatible 调用、Embedding 和连接测试编排 | Codex |
| v1.1.288 | 2026-06-06 | Git review 服务拆分继续推进：将 PR/MR diff 快照上下文校验、大小限制、复用、失败审计和快照保存迁移到 git_review_snapshots service，git_review.py 收窄为 GitLab/GitHub provider 读取和接口响应编排 | Codex |
| v1.1.287 | 2026-06-06 | 生命周期上下文服务拆分继续推进：将 LifecycleContextReadModel、repository 探测、source rows 转换和生命周期 edge/risk 保存 helper 迁移到 lifecycle_source service，lifecycle_context.py 收窄为主体定位、上下游关系构造和响应编排 | Codex |
| v1.1.286 | 2026-06-06 | 模型网关服务拆分继续推进：将 repository 运行时上下文、配置 source store、配置保存 payload、公开脱敏投影、默认配置选择迁移到 model_gateway_config_context service，model_gateway.py 收窄为 Chat/Embedding 调用、连接测试和任务输出解析 | Codex |
| v1.1.285 | 2026-06-06 | AI 助手聊天服务拆分继续推进：将用户级会话列表、会话消息读取、会话归属校验和消息追加迁移到 assistant_history service，并将 AssistantServiceError 抽到 assistant_errors，assistant_chat.py 收窄为聊天编排、上下文准备、模型网关调用和审计保存 | Codex |
| v1.1.284 | 2026-06-06 | 需求交付服务拆分继续推进：将单需求审批、驳回和关闭决策迁移到 requirement_decisions service，requirements.py 收窄为需求创建/编辑/删除、任务生成、列表查询和共享持久化 helper，保持状态校验、活跃任务保护和 DB-first 审计契约不变 | Codex |
| v1.1.283 | 2026-06-06 | 知识沉淀服务拆分继续推进：将知识沉淀采纳/驳回决策迁移到 knowledge_deposit_decisions service，knowledge_deposits.py 收窄为知识文档索引、repository 上下文和共享持久化 helper，保持知识沉淀状态校验、索引、模型日志和 DB-first 审计契约不变 | Codex |
| v1.1.282 | 2026-06-06 | AI 助手聊天服务拆分继续推进：assistant_chat 复用 model_gateway_logging 的 token 估算、OpenAI usage 归一化和模型调用日志写入，消除助手本地重复日志实现，为后续助手工具化查询保持统一模型审计口径 | Codex |
| v1.1.281 | 2026-06-06 | 模型网关服务拆分继续推进：将 token 估算、OpenAI Chat/Embedding usage 归一化和模型调用日志写入迁移到 model_gateway_logging service，model_gateway.py 继续收窄为运行时配置、Chat/Embedding 调用和连接测试编排 | Codex |
| v1.1.280 | 2026-06-06 | Git review 服务拆分继续推进：将 GitLab/GitHub 变更文件摘要、diff 文件树、风险摘要、Review Checklist 和 diff payload 构造迁移到 git_review_diff service，git_review.py 收窄为 provider 读取、快照上下文校验、审计和快照编排 | Codex |
| v1.1.279 | 2026-06-06 | 生命周期上下文服务拆分继续推进：将任务范围/证据匹配/缺失上下文判断迁移到 lifecycle_evidence service，将风险信号生成、稳定记录 ID 和 lifecycle edge/risk 物化迁移到 lifecycle_risks service，lifecycle_context.py 收窄为 source store、主体定位、上下游关系和响应编排 | Codex |
| v1.1.278 | 2026-06-06 | 研发运营服务拆分继续推进：将线上日志指标列表、登记、时间窗口/指标范围校验和产品模块上下文校验迁移到独立 operational_online_logs service，operational_records.py 收窄为采集运行与共享运营 helper | Codex |
| v1.1.277 | 2026-06-06 | 研发运营服务拆分继续推进：将 Jenkins 发布记录列表、登记、时间/状态校验和产品版本上下文校验迁移到独立 operational_jenkins_releases service，operational_records.py 继续收窄为采集运行和线上日志指标 | Codex |
| v1.1.276 | 2026-06-06 | 研发运营服务拆分继续推进：将 GitLab 每日代码指标列表、登记、日期校验、数值范围校验和产品 Git 仓库上下文校验迁移到独立 operational_gitlab_metrics service，operational_records.py 继续收窄为采集运行、Jenkins 发布和线上日志指标 | Codex |
| v1.1.275 | 2026-06-06 | 用户洞察服务拆分继续推进：将用户使用指标列表、登记、时间窗口解析、数值范围校验和产品/模块上下文校验迁移到独立 user_usage_metrics service，user_insights.py 收窄为用户洞察统一列表和共享仓储 helper | Codex |
| v1.1.274 | 2026-06-06 | 用户洞察服务拆分继续推进：将迭代建议列表、生成、决策、证据收集、状态机校验和转需求逻辑迁移到独立 iteration_planning service，user_insights.py 收窄为用户洞察统一列表和使用指标 | Codex |
| v1.1.273 | 2026-06-06 | 用户洞察服务拆分继续推进：将用户反馈列表、登记、处理、枚举校验、满意度校验和产品/模块/需求上下文校验迁移到独立 user_feedback service，user_insights.py 收窄为用户洞察聚合、使用指标和迭代建议 | Codex |
| v1.1.272 | 2026-06-06 | 研发运营服务拆分继续推进：将待归属数据队列的校验、列表、创建和处理迁移到独立 operational_attribution service，operational_records.py 收窄为采集运行和 DevOps 指标记录，attribution router 契约保持不变 | Codex |
| v1.1.271 | 2026-06-06 | 需求交付服务拆分继续推进：将批量生成任务、批量分配负责人、批量排期和批量推进状态迁移到独立 requirement_batch_operations service，requirements.py 收窄为单需求写入、任务生成 helper、列表查询和共享投影 | Codex |
| v1.1.270 | 2026-06-06 | 模型网关服务拆分继续推进：将 Embedding 连接模式、维度校验、配置归一化和测试字段构建迁移到独立 model_gateway_embeddings service，model_gateway.py 保留兼容导出和 Chat/Embedding 调用行为不变 | Codex |
| v1.1.269 | 2026-06-06 | 发布验证流程继续固化：真实浏览器页面 smoke 监听网络响应，核心页面路由期间出现非 favicon 的 4xx/5xx 请求会直接判定失败，避免页面壳渲染但 API 404/500 未被发现 | Codex |
| v1.1.268 | 2026-06-06 | 管理列表查询性能观测继续补齐：产品、迭代版本、知识文档、审计事件等核心管理列表补充显式 P95 目标，并扩展测试验证真实接口响应包含 query/performance、分页参数、行数和目标耗时 | Codex |
| v1.1.267 | 2026-06-06 | 需求交付服务拆分继续推进：将需求详情和需求全链路只读投影、时间线事件、PR/MR 快照引用、代码评审/Bug/发布/知识沉淀链路摘要迁移到独立 requirement_full_chain service，requirements.py 继续收窄为需求写入、批量操作和列表查询 | Codex |
| v1.1.266 | 2026-06-06 | persistence.py 大文件拆分继续收口：将仍需测试兼容的 repository 回调入口迁移到独立 RepositoryCallbackHub，PostgresSnapshotRepository 只负责仓储装配和兼容别名挂载，保持 `_upsert_*`、`_clean_*`、`_delete_missing*` 等边界测试入口不变 | Codex |
| v1.1.265 | 2026-06-06 | 后端任务服务拆分继续推进：将 Review 通过和编辑通过决策编排迁移到独立 task_review_decisions service，tasks router 直接引用该决策边界，ai_tasks.py 收敛为兼容 re-export 薄模块，保持 Review 完成、代码评审报告确认、Bug 建议生成和 DB-first 保存契约不变 | Codex |
| v1.1.264 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务创建、技术方案后续任务校验、发布准备/上线后分析上下文注入、GitHub/GitLab 代码评审快照校验、需求任务关联和任务创建审计保存迁移到独立 task_creation service，保持任务创建和 DB-first 保存契约不变 | Codex |
| v1.1.263 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务详情投影、Graph Run 列表、待确认 Review 列表和 Review 详情读取迁移到独立 task_read_details service，保持任务详情、Review 只读查询和 pending Review SQL read model 契约不变 | Codex |
| v1.1.262 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务启动执行、模型网关失败处理、Code Review executor 调用、Human Review 创建、Graph Run 启动和任务启动保存迁移到独立 task_start_execution service，保持任务启动、失败重试、批量重试和代码评审任务契约不变 | Codex |
| v1.1.261 | 2026-06-06 | 后端任务服务拆分继续推进：将任务取消、补充信息提交、Review 驳回和要求补充信息迁移到独立 task_state_transitions service，并将任务保存/审计 helper 下沉到 task_persistence_helpers，保持任务状态流转、批量操作和 DB-first 保存契约不变 | Codex |
| v1.1.260 | 2026-06-06 | 后端任务服务拆分继续推进：将 Review 完成后的代码评审报告确认、自动化测试/上线后 Bug 建议生成、知识沉淀、需求完成态推进和 Review 决策校验迁移到独立 task_review_artifacts service，保持 Review 决策和持久化契约不变 | Codex |
| v1.1.259 | 2026-06-06 | 后端任务服务拆分继续推进：将产品/Git 上下文脱敏、任务归属校验、技术方案/发布准备前置校验和发布上下文聚合迁移到独立 task_contexts service，保持任务创建和上下文快照契约不变 | Codex |
| v1.1.258 | 2026-06-06 | 后端任务服务拆分继续推进：将 Graph Run、Graph Checkpoint 创建、最新运行态查询和任务图状态推进迁移到独立 task_graph_runtime service，保持任务启动、Review 决策和批量取消运行态契约不变 | Codex |
| v1.1.257 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务列表 SQL read model 入口、时间过滤解析、任务摘要投影和列表性能观测响应迁移到独立 task_listing service，保持任务管理列表分页/筛选/排序契约不变 | Codex |
| v1.1.256 | 2026-06-06 | 后端任务服务拆分继续推进：将 Code Review executor payload、执行器选择、输出归一化和报告创建迁移到独立 task_code_review_execution service，保持代码评审任务启动、失败和报告契约不变 | Codex |
| v1.1.255 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务批量取消、批量重试和异常归一化逻辑迁移到独立 task_batch_operations service，保持任务批量接口契约和回归测试不变 | Codex |
| v1.1.254 | 2026-06-06 | 前端页面测试拆分继续推进：将用户洞察登记/处理/迭代建议和研发运营指标/采集/待归属回归迁移到独立 OperationalInsightsPages.test.tsx，继续降低 App.test.tsx 单文件维护压力 | Codex |
| v1.1.253 | 2026-06-06 | 前端页面测试拆分继续推进：将 Bug 管理证据/重复归并编辑、批量处理和登记 Bug 目标版本选择回归迁移到独立 BugManagementPage.test.tsx，继续降低 App.test.tsx 单文件维护压力 | Codex |
| v1.1.252 | 2026-06-06 | 前端页面测试拆分继续推进：抽取共享 proComponentsMock，并将用户管理角色选项、角色管理目录与详情回归迁移到独立 SystemManagementPages.test.tsx，减少 App.test.tsx 页面职责聚集 | Codex |
| v1.1.251 | 2026-06-06 | 拆分前端管理列表组件测试：将 ManagementListPage 固定布局、默认列宽、横向滚动和右固定操作列回归迁移到独立 ManagementListPage.test.tsx，启动 App.test.tsx 页面巨型测试拆分 | Codex |
| v1.1.250 | 2026-06-06 | 拆分 repository-first 读路径回归测试：将知识文档、知识沉淀、知识检索、审计事件、模型网关配置和模型日志的 stale runtime 回归迁移到独立 test_repository_read_paths.py，继续降低 test_database_persistence.py 单文件维护压力 | Codex |
| v1.1.249 | 2026-06-06 | 拆分管理类列表 SQL read model 回归测试：将 DevOps、用户洞察、需求、Bug、产品和迭代版本分页/筛选/排序防回退用例迁移到独立 test_management_list_read_models.py，降低 test_database_persistence.py 单文件维护压力 | Codex |
| v1.1.248 | 2026-06-06 | 补充任务流程跨表写事务仓储边界验收，验证任务生成、任务启动、Review 决策和任务状态更新由 TaskReadRepository 承接，PostgresSnapshotRepository 不再直接编排这些 SQL upsert | Codex |
| v1.1.247 | 2026-06-06 | 调整需求和任务写入仓储边界验收，去除 PostgresSnapshotRepository 私有 upsert 兼容入口依赖，保留公开保存方法和 DB-first 写入回归验证 | Codex |
| v1.1.246 | 2026-06-06 | 调整产品配置写入仓储边界验收，去除 PostgresSnapshotRepository 私有 upsert 兼容入口依赖，保留公开 save_product_config/save_product_config_record/delete_product_config_record 委托验证 | Codex |
| v1.1.245 | 2026-06-06 | 补充表维护 helper 仓储边界验收，验证 delete_missing/delete_missing_ids 由 TableMaintenanceRepository 承接，persistence.py 不再保留通用删除 SQL 实现 | Codex |
| v1.1.244 | 2026-06-06 | 补充系统状态仓储边界验收，验证数据库发号器、历史 snapshot load/save 均委托 SystemStateRepository，DB-first id counters 和历史 app_state_snapshots 兼容测试保持通过 | Codex |
| v1.1.243 | 2026-06-06 | 补充产品配置读取 SQL 下沉仓储边界验收，验证产品详情、版本、模块、Git 仓库和相关系统读取均由 ProductConfigReadRepository 承接，PostgresSnapshotRepository 不回退直接 SQL | Codex |
| v1.1.242 | 2026-06-06 | 补充管理列表统一表格根样式和可见页面回归验收，验证统一组件稳定 className、工具栏/单元格约束，并通过需求、角色、用户洞察和研发运营真实页面 smoke | Codex |
| v1.1.241 | 2026-06-06 | 补充需求管理列表布局回归验收，验证需求标题、迭代版本和操作列固定宽度、1600 横向滚动、详情页入口收敛到更多菜单，并通过真实页面 smoke | Codex |
| v1.1.240 | 2026-06-06 | 补充 PersistentMemoryStore 测试兼容层拆分验收，验证历史恢复、运行态过期和 DB-first 回归在迁移到 persistent_memory_store 后保持稳定 | Codex |
| v1.1.239 | 2026-06-06 | 补充 PostgresRuntimeStore runtime 模块拆分验收，验证 main.py 直接装配 persistence_runtime 后 data_access_mode、runtime store 和 DB-first 回归保持稳定 | Codex |
| v1.1.238 | 2026-06-06 | 补充 persistence.py payload/helper 拆分验收，验证 snapshot 恢复、清理、counter 同步和 DB-first 列表 read model 在拆到 persistence_payloads 后全量后端回归通过 | Codex |
| v1.1.237 | 2026-06-06 | 补充 persistence.py contracts/constants 拆分验收，验证仓储 Protocol 抽取后 persistence repository 边界、router 边界和 DB-first 列表 read model 回归不受影响 | Codex |
| v1.1.236 | 2026-06-06 | 补充 main.py 最终装配入口边界和任务工作流 repository source context 非 MemoryStore 回归验收，验证 legacy helper 删除后路由与 DB-first 契约不回退 | Codex |
| v1.1.235 | 2026-06-06 | 补充管理列表自定义渲染列布局验收，验证复杂 Tag/Space/状态摘要列不会撑开角色、用户洞察、DevOps 等宽表页面 | Codex |
| v1.1.234 | 2026-06-06 | 补充需求全链路详情版本内多需求对比页面验收，验证同版本需求数量、状态分布和当前需求位置展示 | Codex |
| v1.1.233 | 2026-06-06 | 补充需求全链路详情导出链路报告页面验收，验证导出 Markdown 报告包含需求标题、链路摘要、代码评审、Bug 和时间线信息 | Codex |
| v1.1.232 | 2026-06-06 | 补充需求全链路详情时间线类型筛选页面验收，验证按“代码评审”筛选后只展示代码评审事件并回显筛选后/总事件数 | Codex |
| v1.1.231 | 2026-06-06 | 补充模型网关配置列表服务端分页/筛选/排序和查询性能观测回归测试，验证 `GET /api/system/model-gateway-configs` 状态/默认配置筛选、分页元数据、`query/performance` 与非法排序字段校验；前端模型网关页测试更新为远程分页请求 | Codex |
| v1.1.230 | 2026-06-06 | 补充真实浏览器 smoke 关键文本断言验收，`scripts/web_page_smoke.mjs` 支持 `--expect-text ROUTE=TEXT`，生产就绪门禁默认验证角色管理页面渲染“系统管理员”，避免页面非空但核心数据未加载的假阳性 | Codex |
| v1.1.229 | 2026-06-06 | 补充角色管理列表服务端分页/筛选/排序和查询性能观测回归测试，验证 `GET /api/auth/roles` 分类/业务角色筛选、分页元数据、`query/performance` 与非法排序字段校验；前端角色页测试更新为远程分页请求 | Codex |
| v1.1.228 | 2026-06-06 | 补充任务管理待确认 Review 子表布局回归测试，验证固定布局、横向滚动宽度、摘要省略和操作列右固定，同时继续覆盖任务批量重试/取消请求与结果弹窗 | Codex |
| v1.1.227 | 2026-06-06 | 补充用户管理列表服务端分页/筛选/排序和查询性能观测回归测试，验证 `GET /api/users` 角色/状态/显示名筛选、分页元数据、`query/performance` 与非法排序字段校验；前端用户页测试更新为远程分页请求 | Codex |
| v1.1.226 | 2026-06-06 | 补充管理列表稳定表格默认值与角色详情承载测试，验证默认固定布局、数字横向滚动宽度、操作列右固定、角色入口/权限数量摘要和详情完整展示 | Codex |
| v1.1.225 | 2026-06-06 | persistence.py 拆分验收补充生命周期/看板写入委托边界测试，并复用 lifecycle/dashboard、缓存和 DB-first 持久化测试验证 edge/risk/snapshot 写入契约不回退 | Codex |
| v1.1.224 | 2026-06-06 | persistence.py 拆分验收补充采集运行/待归属写入委托边界测试，并复用 DB-first 持久化测试验证 collector run 与 pending attribution 写入契约不回退 | Codex |
| v1.1.223 | 2026-06-06 | persistence.py 拆分验收补充用户洞察写入委托边界测试，并复用用户洞察/DB-first 持久化测试验证反馈、使用指标、迭代建议/决策和转需求写入契约不回退 | Codex |
| v1.1.222 | 2026-06-06 | persistence.py 拆分验收补充 DevOps 指标写入委托边界测试，并复用 DevOps/DB-first 持久化测试验证 GitLab daily、Jenkins release 和线上日志写入契约不回退 | Codex |
| v1.1.221 | 2026-06-06 | persistence.py 拆分验收补充知识写入委托边界测试，并复用知识治理和 DB-first 持久化测试验证知识文档/chunk/沉淀写入契约不回退 | Codex |
| v1.1.220 | 2026-06-06 | persistence.py 拆分验收补充 Bug 写入委托边界测试，并复用 Bug 生命周期和 DB-first 持久化测试验证 Bug 写入、删除和重复缺陷引用契约不回退 | Codex |
| v1.1.219 | 2026-06-06 | persistence.py 拆分验收补充任务运行态写入委托边界测试，并复用任务/Review/Graph 和 DB-first 持久化测试验证运行态写入契约不回退 | Codex |
| v1.1.218 | 2026-06-06 | persistence.py 拆分验收补充 AI 任务主表写入委托边界测试，并复用任务 API 契约和 DB-first 持久化测试验证任务写入契约不回退 | Codex |
| v1.1.217 | 2026-06-06 | persistence.py 拆分验收补充需求写入委托边界测试，并复用需求生命周期、批量操作和 DB-first 持久化测试验证需求写入契约不回退 | Codex |
| v1.1.216 | 2026-06-06 | persistence.py 拆分验收补充产品配置写入委托边界测试，并复用产品配置与 DB-first 持久化测试验证产品/版本/模块/Git 仓库/相关系统写入契约不回退 | Codex |
| v1.1.215 | 2026-06-06 | persistence.py 拆分验收补充审计写入委托边界测试，并复用 DB-first 持久化测试验证审计保存、追加和恢复契约不回退 | Codex |
| v1.1.214 | 2026-06-06 | persistence.py 拆分验收补充 Git review 写入委托边界测试，并复用 GitLab/GitHub 快照、代码评审报告和 DB-first 持久化测试验证快照/报告写入契约不回退 | Codex |
| v1.1.213 | 2026-06-06 | persistence.py 拆分验收补充模拟 Issue 写回写入委托边界测试，并复用 mock writeback 与 DB-first 持久化测试验证幂等写回、恢复和 stale 数据过滤契约不回退 | Codex |
| v1.1.212 | 2026-06-06 | persistence.py 拆分验收补充 AI 助手写入委托边界测试，并复用助手聊天、助手上下文和 DB-first 持久化测试验证用户级历史/引用写入契约不回退 | Codex |
| v1.1.211 | 2026-06-06 | persistence.py 拆分验收补充模型网关写入委托边界测试，并复用模型网关 API 与 DB-first 持久化测试验证配置/日志写入契约不回退 | Codex |
| v1.1.210 | 2026-06-06 | 后端大文件拆分验收补充任务工作流/Review/Graph/Markdown 导出 legacy helper 清理回归，复用 router 边界、Graph Runtime、Review 行为、代码评审、模型网关和 DB-first 持久化测试验证契约不回退 | Codex |
| v1.1.209 | 2026-06-06 | 后端大文件拆分验收补充模型网关/代码评审 executor legacy helper 清理回归，复用模型网关、代码评审报告、AI 任务和 DB-first 持久化测试验证契约不回退 | Codex |
| v1.1.208 | 2026-06-06 | 后端大文件拆分验收补充 dashboard/DevOps/用户洞察 legacy 投影 helper 清理回归，复用看板、生命周期、DevOps、用户洞察和 DB-first 持久化测试验证契约不回退 | Codex |
| v1.1.207 | 2026-06-06 | 后端大文件拆分验收补充 operational_records legacy helper 清理回归，复用采集运行、待归属、DevOps 指标明细和 router 边界测试验证契约不回退 | Codex |
| v1.1.206 | 2026-06-06 | 后端大文件拆分验收补充需求全链路 legacy helper 清理回归，复用 requirements router 边界、需求生命周期和 DB-first stale runtime 测试验证契约不回退 | Codex |
| v1.1.205 | 2026-06-06 | 后端大文件拆分验收补充知识 legacy helper 清理回归，复用知识 router 边界、知识治理、DB-first 写入和 stale runtime 测试验证契约不回退 | Codex |
| v1.1.204 | 2026-06-06 | 后端大文件拆分验收补充生命周期 legacy helper 清理回归，复用 lifecycle router 边界、生命周期上下文 service、dashboard source rows 和 stale runtime 测试验证契约不回退 | Codex |
| v1.1.203 | 2026-06-06 | persistence.py 拆分验收补充业务大脑 read model 委托边界测试，覆盖 Brain App 恢复读取和 API 契约不回退 | Codex |
| v1.1.202 | 2026-06-06 | persistence.py 拆分验收扩展知识 read model 委托边界测试，覆盖知识恢复读取、知识文档列表、沉淀候选和检索委托契约 | Codex |
| v1.1.201 | 2026-06-06 | persistence.py 拆分验收扩展 Bug read model 委托边界测试，覆盖 Bug 恢复读取、Bug 列表 count/list 和分页筛选排序委托契约 | Codex |
| v1.1.200 | 2026-06-06 | persistence.py 拆分验收扩展任务 read model 委托边界测试，覆盖 AI 任务恢复、workflow runtime 恢复、任务列表 count/list 和待 Review 列表委托契约 | Codex |
| v1.1.199 | 2026-06-06 | persistence.py 拆分验收扩展需求 read model 委托边界测试，覆盖需求台账恢复读取、需求列表 count/list 和分页筛选排序委托契约 | Codex |
| v1.1.198 | 2026-06-06 | persistence.py 拆分验收扩展产品配置 read model 委托边界测试，覆盖产品配置恢复读取、产品列表、迭代版本列表和分页筛选排序委托契约 | Codex |
| v1.1.197 | 2026-06-06 | persistence.py 拆分验收扩展 AI 助手 read model 委托边界测试，覆盖会话/消息恢复读取、会话列表和用户级消息查询委托契约 | Codex |
| v1.1.196 | 2026-06-06 | persistence.py 拆分验收扩展用户洞察 read model 委托边界测试，覆盖使用指标、用户反馈、迭代规划恢复/列表读取和统一洞察列表委托契约 | Codex |
| v1.1.195 | 2026-06-06 | persistence.py 拆分验收扩展 DevOps read model 委托边界测试，覆盖 GitLab daily、Jenkins release、线上日志原始指标恢复/列表读取和统一运营列表委托契约 | Codex |
| v1.1.194 | 2026-06-06 | persistence.py 拆分验收补充生命周期上下文/首页看板读取委托边界测试，并复用 lifecycle/dashboard DB-first source rows、写入和 stale runtime 回归验证 LifecycleDashboardReadRepository 契约 | Codex |
| v1.1.193 | 2026-06-06 | persistence.py 拆分验收补充模拟 Issue 写回恢复读取委托边界测试，并复用 mock writeback 持久化、恢复和 stale 数据过滤回归验证 MockWritebackReadRepository 契约 | Codex |
| v1.1.192 | 2026-06-06 | persistence.py 拆分验收补充 Git review 快照/报告恢复读取委托边界测试，并复用 GitLab/GitHub 快照、代码评审报告和 DB-first 恢复回归验证 GitReviewReadRepository 契约 | Codex |
| v1.1.191 | 2026-06-06 | persistence.py 拆分验收补充采集运行/待归属队列读取委托边界测试，并复用 collector、pending attribution、DB-first stale runtime 和 router 边界测试验证 OperationalCollectionReadRepository 契约 | Codex |
| v1.1.190 | 2026-06-06 | persistence.py 拆分验收补充审计事件读取委托边界测试，并复用审计列表契约、DB-first stale runtime 和 audit router 边界测试验证 AuditReadRepository 契约 | Codex |
| v1.1.189 | 2026-06-06 | persistence.py 拆分验收补充模型网关配置/日志读取委托边界测试，并复用模型网关 API 与 DB-first 持久化回归验证 ModelGatewayReadRepository 契约 | Codex |
| v1.1.188 | 2026-06-06 | persistence.py 拆分验收补充 AI 助手历史读取委托边界测试，并复用助手服务、用户级历史隔离和 DB-first 持久化回归验证 AssistantChatReadRepository 契约 | Codex |
| v1.1.187 | 2026-06-06 | persistence.py 拆分验收补充知识中心 read model 委托边界测试，并复用知识文档列表、知识治理和 DB-first stale runtime 回归验证 KnowledgeReadRepository 契约 | Codex |
| v1.1.186 | 2026-06-06 | 后端大文件拆分验收补充 legacy helper 清理回归：复用 GitLab/GitHub 快照、用户洞察/迭代规划、生命周期上下文和 router 边界测试，验证删除 main.py 旧实现副本后服务化契约保持稳定 | Codex |
| v1.1.185 | 2026-06-06 | 生命周期上下文验收补充 lifecycle router 不得回调 legacy main 的架构边界回归，并复用 lifecycle_context 与 DB-first source rows 测试验证上下游、风险和 materialize 契约 | Codex |
| v1.1.184 | 2026-06-06 | GitLab/GitHub 代码评审链路验收补充 git_review router 不得回调 legacy main 的架构边界回归，并复用 GitLab MR、GitHub PR、DB-first 快照与审计测试验证服务化契约 | Codex |
| v1.1.183 | 2026-06-06 | 用户洞察与迭代规划验收补充 user_insights router 不得回调 legacy main 的架构边界回归，并复用使用指标、用户反馈、迭代建议和 DB-first 写入测试验证服务化契约 | Codex |
| v1.1.182 | 2026-06-06 | DevOps 指标明细验收补充 devops_metrics router 不得回调 legacy main 的架构边界回归，并复用 DevOps 指标、运营列表和 DB-first 写入测试验证服务化契约 | Codex |
| v1.1.181 | 2026-06-06 | 采集运行与待归属处理验收补充 collectors/attribution router 不得回调 legacy main 的架构边界回归，并复用 collector、pending attribution 和 DB-first 写入测试验证服务化契约 | Codex |
| v1.1.180 | 2026-06-06 | AI 任务创建验收补充 tasks router 整体不得回调 legacy main 的架构边界回归，并复用技术方案、后续任务、发布准备、代码评审和 DB-first 写入测试验证创建契约 | Codex |
| v1.1.179 | 2026-06-06 | AI 任务批量重试验收补充 batch-retry handler 不得回调 legacy main 的架构边界回归，并复用契约测试验证重试成功、不可重试/重复/不存在 skipped 和审计 | Codex |
| v1.1.178 | 2026-06-06 | Review 决策验收补充 approve/edit-approve/reject/request-more-info handler 不得回调 legacy main 的架构边界回归，并复用 Review 行为与 DB-first no-persist 测试验证保存契约 | Codex |
| v1.1.177 | 2026-06-06 | AI 任务启动验收补充 start handler 不得回调 legacy main 的架构边界回归，并同步模型网关失败注入测试到 model_gateway service opener | Codex |
| v1.1.176 | 2026-06-06 | AI 任务启动业务逻辑下沉到 ai_tasks service，回归覆盖 Graph Run/Checkpoint、模型失败、失败重试和 DB-first no-persist 保存契约 | Codex |
| v1.1.175 | 2026-06-06 | AI 任务启动前置迁移补充模型网关任务调用 helper service 化回归，覆盖模型失败、失败重试和 DB-first no-persist 写入契约 | Codex |
| v1.1.174 | 2026-06-06 | AI 任务批量取消验收补充 batch-cancel handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.173 | 2026-06-06 | AI 任务取消和补充信息提交验收补充 state write handlers 不得回调 legacy main 的架构边界回归，并复用 DB-first no-persist 测试验证任务状态直接写 repository | Codex |
| v1.1.172 | 2026-06-06 | Graph Run 列表、待确认 Review 列表和 Review 详情验收补充 read handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.171 | 2026-06-06 | AI 任务详情验收补充 detail handler 不得回调 legacy main 的架构边界回归，并覆盖 Graph/Review 流程下任务详情投影稳定性 | Codex |
| v1.1.170 | 2026-06-06 | 批量推进需求状态验收补充 batch-advance-status handler 和 requirements router 整体不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.169 | 2026-06-06 | 批量排期需求验收补充 batch-schedule handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.168 | 2026-06-06 | 批量分配需求负责人验收补充 batch-assign-owner handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.167 | 2026-06-06 | 批量需求生成产品详细设计任务验收补充 batch-generate-tasks handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.166 | 2026-06-06 | 单条需求生成产品详细设计任务验收补充 generate-task handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.165 | 2026-06-06 | 需求审批、驳回和关闭验收补充 decision handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.164 | 2026-06-06 | 需求修改和删除验收补充 update/delete handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.163 | 2026-06-06 | 需求创建验收补充 create handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.162 | 2026-06-06 | 需求详情和需求全链路验收补充 read handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.161 | 2026-06-06 | 研发运营统一列表验收补充 operational metrics handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.160 | 2026-06-06 | 用户洞察统一列表验收补充 items handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.159 | 2026-06-06 | AI 任务列表验收补充 list handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.158 | 2026-06-06 | 需求列表验收补充 list handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.157 | 2026-06-06 | Bug 管理验收升级为整个 bugs router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.156 | 2026-06-06 | Bug 创建、批量更新、修改和删除验收补充 write handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.155 | 2026-06-06 | 知识文档更新、重建索引和删除验收补充 write handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.154 | 2026-06-06 | 知识文档创建验收补充 create handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.153 | 2026-06-06 | 知识沉淀采纳/驳回验收补充 decision handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.152 | 2026-06-06 | 知识搜索验收补充 search handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.151 | 2026-06-06 | 知识沉淀候选列表验收补充 list handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.150 | 2026-06-06 | 知识文档列表验收补充 list handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.149 | 2026-06-06 | 模拟 Issue 写回验收补充 writeback router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.148 | 2026-06-06 | 审计事件列表验收补充 audit router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.147 | 2026-06-06 | 代码评审报告读取验收补充 code_review_reports router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.146 | 2026-06-06 | Markdown 导出验收补充 export router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.145 | 2026-06-06 | Bug 批量处理页面验收补充结果明细弹窗，覆盖批次号、更新数、跳过数和 skipped 原因展示 | Codex |
| v1.1.144 | 2026-06-06 | 任务批量取消/重试验收补充结果明细弹窗，覆盖批次号、成功数、仍失败数和 skipped 原因展示 | Codex |
| v1.1.143 | 2026-06-06 | 需求批量操作验收补充结果明细弹窗，覆盖批次号、成功数、跳过数和 skipped 原因展示 | Codex |
| v1.1.142 | 2026-06-06 | 需求批量推进状态验收补充未排期保护，覆盖 `REQUIREMENT_VERSION_REQUIRED` skipped 明细 | Codex |
| v1.1.141 | 2026-06-05 | 补充需求管理批量推进状态验收，覆盖合法状态推进、不符合路径 skipped 和审计 | Codex |
| v1.1.140 | 2026-06-05 | 补充需求管理批量分配负责人验收，覆盖负责人字段更新、关闭/重复/不存在 skipped 和审计 | Codex |
| v1.1.139 | 2026-06-05 | 补充任务管理批量重试验收，覆盖可重试失败任务恢复、终态/重复/不存在 skipped 和审计 | Codex |
| v1.1.138 | 2026-06-05 | 补充 AI 助手工具化查询引用链接验收，覆盖服务端 references、历史消息持久化和前端来源展示 | Codex |
| v1.1.137 | 2026-06-05 | 补充任务管理多选批量取消验收，覆盖合法任务取消、终态/重复/不存在任务 skipped 和审计 | Codex |
| v1.1.136 | 2026-06-05 | 补充需求全链路详情阶段明细折叠区和实体跳转链接页面验收 | Codex |
| v1.1.135 | 2026-06-05 | 补充前端管理主列表默认普通列宽、右侧固定操作列宽和横向滚动兜底的组件回归验收 | Codex |
| v1.1.134 | 2026-06-05 | 补充 `scripts/release_smoke.sh` 固定发布 smoke 入口验收，确保默认执行 `production_readiness_check.py --rebuild --web-smoke` | Codex |
| v1.1.133 | 2026-06-05 | 补充核心管理列表 `performance.p95_target_ms`、列表级 P95 目标和超目标慢查询日志验收 | Codex |
| v1.1.132 | 2026-06-05 | 补充 PostgresSnapshotRepository 研发运营统一列表 read model 委托到 DevopsReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.131 | 2026-06-05 | 补充 PostgresSnapshotRepository 用户洞察统一列表 read model 委托到 UserInsightReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.130 | 2026-06-05 | 补充 PostgresSnapshotRepository Bug 管理 read model 委托到 BugReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.129 | 2026-06-05 | 补充 PostgresSnapshotRepository AI 任务 read model 委托到 TaskReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.128 | 2026-06-05 | 补充 PostgresSnapshotRepository 需求管理 read model 委托到 RequirementReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.127 | 2026-06-05 | 补充 PostgresSnapshotRepository 产品配置 read model 委托到 ProductConfigReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.126 | 2026-06-05 | 补充采集运行、待归属处理和生命周期上下文 API 独立 router 挂载、功能回归和 main.py 无业务路由边界验收 | Codex |
| v1.1.125 | 2026-06-05 | 补充 Markdown 导出 API 独立 export router 挂载、完成态导出和读取权限回归验收 | Codex |
| v1.1.124 | 2026-06-05 | 补充写回结果、代码评审报告和审计事件 API 独立 router 挂载、DB-first 写入/读取和单一路由归属回归验收 | Codex |
| v1.1.123 | 2026-06-05 | 补充用户洞察与迭代建议 API 独立 user_insights router 挂载、SQL/read model 列表和单一路由归属回归验收 | Codex |
| v1.1.122 | 2026-06-05 | 补充研发运营指标 API 独立 devops_metrics router 挂载、SQL/read model 列表和单一路由归属回归验收 | Codex |
| v1.1.121 | 2026-06-05 | 补充知识中心 API 独立 knowledge router 挂载和单一路由归属回归验收 | Codex |
| v1.1.120 | 2026-06-05 | 补充 AI 任务列表与创建 handler 脱离 main.py 的架构边界回归验收 | Codex |
| v1.1.119 | 2026-06-05 | 补充 AI 任务与 Review API 独立 tasks router 挂载、任务列表 SQL read model 和单一路由归属回归验收 | Codex |
| v1.1.118 | 2026-06-05 | 补充需求交付 API 独立 requirements router 挂载、SQL read model 列表和单一路由归属回归验收 | Codex |
| v1.1.117 | 2026-06-05 | 补充 Bug 管理 API 独立 bugs router 挂载、生命周期 service 复用和单一路由归属回归验收 | Codex |
| v1.1.116 | 2026-06-05 | 补充 GitLab MR / GitHub PR 预览、列表和快照 API 独立 git_review router 挂载和单一路由归属回归验收 | Codex |
| v1.1.115 | 2026-06-05 | 补充业务大脑只读 API 独立 brain_apps router 挂载、repository-first service 拆分和单一路由归属回归验收 | Codex |
| v1.1.114 | 2026-06-05 | 补充模型网关配置和日志 API 独立 model_gateway router 挂载、service helper 拆分和单一路由归属回归验收 | Codex |
| v1.1.113 | 2026-06-05 | 补充相关系统 API 独立 related_systems router 挂载和单一路由归属回归验收 | Codex |
| v1.1.112 | 2026-06-05 | 补充产品 Git 仓库 API 独立 product_git_repositories router 挂载和单一路由归属回归验收 | Codex |
| v1.1.111 | 2026-06-05 | 补充产品模块 API 独立 product_modules router 挂载和单一路由归属回归验收 | Codex |
| v1.1.110 | 2026-06-05 | 补充迭代版本 API 独立 product_versions router 挂载和单一路由归属回归验收 | Codex |
| v1.1.109 | 2026-06-05 | 补充产品主体 CRUD API 独立 products router 挂载和单一路由归属回归验收 | Codex |
| v1.1.108 | 2026-06-05 | 补充用户管理 API 独立 users router 挂载和单一路由归属回归验收 | Codex |
| v1.1.107 | 2026-06-05 | 补充平台健康检查与长期记忆状态 API 独立 platform router 挂载和单一路由归属回归验收 | Codex |
| v1.1.106 | 2026-06-05 | 补充认证与角色目录 API 独立 auth router 挂载和单一路由归属回归验收 | Codex |
| v1.1.105 | 2026-06-05 | 补充首页 IT 团队看板 API 独立 router 挂载和单一路由归属回归验收 | Codex |
| v1.1.104 | 2026-06-05 | 补充 AI 助手 API 独立 router 迁移后的接口回归验收 | Codex |
| v1.1.103 | 2026-06-05 | 补充 AI 助手聊天工作流 service 拆分和用户级历史隔离 service 单测验收 | Codex |
| v1.1.102 | 2026-06-05 | 补充首页 IT 团队看板缓存命中、强制刷新、缓存元数据和慢查询日志验收 | Codex |
| v1.1.101 | 2026-06-05 | 补充 `scripts/web_page_smoke.mjs` 浏览器页面 smoke 和列表慢查询日志验收 | Codex |
| v1.0.0 | 2026-05-27 | 基于 PRD 和技术规格生成项目级测试用例 | Claude |
| v1.0.1 | 2026-05-27 | 对齐当前 API 契约，补充产品上下文和配置接口测试 | Codex |
| v1.0.2 | 2026-05-28 | 补充四个主体独立维护、需求任务解耦、知识中心运营和主体级审计测试 | Claude |
| v1.0.3 | 2026-05-29 | 补充 GitLab、线上日志、Jenkins、首页看板和 Bug 管理测试用例 | Claude |
| v1.0.4 | 2026-05-29 | 补充研发全链路 AI 任务类型测试覆盖 | Claude |
| v1.0.5 | 2026-05-29 | 补充软件研发全流程感知测试用例 | Claude |
| v1.0.6 | 2026-05-29 | 对齐 PRD 阶段边界，拆分人工确认门禁测试并更新全流程感知编号 | Claude |
| v1.0.7 | 2026-05-29 | 补充用户使用洞察、用户反馈收集和 AI 迭代规划建议测试用例 | Claude |
| v1.0.8 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 纳入 v1 MVP，新增 MR diff 快照、code-review 执行器、人工确认和不回写 GitLab 的 P0 测试 | Claude |
| v1.0.9 | 2026-05-29 | 修正 v1 MVP 与 v1.1/v1.2 测试验收口径，明确 MVP 占位入口和后续完整闭环能力的测试边界 | Claude |
| v1.1.0 | 2026-05-29 | 对齐 PRD v1.1.0，补充 MVP-A/B/C 验收切片，修正 GitLab 每日指标采集阶段归属 | Claude |
| v1.1.1 | 2026-05-29 | 修复产品评审问题：将 GitLab 预览和 diff 快照前置到 MVP-A，拆分 AC4/AC21 测试，改为阶段 + 阶段内优先级口径 | Claude |
| v1.1.2 | 2026-05-30 | 将 Bug 管理基础接口纳入 v1.1 自动化验收，覆盖登记、筛选、状态机、重复归并、权限和审计 | Codex |
| v1.1.3 | 2026-05-31 | 补充审计按操作者和时间范围过滤，以及审计列表详情、链路追踪页面验收 | Codex |
| v1.1.4 | 2026-05-31 | 补充 code_review 执行器失败专用错误码和审计断言 | Codex |
| v1.1.5 | 2026-05-31 | 补充 GitLab MR diff 超限失败审计验收 | Codex |
| v1.1.6 | 2026-05-31 | 补充 GitLab MR 变更文件数超限验收 | Codex |
| v1.1.7 | 2026-05-31 | 补充 GitLab MR 单文件 diff 行数超限验收 | Codex |
| v1.1.8 | 2026-05-31 | 补充 MVP 角色目录接口、用户管理角色固定选择和 SQL 角色字典验收 | Codex |
| v1.1.9 | 2026-05-31 | 补充产品配置写入 PostgreSQL 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.10 | 2026-05-31 | 补充需求台账写入 PostgreSQL `requirements` 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.11 | 2026-05-31 | 补充 AI 任务写入 PostgreSQL `ai_tasks` 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.12 | 2026-05-31 | 补充人工确认、Graph Run 和检查点写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.13 | 2026-05-31 | 补充角色目录职责、数据范围、决策范围和前端角色目录加载验收 | Codex |
| v1.1.14 | 2026-05-31 | 补充知识文档、知识沉淀候选和审计事件写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.15 | 2026-05-31 | 补充 Bug 管理写入 PostgreSQL `bugs` 结构表并可恢复的持久化验收 | Codex |
| v1.1.16 | 2026-05-31 | 补充模型网关配置和调用元数据日志写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.17 | 2026-05-31 | 补充 GitLab MR 快照和 Code Review 报告写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.18 | 2026-05-31 | 补充模拟 Issue 回写写入 PostgreSQL `mock_issues` 结构表并可恢复的持久化验收 | Codex |
| v1.1.19 | 2026-05-31 | 补充相关系统写入 PostgreSQL `related_systems` 结构表并可恢复的持久化验收 | Codex |
| v1.1.20 | 2026-05-31 | 补充角色业务映射、可见入口、限制边界和知识索引失败重试验收 | Codex |
| v1.1.21 | 2026-06-01 | 补充生命周期从审计主体、Review、报告、模拟 Issue 和知识沉淀起点追踪验收 | Codex |
| v1.1.22 | 2026-06-01 | 补充知识检索不得为缺失 chunk 的 indexed 文档合成兜底结果的验收 | Codex |
| v1.1.23 | 2026-06-01 | 补充 GitLab MR 相同 diff 快照复用和审计验收 | Codex |
| v1.1.24 | 2026-06-01 | 补充迭代规划建议基于真实反馈/Bug 证据生成、确认和可选转需求的自动化验收 | Codex |
| v1.1.25 | 2026-06-01 | 补充用户使用指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.26 | 2026-06-01 | 补充 GitLab 每日代码指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.27 | 2026-06-01 | 补充 Jenkins 发布记录真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.28 | 2026-06-01 | 补充线上运行日志指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.29 | 2026-06-01 | 补充开发计划和自动化测试任务从已确认技术方案创建、人工确认和 AI 自动测试 Bug 入库验收 | Codex |
| v1.1.30 | 2026-06-01 | 补充发布评估和上线后分析任务从已确认上游任务创建、人工确认和 AI 上线后 Bug 入库验收 | Codex |
| v1.1.31 | 2026-06-01 | 补充首页 IT 团队看板产品筛选页面验收和前端服务查询参数验收 | Codex |
| v1.1.32 | 2026-06-01 | 补充首页 IT 团队看板按产品过滤知识文档和审计事件验收 | Codex |
| v1.1.33 | 2026-06-02 | 补充 Bug 管理工作台复现步骤、证据 JSON、重复归并和来源只读展示自动化验收 | Codex |
| v1.1.34 | 2026-06-02 | 对账 MVP 详细测试用例状态，将已有自动化覆盖的待测试项标为已覆盖，并保留生产就绪和 v1.2 待验范围 | Codex |
| v1.1.35 | 2026-06-02 | 补充首页 IT 团队看板 Bug、DevOps、线上日志、用户洞察和迭代规划聚合及产品/时间范围下钻验收 | Codex |
| v1.1.36 | 2026-06-02 | 补充生命周期 v1.2 真实证据主体、风险信号和动态缺失上下文自动化验收 | Codex |
| v1.1.37 | 2026-06-02 | 补充采集运行记录 API、持久化、审计和研发运营页面自动化验收 | Codex |
| v1.1.38 | 2026-06-02 | 补充待归属数据队列登记、归属/忽略、持久化、审计和前端页面自动化验收 | Codex |
| v1.1.39 | 2026-06-02 | 补充 AI 任务启动由真实 LangGraph StateGraph 驱动并持久化 runtime/node_path 的验收 | Codex |
| v1.1.40 | 2026-06-02 | 补充 GBrain 长期记忆连接器配置状态和密钥脱敏验收 | Codex |
| v1.1.41 | 2026-06-02 | 补充 GitHub provider、GitHub PR 预览和 diff 快照验收 | Codex |
| v1.1.42 | 2026-06-02 | 补充 AI 助手聊天工作台和系统进展问答验收 | Codex |
| v1.1.43 | 2026-06-03 | 记录 AI 助手真实需求全链路复跑结果，并补充 GitHub PR 列表、健康检查和失败任务重试验收 | Codex |
| v1.1.44 | 2026-06-03 | 记录 AI Brain GitHub PR 复跑卡点，补充 code-review 外部命令缺失时复用模型网关、携带 Review 上下文并规范化输出的回归验收 | Codex |
| v1.1.45 | 2026-06-03 | 补充 Embedding 不可用时文本索引兜底和补向量索引验收 | Codex |
| v1.1.46 | 2026-06-03 | 补充 Chat-only 模型网关、单独 Embedding 连接和向量兼容过滤验收 | Codex |
| v1.1.47 | 2026-06-03 | 补充新增需求可不指定迭代版本、需求池排期和需求交付/迭代版本页面验收 | Codex |
| v1.1.48 | 2026-06-03 | 补充 DB-first 任务运行态/Review repository 读路径和 Mock Writeback handler 级写入回归验收 | Codex |
| v1.1.49 | 2026-06-03 | 补充知识沉淀候选列表 repository-first 读取和运行态 store 过期回归验收 | Codex |
| v1.1.50 | 2026-06-03 | 补充知识检索 repository-first 候选查询、权限过滤和运行态 store 过期回归验收 | Codex |
| v1.1.51 | 2026-06-03 | 补充知识沉淀审核写接口 repository 当前记录读取和运行态 store 过期回归验收 | Codex |
| v1.1.52 | 2026-06-03 | 补充生命周期上下文和首页 IT 团队看板 repository source rows 聚合、handler 级写回和 stale-runtime 回归验收 | Codex |
| v1.1.53 | 2026-06-03 | 补充需求/任务详情、Graph Run、Review、回写、Code Review 报告和 Markdown 导出 task workflow source rows 读取回归验收 | Codex |
| v1.1.54 | 2026-06-03 | 补充任务启动、取消、补充信息和 Review 决策写路径在全局运行时 store 过期时仍使用 task workflow source rows 的回归验收 | Codex |
| v1.1.55 | 2026-06-03 | 补充 PostgreSQL 启动返回 PostgresRuntimeStore repository 容器且不预加载业务集合的回归验收 | Codex |
| v1.1.56 | 2026-06-03 | 补充产品配置、需求/任务创建和 Bug 写接口在 PostgresRuntimeStore 空启动容器下仍从 repository source rows 校验上下文的回归验收 | Codex |
| v1.1.57 | 2026-06-03 | 补充运营采集、用户洞察和迭代规划写接口在 PostgresRuntimeStore 空启动容器下仍从 repository source rows 校验上下文的回归验收 | Codex |
| v1.1.58 | 2026-06-03 | 补充模型网关配置和 AI 助手聊天写接口在 PostgresRuntimeStore 空启动容器下仍从 repository 上下文恢复当前记录的回归验收 | Codex |
| v1.1.59 | 2026-06-03 | 补充知识文档和知识沉淀写接口在 PostgresRuntimeStore 空启动容器下仍从 repository 上下文恢复当前记录的回归验收 | Codex |
| v1.1.60 | 2026-06-03 | 补充 GitLab/GitHub PR/MR 预览、列表和快照写路径在 PostgresRuntimeStore 空启动容器下仍从 repository 上下文恢复 Git 资源、需求和任务的回归验收 | Codex |
| v1.1.61 | 2026-06-03 | 补充业务大脑只读接口 repository-first、生产 read snapshot fallback 移除、知识沉淀驳回和 Mock Writeback 生成 source rows 回归验收 | Codex |
| v1.1.62 | 2026-06-03 | 补充生命周期上下文 source rows 使用专用 read model 而非 MemoryStore 投影的回归验收 | Codex |
| v1.1.63 | 2026-06-03 | 补充产品配置、模型网关、助手、需求、任务创建和 Bug 写接口直接提交 repository records/payloads，且只读缓存不得作为写入事实源的回归验收 | Codex |
| v1.1.64 | 2026-06-03 | 补充知识索引、任务运行态新增记录、运营采集、用户洞察和迭代规划写接口直接提交 repository payloads，不以请求态集合为 PostgreSQL 写入源的回归验收 | Codex |
| v1.1.65 | 2026-06-04 | 增加前端和用户可见流程提交前的真实网页界面验证门禁用例 | Codex |
| v1.1.66 | 2026-06-04 | 补充多需求批量排期、迭代版本页归集需求和审计验收 | Codex |
| v1.1.67 | 2026-06-04 | 补充 planning 迭代版本可被需求页批量排期选择、archived 版本过滤和批次审计追加保存回归验收 | Codex |
| v1.1.68 | 2026-06-04 | 补充迭代版本状态推进、影响预览、需求状态同步和阻塞项回归验收 | Codex |
| v1.1.69 | 2026-06-04 | 补充需求管理按迭代版本查询需求列表的页面验收 | Codex |
| v1.1.70 | 2026-06-04 | 补充 Bug 管理按迭代版本展示和查询缺陷列表的验收 | Codex |
| v1.1.71 | 2026-06-04 | 调整迭代版本进入测试中的验收口径，确认版本内已进入交付链路的需求统一同步为测试中 | Codex |
| v1.1.72 | 2026-06-04 | 补充登记 Bug 目标版本可选择测试中/已发布未归档版本并过滤 archived 的页面回归验收 | Codex |
| v1.1.73 | 2026-06-04 | 补充日期/时间登记字段使用 Ant Design DatePicker 的页面回归验收 | Codex |
| v1.1.74 | 2026-06-04 | 补充 Bug 管理列表展示创建时间的页面回归验收 | Codex |
| v1.1.75 | 2026-06-04 | 补充需求管理列表展示创建时间且不再展示更新时间的页面回归验收 | Codex |
| v1.1.76 | 2026-06-04 | 补充用户洞察列表固定列宽、操作列右侧固定和详情弹窗页面回归验收 | Codex |
| v1.1.77 | 2026-06-04 | 补充管理主列表统一服务端分页、排序和筛选验收，覆盖用户洞察与研发运营聚合页 | Codex |
| v1.1.78 | 2026-06-04 | 补充需求全链路详情接口和需求管理页时间线弹窗自动化验收 | Codex |
| v1.1.79 | 2026-06-04 | 补充 Bug 管理批量处理接口、状态机跳过明细、批次审计和页面多选入口验收 | Codex |
| v1.1.80 | 2026-06-05 | 补充 AI 助手系统上下文增强验收，覆盖迭代进度、阻塞需求、待确认 Review、代码评审结论、Bug 分布和知识沉淀摘要 | Codex |
| v1.1.81 | 2026-06-05 | 补充 GitLab/GitHub PR/MR 预览展示 diff 文件树、风险摘要和 Review Checklist 的验收 | Codex |
| v1.1.82 | 2026-06-05 | 补充需求全链路详情页展示 PR/MR 快照风险摘要、diff 文件树和 Review Checklist 的页面验收 | Codex |
| v1.1.83 | 2026-06-05 | 补充角色管理列表摘要化展示和详情弹窗承载完整角色定义的页面验收 | Codex |
| v1.1.84 | 2026-06-05 | 补充核心管理主列表 `query/performance` 查询观测元数据、统一表格兜底规范和发布 smoke Web/API 门禁验收 | Codex |
| v1.1.84 | 2026-06-05 | 补充需求批量生成产品详细设计任务、skipped 明细和批次审计的 API 与页面验收 | Codex |
| v1.1.85 | 2026-06-05 | 补充需求全链路详情阶段进度视图页面验收 | Codex |
| v1.1.86 | 2026-06-05 | 补充需求全链路独立详情页直达路由、返回入口和共享展示组件页面验收 | Codex |
| v1.1.87 | 2026-06-05 | 补充用户洞察统一列表 SQL read model 分页、排序和筛选回归验收 | Codex |
| v1.1.88 | 2026-06-05 | 补充需求全链路详情响应式弹窗、阶段状态中文展示和横向裁切回归验收 | Codex |
| v1.1.89 | 2026-06-05 | 补充研发运营统一列表 SQL read model 分页、排序和筛选回归验收 | Codex |
| v1.1.90 | 2026-06-05 | 明确管理主列表服务端 SQL/read model 查询与首页看板 PostgreSQL source rows + Python 聚合的不同验收边界 | Codex |
| v1.1.91 | 2026-06-05 | 补充迭代版本状态推进 domain service 拆分和 service 层单测验收 | Codex |
| v1.1.92 | 2026-06-05 | 补充 Bug 生命周期 domain service 拆分和 service 层单测验收 | Codex |
| v1.1.99 | 2026-06-05 | 补充需求管理和 Bug 管理列表 PostgreSQL SQL read model 分页、排序和筛选回归验收 | Codex |
| v1.1.100 | 2026-06-05 | 补充产品管理和迭代版本列表 PostgreSQL SQL read model 分页、排序和筛选回归验收 | Codex |

---

## 测试用例规范

### 用例编号规则

```text
TC-AIBRAIN-{模块}-{类型}-{序号}

模块:
- PRODUCT: 产品主数据
- REQUIREMENT: 需求管理
- TASK: AI 任务和任务类型
- GRAPH: LangGraph 工作流
- REVIEW: 人工确认
- KNOWLEDGE: 知识检索与沉淀
- OUTPUT: 模拟回写和导出
- AUDIT: 审计
- AUTH: 认证与角色
- DEPLOY: 部署
- CONFIG: 产品、相关系统和模型网关配置
- FLOW: 端到端业务流程和软件研发全流程感知
- DEVOPS: GitLab 代码质量和 Jenkins 发布数据
- OPS: 线上运行日志和运营状态
- BUG: Bug 管理
- DASHBOARD: 首页 IT 团队看板
- PLANNING: 用户使用洞察、用户反馈和 AI 迭代规划
- ATTRIBUTION: 待归属数据队列
- ASSISTANT: AI 助手和系统问答

类型:
- FUNC: 功能测试
- BOUND: 边界测试
- ERR: 异常测试
- API: 接口测试
- PERF: 性能测试
```

### 用例优先级

测试优先级必须和发布阶段一起解读，避免 v1.2 的 P1 用例阻塞 v1 MVP 发布。

| 字段 | 说明 |
|------|------|
| 适用阶段 | MVP-A、MVP-B、MVP-C、v1.1、v1.2 或 MVP 空状态。 |
| 阶段内优先级 | 当前适用阶段内的 P0/P1/P2/P3。 |

| 阶段内优先级 | 说明 | 通过要求 |
|--------------|------|----------|
| P0 | 当前阶段核心闭环，阻塞该阶段发布 | 当前阶段必须 100% 通过 |
| P1 | 当前阶段重要能力，影响演示和验收 | 当前阶段必须 100% 通过 |
| P2 | 当前阶段一般能力，影响体验 | 当前阶段 ≥ 95% 通过 |
| P3 | 当前阶段边缘场景 | 当前阶段 ≥ 90% 通过 |

---

### 提交前真实网页界面验证门禁

影响用户可见页面的变更，必须在提交代码前完成真实网页界面验证。适用范围包括：`apps/web` 下页面、组件、路由和服务层改动；后端接口字段、筛选、分页、聚合、权限或错误语义会影响页面展示的改动；菜单命名、页面标题、弹窗、表格、按钮和主流程交互调整。

提交前验证要求：
1. 启动或重启真实前端服务，访问实际 Web URL，例如 `http://127.0.0.1:5173`；API 使用 PostgreSQL 运行时，不用纯 MemoryStore 或示例数据替代。
2. 如页面空白、旧文案仍在、端口漂移或控制台出现 MFSU/webpack 缓存错误，必须先清理运行环境或重启服务后复测。
3. 使用浏览器打开目标页面并登录实际角色，验证页面标题、菜单、关键内容、真实空状态或目标交互，不得只看测试快照或接口返回。
4. 检查页面不是空白壳，没有框架错误覆盖层；控制台没有本次变更引入的错误。
5. 发布就绪验证应运行 `scripts/production_readiness_check.py --rebuild --web-smoke` 或直接运行 `scripts/web_page_smoke.mjs`，脚本会登录、打开核心页面并检查非空渲染、登录跳转、框架错误覆盖层和 console/runtime error；需要验证真实数据渲染的页面应通过 `--expect-text ROUTE=TEXT` 增加关键文本断言，生产就绪门禁默认验证角色管理页出现“系统管理员”。
6. 提交前在验收记录或最终说明中写明 URL、角色、验证页面、关键交互、通过结果和已运行的自动化命令；真实网页验证未通过不得提交。

---

## MVP 验收切片

v1 MVP 测试按 MVP-A/B/C 三个切片分批执行；三个切片全部通过后才视为 v1 MVP 完整通过。

| 切片 | 阻塞用例 | 验收重点 |
|------|----------|----------|
| MVP-A 基础 + Git 输入闭环 | TC-AIBRAIN-TASK-FUNC-001、TC-AIBRAIN-GRAPH-FUNC-002、TC-AIBRAIN-REVIEW-FUNC-003 中产品详细设计/技术方案部分、TC-AIBRAIN-OUTPUT-FUNC-004A、TC-AIBRAIN-DEPLOY-FUNC-007、TC-AIBRAIN-CONFIG-API-008、TC-AIBRAIN-REQ-FUNC-011、TC-AIBRAIN-REVIEW-FUNC-023A | 需求审批、产品详细设计、技术方案、人工确认、Markdown 导出、基础审计、GitLab/GitHub 只读绑定、MR/PR 预览和 diff 快照可跑通。 |
| MVP-B Git Review 闭环 | TC-AIBRAIN-REVIEW-FUNC-023B、TC-AIBRAIN-REVIEW-API-023C、TC-AIBRAIN-REVIEW-FUNC-003 中 code_review 部分、TC-AIBRAIN-AUDIT-API-006、TC-AIBRAIN-AUDIT-API-013 | 基于 MVP-A 的 MR/PR 快照生成 code_review 报告、人工确认、内部归档和结构表恢复可跑通，且不回写 GitLab/GitHub。 |
| MVP-C 知识与治理闭环 | TC-AIBRAIN-KNOWLEDGE-FUNC-005、TC-AIBRAIN-OUTPUT-FUNC-004B、TC-AIBRAIN-OUTPUT-API-004D、TC-AIBRAIN-OUTPUT-FUNC-004C、TC-AIBRAIN-FLOW-FUNC-010、TC-AIBRAIN-KNOWLEDGE-FUNC-012 | 知识导入、权限过滤检索、知识沉淀审核、模拟 Issue、模拟 Issue 结构表恢复、真实空状态入口和主体级治理可跑通。 |

### 模块：AI 任务与工作流闭环

| 用例编号 | 用例名称 | 优先级 | 适用阶段 | 前置条件 | 测试步骤 | 预期结果 | 自动化 |
|----------|----------|--------|----------|----------|----------|----------|--------|
| TC-AIBRAIN-TASK-FUNC-001 | 创建并启动产品详细设计 AI 任务 | P0 | MVP | 用户已登录，存在 `rd_brain`、已排期需求和 `planning`/`active` 迭代版本 | 1. 创建 product_detail_design 任务 2. 启动任务 3. 查询详情 | 任务从 draft 进入 waiting_review，并返回 review_id 和 task_type | 是 |
| TC-AIBRAIN-TASK-API-001B | AI 任务 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在已排期需求 | 1. 从需求生成产品详细设计任务 2. 查询 PostgreSQL `ai_tasks` 表 3. 启动或取消任务使状态变化 4. 重启 API 后重新查询任务列表和任务详情 | `ai_tasks` 保存默认 `rd_brain` 归属、任务类型、标题、状态、需求快照、产品上下文、输入输出、当前步骤和创建人；API 重启后仍能从结构表恢复任务和 `task` 计数器，Review/Graph 运行态由对应结构表恢复并回填任务关联；任务详情在 PostgreSQL 运行时读取 task workflow repository source rows，运行态 store 过期时仍能返回结构表任务详情；AI 任务和 Review 端点由 `app.api.routers.tasks` 单一路由注册 | 是 |
| TC-AIBRAIN-GRAPH-FUNC-002 | 信息不足时中断并补充后恢复 | P0 | MVP | 模型返回信息不足判断 | 1. 启动任务 2. 触发 waiting_more_info 3. 提交 answers 4. 再次 start | 任务回到 draft 后再次启动，继续运行到下一节点 | 是 |
| TC-AIBRAIN-GRAPH-API-002B | 人工确认和 Graph 运行态 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在 draft AI 任务 | 1. 启动任务进入 waiting_review 2. 查询 `human_reviews`、`graph_runs`、`graph_checkpoints` 表 3. 审批 Review 4. 重启 API 后查询任务详情、pending reviews、review detail 和 graph runs | Review 内容、版本、状态、Graph Run 状态、`runtime=langgraph`、`node_path`、checkpoint 和 state_snapshot 写入结构表；审批后 Review 与 Graph Run 状态同步更新；API 重启后任务详情、待确认列表、确认详情和 Graph Run 列表均能从 task workflow repository source rows 恢复，不依赖进程内运行态集合；Review 和 Graph Run 读取/决策端点由 `app.api.routers.tasks` 单一路由注册 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-003 | MVP 产品详细设计、技术方案和 Git Review 人工确认门禁 | P0 | MVP | 任务运行到产品详细设计、技术方案或 code_review 报告确认点 | 1. 查询 pending review 2. 不确认并观察后续阶段 3. approve 4. 查询任务 | 未确认前不进入下一阶段或归档，确认后恢复 graph | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004A | MVP-A Markdown 导出 | P0 | MVP-A | 产品详细设计或技术方案已确认 | 1. GET Markdown 导出接口 2. 检查内容 3. 使用无任务读权限角色重试 | 返回 `text/markdown` 方案内容，并可关联 trace_id；无任务读权限角色返回 403 | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004B | MVP-C 模拟 Issue 幂等生成 | P0 | MVP-C | 任务已确认并进入输出阶段 | 1. GET 查询未写回状态 2. POST 显式生成回写 3. 重复 POST 4. GET 查询结果 | 生成 mock issues，重复触发不产生重复结果，GET 不产生写副作用 | 是 |
| TC-AIBRAIN-OUTPUT-API-004D | 模拟 Issue 回写 PostgreSQL 结构表持久化 | P1 | MVP-C | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在已完成 AI 任务 | 1. POST `/api/writeback/results/{task_id}` 生成模拟 Issue 2. 查询 PostgreSQL `mock_issues` 表 3. 重启 API 后 GET 同一任务回写结果 4. 查询生命周期上下文 | `mock_issues` 保存 source_task_id、title、status、idempotency_key 和 payload；生成接口在 handler 返回前写入 `mock_issues` 和 `mock_issue.written` 审计事件，不依赖请求结束 persist；API 重启后仍能按幂等键恢复结果、`mock_issue` 计数器和生命周期关系，旧快照中引用缺失任务的回写不会重新入结构表 | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004C | MVP-C 知识沉淀候选审核 | P0 | MVP-C | 任务已产生可沉淀内容 | 1. 查询知识候选 2. 批准或拒绝 | 返回 pending deposits，审核后状态正确流转 | 是 |
| TC-AIBRAIN-KNOWLEDGE-FUNC-005 | 知识检索权限过滤和来源引用 | P0 | MVP | 存在不同权限文档 | 1. 以用户 A 检索 2. 以用户 B 检索 | 仅返回有权限文档，结果包含来源字段 | 是 |
| TC-AIBRAIN-AUDIT-API-006 | 写操作和 AI 关键动作产生审计事件 | P1 | MVP | 已执行任务闭环 | 1. 查询 audit events 2. 按 ai_task_id 过滤 | 创建、启动、确认、回写均有审计记录 | 是 |
| TC-AIBRAIN-DEPLOY-FUNC-007 | Docker Compose 本地栈健康检查 | P1 | 生产就绪 | Docker 可用 | 1. 启动 compose 2. 请求 /health 3. 检查 postgres/redis | web/api/db/redis 服务正常，生产就绪门禁可验证 | 脚本已提供；目标环境待通过 |
| TC-AIBRAIN-DEPLOY-FUNC-007B | 非测试环境禁用 MemoryStore 运行时 | P1 | MVP | 未设置 `PERSISTENCE_MODE` 或显式配置持久化模式 | 1. 清空 `PERSISTENCE_MODE` 初始化 Settings 2. 以 `APP_ENV=local`、`PERSISTENCE_MODE=memory` 构建后端 store 3. 以 `APP_ENV=test`、`PERSISTENCE_MODE=memory` 运行单测 | 默认持久化模式为 `postgres`；非测试环境 memory 启动 fail fast；测试环境 memory 仅作为 helper 可用 | 是 |
| TC-AIBRAIN-DEPLOY-FUNC-007C | DB-first 迁移模式健康检查 | P1 | 生产就绪 | API 以 `PERSISTENCE_MODE=postgres` 启动 | 1. 构建后端 store 2. 请求 `/health` 3. 检查 `data_access_mode` 4. 切换测试环境 memory helper 运行单测 5. 查询 `/api/brain-apps` 6. 构造任务工作流 repository source context | PostgreSQL 启动返回 `PostgresRuntimeStore` repository 容器，不返回 `PersistentMemoryStore` 或预加载业务集合；PostgreSQL 运行时返回 `data_access_mode=db_first_migration`；生产读路径不再通过 `PersistentMemoryStore.from_repository(...)` 反灌 repository read snapshot；业务大脑只读接口从 repository 读取 `brain_apps`；任务工作流 repository source context 不继承 `MemoryStore`，但保留 `new_id/snapshot/audit` 能力；测试 memory helper 返回 `memory_test_helper`；`/health` 由 `app.api.routers.platform` 单一路由注册；`main.py` 不再承载业务 helper 或 repository source-store 组装。回归见 `apps/api/tests/test_foundation.py::test_repository_read_model_store_does_not_restore_snapshot_payload`、`apps/api/tests/test_foundation.py::test_repository_source_context_is_not_memory_store`、`apps/api/tests/test_foundation.py::test_brain_apps_read_from_repository_under_postgres_runtime` 和 `apps/api/tests/test_router_boundaries.py::test_platform_status_endpoints_are_owned_by_platform_router` | 是 |
| TC-AIBRAIN-CONFIG-API-008 | 产品、迭代版本、模块和 Git 资源配置 | P1 | MVP | admin 已登录 | 1. 进入产品管理配置弹窗和需求交付/迭代版本页面 2. 创建/更新配置 3. 查询 active_only 列表 | 配置可维护，任务可引用产品迭代版本上下文；`GET/POST /api/products` 与 `GET/PATCH/DELETE /api/products/{product_id}` 由独立 `app.api.routers.products` 注册且不得重复挂载；`GET /api/product-versions`、`GET/POST /api/products/{product_id}/versions`、`POST /api/product-versions/{version_id}/advance-status` 和 `PATCH/DELETE /api/product-versions/{version_id}` 由独立 `app.api.routers.product_versions` 注册且不得重复挂载；`GET/POST /api/products/{product_id}/modules` 和 `PATCH/DELETE /api/product-modules/{module_id}` 由独立 `app.api.routers.product_modules` 注册且不得重复挂载；`GET/POST /api/products/{product_id}/git-repositories` 和 `PATCH/DELETE /api/product-git-repositories/{repo_id}` 由独立 `app.api.routers.product_git_repositories` 注册且不得重复挂载；`GET/POST /api/system/related-systems` 和 `PATCH/DELETE /api/system/related-systems/{system_id}` 由独立 `app.api.routers.related_systems` 注册且不得重复挂载；Git 凭据不在页面或 API 响应中明文展示 | 是 |
| TC-AIBRAIN-CONFIG-API-008B | 产品配置 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动 | 1. 创建产品、版本、模块、Git 资源和相关系统 2. 禁用请求结束 `persist()` 或重启 API 3. 重新查询产品配置接口和 PostgreSQL 对应结构表 | `products`、`product_versions`、`product_modules`、`product_git_repositories`、`related_systems` 有对应记录；产品主体 CRUD API 由 `app.api.routers.products` 提供，迭代版本 API 由 `app.api.routers.product_versions` 提供，产品模块 API 由 `app.api.routers.product_modules` 提供，产品 Git 仓库 API 由 `app.api.routers.product_git_repositories` 提供，相关系统 API 由 `app.api.routers.related_systems` 提供；产品配置写接口在 handler 返回前写入 repository，不依赖全局 `PersistentMemoryStore.persist()`；产品配置核心 GET 接口 repository-first 读取，运行态 store 过期时仍返回结构表数据；API 重启后仍能从结构表恢复产品配置和 `system` 计数器。DB-first 读写回归见 `apps/api/tests/test_database_persistence.py::test_product_config_routes_write_repository_without_request_persist`、`apps/api/tests/test_database_persistence.py::test_product_config_get_routes_use_repository_when_runtime_store_is_stale`、`apps/api/tests/test_database_persistence.py::test_product_version_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_router_boundaries.py::test_product_core_endpoints_are_owned_by_products_router`、`apps/api/tests/test_router_boundaries.py::test_product_version_endpoints_are_owned_by_product_versions_router`、`apps/api/tests/test_router_boundaries.py::test_product_module_endpoints_are_owned_by_product_modules_router`、`apps/api/tests/test_router_boundaries.py::test_product_git_repository_endpoints_are_owned_by_product_git_repositories_router` 和 `apps/api/tests/test_router_boundaries.py::test_related_system_endpoints_are_owned_by_related_systems_router` | 是 |
| TC-AIBRAIN-CONFIG-API-008C | 产品版本批量聚合查询 | P1 | MVP | 已存在启用产品和 planning/active/testing/released/archived 迭代版本 | 1. 调用 `GET /api/product-versions` 2. 调用 `GET /api/product-versions?active_only=true` 3. 打开产品管理和迭代版本页面 | 批量接口返回版本及 `product_code`/`product_name`；active_only 只返回 active 版本；PostgreSQL 运行时通过 SQL read model 完成筛选、排序、分页和 `query/performance` 观测；前端不再按产品逐个调用版本列表来拼装页面；路由归属由 `apps/api/tests/test_router_boundaries.py::test_product_version_endpoints_are_owned_by_product_versions_router` 覆盖 | 是 |
| TC-AIBRAIN-CONFIG-FUNC-008D | 迭代版本状态推进和需求状态同步 | P0 | MVP | 用户已登录，存在 planning/active/testing 迭代版本和不同交付状态需求 | 1. 在迭代版本页点击“推进状态” 2. 生成影响预览 3. 确认推进到开发中、测试中或已发布 4. 查询需求和审计 | 规划中到开发中同步 `approved/planned -> ready_for_dev`；开发中到测试中同步 `approved/planned/ready_for_dev/designing/developing/code_reviewing -> testing`；测试中到已发布同步 `testing/ready_for_release -> released` 且阻止未完成需求发布；普通 PATCH 不能直接改状态；状态推进 API 由 `app.api.routers.product_versions` 提供，并通过 `apps/api/tests/test_iteration_version_status_flow.py` 回归 | 是 |
| TC-AIBRAIN-CONFIG-API-009 | 平台模型网关配置 | P1 | MVP | admin 已登录 | 1. 进入系统管理/模型网关 2. 创建默认模型配置 3. 查询列表 | 页面和 API 只返回 `api_key_configured`，不泄露明文 API Key | 是 |
| TC-AIBRAIN-CONFIG-API-009B | 模型网关 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动 | 1. 创建默认 OpenAI-compatible 模型网关配置 2. 启动 AI 任务产生模型调用日志 3. 查询 PostgreSQL `model_gateway_configs` 和 `model_gateway_logs` 表 4. 重启 API 后查询模型网关列表和模型日志 | 配置、默认标记、密钥配置状态、模型、超时、重试和调用元数据写入结构表；API 响应不泄露 API Key；模型网关配置创建/修改/删除在 `PostgresRuntimeStore` 空启动容器下仍从 repository 恢复当前配置和日志上下文；模型网关配置列表和模型日志列表 repository-first 读取，运行态 store 过期时仍能返回配置、脱敏状态和按 purpose/status/task 过滤后的模型日志；API 重启后仍能恢复默认配置、日志列表和 `model_gateway_config`/`model_log` 计数器。DB-first 回归见 `apps/api/tests/test_database_persistence.py::test_model_gateway_config_api_writes_fine_grained_repository_payload`、`apps/api/tests/test_database_persistence.py::test_model_gateway_config_list_uses_repository_when_runtime_store_is_stale` 和 `apps/api/tests/test_database_persistence.py::test_model_gateway_log_list_uses_repository_when_runtime_store_is_stale` | 是 |
| TC-AIBRAIN-ASSISTANT-FUNC-027 | AI 助手系统问答 | P1 | MVP | 已配置 active/default Chat 模型网关，系统存在产品、需求、迭代版本、AI 任务、Review、Bug、代码评审或 Git 配置 | 1. 进入 AI 助手 2. 询问 AI Brain 项目进展 3. 询问阻塞与待确认 4. 查询模型调用日志 | 助手基于服务端系统上下文回答产品、迭代进度、任务、阻塞需求、待确认 Review、代码评审结论、Bug 分布、知识沉淀、Git 仓库和模型网关状态；`/api/assistant/*` 由独立 `app.api.routers.assistant` 提供，聊天工作流由 `app.services.assistant_chat` 统一处理会话续写、用户级历史隔离、模型日志、审计和错误边界，日志仅记录 `purpose=assistant_chat` 元数据，不保存完整问题或回答 | 是 |
| TC-AIBRAIN-FLOW-FUNC-010 | MVP 业务主体独立入口和真实空状态可用 | P0 | MVP | 用户已登录且具备相应角色，至少存在产品、需求、AI 任务和知识文档基础数据 | 1. 进入首页 IT 团队看板 2. 进入产品管理 3. 进入需求管理 4. 进入任务中心 5. 进入 Bug 管理 6. 进入研发运营看板 7. 进入用户洞察 8. 进入知识中心 9. 进入审计与运行 | MVP 必交主体可独立查看或维护；未接入真实采集器的入口展示空状态或禁用态，不返回示例数据、占位统计或伪造结果 | 是 |
| TC-AIBRAIN-FLOW-FUNC-010B | 提交前真实网页界面验证门禁 | P0 | MVP | 存在前端、页面可见文案、路由、服务映射或影响页面展示的后端改动 | 1. 启动/重启真实 Web 服务 2. 打开目标页面并登录实际角色 3. 验证页面标题、菜单、关键内容或目标交互 4. 检查无空白页、无框架错误覆盖层和无本次变更引入的控制台错误 5. 记录 URL、角色、验证项和结果后再提交 | 自动化测试通过之外，实际网页界面验证也必须通过；若发现旧 bundle、旧端口、缓存错误或页面未渲染，必须修复运行环境并复测，未通过不得提交代码 | 手动/浏览器自动化门禁 |
| TC-AIBRAIN-FLOW-API-010C | 管理主列表服务端分页、排序和筛选 | P0 | MVP | 已存在产品、需求、迭代版本、Bug、任务、知识、审计、研发运营指标和用户洞察数据 | 1. 分别调用管理主列表接口携带 `page/page_size/sort_by/sort_order` 和业务筛选条件 2. 打开对应前端页面查询和切换分页/排序 3. 检查网络请求 | 产品、需求、迭代版本、Bug、任务、知识、审计、研发运营和用户洞察主列表均由后端返回分页结果；用户洞察调用 `/api/insights/items`，研发运营调用 `/api/devops/operational-metrics`，前端不再拉全量或多接口拼装主表；首页团队看板属于汇总视图，不纳入“必须 SQL/物化 read model”的管理主列表验收范围 | 是 |
| TC-AIBRAIN-REQ-FUNC-011 | 需求审批与任务执行解耦 | P0 | MVP | 存在已批准需求 | 1. 生成 AI 任务 2. 修改产品配置 3. 查询任务详情 | 需求保留审批状态，任务保留生成时 requirement_snapshot 和 product_context | 是 |
| TC-AIBRAIN-REQ-API-011B | 需求台账 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动且存在产品，可选存在迭代版本 | 1. 创建未排期需求 2. 审批、驳回、排期、关闭或删除需求 3. 从已排期需求生成产品详细设计任务 4. 禁用请求结束 `persist()` 或重启 API 5. 查询 PostgreSQL `requirements` 表并重新查询需求列表和详情 | 需求标题、内容、产品、可选版本、状态、审批备注、删除结果和生成任务后的 `task_ids` 回写写入 `requirements`；相关 handler 在返回前写入 repository，不依赖全局 `PersistentMemoryStore.persist()`；需求列表和详情在 PostgreSQL 运行时读取 task workflow repository source rows，运行态 store 过期时仍能返回结构表需求；需求交付端点由 `app.api.routers.requirements` 单一路由注册 | 是 |
| TC-AIBRAIN-REQ-API-011D | 需求列表产品/迭代版本聚合字段 | P1 | MVP | 已存在产品、迭代版本和需求 | 1. 调用 `GET /api/requirements` 2. 按产品、状态或迭代版本过滤 3. 打开需求管理页面 | 列表响应直接返回 `product_code`、`product_name`、`version_code`、`version_name` 和 `created_at`；前端不再额外拉产品和版本列表翻译展示字段；需求管理查询区可按版本名、版本编码或“未排期”过滤需求列表；需求列表展示“创建时间”列且不再展示“更新时间”列 | 是 |
| TC-AIBRAIN-REQ-FUNC-011C | 新增需求可不指定迭代版本并后续排期 | P0 | MVP | 用户已登录，存在启用产品和 planning/active 迭代版本 | 1. 新增需求不选择版本 2. 审批需求 3. 未排期时生成任务 4. 补充迭代版本 5. 再生成任务 | 新需求为 `submitted`，审批后未排期为 `approved`，未排期生成任务返回状态错误；补充 planning/active 版本后为 `planned` 并可生成产品详细设计任务，需求进入 `designing` | 是 |
| TC-AIBRAIN-REQ-FUNC-011E | 多需求批量排期和迭代版本归集 | P0 | MVP | 用户已登录，存在启用产品、planning/active/testing/released/archived 迭代版本、需求池需求和已排期需求 | 1. 在需求管理勾选多条同产品需求并批量排期 2. 在迭代版本页打开归集需求弹窗并勾选需求 3. 调用批量接口混入待评审/跨产品需求 4. 查询审计 | 合法 `approved/planned` 需求更新为 planning/active 目标版本并进入 `planned`；需求页仅可选择 planning/active 并过滤 testing/released/archived；待评审、跨产品或已进入交付阶段需求返回 skipped；页面只对可排期状态开放选择；结果弹窗展示批次号、成功数、跳过数和 skipped 原因；审计包含追加保存的 `requirement.batch_scheduled` 和每条 `requirement.updated` | 是 |
| TC-AIBRAIN-REQ-FUNC-011F | 多需求批量生成任务 | P0 | MVP | 用户已登录，存在启用产品、同产品已排期需求和需求池/跨产品需求 | 1. 在需求管理勾选同产品已排期需求并点击批量生成任务 2. 输入生成原因并确认 3. 调用批量接口混入需求池、跨产品和重复需求 4. 查询需求、任务和审计 | 合法 `planned` 需求各生成一个 draft 产品详细设计任务并进入 `designing`；需求 `task_ids` 追加任务 ID；需求池、跨产品或重复需求返回 skipped；审计包含 `requirement.batch_tasks_generated` 和每个任务的 `ai_task.created`，payload 带 batch_id 与 reason | 是 |
| TC-AIBRAIN-REQ-FUNC-011G | 多需求批量分配负责人 | P1 | MVP | 用户已登录，存在可分配需求、已关闭需求和重复/不存在 ID | 1. 在需求管理勾选多条非关闭需求并点击批量分配负责人 2. 输入负责人和原因 3. 调用批量接口混入关闭、重复和不存在需求 4. 查询需求和审计 | 合法需求 `assignee` 更新且状态不变化；关闭、取消、重复或不存在需求返回 skipped；审计包含 `requirement.batch_owner_assigned` 和逐条 `requirement.updated`，payload 带 batch_id、from_assignee、assignee 和 reason | 是 |
| TC-AIBRAIN-REQ-FUNC-011H | 多需求批量推进状态 | P1 | MVP | 用户已登录，存在已归属迭代且可推进需求、未排期需求、终态需求和重复/不存在 ID | 1. 在需求管理勾选多条需求并点击批量推进状态 2. 选择目标状态并输入原因 3. 调用批量接口混入未排期、终态、重复和不存在需求 4. 查询需求和审计 | 已归属迭代且合法的需求按研发流程更新状态；未排期需求返回 `REQUIREMENT_VERSION_REQUIRED`，不符合路径/终态、重复或不存在需求返回 skipped；结果弹窗展示批次号、成功数、跳过数和 skipped 原因；审计包含 `requirement.batch_status_advanced` 和逐条 `requirement.updated`，payload 带 batch_id、from_status、to_status 和 reason | 是 |
| TC-AIBRAIN-KNOWLEDGE-FUNC-012 | 知识中心独立运营 | P0 | MVP | 知识维护者已登录 | 1. 导入文档 2. 查看索引状态 3. 检索 4. 审核沉淀 | 知识中心可独立导入、索引、检索、审核和处理失败 | 是 |
| TC-AIBRAIN-AUDIT-API-013 | 主体级审计查询 | P1 | MVP | 已产生产品、需求、任务、知识操作 | 1. 按 subject_type 查询 2. 按 subject_id 查询 3. 按 actor_id 和 created_from/created_to 查询 4. 在审计列表打开详情和链路追踪 | 返回对应主体、操作者和时间范围内的关键写操作；页面弹窗展示审计载荷和生命周期上下文 | 是 |
| TC-AIBRAIN-KNOWLEDGE-API-013B | 知识与审计 PostgreSQL 结构表持久化 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在知识维护者和至少一个可沉淀任务 | 1. 创建/更新/删除知识文档 2. 审核知识沉淀候选 3. 查询 PostgreSQL `knowledge_documents`、`knowledge_deposits`、`audit_events` 表 4. 重启 API 后重新查询知识中心和审计列表 | 知识文档、权限角色、标签、索引状态、chunk、沉淀状态、关联入库文档、驳回原因、索引模型日志和审计事件写入结构表；知识文档和知识沉淀写路径在 `PostgresRuntimeStore` 空启动容器下通过 knowledge source rows 恢复产品、知识文档、chunk、沉淀和模型网关上下文，采纳与驳回均不依赖全局运行时知识沉淀集合；知识文档列表 repository-first 读取，权限、关键字、文档类型和索引状态过滤在查询层执行，运行态 store 过期时仍返回结构表数据和 `chunk_count`；知识检索候选 chunk repository-first 读取，文档权限、chunk 权限、可检索状态和关键词过滤在查询层执行，运行态 store 过期时仍返回结构表检索结果；知识沉淀候选列表 repository-first 读取，状态过滤在查询层执行，运行态 store 过期时仍返回结构表沉淀数据；知识沉淀 approve/reject 写接口优先从 repository 读取当前沉淀记录，运行态 store 过期时仍能完成审核并写回结构表与审计事件；`audit_events.id` 支持字符串 ID，`sequence` 可恢复审计计数器；API 重启后知识和审计不依赖快照兜底数据。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_knowledge_routes_write_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_knowledge_document_list_uses_repository_when_runtime_store_is_stale`、`apps/api/tests/test_database_persistence.py::test_knowledge_deposit_list_uses_repository_when_runtime_store_is_stale` 和 `apps/api/tests/test_database_persistence.py::test_knowledge_search_uses_repository_when_runtime_store_is_stale` | 是 |
| TC-AIBRAIN-ASSISTANT-API-030 | AI 助手会话 PostgreSQL 结构表持久化 | P1 | MVP | 模型网关 Chat 可用，用户已登录 | 1. 发送助手消息 2. 查询本人会话和消息 3. 触发一次模型调用失败 4. 重启 API 后重新查询会话、消息和模型日志 | 助手会话、用户消息、助手消息、成功/失败模型日志和审计事件写入结构表；聊天写路径在 `PostgresRuntimeStore` 空启动容器下通过 assistant source rows 恢复当前用户会话、消息、产品任务摘要和模型网关上下文；历史只返回当前用户会话，列表和消息 repository-first 读取并按 `user_id` 在查询层隔离，运行态 store 过期时仍可恢复本人历史。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_assistant_chat_writes_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_assistant_history_uses_repository_when_runtime_store_is_stale`，结构化会话/消息持久化和恢复计数器回归见 `apps/api/tests/test_assistant_chat_persistence.py` | 是 |
| TC-AIBRAIN-GIT-API-031 | GitLab/GitHub 快照 PostgreSQL 结构表持久化 | P1 | MVP-B | 产品已配置 GitLab/GitHub 代码仓库，存在已确认技术方案 | 1. 创建 MR/PR diff 快照 2. 用相同 diff 再次创建并复用 3. 提交超限 diff 触发失败审计 4. 查询 GitHub PR 列表和 MR/PR 预览 5. 重启 API 后重新查询快照和审计 | 快照成功、复用审计和失败审计在 handler 返回前写入结构表；GitHub PR 列表、GitLab MR 预览和 GitHub PR 预览审计在 handler 返回前写入 repository；Git Review API 入口由 `app.api.routers.git_review` 单一路由注册；相关写路径在 `PostgresRuntimeStore` 空启动容器下通过 product/task workflow source rows 恢复 Git 资源、需求和技术方案任务上下文；重启后不依赖快照兜底数据。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_gitlab_snapshot_writes_repository_without_request_persist` 和 `apps/api/tests/test_database_persistence.py::test_github_list_and_preview_audits_write_repository_without_request_persist` | 是 |
| TC-AIBRAIN-KNOWLEDGE-API-013C | GBrain 长期记忆连接器状态 | P1 | MVP-C | 用户已登录 | 1. 未配置 `GBRAIN_BASE_URL` / `GBRAIN_API_KEY` 时查询 `/api/long-memory/status` 2. 配置两项后重启 API 并再次查询 | 未配置时返回 `status=not_configured`、`fallback_retriever=postgres_pgvector` 和空能力列表；配置后返回 `configured` 和能力列表；响应不包含 GBrain URL、API Key 或密钥片段；`/api/long-memory/status` 由 `app.api.routers.platform` 单一路由注册 | 是 |
| TC-AIBRAIN-AUTH-API-024 | MVP 角色目录和用户管理角色选择 | P1 | MVP | admin 已登录 | 1. 调用 `/api/auth/roles` 2. 进入系统管理/角色管理查看列表和详情 3. 进入系统管理/用户管理并打开角色目录 4. 新增用户时打开角色字段 5. 进入知识中心导入文档并打开权限角色字段 6. 尝试提交未定义角色 | 接口返回 6 个明确角色、业务角色映射、职责、数据范围、决策范围、可见入口、限制边界、权限点和排序；`/api/auth/login`、`/api/auth/me`、`/api/auth/logout` 和 `/api/auth/roles` 只能由独立 `app.api.routers.auth` 注册且不得重复挂载；`GET/POST /api/users` 与 `PATCH/DELETE /api/users/{user_id}` 只能由独立 `app.api.routers.users` 注册且不得重复挂载；角色管理列表展示角色、业务角色、职责与范围摘要、可见入口、权限数量和状态，不在列表铺开长职责/数据范围文本，详情弹窗展示完整定位、职责、数据范围、决策范围、限制边界和权限点；用户管理和知识权限配置均从接口加载固定多选；后端拒绝目录外角色并返回 `VALIDATION_ERROR`；`role_definitions` 迁移脚本可重复执行 | 是 |
| TC-AIBRAIN-DEVOPS-FUNC-014 | GitLab 代码质量与提交统计 | P1 | v1.2 | 产品已绑定 GitLab Git 资源 | 1. 采集每日提交 2. 采集代码质量 3. 按产品和人员查询 | 返回按产品、仓库、人员聚合的提交情况和质量结果；记录和审计在 handler 返回前写入结构表；写路径在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品和仓库；列表 repository-first 读取并在查询层应用产品、仓库和日期过滤。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_operational_routes_write_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_operational_lists_use_repository_when_runtime_store_is_stale` | 是 |
| TC-AIBRAIN-OPS-FUNC-015 | 线上运行日志运营分析 | P1 | v1.1 / v1.2 | 产品和模块已存在；可手工导入真实聚合指标 | 1. 登记线上日志指标 2. 按产品、模块、环境、时间窗口查询 3. 校验错误率和审计 | 返回按产品、模块、环境、时间窗口的运营状态指标；记录和审计在 handler 返回前写入结构表；写路径在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品和模块；列表 repository-first 读取并在查询层应用产品、模块、环境和时间范围过滤。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_operational_routes_write_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_operational_lists_use_repository_when_runtime_store_is_stale` | 是 |
| TC-AIBRAIN-RELEASE-FUNC-016 | Jenkins 发布数据登记与查询 | P1 | v1.1 / v1.2 | 产品和版本已存在 | 1. 登记发布记录 2. 查询产品发布历史 | 返回构建状态、部署环境、失败原因；记录和审计在 handler 返回前写入结构表；写路径在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品和版本；列表 repository-first 读取并在查询层应用产品、版本、状态和环境过滤。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_operational_routes_write_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_operational_lists_use_repository_when_runtime_store_is_stale` | 是 |
| TC-AIBRAIN-DEVOPS-FUNC-023 | 采集运行记录登记与更新 | P1 | v1.2 | 产品已存在；需要追踪 DevOps 或用户洞察采集尝试 | 1. 查询空运行列表 2. 登记运行 3. 标记成功/失败/取消 4. 检查审计和持久化 5. 在研发运营页面登记和结束运行 | 返回真实运行台账；终态不可回退；failed 必须有错误说明；不自动生成指标数据；创建、更新和审计在 handler 返回前写入结构表；写路径在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品和当前运行记录；列表 repository-first 读取并在查询层应用采集类型、产品、状态和来源系统过滤。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_operational_routes_write_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_operational_lists_use_repository_when_runtime_store_is_stale` | 是 |
| TC-AIBRAIN-ATTRIBUTION-FUNC-024 | 待归属数据队列登记与处理 | P1 | v1.2 | 产品已存在；存在无法映射产品/模块/需求的采集或导入样本 | 1. 查询空队列 2. 登记待归属项 3. 归属到产品上下文 4. 忽略噪声 5. 检查审计和持久化 6. 在 DevOps/Insights 页面查看和处理 | 返回真实队列；pending/resolved/ignored 状态正确；终态不可重复处理；不自动生成指标或反馈数据；创建、处理和审计在 handler 返回前写入结构表；写路径在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验建议/归属产品、模块、需求和采集运行；列表 repository-first 读取并在查询层应用来源类型、状态、归属产品和采集运行过滤。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_operational_routes_write_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_operational_lists_use_repository_when_runtime_store_is_stale` | 是 |
| TC-AIBRAIN-DASHBOARD-FUNC-017 | 首页 IT 团队看板 MVP 聚合与 v1.2 完整下钻 | P1 | MVP / v1.2 | MVP 至少存在产品、需求、AI 任务、知识和审计数据；v1.2 另存在 Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议数据 | 1. 打开首页 2. 按产品筛选 3. 下钻明细 4. 检查运行态 store 过期场景 5. 检查缓存命中和强制刷新 | MVP 展示真实需求、研发进展、知识沉淀和审计摘要；v1.2 扩展 Bug、线上系统健康、核心业务运行、用户使用趋势、用户反馈趋势、AI 迭代规划建议摘要和发布状态；PostgreSQL 运行时看板从 repository source rows 读取真实数据，可由 Python 做跨主体聚合和展示计算；必须按任务读权限、产品归属和时间窗口过滤；生成的看板快照在 handler 返回前写入结构表；看板聚合容器不得作为写入事实源，也不强制沉淀为 SQL/物化 read model；短 TTL 缓存必须只作为 PostgreSQL source rows 派生的只读性能优化，并通过 `metadata.dashboard_cache` 和 `refresh=true` 可观测、可绕过 | 是 |
| TC-AIBRAIN-BUG-FUNC-018 | v1.1 Bug 管理基础闭环 | P1 | v1.1 | 存在 AI 自动测试和人工测试输入 | 1. AI 自动测试登记 Bug 2. 人工登记 Bug 并选择测试中目标版本 3. 分派修复 4. 验证关闭 5. 在 Bug 管理按迭代版本查询 6. 多选 Bug 批量处理 | Bug 按产品和版本归属，登记时可选择同产品未归档版本并过滤 archived；列表展示迭代版本；来源正确，状态完整流转；重复 Bug 不进入开放队列；批量处理返回 updated/skipped 明细并记录批次审计；写操作产生审计事件；`GET/POST /api/bugs`、`POST /api/bugs/batch-update` 和 `PATCH/DELETE /api/bugs/{bug_id}` 由 `app.api.routers.bugs` 单一路由注册 | 是 |
| TC-AIBRAIN-BUG-API-018B | Bug 管理 PostgreSQL 结构表持久化 | P1 | v1.1 | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，存在产品、版本和模块 | 1. 创建 Bug 2. 修改状态、负责人、复现步骤和证据 3. 合并重复 Bug 4. 删除 Bug 5. 查询 PostgreSQL `bugs` 表 6. 重启 API 后重新查询 Bug 列表 7. 按 `version_id` 查询 Bug 列表 | `bugs` 保存产品、版本、模块、来源、严重级别、状态、负责人、关联任务/需求、复现步骤、证据和重复归并关系；Bug 创建、修改、删除和审计事件在 handler 返回前写入结构表，删除前清空指向被删 Bug 的重复引用；Bug 列表 repository-first 读取，产品、版本、状态、严重级别和来源过滤在查询层执行，并返回 `version_code`、`version_name`；API 重启后仍能从结构表恢复 Bug 列表和 `bug` 计数器；API 入口由独立 bugs router 承载。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_bug_api_writes_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_bug_list_uses_repository_when_runtime_store_is_stale`，router 边界见 `apps/api/tests/test_router_boundaries.py::test_bug_management_endpoints_are_owned_by_bugs_router` | 是 |
| TC-AIBRAIN-TASK-FUNC-020 | 研发全链路 AI 任务类型覆盖 | P1 | v1.1 / v1.2 | 已存在产品、已排期需求、已确认产品详细设计、已确认技术方案、已确认发布评估、代码 diff、测试结果、Jenkins 发布记录和线上日志样本 | 1. 创建当前已实现 task_type 任务 2. 启动并查询详情 3. 检查输出结构和 input_json 真实上下文快照 | 每类任务均保留 task_type、产品上下文、人工确认点和对应输出结构；自动化覆盖 development_planning、automated_testing、release_readiness 与 post_release_analysis | 是 |
| TC-AIBRAIN-TASK-API-020B | 任务列表 SQL 聚合与详情读取 | P1 | MVP | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动且存在 AI 任务 | 1. 调用 `GET /api/ai-tasks?product_id=...&created_from=...&created_to=...` 2. 检查响应产品名 3. 用无权角色查询 code_review/非 code_review 任务 4. 启动任务并调用 `GET /api/ai-tasks/{task_id}` | PostgreSQL 模式通过 SQL join 返回 `product_name` 并应用状态、类型、产品、需求和时间过滤；权限过滤仍阻止聚合接口泄露无权任务；任务详情通过 task workflow source rows 返回脱敏产品上下文、input/output、pending_review、reviews、graph_runs、knowledge_deposits 和 mock_issues；任务列表与详情端点由 `app.api.routers.tasks` 单一路由注册，详情 handler 不得回调 legacy main，回归见 `apps/api/tests/test_router_boundaries.py::test_ai_task_detail_handler_does_not_call_legacy_main` 和 `apps/api/tests/test_graph_runtime.py::test_starting_task_creates_graph_run_checkpoint_and_task_detail_projection` | 是 |
| TC-AIBRAIN-REVIEW-FUNC-019 | v1.1 研发扩展任务人工确认门禁 | P1 | v1.1 | 开发计划或自动化测试任务运行到确认点 | 1. 查询 pending review 2. 不确认并观察后续阶段 3. approve 4. 查询任务和 Bug 列表 | 开发计划和自动化测试结论未确认前不进入下一阶段或回写；自动化测试确认后生成 `ai_auto_test` Bug | 是 |
| TC-AIBRAIN-REVIEW-FUNC-023A | MVP-A GitLab MR / GitHub PR 预览和 diff 快照 | P0 | MVP-A | 产品已绑定 GitLab 或 GitHub 代码库，存在已排期需求、已确认技术方案和可访问 MR/PR | 1. 预览 MR/PR 2. 查看权限诊断、diff 文件树、风险摘要和 Review Checklist 3. 拉取 diff 快照 4. 再次拉取相同或变化后的 diff 快照 5. 查询快照摘要 | 返回变更元信息、文件摘要、diff 文件树、风险摘要、检查清单、permission_diagnostics、snapshot_id、diff_size_bytes、diff_limit、created_at、previous_snapshot、diff_change_summary 和 snapshot_reused；任务中心创建 Code Review 后展示快照对比结果；快照不受后续远端变更静默影响 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-023B | MVP-B GitLab MR / GitHub PR Code Review 报告闭环 | P0 | MVP-B | 已存在 MVP-A MR/PR diff 快照，code-review 执行器可用 | 1. 创建 code_review 任务 2. 启动任务 3. 生成 Review 报告 4. 人工确认 5. 查询远端变更和审计 | 报告只归档到 AI Brain，不回写 GitLab/GitHub 评论、审批状态或分支变更 | 是 |
| TC-AIBRAIN-REVIEW-API-023C | GitLab MR / GitHub PR 快照和 Code Review 报告 PostgreSQL 结构表持久化 | P1 | MVP-B | Docker 本地栈以 `PERSISTENCE_MODE=postgres` 启动，已完成技术方案并存在 MR/PR 快照 | 1. 生成 MR/PR diff 快照 2. 创建并启动 code_review 任务生成报告 3. 查询 PostgreSQL `gitlab_mr_snapshots` 和 `code_review_reports` 表 4. 重启 API 后查询任务详情、生命周期上下文和报告接口 | 兼容快照和 Review 报告写入结构表；报告保留 task_id、snapshot_id、executor、risk_level、findings、review_id、归档状态和不回写标记；API 重启后能恢复 `snapshot`/`report` 计数器并回填任务 `code_review_report_id`；报告读取 router 不回调 legacy main | 是 |
| TC-AIBRAIN-REVIEW-FUNC-024 | v1.2 发布和上线后分析人工确认门禁 | P1 | v1.2 | 发布上线评估或上线后分析任务运行到确认点 | 1. 查询 pending review 2. 不确认并观察后续处理 3. approve 或 edited_approve 4. 查询结果和 `ai_post_release` Bug | 发布建议、风险处理、知识沉淀和上线后 Bug 入库必须等待人工确认 | 是 |
| TC-AIBRAIN-FLOW-FUNC-021 | 软件研发全流程感知 | P1 | MVP / v1.2 | 存在 MVP 关联数据；v1.2 完整追溯测试另需提交、Review、测试、Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议关联数据 | 1. 以需求查询 MVP 感知视图 2. 查看上下游 3. 查看风险信号 4. 从人工确认、Code Review 报告、模拟 Issue、知识沉淀和审计事件起点查询 5. 用 v1.2 数据下钻到关联主体 | MVP 至少返回需求到产品详细设计、技术方案、代码 Review、人工确认、模拟 Issue、知识沉淀和审计事件，并且从 MVP 证据主体回到对应任务链路；v1.2 返回完整上下文链路、风险来源、影响范围和下一步建议；生成的生命周期边和风险信号在 handler 返回前写入结构表 | 是 |
| TC-AIBRAIN-PLANNING-FUNC-022 | 用户洞察与 AI 迭代规划 | P1 | MVP / v1.2 | 存在产品规划、需求池、用户反馈、Bug；v1.2 另存在用户使用数据、线上日志、发布记录和研发投入样本 | 1. 聚合使用指标 2. 收集用户反馈 3. 处理用户反馈 4. 生成迭代规划建议 5. 检查未自动创建正式需求/变更路线图 6. 产品负责人确认后转需求 | MVP 基于真实用户反馈和 Bug 返回可追溯的迭代建议；AI 未经确认不自动创建正式需求或调整路线图/排期；用户使用指标、用户反馈、迭代建议、决策和转需求审计在 handler 返回前写入结构表；写路径在 `PostgresRuntimeStore` 空启动容器下通过 insight source rows 校验产品、版本、模块、反馈、Bug 和迭代建议当前记录；用户使用指标、用户反馈和迭代建议列表 repository-first 读取，运行态 store 过期时仍能返回结构表数据和筛选结果。DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_insight_planning_routes_write_repository_without_request_persist`，读路径回归见 `apps/api/tests/test_database_persistence.py::test_insight_planning_lists_use_repository_when_runtime_store_is_stale` | 是 |

---

## 业务域测试用例索引

详细测试用例已按业务域拆分维护，主文档保留版本信息、通用规范、MVP 验收切片和索引，避免单文件继续膨胀。

| 业务域 | 文档 | 覆盖范围 |
|------|------|----------|
| 核心工作流 | [test-cases/core-workflow.md](test-cases/core-workflow.md) | AI 任务、Graph 中断恢复、人工确认、Markdown/Issue/知识输出、知识检索、审计、部署门禁、产品配置、模型网关、AI 助手 |
| 需求交付与任务管理 | [test-cases/requirements-and-tasks.md](test-cases/requirements-and-tasks.md) | 主体独立入口、真实网页门禁、管理主列表、需求审批/排期/批量操作、任务批量取消/重试、迭代版本状态同步、知识中心和主体审计 |
| 研发运营、质量与用户洞察 | [test-cases/devops-quality-and-insights.md](test-cases/devops-quality-and-insights.md) | GitLab/Jenkins/线上日志、采集归属、首页看板、Bug、研发全链路任务、Review、GitHub PR、代码评审、生命周期上下文和用户洞察 |
| 支撑矩阵 | [test-cases/supporting-matrices.md](test-cases/supporting-matrices.md) | 边界、异常、API、性能测试用例和测试执行记录 |
