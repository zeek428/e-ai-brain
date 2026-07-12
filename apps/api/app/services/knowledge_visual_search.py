from __future__ import annotations

from math import sqrt
from typing import Any

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
    allowed_products = product_scope_filter(user)
    items = []
    for record in read_memory_dict(current_store, "knowledge_visual_embeddings").values():
        if allowed_products is not None and str(record.get("product_id")) not in set(
            allowed_products
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
