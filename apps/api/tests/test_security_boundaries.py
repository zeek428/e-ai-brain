from fastapi.testclient import TestClient
from gitlab_fakes import install_real_gitlab_api_stub

from app.main import app, settings

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_draft_product_detail_design_task(headers: dict[str, str]) -> str:
    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1 MVP"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "权限边界验证",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "任务读写必须遵守任务类型角色边界。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    return task["task_id"]


def test_gitlab_review_api_surface_has_no_writeback_routes():
    paths = client.get("/openapi.json").json()["paths"]
    gitlab_paths = {
        path: methods
        for path, methods in paths.items()
        if path.startswith("/api/devops/gitlab/merge-requests")
    }

    assert set(gitlab_paths) == {
        "/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/preview",
        "/api/devops/gitlab/merge-requests/{repository_id}/{mr_iid}/snapshot",
    }
    for path in gitlab_paths:
        assert "/comments" not in path
        assert "/approvals" not in path
        assert "/request-changes" not in path
        assert not path.endswith("/merge")


def test_role_boundaries_for_product_audit_and_gitlab_preview(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    forbidden_product = client.post(
        "/api/products",
        json={"code": "forbidden", "name": "Reviewer Cannot Maintain Products"},
        headers=reviewer_headers,
    )
    assert forbidden_product.status_code == 403
    assert forbidden_product.json()["detail"]["code"] == "FORBIDDEN"

    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台"},
        headers=admin_headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain API",
            "remote_url": "https://gitlab.example.com/platform/ai-brain.git",
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
            "credential_ref": "env:GITLAB_READONLY_TOKEN",
        },
        headers=admin_headers,
    ).json()["data"]

    preview = client.get(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/42/preview",
        headers=reviewer_headers,
    )
    assert preview.status_code == 200
    assert preview.json()["data"]["writeback_allowed"] is False

    audit = client.get("/api/audit/events", headers=reviewer_headers)
    assert audit.status_code == 403
    assert audit.json()["detail"]["code"] == "FORBIDDEN"

    filtered_audit = client.get(
        "/api/audit/events?event_type=product.created",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert len(filtered_audit) == 1
    assert filtered_audit[0]["event_type"] == "product.created"
    assert filtered_audit[0]["created_at"].startswith("20")


def test_seeded_default_users_are_disabled_outside_local_env():
    original_env = settings.app_env
    original_persistence_mode = settings.persistence_mode
    settings.app_env = "production"
    try:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
        settings.persistence_mode = "postgres"
        postgres_response = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
    finally:
        settings.app_env = original_env
        settings.persistence_mode = original_persistence_mode

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DEFAULT_CREDENTIALS_DISABLED"
    assert postgres_response.status_code == 403
    assert postgres_response.json()["detail"]["code"] == "DEFAULT_CREDENTIALS_DISABLED"


def test_reviewer_cannot_start_or_read_product_design_tasks_and_reviews():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    task_id = create_draft_product_detail_design_task(admin_headers)

    forbidden_start = client.post(f"/api/ai-tasks/{task_id}/start", headers=reviewer_headers)
    assert forbidden_start.status_code == 403
    assert forbidden_start.json()["detail"]["code"] == "FORBIDDEN"

    reviewer_tasks = client.get("/api/ai-tasks", headers=reviewer_headers).json()["data"]
    assert reviewer_tasks["items"] == []

    forbidden_detail = client.get(f"/api/ai-tasks/{task_id}", headers=reviewer_headers)
    assert forbidden_detail.status_code == 403
    assert forbidden_detail.json()["detail"]["code"] == "FORBIDDEN"

    started = client.post(f"/api/ai-tasks/{task_id}/start", headers=admin_headers).json()["data"]
    pending_reviews = client.get("/api/reviews/pending", headers=reviewer_headers).json()["data"]
    assert pending_reviews["items"] == []

    forbidden_review = client.get(
        f"/api/reviews/{started['review_id']}",
        headers=reviewer_headers,
    )
    assert forbidden_review.status_code == 403
    assert forbidden_review.json()["detail"]["code"] == "FORBIDDEN"
