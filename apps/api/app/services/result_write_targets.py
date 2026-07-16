from __future__ import annotations

from copy import deepcopy
from typing import Any

RESULT_WRITE_TARGETS = [
    {
        "code": "scheduled_job_result",
        "default_result_mapping": {
            "write_target": "scheduled_job_result",
        },
        "description": "仅保存为定时作业运行结果，适合调试、归档或后续人工复制。",
        "form_label": "仅保存运行结果",
        "label": "定时作业结果",
        "mapping_fields": [
            {
                "description": "从响应 JSON 中读取导入数量或结果数组的路径。",
                "key": "records_imported_path",
                "label": "导入数量 JSONPath",
                "placeholder": "$.row_count",
                "required": False,
            },
        ],
        "supported_job_types": ["plugin_action_invoke", "online_log_ai_analysis"],
    },
    {
        "code": "user_feedback_insights",
        "default_result_mapping": {
            "insights_path": "$.insights",
            "records_imported_path": "$.row_count",
            "rows_path": "$.rows",
            "write_target": "user_feedback_insights",
        },
        "description": "把 AI 处理后的用户反馈洞察写入用户洞察表。",
        "form_label": "用户洞察表",
        "label": "用户洞察表",
        "mapping_fields": [],
        "supported_job_types": ["plugin_action_invoke", "user_feedback_insight_extract"],
    },
    {
        "code": "bugs",
        "default_result_mapping": {
            "bugs_path": "$.bugs",
            "write_target": "bugs",
        },
        "description": "把 AI 识别出的缺陷候选写入 Bug 管理。",
        "form_label": "Bug 管理",
        "label": "Bug 管理",
        "mapping_fields": [
            {
                "description": "AI 输出中 Bug 候选数组所在路径。",
                "key": "bugs_path",
                "label": "Bug 列表 JSONPath",
                "placeholder": "$.bugs",
                "required": True,
            },
        ],
        "supported_job_types": ["plugin_action_invoke"],
    },
    {
        "code": "code_inspection_reports",
        "default_result_mapping": {
            "branch_path": "$.branch",
            "commit_sha_path": "$.commit_sha",
            "findings_path": "$.findings",
            "repository_id_path": "$.repository_id",
            "risk_level_path": "$.risk_level",
            "summary_path": "$.summary",
            "write_target": "code_inspection_reports",
        },
        "description": "把仓库扫描或 AI 复核后的 findings 写入代码巡检报告。",
        "form_label": "代码巡检报告",
        "label": "代码巡检报告",
        "mapping_fields": [
            {
                "description": "代码问题列表所在路径。",
                "key": "findings_path",
                "label": "Finding 列表 JSONPath",
                "placeholder": "$.findings",
                "required": True,
            },
            {
                "description": "产品 Git 仓库 ID 所在路径。",
                "key": "repository_id_path",
                "label": "仓库 ID JSONPath",
                "placeholder": "$.repository_id",
                "required": False,
            },
            {
                "description": "扫描分支所在路径。",
                "key": "branch_path",
                "label": "分支 JSONPath",
                "placeholder": "$.branch",
                "required": False,
            },
            {
                "description": "扫描提交 SHA 所在路径。",
                "key": "commit_sha_path",
                "label": "提交 SHA JSONPath",
                "placeholder": "$.commit_sha",
                "required": False,
            },
            {
                "description": "整体风险等级所在路径。",
                "key": "risk_level_path",
                "label": "风险级别 JSONPath",
                "placeholder": "$.risk_level",
                "required": False,
            },
            {
                "description": "巡检摘要所在路径。",
                "key": "summary_path",
                "label": "摘要 JSONPath",
                "placeholder": "$.summary",
                "required": False,
            },
        ],
        "supported_job_types": ["code_repository_inspection", "plugin_action_invoke"],
    },
    {
        "code": "email_notifications",
        "default_result_mapping": {
            "delivery_id_path": "$.message_id",
            "delivery_status_path": "$.status",
            "recipients_path": "$.recipients",
            "subject_path": "$.subject",
            "write_target": "email_notifications",
        },
        "description": "记录邮件通知动作的投递反馈，便于任务运行详情追踪。",
        "form_label": "邮件通知记录",
        "label": "邮件通知记录",
        "mapping_fields": [
            {
                "description": "收件人列表或单个收件人所在路径。",
                "key": "recipients_path",
                "label": "收件人 JSONPath",
                "placeholder": "$.recipients",
                "required": True,
            },
            {
                "description": "邮件主题所在路径。",
                "key": "subject_path",
                "label": "主题 JSONPath",
                "placeholder": "$.subject",
                "required": False,
            },
            {
                "description": "投递状态所在路径。",
                "key": "delivery_status_path",
                "label": "投递状态 JSONPath",
                "placeholder": "$.status",
                "required": False,
            },
            {
                "description": "邮件网关返回的消息 ID 所在路径。",
                "key": "delivery_id_path",
                "label": "消息 ID JSONPath",
                "placeholder": "$.message_id",
                "required": False,
            },
        ],
        "supported_job_types": [
            "plugin_action_invoke",
            "code_repository_inspection",
            "online_log_ai_analysis",
        ],
    },
    {
        "code": "dingtalk_document",
        "default_result_mapping": {
            "content_template": "{{result_summary}}",
            "document_id": "",
            "document_id_path": "$.document_id",
            "status_path": "$.status",
            "write_mode": "append",
            "write_target": "dingtalk_document",
        },
        "description": "把 AI 处理结果追加或覆盖写入指定钉钉文档，并记录文档写入反馈。",
        "form_label": "钉钉文档",
        "label": "钉钉文档",
        "mapping_fields": [
            {
                "description": "可粘贴钉钉文档链接，系统会自动提取 /i/nodes/ 后的文档 ID。",
                "key": "document_id",
                "label": "钉钉文档链接或 ID",
                "placeholder": "https://alidocs.dingtalk.com/i/nodes/...",
                "required": True,
            },
            {
                "description": "写入钉钉文档的内容模板，可引用任务结果摘要。",
                "key": "content_template",
                "label": "写入内容",
                "placeholder": "{{result_summary}}",
                "required": True,
                "type": "textarea",
            },
            {
                "description": "追加到文档末尾或覆盖文档内容。",
                "key": "write_mode",
                "label": "写入方式",
                "options": [
                    {"label": "追加内容", "value": "append"},
                    {"label": "覆盖内容", "value": "overwrite"},
                ],
                "placeholder": "append",
                "required": True,
                "type": "select",
            },
            {
                "description": "从钉钉 MCP 返回中读取文档 ID 的路径，用于写入记录。",
                "key": "document_id_path",
                "label": "返回文档 ID JSONPath",
                "placeholder": "$.document_id",
                "required": False,
            },
            {
                "description": "从钉钉 MCP 返回中读取写入状态的路径。",
                "key": "status_path",
                "label": "返回状态 JSONPath",
                "placeholder": "$.status",
                "required": False,
            },
        ],
        "supported_job_types": [
            "plugin_action_invoke",
            "user_feedback_insight_extract",
            "code_repository_inspection",
            "online_log_ai_analysis",
        ],
    },
    {
        "code": "dingtalk_aitable_records",
        "default_result_mapping": {
            "records_path": "$.records",
            "records_template": "{{result_json}}",
            "record_id_path": "$.result.recordIds",
            "status_path": "$.success",
            "table_id": "",
            "write_target": "dingtalk_aitable_records",
        },
        "description": "把 AI 处理结果作为新记录写入指定钉钉 AI 表格，并记录新增反馈。",
        "form_label": "钉钉表格",
        "label": "钉钉表格",
        "mapping_fields": [
            {
                "description": "目标数据表 Table ID。",
                "key": "table_id",
                "label": "数据表 Table ID",
                "placeholder": "tbl_xxx",
                "required": True,
            },
            {
                "description": (
                    "新增记录 JSON，可填写数组，也可使用 {{result_json}}、{{records}} "
                    "等任务结果变量。单条记录通常为 {\"cells\":{\"字段ID\":\"值\"}}。"
                ),
                "key": "records_template",
                "label": "新增记录内容",
                "placeholder": "[{\"cells\":{\"字段ID\":\"值\"}}]",
                "required": True,
                "type": "textarea",
            },
            {
                "description": "从钉钉 MCP 返回中读取新增记录 ID 列表的路径。",
                "key": "record_id_path",
                "label": "返回记录 ID JSONPath",
                "placeholder": "$.result.recordIds",
                "required": False,
            },
            {
                "description": "从钉钉 MCP 返回中读取写入状态的路径。",
                "key": "status_path",
                "label": "返回状态 JSONPath",
                "placeholder": "$.success",
                "required": False,
            },
        ],
        "supported_job_types": [
            "plugin_action_invoke",
            "user_feedback_insight_extract",
            "code_repository_inspection",
            "online_log_ai_analysis",
        ],
    },
    {
        "code": "requirements",
        "default_result_mapping": {
            "priority": "P1",
            "requirements_path": "$.requirements",
            "source": "user_feedback",
            "write_target": "requirements",
        },
        "description": "把 AI 提炼出的需求候选写入需求管理，默认创建为待处理需求。",
        "form_label": "需求管理",
        "label": "需求管理",
        "mapping_fields": [
            {
                "description": "AI 输出中需求候选数组所在路径。",
                "key": "requirements_path",
                "label": "需求列表 JSONPath",
                "placeholder": "$.requirements",
                "required": True,
            },
            {
                "description": "当候选未给出优先级时使用的默认值。",
                "key": "priority",
                "label": "默认优先级",
                "options": [
                    {"label": "P0", "value": "P0"},
                    {"label": "P1", "value": "P1"},
                    {"label": "P2", "value": "P2"},
                ],
                "placeholder": "P1",
                "required": True,
                "type": "select",
            },
        ],
        "supported_job_types": ["plugin_action_invoke"],
    },
]


def result_write_targets() -> list[dict[str, Any]]:
    return deepcopy(RESULT_WRITE_TARGETS)


def result_write_target_by_code(code: str | None) -> dict[str, Any] | None:
    normalized = str(code or "scheduled_job_result")
    for target in RESULT_WRITE_TARGETS:
        if target["code"] == normalized:
            return deepcopy(target)
    return None


def result_write_target_default_mapping(code: str | None) -> dict[str, Any]:
    target = result_write_target_by_code(code)
    if target is None:
        return {"write_target": str(code or "scheduled_job_result")}
    return deepcopy(target["default_result_mapping"])


def result_write_target_label(code: str | None) -> str:
    target = result_write_target_by_code(code)
    if target is None:
        return str(code or "scheduled_job_result")
    return str(target["label"])
