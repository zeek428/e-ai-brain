# 系统治理、RBAC 与业务大脑 API

> API 分册。覆盖系统设置、用户、角色、菜单、权限矩阵和业务大脑。主入口见 [../api.md](../api.md)，分册组索引见 [system-governance-and-platform.md](system-governance-and-platform.md)。

### 系统 RBAC API

Task 3 提供最小可用角色治理接口，用于系统管理员维护角色、角色权限点、角色菜单、角色数据范围以及用户授权。`GET /api/system/menus` 允许具备 `system.menus.read`、`system.menus.manage` 或历史兼容 `system.roles.manage` 的用户读取；带 `page/page_size` 时支持菜单、父级、路由、权限点、类型、状态筛选，`sort_by=sort_order|code|name|parent_code|path|menu_type|status`，并返回 `query/performance`；菜单资源写接口要求 `system.menus.manage`；角色治理接口要求 `system.roles.manage`；`/api/users/{user_id}/permissions`、`/api/users/{user_id}/roles` 和 `/api/users/{user_id}/scopes` 要求 `system.users.manage`。非授权用户返回 `403 FORBIDDEN`。系统角色（尤其 `admin`）当前不可停用，系统菜单当前不可删除；角色和菜单变更写入 `role_change_events` / `audit_events` 或对应菜单变更审计事件。`admin` 是内置超级管理员角色：有效权限和可见菜单运行时按所有 active 权限点与菜单资源动态展开，不依赖角色权限/菜单配置，角色页无需额外维护 admin 的权限矩阵。

用户管理列表返回账号资料和认证摘要：`local_password_configured` 表示账号密码登录是否可用，`login_methods` 返回 `password/dingtalk` 等可用登录方式，`dingtalk_binding` 返回钉钉绑定状态、企业名称、钉钉显示名、邮箱和外部身份 ID，但不得返回完整 `provider_subject/open_id/union_id`。`GET /api/system/external-identities` 与 `DELETE /api/system/external-identities/{identity_id}` 要求 `system.users.manage`，用于管理员排查和解除外部身份绑定；查询接口只返回外部身份脱敏 hint，删除接口默认阻止 SSO-only 用户被解绑到无登录方式，确需救援时必须显式传 `force=true`，并记录 `dingtalk_account.admin_unbound` 审计。

系统设置接口用于维护全局系统级配置。`GET /api/system/settings`、`PATCH /api/system/settings` 和 `POST /api/system/settings/email/test` 均要求 `system.settings.manage` 权限。`admin_email` 与 `test_recipient_email` 可为空，非空时必须为合法邮箱格式；`test_recipient_email` 用于保存常用测试邮件收件人，未配置时测试发送回退到 `admin_email`。`email_delivery` 用于配置系统级邮件发送能力，字段包括 `enabled`、`sender_email`、`default_from`、`reply_to`、`smtp_host`、`smtp_port`、`smtp_tls=none|starttls|ssl`、`smtp_username`、写入专用 `smtp_password` 和 `smtp_secret_ref`；启用发信时必须配置 SMTP Host、端口、TLS 模式、用户名以及密码或密钥引用，非法值返回 `400 VALIDATION_ERROR`。页面点击“发送测试邮件”必须先保存当前表单配置，再调用测试发送接口，避免刚输入的 SMTP 密码/授权码未生效；系统设置页面仅展示 `smtp_password`，邮箱客户端安全密码或应用授权码必须写入 `smtp_password`，页面不再展示或提交 `smtp_secret_ref`。`smtp_secret_ref` 仅作为 API 级高级字段，用于 `env:SMTP_PASSWORD` 这类外部密钥引用。

`PATCH /api/system/settings` 请求体示例：

```json
{
  "admin_email": "ops@example.com",
  "test_recipient_email": "qa@example.com",
  "email_delivery": {
    "enabled": true,
    "sender_email": "noreply@example.com",
    "default_from": "noreply@example.com",
    "reply_to": "support@example.com",
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_tls": "starttls",
    "smtp_username": "noreply@example.com",
    "smtp_password": "<write-only password or app authorization code>",
    "smtp_secret_ref": "env:SMTP_PASSWORD"
  }
}
```

`GET/PATCH` 响应返回 `admin_email`、`admin_email_configured`、`test_recipient_email`、`test_recipient_email_configured`、`email_delivery_configured`、`updated_at`、`updated_by` 和脱敏后的 `email_delivery`；响应不得包含 `smtp_password`，只能返回 `smtp_password_configured` 与 `smtp_secret_ref_configured`。PostgreSQL 运行态写入 `system_settings(setting_key='system_admin_email')`，并记录 `system.settings.updated` 审计事件，payload 只保存是否已配置、变更字段、密码/密钥引用是否已配置，不记录 SMTP 密码、密钥值、邮件正文或测试邮件内容。

`POST /api/system/settings/email/test` 请求体为 `{"recipient_email": "qa@example.com"}`；未传收件人时依次使用已保存的 `test_recipient_email`、`admin_email`。接口使用已保存配置发送带唯一测试编号、`Date` 和 `Message-ID` 的测试邮件，成功响应示例为 `{"delivery_status":"sent","message_id":"<...@example.com>","message_subject":"[AI Brain] 邮件发送配置测试 ab12cd34","recipient_email":"qa@example.com","sent_at":"2026-07-05T03:00:00+00:00","smtp_host":"smtp.example.com","smtp_port":587,"smtp_tls":"starttls"}`，失败时返回 `400 VALIDATION_ERROR` 或 `502 EMAIL_DELIVERY_TEST_FAILED`；SMTP 明确拒收收件人时不得误报成功。

`GET /api/system/health` 为系统健康与配置体检聚合接口，允许 `system.health.read`、`system.settings.manage` 或 `system.roles.read` 访问。响应会把系统检查、产品低分和钉钉授权到期物化为可处理告警 incident，但不得写入业务事实数据。接口聚合 `/health` 依赖状态、系统设置、钉钉登录配置、钉钉 MCP 插件连接、模型网关日志、知识索引健康、知识质量事件、AI 执行器队列、定时作业运行、观测告警配置和产品初始化状态。每个 `checks[]` 项返回 `key`、`category`、`component`、`title`、`status=ok|configured|warning|degraded|error|not_configured|disabled|info`、`description`、`fix_suggestion`、可选 `last_error`、`metrics` 和 `action_href`；`summary` 返回总数、正常项、需关注项、阻断异常和按状态/分类计数；`recommendations[]` 按异常优先级返回可跳转的修复建议。

接口同时返回 `operations` 运维治理视图，供系统健康页展示和后续告警任务复用：

- `alert_center`：按检查项、产品接入评分和钉钉授权有效期聚合告警，返回 `summary.open_count/high_count/medium_count/low_count/resolving_count/closed_count/rule_count/enabled_rule_count`、`alerts[]`、`rules[]`、`subscriptions[]` 和最近趋势 `trend[]`。告警项包含 `status`、`owner`、`first_seen_at`、`last_seen_at`、`close_reason`、`postmortem` 和命中规则元数据。
- `ai_executor_ops`：聚合 Runner 数、队列状态、排队/运行/失败/死信/超时任务、待审批数、队列压力、最近失败、失败原因分布和重试/取消/超时/dead-letter 策略摘要。
- `knowledge_quality_loop`：聚合知识空间、文档可检索率、索引失败、导入失败、待审核沉淀、质量门禁、近 30 天无结果率、引用点击率、RAG 引用准确率 proxy、有用/无用反馈和低质量/过期文档提示。
- `product_onboarding_scores`：按活跃产品计算接入完整度分数，评分来源包括产品主数据、版本、模块、代码仓库、可检索产品文档、关联系统、插件连接、产品权限范围和最近健康检查。每个产品返回 `missing_items`、`plugin_connection_count`、`plugin_failed_connection_count`、`plugin_total_connection_count`、`permission_scope_count`、`permission_scope_status`、`searchable_knowledge_document_count`、`recent_health_status=healthy|attention|degraded` 与 `recent_health_check`；`recent_health_check` 汇总插件测试失败、知识索引失败、权限范围缺失和代码仓库缺失等真实健康信号。
- `permission_diagnostics`：基于 RBAC 权限矩阵汇总高风险权限、菜单权限缺口和未配置数据范围的角色，并返回保存角色前风险预检、自动修复建议、用户菜单预览说明和 scope 对比。
- `dingtalk_lifecycle`：聚合钉钉登录启用状态、企业白名单、用户绑定数、MCP 连接状态、URL Key 到期提醒、授权主体和个人/系统/应用授权边界说明。
- `help_and_retention`：返回帮助截图覆盖情况和审计、执行链路、模型日志、作业运行、知识导入、帮助截图等归档保留策略。
- `security_audit_governance`：返回敏感配置审批策略、高风险操作二次确认策略、密钥引用格式校验、直接密钥配置数量、审计导出入口和近 7 天管理员周报摘要；响应不得包含任何密钥值。

该接口不得返回 SMTP 密码、钉钉 Client Secret、模型 API Key、插件 URL Key 或任何密钥明文。外部错误摘要必须脱敏 `key/token/secret/password/Authorization` 等敏感字段。

`GET/POST/PATCH /api/system/alerts/rules` 要求 `system.alerts.manage`，用于查看、创建和更新告警规则。规则字段包括 `name`、`source`、`component`、`severity_min=info|low|medium|high`、`owner`、`notification_scope`、`condition_json` 和 `enabled`；系统健康物化告警时会记录命中的规则 ID。

`PATCH /api/system/alerts/{alert_id}` 要求 `system.alerts.manage`，用于更新告警 incident 的 `status=open|acknowledged|resolving|closed|ignored`、`owner`、`close_reason` 和 `postmortem`。当 `status` 为 `closed` 或 `ignored` 时必须填写 `close_reason`。`POST /api/system/alerts/subscriptions` 要求 `system.alerts.manage`，请求体为 `channel=email|dingtalk|webhook|in_app`、`target`、`severity_min=info|low|medium|high`、`scope` 和 `enabled`，用于创建告警订阅。

`GET /api/system/admin-weekly-report?days=7` 允许 `system.alerts.manage`、`audit.read` 或 `system.settings.manage` 访问，返回近 N 天管理员周报摘要、Markdown 正文、待处理告警、敏感配置/权限相关审计摘要和高风险操作摘要；响应不得包含密钥、邮件正文、Prompt 或外部调用完整响应。

`GET /api/system/health` 响应示例：

```json
{
  "data": {
    "overall_status": "warning",
    "checked_at": "2026-07-08T08:30:00+00:00",
    "summary": {
      "total": 13,
      "ok_count": 8,
      "needs_attention_count": 2,
      "critical_count": 0,
      "status_counts": {"configured": 8, "warning": 2, "info": 3},
      "category_counts": {}
    },
    "checks": [
      {
        "key": "smtp",
        "category": "外部通知",
        "component": "smtp",
        "title": "SMTP 邮件发送",
        "status": "configured",
        "description": "邮件发送配置完整，可用于系统通知和测试发送。",
        "fix_suggestion": "建议定期使用系统设置中的发送测试邮件验证 SMTP 授权码仍有效。",
        "metrics": {"enabled": true, "smtp_host": "smtp.example.com"},
        "action_href": "/system/settings"
      }
    ],
    "operations": {
      "alert_center": {
        "summary": {"open_count": 1, "high_count": 0, "medium_count": 1, "low_count": 0},
        "alerts": [
          {
            "id": "check:dingtalk_mcp",
            "title": "钉钉 MCP 连接",
            "severity": "medium",
            "owner": "平台运维",
            "action_href": "/tasks/plugins"
          }
        ]
      },
      "product_onboarding_scores": {
        "summary": {"active_product_count": 3, "average_score": 82},
        "products": [
          {
            "product_id": "product_ai_brain",
            "name": "AI Brain",
            "score": 90,
            "status": "ready",
            "plugin_connection_count": 2,
            "plugin_failed_connection_count": 0,
            "permission_scope_count": 1,
            "permission_scope_status": "configured",
            "recent_health_status": "healthy",
            "recent_health_check": {
              "status": "healthy",
              "summary": "健康检查正常"
            },
            "missing_items": ["未维护关联系统"]
          }
        ]
      }
    },
    "recommendations": [],
    "trace_id": "trace_002"
  },
  "trace_id": "trace_002"
}
```

`GET /api/system/permissions/matrix` 为只读策略矩阵接口，允许 `system.roles.read` 或 `system.roles.manage` 访问。响应聚合 `roles`、`permissions`、`menus`、`rows` 和 `summary`：每个 `rows[]` 项按角色返回 `permission_count`、`granted_permission_codes`、`high_risk_permission_codes`、`menu_count`、`granted_menu_codes`、`required_permission_codes`、`missing_menu_permission_codes`、`scope_summary`、`scopes` 和 `diagnostics`。当角色被授权某菜单但缺少该菜单 `required_permissions` 时，`diagnostics` 必须包含 `menu_permission_gap`；当角色包含高风险权限时，必须包含 `high_risk_permission`。该接口不写入数据，角色管理页用于权限审计、范围检查和授权缺口排障。

角色详情响应统一返回：

```json
{
  "id": "role_delivery_operator",
  "code": "delivery_operator",
  "name": "Delivery Operator",
  "description": "Can operate delivery queues.",
  "category": "delivery",
  "is_system": false,
  "is_assignable": true,
  "status": "active",
  "sort_order": 110,
  "permission_codes": ["bug.read", "task.read"],
  "menu_codes": ["task", "task.center"],
  "scopes": [
    {"scope_type": "product", "scope_id": "product_alpha", "access_level": "write"}
  ],
  "access_preview": {
    "role_id": "role_delivery_operator",
    "role_code": "delivery_operator",
    "role_name": "Delivery Operator",
    "menu_count": 2,
    "permission_count": 2,
    "scope_count": 1,
    "scope_summary": "产品 1 项",
    "visible_menus": [
      {
        "code": "task.center",
        "name": "任务管理",
        "path": "/delivery/rd-tasks",
        "required_permissions": ["task.read"],
        "status": "active"
      }
    ],
    "operation_permissions": [
      {"code": "task.read", "name": "task.read", "category": "task", "risk_level": "normal", "status": "active"}
    ],
    "scopes": [
      {"scope_type": "product", "scope_id": "product_alpha", "scope_name": "Alpha 产品", "access_level": "write"}
    ],
    "scope_groups": [
      {"scope_type": "product", "scope_type_label": "产品", "count": 1, "scopes": []}
    ],
    "missing_menu_permission_codes": [],
    "high_risk_permission_codes": [],
    "diagnostics": []
  }
}
```

`access_preview` 是 `GET /api/system/roles/{role_id}` 的只读投影，便于角色详情、权限诊断和 AI 助手复用同一授权解释。该投影必须返回 `visible_menus`、`operation_permissions`、`scopes`、`scope_groups`、`required_permission_codes`、`missing_menu_permission_codes`、`high_risk_permission_codes` 和 `diagnostics`；产品、知识空间和全局范围必须补齐可读 `scope_name` 或固定名称；菜单已授权但缺少其 `required_permissions` 时必须返回 `menu_permission_gap` 诊断。

请求体约定：

- `POST /api/system/menus`：`code`、`name` 必填，`path`、`parent_code`、`menu_type=group|page|hidden_page`、`icon`、`sort_order`、`required_permissions`、`status=active|inactive` 可选。数据库菜单只维护导航元数据与权限映射，前端仍只加载静态路由注册表中存在的页面组件。
- `PATCH /api/system/menus/{menu_code}`：可更新 `name`、`path`、`parent_code`、`menu_type`、`icon`、`sort_order`、`required_permissions`、`status`，`code` 不可改。
- `PUT /api/system/menus/reorder`：`{"items": [{"code": "system.menus", "sort_order": 63}]}`，只更新排序并返回更新后的菜单资源列表。
- `GET /api/system/roles`：允许 `system.roles.read` 或 `system.roles.manage` 访问；支持 `page/page_size`、`role`、`category`、`business_role`、`menu_scope`、`permission`、`status`、`sort_by=sort_order|code|name|category|status` 和 `sort_order=asc|desc`，分页模式返回 `query/performance` 元数据；PostgreSQL 运行时必须优先调用角色 summary count/page read model，不得先全量 `list_roles()` 后在接口层过滤分页。
- `POST /api/system/roles`：`code`、`name` 必填，`description`、`category`、`is_assignable`、`sort_order` 可选。
- `POST /api/system/roles/{role_id}/copy`：`code` 必填，`name`、`description` 可选，权限、菜单和范围从源角色复制。
- `PATCH /api/system/roles/{role_id}`：可更新 `name`、`description`、`category`、`is_assignable`、`sort_order`。
- `PUT /api/system/roles/{role_id}/permissions`：`{"permission_codes": ["task.read"]}`，整体替换角色权限。
- `PUT /api/system/roles/{role_id}/menus`：`{"menu_codes": ["task", "task.center"]}`，整体替换角色菜单授权。
- `PUT /api/system/roles/{role_id}/scopes` 与 `PUT /api/users/{user_id}/scopes`：`{"scopes": [{"scope_type": "product", "scope_id": "product_alpha", "access_level": "write"}]}`，整体替换范围授权。
- `PUT /api/users/{user_id}/roles`：`{"role_codes": ["developer"]}`，整体替换用户角色授权。

新增错误码：

| 错误码 | HTTP | 说明 |
|------|------|------|
| `ROLE_CODE_EXISTS` | 409 | 角色 `code` 已存在。 |
| `MENU_CODE_EXISTS` | 409 | 菜单 `code` 已存在。 |
| `MENU_HAS_CHILDREN` | 409 | 菜单存在子菜单，不允许直接删除。 |
| `MENU_PARENT_NOT_FOUND` | 400 | 指定父级菜单不存在或不可用。 |
| `SYSTEM_ROLE_PROTECTED` | 409 | 系统角色不可执行当前破坏性操作，当前主要用于拒绝停用系统角色。 |
| `SYSTEM_MENU_PROTECTED` | 409 | 系统菜单不可删除。 |
| `DINGTALK_UNBIND_LOGIN_LOCKOUT_RISK` | 409 | 解除外部身份后用户没有其它可用登录方式。 |
| `EXTERNAL_IDENTITY_NOT_FOUND` | 404 | 外部身份绑定记录不存在。 |
| `EXTERNAL_IDENTITY_NOT_ACTIVE` | 409 | 外部身份绑定记录不是 active 状态。 |
| `UNSUPPORTED_MENU_STATUS` | 400 | 菜单状态不是 `active` 或 `inactive`。 |
| `UNSUPPORTED_MENU_TYPE` | 400 | 菜单类型不是 `group`、`page` 或 `hidden_page`。 |
| `UNSUPPORTED_PERMISSION` | 400 | 请求包含不存在或不可用的权限点。 |
| `UNSUPPORTED_MENU` | 400 | 请求包含不存在或不可用的菜单资源。 |
| `INVALID_SCOPE` | 400 | 数据范围类型、范围 ID 或访问级别非法。 |

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
