import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main
import app.services.model_gateway as model_gateway_service
from app.main import app
from app.services.knowledge_deposits import knowledge_deposit_list_response

client = TestClient(app)


class FakeKnowledgeDepositPagingRepository:
    def __init__(self) -> None:
        self.count_kwargs: dict | None = None
        self.page_kwargs: dict | None = None

    def list_knowledge_deposits(self, **_kwargs):
        raise AssertionError("knowledge deposit list should use count/page read model")

    def count_knowledge_deposits(self, **kwargs):
        self.count_kwargs = kwargs
        return 3

    def list_knowledge_deposits_page(self, **kwargs):
        self.page_kwargs = kwargs
        return [
            {
                "ai_task_id": "task_sql",
                "content": "候选知识内容",
                "content_hash": "hash_sql",
                "created_at": "2026-06-28T01:00:00+00:00",
                "deposit_type": "task_output",
                "id": "deposit_sql",
                "knowledge_document_id": None,
                "rejection_reason": None,
                "status": "pending",
                "title": "候选知识",
                "updated_at": "2026-06-28T02:00:00+00:00",
            }
        ]


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_completed_design_task(headers: dict[str, str]) -> str:
    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1 MVP"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "知识治理闭环",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "任务产出需要成为知识沉淀候选，并支持模拟 Issue 幂等生成。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task_response = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    )
    task = task_response.json()["data"]
    started = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers).json()["data"]
    client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    return task["task_id"]


def test_knowledge_deposit_list_uses_repository_pagination_when_requested():
    repository = FakeKnowledgeDepositPagingRepository()

    response = knowledge_deposit_list_response(
        current_store=SimpleNamespace(repository=repository),
        page=2,
        page_size=1,
        sort_by="updated_at",
        sort_order="desc",
        started_at=None,
        status="pending",
        trace_id="trace_knowledge_deposit_page",
    )

    payload = response["data"]
    assert payload["items"][0]["id"] == "deposit_sql"
    assert payload["page"] == 2
    assert payload["page_size"] == 1
    assert payload["total"] == 3
    assert payload["query"]["name"] == "knowledge_deposits"
    assert payload["query"]["filters"] == {"status": "pending"}
    assert payload["performance"]["p95_target_ms"] == 500
    assert repository.count_kwargs == {"status": "pending"}
    assert repository.page_kwargs == {
        "limit": 1,
        "offset": 1,
        "sort_by": "updated_at",
        "sort_order": "desc",
        "status": "pending",
    }


def test_knowledge_search_filters_permissions_and_deposits_are_reviewable():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    admin_doc = client.post(
        "/api/knowledge/documents",
        json={
            "title": "管理员策略",
            "content": "admin-only launch policy",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    ).json()["data"]
    reviewer_doc = client.post(
        "/api/knowledge/documents",
        json={
            "title": "Review 指南",
            "content": "reviewer code review checklist",
            "permission_roles": ["reviewer"],
        },
        headers=admin_headers,
    ).json()["data"]

    results = client.post(
        "/api/knowledge/search",
        json={"query": "review", "top_k": 5},
        headers=reviewer_headers,
    ).json()["data"]["items"]
    assert [item["document_id"] for item in results] == [reviewer_doc["id"]]
    assert admin_doc["id"] not in [item["document_id"] for item in results]

    task_id = create_completed_design_task(admin_headers)
    space = client.post(
        "/api/knowledge/spaces",
        json={"code": "governance", "name": "治理知识空间"},
        headers=admin_headers,
    ).json()["data"]
    deposits = client.get("/api/knowledge/deposits?status=pending", headers=admin_headers).json()[
        "data"
    ]["items"]
    assert deposits[0]["ai_task_id"] == task_id
    assert deposits[0]["status"] == "pending"

    paged_deposits = client.get(
        "/api/knowledge/deposits"
        "?status=pending&page=1&page_size=1&sort_by=created_at&sort_order=desc",
        headers=admin_headers,
    ).json()["data"]
    assert paged_deposits["page"] == 1
    assert paged_deposits["page_size"] == 1
    assert paged_deposits["query"]["name"] == "knowledge_deposits"
    assert paged_deposits["performance"]["p95_target_ms"] == 500

    approved = client.post(
        f"/api/knowledge/deposits/{deposits[0]['id']}/approve",
        json={"knowledge_space_id": space["id"], "title": "知识治理闭环沉淀"},
        headers=admin_headers,
    ).json()["data"]
    assert approved["status"] == "approved"
    assert approved["knowledge_document_id"].startswith("knowledge_")


def test_knowledge_search_returns_permission_filtered_chunks_and_reindexes_on_update():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    viewer_username = "chunk-viewer@example.com"
    client.post(
        "/api/users",
        json={
            "display_name": "Chunk Viewer",
            "password": "viewer123",
            "roles": ["viewer"],
            "status": "active",
            "username": viewer_username,
        },
        headers=admin_headers,
    )
    viewer_headers = auth_headers(viewer_username, "viewer123")

    document = client.post(
        "/api/knowledge/documents",
        json={
            "title": "Review 分层指南",
            "content": (
                "第一段说明普通研发流程。\n\n"
                "第二段包含 reviewer-only chunk retrieval marker，必须作为单独来源返回。\n\n"
                "第三段说明发布检查。"
            ),
            "permission_roles": ["reviewer"],
            "tags": ["chunk"],
        },
        headers=admin_headers,
    ).json()["data"]

    results = client.post(
        "/api/knowledge/search",
        json={"query": "retrieval marker", "top_k": 5},
        headers=reviewer_headers,
    ).json()["data"]["items"]

    assert len(results) == 1
    assert results[0]["document_id"] == document["id"]
    assert results[0]["chunk_id"] == f"{document['id']}_chunk_002"
    assert results[0]["chunk_index"] == 2
    assert results[0]["content"] == (
        "第二段包含 reviewer-only chunk retrieval marker，必须作为单独来源返回。"
    )
    assert results[0]["source"]["chunk_id"] == f"{document['id']}_chunk_002"
    assert "第一段说明普通研发流程" not in results[0]["content"]

    forbidden = client.post(
        "/api/knowledge/search",
        json={"query": "retrieval marker", "top_k": 5},
        headers=viewer_headers,
    ).json()["data"]["items"]
    assert forbidden == []

    updated = client.patch(
        f"/api/knowledge/documents/{document['id']}",
        json={"content": "更新后的 chunk 只包含 new-search-token。"},
        headers=admin_headers,
    ).json()["data"]
    assert updated["chunk_count"] == 1

    stale_results = client.post(
        "/api/knowledge/search",
        json={"query": "retrieval marker", "top_k": 5},
        headers=reviewer_headers,
    ).json()["data"]["items"]
    fresh_results = client.post(
        "/api/knowledge/search",
        json={"query": "new-search-token", "top_k": 5},
        headers=reviewer_headers,
    ).json()["data"]["items"]

    assert stale_results == []
    assert [item["chunk_id"] for item in fresh_results] == [f"{document['id']}_chunk_001"]


def test_knowledge_search_uses_model_gateway_embeddings_for_semantic_rank(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    embedding_size = 1536

    class FakeResponse:
        def __init__(self, payload: dict):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def vector_for(text: str) -> list[float]:
        if "semantic-target" in text or "deployment intent" in text:
            return [1.0, *([0.0] * (embedding_size - 1))]
        if "payroll" in text:
            return [0.0, 1.0, *([0.0] * (embedding_size - 2))]
        return [0.5, 0.5, *([0.0] * (embedding_size - 2))]

    embedding_calls: list[dict[str, object]] = []

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://llm.test/v1/embeddings"
        payload = json.loads(request.data.decode("utf-8"))
        embedding_calls.append({"payload": payload, "timeout": timeout})
        inputs = payload["input"]
        if isinstance(inputs, str):
            inputs = [inputs]
        return FakeResponse(
            {
                "data": [
                    {"embedding": vector_for(text), "index": index}
                    for index, text in enumerate(inputs)
                ],
                "usage": {"prompt_tokens": 7 * len(inputs), "total_tokens": 7 * len(inputs)},
            }
        )

    monkeypatch.setattr(main, "urlopen", fake_urlopen)
    monkeypatch.setattr(model_gateway_service, "urlopen", fake_urlopen)

    target = client.post(
        "/api/knowledge/documents",
        json={
            "title": "部署语义手册",
            "content": "semantic-target release checklist",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    ).json()["data"]
    client.post(
        "/api/knowledge/documents",
        json={
            "title": "薪资制度",
            "content": "payroll reimbursement policy",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    )

    results = client.post(
        "/api/knowledge/search",
        json={"query": "deployment intent", "top_k": 1},
        headers=admin_headers,
    ).json()["data"]["items"]

    assert [item["document_id"] for item in results] == [target["id"]]
    assert results[0]["score"] == 1.0
    stored_embeddings = [
        chunk["embedding"]
        for chunk in app.state.store.knowledge_chunks.values()
        if chunk["document_id"] == target["id"]
    ]
    assert len(stored_embeddings) == 1
    assert len(stored_embeddings[0]) == embedding_size
    assert embedding_calls[0]["payload"]["model"] == "test-embedding-model"
    assert embedding_calls[-1]["payload"]["input"] == ["deployment intent"]

    logs = client.get(
        "/api/model-gateway/logs?status=succeeded",
        headers=admin_headers,
    ).json()["data"]["items"]
    embedding_logs = [log for log in logs if log["purpose"] == "knowledge_embedding"]
    assert embedding_logs
    assert all(log["model"] == "test-embedding-model" for log in embedding_logs)
    assert "semantic-target" not in str(embedding_logs)


def test_knowledge_document_falls_back_to_text_index_when_embeddings_fail(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    embedding_attempts = 0

    def failing_urlopen(_request, timeout):
        nonlocal embedding_attempts
        _ = timeout
        embedding_attempts += 1
        raise OSError("embedding upstream unavailable")

    monkeypatch.setattr(main, "urlopen", failing_urlopen)
    monkeypatch.setattr(model_gateway_service, "urlopen", failing_urlopen)

    document = client.post(
        "/api/knowledge/documents",
        json={
            "title": "Embedding 不可用兜底",
            "content": "keyword-only-token should still be searchable without embeddings.",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    ).json()["data"]

    assert document["index_status"] == "text_indexed"
    assert document["index_error"] == "Model gateway embedding request failed"
    assert document["chunk_count"] == 1

    results = client.post(
        "/api/knowledge/search",
        json={"query": "keyword-only-token", "top_k": 5},
        headers=admin_headers,
    ).json()["data"]["items"]

    assert [item["document_id"] for item in results] == [document["id"]]
    assert results[0]["score"] is None
    assert results[0]["retrieval_mode"] == "keyword"
    stored_chunks = [
        chunk
        for chunk in app.state.store.knowledge_chunks.values()
        if chunk["document_id"] == document["id"]
    ]
    assert len(stored_chunks) == 1
    assert stored_chunks[0].get("embedding") is None
    assert embedding_attempts == 1


def test_knowledge_search_does_not_vector_compare_incompatible_embedding_metadata(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()
    app.state.store.model_gateway_configs["model_gateway_config_current"] = {
        "api_key": "sk-current-embedding",
        "base_url": "https://embedding.example.com/v1",
        "default_chat_model": "gpt-current",
        "default_embedding_model": "current-embedding-model",
        "embedding_connection_mode": "reuse_chat",
        "id": "model_gateway_config_current",
        "is_default": True,
        "max_retries": 1,
        "name": "当前向量模型",
        "provider": "openai_compatible",
        "status": "active",
        "timeout_seconds": 60,
    }
    app.state.store.knowledge_documents["knowledge_incompatible"] = {
        "content": "legacy vector only content",
        "created_by": "user_admin",
        "doc_type": "manual",
        "id": "knowledge_incompatible",
        "index_error": None,
        "index_status": "vector_indexed",
        "permission_roles": ["admin"],
        "tags": [],
        "title": "旧向量文档",
        "vector_index_error": None,
    }
    app.state.store.knowledge_chunks["knowledge_incompatible_chunk_001"] = {
        "chunk_index": 1,
        "content": "legacy vector only content",
        "document_id": "knowledge_incompatible",
        "embedding": [1.0, *([0.0] * 1535)],
        "id": "knowledge_incompatible_chunk_001",
        "metadata": {
            "doc_type": "manual",
            "embedding_config_id": "model_gateway_config_legacy",
            "embedding_dimension": 1536,
            "embedding_model": "legacy-embedding-model",
            "title": "旧向量文档",
        },
        "permission_roles": ["admin"],
        "permission_scope": {"roles": ["admin"]},
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "data": [{"embedding": [1.0, *([0.0] * 1535)], "index": 0}],
                    "usage": {"prompt_tokens": 1, "total_tokens": 1},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(_request, timeout):
        _ = timeout
        return FakeResponse()

    monkeypatch.setattr(main, "urlopen", fake_urlopen)
    monkeypatch.setattr(model_gateway_service, "urlopen", fake_urlopen)

    results = client.post(
        "/api/knowledge/search",
        json={"query": "query-without-keyword-hit", "top_k": 5},
        headers=admin_headers,
    ).json()["data"]["items"]

    assert results == []


def test_knowledge_search_does_not_synthesize_chunks_when_index_rows_are_missing():
    app.state.store.reset()
    admin_headers = auth_headers()

    document = client.post(
        "/api/knowledge/documents",
        json={
            "title": "索引缺失文档",
            "content": "missing-chunk-token must not be returned without a stored chunk.",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    ).json()["data"]
    app.state.store.knowledge_chunks = {
        chunk_id: chunk
        for chunk_id, chunk in app.state.store.knowledge_chunks.items()
        if chunk["document_id"] != document["id"]
    }

    results = client.post(
        "/api/knowledge/search",
        json={"query": "missing-chunk-token", "top_k": 5},
        headers=admin_headers,
    ).json()["data"]["items"]

    assert results == []


def test_knowledge_index_failure_keeps_error_and_retry_rebuilds_chunks(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "data": [{"embedding": [1.0, *([0.0] * 1535)], "index": 0}],
                    "usage": {"prompt_tokens": 1, "total_tokens": 1},
                },
                ensure_ascii=False,
            ).encode("utf-8")

    def successful_urlopen(_request, timeout):
        _ = timeout
        return FakeResponse()

    monkeypatch.setattr(main, "urlopen", successful_urlopen)
    monkeypatch.setattr(model_gateway_service, "urlopen", successful_urlopen)

    document = client.post(
        "/api/knowledge/documents",
        json={
            "title": "索引失败重试指南",
            "content": "retry-index-token should only appear after successful indexing.",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    ).json()["data"]

    failed = client.patch(
        f"/api/knowledge/documents/{document['id']}",
        json={
            "index_error": "embedding provider timeout",
            "index_status": "index_failed",
        },
        headers=admin_headers,
    ).json()["data"]
    assert failed["index_status"] == "index_failed"
    assert failed["index_error"] == "embedding provider timeout"
    assert failed["chunk_count"] == 0

    indexed_items = client.get(
        "/api/knowledge/documents?index_status=index_failed",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [item["id"] for item in indexed_items] == [document["id"]]

    failed_search = client.post(
        "/api/knowledge/search",
        json={"query": "retry-index-token", "top_k": 5},
        headers=admin_headers,
    ).json()["data"]["items"]
    assert failed_search == []

    retried = client.post(
        f"/api/knowledge/documents/{document['id']}/retry-index",
        headers=admin_headers,
    ).json()["data"]
    assert retried["index_status"] == "vector_indexed"
    assert retried["index_error"] is None
    assert retried["vector_index_error"] is None
    assert retried["chunk_count"] == 1

    retried_search = client.post(
        "/api/knowledge/search",
        json={"query": "retry-index-token", "top_k": 5},
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [item["chunk_id"] for item in retried_search] == [f"{document['id']}_chunk_001"]
    assert retried_search[0]["retrieval_mode"] == "vector"


def test_knowledge_retry_upgrades_text_index_to_vector_index(monkeypatch):
    app.state.store.reset()
    admin_headers = auth_headers()

    def failing_urlopen(_request, timeout):
        _ = timeout
        raise OSError("embedding upstream unavailable")

    monkeypatch.setattr(main, "urlopen", failing_urlopen)
    monkeypatch.setattr(model_gateway_service, "urlopen", failing_urlopen)
    document = client.post(
        "/api/knowledge/documents",
        json={
            "title": "文本索引补向量",
            "content": "retry-upgrade-token can start as keyword-only.",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    ).json()["data"]
    assert document["index_status"] == "text_indexed"

    class FakeResponse:
        def __init__(self, payload: dict):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def successful_urlopen(request, timeout):
        _ = timeout
        payload = json.loads(request.data.decode("utf-8"))
        inputs = payload.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        return FakeResponse(
            {
                "data": [
                    {"embedding": [1.0, *([0.0] * 1535)], "index": index}
                    for index, _text in enumerate(inputs)
                ],
                "usage": {"prompt_tokens": len(inputs), "total_tokens": len(inputs)},
            }
        )

    monkeypatch.setattr(main, "urlopen", successful_urlopen)
    monkeypatch.setattr(model_gateway_service, "urlopen", successful_urlopen)
    retried = client.post(
        f"/api/knowledge/documents/{document['id']}/retry-index",
        headers=admin_headers,
    ).json()["data"]

    assert retried["index_status"] == "vector_indexed"
    assert retried["index_error"] is None
    assert retried["vector_index_error"] is None


def test_knowledge_index_status_must_use_supported_values():
    app.state.store.reset()
    admin_headers = auth_headers()
    document = client.post(
        "/api/knowledge/documents",
        json={
            "title": "索引状态校验",
            "content": "unsupported status should be rejected",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    ).json()["data"]

    response = client.patch(
        f"/api/knowledge/documents/{document['id']}",
        json={"index_status": "failed"},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_mock_issue_writeback_is_idempotent_for_completed_task():
    app.state.store.reset()
    headers = auth_headers()
    task_id = create_completed_design_task(headers)

    initial = client.get(f"/api/writeback/results/{task_id}", headers=headers).json()["data"]
    assert initial["status"] == "not_written"
    assert initial["issues"] == []

    first = client.post(f"/api/writeback/results/{task_id}", headers=headers).json()["data"]
    second = client.post(f"/api/writeback/results/{task_id}", headers=headers).json()["data"]
    queried = client.get(f"/api/writeback/results/{task_id}", headers=headers).json()["data"]

    assert first["status"] == "completed"
    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["issues"] == second["issues"]
    assert queried["issues"] == first["issues"]
    assert len(first["issues"]) == 1


def test_knowledge_deposit_can_be_rejected_once_with_reason():
    app.state.store.reset()
    headers = auth_headers()
    task_id = create_completed_design_task(headers)
    deposit = client.get("/api/knowledge/deposits?status=pending", headers=headers).json()[
        "data"
    ]["items"][0]

    rejected = client.post(
        f"/api/knowledge/deposits/{deposit['id']}/reject",
        json={"reason": "内容仍需人工整理"},
        headers=headers,
    ).json()["data"]
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "内容仍需人工整理"
    assert rejected["ai_task_id"] == task_id

    second_reject = client.post(
        f"/api/knowledge/deposits/{deposit['id']}/reject",
        json={"reason": "重复驳回"},
        headers=headers,
    )
    assert second_reject.status_code == 409
    assert second_reject.json()["detail"]["code"] == "KNOWLEDGE_DEPOSIT_STATE_INVALID"

    rejected_items = client.get(
        "/api/knowledge/deposits?status=rejected",
        headers=headers,
    ).json()["data"]["items"]
    assert [item["id"] for item in rejected_items] == [deposit["id"]]


def test_knowledge_index_health_summarizes_full_scope_and_actions():
    app.state.store.reset()
    headers = auth_headers()
    store = app.state.store

    def put_document(
        document_id: str,
        *,
        active_chunk_set_id: str | None = None,
        index_error: str | None = None,
        status: str,
        title: str,
        vector_index_error: str | None = None,
    ) -> None:
        store.knowledge_documents[document_id] = {
            "active_chunk_set_id": active_chunk_set_id,
            "content": f"{title} content",
            "created_at": "2026-06-29T01:00:00+00:00",
            "created_by": "user_admin",
            "doc_type": "manual",
            "id": document_id,
            "index_error": index_error,
            "index_status": status,
            "permission_roles": ["admin"],
            "source_type": "manual",
            "tags": [],
            "title": title,
            "updated_at": "2026-06-29T02:00:00+00:00",
            "vector_index_error": vector_index_error,
        }

    put_document(
        "knowledge_health_vector",
        active_chunk_set_id="chunk_set_vector",
        status="vector_indexed",
        title="向量就绪知识",
    )
    put_document(
        "knowledge_health_text",
        active_chunk_set_id="chunk_set_text",
        status="text_indexed",
        title="关键词兜底知识",
        vector_index_error="Embedding disabled",
    )
    put_document("knowledge_health_missing", status="indexed", title="分块缺失知识")
    put_document(
        "knowledge_health_failed",
        index_error="parser failed",
        status="index_failed",
        title="索引失败知识",
    )
    put_document("knowledge_health_pending", status="pending_index", title="处理中知识")
    store.knowledge_chunk_sets["chunk_set_vector"] = {
        "chunk_count": 1,
        "document_id": "knowledge_health_vector",
        "embedding_dimension": 1536,
        "embedding_model": "text-embedding-test",
        "id": "chunk_set_vector",
        "index_status": "vector_indexed",
        "is_active": True,
        "status": "active",
    }
    store.knowledge_chunk_sets["chunk_set_text"] = {
        "chunk_count": 1,
        "document_id": "knowledge_health_text",
        "id": "chunk_set_text",
        "index_status": "text_indexed",
        "is_active": True,
        "status": "active",
    }
    store.knowledge_chunks["chunk_vector"] = {
        "chunk_index": 1,
        "chunk_set_id": "chunk_set_vector",
        "content": "vector content",
        "document_id": "knowledge_health_vector",
        "embedding": [0.1, 0.2],
        "id": "chunk_vector",
    }
    store.knowledge_chunks["chunk_text"] = {
        "chunk_index": 1,
        "chunk_set_id": "chunk_set_text",
        "content": "keyword content",
        "document_id": "knowledge_health_text",
        "id": "chunk_text",
    }
    store.knowledge_import_jobs["import_pending"] = {
        "created_at": "2026-06-29T02:00:00+00:00",
        "document_id": "knowledge_health_pending",
        "id": "import_pending",
        "progress": 20,
        "status": "queued",
    }

    response = client.get("/api/knowledge/index-health?doc_type=manual", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"] == {
        "chunk_ready_documents": 2,
        "embedding_ready_chunks": 1,
        "index_failed_documents": 1,
        "keyword_only_chunks": 1,
        "keyword_only_documents": 1,
        "missing_chunk_documents": 1,
        "processing_documents": 1,
        "searchable_documents": 3,
        "total_chunks": 2,
        "total_documents": 5,
        "vector_ready_documents": 2,
    }
    assert {item["status"]: item["count"] for item in data["status_counts"]} == {
        "index_failed": 1,
        "indexed": 1,
        "pending_index": 1,
        "text_indexed": 1,
        "vector_indexed": 1,
    }
    assert {item["status"]: item["count"] for item in data["import_job_counts"]} == {"queued": 1}
    assert data["retrieval_modes"] == {
        "hybrid_ready": 2,
        "keyword_fallback": 1,
        "unavailable": 2,
    }
    assert data["permission_scope"] == {
        "filter_role": None,
        "global_knowledge_access": True,
        "knowledge_space_scope_ids": [],
        "matched_roles": ["admin"],
        "mode": "role_based",
        "readable_role_count": 1,
        "scope_labels": ["角色 admin 命中 5 个文档"],
    }
    assert any(item["model"] == "text-embedding-test" for item in data["embedding_models"])
    assert {issue["label"] for issue in data["issues"]} >= {
        "分块缺失",
        "向量待补",
        "处理中",
        "索引失败",
    }
    assert data["query"]["name"] == "knowledge_index_health"
    assert data["performance"]["result_count"] == 4
