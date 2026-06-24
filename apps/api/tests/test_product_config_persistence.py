from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.users import MemoryUserRepository


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
        "product_id": "product_019",
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
    assert repository.product_config_payload["related_systems"]["related_system_002"][
        "product_id"
    ] == "product_019"

    repository.payload = {"products": {}, "product_versions": {}, "counters": {}}
    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.products["product_019"]["name"] == "结构化产品"
    assert rebuilt_store.product_versions["version_003"]["name"] == "v1"
    assert rebuilt_store.product_modules["module_002"]["owner_team"] == "Platform"
    assert rebuilt_store.product_git_repositories["repo_004"]["credential_ref"] == (
        "env:GITLAB_READONLY_TOKEN"
    )
    assert rebuilt_store.related_systems["related_system_002"]["name"] == "支付系统"
    assert rebuilt_store.related_systems["related_system_002"]["product_id"] == "product_019"
    assert rebuilt_store.new_id("product") == "product_020"


def test_empty_product_config_tables_ignore_snapshot_product_data():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "counters": {"product": 1},
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {
            "version_single_read": {
                "code": "v1",
                "description": None,
                "id": "version_single_read",
                "name": "v1",
                "product_id": "product_single_read",
                "release_date": None,
                "start_date": None,
                "status": "active",
            },
        },
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

    assert rebuilt_store.products == {}


def test_product_config_tables_ignore_snapshot_records_after_structured_migration():
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
    assert "product_011" not in rebuilt_store.products
    assert "version_005" not in rebuilt_store.product_versions
    assert repository.requirements_payload == {"requirements": {}}


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
    assert rebuilt_store.new_id("requirement") == "requirement_001"


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


def test_product_config_routes_write_repository_without_request_persist():
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
            json={"code": "DBFIRST-PRODUCT", "name": "DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
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
                "credential_ref": "secret://github/readonly",
                "git_provider": "github",
                "name": "主仓库",
                "project_path": "org/repo",
                "remote_url": "git@github.com:org/repo.git",
            },
            headers=headers,
        ).json()["data"]
        related_system = client.post(
            "/api/system/related-systems",
            json={
                "code": "DBFIRST-SYSTEM",
                "name": "DB-first 相关系统",
                "product_id": product["id"],
            },
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        products = client.get("/api/products", headers=headers).json()["data"]["items"]
        assert [item["id"] for item in products] == [product["id"]]
        versions = client.get(
            f"/api/products/{product['id']}/versions",
            headers=headers,
        ).json()["data"]["items"]
        modules = client.get(
            f"/api/products/{product['id']}/modules",
            headers=headers,
        ).json()["data"]["items"]
        repositories = client.get(
            f"/api/products/{product['id']}/git-repositories",
            headers=headers,
        ).json()["data"]["items"]
        related_systems = client.get(
            f"/api/system/related-systems?product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in versions] == [version["id"]]
        assert [item["id"] for item in modules] == [module["id"]]
        assert [item["id"] for item in repositories] == [repository_record["id"]]
        assert [item["id"] for item in related_systems] == [related_system["id"]]

        patched_product = client.patch(
            f"/api/products/{product['id']}",
            json={"name": "DB-first 产品已修改"},
            headers=headers,
        ).json()["data"]
        patched_version = client.patch(
            f"/api/product-versions/{version['id']}",
            json={"release_date": "2026-06-30"},
            headers=headers,
        ).json()["data"]
        patched_module = client.patch(
            f"/api/product-modules/{module['id']}",
            json={"owner_team": "platform"},
            headers=headers,
        ).json()["data"]
        patched_repository = client.patch(
            f"/api/product-git-repositories/{repository_record['id']}",
            json={"status": "inactive"},
            headers=headers,
        ).json()["data"]
        patched_related_system = client.patch(
            f"/api/system/related-systems/{related_system['id']}",
            json={"status": "inactive"},
            headers=headers,
        ).json()["data"]

        use_rebuilt_store_without_request_persist()
        assert client.get(
            f"/api/products/{product['id']}",
            headers=headers,
        ).json()["data"]["name"] == patched_product["name"]
        assert client.get(
            f"/api/products/{product['id']}/versions",
            headers=headers,
        ).json()["data"]["items"][0]["release_date"] == patched_version["release_date"]
        assert client.get(
            f"/api/products/{product['id']}/modules",
            headers=headers,
        ).json()["data"]["items"][0]["owner_team"] == patched_module["owner_team"]
        assert client.get(
            f"/api/products/{product['id']}/git-repositories",
            headers=headers,
        ).json()["data"]["items"][0]["status"] == patched_repository["status"]
        assert client.get(
            f"/api/system/related-systems?product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"][0]["status"] == patched_related_system["status"]

        client.delete(
            f"/api/product-git-repositories/{repository_record['id']}",
            headers=headers,
        )
        client.delete(f"/api/product-modules/{module['id']}", headers=headers)
        client.delete(f"/api/product-versions/{version['id']}", headers=headers)
        client.delete(f"/api/products/{product['id']}", headers=headers)

        use_rebuilt_store_without_request_persist()
        assert client.get("/api/products", headers=headers).json()["data"]["items"] == []
        assert client.get(
            f"/api/system/related-systems?product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"] == []
        assert any(
            write.startswith(f"save:products:{product['id']}")
            for write in repository.product_config_direct_writes
        )
        assert any(
            write.startswith(f"delete:products:{product['id']}")
            for write in repository.product_config_direct_writes
        )
        assert (
            f"delete:related_systems:{related_system['id']}"
            in repository.product_config_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_product_config_get_routes_use_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.product_config_payload = {
        "products": {
            "product_read_sql": {
                "code": "READ-SQL",
                "description": "repository product",
                "display_order": 3,
                "id": "product_read_sql",
                "name": "Repository 产品",
                "owner_team": "platform",
                "status": "active",
            },
            "product_inactive_sql": {
                "code": "READ-INACTIVE",
                "description": None,
                "display_order": 9,
                "id": "product_inactive_sql",
                "name": "Inactive 产品",
                "owner_team": None,
                "status": "inactive",
            },
        },
        "product_versions": {
            "version_read_sql": {
                "code": "v1",
                "description": "repository version",
                "id": "version_read_sql",
                "name": "v1",
                "product_id": "product_read_sql",
                "release_date": "2026-06-30",
                "start_date": "2026-06-01",
                "status": "active",
            },
        },
        "product_modules": {
            "module_read_sql": {
                "code": "core",
                "description": "repository module",
                "display_order": 1,
                "id": "module_read_sql",
                "name": "核心模块",
                "owner_team": "rd",
                "product_id": "product_read_sql",
                "status": "active",
            },
        },
        "product_git_repositories": {
            "repo_read_sql": {
                "credential_ref": "secret://github/read",
                "default_branch": "main",
                "git_provider": "github",
                "id": "repo_read_sql",
                "name": "主仓库",
                "product_id": "product_read_sql",
                "project_id": None,
                "project_path": "org/read-sql",
                "remote_url": "git@github.com:org/read-sql.git",
                "repo_type": "code",
                "root_path": "/",
                "status": "active",
            },
        },
        "related_systems": {
            "related_read_sql": {
                "code": "REL-SQL",
                "description": "repository system",
                "display_order": 2,
                "id": "related_read_sql",
                "name": "相关系统",
                "owner_team": "ops",
                "product_id": "product_read_sql",
                "status": "active",
            },
        },
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.products = {}
    stale_store.product_versions = {}
    stale_store.product_modules = {}
    stale_store.product_git_repositories = {}
    stale_store.related_systems = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        products = client.get("/api/products?active_only=true", headers=headers).json()["data"]
        assert [item["id"] for item in products["items"]] == ["product_read_sql"]

        product = client.get("/api/products/product_read_sql", headers=headers).json()["data"]
        assert product["name"] == "Repository 产品"

        versions = client.get(
            "/api/products/product_read_sql/versions",
            headers=headers,
        ).json()["data"]
        modules = client.get(
            "/api/products/product_read_sql/modules",
            headers=headers,
        ).json()["data"]
        repositories = client.get(
            "/api/products/product_read_sql/git-repositories",
            headers=headers,
        ).json()["data"]
        related_systems = client.get(
            "/api/system/related-systems?product_id=product_read_sql",
            headers=headers,
        ).json()["data"]

        assert [item["id"] for item in versions["items"]] == ["version_read_sql"]
        assert [item["id"] for item in modules["items"]] == ["module_read_sql"]
        assert [item["id"] for item in repositories["items"]] == ["repo_read_sql"]
        assert "credential_ref" not in repositories["items"][0]
        assert [item["id"] for item in related_systems["items"]] == ["related_read_sql"]

        missing = client.get("/api/products/missing_product/versions", headers=headers)
        assert missing.status_code == 404
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_product_config_subresource_writes_read_repository_records_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.product_config_payload = {
        "products": {
            "product_single_read": {
                "code": "SINGLE-READ",
                "description": None,
                "display_order": 1,
                "id": "product_single_read",
                "name": "单记录读取产品",
                "owner_team": "platform",
                "status": "active",
            },
        },
        "product_versions": {},
        "product_modules": {
            "module_single_read": {
                "code": "core",
                "description": "repository module",
                "display_order": 2,
                "id": "module_single_read",
                "name": "单记录模块",
                "owner_team": "platform",
                "product_id": "product_single_read",
                "status": "active",
            },
        },
        "product_git_repositories": {
            "repo_single_read": {
                "credential_ref": "secret://github/single",
                "default_branch": "main",
                "git_provider": "github",
                "id": "repo_single_read",
                "name": "单记录仓库",
                "product_id": "product_single_read",
                "project_id": None,
                "project_path": "org/single-read",
                "remote_url": "git@github.com:org/single-read.git",
                "repo_type": "code",
                "root_path": "/",
                "status": "active",
            },
        },
        "product_version_branch_configs": {
            "version_branch_single_read": {
                "base_branch": "main",
                "branch_status": "active",
                "creation_source": "manual",
                "description": "repository branch config",
                "id": "version_branch_single_read",
                "product_id": "product_single_read",
                "repository_id": "repo_single_read",
                "version_id": "version_single_read",
                "working_branch": "feature/single-read",
            },
        },
        "related_systems": {
            "related_single_read": {
                "code": "REL-SINGLE",
                "description": "repository related system",
                "display_order": 3,
                "id": "related_single_read",
                "name": "单记录相关系统",
                "owner_team": "ops",
                "product_id": "product_single_read",
                "status": "active",
            },
        },
    }
    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        patched_module = client.patch(
            "/api/product-modules/module_single_read",
            json={"code": "core-updated", "status": "inactive"},
            headers=headers,
        )
        assert patched_module.status_code == 200
        assert patched_module.json()["data"]["code"] == "core-updated"
        assert patched_module.json()["data"]["status"] == "inactive"

        patched_repository = client.patch(
            "/api/product-git-repositories/repo_single_read",
            json={"status": "inactive"},
            headers=headers,
        )
        assert patched_repository.status_code == 200
        assert patched_repository.json()["data"]["status"] == "inactive"

        patched_system = client.patch(
            "/api/system/related-systems/related_single_read",
            json={
                "code": "REL-SINGLE-2",
                "product_id": "product_single_read",
                "status": "inactive",
            },
            headers=headers,
        )
        assert patched_system.status_code == 200
        assert patched_system.json()["data"]["code"] == "REL-SINGLE-2"

        patched_branch_config = client.patch(
            "/api/product-version-branch-configs/version_branch_single_read",
            json={"branch_status": "testing"},
            headers=headers,
        )
        assert patched_branch_config.status_code == 200
        assert patched_branch_config.json()["data"]["branch_status"] == "testing"
        assert patched_branch_config.json()["data"]["repository_name"] == "单记录仓库"

        assert repository.product_config_single_reads == [
            "get_product_module:module_single_read",
            "get_product_git_repository:repo_single_read",
            "get_related_system:related_single_read",
            "get_related_system_by_code:REL-SINGLE-2",
            "get_product:product_single_read",
            "get_product_version_branch_config:version_branch_single_read",
        ]
        assert (
            repository.product_config_payload["product_modules"]["module_single_read"]["status"]
            == "inactive"
        )
        assert (
            repository.product_config_payload["product_git_repositories"]["repo_single_read"][
                "status"
            ]
            == "inactive"
        )
        assert (
            repository.product_config_payload["related_systems"]["related_single_read"]["status"]
            == "inactive"
        )
        assert (
            repository.product_config_payload["product_version_branch_configs"][
                "version_branch_single_read"
            ]["branch_status"]
            == "testing"
        )
        assert (
            "save:product_modules:module_single_read"
            in repository.product_config_direct_writes
        )
        assert (
            "save:product_git_repositories:repo_single_read"
            in repository.product_config_direct_writes
        )
        assert "save:related_systems:related_single_read" in repository.product_config_direct_writes
        assert (
            "save:product_version_branch_configs:version_branch_single_read"
            in repository.product_config_direct_writes
        )

        repository.product_config_single_reads.clear()
        deleted_module = client.delete(
            "/api/product-modules/module_single_read",
            headers=headers,
        )
        deleted_branch_config = client.delete(
            "/api/product-version-branch-configs/version_branch_single_read",
            headers=headers,
        )
        deleted_repository = client.delete(
            "/api/product-git-repositories/repo_single_read",
            headers=headers,
        )
        deleted_system = client.delete(
            "/api/system/related-systems/related_single_read",
            headers=headers,
        )

        assert deleted_module.status_code == 200
        assert deleted_branch_config.status_code == 200
        assert deleted_repository.status_code == 200
        assert deleted_system.status_code == 200
        assert repository.product_config_single_reads == [
            "get_product_module:module_single_read",
            "product_module_has_related_records:product_single_read:core-updated",
            "get_product_version_branch_config:version_branch_single_read",
            "get_product_git_repository:repo_single_read",
            "get_related_system:related_single_read",
        ]
        assert "module_single_read" not in repository.product_config_payload["product_modules"]
        assert "version_branch_single_read" not in repository.product_config_payload[
            "product_version_branch_configs"
        ]
        assert "repo_single_read" not in repository.product_config_payload[
            "product_git_repositories"
        ]
        assert "related_single_read" not in repository.product_config_payload["related_systems"]
        assert (
            "delete:product_modules:module_single_read"
            in repository.product_config_direct_writes
        )
        assert (
            "delete:product_git_repositories:repo_single_read"
            in repository.product_config_direct_writes
        )
        assert (
            "delete:product_version_branch_configs:version_branch_single_read"
            in repository.product_config_direct_writes
        )
        assert (
            "delete:related_systems:related_single_read"
            in repository.product_config_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_product_config_writes_use_postgres_runtime_source_rows():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "PG-RUNTIME", "name": "Postgres Runtime 产品"},
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
        git_repository = client.post(
            f"/api/products/{product['id']}/git-repositories",
            json={
                "git_provider": "github",
                "name": "Frontend",
                "project_path": "acme/frontend",
                "repo_type": "frontend",
                "status": "active",
            },
            headers=headers,
        ).json()["data"]
        related_system = client.post(
            "/api/system/related-systems",
            json={
                "code": "crm",
                "name": "CRM",
                "product_id": product["id"],
                "status": "active",
            },
            headers=headers,
        ).json()["data"]

        assert version["product_id"] == product["id"]
        assert module["product_id"] == product["id"]
        assert git_repository["product_id"] == product["id"]
        assert related_system["product_id"] == product["id"]
        assert f"save:products:{product['id']}" in repository.product_config_direct_writes
        assert (
            f"save:product_versions:{version['id']}"
            in repository.product_config_direct_writes
        )
        assert (
            f"save:product_modules:{module['id']}"
            in repository.product_config_direct_writes
        )
        assert (
            f"save:product_git_repositories:{git_repository['id']}"
            in repository.product_config_direct_writes
        )
        assert (
            f"save:related_systems:{related_system['id']}"
            in repository.product_config_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
