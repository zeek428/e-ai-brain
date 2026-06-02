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
        self.knowledge_payload: dict | None = None
        self.audit_events_payload: dict | None = None
        self.bugs_payload: dict | None = None
        self.model_gateway_payload: dict | None = None
        self.gitlab_review_payload: dict | None = None
        self.mock_writebacks_payload: dict | None = None
        self.gitlab_daily_code_metrics_payload: dict | None = None
        self.jenkins_release_records_payload: dict | None = None
        self.online_log_metrics_payload: dict | None = None
        self.user_usage_metrics_payload: dict | None = None
        self.user_feedback_payload: dict | None = None
        self.iteration_planning_payload: dict | None = None
        self.collector_runs_payload: dict | None = None

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

    def load_knowledge(self) -> dict | None:
        return self.knowledge_payload

    def save_knowledge(self, payload: dict) -> None:
        self.knowledge_payload = payload

    def load_audit_events(self) -> dict | None:
        return self.audit_events_payload

    def save_audit_events(self, payload: dict) -> None:
        self.audit_events_payload = payload

    def load_bugs(self) -> dict | None:
        return self.bugs_payload

    def save_bugs(self, payload: dict) -> None:
        self.bugs_payload = payload

    def load_model_gateway(self) -> dict | None:
        return self.model_gateway_payload

    def save_model_gateway(self, payload: dict) -> None:
        self.model_gateway_payload = payload

    def load_gitlab_review(self) -> dict | None:
        return self.gitlab_review_payload

    def save_gitlab_review(self, payload: dict) -> None:
        self.gitlab_review_payload = payload

    def load_mock_writebacks(self) -> dict | None:
        return self.mock_writebacks_payload

    def save_mock_writebacks(self, payload: dict) -> None:
        self.mock_writebacks_payload = payload

    def load_gitlab_daily_code_metrics(self) -> dict | None:
        return self.gitlab_daily_code_metrics_payload

    def save_gitlab_daily_code_metrics(self, payload: dict) -> None:
        self.gitlab_daily_code_metrics_payload = payload

    def load_jenkins_release_records(self) -> dict | None:
        return self.jenkins_release_records_payload

    def save_jenkins_release_records(self, payload: dict) -> None:
        self.jenkins_release_records_payload = payload

    def load_online_log_metrics(self) -> dict | None:
        return self.online_log_metrics_payload

    def save_online_log_metrics(self, payload: dict) -> None:
        self.online_log_metrics_payload = payload

    def load_user_feedback(self) -> dict | None:
        return self.user_feedback_payload

    def save_user_feedback(self, payload: dict) -> None:
        self.user_feedback_payload = payload

    def load_user_usage_metrics(self) -> dict | None:
        return self.user_usage_metrics_payload

    def save_user_usage_metrics(self, payload: dict) -> None:
        self.user_usage_metrics_payload = payload

    def load_iteration_planning(self) -> dict | None:
        return self.iteration_planning_payload

    def save_iteration_planning(self, payload: dict) -> None:
        self.iteration_planning_payload = payload

    def load_collector_runs(self) -> dict | None:
        return self.collector_runs_payload

    def save_collector_runs(self, payload: dict) -> None:
        self.collector_runs_payload = payload


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def gitlab_review_context_payload() -> dict:
    return {
        "ai_tasks": {
            "task_002": {
                "created_by": "user_admin",
                "id": "task_002",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "status": "completed",
                "task_type": "technical_solution",
                "title": "Technical solution",
                "version_id": "version_001",
            },
            "task_003": {
                "created_by": "user_admin",
                "id": "task_003",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "status": "waiting_review",
                "task_type": "code_review",
                "title": "Code Review",
                "version_id": "version_001",
            },
        },
        "human_reviews": {
            "review_003": {
                "ai_task_id": "task_003",
                "content": {},
                "id": "review_003",
                "stage": "code_review",
                "status": "pending",
                "version": 1,
            }
        },
        "product_git_repositories": {
            "repo_001": {
                "default_branch": "main",
                "git_provider": "gitlab",
                "id": "repo_001",
                "name": "Main repository",
                "product_id": "product_001",
                "repo_type": "code",
                "root_path": "/",
                "status": "active",
            }
        },
        "product_versions": {
            "version_001": {
                "code": "v1",
                "id": "version_001",
                "name": "Version 1",
                "product_id": "product_001",
                "status": "planning",
            }
        },
        "products": {
            "product_001": {
                "code": "P1",
                "id": "product_001",
                "name": "Product 1",
                "status": "active",
            }
        },
        "requirements": {
            "requirement_001": {
                "created_by": "user_admin",
                "description": "Review requirement",
                "id": "requirement_001",
                "priority": "P1",
                "product_id": "product_001",
                "status": "task_created",
                "task_ids": ["task_002", "task_003"],
                "title": "Review requirement",
                "version_id": "version_001",
            }
        },
    }


def apply_payload_to_store(store: MemoryStore, payload: dict) -> None:
    for field, value in payload.items():
        getattr(store, field).update(value)


def mock_writeback_context_payload() -> dict:
    return {
        "ai_tasks": {
            "task_010": {
                "created_by": "user_admin",
                "id": "task_010",
                "product_id": "product_010",
                "requirement_id": "requirement_010",
                "status": "completed",
                "task_type": "technical_solution",
                "title": "Persist mock writeback",
                "version_id": "version_010",
            }
        },
        "product_versions": {
            "version_010": {
                "code": "v1",
                "id": "version_010",
                "name": "Version 1",
                "product_id": "product_010",
                "status": "planning",
            }
        },
        "products": {
            "product_010": {
                "code": "MOCK",
                "id": "product_010",
                "name": "Mock Product",
                "status": "active",
            }
        },
        "requirements": {
            "requirement_010": {
                "created_by": "user_admin",
                "description": "Persist mock writeback",
                "id": "requirement_010",
                "priority": "P1",
                "product_id": "product_010",
                "status": "task_created",
                "task_ids": ["task_010"],
                "title": "Persist mock writeback",
                "version_id": "version_010",
            }
        },
    }


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
    current_store.related_systems["related_system_002"] = {
        "code": "PAYMENT",
        "description": "结构化相关系统",
        "display_order": 2,
        "id": "related_system_002",
        "name": "支付系统",
        "owner_team": "Business",
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
    assert repository.product_config_payload["related_systems"]["related_system_002"][
        "code"
    ] == "PAYMENT"

    repository.payload = {"products": {}, "product_versions": {}, "counters": {}}
    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.products["product_019"]["name"] == "结构化产品"
    assert rebuilt_store.product_versions["version_003"]["name"] == "v1"
    assert rebuilt_store.product_modules["module_002"]["owner_team"] == "Platform"
    assert rebuilt_store.product_git_repositories["repo_004"]["credential_ref"] == (
        "env:GITLAB_READONLY_TOKEN"
    )
    assert rebuilt_store.related_systems["related_system_002"]["name"] == "支付系统"
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


def test_model_gateway_config_and_logs_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.model_gateway_configs["model_gateway_config_009"] = {
        "api_key": "sk-db-secret",
        "base_url": "https://llm.example.com/v1",
        "default_chat_model": "gpt-real",
        "default_embedding_model": "text-embedding-real",
        "id": "model_gateway_config_009",
        "is_default": True,
        "max_retries": 2,
        "name": "真实模型网关",
        "provider": "openai_compatible",
        "status": "active",
        "timeout_seconds": 45,
    }
    current_store.model_gateway_logs.append(
        {
            "ai_task_id": "task_002",
            "created_at": "2026-05-31T10:00:00+00:00",
            "error": None,
            "id": "model_log_007",
            "latency_ms": 321,
            "model": "gpt-real",
            "model_gateway_config_id": "model_gateway_config_009",
            "provider": "openai_compatible",
            "purpose": "product_detail_design",
            "status": "succeeded",
            "tokens": {"prompt": 10, "completion": 20, "total": 30},
        }
    )

    current_store.persist()

    assert repository.model_gateway_payload == {
        "model_gateway_configs": {
            "model_gateway_config_009": {
                "api_key": "sk-db-secret",
                "base_url": "https://llm.example.com/v1",
                "default_chat_model": "gpt-real",
                "default_embedding_model": "text-embedding-real",
                "id": "model_gateway_config_009",
                "is_default": True,
                "max_retries": 2,
                "name": "真实模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 45,
            }
        },
        "model_gateway_logs": [
            {
                "ai_task_id": "task_002",
                "created_at": "2026-05-31T10:00:00+00:00",
                "error": None,
                "id": "model_log_007",
                "latency_ms": 321,
                "model": "gpt-real",
                "model_gateway_config_id": "model_gateway_config_009",
                "provider": "openai_compatible",
                "purpose": "product_detail_design",
                "status": "succeeded",
                "tokens": {"prompt": 10, "completion": 20, "total": 30},
            }
        ],
    }


def test_structured_model_gateway_restore_and_sync_counters():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "model_gateway_configs": {
            "model_gateway_config_002": {
                "api_key": "snapshot-secret",
                "base_url": "https://snapshot.example.com/v1",
                "default_chat_model": "snapshot-chat",
                "default_embedding_model": "snapshot-embedding",
                "id": "model_gateway_config_002",
                "is_default": True,
                "max_retries": 1,
                "name": "旧快照模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 60,
            }
        },
        "model_gateway_logs": [
            {
                "ai_task_id": "task_001",
                "id": "model_log_002",
                "model": "snapshot-chat",
                "provider": "openai_compatible",
                "purpose": "product_detail_design",
                "status": "succeeded",
                "tokens": {},
            }
        ],
    }
    repository.model_gateway_payload = {
        "model_gateway_configs": {
            "model_gateway_config_009": {
                "api_key": "structured-secret",
                "base_url": "https://structured.example.com/v1",
                "default_chat_model": "structured-chat",
                "default_embedding_model": "structured-embedding",
                "id": "model_gateway_config_009",
                "is_default": True,
                "max_retries": 2,
                "name": "结构表模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            }
        },
        "model_gateway_logs": [
            {
                "ai_task_id": "task_002",
                "id": "model_log_007",
                "model": "structured-chat",
                "provider": "openai_compatible",
                "purpose": "product_detail_design",
                "status": "succeeded",
                "tokens": {"total": 33},
            }
        ],
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert list(rebuilt_store.model_gateway_configs) == ["model_gateway_config_009"]
    assert rebuilt_store.model_gateway_configs["model_gateway_config_009"]["api_key"] == (
        "structured-secret"
    )
    assert [log["id"] for log in rebuilt_store.model_gateway_logs] == ["model_log_007"]
    assert rebuilt_store.new_id("model_gateway_config") == "model_gateway_config_010"
    assert rebuilt_store.new_id("model_log") == "model_log_008"


def test_gitlab_review_artifacts_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    apply_payload_to_store(current_store, gitlab_review_context_payload())
    current_store.gitlab_mr_snapshots["snapshot_009"] = {
        "author": {"username": "dev"},
        "base_sha": "base",
        "changed_files_summary": [{"additions": 2, "deletions": 1, "path": "app.py"}],
        "created_at": "2026-05-31T10:00:00+00:00",
        "created_by": "user_admin",
        "diff_limit_bytes": 500000,
        "diff_refs": {"base_sha": "base", "head_sha": "head"},
        "diff_size_bytes": 1234,
        "diff_storage_ref": "memory://gitlab-mr-diff/snapshot_009",
        "head_sha": "head",
        "id": "snapshot_009",
        "mr_iid": 12,
        "product_id": "product_001",
        "project_id": "123",
        "project_path": "group/project",
        "repository_id": "repo_001",
        "requirement_id": "requirement_001",
        "snapshot_hash": "hash_009",
        "source_branch": "feature",
        "target_branch": "main",
        "technical_solution_task_id": "task_002",
        "title": "MR title",
        "version_id": "version_001",
        "writeback_allowed": False,
    }
    current_store.code_review_reports["report_004"] = {
        "archived_at": None,
        "error_code": None,
        "executor": {"name": "code-review"},
        "findings": [{"file_path": "app.py", "severity": "high"}],
        "gitlab_mr_snapshot_id": "snapshot_009",
        "gitlab_writeback_performed": False,
        "id": "report_004",
        "review_id": "review_003",
        "risk_level": "high",
        "status": "pending_review",
        "summary": "Review summary",
        "task_id": "task_003",
    }

    current_store.persist()

    assert repository.gitlab_review_payload == {
        "code_review_reports": {
            "report_004": current_store.code_review_reports["report_004"],
        },
        "gitlab_mr_snapshots": {
            "snapshot_009": current_store.gitlab_mr_snapshots["snapshot_009"],
        },
    }


def test_structured_gitlab_review_restore_sync_counters_and_task_links():
    repository = FakeSnapshotRepository()
    context_payload = gitlab_review_context_payload()
    repository.payload = {
        "ai_tasks": {
            "task_003": {
                "created_by": "user_admin",
                "id": "task_003",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "status": "waiting_review",
                "task_type": "code_review",
                "title": "Code Review",
                "version_id": "version_001",
            }
        },
        "human_reviews": context_payload["human_reviews"],
        "product_git_repositories": context_payload["product_git_repositories"],
        "product_versions": context_payload["product_versions"],
        "products": context_payload["products"],
        "requirements": context_payload["requirements"],
        "code_review_reports": {
            "report_002": {
                "gitlab_mr_snapshot_id": "snapshot_002",
                "id": "report_002",
                "risk_level": "low",
                "status": "draft",
                "summary": "旧快照报告",
                "task_id": "task_002",
            }
        },
        "counters": {"report": 2, "snapshot": 2, "task": 3},
        "gitlab_mr_snapshots": {
            "snapshot_002": {
                "id": "snapshot_002",
                "snapshot_hash": "old_hash",
            }
        },
    }
    repository.ai_tasks_payload = {"ai_tasks": context_payload["ai_tasks"]}
    repository.product_config_payload = {
        "product_git_repositories": context_payload["product_git_repositories"],
        "product_modules": {},
        "product_versions": context_payload["product_versions"],
        "products": context_payload["products"],
    }
    repository.requirements_payload = {"requirements": context_payload["requirements"]}
    repository.workflow_runtime_payload = {
        "graph_checkpoints": {},
        "graph_runs": {},
        "human_reviews": context_payload["human_reviews"],
    }
    repository.gitlab_review_payload = {
        "code_review_reports": {
            "report_004": {
                "executor": {"name": "code-review"},
                "findings": [],
                "gitlab_mr_snapshot_id": "snapshot_009",
                "gitlab_writeback_performed": False,
                "id": "report_004",
                "risk_level": "high",
                "status": "pending_review",
                "summary": "结构表报告",
                "task_id": "task_003",
            }
        },
        "gitlab_mr_snapshots": {
            "snapshot_009": {
                "author": {"username": "dev"},
                "base_sha": "base",
                "changed_files_summary": [],
                "created_by": "user_admin",
                "diff_limit_bytes": 500000,
                "diff_refs": {"base_sha": "base", "head_sha": "head"},
                "diff_size_bytes": 1234,
                "diff_storage_ref": "memory://gitlab-mr-diff/snapshot_009",
                "head_sha": "head",
                "id": "snapshot_009",
                "mr_iid": 12,
                "product_id": "product_001",
                "project_id": "123",
                "project_path": "group/project",
                "repository_id": "repo_001",
                "requirement_id": "requirement_001",
                "snapshot_hash": "hash_009",
                "source_branch": "feature",
                "target_branch": "main",
                "technical_solution_task_id": "task_002",
                "title": "MR title",
                "version_id": "version_001",
                "writeback_allowed": False,
            }
        },
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert list(rebuilt_store.gitlab_mr_snapshots) == ["snapshot_009"]
    assert list(rebuilt_store.code_review_reports) == ["report_004"]
    assert rebuilt_store.ai_tasks["task_003"]["code_review_report_id"] == "report_004"
    assert rebuilt_store.new_id("snapshot") == "snapshot_010"
    assert rebuilt_store.new_id("report") == "report_005"


def test_stale_gitlab_review_artifacts_with_missing_references_are_not_persisted():
    repository = FakeSnapshotRepository()
    payload = gitlab_review_context_payload()
    payload["gitlab_mr_snapshots"] = {
        "snapshot_005": {
            "author": {"username": "dev"},
            "changed_files_summary": [],
            "created_by": "user_admin",
            "diff_limit_bytes": 500000,
            "diff_refs": {},
            "diff_size_bytes": 100,
            "diff_storage_ref": "memory://gitlab-mr-diff/snapshot_005",
            "head_sha": "head",
            "id": "snapshot_005",
            "mr_iid": 5,
            "product_id": "product_001",
            "repository_id": "repo_005",
            "requirement_id": "requirement_001",
            "snapshot_hash": "stale_hash",
            "source_branch": "feature",
            "target_branch": "main",
            "technical_solution_task_id": "task_002",
            "title": "Stale MR",
            "version_id": "version_001",
            "writeback_allowed": False,
        }
    }
    payload["code_review_reports"] = {
        "report_005": {
            "executor": {},
            "findings": [],
            "gitlab_mr_snapshot_id": "snapshot_005",
            "gitlab_writeback_performed": False,
            "id": "report_005",
            "risk_level": "low",
            "status": "pending_review",
            "summary": "Stale report",
            "task_id": "task_003",
        }
    }
    repository.payload = payload

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    rebuilt_store.persist()

    assert rebuilt_store.gitlab_mr_snapshots == {}
    assert rebuilt_store.code_review_reports == {}
    assert repository.gitlab_review_payload == {
        "code_review_reports": {},
        "gitlab_mr_snapshots": {},
    }


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


def test_model_gateway_config_api_writes_fine_grained_repository_payload():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        config = client.post(
            "/api/system/model-gateway-configs",
            json={
                "api_key": "sk-api-secret",
                "base_url": "https://api.example.com/v1",
                "default_chat_model": "gpt-api",
                "default_embedding_model": "text-embedding-api",
                "is_default": True,
                "name": "API 模型网关",
                "provider": "openai_compatible",
                "status": "active",
                "timeout_seconds": 30,
            },
            headers=headers,
        ).json()["data"]

        assert config["api_key_configured"] is True
        assert "api_key" not in config
        assert repository.model_gateway_payload is not None
        persisted = repository.model_gateway_payload["model_gateway_configs"][config["id"]]
        assert persisted["api_key"] == "sk-api-secret"
        assert persisted["is_default"] is True
        assert persisted["default_chat_model"] == "gpt-api"
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


def test_gitlab_daily_code_metrics_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "devops-product",
            "id": "product_001",
            "name": "研发运营产品",
            "status": "active",
        }
    }
    store.product_git_repositories = {
        "repo_001": {
            "default_branch": "main",
            "git_provider": "gitlab",
            "id": "repo_001",
            "name": "devops-api",
            "product_id": "product_001",
            "project_path": "rd/devops-api",
            "remote_url": "https://gitlab.internal/rd/devops-api.git",
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        }
    }
    store.gitlab_daily_code_metrics = {
        "gitlab_metric_010": {
            "active_author_count": 4,
            "additions": 320,
            "author_metrics": [{"author": "alice", "commit_count": 3}],
            "changed_files": 18,
            "collected_at": "2026-06-01T08:00:00+00:00",
            "commit_count": 7,
            "created_at": "2026-06-01T08:00:00+00:00",
            "created_by": "user_admin",
            "deletions": 48,
            "id": "gitlab_metric_010",
            "merge_request_count": 2,
            "metric_date": "2026-06-01",
            "product_id": "product_001",
            "quality_score": 88.5,
            "repository_id": "repo_001",
            "risk_count": 1,
            "source_channel": "manual_import",
            "status": "collected",
            "updated_at": "2026-06-01T08:05:00+00:00",
        }
    }

    store.persist()

    assert repository.gitlab_daily_code_metrics_payload == {
        "gitlab_daily_code_metrics": store.gitlab_daily_code_metrics,
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": store.product_git_repositories,
        "product_modules": {},
        "product_versions": {},
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.gitlab_daily_code_metrics_payload = {
        "gitlab_daily_code_metrics": store.gitlab_daily_code_metrics,
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.gitlab_daily_code_metrics["gitlab_metric_010"]["commit_count"] == 7
    assert rebuilt_store.new_id("gitlab_metric") == "gitlab_metric_011"


def test_jenkins_release_records_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "release-product",
            "id": "product_001",
            "name": "发布验证产品",
            "status": "active",
        }
    }
    store.product_versions = {
        "version_001": {
            "code": "v1.2.0",
            "id": "version_001",
            "name": "v1.2.0",
            "product_id": "product_001",
            "status": "active",
        }
    }
    store.jenkins_release_records = {
        "jenkins_release_010": {
            "build_id": "build-20260601-17",
            "build_number": 17,
            "commit_sha": "abc123def456",
            "created_at": "2026-06-01T12:30:00+00:00",
            "created_by": "user_admin",
            "deployed_at": "2026-06-01T12:30:00+00:00",
            "duration_seconds": 480,
            "environment": "staging",
            "id": "jenkins_release_010",
            "job_name": "rd-platform-deploy",
            "product_id": "product_001",
            "source_channel": "manual_import",
            "started_at": "2026-06-01T12:22:00+00:00",
            "status": "success",
            "trigger_actor": "jenkins-admin",
            "updated_at": "2026-06-01T12:30:00+00:00",
            "version_id": "version_001",
        }
    }

    store.persist()

    assert repository.jenkins_release_records_payload == {
        "jenkins_release_records": store.jenkins_release_records,
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": store.product_versions,
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.jenkins_release_records_payload = {
        "jenkins_release_records": store.jenkins_release_records,
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.jenkins_release_records["jenkins_release_010"]["status"] == "success"
    assert rebuilt_store.new_id("jenkins_release") == "jenkins_release_011"


def test_online_log_metrics_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "ops-product",
            "id": "product_001",
            "name": "线上运营产品",
            "status": "active",
        }
    }
    store.product_modules = {
        "module_001": {
            "code": "checkout",
            "id": "module_001",
            "name": "结算模块",
            "product_id": "product_001",
            "status": "active",
        }
    }
    store.online_log_metrics = {
        "online_log_metric_010": {
            "anomaly_summary": "checkout error spike after release",
            "core_event_count": 240,
            "created_at": "2026-06-01T01:05:00+00:00",
            "created_by": "user_admin",
            "environment": "prod",
            "error_count": 12,
            "error_rate": 0.005,
            "id": "online_log_metric_010",
            "module_code": "checkout",
            "p95_latency_ms": 318.5,
            "p99_latency_ms": 640.25,
            "product_id": "product_001",
            "request_count": 2400,
            "source_channel": "manual_import",
            "status": "collected",
            "top_errors": [{"count": 7, "message": "PaymentTimeout"}],
            "updated_at": "2026-06-01T01:05:00+00:00",
            "window_end": "2026-06-01T01:00:00+00:00",
            "window_start": "2026-06-01T00:00:00+00:00",
        }
    }

    store.persist()

    assert repository.online_log_metrics_payload == {
        "online_log_metrics": store.online_log_metrics,
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": store.product_modules,
        "product_versions": {},
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.online_log_metrics_payload = {
        "online_log_metrics": store.online_log_metrics,
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.online_log_metrics["online_log_metric_010"]["environment"] == "prod"
    assert rebuilt_store.new_id("online_log_metric") == "online_log_metric_011"


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


def test_collector_runs_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "collector-product",
            "id": "product_001",
            "name": "采集运行产品",
            "status": "active",
        }
    }
    store.collector_runs = {
        "collector_run_010": {
            "collector_type": "gitlab_daily_code_metric",
            "created_at": "2026-06-01T08:00:00+00:00",
            "created_by": "user_admin",
            "error_message": None,
            "finished_at": "2026-06-01T08:05:00+00:00",
            "id": "collector_run_010",
            "payload_summary": {"repository_path": "rd/api"},
            "product_id": "product_001",
            "records_imported": 3,
            "source_system": "gitlab",
            "started_at": "2026-06-01T08:00:00+00:00",
            "status": "succeeded",
            "updated_at": "2026-06-01T08:05:00+00:00",
        }
    }

    store.persist()

    assert repository.collector_runs_payload == {"collector_runs": store.collector_runs}

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {},
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.collector_runs_payload = {"collector_runs": store.collector_runs}

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.collector_runs["collector_run_010"]["records_imported"] == 3
    assert rebuilt_store.new_id("collector_run") == "collector_run_011"
