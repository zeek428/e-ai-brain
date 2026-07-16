# 企业 AI 大脑平台 API 文档

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v2.0.0 |
| 适用系统版本 | ≥ v1.0.0 |
| 文档状态 | Approved |

## 文档定位

本文是 API 契约入口和分册索引。公共约定、接口清单、领域接口细节、错误语义和版本历史已按业务域拆入 [api/](api/) 目录；维护接口时应更新对应分册，并在必要时同步本文索引。

## API 分册

| 分册 | 覆盖范围 |
|------|----------|
| [api/common-and-auth.md](api/common-and-auth.md) | 概述、认证、响应 envelope、错误响应、分页、角色要求和基础接口 |
| [api/catalog.md](api/catalog.md) | 全量接口清单 |
| [api/system-governance-and-platform.md](api/system-governance-and-platform.md) | 系统治理、产品配置、平台配置和 AI 助手分册组索引 |
| [api/system-rbac-and-settings.md](api/system-rbac-and-settings.md) | 系统设置、用户、角色、菜单、权限矩阵、业务大脑 |
| [api/product-config.md](api/product-config.md) | 产品、迭代版本、模块、Git 仓库、相关系统归属、版本分支、版本驾驶舱 |
| [api/platform-settings-and-model-gateway.md](api/platform-settings-and-model-gateway.md) | 相关系统、模型网关配置、连接测试、模型调用日志 |
| [api/assistant-workbench.md](api/assistant-workbench.md) | AI 助手聊天、引用候选、动作草案、草案模板、助手效果指标、会话历史 |
| [api/delivery-and-tasks.md](api/delivery-and-tasks.md) | 正式需求评估、版本归组、统一研发执行策略、AI/真人协作、工作项、AI 任务、人工确认、回写与导出 |
| [api/review-and-knowledge.md](api/review-and-knowledge.md) | GitLab/GitHub 代码 Review、知识中心 |
| [api/quality-operations-and-insights.md](api/quality-operations-and-insights.md) | 质量、运营、洞察和诊断分册组索引 |
| [api/devops-quality-and-code-inspection.md](api/devops-quality-and-code-inspection.md) | 研发运营数据、运维部署、定时作业、GitLab/Jenkins/线上日志指标、代码巡检、质量治理 |
| [api/user-insights-and-bugs.md](api/user-insights-and-bugs.md) | 用户洞察、用户反馈、用户使用指标、迭代规划建议、Bug 管理 |
| [api/lifecycle-dashboard-and-diagnostics.md](api/lifecycle-dashboard-and-diagnostics.md) | 生命周期上下文、首页 IT 团队看板、执行诊断 |
| [api/audit-and-errors.md](api/audit-and-errors.md) | 审计事件、核心接口错误语义、错误码 |
| [api/version-history.md](api/version-history.md) | API 文档版本历史和旧版变更记录 |

## 维护规则

- 新增或修改接口时，先定位业务域分册；跨域约定才更新 `common-and-auth.md`。
- 接口路径、请求/响应字段、权限、错误码和审计语义必须在同一分册内闭环说明。
- 只影响接口清单的新增路由，同步更新 [api/catalog.md](api/catalog.md)。
- 错误语义或错误码变化，同步更新 [api/audit-and-errors.md](api/audit-and-errors.md)。
- 可交付变更继续记录到 [../../changelog.md](../../changelog.md)。
