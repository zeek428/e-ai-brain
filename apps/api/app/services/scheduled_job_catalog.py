from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.api.deps import require_any_permission

SCHEDULED_JOB_MANAGE_PERMISSION = "system.scheduled_jobs.manage"
SCHEDULED_JOB_RUN_PERMISSION = "system.scheduled_jobs.run"

SCHEDULED_JOB_TYPE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "allow_create": True,
        "category": "governance",
        "default_execution_mode": "ai_assisted",
        "label": "代码仓库巡检（质量 / 安全 / 规范）",
        "requires_product": True,
        "requires_plugin_resource": True,
        "runnable": True,
        "value": "code_repository_inspection",
    },
    {
        "allow_create": True,
        "category": "insights",
        "default_execution_mode": "ai_generated",
        "label": "用户反馈洞察抽取（取数 + AI 分析 + 写入）",
        "requires_ai_assembly": True,
        "requires_product": True,
        "requires_plugin_resource": True,
        "runnable": True,
        "value": "user_feedback_insight_extract",
    },
    {
        "allow_create": True,
        "category": "planning",
        "default_execution_mode": "ai_generated",
        "label": "迭代规划建议生成",
        "requires_ai_assembly": True,
        "runnable": True,
        "value": "iteration_plan_suggestion_generate",
    },
    {
        "allow_create": True,
        "category": "operations",
        "default_execution_mode": "ai_generated",
        "label": "线上日志 AI 分析",
        "requires_ai_assembly": True,
        "requires_plugin_resource": True,
        "runnable": True,
        "value": "online_log_ai_analysis",
    },
    {
        "allow_create": False,
        "category": "insights",
        "default_execution_mode": "deterministic",
        "label": "用户使用指标采集",
        "runnable": False,
        "unavailable_reason": "当前仅保留历史兼容类型，新增作业请使用内部数据源或插件执行调用。",
        "value": "user_usage_metric_collect",
    },
    {
        "allow_create": False,
        "category": "insights",
        "default_execution_mode": "deterministic",
        "label": "用户反馈采集（仅取数，不调用 AI）",
        "runnable": False,
        "unavailable_reason": "配置 AI 后会自动升级为用户反馈洞察抽取；纯取数请使用插件执行调用。",
        "value": "user_feedback_collect",
    },
    {
        "allow_create": False,
        "category": "operations",
        "default_execution_mode": "deterministic",
        "label": "线上日志指标采集",
        "runnable": False,
        "unavailable_reason": "当前仅保留历史兼容类型，新增作业请使用内部数据源或插件执行调用。",
        "value": "online_log_metric_collect",
    },
    {
        "allow_create": False,
        "category": "devops",
        "default_execution_mode": "deterministic",
        "label": "GitLab 每日代码指标采集",
        "runnable": False,
        "unavailable_reason": "当前仅保留历史兼容类型，新增作业请使用代码仓库巡检或插件执行调用。",
        "value": "gitlab_daily_code_metric_collect",
    },
    {
        "allow_create": False,
        "category": "devops",
        "default_execution_mode": "deterministic",
        "label": "Jenkins 发布记录采集",
        "runnable": False,
        "unavailable_reason": "当前仅保留历史兼容类型，新增作业请使用插件执行调用。",
        "value": "jenkins_release_collect",
    },
    {
        "allow_create": True,
        "category": "integration",
        "default_execution_mode": "deterministic",
        "label": "插件执行调用",
        "requires_plugin_resource": True,
        "runnable": True,
        "value": "plugin_action_invoke",
    },
    {
        "allow_create": False,
        "category": "dashboard",
        "default_execution_mode": "deterministic",
        "label": "看板快照刷新",
        "runnable": False,
        "unavailable_reason": "当前仅保留系统内部兼容类型，不作为用户新增定时作业入口。",
        "value": "dashboard_snapshot_refresh",
    },
    {
        "allow_create": False,
        "category": "lifecycle",
        "default_execution_mode": "deterministic",
        "label": "生命周期上下文刷新",
        "runnable": False,
        "unavailable_reason": "当前仅保留系统内部兼容类型，不作为用户新增定时作业入口。",
        "value": "lifecycle_context_refresh",
    },
    {
        "allow_create": False,
        "category": "operations",
        "default_execution_mode": "deterministic",
        "label": "待归属数据重试",
        "runnable": False,
        "unavailable_reason": "当前仅保留系统内部兼容类型，不作为用户新增定时作业入口。",
        "value": "pending_attribution_retry",
    },
]

SCHEDULED_JOB_TYPES = {definition["value"] for definition in SCHEDULED_JOB_TYPE_DEFINITIONS}
SCHEDULED_JOB_RUNNABLE_TYPES = {
    definition["value"]
    for definition in SCHEDULED_JOB_TYPE_DEFINITIONS
    if definition.get("runnable") is not False
}
AI_REQUIRED_SCHEDULED_JOB_TYPES = {
    definition["value"]
    for definition in SCHEDULED_JOB_TYPE_DEFINITIONS
    if definition.get("requires_ai_assembly")
}
PRODUCT_REQUIRED_SCHEDULED_JOB_TYPES = {
    definition["value"]
    for definition in SCHEDULED_JOB_TYPE_DEFINITIONS
    if definition.get("requires_product")
}
PLUGIN_RESOURCE_REQUIRED_SCHEDULED_JOB_TYPES = {
    definition["value"]
    for definition in SCHEDULED_JOB_TYPE_DEFINITIONS
    if definition.get("requires_plugin_resource")
}

SCHEDULED_JOB_EXECUTION_MODE_DEFINITIONS = [
    {"label": "不调用 AI", "value": "deterministic"},
    {"label": "AI 辅助", "value": "ai_assisted"},
    {"label": "AI 生成", "value": "ai_generated"},
]
SCHEDULED_JOB_EXECUTION_MODES = {
    definition["value"] for definition in SCHEDULED_JOB_EXECUTION_MODE_DEFINITIONS
}

SCHEDULED_JOB_SCHEDULE_TYPE_DEFINITIONS = [
    {"label": "手动触发", "value": "manual"},
    {"label": "Cron 定时", "value": "cron"},
    {"label": "固定间隔", "value": "interval"},
]
SCHEDULED_JOB_SCHEDULE_TYPES = {
    definition["value"] for definition in SCHEDULED_JOB_SCHEDULE_TYPE_DEFINITIONS
}


def scheduled_job_type_definition(job_type: str | None) -> dict[str, Any] | None:
    normalized = str(job_type or "")
    for definition in SCHEDULED_JOB_TYPE_DEFINITIONS:
        if definition["value"] == normalized:
            return deepcopy(definition)
    return None


def scheduled_job_type_is_runnable(job_type: str | None) -> bool:
    return str(job_type or "") in SCHEDULED_JOB_RUNNABLE_TYPES


def scheduled_job_type_allows_create(job_type: str | None) -> bool:
    definition = scheduled_job_type_definition(job_type)
    if definition is None:
        return False
    return definition.get("allow_create") is not False

CONNECTION_ENVIRONMENT_DEFINITIONS = [
    {"label": "默认", "value": "default"},
    {"label": "开发", "value": "dev"},
    {"label": "测试", "value": "test"},
    {"label": "预发", "value": "staging"},
    {"label": "生产", "value": "prod"},
    {"label": "沙箱", "value": "sandbox"},
]

NATIVE_CODE_INSPECTION_SCAN_MODE = "native_full_scan"
CODE_INSPECTION_SCAN_MODE_DEFINITIONS = [
    {"label": "本地完整扫描（clone 仓库）", "value": NATIVE_CODE_INSPECTION_SCAN_MODE},
    {"label": "同步已有告警", "value": "sync_existing_alerts"},
    {"label": "触发平台扫描", "value": "trigger_platform_scan"},
]
CODE_INSPECTION_SCAN_MODES = {
    definition["value"] for definition in CODE_INSPECTION_SCAN_MODE_DEFINITIONS
}
DEFAULT_CODE_INSPECTION_SCAN_MODE = "sync_existing_alerts"

CODE_INSPECTION_SCANNER_ENGINE_DEFINITIONS = [
    {"label": "内置规则", "value": "builtin"},
    {"label": "gitleaks 密钥扫描", "value": "gitleaks"},
    {"label": "semgrep 代码安全/规范", "value": "semgrep"},
    {"label": "trivy 依赖/镜像风险", "value": "trivy"},
    {"label": "npm audit", "value": "npm"},
    {"label": "pip-audit", "value": "pip-audit"},
    {"label": "mvn dependency-check", "value": "dependency-check"},
]
CODE_INSPECTION_BUILTIN_RULE_DEFINITIONS = [
    {"label": "硬编码凭据", "value": "secrets"},
    {"label": "内部地址暴露", "value": "internal_addresses"},
]
CODE_INSPECTION_IGNORE_RULE_DEFINITIONS = [
    {"label": "secrets.hardcoded_credential", "value": "secrets.hardcoded_credential"},
    {"label": "metadata.internal_address_exposure", "value": "metadata.internal_address_exposure"},
]
CODE_INSPECTION_RESULT_ACTION_DEFINITIONS = [
    {"label": "写入代码巡检报告", "value": "write_code_inspection_report"},
    {"label": "严重问题自动创建 Bug", "value": "create_bug_for_severe_findings"},
    {"label": "严重问题自动创建整改任务", "value": "create_task_for_severe_findings"},
    {"label": "发送问题消息通知", "value": "send_notification"},
]
GENERIC_RESULT_ACTION_DEFINITIONS = [
    {"label": "仅保存运行结果", "value": "save_scheduled_job_result"},
    {"label": "发送通知记录", "value": "send_notification"},
]
CODE_INSPECTION_SEVERITY_THRESHOLD_DEFINITIONS = [
    {"label": "critical", "value": "critical"},
    {"label": "high", "value": "high"},
    {"label": "medium", "value": "medium"},
]
DEFAULT_CODE_INSPECTION_RESULT_ACTIONS = [
    {"type": "write_code_inspection_report"},
    {"severity_threshold": "critical", "type": "create_bug_for_severe_findings"},
    {"severity_threshold": "high", "type": "create_task_for_severe_findings"},
    {"channels": ["email"], "recipients": [], "type": "send_notification"},
]


def list_scheduled_job_catalog_response(*, user: dict[str, Any]) -> dict[str, Any]:
    require_any_permission(user, {SCHEDULED_JOB_MANAGE_PERMISSION, SCHEDULED_JOB_RUN_PERMISSION})
    return {
        "code_inspection": {
            "builtin_rules": deepcopy(CODE_INSPECTION_BUILTIN_RULE_DEFINITIONS),
            "default_result_actions": deepcopy(DEFAULT_CODE_INSPECTION_RESULT_ACTIONS),
            "default_scan_mode": DEFAULT_CODE_INSPECTION_SCAN_MODE,
            "ignore_rules": deepcopy(CODE_INSPECTION_IGNORE_RULE_DEFINITIONS),
            "native_scan_mode": NATIVE_CODE_INSPECTION_SCAN_MODE,
            "result_actions": deepcopy(CODE_INSPECTION_RESULT_ACTION_DEFINITIONS),
            "scan_modes": deepcopy(CODE_INSPECTION_SCAN_MODE_DEFINITIONS),
            "scanner_engines": deepcopy(CODE_INSPECTION_SCANNER_ENGINE_DEFINITIONS),
            "severity_thresholds": deepcopy(CODE_INSPECTION_SEVERITY_THRESHOLD_DEFINITIONS),
        },
        "connection_environments": deepcopy(CONNECTION_ENVIRONMENT_DEFINITIONS),
        "execution_modes": deepcopy(SCHEDULED_JOB_EXECUTION_MODE_DEFINITIONS),
        "generic_result_actions": deepcopy(GENERIC_RESULT_ACTION_DEFINITIONS),
        "job_types": deepcopy(SCHEDULED_JOB_TYPE_DEFINITIONS),
        "required_job_types": {
            "ai_processing": sorted(AI_REQUIRED_SCHEDULED_JOB_TYPES),
            "plugin_resource": sorted(PLUGIN_RESOURCE_REQUIRED_SCHEDULED_JOB_TYPES),
            "product": sorted(PRODUCT_REQUIRED_SCHEDULED_JOB_TYPES),
        },
        "schedule_types": deepcopy(SCHEDULED_JOB_SCHEDULE_TYPE_DEFINITIONS),
    }
