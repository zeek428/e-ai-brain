from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.result_write_targets import result_write_target_default_mapping

STANDARD_PLUGINS = [
    {
        "category": "devops",
        "code": "gitlab",
        "description": (
            "官方标准 GitLab 插件，用于连接 GitLab API、读取项目、分支、"
            "提交、MR 和代码质量数据。"
        ),
        "id": "plugin_standard_gitlab",
        "is_system": True,
        "name": "GitLab",
        "protocol": "http",
        "risk_level": "medium",
        "status": "active",
    },
    {
        "category": "devops",
        "code": "github",
        "description": (
            "官方标准 GitHub 插件，用于连接 GitHub API、读取仓库、分支、"
            "提交、PR 和代码质量数据。"
        ),
        "id": "plugin_standard_github",
        "is_system": True,
        "name": "GitHub",
        "protocol": "http",
        "risk_level": "medium",
        "status": "active",
    },
    {
        "category": "collaboration",
        "code": "email",
        "description": (
            "官方标准邮箱插件，用于连接企业邮件网关或邮件 API，发送代码巡检、"
            "定时作业和业务通知。"
        ),
        "id": "plugin_standard_email",
        "is_system": True,
        "name": "邮箱",
        "protocol": "http",
        "risk_level": "medium",
        "status": "active",
    },
]

STANDARD_PLUGIN_IDS_BY_CODE = {
    str(plugin["code"]): str(plugin["id"])
    for plugin in STANDARD_PLUGINS
}

STANDARD_PLUGIN_MARKETPLACE_METADATA = {
    "email": {
        "action_templates": ["邮件通知发送"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": ["代码巡检通知", "定时作业结果通知", "业务异常提醒"],
        "summary": "连接企业邮件网关或邮件 API，用于任务结果和巡检问题通知。",
    },
    "github": {
        "action_templates": ["GitHub 代码巡检", "GitHub PR / 仓库读取"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": ["代码仓库质量巡检", "安全告警同步", "PR 上下文读取"],
        "summary": "连接 GitHub API，读取仓库、分支、PR、代码扫描和质量数据。",
    },
    "gitlab": {
        "action_templates": ["GitLab 代码巡检", "GitLab MR / 项目读取"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": ["代码仓库质量巡检", "漏洞发现同步", "MR 上下文读取"],
        "summary": "连接 GitLab API，读取项目、分支、MR、提交和代码质量数据。",
    },
}

STANDARD_PLUGIN_CONNECTION_TEMPLATE_VERSION = "v1"

STANDARD_PLUGIN_CONNECTION_DEFAULTS = {
    "email": {
        "auth_config": {
            "header_name": "Authorization",
            "secret_ref": "vault/email/api_key",
        },
        "auth_type": "api_key_header",
        "endpoint_url": "https://mail-gateway.example.com/api",
        "environment": "prod",
        "max_retries": 1,
        "name": "生产邮箱通知连接",
        "request_config": {
            "headers": {"Content-Type": "application/json"},
            "query": {
                "default_from": "",
                "default_to": "",
                "mail_provider": "enterprise_mail_gateway",
                "subject_template": "[AI Brain] {{job_name}} 执行结果",
            },
        },
        "status": "active",
        "timeout_seconds": 30,
    },
    "github": {
        "auth_config": {"token_ref": "vault/github/token"},
        "auth_type": "bearer",
        "endpoint_url": "https://api.github.com",
        "environment": "prod",
        "max_retries": 1,
        "name": "生产 GitHub 连接",
        "request_config": {
            "headers": {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            "query": {
                "owner": "",
                "repo": "",
            },
        },
        "status": "active",
        "timeout_seconds": 30,
    },
    "gitlab": {
        "auth_config": {
            "header_name": "PRIVATE-TOKEN",
            "secret_ref": "vault/gitlab/token",
        },
        "auth_type": "api_key_header",
        "endpoint_url": "https://gitlab.com",
        "environment": "prod",
        "max_retries": 1,
        "name": "生产 GitLab 连接",
        "request_config": {
            "query": {
                "api_version": "v4",
                "group_id": "",
                "project_id": "",
            },
        },
        "status": "active",
        "timeout_seconds": 30,
    },
}

STANDARD_PLUGIN_ACTION_TEMPLATES = [
    {
        "action_type": "mcp_tool",
        "code": "maxcompute_weekly_feedback",
        "default_code": "fetch_weekly_user_feedback",
        "default_name": "获取本周用户反馈数据",
        "description": "从 MaxCompute 获取本周用户反馈明细，交给 Skill 提取用户洞察。",
        "form_defaults": {
            "max_rows": 1000,
            "returned_fields": (
                "feedback_id,user_id,product_id,module_code,feedback_type,"
                "content,sentiment,created_at"
            ),
            "table_name": "ods_user_feedback",
            "time_field": "created_at",
        },
        "name": "MaxCompute 每周用户反馈",
        "plugin_code": "aliyun_maxcompute",
        "request_config": {
            "fields": [
                "feedback_id",
                "user_id",
                "product_id",
                "module_code",
                "feedback_type",
                "content",
                "sentiment",
                "created_at",
            ],
            "limit": 1000,
            "sql_template": (
                "SELECT feedback_id, user_id, product_id, module_code, feedback_type, "
                "content, sentiment, created_at FROM ods_user_feedback "
                "WHERE created_at >= '${week_start}' AND created_at < '${week_end}' LIMIT 1000"
            ),
            "table": "ods_user_feedback",
            "time_field": "created_at",
            "tool_name": "maxcompute.execute_sql",
        },
        "result_mapping": result_write_target_default_mapping("user_feedback_insights"),
        "template_version": "v1",
    },
    {
        "action_type": "http_request",
        "code": "github_code_inspection",
        "default_code": "scan_github_code_inspection",
        "default_name": "GitHub 代码巡检",
        "description": "读取 GitHub 代码扫描告警并映射为平台代码巡检报告。",
        "form_defaults": {},
        "name": "GitHub 代码巡检",
        "plugin_code": "github",
        "request_config": {
            "method": "GET",
            "path": "/repos/{{owner}}/{{repo}}/code-scanning/alerts",
            "query": {
                "per_page": 100,
                "state": "open",
            },
        },
        "result_mapping": result_write_target_default_mapping("code_inspection_reports"),
        "template_version": "v1",
    },
    {
        "action_type": "http_request",
        "code": "gitlab_code_inspection",
        "default_code": "scan_gitlab_code_inspection",
        "default_name": "GitLab 代码巡检",
        "description": "读取 GitLab vulnerability findings 并映射为平台代码巡检报告。",
        "form_defaults": {},
        "name": "GitLab 代码巡检",
        "plugin_code": "gitlab",
        "request_config": {
            "method": "GET",
            "path": "/api/{{api_version}}/projects/{{project_id}}/vulnerability_findings",
            "query": {
                "per_page": 100,
                "report_type": "sast,dependency_scanning,secret_detection",
                "state": "detected",
            },
        },
        "result_mapping": result_write_target_default_mapping("code_inspection_reports"),
        "template_version": "v1",
    },
    {
        "action_type": "http_request",
        "code": "email_notification",
        "default_code": "send_email_notification",
        "default_name": "发送邮件通知",
        "description": "调用企业邮件网关发送定时作业或代码巡检通知，并记录投递反馈。",
        "form_defaults": {},
        "name": "邮箱通知发送",
        "plugin_code": "email",
        "request_config": {
            "headers": {
                "Content-Type": "application/json",
            },
            "method": "POST",
            "path": "/messages/send",
            "query": {
                "body_template": "{{result_summary}}",
                "subject_template": "{{subject_template}}",
                "to": "{{default_to}}",
            },
        },
        "result_mapping": result_write_target_default_mapping("email_notifications"),
        "template_version": "v1",
    },
]

DEFAULT_ACTION_TEMPLATE_BY_PLUGIN_CODE = {
    "email": "email_notification",
    "github": "github_code_inspection",
    "gitlab": "gitlab_code_inspection",
}


def standard_plugin_action_templates() -> list[dict[str, Any]]:
    return deepcopy(STANDARD_PLUGIN_ACTION_TEMPLATES)


def plugin_action_template_by_code(code: str) -> dict[str, Any] | None:
    for template in STANDARD_PLUGIN_ACTION_TEMPLATES:
        if template.get("code") == code:
            return deepcopy(template)
    return None


def plugin_action_template_for_plugin_code(plugin_code: str) -> dict[str, Any] | None:
    template_code = DEFAULT_ACTION_TEMPLATE_BY_PLUGIN_CODE.get(plugin_code)
    if template_code is None:
        return None
    return plugin_action_template_by_code(template_code)


def plugin_action_payload_from_template(
    template: dict[str, Any],
    *,
    connection_id: str | None,
    plugin_id: str,
) -> dict[str, Any]:
    return {
        "action_type": template["action_type"],
        "code": template.get("default_code") or template["code"],
        "connection_id": connection_id,
        "name": template.get("default_name") or template["name"],
        "plugin_id": plugin_id,
        "request_config": deepcopy(template.get("request_config") or {}),
        "requires_human_review": False,
        "result_mapping": deepcopy(template.get("result_mapping") or {}),
        "status": "active",
        "template_code": template["code"],
        "template_version": template["template_version"],
    }


def standard_plugin_connection_defaults(plugin_code: str | None) -> dict[str, Any]:
    return deepcopy(STANDARD_PLUGIN_CONNECTION_DEFAULTS.get(str(plugin_code or ""), {}))


def plugin_connection_payload_from_template(
    plugin_code: str,
    *,
    plugin_id: str,
) -> dict[str, Any]:
    payload = standard_plugin_connection_defaults(plugin_code)
    if not payload:
        return {"plugin_id": plugin_id}
    payload["plugin_id"] = plugin_id
    return payload
