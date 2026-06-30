from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.assistant_draft_builder import AssistantDraftBuilder
from app.services.assistant_references import normalize_assistant_references
from app.services.plugin_result_write_records import result_write_record_from_scheduled_run
from app.services.product_version_dashboard import product_version_dashboard_response

__all__ = ["assistant_tool_results"]


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _read_memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, list) else []


def assistant_tool_results(
    current_store: Any,
    *,
    message: str,
    product_id: str | None,
    references: list[dict[str, Any]] | None = None,
    limit: int = 5,
    user: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic read-model style tools used before asking the model."""

    context = _assistant_read_context(current_store, product_id=product_id)
    intents = _assistant_tool_intents(message, references=references or [])
    draft_builder = AssistantDraftBuilder(context)
    results: list[dict[str, Any]] = []
    for intent in intents:
        if intent == "rd_task_draft":
            results.append(
                draft_builder.rd_task_draft(
                    message=message,
                    references=references or [],
                )
            )
        elif intent == "plugin_connection_draft":
            results.append(draft_builder.plugin_connection_draft(message=message))
        elif intent == "plugin_connection_diagnostic":
            results.append(_plugin_connection_diagnostic_tool(context, limit=limit))
        elif intent == "plugin_action_draft":
            results.append(draft_builder.plugin_action_draft(message=message))
        elif intent == "ai_capability_draft":
            results.append(draft_builder.ai_capability_draft(message=message))
        elif intent == "code_inspection_job_draft":
            results.append(draft_builder.code_inspection_job_draft(message=message))
        elif intent == "email_digest_job_draft":
            results.append(draft_builder.email_digest_job_draft())
        elif intent == "online_log_anomaly_job_draft":
            results.append(draft_builder.online_log_anomaly_job_draft())
        elif intent == "knowledge_base_inspection_draft":
            results.append(draft_builder.knowledge_base_inspection_draft())
        elif intent == "release_risk_analysis_draft":
            results.append(draft_builder.release_risk_analysis_draft())
        elif intent == "scheduled_job_draft":
            results.append(draft_builder.scheduled_job_draft())
        elif intent == "scheduled_job_run_repair_draft":
            results.append(
                _scheduled_job_run_repair_draft_tool(
                    context,
                    limit=limit,
                    references=references or [],
                )
            )
        elif intent == "scheduled_job_diagnostic":
            results.append(
                _scheduled_job_diagnostic_tool(
                    context,
                    limit=limit,
                    references=references or [],
                )
            )
        elif intent == "scheduled_job_run_comparison":
            results.append(
                _scheduled_job_run_comparison_tool(
                    context,
                    limit=limit,
                    references=references or [],
                )
            )
        elif intent == "delivery_progress":
            results.append(_delivery_progress_tool(context, limit=limit))
        elif intent == "pending_reviews":
            results.append(_pending_reviews_tool(context, limit=limit))
        elif intent == "code_review":
            results.append(_code_review_tool(context, limit=limit))
        elif intent == "iteration":
            results.append(
                _iteration_tool(
                    current_store,
                    context,
                    limit=limit,
                    user=user,
                )
            )
        elif intent == "bugs":
            results.append(_bugs_tool(context, limit=limit))
        elif intent == "model_gateway":
            results.append(_model_gateway_tool(current_store))
    return [result for result in results if result.get("items") or result.get("summary")]


def _assistant_read_context(current_store: Any, *, product_id: str | None) -> dict[str, Any]:
    products = list(_read_memory_dict(current_store, "products").values())
    if product_id:
        products = [product for product in products if product.get("id") == product_id]
    product_ids = {str(product["id"]) for product in products if product.get("id") is not None}
    requirements = [
        requirement
        for requirement in _read_memory_dict(current_store, "requirements").values()
        if not product_ids or requirement.get("product_id") in product_ids
    ]
    tasks = [
        task
        for task in _read_memory_dict(current_store, "ai_tasks").values()
        if not product_ids or task.get("product_id") in product_ids
    ]
    task_ids = {str(task["id"]) for task in tasks if task.get("id") is not None}
    scheduled_jobs = [
        job
        for job in _read_memory_dict(current_store, "scheduled_jobs").values()
        if not product_ids or job.get("product_id") in product_ids
    ]
    scheduled_job_ids = {
        str(job["id"]) for job in scheduled_jobs if job.get("id") is not None
    }
    scheduled_job_runs = [
        run
        for run in _read_memory_dict(current_store, "scheduled_job_runs").values()
        if not product_ids or str(run.get("scheduled_job_id")) in scheduled_job_ids
    ]
    result_write_records = []
    for run in scheduled_job_runs:
        record = result_write_record_from_scheduled_run(current_store, run)
        if record is not None:
            result_write_records.append(record)
    return {
        "ai_agents": list(_read_memory_dict(current_store, "ai_agents").values()),
        "ai_skills": list(_read_memory_dict(current_store, "ai_skills").values()),
        "bugs": [
            bug
            for bug in _read_memory_dict(current_store, "bugs").values()
            if not product_ids or bug.get("product_id") in product_ids
        ],
        "code_review_reports": [
            report
            for report in _read_memory_dict(current_store, "code_review_reports").values()
            if str(report.get("task_id")) in task_ids
        ],
        "human_reviews": [
            review
            for review in _read_memory_dict(current_store, "human_reviews").values()
            if str(review.get("ai_task_id")) in task_ids
        ],
        "integration_plugins": list(
            _read_memory_dict(current_store, "integration_plugins").values()
        ),
        "knowledge_deposits": list(
            _read_memory_dict(current_store, "knowledge_deposits").values()
        ),
        "knowledge_documents": list(
            _read_memory_dict(current_store, "knowledge_documents").values()
        ),
        "model_gateway_configs": list(
            _read_memory_dict(current_store, "model_gateway_configs").values()
        ),
        "model_gateway_logs": list(_read_memory_list(current_store, "model_gateway_logs")),
        "plugin_actions": list(_read_memory_dict(current_store, "plugin_actions").values()),
        "plugin_connections": list(_read_memory_dict(current_store, "plugin_connections").values()),
        "plugin_invocation_logs": list(
            _read_memory_dict(current_store, "plugin_invocation_logs").values()
        ),
        "products": products,
        "requirements": requirements,
        "result_write_records": result_write_records,
        "scheduled_jobs": scheduled_jobs,
        "scheduled_job_runs": scheduled_job_runs,
        "tasks": tasks,
        "task_by_id": {str(task["id"]): task for task in tasks if task.get("id") is not None},
        "versions": [
            version
            for version in _read_memory_dict(current_store, "product_versions").values()
            if not product_ids or version.get("product_id") in product_ids
        ],
    }


def _assistant_tool_intents(
    message: str,
    *,
    references: list[dict[str, Any]] | None = None,
) -> list[str]:
    normalized = message.lower()
    has_run_reference = _has_reference_type(references or [], "scheduled_job_run")
    intents: list[str] = []
    if _rd_task_draft_requested(normalized):
        intents.append("rd_task_draft")
    if _plugin_connection_draft_requested(normalized):
        intents.append("plugin_connection_draft")
    if _plugin_connection_diagnostic_requested(normalized):
        intents.append("plugin_connection_diagnostic")
    if _plugin_action_draft_requested(normalized):
        intents.append("plugin_action_draft")
    if _ai_capability_draft_requested(normalized):
        intents.append("ai_capability_draft")
    if _scheduled_job_draft_requested(normalized):
        if _code_inspection_draft_requested(normalized):
            intents.append("code_inspection_job_draft")
        elif _email_digest_draft_requested(normalized):
            intents.append("email_digest_job_draft")
        elif _online_log_anomaly_draft_requested(normalized):
            intents.append("online_log_anomaly_job_draft")
        else:
            intents.append("scheduled_job_draft")
    if _knowledge_base_inspection_draft_requested(normalized):
        intents.append("knowledge_base_inspection_draft")
    if _release_risk_analysis_draft_requested(normalized):
        intents.append("release_risk_analysis_draft")
    if _scheduled_job_run_repair_draft_requested(normalized):
        intents.append("scheduled_job_run_repair_draft")
    if _scheduled_job_run_comparison_requested(normalized, has_run_reference=has_run_reference):
        intents.append("scheduled_job_run_comparison")
    if _scheduled_job_diagnostic_requested(normalized, has_run_reference=has_run_reference):
        intents.append("scheduled_job_diagnostic")
    keyword_map = [
        (("进展", "进度", "全链路", "项目", "开发情况", "progress"), "delivery_progress"),
        (("待确认", "review", "评审", "确认"), "pending_reviews"),
        (("代码", "pr", "mr", "github", "review 报告", "代码评审"), "code_review"),
        (("迭代", "版本", "version"), "iteration"),
        (("bug", "缺陷", "阻塞", "风险"), "bugs"),
        (("模型", "网关", "gateway", "chat", "embedding"), "model_gateway"),
    ]
    for keywords, intent in keyword_map:
        if any(keyword in normalized for keyword in keywords):
            intents.append(intent)
    if not intents:
        intents = ["delivery_progress", "pending_reviews", "bugs"]
    return _unique(intents)[:4]


def _has_reference_type(references: list[dict[str, Any]], reference_type: str) -> bool:
    return any(reference.get("type") == reference_type for reference in references)


def _scheduled_job_diagnostic_requested(
    normalized_message: str,
    *,
    has_run_reference: bool = False,
) -> bool:
    has_diagnostic_intent = any(
        keyword in normalized_message
        for keyword in ("为什么", "原因", "失败", "诊断", "排查", "failed", "failure", "diagnose")
    )
    has_scheduled_job_context = any(
        keyword in normalized_message
        for keyword in ("定时任务", "定时作业", "作业", "任务", "scheduled job", "run")
    )
    return has_diagnostic_intent and (has_scheduled_job_context or has_run_reference)


def _scheduled_job_run_comparison_requested(
    normalized_message: str,
    *,
    has_run_reference: bool = False,
) -> bool:
    has_compare_intent = any(
        keyword in normalized_message
        for keyword in (
            "上次成功",
            "上一次成功",
            "有什么不同",
            "差异",
            "对比",
            "不同",
            "compare",
            "difference",
            "last success",
        )
    )
    has_run_context = any(
        keyword in normalized_message
        for keyword in ("这次", "本次", "任务", "作业", "运行", "scheduled job", "run")
    )
    return has_compare_intent and (has_run_context or has_run_reference)


def _scheduled_job_run_repair_draft_requested(normalized_message: str) -> bool:
    has_repair_intent = any(
        keyword in normalized_message
        for keyword in (
            "怎么修",
            "如何修",
            "修复",
            "修复草案",
            "修复建议",
            "repair",
            "fix",
        )
    )
    has_draft_intent = any(
        keyword in normalized_message
        for keyword in ("草案", "生成", "创建", "draft", "create")
    )
    return has_repair_intent and has_draft_intent


def _rd_task_draft_requested(normalized_message: str) -> bool:
    has_create_intent = any(
        keyword in normalized_message
        for keyword in ("创建", "新增", "新建", "生成", "增加", "create", "add", "draft")
    )
    has_rd_task = any(
        keyword in normalized_message
        for keyword in (
            "研发任务",
            "ai任务",
            "ai 任务",
            "普通任务",
            "产品详细设计",
            "产品细节设计",
            "product detail design",
            "rd task",
        )
    )
    return has_create_intent and has_rd_task


def _scheduled_job_draft_requested(normalized_message: str) -> bool:
    has_create_intent = any(
        keyword in normalized_message
        for keyword in ("创建", "新增", "配置", "生成", "新建", "create", "draft")
    )
    has_scheduled_job = any(
        keyword in normalized_message
        for keyword in ("定时作业", "定时任务", "scheduled job", "schedule")
    )
    has_weekly_feedback = any(
        keyword in normalized_message
        for keyword in ("用户反馈", "周反馈", "每周", "feedback", "maxcompute")
    )
    return (
        has_create_intent
        and has_scheduled_job
        and (
            has_weekly_feedback
            or _code_inspection_draft_requested(normalized_message)
            or _email_digest_draft_requested(normalized_message)
            or _online_log_anomaly_draft_requested(normalized_message)
        )
    )


def _email_digest_draft_requested(normalized_message: str) -> bool:
    return any(
        keyword in normalized_message
        for keyword in (
            "邮件摘要",
            "邮件收取",
            "邮箱摘要",
            "邮箱收取",
            "email digest",
            "email summary",
            "mail digest",
        )
    )


def _code_inspection_draft_requested(normalized_message: str) -> bool:
    return any(
        keyword in normalized_message
        for keyword in (
            "代码巡检",
            "质量",
            "安全",
            "规范",
            "code inspection",
            "github",
            "gitlab",
            "扫描",
        )
    )


def _online_log_anomaly_draft_requested(normalized_message: str) -> bool:
    return any(
        keyword in normalized_message
        for keyword in (
            "线上日志异常",
            "线上日志分析",
            "日志异常",
            "日志分析",
            "online log anomaly",
            "online_log_anomaly",
            "online_log",
            "log anomaly",
        )
    )


def _ai_capability_draft_requested(normalized_message: str) -> bool:
    has_create_intent = any(
        keyword in normalized_message
        for keyword in ("创建", "新增", "配置", "生成", "新建", "create", "draft")
    )
    has_ai_capability = any(
        keyword in normalized_message
        for keyword in (
            "ai 能力",
            "ai能力",
            "ai 角色",
            "ai角色",
            "模型能力",
            "智能体",
            "skill",
            "agent",
        )
    )
    has_supported_scenario = _code_inspection_draft_requested(
        normalized_message
    ) or _online_log_anomaly_draft_requested(normalized_message)
    return (
        has_create_intent
        and has_ai_capability
        and has_supported_scenario
        and not _scheduled_job_draft_requested(normalized_message)
    )


def _knowledge_base_inspection_draft_requested(normalized_message: str) -> bool:
    has_create_intent = any(
        keyword in normalized_message
        for keyword in ("创建", "新增", "配置", "生成", "新建", "create", "draft")
    )
    has_knowledge_inspection = any(
        keyword in normalized_message
        for keyword in (
            "知识库巡检",
            "知识巡检",
            "知识库检查",
            "知识治理",
            "knowledge inspection",
        )
    )
    return has_create_intent and has_knowledge_inspection


def _release_risk_analysis_draft_requested(normalized_message: str) -> bool:
    has_create_intent = any(
        keyword in normalized_message
        for keyword in ("创建", "新增", "配置", "生成", "新建", "create", "draft")
    )
    has_release_risk = any(
        keyword in normalized_message
        for keyword in (
            "发布风险分析",
            "发布风险",
            "版本风险",
            "release risk",
            "release analysis",
        )
    )
    return has_create_intent and has_release_risk


def _plugin_action_draft_requested(normalized_message: str) -> bool:
    has_create_intent = any(
        keyword in normalized_message
        for keyword in ("创建", "新增", "配置", "生成", "新建", "create", "draft")
    )
    has_action = any(
        keyword in normalized_message
        for keyword in ("插件动作", "动作", "结果动作", "plugin action", "action")
    )
    has_supported_template = any(
        keyword in normalized_message
        for keyword in (
            "github",
            "gitlab",
            "邮箱",
            "邮件",
            "email",
            "代码巡检",
            "安全告警",
            "通知",
        )
    )
    return (
        has_create_intent
        and has_action
        and has_supported_template
        and not _scheduled_job_draft_requested(normalized_message)
    )


def _plugin_connection_draft_requested(normalized_message: str) -> bool:
    has_create_intent = any(
        keyword in normalized_message
        for keyword in ("创建", "新增", "配置", "生成", "新建", "接入", "create", "draft")
    )
    has_connection = any(
        keyword in normalized_message
        for keyword in ("插件连接", "连接", "接入配置", "connection", "connector")
    )
    has_supported_plugin = any(
        keyword in normalized_message
        for keyword in ("github", "gitlab", "代码仓库", "代码托管", "邮箱", "邮件", "email")
    )
    return (
        has_create_intent
        and has_connection
        and has_supported_plugin
        and not _scheduled_job_draft_requested(normalized_message)
        and not _plugin_action_draft_requested(normalized_message)
    )


def _plugin_connection_diagnostic_requested(normalized_message: str) -> bool:
    has_connection_context = any(
        keyword in normalized_message
        for keyword in (
            "插件连接",
            "连接失败",
            "连接不可用",
            "connection",
            "connector",
        )
    )
    has_failure_intent = any(
        keyword in normalized_message
        for keyword in (
            "为什么",
            "原因",
            "失败",
            "不可用",
            "诊断",
            "排查",
            "怎么修",
            "修复",
            "failed",
            "failure",
            "diagnose",
            "repair",
            "fix",
        )
    )
    has_create_intent = any(
        keyword in normalized_message
        for keyword in ("创建", "新增", "配置", "生成", "新建", "接入", "create", "draft")
    )
    return has_connection_context and has_failure_intent and not has_create_intent


def _delivery_progress_tool(context: dict[str, Any], *, limit: int) -> dict[str, Any]:
    requirements = context["requirements"]
    tasks = context["tasks"]
    items = [
        {
            "id": requirement["id"],
            "priority": requirement.get("priority"),
            "status": requirement.get("status"),
            "title": requirement.get("title"),
            "url": f"/delivery/requirements?requirement_id={requirement['id']}",
            "version_id": requirement.get("version_id"),
        }
        for requirement in _latest(requirements)[:limit]
    ]
    return {
        "intent": "delivery_progress",
        "items": items,
        "references": _references("requirement", items),
        "summary": {
            "requirements_by_status": _count_by(requirements, "status"),
            "requirements_total": len(requirements),
            "tasks_by_status": _count_by(tasks, "status"),
            "tasks_total": len(tasks),
        },
        "tool": "assistant.delivery_progress",
    }


def _pending_reviews_tool(context: dict[str, Any], *, limit: int) -> dict[str, Any]:
    task_by_id = context["task_by_id"]
    pending_reviews = [
        review for review in context["human_reviews"] if review.get("status") == "pending"
    ]
    items = [
        {
            "ai_task_id": review.get("ai_task_id"),
            "id": review["id"],
            "review_type": review.get("review_type"),
            "status": review.get("status"),
            "task_title": task_by_id.get(str(review.get("ai_task_id")), {}).get("title"),
            "title": review.get("title") or review["id"],
            "url": f"/delivery/rd-tasks?review_id={review['id']}",
        }
        for review in _latest(pending_reviews)[:limit]
    ]
    return {
        "intent": "pending_reviews",
        "items": items,
        "references": _references("human_review", items),
        "summary": {"pending_review_count": len(pending_reviews)},
        "tool": "assistant.pending_reviews",
    }


def _code_review_tool(context: dict[str, Any], *, limit: int) -> dict[str, Any]:
    task_by_id = context["task_by_id"]
    reports = context["code_review_reports"]
    items = [
        {
            "finding_count": len(report.get("findings") or []),
            "id": report["id"],
            "risk_level": report.get("risk_level"),
            "status": report.get("status"),
            "summary": report.get("summary"),
            "task_id": report.get("task_id"),
            "task_title": task_by_id.get(str(report.get("task_id")), {}).get("title"),
            "title": report.get("summary") or report["id"],
            "url": f"/delivery/rd-tasks?code_review_report_id={report['id']}",
        }
        for report in _latest(reports)[:limit]
    ]
    return {
        "intent": "code_review",
        "items": items,
        "references": _references("code_review_report", items),
        "summary": {"code_review_report_count": len(reports)},
        "tool": "assistant.code_review",
    }


def _iteration_tool(
    current_store: Any,
    context: dict[str, Any],
    *,
    limit: int,
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    requirements = context["requirements"]
    tasks = context["tasks"]
    bugs = context["bugs"]
    items = []
    for version in _latest(context["versions"])[:limit]:
        version_requirements = [
            requirement
            for requirement in requirements
            if requirement.get("version_id") == version["id"]
        ]
        version_requirement_ids = {requirement["id"] for requirement in version_requirements}
        version_tasks = [
            task
            for task in tasks
            if task.get("version_id") == version["id"]
            or task.get("requirement_id") in version_requirement_ids
        ]
        version_bugs = [bug for bug in bugs if bug.get("version_id") == version["id"]]
        item = {
            "bug_count": len(version_bugs),
            "code": version.get("code"),
            "id": version["id"],
            "requirement_count": len(version_requirements),
            "requirements_by_status": _count_by(version_requirements, "status"),
            "status": version.get("status"),
            "task_count": len(version_tasks),
            "title": version.get("name") or version.get("code") or version["id"],
            "url": f"/delivery/versions?version_id={version['id']}&view=dashboard",
        }
        item.update(
            _iteration_dashboard_governance(
                current_store,
                str(version["id"]),
                user=user,
            )
        )
        items.append(item)
    return {
        "intent": "iteration",
        "items": items,
        "references": _references("iteration_version", items),
        "summary": {"version_count": len(context["versions"])},
        "tool": "assistant.iteration",
    }


def _iteration_dashboard_governance(
    current_store: Any,
    version_id: str,
    *,
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    if user is None:
        return {}
    try:
        dashboard = product_version_dashboard_response(
            current_store=current_store,
            user=user,
            version_id=version_id,
        )
    except Exception:
        return {}
    if not dashboard:
        return {}
    summary = dashboard.get("summary") or {}
    blockers = dashboard.get("blockers") or []
    return {
        "blocker_count": _safe_int(summary.get("blockers")),
        "blockers_by_source": _count_by(blockers, "source_type"),
        "dashboard_url": f"/delivery/versions?version_id={version_id}&view=dashboard",
        "governance_conclusion": dashboard.get("governance_conclusion") or {},
        "next_actions": [
            _iteration_next_action(action)
            for action in (dashboard.get("next_actions") or [])[:3]
            if isinstance(action, dict)
        ],
        "status_impact": _iteration_status_impact(dashboard.get("status_impact")),
    }


def _iteration_next_action(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_label": action.get("action_label"),
        "action_target_id": action.get("action_target_id"),
        "action_target_type": action.get("action_target_type"),
        "full_chain_subject_id": action.get("full_chain_subject_id"),
        "full_chain_subject_type": action.get("full_chain_subject_type"),
        "priority": _safe_int(action.get("priority")),
        "reason": action.get("reason"),
        "resolution_hint": action.get("resolution_hint"),
        "severity": action.get("severity"),
        "source_label": action.get("source_label"),
        "source_type": action.get("source_type"),
        "title": action.get("title"),
    }


def _iteration_status_impact(status_impact: Any) -> dict[str, Any]:
    if not isinstance(status_impact, dict) or not status_impact:
        return {}
    return {
        "blocked_count": _safe_int(status_impact.get("blocked_count")),
        "from_status": status_impact.get("from_status"),
        "target_status": status_impact.get("target_status"),
        "unchanged_count": _safe_int(status_impact.get("unchanged_count")),
        "updated_count": _safe_int(status_impact.get("updated_count")),
    }


def _bugs_tool(context: dict[str, Any], *, limit: int) -> dict[str, Any]:
    bugs = context["bugs"]
    open_bugs = [bug for bug in bugs if bug.get("status") != "closed"]
    high_severity_open = [
        bug for bug in open_bugs if bug.get("severity") in {"blocker", "critical", "major"}
    ]
    items = [
        {
            "id": bug["id"],
            "requirement_id": bug.get("requirement_id"),
            "severity": bug.get("severity"),
            "status": bug.get("status"),
            "title": bug.get("title") or bug["id"],
            "url": f"/delivery/bugs?bug_id={bug['id']}",
            "version_id": bug.get("version_id"),
        }
        for bug in _latest(high_severity_open or open_bugs)[:limit]
    ]
    return {
        "intent": "bugs",
        "items": items,
        "references": _references("bug", items),
        "summary": {
            "bugs_by_severity": _count_by(bugs, "severity"),
            "bugs_by_status": _count_by(bugs, "status"),
            "high_severity_open": len(high_severity_open),
            "open": len(open_bugs),
            "total": len(bugs),
        },
        "tool": "assistant.bugs",
    }


def _plugin_connection_diagnostic_tool(
    context: dict[str, Any],
    *,
    limit: int,
) -> dict[str, Any]:
    connections = list(context["plugin_connections"])
    failed_connections = [
        connection
        for connection in connections
        if _connection_last_test_summary(connection).get("status") == "failed"
    ]
    candidate_connections = failed_connections or [
        connection
        for connection in connections
        if _connection_last_test_summary(connection) or _connection_latest_test_history(connection)
    ]
    plugins_by_id = {
        str(plugin["id"]): plugin
        for plugin in context["integration_plugins"]
        if plugin.get("id") is not None
    }
    items = [
        _plugin_connection_diagnostic_item(
            connection,
            plugin=plugins_by_id.get(str(connection.get("plugin_id"))) or {},
        )
        for connection in _latest_connections_by_test(candidate_connections)[:limit]
    ]
    return {
        "intent": "plugin_connection_diagnostic",
        "items": items,
        "references": _references("plugin_connection", items),
        "summary": {
            "diagnosed_count": len(items),
            "failed_count": len(failed_connections),
            "source": "plugin_connection.last_test_summary",
        },
        "tool": "assistant.plugin_connection_diagnostic",
    }


def _plugin_connection_diagnostic_item(
    connection: dict[str, Any],
    *,
    plugin: dict[str, Any],
) -> dict[str, Any]:
    last_summary = _connection_last_test_summary(connection)
    latest_history = _connection_latest_test_history(connection)
    repair_suggestions = _connection_repair_suggestions(latest_history)
    status = str(last_summary.get("status") or connection.get("status") or "not_run")
    failed_step = last_summary.get("failed_step")
    error_message = last_summary.get("error_message")
    connection_name = str(connection.get("name") or connection.get("id") or "插件连接")
    stages = [
        {
            "stage": "connection_config",
            "status": "succeeded" if connection.get("status") == "active" else "warning",
            "summary": (
                f"连接状态 {connection.get('status') or '-'}，"
                f"环境 {connection.get('environment') or 'default'}，"
                f"插件 {plugin.get('name') or connection.get('plugin_id') or '-'}。"
            ),
        },
        {
            "stage": "latest_test",
            "status": status,
            "summary": _connection_test_summary_text(last_summary),
        },
        {
            "stage": "repair_suggestions",
            "status": "warning" if repair_suggestions else "succeeded",
            "summary": (
                f"已生成 {len(repair_suggestions)} 条修复建议。"
                if repair_suggestions
                else "最近测试未返回结构化修复建议。"
            ),
        },
    ]
    return {
        "checked_at": last_summary.get("checked_at"),
        "connection_status": connection.get("status"),
        "endpoint_url": connection.get("endpoint_url"),
        "environment": connection.get("environment"),
        "error_code": last_summary.get("error_code"),
        "error_message": error_message,
        "failed_step": failed_step,
        "id": connection.get("id"),
        "plugin_id": connection.get("plugin_id"),
        "plugin_name": plugin.get("name"),
        "repair_suggestions": repair_suggestions,
        "stages": stages,
        "status": status,
        "title": connection_name,
        "url": f"/tasks/plugins?connection_id={connection.get('id')}",
    }


def _connection_last_test_summary(connection: dict[str, Any]) -> dict[str, Any]:
    value = connection.get("last_test_summary")
    return value if isinstance(value, dict) else {}


def _connection_latest_test_history(connection: dict[str, Any]) -> dict[str, Any]:
    history = connection.get("test_history")
    if not isinstance(history, list):
        return {}
    latest = next((item for item in history if isinstance(item, dict)), None)
    return latest or {}


def _connection_repair_suggestions(history_entry: dict[str, Any]) -> list[dict[str, Any]]:
    suggestions = history_entry.get("repair_suggestions")
    if not isinstance(suggestions, list):
        return []
    return [
        {
            "code": suggestion.get("code"),
            "detail": suggestion.get("detail"),
            "title": suggestion.get("title"),
        }
        for suggestion in suggestions
        if isinstance(suggestion, dict)
    ]


def _connection_test_summary_text(last_summary: dict[str, Any]) -> str:
    if not last_summary:
        return "还没有最近连接测试记录。"
    failed_step = last_summary.get("failed_step")
    error_message = last_summary.get("error_message")
    status = last_summary.get("status") or "unknown"
    if failed_step or error_message:
        return (
            f"最近测试状态 {status}，失败步骤 {failed_step or '-'}，"
            f"错误：{error_message or '-'}。"
        )
    return f"最近测试状态 {status}。"


def _connection_test_time(connection: dict[str, Any]) -> str:
    last_summary = _connection_last_test_summary(connection)
    return str(
        last_summary.get("checked_at")
        or connection.get("updated_at")
        or connection.get("created_at")
        or connection.get("id")
        or ""
    )


def _latest_connections_by_test(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=_connection_test_time, reverse=True)


def _scheduled_job_diagnostic_tool(
    context: dict[str, Any],
    *,
    limit: int,
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    referenced_run_ids = [
        str(reference["id"])
        for reference in references
        if reference.get("type") == "scheduled_job_run" and reference.get("id")
    ]
    referenced_job_ids = {
        str(reference["id"])
        for reference in references
        if reference.get("type") == "scheduled_job" and reference.get("id")
    }
    runs = context["scheduled_job_runs"]
    if referenced_run_ids:
        run_id_set = set(referenced_run_ids)
        candidate_runs = [run for run in runs if str(run.get("id")) in run_id_set]
    elif referenced_job_ids:
        candidate_runs = [
            run
            for run in runs
            if run.get("status") == "failed"
            and str(run.get("scheduled_job_id")) in referenced_job_ids
        ]
    else:
        candidate_runs = [run for run in runs if run.get("status") == "failed"]
    jobs_by_id = {
        str(job["id"]): job
        for job in context["scheduled_jobs"]
        if job.get("id") is not None
    }
    plugin_logs_by_run_id = {
        str(log.get("scheduled_job_run_id")): log
        for log in context["plugin_invocation_logs"]
        if log.get("scheduled_job_run_id") is not None
    }
    model_logs_by_id = {
        str(log.get("id")): log
        for log in context["model_gateway_logs"]
        if log.get("id") is not None
    }
    result_write_records_by_run_id = {
        str(record.get("scheduled_job_run_id")): record
        for record in context["result_write_records"]
        if record.get("scheduled_job_run_id") is not None
    }
    items: list[dict[str, Any]] = []
    for run in _latest(candidate_runs)[:limit]:
        run_id = str(run["id"])
        job = jobs_by_id.get(str(run.get("scheduled_job_id"))) or {}
        stages = _scheduled_job_diagnostic_stages(
            run,
            model_logs_by_id=model_logs_by_id,
            plugin_log=plugin_logs_by_run_id.get(run_id),
            result_write_record=result_write_records_by_run_id.get(run_id),
        )
        title = (
            f"{job.get('name') or run.get('scheduled_job_id') or run_id} / "
            f"{run.get('status') or 'unknown'}"
        )
        items.append(
            {
                "completed_at": run.get("completed_at"),
                "duration_ms": run.get("duration_ms"),
                "error_message": run.get("error_message"),
                "id": run_id,
                "job_name": job.get("name"),
                "scheduled_job_id": run.get("scheduled_job_id"),
                "stages": stages,
                "started_at": run.get("started_at"),
                "status": run.get("status"),
                "title": title,
                "url": f"/tasks/scheduled-jobs?run_id={run_id}",
            }
        )
    return {
        "intent": "scheduled_job_diagnostic",
        "items": items,
        "references": _references("scheduled_job_run", items),
        "summary": {
            "failed_count": len([item for item in items if item.get("status") == "failed"]),
            "run_count": len(items),
        },
        "tool": "assistant.scheduled_job_diagnostic",
    }


def _scheduled_job_run_comparison_tool(
    context: dict[str, Any],
    *,
    limit: int,
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    runs = context["scheduled_job_runs"]
    candidate_runs = _scheduled_job_run_comparison_candidates(
        runs,
        limit=limit,
        references=references,
    )
    if not candidate_runs:
        return {
            "intent": "scheduled_job_run_comparison",
            "items": [],
            "references": [],
            "summary": {"baseline_found_count": 0, "comparison_count": 0},
            "tool": "assistant.scheduled_job_run_comparison",
        }
    jobs_by_id = {
        str(job["id"]): job
        for job in context["scheduled_jobs"]
        if job.get("id") is not None
    }
    plugin_logs_by_run_id = {
        str(log.get("scheduled_job_run_id")): log
        for log in context["plugin_invocation_logs"]
        if log.get("scheduled_job_run_id") is not None
    }
    model_logs_by_id = {
        str(log.get("id")): log
        for log in context["model_gateway_logs"]
        if log.get("id") is not None
    }
    result_write_records_by_run_id = {
        str(record.get("scheduled_job_run_id")): record
        for record in context["result_write_records"]
        if record.get("scheduled_job_run_id") is not None
    }
    items: list[dict[str, Any]] = []
    references_out: list[dict[str, Any]] = []
    for current_run in candidate_runs[:limit]:
        run_id = str(current_run.get("id") or "")
        if not run_id:
            continue
        baseline_run = _previous_successful_scheduled_job_run(runs, current_run)
        job = jobs_by_id.get(str(current_run.get("scheduled_job_id"))) or {}
        current_stages = _scheduled_job_diagnostic_stages(
            current_run,
            model_logs_by_id=model_logs_by_id,
            plugin_log=plugin_logs_by_run_id.get(run_id),
            result_write_record=result_write_records_by_run_id.get(run_id),
        )
        baseline_stages = (
            _scheduled_job_diagnostic_stages(
                baseline_run,
                model_logs_by_id=model_logs_by_id,
                plugin_log=plugin_logs_by_run_id.get(str(baseline_run.get("id"))),
                result_write_record=result_write_records_by_run_id.get(
                    str(baseline_run.get("id"))
                ),
            )
            if baseline_run is not None
            else []
        )
        current_summary = _scheduled_job_run_comparison_summary(current_run)
        baseline_summary = (
            _scheduled_job_run_comparison_summary(baseline_run)
            if baseline_run is not None
            else None
        )
        differences = _scheduled_job_run_differences(
            current_summary=current_summary,
            current_stages=current_stages,
            baseline_summary=baseline_summary,
            baseline_stages=baseline_stages,
        )
        item = {
            "baseline_run": baseline_summary,
            "current_run": current_summary,
            "differences": differences,
            "id": run_id,
            "scheduled_job_id": current_run.get("scheduled_job_id"),
            "title": _scheduled_job_run_title(job, current_run),
            "url": f"/tasks/scheduled-jobs?run_id={run_id}",
        }
        items.append(item)
        references_out.append(
            _scheduled_job_run_tool_reference(job=job, run=current_run)
        )
        if baseline_run is not None:
            baseline_job = jobs_by_id.get(str(baseline_run.get("scheduled_job_id"))) or job
            references_out.append(
                _scheduled_job_run_tool_reference(job=baseline_job, run=baseline_run)
            )
    return {
        "intent": "scheduled_job_run_comparison",
        "items": items,
        "references": normalize_assistant_references(references_out),
        "summary": {
            "baseline_found_count": len(
                [item for item in items if item.get("baseline_run") is not None]
            ),
            "comparison_count": len(items),
        },
        "tool": "assistant.scheduled_job_run_comparison",
    }


def _scheduled_job_run_repair_draft_tool(
    context: dict[str, Any],
    *,
    limit: int,
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_runs = _referenced_or_latest_failed_runs(
        context["scheduled_job_runs"],
        limit=limit,
        references=references,
    )
    jobs_by_id = {
        str(job["id"]): job
        for job in context["scheduled_jobs"]
        if job.get("id") is not None
    }
    plugin_actions_by_id = {
        str(action["id"]): action
        for action in context["plugin_actions"]
        if action.get("id") is not None
    }
    plugin_logs_by_run_id = {
        str(log.get("scheduled_job_run_id")): log
        for log in context["plugin_invocation_logs"]
        if log.get("scheduled_job_run_id") is not None
    }
    items: list[dict[str, Any]] = []
    references_out: list[dict[str, Any]] = []
    for run in candidate_runs[:limit]:
        if run.get("status") != "failed":
            continue
        run_id = str(run.get("id") or "")
        job = jobs_by_id.get(str(run.get("scheduled_job_id"))) or {}
        plugin_log = plugin_logs_by_run_id.get(run_id)
        source_action = _repair_source_plugin_action(
            job=job,
            plugin_actions_by_id=plugin_actions_by_id,
            plugin_log=plugin_log,
            run=run,
        )
        payload = _repair_plugin_action_payload(
            plugin_log=plugin_log,
            run=run,
            source_action=source_action,
        )
        if not payload.get("plugin_id") or not payload.get("connection_id"):
            continue
        run_reference = _scheduled_job_run_tool_reference(job=job, run=run)
        item = {
            "action": "create_plugin_action",
            "draft_id": f"assistant_draft_repair_{run_id}",
            "payload": payload,
            "references": [run_reference],
            "requires_confirmation": True,
            "risk_level": "medium",
            "title": payload["name"],
        }
        source_resource = _plugin_action_source_resource(source_action)
        if source_resource:
            item["source_resource"] = source_resource
        items.append(item)
        references_out.append(run_reference)
    return {
        "intent": "scheduled_job_run_repair_draft",
        "items": items,
        "references": normalize_assistant_references(references_out),
        "summary": {
            "draft_count": len(items),
            "requires_confirmation": bool(items),
            "source_run_id": str(candidate_runs[0].get("id")) if candidate_runs else None,
            "target": "plugin_action",
        },
        "tool": "assistant.action_draft",
    }


def _referenced_or_latest_failed_runs(
    runs: list[dict[str, Any]],
    *,
    limit: int,
    references: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    referenced_run_ids = [
        str(reference["id"])
        for reference in references
        if reference.get("type") == "scheduled_job_run" and reference.get("id")
    ]
    referenced_job_ids = {
        str(reference["id"])
        for reference in references
        if reference.get("type") == "scheduled_job" and reference.get("id")
    }
    if referenced_run_ids:
        run_by_id = {str(run["id"]): run for run in runs if run.get("id") is not None}
        return [run_by_id[run_id] for run_id in referenced_run_ids if run_id in run_by_id]
    if referenced_job_ids:
        return [
            run
            for run in _latest(runs)
            if run.get("status") == "failed"
            and str(run.get("scheduled_job_id")) in referenced_job_ids
        ][:limit]
    return [run for run in _latest(runs) if run.get("status") == "failed"][:limit]


def _scheduled_job_run_comparison_candidates(
    runs: list[dict[str, Any]],
    *,
    limit: int,
    references: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    referenced_run_ids = [
        str(reference["id"])
        for reference in references
        if reference.get("type") == "scheduled_job_run" and reference.get("id")
    ]
    if referenced_run_ids:
        run_by_id = {str(run["id"]): run for run in runs if run.get("id") is not None}
        return [run_by_id[run_id] for run_id in referenced_run_ids if run_id in run_by_id]

    referenced_job_ids = _unique(
        [
            str(reference["id"])
            for reference in references
            if reference.get("type") == "scheduled_job" and reference.get("id")
        ]
    )
    if not referenced_job_ids:
        return []

    latest_failed_by_job_id: dict[str, dict[str, Any]] = {}
    for run in _latest(runs):
        scheduled_job_id = str(run.get("scheduled_job_id") or "")
        if (
            run.get("status") == "failed"
            and scheduled_job_id in referenced_job_ids
            and scheduled_job_id not in latest_failed_by_job_id
        ):
            latest_failed_by_job_id[scheduled_job_id] = run
    return [
        latest_failed_by_job_id[job_id]
        for job_id in referenced_job_ids
        if job_id in latest_failed_by_job_id
    ][:limit]


def _repair_source_plugin_action(
    *,
    job: dict[str, Any],
    plugin_actions_by_id: dict[str, dict[str, Any]],
    plugin_log: dict[str, Any] | None,
    run: dict[str, Any],
) -> dict[str, Any]:
    result_action = _result_action_node(run)
    action_id = (
        result_action.get("plugin_action_id")
        or result_action.get("action_id")
        or (plugin_log or {}).get("action_id")
        or job.get("plugin_action_id")
    )
    if action_id and str(action_id) in plugin_actions_by_id:
        return plugin_actions_by_id[str(action_id)]
    return {}


def _plugin_action_source_resource(source_action: dict[str, Any]) -> dict[str, str] | None:
    action_id = str(source_action.get("id") or "").strip()
    if not action_id:
        return None
    title = str(source_action.get("name") or source_action.get("code") or action_id)
    return {
        "id": action_id,
        "title": title,
        "type": "plugin_action",
        "url": f"/tasks/plugins?action_id={action_id}",
    }


def _repair_plugin_action_payload(
    *,
    plugin_log: dict[str, Any] | None,
    run: dict[str, Any],
    source_action: dict[str, Any],
) -> dict[str, Any]:
    result_action = _result_action_node(run)
    request_config = _repair_request_config(source_action, plugin_log)
    result_mapping = _repair_result_mapping(source_action, result_action)
    source_name = str(
        source_action.get("name")
        or source_action.get("code")
        or (plugin_log or {}).get("action_id")
        or "结果动作"
    )
    source_code = str(
        source_action.get("code")
        or (plugin_log or {}).get("action_id")
        or "result_action"
    )
    return {
        "action_type": str(source_action.get("action_type") or "http_request"),
        "code": _repair_action_code(source_code),
        "connection_id": source_action.get("connection_id")
        or (plugin_log or {}).get("connection_id"),
        "description": (
            f"从失败运行 {run.get('id')} 生成，"
            "用于修复结果动作写入失败。"
        ),
        "name": f"{source_name}修复草案",
        "plugin_id": source_action.get("plugin_id") or (plugin_log or {}).get("plugin_id"),
        "request_config": request_config,
        "result_mapping": result_mapping,
        "status": "active",
    }


def _repair_request_config(
    source_action: dict[str, Any],
    plugin_log: dict[str, Any] | None,
) -> dict[str, Any]:
    request_config: dict[str, Any] = {}
    source_request_config = (
        source_action.get("request_config")
        if isinstance(source_action.get("request_config"), dict)
        else {}
    )
    request_summary = (
        plugin_log.get("request_summary")
        if isinstance(plugin_log, dict) and isinstance(plugin_log.get("request_summary"), dict)
        else {}
    )
    for field in ("method", "path"):
        value = source_request_config.get(field) or request_summary.get(field)
        if value:
            request_config[field] = value
    return request_config


def _repair_result_mapping(
    source_action: dict[str, Any],
    result_action: dict[str, Any],
) -> dict[str, Any]:
    result_mapping = (
        deepcopy(source_action.get("result_mapping"))
        if isinstance(source_action.get("result_mapping"), dict)
        else {}
    )
    if result_action.get("write_target") and not result_mapping.get("write_target"):
        result_mapping["write_target"] = result_action["write_target"]
    return result_mapping


def _repair_action_code(source_code: str) -> str:
    normalized = "_".join(str(source_code or "result_action").strip().split())
    if normalized.endswith("_repair"):
        return normalized
    return f"{normalized}_repair"


def _result_action_node(run: dict[str, Any]) -> dict[str, Any]:
    result_summary = (
        run.get("result_summary") if isinstance(run.get("result_summary"), dict) else {}
    )
    execution_nodes = (
        result_summary.get("execution_nodes")
        if isinstance(result_summary.get("execution_nodes"), dict)
        else {}
    )
    node = execution_nodes.get("result_action")
    return node if isinstance(node, dict) else {}


def _previous_successful_scheduled_job_run(
    runs: list[dict[str, Any]],
    current_run: dict[str, Any],
) -> dict[str, Any] | None:
    scheduled_job_id = str(current_run.get("scheduled_job_id") or "")
    current_id = str(current_run.get("id") or "")
    current_time = _run_time(current_run)
    candidates = [
        run
        for run in runs
        if str(run.get("scheduled_job_id") or "") == scheduled_job_id
        and str(run.get("id") or "") != current_id
        and run.get("status") == "succeeded"
    ]
    before_current = [
        run for run in candidates if not current_time or _run_time(run) <= current_time
    ]
    ordered = sorted(
        before_current or candidates,
        key=_run_time,
        reverse=True,
    )
    return ordered[0] if ordered else None


def _scheduled_job_run_comparison_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "completed_at": run.get("completed_at") or run.get("finished_at"),
        "duration_ms": run.get("duration_ms"),
        "error_message": run.get("error_message"),
        "id": run.get("id"),
        "records_imported": _run_records_imported(run),
        "started_at": run.get("started_at"),
        "status": run.get("status"),
        "trigger_type": run.get("trigger_type"),
    }


def _scheduled_job_run_differences(
    *,
    current_summary: dict[str, Any],
    current_stages: list[dict[str, Any]],
    baseline_summary: dict[str, Any] | None,
    baseline_stages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if baseline_summary is None:
        return [{"field": "baseline_run", "current": current_summary.get("id"), "baseline": None}]
    differences: list[dict[str, Any]] = []
    for field in ("status", "records_imported", "duration_ms", "error_message"):
        current_value = current_summary.get(field)
        baseline_value = baseline_summary.get(field)
        if current_value != baseline_value:
            differences.append(
                {"baseline": baseline_value, "current": current_value, "field": field}
            )
    baseline_stage_by_name = {
        str(stage.get("stage")): stage for stage in baseline_stages if stage.get("stage")
    }
    for current_stage in current_stages:
        stage_name = str(current_stage.get("stage") or "")
        baseline_stage = baseline_stage_by_name.get(stage_name, {})
        if not baseline_stage:
            differences.append(
                {
                    "baseline_status": None,
                    "current_status": current_stage.get("status"),
                    "field": f"stage.{stage_name}",
                    "stage": stage_name,
                }
            )
            continue
        stage_changed = any(
            current_stage.get(field) != baseline_stage.get(field)
            for field in (
                "status",
                "summary",
                "result_write_status",
                "result_write_target",
            )
        )
        if stage_changed:
            differences.append(
                {
                    "baseline_result_write_status": baseline_stage.get(
                        "result_write_status"
                    ),
                    "baseline_result_write_target": baseline_stage.get(
                        "result_write_target"
                    ),
                    "baseline_status": baseline_stage.get("status"),
                    "baseline_summary": baseline_stage.get("summary"),
                    "current_result_write_status": current_stage.get(
                        "result_write_status"
                    ),
                    "current_result_write_target": current_stage.get(
                        "result_write_target"
                    ),
                    "current_status": current_stage.get("status"),
                    "current_summary": current_stage.get("summary"),
                    "field": f"stage.{stage_name}",
                    "stage": stage_name,
                }
            )
    return differences


def _scheduled_job_diagnostic_stages(
    run: dict[str, Any],
    *,
    model_logs_by_id: dict[str, dict[str, Any]],
    plugin_log: dict[str, Any] | None,
    result_write_record: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    result_summary = (
        run.get("result_summary") if isinstance(run.get("result_summary"), dict) else {}
    )
    raw_nodes = (
        result_summary.get("execution_nodes")
        if isinstance(result_summary.get("execution_nodes"), dict)
        else {}
    )
    stage_specs = [
        ("data_connection", ("data_connection", "collector", "plugin_fetch")),
        ("ai_processing", ("ai_processing", "skill_processing", "model_gateway")),
        ("result_action", ("result_action", "writeback", "plugin_write")),
    ]
    stages: list[dict[str, Any]] = []
    for stage_name, aliases in stage_specs:
        node = next(
            (
                raw_nodes[alias]
                for alias in aliases
                if isinstance(raw_nodes.get(alias), dict)
            ),
            {},
        )
        log_id = _diagnostic_log_id(stage_name, node, plugin_log=plugin_log)
        if stage_name == "ai_processing" and log_id in model_logs_by_id:
            model_log = model_logs_by_id[log_id]
            node = {
                **node,
                "status": node.get("status") or model_log.get("status"),
                "summary": node.get("summary")
                or (
                    f"模型 {model_log.get('model') or 'unknown'} "
                    f"调用{model_log.get('status') or 'unknown'}"
                ),
            }
        stage = {
            "error_message": node.get("error_message"),
            "log_id": log_id,
            "stage": stage_name,
            "status": node.get("status") or _infer_stage_status(stage_name, run, plugin_log),
            "summary": node.get("summary") or _default_stage_summary(stage_name, run),
        }
        if node.get("error_code"):
            stage["error_code"] = node.get("error_code")
        if stage_name == "result_action":
            stage.update(_result_write_diagnostic_fields(node, result_write_record))
        stages.append(stage)
    return stages


def _result_write_diagnostic_fields(
    node: dict[str, Any],
    result_write_record: dict[str, Any] | None,
) -> dict[str, Any]:
    record = result_write_record if isinstance(result_write_record, dict) else {}
    fields: dict[str, Any] = {}
    if record.get("id"):
        fields["result_write_record_id"] = record["id"]
    if record.get("status"):
        fields["result_write_status"] = record["status"]
    write_target = record.get("write_target") or node.get("write_target")
    if write_target:
        fields["result_write_target"] = write_target
    write_target_label = record.get("write_target_label") or node.get("write_target_label")
    if write_target_label:
        fields["result_write_target_label"] = write_target_label
    return fields


def _diagnostic_log_id(
    stage_name: str,
    node: dict[str, Any],
    *,
    plugin_log: dict[str, Any] | None,
) -> str | None:
    if stage_name == "ai_processing":
        return node.get("model_gateway_log_id") or node.get("log_id")
    if stage_name == "data_connection":
        return node.get("plugin_invocation_log_id") or node.get("log_id")
    if stage_name == "result_action":
        return (
            node.get("plugin_invocation_log_id")
            or node.get("log_id")
            or (plugin_log or {}).get("id")
        )
    return node.get("log_id")


def _infer_stage_status(
    stage_name: str,
    run: dict[str, Any],
    plugin_log: dict[str, Any] | None,
) -> str:
    if stage_name == "result_action" and plugin_log:
        return str(plugin_log.get("status") or run.get("status") or "unknown")
    if stage_name == "result_action" and run.get("status") == "failed":
        return "failed"
    return "unknown"


def _default_stage_summary(stage_name: str, run: dict[str, Any]) -> str:
    if stage_name == "data_connection":
        return "未记录数据连接节点摘要。"
    if stage_name == "ai_processing":
        return "未记录 AI 处理节点摘要。"
    return str(run.get("error_message") or "未记录结果动作节点摘要。")


def _scheduled_job_run_title(job: dict[str, Any], run: dict[str, Any]) -> str:
    job_title = job.get("name") or run.get("scheduled_job_id") or run.get("id")
    return f"{job_title} / {run.get('status') or 'unknown'}"


def _scheduled_job_run_tool_reference(
    *,
    job: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, str | None]:
    run_id = str(run.get("id") or "")
    return {
        "id": run_id,
        "title": _scheduled_job_run_title(job, run),
        "type": "scheduled_job_run",
        "url": f"/tasks/scheduled-jobs?run_id={run_id}",
    }


def _run_records_imported(run: dict[str, Any]) -> int:
    result_summary = (
        run.get("result_summary") if isinstance(run.get("result_summary"), dict) else {}
    )
    value = run.get("records_imported", result_summary.get("records_imported", 0))
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _run_time(run: dict[str, Any]) -> str:
    return str(
        run.get("completed_at")
        or run.get("finished_at")
        or run.get("updated_at")
        or run.get("started_at")
        or run.get("created_at")
        or ""
    )


def _model_gateway_tool(current_store: Any) -> dict[str, Any]:
    default_gateway = next(
        (
            config
            for config in _read_memory_dict(current_store, "model_gateway_configs").values()
            if config.get("is_default") and config.get("status") == "active"
        ),
        None,
    )
    return {
        "intent": "model_gateway",
        "items": [],
        "references": [],
        "summary": {
            "api_key_configured": bool(default_gateway and default_gateway.get("api_key")),
            "chat_model": default_gateway.get("default_chat_model") if default_gateway else None,
            "embedding_model": (
                default_gateway.get("default_embedding_model") if default_gateway else None
            ),
            "is_configured": bool(default_gateway),
            "provider": default_gateway.get("provider") if default_gateway else None,
        },
        "tool": "assistant.model_gateway",
    }


def _latest(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: item.get("updated_at") or item.get("created_at") or item.get("id") or "",
        reverse=True,
    )


def _references(entity_type: str, items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return normalize_assistant_references(
        [
            {
                "id": item.get("id"),
                "title": item.get("title") or item.get("summary") or item.get("id"),
                "type": entity_type,
                "url": item.get("url"),
            }
            for item in items
        ]
    )


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
