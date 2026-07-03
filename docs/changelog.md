# 变更日志

所有重要的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 文档集按业务域和 API 分册拆分：`api.md` 收敛为 API 入口索引，接口细节迁入 `docs/02-specs/enterprise-ai-brain/api/`；`spec.md` 与 `test-case.md` 的长版本历史迁入 `history/`；拆分前完整 changelog 归档到 [releases/changelog-2026-07-03-pre-split.md](releases/changelog-2026-07-03-pre-split.md)。
- 系统管理“系统设置”页面扩展系统级邮件发送配置：支持维护系统管理员邮箱、发件邮箱、默认发件人、Reply-To、SMTP Host/端口/TLS/用户名、密码或密钥引用，并提供 `POST /api/system/settings/email/test` 测试发送；响应和审计仅记录配置状态，不回显 SMTP 密码。

### Fixed
- 产品配置 Git 资源编辑时，手工修改 Project Path 现在会持久化并回显；只修改 Remote URL 且未手工覆盖 Project Path 时，后端会重新推导仓库路径。
- 定时作业手动触发返回 `queued/running` 运行记录后，前端会立即切到“运行记录”并置顶展示新 run，不再等待全量列表刷新完成。
- 代码巡检报告列表现在由后端标记是否可进入需求全链路；未关联需求上下文的独立巡检报告会禁用“全链路”入口，不再跳转后出现 `NO_REQUIREMENT_CONTEXT` 接口异常。
- 代码巡检页新增产品范围选择和产品列，列表与治理概览会按 `product_id` 联动刷新，并收敛工具栏/表格排版，避免全局视图下页面挤压错位。
- 代码巡检治理概览的分支/提交人待办表格改为固定布局和聚合指标列，长报告摘要在表格内省略和横向滚动，避免表头竖排和内容撑宽。
- 代码巡检治理概览重排为治理结论、核心 KPI 与“治理待办 / 风险分布 / 趋势与规则”分组页签，减少默认视图信息堆叠并改善移动端阅读密度。
- 代码巡检治理概览 review 后进一步压缩移动端 KPI 为双列，并移除页签外层卡片化容器，降低嵌套感和纵向堆叠。

## 历史归档

- [拆分前完整 changelog（截至 2026-07-03）](releases/changelog-2026-07-03-pre-split.md)
- API 文档版本历史：[02-specs/enterprise-ai-brain/api/version-history.md](02-specs/enterprise-ai-brain/api/version-history.md)
- 技术规格版本历史：[02-specs/enterprise-ai-brain/history/spec-version-history.md](02-specs/enterprise-ai-brain/history/spec-version-history.md)
- 测试用例版本历史：[02-specs/enterprise-ai-brain/history/test-case-version-history.md](02-specs/enterprise-ai-brain/history/test-case-version-history.md)
