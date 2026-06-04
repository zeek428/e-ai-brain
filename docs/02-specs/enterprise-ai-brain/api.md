# 企业 AI 大脑平台 API 文档

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.92 |
| 适用系统版本 | ≥ v1.0.0 |
| 文档状态 | Approved |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0.0 | 2026-05-27 | 基于设计文档生成项目级 API 文档 | Claude |
| v1.0.1 | 2026-05-27 | 对齐当前 FastAPI 实现，补充产品配置和平台配置接口 | Codex |
| v1.0.2 | 2026-05-28 | 补充主体生命周期、需求任务快照、知识索引状态和主体级审计查询约定 | Claude |
| v1.0.3 | 2026-05-29 | 补充 GitLab、线上日志、Jenkins、首页看板和 Bug 管理 API 约定 | Claude |
| v1.0.4 | 2026-05-29 | 补充研发全链路 AI 任务类型和 task_type 契约 | Claude |
| v1.0.5 | 2026-05-29 | 补充软件研发全流程感知 API 约定 | Claude |
| v1.0.6 | 2026-05-29 | 补充用户洞察、用户反馈和 AI 迭代规划建议 API 约定 | Claude |
| v1.0.7 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 纳入 v1 MVP，补充 MR 预览、diff 快照、Review 报告查询和不回写 GitLab 的错误语义 | Claude |
| v1.1.0 | 2026-05-29 | 对齐 PRD v1.1.0 和 Spec v1.1.0，补充 MVP 角色映射，修正内部 GitLab Git 资源示例和阶段边界 | Claude |
| v1.1.1 | 2026-05-29 | 修复产品评审问题：将 GitLab 预览和 diff 快照前置到 MVP-A，清理 MVP 角色口径，统一 health trace_id、占位接口和阶段边界 | Claude |
| v1.1.2 | 2026-05-30 | 将 Bug 管理 GET/POST/PATCH 从占位升级为 v1.1 基础接口，补充状态流转、重复归并和审计约束 | Codex |
| v1.1.3 | 2026-05-30 | 对齐当前实现的 PostgreSQL 登录用户表、用户管理接口和 SQL 迁移驱动持久化 | Codex |
| v1.1.4 | 2026-05-30 | 补齐当前管理主体 CRUD 契约，新增产品子资源、需求、知识文档、Bug 和用户删除/更新接口说明 | Codex |
| v1.1.5 | 2026-05-31 | 对齐真实删除语义、主数据唯一性校验和需求审批/任务确认前端主链路接口使用 | Codex |
| v1.1.6 | 2026-05-31 | 补齐审计事件按操作者和创建时间范围过滤，并对齐审计列表详情与链路追踪操作 | Codex |
| v1.1.7 | 2026-05-31 | 对齐 MVP-B code_review 执行器失败错误语义，结构化报告生成失败返回专用错误码和审计事件 | Codex |
| v1.1.8 | 2026-05-31 | 补齐 GitLab MR diff 超限失败审计，记录实际大小、限制和关联上下文 | Codex |
| v1.1.9 | 2026-05-31 | 补齐 GitLab MR 变更文件数限制，超限时拒绝快照并记录审计指标 | Codex |
| v1.1.10 | 2026-05-31 | 补齐 GitLab MR 单文件 diff 行数限制，超限时拒绝快照并记录文件指标 | Codex |
| v1.1.11 | 2026-05-31 | 明确 MVP 用户角色目录、角色查询接口、用户管理角色选择和 SQL 角色字典 | Codex |
| v1.1.12 | 2026-05-31 | 将产品、版本、模块和 Git 资源同步到 PostgreSQL 结构表，推进业务主体细粒度持久化 | Codex |
| v1.1.13 | 2026-05-31 | 将需求台账同步到 PostgreSQL `requirements` 结构表，支持从结构表恢复需求和计数器 | Codex |
| v1.1.14 | 2026-05-31 | 将 AI 任务核心字段同步到 PostgreSQL `ai_tasks` 结构表，支持从结构表恢复任务和计数器 | Codex |
| v1.1.15 | 2026-05-31 | 将人工确认、Graph Run 和检查点同步到 PostgreSQL 结构表，支持任务启动后的流程状态恢复 | Codex |
| v1.1.16 | 2026-05-31 | 细化角色目录响应字段，补充职责、数据范围、决策范围和前端固定角色选择约束 | Codex |
| v1.1.17 | 2026-05-31 | 将知识文档、知识沉淀候选和审计事件同步到 PostgreSQL 结构表，减少快照兜底范围 | Codex |
| v1.1.18 | 2026-05-31 | 将 Bug 管理记录同步到 PostgreSQL `bugs` 结构表，支持从结构表恢复列表和计数器 | Codex |
| v1.1.19 | 2026-05-31 | 将模型网关配置和调用元数据日志同步到 PostgreSQL 结构表，支持任务启动后恢复默认配置和日志计数器 | Codex |
| v1.1.20 | 2026-05-31 | 明确系统管理角色管理入口，角色目录只读来自 `/api/auth/roles`，用户和知识权限不得录入未定义角色 | Codex |
| v1.1.21 | 2026-05-31 | 将 GitLab MR 快照和 Code Review 报告同步到 PostgreSQL 结构表，支持证据链恢复和任务反链回填 | Codex |
| v1.1.22 | 2026-05-31 | 将模拟 Issue 回写同步到 PostgreSQL `mock_issues` 结构表，支持幂等结果恢复 | Codex |
| v1.1.23 | 2026-05-31 | 将相关系统同步到 PostgreSQL `related_systems` 结构表，纳入产品配置恢复范围 | Codex |
| v1.1.24 | 2026-05-31 | 移除 AI 任务启动本地输出 fallback，无模型网关配置时明确失败，不再生成伪输出 | Codex |
| v1.1.25 | 2026-05-31 | 知识检索升级为权限过滤后的 chunk 级结果，并将 `knowledge_chunks` 纳入结构表持久化 | Codex |
| v1.1.26 | 2026-05-31 | 生命周期视图和首页看板聚合按任务读权限过滤，避免聚合接口泄露无权任务或 Review | Codex |
| v1.1.27 | 2026-05-31 | 明确角色业务映射、菜单范围、限制边界，并补充知识索引失败原因与重试接口 | Codex |
| v1.1.28 | 2026-06-01 | 生命周期视图支持从审计主体、Review、Code Review 报告、MR 快照、模拟 Issue 和知识沉淀精准追踪上下文 | Codex |
| v1.1.29 | 2026-06-01 | 知识检索不再为缺失 chunk 的 indexed 文档合成结果，索引不一致时返回真实空结果 | Codex |
| v1.1.30 | 2026-06-01 | GitLab MR diff 快照按 repository_id + snapshot_hash 复用已有快照，并记录复用审计事件 | Codex |
| v1.1.31 | 2026-06-01 | 低层 AI 任务创建同步回写需求任务引用，并拒绝已关闭或未审批需求继续创建任务 | Codex |
| v1.1.32 | 2026-06-01 | 模型网关配置入口拒绝非 OpenAI-compatible provider，避免无效配置延迟到任务启动才失败 | Codex |
| v1.1.33 | 2026-06-01 | 知识索引接入 OpenAI-compatible embeddings，chunk 写入 pgvector embedding，检索按权限过滤后进行向量排序 | Codex |
| v1.1.34 | 2026-06-01 | 将用户反馈从空集合入口升级为真实登记、筛选、状态更新和 PostgreSQL 结构表持久化 | Codex |
| v1.1.35 | 2026-06-01 | 将迭代规划建议升级为基于真实反馈/Bug 证据生成、确认和可选转需求的 PostgreSQL 持久化闭环 | Codex |
| v1.1.36 | 2026-06-01 | 将用户使用指标从空集合入口升级为真实登记、筛选、审计和 PostgreSQL 结构表持久化 | Codex |
| v1.1.37 | 2026-06-01 | 将 GitLab 每日代码指标从空集合入口升级为真实登记、筛选、审计和 PostgreSQL 结构表持久化 | Codex |
| v1.1.38 | 2026-06-01 | 将 Jenkins 发布记录从空集合入口升级为真实登记、筛选、审计和 PostgreSQL 结构表持久化 | Codex |
| v1.1.39 | 2026-06-01 | 将线上运行日志指标从空集合入口升级为真实登记、筛选、审计和 PostgreSQL 结构表持久化 | Codex |
| v1.1.40 | 2026-06-01 | 补齐 development_planning 和 automated_testing 低层任务创建、人工确认门禁和自动化测试 Bug 建议入库契约 | Codex |
| v1.1.41 | 2026-06-01 | 补齐 release_readiness 和 post_release_analysis 低层任务创建、真实上下文快照、人工确认和上线后 Bug 建议入库契约 | Codex |
| v1.1.42 | 2026-06-01 | 明确知识文档可绑定产品归属，首页 IT 团队看板按产品过滤知识文档和审计事件 | Codex |
| v1.1.43 | 2026-06-02 | 对齐 Bug 管理工作台完整生命周期字段，前端登记和编辑复现步骤、证据 JSON、重复归并和只读来源展示 | Codex |
| v1.1.44 | 2026-06-02 | 首页 IT 团队看板扩展 Bug、DevOps、线上日志、用户洞察和迭代规划真实聚合，并约定产品/时间范围下钻上下文 | Codex |
| v1.1.45 | 2026-06-02 | 生命周期上下文扩展真实 Bug、GitLab/Jenkins/线上日志、用户使用、用户反馈和迭代建议证据主体及风险来源契约 | Codex |
| v1.1.46 | 2026-06-02 | 新增采集运行记录 GET/POST/PATCH API、状态约束、审计事件和 `collector_runs` 结构表契约 | Codex |
| v1.1.47 | 2026-06-02 | 新增待归属数据队列查询、登记、归属/忽略 API、状态约束、审计事件和 `pending_attribution_items` 持久化契约 | Codex |
| v1.1.48 | 2026-06-02 | 明确 code_review 任务通过可插拔 `code_review_executor` 边界执行，默认适配 Claude Code `code-review` skill 命令，执行器成功/失败均写入专用审计事件 | Codex |
| v1.1.49 | 2026-06-02 | 明确相关系统可绑定产品归属并进入任务产品上下文，补齐需求详情、关闭和 Graph Run 查询接口清单 | Codex |
| v1.1.50 | 2026-06-02 | AI 任务启动接入真实 LangGraph StateGraph，Graph Run 返回 runtime、node_path 和 checkpoint runtime 元数据 | Codex |
| v1.1.51 | 2026-06-02 | 新增长期记忆 GBrain 状态接口，未配置时返回 `not_configured`，配置后只返回脱敏能力状态 | Codex |
| v1.1.52 | 2026-06-02 | 模型网关配置新增测试检测接口，使用临时 OpenAI-compatible 参数调用 chat/completions 与 embeddings 并返回脱敏结果，不保存密钥或模型日志 | Codex |
| v1.1.53 | 2026-06-02 | 模型网关测试检测新增 `test_target`，支持仅测试 Chat 以兼容 ChatGPT OAuth 类上游，同时保留 Embedding 检测和跳过状态 | Codex |
| v1.1.54 | 2026-06-02 | AI 任务列表新增创建时间范围过滤，并在摘要返回产品名、创建时间和更新时间，支撑任务管理页按所属产品和时间段查询 | Codex |
| v1.1.55 | 2026-06-02 | 所有 PostgreSQL 结构表统一补齐 `created_at` 与 `updated_at` 标准时间字段，并通过 `018_standard_timestamps.sql` 升级既有环境 | Codex |
| v1.1.56 | 2026-06-02 | 产品 Git 资源支持 `github` provider，新增 GitHub PR 预览、PR diff 快照和本地直填凭据解析契约 | Codex |
| v1.1.57 | 2026-06-02 | 新增 AI 助手聊天接口，基于当前 AI Brain 系统上下文和模型网关回答产品、任务、进展和配置问题 | Codex |
| v1.1.58 | 2026-06-03 | 全链路真实用例复跑后补齐产品详情、GitHub PR 列表、持久化模型网关健康检查和模型失败任务重试契约 | Codex |
| v1.1.59 | 2026-06-03 | 全链路 GitHub PR 复跑后补齐 code-review 外部命令缺失时自动使用模型网关适配器、Review payload 和输出规范化的启动契约 | Codex |
| v1.1.60 | 2026-06-03 | AI 助手聊天记录按用户级保存，新增会话列表、会话消息查询 API 与 `assistant_conversations` / `assistant_messages` 结构表 | Codex |
| v1.1.61 | 2026-06-03 | 知识索引支持 `text_indexed` 关键词兜底和 `vector_indexed` 向量增强，检索结果返回 `retrieval_mode` | Codex |
| v1.1.62 | 2026-06-03 | 模型网关拆分 Chat 与 Embedding 能力配置，Embedding 支持禁用、复用 Chat 或单独连接，并按向量来源元数据过滤语义检索 | Codex |
| v1.1.63 | 2026-06-03 | 需求创建允许不指定迭代版本，新增需求交付/迭代版本管理口径，并将需求接口状态更新为需求池、排期和研发交付流程 | Codex |
| v1.1.64 | 2026-06-03 | DB-first 迁移补齐任务运行态/Review/回写/导出 repository 读路径和 Mock Writeback handler 级写入契约 | Codex |
| v1.1.65 | 2026-06-03 | DB-first 迁移补齐知识沉淀候选列表 repository-first 读取和状态过滤契约 | Codex |
| v1.1.66 | 2026-06-03 | DB-first 迁移补齐知识检索 repository-first 候选查询、权限过滤和关键词下推契约 | Codex |
| v1.1.67 | 2026-06-03 | DB-first 迁移补齐知识沉淀审核写接口 repository 当前记录读取契约 | Codex |
| v1.1.68 | 2026-06-03 | DB-first 迁移补齐生命周期上下文 repository source rows 聚合和 handler 级写回契约 | Codex |
| v1.1.69 | 2026-06-03 | DB-first 迁移补齐首页 IT 团队看板 repository source rows 聚合和单条 snapshot 写入契约 | Codex |
| v1.1.70 | 2026-06-03 | DB-first 迁移补齐需求/任务详情、Graph Run、Review、回写、Code Review 报告和 Markdown 导出的 task workflow source rows 读取契约 | Codex |
| v1.1.71 | 2026-06-03 | DB-first 迁移补齐任务启动、取消、补充信息和 Review 决策写路径的 task workflow source rows 请求上下文契约 | Codex |
| v1.1.72 | 2026-06-03 | DB-first 迁移将 PostgreSQL 启动运行层切换为轻量 PostgresRuntimeStore repository 容器 | Codex |
| v1.1.73 | 2026-06-03 | DB-first 迁移补齐产品配置、需求/任务创建和 Bug 写路径在 PostgresRuntimeStore 空启动容器下的 source rows 上下文契约 | Codex |
| v1.1.74 | 2026-06-03 | DB-first 迁移补齐运营采集、用户洞察和迭代规划写路径在 PostgresRuntimeStore 空启动容器下的 source rows 上下文契约 | Codex |
| v1.1.75 | 2026-06-03 | DB-first 迁移补齐模型网关配置和 AI 助手聊天写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文契约 | Codex |
| v1.1.76 | 2026-06-03 | DB-first 迁移补齐知识文档和知识沉淀写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文契约 | Codex |
| v1.1.77 | 2026-06-03 | DB-first 迁移补齐 GitLab/GitHub PR/MR 预览、列表和快照写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文契约 | Codex |
| v1.1.78 | 2026-06-03 | DB-first 迁移移除生产 read snapshot 恢复 fallback，补齐业务大脑只读、知识沉淀驳回和 Mock Writeback 生成的 repository/source rows 契约 | Codex |
| v1.1.79 | 2026-06-03 | DB-first 迁移将生命周期上下文 source rows 从 MemoryStore 投影替换为专用 LifecycleContextReadModel | Codex |
| v1.1.80 | 2026-06-03 | DB-first 迁移明确只读缓存允许边界，并将产品配置、模型网关、助手、需求、任务创建和 Bug 写接口进一步收敛为直接 repository records/payloads | Codex |
| v1.1.81 | 2026-06-04 | 新增需求批量排期接口，支持需求管理批量排期和迭代版本页归集需求入口 | Codex |
| v1.1.82 | 2026-06-04 | 明确需求批量排期可选择未归档 planning 版本，并修正批次审计为追加保存而非覆盖式快照保存 | Codex |
| v1.1.83 | 2026-06-04 | 新增迭代版本状态推进接口，支持影响预览、需求状态同步、阻塞项和直接状态 PATCH 拦截 | Codex |
| v1.1.84 | 2026-06-04 | Bug 列表支持迭代版本过滤并返回版本编码和名称投影 | Codex |
| v1.1.85 | 2026-06-04 | 调整迭代版本推进到测试中时的需求同步规则，已进入交付链路需求统一推进到 testing | Codex |
| v1.1.86 | 2026-06-04 | 明确 Bug 管理登记弹窗目标版本使用同产品未归档版本选项，支持 testing/released 版本缺陷归属 | Codex |
| v1.1.87 | 2026-06-04 | 新增研发运营和用户洞察统一聚合列表接口，前端主列表改为服务端分页、排序和筛选 | Codex |
| v1.1.88 | 2026-06-04 | 新增需求全链路详情接口，一次返回需求、迭代版本、任务、Review、PR/MR 快照、代码评审、Bug、发布和知识沉淀时间线 | Codex |
| v1.1.89 | 2026-06-04 | 新增 Bug 批量处理接口，支持多选批量更新状态、严重级别或处理人并记录批次审计 | Codex |
| v1.1.90 | 2026-06-05 | AI 助手系统上下文新增迭代进度、待确认 Review、Bug 分布、代码评审结论和知识沉淀摘要 | Codex |
| v1.1.91 | 2026-06-05 | GitLab MR / GitHub PR 预览响应新增 diff 文件树、风险摘要和 Review Checklist，用于任务中心创建 Code Review 前确认变更范围 | Codex |
| v1.1.92 | 2026-06-05 | 需求全链路详情中的 PR/MR 快照证据展示复用风险摘要、diff 文件树和 Review Checklist 字段 | Codex |

---

## 概述

本文档定义企业 AI 大脑平台 v1 系列的 API 契约。后续版本直接维护本文档。

API 面向 React 工作台，覆盖认证、业务大脑、AI 助手、产品上下文、研发全链路 AI 任务、GitLab MR / GitHub PR 代码 Review、软件研发全流程感知、人工确认、Bug 管理、知识中心、模型网关配置、GitLab 代码质量、线上运行日志、Jenkins 发布、用户使用洞察、用户反馈、AI 迭代规划建议、首页 IT 团队看板、模拟回写、Markdown 导出和审计查询。

当前源码实现说明：MVP 骨架已实现认证、AI 助手、产品/需求/任务/Review/知识/审计/导出/GitLab MR 与 GitHub PR 只读预览、diff 快照、code_review 报告闭环。AI 助手通过模型网关 Chat 能力回答 AI Brain 系统相关问题，请求会携带脱敏系统上下文摘要，包括产品、迭代版本进度、需求、AI 任务、待确认 Review、最近代码评审结论、Bug 分布、高风险 Bug、知识沉淀、Git 仓库和模型网关配置状态；模型日志只记录 `purpose=assistant_chat` 元数据，不保存完整用户消息、系统上下文或助手回答；完整对话内容按当前登录用户写入助手会话与消息结构表，并且历史查询只返回本人会话。产品配置、需求、知识文档、Bug、用户管理、用户反馈和模型网关配置已具备当前管理页所需 CRUD 能力，删除接口会对已被需求、任务或关联资源占用的主体返回 `RESOURCE_IN_USE`；用户使用指标已具备真实登记和查询能力。MVP 明确定义 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 六个可分配角色，`GET /api/auth/roles` 返回角色目录、业务角色映射、职责、数据范围、决策范围、可见入口、限制边界、权限点和排序信息，系统管理下的角色管理页面只读展示该目录，用户管理和知识权限配置只能从该目录选择角色，不得自由创建或录入未定义角色。

产品管理页面可维护产品、模块、Git 资源和产品相关系统；需求交付下的迭代版本页面维护 `product_versions`，用于需求排期和任务版本上下文。`GET /api/product-versions` 支持批量查询版本并返回 `product_code`、`product_name` 投影，`active_only=true` 只返回 active 版本；`GET /api/requirements` 返回需求主体同时带 `product_code`、`product_name`、`version_code`、`version_name`；`POST /api/requirements/batch-schedule` 支持将多条同产品 `approved/planned` 需求批量归集到 `planning` 或 `active` 迭代版本，并返回 updated/skipped 明细；`GET /api/ai-tasks` 在 PostgreSQL 模式按产品表 SQL join 返回 `product_name`，并支持 `product_id`、`created_from`、`created_to` 等筛选。产品、版本、模块、Git 资源、相关系统、需求台账、AI 任务核心字段、人工确认、Graph Run、检查点、GitLab MR 快照、Code Review 报告、知识文档、知识 chunk、知识沉淀候选、审计事件、Bug 记录、GitLab 每日代码指标、Jenkins 发布记录、线上运行日志指标、用户反馈、用户使用指标、采集运行记录、待归属数据队列、迭代规划建议/确认、模拟 Issue 回写、模型网关配置、模型调用元数据、AI 助手会话和助手消息会同步写入 PostgreSQL 结构表 `products`、`product_versions`、`product_modules`、`product_git_repositories`、`related_systems`、`requirements`、`ai_tasks`、`human_reviews`、`graph_runs`、`graph_checkpoints`、`gitlab_mr_snapshots`、`code_review_reports`、`knowledge_documents`、`knowledge_chunks`、`knowledge_deposits`、`audit_events`、`bugs`、`gitlab_daily_code_metrics`、`jenkins_release_records`、`online_log_metrics`、`user_feedback`、`user_usage_metrics`、`collector_runs`、`pending_attribution_items`、`iteration_plan_suggestions`、`iteration_plan_decisions`、`mock_issues`、`model_gateway_configs`、`model_gateway_logs`、`assistant_conversations`、`assistant_messages`。所有 PostgreSQL 结构表必须包含 `created_at` 与 `updated_at` 标准时间字段；新增表必须在建表 SQL 中定义这两个字段，既有环境通过 `018_standard_timestamps.sql` 可重复迁移补齐。Git 资源列表只展示凭据是否已配置，不返回凭据引用或 token 明文。

知识文档创建、更新和知识沉淀采纳会同步重建文本 chunk，并在 active/default OpenAI-compatible 模型网关或环境模型网关支持 `/embeddings` 时生成 `knowledge_chunks.embedding`；Embedding 不可用时文档进入 `text_indexed`，保留 `vector_index_error`/兼容 `index_error`，关键词检索继续可用；Embedding 成功时进入 `vector_indexed`，历史 `indexed` 仅作为兼容状态读取；知识文档可选绑定 `product_id` 作为产品归属上下文，首页 IT 团队看板按产品筛选时只统计该产品归属或该产品任务沉淀产生的知识文档；基础文本索引失败才进入 `index_failed`、保留 `index_error` 并清理旧 chunk，`/api/knowledge/documents/{document_id}/retry-index` 可重建失败索引或将 `text_indexed` 补建为向量索引；`/api/knowledge/search` 先按文档和 chunk 权限过滤，再对有 embedding 的 chunk 执行向量排序并返回真实存在的 chunk 内容、`chunk_id`、`chunk_index`、`retrieval_mode`、`score` 和来源引用，没有可读向量 chunk 时不调用 query embedding 并直接走关键词检索，不返回无权限 chunk，也不为缺失 chunk 的 indexed 文档合成整篇文档结果。GitLab MR 预览和快照读取产品 Git 资源的 `remote_url` 或 `GITLAB_BASE_URL`，GitHub PR 列表、预览和快照读取 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`，并通过环境变量、服务端密钥引用或本地直填只读 token 解析凭据；MR/PR 预览响应除基础元信息外，还返回 `changed_files_summary`、`diff_file_tree`、`risk_summary` 和 `review_checklist`，任务中心创建 Code Review 前据此展示变更范围、风险摘要和人工检查项；缺少 provider 地址、仓库路径或凭据时返回明确错误，不生成本地假 MR/PR。

模型网关配置可在系统管理页面维护，列表和响应只返回 `api_key_configured`，不返回明文密钥、前缀或后缀；配置页支持“测试连接”，调用 `/api/system/model-gateway-configs/test` 使用当前表单参数临时检测 provider `/chat/completions` 与 `/embeddings`，并可通过 `test_target=chat` 仅检测 Chat，适配 ChatGPT OAuth 类不提供 Embedding 的上游；测试不保存配置或密钥，不写入 `model_gateway_logs`，响应仅包含脱敏状态、模型、延迟、embedding 维度、跳过状态和错误码。active/default 且已配置密钥的 OpenAI-compatible 配置会在非 code_review 任务启动时调用 provider `/chat/completions`；知识索引先构建文本 chunk，只有补建向量索引和存在可读向量 chunk 的查询排序会调用 provider `/embeddings`，未配置结构化默认模型网关时可使用 `MODEL_GATEWAY_BASE_URL` 与 `MODEL_GATEWAY_API_KEY` 指向的环境模型网关；调用日志只保存脱敏元数据。缺少可用模型网关、配置缺失密钥或 provider 调用失败时，非 code_review 任务进入 `failed` 并返回 `MODEL_GATEWAY_CONFIG_INVALID` 或 `MODEL_GATEWAY_FAILED`。code_review 任务必须通过可插拔 `code_review_executor` 边界生成报告，默认 `CODE_REVIEW_EXECUTOR_TYPE=claude_code_skill`、`CODE_REVIEW_EXECUTOR_NAME=code-review`，由 `CODE_REVIEW_EXECUTOR_COMMAND` 指定外部命令适配器，输入 JSON 走 stdin，输出 JSON 走 stdout；测试或兼容环境可显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 复用模型网关适配器；默认外部命令为空且存在 active/default 或环境模型网关时，启动会自动通过 `model_gateway` 适配器生成报告，prompt 携带 MR/PR 快照、技术方案、需求和产品上下文，并将常见 Review 输出字段规范化为 AI Brain 报告 schema。执行器调用成功写入 `code_review.executor_called`，执行器配置、调用、解析或结构化校验失败进入 `failed`，返回 `CODE_REVIEW_EXECUTOR_FAILED` 并写入 `code_review.executor_failed` 审计事件。任务启动不会静默生成本地输出。

任务中心已通过真实接口支持启动产品详细设计、确认 Review、基于已确认产品详细设计创建技术方案任务、基于已确认技术方案创建 `development_planning`、`automated_testing` 和 `release_readiness` 任务，基于已确认发布评估创建 `post_release_analysis` 任务，并对已完成技术方案导出 Markdown。需求创建允许 `version_id` 为空，审批后进入 `approved` 需求池；排入 `planning` 或 `active` 迭代版本后进入 `planned`，才能生成产品详细设计任务。AI 任务启动会通过真实 LangGraph `StateGraph` 运行当前 MVP 路径 `retrieve_context -> generate_task_output -> interrupt_for_human_review`，Graph Run 响应和结构表会保留 `runtime=langgraph`、`node_path` 以及 checkpoint `graph_runtime` 元数据。`automated_testing` 输出经人工确认后，可将 `bug_suggestions` 写入 `bugs`，来源为 `ai_auto_test`；`post_release_analysis` 输出经人工确认后，可将 `bug_suggestions` 写入 `bugs`，来源为 `ai_post_release`，两者均关联产品、版本、需求和 AI 任务。GitLab 每日代码指标可通过 `/api/devops/gitlab/daily-code-metrics` 登记和筛选真实产品仓库维度指标，Jenkins 发布记录可通过 `/api/devops/jenkins/releases` 登记和筛选真实产品版本维度发布记录，线上运行日志指标可通过 `/api/ops/online-log-metrics` 登记和筛选真实产品/模块/环境/时间窗口聚合指标；采集运行记录可通过 `/api/collectors/runs` 登记、筛选和结束，不自动生成指标或反馈数据；无法映射产品、模块、需求或导入主体的真实数据可通过 `/api/attribution/pending-items` 进入待归属队列，并通过 `/api/attribution/pending-items/{item_id}/resolve` 人工归属或忽略，处理本身不自动生成指标、反馈、需求或迭代建议；用户反馈可通过 `/api/insights/user-feedback` 登记、筛选和更新状态，用户使用指标可通过 `/api/insights/usage-metrics` 登记和筛选真实聚合指标；写操作均记录审计。审计与运行页面从真实 `/api/audit/events` 加载列表，行操作提供事件详情和基于审计主体优先的生命周期链路追踪；审计列表在 repository 可用时优先读取 SQL/repository，actor、event_type、ai_task、subject 和时间范围过滤在查询层执行。生命周期上下文已支持从 `bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback` 和 `iteration_plan_suggestion` 起点回溯同产品/版本/模块任务链路，并对未关闭严重 Bug、GitLab 风险、Jenkins 失败、线上高错误率、负面反馈和低置信度迭代建议返回来源明确的风险信号。首页 IT 团队看板已聚合真实产品、需求、AI 任务、待确认 Review、知识文档、知识沉淀、审计、Bug、GitLab 指标、Jenkins 发布、线上日志、用户使用、用户反馈和迭代规划摘要；传入 `product_id` 时，所有可归属主体必须按产品归属过滤，不展示其他产品的数据；传入 `time_range` 时，运营类指标按可解析的日期或时间窗口过滤。看板下钻到 Bug、研发运营、用户洞察和审计页面时保留产品和时间范围上下文。Docker 本地栈默认以 `PERSISTENCE_MODE=postgres` 运行，登录账号读取 PostgreSQL `users` 表，管理员可通过系统管理下的用户管理维护用户，并通过角色管理查看固定角色定义；`PERSISTENCE_MODE` 未设置时默认 `postgres`，非测试环境显式配置 `memory` 会启动失败；测试环境可继续用 MemoryStore helper 运行纯业务/接口单测。当前生产数据访问仍处于 DB-first 迁移期，`/health` 返回 `data_access_mode=db_first_migration`；PostgreSQL 启动使用轻量 `PostgresRuntimeStore` repository 容器，不再通过 `PersistentMemoryStore.from_repository(...)` 启动恢复业务集合；生产读路径不再通过 repository read snapshot 反灌 `PersistentMemoryStore`，缺少已声明的 repository/source rows 能力时只能使用测试 helper 或显式迁移后的查询路径；业务大脑列表和详情已在 PostgreSQL 运行时读取 `brain_apps` repository payload。产品配置写接口已在 handler 返回前把产品、版本、模块、Git 资源、相关系统和对应审计事件写入 repository，不依赖请求结束 `PersistentMemoryStore.persist()`；产品配置核心 GET 接口已在 repository 可用时优先读取 SQL/repository，包括产品列表/详情、指定产品的版本、模块、Git 资源和关联系统，并通过运行态 store 过期测试验证不依赖进程内集合；需求创建、修改、审批、驳回、关闭和删除也已在 handler 返回前写入需求记录及审计事件；从需求生成产品详细设计 AI 任务和后续任务创建已在同一 repository 事务中写入需求 `task_ids`/状态、AI task 和 `ai_task.created` 审计事件；需求列表、需求详情、AI 任务详情、Graph Run 列表、待确认 Review、Review 详情、模拟回写结果、Code Review 报告和 Markdown 导出在 PostgreSQL 运行时会优先读取 task workflow repository source rows；任务启动成功路径已写入 AI task、模型调用日志、Human Review、Graph Run、Checkpoint 和启动审计事件；任务启动失败路径已写入 failed task、可选模型失败日志、`ai_task.retry_started` 和失败审计事件；Review approve/edit-approve/reject/request-more-info 主路径已写入完成态或中断态 task/review/graph/checkpoint、需求状态、知识沉淀候选、可选 Bug/Code Review 报告和审计事件；cancel/submit-more-info 已写入 AI task、待确认 Review、Graph Run/Checkpoint 和审计事件；Mock Writeback 生成接口已在 handler 返回前写入 `mock_issues` 与 `mock_issue.written` 审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 task workflow source rows 恢复已完成任务和已有幂等回写结果；知识文档创建/更新/索引重试/删除、知识 chunk 重建、知识沉淀采纳/拒绝和对应审计事件已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 knowledge source rows 恢复产品、知识文档、chunk、沉淀和模型网关上下文，同步索引期间可选模型日志；AI 助手聊天成功路径已在 handler 返回前写入会话、用户消息、助手消息、模型日志和审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 assistant source rows 恢复当前用户会话、消息、产品任务摘要和模型网关上下文；模型调用失败路径写入失败模型日志和审计事件；GitHub PR 列表、GitLab MR / GitHub PR 预览审计以及快照成功、复用和失败审计已在 handler 返回前写入 repository，Code Review 报告生成/确认已随任务启动和 Review 决策事务写入；Bug 创建、修改和删除已在 handler 返回前写入 `bugs` 与对应审计事件，删除前会清空指向被删 Bug 的重复归并引用；采集运行创建/更新、待归属队列创建/处理、GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标创建已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 operational source rows 校验产品、仓库、版本、模块、采集运行和待归属当前记录；用户使用指标创建、用户反馈创建/处理、迭代建议生成和迭代建议决策已在 handler 返回前写入对应结构表与审计事件，并在 `PostgresRuntimeStore` 空启动容器下通过 insight source rows 校验产品、版本、模块、反馈、Bug 和迭代建议当前记录；用户使用指标、用户反馈和迭代建议列表已在 repository 可用时优先读取 SQL/repository，产品、模块、功能、用户群体、时间范围、状态、创建人和规划周期等过滤在查询层执行；迭代建议转需求时会在同一 repository 调用内写入新需求、建议、决策和完整审计事件；模型网关配置创建、修改、删除和连接测试审计已在 handler 返回前写入 repository，并在 `PostgresRuntimeStore` 空启动容器下通过 model gateway source rows 恢复当前配置和调用日志上下文；生命周期上下文查询生成的 edges/risks 和首页看板生成的 dashboard snapshot 已在 handler 返回前写入 repository，且这两个读接口在 PostgreSQL 运行时会读取 repository source rows；生命周期上下文 source rows 使用专用 `LifecycleContextReadModel` 承载，不再实例化 `MemoryStore` 作为聚合中间层；请求结束全局 `persist()` 已从 API middleware 移除，任何 API 请求都不再通过请求结束同步进程内 store；`app_state_snapshots` 仅作为历史迁移表保留，不再作为生产恢复源或写入目标；纯 SQL/物化 read model 聚合仍待迁移，新增生产 API 不得把进程内 store 作为数据源或写入目标。外部 DevOps 自动采集器和用户行为自动采集器尚未接入；线上日志可手工登记或导入真实聚合指标，无记录时返回真实空集合，不提供占位状态或伪造统计数据；迭代规划建议已支持基于真实反馈与 Bug 证据的生成、确认和可选转需求。

当前补充实现：`POST /api/planning/iteration-suggestions` 已基于库内真实 `user_feedback` 与 `bugs` 证据生成迭代建议；无证据时返回真实空集合，不生成占位建议。`POST /api/planning/iteration-suggestions/{suggestion_id}/decide` 支持产品负责人、研发负责人或管理员确认采纳、修改后采纳或驳回；只有 `accepted` / `edited_accepted` 且 `convert_to_requirement=true` 时才创建真实 `requirements` 记录。建议与确认分别写入 `iteration_plan_suggestions` 和 `iteration_plan_decisions`，并记录 `iteration_suggestion.generated` / `iteration_suggestion.decided` 审计事件。

DB-first 迁移补充：`app_state_snapshots` 仅作为历史迁移表保留，当前 PostgreSQL 运行时启动恢复只读取结构表，不再从 app_state JSONB 快照恢复业务集合；手动 `PersistentMemoryStore.persist()` 也不再写入 app_state JSONB 快照。

用户使用指标当前支持通过 `POST /api/insights/usage-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/insights/usage-metrics` 按产品、模块、功能、用户群体和时间范围筛选；记录写入 `user_usage_metrics`，并记录 `usage_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

GitLab 每日代码指标当前支持通过 `POST /api/devops/gitlab/daily-code-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/devops/gitlab/daily-code-metrics` 按产品、仓库和日期筛选；记录写入 `gitlab_daily_code_metrics`，并记录 `gitlab_daily_code_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

Jenkins 发布记录当前支持通过 `POST /api/devops/jenkins/releases` 手工登记或导入真实发布记录，通过 `GET /api/devops/jenkins/releases` 按产品、版本、状态和环境筛选；记录写入 `jenkins_release_records`，并记录 `jenkins_release.created` 审计事件。无记录时返回真实空集合，不生成兜底数据。

线上运行日志指标当前支持通过 `POST /api/ops/online-log-metrics` 手工登记或导入真实聚合指标，通过 `GET /api/ops/online-log-metrics` 按产品、模块、环境和时间窗口筛选；记录写入 `online_log_metrics`，并记录 `online_log_metric.created` 审计事件。无指标时返回真实空集合，不生成兜底数据。

生命周期视图和首页 IT 团队看板的 AI 任务、待确认 Review、知识沉淀和风险信号聚合必须先按任务类型读权限过滤，不能通过聚合接口绕过任务详情权限。

`/api/lifecycle/context` 当前支持的真实起点主体包括 `product`、`requirement`、`ai_task`、`human_review`、`code_review_report`、`gitlab_mr_snapshot`、`mock_issue`、`knowledge_deposit`、`audit_event`、`bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback` 和 `iteration_plan_suggestion`。审计列表发起链路追踪时，后端必须先把审计主体解析到对应需求、AI 任务或可归属证据链路；不支持的 `subject_type` 返回 `VALIDATION_ERROR`，不得退化为全量任务或伪造关系。

## 认证方式

- 方式: 本地账号登录 + Bearer Token。
- Header: `Authorization: Bearer <token>`。
- 除 `/health` 和 `/api/auth/login` 外，所有 `/api/*` 接口都需要 Bearer Token。

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
| 登记、分派、验证或关闭 Bug | product_owner、rd_owner 或 admin；tester 角色按后续真实测试组织模型扩展 |
| 维护产品、相关系统、模型网关配置、用户账号 | admin |

MVP 系统角色以 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 为主；Bug 登记和状态更新先复用 `product_owner`、`rd_owner`、`admin`，`tester`、发布负责人和 IT 管理者写权限按后续真实组织模型扩展。接口鉴权还需要结合产品归属、任务参与关系和主体权限。

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

## 接口清单

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Health | GET | `/health` | 健康检查。 |
| Long Memory | GET | `/api/long-memory/status` | 查询 GBrain 长期记忆连接器配置状态和可用能力。 |
| Auth | POST | `/api/auth/login` | 登录。 |
| Auth | GET | `/api/auth/me` | 当前用户。 |
| Auth | POST | `/api/auth/logout` | 前端退出登录辅助接口。 |
| Auth | GET | `/api/auth/roles` | 查询 MVP 可分配用户角色目录。 |
| User | GET | `/api/users` | 管理员查询用户列表。 |
| User | POST | `/api/users` | 管理员创建用户。 |
| User | PATCH | `/api/users/{user_id}` | 管理员更新用户姓名、角色、状态或密码。 |
| User | DELETE | `/api/users/{user_id}` | 管理员删除非当前登录用户；PostgreSQL 模式下从用户表移除该账号。 |
| Brain App | GET | `/api/brain-apps` | 业务大脑列表。 |
| Brain App | GET | `/api/brain-apps/{brain_app_id}` | 业务大脑详情。 |
| Product | GET | `/api/products` | 产品列表。 |
| Product | GET | `/api/products/{product_id}` | 产品详情。 |
| Product | POST | `/api/products` | 创建产品。 |
| Product | PATCH | `/api/products/{product_id}` | 更新产品。 |
| Product | DELETE | `/api/products/{product_id}` | 删除未被需求、AI 任务或 Bug 占用的产品；无业务依赖时级联清理该产品的版本、模块和 Git 资源配置。 |
| Product Version | GET | `/api/products/{product_id}/versions` | 产品迭代版本列表，前端主入口位于需求交付/迭代版本。 |
| Product Version | POST | `/api/products/{product_id}/versions` | 创建产品迭代版本。 |
| Product Version | PATCH | `/api/product-versions/{version_id}` | 更新产品迭代版本非状态字段；状态变更必须走推进接口。 |
| Product Version | POST | `/api/product-versions/{version_id}/advance-status` | 预览或推进迭代版本状态，并同步符合条件的需求状态。 |
| Product Version | DELETE | `/api/product-versions/{version_id}` | 删除未被需求、AI 任务或 Bug 占用的产品迭代版本。 |
| Product Module | GET | `/api/products/{product_id}/modules` | 产品模块列表。 |
| Product Module | POST | `/api/products/{product_id}/modules` | 创建产品模块。 |
| Product Module | PATCH | `/api/product-modules/{module_id}` | 更新产品模块。 |
| Product Module | DELETE | `/api/product-modules/{module_id}` | 删除未被需求、AI 任务或 Bug 占用的产品模块。 |
| Product Git | GET | `/api/products/{product_id}/git-repositories` | 产品 Git 资源列表。 |
| Product Git | POST | `/api/products/{product_id}/git-repositories` | 创建产品 Git 资源。 |
| Product Git | PATCH | `/api/product-git-repositories/{repo_id}` | 更新产品 Git 资源。 |
| Product Git | DELETE | `/api/product-git-repositories/{repo_id}` | 删除产品 Git 资源配置。 |
| System | GET | `/api/system/related-systems` | 相关系统列表，支持 `active_only` 和 `product_id` 过滤。 |
| System | POST | `/api/system/related-systems` | 创建相关系统。 |
| System | PATCH | `/api/system/related-systems/{system_id}` | 更新相关系统。 |
| System | DELETE | `/api/system/related-systems/{system_id}` | 删除相关系统配置。 |
| System | GET | `/api/system/model-gateway-configs` | 模型网关配置列表。 |
| System | POST | `/api/system/model-gateway-configs/test` | 使用临时参数测试模型网关 Chat 与 Embedding 连通性，不保存配置或密钥。 |
| System | POST | `/api/system/model-gateway-configs` | 创建模型网关配置。 |
| System | PATCH | `/api/system/model-gateway-configs/{config_id}` | 更新模型网关配置。 |
| System | DELETE | `/api/system/model-gateway-configs/{config_id}` | 删除模型网关配置。 |
| System | GET | `/api/model-gateway/logs` | 查询模型调用元数据日志，不返回完整 prompt 或输出。 |
| Assistant | GET | `/api/assistant/conversations` | 查询当前登录用户的 AI 助手会话列表。 |
| Assistant | GET | `/api/assistant/conversations/{conversation_id}/messages` | 查询当前登录用户某个 AI 助手会话的消息记录。 |
| Assistant | POST | `/api/assistant/chat` | AI 助手问答，基于当前 AI Brain 系统上下文和模型网关 Chat 能力回答产品、任务、项目进展和配置问题。 |
| Requirement | GET | `/api/requirements` | 需求列表。 |
| Requirement | POST | `/api/requirements` | 新增待审批需求。 |
| Requirement | POST | `/api/requirements/batch-schedule` | 批量归集同产品需求到迭代版本。 |
| Requirement | GET | `/api/requirements/{requirement_id}` | 需求详情。 |
| Requirement | GET | `/api/requirements/{requirement_id}/full-chain` | 需求全链路详情，按时间线聚合需求、迭代版本、AI 任务、Review、PR/MR 快照、代码评审、Bug、发布和知识沉淀；`git_snapshots` 可包含风险摘要、diff 文件树和 Review Checklist。 |
| Requirement | PATCH | `/api/requirements/{requirement_id}` | 更新待审批或已驳回需求。 |
| Requirement | DELETE | `/api/requirements/{requirement_id}` | 删除未生成任务的需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/approve` | 审批通过需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/reject` | 驳回需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/close` | 关闭需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/generate-task` | 需求排期后生成 AI 任务。 |
| AI Task | GET | `/api/ai-tasks` | 任务列表，支持按状态、任务类型、产品、需求、创建时间、关键词、创建人筛选，并返回分页结果。 |
| AI Task | POST | `/api/ai-tasks` | 低层任务创建接口。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/start` | 启动任务；停在 `model_gateway_failed` 或 `code_review_executor_failed` 的失败任务可用同一 task_id 重试。 |
| AI Task | GET | `/api/ai-tasks/{task_id}` | 任务详情。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/more-info` | 提交补充信息。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/cancel` | 取消任务。 |
| Graph Runtime | GET | `/api/graph-runs` | Graph Run 列表，支持按 `task_id` 查询任务运行态；返回 `runtime`、`node_path`、`checkpoint_id` 和 `state_snapshot.graph_runtime`。 |
| Review | GET | `/api/reviews/pending` | 待确认列表。 |
| Review | GET | `/api/reviews/{review_id}` | 确认详情。 |
| Review | POST | `/api/reviews/{review_id}/approve` | 原样采纳。 |
| Review | POST | `/api/reviews/{review_id}/edit-approve` | 修改后采纳。 |
| Review | POST | `/api/reviews/{review_id}/reject` | 驳回重跑。 |
| Review | POST | `/api/reviews/{review_id}/request-more-info` | 要求补充信息。 |
| Knowledge | GET | `/api/knowledge/documents` | 知识文档列表。 |
| Knowledge | POST | `/api/knowledge/documents` | 导入知识文档。 |
| Knowledge | PATCH | `/api/knowledge/documents/{document_id}` | 更新知识文档元数据、内容、权限角色、标签或索引状态。 |
| Knowledge | DELETE | `/api/knowledge/documents/{document_id}` | 删除知识文档。 |
| Knowledge | POST | `/api/knowledge/documents/{document_id}/retry-index` | 重试失败知识文档索引。 |
| Knowledge | POST | `/api/knowledge/search` | 知识检索。 |
| Knowledge | GET | `/api/knowledge/deposits` | 知识沉淀候选列表。 |
| Knowledge | POST | `/api/knowledge/deposits/{deposit_id}/approve` | 采纳知识沉淀。 |
| Knowledge | POST | `/api/knowledge/deposits/{deposit_id}/reject` | 驳回知识沉淀。 |
| Output | GET | `/api/writeback/results/{task_id}` | 查询模拟回写结果。 |
| Output | POST | `/api/writeback/results/{task_id}` | 显式生成或复用模拟回写结果，使用幂等键避免重复 Issue。 |
| Output | GET | `/api/export/tasks/{task_id}/markdown` | 导出 Markdown 方案。 |
| Audit | GET | `/api/audit/events` | 查询审计事件。 |
| DevOps | GET | `/api/devops/gitlab/daily-code-metrics` | 查询真实 GitLab 每日提交和代码质量审核结果。 |
| DevOps | POST | `/api/devops/gitlab/daily-code-metrics` | 登记真实 GitLab 每日提交和代码质量审核结果。 |
| DevOps | GET | `/api/devops/operational-metrics` | 查询研发运营统一聚合列表，支持服务端分页、排序和筛选。 |
| Collectors | GET | `/api/collectors/runs` | 查询 DevOps/洞察采集运行记录。 |
| Collectors | POST | `/api/collectors/runs` | 登记一次真实采集或导入运行。 |
| Collectors | PATCH | `/api/collectors/runs/{run_id}` | 更新采集运行状态、导入数量、错误说明或摘要。 |
| Attribution | GET | `/api/attribution/pending-items` | 查询待归属数据队列。 |
| Attribution | POST | `/api/attribution/pending-items` | 登记无法映射产品、模块、需求或导入主体的真实数据。 |
| Attribution | POST | `/api/attribution/pending-items/{item_id}/resolve` | 将待归属项归属到已有上下文或忽略为噪声。 |
| GitLab Review | GET | `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview` | 预览内部 GitLab MR 元信息。 |
| GitLab Review | POST | `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot` | 拉取 MR 元信息和 diff，生成 code_review 输入快照。 |
| GitHub Review | GET | `/api/devops/github/pull-requests/{repository_id}` | 列出产品 GitHub 仓库可访问 PR，支持 `state` 和 `limit`。 |
| GitHub Review | GET | `/api/devops/github/pull-requests/{repository_id}/{pr_number}/preview` | 预览 GitHub PR 元信息。 |
| GitHub Review | POST | `/api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot` | 拉取 PR 元信息和 diff 摘要，生成 code_review 输入快照。 |
| Code Review | GET | `/api/ai-tasks/{task_id}/code-review-report` | 查询 GitLab MR / GitHub PR 代码 Review 报告、执行器信息和确认状态。 |
| DevOps | GET | `/api/devops/jenkins/releases` | 查询 Jenkins 发布记录。 |
| DevOps | POST | `/api/devops/jenkins/releases` | 登记真实 Jenkins 发布记录。 |
| Ops | GET | `/api/ops/online-log-metrics` | 查询线上运行日志运营指标。 |
| Ops | POST | `/api/ops/online-log-metrics` | 登记真实线上运行日志聚合指标。 |
| Bug | GET | `/api/bugs` | 查询 Bug 列表，支持产品、迭代版本、状态、严重程度和来源过滤。 |
| Bug | POST | `/api/bugs` | v1.1 基础接口，登记 AI 自动测试或人工测试 Bug。 |
| Bug | POST | `/api/bugs/batch-update` | 批量更新 Bug 状态、严重级别或处理人，返回 updated/skipped 明细并写入批次审计。 |
| Bug | PATCH | `/api/bugs/{bug_id}` | v1.1 基础接口，更新 Bug 状态、分派人、复现信息或重复归并关系。 |
| Bug | DELETE | `/api/bugs/{bug_id}` | 删除 Bug 记录。 |
| Lifecycle | GET | `/api/lifecycle/context` | 查询软件研发全流程上下文关系、上下游影响和风险信号。 |
| Dashboard | GET | `/api/dashboard/it-team` | 查询首页 IT 团队看板。 |
| Insights | GET | `/api/insights/items` | 查询用户洞察统一聚合列表，支持服务端分页、排序和筛选。 |
| Insights | GET | `/api/insights/usage-metrics` | 查询真实用户使用指标。 |
| Insights | POST | `/api/insights/usage-metrics` | 登记真实用户使用指标。 |
| Insights | GET | `/api/insights/user-feedback` | 查询用户反馈列表。 |
| Insights | POST | `/api/insights/user-feedback` | 登记真实用户反馈。 |
| Insights | PATCH | `/api/insights/user-feedback/{feedback_id}` | 更新用户反馈状态和处理信息。 |
| Planning | GET | `/api/planning/iteration-suggestions` | 查询 AI 迭代规划建议。 |
| Planning | POST | `/api/planning/iteration-suggestions` | 基于真实反馈和 Bug 证据生成 AI 迭代规划建议。 |
| Planning | POST | `/api/planning/iteration-suggestions/{suggestion_id}/decide` | 确认、修改后采纳或驳回迭代规划建议。 |

---

## 核心接口详情

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

### 角色目录

```http
GET /api/auth/roles
```

该接口返回当前 MVP 可分配的系统角色目录，供用户管理页面、知识权限选择、权限说明和外部集成统一引用。`POST /api/users`、`PATCH /api/users/{user_id}` 和知识 `permission_roles` 字段只能使用该目录中的 `code`。

响应：

```json
{
  "data": {
    "items": [
      {
        "code": "admin",
        "name": "系统管理员",
        "description": "负责用户、角色、模型网关、审计与系统级配置管理。",
        "category": "system",
        "business_roles": ["平台管理员"],
        "responsibilities": [
          "管理本地用户账号、状态和角色分配。",
          "维护 OpenAI-compatible 模型网关配置。",
          "查看审计与运行状态，处理系统级异常。"
        ],
        "data_scope": "全平台系统配置、审计事件和授权业务数据。",
        "decision_scope": "账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍。",
        "menu_scope": ["系统管理", "审计与运行", "产品资产", "需求交付", "任务中心"],
        "limitations": [
          "不代替产品负责人、研发负责人或评审负责人做业务最终决策。",
          "所有系统配置、用户和模型网关变更必须写入审计。"
        ],
        "permissions": ["system.users.manage", "system.model_gateway.manage", "audit.read", "workspace.read", "workspace.write"],
        "is_assignable": true,
        "sort_order": 10,
        "status": "active"
      }
    ],
    "total": 6
  },
  "trace_id": "trace_002"
}
```

### 业务大脑

业务大脑 v1 MVP 只提供只读配置读取，默认从 `brain_apps` 表加载 `rd_brain`；不提供业务大脑新增、编辑、停用或系统管理页面 CRUD。

```http
GET /api/brain-apps
GET /api/brain-apps/{brain_app_id}
```

列表响应：

```json
{
  "data": {
    "items": [
      {
        "id": "rd_brain",
        "code": "rd_brain",
        "name": "研发大脑",
        "status": "active",
        "description": "把研发需求转成可确认、可回写、可沉淀的任务方案。",
        "config": {
          "default_task_types": [
            "product_detail_design",
            "technical_solution",
            "development_planning",
            "automated_testing",
            "release_readiness",
            "post_release_analysis",
            "code_review"
          ]
        }
      }
    ]
  },
  "trace_id": "trace_002"
}
```

### 产品配置

查询接口都支持 `active_only=true|false`：

```http
GET /api/products?active_only=true
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
POST /api/products/{product_id}/versions
PATCH /api/product-versions/{version_id}
POST /api/product-versions/{version_id}/advance-status
DELETE /api/product-versions/{version_id}
POST /api/products/{product_id}/modules
PATCH /api/product-modules/{module_id}
DELETE /api/product-modules/{module_id}
POST /api/products/{product_id}/git-repositories
PATCH /api/product-git-repositories/{repo_id}
DELETE /api/product-git-repositories/{repo_id}
```

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
  "project_id": "123",
  "project_path": "rd/ai-brain-api",
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
- `git_provider` 支持 `gitlab` 和 `github`。GitLab 绑定需提供 `project_id` 或 `project_path`；GitHub 绑定需提供 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`。
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

### 平台配置

相关系统：

```http
GET /api/system/related-systems?active_only=true&product_id=product_rd
POST /api/system/related-systems
PATCH /api/system/related-systems/{system_id}
```

请求体：

```json
{
  "code": "knowledge",
  "name": "知识中心",
  "description": "文档导入、检索和知识沉淀",
  "owner_team": "rd",
  "product_id": "product_rd",
  "status": "active",
  "display_order": 100
}
```

模型网关配置：

```http
GET /api/system/model-gateway-configs
POST /api/system/model-gateway-configs/test
POST /api/system/model-gateway-configs
PATCH /api/system/model-gateway-configs/{config_id}
DELETE /api/system/model-gateway-configs/{config_id}
```

请求体：

```json
{
  "name": "默认模型网关",
  "provider": "openai_compatible",
  "base_url": "https://api.example.com/v1",
  "api_key": "<redacted>",
  "default_chat_model": "chat-model",
  "default_embedding_model": "embedding-model",
  "embedding_connection_mode": "reuse_chat",
  "embedding_base_url": null,
  "embedding_api_key": null,
  "embedding_dimension": 1536,
  "timeout_seconds": 60,
  "max_retries": 1,
  "status": "active",
  "is_default": true
}
```

响应不会返回明文 `api_key`、`embedding_api_key`、密钥前缀或后缀，只返回 `api_key_configured` 和 `embedding_api_key_configured`。`embedding_connection_mode` 可取 `disabled`、`reuse_chat` 或 `custom`：`disabled` 表示仅启用 Chat 能力，`reuse_chat` 使用 Chat 的 `base_url/api_key` 调用 `/embeddings`，`custom` 使用 `embedding_base_url/embedding_api_key` 调用 `/embeddings`。`default_embedding_model` 在 `disabled` 模式可为空；`embedding_dimension` 当前必须等于系统 `VECTOR_DIMENSION`。
`provider` 目前仅允许 `openai_compatible`；新增或编辑提交其他 provider 返回 `400 VALIDATION_ERROR`，不得保存为 active/default 配置。

测试检测：

```http
POST /api/system/model-gateway-configs/test
```

请求体使用模型网关配置字段，可选传入 `config_id`。编辑已有配置时，如果请求体不含 `api_key` 且 `config_id` 对应配置已保存密钥，则使用服务端已有密钥完成本次 Chat 测试；`embedding_connection_mode=custom` 且请求体不含 `embedding_api_key` 时，可复用已有配置中的服务端 Embedding 密钥。新增配置测试必须显式提交所需密钥。`test_target` 默认为 `chat_and_embedding`，可取 `chat_and_embedding`、`chat` 或 `embedding`；当 `test_target=chat` 或 `embedding_connection_mode=disabled` 时不要求 `default_embedding_model`，Embedding 段返回 `status=skipped`。

```json
{
  "config_id": "model_config_default",
  "name": "默认模型网关",
  "provider": "openai_compatible",
  "base_url": "https://api.example.com/v1",
  "api_key": "<redacted>",
  "default_chat_model": "chat-model",
  "default_embedding_model": "embedding-model",
  "embedding_connection_mode": "custom",
  "embedding_base_url": "https://embedding.example.com/v1",
  "embedding_api_key": "<redacted>",
  "embedding_dimension": 1536,
  "timeout_seconds": 60,
  "max_retries": 1,
  "status": "active",
  "is_default": true,
  "test_target": "chat_and_embedding"
}
```

成功或 provider 调用失败都返回脱敏检测结果；整体 `ok=false` 时前端应展示失败段和 `error_code`，不把本次测试自动保存为配置。

```json
{
  "ok": true,
  "chat": {
    "ok": true,
    "status": "succeeded",
    "model": "chat-model",
    "latency_ms": 18
  },
  "embedding": {
    "ok": true,
    "status": "succeeded",
    "model": "embedding-model",
    "latency_ms": 12,
    "dimension": 1536
  },
  "test_target": "chat_and_embedding"
}
```

仅测试 Chat 的响应示例：

```json
{
  "ok": true,
  "chat": {
    "ok": true,
    "status": "succeeded",
    "model": "codex-auto-review",
    "latency_ms": 18
  },
  "embedding": {
    "ok": true,
    "status": "skipped",
    "model": ""
  },
  "test_target": "chat"
}
```

测试接口会按 `test_target` 临时调用 `{base_url}/chat/completions` 和/或 Embedding 连接对应的 `/embeddings`，但不得持久化配置、密钥或写入 `model_gateway_logs`；只写入 `model_gateway_config.tested` 审计事件，载荷包含 provider、测试范围和测试状态，不包含密钥、完整 prompt 或完整输出。`test_target=chat` 只证明 Chat 能力可用，不代表知识索引、知识检索或长期记忆 embedding 能力可用。健康检查继续返回兼容字段 `model_gateway`，并额外返回 `chat_gateway` 与 `embedding_gateway`，Embedding 可为 `configured`、`disabled`、`failed` 或 `not_configured`。

模型调用日志：

```http
GET /api/model-gateway/logs?ai_task_id=task_001&status=succeeded
```

模型调用日志只返回 `provider`、`model`、`purpose`、`tokens`、`latency_ms`、`status`、`error`、`created_at` 和 `model_gateway_config_id` 等元数据，不返回完整 prompt、完整模型输出或密钥。

AI 助手聊天：

```http
POST /api/assistant/chat
```

请求体：

```json
{
  "conversation_id": "conversation_001",
  "message": "AI Brain 项目现在开发到哪里了？",
  "product_id": "product_001",
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
    "content": "当前已完成 GitHub PR Review 支持，正在推进 AI 助手聊天界面。"
  },
  "model": "codex-auto-review",
  "latency_ms": 358,
  "suggestions": ["查看任务中心", "检查 GitHub PR"]
}
```

助手请求会向模型网关注入服务端生成的 `system_context`，包含当前产品、需求数量、任务数量、最新需求/任务、Git 仓库和默认模型网关配置状态。`system_context` 只进入模型请求，不写入响应或模型日志；模型日志以 `purpose=assistant_chat` 记录元数据，审计事件为 `assistant.chat_completed`。

`conversation_id` 可为空，服务端会创建新会话；也可传入已有会话 ID 继续对话。若传入的会话 ID 已存在但不属于当前用户，接口返回 404；若 ID 不存在，则按当前用户创建该会话以兼容客户端预分配 ID。成功问答会按当前登录用户保存一条 user 消息和一条 assistant 消息，保存内容不进入 `model_gateway_logs`。

当前用户会话列表：

```http
GET /api/assistant/conversations
```

响应：

```json
{
  "items": [
    {
      "id": "conversation_001",
      "title": "AI Brain 项目现在开发到哪里了？",
      "product_id": "product_001",
      "message_count": 2,
      "last_message_at": "2026-06-03T09:00:00+00:00",
      "created_at": "2026-06-03T09:00:00+00:00",
      "updated_at": "2026-06-03T09:00:00+00:00"
    }
  ],
  "total": 1
}
```

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
      "content": "AI Brain 项目现在开发到哪里了？"
    },
    {
      "id": "assistant_message_002",
      "role": "assistant",
      "content": "当前已支持按用户保存聊天历史。",
      "model": "codex-auto-review",
      "suggestions": ["查看任务中心"]
    }
  ],
  "total": 2
}
```

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
- `input.product_id` 必填且必须指向启用产品；`input.version_id` 可选，填写时必须指向同产品 `planning` 或 `active` 迭代版本。
- 审批通过调用 `POST /api/requirements/{requirement_id}/approve`。
- 审批通过但未选择迭代版本时进入 `approved` 需求池；已选择或后续补充有效迭代版本时进入 `planned`。
- 批量排期调用 `POST /api/requirements/batch-schedule`，静态路由必须先于 `/api/requirements/{requirement_id}` 注册，避免被动态详情路由吞掉。
- 只有 `planned` 需求可以调用 `POST /api/requirements/{requirement_id}/generate-task`。
- 生成产品详细设计任务后需求状态进入 `designing`，后续 AI 任务创建和人工确认会继续推进到 `ready_for_dev`、`developing`、`code_reviewing`、`testing`、`ready_for_release`、`released` 或 `accepted`。需求仍保留原始输入和审批结论。
- 关闭需求后不得再生成新 AI 任务。

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

当前实现会同步运行到下一个人工确认点或失败状态。`draft` 任务可启动；已失败且 `current_step` 为 `model_gateway_failed` 或 `code_review_executor_failed` 的任务可用同一 `task_id` 再次调用 start 重试，并记录 `ai_task.retry_started` 审计事件。非 code_review 任务若存在 active/default 的 OpenAI-compatible 模型网关配置且已配置 API Key，启动时调用 `{base_url}/chat/completions` 并要求 `response_format={"type":"json_object"}`；若没有结构化默认配置但设置了 `MODEL_GATEWAY_BASE_URL` 和 `MODEL_GATEWAY_API_KEY`，则使用环境模型网关。缺少可用模型网关或 active/default 配置缺失 API Key 返回 `MODEL_GATEWAY_CONFIG_INVALID`；provider 调用、响应解析或网络失败返回 `MODEL_GATEWAY_FAILED`。code_review 任务通过 `code_review_executor` 执行：默认 `claude_code_skill/code-review` 命令适配器由 `CODE_REVIEW_EXECUTOR_COMMAND` 配置，输入 JSON 通过 stdin 提供，输出必须是包含 `summary`、`risk_level` 和 `findings` 的 JSON 对象，系统会补齐并持久化 executor 元数据；显式设置 `CODE_REVIEW_EXECUTOR_TYPE=model_gateway` 时复用模型网关适配器；默认外部命令为空且存在 active/default 或环境模型网关时，系统会自动使用 `model_gateway` 适配器，并以 MR/PR 快照、技术方案、需求和产品上下文作为 Review 输入。执行器配置缺失、调用失败、超时、响应解析或结构化报告校验失败返回 `CODE_REVIEW_EXECUTOR_FAILED`。这些失败都会把任务置为 `failed`；使用模型网关适配器时保留模型调用元数据日志；任务启动不得生成本地 fallback 输出。
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

响应包含 `task_type`、`input`、`output`、`current_step`、`pending_review`、`reviews`、`mock_issues` 和 `knowledge_deposits`。通过需求生成的任务必须在 `input` 中包含：

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
    "diff_refs": {
      "base_sha": "abc123",
      "head_sha": "def456"
    },
    "web_url": "https://github.com/owner/repo/pull/3"
  },
  "trace_id": "trace_github_preview_001"
}
```

MR/PR diff 快照是 code_review 任务的唯一输入快照来源。MVP-A 必须支持 GitLab/GitHub 只读仓库绑定、变更预览和 diff 快照生成；MVP-B 在快照基础上创建正式 `code_review` 任务并生成 Review 报告。任务中心前端应先读取产品 Git 资源，再根据 provider 预览 MR 或 PR、展示文件树、变更明细、风险摘要和 Review Checklist，确认后生成快照，最后用兼容字段 `gitlab_mr_snapshot_id` 创建 `code_review` 任务；任务创建接口不得静默重新拉取或覆盖已有快照。后端通过 GitLab API 读取 `GET /api/v4/projects/{project}/merge_requests/{iid}` 和 `.../{iid}/changes`，其中 `project` 来自产品 Git 资源的 `project_path` 或 `project_id`。GitHub API 读取 `GET /repos/{owner}/{repo}/pulls/{number}` 和 `.../files?per_page=100`，其中 `owner/repo` 来自 `project_path` 或 `remote_url`。`remote_url` 用于推导 GitLab base URL 或 GitHub Enterprise base URL，也可由 `GITLAB_BASE_URL` / `GITHUB_BASE_URL` 提供；`credential_ref` 推荐使用环境变量或服务端密钥引用，本地联调可直填只读 token，响应不得返回凭据值。同一 `repository_id + snapshot_hash` 已存在时，快照接口返回已有 snapshot 并记录 `gitlab_mr.snapshot_reused` 或 `github_pr.snapshot_reused`，不得重复入库。MR/PR diff、变更文件数或单文件 diff 行数超过限制时返回 `GITLAB_MR_DIFF_TOO_LARGE`，不创建快照，并记录对应 provider 的 `*.snapshot_failed` 审计事件，payload 包含 `diff_size_bytes`、`diff_limit_bytes`、`changed_file_count`、`changed_file_limit`、`file_diff_line_count`、`file_diff_line_limit`、`file_path`、`mr_iid`、`requirement_id` 和 `technical_solution_task_id`。

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
    "diff_size_bytes": 48000,
    "diff_limit_bytes": 204800,
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
    "archived_at": null
  },
  "trace_id": "trace_review_001"
}
```

约束：

- MR diff 快照不可被 GitLab 后续变更静默覆盖；重新 Review 必须创建新快照或新运行记录。
- PR diff 快照不可被 GitHub 后续变更静默覆盖；重新 Review 必须创建新快照或新运行记录。
- 重复拉取相同仓库的相同 diff 时返回已有快照，并通过 `gitlab_mr.snapshot_reused` 或 `github_pr.snapshot_reused` 保留审计痕迹。
- Review 报告经人工确认或修改后采纳后才可归档为正式结论。
- v1 MVP 不提供 GitLab/GitHub 评论、审批状态、request changes、合并状态或分支变更回写接口。
- 首页 IT 团队看板返回当前业务数据聚合，不返回空集合占位；研发运营看板等未接入真实采集器的接口返回空集合响应，响应必须包含 `items` 和 `total`，不得返回占位状态或伪造统计数据。用户使用指标、用户反馈和迭代规划建议已进入真实业务实现，不再使用空集合替代业务数据。

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

### 知识中心

导入文档：

```http
POST /api/knowledge/documents
```

```json
{
  "title": "研发需求拆解模板",
  "doc_type": "system",
  "product_id": "product_001",
  "content": "# 研发需求拆解模板...",
  "tags": ["研发流程", "任务拆解"],
  "permission_roles": ["rd_owner", "knowledge_owner"]
}
```

查询文档：

```http
GET /api/knowledge/documents?keyword=研发&doc_type=system&index_status=text_indexed
```

知识文档索引状态支持：`importing | pending_index | text_indexed | vector_indexed | indexed | index_failed | archived`，其中 `indexed` 为历史兼容状态。Embedding 不可用但文本 chunk 成功时进入 `text_indexed`，响应包含 `vector_index_error` 和兼容展示用 `index_error`；基础文本索引失败时进入 `index_failed`。

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
  "top_k": 5
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
          "chunk_id": "doc_001_chunk_001",
          "doc_type": "manual",
          "title": "研发需求拆解模板"
        }
      }
    ],
    "total": 1
  },
  "trace_id": "trace_008"
}
```

前端知识中心提供“知识检索”弹窗，提交真实 `/api/knowledge/search` 请求并展示可访问结果的标题、来源、召回模式和内容摘要；后端返回 chunk 级命中结果，权限过滤必须在返回 chunk 前完成。存在可读向量 chunk 且 Embedding 网关可用时查询文本会生成 embedding，并只和 `embedding_config_id`、`embedding_model`、`embedding_dimension` 兼容的 chunk 计算 cosine 相似度，返回 `score` 与 `retrieval_mode=vector`；不兼容、缺失或仅文本索引可用时按关键词检索返回 `retrieval_mode=keyword` 且 `score=null`。无结果时展示真实空状态，不回退到示例数据。

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

### 研发与运营数据

GitLab 每日提交和代码质量：

```http
GET /api/devops/gitlab/daily-code-metrics?product_id=product_001&date=2026-05-28
```

当前实现支持按产品、仓库和日期筛选真实登记或导入的 GitLab 每日指标；无指标时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "gitlab_metric_001",
        "product_id": "product_001",
        "repository_id": "repo_001",
        "metric_date": "2026-05-28",
        "commit_count": 18,
        "active_author_count": 5,
        "merge_request_count": 3,
        "changed_files": 42,
        "additions": 860,
        "deletions": 210,
        "quality_score": 86,
        "risk_count": 2,
        "author_metrics": [
          {"author": "alice", "commit_count": 7, "additions": 360, "deletions": 80, "review_issue_count": 1}
        ],
        "status": "collected",
        "source_channel": "manual",
        "created_by": "user_admin",
        "created_at": "2026-05-28T20:10:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_011"
}
```

产品负责人、研发负责人或管理员可登记真实聚合指标：

```http
POST /api/devops/gitlab/daily-code-metrics
Content-Type: application/json

{
  "product_id": "product_001",
  "repository_id": "repo_001",
  "metric_date": "2026-05-28",
  "commit_count": 18,
  "active_author_count": 5,
  "merge_request_count": 3,
  "changed_files": 42,
  "additions": 860,
  "deletions": 210,
  "quality_score": 86,
  "risk_count": 2,
  "author_metrics": [
    {"author": "alice", "commit_count": 7, "additions": 360, "deletions": 80, "review_issue_count": 1}
  ],
  "status": "collected",
  "source_channel": "manual"
}
```

服务端校验产品和 GitLab 仓库处于 active 状态且仓库归属该产品，计数字段不得为负数，`quality_score` 范围为 0-100；写入 `gitlab_daily_code_metrics` 后记录 `gitlab_daily_code_metric.created` 审计事件。

Jenkins 发布记录：

```http
GET /api/devops/jenkins/releases?product_id=product_001&version_id=version_001
```

当前实现支持按产品、版本、状态和环境筛选真实登记或导入的 Jenkins 发布记录；无记录时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "jenkins_release_001",
        "product_id": "product_001",
        "version_id": "version_001",
        "job_name": "rd-brain-deploy",
        "build_id": "build-20260601-001",
        "build_number": 128,
        "environment": "prod",
        "status": "success",
        "trigger_actor": "release-bot",
        "commit_sha": "8f6b7c1",
        "duration_seconds": 420,
        "started_at": "2026-06-01T12:20:00Z",
        "deployed_at": "2026-06-01T12:27:00Z",
        "source_channel": "manual_import",
        "created_by": "user_admin",
        "created_at": "2026-06-01T12:30:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_012"
}
```

产品负责人、研发负责人或管理员可登记真实发布记录：

```http
POST /api/devops/jenkins/releases
Content-Type: application/json

{
  "product_id": "product_001",
  "version_id": "version_001",
  "job_name": "rd-brain-deploy",
  "build_id": "build-20260601-001",
  "build_number": 128,
  "environment": "prod",
  "status": "success",
  "trigger_actor": "release-bot",
  "commit_sha": "8f6b7c1",
  "duration_seconds": 420,
  "started_at": "2026-06-01T12:20:00Z",
  "deployed_at": "2026-06-01T12:27:00Z",
  "source_channel": "manual_import"
}
```

服务端校验产品处于 active 状态且版本归属该产品，archived 版本不得登记发布记录；`status` 只能为 `success`、`failed`、`running` 或 `canceled`，构建编号和耗时不得为负数，部署时间不得早于开始时间；写入 `jenkins_release_records` 后记录 `jenkins_release.created` 审计事件。

研发运营统一聚合列表：

```http
GET /api/devops/operational-metrics?category=Jenkins%20发布&name=deploy&status=success&page=1&page_size=10&sort_by=updated_at&sort_order=desc
```

该接口面向研发运营主列表聚合 GitLab 每日代码指标、Jenkins 发布记录和线上运行日志指标，返回统一行字段 `category`、`name`、`value`、`status`、`updated_at` 以及原始上下文字段。支持 `category` 精确筛选，`name` 文本筛选，`status` 精确筛选，`page/page_size` 服务端分页，`sort_by` 支持 `category/id/name/status/updated_at/value`，`sort_order` 支持 `asc/desc`。前端研发运营指标主列表必须调用该接口，不再并发拉取三类原始接口后本地拼装、排序或分页；登记弹窗仍使用各原始 POST 接口写入真实指标。

线上运行日志运营指标：

```http
GET /api/ops/online-log-metrics?product_id=product_001&module_code=checkout&environment=prod&from=2026-06-01T00:00:00Z&to=2026-06-01T01:00:00Z
```

当前实现支持按产品、模块、环境和时间窗口筛选真实登记或导入的线上运行日志聚合指标；无记录时返回真实空集合：

```json
{
  "data": {
    "items": [
      {
        "id": "online_log_metric_001",
        "product_id": "product_001",
        "module_code": "checkout",
        "environment": "prod",
        "window_start": "2026-06-01T00:00:00Z",
        "window_end": "2026-06-01T01:00:00Z",
        "request_count": 2400,
        "error_count": 12,
        "error_rate": 0.005,
        "p95_latency_ms": 318.5,
        "p99_latency_ms": 640.25,
        "core_event_count": 240,
        "top_errors": [
          {
            "message": "PaymentTimeout",
            "count": 7
          }
        ],
        "anomaly_summary": "checkout error spike after release",
        "status": "collected",
        "source_channel": "manual_import",
        "created_by": "user_admin",
        "created_at": "2026-06-01T01:05:00Z",
        "updated_at": "2026-06-01T01:05:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_013"
}
```

产品负责人、研发负责人或管理员可登记真实线上运行日志聚合指标：

```http
POST /api/ops/online-log-metrics
Content-Type: application/json

{
  "product_id": "product_001",
  "module_code": "checkout",
  "environment": "prod",
  "window_start": "2026-06-01T00:00:00Z",
  "window_end": "2026-06-01T01:00:00Z",
  "request_count": 2400,
  "error_count": 12,
  "p95_latency_ms": 318.5,
  "p99_latency_ms": 640.25,
  "core_event_count": 240,
  "top_errors": [
    {
      "message": "PaymentTimeout",
      "count": 7
    }
  ],
  "anomaly_summary": "checkout error spike after release",
  "status": "collected",
  "source_channel": "manual_import"
}
```

服务端校验产品处于 active 状态，`module_code` 如传入必须属于该产品且模块 active，时间窗口必须满足 `window_end > window_start`；请求数、错误数、核心事件数和延迟不得为负数，错误数不得大于请求数，`status` 只能为 `collected`、`partial` 或 `failed`。`error_rate` 由服务端按 `error_count / request_count` 计算；记录写入 `online_log_metrics` 后记录 `online_log_metric.created` 审计事件。外部线上日志自动采集器仍属后续增强，当前入口用于导入或手工登记真实聚合指标，不生成测试兜底行。

采集运行记录：

```http
GET /api/collectors/runs?collector_type=gitlab_daily_code_metric&product_id=product_001&status=running
```

返回真实采集运行台账；无记录时返回 `items: []` 和 `total: 0`，不返回示例运行：

```json
{
  "data": {
    "items": [
      {
        "id": "collector_run_001",
        "collector_type": "gitlab_daily_code_metric",
        "product_id": "product_001",
        "source_system": "gitlab",
        "status": "running",
        "started_at": "2026-06-01T08:00:00Z",
        "finished_at": null,
        "records_imported": 0,
        "error_message": null,
        "payload_summary": {
          "repository_path": "rd/platform-api"
        },
        "created_by": "user_admin",
        "created_at": "2026-06-01T08:00:00Z",
        "updated_at": "2026-06-01T08:00:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_014"
}
```

产品负责人、研发负责人或管理员可登记运行：

```http
POST /api/collectors/runs
Content-Type: application/json

{
  "collector_type": "gitlab_daily_code_metric",
  "product_id": "product_001",
  "source_system": "gitlab",
  "status": "running",
  "records_imported": 0,
  "payload_summary": {
    "repository_path": "rd/platform-api"
  }
}
```

运行完成或取消时更新状态：

```http
PATCH /api/collectors/runs/collector_run_001
Content-Type: application/json

{
  "status": "succeeded",
  "records_imported": 3
}
```

`collector_type` 只允许 `gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；`status` 只允许 `running`、`succeeded`、`failed`、`cancelled`。`product_id` 如传入必须指向 active 产品；`source_system` 必须非空；`records_imported` 不得为负数；`failed` 必须提供非空 `error_message`；`succeeded / failed / cancelled` 为终态，不得再转回 `running` 或其他状态。创建和更新分别写入 `collector_run.created` 与 `collector_run.updated` 审计事件。采集运行记录只记录采集尝试和结果，不自动写入 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议业务数据。

待归属数据队列：

```http
GET /api/attribution/pending-items?status=pending&source_type=user_feedback
```

响应返回 `pending_attribution_items` 结构表中的真实队列项；没有数据时返回 `items: []` 和 `total: 0`，不返回示例队列项：

```json
{
  "data": {
    "items": [
      {
        "id": "pending_attr_001",
        "source_type": "user_feedback",
        "source_system": "feedback-api",
        "collector_run_id": "collector_run_001",
        "raw_subject_id": "feedback-ext-7788",
        "summary": "无法映射到产品的登录失败反馈",
        "raw_payload": {
          "channel": "support"
        },
        "suggested_product_id": null,
        "suggested_module_code": null,
        "confidence": 0.62,
        "status": "pending",
        "resolution_action": null,
        "resolution_note": null,
        "resolved_product_id": null,
        "resolved_module_code": null,
        "resolved_requirement_id": null,
        "resolved_subject_type": null,
        "resolved_subject_id": null,
        "resolved_by": null,
        "resolved_at": null,
        "created_by": "user_admin",
        "created_at": "2026-06-02T08:00:00Z",
        "updated_at": "2026-06-02T08:00:00Z"
      }
    ],
    "total": 1
  },
  "trace_id": "trace_015"
}
```

产品负责人、研发负责人或管理员可登记待归属项：

```http
POST /api/attribution/pending-items
Content-Type: application/json

{
  "source_type": "user_feedback",
  "source_system": "feedback-api",
  "collector_run_id": "collector_run_001",
  "raw_subject_id": "feedback-ext-7788",
  "summary": "无法映射到产品的登录失败反馈",
  "raw_payload": {
    "channel": "support",
    "message": "login failed after release"
  },
  "suggested_product_id": null,
  "suggested_module_code": null,
  "confidence": 0.62
}
```

将队列项归属到已有上下文：

```http
POST /api/attribution/pending-items/pending_attr_001/resolve
Content-Type: application/json

{
  "resolution_action": "link_existing_context",
  "resolved_product_id": "product_001",
  "resolved_module_code": "login",
  "resolved_requirement_id": "req_001",
  "resolved_subject_type": "user_feedback",
  "resolved_subject_id": "feedback_001",
  "resolution_note": "已确认属于登录模块反馈"
}
```

忽略噪声数据：

```http
POST /api/attribution/pending-items/pending_attr_002/resolve
Content-Type: application/json

{
  "resolution_action": "ignore_as_noise",
  "resolution_note": "重复导入且无业务归属"
}
```

`source_type` 只允许 `gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；`status` 只允许 `pending`、`resolved`、`ignored`；`resolution_action` 只允许 `link_existing_context` 或 `ignore_as_noise`。`collector_run_id` 如传入必须存在；建议产品和归属产品必须为 active；建议模块和归属模块必须属于对应产品；归属需求必须属于归属产品。`link_existing_context` 必须提交 `resolved_product_id`，可选提交模块、需求或目标业务主体；`ignore_as_noise` 不允许提交任何归属上下文字段。队列项一旦 `resolved` 或 `ignored` 即为终态，重复处理返回 `409 PENDING_ATTRIBUTION_STATE_INVALID`。创建、归属和忽略分别写入 `pending_attribution.created`、`pending_attribution.resolved`、`pending_attribution.ignored` 审计事件。队列处理只记录人工归属结果，不自动生成 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议/需求等业务数据。

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
GET /api/insights/items?category=用户反馈&summary=迭代版本&status=open&page=1&page_size=10&sort_by=updated_at&sort_order=desc
```

该接口面向用户洞察主列表聚合用户使用指标、用户反馈和 AI 迭代规划建议，返回统一行字段 `category`、`summary`、`owner`、`status`、`updated_at`、`product_id`、`version_id`、`module_code`、`feature_code`，并保留 `confidence_level`、`planning_cycle`、`priority` 和 `converted_requirement_id` 等迭代建议上下文。支持 `category` 精确筛选，`summary` 文本筛选，`status` 精确筛选，`page/page_size` 服务端分页，`sort_by` 支持 `category/id/owner/status/summary/updated_at`，`sort_order` 支持 `asc/desc`。前端用户洞察主列表必须调用该接口，不再并发拉取使用指标、反馈和迭代建议三个原始接口后本地拼装、排序或分页；登记、处理和决策仍使用对应原始写接口。

反馈状态支持：`open | triaged | linked | resolved | archived`。`POST /api/insights/user-feedback` 允许任意已登录用户登记真实反馈；`PATCH /api/insights/user-feedback/{feedback_id}` 仅允许 `product_owner`、`rd_owner` 或 `admin` 更新状态、标签、情绪、评分和处理备注；GET 支持按 `product_id`、`module_code`、`feature_code`、`status` 和 `created_by` 筛选。反馈写入 `user_feedback` 结构表，并记录 `user_feedback.created` / `user_feedback.updated` 审计事件。

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
POST /api/bugs/batch-update
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

列表响应中的每条 Bug 除 `product_id`、`version_id` 外，还返回 `version_code`、`version_name` 作为页面展示投影；未关联版本时这两个字段为空。

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
    "test_run_id": "test_run_001"
  }
}
```

状态和枚举：

- 来源：`ai_auto_test | ai_post_release | manual_test`。
- 状态：`open | triaged | needs_info | assigned | fixed | verified | closed | reopened`。
- 严重程度：`blocker | critical | major | minor`。
- AI 自动测试来源缺少 `reproduce_steps` 时初始状态为 `needs_info`；人工登记或带复现步骤的 Bug 初始状态为 `open`。
- 提交 `duplicate_of_bug_id` 时重复 Bug 初始状态为 `closed`，并保留主 Bug 关联，避免重复进入修复队列。
- 状态更新必须符合状态机约束，非法跨越返回 `BUG_STATE_INVALID`；创建和更新均写入 `bug.created` 或 `bug.updated` 审计事件。
- Bug 管理工作台必须从真实 `/api/bugs` 响应映射 `version_code`、`version_name`、`reproduce_steps`、`evidence`、`duplicate_of_bug_id`、`requirement_id` 和 `related_task_id`；列表展示迭代版本并支持按版本名、编码或未关联状态过滤；登记弹窗允许录入复现步骤、对象型证据 JSON、关联需求和关联任务，目标版本选项读取同产品未归档迭代版本，支持 `planning`、`active`、`testing` 和 `released`，过滤 `archived`；编辑弹窗允许维护复现步骤、证据 JSON、状态、处理人和重复归并，重复归并候选仅展示同产品 Bug，来源只读展示，不允许把 AI 自动测试或上线后分析来源在前端改写为人工来源；列表勾选多条 Bug 后可打开“批量处理”，调用 `/api/bugs/batch-update` 更新状态、严重级别或处理人，并展示批量结果。

### 软件研发全流程感知

```http
GET /api/lifecycle/context?subject_type=requirement&subject_id=requirement_001&direction=both&include_risks=true
```

查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| subject_type | string | 起点主体类型。当前支持 `product`、`requirement`、`ai_task`、`human_review`、`code_review_report`、`gitlab_mr_snapshot`、`mock_issue`、`knowledge_deposit`、`audit_event`、`bug`、`gitlab_daily_code_metric`、`jenkins_release`、`online_log_metric`、`user_usage_metric`、`user_feedback`、`iteration_plan_suggestion`；未支持类型必须返回 `VALIDATION_ERROR`。 |
| subject_id | string | 起点主体 ID。 |
| product_id | string | 可选，按产品过滤。 |
| version_id | string | 可选，按版本过滤。 |
| module_code | string | 可选，按模块过滤。 |
| direction | string | `upstream | downstream | both`，默认 `both`。 |
| include_risks | boolean | 是否返回风险信号，默认 true。 |

权限规则：当起点是 `ai_task` 时，读取权限与 AI 任务详情一致；当起点是需求、产品或可解析到任务的审计/证据主体时，返回的下游任务、人工确认、报告、知识沉淀、模拟 Issue、真实运营证据和风险信号必须先过滤掉当前用户无权读取的任务链路。

持久化规则：PostgreSQL 运行时聚合前直接读取 repository source rows；接口会把当前查询范围内计算出的上下游关系边同步到 `lifecycle_context_edges`，把风险信号同步到 `lifecycle_risk_signals`；无关系或无风险时保持真实空集合，不生成兜底记录。

响应摘要：

```json
{
  "data": {
    "subject": {
      "type": "requirement",
      "id": "requirement_001"
    },
    "upstream": [],
    "downstream": [
      {
        "subject_type": "ai_task",
        "subject_id": "task_001",
        "relation_type": "generates",
        "summary": "产品详细设计任务",
        "confidence": 1.0
      }
    ],
    "risk_signals": [
      {
        "risk_type": "critical_bug_open",
        "severity": "critical",
        "source_subject_type": "bug",
        "source_subject_id": "bug_001",
        "impact_summary": "阻塞当前版本发布",
        "recommendation": "先完成修复和验证再进入发布评估"
      }
    ],
    "missing_context": [
      "automated_testing",
      "gitlab_daily_code_metric",
      "jenkins_release",
      "online_log_metric",
      "user_usage_metric",
      "user_feedback",
      "iteration_plan_suggestion"
    ],
    "summary": {
      "downstream_count": 1,
      "missing_context_count": 7,
      "risk_count": 1,
      "upstream_count": 0
    }
  },
  "trace_id": "trace_015"
}
```

### 首页 IT 团队看板

```http
GET /api/dashboard/it-team?product_id=product_001&time_range=7d
```

当前实现返回真实聚合指标，来源于产品、需求、AI 任务、待确认 Review、知识文档、知识沉淀、审计事件、Bug、GitLab 每日指标、Jenkins 发布、线上日志、用户使用、用户反馈和迭代规划建议；PostgreSQL 运行时聚合前直接读取 repository source rows，不再通过 repository read snapshot 承载看板聚合；其中 AI 任务、待确认 Review 和知识沉淀计数、列表必须先按任务读权限过滤，`product_id` 存在时所有可归属主体必须按产品归属过滤，`time_range` 存在时运营类指标按可解析的日期或时间窗口过滤，并把当前产品/时间窗口聚合结果通过单条 repository 写入同步到 `dashboard_metric_snapshots`。无数据时返回真实 0 和空数组，不生成占位统计：

```json
{
  "data": {
    "summary": {
      "active_products": 1,
      "requirements": 2,
      "ai_tasks": 1,
      "pending_reviews": 1,
      "knowledge_documents": 1,
      "knowledge_deposits": 0,
      "audit_events": 10,
      "bugs": 1,
      "open_bugs": 1,
      "high_severity_bugs": 1,
      "gitlab_commits": 7,
      "jenkins_releases": 1,
      "online_errors": 12,
      "usage_events": 120,
      "user_feedback": 1,
      "iteration_suggestions": 1
    },
    "bug_status_counts": [
      {"status": "open", "count": 1}
    ],
    "latest_high_severity_bugs": [],
    "gitlab_daily_summary": {
      "metric_count": 1,
      "commit_count": 7,
      "merge_request_count": 2,
      "changed_files": 8,
      "risk_count": 1,
      "average_quality_score": 88.5
    },
    "jenkins_release_status_counts": [
      {"status": "failed", "count": 1}
    ],
    "online_log_summary": {
      "metric_count": 1,
      "request_count": 2400,
      "error_count": 12,
      "error_rate": 0.005,
      "max_p95_latency_ms": 318.5,
      "max_p99_latency_ms": 640.25
    },
    "usage_metric_summary": {
      "metric_count": 1,
      "active_users": 42,
      "event_count": 120,
      "conversion_count": 15,
      "error_count": 2
    },
    "user_feedback_status_counts": [
      {"status": "open", "count": 1}
    ],
    "iteration_suggestion_status_counts": [
      {"status": "suggested", "count": 1}
    ],
    "requirement_status_counts": [
      {"status": "submitted", "count": 1},
      {"status": "designing", "count": 1}
    ],
    "task_status_counts": [
      {"status": "waiting_review", "count": 1}
    ],
    "latest_tasks": [],
    "pending_reviews": [],
    "recent_knowledge_documents": [],
    "recent_audit_events": [],
    "time_range": "7d"
  },
  "trace_id": "trace_014"
}
```

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

### 审计事件

```http
GET /api/audit/events?ai_task_id=task_001
GET /api/audit/events?subject_type=requirement&subject_id=requirement_001
GET /api/audit/events?event_type=review.submitted
GET /api/audit/events?actor_id=user_admin&created_from=2026-05-31T00:00:00Z&created_to=2026-05-31T23:59:59Z
```

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

---

## 核心接口错误语义

| 接口/动作 | HTTP 状态 | 错误码 | 可重试 | 审计要求 | 前端处理建议 |
|-----------|-----------|--------|--------|----------|--------------|
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
| POST `/api/knowledge/documents/{document_id}/retry-index` | 409 | KNOWLEDGE_INDEX_STATE_INVALID | 否 | 记录状态冲突。 | 刷新文档状态；只有索引失败时显示重试。 |
| PATCH knowledge deposit review | 409 | KNOWLEDGE_DEPOSIT_STATE_INVALID | 否 | 记录重复审核或状态冲突。 | 刷新候选状态。 |
| GET/POST model gateway configs | 403 | FORBIDDEN | 否 | 记录越权管理尝试。 | 提示需要 admin 权限。 |
| POST model gateway configs | 400 | VALIDATION_ERROR / MODEL_GATEWAY_CONFIG_INVALID | 否 | 记录配置失败，不记录密钥明文。 | 标出 provider、base_url 或 model 配置错误。 |
| GET `/api/audit/events` | 403 | FORBIDDEN | 否 | 安全审计可采样记录。 | 提示无权限查看审计。 |
| GET `/api/audit/events` | 200 | 无 | 不适用 | 查询本身不强制审计。 | 无结果返回空列表。 |
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
| PRODUCT_VERSION_NOT_SCHEDULABLE | 目标迭代版本不是 `planning` 或 `active`，不能用于新需求排期。 |
| PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED | 迭代版本状态变更必须走状态推进接口，不能通过普通 PATCH 修改。 |
| PRODUCT_VERSION_STATUS_BLOCKED | 迭代版本推进存在阻塞需求，必须处理阻塞项或在允许的阶段强制推进。 |
| PRODUCT_VERSION_STATUS_INVALID | 迭代版本状态或推进路径非法。 |
| REQUIREMENT_STATE_INVALID | 当前需求状态不允许该操作。 |
| TASK_STATE_INVALID | 当前任务状态不允许该操作。 |
| TECHNICAL_SOLUTION_NOT_CONFIRMED | 研发扩展任务缺少同需求、同产品版本下已完成技术方案。 |
| RELEASE_READINESS_NOT_CONFIRMED | 上线后分析任务缺少同需求、同产品版本下已完成发布评估。 |
| REVIEW_VERSION_CONFLICT | 人工确认版本冲突。 |
| MODEL_GATEWAY_FAILED | 模型网关调用失败并导致任务失败。 |
| KNOWLEDGE_DEPOSIT_STATE_INVALID | 知识沉淀候选状态不允许该操作。 |
| KNOWLEDGE_INDEX_FAILED | 知识文档索引失败。 |
| KNOWLEDGE_INDEX_STATE_INVALID | 知识文档当前索引状态不允许重试。 |
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

## 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.1.92 | 2026-06-05 | 需求全链路详情中的 PR/MR 快照证据展示复用风险摘要、diff 文件树和 Review Checklist 字段。 |
| v1.1.91 | 2026-06-05 | GitLab MR / GitHub PR 预览新增 diff 文件树、风险摘要和 Review Checklist 字段，任务中心创建 Code Review 前展示变更范围和检查项。 |
| v1.1.63 | 2026-06-03 | 需求创建允许不指定迭代版本，排期后才能生成 AI 任务，接口状态改为需求池和研发交付状态机。 |
| v1.1.57 | 2026-06-02 | 新增 AI 助手聊天接口和 `/api/assistant/chat` 契约，基于脱敏系统上下文回答 AI Brain 系统信息与项目进展问题。 |
| v1.1.56 | 2026-06-02 | 产品 Git 资源支持 GitHub provider，新增 GitHub PR 预览、PR diff 快照和本地直填凭据解析契约。 |
| v1.1.55 | 2026-06-02 | 所有 PostgreSQL 结构表统一补齐 `created_at`/`updated_at`，并新增 `018_standard_timestamps.sql` 作为既有环境迁移脚本。 |
| v1.1.54 | 2026-06-02 | AI 任务列表新增 `created_from`/`created_to` 查询和摘要时间字段，任务管理页可按所属产品与时间段筛选。 |
| v1.1.50 | 2026-06-02 | AI 任务启动接入真实 LangGraph StateGraph，Graph Run 返回 runtime、node_path 和 checkpoint runtime 元数据。 |
| v1.1.49 | 2026-06-02 | 相关系统支持绑定产品归属，产品配置页可维护相关系统，任务产品上下文只纳入同产品启用相关系统；接口清单补齐需求详情、关闭和 Graph Run 查询。 |
| v1.1.47 | 2026-06-02 | 新增待归属数据队列 API、状态约束、审计事件和 `pending_attribution_items` 持久化契约。 |
| v1.1.46 | 2026-06-02 | 新增采集运行记录 API、状态约束、审计事件和 `collector_runs` 持久化契约。 |
| v1.1.43 | 2026-06-02 | Bug 管理工作台对齐完整生命周期字段，支持复现步骤、证据 JSON、重复归并和只读来源展示。 |
| v1.1.42 | 2026-06-01 | 首页 IT 团队看板按产品过滤知识文档和审计事件。 |
| v1.1.41 | 2026-06-01 | 发布评估和上线后分析任务支持从已确认上游任务创建、保存真实上下文快照、人工确认，并将上线后 Bug 建议写入 `ai_post_release` 来源 Bug。 |
| v1.1.39 | 2026-06-01 | 线上运行日志指标接口支持真实登记、筛选、审计和 `online_log_metrics` PostgreSQL 持久化。 |
| v1.1.38 | 2026-06-01 | Jenkins 发布记录接口支持真实登记、筛选、审计和 `jenkins_release_records` PostgreSQL 持久化。 |
| v1.1.37 | 2026-06-01 | GitLab 每日代码指标接口支持真实登记、筛选、审计和 `gitlab_daily_code_metrics` PostgreSQL 持久化。 |
| v1.1.36 | 2026-06-01 | 用户使用指标接口支持真实登记、筛选、审计和 `user_usage_metrics` PostgreSQL 持久化。 |
| v1.1.35 | 2026-06-01 | 迭代规划建议接口支持基于真实反馈/Bug 证据生成、人工确认、可选转需求和 PostgreSQL 持久化。 |
| v1.1.34 | 2026-06-01 | 用户反馈接口支持真实登记、筛选、状态更新和 `user_feedback` PostgreSQL 持久化。 |
| v1.1.29 | 2026-06-01 | 知识检索不再为缺失 chunk 的 indexed 文档合成结果，索引不一致时返回真实空结果。 |
| v1.1.30 | 2026-06-01 | GitLab MR diff 快照按 repository_id + snapshot_hash 复用已有快照，并记录复用审计事件。 |
| v1.1.28 | 2026-06-01 | 生命周期视图支持从审计主体、Review、Code Review 报告、MR 快照、模拟 Issue 和知识沉淀精准追踪上下文。 |
| v1.1.27 | 2026-05-31 | 角色目录补充业务角色、可见入口和限制边界；知识文档索引失败保留 `index_error` 并支持重试。 |
| v1.1.26 | 2026-05-31 | 生命周期视图和首页看板聚合按任务读权限过滤，避免聚合接口泄露无权任务或 Review。 |
| v1.1.25 | 2026-05-31 | 知识检索升级为权限过滤后的 chunk 级结果，并将 `knowledge_chunks` 纳入结构表持久化。 |
| v1.1.24 | 2026-05-31 | 移除 AI 任务启动本地输出 fallback，无模型网关配置时明确失败，不再生成伪输出。 |
| v1.1.23 | 2026-05-31 | 将相关系统同步到 PostgreSQL `related_systems` 结构表，纳入产品配置恢复范围。 |
| v1.1.22 | 2026-05-31 | 将模拟 Issue 回写同步到 PostgreSQL `mock_issues` 结构表，支持幂等结果恢复。 |
| v1.1.21 | 2026-05-31 | 将 GitLab MR 快照和 Code Review 报告同步到 PostgreSQL 结构表，支持证据链恢复和任务反链回填。 |
| v1.1.12 | 2026-05-31 | 将产品、版本、模块和 Git 资源同步到 PostgreSQL 结构表，推进业务主体细粒度持久化。 |
| v1.1.11 | 2026-05-31 | 明确 MVP 用户角色目录、角色查询接口、用户管理角色选择和 SQL 角色字典。 |
| v1.1.3 | 2026-05-30 | 对齐 PostgreSQL 登录用户表、用户管理接口和 SQL 迁移驱动持久化。 |
| v1.1.2 | 2026-05-30 | 将 Bug 管理 GET/POST/PATCH 从占位升级为 v1.1 基础接口。 |
| v1.1.1 | 2026-05-29 | 将 GitLab 预览和 diff 快照前置到 MVP-A，清理 MVP 角色口径，统一 health trace_id、占位接口和阶段边界。 |
| v1.1.0 | 2026-05-29 | 对齐 PRD/Spec v1.1.0，补充 MVP 角色映射，修正内部 GitLab Git 资源示例和阶段边界。 |
| v1.0.7 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 纳入 v1 MVP，补充 MR 预览、diff 快照、Review 报告查询和不回写 GitLab 的错误语义。 |
| v1.0.6 | 2026-05-29 | 补充用户洞察、用户反馈和 AI 迭代规划建议 API 约定。 |
| v1.0.5 | 2026-05-29 | 补充软件研发全流程感知 API 约定。 |
| v1.0.4 | 2026-05-29 | 补充研发全链路 AI 任务类型和 task_type 契约。 |
| v1.0.3 | 2026-05-29 | 补充 GitLab、线上日志、Jenkins、首页看板和 Bug 管理 API 约定。 |
| v1.0.2 | 2026-05-28 | 补充主体生命周期、需求任务快照、知识索引状态和主体级审计查询约定。 |
| v1.0.1 | 2026-05-27 | 对齐当前实现，修正登录字段、任务输入字段、Markdown 导出、审计查询和配置接口。 |
| v1.0.0 | 2026-05-27 | 初始版本 |

---
最后更新: 2026-06-02
