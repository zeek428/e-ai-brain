from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

OPERATIONAL_REFERENCE_TYPES = {
    "ai_agent",
    "ai_skill",
    "plugin_action",
    "plugin_connection",
    "scheduled_job",
    "scheduled_job_run",
}
EXECUTION_TRACE_REFERENCE_TYPES = {
    "ai_executor_runner",
    "ai_executor_task",
    "assistant_chat_run",
    "assistant_message",
    "audit_event",
    "code_inspection_report",
    "model_gateway_log",
    "plugin_invocation_log",
    "result_write_record",
    "scheduled_job_stage",
}
ASSISTANT_ACTION_REFERENCE_TYPE = "assistant_action"
OPERATIONAL_REFERENCE_PERMISSIONS_BY_TYPE = {
    "ai_agent": ("system.ai_capabilities.manage",),
    "ai_skill": ("system.ai_capabilities.manage",),
    "plugin_action": ("system.plugins.manage",),
    "plugin_connection": ("system.plugins.manage",),
    "scheduled_job": ("system.scheduled_jobs.manage", "system.scheduled_jobs.run"),
    "scheduled_job_run": ("system.scheduled_jobs.manage", "system.scheduled_jobs.run"),
}
OPERATIONAL_REFERENCE_PERMISSION_LABEL_BY_PERMISSION = {
    "system.ai_capabilities.manage": "AI能力管理权限可引用",
    "system.plugins.manage": "插件管理权限可引用",
    "system.scheduled_jobs.manage": "定时作业管理权限可引用",
    "system.scheduled_jobs.run": "定时作业执行权限可引用",
}
REFERENCE_SOURCE_MODULES = {
    "assistant_action": "动作",
    "ai_executor_runner": "执行诊断",
    "ai_executor_task": "执行诊断",
    "ai_agent": "AI能力配置",
    "ai_skill": "AI能力配置",
    "assistant_chat_run": "执行诊断",
    "assistant_message": "执行诊断",
    "audit_event": "审计与诊断",
    "ai_task": "需求交付",
    "bug": "需求交付",
    "code_inspection_report": "执行诊断",
    "code_review_report": "需求交付",
    "human_review": "需求交付",
    "iteration_version": "需求交付",
    "product_version": "需求交付",
    "knowledge_deposit": "知识库",
    "knowledge_chunk": "知识库",
    "knowledge_document": "知识库",
    "knowledge_folder": "知识库",
    "knowledge_space": "知识库",
    "plugin_action": "插件管理",
    "plugin_connection": "插件管理",
    "plugin_invocation_log": "执行诊断",
    "product": "产品资产",
    "requirement": "需求交付",
    "model_gateway_log": "执行诊断",
    "result_write_record": "执行诊断",
    "scheduled_job": "任务中心",
    "scheduled_job_run": "任务中心",
    "scheduled_job_stage": "执行诊断",
}
DEFAULT_REFERENCE_TYPE_ORDER = (
    "assistant_action",
    "knowledge_document",
    "knowledge_chunk",
    "requirement",
    "ai_task",
    "scheduled_job",
    "scheduled_job_run",
    "plugin_action",
    "plugin_connection",
    "ai_agent",
    "ai_skill",
    "knowledge_space",
    "knowledge_folder",
    "assistant_chat_run",
    "model_gateway_log",
    "plugin_invocation_log",
    "ai_executor_task",
    "ai_executor_runner",
    "code_inspection_report",
    "result_write_record",
    "audit_event",
    "assistant_message",
    "human_review",
    "bug",
    "iteration_version",
    "product_version",
    "code_review_report",
    "knowledge_deposit",
    "product",
)
REFERENCE_TYPE_QUERY_ALIASES = {
    "assistant_action": ("新建", "新增", "创建", "配置", "草案"),
    "ai_agent": ("ai角色", "ai 角色", "智能体", "agent", "角色"),
    "ai_skill": ("skill", "能力", "ai能力", "ai 能力"),
    "ai_task": ("研发任务", "ai任务", "任务", "task"),
    "bug": ("bug", "缺陷", "阻塞"),
    "ai_executor_runner": ("runner", "执行器", "ai 执行器", "ai执行器"),
    "ai_executor_task": ("runner task", "执行器任务", "runner任务"),
    "assistant_chat_run": ("助手运行", "ai助手运行", "assistant run", "assistant_chat_run"),
    "assistant_message": ("助手消息", "assistant message", "assistant_message"),
    "audit_event": ("审计", "audit", "audit_event"),
    "code_inspection_report": ("代码巡检", "巡检报告", "inspection"),
    "code_review_report": ("代码评审", "代码巡检", "code review", "pr"),
    "human_review": ("确认", "待确认", "评审", "review"),
    "iteration_version": ("迭代", "版本", "version"),
    "product_version": ("迭代", "版本", "product version", "version"),
    "knowledge_chunk": ("知识片段", "chunk", "片段"),
    "knowledge_deposit": ("知识沉淀", "沉淀"),
    "knowledge_document": ("知识文档", "知识库", "文档"),
    "knowledge_folder": ("知识目录", "目录", "folder"),
    "knowledge_space": ("知识空间", "空间", "knowledge space"),
    "plugin_action": ("动作", "插件动作", "plugin action"),
    "plugin_connection": ("插件连接", "连接", "connection"),
    "plugin_invocation_log": ("插件调用", "调用日志", "plugin invocation"),
    "product": ("产品", "product"),
    "requirement": ("需求", "requirement"),
    "model_gateway_log": ("模型调用", "模型网关", "model gateway", "model_gateway_log"),
    "result_write_record": ("结果写入", "写入记录", "result write"),
    "scheduled_job_stage": ("作业阶段", "执行阶段", "scheduled_job_stage"),
    "scheduled_job": (
        "定时作业",
        "定时任务",
        "作业定义",
        "任务配置",
        "scheduled job",
        "job",
    ),
    "scheduled_job_run": (
        "运行记录",
        "运行实例",
        "执行记录",
        "执行结果",
        "失败",
        "failed",
        "run",
    ),
}
SCHEDULED_JOB_QUERY_KEYWORD_GROUPS = (
    ("用户反馈", "反馈", "feedback", "user feedback"),
    ("洞察", "insight", "insights"),
    ("每周", "周", "weekly"),
    ("提取", "抽取", "extract"),
    ("有价值", "价值", "信息", "summary", "summarize"),
    ("代码", "仓库", "code", "repository"),
    ("巡检", "质量", "安全", "规范", "inspection", "review"),
    ("邮件", "邮箱", "通知", "email", "mail", "notification"),
    ("日志", "分析", "log", "analysis"),
)
SCHEDULED_JOB_DOMAIN_GROUP_INDEXES = {0, 5, 7, 8}


def summary_excerpt(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) > 120:
        return f"{normalized[:117]}..."
    return normalized


def execution_trace_href(source_id: Any, source_type: str) -> str:
    return "/governance/execution-traces?" + urlencode(
        {"source_id": str(source_id), "source_type": source_type}
    )


def merge_reference_lists(
    *reference_lists: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for reference_list in reference_lists:
        for reference in reference_list:
            key = (str(reference.get("type")), str(reference.get("id")))
            if key in seen:
                continue
            if not all(reference.get(field) for field in ("id", "title", "type", "url")):
                continue
            seen.add(key)
            references.append(dict(reference))
            if len(references) >= limit:
                return references
    return references


def merge_reference_lists_by_type(
    *reference_lists: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    buckets: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str]] = set()
    for reference_list in reference_lists:
        for reference in reference_list:
            key = (str(reference.get("type")), str(reference.get("id")))
            if key in seen:
                continue
            if not all(reference.get(field) for field in ("id", "title", "type", "url")):
                continue
            seen.add(key)
            item = dict(reference)
            references.append(item)
            buckets.setdefault(str(item["type"]), []).append(item)

    merged: list[dict[str, Any]] = []
    merged_keys: set[tuple[str, str]] = set()
    for reference_type in DEFAULT_REFERENCE_TYPE_ORDER:
        for reference in buckets.get(reference_type, []):
            key = (str(reference["type"]), str(reference["id"]))
            if key in merged_keys:
                continue
            merged.append(reference)
            merged_keys.add(key)
            break
        if len(merged) >= limit:
            return merged

    for reference in references:
        key = (str(reference["type"]), str(reference["id"]))
        if key in merged_keys:
            continue
        merged.append(reference)
        merged_keys.add(key)
        if len(merged) >= limit:
            break
    return merged


def assistant_reference_type_preferences(message: str) -> dict[str, int]:
    normalized = message.lower()
    ordered: list[str] = []
    keyword_map = [
        (("需求", "requirement"), ["requirement"]),
        (("运行记录", "运行", "run", "失败"), ["scheduled_job_run"]),
        (("bug", "缺陷", "阻塞"), ["bug", "requirement"]),
        (("任务", "task"), ["ai_task", "human_review"]),
        (
            ("定时作业", "定时任务", "定时", "作业", "scheduled", "schedule"),
            ["scheduled_job"],
        ),
        (("动作", "插件动作", "plugin action"), ["plugin_action"]),
        (("插件连接", "连接失败", "connection"), ["plugin_connection"]),
        (("ai角色", "agent", "角色"), ["ai_agent"]),
        (("skill", "能力"), ["ai_skill"]),
        (("review", "确认", "评审"), ["human_review", "code_review_report", "ai_task"]),
        (("迭代", "版本", "version"), ["iteration_version", "product_version", "requirement"]),
        (("产品", "product"), ["product"]),
        (("代码", "pr", "github"), ["code_review_report", "ai_task"]),
        (("知识空间", "knowledge space"), ["knowledge_space"]),
        (("知识目录", "目录", "folder"), ["knowledge_folder"]),
        (("知识", "沉淀"), ["knowledge_deposit"]),
    ]
    for keywords, entity_types in keyword_map:
        if any(keyword in normalized for keyword in keywords):
            ordered.extend(entity_types)
    ordered.extend(
        [
            "requirement",
            "ai_task",
            "human_review",
            "bug",
            "iteration_version",
            "product_version",
            "code_review_report",
            "knowledge_deposit",
            "knowledge_space",
            "knowledge_folder",
            "product",
            "scheduled_job_run",
            "scheduled_job",
            "plugin_action",
            "plugin_connection",
            "ai_agent",
            "ai_skill",
        ]
    )
    preferences: dict[str, int] = {}
    for entity_type in ordered:
        preferences.setdefault(entity_type, len(preferences))
    return preferences


def assistant_reference_sort_key(item: dict[str, Any]) -> str:
    return str(
        item.get("updated_at")
        or item.get("created_at")
        or item.get("last_message_at")
        or item.get("id")
        or ""
    )


def assistant_reference_for_entity(
    entity_type: str,
    item: dict[str, Any],
    *,
    current_store: Any | None = None,
) -> dict[str, Any] | None:
    item_id = item.get("id")
    if item_id is None:
        return None
    title = assistant_reference_title(entity_type, item, current_store=current_store)
    route_map = {
        "ai_agent": f"/tasks/ai-capabilities?agent_id={item_id}",
        "ai_executor_runner": execution_trace_href(item_id, "ai_executor_runner"),
        "ai_executor_task": execution_trace_href(item_id, "ai_executor_task"),
        "ai_skill": f"/tasks/ai-capabilities?skill_id={item_id}",
        "ai_task": f"/delivery/rd-tasks?task_id={item_id}",
        "assistant_chat_run": execution_trace_href(item_id, "assistant_chat_run"),
        "assistant_message": execution_trace_href(item_id, "assistant_message"),
        "audit_event": execution_trace_href(item_id, "audit_event"),
        "bug": f"/delivery/bugs?bug_id={item_id}",
        "code_inspection_report": execution_trace_href(item_id, "code_inspection_report"),
        "code_review_report": f"/delivery/rd-tasks?code_review_report_id={item_id}",
        "human_review": f"/delivery/rd-tasks?review_id={item_id}",
        "iteration_version": f"/delivery/versions?version_id={item_id}",
        "product_version": f"/delivery/versions?version_id={item_id}",
        "knowledge_deposit": f"/knowledge/documents?deposit_id={item_id}",
        "knowledge_folder": (
            f"/knowledge/documents?knowledge_space_id={item.get('knowledge_space_id')}"
            f"&folder_id={item_id}"
        ),
        "knowledge_space": f"/knowledge/documents?knowledge_space_id={item_id}",
        "model_gateway_log": execution_trace_href(item_id, "model_gateway_log"),
        "plugin_action": f"/tasks/plugins?action_id={item_id}",
        "plugin_connection": f"/tasks/plugins?connection_id={item_id}",
        "plugin_invocation_log": execution_trace_href(item_id, "plugin_invocation_log"),
        "product": f"/assets/products?product_id={item_id}",
        "requirement": f"/delivery/requirements?requirement_id={item_id}",
        "result_write_record": execution_trace_href(item_id, "result_write_record"),
        "scheduled_job": f"/tasks/scheduled-jobs?job_id={item_id}",
        "scheduled_job_run": f"/tasks/scheduled-jobs?run_id={item_id}",
        "scheduled_job_stage": execution_trace_href(item_id, "scheduled_job_stage"),
    }
    url = route_map.get(entity_type)
    if url is None:
        return None
    reference: dict[str, Any] = {
        "id": str(item_id),
        "title": str(title),
        "type": entity_type,
        "url": url,
    }
    summary = assistant_reference_summary(entity_type, item)
    if summary:
        reference["summary"] = summary
    return reference


def assistant_reference_title(
    entity_type: str,
    item: dict[str, Any],
    *,
    current_store: Any | None,
) -> str:
    if entity_type == "knowledge_folder":
        return str(item.get("path") or item.get("name") or item.get("id") or "")
    if entity_type == "ai_executor_runner":
        title = item.get("name") or item.get("runner_name") or item.get("id")
        status = item.get("status")
        return f"AI 执行器 Runner {title} / {status}" if status else f"AI 执行器 Runner {title}"
    if entity_type == "ai_executor_task":
        return f"AI 执行器任务 {item.get('id')} / {item.get('status') or 'unknown'}"
    if entity_type == "assistant_chat_run":
        return f"AI 助手运行 {item.get('id')} / {item.get('status') or 'unknown'}"
    if entity_type == "assistant_message":
        return f"AI 助手消息 {item.get('id')}"
    if entity_type == "audit_event":
        return f"审计事件 {item.get('event_type') or item.get('id')}"
    if entity_type == "code_inspection_report":
        return str(
            item.get("summary")
            or item.get("title")
            or f"代码巡检报告 {item.get('id')}"
        )
    if entity_type == "model_gateway_log":
        return f"模型网关调用 {item.get('id')} / {item.get('status') or 'unknown'}"
    if entity_type == "plugin_invocation_log":
        return f"插件调用 {item.get('id')} / {item.get('status') or 'unknown'}"
    if entity_type == "result_write_record":
        return f"结果写入记录 {item.get('id')} / {item.get('status') or 'unknown'}"
    if entity_type == "scheduled_job_stage":
        return f"作业阶段 {item.get('id')} / {item.get('status') or 'unknown'}"
    if entity_type == "scheduled_job_run":
        job_id = item.get("scheduled_job_id")
        job = (
            getattr(current_store, "scheduled_jobs", {}).get(str(job_id))
            if current_store is not None and job_id is not None
            else None
        )
        job_title = job.get("name") if isinstance(job, dict) else None
        return f"{job_title or job_id or item.get('id')} / {item.get('status') or 'unknown'}"
    return str(
        item.get("title")
        or item.get("name")
        or item.get("summary")
        or item.get("code")
        or item.get("id")
        or ""
    )


def assistant_reference_summary(entity_type: str, item: dict[str, Any]) -> str | None:
    summary_fields_by_type = {
        "ai_executor_runner": ("last_error", "health_message", "summary"),
        "ai_executor_task": ("error_message", "summary", "result_summary"),
        "assistant_chat_run": ("error_message", "summary", "status"),
        "assistant_message": ("summary", "role", "content_preview"),
        "audit_event": ("summary", "event_type", "action"),
        "code_inspection_report": ("summary", "repository", "branch"),
        "model_gateway_log": ("error", "error_message", "purpose", "model"),
        "plugin_invocation_log": ("error_message", "summary", "action_id"),
        "result_write_record": ("error_message", "summary", "write_target"),
        "scheduled_job_stage": ("error_message", "summary", "stage"),
    }
    for field in summary_fields_by_type.get(entity_type, ("summary",)):
        value = str(item.get(field) or "").strip()
        if value:
            return summary_excerpt(value)
    return None


def assistant_reference_matches_query(
    entity_type: str,
    item: dict[str, Any],
    query: str,
    *,
    current_store: Any | None,
) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True
    title = assistant_reference_title(entity_type, item, current_store=current_store)
    haystack = " ".join(
        str(value or "")
        for value in (
            item.get("id"),
            item.get("code"),
            item.get("conversation_id"),
            item.get("description"),
            item.get("error"),
            item.get("error_code"),
            item.get("error_message"),
            item.get("event_type"),
            item.get("name"),
            item.get("path"),
            item.get("provider"),
            item.get("purpose"),
            item.get("model"),
            item.get("result_id"),
            item.get("result_type"),
            item.get("runner_id"),
            item.get("status"),
            item.get("summary"),
            item.get("title"),
            item.get("write_target"),
            title,
        )
    ).lower()
    if normalized_query in haystack:
        return True
    if assistant_reference_matches_type_alias(entity_type, normalized_query):
        return True
    return scheduled_job_reference_matches_semantic_query(
        entity_type,
        normalized_query,
        haystack,
    )


def assistant_reference_matches_type_alias(entity_type: str, normalized_query: str) -> bool:
    aliases = REFERENCE_TYPE_QUERY_ALIASES.get(entity_type, ())
    return any(alias in normalized_query or normalized_query in alias for alias in aliases)


def scheduled_job_reference_matches_semantic_query(
    entity_type: str,
    normalized_query: str,
    haystack: str,
) -> bool:
    if entity_type not in {"scheduled_job", "scheduled_job_run"}:
        return False
    query_groups = scheduled_job_keyword_group_indexes(normalized_query)
    if len(query_groups) < 2:
        return False
    haystack_groups = scheduled_job_keyword_group_indexes(haystack)
    overlap = query_groups & haystack_groups
    if len(overlap) < 2:
        return False
    return bool(overlap & SCHEDULED_JOB_DOMAIN_GROUP_INDEXES)


def scheduled_job_keyword_group_indexes(value: str) -> set[int]:
    return {
        index
        for index, keywords in enumerate(SCHEDULED_JOB_QUERY_KEYWORD_GROUPS)
        if any(keyword in value for keyword in keywords)
    }


def reference_permission_label(
    user: dict[str, Any] | None,
    reference_type: str,
) -> str:
    if reference_type in EXECUTION_TRACE_REFERENCE_TYPES:
        roles = set(user.get("roles") or []) if isinstance(user, dict) else set()
        permissions = set(user.get("permissions") or []) if isinstance(user, dict) else set()
        if "admin" in roles or "system.admin" in permissions:
            return "管理员可引用"
        if "diagnostics.execution_traces.read" in permissions:
            return "执行诊断权限可引用"
        return "需授权"
    if reference_type not in OPERATIONAL_REFERENCE_TYPES:
        return "可引用"
    roles = set(user.get("roles") or []) if isinstance(user, dict) else set()
    permissions = set(user.get("permissions") or []) if isinstance(user, dict) else set()
    if "admin" in roles or "system.admin" in permissions:
        return "管理员可引用"
    required_permissions = OPERATIONAL_REFERENCE_PERMISSIONS_BY_TYPE.get(reference_type) or ()
    granted_permission = next(
        (permission for permission in required_permissions if permission in permissions),
        None,
    )
    if granted_permission:
        return OPERATIONAL_REFERENCE_PERMISSION_LABEL_BY_PERMISSION.get(
            granted_permission,
            "已授权可引用",
        )
    return "需授权"
