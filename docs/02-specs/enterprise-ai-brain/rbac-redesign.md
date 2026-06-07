# 系统权限管理 RBAC 重设计

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.2.0-draft |
| 适用系统版本 | ≥ v1.1.256 |
| 文档状态 | Proposed |
| 创建日期 | 2026-06-07 |

## 背景

当前系统权限模型是 MVP 固定角色目录：`admin`、`product_owner`、`rd_owner`、`reviewer`、`knowledge_owner`、`viewer` 六类角色由后端常量和 `role_definitions` 字典表共同声明，用户表 `users.roles` 以 JSON 数组保存角色 code，接口中通过 `require_roles(user, {...})` 判断写权限，知识文档通过 `permission_roles` 做角色级过滤。角色管理页面只读展示固定角色目录，用户管理和知识权限配置只能选择这些固定角色。

这个模型适合 MVP 验证，但在企业权限管理场景中有四个明显限制：

1. 角色不可由管理员创建、复制、停用或调整权限点，无法支撑不同团队的岗位差异。
2. 权限判断分散在接口代码中，依赖角色 code 硬编码，难以审计“某个用户为什么有这个动作权限”。
3. `users.roles` 和知识 `permission_roles` 都是 JSON 数组，缺少关系表、授权来源、授权人、有效期和撤销审计。
4. 数据范围只写在角色说明文本中，缺少可执行的产品、版本、模块、知识空间等授权边界。

本设计把系统权限管理改为以 RBAC 为基础模型：用户通过角色获得权限点，角色通过授权范围约束可访问数据，所有高影响授权变更都写入审计。现有六个角色保留为系统预置角色，作为迁移后的默认模板，而不是唯一可分配角色集合。

## 目标

- 支持角色管理从只读目录升级为可维护的角色 CRUD：创建、复制、编辑、停用、启用、查看详情。
- 建立标准 RBAC 数据模型：`permissions`、`roles`、`role_permissions`、`user_roles`、`role_scope_grants`。
- 统一权限判断入口：业务接口校验权限点，不再直接硬编码业务角色 code。
- 保留系统预置角色，支持管理员基于预置角色复制出企业自定义角色。
- 支持菜单权限、操作权限和数据范围权限组合，避免仅靠前端隐藏入口。
- 支持角色授权、撤销、权限变更和数据范围变更的审计追踪。
- 保持 DB-first 架构：角色、权限、用户授权和数据范围均以 PostgreSQL 结构表为事实源。

## 非目标

- 不引入 ABAC 规则引擎或脚本化策略语言；v1.2 只在 RBAC 基础上增加受控的数据范围授权。
- 不做组织架构、部门、岗位、审批流和 SSO/LDAP 同步；这些可在 RBAC 稳定后扩展。
- 不允许普通管理员修改系统保留权限点的 code、语义或高危系统角色保护规则。
- 不用前端菜单隐藏替代后端权限判断。

## 设计原则

- **最小权限**：新角色默认无权限，必须显式选择权限点和数据范围。
- **职责分离**：系统配置、产品决策、研发执行、评审确认、知识治理和只读查看保持可分离授权。
- **权限点稳定**：业务代码依赖权限点 code，而不是依赖可变角色 code。
- **范围可解释**：用户详情、角色详情和审计记录都能解释权限来自哪个角色、覆盖哪个范围。
- **高危保护**：系统内置角色、系统权限点和超级管理能力有保护机制，避免误删后无法恢复。
- **后端强制**：所有写操作、敏感读操作和聚合 read model 都必须在后端执行权限与数据范围过滤。

## 权限模型

### 核心对象

| 对象 | 说明 |
|------|------|
| 用户 User | 登录主体，仍由 `users` 表管理账号、密码、状态和显示名。 |
| 角色 Role | 一组权限点和默认数据范围的集合，可为系统预置或管理员自定义。 |
| 权限点 Permission | 稳定的动作能力，例如 `system.users.manage`、`requirement.approve`、`knowledge.search`。 |
| 菜单 Menu | 左侧导航和页面入口资源，例如系统管理、角色管理、任务中心、Bug 管理。 |
| 用户角色 UserRole | 用户和角色的授权关系，记录授权人、有效期、状态和撤销信息。 |
| 数据范围 ScopeGrant | 角色或用户在产品、版本、模块、知识空间等资源上的授权边界。 |
| 权限快照 PermissionSnapshot | 登录和请求期间派生的有效权限点与范围集合，不作为写入事实源。 |

### 权限点分类

| 分类 | 示例权限点 | 说明 |
|------|------------|------|
| `system` | `system.users.manage`、`system.roles.read`、`system.roles.manage`、`system.model_gateway.manage` | 系统管理与平台配置。 |
| `product` | `product.read`、`product.manage`、`product.scope.manage` | 产品主数据与产品授权范围维护。 |
| `requirement` | `requirement.read`、`requirement.create`、`requirement.approve`、`requirement.task_generate` | 需求台账与任务生成。 |
| `task` | `task.read`、`task.create`、`task.execute`、`task.cancel`、`task.retry` | AI 任务生命周期。 |
| `review` | `review.read`、`review.decide` | 人工确认点。 |
| `bug` | `bug.read`、`bug.manage` | Bug 管理。 |
| `testing` | `test.read`、`test.case.manage`、`test.execution.manage`、`test.bug.verify` | 测试计划、测试执行、自动化测试结果确认和 Bug 验证。 |
| `release` | `release.read`、`release.readiness.manage`、`release.decide` | 发布评估、发布确认和上线后分析。 |
| `knowledge` | `knowledge.read`、`knowledge.search`、`knowledge.manage`、`knowledge.deposit.decide` | 知识文档、检索和沉淀。 |
| `devops` | `devops.read`、`devops.metrics.manage` | GitLab、Jenkins、线上日志指标。 |
| `insight` | `insight.read`、`insight.feedback.manage`、`planning.decide` | 用户洞察、反馈和迭代建议。 |
| `audit` | `audit.read` | 审计查询。 |
| `assistant` | `assistant.chat` | AI 助手访问。 |

权限点 code 必须稳定、低频变更。新增业务接口时先在 `permissions` 中声明权限点，再在 API 文档、测试用例和角色模板中映射。

### 数据范围

RBAC 只回答“用户能做什么动作”，数据范围回答“用户能在哪些数据上做”。v1.2 支持以下范围类型：

| scope_type | scope_id | 说明 |
|------------|----------|------|
| `global` | `*` | 全平台范围，仅系统管理、高级审计和平台级看板使用。 |
| `product` | `products.id` | 产品范围，约束需求、任务、Bug、DevOps、用户洞察和看板数据。 |
| `version` | `product_versions.id` | 迭代版本范围，继承所属产品但可进一步收窄。 |
| `module` | `product_modules.id` | 模块范围，约束 Bug、日志、需求模块和知识上下文。 |
| `knowledge_space` | `knowledge_documents.product_id` 或后续知识空间 ID | 知识文档和检索范围。 |
| `review_assignment` | `human_reviews.assignee_id` 或任务评审人字段 | 评审负责人只访问分配给自己的 Review。 |
| `self` | 当前用户 ID | AI 助手历史、个人会话等用户级数据。 |

范围匹配规则：

1. `global:*` 覆盖所有资源。
2. `product:{id}` 覆盖该产品下需求、任务、Bug、指标、反馈、迭代建议、知识文档和看板摘要。
3. `version:{id}` 只覆盖该版本及其关联需求、任务、Bug、发布记录。
4. `module:{id}` 只覆盖该模块及其关联 Bug、日志指标和需求模块字段。
5. `review_assignment:self` 只覆盖分配给当前用户的待确认 Review 和对应任务上下文。
6. 多角色授权取并集；显式撤销或停用角色立即从有效权限快照中移除。

### 菜单权限与左侧导航

左侧菜单属于 RBAC 设计范围，但它只负责“能看到哪些功能入口”，不能替代后端动作权限和数据范围校验。

目标态菜单授权链路：

```text
角色配置功能菜单
-> 角色授权给用户
-> 用户登录后后端计算有效角色、权限点、数据范围和可见菜单
-> /api/auth/me 返回 menu_tree
-> 前端左侧导航按 menu_tree 渲染
-> 用户点击页面或按钮时，后端继续校验权限点和数据范围
```

菜单资源由后端维护为稳定目录，前端路由以菜单 code 绑定，不允许前端自行根据本地角色常量决定主导航。角色管理页面可以为角色勾选菜单资源；保存后写入角色-菜单关系。用户拥有多个角色时，可见菜单取并集；角色停用、授权撤销或菜单停用后，用户下一次权限快照刷新时不再返回对应菜单。

菜单资源分为三类：

| menu_type | 说明 | 示例 |
|-----------|------|------|
| `group` | 左侧分组或父级菜单，不直接打开页面。 | `system` 系统管理、`delivery` 需求交付 |
| `page` | 可导航页面。 | `system.roles` 角色管理、`task.center` 任务中心 |
| `hidden_page` | 不在左侧展示，但可通过详情链接访问；访问仍需权限。 | `requirement.full_chain` 需求全链路详情 |

菜单显示规则：

1. 后端只返回 active 菜单、当前用户角色已授权菜单，以及父级链路完整的菜单树。
2. 菜单可以配置 `required_permissions`，用户必须同时拥有对应权限点才返回该菜单；只授予菜单但没有权限点时不显示。
3. `hidden_page` 不出现在左侧菜单，但可在 `auth/me` 的 `route_permissions` 中返回，用于前端路由守卫。
4. 前端左侧菜单只使用 `menu_tree` 渲染，不再根据硬编码角色 code 展示菜单。
5. 页面内按钮仍基于具体权限点控制显示；接口提交以后端 `require_permissions` 为准。

## 数据库设计

### 新增和调整表

| 表 | 用途 | 关键字段 |
|----|------|----------|
| `permissions` | 权限点字典 | `code`、`name`、`category`、`description`、`risk_level`、`is_system`、`status`、`created_at`、`updated_at` |
| `menu_resources` | 菜单和路由资源字典 | `code`、`name`、`path`、`parent_code`、`menu_type`、`icon`、`sort_order`、`required_permissions`、`is_system`、`status`、`created_at`、`updated_at` |
| `roles` | 角色主表 | `id`、`code`、`name`、`description`、`category`、`is_system`、`is_assignable`、`status`、`sort_order`、`created_by`、`updated_by`、`created_at`、`updated_at` |
| `role_permissions` | 角色-权限关系 | `role_id`、`permission_code`、`granted_by`、`created_at`、`updated_at` |
| `role_menu_grants` | 角色-菜单关系 | `role_id`、`menu_code`、`granted_by`、`created_at`、`updated_at` |
| `user_roles` | 用户-角色关系 | `user_id`、`role_id`、`granted_by`、`grant_reason`、`effective_from`、`expires_at`、`status`、`revoked_by`、`revoked_at`、`created_at`、`updated_at` |
| `role_scope_grants` | 角色默认数据范围 | `role_id`、`scope_type`、`scope_id`、`access_level`、`granted_by`、`created_at`、`updated_at` |
| `user_scope_grants` | 用户补充数据范围 | `user_id`、`scope_type`、`scope_id`、`access_level`、`granted_by`、`expires_at`、`status`、`created_at`、`updated_at` |
| `role_change_events` | 角色配置变更历史 | `role_id`、`event_type`、`before_payload`、`after_payload`、`actor_id`、`trace_id`、`created_at` |

兼容调整：

- `role_definitions` 保留为迁移兼容视图或同步表，后续由 `roles + role_permissions` 派生，不再作为角色事实源。
- `users.roles` 在迁移期保留并由 `user_roles` 反向同步；完成迁移后降级为兼容读字段，新增授权不再直接写 JSON 数组。
- `knowledge_documents.permission_roles` 在迁移期继续支持，新增知识权限应逐步改为 `scope_type=knowledge_space/product` 的范围授权，避免知识检索依赖角色 code。

### 索引和约束

- `permissions.code` 唯一，系统权限点 `is_system=true` 不允许删除，只允许停用非核心权限点。
- `roles.code` 唯一，系统预置角色 `is_system=true` 不允许删除，只允许调整 `is_assignable` 和展示字段；高危权限的授予需要审计。
- `role_permissions(role_id, permission_code)` 唯一。
- `menu_resources.code` 唯一；系统菜单 `is_system=true` 不允许删除，只允许停用或调整展示字段。
- `role_menu_grants(role_id, menu_code)` 唯一。
- `user_roles(user_id, role_id, status)` 至少保证同一用户同一 active 角色不重复。
- `role_scope_grants(role_id, scope_type, scope_id, access_level)` 唯一。
- 所有新增结构表必须包含 `created_at` 和 `updated_at` 标准时间字段，满足现有迁移门禁要求。

## 后端授权设计

### 当前模式迁移

当前：

```python
require_roles(user, {"product_owner", "rd_owner"})
```

目标：

```python
require_permissions(user, {"task.create"}, scope=ProductScope(product_id))
```

服务层统一通过 `AuthorizationService` 派生当前用户有效授权：

1. 读取 active 用户。
2. 读取 active 且未过期的 `user_roles`。
3. 合并 active 角色的 `role_permissions`。
4. 合并角色范围和用户补充范围。
5. 加入 `self` 范围和被分配 Review 范围。
6. 返回 request-scoped `PermissionSnapshot`。

`PermissionSnapshot` 只在请求期间缓存，不能写回为事实源。缓存 key 必须包含 `user_id`、用户更新时间、角色授权更新时间或短 TTL，避免角色变更后长时间不生效。

### 后端检查类型

| 类型 | 检查内容 | 示例 |
|------|----------|------|
| 动作权限 | 是否拥有权限点 | 创建需求需要 `requirement.create`。 |
| 数据范围 | 是否覆盖资源范围 | 审批需求需要 `requirement.approve` 且覆盖需求所属产品。 |
| 状态机 | 资源状态是否允许动作 | 只有可审批状态的需求能审批。 |
| 高危保护 | 是否触发额外限制 | 不能停用最后一个拥有 `system.roles.manage` 的 active 用户。 |
| 审计 | 是否记录授权或高影响业务动作 | 修改角色权限记录 `role.permission_updated`。 |

业务接口不得只检查菜单权限。前端菜单仅用于展示入口，后端必须检查动作权限和范围。

### 权限点替换关系

| 现有角色判断 | 目标权限判断 |
|--------------|--------------|
| `admin` | `system.users.manage`、`system.roles.read`、`system.roles.manage`、`system.model_gateway.manage`、`audit.read` |
| `product_owner` | `product.manage`、`requirement.create`、`requirement.approve`、`requirement.task_generate`、`planning.decide` |
| `rd_owner` | `task.create`、`task.execute`、`review.decide`、`knowledge.manage`、`bug.manage`、`devops.metrics.manage` |
| `developer` | `task.read`、`task.create`、`task.execute`、`bug.read`、`knowledge.search` |
| `test_owner` | `task.read`、`task.create`、`review.decide`、`test.case.manage`、`test.execution.manage`、`test.bug.verify`、`bug.manage` |
| `tester` | `task.read`、`test.read`、`test.execution.manage`、`test.bug.verify`、`bug.read`、`bug.manage` |
| `release_owner` | `task.read`、`release.readiness.manage`、`release.decide`、`devops.read`、`bug.read` |
| `reviewer` | `review.read`、`review.decide`、`task.read` |
| `knowledge_owner` | `knowledge.manage`、`knowledge.search`、`knowledge.deposit.decide` |
| `viewer` | `workspace.read` 或按领域拆分后的 `*.read` |

`workspace.read` 可作为兼容读权限保留，但管理主列表和敏感详情应逐步替换为领域读权限，例如 `requirement.read`、`task.read`、`bug.read`、`knowledge.read`。

## API 设计

### 角色管理

| 方法 | 路径 | 权限点 | 说明 |
|------|------|--------|------|
| GET | `/api/system/roles` | `system.roles.read` | 查询角色列表，支持分页、筛选、排序和性能元数据。 |
| POST | `/api/system/roles` | `system.roles.manage` | 创建自定义角色。 |
| GET | `/api/system/roles/{role_id}` | `system.roles.read` | 查询角色详情、权限点、数据范围、已授权用户摘要和变更历史。 |
| PATCH | `/api/system/roles/{role_id}` | `system.roles.manage` | 更新角色基础信息、状态、可分配标记和排序。 |
| POST | `/api/system/roles/{role_id}/copy` | `system.roles.manage` | 从系统角色或自定义角色复制新角色。 |
| PUT | `/api/system/roles/{role_id}/permissions` | `system.roles.manage` | 整体替换角色权限点，写入变更审计。 |
| PUT | `/api/system/roles/{role_id}/menus` | `system.roles.manage` | 整体替换角色可见功能菜单，写入变更审计。 |
| PUT | `/api/system/roles/{role_id}/scopes` | `system.roles.manage` | 整体替换角色默认数据范围。 |
| POST | `/api/system/roles/{role_id}/disable` | `system.roles.manage` | 停用角色；禁止停用最后一个系统管理能力来源。 |
| POST | `/api/system/roles/{role_id}/enable` | `system.roles.manage` | 启用角色。 |

`GET /api/auth/roles` 作为兼容接口保留，短期返回 active 且 assignable 的角色目录；新角色管理页使用 `/api/system/roles`。

### 权限点目录

| 方法 | 路径 | 权限点 | 说明 |
|------|------|--------|------|
| GET | `/api/system/permissions` | `system.roles.read` | 查询权限点目录，按分类、风险等级和状态筛选。 |
| GET | `/api/system/permissions/matrix` | `system.roles.read` | 返回角色 x 权限点矩阵，供角色管理页展示和批量编辑。 |

### 菜单资源目录

| 方法 | 路径 | 权限点 | 说明 |
|------|------|--------|------|
| GET | `/api/system/menus` | `system.roles.read` | 查询菜单资源树，供角色管理页配置功能菜单。 |
| GET | `/api/system/menus/matrix` | `system.roles.read` | 返回角色 x 菜单矩阵，供角色菜单授权和差异查看。 |

权限点由迁移脚本和代码定义同步，不提供普通页面创建权限点。新增权限点属于开发和发布流程，不属于运行时配置。

### 用户授权

| 方法 | 路径 | 权限点 | 说明 |
|------|------|--------|------|
| GET | `/api/users/{user_id}/roles` | `system.users.manage` | 查询用户角色授权和有效期。 |
| PUT | `/api/users/{user_id}/roles` | `system.users.manage` | 整体替换用户角色，支持授权原因、有效期和审计。 |
| POST | `/api/users/{user_id}/roles/{role_id}/revoke` | `system.users.manage` | 撤销单个角色授权。 |
| GET | `/api/users/{user_id}/permissions` | `system.users.manage` | 查询用户有效权限点和范围解释，用于排障。 |
| PUT | `/api/users/{user_id}/scopes` | `system.users.manage` | 配置用户补充数据范围。 |

用户创建和修改接口中的 `roles` 字段迁移为兼容字段：前端仍可一次性选择角色，但后端写入 `user_roles`，响应中继续返回 `roles` code 数组和新增的 `role_assignments`。

### 当前用户权限

| 方法 | 路径 | 权限点 | 说明 |
|------|------|--------|------|
| GET | `/api/auth/me` | 已登录 | 返回当前用户、角色 code、有效权限点、菜单入口和简化范围摘要。 |
| GET | `/api/auth/me/permissions` | 已登录 | 返回完整有效权限点和范围解释，供前端调试面板或权限问题排查。 |

`GET /api/auth/me` 目标响应必须包含 `menu_tree` 和 `route_permissions`：`menu_tree` 用于左侧菜单渲染，`route_permissions` 用于隐藏详情页和直接 URL 访问守卫。前端路由守卫应基于 `permissions`、`menu_tree` 和 `route_permissions` 控制入口展示；页面内按钮基于具体权限点控制；提交动作仍以后端校验为准。

## 角色管理页面重设计

系统管理下的角色管理从“只读目录”改为“角色治理工作台”。

### 页面结构

1. 角色列表：展示角色名称、code、分类、系统/自定义、状态、可分配、权限数量、范围摘要、用户数量、更新时间。
2. 筛选区：角色名称/code、分类、状态、系统/自定义、权限点、数据范围类型、是否可分配。
3. 行操作：查看、复制、编辑、停用/启用。
4. 详情抽屉：基础信息、权限矩阵、菜单矩阵、数据范围、已授权用户、变更历史。
5. 新增/编辑弹窗：基础信息、功能菜单选择、权限点选择、默认数据范围、风险确认。

### 交互约束

- 系统预置角色可以查看和复制；默认不允许删除。
- 自定义角色可以编辑、停用和启用；已被用户使用的角色停用前必须二次确认。
- 权限点以分类树或矩阵展示，危险权限用风险标签标识。
- 功能菜单以左侧导航同构的树控件展示，勾选父级菜单不会自动授予子页面动作权限；保存时同时校验菜单所需权限点是否已授予。
- 选择 `system.roles.manage`、`system.users.manage`、`system.model_gateway.manage` 等高危权限时，必须显示风险确认。
- 数据范围选择使用明确控件：全局、指定产品、指定版本、指定模块、指定知识空间，不允许自由输入 ID。
- 角色详情必须展示“该角色赋予哪些动作、覆盖哪些数据、哪些用户正在使用”。

## 预置角色设计

RBAC 目标态的系统预置角色分为两组：MVP 兼容角色和研发交付扩展角色。预置角色是默认模板，不限制管理员创建企业自定义角色。

### MVP 兼容角色

现有六个角色迁移为系统预置角色：

| 旧 code | 新角色 | 迁移策略 |
|---------|--------|----------|
| `admin` | 系统管理员 | `is_system=true`，授予系统管理、审计、全局读写范围。 |
| `product_owner` | 产品负责人 | `is_system=true`，授予产品、需求、规划、Bug 相关权限，默认无全局产品范围；本地种子可给示例产品范围。 |
| `rd_owner` | 研发负责人 | `is_system=true`，授予任务执行、Review、知识、Bug、DevOps 权限，按产品范围生效。 |
| `reviewer` | 评审负责人 | `is_system=true`，授予 Review 权限，默认使用 `review_assignment:self` 范围。 |
| `knowledge_owner` | 知识负责人 | `is_system=true`，授予知识管理和检索权限，按知识空间或产品范围生效。 |
| `viewer` | 查看者 | `is_system=true`，授予领域读权限和有限菜单入口，按产品或自有范围生效。 |

### 研发交付扩展角色

v1.2 预置以下开发相关角色，解决测试、开发、发布职责被 `rd_owner` 或 `viewer` 兼任的问题：

| 新 code | 中文名称 | 定位 | 默认权限点 | 默认数据范围 |
|---------|----------|------|------------|--------------|
| `developer` | 开发工程师 | 承接技术方案后的开发计划、代码开发辅助、缺陷修复和研发知识查询。 | `task.read`、`task.create`、`task.execute`、`bug.read`、`knowledge.search` | 授权产品、版本或模块。 |
| `test_owner` | 测试负责人 | 负责测试计划、自动化测试任务确认、测试 Bug 管理和质量门禁。 | `task.read`、`task.create`、`review.decide`、`test.case.manage`、`test.execution.manage`、`test.bug.verify`、`bug.manage` | 授权产品、版本或模块；可确认分配给自己的测试 Review。 |
| `tester` | 测试人员 | 执行人工测试、登记 Bug、验证修复结果和查看测试相关任务。 | `task.read`、`test.read`、`test.execution.manage`、`test.bug.verify`、`bug.read`、`bug.manage` | 授权产品、版本或模块；默认不具备需求审批、任务启动或发布确认权限。 |
| `release_owner` | 发布负责人 | 负责发布评估、发布确认、上线后分析和发布风险复核。 | `task.read`、`release.readiness.manage`、`release.decide`、`devops.read`、`bug.read` | 授权产品或版本；可读取同版本发布、日志和未关闭 Bug。 |

测试相关动作的权限边界：

1. `tester` 可以登记人工测试 Bug、更新复现信息、验证修复结果，但不能审批需求、确认产品设计、确认技术方案或执行发布确认。
2. `test_owner` 可以创建或确认 `automated_testing` 相关 AI 任务输出，并对测试结论进入发布前门禁负责。
3. `rd_owner` 仍可管理研发侧 Bug 和任务执行，但不再作为测试组织的唯一写权限来源。
4. `release_owner` 只负责发布准备和上线后分析，不默认拥有模型网关、用户管理、角色管理或产品主数据维护权限。

迁移步骤：

1. 创建 `permissions`、`roles`、`role_permissions`、`user_roles`、`role_scope_grants`、`user_scope_grants`、`role_change_events`。
2. 将 `role_definitions` 中的六个 MVP 角色导入 `roles`，将 `permissions` JSON 展开到 `role_permissions`。
3. 将 `users.roles` JSON 展开到 `user_roles`，授权来源标记为 `migration`。
4. 为 `admin` 添加 `global:*` 范围；其他角色如无明确产品范围，先保留兼容 `legacy_role_scope=true`，实现切换期继续按旧行为读，但页面提示需要补齐范围。
5. 新增 `developer`、`test_owner`、`tester`、`release_owner` 研发交付预置角色，默认 `is_system=true`、`is_assignable=true`，但不自动授予既有用户。
6. 用户管理和角色管理写入新表，同时短期回写 `users.roles` 保持兼容。
7. 后端接口逐步从 `require_roles` 切换到 `require_permissions`；每迁移一个业务域就补齐对应测试。
8. 全部业务域切换完成后，`users.roles` 和 `role_definitions` 只作为兼容读投影，不再作为授权事实源。

## 审计事件

新增审计事件：

| 事件 | 触发场景 |
|------|----------|
| `role.created` | 创建角色。 |
| `role.updated` | 更新角色基础信息。 |
| `role.copied` | 复制角色。 |
| `role.disabled` / `role.enabled` | 停用或启用角色。 |
| `role.permissions_updated` | 修改角色权限点。 |
| `role.menus_updated` | 修改角色可见功能菜单。 |
| `role.scopes_updated` | 修改角色默认数据范围。 |
| `user.roles_updated` | 修改用户角色授权。 |
| `user.role_revoked` | 撤销用户角色。 |
| `user.scopes_updated` | 修改用户补充范围。 |

审计 payload 至少包含 `actor_id`、目标角色或用户、变更前后摘要、权限点增删、菜单增删、范围增删、授权原因、trace_id。不得在审计中保存密码、token 或模型密钥。

## 安全保护

- 禁止删除系统权限点和系统预置角色。
- 禁止停用或撤销最后一个拥有 `system.roles.manage` 与 `system.users.manage` 的 active 用户授权。
- 非 active 用户没有任何有效权限。
- 停用角色后，相关用户的有效权限立即失效；历史审计仍保留角色名称和 code。
- 权限点变更、菜单授权变更、角色停用和用户授权变更必须记录审计。
- 权限校验失败统一返回 `403 FORBIDDEN`，响应包含 trace_id 和权限错误码，不泄露无权资源详情。
- 左侧菜单隐藏不得作为安全边界；直接访问 URL 或调用 API 时必须继续校验权限点和数据范围。
- 管理列表、聚合看板、知识检索和任务详情必须在查询层或 service 层应用数据范围过滤。

## 测试策略

### 后端

- 迁移测试：旧 `role_definitions` 和 `users.roles` 能正确展开到新 RBAC 表，迁移可重复执行。
- 权限目录测试：权限点 code、分类、风险等级、系统标记和状态完整。
- 菜单目录测试：菜单 code、父子关系、路由路径、菜单类型、所需权限点和状态完整。
- 预置角色测试：MVP 六角色和 `developer`、`test_owner`、`tester`、`release_owner` 均可查询、复制和分配，且系统预置角色不可删除。
- 角色 CRUD 测试：创建、复制、编辑、停用、启用、权限替换、范围替换和保护规则。
- 菜单授权测试：角色菜单保存后，授权用户登录返回正确 `menu_tree`；撤销角色、停用角色或停用菜单后不再返回。
- 用户授权测试：用户角色授予、撤销、有效期、停用角色失效、权限解释。
- 业务接口回归：每个从 `require_roles` 迁移的接口覆盖允许、拒绝、范围不匹配三类用例。
- 知识检索和看板测试：无权范围不能通过搜索、聚合或详情绕过。
- 审计测试：所有角色和用户授权变更写入审计。

### 前端

- 角色管理页：列表筛选、分页、详情、复制、新增、编辑、停用/启用、权限矩阵和范围控件。
- 角色菜单配置：角色编辑时可勾选功能菜单树，保存后用户重新登录左侧菜单按授权显示。
- 用户管理页：角色选择改为读取 active assignable 角色，授权详情展示有效期和来源。
- 路由和按钮权限：不同权限快照下菜单、按钮和提交错误态正确。
- 真实网页 smoke：登录管理员，打开 `/system/roles`，验证非空渲染、可见预置角色、自定义角色创建/复制入口和无 console/runtime error。

## 分阶段落地

### Phase 1：模型和兼容读

- 新增 RBAC 表和迁移脚本。
- 导入权限点、菜单资源、六个 MVP 兼容预置角色和研发交付扩展预置角色。
- 将 `users.roles` 展开到 `user_roles`。
- 新增 `AuthorizationService`，但业务接口暂不切换。
- `/api/auth/me` 返回兼容 roles 和新增 permissions、scope summary、menu_tree。

### Phase 2：角色管理 CRUD

- 新增 `/api/system/roles` 和 `/api/system/permissions`。
- 新增 `/api/system/menus` 和角色菜单授权接口。
- 前端角色管理页从只读目录升级为角色治理工作台。
- 用户管理写入 `user_roles`，短期回写 `users.roles`。
- 补齐授权变更审计。

### Phase 3：业务接口权限点化

- 从系统管理、用户管理、模型网关、审计开始替换为 `require_permissions`。
- 再迁移产品、需求、任务、Review、知识、Bug、DevOps、用户洞察和 AI 助手。
- 每个领域迁移时补齐范围过滤测试。

### Phase 4：移除旧授权事实源

- `users.roles` 改为只读兼容投影或废弃字段。
- `role_definitions` 改为视图或废弃表。
- 知识权限从 `permission_roles` 迁移到产品/知识空间范围授权。
- 删除业务代码中的角色 code 硬编码，仅保留系统预置角色种子。

## 开放问题

1. 是否需要在 v1.2 同时引入组织/部门维度，还是先用产品范围承载团队边界？
2. 产品负责人和研发负责人的产品范围由系统管理员配置，还是由产品管理页的产品成员配置？
3. 知识权限是否需要独立“知识空间”实体，还是继续以产品归属和文档范围承载？
4. 高危权限变更是否需要双人审批？本设计先要求二次确认和审计，不包含审批流。
5. 外部 SSO 用户进入后，默认角色和范围如何映射？本设计暂不包含 SSO。

## 验收标准

- 管理员可以创建自定义角色、选择权限点和数据范围，并将角色授予用户。
- 系统预置六个 MVP 兼容角色迁移后仍能满足当前页面和接口权限回归。
- 系统预置开发工程师、测试负责人、测试人员和发布负责人角色，测试人员可登记/验证授权范围内 Bug，但不能执行需求审批、技术方案确认或发布确认。
- 角色可以配置功能菜单；角色授权给用户后，用户登录返回 `menu_tree`，前端左侧菜单按 `menu_tree` 展示。
- 后端业务接口能够基于权限点和数据范围拒绝越权访问。
- 角色、权限和用户授权变更均可在审计中追踪。
- 角色管理页面不再只是只读目录，而是可执行角色治理的系统管理入口。
- 现有登录、用户管理、知识权限选择和发布 smoke 在兼容期不回归。
