from __future__ import annotations

from typing import Any

from app.services.assistant_reference_formatting import summary_excerpt
from app.services.knowledge_documents import (
    knowledge_document_chunks,
    knowledge_query_repository,
    knowledge_repository_access_args,
    user_can_read_roles,
)
from app.services.knowledge_search import KNOWLEDGE_SEARCHABLE_STATUSES


def refresh_knowledge_scope_collections_from_repository(current_store: Any) -> None:
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


def readable_knowledge_spaces(
    current_store: Any,
    *,
    query: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    from app.services.knowledge_management import user_can_access_space

    refresh_knowledge_scope_collections_from_repository(current_store)
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


def readable_knowledge_space(
    current_store: Any,
    *,
    space_id: str,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    for space in readable_knowledge_spaces(current_store, query=None, user=user):
        if str(space.get("id")) == space_id:
            return space
    return None


def readable_knowledge_folders(
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

    refresh_knowledge_scope_collections_from_repository(current_store)
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


def readable_knowledge_folder(
    current_store: Any,
    *,
    folder_id: str,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    for folder in readable_knowledge_folders(current_store, query=None, user=user):
        if str(folder.get("id")) == folder_id:
            return folder
    return None


def knowledge_document_reference_candidates(
    current_store: Any,
    *,
    limit: int,
    query: str,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    normalized_query = query.strip()
    documents = readable_knowledge_documents(
        current_store,
        query=normalized_query or None,
        user=user,
    )
    references = [
        {
            **knowledge_document_reference(document),
            "chunk_count": knowledge_document_injectable_chunk_count(
                current_store,
                document=document,
                user=user,
            ),
            "index_status": str(document.get("index_status") or ""),
            **knowledge_document_reference_summary(document),
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


def knowledge_chunk_reference_candidates(
    current_store: Any,
    *,
    limit: int,
    query: str,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    normalized_query = query.strip().lower()
    candidates = readable_knowledge_chunk_candidates(
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
                **knowledge_chunk_reference(document, chunk),
                "chunk_count": 1,
                "chunk_index": int(chunk.get("chunk_index") or 0),
                "document_id": str(document["id"]),
                "summary": summary_excerpt(str(chunk.get("content") or "")),
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


def knowledge_scope_documents(
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
        for document in readable_knowledge_documents(
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


def knowledge_scope_chunk_count(
    current_store: Any,
    *,
    documents: list[dict[str, Any]],
    user: dict[str, Any],
) -> int:
    return sum(
        len(readable_knowledge_chunks(current_store, document=document, user=user))
        for document in documents
    )


def knowledge_scope_reference_metadata(
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
    documents = knowledge_scope_documents(
        current_store,
        folder_id=folder_id,
        space_id=space_id,
        user=user,
    )
    chunk_count = knowledge_scope_chunk_count(
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
        "summary": summary_excerpt(summary),
    }


def knowledge_context_for_space(
    current_store: Any,
    *,
    max_chunks: int,
    space: dict[str, Any],
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    return knowledge_context_for_scope(
        current_store,
        folder_id=None,
        max_chunks=max_chunks,
        space_id=str(space["id"]),
        user=user,
    )


def knowledge_context_for_folder(
    current_store: Any,
    *,
    folder: dict[str, Any],
    max_chunks: int,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    return knowledge_context_for_scope(
        current_store,
        folder_id=str(folder["id"]),
        max_chunks=max_chunks,
        space_id=str(folder["knowledge_space_id"]),
        user=user,
    )


def knowledge_context_for_scope(
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
    for document in knowledge_scope_documents(
        current_store,
        folder_id=folder_id,
        space_id=space_id,
        user=user,
    ):
        remaining = max_chunks - len(context_items)
        if remaining <= 0:
            break
        context_items.extend(
            knowledge_context_for_document(
                current_store,
                document=document,
                max_chunks=remaining,
                user=user,
            )
        )
    return context_items[:max_chunks]


def readable_knowledge_documents(
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


def readable_knowledge_document(
    current_store: Any,
    *,
    document_id: str,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    for document in readable_knowledge_documents(
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


def readable_knowledge_chunk(
    current_store: Any,
    *,
    chunk_id: str,
    user: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for candidate in readable_knowledge_chunk_candidates(
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


def readable_knowledge_chunk_candidates(
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
    for document in readable_knowledge_documents(
        current_store,
        query=None,
        user=user,
    ):
        if document.get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES:
            continue
        for chunk in readable_knowledge_chunks(
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


def knowledge_context_for_document(
    current_store: Any,
    *,
    document: dict[str, Any],
    max_chunks: int,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    if max_chunks <= 0:
        return []
    candidates = readable_knowledge_chunks(
        current_store,
        document=document,
        user=user,
    )
    context_items = []
    for chunk in candidates[:max_chunks]:
        context_items.append(knowledge_context_for_chunk(document, chunk))
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


def knowledge_context_for_chunk(
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


def readable_knowledge_chunks(
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


def knowledge_document_injectable_chunk_count(
    current_store: Any,
    *,
    document: dict[str, Any],
    user: dict[str, Any],
) -> int:
    repository = knowledge_query_repository(current_store)
    search_chunks = getattr(repository, "search_knowledge_chunks", None)
    if repository is not None and not callable(search_chunks):
        return int(document.get("chunk_count") or 0)
    return len(
        readable_knowledge_chunks(
            current_store,
            document=document,
            user=user,
        )
    )


def knowledge_document_reference_summary(document: dict[str, Any]) -> dict[str, str]:
    summary = str(
        document.get("summary")
        or document.get("abstract")
        or document.get("description")
        or document.get("content")
        or ""
    ).strip()
    if not summary:
        return {}
    return {"summary": summary_excerpt(summary)}


def knowledge_space_reference(space: dict[str, Any]) -> dict[str, str]:
    space_id = str(space["id"])
    return {
        "id": space_id,
        "title": str(space.get("name") or space.get("code") or space_id),
        "type": "knowledge_space",
        "url": f"/knowledge/documents?knowledge_space_id={space_id}",
    }


def knowledge_space_reference_with_metadata(
    current_store: Any,
    space: dict[str, Any],
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    return {
        **knowledge_space_reference(space),
        **knowledge_scope_reference_metadata(
            current_store,
            folder=None,
            space=space,
            user=user,
        ),
    }


def knowledge_folder_reference(folder: dict[str, Any]) -> dict[str, str]:
    folder_id = str(folder["id"])
    space_id = str(folder.get("knowledge_space_id") or "")
    return {
        "id": folder_id,
        "title": str(folder.get("path") or folder.get("name") or folder_id),
        "type": "knowledge_folder",
        "url": f"/knowledge/documents?knowledge_space_id={space_id}&folder_id={folder_id}",
    }


def knowledge_folder_reference_with_metadata(
    current_store: Any,
    folder: dict[str, Any],
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    return {
        **knowledge_folder_reference(folder),
        **knowledge_scope_reference_metadata(
            current_store,
            folder=folder,
            space=None,
            user=user,
        ),
    }


def knowledge_document_reference(document: dict[str, Any]) -> dict[str, str]:
    document_id = str(document["id"])
    return {
        "id": document_id,
        "title": str(document.get("title") or document_id),
        "type": "knowledge_document",
        "url": f"/knowledge/documents?document_id={document_id}",
    }


def knowledge_chunk_reference(document: dict[str, Any], chunk: dict[str, Any]) -> dict[str, str]:
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
