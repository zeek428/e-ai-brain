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
    related_system = client.post(
        "/api/system/related-systems",
        json={
            "code": "billing",
            "name": "计费系统",
            "owner_team": "business-platform",
            "product_id": product["id"],
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    assert related_system["product_id"] == product["id"]
    related_systems = client.get(
        f"/api/system/related-systems?product_id={product['id']}",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in related_systems["items"]] == [related_system["id"]]

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

    branch_config = client.post(
        f"/api/product-versions/{version['id']}/branch-configs",
        json={
            "base_branch": "main",
            "branch_status": "active",
            "creation_source": "manual",
            "repository_id": repository["id"],
            "working_branch": "release/2026-v1",
        },
        headers=headers,
    ).json()["data"]
    assert branch_config["product_id"] == product["id"]
    assert branch_config["version_id"] == version["id"]
    assert branch_config["repository_id"] == repository["id"]
    assert branch_config["repository_name"] == "ai-brain-api"
    assert branch_config["working_branch"] == "release/2026-v1"
    branch_configs = client.get(
        f"/api/product-versions/{version['id']}/branch-configs",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in branch_configs["items"]] == [branch_config["id"]]
    patched_branch_config = client.patch(
        f"/api/product-version-branch-configs/{branch_config['id']}",
        json={"branch_status": "testing"},
        headers=headers,
    ).json()["data"]
    assert patched_branch_config["branch_status"] == "testing"

    patched_repository = client.patch(
        f"/api/product-git-repositories/{repository['id']}",
        json={"status": "inactive"},
        headers=headers,
    ).json()["data"]
    assert patched_repository["status"] == "inactive"
    assert "credential_ref" not in patched_repository
    assert patched_repository["credential_ref_configured"] is True


def test_product_detail_endpoint_returns_single_product():
    app.state.store.reset()
    headers = auth_headers()
    product = client.post(
        "/api/products",
        json={"code": "detail-product", "name": "产品详情"},
        headers=headers,
    ).json()["data"]

    detail = client.get(f"/api/products/{product['id']}", headers=headers)
    missing = client.get("/api/products/product_missing", headers=headers)

    assert detail.status_code == 200
    assert detail.json()["data"] == product
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "NOT_FOUND"


def test_product_list_supports_server_pagination_sort_and_filters():
    app.state.store.reset()
    headers = auth_headers()
    first = client.post(
        "/api/products",
        json={
            "code": "list-a",
            "name": "列表产品 A",
            "owner_team": "growth",
            "status": "active",
        },
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/products/{first['id']}/versions",
        json={"code": "list-a-v1", "name": "列表产品 A 版本", "status": "testing"},
        headers=headers,
    )
    client.post(
        f"/api/products/{first['id']}/modules",
        json={"code": "list-a-module", "name": "列表产品 A 模块", "status": "active"},
        headers=headers,
    )
    second = client.post(
        "/api/products",
        json={
            "code": "list-b",
            "name": "列表产品 B",
            "owner_team": "platform",
            "status": "inactive",
        },
        headers=headers,
    ).json()["data"]

    filtered = client.get(
        "/api/products?owner_team=platform&status=inactive&page=1&page_size=1"
        "&sort_by=code&sort_order=desc",
        headers=headers,
    ).json()["data"]
    invalid_sort = client.get(
        "/api/products?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )

    assert filtered["page"] == 1
    assert filtered["page_size"] == 1
    assert filtered["total"] == 1
    assert [item["id"] for item in filtered["items"]] == [second["id"]]
    assert first["id"] not in [item["id"] for item in filtered["items"]]
    assert invalid_sort.status_code == 400
    assert invalid_sort.json()["detail"]["code"] == "VALIDATION_ERROR"

    projected = client.get(
        "/api/products?code=list-a&page=1&page_size=1",
        headers=headers,
    ).json()["data"]
    assert projected["items"][0]["current_version_name"] == "列表产品 A 版本"
    assert projected["items"][0]["module_count"] == 1


def test_related_systems_are_saved_in_generated_task_product_context():
    app.state.store.reset()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={"code": "context-product", "name": "上下文产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1"},
        headers=headers,
    ).json()["data"]
    client.post(
        "/api/system/related-systems",
        json={
            "code": "crm",
            "name": "CRM 系统",
            "product_id": product["id"],
            "status": "active",
        },
        headers=headers,
    )
    other_product = client.post(
        "/api/products",
        json={"code": "other-context-product", "name": "其他产品"},
        headers=headers,
    ).json()["data"]
    client.post(
        "/api/system/related-systems",
        json={
            "code": "other-crm",
            "name": "其他 CRM",
            "product_id": other_product["id"],
            "status": "active",
        },
        headers=headers,
    )
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "需要把相关系统带入任务上下文",
            "product_id": product["id"],
            "title": "相关系统上下文需求",
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
    task_detail = client.get(
        f"/api/ai-tasks/{generated['task_id']}",
        headers=headers,
    ).json()["data"]

    related_systems = task_detail["product_context"]["related_systems"]["items"]
    assert [item["code"] for item in related_systems] == ["crm"]


def test_generated_task_product_context_does_not_expose_git_credentials():
    app.state.store.reset()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={"code": "context-credential-product", "name": "凭据上下文产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1"},
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "credential_ref": "secret://git/readonly",
            "git_provider": "github",
            "name": "代码仓库",
            "project_path": "org/repo",
            "remote_url": "git@github.com:org/repo.git",
        },
        headers=headers,
    )
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "生成任务上下文时不能泄露 Git 凭据",
            "product_id": product["id"],
            "title": "Git 凭据脱敏需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)

    generated = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    task_detail = client.get(
        f"/api/ai-tasks/{generated['task_id']}",
        headers=headers,
    ).json()["data"]

    repositories = task_detail["product_context"]["repositories"]["items"]
    input_repositories = task_detail["input"]["product_context"]["repositories"]["items"]
    assert repositories[0]["credential_ref_configured"] is True
    assert input_repositories[0]["credential_ref_configured"] is True
    assert "credential_ref" not in repositories[0]
    assert "credential_ref" not in input_repositories[0]


def test_product_config_rejects_duplicate_codes_and_invalid_statuses():
    app.state.store.reset()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={"code": "unique-product", "name": "唯一产品"},
        headers=headers,
    ).json()["data"]
    duplicate_product = client.post(
        "/api/products",
        json={"code": "unique-product", "name": "重复产品"},
        headers=headers,
    )
    assert duplicate_product.status_code == 409
    assert duplicate_product.json()["detail"]["code"] == "PRODUCT_CODE_EXISTS"

    invalid_product_status = client.patch(
        f"/api/products/{product['id']}",
        json={"status": "deleted"},
        headers=headers,
    )
    assert invalid_product_status.status_code == 400
    assert invalid_product_status.json()["detail"]["code"] == "VALIDATION_ERROR"

    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1"},
        headers=headers,
    ).json()["data"]
    duplicate_version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "重复版本"},
        headers=headers,
    )
    assert duplicate_version.status_code == 409
    assert duplicate_version.json()["detail"]["code"] == "PRODUCT_VERSION_CODE_EXISTS"

    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "core", "name": "核心模块"},
        headers=headers,
    ).json()["data"]
    duplicate_module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": module["code"], "name": "重复模块"},
        headers=headers,
    )
    assert duplicate_module.status_code == 409
    assert duplicate_module.json()["detail"]["code"] == "PRODUCT_MODULE_CODE_EXISTS"

    direct_archive = client.patch(
        f"/api/product-versions/{version['id']}",
        json={"status": "archived"},
        headers=headers,
    )
    assert direct_archive.status_code == 409
    assert direct_archive.json()["detail"]["code"] == "PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED"

    for target_status in ["active", "testing", "released", "archived"]:
        advance_response = client.post(
            f"/api/product-versions/{version['id']}/advance-status",
            json={"reason": "验证归档版本校验", "target_status": target_status},
            headers=headers,
        )
        assert advance_response.status_code == 200
        archived = advance_response.json()["data"]["version"]
    assert archived["status"] == "archived"

    requirement = client.post(
        "/api/requirements",
        json={
            "content": "归档版本不能创建需求",
            "product_id": product["id"],
            "title": "归档版本需求",
            "version_id": archived["id"],
        },
        headers=headers,
    )
    assert requirement.status_code == 400
    assert requirement.json()["detail"]["code"] == "PRODUCT_VERSION_ARCHIVED"


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
