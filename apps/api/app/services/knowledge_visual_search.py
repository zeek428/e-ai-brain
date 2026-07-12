from __future__ import annotations

from math import sqrt
from typing import Any

from app.api.deps import api_error
from app.services.knowledge_documents import (
    knowledge_memory_records,
    knowledge_repository_access_args,
)
from app.services.knowledge_management import document_is_readable
from app.services.knowledge_multimodal import resolve_knowledge_processing_provider
from app.services.knowledge_multimodal_governance import get_processing_profile
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
        active_version_id = str(document.get("active_document_version_id") or "")
        record_version_id = str(record.get("document_version_id") or "")
        if active_version_id and record_version_id and active_version_id != record_version_id:
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


def _image_query_embedding(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
    profile: dict[str, Any],
) -> list[float]:
    if not mime_type.startswith("image/"):
        raise api_error(400, "VALIDATION_ERROR", "Visual search only accepts image files")
    if "image_embedding" not in set(profile.get("capabilities") or []):
        raise api_error(
            409,
            "KNOWLEDGE_IMAGE_EMBEDDING_UNAVAILABLE",
            "Processing profile does not support image embedding",
        )
    provider = resolve_knowledge_processing_provider(profile)
    result = provider.process(
        content=content,
        filename=filename,
        mime_type=mime_type,
        profile=profile,
    )
    embedding = result.get("embedding") or result.get("query_embedding")
    if not isinstance(embedding, list) or not embedding or len(embedding) > 4096:
        raise api_error(
            502,
            "KNOWLEDGE_IMAGE_EMBEDDING_INVALID",
            "Image embedding provider returned an invalid embedding",
        )
    try:
        return [float(value) for value in embedding]
    except (TypeError, ValueError) as exc:
        raise api_error(
            502,
            "KNOWLEDGE_IMAGE_EMBEDDING_INVALID",
            "Image embedding provider returned an invalid embedding",
        ) from exc


def visual_search_with_image_response(
    *,
    content: bytes,
    current_store: Any,
    filename: str,
    mime_type: str,
    processing_profile_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    if not content:
        raise api_error(400, "VALIDATION_ERROR", "Image file is empty")
    if len(content) > 10 * 1024 * 1024:
        raise api_error(413, "PAYLOAD_TOO_LARGE", "Image file exceeds 10 MB")
    profile = get_processing_profile(current_store, processing_profile_id, user=user)
    if profile is None:
        raise api_error(404, "NOT_FOUND", "Knowledge processing profile not found")
    query_embedding = _image_query_embedding(
        content=content,
        filename=filename,
        mime_type=mime_type,
        profile=profile,
    )
    return {
        **visual_search_response(
            current_store=current_store,
            query_embedding=query_embedding,
            user=user,
        ),
        "query_profile_id": profile["id"],
    }


def save_knowledge_visual_embedding(current_store: Any, record: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_trusted_delivery_record", None)
    if callable(save_record):
        save_record(record=record, record_type="knowledge_visual_embedding")
    read_memory_dict(current_store, "knowledge_visual_embeddings")[record["id"]] = dict(record)
