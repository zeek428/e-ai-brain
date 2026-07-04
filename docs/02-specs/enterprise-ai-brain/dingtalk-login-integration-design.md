# 钉钉登录集成设计

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.2-p0 |
| 适用系统版本 | 当前主干 P0 已实现，管理端扩展待后续迭代 |
| 文档状态 | P0 Implemented / Evolving |

## 文档定位

本文是 AI Brain 集成钉钉登录的方案设计与演进记录。当前主干已落地 P0：登录 provider 查询、钉钉 OAuth start/callback、一次性 ticket 换取 AI Brain Token、`user_external_identities` 绑定表、登录页钉钉入口、回调页和用户自助绑定/解绑后端接口。系统设置管理页、个人中心绑定 UI、管理员外部身份审批和多企业深度治理按后续迭代推进。

当前 AI Brain 已具备本地账号登录和 Bearer Token 鉴权。钉钉登录目标是在保留本地管理员兜底入口的前提下，允许企业用户通过钉钉 OAuth 或扫码完成身份认证，并映射到 AI Brain 内部用户、角色、权限和数据范围。

## 背景与目标

### 背景

当前认证能力：

- 后端 `POST /api/auth/login` 通过本地用户名密码校验用户并签发 AI Brain 自有 JWT。
- 用户主表 `users` 保存 `email/display_name/roles/password_hash/status`。
- 前端登录页只有本地账号密码入口。
- 钉钉 MCP 插件已经作为外部能力集成方向存在，但插件授权 token 与 AI Brain 登录身份尚未打通。

钉钉开放平台提供网页方式登录和扫码登录能力，可通过 OAuth 2.0 授权码流程获取用户级访问令牌，并用于获取用户授权的个人身份信息。钉钉用户级 access token 有有效期，适合代表用户访问钉钉资源；AI Brain 登录态仍必须由 AI Brain 后端自行签发和校验。

### 目标

- 登录页增加可配置的“钉钉登录”入口。
- 钉钉回调后把钉钉用户身份绑定到 AI Brain `users.id`。
- 登录成功后仍签发 AI Brain 自有 JWT，业务接口继续只信任 AI Brain JWT。
- 支持管理员预绑定、用户自助绑定、首次登录自动创建 viewer 或待审批。
- 严格区分“AI Brain 登录身份”和“钉钉 MCP 调用授权”。
- 登录、绑定、解绑、拒绝、失败和自动开户必须可审计。
- 支持后续扩展到飞书、企业微信、OIDC 等外部身份源。

### 非目标

- 不在本阶段替换现有本地账号密码登录。
- 不把钉钉 user access token 当作 AI Brain API 的 Bearer Token。
- 不在登录阶段默认获得所有钉钉文档、审批、日历、群聊等业务权限。
- 不在首版实现钉钉组织架构、部门、角色的全量同步。
- 不要求首版支持多钉钉企业同时自动开户；多企业只通过白名单和身份绑定识别。

## 官方能力依据

设计依赖以下钉钉开放平台能力，具体字段和权限点在实现前需按当时官方文档再次校验：

- [实现网页方式登录应用（登录第三方网站）](https://open.dingtalk.com/document/development/tutorial-obtaining-user-personal-information)：用于浏览器登录应用并获取用户授权的个人信息。
- [获取用户 token](https://open.dingtalk.com/document/development/obtain-user-token)：用户级访问令牌接口，支持 OAuth 2.0 授权码模式和刷新令牌模式。
- [扫码登录第三方网站](https://open.dingtalk.com/document/app/scan-qr-code-to-log-on-to-third-party-websites)：用于钉钉客户端扫码确认登录第三方 Web 系统。

## 核心原则

1. **三层身份分离**
   AI Brain 登录账号、钉钉登录身份、钉钉 MCP 调用授权必须分层保存和校验。

2. **内部权限以 AI Brain 为准**
   钉钉登录只证明“此人是钉钉某企业中的某个用户”；是否能看需求、任务、知识、插件和系统配置，仍由 AI Brain `users`、RBAC 和数据范围决定。

3. **外部身份必须绑定内部用户**
   未绑定到 `users.id` 的钉钉身份不得获得默认业务权限。若开启自动开户，也只能按配置创建低权限用户或待审批用户。

4. **token 不进前端和日志**
   钉钉 `accessToken/refreshToken`、应用 `clientSecret/appSecret`、MCP URL Key 和其它密钥只保存在服务端密钥仓库或 `secret_ref`，不返回前端、不进入审计 payload、不进入模型上下文。

5. **回调必须防 CSRF 和开放跳转**
   OAuth `state` 一次性、短有效期、服务端保存；登录完成后的 `redirect` 只能是站内路径。

6. **生产回调使用 HTTPS 固定公网域名**
   钉钉开放平台回调地址必须与 AI Brain 配置一致。生产环境使用固定 HTTPS 域名；本地开发可通过 ngrok、frp 或企业公网网关临时映射。

## 术语

| 术语 | 说明 |
|------|------|
| AI Brain 用户 | `users` 表中的平台内部账号，是 RBAC 和审计 actor 的主体。 |
| 钉钉外部身份 | 来自钉钉 OAuth 的用户身份，例如企业、用户 ID、unionId、openId。 |
| 登录 token | AI Brain 自己签发的 JWT，业务 API 只接受它。 |
| 钉钉用户 token | 钉钉 OAuth 返回的用户级 access token，可用于获取用户身份或后续代表用户访问钉钉 API。 |
| MCP 授权 token | 钉钉 MCP 连接调用所需的 URL Key、应用凭证或用户授权 token。 |
| 自动开户 | 首次钉钉登录时自动创建 AI Brain 用户。 |
| 待审批账号 | 首次钉钉登录后创建 pending 记录，管理员确认前不能进入系统。 |

## 总体架构

```text
React 登录页
  -> GET /api/auth/providers
  -> GET /api/auth/dingtalk/start
  -> 钉钉 OAuth / 扫码登录
  -> GET /api/auth/dingtalk/callback
  -> AI Brain Auth Service
      -> 校验 state
      -> code 换钉钉 user token
      -> 获取钉钉用户身份
      -> corp 白名单校验
      -> 外部身份绑定 / 自动开户 / 待审批
      -> 签发一次性 login ticket
  -> 前端 POST /api/auth/dingtalk/exchange-ticket
  -> 返回 AI Brain JWT
```

### 模块边界

| 模块 | 职责 |
|------|------|
| `auth` | OAuth state、钉钉回调、login ticket、AI Brain JWT 签发、登录审计。 |
| `users` | 内部用户创建、状态、角色和账号管理。 |
| `external_identity` | 外部身份绑定、解绑、查找、待审批和冲突检测。 |
| `secret` | 钉钉应用密钥、用户 token 和 refresh token 的密钥引用管理。 |
| `system_settings` | 钉钉登录开关、corp 白名单、自动开户策略、默认角色和回调配置。 |
| `plugin_management` | 后续消费“当前登录用户钉钉授权”调用 MCP，不参与登录判断。 |
| `audit` | 登录、绑定、解绑、拒绝、失败、自动开户和管理员操作审计。 |

## 账号关联设计

### 推荐数据模型

保留 `users` 作为内部账号事实源。新增外部身份绑定表：

```sql
CREATE TABLE user_external_identities (
  id text PRIMARY KEY,
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider text NOT NULL,
  corp_id text NOT NULL,
  external_user_id text NOT NULL,
  union_id text,
  open_id text,
  display_name text,
  avatar_url text,
  email text,
  mobile_hash text,
  status text NOT NULL DEFAULT 'active',
  binding_source text NOT NULL DEFAULT 'self_service',
  last_login_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_external_identity UNIQUE (provider, corp_id, external_user_id)
);
```

其中：

- `provider` 首版固定为 `dingtalk`，后续可扩展。
- `corp_id + external_user_id` 是同一企业内钉钉用户的主要绑定键。
- `union_id` 用于辅助识别同一自然人在钉钉生态下的跨应用身份，但不得单独作为权限判定依据。
- `mobile_hash` 只保存哈希，用于管理员排查，不保存明文手机号。
- `binding_source` 可取 `admin_bound/self_service/auto_provision/pending_approval/migrated`。

如后续要代表用户调用钉钉 API 或 MCP，再新增用户 OAuth token 表：

```sql
CREATE TABLE user_oauth_tokens (
  id text PRIMARY KEY,
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider text NOT NULL,
  corp_id text NOT NULL,
  external_identity_id text REFERENCES user_external_identities(id) ON DELETE CASCADE,
  access_token_ref text NOT NULL,
  refresh_token_ref text,
  expires_at timestamptz,
  scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'active',
  last_refreshed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_user_oauth_provider_corp UNIQUE (user_id, provider, corp_id)
);
```

首版登录可以不落用户 OAuth token，只在回调阶段临时使用 token 获取身份；若确认要支持“以当前用户身份调用钉钉 MCP”，再启用该表和 refresh 流程。

### 绑定策略

| 策略 | 说明 | 推荐阶段 |
|------|------|----------|
| 管理员预绑定 | 管理员在用户管理中把 AI Brain 用户绑定到钉钉身份。 | 企业正式上线、关键角色 |
| 用户自助绑定 | 用户先用本地账号登录，再从个人中心发起钉钉绑定。 | P1 |
| 首次登录自动创建 | 钉钉身份未绑定时自动创建 AI Brain 用户。 | P0 可选 |
| 首次登录待审批 | 钉钉身份未绑定时创建 pending 记录，管理员审核后启用。 | P1 |

默认建议：

- 生产环境默认 `auto_provision=false`，由管理员预绑定或待审批。
- 内部试点可启用 `auto_provision=true`，默认角色只能是 `viewer`。
- 自动创建用户时 `username` 推荐使用 `dingtalk:<corp_id>:<external_user_id>` 或已验证邮箱；展示名使用钉钉昵称。
- 不能仅凭邮箱、手机号或 unionId 静默绑定已有高权限账号；匹配到已有账号时进入待确认绑定。

### 登录决策

```text
钉钉 callback 得到 code/state
-> 校验 state 和 redirect
-> code 换取钉钉 user token
-> 获取钉钉用户身份
-> 校验 corp_id 在允许列表
-> 查询 user_external_identities(provider=dingtalk, corp_id, external_user_id)
   -> active 绑定存在:
      -> 校验 users.status=active
      -> 更新 last_login_at
      -> 签发 AI Brain login ticket
   -> 绑定不存在:
      -> auto_provision=true:
         -> 创建 viewer 用户和 active 绑定
         -> 签发 login ticket
      -> pending_approval=true:
         -> 创建 pending 外部身份或登录申请
         -> 返回 DINGTALK_ACCOUNT_PENDING_APPROVAL
      -> 否则:
         -> 返回 DINGTALK_ACCOUNT_NOT_BOUND
```

## 登录流程

### 登录页展示

前端登录页启动时调用：

```http
GET /api/auth/providers
```

后端只返回启用且可展示的 provider，不返回密钥、corp 白名单明文详情或内部策略细节。

示例：

```json
{
  "data": {
    "local_password": {
      "enabled": true,
      "label": "账号密码登录"
    },
    "dingtalk": {
      "enabled": true,
      "label": "钉钉登录",
      "start_url": "/api/auth/dingtalk/start"
    }
  },
  "trace_id": "trace_auth_provider_001"
}
```

登录页规则：

- 本地账号密码入口保留，作为管理员兜底。
- 钉钉未配置或被禁用时不展示钉钉登录按钮。
- 钉钉启用时展示“钉钉登录”按钮。
- 钉钉登录失败时回到登录页并展示可读错误，不泄露 code、token 或内部配置。

### OAuth state 创建

```http
GET /api/auth/dingtalk/start?redirect=/welcome
```

服务端处理：

- 校验 `redirect` 是站内路径，拒绝 `//evil.com`、完整外部 URL 和 `/login` 循环跳转。
- 生成随机 `state`，保存 `state_hash/provider/redirect/expires_at/client_ip/user_agent`。
- 302 跳转到钉钉 OAuth 授权地址。

state 建议有效期 5 分钟，只能使用一次。

### 回调处理

```http
GET /api/auth/dingtalk/callback?code=<auth_code>&state=<state>
```

服务端处理：

- 校验 state 存在、未过期、未使用、provider 匹配。
- 使用钉钉应用凭证和 code 换取用户 token。
- 获取用户身份信息，解析 `corp_id/external_user_id/union_id/open_id/display_name/avatar_url` 等安全字段。
- 执行登录决策。
- 成功时生成一次性 `login_ticket`，302 回前端：

```text
/login/dingtalk/callback?ticket=<ticket>&redirect=/welcome
```

不允许把 AI Brain JWT、钉钉 access token 或 refresh token 放到 URL。

### ticket 换 AI Brain token

```http
POST /api/auth/dingtalk/exchange-ticket
```

请求：

```json
{
  "ticket": "<one_time_ticket>"
}
```

响应与本地登录保持一致：

```json
{
  "data": {
    "access_token": "<ai_brain_jwt>",
    "token_type": "bearer",
    "expires_in": 28800,
    "user": {
      "id": "user_xxx",
      "username": "dingtalk:corp_xxx:user_xxx",
      "display_name": "张三",
      "roles": ["viewer"]
    }
  },
  "trace_id": "trace_login_001"
}
```

ticket 必须一次性、短有效期。当前 P0 实现为 5 分钟有效，重复、过期或无效 ticket 统一返回 `DINGTALK_TICKET_INVALID`。

## 绑定与解绑流程

### 自助绑定

已登录用户在个人中心点击“绑定钉钉账号”：

1. 前端调用 `POST /api/auth/dingtalk/bind/start`。
2. 后端生成 bind state 并跳转钉钉授权页。
3. 回调后解析钉钉身份。
4. 若该钉钉身份未被其它用户绑定，写入 `user_external_identities`。
5. 若已绑定其它用户，返回 `EXTERNAL_IDENTITY_CONFLICT`。

自助绑定不改变用户角色和权限。

### 管理员绑定

系统管理用户详情页支持管理员绑定或解绑外部身份：

- 管理员可搜索待审批身份。
- 管理员可绑定到指定 AI Brain 用户。
- 管理员不能把一个钉钉身份同时绑定给多个用户。
- 管理员解绑最后一个登录方式前需确认，避免用户无法登录。

### 解绑

解绑只删除或停用外部身份绑定，不删除 `users` 账号，不删除历史审计 actor。解绑后用户仍可通过本地账号登录，若没有本地密码或其它身份源，则进入不可登录状态，需要管理员处理。

## 配置设计

### 环境变量

| 变量 | 说明 |
|------|------|
| `DINGTALK_LOGIN_ENABLED` | 是否启用钉钉登录。 |
| `DINGTALK_CLIENT_ID` | 钉钉 OAuth 应用 client id 或 app key。 |
| `DINGTALK_CLIENT_SECRET` | 本地或测试环境可直接提供钉钉应用密钥；生产建议使用密钥管理方案。 |
| `DINGTALK_CLIENT_SECRET_REF` | 钉钉应用密钥引用；当前实现支持 `env:ENV_NAME` 形式从环境变量解析。 |
| `DINGTALK_REDIRECT_URI` | 钉钉开放平台配置的回调地址。 |
| `DINGTALK_BIND_REDIRECT_URI` | 自助绑定回调地址；未配置且登录回调以 `/callback` 结尾时自动推导为 `/bind/callback`。 |
| `DINGTALK_ALLOWED_CORP_IDS` | 允许登录的企业 corp id 列表。 |
| `DINGTALK_AUTO_PROVISION` | 是否允许首次登录自动创建用户。 |
| `DINGTALK_AUTO_PROVISION_ROLE` | 自动创建用户默认角色，默认 `viewer`。 |
| `DINGTALK_PENDING_APPROVAL` | 未绑定身份是否进入待审批。 |
| `DINGTALK_FRONTEND_BASE_URL` | OAuth callback 完成后跳回前端的 base URL；未配置时默认使用 CORS origin 第一项。 |
| `DINGTALK_FRONTEND_CALLBACK_PATH` | 前端钉钉登录回调页路径，默认 `/login/dingtalk/callback`。 |
| `DINGTALK_AUTH_URL` / `DINGTALK_TOKEN_URL` / `DINGTALK_USERINFO_URL` | 钉钉 OAuth 授权、换 token 和读取用户信息的服务端点，默认使用钉钉开放平台当前接口地址。 |

### 系统管理配置

长期建议在系统设置中维护钉钉登录配置，环境变量作为启动兜底。配置项：

- 启用或停用钉钉登录。
- 回调地址展示和连通性检查。
- 企业 corp 白名单。
- 自动开户策略。
- 默认角色。
- 是否保存用户 OAuth token 以供 MCP 使用。
- 管理员测试登录配置，不保存真实用户 token。

系统配置响应必须只返回 `client_secret_configured=true/false`，不得返回 secret 明文或密钥引用细节。

## 与钉钉 MCP 插件的关系

钉钉登录和钉钉 MCP 插件必须保持边界：

| 能力 | 解决的问题 | token 使用 |
|------|------------|------------|
| 钉钉登录 | 用户是谁，是否允许进入 AI Brain | 只用于获取身份，登录后换成 AI Brain JWT |
| 钉钉 MCP 连接 | AI Brain 如何调用钉钉文档、审批、日历、消息等能力 | 使用连接配置中的 URL Key、应用 token 或用户 OAuth token |
| 当前用户钉钉授权调用 | 以当前登录用户身份访问钉钉资源 | 需要单独保存并刷新用户 OAuth token |

首版建议：

- 钉钉登录只做身份认证和账号绑定。
- MCP 插件继续使用现有连接配置。
- 后续在插件连接中增加“使用当前登录用户钉钉授权”选项时，再读取 `user_oauth_tokens`。
- 高风险 MCP 动作仍必须走 AI Brain 的人审、权限、审计和结果写入治理，不因钉钉登录而放开。

## 权限与审计

### 权限

- `GET /api/auth/providers`、`GET /api/auth/dingtalk/start`、`GET /api/auth/dingtalk/callback`、`POST /api/auth/dingtalk/exchange-ticket` 不要求已登录。
- 自助绑定、解绑要求当前用户已登录。
- 管理员绑定、审批外部身份要求 `system.users.manage`。
- 查看外部身份列表要求 `system.users.manage`，个人中心只允许查看自己的绑定摘要。

### 审计事件

| 事件 | 触发时机 | payload 要点 |
|------|----------|--------------|
| `dingtalk_login.succeeded` | 钉钉登录生成一次性 ticket 前 | user_id、corp_id |
| `dingtalk_account.provisioned` | 自动创建 AI Brain 用户并绑定钉钉身份 | user_id、corp_id、status |
| `dingtalk_account.bound` | 当前用户自助绑定成功 | user_id、corp_id |
| `dingtalk_account.unbound` | 当前用户解绑成功 | user_id |
| `auth.dingtalk.login_started` / `auth.dingtalk.login_failed` | 后续可选增强 | provider、redirect_hash、state_valid、reason；不得保存 code/token/secret |

payload 禁止保存 auth code、access token、refresh token、client secret、完整手机号、完整邮箱以外的敏感资料。手机号只允许 hash。

## 错误语义

| code | HTTP | 场景 |
|------|------|------|
| `DINGTALK_LOGIN_NOT_CONFIGURED` | 503 | 钉钉登录未启用或配置不完整。 |
| `DINGTALK_STATE_INVALID` | 400 / 前端回调错误 | state 缺失、过期、不匹配或已使用。 |
| `DINGTALK_AUTH_DENIED` | 前端回调错误 | 用户拒绝授权或钉钉返回授权错误。 |
| `DINGTALK_CODE_MISSING` | 前端回调错误 | callback 缺少授权码。 |
| `DINGTALK_UPSTREAM_ERROR` | 前端回调错误 | 钉钉 token 或用户信息接口调用失败。 |
| `DINGTALK_PROFILE_INCOMPLETE` | 前端回调错误 | 钉钉用户信息缺少可绑定主体。 |
| `DINGTALK_CORP_NOT_ALLOWED` | 403 | 钉钉企业不在白名单。 |
| `DINGTALK_ACCOUNT_NOT_BOUND` | 403 | 未绑定且未开启自动开户。 |
| `DINGTALK_ACCOUNT_PENDING_APPROVAL` | 403 | 登录申请等待管理员审批。 |
| `DINGTALK_ACCOUNT_INACTIVE` | 403 | 绑定的内部用户被停用。 |
| `EXTERNAL_IDENTITY_CONFLICT` | 409 | 钉钉身份已绑定其它 AI Brain 用户。 |
| `DINGTALK_TICKET_INVALID` | 401 | 一次性 ticket 缺失、过期、无效或已使用。 |

## 前端交互设计

登录页：

- 展示本地账号密码表单。
- 当 `/api/auth/providers.data.dingtalk.enabled=true` 时展示“钉钉登录”按钮。
- 点击按钮跳转 `start_url?redirect=<current_redirect>`。
- 回调页解析 `ticket`，调用 `exchange-ticket`，保存 AI Brain access token 和当前用户。
- 回调页展示处理中、成功跳转、失败重试和联系管理员四类状态。

个人中心：

- 展示钉钉绑定状态、企业名称、绑定时间、最近登录时间。
- 支持绑定、重新授权、解绑。
- 解绑前提示若没有其它登录方式会导致无法登录。

系统管理：

- 用户详情展示外部身份绑定列表。
- 支持管理员绑定、解绑、审批待绑定身份。
- 系统设置展示钉钉登录配置和回调地址检查。

## 安全设计

- P0 的 `state` 和 `login_ticket` 保存在服务端短期内存容器中，生产多实例部署时应升级为 Redis 或等价共享短期存储，并优先保存 hash。
- 当前 `state` 有效期 10 分钟，`login_ticket` 有效期 5 分钟，均一次性使用。
- OAuth 回调只接受配置中的 `redirect_uri`，生产必须 HTTPS。
- `redirect` 只允许站内相对路径，拒绝协议头和双斜杠路径。
- token 和 secret 使用服务端密钥仓库或 `secret_ref`，响应和审计只返回 configured 状态。
- 自动开户默认角色只能是 `viewer` 或待审批，不允许自动授予 `admin`、`product_owner`、`rd_owner`。
- 登录成功后重新加载 `/api/auth/me`，菜单和权限由后端授权快照决定。
- 绑定冲突必须明确阻断，不能自动迁移绑定。
- 退出登录只清理 AI Brain 本地登录态，不默认吊销钉钉 OAuth 授权。

## 运维与环境

### 回调域名

生产配置：

```text
https://brain.company.com/api/auth/dingtalk/callback
```

本地联调：

- 优先使用企业允许的公网测试域名或临时网关。
- ngrok/frp 可用于短期联调，但回调地址变化后需要同步钉钉开放平台配置。
- 不建议把开发者个人临时域名写入共享环境配置。

### 健康检查

系统设置页可提供钉钉登录健康检查：

- `enabled` 是否开启。
- `redirect_uri` 是否配置。
- `client_secret_configured` 是否为 true。
- `allowed_corp_ids` 是否非空。
- 最近一次登录成功/失败时间。

健康检查不得真实发起用户授权流程。

## 实施计划

### P0 已落地

- 新增钉钉登录环境配置。
- 新增 `user_external_identities` 表。
- 新增 auth provider 查询、start、callback、ticket exchange 接口。
- 新增当前用户自助绑定/解绑后端接口。
- 登录页增加钉钉登录按钮和回调页。
- 支持 corp 白名单、自动创建 viewer 或未绑定拒绝。
- 写入自动开户、登录成功、绑定和解绑审计。
- 保留本地账号密码登录。

### P1 管理与绑定

- 个人中心自助绑定/解绑 UI。
- 系统管理外部身份列表、管理员绑定、待审批处理。
- 自动开户策略可视化配置。
- 登录失败和绑定冲突排障视图。

### P2 MCP 用户授权联动

- 保存用户 OAuth token 的 secret_ref。
- 支持刷新 token。
- 插件连接可选择“使用当前登录用户钉钉授权”。
- 高风险钉钉 MCP 动作接入统一人审策略。

## 测试计划

### 后端

- `GET /api/auth/providers` 按配置返回本地和钉钉 provider。
- `start` 拒绝外部 redirect，生成一次性 state。
- callback 拒绝过期、重复、篡改 state。
- callback 处理 corp 白名单拒绝。
- 已绑定钉钉身份可换取 AI Brain JWT。
- 未绑定且自动开户关闭返回 `DINGTALK_ACCOUNT_NOT_BOUND`。
- 自动开户只创建 `viewer`，并写入外部身份绑定。
- `exchange-ticket` 一次性和过期语义正确。
- 绑定冲突返回 `EXTERNAL_IDENTITY_CONFLICT`。
- 审计 payload 不含 token、secret、auth code。

### 前端

- 未启用钉钉时登录页不展示按钮。
- 启用钉钉时展示按钮并携带 redirect。
- 回调页成功保存 access token 并跳转原路径。
- 回调页失败展示可读错误。
- 个人中心展示绑定状态。
- 管理员用户详情展示外部身份绑定。

### 安全与回归

- 本地账号登录仍可用。
- `/api/auth/me`、菜单和权限不因钉钉登录绕过 RBAC。
- scope 外产品、知识和定时作业仍不可见。
- 日志、审计、模型上下文和前端响应不包含钉钉 token。

## 后续评审问题

1. 生产默认策略采用“自动创建 viewer”还是“待审批”？
2. 是否要求保存用户 OAuth token 以便后续当前用户身份调用 MCP？
3. 是否需要同步钉钉企业部门和人员状态，还是只做登录时校验？
4. 钉钉登录配置是否进入系统设置页面并提供健康检查？
5. 生产回调域名和本地联调网关由谁维护？

## 后续待实现清单

- 个人中心展示钉钉绑定状态，并提供绑定、重新授权和解绑 UI。
- 系统设置维护钉钉登录配置、回调地址和健康检查。
- 系统管理用户详情展示外部身份绑定列表，支持管理员绑定和待审批处理。
- 多实例生产部署时将 OAuth `state` 和 `login_ticket` 从进程内存迁移到 Redis 或等价共享短期存储。
- 若后续需要“以当前用户身份调用钉钉 MCP”，再启用用户 OAuth token 刷新、密钥存储和权限治理。
- 增加真实浏览器 smoke：登录页 provider 展示、钉钉回调页换票、失败回调状态和本地登录兜底。
