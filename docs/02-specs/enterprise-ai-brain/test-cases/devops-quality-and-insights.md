# 研发运营、质量与用户洞察测试用例

> 来源：../test-case.md。该文件按业务域承接详细测试用例，主入口保留索引与通用规范。

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
2. GitLab 每日指标登记/导入数据包含提交、作者、Merge Request、代码变更量和代码质量审核结果。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 产品负责人、研发负责人或管理员调用 `POST /api/devops/gitlab/daily-code-metrics` 登记每日 GitLab 指标 | 提交、作者、MR、变更量和质量风险写入 `gitlab_daily_code_metrics`。 |
| 2 | GET `/api/devops/gitlab/daily-code-metrics?product_id=product_001&date=2026-05-29` | 返回产品、仓库、日期、提交数量、活跃作者数、质量评分和风险数量。 |
| 3 | 按人员查看作者聚合 | 返回每位作者的提交数、变更行数和代码审核问题数。 |
| 4 | 使用不属于该产品或 inactive 的仓库登记指标 | 返回参数错误，不写入产品级统计。 |

**预期结果**:
1. GitLab 指标必须通过 `product_git_repositories` 归属产品。
2. 产品级统计不混入未归属仓库数据。
3. 指标登记记录 `gitlab_daily_code_metric.created` 审计事件；外部自动采集器接入后仍不得绕过产品归属校验。

**状态**: 已自动化覆盖基础登记、筛选、审计和持久化；外部自动采集器接入后补充采集运行记录验收。

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
1. 系统存在 active 产品，且可选存在 active 产品模块。
2. 有来自线上运行日志采集器、监控平台或人工导入的真实聚合指标，包含请求数、错误数、接口耗时、核心业务事件和 Top Errors。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | `POST /api/ops/online-log-metrics` 登记指定产品、模块、环境和时间窗口的真实聚合指标 | 返回 `online_log_metric_*`，服务端按错误数/请求数计算 `error_rate`，写入 `online_log_metrics` 并记录 `online_log_metric.created` 审计事件。 |
| 2 | GET `/api/ops/online-log-metrics?product_id=product_001&module_code=checkout&environment=prod&from=2026-06-01T00:00:00Z&to=2026-06-01T01:00:00Z` | 返回产品、模块、环境、时间窗口、请求数、错误数、错误率、延迟、核心业务事件和 top_errors。 |
| 3 | 按模块、环境或时间窗口过滤指标 | 仅返回匹配条件的日志聚合结果；没有记录时返回真实空集合。 |
| 4 | 使用 reviewer 角色、无效模块、反向时间窗口或负数指标登记 | 返回 `FORBIDDEN` 或 `VALIDATION_ERROR`/`NOT_FOUND`，不得写入指标或生成兜底数据。 |

**预期结果**:
1. 线上运行日志指标支持按产品、模块、环境和时间窗口查询。
2. 登记写操作必须校验角色、产品/模块归属、时间窗口和计数字段，并记录审计。
3. 核心业务事件和系统健康指标可被首页看板复用；外部自动采集器未接入时也不得生成伪造指标。

**状态**: 已自动化覆盖基础登记、查询、权限、校验和持久化；外部自动采集器端到端按 v1.2 后续补充。

---

### TC-AIBRAIN-RELEASE-FUNC-016: Jenkins 发布数据登记与查询

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-RELEASE-FUNC-016 |
| 用例名称 | Jenkins 发布数据登记与查询 |
| 优先级 | P1 |
| 模块 | DEVOPS |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 产品和版本已存在，且产品处于 active 状态、版本不是 `archived`。
2. 当前用户具备产品负责人、研发负责人或管理员角色。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST `/api/devops/jenkins/releases` 登记成功发布记录 | job、build_id、状态、环境、版本、触发人、耗时和提交号被记录，并写入 `jenkins_release.created` 审计事件。 |
| 2 | GET `/api/devops/jenkins/releases?product_id=product_001&version_id=version_001` | 返回产品版本下的发布记录列表。 |
| 3 | 按 `status=success` 和 `environment=prod` 查询发布 | 返回最近成功部署时间、环境和构建 ID。 |
| 4 | 登记失败发布并查询 `status=failed` | 返回失败原因，不覆盖最近成功发布信息。 |

**预期结果**:
1. Jenkins 发布记录必须按产品和版本归属。
2. 发布失败原因可用于首页看板风险摘要。
3. 发布记录可关联 GitLab 提交、需求、AI 任务或线上日志事件。
4. 记录必须持久化到 `jenkins_release_records`，无记录时返回真实空集合，不生成兜底数据。
5. archived 版本不得继续登记发布记录。

**状态**: 已自动化覆盖基础登记、筛选、审计和持久化；外部自动采集器接入后补充采集运行记录验收。

---

### TC-AIBRAIN-DEVOPS-FUNC-023: 采集运行记录登记与更新

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DEVOPS-FUNC-023 |
| 用例名称 | 采集运行记录登记与更新 |
| 优先级 | P1 |
| 模块 | DEVOPS |
| 创建人 | Codex |
| 创建日期 | 2026-06-02 |

**前置条件**:
1. 产品已存在且处于 active 状态。
2. 当前用户具备产品负责人、研发负责人或管理员角色；另准备 reviewer/viewer 角色用于越权验证。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/collectors/runs` | 无数据时返回 `items=[]`、`total=0`，不返回示例采集运行。 |
| 2 | POST `/api/collectors/runs` 登记 `gitlab_daily_code_metric` 运行 | 返回 `collector_run_*`，写入 `collector_runs`，并记录 `collector_run.created` 审计事件。 |
| 3 | PATCH `/api/collectors/runs/{run_id}` 标记 `succeeded` 并设置 `records_imported` | 自动补齐 `finished_at`，记录 `collector_run.updated` 审计事件。 |
| 4 | PATCH 已终态运行回 `running` | 返回 `COLLECTOR_RUN_STATE_INVALID`。 |
| 5 | 登记或更新 `failed` 但不提供 `error_message` | 返回 `VALIDATION_ERROR`。 |
| 6 | reviewer/viewer 尝试 POST/PATCH | 返回 `FORBIDDEN`。 |
| 7 | 在研发运营页面打开“采集运行记录”，登记运行并标记成功 | 页面调用 `/api/collectors/runs`，刷新后仍展示真实持久化运行记录。 |

**预期结果**:
1. 采集运行记录只记录采集尝试和结果，不自动生成 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议数据。
2. `collector_runs` 可从 PostgreSQL 结构表恢复，`collector_run` 计数器可延续。
3. 运行列表支持按采集类型、产品、状态和来源系统筛选。

**状态**: 已自动化覆盖 API、权限、审计、持久化和前端页面操作；见 `apps/api/tests/test_collector_runs.py`、`apps/api/tests/test_database_persistence.py::test_collector_runs_are_persisted_through_fine_grained_repository_payload` 和 `apps/web/tests/App.test.tsx` collector run 用例。

---

### TC-AIBRAIN-SCHED-FUNC-031: AI 能力配置与定时作业装配

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-SCHED-FUNC-031 |
| 用例名称 | AI 能力配置与定时作业装配 |
| 优先级 | P1 |
| 模块 | SCHEDULER / AI_CAPABILITY |
| 创建人 | Codex |
| 创建日期 | 2026-06-10 |

**前置条件**:
1. 系统已配置 active 模型网关。
2. 当前用户为管理员；另准备产品负责人、研发负责人和 viewer 角色用于越权验证。
3. 存在 active 产品、用户反馈、用户使用指标、Bug 或线上日志证据。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 管理员调用 `POST /api/system/ai-skills` 创建 `iteration_planning` Skill | 写入 `ai_skills`，返回输入/输出 schema、允许工具、所需上下文、人工确认要求和 active 状态；不包含任何密钥。 |
| 2 | 管理员调用 `POST /api/system/ai-skills/upload` 上传包含 `skill.yaml` 和 `SKILL.md` 的 zip Skill 包 | 写入 package 类型 Skill，返回 `package_uri`、`package_checksum`、`manifest`、`package_entry` 和文件清单；本地文件落盘，记录 `ai_skill.package_uploaded` 审计。 |
| 3 | 管理员调用 `POST /api/system/ai-agents/upload` 上传包含 `agent.yaml` 和 `AGENT.md` 的 zip Agent 包，绑定默认模型网关和上一步 Skill | 写入 package 类型 `ai_agents`，返回 `source_type=package`、默认 Skill、模型网关、`package_uri`、`package_checksum`、`manifest`、运行边界和 active 状态；记录 `ai_agent.package_uploaded` 审计。 |
| 4 | 管理员调用 `POST /api/system/ai-agents` 创建 `agent_iteration_planner`，绑定默认模型网关和上一步 Skill | 写入 inline 类型 `ai_agents`，返回默认 Skill、执行策略、工具策略和 active 状态；记录 `ai_agent.created` 审计。 |
| 5 | 管理员调用 `POST /api/system/scheduled-jobs` 创建 `iteration_plan_suggestion_generate` 作业，设置 cron、Agent、Skill、execution_mode=`ai_generated` | 写入 `scheduled_jobs`，计算 `next_run_at`，记录作业配置和 `scheduled_job.created` 审计。 |
| 6 | 管理员进入 AI 能力配置页，分别在 AI角色和 Skill 管理页签使用关键词、状态、模型网关、来源或人工确认查询，并保存本地筛选视图 | 两个页签均复用统一管理列表底座，保留新增/编辑/停用、Agent 包上传和 Skill 包上传入口；筛选仅影响当前列表，本地视图分别按页签保存；文件包脚本展示为“不自动执行”。 |
| 7 | 产品负责人或 viewer 尝试创建/修改 Agent、Skill 或系统级定时作业 | 返回 `FORBIDDEN`，不得写入配置或审计成功事件。 |
| 8 | 停用 Skill 后再次启用引用该 Skill 的定时作业 | 返回配置校验错误，提示引用的 Skill 不可用。 |

**预期结果**:
1. Agent/Skill 作为平台级配置独立维护，普通业务用户不能修改 Prompt、工具策略或模型网关。
2. 定时 AI 作业只能引用 active Agent、active Skill 和 active 模型网关。
3. 配置变更必须写审计，API 响应不泄露密钥、外部系统 token 或完整历史 prompt 输出。

**状态**: 基础自动化已覆盖 Agent/Skill/定时作业配置、Agent/Skill 包上传、管理员写入和非管理员拒绝；周期 worker 自动扫描和抢锁调度另行补充集成用例。

---

### TC-AIBRAIN-PLUGIN-FUNC-032: 插件管理与定时任务插件调用

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-PLUGIN-FUNC-032 |
| 用例名称 | 插件管理与定时任务插件调用 |
| 优先级 | P1 |
| 模块 | PLUGIN / SCHEDULER |
| 创建人 | Codex |
| 创建日期 | 2026-06-10 |

**前置条件**:
1. 当前用户为管理员；另准备 reviewer 或 viewer 用于越权验证。
2. 系统已存在可用于测试的 HTTP 或 MCP HTTP 三方系统 endpoint；自动化测试可使用 `mock_response_json` 替代真实网络。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 非管理员调用 `POST /api/system/plugins` | 返回 `FORBIDDEN`，不得写入插件配置。 |
| 2 | 管理员创建 `integration_plugins`、`plugin_connections` 和 `plugin_actions` | 返回 active 插件、连接和动作；连接响应对 `secret_ref/token/api_key/password` 等字段脱敏；分别写入 `plugin.created`、`plugin_connection.created`、`plugin_action.created` 审计。 |
| 3 | 管理员从列表编辑插件、连接和动作 | 编辑弹窗回填现有配置；连接和动作 Params/Headers 可继续可视化维护；PATCH 保存后写入更新审计；提交脱敏占位 `***` 时保留服务端原始密钥。 |
| 4 | 管理员手动调用 `POST /api/system/plugin-actions/{action_id}/invoke` | 创建 `plugin_invocation_logs`，记录请求摘要、响应摘要、状态、耗时和 trace_id；日志不保存明文密钥。 |
| 5 | 管理员创建 `job_type=plugin_action_invoke` 的定时作业并引用 `plugin_action_id` | 定时作业保存插件动作、可选连接覆盖、输入映射和输出映射；记录 `scheduled_job.created` 审计。 |
| 6 | 手动触发该定时作业 | 运行实例保存 `resolved_plugin_snapshot`、`plugin_invocation_log_id`、`result_summary.plugin` 和 records_imported 映射结果；关联 collector run 和审计事件。 |
| 7 | 选择“MaxCompute 每周用户反馈”动作模板，创建 `job_type=user_feedback_insight_extract` 定时作业并手动运行 | 页面生成 MCP 查询 JSON 且允许高级 JSON 编辑；运行实例从 `$.insights` 读取洞察，通过用户反馈 service 写入用户洞察表，`records_imported` 等于新增洞察数。 |
| 8 | 定时作业通过 `plugin_connection_ids` / `plugin_action_ids` 多选数组引用插件连接或动作后，在插件管理页删除对应连接或动作 | 删除前端阻断并展示“正在使用”提示和占用定时作业名称，不调用 DELETE 接口；旧单值 `plugin_connection_id` / `plugin_action_id` 引用也必须保持同样保护。 |
| 9 | 插件协议为 `mcp_stdio` 时尝试执行 | 返回 `PLUGIN_PROTOCOL_UNSUPPORTED`，第一阶段不得执行未隔离的本地命令。 |

**预期结果**:
1. 插件管理负责“调哪个三方动作、用哪个连接、如何审计”，AI Skill 只负责消费插件返回数据进行语义分析。
2. 插件连接密钥和调用日志均不得泄露明文凭据。
3. 定时任务调用插件动作必须可追溯到作业定义、插件快照、调用日志和审计事件；插件、连接和动作删除保护必须识别定时作业单值与数组型引用。

**状态**: 基础自动化已覆盖插件/连接/动作 CRUD 与编辑维护、密钥脱敏占位保留、审计、mock HTTP 插件调用、定时作业插件快照、调用日志，以及 MaxCompute 每周用户反馈洞察抽取；插件页多连接/多动作定时作业占用删除保护见 `apps/web/tests/PluginsPage.test.tsx`。

---

### TC-AIBRAIN-SCHED-FUNC-032: 定时 AI 作业运行、快照与失败处理

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-SCHED-FUNC-032 |
| 用例名称 | 定时 AI 作业运行、快照与失败处理 |
| 优先级 | P1 |
| 模块 | SCHEDULER / USER_INSIGHTS |
| 创建人 | Codex |
| 创建日期 | 2026-06-10 |

**前置条件**:
1. 已存在 active `iteration_plan_suggestion_generate` 定时作业，绑定 active Agent、Skill 和模型网关。
2. 系统有可用于生成建议的真实用户反馈、Bug、用户使用或线上日志证据。
3. scheduler worker 可运行；测试环境可通过手动触发替代真实时间等待。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 调用 `POST /api/system/scheduled-jobs/{job_id}/run` 手动触发作业 | 创建 `scheduled_job_runs`，状态为 `queued` 或 `running`，生成关联 `collector_runs`，记录 trigger_type=`manual`。 |
| 2 | worker 执行作业 | 运行实例保存 `config_snapshot`、`resolved_agent_snapshot`、`resolved_skill_snapshots`、`resolved_prompt_snapshot` 和 `tool_policy_snapshot`；package 类型 Skill 额外保存从本地文件加载出的 `package_snapshot.entry_content`；模型调用走模型网关并写模型日志元数据。 |
| 3 | AI 输出通过 schema 校验 | 写入 `iteration_plan_suggestions` 候选建议和审计事件，运行状态变为 `succeeded`，collector run 同步为 `succeeded` 并记录 `records_imported`。 |
| 4 | 产品负责人通过现有迭代建议确认接口采纳或驳回 | 只有确认后才可转正式需求；定时作业本身不得自动创建正式需求或变更迭代排期。 |
| 5 | 模型网关失败或 Skill 输出 schema 不合法 | 运行状态变为 `failed`，记录 `error_code/error_message`，collector run 同步失败；不会写入伪造建议。 |
| 6 | 配置 `max_retry_count>0` 后重试失败运行 | 系统创建新的运行实例，保留原失败历史，不覆盖旧 run；达到最大重试次数后停止自动重试。 |
| 7 | 两个 worker 同时扫描同一 due job | 只有一个 worker 成功获得锁租约并创建有效 running 实例；另一个 worker 跳过或拿不到租约，不重复写业务数据。 |

**预期结果**:
1. 定时 AI 作业运行可追溯到作业定义、collector run、模型日志、AI 配置快照和最终候选业务结果。
2. AI 生成类作业只生成建议或候选，不绕过人工确认。
3. 失败、超时、取消和锁竞争都有明确状态和审计，不生成占位数据。

**状态**: 基础自动化已覆盖手动触发、配置快照、本地 Skill 文件加载、collector run 关联和 AI 迭代建议生成；周期触发、重试退避和抢锁冲突另行补充集成用例。

---

### TC-AIBRAIN-ATTRIBUTION-FUNC-024: 待归属数据队列登记与处理

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-ATTRIBUTION-FUNC-024 |
| 用例名称 | 待归属数据队列登记与处理 |
| 优先级 | P1 |
| 模块 | ATTRIBUTION |
| 创建人 | Codex |
| 创建日期 | 2026-06-02 |

**前置条件**:
1. 系统存在 active 产品，可选存在产品模块和需求。
2. 当前用户具备产品负责人、研发负责人或管理员角色；另准备 reviewer/viewer 角色用于越权验证。
3. 可选存在 `collector_runs` 记录，用于验证采集运行来源追踪。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/attribution/pending-items` | 无数据时返回 `items=[]`、`total=0`，不返回示例待归属项。 |
| 2 | POST `/api/attribution/pending-items` 登记 `user_feedback` 待归属项 | 返回 `pending_attr_*`，状态为 `pending`，写入 `pending_attribution_items`，并记录 `pending_attribution.created` 审计事件。 |
| 3 | GET 按 `source_type/status/collector_run_id` 筛选 | 仅返回匹配的真实队列项。 |
| 4 | POST `/api/attribution/pending-items/{item_id}/resolve`，`resolution_action=link_existing_context` | 状态变为 `resolved`，保存 resolved_product/module/requirement/subject 字段，并记录 `pending_attribution.resolved` 审计事件。 |
| 5 | POST 另一个队列项，`resolution_action=ignore_as_noise` | 状态变为 `ignored`，不允许携带归属上下文字段，并记录 `pending_attribution.ignored` 审计事件。 |
| 6 | 对 `resolved` 或 `ignored` 项再次 resolve | 返回 `PENDING_ATTRIBUTION_STATE_INVALID`。 |
| 7 | reviewer/viewer 尝试 POST 或 resolve | 返回 `FORBIDDEN`。 |
| 8 | 在研发运营页面打开“待归属数据队列”，归属或忽略队列项 | 页面调用真实接口，处理后刷新列表，不生成任何指标或反馈行。 |

**预期结果**:
1. 待归属队列只记录无法自动映射的真实导入事实和人工处理结果。
2. 处理动作不自动生成 GitLab/Jenkins/线上日志/用户使用/用户反馈/迭代建议/需求等业务数据。
3. `pending_attribution_items` 可从 PostgreSQL 结构表恢复，`pending_attr` 计数器可延续。

**状态**: 已自动化覆盖 API、权限、审计、持久化和前端页面操作；见 `apps/api/tests/test_pending_attribution.py`、`apps/api/tests/test_database_persistence.py::test_pending_attribution_items_are_persisted_through_fine_grained_repository_payload` 和 `apps/web/tests/App.test.tsx` 待归属队列用例。

---

### TC-AIBRAIN-DIAGNOSTICS-FUNC-032: 执行诊断中心统一运行链路

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-DIAGNOSTICS-FUNC-032 |
| 用例名称 | 执行诊断中心统一运行链路 |
| 优先级 | P0 |
| 模块 | DIAGNOSTICS |
| 创建人 | Codex |
| 创建日期 | 2026-06-23 |

**前置条件**:
1. 存在一次真实或测试构造的定时作业运行，关联插件调用、AI 执行器任务、模型网关日志、代码巡检报告和审计事件；另准备一次 AI 助手聊天运行，关联模型网关日志和失败审计事件。
2. 管理员具备 `diagnostics.execution_traces.read` 权限；准备 reviewer 等普通角色用于越权验证。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 管理员 GET `/api/governance/execution-traces` | 返回按运行根聚合的链路列表，包含 root_type、status、node_count、failed_node_count、duration_ms、started_at、updated_at、related_ids 和 `diagnostic_nodes`；成功链路的 `diagnostic_nodes` 为空数组。 |
| 2 | 使用 `scheduled_job_run_id`、`plugin_invocation_log_id`、`result_write_record_id` 或任一节点 `source_id` GET `/api/governance/execution-traces/{trace_id}` | 返回同一条详情链路，nodes 至少覆盖定时作业运行、阶段节点、插件调用、AI 执行器任务、模型网关日志、代码巡检报告、结果写入记录和审计事件，edges 展示 invokes/dispatches/writes_report/writes_result/audits 等关系。 |
| 3 | 管理员 GET `/api/governance/execution-traces?source_type=assistant_chat_run`，再用关联的 `model_gateway_log_id` 打开详情 | 返回 `root_type=assistant_chat_run` 的链路，nodes 至少覆盖 AI 助手运行、模型网关日志和审计事件，edges 展示 `calls_model` 和 `audits`，详情不返回完整用户提问、助手回复、Prompt 或知识正文。 |
| 4 | 管理员 GET `/api/governance/execution-traces?source_id={model_gateway_log_id}&source_type=model_gateway_log`、`source_type=result_write_record&source_id={result_write_record_id}`、`source_type=scheduled_job_stage&source_id={run_id}:{stage_id}` 或 `source_type=ai_executor_runner&source_id={runner_id}`，并打开 `/governance/execution-traces?source_id={model_gateway_log_id}&source_type=model_gateway_log` | 列表只返回该来源 ID 所属链路；Runner 过滤返回包含对应 `ai_executor_runner` 节点的运行链路，任务节点通过 `assigned_runner` 关联 Runner 且不暴露 `token_hash`；前端深链必须同时携带 `source_id` 与 `source_type`，命中唯一链路时自动打开详情弹窗，便于从模型网关、插件、Runner、定时作业阶段、结果写入记录、代码巡检或 AI 助手页面跳转排障。 |
| 5 | 打开包含失败、取消、运行中或排队节点的执行诊断详情 | 详情响应 `diagnostic_nodes` 返回异常/运行中节点安全摘要且不包含 metadata；详情顶部展示“诊断建议”，优先按该摘要汇总异常节点，提供来源 ID 深链和“问 AI”入口；成功链路展示无失败节点提示。 |
| 6 | 在插件请求摘要、执行器 request_config 或审计 payload 中放入 token/API key/Authorization | 响应详情 metadata 中敏感值统一为 `<redacted>`，不得泄露明文 token、API key、cookie、password 或 secret。 |
| 7 | reviewer 调用列表或详情接口 | 返回 `403 FORBIDDEN`，不暴露运行链路。 |
| 8 | 打开运营治理 / 执行诊断页面 | 页面使用服务端分页、排序和筛选；列表显示规范化北京时间、状态、耗时、节点数和首个诊断节点摘要；成功链路展示无异常节点，失败或运行中链路可在列表层看到优先排查的来源、状态和错误摘要；点击详情弹窗展示关联对象、节点表、节点关系表，长文本和 JSON 不撑坏布局。 |
| 9 | 在 repository 快照已刷新的短 TTL 内连续查询列表和已存在详情，再新增一条 AI 助手运行并用其模型日志 ID 打开详情 | 连续列表和已存在详情复用快照，不重复全量刷新；新链路详情未命中旧快照时强制重建并返回最新聚合链路。 |

**预期结果**:
1. 执行诊断只读聚合已有运行事实，不新增业务写入事实源。
2. 诊断入口能把作业运行失败排障需要的插件、执行器、模型、巡检报告、AI 助手运行和审计线索放在同一视图中。
3. 所有响应必须脱敏敏感配置和值，`diagnostic_nodes` 不返回完整节点 metadata，权限由后端强制校验。
4. `execution_trace_snapshots` 是可重建读模型；短 TTL 只能用于降低重复读取成本，详情未命中必须刷新后再判断不存在。

**状态**: 已新增后端和前端自动化覆盖；见 `apps/api/tests/test_execution_traces.py` 与 `apps/web/tests/ExecutionTracesPage.test.tsx`。

---

### TC-AIBRAIN-CODEINSPECTION-FUNC-033: 代码巡检 finding 误报忽略审批

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-CODEINSPECTION-FUNC-033 |
| 用例名称 | 代码巡检 finding 误报忽略审批 |
| 优先级 | P0 |
| 模块 | CODE_INSPECTION |
| 创建人 | Codex |
| 创建日期 | 2026-06-24 |

**前置条件**:
1. 已存在一次 `code_repository_inspection` 定时作业运行，写入 `code_inspection_reports` 和至少一条 `code_inspection_findings`。
2. 管理员具备代码巡检读取与治理权限；另准备可查看页面的普通角色用于只读边界验证。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET `/api/governance/code-inspections/{report_id}` | `findings[]` 返回 `suppression_status=none` 以及 suppression 申请/审批字段；详情页展示“忽略审批”和“治理操作”列。 |
| 2 | POST `/api/governance/code-inspections/{report_id}/findings/{finding_id}/suppression-request`，reason=`false_positive` | finding 进入 `pending`，记录申请人、申请时间和申请说明；写入 `code_inspection_finding_suppression.requested` 审计事件。 |
| 3 | POST `/api/governance/code-inspections/{report_id}/findings/{finding_id}/suppression-review`，decision=`approve` | finding 进入 `approved`，记录审批人和审批时间；报告 `suppressed_finding_count` 加 1，`suppression_summary.false_positive` 加 1；写入 `code_inspection_finding_suppression.approved` 审计事件。 |
| 4 | 对同一 finding 再次提交审批 | 返回 409，不重复增加 suppression 统计，也不重复写成功审批。 |
| 5 | GET `/api/governance/code-inspections/dashboard?product_id=...` | `rule_governance.suppression_distribution` 包含 `false_positive=1`，页面“规则包与误报治理”同步显示。 |
| 6 | 在 `/governance/code-inspections` 打开报告详情，点击“申请忽略”再点击“批准忽略” | 页面调用真实 suppression API，按钮 loading 不影响其它行操作，审批状态从“未申请”更新为“待审批”再更新为“已忽略”，长问题/建议/位置不撑坏表格。 |

**预期结果**:
1. 逐条 finding 的误报/忽略必须经过服务端状态机和审计，不得只靠前端隐藏或静态配置过滤。
2. 审批通过后的统计必须同时影响报告详情和治理概览，便于后续治理误报率和规则质量。
3. 重复审批、无效 reason 或非 pending 审批必须返回明确错误，避免统计重复累加。

**状态**: 后端和前端自动化覆盖见 `apps/api/tests/test_code_inspection_governance.py::test_code_inspection_finding_suppression_approval_updates_report_governance` 与 `apps/web/tests/CodeInspectionsPage.test.tsx::requests and approves a finding suppression from the detail dialog`；真实页面 smoke 按 `/governance/code-inspections` 验证。

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
| 1 | 打开首页 IT 团队看板 | 展示真实需求、研发进展、待确认 Review、知识沉淀、审计、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈和迭代建议摘要。 |
| 2 | GET `/api/dashboard/it-team?product_id=product_001&time_range=7d` | 返回同一产品维度下的需求、任务、Review、知识、审计、Bug、DevOps、线上日志和用户洞察聚合指标，其他产品数据不计入当前产品，运营类指标按可解析时间窗口过滤；PostgreSQL 运行时读取 repository source rows 后可由 Python 完成展示聚合；响应包含 `metadata.dashboard_cache.cache_hit=false`、生成时间、TTL、耗时和慢查询阈值。 |
| 3 | 按产品和时间范围切换筛选 | 看板所有卡片同步切换产品归属和时间范围。 |
| 4 | 从 Bug、研发运营、用户洞察或审计卡片下钻 | 跳转到对应主体列表或明细，并保留产品和时间范围上下文。 |
| 5 | 在短 TTL 内再次 GET 同一产品、时间窗口和角色维度看板 | 返回聚合结果，`metadata.dashboard_cache.cache_hit=true`，不重复写入新的看板快照。 |
| 6 | GET `/api/dashboard/it-team?product_id=product_001&time_range=7d&refresh=true` | 强制绕过并清除当前查询维度缓存，重新读取 source rows、写入新快照，返回 `cache_hit=false`。 |

**预期结果**:
1. 首页只展示聚合和风险摘要，明细下钻到对应主体页面。
2. 看板指标来源可追溯到需求、任务、Bug、GitLab、Jenkins、线上日志、用户使用、用户反馈、迭代规划建议、知识沉淀和审计事件；看板不强制 SQL/物化 read model，但不得把聚合容器作为写入事实源。
3. 看板缓存仅作为 PostgreSQL source rows 派生的只读优化，必须可通过 `refresh=true` 绕过；接口耗时超过阈值时记录 `slow_dashboard_query`。
4. 无数据产品展示空状态，不报 500。

**状态**: 已自动化覆盖。后端聚合见 `apps/api/tests/test_empty_collections.py::test_dashboard_it_team_returns_real_mvp_aggregate_without_fake_rows`；dashboard API 只能由独立 `app.api.routers.dashboard` 注册且路由不可重复，见 `apps/api/tests/test_router_boundaries.py::test_dashboard_endpoint_is_owned_by_dashboard_router`；前端产品/时间筛选、运营卡片和下钻链接见 `apps/web/tests/App.test.tsx::renders dashboard and operation pages without placeholder data`、`apps/web/tests/App.test.tsx::reloads the dashboard with a selected product filter` 与 `apps/web/tests/App.test.tsx::fetches the dashboard with product and time range query parameters`；看板快照 handler 级写入结构表、禁用请求结束持久化后重建仍可恢复见 `apps/api/tests/test_database_persistence.py::test_lifecycle_and_dashboard_handlers_write_repository_without_request_persist`；运行时 store 过期时看板和生命周期上下文均读取 repository source rows；看板单条写入 dashboard snapshot，生命周期上下文写回 lifecycle edges/risks，见 `apps/api/tests/test_database_persistence.py::test_lifecycle_and_dashboard_use_repository_source_rows_when_runtime_store_is_stale`，该回归同时覆盖首次查询 `cache_hit=false`、二次查询 `cache_hit=true` 和 `refresh=true` 强刷；GET 请求结束不会把过期运行时 store 持久化覆盖 repository 见 `apps/api/tests/test_database_persistence.py::test_repository_read_snapshot_get_does_not_persist_stale_runtime_store`。

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
| 2 | 在 Bug 管理工作台点击“登记 Bug”，source=`manual_test`，选择同产品 `testing` 目标版本并提交 POST `/api/bugs` | 目标版本下拉展示同产品未归档版本，包括 `testing` 和 `released`，不展示 `archived`；Bug 创建成功，来源为人工测试并保存所选 `version_id`。 |
| 3 | PATCH `/api/bugs/{id}` 补充复现步骤并分派处理人 | 状态按 `needs_info -> triaged -> assigned` 或 `open -> assigned` 合法流转。 |
| 4 | PATCH `/api/bugs/{id}` 标记 fixed/verified/closed | Bug 完成修复、验证和关闭。 |
| 5 | 创建重复 Bug 并设置 duplicate_of_bug_id | 重复 Bug 关联主 Bug，不重复进入修复队列。 |
| 6 | GET `/api/bugs?product_id=...&version_id=...` 并打开 Bug 管理工作台 | 接口只返回目标版本 Bug，列表项包含 `version_code`、`version_name` 和 `created_at`；页面展示迭代版本列和创建时间列，并可按版本名/编码或“未关联”查询。 |
| 7 | 在 Bug 管理工作台编辑 Bug | 弹窗展示后端返回的复现步骤、证据 JSON、重复归并和只读来源；保存时 PATCH `reproduce_steps`、`evidence`、`duplicate_of_bug_id`、状态和处理人，不生成本地兜底数据。 |
| 8 | 在 Bug 管理工作台勾选多条 Bug，点击“批量处理”，填写状态、严重级别或处理人后提交 POST `/api/bugs/batch-update` | 合法 Bug 按状态机批量更新；重复 ID、不存在 ID 或非法状态流转进入 `skipped` 明细，不阻塞其他记录；响应包含 `batch_id`、`updated_count`、`skipped_count`；前端结果弹窗展示批次号、更新数、跳过数和 skipped 原因；写入 `bug.batch_updated` 和逐条 `bug.updated` 审计。 |
| 9 | 使用无写权限角色 POST `/api/bugs` 或 `/api/bugs/batch-update` | 返回 `FORBIDDEN`，不创建或更新 Bug。 |

**预期结果**:
1. Bug 必须归属产品，可关联版本、模块、需求、任务、提交、发布或线上日志事件，列表可直接判断和查询归属迭代版本。
2. AI 自动测试和人工测试登记来源可区分。
3. Bug 状态流转、重复归并、批量处理和越权拦截写入或保留可追溯审计语义。

**状态**: 已自动化覆盖 API 状态机、批量处理、PostgreSQL 持久化、独立 bugs router 归属和前端 Bug 工作台字段闭环；Bug 生命周期 service 层单测见 `apps/api/tests/test_bug_lifecycle_service.py`，批量处理见 `apps/api/tests/test_bug_management.py::test_bug_batch_update_updates_eligible_bugs_and_records_audit`，路由归属见 `apps/api/tests/test_router_boundaries.py::test_bug_management_endpoints_are_owned_by_bugs_router`，页面批量处理与结果明细弹窗见 `apps/web/tests/App.test.tsx::batch updates selected bugs from the bug management page`；仍需在集成环境补充真实测试组织角色。

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
1. 存在已排期需求、产品上下文、代码 diff、测试结果、Jenkins 发布记录和线上日志样本。
2. 当前用户具备创建和启动 AI 任务权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 从已确认产品详细设计创建 `technical_solution`，再从已确认技术方案创建 `development_planning` | 均返回 `task_type`，并保留需求快照和产品上下文。 |
| 2 | 创建 `code_review` 任务并传入 MR/PR diff 快照 | 输出结构化 Review 报告、风险等级、文件/行号、修改建议和执行器元数据。 |
| 3 | 从已确认技术方案创建并启动 `automated_testing` 任务 | 输出测试分析和 Bug 建议；未确认前不创建 Bug，确认后生成来源为 `ai_auto_test` 的 Bug 记录。 |
| 4 | 从已确认技术方案创建并启动 `release_readiness` 任务 | input 包含源技术方案、Bug、Jenkins 发布记录、线上日志指标和 GitLab 每日代码指标真实快照；输出上线检查清单、发布风险评估和回滚建议。 |
| 5 | 从已确认发布评估创建并启动 `post_release_analysis` 任务 | input 包含源发布评估、发布记录、线上日志和 Bug 真实快照；输出上线后健康报告、异常趋势和疑似回归 Bug。 |

**预期结果**:
1. 已实现任务类型复用统一任务状态机、人工确认、审计和详情查询能力；`release_readiness` 和 `post_release_analysis` 已纳入当前自动化切片。
2. v1 系列不自动改代码、不自动提交 PR、不自动部署上线。
3. 自动化测试和上线后分析产生的 Bug 必须进入 Bug 管理闭环。

**状态**: development_planning / automated_testing / release_readiness / post_release_analysis 自动化通过。2026-06-03 使用 AI 助手聊天界面真实需求复跑时，`task_066` development_planning 完成，`task_067` automated_testing 首次模型失败后以 `task_068` 完成，`task_070` release_readiness 在同任务重试能力上线后可重新触发但上游模型仍失败，post_release_analysis 因缺少已完成发布评估未继续；该批次用于验证失败重试和外部模型稳定性风险。

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
| 4 | 查询任务详情；若为 `automated_testing`，查询 `/api/bugs?source=ai_auto_test` | 任务完成；自动化测试输出的 Bug 建议已转为真实 Bug 记录并关联需求和任务。 |

**预期结果**:
1. v1.1 研发扩展任务的高影响结论均受人工确认门禁保护。
2. 自动化测试任务生成 Bug 建议时，进入 Bug 管理前保留产品归属和复现信息要求。

**状态**: 自动化通过；Graph Run 列表、待确认 Review 列表和 Review 详情 read handlers 已补充不得回调 legacy main 的架构边界回归，见 `apps/api/tests/test_router_boundaries.py::test_task_workflow_read_handlers_do_not_call_legacy_main`；取消任务和补充信息提交 write handlers 已补充不得回调 legacy main 的架构边界回归，见 `apps/api/tests/test_router_boundaries.py::test_task_state_write_handlers_do_not_call_legacy_main`；DB-first no-persist 写入契约见 `apps/api/tests/test_database_persistence.py::test_cancel_and_submit_more_info_write_task_state_without_request_persist`；Graph/Review 详情投影流程回归见 `apps/api/tests/test_graph_runtime.py::test_starting_task_creates_graph_run_checkpoint_and_task_detail_projection` 和 `apps/api/tests/test_review_actions.py`。

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
| 3 | POST `/api/reviews/{id}/approve` 或 `/edit-approve` | 保存人工确认或人工修改后的确认内容。 |
| 4 | 查询任务结果；若为 `post_release_analysis`，查询 `/api/bugs?source=ai_post_release` | 任务基于确认后的内容完成；上线后分析输出的 Bug 建议已转为真实 Bug 记录并关联需求和任务。 |

**预期结果**:
1. 发布上线评估和上线后分析不能绕过人工确认。
2. 系统只给出风险判断和建议，不自动部署上线；上线后疑似回归进入 Bug 管理闭环。

**状态**: 自动化通过

---

### TC-AIBRAIN-REVIEW-FUNC-023A: MVP-A GitLab MR / GitHub PR 预览和 diff 快照

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-023A |
| 用例名称 | MVP-A GitLab MR / GitHub PR 预览和 diff 快照 |
| 阶段内优先级 | P0 |
| 适用阶段 | MVP-A |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 产品已绑定 GitLab/GitHub 代码库；GitLab 提供可解析的 `remote_url` 或 `GITLAB_BASE_URL`，GitHub 提供 `project_path=owner/repo` 或可解析 owner/repo 的 `remote_url`，并通过环境变量、服务端密钥引用或本地直填只读 token 提供凭据；当前用户具备该产品和 MR/PR 的 Review 权限。
2. 存在已排期需求、已确认产品详细设计和已确认技术方案。
3. 远端存在可访问 Merge Request 或 Pull Request，且 diff 未超过 v1 MVP 限制。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GitHub 仓库 GET `/api/devops/github/pull-requests/{repository_id}?state=all&limit=20` | 返回当前凭据可访问 PR 列表、分支、作者、更新时间和 `writeback_allowed=false`；无 PR 时返回真实空集合。 |
| 2 | GET GitLab `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview` 或 GitHub `/api/devops/github/pull-requests/{repository_id}/{pr_number}/preview` | 返回 MR/PR 标题、作者、source/head branch、target/base branch、changed_file_count、changed_files_summary、diff_refs、web_url、diff_file_tree、risk_summary 和 review_checklist。 |
| 3 | POST GitLab `/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot` 或 GitHub `/api/devops/github/pull-requests/{repository_id}/{pr_number}/snapshot` | 返回 snapshot_id、diff_size_bytes、diff_limit 和 created_at；快照不受后续 MR/PR 变更静默影响。 |
| 4 | 再次拉取相同 diff | 返回已有 snapshot_id，不重复写入 `gitlab_mr_snapshots`，并记录 `gitlab_mr.snapshot_reused` 或 `github_pr.snapshot_reused` 审计事件。 |
| 5 | 输入超过 diff 字节数、变更文件数或单文件 diff 行数限制的 MR/PR | 返回 `GITLAB_MR_DIFF_TOO_LARGE`，不得静默截断后继续；审计包含 `*.snapshot_failed`、`diff_size_bytes`、`diff_limit_bytes`、`changed_file_count`、`changed_file_limit`、`file_diff_line_count` 或 `file_diff_line_limit`。 |
| 6 | 移除 GitLab/GitHub base URL 或只读 token 后重试 preview | 返回 provider 对应的配置或凭据错误，不得生成本地假 MR/PR。 |

**预期结果**:
1. MVP-A 已具备 GitLab/GitHub 只读输入依赖。
2. MR/PR 快照是后续 code_review 任务的唯一输入来源。
3. 系统不得向 GitLab/GitHub 回写评论、审批状态、request changes、合并状态或分支变更。
4. diff 字节数、变更文件数或单文件 diff 行数超限失败必须留下可审计指标，便于判断拆分 MR/PR 或调整限制。

**状态**: 已自动化覆盖。GitLab MR 预览、只读快照、相同 diff 复用和超限错误见 `apps/api/tests/test_gitlab_snapshot.py`，其中预览断言 diff 文件树、风险摘要和 Review Checklist；GitHub PR 列表、预览、只读快照和 code_review 任务创建见 `apps/api/tests/test_github_snapshot.py`；Git Review API 入口单一路由归属见 `apps/api/tests/test_router_boundaries.py::test_git_review_endpoints_are_owned_by_git_review_router`；GitHub PR 列表、GitLab MR 预览和 GitHub PR 预览审计在禁用请求结束持久化后仍写入 repository 见 `apps/api/tests/test_database_persistence.py::test_gitlab_snapshot_writes_repository_without_request_persist` 与 `apps/api/tests/test_database_persistence.py::test_github_list_and_preview_audits_write_repository_without_request_persist`；任务中心预览弹窗展示见 `apps/web/tests/App.test.tsx`。需真实企业 GitLab/GitHub 凭据的端到端环境仍按生产就绪门禁验证。2026-06-03 使用产品 `product_118` / 仓库 `repo_024` 复跑时创建 GitHub PR #1，AI Brain 成功读取 PR 列表、预览最新 head `2e14a7f` 的 35 个变更文件并生成 `snapshot_006`。

---

### TC-AIBRAIN-REVIEW-FUNC-023B: MVP-B GitLab MR / GitHub PR Code Review 报告闭环

| 项目 | 内容 |
|------|------|
| 用例编号 | TC-AIBRAIN-REVIEW-FUNC-023B |
| 用例名称 | MVP-B GitLab MR / GitHub PR Code Review 报告闭环 |
| 阶段内优先级 | P0 |
| 适用阶段 | MVP-B |
| 模块 | REVIEW |
| 创建人 | Claude |
| 创建日期 | 2026-05-29 |

**前置条件**:
1. 已存在已确认的 `technical_solution` 任务和产品 GitLab/GitHub 只读资源绑定。
2. code-review 执行器默认适配 Claude Code `code-review` skill；本地联调未配置外部执行器命令但存在可用 Chat 模型网关时，应通过 `model_gateway` 适配器生成结构化 Review 报告。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在任务中心基于已完成 `technical_solution` 选择产品 GitLab/GitHub 代码库并预览 MR/PR | 页面展示 MR/PR 标题、作者、分支、变更文件数、风险摘要、变更文件树、变更文件明细、Review Checklist 和“不回写远端”提示。 |
| 2 | 生成 MR/PR diff 快照并 POST `/api/ai-tasks` 创建 `task_type=code_review` 任务 | 任务为 `draft`，input 包含 requirement_snapshot、product_context 和 gitlab_mr_snapshot 兼容引用。 |
| 3 | POST `/api/ai-tasks/{id}/start` | 调用 code-review 执行器，任务进入 `waiting_review`，返回 pending review。 |
| 4 | 在任务中心查看 Code Review 报告或 GET `/api/ai-tasks/{id}/code-review-report` | 返回 summary、risk_level、findings、文件/行号、建议、confidence、executor metadata 和 human_review；任务中心报告弹窗提供“查看需求全链路”入口，跳转到该任务 `requirement_id` 对应的 `/delivery/requirements/{requirement_id}/full-chain`。 |
| 5 | POST `/api/reviews/{id}/approve` 或 `edit-approve` | Review 报告归档到 AI Brain 内部，任务继续或完成。 |
| 6 | 查询远端 MR/PR | 未新增评论，未改变审批状态、request changes、合并状态或分支。 |
| 7 | GET `/api/audit/events?ai_task_id={id}` | 返回执行器调用、报告生成、人工确认和归档审计事件。 |
| 8 | 保持默认 `claude_code_skill` 但不配置外部命令，同时保留 active/default Chat 模型网关 | 任务通过 `model_gateway` 适配器进入 `waiting_review`，prompt 携带 MR/PR 快照和技术方案；报告包含 executor metadata，审计包含 `model_gateway.called` 和 `code_review.executor_called`。 |
| 9 | 让 code-review 执行器返回非法结构或调用失败 | 返回 `CODE_REVIEW_EXECUTOR_FAILED`，任务为 `failed`，`current_step=code_review_executor_failed`，审计包含 `code_review.executor_failed` 和 `ai_task.failed`。 |
| 10 | 修复执行器或上游模型后再次 POST `/api/ai-tasks/{id}/start` | 同一任务可重新进入执行器调用；成功时进入 `waiting_review`，并记录 `ai_task.retry_started` 审计事件。 |

**预期结果**:
1. v1 MVP 可以基于 GitLab MR / GitHub PR diff 快照生成结构化 Review 报告。
2. Review 报告必须经过人工确认后才能归档为正式结论。
3. 系统不得向 GitLab/GitHub 回写评论、审批状态、request changes、合并状态或分支变更。
4. 执行器失败时返回 `CODE_REVIEW_EXECUTOR_FAILED`，停留在可排查的失败步骤并写入审计；修复配置后可用同一任务重试，避免复制新任务导致链路割裂。

**状态**: 已自动化覆盖。Code Review 报告生成、确认归档、编辑确认、执行器失败语义，以及外部执行器命令缺失时复用模型网关的本地联调路径见 `apps/api/tests/test_code_review_report.py`；任务中心报告弹窗的需求全链路跳转见 `apps/web/tests/TaskCenterPage.test.tsx::opens a Code Review report with a requirement full-chain link`；真实执行器/模型 provider 端到端按生产就绪门禁验证。2026-06-03 使用 AI Brain GitHub PR #1 最新 head 复跑时，`task_072` 基于 `snapshot_006` 生成 `report_006`，人工确认后任务完成且报告归档，GitHub issue comments、review comments 和 reviews 均为 0。

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
1. 存在 MVP 数据：已排期需求、产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、知识沉淀和审计事件。
2. v1.2 扩展测试需要额外准备提交、自动化测试结果、Bug、Jenkins 发布记录、线上日志、用户使用、用户反馈和迭代规划建议关联数据。
3. 上述数据均可映射到同一产品、版本、模块或需求。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 以 MVP 数据查询感知视图 | 返回需求下游产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、模拟 Issue、知识沉淀和审计事件。 |
| 2 | 从感知视图下钻到任务或审计事件 | 保留产品、版本、模块、需求和时间范围上下文。 |
| 3 | 分别以 `human_review`、`code_review_report`、`mock_issue`、`knowledge_deposit` 和 `audit_event` 作为起点查询 | 返回对应任务的上游需求、下游证据和风险信号，不混入同产品下无关任务。 |
| 4 | 使用不支持的 `subject_type` 查询 | 返回 `VALIDATION_ERROR`，不得退化为全量任务结果。 |
| 5 | 以 v1.2 数据查询感知视图 | 返回提交、Review、测试、Bug、发布、线上日志、用户使用、用户反馈和迭代规划建议等扩展关系。 |
| 6 | 注入无法归属产品的提交 | 进入待归属队列，不参与需求级风险结论；队列登记和处理按 `TC-AIBRAIN-ATTRIBUTION-FUNC-024` 验证。 |
| 7 | 在需求管理页点击“全链路”或直接访问 `/delivery/requirements/{requirement_id}/full-chain` | 弹窗和独立详情页均一次展示需求、迭代版本、AI 任务、Review、PR/MR 快照、代码评审、Bug、发布和知识沉淀时间线；时间线支持按事件类型筛选，并显示筛选后/总事件数；需求已归属迭代版本时展示版本内多需求对比，包含同版本需求总数、状态分布和当前需求位置；提供“导出链路报告”操作，导出的 Markdown 报告包含需求标题、产品、迭代版本、链路摘要、阶段实体摘要和完整时间线；阶段进度区按需求、迭代版本、AI 任务、Review、PR/代码评审、Bug、发布和知识沉淀展示覆盖状态，并以中文业务状态展示；阶段明细区按同一阶段分组展示可展开实体清单，并提供跳转到需求、迭代版本、任务、Review、代码评审、Bug、发布和知识沉淀对应管理页的链接；弹窗摘要和阶段卡片自适应宽度，长标题或版本名不得造成右侧裁切；PR/MR 快照区展示风险摘要、diff 文件树和 Review Checklist；独立详情页提供返回需求管理入口。 |

**预期结果**:
1. 全流程感知在 v1 MVP 至少支持从需求查看下游产品详细设计任务、技术方案任务、代码 Review 报告、人工确认、模拟 Issue、知识沉淀和审计事件。
2. 全流程感知在 v1 MVP 可以从人工确认、Code Review 报告、MR 快照、模拟 Issue、知识沉淀、审计事件和 Bug 等证据主体回到对应任务链路。
3. v1.2 扩展后可以从任一主体追溯上游依据和下游影响。
4. 风险信号必须包含来源主体、影响摘要和处理建议。
5. 上下游链路缺失时明确标识缺口，不把缺失上下文当作无风险。
6. 需求全链路详情接口返回 `summary` 和按 `occurred_at` 升序排列的 `timeline`，弹窗和独立详情页入口只调用 `/api/requirements/{requirement_id}/full-chain` 获取详情，并通过共享组件展示阶段进度、阶段明细、实体跳转、PR/MR 快照风险摘要、diff 文件树和 Review Checklist。

**状态**: 已自动化覆盖 MVP 与 v1.2 真实证据主体链路追踪。MVP 需求下游、人工确认、Code Review 报告、模拟 Issue、知识沉淀和审计起点见 `apps/api/tests/test_lifecycle_context.py` 与 `apps/web/tests/App.test.tsx::opens real audit detail and lifecycle trace actions from audit rows`；需求全链路聚合接口见 `apps/api/tests/test_lifecycle_context.py::test_requirement_full_chain_returns_requirement_timeline_and_related_subjects`，需求管理页弹窗入口、阶段进度视图、版本内多需求对比、时间线类型筛选、导出链路报告和 PR/MR 证据展示见 `apps/web/tests/App.test.tsx::opens a requirement full-chain timeline from the requirements page`，独立详情页直达路由、返回入口、版本内多需求对比和共享展示组件见 `apps/web/tests/RequirementFullChainPage.test.tsx::opens a requirement full-chain detail page directly from the route`；v1.2 Bug、GitLab 每日代码指标、Jenkins 发布记录、线上日志指标、用户使用指标、用户反馈、迭代规划建议、动态 `missing_context` 和风险来源断言见 `apps/api/tests/test_lifecycle_context.py::test_lifecycle_context_links_v1_2_evidence_and_dynamic_missing_context`、`apps/api/tests/test_lifecycle_context.py::test_lifecycle_context_reports_missing_v1_2_context_dynamically` 以及 `apps/web/tests/App.test.tsx::opens real audit detail and lifecycle trace actions from audit rows`；生命周期边/风险信号和首页看板快照物化持久化见 `apps/api/tests/test_lifecycle_context.py::test_lifecycle_context_and_dashboard_queries_materialize_persistent_records` 与 `apps/api/tests/test_database_persistence.py::test_lifecycle_context_and_dashboard_snapshots_persist_through_fine_grained_repository`；handler 级写入结构表、禁用请求结束持久化后重建仍可恢复见 `apps/api/tests/test_database_persistence.py::test_lifecycle_and_dashboard_handlers_write_repository_without_request_persist`；运行时 store 过期时看板和生命周期上下文均读取 repository source rows；看板单条写入 dashboard snapshot，生命周期上下文写回 lifecycle edges/risks，见 `apps/api/tests/test_database_persistence.py::test_lifecycle_context_and_dashboard_use_repository_source_rows_when_runtime_store_is_stale`；GET 请求结束不会把过期运行时 store 持久化覆盖 repository 见 `apps/api/tests/test_database_persistence.py::test_repository_read_snapshot_get_does_not_persist_stale_runtime_store`。

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
2. 已通过 API、页面或采集器导入实际业务系统用户使用数据和用户反馈样本。
3. 用户具备产品负责人或 IT 管理者权限。

**测试步骤**:
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 聚合产品用户使用指标 | 返回活跃用户、功能访问、关键路径转化、停留、异常退出和低使用功能。 |
| 2 | 收集并查询用户反馈 | 返回满意度、问题反馈、改进建议、投诉、来源渠道、标签和关联模块；列表列宽固定，长反馈摘要不得撑开页面，操作列固定在右侧可见。 |
| 3 | 触发 AI 迭代规划建议生成 | 返回下阶段优先迭代需求建议清单，状态为 `suggested`，不创建新 requirement。 |
| 4 | 查看用户洞察或建议详情 | 点击“详情”弹窗展示摘要、数据类型、状态、归属用户、更新时间、产品/版本/模块/功能、反馈类型、规划周期、优先级、置信度和转化需求 ID；迭代建议详情包含推荐理由、用户证据、业务价值、风险信号、依赖条件、预估研发投入和建议优先级。 |
| 5 | 模拟使用数据不足或反馈样本过少 | 建议标识证据不足，不给出确定性排序。 |
| 6 | 查询需求列表和产品规划 | 未出现由 AI 建议自动创建的新需求、路线图变更或迭代排期变更。 |
| 7 | 产品负责人确认采纳并选择转正式需求 | 建议状态变为 `converted_to_requirement`，并返回人工确认后创建的 requirement_id。 |

**预期结果**:
1. MVP 阶段用户使用指标、用户反馈和 AI 迭代规划建议均来自真实结构表；AI 迭代规划建议可追溯到真实用户反馈和 Bug，v1.2 扩展到产品规划、需求、用户使用指标、线上日志和发布记录。
2. AI 只生成建议，不自动创建正式需求、不自动变更路线图、不自动调整迭代排期。
3. 只有产品负责人或等价权限确认采纳后，建议才能转为正式需求或进入迭代计划。
4. 无法归属产品或模块的使用数据和反馈进入待归属队列，登记、归属和忽略处理由 `TC-AIBRAIN-ATTRIBUTION-FUNC-024` 覆盖。

**状态**: 已自动化覆盖用户使用指标登记/查询、用户反馈、用户洞察详情弹窗和迭代规划基础闭环；待归属队列登记、归属和忽略处理由 `TC-AIBRAIN-ATTRIBUTION-FUNC-024` 覆盖；外部采集器和模型驱动规划仍属后续增强。

---
