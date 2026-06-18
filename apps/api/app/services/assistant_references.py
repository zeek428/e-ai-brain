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
    "plugin_connection",
    "scheduled_job",
    "scheduled_job_run",
}
OPERATIONAL_REFERENCE_PERMISSION_BY_TYPE = {
    "ai_agent": "system.ai_capabilities.manage",
    "ai_skill": "system.ai_capabilities.manage",
    "plugin_action": "system.plugins.manage",
    "plugin_connection": "system.plugins.manage",
    "scheduled_job": "system.scheduled_jobs.manage",
    "scheduled_job_run": "system.scheduled_jobs.manage",
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
    "knowledge_chunk": "知识库",
    "knowledge_document": "知识库",
    "knowledge_folder": "知识库",
    "knowledge_space": "知识库",
    "plugin_action": "插件管理",
    "plugin_connection": "插件管理",
    "product": "产品资产",
    "requirement": "需求交付",
    "scheduled_job": "任务中心",
    "scheduled_job_run": "任务中心",
}
DEFAULT_REFERENCE_TYPE_ORDER = (
    "knowledge_space",
    "knowledge_folder",
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
    "human_review",
    "bug",
    "iteration_version",
    "code_review_report",
    "knowledge_deposit",
    "product",
)
REFERENCE_TYPE_QUERY_ALIASES = {
    "ai_agent": ("ai角色", "ai 角色", "智能体", "agent", "角色"),
    "ai_skill": ("skill", "能力", "ai能力", "ai 能力"),
    "ai_task": ("研发任务", "ai任务", "任务", "task"),
    "bug": ("bug", "缺陷", "阻塞"),
    "code_review_report": ("代码评审", "代码巡检", "code review", "pr"),
    "human_review": ("确认", "待确认", "评审", "review"),
    "iteration_version": ("迭代", "版本", "version"),
    "knowledge_chunk": ("知识片段", "chunk", "片段"),
    "knowledge_deposit": ("知识沉淀", "沉淀"),
    "knowledge_document": ("知识文档", "知识库", "文档"),
    "knowledge_folder": ("知识目录", "目录", "folder"),
    "knowledge_space": ("知识空间", "空间", "knowledge space"),
    "plugin_action": ("插件动作", "动作", "plugin action"),
    "plugin_connection": ("插件连接", "连接", "connection"),
    "product": ("产品", "product"),
    "requirement": ("需求", "requirement"),
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
    per_type_limit: int = 3,
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
    knowledge_spaces = _readable_knowledge_spaces(
        current_store,
        query=None,
        user=user or {},
    )
    knowledge_folders = _readable_knowledge_folders(
        current_store,
        query=None,
        user=user or {},
    )
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
        ("knowledge_space", knowledge_spaces),
        ("knowledge_folder", knowledge_folders),
        ("product", products),
        ("iteration_version", versions),
        ("requirement", requirements),
        ("ai_task", tasks),
        ("human_review", reviews),
        ("bug", bugs),
        ("code_review_report", code_reviews),
        ("knowledge_deposit", deposits),
    ]
    operational_pools = [
        ("scheduled_job", scheduled_jobs),
        ("scheduled_job_run", scheduled_job_runs),
        ("plugin_action", list(getattr(current_store, "plugin_actions", {}).values())),
        (
            "plugin_connection",
            list(getattr(current_store, "plugin_connections", {}).values()),
        ),
        ("ai_agent", list(getattr(current_store, "ai_agents", {}).values())),
        ("ai_skill", list(getattr(current_store, "ai_skills", {}).values())),
    ]
    pools.extend(
        (entity_type, items)
        for entity_type, items in operational_pools
        if _user_can_reference_operational_type(user, entity_type)
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
        for item in pool_items[:per_type_limit]:
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
    if normalized_type in OPERATIONAL_REFERENCE_TYPES and not _user_can_reference_operational_type(
        user,
        normalized_type,
    ):
        return {"items": [], "total": 0}
    if normalized_type == "knowledge_document":
        items = _knowledge_document_reference_candidates(
            current_store,
            limit=normalized_limit,
            query=message,
            user=user,
        )
        enriched_items = _reference_candidates_with_metadata(current_store, items, user=user)
        return {"items": enriched_items, "total": len(enriched_items)}
    if normalized_type == "knowledge_chunk":
        items = _knowledge_chunk_reference_candidates(
            current_store,
            limit=normalized_limit,
            query=message,
            user=user,
        )
        enriched_items = _reference_candidates_with_metadata(current_store, items, user=user)
        return {"items": enriched_items, "total": len(enriched_items)}
    if normalized_type:
        candidate_limit = max(
            normalized_limit * len(DEFAULT_REFERENCE_TYPE_ORDER),
            len(DEFAULT_REFERENCE_TYPE_ORDER) * 3,
        )
        items = [
            reference
            for reference in assistant_reference_candidates(
                current_store,
                filter_by_query=True,
                limit=candidate_limit,
                message=message,
                per_type_limit=normalized_limit,
                product_id=product_id,
                user=user,
            )
            if reference["type"] == normalized_type
        ]
        enriched_items = _reference_candidates_with_metadata(
            current_store,
            items[:normalized_limit],
            user=user,
        )
        return {"items": enriched_items, "total": len(enriched_items)}
    knowledge_references = _knowledge_document_reference_candidates(
        current_store,
        limit=normalized_limit,
        query=message,
        user=user,
    )
    if message.strip():
        knowledge_references = _merge_reference_lists(
            _knowledge_chunk_reference_candidates(
                current_store,
                limit=normalized_limit,
                query=message,
                user=user,
            ),
            knowledge_references,
            limit=normalized_limit,
        )
    candidate_limit = max(normalized_limit * 4, len(DEFAULT_REFERENCE_TYPE_ORDER) * 3)
    items = _merge_reference_lists_by_type(
        knowledge_references,
        assistant_reference_candidates(
            current_store,
            filter_by_query=True,
            limit=candidate_limit,
            message=message,
            product_id=product_id,
            user=user,
        ),
        limit=normalized_limit,
    )
    enriched_items = _reference_candidates_with_metadata(current_store, items, user=user)
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
        if reference_type == "knowledge_chunk":
            chunk_record = _readable_knowledge_chunk(
                current_store,
                chunk_id=reference_id,
                user=user,
            )
            if chunk_record is None:
                raise AssistantReferenceError(
                    404,
                    "REFERENCE_NOT_FOUND",
                    "Assistant reference not found",
                )
            chunk, document = chunk_record
            resolved.append(_knowledge_chunk_reference(document, chunk))
            if len(knowledge_context) < max_chunks:
                knowledge_context.append(_knowledge_context_for_chunk(document, chunk))
            continue
        if reference_type == "knowledge_space":
            space = _readable_knowledge_space(
                current_store,
                space_id=reference_id,
                user=user,
            )
            if space is None:
                raise AssistantReferenceError(
                    404,
                    "REFERENCE_NOT_FOUND",
                    "Assistant reference not found",
                )
            resolved.append(
                _knowledge_space_reference_with_metadata(current_store, space, user=user)
            )
            knowledge_context.extend(
                _knowledge_context_for_space(
                    current_store,
                    max_chunks=max_chunks - len(knowledge_context),
                    space=space,
                    user=user,
                )
            )
            continue
        if reference_type == "knowledge_folder":
            folder = _readable_knowledge_folder(
                current_store,
                folder_id=reference_id,
                user=user,
            )
            if folder is None:
                raise AssistantReferenceError(
                    404,
                    "REFERENCE_NOT_FOUND",
                    "Assistant reference not found",
                )
            resolved.append(
                _knowledge_folder_reference_with_metadata(current_store, folder, user=user)
            )
            knowledge_context.extend(
                _knowledge_context_for_folder(
                    current_store,
                    folder=folder,
                    max_chunks=max_chunks - len(knowledge_context),
                    user=user,
                )
            )
            continue
        entity_reference = _entity_reference_for_id(current_store, reference_type, reference_id)
        if (
            reference_type in OPERATIONAL_REFERENCE_TYPES
            and not _user_can_reference_operational_type(
                user,
                reference_type,
            )
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
    *,
    user: dict[str, Any] | None,
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
        if reference_type == "knowledge_space" and item is not None:
            enriched_item.update(
                _knowledge_scope_reference_metadata(
                    current_store,
                    folder=None,
                    space=item,
                    user=user,
                )
            )
        if reference_type == "knowledge_folder" and item is not None:
            enriched_item.update(
                _knowledge_scope_reference_metadata(
                    current_store,
                    folder=item,
                    space=None,
                    user=user,
                )
            )
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
        "knowledge_folder": "knowledge_folders",
        "knowledge_space": "knowledge_spaces",
        "plugin_action": "plugin_actions",
        "plugin_connection": "plugin_connections",
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


def _refresh_knowledge_scope_collections_from_repository(current_store: Any) -> None:
    repository = getattr(current_store, "repository", None)
    load_knowledge = getattr(repository, "load_knowledge", None)
    if not callable(load_knowledge):
        return
    payload = load_knowledge() or {}
    for collection_name in (
        "knowledge_folders",
        "knowledge_space_members",
        "knowledge_spaces",
    ):
        collection = payload.get(collection_name)
        if isinstance(collection, dict):
            setattr(current_store, collection_name, collection)


def _readable_knowledge_spaces(
    current_store: Any,
    *,
    query: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    from app.services.knowledge_management import user_can_access_space

    _refresh_knowledge_scope_collections_from_repository(current_store)
    normalized_query = (query or "").strip().lower()
    spaces = []
    for space in getattr(current_store, "knowledge_spaces", {}).values():
        if not isinstance(space, dict):
            continue
        space_id = str(space.get("id") or "")
        if not space_id:
            continue
        if not user_can_access_space(current_store, user, space_id=space_id, required="read"):
            continue
        if normalized_query:
            haystack = " ".join(
                str(value or "")
                for value in (
                    space.get("id"),
                    space.get("code"),
                    space.get("name"),
                    space.get("description"),
                )
            ).lower()
            if normalized_query not in haystack:
                continue
        spaces.append(dict(space))
    spaces.sort(key=lambda item: (item.get("code") or item.get("name") or "", item.get("id") or ""))
    return spaces


def _readable_knowledge_space(
    current_store: Any,
    *,
    space_id: str,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    for space in _readable_knowledge_spaces(current_store, query=None, user=user):
        if str(space.get("id")) == space_id:
            return space
    return None


def _readable_knowledge_folders(
    current_store: Any,
    *,
    query: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    from app.services.knowledge_management import (
        folder_is_effectively_active,
        folder_path,
        user_can_access_space,
    )

    _refresh_knowledge_scope_collections_from_repository(current_store)
    normalized_query = (query or "").strip().lower()
    folders = []
    for folder in getattr(current_store, "knowledge_folders", {}).values():
        if not isinstance(folder, dict):
            continue
        folder_id = str(folder.get("id") or "")
        space_id = str(folder.get("knowledge_space_id") or "")
        if not folder_id or not space_id:
            continue
        if not user_can_access_space(current_store, user, space_id=space_id, required="read"):
            continue
        if not folder_is_effectively_active(current_store, folder_id):
            continue
        folder_item = {**folder, "path": folder.get("path") or folder_path(current_store, folder)}
        if normalized_query:
            haystack = " ".join(
                str(value or "")
                for value in (
                    folder_item.get("id"),
                    folder_item.get("name"),
                    folder_item.get("path"),
                )
            ).lower()
            if normalized_query not in haystack:
                continue
        folders.append(folder_item)
    folders.sort(
        key=lambda item: (
            item.get("knowledge_space_id") or "",
            item.get("sort_order") or 0,
            item.get("path") or item.get("name") or "",
            item.get("id") or "",
        )
    )
    return folders


def _readable_knowledge_folder(
    current_store: Any,
    *,
    folder_id: str,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    for folder in _readable_knowledge_folders(current_store, query=None, user=user):
        if str(folder.get("id")) == folder_id:
            return folder
    return None


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


def _knowledge_chunk_reference_candidates(
    current_store: Any,
    *,
    limit: int,
    query: str,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    normalized_query = query.strip().lower()
    candidates = _readable_knowledge_chunk_candidates(
        current_store,
        query=normalized_query or None,
        user=user,
    )
    references = []
    for candidate in candidates:
        document = candidate["document"]
        chunk = candidate["chunk"]
        if chunk.get("metadata", {}).get("chunk_role") == "parent":
            continue
        references.append(
            {
                **_knowledge_chunk_reference(document, chunk),
                "chunk_count": 1,
                "chunk_index": int(chunk.get("chunk_index") or 0),
                "document_id": str(document["id"]),
                "summary": _summary_excerpt(str(chunk.get("content") or "")),
                "updated_at": str(document.get("updated_at") or document.get("created_at") or ""),
            }
        )
    references.sort(
        key=lambda item: (
            item.get("title", ""),
            item.get("id", ""),
        )
    )
    return references[:limit]


def _knowledge_scope_documents(
    current_store: Any,
    *,
    folder_id: str | None,
    searchable_only: bool = True,
    space_id: str,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    folder_ids: set[str] | None = None
    if folder_id is not None:
        from app.services.knowledge_management import folder_descendant_ids

        folder_ids = {folder_id, *folder_descendant_ids(current_store, folder_id)}
    documents = [
        document
        for document in _readable_knowledge_documents(
            current_store,
            query=None,
            user=user,
        )
        if document.get("knowledge_space_id") == space_id
        and (folder_ids is None or document.get("folder_id") in folder_ids)
        and (
            not searchable_only
            or document.get("index_status") in KNOWLEDGE_SEARCHABLE_STATUSES
        )
    ]
    documents.sort(
        key=lambda item: (
            item.get("updated_at") or item.get("created_at") or "",
            item.get("title") or "",
            item.get("id") or "",
        ),
        reverse=True,
    )
    return documents


def _knowledge_scope_chunk_count(
    current_store: Any,
    *,
    documents: list[dict[str, Any]],
    user: dict[str, Any],
) -> int:
    return sum(
        len(_readable_knowledge_chunks(current_store, document=document, user=user))
        for document in documents
    )


def _knowledge_scope_reference_metadata(
    current_store: Any,
    *,
    folder: dict[str, Any] | None,
    space: dict[str, Any] | None,
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    if user is None:
        return {}
    if folder is not None:
        space_id = str(folder.get("knowledge_space_id") or "")
        folder_id = str(folder.get("id") or "")
    elif space is not None:
        space_id = str(space.get("id") or "")
        folder_id = None
    else:
        return {}
    if not space_id:
        return {}
    documents = _knowledge_scope_documents(
        current_store,
        folder_id=folder_id,
        space_id=space_id,
        user=user,
    )
    chunk_count = _knowledge_scope_chunk_count(
        current_store,
        documents=documents,
        user=user,
    )
    if folder is not None:
        folder_title = str(folder.get("path") or folder.get("name") or folder.get("id") or "")
        summary = (
            f"{folder_title} 下 {len(documents)} 篇可检索知识文档，"
            f"{chunk_count} 个知识 chunk 可按权限注入。"
        )
        return {
            "chunk_count": chunk_count,
            "document_count": len(documents),
            "folder_path": folder.get("path") or folder.get("name"),
            "knowledge_space_id": space_id,
            "summary": summary,
        }
    space_title = str(space.get("name") or space.get("code") or space_id)
    description = str(space.get("description") or "").strip()
    summary = (
        f"{space_title} 下 {len(documents)} 篇可检索知识文档，"
        f"{chunk_count} 个知识 chunk 可按权限注入。"
    )
    if description:
        summary = f"{description} {summary}"
    return {
        "chunk_count": chunk_count,
        "document_count": len(documents),
        "summary": _summary_excerpt(summary),
    }


def _knowledge_context_for_space(
    current_store: Any,
    *,
    max_chunks: int,
    space: dict[str, Any],
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    return _knowledge_context_for_scope(
        current_store,
        folder_id=None,
        max_chunks=max_chunks,
        space_id=str(space["id"]),
        user=user,
    )


def _knowledge_context_for_folder(
    current_store: Any,
    *,
    folder: dict[str, Any],
    max_chunks: int,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    return _knowledge_context_for_scope(
        current_store,
        folder_id=str(folder["id"]),
        max_chunks=max_chunks,
        space_id=str(folder["knowledge_space_id"]),
        user=user,
    )


def _knowledge_context_for_scope(
    current_store: Any,
    *,
    folder_id: str | None,
    max_chunks: int,
    space_id: str,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    if max_chunks <= 0:
        return []
    context_items: list[dict[str, Any]] = []
    for document in _knowledge_scope_documents(
        current_store,
        folder_id=folder_id,
        space_id=space_id,
        user=user,
    ):
        remaining = max_chunks - len(context_items)
        if remaining <= 0:
            break
        context_items.extend(
            _knowledge_context_for_document(
                current_store,
                document=document,
                max_chunks=remaining,
                user=user,
            )
        )
    return context_items[:max_chunks]


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
        if (
            str(document.get("id")) == document_id
            and document.get("index_status") in KNOWLEDGE_SEARCHABLE_STATUSES
        ):
            return document
    return None


def _readable_knowledge_chunk(
    current_store: Any,
    *,
    chunk_id: str,
    user: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for candidate in _readable_knowledge_chunk_candidates(
        current_store,
        query=None,
        user=user,
    ):
        chunk = candidate["chunk"]
        if chunk.get("metadata", {}).get("chunk_role") == "parent":
            continue
        if str(chunk.get("id")) == chunk_id:
            return chunk, candidate["document"]
    return None


def _readable_knowledge_chunk_candidates(
    current_store: Any,
    *,
    query: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    repository = knowledge_query_repository(current_store)
    search_chunks = getattr(repository, "search_knowledge_chunks", None)
    if callable(search_chunks):
        access_args = knowledge_repository_access_args(user)
        try:
            return search_chunks(
                **access_args,
                query=query,
            )
        except TypeError:
            return search_chunks(
                user_roles=access_args["user_roles"],
                query=query,
            )

    candidates: list[dict[str, Any]] = []
    for document in _readable_knowledge_documents(
        current_store,
        query=None,
        user=user,
    ):
        if document.get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES:
            continue
        for chunk in _readable_knowledge_chunks(
            current_store,
            document=document,
            user=user,
        ):
            if query:
                haystack = f"{document.get('title', '')} {chunk.get('content', '')}".lower()
                if query not in haystack:
                    continue
            candidates.append({"chunk": chunk, "document": document})
    return candidates


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
        context_items.append(_knowledge_context_for_chunk(document, chunk))
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


def _knowledge_context_for_chunk(
    document: dict[str, Any],
    chunk: dict[str, Any],
) -> dict[str, Any]:
    return {
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
    return {"summary": _summary_excerpt(summary)}


def _knowledge_space_reference(space: dict[str, Any]) -> dict[str, str]:
    space_id = str(space["id"])
    return {
        "id": space_id,
        "title": str(space.get("name") or space.get("code") or space_id),
        "type": "knowledge_space",
        "url": f"/knowledge/documents?knowledge_space_id={space_id}",
    }


def _knowledge_space_reference_with_metadata(
    current_store: Any,
    space: dict[str, Any],
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    return {
        **_knowledge_space_reference(space),
        **_knowledge_scope_reference_metadata(
            current_store,
            folder=None,
            space=space,
            user=user,
        ),
    }


def _knowledge_folder_reference(folder: dict[str, Any]) -> dict[str, str]:
    folder_id = str(folder["id"])
    space_id = str(folder.get("knowledge_space_id") or "")
    return {
        "id": folder_id,
        "title": str(folder.get("path") or folder.get("name") or folder_id),
        "type": "knowledge_folder",
        "url": f"/knowledge/documents?knowledge_space_id={space_id}&folder_id={folder_id}",
    }


def _knowledge_folder_reference_with_metadata(
    current_store: Any,
    folder: dict[str, Any],
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    return {
        **_knowledge_folder_reference(folder),
        **_knowledge_scope_reference_metadata(
            current_store,
            folder=folder,
            space=None,
            user=user,
        ),
    }


def _knowledge_document_reference(document: dict[str, Any]) -> dict[str, str]:
    document_id = str(document["id"])
    return {
        "id": document_id,
        "title": str(document.get("title") or document_id),
        "type": "knowledge_document",
        "url": f"/knowledge/documents?document_id={document_id}",
    }


def _knowledge_chunk_reference(document: dict[str, Any], chunk: dict[str, Any]) -> dict[str, str]:
    document_id = str(document["id"])
    chunk_id = str(chunk["id"])
    chunk_number = int(chunk.get("chunk_index") or 0) + 1
    title = f"{document.get('title') or document_id} #{chunk_number}"
    return {
        "id": chunk_id,
        "title": title,
        "type": "knowledge_chunk",
        "url": f"/knowledge/documents?document_id={document_id}&chunk_id={chunk_id}",
    }


def _summary_excerpt(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) > 120:
        return f"{normalized[:117]}..."
    return normalized


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
        "knowledge_folder": "knowledge_folders",
        "knowledge_space": "knowledge_spaces",
        "plugin_action": "plugin_actions",
        "plugin_connection": "plugin_connections",
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


def _merge_reference_lists_by_type(
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


def _assistant_reference_type_preferences(message: str) -> dict[str, int]:
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
        (("插件动作", "动作", "plugin action"), ["plugin_action"]),
        (("插件连接", "连接失败", "connection"), ["plugin_connection"]),
        (("ai角色", "agent", "角色"), ["ai_agent"]),
        (("skill", "能力"), ["ai_skill"]),
        (("review", "确认", "评审"), ["human_review", "code_review_report", "ai_task"]),
        (("迭代", "版本", "version"), ["iteration_version", "requirement"]),
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
        "knowledge_folder": (
            f"/knowledge/documents?knowledge_space_id={item.get('knowledge_space_id')}"
            f"&folder_id={item_id}"
        ),
        "knowledge_space": f"/knowledge/documents?knowledge_space_id={item_id}",
        "plugin_action": f"/tasks/plugins?action_id={item_id}",
        "plugin_connection": f"/tasks/plugins?connection_id={item_id}",
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
    if entity_type == "knowledge_folder":
        return str(item.get("path") or item.get("name") or item.get("id") or "")
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
            item.get("description"),
            item.get("name"),
            item.get("path"),
            item.get("status"),
            item.get("summary"),
            item.get("title"),
            title,
        )
    ).lower()
    if normalized_query in haystack:
        return True
    if _assistant_reference_matches_type_alias(entity_type, normalized_query):
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


def _assistant_reference_matches_type_alias(entity_type: str, normalized_query: str) -> bool:
    aliases = REFERENCE_TYPE_QUERY_ALIASES.get(entity_type, ())
    return any(
        alias in normalized_query or normalized_query in alias
        for alias in aliases
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


def _user_can_reference_operational_type(
    user: dict[str, Any] | None,
    reference_type: str,
) -> bool:
    roles = set(user.get("roles") or []) if isinstance(user, dict) else set()
    permissions = set(user.get("permissions") or []) if isinstance(user, dict) else set()
    required_permission = OPERATIONAL_REFERENCE_PERMISSION_BY_TYPE.get(reference_type)
    return (
        "admin" in roles
        or "system.admin" in permissions
        or (required_permission is not None and required_permission in permissions)
    )
