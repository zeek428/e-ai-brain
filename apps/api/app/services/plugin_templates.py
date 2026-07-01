from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.ai_executor_runners import (
    SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
)
from app.services.internal_data_sources import (
    INTERNAL_DATA_SOURCE_DEFAULT_TYPES,
    internal_data_source_source_options,
)
from app.services.result_write_targets import result_write_target_default_mapping

STANDARD_PLUGINS = [
    {
        "category": "ai_service",
        "code": "ai_executor",
        "description": (
            "官方标准 AI 执行器插件，默认使用系统 AI 大模型执行，也支持通过受控 Runner "
            "向 Codex、Claude、Hermes、OpenClaw 等执行器下达指令并同步回写。"
        ),
        "id": "plugin_standard_ai_executor",
        "is_system": True,
        "name": "AI 执行器",
        "protocol": "runner_polling",
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
    {
        "category": "operations",
        "code": "observability",
        "description": "官方标准可观测平台插件，用于读取线上日志、错误率、延迟和异常指标。",
        "id": "plugin_standard_observability",
        "is_system": True,
        "name": "可观测平台",
        "protocol": "http",
        "risk_level": "medium",
        "status": "active",
    },
    {
        "category": "business_system",
        "code": "internal_data_source",
        "description": (
            "官方标准内部数据源插件，只读访问 AI Brain 内部业务数据，支持用户洞察、"
            "需求、产品和 Bug 数据作为定时作业输入。"
        ),
        "id": "plugin_standard_internal_data_source",
        "is_system": True,
        "name": "内部数据源",
        "protocol": "internal_read_model",
        "risk_level": "low",
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
            "使用系统默认 AI 大模型执行任务",
            "代码巡检自动执行",
            "定时任务委派给 Codex/Claude/Hermes/OpenClaw",
            "执行完成后同步回写",
        ],
        "summary": (
            "默认调用系统 AI 大模型，也可通过受控 Runner 对接 Codex、Claude、Hermes、OpenClaw "
            "等执行器，支持下达指令、等待完成、拉取结果和回写同步。"
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
    "github": {
        "action_templates": ["GitHub 代码巡检", "GitHub PR / 仓库读取"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": ["代码仓库质量巡检", "安全告警同步", "PR 上下文读取"],
        "summary": "连接 GitHub API，读取仓库、分支、PR、代码扫描和质量数据。",
    },
    "internal_data_source": {
        "action_templates": ["读取内部业务数据"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": [
            "每周内部业务洞察",
            "需求与 Bug 风险分析",
            "用户洞察转需求",
            "产品反馈趋势分析",
        ],
        "summary": "只读读取 AI Brain 内部业务数据，作为定时作业和 AI 处理的数据输入。",
    },
    "gitlab": {
        "action_templates": ["GitLab 代码巡检", "GitLab MR / 项目读取"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": ["代码仓库质量巡检", "漏洞发现同步", "MR 上下文读取"],
        "summary": "连接 GitLab API，读取项目、分支、MR、提交和代码质量数据。",
    },
    "observability": {
        "action_templates": ["线上日志指标查询"],
        "publisher": "AI Brain 官方",
        "recommended_scenarios": ["线上日志异常发现", "错误率突增分析", "生产告警复盘"],
        "summary": "连接可观测平台，读取线上日志、错误率、延迟和异常指标。",
    },
}

STANDARD_PLUGIN_CONNECTION_TEMPLATE_VERSION = "v1"

STANDARD_PLUGIN_CONNECTION_DEFAULTS = {
    "ai_executor": {
        "auth_config": {},
        "auth_type": "none",
        "endpoint_url": "model-gateway://default",
        "environment": "prod",
        "max_retries": 0,
        "name": "系统默认 AI 执行器连接",
        "protocol": "runner_polling",
        "request_config": {
            "query": {
                "executor_type": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
                "instruction_timeout_seconds": 1800,
                "runner_id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
                "result_callback_url": "",
                "runner_profile": "default",
                "supported_executor_types": [
                    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
                    "codex",
                    "claude",
                    "hermes",
                    "openclaw",
                ],
                "workspace_root": "/workspace",
            },
        },
        "status": "active",
        "timeout_seconds": 30,
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
        "auth_config": {},
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
    "internal_data_source": {
        "auth_config": {},
        "auth_type": "none",
        "endpoint_url": "internal://e-ai-brain/business-data",
        "environment": "prod",
        "max_retries": 0,
        "name": "内部业务数据连接",
        "request_config": {
            "query": {
                "field_mode": "summary",
                "limit": 100,
                "product_scope": "current_user_scope",
                "source_types": list(INTERNAL_DATA_SOURCE_DEFAULT_TYPES),
                "window_end": "{{now}}",
                "window_start": "{{current_date-30}}",
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
        "endpoint_url": "http://gitlab.local",
        "environment": "prod",
        "max_retries": 1,
        "name": "生产 GitLab 连接",
        "request_config": {
            "query": {
                "api_version": "v4",
                "project_id": "",
                "project_path": "",
            },
        },
        "status": "active",
        "timeout_seconds": 30,
    },
    "observability": {
        "auth_config": {
            "header_name": "Authorization",
            "secret_ref": "vault/observability/api_key",
        },
        "auth_type": "api_key_header",
        "endpoint_url": "https://logs.example.com/api",
        "environment": "prod",
        "max_retries": 1,
        "name": "生产可观测平台连接",
        "request_config": {
            "headers": {"Content-Type": "application/json"},
            "query": {
                "app": "",
                "environment": "prod",
                "service": "",
                "window_minutes": 30,
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
                "title": "执行器调用配置",
                "fields": [
                    {
                        "description": (
                            "系统默认执行器使用 ai_executor_runner_system_default；"
                            "本地 Runner 可填写对应 Runner ID。"
                        ),
                        "key": "runner_id",
                        "label": "Runner",
                        "path": "request_config.query.runner_id",
                        "placeholder": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
                        "required": False,
                        "type": "text",
                    },
                    {
                        "key": "executor_type",
                        "label": "执行器类型",
                        "options": [
                            SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
                            "codex",
                            "claude",
                            "hermes",
                            "openclaw",
                        ],
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
                        "description": (
                            "可粘贴 https://github.com/acme/ai-brain.git、"
                            "git@github.com:acme/ai-brain.git，或直接填写 acme/ai-brain。"
                        ),
                        "key": "repository_url",
                        "label": "仓库地址",
                        "managed_query_keys": ["owner", "repo"],
                        "placeholder": "https://github.com/acme/ai-brain.git",
                        "required": True,
                        "type": "github_repository_url",
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
                        "description": (
                            "填写本地 GitLab 项目地址，例如 "
                            "http://gitlab.local/acme/ai-brain.git；"
                            "系统会自动解析 Endpoint 和项目路径。"
                        ),
                        "key": "gitlab_project_url",
                        "label": "GitLab 地址",
                        "managed_query_keys": [
                            "api_version",
                            "group_id",
                            "project_id",
                            "project_path",
                        ],
                        "placeholder": "http://gitlab.local/acme/ai-brain.git",
                        "required": True,
                        "type": "gitlab_project_url",
                    },
                ],
            },
        ],
    },
    "internal_data_source": {
        "schema_version": "v1",
        "sections": [
            {
                "key": "sources",
                "title": "源数据选择",
                "fields": [
                    {
                        "description": "可多选，运行时按数据源分别读取并合并为结构化输入。",
                        "key": "source_types",
                        "label": "源数据",
                        "options": internal_data_source_source_options(),
                        "path": "request_config.query.source_types",
                        "required": True,
                        "type": "multi_select",
                    },
                    {
                        "description": "summary 只返回常用字段，detail 返回更完整的业务字段。",
                        "key": "field_mode",
                        "label": "字段模式",
                        "options": [
                            {"label": "摘要字段", "value": "summary"},
                            {"label": "完整字段", "value": "detail"},
                        ],
                        "path": "request_config.query.field_mode",
                        "required": True,
                        "type": "select",
                    },
                    {
                        "description": "每类源数据最多返回条数。",
                        "key": "limit",
                        "label": "每类最大行数",
                        "path": "request_config.query.limit",
                        "required": True,
                        "type": "number",
                    },
                    {
                        "description": "默认按当前用户可访问产品范围过滤。",
                        "key": "product_scope",
                        "label": "产品范围",
                        "options": [
                            {"label": "当前用户可访问产品", "value": "current_user_scope"},
                            {"label": "全部可访问数据", "value": "all_accessible"},
                        ],
                        "path": "request_config.query.product_scope",
                        "required": True,
                        "type": "select",
                    },
                ],
            },
            {
                "key": "filters",
                "title": "过滤条件",
                "fields": [
                    {
                        "description": "支持系统变量，例如 {{current_date-7}}。",
                        "key": "window_start",
                        "label": "开始时间",
                        "path": "request_config.query.window_start",
                        "required": False,
                        "supports_system_variables": True,
                        "type": "text",
                    },
                    {
                        "description": "支持系统变量，例如 {{now}}。",
                        "key": "window_end",
                        "label": "结束时间",
                        "path": "request_config.query.window_end",
                        "required": False,
                        "supports_system_variables": True,
                        "type": "text",
                    },
                    {
                        "description": "选填，限制读取某一个产品。",
                        "key": "product_id",
                        "label": "产品 ID",
                        "path": "request_config.query.product_id",
                        "required": False,
                        "type": "text",
                    },
                    {
                        "description": "选填，按业务状态过滤。",
                        "key": "status",
                        "label": "状态",
                        "path": "request_config.query.status",
                        "required": False,
                        "type": "text",
                    },
                ],
            },
            {
                "key": "source_filters",
                "title": "按源过滤",
                "fields": [
                    {
                        "description": "只作用于需求数据。",
                        "key": "requirements_status",
                        "label": "需求状态",
                        "options": [
                            {"label": "草稿", "value": "draft"},
                            {"label": "已提交", "value": "submitted"},
                            {"label": "已批准", "value": "approved"},
                            {"label": "已排期", "value": "planned"},
                            {"label": "设计中", "value": "designing"},
                            {"label": "待开发", "value": "ready_for_dev"},
                            {"label": "开发中", "value": "developing"},
                            {"label": "代码评审中", "value": "code_reviewing"},
                            {"label": "测试中", "value": "testing"},
                            {"label": "待发布", "value": "ready_for_release"},
                            {"label": "已发布", "value": "released"},
                            {"label": "已验收", "value": "accepted"},
                            {"label": "已拒绝", "value": "rejected"},
                            {"label": "已延期", "value": "deferred"},
                            {"label": "已取消", "value": "cancelled"},
                            {"label": "已关闭", "value": "closed"},
                        ],
                        "path": "request_config.query.source_filters.requirements.status",
                        "required": False,
                        "type": "select",
                    },
                    {
                        "description": "只作用于需求数据。",
                        "key": "requirements_priority",
                        "label": "需求优先级",
                        "options": [
                            {"label": "P0", "value": "P0"},
                            {"label": "P1", "value": "P1"},
                            {"label": "P2", "value": "P2"},
                        ],
                        "path": "request_config.query.source_filters.requirements.priority",
                        "required": False,
                        "type": "select",
                    },
                    {
                        "description": "只作用于 Bug 数据。",
                        "key": "bugs_status",
                        "label": "Bug 状态",
                        "options": [
                            {"label": "待处理", "value": "open"},
                            {"label": "已分诊", "value": "triaged"},
                            {"label": "需补充", "value": "needs_info"},
                            {"label": "已分派", "value": "assigned"},
                            {"label": "已修复", "value": "fixed"},
                            {"label": "已验证", "value": "verified"},
                            {"label": "已关闭", "value": "closed"},
                            {"label": "重新打开", "value": "reopened"},
                        ],
                        "path": "request_config.query.source_filters.bugs.status",
                        "required": False,
                        "type": "select",
                    },
                    {
                        "description": "只作用于 Bug 数据。",
                        "key": "bugs_severity",
                        "label": "Bug 严重级别",
                        "options": [
                            {"label": "blocker", "value": "blocker"},
                            {"label": "critical", "value": "critical"},
                            {"label": "major", "value": "major"},
                            {"label": "minor", "value": "minor"},
                        ],
                        "path": "request_config.query.source_filters.bugs.severity",
                        "required": False,
                        "type": "select",
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
            "默认向系统 AI 大模型下达任务指令，也可委派给 Codex、Claude、Hermes、OpenClaw "
            "等受控执行器，返回结构化结果。"
        ),
        "form_defaults": {
            "executor_type": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
            "instruction": "请检查仓库质量、安全和规范问题，并输出结构化报告。",
            "instruction_timeout_seconds": 1800,
            "result_callback_url": "",
            "runner_id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
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
    {
        "action_type": "http_request",
        "code": "observability_online_log_metrics",
        "default_code": "query_online_log_metrics",
        "default_name": "查询线上日志指标",
        "description": "从可观测平台读取指定窗口内的错误率、延迟、异常日志和采样记录。",
        "form_defaults": {
            "window_end": "{{now}}",
            "window_start": "{{current_date}}",
        },
        "name": "线上日志指标查询",
        "plugin_code": "observability",
        "request_config": {
            "headers": {"Content-Type": "application/json"},
            "method": "GET",
            "path": "/logs/anomaly-metrics",
            "query": {
                "app": "{{app}}",
                "environment": "{{environment}}",
                "service": "{{service}}",
                "window_end": "{{window_end}}",
                "window_start": "{{window_start}}",
            },
        },
        "result_mapping": {
            "records_imported_path": "$.row_count",
            "source_rows_path": "$.logs",
            "write_target": "scheduled_job_result",
        },
        "template_version": "v1",
    },
    {
        "action_type": "internal_query",
        "code": "internal_business_data_query",
        "default_code": "query_internal_business_data",
        "default_name": "读取内部业务数据",
        "description": (
            "只读读取 AI Brain 内部用户洞察、需求、产品和 Bug 数据，作为定时作业 "
            "AI 处理输入。"
        ),
        "form_defaults": {},
        "name": "读取内部业务数据",
        "plugin_code": "internal_data_source",
        "request_config": {
            "tool_name": "internal_data_source.query",
        },
        "result_mapping": result_write_target_default_mapping("scheduled_job_result"),
        "template_version": "v1",
    },
]

DEFAULT_ACTION_TEMPLATE_BY_PLUGIN_CODE = {
    "ai_executor": "ai_executor_command",
    "email": "email_notification",
    "github": "github_code_inspection",
    "internal_data_source": "internal_business_data_query",
    "gitlab": "gitlab_code_inspection",
    "observability": "observability_online_log_metrics",
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
