from __future__ import annotations

from time import perf_counter
from typing import Any

from app.core.trace import envelope
from app.services.knowledge_search import knowledge_search_response


def _compact_text(value: str, *, limit: int = 360) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _answer_from_citations(query: str, citations: list[dict[str, Any]]) -> str:
    if not citations:
        return "未检索到可引用的知识依据，暂无法生成可靠答案。"
    evidence_lines = [
        f"{index}. {citation['title']}：{_compact_text(citation['content'], limit=220)}"
        for index, citation in enumerate(citations[:3], start=1)
    ]
    return "\n".join(
        [
            f"围绕“{query}”，可参考以下知识依据：",
            *evidence_lines,
            "建议结合引用来源继续核对上下文后再用于正式决策。",
        ]
    )


def knowledge_rag_response(
    *,
    current_store: Any,
    knowledge_space_id: str | None,
    query_value: str,
    top_k: int,
    trace_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    started_at = perf_counter()
    search_payload = knowledge_search_response(
        current_store=current_store,
        knowledge_space_id=knowledge_space_id,
        query_value=query_value,
        top_k=top_k,
        trace_id=trace_id,
        user=user,
    )
    search_data = search_payload["data"]
    items = search_data.get("items") or []
    citations = [
        {
            "chunk_id": item.get("chunk_id"),
            "chunk_index": item.get("chunk_index"),
            "content": item.get("content") or "",
            "document_id": item.get("document_id"),
            "retrieval_mode": item.get("retrieval_mode"),
            "score": item.get("score"),
            "source": item.get("source") or {},
            "title": item.get("title") or item.get("document_id"),
        }
        for item in items
    ]
    latency_ms = round((perf_counter() - started_at) * 1000, 2)
    has_citations = bool(citations)
    return envelope(
        {
            "answer": _answer_from_citations(query_value.strip(), citations),
            "answer_mode": "extractive_rag",
            "citations": citations,
            "metrics": {
                "citation_count": len(citations),
                "hit_count": len(items),
                "latency_ms": latency_ms,
                "no_result": not has_citations,
                "no_result_rate": 0.0 if has_citations else 1.0,
                "rag_citation_accuracy_proxy": 1.0 if has_citations else 0.0,
                "retrieval": search_data.get("metrics") or {},
            },
        },
        trace_id,
    )
