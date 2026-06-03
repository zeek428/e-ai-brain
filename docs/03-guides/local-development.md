# 本地开发环境搭建

## 适用人群

需要在本地开发、调试或验证 AI Brain 的开发者、测试人员和 AI 编码助手。

## 前置条件

- 已完成 [快速入门](getting-started.md)。
- 已阅读 [项目级 PRD](../01-prd/enterprise-ai-brain/prd.md) 和 [项目级技术规格](../02-specs/enterprise-ai-brain/spec.md)。
- 已理解 v1 技术路线：React + FastAPI + LangGraph + PostgreSQL + pgvector + Redis。

## 开发环境配置

### 推荐工具

| 工具 | 用途 |
|------|------|
| Docker Compose | 启动 web、api、postgres、redis。 |
| uv | 后端 Python 依赖和测试。 |
| Node.js | 前端本地开发。 |
| VS Code | 代码编辑和调试。 |

### 环境变量

本地开发从 `.env.example` 复制：

```bash
cp .env.example .env
```

项目默认使用官方镜像和官方软件源；网络受限时只修改本地 `.env`，不要把私有或临时镜像源写进 `.env.example`。

默认依赖来源：

```text
pgvector/pgvector:pg16
python:3.11-slim
node:22-alpine
https://pypi.org/simple
https://registry.npmjs.org
```

关键变量：

```bash
APP_ENV=local
APP_SECRET_KEY=<local-secret>
ALLOW_SEEDED_USERS=
ACCESS_TOKEN_EXPIRE_SECONDS=28800

DATABASE_URL=postgresql://ai_brain:<password>@postgres:5432/ai_brain
REDIS_URL=redis://redis:6379/0

MODEL_GATEWAY_BASE_URL=<openai-compatible-base-url>
MODEL_GATEWAY_API_KEY=<redacted>
MODEL_GATEWAY_DEFAULT_CHAT_MODEL=<chat-model>
MODEL_GATEWAY_DEFAULT_EMBEDDING_MODEL=<embedding-model>
MODEL_GATEWAY_TIMEOUT_SECONDS=60
MODEL_GATEWAY_MAX_RETRIES=1
VECTOR_DIMENSION=1536
LOG_LEVEL=INFO
```

默认配置不访问外部模型时，`/health` 返回 `model_gateway=not_configured`，AI 任务启动会返回明确错误，不生成本地兜底输出。配置 `MODEL_GATEWAY_BASE_URL` 和 `MODEL_GATEWAY_API_KEY` 后，`/health` 返回 `model_gateway=configured`，任务启动才会进入真实 OpenAI-compatible 网关路径。

真实 `.env` 不提交到仓库。

本地内置种子账号仅在 `APP_ENV=local|test|development` 时启用；非本地环境默认拒绝这些账号登录。前端不会自动使用种子账号登录，若要在本地直接调用管理列表 API，可通过登录接口获取 token 后写入浏览器 `localStorage.ai_brain_access_token`。

### 网络受限环境

如果当前网络无法访问 Docker Hub、PyPI 或 npm registry，可以只在本地 `.env` 中覆盖镜像和软件源。

示例：

```text
PGVECTOR_IMAGE=<mirror>/pgvector/pgvector:pg16
API_BASE_IMAGE=<mirror>/python:3.11-slim
WEB_BASE_IMAGE=<mirror>/node:22-alpine
PIP_INDEX_URL=https://pypi.example.com/simple
NPM_CONFIG_REGISTRY=https://registry.example.com
```

镜像源必须等价于默认镜像，尤其是 PostgreSQL 镜像必须包含 `pgvector` 扩展。PostgreSQL 数据卷路径应以实际镜像约定为准，避免在不同主版本之间复用不兼容数据目录。

### 本地服务

```bash
# 校验 compose 配置
docker compose config

# 启动完整开发栈
docker compose up -d --build

# 查看服务状态
docker compose ps
```

服务职责：

| 服务 | 职责 |
|------|------|
| web | React 工作台。 |
| api | FastAPI 接口、LangGraph、模型网关、知识检索和审计。 |
| postgres | 业务数据、知识文档、pgvector 向量。 |
| redis | 队列、临时状态、限流和短期缓存。 |

当前 API 运行时仍以进程内 `MemoryStore` 承载本地测试和演示数据；PostgreSQL 初始化脚本已经定义目标持久化表结构，用于后续数据库仓储接入和 Compose 依赖验证。不要把当前内存存储误判为生产持久化能力。

## 开发工作流

### 启动开发服务

优先使用 Docker Compose 启动全栈：

```bash
docker compose up -d --build
```

如需单独调试后端：

```bash
cd apps/api
uv run pytest
```

### 验证健康状态

```bash
curl http://localhost:8000/health
```

推荐健康响应包含：

```json
{
  "status": "ok",
  "postgres": "ok",
  "redis": "ok",
  "model_gateway": "not_configured"
}
```

`model_gateway` 当前取值为 `configured` 或 `not_configured`。默认 `.env.example` 未配置真实模型 API Key 时会返回 `not_configured`。

可选基础设施验证：

```bash
docker compose config --quiet
docker compose ps
docker compose exec redis redis-cli ping
curl http://localhost:8000/health
```

当 PostgreSQL 可用后，还需要验证扩展：

```bash
docker compose exec postgres psql -U ai_brain -d ai_brain -c "select extname from pg_extension where extname in ('vector', 'pgcrypto');"
```

### 运行测试

```bash
cd apps/api
uv run pytest

cd ../web
npm test
npm run typecheck
npm run lint
```

测试应覆盖 [项目级测试用例](../02-specs/enterprise-ai-brain/test-case.md) 中的 P0/P1 用例。

### 代码检查

根据具体子项目脚本执行。若脚本尚未建立，先以测试和 Docker Compose 健康检查作为最低验证。

## 调试

### API 调试

```bash
docker compose logs api
curl http://localhost:8000/health
```

关注字段：`trace_id`、`ai_task_id`、`module`、`event`、`latency_ms`、`status`。

### 数据库调试

```bash
docker compose logs postgres
```

重点确认：

- pgvector 扩展初始化成功。
- 数据库连接串使用 compose 服务名 `postgres`。
- embedding 维度与 `VECTOR_DIMENSION` 一致。

### Redis 调试

```bash
docker compose logs redis
```

重点确认：

- `REDIS_URL` 使用 compose 服务名 `redis`。
- Graph 临时状态、缓存或队列失败时先检查 Redis 连接。

### 模型网关调试

重点确认：

- `MODEL_GATEWAY_BASE_URL` 指向 OpenAI-compatible API。
- `MODEL_GATEWAY_API_KEY` 已配置且未写入日志。
- 结构化输出节点请求 JSON 并做 schema 校验。

## 模拟数据

v1 建议初始化：

- 默认管理员。
- 研发大脑配置 `rd_brain`。
- 示例业务大脑配置。
- 示例知识文档。
- 从 `.env` 读取默认模型配置。
- 模拟任务系统配置。

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| `/health` 失败 | 查看 `docker compose ps` 和 `docker compose logs api`。 |
| 数据库连接失败 | 检查 `DATABASE_URL`、postgres 服务名和容器状态。 |
| Redis 连接失败 | 检查 `REDIS_URL` 和 redis 容器状态。 |
| 模型调用失败 | 检查模型网关环境变量和供应商响应。 |
| 知识检索无结果 | 检查文档是否导入、是否已生成文本 chunk、权限过滤是否命中；Embedding 不可用时应进入 `text_indexed` 并通过关键词检索返回结果。 |

## 性能调优

- 常规 API 使用分页和索引。
- 知识检索限制 `top_k`，避免无界向量或关键词查询。
- Graph 长任务异步执行，前端通过任务详情查询状态。
- 审计查询按 `ai_task_id`、`event_type`、`created_at` 建索引；`trace_id` 用于 API 请求日志定位。

---
最后更新: 2026-05-27
