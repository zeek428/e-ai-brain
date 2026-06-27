from __future__ import annotations

from typing import Any

from fastapi import Request

from app.api.deps import api_error, require_permissions
from app.core.listing import (
    add_list_observability,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.trace import envelope, get_trace_id

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
    "folder_id",
    "id",
    "index_status",
    "knowledge_space_id",
    "permission_roles",
    "title",
    "updated_at",
}


def knowledge_repository_access_args(user: dict[str, Any]) -> dict[str, Any]:
    roles = list(user.get("roles") or [])
    global_access = "admin" in set(roles)
    space_scope_ids: list[str] = []
    for scope in user.get("scope_summary") or []:
        if scope.get("scope_type") not in {"global", "knowledge_space"}:
            continue
        if scope.get("access_level") not in {"read", "write", "admin"}:
            continue
        scope_id = scope.get("scope_id")
        if scope_id == "*":
            global_access = True
        elif scope.get("scope_type") == "knowledge_space" and scope_id:
            space_scope_ids.append(str(scope_id))
    return {
        "global_knowledge_access": global_access,
        "knowledge_space_scope_ids": sorted(set(space_scope_ids)),
        "user_id": str(user["id"]) if user.get("id") is not None else None,
        "user_roles": roles,
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


def knowledge_memory_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def knowledge_memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(knowledge_memory_collection(current_store, collection_name).values())


def knowledge_document_chunks(current_store: Any, document_id: str) -> list[dict[str, Any]]:
    chunks = [
        chunk
        for chunk in knowledge_memory_records(current_store, "knowledge_chunks")
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
    folder_id = document.get("folder_id")
    if folder_id:
        folder = getattr(current_store, "knowledge_folders", {}).get(folder_id)
        if folder is not None:
            response["folder_path"] = folder.get("path") or folder.get("name")
    response["index_error"] = document.get("index_error")
    response["vector_index_error"] = document.get("vector_index_error")
    return response


def knowledge_document_list_response(
    *,
    current_store: Any,
    doc_type: str | None,
    index_status: str | None,
    keyword: str | None,
    folder_id: str | None = None,
    knowledge_space_id: str | None = None,
    page: int | None,
    page_size: int | None,
    permission_role: str | None,
    request: Request,
    sort_by: str | None,
    sort_order: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_permissions(user, {"knowledge.read"})
    ensure_knowledge_index_status(index_status)
    if sort_order not in {"asc", "desc"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_order")
    resolved_sort_by = sort_by or "id"
    if resolved_sort_by not in KNOWLEDGE_DOCUMENT_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    repository = knowledge_query_repository(current_store)
    access_args = knowledge_repository_access_args(user)
    filters = {
        "doc_type": doc_type,
        "folder_id": folder_id,
        "index_status": index_status,
        "keyword": keyword,
        "knowledge_space_id": knowledge_space_id,
        "permission_role": permission_role,
    }
    if (
        repository is not None
        and (page is not None or page_size is not None)
        and callable(getattr(repository, "count_knowledge_document_summaries", None))
        and callable(getattr(repository, "list_knowledge_document_summaries_page", None))
    ):
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        count_args = {
            **access_args,
            "doc_type": doc_type,
            "folder_id": folder_id,
            "index_status": index_status,
            "keyword": keyword,
            "knowledge_space_id": knowledge_space_id,
            "permission_role": permission_role,
        }
        total = repository.count_knowledge_document_summaries(**count_args)
        items = repository.list_knowledge_document_summaries_page(
            **count_args,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        return envelope(
            add_list_observability(
                {
                    "items": items,
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "total": total,
                },
                filters=filters,
                list_name="knowledge_documents",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=request_started_at(request),
            ),
            get_trace_id(request),
        )
    if repository is not None:
        try:
            items = repository.list_knowledge_documents(
                **access_args,
                keyword=keyword,
                doc_type=doc_type,
                index_status=index_status,
                folder_id=folder_id,
                knowledge_space_id=knowledge_space_id,
            )
        except TypeError:
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
            folder_id=folder_id,
            index_status=index_status,
            knowledge_space_id=knowledge_space_id,
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
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        items,
        filters=filters,
        list_name="knowledge_documents",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
        started_at=request_started_at(request),
        trace_id=get_trace_id(request),
    )


def memory_knowledge_document_items(
    *,
    current_store: Any,
    doc_type: str | None,
    folder_id: str | None,
    index_status: str | None,
    knowledge_space_id: str | None,
    keyword: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    from app.services.knowledge_management import document_is_readable

    items = [
        document
        for document in knowledge_memory_records(current_store, "knowledge_documents")
        if document_is_readable(current_store, user, document)
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
    if knowledge_space_id:
        items = [item for item in items if item.get("knowledge_space_id") == knowledge_space_id]
    if folder_id:
        items = [item for item in items if item.get("folder_id") == folder_id]
    if index_status:
        items = [item for item in items if item["index_status"] == index_status]
    return [knowledge_document_response(current_store, item) for item in items]
