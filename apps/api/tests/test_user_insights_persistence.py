from test_database_persistence import FakeSnapshotRepository

from app.core.persistence import PersistentMemoryStore


def test_user_feedback_is_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "feedback-product",
            "id": "product_001",
            "name": "反馈产品",
            "status": "active",
        }
    }
    store.product_modules = {
        "module_001": {
            "code": "knowledge",
            "id": "module_001",
            "name": "知识中心",
            "product_id": "product_001",
            "status": "active",
        }
    }
    store.user_feedback = {
        "feedback_010": {
            "content": "知识检索相关性不足。",
            "created_at": "2026-06-01T08:00:00+00:00",
            "created_by": "user_reviewer",
            "feature_code": "search",
            "feedback_type": "improvement",
            "id": "feedback_010",
            "module_code": "knowledge",
            "product_id": "product_001",
            "satisfaction_score": 2,
            "sentiment": "negative",
            "source_channel": "in_app",
            "status": "triaged",
            "tags": ["search"],
            "triage_note": "进入知识检索优化池。",
            "updated_at": "2026-06-01T08:10:00+00:00",
        }
    }

    store.persist()

    assert repository.user_feedback_payload == {"user_feedback": store.user_feedback}

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": store.product_modules,
        "product_versions": {},
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.user_feedback_payload = {
        "user_feedback": {
            "feedback_011": {
                **store.user_feedback["feedback_010"],
                "id": "feedback_011",
                "status": "resolved",
            }
        }
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.user_feedback["feedback_011"]["status"] == "resolved"
    assert rebuilt_store.new_id("feedback") == "feedback_012"



def test_user_usage_metrics_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "usage-product",
            "id": "product_001",
            "name": "使用指标产品",
            "status": "active",
        }
    }
    store.user_usage_metrics = {
        "usage_010": {
            "active_users": 10,
            "avg_duration_seconds": 28.5,
            "bounce_rate": 0.2,
            "conversion_count": 3,
            "conversion_rate": 0.3,
            "created_at": "2026-06-01T08:00:00+00:00",
            "created_by": "user_admin",
            "error_count": 1,
            "event_count": 40,
            "feature_code": "semantic-search",
            "id": "usage_010",
            "module_code": "search",
            "product_id": "product_001",
            "source_channel": "manual_import",
            "updated_at": "2026-06-01T08:05:00+00:00",
            "user_segment": "rd",
            "window_end": "2026-06-01T01:00:00+00:00",
            "window_start": "2026-06-01T00:00:00+00:00",
        }
    }

    store.persist()

    assert repository.user_usage_metrics_payload == {
        "user_usage_metrics": store.user_usage_metrics,
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {},
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.user_usage_metrics_payload = {
        "user_usage_metrics": store.user_usage_metrics,
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.user_usage_metrics["usage_010"]["feature_code"] == "semantic-search"
    assert rebuilt_store.new_id("usage") == "usage_011"


