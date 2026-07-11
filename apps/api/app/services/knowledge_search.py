from __future__ import annotations

from time import perf_counter
from typing import Any

from app.api.deps import api_error
from app.core.trace import envelope
from app.services.knowledge_documents import (
    knowledge_document_chunks,
    knowledge_memory_records,
    knowledge_query_repository,
    knowledge_repository_access_args,
    user_can_read_roles,
)
from app.services.knowledge_quality import record_knowledge_quality_event_best_effort
from app.services.model_gateway import (
    ModelGatewayCallError,
    ModelGatewayConfigError,
    call_model_gateway_embeddings_with_context,
)

KNOWLEDGE_SEARCHABLE_STATUSES = {"indexed", "text_indexed", "vector_indexed"}


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def chunk_embedding_is_compatible(
    chunk: dict[str, Any],
    query_embedding_context: dict[str, Any],
) -> bool:
    embedding = chunk.get("embedding")
    if not isinstance(embedding, list):
        return False
    metadata = chunk.get("metadata") or {}
    query_dimension = query_embedding_context.get("embedding_dimension")
    chunk_dimension = metadata.get("embedding_dimension")
    if query_dimension is not None:
        try:
            normalized_query_dimension = int(query_dimension)
            normalized_chunk_dimension = (
                int(chunk_dimension) if chunk_dimension is not None else None
            )
        except (TypeError, ValueError):
            return False
        if (
            normalized_chunk_dimension is not None
            and normalized_chunk_dimension != normalized_query_dimension
        ):
            return False
        if len(embedding) != normalized_query_dimension:
            return False
    query_model = query_embedding_context.get("embedding_model")
    chunk_model = metadata.get("embedding_model")
    if query_model and chunk_model and chunk_model != query_model:
        return False
    query_config_id = query_embedding_context.get("embedding_config_id")
    chunk_config_id = metadata.get("embedding_config_id")
    if query_config_id and chunk_config_id and chunk_config_id != query_config_id:
        return False
    return True


def has_readable_vector_chunks(current_store: Any, user: dict[str, Any]) -> bool:
    from app.services.knowledge_management import document_is_readable

    for document in knowledge_memory_records(current_store, "knowledge_documents"):
        if document.get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES:
            continue
        if not document_is_readable(current_store, user, document):
            continue
        for chunk in knowledge_document_chunks(current_store, document["id"]):
            chunk_readable = bool(document.get("knowledge_space_id"))
            if not chunk_readable:
                chunk_roles = chunk.get("permission_roles", document["permission_roles"])
                chunk_readable = user_can_read_roles(user, chunk_roles)
            if chunk_readable and isinstance(chunk.get("embedding"), list):
                return True
    return False


def knowledge_query_embedding(
    current_store: Any,
    query: str,
) -> tuple[list[float], dict[str, Any]] | None:
    try:
        embeddings, embedding_context = call_model_gateway_embeddings_with_context(
            current_store,
            [query],
        )
        return embeddings[0], embedding_context
    except (ModelGatewayConfigError, ModelGatewayCallError):
        return None


def knowledge_search_response(
    *,
    current_store: Any,
    knowledge_space_id: str | None,
    query_value: str,
    top_k: int,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    started_at = perf_counter()
    query = ensure_non_blank(query_value, "query").lower()
    candidates, query_embedding_result = knowledge_search_candidates(
        current_store=current_store,
        knowledge_space_id=knowledge_space_id,
        query=query,
        user=user,
    )
    query_embedding = query_embedding_result[0] if query_embedding_result else None
    query_embedding_context = query_embedding_result[1] if query_embedding_result else None
    items = knowledge_search_items(
        candidates=candidates,
        query=query,
        query_embedding=query_embedding,
        query_embedding_context=query_embedding_context,
    )
    items.sort(
        key=lambda item: (
            -(item["score"] if item["score"] is not None else -1.0),
            item["document_id"],
            item["chunk_index"],
        )
    )
    returned_items = items[: max(1, min(top_k, 50))]
    metrics = knowledge_search_metrics(
        items=returned_items,
        total_candidates=len(items),
    )
    quality_event = record_knowledge_quality_event_best_effort(
        current_store,
        event_type="search",
        hit_count=len(returned_items),
        knowledge_space_id=knowledge_space_id,
        latency_ms=round((perf_counter() - started_at) * 1000, 2),
        metadata={"top_k": top_k, "total_candidates": len(items)},
        no_result=len(returned_items) == 0,
        query=query_value,
        retrieval_modes=metrics.get("retrieval_modes") or {},
        trace_id=trace_id,
        user=user,
    )
    if quality_event:
        metrics["quality_event_id"] = quality_event.get("id")
    return envelope(
        {
            "items": returned_items,
            "metrics": metrics,
            "total": len(items),
        },
        trace_id,
    )


def knowledge_search_metrics(
    *,
    items: list[dict[str, Any]],
    total_candidates: int,
) -> dict[str, Any]:
    retrieval_modes: dict[str, int] = {}
    for item in items:
        mode = item.get("retrieval_mode") or "unknown"
        retrieval_modes[mode] = retrieval_modes.get(mode, 0) + 1
    return {
        "hit_count": len(items),
        "no_result": len(items) == 0,
        "no_result_rate": 1.0 if len(items) == 0 else 0.0,
        "recall_proxy": len(items) / total_candidates if total_candidates else 0.0,
        "retrieval_modes": retrieval_modes,
        "total_candidates": total_candidates,
    }


def knowledge_search_candidates(
    *,
    current_store: Any,
    knowledge_space_id: str | None,
    query: str,
    user: dict[str, Any],
) -> tuple[list[dict[str, Any]], tuple[list[float], dict[str, Any]] | None]:
    repository = knowledge_query_repository(current_store)
    has_vector_chunks = getattr(repository, "has_readable_vector_chunks", None)
    search_chunks = getattr(repository, "search_knowledge_chunks", None)
    search_hybrid_chunks = getattr(repository, "search_knowledge_chunks_hybrid", None)
    if callable(has_vector_chunks) and callable(search_chunks):
        access_args = knowledge_repository_access_args(user)
        try:
            has_vectors = has_vector_chunks(
                **access_args,
                knowledge_space_id=knowledge_space_id,
            )
        except TypeError:
            has_vectors = has_vector_chunks(user_roles=access_args["user_roles"])
        query_embedding_result = (
            knowledge_query_embedding(current_store, query) if has_vectors else None
        )
        if query_embedding_result is not None and callable(search_hybrid_chunks):
            try:
                return (
                    search_hybrid_chunks(
                        **access_args,
                        candidate_limit=50,
                        knowledge_space_id=knowledge_space_id,
                        query=query,
                        query_embedding=query_embedding_result[0],
                    ),
                    query_embedding_result,
                )
            except TypeError:
                pass
        try:
            candidates = search_chunks(
                **access_args,
                knowledge_space_id=knowledge_space_id,
                query=None if query_embedding_result is not None else query,
            )
        except TypeError:
            candidates = search_chunks(
                user_roles=access_args["user_roles"],
                query=None if query_embedding_result is not None else query,
            )
        return candidates, query_embedding_result

    query_embedding_result = (
        knowledge_query_embedding(current_store, query)
        if has_readable_vector_chunks(current_store, user)
        else None
    )
    return memory_knowledge_search_candidates(
        current_store=current_store,
        knowledge_space_id=knowledge_space_id,
        user=user,
    ), query_embedding_result


def memory_knowledge_search_candidates(
    *,
    current_store: Any,
    knowledge_space_id: str | None,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    from app.services.knowledge_management import document_is_readable

    candidates = []
    document_versions = getattr(current_store, "knowledge_document_versions", {})
    for document in knowledge_memory_records(current_store, "knowledge_documents"):
        if document.get("index_status") not in KNOWLEDGE_SEARCHABLE_STATUSES:
            continue
        if knowledge_space_id and document.get("knowledge_space_id") != knowledge_space_id:
            continue
        if not document_is_readable(current_store, user, document):
            continue
        chunks = knowledge_document_chunks(current_store, document["id"])
        if not chunks:
            continue
        for chunk in chunks:
            if not document.get("knowledge_space_id"):
                chunk_roles = chunk.get("permission_roles", document["permission_roles"])
                if not user_can_read_roles(user, chunk_roles):
                    continue
            if document.get("active_chunk_set_id") and chunk.get("chunk_set_id"):
                if chunk["chunk_set_id"] != document["active_chunk_set_id"]:
                    continue
            elif document.get("active_chunk_set_id"):
                continue
            active_document_version = (
                document_versions.get(document.get("active_document_version_id"))
                if isinstance(document_versions, dict)
                else None
            )
            candidates.append(
                {
                    "chunk": chunk,
                    "document": {
                        **document,
                        "active_document_version": active_document_version,
                    },
                }
            )
    return candidates


def knowledge_search_items(
    *,
    candidates: list[dict[str, Any]],
    query: str,
    query_embedding: list[float] | None,
    query_embedding_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    items = []
    chunk_content_by_id = {
        candidate["chunk"]["id"]: candidate["chunk"]["content"]
        for candidate in candidates
    }
    for candidate in candidates:
        document = candidate["document"]
        chunk = candidate["chunk"]
        if chunk.get("metadata", {}).get("chunk_role") == "parent":
            continue
        haystack = f"{document['title']} {chunk['content']}".lower()
        embedding = chunk.get("embedding")
        score = None
        retrieval_modes = set(chunk.get("retrieval_modes") or [])
        precomputed_score = chunk.get("hybrid_score")
        if precomputed_score is not None:
            score = float(precomputed_score)
            if not retrieval_modes:
                retrieval_modes.add("hybrid")
        elif (
            query_embedding is not None
            and query_embedding_context is not None
            and isinstance(embedding, list)
            and chunk_embedding_is_compatible(chunk, query_embedding_context)
        ):
            score = cosine_similarity(
                query_embedding,
                [float(value) for value in embedding],
            )
            if score <= 0 and query not in haystack:
                continue
        elif query not in haystack:
            continue
        retrieval_mode = (
            "hybrid"
            if {"keyword", "vector"}.issubset(retrieval_modes)
            else ("vector" if "vector" in retrieval_modes or score is not None else "keyword")
        )
        if query in haystack and score is not None:
            score += 1.0
        parent_chunk_id = chunk.get("parent_chunk_id")
        parent_content = None
        if parent_chunk_id:
            parent_content = chunk_content_by_id.get(parent_chunk_id) or chunk.get(
                "metadata",
                {},
            ).get("parent_content")
        active_document_version = document.get("active_document_version")
        from app.services.knowledge_multimodal_governance import version_freshness_status

        chunk_metadata = chunk.get("metadata", {})
        items.append(
            {
                "chunk_id": chunk["id"],
                "chunk_index": chunk["chunk_index"],
                "document_id": document["id"],
                "title": document["title"],
                "content": chunk["content"],
                "retrieval_mode": retrieval_mode,
                "score": round(score, 6) if score is not None else None,
                "source": {
                    "asset_id": document.get("source_asset_id")
                    or chunk.get("metadata", {}).get("source_asset_id"),
                    "chunk_id": chunk["id"],
                    "chunk_set_id": document.get("active_chunk_set_id")
                    or chunk_metadata.get("chunk_set_id"),
                    "document_version_id": chunk.get("document_version_id")
                    or document.get("active_document_version_id")
                    or chunk_metadata.get("document_version_id"),
                    "document_version": (active_document_version or {}).get("version")
                    or chunk_metadata.get("document_version"),
                    "expires_at": (active_document_version or {}).get("expires_at")
                    or chunk_metadata.get("expires_at"),
                    "freshness_status": version_freshness_status(
                        active_document_version
                        or {
                            "status": "active",
                            "expires_at": chunk_metadata.get("expires_at"),
                        }
                    ),
                    "modality": chunk.get("modality")
                    or chunk_metadata.get("modality", "text"),
                    "page_number": chunk_metadata.get("page_number"),
                    "bounding_boxes": chunk_metadata.get("bounding_boxes") or [],
                    "provider_metadata": chunk_metadata.get("provider_metadata") or {},
                    "structured_asset_id": chunk_metadata.get("structured_asset_id"),
                    "doc_type": document["doc_type"],
                    "folder_id": document.get("folder_id")
                    or chunk_metadata.get("folder_id"),
                    "knowledge_space_id": document.get("knowledge_space_id")
                    or chunk_metadata.get("knowledge_space_id"),
                    "parent_chunk_id": parent_chunk_id,
                    "parent_content": parent_content,
                    "retrieval_modes": sorted(retrieval_modes),
                    "hybrid_score": chunk.get("hybrid_score"),
                    "keyword_rank": chunk.get("keyword_rank"),
                    "vector_rank": chunk.get("vector_rank"),
                    "vector_score": chunk.get("vector_score"),
                    "title": document["title"],
                },
            }
        )
    return items
