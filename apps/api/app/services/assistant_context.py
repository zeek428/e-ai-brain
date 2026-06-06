from __future__ import annotations

import json
from typing import Any

from app.services.assistant_references import (
    assistant_reference_candidates,
    normalize_assistant_references,
)

__all__ = [
    "assistant_chat_messages",
    "assistant_conversation_messages",
    "assistant_conversation_title",
    "assistant_reference_candidates",
    "assistant_response_content",
    "build_assistant_system_context",
    "public_assistant_conversation",
    "public_assistant_message",
]


def build_assistant_system_context(
    current_store: Any,
    *,
    default_gateway: dict[str, Any] | None,
    model_gateway_status: str,
    product_id: str | None,
) -> dict[str, Any]:
    products = list(current_store.products.values())
    if product_id:
        products = [product for product in products if product["id"] == product_id]
    product_ids = {product["id"] for product in products}
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
    task_by_id = {str(task["id"]): task for task in tasks}
    task_ids = set(task_by_id)
    versions = [
        version
        for version in current_store.product_versions.values()
        if not product_ids or version.get("product_id") in product_ids
    ]
    bugs = [
        bug
        for bug in current_store.bugs.values()
        if not product_ids or bug.get("product_id") in product_ids
    ]
    open_bugs = [bug for bug in bugs if bug.get("status") != "closed"]
    high_severity_bugs = [
        bug for bug in open_bugs if bug.get("severity") in {"blocker", "critical", "major"}
    ]
    pending_reviews = [
        review
        for review in current_store.human_reviews.values()
        if review.get("status") == "pending" and str(review.get("ai_task_id")) in task_ids
    ]
    code_review_reports = [
        report
        for report in current_store.code_review_reports.values()
        if str(report.get("task_id")) in task_ids
    ]
    knowledge_deposits = [
        deposit
        for deposit in current_store.knowledge_deposits.values()
        if str(deposit.get("ai_task_id")) in task_ids
    ]
    repositories = [
        repository
        for repository in current_store.product_git_repositories.values()
        if not product_ids or repository.get("product_id") in product_ids
    ]
    return {
        "ai_tasks_by_status": _count_by(tasks, "status"),
        "ai_tasks_by_type": _count_by(tasks, "task_type"),
        "ai_tasks_total": len(tasks),
        "blocked_requirements": _blocked_requirements(
            requirements,
            high_severity_bugs,
        ),
        "bug_distribution": {
            "by_severity": _count_by(bugs, "severity"),
            "by_status": _count_by(bugs, "status"),
            "high_severity_open": len(high_severity_bugs),
            "open": len(open_bugs),
            "total": len(bugs),
        },
        "git_repositories": [
            {
                "default_branch": repository.get("default_branch"),
                "id": repository["id"],
                "name": repository["name"],
                "provider": repository.get("git_provider", "gitlab"),
                "status": repository.get("status"),
            }
            for repository in repositories[:8]
        ],
        "iteration_progress": _iteration_progress(
            versions=versions,
            requirements=requirements,
            tasks=tasks,
            bugs=bugs,
            pending_reviews=pending_reviews,
        ),
        "knowledge_deposits_total": len(knowledge_deposits),
        "latest_requirements": [
            {
                "id": requirement["id"],
                "priority": requirement.get("priority"),
                "status": requirement["status"],
                "title": requirement["title"],
            }
            for requirement in sorted(
                requirements,
                key=lambda item: item.get("created_at", ""),
                reverse=True,
            )[:6]
        ],
        "latest_tasks": [
            {
                "id": task["id"],
                "status": task["status"],
                "title": task["title"],
                "type": task["task_type"],
            }
            for task in sorted(tasks, key=lambda item: item.get("created_at", ""), reverse=True)[:8]
        ],
        "model_gateway": {
            "api_key_configured": bool(default_gateway and default_gateway.get("api_key")),
            "chat_model": default_gateway.get("default_chat_model") if default_gateway else None,
            "is_configured": bool(default_gateway) or model_gateway_status == "configured",
            "provider": default_gateway.get("provider") if default_gateway else "openai_compatible",
        },
        "open_high_severity_bugs": [
            {
                "id": bug["id"],
                "requirement_id": bug.get("requirement_id"),
                "severity": bug.get("severity"),
                "status": bug.get("status"),
                "title": bug.get("title"),
                "version_id": bug.get("version_id"),
            }
            for bug in sorted(
                high_severity_bugs,
                key=lambda item: item.get("updated_at") or item.get("created_at") or "",
                reverse=True,
            )[:6]
        ],
        "pending_reviews": [
            {
                "ai_task_id": review.get("ai_task_id"),
                "id": review.get("id"),
                "review_type": review.get("review_type"),
                "task_title": task_by_id.get(str(review.get("ai_task_id")), {}).get("title"),
            }
            for review in sorted(
                pending_reviews,
                key=lambda item: item.get("created_at") or item.get("updated_at") or "",
                reverse=True,
            )[:8]
        ],
        "products": [
            {
                "code": product.get("code"),
                "id": product["id"],
                "name": product["name"],
                "status": product.get("status"),
            }
            for product in products[:8]
        ],
        "recent_code_review_reports": [
            {
                "finding_count": len(report.get("findings") or []),
                "id": report.get("id"),
                "risk_level": report.get("risk_level"),
                "status": report.get("status"),
                "summary": report.get("summary"),
                "task_id": report.get("task_id"),
                "task_title": task_by_id.get(str(report.get("task_id")), {}).get("title"),
            }
            for report in sorted(
                code_review_reports,
                key=lambda item: _first_value(
                    item,
                    ("archived_at", "updated_at", "created_at", "id"),
                )
                or "",
                reverse=True,
            )[:6]
        ],
        "recent_knowledge_deposits": [
            {
                "ai_task_id": deposit.get("ai_task_id"),
                "id": deposit.get("id"),
                "status": deposit.get("status"),
                "task_title": task_by_id.get(str(deposit.get("ai_task_id")), {}).get("title"),
                "title": deposit.get("title"),
            }
            for deposit in sorted(
                knowledge_deposits,
                key=lambda item: item.get("updated_at") or item.get("created_at") or "",
                reverse=True,
            )[:6]
        ],
        "requirements_by_status": _count_by(requirements, "status"),
        "requirements_by_version": _count_by(requirements, "version_id"),
        "requirements_total": len(requirements),
    }


def assistant_chat_messages(
    *,
    context: dict[str, Any] | None,
    conversation_id: str | None,
    message: str,
    product_id: str | None,
    system_context: dict[str, Any],
) -> list[dict[str, str]]:
    user_payload = {
        "context": context,
        "conversation_id": conversation_id,
        "message": message,
        "product_id": product_id,
        "system_context": system_context,
    }
    return [
        {
            "role": "system",
            "content": (
                "You are AI Brain's assistant for R&D delivery work. Answer in Chinese. "
                "Use system_context to answer questions about AI Brain configuration, "
                "development progress, requirements, tasks, repositories, "
                "iteration progress, pending reviews, code review conclusions, "
                "bug distribution, knowledge deposits, and model gateway status. "
                "Return one compact JSON object with string field answer and optional "
                "array fields suggestions and references. References must use items "
                "from system_context.reference_candidates when useful. "
                "Do not include markdown fences."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def assistant_response_content(content: Any) -> dict[str, Any]:
    parsed: Any = content
    if isinstance(content, str):
        stripped = content.strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {"answer": stripped, "references": [], "suggestions": []}
    if not isinstance(parsed, dict):
        return {"answer": str(parsed), "references": [], "suggestions": []}
    answer = parsed.get("answer") or parsed.get("content") or parsed.get("message") or ""
    suggestions = parsed.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = []
    references = normalize_assistant_references(parsed.get("references"))
    return {
        "answer": str(answer).strip(),
        "references": references,
        "suggestions": [str(item).strip() for item in suggestions if str(item).strip()][:4],
    }


def assistant_conversation_title(message: str) -> str:
    normalized = " ".join(message.strip().split())
    if len(normalized) <= 60:
        return normalized
    return f"{normalized[:57]}..."


def assistant_conversation_messages(
    current_store: Any,
    *,
    conversation_id: str,
) -> list[dict[str, Any]]:
    messages = [
        message
        for message in current_store.assistant_messages.values()
        if message.get("conversation_id") == conversation_id
    ]
    return sorted(messages, key=lambda item: item.get("created_at", ""))


def public_assistant_conversation(conversation: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": conversation["created_at"],
        "id": conversation["id"],
        "last_message_at": conversation.get("last_message_at") or conversation["updated_at"],
        "message_count": int(conversation.get("message_count") or 0),
        "product_id": conversation.get("product_id"),
        "title": conversation["title"],
        "updated_at": conversation["updated_at"],
    }


def public_assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    public_message = {
        "content": message["content"],
        "conversation_id": message["conversation_id"],
        "created_at": message["created_at"],
        "id": message["id"],
        "role": message["role"],
    }
    if message.get("model"):
        public_message["model"] = message["model"]
    if message.get("suggestions"):
        public_message["suggestions"] = message["suggestions"]
    references = message.get("references") or (message.get("metadata_json") or {}).get("references")
    if references:
        public_message["references"] = normalize_assistant_references(references)
    return public_message


def _iteration_progress(
    *,
    versions: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    bugs: list[dict[str, Any]],
    pending_reviews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    version_progress = []
    for version in sorted(
        versions,
        key=lambda item: item.get("updated_at") or item.get("created_at") or item.get("code") or "",
        reverse=True,
    )[:8]:
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
        version_task_ids = {task["id"] for task in version_tasks}
        version_bugs = [bug for bug in bugs if bug.get("version_id") == version["id"]]
        version_progress.append(
            {
                "ai_task_count": len(version_tasks),
                "ai_tasks_by_status": _count_by(version_tasks, "status"),
                "code": version.get("code"),
                "id": version["id"],
                "name": version.get("name"),
                "open_bug_count": len(
                    [bug for bug in version_bugs if bug.get("status") != "closed"]
                ),
                "pending_review_count": len(
                    [
                        review
                        for review in pending_reviews
                        if review.get("ai_task_id") in version_task_ids
                    ]
                ),
                "requirement_count": len(version_requirements),
                "requirements_by_status": _count_by(version_requirements, "status"),
                "status": version.get("status"),
            }
        )
    return version_progress


def _blocked_requirements(
    requirements: list[dict[str, Any]],
    high_severity_bugs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blocked_requirement_ids = {
        str(bug.get("requirement_id"))
        for bug in high_severity_bugs
        if bug.get("requirement_id")
    }
    return [
        {
            "id": requirement["id"],
            "priority": requirement.get("priority"),
            "reason": (
                "high_severity_open_bug"
                if requirement["id"] in blocked_requirement_ids
                else f"status:{requirement.get('status')}"
            ),
            "status": requirement.get("status"),
            "title": requirement.get("title"),
            "version_id": requirement.get("version_id"),
        }
        for requirement in requirements
        if requirement["id"] in blocked_requirement_ids
        or requirement.get("status") in {"rejected", "deferred", "cancelled"}
    ][:8]


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _first_value(item: dict[str, Any], fields: tuple[str, ...]) -> Any | None:
    for field in fields:
        value = item.get(field)
        if value not in (None, ""):
            return value
    return None
