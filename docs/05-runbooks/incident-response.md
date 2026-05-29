# 故障响应

## 故障等级定义

| 级别 | 定义 | 响应目标 | 示例 |
|------|------|----------|------|
| P0 | 核心闭环不可用 | 立即处理 | API/数据库不可用，AI 任务无法创建或启动。 |
| P1 | 主要能力异常 | 优先处理 | LangGraph 连续失败、模型网关不可用、知识检索不可用。 |
| P2 | 局部功能异常 | 排期处理 | 单个任务失败、导出失败、审计查询变慢。 |
| P3 | 轻微问题 | 常规处理 | 文案、低频边界问题、非阻塞告警。 |

## 角色与升级

| 角色 | 职责 |
|------|------|
| Incident Commander | 统一协调、定级、决策恢复和回滚。 |
| Tech Lead | 定位 API、Graph、数据库、Redis、模型网关和 GitLab 集成问题。 |
| Product Owner | 判断业务影响、用户沟通和功能降级优先级。 |
| Security Owner | 处理密钥泄漏、越权访问、GitLab 回写边界和审计缺失。 |

## RTO / RPO 目标

| 环境 | RTO | RPO | 说明 |
|------|-----|-----|------|
| Local | 尽快恢复 | 不承诺 | 开发环境可重建。 |
| Staging | 4 小时 | 24 小时 | 使用脱敏数据。 |
| Production | 1 小时 | 15 分钟或按企业 SLA | 需依赖正式备份策略和变更审批。 |

## 故障处理流程

### 1. 发现与确认

- [ ] 记录故障时间、发现方式和 trace_id。
- [ ] 确认影响范围：web、api、postgres、redis、model_gateway、graph_runtime、knowledge。
- [ ] 确定故障等级。
- [ ] 保留相关日志，避免先清理容器或数据卷。

### 2. 响应与定位

- [ ] 查看 `docker compose ps`。
- [ ] 查看相关服务日志。
- [ ] 调用 `/health` 检查依赖状态。
- [ ] 按 trace_id 查询请求/运行日志，按 ai_task_id 查询审计事件和 Graph 运行记录。
- [ ] 判断是否为配置、数据库、Redis、模型网关或 Graph 节点问题。

### 3. 处理与恢复

- [ ] 优先恢复服务可用性。
- [ ] 对单个失败任务优先使用 retry/cancel，不直接修改数据库状态。
- [ ] 对数据库迁移问题先确认迁移脚本和回滚脚本。
- [ ] 恢复后重新执行健康检查和关键业务路径。

### 4. 复盘与改进

- [ ] 记录时间线、根因、影响范围和恢复动作。
- [ ] 补充缺失监控或审计字段。
- [ ] 必要时更新 PRD/spec/API/test-case 和 runbook。

## 常见故障处理

### API 服务不可用

**现象**: `/health` 无响应或返回错误。

**排查步骤**:
```bash
docker compose ps
docker compose logs api
curl http://localhost:8000/health
```

**恢复建议**:
- 检查 `.env` 中 `DATABASE_URL`、`REDIS_URL`、`APP_SECRET_KEY`。
- 修复配置后重启 API 服务。
- 不要通过删除数据库卷来绕过迁移或启动错误。

### PostgreSQL 或 pgvector 故障

**现象**: API 日志出现数据库连接失败、pgvector extension 缺失、embedding 写入失败。

**排查步骤**:
```bash
docker compose logs postgres
docker compose ps postgres
```

**恢复建议**:
- 确认 PostgreSQL 服务名与 `DATABASE_URL` 一致。
- 确认初始化脚本包含 `CREATE EXTENSION vector`。
- embedding 维度错误时检查 `VECTOR_DIMENSION` 与 embedding 模型配置。

### Redis 故障

**现象**: Graph 临时状态、缓存或队列相关操作失败。

**排查步骤**:
```bash
docker compose logs redis
docker compose ps redis
```

**恢复建议**:
- 确认 `REDIS_URL=redis://redis:6379/0` 或等价 compose 服务名。
- 对可重建缓存允许清空；对运行态数据必须先确认是否会影响正在运行的 graph_run。

### 模型网关故障

**现象**: 任务进入 failed，错误码指向 `MODEL_GATEWAY_FAILED` 或模型网关调用异常。

**排查步骤**:
- 检查 `MODEL_GATEWAY_BASE_URL`、`MODEL_GATEWAY_API_KEY`、默认 chat/embedding model。
- 查看 model_gateway 日志字段：provider、model、purpose、latency_ms、status、error。
- 确认错误不是由结构化 JSON 校验失败引起。

**恢复建议**:
- 修正配置后对失败任务执行 retry。
- 不在日志中输出完整 API Key、prompt 或模型输出。

### LangGraph 任务卡住

**现象**: AI 任务长时间停留在 `running`、`waiting_more_info` 或 `waiting_review`。

**排查步骤**:
- 查询任务详情和当前 stage。
- 查询 graph_run checkpoint 和最近节点日志。
- 查询 human_reviews 是否存在 pending 记录。

**恢复建议**:
- `waiting_more_info` 需要提交补充信息；提交后任务回到 `draft`，需要再次调用 `/api/ai-tasks/{id}/start` 才会继续运行。
- `waiting_review` 需要负责人确认。
- 节点失败后按任务 retry 机制恢复，不直接改状态字段。

### 知识检索异常

**现象**: 检索无结果、返回无引用内容或权限过滤异常。

**排查步骤**:
- 检查知识文档索引状态。
- 检查 chunk 是否存在 embedding。
- 检查用户角色和文档权限。
- 检查 query_hash、top_k、result_count、latency_ms 日志。

**恢复建议**:
- 重新索引失败文档。
- 修复权限规则后重跑检索。
- 禁止前端隐藏无权限内容来替代后端权限过滤。

### 数据库迁移事故

**现象**: 发布后 API 500、字段缺失、迁移卡住或数据不一致。

**处理**:
1. 立即停止继续发布。
2. 确认最近迁移版本、执行日志和失败语句。
3. 若应用可回滚且数据兼容，先回滚应用版本。
4. 若需要恢复数据，使用已验证备份恢复到隔离环境，确认影响范围后再执行正式恢复。
5. 恢复后验证 `/health`、核心 API、审计查询和 P0 测试。

### 密钥或凭据泄漏

**现象**: API Key、Bearer Token、GitLab token 或 APP_SECRET_KEY 出现在日志、API 响应、报告或仓库中。

**处理**:
1. 立即撤销或轮换泄漏凭据。
2. 暂停依赖该凭据的模型网关或 GitLab 集成。
3. 清理日志展示面和报告归档中的敏感内容。
4. 检查访问日志和审计事件，确认是否存在未授权访问。
5. 复盘并补充脱敏、掩码和 secret scanning 规则。

### GitLab 回写边界违反

**现象**: AI Brain 对 GitLab MR 写入评论、审批状态、request changes、合并状态或分支变更。

**处理**:
1. 立即停用 code_review 执行器和相关 GitLab 凭据。
2. 保存 MR、task_id、snapshot_id、trace_id 和执行器日志。
3. 通知受影响项目负责人，人工确认是否需要撤销外部变更。
4. 修复执行器权限和 API 调用边界，只保留只读凭据。
5. 重新执行 no-writeback 验证后才能恢复 code_review 能力。

## 故障报告模板

```markdown
# 故障报告

## 基本信息
- 故障时间:
- 故障等级:
- 影响范围:
- trace_id / ai_task_id:
- 处理人员:

## 时间线
- HH:mm 发现问题
- HH:mm 定位到模块
- HH:mm 执行恢复动作
- HH:mm 验证恢复

## 根因分析
- 直接原因:
- 深层原因:

## 恢复动作
- 已执行:
- 未执行及原因:

## 改进措施
| 措施 | 负责人 | 截止日期 |
|------|--------|----------|
|  |  |  |
```

---
最后更新: 2026-05-27
