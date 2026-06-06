from test_database_persistence import FakeSnapshotRepository

from app.core.persistence import PersistentMemoryStore


def test_workflow_runtime_is_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.ai_tasks["task_012"] = {
        "created_by": "user_admin",
        "current_step": "interrupt_for_human_review",
        "graph_run_ids": ["graph_run_004"],
        "id": "task_012",
        "input_json": {},
        "module_code": None,
        "output_json": {"kind": "product_detail_design", "summary": "结构表输出"},
        "product_context": {},
        "product_id": "product_001",
        "requirement_id": "requirement_001",
        "requirement_snapshot": {"id": "requirement_001"},
        "review_ids": ["review_006"],
        "status": "waiting_review",
        "task_type": "product_detail_design",
        "title": "产品详细设计：结构表验证",
        "version_id": "version_001",
    }
    current_store.graph_runs["graph_run_004"] = {
        "ai_task_id": "task_012",
        "checkpoint_id": "checkpoint_005",
        "completed_at": None,
        "current_step": "interrupt_for_human_review",
        "id": "graph_run_004",
        "started_at": "2026-05-31T10:00:00+00:00",
        "state_snapshot": {"review_id": "review_006", "task_status": "waiting_review"},
        "status": "interrupted",
        "task_type": "product_detail_design",
    }
    current_store.graph_checkpoints["checkpoint_005"] = {
        "ai_task_id": "task_012",
        "created_at": "2026-05-31T10:00:01+00:00",
        "current_step": "interrupt_for_human_review",
        "graph_run_id": "graph_run_004",
        "id": "checkpoint_005",
        "state_snapshot": {"review_id": "review_006", "task_status": "waiting_review"},
    }
    current_store.human_reviews["review_006"] = {
        "ai_task_id": "task_012",
        "content": {"kind": "product_detail_design", "summary": "结构表输出"},
        "id": "review_006",
        "stage": "product_detail_design",
        "status": "pending",
        "version": 1,
    }

    current_store.persist()

    assert repository.workflow_runtime_payload is not None
    assert repository.workflow_runtime_payload["graph_runs"]["graph_run_004"]["status"] == (
        "interrupted"
    )
    assert repository.workflow_runtime_payload["graph_checkpoints"]["checkpoint_005"][
        "graph_run_id"
    ] == "graph_run_004"
    assert repository.workflow_runtime_payload["human_reviews"]["review_006"]["status"] == (
        "pending"
    )

    repository.payload = {
        "ai_tasks": {
            "task_012": {
                "created_by": "user_admin",
                "current_step": "draft",
                "graph_run_ids": [],
                "id": "task_012",
                "input_json": {},
                "module_code": None,
                "output_json": None,
                "product_context": {},
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "requirement_snapshot": {"id": "requirement_001"},
                "review_ids": [],
                "status": "draft",
                "task_type": "product_detail_design",
                "title": "产品详细设计：结构表验证",
                "version_id": "version_001",
            }
        },
        "counters": {},
    }
    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.human_reviews["review_006"]["content"]["summary"] == "结构表输出"
    assert rebuilt_store.graph_runs["graph_run_004"]["checkpoint_id"] == "checkpoint_005"
    assert rebuilt_store.graph_checkpoints["checkpoint_005"]["current_step"] == (
        "interrupt_for_human_review"
    )
    assert rebuilt_store.ai_tasks["task_012"]["review_ids"] == ["review_006"]
    assert rebuilt_store.ai_tasks["task_012"]["graph_run_ids"] == ["graph_run_004"]
    assert rebuilt_store.ai_tasks["task_012"]["checkpoint_id"] == "checkpoint_005"
    assert rebuilt_store.new_id("review") == "review_007"
    assert rebuilt_store.new_id("graph_run") == "graph_run_005"
    assert rebuilt_store.new_id("checkpoint") == "checkpoint_006"


def test_empty_workflow_runtime_tables_ignore_snapshot_runtime_data():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "graph_checkpoints": {
            "checkpoint_001": {
                "ai_task_id": "task_001",
                "created_at": "2026-05-31T10:00:01+00:00",
                "current_step": "interrupt_for_human_review",
                "graph_run_id": "graph_run_001",
                "id": "checkpoint_001",
                "state_snapshot": {"review_id": "review_001"},
            }
        },
        "graph_runs": {
            "graph_run_001": {
                "ai_task_id": "task_001",
                "checkpoint_id": "checkpoint_001",
                "completed_at": None,
                "current_step": "interrupt_for_human_review",
                "id": "graph_run_001",
                "started_at": "2026-05-31T10:00:00+00:00",
                "state_snapshot": {"review_id": "review_001"},
                "status": "interrupted",
                "task_type": "product_detail_design",
            }
        },
        "human_reviews": {
            "review_001": {
                "ai_task_id": "task_001",
                "content": {"summary": "快照 Review"},
                "id": "review_001",
                "stage": "product_detail_design",
                "status": "pending",
                "version": 1,
            }
        },
        "counters": {"checkpoint": 1, "graph_run": 1, "review": 1},
    }
    repository.workflow_runtime_payload = {
        "graph_checkpoints": {},
        "graph_runs": {},
        "human_reviews": {},
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.human_reviews == {}
    assert rebuilt_store.graph_runs == {}
    assert rebuilt_store.graph_checkpoints == {}


def test_orphan_snapshot_workflow_runtime_is_ignored_after_structured_task_migration():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "graph_checkpoints": {
            "checkpoint_009": {
                "ai_task_id": "task_missing",
                "created_at": "2026-05-31T10:00:01+00:00",
                "current_step": "interrupt_for_human_review",
                "graph_run_id": "graph_run_009",
                "id": "checkpoint_009",
                "state_snapshot": {},
            }
        },
        "graph_runs": {
            "graph_run_009": {
                "ai_task_id": "task_missing",
                "checkpoint_id": "checkpoint_009",
                "completed_at": None,
                "current_step": "interrupt_for_human_review",
                "id": "graph_run_009",
                "started_at": "2026-05-31T10:00:00+00:00",
                "state_snapshot": {},
                "status": "interrupted",
                "task_type": "product_detail_design",
            }
        },
        "human_reviews": {
            "review_009": {
                "ai_task_id": "task_missing",
                "content": {},
                "id": "review_009",
                "stage": "product_detail_design",
                "status": "pending",
                "version": 1,
            }
        },
        "counters": {"checkpoint": 9, "graph_run": 9, "review": 9},
    }
    repository.ai_tasks_payload = {
        "ai_tasks": {
            "task_001": {
                "created_by": "user_admin",
                "current_step": "draft",
                "id": "task_001",
                "input_json": {},
                "module_code": None,
                "output_json": None,
                "product_context": {},
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "requirement_snapshot": {"id": "requirement_001"},
                "status": "draft",
                "task_type": "product_detail_design",
                "title": "结构表任务",
                "version_id": "version_001",
            }
        }
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    rebuilt_store.persist()

    assert rebuilt_store.graph_runs == {}
    assert rebuilt_store.graph_checkpoints == {}
    assert rebuilt_store.human_reviews == {}
    assert repository.workflow_runtime_payload == {
        "graph_checkpoints": {},
        "graph_runs": {},
        "human_reviews": {},
    }
    assert rebuilt_store.new_id("review") == "review_001"
