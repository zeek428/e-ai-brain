# 需求交付与任务管理测试用例

> 来源：../test-case.md。该文件按业务域承接详细测试用例，主入口保留索引与通用规范。

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
2. 系统至少存在产品、需求、AI 任务、知识文档和审计基础数据；Bug 管理、用户反馈、用户使用指标和迭代规划建议可加载真实列表或真实空列表，研发运营看板在 MVP 可没有业务数据。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 进入首页 IT 团队看板 | MVP 可展示需求、研发进展、知识沉淀和审计摘要；尚未接入真实采集器的线上系统健康和发布能力展示空状态或禁用态；GitLab 每日指标、用户使用指标、用户反馈和迭代规划建议来自真实结构表，不返回示例数据或伪造统计。 |
| 2 | 进入产品管理 | 可以查看和维护产品、版本、模块和 Git 资源。 |
| 3 | 进入需求管理 | 可以查看需求列表、需求详情和审批状态。 |
| 4 | 进入任务中心 | 可以查看 AI 任务列表；任务类型展示业务中文标签；列表行内仅展示单一“操作”入口，启动产品详细设计任务、确认 Review 输出、从已确认产品详细设计创建技术方案任务、对已完成技术方案执行 Markdown 导出等动作均在上方摘要、下方纵向操作的任务操作弹窗中完成。 |
| 5 | 进入 Bug 管理 | v1.1 可展示真实 Bug 列表、权限校验和真实空列表；登记、分派、验证、关闭和重复归并按 TC-AIBRAIN-BUG-FUNC-018 验收。 |
| 6 | 进入研发运营看板 | MVP 可展示真实接口空状态；GitLab、Jenkins 与线上日志支持真实登记/导入和查询，外部自动采集和完整下钻按 v1.2 验收。 |
| 7 | 进入用户洞察 | MVP 可展示真实用户反馈、用户使用指标和迭代规划建议列表；无反馈/Bug 证据时生成建议返回真实空集合；无使用指标时返回真实空集合。 |
| 8 | 进入知识中心 | 可以查看知识文档、检索、索引状态和沉淀审核。 |
| 9 | 进入审计与运行 | 可以查看审计事件、运行记录、健康检查和失败排查信息。 |

**预期结果**:
1. 产品、需求、AI 任务、知识中心和审计与运行在 MVP 可独立查看或维护。
2. Bug 管理、用户反馈、用户使用指标和迭代规划建议使用真实 API 或真实空列表；研发运营看板等后续阶段入口在 MVP 不误导为已完成能力，不返回示例数据或占位统计。
3. 用户不需要进入 AI 任务详情页才能维护产品、需求、知识或查看审计运行信息。

**状态**: 已自动化覆盖。管理入口、真实空状态和无本地示例行见 `apps/web/tests/App.test.tsx::renders management modules as query filters with table lists`、`apps/web/tests/App.test.tsx::renders dashboard and operation pages without placeholder data`、`apps/web/tests/App.test.tsx::shows backend load failures without local example rows`；外部采集器完整闭环仍按后续用例推进。

---

### TC-AIBRAIN-FLOW-FUNC-010B: 提交前真实网页界面验证门禁

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-FLOW-FUNC-010B |
| 用例名称 | 提交前真实网页界面验证门禁 |
| 优先级 | P0 |
| 适用阶段 | MVP |
| 模块 | FLOW |
| 创建人 | Codex |
| 创建日期 | 2026-06-04 |

**前置条件**:
1. 本次改动影响前端页面、菜单、路由、可见文案、表格字段、弹窗交互、前端服务层，或影响页面展示的后端 API。
2. API 以 PostgreSQL 运行时启动，前端服务已启动或可重启。
3. 测试人员具备目标页面所需登录角色。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 运行与改动范围匹配的自动化测试，例如前端 `npm test`、`npm run lint`、`npm run typecheck` 或后端 `uv run pytest` | 自动化测试通过；失败项不得跳过后直接进入提交。 |
| 2 | 启动或重启真实 Web 服务，访问目标 URL | 页面从当前代码重新编译和加载；如果端口漂移、旧 bundle 或缓存错误导致页面异常，必须修复后复测。 |
| 3 | 使用浏览器登录目标角色并打开目标页面 | URL 和页面标题符合预期；页面不是空白壳，没有框架错误覆盖层。 |
| 4 | 验证本次改动对应的菜单、标题、表格字段、筛选、按钮、弹窗、空状态或主流程交互 | 新状态可见且符合需求；旧文案、旧交互或本地示例数据不再出现。 |
| 5 | 检查浏览器控制台错误和页面加载状态 | 无本次变更引入的错误；已有环境噪声需要说明，不得影响目标页面渲染和交互。 |
| 6 | 在提交说明或验收记录中写明 URL、角色、验证页面、关键交互、自动化命令和网页验证结果 | 形成可追溯证据；实际网页验证未通过不得提交代码。 |

**预期结果**:
1. 所有用户可见改动都经过真实网页界面验证，而不是只通过单元测试或接口测试推断。
2. 发现旧前端服务、旧缓存、端口漂移、页面空白或运行时错误时，先修复运行环境并复测。
3. 代码提交发生在自动化测试和真实网页验证均通过之后。

**状态**: 作为提交前门禁执行。2026-06-04 用户洞察菜单命名调整回归中，曾发现前端未重启、端口漂移和 MFSU 缓存导致页面未更新；清理缓存、重启 `http://127.0.0.1:5173` 后，通过浏览器验证 `/governance/insights` 页面标题为“用户洞察 - Enterprise AI Brain”，菜单项为“用户洞察”，旧“用户洞察/迭代规划”不再出现。同日日期/时间登记控件回归要求覆盖迭代版本、产品配置版本、用户洞察使用指标、研发运营 GitLab 指标、Jenkins 发布、线上日志和采集运行弹窗，确认相关字段使用 Ant Design DatePicker 而非普通文本输入。

---

### TC-AIBRAIN-FLOW-API-010C: 管理主列表服务端分页、排序和筛选

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-FLOW-API-010C |
| 用例名称 | 管理主列表服务端分页、排序和筛选 |
| 优先级 | P0 |
| 适用阶段 | MVP |
| 模块 | FLOW |
| 创建人 | Codex |
| 创建日期 | 2026-06-04 |

**前置条件**:
1. 已存在产品、需求、迭代版本、Bug、任务、知识、审计、研发运营指标和用户洞察数据。
2. 用户具备对应页面读取权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 调用 `GET /api/products`、`/api/requirements`、`/api/product-versions`、`/api/bugs`、`/api/ai-tasks`、`/api/knowledge/documents`、`/api/audit/events`，携带 `page/page_size/sort_by/sort_order` 和业务筛选条件。 | 响应包含 `items/total/page/page_size`，排序和筛选由服务端完成；核心管理列表额外返回 `query/performance` 元数据，记录 `query.name`、生效查询、接口耗时、当前页返回条数、总数、`p95_target_ms` 和慢查询标记；PostgreSQL 运行时 `/api/products`、`/api/product-versions`、`/api/requirements` 和 `/api/bugs` 均通过各自 SQL read model 完成筛选、排序和分页，不加载全量集合后本地切片；非法 `sort_by` 返回 `VALIDATION_ERROR`。 |
| 2 | 调用 `GET /api/devops/operational-metrics?category=Jenkins 发布&name=deploy&status=success&page=1&page_size=1&sort_by=updated_at&sort_order=desc`。 | PostgreSQL 运行时通过 repository SQL read model 返回研发运营聚合行，在 SQL 层完成 GitLab/Jenkins/线上日志统一投影、筛选、排序和分页，前端研发运营主表无需三接口本地拼装。 |
| 3 | 调用 `GET /api/insights/items?category=用户反馈&summary=迭代版本&status=open&page=1&page_size=1&sort_by=updated_at&sort_order=desc`。 | 返回用户洞察聚合行，来源于使用趋势、用户反馈和迭代建议统一投影；PostgreSQL 运行时通过 SQL read model 完成筛选、排序和分页，前端用户洞察主表无需三接口本地拼装。 |
| 4 | 打开产品、需求、迭代版本、Bug、任务、知识、审计、研发运营和用户洞察页面，执行查询、分页和表头排序。 | 页面请求携带后端分页、排序和筛选参数；主表不再先拉全量数据后本地过滤。 |
| 5 | 渲染使用 `ManagementListPage` 的管理主表，检查未显式配置宽度的普通列、自定义渲染列和操作列。 | 表格默认 `tableLayout=fixed`、`scroll.x=max-content`；普通列和自定义渲染列默认具备 160px 稳定宽度；自定义渲染列内的 Tag、Space、Typography 和状态摘要组合被稳定单元格容器约束并省略；操作列默认右侧固定且宽度为 220px，页面可按业务场景显式覆盖。 |

**预期结果**:
1. 管理主列表统一由服务端承载分页、排序和筛选；核心列表返回 `query/performance` 元数据用于慢页面诊断，`requirements/ai_tasks/bugs` 的 `p95_target_ms` 为 300ms，`user_insights` 为 400ms，`devops_operational_metrics` 为 500ms，超过阈值时后端记录包含 `p95_target_ms` 的 `slow_list_query` 日志。
2. 用户洞察调用 `/api/insights/items`，研发运营调用 `/api/devops/operational-metrics`，两者在 PostgreSQL 运行时均使用 SQL read model 聚合查询。
3. 前端管理主列表默认具备横向滚动、普通列稳定宽度、长文本省略和右侧固定操作列，避免角色、用户洞察、DevOps、任务和 Bug 等宽表页面因内容变长而挤压变形。
4. 子表、低数据量配置表和团队看板等汇总视图可暂保留独立接口或 Python 聚合，但不得作为管理主列表的多接口聚合替代。

**状态**: 已自动化覆盖核心后端和前端契约。后端见 `apps/api/tests/test_product_system_config.py`、`apps/api/tests/test_requirement_lifecycle.py::test_management_lists_include_query_observability_metadata`、`apps/api/tests/test_bug_management.py`、`apps/api/tests/test_api_contract_completion.py`、`apps/api/tests/test_devops_gitlab_metrics.py`、`apps/api/tests/test_user_feedback.py`、`apps/api/tests/test_database_persistence.py::test_product_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_database_persistence.py::test_product_version_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_database_persistence.py::test_requirement_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_database_persistence.py::test_bug_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_database_persistence.py::test_insight_items_use_repository_read_model_for_sql_pagination` 和 `apps/api/tests/test_database_persistence.py::test_operational_metrics_use_repository_read_model_for_sql_pagination`；前端见 `apps/web/tests/App.test.tsx` 中管理表格默认规范、研发运营和用户洞察页面回归。

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
1. 存在启用产品和 `planning` 或 `active` 迭代版本。
2. 存在状态为 `planned` 的已排期需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/requirements/{id}/generate-task` | 返回 task_id，需求状态变为 `designing`。 |
| 2 | PATCH 产品、版本或模块名称 | 产品配置更新成功。 |
| 3 | GET `/api/ai-tasks/{task_id}` | 返回生成时的 `requirement_snapshot` 和 `product_context`，不被后续配置修改覆盖。 |
| 4 | GET `/api/requirements/{id}` | 需求仍保留原始输入、审批结论和任务引用。 |

**预期结果**:
1. 需求是业务审批对象，任务是 AI 执行对象。
2. 历史任务解释依赖生成时快照，而不是实时主数据。

**状态**: 已自动化覆盖。需求审批、任务生成、快照保留和后续任务引用见 `apps/api/tests/test_requirement_lifecycle.py`、`apps/api/tests/test_api_contract_completion.py::test_brain_apps_and_task_list_contracts_are_available` 与 `apps/api/tests/test_technical_solution_export.py`。

---

### TC-AIBRAIN-REQ-FUNC-011C: 新增需求可不指定迭代版本并后续排期

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011C |
| 用例名称 | 新增需求可不指定迭代版本并后续排期 |
| 优先级 | P0 |
| 模块 | REQUIREMENT |
| 创建人 | Codex |
| 创建日期 | 2026-06-03 |

**前置条件**:
1. 用户已登录并具备需求创建、审批和任务生成权限。
2. 系统存在启用产品和同产品 `planning` 或 `active` 迭代版本。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/requirements`，只传产品、不传 `version_id` | 需求创建成功，状态为 `submitted`，`version_id=null`。 |
| 2 | POST `/api/requirements/{id}/approve` | 需求进入 `approved` 需求池，仍未排期。 |
| 3 | POST `/api/requirements/{id}/generate-task` | 返回 `409 REQUIREMENT_STATE_INVALID`，提示只能对已排期需求生成任务。 |
| 4 | PATCH `/api/requirements/{id}`，补充 `planning` 或 `active` `version_id` | 需求进入 `planned`，可在需求列表看到迭代版本名称。 |
| 5 | POST `/api/requirements/{id}/generate-task` | 返回 draft 产品详细设计任务，需求状态进入 `designing` 并追加 `task_ids`。 |

**预期结果**:
1. 需求池和迭代排期解耦，新增需求阶段不强迫选择版本。
2. 只有已排期需求能进入 AI 任务交付，避免任务缺少版本上下文。

**状态**: 已自动化覆盖。见 `apps/api/tests/test_requirement_lifecycle.py::test_requirement_can_start_in_backlog_and_be_planned_into_iteration_version` 与 `apps/web/tests/App.test.tsx` 路由/表单用例。

---

### TC-AIBRAIN-REQ-FUNC-011E: 多需求批量排期和迭代版本归集

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011E |
| 用例名称 | 多需求批量排期和迭代版本归集 |
| 优先级 | P0 |
| 模块 | REQUIREMENT |
| 创建人 | Codex |
| 创建日期 | 2026-06-04 |

**前置条件**:
1. 用户已登录并具备产品负责人、研发负责人或管理员角色。
2. 系统存在启用产品、同产品 `planning`/`active`/`testing`/`released`/`archived` 迭代版本、至少一条 `approved` 需求池需求和一条 `planned` 已排期需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在需求管理勾选同产品 `approved/planned` 需求，点击“批量排期”，选择目标版本并确认 | 目标版本下拉仅展示 `planning`/`active` 版本并过滤 `testing`、`released` 和 `archived`；前端只发送一次 `POST /api/requirements/batch-schedule`，请求体包含产品、目标版本、需求 ID 列表和归集原因。 |
| 2 | 在迭代版本页面点击目标版本行“归集需求”，勾选可归集需求并确认 | 前端复用同一个批量接口，目标产品和版本由版本行透传。 |
| 3 | 通过 API 混入 `submitted`、跨产品或重复需求 ID | 合法需求进入 `updated`，不合规需求进入 `skipped` 并返回稳定 code。 |
| 4 | 查询需求列表和审计列表 | 已更新需求状态为 `planned` 且版本为目标版本；审计包含追加保存的 `requirement.batch_scheduled` 和每条更新需求的 `requirement.updated`，payload 带 `batch_id`，历史批次审计不被覆盖删除。 |

**预期结果**:
1. 多需求可快速手动归集到一个产品迭代版本，不需要逐条编辑。
2. 批量操作不影响已进入交付阶段的需求，并保留可追溯审计。

**状态**: 已自动化覆盖。见 `apps/api/tests/test_requirement_batch_schedule.py` 与 `apps/web/tests/App.test.tsx` 中批量排期页面用例。

---

### TC-AIBRAIN-REQ-FUNC-011F: 多需求批量生成任务

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011F |
| 用例名称 | 多需求批量生成任务 |
| 优先级 | P0 |
| 模块 | REQUIREMENT / AI_TASK |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备产品负责人、研发负责人或管理员角色。
2. 系统存在启用产品、同产品至少两条 `planned` 已排期需求、一条 `approved` 需求池需求，以及可选跨产品需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在需求管理勾选同产品 `planned` 需求，点击“批量生成任务” | 弹窗展示将为已排期需求生成产品详细设计任务；若勾选不同产品或无可生成需求，页面给出阻断提示。 |
| 2 | 输入生成原因并确认 | 前端只发送一次 `POST /api/requirements/batch-generate-tasks`，请求体包含产品 ID、需求 ID 列表和 reason。 |
| 3 | 通过 API 混入 `approved` 需求池、跨产品需求和重复需求 ID | 合法 `planned` 需求进入 `generated`，不合规需求进入 `skipped`，code 分别稳定返回 `REQUIREMENT_STATE_INVALID`、`PRODUCT_MISMATCH` 或 `DUPLICATE_REQUIREMENT`。 |
| 4 | 查询需求列表、AI 任务列表和审计列表 | 已生成任务为 draft `product_detail_design`；对应需求 `task_ids` 追加任务 ID 并进入 `designing`；审计包含 `requirement.batch_tasks_generated` 和每个任务的 `ai_task.created`，payload 带 `batch_id` 与 reason。 |

**预期结果**:
1. 需求排期后可批量进入产品详细设计阶段，减少逐条点击生成任务的操作成本。
2. 部分失败不影响合法需求生成任务，并保留批次级与任务级审计。

**状态**: 已自动化覆盖。见 `apps/api/tests/test_requirement_batch_schedule.py::test_batch_generate_tasks_creates_tasks_for_planned_requirements_and_records_audit` 与 `apps/web/tests/App.test.tsx` 中批量生成任务页面用例。

---

### TC-AIBRAIN-REQ-FUNC-011G: 多需求批量分配负责人

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011G |
| 用例名称 | 多需求批量分配负责人 |
| 优先级 | P1 |
| 模块 | REQUIREMENT |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备产品负责人、研发负责人或管理员角色。
2. 系统存在至少两条非关闭需求、一条已关闭需求，以及可选重复或不存在需求 ID。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在需求管理勾选多条非关闭需求，点击“批量分配负责人” | 弹窗展示负责人和分配原因输入框；前端只发送一次 `POST /api/requirements/batch-assign-owner`。 |
| 2 | 输入负责人和原因并确认 | 请求体包含 `assignee`、`requirement_ids` 和 reason；合法需求 `assignee` 更新，原状态不变化。 |
| 3 | 通过 API 混入已关闭需求、重复需求 ID 和不存在需求 ID | 合法需求进入 `updated`，已关闭/已取消需求返回 `REQUIREMENT_STATE_INVALID`，重复需求返回 `DUPLICATE_REQUIREMENT`，不存在需求返回 `NOT_FOUND`。 |
| 4 | 查询需求详情和审计列表 | 需求详情返回新的 `assignee`；审计包含批次级 `requirement.batch_owner_assigned` 和逐条 `requirement.updated`，payload 带 `batch_id`、`from_assignee`、`assignee` 和 reason。 |

**预期结果**:
1. 需求负责人可批量调整，不需要逐条编辑需求。
2. 批量分配不改变需求研发状态，并保留可追溯审计。

**状态**: 已自动化覆盖。见 `apps/api/tests/test_requirement_batch_schedule.py::test_batch_assign_owner_updates_requirements_and_records_audit` 与 `apps/web/tests/App.test.tsx` 中需求管理批量分配负责人页面用例。

---

### TC-AIBRAIN-REQ-FUNC-011H: 多需求批量推进状态

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011H |
| 用例名称 | 多需求批量推进状态 |
| 优先级 | P1 |
| 模块 | REQUIREMENT |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备产品负责人、研发负责人或管理员角色。
2. 系统存在至少一条已归属迭代版本且可从当前状态推进到目标状态的需求、一条未排期需求，以及一条终态或不符合路径的需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在需求管理勾选多条需求，点击“批量推进状态” | 弹窗展示目标状态和推进原因输入框；前端只发送一次 `POST /api/requirements/batch-advance-status`。 |
| 2 | 选择目标状态并确认 | 请求体包含 `target_status`、`requirement_ids` 和 reason；合法需求状态更新为目标状态。 |
| 3 | 通过 API 混入未排期需求、不符合路径需求、重复需求 ID 和不存在需求 ID | 合法需求进入 `updated`；未排期需求返回 `REQUIREMENT_VERSION_REQUIRED`；不符合路径需求返回 `REQUIREMENT_STATE_INVALID`；重复需求返回 `DUPLICATE_REQUIREMENT`；不存在需求返回 `NOT_FOUND`；前端结果弹窗展示批次号、成功数、跳过数和 skipped 原因。 |
| 4 | 查询需求详情和审计列表 | 需求详情返回目标状态；审计包含批次级 `requirement.batch_status_advanced` 和逐条 `requirement.updated`，payload 带 `batch_id`、`from_status`、`to_status` 和 reason。 |

**预期结果**:
1. 需求可按研发流程批量前进，减少逐条编辑成本。
2. 批量推进不会绕过状态机或迭代版本归属要求，不符合路径或未排期的需求只跳过，不影响合法项。

**状态**: 已自动化覆盖。见 `apps/api/tests/test_requirement_batch_schedule.py::test_batch_advance_status_updates_valid_requirements_and_records_audit` 与 `apps/web/tests/App.test.tsx` 中需求管理批量推进状态页面用例。

---

### TC-AIBRAIN-TASK-FUNC-020C: 任务管理批量取消

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-020C |
| 用例名称 | 任务管理批量取消 |
| 优先级 | P1 |
| 模块 | AI_TASK |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备研发负责人或管理员角色。
2. 系统存在至少一条可取消任务和一条已完成或已失败的终态任务。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在任务管理勾选可取消任务，点击“批量取消” | 前端只发送一次 `POST /api/ai-tasks/batch-cancel`，请求体包含 `task_ids` 和批量取消原因。 |
| 2 | 通过 API 混入终态任务、重复任务 ID 和不存在任务 ID | 合法任务进入 `updated` 并变为 `cancelled`；终态、重复和不存在任务进入 `skipped`，code 分别稳定返回 `TASK_STATE_INVALID`、`DUPLICATE_TASK` 和 `NOT_FOUND`；前端结果弹窗展示批次号、取消数、跳过数和 skipped 原因。 |
| 3 | 查询任务详情、待确认 Review 和审计列表 | 已取消任务状态为 `cancelled`，待处理 Review 被取消；审计包含批次级 `ai_task.batch_cancelled` 和逐任务 `ai_task.cancelled`，payload 带 `batch_id` 与 reason。 |

**预期结果**:
1. 任务管理可一次取消多条未完成任务，减少逐条进入操作弹窗的成本。
2. 部分失败不影响合法任务取消，并保留批次级与任务级审计。

**状态**: 已自动化覆盖。见 `apps/api/tests/test_api_contract_completion.py::test_ai_task_batch_cancel_updates_valid_tasks_and_skips_terminal_tasks` 与 `apps/web/tests/App.test.tsx` 中任务管理批量取消页面用例；handler 防回退见 `apps/api/tests/test_router_boundaries.py::test_ai_task_batch_cancel_handler_does_not_call_legacy_main`。

---

### TC-AIBRAIN-TASK-FUNC-020D: 任务管理批量重试

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-020D |
| 用例名称 | 任务管理批量重试 |
| 优先级 | P1 |
| 模块 | AI_TASK |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备研发负责人、评审人或管理员角色。
2. 系统存在至少一条 `failed` 且 `current_step=model_gateway_failed` 或 `code_review_executor_failed` 的失败任务。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在任务管理勾选可重试失败任务，点击“批量重试” | 前端只发送一次 `POST /api/ai-tasks/batch-retry`，请求体包含 `task_ids` 和批量重试原因。 |
| 2 | 通过 API 混入已完成任务、重复任务 ID 和不存在任务 ID | 可重试失败任务复用 `/start` 状态机进入 `waiting_review` 并返回 `updated`；仍失败任务保留在 `retried` 并携带错误码和错误信息；终态、重复和不存在任务进入 `skipped`，code 分别稳定返回 `TASK_STATE_INVALID`、`DUPLICATE_TASK` 和 `NOT_FOUND`；前端结果弹窗展示批次号、重试数、成功数、仍失败数、错误信息和 skipped 原因。 |
| 3 | 查询任务详情、待确认 Review 和审计列表 | 已重试成功任务保留原 task id，新增待确认 Review；审计包含批次级 `ai_task.batch_retried` 和逐任务 `ai_task.retry_started`。 |

**预期结果**:
1. 模型网关或代码评审执行器恢复后，可批量恢复失败任务，避免为同一阶段复制新任务。
2. 批量重试部分失败不阻塞其他合法任务，响应能区分 `retried`、`updated` 和 `skipped`。

**状态**: 已自动化覆盖。见 `apps/api/tests/test_api_contract_completion.py::test_ai_task_batch_retry_restarts_retryable_failed_tasks_and_skips_invalid_items` 与 `apps/web/tests/App.test.tsx` 中任务管理批量重试页面用例。

---

### TC-AIBRAIN-CONFIG-FUNC-008D: 迭代版本状态推进和需求状态同步

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-CONFIG-FUNC-008D |
| 用例名称 | 迭代版本状态推进和需求状态同步 |
| 优先级 | P0 |
| 模块 | PRODUCT_CONFIG / REQUIREMENT |
| 创建人 | Codex |
| 创建日期 | 2026-06-04 |

**前置条件**:
1. 用户已登录并具备产品负责人、研发负责人或管理员角色。
2. 系统存在 `planning`、`active`、`testing` 迭代版本，以及同版本内 `approved/planned/ready_for_dev/designing/developing/code_reviewing/testing/ready_for_release` 等不同状态需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在迭代版本页对 `planning` 版本点击“推进状态”，生成影响预览后确认推进到 `active` | 预览展示将推进的需求；确认后版本状态为 `active`，`approved/planned` 需求同步变为 `ready_for_dev`，记录版本推进和逐需求审计。 |
| 2 | 对 `active` 版本推进到 `testing`，版本内混有 `planned/ready_for_dev/designing/developing/code_reviewing` 需求 | 预览展示这些已进入交付链路的需求均将同步为 `testing`；确认后版本进入 `testing`，上述需求状态全部为 `testing`，并记录版本推进和逐需求审计。 |
| 3 | 对 `testing` 版本推进到 `released`，版本内仍有 `developing` 需求 | 即使提交 `force=true` 也返回 `PRODUCT_VERSION_STATUS_BLOCKED`；处理未完成需求为 `deferred/cancelled/closed` 后，`testing/ready_for_release` 自动推进为 `released`。 |
| 4 | 对 `released` 版本归档为 `archived` | `released/accepted/deferred/cancelled/closed/rejected` 需求保持不变；未完成需求作为归档风险项。 |
| 5 | 直接 PATCH 版本 `status` | 返回 `PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED`，不能绕过影响预览和需求同步逻辑。 |
| 6 | 对 `testing` 版本点击“查看需求” | “归集需求”保持禁用，但只读需求清单可打开，且只展示当前版本下的需求。 |
| 7 | 打开真实迭代版本页面 | “推进状态”入口可见，弹窗可生成影响预览，“查看需求”可回看当前版本需求，页面无空白、无框架错误覆盖层、无相关控制台错误。 |

**状态**: 已自动化覆盖。版本状态机 service 层单测见 `apps/api/tests/test_version_status_service.py`，接口行为见 `apps/api/tests/test_iteration_version_status_flow.py`，页面用例见 `apps/web/tests/App.test.tsx`；真实网页验证作为提交前门禁执行。

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
| 1 | POST `/api/knowledge/documents` | 文档创建成功；Embedding 可用时进入 `vector_indexed`，不可用但文本切片成功时进入 `text_indexed`。 |
| 2 | GET `/api/knowledge/documents?index_status=text_indexed` 或 `vector_indexed` | 可按索引状态查询。 |
| 3 | POST `/api/knowledge/search` | 仅返回有权限的知识结果；文本兜底结果 `retrieval_mode=keyword`，向量结果 `retrieval_mode=vector`。 |
| 4 | 审核知识沉淀候选 | 可批准或拒绝，状态正确流转。 |
| 5 | 模拟 Embedding 不可用后调用 `POST /api/knowledge/documents/{document_id}/retry-index` | 文档先保持 `text_indexed` 且关键词检索可用；Embedding 恢复后重试升级为 `vector_indexed`。 |

**预期结果**:
1. 知识中心不依赖 AI 任务完成也可以主动导入和检索。
2. 知识沉淀必须审核后才能进入正式知识库。

**状态**: 已自动化覆盖。知识导入、索引、检索、沉淀审核和失败重试见 `apps/api/tests/test_knowledge_governance.py` 与 `apps/web/tests/KnowledgePage.test.tsx` 知识中心用例。

---

### TC-AIBRAIN-KNOWLEDGE-FUNC-012B: 知识空间目录和资产导入

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-KNOWLEDGE-FUNC-012B |
| 用例名称 | 知识空间目录和资产导入 |
| 优先级 | P0 |
| 模块 | KNOWLEDGE |
| 创建人 | Codex |
| 创建日期 | 2026-06-10 |

**前置条件**:
1. 知识维护者已登录。
2. API 以 PostgreSQL 运行时启动，配置 MinIO 或 S3-compatible 对象存储。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/knowledge/spaces` 创建知识空间 | 返回空间 ID，记录空间创建审计。 |
| 2 | POST `/api/knowledge/spaces/{space_id}/folders` 创建目录 | 返回目录 ID 和路径，目录归属空间。 |
| 3 | POST `/api/knowledge/documents/upload` 上传 Markdown 文件 | 文件写入对象存储，结构表写入 `knowledge_assets`、`knowledge_import_jobs`、`knowledge_chunk_sets`、`knowledge_documents` 和 `knowledge_chunks`。 |
| 4 | GET `/api/knowledge/documents?knowledge_space_id=...&folder_id=...` | 返回上传文档，包含 `source_asset_id`、`active_chunk_set_id` 和目录信息。 |
| 5 | POST `/api/knowledge/search` 并传 `knowledge_space_id` | 只返回当前空间可读结果，source 包含 `asset_id`、`chunk_set_id`、`folder_id` 和 `knowledge_space_id`。 |
| 6 | GET `/api/knowledge/assets/{asset_id}/preview` | 通过 API 鉴权返回文本预览，不暴露永久对象存储 URL。 |
| 7 | 使用非空间成员重复列表、检索和预览 | 返回空结果或 403，不泄露空间文档、chunk 或资产内容。 |

**预期结果**:
1. 知识空间是权限边界，目录是组织结构，资产存储只承载原始文件和解析产物。
2. PostgreSQL 仍是业务事实源，MinIO/S3 仅作为对象存储层。
3. 前端知识中心支持空间筛选、目录选择、新建空间/目录和文件上传。

**状态**: 已自动化覆盖。后端见 `apps/api/tests/test_knowledge_space_assets.py`、`apps/api/tests/test_knowledge_management_foundation.py` 和 `apps/api/tests/test_persistence_repository_boundaries.py`；前端见 `apps/web/tests/KnowledgePage.test.tsx`。

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
| 4 | GET `/api/audit/events?actor_id={user_id}&created_from={start}&created_to={end}` | 只返回该操作者在时间范围内的审计事件。 |
| 5 | 在审计与运行列表点击“详情” | 弹窗展示事件类型、主体、AI 任务、操作者、发生时间和 payload。 |
| 6 | 在审计与运行列表点击“链路追踪” | 优先以审计主体查询生命周期上下游、风险信号和缺失上下文。 |
| 7 | 使用无权限用户查询主体审计事件 | 返回 403 或空结果，不泄露主体存在性。 |
| 8 | 使用不存在的 subject_id 查询 | 返回空列表，不报 500。 |

**预期结果**:
1. 审计事件可按主体类型、主体 ID、操作者和创建时间范围过滤。
2. 审计详情和链路追踪均从真实接口数据渲染，不展示兜底示例数据。
3. 主体级查询遵守同一权限边界。
4. 无结果和无权限场景语义明确。

**状态**: 已自动化覆盖。主体、操作者、时间过滤见 `apps/api/tests/test_security_boundaries.py::test_audit_events_filter_by_actor_and_time_range`，审计列表 repository-first 读路径和运行态 store 过期回归见 `apps/api/tests/test_database_persistence.py::test_audit_event_list_uses_repository_when_runtime_store_is_stale`，审计详情和生命周期追踪入口见 `apps/web/tests/App.test.tsx::opens real audit detail and lifecycle trace actions from audit rows`。

---
