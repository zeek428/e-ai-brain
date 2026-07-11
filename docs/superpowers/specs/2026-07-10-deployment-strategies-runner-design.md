# 运维部署方案与 Runner 执行设计

## 背景

当前运维部署只支持人工登记执行：部署单保存产品、版本、环境、分支、制品、窗口和回滚方案，点击“启动部署”后以 `executor_type=manual` 创建运行记录，再由人工登记成功、失败或回滚。系统没有可复用的部署方案，也不会真实触发远程部署、Docker Compose 或 Jenkins Job。

本次迭代在“运营治理 / 运维部署”内增加产品级部署方案，首批支持人工部署、SSH、Docker 和 Jenkins。SSH 与 Docker 复用现有本地 Runner 的任务队列、日志、取消、超时和完成回写；Jenkins 通过受管连接触发并同步 Job。部署方式是业务语义，Runner 是执行通道，两者不合并成同一个页面选项。

## 目标

- 按产品和环境维护可复用、可启停、可设默认值的部署方案。
- 部署单创建时选择方案并冻结方案快照，历史执行不受后续方案修改影响。
- 人工部署沿用人工状态登记。
- SSH 和 Docker 通过本地 Runner 执行，不让 AI Brain API 持有 SSH 私钥或直接执行本机 Shell。
- Jenkins 通过受管连接触发指定 Job，并能同步排队、执行、成功、失败和取消状态。
- 自动执行日志、外部任务标识、失败原因、审计事件和关联需求状态形成闭环。
- 保持产品范围权限、幂等、取消、超时和失败 Bug 生成规则。

## 非目标

- 本期不支持 Kubernetes、GitLab CI、蓝绿发布、金丝雀发布或多阶段发布编排。
- 本期不自动执行回滚；失败后由有权限人员确认并按回滚方案操作。
- 平台不在线编辑 Runner 本机的 SSH 私钥、known_hosts 或 Docker 凭据。
- 自动化测试不连接真实生产主机、不启动真实生产容器、不触发真实 Jenkins Job。
- 本期不建设通用 Vault；Jenkins 凭据继续使用现有密钥引用约定，SSH 凭据只在 Runner 本机解析。

## 术语

- `deployment_method`：用户选择的业务部署方式，取值为 `manual | ssh | docker | jenkins`。
- `executor_channel`：实际执行通道，取值为 `manual | runner | integration`。
- 部署方案：产品和环境下可复用的部署配置。
- Runner 目标：Runner 本机 `runner_config.json` 中维护的受控目标别名，包含 SSH 或 Docker 的本地配置。
- 方案快照：创建部署单时冻结的方案非敏感配置，用于审计和历史解释。

## 方案比较

### 方案 A：页面只展示“人工 / Runner / Jenkins”

SSH 和 Docker 作为 Runner 的子类型。实现字段较少，但用户无法直接按部署技术筛选，动态表单和失败诊断也会混在“Runner 部署”下，不采用。

### 方案 B：四种方式各自建设独立执行队列

页面语义清楚，但 SSH 和 Docker 会重复任务认领、日志、取消、超时、心跳和回写能力，运维成本高，不采用。

### 方案 C：业务方式分离，执行通道复用

页面展示人工、SSH、Docker、Jenkins四种方式；SSH和Docker统一创建 Runner 任务，Runner 根据方案快照中的目标别名选择本机白名单配置；Jenkins复用系统连接。该方案同时保持业务清晰和执行复用，采用此方案。

## 总体架构

```text
运维部署页面
  -> 部署方案（产品 + 环境 + method）
  -> 部署单（冻结 scheme_snapshot）
  -> 启动部署
       manual  -> 人工运行记录 -> 人工完成/失败/回滚
       ssh     -> Runner Task -> 本机目标别名 -> ssh -> 远端固定脚本
       docker  -> Runner Task -> 本机目标别名 -> docker compose
       jenkins -> Jenkins Connection -> Queue/Build -> 状态同步
  -> 部署运行记录 / 实时日志 / 审计
  -> 成功推进需求，失败恢复需求并生成 Bug
```

## 数据模型

### deployment_schemes

新增部署方案表：

| 字段 | 说明 |
|---|---|
| `id` | 方案编号 |
| `product_id` | 所属产品，必须执行产品 scope 校验 |
| `code` / `name` | 产品内唯一编码和显示名称 |
| `environment` | `dev/test/staging/prod/sandbox` |
| `deployment_method` | `manual/ssh/docker/jenkins` |
| `executor_channel` | 由服务端派生，不由页面自由填写 |
| `runner_id` | SSH、Docker必填 |
| `target_code` | SSH、Docker必填，引用Runner心跳公布的目标别名 |
| `jenkins_connection_id` | Jenkins必填，引用启用的Jenkins连接 |
| `jenkins_job_name` | Jenkins必填 |
| `timeout_seconds` | 执行或状态同步超时 |
| `config_json` | Jenkins参数映射、Docker/SSH非敏感覆盖项等扩展配置 |
| `is_default` | 是否为产品和环境的默认方案 |
| `status` | `active/disabled` |
| `version` | 乐观锁版本，防止并发覆盖 |
| `created_by/created_at/updated_at` | 审计字段 |

约束：

- `product_id + code` 唯一。
- 同一产品和环境最多一个启用的默认方案。
- `manual` 不允许保存 Runner 或 Jenkins 引用。
- `ssh/docker` 必须保存 `runner_id + target_code`，且 Runner 必须启用部署执行能力。
- `jenkins` 必须保存连接和 Job 名称。
- 被部署单引用的方案不能物理删除，只能停用。

### deployment_requests

增加：

- `deployment_scheme_id`：允许历史兼容记录为空。
- `deployment_method`：历史记录默认 `manual`。
- `executor_channel`。
- `scheme_snapshot jsonb`：冻结方案名称、方式、环境、Runner/目标别名或Jenkins Job等非敏感字段，不保存私钥、密码或Token。

### deployment_runs

增加：

- `deployment_method`。
- `runner_task_id`：SSH、Docker关联Runner任务。
- `plugin_invocation_log_id`：Jenkins调用日志引用。
- `idempotency_key`：同一部署单启动请求幂等。
- `external_queue_url/external_build_url`：Jenkins排队和构建地址。
- `execution_snapshot jsonb`：记录实际执行资源和状态同步元数据，不保存密钥。
- `next_sync_at/sync_attempts/sync_lease_owner/sync_lease_until`：Jenkins后台同步调度和多实例租约。

### ai_executor_tasks

现有表继续作为兼容的 Runner 任务队列，新增可空 `deployment_run_id` 外键和索引，并增加非终态 `cancel_requested`。Runner注册允许额外能力 `deployment`，但研发执行器策略仍只允许 Codex、Claude、Hermes、OpenClaw和系统模型网关，避免把部署执行器错误暴露为代码执行策略。

## API 设计

### 部署方案

- `GET /api/devops/deployment-schemes`
- `POST /api/devops/deployment-schemes`
- `PATCH /api/devops/deployment-schemes/{scheme_id}`
- `DELETE /api/devops/deployment-schemes/{scheme_id}`
- `GET /api/devops/deployment-runner-targets?runner_id=<id>&method=<ssh|docker>`

列表支持产品、环境、方式、状态、名称、服务端分页和排序。读权限为 `deployment.read`；新增 `deployment.scheme.manage` 高风险权限，默认授予管理员和发布负责人。所有读写继续执行产品 scope 校验。

### 部署单与运行

- 创建部署单增加必填 `deployment_scheme_id`；迁移为每个现有产品补建默认人工方案，新产品创建时同步创建默认人工方案。旧客户端未传时由服务端命中同产品、同环境的唯一启用默认方案，否则返回明确校验错误。
- 启动接口接收 `idempotency_key`，服务端使用唯一约束防止重复任务。
- 增加 `GET /api/devops/deployments/{id}/runs/{run_id}/logs`，统一返回人工、Runner和Jenkins日志视图。
- 增加 `POST /api/devops/deployments/{id}/runs/{run_id}/sync`，用于Jenkins状态同步和运维补偿。
- 取消接口根据运行类型通知Runner或Jenkins；部署单与运行记录先持久化进入 `cancelling`，只有Runner取消确认或Jenkins外部状态确认停止后才进入 `cancelled`。

## Runner 设计

### 本机配置

Runner包的 `runner_config.json` 增加：

```json
{
  "deployment_targets": {
    "production-ssh": {
      "name": "生产主机",
      "method": "ssh",
      "host": "app.internal",
      "port": 22,
      "username": "deploy",
      "identity_file": "/opt/ai-brain-runner/secrets/id_ed25519",
      "known_hosts_file": "/opt/ai-brain-runner/secrets/known_hosts",
      "remote_command": "/opt/company/bin/deploy-from-ai-brain"
    },
    "production-compose": {
      "name": "生产 Docker Compose",
      "method": "docker",
      "working_directory": "/srv/product",
      "compose_files": ["compose.yaml"],
      "project_name": "product",
      "services": ["api", "web"],
      "pull": true
    }
  }
}
```

Runner心跳只上报目标的 `code/name/method` 和就绪诊断，不上报主机、用户名、文件路径、私钥或Docker环境变量。

### SSH 执行

- 平台只向Runner发送结构化JSON：部署单、运行记录、目标别名、产品、版本、环境、分支、Commit和制品版本。
- Runner按目标别名读取本机配置，平台不能覆盖主机、用户名、私钥、known_hosts或远端命令。
- 本机使用无Shell argv调用 `ssh`，强制 `BatchMode=yes`、`StrictHostKeyChecking=yes` 和指定 `UserKnownHostsFile`。
- 远端命令固定；结构化部署上下文通过标准输入传给远端脚本，不拼接到Shell命令。
- stdout/stderr沿用Runner实时日志上传，退出码决定成功或失败。

### Docker 执行

- Runner按目标别名使用固定工作目录、Compose文件、项目名和服务白名单。
- 固定流程为可选 `docker compose pull`，随后执行 `docker compose up -d --remove-orphans`。
- 页面不能提交任意命令、Compose文件路径、工作目录或服务名。
- 制品版本等允许值通过受控环境变量传入，不拼接Shell命令。
- 命令使用无Shell argv执行，日志、超时、取消和退出码沿用Runner通用能力。

### 完成回写

Runner任务完成后，现有完成接口根据 `deployment_run_id`：

- 成功：部署运行和部署单进入成功，关联需求进入已发布。
- 失败、超时、死信：部署运行和部署单进入失败，关联需求恢复待发布，并按现有规则生成部署失败Bug。
- 取消：确认本地进程终止后进入已取消；未确认前保持取消中。

部署Runner任务收到取消请求时先进入 `cancel_requested`；Runner轮询到该状态后终止进程树，再通过现有完成接口回写 `cancelled`。取消请求本身不再提前写成终态，从而区分“已请求取消”和“已确认停止”。

## Jenkins 设计

- 增加官方Jenkins插件/连接模板，协议为HTTP，认证支持Basic用户名和API Token密钥引用。
- Jenkins运行时解析 `env:NAME` 密钥引用；直接凭据只允许本地开发兼容，响应、方案快照、审计和日志统一脱敏。
- 方案绑定连接和Job名称，可维护参数映射；参数值仅从部署快照白名单字段解析。
- 启动时调用 `buildWithParameters`，保存Queue Location和调用日志。
- 状态同步先查询Queue获取Build编号，再查询Build API获取 `building/result/url/duration`。
- 页面运行中自动轮询；后台补偿扫描和“同步状态”按钮保证页面关闭后仍可收敛。
- API lifespan启动Jenkins部署状态同步器；同步器按 `next_sync_at` 认领记录，使用 `sync_lease_owner/sync_lease_until` 和 `FOR UPDATE SKIP LOCKED` 避免多实例重复轮询，并以退避策略更新下一次同步时间。
- 成功、失败、取消分别映射部署状态，并写入或更新关联Jenkins发布记录。
- 取消优先取消Queue项；已有Build时调用stop端点。无法确认停止时保持取消中。

## 页面设计

`/governance/deployments` 增加：

- “部署单”页签：展示部署方案、方式、执行通道、运行状态和执行日志。
- “部署方案”页签：展示产品、环境、方式、默认方案、Runner/目标或Jenkins资源、状态和更新时间。
- 新增/编辑方案使用动态表单：人工无执行资源；SSH、Docker选择Runner和就绪目标；Jenkins选择连接、Job和参数映射。
- 创建部署单按产品和环境自动选择默认方案，可切换其它启用方案。
- 启动前显示只读执行摘要和资源就绪状态。
- 自动部署运行中提供日志抽屉和自动刷新；人工部署继续提供人工结果登记。

## 状态与错误处理

- 部署方案：`active | disabled`。
- 部署运行：`queued | running | cancelling | success | failed | cancelled | timed_out | rolled_back`。
- 部署单状态约束新增真实 `cancelling` 状态，不允许外部任务仍运行时显示最终取消。
- `DEPLOYMENT_SCHEME_REQUIRED`：未选择方案且无法唯一命中默认方案。
- `DEPLOYMENT_SCHEME_DISABLED`：方案已停用。
- `DEPLOYMENT_RUNNER_UNAVAILABLE`：Runner离线或并发能力不足。
- `DEPLOYMENT_TARGET_NOT_READY`：目标未上报、类型不匹配或本机诊断失败。
- `DEPLOYMENT_JENKINS_UNAVAILABLE`：连接、认证或Job不可用。
- `DEPLOYMENT_ALREADY_RUNNING`：已有活动运行，拒绝重复启动。
- `DEPLOYMENT_EXTERNAL_CANCEL_PENDING`：已请求取消但尚未确认外部停止。

所有错误返回 `trace_id`，页面展示业务提示而不是裸 `Failed to fetch`。

## 权限与审计

- `deployment.read`：读取方案、部署单、运行和日志。
- `deployment.create`：创建部署单。
- `deployment.execute`：启动、同步、完成、失败和回滚。
- `deployment.cancel`：取消部署。
- `deployment.scheme.manage`：创建、编辑、停用部署方案。
- 平台端所有资源按产品scope过滤；Runner认领继续使用Runner Token和任务归属校验。
- 方案变更、部署启动、Runner任务创建、Jenkins触发、状态同步、取消、成功、失败和超时均写审计。
- 审计和方案快照不记录私钥、密码、Token、完整环境变量或敏感日志。

## 测试策略

### 后端

- 部署方案CRUD、默认方案唯一性、乐观锁、依赖删除和产品scope。
- 四种部署方式的字段约束、方案快照和启动分流。
- 幂等启动、并发启动、取消确认、超时、Runner/Jenkins完成回写。
- 成功推进需求、失败恢复需求和失败Bug去重。
- PostgreSQL迁移、repository边界、SQL分页和权限回归。

### Runner

- Runner包包含部署目标配置和内置部署执行能力。
- SSH目标白名单、host key校验、固定命令、无Shell argv和JSON标准输入。
- Docker工作目录、Compose文件、服务白名单、受控环境变量和无Shell argv。
- 实时日志、取消、超时和完成回写使用模拟子进程验证。

### Jenkins

- 使用本地模拟HTTP服务验证认证、触发、Queue到Build转换、结果同步和取消。
- 测试密钥脱敏、参数白名单和调用日志。

### 前端与真实页面

- 部署方案页签、动态表单、默认方案和权限按钮。
- 部署单创建、启动摘要、运行日志、自动刷新、同步和取消状态。
- 真实PostgreSQL API与前端页面验收，不连接真实生产目标。
- 更新帮助中心操作说明和真实页面截图。

## 验收标准

- 用户可为授权产品配置四种部署方式，并按环境设置唯一默认方案。
- SSH、Docker方案只能选择Runner已上报且类型匹配的目标。
- SSH私钥和目标敏感配置不进入数据库、API响应、日志或审计。
- SSH、Docker部署可创建Runner任务，实时显示日志，并自动回写最终结果。
- Jenkins可触发Job、取得Build状态、同步结果并支持取消。
- 重复启动不会生成重复Runner任务或Jenkins Build。
- 自动部署成功后关联需求进入已发布；失败或超时后恢复待发布并生成单个失败Bug。
- 无权限或产品scope外用户不能读取或操作方案、运行和日志。
- 自动化测试、类型检查、构建、帮助检查和真实页面验收通过。
