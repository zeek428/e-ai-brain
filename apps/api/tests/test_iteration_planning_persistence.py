from test_database_persistence import FakeSnapshotRepository

from app.core.persistence import PersistentMemoryStore


def test_iteration_planning_is_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "planning-product",
            "id": "product_001",
            "name": "规划产品",
            "status": "active",
        }
    }
    store.product_versions = {
        "version_001": {
            "code": "2026Q3",
            "id": "version_001",
            "name": "2026 Q3",
            "product_id": "product_001",
            "status": "planning",
        }
    }
    store.iteration_plan_suggestions = {
        "suggestion_010": {
            "business_value": "提升知识复用效率。",
            "confidence_level": "medium",
            "created_at": "2026-06-01T08:00:00+00:00",
            "created_by": "user_admin",
            "dependencies": ["排序评估"],
            "estimated_effort": "medium",
            "evidence": [
                {
                    "subject_id": "feedback_001",
                    "subject_type": "user_feedback",
                    "summary": "检索不准",
                }
            ],
            "evidence_insufficient": False,
            "id": "suggestion_010",
            "module_codes": ["knowledge"],
            "planning_cycle": "2026Q3",
            "priority": "P1",
            "priority_score": 76,
            "product_id": "product_001",
            "recommendation_reason": "用户反馈集中在检索相关性。",
            "risk_signals": ["user_feedback_signal"],
            "status": "accepted",
            "title": "优化知识检索",
            "updated_at": "2026-06-01T08:05:00+00:00",
            "version_id": "version_001",
        }
    }
    store.iteration_plan_decisions = {
        "iteration_decision_010": {
            "comment": "采纳。",
            "convert_to_requirement": False,
            "decided_at": "2026-06-01T08:06:00+00:00",
            "decided_by": "user_admin",
            "decision": "accepted",
            "id": "iteration_decision_010",
            "suggestion_id": "suggestion_010",
        }
    }

    store.persist()

    assert repository.iteration_planning_payload == {
        "iteration_plan_decisions": store.iteration_plan_decisions,
        "iteration_plan_suggestions": store.iteration_plan_suggestions,
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": store.product_versions,
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.iteration_planning_payload = {
        "iteration_plan_decisions": store.iteration_plan_decisions,
        "iteration_plan_suggestions": {
            "suggestion_011": {
                **store.iteration_plan_suggestions["suggestion_010"],
                "id": "suggestion_011",
                "status": "rejected",
            }
        },
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.iteration_plan_suggestions["suggestion_011"]["status"] == "rejected"
    assert rebuilt_store.new_id("suggestion") == "suggestion_012"
    assert rebuilt_store.new_id("iteration_decision") == "iteration_decision_011"

