from __future__ import annotations

ASSISTANT_ACTION_QUERY_TRIGGERS = (
    "新建",
    "新增",
    "创建",
    "我要建",
    "配置",
    "诊断",
    "排查",
    "指标",
    "效果",
    "失败",
)

ASSISTANT_ACTION_CANDIDATES = (
    {
        "action": "create_requirement",
        "aliases": ("新建", "新增", "创建", "需求", "requirement"),
        "id": "create_requirement",
        "prompt": (
            "我要新建需求，请帮我梳理标题、背景、目标、优先级、"
            "产品和版本，并生成可提交的需求草案。"
        ),
        "roles": ("admin", "product_owner", "rd_owner"),
        "summary": "进入需求交付的新建需求流程，先整理需求草案字段。",
        "title": "新建需求",
        "url": "/delivery/requirements",
    },
    {
        "action": "create_bug",
        "aliases": ("新建", "新增", "创建", "bug", "缺陷", "问题"),
        "id": "create_bug",
        "prompt": (
            "我要新建 Bug，请帮我整理标题、复现步骤、严重级别、影响范围、"
            "关联需求或任务，并生成 Bug 登记草案。"
        ),
        "roles": (
            "admin",
            "rd_owner",
            "reviewer",
            "test_owner",
            "tester",
            "release_owner",
        ),
        "summary": "进入 Bug 登记流程，先整理复现步骤、严重级别和证据。",
        "title": "新建 Bug",
        "url": "/delivery/bugs",
    },
    {
        "action": "create_plugin_connection",
        "aliases": ("新建", "新增", "创建", "插件", "插件连接", "连接", "plugin"),
        "id": "create_plugin_connection",
        "permissions": ("system.plugins.manage",),
        "prompt": "请帮我生成插件连接草案，先确认插件类型、Endpoint、认证方式、环境和必填参数。",
        "summary": "生成可确认的插件连接草案。",
        "title": "新建插件连接",
        "url": "/tasks/plugins",
    },
    {
        "action": "create_plugin_action",
        "aliases": ("新建", "新增", "创建", "插件", "插件动作", "动作", "plugin action"),
        "id": "create_plugin_action",
        "permissions": ("system.plugins.manage",),
        "prompt": (
            "请帮我生成动作草案，先确认连接、请求方法、路径、"
            "参数映射和结果写入目标。"
        ),
        "summary": "生成可确认的动作草案。",
        "title": "新建动作",
        "url": "/tasks/plugins",
    },
    {
        "action": "create_scheduled_job",
        "aliases": (
            "新建",
            "新增",
            "创建",
            "定时作业",
            "定时任务",
            "任务",
            "作业",
            "scheduled job",
        ),
        "id": "create_scheduled_job",
        "permissions": ("system.scheduled_jobs.manage",),
        "prompt": "请帮我生成定时作业配置草案，并说明数据来源、AI处理、结果动作和调度策略。",
        "summary": "生成可确认的定时作业草案。",
        "title": "新建定时作业",
        "url": "/tasks/scheduled-jobs",
    },
    {
        "action": "create_knowledge_document",
        "aliases": ("新建", "新增", "创建", "知识", "知识文档", "导入", "导入任务", "knowledge"),
        "id": "create_knowledge_document",
        "prompt": (
            "我要新建知识文档或导入任务，请帮我确认知识空间、目录、"
            "来源文件、权限和索引策略。"
        ),
        "roles": ("admin", "knowledge_owner"),
        "summary": "进入知识文档或导入任务创建流程，先整理空间、目录、权限和索引策略。",
        "title": "新建知识文档/导入任务",
        "url": "/assets/knowledge",
    },
    {
        "action": "create_ai_capability",
        "aliases": ("新建", "新增", "创建", "ai能力", "ai 能力", "skill", "ai角色", "角色"),
        "id": "create_ai_capability",
        "permissions": ("system.ai_capabilities.manage",),
        "prompt": "我要新增 AI能力配置，请帮我选择创建 Skill 或 AI角色，并生成可确认的配置草案。",
        "summary": "进入 AI 能力配置向导，生成 Skill 或 AI角色草案。",
        "title": "新建 AI 能力配置",
        "url": "/tasks/ai-capabilities",
    },
    {
        "action": "diagnose_scheduled_job_run",
        "aliases": ("诊断", "排查", "失败", "运行失败", "定时作业", "定时任务", "run diagnostic"),
        "id": "diagnose_scheduled_job_run",
        "permissions": ("system.scheduled_jobs.manage", "system.scheduled_jobs.run"),
        "prompt": "请诊断最近失败的定时作业运行，并按数据连接、AI处理、结果动作说明原因。",
        "summary": "读取定时作业运行、插件调用、模型日志和结果写入记录，解释失败原因。",
        "title": "运行诊断",
        "url": "/tasks/scheduled-jobs?tab=runs",
    },
    {
        "action": "explain_assistant_metrics",
        "aliases": ("指标", "效果", "漏斗", "采纳率", "修复率", "metrics"),
        "id": "explain_assistant_metrics",
        "prompt": (
            "请解释当前 AI 助手效果指标，包括草案采纳、引用使用、"
            "作业运行成功率和失败修复率。"
        ),
        "summary": "汇总 AI 助手草案、引用、运行和失败修复指标。",
        "title": "指标解释",
        "url": "/assistant",
    },
)

ASSISTANT_ACTION_STANDARD_SORT_STEP = 10
ASSISTANT_ACTION_REFERENCE_CONFIG_LIST_NAME = "assistant_action_reference_configs"
ASSISTANT_ACTION_REFERENCE_CONFIG_SORT_FIELDS = {
    "action_key",
    "created_at",
    "enabled",
    "enterprise_id",
    "sort_order",
    "template_version",
    "title",
    "updated_at",
}
ASSISTANT_ACTION_REFERENCE_CONFIG_STATUSES = {"disabled", "enabled"}
