from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.services.model_gateway import (
    ModelGatewayCallError,
    ModelGatewayConfigError,
    call_model_gateway_embeddings_with_context,
)


def split_knowledge_content(content: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", content) if part.strip()]
    if not paragraphs:
        paragraphs = [content.strip()]
    chunks: list[str] = []
    max_chars = 1200
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        for start in range(0, len(paragraph), max_chars):
            chunk = paragraph[start : start + max_chars].strip()
            if chunk:
                chunks.append(chunk)
    return chunks


def build_knowledge_chunks(
    document: dict[str, Any],
    chunks: list[str],
    *,
    embeddings: list[list[float]] | None = None,
    embedding_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    permission_roles = list(document.get("permission_roles", ["admin"]))
    now = datetime.now(UTC).isoformat()
    records: list[dict[str, Any]] = []
    for chunk_index, content in enumerate(chunks, start=1):
        chunk_id = f"{document['id']}_chunk_{chunk_index:03d}"
        metadata = {
            "doc_type": document.get("doc_type", "manual"),
            "product_id": document.get("product_id"),
            "tags": list(document.get("tags", [])),
            "title": document["title"],
        }
        if embeddings is not None and embedding_context is not None:
            metadata.update(
                {
                    key: value
                    for key, value in {
                        **embedding_context,
                        "embedding_created_at": datetime.now(UTC).isoformat(),
                    }.items()
                    if value is not None
                }
            )
        records.append(
            {
                "chunk_index": chunk_index,
                "content": content,
                "document_id": document["id"],
                "embedding": embeddings[chunk_index - 1] if embeddings is not None else None,
                "id": chunk_id,
                "metadata": metadata,
                "permission_roles": permission_roles,
                "permission_scope": {"roles": permission_roles},
                "created_at": now,
                "updated_at": now,
            }
        )
    return records


def knowledge_index_failed_result(
    document: dict[str, Any],
    error: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    updated_document["chunk_count"] = 0
    updated_document["index_error"] = error.strip() or "index_error is required"
    updated_document["index_status"] = "index_failed"
    updated_document["vector_index_error"] = None
    return updated_document, []


def knowledge_text_indexed_result(
    document: dict[str, Any],
    chunks: list[str],
    *,
    vector_error: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    chunk_records = build_knowledge_chunks(updated_document, chunks)
    updated_document["chunk_count"] = len(chunk_records)
    updated_document["index_status"] = "text_indexed"
    updated_document["index_error"] = vector_error
    updated_document["vector_index_error"] = vector_error
    return updated_document, chunk_records


def knowledge_vector_indexed_result(
    document: dict[str, Any],
    chunks: list[str],
    embeddings: list[list[float]],
    embedding_context: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    updated_document = {**document}
    chunk_records = build_knowledge_chunks(
        updated_document,
        chunks,
        embeddings=embeddings,
        embedding_context=embedding_context,
    )
    updated_document["chunk_count"] = len(chunk_records)
    updated_document["index_status"] = "vector_indexed"
    updated_document["index_error"] = None
    updated_document["vector_index_error"] = None
    return updated_document, chunk_records


def replace_knowledge_chunks_result(
    current_store: Any,
    document: dict[str, Any],
    *,
    attempt_vector: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    chunks = split_knowledge_content(document["content"])
    if not chunks:
        return knowledge_index_failed_result(document, "NO_INDEXABLE_CONTENT")
    if not attempt_vector:
        return knowledge_text_indexed_result(document, chunks)
    try:
        embeddings, embedding_context = call_model_gateway_embeddings_with_context(
            current_store,
            chunks,
        )
    except ModelGatewayConfigError as exc:
        return knowledge_text_indexed_result(document, chunks, vector_error=str(exc))
    except ModelGatewayCallError as exc:
        return knowledge_text_indexed_result(
            document,
            chunks,
            vector_error=exc.log.get("error") or "Model gateway embedding request failed",
        )
    return knowledge_vector_indexed_result(document, chunks, embeddings, embedding_context)
