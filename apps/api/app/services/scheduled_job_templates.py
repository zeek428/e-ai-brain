from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.api.deps import require_roles
from app.services.ai_executor_runners import (
    SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
)

STANDARD_WIZARD_STEPS = [
    {
        "description": "选择数据连接和执行模板，负责获取原始输入数据。",
        "key": "data_connection",
        "required": True,
        "title": "数据连接",
    },
    {
        "description": "选择 AI 模型、Agent、Skill；无 Skill 时不会调用大模型。",
        "key": "ai_processing",
        "required": False,
        "title": "AI 处理",
    },
    {
        "description": "按需引用知识文档，作为 AI 处理前置上下文。",
        "key": "knowledge_reference",
        "required": False,
        "title": "知识引用",
    },
    {
        "description": "选择写入目标、通知渠道或治理闭环动作。",
        "key": "result_write",
        "required": True,
        "title": "结果写入",
    },
    {
        "description": "配置手动、Cron 或固定间隔触发。",
        "key": "schedule",
        "required": True,
        "title": "调度",
    },
]

STANDARD_SCHEDULED_JOB_TEMPLATES = [
    {
        "category": "insights",
        "code": "weekly_feedback_insight",
        "description": "每周从数据仓库拉取用户反馈，经 AI/Skill 分析后写入用户洞察表。",
        "name": "每周用户反馈洞察抽取",
        "payload_defaults": {
            "cron_expression": "0 9 * * MON",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "user_feedback_insight_extract",
            "name": "每周用户反馈洞察抽取",
            "plugin_input_mapping": {
                "week_end": "{{last_full_week.end}}",
                "week_start": "{{last_full_week.start}}",
            },
            "result_actions": [],
            "schedule_type": "cron",
            "source_system": "aliyun-maxcompute",
        },
        "recommended_scenarios": ["用户反馈洞察", "周度用户声音复盘", "产品体验问题发现"],
        "resource_selectors": {
            "agent": {"strategy": "first_active"},
            "knowledge_document": {"strategy": "first_indexed_optional"},
            "model_gateway_config": {"strategy": "default_or_first_active"},
            "plugin_action": {"code_candidates": ["fetch_weekly_user_feedback"]},
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
            "skill": {"strategy": "first_active"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "governance",
        "code": "code_repository_inspection",
        "description": "定期 clone 产品 Git 仓库并扫描质量、安全和规范问题，写入代码巡检报告。",
        "name": "代码仓库质量 / 安全 / 规范巡检",
        "payload_defaults": {
            "config_json": {
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "cron_expression": "0 2 * * MON",
            "enabled": True,
            "execution_mode": "ai_assisted",
            "job_type": "code_repository_inspection",
            "knowledge_document_ids": [],
            "name": "代码仓库质量安全规范巡检",
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {
                    "severity_threshold": "critical",
                    "type": "create_bug_for_severe_findings",
                },
                {
                    "severity_threshold": "high",
                    "type": "create_task_for_severe_findings",
                },
                {"channels": ["email"], "recipients": [], "type": "send_notification"},
            ],
            "schedule_type": "cron",
            "skill_ids": [],
            "source_system": "code-inspection",
        },
        "recommended_scenarios": ["本地完整代码扫描", "安全漏洞扫描", "研发规范治理"],
        "resource_selectors": {
            "agent": {
                "code_candidates": ["code-reviewer"],
                "fallback_code_candidates": ["code_reviewer", "code_inspection_agent"],
                "text_candidates": ["代码审查", "代码巡检", "code review", "code inspection"],
            },
            "model_gateway_config": {"strategy": "default_or_first_active"},
            "plugin_action": {
                "code_candidates": [
                    "scan_github_code_inspection",
                    "scan_gitlab_code_inspection",
                ],
                "text_candidates": ["code_inspection", "代码巡检"],
            },
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
            "skill": {
                "code_candidates": ["code_analysis_skill"],
                "fallback_code_candidates": ["code_inspection_analysis", "code_review"],
                "text_candidates": [
                    "代码分析skill",
                    "代码分析",
                    "代码巡检",
                    "代码审查",
                    "code inspection",
                    "code review",
                ],
            },
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "collaboration",
        "code": "email_digest",
        "description": "定期从邮箱收取邮件，后续可交给 AI 汇总摘要或直接归档运行结果。",
        "name": "邮件摘要收取",
        "payload_defaults": {
            "cron_expression": "0 8 * * MON-FRI",
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "每日邮件摘要收取",
            "plugin_input_mapping": {
                "poll_since": "{{current_date-1}}",
            },
            "result_actions": [],
            "schedule_type": "cron",
            "source_system": "email",
        },
        "recommended_scenarios": ["邮件摘要", "邮件工单收取", "业务反馈收取"],
        "resource_selectors": {
            "plugin_action": {"code_candidates": ["receive_email_messages"]},
            "plugin_connection": {"strategy": "same_plugin_as_action"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "operations",
        "code": "online_log_anomaly_analysis",
        "description": "按时间窗口读取线上日志指标，经 AI/Skill 分析异常并生成处置建议或通知。",
        "name": "线上日志异常分析",
        "payload_defaults": {
            "cron_expression": "*/30 * * * *",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "online_log_ai_analysis",
            "knowledge_document_ids": [],
            "name": "线上日志异常分析",
            "plugin_input_mapping": {
                "window_end": "{{now}}",
                "window_start": "{{current_date}}",
            },
            "result_actions": [
                {"channels": ["email"], "recipients": [], "type": "send_notification"},
            ],
            "schedule_type": "cron",
            "source_system": "online-log",
        },
        "recommended_scenarios": ["线上日志异常发现", "错误率突增分析", "生产告警复盘"],
        "resource_selectors": {
            "agent": {"strategy": "first_active"},
            "knowledge_document": {"strategy": "first_indexed_optional"},
            "model_gateway_config": {"strategy": "default_or_first_active"},
            "plugin_action": {
                "code_candidates": [
                    "query_online_log_metrics",
                    "fetch_online_log_metrics",
                    "collect_online_log_metrics",
                ],
                "text_candidates": ["online_log", "log_anomaly", "线上日志", "日志异常"],
            },
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
            "skill": {"strategy": "first_active"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "governance",
        "code": "gitlab_mr_review",
        "description": "读取 GitLab MR 或项目扫描数据，经 AI 复核后写入代码巡检报告。",
        "name": "GitLab MR AI 审查",
        "payload_defaults": {
            "cron_expression": "0 */4 * * *",
            "enabled": True,
            "execution_mode": "ai_assisted",
            "job_type": "code_repository_inspection",
            "knowledge_document_ids": [],
            "name": "GitLab MR AI 审查",
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {"severity_threshold": "critical", "type": "create_bug_for_severe_findings"},
                {"severity_threshold": "high", "type": "create_task_for_severe_findings"},
            ],
            "schedule_type": "cron",
            "skill_ids": [],
            "source_system": "gitlab",
        },
        "recommended_scenarios": ["GitLab MR 审查", "代码规范复核", "安全变更巡检"],
        "resource_selectors": {
            "agent": {"strategy": "first_active"},
            "model_gateway_config": {"strategy": "default_or_first_active"},
            "plugin_action": {"code_candidates": ["scan_gitlab_code_inspection"]},
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
            "skill": {"strategy": "first_active"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "ai_service",
        "code": "ai_executor_repository_task",
        "description": (
            "默认使用系统默认 AI 大模型执行仓库任务，也可切换到本地 "
            "Codex、Claude、Hermes 或 OpenClaw Runner 并回写结果。"
        ),
        "name": "AI 执行器仓库任务",
        "payload_defaults": {
            "config_json": {
                "ai_executor": {
                    "executor_type": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
                    "runner_id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
                    "runner_label": "系统默认执行器",
                },
            },
            "cron_expression": "0 3 * * MON",
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "plugin_action_invoke",
            "name": "AI 执行器仓库巡检",
            "result_actions": [],
            "schedule_type": "cron",
            "source_system": "ai_executor",
        },
        "recommended_scenarios": [
            "系统默认执行器",
            "系统 AI 大模型仓库分析",
            "本地 Codex/OpenClaw Runner",
        ],
        "resource_selectors": {
            "plugin_action": {"code_candidates": ["run_ai_executor_instruction"]},
            "plugin_connection": {"strategy": "same_plugin_as_action"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "insights",
        "code": "internal_business_weekly_insight",
        "description": (
            "每周读取内部用户洞察、需求、产品和 Bug 数据，"
            "经 AI/Skill 分析后保存运行结果或写入业务目标。"
        ),
        "name": "每周内部业务洞察分析",
        "payload_defaults": {
            "cron_expression": "0 9 * * MON",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "plugin_action_invoke",
            "name": "每周内部业务洞察分析",
            "plugin_input_mapping": {
                "source_types": ["user_insights", "requirements", "products", "bugs"],
                "window_end": "{{last_full_week.end}}",
                "window_start": "{{last_full_week.start}}",
            },
            "result_actions": [{"type": "save_scheduled_job_result"}],
            "schedule_type": "cron",
            "source_system": "internal_data_source",
        },
        "recommended_scenarios": ["内部经营复盘", "产品与交付风险汇总", "周度 AI 分析简报"],
        "resource_selectors": {
            "agent": {"strategy": "first_active"},
            "knowledge_document": {"strategy": "first_indexed_optional"},
            "model_gateway_config": {"strategy": "default_or_first_active"},
            "plugin_action": {"code_candidates": ["query_internal_business_data"]},
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
            "skill": {"strategy": "first_active"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "governance",
        "code": "requirement_bug_risk_analysis",
        "description": "定期读取需求和 Bug 数据，经 AI 分析识别延期、阻塞和质量风险。",
        "name": "需求与 Bug 风险分析",
        "payload_defaults": {
            "cron_expression": "0 10 * * MON",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "plugin_action_invoke",
            "name": "需求与 Bug 风险分析",
            "plugin_input_mapping": {
                "source_types": ["requirements", "bugs"],
                "window_end": "{{now}}",
                "window_start": "{{current_date-14}}",
            },
            "result_actions": [{"type": "save_scheduled_job_result"}],
            "schedule_type": "cron",
            "source_system": "internal_data_source",
        },
        "recommended_scenarios": ["版本风险巡检", "需求延期预警", "质量阻塞分析"],
        "resource_selectors": {
            "agent": {"strategy": "first_active"},
            "model_gateway_config": {"strategy": "default_or_first_active"},
            "plugin_action": {"code_candidates": ["query_internal_business_data"]},
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
            "skill": {"strategy": "first_active"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "insights",
        "code": "user_insight_requirement_mining",
        "description": "读取用户洞察和现有需求，经 AI 判断可转化的需求机会并保存分析结果。",
        "name": "用户洞察需求机会挖掘",
        "payload_defaults": {
            "cron_expression": "0 11 * * MON",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "plugin_action_invoke",
            "name": "用户洞察需求机会挖掘",
            "plugin_input_mapping": {
                "source_types": ["user_insights", "requirements"],
                "window_end": "{{now}}",
                "window_start": "{{current_date-30}}",
            },
            "result_actions": [{"type": "save_scheduled_job_result"}],
            "schedule_type": "cron",
            "source_system": "internal_data_source",
        },
        "recommended_scenarios": ["用户反馈转需求", "需求池补充", "高价值洞察提取"],
        "resource_selectors": {
            "agent": {"strategy": "first_active"},
            "knowledge_document": {"strategy": "first_indexed_optional"},
            "model_gateway_config": {"strategy": "default_or_first_active"},
            "plugin_action": {"code_candidates": ["query_internal_business_data"]},
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
            "skill": {"strategy": "first_active"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
    {
        "category": "insights",
        "code": "product_feedback_trend_analysis",
        "description": "读取产品、用户洞察和 Bug 数据，经 AI 分析产品体验趋势和重点改进方向。",
        "name": "产品反馈趋势分析",
        "payload_defaults": {
            "cron_expression": "0 14 * * FRI",
            "enabled": True,
            "execution_mode": "ai_generated",
            "job_type": "plugin_action_invoke",
            "name": "产品反馈趋势分析",
            "plugin_input_mapping": {
                "source_types": ["products", "user_insights", "bugs"],
                "window_end": "{{now}}",
                "window_start": "{{current_date-30}}",
            },
            "result_actions": [{"type": "save_scheduled_job_result"}],
            "schedule_type": "cron",
            "source_system": "internal_data_source",
        },
        "recommended_scenarios": ["产品体验趋势", "反馈与缺陷关联分析", "月度产品复盘"],
        "resource_selectors": {
            "agent": {"strategy": "first_active"},
            "knowledge_document": {"strategy": "first_indexed_optional"},
            "model_gateway_config": {"strategy": "default_or_first_active"},
            "plugin_action": {"code_candidates": ["query_internal_business_data"]},
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
            "skill": {"strategy": "first_active"},
        },
        "template_version": "v1",
        "wizard_steps": STANDARD_WIZARD_STEPS,
    },
]


def standard_scheduled_job_templates() -> list[dict[str, Any]]:
    return deepcopy(STANDARD_SCHEDULED_JOB_TEMPLATES)


def scheduled_job_template_by_code(code: str | None) -> dict[str, Any] | None:
    normalized = str(code or "")
    for template in STANDARD_SCHEDULED_JOB_TEMPLATES:
        if template["code"] == normalized:
            return deepcopy(template)
    return None


def list_scheduled_job_templates_response(
    *,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"admin"})
    items = []
    for template in standard_scheduled_job_templates():
        items.append(
            {
                **template,
                "available_resource_counts": _scheduled_template_resource_counts(
                    current_store,
                    template,
                ),
                "installed": True,
                "publisher": "AI Brain 官方",
            },
        )
    items.sort(key=lambda item: (str(item.get("category")), str(item.get("code"))))
    return {"items": items, "total": len(items)}


def _scheduled_template_resource_counts(
    current_store: Any,
    template: dict[str, Any],
) -> dict[str, int]:
    selectors = template.get("resource_selectors") or {}
    plugin_action_selector = selectors.get("plugin_action") or {}
    action_candidates = set(plugin_action_selector.get("code_candidates") or [])
    text_candidates = [
        str(candidate).lower()
        for candidate in plugin_action_selector.get("text_candidates") or []
    ]
    matching_actions = [
        action
        for action in getattr(current_store, "plugin_actions", {}).values()
        if (
            action.get("code") in action_candidates
            or any(
                candidate in f"{action.get('code') or ''} {action.get('name') or ''}".lower()
                for candidate in text_candidates
            )
        )
    ]
    matching_plugin_ids = {action.get("plugin_id") for action in matching_actions}
    matching_connections = [
        connection
        for connection in getattr(current_store, "plugin_connections", {}).values()
        if connection.get("plugin_id") in matching_plugin_ids
    ]
    return {
        "active_agent_count": len(
            [
                agent
                for agent in getattr(current_store, "ai_agents", {}).values()
                if agent.get("status") == "active"
            ],
        ),
        "active_plugin_action_count": len(
            [action for action in matching_actions if action.get("status") == "active"],
        ),
        "active_plugin_connection_count": len(
            [
                connection
                for connection in matching_connections
                if connection.get("status") == "active"
            ],
        ),
        "active_product_count": len(
            [
                product
                for product in getattr(current_store, "products", {}).values()
                if product.get("status") == "active"
            ],
        ),
        "active_skill_count": len(
            [
                skill
                for skill in getattr(current_store, "ai_skills", {}).values()
                if skill.get("status") == "active"
            ],
        ),
    }
