# 企业 AI 大脑平台测试用例

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.0 |
| 适用系统版本 | ≥ v1.0.0 |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0.0 | 2026-05-27 | 基于 PRD 和技术规格生成项目级测试用例 | Claude |
| v1.0.1 | 2026-05-27 | 对齐当前 API 契约，补充产品上下文和配置接口测试 | Codex |
| v1.0.2 | 2026-05-28 | 补充四个主体独立维护、需求任务解耦、知识中心运营和主体级审计测试 | Claude |
| v1.0.3 | 2026-05-29 | 补充 GitLab、线上日志、Jenkins、首页看板和 Bug 管理测试用例 | Claude |
| v1.0.4 | 2026-05-29 | 补充研发全链路 AI 任务类型测试覆盖 | Claude |
| v1.0.5 | 2026-05-29 | 补充软件研发全流程感知测试用例 | Claude |
| v1.0.6 | 2026-05-29 | 对齐 PRD 阶段边界，拆分人工确认门禁测试并更新全流程感知编号 | Claude |
| v1.0.7 | 2026-05-29 | 补充用户使用洞察、用户反馈收集和 AI 迭代规划建议测试用例 | Claude |
| v1.0.8 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 纳入 v1 MVP，新增 MR diff 快照、code-review 执行器、人工确认和不回写 GitLab 的 P0 测试 | Claude |
| v1.0.9 | 2026-05-29 | 修正 v1 MVP 与 v1.1/v1.2 测试验收口径，明确 MVP 占位入口和后续完整闭环能力的测试边界 | Claude |
| v1.1.0 | 2026-05-29 | 对齐 PRD v1.1.0，补充 MVP-A/B/C 验收切片，修正 GitLab 每日指标采集阶段归属 | Claude |
| v1.1.1 | 2026-05-29 | 修复产品评审问题：将 GitLab 预览和 diff 快照前置到 MVP-A，拆分 AC4/AC21 测试，改为阶段 + 阶段内优先级口径 | Claude |
| v1.1.2 | 2026-05-30 | 将 Bug 管理基础接口纳入 v1.1 自动化验收，覆盖登记、筛选、状态机、重复归并、权限和审计 | Codex |

---

## 测试用例规范

### 用例编号规则

```text
TC-AIBRAIN-{模块}-{类型}-{序号}

模块:
- PRODUCT: 产品主数据
- REQUIREMENT: 需求管理
- TASK: AI 任务和任务类型
- GRAPH: LangGraph 工作流
- REVIEW: 人工确认
- KNOWLEDGE: 知识检索与沉淀
- OUTPUT: 模拟回写和导出
- AUDIT: 审计
- DEPLOY: 部署
- CONFIG: 产品、相关系统和模型网关配置
- FLOW: 端到端业务流程和软件研发全流程感知
- DEVOPS: GitLab 代码质量和 Jenkins 发布数据
- OPS: 线上运行日志和运营状态
- BUG: Bug 管理
- DASHBOARD: 首页 IT 团队看板
- PLANNING: 用户使用洞察、用户反馈和 AI 迭代规划

类型:
- FUNC: 功能测试
- BOUND: 边界测试
- ERR: 异常测试
- API: 接口测试
- PERF: 性能测试
```

### 用例优先级

测试优先级必须和发布阶段一起解读，避免 v1.2 的 P1 用例阻塞 v1 MVP 发布。

| 字段 | 说明 |
|------|------|
| 适用阶段 | MVP-A、MVP-B、MVP-C、v1.1、v1.2 或 MVP 空状态。 |
| 阶段内优先级 | 当前适用阶段内的 P0/P1/P2/P3。 |

| 阶段内优先级 | 说明 | 通过要求 |
|--------------|------|----------|
| P0 | 当前阶段核心闭环，阻塞该阶段发布 | 当前阶段必须 100% 通过 |
| P1 | 当前阶段重要能力，影响演示和验收 | 当前阶段必须 100% 通过 |
| P2 | 当前阶段一般能力，影响体验 | 当前阶段 ≥ 95% 通过 |
| P3 | 当前阶段边缘场景 | 当前阶段 ≥ 90% 通过 |

---

## MVP 验收切片

v1 MVP 测试按 MVP-A/B/C 三个切片分批执行；三个切片全部通过后才视为 v1 MVP 完整通过。

| 切片 | 阻塞用例 | 验收重点 |
|------|----------|----------|
| MVP-A 基础 + GitLab 输入闭环 | TC-AIBRAIN-TASK-FUNC-001、TC-AIBRAIN-GRAPH-FUNC-002、TC-AIBRAIN-REVIEW-FUNC-003 中产品详细设计/技术方案部分、TC-AIBRAIN-OUTPUT-FUNC-004A、TC-AIBRAIN-DEPLOY-FUNC-007、TC-AIBRAIN-CONFIG-API-008、TC-AIBRAIN-REQ-FUNC-011、TC-AIBRAIN-REVIEW-FUNC-023A | 需求审批、产品详细设计、技术方案、人工确认、Markdown 导出、基础审计、内部 GitLab 只读绑定、MR 预览和 diff 快照可跑通。 |
| MVP-B GitLab Review 闭环 | TC-AIBRAIN-REVIEW-FUNC-023B、TC-AIBRAIN-REVIEW-FUNC-003 中 code_review 部分、TC-AIBRAIN-AUDIT-API-006、TC-AIBRAIN-AUDIT-API-013 | 基于 MVP-A 的 MR 快照生成 code_review 报告、人工确认和内部归档可跑通，且不回写 GitLab。 |
| MVP-C 知识与治理闭环 | TC-AIBRAIN-KNOWLEDGE-FUNC-005、TC-AIBRAIN-OUTPUT-FUNC-004B、TC-AIBRAIN-OUTPUT-FUNC-004C、TC-AIBRAIN-FLOW-FUNC-010、TC-AIBRAIN-KNOWLEDGE-FUNC-012 | 知识导入、权限过滤检索、知识沉淀审核、模拟 Issue、真实空状态入口和主体级治理可跑通。 |

### 模块：AI 任务与工作流闭环

| 用例编号 | 用例名称 | 优先级 | 适用阶段 | 前置条件 | 测试步骤 | 预期结果 | 自动化 |
|----------|----------|--------|----------|----------|----------|----------|--------|
| TC-AIBRAIN-TASK-FUNC-001 | 创建并启动产品详细设计 AI 任务 | P0 | MVP | 用户已登录，存在 `rd_brain`、已审批需求和产品版本 | 1. 创建 product_detail_design 任务 2. 启动任务 3. 查询详情 | 任务从 draft 进入 waiting_review，并返回 review_id 和 task_type | 是 |
| TC-AIBRAIN-GRAPH-FUNC-002 | 信息不足时中断并补充后恢复 | P0 | MVP | 模型返回信息不足判断 | 1. 启动任务 2. 触发 waiting_more_info 3. 提交 answers 4. 再次 start | 任务回到 draft 后再次启动，继续运行到下一节点 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-003 | MVP 产品详细设计、技术方案和 GitLab MR Code Review 人工确认门禁 | P0 | MVP | 任务运行到产品详细设计、技术方案或 code_review 报告确认点 | 1. 查询 pending review 2. 不确认并观察后续阶段 3. approve 4. 查询任务 | 未确认前不进入下一阶段或归档，确认后恢复 graph | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004A | MVP-A Markdown 导出 | P0 | MVP-A | 产品详细设计或技术方案已确认 | 1. GET Markdown 导出接口 2. 检查内容 3. 使用无任务读权限角色重试 | 返回 `text/markdown` 方案内容，并可关联 trace_id；无任务读权限角色返回 403 | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004B | MVP-C 模拟 Issue 幂等生成 | P0 | MVP-C | 任务已确认并进入输出阶段 | 1. GET 查询未写回状态 2. POST 显式生成回写 3. 重复 POST 4. GET 查询结果 | 生成 mock issues，重复触发不产生重复结果，GET 不产生写副作用 | 是 |
| TC-AIBRAIN-OUTPUT-FUNC-004C | MVP-C 知识沉淀候选审核 | P0 | MVP-C | 任务已产生可沉淀内容 | 1. 查询知识候选 2. 批准或拒绝 | 返回 pending deposits，审核后状态正确流转 | 是 |
| TC-AIBRAIN-KNOWLEDGE-FUNC-005 | 知识检索权限过滤和来源引用 | P0 | MVP | 存在不同权限文档 | 1. 以用户 A 检索 2. 以用户 B 检索 | 仅返回有权限文档，结果包含来源字段 | 是 |
| TC-AIBRAIN-AUDIT-API-006 | 写操作和 AI 关键动作产生审计事件 | P1 | MVP | 已执行任务闭环 | 1. 查询 audit events 2. 按 ai_task_id 过滤 | 创建、启动、确认、回写均有审计记录 | 是 |
| TC-AIBRAIN-DEPLOY-FUNC-007 | Docker Compose 本地栈健康检查 | P1 | 生产就绪 | Docker 可用 | 1. 启动 compose 2. 请求 /health 3. 检查 postgres/redis | web/api/db/redis 服务正常，生产就绪门禁可验证 | 是 |
| TC-AIBRAIN-CONFIG-API-008 | 产品、版本、模块和 Git 资源配置 | P1 | MVP | admin 已登录 | 1. 进入产品管理配置弹窗 2. 创建/更新配置 3. 查询 active_only 列表 | 配置可维护，任务可引用产品版本上下文；Git 凭据不在页面或 API 响应中明文展示 | 是 |
| TC-AIBRAIN-CONFIG-API-009 | 平台模型网关配置 | P1 | MVP | admin 已登录 | 1. 进入系统管理/模型网关 2. 创建默认模型配置 3. 查询列表 | 页面和 API 只返回 `api_key_configured`，不泄露明文 API Key | 是 |
| TC-AIBRAIN-FLOW-FUNC-010 | MVP 业务主体独立入口和真实空状态可用 | P0 | MVP | 用户已登录且具备相应角色，至少存在产品、需求、AI 任务和知识文档基础数据 | 1. 进入首页 IT 团队看板 2. 进入产品管理 3. 进入需求管理 4. 进入任务中心 5. 进入 Bug 管理 6. 进入研发运营看板 7. 进入用户洞察/迭代规划 8. 进入知识中心 9. 进入审计与运行 | MVP 必交主体可独立查看或维护；未接入真实采集器的入口展示空状态或禁用态，不返回示例数据、占位统计或伪造结果 | 是 |
| TC-AIBRAIN-REQ-FUNC-011 | 需求审批与任务执行解耦 | P0 | MVP | 存在已批准需求 | 1. 生成 AI 任务 2. 修改产品配置 3. 查询任务详情 | 需求保留审批状态，任务保留生成时 requirement_snapshot 和 product_context | 是 |
| TC-AIBRAIN-KNOWLEDGE-FUNC-012 | 知识中心独立运营 | P0 | MVP | 知识维护者已登录 | 1. 导入文档 2. 查看索引状态 3. 检索 4. 审核沉淀 | 知识中心可独立导入、索引、检索、审核和处理失败 | 是 |
| TC-AIBRAIN-AUDIT-API-013 | 主体级审计查询 | P1 | MVP | 已产生产品、需求、任务、知识操作 | 1. 按 subject_type 查询 2. 按 subject_id 查询 | 返回对应主体的关键写操作和 AI 高影响动作 | 是 |
| TC-AIBRAIN-DEVOPS-FUNC-014 | GitLab 代码质量与提交统计 | P1 | v1.2 | 产品已绑定 GitLab Git 资源 | 1. 采集每日提交 2. 采集代码质量 3. 按产品和人员查询 | 返回按产品、仓库、人员聚合的提交情况和质量结果 | 是 |
| TC-AIBRAIN-OPS-FUNC-015 | 线上运行日志运营分析 | P1 | v1.2 | 已接入线上运行日志样本 | 1. 聚合错误率 2. 聚合延迟 3. 聚合核心业务事件 | 返回按产品、环境、时间窗口的运营状态指标 | 是 |
| TC-AIBRAIN-RELEASE-FUNC-016 | Jenkins 发布数据采集 | P1 | v1.2 | 产品已配置 Jenkins job 映射 | 1. 采集发布记录 2. 查询产品发布历史 | 返回构建状态、部署环境、失败原因和最近成功发布 | 是 |
| TC-AIBRAIN-DASHBOARD-FUNC-017 | v1.2 首页 IT 团队看板完整下钻 | P1 | MVP 空状态 / v1.2 | 存在需求、任务、Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议数据 | 1. 打开首页 2. 按产品筛选 3. 下钻明细 | 展示需求、研发进展、Bug、线上系统健康、核心业务运行、用户使用趋势、用户反馈趋势、AI 迭代规划建议摘要和发布状态；MVP 阶段只要求真实空状态不阻塞验收 | 是 |
| TC-AIBRAIN-BUG-FUNC-018 | v1.1 Bug 管理基础闭环 | P1 | v1.1 | 存在 AI 自动测试和人工测试输入 | 1. AI 自动测试登记 Bug 2. 人工登记 Bug 3. 分派修复 4. 验证关闭 | Bug 按产品归属，来源正确，状态完整流转；重复 Bug 不进入开放队列；写操作产生审计事件 | 是 |
| TC-AIBRAIN-TASK-FUNC-020 | 研发全链路 AI 任务类型覆盖 | P1 | v1.1 / v1.2 | 已存在产品、已审批需求、代码 diff、测试结果、Jenkins 发布记录和线上日志样本 | 1. 分别创建 7 类 task_type 任务 2. 启动并查询详情 3. 检查输出结构 | 每类任务均保留 task_type、产品上下文、人工确认点和对应输出结构 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-019 | v1.1 研发扩展任务人工确认门禁 | P1 | v1.1 | 开发计划或自动化测试任务运行到确认点 | 1. 查询 pending review 2. 不确认并观察后续阶段 3. approve 4. 查询任务 | 开发计划和自动化测试结论未确认前不进入下一阶段或回写 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-023A | MVP-A 内部 GitLab MR 预览和 diff 快照 | P0 | MVP-A | 产品已绑定内部 GitLab 项目，存在已审批需求、已确认技术方案和可访问 MR | 1. 预览 MR 2. 拉取 diff 快照 3. 查询快照摘要 | 返回 MR 元信息、snapshot_id、diff_size_bytes、diff_limit 和 created_at；快照不受后续 MR 变更静默影响 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-023B | MVP-B 内部 GitLab MR Code Review 报告闭环 | P0 | MVP-B | 已存在 MVP-A MR diff 快照，code-review 执行器可用 | 1. 创建 code_review 任务 2. 启动任务 3. 生成 Review 报告 4. 人工确认 5. 查询 GitLab MR 和审计 | 报告只归档到 AI Brain，不回写 GitLab 评论、审批状态或分支变更 | 是 |
| TC-AIBRAIN-REVIEW-FUNC-024 | v1.2 发布和上线后分析人工确认门禁 | P1 | v1.2 | 发布上线评估或上线后分析任务运行到确认点 | 1. 查询 pending review 2. 不确认并观察后续处理 3. approve 或 edited_approve 4. 查询结果 | 发布建议、风险处理或知识沉淀流程必须等待人工确认 | 是 |
| TC-AIBRAIN-FLOW-FUNC-021 | 软件研发全流程感知 | P1 | MVP / v1.2 | 存在 MVP 关联数据；v1.2 完整追溯测试另需提交、Review、测试、Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议关联数据 | 1. 以需求查询 MVP 感知视图 2. 查看上下游 3. 查看风险信号 4. 用 v1.2 数据下钻到关联主体 | MVP 至少返回需求到产品详细设计、技术方案、代码 Review、人工确认、模拟 Issue、知识沉淀和审计事件；v1.2 返回完整上下文链路、风险来源、影响范围和下一步建议 | 是 |
| TC-AIBRAIN-PLANNING-FUNC-022 | v1.2 用户使用洞察与 AI 迭代规划 | P1 | MVP 空状态 / v1.2 | 存在产品规划、需求池、用户使用数据、用户反馈、Bug、线上日志、发布记录和研发投入样本 | 1. 聚合使用指标 2. 收集用户反馈 3. 生成迭代规划建议 4. 检查未自动创建正式需求/变更路线图 5. 产品负责人确认后转需求 | 返回可追溯的下阶段优先迭代需求建议；AI 未经确认不自动创建正式需求或调整路线图/排期；MVP 阶段只要求真实空状态 | 是 |

---

## 详细测试用例

### TC-AIBRAIN-TASK-FUNC-001: 创建并启动产品详细设计 AI 任务

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-001 |
| 用例名称 | 创建并启动产品详细设计 AI 任务 |
| 优先级 | P0 |
| 模块 | TASK |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 用户已通过本地账号登录并持有 Bearer Token。
2. 系统存在启用状态的 `rd_brain`。
3. 系统存在启用产品和未归档产品版本。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/ai-tasks` 创建任务 | 返回 `data.id`，状态为 `draft`。 |
| 2 | POST `/api/ai-tasks/{id}/start` | 返回 `review_id`，任务进入 `waiting_review`，或模型失败时进入 `failed` 并记录错误码。 |
| 3 | GET `/api/ai-tasks/{id}` | 返回任务详情、当前状态和 trace_id。 |

**测试数据**:
```json
{
  "brain_app_code": "rd_brain",
  "task_type": "product_detail_design",
  "title": "支持 Markdown 知识导入",
  "input": {
    "background": "知识散落在 Markdown 中",
    "goal": "导入后可检索引用",
    "product_id": "product_001",
    "version_id": "version_001",
    "module_codes": ["knowledge"]
  }
}
```

**预期结果**:
1. API 响应使用 `{data, trace_id}` envelope。
2. 创建和启动操作均写入审计事件。
3. 任务详情返回 `task_type = product_detail_design`。

**状态**: 待测试

---

### TC-AIBRAIN-GRAPH-FUNC-002: 信息不足时中断并补充后恢复

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-GRAPH-FUNC-002 |
| 用例名称 | 信息不足时中断并补充后恢复 |
| 优先级 | P0 |
| 模块 | GRAPH |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. AI 任务已启动。
2. 测试模型或夹具可让 `is_information_enough` 返回不足。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 等待任务运行到信息评估节点 | 任务状态变为 `waiting_more_info`。 |
| 2 | GET 任务详情 | 返回 clarifying questions。 |
| 3 | POST `/api/ai-tasks/{id}/more-info` | 任务回到 `draft`，补充信息写入 input。 |
| 4 | POST `/api/ai-tasks/{id}/start` | 任务继续运行到下一确认点或完成。 |
| 5 | 在任务管理待确认弹窗点击“要求补充”，再在任务操作弹窗提交补充说明 | 页面分别调用真实 `/api/reviews/{id}/request-more-info` 和 `/api/ai-tasks/{id}/more-info`，任务状态从 `waiting_more_info` 回到 `draft`。 |

**测试数据**:
```json
{
  "answers": [
    {
      "question_id": "q_001",
      "answer": "v1 仅支持 Markdown 文档导入。"
    }
  ]
}
```

**预期结果**:
1. 中断前后 Graph State 不丢失。
2. 补充信息作为审计事件记录。

**状态**: 待测试

---

### TC-AIBRAIN-REVIEW-FUNC-003: MVP 产品详细设计和技术方案人工确认门禁

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-003 |
| 用例名称 | MVP 产品详细设计和技术方案人工确认门禁 |
| 优先级 | P0 |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 任务已运行到任一 review 阶段。
2. 当前用户具备确认权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/ai-tasks/{id}` | 返回 pending review。 |
| 2 | 不提交确认并等待 | 后续阶段不会执行。 |
| 3 | POST `/api/reviews/{id}/approve` | review 状态变为 `approved`。 |
| 4 | 查询任务详情 | 任务恢复 running 或进入下一确认阶段。 |

**测试数据**:
```json
{
  "version": 1,
  "comment": "确认通过"
}
```

**预期结果**:
1. 产品详细设计和技术方案等 MVP 高影响 AI 产出均有人工确认点。
2. version 不匹配时返回 `REVIEW_VERSION_CONFLICT`。

**状态**: 待测试

---

### TC-AIBRAIN-OUTPUT-FUNC-004A/B/C: Markdown、模拟 Issue 和知识候选

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-OUTPUT-FUNC-004A / 004B / 004C |
| 用例名称 | Markdown 导出、模拟 Issue 幂等生成和知识沉淀候选审核 |
| 阶段内优先级 | P0 |
| 模块 | OUTPUT |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 产品详细设计、技术方案或代码 Review 报告已确认。
2. Graph 运行到导出、模拟回写或知识沉淀候选生成阶段。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | MVP-A: GET `/api/export/tasks/{task_id}/markdown` | 返回 `text/markdown` 方案内容，并通过 Header 或日志关联 `trace_id`。 |
| 2 | MVP-C: 在任务中心打开已完成任务的“模拟 Issue”弹窗，GET `/api/writeback/results/{task_id}` | 未写回时页面展示 `not_written`/未写回、幂等键和空 issues，不创建 mock issue。 |
| 3 | MVP-C: 在弹窗中点击生成，POST `/api/writeback/results/{task_id}` | 页面展示模拟 Issue、`completed`/已生成和 idempotency_key。 |
| 4 | MVP-C: 重复 POST 模拟输出 | 不产生重复 mock issue。 |
| 5 | MVP-C: 在知识中心打开“沉淀审核”弹窗查询知识沉淀候选 | 返回 pending deposits。 |
| 6 | MVP-C: 批准或拒绝知识沉淀候选 | 候选状态正确流转，未批准内容不进入正式知识库。 |

**预期结果**:
1. MVP-A 只阻塞 Markdown 导出。
2. MVP-C 阻塞模拟 Issue 幂等生成和知识沉淀候选审核。
3. mock_issues 幂等键唯一，knowledge_deposits 按 `ai_task_id + deposit_type + content_hash` 去重。

**状态**: 待测试

---

### TC-AIBRAIN-KNOWLEDGE-FUNC-005: 知识检索权限过滤和来源引用

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-KNOWLEDGE-FUNC-005 |
| 用例名称 | 知识检索权限过滤和来源引用 |
| 优先级 | P0 |
| 模块 | KNOWLEDGE |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 知识库中存在公开文档和受限文档。
2. 用户 A 有受限文档权限，用户 B 无权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 用户 A POST `/api/knowledge/search` | 返回公开和授权受限 chunk。 |
| 2 | 用户 B 使用相同 query 检索 | 不返回无权限受限 chunk。 |
| 3 | 检查每条结果 | 包含文档 id、title、snippet、source 或等价来源字段。 |
| 4 | 在知识中心打开“知识检索”弹窗并输入同一 query | 页面调用真实 `/api/knowledge/search`，展示可访问结果标题、来源和内容摘要；无结果时展示空状态。 |

**测试数据**:
```json
{
  "brain_app_code": "rd_brain",
  "query": "需求评估规则",
  "filters": {},
  "top_k": 5
}
```

**预期结果**:
1. 权限过滤在数据库查询层完成。
2. AI 输出引用知识时可追溯来源。

**状态**: 待测试

---

### TC-AIBRAIN-AUDIT-API-006: 写操作和 AI 关键动作产生审计事件

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-AUDIT-API-006 |
| 用例名称 | 写操作和 AI 关键动作产生审计事件 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | AUDIT |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 用户已登录并具备创建需求、启动 AI 任务和处理人工确认的权限。
2. 系统已完成一次从需求审批到 AI 任务人工确认的最小闭环。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建需求并提交审批 | 写入 `requirement.created` 或等价审计事件。 |
| 2 | 审批需求并生成 AI 任务 | 写入 `requirement.approved` 和 `ai_task.created` 审计事件。 |
| 3 | 启动 AI 任务并进入人工确认 | 写入 `ai_task.started` 和 `review.created` 审计事件。 |
| 4 | approve 人工确认 | 写入 `review.submitted` 审计事件，包含 review_id、task_id 和 actor_id。 |
| 5 | GET `/api/audit/events?ai_task_id={task_id}` | 返回上述任务相关审计事件，按 created_at 倒序或稳定排序返回。 |

**预期结果**:
1. 创建、审批、启动、人工确认等写操作均可追踪。
2. 审计事件包含主体类型、主体 ID、操作者、事件类型和发生时间。
3. API 响应包含 `trace_id`，但审计表不要求持久化完整 `trace_id`。

**状态**: 待测试

---

### TC-AIBRAIN-DEPLOY-FUNC-007: Docker Compose 本地栈与生产就绪门禁健康检查

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DEPLOY-FUNC-007 |
| 用例名称 | Docker Compose 本地栈与生产就绪门禁健康检查 |
| 优先级 | P1 |
| 适用阶段 | 生产就绪 |
| 模块 | DEPLOYMENT |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. Docker 可用。
2. `.env` 已配置本地运行所需变量。
3. PostgreSQL、Redis、模型网关配置和内部 GitLab 只读凭据引用均按部署 runbook 准备。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 运行 `docker compose config --quiet` | Compose 配置校验通过。 |
| 2 | 运行 `docker compose up -d --build` | web、api、postgres、redis 服务启动。 |
| 3 | GET `/health` | 返回 API、数据库、Redis、模型网关配置状态和 trace_id。 |
| 4 | 验证 PostgreSQL 扩展 | `pgvector` 和 `pgcrypto` 可用。 |
| 5 | 调用模型网关配置查询 | 只返回密钥掩码或 configured 标记，不返回明文。 |
| 6 | 调用 GitLab MR preview 和 snapshot | 只读链路可用，不产生 GitLab 评论、审批、request changes、合并或分支变更。 |

**预期结果**:
1. 本地栈健康检查通过。
2. 生产就绪门禁覆盖配置、凭据、数据库扩展和 GitLab 只读边界。
3. 任一门禁失败时不得宣称环境可发布。

**状态**: 待测试

---

### TC-AIBRAIN-CONFIG-API-008: 产品、版本、模块和 Git 资源配置

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-CONFIG-API-008 |
| 用例名称 | 产品、版本、模块和 Git 资源配置 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | PRODUCT_CONFIG |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. admin 用户已登录。
2. 系统已存在业务大脑 `rd_brain`。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/products` 创建产品 | 返回产品 ID，状态为 active。 |
| 2 | POST `/api/products/{product_id}/versions` 创建版本 | 返回版本 ID，版本归属该产品。 |
| 3 | POST `/api/products/{product_id}/modules` 创建模块 | 返回模块 code，模块归属该产品。 |
| 4 | 在产品管理页面点击“配置”，分别新增版本、模块和 Git 资源 | 弹窗内出现版本管理、模块管理和 Git 资源列表，新增后刷新真实 API 数据。 |
| 5 | POST `/api/products/{product_id}/git-repositories` 绑定内部 GitLab 只读资源 | 返回 repository_id 和 `credential_ref_configured`，不返回凭据引用或明文 token。 |
| 6 | GET `/api/products/{product_id}/versions?active_only=true` | 不返回 archived 版本。 |
| 7 | 使用 archived 版本创建需求或任务 | 返回 `PRODUCT_VERSION_ARCHIVED` 或 `VALIDATION_ERROR`。 |

**预期结果**:
1. 产品、版本、模块、Git 资源可独立维护。
2. 新需求和 AI 任务只能引用有效产品与未归档版本。
3. 写操作产生审计事件。
4. 页面列表只显示 Git 凭据“已配置/未配置”状态，不回显 `credential_ref`。

**状态**: 自动化与 Docker 页面回归通过

---

### TC-AIBRAIN-CONFIG-API-009: 平台模型网关配置

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-CONFIG-API-009 |
| 用例名称 | 平台模型网关配置 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | MODEL_GATEWAY |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. admin 用户已登录。
2. 系统允许通过环境变量或密钥管理系统提供模型 API Key。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 进入系统管理 / 模型网关页面 | 展示模型网关配置管理列表，风格与其他管理列表一致。 |
| 2 | 在页面新增默认模型配置并填写 API Key | POST `/api/system/model-gateway-configs`，返回 config_id、provider、默认模型和 active 状态。 |
| 3 | GET `/api/system/model-gateway-configs` 或刷新页面 | 返回并展示 `api_key_configured=true`，不返回也不渲染明文 API Key、密钥前缀或后缀。 |
| 4 | 在页面编辑配置但 API Key 留空 | PATCH `/api/system/model-gateway-configs/{config_id}` 不携带 `api_key`，服务端保留现有密钥。 |
| 5 | PATCH `/api/system/model-gateway-configs/{config_id}` 禁用配置 | 配置变为 inactive，新任务不能选择该配置。 |
| 6 | 使用 active/default 且已配置 API Key 的 OpenAI-compatible 配置启动任务 | 后端调用 `{base_url}/chat/completions`，请求带 Bearer Token 和 `response_format={"type":"json_object"}`；任务输出使用 provider JSON，模型日志记录 provider/model/tokens/config_id/status，不记录 prompt、完整输出或 API Key。 |
| 7 | 使用缺失密钥或无效 provider 响应启动任务 | 返回 `MODEL_GATEWAY_CONFIG_INVALID` 或 `MODEL_GATEWAY_FAILED`，任务进入 `failed`，不静默完成或回退本地输出。 |

**预期结果**:
1. 系统管理下模型网关配置可维护。
2. 页面、API 响应和日志不泄露模型 API Key。
3. 配置变更、模型调用成功和模型调用失败均产生可追踪事件。

**状态**: 待测试

---

## 主体独立维护测试用例

### TC-AIBRAIN-FLOW-FUNC-010: MVP 业务主体独立入口和真实空状态可用

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-FLOW-FUNC-010 |
| 用例名称 | MVP 业务主体独立入口和真实空状态可用 |
| 优先级 | P0 |
| 模块 | FLOW |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 用户已登录。
2. 系统至少存在产品、需求、AI 任务和知识文档基础数据；Bug 管理在 v1.1 可加载真实列表或空列表，研发运营看板和用户洞察/迭代规划在 MVP 可没有业务数据。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 进入首页 IT 团队看板 | MVP 可展示需求、研发进展、知识沉淀和审计摘要；尚未接入真实采集器的线上系统健康、用户使用、用户反馈、迭代规划和发布能力展示空状态或禁用态，不返回示例数据或伪造统计。 |
| 2 | 进入产品管理 | 可以查看和维护产品、版本、模块和 Git 资源。 |
| 3 | 进入需求管理 | 可以查看需求列表、需求详情和审批状态。 |
| 4 | 进入任务中心 | 可以查看 AI 任务列表；任务类型展示业务中文标签；列表行内仅展示单一“操作”入口，启动产品详细设计任务、确认 Review 输出、从已确认产品详细设计创建技术方案任务、对已完成技术方案执行 Markdown 导出等动作均在上方摘要、下方纵向操作的任务操作弹窗中完成。 |
| 5 | 进入 Bug 管理 | v1.1 可展示真实 Bug 列表、权限校验和真实空列表；登记、分派、验证、关闭和重复归并按 TC-AIBRAIN-BUG-FUNC-018 验收。 |
| 6 | 进入研发运营看板 | MVP 可展示真实接口空状态；GitLab/Jenkins/线上日志完整采集和下钻按 v1.2 验收。 |
| 7 | 进入用户洞察/迭代规划 | MVP 可展示真实接口空状态；使用数据、反馈和 AI 迭代规划闭环按 v1.2 验收。 |
| 8 | 进入知识中心 | 可以查看知识文档、检索、索引状态和沉淀审核。 |
| 9 | 进入审计与运行 | 可以查看审计事件、运行记录、健康检查和失败排查信息。 |

**预期结果**:
1. 产品、需求、AI 任务、知识中心和审计与运行在 MVP 可独立查看或维护。
2. Bug 管理在 v1.1 使用真实 API 或真实空列表；研发运营看板、用户洞察/迭代规划等后续阶段入口在 MVP 不误导为已完成能力，不返回示例数据或占位统计。
3. 用户不需要进入 AI 任务详情页才能维护产品、需求、知识或查看审计运行信息。

**状态**: 待测试

---

### TC-AIBRAIN-REQ-FUNC-011: 需求审批与任务执行解耦

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011 |
| 用例名称 | 需求审批与任务执行解耦 |
| 优先级 | P0 |
| 模块 | REQUIREMENT |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 存在启用产品和未归档版本。
2. 存在状态为 `approved` 的需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/requirements/{id}/generate-task` | 返回 task_id，需求状态变为 `task_created`。 |
| 2 | PATCH 产品、版本或模块名称 | 产品配置更新成功。 |
| 3 | GET `/api/ai-tasks/{task_id}` | 返回生成时的 `requirement_snapshot` 和 `product_context`，不被后续配置修改覆盖。 |
| 4 | GET `/api/requirements/{id}` | 需求仍保留原始输入、审批结论和任务引用。 |

**预期结果**:
1. 需求是业务审批对象，任务是 AI 执行对象。
2. 历史任务解释依赖生成时快照，而不是实时主数据。

**状态**: 待测试

---

### TC-AIBRAIN-KNOWLEDGE-FUNC-012: 知识中心独立运营

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-KNOWLEDGE-FUNC-012 |
| 用例名称 | 知识中心独立运营 |
| 优先级 | P0 |
| 模块 | KNOWLEDGE |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 知识维护者已登录。
2. 系统存在可导入的 Markdown 测试文档。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/knowledge/documents` | 文档创建成功，状态进入 `pending_index` 或 `indexed`。 |
| 2 | GET `/api/knowledge/documents?index_status=indexed` | 可按索引状态查询。 |
| 3 | POST `/api/knowledge/search` | 仅返回有权限的知识结果。 |
| 4 | 审核知识沉淀候选 | 可批准或拒绝，状态正确流转。 |
| 5 | 模拟索引失败后重试 | 展示失败原因，重试后可回到待索引或已索引。 |

**预期结果**:
1. 知识中心不依赖 AI 任务完成也可以主动导入和检索。
2. 知识沉淀必须审核后才能进入正式知识库。

**状态**: 待测试

---

### TC-AIBRAIN-AUDIT-API-013: 主体级审计查询

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-AUDIT-API-013 |
| 用例名称 | 主体级审计查询 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | AUDIT |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 系统已产生产品、需求、AI 任务、知识文档和人工确认相关审计事件。
2. 当前用户具备查看对应主体审计事件的权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/audit/events?subject_type=requirement&subject_id={requirement_id}` | 只返回该需求相关事件。 |
| 2 | GET `/api/audit/events?subject_type=ai_task&subject_id={task_id}` | 返回任务创建、启动、确认、回写相关事件。 |
| 3 | GET `/api/audit/events?subject_type=knowledge_document&subject_id={document_id}` | 返回导入、索引、权限变更或沉淀审核事件。 |
| 4 | 使用无权限用户查询主体审计事件 | 返回 403 或空结果，不泄露主体存在性。 |
| 5 | 使用不存在的 subject_id 查询 | 返回空列表，不报 500。 |

**预期结果**:
1. 审计事件可按主体类型和主体 ID 过滤。
2. 主体级查询遵守同一权限边界。
3. 无结果和无权限场景语义明确。

**状态**: 待测试

---

## 研发运营与 Bug 管理测试用例

### TC-AIBRAIN-DEVOPS-FUNC-014: GitLab 代码质量与提交统计

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DEVOPS-FUNC-014 |
| 用例名称 | GitLab 代码质量与提交统计 |
| 优先级 | P1 |
| 模块 | DEVOPS |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 产品已绑定状态为 `active` 的 GitLab Git 资源。
2. GitLab 采集夹具包含提交、作者、Merge Request、代码变更量和代码质量审核结果。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 触发每日 GitLab 指标采集 | 提交、作者、MR、变更量和质量风险写入产品维度指标。 |
| 2 | GET `/api/devops/gitlab/daily-code-metrics?product_id=product_001&date=2026-05-29` | 返回产品、仓库、日期、提交数量、活跃作者数、质量评分和风险数量。 |
| 3 | 按人员查看作者聚合 | 返回每位作者的提交数、变更行数和代码审核问题数。 |
| 4 | 注入无法映射产品的仓库数据 | 数据进入待归属队列，不参与产品级统计。 |

**预期结果**:
1. GitLab 指标必须通过 `product_git_repositories` 归属产品。
2. 产品级统计不混入未归属仓库数据。
3. 采集完成和采集失败均保留可排查的运行记录或审计事件。

**状态**: 待测试

---

### TC-AIBRAIN-OPS-FUNC-015: 线上运行日志运营分析

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-OPS-FUNC-015 |
| 用例名称 | 线上运行日志运营分析 |
| 优先级 | P1 |
| 模块 | OPS |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 已接入线上运行日志样本，日志可映射到产品、模块和环境。
2. 日志样本包含错误、接口耗时和核心业务事件。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 聚合指定产品 24 小时线上日志 | 生成错误率、P95 延迟、核心业务事件数量和异常趋势。 |
| 2 | GET `/api/ops/online-log-metrics?product_id=product_001&environment=prod&from=2026-05-29T00:00:00Z&to=2026-05-29T23:59:59Z` | 返回产品、环境、时间窗口、错误率、延迟和 top_errors。 |
| 3 | 按模块过滤指标 | 仅返回对应模块的日志聚合结果。 |
| 4 | 模拟日志源不可用 | 返回 `DEVOPS_SOURCE_UNAVAILABLE` 或展示最后成功采集时间和失败原因。 |

**预期结果**:
1. 线上运行日志指标支持按产品、模块、环境和时间窗口查询。
2. 外部数据源失败时不得静默返回空指标。
3. 核心业务事件和系统健康指标可被首页看板复用。

**状态**: 待测试

---

### TC-AIBRAIN-RELEASE-FUNC-016: Jenkins 发布数据采集

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-RELEASE-FUNC-016 |
| 用例名称 | Jenkins 发布数据采集 |
| 优先级 | P1 |
| 模块 | DEVOPS |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 产品已配置 Jenkins job 到产品版本的映射。
2. Jenkins 采集夹具包含成功、失败和进行中的构建记录。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 触发 Jenkins 发布记录采集 | job、build_id、状态、环境、版本、触发人、耗时和失败原因被记录。 |
| 2 | GET `/api/devops/jenkins/releases?product_id=product_001&version_id=version_001` | 返回产品版本下的发布记录列表。 |
| 3 | 查询最近成功发布 | 返回最近成功部署时间、环境和构建 ID。 |
| 4 | 查询失败发布 | 返回失败原因，不覆盖最近成功发布信息。 |

**预期结果**:
1. Jenkins 发布记录必须按产品和版本归属。
2. 发布失败原因可用于首页看板风险摘要。
3. 发布记录可关联 GitLab 提交、需求、AI 任务或线上日志事件。

**状态**: 待测试

---

### TC-AIBRAIN-DASHBOARD-FUNC-017: 首页 IT 团队看板

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DASHBOARD-FUNC-017 |
| 用例名称 | 首页 IT 团队看板 |
| 优先级 | P1 |
| 模块 | DASHBOARD |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 系统存在需求、AI 任务、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈、AI 迭代规划建议和知识沉淀统计数据。
2. 用户具备查看首页 IT 团队看板权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开首页 IT 团队看板 | 展示需求、研发进展、Bug、线上系统健康、核心业务运行、用户使用趋势、用户反馈趋势、AI 迭代规划建议摘要、发布状态和知识沉淀统计。 |
| 2 | GET `/api/dashboard/it-team?product_id=product_001&time_range=7d` | 返回同一产品维度下的聚合指标。 |
| 3 | 按产品切换筛选 | 看板所有卡片同步切换产品归属。 |
| 4 | 从 Bug、发布或线上健康卡片下钻 | 跳转到对应主体列表或明细，并保留产品和时间范围上下文。 |

**预期结果**:
1. 首页只展示聚合和风险摘要，明细下钻到对应主体页面。
2. 看板指标来源可追溯到需求、任务、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件。
3. 无数据产品展示空状态，不报 500。

**状态**: 待测试

---

### TC-AIBRAIN-BUG-FUNC-018: Bug 管理基础闭环

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-BUG-FUNC-018 |
| 用例名称 | Bug 管理基础闭环 |
| 优先级 | P1 |
| 模块 | BUG |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 存在启用产品、版本和模块。
2. 存在 AI 自动测试执行结果和人工测试登记输入。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/bugs`，source=`ai_auto_test` 且不带 reproduce_steps | Bug 创建成功，来源为 AI 自动测试，状态为 `needs_info`。 |
| 2 | POST `/api/bugs`，source=`manual_test` | Bug 创建成功，来源为人工测试。 |
| 3 | PATCH `/api/bugs/{id}` 补充复现步骤并分派处理人 | 状态按 `needs_info -> triaged -> assigned` 或 `open -> assigned` 合法流转。 |
| 4 | PATCH `/api/bugs/{id}` 标记 fixed/verified/closed | Bug 完成修复、验证和关闭。 |
| 5 | 创建重复 Bug 并设置 duplicate_of_bug_id | 重复 Bug 关联主 Bug，不重复进入修复队列。 |
| 6 | 使用无写权限角色 POST `/api/bugs` | 返回 `FORBIDDEN`，不创建 Bug。 |

**预期结果**:
1. Bug 必须归属产品，可关联版本、模块、需求、任务、提交、发布或线上日志事件。
2. AI 自动测试和人工测试登记来源可区分。
3. Bug 状态流转、重复归并和越权拦截写入或保留可追溯审计语义。

**状态**: 待测试

---

### TC-AIBRAIN-TASK-FUNC-020: 研发全链路 AI 任务类型覆盖

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-020 |
| 用例名称 | 研发全链路 AI 任务类型覆盖 |
| 优先级 | P1 |
| 模块 | TASK |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 存在已审批需求、产品上下文、代码 diff、测试结果、Jenkins 发布记录和线上日志样本。
2. 当前用户具备创建和启动 AI 任务权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 分别创建 `product_detail_design`、`technical_solution`、`development_planning` 任务 | 均返回 `task_type`，并保留需求快照和产品上下文。 |
| 2 | 创建 `code_review` 任务并传入内部 GitLab MR diff 快照 | 输出结构化 Review 报告、风险等级、文件/行号、修改建议和执行器元数据。 |
| 3 | 创建 `automated_testing` 任务并传入测试结果 | 输出测试分析，可生成来源为 `ai_auto_test` 的 Bug 建议。 |
| 4 | 创建 `release_readiness` 任务 | 输出上线检查清单、发布风险评估和回滚建议。 |
| 5 | 创建 `post_release_analysis` 任务 | 输出上线后健康报告、异常趋势和疑似回归 Bug。 |

**预期结果**:
1. 七类任务均复用统一任务状态机、人工确认、审计和详情查询能力。
2. v1 系列不自动改代码、不自动提交 PR、不自动部署上线。
3. 自动化测试和上线后分析产生的 Bug 必须进入 Bug 管理闭环。

**状态**: 待测试

---

### TC-AIBRAIN-REVIEW-FUNC-019: v1.1 研发扩展任务人工确认门禁

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-019 |
| 用例名称 | v1.1 研发扩展任务人工确认门禁 |
| 优先级 | P1 |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. `development_planning` 或 `automated_testing` 任务已运行到确认点。
2. 当前用户具备对应任务类型的确认权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/ai-tasks/{id}` | 返回 pending review 和 task_type。 |
| 2 | 不提交确认并等待 | 开发计划或自动化测试结论不进入下一阶段或回写。 |
| 3 | POST `/api/reviews/{id}/approve` | review 状态变为 `approved`。 |
| 4 | 查询任务详情 | 任务恢复 running、进入下一阶段或完成。 |

**预期结果**:
1. v1.1 研发扩展任务的高影响结论均受人工确认门禁保护。
2. 自动化测试任务生成 Bug 建议时，进入 Bug 管理前保留产品归属和复现信息要求。

**状态**: 待测试

---

### TC-AIBRAIN-REVIEW-FUNC-024: v1.2 发布和上线后分析人工确认门禁

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-024 |
| 用例名称 | v1.2 发布和上线后分析人工确认门禁 |
| 优先级 | P1 |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. `release_readiness` 或 `post_release_analysis` 任务已运行到确认点。
2. 当前用户具备发布负责人、运营负责人或研发负责人确认权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/ai-tasks/{id}` | 返回 pending review、风险结论和建议动作。 |
| 2 | 不提交确认并等待 | 发布建议采纳、风险处理或知识沉淀流程不继续。 |
| 3 | POST `/api/reviews/{id}/edit-approve` | 保存人工修改后的确认内容。 |
| 4 | 查询任务结果 | 任务基于确认后的内容进入后续流程或完成。 |

**预期结果**:
1. 发布上线评估和上线后分析不能绕过人工确认。
2. 系统只给出风险判断和建议，不自动部署上线。

**状态**: 待测试

---

### TC-AIBRAIN-REVIEW-FUNC-023A: MVP-A 内部 GitLab MR 预览和 diff 快照

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-023A |
| 用例名称 | MVP-A 内部 GitLab MR 预览和 diff 快照 |
| 阶段内优先级 | P0 |
| 适用阶段 | MVP-A |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 产品已绑定内部 GitLab 项目、可解析的 `remote_url` 或 `GITLAB_BASE_URL`，并通过 `env:GITLAB_READONLY_TOKEN` 等凭据引用提供只读 token；当前用户具备该产品和 MR 的 Review 权限。
2. 存在已审批需求、已确认产品详细设计和已确认技术方案。
3. 内部 GitLab 中存在可访问 Merge Request，且 diff 未超过 v1 MVP 限制。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview` | 返回 MR 标题、作者、source/target branch、changed_file_count、diff_refs 和 web_url。 |
| 2 | POST `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot` | 返回 snapshot_id、diff_size_bytes、diff_limit 和 created_at；快照不受后续 MR 变更静默影响。 |
| 3 | 再次拉取相同 diff | 可返回已有 snapshot_id 或创建新运行记录，但必须可审计。 |
| 4 | 输入超过 diff 限制的 MR | 返回 `GITLAB_MR_DIFF_TOO_LARGE`，不得静默截断后继续。 |
| 5 | 移除 GitLab base URL 或只读 token 后重试 preview | 返回 `GITLAB_CONFIG_INVALID` 或 `GITLAB_CREDENTIAL_UNAVAILABLE`，不得生成本地假 MR。 |

**预期结果**:
1. MVP-A 已具备内部 GitLab 只读输入依赖。
2. MR 快照是后续 code_review 任务的唯一输入来源。
3. 系统不得向 GitLab 回写评论、审批状态、request changes、合并状态或分支变更。

**状态**: 待测试

---

### TC-AIBRAIN-REVIEW-FUNC-023B: MVP-B 内部 GitLab MR Code Review 报告闭环

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-023B |
| 用例名称 | MVP-B 内部 GitLab MR Code Review 报告闭环 |
| 阶段内优先级 | P0 |
| 适用阶段 | MVP-B |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 已存在已确认的 `technical_solution` 任务和产品 GitLab 只读资源绑定。
2. code-review 执行器默认适配 Claude Code `code-review` skill。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在任务中心基于已完成 `technical_solution` 选择产品 GitLab 仓库并预览 MR | 页面展示 MR 标题、作者、分支、变更文件数和“不回写 GitLab”提示。 |
| 2 | 生成 MR diff 快照并 POST `/api/ai-tasks` 创建 `task_type=code_review` 任务 | 任务为 `draft`，input 包含 requirement_snapshot、product_context 和 gitlab_mr_snapshot 引用。 |
| 3 | POST `/api/ai-tasks/{id}/start` | 调用 code-review 执行器，任务进入 `waiting_review`，返回 pending review。 |
| 4 | 在任务中心查看 Code Review 报告或 GET `/api/ai-tasks/{id}/code-review-report` | 返回 summary、risk_level、findings、文件/行号、建议、confidence、executor metadata 和 human_review。 |
| 5 | POST `/api/reviews/{id}/approve` 或 `edit-approve` | Review 报告归档到 AI Brain 内部，任务继续或完成。 |
| 6 | 查询 GitLab MR | 未新增评论，未改变审批状态、request changes、合并状态或分支。 |
| 7 | GET `/api/audit/events?ai_task_id={id}` | 返回执行器调用、报告生成、人工确认和归档审计事件。 |

**预期结果**:
1. v1 MVP 可以基于内部 GitLab MR diff 快照生成结构化 Review 报告。
2. Review 报告必须经过人工确认后才能归档为正式结论。
3. 系统不得向 GitLab 回写评论、审批状态、request changes、合并状态或分支变更。
4. 执行器失败时返回明确错误码并写入审计。

**状态**: 待测试

---

### TC-AIBRAIN-FLOW-FUNC-021: 软件研发全流程感知

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-FLOW-FUNC-021 |
| 用例名称 | 软件研发全流程感知 |
| 优先级 | P1 |
| 模块 | FLOW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 存在 MVP 数据：已审批需求、产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、知识沉淀和审计事件。
2. v1.2 扩展测试需要额外准备提交、自动化测试结果、Bug、Jenkins 发布记录、线上日志、用户使用、用户反馈和迭代规划建议关联数据。
3. 上述数据均可映射到同一产品、版本、模块或需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 以 MVP 数据查询感知视图 | 返回需求下游产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、模拟 Issue、知识沉淀和审计事件。 |
| 2 | 从感知视图下钻到任务或审计事件 | 保留产品、版本、模块、需求和时间范围上下文。 |
| 3 | 以 v1.2 数据查询感知视图 | 返回提交、Review、测试、Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议等扩展关系。 |
| 4 | 注入无法归属产品的提交 | 进入待归属队列，不参与需求级风险结论。 |

**预期结果**:
1. 全流程感知在 v1 MVP 至少支持从需求查看下游产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、模拟 Issue、知识沉淀和审计事件。
2. v1.2 扩展后可以从任一主体追溯上游依据和下游影响。
3. 风险信号必须包含来源主体、影响摘要和处理建议。
4. 上下游链路缺失时明确标识缺口，不把缺失上下文当作无风险。

**状态**: 待测试

---

### TC-AIBRAIN-PLANNING-FUNC-022: 用户使用洞察与 AI 迭代规划

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-PLANNING-FUNC-022 |
| 用例名称 | 用户使用洞察与 AI 迭代规划 |
| 优先级 | P1 |
| 模块 | PLANNING |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 存在产品规划、需求池、Bug、线上日志、发布记录和研发投入样本。
2. 已采集实际业务系统用户使用数据和用户反馈样本。
3. 用户具备产品负责人或 IT 管理者权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 聚合产品用户使用指标 | 返回活跃用户、功能访问、关键路径转化、停留、异常退出和低使用功能。 |
| 2 | 收集并查询用户反馈 | 返回满意度、问题反馈、改进建议、投诉、来源渠道、标签和关联模块。 |
| 3 | 触发 AI 迭代规划建议生成 | 返回下阶段优先迭代需求建议清单，状态为 `suggested`，不创建新 requirement。 |
| 4 | 查看建议详情 | 每条建议包含推荐理由、用户证据、业务价值、风险信号、依赖条件、预估研发投入和建议优先级。 |
| 5 | 模拟使用数据不足或反馈样本过少 | 建议标识证据不足，不给出确定性排序。 |
| 6 | 查询需求列表和产品规划 | 未出现由 AI 建议自动创建的新需求、路线图变更或迭代排期变更。 |
| 7 | 产品负责人确认采纳并选择转正式需求 | 建议状态变为 `converted_to_requirement`，并返回人工确认后创建的 requirement_id。 |

**预期结果**:
1. AI 迭代规划建议可追溯到产品规划、需求、用户使用指标、用户反馈、Bug、线上日志或发布记录。
2. AI 只生成建议，不自动创建正式需求、不自动变更路线图、不自动调整迭代排期。
3. 只有产品负责人或等价权限确认采纳后，建议才能转为正式需求或进入迭代计划。
4. 无法归属产品或模块的使用数据和反馈进入待归属队列。

**状态**: 待测试

---

## 边界测试用例

| 用例编号 | 边界类型 | 测试数据 | 预期结果 |
|----------|----------|----------|----------|
| TC-AIBRAIN-TASK-BOUND-001 | 空标题 | `title = ""` | 返回 `VALIDATION_ERROR`。 |
| TC-AIBRAIN-KNOWLEDGE-BOUND-002 | top_k 超过上限 | `top_k = 1000` | 按最大允许值截断或返回校验错误。 |
| TC-AIBRAIN-REVIEW-BOUND-003 | 重复确认 | 同一 review 连续 approve 两次 | 第二次返回状态错误或版本冲突。 |
| TC-AIBRAIN-AUDIT-BOUND-004 | 空审计结果 | 不存在的 ai_task_id | 返回空列表，不报 500。 |

---

## 异常测试用例

| 用例编号 | 异常类型 | 触发条件 | 预期结果 |
|----------|----------|----------|----------|
| TC-AIBRAIN-AUTH-ERR-001 | 未授权 | 无 Bearer Token 调用写接口 | 返回 `UNAUTHORIZED`。 |
| TC-AIBRAIN-TASK-ERR-002 | 非法状态 | completed 任务再次 start | 返回 `TASK_STATE_INVALID`。 |
| TC-AIBRAIN-REVIEW-ERR-003 | 版本冲突 | 使用过期 version 确认 | 返回 `REVIEW_VERSION_CONFLICT`。 |
| TC-AIBRAIN-GRAPH-ERR-004 | 模型失败 | 模型网关返回错误 | 任务进入 failed 或可重试状态，记录审计。 |
| TC-AIBRAIN-KNOWLEDGE-ERR-005 | embedding 维度不匹配 | embedding 写入 pgvector 失败 | 返回明确错误并阻止索引完成。 |
| TC-AIBRAIN-KNOWLEDGE-ERR-006 | 知识索引失败 | 文档内容无法切片或 embedding 调用失败 | 文档进入 `index_failed`，保留失败原因并允许重试。 |

---

## API 测试用例

| 用例编号 | 接口 | 场景 | 预期结果 |
|----------|------|------|----------|
| TC-AIBRAIN-TASK-API-001 | POST /api/ai-tasks | 正常创建 `product_detail_design` 任务 | 201/200，返回 task id 和 task_type。 |
| TC-AIBRAIN-TASK-API-002 | GET /api/ai-tasks/{id} | 查询无权限任务 | 403 或 404。 |
| TC-AIBRAIN-TASK-API-019 | POST /api/ai-tasks | 创建七类研发全链路 task_type | 均返回对应 task_type，非法类型返回 `VALIDATION_ERROR`。 |
| TC-AIBRAIN-REVIEW-API-003 | POST /api/reviews/{id}/edit-approve | 修改后采纳 | 保存 edited_content 并恢复 graph。 |
| TC-AIBRAIN-KNOWLEDGE-API-004 | POST /api/knowledge/search | 正常检索 | 返回 items，包含 title、snippet、source。 |
| TC-AIBRAIN-OUTPUT-API-005 | GET /api/export/tasks/{task_id}/markdown | MVP-A 导出方案 | 返回 `text/markdown`，并通过 Header 或日志关联 trace_id。 |
| TC-AIBRAIN-AUDIT-API-006 | GET /api/audit/events?ai_task_id={id} | 按任务查询 | 返回 items，最多 120 条。 |
| TC-AIBRAIN-AUDIT-API-013 | GET /api/audit/events?subject_type={type}&subject_id={id} | 按主体查询 | 返回指定主体的审计事件。 |
| TC-AIBRAIN-DEVOPS-API-014 | GET /api/devops/gitlab/daily-code-metrics | 查询 GitLab 每日指标 | 返回按产品归属的提交和代码质量指标。 |
| TC-AIBRAIN-OPS-API-015 | GET /api/ops/online-log-metrics | 查询线上运行日志指标 | 返回错误率、延迟和核心业务事件。 |
| TC-AIBRAIN-RELEASE-API-016 | GET /api/devops/jenkins/releases | 查询 Jenkins 发布 | 返回发布状态、失败原因和最近成功发布。 |
| TC-AIBRAIN-DASHBOARD-API-017 | GET /api/dashboard/it-team | 查询首页 IT 团队看板 | 返回需求、研发、Bug、线上系统、核心业务和发布统计。 |
| TC-AIBRAIN-LIFECYCLE-API-021 | GET /api/lifecycle/context | 查询软件研发全流程感知 | 返回上下游关系、风险信号、影响摘要和建议。 |
| TC-AIBRAIN-PLANNING-API-022 | GET/POST /api/planning/iteration-suggestions | 查询或生成 AI 迭代规划建议 | 返回建议清单、优先级、证据链、价值、风险、依赖和投入评估，不自动创建正式需求或调整路线图/排期。 |
| TC-AIBRAIN-PLANNING-API-023 | POST /api/planning/iteration-suggestions/{suggestion_id}/decide | 产品负责人确认迭代规划建议 | accepted/edited_accepted 后才允许转正式需求，未确认时返回 `ITERATION_PLAN_CONFIRMATION_REQUIRED` 或保持 suggested 状态。 |
| TC-AIBRAIN-BUG-API-018 | GET/POST/PATCH /api/bugs | Bug 查询、登记和状态更新 | 支持 AI 自动测试和人工测试来源，状态正确流转。 |
| TC-AIBRAIN-CONFIG-API-008 | GET/POST/PATCH 产品配置接口 | 配置产品上下文 | 返回 items 或配置详情，写操作产生审计。 |
| TC-AIBRAIN-CONFIG-API-009 | GET/POST/PATCH /api/system/model-gateway-configs | 配置平台模型网关 | 返回 api_key_configured，不返回明文或密钥片段。 |

---

## 性能测试用例

| 用例编号 | 指标 | 测试方式 | 目标 |
|----------|------|----------|------|
| TC-AIBRAIN-TASK-PERF-001 | 任务详情接口 | 并发查询任务详情 | P95 < 500ms。 |
| TC-AIBRAIN-KNOWLEDGE-PERF-002 | 知识检索 | 1000 个 chunk 数据集执行 top_k 检索 | P95 < 1s。 |
| TC-AIBRAIN-AUDIT-PERF-003 | 审计查询 | 按 ai_task_id 查询 | P95 < 500ms。 |
| TC-AIBRAIN-DASHBOARD-PERF-004 | 首页 IT 团队看板 | 读取 30 天产品指标快照 | P95 < 800ms。 |
| TC-AIBRAIN-OPS-PERF-005 | 线上运行日志指标查询 | 按产品和环境查询 24 小时窗口 | P95 < 1s。 |
| TC-AIBRAIN-LIFECYCLE-PERF-006 | 软件研发全流程感知查询 | 从需求查询两跳上下游和风险信号 | P95 < 1s。 |
| TC-AIBRAIN-PLANNING-PERF-007 | 用户洞察和迭代规划查询 | 读取 30 天产品使用、反馈和规划建议聚合快照 | P95 < 800ms。 |

---

## 测试执行记录

### 执行汇总

| 批次 | 执行日期 | 执行人 | 用例总数 | 通过 | 失败 | 阻塞 | 通过率 |
|------|----------|--------|----------|------|------|------|--------|
| 1 | 2026-05-29 |  | 待执行统计 |  |  |  |  |

### 缺陷追踪

| 缺陷编号 | 关联用例 | 缺陷描述 | 严重程度 | 状态 | 修复版本 |
|----------|----------|----------|----------|------|----------|
|  |  |  |  |  |  |

---
最后更新: 2026-05-29
