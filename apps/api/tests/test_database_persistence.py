from fastapi.testclient import TestClient

from app.core.persistence import PersistentMemoryStore
from app.core.security import hash_password
from app.core.store import MemoryStore
from app.core.users import MemoryUserRepository
from app.main import app

client = TestClient(app)


class FakeSnapshotRepository:
    def __init__(self) -> None:
        self.payload: dict | None = None
        self.product_config_payload: dict | None = None
        self.requirements_payload: dict | None = None
        self.ai_tasks_payload: dict | None = None
        self.workflow_runtime_payload: dict | None = None

    def load(self) -> dict | None:
        return self.payload

    def save(self, payload: dict) -> None:
        self.payload = payload

    def load_product_config(self) -> dict | None:
        return self.product_config_payload

    def save_product_config(self, payload: dict) -> None:
        self.product_config_payload = payload

    def load_requirements(self) -> dict | None:
        return self.requirements_payload

    def save_requirements(self, payload: dict) -> None:
        self.requirements_payload = payload

    def load_ai_tasks(self) -> dict | None:
        return self.ai_tasks_payload

    def save_ai_tasks(self, payload: dict) -> None:
        self.ai_tasks_payload = payload

    def load_workflow_runtime(self) -> dict | None:
        return self.workflow_runtime_payload

    def save_workflow_runtime(self, payload: dict) -> None:
        self.workflow_runtime_payload = payload


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_business_state_survives_store_rebuild_from_database_snapshot():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "REAL-DB", "name": "真实数据库产品"},
            headers=headers,
        ).json()["data"]

        app.state.store = PersistentMemoryStore.from_repository(repository)

        products = client.get("/api/products", headers=headers).json()["data"]["items"]
        assert [item["id"] for item in products] == [product["id"]]
        assert products[0]["code"] == "REAL-DB"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_product_config_is_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.products["product_019"] = {
        "code": "TABLE-PRODUCT",
        "description": "写入结构化产品表",
        "display_order": 7,
        "id": "product_019",
        "name": "结构化产品",
        "owner_team": "AI Team",
        "status": "active",
    }
    current_store.product_versions["version_003"] = {
        "code": "v1",
        "description": "结构化版本",
        "id": "version_003",
        "name": "v1",
        "product_id": "product_019",
        "release_date": "2026-06-30",
        "start_date": "2026-06-01",
        "status": "active",
    }
    current_store.product_modules["module_002"] = {
        "code": "core",
        "description": "结构化模块",
        "display_order": 3,
        "id": "module_002",
        "name": "核心模块",
        "owner_team": "Platform",
        "product_id": "product_019",
        "status": "active",
    }
    current_store.product_git_repositories["repo_004"] = {
        "credential_ref": "env:GITLAB_READONLY_TOKEN",
        "default_branch": "main",
        "git_provider": "gitlab",
        "id": "repo_004",
        "name": "核心仓库",
        "product_id": "product_019",
        "project_id": "42",
        "project_path": "platform/core",
        "remote_url": "https://gitlab.example.com/platform/core.git",
        "repo_type": "code",
        "root_path": "/",
        "status": "active",
    }

    current_store.persist()

    assert repository.product_config_payload is not None
    assert repository.product_config_payload["products"]["product_019"]["code"] == "TABLE-PRODUCT"
    assert repository.product_config_payload["product_versions"]["version_003"]["product_id"] == (
        "product_019"
    )
    assert repository.product_config_payload["product_modules"]["module_002"]["code"] == "core"
    assert repository.product_config_payload["product_git_repositories"]["repo_004"][
        "project_path"
    ] == "platform/core"

    repository.payload = {"products": {}, "product_versions": {}, "counters": {}}
    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.products["product_019"]["name"] == "结构化产品"
    assert rebuilt_store.product_versions["version_003"]["name"] == "v1"
    assert rebuilt_store.product_modules["module_002"]["owner_team"] == "Platform"
    assert rebuilt_store.product_git_repositories["repo_004"]["credential_ref"] == (
        "env:GITLAB_READONLY_TOKEN"
    )
    assert rebuilt_store.new_id("product") == "product_020"


def test_empty_product_config_tables_do_not_erase_snapshot_product_data():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "counters": {"product": 1},
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {},
        "products": {
            "product_001": {
                "code": "SNAPSHOT-PRODUCT",
                "description": None,
                "display_order": 0,
                "id": "product_001",
                "name": "快照产品",
                "owner_team": None,
                "status": "active",
            }
        },
    }
    repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {},
        "products": {},
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.products["product_001"]["code"] == "SNAPSHOT-PRODUCT"


def test_product_config_tables_merge_snapshot_records_during_structured_migration():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "counters": {"product": 11, "requirement": 3, "version": 5},
        "product_versions": {
            "version_005": {
                "code": "v1",
                "description": None,
                "id": "version_005",
                "name": "v1",
                "product_id": "product_011",
                "release_date": None,
                "start_date": None,
                "status": "active",
            }
        },
        "products": {
            "product_011": {
                "code": "SNAPSHOT-ONLY",
                "description": None,
                "display_order": 0,
                "id": "product_011",
                "name": "仅在快照中的产品",
                "owner_team": None,
                "status": "active",
            }
        },
        "requirements": {
            "requirement_003": {
                "content": "引用尚未迁移到结构表的产品",
                "created_at": "2026-05-31T10:00:00+00:00",
                "created_by": "user_admin",
                "id": "requirement_003",
                "module_code": None,
                "priority": "P1",
                "product_id": "product_011",
                "status": "pending_approval",
                "task_ids": [],
                "title": "快照迁移需求",
                "version_id": "version_005",
            }
        },
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

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    rebuilt_store.persist()

    assert rebuilt_store.products["product_001"]["code"] == "TABLE-ONLY"
    assert rebuilt_store.products["product_011"]["code"] == "SNAPSHOT-ONLY"
    assert rebuilt_store.product_versions["version_005"]["product_id"] == "product_011"
    assert repository.product_config_payload["products"]["product_011"]["name"] == (
        "仅在快照中的产品"
    )
    assert repository.requirements_payload["requirements"]["requirement_003"]["product_id"] == (
        "product_011"
    )


def test_orphan_snapshot_requirements_are_ignored_after_structured_product_migration():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "counters": {"requirement": 9},
        "products": {},
        "product_versions": {},
        "requirements": {
            "requirement_009": {
                "content": "已经失去产品上下文的历史需求",
                "created_at": "2026-05-31T10:00:00+00:00",
                "created_by": "user_admin",
                "id": "requirement_009",
                "module_code": None,
                "priority": "P1",
                "product_id": "product_missing",
                "status": "pending_approval",
                "task_ids": [],
                "title": "孤儿需求",
                "version_id": "version_missing",
            }
        },
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

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    rebuilt_store.persist()

    assert rebuilt_store.requirements == {}
    assert repository.requirements_payload == {"requirements": {}}
    assert rebuilt_store.new_id("requirement") == "requirement_010"


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


def test_empty_requirement_table_does_not_erase_snapshot_requirement_data():
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

    assert rebuilt_store.requirements["requirement_001"]["title"] == "快照需求"


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


def test_empty_ai_task_table_does_not_erase_snapshot_task_data():
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

    assert rebuilt_store.ai_tasks["task_001"]["title"] == "快照任务"


def test_structured_ai_task_load_preserves_snapshot_runtime_links():
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
    assert rebuilt_store.ai_tasks["task_012"]["review_ids"] == ["review_002"]
    assert rebuilt_store.ai_tasks["task_012"]["graph_run_ids"] == ["graph_run_002"]
    assert rebuilt_store.ai_tasks["task_012"]["checkpoint_id"] == "checkpoint_003"


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
    assert rebuilt_store.new_id("task") == "task_010"


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


def test_empty_workflow_runtime_tables_do_not_erase_snapshot_runtime_data():
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

    assert rebuilt_store.human_reviews["review_001"]["content"]["summary"] == "快照 Review"
    assert rebuilt_store.graph_runs["graph_run_001"]["checkpoint_id"] == "checkpoint_001"


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
    assert rebuilt_store.new_id("review") == "review_010"


def test_product_config_api_writes_fine_grained_repository_payload():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "TABLE-API", "name": "结构表 API 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1"},
            headers=headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "core", "name": "核心模块"},
            headers=headers,
        ).json()["data"]
        repository_record = client.post(
            f"/api/products/{product['id']}/git-repositories",
            json={
                "name": "AI Brain API",
                "project_id": "42",
                "project_path": "platform/e-ai-brain",
            },
            headers=headers,
        ).json()["data"]

        assert repository.product_config_payload is not None
        assert repository.product_config_payload["products"][product["id"]]["code"] == "TABLE-API"
        assert repository.product_config_payload["product_versions"][version["id"]]["name"] == "v1"
        assert repository.product_config_payload["product_modules"][module["id"]]["code"] == "core"
        assert repository.product_config_payload["product_git_repositories"][
            repository_record["id"]
        ]["project_path"] == "platform/e-ai-brain"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_requirement_api_writes_fine_grained_repository_payload():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "REQ-TABLE-API", "name": "需求结构表 API 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1"},
            headers=headers,
        ).json()["data"]

        requirement = client.post(
            "/api/requirements",
            json={
                "content": "API 创建后必须落到 requirements 表",
                "priority": "P0",
                "product_id": product["id"],
                "title": "需求结构表 API 验证",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]

        assert repository.requirements_payload is not None
        persisted = repository.requirements_payload["requirements"][requirement["id"]]
        assert persisted["title"] == "需求结构表 API 验证"
        assert persisted["product_id"] == product["id"]
        assert persisted["version_id"] == version["id"]
        assert persisted["status"] == "pending_approval"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_ai_task_api_writes_fine_grained_repository_payload():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "TASK-TABLE-API", "name": "任务结构表 API 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "生成任务后必须落到 ai_tasks 表",
                "priority": "P0",
                "product_id": product["id"],
                "title": "任务结构表 API 验证",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "通过"},
            headers=headers,
        )

        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]

        assert repository.ai_tasks_payload is not None
        persisted = repository.ai_tasks_payload["ai_tasks"][generated["task_id"]]
        assert persisted["task_type"] == "product_detail_design"
        assert persisted["requirement_id"] == requirement["id"]
        assert persisted["product_id"] == product["id"]
        assert persisted["status"] == "draft"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_ai_task_start_and_review_update_write_workflow_runtime_payload():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "WORKFLOW-TABLE-API", "name": "流程结构表 API 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "启动任务后 Review 和 Graph 必须落到结构表",
                "priority": "P0",
                "product_id": product["id"],
                "title": "流程结构表 API 验证",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "通过"},
            headers=headers,
        )
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]

        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]

        assert repository.workflow_runtime_payload is not None
        assert started["graph_run_id"] in repository.workflow_runtime_payload["graph_runs"]
        assert started["checkpoint_id"] in repository.workflow_runtime_payload["graph_checkpoints"]
        assert started["review_id"] in repository.workflow_runtime_payload["human_reviews"]
        assert repository.workflow_runtime_payload["human_reviews"][started["review_id"]][
            "status"
        ] == "pending"

        client.post(
            f"/api/reviews/{started['review_id']}/approve",
            json={"version": 1},
            headers=headers,
        )

        assert repository.workflow_runtime_payload["human_reviews"][started["review_id"]][
            "status"
        ] == "approved"
        assert repository.workflow_runtime_payload["graph_runs"][started["graph_run_id"]][
            "status"
        ] == "completed"
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_login_uses_user_repository_instead_of_hardcoded_seed_users():
    original_store = app.state.store
    original_users = app.state.user_repository
    app.state.store = MemoryStore()
    app.state.user_repository = MemoryUserRepository(
        {
            "db_user@example.com": {
                "display_name": "DB User",
                "id": "user_db",
                "password_hash": hash_password("db-secret", salt="db-user-salt"),
                "roles": ["product_owner"],
                "status": "active",
                "username": "db_user@example.com",
            }
        }
    )

    try:
        response = client.post(
            "/api/auth/login",
            json={"username": "db_user@example.com", "password": "db-secret"},
        )
        assert response.status_code == 200
        token = response.json()["data"]["access_token"]

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["data"]["username"] == "db_user@example.com"

        seeded_login = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
        assert seeded_login.status_code == 401
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_admin_can_manage_users_through_repository():
    original_store = app.state.store
    original_users = app.state.user_repository
    app.state.store = MemoryStore()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        created = client.post(
            "/api/users",
            json={
                "display_name": "真实系统用户",
                "password": "real-secret",
                "roles": ["product_owner"],
                "status": "active",
                "username": "real_user@example.com",
            },
            headers=headers,
        )
        assert created.status_code == 200
        user_id = created.json()["data"]["id"]

        updated = client.patch(
            f"/api/users/{user_id}",
            json={"roles": ["reviewer"], "display_name": "真实系统 Reviewer"},
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["roles"] == ["reviewer"]

        listed = client.get("/api/users", headers=headers)
        assert listed.status_code == 200
        assert any(
            item["username"] == "real_user@example.com"
            and item["display_name"] == "真实系统 Reviewer"
            for item in listed.json()["data"]["items"]
        )

        login = client.post(
            "/api/auth/login",
            json={"username": "real_user@example.com", "password": "real-secret"},
        )
        assert login.status_code == 200
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
