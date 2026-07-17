from test_database_persistence import (
    FakeSnapshotRepository,
    app,
    apply_payload_to_store,
    auth_headers,
    client,
    mock_writeback_context_payload,
)

from app.core.persistence import PersistentMemoryStore
from app.core.users import MemoryUserRepository
from app.services.mock_writeback import create_mock_writeback_result
from tests.requirement_fixtures import seed_accepted_assessment_provenance


def test_mock_writebacks_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    apply_payload_to_store(current_store, mock_writeback_context_payload())
    current_store.mock_writebacks["mock_issue:task_010"] = {
        "idempotency_key": "mock_issue:task_010",
        "issues": [
            {
                "id": "mock_issue_010",
                "source_task_id": "task_010",
                "status": "open",
                "title": "Persist mock writeback",
            }
        ],
        "status": "completed",
        "task_id": "task_010",
    }

    current_store.persist()

    assert repository.mock_writebacks_payload == {
        "mock_writebacks": current_store.mock_writebacks,
    }


def test_structured_mock_writebacks_restore_and_sync_counters():
    repository = FakeSnapshotRepository()
    context_payload = mock_writeback_context_payload()
    repository.payload = {
        "ai_tasks": context_payload["ai_tasks"],
        "counters": {"mock_issue": 10},
        "mock_writebacks": {
            "mock_issue:task_010": {
                "idempotency_key": "mock_issue:task_010",
                "issues": [
                    {
                        "id": "mock_issue_010",
                        "source_task_id": "task_010",
                        "status": "open",
                        "title": "旧快照 Issue",
                    }
                ],
                "status": "completed",
                "task_id": "task_010",
            }
        },
        "product_versions": context_payload["product_versions"],
        "products": context_payload["products"],
        "requirements": context_payload["requirements"],
    }
    repository.ai_tasks_payload = {"ai_tasks": context_payload["ai_tasks"]}
    repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": context_payload["product_versions"],
        "products": context_payload["products"],
    }
    repository.requirements_payload = {"requirements": context_payload["requirements"]}
    repository.mock_writebacks_payload = {
        "mock_writebacks": {
            "mock_issue:task_010": {
                "idempotency_key": "mock_issue:task_010",
                "issues": [
                    {
                        "id": "mock_issue_011",
                        "source_task_id": "task_010",
                        "status": "open",
                        "title": "结构表 Issue",
                    }
                ],
                "status": "completed",
                "task_id": "task_010",
            }
        }
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    writeback = rebuilt_store.mock_writebacks["mock_issue:task_010"]
    assert writeback["issues"][0]["id"] == "mock_issue_011"
    assert writeback["issues"][0]["title"] == "结构表 Issue"
    assert rebuilt_store.new_id("mock_issue") == "mock_issue_012"


def test_stale_mock_writebacks_with_missing_tasks_are_not_persisted():
    repository = FakeSnapshotRepository()
    payload = mock_writeback_context_payload()
    payload["mock_writebacks"] = {
        "mock_issue:task_999": {
            "idempotency_key": "mock_issue:task_999",
            "issues": [
                {
                    "id": "mock_issue_999",
                    "source_task_id": "task_999",
                    "status": "open",
                    "title": "Stale issue",
                }
            ],
            "status": "completed",
            "task_id": "task_999",
        }
    }
    repository.payload = payload

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    rebuilt_store.persist()

    assert rebuilt_store.mock_writebacks == {}
    assert repository.mock_writebacks_payload == {"mock_writebacks": {}}


def test_mock_writeback_memory_fallback_writes_result_and_audit_once():
    current_store = app.state.store
    current_store.reset()
    current_store.ai_tasks["task_mock_writeback"] = {
        "id": "task_mock_writeback",
        "status": "completed",
        "title": "Mock writeback helper",
    }

    first = create_mock_writeback_result(
        current_store,
        task_id="task_mock_writeback",
        actor_id="user_admin",
    )
    second = create_mock_writeback_result(
        current_store,
        task_id="task_mock_writeback",
        actor_id="user_admin",
    )

    assert second == first
    assert current_store.mock_writebacks[first["idempotency_key"]] == first
    assert len(first["issues"]) == 1
    writeback_events = [
        event
        for event in current_store.audit_events
        if event["event_type"] == "mock_issue.written"
        and event["ai_task_id"] == "task_mock_writeback"
    ]
    assert len(writeback_events) == 1


def _create_generated_design_task(
    headers: dict[str, str],
    *,
    product_code: str,
    product_name: str,
    requirement_title: str,
) -> dict:
    product = client.post(
        "/api/products",
        json={"code": product_code, "name": product_name},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1", "status": "active"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": f"{requirement_title} 必须在失败时直接写 repository。",
            "product_id": product["id"],
            "title": requirement_title,
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    seed_accepted_assessment_provenance(app.state.store, requirement)
    client.post(
        f"/api/requirements/{requirement['id']}/approve",
        json={"comment": "进入设计"},
        headers=headers,
    )
    return client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]

def test_mock_writeback_writes_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        generated = _create_generated_design_task(
            headers,
            product_code="WRITEBACK-DBFIRST",
            product_name="Mock Writeback DB-first 产品",
            requirement_title="Mock Writeback DB-first",
        )
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        approved = client.post(
            f"/api/reviews/{started['review_id']}/approve",
            json={"version": 1},
            headers=headers,
        ).json()["data"]
        assert approved["task_status"] == "completed"

        use_rebuilt_store_without_request_persist()
        written = client.post(
            f"/api/writeback/results/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        repeated = client.post(
            f"/api/writeback/results/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        assert written["status"] == "completed"
        assert written["idempotency_key"] == f"mock_issue:{generated['task_id']}"
        assert repeated == written
        assert repository.mock_writebacks_payload is not None
        assert (
            repository.mock_writebacks_payload["mock_writebacks"][written["idempotency_key"]]
            == written
        )
        assert any(
            event["event_type"] == "mock_issue.written"
            and event["ai_task_id"] == generated["task_id"]
            for event in repository.audit_events_payload["audit_events"]
        )

        use_rebuilt_store_without_request_persist()
        app.state.store.ai_tasks = {}
        app.state.store.mock_writebacks = {}
        repository.task_workflow_source_row_reads = 0
        restored = client.get(
            f"/api/writeback/results/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        assert restored == written
        assert repository.task_workflow_source_row_reads == 1
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
