from __future__ import annotations

from copy import deepcopy
from typing import Any

STANDARD_ASSISTANT_ROLE_QUICK_TASK_GROUPS = [
    {
        "enabled": True,
        "key": "product",
        "label": "产品快捷任务",
        "roles": ["product_owner"],
        "sort_order": 10,
        "tasks": [
            {
                "analytics_key": "product.requirement_progress",
                "enabled": True,
                "key": "requirement_progress",
                "label": "需求进展",
                "permissions": [],
                "prompt": "请按产品视角总结当前需求进展、阻塞和下一步推进建议。",
                "sort_order": 10,
                "target_draft_type": None,
            },
            {
                "analytics_key": "product.feedback_insights",
                "enabled": True,
                "key": "feedback_insights",
                "label": "反馈洞察",
                "permissions": ["system.scheduled_jobs.manage"],
                "prompt": (
                    "请帮我生成每周用户反馈洞察定时作业草案，"
                    "并说明数据来源、AI处理、结果动作和调度策略。"
                ),
                "sort_order": 20,
                "target_draft_type": "create_scheduled_job",
            },
            {
                "analytics_key": "product.version_risk",
                "enabled": True,
                "key": "version_risk",
                "label": "版本风险",
                "permissions": [],
                "prompt": (
                    "请生成发布风险分析草案，"
                    "基于需求、缺陷、发布记录和用户反馈评估当前版本风险。"
                ),
                "sort_order": 30,
                "target_draft_type": "create_analysis_draft",
            },
        ],
    },
    {
        "enabled": True,
        "key": "engineering",
        "label": "研发快捷任务",
        "roles": ["rd_owner"],
        "sort_order": 20,
        "tasks": [
            {
                "analytics_key": "engineering.task_blockers",
                "enabled": True,
                "key": "task_blockers",
                "label": "任务阻塞",
                "permissions": [],
                "prompt": "请列出当前研发任务阻塞、待确认项和建议处理顺序。",
                "sort_order": 10,
                "target_draft_type": None,
            },
            {
                "analytics_key": "engineering.code_inspection",
                "enabled": True,
                "key": "code_inspection",
                "label": "代码巡检",
                "permissions": ["system.scheduled_jobs.manage"],
                "prompt": (
                    "请帮我生成或检查代码巡检任务草案，"
                    "并说明数据连接、AI处理和结果动作依赖。"
                ),
                "sort_order": 20,
                "target_draft_type": "create_scheduled_job",
            },
            {
                "analytics_key": "engineering.defect_fix",
                "enabled": True,
                "key": "defect_fix",
                "label": "缺陷修复",
                "permissions": [],
                "prompt": "请按严重度梳理待修复缺陷，给出修复优先级和关联需求/任务。",
                "sort_order": 30,
                "target_draft_type": None,
            },
        ],
    },
    {
        "enabled": True,
        "key": "testing",
        "label": "测试快捷任务",
        "roles": ["reviewer", "test_owner", "tester", "release_owner"],
        "sort_order": 30,
        "tasks": [
            {
                "analytics_key": "testing.test_defects",
                "enabled": True,
                "key": "test_defects",
                "label": "测试缺陷",
                "permissions": [],
                "prompt": "请汇总当前测试缺陷、复现状态、阻塞发布的问题和建议责任归属。",
                "sort_order": 10,
                "target_draft_type": None,
            },
            {
                "analytics_key": "testing.automated_tests",
                "enabled": True,
                "key": "automated_tests",
                "label": "自动化测试",
                "permissions": [],
                "prompt": "请检查自动化测试相关任务、失败原因和可生成的测试草案。",
                "sort_order": 20,
                "target_draft_type": "create_rd_task",
            },
            {
                "analytics_key": "testing.release_risk",
                "enabled": True,
                "key": "release_risk",
                "label": "发布风险",
                "permissions": [],
                "prompt": (
                    "请生成发布风险分析草案，"
                    "基于测试结果、未关闭缺陷和发布记录评估当前发布风险。"
                ),
                "sort_order": 30,
                "target_draft_type": "create_analysis_draft",
            },
        ],
    },
    {
        "enabled": True,
        "key": "knowledge",
        "label": "知识快捷任务",
        "roles": ["knowledge_owner"],
        "sort_order": 40,
        "tasks": [
            {
                "analytics_key": "knowledge.knowledge_base_inspection",
                "enabled": True,
                "key": "knowledge_base_inspection",
                "label": "知识库巡检",
                "permissions": [],
                "prompt": (
                    "请生成知识库巡检草案，"
                    "检查索引失败、权限异常、过期知识和待处理知识沉淀。"
                ),
                "sort_order": 10,
                "target_draft_type": "create_analysis_draft",
            },
            {
                "analytics_key": "knowledge.knowledge_deposits",
                "enabled": True,
                "key": "knowledge_deposits",
                "label": "知识沉淀",
                "permissions": [],
                "prompt": "请汇总待处理知识沉淀候选，按来源任务、价值和风险给出处理优先级。",
                "sort_order": 20,
                "target_draft_type": None,
            },
            {
                "analytics_key": "knowledge.knowledge_permissions",
                "enabled": True,
                "key": "knowledge_permissions",
                "label": "知识权限",
                "permissions": [],
                "prompt": "请检查知识空间、目录和文档的权限风险，指出需要调整或复核的对象。",
                "sort_order": 30,
                "target_draft_type": None,
            },
        ],
    },
    {
        "enabled": True,
        "key": "admin",
        "label": "管理员快捷任务",
        "roles": ["admin"],
        "sort_order": 50,
        "tasks": [
            {
                "analytics_key": "admin.plugin_connections",
                "enabled": True,
                "key": "plugin_connections",
                "label": "插件连接",
                "permissions": ["system.plugins.manage"],
                "prompt": "请检查插件连接配置状态，指出失败连接和可生成的连接草案。",
                "sort_order": 10,
                "target_draft_type": "create_plugin_connection",
            },
            {
                "analytics_key": "admin.ai_capabilities",
                "enabled": True,
                "key": "ai_capabilities",
                "label": "AI能力",
                "permissions": ["system.ai_capabilities.manage"],
                "prompt": "我要新增 AI能力配置",
                "sort_order": 20,
                "target_draft_type": "create_ai_skill",
            },
            {
                "analytics_key": "admin.scheduled_jobs",
                "enabled": True,
                "key": "scheduled_jobs",
                "label": "定时作业",
                "permissions": ["system.scheduled_jobs.manage"],
                "prompt": "请汇总定时作业配置、运行健康和需要补齐的依赖。",
                "sort_order": 30,
                "target_draft_type": "create_scheduled_job",
            },
            {
                "analytics_key": "admin.run_failures",
                "enabled": True,
                "key": "run_failures",
                "label": "运行失败",
                "permissions": ["system.scheduled_jobs.run"],
                "prompt": (
                    "请诊断最近失败的定时作业运行，"
                    "按数据连接、AI处理、结果动作给出原因和修复建议。"
                ),
                "sort_order": 40,
                "target_draft_type": "repair_scheduled_job_run",
            },
        ],
    },
]


def list_assistant_role_quick_tasks_response(*, user: dict[str, Any]) -> dict[str, Any]:
    user_roles = set(user.get("roles") or [])
    user_permissions = set(user.get("permissions") or [])
    is_admin = "admin" in user_roles
    groups: list[dict[str, Any]] = []
    for group in deepcopy(STANDARD_ASSISTANT_ROLE_QUICK_TASK_GROUPS):
        if not group.get("enabled", True):
            continue
        group_roles = set(group.get("roles") or [])
        if not is_admin and group_roles and not user_roles.intersection(group_roles):
            continue
        tasks = []
        for task in group.get("tasks") or []:
            if not task.get("enabled", True):
                continue
            permissions = set(task.get("permissions") or [])
            if not is_admin and permissions and not permissions.issubset(user_permissions):
                continue
            tasks.append(task)
        if not tasks:
            continue
        group["tasks"] = sorted(tasks, key=lambda item: int(item.get("sort_order") or 0))
        groups.append(group)
    groups.sort(key=lambda item: int(item.get("sort_order") or 0))
    return {"items": groups, "total": len(groups)}
