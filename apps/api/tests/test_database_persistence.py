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

    def load(self) -> dict | None:
        return self.payload

    def save(self, payload: dict) -> None:
        self.payload = payload

    def load_product_config(self) -> dict | None:
        return self.product_config_payload

    def save_product_config(self, payload: dict) -> None:
        self.product_config_payload = payload


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
