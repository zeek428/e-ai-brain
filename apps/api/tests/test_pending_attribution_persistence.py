from test_database_persistence import FakeSnapshotRepository

from app.core.persistence import PersistentMemoryStore


def test_pending_attribution_items_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.pending_attribution_items = {
        "pending_attr_010": {
            "id": "pending_attr_010",
            "source_type": "user_feedback",
            "source_system": "feedback-api",
            "collector_run_id": None,
            "raw_subject_id": "feedback-ext-42",
            "summary": "Cannot map module",
            "raw_payload": {"module_hint": "search-v2"},
            "suggested_product_id": None,
            "suggested_module_code": "search",
            "confidence": 0.44,
            "status": "pending",
            "resolution_action": None,
            "resolution_note": None,
            "resolved_product_id": None,
            "resolved_module_code": None,
            "resolved_requirement_id": None,
            "resolved_subject_type": None,
            "resolved_subject_id": None,
            "resolved_by": None,
            "resolved_at": None,
            "created_by": "user_admin",
            "created_at": "2026-06-02T05:30:00+00:00",
            "updated_at": "2026-06-02T05:30:00+00:00",
        }
    }

    store.persist()

    assert repository.pending_attribution_payload == {
        "pending_attribution_items": store.pending_attribution_items
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.pending_attribution_payload = {
        "pending_attribution_items": store.pending_attribution_items
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.pending_attribution_items["pending_attr_010"]["source_type"] == (
        "user_feedback"
    )
    assert rebuilt_store.new_id("pending_attr") == "pending_attr_011"


def test_pending_attribution_persistence_clears_stale_context_references():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.pending_attribution_items = {
        "pending_attr_010": {
            "id": "pending_attr_010",
            "source_type": "user_feedback",
            "source_system": "feedback-api",
            "collector_run_id": "collector_run_missing",
            "raw_subject_id": "feedback-ext-42",
            "summary": "Cannot map module",
            "raw_payload": {"module_hint": "search-v2"},
            "suggested_product_id": "product_missing",
            "suggested_module_code": "search",
            "confidence": 0.44,
            "status": "resolved",
            "resolution_action": "link_existing_context",
            "resolution_note": None,
            "resolved_product_id": "product_missing",
            "resolved_module_code": "search",
            "resolved_requirement_id": "requirement_missing",
            "resolved_subject_type": "user_feedback",
            "resolved_subject_id": "feedback_001",
            "resolved_by": "user_admin",
            "resolved_at": "2026-06-02T05:35:00+00:00",
            "created_by": "user_admin",
            "created_at": "2026-06-02T05:30:00+00:00",
            "updated_at": "2026-06-02T05:35:00+00:00",
        }
    }

    store.persist()

    item = repository.pending_attribution_payload["pending_attribution_items"][
        "pending_attr_010"
    ]
    assert item["collector_run_id"] is None
    assert item["suggested_product_id"] is None
    assert item["suggested_module_code"] is None
    assert item["resolved_product_id"] is None
    assert item["resolved_module_code"] is None
    assert item["resolved_requirement_id"] is None
