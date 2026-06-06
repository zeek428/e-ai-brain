from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.users import MemoryUserRepository


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
        assert persisted["status"] == "submitted"
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
        assert persisted["brain_app_id"] == "rd_brain"
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


def test_requirement_routes_write_repository_without_request_persist():
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
        product = client.post(
            "/api/products",
            json={"code": "REQ-DBFIRST", "name": "需求 DB-first 产品"},
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
                "content": "需求台账写接口不能依赖请求结束 persist。",
                "product_id": product["id"],
                "title": "需求 DB-first 创建",
            },
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        assert detail["title"] == requirement["title"]
        assert detail["status"] == "submitted"

        approved = client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入需求池"},
            headers=headers,
        ).json()["data"]
        assert approved["status"] == "approved"
        planned = client.patch(
            f"/api/requirements/{requirement['id']}",
            json={"version_id": version["id"]},
            headers=headers,
        ).json()["data"]
        assert planned["status"] == "planned"
        closed = client.post(
            f"/api/requirements/{requirement['id']}/close",
            headers=headers,
        ).json()["data"]
        assert closed["status"] == "closed"

        use_rebuilt_store_without_request_persist()
        closed_detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        assert closed_detail["status"] == "closed"
        assert closed_detail["version_id"] == version["id"]

        rejected_candidate = client.post(
            "/api/requirements",
            json={
                "content": "用于验证拒绝和删除也直接写 repository。",
                "product_id": product["id"],
                "title": "需求 DB-first 驳回",
            },
            headers=headers,
        ).json()["data"]
        rejected = client.post(
            f"/api/requirements/{rejected_candidate['id']}/reject",
            json={"rejection_reason": "边界不清晰"},
            headers=headers,
        ).json()["data"]
        assert rejected["status"] == "rejected"

        delete_candidate = client.post(
            "/api/requirements",
            json={
                "content": "用于验证删除直接写 repository。",
                "product_id": product["id"],
                "title": "需求 DB-first 删除",
            },
            headers=headers,
        ).json()["data"]
        delete_response = client.delete(
            f"/api/requirements/{delete_candidate['id']}",
            headers=headers,
        )
        assert delete_response.status_code == 200

        use_rebuilt_store_without_request_persist()
        deleted_detail = client.get(
            f"/api/requirements/{delete_candidate['id']}",
            headers=headers,
        )
        assert deleted_detail.status_code == 404
        rejected_detail = client.get(
            f"/api/requirements/{rejected_candidate['id']}",
            headers=headers,
        ).json()["data"]
        assert rejected_detail["status"] == "rejected"
        assert any(
            write == f"save:{requirement['id']}:closed"
            for write in repository.requirement_direct_writes
        )
        assert f"delete:{delete_candidate['id']}" in repository.requirement_direct_writes
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_generate_task_writes_requirement_and_ai_task_without_request_persist():
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
        product = client.post(
            "/api/products",
            json={"code": "TASK-DBFIRST", "name": "任务 DB-first 产品"},
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
                "content": "生成任务时需求和 AI task 必须同事务写入。",
                "product_id": product["id"],
                "title": "任务 DB-first 生成",
            },
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入需求池"},
            headers=headers,
        )
        planned = client.patch(
            f"/api/requirements/{requirement['id']}",
            json={"version_id": version["id"]},
            headers=headers,
        ).json()["data"]
        assert planned["status"] == "planned"

        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        app.state.store.requirements = {}
        app.state.store.ai_tasks = {}
        repository.task_workflow_source_row_reads = 0
        requirement_detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        task_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        assert requirement_detail["status"] == "designing"
        assert requirement_detail["task_ids"] == [generated["task_id"]]
        assert task_detail["status"] == "draft"
        assert task_detail["requirement_id"] == requirement["id"]
        assert task_detail["product_context"]["product"]["id"] == product["id"]
        assert repository.task_workflow_source_row_reads == 2
        assert (
            f"save:{requirement['id']}:{generated['task_id']}:draft"
            in repository.ai_task_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_requirement_and_task_writes_use_postgres_runtime_source_rows():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "REQ-PG-RUNTIME", "name": "需求 Runtime 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "core", "name": "核心模块", "status": "active"},
            headers=headers,
        ).json()["data"]

        requirement = client.post(
            "/api/requirements",
            json={
                "content": "空启动容器下仍应从 repository source rows 校验产品上下文。",
                "module_code": module["code"],
                "product_id": product["id"],
                "title": "Runtime source rows 需求",
            },
            headers=headers,
        ).json()["data"]
        approved = client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入需求池"},
            headers=headers,
        ).json()["data"]
        planned = client.patch(
            f"/api/requirements/{requirement['id']}",
            json={"version_id": version["id"]},
            headers=headers,
        ).json()["data"]
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]

        assert approved["status"] == "approved"
        assert planned["status"] == "planned"
        assert generated["task_status"] == "draft"
        assert repository.task_workflow_source_row_reads >= 4
        assert (
            f"save:{requirement['id']}:{generated['task_id']}:draft"
            in repository.ai_task_direct_writes
        )
        task = repository.ai_tasks_payload["ai_tasks"][generated["task_id"]]
        assert task["product_context"]["product"]["id"] == product["id"]
        assert task["product_context"]["module"]["code"] == module["code"]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_start_task_writes_review_graph_and_checkpoint_without_request_persist():
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
        product = client.post(
            "/api/products",
            json={"code": "START-DBFIRST", "name": "启动 DB-first 产品"},
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
                "content": "启动任务必须直接写 Review、Graph Run 和 Checkpoint。",
                "product_id": product["id"],
                "title": "任务启动 DB-first",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入设计"},
            headers=headers,
        )
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]
        use_rebuilt_store_without_request_persist()
        draft_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        app.state.store.graph_runs = {}
        app.state.store.human_reviews = {}
        app.state.store.ai_tasks = {}
        repository.task_workflow_source_row_reads = 0
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={generated['task_id']}",
            headers=headers,
        ).json()["data"]
        pending_reviews = client.get("/api/reviews/pending", headers=headers).json()["data"][
            "items"
        ]
        review_detail = client.get(
            f"/api/reviews/{started['review_id']}",
            headers=headers,
        ).json()["data"]

        assert detail["status"] == "waiting_review"
        assert detail["pending_review"]["id"] == started["review_id"]
        assert detail["current_step"] == "interrupt_for_human_review"
        assert detail["checkpoint_id"] == started["checkpoint_id"]
        assert detail["updated_at"] != draft_detail["updated_at"]
        assert [run["id"] for run in graph_runs["items"]] == [started["graph_run_id"]]
        assert graph_runs["items"][0]["checkpoint_id"] == started["checkpoint_id"]
        assert [review["id"] for review in pending_reviews] == [started["review_id"]]
        assert review_detail["id"] == started["review_id"]
        assert review_detail["task"]["id"] == generated["task_id"]
        assert repository.task_workflow_source_row_reads == 3
        assert (
            f"start:{generated['task_id']}:{started['review_id']}:"
            f"{started['graph_run_id']}:{started['checkpoint_id']}"
            in repository.workflow_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users



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
    client.post(
        f"/api/requirements/{requirement['id']}/approve",
        json={"comment": "进入设计"},
        headers=headers,
    )
    return client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]


def test_create_followup_task_writes_requirement_and_ai_task_without_request_persist():
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
            product_code="FOLLOWUP-DBFIRST",
            product_name="后续任务 DB-first 产品",
            requirement_title="后续任务创建 DB-first",
        )
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        client.post(
            f"/api/reviews/{started['review_id']}/approve",
            json={"version": 1},
            headers=headers,
        )
        use_rebuilt_store_without_request_persist()
        design_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        followup = client.post(
            "/api/ai-tasks",
            json={
                "input": {"product_detail_design_task_id": generated["task_id"]},
                "requirement_id": design_detail["requirement_id"],
                "task_type": "technical_solution",
                "title": "技术方案后续任务 DB-first",
            },
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        followup_detail = client.get(
            f"/api/ai-tasks/{followup['id']}",
            headers=headers,
        ).json()["data"]
        requirement_detail = client.get(
            f"/api/requirements/{design_detail['requirement_id']}",
            headers=headers,
        ).json()["data"]

        assert followup_detail["status"] == "draft"
        assert followup_detail["task_type"] == "technical_solution"
        assert followup_detail["input"]["product_detail_design_task_id"] == generated["task_id"]
        assert requirement_detail["status"] == "ready_for_dev"
        assert requirement_detail["task_ids"] == [generated["task_id"], followup["id"]]
        assert (
            f"save:{design_detail['requirement_id']}:{followup['id']}:draft"
            in repository.ai_task_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
