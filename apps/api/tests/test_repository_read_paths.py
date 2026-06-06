from app.core.persistence import PersistentMemoryStore
from app.core.users import MemoryUserRepository
from tests.test_database_persistence import FakeSnapshotRepository, app, auth_headers, client


def _use_stale_store(repository: FakeSnapshotRepository) -> tuple[object, object]:
    original_store = app.state.store
    original_users = app.state.user_repository
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()
    return original_store, original_users


def _restore_store(original_store: object, original_users: object) -> None:
    app.state.store = original_store
    app.state.user_repository = original_users


def test_knowledge_document_list_uses_repository_when_runtime_store_is_stale():
    repository = FakeSnapshotRepository()
    repository.knowledge_payload = {
        "knowledge_chunks": {
            "knowledge_repo_admin_chunk_001": {
                "content": "repository keyword chunk",
                "document_id": "knowledge_repo_admin",
                "id": "knowledge_repo_admin_chunk_001",
            },
            "knowledge_repo_admin_chunk_002": {
                "content": "second chunk",
                "document_id": "knowledge_repo_admin",
                "id": "knowledge_repo_admin_chunk_002",
            },
            "knowledge_repo_reviewer_chunk_001": {
                "content": "reviewer chunk",
                "document_id": "knowledge_repo_reviewer",
                "id": "knowledge_repo_reviewer_chunk_001",
            },
        },
        "knowledge_deposits": {},
        "knowledge_documents": {
            "knowledge_repo_admin": {
                "content": "repository keyword content",
                "created_by": "user_admin",
                "doc_type": "system",
                "id": "knowledge_repo_admin",
                "index_error": None,
                "index_status": "text_indexed",
                "permission_roles": ["admin"],
                "tags": ["db-first"],
                "title": "Repository 知识文档",
                "vector_index_error": "Embedding gateway is disabled",
            },
            "knowledge_repo_reviewer": {
                "content": "reviewer only content",
                "created_by": "user_reviewer",
                "doc_type": "manual",
                "id": "knowledge_repo_reviewer",
                "index_error": "人工失败",
                "index_status": "index_failed",
                "permission_roles": ["reviewer"],
                "tags": [],
                "title": "Reviewer 知识文档",
                "vector_index_error": None,
            },
        },
    }
    original_store, original_users = _use_stale_store(repository)
    app.state.store.knowledge_documents = {}
    app.state.store.knowledge_chunks = {}

    try:
        admin_response = client.get(
            "/api/knowledge/documents?keyword=repository%20keyword&doc_type=system"
            "&index_status=text_indexed",
            headers=auth_headers(),
        )
        assert admin_response.status_code == 200
        admin_items = admin_response.json()["data"]["items"]
        assert [item["id"] for item in admin_items] == ["knowledge_repo_admin"]
        assert admin_items[0]["chunk_count"] == 2
        assert admin_items[0]["vector_index_error"] == "Embedding gateway is disabled"

        reviewer_response = client.get(
            "/api/knowledge/documents",
            headers=auth_headers("reviewer@example.com", "reviewer123"),
        )
        assert reviewer_response.status_code == 200
        reviewer_items = reviewer_response.json()["data"]["items"]
        assert [item["id"] for item in reviewer_items] == ["knowledge_repo_reviewer"]
        assert reviewer_items[0]["chunk_count"] == 1
        assert reviewer_items[0]["index_error"] == "人工失败"
    finally:
        _restore_store(original_store, original_users)


def test_audit_event_list_uses_repository_when_runtime_store_is_stale():
    repository = FakeSnapshotRepository()
    repository.audit_events_payload = {
        "audit_events": [
            {
                "actor_id": "user_admin",
                "ai_task_id": "task_audit_read",
                "created_at": "2026-06-03T08:00:00+00:00",
                "event_type": "requirement.created",
                "id": "audit_repo_001",
                "payload": {"source": "repository"},
                "sequence": 1,
                "subject_id": "requirement_audit_read",
                "subject_type": "requirement",
            },
            {
                "actor_id": "user_admin",
                "ai_task_id": "task_audit_read",
                "created_at": "2026-06-03T09:00:00+00:00",
                "event_type": "requirement.created",
                "id": "audit_repo_002",
                "payload": {"source": "repository"},
                "sequence": 2,
                "subject_id": "requirement_audit_read",
                "subject_type": "requirement",
            },
            {
                "actor_id": "user_reviewer",
                "created_at": "2026-06-03T10:00:00+00:00",
                "event_type": "review.approved",
                "id": "audit_repo_003",
                "payload": {},
                "sequence": 3,
                "subject_id": "review_audit_read",
                "subject_type": "review",
            },
        ]
    }
    original_store, original_users = _use_stale_store(repository)
    app.state.store.audit_events = []

    try:
        response = client.get(
            "/api/audit/events?actor_id=user_admin&event_type=requirement.created"
            "&ai_task_id=task_audit_read&subject_type=requirement"
            "&subject_id=requirement_audit_read"
            "&created_from=2026-06-03T08:30:00%2B00:00"
            "&created_to=2026-06-03T09:30:00%2B00:00",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert [event["id"] for event in data["items"]] == ["audit_repo_002"]
        assert data["items"][0]["payload"] == {"source": "repository"}
    finally:
        _restore_store(original_store, original_users)


def test_knowledge_deposit_list_uses_repository_when_runtime_store_is_stale():
    repository = FakeSnapshotRepository()
    repository.knowledge_payload = {
        "knowledge_chunks": {},
        "knowledge_deposits": {
            "deposit_repo_pending": {
                "ai_task_id": "task_repo_001",
                "content": "待审核沉淀内容",
                "created_at": "2026-06-03T08:00:00+00:00",
                "deposit_type": "task_solution",
                "id": "deposit_repo_pending",
                "status": "pending",
                "title": "Repository 待审核沉淀",
            },
            "deposit_repo_rejected": {
                "ai_task_id": "task_repo_002",
                "content": "已拒绝沉淀内容",
                "created_at": "2026-06-03T09:00:00+00:00",
                "deposit_type": "task_solution",
                "id": "deposit_repo_rejected",
                "rejection_reason": "内容重复",
                "status": "rejected",
                "title": "Repository 已拒绝沉淀",
            },
        },
        "knowledge_documents": {},
    }
    original_store, original_users = _use_stale_store(repository)
    app.state.store.knowledge_deposits = {}

    try:
        headers = auth_headers()
        pending = client.get(
            "/api/knowledge/deposits?status=pending",
            headers=headers,
        ).json()["data"]
        all_deposits = client.get("/api/knowledge/deposits", headers=headers).json()["data"]

        assert [item["id"] for item in pending["items"]] == ["deposit_repo_pending"]
        assert pending["total"] == 1
        assert [item["id"] for item in all_deposits["items"]] == [
            "deposit_repo_pending",
            "deposit_repo_rejected",
        ]
        assert all_deposits["total"] == 2
    finally:
        _restore_store(original_store, original_users)


def test_knowledge_search_uses_repository_when_runtime_store_is_stale():
    repository = FakeSnapshotRepository()
    repository.knowledge_payload = {
        "knowledge_chunks": {
            "knowledge_repo_search_chunk_001": {
                "chunk_index": 1,
                "content": "repository-search-token 可通过结构表检索",
                "document_id": "knowledge_repo_search",
                "id": "knowledge_repo_search_chunk_001",
                "metadata": {"doc_type": "system", "title": "Repository 检索文档"},
                "permission_roles": ["admin"],
                "permission_scope": {"roles": ["admin"]},
            },
            "knowledge_repo_review_chunk_001": {
                "chunk_index": 1,
                "content": "reviewer-only-token 不应对 admin 以外无权限用户泄露",
                "document_id": "knowledge_repo_review",
                "id": "knowledge_repo_review_chunk_001",
                "metadata": {"doc_type": "manual", "title": "Reviewer 检索文档"},
                "permission_roles": ["reviewer"],
                "permission_scope": {"roles": ["reviewer"]},
            },
        },
        "knowledge_deposits": {},
        "knowledge_documents": {
            "knowledge_repo_search": {
                "content": "repository-search-token 可通过结构表检索",
                "created_by": "user_admin",
                "doc_type": "system",
                "id": "knowledge_repo_search",
                "index_status": "text_indexed",
                "permission_roles": ["admin"],
                "tags": ["db-first"],
                "title": "Repository 检索文档",
            },
            "knowledge_repo_review": {
                "content": "reviewer-only-token",
                "created_by": "user_reviewer",
                "doc_type": "manual",
                "id": "knowledge_repo_review",
                "index_status": "text_indexed",
                "permission_roles": ["reviewer"],
                "tags": [],
                "title": "Reviewer 检索文档",
            },
        },
    }
    original_store, original_users = _use_stale_store(repository)
    app.state.store.knowledge_documents = {}
    app.state.store.knowledge_chunks = {}

    try:
        headers = auth_headers()
        results = client.post(
            "/api/knowledge/search",
            json={"query": "repository-search-token", "top_k": 5},
            headers=headers,
        ).json()["data"]["items"]
        forbidden = client.post(
            "/api/knowledge/search",
            json={"query": "reviewer-only-token", "top_k": 5},
            headers=headers,
        ).json()["data"]["items"]

        assert [item["chunk_id"] for item in results] == ["knowledge_repo_search_chunk_001"]
        assert results[0]["retrieval_mode"] == "keyword"
        assert forbidden == []
    finally:
        _restore_store(original_store, original_users)


def test_model_gateway_config_list_uses_repository_when_runtime_store_is_stale():
    repository = FakeSnapshotRepository()
    repository.model_gateway_payload = {
        "model_gateway_configs": {
            "model_gateway_config_read": {
                "api_key": "sk-stale-runtime",
                "base_url": "https://api.example.com/v1",
                "default_chat_model": "gpt-read",
                "default_embedding_model": "text-embedding-read",
                "embedding_api_key": "sk-embedding-stale-runtime",
                "embedding_base_url": "https://embedding.example.com/v1",
                "embedding_connection_mode": "separate",
                "embedding_dimension": 1536,
                "id": "model_gateway_config_read",
                "is_default": True,
                "max_retries": 2,
                "name": "Repository 模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            }
        },
        "model_gateway_logs": [],
    }
    original_store, original_users = _use_stale_store(repository)
    app.state.store.model_gateway_configs = {}

    try:
        response = client.get("/api/system/model-gateway-configs", headers=auth_headers())
        assert response.status_code == 200
        data = response.json()["data"]
        assert [item["id"] for item in data["items"]] == ["model_gateway_config_read"]
        item = data["items"][0]
        assert item["api_key_configured"] is True
        assert item["embedding_api_key_configured"] is True
        assert "api_key" not in item
        assert "embedding_api_key" not in item
    finally:
        _restore_store(original_store, original_users)


def test_model_gateway_log_list_uses_repository_when_runtime_store_is_stale():
    repository = FakeSnapshotRepository()
    repository.model_gateway_payload = {
        "model_gateway_configs": {},
        "model_gateway_logs": [
            {
                "ai_task_id": "task_log_read",
                "created_at": "2026-06-03T08:00:00+00:00",
                "id": "model_log_repo_001",
                "latency_ms": 12,
                "model": "gpt-read",
                "model_gateway_config_id": "model_gateway_config_read",
                "provider": "openai_compatible",
                "purpose": "assistant_chat",
                "status": "succeeded",
                "tokens": {"total_tokens": 8},
            },
            {
                "ai_task_id": "task_other",
                "created_at": "2026-06-03T09:00:00+00:00",
                "error": "failed",
                "id": "model_log_repo_002",
                "latency_ms": 3,
                "model": "gpt-read",
                "provider": "openai_compatible",
                "purpose": "task_generation",
                "status": "failed",
                "tokens": {},
            },
        ],
    }
    original_store, original_users = _use_stale_store(repository)
    app.state.store.model_gateway_logs = []

    try:
        response = client.get(
            "/api/model-gateway/logs?purpose=assistant_chat&status=succeeded",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert [item["id"] for item in data["items"]] == ["model_log_repo_001"]
        assert data["items"][0]["tokens"] == {"total_tokens": 8}
    finally:
        _restore_store(original_store, original_users)
