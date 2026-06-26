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
- 角色管理页的角色列表属于管理型列表，`GET /api/system/roles` 必须在服务端完成分页、角色/分类/业务角色/可见入口/权限点/状态筛选、白名单排序和 `query/performance` 观测，前端不得拉全量角色后本地分页过滤。
- 角色管理页提供用户权限诊断工具，按用户 ID、菜单路径、权限点和数据范围解释“能看/不能看”的服务端判定依据。
- 菜单资源由数据库维护名称、父级、路由、图标、排序、状态和页面访问权限点，但前端只能加载静态注册路由组件。
- 管理列表型接口必须在 SQL/repository/read model 层完成分页、排序和筛选，并返回查询性能元数据。
- 启用统一 `ManagementListPage` 的管理页面可通过页面级 `viewStorageKey` 保存、应用和删除本地筛选视图；该能力仅作为当前浏览器偏好保存筛选/排序组合，不进入业务数据库，也不替代服务端权限或查询条件校验。存在页签的配置页可使用 `ManagementListPage` 嵌入模式，例如 AI 能力配置页的 AI角色和 Skill 管理页签分别保存独立筛选视图。
- 单记录创建、更新、状态流转和跨表写入不得为了兼容旧客户端而依赖运行时内存全量集合；例如迭代版本、产品模块、产品 Git 仓库和相关系统创建应按产品 ID 从 repository 读取产品存在性并使用轻量冲突校验；迭代版本编辑/删除、产品模块编辑/删除、产品 Git 仓库/相关系统更新删除、迭代版本分支配置更新删除、用户反馈更新/转需求应按业务 ID 从 repository 读取源记录，再在同一仓储边界写入业务记录和审计。
- 模型网关配置新增、编辑、删除由 repository 单记录写入或删除；MemoryStore 测试 fallback 的配置替换和模型调用日志追加必须通过模型网关配置集合/日志集合 helper 操作，不得直接赋值 `current_store.model_gateway_configs` 或 append `current_store.model_gateway_logs`。
- 通用审计 helper 在轻量上下文 fallback 中必须通过审计事件列表 helper 写入，不得直接 append `current_store.audit_events`；repository 运行态的审计事件由业务写入 helper 或仓储事务显式携带提交。
- 只读缓存允许用于看板等汇总视图，但必须可重建、权限过滤清晰，且不得作为写入事实源。
- DB-first 收口专项审计使用 `python scripts/audit_memory_store_usage.py --format text` 扫描 `apps/api/app` 内 `current_store.*` 残留；报告按 `P0/write|helper`、`P1/read` 和 `P2/helper` 分级，生产路径 P0/P1 必须清零，剩余 P2 仅允许 helper/test fallback、可重建只读缓存入口或 `MemoryStore` 自身测试辅助代码。

## 验收映射

- 详细验收见 [../test-case.md](../test-case.md) 的系统管理、模型网关、知识、审计和 RBAC 用例，以及 [../rbac-redesign.md](../rbac-redesign.md)。
