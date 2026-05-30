from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


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


def test_role_boundaries_for_product_audit_and_gitlab_preview():
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
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
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
