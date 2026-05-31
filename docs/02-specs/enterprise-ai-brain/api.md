# 企业 AI 大脑平台 API 文档

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.21 |
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

---

## 概述

本文档定义企业 AI 大脑平台 v1 系列的 API 契约。后续版本直接维护本文档。

API 面向 React 工作台，覆盖认证、业务大脑、产品上下文、研发全链路 AI 任务、内部 GitLab MR 代码 Review、软件研发全流程感知、人工确认、Bug 管理、知识中心、模型网关配置、GitLab 代码质量、线上运行日志、Jenkins 发布、用户使用洞察、用户反馈、AI 迭代规划建议、首页 IT 团队看板、模拟回写、Markdown 导出和审计查询。

当前源码实现说明：MVP 骨架已实现认证、产品/需求/任务/Review/知识/审计/导出/GitLab MR 只读预览与 diff 快照、code_review 报告闭环；产品配置、需求、知识文档、Bug、用户管理和模型网关配置已具备当前管理页所需 CRUD 能力，删除接口会对已被需求、任务或关联资源占用的主体返回 `RESOURCE_IN_USE`。MVP 明确定义 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 六个可分配角色，`GET /api/auth/roles` 返回角色目录、职责、数据范围、决策范围、权限点和排序信息，系统管理下的角色管理页面只读展示该目录，用户管理和知识权限配置只能从该目录选择角色，不得自由创建或录入未定义角色。产品管理页面可维护产品版本、模块和 Git 资源；产品、版本、模块、Git 资源、需求台账、AI 任务核心字段、人工确认、Graph Run、检查点、GitLab MR 快照、Code Review 报告、知识文档、知识沉淀候选、审计事件、Bug 记录、模型网关配置和模型调用元数据会同步写入 PostgreSQL 结构表 `products`、`product_versions`、`product_modules`、`product_git_repositories`、`requirements`、`ai_tasks`、`human_reviews`、`graph_runs`、`graph_checkpoints`、`gitlab_mr_snapshots`、`code_review_reports`、`knowledge_documents`、`knowledge_deposits`、`audit_events`、`bugs`、`model_gateway_configs`、`model_gateway_logs`，Git 资源列表只展示凭据是否已配置，不返回凭据引用或 token 明文。GitLab MR 预览和快照读取产品 Git 资源的 `remote_url` 或 `GITLAB_BASE_URL`，并通过 `env:GITLAB_READONLY_TOKEN` 等凭据引用解析只读 token；缺少 GitLab 地址或凭据时返回明确错误，不生成本地假 MR。模型网关配置可在系统管理页面维护，列表和响应只返回 `api_key_configured`，不返回明文密钥、前缀或后缀；active/default 且已配置密钥的 OpenAI-compatible 配置会在任务启动时调用 provider `/chat/completions`，调用日志只保存脱敏元数据。配置缺失密钥或 provider 调用失败时，非 code_review 任务进入 `failed` 并返回 `MODEL_GATEWAY_CONFIG_INVALID` 或 `MODEL_GATEWAY_FAILED`；code_review 报告生成阶段的 provider 调用、响应解析或结构化报告校验失败进入 `failed`，返回 `CODE_REVIEW_EXECUTOR_FAILED` 并写入 `code_review.executor_failed` 审计事件。任务启动不会静默生成本地输出。任务中心已通过真实接口支持启动产品详细设计、确认 Review、基于已确认产品详细设计创建技术方案任务，并对已完成技术方案导出 Markdown。审计与运行页面从真实 `/api/audit/events` 加载列表，行操作提供事件详情和基于审计主体优先的生命周期链路追踪。首页 IT 团队看板已聚合真实产品、需求、AI 任务、待确认 Review、知识文档、知识沉淀和审计摘要。Docker 本地栈默认以 `PERSISTENCE_MODE=postgres` 运行，登录账号读取 PostgreSQL `users` 表，管理员可通过系统管理下的用户管理维护用户，并通过角色管理查看固定角色定义；产品配置、需求台账、AI 任务核心字段、人工确认、Graph 运行态、GitLab MR 快照、Code Review 报告、知识文档、知识沉淀候选、审计事件、Bug 记录和模型网关配置/调用日志从结构表恢复，未完成细粒度迁移的其余业务运行状态仍以 `app_state_snapshots` JSONB 快照兜底持久化。用户洞察和迭代规划的写接口仍属于后续阶段目标；DevOps 和洞察类 GET 接口在未接入真实采集器前返回空集合，不提供占位状态或伪造统计数据。

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
    "message": "需求必须选择产品和目标版本",
    "trace_id": "trace_001"
  }
}
```

未改造完成的框架级异常也必须在响应 Header 或日志中关联同一 `trace_id`。

### 分页参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| page | int | 1 | 页码。当前主要用于任务列表。 |
| page_size | int | 20 | 每页数量，最大 100。 |

### 角色要求

| 能力 | 最低角色 |
|------|----------|
| 查询健康检查 | 无需登录 |
| 登录 | 无需登录 |
| 读取业务/任务/知识/产品配置 | viewer |
| 创建需求、补充信息、取消自己创建或参与的任务 | product_owner 或 rd_owner；creator policy 由实现按产品归属和参与关系收敛 |
| 审批需求、确认产品详细设计、采纳迭代规划建议 | product_owner |
| 创建和启动 AI 任务、确认技术方案 | rd_owner |
| 创建内部 GitLab MR 预览和 diff 快照、创建 code_review 任务、确认 Review 报告 | reviewer 或 rd_owner |
| 审核知识沉淀 | knowledge_owner 或 rd_owner |
| 登记、分派、验证或关闭 Bug | product_owner、rd_owner 或 admin；tester 角色按后续真实测试组织模型扩展 |
| 维护产品、相关系统、模型网关配置、用户账号 | admin |

MVP 系统角色以 `admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 为主；Bug 登记和状态更新先复用 `product_owner`、`rd_owner`、`admin`，`tester`、发布负责人和 IT 管理者写权限按后续真实组织模型扩展。接口鉴权还需要结合产品归属、任务参与关系和主体权限。

| 角色 code | 中文名称 | 主要职责 | 数据范围 | 决策范围 |
|-----------|----------|----------|----------|----------|
| `admin` | 系统管理员 | 用户、角色、模型网关、审计与系统级配置管理 | 全平台系统配置、审计事件和授权业务数据 | 账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍 |
| `product_owner` | 产品负责人 | 产品配置、版本模块、需求审批、任务生成、产品侧交付闭环和 Bug 管理 | 所负责产品、版本和模块下的需求、AI 任务、Bug、知识引用和看板摘要 | 需求审批、产品详细设计确认、迭代规划采纳和产品侧优先级决策 |
| `rd_owner` | 研发负责人 | 研发任务启动、技术方案确认、Code Review 任务创建、Bug 处理和研发知识沉淀 | 授权产品下的 AI 任务、技术方案、GitLab 只读快照、Bug 和研发知识 | 技术方案确认、研发任务推进、Bug 处理和研发知识沉淀决策 |
| `reviewer` | 评审负责人 | 高影响 AI 输出、需求分析、设计方案和内部 GitLab MR Code Review 的人工确认 | 分配给评审人的 AI 任务、Review 检查点、MR 只读快照和评审报告 | 对高影响 AI 输出执行批准、修改后批准、拒绝或要求补充信息 |
| `knowledge_owner` | 知识负责人 | 知识文档导入、权限角色维护、知识检索治理和知识沉淀审核 | 知识文档、chunk、检索结果、权限角色和知识沉淀候选 | 知识导入、权限配置、索引治理和沉淀候选审核 |
| `viewer` | 查看者 | 查看有权限访问的工作台数据、任务结果、知识和看板摘要 | 授权范围内的列表、详情、任务结果、知识检索结果和看板摘要 | 无写入或审批决策权限 |

### 主体级 API 约定

产品、需求、AI 任务、Bug、知识中心、研发运营指标/看板和用户洞察/迭代规划是独立业务主体或独立运营视图。API 设计应遵循以下约定：

- 产品接口维护长期主数据，归档版本不得用于新需求或新任务。
- 需求接口维护业务事实和审批状态，生成任务时必须把需求快照写入任务输入。
- AI 任务接口维护任务类型、执行状态、人工确认、回写、导出和运行结果，不承担产品主数据维护。
- 内部 GitLab MR 代码 Review 接口只读取授权 MR 元信息和 diff 快照，生成 AI Brain 内部 Review 报告，不提供 GitLab 评论、审批、request changes、合并或分支变更回写能力。
- 知识接口支持独立导入、索引状态查询、权限过滤检索、索引失败重试和沉淀审核。
- Bug 接口支持 AI 自动测试和人工测试两类来源的登记、分派、修复、验证、关闭和重复归并。
- DevOps/运营接口按产品归属暴露 GitLab 每日代码质量、Jenkins 发布、线上运行日志、用户使用、用户反馈、迭代规划建议和首页 IT 团队看板指标。
- 全流程感知接口按产品、版本、模块、需求、AI 任务或任一主体查询上下文关系、上下游影响和风险信号。
- 审计接口支持按 `ai_task_id`、`subject_type`、`subject_id`、`event_type`、`actor_id` 和创建时间范围过滤。
- 迭代规划建议接口只生成建议和采纳记录，不能绕过产品负责人确认自动创建正式需求或调整迭代排期。

---

## 接口清单

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Health | GET | `/health` | 健康检查。 |
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
| Product | POST | `/api/products` | 创建产品。 |
| Product | PATCH | `/api/products/{product_id}` | 更新产品。 |
| Product | DELETE | `/api/products/{product_id}` | 删除未被需求、AI 任务或 Bug 占用的产品；无业务依赖时级联清理该产品的版本、模块和 Git 资源配置。 |
| Product Version | GET | `/api/products/{product_id}/versions` | 产品版本列表。 |
| Product Version | POST | `/api/products/{product_id}/versions` | 创建产品版本。 |
| Product Version | PATCH | `/api/product-versions/{version_id}` | 更新产品版本。 |
| Product Version | DELETE | `/api/product-versions/{version_id}` | 删除未被需求、AI 任务或 Bug 占用的产品版本。 |
| Product Module | GET | `/api/products/{product_id}/modules` | 产品模块列表。 |
| Product Module | POST | `/api/products/{product_id}/modules` | 创建产品模块。 |
| Product Module | PATCH | `/api/product-modules/{module_id}` | 更新产品模块。 |
| Product Module | DELETE | `/api/product-modules/{module_id}` | 删除未被需求、AI 任务或 Bug 占用的产品模块。 |
| Product Git | GET | `/api/products/{product_id}/git-repositories` | 产品 Git 资源列表。 |
| Product Git | POST | `/api/products/{product_id}/git-repositories` | 创建产品 Git 资源。 |
| Product Git | PATCH | `/api/product-git-repositories/{repo_id}` | 更新产品 Git 资源。 |
| Product Git | DELETE | `/api/product-git-repositories/{repo_id}` | 删除产品 Git 资源配置。 |
| System | GET | `/api/system/related-systems` | 相关系统列表。 |
| System | POST | `/api/system/related-systems` | 创建相关系统。 |
| System | PATCH | `/api/system/related-systems/{system_id}` | 更新相关系统。 |
| System | DELETE | `/api/system/related-systems/{system_id}` | 删除相关系统配置。 |
| System | GET | `/api/system/model-gateway-configs` | 模型网关配置列表。 |
| System | POST | `/api/system/model-gateway-configs` | 创建模型网关配置。 |
| System | PATCH | `/api/system/model-gateway-configs/{config_id}` | 更新模型网关配置。 |
| System | DELETE | `/api/system/model-gateway-configs/{config_id}` | 删除模型网关配置。 |
| System | GET | `/api/model-gateway/logs` | 查询模型调用元数据日志，不返回完整 prompt 或输出。 |
| Requirement | GET | `/api/requirements` | 需求列表。 |
| Requirement | POST | `/api/requirements` | 新增待审批需求。 |
| Requirement | PATCH | `/api/requirements/{requirement_id}` | 更新待审批或已驳回需求。 |
| Requirement | DELETE | `/api/requirements/{requirement_id}` | 删除未生成任务的需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/approve` | 审批通过需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/reject` | 驳回需求。 |
| Requirement | POST | `/api/requirements/{requirement_id}/generate-task` | 审批后生成 AI 任务。 |
| AI Task | GET | `/api/ai-tasks` | 任务列表，支持按状态和任务类型筛选。 |
| AI Task | POST | `/api/ai-tasks` | 低层任务创建接口。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/start` | 启动或重新启动任务。 |
| AI Task | GET | `/api/ai-tasks/{task_id}` | 任务详情。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/more-info` | 提交补充信息。 |
| AI Task | POST | `/api/ai-tasks/{task_id}/cancel` | 取消任务。 |
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
| Knowledge | POST | `/api/knowledge/search` | 知识检索。 |
| Knowledge | GET | `/api/knowledge/deposits` | 知识沉淀候选列表。 |
| Knowledge | POST | `/api/knowledge/deposits/{deposit_id}/approve` | 采纳知识沉淀。 |
| Knowledge | POST | `/api/knowledge/deposits/{deposit_id}/reject` | 驳回知识沉淀。 |
| Output | GET | `/api/writeback/results/{task_id}` | 查询模拟回写结果。 |
| Output | POST | `/api/writeback/results/{task_id}` | 显式生成或复用模拟回写结果，使用幂等键避免重复 Issue。 |
| Output | GET | `/api/export/tasks/{task_id}/markdown` | 导出 Markdown 方案。 |
| Audit | GET | `/api/audit/events` | 查询审计事件。 |
| DevOps | GET | `/api/devops/gitlab/daily-code-metrics` | 查询 GitLab 每日提交和代码质量审核结果。 |
| GitLab Review | GET | `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview` | 预览内部 GitLab MR 元信息。 |
| GitLab Review | POST | `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot` | 拉取 MR 元信息和 diff，生成 code_review 输入快照。 |
| Code Review | GET | `/api/ai-tasks/{task_id}/code-review-report` | 查询内部 GitLab MR 代码 Review 报告、执行器信息和确认状态。 |
| DevOps | GET | `/api/devops/jenkins/releases` | 查询 Jenkins 发布记录。 |
| Ops | GET | `/api/ops/online-log-metrics` | 查询线上运行日志运营指标。 |
| Bug | GET | `/api/bugs` | 查询 Bug 列表。 |
| Bug | POST | `/api/bugs` | v1.1 基础接口，登记 AI 自动测试或人工测试 Bug。 |
| Bug | PATCH | `/api/bugs/{bug_id}` | v1.1 基础接口，更新 Bug 状态、分派人、复现信息或重复归并关系。 |
| Bug | DELETE | `/api/bugs/{bug_id}` | 删除 Bug 记录。 |
| Lifecycle | GET | `/api/lifecycle/context` | 查询软件研发全流程上下文关系、上下游影响和风险信号。 |
| Dashboard | GET | `/api/dashboard/it-team` | 查询首页 IT 团队看板。 |
| Insights | GET | `/api/insights/usage-metrics` | 查询用户使用指标。 |
| Insights | GET | `/api/insights/user-feedback` | 查询用户反馈列表。 |
| Insights | POST | `/api/insights/user-feedback` | v1.2 目标接口；当前实现未开放写入。 |
| Insights | PATCH | `/api/insights/user-feedback/{feedback_id}` | v1.2 目标接口；当前实现未开放写入。 |
| Planning | GET | `/api/planning/iteration-suggestions` | 查询 AI 迭代规划建议。 |
| Planning | POST | `/api/planning/iteration-suggestions` | v1.2 目标接口；当前实现未开放写入。 |
| Planning | POST | `/api/planning/iteration-suggestions/{suggestion_id}/decide` | v1.2 目标接口；当前实现未开放写入。 |

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
  "model_gateway": "local_fallback",
  "trace_id": "trace_health_001"
}
```

`status` 在 PostgreSQL 或 Redis 异常时为 `degraded`。

字段枚举：

| 字段 | 当前取值 |
|------|----------|
| status | `ok` 或 `degraded` |
| postgres | `ok` 或 `error` |
| redis | `ok` 或 `error` |
| model_gateway | `configured` 或 `local_fallback` |

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
        "responsibilities": [
          "管理本地用户账号、状态和角色分配。",
          "维护 OpenAI-compatible 模型网关配置。",
          "查看审计与运行状态，处理系统级异常。"
        ],
        "data_scope": "全平台系统配置、审计事件和授权业务数据。",
        "decision_scope": "账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍。",
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
        "config": {}
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

维护接口：

```http
POST /api/products
PATCH /api/products/{product_id}
POST /api/products/{product_id}/versions
PATCH /api/product-versions/{version_id}
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
- 版本状态：`planning | active | archived`。
- Git 资源类型：`code | docs | prd | test`。
- Git 资源状态：`active | inactive`。
- MVP 内部 GitLab MR 代码 Review 只使用 `git_provider=gitlab` 且带有 `project_id` 或 `project_path` 的只读仓库绑定；`credential_ref` 只能引用服务端密钥或密文，API 响应只返回 `credential_ref_configured`，不返回密钥引用或明文 token。
- 前端产品配置弹窗可提交 `credential_ref`，编辑时留空表示保留服务端已有凭据；列表只显示“已配置/未配置”状态。
- 归档版本不可用于新需求和新 AI 任务，历史任务继续使用生成时保存的产品上下文快照。

### 平台配置

相关系统：

```http
GET /api/system/related-systems?active_only=true
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
  "status": "active",
  "display_order": 100
}
```

模型网关配置：

```http
GET /api/system/model-gateway-configs
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
  "timeout_seconds": 60,
  "max_retries": 1,
  "status": "active",
  "is_default": true
}
```

响应不会返回明文 `api_key`、密钥前缀或后缀，只返回 `api_key_configured`。

模型调用日志：

```http
GET /api/model-gateway/logs?ai_task_id=task_001&status=succeeded
```

模型调用日志只返回 `provider`、`model`、`purpose`、`tokens`、`latency_ms`、`status`、`error`、`created_at` 和 `model_gateway_config_id` 等元数据，不返回完整 prompt、完整模型输出或密钥。

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

- 新增后状态为 `pending_approval`。
- 需求可支持 `draft | pending_approval | approved | rejected | task_created | closed` 生命周期；v1 API 可先从 `pending_approval` 开始。
- `input.product_id` 和 `input.version_id` 必填，且必须指向启用产品和未归档版本。
- 审批通过调用 `POST /api/requirements/{requirement_id}/approve`。
- 只有 `approved` 需求可以调用 `POST /api/requirements/{requirement_id}/generate-task`。
- 生成任务后需求状态为 `task_created`，表示已至少创建一个关联任务；该状态不阻止继续创建满足前置依赖的技术方案、code_review 或后续阶段任务。需求仍保留原始输入和审批结论。
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
- `code_review` 任务需要已确认技术方案和内部 GitLab MR diff 快照，默认通过 MR 预览/快照流程和低层 `POST /api/ai-tasks` 创建，不由需求审批流一次性自动生成。

生成任务响应：

```json
{
  "data": {
    "id": "requirement_001",
    "status": "task_created",
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
| `code_review` | 内部 GitLab MR 代码 Review。 |
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
  "brain_app_code": "rd_brain",
  "task_type": "product_detail_design",
  "title": "支持企业知识库导入 Markdown",
  "priority": "P1",
  "input": {
    "background": "团队知识散落在 Markdown 文档中",
    "goal": "导入后可被研发大脑检索引用",
    "constraints": ["v1 使用 PostgreSQL + pgvector"],
    "product_id": "product_001",
    "version_id": "version_001",
    "module_codes": ["knowledge"],
    "related_system_codes": ["rd"]
  }
}
```

`code_review` 任务请求体示例：

```json
{
  "brain_app_code": "rd_brain",
  "task_type": "code_review",
  "title": "Review MR !42: 知识导入",
  "priority": "P0",
  "input": {
    "product_id": "product_001",
    "version_id": "version_001",
    "module_codes": ["knowledge"],
    "requirement_id": "requirement_001",
    "technical_solution_task_id": "task_tech_001",
    "gitlab_mr_snapshot_id": "mr_snapshot_001"
  }
}
```

规则：

- `title` 必填。
- `input.product_id` 和 `input.version_id` 必填，且必须指向可用产品和未归档版本。
- `input.module_codes` 可选；提供时必须属于所选产品且处于启用状态。
- 后端会把产品、版本、模块和 Git 资源解析到 `input.product_context`。
- `task_type = code_review` 时，`input.gitlab_mr_snapshot_id` 必填；快照必须先通过 MR 预览/快照接口生成，并且当前用户必须对快照所属产品 Git 资源和 MR 具备 Review 权限。
- 后端创建 code_review 任务时只引用已有不可变快照，不在任务创建接口中重复拉取 MR diff。
- code_review 任务只归档 AI Brain 内部 Review 报告，不向 GitLab 回写评论、审批状态、request changes、合并状态或分支变更。
- 前端默认通过需求审批后的 `generate-task` 创建 AI 任务，不直接调用该低层接口。

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
GET /api/ai-tasks?status=waiting_review&task_type=code_review&page=1&page_size=20
```

可按 `status`、`task_type`、`product_id`、`requirement_id` 查询。
列表只返回当前用户有权读取的任务摘要，不返回 `requirement_snapshot`、`product_context`、`input_json` 或 `output_json` 等任务内部上下文。

启动任务：

```http
POST /api/ai-tasks/{task_id}/start
```

当前实现会同步运行到下一个人工确认点或失败状态。若存在 active/default 的 OpenAI-compatible 模型网关配置且已配置 API Key，启动时调用 `{base_url}/chat/completions` 并要求 `response_format={"type":"json_object"}`；无 active/default 配置时仅允许本地开发 fallback。active/default 配置缺失 API Key 返回 `MODEL_GATEWAY_CONFIG_INVALID`；非 code_review 任务的 provider 调用、响应解析或网络失败返回 `MODEL_GATEWAY_FAILED`；code_review 报告生成阶段的 provider 调用、响应解析或结构化报告校验失败返回 `CODE_REVIEW_EXECUTOR_FAILED`。这些失败都会把任务置为 `failed`，并保留模型调用元数据日志。
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
- `gitlab_mr_snapshot`: `code_review` 任务的内部 GitLab MR 输入快照，包括 project_id 或 project_path、mr_iid、标题、作者、source/target branch、commit sha 或 diff refs、变更文件摘要、diff 存储引用、GitLab Web URL 和快照时间。

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

### 内部 GitLab MR 代码 Review

MR 预览：

```http
GET /api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview
```

响应：

```json
{
  "data": {
    "repository_id": "repo_001",
    "project_id": "123",
    "mr_iid": 42,
    "title": "feat: add knowledge import",
    "author": "alice",
    "source_branch": "feature/knowledge-import",
    "target_branch": "main",
    "changed_file_count": 8,
    "diff_refs": {
      "base_sha": "abc123",
      "head_sha": "def456"
    },
    "web_url": "https://gitlab.internal/group/project/-/merge_requests/42"
  },
  "trace_id": "trace_gitlab_001"
}
```

MR diff 快照是 code_review 任务的唯一输入快照来源。MVP-A 必须支持内部 GitLab 只读项目绑定、MR 预览和 diff 快照生成；MVP-B 在快照基础上创建正式 `code_review` 任务并生成 Review 报告。任务中心前端应先读取产品 Git 资源，再预览 MR、生成快照，最后用 `gitlab_mr_snapshot_id` 创建 `code_review` 任务；任务创建接口不得静默重新拉取或覆盖已有快照。后端通过 GitLab API 读取 `GET /api/v4/projects/{project}/merge_requests/{iid}` 和 `.../{iid}/changes`，其中 `project` 来自产品 Git 资源的 `project_path` 或 `project_id`。`remote_url` 用于推导 GitLab base URL，也可由 `GITLAB_BASE_URL` 提供；`credential_ref` 推荐使用 `env:GITLAB_READONLY_TOKEN`，响应不得返回凭据值。MR diff、变更文件数或单文件 diff 行数超过限制时返回 `GITLAB_MR_DIFF_TOO_LARGE`，不创建快照，并记录 `gitlab_mr.snapshot_failed` 审计事件，payload 包含 `diff_size_bytes`、`diff_limit_bytes`、`changed_file_count`、`changed_file_limit`、`file_diff_line_count`、`file_diff_line_limit`、`file_path`、`mr_iid`、`requirement_id` 和 `technical_solution_task_id`。

生成 MR diff 快照：

```http
POST /api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot
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
- Review 报告经人工确认或修改后采纳后才可归档为正式结论。
- v1 MVP 不提供 GitLab 评论、审批状态、request changes、合并状态或分支变更回写接口。
- 首页 IT 团队看板返回当前业务数据聚合，不返回空集合占位；研发运营看板和用户洞察/迭代规划在未接入真实采集器前返回空集合响应，响应必须包含 `items` 和 `total`，不得返回占位状态或伪造统计数据。Bug 管理已进入 v1.1 基础实现，不再使用空集合替代业务数据。

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
  "content": "# 研发需求拆解模板...",
  "source": "manual",
  "tags": ["研发流程", "任务拆解"],
  "brain_app_codes": ["rd_brain"],
  "system_codes": ["knowledge"],
  "permission_level": "rd"
}
```

查询文档：

```http
GET /api/knowledge/documents?keyword=研发&doc_type=system&index_status=indexed
```

知识文档索引状态建议支持：`importing | pending_index | indexed | index_failed | archived`。索引失败时响应应包含错误码或错误摘要，便于前端提供重试入口。

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
        "document_id": "doc_001",
        "title": "研发需求拆解模板",
        "content": "研发需求拆解应包含背景、业务目标...",
        "source": {
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

前端知识中心提供“知识检索”弹窗，提交真实 `/api/knowledge/search` 请求并展示可访问结果的标题、来源和内容摘要；无结果时展示真实空状态，不回退到示例数据。

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

当前实现尚未接入真实采集器时返回空集合；不得返回伪造统计数据：

```json
{
  "data": {
    "items": [],
    "total": 0
  },
  "trace_id": "trace_011"
}
```

Jenkins 发布记录：

```http
GET /api/devops/jenkins/releases?product_id=product_001&version_id=version_001
```

当前实现尚未接入真实 Jenkins 采集器时返回空集合；不得返回伪造发布数据：

```json
{
  "data": {
    "items": [],
    "total": 0
  },
  "trace_id": "trace_012"
}
```

线上运行日志运营指标：

```http
GET /api/ops/online-log-metrics?product_id=product_001&environment=prod&from=2026-05-28T00:00:00Z&to=2026-05-28T23:59:59Z
```

当前实现尚未接入线上日志采集器时返回空集合；不得返回伪造运行指标：

```json
{
  "data": {
    "items": [],
    "total": 0
  },
  "trace_id": "trace_013"
}
```

### 用户洞察与迭代规划

用户使用指标：

```http
GET /api/insights/usage-metrics?product_id=product_001&module_code=knowledge&feature_code=search&user_segment=rd&from=2026-05-01T00:00:00Z&to=2026-05-28T23:59:59Z
```

当前实现尚未接入真实用户行为采集器时返回空集合；不得返回伪造使用指标：

```json
{
  "data": {
    "items": [],
    "total": 0
  },
  "trace_id": "trace_016"
}
```

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

反馈状态建议支持：`open | triaged | linked | resolved | archived`。

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
            "subject_type": "usage_metric",
            "subject_id": "usage_001",
            "summary": "搜索转化率 28 天下降 12%"
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

- 迭代规划建议状态建议支持 `draft | suggested | accepted | edited_accepted | rejected | converted_to_requirement`。
- `POST /api/planning/iteration-suggestions` 只生成建议，不自动创建正式需求。
- 只有 `rd_owner`、产品负责人等价权限或更高权限的用户可以调用 decide 接口。
- 只有 `accepted` 或 `edited_accepted` 且 `convert_to_requirement=true` 时，系统才可以创建正式需求。
- 使用数据不足或反馈样本过少时，响应必须标识 `confidence_level = low` 或等价证据不足字段。

### Bug 管理

查询和登记：

```http
GET /api/bugs?product_id=product_001&status=open
POST /api/bugs
PATCH /api/bugs/{bug_id}
```

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

- 来源：`ai_auto_test | manual_test`。
- 状态：`open | triaged | needs_info | assigned | fixed | verified | closed | reopened`。
- 严重程度：`blocker | critical | major | minor`。
- AI 自动测试来源缺少 `reproduce_steps` 时初始状态为 `needs_info`；人工登记或带复现步骤的 Bug 初始状态为 `open`。
- 提交 `duplicate_of_bug_id` 时重复 Bug 初始状态为 `closed`，并保留主 Bug 关联，避免重复进入修复队列。
- 状态更新必须符合状态机约束，非法跨越返回 `BUG_STATE_INVALID`；创建和更新均写入 `bug.created` 或 `bug.updated` 审计事件。

### 软件研发全流程感知

```http
GET /api/lifecycle/context?subject_type=requirement&subject_id=requirement_001&direction=both&include_risks=true
```

查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| subject_type | string | 起点主体类型，例如 `product`、`requirement`、`ai_task`、`git_commit`、`code_review`、`test_run`、`bug`、`release`、`online_log_event`、`usage_metric`、`user_feedback`、`iteration_plan_suggestion`。 |
| subject_id | string | 起点主体 ID。 |
| product_id | string | 可选，按产品过滤。 |
| version_id | string | 可选，按版本过滤。 |
| module_code | string | 可选，按模块过滤。 |
| direction | string | `upstream | downstream | both`，默认 `both`。 |
| include_risks | boolean | 是否返回风险信号，默认 true。 |

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
    ]
  },
  "trace_id": "trace_015"
}
```

### 首页 IT 团队看板

```http
GET /api/dashboard/it-team?product_id=product_001&time_range=7d
```

当前实现返回 MVP 真实聚合指标，来源于产品、需求、AI 任务、待确认 Review、知识文档、知识沉淀和审计事件；未接入的 DevOps、用户洞察、发布和线上运行类指标不得伪造成看板数据：

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
      "audit_events": 10
    },
    "requirement_status_counts": [
      {"status": "pending_approval", "count": 1},
      {"status": "task_created", "count": 1}
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
| GET `/api/ai-tasks/{task_id}` | 403/404 | FORBIDDEN / NOT_FOUND | 否 | 无权限访问不写高频审计，安全审计可采样记录。 | 显示无权限或不存在，不泄露敏感主体。 |
| POST `/api/reviews/{review_id}/approve` | 409 | REVIEW_VERSION_CONFLICT | 是，刷新后重试 | 记录冲突事件和提交 version。 | 提示确认内容已变化，刷新后重新决策。 |
| POST `/api/reviews/{review_id}/edit-approve` | 400/409 | VALIDATION_ERROR / REVIEW_VERSION_CONFLICT | 视错误而定 | 成功和冲突均记录。 | 保留用户编辑内容，刷新后允许重新提交。 |
| POST `/api/reviews/{review_id}/reject` | 400 | VALIDATION_ERROR | 否 | 成功必须记录 rejection reason。 | 要求填写驳回原因。 |
| POST `/api/reviews/{review_id}/request-more-info` | 400 | VALIDATION_ERROR | 否 | 成功必须记录补充问题。 | 要求填写明确问题。 |
| GET GitLab MR preview | 404/403 | GITLAB_MR_NOT_FOUND / FORBIDDEN | 否 | 记录只读预览失败原因。 | 提示检查项目绑定、MR IID 和权限。 |
| POST GitLab MR snapshot | 413 | GITLAB_MR_DIFF_TOO_LARGE | 否 | 记录 `gitlab_mr.snapshot_failed`，包含 diff_size_bytes、changed_file_count、file_diff_line_count 和限制。 | 提示拆分 MR 或缩小范围。 |
| POST GitLab MR snapshot | 502/503 | DEVOPS_SOURCE_UNAVAILABLE | 是 | 记录 GitLab API 超时、限流或不可用。 | 提示稍后重试，保留 MR 输入。 |
| GET `/api/ai-tasks/{task_id}/code-review-report` | 404 | NOT_FOUND | 否 | 不要求审计。 | 显示报告尚未生成或不存在。 |
| code-review 执行器生成报告 | 502/503 | CODE_REVIEW_EXECUTOR_FAILED | 是 | 记录 executor_type、executor_name、阶段和 retryable。 | 显示执行器失败，可重跑或联系管理员。 |
| POST `/api/knowledge/import` | 400 | VALIDATION_ERROR | 否 | 成功和失败均记录文档来源。 | 标出文件类型、大小或权限错误。 |
| POST `/api/knowledge/search` | 400 | VALIDATION_ERROR | 否 | 可记录 query_hash，不记录原始敏感 query。 | 提示 query 或 top_k 无效。 |
| POST `/api/knowledge/search` | 200 | 无 | 不适用 | 不记录完整 query，记录 result_count 和 latency。 | 无结果时显示空状态，不暗示系统错误。 |
| PATCH knowledge deposit review | 409 | KNOWLEDGE_DEPOSIT_STATE_INVALID | 否 | 记录重复审核或状态冲突。 | 刷新候选状态。 |
| GET/POST model gateway configs | 403 | FORBIDDEN | 否 | 记录越权管理尝试。 | 提示需要 admin 权限。 |
| POST model gateway configs | 400 | VALIDATION_ERROR / MODEL_GATEWAY_CONFIG_INVALID | 否 | 记录配置失败，不记录密钥明文。 | 标出 provider、base_url 或 model 配置错误。 |
| GET `/api/audit/events` | 403 | FORBIDDEN | 否 | 安全审计可采样记录。 | 提示无权限查看审计。 |
| GET `/api/audit/events` | 200 | 无 | 不适用 | 查询本身不强制审计。 | 无结果返回空列表。 |

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| VALIDATION_ERROR | 请求参数错误。 |
| UNAUTHORIZED | 未登录、账号密码错误或 Token 无效。 |
| TOKEN_EXPIRED | Token 已过期。 |
| FORBIDDEN | 角色权限不足。 |
| NOT_FOUND | 资源不存在。 |
| REQUIREMENT_STATE_INVALID | 当前需求状态不允许该操作。 |
| TASK_STATE_INVALID | 当前任务状态不允许该操作。 |
| REVIEW_VERSION_CONFLICT | 人工确认版本冲突。 |
| MODEL_GATEWAY_FAILED | 模型网关调用失败并导致任务失败。 |
| KNOWLEDGE_DEPOSIT_STATE_INVALID | 知识沉淀候选状态不允许该操作。 |
| KNOWLEDGE_INDEX_FAILED | 知识文档索引失败。 |
| BUG_STATE_INVALID | 当前 Bug 状态不允许该操作。 |
| DEVOPS_SOURCE_UNAVAILABLE | GitLab、Jenkins、线上日志、用户使用或用户反馈数据源不可用。 |
| GITLAB_MR_NOT_FOUND | 内部 GitLab Merge Request 不存在或不可访问。 |
| GITLAB_MR_DIFF_TOO_LARGE | MR diff 超过 v1 MVP code_review 处理限制，需要拆分 MR 或缩小范围。 |
| CODE_REVIEW_EXECUTOR_FAILED | code-review 执行器调用失败。 |
| GITLAB_WRITEBACK_NOT_SUPPORTED | v1 MVP 不支持向 GitLab 回写评论、审批状态、request changes、合并状态或分支变更。 |
| PRODUCT_MAPPING_REQUIRED | 采集数据缺少产品归属，无法进入产品级统计。 |
| ITERATION_PLAN_EVIDENCE_INSUFFICIENT | 迭代规划建议证据不足，只能生成低置信度建议。 |
| ITERATION_PLAN_STATE_INVALID | 当前迭代规划建议状态不允许确认、驳回或转需求。 |
| ITERATION_PLAN_CONFIRMATION_REQUIRED | AI 建议必须经过产品负责人确认后才能转为正式需求或进入迭代计划。 |
| LIFECYCLE_SUBJECT_REQUIRED | 全流程感知查询缺少 subject_type/subject_id 或 product_id 等查询起点。 |

---

## 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
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
最后更新: 2026-05-31
