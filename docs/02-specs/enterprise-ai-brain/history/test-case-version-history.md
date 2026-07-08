# 测试用例版本历史

> 从 [test-case.md](../test-case.md) 拆出，保留完整版本历史，主文档只维护当前事实与导航。

# 企业 AI 大脑平台测试用例

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.969 |
| 适用系统版本 | ≥ v1.0.0 |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.1.969 | 2026-07-08 | 补充研发执行器策略任务类型收敛验收：新增策略不再展示代码巡检整改，代码巡检问题经 Bug 修复策略推进 | Codex |
| v1.1.968 | 2026-07-08 | 补充研发执行器策略 Runner 上下文验收：下发任务必须携带同产品知识中心引用，并排除其他产品文档 | Codex |
| v1.1.967 | 2026-07-04 | 补充钉钉官方 MCP 增强验收：授权配置向导、tools/list 动态发现、高风险治理、健康看板和业务模板 | Codex |
| v1.1.966 | 2026-07-04 | 补充钉钉官方 MCP P0 插件验收：六个标准插件、URL Key 连接表单、Streamable HTTP 调用、脱敏和动作模板风险层级 | Codex |
| v1.1.965 | 2026-07-03 | 补充产品 Git 资源编辑验收：手工修改 Project Path 必须保存，只修改 Remote URL 时由后端重新推导路径 | Codex |
| v1.1.964 | 2026-07-03 | 补充定时作业运行记录可读性验收：运行记录列表和详情需显示作业名称，名称缺失才兜底作业 ID | Codex |
| v1.1.963 | 2026-07-03 | 补充系统设置发信能力验收：SMTP 配置、密码脱敏、测试发送和审计不得记录密钥 | Codex |
| v1.1.962 | 2026-07-03 | 补充 GitLab 连接 Token-only 验收：新增连接只填 Endpoint 和 Token 即可保存，GitLab 地址仅作为可选默认项目参数 | Codex |
| v1.1.961 | 2026-07-03 | 补充 GitHub 连接 Token-only 验收：新增连接只填 Token 即可保存，仓库地址仅作为可选默认 owner/repo | Codex |
| v1.1.960 | 2026-07-03 | 补充本地完整代码巡检凭据验收：任务可绑定 GitHub/GitLab 连接读取 token，产品代码库只维护 remote_url | Codex |
| v1.1.959 | 2026-07-03 | 补充系统设置验收：系统管理员邮箱配置需走 `system.settings.manage` 权限、数据库持久化、审计和真实页面回归 | Codex |
| v1.1.958 | 2026-07-03 | 补充代码巡检产品级默认多仓扫描验收：新增作业只选产品，运行层展开 active 仓库，详情展示按仓库扫描/AI/写入明细和 Worker 重试 | Codex |
| v1.1.957 | 2026-07-03 | 补充需求删除保护验收：已有 AI 任务的需求删除返回占用数量，页面展示中文处理建议 | Codex |
| v1.1.956 | 2026-07-03 | 补充 Bug 管理图片预览验收：已上传图片点击后通过后端预览代理展示图片 | Codex |
| v1.1.955 | 2026-07-03 | 补充 Bug 管理图片证据验收：本地多选和剪贴板粘贴图片先上传 MinIO 对象存储，再随 Bug `evidence.images[]` 保存引用 | Codex |
| v1.1.954 | 2026-07-03 | 补充插件配置删除保护回归：历史插件调用日志保留但不阻断连接、动作或插件删除，删除配置时置空日志引用 | Codex |
| v1.1.953 | 2026-07-02 | 补充定时作业 AI执行器选择验收：页面可选择本地 Codex Runner，运行先进入等待 Runner，完成回写后继续动作并生成用户洞察 | Codex |
| v1.1.952 | 2026-07-02 | 样例复用向导验收补充进度字段，页面需展示连接测试、动作试运行和 dry-run 的“进度：N/4 步已就绪” | Codex |
| v1.1.951 | 2026-07-02 | 补充 Runner 沙箱权限边界验收：心跳上报安全元数据后就绪清单展示 `sandbox_permission_boundary` | Codex |
| v1.1.950 | 2026-07-02 | 补充 Runner 高风险审批写回验收：点击审批后写回动作配置并自动重新试运行 | Codex |
| v1.1.949 | 2026-07-02 | 补充动作试运行失败态样例复用验收：blocked 向导展示缺失项，不展示“生成作业草稿”入口 | Codex |
| v1.1.948 | 2026-07-02 | 补充 Runner 高风险阻断验收：返回 `approval_request` 审批草案并写入审批请求审计，不创建队列任务 | Codex |
| v1.1.947 | 2026-07-02 | 补充 Trace DAG 保护态节点前端验收：节点无 `rerun_plan` 但有保护态信息时仍可预检，并可按 `full_run_request` 复跑整条运行记录 | Codex |
| v1.1.946 | 2026-07-02 | 补充 Trace DAG 单节点复跑前端验收：确认复跑后应调用节点复跑接口、刷新列表并打开新运行详情 | Codex |
| v1.1.945 | 2026-07-02 | 补充普通插件执行调用 AI 模式验收：`plugin_action_invoke + ai_generated` 正式运行必须调用模型、生成 Skill 节点并执行通用结果动作 | Codex |
| v1.1.944 | 2026-07-02 | 补充 Agent/Skill 文件包脚本边界验收：公开 `runtime_capabilities.script_files` 只列出 `scripts/` 下脚本，Agent 根目录可执行脚本上传必须拒绝 | Codex |
| v1.1.943 | 2026-07-02 | 补充 Runner 安装包代理真实执行探针验收：解包 `runner_agent.py` 后需实际执行本地命令、验证 stdin 指令、日志追加和完成回写 payload | Codex |
| v1.1.942 | 2026-07-02 | 补充动作试运行草稿自动 dry-run 验收：存在响应样例时新增作业页应自动复用样例执行全链路试运行 | Codex |
| v1.1.941 | 2026-07-02 | 补充 Runner 运行中取消感知验收：服务端取消或终态后，本地代理需清理进程树并跳过完成回写 | Codex |
| v1.1.940 | 2026-07-02 | 补充 Runner 安装包进程组隔离验收：超时必须终止整棵执行器进程树并保留日志回写 | Codex |
| v1.1.939 | 2026-07-02 | 补充插件管理执行器列表超时扫描入口验收：页面触发后展示重派、死信、超时摘要和下一步建议 | Codex |
| v1.1.938 | 2026-07-02 | 补充 Runner 超时扫描摘要验收：返回重派、死信、超时数量和下一步动作建议 | Codex |
| v1.1.937 | 2026-07-02 | 补充定时作业 dry-run 样例复用验收：带入动作试运行响应样例时跳过第三方连接调用并延续样例来源 | Codex |
| v1.1.936 | 2026-07-02 | 补充 Trace DAG AI 处理节点单节点复跑验收：复用来源数据连接响应快照重新调用模型，且不执行动作写入 | Codex |
| v1.1.935 | 2026-07-02 | 补充 Trace DAG 通用结果动作节点单节点复跑验收：复用来源 AI 输出快照生成独立结果写入记录 | Codex |
| v1.1.934 | 2026-07-02 | 补充 Trace DAG 数据连接节点单节点复跑验收：预检 ready 后 POST 创建来源运行，Skill/动作节点仍保持保护态 | Codex |
| v1.1.933 | 2026-07-02 | 补充 AI 执行器 Runner 高风险审批快照验收：未审批阻断，完整审批后任务入队并记录审批审计 | Codex |
| v1.1.932 | 2026-07-02 | 补充 Agent/Skill 文件包脚本资产验收：`scripts/` 下脚本可落盘并显示为待沙箱，非 scripts 目录可执行脚本必须拒绝 | Codex |
| v1.1.931 | 2026-07-02 | 补充 AI 角色 Agent 文件包上传验收：`agent.yaml`/`AGENT.md` 落盘、权限校验、运行边界和页面上传入口需覆盖 | Codex |
| v1.1.930 | 2026-07-02 | 补充样例复用向导交接摘要验收，连接测试、动作试运行、dry-run 和新增作业页需展示当前步骤、下一步说明和已带入项 | Codex |
| v1.1.929 | 2026-07-02 | 补充 AI 执行器 Runner 高风险指令拦截验收，服务端预检和本地 agent 兜底需阻止 push、删除、强制 reset 和发布部署类指令进入队列 | Codex |
| v1.1.928 | 2026-07-02 | 补充 AI 执行器 Runner 命令白名单强制验收，安装包需拒绝未配置执行器命令，就绪清单需展示命令白名单、禁用 shell 和高风险审批 | Codex |
| v1.1.927 | 2026-07-02 | 补充 Trace DAG 复跑预检执行策略和下一步动作验收，页面需展示保护态说明和推荐整条复跑 | Codex |
| v1.1.926 | 2026-07-02 | 补充连接测试样例复制动作后自动试运行验收，保存动作后应直接生成写入预览和定时作业草稿入口 | Codex |
| v1.1.925 | 2026-07-02 | 补充 AI 执行器 Runner 运行就绪清单验收，列表需展示 ready/attention/blocked 和关键控制项状态 | Codex |
| v1.1.924 | 2026-07-02 | 补充 Trace DAG 复跑预检结构化控制项验收，缺失控制只统计未满足项，页面展示控制项摘要和中文状态 | Codex |
| v1.1.923 | 2026-07-02 | 补充 AI 执行器 Runner 队列概览验收，列表需展示排队、运行中、异常、可用槽和最近失败原因 | Codex |
| v1.1.922 | 2026-07-02 | 补充动作试运行生成作业草稿后的样例复用前端验收，新增页需展示连接、动作、样例来源、写入目标和预计写入 | Codex |
| v1.1.921 | 2026-07-02 | 补充定时作业运行详情 Trace DAG 复跑预检前端验收，点击节点预检后展示阻断原因、缺失控制和快照摘要 | Codex |
| v1.1.920 | 2026-07-02 | 补充 Trace DAG 节点级复跑只读预检验收，校验快照预览、缺失控制项和受保护复跑语义不变 | Codex |
| v1.1.919 | 2026-07-02 | 补充连接测试、动作试运行和定时作业 dry-run 样例复用向导验收，校验 `reuse_wizard` 的步骤状态、下一步动作和缺失项 | Codex |
| v1.1.918 | 2026-07-02 | 补充 Trace DAG 节点级复跑受保护 API 验收：返回保护响应、整条复跑替代请求和审计事件 | Codex |
| v1.1.917 | 2026-07-02 | 补充 Runner 代理需流式追加 stdout/stderr、禁用 shell 执行并通过 stdin 传入指令的安装包验收 | Codex |
| v1.1.916 | 2026-07-02 | 补充 AI 执行器 Runner 安装包内置轮询代理和完成回写保留流式日志验收 | Codex |
| v1.1.915 | 2026-07-02 | 补充 AI 执行器 Runner 工作区白名单派发和认领双重校验验收，覆盖子目录允许、白名单漂移拒绝和任务日志回写 | Codex |
| v1.1.914 | 2026-07-02 | 补充 Trace DAG 受保护复跑计划、动作试运行生成定时作业草稿、dry-run 样例复用摘要和 Skill 脚本待沙箱验收 | Codex |
| v1.1.913 | 2026-07-02 | 补充定时作业通用结果动作和多连接同插件校验验收：线上日志 AI 分析需写入通知记录，跨插件连接保存需拦截 | Codex |
| v1.1.912 | 2026-07-02 | 补充定时作业运行详情需展示用户可读“运行摘要”的前端验收 | Codex |
| v1.1.911 | 2026-07-02 | 补充插件执行调用类定时作业成功摘要不得返回开发占位文案的验收 | Codex |
| v1.1.910 | 2026-07-02 | 补充定时作业 Skill 输出类型校验失败时仍需返回 `model_log_id` 的排障验收 | Codex |
| v1.1.909 | 2026-07-02 | 补充定时作业正式运行 Skill 输出类型校验验收：模型输出字段类型不匹配时 AI 节点失败且结果动作不执行 | Codex |
| v1.1.908 | 2026-07-02 | 补充定时作业 dry-run Skill 输出样例验收：未声明 item schema 的 `insights` 数组也需生成结构化样例记录并进入写入预览 | Codex |
| v1.1.907 | 2026-07-02 | 补充定时作业 dry-run 页面摘要验收：全链路试运行结果需展示 AI 输出来源、动作预计写入数量和预览来源 | Codex |
| v1.1.906 | 2026-07-02 | 补充定时作业 dry-run AI 场景写入预览来源验收：动作预计写入数量必须基于 Skill 输出 Schema 样例而非数据连接原始响应 | Codex |
| v1.1.905 | 2026-07-02 | 补充定时作业多节点诊断验收：数据连接失败时 AI 节点必须未开始，多数据连接、多结果动作诊断和运行健康统计按明细聚合 | Codex |
| v1.1.904 | 2026-07-01 | 补充 AI 助手定时作业草案空引用归一化验收：预览和确认保存必须跳过空值并保序去重 | Codex |
| v1.1.903 | 2026-07-01 | 补充内部数据源重复源验收：旧客户端传入重复 `source_types` 时服务端需保序去重并稳定返回摘要 | Codex |
| v1.1.902 | 2026-07-01 | 补充内部数据源服务端裁剪验收：旧客户端带入未选源过滤时，测试预览和动作读取只返回实际生效 `source_filters` | Codex |
| v1.1.901 | 2026-07-01 | 补充内部数据源按源过滤联动验收：取消需求或 Bug 源后对应过滤字段隐藏且不提交残留 `source_filters` | Codex |
| v1.1.900 | 2026-07-01 | 补充内部数据源注册表同源验收：市场 schema 的 `source_types` 选项、连接默认值和读取默认源顺序必须一致 | Codex |
| v1.1.899 | 2026-07-01 | 补充 AI 助手动作命名验收：`create_plugin_action` 在用户侧统一展示为“动作/新增动作/应用到动作表单”，旧“插件动作”仅作为兼容输入 | Codex |
| v1.1.898 | 2026-07-01 | 收口插件连接环境弱化验收：页面不得展示环境筛选或环境列，后台 `environment` 查询仅作为接口兼容和运行排障能力 | Codex |
| v1.1.897 | 2026-07-01 | 补充内部数据源连接按源过滤可视化验收：需求状态/优先级和 Bug 状态/严重级别需由表单写入 `source_filters` | Codex |
| v1.1.896 | 2026-07-01 | 补充内部数据源 detail 字段权限授权验收：`system.internal_data_source.detail` 必须在权限目录和角色授权中可用 | Codex |
| v1.1.895 | 2026-07-01 | 补充内部数据源 P2 验收：字段白名单、按源 `source_filters`、响应 schemas 和字段权限过滤需有后端回归 | Codex |
| v1.1.894 | 2026-07-01 | 补充 AI 助手定时作业运行转业务草案后端验收：引用运行记录后应持久化洞察、需求和 Bug 三类分析草案 | Codex |
| v1.1.893 | 2026-07-01 | 补充定时作业运行详情“转业务草案”验收：菜单需支持洞察、需求和 Bug 三类 AI 助手草案入口 | Codex |
| v1.1.892 | 2026-07-01 | 补充定时作业运行详情“转洞察草案”验收：详情弹窗必须携带运行记录引用进入 AI 助手生成用户洞察草案 | Codex |
| v1.1.891 | 2026-07-01 | 补充定时作业运行详情 JSON 导出验收：详情弹窗必须提供导出入口，导出 payload 包含运行记录、展示标签、数据连接/AI执行/动作节点、结果写入记录和快照 | Codex |
| v1.1.890 | 2026-07-01 | 补充官方内部数据源插件验收：市场目录、连接 schema 多选、内部只读连接测试、`internal_query` 动作调用、产品 scope 过滤、内部业务定时作业模板和插件页表单展示均需覆盖 | Codex |
| v1.1.889 | 2026-07-01 | 补充插件管理连接环境弱化验收：新增/编辑连接不展示环境字段，连接列表不展示环境筛选或环境列，动作连接选择只显示连接名称，后台仍保留环境字段 | Codex |
| v1.1.888 | 2026-07-01 | 补充插件管理动作表单连接优先验收：新增/编辑动作不展示插件选择，选择连接后自动推导插件，后端支持仅提交 `connection_id` 并校验插件连接不匹配 | Codex |
| v1.1.887 | 2026-07-01 | 补充真实全链路回归稳定性验收：脚本族必须复用 `full_chain_regression_slug`，权限可视化场景必须按本次唯一后缀筛选角色列表，连续运行 `all-targeted` 时不得因秒级 fixture 目录或历史角色分页污染失败 | Codex |
| v1.1.886 | 2026-07-01 | 补充迭代版本总览发布准备清单后端投影验收：dashboard 必须返回 `release_readiness_checklist`，页面清单优先消费该字段，版本驾驶舱/助手/代码巡检快速回归 helper 必须校验结构、顺序和计数一致性 | Codex |
| v1.1.885 | 2026-07-01 | 补充定时作业 read model 拆分守护：`scheduled_jobs.py` 纳入 1900 行预算，定时作业列表、运行记录列表和运行公开投影必须留在 `scheduled_job_read_models.py` | Codex |
| v1.1.884 | 2026-07-01 | 补充 AI 执行器 Runner 任务上下文拆分守护：`ai_executor_runners.py` 纳入 2050 行预算，任务产品 scope、上游运行上下文、运行节点投影和时间解析 helper 必须留在 `ai_executor_runner_task_context.py` | Codex |
| v1.1.883 | 2026-06-30 | 补充插件调用运行时拆分守护：`plugins.py` 纳入 1800 行预算，动态请求配置解析、请求预览、HTTP/MCP 调用、AI 执行器 Runner 派发和系统默认模型网关执行器必须留在 `plugin_invocation_runtime.py` | Codex |
| v1.1.882 | 2026-06-30 | 补充代码巡检读模型拆分守护：`code_inspections.py` 纳入 1600 行预算，列表分页、Dashboard 聚合、趋势、分支/提交人治理和读模型 scope 必须留在 `code_inspection_read_models.py` | Codex |
| v1.1.881 | 2026-06-30 | 补充迭代版本总览交付总览拆分守护：`product_version_dashboard.py` 纳入 1300 行预算，证据覆盖评分必须留在 `product_version_evidence_coverage.py`，治理结论和交付阶段投影必须留在 `product_version_delivery_overview.py` | Codex |
| v1.1.880 | 2026-06-30 | 补充迭代版本总览证据覆盖评分拆分守护：`product_version_dashboard.py` 纳入 1800 行预算，证据覆盖评分必须留在 `product_version_evidence_coverage.py` | Codex |
| v1.1.879 | 2026-06-30 | 补充真实全链路回归版本证据覆盖门禁：`full`、`version-dashboard`、`assistant-qa` 和 `code-inspection-governance` 必须校验 `evidence_coverage` 结构、顺序、计数和覆盖分一致性 | Codex |
| v1.1.878 | 2026-06-30 | 补充迭代版本总览证据覆盖验收：dashboard 必须返回 `evidence_coverage`，页面首屏展示覆盖评分、阻断域、缺口域和权限降级域 | Codex |
| v1.1.877 | 2026-06-30 | 补充用户反馈原始列表分页性能验收：`GET /api/insights/user-feedback?page=&page_size=&summary_only=true` 必须走 count/page read model、返回性能观测并截断长内容 | Codex |
| v1.1.876 | 2026-06-30 | 补充真实全链路回归 AI 助手问答 helper 拆分守护：确定性助手、版本引用、`assistant.iteration`、版本总览投影和会话历史校验必须留在 `full_chain_regression_assistant_qa.py` | Codex |
| v1.1.875 | 2026-06-30 | 补充真实全链路回归代码巡检治理 helper 拆分守护：本地完整扫描、质量门禁、Bug/整改任务写回、提交人治理、趋势对比和版本总览阻塞校验必须留在 `full_chain_regression_code_inspection.py` | Codex |
| v1.1.874 | 2026-06-30 | 补充真实全链路回归权限可视化 helper 拆分守护：角色列表、权限矩阵、角色访问预览、范围名称和用户权限诊断校验必须留在 `full_chain_regression_permissions.py` | Codex |
| v1.1.873 | 2026-06-30 | 补充真实全链路回归知识索引健康 helper 拆分守护：文档创建、索引健康、权限命中、失败重试和检索恢复校验必须留在 `full_chain_regression_knowledge.py` | Codex |
| v1.1.872 | 2026-06-30 | 补充真实全链路回归 AI 动作草案治理 helper 拆分守护：确认、失败重试、列表 read model 和审计链路校验必须留在 `full_chain_regression_assistant_drafts.py` | Codex |
| v1.1.871 | 2026-06-30 | 补充迭代版本总览发布证据增强验收：dashboard summary 必须返回成功/失败发布计数，交付阶段发布证据卡和回归 helper 必须展示/校验最近发布状态与时间 | Codex |
| v1.1.870 | 2026-06-30 | 补充任务中心任务详情弹窗拆分守护验收：`TaskDetailModal` 承接详情展示和 JSON 预览，TaskCenter 页面预算收紧到 1800 行 | Codex |
| v1.1.869 | 2026-06-30 | 补充前端页面容器拆分守护验收：TaskCenter、知识中心、角色、插件、迭代版本等大页面必须保持预算内，新超过 900 行页面必须登记预算或继续拆分 | Codex |
| v1.1.868 | 2026-06-30 | 补充 Runner 可靠性快速回归取消/重试验收：`runner-reliability` 必须覆盖运行中任务取消、人工重试、重试任务认领完成、重复重试拒绝和审计链路 | Codex |
| v1.1.867 | 2026-06-30 | 补充版本驾驶舱快速回归 Bug 聚合验收：`version-dashboard` 必须覆盖手工 blocker Bug、Bug 汇总/明细/状态计数、阻塞项和 next_actions 优先级 | Codex |
| v1.1.866 | 2026-06-30 | 补充知识索引健康快速回归失败恢复验收：`knowledge-index-health` 必须覆盖索引失败、健康问题 retry 动作、重试恢复和恢复后搜索命中 | Codex |
| v1.1.865 | 2026-06-30 | 补充 AI 动作草案治理快速回归失败重试验收：`assistant-draft-governance` 必须覆盖确认失败、失败原因、重试恢复、修复后确认和审计事件 | Codex |
| v1.1.864 | 2026-06-30 | 补充 AI 助手版本治理问答状态推进投影验收：即时回答和历史消息中的 `status_impact` 必须与版本驾驶舱保持一致 | Codex |
| v1.1.863 | 2026-06-30 | 补充真实全链路回归版本驾驶舱状态影响 helper 验收：`validate_version_dashboard_status_impact` 必须集中校验 `status_impact` 结构和目标状态 | Codex |
| v1.1.862 | 2026-06-30 | 补充迭代版本总览状态推进影响预览验收：页面必须在明细表前展示同步推进、阻塞和保持不变摘要，覆盖代表需求与阻塞原因 | Codex |
| v1.1.861 | 2026-06-30 | 补充 AI 动作确认中心统一确认决策验收：列表 summary、列表行和详情治理摘要必须返回可确认、阻断、失败、过期和下一步动作 | Codex |
| v1.1.860 | 2026-06-30 | 补充迭代版本总览后端交付阶段总览验收：dashboard 必须返回 `delivery_stage_overview`，页面、AI 助手和回归脚本优先复用 | Codex |
| v1.1.859 | 2026-06-30 | 补充真实全链路回归版本驾驶舱 helper 拆分守护：版本阻塞、下一步行动、治理结论和分支质量校验必须留在 `full_chain_regression_version_dashboard.py` | Codex |
| v1.1.858 | 2026-06-30 | 补充迭代版本总览后端治理结论验收：dashboard 必须返回 `governance_conclusion`，前端和 AI 助手优先复用该结论 | Codex |
| v1.1.857 | 2026-06-30 | 补充真实全链路回归 Runner 可靠性 helper 拆分守护：健康告警、Token 轮换、租约重派、死信队列和日志校验必须留在 `full_chain_regression_runner.py` | Codex |
| v1.1.856 | 2026-06-30 | 补充真实全链路回归脚本 suite 元数据拆分守护：目标域、快速 suite 编排和 coverage 计算必须留在 `full_chain_regression_suites.py` | Codex |
| v1.1.855 | 2026-06-30 | 补充真实全链路回归脚本 `assistant-qa` 快速套件验收：独立校验 AI 助手迭代版本治理问答、版本引用、版本总览 next_actions 和历史持久化，并纳入 all-targeted | Codex |
| v1.1.854 | 2026-06-30 | 补充真实全链路回归脚本 `all-targeted` 快速治理组合套件验收：一次串行运行 Runner、版本总览、草案治理、代码巡检治理、知识索引健康和权限可视化，但覆盖矩阵必须标记非完整主链路 | Codex |
| v1.1.853 | 2026-06-30 | 补充知识索引健康中心治理摘要验收：页面必须集中展示解析状态、Chunk/Embedding、检索与权限，并明确补向量、重试索引、查看分块或导入任务动作 | Codex |
| v1.1.852 | 2026-06-30 | 补充 AI 助手迭代版本治理问答验收：版本阻塞/下一步行动问题必须走确定性 `assistant.iteration`，携带版本总览摘要且历史消息保留安全投影 | Codex |
| v1.1.851 | 2026-06-30 | 补充迭代版本总览 next_actions 验收：后端必须按阻塞优先级返回前三个治理建议、来源标签和全链路主体，前端优先消费该字段 | Codex |
| v1.1.850 | 2026-06-30 | 补充角色详情 access_preview 验收：单角色详情必须返回可见菜单、操作权限、产品/知识空间范围名称和菜单权限缺口诊断 | Codex |
| v1.1.849 | 2026-06-30 | 补充真实全链路回归脚本权限可视化快速场景验收：`permission-visibility` 独立校验角色列表、权限矩阵、范围名称、菜单权限缺口和用户权限诊断 | Codex |
| v1.1.848 | 2026-06-30 | 补充真实全链路回归脚本知识索引健康快速场景验收：`knowledge-index-health` 独立校验文档创建、索引健康、权限命中说明、检索模式和搜索命中 | Codex |
| v1.1.847 | 2026-06-30 | 补充真实全链路回归脚本代码巡检治理快速场景验收：`code-inspection-governance` 独立校验扫描、门禁、写回、提交人治理、趋势对比和版本总览阻塞 | Codex |
| v1.1.846 | 2026-06-30 | 补充迭代版本总览待确认 Code Review 阻塞项验收：版本阻塞队列必须提供评审处理入口和全链路入口 | Codex |
| v1.1.845 | 2026-06-30 | 补充真实全链路回归脚本 Runner 健康告警门禁：`runner-reliability` 必须验证 `runner_never_connected` 和心跳恢复后 `health_alert` 清除 | Codex |
| v1.1.844 | 2026-06-30 | 补充 AI 执行器 Runner 健康告警验收：API 返回 `health_alert`，列表直接展示未连接或心跳超时原因，测试覆盖系统默认、正常和异常 Runner | Codex |
| v1.1.843 | 2026-06-30 | 补充 AI 动作草案服务拆分守护验收：`assistant_action_draft_common` 承接状态/动作枚举、默认 payload 和 Cron 校验，架构守护防止通用规则回流主服务文件 | Codex |
| v1.1.842 | 2026-06-30 | 补充代码巡检服务拆分守护验收：`code_inspection_common` 承接通用规则/校验，架构守护防止逻辑回流主服务文件 | Codex |
| v1.1.841 | 2026-06-30 | 补充执行诊断问 AI 链路兜底验收：链接需携带 `diagnostic_trace_id`，助手在 prompt 缺失时按 Trace 详情重建诊断问题 | Codex |
| v1.1.840 | 2026-06-30 | 补充迭代版本总览交付链路处理入口验收：各阶段卡片必须直达需求、任务、分支、巡检、评审、Bug、知识、发布或状态推进上下文 | Codex |
| v1.1.839 | 2026-06-30 | 补充代码巡检治理结论验收：治理概览首屏必须展示总体判断、主要风险标签和下一步动作 | Codex |
| v1.1.838 | 2026-06-30 | 补充迭代版本总览版本治理结论验收：首屏必须展示总体推进建议、主要风险标签和下一步动作 | Codex |
| v1.1.837 | 2026-06-30 | 补充迭代版本总览首屏分支治理验收：顶部指标和健康摘要必须展示待治理分支、门禁失败、待审批忽略和到期风险 | Codex |
| v1.1.836 | 2026-06-30 | 补充知识索引健康验收：健康面板必须展示文档状态分布和 Chunk/Embedding 覆盖率，便于定位解析、分块和向量索引进度 | Codex |
| v1.1.835 | 2026-06-30 | 补充迭代版本总览分支质量 finding 级治理验收：版本总览必须展示活跃严重、误报忽略、接受风险、过期风险和待审批忽略指标 | Codex |
| v1.1.834 | 2026-06-30 | 补充真实全链路回归脚本代码巡检趋势对比验收：完整链路同仓同分支二次扫描必须校验 `previous_comparison`、前次报告和问题数 delta | Codex |
| v1.1.833 | 2026-06-30 | 补充真实全链路回归脚本迭代版本总览分支质量治理门禁：`full` 和 `version-dashboard` 场景均需校验 `branch_quality_governance` 与 summary 分支治理计数 | Codex |
| v1.1.832 | 2026-06-30 | 补充迭代版本总览分支质量治理验收：dashboard 返回 `branch_quality_governance`，页面展示待治理/待巡检分支、严重问题 Bug/整改覆盖、质量门禁和最近报告 | Codex |
| v1.1.831 | 2026-06-30 | 补充代码巡检分支治理待办验收：dashboard 返回 `branch_governance` 与治理压力分支计数，页面展示分支闭环状态、门禁失败和 Bug/整改覆盖 | Codex |
| v1.1.830 | 2026-06-30 | 补充 AI 助手模型网关 helper 拆分守护：`assistant_chat_gateway` 承接模型配置选择、请求组装、取消中断、响应解析和模型日志，避免回流 `assistant_chat.py` | Codex |
| v1.1.829 | 2026-06-30 | 补充 AI 助手知识引用 helper 拆分守护：`assistant_knowledge_references` 承接知识空间、目录、文档、chunk 候选和模型注入上下文，避免回流 `assistant_references.py` | Codex |
| v1.1.828 | 2026-06-30 | 补充 AI 助手定时作业 run-once helper 拆分守护：`assistant_scheduled_job_run` 承接显式提及解析、权限提示、草案兜底和运行结果投影，避免回流 `assistant_chat.py` | Codex |
| v1.1.827 | 2026-06-30 | 补充插件公开投影拆分守护：`plugin_projection` 承接插件版本元数据、公开投影和调用请求摘要脱敏，避免回流 `plugins.py` | Codex |
| v1.1.826 | 2026-06-30 | 补充定时作业配置 helper 拆分守护：`scheduled_job_config` 承接调度时间、配置编排、多数据源引用、仓库默认分支、数据连接策略和有效作业类型推导，避免回流 `scheduled_jobs.py` | Codex |
| v1.1.825 | 2026-06-30 | 补充迭代版本总览版本范围 read model 验收：PostgreSQL 运行时必须优先读取该版本专用 source rows，不能回退到全量 task workflow source rows 后服务层过滤 | Codex |
| v1.1.824 | 2026-06-30 | 补充迭代版本总览优先处理建议验收：下一步行动区必须按阻塞队列优先级展示前三个处理建议及跳转入口 | Codex |
| v1.1.823 | 2026-06-30 | 补充真实全链路回归脚本代码巡检治理压力验收：完整链路必须校验 dashboard `governance_pressure` 的门禁失败、严重问题和 Bug/整改任务闭环覆盖 | Codex |
| v1.1.822 | 2026-06-30 | 补充代码巡检治理压力总览验收：dashboard 必须返回 `governance_pressure`，页面顶部展示闭环状态、待闭环提交人、缺 Bug、缺整改任务、门禁失败和到期接受风险 | Codex |
| v1.1.821 | 2026-06-30 | 补充 AI 动作确认中心列表治理压力总览验收：草案任务台 summary 必须返回风险、权限和治理计数，页面顶部展示高风险、权限阻塞、校验阻塞、失败/重试和审计事件 | Codex |
| v1.1.820 | 2026-06-30 | 补充真实全链路回归脚本结构化验收报告：`--json-output` / `FULL_CHAIN_JSON_OUTPUT` 成功和失败均输出 suite、耗时、步骤和失败原因，便于 CI 留存证据和定位断点 | Codex |
| v1.1.819 | 2026-06-30 | 补充迭代版本总览交付链路验收：版本总览需按研发链路顺序展示需求、任务、分支、巡检、评审、Bug、知识、发布和状态推进风险；前端页面测试覆盖 | Codex |
| v1.1.818 | 2026-06-30 | 补充 AI 执行器 Runner 人工重试验收：`cancelled/failed/timed_out/dead_letter` 任务可复制上下文重新入队，记录 `retry_of_task_id/retry_history` 和 `ai_executor_task.retry_requested` 审计；非重试态返回 409 | Codex |
| v1.1.817 | 2026-06-29 | 补充插件常量拆分守护：协议、状态、认证类型、连接环境、调用状态和排序字段必须从 `plugin_constants` 导入，避免回流 `plugins.py` | Codex |
| v1.1.816 | 2026-06-29 | 补充 AI 助手动作引用默认入口拆分守护：默认候选、触发词和配置常量必须从 `assistant_action_reference_defaults` 导入，避免回流主服务 | Codex |
| v1.1.815 | 2026-06-29 | 补充迭代版本入口体验验收：版本列表默认按创建时间倒序，`view=dashboard` 深链直达版本总览，代码分支深链保持原行为 | Codex |
| v1.1.814 | 2026-06-29 | 补充迭代版本总览知识沉淀索引健康验收：版本总览必须展示可检索/向量就绪沉淀数、索引状态、chunk/embedding 覆盖和检索模式 | Codex |
| v1.1.813 | 2026-06-29 | 补充迭代版本总览知识沉淀聚合验收：版本总览必须按版本任务展示知识沉淀数、来源任务、知识文档 ID 和全链路入口，缺少 `knowledge.read` 时明细降级隐藏；后端、前端和全链路脚本覆盖 | Codex |
| v1.1.812 | 2026-06-29 | 补充真实全链路回归脚本版本总览 Code Review 门禁验收：`--suite version-dashboard` 必须创建本地 GitLab fixture MR 快照和待确认代码评审报告，并校验版本总览报告数与待确认数 | Codex |
| v1.1.811 | 2026-06-29 | 补充 RBAC 权限范围名称验收：权限矩阵和用户权限诊断必须返回产品、知识空间、全局 scope 的可读名称，角色页展示名称、ID 与访问级别；后端 RBAC 与系统管理页测试覆盖 | Codex |
| v1.1.810 | 2026-06-29 | 补充迭代版本总览代码评审聚合验收：版本驾驶舱必须展示 Code Review 报告数、待确认数、风险、执行器和关联任务入口；后端版本流与前端页面测试覆盖 | Codex |
| v1.1.809 | 2026-06-29 | 补充真实全链路回归脚本 AI 动作草案治理场景验收：`--suite assistant-draft-governance` 必须验证风险、影响、权限、差异、查看/修改/确认和审计链路；`test_release_smoke_script.py` 覆盖 | Codex |
| v1.1.808 | 2026-06-29 | 补充真实全链路回归脚本 Runner Token 轮换验收：`--suite runner-reliability` 必须验证旧 Token 拒绝、新 Token 心跳可用和 token 版本递增；`test_release_smoke_script.py` 覆盖 | Codex |
| v1.1.807 | 2026-06-29 | 补充真实全链路回归脚本版本总览快速场景验收：`--suite version-dashboard` 通过公开 API 校验需求/任务/分支聚合、状态推进影响和发布/分支阻塞项；`test_release_smoke_script.py` 覆盖 | Codex |
| v1.1.806 | 2026-06-29 | 补充真实全链路回归脚本场景集验收：`--suite full` 保持完整链路，`--suite runner-reliability` 可单独执行 AI 执行器 Runner 租约/死信门禁；`test_release_smoke_script.py` 覆盖 | Codex |
| v1.1.805 | 2026-06-29 | 补充 AI 执行器 Runner 安装包版本验收：env、manifest、runner_config 和 README 必须暴露安装包版本；`test_plugin_management.py` 覆盖 | Codex |
| v1.1.804 | 2026-06-29 | 补充真实全链路回归脚本 AI 执行器 Runner 可靠性验收：脚本必须通过公开 API 覆盖任务认领、短租约超时重派、死信转换、死信列表和任务日志；`test_release_smoke_script.py` 覆盖脚本 marker | Codex |
| v1.1.803 | 2026-06-29 | 补充真实全链路回归脚本版本总览阻塞处理队列门禁：所有阻塞项需携带来源、级别、标题、原因、动作目标和解除条件；`test_release_smoke_script.py` 覆盖脚本 marker | Codex |
| v1.1.802 | 2026-06-29 | 补充迭代版本总览阻塞处理队列验收：阻塞项需按严重级别和来源类型排序展示优先级、解除条件和处理入口；`IterationVersionsPage.test.tsx` 覆盖 | Codex |
| v1.1.801 | 2026-06-29 | 补充迭代版本总览发布准备清单验收：版本总览必须在明细表前展示需求范围、研发任务、代码分支、代码巡检、Bug 收敛、发布证据和状态推进影响；`IterationVersionsPage.test.tsx` 覆盖 | Codex |
| v1.1.800 | 2026-06-29 | 补充定时作业常量拆分守护：`scheduled_job_constants` 承接运行状态、排序字段和默认编排策略常量，避免 `scheduled_jobs.py` 重新贴近行数预算上限 | Codex |
| v1.1.799 | 2026-06-29 | 补充 PostgreSQL 旧库兼容迁移守护：启动兼容迁移必须纳入 `073_code_inspection_risk_acceptance_expiry.sql`，避免全链路代码巡检写入 finding 时缺列 | Codex |
| v1.1.798 | 2026-06-29 | 补充真实全链路回归脚本版本总览发布证据门禁验收：脚本必须推进版本到测试中，并校验缺少成功发布记录时返回 `product_version` 级发布阻塞项 | Codex |
| v1.1.797 | 2026-06-29 | 补充版本总览发布准入验收：测试中版本推进到已发布前若缺少成功发布记录，版本总览必须返回可处理发布阻塞项并跳转按版本筛选的发布记录；后端版本流和 IterationVersions 页面测试覆盖 | Codex |
| v1.1.796 | 2026-06-29 | 补充定时作业访问与运行 helper 拆分守护：`scheduled_job_access` 承接权限/产品范围 helper，`scheduled_job_runtime` 承接时区、动态输入映射和异常摘要，`scheduled_jobs.py` 行数预算收紧到 2600，定时作业与安全边界回归覆盖 | Codex |
| v1.1.795 | 2026-06-29 | 补充插件连接配置 helper 拆分守护：`plugin_connection_config` 承接 GitHub/GitLab 连接地址解析、请求配置规范化和 GitHub 认证校验，`plugins.py` 行数预算收紧到 2600，插件连接回归覆盖 | Codex |
| v1.1.794 | 2026-06-29 | 补充前端系统管理 client 拆分守护：`systemManagementClient` 承接用户、角色、菜单和权限诊断 API，`aiBrain.ts` 行数预算收紧到 2400，SystemManagementPages/ManagementCrudServices/typecheck 回归 | Codex |
| v1.1.793 | 2026-06-29 | 补充知识索引健康中心权限命中验收：`GET /api/knowledge/index-health` 必须返回 `permission_scope`，页面展示角色命中文档数、全局知识权限或知识空间 scope | Codex |
| v1.1.792 | 2026-06-29 | 补充授权仓储拆大文件守护：`authorization.py` 纳入 2800 行预算，默认菜单/角色授权配置拆到 `authorization_defaults` 后需继续通过 RBAC 与架构守护测试 | Codex |
| v1.1.791 | 2026-06-29 | 补充 AI 执行器 Runner 拆大文件守护：`ai_executor_runners.py` 纳入 2800 行预算，安装包构造拆到独立模块后需继续通过 Runner 安装包和架构守护测试 | Codex |
| v1.1.790 | 2026-06-29 | 补充代码巡检风险接受到期治理验收：`accepted_risk` 缺少到期时间必须拒绝，详情页需提供独立“接受风险”入口、责任人和到期时间，并在详情和 dashboard 标记过期接受风险待复核 | Codex |
| v1.1.789 | 2026-06-29 | 补充工程拆大文件守护验收：架构守护测试固定关键领域入口文件 2800 行预算，防止已拆分模块重新膨胀 | Codex |
| v1.1.788 | 2026-06-29 | 补充真实全链路回归脚本提交人治理待办验收：脚本必须校验代码巡检 dashboard `committer_governance` 中的提交人闭环状态、活跃严重问题、Bug 覆盖和整改任务覆盖 | Codex |
| v1.1.787 | 2026-06-29 | 补充代码巡检提交人治理待办验收：dashboard 必须按提交人聚合活跃严重问题、缺 Bug、缺整改任务和待审批忽略；后端与前端页面测试覆盖 | Codex |
| v1.1.786 | 2026-06-29 | 补充角色详情单角色访问预览验收：角色详情必须集中展示可见菜单路径、操作权限名称、产品/知识空间/全局范围和风险提示；`SystemManagementPages.test.tsx` 覆盖 | Codex |
| v1.1.785 | 2026-06-29 | 补充真实全链路回归脚本质量门禁验收：脚本必须校验本地完整扫描质量门禁失败、报告详情持久化、治理概览失败原因聚合和版本总览质量门禁阻塞项 | Codex |
| v1.1.784 | 2026-06-29 | 补充 AI 动作确认中心详情治理面板回归：草案详情必须展示风险原因、权限必需/缺失/问题、修复动作、审计事件和失败重试状态；`AssistantDraftsPage.test.tsx` 覆盖 | Codex |
| v1.1.783 | 2026-06-29 | 补充知识中心索引健康组件化回归：`KnowledgeIndexHealthPanel` 拆出后必须继续展示可检索、向量/关键词、chunk、Embedding、召回模式和健康问题动作；`KnowledgePage.test.tsx`、lint、typecheck 和真实知识中心页面 smoke 必须通过 | Codex |
| v1.1.782 | 2026-06-29 | 补充版本总览组件继续细分回归：摘要行动区、状态分布、推进影响、阻塞项和质量交付明细拆到独立组件后，`IterationVersionsPage.test.tsx`、lint、typecheck 和真实 `/delivery/versions` 页面 smoke 必须继续通过 | Codex |
| v1.1.781 | 2026-06-29 | 补充迭代版本页版本总览组件拆分回归：`VersionDashboardModal` 抽出后，版本总览弹窗仍需展示下一步行动、交付健康摘要、状态分布、推进影响、阻塞项处理入口和各明细表；`IterationVersionsPage.test.tsx`、typecheck 和真实 `/delivery/versions` 页面 smoke 必须通过 | Codex |
| v1.1.780 | 2026-06-29 | 补充前端系统运维 client 拆分回归：`systemOperationsClient` / `devopsOperationsClient` 拆分后必须保持 `services/aiBrain.ts` 兼容导出；`npm run typecheck`、定时作业、插件、AI 能力配置、研发执行器策略、团队看板和日志监控页面测试覆盖 | Codex |
| v1.1.779 | 2026-06-29 | 补充定时作业 AI 处理拆分回归：不可检索知识引用拒绝、Skill 输出映射契约 dry-run、AI 生成洞察、代码巡检 AI/结果动作和助手草案确认继续覆盖 `scheduled_job_ai_processing` 拆分后的契约 | Codex |
| v1.1.778 | 2026-06-29 | 补充定时作业 AI 能力配置拆分回归：AI Skill/Agent 分页查询、包上传、管理员管理、草案确认 PostgreSQL runtime store 和不可检索知识引用拒绝继续覆盖 `scheduled_job_ai_capabilities`、`scheduled_job_store` 拆分后的契约 | Codex |
| v1.1.777 | 2026-06-29 | 补充 AI 助手引用格式化拆分回归：`assistant_reference_formatting` 覆盖执行诊断链接、定时作业运行标题、定时作业语义匹配、候选按类型均衡合并和权限标签；原引用候选/解析集成测试继续覆盖接口契约 | Codex |
| v1.1.776 | 2026-06-29 | 补充 AI 助手确定性意图拆分回归：`assistant_chat_intents` 直接覆盖执行一次、定时作业诊断、插件连接诊断、任务向导输出和引用去重，原注册表集成测试继续覆盖 intent metadata | Codex |
| v1.1.775 | 2026-06-29 | 补充插件结果写入记录拆分回归：结果写入目标、future write target action log、产品 scope 过滤和结果写入记录分页观测继续覆盖 `plugin_result_mapping` 与 `plugin_result_write_records` 拆分后的契约 | Codex |
| v1.1.774 | 2026-06-29 | 补充插件删除保护拆分回归：`plugin_delete_protection` 需识别定时作业 `plugin_action_ids`、`plugin_connection_ids` 和 orchestration 多引用，插件管理删除接口在备用动作/连接仍被多数据源作业引用时返回 409 | Codex |
| v1.1.773 | 2026-06-29 | 补充定时作业本地代码巡检拆分回归：`scheduled_job_native_scan` 覆盖多仓库 ID 合并去重和 queued 摘要默认分支，原多仓库本地完整扫描流程继续由代码巡检治理测试兜底 | Codex |
| v1.1.772 | 2026-06-29 | 补充定时作业审计与多引用解析拆分回归：`scheduled_job_refs` 覆盖 legacy 字段和 orchestration 多 ID 合并去重，`scheduled_job_audit` 覆盖运行审计上下文 | Codex |
| v1.1.771 | 2026-06-29 | 补充定时作业运行记录投影拆分回归：`scheduled_job_run_projection` 直接覆盖 trace graph 补齐和 rerun 来源摘要，避免大文件拆分后运行详情字段漂移 | Codex |
| v1.1.770 | 2026-06-29 | 补充真实全链路回归脚本版本总览阻塞项治理动作验收：脚本必须校验阻塞项动作标签、目标主体、解除条件，并覆盖代码巡检报告和派生 Bug 处理入口 | Codex |
| v1.1.769 | 2026-06-29 | 补充迭代版本总览阻塞项治理动作验收：阻塞项需展示解除条件和处理入口，并可跳转需求、Bug、代码巡检、版本分支或发布记录管理页；后端和 `IterationVersionsPage.test.tsx` 覆盖 | Codex |
| v1.1.768 | 2026-06-29 | 补充代码巡检增量扫描快照验收：本地增量扫描报告必须保留 `incremental_from_commit`、`incremental_file_count` 和 `is_full_scan=false`，详情页展示扫描范围、增量基线 Commit 和增量文件数 | Codex |
| v1.1.767 | 2026-06-29 | 补充真实全链路回归脚本知识索引健康验收：知识沉淀采纳后必须调用 `GET /api/knowledge/index-health` 验证可检索文档、chunk 和召回模式，并通过 `POST /api/knowledge/search` 命中沉淀文档；`test_release_smoke_script.py` 覆盖脚本 marker | Codex |
| v1.1.766 | 2026-06-29 | 补充迭代版本驾驶舱升级为版本总览验收：版本列表入口改为“总览”，弹窗顶部必须集中展示下一步行动，包括推进到下一阶段、查看需求、维护分支、查看 Bug、代码巡检、发布记录和版本全链路；`IterationVersionsPage.test.tsx` 覆盖 | Codex |
| v1.1.765 | 2026-06-28 | 补充真实全链路回归脚本强校验：脚本需验证本地完整扫描 finding、提交人归因、治理覆盖率、派生 Bug/整改任务 ID、版本驾驶舱状态分布、full-chain 主体解析、团队看板计数和 AI 助手会话历史引用；版本驾驶舱需纳入同版本巡检报告派生 Bug | Codex |
| v1.1.764 | 2026-06-28 | 补充迭代版本驾驶舱总览增强验收：驾驶舱弹窗必须展示需求/任务/Bug 状态分布和推进影响明细，覆盖同步推进、阻塞和保持不变需求；`IterationVersionsPage.test.tsx` 覆盖 | Codex |
| v1.1.763 | 2026-06-28 | 补充 AI 执行器任务租约重派与死信队列验收：Runner 认领任务后租约过期应先重派并累加 `reclaim_count`，再次过期超过 `max_reclaim_count` 后进入 `dead_letter`，任务列表可按死信状态筛选；`test_plugin_management.py` 覆盖 | Codex |
| v1.1.762 | 2026-06-28 | 补充角色权限与范围预览验收：角色管理页必须基于 RBAC 策略矩阵展示全局/产品范围、未配置范围、高风险权限和菜单权限缺口，并在角色列表与详情展示 scope 授权；`SystemManagementPages.test.tsx` 覆盖 | Codex |
| v1.1.761 | 2026-06-28 | 补充知识中心索引健康视图验收：页面基于当前远程分页结果展示可检索、向量就绪、关键词兜底、索引失败、处理中和分块版本指标，并为索引失败、向量待补、分块缺失和导入中状态提供处理入口；`KnowledgePage.test.tsx` 覆盖 | Codex |
| v1.1.760 | 2026-06-28 | 补充代码巡检报告详情治理闭环验收：详情响应 `governance_summary` 必须返回闭环状态、Bug/整改任务覆盖率、待审批忽略和治理待办；详情页展示治理闭环和 finding 整改任务链接；`test_code_inspection_governance.py` 与 `CodeInspectionsPage.test.tsx` 覆盖 | Codex |
| v1.1.759 | 2026-06-28 | 补充 AI 动作确认中心治理摘要验收：`GET /api/assistant/action-drafts` 和详情响应必须展示影响对象、权限状态、执行前后差异、失败重试和审计链路；`test_assistant_draft_workbench.py` 与 `AssistantDraftsPage.test.tsx` 覆盖 | Codex |
| v1.1.758 | 2026-06-28 | 补充真实全链路回归脚本验收：`scripts/full_chain_regression.py` 通过公开 API 串联用户反馈、需求、迭代版本、AI 任务、Review、知识沉淀、版本分支、代码巡检、Bug/整改任务、版本驾驶舱、full-chain、团队看板和 AI 助手引用；任务启动 deterministic 模式仅允许管理员显式验收，跳过 Runner/模型网关并写审计 | Codex |
| v1.1.757 | 2026-06-28 | 补充 AI 助手失败草案重新打开验收：`POST /api/assistant/action-drafts/{draft_id}/retry` 仅允许 failed 草案回到 pending，保留失败历史、清空失败 run、写审计；草案任务台展示“重新打开”入口；`test_assistant_draft_workbench.py` 与 `AssistantDraftsPage.test.tsx` 覆盖 | Codex |
| v1.1.756 | 2026-06-28 | 补充模型网关配置列表生产查询路径验收：分页请求必须调用模型网关配置 count/page read model，筛选和排序下推到仓储层，响应仍脱敏密钥并返回 `query/performance`；`test_model_gateway.py` 覆盖 | Codex |
| v1.1.755 | 2026-06-28 | 补充模型调用日志服务端分页验收：`GET /api/model-gateway/logs?page=1&page_size=...` 必须返回分页元数据、`query/performance`、支持 AI 任务/用途/状态筛选和排序白名单，非法排序字段返回校验错误；模型网关页最近调用日志表必须携带远程分页排序参数并展示查询耗时；`test_model_gateway.py` 与 `ModelGatewayPage.test.tsx` 覆盖 | Codex |
| v1.1.754 | 2026-06-28 | 补充 AI 助手角色快捷任务配置服务端分页验收：`GET /api/assistant/role-quick-task-configs?page=1&page_size=...` 必须调用快捷任务配置 count/page read model，支持关键字、任务/分组启停状态、角色、权限、企业、草案模板、模板版本和排序白名单并返回 `query/performance`；`test_assistant_chat.py` 与 `AssistantRoleQuickTasksPage.test.tsx` 覆盖 | Codex |
| v1.1.753 | 2026-06-28 | 补充 AI 助手 @ 能力配置服务端分页验收：`GET /api/assistant/action-reference-configs?page=1&page_size=...` 必须调用动作引用配置 count/page read model，支持关键字、启停状态、角色、权限、企业、模板版本和排序白名单并返回 `query/performance`；`test_assistant_chat.py` 与 `AssistantActionReferencesPage.test.tsx` 覆盖 | Codex |
| v1.1.752 | 2026-06-28 | 补充任务中心待确认 Review 子列表服务端分页验收：`GET /api/reviews/pending?ai_task_id=&page=&page_size=&sort_by=&sort_order=` 必须调用待确认 Review count/page read model，返回 `query/performance`；任务操作进入确认弹窗时必须携带 `ai_task_id`，不再全量拉取后前端过滤；`test_workflow_runtime_persistence.py` 与 `TaskCenterPage.test.tsx` 覆盖 | Codex |
| v1.1.751 | 2026-06-28 | 补充 P0 路由-权限点-数据范围契约矩阵验收：需求、Bug、知识文档、代码巡检、定时作业、插件配置/调用日志和 AI 执行器 Runner/任务需覆盖 OpenAPI 路由、无权限 403、产品或知识空间 scope 过滤；`test_security_boundaries.py::test_p0_management_routes_have_permission_and_scope_contract_matrix` 覆盖 | Codex |
| v1.1.750 | 2026-06-28 | 补充版本代码分支配置进入统一需求全链路验收：`product_version_branch_config` / `branch_config` 可解析回同版本需求链路，版本分支列表和 AI 助手引用生成“全链路”深链；`test_lifecycle_context.py`、`IterationVersionsPage.test.tsx` 与 `AssistantFullChainLinks.test.tsx` 覆盖 | Codex |
| v1.1.749 | 2026-06-28 | 补充需求全链路执行诊断证据验收：full-chain payload 必须返回 `execution_traces/summary.execution_traces/type=execution_trace`，页面阶段明细可跳转执行诊断中心；`test_lifecycle_context.py` 与 `RequirementFullChainPage.test.tsx` 覆盖 | Codex |
| v1.1.748 | 2026-06-28 | 补充结果写入记录分页观测验收：`GET /api/system/result-write-records?page=1&page_size=...` 返回 `query/performance`，非法排序字段返回校验错误；`test_plugin_management.py` 覆盖 | Codex |
| v1.1.747 | 2026-06-28 | 补充结果写入记录产品 scope 验收：具备插件管理权限但仅授权单产品的用户查询 `result-write-records` 时，只能看到授权产品定时作业或运行实例关联写入记录；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.746 | 2026-06-28 | 补充插件调用日志产品 scope 验收：具备插件管理权限但仅授权单产品的用户查询 `plugin-invocation-logs` 时，只能看到授权产品定时作业或运行实例关联日志，PostgreSQL count/page read model 下推 `product_scope_ids`；`test_security_boundaries.py` 与 `test_plugin_management.py` 覆盖 | Codex |
| v1.1.745 | 2026-06-28 | 补充执行诊断主体进入统一需求全链路验收：`scheduled_job_run`、`ai_executor_task`、`model_gateway_log` 和 `execution_trace` 可解析回需求链路，scope 外仍返回 404；`test_lifecycle_context.py` 与 `ExecutionTracesPage.test.tsx` 覆盖 | Codex |
| v1.1.744 | 2026-06-28 | 补充系统管理权限点验收：具备 `system.users.manage`、`system.model_gateway.manage`、`audit.read` 的自定义角色可访问用户管理、模型网关和审计事件接口，普通 reviewer 仍返回 403；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.743 | 2026-06-28 | 补充 AI 助手草案任务台 `validation_status` 数据库侧筛选验收：列表服务携带校验状态筛选时仍必须调用草案分页 read model，不得退回全量草案读取；`test_assistant_draft_workbench.py` 与仓储边界测试覆盖 | Codex |
| v1.1.742 | 2026-06-28 | 补充产品主体、迭代版本和版本分支权限点与产品 scope 验收：自定义 `product.read` / `product.manage` 角色只能查看和维护授权产品、版本和分支配置，scope 外列表过滤或返回 404；产品和版本 SQL read model 下推 `product_scope_ids`；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.741 | 2026-06-28 | 补充产品模块权限点和产品 scope 验收：自定义 `product.read` / `product.manage` 角色只能访问和维护授权产品模块，scope 外列表、创建、更新和删除返回 404；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.740 | 2026-06-28 | 补充相关系统权限点和产品 scope 验收：自定义 `product.read` / `product.manage` 角色只能访问和维护授权产品相关系统，scope 外列表、创建、更新、改绑和删除返回 404；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.739 | 2026-06-28 | 补充产品 Git 仓库权限点和产品 scope 验收：自定义 `product.read` / `product.manage` 角色只能访问和维护授权产品代码库，scope 外列表、创建、更新和删除返回 404；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.738 | 2026-06-28 | 补充 AI 执行器任务产品 scope 验收：具备插件管理权限但仅授权单产品的用户查询 Runner 任务列表或日志时，不得看到 scope 外产品定时作业派生任务；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.737 | 2026-06-28 | 补充知识沉淀审核权限点验收：具备 `knowledge.deposit.decide` 的自定义角色可查询审核列表，仅具备 `knowledge.read` 的查看者仍被拒绝；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.736 | 2026-06-28 | 补充角色治理列表 PostgreSQL read model 验收：`GET /api/system/roles?page=1&page_size=10` 必须优先调用角色 summary count/page 查询，覆盖业务角色、菜单范围、权限点、分类、状态、排序白名单和 `query/performance` 观测；`test_rbac_system_api.py` 覆盖 | Codex |
| v1.1.735 | 2026-06-28 | 补充知识沉淀候选列表远程分页验收：`GET /api/knowledge/deposits?page=1&page_size=10` 必须优先调用 PostgreSQL count/page read model，支持状态筛选、排序白名单和 `query/performance` 观测；`test_knowledge_governance.py` 覆盖 | Codex |
| v1.1.734 | 2026-06-28 | 补充插件调用日志列表远程分页验收：`GET /api/system/plugin-invocation-logs?page=1&page_size=10` 必须优先调用 PostgreSQL count/page read model，支持动作、定时作业、运行实例和状态筛选、排序白名单和 `query/performance` 观测；`test_plugin_management.py` 覆盖 | Codex |
| v1.1.733 | 2026-06-28 | 补充 AI 执行器任务列表远程分页验收：`GET /api/system/ai-executor-tasks?page=1&page_size=10` 必须优先调用 PostgreSQL count/page read model，支持 Runner、研发任务、定时作业运行和状态筛选、排序白名单和 `query/performance` 观测；`test_plugin_management.py` 覆盖 | Codex |
| v1.1.732 | 2026-06-27 | 补充核心管理列表权限和产品 scope 验收：需求、Bug、知识中心和代码巡检列表必须服务端校验 read 权限；受限产品用户查询需求/Bug/代码巡检只能返回 scope 内业务记录 | Codex |
| v1.1.731 | 2026-06-27 | 补充 AI 助手裸 `@` 默认候选均衡验收：执行诊断来源加入后不得挤掉知识文档、需求、研发任务、定时作业、运行记录、插件动作、插件连接、AI 角色和 Skill，模型网关日志等诊断引用仍可在后续候选中出现 | Codex |
| v1.1.730 | 2026-06-27 | 补充知识中心主列表服务端分页验收：`GET /api/knowledge/documents?page=1&page_size=10` 必须优先调用知识文档 PostgreSQL count/page read model，在数据库侧完成权限、空间/目录、类型、索引状态、权限角色、关键字筛选和白名单排序；外层 Postgres repository 委托和 `KnowledgePage.test.tsx` 远程请求覆盖 | Codex |
| v1.1.729 | 2026-06-27 | 补充 AI 能力配置主表服务端分页验收：AI角色默认请求 `ai-agents?page=1&page_size=10&sort_by=code&sort_order=asc`，Skill 默认请求 `ai-skills?page=1&page_size=10&sort_by=code&sort_order=asc`；仓储测试覆盖 AI角色/Skill count/page SQL、筛选和排序白名单，`AiCapabilitiesPage.test.tsx` 覆盖远程筛选请求 | Codex |
| v1.1.728 | 2026-06-27 | 补充定时作业配置/运行记录主表服务端分页验收：作业配置默认请求 `scheduled-jobs?page=1&page_size=10&sort_by=next_run_at&sort_order=desc`，运行记录默认请求 `scheduled-job-runs?page=1&page_size=10&sort_by=started_at&sort_order=desc`，仓储测试覆盖运行记录 count/page SQL、产品 scope 和排序白名单 | Codex |
| v1.1.727 | 2026-06-27 | 补充插件管理连接/动作主表服务端分页验收：连接页签默认请求 `plugin-connections?page=1&page_size=10&sort_by=plugin_id&sort_order=asc`，环境筛选保留分页排序参数；动作页签默认请求 `plugin-actions?page=1&page_size=10&sort_by=plugin_id&sort_order=asc`，`PluginsPage.test.tsx` 覆盖 | Codex |
| v1.1.726 | 2026-06-27 | 补充执行诊断到 AI 助手深链上下文验收：`assistant_chat_run` 等执行诊断来源必须能通过助手引用候选解析为本次上下文，未知引用类型仍只保留 route prompt；`test_assistant_chat.py` 与 `AssistantPage.test.tsx` 覆盖 | Codex |
| v1.1.725 | 2026-06-27 | 补充 AI 助手草案任务台 read model 验收：PostgreSQL 外层仓储必须暴露草案分页 read model，列表服务优先使用数据库侧当前用户、动作、状态、校验状态、时间、关键词、排序和分页查询；`test_assistant_draft_workbench.py` 与 `test_persistence_repository_boundaries.py` 覆盖 | Codex |
| v1.1.724 | 2026-06-27 | 补充受控运维接口权限验收：定时作业、运行记录、插件、连接、动作、调用日志和 AI 执行器列表必须服务端校验专项权限，定时作业执行权限用户只能看到或运行产品 scope 内对象；`test_security_boundaries.py` 覆盖 | Codex |
| v1.1.723 | 2026-06-27 | 补充知识沉淀审核全链路入口验收：知识中心“沉淀审核”列表每条候选提供 `knowledge_deposit` 主体全链路链接，审核表格保持固定列宽和横向滚动；`KnowledgePage.test.tsx` 覆盖 | Codex |
| v1.1.722 | 2026-06-27 | 补充 AI 助手引用全链路入口验收：助手上下文和消息引用对可解析交付主体展示“全链路”，`iteration_version` 可通过 `/api/lifecycle/full-chain` 解析回需求链路；`AssistantFullChainLinks.test.tsx` 与 `test_lifecycle_context.py` 覆盖 | Codex |
| v1.1.721 | 2026-06-27 | 补充需求全链路版本分支和审计事件验收：full-chain 响应、阶段明细、时间线和导出报告必须展示 `branch_configs` 与脱敏 `audit_events`；`test_lifecycle_context.py` 与 `RequirementFullChainPage.test.tsx` 覆盖 | Codex |
| v1.1.720 | 2026-06-27 | 补充 P0 优化验收：研发执行器策略列表必须走服务端分页/筛选/排序并返回性能观测；需求全链路接口必须校验读权限和产品 scope；`test_management_list_read_models.py`、`test_rd_task_executor_policies.py`、`test_lifecycle_context.py` 覆盖 | Codex |
| v1.1.719 | 2026-06-27 | 补充需求全链路统一主体入口验收：`/api/lifecycle/full-chain` 需支持 Bug、迭代版本和代码巡检报告解析到需求链路，响应包含 `anchor` 和代码巡检报告摘要；`test_lifecycle_context.py` 与 `RequirementFullChainPage.test.tsx` 覆盖 | Codex |
| v1.1.718 | 2026-06-27 | 补充执行诊断列表性能验收：普通列表查询必须复用已有快照且不触发同步重建，`refresh=true` 才强制刷新；`test_execution_traces.py` 覆盖 | Codex |
| v1.1.717 | 2026-06-26 | 补充代码巡检门禁失败原因验收：治理概览需返回并展示 `quality_gate_violations[]`，覆盖指标、级别、触发数、报告数和实际/阈值 | Codex |
| v1.1.716 | 2026-06-26 | 补充执行诊断整条链路诊断包验收：详情页需提供“问 AI 分析链路”和“复制诊断包”，助手链接按根对象携带 prompt、`diagnostic_trace_id` 和可选 `diagnostic_node_id`，包含失败节点和建议输出结构；当 prompt 缺失时助手需按 Trace 详情重建问题；`ExecutionTracesPage.test.tsx` 和 `AssistantPage.test.tsx` 覆盖 | Codex |
| v1.1.715 | 2026-06-26 | 补充定时作业工作台数据加载 hook 化验收：作业/运行/模板/插件/产品/AI/知识/模型网关/catalog 加载从主页面拆出后，`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.714 | 2026-06-26 | 补充定时作业运行详情状态 hook 化验收：运行详情路由深链、结果写入记录聚焦、生成模板和复制本次配置继续由 `ScheduledJobsPage.test.tsx` 覆盖，typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.713 | 2026-06-26 | 补充插件管理 Runner 运维 hook 化验收：Runner 新增/编辑、安装包下载、测试诊断、Token 轮换、日志查看和取消任务由 `PluginsPage.test.tsx` 覆盖，typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.712 | 2026-06-26 | 补充代码巡检治理概览组件化验收：治理概览和通用展示 helper 拆出后，`CodeInspectionsPage.test.tsx`、typecheck、lint 和真实 `/governance/code-inspections` 页面 smoke 必须通过 | Codex |
| v1.1.711 | 2026-06-26 | 补充执行诊断列表异常节点预览验收：列表需展示首个 `diagnostic_nodes` 来源、状态和错误摘要，成功链路展示无异常节点；`ExecutionTracesPage.test.tsx` 覆盖 | Codex |
| v1.1.710 | 2026-06-26 | 补充定时作业执行链路节点构建拆分验收：执行链路状态预览、数据连接测试和模板表单能力由 `ScheduledJobsPage.test.tsx` 覆盖，主页面不再直接拼装节点展示细节 | Codex |
| v1.1.709 | 2026-06-26 | 补充插件管理删除保护验收：定时作业通过 `plugin_connection_ids` / `plugin_action_ids` 数组引用连接或动作时，插件页必须阻断删除并展示占用作业；`PluginsPage.test.tsx` 覆盖 | Codex |
| v1.1.709 | 2026-07-01 | 补充插件管理页首屏收敛验收：页面不得常驻展示“系统变量预览”“常用变量”或“通用调用链路”，连接/动作参数表单仍需提供系统变量插入选项，连接测试诊断继续展示变量解析前后；`PluginsPage.test.tsx` 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.708 | 2026-06-26 | 补充执行诊断 `diagnostic_nodes` 验收：列表和详情需返回异常/运行中节点安全摘要，成功链路为空数组，失败 AI 助手链路不暴露 metadata；`test_execution_traces.py` 覆盖 | Codex |
| v1.1.707 | 2026-06-26 | 补充菜单资源与前端路由一致性验收：active 的可导航菜单 path 必须在前端 `routes.ts` 注册，研发任务、定时作业、插件管理、执行诊断等关键菜单路径不得回退旧入口；`test_menu_route_consistency.py` 覆盖 | Codex |
| v1.1.706 | 2026-06-26 | 补充执行诊断来源类型筛选文案验收：列表查询表单必须展示“来源类型”，对应 `source_type` 可筛选根或节点来源类型；`ExecutionTracesPage.test.tsx` 覆盖文案存在 | Codex |
| v1.1.705 | 2026-06-26 | 补充可复用执行诊断链接验收：`ExecutionTraceLink` 必须生成 `source_id + source_type` 深链，缺少 `source_type` 时展示 fallback，不生成仅按 ID 定位的歧义链接；`ExecutionTraceLink.test.tsx` 覆盖组件行为 | Codex |
| v1.1.704 | 2026-06-26 | 补充执行诊断详情深链验收：详情页关联对象、诊断建议节点和节点表中的来源 ID 链接必须同时携带 `source_id` 与 `source_type`；`ExecutionTracesPage.test.tsx` 覆盖链接生成 | Codex |
| v1.1.703 | 2026-06-26 | 补充产品/版本上下文选项分页验收：共享产品选择器必须按服务端 `total` 继续读取后续页，第二页产品及其迭代版本需可出现在需求、Bug、任务和洞察表单上下文中；`ProductContextOptions.test.ts` 覆盖分页合并 | Codex |
| v1.1.702 | 2026-06-26 | 补充 AI 助手运行状态时间格式验收：检测时间必须使用统一展示时区格式 `YYYY-MM-DD HH:mm`，不得回退到浏览器本地 `toLocaleTimeString()`；`AssistantRuntimeStatus.test.tsx` 覆盖 UTC 到北京时间展示 | Codex |
| v1.1.701 | 2026-06-26 | 补充审计列表执行诊断入口验收：审计行需提供 `/governance/execution-traces?source_id=<audit_id>&source_type=audit_event` 深链，并保留原生命周期链路追踪动作；`App.test.tsx` 覆盖链接生成 | Codex |
| v1.1.700 | 2026-06-26 | 补充 AI 助手执行诊断深链验收：运行状态最近失败需按 `assistant_chat_run`、`model_gateway_log`、`scheduled_job_run` 跳统一执行诊断；运行诊断卡片中的 `plugin_invocation_log` 和 `model_gateway_log` 关联日志 ID 必须可点击到 `/governance/execution-traces?source_id=...&source_type=...`，`AssistantPage.test.tsx` 覆盖链接生成 | Codex |
| v1.1.699 | 2026-06-26 | 补充模型网关调用日志诊断入口验收：模型网关页需展示最近模型调用日志，并为每条日志提供 `/governance/execution-traces?source_id=...&source_type=model_gateway_log` 调用诊断链接；`ModelGatewayPage.test.tsx` 覆盖链接生成 | Codex |
| v1.1.698 | 2026-06-26 | 补充 Runner 执行日志诊断入口验收：插件管理 Runner 日志弹窗必须提供任务诊断、Runner 诊断和来源运行诊断链接，分别跳转 `/governance/execution-traces?source_id=...&source_type=ai_executor_task|ai_executor_runner|scheduled_job_run`；`PluginsPage.test.tsx` 覆盖链接生成 | Codex |
| v1.1.697 | 2026-06-26 | 补充管理列表性能观测扩展验收：产品、迭代版本、知识、审计、模型网关、执行诊断、日志监控、用户和 AI 助手草案任务台必须透传远程分页 `performance` 元数据；`ExecutionTracesPage.test.tsx` 覆盖执行诊断页查询耗时展示 | Codex |
| v1.1.696 | 2026-06-26 | 补充管理列表性能观测验收：统一列表底座必须展示远程分页查询耗时，`performance.slow=true` 时显示慢查询阈值和排查提示；需求、任务、Bug、用户洞察、代码巡检和角色列表需透传服务端 `performance` 元数据，`ManagementListPage.test.tsx` 覆盖查询耗时标签和慢查询提示 | Codex |
| v1.1.695 | 2026-06-26 | 补充 AI 助手页草案详情弹窗组件化验收：`AssistantDraftDetailModal` 承载 Payload、对比来源、字段差异和校验问题展示，草案卡主体继续保留确认、取消、详情打开和资源追踪编排；`AssistantPage.test.tsx`、typecheck、lint 和真实 `/assistant` 页面 smoke 必须通过 | Codex |
| v1.1.694 | 2026-06-26 | 补充 AI 助手草案应用前预检组件化验收：`AssistantDraftPreviewBlock` 承载字段差异、校验问题和修复动作入口，`assistantDraftPreviewHelpers` 统一卡片与详情中的差异值格式化；`AssistantPage.test.tsx`、typecheck、lint 和真实 `/assistant` 页面 smoke 必须通过 | Codex |
| v1.1.693 | 2026-06-26 | 补充 AI 助手草案配置向导组件化验收：`AssistantDraftWizardBlock` 承载向导步骤、AI 生成步骤草案、前置草案和手动调整入口；`AssistantPage.test.tsx`、typecheck、lint 和真实 `/assistant` 页面 smoke 必须通过 | Codex |
| v1.1.692 | 2026-06-26 | 补充插件管理弹窗组组件化验收：`PluginManagementModals` 承载 Runner Token/日志、插件、执行器、连接、动作和动作试运行弹窗装配；`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.691 | 2026-06-26 | 补充定时作业新增/编辑弹窗组件化验收：`ScheduledJobFormModal` 承载 Modal 外壳、模板来源提示、作业模板选择、编排预览、基础信息、数据连接、代码仓库、AI执行、动作配置、调度配置和全链路试运行结果展示，主页面仍负责字段联动、提交和试运行；`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.690 | 2026-06-26 | 补充定时作业页签组件化验收：`ScheduledJobManagementTabs` 承载作业配置与运行记录两个页签装配，页面继续保留新增、编辑、删除、复制、运行、复跑、运行详情和深链打开能力；`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.689 | 2026-06-26 | 补充插件管理页签组件化验收：`PluginManagementTabs` 承载插件市场、插件、连接、执行器和动作五个页签装配，插件页主文件继续保留数据加载、弹窗和事件编排；`PluginsPage.test.tsx`、typecheck 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.688 | 2026-06-26 | 补充 DB-first 兼容层持续门禁验收：`test_memory_store_usage_audit.py` 必须扫描当前 `apps/api/app` 并确认 P0/P1 为 0；扫描脚本提供 `--fail-on-p1`，用于 CI 同时阻断直接写/helper 和直接读 `current_store` 残留 | Codex |
| v1.1.687 | 2026-06-26 | 补充角色治理列表服务端查询验收：`GET /api/system/roles` 必须支持分页、筛选、排序、非法排序字段校验和 `query/performance` 观测；角色管理页请求必须携带远程分页参数，不得退回前端全量过滤 | Codex |
| v1.1.686 | 2026-06-26 | 补充 AI 助手草案任务台组件化验收：摘要指标条、详情弹窗和草案状态/风险/校验展示 helper 必须从页面主文件拆出，页面继续保留待确认、失败、已采纳、采纳率、处理率、用户修改率、来源链路、继续编辑、确认和取消能力；`AssistantDraftsPage.test.tsx`、typecheck、lint 和真实 `/assistant/drafts` 页面 smoke 必须通过 | Codex |
| v1.1.685 | 2026-06-26 | 补充插件管理工作区指南组件化验收：系统变量预览、全部变量弹窗入口和通用调用链路说明必须从主页面拆到 `PluginWorkspaceGuide`，连接/动作弹窗继续复用同一系统变量选项；`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.684 | 2026-06-25 | 补充定时作业表格组件化验收：作业配置表格与运行记录表格必须从主页面拆到 `ScheduledJobConfigTable` / `ScheduledJobRunTable`，保留新增、刷新、编辑、复制、运行、删除、详情、复制配置、复跑、横向滚动和表格设置能力；`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.683 | 2026-06-25 | 补充 AI 能力配置页列表标准化验收：AI角色与 Skill 管理页签必须复用统一管理列表底座，保留新增/编辑/停用和 Skill 包上传，同时支持关键词、状态、模型网关、来源、人工确认筛选、本地筛选视图保存、横向滚动和表格设置；`AiCapabilitiesPage.test.tsx` 必须覆盖统一查询入口和保存视图入口 | Codex |
| v1.1.682 | 2026-06-25 | 补充 AI 助手 @ 能力配置列表标准化验收：页面必须复用统一管理列表底座，支持标题/关键词/角色/权限/URL 搜索、状态筛选、角色筛选、本地筛选视图保存、横向滚动和批量启停；`AssistantActionReferencesPage.test.tsx` 必须覆盖保存视图入口、统一查询表单过滤和批量状态操作 | Codex |
| v1.1.681 | 2026-06-25 | 补充研发执行器策略列表标准化验收：页面必须复用统一管理列表底座，支持策略名称、任务类型、执行器、产品和状态筛选、本地筛选视图保存、横向滚动和表格设置，同时新增/编辑弹窗仍不得出现 AI角色、Skill 或模型网关字段；`RdExecutorPoliciesPage.test.tsx` 必须覆盖统一筛选入口与保存视图入口 | Codex |
| v1.1.680 | 2026-06-25 | 补充定时作业 fallback 收口验收：AI Skill/Agent、定时作业配置、采集运行、运行记录和作业最近运行状态更新不得直接写 `current_store` 作业集合；MemoryStore 测试 fallback 必须通过定时作业集合 helper 保持配置、运行、取消、异步队列和采集状态可查询；`test_scheduled_ai_jobs.py`、插件调用作业测试与 DB-first 扫描必须通过 | Codex |
| v1.1.679 | 2026-06-25 | 补充插件管理 fallback 收口验收：标准插件同步、插件定义、连接、动作、调用日志和 Runner 任务关联不得直接写 `current_store` 插件集合；MemoryStore 测试 fallback 必须通过插件集合 helper 保持新增、复制、编辑、删除、连接测试和调用日志可查询；`test_plugin_management.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.678 | 2026-06-25 | 补充任务运行与评审产物 fallback 收口验收：任务审计 helper、Graph run/checkpoint、代码评审报告、任务确认后派生 Bug 和知识沉淀不得直接写 `current_store` 业务集合或调用 `current_store.audit()`；MemoryStore 测试 fallback 必须通过集合 helper 和审计 helper 保持可查询与 audit_events 切片语义；`test_task_runtime_fallbacks.py`、任务回归测试与 DB-first 扫描必须通过 | Codex |
| v1.1.677 | 2026-06-25 | 补充产品配置上下文 fallback 收口验收：`save_requirement_record` 不得直接写 `current_store.requirements`，`record_audit_event` 不得直接调用 `current_store.audit()`；无 `audit()` 方法的轻量测试上下文必须通过审计事件列表 helper 写入事件；`test_product_config_context.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.676 | 2026-06-25 | 补充用户反馈 fallback 收口验收：反馈创建、编辑和转需求不得直接写 `current_store.user_feedback` / `current_store.requirements`；MemoryStore 测试 fallback 必须通过 `save_user_feedback_record` 和 `save_user_feedback_requirement_conversion` 写入反馈、需求和 linked 状态；`test_user_feedback.py`、用户洞察持久化测试与 DB-first 扫描必须通过 | Codex |
| v1.1.675 | 2026-06-25 | 补充用户洞察审计 helper fallback 收口验收：`record_audit_event` 在轻量上下文无 `audit()` 方法时不得直接 append `current_store.audit_events`；必须通过审计事件列表 helper 写入并保留事件 ID、payload 和返回值一致性；`test_user_insights_persistence.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.674 | 2026-06-25 | 补充用户使用指标 fallback 收口验收：使用指标创建不得直接写 `current_store.user_usage_metrics`；MemoryStore 测试 fallback 必须通过 `save_user_usage_metric_record` 写入指标并可查询，repository 运行态继续通过 `save_user_usage_metric_record` 单记录写入指标和审计；`test_usage_metrics.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.673 | 2026-06-25 | 补充运营记录审计 helper fallback 收口验收：`record_audit_event` 在轻量上下文无 `audit()` 方法时不得直接 append `current_store.audit_events`；必须通过审计事件列表 helper 写入并保留事件 ID、payload 和返回值一致性；`test_operational_records.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.672 | 2026-06-25 | 补充模型网关配置与日志 fallback 收口验收：配置替换不得直接赋值 `current_store.model_gateway_configs`，模型调用日志不得直接 append `current_store.model_gateway_logs`；MemoryStore 测试 fallback 必须通过配置集合和日志集合 helper 更新，repository 运行态继续通过模型网关仓储/调用方事务持久化；`test_model_gateway_persistence.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.671 | 2026-06-25 | 补充 Mock Issue 写回 fallback 收口验收：写回创建不得直接写 `current_store.mock_writebacks` 或调用 `current_store.audit()`；MemoryStore 测试 fallback 必须通过写回保存 helper 同时落写结果和单条审计，repository 运行态重复 POST 必须复用本地读缓存保持幂等；`test_mock_writeback_persistence.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.670 | 2026-06-25 | 补充研发执行器策略 fallback 收口验收：策略刷新、新增、编辑、删除和资源缓存补齐不得直接写 `current_store.rd_task_executor_policies` / `current_store.products` / `current_store.product_git_repositories`；MemoryStore 测试 fallback 必须通过策略保存/删除和资源缓存 helper 保持 create/update/delete 语义；`test_rd_task_executor_policies.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.669 | 2026-06-25 | 补充需求主流程 DB-first fallback 收口验收：需求创建/编辑/删除/审批/拒绝/关闭、批量分配/排期/推进和生成产品详细设计任务不得在调用方直接写 `current_store.requirements` / `current_store.ai_tasks` 或调用 `current_store.audit()`；MemoryStore 测试 fallback 必须由需求保存、删除、任务联动和审计 helper 写入且避免重复审计；`test_requirement_lifecycle.py`、`test_requirement_batch_schedule.py`、`test_requirement_task_persistence.py`、`test_persistence_repository_boundaries.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.668 | 2026-06-24 | 补充生命周期上下文刷新 fallback 收口验收：上下文边和风险信号刷新不得直接写 `current_store.lifecycle_context_edges` / `current_store.lifecycle_risk_signals`；刷新必须移除当前锚点/任务范围旧记录、保留无关记录并 upsert 新边和新风险；`test_lifecycle_context.py`、`test_lifecycle_dashboard_persistence.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.667 | 2026-06-24 | 补充知识空间配置 fallback 收口验收：知识空间、空间成员和文件夹新增/更新不得直接写 `current_store.knowledge_spaces` / `current_store.knowledge_space_members` / `current_store.knowledge_folders`；成员更新必须保留按空间替换语义，文件夹更新必须保持路径与归档校验；`test_knowledge_space_assets.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.666 | 2026-06-24 | 补充知识导入结构化产物 fallback 收口验收：导入解析生成的知识资产、chunk set 和 chunks 不得直接写 `current_store.knowledge_assets` / `current_store.knowledge_chunk_sets` / `current_store.knowledge_chunks`；MemoryStore 测试 fallback 必须通过资产、chunk set 和 chunk helper 保持解析、归档、激活与索引语义；`test_knowledge_import_operations.py`、知识审计测试与 DB-first 扫描必须通过 | Codex |
| v1.1.665 | 2026-06-24 | 补充知识文档主流程 fallback 收口验收：上传、导入运行、失败标记、索引完成、重试、取消、chunk set 激活、重新解析和批量移动不得直接写 `current_store.knowledge_documents`；文档状态/目录更新必须通过只写文档的 `put_knowledge_document_to_memory`，不得清理已有 chunks；`test_knowledge_import_operations.py`、知识审计测试与 DB-first 扫描必须通过 | Codex |
| v1.1.664 | 2026-06-24 | 补充知识导入任务主流程 fallback 收口验收：上传、运行、失败标记、完成、重试、取消和重新解析不得直接写 `current_store.knowledge_import_jobs`；MemoryStore 测试 fallback 必须通过 import job helper 保持状态变更语义，`test_knowledge_import_operations.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.663 | 2026-06-24 | 补充知识导入 worker claim fallback 收口验收：worker 在无 repository claim 时必须通过 import job helper 标记 `locked_by` / `locked_until` / `attempt_count`，不得直接写 `current_store.knowledge_import_jobs`；repository 运行态仍优先调用 `claim_knowledge_import_job`；`test_knowledge_import_operations.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.662 | 2026-06-24 | 补充知识 chunk set MemoryStore fallback 写入收口验收：知识空间文档创建、编辑和重试索引不得直接写 `current_store.knowledge_chunk_sets`；MemoryStore 测试 fallback 必须通过 chunk set helper 写入/读取 building 与 active 状态，`test_knowledge_audit_persistence.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.661 | 2026-06-24 | 补充知识文档 MemoryStore fallback 写入收口验收：`clear_knowledge_chunks`、`apply_knowledge_document_to_memory` 和知识文档删除 fallback 不得直接写 `current_store.knowledge_documents` / `current_store.knowledge_chunks` / `current_store.knowledge_deposits`；MemoryStore 测试集合由 `_memory_collection` helper 操作并保持 chunk 替换语义；`test_knowledge_audit_persistence.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.660 | 2026-06-24 | 补充知识域审计 helper DB-first 收口验收：`record_audit_event` 不得调用 `current_store.audit()`；repository 运行态只生成待写审计事件，MemoryStore 测试 fallback 必须通过显式审计列表 helper 追加事件且避免重复；`test_knowledge_audit_persistence.py` 与 DB-first 扫描必须通过 | Codex |
| v1.1.659 | 2026-06-24 | 补充知识沉淀决策 DB-first 写路径收口验收：知识沉淀采纳/拒绝不得在决策服务层直接写 `current_store.knowledge_deposits`；MemoryStore fallback 由 `save_knowledge_deposit_records` 承接，PostgreSQL 运行态沉淀、可选知识文档、chunks、模型日志和审计必须使用同一数据库事务；`test_knowledge_audit_persistence.py`、`test_knowledge_governance.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.658 | 2026-06-24 | 补充首页看板快照 DB-first fallback 收口验收：`sync_dashboard_metric_snapshot` 不得直接写 `current_store.dashboard_metric_snapshots`；repository 可用时必须调用 `save_dashboard_metric_snapshot_record`，MemoryStore 测试 fallback 仍需保留既有 `created_at` 和稳定快照 ID；`test_dashboard_metrics_service.py`、`test_lifecycle_dashboard_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.657 | 2026-06-24 | 补充迭代规划 DB-first 写路径收口验收：迭代建议生成、建议决策和建议转需求不得在服务层直接写 `current_store.requirements`、`current_store.iteration_plan_suggestions`、`current_store.iteration_plan_decisions` 或通过 `audit_events` 切片收集审计；MemoryStore fallback 由 `persist_iteration_suggestion_record` / `persist_iteration_decision_records` 承接，PostgreSQL 运行态建议、决策、转需求和审计必须使用同一数据库事务；`test_iteration_planning.py`、`test_iteration_planning_persistence.py`、`test_insight_planning_api_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.656 | 2026-06-24 | 补充 Git Review 快照 DB-first 写路径收口验收：GitLab MR / GitHub PR 快照成功、复用和失败审计不得在服务层直接写 `current_store.gitlab_mr_snapshots` 或追加 `current_store.audit_events`；MemoryStore fallback 由 `save_git_review_snapshot_record` 承接，PostgreSQL 运行态快照和审计必须使用同一数据库事务；`test_gitlab_snapshot.py`、`test_github_snapshot.py`、`test_git_review_artifacts_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.655 | 2026-06-24 | 补充代码巡检 DB-first 写路径收口验收：代码巡检报告、finding、通知、误报忽略审批和整改任务派生不得在生产服务层直接写 `current_store.code_inspection_*` 或 `current_store.ai_tasks`；MemoryStore fallback 由 `persist_code_inspection_records` / `persist_ai_task_record` 承接，PostgreSQL 运行态巡检报告、finding、通知和审计必须使用同一数据库事务；`test_code_inspection_governance.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.654 | 2026-06-24 | 补充 Bug 管理 DB-first 写路径收口验收：Bug 创建、批量更新、编辑和删除不得直接调用 `current_store.audit()` 或写 `current_store.bugs`；MemoryStore fallback 由 `save_bug_record` / `delete_bug_record` 写入，PostgreSQL 运行态 Bug 单记录写入、删除和审计必须使用同一数据库事务；`test_bug_management.py`、`test_bug_persistence.py`、`test_bug_lifecycle_service.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.653 | 2026-06-24 | 补充 AI 助手历史与配置 DB-first 收口验收：`assistant_history` 的会话/消息测试 fallback 不得直接写 `current_store.assistant_conversations` 或 `current_store.assistant_messages`；助手动作引用配置和角色快捷任务配置不得调用 `current_store.audit()` 或直接写配置集合，配置、删除和审计必须通过 repository 单记录写入或 MemoryStore fallback 写入；`test_assistant_chat.py`、`test_assistant_chat_persistence.py` 与 `test_assistant_context_service.py` 必须通过 | Codex |
| v1.1.652 | 2026-06-24 | 补充 AI 助手聊天 DB-first 写路径收口验收：`assistant_chat` 服务不得在开始、完成、取消、失败和模型网关调用审计链路中直接写 `current_store.assistant_chat_runs` 或调用 `current_store.audit()`，助手触发定时作业运行归因不得直接写 `current_store.scheduled_job_runs`；聊天运行、会话、消息、模型日志和审计必须通过 `save_assistant_chat_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态必须使用同一数据库事务；`test_assistant_chat.py`、`test_assistant_chat_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.651 | 2026-06-24 | 补充 AI 助手草案 DB-first 写路径收口验收：`assistant_action_drafts` 服务不得在创建、确认、失败、取消、修改、查看和过期链路中直接写 `current_store.assistant_action_drafts`、`current_store.assistant_action_runs` 或调用 `current_store.audit()`；助手触发定时作业运行归因不得直接写 `current_store.scheduled_job_runs`；草案、动作运行和审计必须通过 `save_assistant_action_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态必须使用同一数据库事务；`test_assistant_chat.py`、`test_assistant_draft_workbench.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.650 | 2026-06-24 | 补充 AI 执行器 Runner DB-first 写路径收口验收：Runner 服务不得在状态同步和回写链路中直接写 `current_store` 的 Runner、任务、插件调用、定时作业运行、采集运行或 AI 任务集合，MemoryStore 测试路径由 helper fallback 写入，PostgreSQL 运行态通过 repository 单记录写入；Runner/任务/插件调用/定时作业/采集运行单记录写入和审计必须使用同一数据库事务；`test_plugin_management.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.649 | 2026-06-24 | 补充迭代版本 DB-first 写路径收口验收：迭代版本和版本代码分支配置 create/patch/delete/status advance 不得在路由中直接写 `current_store` 集合，MemoryStore 测试路径由 helper fallback 写入，PostgreSQL 运行态通过 repository 单记录写入；需求单记录写入/删除和审计必须使用同一数据库事务；`test_product_config_persistence.py`、`test_product_system_config.py`、`test_iteration_version_status_flow.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.648 | 2026-06-24 | 补充产品配置路由 DB-first 收口验收：产品、产品模块、产品 Git 仓库和相关系统 create/patch/delete 不得在路由中直接写 `current_store` 集合，必须通过产品配置单记录 helper 进入 MemoryStore 测试 fallback 或 repository；单记录写入/删除和审计必须使用同一数据库事务；`test_product_config_persistence.py`、`test_product_system_config.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.647 | 2026-06-24 | 补充执行诊断快照事务验收：`execution_trace_snapshots` 刷新必须通过单个数据库事务完成 upsert 和过期快照删除，避免读模型半刷新；`test_execution_traces.py` 必须覆盖连接 `autocommit=False` | Codex |
| v1.1.646 | 2026-06-24 | 补充模型网关配置 DB-first 单记录写入验收：PostgreSQL/repository 运行态即使 runtime store 为空，模型网关配置 create/patch/delete 也必须按配置 ID 读取源记录，并通过 repository 单记录 upsert/delete 写回配置和审计；`test_model_gateway_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.645 | 2026-06-24 | 补充 DB-first 兼容层扫描验收：`scripts/audit_memory_store_usage.py` 必须能识别 `current_store.*` 读、写和 helper 残留并输出 P0/P1/P2 分级，`test_memory_store_usage_audit.py` 必须通过 | Codex |
| v1.1.644 | 2026-06-24 | 补充产品配置子资源创建 DB-first 验收：PostgreSQL/repository 运行态即使 runtime store 为空，迭代版本、产品模块、产品 Git 仓库和相关系统 create 也必须按产品 ID 读取产品存在性，同产品版本/模块 code 冲突使用列表读模型，相关系统 code 冲突使用单查，并直接写回记录和审计；`test_product_config_persistence.py` 必须通过 | Codex |
| v1.1.643 | 2026-06-24 | 补充迭代版本编辑/删除 DB-first 验收：PostgreSQL/repository 运行态即使 runtime store 为空，迭代版本 patch/delete 也必须按版本 ID 读取源记录，修改版本编码时只读取同产品版本列表做冲突校验，删除前通过 repository EXISTS 检查需求、任务、Bug 和分支配置引用；`test_product_config_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.642 | 2026-06-24 | 补充产品模块删除 DB-first 验收：PostgreSQL/repository 运行态即使 runtime store 为空，产品模块 delete 也必须按模块 ID 读取源记录，并通过 repository EXISTS 检查需求、任务和 Bug 引用后再直接删除记录与审计；`test_product_config_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.641 | 2026-06-24 | 补充产品模块编辑 DB-first 验收：PostgreSQL/repository 运行态即使 runtime store 为空，产品模块 patch 也必须按模块 ID 从 repository 读取源记录，修改模块编码时只读取同产品模块列表做冲突校验，并把更新和审计直接写回仓储；`test_product_config_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.640 | 2026-06-24 | 补充迭代版本分支配置 DB-first 验收：PostgreSQL/repository 运行态即使 runtime store 为空，版本代码分支配置 patch/delete 也必须按分支配置 ID 从 repository 读取源记录并把更新、删除和审计写回仓储；`test_product_config_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.639 | 2026-06-24 | 补充产品配置子资源 DB-first 验收：PostgreSQL/repository 运行态即使 runtime store 为空，产品 Git 仓库和相关系统 patch/delete 也必须按资源 ID 从 repository 读取源记录并把更新、删除和审计写回仓储；`test_product_config_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.638 | 2026-06-24 | 补充用户反馈更新/转需求 DB-first 验收：PostgreSQL/repository 运行态即使 runtime store 为空，也必须按反馈 ID 从 repository 读取源记录并把更新、转需求和审计写回仓储；`test_insight_planning_api_persistence.py` 与 `test_persistence_repository_boundaries.py` 必须通过 | Codex |
| v1.1.637 | 2026-06-24 | 补充管理列表筛选视图验收：启用 `viewStorageKey` 的 `ManagementListPage` 页面可保存、应用和删除本地筛选/排序视图，需求、任务、迭代版本、Bug、用户洞察、代码巡检、执行诊断、草案任务台、产品资产和系统管理列表均应展示筛选视图入口；`ManagementListPage.test.tsx`、typecheck 和真实管理页面 smoke 必须通过 | Codex |
| v1.1.636 | 2026-06-24 | 补充执行诊断 Runner 节点验收：`ai_executor_task.runner_id` 必须解析为 `ai_executor_runner` 节点，支持按 `source_type=ai_executor_runner` 和 Runner ID 定位链路，响应不得泄露 `token_hash` | Codex |
| v1.1.635 | 2026-06-24 | 补充代码巡检 finding 误报忽略审批验收：报告详情支持申请忽略和批准/驳回，审批通过同步报告 suppression 统计、治理概览分布和审计事件；`test_code_inspection_governance.py`、`CodeInspectionsPage.test.tsx`、typecheck、lint 和真实 `/governance/code-inspections` 页面 smoke 必须通过 | Codex |
| v1.1.634 | 2026-06-24 | 补充代码巡检规则包与误报治理验收：dashboard API 必须返回 `rule_governance` 版本分布和 suppression 分布，代码巡检页展示“规则包与误报治理”；`test_code_inspection_governance.py`、`CodeInspectionsPage.test.tsx`、typecheck、lint 和真实 `/governance/code-inspections` 页面 smoke 必须通过 | Codex |
| v1.1.633 | 2026-06-24 | 补充 AI 助手草案继续编辑深链验收：草案任务台列表和详情弹窗的“继续编辑”必须统一跳转 `/assistant?draft_id=...`，助手页需按 draft_id 加载草案卡；`AssistantDraftsPage.test.tsx`、typecheck、lint 和真实 `/assistant/drafts`、`/assistant` 页面 smoke 必须通过 | Codex |
| v1.1.632 | 2026-06-24 | 补充执行诊断统一入口验收：`ExecutionTraceLink` 需在 AI 助手草案、定时作业运行详情和代码巡检报告详情生成一致深链；代码巡检详情需提供巡检报告、来源运行和插件调用三个诊断入口，`AssistantDraftsPage.test.tsx`、`CodeInspectionsPage.test.tsx`、`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实页面 smoke 必须通过 | Codex |
| v1.1.631 | 2026-06-24 | 补充 AI 助手草案来源链路验收：执行诊断可按 `assistant_message` source_id 定位 `assistant_chat_run` 链路，草案任务台列表和详情展示“来源链路”并跳转 `/governance/execution-traces?source_id=...` | Codex |
| v1.1.630 | 2026-06-24 | 补充插件管理测试诊断弹窗组件化验收：连接测试诊断和 Runner 测试诊断从主页面收口到 `PluginDiagnostics` 后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.629 | 2026-06-24 | 补充用户权限诊断验收：`GET /api/system/permissions/diagnostics` 可解释用户状态、角色、菜单路径、权限点和数据范围阻断原因，角色管理页展示“用户权限诊断”并可运行查询 | Codex |
| v1.1.628 | 2026-06-24 | 补充定时作业 Catalog hook 组件化验收：catalog 选项映射、必填校验、默认结果动作和标签格式化从主页面抽到 `useScheduledJobCatalogOptions` 后，`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.627 | 2026-06-24 | 补充定时作业 catalog 验收：`GET /api/system/scheduled-job-catalog` 返回服务端作业类型/必填规则/代码巡检选项，页面新增/编辑弹窗优先使用 catalog 并在接口不可用时降级静态选项 | Codex |
| v1.1.626 | 2026-06-24 | 补充定时作业表单转换组件化验收：作业类型/扫描选项、模板 payload、助手草案、结果动作、路由参数和配置归一化从主页面抽到 `scheduledJobFormTransformHelpers` 后，`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.625 | 2026-06-24 | 补充插件管理表单转换组件化验收：连接/动作/Runner payload、请求预览、结果映射、schema 回填和助手草案回填从主页面抽到 `pluginFormTransformHelpers` 后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.624 | 2026-06-24 | 补充执行诊断详情排障建议验收：详情需汇总失败/运行中节点，提供来源 ID 深链和“问 AI”入口；成功链路展示无失败节点提示 | Codex |
| v1.1.623 | 2026-06-24 | 补充执行诊断来源 ID 深链验收：`GET /api/governance/execution-traces?source_id=...` 可按任一节点来源 ID 精准返回所属链路，`/governance/execution-traces?source_id=...` 命中唯一链路时自动打开详情 | Codex |
| v1.1.622 | 2026-06-23 | 补充定时作业运行详情弹窗组件化验收：运行结果详情从主页面收口到 `ScheduledJobRunDetailModal` 后，`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.621 | 2026-06-23 | 补充插件管理 Runner 新增/编辑弹窗组件化验收：Runner Modal/Form 外壳和目标系统联动从主页面收口到 `PluginRunnerModal` 后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.620 | 2026-06-23 | 补充插件管理 Runner Token 轮换组件化验收：轮换成功提示和确认弹窗从主页面收口到 `PluginUtilityModals` 后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.619 | 2026-06-23 | 补充插件管理插件定义弹窗组件化验收：插件新增/编辑字段从主页面拆到 `PluginModal` 后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.618 | 2026-06-23 | 补充执行诊断快照刷新节流验收：repository 快照列表短 TTL 内重复查询不得重复全量刷新，详情命中现有快照不刷新，详情未命中新链路时必须强制刷新并返回最新聚合链路 | Codex |
| v1.1.617 | 2026-06-23 | 补充定时作业基础信息组件化验收：新增/编辑作业的名称、作业类型、所属产品和启用字段从主页面拆出后，`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.616 | 2026-06-23 | 补充定时作业代码仓库配置组件化验收：代码巡检作业的仓库/分支、扫描引擎、规则、baseline、已接受风险和质量门禁字段从主页面拆出后，`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.615 | 2026-06-23 | 补充插件管理动作编辑弹窗组件化验收：动作新增/编辑表单、结果写入映射字段、请求预览和高级 JSON 字段从主页面拆出后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.614 | 2026-06-23 | 补充插件管理连接编辑弹窗组件化验收：连接新增/编辑表单、认证 JSON、请求 JSON、schema 字段和保存并测试从主页面拆出后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.613 | 2026-06-23 | 补充插件管理连接/动作表格组件化验收：环境筛选、连接测试入口、动作试运行/运行/删除和写入目标展示从主页面拆出后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/tasks/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.612 | 2026-06-23 | 补充执行诊断 AI 助手运行链路验收：`assistant_chat_run` 可作为 root_type，详情可从模型日志 ID 反查并必须脱敏审计 payload | Codex |
| v1.1.611 | 2026-06-23 | 补充代码巡检整改任务 SLA 验收：治理概览 sla 必须同时返回 Bug 覆盖率和整改任务覆盖率，页面展示“整改任务覆盖率”与未派生任务摘要 | Codex |
| v1.1.610 | 2026-06-23 | 补充代码巡检质量门禁趋势验收：治理概览 trend 必须返回质量门禁通过、失败、跳过和未知计数，代码巡检页面展示“质量门禁趋势” | Codex |
| v1.1.609 | 2026-06-23 | 补充插件管理工具弹窗组件化验收：系统变量全集、Runner 执行日志和动作试运行弹窗从主页面拆出后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/system/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.608 | 2026-06-23 | 补充 RBAC 策略矩阵验收：`GET /api/system/permissions/matrix` 返回角色权限、菜单、范围、高风险权限和菜单权限缺口；角色管理页展示权限审计矩阵并可刷新 | Codex |
| v1.1.607 | 2026-06-23 | 补充定时作业运行健康概览组件化验收：`ScheduledJobRunObservabilityOverview` 抽出后，定时作业页签切换、运行概览、最近失败和慢运行展示需通过 typecheck、单测和真实页面 smoke | Codex |
| v1.1.606 | 2026-06-23 | 补充执行诊断 PostgreSQL 快照读模型验收：启动兼容迁移必须包含 `069_execution_trace_read_model.sql`，服务层测试覆盖 repository 快照刷新、列表分页和关联 ID 详情命中 | Codex |
| v1.1.605 | 2026-06-23 | 补充执行诊断详情组件化验收：链路概要、关联对象、节点表、关系表和元数据预览从主页面拆出后，`ExecutionTracesPage.test.tsx`、typecheck、lint 和真实 `/governance/execution-traces` 页面 smoke 必须通过 | Codex |
| v1.1.604 | 2026-06-23 | 补充插件管理 Runner 配置组件化验收：执行器协议、命令、目标系统、安装模式、工作区和 Token 字段从主页面拆出后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/system/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.603 | 2026-06-23 | 补充插件管理连接表单组件化验收：请求参数行、连接 schema 字段、GitHub/GitLab 地址校验从主页面拆出后，`PluginsPage.test.tsx`、typecheck、lint 和真实 `/system/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.602 | 2026-06-23 | 补充插件管理诊断组件化验收：连接测试请求调试台、市场连接 schema、最近测试摘要和试运行写入预览从主页面拆出后，typecheck、lint 和真实 `/system/plugins` 页面 smoke 必须通过 | Codex |
| v1.1.601 | 2026-06-23 | 补充定时作业运行详情组件化验收：运行链路、Trace DAG、模板来源和复跑对比从主页面拆出后，`ScheduledJobsPage.test.tsx`、typecheck、lint 和真实 `/tasks/scheduled-jobs` 页面 smoke 必须通过 | Codex |
| v1.1.600 | 2026-06-23 | 补充 AI 助手草案任务台验收：当前用户可分页筛选待确认、失败、已采纳和已修改草案，查看详情写入埋点，继续编辑回到 `/assistant?draft_id=...`，列表汇总采纳率、处理率和用户修改率 | Codex |
| v1.1.599 | 2026-06-23 | 补充执行诊断中心验收：管理员可查看跨定时作业运行、插件、AI 执行器、模型网关、代码巡检和审计的统一节点链路，普通角色无权访问，响应不得泄露 token/API key | Codex |
| v1.1.598 | 2026-06-21 | 补充 AI 助手页面 hooks 拆分、页面级 scoped CSS、多视口 smoke 和效果指标产品/角色/趋势/导出验收 | Codex |
| v1.1.597 | 2026-06-21 | 补充 AI 助手历史分页、历史草案脱敏、指标明细 limit 下推和草案深链可见性验收 | Codex |
| v1.1.596 | 2026-06-21 | 补充研发执行器策略任务类型选项验收：新增策略下拉必须覆盖 PRD/原型/产品详细设计、技术方案、代码实现/开发计划、代码评审、自动化测试、代码整改、发布上线评估和上线后分析 | Codex |
| v1.1.595 | 2026-06-21 | 补充研发执行器策略验收：策略只引用插件管理 AI 执行器 Runner，不装配 Agent/Skill；研发任务启动命中策略后进入 Runner 队列，完成后回写任务并进入人工确认 | Codex |
| v1.1.594 | 2026-06-20 | 补充前端展示型 UTC 时间转北京时间验收，覆盖用户洞察、代码巡检、定时作业下次运行/运行详情、Runner 和助手引用时间显示不再少 8 小时或暴露 ISO 原文 | Codex |
| v1.1.593 | 2026-06-20 | 补充 AI 助手聊天运行恢复、可取消模型请求、生成运行指标和多视口真实页面 smoke 验收 | Codex |
| v1.1.592 | 2026-06-19 | 补充 AI 助手动作候选选择后的命令前缀验收：保留 `@动作名` 并承接用户正文 | Codex |
| v1.1.591 | 2026-06-19 | 补充 AI 助手 `@新建` 动作候选验收：动作项按权限返回并回填指令，不进入本次上下文引用 | Codex |
| v1.1.590 | 2026-06-19 | 补充 AI 助手草案表单 PATCH+confirm 闭环、确认幂等、终态修改保护、运营引用产品 scope 和角色快捷任务配置页验收 | Codex |
| v1.1.589 | 2026-06-18 | 补充 AI 助手失败运行修复草案来源配置和 current/proposed 字段差异验收 | Codex |
| v1.1.588 | 2026-06-18 | 补充 AI 助手草案模板市场全模板可生成验收：首批六类模板不得再显示暂未完整接入 | Codex |
| v1.1.587 | 2026-06-18 | 补充 AI 助手定时作业执行权限验收：`system.scheduled_jobs.run` 可执行一次且不授予定时作业配置管理 | Codex |
| v1.1.586 | 2026-06-18 | 补充 AI 助手测试/发布角色发布风险快捷任务验收：点击后必须回填发布风险分析草案提示 | Codex |
| v1.1.585 | 2026-06-18 | 补充 AI 助手管理员 AI能力快捷任务验收：点击后必须回填新增 AI能力配置向导提示 | Codex |
| v1.1.584 | 2026-06-18 | 补充 AI 助手泛化 AI 能力配置向导验收：未指定场景时必须先返回任务类型向导并展示 AI能力配置入口 | Codex |
| v1.1.583 | 2026-06-18 | 补充 AI 助手 @ 定时作业空候选验收：无匹配时必须给出新增定时作业和生成任务草案入口 | Codex |
| v1.1.582 | 2026-06-18 | 补充 AI 助手 run-once 发送前权限提示验收：无定时作业管理权限用户输入执行命令时应先看到不会直接执行 | Codex |
| v1.1.581 | 2026-06-18 | 补充 AI 助手产品角色快捷任务草案优先验收：反馈洞察和版本风险入口必须回填草案生成提示 | Codex |
| v1.1.580 | 2026-06-18 | 补充 AI 助手 @ 执行一次等待 AI 执行器验收：后端需返回 `progress_text`，前端运行卡片需展示等待执行器状态 | Codex |
| v1.1.579 | 2026-06-18 | 补充 AI 助手运行诊断数据连接日志追踪验收：数据连接和结果动作各自的插件调用日志 ID 不得互相覆盖 | Codex |
| v1.1.578 | 2026-06-18 | 补充 AI 助手 @ 候选搜索态键盘提示验收：输入关键词后仍显示上下选择和回车添加提示 | Codex |
| v1.1.577 | 2026-06-18 | 补充 AI 助手失败修复率口径验收：只有成功 `manual_rerun` 可把失败运行计为已修复 | Codex |
| v1.1.576 | 2026-06-18 | 补充 AI 助手 run-once 权限闭环验收：定时作业管理员可获得缺失作业草案，前端无运行记录时展示未执行原因卡 | Codex |
| v1.1.575 | 2026-06-18 | 补充 AI 助手插件草案权限验收：插件连接/动作草案由插件管理权限确认，不再仅限 admin 角色 | Codex |
| v1.1.574 | 2026-06-18 | 补充 AI 助手 AI 能力草案权限验收：Skill / AI角色草案由 AI 能力管理权限确认，不再误要求定时作业管理权限 | Codex |
| v1.1.573 | 2026-06-18 | 补充 AI 助手新增任务向导统一五步闭环验收：每类任务项和研发任务草案均展示“数据来源、AI处理、结果动作、调度策略、确认执行” | Codex |
| v1.1.572 | 2026-06-18 | 补充 AI 助手 @ 候选权限标签验收：通过专项权限引用运维对象时不得误标为管理员可引用 | Codex |
| v1.1.571 | 2026-06-18 | 补充 AI 助手 run-once 草案待确认提示验收：未命中可执行作业时必须明确“尚未执行” | Codex |
| v1.1.570 | 2026-06-18 | 补充 AI 助手草案预检权限验收：缺少确认所需权限时，草案必须在确认前阻塞并展示权限原因 | Codex |
| v1.1.569 | 2026-06-18 | 补充 AI 助手草案预检 Cron 表达式验收：非法调度表达式必须在确认前阻塞并展示校验原因 | Codex |
| v1.1.568 | 2026-06-18 | 补充 AI 助手草案预检连接状态验收：引用最近测试失败的插件连接时，草案必须在确认前阻塞并展示失败原因 | Codex |
| v1.1.567 | 2026-06-18 | 补充 AI 助手全角 `＠` 引用验收：中文输入法输入全角 @ 时仍应弹出候选并执行 `@定时作业 执行一次` 命令 | Codex |
| v1.1.566 | 2026-06-18 | 补充 AI 助手运行记录卡片修复入口验收：只有失败运行才展示“生成修复草案”，成功运行不应导向失败修复 | Codex |
| v1.1.565 | 2026-06-18 | 补充 AI 助手运行记录卡片成功态追问验收：成功运行的“问这次运行”必须回填结果分析，而不是失败诊断 | Codex |
| v1.1.564 | 2026-06-18 | 补充 AI 助手运行详情继续诊断入口验收：失败运行详情必须显式提供继续诊断深链并携带运行记录上下文 | Codex |
| v1.1.563 | 2026-06-18 | 补充 AI 助手定时作业运行对比验收：用户引用 `scheduled_job` 追问上次成功对比时，必须限定到该作业最近失败运行 | Codex |
| v1.1.562 | 2026-06-18 | 补充 AI 助手定时作业修复草案来源验收：用户引用 `scheduled_job` 生成修复草案时，来源运行必须限定到该作业 | Codex |
| v1.1.561 | 2026-06-18 | 补充 AI 助手定时作业引用诊断验收：用户引用 `scheduled_job` 问失败原因时，诊断必须限定到该作业最近失败运行 | Codex |
| v1.1.560 | 2026-06-18 | 补充 AI 助手知识文档候选 chunk 数验收：候选展示必须按实际可注入模型的 chunk 口径计算 | Codex |
| v1.1.559 | 2026-06-18 | 补充 AI 助手不可检索知识文档显式引用验收：`index_failed` 等不可检索文档不得进入助手上下文 | Codex |
| v1.1.558 | 2026-06-18 | 补充 AI 助手 @ 定时作业执行一次无空格命令验收：命令词和作业名粘连时仍应弹出候选并带结构化引用发送 | Codex |
| v1.1.557 | 2026-06-18 | 补充 AI 助手直接生成 AI 能力草案验收：用户无需先创建定时作业，也可在助手中生成 Skill 和 AI角色服务端草案 | Codex |
| v1.1.556 | 2026-06-18 | 补充 AI 助手知识负责人角色化入口验收：`knowledge_owner` 进入助手时可直接使用知识库巡检、知识沉淀和知识权限快捷任务 | Codex |
| v1.1.555 | 2026-06-18 | 补充 AI 助手 @ 定时作业执行权限一致性验收：具备定时作业管理权限的非 admin 用户也能看到并解析定时作业候选 | Codex |
| v1.1.554 | 2026-06-18 | 补充 AI 助手前置草案依赖标题化验收：前端展示和回填提示时不得暴露机器草案 ID | Codex |
| v1.1.553 | 2026-06-18 | 补充 AI 助手邮件摘要和线上日志异常配置前置草案验收：缺连接、缺动作、缺 AI 能力时必须生成可确认依赖链 | Codex |
| v1.1.552 | 2026-06-18 | 补充 AI 助手已应用草案深链结果追踪验收：草案查询必须返回动作运行，前端从 `draft_id` 恢复真实资源和本次运行入口 | Codex |
| v1.1.551 | 2026-06-18 | 补充 AI 助手草案确认失败持久化验收：确认失败必须写入 failed 草案状态、failed 动作运行和失败审计 | Codex |
| v1.1.550 | 2026-06-18 | 补充 AI 助手前置草案 DB-first 确认验收：PostgreSQL/repository 运行态必须从服务端草案和动作运行 read model 解析已确认前置资源 ID | Codex |
| v1.1.549 | 2026-06-18 | 补充 AI 助手效果指标 DB-first 运行追踪验收：PostgreSQL/repository 运行态必须读取定时作业运行 read model 后再按用户草案和引用过滤 | Codex |
| v1.1.548 | 2026-06-18 | 补充 AI 助手 @ 引用输入收敛验收：邮箱地址等非独立 @ 不得打开候选，多定时作业候选的执行一次命令不得自动绑定首个候选 | Codex |
| v1.1.547 | 2026-06-18 | 补充 AI 助手深链引用最近使用验收：从知识空间/知识目录等深链带入的引用，移除后再次输入裸 `@` 必须可在“最近使用”分组找回 | Codex |
| v1.1.546 | 2026-06-18 | 补充 AI 助手知识空间/知识目录深链上下文验收：`reference_type=knowledge_space/knowledge_folder` 必须自动带入本次上下文 | Codex |
| v1.1.545 | 2026-06-18 | 补充 AI 助手分析类草案向导验收：发布风险和知识库巡检 `create_analysis_draft` 必须返回五步 `wizard_steps` | Codex |
| v1.1.544 | 2026-06-18 | 补充 AI 助手周反馈 run-once 边界验收：停用精确同名作业不得拦截官方洞察作业执行 | Codex |
| v1.1.543 | 2026-06-18 | 补充 AI 助手运行诊断三段判断验收：前端需展示“数据连接是否成功 / AI处理是否成功 / 结果动作是否写入成功” | Codex |
| v1.1.542 | 2026-06-18 | 补充 AI 助手草案模板市场流程验收：模板 `wizard_steps` 必须和任务引导、草案卡片统一为五步闭环 | Codex |
| v1.1.541 | 2026-06-17 | 对齐 AI 助手效果指标前端展示：知识命中率统一显示为知识引用命中率 | Codex |
| v1.1.540 | 2026-06-17 | 补充 AI 助手周反馈 run-once 官方作业评分消歧和草案修改率真实写入验收 | Codex |
| v1.1.539 | 2026-06-17 | 补充 AI 助手服务端草案向导验收：草案详情和深链卡片必须保留 `wizard_steps` 配置向导 | Codex |
| v1.1.538 | 2026-06-17 | 补充 AI 助手草案深链验收：`/assistant?draft_id=...` 必须加载服务端草案并展示可确认追踪卡片 | Codex |
| v1.1.537 | 2026-06-17 | 补充 AI 助手 `@` 候选面板验收：候选项展示权限/来源/更新时间/摘要，无匹配时保持面板提示 | Codex |
| v1.1.536 | 2026-06-17 | 补充 AI 助手 `@定时作业 执行一次` 权限验收：无执行权限返回 `permission_denied`，具备 `system.scheduled_jobs.manage` 可触发显式 @ 命令 | Codex |
| v1.1.535 | 2026-06-17 | 补充 AI 助手执行一次运行进度刷新验收：状态仍为 running 但执行节点摘要更新时也必须刷新卡片 | Codex |
| v1.1.534 | 2026-06-17 | 补充 AI 助手知识空间和知识目录显式引用验收，范围内 chunk 必须按权限限量注入 | Codex |
| v1.1.533 | 2026-06-17 | 补充 AI 助手 `@` 类型词搜索验收：定时作业与运行记录必须分别优先命中对应引用类型 | Codex |
| v1.1.532 | 2026-06-17 | 补充 AI 助手 `@` 候选标签验收：研发任务和 Skill 必须用清晰用户侧标签展示 | Codex |
| v1.1.531 | 2026-06-17 | 补充 AI 助手裸 `@` 默认候选验收：管理员默认候选必须覆盖插件连接且不挤掉 AI角色和 Skill | Codex |
| v1.1.530 | 2026-06-17 | 补充 AI 助手 run-once 输入路径验收：候选未完成时点击发送或按 Enter 必须按 `type=scheduled_job` 补查引用 | Codex |
| v1.1.529 | 2026-06-17 | 补充 AI 助手插件连接失败诊断验收：不调用模型网关即可解释最近失败连接测试和修复建议 | Codex |
| v1.1.528 | 2026-06-17 | 补充 AI 助手执行一次运行进度验收：running/queued 卡片必须展示当前执行节点，避免用户误判为没有执行 | Codex |
| v1.1.527 | 2026-06-17 | 补充 AI 助手草案类型处理率验收：效果指标中每类草案必须展示处理率以解释待确认卡点 | Codex |
| v1.1.526 | 2026-06-17 | 补充 AI 助手配置向导逐步骤 AI 生成验收：ready/pending/blocked 步骤均可回填步骤草案提示 | Codex |
| v1.1.525 | 2026-06-17 | 补充 AI 助手运行详情深链引用状态验收：从运行详情进入助手后必须可见引用解析中、已带入或失败状态 | Codex |
| v1.1.524 | 2026-06-17 | 补充 AI 助手配置向导手动调整入口验收：每个向导步骤可跳转到对应配置页人工补齐依赖 | Codex |
| v1.1.523 | 2026-06-17 | 补充 AI 助手草案确认失败前端验收：确认接口失败后草案卡必须显示失败状态并保留重新生成 | Codex |
| v1.1.522 | 2026-06-17 | 补充 AI 助手运行记录卡片快捷追问验收：运行卡片可直接携带当前运行引用进入诊断、修复草案和上次成功对比 | Codex |
| v1.1.521 | 2026-06-17 | 补充 AI 助手执行一次运行状态刷新验收：running 运行轮询到终态后必须显式展示最新状态提示 | Codex |
| v1.1.520 | 2026-06-17 | 补充 AI 助手“本次上下文”常驻空态验收：未选择引用时也必须展示上下文注入状态 | Codex |
| v1.1.519 | 2026-06-17 | 补充 AI 助手角色化入口后端访问验收：测试负责人、测试人员和发布负责人必须能调用助手会话与聊天 API | Codex |
| v1.1.518 | 2026-06-17 | 补充 AI 助手周反馈执行一次多候选消歧验收：多个 active 周反馈相关作业同时命中时必须执行官方周反馈洞察作业 | Codex |
| v1.1.517 | 2026-06-17 | 补充 AI 助手角色化快捷任务验收：测试负责人、测试人员和发布负责人必须看到测试快捷任务 | Codex |
| v1.1.516 | 2026-06-17 | 补充 AI 助手运行诊断日志追踪验收：诊断卡片需展示模型日志和插件调用日志 ID | Codex |
| v1.1.515 | 2026-06-17 | 补充 AI 助手引用摘要和 run-once 草案确认提示验收：本次上下文可查看摘要，执行一次草案必须展示“确认并执行一次” | Codex |
| v1.1.514 | 2026-06-17 | 补充 AI 助手配置向导前置草案入口验收：阻塞或需前置配置步骤必须可一键回填生成前置草案提示 | Codex |
| v1.1.513 | 2026-06-17 | 补充 AI 助手效果指标追踪验收：前端必须展示作业运行、失败修复、用户消息引用和知识命中的分子分母计数 | Codex |
| v1.1.512 | 2026-06-17 | 补充 AI 助手效果指标拆分验收：前端必须展示草案状态分布和 drafts_by_action 动作类型分布 | Codex |
| v1.1.511 | 2026-06-17 | 补充 AI 助手运行诊断/对比卡片后续追问验收：卡片按钮必须携带运行引用回填修复草案、对比或诊断追问 | Codex |
| v1.1.510 | 2026-06-17 | 补充 AI 助手 @ 执行一次运行中去重和可追踪启动验收：TTL 内已有 running 运行时必须返回追踪，新运行需可读回后再返回 | Codex |
| v1.1.509 | 2026-06-17 | 补充 AI 助手服务端草案 ID 兼容验收：仅返回 `server_draft_id` 的草案仍必须显示卡片并提供追踪链接 | Codex |
| v1.1.508 | 2026-06-17 | 补充 AI 助手 @ 执行一次快速发送验收和定时作业运行详情 `result_write_record_id` 自动展开验收 | Codex |
| v1.1.507 | 2026-06-17 | 补充 AI 助手运行诊断追踪验收：结果写入记录 ID 必须可跳转到对应运行详情 | Codex |
| v1.1.506 | 2026-06-17 | 补充 AI 助手知识上下文注入上限验收：大文档引用不得显示为全部 chunk 注入模型 | Codex |
| v1.1.505 | 2026-06-17 | 补充 AI 助手终态草案前端验收：已取消、已过期或失败草案不得再应用到配置表单 | Codex |
| v1.1.504 | 2026-06-17 | 补充 AI 助手裸 `@` 默认候选均衡验收：知识文档不能挤掉需求、AI任务、定时作业、运行记录、插件动作、AI角色和 Skill | Codex |
| v1.1.503 | 2026-06-17 | 补充 AI 助手定时作业草案向导验收：周反馈、邮件摘要和线上日志异常草案均必须返回 `wizard_steps` | Codex |
| v1.1.502 | 2026-06-17 | 补充 AI 助手草案配置向导与 run-once 消歧验收：代码巡检作业草案必须展示 `wizard_steps`，相似历史任务存在时优先执行唯一启用 active 作业 | Codex |
| v1.1.501 | 2026-06-17 | 补充 AI 助手代码巡检 AI 能力前置草案验收：缺 AI Skill/AI角色时必须生成、确认并解析 `create_ai_skill`/`create_ai_agent` 草案 | Codex |
| v1.1.500 | 2026-06-17 | 补充 AI 助手知识片段级 @ 引用验收：候选/解析支持 `knowledge_chunk`，聊天只注入被选中的片段 | Codex |
| v1.1.499 | 2026-06-17 | 补充 AI 助手运行记录追踪与草案详情验收：执行一次后前端自动刷新运行终态，草案可在当前页查看 payload、差异和校验问题 | Codex |
| v1.1.498 | 2026-06-17 | 补充 AI 助手新增任务向导验收：工具项和建议按钮均覆盖五类任务类型 | Codex |
| v1.1.497 | 2026-06-17 | 补充 AI 助手 run-once 草案前端验收：确认后草案卡片必须展示本次运行深链 | Codex |
| v1.1.496 | 2026-06-17 | 补充 AI 助手 run-once 草案确认验收：确认后必须创建作业并触发一次手动运行，审计记录运行 ID | Codex |
| v1.1.495 | 2026-06-17 | 补充 AI 助手执行一次兜底验收：周反馈洞察作业未配置时必须生成可确认定时作业草案 | Codex |
| v1.1.494 | 2026-06-17 | 补充 AI 助手运行短追问验收：已引用运行记录后，“为什么这次失败？”和“和上次成功有什么不同？”必须触发对应工具 | Codex |
| v1.1.493 | 2026-06-17 | 补充 AI 助手效果指标前端验收：工作台侧栏可按需加载并展示草案、引用、运行和失败修复指标 | Codex |
| v1.1.492 | 2026-06-17 | 补充 AI 助手失败运行修复草案验收：引用失败运行后可生成可确认的结果动作修复草案 | Codex |
| v1.1.491 | 2026-06-17 | 补充 AI 助手 @ 定时作业执行回归：完整 @ 名称精确命中应覆盖相近作业和错误自动候选引用 | Codex |
| v1.1.490 | 2026-06-17 | 补充 AI 助手运行追问对比验收：引用一次运行后可询问“和上次成功有什么不同”并展示运行对比卡片 | Codex |
| v1.1.489 | 2026-06-17 | 补充 AI 助手运行失败诊断验收：结果动作段必须返回结果写入记录 ID、写入目标和写入状态 | Codex |
| v1.1.488 | 2026-06-17 | 补充 AI 助手过期草案验收：`expires_at` 到期后草案自动进入 `expired`，确认返回 `DRAFT_EXPIRED` 且不写业务资源 | Codex |
| v1.1.487 | 2026-06-17 | 补充 AI 助手线上日志异常分析草案验收：聊天生成 AI 定时作业服务端草案并绑定日志动作、连接和 AI 装配 | Codex |
| v1.1.486 | 2026-06-17 | 补充 AI 助手执行一次长任务验收：AI 类定时作业应先返回运行中记录并后台完成 | Codex |
| v1.1.485 | 2026-06-17 | 补充 AI 助手分析类草案验收：发布风险分析和知识库巡检可生成 `create_analysis_draft` 并确认追踪 | Codex |
| v1.1.484 | 2026-06-17 | 补充 AI 助手邮件摘要模板草案验收：聊天生成邮件收取定时作业服务端草案并绑定可用邮箱动作和连接 | Codex |
| v1.1.483 | 2026-06-17 | 补充 AI 助手草案模板市场验收：服务端目录返回六类模板，前端侧栏可加载并回填提示 | Codex |
| v1.1.482 | 2026-06-16 | 补充 AI 执行器列表测试验收：系统默认执行器和本地 Runner 均可从列表发起健康诊断 | Codex |
| v1.1.481 | 2026-06-16 | 补充插件连接“保存并测试”验收：新增/编辑连接保存成功后立即执行连接测试并展示诊断 | Codex |
| v1.1.480 | 2026-06-16 | 补充 Runner 安装包 START_STOP.md 验收，要求覆盖各系统启动、停止、状态查看、重启和页面停用边界 | Codex |
| v1.1.479 | 2026-06-16 | 补充 AI 执行器 Runner 安装包目标系统验收：Linux、macOS、Windows、Docker 和通用手动安装分别生成专属 ZIP 资产 | Codex |
| v1.1.478 | 2026-06-16 | 补充 AI 执行器 Runner 安装包验收：Codex/Claude Code/Hermes/OpenClaw 命令配置、Skill 和远程连接 env/config 下载 | Codex |
| v1.1.477 | 2026-06-16 | 补充代码巡检私有仓库凭据拉取和 AI 后处理保留 native 扫描快照验收 | Codex |
| v1.1.476 | 2026-06-16 | 补充代码巡检外部扫描引擎实际执行和异步取消竞态验收 | Codex |
| v1.1.475 | 2026-06-16 | 补充代码巡检增强验收：固定工作区快照、异步执行、baseline/质量门禁、多仓库、详情聚合和上次扫描对比 | Codex |
| v1.1.474 | 2026-06-15 | 补充本地完整代码静态扫描验收：代码巡检作业可不依赖插件连接，直接 clone 仓库、扫描内置规则并回填提交人 | Codex |
| v1.1.473 | 2026-06-15 | 补充代码巡检扫描分支验收：代码巡检作业编辑页展示代码仓库和扫描分支，未手工填写时默认使用产品 Git 仓库默认分支，报告写入分支不可为空 | Codex |
| v1.1.472 | 2026-06-15 | 补充代码巡检运行回归验收：扫描器或 AI 返回 GitLab project_path 时应映射到作业配置的产品 Git 仓库 ID；插件调用日志和运行摘要不得保存明文 Authorization/Token Header | Codex |
| v1.1.471 | 2026-06-15 | 补充 AI 助手显式引用扩展和定时作业运行失败诊断验收：管理员可引用作业/运行/动作/AI角色/Skill，普通用户被权限过滤 | Codex |
| v1.1.470 | 2026-06-14 | 补充 AI 助手 P0 落地验收：`@` 知识文档候选/解析、知识 chunk 注入不入日志、服务端动作草案确认/取消和前端草案卡片操作 | Codex |
| v1.1.469 | 2026-06-14 | 调整 MaxCompute 插件验收：MaxCompute 不再属于官方标准插件和官方动作模板，历史官方插件降级为普通 HTTP 插件，连接编辑不展示项目与表配置 | Codex |
| v1.1.468 | 2026-06-14 | 补充 GitLab 本地地址验收：新增/编辑 GitLab 连接只填写“GitLab 地址”，支持本地自建 GitLab 项目 URL，保存时自动同步 Endpoint 并解析 project_id/project_path，Project ID / Group ID / API 版本不再手工填写 | Codex |
| v1.1.467 | 2026-06-14 | 补充 GitHub 连接仓库地址验收：新增/编辑 GitHub 连接只填写“仓库地址”，支持 HTTPS、SSH 和 `owner/repo` 简写，保存时自动解析 `owner/repo` 且高级 Params 不展示拆分字段 | Codex |
| v1.1.466 | 2026-06-14 | 补充 GitHub 官方连接认证验收：官方模板不得预填假 Token，新增/编辑 GitHub 连接必须填写 Token 或密钥引用，空值前端拦截且后端返回 `VALIDATION_ERROR` | Codex |
| v1.1.465 | 2026-06-14 | 补充官方插件连接 schema 表单验收：GitHub/GitLab 仓库项目字段必须以业务字段展示并写回 request_config，schema 字段不重复出现在高级 Params，动作路径模板可从连接参数解析 | Codex |
| v1.1.464 | 2026-06-14 | 补充任务编排平台 5 项优化验收：多连接运行合并、Skill Schema/动作映射契约校验、定时作业全链路试运行、写入策略展示和官方插件模板版本/复制能力 | Codex |
| v1.1.463 | 2026-06-14 | 补充系统菜单管理验收：菜单资源由数据库维护，系统管理页可新增/编辑/启停/删除非系统菜单，静态路由边界和权限点保护需回归 | Codex |
| v1.1.462 | 2026-06-14 | 补充定时作业多连接/多动作配置验收：数据连接和动作均支持多选，提交 payload 保留 `plugin_connection_ids` / `plugin_action_ids` 数组并兼容旧单字段 | Codex |
| v1.1.461 | 2026-06-14 | 补充定时作业配置页直观化验收：新增/编辑表单按基础信息、数据连接、AI执行、动作和调度分区，列表合并展示数据连接 / AI执行 / 动作 / 调度，运行详情展示运行链路 | Codex |
| v1.1.460 | 2026-06-14 | 补充定时作业表单调度配置验收：调度方式、Cron 表达式和间隔秒数连续展示，`source_system` 作为模板/审计内部来源标识隐藏提交 | Codex |
| v1.1.459 | 2026-06-14 | 补充 AI角色命名验收：AI 能力配置页签、定时作业表单、AI 助手草案和运行详情展示使用“AI角色”，技术 payload 仍提交 `agent_id` | Codex |
| v1.1.458 | 2026-06-14 | 补充定时作业系统默认执行器验收：AI 执行器仓库任务模板保存 `config_json.ai_executor`，运行详情展示系统默认执行器模型日志和结果摘要 | Codex |
| v1.1.457 | 2026-06-14 | 补充系统默认执行器验收：执行器列表展示只读系统默认执行器，官方 AI 执行器连接/动作模板默认使用 `model_gateway`，动作调用直接走系统默认模型 | Codex |
| v1.1.456 | 2026-06-14 | 补充插件管理命名验收：动作页签、按钮、模板入口和删除占用提示必须统一展示为“动作”，AI 执行器保持独立页签 | Codex |
| v1.1.455 | 2026-06-14 | 补充导航和插件日志归属验收：研发任务位于需求交付，任务中心只保留 AI 能力配置、定时作业、插件管理；插件管理不展示调用日志页签 | Codex |
| v1.1.454 | 2026-06-13 | 补充 Runner Token/日志/取消/超时、成功运行生成模板和运行 Trace DAG 验收 | Codex |
| v1.1.453 | 2026-06-13 | 补充任务编排平台升级验收：模板向导、官方连接 schema、Runner 健康状态/启动命令和代码巡检整改任务闭环 | Codex |
| v1.1.452 | 2026-06-13 | 补充 AI 执行器 Runner/OpenClaw 验收：Runner 注册、心跳、认领、完成回写和运行详情节点必须闭环 | Codex |
| v1.1.451 | 2026-06-13 | 调整结果写入记录验收归属：定时作业运行详情按 `scheduled_job_run_id` 展示最终写入反馈，插件管理不再展示运行结果记录 | Codex |
| v1.1.450 | 2026-06-13 | 补充通用结果写入记录验收：插件管理可按写入目标查看邮件通知和未来目标运行反馈 | Codex |
| v1.1.449 | 2026-06-13 | 补充邮箱收发连接参数和 AI 执行器官方插件验收：市场模板需返回 SMTP/IMAP/POP3 参数、邮件收取动作和 Codex/Claude/Hermes/OpenClaw Runner 配置 | Codex |
| v1.1.448 | 2026-06-13 | 补充官方连接模板唯一来源验收：插件市场返回连接默认 payload 和版本，页面与 AI 助手复用该模板 | Codex |
| v1.1.447 | 2026-06-13 | 补充 AI 助手动作草案写入目标验收：草案卡片中文写入目标必须从结果写入目标 registry 渲染 | Codex |
| v1.1.446 | 2026-06-13 | 补充定时作业运行可观测性验收：运行记录页签展示成功率、失败原因、耗时、AI/Token/插件调用和动作写入成功率 | Codex |
| v1.1.445 | 2026-06-13 | 补充运行详情节点追踪和请求回放历史展开验收：节点摘要展示请求/响应/耗时/业务记录，历史测试可查看完整请求响应 | Codex |
| v1.1.444 | 2026-06-13 | 补充动作模板唯一来源验收：前端和助手不得在模板缺失时硬编码生成官方动作 | Codex |
| v1.1.443 | 2026-06-13 | 补充代码巡检治理概览验收：规则统计、仓库/分支/提交人排行和严重问题 SLA 必须从真实报告聚合 | Codex |
| v1.1.442 | 2026-06-13 | 补充结果写入目标注册表验收：服务端返回目标默认映射和字段，动作表单按 registry 渲染 | Codex |
| v1.1.441 | 2026-06-13 | 补充插件连接请求回放台验收：最近测试记录、复制动作模板、失败修复建议和变量解析前后差异 | Codex |
| v1.1.440 | 2026-06-13 | 补充定时作业编排视图验收：新增/编辑弹窗展示四段式状态预览，并可在数据连接节点测试连接 | Codex |
| v1.1.439 | 2026-06-13 | 补充动作模板唯一来源验收：模板接口返回版本，AI 助手动作草案必须携带模板 code/version 并复用模板 payload | Codex |
| v1.1.438 | 2026-06-13 | 补充动作动态模板验收：新增动作表单从服务端模板目录回填请求配置和结果映射 | Codex |
| v1.1.437 | 2026-06-13 | 补充插件连接最近测试摘要验收：连接测试后列表显示状态、耗时和错误码 | Codex |
| v1.1.436 | 2026-06-13 | 补充定时作业复跑对比验收：复跑详情展示来源运行状态、导入数和错误码摘要 | Codex |
| v1.1.435 | 2026-06-12 | 补充定时作业邮件通知运行反馈验收：结果动作节点展示邮件通知记录、投递 ID、状态和收件人 | Codex |
| v1.1.434 | 2026-06-12 | 补充助手邮箱动作草案验收：草案使用邮件通知记录写入目标并展示中文标签 | Codex |
| v1.1.433 | 2026-06-12 | 补充邮箱通知写入目标验收：邮箱动作模板默认使用邮件通知记录并展示投递字段映射 | Codex |
| v1.1.432 | 2026-06-12 | 补充代码巡检来源跳转验收：来源运行链接进入定时作业页后自动打开运行详情 | Codex |
| v1.1.431 | 2026-06-12 | 补充代码巡检来源链路验收：报告列表和详情必须展示来源作业、运行、连接、动作和插件调用 | Codex |
| v1.1.430 | 2026-06-12 | 补充 AI 助手草案组串联保存验收：连接/动作保存后后续草案自动解析真实资源 ID | Codex |
| v1.1.429 | 2026-06-12 | 补充 AI 助手代码巡检配置草案组验收：缺少连接/动作时必须同时生成前置草案和作业草案 | Codex |
| v1.1.428 | 2026-06-12 | 补充 AI 助手插件连接草案验收：GitHub/GitLab/邮箱连接草案必须可展示并回填插件管理新增连接表单 | Codex |
| v1.1.427 | 2026-06-12 | 补充定时作业 collector run 类型约束验收：dashboard/lifecycle/plugin/pending 等作业运行不得因 `collector_type` 约束失败 | Codex |
| v1.1.426 | 2026-06-12 | 补充定时作业模板来源可视化验收：复制弹窗和运行详情必须显示来源 | Codex |
| v1.1.425 | 2026-06-12 | 补充定时作业模板化复制验收：作业和运行快照可复制为新增草稿并保留 `template_source` | Codex |
| v1.1.424 | 2026-06-12 | 补充连接测试请求调试台原始请求配置和无动态变量空状态验收 | Codex |
| v1.1.423 | 2026-06-12 | 补充插件连接测试动态变量解析验收：请求调试台必须展示变量位置、表达式、偏移和最终值 | Codex |
| v1.1.422 | 2026-06-12 | 补充定时作业复跑来源验收：复跑请求、运行详情和审计 payload 必须包含 `source_run_id` | Codex |
| v1.1.421 | 2026-06-12 | 补充 AI 助手动作草案验收：GitHub/GitLab/邮箱动作草案必须可展示并回填插件管理新增动作表单 | Codex |
| v1.1.420 | 2026-06-12 | 补充动作试运行审计验收：试运行成功/失败必须写 `plugin_action.trial_*` 轻量审计事件 | Codex |
| v1.1.419 | 2026-06-12 | 补充插件市场动作模板入口验收：从 GitHub/GitLab/邮箱市场项点击创建动作应直接套用官方场景模板 | Codex |
| v1.1.418 | 2026-06-12 | 补充 AI 助手 AI 代码巡检草案验收：明确要求大模型分析时草案应带出执行模式、模型、Agent 和 Skill 并在卡片展示 | Codex |
| v1.1.417 | 2026-06-12 | 补充定时作业终态审计上下文验收：插件+AI+知识链路必须记录模型、Agent、Skill、连接环境、动作和写入目标轻量字段 | Codex |
| v1.1.416 | 2026-06-12 | 补充按执行模式触发 AI 装配校验：代码巡检切换为 AI 生成时前端必须拦截缺少模型、Agent 和 Skill 的保存 | Codex |
| v1.1.415 | 2026-06-12 | 补充定时作业连接环境筛选验收：作业表单可按环境过滤数据连接，提交 payload 不包含筛选字段 | Codex |
| v1.1.414 | 2026-06-12 | 补充代码巡检 AI 执行模式验收：`ai_assisted/ai_generated` 巡检必须调用模型归一化扫描结果，运行详情展示三段式节点 | Codex |
| v1.1.413 | 2026-06-12 | 补充插件连接环境筛选验收：连接列表和 API 按 `default/dev/test/staging/prod/sandbox` 过滤，非法环境被拒绝 | Codex |
| v1.1.412 | 2026-06-12 | 补充官方插件市场验收：GitLab/GitHub/邮箱标准插件需展示推荐场景、动作模板、安装状态和连接/动作数量，并可引导新增连接 | Codex |
| v1.1.411 | 2026-06-12 | 补充定时作业运行审计验收：终态审计 payload 必须包含触发方式、运行状态、导入数量和 collector/plugin 上下文 | Codex |
| v1.1.410 | 2026-06-12 | 补充定时作业复跑触发方式验收：普通手动运行为 `manual`，运行记录复跑为 `manual_rerun`，非法触发类型被拒绝 | Codex |
| v1.1.409 | 2026-06-12 | 补充插件连接测试 cURL 复现验收：请求调试台必须展示可复制 cURL | Codex |
| v1.1.408 | 2026-06-12 | 补充 AI 助手草案保存审计验收：作业配置和 `scheduled_job.created/updated` 审计 payload 必须保留草案来源 | Codex |
| v1.1.407 | 2026-06-12 | 补充 AI 助手草案应用验收：定时作业草案可回填新增作业表单并保留动态变量映射 | Codex |
| v1.1.406 | 2026-06-12 | 补充 AI 助手草案前端展示验收：`assistant.action_draft` 必须显示为待确认配置草案卡片 | Codex |
| v1.1.405 | 2026-06-12 | 补充 AI 助手定时作业草案验收：聊天工具结果返回周反馈洞察和代码巡检作业草案且确认前不写入作业定义 | Codex |
| v1.1.404 | 2026-06-12 | 补充定时作业场景模板验收：周反馈洞察和代码巡检模板自动生成连接、AI 装配、调度和结果动作配置 | Codex |
| v1.1.403 | 2026-06-12 | 补充邮箱官方动作模板验收：邮箱通知发送模板自动生成插件、连接、请求配置和运行结果映射 | Codex |
| v1.1.402 | 2026-06-12 | 补充动作试运行写入预览验收：页面展示写入目标、预计写入、候选数量和样例数据 | Codex |
| v1.1.401 | 2026-06-12 | 补充代码巡检运行时映射验收：动作 `result_mapping` 必须参与巡检报告字段和 finding 提取 | Codex |
| v1.1.400 | 2026-06-12 | 补充官方动作模板验收：GitHub/GitLab 代码巡检模板自动生成请求配置和代码巡检报告映射 | Codex |
| v1.1.399 | 2026-06-12 | 补充定时作业运行记录复跑验收：运行记录操作列可重新触发原作业并打开新运行详情 | Codex |
| v1.1.398 | 2026-06-11 | 补充 AI 作业强校验和调试展示验收：线上日志 AI 分析不得缺少 Agent/Skill/模型网关，运行详情展示三段式执行链路，请求调试台展示完整请求信息 | Codex |
| v1.1.397 | 2026-06-11 | 补充动作代码巡检写入目标验收：新增动作可选择代码巡检报告并填写巡检报告 JSONPath 映射 | Codex |
| v1.1.396 | 2026-06-11 | 补充代码巡检提交人维度验收：报告/finding 展示提交人，支持提交人筛选、severity mapping、Bug 去重和产品范围读取控制 | Codex |
| v1.1.395 | 2026-06-11 | 补充代码仓库定期巡检验收：定时作业扫描质量/安全/规范问题，结果写入代码巡检报告表，严重问题自动建 Bug，通知动作记录反馈 | Codex |
| v1.1.394 | 2026-06-11 | 补充 AI 助手工作台升级验收：`@` 引用、知识库注入、助理动作草案、AI/插件/定时任务配置确认和权限绕过防护 | Codex |
| v1.1.393 | 2026-06-11 | 补充定时作业配置与执行链路验收：配置顺序为数据连接、AI 模型、Agent、Skills、结果动作，用户反馈洞察抽取必须先模型处理再写入 | Codex |
| v1.1.392 | 2026-06-11 | 补充定时作业运行结果三节点验收：运行详情必须展示数据连接获取内容、Skill 处理内容和结果动作反馈内容，并展示 Skill 节点模型调用状态 | Codex |
| v1.1.391 | 2026-06-11 | 补充定时作业运行结果详情验收：运行记录必须可查看结果摘要、插件调用、Skill/Prompt 快照、作业配置快照和错误信息 | Codex |
| v1.1.390 | 2026-06-11 | 补充插件删除验收：插件、连接、动作列表必须提供删除入口，被连接/动作/定时作业/调用日志使用时必须提示并阻断删除 | Codex |
| v1.1.389 | 2026-06-11 | 补充定时作业维护验收：作业列表必须提供编辑和删除入口，编辑回填配置并通过 PATCH 保存，删除通过 DELETE 生效并记录审计 | Codex |
| v1.1.386 | 2026-06-11 | 补充插件新增后维护验收：插件、连接和动作必须可编辑回填，连接/动作 Params 与 Headers 编辑后通过 PATCH 保存，脱敏占位不得覆盖真实密钥 | Codex |
| v1.1.387 | 2026-06-11 | 补充动作写入目标验收：MaxCompute 场景默认写入用户洞察表，定时作业未配置输出覆盖时复用动作 `result_mapping`，运行摘要展示 Skill 处理信息和写入目标 | Codex |
| v1.1.388 | 2026-06-11 | 补充动作写入目标联动验收：切换结果写入目标时，下方 JSONPath 映射字段必须按目标动态变化并同步高级 JSON | Codex |
| v1.1.385 | 2026-06-11 | 补充知识导入可靠性验收：worker 租约 claim、目录子树归档、资产幂等 upsert 和 chunk set 索引状态回滚 | Codex |
| v1.1.383 | 2026-06-11 | 补充 OCR JSON 图片来源验收：chunk metadata 和预览应展示页内图片数量、表格数量和图片引用 | Codex |
| v1.1.382 | 2026-06-11 | 补充 regex_section 正则分块验收：按结构分隔符生成 chunk，并在预览和 metadata 中保留分段标题与切分规则 | Codex |
| v1.1.381 | 2026-06-11 | 补充知识中心前端运营验收：导入任务弹窗应展示 worker 状态，chunk 预览应展示 OCR/Table 来源元数据 | Codex |
| v1.1.380 | 2026-06-11 | 补充知识 chunk set 版本化约束验收：同一文档多次导入或重解析允许不同 chunk set 复用 chunk_index，不得被旧唯一约束阻断 | Codex |
| v1.1.379 | 2026-06-11 | 补充知识导入 worker 补偿扫描创建人验收：后台消费遗漏 queued 任务时 chunk set 创建人应沿用导入任务创建人 | Codex |
| v1.1.378 | 2026-06-11 | 补充知识导入解析产物拆分验收：OCR/Table JSON 应沉淀结构化 sidecar 资产，chunk metadata 应保留页码、表格列和来源资产引用 | Codex |
| v1.1.377 | 2026-06-11 | 补充知识导入后台 worker 验收：上传、重解析和 retry 自动入队，worker 状态可观测，run 仅作为补偿入口 | Codex |
| v1.1.376 | 2026-06-11 | 补充知识导入任务 run/retry/cancel、chunk set 回滚、父子分块检索和目录批量整理验收 | Codex |
| v1.1.375 | 2026-06-10 | 补充知识管理升级验收：知识空间、目录、MinIO/S3 资产、导入任务、chunk set 和空间权限过滤需整体可用 | Codex |
| v1.1.374 | 2026-06-10 | 补充 MaxCompute 每周用户反馈洞察验收：动作引导配置可生成 MCP 查询 JSON，定时作业运行后将插件返回洞察写入用户反馈洞察表 | Codex |
| v1.1.386 | 2026-06-11 | 补充插件连接测试诊断验收：认证配置覆盖同名认证 Header，`***` 占位被拦截，页面展示最终 URL、query、Header 来源和远端响应摘要 | Codex |
| v1.1.385 | 2026-06-11 | 补充插件连接级 Params/Headers 验收：连接表格配置生成 `request_config.query/headers`，连接测试、动作预览和实际调用合并连接默认值与动作覆盖项 | Codex |
| v1.1.384 | 2026-06-11 | 补充插件配置体验优化验收：连接测试诊断、系统变量预览、动作请求预览/试运行、参数表格与 JSON 双向同步、定时作业插件输入映射表格化 | Codex |
| v1.1.387 | 2026-06-11 | 补充 GitLab/GitHub 官方标准插件验收：官方插件不可修改删除，连接表单自动带出平台 endpoint、认证和 Params/Headers | Codex |
| v1.1.388 | 2026-06-11 | 补充邮箱官方标准插件验收：邮箱插件不可修改删除，连接表单自动带出邮件网关/API 参数 | Codex |
| v1.1.373 | 2026-06-10 | 补充插件管理验收：插件、连接、动作和调用日志需脱敏、审计，定时作业可引用动作并保存插件快照和调用日志 | Codex |
| v1.1.372 | 2026-06-10 | 补充定时系统作业和 AI 能力装配验收：Agent/Skill 配置、定时作业计划、手动触发、运行快照、collector run 关联、失败重试和 AI 生成结果确认边界 | Codex |
| v1.1.371 | 2026-06-09 | 迭代版本代码分支配置验收补齐：版本页可按多代码库维护基准分支、开发分支、状态和来源，并通过结构表持久化 | Codex |
| v1.1.370 | 2026-06-07 | 日志监控验收更新：研发运营看板更名为日志监控，页面移除采集运行记录和待归属数据队列，只验证 GitLab、Jenkins 和线上日志指标入口 | Codex |
| v1.1.369 | 2026-06-07 | 用户洞察转需求验收补齐：用户反馈可直接转正式需求，需求来源、产品归属、反馈 linked 状态和审计需一致；需求列表支持来源筛选 | Codex |
| v1.1.368 | 2026-06-07 | Code Review 闭环验收增强：报告接口和任务中心弹窗新增只读 Review 结论回写模板，支持人工复制到 GitLab MR / GitHub PR 评论区，同时保持系统不自动远端回写 | Codex |
| v1.1.367 | 2026-06-07 | AI 助手工具化查询验收增强：后端新增 read-model 工具结果 `tool_results`，覆盖需求/任务进展、待确认 Review、代码评审、迭代、Bug 和模型网关，聊天响应与历史消息持久化工具结果和引用链接 | Codex |
| v1.1.366 | 2026-06-07 | 前端页面测试拆分继续推进：将首页 IT 团队看板、运营明细入口和产品/时间筛选回归迁移到独立 DashboardPage.test.tsx，App.test.tsx 继续收敛为少量跨管理模块 smoke | Codex |
| v1.1.365 | 2026-06-07 | 后端持久化测试拆分继续推进：将 PersistentMemoryStore 仓储边界和 repository read path 余量回归迁移到 test_persistence_repository_boundaries.py 与 test_repository_read_paths.py，test_database_persistence.py 收敛为共享 FakeRepository/fixture | Codex |
| v1.1.364 | 2026-06-07 | 后端持久化测试拆分继续推进：将 GitLab MR 快照 API DB-first 写入和 GitHub PR 列表/预览审计回归迁移到 test_git_review_artifacts_persistence.py，和 Git review artifact 用例按领域维护 | Codex |
| v1.1.363 | 2026-06-07 | 后端持久化测试拆分继续推进：将 AI 助手聊天 DB-first 写入和用户级历史 stale runtime 读取回归迁移到 test_assistant_chat_persistence.py，和 assistant chat 用例按领域维护 | Codex |
| v1.1.362 | 2026-06-07 | 后端持久化测试拆分继续推进：将知识文档创建/修改/检索/重试索引、知识沉淀采纳/拒绝和审计回归迁移到 test_knowledge_audit_persistence.py，和知识审计用例按领域维护 | Codex |
| v1.1.361 | 2026-06-07 | 后端持久化测试拆分继续推进：将 Mock Issue 写回 API DB-first 写入、幂等结果恢复和审计回归迁移到 test_mock_writeback_persistence.py，和 mock writeback 用例按领域维护 | Codex |
| v1.1.360 | 2026-06-07 | 后端持久化测试拆分继续推进：将任务启动失败/重试、Review 审批/编辑审批/驳回/补充信息、任务取消和补充信息提交回归迁移到 test_workflow_runtime_persistence.py，和 workflow runtime 用例按领域维护 | Codex |
| v1.1.359 | 2026-06-07 | 后端持久化测试拆分继续推进：将需求 API DB-first 写入、任务生成、Postgres runtime source rows、任务启动 Review/Graph 写入和后续任务创建回归迁移到 test_requirement_task_persistence.py，和需求任务用例按领域维护 | Codex |
| v1.1.358 | 2026-06-07 | 后端持久化测试拆分继续推进：将产品配置 API DB-first 写入、stale runtime 读取和 Postgres runtime source rows 回归迁移到 test_product_config_persistence.py，和产品配置用例按领域维护 | Codex |
| v1.1.357 | 2026-06-07 | 后端持久化测试拆分继续推进：将用户洞察指标、用户反馈、迭代建议生成/决策转需求和 stale runtime 列表读取回归迁移到 test_insight_planning_api_persistence.py，和 insight planning API 用例按领域维护 | Codex |
| v1.1.356 | 2026-06-07 | 后端持久化测试拆分继续推进：将研发运营采集运行、待归属、GitLab/Jenkins/线上日志列表读取与 DB-first 写入回归迁移到 test_operational_collection_persistence.py，和 operational collection 用例按领域维护 | Codex |
| v1.1.355 | 2026-06-07 | 后端持久化测试拆分继续推进：将知识文档 API 结构化写入与审计 payload 回归迁移到 test_knowledge_audit_persistence.py，和知识审计持久化用例按领域维护 | Codex |
| v1.1.354 | 2026-06-07 | 后端持久化测试拆分继续推进：将待确认 Review repository direct query 回归迁移到 test_workflow_runtime_persistence.py，和 workflow runtime 持久化用例按领域维护 | Codex |
| v1.1.353 | 2026-06-07 | 后端持久化测试拆分继续推进：将需求 API、AI 任务生成 API 和任务启动/Review 更新的结构化写入回归迁移到 test_requirement_task_persistence.py，和需求任务持久化用例按领域维护 | Codex |
| v1.1.352 | 2026-06-07 | 后端持久化测试拆分继续推进：将产品配置 API 结构化写入回归迁移到 test_product_config_persistence.py，和产品配置结构化持久化用例按领域维护 | Codex |
| v1.1.351 | 2026-06-07 | 后端持久化测试拆分继续推进：将知识文档、知识分块、知识沉淀和审计事件结构化持久化与恢复计数器回归迁移到独立 test_knowledge_audit_persistence.py | Codex |
| v1.1.350 | 2026-06-07 | 后端持久化测试拆分继续推进：将 Graph Run、Graph Checkpoint 和 Human Review workflow runtime 结构化持久化、空结构表忽略历史快照和孤儿运行态清理回归迁移到独立 test_workflow_runtime_persistence.py | Codex |
| v1.1.349 | 2026-06-07 | 后端持久化测试拆分继续推进：将需求与 AI 任务结构化持久化、空结构表忽略历史快照和孤儿任务清理回归迁移到独立 test_requirement_task_persistence.py | Codex |
| v1.1.348 | 2026-06-07 | 后端持久化测试拆分继续推进：将产品配置结构化持久化、空结构表忽略历史快照和孤儿需求清理回归迁移到独立 test_product_config_persistence.py | Codex |
| v1.1.347 | 2026-06-07 | 后端持久化测试拆分继续推进：将生命周期上下文与团队看板快照持久化、DB-first handler 写入和 repository source rows/cache 回归迁移到独立 test_lifecycle_dashboard_persistence.py | Codex |
| v1.1.346 | 2026-06-07 | 后端持久化测试拆分继续推进：将 Bug 结构化持久化、Bug API DB-first 写入和 stale runtime 列表读取回归迁移到独立 test_bug_persistence.py | Codex |
| v1.1.345 | 2026-06-06 | 后端持久化测试拆分继续推进：将 Mock Issue 写回结构化持久化、恢复计数器和陈旧任务引用清理回归迁移到独立 test_mock_writeback_persistence.py | Codex |
| v1.1.344 | 2026-06-06 | 后端持久化测试拆分继续推进：将 GitLab/GitHub Review 快照与代码评审报告结构化持久化、恢复计数器和陈旧引用清理回归迁移到独立 test_git_review_artifacts_persistence.py | Codex |
| v1.1.343 | 2026-06-06 | 后端持久化测试拆分继续推进：将模型网关配置/日志结构化持久化、恢复计数器和配置 API 写入回归迁移到独立 test_model_gateway_persistence.py | Codex |
| v1.1.342 | 2026-06-06 | 后端持久化测试拆分继续推进：将用户仓储登录和用户管理 API 回归迁移到独立 test_user_repository_auth.py | Codex |
| v1.1.341 | 2026-06-06 | 后端持久化测试拆分继续推进：将迭代建议和迭代决策的结构化持久化用例迁移到独立 test_iteration_planning_persistence.py | Codex |
| v1.1.340 | 2026-06-06 | 后端持久化测试拆分继续推进：将用户反馈和用户使用指标的结构化持久化用例迁移到独立 test_user_insights_persistence.py | Codex |
| v1.1.339 | 2026-06-06 | 后端持久化测试拆分继续推进：将 GitLab 日指标、Jenkins 发布记录、线上日志指标和采集运行的结构化持久化用例迁移到独立 test_devops_metrics_persistence.py | Codex |
| v1.1.338 | 2026-06-06 | 后端持久化测试拆分继续推进：将待归属数据 pending attribution 的结构化持久化和陈旧上下文清理用例迁移到独立 test_pending_attribution_persistence.py | Codex |
| v1.1.337 | 2026-06-06 | 前端页面测试拆分继续推进：将需求管理批量排期/生成任务/全链路弹窗回归迁移到独立 RequirementsPage.test.tsx，将迭代版本归集需求/版本需求查看/状态推进影响预览迁移到独立 IterationVersionsPage.test.tsx | Codex |
| v1.1.336 | 2026-06-06 | 前端页面测试拆分继续推进：将任务中心列表、筛选、批量重试/取消、Review 决策、任务操作弹窗、Mock Issue 写回和补充信息回归迁移到独立 TaskCenterPage.test.tsx | Codex |
| v1.1.335 | 2026-06-06 | 前端页面测试拆分继续推进：将产品配置页筛选、错误态、版本/模块/Git 资源/相关系统维护和 GitHub provider 编辑保存回归迁移到独立 ProductsPage.test.tsx | Codex |
| v1.1.334 | 2026-06-06 | 前端测试拆分继续推进：将 Umi 路由注册、登录、鉴权初始化、auth state 事件、过期 token 清理和登出跳转回归迁移到独立 AuthFlow.test.tsx | Codex |
| v1.1.333 | 2026-06-06 | 前端测试拆分继续推进：将管理 CRUD、任务创建、GitLab MR 预览/快照、Code Review 报告和批量排期 service 契约迁移到独立 ManagementCrudServices.test.ts | Codex |
| v1.1.332 | 2026-06-06 | 前端测试拆分继续推进：将 MVP-C mock issue 写回、知识沉淀列表/审批/驳回和知识检索 service 契约迁移到独立 KnowledgeWritebackServices.test.ts | Codex |
| v1.1.331 | 2026-06-06 | 前端测试拆分继续推进：将 Review 补充信息、编辑确认、驳回和任务补充信息提交 service 契约迁移到独立 ReviewServices.test.ts | Codex |
| v1.1.330 | 2026-06-06 | 前端测试拆分继续推进：将模型网关配置 CRUD、Chat-only 连接测试和密钥脱敏 service 契约迁移到独立 ModelGatewayServices.test.ts | Codex |
| v1.1.329 | 2026-06-06 | 前端测试拆分继续推进：将团队看板 product/time-range 查询、active 产品筛选和 GitHub PR preview/snapshot service 契约迁移到独立 DashboardServices.test.ts 与 GitReviewServices.test.ts | Codex |
| v1.1.328 | 2026-06-06 | 前端测试拆分继续推进：将产品版本/模块/Git 仓库/相关系统 service 契约与 Git 凭据脱敏回归迁移到独立 ProductServices.test.ts | Codex |
| v1.1.327 | 2026-06-06 | 前端页面测试拆分继续推进：将模型网关配置新增/编辑、仅 Chat 测试、密钥不回显和编辑不覆盖密钥页面回归迁移到独立 ModelGatewayPage.test.tsx | Codex |
| v1.1.326 | 2026-06-06 | 前端页面测试拆分继续推进：将知识中心沉淀审核、权限检索来源展示和索引失败重试页面回归迁移到独立 KnowledgePage.test.tsx | Codex |
| v1.1.325 | 2026-06-06 | 前端页面测试拆分继续推进：将需求全链路独立详情页直达路由、返回入口、版本内对比和共享展示组件回归迁移到独立 RequirementFullChainPage.test.tsx | Codex |
| v1.1.324 | 2026-06-06 | 后端测试拆分继续推进：将 AI 助手会话/消息结构化持久化与恢复计数器用例迁移到独立 test_assistant_chat_persistence.py | Codex |
| v1.1.323 | 2026-06-06 | 前端页面测试拆分继续推进：将 AI 助手页面、引用链接、用户级会话历史和助手 service 映射用例迁移到独立 AssistantPage.test.tsx | Codex |
| v1.1.322 | 2026-06-06 | 前端页面测试拆分继续推进：将任务中心 Code Review 报告全链路跳转用例迁移到独立 TaskCenterPage.test.tsx，保留 App.test.tsx 作为少量端到端工作台 smoke | Codex |
| v1.1.321 | 2026-06-06 | 补充 Code Review 报告到需求全链路闭环验收：任务中心报告弹窗展示“查看需求全链路”入口，并验证跳转到对应需求 full-chain 详情页 | Codex |
| v1.1.320 | 2026-06-06 | 补充 GitHub PR / GitLab MR 代码 Review 闭环验收：预览返回权限诊断，快照响应返回上一快照引用、diff 对比摘要和复用标记，任务中心展示快照结果用于 PR 刷新/重试排查 | Codex |
| v1.1.319 | 2026-06-06 | PostgreSQL 旧库兼容验收补齐：PostgresSnapshotRepository 启动时执行安全 additive schema patch，补齐历史本地 volume 缺失的 requirements.assignee 字段和索引，避免需求列表与首页看板 SQL read model 在旧库上返回 500；真实页面 smoke 复验 8 个核心路由通过 | Codex |
| v1.1.318 | 2026-06-06 | 测试用例文档按业务域拆分：主 test-case.md 保留版本信息、通用规范、MVP 验收切片和业务域索引，详细用例迁移到 test-cases/core-workflow.md、requirements-and-tasks.md、devops-quality-and-insights.md 与 supporting-matrices.md，降低单文件维护成本 | Codex |
| v1.1.317 | 2026-06-06 | 模型网关 router 拆分继续收口：将模型网关配置列表的筛选、排序、分页、query/performance 观测和模型调用日志 repository-first 读取迁移到 model_gateway_listing，model_gateway router 收窄为配置测试、创建、修改、删除和响应封装编排 | Codex |
| v1.1.316 | 2026-06-06 | 相关系统 router 拆分继续收口：将相关系统列表的 repository-first 读取、产品归属筛选、active_only 过滤和本地兼容排序迁移到 related_system_listing，related_systems router 收窄为相关系统创建、修改、删除和审计保存编排 | Codex |
| v1.1.315 | 2026-06-06 | 产品 Git 仓库 router 拆分继续收口：将单产品 Git 仓库列表的 repository-first 读取、凭据脱敏投影、active_only 过滤、缺失产品校验和本地兼容排序迁移到 product_git_repository_listing，product_git_repositories router 收窄为 GitLab/GitHub 绑定校验和仓库创建、修改、删除编排 | Codex |
| v1.1.314 | 2026-06-06 | 产品模块 router 拆分继续收口：将单产品模块列表的 repository-first 读取、active_only 过滤、缺失产品校验和本地兼容排序迁移到 product_module_listing，product_modules router 收窄为模块创建、修改、删除和依赖保护编排 | Codex |
| v1.1.313 | 2026-06-06 | 产品主体 router 拆分继续收口：将产品列表 SQL read model 探测、当前版本/模块数投影、本地兼容筛选排序分页和 query/performance 观测迁移到 product_listing，products router 收窄为端点装配、产品详情和产品 CRUD 编排 | Codex |
| v1.1.312 | 2026-06-06 | 迭代版本 router 拆分继续收口：将全量迭代版本列表 SQL read model 探测、所属产品投影、本地兼容筛选排序分页和 query/performance 观测迁移到 product_version_listing，product_versions router 收窄为端点装配、单产品版本列表和版本写入/状态推进编排 | Codex |
| v1.1.311 | 2026-06-06 | Bug 管理服务拆分继续收口：将 Bug 列表 SQL read model 探测、摘要投影、本地兼容筛选排序分页和 query/performance 观测迁移到 bug_listing，bugs service 收窄为 Bug 创建、批量更新、修改、删除和审计保存编排 | Codex |
| v1.1.310 | 2026-06-06 | AI 助手聊天服务拆分继续收口：将 repository-backed request context、任务工作流 source rows 恢复、用户级会话/消息 source store 和助手聊天保存委托迁移到 assistant_request_context，assistant_chat 收窄为聊天校验、模型调用、消息写入和审计编排 | Codex |
| v1.1.309 | 2026-06-06 | 模型网关 router 拆分继续收口：将配置连接测试的目标校验、既有配置凭据复用、Chat/Embedding 测试编排和测试审计保存迁移到 model_gateway_config_tests，model_gateway router 收窄为请求模型、鉴权、运行态 store 装配和响应封装 | Codex |
| v1.1.308 | 2026-06-06 | 模型网关服务拆分继续收口：将 Chat/Embedding URL 规范化、连接测试结果构造、Embedding 响应解析和 Embedding context 构造迁移到 model_gateway_runtime，model_gateway 收窄为 OpenAI-compatible 调用、配置选择和测试编排并保留兼容导出 | Codex |
| v1.1.307 | 2026-06-06 | 知识沉淀服务拆分继续收口：将知识内容切分、chunk 构造、文本索引/向量索引状态转换和 Embedding 失败降级逻辑迁移到 knowledge_indexing，knowledge_deposits 收窄为知识文档/沉淀读写编排并保留兼容导出 | Codex |
| v1.1.306 | 2026-06-06 | Git review 服务拆分继续收口：将 GitLab base URL/凭据解析、项目 key 校验、MR 读取、changes 解析和 GitLab API 错误归一化迁移到 git_review_gitlab，git_review 保留 gitlab_request_json/urlopen/gitlab_preview 兼容 wrapper 与审计/快照编排 | Codex |
| v1.1.305 | 2026-06-06 | Git review 服务拆分继续收口：将 GitHub base URL/凭据解析、仓库路径解析、PR 列表读取、PR 预览和 GitHub API 错误归一化迁移到 git_review_github，git_review 保留兼容 wrapper 与审计/快照编排，为后续 PR 刷新、重试和权限诊断增强打基础 | Codex |
| v1.1.304 | 2026-06-06 | 需求交付服务拆分继续收口：将需求列表 SQL read model 入口、需求摘要投影、本地兼容筛选排序分页和查询性能观测响应迁移到 requirement_listing，requirements 收窄为需求写入、编辑、删除和任务生成编排，并保留兼容导出 | Codex |
| v1.1.303 | 2026-06-06 | AI 助手上下文服务拆分继续收口：将引用候选、引用类型偏好、实体跳转路由和引用归一化迁移到 assistant_references，assistant_context 收窄为系统上下文、消息构造和公开投影，并保留兼容导出 | Codex |
| v1.1.302 | 2026-06-06 | persistence_contracts.py 大文件拆分继续收口：将集合字段常量、历史 snapshot collection 清单和 ID counter 来源表迁移到 persistence_fields，persistence_contracts 收窄为 repository Protocol 契约并保留兼容导出 | Codex |
| v1.1.301 | 2026-06-06 | persistence_payloads.py 大文件拆分继续收口：将结构化恢复与保存前的上下文清理、运行态链接同步和默认字段补齐 helper 迁移到 persistence_payload_cleanup，persistence_payloads 收窄为 repository load/save 包装与兼容导出门面 | Codex |
| v1.1.300 | 2026-06-06 | persistence_payloads.py 大文件拆分继续收口：将结构化恢复时的 ID counter 同步 helper 迁移到 persistence_payload_counters，persistence_payloads 继续保留兼容导出并聚焦 repository load/save 包装与上下文清理 | Codex |
| v1.1.299 | 2026-06-06 | persistence_payloads.py 大文件拆分继续收口：将纯 payload 选择/合并 helper 迁移到 persistence_payload_selectors，将结构化 payload 是否存在的检查 helper 迁移到 persistence_payload_checks，保留 persistence_payloads 兼容导出给历史测试兼容层使用 | Codex |
| v1.1.298 | 2026-06-06 | persistence.py 大文件拆分继续收口：将 PostgreSQL snapshot repository 的领域仓储装配、callback bind 和兼容 alias 安装迁移到 persistence_repositories，PostgresSnapshotRepository 聚焦连接池、公开委托接口和连接重试 | Codex |
| v1.1.297 | 2026-06-06 | 用户洞察仓储拆分继续推进：将用户洞察统一列表 SQL CTE、筛选、排序、分页和响应投影迁移到 user_insights_lists repository，UserInsightReadRepository 进一步收窄为单表读取与写入/列表委托入口 | Codex |
| v1.1.296 | 2026-06-06 | 任务仓储拆分继续推进：将 AI 任务、Graph Run、Graph Checkpoint 和 Human Review 的基础保存与 upsert SQL 迁移到 task_writes repository，TaskReadRepository 收窄为任务读取、任务列表 read model 与跨域事务编排入口 | Codex |
| v1.1.295 | 2026-06-06 | 知识仓储拆分继续推进：将知识文档、知识分块和知识沉淀的保存、删除、引用清理、向量 literal 格式化与 upsert SQL 迁移到 knowledge_writes repository，KnowledgeReadRepository 收窄为知识读取、搜索和兼容委托入口 | Codex |
| v1.1.294 | 2026-06-06 | 用户洞察仓储拆分继续推进：将用户反馈、用户使用指标、迭代建议和迭代决策的批量保存、单记录保存、转需求事务与 upsert SQL 迁移到 user_insights_writes repository，UserInsightReadRepository 收窄为洞察读取、统一列表 read model 与兼容委托入口 | Codex |
| v1.1.293 | 2026-06-06 | 研发运营仓储拆分继续推进：将 GitLab 每日代码指标、Jenkins 发布记录和线上日志指标的批量保存、单记录保存与 upsert SQL 迁移到 devops_writes repository，DevopsReadRepository 收窄为运营指标读取、列表 read model 与兼容委托入口 | Codex |
| v1.1.292 | 2026-06-06 | 产品配置仓储拆分继续推进：将产品、迭代版本、模块、Git 仓库和相关系统的批量保存、单记录保存、删除与 upsert SQL 迁移到 product_config_writes repository，ProductConfigReadRepository 进一步收窄为读取门面与兼容委托入口 | Codex |
| v1.1.291 | 2026-06-06 | 产品配置仓储拆分继续推进：将产品和迭代版本管理列表 SQL read model 的 count/list 查询迁移到 product_config_lists repository，ProductConfigReadRepository 收窄为产品配置恢复、详情读取和写入编排 | Codex |
| v1.1.290 | 2026-06-06 | 生命周期上下文服务拆分继续推进：将 lifecycle subject 到任务集合解析、主体产品归属推导、审计/Mock Issue/知识沉淀等主体定位迁移到 lifecycle_subjects service，lifecycle_context.py 收窄为上下游关系构造和响应编排 | Codex |
| v1.1.289 | 2026-06-06 | 模型网关服务拆分继续推进：将任务消息构造、产品上下文脱敏、模型输出 JSON 解析和 Code Review 风险归一化迁移到 model_gateway_task_io service，model_gateway.py 收窄为运行时配置、OpenAI-compatible 调用、Embedding 和连接测试编排 | Codex |
| v1.1.288 | 2026-06-06 | Git review 服务拆分继续推进：将 PR/MR diff 快照上下文校验、大小限制、复用、失败审计和快照保存迁移到 git_review_snapshots service，git_review.py 收窄为 GitLab/GitHub provider 读取和接口响应编排 | Codex |
| v1.1.287 | 2026-06-06 | 生命周期上下文服务拆分继续推进：将 LifecycleContextReadModel、repository 探测、source rows 转换和生命周期 edge/risk 保存 helper 迁移到 lifecycle_source service，lifecycle_context.py 收窄为主体定位、上下游关系构造和响应编排 | Codex |
| v1.1.286 | 2026-06-06 | 模型网关服务拆分继续推进：将 repository 运行时上下文、配置 source store、配置保存 payload、公开脱敏投影、默认配置选择迁移到 model_gateway_config_context service，model_gateway.py 收窄为 Chat/Embedding 调用、连接测试和任务输出解析 | Codex |
| v1.1.285 | 2026-06-06 | AI 助手聊天服务拆分继续推进：将用户级会话列表、会话消息读取、会话归属校验和消息追加迁移到 assistant_history service，并将 AssistantServiceError 抽到 assistant_errors，assistant_chat.py 收窄为聊天编排、上下文准备、模型网关调用和审计保存 | Codex |
| v1.1.284 | 2026-06-06 | 需求交付服务拆分继续推进：将单需求审批、驳回和关闭决策迁移到 requirement_decisions service，requirements.py 收窄为需求创建/编辑/删除、任务生成、列表查询和共享持久化 helper，保持状态校验、活跃任务保护和 DB-first 审计契约不变 | Codex |
| v1.1.283 | 2026-06-06 | 知识沉淀服务拆分继续推进：将知识沉淀采纳/驳回决策迁移到 knowledge_deposit_decisions service，knowledge_deposits.py 收窄为知识文档索引、repository 上下文和共享持久化 helper，保持知识沉淀状态校验、索引、模型日志和 DB-first 审计契约不变 | Codex |
| v1.1.282 | 2026-06-06 | AI 助手聊天服务拆分继续推进：assistant_chat 复用 model_gateway_logging 的 token 估算、OpenAI usage 归一化和模型调用日志写入，消除助手本地重复日志实现，为后续助手工具化查询保持统一模型审计口径 | Codex |
| v1.1.281 | 2026-06-06 | 模型网关服务拆分继续推进：将 token 估算、OpenAI Chat/Embedding usage 归一化和模型调用日志写入迁移到 model_gateway_logging service，model_gateway.py 继续收窄为运行时配置、Chat/Embedding 调用和连接测试编排 | Codex |
| v1.1.280 | 2026-06-06 | Git review 服务拆分继续推进：将 GitLab/GitHub 变更文件摘要、diff 文件树、风险摘要、Review Checklist 和 diff payload 构造迁移到 git_review_diff service，git_review.py 收窄为 provider 读取、快照上下文校验、审计和快照编排 | Codex |
| v1.1.279 | 2026-06-06 | 生命周期上下文服务拆分继续推进：将任务范围/证据匹配/缺失上下文判断迁移到 lifecycle_evidence service，将风险信号生成、稳定记录 ID 和 lifecycle edge/risk 物化迁移到 lifecycle_risks service，lifecycle_context.py 收窄为 source store、主体定位、上下游关系和响应编排 | Codex |
| v1.1.278 | 2026-06-06 | 研发运营服务拆分继续推进：将线上日志指标列表、登记、时间窗口/指标范围校验和产品模块上下文校验迁移到独立 operational_online_logs service，operational_records.py 收窄为采集运行与共享运营 helper | Codex |
| v1.1.277 | 2026-06-06 | 研发运营服务拆分继续推进：将 Jenkins 发布记录列表、登记、时间/状态校验和产品版本上下文校验迁移到独立 operational_jenkins_releases service，operational_records.py 继续收窄为采集运行和线上日志指标 | Codex |
| v1.1.276 | 2026-06-06 | 研发运营服务拆分继续推进：将 GitLab 每日代码指标列表、登记、日期校验、数值范围校验和产品 Git 仓库上下文校验迁移到独立 operational_gitlab_metrics service，operational_records.py 继续收窄为采集运行、Jenkins 发布和线上日志指标 | Codex |
| v1.1.275 | 2026-06-06 | 用户洞察服务拆分继续推进：将用户使用指标列表、登记、时间窗口解析、数值范围校验和产品/模块上下文校验迁移到独立 user_usage_metrics service，user_insights.py 收窄为用户洞察统一列表和共享仓储 helper | Codex |
| v1.1.274 | 2026-06-06 | 用户洞察服务拆分继续推进：将迭代建议列表、生成、决策、证据收集、状态机校验和转需求逻辑迁移到独立 iteration_planning service，user_insights.py 收窄为用户洞察统一列表和使用指标 | Codex |
| v1.1.273 | 2026-06-06 | 用户洞察服务拆分继续推进：将用户反馈列表、登记、处理、枚举校验、满意度校验和产品/模块/需求上下文校验迁移到独立 user_feedback service，user_insights.py 收窄为用户洞察聚合、使用指标和迭代建议 | Codex |
| v1.1.272 | 2026-06-06 | 研发运营服务拆分继续推进：将待归属数据队列的校验、列表、创建和处理迁移到独立 operational_attribution service，operational_records.py 收窄为采集运行和 DevOps 指标记录，attribution router 契约保持不变 | Codex |
| v1.1.271 | 2026-06-06 | 需求交付服务拆分继续推进：将批量生成任务、批量分配负责人、批量排期和批量推进状态迁移到独立 requirement_batch_operations service，requirements.py 收窄为单需求写入、任务生成 helper、列表查询和共享投影 | Codex |
| v1.1.270 | 2026-06-06 | 模型网关服务拆分继续推进：将 Embedding 连接模式、维度校验、配置归一化和测试字段构建迁移到独立 model_gateway_embeddings service，model_gateway.py 保留兼容导出和 Chat/Embedding 调用行为不变 | Codex |
| v1.1.269 | 2026-06-06 | 发布验证流程继续固化：真实浏览器页面 smoke 监听网络响应，核心页面路由期间出现非 favicon 的 4xx/5xx 请求会直接判定失败，避免页面壳渲染但 API 404/500 未被发现 | Codex |
| v1.1.268 | 2026-06-06 | 管理列表查询性能观测继续补齐：产品、迭代版本、知识文档、审计事件等核心管理列表补充显式 P95 目标，并扩展测试验证真实接口响应包含 query/performance、分页参数、行数和目标耗时 | Codex |
| v1.1.267 | 2026-06-06 | 需求交付服务拆分继续推进：将需求详情和需求全链路只读投影、时间线事件、PR/MR 快照引用、代码评审/Bug/发布/知识沉淀链路摘要迁移到独立 requirement_full_chain service，requirements.py 继续收窄为需求写入、批量操作和列表查询 | Codex |
| v1.1.266 | 2026-06-06 | persistence.py 大文件拆分继续收口：将仍需测试兼容的 repository 回调入口迁移到独立 RepositoryCallbackHub，PostgresSnapshotRepository 只负责仓储装配和兼容别名挂载，保持 `_upsert_*`、`_clean_*`、`_delete_missing*` 等边界测试入口不变 | Codex |
| v1.1.265 | 2026-06-06 | 后端任务服务拆分继续推进：将 Review 通过和编辑通过决策编排迁移到独立 task_review_decisions service，tasks router 直接引用该决策边界，ai_tasks.py 收敛为兼容 re-export 薄模块，保持 Review 完成、代码评审报告确认、Bug 建议生成和 DB-first 保存契约不变 | Codex |
| v1.1.264 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务创建、技术方案后续任务校验、发布准备/上线后分析上下文注入、GitHub/GitLab 代码评审快照校验、需求任务关联和任务创建审计保存迁移到独立 task_creation service，保持任务创建和 DB-first 保存契约不变 | Codex |
| v1.1.263 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务详情投影、Graph Run 列表、待确认 Review 列表和 Review 详情读取迁移到独立 task_read_details service，保持任务详情、Review 只读查询和 pending Review SQL read model 契约不变 | Codex |
| v1.1.262 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务启动执行、模型网关失败处理、Code Review executor 调用、Human Review 创建、Graph Run 启动和任务启动保存迁移到独立 task_start_execution service，保持任务启动、失败重试、批量重试和代码评审任务契约不变 | Codex |
| v1.1.261 | 2026-06-06 | 后端任务服务拆分继续推进：将任务取消、补充信息提交、Review 驳回和要求补充信息迁移到独立 task_state_transitions service，并将任务保存/审计 helper 下沉到 task_persistence_helpers，保持任务状态流转、批量操作和 DB-first 保存契约不变 | Codex |
| v1.1.260 | 2026-06-06 | 后端任务服务拆分继续推进：将 Review 完成后的代码评审报告确认、自动化测试/上线后 Bug 建议生成、知识沉淀、需求完成态推进和 Review 决策校验迁移到独立 task_review_artifacts service，保持 Review 决策和持久化契约不变 | Codex |
| v1.1.259 | 2026-06-06 | 后端任务服务拆分继续推进：将产品/Git 上下文脱敏、任务归属校验、技术方案/发布准备前置校验和发布上下文聚合迁移到独立 task_contexts service，保持任务创建和上下文快照契约不变 | Codex |
| v1.1.258 | 2026-06-06 | 后端任务服务拆分继续推进：将 Graph Run、Graph Checkpoint 创建、最新运行态查询和任务图状态推进迁移到独立 task_graph_runtime service，保持任务启动、Review 决策和批量取消运行态契约不变 | Codex |
| v1.1.257 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务列表 SQL read model 入口、时间过滤解析、任务摘要投影和列表性能观测响应迁移到独立 task_listing service，保持任务管理列表分页/筛选/排序契约不变 | Codex |
| v1.1.256 | 2026-06-06 | 后端任务服务拆分继续推进：将 Code Review executor payload、执行器选择、输出归一化和报告创建迁移到独立 task_code_review_execution service，保持代码评审任务启动、失败和报告契约不变 | Codex |
| v1.1.255 | 2026-06-06 | 后端任务服务拆分继续推进：将 AI 任务批量取消、批量重试和异常归一化逻辑迁移到独立 task_batch_operations service，保持任务批量接口契约和回归测试不变 | Codex |
| v1.1.254 | 2026-06-06 | 前端页面测试拆分继续推进：将用户洞察登记/处理/迭代建议和研发运营指标/采集/待归属回归迁移到独立 OperationalInsightsPages.test.tsx，继续降低 App.test.tsx 单文件维护压力 | Codex |
| v1.1.253 | 2026-06-06 | 前端页面测试拆分继续推进：将 Bug 管理证据/重复归并编辑、批量处理和登记 Bug 目标版本选择回归迁移到独立 BugManagementPage.test.tsx，继续降低 App.test.tsx 单文件维护压力 | Codex |
| v1.1.252 | 2026-06-06 | 前端页面测试拆分继续推进：抽取共享 proComponentsMock，并将用户管理角色选项、角色管理目录与详情回归迁移到独立 SystemManagementPages.test.tsx，减少 App.test.tsx 页面职责聚集 | Codex |
| v1.1.251 | 2026-06-06 | 拆分前端管理列表组件测试：将 ManagementListPage 固定布局、默认列宽、横向滚动和右固定操作列回归迁移到独立 ManagementListPage.test.tsx，启动 App.test.tsx 页面巨型测试拆分 | Codex |
| v1.1.250 | 2026-06-06 | 拆分 repository-first 读路径回归测试：将知识文档、知识沉淀、知识检索、审计事件、模型网关配置和模型日志的 stale runtime 回归迁移到独立 test_repository_read_paths.py，继续降低 test_database_persistence.py 单文件维护压力 | Codex |
| v1.1.249 | 2026-06-06 | 拆分管理类列表 SQL read model 回归测试：将 DevOps、用户洞察、需求、Bug、产品和迭代版本分页/筛选/排序防回退用例迁移到独立 test_management_list_read_models.py，降低 test_database_persistence.py 单文件维护压力 | Codex |
| v1.1.248 | 2026-06-06 | 补充任务流程跨表写事务仓储边界验收，验证任务生成、任务启动、Review 决策和任务状态更新由 TaskReadRepository 承接，PostgresSnapshotRepository 不再直接编排这些 SQL upsert | Codex |
| v1.1.247 | 2026-06-06 | 调整需求和任务写入仓储边界验收，去除 PostgresSnapshotRepository 私有 upsert 兼容入口依赖，保留公开保存方法和 DB-first 写入回归验证 | Codex |
| v1.1.246 | 2026-06-06 | 调整产品配置写入仓储边界验收，去除 PostgresSnapshotRepository 私有 upsert 兼容入口依赖，保留公开 save_product_config/save_product_config_record/delete_product_config_record 委托验证 | Codex |
| v1.1.245 | 2026-06-06 | 补充表维护 helper 仓储边界验收，验证 delete_missing/delete_missing_ids 由 TableMaintenanceRepository 承接，persistence.py 不再保留通用删除 SQL 实现 | Codex |
| v1.1.244 | 2026-06-06 | 补充系统状态仓储边界验收，验证数据库发号器、历史 snapshot load/save 均委托 SystemStateRepository，DB-first id counters 和历史 app_state_snapshots 兼容测试保持通过 | Codex |
| v1.1.243 | 2026-06-06 | 补充产品配置读取 SQL 下沉仓储边界验收，验证产品详情、版本、模块、Git 仓库和相关系统读取均由 ProductConfigReadRepository 承接，PostgresSnapshotRepository 不回退直接 SQL | Codex |
| v1.1.242 | 2026-06-06 | 补充管理列表统一表格根样式和可见页面回归验收，验证统一组件稳定 className、工具栏/单元格约束，并通过需求、角色、用户洞察和研发运营真实页面 smoke | Codex |
| v1.1.241 | 2026-06-06 | 补充需求管理列表布局回归验收，验证需求标题、迭代版本和操作列固定宽度、1600 横向滚动、详情页入口收敛到更多菜单，并通过真实页面 smoke | Codex |
| v1.1.240 | 2026-06-06 | 补充 PersistentMemoryStore 测试兼容层拆分验收，验证历史恢复、运行态过期和 DB-first 回归在迁移到 persistent_memory_store 后保持稳定 | Codex |
| v1.1.239 | 2026-06-06 | 补充 PostgresRuntimeStore runtime 模块拆分验收，验证 main.py 直接装配 persistence_runtime 后 data_access_mode、runtime store 和 DB-first 回归保持稳定 | Codex |
| v1.1.238 | 2026-06-06 | 补充 persistence.py payload/helper 拆分验收，验证 snapshot 恢复、清理、counter 同步和 DB-first 列表 read model 在拆到 persistence_payloads 后全量后端回归通过 | Codex |
| v1.1.237 | 2026-06-06 | 补充 persistence.py contracts/constants 拆分验收，验证仓储 Protocol 抽取后 persistence repository 边界、router 边界和 DB-first 列表 read model 回归不受影响 | Codex |
| v1.1.236 | 2026-06-06 | 补充 main.py 最终装配入口边界和任务工作流 repository source context 非 MemoryStore 回归验收，验证 legacy helper 删除后路由与 DB-first 契约不回退 | Codex |
| v1.1.235 | 2026-06-06 | 补充管理列表自定义渲染列布局验收，验证复杂 Tag/Space/状态摘要列不会撑开角色、用户洞察、DevOps 等宽表页面 | Codex |
| v1.1.234 | 2026-06-06 | 补充需求全链路详情版本内多需求对比页面验收，验证同版本需求数量、状态分布和当前需求位置展示 | Codex |
| v1.1.233 | 2026-06-06 | 补充需求全链路详情导出链路报告页面验收，验证导出 Markdown 报告包含需求标题、链路摘要、代码评审、Bug 和时间线信息 | Codex |
| v1.1.232 | 2026-06-06 | 补充需求全链路详情时间线类型筛选页面验收，验证按“代码评审”筛选后只展示代码评审事件并回显筛选后/总事件数 | Codex |
| v1.1.231 | 2026-06-06 | 补充模型网关配置列表服务端分页/筛选/排序和查询性能观测回归测试，验证 `GET /api/system/model-gateway-configs` 状态/默认配置筛选、分页元数据、`query/performance` 与非法排序字段校验；前端模型网关页测试更新为远程分页请求 | Codex |
| v1.1.230 | 2026-06-06 | 补充真实浏览器 smoke 关键文本断言验收，`scripts/web_page_smoke.mjs` 支持 `--expect-text ROUTE=TEXT`，生产就绪门禁默认验证角色管理页面渲染“系统管理员”，避免页面非空但核心数据未加载的假阳性 | Codex |
| v1.1.229 | 2026-06-06 | 补充角色管理列表服务端分页/筛选/排序和查询性能观测回归测试，验证 `GET /api/auth/roles` 分类/业务角色筛选、分页元数据、`query/performance` 与非法排序字段校验；前端角色页测试更新为远程分页请求 | Codex |
| v1.1.228 | 2026-06-06 | 补充任务管理待确认 Review 子表布局回归测试，验证固定布局、横向滚动宽度、摘要省略和操作列右固定，同时继续覆盖任务批量重试/取消请求与结果弹窗 | Codex |
| v1.1.227 | 2026-06-06 | 补充用户管理列表服务端分页/筛选/排序和查询性能观测回归测试，验证 `GET /api/users` 角色/状态/显示名筛选、分页元数据、`query/performance` 与非法排序字段校验；前端用户页测试更新为远程分页请求 | Codex |
| v1.1.226 | 2026-06-06 | 补充管理列表稳定表格默认值与角色详情承载测试，验证默认固定布局、数字横向滚动宽度、操作列右固定、角色入口/权限数量摘要和详情完整展示 | Codex |
| v1.1.225 | 2026-06-06 | persistence.py 拆分验收补充生命周期/看板写入委托边界测试，并复用 lifecycle/dashboard、缓存和 DB-first 持久化测试验证 edge/risk/snapshot 写入契约不回退 | Codex |
| v1.1.224 | 2026-06-06 | persistence.py 拆分验收补充采集运行/待归属写入委托边界测试，并复用 DB-first 持久化测试验证 collector run 与 pending attribution 写入契约不回退 | Codex |
| v1.1.223 | 2026-06-06 | persistence.py 拆分验收补充用户洞察写入委托边界测试，并复用用户洞察/DB-first 持久化测试验证反馈、使用指标、迭代建议/决策和转需求写入契约不回退 | Codex |
| v1.1.222 | 2026-06-06 | persistence.py 拆分验收补充 DevOps 指标写入委托边界测试，并复用 DevOps/DB-first 持久化测试验证 GitLab daily、Jenkins release 和线上日志写入契约不回退 | Codex |
| v1.1.221 | 2026-06-06 | persistence.py 拆分验收补充知识写入委托边界测试，并复用知识治理和 DB-first 持久化测试验证知识文档/chunk/沉淀写入契约不回退 | Codex |
| v1.1.220 | 2026-06-06 | persistence.py 拆分验收补充 Bug 写入委托边界测试，并复用 Bug 生命周期和 DB-first 持久化测试验证 Bug 写入、删除和重复缺陷引用契约不回退 | Codex |
| v1.1.219 | 2026-06-06 | persistence.py 拆分验收补充任务运行态写入委托边界测试，并复用任务/Review/Graph 和 DB-first 持久化测试验证运行态写入契约不回退 | Codex |
| v1.1.218 | 2026-06-06 | persistence.py 拆分验收补充 AI 任务主表写入委托边界测试，并复用任务 API 契约和 DB-first 持久化测试验证任务写入契约不回退 | Codex |
| v1.1.217 | 2026-06-06 | persistence.py 拆分验收补充需求写入委托边界测试，并复用需求生命周期、批量操作和 DB-first 持久化测试验证需求写入契约不回退 | Codex |
| v1.1.216 | 2026-06-06 | persistence.py 拆分验收补充产品配置写入委托边界测试，并复用产品配置与 DB-first 持久化测试验证产品/版本/模块/Git 仓库/相关系统写入契约不回退 | Codex |
| v1.1.215 | 2026-06-06 | persistence.py 拆分验收补充审计写入委托边界测试，并复用 DB-first 持久化测试验证审计保存、追加和恢复契约不回退 | Codex |
| v1.1.214 | 2026-06-06 | persistence.py 拆分验收补充 Git review 写入委托边界测试，并复用 GitLab/GitHub 快照、代码评审报告和 DB-first 持久化测试验证快照/报告写入契约不回退 | Codex |
| v1.1.213 | 2026-06-06 | persistence.py 拆分验收补充模拟 Issue 写回写入委托边界测试，并复用 mock writeback 与 DB-first 持久化测试验证幂等写回、恢复和 stale 数据过滤契约不回退 | Codex |
| v1.1.212 | 2026-06-06 | persistence.py 拆分验收补充 AI 助手写入委托边界测试，并复用助手聊天、助手上下文和 DB-first 持久化测试验证用户级历史/引用写入契约不回退 | Codex |
| v1.1.211 | 2026-06-06 | persistence.py 拆分验收补充模型网关写入委托边界测试，并复用模型网关 API 与 DB-first 持久化测试验证配置/日志写入契约不回退 | Codex |
| v1.1.210 | 2026-06-06 | 后端大文件拆分验收补充任务工作流/Review/Graph/Markdown 导出 legacy helper 清理回归，复用 router 边界、Graph Runtime、Review 行为、代码评审、模型网关和 DB-first 持久化测试验证契约不回退 | Codex |
| v1.1.209 | 2026-06-06 | 后端大文件拆分验收补充模型网关/代码评审 executor legacy helper 清理回归，复用模型网关、代码评审报告、AI 任务和 DB-first 持久化测试验证契约不回退 | Codex |
| v1.1.208 | 2026-06-06 | 后端大文件拆分验收补充 dashboard/DevOps/用户洞察 legacy 投影 helper 清理回归，复用看板、生命周期、DevOps、用户洞察和 DB-first 持久化测试验证契约不回退 | Codex |
| v1.1.207 | 2026-06-06 | 后端大文件拆分验收补充 operational_records legacy helper 清理回归，复用采集运行、待归属、DevOps 指标明细和 router 边界测试验证契约不回退 | Codex |
| v1.1.206 | 2026-06-06 | 后端大文件拆分验收补充需求全链路 legacy helper 清理回归，复用 requirements router 边界、需求生命周期和 DB-first stale runtime 测试验证契约不回退 | Codex |
| v1.1.205 | 2026-06-06 | 后端大文件拆分验收补充知识 legacy helper 清理回归，复用知识 router 边界、知识治理、DB-first 写入和 stale runtime 测试验证契约不回退 | Codex |
| v1.1.204 | 2026-06-06 | 后端大文件拆分验收补充生命周期 legacy helper 清理回归，复用 lifecycle router 边界、生命周期上下文 service、dashboard source rows 和 stale runtime 测试验证契约不回退 | Codex |
| v1.1.203 | 2026-06-06 | persistence.py 拆分验收补充业务大脑 read model 委托边界测试，覆盖 Brain App 恢复读取和 API 契约不回退 | Codex |
| v1.1.202 | 2026-06-06 | persistence.py 拆分验收扩展知识 read model 委托边界测试，覆盖知识恢复读取、知识文档列表、沉淀候选和检索委托契约 | Codex |
| v1.1.201 | 2026-06-06 | persistence.py 拆分验收扩展 Bug read model 委托边界测试，覆盖 Bug 恢复读取、Bug 列表 count/list 和分页筛选排序委托契约 | Codex |
| v1.1.200 | 2026-06-06 | persistence.py 拆分验收扩展任务 read model 委托边界测试，覆盖 AI 任务恢复、workflow runtime 恢复、任务列表 count/list 和待 Review 列表委托契约 | Codex |
| v1.1.199 | 2026-06-06 | persistence.py 拆分验收扩展需求 read model 委托边界测试，覆盖需求台账恢复读取、需求列表 count/list 和分页筛选排序委托契约 | Codex |
| v1.1.198 | 2026-06-06 | persistence.py 拆分验收扩展产品配置 read model 委托边界测试，覆盖产品配置恢复读取、产品列表、迭代版本列表和分页筛选排序委托契约 | Codex |
| v1.1.197 | 2026-06-06 | persistence.py 拆分验收扩展 AI 助手 read model 委托边界测试，覆盖会话/消息恢复读取、会话列表和用户级消息查询委托契约 | Codex |
| v1.1.196 | 2026-06-06 | persistence.py 拆分验收扩展用户洞察 read model 委托边界测试，覆盖使用指标、用户反馈、迭代规划恢复/列表读取和统一洞察列表委托契约 | Codex |
| v1.1.195 | 2026-06-06 | persistence.py 拆分验收扩展 DevOps read model 委托边界测试，覆盖 GitLab daily、Jenkins release、线上日志原始指标恢复/列表读取和统一运营列表委托契约 | Codex |
| v1.1.194 | 2026-06-06 | persistence.py 拆分验收补充生命周期上下文/首页看板读取委托边界测试，并复用 lifecycle/dashboard DB-first source rows、写入和 stale runtime 回归验证 LifecycleDashboardReadRepository 契约 | Codex |
| v1.1.193 | 2026-06-06 | persistence.py 拆分验收补充模拟 Issue 写回恢复读取委托边界测试，并复用 mock writeback 持久化、恢复和 stale 数据过滤回归验证 MockWritebackReadRepository 契约 | Codex |
| v1.1.192 | 2026-06-06 | persistence.py 拆分验收补充 Git review 快照/报告恢复读取委托边界测试，并复用 GitLab/GitHub 快照、代码评审报告和 DB-first 恢复回归验证 GitReviewReadRepository 契约 | Codex |
| v1.1.191 | 2026-06-06 | persistence.py 拆分验收补充采集运行/待归属队列读取委托边界测试，并复用 collector、pending attribution、DB-first stale runtime 和 router 边界测试验证 OperationalCollectionReadRepository 契约 | Codex |
| v1.1.190 | 2026-06-06 | persistence.py 拆分验收补充审计事件读取委托边界测试，并复用审计列表契约、DB-first stale runtime 和 audit router 边界测试验证 AuditReadRepository 契约 | Codex |
| v1.1.189 | 2026-06-06 | persistence.py 拆分验收补充模型网关配置/日志读取委托边界测试，并复用模型网关 API 与 DB-first 持久化回归验证 ModelGatewayReadRepository 契约 | Codex |
| v1.1.188 | 2026-06-06 | persistence.py 拆分验收补充 AI 助手历史读取委托边界测试，并复用助手服务、用户级历史隔离和 DB-first 持久化回归验证 AssistantChatReadRepository 契约 | Codex |
| v1.1.187 | 2026-06-06 | persistence.py 拆分验收补充知识中心 read model 委托边界测试，并复用知识文档列表、知识治理和 DB-first stale runtime 回归验证 KnowledgeReadRepository 契约 | Codex |
| v1.1.186 | 2026-06-06 | 后端大文件拆分验收补充 legacy helper 清理回归：复用 GitLab/GitHub 快照、用户洞察/迭代规划、生命周期上下文和 router 边界测试，验证删除 main.py 旧实现副本后服务化契约保持稳定 | Codex |
| v1.1.185 | 2026-06-06 | 生命周期上下文验收补充 lifecycle router 不得回调 legacy main 的架构边界回归，并复用 lifecycle_context 与 DB-first source rows 测试验证上下游、风险和 materialize 契约 | Codex |
| v1.1.184 | 2026-06-06 | GitLab/GitHub 代码评审链路验收补充 git_review router 不得回调 legacy main 的架构边界回归，并复用 GitLab MR、GitHub PR、DB-first 快照与审计测试验证服务化契约 | Codex |
| v1.1.183 | 2026-06-06 | 用户洞察与迭代规划验收补充 user_insights router 不得回调 legacy main 的架构边界回归，并复用使用指标、用户反馈、迭代建议和 DB-first 写入测试验证服务化契约 | Codex |
| v1.1.182 | 2026-06-06 | DevOps 指标明细验收补充 devops_metrics router 不得回调 legacy main 的架构边界回归，并复用 DevOps 指标、运营列表和 DB-first 写入测试验证服务化契约 | Codex |
| v1.1.181 | 2026-06-06 | 采集运行与待归属处理验收补充 collectors/attribution router 不得回调 legacy main 的架构边界回归，并复用 collector、pending attribution 和 DB-first 写入测试验证服务化契约 | Codex |
| v1.1.180 | 2026-06-06 | AI 任务创建验收补充 tasks router 整体不得回调 legacy main 的架构边界回归，并复用技术方案、后续任务、发布准备、代码评审和 DB-first 写入测试验证创建契约 | Codex |
| v1.1.179 | 2026-06-06 | AI 任务批量重试验收补充 batch-retry handler 不得回调 legacy main 的架构边界回归，并复用契约测试验证重试成功、不可重试/重复/不存在 skipped 和审计 | Codex |
| v1.1.178 | 2026-06-06 | Review 决策验收补充 approve/edit-approve/reject/request-more-info handler 不得回调 legacy main 的架构边界回归，并复用 Review 行为与 DB-first no-persist 测试验证保存契约 | Codex |
| v1.1.177 | 2026-06-06 | AI 任务启动验收补充 start handler 不得回调 legacy main 的架构边界回归，并同步模型网关失败注入测试到 model_gateway service opener | Codex |
| v1.1.176 | 2026-06-06 | AI 任务启动业务逻辑下沉到 ai_tasks service，回归覆盖 Graph Run/Checkpoint、模型失败、失败重试和 DB-first no-persist 保存契约 | Codex |
| v1.1.175 | 2026-06-06 | AI 任务启动前置迁移补充模型网关任务调用 helper service 化回归，覆盖模型失败、失败重试和 DB-first no-persist 写入契约 | Codex |
| v1.1.174 | 2026-06-06 | AI 任务批量取消验收补充 batch-cancel handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.173 | 2026-06-06 | AI 任务取消和补充信息提交验收补充 state write handlers 不得回调 legacy main 的架构边界回归，并复用 DB-first no-persist 测试验证任务状态直接写 repository | Codex |
| v1.1.172 | 2026-06-06 | Graph Run 列表、待确认 Review 列表和 Review 详情验收补充 read handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.171 | 2026-06-06 | AI 任务详情验收补充 detail handler 不得回调 legacy main 的架构边界回归，并覆盖 Graph/Review 流程下任务详情投影稳定性 | Codex |
| v1.1.170 | 2026-06-06 | 批量推进需求状态验收补充 batch-advance-status handler 和 requirements router 整体不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.169 | 2026-06-06 | 批量排期需求验收补充 batch-schedule handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.168 | 2026-06-06 | 批量分配需求负责人验收补充 batch-assign-owner handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.167 | 2026-06-06 | 批量需求生成产品详细设计任务验收补充 batch-generate-tasks handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.166 | 2026-06-06 | 单条需求生成产品详细设计任务验收补充 generate-task handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.165 | 2026-06-06 | 需求审批、驳回和关闭验收补充 decision handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.164 | 2026-06-06 | 需求修改和删除验收补充 update/delete handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.163 | 2026-06-06 | 需求创建验收补充 create handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.162 | 2026-06-06 | 需求详情和需求全链路验收补充 read handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.161 | 2026-06-06 | 研发运营统一列表验收补充 operational metrics handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.160 | 2026-06-06 | 用户洞察统一列表验收补充 items handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.159 | 2026-06-06 | AI 任务列表验收补充 list handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.158 | 2026-06-06 | 需求列表验收补充 list handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.157 | 2026-06-06 | Bug 管理验收升级为整个 bugs router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.156 | 2026-06-06 | Bug 创建、批量更新、修改和删除验收补充 write handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.155 | 2026-06-06 | 知识文档更新、重建索引和删除验收补充 write handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.154 | 2026-06-06 | 知识文档创建验收补充 create handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.153 | 2026-06-06 | 知识沉淀采纳/驳回验收补充 decision handlers 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.152 | 2026-06-06 | 知识搜索验收补充 search handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.151 | 2026-06-06 | 知识沉淀候选列表验收补充 list handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.150 | 2026-06-06 | 知识文档列表验收补充 list handler 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.149 | 2026-06-06 | 模拟 Issue 写回验收补充 writeback router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.148 | 2026-06-06 | 审计事件列表验收补充 audit router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.147 | 2026-06-06 | 代码评审报告读取验收补充 code_review_reports router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.146 | 2026-06-06 | Markdown 导出验收补充 export router 不得回调 legacy main 的架构边界回归 | Codex |
| v1.1.145 | 2026-06-06 | Bug 批量处理页面验收补充结果明细弹窗，覆盖批次号、更新数、跳过数和 skipped 原因展示 | Codex |
| v1.1.144 | 2026-06-06 | 任务批量取消/重试验收补充结果明细弹窗，覆盖批次号、成功数、仍失败数和 skipped 原因展示 | Codex |
| v1.1.143 | 2026-06-06 | 需求批量操作验收补充结果明细弹窗，覆盖批次号、成功数、跳过数和 skipped 原因展示 | Codex |
| v1.1.142 | 2026-06-06 | 需求批量推进状态验收补充未排期保护，覆盖 `REQUIREMENT_VERSION_REQUIRED` skipped 明细 | Codex |
| v1.1.141 | 2026-06-05 | 补充需求管理批量推进状态验收，覆盖合法状态推进、不符合路径 skipped 和审计 | Codex |
| v1.1.140 | 2026-06-05 | 补充需求管理批量分配负责人验收，覆盖负责人字段更新、关闭/重复/不存在 skipped 和审计 | Codex |
| v1.1.139 | 2026-06-05 | 补充任务管理批量重试验收，覆盖可重试失败任务恢复、终态/重复/不存在 skipped 和审计 | Codex |
| v1.1.138 | 2026-06-05 | 补充 AI 助手工具化查询引用链接验收，覆盖服务端 references、历史消息持久化和前端来源展示 | Codex |
| v1.1.137 | 2026-06-05 | 补充任务管理多选批量取消验收，覆盖合法任务取消、终态/重复/不存在任务 skipped 和审计 | Codex |
| v1.1.136 | 2026-06-05 | 补充需求全链路详情阶段明细折叠区和实体跳转链接页面验收 | Codex |
| v1.1.135 | 2026-06-05 | 补充前端管理主列表默认普通列宽、右侧固定操作列宽和横向滚动兜底的组件回归验收 | Codex |
| v1.1.134 | 2026-06-05 | 补充 `scripts/release_smoke.sh` 固定发布 smoke 入口验收，确保默认执行 `production_readiness_check.py --rebuild --web-smoke` | Codex |
| v1.1.133 | 2026-06-05 | 补充核心管理列表 `performance.p95_target_ms`、列表级 P95 目标和超目标慢查询日志验收 | Codex |
| v1.1.132 | 2026-06-05 | 补充 PostgresSnapshotRepository 研发运营统一列表 read model 委托到 DevopsReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.131 | 2026-06-05 | 补充 PostgresSnapshotRepository 用户洞察统一列表 read model 委托到 UserInsightReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.130 | 2026-06-05 | 补充 PostgresSnapshotRepository Bug 管理 read model 委托到 BugReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.129 | 2026-06-05 | 补充 PostgresSnapshotRepository AI 任务 read model 委托到 TaskReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.128 | 2026-06-05 | 补充 PostgresSnapshotRepository 需求管理 read model 委托到 RequirementReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.127 | 2026-06-05 | 补充 PostgresSnapshotRepository 产品配置 read model 委托到 ProductConfigReadRepository 的 repository 边界回归验收 | Codex |
| v1.1.126 | 2026-06-05 | 补充采集运行、待归属处理和生命周期上下文 API 独立 router 挂载、功能回归和 main.py 无业务路由边界验收 | Codex |
| v1.1.125 | 2026-06-05 | 补充 Markdown 导出 API 独立 export router 挂载、完成态导出和读取权限回归验收 | Codex |
| v1.1.124 | 2026-06-05 | 补充写回结果、代码评审报告和审计事件 API 独立 router 挂载、DB-first 写入/读取和单一路由归属回归验收 | Codex |
| v1.1.123 | 2026-06-05 | 补充用户洞察与迭代建议 API 独立 user_insights router 挂载、SQL/read model 列表和单一路由归属回归验收 | Codex |
| v1.1.122 | 2026-06-05 | 补充研发运营指标 API 独立 devops_metrics router 挂载、SQL/read model 列表和单一路由归属回归验收 | Codex |
| v1.1.121 | 2026-06-05 | 补充知识中心 API 独立 knowledge router 挂载和单一路由归属回归验收 | Codex |
| v1.1.120 | 2026-06-05 | 补充 AI 任务列表与创建 handler 脱离 main.py 的架构边界回归验收 | Codex |
| v1.1.119 | 2026-06-05 | 补充 AI 任务与 Review API 独立 tasks router 挂载、任务列表 SQL read model 和单一路由归属回归验收 | Codex |
| v1.1.118 | 2026-06-05 | 补充需求交付 API 独立 requirements router 挂载、SQL read model 列表和单一路由归属回归验收 | Codex |
| v1.1.117 | 2026-06-05 | 补充 Bug 管理 API 独立 bugs router 挂载、生命周期 service 复用和单一路由归属回归验收 | Codex |
| v1.1.116 | 2026-06-05 | 补充 GitLab MR / GitHub PR 预览、列表和快照 API 独立 git_review router 挂载和单一路由归属回归验收 | Codex |
| v1.1.115 | 2026-06-05 | 补充业务大脑只读 API 独立 brain_apps router 挂载、repository-first service 拆分和单一路由归属回归验收 | Codex |
| v1.1.114 | 2026-06-05 | 补充模型网关配置和日志 API 独立 model_gateway router 挂载、service helper 拆分和单一路由归属回归验收 | Codex |
| v1.1.113 | 2026-06-05 | 补充相关系统 API 独立 related_systems router 挂载和单一路由归属回归验收 | Codex |
| v1.1.112 | 2026-06-05 | 补充产品 Git 仓库 API 独立 product_git_repositories router 挂载和单一路由归属回归验收 | Codex |
| v1.1.111 | 2026-06-05 | 补充产品模块 API 独立 product_modules router 挂载和单一路由归属回归验收 | Codex |
| v1.1.110 | 2026-06-05 | 补充迭代版本 API 独立 product_versions router 挂载和单一路由归属回归验收 | Codex |
| v1.1.109 | 2026-06-05 | 补充产品主体 CRUD API 独立 products router 挂载和单一路由归属回归验收 | Codex |
| v1.1.108 | 2026-06-05 | 补充用户管理 API 独立 users router 挂载和单一路由归属回归验收 | Codex |
| v1.1.107 | 2026-06-05 | 补充平台健康检查与长期记忆状态 API 独立 platform router 挂载和单一路由归属回归验收 | Codex |
| v1.1.106 | 2026-06-05 | 补充认证与角色目录 API 独立 auth router 挂载和单一路由归属回归验收 | Codex |
| v1.1.105 | 2026-06-05 | 补充首页 IT 团队看板 API 独立 router 挂载和单一路由归属回归验收 | Codex |
| v1.1.104 | 2026-06-05 | 补充 AI 助手 API 独立 router 迁移后的接口回归验收 | Codex |
| v1.1.103 | 2026-06-05 | 补充 AI 助手聊天工作流 service 拆分和用户级历史隔离 service 单测验收 | Codex |
| v1.1.102 | 2026-06-05 | 补充首页 IT 团队看板缓存命中、强制刷新、缓存元数据和慢查询日志验收 | Codex |
| v1.1.101 | 2026-06-05 | 补充 `scripts/web_page_smoke.mjs` 浏览器页面 smoke 和列表慢查询日志验收 | Codex |
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
| v1.1.3 | 2026-05-31 | 补充审计按操作者和时间范围过滤，以及审计列表详情、链路追踪页面验收 | Codex |
| v1.1.4 | 2026-05-31 | 补充 code_review 执行器失败专用错误码和审计断言 | Codex |
| v1.1.5 | 2026-05-31 | 补充 GitLab MR diff 超限失败审计验收 | Codex |
| v1.1.6 | 2026-05-31 | 补充 GitLab MR 变更文件数超限验收 | Codex |
| v1.1.7 | 2026-05-31 | 补充 GitLab MR 单文件 diff 行数超限验收 | Codex |
| v1.1.8 | 2026-05-31 | 补充 MVP 角色目录接口、用户管理角色固定选择和 SQL 角色字典验收 | Codex |
| v1.1.9 | 2026-05-31 | 补充产品配置写入 PostgreSQL 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.10 | 2026-05-31 | 补充需求台账写入 PostgreSQL `requirements` 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.11 | 2026-05-31 | 补充 AI 任务写入 PostgreSQL `ai_tasks` 结构表并可从结构表恢复的持久化验收 | Codex |
| v1.1.12 | 2026-05-31 | 补充人工确认、Graph Run 和检查点写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.13 | 2026-05-31 | 补充角色目录职责、数据范围、决策范围和前端角色目录加载验收 | Codex |
| v1.1.14 | 2026-05-31 | 补充知识文档、知识沉淀候选和审计事件写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.15 | 2026-05-31 | 补充 Bug 管理写入 PostgreSQL `bugs` 结构表并可恢复的持久化验收 | Codex |
| v1.1.16 | 2026-05-31 | 补充模型网关配置和调用元数据日志写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.17 | 2026-05-31 | 补充 GitLab MR 快照和 Code Review 报告写入 PostgreSQL 结构表并可恢复的持久化验收 | Codex |
| v1.1.18 | 2026-05-31 | 补充模拟 Issue 回写写入 PostgreSQL `mock_issues` 结构表并可恢复的持久化验收 | Codex |
| v1.1.19 | 2026-05-31 | 补充相关系统写入 PostgreSQL `related_systems` 结构表并可恢复的持久化验收 | Codex |
| v1.1.20 | 2026-05-31 | 补充角色业务映射、可见入口、限制边界和知识索引失败重试验收 | Codex |
| v1.1.21 | 2026-06-01 | 补充生命周期从审计主体、Review、报告、模拟 Issue 和知识沉淀起点追踪验收 | Codex |
| v1.1.22 | 2026-06-01 | 补充知识检索不得为缺失 chunk 的 indexed 文档合成兜底结果的验收 | Codex |
| v1.1.23 | 2026-06-01 | 补充 GitLab MR 相同 diff 快照复用和审计验收 | Codex |
| v1.1.24 | 2026-06-01 | 补充迭代规划建议基于真实反馈/Bug 证据生成、确认和可选转需求的自动化验收 | Codex |
| v1.1.25 | 2026-06-01 | 补充用户使用指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.26 | 2026-06-01 | 补充 GitLab 每日代码指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.27 | 2026-06-01 | 补充 Jenkins 发布记录真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.28 | 2026-06-01 | 补充线上运行日志指标真实登记、筛选、审计和 PostgreSQL 持久化验收 | Codex |
| v1.1.29 | 2026-06-01 | 补充开发计划和自动化测试任务从已确认技术方案创建、人工确认和 AI 自动测试 Bug 入库验收 | Codex |
| v1.1.30 | 2026-06-01 | 补充发布评估和上线后分析任务从已确认上游任务创建、人工确认和 AI 上线后 Bug 入库验收 | Codex |
| v1.1.31 | 2026-06-01 | 补充首页 IT 团队看板产品筛选页面验收和前端服务查询参数验收 | Codex |
| v1.1.32 | 2026-06-01 | 补充首页 IT 团队看板按产品过滤知识文档和审计事件验收 | Codex |
| v1.1.33 | 2026-06-02 | 补充 Bug 管理工作台复现步骤、证据 JSON、重复归并和来源只读展示自动化验收 | Codex |
| v1.1.34 | 2026-06-02 | 对账 MVP 详细测试用例状态，将已有自动化覆盖的待测试项标为已覆盖，并保留生产就绪和 v1.2 待验范围 | Codex |
| v1.1.35 | 2026-06-02 | 补充首页 IT 团队看板 Bug、DevOps、线上日志、用户洞察和迭代规划聚合及产品/时间范围下钻验收 | Codex |
| v1.1.36 | 2026-06-02 | 补充生命周期 v1.2 真实证据主体、风险信号和动态缺失上下文自动化验收 | Codex |
| v1.1.37 | 2026-06-02 | 补充采集运行记录 API、持久化、审计和研发运营页面自动化验收 | Codex |
| v1.1.38 | 2026-06-02 | 补充待归属数据队列登记、归属/忽略、持久化、审计和前端页面自动化验收 | Codex |
| v1.1.39 | 2026-06-02 | 补充 AI 任务启动由真实 LangGraph StateGraph 驱动并持久化 runtime/node_path 的验收 | Codex |
| v1.1.40 | 2026-06-02 | 补充 GBrain 长期记忆连接器配置状态和密钥脱敏验收 | Codex |
| v1.1.41 | 2026-06-02 | 补充 GitHub provider、GitHub PR 预览和 diff 快照验收 | Codex |
| v1.1.42 | 2026-06-02 | 补充 AI 助手聊天工作台和系统进展问答验收 | Codex |
| v1.1.43 | 2026-06-03 | 记录 AI 助手真实需求全链路复跑结果，并补充 GitHub PR 列表、健康检查和失败任务重试验收 | Codex |
| v1.1.44 | 2026-06-03 | 记录 AI Brain GitHub PR 复跑卡点，补充 code-review 外部命令缺失时复用模型网关、携带 Review 上下文并规范化输出的回归验收 | Codex |
| v1.1.45 | 2026-06-03 | 补充 Embedding 不可用时文本索引兜底和补向量索引验收 | Codex |
| v1.1.46 | 2026-06-03 | 补充 Chat-only 模型网关、单独 Embedding 连接和向量兼容过滤验收 | Codex |
| v1.1.47 | 2026-06-03 | 补充新增需求可不指定迭代版本、需求池排期和需求交付/迭代版本页面验收 | Codex |
| v1.1.48 | 2026-06-03 | 补充 DB-first 任务运行态/Review repository 读路径和 Mock Writeback handler 级写入回归验收 | Codex |
| v1.1.49 | 2026-06-03 | 补充知识沉淀候选列表 repository-first 读取和运行态 store 过期回归验收 | Codex |
| v1.1.50 | 2026-06-03 | 补充知识检索 repository-first 候选查询、权限过滤和运行态 store 过期回归验收 | Codex |
| v1.1.51 | 2026-06-03 | 补充知识沉淀审核写接口 repository 当前记录读取和运行态 store 过期回归验收 | Codex |
| v1.1.52 | 2026-06-03 | 补充生命周期上下文和首页 IT 团队看板 repository source rows 聚合、handler 级写回和 stale-runtime 回归验收 | Codex |
| v1.1.53 | 2026-06-03 | 补充需求/任务详情、Graph Run、Review、回写、Code Review 报告和 Markdown 导出 task workflow source rows 读取回归验收 | Codex |
| v1.1.54 | 2026-06-03 | 补充任务启动、取消、补充信息和 Review 决策写路径在全局运行时 store 过期时仍使用 task workflow source rows 的回归验收 | Codex |
| v1.1.55 | 2026-06-03 | 补充 PostgreSQL 启动返回 PostgresRuntimeStore repository 容器且不预加载业务集合的回归验收 | Codex |
| v1.1.56 | 2026-06-03 | 补充产品配置、需求/任务创建和 Bug 写接口在 PostgresRuntimeStore 空启动容器下仍从 repository source rows 校验上下文的回归验收 | Codex |
| v1.1.57 | 2026-06-03 | 补充运营采集、用户洞察和迭代规划写接口在 PostgresRuntimeStore 空启动容器下仍从 repository source rows 校验上下文的回归验收 | Codex |
| v1.1.58 | 2026-06-03 | 补充模型网关配置和 AI 助手聊天写接口在 PostgresRuntimeStore 空启动容器下仍从 repository 上下文恢复当前记录的回归验收 | Codex |
| v1.1.59 | 2026-06-03 | 补充知识文档和知识沉淀写接口在 PostgresRuntimeStore 空启动容器下仍从 repository 上下文恢复当前记录的回归验收 | Codex |
| v1.1.60 | 2026-06-03 | 补充 GitLab/GitHub PR/MR 预览、列表和快照写路径在 PostgresRuntimeStore 空启动容器下仍从 repository 上下文恢复 Git 资源、需求和任务的回归验收 | Codex |
| v1.1.61 | 2026-06-03 | 补充业务大脑只读接口 repository-first、生产 read snapshot fallback 移除、知识沉淀驳回和 Mock Writeback 生成 source rows 回归验收 | Codex |
| v1.1.62 | 2026-06-03 | 补充生命周期上下文 source rows 使用专用 read model 而非 MemoryStore 投影的回归验收 | Codex |
| v1.1.63 | 2026-06-03 | 补充产品配置、模型网关、助手、需求、任务创建和 Bug 写接口直接提交 repository records/payloads，且只读缓存不得作为写入事实源的回归验收 | Codex |
| v1.1.64 | 2026-06-03 | 补充知识索引、任务运行态新增记录、运营采集、用户洞察和迭代规划写接口直接提交 repository payloads，不以请求态集合为 PostgreSQL 写入源的回归验收 | Codex |
| v1.1.65 | 2026-06-04 | 增加前端和用户可见流程提交前的真实网页界面验证门禁用例 | Codex |
| v1.1.66 | 2026-06-04 | 补充多需求批量排期、迭代版本页归集需求和审计验收 | Codex |
| v1.1.67 | 2026-06-04 | 补充 planning 迭代版本可被需求页批量排期选择、archived 版本过滤和批次审计追加保存回归验收 | Codex |
| v1.1.68 | 2026-06-04 | 补充迭代版本状态推进、影响预览、需求状态同步和阻塞项回归验收 | Codex |
| v1.1.69 | 2026-06-04 | 补充需求管理按迭代版本查询需求列表的页面验收 | Codex |
| v1.1.70 | 2026-06-04 | 补充 Bug 管理按迭代版本展示和查询缺陷列表的验收 | Codex |
| v1.1.71 | 2026-06-04 | 调整迭代版本进入测试中的验收口径，确认版本内已进入交付链路的需求统一同步为测试中 | Codex |
| v1.1.72 | 2026-06-04 | 补充登记 Bug 目标版本可选择测试中/已发布未归档版本并过滤 archived 的页面回归验收 | Codex |
| v1.1.73 | 2026-06-04 | 补充日期/时间登记字段使用 Ant Design DatePicker 的页面回归验收 | Codex |
| v1.1.74 | 2026-06-04 | 补充 Bug 管理列表展示创建时间的页面回归验收 | Codex |
| v1.1.75 | 2026-06-04 | 补充需求管理列表展示创建时间且不再展示更新时间的页面回归验收 | Codex |
| v1.1.76 | 2026-06-04 | 补充用户洞察列表固定列宽、操作列右侧固定和详情弹窗页面回归验收 | Codex |
| v1.1.77 | 2026-06-04 | 补充管理主列表统一服务端分页、排序和筛选验收，覆盖用户洞察与研发运营聚合页 | Codex |
| v1.1.78 | 2026-06-04 | 补充需求全链路详情接口和需求管理页时间线弹窗自动化验收 | Codex |
| v1.1.79 | 2026-06-04 | 补充 Bug 管理批量处理接口、状态机跳过明细、批次审计和页面多选入口验收 | Codex |
| v1.1.80 | 2026-06-05 | 补充 AI 助手系统上下文增强验收，覆盖迭代进度、阻塞需求、待确认 Review、代码评审结论、Bug 分布和知识沉淀摘要 | Codex |
| v1.1.81 | 2026-06-05 | 补充 GitLab/GitHub PR/MR 预览展示 diff 文件树、风险摘要和 Review Checklist 的验收 | Codex |
| v1.1.82 | 2026-06-05 | 补充需求全链路详情页展示 PR/MR 快照风险摘要、diff 文件树和 Review Checklist 的页面验收 | Codex |
| v1.1.83 | 2026-06-05 | 补充角色管理列表摘要化展示和详情弹窗承载完整角色定义的页面验收 | Codex |
| v1.1.84 | 2026-06-05 | 补充核心管理主列表 `query/performance` 查询观测元数据、统一表格兜底规范和发布 smoke Web/API 门禁验收 | Codex |
| v1.1.84 | 2026-06-05 | 补充需求批量生成产品详细设计任务、skipped 明细和批次审计的 API 与页面验收 | Codex |
| v1.1.85 | 2026-06-05 | 补充需求全链路详情阶段进度视图页面验收 | Codex |
| v1.1.86 | 2026-06-05 | 补充需求全链路独立详情页直达路由、返回入口和共享展示组件页面验收 | Codex |
| v1.1.87 | 2026-06-05 | 补充用户洞察统一列表 SQL read model 分页、排序和筛选回归验收 | Codex |
| v1.1.88 | 2026-06-05 | 补充需求全链路详情响应式弹窗、阶段状态中文展示和横向裁切回归验收 | Codex |
| v1.1.89 | 2026-06-05 | 补充研发运营统一列表 SQL read model 分页、排序和筛选回归验收 | Codex |
| v1.1.90 | 2026-06-05 | 明确管理主列表服务端 SQL/read model 查询与首页看板 PostgreSQL source rows + Python 聚合的不同验收边界 | Codex |
| v1.1.91 | 2026-06-05 | 补充迭代版本状态推进 domain service 拆分和 service 层单测验收 | Codex |
| v1.1.92 | 2026-06-05 | 补充 Bug 生命周期 domain service 拆分和 service 层单测验收 | Codex |
| v1.1.99 | 2026-06-05 | 补充需求管理和 Bug 管理列表 PostgreSQL SQL read model 分页、排序和筛选回归验收 | Codex |
| v1.1.100 | 2026-06-05 | 补充产品管理和迭代版本列表 PostgreSQL SQL read model 分页、排序和筛选回归验收 | Codex |

---
