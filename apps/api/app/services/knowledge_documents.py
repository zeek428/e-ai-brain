from __future__ import annotations

from typing import Any

from fastapi import Request

from app.api.deps import api_error
from app.core.listing import list_text_matches, paginated_list_payload, sort_list_items
from app.core.trace import get_trace_id

KNOWLEDGE_INDEX_STATUSES = {
    "archived",
    "importing",
    "indexed",
    "index_failed",
    "pending_index",
    "text_indexed",
    "vector_indexed",
}

KNOWLEDGE_DOCUMENT_SORT_FIELDS = {
    "created_at",
    "doc_type",
    "id",
    "index_status",
    "title",
    "updated_at",
}


def request_started_at(request: Request) -> float | None:
    started_at = getattr(request.state, "started_at", None)
    return started_at if isinstance(started_at, float) else None


def ensure_knowledge_index_status(index_status: str | None) -> None:
    if index_status is not None and index_status not in KNOWLEDGE_INDEX_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "Invalid knowledge index status")


def knowledge_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    list_documents = getattr(repository, "list_knowledge_documents", None)
    if callable(list_documents):
        return repository
    return None


def user_can_read_roles(user: dict[str, Any], permission_roles: list[str]) -> bool:
    user_roles = set(user["roles"])
    if "admin" in user_roles:
        return True
    return bool(user_roles.intersection(permission_roles))


def knowledge_document_chunks(current_store: Any, document_id: str) -> list[dict[str, Any]]:
    chunks = [
        chunk
        for chunk in current_store.knowledge_chunks.values()
        if chunk.get("document_id") == document_id
    ]
    return sorted(chunks, key=lambda chunk: (chunk.get("chunk_index", 0), chunk.get("id", "")))


def knowledge_document_response(
    current_store: Any,
    document: dict[str, Any],
    chunks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    response = current_store.snapshot(document)
    response["chunk_count"] = (
        len(chunks)
        if chunks is not None
        else len(knowledge_document_chunks(current_store, document["id"]))
    )
    response["index_error"] = document.get("index_error")
    response["vector_index_error"] = document.get("vector_index_error")
    return response


def knowledge_document_list_response(
    *,
    current_store: Any,
    doc_type: str | None,
    index_status: str | None,
    keyword: str | None,
    page: int | None,
    page_size: int | None,
    permission_role: str | None,
    request: Request,
    sort_by: str | None,
    sort_order: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    ensure_knowledge_index_status(index_status)
    repository = knowledge_query_repository(current_store)
    if repository is not None:
        items = repository.list_knowledge_documents(
            user_roles=list(user.get("roles", [])),
            keyword=keyword,
            doc_type=doc_type,
            index_status=index_status,
        )
    else:
        items = memory_knowledge_document_items(
            current_store=current_store,
            doc_type=doc_type,
            index_status=index_status,
            keyword=keyword,
            user=user,
        )
    items = [
        item
        for item in items
        if list_text_matches(item, permission_role, ("permission_roles",))
    ]
    items = sort_list_items(
        items,
        allowed_fields=KNOWLEDGE_DOCUMENT_SORT_FIELDS,
        default_sort_by="id",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters={
            "doc_type": doc_type,
            "index_status": index_status,
            "keyword": keyword,
            "permission_role": permission_role,
        },
        list_name="knowledge_documents",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=sort_by or "id",
        sort_order=sort_order,
        started_at=request_started_at(request),
        trace_id=get_trace_id(request),
    )


def memory_knowledge_document_items(
    *,
    current_store: Any,
    doc_type: str | None,
    index_status: str | None,
    keyword: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    items = [
        document
        for document in current_store.knowledge_documents.values()
        if user_can_read_roles(user, document["permission_roles"])
    ]
    if keyword:
        normalized_keyword = keyword.lower()
        items = [
            item
            for item in items
            if normalized_keyword in f"{item['title']} {item['content']}".lower()
        ]
    if doc_type:
        items = [item for item in items if item["doc_type"] == doc_type]
    if index_status:
        items = [item for item in items if item["index_status"] == index_status]
    return [knowledge_document_response(current_store, item) for item in items]
