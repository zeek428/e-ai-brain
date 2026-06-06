from test_database_persistence import (
    FakeSnapshotRepository,
    apply_payload_to_store,
    mock_writeback_context_payload,
)

from app.core.persistence import PersistentMemoryStore


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
