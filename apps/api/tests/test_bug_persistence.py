from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore
from app.core.users import MemoryUserRepository


def test_bugs_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.bugs["bug_009"] = {
        "assignee": "rd_owner@example.com",
        "created_at": "2026-05-31T10:00:00+00:00",
        "created_by": "user_admin",
        "description": "结构表持久化验证",
        "duplicate_of_bug_id": None,
        "evidence": {"browser": "chrome"},
        "id": "bug_009",
        "module_code": "knowledge",
        "product_id": "product_001",
        "related_task_id": None,
        "reproduce_steps": ["打开知识检索"],
        "requirement_id": None,
        "severity": "major",
        "source": "manual_test",
        "status": "assigned",
        "title": "Bug 结构表验证",
        "updated_at": "2026-05-31T10:05:00+00:00",
        "version_id": "version_001",
    }

    current_store.persist()

    assert repository.bugs_payload == {
        "bugs": {
            "bug_009": {
                "assignee": "rd_owner@example.com",
                "created_at": "2026-05-31T10:00:00+00:00",
                "created_by": "user_admin",
                "description": "结构表持久化验证",
                "duplicate_of_bug_id": None,
                "evidence": {"browser": "chrome"},
                "id": "bug_009",
                "module_code": "knowledge",
                "product_id": "product_001",
                "related_task_id": None,
                "reproduce_steps": ["打开知识检索"],
                "requirement_id": None,
                "severity": "major",
                "source": "manual_test",
                "status": "assigned",
                "title": "Bug 结构表验证",
                "updated_at": "2026-05-31T10:05:00+00:00",
                "version_id": "version_001",
            }
        }
    }


def test_structured_bugs_restore_and_sync_counter():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "bugs": {
            "bug_002": {
                "created_by": "user_admin",
                "description": "旧快照 Bug",
                "evidence": {},
                "id": "bug_002",
                "product_id": "product_001",
                "reproduce_steps": [],
                "severity": "major",
                "source": "manual_test",
                "status": "open",
                "title": "旧快照 Bug",
            }
        }
    }
    repository.bugs_payload = {
        "bugs": {
            "bug_009": {
                "created_by": "user_admin",
                "description": "结构表 Bug",
                "evidence": {},
                "id": "bug_009",
                "product_id": "product_001",
                "reproduce_steps": ["复现步骤"],
                "severity": "critical",
                "source": "manual_test",
                "status": "triaged",
                "title": "结构表 Bug",
            }
        }
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert list(rebuilt_store.bugs) == ["bug_009"]
    assert rebuilt_store.bugs["bug_009"]["status"] == "triaged"
    assert rebuilt_store.new_id("bug") == "bug_010"


def test_bug_api_writes_fine_grained_repository_payload():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "bug-persist", "name": "Bug 持久化产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1"},
            headers=headers,
        ).json()["data"]
        bug = client.post(
            "/api/bugs",
            json={
                "description": "Bug 创建必须写入结构表 payload",
                "product_id": product["id"],
                "severity": "major",
                "source": "manual_test",
                "title": "Bug API 结构表验证",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]

        assert repository.bugs_payload is not None
        persisted = repository.bugs_payload["bugs"][bug["id"]]
        assert persisted["title"] == "Bug API 结构表验证"
        assert persisted["version_id"] == version["id"]
        assert persisted["status"] == "open"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_bug_api_writes_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> PersistentMemoryStore:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store
        return rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "BUG-DBFIRST", "name": "Bug DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1"},
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        bug = client.post(
            "/api/bugs",
            json={
                "description": "Bug 创建、修改、删除必须直接写 repository。",
                "product_id": product["id"],
                "severity": "major",
                "source": "manual_test",
                "title": "Bug DB-first 创建",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        listed = client.get(
            f"/api/bugs?product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in listed] == [bug["id"]]
        assert listed[0]["status"] == "open"

        patched = client.patch(
            f"/api/bugs/{bug['id']}",
            json={"assignee": "rd_owner@example.com", "status": "triaged"},
            headers=headers,
        ).json()["data"]
        assert patched["status"] == "triaged"

        use_rebuilt_store_without_request_persist()
        patched_list = client.get(
            f"/api/bugs?product_id={product['id']}&status=triaged",
            headers=headers,
        ).json()["data"]["items"]
        assert patched_list[0]["assignee"] == "rd_owner@example.com"

        duplicate = client.post(
            "/api/bugs",
            json={
                "description": "重复归并引用在目标删除后必须清空。",
                "duplicate_of_bug_id": bug["id"],
                "product_id": product["id"],
                "severity": "minor",
                "source": "manual_test",
                "title": "Bug DB-first 重复引用",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        assert duplicate["duplicate_of_bug_id"] == bug["id"]

        deleted = client.delete(f"/api/bugs/{bug['id']}", headers=headers).json()["data"]
        assert deleted == {"deleted": True, "id": bug["id"]}

        use_rebuilt_store_without_request_persist()
        remaining = client.get(
            f"/api/bugs?product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in remaining] == [duplicate["id"]]
        assert remaining[0]["duplicate_of_bug_id"] is None

        duplicate_deleted = client.delete(
            f"/api/bugs/{duplicate['id']}",
            headers=headers,
        ).json()["data"]
        assert duplicate_deleted == {"deleted": True, "id": duplicate["id"]}

        use_rebuilt_store_without_request_persist()
        empty_list = client.get(
            f"/api/bugs?product_id={product['id']}",
            headers=headers,
        ).json()["data"]
        assert empty_list["items"] == []
        assert empty_list["total"] == 0
        assert empty_list["performance"]["result_count"] == 0
        assert [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ].count("bug.created") == 2
        assert [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ].count("bug.updated") == 1
        assert [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ].count("bug.deleted") == 2
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_bug_list_uses_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.bugs_payload = {
        "bugs": {
            "bug_repo_001": {
                "assignee": "rd_owner@example.com",
                "created_at": "2026-06-03T08:00:00+00:00",
                "created_by": "user_admin",
                "description": "repository bug",
                "evidence": {"log": "error"},
                "id": "bug_repo_001",
                "product_id": "product_bug_repo",
                "reproduce_steps": ["open page"],
                "severity": "major",
                "source": "manual_test",
                "status": "triaged",
                "title": "Repository Bug",
            },
            "bug_repo_002": {
                "created_at": "2026-06-03T09:00:00+00:00",
                "created_by": "user_admin",
                "description": "other bug",
                "evidence": {},
                "id": "bug_repo_002",
                "product_id": "product_other",
                "reproduce_steps": [],
                "severity": "minor",
                "source": "ai_auto_test",
                "status": "open",
                "title": "Other Bug",
            },
        }
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.bugs = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        response = client.get(
            "/api/bugs?product_id=product_bug_repo&status=triaged"
            "&severity=major&source=manual_test",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert [item["id"] for item in data["items"]] == ["bug_repo_001"]
        assert data["items"][0]["evidence"] == {"log": "error"}
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
