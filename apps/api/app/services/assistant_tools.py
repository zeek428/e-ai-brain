from __future__ import annotations

from typing import Any

from app.services.assistant_references import normalize_assistant_references

__all__ = ["assistant_tool_results"]


def assistant_tool_results(
    current_store: Any,
    *,
    message: str,
    product_id: str | None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Deterministic read-model style tools used before asking the model."""

    context = _assistant_read_context(current_store, product_id=product_id)
    intents = _assistant_tool_intents(message)
    results: list[dict[str, Any]] = []
    for intent in intents:
        if intent == "delivery_progress":
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
        "products": products,
        "requirements": requirements,
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
            "url": f"/tasks/management?review_id={review['id']}",
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
            "url": f"/tasks/management?code_review_report_id={report['id']}",
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
