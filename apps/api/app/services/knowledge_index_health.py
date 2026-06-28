from __future__ import annotations

from typing import Any

from fastapi import Request

from app.api.deps import require_permissions
from app.core.listing import add_list_observability
from app.core.trace import envelope, get_trace_id
from app.services.knowledge_documents import (
    ensure_knowledge_index_status,
    knowledge_query_repository,
    knowledge_repository_access_args,
    memory_knowledge_document_items,
    request_started_at,
)

SEARCHABLE_INDEX_STATUSES = {"indexed", "text_indexed", "vector_indexed"}
PROCESSING_INDEX_STATUSES = {"importing", "pending_index"}


def _count_by_status(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or item.get("index_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return [{"count": count, "status": status} for status, count in sorted(counts.items())]


def _issue_from_document(document: dict[str, Any], *, chunk_count: int) -> dict[str, Any] | None:
    status = str(document.get("index_status") or "pending_index")
    if status == "index_failed":
        return {
            "action": "retry_index",
            "chunk_count": chunk_count,
            "description": document.get("index_error")
            or document.get("vector_index_error")
            or "索引失败，需重试或检查模型网关。",
            "document_id": document["id"],
            "index_error": document.get("index_error"),
            "knowledge_space_id": document.get("knowledge_space_id"),
            "label": "索引失败",
            "severity": "error",
            "status": status,
            "title": document.get("title") or document["id"],
            "updated_at": document.get("updated_at"),
            "vector_index_error": document.get("vector_index_error"),
        }
    if status == "text_indexed":
        return {
            "action": "retry_index",
            "chunk_count": chunk_count,
            "description": (
                document.get("vector_index_error") or "当前仅支持关键词检索，向量索引可补建。"
            ),
            "document_id": document["id"],
            "index_error": document.get("index_error"),
            "knowledge_space_id": document.get("knowledge_space_id"),
            "label": "向量待补",
            "severity": "warning",
            "status": status,
            "title": document.get("title") or document["id"],
            "updated_at": document.get("updated_at"),
            "vector_index_error": document.get("vector_index_error"),
        }
    if status in PROCESSING_INDEX_STATUSES:
        return {
            "action": "open_import_jobs",
            "chunk_count": chunk_count,
            "description": "导入或索引任务仍在排队/处理中。",
            "document_id": document["id"],
            "index_error": document.get("index_error"),
            "knowledge_space_id": document.get("knowledge_space_id"),
            "label": "处理中",
            "severity": "processing",
            "status": status,
            "title": document.get("title") or document["id"],
            "updated_at": document.get("updated_at"),
            "vector_index_error": document.get("vector_index_error"),
        }
    if status in SEARCHABLE_INDEX_STATUSES and chunk_count == 0:
        return {
            "action": "open_chunks",
            "chunk_count": chunk_count,
            "description": "文档处于可检索状态，但没有可用分块。",
            "document_id": document["id"],
            "index_error": document.get("index_error"),
            "knowledge_space_id": document.get("knowledge_space_id"),
            "label": "分块缺失",
            "severity": "warning",
            "status": status,
            "title": document.get("title") or document["id"],
            "updated_at": document.get("updated_at"),
            "vector_index_error": document.get("vector_index_error"),
        }
    return None


def _decorate_repository_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decorated: list[dict[str, Any]] = []
    for issue in issues:
        decorated_issue = _issue_from_document(
            {
                "id": issue["document_id"],
                "index_error": issue.get("index_error"),
                "index_status": issue.get("status"),
                "knowledge_space_id": issue.get("knowledge_space_id"),
                "title": issue.get("title") or issue["document_id"],
                "updated_at": issue.get("updated_at"),
                "vector_index_error": issue.get("vector_index_error"),
            },
            chunk_count=int(issue.get("chunk_count") or 0),
        )
        if decorated_issue is not None:
            decorated.append(decorated_issue)
    return decorated


def _memory_chunk_counts(
    current_store: Any,
    document_id: str,
    active_chunk_set_id: str | None,
) -> dict[str, int]:
    total_chunks = 0
    embedding_chunks = 0
    keyword_chunks = 0
    for chunk in getattr(current_store, "knowledge_chunks", {}).values():
        if chunk.get("document_id") != document_id:
            continue
        if active_chunk_set_id and chunk.get("chunk_set_id") != active_chunk_set_id:
            continue
        total_chunks += 1
        if chunk.get("embedding") is not None:
            embedding_chunks += 1
        else:
            keyword_chunks += 1
    return {
        "embedding_chunks": embedding_chunks,
        "keyword_chunks": keyword_chunks,
        "total_chunks": total_chunks,
    }


def _memory_embedding_models(
    current_store: Any,
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    active_chunk_set_ids = {
        document.get("active_chunk_set_id")
        for document in documents
        if document.get("active_chunk_set_id")
    }
    counts: dict[tuple[str, int | None], int] = {}
    for chunk_set in getattr(current_store, "knowledge_chunk_sets", {}).values():
        if chunk_set.get("id") not in active_chunk_set_ids:
            continue
        key = (
            str(chunk_set.get("embedding_model") or "not_configured"),
            chunk_set.get("embedding_dimension"),
        )
        counts[key] = counts.get(key, 0) + 1
    return [
        {"count": count, "dimension": dimension, "model": model}
        for (model, dimension), count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0][0]),
        )
    ]


def _memory_import_jobs(
    current_store: Any,
    documents_by_id: dict[str, dict[str, Any]],
    *,
    knowledge_space_id: str | None,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for job in getattr(current_store, "knowledge_import_jobs", {}).values():
        document = documents_by_id.get(str(job.get("document_id") or ""))
        if document is None:
            continue
        if (
            knowledge_space_id is not None
            and document.get("knowledge_space_id") != knowledge_space_id
        ):
            continue
        jobs.append(job)
    return jobs


def _memory_index_health(
    *,
    current_store: Any,
    doc_type: str | None,
    folder_id: str | None,
    index_status: str | None,
    issue_limit: int,
    keyword: str | None,
    knowledge_space_id: str | None,
    permission_role: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    documents = memory_knowledge_document_items(
        current_store=current_store,
        doc_type=doc_type,
        folder_id=folder_id,
        index_status=index_status,
        knowledge_space_id=knowledge_space_id,
        keyword=keyword,
        user=user,
    )
    if permission_role:
        documents = [
            document
            for document in documents
            if permission_role in set(document.get("permission_roles") or [])
        ]
    documents_by_id = {document["id"]: document for document in documents}
    chunk_counts_by_document = {
        document["id"]: _memory_chunk_counts(
            current_store,
            document["id"],
            document.get("active_chunk_set_id"),
        )
        for document in documents
    }
    status_counts = _count_by_status(
        [{"status": document.get("index_status")} for document in documents]
    )
    import_jobs = _memory_import_jobs(
        current_store,
        documents_by_id,
        knowledge_space_id=knowledge_space_id,
    )
    issues = [
        issue
        for document in documents
        if (
            issue := _issue_from_document(
                document,
                chunk_count=chunk_counts_by_document[document["id"]]["total_chunks"],
            )
        )
        is not None
    ]
    severity_order = {"error": 0, "warning": 1, "processing": 2}
    issues.sort(
        key=lambda issue: (
            severity_order.get(str(issue.get("severity")), 9),
            str(issue.get("updated_at") or ""),
            str(issue.get("document_id") or ""),
        )
    )
    total_chunks = sum(item["total_chunks"] for item in chunk_counts_by_document.values())
    embedding_ready_chunks = sum(
        item["embedding_chunks"] for item in chunk_counts_by_document.values()
    )
    return {
        "embedding_models": _memory_embedding_models(current_store, documents),
        "import_job_counts": _count_by_status(
            [{"status": job.get("status")} for job in import_jobs]
        ),
        "issues": issues[:issue_limit],
        "status_counts": status_counts,
        "summary": {
            "chunk_ready_documents": sum(
                1 for item in chunk_counts_by_document.values() if item["total_chunks"] > 0
            ),
            "embedding_ready_chunks": embedding_ready_chunks,
            "index_failed_documents": sum(
                1 for document in documents if document.get("index_status") == "index_failed"
            ),
            "keyword_only_chunks": total_chunks - embedding_ready_chunks,
            "keyword_only_documents": sum(
                1 for document in documents if document.get("index_status") == "text_indexed"
            ),
            "missing_chunk_documents": sum(
                1
                for document in documents
                if document.get("index_status") in SEARCHABLE_INDEX_STATUSES
                and chunk_counts_by_document[document["id"]]["total_chunks"] == 0
            ),
            "processing_documents": sum(
                1
                for document in documents
                if document.get("index_status") in PROCESSING_INDEX_STATUSES
            ),
            "searchable_documents": sum(
                1
                for document in documents
                if document.get("index_status") in SEARCHABLE_INDEX_STATUSES
            ),
            "total_chunks": total_chunks,
            "total_documents": len(documents),
            "vector_ready_documents": sum(
                1
                for document in documents
                if document.get("index_status") in {"indexed", "vector_indexed"}
            ),
        },
    }


def knowledge_index_health_response(
    *,
    current_store: Any,
    doc_type: str | None,
    folder_id: str | None,
    index_status: str | None,
    issue_limit: int,
    keyword: str | None,
    knowledge_space_id: str | None,
    permission_role: str | None,
    request: Request,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_permissions(user, {"knowledge.read"})
    ensure_knowledge_index_status(index_status)
    repository = knowledge_query_repository(current_store)
    filters = {
        "doc_type": doc_type,
        "folder_id": folder_id,
        "index_status": index_status,
        "keyword": keyword,
        "knowledge_space_id": knowledge_space_id,
        "permission_role": permission_role,
    }
    if repository is not None and callable(getattr(repository, "knowledge_index_health", None)):
        health = repository.knowledge_index_health(
            **knowledge_repository_access_args(user),
            doc_type=doc_type,
            folder_id=folder_id,
            index_status=index_status,
            issue_limit=issue_limit,
            keyword=keyword,
            knowledge_space_id=knowledge_space_id,
            permission_role=permission_role,
        )
        health["issues"] = _decorate_repository_issues(health.get("issues") or [])
    else:
        health = _memory_index_health(
            current_store=current_store,
            doc_type=doc_type,
            folder_id=folder_id,
            index_status=index_status,
            issue_limit=issue_limit,
            keyword=keyword,
            knowledge_space_id=knowledge_space_id,
            permission_role=permission_role,
            user=user,
        )
    health["retrieval_modes"] = {
        "hybrid_ready": int(health["summary"].get("vector_ready_documents") or 0),
        "keyword_fallback": int(health["summary"].get("keyword_only_documents") or 0),
        "unavailable": int(health["summary"].get("missing_chunk_documents") or 0)
        + int(health["summary"].get("index_failed_documents") or 0),
    }
    health["items"] = list(health.get("issues") or [])
    health["total"] = int(health["summary"].get("total_documents") or 0)
    return envelope(
        add_list_observability(
            health,
            filters=filters,
            list_name="knowledge_index_health",
            started_at=request_started_at(request),
        ),
        get_trace_id(request),
    )
