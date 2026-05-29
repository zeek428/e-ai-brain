# 变更日志

所有重要的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 新增 P0 字段级 schema、状态机动作矩阵和核心接口错误语义，降低实现阶段二次解释成本。
- 新增缺失的审计、部署、产品配置、模型网关配置和主体级审计详细测试用例。
- 扩展部署、监控和故障响应 runbook，补充 staging/production-readiness 门禁、SLO、RTO/RPO、备份恢复、密钥轮换和 GitLab 只读边界事故处理。
- 项目级 API 文档补充产品、版本、模块、Git 资源、相关系统和模型网关配置接口。
- 新增需求实体、需求审批状态流转和审批后生成 AI 任务接口。
- 补充 GitLab 代码质量、线上运行日志、Jenkins 发布、首页 IT 团队看板和 Bug 管理的 PRD、技术规格、API、测试用例和评审指南覆盖。
- 扩展 AI 任务为产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估和上线后分析七类研发全链路任务。
- PRD 增加 MVP 成功指标，覆盖需求到产品详细设计耗时、技术方案采纳率、Code Review 报告采纳率、高风险问题有效率、知识沉淀复用率和审计可追踪率。

### Changed
- 测试用例清单增加适用阶段口径，区分 MVP 必交、MVP 占位、v1.1、v1.2 和生产就绪验证。
- 文档入口增加实现者最短路径，明确 P0 表、API、页面、测试和 runbook 的推荐落地顺序。
- 前端提交需求入口调整为需求管理查询表格，新增需求和配置类表单统一使用弹窗。
- 文档维护源切换为项目级 PRD/spec/API/test-case，`docs/design/` 转为历史归档。
- API 和测试用例文档对齐当前实现，包括登录字段、任务输入字段、Markdown 导出和审计查询参数。
- 统一补充信息后的状态契约：`waiting_more_info` 提交补充后回到 `draft`，再次启动后继续运行。
- 统一审计事件字段、健康检查枚举和 AI Brain 业务域示例。
- PRD 增加产品配置和模型网关配置验收标准。
- PRD 和测试用例对齐 v1 系列分阶段交付边界，拆分 MVP、v1.1、v1.2 人工确认门禁验收。
- PRD 和测试用例补充实际业务系统用户使用数据、用户反馈收集和 AI 主动迭代规划建议能力。
- 技术规格同步用户洞察/迭代规划模块、数据表、接口清单、状态流转、数据流、安全和风险设计。
- API 文档补充用户使用指标、用户反馈、AI 迭代规划建议、规划确认和相关错误码。
- 测试用例补充 AI 迭代规划建议不得自动创建正式需求、变更路线图或调整排期的断言。
- PRD、技术规格、API、测试用例、架构摘要和技术栈同步将内部 GitLab MR 代码 Review 提前纳入 v1 MVP，补充 MR 预览、diff 快照、可插拔 code-review 执行器、人工确认、内部报告归档和不回写 GitLab 的阶段边界。
- MVP-A/B/C 阶段边界调整为 MVP-A 包含内部 GitLab 只读绑定、MR 预览和 diff 快照，MVP-B 专注 code_review 执行器、正式 Review 报告和内部归档，MVP-C 专注知识治理和模拟 Issue。
- 部署 runbook 补充模型网关、内部 GitLab MR 预览、diff 快照和 code-review 执行器的 MVP 验证步骤。

### Deprecated
- `docs/design/` 不再作为后续版本迭代的维护目录。

### Removed
- 移除已合并到规范化本地开发指南的 `docs/development/local-environment.md`。

### Fixed
- 修复 PRD 和技术规格中指向不存在业务流程 HTML 的相对链接。
- 修复 PRD、技术规格、架构摘要、技术栈、测试用例和 CLAUDE 指令中业务入口数量、用户洞察/迭代规划模块、看板指标、Requirement 状态枚举、已删除 docs/design 引用和无效文档链接的不一致。
- 修复 AC10 用户洞察/迭代规划入口遗漏、Bug 管理阶段验收边界、需求到 AI 任务一对多关系和首页看板依赖项不一致。
- 修复测试用例中 v1 MVP 占位入口与 v1.1/v1.2 完整闭环能力混用的问题。
- 修复跨阶段 P0/P1 口径混用问题，测试用例改为“适用阶段 + 阶段内优先级”，避免 v1.2 用例阻塞 MVP 发布。
- 修复 API 角色表出现 MVP 未实现 `member`/`tester` 写权限的问题，统一到 MVP 六类系统角色并标注 v1.1/v1.2 扩展。
- 修复 `/health` trace_id 约定、Requirement `task_created` 多任务语义、审计主体字段必填口径和 GBrain MVP 可选边界不一致。
- 补齐技术规格中 `gitlab_mr_snapshots` 表、MR 快照幂等索引、code-review 执行器超时、schema 校验和审计约束。
- 修复 README 对 v1 MVP 范围描述偏旧、测试规范工具链过泛和部署 runbook 验证项不足的问题。
- 合并单独维护的本地环境说明到规范化本地开发指南。

### Security
- 补充内部 GitLab MR 快照、code-review 执行器、用户反馈/使用数据采集失败和不可归属数据的审计要求。
- 明确 MR diff、用户反馈和使用数据进入模型前必须脱敏、限长，且 GitLab token 不得传给 code-review 执行器。

---

## [1.0.0] - 2026-05-27

### Added
- 初始版本发布
- 核心功能实现

### Changed
-

### Fixed
-

---

## [0.1.0] - 2026-05-27

### Added
- 项目初始化

---

[Unreleased]: https://github.com/zeek428/e-ai-brain/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/zeek428/e-ai-brain/releases/tag/v1.0.0
[0.1.0]: https://github.com/zeek428/e-ai-brain/releases/tag/v0.1.0
