from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore
from app.core.users import MemoryUserRepository


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
