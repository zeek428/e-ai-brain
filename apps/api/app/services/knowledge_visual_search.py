from __future__ import annotations

from math import sqrt
from typing import Any

from app.services.knowledge_documents import (
    knowledge_memory_records,
    knowledge_repository_access_args,
)
from app.services.knowledge_management import document_is_readable
from app.services.operational_records import read_memory_dict
from app.services.product_scope import product_scope_filter


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return -1.0
    denominator = sqrt(sum(item * item for item in left)) * sqrt(sum(item * item for item in right))
    return (
        sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else -1.0
    )


def visual_search_response(
    *,
    current_store: Any,
    query_embedding: list[float],
    user: dict[str, Any],
) -> dict[str, Any]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_trusted_delivery_records", None)
    records = (
        list_records(record_type="knowledge_visual_embedding")
        if callable(list_records)
        else read_memory_dict(current_store, "knowledge_visual_embeddings").values()
    )
    list_documents = getattr(repository, "list_knowledge_documents", None)
    repository_filtered_documents = callable(list_documents)
    document_records = (
        list(list_documents(**knowledge_repository_access_args(user)))
        if callable(list_documents)
        else [
            document
            for document in knowledge_memory_records(current_store, "knowledge_documents")
            if document_is_readable(current_store, user, document)
        ]
    )
    documents = {str(document["id"]): document for document in document_records}
    product_scope_ids = product_scope_filter(user)
    items = []
    for record in records:
        document = documents.get(str(record.get("document_id") or ""))
        if document is None or (
            not repository_filtered_documents
            and not document_is_readable(current_store, user, document)
        ):
            continue
        if product_scope_ids is not None and str(document.get("product_id") or "") not in set(
            product_scope_ids
        ):
            continue
        embedding = record.get("embedding")
        if not isinstance(embedding, list):
            continue
        score = _cosine(query_embedding, embedding)
        if score < 0:
            continue
        items.append(
            {
                "asset_id": record.get("asset_id"),
                "bounding_box": record.get("bounding_box"),
                "document_id": record.get("document_id"),
                "page_number": record.get("page_number"),
                "score": round(score, 6),
            }
        )
    return {"items": sorted(items, key=lambda item: item["score"], reverse=True)}


def save_knowledge_visual_embedding(current_store: Any, record: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_trusted_delivery_record", None)
    if callable(save_record):
        save_record(record=record, record_type="knowledge_visual_embedding")
    read_memory_dict(current_store, "knowledge_visual_embeddings")[record["id"]] = dict(record)
