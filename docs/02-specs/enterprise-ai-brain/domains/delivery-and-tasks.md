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
- 产品模块编辑/删除属于产品配置单记录写入，PostgreSQL/repository 运行态必须按模块 ID 读取源记录；模块编码冲突校验只读取同产品模块列表，删除前通过 repository 检查需求、任务和 Bug 引用。

## 关键 API 与页面

- 需求管理：`/delivery/requirements`
- 迭代版本：`/delivery/versions`
- 研发任务：`/delivery/rd-tasks`
- 需求全链路：`/delivery/requirements/:requirementId/full-chain`
- 核心接口见 [../api.md](../api.md) 的 requirement、task、review、product config、git review 和 export 章节。

## 当前落地要求

- 新增需求可以不指定迭代版本，后续通过批量排期或版本归集进入交付计划。
- 迭代版本推进到开发中、测试中、已发布等阶段时，必须按规则同步包含需求的状态，并提供影响预览。
- 迭代版本代码分支配置属于产品配置子资源；在 PostgreSQL runtime 下，分支配置更新和删除必须按 `branch_config_id` 从 repository 单记录读取源记录，再通过产品配置仓储边界写入变更和审计，不能依赖运行时内存全量集合。
- 需求、任务、版本和 Review 的列表型接口优先在 SQL/repository/read model 层完成筛选、排序和分页。
- 需求全链路必须聚合需求、产品、迭代版本、AI 任务、Review、PR/MR 快照、代码评审、Bug、发布和知识沉淀。

## 验收映射

- 详细验收见 [../test-case.md](../test-case.md) 的 MVP 流程与 [../test-cases/requirements-and-tasks.md](../test-cases/requirements-and-tasks.md)。
