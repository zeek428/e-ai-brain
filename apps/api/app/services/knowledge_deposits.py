from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.listing import add_list_observability, ensure_list_enum, sort_list_items
from app.core.roles import ASSIGNABLE_ROLE_CODES
from app.core.store import MemoryStore
from app.core.trace import envelope
from app.services.knowledge_documents import knowledge_document_chunks, knowledge_document_response
from app.services.knowledge_indexing import (
    build_knowledge_chunks,
    knowledge_index_failed_result,
    knowledge_text_indexed_result,
    knowledge_vector_indexed_result,
    replace_knowledge_chunks_result,
    split_knowledge_content,
)

USER_ROLES = ASSIGNABLE_ROLE_CODES
KNOWLEDGE_INDEX_STATUSES = {
    "archived",
    "importing",
    "indexed",
    "index_failed",
    "pending_index",
    "text_indexed",
    "vector_indexed",
}
KNOWLEDGE_DEPOSIT_SORT_FIELDS = {
    "ai_task_id",
    "created_at",
    "deposit_type",
    "id",
    "status",
    "title",
    "updated_at",
}

__all__ = [
    "KNOWLEDGE_INDEX_STATUSES",
    "KnowledgeRepositoryContext",
    "apply_knowledge_document_to_memory",
    "build_knowledge_chunks",
    "create_knowledge_document_result",
    "delete_knowledge_document_result",
    "get_knowledge_chunk_set_from_memory",
    "get_knowledge_deposit",
    "get_knowledge_document",
    "knowledge_deposit_list_response",
    "knowledge_index_failed_result",
    "knowledge_text_indexed_result",
    "knowledge_vector_indexed_result",
    "knowledge_write_store",
    "patch_knowledge_document_result",
    "put_knowledge_asset_to_memory",
    "put_knowledge_chunk_to_memory",
    "put_knowledge_chunk_set_to_memory",
    "put_knowledge_document_to_memory",
    "replace_knowledge_chunks_result",
    "retry_knowledge_document_index_result",
    "save_knowledge_deposit_records",
    "split_knowledge_content",
]


class KnowledgeRepositoryContext(MemoryStore):
    def __init__(self, repository: Any) -> None:
        super().__init__()
        self.repository = repository

    def new_id(self, prefix: str) -> str:
        next_id = getattr(self.repository, "next_id", None)
        if not callable(next_id):
            return super().new_id(prefix)
        allocated_id = next_id(prefix)
        suffix = allocated_id.removeprefix(f"{prefix}_")
        if suffix.isdigit():
            self.counters[prefix] = max(self.counters.get(prefix, 0), int(suffix))
        return allocated_id


def knowledge_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    list_deposits = getattr(repository, "list_knowledge_deposits", None)
    if callable(list_deposits):
        return repository
    return None


def knowledge_deposit_list_response(
    *,
    current_store: Any,
    page: int | None = None,
    page_size: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None,
    trace_id: str,
) -> dict[str, Any]:
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    resolved_sort_by = sort_by or "created_at"
    ensure_list_enum(resolved_sort_by, KNOWLEDGE_DEPOSIT_SORT_FIELDS, "sort_by")
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    with_pagination = page is not None or page_size is not None
    filters = {"status": status}
    repository = knowledge_query_repository(current_store)
    count_page = getattr(repository, "count_knowledge_deposits", None)
    list_page = getattr(repository, "list_knowledge_deposits_page", None)
    if with_pagination and callable(count_page) and callable(list_page):
        total = count_page(status=status)
        items = list_page(
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            status=status,
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
                list_name="knowledge_deposits",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=started_at,
            ),
            trace_id,
        )
    items = (
        repository.list_knowledge_deposits(status=status)
        if repository is not None
        else list(_read_memory_dict(current_store, "knowledge_deposits").values())
    )
    if status:
        items = [item for item in items if item["status"] == status]
    items = sort_list_items(
        items,
        allowed_fields=KNOWLEDGE_DEPOSIT_SORT_FIELDS,
        default_sort_by=resolved_sort_by,
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    if with_pagination:
        start = (resolved_page - 1) * resolved_page_size
        items = items[start : start + resolved_page_size]
        return envelope(
            add_list_observability(
                {
                    "items": items,
                    "page": resolved_page,
                    "page_size": resolved_page_size,
                    "total": total,
                },
                filters=filters,
                list_name="knowledge_deposits",
                page=resolved_page,
                page_size=resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=started_at,
            ),
            trace_id,
        )
    return envelope({"items": items, "total": total}, trace_id)


def knowledge_write_store(current_store: Any) -> Any:
    repository = knowledge_query_repository(current_store)
    if repository is None:
        return current_store
    source_store = KnowledgeRepositoryContext(repository)
    load_knowledge = getattr(repository, "load_knowledge", None)
    if callable(load_knowledge):
        knowledge_payload = load_knowledge() or {}
        source_store.knowledge_documents = payload_collection(
            knowledge_payload,
            "knowledge_documents",
        )
        source_store.knowledge_chunks = payload_collection(
            knowledge_payload,
            "knowledge_chunks",
        )
        source_store.knowledge_deposits = payload_collection(
            knowledge_payload,
            "knowledge_deposits",
        )
        source_store.knowledge_spaces = payload_collection(
            knowledge_payload,
            "knowledge_spaces",
        )
        source_store.knowledge_space_members = payload_collection(
            knowledge_payload,
            "knowledge_space_members",
        )
        source_store.knowledge_folders = payload_collection(
            knowledge_payload,
            "knowledge_folders",
        )
        source_store.knowledge_assets = payload_collection(
            knowledge_payload,
            "knowledge_assets",
        )
        source_store.knowledge_import_jobs = payload_collection(
            knowledge_payload,
            "knowledge_import_jobs",
        )
        source_store.knowledge_chunk_sets = payload_collection(
            knowledge_payload,
            "knowledge_chunk_sets",
        )
    load_model_gateway = getattr(repository, "load_model_gateway", None)
    if callable(load_model_gateway):
        model_gateway_payload = load_model_gateway() or {}
        source_store.model_gateway_configs = payload_collection(
            model_gateway_payload,
            "model_gateway_configs",
        )
        source_store.model_gateway_logs = [
            dict(item) for item in model_gateway_payload.get("model_gateway_logs", [])
        ]
    list_products = getattr(repository, "list_products", None)
    if callable(list_products):
        source_store.products = {
            str(item["id"]): dict(item)
            for item in list_products()
            if item.get("id") is not None
        }
    return source_store


def payload_collection(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    return {
        str(item_id): dict(item)
        for item_id, item in (payload.get(key) or {}).items()
        if isinstance(item, dict)
    }


def ensure_roles(roles: list[str]) -> None:
    if not roles:
        raise api_error(400, "VALIDATION_ERROR", "roles is required")
    if len(set(roles)) != len(roles):
        raise api_error(400, "VALIDATION_ERROR", "roles must be unique")
    invalid_roles = sorted(set(roles) - USER_ROLES)
    if invalid_roles:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported roles: {', '.join(invalid_roles)}")


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def get_knowledge_deposit(current_store: Any, deposit_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    get_deposit = getattr(repository, "get_knowledge_deposit", None)
    if callable(get_deposit):
        return get_deposit(deposit_id)
    return _read_memory_dict(current_store, "knowledge_deposits").get(deposit_id)


def get_knowledge_document(current_store: Any, document_id: str) -> dict[str, Any] | None:
    return _read_memory_dict(current_store, "knowledge_documents").get(document_id)


def record_audit_event(
    current_store: Any,
    *,
    actor_id: str,
    event_type: str,
    subject_id: str,
    subject_type: str = "knowledge_deposit",
) -> dict[str, Any]:
    audit_events = _memory_audit_events(current_store)
    event = {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": {},
        "sequence": len(audit_events) + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }
    if not uses_repository_context(current_store):
        _append_memory_audit_event(current_store, event)
    return event


def save_knowledge_deposit_records(
    current_store: Any,
    *,
    deposit: dict[str, Any],
    audit_event: dict[str, Any] | None = None,
    document: dict[str, Any] | None = None,
    chunks: list[dict[str, Any]] | None = None,
    model_logs: list[dict[str, Any]] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_knowledge_deposit_records", None)
    if callable(save_records):
        save_records(
            deposit=deposit,
            document=document,
            chunks=chunks
            if chunks is not None
            else (
                knowledge_document_chunks(current_store, document["id"])
                if document is not None
                else None
            ),
            audit_event=audit_event,
            model_logs=model_logs,
        )
        return
    if document is not None:
        apply_knowledge_document_to_memory(
            current_store,
            document,
            chunks
            if chunks is not None
            else knowledge_document_chunks(current_store, document["id"]),
        )
    _memory_collection(current_store, "knowledge_deposits")[str(deposit["id"])] = deposit
    if audit_event is not None:
        _append_memory_audit_event(current_store, audit_event)


def _memory_collection(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        vars(current_store)[collection_name] = collection
    return collection


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, Any]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _read_memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, list) else []


def get_knowledge_chunk_set_from_memory(
    current_store: Any,
    chunk_set_id: str | None,
) -> dict[str, Any] | None:
    if not chunk_set_id:
        return None
    return _memory_collection(current_store, "knowledge_chunk_sets").get(str(chunk_set_id))


def put_knowledge_chunk_set_to_memory(
    current_store: Any,
    chunk_set_id: str,
    chunk_set: dict[str, Any],
) -> None:
    _memory_collection(current_store, "knowledge_chunk_sets")[str(chunk_set_id)] = chunk_set


def put_knowledge_asset_to_memory(
    current_store: Any,
    asset: dict[str, Any],
) -> None:
    asset_id = asset.get("id")
    if asset_id is None:
        return
    _memory_collection(current_store, "knowledge_assets")[str(asset_id)] = asset


def put_knowledge_chunk_to_memory(
    current_store: Any,
    chunk: dict[str, Any],
) -> None:
    chunk_id = chunk.get("id")
    if chunk_id is None:
        return
    _memory_collection(current_store, "knowledge_chunks")[str(chunk_id)] = chunk


def merge_knowledge_chunk_set_to_memory(
    current_store: Any,
    chunk_set_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    chunk_set = {
        **(get_knowledge_chunk_set_from_memory(current_store, chunk_set_id) or {}),
        **updates,
    }
    put_knowledge_chunk_set_to_memory(current_store, chunk_set_id, chunk_set)
    return chunk_set


def _append_memory_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    audit_events = _memory_audit_events(current_store)
    if not any(event.get("id") == audit_event.get("id") for event in audit_events):
        audit_events.append(audit_event)


def _memory_audit_events(current_store: Any) -> list[dict[str, Any]]:
    audit_events = getattr(current_store, "audit_events", None)
    if not isinstance(audit_events, list):
        audit_events = []
        vars(current_store)["audit_events"] = audit_events
    return audit_events


def save_knowledge_document_records(
    current_store: Any,
    *,
    document: dict[str, Any],
    chunks: list[dict[str, Any]] | None = None,
    audit_event: dict[str, Any] | None = None,
    model_logs: list[dict[str, Any]] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_knowledge_document_records", None)
    if callable(save_records):
        save_records(
            document=document,
            chunks=chunks
            if chunks is not None
            else knowledge_document_chunks(current_store, document["id"]),
            audit_event=audit_event,
            model_logs=model_logs,
        )


def persist_knowledge_structure(
    current_store: Any,
    *,
    document: dict[str, Any] | None = None,
) -> None:
    if not uses_repository_context(current_store):
        return
    if document is not None and not any(
        document.get(field)
        for field in (
            "knowledge_space_id",
            "folder_id",
            "source_asset_id",
            "parsed_asset_id",
            "active_chunk_set_id",
        )
    ):
        return
    from app.services.knowledge_management import persist_knowledge_payload

    persist_knowledge_payload(current_store)


def delete_knowledge_document_records(
    current_store: Any,
    *,
    document_id: str,
    deposits: list[dict[str, Any]],
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    delete_records = getattr(repository, "delete_knowledge_document_records", None)
    if callable(delete_records):
        delete_records(document_id=document_id, deposits=deposits, audit_event=audit_event)


def clear_knowledge_chunks(current_store: Any, document_id: str) -> None:
    chunks = _memory_collection(current_store, "knowledge_chunks")
    for chunk_id in [
        chunk_id
        for chunk_id, chunk in chunks.items()
        if chunk.get("document_id") == document_id
    ]:
        chunks.pop(chunk_id, None)


def apply_knowledge_document_to_memory(
    current_store: Any,
    document: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> None:
    _memory_collection(current_store, "knowledge_documents")[str(document["id"])] = document
    clear_knowledge_chunks(current_store, document["id"])
    stored_chunks = _memory_collection(current_store, "knowledge_chunks")
    for chunk in chunks:
        stored_chunks[str(chunk["id"])] = chunk


def put_knowledge_document_to_memory(
    current_store: Any,
    document: dict[str, Any],
) -> None:
    document_id = document.get("id")
    if document_id is None:
        return
    _memory_collection(current_store, "knowledge_documents")[str(document_id)] = document


def remove_knowledge_document_from_memory(
    current_store: Any,
    *,
    affected_deposits: list[dict[str, Any]],
    document_id: str,
) -> None:
    _memory_collection(current_store, "knowledge_documents").pop(document_id, None)
    clear_knowledge_chunks(current_store, document_id)
    deposits = _memory_collection(current_store, "knowledge_deposits")
    for deposit in affected_deposits:
        deposits[str(deposit["id"])] = deposit


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is not None and value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def payload_updates(payload: Any) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


def create_knowledge_document_result(
    *,
    content: str,
    current_store: Any,
    doc_type: str,
    folder_id: str | None = None,
    knowledge_space_id: str | None = None,
    permission_roles: list[str],
    product_id: str | None,
    tags: list[str],
    title: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    title = ensure_non_blank(title, "title")
    content = ensure_non_blank(content, "content")
    if product_id is not None and product_id not in _read_memory_dict(current_store, "products"):
        raise api_error(404, "NOT_FOUND", "Product not found")
    if knowledge_space_id is not None:
        from app.services.knowledge_management import ensure_space_access

        ensure_space_access(current_store, user, space_id=knowledge_space_id, required="write")
        if folder_id is not None:
            folder = _read_memory_dict(current_store, "knowledge_folders").get(folder_id)
            if folder is None or folder.get("knowledge_space_id") != knowledge_space_id:
                raise api_error(404, "NOT_FOUND", "Knowledge folder not found")
    ensure_roles(permission_roles)
    document_id = current_store.new_id("knowledge")
    chunk_set_id = (
        current_store.new_id("knowledge_chunk_set") if knowledge_space_id is not None else None
    )
    now = datetime.now(UTC).isoformat()
    document = {
        "id": document_id,
        "title": title,
        "content": content,
        "doc_type": doc_type,
        "folder_id": folder_id,
        "knowledge_space_id": knowledge_space_id,
        "product_id": product_id,
        "permission_roles": permission_roles,
        "tags": tags,
        "index_status": "pending_index",
        "index_error": None,
        "vector_index_error": None,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    if knowledge_space_id is not None:
        document["active_chunk_set_id"] = chunk_set_id
        document["document_version"] = 1
        document["permission_scope"] = {"knowledge_space_id": knowledge_space_id}
        if chunk_set_id is not None:
            put_knowledge_chunk_set_to_memory(
                current_store,
                chunk_set_id,
                {
                    "id": chunk_set_id,
                    "document_id": document_id,
                    "source_asset_id": None,
                    "parsed_asset_id": None,
                    "parser_engine": "manual_text",
                    "parser_version": "v1",
                    "chunk_strategy": "simple_text",
                    "embedding_model": None,
                    "embedding_dimension": None,
                    "status": "building",
                    "created_by": user["id"],
                    "created_at": now,
                    "updated_at": now,
                    "activated_at": None,
                },
            )
    model_log_start_index = len(_read_memory_list(current_store, "model_gateway_logs"))
    document, chunks = replace_knowledge_chunks_result(current_store, document)
    if chunk_set_id is not None:
        for chunk in chunks:
            chunk["chunk_set_id"] = chunk_set_id
            chunk.setdefault("metadata", {})["knowledge_space_id"] = knowledge_space_id
            chunk["metadata"]["folder_id"] = folder_id
            chunk["metadata"]["chunk_set_id"] = chunk_set_id
        merge_knowledge_chunk_set_to_memory(
            current_store,
            chunk_set_id,
            {
                "status": "active",
                "embedding_model": chunks[0].get("metadata", {}).get("embedding_model")
                if chunks
                else None,
                "embedding_dimension": chunks[0].get("metadata", {}).get("embedding_dimension")
                if chunks
                else None,
                "activated_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
    if not uses_repository_context(current_store):
        apply_knowledge_document_to_memory(current_store, document, chunks)
    audit_event = record_audit_event(
        current_store,
        event_type="knowledge_document.created",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    save_knowledge_document_records(
        current_store,
        document=document,
        chunks=chunks,
        audit_event=audit_event,
        model_logs=_read_memory_list(current_store, "model_gateway_logs")[model_log_start_index:],
    )
    persist_knowledge_structure(current_store, document=document)
    return knowledge_document_response(current_store, document, chunks)


def patch_knowledge_document_result(
    *,
    current_store: Any,
    document_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = get_knowledge_document(current_store, document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    updates = payload_updates(payload)
    if "title" in updates:
        updates["title"] = ensure_non_blank(updates["title"], "title")
    if "content" in updates:
        updates["content"] = ensure_non_blank(updates["content"], "content")
    if "permission_roles" in updates:
        ensure_roles(updates["permission_roles"])
    if "product_id" in updates and updates["product_id"] is not None:
        if updates["product_id"] not in _read_memory_dict(current_store, "products"):
            raise api_error(404, "NOT_FOUND", "Product not found")
    target_space_id = updates.get("knowledge_space_id", document.get("knowledge_space_id"))
    target_folder_id = updates.get("folder_id", document.get("folder_id"))
    if target_space_id is not None:
        from app.services.knowledge_management import ensure_space_access

        ensure_space_access(current_store, user, space_id=target_space_id, required="write")
        if target_folder_id is not None:
            folder = _read_memory_dict(current_store, "knowledge_folders").get(target_folder_id)
            if folder is None or folder.get("knowledge_space_id") != target_space_id:
                raise api_error(404, "NOT_FOUND", "Knowledge folder not found")
    if "index_status" in updates:
        ensure_enum(updates["index_status"], KNOWLEDGE_INDEX_STATUSES, "knowledge index status")
    if "index_error" in updates and updates["index_error"] is not None:
        updates["index_error"] = ensure_non_blank(updates["index_error"], "index_error")
    document = {**document, **updates, "updated_at": datetime.now(UTC).isoformat()}
    model_log_start_index = len(_read_memory_list(current_store, "model_gateway_logs"))
    if updates.get("index_status") == "index_failed":
        document, chunks = knowledge_index_failed_result(
            document,
            document.get("index_error") or "Knowledge indexing failed",
        )
    elif updates.get("index_status") in {"archived", "importing", "pending_index"}:
        chunks = []
        document["chunk_count"] = 0
        document["index_error"] = None
        document["vector_index_error"] = None
    elif updates.get("index_status") == "text_indexed":
        document, chunks = replace_knowledge_chunks_result(
            current_store,
            document,
            attempt_vector=False,
        )
    elif updates.get("index_status") in {"indexed", "vector_indexed"} or {
        "content",
        "folder_id",
        "knowledge_space_id",
        "title",
        "permission_roles",
        "product_id",
        "doc_type",
        "tags",
    }.intersection(updates):
        if document.get("knowledge_space_id") and not document.get("active_chunk_set_id"):
            document["active_chunk_set_id"] = current_store.new_id("knowledge_chunk_set")
        chunk_set_id = document.get("active_chunk_set_id")
        if (
            chunk_set_id
            and get_knowledge_chunk_set_from_memory(current_store, chunk_set_id) is None
        ):
            put_knowledge_chunk_set_to_memory(
                current_store,
                chunk_set_id,
                {
                    "id": chunk_set_id,
                    "document_id": document_id,
                    "source_asset_id": document.get("source_asset_id"),
                    "parsed_asset_id": document.get("parsed_asset_id"),
                    "parser_engine": document.get("parser_engine") or "manual_text",
                    "parser_version": "v1",
                    "chunk_strategy": document.get("chunk_strategy") or "simple_text",
                    "embedding_model": None,
                    "embedding_dimension": None,
                    "status": "building",
                    "created_by": user["id"],
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                    "activated_at": None,
                },
            )
        document, chunks = replace_knowledge_chunks_result(current_store, document)
        if chunk_set_id:
            for chunk in chunks:
                chunk["chunk_set_id"] = chunk_set_id
                chunk.setdefault("metadata", {})["knowledge_space_id"] = document.get(
                    "knowledge_space_id"
                )
                chunk["metadata"]["folder_id"] = document.get("folder_id")
                chunk["metadata"]["chunk_set_id"] = chunk_set_id
            merge_knowledge_chunk_set_to_memory(
                current_store,
                chunk_set_id,
                {
                    "status": "active",
                    "embedding_model": chunks[0].get("metadata", {}).get("embedding_model")
                    if chunks
                    else None,
                    "embedding_dimension": chunks[0].get("metadata", {}).get(
                        "embedding_dimension"
                    )
                    if chunks
                    else None,
                    "activated_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
    else:
        chunks = knowledge_document_chunks(current_store, document_id)
    if not uses_repository_context(current_store):
        apply_knowledge_document_to_memory(current_store, document, chunks)
    audit_event = record_audit_event(
        current_store,
        event_type="knowledge_document.updated",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    save_knowledge_document_records(
        current_store,
        document=document,
        chunks=chunks,
        audit_event=audit_event,
        model_logs=_read_memory_list(current_store, "model_gateway_logs")[model_log_start_index:],
    )
    persist_knowledge_structure(current_store, document=document)
    return knowledge_document_response(current_store, document, chunks)


def retry_knowledge_document_index_result(
    *,
    current_store: Any,
    document_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    document = get_knowledge_document(current_store, document_id)
    if document is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    if document.get("index_status") not in {"index_failed", "text_indexed"}:
        raise api_error(
            409,
            "KNOWLEDGE_INDEX_STATE_INVALID",
            "Knowledge document is not eligible for index retry",
        )
    document = {**document, "updated_at": datetime.now(UTC).isoformat()}
    model_log_start_index = len(_read_memory_list(current_store, "model_gateway_logs"))
    document, chunks = replace_knowledge_chunks_result(current_store, document)
    chunk_set_id = document.get("active_chunk_set_id")
    if chunk_set_id:
        for chunk in chunks:
            chunk["chunk_set_id"] = chunk_set_id
            chunk.setdefault("metadata", {})["knowledge_space_id"] = document.get(
                "knowledge_space_id"
            )
            chunk["metadata"]["folder_id"] = document.get("folder_id")
            chunk["metadata"]["chunk_set_id"] = chunk_set_id
        if get_knowledge_chunk_set_from_memory(current_store, chunk_set_id) is not None:
            merge_knowledge_chunk_set_to_memory(
                current_store,
                chunk_set_id,
                {
                    "status": "active",
                    "embedding_model": chunks[0].get("metadata", {}).get("embedding_model")
                    if chunks
                    else None,
                    "embedding_dimension": chunks[0].get("metadata", {}).get(
                        "embedding_dimension"
                    )
                    if chunks
                    else None,
                    "activated_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
    if not uses_repository_context(current_store):
        apply_knowledge_document_to_memory(current_store, document, chunks)
    audit_event = record_audit_event(
        current_store,
        event_type="knowledge_document.index_retried",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    save_knowledge_document_records(
        current_store,
        document=document,
        chunks=chunks,
        audit_event=audit_event,
        model_logs=_read_memory_list(current_store, "model_gateway_logs")[model_log_start_index:],
    )
    persist_knowledge_structure(current_store, document=document)
    return knowledge_document_response(current_store, document, chunks)


def delete_knowledge_document_result(
    *,
    current_store: Any,
    document_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    if get_knowledge_document(current_store, document_id) is None:
        raise api_error(404, "NOT_FOUND", "Knowledge document not found")
    affected_deposits = []
    now = datetime.now(UTC).isoformat()
    for deposit in _read_memory_dict(current_store, "knowledge_deposits").values():
        if deposit.get("knowledge_document_id") == document_id:
            affected_deposit = {
                **deposit,
                "knowledge_document_id": None,
                "updated_at": now,
            }
            affected_deposits.append(affected_deposit)
    if not uses_repository_context(current_store):
        remove_knowledge_document_from_memory(
            current_store,
            affected_deposits=affected_deposits,
            document_id=document_id,
        )
    audit_event = record_audit_event(
        current_store,
        event_type="knowledge_document.deleted",
        actor_id=user["id"],
        subject_type="knowledge_document",
        subject_id=document_id,
    )
    delete_knowledge_document_records(
        current_store,
        document_id=document_id,
        deposits=affected_deposits,
        audit_event=audit_event,
    )
    return {"deleted": True, "id": document_id}
