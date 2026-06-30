from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from full_chain_regression_slug import regression_slug


@dataclass
class StepResult:
    name: str
    detail: str


def _slug() -> str:
    return regression_slug()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("id")) for item in items if item.get("id")}


def _assert_contains(values: set[str], expected: str, message: str) -> None:
    _assert(expected in values, f"{message}: expected {expected}, got {sorted(values)}")


def validate_knowledge_index_health_quick_regression(
    client: Any,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    marker = f"knowledge-health-{slug}"
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    document = client.post(
        "/api/knowledge/documents",
        {
            "content": (
                f"{marker}\n\n"
                "知识索引健康快速回归文档，用于验证文档创建、分块、权限命中、"
                "检索模式和搜索结果能够通过公开 API 闭环。"
            ),
            "doc_type": "runbook",
            "permission_roles": ["admin", "knowledge_owner", "rd_owner"],
            "tags": ["full-chain", "knowledge-index-health"],
            "title": f"知识索引健康快速回归 {slug}",
        },
    )
    document_id = str(document.get("id") or "")
    _assert(document_id, f"Knowledge document creation did not return id: {document}")
    _assert(
        document.get("index_status") in {"indexed", "text_indexed", "vector_indexed"},
        f"Knowledge document was not searchable after creation: {document}",
    )
    _assert(
        int(document.get("chunk_count") or 0) >= 1,
        f"Knowledge document creation did not create chunks: {document}",
    )
    results.append(
        StepResult(
            "knowledge_document",
            f"{document_id} / status={document.get('index_status')}",
        )
    )

    documents = client.get(
        "/api/knowledge/documents",
        {
            "keyword": marker,
            "page": 1,
            "page_size": 10,
            "permission_role": "admin",
            "sort_by": "created_at",
            "sort_order": "desc",
        },
    )
    document_items = documents.get("items", [])
    _assert_contains(_ids(document_items), document_id, "Knowledge document list missed created document")
    listed_document = next(item for item in document_items if str(item.get("id")) == document_id)
    _assert(
        int(listed_document.get("chunk_count") or 0) >= 1,
        f"Knowledge document list missed chunk count: {listed_document}",
    )
    _assert(
        "admin" in set(listed_document.get("permission_roles") or []),
        f"Knowledge document list missed permission role projection: {listed_document}",
    )

    knowledge_health = client.get(
        "/api/knowledge/index-health",
        {"issue_limit": 20, "keyword": marker, "permission_role": "admin"},
    )
    knowledge_health_summary = knowledge_health.get("summary") or {}
    _assert(
        int(knowledge_health_summary.get("total_documents") or 0) >= 1,
        f"Knowledge index health missed created document: {knowledge_health}",
    )
    _assert(
        int(knowledge_health_summary.get("searchable_documents") or 0) >= 1,
        f"Knowledge index health did not mark document searchable: {knowledge_health_summary}",
    )
    _assert(
        int(knowledge_health_summary.get("chunk_ready_documents") or 0) >= 1,
        f"Knowledge index health missed chunk-ready document: {knowledge_health_summary}",
    )
    _assert(
        int(knowledge_health_summary.get("total_chunks") or 0) >= 1,
        f"Knowledge index health missed chunks: {knowledge_health_summary}",
    )
    retrieval_modes = knowledge_health.get("retrieval_modes") or {}
    _assert(
        int(retrieval_modes.get("hybrid_ready") or 0) + int(retrieval_modes.get("keyword_fallback") or 0) >= 1,
        f"Knowledge index health did not expose usable retrieval mode: {retrieval_modes}",
    )
    _assert(
        int(retrieval_modes.get("unavailable") or 0) == 0,
        f"Knowledge index health marked the new searchable document unavailable: {retrieval_modes}",
    )
    permission_scope = knowledge_health.get("permission_scope") or {}
    _assert(
        permission_scope.get("mode") == "role_based",
        f"Knowledge index health missed role-based permission scope: {permission_scope}",
    )
    _assert(
        "admin" in set(permission_scope.get("matched_roles") or []),
        f"Knowledge index health missed admin role match: {permission_scope}",
    )
    _assert(
        permission_scope.get("scope_labels"),
        f"Knowledge index health missed readable permission scope labels: {permission_scope}",
    )
    document_health_issues = [
        issue for issue in knowledge_health.get("items", []) if str(issue.get("document_id")) == document_id
    ]
    if document.get("index_status") == "text_indexed":
        _assert(
            any(
                issue.get("action") == "retry_index"
                and issue.get("severity") == "warning"
                and issue.get("status") == "text_indexed"
                for issue in document_health_issues
            ),
            f"Knowledge index health missed vector-backfill warning for text-indexed document: {document_health_issues}",
        )
    else:
        _assert(
            not document_health_issues,
            f"Knowledge index health reported an issue for a vector-ready document: {document_health_issues}",
        )

    knowledge_search = client.post("/api/knowledge/search", {"query": marker, "top_k": 5})
    search_items = knowledge_search.get("items", [])
    search_document_ids = {str(item.get("document_id")) for item in search_items}
    _assert_contains(
        search_document_ids,
        document_id,
        "Knowledge search did not retrieve created document",
    )
    _assert(
        any(item.get("retrieval_mode") in {"keyword", "vector"} for item in search_items),
        f"Knowledge search did not return retrieval mode: {search_items}",
    )

    failed_document = client.request(
        "PATCH",
        f"/api/knowledge/documents/{document_id}",
        body={
            "index_error": "full-chain regression forced index failure",
            "index_status": "index_failed",
        },
    )
    _assert(
        failed_document.get("index_status") == "index_failed",
        f"Knowledge document was not marked index_failed: {failed_document}",
    )
    _assert(
        int(failed_document.get("chunk_count") or 0) == 0,
        f"Knowledge index_failed document should not keep active chunks: {failed_document}",
    )
    failed_health = client.get(
        "/api/knowledge/index-health",
        {
            "index_status": "index_failed",
            "issue_limit": 20,
            "keyword": marker,
            "permission_role": "admin",
        },
    )
    failed_summary = failed_health.get("summary") or {}
    _assert(
        int(failed_summary.get("index_failed_documents") or 0) >= 1,
        f"Knowledge index health missed failed document count: {failed_health}",
    )
    failed_issues = [
        issue for issue in failed_health.get("items", []) if str(issue.get("document_id")) == document_id
    ]
    _assert(
        any(
            issue.get("action") == "retry_index"
            and issue.get("severity") == "error"
            and issue.get("status") == "index_failed"
            for issue in failed_issues
        ),
        f"Knowledge index health missed retry issue for failed document: {failed_issues}",
    )
    failed_search = client.post("/api/knowledge/search", {"query": marker, "top_k": 5})
    failed_search_ids = {str(item.get("document_id")) for item in failed_search.get("items", [])}
    _assert(
        document_id not in failed_search_ids,
        f"Knowledge search returned index_failed document before retry: {failed_search}",
    )

    retried_document = client.post(f"/api/knowledge/documents/{document_id}/retry-index")
    _assert(
        retried_document.get("index_status") in {"indexed", "text_indexed", "vector_indexed"},
        f"Knowledge retry did not restore a searchable status: {retried_document}",
    )
    _assert(
        int(retried_document.get("chunk_count") or 0) >= 1,
        f"Knowledge retry did not rebuild chunks: {retried_document}",
    )
    retried_search = client.post("/api/knowledge/search", {"query": marker, "top_k": 5})
    retried_search_items = retried_search.get("items", [])
    _assert_contains(
        {str(item.get("document_id")) for item in retried_search_items},
        document_id,
        "Knowledge search did not retrieve document after retry-index",
    )
    results.append(
        StepResult(
            "knowledge_index_health_quick",
            (
                f"{document_id} / chunks={knowledge_health_summary.get('total_chunks')} / "
                f"mode={permission_scope.get('mode')}"
            ),
        )
    )
    results.append(
        StepResult(
            "knowledge_search",
            f"hits={len(search_items)} / retried_hits={len(retried_search_items)} / document={document_id}",
        )
    )
    return results
