from __future__ import annotations

from copy import deepcopy
from typing import Any

ASSISTANT_DRAFT_WIZARD_STEPS = [
    "数据来源",
    "AI处理",
    "知识引用",
    "结果动作",
    "调度策略",
    "确认执行",
]

STANDARD_ASSISTANT_DRAFT_TEMPLATES = [
    {
        "available": True,
        "category": "insights",
        "code": "weekly_feedback_insight",
        "dependencies": ["用户反馈数据连接", "反馈洞察 Skill", "用户洞察写入动作"],
        "description": "按周提取用户反馈高价值信息，生成可确认的定时作业草案。",
        "draft_action": "create_scheduled_job",
        "name": "周反馈洞察",
        "prompt": (
            "请帮我生成每周用户反馈洞察定时作业草案，配置数据来源、AI处理、"
            "结果动作和调度策略，并在确认后执行一次。"
        ),
        "roles": ["product_owner", "admin"],
        "source_module": "用户洞察",
        "target_resource": "scheduled_job",
        "template_version": "v1",
        "wizard_steps": ASSISTANT_DRAFT_WIZARD_STEPS,
    },
    {
        "available": True,
        "category": "governance",
        "code": "code_inspection",
        "dependencies": ["GitHub/GitLab 连接", "代码巡检动作", "代码巡检报告写入"],
        "description": "围绕仓库质量、安全和规范扫描，生成代码巡检任务草案。",
        "draft_action": "create_scheduled_job",
        "name": "代码巡检",
        "prompt": (
            "请帮我生成代码巡检定时作业草案，按数据连接、AI处理、结果动作、"
            "调度策略展示依赖关系。"
        ),
        "roles": ["rd_owner", "admin"],
        "source_module": "代码巡检",
        "target_resource": "scheduled_job",
        "template_version": "v1",
        "wizard_steps": ASSISTANT_DRAFT_WIZARD_STEPS,
    },
    {
        "available": True,
        "category": "collaboration",
        "code": "email_digest",
        "dependencies": ["邮箱连接", "邮件收取动作", "摘要处理 Skill"],
        "description": "从邮箱收取消息并生成摘要，适合周报、工单和业务反馈归档。",
        "draft_action": "create_scheduled_job",
        "name": "邮件摘要",
        "prompt": (
            "请帮我生成邮件摘要收取定时作业草案，先检查邮箱连接和邮件收取动作，"
            "再给出确认前字段校验。"
        ),
        "roles": ["admin", "product_owner", "reviewer"],
        "source_module": "插件管理",
        "target_resource": "scheduled_job",
        "template_version": "v1",
        "wizard_steps": ASSISTANT_DRAFT_WIZARD_STEPS,
    },
    {
        "available": True,
        "category": "release",
        "code": "release_risk_analysis",
        "dependencies": ["发布记录", "缺陷列表", "测试结论", "需求状态"],
        "description": "汇总发布、缺陷、测试和需求上下文，生成发布风险分析草案。",
        "draft_action": "create_analysis_draft",
        "name": "发布风险分析",
        "prompt": (
            "请基于当前发布记录、未关闭缺陷、测试结论和需求状态生成发布风险分析草案，"
            "并标出需要人工确认的风险项。"
        ),
        "roles": ["product_owner", "reviewer", "test_owner", "tester", "release_owner"],
        "source_module": "发布治理",
        "target_resource": "assistant_analysis",
        "template_version": "v1",
        "wizard_steps": ASSISTANT_DRAFT_WIZARD_STEPS,
    },
    {
        "available": True,
        "category": "knowledge",
        "code": "knowledge_base_inspection",
        "dependencies": ["知识空间", "知识文档索引", "知识沉淀候选"],
        "description": "检查知识库索引、权限、过期文档和沉淀候选，生成治理草案。",
        "draft_action": "create_analysis_draft",
        "name": "知识库巡检",
        "prompt": (
            "请生成知识库巡检草案，检查索引失败、权限异常、过期知识和待处理知识沉淀，"
            "并给出可执行修复建议。"
        ),
        "roles": ["knowledge_owner", "admin"],
        "source_module": "知识库",
        "target_resource": "assistant_analysis",
        "template_version": "v1",
        "wizard_steps": ASSISTANT_DRAFT_WIZARD_STEPS,
    },
    {
        "available": True,
        "category": "operations",
        "code": "online_log_anomaly_analysis",
        "dependencies": ["线上日志采集", "异常检测 Skill", "告警结果动作"],
        "description": "面向线上日志异常发现和处置建议，生成可确认的定时作业草案。",
        "draft_action": "create_scheduled_job",
        "name": "线上日志异常分析",
        "prompt": (
            "请生成线上日志异常分析定时作业草案，说明需要的数据连接、AI处理、"
            "结果动作和调度策略。"
        ),
        "roles": ["admin", "rd_owner"],
        "source_module": "运行数据",
        "target_resource": "scheduled_job",
        "template_version": "v1",
        "wizard_steps": ASSISTANT_DRAFT_WIZARD_STEPS,
    },
]


def standard_assistant_draft_templates() -> list[dict[str, Any]]:
    return deepcopy(STANDARD_ASSISTANT_DRAFT_TEMPLATES)


def list_assistant_draft_templates_response(*, user: dict[str, Any]) -> dict[str, Any]:
    user_roles = set(user.get("roles") or [])
    templates = []
    for template in standard_assistant_draft_templates():
        template_roles = set(template.get("roles") or [])
        if (
            "admin" not in user_roles
            and template_roles
            and not user_roles.intersection(template_roles)
        ):
            continue
        templates.append(template)
    templates.sort(key=lambda item: (str(item.get("category")), str(item.get("code"))))
    return {"items": templates, "total": len(templates)}
