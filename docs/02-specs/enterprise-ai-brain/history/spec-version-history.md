# 技术规格版本历史

> 从 [spec.md](../spec.md) 拆出，保留完整版本历史，主文档只维护当前事实与导航。

# 企业 AI 大脑平台技术规格

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.1.883 |
| 适用系统版本 | ≥ v1.0.0 |
| 文档状态 | Approved |

**版本历史**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.1.883 | 2026-07-09 | 系统设置邮件发送敏感配置变更新增后端强制二次确认，审计只记录字段、配置状态和确认状态 | Codex |
| v1.1.882 | 2026-07-04 | 钉钉官方 MCP 插件补充授权向导、动态能力发现、高风险动作治理、插件观测看板和业务场景模板技术契约 | Codex |
| v1.1.881 | 2026-07-04 | 插件数据模型补充钉钉官方 MCP P0 标准插件、`mcp_streamable_http` 协议、`url_key` 鉴权和 P0 动作模板风险分层 | Codex |
| v1.1.880 | 2026-07-03 | 产品 Git 资源编辑修复 Project Path 保存语义：显式 Project Path 覆盖优先，仅修改 Remote URL 时重新推导仓库路径 | Codex |
| v1.1.879 | 2026-07-03 | 定时作业运行记录读模型补充作业名称投影，运行记录列表和详情优先展示作业名称 | Codex |
| v1.1.878 | 2026-07-03 | 系统设置扩展邮件发送配置，支持 SMTP Host/端口/TLS/用户名/密码或密钥引用、默认发件人、Reply-To 和测试发送，响应与审计均不回显密钥 | Codex |
| v1.1.877 | 2026-07-03 | GitLab 官方连接改为 Endpoint + Token 凭据连接，GitLab 地址仅作为可选默认项目参数，代码巡检继续使用产品代码库 Remote URL | Codex |
| v1.1.876 | 2026-07-03 | GitHub 官方连接改为凭据连接：Token 必填、仓库地址可选，产品代码库继续维护实际 Remote URL | Codex |
| v1.1.875 | 2026-07-03 | 本地完整代码巡检支持从任务绑定的 GitHub/GitLab 插件连接读取只读 token，产品代码库继续只维护 remote_url | Codex |
| v1.1.874 | 2026-07-03 | 系统管理新增系统设置页，管理员邮箱写入 `system_settings`，通过 `system.settings.manage` 权限和审计事件治理 | Codex |
| v1.1.873 | 2026-07-03 | 代码巡检定时作业支持产品级默认多仓扫描、Worker 重试、默认 AI 输出 Schema 和按仓库运行节点明细 | Codex |
| v1.1.872 | 2026-07-03 | 产品管理 Git 资源配置以 Remote URL 为默认必填输入，后端自动推导 `project_path` 并保留显式覆盖能力 | Codex |
| v1.1.871 | 2026-07-03 | 需求删除保护补充 AI 任务占用数量，前端将 `RESOURCE_IN_USE` 转为中文处理建议 | Codex |
| v1.1.870 | 2026-07-03 | Bug 管理已上传图片支持点击预览，预览接口校验 `bug.read` 并仅代理 Bug 图片证据对象 | Codex |
| v1.1.869 | 2026-07-03 | Bug 管理新增图片证据上传接口和页面上传/粘贴能力，图片进入 MinIO/S3-compatible 对象存储并以 evidence 元数据关联 Bug | Codex |
| v1.1.868 | 2026-07-03 | 插件配置删除保护不再将历史插件调用日志作为硬阻断，删除插件/连接/动作时保留日志并置空对应引用 | Codex |
| v1.1.867 | 2026-07-02 | 定时作业 AI 处理链路新增 `config_json.ai_executor` 执行器选择：系统默认执行器走模型网关，本地 Runner 派发 `ai_executor_task` 并在完成回写后继续结果动作 | Codex |
| v1.1.866 | 2026-07-02 | 样例复用向导新增进度汇总，连接测试、动作试运行、dry-run 与作业草稿页统一展示“已就绪步骤 / 总步骤” | Codex |
| v1.1.865 | 2026-07-02 | AI 执行器 Runner 就绪清单新增“沙箱权限边界”控制项，安装包代理心跳上报安全边界元数据 | Codex |
| v1.1.864 | 2026-07-02 | 插件动作新增 AI 执行器高风险审批写回接口，审批后可自动重新试运行并进入 Runner 队列 | Codex |
| v1.1.864 | 2026-07-02 | AI 执行器高风险审批请求持久化为 `ai_executor_approval_requests`，支持独立查询与审批写回 | Codex |
| v1.1.863 | 2026-07-02 | 动作试运行失败时即使返回 `scheduled_job_dry_run_seed`，前端也按 `reuse_wizard` 展示缺失项并禁止生成作业草稿 | Codex |
| v1.1.862 | 2026-07-02 | AI 执行器 Runner 高风险指令阻断响应新增 `approval_request` 审批草案，并写入 `ai_executor_task.approval_requested` 审计 | Codex |
| v1.1.861 | 2026-07-02 | 定时作业 Trace DAG 保护态节点也可打开复跑预检，并可按 `full_run_request` 直接发起整条运行记录复跑 | Codex |
| v1.1.860 | 2026-07-02 | 定时作业 Trace DAG 单节点复跑成功后前端刷新运行列表、切到运行记录并打开新运行详情，避免用户找不到复跑结果 | Codex |
| v1.1.859 | 2026-07-02 | 普通插件执行调用在 `ai_assisted/ai_generated` 模式下正式运行会先经 Skill/模型处理，再执行通用结果动作，和 dry-run 的 AI 预览保持一致 | Codex |
| v1.1.858 | 2026-07-02 | Agent/Skill 文件包公开运行边界收口到 `scripts/` 合法脚本资产，非 scripts 可执行文件继续拒绝上传且不在运行能力中展示 | Codex |
| v1.1.857 | 2026-07-02 | AI 执行器 Runner 安装包代理增加真实执行探针验收，确认本地命令通过 stdin 接收指令、流式日志和完成回写链路可运行 | Codex |
| v1.1.856 | 2026-07-02 | 动作试运行生成定时作业草稿时可携带自动 dry-run 标记，新增作业页在存在响应样例时自动复用样例执行全链路试运行 | Codex |
| v1.1.855 | 2026-07-02 | AI 执行器 Runner 运行中轮询服务端任务终态，取消或超时后终止本地进程树且不覆盖平台终态 | Codex |
| v1.1.854 | 2026-07-02 | AI 执行器 Runner 安装包启用进程组隔离，超时后终止整棵执行器进程树并回写日志 | Codex |
| v1.1.853 | 2026-07-02 | 插件管理执行器列表新增 Runner 超时扫描入口，页面直接展示 summary/next_actions 运维建议 | Codex |
| v1.1.852 | 2026-07-02 | AI 执行器 Runner 超时扫描响应补充 `summary/next_actions`，直接展示重派、死信、超时数量和后续处理建议 | Codex |
| v1.1.851 | 2026-07-02 | 定时作业 dry-run 支持复用动作试运行草稿中的 `config_json.sample_reuse.response_summary`，跳过重复第三方请求并延续样例来源 | Codex |
| v1.1.850 | 2026-07-02 | Trace DAG AI 处理节点在具备输入快照、模型幂等键和下游隔离策略时支持受控单节点复跑，复用来源数据连接响应快照重新调用模型且不执行动作 | Codex |
| v1.1.849 | 2026-07-02 | Trace DAG 通用结果动作节点在具备动作输入/输出快照和写入幂等键时支持受控单节点复跑，复用来源 AI 输出快照生成独立结果写入记录 | Codex |
| v1.1.848 | 2026-07-02 | Trace DAG 数据连接节点在具备请求快照、连接读取幂等键和下游隔离策略时支持受控单节点复跑，生成独立运行记录且不执行下游 AI/动作 | Codex |
| v1.1.847 | 2026-07-02 | AI 执行器 Runner 高风险指令审批契约落地：未携带完整审批快照继续阻断，审批操作覆盖、策略版本和有效期校验通过后可入队并写审计 | Codex |
| v1.1.846 | 2026-07-02 | Agent/Skill 文件包允许携带 `scripts/` 脚本资产但不执行，非 scripts 目录可执行脚本继续拒绝，为后续沙箱执行预留资产边界 | Codex |
| v1.1.845 | 2026-07-02 | AI角色支持上传 Agent 文件包，`AGENT.md` 作为系统提示词，`agent.yaml` 声明默认 Skill/模型网关，脚本仍保持待沙箱运行边界 | Codex |
| v1.1.844 | 2026-07-02 | 样例复用向导补齐当前步骤、下一步说明和交接摘要，连接测试、动作试运行、dry-run 与作业草稿页统一展示已带入内容 | Codex |
| v1.1.843 | 2026-07-02 | AI 执行器 Runner 增加高风险指令服务端预检和本地 agent 兜底，push、删除、强制 reset、发布部署类指令在审批流接入前不得进入执行队列 | Codex |
| v1.1.842 | 2026-07-02 | AI 执行器 Runner 安装包强制命令白名单，运行就绪清单拆分命令白名单、禁用 shell 和高风险操作审批状态 | Codex |
| v1.1.841 | 2026-07-02 | Trace DAG 节点复跑预检新增执行策略和下一步动作，明确保护态原因、推荐整条复跑和待补齐控制项 | Codex |
| v1.1.840 | 2026-07-02 | 连接测试样例复制为动作后自动携带样例响应触发动作试运行，直接生成写入预览和作业草稿入口 | Codex |
| v1.1.839 | 2026-07-02 | AI 执行器 Runner 列表新增运行就绪清单，按注册、心跳、Token、白名单、队列、超时、日志、回写和沙箱边界展示状态 | Codex |
| v1.1.838 | 2026-07-02 | Trace DAG 节点复跑预检补齐结构化控制项清单和摘要，区分已满足、缺失、阻断和待确认控制项 | Codex |
| v1.1.837 | 2026-07-02 | AI 执行器 Runner 列表补齐队列摘要，展示排队、运行中、异常、可用槽和最近失败原因，提升本地 Runner 运维可见性 | Codex |
| v1.1.836 | 2026-07-02 | 动作试运行生成定时作业草稿后，新增页展示样例复用来源、连接、动作、写入目标和预计写入，引导继续全链路试运行 | Codex |
| v1.1.835 | 2026-07-02 | 定时作业运行详情 Trace DAG 节点补齐复跑预检展示，页面可直接查看阻断原因、缺失控制和快照体积 | Codex |
| v1.1.834 | 2026-07-02 | Trace DAG 节点级复跑补齐只读预检和快照预览，先显式返回缺失控制项再允许后续演进真实复跑 | Codex |
| v1.1.833 | 2026-07-02 | 连接测试、动作试运行和定时作业 dry-run 样例复用统一沉淀 `reuse_wizard`，作为作业配置向导的步骤状态和下一步动作契约 | Codex |
| v1.1.832 | 2026-07-02 | 定时作业 Trace DAG 增加节点级复跑受保护 API，返回节点快照、阻断控制、整条复跑替代请求并写入审计 | Codex |
| v1.1.831 | 2026-07-02 | AI 执行器 Runner 代理改为 Popen 流式追加 stdout/stderr 日志，安装包安全配置声明无 shell 执行、stdin 指令传递和日志 flush 策略 | Codex |
| v1.1.830 | 2026-07-02 | AI 执行器 Runner 安装包内置可运行轮询代理，完成回写保留流式追加日志 | Codex |
| v1.1.829 | 2026-07-02 | AI 执行器 Runner 工作区白名单升级为派发和认领双重校验，白名单目录可覆盖子工作区，越界任务失败并回写日志 | Codex |
| v1.1.828 | 2026-07-02 | Trace DAG 补齐受保护复跑计划和快照状态，动作试运行样例可生成定时作业草稿，AI Skill 运行边界明确脚本待沙箱 | Codex |
| v1.1.827 | 2026-07-02 | 定时作业 Trace DAG 节点补齐阶段、复制调试动作和复跑边界提示，试运行面板展示 Skill 输出映射校验摘要，列表加载态避免误判空数据 | Codex |
| v1.1.826 | 2026-07-02 | 定时作业通用 AI 分析链路补齐 `generic_result_actions` catalog、通用结果动作写入预览和多连接同插件校验 | Codex |
| v1.1.825 | 2026-07-02 | 定时作业运行详情基础信息展示 `result_summary.message` 用户可读摘要，便于插件执行调用结果直接判断 | Codex |
| v1.1.824 | 2026-07-02 | 插件执行调用类定时作业成功摘要返回 `job_type` 与“插件执行调用完成”，避免排障详情出现开发占位文案 | Codex |
| v1.1.823 | 2026-07-02 | 定时作业模型输出 Schema 校验失败时仍保留模型调用日志，并在失败运行摘要中返回 `model_log_id` 等 AI 排障元数据 | Codex |
| v1.1.822 | 2026-07-02 | 定时作业正式运行补齐 Skill 输出 JSON Schema 子集校验，必填字段、对象/数组/基础类型和数组 item 类型不匹配时阻止动作写入 | Codex |
| v1.1.821 | 2026-07-02 | 定时作业 dry-run Skill 输出样例对未声明 item schema 的常见业务数组生成结构化样例，提升写入预览样例记录可读性 | Codex |
| v1.1.820 | 2026-07-02 | 定时作业全链路试运行结果面板补充 `output_preview_source` 和 `write_preview_source` 的中文摘要展示，保留 JSON 排障区 | Codex |
| v1.1.819 | 2026-07-02 | 定时作业 dry-run AI 场景补齐 Skill 输出 Schema 样例预览，结果动作写入预览按 AI 输出结构计算并返回预览来源 | Codex |
| v1.1.818 | 2026-07-02 | 定时作业 Trace DAG 边关系改为按节点层连接，多数据连接 fan-in 到 AI/动作节点，多结果动作从上游节点 fan-out，避免同层节点被误判为依赖链 | Codex |
| v1.1.817 | 2026-07-02 | 定时作业失败阶段归因、AI 助手诊断和运行健康统计补齐多节点消费：数据连接失败不再标记 AI 已调用，多连接/多动作诊断和写入统计按明细聚合 | Codex |
| v1.1.816 | 2026-07-02 | 定时作业多数据连接补齐运行层失败策略，失败连接进入明细节点，`continue_on_error` 继续合并成功连接数据，`fail_fast` 保留失败 Trace 后中断 | Codex |
| v1.1.815 | 2026-07-02 | 用户反馈洞察定时作业补齐多结果动作失败策略落地，默认 `continue_on_error` 时失败动作记录明细并继续后续写入，`fail_fast` 保持中断语义 | Codex |
| v1.1.814 | 2026-07-02 | 定时作业运行 Trace DAG 对 `data_connection.items[]` 和 `execution_nodes.result_actions[]` 展开明细节点，保留旧单节点运行兼容 | Codex |
| v1.1.813 | 2026-07-02 | 定时作业 Skill 输出 Schema 契约校验与动作结果映射共用 JSONPath token 规则，dry-run 返回 `mapping_contract.checked_paths/invalid_fields` 诊断 | Codex |
| v1.1.812 | 2026-07-02 | 插件动作和定时作业结果映射 JSONPath 子集扩展为支持 bracket key、数组下标和 `[*]` 通配，写入预览与运行记录共用同一解析口径 | Codex |
| v1.1.811 | 2026-07-01 | 定时作业 Catalog 增加 `allow_create/runnable/unavailable_reason`，新增表单只展示已闭环类型，后端创建和手动运行共同拒绝未完成运行处理器 | Codex |
| v1.1.810 | 2026-07-01 | 内部数据源移除 `product_scope` 配置项并按源权限返回 access_issues；定时作业数据连接配置去掉连接环境筛选，用户反馈洞察运行摘要和结果写入记录支持多动作反馈 | Codex |
| v1.1.809 | 2026-07-01 | AI 助手定时作业草案引用数组统一跳过 null/空字符串并保序去重，预览和确认保存使用同一引用口径 | Codex |
| v1.1.808 | 2026-07-01 | 内部数据源 `source_types` 输入新增服务端保序去重规则，避免重复源导致响应摘要不稳定 | Codex |
| v1.1.807 | 2026-07-01 | 内部数据源读取解析按 `source_types` 裁剪残留 `source_filters`，连接测试预览和动作读取返回一致过滤摘要 | Codex |
| v1.1.806 | 2026-07-01 | 内部数据源按源过滤字段新增 `visible_when_source_types` 契约，前端按所选源数据联动展示并跳过隐藏字段提交 | Codex |
| v1.1.805 | 2026-07-01 | 内部数据源连接 schema 的源数据多选项和默认读取源顺序统一由服务端注册表生成，防止插件模板与读取层漂移 | Codex |
| v1.1.804 | 2026-07-01 | AI 助手和草案工作台用户侧统一把 `create_plugin_action` 展示为“动作”，保留“插件动作”作为兼容别名 | Codex |
| v1.1.803 | 2026-07-01 | 修正 AI 执行器官方连接默认值文档：默认使用系统模型网关 `executor_type=model_gateway`，本地 Runner 才选择 Codex/Claude/Hermes/OpenClaw | Codex |
| v1.1.802 | 2026-07-01 | 收口插件连接环境契约：环境为后台元数据和接口兼容筛选，插件管理页面不展示环境字段、筛选或环境列 | Codex |
| v1.1.801 | 2026-07-01 | 内部数据源官方连接 schema 新增按源过滤可视化字段，常用需求和 Bug 过滤写入 `source_filters`，高级 JSON 仅作补充 | Codex |
| v1.1.800 | 2026-07-01 | 内部数据源 detail 受保护字段补齐 `system.internal_data_source.detail` 权限种子、管理员授权和迁移说明 | Codex |
| v1.1.799 | 2026-07-01 | 内部数据源 read model 收口为注册表驱动，补充 summary/detail 字段白名单、字段权限、按源 `source_filters` 和返回 schemas 契约 | Codex |
| v1.1.798 | 2026-07-01 | AI 助手新增 `scheduled_job_run_business_draft` 确定性工具结果，可从运行记录生成 `create_analysis_draft` 洞察、需求和 Bug 草案 | Codex |
| v1.1.797 | 2026-07-01 | 定时作业运行详情“转业务草案”菜单支持按运行记录引用生成用户洞察、需求和 Bug 三类 AI 助手草案 | Codex |
| v1.1.796 | 2026-07-01 | 定时作业运行详情新增“转洞察草案”AI 助手深链，复用 `scheduled_job_run` 引用和预填 prompt 将运行结果转为可确认草案 | Codex |
| v1.1.795 | 2026-07-01 | 定时作业运行详情前端新增 JSON 导出契约，导出运行记录、展示标签、执行节点、结果写入记录和配置/插件/Skill/Prompt 快照，作为运行结果消费和排障归档入口 | Codex |
| v1.1.794 | 2026-07-01 | 插件管理新增官方内部数据源插件：协议 `internal_read_model`、动作类型 `internal_query`，连接可多选用户洞察、需求、产品和 Bug 等内部只读源数据，并补充内部业务定时作业模板 | Codex |
| v1.1.793 | 2026-07-01 | 插件管理连接环境弱化为后台元数据：连接弹窗不展示环境字段，连接列表不展示环境筛选或环境列，动作/试运行连接下拉只显示连接名称，API 仍保留环境用于审计、定时作业筛选和未来隔离 | Codex |
| v1.1.792 | 2026-07-01 | 真实全链路回归脚本 slug 生成统一使用微秒时间、进程号和进程内计数；权限可视化回归按本次唯一后缀筛选角色列表，避免组合套件复用秒级 fixture 目录或历史权限回归数据 | Codex |
| v1.1.791 | 2026-07-01 | 迭代版本总览新增后端 `release_readiness_checklist` 发布准备清单：需求、任务、分支、巡检、评审、Bug、知识、发布和状态推进九类准入项统一输出，并纳入前端与全链路回归 helper | Codex |
| v1.1.790 | 2026-07-01 | 定时作业主服务继续拆大文件：列表查询、运行记录查询和运行公开投影迁移到 `scheduled_job_read_models.py`，`scheduled_jobs.py` 预算收紧到 1900 行 | Codex |
| v1.1.789 | 2026-07-01 | AI 执行器 Runner 主服务继续拆大文件：任务产品 scope、上游定时作业/插件日志/AI任务上下文、运行节点投影和时间解析 helper 迁移到 `ai_executor_runner_task_context.py`，`ai_executor_runners.py` 预算收紧到 2050 行 | Codex |
| v1.1.788 | 2026-06-30 | 插件主服务继续拆大文件：动态请求配置解析、请求预览、HTTP/MCP 调用、AI 执行器 Runner 派发和系统默认模型网关执行器迁移到 `plugin_invocation_runtime.py`，`plugins.py` 预算收紧到 1800 行 | Codex |
| v1.1.787 | 2026-06-30 | 代码巡检服务继续拆大文件：列表分页、Dashboard 聚合、读模型 scope、趋势和分支/提交人治理投影迁移到 `code_inspection_read_models.py`，`code_inspections.py` 预算收紧到 1600 行 | Codex |
| v1.1.786 | 2026-06-30 | 迭代版本总览治理结论和交付阶段投影继续拆大文件：发布状态判断、治理结论和交付阶段总览迁移到 `product_version_delivery_overview.py`，`product_version_dashboard.py` 预算收紧到 1300 行 | Codex |
| v1.1.785 | 2026-06-30 | 迭代版本总览证据覆盖评分继续拆大文件：评分域、权限降级、覆盖分和摘要计算迁移到 `product_version_evidence_coverage.py`，`product_version_dashboard.py` 预算收紧到 1800 行 | Codex |
| v1.1.784 | 2026-06-30 | AI 动作草案预览校验继续拆大文件：通用预览差异、引用校验、权限校验、修复动作和 validation 状态计算迁移到 `assistant_action_draft_preview_helpers.py`，`assistant_action_drafts.py` 预算收紧到 2000 行 | Codex |
| v1.1.783 | 2026-06-30 | 定时作业引用校验继续拆大文件：AI Agent/Skill/模型网关、产品、插件动作/连接和多引用校验迁移到 `scheduled_job_ref_validation.py`，`scheduled_jobs.py` 预算收紧到 2200 行 | Codex |
| v1.1.782 | 2026-06-30 | AI 执行器 Runner 健康投影继续拆大文件：系统默认 Runner、公开投影、心跳健康状态、健康告警和启动命令迁移到 `ai_executor_runner_health.py`，`ai_executor_runners.py` 预算收紧到 2200 行 | Codex |
| v1.1.781 | 2026-06-30 | AI 动作草案治理投影继续拆大文件：风险、影响对象、权限校验、执行前后差异、失败重试、审计链路和确认决策迁移到 `assistant_action_draft_governance.py`，`assistant_action_drafts.py` 预算收紧到 2250 行 | Codex |
| v1.1.780 | 2026-06-30 | 代码巡检详情治理投影继续拆大文件：扫描覆盖摘要、规则/文件/提交人分布、Bug/整改覆盖率、待审批忽略和到期接受风险判断迁移到 `code_inspection_detail_projection.py`，`code_inspections.py` 预算收紧到 2400 行 | Codex |
| v1.1.779 | 2026-06-30 | 插件主服务继续拆大文件：MemoryStore 兼容、Repository 同步、通用校验、标准插件种子和脱敏合并 helper 迁移到 `plugin_store_helpers.py`，`plugins.py` 预算收紧到 2300 行 | Codex |
| v1.1.778 | 2026-06-30 | 结果写入记录分页查询改为 PostgreSQL 派生 read model：按定时作业运行和独立插件调用日志聚合写入记录，产品 scope、筛选、排序和分页下推数据库，避免执行诊断/运行详情拉全量内存再分页 | Codex |
| v1.1.777 | 2026-06-30 | AI 动作草案服务继续拆大文件：任务台行投影、风险/权限/审计/重试汇总迁移到 `assistant_action_draft_workbench.py`，主服务行数预算收紧到 2400 | Codex |
| v1.1.776 | 2026-06-30 | 定时作业服务继续拆大文件：用户反馈洞察提取、输出映射解析和反馈写回摘要迁移到 `scheduled_job_user_feedback.py`，主服务行数预算收紧到 2400 | Codex |
| v1.1.775 | 2026-06-30 | 真实全链路回归版本驾驶舱 helper 纳入 `evidence_coverage` 门禁：校验证据域顺序、状态、计数和覆盖分一致性 | Codex |
| v1.1.774 | 2026-06-30 | 迭代版本总览新增 `evidence_coverage` 证据覆盖评分：按需求、任务、分支、巡检、评审、Bug、知识、发布和状态推进输出覆盖/阻断/缺口摘要 | Codex |
| v1.1.773 | 2026-06-30 | 用户反馈原始列表补齐分页性能治理：`GET /api/insights/user-feedback` 带分页时走 count/page read model，支持摘要模式和查询性能观测，用户洞察聚合列表反馈摘要截断 | Codex |
| v1.1.772 | 2026-06-30 | 真实全链路回归脚本 AI 助手问答校验拆分：确定性助手、版本引用、`assistant.iteration`、版本总览投影和会话历史断言迁移到 `full_chain_regression_assistant_qa.py` | Codex |
| v1.1.771 | 2026-06-30 | 真实全链路回归脚本代码巡检治理校验拆分：本地完整扫描、质量门禁、Bug/整改任务写回、提交人治理、趋势对比和版本总览阻塞断言迁移到 `full_chain_regression_code_inspection.py` | Codex |
| v1.1.770 | 2026-06-30 | 真实全链路回归脚本权限可视化校验拆分：角色列表、权限矩阵、角色访问预览、范围名称和用户权限诊断断言迁移到 `full_chain_regression_permissions.py` | Codex |
| v1.1.769 | 2026-06-30 | 真实全链路回归脚本知识索引健康校验拆分：文档创建、索引健康、权限命中、失败重试和检索恢复断言迁移到 `full_chain_regression_knowledge.py` | Codex |
| v1.1.768 | 2026-06-30 | 真实全链路回归脚本 AI 动作草案治理校验拆分：确认、失败重试、列表 read model 和审计链路断言迁移到 `full_chain_regression_assistant_drafts.py` | Codex |
| v1.1.767 | 2026-06-30 | 迭代版本总览发布证据增强：summary 返回成功/失败发布计数，交付阶段发布证据卡展示最近一次发布状态和时间，真实全链路回归 helper 校验发布证据计数 | Codex |
| v1.1.766 | 2026-06-30 | 前端任务中心继续拆大文件：任务详情弹窗抽取为 `TaskDetailModal`，主页面只保留加载和开关编排，TaskCenter 页面预算收紧到 1800 行 | Codex |
| v1.1.765 | 2026-06-30 | 工程拆大文件守护补齐前端页面容器预算：TaskCenter、知识中心、角色、插件、迭代版本等高风险页面纳入行数门禁，新出现超过 900 行的页面必须登记预算或继续拆分 | Codex |
| v1.1.764 | 2026-06-30 | 真实全链路回归 `runner-reliability` 补齐 Runner 任务取消、人工重试、重试任务认领完成、重复重试拒绝和审计链路校验 | Codex |
| v1.1.763 | 2026-06-30 | 真实全链路回归 `version-dashboard` 快速场景补齐手工 blocker Bug 创建、版本总览 Bug 汇总、阻塞队列和下一步行动优先级校验 | Codex |
| v1.1.762 | 2026-06-30 | 真实全链路回归 `knowledge-index-health` 补齐索引失败、健康问题 retry 动作、重试恢复和恢复后检索命中校验 | Codex |
| v1.1.761 | 2026-06-30 | 真实全链路回归 `assistant-draft-governance` 补齐 AI 动作草案确认失败、失败原因投影、人工重试、修复后确认和审计链路校验 | Codex |
| v1.1.760 | 2026-06-30 | 真实全链路回归补齐 AI 助手 `status_impact` 投影一致性校验，确保助手即时回答和历史消息复用版本驾驶舱状态推进摘要 | Codex |
| v1.1.759 | 2026-06-30 | 真实全链路回归版本驾驶舱 helper 补齐 `status_impact` 结构校验，统一守护同步推进、阻塞和保持不变需求数据 | Codex |
| v1.1.758 | 2026-06-30 | 迭代版本总览新增状态推进影响预览：在明细表前集中展示同步推进、阻塞和保持不变需求，降低版本推进前跨表核对成本 | Codex |
| v1.1.757 | 2026-06-30 | AI 动作确认中心新增服务端统一确认决策：`governance.decision` 和列表行决策字段集中说明可确认、阻断、失败、过期和下一步动作 | Codex |
| v1.1.756 | 2026-06-30 | 迭代版本总览新增后端 `delivery_stage_overview`：版本页、AI 助手和回归脚本复用同一交付阶段总览 | Codex |
| v1.1.755 | 2026-06-30 | 真实全链路回归脚本版本驾驶舱校验逻辑拆分：阻塞项、下一步行动、治理结论和分支质量门禁迁移到 `full_chain_regression_version_dashboard.py` | Codex |
| v1.1.754 | 2026-06-30 | 迭代版本总览新增后端 `governance_conclusion`：版本页、AI 助手和回归脚本复用同一治理结论，前端仅保留旧响应兜底推导 | Codex |
| v1.1.753 | 2026-06-30 | 真实全链路回归脚本 Runner 可靠性逻辑拆分：健康告警、Token 轮换、租约重派、死信队列和日志校验迁移到 `full_chain_regression_runner.py` | Codex |
| v1.1.752 | 2026-06-30 | 真实全链路回归脚本 suite 元数据拆分：目标域、快速 suite 编排和 coverage 计算迁移到 `full_chain_regression_suites.py`，主脚本聚焦公开 API 执行编排 | Codex |
| v1.1.751 | 2026-06-30 | 真实全链路回归脚本新增 `assistant-qa` 快速套件：独立校验迭代版本治理问答走确定性助手、版本引用、`assistant.iteration`、下一步行动和会话历史，并纳入 `all-targeted` | Codex |
| v1.1.750 | 2026-06-30 | 真实全链路回归脚本新增 `all-targeted` 快速治理组合套件：串联 Runner、版本总览、草案治理、代码巡检治理、知识索引健康和权限可视化，并在覆盖矩阵中明确不是完整主链路 | Codex |
| v1.1.749 | 2026-06-30 | 真实全链路回归报告新增 suite 覆盖矩阵：JSON 输出声明覆盖/跳过的目标域，`full` 主链路补齐 AI 动作草案治理和权限可视化门禁，避免局部 suite 被误判为完整验收 | Codex |
| v1.1.748 | 2026-06-30 | AI 动作确认中心新增草案治理优先队列：基于 summary 和当前页草案聚合权限阻断、校验阻断、失败重试、高风险和审计缺口，直接给出处理建议与代表草案入口 | Codex |
| v1.1.747 | 2026-06-30 | 知识索引健康面板升级为三段治理摘要：集中展示解析状态、Chunk/Embedding、检索与权限，并在健康问题中明确补向量、重试索引、查看分块或导入任务动作 | Codex |
| v1.1.746 | 2026-06-30 | AI 助手迭代版本治理问答改为确定性意图：`assistant.iteration` 复用版本总览，返回阻塞数量、来源分布、前三个 next_actions 和状态推进影响，聊天历史保留安全摘要 | Codex |
| v1.1.745 | 2026-06-30 | 迭代版本总览新增后端 next_actions 投影：服务端统一阻塞排序并返回前三个版本治理建议和全链路主体，前端优先消费该字段 | Codex |
| v1.1.744 | 2026-06-30 | 系统角色详情接口新增 access_preview，集中返回可见菜单、操作权限、产品/知识空间范围名称和授权风险诊断，便于权限可视化复用 | Codex |
| v1.1.743 | 2026-06-30 | 真实全链路回归脚本新增 permission-visibility 快速场景，独立验收角色列表、权限矩阵、范围名称、菜单权限缺口和用户权限诊断 | Codex |
| v1.1.742 | 2026-06-30 | 真实全链路回归脚本新增 knowledge-index-health 快速场景，独立验收知识文档创建、索引健康、权限命中说明、检索模式和知识搜索命中 | Codex |
| v1.1.741 | 2026-06-30 | 真实全链路回归脚本新增 code-inspection-governance 快速场景，独立验收本地完整扫描、质量门禁、Bug/整改任务写回、提交人治理、趋势对比和版本总览阻塞 | Codex |
| v1.1.740 | 2026-06-30 | 迭代版本总览将待确认 Code Review 纳入发布阻塞处理队列，阻塞项可直接跳转评审处理和全链路上下文 | Codex |
| v1.1.739 | 2026-06-30 | 真实全链路回归脚本 `runner-reliability` 场景补齐 Runner `health_alert` 门禁，验证新 Runner 未连接告警和心跳恢复后告警清除 | Codex |
| v1.1.738 | 2026-06-30 | AI 执行器 Runner 公开投影新增 `health_alert`，列表可直接展示未连接、心跳超时、离线或停用原因和建议动作 | Codex |
| v1.1.737 | 2026-06-30 | AI 动作草案服务继续拆大文件：新增 `assistant_action_draft_common` 承接草案状态/动作枚举、默认 payload、基础校验和 Cron 表达式校验，`assistant_action_drafts.py` 聚焦草案确认、治理摘要、写入和审计编排 | Codex |
| v1.1.736 | 2026-06-30 | 代码巡检服务继续拆大文件：新增 `code_inspection_common` 承接巡检枚举、严重级别归一化、提交人摘要和结果动作校验，`code_inspections.py` 聚焦报告、治理和写回编排 | Codex |
| v1.1.735 | 2026-06-30 | 执行诊断问 AI 链路增加 `diagnostic_trace_id` 兜底：助手在 prompt 缺失时可按 Trace 详情重建链路或节点诊断问题 | Codex |
| v1.1.734 | 2026-06-30 | 迭代版本总览交付链路总览补齐各阶段直接处理入口：需求、任务、分支、巡检、评审、Bug、知识、发布和状态推进卡片可直接进入对应上下文 | Codex |
| v1.1.733 | 2026-06-30 | 代码巡检治理概览新增首屏治理结论：基于质量门禁、分支/提交人闭环、Bug/整改覆盖、待审批忽略和到期接受风险生成总体判断与下一步动作 | Codex |
| v1.1.732 | 2026-06-30 | 迭代版本总览首屏新增版本治理结论：基于阻塞项、质量门禁、Bug、分支治理、待确认评审、知识可检索和状态推进阻塞生成总体判断与下一步动作 | Codex |
| v1.1.731 | 2026-06-30 | 迭代版本总览顶部指标和交付健康摘要补齐分支质量治理信号：待治理分支、门禁失败、待审批忽略和到期接受风险可在首屏判断 | Codex |
| v1.1.730 | 2026-06-30 | 知识索引健康面板补齐文档状态分布和 Chunk/Embedding 覆盖率展示，帮助判断解析、分块和向量索引进展 | Codex |
| v1.1.729 | 2026-06-30 | 迭代版本总览分支质量治理补齐 finding 级 suppression 指标：版本 read model 拉取轻量巡检 finding，dashboard 聚合误报忽略、接受风险、过期接受风险、待审批忽略和活跃严重问题 | Codex |
| v1.1.728 | 2026-06-30 | 真实全链路回归脚本补齐代码巡检趋势对比门禁：完整链路同仓同分支二次扫描必须生成 `previous_comparison` 并指向前次报告 | Codex |
| v1.1.727 | 2026-06-30 | 真实全链路回归脚本补齐迭代版本总览分支质量治理门禁：`full` 校验待治理分支质量，`version-dashboard` 快速套件校验待巡检分支质量 | Codex |
| v1.1.726 | 2026-06-30 | 迭代版本总览补齐分支质量治理：dashboard 返回 `branch_quality_governance` 与 summary 分支治理计数，版本页集中展示分支巡检报告、严重问题、Bug/整改覆盖、质量门禁和最近报告 | Codex |
| v1.1.725 | 2026-06-30 | 代码巡检治理概览补齐分支治理待办：dashboard 返回 `branch_governance` 与治理压力分支计数，页面集中展示按分支闭环状态、门禁失败、Bug/整改覆盖和最近报告 | Codex |
| v1.1.724 | 2026-06-30 | AI 助手聊天服务继续拆大文件：新增 `assistant_chat_gateway` 承接模型网关配置选择、请求组装、取消中断、响应解析和模型日志，`assistant_chat.py` 聚焦聊天运行、确定性意图和记录持久化 | Codex |
| v1.1.723 | 2026-06-30 | AI 助手引用服务继续拆大文件：新增 `assistant_knowledge_references` 承接知识空间、目录、文档、chunk 候选、可读范围和模型注入上下文，`assistant_references.py` 聚焦引用编排、权限分发和动作配置 | Codex |
| v1.1.722 | 2026-06-30 | AI 助手聊天服务继续拆大文件：新增 `assistant_scheduled_job_run` 承接定时作业运行一次的显式提及解析、权限提示、草案兜底和运行结果投影，`assistant_chat.py` 聚焦聊天编排与模型调用 | Codex |
| v1.1.721 | 2026-06-30 | 插件服务继续拆大文件：新增 `plugin_projection` 承接插件版本元数据、公开投影和调用请求摘要脱敏，`plugins.py` 聚焦插件配置、连接、动作和调用编排 | Codex |
| v1.1.720 | 2026-06-30 | 定时作业服务继续拆大文件：新增 `scheduled_job_config` 承接调度时间、配置编排、多数据源引用、代码巡检仓库默认分支、数据连接策略和有效作业类型推导，`scheduled_jobs.py` 降至 2600 行预算安全区 | Codex |
| v1.1.719 | 2026-06-30 | 迭代版本总览 PostgreSQL 运行时切换为版本范围专用 read model，避免加载全量 task workflow source rows 后再服务层过滤 | Codex |
| v1.1.718 | 2026-06-30 | 迭代版本总览顶部新增优先处理建议：基于阻塞处理队列在下一步行动区展示前三个最高优先级阻塞及处理入口 | Codex |
| v1.1.717 | 2026-06-30 | 真实全链路回归脚本补齐代码巡检治理压力门禁：完整链路必须校验 `governance_pressure` 的闭环状态、质量门禁失败、严重问题和 Bug/整改任务覆盖 | Codex |
| v1.1.716 | 2026-06-30 | 代码巡检治理概览新增治理压力总览：dashboard 返回 `governance_pressure`，集中展示待闭环提交人、缺 Bug、缺整改任务、门禁失败、待审批忽略和到期接受风险 | Codex |
| v1.1.715 | 2026-06-30 | AI 动作确认中心补齐列表治理压力总览：草案任务台 summary 返回风险、权限和治理计数，前端顶部集中展示高风险、权限阻塞、校验阻塞、失败/重试和审计事件 | Codex |
| v1.1.714 | 2026-06-30 | AI 执行器 Runner 任务补齐人工重试：`cancelled/failed/timed_out/dead_letter` 任务可复制上下文重新入队，保留来源任务、重试原因和审计链路 | Codex |
| v1.1.713 | 2026-06-29 | 插件服务继续拆大文件：新增 `plugin_constants` 承接插件协议、分类、状态、认证类型、连接环境、调用状态和排序字段常量，`plugins.py` 聚焦插件、连接、动作和调用编排 | Codex |
| v1.1.712 | 2026-06-29 | AI 助手引用服务继续拆大文件：新增 `assistant_action_reference_defaults` 承接动作引用默认候选和配置常量，`assistant_references.py` 聚焦引用候选读取、权限过滤和配置读写 | Codex |
| v1.1.711 | 2026-06-29 | 迭代版本列表默认按创建时间倒序展示，并支持 `/delivery/versions?version_id=<id>&view=dashboard` 直达版本总览；原代码分支深链继续保持独立入口 | Codex |
| v1.1.710 | 2026-06-29 | 迭代版本总览知识沉淀升级为可用性健康视图：沉淀行展示索引状态、chunk/embedding 覆盖和关键词/混合/不可用检索模式，summary 补齐可检索与向量就绪沉淀数 | Codex |
| v1.1.709 | 2026-06-29 | 迭代版本总览补齐知识沉淀聚合：按版本内 AI 任务聚合知识沉淀候选，summary 展示沉淀数，明细按 `knowledge.read` 权限降级隐藏并提供来源任务和全链路入口 | Codex |
| v1.1.708 | 2026-06-29 | 真实全链路回归脚本的 `version-dashboard` 场景补齐 Code Review 门禁：通过本地 GitLab fixture MR 快照创建待确认代码评审报告，并校验版本总览报告数和待确认数 | Codex |
| v1.1.707 | 2026-06-29 | RBAC 权限范围预览补齐资源名称：权限矩阵和用户权限诊断中的产品、知识空间、全局 scope 返回可读名称，角色页展示名称、ID 与访问级别 | Codex |
| v1.1.706 | 2026-06-29 | 迭代版本总览补齐代码评审聚合：版本驾驶舱按版本内任务关联 Code Review 报告，集中展示报告数、待确认报告、风险、执行器和任务入口 | Codex |
| v1.1.705 | 2026-06-29 | 真实全链路回归脚本新增 `assistant-draft-governance` 场景集：通过公开 API 快速验收 AI 动作草案风险、影响、权限、差异、查看/修改/确认和审计链路 | Codex |
| v1.1.704 | 2026-06-29 | 真实全链路回归脚本补齐 AI 执行器 Runner Token 轮换门禁：`runner-reliability` 在租约/死信前先验证旧 Token 失效、新 Token 心跳可用和版本号递增 | Codex |
| v1.1.703 | 2026-06-29 | 真实全链路回归脚本新增 `version-dashboard` 场景集：通过公开 API 快速验收版本总览需求/任务/分支聚合、状态推进影响和发布/分支阻塞项 | Codex |
| v1.1.702 | 2026-06-29 | 真实全链路回归脚本支持场景集执行：默认 `full` 保持完整公开 API 主链路，`runner-reliability` 可单独验收 AI 执行器 Runner 租约、重派和死信门禁 | Codex |
| v1.1.701 | 2026-06-29 | AI 执行器 Runner 安装包补齐版本元数据：env、manifest、runner_config 和 README 均暴露安装包版本，便于 Runner 端兼容诊断和运维追踪 | Codex |
| v1.1.700 | 2026-06-29 | 真实全链路回归脚本补齐 AI 执行器 Runner 可靠性门禁：脚本通过公开 API 验证短租约任务认领、租约过期重派、超过最大重派后进入死信队列和日志可追踪 | Codex |
| v1.1.699 | 2026-06-29 | 真实全链路回归脚本补齐版本总览阻塞项处理队列门禁：所有 blockers 必须携带来源、级别、标题、原因、动作目标和解除条件，避免队列无法排序或无法跳转处理 | Codex |
| v1.1.698 | 2026-06-29 | 迭代版本总览阻塞项升级为处理队列：按严重级别和来源类型排序展示发布准入风险、解除条件和处理入口，帮助用户优先处理版本推进阻塞 | Codex |
| v1.1.697 | 2026-06-29 | 迭代版本总览新增发布准备清单：在明细表前聚合需求范围、研发任务、代码分支、代码巡检、Bug 收敛、发布证据和状态推进影响，降低版本推进前跨表拼上下文成本 | Codex |
| v1.1.696 | 2026-06-29 | 定时作业服务继续拆大文件：新增 `scheduled_job_constants` 承接运行状态、排序字段和默认编排策略常量，给 `scheduled_jobs.py` 2600 行预算留出余量 | Codex |
| v1.1.695 | 2026-06-29 | PostgreSQL 旧库兼容迁移补齐代码巡检风险接受到期字段：启动兼容迁移纳入 `073_code_inspection_risk_acceptance_expiry.sql`，避免全链路代码巡检写入 finding 时缺少 `suppression_owner` | Codex |
| v1.1.694 | 2026-06-29 | 真实全链路回归脚本补齐版本总览发布证据门禁：脚本将版本推进到测试中后校验缺少成功发布记录时必须返回可跳转的发布阻塞项 | Codex |
| v1.1.693 | 2026-06-29 | 版本总览发布准入增强：测试中版本推进到已发布时若缺少成功发布记录，驾驶舱返回可处理的发布阻塞项并跳转到按版本筛选的发布记录 | Codex |
| v1.1.692 | 2026-06-29 | 定时作业服务继续拆大文件：新增 `scheduled_job_access` 承接权限/产品范围 helper，新增 `scheduled_job_runtime` 承接时区、动态输入映射和异常摘要，`scheduled_jobs.py` 架构守护预算收紧到 2600 行 | Codex |
| v1.1.691 | 2026-06-29 | 插件服务继续拆大文件：新增 `plugin_connection_config` 承接 GitHub/GitLab 连接地址解析、请求配置规范化和 GitHub 认证校验，`plugins.py` 架构守护预算收紧到 2600 行 | Codex |
| v1.1.690 | 2026-06-29 | 前端系统管理 client 继续拆分：新增 `systemManagementClient` 承接用户、角色、菜单和权限诊断 API，`aiBrain.ts` 保持兼容导出并将前端服务 barrel 行数预算收紧到 2400 | Codex |
| v1.1.689 | 2026-06-29 | 知识索引健康中心补齐权限命中说明：`GET /api/knowledge/index-health` 返回 `permission_scope`，前端展示角色命中文档数、全局知识权限和知识空间 scope | Codex |
| v1.1.688 | 2026-06-29 | 授权仓储继续拆大文件：默认菜单、角色菜单授权、scope 白名单和排序字段抽取到 `authorization_defaults`，`authorization.py` 纳入 2800 行架构守护 | Codex |
| v1.1.687 | 2026-06-29 | AI 执行器 Runner 服务继续拆大文件：常量抽取到 `ai_executor_runner_constants`，安装包构造抽取到 `ai_executor_runner_packages`，`ai_executor_runners.py` 纳入 2800 行架构守护 | Codex |
| v1.1.686 | 2026-06-29 | 代码巡检风险接受补齐责任人与到期治理：`accepted_risk` 申请必须携带到期时间，finding 持久化责任人和到期时间，详情页提供独立接受风险入口，过期接受风险重新进入报告详情和提交人治理待办 | Codex |
| v1.1.685 | 2026-06-29 | 工程拆大文件增加行数守护门禁：对 `scheduled_jobs.py`、`plugins.py`、`assistant_references.py`、`assistant_chat.py` 和 `services/aiBrain.ts` 固化 2800 行预算，防止领域入口文件重新膨胀 | Codex |
| v1.1.684 | 2026-06-29 | 真实全链路回归脚本补齐代码巡检提交人治理待办校验：同产品同仓库 dashboard 必须返回提交人闭环状态、活跃严重问题、Bug 覆盖和整改任务覆盖 | Codex |
| v1.1.683 | 2026-06-29 | 代码巡检治理概览新增提交人治理待办：按提交人聚合活跃严重问题、未关联 Bug、未派生整改任务、待审批忽略和已接受风险，便于从风险排行进入责任人闭环 | Codex |
| v1.1.682 | 2026-06-29 | 角色管理详情补齐单角色访问预览：在角色详情中集中展示可见菜单路径、操作权限名称、产品/知识空间/全局数据范围和高风险/菜单权限缺口，提升权限可视化可用性 | Codex |
| v1.1.681 | 2026-06-29 | 真实全链路回归脚本补齐代码巡检质量门禁硬校验：本地完整扫描必须触发并持久化质量门禁失败，治理概览聚合失败原因，版本总览阻塞项必须体现质量门禁风险 | Codex |
| v1.1.680 | 2026-06-29 | AI 动作确认中心详情治理面板组件化：草案详情统一展示风险原因、影响/来源对象、权限必需/缺失/问题、字段差异、审计事件和失败重试状态，降低确认高影响动作前的信息遗漏风险 | Codex |
| v1.1.679 | 2026-06-29 | 知识中心索引健康前端组件化：健康摘要、问题动作和 chunk/Embedding/召回模式信号由 `KnowledgeIndexHealthPanel` 承载，知识中心主页面保留列表、弹窗和导入编排 | Codex |
| v1.1.678 | 2026-06-29 | 版本总览前端组件继续细分：`VersionDashboardModal` 只负责弹窗编排，摘要行动区、明细表和纯数据 helper 分别下沉到 `VersionDashboardSummary`、`VersionDashboardTables` 和 `versionDashboardModel`，降低版本驾驶舱后续演进风险 | Codex |
| v1.1.677 | 2026-06-29 | 前端迭代版本页继续拆大文件：版本总览弹窗抽取为 `VersionDashboardModal`，主页面保留版本列表、分支配置和状态推进编排，版本健康、阻塞治理、状态分布和明细表展示由独立组件承载 | Codex |
| v1.1.676 | 2026-06-29 | 前端系统运维与研发运营 client 继续拆分：新增 `systemOperationsClient` 承接 AI Skill/Agent、定时作业、插件、AI 执行器和研发执行器策略 API，新增 `devopsOperationsClient` 承接日志监控、采集运行和待归属数据 API，`services/aiBrain.ts` 保持兼容导出并降至 2800 行以内 | Codex |
| v1.1.675 | 2026-06-29 | 定时作业服务 AI 处理链路拆分：知识文档引用校验、Skill 输出契约校验、AI prompts 组装、模型网关 JSON 调用和模型调用审计抽取到 `scheduled_job_ai_processing`，`scheduled_jobs.py` 降至 2800 行以内并继续聚焦作业配置、执行和运行状态落库 | Codex |
| v1.1.674 | 2026-06-29 | 定时作业服务继续拆分：通用校验抽取到 `scheduled_job_common`，仓储同步/MemoryStore 兼容 helper 抽取到 `scheduled_job_store`，AI Skill/Agent 配置 CRUD 与活跃依赖校验抽取到 `scheduled_job_ai_capabilities`，`scheduled_jobs.py` 聚焦作业配置、执行和运行记录编排 | Codex |
| v1.1.673 | 2026-06-29 | AI 助手引用服务继续拆分：引用类型元数据、来源模块、URL/标题/摘要格式化、候选合并、语义匹配和权限标签抽取到 `assistant_reference_formatting`，`assistant_references.py` 聚焦候选读取、权限过滤和配置写接口 | Codex |
| v1.1.672 | 2026-06-29 | AI 助手聊天服务继续拆分：确定性意图 detector、任务向导/诊断/指标静态输出和引用合并 helper 抽取到 `assistant_chat_intents`，`assistant_chat.py` 保留聊天运行、模型调用、草案和定时作业执行编排 | Codex |
| v1.1.671 | 2026-06-29 | 插件管理服务继续拆分：结果映射/写入预览抽取到 `plugin_result_mapping`，结果写入记录构造、分页和产品 scope 过滤抽取到 `plugin_result_write_records`，`plugins.py` 降低为插件配置、调用和兼容入口 | Codex |
| v1.1.670 | 2026-06-29 | 插件管理服务继续拆分：插件/连接/动作删除保护抽取到 `plugin_delete_protection`，删除前统一识别定时作业单 ID、多 ID 和 orchestration 多引用，避免多数据源作业仍引用资源时误删 | Codex |
| v1.1.669 | 2026-06-29 | 定时作业服务继续拆分：本地代码巡检多仓库扫描摘要、queued native scan 摘要和仓库 ID 去重抽取到 `scheduled_job_native_scan`，主执行服务仅保留运行编排和仓库 read model 兼容封装 | Codex |
| v1.1.668 | 2026-06-29 | 定时作业服务继续拆分：多连接/多动作引用解析抽取到 `scheduled_job_refs`，作业与运行审计 payload 抽取到 `scheduled_job_audit`，降低运行可靠性改造对主执行服务的影响面 | Codex |
| v1.1.667 | 2026-06-29 | 定时作业服务拆分：运行记录对外投影、trace graph 补齐和 rerun 来源摘要抽取到 `scheduled_job_run_projection`，降低 `scheduled_jobs.py` 主执行服务职责 | Codex |
| v1.1.666 | 2026-06-29 | 真实全链路回归脚本补齐版本总览阻塞项治理动作验收：阻塞项必须包含动作标签、目标主体和解除条件，并覆盖代码巡检报告与派生 Bug 处理入口 | Codex |
| v1.1.665 | 2026-06-29 | 迭代版本总览阻塞项新增治理动作：后端 blockers 返回处理动作、目标主体和解除条件，前端可直接跳转需求、Bug、代码巡检、分支或发布记录处理入口 | Codex |
| v1.1.664 | 2026-06-29 | 代码巡检报告快照补齐增量扫描上下文：持久化 `incremental_from_commit` 和 `incremental_file_count`，详情页展示全量/增量扫描范围、增量基线 Commit 和增量文件数 | Codex |
| v1.1.663 | 2026-06-29 | 真实全链路回归脚本补齐知识索引健康和检索验收：知识沉淀采纳后需验证 `index-health` 可见可检索文档、chunk 和召回模式，并通过知识检索命中沉淀文档 | Codex |
| v1.1.662 | 2026-06-29 | 知识中心索引健康升级为后端聚合中心：新增 `GET /api/knowledge/index-health`，按当前用户知识权限和筛选条件在 PostgreSQL read model 聚合全量文档、chunk、embedding、导入任务和可操作问题，前端不再只基于当前分页结果推断健康度 | Codex |
| v1.1.661 | 2026-06-28 | 真实全链路回归脚本验收强度增强：在原公开 API 主链路基础上，新增代码巡检 finding/提交人/治理覆盖率、Bug/整改任务回写、版本驾驶舱状态分布、full-chain 主体解析、团队看板计数和 AI 助手会话历史引用的硬校验；版本驾驶舱补齐同版本巡检报告派生 Bug 聚合 | Codex |
| v1.1.660 | 2026-06-28 | 迭代版本驾驶舱总览增强：弹窗集中展示需求/任务/Bug 状态分布和版本推进影响明细，用户可直接识别同步推进、阻塞和保持不变的需求，减少跨页面拼接版本健康上下文 | Codex |
| v1.1.659 | 2026-06-28 | AI 执行器 Runner 任务补齐租约重派和死信队列：任务认领写入租约过期时间，日志追加刷新租约，超时扫描优先将租约过期任务按 `max_reclaim_count` 重派或置为 `dead_letter`，并同步上游定时作业和研发任务失败态 | Codex |
| v1.1.658 | 2026-06-28 | 角色管理新增权限与范围预览：复用 RBAC 策略矩阵在列表前展示全局/产品范围覆盖、未配置范围、高风险角色和菜单权限缺口，并在角色列表与详情中展示 scope 授权，便于权限分配前快速排查风险 | Codex |
| v1.1.657 | 2026-06-28 | 知识中心新增索引健康视图：基于后端权限过滤后的筛选范围聚合可检索、向量就绪、关键词兜底、索引失败、处理中和分块版本状态，暴露索引失败重试、向量补建、导入任务和分块查看入口，帮助在 Embedding 可选/降级场景下识别知识检索健康度 | Codex |
| v1.1.656 | 2026-06-28 | 代码巡检报告详情新增治理闭环摘要：详情响应返回 `governance_summary`，按严重 finding 计算 Bug 覆盖、整改任务覆盖、待审批忽略、已接受风险和治理待办；详情页展示闭环状态并在 finding 列表暴露整改任务链接 | Codex |
| v1.1.655 | 2026-06-28 | AI 动作确认中心增强治理摘要：草案详情和任务台统一展示风险等级、影响对象、权限校验、执行前后差异、失败重试和审计链路；`public_assistant_action_draft.governance` 由草案、预检、动作运行和审计事件派生，确认前帮助用户判断写入影响 | Codex |
| v1.1.654 | 2026-06-28 | 固化真实全链路回归脚本：通过公开 API 串联用户反馈、需求、迭代版本、AI 任务、Review、知识沉淀、版本分支、代码巡检、Bug/整改任务、版本驾驶舱、full-chain、团队看板和 AI 助手引用；AI 任务启动新增管理员显式 `deterministic` 验收模式并记录审计，可跳过研发执行器策略和模型网关，生产默认仍走模型网关或研发执行器策略 | Codex |
| v1.1.653 | 2026-06-28 | 需求交付新增迭代版本驾驶舱：按版本聚合需求、AI 任务、版本代码分支、Bug、代码巡检、发布记录、状态推进影响和阻塞项，读接口按 `product.read` 与产品 scope 校验，Bug/代码巡检明细按子权限降级隐藏 | Codex |
| v1.1.652 | 2026-06-28 | AI 助手失败草案补齐重试治理：failed 草案可通过 retry 重新打开为 pending，保留失败历史、清空失败 run 绑定、记录重试审计，重新确认前不写入业务配置 | Codex |
| v1.1.651 | 2026-06-28 | 模型网关配置列表生产查询路径收口：`GET /api/system/model-gateway-configs?page=...` 必须优先走模型网关配置 count/page read model，按配置名、Provider、状态、默认配置、Chat/Embedding 模型和 Embedding 连接模式在数据库侧筛选排序 | Codex |
| v1.1.650 | 2026-06-28 | 模型调用日志补齐服务端分页、筛选、排序和性能观测：`GET /api/model-gateway/logs` 支持 `page/page_size`、AI 任务、用途、状态和排序白名单，模型网关页“最近模型调用日志”默认请求远程分页结果并展示查询耗时 | Codex |
| v1.1.649 | 2026-06-28 | AI 助手角色快捷任务配置列表补齐服务端分页、筛选、排序和性能观测：`GET /api/assistant/role-quick-task-configs` 支持 `page/page_size`、关键字、任务/分组启停状态、角色、权限、企业、草案模板、模板版本和排序白名单，系统管理页默认请求远程分页结果 | Codex |
| v1.1.648 | 2026-06-28 | 任务中心待确认 Review 子列表补齐服务端分页、排序、按 AI 任务筛选和查询性能观测：`GET /api/reviews/pending` 支持 `ai_task_id/page/page_size/sort_by/sort_order`，PostgreSQL 运行态优先调用 count/page read model，前端从任务操作进入确认弹窗时不再拉全量后本地过滤 | Codex |
| v1.1.647 | 2026-06-28 | P0 路由-权限点-数据范围契约矩阵补齐：需求、Bug、知识文档、代码巡检、定时作业、插件配置/调用日志和 AI 执行器 Runner/任务必须由后端校验权限点，产品或知识空间 scope 外数据不得返回；`test_security_boundaries.py` 覆盖 OpenAPI 路由存在、无权限 403 和 scope 过滤 | Codex |
| v1.1.646 | 2026-06-28 | 统一需求全链路工作台补齐版本代码分支入口：`product_version_branch_config` / `branch_config` 可解析回版本需求链路，迭代版本分支列表和 AI 助手引用提供“全链路”深链并继续按产品 scope 校验 | Codex |
| v1.1.645 | 2026-06-28 | 统一需求全链路工作台补齐执行诊断证据展示：full-chain payload 纳入脱敏 `execution_traces`、阶段摘要和时间线，前端可从链路明细下钻到执行诊断中心 | Codex |
| v1.1.644 | 2026-06-28 | 结果写入记录排障 API 补齐可选分页、白名单排序和性能观测，带 `page/page_size` 时返回统一列表元数据 | Codex |
| v1.1.643 | 2026-06-28 | 结果写入记录排障 API 补齐产品 scope：通用写入记录读模型通过 `scheduled_job_id` 或 `scheduled_job_run_id` 解析产品后过滤，scope 外记录不返回 | Codex |
| v1.1.642 | 2026-06-28 | 插件调用日志排障兼容 API 补齐产品 scope：列表通过 `scheduled_job_id` 或 `scheduled_job_run_id` 解析产品后过滤，PostgreSQL count/page read model 下推 `product_scope_ids`，兼容全量路径同样过滤 scope 外日志 | Codex |
| v1.1.641 | 2026-06-28 | 统一需求全链路工作台补齐执行诊断入口：`/api/lifecycle/full-chain` 支持从 `scheduled_job_run`、`plugin_invocation_log`、`ai_executor_task`、`model_gateway_log`、`execution_trace` 等 Trace 主体解析回需求链路，执行诊断详情同步提供“全链路”入口并继续按产品 scope 校验 | Codex |
| v1.1.640 | 2026-06-28 | 系统管理接口从固定 admin 角色收口到权限点：用户管理校验 `system.users.manage`，模型网关配置与日志校验 `system.model_gateway.manage`，审计事件查询校验 `audit.read`，支持自定义治理角色访问对应页面 | Codex |
| v1.1.639 | 2026-06-28 | AI 助手草案任务台 read model 补齐 `validation_status` 下推：当前用户草案按动作、状态、校验状态、时间、关键词、排序和分页在数据库侧完成，避免校验筛选退回全量草案读取 | Codex |
| v1.1.638 | 2026-06-28 | 产品主体、迭代版本和版本分支配置接口从固定角色名收口到 `product.read` / `product.manage` 权限点；列表按产品 scope 过滤，单资源按归属产品校验并对 scope 外资源返回 404，产品与版本 SQL read model 下推 `product_scope_ids` | Codex |
| v1.1.637 | 2026-06-28 | 产品模块配置接口从固定角色名收口到 `product.read` / `product.manage` 权限点，并按当前用户产品 scope 校验列表、创建、更新和删除，scope 外资源按 404 隐藏 | Codex |
| v1.1.636 | 2026-06-28 | 相关系统配置接口从固定角色名收口到 `product.read` / `product.manage` 权限点，列表、创建、更新、删除按当前用户产品 scope 过滤或校验，scope 外产品和资源按 404 隐藏 | Codex |
| v1.1.635 | 2026-06-28 | 产品 Git 仓库配置接口从固定角色名收口到 `product.read` / `product.manage` 权限点，并按当前用户产品 scope 校验列表、创建、更新和删除，scope 外资源按 404 隐藏 | Codex |
| v1.1.634 | 2026-06-28 | AI 执行器任务管理补齐产品 scope：任务列表、日志查询、取消和超时扫描必须通过定时作业、运行快照或研发任务解析产品归属，受限用户不得查看或操作 scope 外 Runner 任务 | Codex |
| v1.1.633 | 2026-06-28 | 知识沉淀候选审核权限从固定角色名收口到 `knowledge.deposit.decide` 权限点，支持自定义审核角色并阻止仅具备 `knowledge.read` 的只读用户访问审核列表或执行采纳/驳回 | Codex |
| v1.1.632 | 2026-06-28 | 角色治理列表生产查询路径收口：`GET /api/system/roles` 在 PostgreSQL 运行时必须优先走 `count_role_summaries` / `list_role_summaries_page` read model，不得先全量 `list_roles()` 后在接口层过滤分页 | Codex |
| v1.1.631 | 2026-06-28 | 知识沉淀候选列表补齐服务端分页、筛选、排序和性能观测契约：`GET /api/knowledge/deposits` 传入 `page/page_size` 时必须优先走 PostgreSQL read model 的 count/page 查询，支持按状态过滤和白名单排序 | Codex |
| v1.1.630 | 2026-06-28 | 插件调用日志排障兼容 API 补齐服务端分页、筛选、排序和性能观测契约：`GET /api/system/plugin-invocation-logs` 传入 `page/page_size` 时必须优先走 PostgreSQL read model 的 count/page 查询，支持按动作、定时作业、运行实例和状态过滤 | Codex |
| v1.1.629 | 2026-06-28 | AI 执行器任务列表补齐服务端分页、筛选、排序和性能观测契约：`GET /api/system/ai-executor-tasks` 传入 `page/page_size` 时必须优先走 PostgreSQL read model 的 count/page 查询，支持按研发任务、Runner、定时作业运行和状态过滤 | Codex |
| v1.1.628 | 2026-06-28 | 定时作业运行观测权限与产品范围收口：`GET /api/system/scheduled-job-runs/observability` 允许具备 `system.scheduled_jobs.manage` 或 `system.scheduled_jobs.run` 的用户访问，所有健康汇总、失败分布、最近失败和慢运行必须按当前用户产品 scope 过滤 | Codex |
| v1.1.627 | 2026-06-27 | 统一需求全链路工作台补齐入口主体提示：从 Bug、迭代版本、代码巡检、AI 助手等主体进入 `/delivery/full-chain` 时，页面展示入口主体和已解析需求 ID，避免跨页面跳转后丢失上下文 | Codex |
| v1.1.626 | 2026-06-27 | 核心管理列表权限与产品范围收口：需求、Bug、知识文档和代码巡检列表必须校验菜单声明的 read 权限，需求/Bug/代码巡检在服务端按当前用户产品 scope 过滤并下推到 PostgreSQL read model | Codex |
| v1.1.625 | 2026-06-27 | 执行诊断“问 AI 分析链路”深链增加同标签页待带入 prompt 兜底：详情页点击时写入短期 sessionStorage，上游 URL prompt 被浏览器、路由或复制过程截断时，助手页仍可恢复诊断问题并继续解析 `reference_type/reference_id` 上下文 | Codex |
| v1.1.624 | 2026-06-27 | AI 助手裸 `@` 默认引用候选顺序恢复常用对象优先：知识/需求/研发任务/作业/插件/AI 角色与 Skill 不被执行诊断来源挤出首屏，执行诊断来源仍保留权限校验后的可引用能力 | Codex |
| v1.1.623 | 2026-06-27 | 知识中心知识文档主列表收口到 PostgreSQL read model：带分页参数时在数据库侧完成权限过滤、关键字、知识空间、目录、类型、索引状态、权限角色筛选和白名单排序，旧全量返回仅保留兼容用途 | Codex |
| v1.1.622 | 2026-06-27 | AI 能力配置的 AI角色与 Skill 主表接入服务端分页、筛选和排序：页面默认请求 `/api/system/ai-agents?page=1&page_size=10&sort_by=code&sort_order=asc` 与 `/api/system/ai-skills?page=1&page_size=10&sort_by=code&sort_order=asc`，旧全量返回仅保留兼容下拉和测试 helper 用途 | Codex |
| v1.1.621 | 2026-06-27 | 定时作业配置和运行记录主表统一接入服务端分页、排序和产品 scope 过滤：作业配置默认请求 `/api/system/scheduled-jobs?page=1&page_size=10&sort_by=next_run_at&sort_order=desc`，运行记录默认请求 `/api/system/scheduled-job-runs?page=1&page_size=10&sort_by=started_at&sort_order=desc`，旧全量返回仅保留兼容用途 | Codex |
| v1.1.620 | 2026-06-27 | 插件管理连接和动作主表接入服务端分页、排序和筛选：连接页签默认携带分页/排序和环境筛选请求 `/api/system/plugin-connections`，动作页签默认携带分页/排序请求 `/api/system/plugin-actions`，旧全量接口仅保留下拉和测试兼容用途 | Codex |
| v1.1.619 | 2026-06-27 | 执行诊断到 AI 助手深链补齐上下文解析：`assistant_chat_run`、`model_gateway_log`、`plugin_invocation_log`、`ai_executor_task`、`ai_executor_runner`、`code_inspection_report`、`audit_event` 等执行诊断来源可作为助手引用候选，`/assistant?reference_type=&reference_id=&prompt=` 会带入 prompt 和本次上下文，并继续受执行诊断读权限控制 | Codex |
| v1.1.618 | 2026-06-27 | AI 助手草案任务台列表收口到 PostgreSQL read model：当前用户草案按动作、状态、时间、关键词、排序和分页在数据库侧完成，返回状态/采纳/处理/修改率汇总与列表性能观测；实时预检校验状态筛选保留兼容路径 | Codex |
| v1.1.617 | 2026-06-27 | 受控运维接口权限边界收紧：定时作业列表/运行按专项权限和产品 scope 服务端过滤，运行健康概览要求管理权限；插件列表、连接、动作、调用日志和 AI 执行器管理统一要求插件管理权限 | Codex |
| v1.1.616 | 2026-06-27 | 知识中心沉淀审核列表补齐统一全链路入口，待审核知识沉淀可直接按 `knowledge_deposit` 主体进入需求交付链路，审核弹窗表格固定列宽与横向滚动 | Codex |
| v1.1.616 | 2026-07-01 | 定时作业配置列表移除“模板来源”列，模板来源继续保留在复制确认、运行详情和审计 payload 中 | Codex |
| v1.1.615 | 2026-06-27 | AI 助手引用补齐统一全链路入口，需求、迭代版本、研发任务、Review、代码评审、Bug、代码巡检、知识沉淀和审计事件等可解析主体可直接进入需求交付链路；`iteration_version` 兼容映射到版本主体解析 | Codex |
| v1.1.614 | 2026-06-27 | 需求全链路聚合补齐版本级代码分支配置和脱敏审计事件，阶段进度、阶段明细、导出报告和时间线统一展示 | Codex |
| v1.1.613 | 2026-06-27 | 研发执行器策略列表改为服务端分页、筛选、排序和查询性能观测；需求全链路入口补齐读权限和产品 scope 校验 | Codex |
| v1.1.612 | 2026-06-27 | 需求全链路补齐统一主体入口：`/api/lifecycle/full-chain` 支持从 Bug、迭代版本和代码巡检报告解析回需求链路，链路摘要纳入代码巡检报告 | Codex |
| v1.1.611 | 2026-06-27 | 执行诊断列表性能优化：普通列表默认复用已有 PostgreSQL 快照，页面刷新或 `refresh=true` 才同步重建快照，source_id 深链未命中和详情未命中继续强制刷新 | Codex |
| v1.1.610 | 2026-06-26 | 代码巡检治理概览补充质量门禁失败原因分布，按指标/规则聚合触发次数、影响报告数、实际值/阈值和最近报告摘要 | Codex |
| v1.1.609 | 2026-06-26 | 执行诊断详情补齐整条链路诊断包：失败/运行中链路和成功链路均可生成脱敏摘要，支持复制并按根对象带入 AI 助手分析整条链路 | Codex |
| v1.1.608 | 2026-06-26 | 定时作业前端继续拆深：作业、运行、模板、插件资源、产品、AI 资源、知识文档、模型网关和作业 catalog 的工作台数据加载收口到 `useScheduledJobWorkspaceData`，主页面继续聚焦表单联动和运行编排 | Codex |
| v1.1.607 | 2026-06-26 | 定时作业前端继续拆深：运行详情打开、路由深链、结果写入记录加载和运行标签计算收口到 `useScheduledJobRunDetailState`，主页面只保留作业列表、表单和运行触发编排 | Codex |
| v1.1.606 | 2026-06-26 | 插件管理前端继续拆深：Runner 新增/编辑、安装包、测试诊断、Token 轮换、日志查看和取消任务操作收口到 `usePluginRunnerOperations`，主页面只装配插件、连接、动作和 Runner 工作台 | Codex |
| v1.1.605 | 2026-06-26 | 代码巡检前端继续拆深：治理概览统计与通用展示 helper 从主页面抽到独立组件，主页面保留查询、详情弹窗和治理操作编排 | Codex |
| v1.1.605 | 2026-07-01 | 插件管理页首屏体验收敛：移除常驻“系统变量预览”和“通用调用链路”说明，页面直接展示插件、连接、执行器和动作配置；系统变量插入继续保留在连接/动作参数表单，变量解析详情通过连接测试诊断查看，任务链路说明回到定时作业配置和运行详情 | Codex |
| v1.1.604 | 2026-06-26 | 执行诊断列表直接展示 `diagnostic_nodes` 首个异常/运行中节点摘要，让失败链路在列表层即可识别优先排查对象 | Codex |
| v1.1.603 | 2026-06-26 | 定时作业前端继续拆深：新增/编辑弹窗的执行链路节点构建抽到 `scheduledJobOrchestrationNodeBuilder`，主页面只传入表单状态和事件回调 | Codex |
| v1.1.602 | 2026-06-26 | 插件管理删除保护补齐多连接/多动作定时作业引用：删除插件、连接或动作前同时检查单值兼容字段和 `plugin_connection_ids` / `plugin_action_ids` 数组字段 | Codex |
| v1.1.601 | 2026-06-26 | 执行诊断列表与详情补充派生 `diagnostic_nodes`，返回失败、取消、运行中或排队节点的轻量摘要，供前端和 AI 助手统一诊断且不暴露节点 metadata | Codex |
| v1.1.600 | 2026-06-26 | 系统菜单治理补充静态路由一致性门禁：active 的可导航菜单 path 必须在前端 routes.ts 中注册，关键菜单路径不得漂移到旧入口 | Codex |
| v1.1.599 | 2026-06-26 | 执行诊断筛选文案从“根类型”调整为“来源类型”，明确 `source_type` 可定位根节点或任一执行节点，避免把节点类型误解为 root_type | Codex |
| v1.1.598 | 2026-06-26 | 执行诊断深链契约继续收紧：可复用 `ExecutionTraceLink` 增加组件级验收，缺少 `source_type` 时不生成歧义链接；API 与验收示例统一为 `source_id + source_type` | Codex |
| v1.1.597 | 2026-06-26 | 执行诊断入口继续统一：详情页关联对象、失败/运行中节点和节点表来源 ID 深链补齐 `source_type`，避免仅按 ID 下钻造成跨来源歧义 | Codex |
| v1.1.596 | 2026-06-26 | 管理列表体验继续统一：产品/迭代版本上下文选项改为分页拉全，避免需求、Bug、任务和洞察表单只取前 100 条导致产品或目标版本不可选 | Codex |
| v1.1.595 | 2026-06-26 | 管理列表体验继续统一：AI 助手运行状态检测时间改为统一展示时区格式，避免浏览器本地短时间格式造成时间差异 | Codex |
| v1.1.594 | 2026-06-26 | 执行诊断入口继续统一：审计列表按 `audit_event` 来源 ID 提供统一执行诊断深链，保留原生命周期链路追踪入口 | Codex |
| v1.1.593 | 2026-06-26 | 执行诊断入口继续统一：AI 助手运行状态最近失败和运行诊断卡片中的模型/插件日志 ID 提供统一执行诊断深链 | Codex |
| v1.1.592 | 2026-06-26 | 执行诊断入口继续统一：模型网关配置页展示最近模型调用日志，并按 `model_gateway_log` 来源 ID 提供统一执行诊断深链 | Codex |
| v1.1.591 | 2026-06-26 | 执行诊断入口继续统一：插件管理 Runner 执行日志弹窗提供任务诊断、Runner 诊断和来源运行诊断深链，按 `ai_executor_task`、`ai_executor_runner` 和 `scheduled_job_run` 来源 ID 跳转统一执行诊断中心 | Codex |
| v1.1.590 | 2026-06-26 | 管理列表性能观测继续统一：产品、迭代版本、知识、审计、模型网关、执行诊断、日志监控、用户和 AI 助手草案任务台透传远程分页 `performance` 元数据，统一列表工具栏展示查询耗时并复用慢查询提示 | Codex |
| v1.1.589 | 2026-06-26 | 管理列表体验统一：核心远程分页列表承接服务端 `performance` 元数据，需求、任务、Bug、用户洞察、代码巡检和角色列表工具栏展示查询耗时，慢查询统一显示阈值提示并指引结合 trace、筛选条件和数据库慢查询日志排查 | Codex |
| v1.1.588 | 2026-06-26 | AI 助手草案卡片继续组件化：助手页草案详情弹窗收口到 `AssistantDraftDetailModal`，Payload、对比来源、字段差异和校验问题展示独立于草案卡主体 | Codex |
| v1.1.587 | 2026-06-26 | AI 助手草案卡片继续组件化：应用前预检、字段差异、校验问题和修复动作入口收口到 `AssistantDraftPreviewBlock` 与 `assistantDraftPreviewHelpers`，草案卡主体继续保留确认、取消、详情和资源追踪编排 | Codex |
| v1.1.586 | 2026-06-26 | AI 助手草案卡片继续组件化：配置向导、步骤状态、前置草案提示和手动调整入口收口到 `AssistantDraftWizardBlock`，草案卡主体继续保留确认、取消、详情和资源追踪编排 | Codex |
| v1.1.585 | 2026-06-26 | 插件管理配置弹窗继续组件化：Runner Token/日志、插件、执行器、连接、动作和动作试运行弹窗装配收口到 `PluginManagementModals`，主页面继续保留表单联动、保存/测试/试运行和数据加载编排 | Codex |
| v1.1.584 | 2026-06-26 | 定时作业新增/编辑弹窗继续组件化：表单 Modal 外壳、模板来源提示、作业模板选择、编排预览和各表单分区装配收口到 `ScheduledJobFormModal`，主页面保留字段联动、提交、试运行和数据加载编排 | Codex |
| v1.1.583 | 2026-06-26 | 定时作业前端页签装配继续组件化：作业配置和运行记录两个页签收口到 `ScheduledJobManagementTabs`，主页面继续聚焦数据加载、弹窗状态、运行触发和深链编排 | Codex |
| v1.1.582 | 2026-06-26 | 插件管理前端页签装配继续组件化：插件市场、插件、连接、执行器、动作五个页签收口到 `PluginManagementTabs`，主页面继续聚焦数据加载、弹窗状态和操作编排 | Codex |
| v1.1.581 | 2026-06-26 | DB-first 兼容层专项扫描升级为回归门禁：`audit_memory_store_usage.py` 新增 `--fail-on-p1`，测试直接扫描当前 `apps/api/app` 并要求 P0/P1 残留为 0，确保生产路径不再回退到直接 `current_store` 读写 | Codex |
| v1.1.580 | 2026-06-26 | 角色治理列表补齐服务端管理列表契约：`GET /api/system/roles` 支持分页、筛选、排序和 `query/performance` 观测，前端角色管理页不再拉取全量角色后本地分页过滤；查询权限对齐为 `system.roles.read` 或 `system.roles.manage` | Codex |
| v1.1.579 | 2026-06-26 | AI 助手草案任务台继续组件化：摘要指标条、草案详情弹窗和草案展示 helper 分别收口到 `AssistantDraftSummaryStrip`、`AssistantDraftDetailModal` 与 `assistantDraftWorkbenchPresentation`，主页面只保留远程查询、确认/取消和详情打开编排 | Codex |
| v1.1.578 | 2026-06-26 | 插件管理前端主文件继续减重：系统变量预览、全部变量弹窗入口和通用调用链路说明收口到 `PluginWorkspaceGuide`，主页面继续聚焦插件、连接、动作、Runner 数据加载与操作编排，系统变量选项由 `pluginSystemVariableOptions` 统一维护并给连接/动作弹窗复用 | Codex |
| v1.1.577 | 2026-06-25 | 定时作业前端主文件继续减重：作业配置表格和运行记录表格分别收口到 `ScheduledJobConfigTable` 与 `ScheduledJobRunTable`，列表列渲染、工具栏、横向滚动、表格设置和行操作由表格组件承接，主页面只保留数据加载、弹窗、复制、运行、删除和详情打开编排 | Codex |
| v1.1.576 | 2026-06-25 | 管理列表体验继续统一：AI 能力配置页的 AI角色与 Skill 管理页签接入 `ManagementListPage` 嵌入模式，保留新增、编辑、停用、Skill 包上传和模型网关展示，同时支持统一查询表单、横向滚动、表格设置、刷新和本地筛选视图保存 | Codex |
| v1.1.575 | 2026-06-25 | 管理列表体验继续统一：AI 助手 @ 能力配置页接入 `ManagementListPage`，保留新增/编辑/删除、启停、批量启停、灰度和审计跳转能力，同时获得统一搜索、状态/角色筛选、横向滚动、表格设置、刷新和本地筛选视图保存能力 | Codex |
| v1.1.574 | 2026-06-25 | 管理列表体验继续统一：研发执行器策略页接入 `ManagementListPage`，保留新增/编辑/删除策略能力，同时获得统一筛选、横向滚动、表格设置、刷新和本地筛选视图保存能力 | Codex |
| v1.1.573 | 2026-06-25 | DB-first 兼容层 P1 读路径清零：定时作业观测、审计、业务脑配置、平台状态、模型网关日志、Markdown 导出、Mock 写回、原生代码扫描、Graph runtime、首页看板和知识域只读链路不再直接读取 `current_store` 业务集合；统一改为 repository/helper 优先读取，`audit_memory_store_usage` 仅保留 P2 helper/test fallback 残留 | Codex |
| v1.1.572 | 2026-06-25 | 产品配置 DB-first 读路径继续收口：产品详情、产品编码冲突校验、产品删除引用检查、产品子资源清理、按产品列迭代版本和版本分支配置补全不再由路由层直接读取 `current_store` 集合；统一通过产品配置 helper 走 repository-first 读取，PostgreSQL 运行态使用产品级 `EXISTS` 校验引用，MemoryStore 仅作为测试 fallback | Codex |
| v1.1.571 | 2026-06-25 | 定时作业 DB-first fallback 写入收口：AI Skill/Agent、定时作业配置、采集运行、定时作业运行记录和作业最近运行状态更新不再直接写 `current_store` 作业集合；统一通过定时作业内存集合 helper 维护测试 fallback，PostgreSQL 运行态继续由 scheduled job repository 单记录写入和审计事务提交 | Codex |
| v1.1.570 | 2026-06-25 | 插件管理 DB-first fallback 写入收口：标准插件同步、插件定义新增/复制/编辑/删除、插件连接新增/编辑/删除/测试、插件动作新增/编辑/删除、插件调用日志和 Runner 任务关联不再直接写 `current_store` 插件集合；统一通过插件内存集合 helper 更新测试 fallback，PostgreSQL 运行态继续由插件 repository 单记录方法和审计事务提交 | Codex |
| v1.1.569 | 2026-06-25 | 任务运行与评审产物 DB-first fallback 写入收口：任务审计 helper、Graph run/checkpoint、代码评审报告、AI 任务确认后派生 Bug 和知识沉淀不再直接写 `current_store` 业务集合或调用 `current_store.audit()`；MemoryStore 测试 fallback 统一通过集合 helper 和审计 helper 操作，PostgreSQL 运行态继续由任务启动/评审决策 repository 事务提交任务、Review、Graph、报告、Bug、知识沉淀和审计 | Codex |
| v1.1.568 | 2026-06-25 | 产品配置上下文需求/审计 helper DB-first fallback 写入收口：需求单记录 fallback 不再直接写 `current_store.requirements`，审计 helper 不再直接调用 `current_store.audit()`；统一通过需求集合 helper 和审计方法引用/事件列表 helper 操作测试集合，PostgreSQL 运行态继续由 repository 单记录写入和调用方事务提交审计 | Codex |
| v1.1.567 | 2026-06-25 | 用户反馈 DB-first fallback 写入收口：反馈创建、编辑和转需求不再直接写 `current_store.user_feedback` / `current_store.requirements`；反馈单记录通过 `save_user_feedback_record` 写入 repository 或 MemoryStore 测试集合，转需求通过 `save_user_feedback_requirement_conversion` 同步提交需求、反馈 linked 状态和审计事件 | Codex |
| v1.1.566 | 2026-06-25 | 用户洞察审计 helper DB-first fallback 收口：`record_audit_event` 在轻量上下文无 `audit()` 方法时不再直接 append `current_store.audit_events`，统一通过审计事件列表 helper 写入测试集合；普通 MemoryStore 继续走 `audit()`，repository 运行态审计事件继续由对应业务写入 helper 携带提交 | Codex |
| v1.1.565 | 2026-06-25 | 用户使用指标 DB-first fallback 写入收口：使用指标创建不再由调用方直接写 `current_store.user_usage_metrics`，统一通过 `save_user_usage_metric_record` 在 repository 单记录写入或 MemoryStore 测试 fallback 中保存指标；审计事件继续随 repository 写入或测试 fallback 提交 | Codex |
| v1.1.564 | 2026-06-25 | 运营记录审计 helper DB-first fallback 收口：`record_audit_event` 在轻量上下文无 `audit()` 方法时不再直接 append `current_store.audit_events`，统一通过审计事件列表 helper 写入 MemoryStore 测试集合；普通 MemoryStore 继续走 `audit()`，repository 写入仍由调用方事务携带审计事件提交 | Codex |
| v1.1.563 | 2026-06-25 | 模型网关配置与日志 DB-first fallback 写入收口：测试 fallback 的配置替换不再直接赋值 `current_store.model_gateway_configs`，模型调用日志不再直接 append `current_store.model_gateway_logs`；统一通过模型网关配置集合和日志集合 helper 更新 MemoryStore 测试集合，PostgreSQL 运行态继续由模型网关 repository 和调用方事务持久化配置、日志和审计 | Codex |
| v1.1.562 | 2026-06-25 | Mock Issue 写回 DB-first fallback 写入收口：写回结果创建不再先直接写 `current_store.mock_writebacks`，审计不再调用 `current_store.audit()`；统一由 `save_mock_writeback_record` 在 repository 事务或 MemoryStore 测试 fallback 中写入写回结果和审计事件，repository 运行态同步刷新本地读缓存以保持幂等重复提交 | Codex |
| v1.1.561 | 2026-06-25 | 研发执行器策略 DB-first fallback 写入收口：策略列表刷新、策略新增/编辑/删除以及按需补齐产品/代码库资源缓存不再直接写 `current_store.rd_task_executor_policies` / `current_store.products` / `current_store.product_git_repositories`；统一通过策略保存/删除和资源缓存 helper 操作 MemoryStore 测试集合，PostgreSQL 运行态继续通过 rd_task_executor_policy repository 写入策略和审计 | Codex |
| v1.1.560 | 2026-06-25 | 需求主流程 DB-first fallback 写入收口：需求创建、编辑、删除、审批、拒绝、关闭、批量分配、批量排期、批量推进和产品详细设计任务生成不再在调用方直接写 `current_store.requirements` / `current_store.ai_tasks` 或调用 `current_store.audit()`；统一通过需求保存、删除、任务联动和审计 helper 写入 MemoryStore 测试集合或 repository，PostgreSQL 运行态继续使用单记录/联动写入事务 | Codex |
| v1.1.559 | 2026-06-24 | 生命周期上下文与风险信号 MemoryStore fallback 写入收口：上下文边和风险信号刷新不再直接写 `current_store.lifecycle_context_edges` / `current_store.lifecycle_risk_signals`，统一通过锚点替换和风险范围替换 helper 操作测试集合；PostgreSQL 运行态继续由 lifecycle_context repository 持久化刷新结果 | Codex |
| v1.1.558 | 2026-06-24 | 知识空间配置 MemoryStore fallback 写入收口：知识空间、空间成员和文件夹新增/更新不再直接写 `current_store.knowledge_spaces` / `current_store.knowledge_space_members` / `current_store.knowledge_folders`，统一通过空间、成员替换和文件夹 helper 操作测试集合；PostgreSQL 运行态继续由知识 payload repository 持久化空间配置 | Codex |
| v1.1.557 | 2026-06-24 | 知识导入结构化产物 MemoryStore fallback 写入收口：导入解析生成的知识资产、chunk set 和 chunks 不再直接写 `current_store.knowledge_assets` / `current_store.knowledge_chunk_sets` / `current_store.knowledge_chunks`，统一通过资产、chunk set 和 chunk helper 操作测试集合；PostgreSQL 运行态继续由知识 payload repository 持久化结构化产物 | Codex |
| v1.1.556 | 2026-06-24 | 知识文档主流程 MemoryStore fallback 写入收口：上传、导入运行、失败标记、索引完成、重试、取消、chunk set 激活、重新解析和批量移动链路不再直接写 `current_store.knowledge_documents`，统一通过只写文档的 `put_knowledge_document_to_memory` helper 操作测试集合，避免误用会清理 chunks 的文档应用 helper | Codex |
| v1.1.555 | 2026-06-24 | 知识导入任务主流程 MemoryStore fallback 写入收口：上传、运行、失败标记、完成、重试、取消和重新解析链路不再直接写 `current_store.knowledge_import_jobs`，统一通过 import job helper 操作测试集合；PostgreSQL 运行态继续由知识 payload repository 持久化导入任务状态 | Codex |
| v1.1.554 | 2026-06-24 | 知识导入 worker claim MemoryStore fallback 写入收口：worker 本地 claim 不再直接写 `current_store.knowledge_import_jobs`，统一通过 import job helper 操作测试集合；repository 运行态继续优先使用 `claim_knowledge_import_job` 租约 | Codex |
| v1.1.553 | 2026-06-24 | 知识 chunk set MemoryStore fallback 写入收口：知识空间文档创建、编辑和重试索引中的 chunk set building/active 状态不再直接写 `current_store.knowledge_chunk_sets`，统一通过显式 chunk set helper 操作测试集合；PostgreSQL 运行态继续由知识文档 repository 写入和 `persist_knowledge_structure` 持久化结构化知识 payload | Codex |
| v1.1.552 | 2026-06-24 | 知识文档 MemoryStore fallback 写入收口：`clear_knowledge_chunks`、`apply_knowledge_document_to_memory` 和知识文档删除 fallback 不再直接写 `current_store.knowledge_documents` / `current_store.knowledge_chunks` / `current_store.knowledge_deposits`，统一通过显式 `_memory_collection` helper 操作测试集合，保持 PostgreSQL 运行态写入由 repository 承接 | Codex |
| v1.1.551 | 2026-06-24 | 知识域审计 helper DB-first 收口：`record_audit_event` 不再调用 `current_store.audit()`；repository 运行态只生成待写审计事件，MemoryStore 测试 fallback 通过显式审计事件列表 helper 追加并去重，保持知识文档和知识沉淀写路径由 repository/fallback helper 承接 | Codex |
| v1.1.550 | 2026-06-24 | 知识沉淀决策 DB-first 写路径收口：知识沉淀采纳/拒绝不再在决策服务层直接写 `current_store.knowledge_deposits`；统一通过 `save_knowledge_deposit_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态沉淀、可选知识文档、chunks、模型日志和审计使用同一数据库事务提交 | Codex |
| v1.1.549 | 2026-06-24 | 首页看板快照 DB-first fallback 收口：`sync_dashboard_metric_snapshot` 不再直接写 `current_store.dashboard_metric_snapshots`，统一优先调用 `save_dashboard_metric_snapshot_record`，仅在 MemoryStore 测试 fallback 中通过 helper 写入快照集合，保持 PostgreSQL 运行态看板快照单条 repository 写入和短 TTL 只读缓存语义 | Codex |
| v1.1.548 | 2026-06-24 | 迭代规划 DB-first 写路径收口：迭代建议生成、建议决策和建议转需求不再在服务层直接写 `current_store.requirements`、`current_store.iteration_plan_suggestions`、`current_store.iteration_plan_decisions` 或通过 `audit_events` 切片收集审计；统一通过 `persist_iteration_suggestion_record` / `persist_iteration_decision_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态建议、决策、转需求和审计使用同一数据库事务提交 | Codex |
| v1.1.547 | 2026-06-24 | Git Review 快照 DB-first 写路径收口：GitLab MR / GitHub PR 快照成功、复用和失败审计不再在服务层直接写 `current_store.gitlab_mr_snapshots` 或追加 `current_store.audit_events`；统一通过 `save_git_review_snapshot_record` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态快照和审计使用同一数据库事务提交 | Codex |
| v1.1.546 | 2026-06-24 | 代码巡检 DB-first 写路径收口：巡检报告、finding、通知、误报忽略审批和整改任务派生不再在生产服务层直接写 `current_store.code_inspection_*` 或 `current_store.ai_tasks`；统一通过 `persist_code_inspection_records` / `persist_ai_task_record` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态的巡检报告、finding、通知和审计使用同一数据库事务提交 | Codex |
| v1.1.545 | 2026-06-24 | Bug 管理 DB-first 收口：Bug 创建、批量更新、编辑和删除不再直接调用 `current_store.audit()` 或写 `current_store.bugs`，统一通过 `save_bug_record` / `delete_bug_record` 写入 MemoryStore fallback 或 repository；Bug 单记录写入、删除和审计在 PostgreSQL 运行态使用同一数据库事务 | Codex |
| v1.1.544 | 2026-06-24 | AI 助手历史与配置 DB-first 收口：会话/消息测试 fallback 写入改为 helper 访问，助手动作引用配置和角色快捷任务配置不再调用 `current_store.audit()` 或直接写配置集合，统一通过 repository 单记录写入或 MemoryStore fallback 写入配置和审计 | Codex |
| v1.1.543 | 2026-06-24 | AI 助手聊天 DB-first 收口：`assistant_chat` 服务移除聊天运行完成、取消、失败和模型网关审计链路中的直接 `current_store` 写入，不再通过 `current_store.audit_events` 切片收集本次审计；聊天运行、会话、消息、模型日志和审计统一通过 `save_assistant_chat_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态使用数据库事务提交；助手触发定时作业运行归因同步通过 repository 写回 | Codex |
| v1.1.542 | 2026-06-24 | AI 助手草案 DB-first 收口：`assistant_action_drafts` 服务移除草案、动作运行和助手触发定时作业运行归因链路中的直接 `current_store` 写入，不再调用 `current_store.audit()` 生成草案审计；草案、动作运行和审计统一通过 `save_assistant_action_records` 写入 MemoryStore 测试 fallback 或 repository，PostgreSQL 运行态使用数据库事务提交 | Codex |
| v1.1.541 | 2026-06-24 | DB-first 兼容层继续收口：AI 执行器 Runner 服务移除 Runner、任务、插件调用、定时作业运行、采集运行和 AI 任务状态同步中的直接 `current_store` 写入，统一通过单记录 helper 写入 MemoryStore 测试 fallback 或 repository；相关单记录写入与审计事件使用数据库事务 | Codex |
| v1.1.540 | 2026-06-24 | 产品配置 DB-first 收口继续推进：迭代版本和版本代码分支配置路由移除直接 `current_store` 写入，统一通过单记录 helper 写入 MemoryStore 测试 fallback 或 repository；需求单记录写入/删除与审计事件开始使用数据库事务 | Codex |
| v1.1.539 | 2026-06-24 | 产品配置 DB-first 收口继续推进：产品、产品模块、产品 Git 仓库和相关系统路由移除直接 `current_store` 写入，统一通过产品配置单记录 helper 写入 MemoryStore 测试 fallback 或 repository，并把产品配置单记录写入/删除与审计收口为数据库事务 | Codex |
| v1.1.538 | 2026-06-24 | 执行诊断中心稳定性增强：`execution_trace_snapshots` 刷新必须在单个数据库事务中完成 upsert 与过期快照删除，避免诊断读模型出现半刷新状态 | Codex |
| v1.1.537 | 2026-06-24 | 模型网关配置 DB-first 收口：配置 create/patch/delete 新增 repository 单记录读取、upsert 和 delete，默认配置切换与审计随单条记录写入，不再通过整包 `model_gateway_configs/model_gateway_logs` payload 同步配置变更 | Codex |
| v1.1.536 | 2026-06-24 | DB-first 剩余兼容层专项扫描工具化：新增 `scripts/audit_memory_store_usage.py`，按读路径、写路径和 helper 对 `current_store.*` 残留分级输出，用于后续收口和发布前审计 | Codex |
| v1.1.535 | 2026-06-24 | 产品配置 DB-first 收口继续推进：迭代版本、产品模块、产品 Git 仓库和相关系统 create 使用 repository 单记录产品存在性校验、同产品列表或 code 单查冲突校验，不再为子资源创建预加载全量产品配置集合 | Codex |
| v1.1.534 | 2026-06-24 | 产品配置 DB-first 收口继续推进：迭代版本 patch/delete 使用 repository 单记录读取，同产品版本 code 冲突和需求/任务/Bug/分支配置引用检查不再预加载全量产品配置及业务集合 | Codex |
| v1.1.533 | 2026-06-24 | 产品配置 DB-first 收口继续推进：产品模块 delete 使用 repository 单记录读取和跨需求/任务/Bug 的 EXISTS 引用检查，删除不再预加载全量产品配置及业务集合 | Codex |
| v1.1.532 | 2026-06-24 | 产品配置 DB-first 收口继续推进：产品模块 patch 新增 repository 单记录读取与轻量写上下文，模块编码冲突校验仅读取同产品模块列表，避免为单条模块编辑预加载全量产品配置集合 | Codex |
| v1.1.531 | 2026-06-24 | 产品配置 DB-first 收口继续推进：迭代版本代码分支配置 patch/delete 新增 repository 单记录读取与轻量写上下文，避免为单条版本分支配置操作预加载全量产品配置集合 | Codex |
| v1.1.530 | 2026-06-24 | 产品配置 DB-first 收口继续推进：产品 Git 仓库和相关系统 patch/delete 新增 repository 单记录读取与轻量写上下文，避免为单条子资源操作预加载全量产品配置集合 | Codex |
| v1.1.529 | 2026-06-24 | 用户洞察 DB-first 收口：用户反馈更新和转需求链路新增 repository 按 ID 读取，服务层使用反馈专用写上下文，避免依赖运行时 MemoryStore 全量反馈集合 | Codex |
| v1.1.528 | 2026-06-24 | 管理主列表统一支持本地筛选视图：`ManagementListPage` 通过页面级 `viewStorageKey` 保存、应用、删除当前筛选与排序组合，需求、任务、迭代版本、Bug、用户洞察、代码巡检、执行诊断、草案任务台、产品资产和系统管理列表统一接入 | Codex |
| v1.1.527 | 2026-06-24 | 执行诊断中心补齐 Runner 节点：`ai_executor_task.runner_id` 解析为 `ai_executor_runner` 节点并支持按 Runner source_type/source_id 过滤，节点展示心跳、协议、工作区和健康状态且不暴露 token hash | Codex |
| v1.1.526 | 2026-06-24 | 执行诊断中心补齐模型网关日志审计吸附：独立 `model_gateway_log` Trace 会关联 subject、payload 或 ai_task 指向的审计事件，按审计 ID 下钻回到同一模型调用链路并避免重复孤立审计 Trace | Codex |
| v1.1.525 | 2026-06-24 | 插件连接和动作配置列表接入可选 PostgreSQL 分页读路径：带 `page/page_size` 时按关键字、插件、状态和环境筛选并返回 query/performance，未分页保留旧全量兼容 | Codex |
| v1.1.524 | 2026-06-24 | 执行诊断中心补齐定时作业阶段节点过滤：`scheduled_job_stage` 纳入 source_type 枚举和前端筛选，下钻可按 `scheduled_job_run_id:stage_id` 精准定位运行阶段链路 | Codex |
| v1.1.523 | 2026-06-24 | 定时作业配置列表接入 PostgreSQL read model 分页：`GET /api/system/scheduled-jobs` 支持名称、关键字、产品、来源、类型、启停、状态筛选和服务端排序，旧全量返回仅作为兼容路径 | Codex |
| v1.1.522 | 2026-06-24 | 执行诊断中心纳入结果写入记录节点：定时作业运行和插件调用链路自动派生 `result_write_record`，可按写入记录 ID 反查同一条 Trace 并确认产物写入状态 | Codex |
| v1.1.521 | 2026-06-24 | 代码巡检 finding 新增误报忽略审批闭环：报告详情展示逐条审批状态，支持提交忽略申请和批准/驳回，审批通过同步 suppression 统计与审计事件 | Codex |
| v1.1.520 | 2026-06-24 | 代码巡检治理概览新增规则包与误报治理聚合：dashboard 返回 `rule_governance`，页面展示最近报告规则/扫描器版本、版本不一致提示、规则/扫描器版本分布、suppression 总量和过滤原因分布 | Codex |
| v1.1.519 | 2026-06-24 | AI 助手草案任务台继续编辑入口收敛：列表与详情弹窗统一根据草案 ID 生成 `/assistant?draft_id=...` 深链，不再依赖后端来源链接字段；进入助手后复用既有草案深链加载草案卡，来源链路仍独立跳转执行诊断 | Codex |
| v1.1.518 | 2026-06-24 | 执行诊断入口继续统一：前端新增可复用 `ExecutionTraceLink`，AI 助手草案、定时作业运行详情和代码巡检报告详情统一生成 `/governance/execution-traces?source_id=...&source_type=...` 深链，代码巡检详情同时提供巡检报告、来源运行和插件调用诊断入口 | Codex |
| v1.1.517 | 2026-06-24 | 执行诊断中心补齐 AI 助手消息来源链路：`assistant_chat_run` Trace 增加用户消息和助手消息节点，`source_id` 可按 `assistant_message_id` 定位链路；草案任务台新增“来源链路”入口，从草案 `source_message_id` 跳转统一执行诊断 | Codex |
| v1.1.516 | 2026-06-24 | 插件管理前端连接/Runner 测试诊断弹窗继续组件化：连接测试状态、占位 Header 阻断提示、诊断检查项、请求调试台和远端响应预览统一收口到 `PluginDiagnostics`，主页面只保留测试触发、列表状态更新和提示消息编排 | Codex |
| v1.1.515 | 2026-06-24 | 系统角色治理新增用户权限诊断：`GET /api/system/permissions/diagnostics` 可按用户、菜单路径、权限点和数据范围解释允许/阻断原因，角色管理页新增只读诊断工具用于排查某用户为什么能看或不能看 | Codex |
| v1.1.514 | 2026-06-24 | 定时作业前端 Catalog 派生逻辑继续组件化：服务端 catalog 的选项映射、必填校验、默认结果动作和标签格式化抽到 `useScheduledJobCatalogOptions`，主页面只保留 catalog 状态与业务编排 | Codex |
| v1.1.513 | 2026-06-24 | 定时作业新增服务端 catalog/注册中心：作业类型、执行方式、调度方式、连接环境、代码巡检扫描/规则/结果动作和必填规则由 `/api/system/scheduled-job-catalog` 返回，前端新增/编辑弹窗优先使用服务端配置并保留静态降级 | Codex |
| v1.1.512 | 2026-06-24 | 定时作业前端表单转换继续组件化：作业类型选项、扫描配置选项、模板 payload 解析、助手草案回填、配置归一化和路由参数解析抽到 `scheduledJobFormTransformHelpers`，主页面继续收敛为作业配置、运行列表和详情编排 | Codex |
| v1.1.511 | 2026-06-24 | 插件管理前端表单转换继续组件化：连接/动作/Runner 表单 payload、请求预览、结果映射、schema 回填和助手草案回填抽到 `pluginFormTransformHelpers`，主页面只保留插件、连接、动作和 Runner 编排 | Codex |
| v1.1.510 | 2026-06-24 | 执行诊断详情补齐排障建议：详情顶部汇总失败、取消、运行中或排队节点，提供来源 ID 深链和“问 AI”入口，帮助从统一 Trace 直接进入后续诊断 | Codex |
| v1.1.509 | 2026-06-24 | 执行诊断中心补齐来源 ID 深链定位：列表支持 `source_id` 按任一节点来源 ID 精准过滤，前端 URL 命中唯一链路时自动打开详情，便于从定时作业、插件、Runner、模型网关、代码巡检和 AI 助手跳转排障 | Codex |
| v1.1.508 | 2026-06-23 | 定时作业前端运行详情弹窗继续组件化：运行结果详情的 footer、基础信息、运行链路、Trace DAG、结果写入记录和 JSON 预览收口到 `ScheduledJobRunDetailModal`，主页面只保留选中运行、关闭、复制配置和模板生成编排 | Codex |
| v1.1.507 | 2026-06-23 | 插件管理前端 Runner 新增/编辑弹窗继续组件化：Runner Modal/Form 外壳和目标系统联动逻辑抽到 `PluginRunnerModal`，主页面只保留 Runner 表单打开、提交和刷新编排 | Codex |
| v1.1.506 | 2026-06-23 | 插件管理前端 Runner Token 轮换提示和确认弹窗继续组件化：轮换成功提示与确认弹窗收口到 `PluginUtilityModals`，主页面只保留 Runner 轮换状态和提交编排 | Codex |
| v1.1.505 | 2026-06-23 | 插件管理前端插件定义弹窗继续组件化：插件名称、编码、协议、分类、风险等级、状态和说明字段抽到 `PluginModal`，主页面只保留插件表单打开、校验和提交编排 | Codex |
| v1.1.504 | 2026-06-23 | 执行诊断快照读模型增加短 TTL 复用与详情未命中强制刷新：列表/已有详情在短时间内复用 `execution_trace_snapshots`，新链路详情查不到时立即重建快照，降低诊断页重复查询开销且保持钻取可见性 | Codex |
| v1.1.503 | 2026-06-23 | 定时作业前端基础信息继续组件化：新增/编辑作业的名称、作业类型、所属产品和启用字段抽到 `ScheduledJobBasicInfoSection`，主页面只保留作业类型默认配置和产品切换联动编排 | Codex |
| v1.1.502 | 2026-06-23 | 定时作业前端代码仓库配置继续组件化：代码巡检作业的扫描方式、仓库/分支、扫描引擎、规则、baseline、已接受风险和质量门禁字段抽到 `ScheduledJobCodeRepositorySection`，主页面只保留扫描模式默认值和仓库变更编排 | Codex |
| v1.1.501 | 2026-06-23 | 插件管理前端动作编辑弹窗继续组件化：动作新增/编辑表单、结果写入映射字段、请求预览和高级 JSON 字段抽到 `PluginActionModal`，主页面只保留动作表单状态、场景默认值和提交编排 | Codex |
| v1.1.500 | 2026-06-23 | 插件管理前端连接编辑弹窗继续组件化：连接新增/编辑表单、认证 JSON、请求 JSON、schema 字段和“保存并测试”入口抽到 `PluginConnectionModal`，主页面只保留连接表单状态、默认值和提交/测试编排 | Codex |
| v1.1.499 | 2026-06-23 | 插件管理前端连接与动作列表继续组件化：环境筛选、连接测试入口、动作写入目标展示、试运行/运行/删除操作抽到 `PluginConnectionTable` 与 `PluginActionTable`，主页面只保留插件业务事件编排 | Codex |
| v1.1.498 | 2026-06-23 | 插件管理前端插件市场继续组件化：官方插件市场表格、schema 展开、推荐场景、动作模板和配置入口抽到 `PluginMarketplaceTable`，主页面只保留市场动作事件编排 | Codex |
| v1.1.497 | 2026-06-23 | 插件管理前端插件列表继续组件化：插件表格、官方插件复制、编辑/删除操作和分类/版本标签 helper 抽到 `PluginTable` 与 `pluginCatalogHelpers`，主页面只保留插件事件编排 | Codex |
| v1.1.496 | 2026-06-23 | 插件管理前端 Runner 表格继续组件化：执行器列表、展开启动命令、健康状态、Token 状态和操作列抽到 `PluginRunnerTable`，主页面只保留 Runner 事件编排 | Codex |
| v1.1.495 | 2026-06-23 | 插件管理前端 Runner 测试诊断继续组件化：执行器状态摘要、诊断检查项表格和健康状态展示抽到 `RunnerTestDiagnosticsContent`，主页面只保留测试触发和弹窗编排 | Codex |
| v1.1.494 | 2026-06-23 | 定时作业前端执行链路预览继续组件化：配置向导 Steps、编排节点卡片和默认向导步骤抽到 `ScheduledJobOrchestrationFlow`，主页面只保留节点数据构造 | Codex |
| v1.1.493 | 2026-06-23 | 定时作业前端运行详情继续组件化：结果写入记录表格、展开 JSON 预览、来源/状态/摘要展示抽到 `ScheduledJobRunResultWriteRecords`，主页面只保留运行详情编排 | Codex |
| v1.1.492 | 2026-06-23 | 定时作业前端试运行结果继续组件化：JSON 预览抽到 `ScheduledJobJsonPreview`，全链路试运行结果面板抽到 `ScheduledJobDryRunResultPanel`，主页面保留试运行状态与提交编排 | Codex |
| v1.1.491 | 2026-06-23 | 定时作业前端调度配置继续组件化：调度方式、Cron 表达式和固定间隔字段抽到 `ScheduledJobScheduleConfigSection`，主页面只保留表单段落编排 | Codex |
| v1.1.490 | 2026-06-23 | 定时作业前端结果动作编辑器继续组件化：写入策略选择、代码巡检结果动作列表、严重级别和通知动作字段抽到 `ScheduledJobActionConfigSection`，主页面保留插件动作数据和提交编排 | Codex |
| v1.1.489 | 2026-06-23 | 定时作业前端数据连接选择器继续组件化：连接环境筛选、数据连接多选、native full scan 禁用提示和插件资源校验抽到 `ScheduledJobDataConnectionSection`，主页面保留筛选数据与自动匹配动作编排 | Codex |
| v1.1.488 | 2026-06-23 | 定时作业前端表单继续按配置域减重：通用表单分区抽到 `ScheduledJobFormSection`，AI 模型、AI角色、Skills 和知识引用字段抽到 `ScheduledJobAiExecutionSection`，主页面保留作业编排和提交逻辑 | Codex |
| v1.1.487 | 2026-06-23 | 执行诊断中心补齐 AI 助手聊天运行链路：`assistant_chat_runs` 可作为 ExecutionTrace 根类型，关联模型网关日志和审计事件并统一脱敏展示 | Codex |
| v1.1.486 | 2026-06-23 | 代码巡检治理概览 SLA 补齐整改任务覆盖口径：严重 finding 同时统计 Bug 关联和整改任务派生覆盖率，页面展示整改任务覆盖率和未派生任务摘要 | Codex |
| v1.1.485 | 2026-06-23 | 代码巡检治理概览补齐质量门禁趋势：后端 dashboard trend 按日期聚合通过、失败、跳过和未知门禁数，前端概览新增“质量门禁趋势”表 | Codex |
| v1.1.484 | 2026-06-23 | 技术规格启动按业务域拆分：新增 `domains/` 索引和需求交付、AI 助手、插件定时作业执行器、质量运营洞察、系统治理 RBAC 平台配置五个域文档，主规格保留跨域原则和导航 | Codex |
| v1.1.483 | 2026-06-23 | 插件管理前端继续按工具弹窗边界减重：系统变量全集、Runner 执行日志和动作试运行弹窗抽到 `PluginUtilityModals`，主页面保留插件、连接、动作和 Runner 状态编排 | Codex |
| v1.1.482 | 2026-06-23 | 系统角色治理新增只读 RBAC 策略矩阵：后端按角色聚合权限点、菜单入口、数据范围、高风险权限和菜单权限缺口，角色管理页展示“权限审计矩阵”用于排查入口可见但接口无权等授权问题 | Codex |
| v1.1.481 | 2026-06-23 | 定时作业前端继续按运行页签边界减重：运行健康概览、最近失败和慢运行表格抽到 `ScheduledJobRunObservabilityOverview`，主页面保留作业/运行编排逻辑 | Codex |
| v1.1.480 | 2026-06-23 | 执行诊断中心新增 PostgreSQL 持久化读模型：统一链路构建后刷新 `execution_trace_snapshots`，列表和详情优先读取快照分页，保留 MemoryStore 测试 fallback | Codex |
| v1.1.479 | 2026-06-23 | 执行诊断中心前端详情继续按组件边界减重：链路概要、关联对象、节点表、关系表和元数据预览抽到 `ExecutionTraceDetailContent`，为后续 Trace DAG 钻取和诊断建议扩展预留稳定边界 | Codex |
| v1.1.478 | 2026-06-23 | 插件管理前端 Runner 配置继续减重：执行器协议、命令、目标系统、安装模式、工作区白名单和 Token 字段抽到 `PluginRunnerFormFields`，Runner 选项与安装包 helper 独立为 `pluginRunnerHelpers` | Codex |
| v1.1.477 | 2026-06-23 | 插件管理前端连接表单继续减重：请求参数行、连接 schema 字段、GitHub/GitLab 地址校验抽到 `PluginConnectionFormFields` 与 `pluginConnectionAddressHelpers`，主页面保留插件、连接和动作编排逻辑 | Codex |
| v1.1.476 | 2026-06-23 | 插件管理前端继续按诊断边界减重：连接测试请求调试台、市场连接 schema 展示、最近测试摘要、试运行写入预览和状态颜色 helper 抽到 `PluginDiagnostics`，主页面聚焦插件、连接、动作和 Runner 编排 | Codex |
| v1.1.475 | 2026-06-23 | 定时作业前端运行详情继续按组件边界减重：运行链路、Trace DAG、模板来源和复跑对比抽到 `ScheduledJobRunTraceDetails`，执行节点 helper 独立维护，主页面聚焦作业列表、表单和运行详情编排 | Codex |
| v1.1.474 | 2026-06-23 | AI 助手前端主页面继续按组件边界减重：消息气泡、草案工具结果、运行诊断、插件连接诊断和运行对比卡片收口到 `AssistantMessageBubble`，共享消息 helper 独立维护，主页面聚焦会话、Composer 和面板编排 | Codex |
| v1.1.473 | 2026-06-23 | 新增 AI 助手草案任务台：`/assistant/drafts` 按当前用户汇总待确认、失败、已采纳和已修改草案，支持来源深链、详情埋点、继续编辑、确认和取消，并以列表 API 输出采纳率、处理率和用户修改率 | Codex |
| v1.1.472 | 2026-06-23 | 新增运营治理“执行诊断”中心：按运行根聚合定时作业运行、插件调用、AI 执行器任务、模型网关日志、代码巡检报告和审计事件，统一展示节点、边、状态、耗时和脱敏元数据 | Codex |
| v1.1.471 | 2026-06-21 | AI 助手历史列表补齐 cursor 分页与加载更多，历史消息草案工具结果按动作白名单脱敏，指标明细按 limit 下推，草案深链自动滚动到可视区域 | Codex |
| v1.1.470 | 2026-06-21 | 研发执行器策略任务类型下拉按研发流程补齐：展示 PRD/原型/产品详细设计、技术方案、代码实现/开发计划、代码评审、自动化测试、代码整改、发布上线评估和上线后分析，并与现有 `task_type` 匹配口径保持一致 | Codex |
| v1.1.469 | 2026-06-21 | 新增研发执行器策略设计与实现口径：研发任务可按任务类型、产品和优先级匹配 Codex、Claude Code、OpenClaw Runner；该策略只引用插件管理下的 AI 执行器，不装配 Agent/Skill，Runner 完成后回写 AI 任务并进入人工确认 | Codex |
| v1.1.468 | 2026-06-20 | 前端展示型时间统一按 `Asia/Shanghai` 转换后端 UTC 时间，覆盖管理列表、代码巡检、定时作业下次运行/运行详情、Runner 和助手引用等页面，避免少显示 8 小时或直接暴露 ISO 原文 | Codex |
| v1.1.467 | 2026-06-20 | AI 助手补齐运行环境自检引导、效果指标查看口径校准、历史命令会话签名折叠、@ 能力后台配置页和真实页面 smoke 验证 | Codex |
| v1.1.466 | 2026-06-20 | AI 助手 @ 动作候选配置化：新增 `assistant_action_reference_configs` 表、管理 API、灰度/启停/排序/模板版本和审计；效果指标补齐明细钻取 | Codex |
| v1.1.465 | 2026-06-20 | AI 助手新增聊天运行表、消息生命周期字段和服务端取消链路，停止生成后可持久化、审计和历史追踪 | Codex |
| v1.1.464 | 2026-06-19 | AI 助手动作候选选择后保留 `@动作名` 命令前缀并承接用户正文，避免候选 prompt 覆盖输入 | Codex |
| v1.1.463 | 2026-06-19 | AI 助手 @ 候选新增动作入口类型，支持 `@新建` 搜索新建需求/Bug/插件/定时作业/知识/AI 能力配置并回填指令 | Codex |
| v1.1.462 | 2026-06-19 | AI 助手草案表单应用改为服务端 PATCH+confirm 闭环，确认幂等和终态修改保护落地；运营引用候选按产品 scope 收敛，角色快捷任务补齐前端配置入口 | Codex |
| v1.1.461 | 2026-06-18 | AI 助手补齐草案详情查看服务端埋点、定时作业运行助手归因、角色快捷任务配置表和结构化引用严格优先 | Codex |
| v1.1.460 | 2026-06-18 | AI 助手失败运行修复草案补齐来源配置和 current/proposed 字段差异追踪 | Codex |
| v1.1.459 | 2026-06-18 | AI 助手草案模板市场首批六类模板均改为可生成草案，依赖缺失走前置草案闭环 | Codex |
| v1.1.458 | 2026-06-18 | AI 助手定时作业执行权限拆分为 `system.scheduled_jobs.run`，业务角色可执行一次但不能管理作业配置 | Codex |
| v1.1.457 | 2026-06-18 | AI 助手测试/发布角色“发布风险”快捷任务改为草案优先，回填发布风险分析草案提示 | Codex |
| v1.1.456 | 2026-06-18 | AI 助手管理员“AI能力”快捷任务改为草案优先，直接回填新增 AI能力配置向导提示 | Codex |
| v1.1.455 | 2026-06-18 | AI 助手泛化新增任务向导补齐 AI 能力配置入口，用户可先选择 Skill / AI角色草案路径再生成具体能力配置 | Codex |
| v1.1.454 | 2026-06-18 | AI 助手 @ 候选空态补齐定时作业新增和草案生成入口，避免用户误以为 @ 功能无响应 | Codex |
| v1.1.453 | 2026-06-18 | AI 助手对无定时作业管理权限用户输入 `@... 执行一次` 增加发送前权限提示，明确本次不会直接执行 | Codex |
| v1.1.452 | 2026-06-18 | AI 助手产品角色快捷任务改为草案优先，反馈洞察回填周反馈洞察定时作业草案提示，版本风险回填发布风险分析草案提示 | Codex |
| v1.1.451 | 2026-06-18 | AI 助手 @ 定时作业执行一次在等待外部 AI 执行器时返回 `progress_text`，运行卡片明确展示“等待 AI 执行器接单”，避免误判为未执行 | Codex |
| v1.1.450 | 2026-06-18 | AI 助手运行诊断补齐数据连接阶段插件调用日志追踪，三段诊断均可回溯安全日志元数据 | Codex |
| v1.1.449 | 2026-06-18 | AI 助手 @ 候选搜索态保留键盘操作提示，避免输入关键词后用户不知道仍可上下选择并回车添加 | Codex |
| v1.1.448 | 2026-06-18 | AI 助手效果指标失败修复率收紧为仅统计成功 `manual_rerun`，普通调度成功不得误算为修复 | Codex |
| v1.1.447 | 2026-06-18 | AI 助手 run-once 权限闭环补齐：定时作业管理员未命中现成作业时也生成待确认草案，前端展示未执行原因状态卡 | Codex |
| v1.1.446 | 2026-06-18 | AI 助手插件连接/动作草案确认改用插件管理权限，和 @ 插件候选专项授权保持一致 | Codex |
| v1.1.445 | 2026-06-18 | AI 助手 AI 能力草案确认改用 AI 能力管理权限，避免误依赖定时作业管理权限 | Codex |
| v1.1.444 | 2026-06-18 | AI 助手新增任务向导和研发任务草案统一使用“数据来源、AI处理、结果动作、调度策略、确认执行”五步闭环 | Codex |
| v1.1.443 | 2026-06-18 | AI 助手 @ 运维候选权限标签改为显示专项授权来源，避免非 admin 用户被误标为管理员可引用 | Codex |
| v1.1.442 | 2026-06-18 | AI 助手分析类草案补齐 `wizard_steps`，发布风险和知识库巡检卡片展示统一五步闭环 | Codex |
| v1.1.441 | 2026-06-18 | AI 助手周反馈 run-once 消歧补强：停用或非洞察的精确同名作业不得拦截官方周反馈洞察执行 | Codex |
| v1.1.440 | 2026-06-18 | AI 助手运行诊断卡片显式展示“数据连接是否成功 / AI处理是否成功 / 结果动作是否写入成功”三段判断 | Codex |
| v1.1.439 | 2026-06-18 | AI 助手草案模板市场流程收敛为“数据来源、AI处理、结果动作、调度策略、确认执行”五步，知识引用纳入 AI 处理上下文 | Codex |
| v1.1.438 | 2026-06-17 | 对齐 AI 助手效果指标展示口径：前端主指标显示为知识引用命中率 | Codex |
| v1.1.437 | 2026-06-17 | AI 助手周反馈 `@... 执行一次` 消歧改为按官方模板、作业类型和名称语义评分；草案用户修改率接入服务端修改标记 API | Codex |
| v1.1.436 | 2026-06-17 | AI 助手服务端草案详情保留并返回 `wizard_steps`，深链草案卡片不丢配置向导和依赖关系 | Codex |
| v1.1.435 | 2026-06-17 | AI 助手 `/assistant?draft_id=...` 深链加载服务端草案，复用草案卡片展示状态、预检、确认/取消和追踪入口 | Codex |
| v1.1.434 | 2026-06-17 | AI 助手 `@` 候选面板显性化权限、来源、更新时间和摘要；无匹配候选时保持面板可见并提示换词或检查权限 | Codex |
| v1.1.433 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 无执行权限时返回明确 `permission_denied` 工具结果；具备 `system.scheduled_jobs.manage` 的用户可通过显式 @ 命令触发定时作业 | Codex |
| v1.1.432 | 2026-06-17 | AI 助手执行一次运行卡片轮询增强，状态仍为 running 但执行节点摘要更新时也刷新进度 | Codex |
| v1.1.431 | 2026-06-17 | AI 助手显式知识引用补齐知识空间和知识目录，按权限限量注入范围内 chunk | Codex |
| v1.1.430 | 2026-06-17 | AI 助手 `@` 候选类型词搜索收敛，定时作业优先作业定义，运行记录/失败优先运行实例 | Codex |
| v1.1.429 | 2026-06-17 | AI 助手 `@` 候选显示口径对齐，`ai_task` 展示为“研发任务”，`ai_skill` 展示为“Skill” | Codex |
| v1.1.428 | 2026-06-17 | AI 助手裸 `@` 默认候选补齐插件连接，默认上下文候选覆盖插件动作、插件连接、AI角色和 Skill | Codex |
| v1.1.427 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 前端提交路径增强，点击发送或按 Enter 时按 `type=scheduled_job` 补查引用再提交 | Codex |
| v1.1.426 | 2026-06-17 | AI 助手新增插件连接失败诊断工具结果，按连接配置、最近测试和修复建议解释连接失败且不调用模型网关 | Codex |
| v1.1.425 | 2026-06-17 | AI 助手执行一次运行卡片新增当前执行节点说明，展示正在等待数据连接、AI执行器、AI处理或结果动作 | Codex |
| v1.1.424 | 2026-06-17 | AI 助手效果指标的草案类型拆分新增处理率展示，帮助定位不同草案类型的待确认卡点 | Codex |
| v1.1.423 | 2026-06-17 | AI 助手草案配置向导每个步骤新增“AI生成<步骤>草案”回填入口，ready/pending 步骤也可由 AI 调整草案 | Codex |
| v1.1.422 | 2026-06-17 | AI 助手从运行详情链接带入 `scheduled_job_run` 时，在“本次上下文”常驻展示引用解析中、已带入或失败状态 | Codex |
| v1.1.421 | 2026-06-17 | AI 助手配置向导每步补齐“手动调整”入口，数据来源/结果动作跳插件管理，AI处理跳 AI 能力配置，调度/确认跳定时作业配置 | Codex |
| v1.1.420 | 2026-06-17 | AI 助手草案确认失败后前端草案卡片显式进入“失败”状态，不再停留在待确认并仅依赖 toast 提示 | Codex |
| v1.1.419 | 2026-06-17 | AI 助手运行记录卡片补齐“问这次运行 / 生成修复草案 / 对比上次成功”快捷追问，直接携带当前运行引用进入诊断闭环 | Codex |
| v1.1.418 | 2026-06-17 | AI 助手执行一次运行卡片在轮询到终态后显式展示“已刷新到最新状态”，避免初始 running 文案让用户误以为未执行 | Codex |
| v1.1.417 | 2026-06-17 | AI 助手“本次上下文”区域改为常驻展示，未选择引用时明确显示 0 个显式引用、0 个知识 chunk 和未注入知识正文 | Codex |
| v1.1.416 | 2026-06-17 | AI 助手后端访问白名单补齐 `test_owner`、`tester`、`release_owner`，避免测试/发布角色看到快捷入口但调用助手 API 被拒 | Codex |
| v1.1.415 | 2026-06-17 | AI 助手 `@提取每周用户反馈有价值信息 执行一次` 在多个相近 active 周反馈作业下优先执行官方周反馈洞察作业，避免命令退回草案 | Codex |
| v1.1.414 | 2026-06-17 | AI 助手测试快捷任务扩展到测试负责人、测试人员和发布负责人，补齐角色化入口覆盖面 | Codex |
| v1.1.413 | 2026-06-17 | AI 助手运行诊断卡片展示各阶段关联日志 ID，让 AI 处理和结果动作可从对话继续追踪到模型/插件日志 | Codex |
| v1.1.412 | 2026-06-17 | AI 助手本次上下文新增显式“查看摘要”弹窗，run-once 定时作业草案卡片明确“确认并执行一次”闭环提示 | Codex |
| v1.1.411 | 2026-06-17 | AI 助手草案配置向导对需前置配置或阻塞步骤提供“生成前置草案”回填入口，让缺连接、缺动作、缺 AI 能力可继续闭环 | Codex |
| v1.1.410 | 2026-06-17 | AI 助手效果指标面板新增运行追踪和引用追踪分子分母展示，让作业成功率、失败修复率和引用命中率可解释 | Codex |
| v1.1.409 | 2026-06-17 | AI 助手效果指标面板新增草案状态和草案类型拆分，便于追踪待确认、已应用、已取消等草案闭环分布 | Codex |
| v1.1.408 | 2026-06-17 | AI 助手运行诊断和运行对比卡片新增就地后续追问入口，可直接带运行引用生成修复草案、对比上次成功或继续诊断 | Codex |
| v1.1.407 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 识别 TTL 内已有运行中记录并等待新运行可追踪后返回，避免重复触发后仍像未执行 | Codex |
| v1.1.406 | 2026-06-17 | 定时作业失败运行详情新增 AI 快捷追问入口，可一键携带运行引用生成修复草案或对比上次成功运行 | Codex |
| v1.1.405 | 2026-06-17 | AI 助手前端草案卡片按 `draft_id/server_draft_id/client_draft_id` 归一化追踪 ID，避免服务端草案字段差异导致卡片消失或无法跳转 | Codex |
| v1.1.404 | 2026-06-17 | AI 助手发送 `@定时作业 执行一次` 前补齐当前 @ 候选兜底解析，定时作业运行详情消费 `result_write_record_id` 深链并自动展开目标写入记录 | Codex |
| v1.1.403 | 2026-06-17 | AI 助手运行诊断卡片把结果动作段的结果写入记录 ID 链接到定时作业运行详情，增强失败排障追踪闭环 | Codex |
| v1.1.402 | 2026-06-17 | AI 助手“本次上下文”对超出后端注入上限的知识文档显示“最多 8 个知识 chunk 按权限注入”，避免误导用户以为整篇文档全量进入模型 | Codex |
| v1.1.401 | 2026-06-17 | AI 助手终态草案前端收紧：已取消、已过期或失败草案不得再应用到配置表单，只能查看详情或重新生成 | Codex |
| v1.1.400 | 2026-06-17 | AI 助手裸 `@` 默认候选按引用类型均衡返回，避免知识文档数量过多时挤掉需求、AI任务、定时作业、运行记录、动作、AI角色和 Skill | Codex |
| v1.1.399 | 2026-06-17 | AI 助手周反馈、邮件摘要和线上日志异常定时作业草案统一返回 `wizard_steps` 配置向导状态，让数据来源、AI处理、结果动作、调度和确认闭环可追踪 | Codex |
| v1.1.398 | 2026-06-17 | AI 助手代码巡检定时作业草案新增显式 `wizard_steps` 配置向导状态，并增强 `@定时作业 执行一次` 对相似历史任务的可执行作业消歧 | Codex |
| v1.1.397 | 2026-06-17 | AI 助手代码巡检草案补齐 AI Skill/AI角色前置草案，草案生成可确定性返回并支持确认写入 AI 能力配置和解析前置草案资源 | Codex |
| v1.1.396 | 2026-06-17 | AI 助手显式知识引用从文档级补齐到知识 chunk 级，支持 @ 候选、解析和只注入被选中片段 | Codex |
| v1.1.395 | 2026-06-17 | AI 助手执行一次运行记录在聊天气泡内展示状态追踪，并补齐草案详情弹窗展示 payload、字段差异和校验问题 | Codex |
| v1.1.394 | 2026-06-17 | AI 助手“新增任务”向导的建议入口补齐研发任务、定时作业、插件动作、代码巡检和反馈洞察五类任务 | Codex |
| v1.1.393 | 2026-06-17 | AI 助手 run-once 定时作业草案确认后，前端草案卡片展示创建作业和本次运行记录两个追踪入口 | Codex |
| v1.1.392 | 2026-06-17 | AI 助手带“执行一次”意图的定时作业草案确认后会自动触发一次手动运行，并在确认结果和审计中返回运行记录 | Codex |
| v1.1.391 | 2026-06-17 | AI 助手 `@周反馈洞察 执行一次` 未命中已配置作业时，自动生成可确认的周反馈定时作业草案，避免命令无闭环 | Codex |
| v1.1.390 | 2026-06-17 | AI 助手围绕已引用运行记录的失败诊断和上次成功对比支持短追问，无需再次写出“任务/作业/运行”关键词 | Codex |
| v1.1.389 | 2026-06-17 | AI 助手工作台侧栏接入当前用户效果指标，按需展示草案、引用、运行成功和失败修复指标 | Codex |
| v1.1.388 | 2026-06-17 | AI 助手支持围绕失败定时作业运行生成结果动作修复草案，确认前仅写入服务端草案 | Codex |
| v1.1.387 | 2026-06-17 | AI 助手 `@定时作业 执行一次` 优先使用完整 @ 名称精确命中，避免相近作业或前端自动候选引用导致不执行或执行错作业 | Codex |
| v1.1.386 | 2026-06-17 | AI 助手支持围绕一次定时作业运行追问“和上次成功有什么不同”，返回运行对比工具结果和前端对比卡片 | Codex |
| v1.1.385 | 2026-06-17 | AI 助手运行失败诊断接入结果写入记录，结果动作段返回写入目标、写入状态和记录 ID | Codex |
| v1.1.384 | 2026-06-17 | AI 助手服务端草案补齐 `expired` 生命周期、过期预检和效果指标过期草案口径 | Codex |
| v1.1.383 | 2026-06-17 | AI 助手草案模板市场的线上日志异常分析模板接入真实定时作业草案生成链路，并复用服务端定时作业模板目录 | Codex |
| v1.1.382 | 2026-06-17 | AI 助手手动触发 AI 类定时作业时先返回运行中记录，避免聊天请求等待完整外部取数、模型处理和结果写入 | Codex |
| v1.1.381 | 2026-06-17 | AI 助手新增分析类服务端草案，发布风险分析和知识库巡检可生成、确认并追踪助手分析结果 | Codex |
| v1.1.380 | 2026-06-17 | AI 助手邮件摘要草案接入真实定时作业生成链路，聊天可生成绑定邮件收取动作和邮箱连接的服务端草案 | Codex |
| v1.1.379 | 2026-06-17 | AI 助手新增服务端草案模板市场目录，前端侧栏可按模板回填草案提示并显示角色、依赖、流程和接入状态 | Codex |
| v1.1.378 | 2026-06-17 | AI 助手效果指标补齐定时作业运行成功率、失败复跑修复率和知识引用命中率口径 | Codex |
| v1.1.377 | 2026-06-17 | AI 助手新增效果指标接口，按当前用户统计草案采纳、用户修改、动作运行成功和显式引用使用情况 | Codex |
| v1.1.376 | 2026-06-16 | AI 执行器列表新增测试诊断能力，管理员可检测系统默认执行器和本地 Runner 健康项并写入审计 | Codex |
| v1.1.375 | 2026-06-16 | 插件连接新增“保存并测试”交互，连接弹窗保存成功后复用返回连接 ID 调用现有测试诊断接口 | Codex |
| v1.1.374 | 2026-06-16 | AI 执行器 Runner 安装包补充 START_STOP.md 启停说明，明确页面停用与本机进程停止的边界 | Codex |
| v1.1.373 | 2026-06-16 | AI 执行器 Runner 安装包按 Linux、macOS、Windows、Docker 和通用手动安装拆分资产，并在 Runner 元数据中保存目标系统、CPU 架构和安装模式 | Codex |
| v1.1.372 | 2026-06-16 | AI 执行器 Runner 增加远程安装包和 Skill 分发契约，配置 Codex、Claude Code、Hermes、OpenClaw 命令参数并通过 ZIP 下载 | Codex |
| v1.1.371 | 2026-06-16 | 代码巡检 native 扫描支持产品仓库 credential_ref 的 Git askpass 拉取，并在 AI 后处理后保留扫描快照元数据 | Codex |
| v1.1.370 | 2026-06-16 | 代码巡检 native 扫描补充外部引擎实际执行/解析、scan_profile 引擎状态和异步取消保护 | Codex |
| v1.1.369 | 2026-06-16 | 代码巡检报告增强 baseline/质量门禁、多仓库批量扫描、详情聚合、上次扫描对比和对应持久化字段 | Codex |
| v1.1.368 | 2026-06-16 | 代码巡检本地扫描升级为固定工作区 + mirror 缓存 + 运行快照 + 异步 worker；补充规则配置、忽略机制、增量扫描和报告详情快照字段 | Codex |
| v1.1.367 | 2026-06-15 | 代码巡检支持本地完整静态扫描：`native_full_scan` 作业可 clone 产品 Git 仓库、按分支扫描内置规则、记录扫描覆盖率并回填提交人 | Codex |
| v1.1.366 | 2026-06-15 | 代码巡检作业新增显式扫描分支契约：作业按产品 Git 仓库维护 `config_json.repository_id/branch`，未填写分支时默认取仓库 `default_branch`，插件输入和 AI 上下文同步携带分支 | Codex |
| v1.1.365 | 2026-06-15 | 代码巡检仓库绑定和插件调用日志脱敏修复：AI 输出 GitLab project_path 时优先映射到产品 Git 仓库，模型上下文注入配置仓库 ID，插件调用日志 request_summary 落库与返回均脱敏敏感 Header | Codex |
| v1.1.364 | 2026-06-15 | AI 助手显式引用扩展到定时作业、运行记录、插件动作、AI角色和 Skill，并新增定时作业运行失败三段诊断工具结果 | Codex |
| v1.1.363 | 2026-06-14 | AI 助手工作台 P0 能力落地：`@` 知识文档显式引用、引用候选/解析接口、知识 chunk 注入、服务端动作草案持久化和确认/取消闭环 | Codex |
| v1.1.362 | 2026-06-14 | MaxCompute 不再作为官方标准插件和官方动作模板维护；历史官方 MaxCompute 自动降级为普通 HTTP 插件，连接编辑仅保留通用配置 | Codex |
| v1.1.361 | 2026-06-14 | GitLab 官方连接支持本地项目地址单字段配置：页面填写 GitLab 地址，系统自动同步 endpoint 并解析 project_id/project_path，Project ID / Group ID / API 版本不再作为用户手填字段 | Codex |
| v1.1.360 | 2026-06-14 | 系统菜单管理落地：`menu_resources` 由数据库维护菜单元数据、排序、启停和页面访问权限点，系统管理新增菜单管理页；前端仍以静态路由注册表限制可加载页面组件 | Codex |
| v1.1.359 | 2026-06-14 | 定时作业多连接/多动作配置契约：前端表单和列表支持多选展示，后端接收 `plugin_connection_ids` / `plugin_action_ids` 并持久化到 `config_json.orchestration`，旧单字段保留第一项兼容现有运行入口 | Codex |
| v1.1.358 | 2026-06-14 | 定时作业页面配置链路收口：新增/编辑表单按基础信息、数据连接、AI执行、动作和调度分区，列表合并展示“数据连接 / AI执行 / 动作”，运行详情展示运行链路 | Codex |
| v1.1.357 | 2026-06-14 | 定时作业表单调度配置优化：`schedule_type`、`cron_expression`、`interval_seconds` 连续展示，`source_system` 改为模板/审计内部标识并隐藏提交 | Codex |
| v1.1.356 | 2026-06-14 | AI 能力配置用户侧命名调整为“AI角色”：前端、定时作业、AI 助手草案和文档展示统一使用 AI角色，后端继续保留 `ai_agents` / `agent_id` / `resolved_agent_snapshot` 技术契约 | Codex |
| v1.1.355 | 2026-06-14 | 定时作业同步系统默认执行器：AI 执行器仓库任务模板默认携带 `config_json.ai_executor`，前端保存保留模板 JSON，运行节点透传 `model_gateway_log_id` 和执行结果摘要 | Codex |
| v1.1.354 | 2026-06-14 | AI 执行器新增系统默认执行器：`model_gateway` 作为平台托管执行器类型，列表只读展示 `ai_executor_runner_system_default`，动作调用可直接走系统默认模型并返回执行结果；本地 Runner 仍用于 Codex/Claude/Hermes/OpenClaw | Codex |
| v1.1.353 | 2026-06-14 | 插件管理用户侧命名统一为“动作”，配置页、市场统计、删除占用提示和模板说明不再使用“执行”代指动作；AI 执行器概念保持独立 | Codex |
| v1.1.352 | 2026-06-14 | 导航与插件日志边界调整：研发任务菜单归入需求交付，任务中心聚焦配置和定时作业；插件管理移除独立调用日志页签，调用日志在定时作业运行详情体现 | Codex |
| v1.1.351 | 2026-06-13 | Runner 控制补齐 Token 轮换、任务日志、取消和超时熔断；成功运行可反向生成模板，运行详情新增 Trace DAG | Codex |
| v1.1.350 | 2026-06-13 | 任务编排平台升级：官方插件连接 schema、定时作业向导模板、Runner 健康/启动命令和代码巡检整改任务闭环纳入规格 | Codex |
| v1.1.349 | 2026-06-13 | AI 执行器 Runner 数据模型与轮询协议落地，支持 OpenClaw，Runner 完成回写会更新插件日志、定时作业运行和执行器节点 | Codex |
| v1.1.348 | 2026-06-13 | 结果写入记录读模型归入定时作业运行详情，支持按 `scheduled_job_run_id` 精确查看单次运行写入反馈 | Codex |
| v1.1.347 | 2026-06-13 | 新增通用结果写入记录读模型和插件管理结果记录页签，支持按 `write_target` 查看邮件通知及未来扩展目标反馈 | Codex |
| v1.1.346 | 2026-06-13 | 官方插件模板补充 AI 执行器和邮箱收发能力：`ai_executor` 提供 Codex/Claude/Hermes/OpenClaw Runner 连接契约，邮箱模板补齐 SMTP/IMAP/POP3/API 参数和邮件收取动作 | Codex |
| v1.1.345 | 2026-06-13 | 官方插件连接模板收口到 `plugin_templates` 服务端目录，插件市场返回 `connection_defaults/connection_template_version`，页面和助手共用连接草案 payload | Codex |
| v1.1.344 | 2026-06-13 | 定时作业模板市场化收口：新增 `scheduled_job_templates` 服务端目录，页面和助手复用模板包的默认 payload、资源选择规则和版本 | Codex |
| v1.1.343 | 2026-06-13 | 后端定时作业模块继续收口：执行期节点追踪、插件写入预览、代码巡检节点摘要和 AI 处理判断迁移到独立 `scheduled_job_execution_engine` service | Codex |
| v1.1.342 | 2026-06-13 | 后端助手模块继续收口：插件连接、动作、定时作业和代码巡检配置草案构造迁移到独立 `assistant_draft_builder` service | Codex |
| v1.1.341 | 2026-06-13 | 后端插件模块继续收口：连接测试诊断、请求回放、动作草案、修复建议和测试历史构造迁移到独立 `connection_diagnostics` service | Codex |
| v1.1.340 | 2026-06-13 | AI 助手动作草案展示收口到结果写入目标注册表，中文写入目标标签不再由前端本地映射维护 | Codex |
| v1.1.339 | 2026-06-13 | 后端模块收口：定时作业运行可观测性聚合迁移到独立 `scheduled_job_observability` service，避免继续堆入执行服务 | Codex |
| v1.1.338 | 2026-06-13 | 定时作业运行记录新增运行健康概览接口和页面摘要，聚合成功率、失败原因、耗时、AI/Token/插件调用和动作写入成功率 | Codex |
| v1.1.337 | 2026-06-13 | 定时作业运行节点摘要补齐请求方法、URL、HTTP 状态、耗时和业务记录 ID；插件连接测试历史支持展开查看完整请求响应和动作模板草案 | Codex |
| v1.1.336 | 2026-06-13 | 动作模板唯一来源补齐：前端和助手去除官方动作硬编码兜底，模板缺失时不生成可保存动作 | Codex |
| v1.1.335 | 2026-06-13 | 代码巡检治理概览新增聚合接口和页面概览，按当前筛选展示趋势、规则、排行和严重问题 SLA | Codex |
| v1.1.334 | 2026-06-13 | 新增结果写入目标注册表模块，动作表单和写入预览统一使用服务端目标定义、默认映射和可视化字段 | Codex |
| v1.1.333 | 2026-06-13 | 插件连接测试增加 `test_history`、动作模板草案、失败修复建议和变量解析前后差异展示，形成请求回放台 | Codex |
| v1.1.332 | 2026-06-13 | 定时作业表单新增四段式编排视图，基于表单选择实时展示数据连接、AI 处理、知识引用和结果动作状态，并在数据连接节点调用连接测试 | Codex |
| v1.1.331 | 2026-06-13 | 动作模板目录收口为 `plugin_templates` 深模块，模板返回 `template_version`，AI 助手动作草案复用同一模板目录生成 payload | Codex |
| v1.1.330 | 2026-06-13 | 动作模板目录服务端化，前端新增动作表单按模板动态回填请求配置和结果映射 | Codex |
| v1.1.329 | 2026-06-13 | 插件连接测试结果沉淀为 `last_test_summary`，连接列表展示最近测试状态、耗时和错误码 | Codex |
| v1.1.328 | 2026-06-13 | 定时作业复跑运行投影补充 `source_run_summary`，详情页展示来源运行与本次运行对比摘要 | Codex |
| v1.1.327 | 2026-06-12 | 定时作业正式运行复用动作写入预览，邮件通知结果动作在运行详情展示投递 ID、状态和收件人 | Codex |
| v1.1.326 | 2026-06-12 | AI 助手邮箱通知动作草案同步使用 `email_notifications` 映射，草案卡片按中文展示写入目标 | Codex |
| v1.1.325 | 2026-06-12 | 动作补充 `email_notifications` 写入目标，邮箱通知模板和试运行预览展示投递反馈字段 | Codex |
| v1.1.324 | 2026-06-12 | 代码巡检来源链路增加页面跳转：报告详情可跳转来源作业和来源运行，定时作业页支持 `run_id` 深链打开运行详情 | Codex |
| v1.1.323 | 2026-06-12 | 代码巡检报告补充动作和数据连接来源字段，详情页展示来源作业、运行、连接、动作和插件调用链路 | Codex |
| v1.1.322 | 2026-06-12 | AI 助手草案组前端增加临时解析映射，连接/动作保存后可自动回填后续动作/作业草案的真实 ID | Codex |
| v1.1.321 | 2026-06-12 | AI 助手代码巡检配置草案组增强：缺少官方连接或动作时返回连接、动作和作业三类待确认草案 | Codex |
| v1.1.320 | 2026-06-12 | AI 助手新增官方插件连接草案，支持生成 GitHub/GitLab/邮箱 `create_plugin_connection` payload 并带入插件管理新增连接表单 | Codex |
| v1.1.319 | 2026-06-12 | 采集运行记录约束补齐定时作业运行类型，避免 dashboard/lifecycle/plugin/pending 等作业运行写入 `collector_runs` 时触发旧库约束错误 | Codex |
| v1.1.318 | 2026-06-12 | 定时作业模板来源可视化：复制弹窗和运行详情展示 `template_source` | Codex |
| v1.1.317 | 2026-06-12 | 定时作业新增模板化复制：可从作业或运行快照生成新作业草稿，并审计 `template_source` | Codex |
| v1.1.316 | 2026-06-12 | 插件连接测试 request_summary 增加原始请求配置，动态变量解析区块无变量时也显示空状态 | Codex |
| v1.1.315 | 2026-06-12 | 插件连接测试 request_summary 增加动态变量解析明细，前端请求调试台展示表达式、偏移和解析值 | Codex |
| v1.1.314 | 2026-06-12 | 定时作业运行记录复跑补充 `source_run_id`，运行实例、页面详情和终态审计均可追踪来源运行 | Codex |
| v1.1.313 | 2026-06-12 | AI 助手新增官方动作草案，支持生成 GitHub/GitLab 代码巡检和邮箱通知 `create_plugin_action` payload 并带入插件管理表单 | Codex |
| v1.1.312 | 2026-06-12 | 动作试运行补充 `plugin_action.trial_*` 审计事件，保存动作、连接环境、写入目标和状态等轻量上下文 | Codex |
| v1.1.311 | 2026-06-12 | 官方插件市场前端补充动作模板入口，GitHub/GitLab/邮箱市场项可直接创建对应官方动作模板 | Codex |
| v1.1.310 | 2026-06-12 | AI 助手代码巡检定时作业草案支持按用户意图生成 AI 执行模式，并在草案卡片展示模型、Agent 和 Skill 装配 | Codex |
| v1.1.309 | 2026-06-12 | 定时作业运行终态审计继续补齐 AI、插件、连接环境、知识引用和结果写入目标轻量上下文，支持多环境排障与治理追踪 | Codex |
| v1.1.308 | 2026-06-12 | 定时作业前端 AI 装配校验按执行模式触发，非固定 AI 作业切换为 `ai_assisted/ai_generated` 时也必须选择模型、Agent 和 Skill | Codex |
| v1.1.307 | 2026-06-12 | 定时作业表单增加连接环境筛选，按 `default/dev/test/staging/prod/sandbox` 过滤数据连接选项，筛选值不进入作业配置 | Codex |
| v1.1.306 | 2026-06-12 | 代码巡检定时作业支持 AI 执行模式：模型先归一化插件扫描结果，再由结果动作写入代码巡检报告，运行详情保留三段式节点 | Codex |
| v1.1.305 | 2026-06-12 | 插件连接列表和 API 支持按环境筛选，后端校验 `default/dev/test/staging/prod/sandbox` 枚举并在查询层过滤 | Codex |
| v1.1.304 | 2026-06-12 | 插件管理新增官方插件市场只读目录：展示标准插件推荐场景、动作模板、安装状态和运行配置数量，并引导创建连接 | Codex |
| v1.1.303 | 2026-06-12 | 定时作业运行终态审计 payload 补充触发方式、运行状态、导入数量、collector run、插件调用和产品上下文 | Codex |
| v1.1.302 | 2026-06-12 | 定时作业运行触发方式收敛为 `manual/manual_rerun/scheduler` 枚举，复跑写入 `manual_rerun` 便于审计和排障 | Codex |
| v1.1.301 | 2026-06-12 | 插件连接测试 `request_summary` 新增可复制 cURL，页面请求调试台展示完整复现命令 | Codex |
| v1.1.300 | 2026-06-12 | 定时作业保存 AI 助手草案来源时，将草案 ID、来源和标题写入作业配置与 `scheduled_job.created/updated` 审计 payload | Codex |
| v1.1.299 | 2026-06-12 | AI 助手定时作业草案可传递到任务中心新增作业表单，用户确认保存时保留草案映射 | Codex |
| v1.1.298 | 2026-06-12 | AI 助手页面消费 `assistant.action_draft` 工具结果，以待确认配置草案卡片展示定时作业核心配置 | Codex |
| v1.1.297 | 2026-06-12 | AI 助手工具结果新增定时作业配置草案：周反馈洞察和代码巡检请求返回 `assistant.action_draft`，确认前不写 `scheduled_jobs` | Codex |
| v1.1.296 | 2026-06-12 | 定时作业新增场景模板：周反馈洞察和代码巡检模板自动带出连接、AI 能力、调度、动态变量映射和结果动作 | Codex |
| v1.1.295 | 2026-06-12 | 动作补充邮箱通知发送场景模板，自动带出官方邮箱插件、邮件发送路径、Content-Type 和默认通知参数 | Codex |
| v1.1.294 | 2026-06-12 | 动作试运行响应和页面补充 `write_preview`，展示结果动作写入目标、候选数量和样例数据 | Codex |
| v1.1.293 | 2026-06-12 | 代码巡检报告写入支持运行时应用动作 `result_mapping`，可从嵌套响应或 `$` 根数组提取 finding | Codex |
| v1.1.292 | 2026-06-12 | 动作补充 GitHub/GitLab 代码巡检场景模板，自动带出官方插件、请求路径、默认 Params 和巡检报告映射 | Codex |
| v1.1.291 | 2026-06-12 | 定时作业运行记录增加复跑入口：运行记录操作列可基于原作业重新触发并展示新运行详情 | Codex |
| v1.1.290 | 2026-06-11 | 收紧定时 AI 作业校验并增强前端可观测性：AI 类型作业强制 Agent/Skill/模型网关，运行详情展示三段执行链路卡片，连接测试展示请求调试台 | Codex |
| v1.1.289 | 2026-06-11 | 动作结果写入目标补充 `code_inspection_reports`，新增代码巡检报告 JSONPath 可视化字段 | Codex |
| v1.1.288 | 2026-06-11 | 代码巡检结果新增提交人维度、产品范围读取控制、扫描器 severity mapping、严重问题 Bug 去重和结果动作状态摘要 | Codex |
| v1.1.287 | 2026-06-11 | 同步代码仓库巡检技术规格：`code_repository_inspection` 定时作业支持多结果动作，写入代码巡检报告、自动创建严重问题 Bug 并记录邮件/钉钉通知反馈 | Codex |
| v1.1.286 | 2026-06-11 | 新增 AI 助手工作台升级整体方案：通过 `@` 显式引用知识库、业务对象、插件、AI 能力和定时任务，并在助理内生成可确认的配置/动作草案 | Codex |
| v1.1.285 | 2026-06-11 | 定时作业配置和执行链路校正：表单按数据连接、AI 模型、Agent、Skills、结果动作排序，用户反馈洞察抽取必须经过模型网关处理后再执行结果动作 | Codex |
| v1.1.284 | 2026-06-11 | 定时作业运行结果详情补齐三段核心节点：数据连接获取内容、Skill 处理内容、结果动作反馈内容，并在 Skill 节点展示模型调用状态 | Codex |
| v1.1.283 | 2026-06-11 | 定时作业运行记录增强：列表提供运行结果详情入口，手动触发后展示本次结果摘要、插件调用、Skill/Prompt 快照、作业配置快照和错误信息 | Codex |
| v1.1.282 | 2026-06-11 | 插件管理删除闭环增强：插件、连接和动作列表提供删除入口，删除前提示使用清单；后端在被连接、动作、定时作业或调用日志引用时返回 409 | Codex |
| v1.1.281 | 2026-06-11 | 定时作业维护闭环增强：作业列表提供编辑和删除入口，编辑回填调度/插件/AI 装配配置，删除通过 DELETE 接口写入审计 | Codex |
| v1.1.278 | 2026-06-11 | 插件管理维护闭环增强：插件、连接和动作列表提供编辑入口，PATCH 编辑保留服务端脱敏密钥，连接/动作 Params 与 Headers 可继续可视化维护 | Codex |
| v1.1.279 | 2026-06-11 | 明确插件任务链路为数据连接取数、Skill 分析处理、结果动作写入；动作 `result_mapping.write_target` 提供可视化写入目标，定时作业输出映射为空时复用动作结果映射 | Codex |
| v1.1.280 | 2026-06-11 | 补充动作写入目标表单联动：前端必须按 `write_target` 动态展示对应 JSONPath 字段，并与高级 `result_mapping` JSON 双向同步 | Codex |
| v1.1.277 | 2026-06-11 | 知识管理可靠性增强：导入 worker 使用 PostgreSQL 租约 claim，目录归档按子树生效，资产按 bucket/object_key 幂等 upsert，chunk set 保存索引状态用于回滚 | Codex |
| v1.1.275 | 2026-06-11 | OCR JSON chunk 来源元数据补齐页内图片数量、表格数量和图片引用，知识中心 chunk 预览展示图片来源 | Codex |
| v1.1.274 | 2026-06-11 | 知识导入新增 regex_section 正则分块策略，按结构分隔符切分并保留分段标题和切分规则元数据 | Codex |
| v1.1.273 | 2026-06-11 | 知识中心导入任务弹窗展示后台 worker 状态，chunk 预览展示 OCR/Table 页码、表格和来源资产元数据 | Codex |
| v1.1.272 | 2026-06-11 | 知识 chunk 版本化约束收口：数据库移除旧单文档 chunk_index 唯一约束，改为按 chunk set 维度约束 chunk 序号 | Codex |
| v1.1.271 | 2026-06-11 | 知识导入 worker 补偿扫描 queued 任务时使用导入任务创建人执行写入，确保 chunk set 创建人、审计归属和 PostgreSQL 用户外键一致 | Codex |
| v1.1.270 | 2026-06-11 | 知识导入解析产物拆分增强：OCR JSON / Table JSON 生成结构化 sidecar 资产和 parsed Markdown，并把页码/表格来源写入 chunk metadata | Codex |
| v1.1.269 | 2026-06-11 | 知识导入任务补齐应用内后台 worker/队列：上传、重解析和重试自动入队，启动时补偿 queued 任务，并保留 run 作为运维补偿入口 | Codex |
| v1.1.268 | 2026-06-10 | 知识管理第一阶段实现落地：知识空间、目录、MinIO/S3-compatible 资产、导入任务、chunk set、上传预览和空间权限过滤进入当前架构 | Codex |
| v1.1.267 | 2026-06-10 | 新增知识管理升级设计：明确知识空间、目录、文档、MinIO 资产、导入任务、解析器适配、父子分块、权限过滤和分阶段实施边界 | Codex |
| v1.1.266 | 2026-06-10 | 补充 MaxCompute 用户反馈洞察抽取实现：`user_feedback_insight_extract` 定时作业消费插件返回 `$.insights` 并通过用户反馈 service 写入，动作页面支持场景模板和高级 JSON 编辑 | Codex |
| v1.1.278 | 2026-06-11 | 增强插件连接测试诊断：完整展示最终请求 URL、query、headers 明文值、Header 来源和远端响应摘要，对 `***` 占位做诊断标记并明确认证 Header 优先级 | Codex |
| v1.1.277 | 2026-06-11 | 补充插件连接级请求配置：`plugin_connections.request_config` 保存公共 Params/Headers，运行时与动作 `request_config` 合并且动作覆盖同名 query/header | Codex |
| v1.1.276 | 2026-06-11 | 补充插件配置体验优化：连接测试诊断报告、系统变量预览、动作请求预览/试运行、可视化参数与 JSON 双向同步、定时作业插件输入映射表格化 | Codex |
| v1.1.265 | 2026-06-10 | 新增插件管理第一阶段实现：补充 `integration_plugins`、`plugin_connections`、`plugin_actions`、`plugin_invocation_logs` 数据模型，定时作业可通过动作调用 HTTP/MCP HTTP 集成并保存插件快照、调用日志和审计 | Codex |
| v1.1.264 | 2026-06-10 | 新增定时系统作业与 AI 能力装配设计：补充 `ai_skills`、`ai_agents`、`scheduled_jobs`、`scheduled_job_runs` 数据模型，明确定时采集、AI 分析、Agent/Skill 快照、锁租约、审计和人工确认边界 | Codex |
| v1.1.263 | 2026-06-09 | 迭代版本新增版本级代码分支配置，`product_version_branch_configs` 结构表与 API 支持维护多仓库基准分支、开发分支、状态和来源 | Codex |
| v1.1.262 | 2026-06-09 | RBAC 重设计评审完成后新增开发实施计划，明确数据库迁移、授权服务、系统角色 API、动态菜单、部门、产品成员、知识空间和业务接口权限迁移的分阶段开发顺序 | Codex |
| v1.1.261 | 2026-06-07 | RBAC 重设计确认外部 SSO 身份映射原则：外部用户必须绑定到系统 users.id 后才能获得部门、角色、产品成员和知识空间授权，SSO 不直接下发权限 | Codex |
| v1.1.260 | 2026-06-07 | RBAC 重设计确认组织/部门、产品成员和知识空间决策：人员归属部门，产品范围由产品管理页成员配置维护，知识权限使用独立知识空间，高危权限由系统管理员配置并审计 | Codex |
| v1.1.259 | 2026-06-07 | RBAC 重设计补充菜单权限与左侧导航：角色可配置功能菜单，用户登录后返回 menu_tree，前端左侧按授权菜单渲染，后端仍按权限点和数据范围强制校验 | Codex |
| v1.1.258 | 2026-06-07 | RBAC 重设计补充研发交付扩展预置角色：开发工程师、测试负责人、测试人员和发布负责人，明确测试 Bug 登记/验证、自动化测试确认和发布评估权限边界 | Codex |
| v1.1.257 | 2026-06-07 | 新增系统权限管理 RBAC 重设计文档，明确角色 CRUD、权限点、用户角色关系、数据范围授权、审计和从固定六角色模型迁移的目标方案 | Codex |
| v1.1.256 | 2026-06-07 | 研发运营看板更名为日志监控，前端页面仅保留 GitLab、Jenkins 和线上日志指标；采集运行记录与待归属数据队列降为历史兼容 API，不再作为当前页面功能入口 | Codex |
| v1.1.255 | 2026-06-07 | 用户洞察新增用户反馈转需求闭环，需求新增来源字段并支持来源筛选/排序；用户洞察页面移除手工登记使用指标和生成迭代建议入口，聚焦反馈详情、处理和转需求 | Codex |
| v1.1.254 | 2026-06-07 | Code Review 报告新增只读 Review 结论回写模板，任务中心报告弹窗展示可复制 Markdown 模板，用于人工贴回 GitLab MR / GitHub PR；系统继续保持只读 Review 流程，不自动远端回写 | Codex |
| v1.1.253 | 2026-06-07 | AI 助手从系统上下文摘要回答升级为后端工具化查询：聊天前按用户问题生成 delivery progress、pending reviews、code review、iteration、bugs、model gateway 等 read-model 工具结果，模型优先依据 `system_context.tool_results` 回答，助手消息 metadata 持久化 `tool_results` 和引用链接 | Codex |
| v1.1.252 | 2026-06-06 | Code Review 报告弹窗新增需求全链路跳转入口，报告可从任务中心直接回到对应需求的完整交付链路，补齐 Review 报告到需求全链路的闭环追踪 | Codex |
| v1.1.251 | 2026-06-06 | GitHub PR / GitLab MR 代码 Review 闭环增强：预览返回权限诊断，快照响应返回上一快照引用、diff 新增/修改/删除对比和复用标记，任务中心展示快照结果用于 PR 刷新、重试和配置排查 | Codex |
| v1.1.250 | 2026-06-06 | persistence.py 大文件拆分继续收口：任务启动、Review 决策和任务状态更新的跨表写事务下沉到 TaskReadRepository，PostgresSnapshotRepository 只保留公开方法委托和跨域回调装配 | Codex |
| v1.1.249 | 2026-06-06 | persistence.py 大文件拆分继续收口：删除需求和任务运行态私有 upsert 兼容入口，跨域事务直接调用 RequirementReadRepository 和 TaskReadRepository 的领域 upsert 方法 | Codex |
| v1.1.248 | 2026-06-06 | persistence.py 大文件拆分继续收口：删除仅测试引用的产品配置私有 upsert 兼容入口，产品配置写入边界统一通过 ProductConfigReadRepository 的公开保存方法验证 | Codex |
| v1.1.247 | 2026-06-06 | persistence.py 大文件拆分继续收口：删除未引用的知识沉淀 row 转换旧副本，并将通用 delete_missing/delete_missing_ids 表维护 helper 抽取到 TableMaintenanceRepository，PostgresSnapshotRepository 仅保留回调委托入口 | Codex |
| v1.1.246 | 2026-06-06 | persistence.py 大文件拆分继续收口：数据库发号器和历史 app_state_snapshots 读写抽取到 SystemStateRepository，PostgresSnapshotRepository 仅保留 next_id/load/save 委托入口 | Codex |
| v1.1.245 | 2026-06-06 | persistence.py 大文件拆分继续收口：产品详情、产品版本、产品模块、产品 Git 仓库和相关系统读取 SQL 下沉到 ProductConfigReadRepository，PostgresSnapshotRepository 仅保留产品配置读取委托入口 | Codex |
| v1.1.244 | 2026-06-06 | 管理列表统一表格规范继续增强：ManagementListPage 增加稳定根样式入口，统一约束工具栏换行、表格单元格换行和右固定操作列不换行，降低需求、角色、用户洞察、DevOps 等宽表页面在中等视口下变形风险 | Codex |
| v1.1.243 | 2026-06-06 | 需求管理列表布局优化：固定更宽业务列、操作列收敛为“全链路 + 更多”、详情页入口进入更多菜单，并将表格横向滚动宽度提高到 1600，降低中等宽度页面列挤压 | Codex |
| v1.1.242 | 2026-06-06 | persistence.py 大文件拆分继续收口：PersistentMemoryStore 测试兼容层抽取到 persistent_memory_store，persistence.py 保留兼容 re-export 并继续收窄为 PostgreSQL snapshot repository 实现 | Codex |
| v1.1.241 | 2026-06-06 | persistence.py 大文件拆分继续收口：生产 PostgreSQL 运行时容器 PostgresRuntimeStore 抽取到 persistence_runtime，main.py 直接从 runtime 模块装配，persistence.py 保留兼容 re-export 和 snapshot repository 实现 | Codex |
| v1.1.240 | 2026-06-06 | persistence.py 大文件拆分继续收口：snapshot payload/load/save、集合合并、上下文清理、counter 同步和恢复链路 helper 抽取到 persistence_payloads，persistence.py 继续收窄为运行时 store 与 PostgreSQL repository 实现 | Codex |
| v1.1.239 | 2026-06-06 | persistence.py 大文件拆分继续收口：仓储 Protocol、集合字段常量和 snapshot contract 抽取到 persistence_contracts，persistence.py 聚焦 payload helper、运行时 store 和 PostgreSQL repository 实现 | Codex |
| v1.1.238 | 2026-06-06 | 后端大文件拆分继续收口：main.py 删除剩余 repository/source-store/save legacy helper，收敛为 FastAPI 装配、启动运行时、middleware 和异常处理入口；任务工作流 PostgreSQL source context 下沉到 task_workflow_context 且不继承 MemoryStore | Codex |
| v1.1.237 | 2026-06-06 | 管理列表统一表格规范继续增强：自定义渲染列默认包裹稳定单元格容器，长文本、Tag 和 Space 组合不得撑开宽表或造成角色/用户洞察/DevOps 等页面变形 | Codex |
| v1.1.236 | 2026-06-06 | 需求全链路详情新增版本内多需求对比，在需求归属迭代版本时展示同版本需求数量、状态分布和当前需求位置，便于版本级交付验收 | Codex |
| v1.1.235 | 2026-06-06 | 需求全链路详情新增“导出链路报告”能力，前端基于同一 full-chain read model 生成 Markdown 报告，覆盖需求、产品、迭代版本、阶段实体摘要和时间线，便于真实迭代测试留痕 | Codex |
| v1.1.234 | 2026-06-06 | 需求全链路详情时间线新增类型筛选，支持在同一需求链路内按需求、AI 任务、Review、代码评审、Bug、发布和知识沉淀等事件类型聚焦查看，并显示筛选后事件数量 | Codex |
| v1.1.233 | 2026-06-06 | 模型网关配置列表纳入服务端分页/筛选/排序和查询性能观测：`GET /api/system/model-gateway-configs` 在分页模式下返回 `query/performance`，支持配置名、provider、状态、默认配置、Chat/Embedding 模型和 Embedding 连接模式筛选；前端模型网关页接入远程列表模式 | Codex |
| v1.1.232 | 2026-06-06 | 角色管理列表纳入服务端分页/筛选/排序和查询性能观测：`GET /api/auth/roles` 在分页模式下返回 `query/performance`，支持角色、分类、业务角色、可见入口、权限点和状态筛选；前端角色页接入远程列表模式 | Codex |
| v1.1.231 | 2026-06-06 | 任务管理待确认 Review 子表纳入统一表格规范：固定布局、横向滚动、摘要省略和操作列右固定，降低确认按钮拥挤和弹窗列宽变形风险；任务批量重试/取消现有状态机与回归验证保持不变 | Codex |
| v1.1.230 | 2026-06-06 | 用户管理列表纳入管理类服务端分页/筛选/排序和查询性能观测：`GET /api/users` 支持用户名、显示名、角色、状态筛选，PostgreSQL 运行时优先由 users SQL read model 返回分页结果；前端用户管理页接入远程列表模式和角色下拉筛选 | Codex |
| v1.1.229 | 2026-06-06 | 管理列表统一表格规范继续推进：ManagementListPage 默认固定布局、按显示列宽计算横向滚动、默认长文本省略和操作列右固定；角色、DevOps 采集运行/待归属列表补齐固定列宽、横向滚动和详情承载，降低列宽变形风险 | Codex |
| v1.1.228 | 2026-06-06 | persistence.py 大文件拆分继续推进：生命周期上下文 edge/risk 和首页看板快照保存/写入 SQL upsert 归入 LifecycleDashboardReadRepository，PostgresSnapshotRepository 保留生命周期/看板写入委托入口 | Codex |
| v1.1.227 | 2026-06-06 | persistence.py 大文件拆分继续推进：采集运行和待归属队列保存、单记录保存和写入 SQL upsert 归入 OperationalCollectionReadRepository，PostgresSnapshotRepository 保留采集/归属写入委托入口和审计回调 | Codex |
| v1.1.226 | 2026-06-06 | persistence.py 大文件拆分继续推进：用户反馈、用户使用指标、迭代建议和迭代决策保存/写入 SQL upsert 归入 UserInsightReadRepository，PostgresSnapshotRepository 保留用户洞察写入委托入口和审计/需求回调 | Codex |
| v1.1.225 | 2026-06-06 | persistence.py 大文件拆分继续推进：GitLab daily、Jenkins release 和线上日志指标保存、单记录保存和写入 SQL upsert 归入 DevopsReadRepository，PostgresSnapshotRepository 保留 DevOps 写入委托入口和审计回调 | Codex |
| v1.1.224 | 2026-06-06 | persistence.py 大文件拆分继续推进：知识文档、知识 chunk、知识沉淀保存/删除、引用清理和写入 SQL upsert 归入 KnowledgeReadRepository，PostgresSnapshotRepository 保留知识写入委托入口和审计/模型日志回调 | Codex |
| v1.1.223 | 2026-06-06 | persistence.py 大文件拆分继续推进：Bug 保存、单记录保存/删除、重复缺陷引用清理和 bugs 写入 SQL upsert 归入 BugReadRepository，PostgresSnapshotRepository 保留 Bug 写入委托入口 | Codex |
| v1.1.222 | 2026-06-06 | persistence.py 大文件拆分继续推进：Graph Run、Graph Checkpoint 和 Human Review 运行态保存/upsert 归入 TaskReadRepository，PostgresSnapshotRepository 保留任务运行态写入委托入口 | Codex |
| v1.1.221 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 任务主表保存和 ai_tasks 写入 SQL upsert 归入 TaskReadRepository，PostgresSnapshotRepository 保留任务写入委托入口和 Review/Graph 跨域事务回调 | Codex |
| v1.1.220 | 2026-06-06 | persistence.py 大文件拆分继续推进：需求台账保存、单记录保存/删除和 requirements 写入 SQL upsert 归入 RequirementReadRepository，PostgresSnapshotRepository 保留需求写入委托入口和跨域事务回调 | Codex |
| v1.1.219 | 2026-06-06 | persistence.py 大文件拆分继续推进：产品、迭代版本、产品模块、产品 Git 仓库和相关系统写入 SQL upsert 归入 ProductConfigReadRepository，PostgresSnapshotRepository 保留产品配置写入委托入口和审计回调 | Codex |
| v1.1.218 | 2026-06-06 | persistence.py 大文件拆分继续推进：审计事件保存和 audit_events 写入 SQL upsert 归入 AuditReadRepository，PostgresSnapshotRepository 保留审计写入委托入口和跨域审计回调 | Codex |
| v1.1.217 | 2026-06-06 | persistence.py 大文件拆分继续推进：GitLab MR / GitHub PR 兼容快照和代码评审报告写入 SQL upsert 归入 GitReviewReadRepository，PostgresSnapshotRepository 保留 Git review 写入委托入口和审计回调 | Codex |
| v1.1.216 | 2026-06-06 | persistence.py 大文件拆分继续推进：模拟 Issue 写回行转换和 mock_issues 写入 SQL upsert 归入 MockWritebackReadRepository，PostgresSnapshotRepository 保留写回写入委托入口和审计回调 | Codex |
| v1.1.215 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 助手会话/消息写入 SQL upsert 归入 AssistantChatReadRepository，PostgresSnapshotRepository 保留助手历史写入委托入口和跨域模型日志/审计回调 | Codex |
| v1.1.214 | 2026-06-06 | persistence.py 大文件拆分继续推进：模型网关配置/日志写入 SQL upsert 归入 ModelGatewayReadRepository，PostgresSnapshotRepository 保留写入委托入口和跨域模型日志薄委托 | Codex |
| v1.1.213 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中任务工作流、Review 决策、Graph checkpoint、知识沉淀/Bug 建议生成和 Markdown 导出旧实现副本，相关契约继续由 ai_tasks、markdown_export、mock_writeback 和代码评审服务承接 | Codex |
| v1.1.212 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 model_gateway 和 ai_tasks services 承接的 OpenAI-compatible chat/embedding、模型日志、token 估算和代码评审 executor 旧 helper 副本 | Codex |
| v1.1.211 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 dashboard_metrics、devops_metrics 和 user_insights services 承接的看板产品归属过滤、DevOps 统一列表和用户洞察统一列表投影旧 helper 副本 | Codex |
| v1.1.210 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 operational_records service 承接的采集运行、待归属处理、GitLab/Jenkins/线上日志指标校验旧 helper 副本，保持 DevOps 明细、采集和归属 API 契约不变 | Codex |
| v1.1.209 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 requirements service 承接的需求全链路 payload/时间线旧 helper 副本，保持需求详情、全链路聚合、任务读权限和 DB-first stale runtime 契约不变 | Codex |
| v1.1.208 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 knowledge_documents、knowledge_search 和 knowledge_deposits services 承接的知识索引/检索旧 helper 副本，保持知识 API、Embedding 兜底、权限过滤和 DB-first stale runtime 契约不变 | Codex |
| v1.1.207 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已由 lifecycle_context service 承接的生命周期上下文旧 helper 副本，保留生命周期 API、dashboard source rows 和审计产品过滤契约不变 | Codex |
| v1.1.206 | 2026-06-06 | persistence.py 大文件拆分继续推进：业务大脑配置恢复读取 SQL 查询归入 BrainAppReadRepository，PostgresSnapshotRepository 仅保留委托入口，保持 rd_brain 只读配置和 PostgreSQL 运行时契约不变 | Codex |
| v1.1.205 | 2026-06-06 | persistence.py 大文件拆分继续推进：知识文档、知识 chunk 和知识沉淀恢复读取 SQL 查询归入 KnowledgeReadRepository，保持知识恢复、知识列表/检索 read model 和 DB-first stale runtime 契约不变 | Codex |
| v1.1.204 | 2026-06-06 | persistence.py 大文件拆分继续推进：Bug 恢复读取 SQL 查询归入 BugReadRepository，保持 Bug 恢复、Bug 管理列表 SQL read model、版本归属和 DB-first 兼容契约不变 | Codex |
| v1.1.203 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 任务、Graph Run、Graph Checkpoint 和 Human Review 恢复读取 SQL 查询归入 TaskReadRepository，保持任务/Review/Graph 恢复、任务列表 SQL read model 和 DB-first 兼容契约不变 | Codex |
| v1.1.202 | 2026-06-06 | persistence.py 大文件拆分继续推进：需求台账恢复读取 SQL 查询归入 RequirementReadRepository，保持需求恢复、需求列表 SQL read model、负责人字段和 DB-first 兼容契约不变 | Codex |
| v1.1.201 | 2026-06-06 | persistence.py 大文件拆分继续推进：产品、迭代版本、产品模块、产品 Git 仓库和相关系统恢复读取 SQL 查询归入 ProductConfigReadRepository，保持产品配置恢复、列表 SQL read model 和 DB-first 兼容契约不变 | Codex |
| v1.1.200 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 助手会话和消息恢复读取 SQL 查询归入 AssistantChatReadRepository，保持用户级历史隔离、消息 references 和 DB-first 恢复契约不变 | Codex |
| v1.1.199 | 2026-06-06 | persistence.py 大文件拆分继续推进：用户使用指标、用户反馈和迭代规划建议/决策恢复/列表读取 SQL 查询归入 UserInsightReadRepository，保持用户洞察统一列表、看板 source rows 和助手上下文契约不变 | Codex |
| v1.1.198 | 2026-06-06 | persistence.py 大文件拆分继续推进：GitLab daily、Jenkins release 和线上日志原始指标恢复/列表读取 SQL 查询归入 DevopsReadRepository，保持 DevOps 明细和看板 source rows 契约不变 | Codex |
| v1.1.197 | 2026-06-06 | persistence.py 大文件拆分继续推进：生命周期上下文和首页看板快照/source rows 读取与组装抽取为 LifecycleDashboardReadRepository，保持 DB 派生看板、权限过滤和慢查询缓存契约不变 | Codex |
| v1.1.196 | 2026-06-06 | persistence.py 大文件拆分继续推进：模拟 Issue 写回恢复读取 SQL 查询抽取为 MockWritebackReadRepository，保持幂等 key 聚合、Issue payload 投影和恢复读取契约不变 | Codex |
| v1.1.195 | 2026-06-06 | persistence.py 大文件拆分继续推进：GitLab MR / GitHub PR 兼容快照和代码评审报告恢复读取 SQL 查询抽取为 GitReviewReadRepository，保持快照、报告、任务链接和恢复计数器契约不变 | Codex |
| v1.1.194 | 2026-06-06 | persistence.py 大文件拆分继续推进：采集运行和待归属队列恢复快照/列表读取 SQL 查询抽取为 OperationalCollectionReadRepository，保持列表过滤、真实空集合和 DB-first stale runtime 契约不变 | Codex |
| v1.1.193 | 2026-06-06 | persistence.py 大文件拆分继续推进：审计事件恢复快照和审计列表读取 SQL 查询抽取为独立 AuditReadRepository，保持主体/操作者/时间过滤、sequence 排序和 query/performance 观测契约不变 | Codex |
| v1.1.192 | 2026-06-06 | persistence.py 大文件拆分继续推进：模型网关配置列表和模型调用日志列表读取 SQL 查询抽取为独立 ModelGatewayReadRepository，保持配置脱敏、日志过滤和排序响应契约不变 | Codex |
| v1.1.191 | 2026-06-06 | persistence.py 大文件拆分继续推进：AI 助手会话列表和会话消息读取 SQL 查询抽取为独立 AssistantChatReadRepository，保持用户级历史隔离和消息 references 响应契约不变 | Codex |
| v1.1.190 | 2026-06-06 | persistence.py 大文件拆分继续推进：知识文档列表、知识沉淀列表/详情、可读向量 chunk 检查和知识 chunk 搜索 SQL 查询抽取为独立 KnowledgeReadRepository，PostgresSnapshotRepository 仅保留委托入口 | Codex |
| v1.1.189 | 2026-06-06 | 后端大文件拆分继续收口：删除 main.py 中已迁往 git_review、user_insights 和 lifecycle_context service 的 GitHub/GitLab 预览/快照、用户洞察/迭代规划和生命周期 read model 遗留实现副本，保留现有 API 契约与回归测试 | Codex |
| v1.1.188 | 2026-06-06 | 生命周期上下文 handler 移除 legacy main 回调，上下游实体追踪、v1.2 证据匹配、风险信号、缺失上下文和 lifecycle edge/risk materialize 收口到 lifecycle_context service | Codex |
| v1.1.187 | 2026-06-06 | GitLab MR 与 GitHub PR 预览/列表/快照 handler 移除 legacy main 回调，provider API 读取、diff 风险摘要、快照限制校验、审计和 DB-first 保存收口到 git_review service | Codex |
| v1.1.186 | 2026-06-06 | 用户洞察与迭代规划 handler 移除 legacy main 回调，使用指标、用户反馈、迭代建议和建议决策的列表查询、状态机校验、上下文校验、审计和 DB-first 保存收口到 user_insights service | Codex |
| v1.1.185 | 2026-06-06 | DevOps 指标明细 handler 移除 legacy main 回调，GitLab 每日代码指标、Jenkins 发布记录和线上日志指标的列表查询、上下文校验、指标校验、审计和 DB-first 保存收口到 operational_records service | Codex |
| v1.1.184 | 2026-06-06 | 采集运行与待归属处理 handler 移除 legacy main 回调，collector run 和 pending attribution 的列表查询、状态机校验、上下文校验、审计和 DB-first 保存收口到 operational_records service | Codex |
| v1.1.183 | 2026-06-06 | AI 任务创建 handler 移除 legacy main 回调，技术方案/后续任务/发布准备/发布后分析/代码评审上下文校验、产品上下文快照、需求状态推进、审计和 DB-first 保存收口到 ai_tasks service；tasks router 已整体不再回调 legacy main | Codex |
| v1.1.182 | 2026-06-06 | AI 任务批量重试 handler 移除 legacy main 回调，重复/不存在/不可重试 skipped、失败重试复用 start service、失败仍可解释返回、批次审计和 repository 保存收口到 ai_tasks service | Codex |
| v1.1.181 | 2026-06-06 | Review 决策 handler 移除 legacy main 回调，审批、编辑后审批、驳回和补充信息请求的状态机、需求推进、Bug 建议生成、知识沉淀、Graph checkpoint、Code Review 报告确认和 DB-first 保存契约收口到 ai_tasks service | Codex |
| v1.1.180 | 2026-06-06 | AI 任务启动 handler 移除 legacy main 回调，`POST /api/ai-tasks/{task_id}/start` 直接调用 ai_tasks service；模型网关失败注入测试改为 patch model_gateway service opener，启动、失败重试、Graph Run、Code Review 报告和 DB-first 保存契约保持不变 | Codex |
| v1.1.179 | 2026-06-06 | AI 任务启动业务逻辑下沉到 ai_tasks service，模型调用失败/配置失败、Code Review 执行器失败、Human Review 创建、Graph Run/Checkpoint 创建、Code Review 报告生成和 DB-first 保存契约保持不变；main.py 暂保留薄委托以兼容现有 opener 注入 | Codex |
| v1.1.178 | 2026-06-06 | AI 任务启动依赖的模型网关任务调用 helper 从 main.py 下沉到 model_gateway service，保留 URL opener 注入以兼容失败重试测试，为 start_ai_task 后续迁移到 ai_tasks service 做准备 | Codex |
| v1.1.177 | 2026-06-06 | AI 任务批量取消 handler 移除 legacy main 回调，重复/不存在/终态 skipped 明细、逐任务取消、pending Review 取消、Graph Run 取消 checkpoint、逐任务审计、批次审计和 repository 保存收口到 ai_tasks service | Codex |
| v1.1.176 | 2026-06-06 | AI 任务取消和补充信息提交 handler 移除 legacy main 回调，任务工作流写上下文、Graph Run 取消 checkpoint、pending Review 取消、more_info_answers 追加、审计事件和任务状态 repository 保存收口到 ai_tasks service | Codex |
| v1.1.175 | 2026-06-06 | Graph Run 列表、待确认 Review 列表和 Review 详情 handler 移除 legacy main 回调，任务工作流只读上下文、pending Review SQL 摘要仓储、Review 详情投影和任务读权限校验收口到 ai_tasks service | Codex |
| v1.1.174 | 2026-06-06 | AI 任务详情 handler 移除 legacy main 回调，任务工作流只读上下文、任务详情投影、Review/Graph Run/知识沉淀/Mock Issue 聚合和任务读权限校验收口到 ai_tasks service | Codex |
| v1.1.173 | 2026-06-06 | 批量推进需求状态 handler 移除 legacy main 回调，目标状态校验、版本归属保护、状态机 skipped 明细、逐需求审计、批次审计和 repository 保存收口到 requirements service，requirements router 已整体不再回调 legacy main | Codex |
| v1.1.172 | 2026-06-06 | 批量排期需求 handler 移除 legacy main 回调，产品/版本校验、可排期状态校验、skipped 明细、逐需求审计、批次审计和 repository 保存收口到 requirements service | Codex |
| v1.1.171 | 2026-06-06 | 批量分配需求负责人 handler 移除 legacy main 回调，负责人校验、skipped 明细、逐需求审计、批次审计和 repository 保存收口到 requirements service | Codex |
| v1.1.170 | 2026-06-06 | 批量需求生成产品详细设计任务 handler 移除 legacy main 回调，批量校验、skipped 明细、逐任务创建、批次审计和 repository 保存收口到 requirements service | Codex |
| v1.1.169 | 2026-06-06 | 单条需求生成产品详细设计任务 handler 移除 legacy main 回调，产品上下文快照、需求状态推进、AI task 创建、审计事件和同事务 repository 保存收口到 requirements service | Codex |
| v1.1.168 | 2026-06-06 | 需求审批、驳回和关闭 handler 移除 legacy main 回调，状态机校验、活跃任务保护、审计事件和 repository 精细保存收口到 requirements service | Codex |
| v1.1.167 | 2026-06-06 | 需求修改和删除 handler 移除 legacy main 回调，状态保护、产品/版本/模块校验、审计事件、repository 精细保存和删除收口到 requirements service | Codex |
| v1.1.166 | 2026-06-06 | 需求创建 handler 移除 legacy main 回调，写权限、产品/版本/模块校验、审计事件和 repository 精细保存收口到 requirements service | Codex |
| v1.1.165 | 2026-06-06 | 需求详情和需求全链路读 handler 移除 legacy main 回调，任务工作流只读上下文、链路实体聚合和时间线组装收口到 requirements service | Codex |
| v1.1.164 | 2026-06-06 | 研发运营统一列表 handler 移除 legacy main 回调，SQL read model、GitLab/Jenkins/线上日志 fallback 和查询观测收口到 devops_metrics service | Codex |
| v1.1.163 | 2026-06-06 | 用户洞察统一列表 handler 移除 legacy main 回调，SQL read model、使用趋势/反馈/迭代建议 fallback 和查询观测收口到 user_insights service | Codex |
| v1.1.162 | 2026-06-06 | AI 任务列表 handler 移除 legacy main 回调，任务 SQL read model、权限范围、时间过滤、兼容 fallback 和查询观测收口到 ai_tasks service | Codex |
| v1.1.161 | 2026-06-06 | 需求列表 handler 移除 legacy main 回调，SQL read model 分页筛选排序、兼容 fallback 投影和查询观测收口到 requirements service | Codex |
| v1.1.160 | 2026-06-06 | Bug 列表 handler 移除 legacy main 回调，SQL read model 分页筛选排序、兼容 fallback 投影和查询观测收口到 bugs service | Codex |
| v1.1.159 | 2026-06-06 | Bug 创建、批量更新、修改和删除 handler 移除 legacy main 回调，写权限、上下文校验、状态机、审计和 repository 保存收口到 bugs service | Codex |
| v1.1.158 | 2026-06-06 | 知识文档更新、重建索引和删除 handler 移除 legacy main 回调，状态校验、chunk 重建、沉淀解除关联、审计和 repository 保存收口到 knowledge service | Codex |
| v1.1.157 | 2026-06-06 | 知识文档创建 handler 移除 legacy main 回调，标题/内容/角色/产品校验、chunk 索引、模型日志、审计和 repository 保存收口到 knowledge service | Codex |
| v1.1.156 | 2026-06-06 | 知识沉淀采纳/驳回 handler 移除 legacy main 回调，状态校验、文档生成、索引、审计和 repository 保存收口到 knowledge_deposits service | Codex |
| v1.1.155 | 2026-06-06 | 知识搜索 handler 移除 legacy main 回调，repository-first 候选、关键词兜底、向量兼容过滤和响应投影收口到 knowledge_search service | Codex |
| v1.1.154 | 2026-06-06 | 知识沉淀候选列表 handler 移除 legacy main 回调，repository-first 读取和状态过滤收口到 knowledge_deposits service | Codex |
| v1.1.153 | 2026-06-06 | 知识文档列表 handler 移除 legacy main 回调，repository-first 列表查询、权限过滤、排序分页和性能观测收口到 knowledge_documents service | Codex |
| v1.1.152 | 2026-06-06 | 模拟 Issue 写回 router 移除 legacy main 回调，幂等写回、审计和 repository 保存收口到 mock_writeback service | Codex |
| v1.1.151 | 2026-06-06 | 审计事件列表 router 移除 legacy main 回调，筛选、排序、分页和性能观测收口到 audit_events service | Codex |
| v1.1.150 | 2026-06-06 | 代码评审报告读取 router 移除 legacy main 回调，报告关联和任务读权限校验下沉到 code_review_report service | Codex |
| v1.1.149 | 2026-06-06 | Markdown 导出 router 移除 legacy main 回调，任务工作流只读上下文和 Markdown 渲染下沉到 service | Codex |
| v1.1.148 | 2026-06-06 | 需求、任务和 Bug 批量操作结果统一使用 ManagementBatchResultModal 展示批次号、成功数、跳过数和明细 | Codex |
| v1.1.147 | 2026-06-06 | 任务管理批量取消和批量重试完成后展示批次号、成功数、仍失败和 skipped 明细，补齐任务批量操作可解释性 | Codex |
| v1.1.146 | 2026-06-06 | 需求批量排期、分配负责人、推进状态和生成任务完成后展示批次号、成功数和 skipped 明细，提升批量操作可解释性 | Codex |
| v1.1.145 | 2026-06-06 | 需求批量推进状态补充迭代版本归属保护，进入交付链路状态前必须先排期，避免全链路断链 | Codex |
| v1.1.144 | 2026-06-05 | 需求管理新增批量推进状态，按研发流程前进路径逐条校验并记录 requirement.batch_status_advanced 审计 | Codex |
| v1.1.143 | 2026-06-05 | 需求管理新增批量分配负责人，需求台账补充 assignee 字段，批量接口逐条校验需求状态并记录批次级与逐需求审计 | Codex |
| v1.1.142 | 2026-06-05 | 任务管理新增多选批量重试，复用单任务失败重试状态机，支持模型网关和代码评审执行器失败任务批量恢复并记录审计 | Codex |
| v1.1.141 | 2026-06-05 | AI 助手回答新增服务端引用候选与消息 references 持久化，支持从回答跳转到产品、迭代、需求、任务、Review、Bug、代码评审和知识沉淀 | Codex |
| v1.1.140 | 2026-06-05 | 任务管理新增多选批量取消，批量接口逐条校验任务状态并写入批次级与逐任务审计 | Codex |
| v1.1.139 | 2026-06-05 | 需求全链路详情新增按阶段分组的可展开明细区，并为需求、迭代、任务、Review、PR/代码评审、Bug、发布和知识沉淀提供管理页跳转入口 | Codex |
| v1.1.138 | 2026-06-05 | 前端管理主列表统一补齐普通列默认最小宽度和更宽的右侧固定操作列，减少角色、用户洞察、DevOps、任务和 Bug 等宽表页面挤压变形 | Codex |
| v1.1.137 | 2026-06-05 | 发布验证流程固化为 `scripts/release_smoke.sh` 固定入口，默认执行重建容器、生产就绪 API 门禁和真实浏览器页面 smoke | Codex |
| v1.1.136 | 2026-06-05 | 核心管理列表性能观测新增按列表名解析的 P95 目标，响应 `performance` 返回 `p95_target_ms`，慢查询日志同步记录目标值 | Codex |
| v1.1.135 | 2026-06-05 | 研发运营统一列表 SQL read model 从 persistence.py 抽取为独立 DevopsReadRepository，PostgresSnapshotRepository 仅保留统一列表委托入口 | Codex |
| v1.1.134 | 2026-06-05 | 用户洞察统一列表 SQL read model 从 persistence.py 抽取为独立 UserInsightReadRepository，PostgresSnapshotRepository 仅保留统一列表委托入口 | Codex |
| v1.1.133 | 2026-06-05 | Bug 管理 SQL read model 从 persistence.py 抽取为独立 BugReadRepository，PostgresSnapshotRepository 仅保留 Bug 列表 count/list 委托入口 | Codex |
| v1.1.132 | 2026-06-05 | AI 任务 SQL read model 和待 Review 摘要查询从 persistence.py 抽取为独立 TaskReadRepository，PostgresSnapshotRepository 仅保留任务列表与待确认列表委托入口 | Codex |
| v1.1.131 | 2026-06-05 | 需求管理 SQL read model 从 persistence.py 抽取为独立 RequirementReadRepository，PostgresSnapshotRepository 仅保留需求列表 count/list 委托入口 | Codex |
| v1.1.130 | 2026-06-05 | 产品配置 SQL read model 从 persistence.py 抽取为独立 ProductConfigReadRepository，PostgresSnapshotRepository 仅保留委托入口 | Codex |
| v1.1.129 | 2026-06-05 | 采集运行、待归属处理和生命周期上下文 API 从 main.py 迁移为独立 collectors、attribution、lifecycle router，main.py 不再承载业务 @app 路由 | Codex |
| v1.1.128 | 2026-06-05 | Markdown 导出 API 从 main.py 迁移为独立 export router，并保留任务读取权限、完成态校验和 text/markdown 响应契约 | Codex |
| v1.1.127 | 2026-06-05 | 写回结果、代码评审报告和审计事件 API 从 main.py 迁移为独立 writeback、code_review_reports、audit router，并保留 DB-first 写入与列表观测契约 | Codex |
| v1.1.126 | 2026-06-05 | 用户洞察与迭代建议 API 从 main.py 迁移为独立 user_insights router，并保留 SQL/read model 列表和查询观测契约 | Codex |
| v1.1.125 | 2026-06-05 | 研发运营指标 API 从 main.py 迁移为独立 devops_metrics router，并保留 SQL/read model 列表和查询观测契约 | Codex |
| v1.1.124 | 2026-06-05 | 知识中心 API 从 main.py 迁移为独立 knowledge router，并补充单一路由归属约束 | Codex |
| v1.1.123 | 2026-06-05 | AI 任务列表与创建 handler 从 main.py 下沉到 tasks router，进一步收敛任务 API 领域边界 | Codex |
| v1.1.122 | 2026-06-05 | AI 任务与 Review API 入口迁移为独立 tasks router，并补充单一路由归属约束 | Codex |
| v1.1.121 | 2026-06-05 | 需求交付 API 从 main.py 迁移为独立 requirements router，并补充单一路由归属约束 | Codex |
| v1.1.120 | 2026-06-05 | Bug 管理 API 从 main.py 迁移为独立 bugs router，并补充单一路由归属约束 | Codex |
| v1.1.119 | 2026-06-05 | GitLab MR / GitHub PR 预览、列表和快照 API 从 main.py 迁移为独立 git_review router，并补充单一路由归属约束 | Codex |
| v1.1.118 | 2026-06-05 | 业务大脑只读 API 从 main.py 迁移为独立 brain_apps router，repository-first 读取逻辑收口到 brain_apps service | Codex |
| v1.1.117 | 2026-06-05 | 模型网关配置与日志 API 从 main.py 迁移为独立 model_gateway router，配置校验、连接测试和运行时 URL/Embedding helper 收口到 model_gateway service | Codex |
| v1.1.116 | 2026-06-05 | 相关系统 API 从 main.py 迁移为独立 related_systems router，产品配置域 router 拆分完成 | Codex |
| v1.1.115 | 2026-06-05 | 产品 Git 仓库 API 从 main.py 迁移为独立 product_git_repositories router，并保留 provider 校验与凭据脱敏契约 | Codex |
| v1.1.114 | 2026-06-05 | 产品模块 API 从 main.py 迁移为独立 product_modules router，并复用产品配置共享上下文 service | Codex |
| v1.1.113 | 2026-06-05 | 迭代版本 API 从 main.py 迁移为独立 product_versions router，并抽取产品配置共享上下文 service | Codex |
| v1.1.112 | 2026-06-05 | 产品主体 CRUD API 从 main.py 迁移为独立 products router 并补充路由边界约束 | Codex |
| v1.1.111 | 2026-06-05 | 用户管理 API 从 main.py 迁移为独立 users router 并补充路由边界约束 | Codex |
| v1.1.110 | 2026-06-05 | 平台健康检查与长期记忆状态 API 从 main.py 迁移为独立 platform router 和 platform status service | Codex |
| v1.1.109 | 2026-06-05 | 认证与角色目录 API 从 main.py 迁移为独立 auth router 并补充路由边界约束 | Codex |
| v1.1.108 | 2026-06-05 | 首页 IT 团队看板 API 从 main.py 迁移为独立 dashboard router 并补充路由边界约束 | Codex |
| v1.1.107 | 2026-06-05 | AI 助手 API 从 main.py 迁移为独立 assistant router | Codex |
| v1.1.106 | 2026-06-05 | API 通用错误封装、当前用户依赖、store 获取和角色校验拆分为共享 deps 模块 | Codex |
| v1.1.105 | 2026-06-05 | AI 助手聊天工作流、会话读写和错误边界拆分为独立 assistant chat service | Codex |
| v1.1.104 | 2026-06-05 | AI 助手系统上下文与消息投影拆分为独立 assistant context service | Codex |
| v1.1.103 | 2026-06-05 | 首页 IT 团队看板指标聚合拆分为独立 service，Web shell 与登录页品牌统一为 Enterprise AI Brain | Codex |
| v1.1.102 | 2026-06-05 | 首页 IT 团队看板补充短 TTL 缓存、强制刷新、缓存元数据和慢查询日志设计 | Codex |
| v1.1.101 | 2026-06-05 | 发布就绪门禁新增浏览器页面 smoke 脚本，管理主列表查询观测补齐列表名和慢查询日志 | Codex |
| v1.0.0 | 2026-05-27 | 基于设计文档生成项目级技术规格 | Claude |
| v1.0.1 | 2026-05-27 | 切换为项目级文档维护源，补充产品和平台配置实现边界 | Codex |
| v1.0.2 | 2026-05-28 | 补充四个业务主体生命周期、页面信息架构、需求任务快照和主体级审计约束 | Claude |
| v1.0.3 | 2026-05-29 | 补充 GitLab 代码质量、线上日志运营分析、Jenkins 发布数据、首页看板和 Bug 管理技术设计 | Claude |
| v1.0.4 | 2026-05-29 | 扩展 AI 任务类型为产品详细设计、技术方案、代码开发辅助、代码 Review、自动化测试、发布上线评估和上线后分析 | Claude |
| v1.0.5 | 2026-05-29 | 强化软件研发全流程感知，补充研发上下文图谱、跨阶段追溯和风险信号设计 | Claude |
| v1.0.6 | 2026-05-29 | 补充用户使用洞察、用户反馈收集和 AI 迭代规划建议技术设计 | Claude |
| v1.0.7 | 2026-05-29 | 对齐 PRD，将内部 GitLab MR 代码 Review 提前纳入 v1 MVP，补充 diff 快照、可插拔 code-review 执行器、内部报告归档和不回写 GitLab 约束 | Claude |
| v1.0.8 | 2026-05-29 | 补齐 GitLab MR 快照表、索引、执行器调用协议、超时、schema 校验和审计边界 | Claude |
| v1.1.0 | 2026-05-29 | 对齐 PRD v1.1.0，补充 MVP-A/B/C 实施切片、MVP 角色映射、PRD 草案与产品详细设计边界和文档链接修正 | Claude |
| v1.1.1 | 2026-05-29 | 修复产品评审问题：将 GitLab 只读集成前置到 MVP-A，统一阶段优先级、需求多任务语义、GBrain 边界、审计字段和 diff 限制 | Claude |
| v1.1.2 | 2026-05-31 | 对齐真实 CRUD 删除语义、主数据唯一性约束和需求审批到任务确认的前端主链路 | Codex |
| v1.1.3 | 2026-05-31 | 补齐审计查询过滤和审计列表详情、生命周期追踪页面操作约束 | Codex |
| v1.1.4 | 2026-05-31 | 对齐 code_review 执行器失败状态、错误码和审计事件 | Codex |
| v1.1.5 | 2026-05-31 | 补齐 GitLab MR diff 超限失败审计和快照状态机事件 | Codex |
| v1.1.6 | 2026-05-31 | 补齐 GitLab MR 变更文件数限制和审计指标 | Codex |
| v1.1.7 | 2026-05-31 | 补齐 GitLab MR 单文件 diff 行数限制和审计指标 | Codex |
| v1.1.8 | 2026-05-31 | 明确 MVP 用户角色目录、权限边界、角色字典表和用户管理角色选择约束 | Codex |
| v1.1.9 | 2026-05-31 | 推进产品配置细粒度 PostgreSQL 持久化，产品、版本、模块和 Git 资源同步结构表 | Codex |
| v1.1.10 | 2026-05-31 | 推进需求台账细粒度 PostgreSQL 持久化，需求创建、审批和任务引用同步 `requirements` 结构表 | Codex |
| v1.1.11 | 2026-05-31 | 推进 AI 任务细粒度 PostgreSQL 持久化，任务核心字段同步 `ai_tasks` 结构表 | Codex |
| v1.1.12 | 2026-05-31 | 推进人工确认和 Graph 运行态细粒度 PostgreSQL 持久化，Review、Run 和 Checkpoint 同步结构表 | Codex |
| v1.1.13 | 2026-05-31 | 细化 MVP 用户角色定义，补齐职责、数据范围、决策范围和前端角色目录加载约束 | Codex |
| v1.1.14 | 2026-05-31 | 推进知识文档、知识沉淀候选和审计事件细粒度 PostgreSQL 持久化 | Codex |
| v1.1.15 | 2026-05-31 | 推进 Bug 管理细粒度 PostgreSQL 持久化，Bug 记录同步 `bugs` 结构表 | Codex |
| v1.1.16 | 2026-05-31 | 推进模型网关配置和调用元数据日志细粒度 PostgreSQL 持久化 | Codex |
| v1.1.17 | 2026-05-31 | 系统管理新增只读角色管理入口，明确 MVP 六类角色定义、职责、范围和不可自由创建角色约束 | Codex |
| v1.1.18 | 2026-05-31 | 推进 GitLab MR 快照和 Code Review 报告细粒度 PostgreSQL 持久化 | Codex |
| v1.1.19 | 2026-05-31 | 推进模拟 Issue 回写细粒度 PostgreSQL 持久化，写入 `mock_issues` 并支持恢复幂等结果 | Codex |
| v1.1.20 | 2026-05-31 | 推进相关系统细粒度 PostgreSQL 持久化，纳入产品配置结构表恢复范围 | Codex |
| v1.1.21 | 2026-05-31 | 移除 AI 任务启动本地输出 fallback，缺少模型网关时任务明确失败 | Codex |
| v1.1.22 | 2026-05-31 | 将知识检索升级为 chunk 级权限过滤结果，并持久化 `knowledge_chunks` | Codex |
| v1.1.23 | 2026-05-31 | 补齐生命周期视图和首页看板任务聚合的任务读权限过滤 | Codex |
| v1.1.24 | 2026-05-31 | 明确角色业务映射、可见入口和限制边界，并补齐知识索引失败原因与重试契约 | Codex |
| v1.1.25 | 2026-06-01 | 补齐生命周期上下文从审计主体和 MVP 证据主体精准解析到任务链路的实现约束 | Codex |
| v1.1.26 | 2026-06-01 | 明确低层 AI 任务创建必须回写需求任务引用并遵守需求关闭状态边界 | Codex |
| v1.1.27 | 2026-06-01 | 收敛模型网关 provider 配置边界，非 OpenAI-compatible provider 在配置入口拒绝 | Codex |
| v1.1.28 | 2026-06-01 | 增加可重复执行的 pgvector HNSW 索引迁移，补齐知识 chunk 向量检索索引基础设施 | Codex |
| v1.1.29 | 2026-06-01 | 知识索引接入 OpenAI-compatible embeddings，检索按权限过滤后的 chunk embedding 做向量排序 | Codex |
| v1.1.30 | 2026-06-01 | 将用户反馈升级为真实业务主体，支持登记、筛选、状态处理、审计和 `user_feedback` PostgreSQL 持久化 | Codex |
| v1.1.31 | 2026-06-01 | 将迭代规划建议升级为基于真实反馈/Bug 证据生成、确认、可选转需求和 PostgreSQL 持久化 | Codex |
| v1.1.32 | 2026-06-01 | 将用户使用指标升级为真实业务主体，支持登记、筛选、审计和 `user_usage_metrics` PostgreSQL 持久化 | Codex |
| v1.1.33 | 2026-06-01 | 将 GitLab 每日代码指标升级为真实业务主体，支持登记、筛选、审计和 `gitlab_daily_code_metrics` PostgreSQL 持久化 | Codex |
| v1.1.34 | 2026-06-01 | 将 Jenkins 发布记录升级为真实业务主体，支持登记、筛选、审计和 `jenkins_release_records` PostgreSQL 持久化 | Codex |
| v1.1.35 | 2026-06-01 | 将线上运行日志指标升级为真实业务主体，支持登记、筛选、审计和 `online_log_metrics` PostgreSQL 持久化 | Codex |
| v1.1.36 | 2026-06-01 | 补齐 development_planning 和 automated_testing 基础闭环，自动化测试确认后生成 AI 自动测试 Bug 记录 | Codex |
| v1.1.37 | 2026-06-01 | 补齐 release_readiness 和 post_release_analysis 基础闭环，发布评估保存真实发布/日志/缺陷上下文，上线后分析确认后生成 AI 上线后 Bug 记录 | Codex |
| v1.1.38 | 2026-06-01 | 首页 IT 团队看板按产品过滤知识文档和审计事件，知识文档支持产品归属上下文 | Codex |
| v1.1.39 | 2026-06-02 | 生命周期上下文接入 v1.2 真实证据主体，动态标识缺失上下文并归集跨阶段风险信号 | Codex |
| v1.1.40 | 2026-06-02 | 新增采集运行记录结构表、API、审计和研发运营页面入口，作为外部采集器接入前的真实运行台账 | Codex |
| v1.1.41 | 2026-06-02 | 新增待归属数据队列结构表、API、审计和 DevOps 处理入口 | Codex |
| v1.1.42 | 2026-06-02 | 模型网关配置新增测试检测能力，临时调用 OpenAI-compatible Chat 与 Embedding 接口并返回脱敏状态，不保存密钥或模型日志 | Codex |
| v1.1.43 | 2026-06-02 | 模型网关测试检测支持 `test_target=chat`，允许 ChatGPT OAuth 类上游仅验证 Chat 能力并将 Embedding 标记为跳过 | Codex |
| v1.1.44 | 2026-06-02 | 任务管理列表支持按所属产品和创建时间段筛选，AI 任务摘要返回产品名与时间字段 | Codex |
| v1.1.45 | 2026-06-02 | 所有 PostgreSQL 结构表统一补齐 `created_at` 和 `updated_at` 标准时间字段，并新增迁移门禁测试 | Codex |
| v1.1.46 | 2026-06-02 | 产品 Git 资源扩展 GitHub provider，支持 GitHub PR 预览、diff 快照和凭据解析 | Codex |
| v1.1.47 | 2026-06-02 | 新增 AI 助手聊天工作台和 `/api/assistant/chat`，基于系统上下文回答 AI Brain 配置与开发进展问题 | Codex |
| v1.1.48 | 2026-06-03 | 基于 AI 助手真实需求复跑补齐 GitHub PR 列表、产品详情、模型网关健康检查和失败任务重试能力 | Codex |
| v1.1.49 | 2026-06-03 | 基于 AI Brain GitHub PR 复跑补齐 code-review 外部命令缺失时复用模型网关的执行器策略，并强化模型网关 Review payload 与输出规范化 | Codex |
| v1.1.50 | 2026-06-03 | AI 助手聊天记录按用户级持久化，补齐会话列表、消息查询和结构表恢复契约 | Codex |
| v1.1.51 | 2026-06-03 | 知识索引新增文本兜底状态 `text_indexed` 和向量增强状态 `vector_indexed`，Embedding 不可用时仍支持关键词检索 | Codex |
| v1.1.52 | 2026-06-03 | 模型网关拆分 Chat 与 Embedding 能力，Embedding 可禁用、复用 Chat 或单独配置，检索按向量元数据判断兼容性 | Codex |
| v1.1.53 | 2026-06-03 | 需求新增支持不指定迭代版本，需求交付新增迭代版本管理入口，并将需求状态机扩展为需求池、排期、设计、开发、评审、测试、发布和验收流程 | Codex |
| v1.1.54 | 2026-06-03 | DB-first 迁移补齐任务运行态/Review/回写/导出 repository 读路径和 Mock Writeback handler 级写入约束 | Codex |
| v1.1.55 | 2026-06-03 | DB-first 迁移补齐知识沉淀候选列表 repository-first 读取和状态过滤约束 | Codex |
| v1.1.56 | 2026-06-03 | DB-first 迁移补齐知识检索 repository-first 候选查询、权限过滤和关键词下推约束 | Codex |
| v1.1.57 | 2026-06-03 | DB-first 迁移补齐知识沉淀审核写接口 repository 当前记录读取约束 | Codex |
| v1.1.58 | 2026-06-03 | DB-first 迁移补齐生命周期上下文 repository source rows 聚合和过渡读侧容器边界 | Codex |
| v1.1.59 | 2026-06-03 | DB-first 迁移补齐首页 IT 团队看板 repository source rows 聚合和单条 snapshot 写入边界 | Codex |
| v1.1.60 | 2026-06-03 | DB-first 迁移补齐任务/Review/导出 task workflow source rows 读取边界，减少 repository read snapshot 依赖 | Codex |
| v1.1.61 | 2026-06-03 | DB-first 迁移补齐任务启动、取消、补充信息和 Review 决策写路径的请求级 source rows 上下文边界 | Codex |
| v1.1.62 | 2026-06-03 | DB-first 迁移将 PostgreSQL 启动运行层切换为轻量 PostgresRuntimeStore repository 容器 | Codex |
| v1.1.63 | 2026-06-03 | DB-first 迁移补齐产品配置、需求/任务创建和 Bug 写路径在 PostgresRuntimeStore 空启动容器下的 source rows 上下文边界 | Codex |
| v1.1.64 | 2026-06-03 | DB-first 迁移补齐运营采集、用户洞察和迭代规划写路径在 PostgresRuntimeStore 空启动容器下的 source rows 上下文边界 | Codex |
| v1.1.65 | 2026-06-03 | DB-first 迁移补齐模型网关配置和 AI 助手聊天写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文边界 | Codex |
| v1.1.66 | 2026-06-03 | DB-first 迁移补齐知识文档和知识沉淀写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文边界 | Codex |
| v1.1.67 | 2026-06-03 | DB-first 迁移补齐 GitLab/GitHub PR/MR 预览、列表和快照写路径在 PostgresRuntimeStore 空启动容器下的 repository 上下文边界 | Codex |
| v1.1.68 | 2026-06-03 | DB-first 迁移移除生产 read snapshot 恢复 fallback，补齐业务大脑只读、知识沉淀驳回和 Mock Writeback 生成的 repository/source rows 边界 | Codex |
| v1.1.69 | 2026-06-03 | DB-first 迁移将生命周期上下文 source rows 从 MemoryStore 投影替换为专用 LifecycleContextReadModel | Codex |
| v1.1.70 | 2026-06-03 | DB-first 迁移明确只读缓存允许边界，并将产品配置、模型网关、助手、需求、任务创建和 Bug 写路径进一步收敛为直接 repository records/payloads | Codex |
| v1.1.71 | 2026-06-04 | 增加前端和用户可见流程提交前的真实网页界面验证门禁 | Codex |
| v1.1.72 | 2026-06-04 | 新增需求批量排期接口、需求管理批量排期入口和迭代版本页归集需求入口，并补齐审计规则 | Codex |
| v1.1.73 | 2026-06-04 | 真实网页验收发现 planning 迭代版本无法从需求页选择，修正为需求页读取未归档版本并以追加方式保存批次审计 | Codex |
| v1.1.74 | 2026-06-04 | 新增迭代版本状态推进能力，支持规划中、开发中、测试中、已发布主状态和需求状态同步预览/审计 | Codex |
| v1.1.75 | 2026-06-04 | 需求管理页新增迭代版本查询条件，基于需求列表版本投影过滤需求范围 | Codex |
| v1.1.76 | 2026-06-04 | Bug 管理列表新增迭代版本展示和查询条件，Bug 列表返回版本投影并支持版本过滤 | Codex |
| v1.1.77 | 2026-06-04 | 调整迭代版本开发中推进测试中规则，版本内已进入交付链路的需求统一同步到测试中 | Codex |
| v1.1.78 | 2026-06-04 | Bug 登记目标版本选择改为同产品未归档迭代版本，支持测试中和已发布版本缺陷归属 | Codex |
| v1.1.79 | 2026-06-04 | 用户洞察页面移除无操作的待归属使用/反馈只读区，待归属队列统一收口到研发运营处理入口 | Codex |
| v1.1.80 | 2026-06-04 | 前端日期/时间登记字段统一使用 Ant Design DatePicker，并保持 API 日期字符串契约 | Codex |
| v1.1.81 | 2026-06-04 | Bug 管理列表新增创建时间展示，便于按登记先后追踪缺陷 | Codex |
| v1.1.82 | 2026-06-04 | 需求管理列表时间列从更新时间调整为创建时间，便于按提交先后查看需求 | Codex |
| v1.1.83 | 2026-06-04 | 用户洞察列表固定列宽、操作列右侧固定并新增详情弹窗，避免长反馈内容撑开页面 | Codex |
| v1.1.84 | 2026-06-04 | 用户洞察和研发运营主列表改为统一服务端聚合接口分页、排序和筛选 | Codex |
| v1.1.85 | 2026-06-04 | 新增需求全链路详情读模型和需求管理页入口，按需求聚合研发全流程时间线 | Codex |
| v1.1.86 | 2026-06-04 | Bug 管理新增多选批量处理，支持批量更新状态、严重级别或处理人并写入批次审计 | Codex |
| v1.1.87 | 2026-06-05 | AI 助手上下文增强为可回答迭代进度、阻塞需求、待确认 Review、代码评审结论和 Bug 分布 | Codex |
| v1.1.88 | 2026-06-05 | GitLab MR / GitHub PR 预览增强为 Review 准备视图，提供 diff 文件树、风险摘要和 Review Checklist | Codex |
| v1.1.89 | 2026-06-05 | 需求全链路详情页展示 PR/MR 证据，包括快照风险摘要、diff 文件树和 Review Checklist | Codex |
| v1.1.90 | 2026-06-05 | 角色管理列表改为摘要化展示，职责、数据范围、限制边界和权限明细收口到详情弹窗 | Codex |
| v1.1.91 | 2026-06-05 | 需求管理新增批量生成任务入口和接口，同产品已排期需求可批量生成产品详细设计任务并记录批次审计 | Codex |
| v1.1.92 | 2026-06-05 | 需求全链路详情页新增阶段进度视图，按需求、迭代、任务、Review、PR/代码评审、Bug、发布和知识沉淀展示链路覆盖状态 | Codex |
| v1.1.93 | 2026-06-05 | 需求全链路新增可直达详情页路由，列表保留弹窗快查并提供详情页入口，便于刷新、分享和跨模块跳转 | Codex |
| v1.1.94 | 2026-06-05 | 用户洞察统一列表沉淀为 PostgreSQL SQL read model，并补充排序过滤索引 | Codex |
| v1.1.95 | 2026-06-05 | 需求全链路详情弹窗摘要和阶段进度改为响应式布局，阶段与时间线状态展示中文业务状态，避免长标题或版本名撑宽裁切 | Codex |
| v1.1.96 | 2026-06-05 | 研发运营统一列表沉淀为 PostgreSQL SQL read model，并补充排序过滤索引 | Codex |
| v1.1.97 | 2026-06-05 | 明确团队看板可基于 PostgreSQL source rows 进行 Python 聚合，管理列表必须优先 SQL/read model 分页排序筛选 | Codex |
| v1.1.99 | 2026-06-05 | 需求管理和 Bug 管理列表在 PostgreSQL 运行时切换为 SQL read model，筛选、排序和分页在数据库层完成 | Codex |
| v1.1.100 | 2026-06-05 | 产品管理和迭代版本列表在 PostgreSQL 运行时切换为 SQL read model，筛选、排序和分页在数据库层完成 | Codex |

---
