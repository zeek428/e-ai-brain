from __future__ import annotations

from typing import Any

from app.services.assistant_draft_builder import AssistantDraftBuilder
from app.services.assistant_references import normalize_assistant_references

__all__ = ["assistant_tool_results"]

def assistant_tool_results(
    current_store: Any,
    *,
    message: str,
    product_id: str | None,
    references: list[dict[str, Any]] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Deterministic read-model style tools used before asking the model."""

    context = _assistant_read_context(current_store, product_id=product_id)
    intents = _assistant_tool_intents(message)
    draft_builder = AssistantDraftBuilder(context)
    results: list[dict[str, Any]] = []
    for intent in intents:
        if intent == "plugin_connection_draft":
            results.append(draft_builder.plugin_connection_draft(message=message))
        elif intent == "plugin_action_draft":
            results.append(draft_builder.plugin_action_draft(message=message))
        elif intent == "code_inspection_job_draft":
            results.append(draft_builder.code_inspection_job_draft(message=message))
        elif intent == "scheduled_job_draft":
            results.append(draft_builder.scheduled_job_draft())
        elif intent == "scheduled_job_diagnostic":
            results.append(
                _scheduled_job_diagnostic_tool(
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
            results.append(_iteration_tool(context, limit=limit))
        elif intent == "bugs":
            results.append(_bugs_tool(context, limit=limit))
        elif intent == "model_gateway":
            results.append(_model_gateway_tool(current_store))
    return [result for result in results if result.get("items") or result.get("summary")]


def _assistant_read_context(current_store: Any, *, product_id: str | None) -> dict[str, Any]:
    products = list(current_store.products.values())
    if product_id:
        products = [product for product in products if product.get("id") == product_id]
    product_ids = {str(product["id"]) for product in products if product.get("id") is not None}
    requirements = [
        requirement
        for requirement in current_store.requirements.values()
        if not product_ids or requirement.get("product_id") in product_ids
    ]
    tasks = [
        task
        for task in current_store.ai_tasks.values()
        if not product_ids or task.get("product_id") in product_ids
    ]
    task_ids = {str(task["id"]) for task in tasks if task.get("id") is not None}
    return {
        "ai_agents": list(getattr(current_store, "ai_agents", {}).values()),
        "ai_skills": list(getattr(current_store, "ai_skills", {}).values()),
        "bugs": [
            bug
            for bug in current_store.bugs.values()
            if not product_ids or bug.get("product_id") in product_ids
        ],
        "code_review_reports": [
            report
            for report in current_store.code_review_reports.values()
            if str(report.get("task_id")) in task_ids
        ],
        "human_reviews": [
            review
            for review in current_store.human_reviews.values()
            if str(review.get("ai_task_id")) in task_ids
        ],
        "integration_plugins": list(getattr(current_store, "integration_plugins", {}).values()),
        "knowledge_documents": list(getattr(current_store, "knowledge_documents", {}).values()),
        "model_gateway_configs": list(getattr(current_store, "model_gateway_configs", {}).values()),
        "model_gateway_logs": list(getattr(current_store, "model_gateway_logs", [])),
        "plugin_actions": list(getattr(current_store, "plugin_actions", {}).values()),
        "plugin_connections": list(getattr(current_store, "plugin_connections", {}).values()),
        "plugin_invocation_logs": list(
            getattr(current_store, "plugin_invocation_logs", {}).values()
        ),
        "products": products,
        "requirements": requirements,
        "scheduled_jobs": [
            job
            for job in getattr(current_store, "scheduled_jobs", {}).values()
            if not product_ids or job.get("product_id") in product_ids
        ],
        "scheduled_job_runs": [
            run
            for run in getattr(current_store, "scheduled_job_runs", {}).values()
            if not product_ids
            or str(run.get("scheduled_job_id"))
            in {
                str(job["id"])
                for job in getattr(current_store, "scheduled_jobs", {}).values()
                if job.get("id") is not None
                and (not product_ids or job.get("product_id") in product_ids)
            }
        ],
        "tasks": tasks,
        "task_by_id": {str(task["id"]): task for task in tasks if task.get("id") is not None},
        "versions": [
            version
            for version in current_store.product_versions.values()
            if not product_ids or version.get("product_id") in product_ids
        ],
    }


def _assistant_tool_intents(message: str) -> list[str]:
    normalized = message.lower()
    intents: list[str] = []
    if _plugin_connection_draft_requested(normalized):
        intents.append("plugin_connection_draft")
    if _plugin_action_draft_requested(normalized):
        intents.append("plugin_action_draft")
    if _scheduled_job_draft_requested(normalized):
        intents.append(
            "code_inspection_job_draft"
            if _code_inspection_draft_requested(normalized)
            else "scheduled_job_draft",
        )
    if _scheduled_job_diagnostic_requested(normalized):
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


def _scheduled_job_diagnostic_requested(normalized_message: str) -> bool:
    has_diagnostic_intent = any(
        keyword in normalized_message
        for keyword in ("为什么", "原因", "失败", "诊断", "排查", "failed", "failure", "diagnose")
    )
    has_scheduled_job_context = any(
        keyword in normalized_message
        for keyword in ("定时任务", "定时作业", "作业", "任务", "scheduled job", "run")
    )
    return has_diagnostic_intent and has_scheduled_job_context


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
    if has_create_intent and has_scheduled_job and _code_inspection_draft_requested(
        normalized_message,
    ):
        return True
    return has_create_intent and has_scheduled_job and has_weekly_feedback


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
        for keyword in ("github", "gitlab", "邮箱", "邮件", "email")
    )
    return (
        has_create_intent
        and has_connection
        and has_supported_plugin
        and not _scheduled_job_draft_requested(normalized_message)
        and not _plugin_action_draft_requested(normalized_message)
    )


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


def _iteration_tool(context: dict[str, Any], *, limit: int) -> dict[str, Any]:
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
        items.append(
            {
                "bug_count": len(version_bugs),
                "code": version.get("code"),
                "id": version["id"],
                "requirement_count": len(version_requirements),
                "requirements_by_status": _count_by(version_requirements, "status"),
                "status": version.get("status"),
                "task_count": len(version_tasks),
                "title": version.get("name") or version.get("code") or version["id"],
                "url": f"/delivery/versions?version_id={version['id']}",
            }
        )
    return {
        "intent": "iteration",
        "items": items,
        "references": _references("iteration_version", items),
        "summary": {"version_count": len(context["versions"])},
        "tool": "assistant.iteration",
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
    runs = context["scheduled_job_runs"]
    if referenced_run_ids:
        run_id_set = set(referenced_run_ids)
        candidate_runs = [run for run in runs if str(run.get("id")) in run_id_set]
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
    items: list[dict[str, Any]] = []
    for run in _latest(candidate_runs)[:limit]:
        run_id = str(run["id"])
        job = jobs_by_id.get(str(run.get("scheduled_job_id"))) or {}
        stages = _scheduled_job_diagnostic_stages(
            run,
            model_logs_by_id=model_logs_by_id,
            plugin_log=plugin_logs_by_run_id.get(run_id),
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


def _scheduled_job_diagnostic_stages(
    run: dict[str, Any],
    *,
    model_logs_by_id: dict[str, dict[str, Any]],
    plugin_log: dict[str, Any] | None,
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
        stages.append(
            {
                "error_message": node.get("error_message"),
                "log_id": log_id,
                "stage": stage_name,
                "status": node.get("status") or _infer_stage_status(stage_name, run, plugin_log),
                "summary": node.get("summary") or _default_stage_summary(stage_name, run),
            }
        )
    return stages


def _diagnostic_log_id(
    stage_name: str,
    node: dict[str, Any],
    *,
    plugin_log: dict[str, Any] | None,
) -> str | None:
    if stage_name == "ai_processing":
        return node.get("model_gateway_log_id") or node.get("log_id")
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


def _model_gateway_tool(current_store: Any) -> dict[str, Any]:
    default_gateway = next(
        (
            config
            for config in current_store.model_gateway_configs.values()
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
