from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_product_config_supports_list_patch_and_active_filters():
    app.state.store.reset()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={
            "code": "ai-brain",
            "name": "AI Brain",
            "description": "企业 AI 大脑平台",
            "owner_team": "rd",
            "display_order": 100,
        },
        headers=headers,
    ).json()["data"]
    inactive = client.post(
        "/api/products",
        json={"code": "legacy", "name": "Legacy", "status": "inactive"},
        headers=headers,
    ).json()["data"]

    product_list = client.get("/api/products?active_only=true", headers=headers).json()["data"]
    assert [item["id"] for item in product_list["items"]] == [product["id"]]
    assert inactive["id"] not in [item["id"] for item in product_list["items"]]

    patched_product = client.patch(
        f"/api/products/{product['id']}",
        json={"name": "Enterprise AI Brain", "status": "active"},
        headers=headers,
    ).json()["data"]
    assert patched_product["name"] == "Enterprise AI Brain"
    assert patched_product["display_order"] == 100

    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1", "status": "active"},
        headers=headers,
    ).json()["data"]
    archived = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "old", "name": "old", "status": "archived"},
        headers=headers,
    ).json()["data"]
    versions = client.get(
        f"/api/products/{product['id']}/versions?active_only=true",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in versions["items"]] == [version["id"]]
    assert archived["id"] not in [item["id"] for item in versions["items"]]

    patched_version = client.patch(
        f"/api/product-versions/{version['id']}",
        json={"release_date": "2026-05-31"},
        headers=headers,
    ).json()["data"]
    assert patched_version["release_date"] == "2026-05-31"

    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "knowledge", "name": "知识中心", "display_order": 10},
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "legacy", "name": "旧模块", "status": "inactive"},
        headers=headers,
    )
    modules = client.get(
        f"/api/products/{product['id']}/modules?active_only=true",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in modules["items"]] == [module["id"]]

    patched_module = client.patch(
        f"/api/product-modules/{module['id']}",
        json={"owner_team": "knowledge-platform"},
        headers=headers,
    ).json()["data"]
    assert patched_module["owner_team"] == "knowledge-platform"

    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "repo_type": "code",
            "name": "ai-brain-api",
            "remote_url": "https://gitlab.internal/rd/ai-brain-api.git",
            "git_provider": "gitlab",
            "project_path": "rd/ai-brain-api",
            "credential_ref": "secret://gitlab/readonly",
            "default_branch": "main",
            "root_path": "/",
        },
        headers=headers,
    ).json()["data"]
    assert "credential_ref" not in repository
    assert repository["credential_ref_configured"] is True
    repositories = client.get(
        f"/api/products/{product['id']}/git-repositories?active_only=true",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in repositories["items"]] == [repository["id"]]
    assert "credential_ref" not in repositories["items"][0]
    assert repositories["items"][0]["credential_ref_configured"] is True

    patched_repository = client.patch(
        f"/api/product-git-repositories/{repository['id']}",
        json={"status": "inactive"},
        headers=headers,
    ).json()["data"]
    assert patched_repository["status"] == "inactive"
    assert "credential_ref" not in patched_repository
    assert patched_repository["credential_ref_configured"] is True


def test_related_systems_and_model_gateway_configs_mask_secrets_and_audit_writes():
    app.state.store.reset()
    headers = auth_headers()

    related_system = client.post(
        "/api/system/related-systems",
        json={
            "code": "knowledge",
            "name": "知识中心",
            "description": "文档导入、检索和知识沉淀",
            "owner_team": "rd",
            "display_order": 100,
        },
        headers=headers,
    ).json()["data"]
    patched_system = client.patch(
        f"/api/system/related-systems/{related_system['id']}",
        json={"status": "inactive"},
        headers=headers,
    ).json()["data"]
    assert patched_system["status"] == "inactive"
    assert client.get(
        "/api/system/related-systems?active_only=true",
        headers=headers,
    ).json()["data"]["items"] == []

    config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "name": "默认模型网关",
            "provider": "openai_compatible",
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-secret-value",
            "default_chat_model": "chat-model",
            "default_embedding_model": "embedding-model",
            "timeout_seconds": 60,
            "max_retries": 1,
            "status": "active",
            "is_default": True,
        },
        headers=headers,
    ).json()["data"]
    assert config["api_key_configured"] is True
    assert "api_key" not in config
    assert "api_key_masked" not in config

    second_config = client.post(
        "/api/system/model-gateway-configs",
        json={
            "name": "备用模型网关",
            "provider": "openai_compatible",
            "base_url": "https://backup.example.com/v1",
            "api_key": "backup-secret",
            "default_chat_model": "backup-chat",
            "default_embedding_model": "backup-embedding",
            "is_default": True,
        },
        headers=headers,
    ).json()["data"]
    configs = client.get("/api/system/model-gateway-configs", headers=headers).json()["data"][
        "items"
    ]
    assert [item["id"] for item in configs if item["is_default"]] == [second_config["id"]]
    assert all("api_key" not in item for item in configs)
    assert all("api_key_masked" not in item for item in configs)

    patched_config = client.patch(
        f"/api/system/model-gateway-configs/{second_config['id']}",
        json={"api_key": "rotated-secret", "timeout_seconds": 45},
        headers=headers,
    ).json()["data"]
    assert patched_config["api_key_configured"] is True
    assert "api_key_masked" not in patched_config
    assert patched_config["timeout_seconds"] == 45

    audit_events = client.get("/api/audit/events", headers=headers).json()["data"]["items"]
    assert "related_system.created" in [event["event_type"] for event in audit_events]
    assert "model_gateway_config.updated" in [event["event_type"] for event in audit_events]
    assert "sk-secret-value" not in str(audit_events)
