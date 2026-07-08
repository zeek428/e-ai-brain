# AI Brain 文档中心

AI Brain 是企业 AI 大脑平台项目。v1 以“研发大脑”为样板，MVP 跑通从研发需求审批、产品详细设计、技术方案、内部 GitLab MR 预览和 diff 快照、内部 GitLab MR Code Review、人工确认、内部报告归档到知识沉淀和审计追踪的最小闭环；v1.1 已开始补齐 Bug 管理基础登记、筛选、状态流转和重复归并能力；自动化测试深度联动、发布上线评估、上线后分析、完整研发运营看板和用户洞察按后续阶段扩展。

项目仓库: [zeek428/e-ai-brain](https://github.com/zeek428/e-ai-brain)

## 当前文档入口

| 文档 | 用途 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | 面向 AI 编码助手的文档阅读入口。 |
| [01-prd/enterprise-ai-brain/prd.md](01-prd/enterprise-ai-brain/prd.md) | 项目级 PRD，描述产品目标、范围、用户故事和验收标准。 |
| [01-prd/enterprise-ai-brain/solution-overview.html](01-prd/enterprise-ai-brain/solution-overview.html) | 面向管理层和非技术人员的 HTML 方案说明，包含业务价值、AI 赋能机制、核心闭环、总体架构图、企业级扩展架构、组件可更替性、项目风险、实施路线、阶段边界和治理要点。 |
| [02-specs/enterprise-ai-brain/spec.md](02-specs/enterprise-ai-brain/spec.md) | 项目级技术规格入口，保留跨域架构、数据、状态、风险和测试策略，业务域细节见 `domains/`。 |
| [02-specs/enterprise-ai-brain/api.md](02-specs/enterprise-ai-brain/api.md) | 项目级 API 文档入口，接口细节按业务域拆入 `api/` 分册。 |
| [02-specs/enterprise-ai-brain/test-case.md](02-specs/enterprise-ai-brain/test-case.md) | 项目级测试用例入口，详细用例按业务域拆入 `test-cases/`。 |
| [08-help/README.md](08-help/README.md) | 面向最终用户的帮助中心和业务模块操作手册维护入口，包含截图规范和迭代同步检查清单。 |

## 推荐阅读顺序

1. [01-prd/enterprise-ai-brain/prd.md](01-prd/enterprise-ai-brain/prd.md) — 理解产品范围和验收标准。
2. [02-specs/enterprise-ai-brain/spec.md](02-specs/enterprise-ai-brain/spec.md) — 理解技术实现边界。
3. [02-specs/enterprise-ai-brain/api.md](02-specs/enterprise-ai-brain/api.md) — 进入 API 分册索引，再按业务域阅读接口契约。
4. [02-specs/enterprise-ai-brain/test-case.md](02-specs/enterprise-ai-brain/test-case.md) — 进入测试用例索引，再按业务域阅读验收要求。
5. [02-specs/architecture/system-overview.md](02-specs/architecture/system-overview.md) 和 [02-specs/architecture/tech-stack.md](02-specs/architecture/tech-stack.md) — 快速查看架构和技术栈摘要。

## 实现者最短路径

当前源码已包含 FastAPI + Ant Design Pro 的 MVP 真实系统骨架。Docker 本地栈默认以 `PERSISTENCE_MODE=postgres` 启动，登录账号来自 PostgreSQL `users` 表，产品、版本、模块、Git 资源、相关系统、需求、AI 任务、人工确认、Graph 运行态、GitLab MR / GitHub PR 兼容快照、Code Review 报告、知识文档、知识 chunk、知识沉淀候选、审计事件、Bug 记录、采集运行、待归属队列、GitLab 每日代码指标、Jenkins 发布记录、线上日志指标、用户使用指标、用户反馈、迭代规划建议/确认、生命周期上下文边、生命周期风险信号、首页看板快照、模拟 Issue 回写、模型网关配置/调用元数据和 AI 助手会话/消息已写入 PostgreSQL 结构表。当前仍处于 DB-first 迁移期：`/health` 返回 `data_access_mode=db_first_migration`，PostgreSQL 启动使用轻量 `PostgresRuntimeStore` repository 容器而不是 `PersistentMemoryStore.from_repository(...)` 恢复业务集合，请求结束全局 `persist()` 已从 API middleware 移除，`app_state_snapshots` 仅作为历史迁移表保留，不再作为生产业务状态恢复源或写入目标；进程内 `MemoryStore` 仅作为自动化测试 helper，不作为 FastAPI 本地开发持久化模式，PostgreSQL 请求上下文使用非 `MemoryStore` 的 repository source rows/read model 投影。只读缓存可为性能保留，但必须从 PostgreSQL 派生、可重建，且不得作为写接口事实源。数据库升级通过 `apps/api/app/db/migrations/*.sql` 可重复执行脚本完成，不需要也不应清空数据库卷。内部 GitLab / GitHub 预览和 diff 快照必须读取配置的只读 API 凭据；非 `code_review` AI 任务启动必须使用 active/default OpenAI-compatible 模型网关或环境模型网关，`code_review` 任务必须通过可插拔 `code_review_executor` 边界生成报告；默认外部执行器命令为空但模型网关可用时，会在该边界内使用 `model_gateway` 适配器。缺少可用配置时任务明确失败，不生成本地输出、示例数据或前端兜底行。

PostgreSQL 服务默认使用本地项目镜像别名 `e-ai-brain-postgres-pgvector:0.8.2-pg18-trixie`，它对应官方 `pgvector/pgvector:0.8.2-pg18-trixie`，方便 Docker Desktop 中和 `e-ai-brain` 容器组一起管理，并避免已有 PG18 数据卷被错误挂载到 PG16 镜像。网络受限无法拉取官方镜像时，可用 `infra/docker/postgres-pgvector.Dockerfile` 基于本机已有 `postgres:18-alpine` 构建同主版本 fallback 镜像，并通过 `PGVECTOR_IMAGE` 指向它。

```bash
docker build -f infra/docker/postgres-pgvector.Dockerfile \
  --build-arg POSTGRES_BASE_IMAGE=postgres:18-alpine \
  --build-arg PGVECTOR_REF=v0.8.2 \
  -t e-ai-brain-postgres-pgvector .

PGVECTOR_IMAGE=e-ai-brain-postgres-pgvector docker compose up -d --no-deps postgres
```

1. 先阅读 PRD 的 v1 交付边界、MVP-A/B/C 实施切片、MVP 成功指标、演示验收路径和阶段计划，明确 MVP、v1.1、v1.2 与生产就绪门禁的差异。
2. 再阅读技术规格中的实施切片、P0 数据表字段、状态机动作矩阵和模块边界，先按 MVP-A 落地需求审批、产品详细设计、技术方案、内部 GitLab 只读绑定、MR 预览、MR diff 快照、人工确认、导出和基础审计。
3. 然后按 MVP-B 实现 `code_review` 任务、可插拔 code-review 执行器、Review 报告人工确认、内部归档和不回写 GitLab 的只读边界。
4. 再按 MVP-C 实现知识中心导入、权限过滤检索、知识沉淀审核、模拟 Issue 幂等生成、主体级审计和后续阶段入口空状态。
5. 前端页面优先实现产品配置、需求管理、任务中心待确认弹窗、知识中心、Bug 管理、审计与运行入口；研发运营、用户洞察、迭代规划和首页 IT 团队看板必须读取真实 API 与真实结构表，未接入外部自动采集器时展示真实空状态，不返回示例数据、占位统计或伪造结果。
6. 测试按 `test-case.md` 的 MVP-A/B/C 切片和 P0 用例先跑通，再补 v1.1、v1.2 和生产就绪用例。
7. 任何影响前端、页面可见文案、路由、交互、服务映射或页面展示的后端改动，提交前必须打开真实 Web 页面完成界面验证；记录 URL、角色、目标页面、关键交互、自动化命令和验证结果，网页验证未通过不得提交。
8. 发布前执行部署、监控和故障响应 runbook 中的生产就绪门禁脚本 `scripts/production_readiness_check.py`，尤其是密钥掩码、GitLab 只读边界、数据库迁移、pgvector/pgcrypto、备份恢复和审计可追踪；脚本在目标环境通过前不得宣称可发布。

## 文档结构

```text
docs/
├── 01-prd/
│   ├── _template/
│   └── enterprise-ai-brain/
│       └── prd.md
├── 02-specs/
│   ├── _template/
│   ├── architecture/
│   └── enterprise-ai-brain/
│       ├── spec.md
│       ├── api.md
│       ├── test-case.md
│       ├── api/
│       │   ├── README.md
│       │   ├── common-and-auth.md
│       │   ├── catalog.md
│       │   ├── system-governance-and-platform.md
│       │   ├── system-rbac-and-settings.md
│       │   ├── product-config.md
│       │   ├── platform-settings-and-model-gateway.md
│       │   ├── assistant-workbench.md
│       │   ├── delivery-and-tasks.md
│       │   ├── review-and-knowledge.md
│       │   ├── quality-operations-and-insights.md
│       │   ├── devops-quality-and-code-inspection.md
│       │   ├── user-insights-and-bugs.md
│       │   ├── lifecycle-dashboard-and-diagnostics.md
│       │   └── audit-and-errors.md
│       ├── domains/
│       ├── history/
│       └── test-cases/
├── 03-guides/
├── 04-decisions/
├── 05-runbooks/
├── 06-standards/
├── 07-deprecated/
└── 08-help/
    ├── README.md
    └── assets/
        └── screenshots/
```

## 文档维护规则

- 项目级入口文档仍是维护源：PRD 保持单文件，spec/API/test-case 通过入口文件索引到业务域分册和历史归档。
- 每个 PRD 验收标准必须映射到至少一个测试用例。
- 每个新增模块必须同步补充对应业务域规格、API 分册、数据模型、权限、审计说明和测试用例。
- 每个影响用户操作的页面或流程变更必须检查 `08-help/`，同步更新操作手册、截图或 FAQ；确认无需更新时，在交付说明中写明原因。
- 所有高影响 AI 动作必须保留明确人工确认点。
- 当实现与文档不一致时，先更新项目级入口和对应分册，再更新代码；完成后同步 changelog。
- 部署、监控和故障响应 runbook 同时记录 local、staging 和 production-readiness 门禁；当前实现状态必须以代码、`scripts/production_readiness_check.py` 和目标环境验证结果为准。

## 本地开发

```bash
# 校验 Docker Compose 配置
docker compose config

# 启动本地开发栈
docker compose up -d --build

# 已有数据库卷升级时，API 启动入口会按顺序执行迁移 SQL
# 不要通过删除 postgres_data 卷来规避迁移问题

# 后端测试
cd apps/api
uv run pytest
```

---
最后更新: 2026-07-03
