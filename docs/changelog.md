# 变更日志

所有重要的变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 文档集按业务域和 API 分册拆分：`api.md` 收敛为 API 入口索引，接口细节迁入 `docs/02-specs/enterprise-ai-brain/api/`；`spec.md` 与 `test-case.md` 的长版本历史迁入 `history/`；拆分前完整 changelog 归档到 [releases/changelog-2026-07-03-pre-split.md](releases/changelog-2026-07-03-pre-split.md)。
- 系统管理“系统设置”页面扩展系统级邮件发送配置：支持维护系统管理员邮箱、发件邮箱、默认发件人、Reply-To、SMTP Host/端口/TLS/用户名、密码或密钥引用，并提供 `POST /api/system/settings/email/test` 测试发送；响应和审计仅记录配置状态，不回显 SMTP 密码。

### Fixed
- 产品配置 Git 资源编辑时，手工修改 Project Path 现在会持久化并回显；只修改 Remote URL 且未手工覆盖 Project Path 时，后端会重新推导仓库路径。

## 历史归档

- [拆分前完整 changelog（截至 2026-07-03）](releases/changelog-2026-07-03-pre-split.md)
- API 文档版本历史：[02-specs/enterprise-ai-brain/api/version-history.md](02-specs/enterprise-ai-brain/api/version-history.md)
- 技术规格版本历史：[02-specs/enterprise-ai-brain/history/spec-version-history.md](02-specs/enterprise-ai-brain/history/spec-version-history.md)
- 测试用例版本历史：[02-specs/enterprise-ai-brain/history/test-case-version-history.md](02-specs/enterprise-ai-brain/history/test-case-version-history.md)
