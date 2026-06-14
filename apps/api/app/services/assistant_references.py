from __future__ import annotations

from typing import Any

from app.services.knowledge_documents import (
    knowledge_document_chunks,
    knowledge_query_repository,
    knowledge_repository_access_args,
    user_can_read_roles,
)
from app.services.knowledge_search import KNOWLEDGE_SEARCHABLE_STATUSES


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
    limit: int = 6,
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
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    preferred_types = _assistant_reference_type_preferences(message)
    ordered_pools = sorted(
        pools,
        key=lambda item: preferred_types.get(item[0], len(preferred_types) + 10),
    )
    for entity_type, items in ordered_pools:
        for item in sorted(items, key=_assistant_reference_sort_key, reverse=True)[:3]:
            reference = _assistant_reference_for_entity(entity_type, item)
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
    if normalized_type == "knowledge_document":
        items = _knowledge_document_reference_candidates(
            current_store,
            limit=normalized_limit,
            query=message,
            user=user,
        )
        return {"items": items, "total": len(items)}
    if normalized_type:
        items = [
            reference
            for reference in assistant_reference_candidates(
                current_store,
                limit=normalized_limit,
                message=message,
                product_id=product_id,
            )
            if reference["type"] == normalized_type
        ]
        return {"items": items[:normalized_limit], "total": len(items)}
    items = _merge_reference_lists(
        _knowledge_document_reference_candidates(
            current_store,
            limit=normalized_limit,
            query=message,
            user=user,
        ),
        assistant_reference_candidates(
            current_store,
            limit=normalized_limit,
            message=message,
            product_id=product_id,
        ),
        limit=normalized_limit,
    )
    return {"items": items, "total": len(items)}


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
        "product": "products",
        "requirement": "requirements",
    }
    collection_name = collection_map.get(entity_type)
    if collection_name is None:
        return None
    item = getattr(current_store, collection_name, {}).get(item_id)
    if item is None:
        return None
    return _assistant_reference_for_entity(entity_type, item)


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
) -> dict[str, str] | None:
    item_id = item.get("id")
    if item_id is None:
        return None
    title = (
        item.get("title")
        or item.get("name")
        or item.get("summary")
        or item.get("code")
        or str(item_id)
    )
    route_map = {
        "ai_task": f"/delivery/rd-tasks?task_id={item_id}",
        "bug": f"/delivery/bugs?bug_id={item_id}",
        "code_review_report": f"/delivery/rd-tasks?code_review_report_id={item_id}",
        "human_review": f"/delivery/rd-tasks?review_id={item_id}",
        "iteration_version": f"/delivery/versions?version_id={item_id}",
        "knowledge_deposit": f"/knowledge/documents?deposit_id={item_id}",
        "product": f"/assets/products?product_id={item_id}",
        "requirement": f"/delivery/requirements?requirement_id={item_id}",
    }
    return {
        "id": str(item_id),
        "title": str(title),
        "type": entity_type,
        "url": route_map[entity_type],
    }
