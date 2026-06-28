# 系统治理、RBAC 与平台配置

> 来源：../spec.md 与 ../rbac-redesign.md。本文承接系统治理、权限、模型网关、知识和 DB-first 迁移约束的业务域规格导航。

## 职责边界

- 系统治理维护用户、角色、菜单、权限点、数据范围、审计和平台配置。
- RBAC 以服务端权限点和数据范围为强制边界，前端菜单可见性只作为导航体验，不替代后端鉴权。
- 模型网关提供 Chat 和 Embedding 能力配置边界，业务模块不得直接调用 provider SDK。
- 知识管理负责文档、chunk、索引、检索权限和知识沉淀。
- DB-first 迁移要求生产读写以 PostgreSQL repository/read model 为事实源，`MemoryStore` 只能作为测试 helper。

## 关键数据

- `users`、`roles`、`permissions`、`menu_resources`、`role_permissions`、`role_menu_grants`、`role_scope_grants`
- `model_gateway_configs`、`model_gateway_logs`
- `knowledge_documents`、`knowledge_chunks`、`knowledge_deposits`
- `audit_events`

## 关键 API 与页面

- 用户管理、角色管理、菜单管理、模型网关、知识中心和审计与运行。
- RBAC 策略矩阵：`GET /api/system/permissions/matrix`
- 用户权限诊断：`GET /api/system/permissions/diagnostics`
- 菜单树：`GET /api/auth/me`
- 模型网关：`/api/system/model-gateway-configs`

## 当前落地要求

- 角色管理页展示权限审计矩阵，按角色聚合权限点、菜单入口、数据范围、高风险权限和菜单权限缺口。
- 角色管理页必须在权限审计矩阵前提供“角色权限与范围预览”，复用矩阵结果展示全局/产品范围覆盖、未配置范围、高风险权限和菜单权限缺口；角色列表和角色详情必须展示 `role_scope_grants` 的范围类型、范围 ID 和访问级别，便于分配前快速识别越权或漏配风险。
- 角色管理页的角色列表属于管理型列表，`GET /api/system/roles` 必须在服务端完成分页、角色/分类/业务角色/可见入口/权限点/状态筛选、白名单排序和 `query/performance` 观测，前端不得拉全量角色后本地分页过滤。
- 角色管理页提供用户权限诊断工具，按用户 ID、菜单路径、权限点和数据范围解释“能看/不能看”的服务端判定依据。
- 系统管理核心 API 必须服务端校验权限点而不是固定 admin 角色：`/api/users` 需要 `system.users.manage`，`/api/system/model-gateway-configs` 和 `/api/model-gateway/logs` 需要 `system.model_gateway.manage`，`/api/audit/events` 需要 `audit.read`；`admin` 与 `system.admin` 仅作为 `require_permissions` 的兼容超级授权来源，未授予对应权限点的普通角色必须返回 403。
- 模型网关配置列表属于系统管理型列表；`GET /api/system/model-gateway-configs` 传入 `page/page_size` 时必须优先走 PostgreSQL 模型网关配置 count/page read model，按配置名、Provider、状态、默认配置、Chat/Embedding 模型和 Embedding 连接模式在数据库侧筛选排序，响应继续脱敏密钥并返回 `query/performance`。
- 模型调用日志属于执行排障型管理列表；`GET /api/model-gateway/logs` 传入 `page/page_size` 时必须优先走 PostgreSQL 模型日志 count/page read model，支持 AI 任务、用途、状态筛选和 `created_at/id/purpose/status/provider/model/latency_ms/ai_task_id` 白名单排序，并返回 `query/performance`；无分页请求仅作为历史兼容和轻量诊断兜底。
- 菜单资源由数据库维护名称、父级、路由、图标、排序、状态和页面访问权限点，但前端只能加载静态注册路由组件。
- 菜单资源与前端路由必须持续一致：active 的 `group/page` 菜单 path 必须存在于前端 `routes.ts`，研发任务、定时作业、插件管理、AI 能力配置、执行诊断、代码巡检和菜单管理等关键入口不得回退到旧路径；该约束由 `test_menu_route_consistency.py` 作为后端回归门禁。
- P0 管理型路由必须纳入“路由 -> 权限点 -> 数据范围”契约矩阵：需求、Bug、知识文档、代码巡检、定时作业、插件配置、插件调用日志、AI 执行器 Runner 和 Runner 任务均需验证 OpenAPI 路由存在、无权限用户返回 403；带业务归属的数据列表必须在服务端按产品 scope 或知识空间 scope 过滤，不能依赖菜单隐藏或前端过滤兜底。
- 审计列表每条记录必须同时保留业务生命周期“链路追踪”入口和运行排障“执行诊断”入口；执行诊断入口按审计 ID 生成 `source_type=audit_event` 深链，排查模型、插件、Runner、定时作业或代码巡检等运行链路时不得只停留在审计详情 JSON。
- 执行诊断列表的 `source_type` 筛选面向任一来源节点，前端统一展示为“来源类型”，不得误标为“根类型”；所有来源深链必须同时携带 `source_id` 和 `source_type`。
- 管理列表型接口必须在 SQL/repository/read model 层完成分页、排序和筛选，并返回查询性能元数据；前端统一列表底座需展示查询耗时，`performance.slow=true` 时显示慢查询阈值提示并指引结合接口 trace、筛选条件和数据库慢查询日志排查。需求、任务、Bug、用户洞察、代码巡检、角色、产品、迭代版本、知识、审计、模型网关、执行诊断、日志监控、用户和 AI 助手草案任务台等远程分页列表必须透传该性能元数据，不得在页面侧静默丢弃。
- 知识中心知识文档主列表属于管理型列表；`GET /api/knowledge/documents` 必须先校验 `knowledge.read`，传入 `page/page_size` 时必须在 PostgreSQL read model 层完成知识空间权限、角色权限、关键字、知识空间、目录、类型、索引状态、权限角色筛选和白名单排序，并返回 `query/performance`；未分页全量返回仅用于兼容旧调用或下拉类轻量场景。
- 知识中心页面需要在主列表上方展示索引健康视图，基于当前分页结果聚合 `index_status`、`active_chunk_set_id`、`index_error` 和 `vector_index_error`，区分可检索、向量就绪、关键词兜底、索引失败、处理中和分块版本状态；索引失败与文本索引文档应复用 `retry-index` 入口处理，分块缺失文档应可直接打开分块版本，导入中/待索引文档应可进入导入任务排查。
- 知识沉淀候选审核列表也属于管理型审核列表；查询、采纳和驳回必须校验 `knowledge.deposit.decide` 权限点，不得绑定固定角色名，只有 `knowledge.read` 的只读用户不能访问审核候选；`GET /api/knowledge/deposits` 传入 `page/page_size` 时必须优先走 PostgreSQL read model 完成状态筛选、白名单排序和 count/page 查询，并返回 `query/performance`；未分页全量返回仅用于旧审核弹窗兼容和测试 helper。
- 启用统一 `ManagementListPage` 的管理页面可通过页面级 `viewStorageKey` 保存、应用和删除本地筛选视图；该能力仅作为当前浏览器偏好保存筛选/排序组合，不进入业务数据库，也不替代服务端权限或查询条件校验。存在页签的配置页可使用 `ManagementListPage` 嵌入模式，例如 AI 能力配置页的 AI角色和 Skill 管理页签分别保存独立筛选视图。
- 单记录创建、更新、状态流转和跨表写入不得为了兼容旧客户端而依赖运行时内存全量集合；例如迭代版本、产品模块、产品 Git 仓库和相关系统创建应按产品 ID 从 repository 读取产品存在性并使用轻量冲突校验；迭代版本编辑/删除、产品模块编辑/删除、产品 Git 仓库/相关系统更新删除、迭代版本分支配置更新删除、用户反馈更新/转需求应按业务 ID 从 repository 读取源记录，再在同一仓储边界写入业务记录和审计。
- 模型网关配置新增、编辑、删除由 repository 单记录写入或删除；MemoryStore 测试 fallback 的配置替换和模型调用日志追加必须通过模型网关配置集合/日志集合 helper 操作，不得直接赋值 `current_store.model_gateway_configs` 或 append `current_store.model_gateway_logs`。
- 通用审计 helper 在轻量上下文 fallback 中必须通过审计事件列表 helper 写入，不得直接 append `current_store.audit_events`；repository 运行态的审计事件由业务写入 helper 或仓储事务显式携带提交。
- 只读缓存允许用于看板等汇总视图，但必须可重建、权限过滤清晰，且不得作为写入事实源。
- DB-first 收口专项审计使用 `python scripts/audit_memory_store_usage.py --format text --fail-on-p1` 扫描 `apps/api/app` 内 `current_store.*` 残留；报告按 `P0/write|helper`、`P1/read` 和 `P2/helper` 分级，生产路径 P0/P1 必须清零并由单测扫描当前仓库持续兜底，剩余 P2 仅允许 helper/test fallback、可重建只读缓存入口或 `MemoryStore` 自身测试辅助代码。

## 验收映射

- 详细验收见 [../test-case.md](../test-case.md) 的系统管理、模型网关、知识、审计和 RBAC 用例，以及 [../rbac-redesign.md](../rbac-redesign.md)。
