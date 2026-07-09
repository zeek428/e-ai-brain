# Enterprise AI Brain

Enterprise AI Brain 是面向企业研发与 IT 治理场景的 AI 大脑平台。当前样板业务脑为“研发大脑”，目标是把需求、设计、研发任务、代码巡检、Bug、知识沉淀、审计与运营指标串成可追踪、可确认、可治理的闭环。

平台强调 Agent 自治循环能力：围绕给定需求或 Bug，由定时作业或业务事件触发，Agent 可在受控边界内自主理解目标、拆解计划、执行任务、检查结果、沉淀记忆并再次规划下一轮动作，持续推进开发、测试、部署准备和结果验证，直到达到可验证目标，或触发权限、高风险操作、失败重试上限等安全边界并转入人工确认。

项目当前包含：

- FastAPI 后端服务，采用模块化单体架构。
- React + TypeScript + Ant Design Pro 前端工作台。
- PostgreSQL + pgvector 作为主要业务数据和知识检索存储。
- Redis 作为缓存、队列和短期运行支撑。
- MinIO/S3 兼容对象存储，用于知识文档上传资产。
- LangGraph 作为 AI 任务工作流编排层，支撑状态图、检查点、人机中断和恢复。
- 兼容通用 Chat/Embedding API 的模型网关，用于 AI 助手、任务执行和知识问答。
- 本地 AI 工具执行器调用能力，可集成本机 Codex、Claude Code、Hermes、OpenClaw 等研发执行工具。

## 核心能力

### 团队看板

面向管理视角展示交付负载、风险压力、工程活跃、用户声音和趋势数据，帮助快速判断当前团队治理重点。

### AI 助手

支持围绕 AI Brain 内部业务数据进行问答，可通过 `@` 引用产品、需求、任务、Bug、知识、插件、定时作业等上下文，并生成可审查的业务草案。

### 草案任务台

集中管理 AI 助手生成的操作草案，包括校验、重试、取消和进入对应业务流程。

### 任务中心

管理定时作业、AI 能力配置和插件能力。定时作业可以编排采集、巡检、通知、写入报告等动作，并保留运行记录；本地 AI 工具执行器可通过受控命令、工作区隔离和运行审计，调用本机 Codex、Claude Code、Hermes、OpenClaw 等工具完成代码巡检、研发执行和结果回收。

### 需求交付

覆盖需求管理、研发任务、研发执行器策略、迭代版本、Bug 管理和全链路追踪。需求和 Bug 可推进为 AI Task，由 Agent 按策略形成自治循环，持续执行、检查、记忆和再规划；高影响 AI 动作需要人工确认后继续推进。

### 产品资产

维护产品、版本、模块、Git 仓库、相关系统和知识中心。知识中心支持文档上传、解析、分块、Hybrid Search、引用式知识问答和知识沉淀审核。

### 运营治理

包含日志监控、用户洞察、审计与运行、执行诊断和代码巡检，帮助定位系统运行、AI 执行和研发质量问题。

### 系统管理

包含用户、角色、菜单、系统设置、邮件发送配置、模型网关、本地 AI 工具执行器、AI 助手快捷任务和 `@` 能力管理。

## 技术架构

```text
React + TypeScript + Ant Design Pro
  -> FastAPI modular monolith
     -> LangGraph workflow runtime
     -> PostgreSQL + pgvector
     -> Redis
     -> MinIO / S3-compatible object storage
     -> provider-compatible model gateway
     -> local AI tool executors
```

关键原则：

- 业务数据以 PostgreSQL 为事实源。
- AI 任务工作流通过 LangGraph 保留运行节点、检查点和人工确认中断点。
- Agent 自治循环必须围绕可验证目标推进，每轮执行、检查、记忆和再规划都应可追踪；失败重试、高风险动作和权限边界需要被审计并可转入人工确认。
- 知识检索必须在数据库查询层执行权限过滤。
- 模型调用必须经过 `model_gateway`，业务模块不直接调用模型供应商 SDK，也不绑定具体模型供应商。
- 本地 AI 工具执行器必须经过平台配置、权限校验、工作区隔离和审计记录后调用，避免业务流程直接执行未治理的本机命令。
- AI 高影响动作必须保留人工确认点。
- 审计、错误响应和重要 API 返回应携带可追踪 `trace_id`。

## 目录结构

```text
.
├── apps/
│   ├── api/                 # FastAPI 后端
│   └── web/                 # React + TypeScript 前端
├── docs/                    # PRD、规格、API、测试、运维、帮助文档
│   ├── 01-prd/
│   ├── 02-specs/
│   ├── 03-guides/
│   ├── 05-runbooks/
│   ├── 06-standards/
│   └── 08-help/             # 用户帮助中心和操作手册
├── infra/                   # Docker 镜像和基础设施文件
├── scripts/                 # 巡检、回归、生产就绪等脚本
├── docker-compose.yml       # 本地完整开发栈
├── AGENTS.md                # AI 编码助手项目级工作约定
└── CLAUDE.md                # Claude/Codex 文档阅读入口
```

## 快速开始

### 1. 准备环境

建议准备：

- Docker Desktop 或兼容 Docker Compose 的容器环境。
- Python 3.11+。
- Node.js 22+。
- `uv`，用于后端依赖和测试。

复制环境变量模板：

```bash
cp .env.example .env
```

本地开发时请根据实际情况配置 `.env`。不要提交真实密钥、SMTP 密码、模型 API Key、Cookie、Token 或公网隧道域名。

### 2. 校验 Docker Compose

```bash
docker compose config
docker compose config --quiet
```

### 3. 启动完整本地栈

```bash
docker compose up -d --build
```

默认端口：

| 服务 | 地址 |
|------|------|
| Web 前端 | http://localhost:5173 |
| API 后端 | http://localhost:8000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| MinIO API | http://localhost:9000 |
| MinIO Console | http://localhost:9001 |

### 4. 健康检查

```bash
curl http://localhost:8000/health
docker compose ps
docker compose logs api
```

检查 PostgreSQL 扩展：

```bash
docker compose exec postgres psql -U ai_brain -d ai_brain \
  -c "select extname from pg_extension where extname in ('vector', 'pgcrypto');"
```

## 本地开发

### 后端

```bash
cd apps/api
uv run pytest
```

运行单个后端测试：

```bash
cd apps/api
uv run pytest tests/test_file.py::test_name
```

### 前端

```bash
cd apps/web
npm install
npm run dev
```

常用前端校验：

```bash
cd apps/web
npm test
npm run typecheck
npm run build
```

## 文档入口

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | 文档中心入口。 |
| [docs/01-prd/enterprise-ai-brain/prd.md](docs/01-prd/enterprise-ai-brain/prd.md) | 产品范围、用户故事、验收标准和阶段规划。 |
| [docs/02-specs/enterprise-ai-brain/spec.md](docs/02-specs/enterprise-ai-brain/spec.md) | 技术规格、模块边界、数据模型、状态机和安全策略。 |
| [docs/02-specs/enterprise-ai-brain/api.md](docs/02-specs/enterprise-ai-brain/api.md) | API 契约入口。 |
| [docs/02-specs/enterprise-ai-brain/test-case.md](docs/02-specs/enterprise-ai-brain/test-case.md) | 测试用例和验收映射入口。 |
| [docs/03-guides/local-development.md](docs/03-guides/local-development.md) | 本地开发指南。 |
| [docs/05-runbooks/deployment.md](docs/05-runbooks/deployment.md) | 部署 runbook。 |
| [docs/06-standards/security.md](docs/06-standards/security.md) | 安全规范。 |
| [docs/08-help/README.md](docs/08-help/README.md) | 用户帮助文档、操作手册和截图维护规范。 |
| [docs/changelog.md](docs/changelog.md) | 变更日志。 |

## 开发和提交要求

开发时请遵守：

- 先阅读 [AGENTS.md](AGENTS.md) 和相关业务文档。
- 不要回滚或覆盖他人未提交改动。
- 涉及前端页面、菜单、可见文案、流程或 API 展示行为时，必须完成真实页面验证。
- 涉及用户操作变化时，检查并同步 [docs/08-help](docs/08-help) 中的帮助文档和截图。
- 涉及权限、API、数据模型、审计或运维行为时，同步规格、API 文档、测试用例和 changelog。
- 不要提交真实密码、Token、API Key、Cookie、私有连接串或未脱敏截图。

## 常用排障

### 前端页面没有更新

可能是开发服务缓存或旧端口实例导致。建议：

```bash
lsof -nP -iTCP:5173 -sTCP:LISTEN
curl -I http://localhost:5173/
```

必要时重启前端开发服务。

### API 无法访问

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
curl http://localhost:8000/health
docker compose logs api
```

### 数据库迁移异常

不要通过删除 PostgreSQL 数据卷规避迁移问题。先检查迁移脚本和 API 启动日志：

```bash
docker compose logs postgres
docker compose logs api
```

### 登录或权限问题

优先确认：

- 当前环境是否为本地开发环境。
- `.env` 中登录、钉钉、种子账号和安全校验配置是否符合预期。
- 用户角色、菜单权限和产品数据范围是否已授权。
- 接口错误中的 `trace_id`，可用于审计与执行诊断。

## 当前状态说明

项目仍处于持续迭代阶段，功能、权限、页面和帮助文档会随业务推进更新。以代码、数据库迁移、`docs/` 下的项目级文档、真实运行环境验证结果为准。
