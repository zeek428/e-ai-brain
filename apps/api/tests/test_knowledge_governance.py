import json

from fastapi.testclient import TestClient

import app.main as main
from app.main import app

client = TestClient(app)


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
    deposits = client.get("/api/knowledge/deposits?status=pending", headers=admin_headers).json()[
        "data"
    ]["items"]
    assert deposits[0]["ai_task_id"] == task_id
    assert deposits[0]["status"] == "pending"

    approved = client.post(
        f"/api/knowledge/deposits/{deposits[0]['id']}/approve",
        json={"title": "知识治理闭环沉淀"},
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


def test_knowledge_index_failure_keeps_error_and_retry_rebuilds_chunks():
    app.state.store.reset()
    admin_headers = auth_headers()

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
    assert retried["index_status"] == "indexed"
    assert retried["index_error"] is None
    assert retried["chunk_count"] == 1

    retried_search = client.post(
        "/api/knowledge/search",
        json={"query": "retry-index-token", "top_k": 5},
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [item["chunk_id"] for item in retried_search] == [f"{document['id']}_chunk_001"]


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
