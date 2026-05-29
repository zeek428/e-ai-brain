# 版本文档索引

## 当前版本：v1.0.11-docs

- **发布日期**: 2026-05-29
- **主要变更**: 补齐 PRD 验收映射的详细测试用例，修复正式文档断链，新增 P0 字段级 schema、状态机动作矩阵、核心 API 错误语义和生产就绪 runbook 门禁。
- **文档入口**: [README.md](./README.md)

---

## 当前文档集

| 文档 | 状态 | 说明 |
|------|------|------|
| [01-prd/enterprise-ai-brain/prd.md](01-prd/enterprise-ai-brain/prd.md) | 当前 | 项目级 PRD。 |
| [02-specs/enterprise-ai-brain/spec.md](02-specs/enterprise-ai-brain/spec.md) | 当前 | 项目级技术规格。 |
| [02-specs/enterprise-ai-brain/api.md](02-specs/enterprise-ai-brain/api.md) | 当前 | 项目级 API 文档。 |
| [02-specs/enterprise-ai-brain/test-case.md](02-specs/enterprise-ai-brain/test-case.md) | 当前 | 项目级测试用例。 |

---

## 文档版本说明

PRD、技术规格、API 文档和测试用例各自按变更独立递增版本号；只要本索引标记为“当前”，即表示它们共同组成当前有效文档集，不要求四个文件的内部版本号完全一致。

## 当前维护策略

后续版本迭代直接维护项目级文档：

1. 产品范围和验收标准更新 `01-prd/enterprise-ai-brain/prd.md`。
2. 技术模块、数据模型、状态机、风险和回滚更新 `02-specs/enterprise-ai-brain/spec.md`。
3. 接口、请求响应、错误码和权限更新 `02-specs/enterprise-ai-brain/api.md`。
4. 验收、边界、异常、接口和性能测试更新 `02-specs/enterprise-ai-brain/test-case.md`。
5. 可交付变更更新 `changelog.md`；版本关系或归档策略变化更新本文件。

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
最后更新: 2026-05-29
