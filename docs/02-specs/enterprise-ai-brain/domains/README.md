# Enterprise AI Brain 业务域规格索引

> 来源：../spec.md。该目录按业务域承接技术规格导航和后续细节拆分，主 `spec.md` 继续保留跨域架构、数据模型、状态机、安全和测试门禁。

## 拆分原则

- 主规格保留跨域事实源：架构图、模块边界、DB-first 原则、状态机、缓存策略、安全策略和提交前真实页面验证门禁。
- 业务域文档承接高频迭代内容：页面职责、关键 API、核心表、权限边界、已落地组件和后续演进项。
- API 契约仍以 [../api.md](../api.md) 为准；测试验收仍以 [../test-case.md](../test-case.md) 和 [../test-cases/](../test-cases/) 为准。
- 当域文档与主规格不一致时，先更新主规格中的跨域原则，再同步域文档和 changelog。

## 业务域

| 业务域 | 文档 | 覆盖范围 |
|------|------|----------|
| 需求交付与研发任务 | [delivery-and-tasks.md](delivery-and-tasks.md) | 产品、迭代版本、需求、研发任务、Review、需求全链路、版本状态同步 |
| AI 助手与草案工作台 | [assistant-workbench.md](assistant-workbench.md) | 聊天、用户级历史、引用候选、草案生成/确认/取消、草案任务台、效果指标 |
| 插件、定时作业与执行器 | [plugins-jobs-and-runners.md](plugins-jobs-and-runners.md) | 插件、连接、动作、定时作业、作业运行、Runner、研发执行器策略 |
| 质量、运营与洞察 | [quality-operations-and-insights.md](quality-operations-and-insights.md) | 执行诊断、代码巡检、Bug、用户洞察、生命周期上下文、团队看板 |
| 系统治理、RBAC 与平台配置 | [governance-rbac-and-platform.md](governance-rbac-and-platform.md) | 用户、角色、菜单、权限矩阵、模型网关、知识、审计、DB-first 迁移约束 |

## 后续维护

新增或重构业务模块时，优先在对应域文档补齐“当前落地”和“验收映射”；只有涉及跨域原则、表结构主索引、状态机或安全边界时才扩写主 `spec.md`。
