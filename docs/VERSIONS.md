# 版本文档索引

## 当前版本：v1.0.12-docs

- **发布日期**: 2026-07-03
- **主要变更**: 按业务域拆分 API 分册，归档 Spec/API/Test Case 版本历史和拆分前 changelog，主入口文档保留索引、跨域事实源和维护规则。
- **文档入口**: [README.md](./README.md)

---

## 当前文档集

| 文档 | 状态 | 说明 |
|------|------|------|
| [01-prd/enterprise-ai-brain/prd.md](01-prd/enterprise-ai-brain/prd.md) | 当前 | 项目级 PRD。 |
| [02-specs/enterprise-ai-brain/spec.md](02-specs/enterprise-ai-brain/spec.md) | 当前 | 项目级技术规格入口，保留跨域架构、状态机、安全和测试门禁；业务域细节见 [02-specs/enterprise-ai-brain/domains/](02-specs/enterprise-ai-brain/domains/)。 |
| [02-specs/enterprise-ai-brain/api.md](02-specs/enterprise-ai-brain/api.md) | 当前 | 项目级 API 入口；接口细节按业务域拆入 [02-specs/enterprise-ai-brain/api/](02-specs/enterprise-ai-brain/api/)。 |
| [02-specs/enterprise-ai-brain/test-case.md](02-specs/enterprise-ai-brain/test-case.md) | 当前 | 项目级测试入口；详细用例按主题拆入 [02-specs/enterprise-ai-brain/test-cases/](02-specs/enterprise-ai-brain/test-cases/)。 |
| [02-specs/enterprise-ai-brain/history/](02-specs/enterprise-ai-brain/history/) | 归档 | Spec 与 Test Case 文档版本历史。 |
| [02-specs/enterprise-ai-brain/api/version-history.md](02-specs/enterprise-ai-brain/api/version-history.md) | 归档 | API 文档版本历史。 |
| [releases/changelog-2026-07-03-pre-split.md](releases/changelog-2026-07-03-pre-split.md) | 归档 | 拆分前完整 changelog 快照。 |

---

## 文档版本说明

PRD、技术规格、API 文档和测试用例各自按变更独立递增版本号；只要本索引标记为“当前”，即表示它们共同组成当前有效文档集，不要求四个文件的内部版本号完全一致。

## 当前维护策略

后续版本迭代按“入口 + 分册”共同维护：

1. 产品范围和验收标准更新 `01-prd/enterprise-ai-brain/prd.md`。
2. 跨域架构、数据模型主索引、状态机、安全和测试门禁更新 `02-specs/enterprise-ai-brain/spec.md`；业务域细节更新 `02-specs/enterprise-ai-brain/domains/*.md`。
3. API 入口和分册关系更新 `02-specs/enterprise-ai-brain/api.md`；接口、请求响应、错误码和权限更新对应 `02-specs/enterprise-ai-brain/api/*.md`。
4. 测试入口和验收矩阵更新 `02-specs/enterprise-ai-brain/test-case.md`；详细验收、边界、异常、接口和性能测试更新对应 `02-specs/enterprise-ai-brain/test-cases/*.md`。
5. 可交付变更更新 `changelog.md`；长历史或拆分前快照放入 `docs/releases/` 或 `02-specs/enterprise-ai-brain/history/`，版本关系或归档策略变化更新本文件。

---

## 版本命名规范

遵循语义化版本和 Git 标签管理发布版本。文档文件名不携带版本号，历史状态通过 Git 提交和标签追溯。

```text
v{MAJOR}.{MINOR}.{PATCH}

MAJOR: 不兼容的 API 或架构变更
MINOR: 向后兼容的功能新增
PATCH: 向后兼容的问题修复
```

## 版本状态说明

| 状态 | 说明 | 文档处理 |
|------|------|----------|
| 开发中 | 开发分支，未发布 | 当前目录，Draft 或 Review 状态。 |
| 当前版本 | 已发布，正在使用 | 当前目录，Approved 状态。 |
| 维护中 | 旧版本仍在维护 | 通过 Git tag 查看历史文档。 |
| 已归档 | 不再维护 | 必要时复制到归档目录并标记 deprecated。 |

---

## 文档归档规则

### 归档触发条件

- [ ] 大版本发布。
- [ ] 重大架构变更。
- [ ] 产品方向调整。
- [ ] 版本停止维护。

### 推荐归档方式

优先使用 Git tag 保留代码和文档的一致快照。

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git show v1.0.0:docs/README.md
```

如确需在当前仓库并行展示多个大版本，再创建 `docs/archive/<version>/` 并从本文件链接。

---
最后更新: 2026-07-03
