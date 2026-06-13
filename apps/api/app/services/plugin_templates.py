from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.result_write_targets import result_write_target_default_mapping

STANDARD_PLUGINS = [
    {
        "category": "ai_service",
        "code": "ai_executor",
        "description": (
            "官方标准 AI 执行器插件，用于通过受控 Runner 向 Codex、Claude、"
            "Hermes、OpenClaw 等执行器下达指令、等待执行结果并同步回写。"
        ),
        "id": "plugin_standard_ai_executor",
        "is_system": True,
        "name": "AI 执行器",
        "protocol": "runner_polling",
        "risk_level": "high",
        "status": "active",
    },
    {
        "category": "data_warehouse",
        "code": "aliyun_maxcompute",
        "description": (
            "官方标准阿里云 MaxCompute 插件，用于连接数据仓库、执行 SQL "
            "并把结果交给定时作业或 AI Skill 分析。"
        ),
        "id": "plugin_standard_aliyun_maxcompute",
        "is_system": True,
        "name": "阿里云 MaxCompute",
        "protocol": "mcp_http",
        "risk_level": "high",
        "status": "active",
    },
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
    "ai_executor": {
        "action_templates": ["AI 执行器下达指令", "AI 执行器结果同步"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": [
            "代码巡检自动执行",
            "定时任务委派给 Codex/Claude/Hermes/OpenClaw",
            "执行完成后同步回写",
        ],
        "summary": (
            "通过受控 Runner 对接 Codex、Claude、Hermes、OpenClaw 等执行器，"
            "支持下达指令、等待完成、拉取结果和回写同步。"
        ),
    },
    "email": {
        "action_templates": ["邮件通知发送", "邮件收取"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": [
            "代码巡检通知",
            "定时作业结果通知",
            "业务异常提醒",
            "邮件工单或反馈收取",
        ],
        "summary": "连接企业邮件网关、SMTP/IMAP/POP3 或邮件 API，用于邮件收取和发送。",
    },
    "aliyun_maxcompute": {
        "action_templates": ["MaxCompute 每周用户反馈"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": [
            "每周用户反馈分析",
            "数据仓库取数",
            "用户洞察生成",
        ],
        "summary": "连接阿里云 MaxCompute 项目，按时间窗口执行 SQL 并返回结构化数据。",
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
    "ai_executor": {
        "auth_config": {
            "token_ref": "vault/ai-executor/token",
        },
        "auth_type": "bearer",
        "endpoint_url": "runner://ai-executor",
        "environment": "prod",
        "max_retries": 0,
        "name": "生产 AI 执行器连接",
        "protocol": "runner_polling",
        "request_config": {
            "query": {
                "executor_type": "codex",
                "instruction_timeout_seconds": 1800,
                "runner_id": "",
                "result_callback_url": "",
                "runner_profile": "default",
                "supported_executor_types": ["codex", "claude", "hermes", "openclaw"],
                "workspace_root": "/workspace",
            },
        },
        "status": "active",
        "timeout_seconds": 30,
    },
    "aliyun_maxcompute": {
        "auth_config": {
            "access_key_id_ref": "vault/maxcompute/access_key_id",
            "access_key_secret_ref": "vault/maxcompute/access_key_secret",
        },
        "auth_type": "bearer",
        "endpoint_url": "https://maxcompute.aliyuncs.com",
        "environment": "prod",
        "max_retries": 1,
        "name": "生产 MaxCompute 连接",
        "protocol": "mcp_http",
        "request_config": {
            "query": {
                "endpoint": "https://service.cn-hangzhou.maxcompute.aliyun.com/api",
                "project": "",
                "region": "cn-hangzhou",
                "table_name": "ods_user_feedback",
                "tunnel_endpoint": "",
            },
        },
        "status": "active",
        "timeout_seconds": 60,
    },
    "email": {
        "auth_config": {
            "header_name": "Authorization",
            "secret_ref": "vault/email/api_key",
        },
        "auth_type": "api_key_header",
        "endpoint_url": "https://mail-gateway.example.com/api",
        "environment": "prod",
        "max_retries": 1,
        "name": "生产邮箱连接",
        "request_config": {
            "headers": {"Content-Type": "application/json"},
            "query": {
                "default_from": "noreply@example.com",
                "default_to": "",
                "imap_host": "imap.example.com",
                "imap_port": 993,
                "mail_provider": "enterprise_mail_gateway",
                "mailbox_folder": "INBOX",
                "poll_since": "{{current_date-7}}",
                "pop3_host": "pop3.example.com",
                "pop3_port": 995,
                "receive_protocol": "imap",
                "reply_to": "",
                "send_protocol": "smtp",
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "smtp_tls": "ssl",
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

STANDARD_PLUGIN_CONNECTION_SCHEMAS = {
    "ai_executor": {
        "schema_version": "v1",
        "sections": [
            {
                "key": "runner",
                "title": "Runner 调用配置",
                "fields": [
                    {
                        "description": "留空时由平台按执行器类型和工作区自动选择在线 Runner。",
                        "key": "runner_id",
                        "label": "Runner",
                        "path": "request_config.query.runner_id",
                        "placeholder": "ai_executor_runner_xxx",
                        "required": False,
                        "type": "text",
                    },
                    {
                        "key": "executor_type",
                        "label": "执行器类型",
                        "options": ["codex", "claude", "hermes", "openclaw"],
                        "path": "request_config.query.executor_type",
                        "required": True,
                        "type": "select",
                    },
                    {
                        "key": "workspace_root",
                        "label": "工作区",
                        "path": "request_config.query.workspace_root",
                        "placeholder": "/workspace",
                        "required": True,
                        "type": "text",
                    },
                    {
                        "key": "instruction_timeout_seconds",
                        "label": "指令超时秒数",
                        "path": "request_config.query.instruction_timeout_seconds",
                        "required": True,
                        "type": "number",
                    },
                    {
                        "key": "result_callback_url",
                        "label": "结果回写地址",
                        "path": "request_config.query.result_callback_url",
                        "required": False,
                        "type": "text",
                    },
                ],
            },
        ],
    },
    "aliyun_maxcompute": {
        "schema_version": "v1",
        "sections": [
            {
                "key": "project",
                "title": "项目与表配置",
                "fields": [
                    {
                        "key": "project",
                        "label": "Project",
                        "path": "request_config.query.project",
                        "required": True,
                        "type": "text",
                    },
                    {
                        "key": "region",
                        "label": "地域",
                        "path": "request_config.query.region",
                        "required": True,
                        "type": "text",
                    },
                    {
                        "key": "table_name",
                        "label": "默认表名",
                        "path": "request_config.query.table_name",
                        "required": False,
                        "type": "text",
                    },
                    {
                        "key": "endpoint",
                        "label": "Endpoint",
                        "path": "request_config.query.endpoint",
                        "required": True,
                        "type": "text",
                    },
                    {
                        "key": "tunnel_endpoint",
                        "label": "Tunnel Endpoint",
                        "path": "request_config.query.tunnel_endpoint",
                        "required": False,
                        "type": "text",
                    },
                ],
            },
        ],
    },
    "email": {
        "schema_version": "v1",
        "sections": [
            {
                "key": "send",
                "title": "发件配置",
                "fields": [
                    {
                        "key": "default_from",
                        "label": "默认发件人",
                        "path": "request_config.query.default_from",
                        "required": True,
                        "type": "text",
                    },
                    {
                        "key": "default_to",
                        "label": "默认收件人",
                        "path": "request_config.query.default_to",
                        "required": False,
                        "type": "text",
                    },
                    {
                        "key": "smtp_host",
                        "label": "SMTP Host",
                        "path": "request_config.query.smtp_host",
                        "required": False,
                        "type": "text",
                    },
                    {
                        "key": "smtp_port",
                        "label": "SMTP Port",
                        "path": "request_config.query.smtp_port",
                        "required": False,
                        "type": "number",
                    },
                ],
            },
            {
                "key": "receive",
                "title": "收件配置",
                "fields": [
                    {
                        "key": "receive_protocol",
                        "label": "收件协议",
                        "options": ["imap", "pop3", "mail_api"],
                        "path": "request_config.query.receive_protocol",
                        "required": True,
                        "type": "select",
                    },
                    {
                        "key": "mailbox_folder",
                        "label": "邮箱文件夹",
                        "path": "request_config.query.mailbox_folder",
                        "required": False,
                        "type": "text",
                    },
                    {
                        "description": "支持 {{current_date-7}} 等系统变量。",
                        "key": "poll_since",
                        "label": "收取起始时间",
                        "path": "request_config.query.poll_since",
                        "required": False,
                        "supports_system_variables": True,
                        "type": "text",
                    },
                ],
            },
        ],
    },
    "github": {
        "schema_version": "v1",
        "sections": [
            {
                "key": "repository",
                "title": "仓库配置",
                "fields": [
                    {
                        "key": "owner",
                        "label": "Owner / Org",
                        "path": "request_config.query.owner",
                        "required": True,
                        "type": "text",
                    },
                    {
                        "key": "repo",
                        "label": "Repository",
                        "path": "request_config.query.repo",
                        "required": True,
                        "type": "text",
                    },
                ],
            },
        ],
    },
    "gitlab": {
        "schema_version": "v1",
        "sections": [
            {
                "key": "project",
                "title": "项目配置",
                "fields": [
                    {
                        "key": "project_id",
                        "label": "Project ID",
                        "path": "request_config.query.project_id",
                        "required": True,
                        "type": "text",
                    },
                    {
                        "key": "group_id",
                        "label": "Group ID",
                        "path": "request_config.query.group_id",
                        "required": False,
                        "type": "text",
                    },
                    {
                        "key": "api_version",
                        "label": "API 版本",
                        "path": "request_config.query.api_version",
                        "required": True,
                        "type": "text",
                    },
                ],
            },
        ],
    },
}

STANDARD_PLUGIN_ACTION_TEMPLATES = [
    {
        "action_type": "mcp_tool",
        "code": "ai_executor_command",
        "default_code": "run_ai_executor_instruction",
        "default_name": "AI 执行器下达指令",
        "description": (
            "向 Codex、Claude、Hermes、OpenClaw 等受控执行器下达任务指令，等待完成后"
            "返回结构化结果。"
        ),
        "form_defaults": {
            "executor_type": "codex",
            "instruction": "请检查仓库质量、安全和规范问题，并输出结构化报告。",
            "instruction_timeout_seconds": 1800,
            "result_callback_url": "",
            "runner_id": "",
            "workspace_root": "/workspace",
        },
        "name": "AI 执行器下达指令",
        "plugin_code": "ai_executor",
        "request_config": {
            "executor_type": "{{executor_type}}",
            "instruction": "{{instruction}}",
            "instruction_timeout_seconds": "{{instruction_timeout_seconds}}",
            "query": {
                "result_callback_url": "{{result_callback_url}}",
                "runner_id": "{{runner_id}}",
            },
            "runner_id": "{{runner_id}}",
            "tool_name": "ai_executor.run_instruction",
            "wait_for_completion": True,
            "workspace_root": "{{workspace_root}}",
        },
        "result_mapping": result_write_target_default_mapping("scheduled_job_result"),
        "template_version": "v1",
    },
    {
        "action_type": "mcp_tool",
        "code": "ai_executor_result_sync",
        "default_code": "sync_ai_executor_result",
        "default_name": "AI 执行器结果同步",
        "description": "拉取执行器运行结果，并通过配置的回写地址同步到平台或外部系统。",
        "form_defaults": {
            "executor_type": "codex",
            "result_callback_url": "",
            "run_id": "",
        },
        "name": "AI 执行器结果同步",
        "plugin_code": "ai_executor",
        "request_config": {
            "executor_type": "{{executor_type}}",
            "query": {
                "result_callback_url": "{{result_callback_url}}",
                "run_id": "{{run_id}}",
            },
            "tool_name": "ai_executor.sync_result",
        },
        "result_mapping": result_write_target_default_mapping("scheduled_job_result"),
        "template_version": "v1",
    },
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
        "code": "email_receive",
        "default_code": "receive_email_messages",
        "default_name": "收取邮箱邮件",
        "description": "从企业邮箱网关或邮件 API 按文件夹和时间窗口收取邮件，供定时作业后续分析。",
        "form_defaults": {
            "folder": "INBOX",
            "since": "{{current_date-7}}",
        },
        "name": "邮件收取",
        "plugin_code": "email",
        "request_config": {
            "headers": {
                "Content-Type": "application/json",
            },
            "method": "GET",
            "path": "/messages/search",
            "query": {
                "folder": "{{mailbox_folder}}",
                "from": "{{receive_from}}",
                "since": "{{poll_since}}",
                "subject_keyword": "{{subject_keyword}}",
            },
        },
        "result_mapping": result_write_target_default_mapping("scheduled_job_result"),
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
    "ai_executor": "ai_executor_command",
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


def standard_plugin_connection_schema(plugin_code: str | None) -> dict[str, Any]:
    return deepcopy(STANDARD_PLUGIN_CONNECTION_SCHEMAS.get(str(plugin_code or ""), {}))


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
