# 部署流程

## 当前源码状态提示

本 runbook 描述目标实现状态下的本地或 v1 演示部署流程。若当前 checkout 仍只有文档集，且尚未包含应用源码、`.env.example` 或 `docker-compose.yml`，请先完成基础工程初始化，再执行部署命令。

## 环境定位

| 环境 | 目标 | 发布要求 |
|------|------|----------|
| Local | 开发和演示闭环 | Docker Compose 可启动，P0 API 和 P0 测试通过。 |
| Staging | 企业试点前验证 | 使用脱敏数据，执行迁移、备份恢复、监控告警和权限验证。 |
| Production | 企业内部正式使用 | 需要变更审批、备份恢复演练、SLO 告警、密钥轮换计划和回滚方案。 |

当前仓库仍以文档和本地栈为主；production 条目是上线准入要求，不代表当前实现已经满足。

## 触发条件

- 本地开发环境初始化。
- v1 演示环境部署。
- 验证 web、api、PostgreSQL + pgvector、Redis、模型网关和内部 GitLab MR Code Review 只读链路是否能协同启动。

## 前置条件

- [ ] 已复制 `.env.example` 为 `.env` 并填写必要配置。
- [ ] Docker Compose 可用。
- [ ] `docker compose config` 校验通过。
- [ ] 普通 additive 数据库迁移已随 API 镜像或启动流程执行；显式 cutover cleanup 与并发大索引路径已按下述边界单独核验。
- [ ] 已配置默认模型网关，API Key 只存在 `.env` 或密钥管理系统中。
- [ ] 已配置内部 GitLab 只读凭据引用和产品 Git 资源绑定；凭据不得出现在 API 响应、执行器输入或日志中。
- [ ] 已配置 code-review 执行器适配器；未配置时必须让 code_review 任务失败为可排查状态，而不是静默跳过。
- [ ] 已准备生产就绪门禁脚本所需变量：`READINESS_BEARER_TOKEN` 或 `READINESS_USERNAME`/`READINESS_PASSWORD`，以及 `READINESS_GITLAB_REPOSITORY_ID`、`READINESS_GITLAB_MR_IID`、`READINESS_REQUIREMENT_ID`、`READINESS_TECHNICAL_SOLUTION_TASK_ID`。如 `docker` 不在 PATH，设置 `READINESS_DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker`。
- [ ] 非本地/非测试环境已配置至少 32 位且非占位的 `APP_SECRET_KEY`，并保持 `ALLOW_SEEDED_USERS=false`。

## 发布准入门禁

- [ ] P0/MVP 测试用例通过，生产就绪用例无阻塞项。
- [ ] 数据库迁移脚本和回滚脚本已评审。
- [ ] 最近一次备份恢复演练通过，恢复数据可被应用读取。
- [ ] 模型 API Key、GitLab 只读凭据和 APP_SECRET_KEY 不出现在仓库、日志或 API 响应中。
- [ ] 生产就绪门禁使用真实管理员 Token 或真实管理员账号，不使用 `admin@example.com` / `admin123` 等内置种子账号。
- [ ] GitLab MR Code Review 只读链路验证通过，不会回写评论、审批状态、request changes、合并状态或分支。
- [ ] 监控告警、trace_id 关联和审计查询可用。
- [ ] 回滚负责人、审批人和沟通渠道已确认。

## 部署步骤

### 1. 准备阶段

```bash
# 检查工作目录
pwd

# 校验 Compose 配置
docker compose config
```

### 2. 构建与启动

```bash
docker compose up -d --build
```

#### 数据库迁移执行边界

正常 API 容器启动只执行普通 additive SQL，并显式跳过以下迁移：

- `121_requirement_driven_rd_cutover.sql`：破坏性切换 cleanup，只能在维护围栏进入 `cutover_locked`、Schema v2 和新应用健康证据满足后，通过 `scripts/rd_collaboration_cutover.py cleanup --execute` 显式执行；不得依赖重启 API 容器触发。
- `125_rd_dispatch_due_index.sql`、`126_rd_dispatch_page_index.sql`、`127_rd_active_run_dispatch_index.sql`、`128_rd_dependency_successor_index.sql`：大表派发索引，不在入口脚本的逐文件 SQL 循环中执行。

正常非测试 API 初始化会由 repository schema-compatibility 路径接管 125-128：在 autocommit 连接上尝试同一个 PostgreSQL advisory lock；取得锁的实例逐个检查索引是否 `valid` 且 `ready`，无效索引使用 concurrent drop 后，以 `CREATE INDEX CONCURRENTLY` 创建；未取得锁的并发实例立即继续启动，不等待持锁实例。该路径在后续 API 启动时会再次检查，因此跳过不表示迁移完成。发布观察中应确认 API 日志没有 compatibility index 错误，并在 PostgreSQL 验证四个索引均有效、可用；如果 concurrent DDL 失败，不得改用会长期阻塞业务写入的普通 `CREATE INDEX` 临时绕过。

### 3. 验证服务

```bash
# API 健康检查
curl http://localhost:8000/health

# 查看服务状态
docker compose ps

# 查看 API 日志
docker compose logs api
```

### 4. 运行发布 Smoke 门禁脚本

推荐使用固定入口，默认会重建本地 Docker Compose 栈并运行 API + Web 真实页面门禁：

```bash
READINESS_BEARER_TOKEN=<admin-bearer-token> \
READINESS_GITLAB_REPOSITORY_ID=<repository_id> \
READINESS_GITLAB_MR_IID=<mr_iid> \
READINESS_REQUIREMENT_ID=<requirement_id> \
READINESS_TECHNICAL_SOLUTION_TASK_ID=<technical_solution_task_id> \
./scripts/release_smoke.sh
```

如需自定义地址或 Docker 路径，可通过环境变量覆盖：

```bash
READINESS_API_BASE_URL=http://localhost:8000 \
READINESS_WEB_BASE_URL=http://localhost:5173 \
READINESS_DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker \
./scripts/release_smoke.sh
```

底层仍可直接调用生产就绪门禁脚本：

```bash
READINESS_API_BASE_URL=http://localhost:8000 \
READINESS_DOCKER_BIN=/Applications/Docker.app/Contents/Resources/bin/docker \
READINESS_BEARER_TOKEN=<admin-bearer-token> \
READINESS_GITLAB_REPOSITORY_ID=<repository_id> \
READINESS_GITLAB_MR_IID=<mr_iid> \
READINESS_REQUIREMENT_ID=<requirement_id> \
READINESS_TECHNICAL_SOLUTION_TASK_ID=<technical_solution_task_id> \
./scripts/production_readiness_check.py --rebuild --web-smoke
```

`release_smoke.sh` 固定调用 `scripts/production_readiness_check.py --rebuild --web-smoke`。该脚本会先执行 `docker compose up -d --build`，随后验证 `docker compose config --quiet`、compose 中 `api/web/postgres/redis` 运行状态、`/health`、Redis `PONG`、PostgreSQL `pgcrypto`/`vector` 扩展、Web shell HTML、模型网关配置脱敏和 active/default 配置、需求/任务/Bug/用户洞察/研发运营核心列表、GitLab MR preview 与 snapshot 只读链路；并调用 `scripts/web_page_smoke.mjs`，通过真实 Chrome/Chromium 登录并打开 `/welcome`、需求、迭代版本、Bug、任务、用户洞察、研发运营和角色管理等核心页面，检查非空渲染、未跳回登录页、无框架错误覆盖层、无 console/runtime error，并监听浏览器网络响应，任一路由期间出现非 favicon 的 4xx/5xx 请求都会让该路由 smoke 失败。生产就绪门禁默认额外断言角色管理页出现“系统管理员”；其他页面可通过 `--expect-text ROUTE=TEXT` 增加关键内容断言，避免页面壳非空但核心数据未渲染的假阳性。脚本任一检查失败即返回非 0；不得在失败时宣称环境可发布。门禁不接受内置种子账号默认凭据，推荐使用 `READINESS_BEARER_TOKEN`；若使用 `READINESS_USERNAME`/`READINESS_PASSWORD`，必须是已创建的真实管理员账号。可通过 `READINESS_WEB_BASE_URL` 或 `--web-base-url` 指向非默认 Web 地址；如 Chrome 不在默认路径，设置 `READINESS_CHROME_PATH`。

本地代码启动 API 时，可用真实全链路回归脚本验证业务闭环：

```bash
FULL_CHAIN_USERNAME=<real-admin-email> \
FULL_CHAIN_PASSWORD=<real-admin-password> \
./scripts/full_chain_regression.py \
  --api-base-url http://localhost:8000 \
  --json-output /tmp/ai-brain-full-chain-report.json
```

该脚本只调用公开 API，不直接写数据库或 MemoryStore；默认通过管理员显式 `execution_mode=deterministic` 启动 AI 任务，跳过研发执行器 Runner 和外部模型网关波动，但仍写入 `ai_task.deterministic_execution_used` 审计。脚本覆盖产品、迭代版本、用户反馈转需求、批量排期、AI 任务、Review、知识沉淀、版本代码分支、本地完整代码巡检、Bug/整改任务写回、版本驾驶舱、统一 full-chain、团队看板、AI 助手引用、AI 动作草案治理和权限可视化，并校验扫描 finding、提交人归因、治理覆盖率、治理压力总览、看板计数、助手会话历史、草案确认审计和角色权限诊断。代码巡检治理压力必须能暴露质量门禁失败、活跃严重问题，并确认严重 finding 的 Bug 和整改任务覆盖已闭环；版本驾驶舱必须校验 `evidence_coverage` 证据域顺序、状态、阻断/缺口计数和覆盖分，防止版本总览证据覆盖在局部页面可见但自动验收不断链。`--json-output` 或 `FULL_CHAIN_JSON_OUTPUT` 会在成功和失败时输出结构化验收报告，包含 suite、开始/结束时间、耗时、步骤列表、失败原因和 `coverage` 覆盖矩阵；`coverage.covered_keys/skipped_keys` 用于区分完整主链路与局部快速 suite，避免 CI 把单域回归误判为全链路验收。需要一次跑完快速治理门禁时，可执行 `--suite all-targeted`，它会串行运行 Runner、版本总览、AI 助手问答、草案治理、代码巡检治理、知识索引健康和权限可视化，且 `coverage.is_complete_chain=false`，不能替代默认 `--suite full` 的端到端主链路。需要验证真实模型网关时，可切换为 `--task-execution-mode model_gateway`。

### 5. 验证数据库与缓存

```bash
# PostgreSQL 容器日志
docker compose logs postgres

# Redis 容器日志
docker compose logs redis
```

### 6. 验证 v1 MVP AI 链路

```bash
# 登录并获取 Bearer Token 后，验证模型网关配置只返回 configured 标记
curl http://localhost:8000/api/system/model-gateway-configs \
  -H "Authorization: Bearer <token>"

# 验证内部 GitLab MR 预览只读链路
curl http://localhost:8000/api/devops/gitlab/merge-requests/<repository_id>/<mr_iid>/preview \
  -H "Authorization: Bearer <token>"

# 验证 MR diff 快照可以创建，且响应只返回 snapshot_id 和摘要信息
curl -X POST http://localhost:8000/api/devops/gitlab/merge-requests/<repository_id>/<mr_iid>/snapshot \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"requirement_id":"requirement_001","technical_solution_task_id":"task_tech_001"}'
```

上述检查不得在 GitLab MR 中新增评论、改变审批状态、request changes、合并状态或分支。

## 回滚方案

本地或 v1 演示环境回滚以停止当前栈、恢复上一版本镜像或代码为主。

```bash
# 停止服务
docker compose down

# 如需清理本地构建镜像，先确认不会影响其他项目后再执行 Docker 清理命令
```

如涉及数据库结构变更，必须先查阅对应迁移和回滚脚本，不得直接删除数据库卷来规避问题。

### Staging / Production 回滚要求

1. 优先回滚应用版本，避免直接回滚数据库结构。
2. 若迁移不可逆，必须使用已验证备份恢复方案，并记录数据影响范围。
3. 回滚后执行 `/health`、数据库扩展检查、Redis 检查、模型网关配置检查、GitLab 只读链路检查和审计查询。
4. 回滚完成后在故障报告中记录触发原因、影响窗口、恢复动作和后续改进。

### 备份恢复门禁

- [ ] PostgreSQL 备份文件存在且可恢复到隔离环境。
- [ ] pgvector 数据恢复后知识检索 smoke test 通过。
- [ ] Redis 不作为长期事实来源，恢复流程不得依赖 Redis 保留业务事实。
- [ ] 审计事件恢复后可按 ai_task_id 和 subject 查询。

## 验证清单

- [ ] `docker compose config` 通过。
- [ ] `docker compose ps` 中 web、api、postgres、redis 均正常。
- [ ] `/health` 返回健康状态。
- [ ] PostgreSQL 初始化包含 pgvector 扩展。
- [ ] Redis 可连接。
- [ ] API 日志无启动错误。
- [ ] 普通 API 启动未执行 `121_requirement_driven_rd_cutover.sql`，且四个派发索引 125-128 已由 repository compatibility 路径确认为 valid/ready；并发启动未因索引 advisory lock 相互等待。
- [ ] `./scripts/release_smoke.sh` 通过，核心页面真实浏览器 smoke 无空白页、无控制台错误。
- [ ] 本地代码运行态使用真实管理员 `FULL_CHAIN_USERNAME`/`FULL_CHAIN_PASSWORD` 执行 `./scripts/full_chain_regression.py --api-base-url http://localhost:8000` 通过，确认真实全链路业务写入、代码巡检和 full-chain 聚合正常；日常快速治理回归可补充执行 `./scripts/full_chain_regression.py --suite all-targeted --api-base-url http://localhost:8000`，其中包含确定性 AI 助手问答 smoke，但不能替代完整主链路验收。
- [ ] 模型网关配置可查询，API Key 只返回 configured 标记，不返回明文或密钥片段。
- [ ] 产品 Git 资源可绑定内部 GitLab 项目，凭据不在 API 响应或日志中出现。
- [ ] MR preview 能返回标题、作者、分支、diff refs 和变更文件数。
- [ ] MR snapshot 能生成不可变 snapshot_id，并记录 diff_size_bytes、created_at 和审计事件。
- [ ] code_review 执行器失败时返回明确错误码和 trace_id，不静默生成空报告。
- [ ] code_review 全流程不会向 GitLab 回写评论、审批状态、request changes、合并状态或分支变更。

## 常见问题

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| API 健康检查失败 | API 容器未启动或端口不一致 | 查看 `docker compose ps` 和 `docker compose logs api`。 |
| 数据库连接失败 | `.env` 与 compose 服务名不一致 | 使用 compose 内部服务名连接 PostgreSQL。 |
| pgvector 初始化失败 | 镜像或迁移配置不支持扩展 | 检查数据库镜像和 `001_init.sql`。 |
| API 启动期间派发索引报错或缺失 | 125-128 的 concurrent compatibility DDL 失败、索引无效，或本实例未取得 advisory lock | 查看 API/PostgreSQL 日志和 `pg_index.indisvalid/indisready`；让后续单实例启动重新校验，不能把 125-128 放回普通入口事务，也不能手工执行 121。 |
| 前端访问 API 失败 | API base URL 配置错误 | 检查 web 环境变量和浏览器网络请求。 |
| MR 预览失败 | GitLab 项目未绑定、凭据无权限或 MR 不存在 | 检查产品 Git 资源、凭据引用、repository_id 和 mr_iid。 |
| MR 快照失败或 diff 过大 | GitLab API 超时、限流或 diff 超过配置上限 | 重试、拆分 MR 或缩小 Review 范围，不允许静默截断正式报告。 |
| code-review 报告为空 | 执行器未配置、超时或 schema 校验失败 | 查看任务详情、执行器错误码、trace_id 和 API 日志。 |

## 联系人

- 负责人: Project Maintainers
- 升级路径: 以 [项目级技术规格](../02-specs/enterprise-ai-brain/spec.md)、[API 文档](../02-specs/enterprise-ai-brain/api.md) 和本 runbook 为准。

---
最后更新: 2026-06-05
