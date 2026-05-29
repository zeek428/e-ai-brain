# 术语表

## A

### ADR
Architecture Decision Record，架构决策记录。用于记录项目中重要的架构决策及其背景、理由和后果。

### API
Application Programming Interface，应用程序编程接口。定义了软件组件之间交互的方式。

### AI Task
AI 任务。AI Brain 中承载产品详细设计、技术方案、代码 Review、自动化测试、发布评估或上线后分析的可执行任务实体，使用统一状态机、人工确认和审计。

### Ant Design Pro
React 后台工作台模板。AI Brain v1 前端工程以其布局、菜单、权限和页面脚手架为起点，但运行时必须保持本仓库独立安装、构建和部署。

## B

### Bearer Token
一种身份验证令牌，持有者可以使用该令牌访问受保护的资源。

## C

### CI/CD
Continuous Integration / Continuous Deployment，持续集成/持续部署。自动化代码集成、测试和部署的实践。

### Code Review Executor
代码 Review 执行器。AI Brain 中用于把内部 GitLab MR diff、需求摘要、技术方案和项目规范转成结构化 Review 报告的可插拔边界，一期默认适配 Claude Code `code-review` skill。

## D

### DDD
Domain-Driven Design，领域驱动设计。一种软件开发方法，强调业务领域建模。

## E

### E2E
End-to-End，端到端测试。验证完整系统流程的测试类型。

## G

### GBrain
长期记忆和公司大脑层。AI Brain 使用 GBrain 作为补充检索、答案合成和知识图谱能力，不替代 PostgreSQL 中的产品、需求、任务、审计和权限数据。

## J

### JWT
JSON Web Token，一种用于身份验证的令牌标准。

## L

### LangGraph
用于 AI 工作流编排的状态图框架。AI Brain 用它管理长任务、检查点、人机中断和恢复。

### Lifecycle Context
研发上下文图谱。用于串联需求、设计、方案、代码、Review、测试、Bug、发布、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件。

## M

### Microservices
微服务。一种架构风格，将应用拆分为小型、独立的服务。

### Model Gateway
模型网关。AI Brain 中统一承载 chat 和 embedding 模型调用的边界，业务模块不得直接依赖供应商 SDK。

## P

### PR
Pull Request，拉取请求。代码合并请求，用于代码审查和讨论。

### PRD
Product Requirements Document，产品需求文档。描述产品功能需求的文档。

### pgvector
PostgreSQL 向量扩展。AI Brain v1 用它在 PostgreSQL 中存储 embedding 并执行向量检索。

## Q

### QPS
Queries Per Second，每秒查询数。衡量系统处理能力的指标。

## R

### rd_brain
研发大脑。AI Brain v1 默认业务大脑，用于把研发需求转化为可确认、可回写、可沉淀的研发任务闭环。

## S

### SLO
Service Level Objective，服务等级目标。定义服务性能目标的指标。

### SLA
Service Level Agreement，服务等级协议。服务提供者与用户之间的正式协议。

## T

### TDD
Test-Driven Development，测试驱动开发。先写测试再写实现的开发方式。

### Test Case
测试用例。描述测试输入、执行条件和预期结果的文档，用于验证软件功能是否符合需求。

### AC
Acceptance Criteria，验收标准。定义用户故事完成的条件，是测试用例设计的依据。

## U

### Unit Test
单元测试。对软件中最小可测试单元进行验证的测试类型。

---

## 缩写对照

| 缩写 | 全称 | 中文 |
|------|------|------|
| AC | Acceptance Criteria | 验收标准 |
| AI Task | AI Task | AI 任务 |
| API | Application Programming Interface | 应用程序编程接口 |
| ADR | Architecture Decision Record | 架构决策记录 |
| CI/CD | Continuous Integration/Deployment | 持续集成/部署 |
| E2E | End-to-End | 端到端 |
| JWT | JSON Web Token | JSON 网络令牌 |
| PR | Pull Request | 拉取请求 |
| PRD | Product Requirements Document | 产品需求文档 |
| QPS | Queries Per Second | 每秒查询数 |
| SLA | Service Level Agreement | 服务等级协议 |
| SLO | Service Level Objective | 服务等级目标 |
| TDD | Test-Driven Development | 测试驱动开发 |
| TC | Test Case | 测试用例 |

---
最后更新: 2026-05-29
