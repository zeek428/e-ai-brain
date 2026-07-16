# 核心工作流测试用例

> 来源：../test-case.md。该文件按业务域承接详细测试用例，主入口保留索引与通用规范。

## 详细测试用例

### TC-AIBRAIN-TASK-FUNC-001: 协作工作项内部创建并派发产品详细设计 AI 任务

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-001 |
| 用例名称 | 协作工作项内部创建并派发产品详细设计 AI 任务 |
| 优先级 | P0 |
| 模块 | TASK |
| 创建人 | Claude |
| 创建日期 | 2026-05-27 |

**前置条件**:
1. 用户已通过本地账号登录并持有 Bearer Token，系统同时具备协作编排服务身份。
2. 系统存在启用状态的 `rd_brain`、统一研发执行策略、AI 数字员工和执行器档案。
3. 系统存在已完成正式评估和组版的需求、`active` 迭代版本、协作运行及状态为 `ready` 的产品详细设计工作项。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 真人分别 POST `/api/ai-tasks` 和 `/api/ai-tasks/{id}/start` | 均返回 `409 RD_COLLABORATION_REQUIRED`，不创建、不启动、不推进需求。 |
| 2 | 协作编排器调用内部 `create_ai_task_for_work_item` | 创建唯一 AI 任务并关联 `collaboration_run_id/work_item_id`，冻结岗位、`ai_employee_id`、`executor_profile_id` 和策略快照。 |
| 3 | 协作编排器调用内部 `dispatch_ai_task_for_work_item` | 工作项从 ready 进入 running，任务进入运行；成功时进入独立质量门禁/待审核，失败时记录错误和可恢复状态。 |
| 4 | 重复创建、派发或 Runner 完成事件并查询详情 | 幂等返回同一任务/结果，任务详情返回协作、工作项、员工、执行器、当前状态和 trace_id。 |

**测试数据**:
```json
{
  "brain_app_code": "rd_brain",
  "collaboration_run_id": "rd_run_001",
  "work_item_id": "rd_work_item_design_001",
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
2. 内部创建和派发操作均写入审计事件；外部拒绝写入安全审计但无业务副作用。
3. 任务详情返回 `task_type = product_detail_design`、协作/工作项引用以及独立员工和执行器归因。

**状态**: v2.0 待由 `test_rd_requirement_entry_adapters.py` 和 `test_rd_work_item_execution.py` 自动化；现有直接创建/启动测试在一次性切换时重写为兼容拒绝与内部服务测试。

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
1. AI 任务已由协作工作项内部派发。
2. 测试模型或夹具可让 `is_information_enough` 返回不足。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 等待任务运行到信息评估节点 | 任务状态变为 `waiting_more_info`。 |
| 2 | GET 任务详情 | 返回 clarifying questions。 |
| 3 | POST `/api/ai-tasks/{id}/more-info` | 任务回到 `draft`，补充信息写入 input。 |
| 4 | 协作编排器消费补充事件并按原 thread 恢复 | 任务按平台冻结的恢复目标继续运行到下一确认点或完成；真人调用 `/start` 仍被拒绝。 |
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
2. 补充信息作为审计事件记录，由协作编排器继续原任务，不创建新任务或开放真人直接启动。

**状态**: 已自动化覆盖。后端状态流转见 `apps/api/tests/test_review_actions.py::test_reject_and_request_more_info_move_task_to_documented_states`，前端任务弹窗补充信息链路见 `apps/web/tests/App.test.tsx::requests and submits more information from task management dialogs`。Review reject/request-more-info 主路径 DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_reject_and_more_info_reviews_write_decisions_without_request_persist`；cancel/submit-more-info 任务状态 DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_cancel_and_submit_more_info_write_task_state_without_request_persist`。

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

**状态**: 已自动化覆盖。产品详细设计、技术方案和 Code Review 人工确认门禁分别见 `apps/api/tests/test_graph_runtime.py`、`apps/api/tests/test_technical_solution_export.py`、`apps/api/tests/test_code_review_report.py` 与 `apps/web/tests/App.test.tsx` 任务操作弹窗用例。Review approve/edit-approve 主路径 DB-first no-persist 回归见 `apps/api/tests/test_database_persistence.py::test_approve_review_writes_completion_records_without_request_persist` 和 `apps/api/tests/test_database_persistence.py::test_edit_approve_review_writes_completion_records_without_request_persist`。

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
| 5 | MVP-C: 在知识中心打开“沉淀审核”弹窗查询知识沉淀候选 | 返回 pending deposits，列表固定列宽并提供按 `knowledge_deposit` 主体进入统一需求全链路的入口。 |
| 6 | MVP-C: 批准或拒绝知识沉淀候选 | 候选状态正确流转，未批准内容不进入正式知识库，全链路入口仍可用于追溯候选来源任务和需求链路。 |

**预期结果**:
1. MVP-A 只阻塞 Markdown 导出。
2. MVP-C 阻塞模拟 Issue 幂等生成和知识沉淀候选审核。
3. mock_issues 幂等键唯一，knowledge_deposits 按 `ai_task_id + deposit_type + content_hash` 去重。

**状态**: 已自动化覆盖。Markdown 导出见 `apps/api/tests/test_technical_solution_export.py`，export router 不回调 legacy main 的边界回归见 `apps/api/tests/test_router_boundaries.py::test_export_router_does_not_call_legacy_main`；模拟 Issue 幂等和知识沉淀审核见 `apps/api/tests/test_knowledge_governance.py` 与 `apps/web/tests/App.test.tsx::sends MVP-C writeback and knowledge deposit mutations to backend APIs`；知识沉淀审核列表全链路入口和固定表格布局见 `apps/web/tests/KnowledgePage.test.tsx::opens knowledge deposit review and approves a pending deposit`；Mock Writeback handler 级 DB-first 写入与 task workflow source rows 恢复见 `apps/api/tests/test_database_persistence.py::test_mock_writeback_writes_repository_without_request_persist`，writeback router 不回调 legacy main 的边界回归见 `apps/api/tests/test_router_boundaries.py::test_writeback_router_does_not_call_legacy_main`。

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
| 4 | 将 indexed 文档的 chunk 行清空后再次检索 | 返回空结果，不用整篇文档合成 `*_chunk_001` 兜底来源。 |
| 5 | 在知识中心打开“知识检索”弹窗并输入同一 query | 页面调用真实 `/api/knowledge/search`，展示可访问结果标题、来源和内容摘要；无结果时展示空状态。 |

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
2. AI 输出引用知识时可追溯到真实存在的 chunk 来源。
3. 索引状态与 chunk 行不一致时暴露真实空结果，不返回合成数据。

**状态**: 已自动化覆盖。权限过滤、来源引用、embedding 排序和无兜底结果见 `apps/api/tests/test_knowledge_governance.py`；前端检索弹窗见 `apps/web/tests/KnowledgePage.test.tsx::opens knowledge search and shows permission-filtered sources`。

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
1. 用户已登录并具备创建需求、参与正式评估、处理协作工作项或人工确认的权限。
2. 系统已完成一次从需求评估、版本归组、协作工作项到人工确认的最小闭环。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建需求并发起正式评估 | 写入 `requirement.created` 和 `requirement_assessment.created` 或等价审计事件。 |
| 2 | 提交评估意见与 accepted 决策并完成版本归组 | 写入评估意见、`requirement_assessment.decided` 和版本 assignment 审计；需求依次达到 `approved/planned`。 |
| 3 | 创建协作运行，调度器领取工作项并通过内部服务创建/派发 AI 任务 | 写入协作运行、工作项 attempt、`ai_task.created/started` 和 `review.created` 审计；公开 create/start 返回 `RD_COLLABORATION_REQUIRED`。 |
| 4 | approve 人工确认 | 写入 `review.submitted` 审计事件，包含 review_id、task_id 和 actor_id。 |
| 5 | GET `/api/audit/events?ai_task_id={task_id}` | 返回上述任务相关审计事件，按 created_at 倒序或稳定排序返回。 |

**预期结果**:
1. 创建、评估、归组、协作派发、人工确认等写操作均可追踪。
2. 审计事件包含主体类型、主体 ID、操作者、事件类型和发生时间。
3. API 响应包含 `trace_id`，但审计表不要求持久化完整 `trace_id`。

**状态**: v1 审计持久化已覆盖；v2.0 评估、归组、协作运行、工作项 attempt 和内部任务派发审计待按实施计划重写。现有主体/操作者/时间过滤与 DB-first 写入回归继续保留。

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
| 3 | GET `/health` | 返回 API、数据库、Redis、模型网关配置状态和 trace_id；存在持久化 active/default 模型网关且已配置密钥时返回 `model_gateway=configured`。 |
| 4 | 验证 PostgreSQL 扩展 | `pgvector` 和 `pgcrypto` 可用。 |
| 5 | 调用模型网关配置查询 | 只返回密钥掩码或 configured 标记，不返回明文。 |
| 6 | 调用 GitLab MR preview 和 snapshot | 只读链路可用，不产生 GitLab 评论、审批、request changes、合并或分支变更。 |

**预期结果**:
1. 本地栈健康检查通过。
2. 生产就绪门禁覆盖配置、凭据、数据库扩展、Web shell、核心列表和 GitLab 只读边界。
3. 任一门禁失败时不得宣称环境可发布。

**状态**: 已提供可执行生产就绪门禁脚本 `scripts/production_readiness_check.py`，`--rebuild` 模式会先执行 `docker compose up -d --build`，`--web-smoke` 模式会调用 `scripts/web_page_smoke.mjs` 通过真实浏览器登录并打开 `/welcome`、需求、迭代版本、Bug、任务、用户洞察、研发运营和角色管理等核心页面。脚本覆盖 Docker Compose、pgvector/pgcrypto、Redis、Web shell、核心管理列表、模型网关配置脱敏、真实页面非空/控制台健康和 GitLab 只读 preview/snapshot；健康检查读取持久化默认模型网关配置的回归见 `apps/api/tests/test_foundation.py`，发布门禁回归见 `apps/api/tests/test_production_readiness.py`；真实目标环境仍必须执行并通过脚本，不能以本地 API/Web 单元测试替代。

---

### TC-AIBRAIN-CONFIG-API-008: 产品、版本、模块和 Git 资源配置

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-CONFIG-API-008 |
| 用例名称 | 产品、迭代版本、模块和 Git 资源配置 |
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
| 2 | 在需求交付/迭代版本页面或 POST `/api/products/{product_id}/versions` 创建迭代版本 | 返回版本 ID，版本归属该产品。 |
| 3 | POST `/api/products/{product_id}/modules` 创建模块 | 返回模块 code，模块归属该产品。 |
| 4 | 在产品管理页面点击“配置”维护模块和 Git 资源，并进入需求交付/迭代版本页面维护版本 | 页面显示真实模块、Git 资源和迭代版本列表，新增后刷新真实 API 数据。 |
| 5 | POST `/api/products/{product_id}/git-repositories` 绑定内部 GitLab 只读资源 | 返回 repository_id 和 `credential_ref_configured`，不返回凭据引用或明文 token。 |
| 6 | GET `/api/products/{product_id}/versions?active_only=true` | 不返回 archived 版本。 |
| 7 | 使用 archived 版本排期需求或创建任务 | 返回 `PRODUCT_VERSION_ARCHIVED` 或 `VALIDATION_ERROR`。 |

**预期结果**:
1. 产品、迭代版本、模块、Git 资源可独立维护，迭代版本主入口位于需求交付菜单。
2. 新需求可暂不选择版本；排期和 AI 任务只能引用有效产品与 `planning`/`active` 迭代版本。
3. 写操作产生审计事件。
4. 页面列表只显示 Git 凭据“已配置/未配置”状态，不回显 `credential_ref`。
5. 产品 Git 仓库和相关系统端点只能分别由 `app.api.routers.product_git_repositories`、`app.api.routers.related_systems` 单一路由注册，避免回退到 `main.py`。

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

**状态**: 已自动化覆盖。配置 CRUD、密钥脱敏、provider 校验和模型日志见 `apps/api/tests/test_product_system_config.py`、`apps/api/tests/test_model_gateway.py` 与 `apps/api/tests/test_database_persistence.py`；`GET/POST/PATCH/DELETE/POST(test) /api/system/model-gateway-configs` 和 `GET /api/model-gateway/logs` 由 `app.api.routers.model_gateway` 单一路由注册，回归见 `apps/api/tests/test_router_boundaries.py::test_model_gateway_endpoints_are_owned_by_model_gateway_router`；前端配置表单见 `apps/web/tests/App.test.tsx::manages model gateway configs without exposing api keys`。

---

### TC-AIBRAIN-ASSISTANT-FUNC-027: AI 助手系统问答

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-ASSISTANT-FUNC-027 |
| 用例名称 | AI 助手系统问答 |
| 优先级 | P1 |
| 适用阶段 | MVP |
| 模块 | ASSISTANT |
| 创建人 | Codex |
| 创建日期 | 2026-06-02 |

**前置条件**:
1. 用户已登录，并具备 `admin`、`product_owner`、`rd_owner`、`reviewer` 或 `knowledge_owner` 角色。
2. 系统已配置 active/default OpenAI-compatible Chat 模型网关；该入口不要求 Embedding 可用。
3. 系统存在真实产品、需求、迭代版本、AI 任务、待确认 Review、Bug、代码评审报告、知识沉淀、Git 仓库或模型网关配置数据。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 进入 `/assistant` AI 助手页面 | 页面展示快速问题、上下文标签、聊天消息区和输入框。 |
| 2 | 点击“项目进展”或输入“AI Brain 项目现在开发到哪里了？” | 前端调用 `POST /api/assistant/chat`，请求包含用户问题和可选 conversation_id/product_id。 |
| 3 | 点击“阻塞与待确认”或输入“当前迭代有哪些阻塞需求、待确认 Review、代码评审结论和高风险 Bug？” | 前端复用助手聊天入口提交问题，页面保留当前会话上下文。 |
| 4 | 服务端处理助手请求 | 服务端生成脱敏 `system_context`，包含产品、迭代进度、需求数量、AI 任务数量、待确认 Review、阻塞需求、Bug 分布、高风险 Bug、最近代码评审结论、知识沉淀、Git 仓库和模型网关状态；同时根据用户问题生成 `reference_candidates`，覆盖产品、迭代、需求、任务、Review、Bug、代码评审报告和知识沉淀可跳转来源。 |
| 5 | 模型返回回答 | API 返回 assistant 消息、references、suggestions、model、latency_ms 和 conversation_id，页面渲染回答、来源链接和建议按钮；若模型未返回有效 references，服务端使用候选引用兜底。 |
| 6 | GET `/api/assistant/conversations` | 返回当前登录用户的最近对话，包含 conversation_id、标题、消息数和最后消息时间。 |
| 7 | GET `/api/assistant/conversations/{conversation_id}/messages` | 返回该会话的 user/assistant 消息，assistant 消息保留历史 references；其他用户读取同一 conversation_id 返回 404。 |
| 8 | GET `/api/model-gateway/logs?purpose=assistant_chat` | 返回助手模型调用元数据，包含 provider、model、tokens、latency、status 和 config_id，不包含完整用户问题、系统上下文、助手回答或 API Key。 |
| 9 | 模型网关未配置或调用失败 | API 返回 `MODEL_GATEWAY_CONFIG_INVALID` 或 `ASSISTANT_CHAT_FAILED`，页面展示错误消息并保留用户输入上下文。 |

**预期结果**:
1. AI 助手可以回答 AI Brain 系统配置、产品、迭代版本进度、需求、任务、待确认 Review、代码评审结论、Bug 分布、知识沉淀、Git 仓库和项目开发进展相关问题。
2. 助手聊天只依赖 Chat 模型网关，不因上游不支持 Embedding 而阻断。
3. 聊天历史按用户保存并隔离，前端可展示最近对话、打开历史消息并继续显示来源链接。
4. 模型日志和审计事件只记录脱敏元数据，不能保存完整 prompt、完整输出或密钥。

**状态**: 已自动化覆盖。后端系统上下文注入、迭代进度/阻塞/待确认/代码评审/Bug 分布摘要、引用候选生成、模型日志脱敏和助手审计见 `apps/api/tests/test_assistant_context_service.py` 与 `apps/api/tests/test_assistant_chat.py`；前端聊天页面、消息气泡、草案工具结果、运行诊断卡片、快速问题、来源链接、用户级会话历史和服务请求映射见 `apps/web/tests/AssistantPage.test.tsx`。

---

### TC-AIBRAIN-ASSISTANT-FUNC-027B: AI 助手草案任务台

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-ASSISTANT-FUNC-027B |
| 用例名称 | AI 助手草案任务台 |
| 优先级 | P0 |
| 适用阶段 | v1.1 |
| 模块 | ASSISTANT |
| 创建人 | Codex |
| 创建日期 | 2026-06-23 |

**前置条件**:
1. 用户已登录并具备 AI 助手访问权限。
2. 当前用户已有 `pending/confirmed/failed/cancelled/expired` 等状态的助手动作草案。
3. 至少一个草案包含查看次数、用户修改字段、预检问题或动作运行结果。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 进入 `/assistant/drafts` 草案任务台 | 页面调用 `GET /api/assistant/action-drafts`，PostgreSQL 运行态通过草案任务台 read model 按 `updated_at desc` 分页展示当前用户草案，不展示其它用户草案。 |
| 2 | 查看顶部汇总 | 展示待确认草案、失败草案、已采纳草案、采纳率、处理率和用户修改率。 |
| 3 | 按草案类型、状态、校验状态、关键词和创建时间筛选 | API 接收相同筛选参数并返回分页结果，列表不会前端拼装跨页数据。 |
| 4 | 点击某条草案“详情” | 页面调用 `POST /api/assistant/action-drafts/{draft_id}/view` 且 `surface=detail_modal`，弹窗展示 payload、校验问题、状态、风险和来源消息。 |
| 5 | 点击“继续编辑” | 跳转 `/assistant?draft_id=<draft_id>`，复用助手深链加载草案。 |
| 6 | 对 pending 草案点击确认或取消 | 页面调用对应 confirm/cancel API，完成后刷新任务台；终态草案不展示确认或取消入口。 |

**预期结果**:
1. 草案任务台是用户级 read model，PostgreSQL 运行态不得读取当前用户全量草案后再分页，不从聊天历史或前端本地缓存拼装主列表。
2. 查看详情、确认、取消仍复用草案生命周期接口并写入审计。
3. 列表 summary 与行字段能支撑草案采纳率、处理率、用户修改率和来源链路追踪。

**状态**: 已自动化覆盖。后端列表、筛选、用户隔离、过期刷新和 summary 见 `apps/api/tests/test_assistant_draft_workbench.py`；前端页面指标、详情弹窗和继续编辑入口见 `apps/web/tests/AssistantDraftsPage.test.tsx`。真实页面 smoke 应覆盖 `/assistant/drafts` 非空渲染和无控制台错误。

---
