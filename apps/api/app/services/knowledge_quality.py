from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.api.deps import api_error

KNOWLEDGE_QUALITY_EVENT_TYPES = {"citation_click", "feedback", "rag", "search"}
KNOWLEDGE_FEEDBACK_VALUES = {"incorrect", "not_useful", "outdated", "partial", "useful"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _next_event_id(current_store: Any) -> str:
    repository = getattr(current_store, "repository", None)
    next_id = getattr(repository, "next_id", None)
    if callable(next_id):
        return next_id("knowledge_quality_event")
    new_id = getattr(current_store, "new_id", None)
    if callable(new_id):
        return new_id("knowledge_quality_event")
    return f"knowledge_quality_event_{int(datetime.now(UTC).timestamp() * 1000)}"


def _memory_events(current_store: Any) -> dict[str, dict[str, Any]]:
    events = getattr(current_store, "knowledge_quality_events", None)
    if not isinstance(events, dict):
        return {}
    return events


def _event_payload(
    *,
    citation_chunk_id: str | None = None,
    citation_count: int = 0,
    citation_document_id: str | None = None,
    event_id: str,
    event_type: str,
    feedback_comment: str | None = None,
    feedback_value: str | None = None,
    hit_count: int = 0,
    knowledge_space_id: str | None = None,
    latency_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
    no_result: bool = False,
    query: str | None = None,
    related_event_id: str | None = None,
    retrieval_modes: dict[str, Any] | None = None,
    trace_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    return {
        "citation_chunk_id": citation_chunk_id,
        "citation_count": max(0, citation_count),
        "citation_document_id": citation_document_id,
        "created_at": _now_iso(),
        "event_type": event_type,
        "feedback_comment": feedback_comment,
        "feedback_value": feedback_value,
        "hit_count": max(0, hit_count),
        "id": event_id,
        "knowledge_space_id": knowledge_space_id,
        "latency_ms": latency_ms,
        "metadata": metadata or {},
        "no_result": bool(no_result),
        "query": query,
        "related_event_id": related_event_id,
        "retrieval_modes": retrieval_modes or {},
        "trace_id": trace_id,
        "user_id": user_id,
    }


def record_knowledge_quality_event(
    current_store: Any,
    *,
    citation_chunk_id: str | None = None,
    citation_count: int = 0,
    citation_document_id: str | None = None,
    event_type: str,
    feedback_comment: str | None = None,
    feedback_value: str | None = None,
    hit_count: int = 0,
    knowledge_space_id: str | None = None,
    latency_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
    no_result: bool = False,
    query: str | None = None,
    related_event_id: str | None = None,
    retrieval_modes: dict[str, Any] | None = None,
    trace_id: str | None = None,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_event_type = str(event_type or "").strip()
    if normalized_event_type not in KNOWLEDGE_QUALITY_EVENT_TYPES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported knowledge quality event type")
    if feedback_value is not None and feedback_value not in KNOWLEDGE_FEEDBACK_VALUES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported knowledge feedback value")
    event = _event_payload(
        citation_chunk_id=citation_chunk_id,
        citation_count=citation_count,
        citation_document_id=citation_document_id,
        event_id=_next_event_id(current_store),
        event_type=normalized_event_type,
        feedback_comment=feedback_comment.strip()[:500] if feedback_comment else None,
        feedback_value=feedback_value,
        hit_count=hit_count,
        knowledge_space_id=knowledge_space_id,
        latency_ms=_safe_float(latency_ms),
        metadata=metadata,
        no_result=no_result,
        query=query.strip()[:500] if query else None,
        related_event_id=related_event_id,
        retrieval_modes=retrieval_modes,
        trace_id=trace_id,
        user_id=str((user or {}).get("id") or "") or None,
    )
    repository = getattr(current_store, "repository", None)
    insert_event = getattr(repository, "insert_knowledge_quality_event", None)
    if callable(insert_event):
        return insert_event(event)
    _memory_events(current_store)[event["id"]] = dict(event)
    return dict(event)


def record_knowledge_quality_event_best_effort(
    current_store: Any,
    **kwargs: Any,
) -> dict[str, Any] | None:
    try:
        return record_knowledge_quality_event(current_store, **kwargs)
    except Exception:
        return None


def list_knowledge_quality_events(
    current_store: Any,
    *,
    event_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    normalized_limit = max(1, min(int(limit or 100), 500))
    repository = getattr(current_store, "repository", None)
    list_events = getattr(repository, "list_knowledge_quality_events", None)
    if callable(list_events):
        return list_events(event_type=event_type, limit=normalized_limit)
    events = [
        dict(event)
        for event in _memory_events(current_store).values()
        if event_type is None or event.get("event_type") == event_type
    ]
    events.sort(
        key=lambda event: (event.get("created_at") or "", event.get("id") or ""), reverse=True
    )
    return events[:normalized_limit]


def knowledge_quality_summary(current_store: Any, *, since_days: int = 30) -> dict[str, Any]:
    repository = getattr(current_store, "repository", None)
    summary = getattr(repository, "knowledge_quality_summary", None)
    if callable(summary):
        return summary(since_days=since_days)
    since_at = datetime.now(UTC) - timedelta(days=max(1, since_days))
    query_events = []
    feedback_events = []
    citation_click_count = 0
    citation_count = 0
    latencies: list[float] = []
    for event in _memory_events(current_store).values():
        created_at = _parse_datetime(event.get("created_at"))
        if created_at and created_at < since_at:
            continue
        event_type = event.get("event_type")
        if event_type in {"search", "rag"}:
            query_events.append(event)
            citation_count += _safe_int(event.get("citation_count"))
            latency_ms = _safe_float(event.get("latency_ms"))
            if latency_ms is not None:
                latencies.append(latency_ms)
        elif event_type == "feedback":
            feedback_events.append(event)
        elif event_type == "citation_click":
            citation_click_count += 1
    no_result_count = sum(1 for event in query_events if event.get("no_result"))
    useful_feedback_count = sum(
        1 for event in feedback_events if event.get("feedback_value") == "useful"
    )
    negative_feedback_count = sum(
        1 for event in feedback_events if event.get("feedback_value") in {"incorrect", "not_useful"}
    )
    return {
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "citation_click_count": citation_click_count,
        "citation_click_rate": round(citation_click_count / citation_count, 4)
        if citation_count
        else None,
        "citation_count": citation_count,
        "feedback_count": len(feedback_events),
        "negative_feedback_count": negative_feedback_count,
        "no_result_count": no_result_count,
        "no_result_rate": round(no_result_count / len(query_events), 4) if query_events else None,
        "query_count": len(query_events),
        "rag_citation_accuracy_proxy": round(useful_feedback_count / len(feedback_events), 4)
        if feedback_events
        else None,
        "since_days": since_days,
        "useful_feedback_count": useful_feedback_count,
    }


def knowledge_quality_metrics_response(
    current_store: Any,
    *,
    event_type: str | None,
    limit: int,
    since_days: int,
    trace_id: str,
) -> dict[str, Any]:
    from app.core.trace import envelope

    if event_type is not None and event_type not in KNOWLEDGE_QUALITY_EVENT_TYPES:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported knowledge quality event type")
    return envelope(
        {
            "events": list_knowledge_quality_events(
                current_store,
                event_type=event_type,
                limit=limit,
            ),
            "summary": knowledge_quality_summary(current_store, since_days=since_days),
        },
        trace_id,
    )


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
