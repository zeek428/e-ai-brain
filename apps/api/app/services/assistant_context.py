from __future__ import annotations

import json
from typing import Any

from app.services.assistant_references import (
    assistant_reference_candidates,
    normalize_assistant_references,
)

__all__ = [
    "assistant_chat_messages",
    "assistant_conversation_history_context",
    "assistant_conversation_messages",
    "assistant_conversation_title",
    "assistant_reference_candidates",
    "assistant_response_content",
    "build_assistant_system_context",
    "public_assistant_conversation",
    "public_assistant_message",
]

ASSISTANT_HISTORY_LIMIT = 10
ASSISTANT_HISTORY_CONTENT_LIMIT = 520
ASSISTANT_HISTORY_TOOL_RESULT_LIMIT = 4
ASSISTANT_HISTORY_TOOL_ITEM_LIMIT = 4


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def build_assistant_system_context(
    current_store: Any,
    *,
    default_gateway: dict[str, Any] | None,
    model_gateway_status: str,
    product_id: str | None,
) -> dict[str, Any]:
    products = list(_read_memory_dict(current_store, "products").values())
    if product_id:
        products = [product for product in products if product["id"] == product_id]
    product_ids = {product["id"] for product in products}
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
    task_by_id = {str(task["id"]): task for task in tasks}
    task_ids = set(task_by_id)
    versions = [
        version
        for version in _read_memory_dict(current_store, "product_versions").values()
        if not product_ids or version.get("product_id") in product_ids
    ]
    bugs = [
        bug
        for bug in _read_memory_dict(current_store, "bugs").values()
        if not product_ids or bug.get("product_id") in product_ids
    ]
    open_bugs = [bug for bug in bugs if bug.get("status") != "closed"]
    high_severity_bugs = [
        bug for bug in open_bugs if bug.get("severity") in {"blocker", "critical", "major"}
    ]
    pending_reviews = [
        review
        for review in _read_memory_dict(current_store, "human_reviews").values()
        if review.get("status") == "pending" and str(review.get("ai_task_id")) in task_ids
    ]
    code_review_reports = [
        report
        for report in _read_memory_dict(current_store, "code_review_reports").values()
        if str(report.get("task_id")) in task_ids
    ]
    knowledge_deposits = [
        deposit
        for deposit in _read_memory_dict(current_store, "knowledge_deposits").values()
        if str(deposit.get("ai_task_id")) in task_ids
    ]
    repositories = [
        repository
        for repository in _read_memory_dict(current_store, "product_git_repositories").values()
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
    conversation_history: list[dict[str, Any]] | None = None,
    context: dict[str, Any] | None,
    conversation_id: str | None,
    message: str,
    product_id: str | None,
    system_context: dict[str, Any],
) -> list[dict[str, str]]:
    user_payload = {
        "context": context,
        "conversation_id": conversation_id,
        "conversation_history": conversation_history or [],
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
                "Use conversation_history as bounded prior-turn context for follow-up "
                "phrases like 上一次, 刚才, 继续, this run, or previous draft. "
                "Prefer precise facts from system_context.tool_results; treat them as "
                "backend read-model tool outputs and cite their references. "
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


def assistant_conversation_history_context(
    current_store: Any,
    *,
    conversation_id: str | None,
    limit: int = ASSISTANT_HISTORY_LIMIT,
) -> list[dict[str, Any]]:
    if not conversation_id:
        return []
    messages = assistant_conversation_messages(
        current_store,
        conversation_id=conversation_id,
    )
    messages = [
        message
        for message in messages
        if (message.get("status") or "completed") != "pending"
    ]
    bounded_limit = max(1, min(limit, ASSISTANT_HISTORY_LIMIT))
    return [_assistant_history_message(message) for message in messages[-bounded_limit:]]


def _assistant_history_message(message: dict[str, Any]) -> dict[str, Any]:
    metadata = message.get("metadata_json") or {}
    history_message: dict[str, Any] = {
        "content": _history_text_excerpt(message.get("content")),
        "created_at": message.get("created_at"),
        "id": message.get("id"),
        "role": message.get("role"),
        "status": message.get("status") or "completed",
    }
    references = message.get("references") or metadata.get("references")
    normalized_references = normalize_assistant_references(references)
    if normalized_references:
        history_message["references"] = normalized_references[:ASSISTANT_HISTORY_TOOL_ITEM_LIMIT]
    intent = metadata.get("intent")
    if isinstance(intent, dict) and intent:
        history_message["intent"] = {
            key: intent.get(key)
            for key in ("intent_code", "summary", "confidence")
            if intent.get(key) is not None
        }
    tool_results = metadata.get("tool_results")
    if isinstance(tool_results, list) and tool_results:
        history_message["tool_results"] = [
            _assistant_history_tool_result(tool_result)
            for tool_result in tool_results[:ASSISTANT_HISTORY_TOOL_RESULT_LIMIT]
            if isinstance(tool_result, dict)
        ]
    return {key: value for key, value in history_message.items() if value not in (None, [], {})}


def _assistant_history_tool_result(tool_result: dict[str, Any]) -> dict[str, Any]:
    summary = tool_result.get("summary")
    items = tool_result.get("items")
    references = normalize_assistant_references(tool_result.get("references"))
    history_result: dict[str, Any] = {
        "intent": tool_result.get("intent"),
        "tool": tool_result.get("tool"),
    }
    if isinstance(summary, dict):
        history_result["summary"] = _safe_history_json(summary)
    elif summary is not None:
        history_result["summary"] = _history_text_excerpt(summary)
    if isinstance(items, list):
        history_items = [
            _assistant_history_tool_item(item)
            for item in items[:ASSISTANT_HISTORY_TOOL_ITEM_LIMIT]
            if isinstance(item, dict)
        ]
        if history_items:
            history_result["items"] = history_items
    if references:
        history_result["references"] = references[:ASSISTANT_HISTORY_TOOL_ITEM_LIMIT]
    return {key: value for key, value in history_result.items() if value not in (None, [], {})}


def _assistant_history_tool_item(item: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = (
        "id",
        "title",
        "type",
        "status",
        "action",
        "draft_id",
        "server_draft_id",
        "scheduled_job_id",
        "scheduled_job_run_id",
        "run_id",
        "url",
    )
    return {
        key: _history_text_excerpt(item.get(key), limit=180)
        for key in allowed_keys
        if item.get(key) is not None
    }


ASSISTANT_HISTORY_REDACTED_VALUE = "***"
ASSISTANT_HISTORY_SENSITIVE_EXACT_KEYS = {
    "api-key",
    "api_key",
    "apikey",
    "auth_config",
    "authorization",
    "cookie",
    "credentials",
    "password",
    "private_key",
    "secret",
    "set-cookie",
    "set_cookie",
}
ASSISTANT_HISTORY_SENSITIVE_KEY_PARTS = (
    "access_token",
    "api_key",
    "apikey",
    "bearer",
    "credential",
    "cookie",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
)
ASSISTANT_ACTION_DRAFT_PUBLIC_PAYLOAD_FIELDS = {
    "create_ai_agent": {
        "code",
        "default_skill_ids",
        "description",
        "model_gateway_config_id",
        "name",
        "status",
    },
    "create_ai_skill": {
        "code",
        "description",
        "input_schema",
        "name",
        "output_schema",
        "prompt_template",
        "status",
    },
    "create_analysis_draft": {
        "analysis_type",
        "findings",
        "source_reference_ids",
        "summary",
        "title",
    },
    "create_plugin_action": {
        "action_type",
        "assistant_prerequisite_draft_ids",
        "code",
        "connection_id",
        "description",
        "input_schema",
        "name",
        "output_schema",
        "plugin_id",
        "provider_candidates",
        "requires_human_review",
        "result_mapping",
        "status",
    },
    "create_plugin_connection": {
        "base_url",
        "code",
        "description",
        "endpoint_url",
        "environment",
        "max_retries",
        "name",
        "plugin_id",
        "provider_candidates",
        "status",
        "timeout_seconds",
    },
    "create_rd_task": {
        "input",
        "requirement_id",
        "task_type",
        "title",
    },
    "create_scheduled_job": {
        "agent_id",
        "assistant_prerequisite_draft_ids",
        "config_json",
        "cron_expression",
        "enabled",
        "execution_mode",
        "interval_seconds",
        "job_type",
        "knowledge_document_ids",
        "model_gateway_config_id",
        "name",
        "plugin_action_id",
        "plugin_action_ids",
        "plugin_connection_id",
        "plugin_connection_ids",
        "plugin_input_mapping",
        "product_id",
        "schedule_type",
        "skill_ids",
        "source_system",
    },
}


def _history_sensitive_key(key: Any) -> bool:
    normalized = str(key or "").strip().replace(".", "_").replace("-", "_").lower()
    if not normalized:
        return False
    if normalized in ASSISTANT_HISTORY_SENSITIVE_EXACT_KEYS:
        return True
    return any(part in normalized for part in ASSISTANT_HISTORY_SENSITIVE_KEY_PARTS)


def _history_sensitive_diff_item(value: dict[str, Any]) -> bool:
    for key in ("field", "key", "path", "name", "label"):
        if _history_sensitive_key(value.get(key)):
            return True
    return False


def _safe_history_json(value: Any, *, depth: int = 0) -> Any:
    if isinstance(value, int | float | bool) or value is None:
        return value
    if isinstance(value, str):
        return _history_text_excerpt(value)
    if depth >= 3:
        return _history_text_excerpt(value, limit=180)
    if isinstance(value, dict):
        sensitive_diff = _history_sensitive_diff_item(value)
        public_value: dict[str, Any] = {}
        for key, child in value.items():
            if _history_sensitive_key(key) or str(key).lower() in {
                "content",
                "text",
                "body",
                "chunk_text",
                "raw",
                "prompt",
                "markdown",
            }:
                continue
            if sensitive_diff and str(key).lower() in {"field", "key", "label", "name", "path"}:
                public_value[str(key)] = ASSISTANT_HISTORY_REDACTED_VALUE
                continue
            if sensitive_diff and str(key).lower() in {
                "current",
                "default",
                "previous",
                "proposed",
                "value",
            }:
                public_value[str(key)] = ASSISTANT_HISTORY_REDACTED_VALUE
                continue
            public_value[str(key)] = _safe_history_json(child, depth=depth + 1)
        return public_value
    if isinstance(value, list):
        return [_safe_history_json(item, depth=depth + 1) for item in value[:8]]
    return _history_text_excerpt(value)


def _public_action_draft_payload(item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload")
    if not isinstance(payload, dict):
        return {}
    action = str(item.get("action") or "").strip()
    allowed_fields = ASSISTANT_ACTION_DRAFT_PUBLIC_PAYLOAD_FIELDS.get(action)
    if not allowed_fields:
        allowed_fields = {
            key
            for key, value in payload.items()
            if not _history_sensitive_key(key)
            and isinstance(value, str | int | float | bool | list | dict)
        }
    public_payload: dict[str, Any] = {}
    for key in allowed_fields:
        if key not in payload or _history_sensitive_key(key):
            continue
        value = _safe_history_json(payload[key])
        if value not in ({}, []):
            public_payload[key] = value
        elif isinstance(payload[key], dict):
            public_payload[key] = {}
    return public_payload


def _history_text_excerpt(value: Any, *, limit: int = ASSISTANT_HISTORY_CONTENT_LIMIT) -> str:
    if isinstance(value, str):
        text = " ".join(value.strip().split())
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = str(value)
        text = " ".join(text.strip().split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


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
        for message in _read_memory_dict(current_store, "assistant_messages").values()
        if message.get("conversation_id") == conversation_id
    ]
    return sorted(messages, key=lambda item: item.get("created_at", ""))


def public_assistant_conversation(conversation: dict[str, Any]) -> dict[str, Any]:
    public_conversation = {
        "created_at": conversation["created_at"],
        "id": conversation["id"],
        "last_message_at": conversation.get("last_message_at") or conversation["updated_at"],
        "message_count": int(conversation.get("message_count") or 0),
        "product_id": conversation.get("product_id"),
        "title": conversation["title"],
        "updated_at": conversation["updated_at"],
    }
    if conversation.get("command_signature"):
        public_conversation["command_signature"] = conversation["command_signature"]
        if conversation.get("context_scope"):
            public_conversation["context_scope"] = conversation["context_scope"]
    return public_conversation


def public_assistant_message(
    message: dict[str, Any],
    *,
    include_tool_details: bool = True,
) -> dict[str, Any]:
    public_message = {
        "content": message["content"],
        "conversation_id": message["conversation_id"],
        "created_at": message["created_at"],
        "id": message["id"],
        "role": message["role"],
        "status": message.get("status") or "completed",
    }
    for key in (
        "cancelled_at",
        "client_request_id",
        "completed_at",
        "error_code",
        "failed_at",
        "run_id",
    ):
        if message.get(key):
            public_message[key] = message[key]
    if message.get("model"):
        public_message["model"] = message["model"]
    if message.get("suggestions"):
        public_message["suggestions"] = message["suggestions"]
    references = message.get("references") or (message.get("metadata_json") or {}).get("references")
    if references:
        public_message["references"] = normalize_assistant_references(references)
    intent = (message.get("metadata_json") or {}).get("intent")
    if isinstance(intent, dict) and intent:
        public_message["intent"] = intent
    tool_results = (message.get("metadata_json") or {}).get("tool_results")
    if isinstance(tool_results, list) and tool_results:
        public_message["tool_results"] = (
            tool_results if include_tool_details else _public_light_tool_results(tool_results)
        )
    return public_message


def _public_light_tool_results(tool_results: list[Any]) -> list[dict[str, Any]]:
    return [
        result
        for result in (
            _public_light_tool_result(tool_result)
            for tool_result in tool_results
            if isinstance(tool_result, dict)
        )
        if result
    ]


def _public_light_tool_result(tool_result: dict[str, Any]) -> dict[str, Any]:
    tool_name = str(tool_result.get("tool") or "")
    result: dict[str, Any] = {
        "intent": tool_result.get("intent"),
        "tool": tool_name,
    }
    summary = tool_result.get("summary")
    if isinstance(summary, dict):
        result["summary"] = _safe_history_json(summary)
    elif summary is not None:
        result["summary"] = _history_text_excerpt(summary)
    items = tool_result.get("items")
    if isinstance(items, list):
        light_items = [
            _public_light_tool_item(tool_name, item)
            for item in items[:ASSISTANT_HISTORY_TOOL_ITEM_LIMIT]
            if isinstance(item, dict)
        ]
        light_items = [item for item in light_items if item]
        if light_items:
            result["items"] = light_items
    references = normalize_assistant_references(tool_result.get("references"))
    if references:
        result["references"] = references[:ASSISTANT_HISTORY_TOOL_ITEM_LIMIT]
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def _public_light_tool_item(tool_name: str, item: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "assistant.action_draft":
        allowed_keys = (
            "action",
            "client_draft_id",
            "draft_id",
            "payload",
            "preview",
            "requires_confirmation",
            "risk_level",
            "run_once_requested",
            "server_draft_id",
            "status",
            "title",
            "url",
            "wizard_steps",
        )
    elif tool_name == "assistant.iteration":
        allowed_keys = (
            "blocker_count",
            "blockers_by_source",
            "code",
            "dashboard_url",
            "id",
            "next_actions",
            "requirement_count",
            "status",
            "status_impact",
            "task_count",
            "title",
            "url",
        )
    elif tool_name == "assistant.scheduled_job_run":
        allowed_keys = (
            "error_message",
            "id",
            "progress_text",
            "records_imported",
            "run_id",
            "scheduled_job_id",
            "status",
            "title",
            "trigger_type",
            "url",
        )
    else:
        allowed_keys = (
            "id",
            "title",
            "type",
            "status",
            "action",
            "url",
        )
    public_item: dict[str, Any] = {}
    for key in allowed_keys:
        value = item.get(key)
        if value is None:
            continue
        safe_value = _public_action_draft_payload(item) if (
            tool_name == "assistant.action_draft" and key == "payload"
        ) else _safe_history_json(value)
        if safe_value in ({}, []):
            continue
        public_item[key] = safe_value
    return public_item


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
