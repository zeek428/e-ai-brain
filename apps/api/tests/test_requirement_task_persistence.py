from test_database_persistence import FakeSnapshotRepository

from app.core.persistence import PersistentMemoryStore


def test_requirements_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.requirements["requirement_007"] = {
        "approval_comment": "通过",
        "content": "把需求写入结构化 requirements 表",
        "created_at": "2026-05-31T10:00:00+00:00",
        "created_by": "user_admin",
        "id": "requirement_007",
        "module_code": "core",
        "priority": "P0",
        "product_id": "product_001",
        "rejection_reason": None,
        "status": "approved",
        "task_ids": ["task_001"],
        "title": "结构化需求持久化",
        "updated_at": "2026-05-31T10:30:00+00:00",
        "version_id": "version_001",
    }

    current_store.persist()

    assert repository.requirements_payload is not None
    assert repository.requirements_payload["requirements"]["requirement_007"]["title"] == (
        "结构化需求持久化"
    )
    assert repository.requirements_payload["requirements"]["requirement_007"]["task_ids"] == [
        "task_001"
    ]

    repository.payload = {"counters": {}, "requirements": {}}
    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.requirements["requirement_007"]["content"] == (
        "把需求写入结构化 requirements 表"
    )
    assert rebuilt_store.new_id("requirement") == "requirement_008"


def test_empty_requirement_table_ignores_snapshot_requirement_data():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "counters": {"requirement": 1},
        "requirements": {
            "requirement_001": {
                "content": "来自旧快照的需求",
                "created_at": "2026-05-31T10:00:00+00:00",
                "created_by": "user_admin",
                "id": "requirement_001",
                "module_code": None,
                "priority": "P1",
                "product_id": "product_001",
                "status": "pending_approval",
                "task_ids": [],
                "title": "快照需求",
                "version_id": "version_001",
            }
        },
    }
    repository.requirements_payload = {"requirements": {}}

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.requirements == {}


def test_ai_tasks_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.products["product_001"] = {
        "code": "TASK-PRODUCT",
        "description": None,
        "display_order": 0,
        "id": "product_001",
        "name": "任务产品",
        "owner_team": None,
        "status": "active",
    }
    current_store.product_versions["version_001"] = {
        "code": "v1",
        "description": None,
        "id": "version_001",
        "name": "v1",
        "product_id": "product_001",
        "release_date": None,
        "start_date": None,
        "status": "active",
    }
    current_store.requirements["requirement_001"] = {
        "content": "任务结构表验证需求",
        "created_at": "2026-05-31T10:00:00+00:00",
        "created_by": "user_admin",
        "id": "requirement_001",
        "module_code": "core",
        "priority": "P0",
        "product_id": "product_001",
        "status": "task_created",
        "task_ids": ["task_012"],
        "title": "任务结构表验证",
        "version_id": "version_001",
    }
    current_store.ai_tasks["task_012"] = {
        "checkpoint_id": "checkpoint_003",
        "created_by": "user_admin",
        "current_step": "interrupt_for_human_review",
        "error_code": None,
        "error_message": None,
        "graph_run_ids": ["graph_run_002"],
        "id": "task_012",
        "input_json": {"product_detail_design_task_id": "task_001"},
        "module_code": "core",
        "output_json": {"kind": "technical_solution", "summary": "结构表输出"},
        "product_context": {"product": {"id": "product_001"}},
        "product_id": "product_001",
        "requirement_id": "requirement_001",
        "requirement_snapshot": {"id": "requirement_001", "title": "任务结构表验证"},
        "review_ids": ["review_002"],
        "status": "waiting_review",
        "task_type": "technical_solution",
        "title": "技术方案：任务结构表验证",
        "version_id": "version_001",
    }

    current_store.persist()

    assert repository.ai_tasks_payload is not None
    persisted = repository.ai_tasks_payload["ai_tasks"]["task_012"]
    assert persisted["title"] == "技术方案：任务结构表验证"
    assert persisted["output_json"]["summary"] == "结构表输出"
    assert persisted["input_json"]["product_detail_design_task_id"] == "task_001"

    repository.payload = {
        "ai_tasks": {
            "task_012": {
                "checkpoint_id": "checkpoint_003",
                "graph_run_ids": ["graph_run_002"],
                "review_ids": ["review_002"],
            }
        },
        "counters": {},
    }
    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.ai_tasks["task_012"]["title"] == "技术方案：任务结构表验证"
    assert rebuilt_store.ai_tasks["task_012"]["review_ids"] == ["review_002"]
    assert rebuilt_store.ai_tasks["task_012"]["graph_run_ids"] == ["graph_run_002"]
    assert rebuilt_store.ai_tasks["task_012"]["checkpoint_id"] == "checkpoint_003"
    assert rebuilt_store.new_id("task") == "task_013"


def test_empty_ai_task_table_ignores_snapshot_task_data():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "ai_tasks": {
            "task_001": {
                "created_by": "user_admin",
                "current_step": "draft",
                "graph_run_ids": [],
                "id": "task_001",
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
                "title": "快照任务",
                "version_id": "version_001",
            }
        },
        "counters": {"task": 1},
    }
    repository.ai_tasks_payload = {"ai_tasks": {}}

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.ai_tasks == {}


def test_structured_ai_task_load_ignores_snapshot_runtime_links():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "ai_tasks": {
            "task_012": {
                "checkpoint_id": "checkpoint_003",
                "graph_run_ids": ["graph_run_002"],
                "review_ids": ["review_002"],
            }
        },
        "counters": {"task": 12},
    }
    repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {
            "version_001": {
                "code": "v1",
                "description": None,
                "id": "version_001",
                "name": "v1",
                "product_id": "product_001",
                "release_date": None,
                "start_date": None,
                "status": "active",
            }
        },
        "products": {
            "product_001": {
                "code": "TASK-PRODUCT",
                "description": None,
                "display_order": 0,
                "id": "product_001",
                "name": "任务产品",
                "owner_team": None,
                "status": "active",
            }
        },
    }
    repository.requirements_payload = {
        "requirements": {
            "requirement_001": {
                "content": "任务结构表验证需求",
                "created_at": "2026-05-31T10:00:00+00:00",
                "created_by": "user_admin",
                "id": "requirement_001",
                "module_code": "core",
                "priority": "P0",
                "product_id": "product_001",
                "status": "task_created",
                "task_ids": ["task_012"],
                "title": "任务结构表验证",
                "version_id": "version_001",
            }
        }
    }
    repository.ai_tasks_payload = {
        "ai_tasks": {
            "task_012": {
                "created_by": "user_admin",
                "current_step": "interrupt_for_human_review",
                "id": "task_012",
                "input_json": {},
                "module_code": "core",
                "output_json": {"kind": "product_detail_design"},
                "product_context": {"product": {"id": "product_001"}},
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "requirement_snapshot": {"id": "requirement_001"},
                "graph_run_ids": [],
                "review_ids": [],
                "status": "waiting_review",
                "task_type": "product_detail_design",
                "title": "结构表任务",
                "version_id": "version_001",
            }
        }
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.ai_tasks["task_012"]["title"] == "结构表任务"
    assert rebuilt_store.ai_tasks["task_012"]["review_ids"] == []
    assert rebuilt_store.ai_tasks["task_012"]["graph_run_ids"] == []
    assert "checkpoint_id" not in rebuilt_store.ai_tasks["task_012"]


def test_orphan_snapshot_ai_tasks_are_ignored_after_structured_context_migration():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "ai_tasks": {
            "task_009": {
                "created_by": "user_admin",
                "current_step": "draft",
                "graph_run_ids": [],
                "id": "task_009",
                "input_json": {},
                "module_code": None,
                "output_json": None,
                "product_context": {},
                "product_id": "product_missing",
                "requirement_id": "requirement_missing",
                "requirement_snapshot": {"id": "requirement_missing"},
                "review_ids": [],
                "status": "draft",
                "task_type": "product_detail_design",
                "title": "孤儿任务",
                "version_id": "version_missing",
            }
        },
        "counters": {"task": 9},
    }
    repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {
            "version_001": {
                "code": "v1",
                "description": None,
                "id": "version_001",
                "name": "v1",
                "product_id": "product_001",
                "release_date": None,
                "start_date": None,
                "status": "active",
            }
        },
        "products": {
            "product_001": {
                "code": "TABLE-ONLY",
                "description": None,
                "display_order": 0,
                "id": "product_001",
                "name": "结构表产品",
                "owner_team": None,
                "status": "active",
            }
        },
    }
    repository.requirements_payload = {
        "requirements": {
            "requirement_001": {
                "content": "结构表需求",
                "created_at": "2026-05-31T10:00:00+00:00",
                "created_by": "user_admin",
                "id": "requirement_001",
                "module_code": None,
                "priority": "P1",
                "product_id": "product_001",
                "status": "approved",
                "task_ids": [],
                "title": "结构表需求",
                "version_id": "version_001",
            }
        }
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    rebuilt_store.persist()

    assert rebuilt_store.ai_tasks == {}
    assert repository.ai_tasks_payload == {"ai_tasks": {}}
    assert rebuilt_store.new_id("task") == "task_001"
