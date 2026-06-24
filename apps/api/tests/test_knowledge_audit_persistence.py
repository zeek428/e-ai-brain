from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.store import MemoryStore
from app.core.users import MemoryUserRepository
from app.services.knowledge_deposits import apply_knowledge_document_to_memory, record_audit_event


def test_knowledge_record_audit_event_appends_memory_fallback_event():
    current_store = MemoryStore()

    event = record_audit_event(
        current_store,
        actor_id="user_admin",
        event_type="knowledge_document.created",
        subject_id="knowledge_001",
        subject_type="knowledge_document",
    )

    assert event["id"] == "audit_001"
    assert event["sequence"] == 1
    assert current_store.audit_events == [event]


def test_apply_knowledge_document_to_memory_replaces_document_chunks():
    current_store = MemoryStore()
    current_store.knowledge_chunks["knowledge_001_chunk_old"] = {
        "document_id": "knowledge_001",
        "id": "knowledge_001_chunk_old",
    }
    current_store.knowledge_chunks["knowledge_other_chunk_001"] = {
        "document_id": "knowledge_other",
        "id": "knowledge_other_chunk_001",
    }

    apply_knowledge_document_to_memory(
        current_store,
        {"id": "knowledge_001", "title": "知识"},
        [
            {
                "document_id": "knowledge_001",
                "id": "knowledge_001_chunk_001",
            }
        ],
    )

    assert current_store.knowledge_documents["knowledge_001"]["title"] == "知识"
    assert set(current_store.knowledge_chunks) == {
        "knowledge_001_chunk_001",
        "knowledge_other_chunk_001",
    }


def test_knowledge_and_audit_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.knowledge_documents["knowledge_009"] = {
        "content": "真实系统知识文档必须写入结构表",
        "created_by": "user_admin",
        "doc_type": "manual",
        "id": "knowledge_009",
        "index_status": "indexed",
        "permission_roles": ["admin", "knowledge_owner"],
        "tags": ["persistence"],
        "title": "知识结构表验证",
    }
    current_store.knowledge_chunks["knowledge_009_chunk_001"] = {
        "chunk_index": 1,
        "content": "真实系统知识文档必须写入结构表",
        "document_id": "knowledge_009",
        "embedding": [0.25, *([0.0] * 1535)],
        "id": "knowledge_009_chunk_001",
        "metadata": {"title": "知识结构表验证"},
        "permission_roles": ["admin", "knowledge_owner"],
    }
    current_store.knowledge_deposits["deposit_004"] = {
        "ai_task_id": "task_002",
        "content": "任务输出摘要",
        "id": "deposit_004",
        "knowledge_document_id": "knowledge_009",
        "status": "approved",
        "title": "任务输出沉淀",
    }
    current_store.audit_events.append(
        {
            "actor_id": "user_admin",
            "event_type": "knowledge_document.created",
            "id": "audit_007",
            "payload": {"source": "test"},
            "sequence": 7,
            "subject_id": "knowledge_009",
            "subject_type": "knowledge_document",
        }
    )

    current_store.persist()

    assert repository.knowledge_payload is not None
    assert repository.knowledge_payload["knowledge_documents"]["knowledge_009"]["title"] == (
        "知识结构表验证"
    )
    assert repository.knowledge_payload["knowledge_chunks"]["knowledge_009_chunk_001"][
        "document_id"
    ] == "knowledge_009"
    assert repository.knowledge_payload["knowledge_chunks"]["knowledge_009_chunk_001"][
        "embedding"
    ] == [0.25, *([0.0] * 1535)]
    assert repository.knowledge_payload["knowledge_deposits"]["deposit_004"][
        "knowledge_document_id"
    ] == "knowledge_009"
    assert repository.audit_events_payload == {
        "audit_events": [
            {
                "actor_id": "user_admin",
                "event_type": "knowledge_document.created",
                "id": "audit_007",
                "payload": {"source": "test"},
                "sequence": 7,
                "subject_id": "knowledge_009",
                "subject_type": "knowledge_document",
            }
        ]
    }


def test_structured_knowledge_and_audit_restore_and_sync_counters():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "audit_events": [
            {
                "actor_id": "snapshot_user",
                "event_type": "snapshot.audit",
                "id": "audit_003",
                "payload": {},
                "sequence": 3,
            }
        ],
        "knowledge_documents": {
            "knowledge_002": {
                "content": "旧快照知识",
                "created_by": "user_admin",
                "doc_type": "manual",
                "id": "knowledge_002",
                "index_status": "indexed",
                "permission_roles": ["admin"],
                "tags": [],
                "title": "旧快照知识",
            }
        },
    }
    repository.knowledge_payload = {
        "knowledge_deposits": {
            "deposit_004": {
                "ai_task_id": "task_002",
                "content": "结构表沉淀",
                "id": "deposit_004",
                "knowledge_document_id": "knowledge_009",
                "status": "approved",
                "title": "结构表沉淀",
            }
        },
        "knowledge_documents": {
            "knowledge_009": {
                "content": "结构表知识",
                "created_by": "user_admin",
                "doc_type": "manual",
                "id": "knowledge_009",
                "index_status": "indexed",
                "permission_roles": ["admin"],
                "tags": [],
                "title": "结构表知识",
            }
        },
        "knowledge_chunks": {
            "knowledge_009_chunk_001": {
                "chunk_index": 1,
                "content": "结构表知识",
                "document_id": "knowledge_009",
                "embedding": [0.5, *([0.0] * 1535)],
                "id": "knowledge_009_chunk_001",
                "metadata": {"title": "结构表知识"},
                "permission_roles": ["admin"],
            }
        },
    }
    repository.audit_events_payload = {
        "audit_events": [
            {
                "actor_id": "user_admin",
                "event_type": "structured.audit",
                "id": "audit_007",
                "payload": {},
                "sequence": 7,
            }
        ]
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert list(rebuilt_store.knowledge_documents) == ["knowledge_009"]
    assert list(rebuilt_store.knowledge_chunks) == ["knowledge_009_chunk_001"]
    assert rebuilt_store.knowledge_chunks["knowledge_009_chunk_001"]["embedding"] == [
        0.5,
        *([0.0] * 1535),
    ]
    assert rebuilt_store.knowledge_deposits["deposit_004"]["title"] == "结构表沉淀"
    assert [event["id"] for event in rebuilt_store.audit_events] == ["audit_007"]
    assert rebuilt_store.new_id("knowledge") == "knowledge_010"
    assert rebuilt_store.new_id("deposit") == "deposit_005"
    assert rebuilt_store.new_id("audit") == "audit_008"


def test_knowledge_api_writes_fine_grained_repository_and_audit_payload():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        document = client.post(
            "/api/knowledge/documents",
            json={
                "content": "知识文档必须从结构表恢复",
                "doc_type": "manual",
                "permission_roles": ["admin", "knowledge_owner"],
                "tags": ["db"],
                "title": "知识结构表 API 验证",
            },
            headers=headers,
        ).json()["data"]

        assert repository.knowledge_payload is not None
        persisted = repository.knowledge_payload["knowledge_documents"][document["id"]]
        assert persisted["title"] == "知识结构表 API 验证"
        assert persisted["permission_roles"] == ["admin", "knowledge_owner"]
        chunk_items = list(repository.knowledge_payload["knowledge_chunks"].values())
        assert [chunk["document_id"] for chunk in chunk_items] == [document["id"]]
        assert chunk_items[0]["content"] == "知识文档必须从结构表恢复"

        assert repository.audit_events_payload is not None
        assert repository.audit_events_payload["audit_events"][-1]["event_type"] == (
            "knowledge_document.created"
        )
        assert repository.audit_events_payload["audit_events"][-1]["subject_id"] == document["id"]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_knowledge_routes_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        created = client.post(
            "/api/knowledge/documents",
            json={
                "content": "retrieval marker\n\nDB-first 知识文档必须直接写 repository。",
                "doc_type": "system",
                "permission_roles": ["admin", "knowledge_owner"],
                "tags": ["db-first"],
                "title": "知识 DB-first 创建",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        documents = client.get("/api/knowledge/documents", headers=headers).json()["data"][
            "items"
        ]
        search_results = client.post(
            "/api/knowledge/search",
            json={"query": "retrieval marker"},
            headers=headers,
        ).json()["data"]["items"]
        assert [document["id"] for document in documents] == [created["id"]]
        assert documents[0]["chunk_count"] == 2
        assert search_results[0]["document_id"] == created["id"]
        assert repository.model_gateway_payload["model_gateway_logs"]

        patched = client.patch(
            f"/api/knowledge/documents/{created['id']}",
            json={
                "content": "new-search-token\n\n更新后的知识内容。",
                "title": "知识 DB-first 修改",
            },
            headers=headers,
        ).json()["data"]
        assert patched["title"] == "知识 DB-first 修改"

        use_empty_postgres_runtime_store()
        patched_detail = client.get("/api/knowledge/documents", headers=headers).json()["data"][
            "items"
        ][0]
        patched_search_results = client.post(
            "/api/knowledge/search",
            json={"query": "new-search-token"},
            headers=headers,
        ).json()["data"]["items"]
        assert patched_detail["title"] == "知识 DB-first 修改"
        assert patched_search_results[0]["document_id"] == created["id"]

        client.patch(
            f"/api/knowledge/documents/{created['id']}",
            json={"index_error": "人工标记索引失败", "index_status": "index_failed"},
            headers=headers,
        )
        use_empty_postgres_runtime_store()
        failed_detail = client.get(
            "/api/knowledge/documents?index_status=index_failed",
            headers=headers,
        ).json()["data"]["items"][0]
        assert failed_detail["chunk_count"] == 0
        retried = client.post(
            f"/api/knowledge/documents/{created['id']}/retry-index",
            headers=headers,
        ).json()["data"]
        assert retried["index_status"] == "vector_indexed"

        repository.knowledge_payload.setdefault("knowledge_deposits", {})[
            "deposit_dbfirst_approve"
        ] = {
            "ai_task_id": "task_knowledge_dbfirst",
            "content": "沉淀采纳内容 retrieval marker",
            "id": "deposit_dbfirst_approve",
            "knowledge_document_id": None,
            "status": "pending",
            "title": "待采纳知识沉淀",
        }
        current_store = use_empty_postgres_runtime_store()
        current_store.knowledge_deposits = {}
        approved_deposit = client.post(
            "/api/knowledge/deposits/deposit_dbfirst_approve/approve",
            json={
                "permission_roles": ["admin", "knowledge_owner"],
                "title": "采纳后的知识文档",
            },
            headers=headers,
        ).json()["data"]
        assert approved_deposit["status"] == "approved"
        approved_document_id = approved_deposit["knowledge_document_id"]

        use_empty_postgres_runtime_store()
        deposits = client.get("/api/knowledge/deposits", headers=headers).json()["data"]["items"]
        approved = next(deposit for deposit in deposits if deposit["id"] == approved_deposit["id"])
        assert approved["knowledge_document_id"] == approved_document_id
        assert approved["updated_at"]

        client.delete(f"/api/knowledge/documents/{approved_document_id}", headers=headers)
        use_empty_postgres_runtime_store()
        deposits_after_delete = client.get("/api/knowledge/deposits", headers=headers).json()[
            "data"
        ]["items"]
        approved_after_delete = next(
            deposit for deposit in deposits_after_delete if deposit["id"] == approved_deposit["id"]
        )
        assert approved_after_delete["knowledge_document_id"] is None

        repository.knowledge_payload.setdefault("knowledge_deposits", {})[
            "deposit_dbfirst_reject"
        ] = {
            "ai_task_id": "task_knowledge_dbfirst",
            "content": "沉淀拒绝内容",
            "id": "deposit_dbfirst_reject",
            "knowledge_document_id": None,
            "status": "pending",
            "title": "待拒绝知识沉淀",
        }
        current_store = use_empty_postgres_runtime_store()
        current_store.knowledge_deposits = {}
        rejected_deposit = client.post(
            "/api/knowledge/deposits/deposit_dbfirst_reject/reject",
            json={"reason": "内容重复"},
            headers=headers,
        ).json()["data"]
        assert rejected_deposit["status"] == "rejected"

        use_empty_postgres_runtime_store()
        rejected = next(
            deposit
            for deposit in client.get("/api/knowledge/deposits", headers=headers).json()["data"][
                "items"
            ]
            if deposit["id"] == "deposit_dbfirst_reject"
        )
        assert rejected["rejection_reason"] == "内容重复"
        assert any(
            event["event_type"] == "knowledge_deposit.rejected"
            for event in repository.audit_events_payload["audit_events"]
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
