from __future__ import annotations

from typing import Any

from app.services.knowledge_documents import (
    knowledge_document_chunks,
    knowledge_query_repository,
    knowledge_repository_access_args,
    user_can_read_roles,
)
from app.services.knowledge_search import KNOWLEDGE_SEARCHABLE_STATUSES

OPERATIONAL_REFERENCE_TYPES = {
    "ai_agent",
    "ai_skill",
    "plugin_action",
    "scheduled_job",
    "scheduled_job_run",
}
REFERENCE_SOURCE_MODULES = {
    "ai_agent": "AI能力配置",
    "ai_skill": "AI能力配置",
    "ai_task": "需求交付",
    "bug": "需求交付",
    "code_review_report": "需求交付",
    "human_review": "需求交付",
    "iteration_version": "需求交付",
    "knowledge_deposit": "知识库",
    "knowledge_document": "知识库",
    "plugin_action": "插件管理",
    "product": "产品资产",
    "requirement": "需求交付",
    "scheduled_job": "任务中心",
    "scheduled_job_run": "任务中心",
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


class AssistantReferenceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def assistant_reference_candidates(
    current_store: Any,
    *,
    message: str,
    product_id: str | None,
    filter_by_query: bool = False,
    limit: int = 6,
    user: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
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
    versions = [
        version
        for version in current_store.product_versions.values()
        if not product_ids or version.get("product_id") in product_ids
    ]
    reviews = [
        review
        for review in current_store.human_reviews.values()
        if str(review.get("ai_task_id")) in task_ids
    ]
    bugs = [
        bug
        for bug in current_store.bugs.values()
        if not product_ids or bug.get("product_id") in product_ids
    ]
    code_reviews = [
        report
        for report in current_store.code_review_reports.values()
        if str(report.get("task_id")) in task_ids
    ]
    deposits = [
        deposit
        for deposit in current_store.knowledge_deposits.values()
        if str(deposit.get("ai_task_id")) in task_ids
    ]
    scheduled_jobs = [
        job
        for job in getattr(current_store, "scheduled_jobs", {}).values()
        if not product_ids or job.get("product_id") in product_ids
    ]
    scheduled_job_ids = {str(job["id"]) for job in scheduled_jobs if job.get("id") is not None}
    scheduled_job_runs = [
        run
        for run in getattr(current_store, "scheduled_job_runs", {}).values()
        if not scheduled_job_ids or str(run.get("scheduled_job_id")) in scheduled_job_ids
    ]
    pools: list[tuple[str, list[dict[str, Any]]]] = [
        ("product", products),
        ("iteration_version", versions),
        ("requirement", requirements),
        ("ai_task", tasks),
        ("human_review", reviews),
        ("bug", bugs),
        ("code_review_report", code_reviews),
        ("knowledge_deposit", deposits),
    ]
    if _user_can_reference_operational(user):
        pools.extend(
            [
                ("scheduled_job", scheduled_jobs),
                ("scheduled_job_run", scheduled_job_runs),
                ("plugin_action", list(getattr(current_store, "plugin_actions", {}).values())),
                ("ai_agent", list(getattr(current_store, "ai_agents", {}).values())),
                ("ai_skill", list(getattr(current_store, "ai_skills", {}).values())),
            ]
        )
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    preferred_types = _assistant_reference_type_preferences(message)
    ordered_pools = sorted(
        pools,
        key=lambda item: preferred_types.get(item[0], len(preferred_types) + 10),
    )
    for entity_type, items in ordered_pools:
        pool_items = sorted(items, key=_assistant_reference_sort_key, reverse=True)
        if filter_by_query:
            pool_items = [
                item
                for item in pool_items
                if _assistant_reference_matches_query(
                    entity_type,
                    item,
                    message,
                    current_store=current_store,
                )
            ]
        for item in pool_items[:3]:
            reference = _assistant_reference_for_entity(
                entity_type,
                item,
                current_store=current_store,
            )
            if reference is None:
                continue
            key = (reference["type"], reference["id"])
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
            if len(references) >= limit:
                return references
    return references


def assistant_reference_candidates_response(
    current_store: Any,
    *,
    limit: int,
    message: str,
    product_id: str | None,
    reference_type: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    normalized_type = (reference_type or "").strip() or None
    normalized_limit = min(max(limit, 1), 20)
    if normalized_type in OPERATIONAL_REFERENCE_TYPES and not _user_can_reference_operational(
        user,
    ):
        return {"items": [], "total": 0}
    if normalized_type == "knowledge_document":
        items = _knowledge_document_reference_candidates(
            current_store,
            limit=normalized_limit,
            query=message,
            user=user,
        )
        enriched_items = _reference_candidates_with_metadata(current_store, items)
        return {"items": enriched_items, "total": len(enriched_items)}
    if normalized_type:
        items = [
            reference
            for reference in assistant_reference_candidates(
                current_store,
                filter_by_query=True,
                limit=normalized_limit,
                message=message,
                product_id=product_id,
                user=user,
            )
            if reference["type"] == normalized_type
        ]
        enriched_items = _reference_candidates_with_metadata(
            current_store,
            items[:normalized_limit],
        )
        return {"items": enriched_items, "total": len(enriched_items)}
    items = _merge_reference_lists(
        _knowledge_document_reference_candidates(
            current_store,
            limit=normalized_limit,
            query=message,
            user=user,
        ),
        assistant_reference_candidates(
            current_store,
            filter_by_query=True,
            limit=normalized_limit,
            message=message,
            product_id=product_id,
            user=user,
        ),
        limit=normalized_limit,
    )
    enriched_items = _reference_candidates_with_metadata(current_store, items)
    return {"items": enriched_items, "total": len(enriched_items)}


def resolve_assistant_references(
    current_store: Any,
    *,
    references: list[dict[str, Any]],
    user: dict[str, Any],
    max_chunks: int = 8,
    max_references: int = 6,
) -> dict[str, Any]:
    normalized_requests = normalize_assistant_reference_requests(references)[:max_references]
    resolved: list[dict[str, str]] = []
    knowledge_context: list[dict[str, Any]] = []
    for reference in normalized_requests:
        reference_type = reference["type"]
        reference_id = reference["id"]
        if reference_type == "knowledge_document":
            document = _readable_knowledge_document(
                current_store,
                document_id=reference_id,
                user=user,
            )
            if document is None:
                raise AssistantReferenceError(
                    404,
                    "REFERENCE_NOT_FOUND",
                    "Assistant reference not found",
                )
            resolved.append(_knowledge_document_reference(document))
            knowledge_context.extend(
                _knowledge_context_for_document(
                    current_store,
                    document=document,
                    max_chunks=max_chunks - len(knowledge_context),
                    user=user,
                )
            )
            continue
        entity_reference = _entity_reference_for_id(current_store, reference_type, reference_id)
        if reference_type in OPERATIONAL_REFERENCE_TYPES and not _user_can_reference_operational(
            user,
        ):
            entity_reference = None
        if entity_reference is None:
            raise AssistantReferenceError(
                404,
                "REFERENCE_NOT_FOUND",
                "Assistant reference not found",
            )
        resolved.append(entity_reference)
    return {
        "items": _merge_reference_lists(resolved, limit=max_references),
        "knowledge_context": knowledge_context[:max_chunks],
        "total": len(resolved),
    }


def normalize_assistant_reference_requests(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        item_type = str(item.get("type") or "").strip()
        if not item_id or not item_type:
            continue
        key = (item_type, item_id)
        if key in seen:
            continue
        seen.add(key)
        references.append({"id": item_id, "type": item_type})
        if len(references) >= 6:
            break
    return references


def normalize_assistant_references(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        item_type = str(item.get("type") or "").strip()
        title = str(item.get("title") or item_id).strip()
        url = str(item.get("url") or "").strip()
        if not item_id or not item_type or not title or not url:
            continue
        key = (item_type, item_id)
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "id": item_id,
                "title": title,
                "type": item_type,
                "url": url,
            }
        )
        if len(references) >= 6:
            break
    return references


def _reference_candidates_with_metadata(
    current_store: Any,
    references: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for reference in references:
        reference_type = str(reference.get("type") or "")
        reference_id = str(reference.get("id") or "")
        item = _entity_for_reference(current_store, reference_type, reference_id)
        updated_at = (
            item.get("updated_at")
            or item.get("created_at")
            or item.get("last_message_at")
            if item
            else None
        )
        enriched_item = {
            **reference,
            "permission_label": "管理员可引用"
            if reference_type in OPERATIONAL_REFERENCE_TYPES
            else "可引用",
            "source_module": REFERENCE_SOURCE_MODULES.get(reference_type, "AI Brain"),
        }
        if updated_at:
            enriched_item["updated_at"] = str(updated_at)
        enriched.append(enriched_item)
    return enriched


def _entity_for_reference(
    current_store: Any,
    entity_type: str,
    item_id: str,
) -> dict[str, Any] | None:
    collection_map = {
        "ai_agent": "ai_agents",
        "ai_skill": "ai_skills",
        "ai_task": "ai_tasks",
        "bug": "bugs",
        "code_review_report": "code_review_reports",
        "human_review": "human_reviews",
        "iteration_version": "product_versions",
        "knowledge_deposit": "knowledge_deposits",
        "knowledge_document": "knowledge_documents",
        "plugin_action": "plugin_actions",
        "product": "products",
        "requirement": "requirements",
        "scheduled_job": "scheduled_jobs",
        "scheduled_job_run": "scheduled_job_runs",
    }
    collection_name = collection_map.get(entity_type)
    if collection_name is None:
        return None
    item = getattr(current_store, collection_name, {}).get(item_id)
    return item if isinstance(item, dict) else None


def _knowledge_document_reference_candidates(
    current_store: Any,
    *,
    limit: int,
    query: str,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    normalized_query = query.strip()
    documents = _readable_knowledge_documents(
        current_store,
        query=normalized_query or None,
        user=user,
    )
    references = [
        {
            **_knowledge_document_reference(document),
            "chunk_count": int(
                document.get("chunk_count")
                or _knowledge_chunk_count(current_store, document)
            ),
            "index_status": str(document.get("index_status") or ""),
            **_knowledge_document_reference_summary(document),
        }
        for document in documents
        if document.get("index_status") in KNOWLEDGE_SEARCHABLE_STATUSES
    ]
    references.sort(
        key=lambda item: (
            item.get("title", ""),
            item.get("id", ""),
        )
    )
    return references[:limit]


def _readable_knowledge_documents(
    current_store: Any,
    *,
    query: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    repository = knowledge_query_repository(current_store)
    if repository is not None:
        try:
            return repository.list_knowledge_documents(
                **knowledge_repository_access_args(user),
                keyword=query,
            )
        except TypeError:
            return repository.list_knowledge_documents(
                user_roles=list(user.get("roles") or []),
                keyword=query,
            )
    from app.services.knowledge_management import document_is_readable

    documents = [
        document
        for document in getattr(current_store, "knowledge_documents", {}).values()
        if document_is_readable(current_store, user, document)
    ]
    if query:
        normalized_query = query.lower()
        documents = [
            document
            for document in documents
            if normalized_query
            in f"{document.get('title', '')} {document.get('content', '')}".lower()
        ]
    return documents


def _readable_knowledge_document(
    current_store: Any,
    *,
    document_id: str,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    for document in _readable_knowledge_documents(
        current_store,
        query=None,
        user=user,
    ):
        if str(document.get("id")) == document_id:
            return document
    return None


def _knowledge_context_for_document(
    current_store: Any,
    *,
    document: dict[str, Any],
    max_chunks: int,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    if max_chunks <= 0:
        return []
    candidates = _readable_knowledge_chunks(
        current_store,
        document=document,
        user=user,
    )
    context_items = []
    for chunk in candidates[:max_chunks]:
        context_items.append(
            {
                "chunk_id": str(chunk["id"]),
                "chunk_index": int(chunk.get("chunk_index") or 0),
                "content": str(chunk.get("content") or ""),
                "document_id": str(document["id"]),
                "document_title": str(document.get("title") or document["id"]),
                "source": {
                    "doc_type": document.get("doc_type"),
                    "knowledge_space_id": document.get("knowledge_space_id"),
                },
            }
        )
    if context_items:
        return context_items
    content = str(document.get("content") or "").strip()
    if not content:
        return []
    return [
        {
            "chunk_id": None,
            "chunk_index": 0,
            "content": content[:1200],
            "document_id": str(document["id"]),
            "document_title": str(document.get("title") or document["id"]),
            "source": {
                "doc_type": document.get("doc_type"),
                "knowledge_space_id": document.get("knowledge_space_id"),
            },
        }
    ]


def _readable_knowledge_chunks(
    current_store: Any,
    *,
    document: dict[str, Any],
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    repository = knowledge_query_repository(current_store)
    search_chunks = getattr(repository, "search_knowledge_chunks", None)
    if callable(search_chunks):
        access_args = knowledge_repository_access_args(user)
        try:
            candidates = search_chunks(
                **access_args,
                knowledge_space_id=document.get("knowledge_space_id"),
                query=None,
            )
        except TypeError:
            candidates = search_chunks(
                user_roles=access_args["user_roles"],
                query=None,
            )
        chunks = [
            candidate["chunk"]
            for candidate in candidates
            if str(candidate.get("document", {}).get("id")) == str(document["id"])
        ]
        return sorted(chunks, key=lambda chunk: (chunk.get("chunk_index", 0), chunk.get("id", "")))
    chunks = []
    for chunk in knowledge_document_chunks(current_store, str(document["id"])):
        if chunk.get("metadata", {}).get("chunk_role") == "parent":
            continue
        if document.get("knowledge_space_id"):
            chunk_readable = True
        else:
            chunk_roles = chunk.get("permission_roles", document.get("permission_roles") or [])
            chunk_readable = user_can_read_roles(user, chunk_roles)
        if not chunk_readable:
            continue
        if document.get("active_chunk_set_id") and chunk.get("chunk_set_id"):
            if chunk["chunk_set_id"] != document["active_chunk_set_id"]:
                continue
        elif document.get("active_chunk_set_id"):
            continue
        chunks.append(chunk)
    return sorted(chunks, key=lambda chunk: (chunk.get("chunk_index", 0), chunk.get("id", "")))


def _knowledge_chunk_count(current_store: Any, document: dict[str, Any]) -> int:
    return len(
        [
            chunk
            for chunk in getattr(current_store, "knowledge_chunks", {}).values()
            if chunk.get("document_id") == document.get("id")
        ]
    )


def _knowledge_document_reference_summary(document: dict[str, Any]) -> dict[str, str]:
    summary = str(
        document.get("summary")
        or document.get("abstract")
        or document.get("description")
        or document.get("content")
        or ""
    ).strip()
    if not summary:
        return {}
    normalized = " ".join(summary.split())
    if len(normalized) > 120:
        normalized = f"{normalized[:117]}..."
    return {"summary": normalized}


def _knowledge_document_reference(document: dict[str, Any]) -> dict[str, str]:
    document_id = str(document["id"])
    return {
        "id": document_id,
        "title": str(document.get("title") or document_id),
        "type": "knowledge_document",
        "url": f"/knowledge/documents?document_id={document_id}",
    }


def _entity_reference_for_id(
    current_store: Any,
    entity_type: str,
    item_id: str,
) -> dict[str, str] | None:
    collection_map = {
        "ai_task": "ai_tasks",
        "bug": "bugs",
        "code_review_report": "code_review_reports",
        "human_review": "human_reviews",
        "iteration_version": "product_versions",
        "knowledge_deposit": "knowledge_deposits",
        "plugin_action": "plugin_actions",
        "product": "products",
        "requirement": "requirements",
        "scheduled_job": "scheduled_jobs",
        "scheduled_job_run": "scheduled_job_runs",
        "ai_agent": "ai_agents",
        "ai_skill": "ai_skills",
    }
    collection_name = collection_map.get(entity_type)
    if collection_name is None:
        return None
    item = getattr(current_store, collection_name, {}).get(item_id)
    if item is None:
        return None
    return _assistant_reference_for_entity(entity_type, item, current_store=current_store)


def _merge_reference_lists(
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


def _assistant_reference_type_preferences(message: str) -> dict[str, int]:
    normalized = message.lower()
    ordered: list[str] = []
    keyword_map = [
        (("需求", "requirement"), ["requirement"]),
        (("bug", "缺陷", "阻塞"), ["bug", "requirement"]),
        (("任务", "task"), ["ai_task", "human_review"]),
        (
            ("定时", "作业", "scheduled", "schedule"),
            ["scheduled_job_run", "scheduled_job"],
        ),
        (("插件动作", "动作", "plugin action"), ["plugin_action"]),
        (("ai角色", "agent", "角色"), ["ai_agent"]),
        (("skill", "能力"), ["ai_skill"]),
        (("review", "确认", "评审"), ["human_review", "code_review_report", "ai_task"]),
        (("迭代", "版本", "version"), ["iteration_version", "requirement"]),
        (("产品", "product"), ["product"]),
        (("代码", "pr", "github"), ["code_review_report", "ai_task"]),
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
            "code_review_report",
            "knowledge_deposit",
            "product",
            "scheduled_job_run",
            "scheduled_job",
            "plugin_action",
            "ai_agent",
            "ai_skill",
        ]
    )
    preferences: dict[str, int] = {}
    for entity_type in ordered:
        preferences.setdefault(entity_type, len(preferences))
    return preferences


def _assistant_reference_sort_key(item: dict[str, Any]) -> str:
    return str(
        item.get("updated_at")
        or item.get("created_at")
        or item.get("last_message_at")
        or item.get("id")
        or ""
    )


def _assistant_reference_for_entity(
    entity_type: str,
    item: dict[str, Any],
    *,
    current_store: Any | None = None,
) -> dict[str, str] | None:
    item_id = item.get("id")
    if item_id is None:
        return None
    title = _assistant_reference_title(entity_type, item, current_store=current_store)
    route_map = {
        "ai_task": f"/delivery/rd-tasks?task_id={item_id}",
        "ai_agent": f"/tasks/ai-capabilities?agent_id={item_id}",
        "ai_skill": f"/tasks/ai-capabilities?skill_id={item_id}",
        "bug": f"/delivery/bugs?bug_id={item_id}",
        "code_review_report": f"/delivery/rd-tasks?code_review_report_id={item_id}",
        "human_review": f"/delivery/rd-tasks?review_id={item_id}",
        "iteration_version": f"/delivery/versions?version_id={item_id}",
        "knowledge_deposit": f"/knowledge/documents?deposit_id={item_id}",
        "plugin_action": f"/tasks/plugins?action_id={item_id}",
        "product": f"/assets/products?product_id={item_id}",
        "requirement": f"/delivery/requirements?requirement_id={item_id}",
        "scheduled_job": f"/tasks/scheduled-jobs?job_id={item_id}",
        "scheduled_job_run": f"/tasks/scheduled-jobs?run_id={item_id}",
    }
    return {
        "id": str(item_id),
        "title": str(title),
        "type": entity_type,
        "url": route_map[entity_type],
    }


def _assistant_reference_title(
    entity_type: str,
    item: dict[str, Any],
    *,
    current_store: Any | None,
) -> str:
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


def _assistant_reference_matches_query(
    entity_type: str,
    item: dict[str, Any],
    query: str,
    *,
    current_store: Any | None,
) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True
    title = _assistant_reference_title(entity_type, item, current_store=current_store)
    haystack = " ".join(
        str(value or "")
        for value in (
            item.get("id"),
            item.get("code"),
            item.get("name"),
            item.get("status"),
            item.get("summary"),
            item.get("title"),
            title,
        )
    ).lower()
    if normalized_query in haystack:
        return True
    return _scheduled_job_reference_matches_semantic_query(
        entity_type,
        normalized_query,
        haystack,
    )


def assistant_reference_matches_query(
    entity_type: str,
    item: dict[str, Any],
    query: str,
    *,
    current_store: Any | None = None,
) -> bool:
    return _assistant_reference_matches_query(
        entity_type,
        item,
        query,
        current_store=current_store,
    )


def _scheduled_job_reference_matches_semantic_query(
    entity_type: str,
    normalized_query: str,
    haystack: str,
) -> bool:
    if entity_type not in {"scheduled_job", "scheduled_job_run"}:
        return False
    query_groups = _scheduled_job_keyword_group_indexes(normalized_query)
    if len(query_groups) < 2:
        return False
    haystack_groups = _scheduled_job_keyword_group_indexes(haystack)
    overlap = query_groups & haystack_groups
    if len(overlap) < 2:
        return False
    return bool(overlap & SCHEDULED_JOB_DOMAIN_GROUP_INDEXES)


def _scheduled_job_keyword_group_indexes(value: str) -> set[int]:
    return {
        index
        for index, keywords in enumerate(SCHEDULED_JOB_QUERY_KEYWORD_GROUPS)
        if any(keyword in value for keyword in keywords)
    }


def _user_can_reference_operational(user: dict[str, Any] | None) -> bool:
    roles = set(user.get("roles") or []) if isinstance(user, dict) else set()
    return "admin" in roles
