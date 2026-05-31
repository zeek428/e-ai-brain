# 监控配置

## 监控目标

v1 监控以本地和测试环境可诊断为目标，确保 web、api、PostgreSQL + pgvector、Redis、LangGraph 运行和模型网关调用出现问题时能快速定位。

## SLO 目标

| 能力 | Local | Staging | Production |
|------|-------|---------|------------|
| API 可用性 | 手动健康检查通过 | 99% | 99.5% 或按企业内部 SLA 调整 |
| 任务详情查询 P95 | < 500ms | < 500ms | < 500ms |
| 知识检索 P95 | < 1s | < 1s | < 1s |
| 首页看板 P95 | < 800ms | < 800ms | < 800ms |
| 模型网关失败率 | 可诊断 | < 5% | < 2% |
| pending 人工确认积压 | 可见 | 超过团队日处理量告警 | 超过团队日处理量告警 |

## 监控架构

```text
Docker Compose services
  ├─ web logs
  ├─ api logs
  ├─ postgres logs / health
  └─ redis logs / health
        │
        ▼
本地排查：docker compose ps/logs + /health + audit_events
        │
        ▼
后续演进：OpenTelemetry / Prometheus / Grafana / Sentry
```

## 监控指标

### 基础指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| API 容器状态 | FastAPI 服务是否运行 | 容器退出或健康检查失败。 |
| Web 容器状态 | React 工作台是否运行 | 容器退出或页面不可访问。 |
| PostgreSQL 状态 | 数据库连接和 pgvector 可用性 | 连接失败或迁移失败。 |
| Redis 状态 | 缓存/队列依赖可用性 | 连接失败。 |
| 磁盘空间 | PostgreSQL 数据卷空间 | 测试/生产环境按容量阈值告警。 |

### 应用指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| API 错误率 | 5xx 和未处理异常比例 | 测试/生产环境 > 1%。 |
| API 响应时间 | 常规 API P95/P99 | 常规接口 P95 > 500ms 需排查。 |
| Graph 运行失败数 | LangGraph run 失败或卡住数量 | 连续失败或长时间 running。 |
| 模型调用失败数 | model_gateway 调用超时、重试、失败 | 连续失败或供应商错误率升高。 |
| 知识检索延迟 | `/api/knowledge/search` 延迟 | P95 > 1s 需排查索引和权限过滤。 |
| 审计写入失败 | audit_events 写入异常 | 任意失败都需要排查。 |

### 业务指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| AI 任务创建数 | 每日/每小时创建任务数量 | 异常归零或突增。 |
| 等待人工确认任务数 | `waiting_review` 任务积压 | 超过团队处理能力。 |
| 等待补充信息任务数 | `waiting_more_info` 任务积压 | 长时间无人补充。 |
| 任务完成率 | completed / created | 明显下降。 |
| 知识沉淀待审核数 | pending deposits 数量 | 长时间积压。 |

## 健康检查

API 健康检查接口：

```http
GET /health
```

推荐返回结构：

```json
{
  "status": "ok",
  "postgres": "ok",
  "redis": "ok",
  "model_gateway": "not_configured"
}
```

健康状态枚举：

| 字段 | 当前取值 |
|------|----------|
| status | `ok` 或 `degraded` |
| postgres | `ok` 或 `error` |
| redis | `ok` 或 `error` |
| model_gateway | `configured` 或 `not_configured` |

模型网关健康检查默认只验证配置，不建议每次真实调用模型。未配置真实 API Key 或 Base URL 时返回 `not_configured`；AI 任务启动会返回明确错误，不生成本地输出。

## 日志配置

### 日志类型

| 日志 | 来源 | 必备字段 |
|------|------|----------|
| API 请求日志 | api | trace_id, user_id, method, path, status, latency_ms |
| 错误日志 | api | trace_id, module, error_code, error_message |
| Graph 节点日志 | graph_runtime | trace_id, ai_task_id, graph_run_id, node, status, latency_ms |
| 模型调用日志 | model_gateway | trace_id, provider, model, purpose, tokens, latency_ms, status |
| 检索日志 | knowledge | trace_id, user_id, query_hash, top_k, result_count, latency_ms |
| 回写日志 | integration | trace_id, ai_task_id, idempotency_key, issue_count, status |

### 敏感信息要求

- 不记录完整 prompt 和模型输出。
- 不记录模型 API Key、Bearer Token、密码。
- 对邮箱、手机号等敏感信息做脱敏或哈希。

## 常用排查命令

```bash
# 查看服务状态
docker compose ps

# 查看 API 日志
docker compose logs api

# 查看数据库日志
docker compose logs postgres

# 查看 Redis 日志
docker compose logs redis

# 健康检查
curl http://localhost:8000/health
```

## 告警配置

v1 本地环境不强制配置外部告警。测试/生产环境建议按以下级别落地：

| 级别 | 说明 | 示例 |
|------|------|------|
| P0 | 核心闭环不可用 | API 不可用、数据库不可用、任务无法创建。 |
| P1 | 主要能力异常 | Graph 连续失败、模型网关不可用、知识检索失败。 |
| P2 | 体验或积压问题 | waiting_review 长时间积压、检索延迟升高。 |
| P3 | 提示性问题 | 单次任务失败、低频外部依赖抖动。 |

### 生产告警阈值

| 告警 | 级别 | 触发条件 | 首要动作 |
|------|------|----------|----------|
| API 不可用 | P0 | `/health` 连续失败 3 次 | 查看 API 日志、数据库、Redis 和最近发布。 |
| 数据库不可用 | P0 | API 无法连接 PostgreSQL 或迁移失败 | 停止发布，进入数据库故障流程。 |
| 权限过滤异常 | P0 | 知识检索返回无权限内容 | 立即禁用相关检索入口并排查权限规则。 |
| GitLab 回写边界异常 | P0 | 发现系统向 GitLab 写评论、审批或合并状态 | 立即停用 code_review 执行器和 GitLab 凭据。 |
| 模型网关失败率升高 | P1 | 15 分钟失败率超过阈值 | 切换供应商配置或降级到人工处理。 |
| Graph 任务积压 | P1 | running 或 waiting_review 超过团队容量 | 排查 Graph、模型网关和人工确认队列。 |
| 审计写入失败 | P1 | 高影响动作无审计事件 | 暂停高影响 AI 动作，修复审计链路。 |

## 后续演进

- 接入 OpenTelemetry 统一 trace。
- 接入 Prometheus/Grafana 采集容器和应用指标。
- 接入 Sentry 或等价错误追踪系统。
- 接入统一 trace 后，可将 API 请求日志、运行日志和审计事件通过 trace_id 关联；当前审计事件主要通过 ai_task_id、event_type 和 created_at 排查。

---
最后更新: 2026-05-27
