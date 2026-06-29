# 需求交付与研发任务

> 来源：../spec.md。本文承接产品、迭代版本、需求、研发任务和 Review 链路的业务域规格导航。

## 职责边界

- 产品资产提供产品、模块、Git 仓库、关联系统和迭代版本上下文。
- 需求交付负责需求创建、审批、排期、版本归集、状态推进、批量生成任务和需求全链路查看。
- 研发任务负责从需求生成 AI 任务、启动执行、人工确认、补充信息、Mock Issue 写回、知识沉淀和代码评审报告归档。
- 迭代版本状态推进由 `app.services.version_status` 承载，需求状态同步和阻塞规则必须在 domain service 内维护。

## 关键数据

- `products`、`product_versions`、`product_modules`、`product_git_repositories`、`related_systems`
- `requirements`、`ai_tasks`、`human_reviews`、`graph_runs`、`graph_checkpoints`
- `gitlab_mr_snapshots`、`code_review_reports`、`mock_issues`、`knowledge_deposits`
- `product_version_branch_configs` 维护迭代版本关联代码分支。
- 迭代版本与产品模块创建、编辑、删除属于产品配置单记录写入，PostgreSQL/repository 运行态创建时必须按产品 ID 单查产品存在性，版本/模块编码冲突校验只读取同产品版本/模块列表；编辑和删除时必须按版本 ID 或模块 ID 读取源记录，删除版本前通过 repository 检查需求、任务、Bug 和分支配置引用，删除模块前通过 repository 检查需求、任务和 Bug 引用。
- 产品详情、产品编码冲突校验、产品删除引用检查、产品子资源清理、按产品列迭代版本和版本分支配置补全必须通过产品配置 helper 进入 repository-first 读路径；PostgreSQL 运行态使用产品级 `EXISTS` 校验需求、任务和 Bug 引用，测试 fallback 才允许读取 MemoryStore 集合。
- 产品、产品模块、产品 Git 仓库和相关系统路由不得直接写 `current_store` 集合；写入必须通过产品配置单记录 helper，测试环境可落到 MemoryStore fallback，PostgreSQL 运行态必须直接调用 repository，且单记录写入/删除和审计事件在同一数据库事务中提交。
- 产品主体接口必须使用权限点和产品范围双重边界：列表和详情要求 `product.read`，列表按当前用户产品 scope 过滤；创建、更新和删除要求 `product.manage`，创建产品要求全局产品范围，单产品更新和删除按当前用户产品 scope 校验，scope 外统一按 404 隐藏资源存在性。
- 迭代版本与版本分支接口必须使用权限点和产品范围双重边界：版本列表和分支列表要求 `product.read`，创建、更新、状态推进和删除要求 `product.manage`；版本批量列表按当前用户产品 scope 过滤，嵌套产品、单版本和单分支配置均按归属产品校验 scope，新增分支时版本和仓库都必须在 scope 内，scope 外统一按 404 隐藏资源存在性。
- 产品模块接口必须使用权限点和产品范围双重边界：列表接口要求 `product.read`，创建、更新和删除要求 `product.manage`；嵌套在产品下的列表/创建按 URL 产品校验当前用户产品 scope，单模块更新/删除按模块归属产品校验 scope，scope 外统一按 404 隐藏资源存在性。
- 产品 Git 仓库接口必须使用权限点和产品范围双重边界：列表接口要求 `product.read`，创建、更新和删除要求 `product.manage`；嵌套在产品下的列表/创建按 URL 产品校验当前用户产品 scope，单仓库更新/删除按仓库归属产品校验 scope，scope 外统一按 404 隐藏资源存在性。
- 相关系统接口必须使用权限点和产品范围双重边界：列表接口要求 `product.read` 并按当前用户产品 scope 过滤，无产品参数时只返回授权产品相关系统，指定 scope 外产品返回 404；创建、更新和删除要求 `product.manage`，按原归属产品和变更后产品校验 scope，scope 外统一按 404 隐藏资源存在性。
- 迭代版本和版本代码分支配置路由不得直接写 `current_store` 集合；新增、编辑、删除和状态推进必须通过产品配置单记录 helper 或需求记录 helper 写入，测试环境由 helper 落到 MemoryStore fallback，PostgreSQL 运行态通过 repository 单记录写入。需求单记录写入/删除与审计事件必须在同一数据库事务中提交。
- 产品配置上下文公共 helper 的需求单记录和审计事件 fallback 不得直接操作 `current_store.requirements` 或调用 `current_store.audit()`；轻量测试上下文统一通过集合 helper 和审计事件列表 helper 追加，repository 运行态继续由业务写入事务携带审计事件。

## 关键 API 与页面

- 需求管理：`/delivery/requirements`
- 迭代版本：`/delivery/versions`
- 研发任务：`/delivery/rd-tasks`
- 需求全链路：`/delivery/requirements/:requirementId/full-chain`
- 统一需求全链路工作台：`/delivery/full-chain?subject_type=<type>&subject_id=<id>`
- 核心接口见 [../api.md](../api.md) 的 requirement、task、review、product config、git review 和 export 章节。

## 当前落地要求

- 新增需求可以不指定迭代版本，后续通过批量排期或版本归集进入交付计划。
- 需求、Bug、任务、用户洞察、日志监控和迭代版本等表单复用的产品/迭代版本上下文选项必须按服务端分页 `total` 拉取完整可选集合；不得只读取第一页或固定前 100 条，避免产品、目标版本或版本归集入口在数据量增长后不可选。
- 迭代版本推进到开发中、测试中、已发布等阶段时，必须按规则同步包含需求的状态，并提供影响预览。
- 迭代版本驾驶舱必须按版本聚合需求、AI 任务、版本代码分支、Bug、代码巡检、代码评审、知识沉淀、发布记录、状态推进影响和阻塞项，作为版本进入下一阶段前的交付健康视图。入口要求 `product.read` 并按版本归属产品校验 scope；Bug、代码巡检和知识沉淀明细分别按 `bug.read`、`code_inspection.read`、`knowledge.read` 降级隐藏；知识沉淀明细只展示沉淀标题、状态、来源任务、知识文档 ID 和全链路入口，不返回知识正文；页面必须先展示发布准备清单，聚合需求范围、研发任务、代码分支、代码巡检、代码评审、Bug 收敛、知识沉淀、发布证据和状态推进判断，再展示需求/任务/Bug 状态分布，并把状态推进影响拆成同步推进、阻塞和保持不变的需求明细；阻塞项区域必须先按严重级别和来源类型展示处理队列，每条阻塞项必须展示解除条件和处理入口，能直接进入需求、Bug、代码巡检、版本分支或发布记录治理；页面明细表格必须固定列宽并允许横向滚动，避免长文本导致布局变形。
- 迭代版本代码分支配置属于产品配置子资源；在 PostgreSQL runtime 下，分支配置更新和删除必须按 `branch_config_id` 从 repository 单记录读取源记录，再通过产品配置仓储边界写入变更和审计，不能依赖运行时内存全量集合。
- 需求、任务、版本和 Review 的列表型接口优先在 SQL/repository/read model 层完成筛选、排序和分页；其中需求列表必须校验 `requirement.read`，并按当前用户产品 scope 在服务端过滤，PostgreSQL 运行态需将产品 scope 下推到 read model，不能由前端或本地内存二次过滤兜底。
- 需求全链路必须聚合需求、产品、迭代版本、版本代码分支、AI 任务、Review、PR/MR 快照、代码评审、代码巡检、Bug、执行诊断、发布、知识沉淀和审计事件；从 Bug、迭代版本、版本代码分支配置、代码巡检、AI 助手或执行诊断等主体进入统一工作台时，页面必须展示入口主体和已解析需求 ID，避免跨页面跳转后丢失上下文。版本分支入口使用 `product_version_branch_config` / `branch_config` 主体解析回同版本最新需求链路，并继续按产品 scope 校验；执行诊断只返回脱敏 Trace 摘要，阶段明细通过 `source_id + source_type` 跳转执行诊断中心查看完整链路。
- 任务启动、Graph run/checkpoint、代码评审报告和 Review 决策产物属于 DB-first 写路径：Graph、报告、派生 Bug、知识沉淀和审计事件不得直接操作 `current_store` 业务集合或调用 `current_store.audit()`；MemoryStore 仅作为测试 fallback，PostgreSQL 运行态必须通过任务启动/评审决策 repository 事务提交完整产物链路。
- Mock Issue 写回必须通过 `save_mock_writeback_record` 写入结果和审计事件；PostgreSQL 运行态写回结果和审计在同一 repository 事务中提交，并刷新本地读缓存以保持幂等重复提交，MemoryStore 仅作为测试 fallback，不得由服务层直接写 `current_store.mock_writebacks` 或调用 `current_store.audit()`。
- GitLab MR / GitHub PR 快照成功、复用和失败审计必须通过 `save_git_review_snapshot_record` 统一写入；PostgreSQL 运行态快照和审计在同一事务提交，MemoryStore 仅作为测试 fallback，不得由服务层直接写 `current_store.gitlab_mr_snapshots` 或追加 `current_store.audit_events`。

## 验收映射

- 详细验收见 [../test-case.md](../test-case.md) 的 MVP 流程与 [../test-cases/requirements-and-tasks.md](../test-cases/requirements-and-tasks.md)。
