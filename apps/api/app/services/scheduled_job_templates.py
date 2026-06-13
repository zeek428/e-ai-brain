from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.api.deps import require_roles

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
    },
    {
        "category": "governance",
        "code": "code_repository_inspection",
        "description": "定期扫描 GitHub/GitLab 仓库质量、安全和规范问题，写入代码巡检报告。",
        "name": "代码仓库质量 / 安全 / 规范巡检",
        "payload_defaults": {
            "cron_expression": "0 2 * * MON",
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "knowledge_document_ids": [],
            "name": "代码仓库质量安全规范巡检",
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {
                    "severity_threshold": "critical",
                    "type": "create_bug_for_severe_findings",
                },
                {"channels": ["email"], "recipients": [], "type": "send_notification"},
            ],
            "schedule_type": "cron",
            "skill_ids": [],
            "source_system": "code-inspection",
        },
        "recommended_scenarios": ["代码质量巡检", "安全漏洞扫描", "研发规范治理"],
        "resource_selectors": {
            "plugin_action": {
                "code_candidates": [
                    "scan_github_code_inspection",
                    "scan_gitlab_code_inspection",
                ],
                "text_candidates": ["code_inspection", "代码巡检"],
            },
            "plugin_connection": {"strategy": "same_plugin_as_action"},
            "product": {"strategy": "first_active"},
        },
        "template_version": "v1",
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
