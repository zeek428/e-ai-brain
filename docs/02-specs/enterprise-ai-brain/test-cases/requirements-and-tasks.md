# 需求交付与研发任务测试用例

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
| 4 | 进入任务中心 | 可以只读查看协作工作项产生的 AI 任务、任务类型、结果和 Review；不提供直接创建或启动入口。协作推进、工作项审核/返工和人工决策从研发协同工作台处理，已完成任务仍可按权限导出 Markdown。 |
| 5 | 进入 Bug 管理 | v1.1 可展示真实 Bug 列表、权限校验和真实空列表；登记、分派、验证、关闭和重复归并按 TC-AIBRAIN-BUG-FUNC-018 验收。 |
| 6 | 进入研发运营看板 | MVP 可展示真实接口空状态；GitLab、运维部署、Jenkins 与线上日志支持真实登记/导入和查询，外部自动采集和完整下钻按 v1.2 验收。 |
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
| 1 | 调用 `GET /api/products`、`/api/requirements`、`/api/product-versions`、`/api/bugs`、`/api/ai-tasks`、`/api/knowledge/documents`、`/api/audit/events`，携带 `page/page_size/sort_by/sort_order` 和业务筛选条件。 | 响应包含 `items/total/page/page_size`，排序和筛选由服务端完成；核心管理列表额外返回 `query/performance` 元数据，记录 `query.name`、生效查询、接口耗时、当前页返回条数、总数、`p95_target_ms` 和慢查询标记；PostgreSQL 运行时 `/api/products`、`/api/product-versions`、`/api/requirements` 和 `/api/bugs` 均通过各自 SQL read model 完成筛选、排序和分页，不加载全量集合后本地切片；需求、Bug、知识中心和代码巡检列表必须分别校验 `requirement.read`、`bug.read`、`knowledge.read`、`code_inspection.read`，需求/Bug/代码巡检列表还必须在服务端按当前用户产品 scope 过滤并下推到 read model；非法 `sort_by` 返回 `VALIDATION_ERROR`。 |
| 2 | 调用 `GET /api/devops/operational-metrics?category=Jenkins 发布&name=deploy&status=success&page=1&page_size=1&sort_by=updated_at&sort_order=desc`。 | PostgreSQL 运行时通过 repository SQL read model 返回研发运营聚合行，在 SQL 层完成 GitLab/Jenkins/线上日志统一投影、筛选、排序和分页，前端研发运营主表无需三接口本地拼装。 |
| 3 | 调用 `GET /api/insights/items?category=用户反馈&summary=迭代版本&status=open&page=1&page_size=1&sort_by=updated_at&sort_order=desc`。 | 返回用户洞察聚合行，来源于使用趋势、用户反馈和迭代建议统一投影；PostgreSQL 运行时通过 SQL read model 完成筛选、排序和分页，前端用户洞察主表无需三接口本地拼装。 |
| 4 | 打开产品、需求、迭代版本、Bug、任务、知识、审计、研发运营和用户洞察页面，执行查询、分页和表头排序。 | 页面请求携带后端分页、排序和筛选参数；主表不再先拉全量数据后本地过滤。 |
| 5 | 渲染使用 `ManagementListPage` 的管理主表，检查未显式配置宽度的普通列、自定义渲染列和操作列。 | 表格默认 `tableLayout=fixed`、`scroll.x=max-content`；普通列和自定义渲染列默认具备 160px 稳定宽度；自定义渲染列内的 Tag、Space、Typography 和状态摘要组合被稳定单元格容器约束并省略；操作列默认右侧固定且宽度为 220px，页面可按业务场景显式覆盖。 |

**预期结果**:
1. 管理主列表统一由服务端承载分页、排序和筛选；核心列表返回 `query/performance` 元数据用于慢页面诊断，`requirements/ai_tasks/bugs` 的 `p95_target_ms` 为 300ms，`user_insights` 为 400ms，`devops_operational_metrics` 为 500ms，超过阈值时后端记录包含 `p95_target_ms` 的 `slow_list_query` 日志。
2. 用户洞察调用 `/api/insights/items`，研发运营调用 `/api/devops/operational-metrics`，两者在 PostgreSQL 运行时均使用 SQL read model 聚合查询。
3. 菜单声明的读取权限必须与后端列表接口保持一致；无 read 权限用户访问需求、Bug、知识中心或代码巡检列表返回 403，具备产品范围的业务用户只能读取范围内需求、Bug 和代码巡检记录。
4. 前端管理主列表默认具备横向滚动、普通列稳定宽度、长文本省略和右侧固定操作列，避免角色、用户洞察、DevOps、任务和 Bug 等宽表页面因内容变长而挤压变形。
5. 子表、低数据量配置表和团队看板等汇总视图可暂保留独立接口或 Python 聚合，但不得作为管理主列表的多接口聚合替代。

**状态**: 已自动化覆盖核心后端和前端契约。后端见 `apps/api/tests/test_product_system_config.py`、`apps/api/tests/test_requirement_lifecycle.py::test_management_lists_include_query_observability_metadata`、`apps/api/tests/test_bug_management.py`、`apps/api/tests/test_api_contract_completion.py`、`apps/api/tests/test_devops_gitlab_metrics.py`、`apps/api/tests/test_user_feedback.py`、`apps/api/tests/test_security_boundaries.py::test_core_management_lists_require_menu_declared_read_permissions`、`apps/api/tests/test_security_boundaries.py::test_product_scoped_management_lists_filter_business_records`、`apps/api/tests/test_database_persistence.py::test_product_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_database_persistence.py::test_product_version_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_database_persistence.py::test_requirement_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_database_persistence.py::test_bug_list_uses_repository_read_model_for_sql_pagination`、`apps/api/tests/test_database_persistence.py::test_insight_items_use_repository_read_model_for_sql_pagination` 和 `apps/api/tests/test_database_persistence.py::test_operational_metrics_use_repository_read_model_for_sql_pagination`；前端见 `apps/web/tests/App.test.tsx` 中管理表格默认规范、研发运营和用户洞察页面回归。

---

### TC-AIBRAIN-REQ-FUNC-011: 需求评估、版本协作与任务执行解耦

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011 |
| 用例名称 | 需求评估、版本协作与任务执行解耦 |
| 优先级 | P0 |
| 模块 | REQUIREMENT |
| 创建人 | Claude |
| 创建日期 | 2026-05-28 |

**前置条件**:
1. 存在启用产品、统一研发执行策略和 `planning` 迭代版本。
2. 存在评估 accepted 且状态为 `planned` 的需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/product-versions/{version_id}/collaboration-runs` | 返回唯一版本协作运行并冻结需求、产品、版本、策略和岗位快照。 |
| 2 | 协作编排服务创建产品详细设计工作项和内部 AI 任务 | AI 任务关联 `collaboration_run_id/work_item_id`，外部用户不能直接创建。 |
| 3 | PATCH 产品、版本或模块名称 | 产品配置更新成功。 |
| 4 | GET `/api/ai-tasks/{task_id}` | 返回生成时的评估、需求、产品、版本、策略和工作项快照，不被后续配置修改覆盖。 |
| 5 | GET `/api/requirements/{id}` | 需求保留原始输入、评估结论，并可定位所属版本协作运行。 |

**预期结果**:
1. 需求是评估和组版对象，产品版本是协作聚合根，AI 任务只是工作项执行单元。
2. 历史运行和任务依赖冻结快照解释，不读取实时策略覆盖历史。

**状态**: v2.0 待按 `test_requirement_assessments.py`、`test_rd_collaboration_runtime.py` 和 `test_rd_work_item_execution.py` 自动化；现有 v1 测试在切换时重写。

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
1. 用户已登录并具备需求创建、评估读取/决策权限。
2. 系统存在启用产品和同产品 `planning` 迭代版本。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/requirements`，只传产品、不传 `version_id` | 需求创建成功，状态为 `submitted`，`version_id=null`。 |
| 2 | POST `/api/requirements/{id}/assessments` 并形成 accepted 结论 | 评估持久化，需求进入 `approved`。 |
| 3 | 运行自动组版 | 优先归入兼容 `planning` 版本并进入 `planned`；无候选时只创建一个新规划版本。 |
| 4 | POST `/api/requirements/{id}/generate-task` | 返回 `409 RD_COLLABORATION_REQUIRED`，不创建任务。 |
| 5 | POST `/api/product-versions/{version_id}/collaboration-runs` | 创建版本协作，后续由工作项生成产品详细设计任务。 |

**预期结果**:
1. 需求池和迭代排期解耦，新增需求阶段不强迫选择版本。
2. 只有 accepted 且已组版需求能进入版本协作，用户不能绕过评估直接生成任务。

**状态**: v2.0 待由需求评估、自动组版和入口适配测试覆盖。

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
2. 系统存在启用产品、同产品各状态迭代版本、至少一条评估 accepted 的 `approved` 需求和一条 `planned` 需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在需求管理勾选同产品 `approved/planned` 需求，点击“调整组版”，选择目标版本并确认 | 目标版本下拉只展示 `planning` 并过滤已启动版本；前端发送 `POST /api/requirements/batch-schedule`，请求体包含产品、目标版本、需求、调整原因和最新评估版本。 |
| 2 | 在规划版本页面点击“调整需求范围”，勾选可归集需求并确认 | 前端复用同一调整接口；只有评估 accepted 且尚未进入活动协作的需求可加入。 |
| 3 | 通过 API 混入 `submitted`、跨产品、重复、策略/容量/仓库/交付终点/硬依赖不兼容和高风险覆盖需求 | 只有全部硬条件兼容的需求进入 `updated`；不兼容项进入 `skipped`，候选争议或高风险覆盖保持原状态并创建 `decision_request`。 |
| 4 | 查询需求列表和审计列表 | 已更新需求状态为 `planned` 且版本为目标版本；审计包含追加保存的 `requirement.batch_scheduled` 和每条更新需求的 `requirement.updated`，payload 带 `batch_id`，历史批次审计不被覆盖删除。 |

**预期结果**:
1. 多需求可快速手动归集到一个产品迭代版本，不需要逐条编辑。
2. 人工批量调整不影响已进入交付阶段的需求，也不能绕过自动组版使用的硬条件，并保留可追溯审计和决策。

**状态**: v1 基础能力已覆盖；v2.0 切换时扩展 `test_requirement_iteration_grouping.py`、`test_requirement_batch_schedule.py` 和页面用例覆盖硬条件与决策请求。

---

### TC-AIBRAIN-REQ-FUNC-011F: 旧批量生成任务入口关闭

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011F |
| 用例名称 | 旧批量生成任务入口关闭 |
| 优先级 | P0 |
| 模块 | REQUIREMENT / AI_TASK |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备产品负责人、研发负责人或管理员角色。
2. 系统存在启用产品和同产品至少两条 `planned` 需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开需求管理并勾选多条需求 | 页面不展示“批量生成任务”或单条“生成任务”。 |
| 2 | 直接调用 `POST /api/requirements/batch-generate-tasks` | 返回 `409 RD_COLLABORATION_REQUIRED` 和评估/版本协作入口，不创建任务。 |
| 3 | 查询需求、AI 任务和审计 | 需求状态与 task_ids 不变，没有 `ai_task.created`；记录旧入口阻断审计。 |

**预期结果**:
1. v2.0 不允许批量绕过版本协作生成任务。
2. 多需求通过同一版本协作运行统一拆解和执行。

**状态**: v2.0 待由 `test_rd_requirement_entry_adapters.py` 和 `RequirementsPage.test.tsx` 覆盖，现有 v1 批量生成用例在切换时替换。

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

### TC-AIBRAIN-REQ-FUNC-011H: v2.0 批量状态管理不得绕过研发协作

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REQ-FUNC-011H |
| 用例名称 | v2.0 批量状态管理不得绕过研发协作 |
| 优先级 | P1 |
| 模块 | REQUIREMENT |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备产品负责人、研发负责人或管理员角色。
2. 系统存在 submitted、planned、developing 需求，以及分别带有活动协作运行、非终态工作项和无活动协作的需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在需求管理批量操作中查看目标状态 | 页面只提供“取消”和“关闭”，不提供 planned、设计、开发、评审、测试、待发布、部署、发布或验收状态。 |
| 2 | 直接调用 API 并传入 `target_status=ready_for_release` 或其他交付状态 | 整个请求返回 `409 RD_COLLABORATION_REQUIRED`，所有需求状态不变，不写成功审计。 |
| 3 | 传入 `target_status=closed`，混入活动协作、非终态工作项、无活动协作、重复和不存在需求 | 只有既无活动协作运行、也不存在非终态工作项的合法需求关闭；其他项返回带 run/work-item 引用的 skipped 原因。 |
| 4 | 查询需求详情和审计列表 | 成功项记录 `requirement.batch_closed` 与逐需求 `requirement.updated`；不存在 `requirement.batch_status_advanced` 交付推进事件。 |

**预期结果**:
1. 需求交付状态只能由评估、组版、协作工作项、审核、版本动作和门禁证据推进。
2. 批量接口只承担安全取消/关闭管理，不形成第二条研发推进路径。

**状态**: v2.0 切换时重写现有自动化，覆盖 `RD_COLLABORATION_REQUIRED`、活动协作阻断和前端目标状态收口。

---

### TC-AIBRAIN-TASK-FUNC-020C: 研发任务批量取消

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-020C |
| 用例名称 | 研发任务批量取消 |
| 优先级 | P0 |
| 模块 | AI_TASK |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备研发负责人或管理员角色。
2. 系统存在未关联协作工作项的历史可取消任务、终态任务，以及关联 `collaboration_run_id/work_item_id` 的 v2 协作任务。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 对 v2 协作任务调用单个 `/cancel` | 返回 `409 RD_COLLABORATION_REQUIRED` 和工作项/运行入口，任务、Review、attempt、工作项和运行均不改变。 |
| 2 | 批量请求混入一个 v2 协作任务和一个历史任务 | 整批返回 `409 RD_COLLABORATION_REQUIRED`，历史任务也不发生部分取消。 |
| 3 | 仅对历史任务批量取消，并混入终态、重复和不存在 ID | 合法历史任务进入 `updated/cancelled`；终态、重复和不存在任务进入 `skipped`，code 稳定返回 `TASK_STATE_INVALID`、`DUPLICATE_TASK` 和 `NOT_FOUND`。 |
| 4 | 调用 `POST /api/delivery/rd-work-items/{id}/cancel`，提交 `reason/version/idempotency_key`；分别取消低风险可选项和影响必需交付的高风险项，并模拟事务失败、Runner 取消 Outbox 失败、Runner 迟到完成，以及高风险取消被拒绝/选择继续 | 低风险成功时原子取消 AI task、pending Review、当前 attempt 和工作项，撤销租约、重算运行状态并写协作事件、审计和 Runner 取消 Outbox；领域事务失败时全部回滚，Outbox 可幂等重试。高风险返回 `202` 和 decision request，同时进入 awaiting_human、撤销旧 lease、挂起 attempt 并发出取消 Outbox；迟到结果只作审计证据。批准后完成取消；拒绝/继续时旧 attempt/lease 不复活，工作项重新校验到 ready，由新 claim 创建 attempt/lease。 |

**预期结果**:
1. 历史非协作任务继续支持批量取消和逐项 skipped 结果。
2. v2 协作任务不能绕过工作项状态机，取消结果在协作聚合内保持原子一致。

**状态**: 历史任务路径已自动化覆盖；v2.0 需新增单个/批量 `RD_COLLABORATION_REQUIRED` 和工作项取消原子性测试。既有覆盖见 `apps/api/tests/test_api_contract_completion.py::test_ai_task_batch_cancel_updates_valid_tasks_and_skips_terminal_tasks` 与 `apps/api/tests/test_router_boundaries.py::test_ai_task_batch_cancel_handler_does_not_call_legacy_main`。

---

### TC-AIBRAIN-TASK-FUNC-020D: v2.0 失败任务由工作项调度恢复

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-TASK-FUNC-020D |
| 用例名称 | v2.0 失败任务由工作项调度恢复 |
| 优先级 | P1 |
| 模块 | AI_TASK |
| 创建人 | Codex |
| 创建日期 | 2026-06-05 |

**前置条件**:
1. 用户已登录并具备研发负责人、评审人或管理员角色。
2. 系统存在关联协作工作项的可恢复失败任务、不可恢复任务和预算耗尽任务。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开任务中心并选择失败任务 | 页面不提供批量重试或直接 start；提供跳转关联工作项、查看证据和请求人工处理。 |
| 2 | 真人调用 `POST /api/ai-tasks/batch-retry` 或 `/start` | 返回 `409 RD_COLLABORATION_REQUIRED`，任务和工作项不变。 |
| 3 | 工作项调度器处理可恢复失败、不可恢复失败和预算耗尽 | 可恢复失败复用原 task id 创建新 attempt 并内部派发；不可恢复或预算耗尽进入 `awaiting_human/rework_required/failed`，保存原因和恢复目标。 |
| 4 | 查询任务、工作项、attempt、事件和审计 | 所有恢复结果可追溯，重复调度幂等，不存在真人直接启动审计。 |

**预期结果**:
1. 模型网关或执行器恢复后，由协作调度器安全恢复失败工作项，避免复制任务或绕过预算和策略。
2. 真人只能处理工作项决策，不能通过任务批量重试形成第二条运行路径。

**状态**: v2.0 切换时由 `test_rd_requirement_entry_adapters.py` 和 `test_rd_work_item_execution.py` 重写覆盖。

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
| 3 | 对 `testing` 版本推进到 `ready_for_release`，版本内仍有 `developing` 需求或缺少远程 Git 对账证据 | 返回 `PRODUCT_VERSION_STATUS_BLOCKED`；未完成需求处理完且每个必需仓库具备对账成功的远程分支/commit/MR-PR 证据后才能进入 `ready_for_release`，不会自动进入 `released`。 |
| 4 | 对 `released` 版本归档为 `archived` | `released/accepted/deferred/cancelled/closed/rejected` 需求保持不变；未完成需求作为归档风险项。 |
| 5 | 直接 PATCH 版本 `status` | 返回 `PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED`，不能绕过影响预览和需求同步逻辑。 |
| 6 | 对 `testing` 版本点击“查看需求” | “归集需求”保持禁用，但只读需求清单可打开，且只展示当前版本下的需求。 |
| 7 | 打开真实迭代版本页面 | “推进状态”入口可见，弹窗可生成影响预览，“查看需求”可回看当前版本需求，页面无空白、无框架错误覆盖层、无相关控制台错误。 |

**状态**: 已自动化覆盖。版本状态机 service 层单测见 `apps/api/tests/test_version_status_service.py`，接口行为见 `apps/api/tests/test_iteration_version_status_flow.py`，页面用例见 `apps/web/tests/App.test.tsx`；真实网页验证作为提交前门禁执行。

---

### TC-AIBRAIN-CONFIG-FUNC-008E: 迭代版本驾驶舱

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-CONFIG-FUNC-008E |
| 用例名称 | 迭代版本驾驶舱 |
| 优先级 | P1 |
| 模块 | PRODUCT_CONFIG / REQUIREMENT / BUG / CODE_INSPECTION |
| 创建人 | Codex |
| 创建日期 | 2026-06-28 |

**前置条件**:
1. 用户已登录并具备 `product.read`，且产品 scope 覆盖目标迭代版本。
2. 系统存在至少一个迭代版本，版本下关联需求、AI 任务、版本代码分支、Bug、代码巡检报告、代码评审报告、知识沉淀和发布记录。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在迭代版本列表点击目标版本“驾驶舱” | 页面调用 `GET /api/product-versions/{version_id}/dashboard`，弹窗展示版本名称、当前阶段、下一阶段、需求数、任务数、分支数、Bug 数、代码巡检数、代码评审数、知识沉淀数和发布记录数。 |
| 2 | 查看交付链路总览和发布准备清单 | 弹窗在明细表前按研发链路顺序展示需求范围、研发任务、代码分支、代码巡检、代码评审、Bug 收敛、知识沉淀、发布证据和状态推进九项，红/黄环节优先提示治理风险，能直接看出可推进、阻塞或待治理状态。 |
| 3 | 查看阻塞处理队列和阶段影响 | 未完成需求、发布阻塞 Bug、高风险代码巡检、缺少版本分支或缺少发布记录会进入阻塞项；阻塞处理队列按严重级别和来源类型排序展示优先级、来源、解除条件和处理入口；状态推进影响展示目标阶段和会被同步推进的需求数。 |
| 4 | 点击阻塞项的处理入口 | 阻塞处理队列和明细表均提供处理入口；需求跳转需求管理，Bug 跳转 Bug 管理，代码巡检跳转巡检详情，版本分支跳转迭代版本分支配置，发布记录跳转日志监控/发布记录筛选。 |
| 5 | 查看明细表格 | 需求、AI 任务、Bug、代码巡检、代码评审、知识沉淀、版本分支和发布记录均使用固定列宽和横向滚动，长标题、仓库地址或建议文本不会挤压操作区；知识沉淀行展示沉淀标题、来源任务、知识文档 ID 和全链路入口，不展示知识正文。 |
| 6 | 使用只有 `product.read`、无 `bug.read`、`code_inspection.read` 或 `knowledge.read` 的角色访问驾驶舱 | 版本摘要、需求、任务和分支仍可展示；Bug、代码巡检或知识沉淀明细为空，并在 `access_issues` 中提示对应能力缺少权限。 |
| 7 | 使用产品 scope 外用户访问驾驶舱接口 | 返回 404，不泄露 scope 外版本是否存在。 |

**状态**: 已自动化覆盖。接口聚合用例见 `apps/api/tests/test_iteration_version_status_flow.py::test_product_version_dashboard_aggregates_delivery_health_and_blockers`，页面弹窗用例见 `apps/web/tests/IterationVersionsPage.test.tsx`；真实网页验证作为提交前门禁执行。

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
| 6 | 进入知识中心主列表并查看“索引健康”视图 | 当前分页结果展示可检索、向量就绪、关键词兜底、索引失败、处理中和分块版本指标；`text_indexed` 文档显示向量待补并可处理，`index_failed` 文档可重试索引，缺少 `active_chunk_set_id` 的可检索文档可进入分块版本。 |

**预期结果**:
1. 知识中心不依赖 AI 任务完成也可以主动导入和检索。
2. 知识沉淀必须审核后才能进入正式知识库。
3. 知识负责人能够在主列表直接识别 Embedding 降级、索引失败和分块缺失，不需要逐条打开资产或分块弹窗排查。

**状态**: 已自动化覆盖。知识导入、索引、检索、沉淀审核、失败重试和索引健康视图见 `apps/api/tests/test_knowledge_governance.py` 与 `apps/web/tests/KnowledgePage.test.tsx` 知识中心用例。

---

### TC-AIBRAIN-KNOWLEDGE-FUNC-012B: 知识空间目录和资产导入

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-KNOWLEDGE-FUNC-012B |
| 用例名称 | 知识空间目录、资产导入和分块版本治理 |
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
| 3 | POST `/api/knowledge/documents/upload` 上传 Markdown 文件，指定 `parser_engine=markdown`、`chunk_strategy=parent_child`，再上传一份 `chunk_strategy=regex_section` 文档 | 文件写入对象存储，结构表写入 `knowledge_documents`、原始 `knowledge_assets` 和 queued `knowledge_import_jobs`；文档状态为 `importing`，暂不暴露 active chunk set；worker 可用时任务自动入队；正则分块任务按结构分隔符生成 chunk 并保留分段标题。 |
| 4 | 轮询 `GET /api/knowledge/import-jobs` 或查询 `GET /api/knowledge/import-worker/status`，必要时用 `POST /api/knowledge/import-jobs/{job_id}/run` 补偿 | 后台 worker 完成导入任务，生成独立 `parsed_markdown` 资产、新 `knowledge_chunk_sets` 和父子 `knowledge_chunks`；OCR/Table JSON 同时生成 `ocr_json` / `table_json` 结构化 sidecar 资产；文档切换到 active chunk set；导入任务弹窗展示 worker 启用、运行、待处理、active、已处理和失败计数；`run` 仅作为测试/运维补偿入口。 |
| 5 | GET `/api/knowledge/documents?knowledge_space_id=...&folder_id=...` | 返回上传文档，包含 `source_asset_id`、`parsed_asset_id`、`active_chunk_set_id` 和目录信息。 |
| 6 | POST `/api/knowledge/search` 并传 `knowledge_space_id` | 只返回当前空间可读结果；父子分块时命中子块，source 包含 `asset_id`、`chunk_set_id`、`folder_id`、`knowledge_space_id`、`parent_chunk_id` 和 `parent_content`；OCR/Table 命中 chunk metadata 可回溯 `page_number`、`table_index`、`columns` 和结构化资产。 |
| 7 | GET `/api/knowledge/documents/{document_id}/assets` | 只返回当前用户可读文档的原始资产和解析资产，包含文件名、资产类型、MIME、大小和存储提供方；OCR/Table JSON 导入应同时返回结构化 `ocr_json` / `table_json` 和 `parsed_markdown`。 |
| 8 | GET `/api/knowledge/import-jobs?knowledge_space_id=...` | 只返回当前用户可读空间的导入任务，包含文档标题、源文件、目录、解析器、切片策略、进度和状态。 |
| 9 | GET `/api/knowledge/documents/{document_id}/chunk-sets` 与 GET `/api/knowledge/documents/{document_id}/chunks?chunk_set_id=...` | 可查看 active/archived chunk set、父块/子块预览和正则分块预览；前端展示 OCR/Table 页码、表格序号、列名、来源资产类型、正则分段标题和切分规则。 |
| 10 | POST `/api/knowledge/documents/{document_id}/reparse` 后等待 worker 处理新导入任务，再 POST `/api/knowledge/documents/{document_id}/chunk-sets/{old_id}/activate` | 重解析任务自动入队；成功生成新 chunk set，旧版本归档；激活旧版本可回滚 active chunk set。 |
| 11 | 构造解析失败任务后 POST `/api/knowledge/import-jobs/{job_id}/retry`，再对 queued 任务 POST cancel | 失败任务重试回到 queued 且 worker 可用时自动重新入队，不重复创建文档；queued 任务可取消，已取消任务运行返回 `IMPORT_JOB_STATE_INVALID`。 |
| 12 | PATCH `/api/knowledge/folders/{folder_id}` 与 POST `/api/knowledge/documents/batch-move` | 目录支持重命名、移动、排序、归档；文档批量移动返回 updated/skipped 明细并校验空间写权限。 |
| 13 | GET `/api/knowledge/assets/{asset_id}/preview` | 通过 API 鉴权返回文本预览，不暴露永久对象存储 URL。 |
| 14 | 使用非空间成员重复列表、检索、资产、导入任务、chunk set、chunk 预览和预览接口 | 返回空结果或 403，不泄露空间文档、chunk、任务或资产内容。 |

**预期结果**:
1. 知识空间是权限边界，目录是组织结构，资产存储只承载原始文件和解析产物。
2. PostgreSQL 仍是业务事实源，MinIO/S3 仅作为对象存储层。
3. 知识中心页面提供文档资产弹窗、导入任务弹窗、worker 状态摘要、chunk 预览弹窗和批量移动入口，运营人员可查看导入处理结果并治理分块版本。
4. 前端知识中心支持空间筛选、目录选择、新建空间/目录、文件上传、导入任务状态查看、worker 状态查看、chunk 来源元数据预览和文档批量移动；后台 worker 自动处理导入，手动运行仅作为补偿入口。

**状态**: 已自动化覆盖。后端见 `apps/api/tests/test_knowledge_import_operations.py`、`apps/api/tests/test_knowledge_space_assets.py`、`apps/api/tests/test_knowledge_management_foundation.py` 和 `apps/api/tests/test_persistence_repository_boundaries.py`；前端见 `apps/web/tests/KnowledgePage.test.tsx`。

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

### TC-AIBRAIN-TASK-FUNC-025: Agent 自治循环与人工接管

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v1.2 |

**测试步骤**:
1. 配置 `autonomy_mode=autonomous_loop`、最大轮次/时长和 Token/费用预算并启动任务。
2. 让首轮独立门禁返回可重试失败，再让下一轮通过。
3. 重复一次场景，在循环运行中调用 `POST /api/ai-tasks/{task_id}/agent-loop/takeover`。

**预期结果**:
- 每轮保存计划、上下文版本、编码/verifier 任务、门禁、修改摘要、测试证据、失败分析和预算；下一轮指令包含上一轮失败证据。
- 达标后进入人工确认或受控自动合入；预算耗尽、安全阻断或人工接管后不再派发下一轮。
- 人工接管取消运行中循环任务但保留隔离工作区和已有证据，任务详情时间线可解释接管原因。

**状态**: 已自动化覆盖，见 `apps/api/tests/test_rd_task_executor_policies.py::test_autonomous_loop_retries_failed_gate_with_versioned_context_then_merges`、`test_autonomous_loop_can_be_stopped_for_human_takeover_without_discarding_workspace` 和 `apps/web/tests/AgentGovernancePages.test.tsx`。

---

### TC-AIBRAIN-TASK-FUNC-026: 独立质量门禁与受控自动合入

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v1.2 |

**测试步骤**:
1. 配置 `auto_commit` 并让编码 Runner 回写成功，但让 required verifier 检查失败。
2. 让测试全部通过但变更命中数据库迁移或受保护目录。
3. 提供通过的独立 verifier/CI 证据且风险低于阈值。

**预期结果**:
- 步骤 1 不产生 merge 决策，任务保留门禁失败证据；编码 Runner 自报成功不计作唯一独立证据。
- 步骤 2 强制进入人工确认；高风险安全发现、变更文件/行数超限同样阻止自动合入。
- 只有步骤 3 自动创建已通过 Review 和幂等 merge 决策，任务详情按检查项展示来源、状态和结构化证据。

**状态**: 已自动化覆盖，见 `apps/api/tests/test_quality_gates.py` 和 `apps/api/tests/test_rd_task_executor_policies.py::test_executor_policy_auto_commit_waits_for_independent_quality_gate_before_merge`。

---

### TC-AIBRAIN-TASK-FUNC-027: 版本化执行上下文清单

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v1.2 |

**测试步骤**:
1. 从带需求、Bug、仓库、版本和产品知识的任务启动执行。
2. 查看任务详情“执行上下文”，再以同一事实重建一次清单。
3. 尝试注入 scope 外产品或在摘要中放入 token-like 内容。

**预期结果**:
- 清单返回稳定版本/内容哈希、需求/Bug、仓库/分支、知识文档/chunk/版本、召回原因、验收标准、权限和截断摘要；相同内容去重。
- scope 外产品被拒绝，凭据和完整知识正文不进入清单；任务详情能逐项核对 AI 收到的上下文。

**状态**: 已自动化覆盖，见 `apps/api/tests/test_execution_context_manifests.py` 和 `apps/web/tests/AgentGovernancePages.test.tsx`。

---

### TC-AIBRAIN-KNOWLEDGE-FUNC-031: 多模态知识版本与新鲜度治理

| 项目 | 内容 |
|------|------|
| 优先级 | P1 |
| 适用阶段 | v1.2 |

**测试步骤**:
1. 创建测试 HTTP 多模态 Profile，使用 `env:` 凭据引用上传图片/PDF并选择 `parser_engine=multimodal`。
2. 运行导入并查看资产、文档版本、chunk 和搜索来源。
3. 重解析生成新版本，分别模拟成功和失败。
4. 提交 `outdated` 引用反馈并执行新鲜度扫描。

**预期结果**:
- 原始资产保留在对象存储，解析生成 Markdown、OCR、版面、表格和图片标注资产；chunk/source 返回版本、模态、页码、位置框和脱敏 Provider 元数据。
- 成功新版本才切换 active；失败版本不影响旧版本继续检索。
- Profile 响应不解析或回显凭据；直接 token/password 配置被拒绝。
- 过期反馈和时间扫描形成 `fresh/expiring/expired/flagged_outdated`，并关联具体版本。

**状态**: 已自动化覆盖，见 `apps/api/tests/test_knowledge_multimodal_governance.py` 和 `apps/web/tests/KnowledgePage.test.tsx`。

---

### TC-AIBRAIN-RD-FUNC-032: 正式需求评估与规划版本优先归组

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v2.0 |

1. 为同产品准备一个容量和范围兼容的 `planning` 版本，提交需求并创建正式评估，确认需求仍为 `submitted`；分别以普通用户、评估决策人和策略管理员请求尝试指定任意 `strategy_id`，再通过统一策略 API 更新策略形成新 `policy_version` 后重新评估。
2. 由被分配的真人/AI 评估者提交岗位意见，由需求负责人提交补充回答，再分别执行 `accept/reject/request_more_info/request_rework/defer` 决策。
3. 让评估通过，验证需求归入既有版本；再提交一个无候选的低风险需求、一个候选并列需求和一个高风险新建版本需求。

**预期结果**: 评估持久化需求修订、初始/最终不可变策略快照、完整度、风险、依赖、工作量、候选版本和确定性检查；所有调用者都不能在评估请求中覆盖策略，需要调整时只能先更新统一策略再重新评估。同一 `requirement_id + requirement_revision + initial_strategy_snapshot_id` 进行中或成功评估受唯一约束保护，切换 final/effective 快照不会释放该业务键；`requirement_id + request_id` 由持久化命令幂等记录约束，重复摘要返回原结果、不同摘要返回 `RD_IDEMPOTENCY_CONFLICT`。`opinions/answers/decisions` 分别校验执行主体、输入版本、意见快照外键和乐观锁并映射到规范状态；accepted 后需求先进入 `approved`，兼容时复用已有规划版本、无候选低风险需求才自动新建，候选并列或高风险建版保持 `approved` 并创建组版决策，成功组版后进入 `planned`。非 accepted 评估不能组版或创建协作运行，旧 approve/reject 不能绕过评估。

---

### TC-AIBRAIN-RD-FUNC-033: 单一统一研发执行策略

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v2.0 |

1. 通过原研发执行器策略入口提交唯一顶层契约 `name/brain_app_id/product_id/status/matching_config/assessment_config/iteration_config/delivery_target/team_config/autonomy_config/quality_gate_config/git_config/experience_reuse_config/deployment_config/role_bindings`；以 `policy_version` 创建、读取并通过 `expected_policy_version` 并发更新，尝试同时启用两个默认策略或两个同产品策略。
2. 提交旧版单任务策略、缺少岗位执行器的策略，以及不存在 active 策略时启动评估/协作。
3. 并发冻结同一规范化策略；让两个评估从同一 `policy_version`/base 快照分别自动收紧出不同 final payload，再让另外两条需求都没有收紧差异并共同复用该 base 作为 final/effective；分别合并成 version_resolved 并保存逐需求来源与运行范围，再模拟不同 policy version、未声明 merge operator、允许集/禁止项/岗位/门禁/上限/交付终点冲突，以及经验复用 enabled/置信度/容量/时效/兼容性/信任域差异；修改策略后读取既有评估、岗位意见、运行、反馈和经验来源引用；尝试构造空身份列、base 带 parent、assessment_resolved 缺 parent/越界 revision、version_resolved 无来源/跨 policy version 来源、来源缺失/多余/同需求重复或与运行范围不一致，尝试 UPDATE/DELETE 快照、来源及运行范围、删除仍有快照的策略，以及篡改快照 payload、哈希或 Schema 版本。

**预期结果**: 只存在一套写契约和运行规则；旧契约、同义字段、评估/版本显式策略和不完整策略被拒绝，缺少策略时明确阻断且无旁路。策略创建为 `policy_version=1`，成功更新原子递增，过期版本返回乐观锁冲突；同一业务大脑最多一个 active 默认策略、同一产品最多一个 active 产品策略，产品策略优先。策略复核最多自动单调收紧两轮，新增岗位补齐意见，不可比较或可能放宽的变化进入人工决策。base 快照使用 revision 0 且 parent 为空，自动收紧生成带同策略版本 parent、assessment context 和 revision 1..2 的 assessment_resolved 快照；身份列为非空并受 CHECK/唯一约束保护，两个评估可有不同 final payload 且互不冲突，同一快照身份的不同哈希被拒绝；没有差异时 final/effective 直接引用 base，多条需求可各保留 requirement 来源边并共同引用同一 base。多需求运行始终生成唯一 version_resolved，允许集交集、禁止项/岗位/门禁/人工点并集、上限取严、ready_for_release 优先；经验复用 enabled 取 AND、最低置信度取最大、容量/时效上限取最小、信任域取交集、兼容性取最严、独立审核取 OR。策略来源和不可变运行范围逐条覆盖全部 requirement/assessment final，source count 等于范围行数；只允许 `(snapshot_id,requirement_id)` 唯一，不允许阻止共享 base 的 `(snapshot_id,source_snapshot_id)` 唯一约束。未声明/不可比较字段返回 `RD_VERSION_POLICY_MERGE_REQUIRED`。延迟约束触发器拒绝无来源、范围缺失/多余、同需求重复、跨策略版本或主体不匹配关系，数据库触发器拒绝快照/来源/运行范围 UPDATE/DELETE；策略及所有消费者外键为 `ON DELETE RESTRICT`，有快照的策略 DELETE 返回 `RD_POLICY_IN_USE`；策略修改不改变历史解释，快照缺失、哈希不一致或 Schema 不兼容返回 `RD_POLICY_SNAPSHOT_INVALID`。

---

### TC-AIBRAIN-RD-FUNC-034: 动态岗位、混合席位与工作项 DAG

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v2.0 |

1. 新增文档/安全岗位、两个复用同一执行器的 AI 数字员工和真人用户；分别用 AI 员工与真人占用岗位席位。
2. 给同一规划版本加入两条 accepted/planned 需求，使其 final payload 不同但可确定性合并，读取列表/详情中的 `scope_version`；分别修改需求成员、需求修订/验收、纳入需求的 final/effective 策略快照、仓库和分支冻结输入，验证范围版本原子递增，再使用相同和不同 `request_id/scope_version` 并发启动协作运行；另用不同 policy version 或不可合并 payload 尝试启动；创建含并行开发、测试、文档和集成依赖的工作项图并尝试重复边与循环依赖。
3. 使用 `expected_version/lease_seconds/idempotency_key` claim，在租约有效期内重复相同请求，再在租约过期后重复旧键；使用 `attempt_id/lease_token/version/output/evidence/idempotency_key` submit，再以 `decision/comment/version/idempotency_key` 执行独立审核并分别触发 approve、request_rework 和 reject。
4. 在活动运行中分别通过普通入口尝试加入/移除需求、切换修订/验收/final 快照和改变仓库/分支，并执行一次不改变范围的重规划。随后调用 `POST /api/product-versions/{version_id}/scope-change-requests`，使用 `request_id/expected_scope_version/expected_run_generation/source_run_id/reason/operations` 覆盖四类合法 operation、非法任意 payload、过期 scope/generation、相同/不同 request 并发和一个版本多个 pending 请求；从 running/integrating/verifying 分别验证暂停，再批准或拒绝，模拟 operations 中途失败。批准后用响应的 `terminal_run_id/applied_scope_version` 显式并发 restart；另模拟非最近代、已有活动运行、策略/仓库/岗位失效和历史 approved 证据仍兼容/已失效。最后让 ready-target 运行处于 `completed(completion_reason=ready_for_release)`，并让 deployed 目标运行分别处于 `ready_for_release/deploying`，提交范围请求与终结/restart；通过标准需求接口分别创建仅携带 `source_collaboration_run_id` 的全新后续需求、同时携带 `supersedes_requirement_id/source_collaboration_run_id` 的延续需求，以及缺少来源运行却单填 supersedes 的非法需求。

**预期结果**: 动态岗位和 AI 员工档案不修改系统 RBAC；P0 真人只能从显式 user_ids、AI 只能从显式 ai_employee_ids 选择。AI 席位分别冻结 `ai_employee_id` 和 `executor_profile_id`，两个员工复用执行器时仍可独立归因；`product_versions.scope_version` 是持久化范围事实版本，需求成员、修订/验收、final/effective 策略快照、仓库及分支这五类输入变化在无活动运行时于同一事务递增，列表、详情、候选分组和冲突响应返回当前值。启动后普通变更全部返回 `RD_SCOPE_FROZEN`，运行范围与来源不变；非范围重规划只递增 `plan_version`。受控范围请求按版本/request 唯一且同版本最多一个 pending；无效 operation 返回 `RD_SCOPE_CHANGE_INVALID` 且无部分写，过期 scope/generation 分别返回 `RD_SCOPE_VERSION_CONFLICT/RD_RUN_GENERATION_CONFLICT` 且不创建决策。running/integrating/verifying 请求暂停旧运行，draft/planning 使用 pending 请求围栏继续调度，已有其他 waiting_human 决策时不得覆盖；批准事务终结旧运行、应用全部 operations、恰好递增一次 scope 并返回 terminal_run_id，失败整体回滚；拒绝只恢复由本请求暂停的阶段并保持范围不变。调用方随后显式 restart 生成新 generation。ready-target completed 或 deployed-target 进入 `ready_for_release/deploying` 后，范围请求返回带 `resolution=new_planning_version/next_action=create_followup_requirement` 的 `RD_SCOPE_FROZEN`，不得回退、终结或 restart；后续需求必带同产品来源运行，延续/替代时可再带旧需求，缺少来源运行的 supersedes 被拒绝，且新需求从 submitted 独立评估并只进入新 planning 版本。启动返回 `strategy_snapshot_kind=version_resolved`、hash 和准确 source count，不可变运行范围与来源逐条覆盖两条需求 final/effective；不同策略版本或不可合并字段返回 `RD_VERSION_POLICY_MERGE_REQUIRED` 且无运行，决策选项只能拆分/移出需求、修改统一策略后重评或取消，不能提交任意合并 payload/版本显式策略。同一范围和版本快照并发启动以完整成功响应快照幂等返回唯一活动运行并标记 `idempotent_replay=true`，不同或过期 `scope_version` 返回 `RD_SCOPE_VERSION_CONFLICT/RD_ACTIVE_RUN_CONFLICT`。failed/cancelled 运行和历史证据保持不可变，产品版本保留 active/testing 阶段；合法 restart 创建唯一 `run_generation+1/supersedes_run_id` 新运行，重复请求幂等。过期 scope、策略合并失败、快照损坏分别返回 `RD_SCOPE_VERSION_CONFLICT/RD_VERSION_POLICY_MERGE_REQUIRED/RD_POLICY_SNAPSHOT_INVALID`；非法来源、非最近代、已有活动运行或资源失效返回 `RD_RUN_RESTART_NOT_ALLOWED`，均无部分新计划。仅仍兼容的 approved 证据可被新工作项引用，旧 attempt/lease 不复活。活动运行、generation、范围请求及其类型化 operation、命令幂等、依赖边、工作项幂等键和 attempt 编号/幂等键均有数据库唯一约束；无依赖项并行派发，重复边和循环依赖被拒绝。claim/submit/review 的成功和幂等重放响应完整返回工作项、attempt、运行版本、next_state、idempotent_replay 和 trace_id；claim 只在原租约有效期内从 replay secret 重放同一 attempt/token，过期清理擦除密文并固定返回 `RD_WORK_ITEM_LEASE_EXPIRED`，不创建新 attempt。冲突无部分写。approve -> approved，request_rework -> rework_required 并保留原 attempt，reject -> failed 且必需项触发运行级重规划/终止决策；同范围返工创建新 attempt。

**范围批准原子性断言**: 批准 scope change 时，旧 generation 的全部活动租约/replay secret、非终态工作项、当前 attempt、pending Review、关联 AI task、未派发 Runner/Git Outbox 必须与运行终结、范围应用和 scope 递增一起收敛；已派发 Runner 写 cancellation Outbox，已派发或未知外部动作进入对账。任一写入失败全部回滚。提交后迟到 submit、Review、Runner completion、Git callback 或 Outbox 回写只形成审计/对账证据，不能改变旧运行或新 generation；restart 创建新的隔离 worktree/分支、工作项、attempt 和租约。

---

### TC-AIBRAIN-RD-FUNC-035: LLM 建议与确定性控制、人类决策

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v2.0 |

1. 让 LLM 返回合法拆解建议，再返回循环依赖、越权负责人、低报风险和超预算建议。
2. 触发敏感目录、数据库迁移、质量门禁失败和岗位冲突。
3. 让工作项分别进入 `blocked` 和 `awaiting_human`；再让协作运行分别从 `running/integrating/verifying` 进入 `waiting_human`。检查 `plan_version=0` 的非计划决策及选项冻结的 `code/label/outcome/subject_transition/requires_comment/input_schema/effect_preview`，使用 `selected_option/input/comment/version/idempotency_key` 人工批准、拒绝或要求补充信息；分别提交合法 input、缺少必填字段、额外字段和类型错误。通过 answers 子资源以有/无 `delivery.decision_requests.answer`、命中/未命中 `answer_actor_selector` 和产品范围的账号补充后再次决策，并重复提交相同、不同摘要或过期决策；并发创建同主体/类型/计划版本的 `pending/waiting_more_info` 请求，直接构造不完整暂停字段和非法 resume_state。
4. 为 pending/waiting_more_info 决策冻结 `expires_at/timeout_policy=escalate_keep_paused/escalation_target_selector`，在数据库时间到期边界前后并发、重复执行超时扫描，模拟升级对象存在和不存在，再对旧请求执行 decide/answer。
5. 分别触发策略缺失、岗位缺席、执行器暂时不可用、策略冲突需人工处理、自动收紧超限、旧入口绕过协作和非法范围 operation，核对公共 FastAPI `detail` envelope、HTTP、details、retryable、next_action、当前版本/范围/代次和主体状态。

**预期结果**: 合法建议经平台写入；非法 DAG、权限、风险和预算建议不能改变状态；高风险问题创建决策请求并只暂停受影响分支。服务端只按冻结 option 的 outcome/subject_transition 执行确定性映射并严格校验 input_schema，缺失/额外/类型错误均稳定拒绝且无部分状态；客户端和 LLM 不能注入任意目标状态。request_more_info 进入 `waiting_more_info`；只有同时具备 answer 权限、业务大脑/产品范围并命中 selector 的答复者可提交，answers 形成新版本后才可再次决策。答案提交及重放完整返回 pending 决策请求、新 options/options_hash、受影响主体、next_state、idempotent_replay 和 trace_id，冲突不写部分答案。`plan_version` 非空且非计划决策固定为 0，同一有效主体/类型/计划版本最多一个 `pending/waiting_more_info` 请求。工作项暂停时保存平台冻结的 `resume_state`、attempt 和解除条件；运行暂停时原子保存 `resume_state/suspended_decision_request_id/suspended_at`，三个来源阶段均按冻结值恢复并清空字段。数据库 FK/CHECK 拒绝缺字段、非法阶段、悬空决策引用和非 waiting_human 残留暂停字段。`blocked` 重新校验后只能进入 ready/cancelled；一般 `awaiting_human` 按决策进入 running/rework_required/cancelled，取消被拒绝/继续时进入 ready 并等待新 claim。客户端伪造恢复目标被拒绝。数据库时间达到 expires_at 后原请求原子进入 expired 并记录唯一 expiry event，主体保持暂停；存在升级对象时只创建一个活动后继请求并切换主体引用，不存在时告警但不恢复。重复/并发扫描幂等，任何 option 都不会被自动批准，旧请求 decide/answer 返回 `RD_DECISION_EXPIRED`。决策成功/重放响应返回决策结果、受影响主体、运行版本、next_state、idempotent_replay 和 trace_id；乐观锁、不同摘要幂等冲突、过期或已替代请求返回稳定错误且无部分写。`RD_EXECUTION_POLICY_REQUIRED/RD_ROLE_ASSIGNMENT_REQUIRED` 为 409 且配置修复前不可原请求重试；`RD_EXECUTOR_UNAVAILABLE` 为 503 并返回 retry_after；`RD_POLICY_HUMAN_DECISION_REQUIRED/RD_POLICY_RESOLUTION_LIMIT` 为 409 且评估保持 waiting_human；`RD_COLLABORATION_REQUIRED` 为 409 且旧入口无状态变化；`RD_SCOPE_CHANGE_INVALID` 为 422 且返回 operation/field 问题。所有错误均返回明确 retryable/next_action，审计可追溯建议与最终平台判断。

---

### TC-AIBRAIN-RD-FUNC-036: 默认待发布终点与可信远程交付

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v2.0 |

1. 使用默认 `delivery_target=ready_for_release`，让集成工作项通过 Outbox 完成远程推送并保存分支、local/remote SHA、MR/PR 和对账证据，再完成测试和门禁。
2. 删除或篡改远程 commit/MR/PR 对账证据，重复完成判定。

**预期结果**: P0 集成工作项必须完成最小工作分支隔离、远程 push 或 MR/PR Outbox、版本级集成测试和不可变交付证据。缺少或不匹配远程证据时不能进入待发布，完成判定不临时执行 push。发布就绪证据记录与目标终结分离；默认策略让产品版本进入并保持 `ready_for_release`，协作运行进入 `completed` 且 `completion_reason=ready_for_release`，不创建部署单，服务不得无条件关闭所有交付目标的运行。

---

### TC-AIBRAIN-RD-FUNC-036B: P1 可选部署边界

| 项目 | 内容 |
|------|------|
| 优先级 | P1 |
| 适用阶段 | v2.0 P1 |

1. 在 `RD_COLLABORATION_DEPLOYMENT_ENABLED=false` 时尝试创建/激活 `delivery_target=deployed` 策略，并运行 P0 协作套件。
2. 开启 P1 标志，在已经具备可信远程交付和 `ready_for_release` 证据、且协作运行保持非终态 `ready_for_release` 的版本上使用 `delivery_target=deployed`。
3. 分别模拟未通过和通过人工发布门禁、部署失败回滚和部署成功。

**预期结果**: P1 标志关闭时 deployed 策略稳定拒绝，P0 策略、页面和完整套件仍可独立通过。部署目标在可信待发布证据完成后运行仍处于非终态 `ready_for_release`，未确认时不创建部署单；确认后只通过现有部署域推进到 `deploying`。失败或回滚保持版本和运行 `ready_for_release`，成功后协作运行才以 `completed(completion_reason=deployed)` 完成，所有部署副作用仍受既有 Outbox、资源授权和人工门禁约束。

---

### TC-AIBRAIN-RD-FUNC-037A: 基础反馈归因、入口与定时作业隔离

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v2.0 |

1. 完成包含审核、返工、门禁与交付反馈的协作运行。
2. 查询业务大脑、产品、运行、反馈类型、来源事件、岗位、席位、真人用户或 AI 数字员工、执行器、工作项、attempt 和策略快照的反馈记录；核对被归因执行主体与 `producer_subject_type/producer_subject_id/producer_role_code/producer_seat_id` 反馈生产者分别持久化，验证复用同一执行器的不同 AI 员工仍分别归因。对同一持久化事件执行顺序重放、并发消费和 Graph checkpoint 失败恢复，另以不同 feedback_kind/归因主体生成反馈；再尝试缺少 source_event、引用另一 collaboration_run 的真实 event、写入不存在的真人/AI 主体、未列入 CHECK 的 service 代码、只填岗位或席位之一、以及岗位与席位不匹配的反馈。
3. 验证 Bug、代码巡检和 AI 助手旧入口只创建/关联需求；需求交付状态批量推进及公开 AI 任务创建/启动/重试/取消返回 `RD_COLLABORATION_REQUIRED`。
4. 在升级前后执行同一现有定时作业并比较表结构可读性、作业定义、触发、锁、重试、AI角色/Skill 快照和运行结果。

**预期结果**: P0 `role_feedback_records` 是不可变、可追溯的基础证据，完整归因到业务大脑、产品、运行、反馈类型、来源事件、岗位、席位、真人用户或 AI 数字员工、执行器、工作项、attempt 和不可变策略快照；实际反馈生产者的主体、岗位和席位独立冻结，不能用被评价对象代替。每条反馈通过 `(collaboration_run_id,source_event_id)` 复合外键引用同一运行的 `rd_collaboration_events`，规范化 fingerprint 覆盖运行代次、事件、反馈类型、归因主体、工作项/attempt 和快照；数据库 `(collaboration_run_id,feedback_fingerprint)` 唯一键使顺序/并发重放只得到一条记录，不同业务反馈仍可分别记录。缺少事件、跨运行事件、不存在/未授权主体、岗位席位半空或不匹配均在事务提交前被数据库拒绝。旧入口不产生可启动 AI 任务，批量状态和公开 AI 任务端点不形成旁路；定时作业表、历史记录、配置、触发、调度、锁、重试和 Agent/Skill 装配语义不变，代码巡检结果动作的业务目标变为需求并单独审计。

---

### TC-AIBRAIN-RD-FUNC-037B: 岗位经验治理与受控复用

| 项目 | 内容 |
| 优先级 | P1 |
| 适用阶段 | v2.0 P1 |

1. 设置 `RD_ROLE_EXPERIENCE_ENABLED=false` 完成一次 P0 协作并检查反馈、路由、候选和上下文；再开启 P1 标志。
2. 由多个 P0 反馈证据生成经验候选，安排一个“不是被评价对象、但确实产生了其中一条反馈”的用户审核，另分别执行 approve/reject/retire、并发旧版本审核和越产品范围审核；在 `require_independent_reviewer=true` 时分别使用来源生产者岗位/席位和独立岗位/席位审核。
3. 按业务大脑、产品、岗位、工作项类型、场景、风险、仓库/工具信任域、最低置信度、状态、版本和证据主体组合查询；使用无权限、跨业务大脑或跨产品账号查询。
4. 分别设置平台标志和冻结策略 `experience_reuse_config.enabled` 的开/关组合，再启动后续同岗位协作；模拟全部范围匹配、空信任域、低置信度、超时效、权限不匹配、跨产品、跨信任域、`same_policy_version/same_policy_schema` 兼容与不兼容以及超过 `max_items/max_context_tokens` 的经验检索注入，并追踪被引用的经验 ID、版本与来源证据。

**预期结果**: P1 标志关闭时 P0 反馈照常落库，经验端点/候选/注入关闭且 P0 套件独立通过。开启后经验候选进入 `pending/approved/rejected/retired` 生命周期，审核校验权限、业务大脑/产品范围、与所有来源反馈生产者隔离及 `review_version`；配置要求独立审核时，来源岗位/席位也不得审核。被拒绝或退役的版本不可复活。查询 API 在服务端执行全部范围和权限过滤，不泄露跨业务大脑/跨产品元数据。只有平台标志与冻结配置同时启用，且经验为 approved、未退役、达到最低置信度并满足业务大脑、产品、岗位、工作项、场景、风险、最大时效、仓库/工具信任域及策略兼容规则时，才能在 `max_items/max_context_tokens` 内带 ID/版本/证据引用进入后续岗位上下文；空信任域按 deny-all，same_policy_schema 也不得跨业务大脑/产品或放宽当前策略。其他经验不注入，经验不能直接修改生产策略、放宽权限或跳过门禁。

---

### TC-AIBRAIN-RD-FUNC-038: 领域事件与 Checkpoint 局部失败恢复

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v2.0 |

1. 写入同一幂等事件，分别模拟领域事务成功但 Checkpoint 失败、Checkpoint 写入后领域命令失败。
2. 重复恢复原 `thread_id` 并重复投递同一事件 ID。

**预期结果**: 领域表和事件 Inbox 决定业务完成状态；Graph 重读领域状态并安全继续；领域状态、审计、Outbox 和岗位反馈不重复，反馈由 source_event 与数据库唯一 fingerprint 保证一次写入，Runner、Git、部署副作用各最多一次，无法兼容的图版本进入人工接管。

---

### TC-AIBRAIN-RD-FUNC-039: 维护围栏与一次性切换

| 项目 | 内容 |
|------|------|
| 优先级 | P0 |
| 适用阶段 | v2.0 |

1. 应用非破坏迁移 109，确认旧字段仍存在且尚未改变运行规则。
2. 在 `fence_mode=disabled` 执行围栏外只读预检，再进入 `draining`，尝试需求 approve/generate、任务 start/retry、策略写入、协作写入、Runner 新领取、已领取任务终态回写、普通取消、管理员 drain 取消和定时作业运行。
3. 在 Schema v2 未激活且 cleanup 未开始时，以正确/过期版本中止 draining；然后再次 draining，待活动任务、Agent Loop、Runner lease 和协作命令归零并写备份标记后进入 `cutover_locked`，重跑锁内预检。分别模拟锁内预检阻断、cutover_locked 后尝试中止、转换成功、新应用健康失败、清理迁移 110 重试、Worker 图版本不一致、v2 写入冒烟失败和全部成功。

**预期结果**: 围栏外 preflight 只读；draining 阻断新增研发写入与 Runner 新领取并返回 `RD_UPGRADE_MAINTENANCE`，但允许在途终态回写和管理员受控取消，不阻断定时作业。合法早期中止审计后恢复旧写路径，过期版本返回 `RD_VERSION_CONFLICT` 且不改变围栏；零活动和备份是进入 cutover_locked 的硬前置，不满足时返回 `RD_UPGRADE_STATE_INVALID`。锁内预检失败不删除旧字段；进入 cutover_locked、Schema v2 激活或 cleanup 开始后，中止返回 `RD_UPGRADE_ABORT_NOT_ALLOWED`，只能向前重试。切换成功后只启用 v2 规则；健康、清理、Worker/Schema/图版本或写入冒烟任一步失败都保持 `cutover_locked`。全部成功后显式置为 disabled，v2 评估和协作写入恢复，旧 approve/generate/batch-delivery-advance/AI-task-create/start 仍永久拒绝。

---
