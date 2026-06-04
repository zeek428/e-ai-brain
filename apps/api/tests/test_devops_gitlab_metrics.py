from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_gitlab_context(headers: dict[str, str]) -> dict[str, str]:
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "devops-product", "name": "研发运营产品"},
        headers=headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "default_branch": "main",
            "git_provider": "gitlab",
            "name": "devops-api",
            "project_path": "rd/devops-api",
            "remote_url": "https://gitlab.internal/rd/devops-api.git",
            "repo_type": "code",
            "root_path": "/",
        },
        headers=headers,
    ).json()["data"]
    return {
        "product_id": product["id"],
        "repository_id": repository["id"],
    }


def test_gitlab_daily_code_metrics_are_recorded_queried_and_audited():
    admin_headers = auth_headers()
    context = create_gitlab_context(admin_headers)

    created = client.post(
        "/api/devops/gitlab/daily-code-metrics",
        json={
            "active_author_count": 4,
            "additions": 320,
            "author_metrics": [
                {"author": "alice", "commit_count": 3, "changed_lines": 180},
                {"author": "bob", "commit_count": 2, "changed_lines": 140},
            ],
            "changed_files": 18,
            "commit_count": 7,
            "deletions": 48,
            "metric_date": "2026-06-01",
            "merge_request_count": 2,
            "product_id": context["product_id"],
            "quality_score": 88.5,
            "repository_id": context["repository_id"],
            "risk_count": 1,
            "source_channel": "manual_import",
            "status": "collected",
        },
        headers=admin_headers,
    ).json()["data"]

    assert created["id"].startswith("gitlab_metric_")
    assert created["product_id"] == context["product_id"]
    assert created["repository_id"] == context["repository_id"]
    assert created["commit_count"] == 7
    assert created["quality_score"] == 88.5
    assert created["author_metrics"][0]["author"] == "alice"

    listed = client.get(
        (
            "/api/devops/gitlab/daily-code-metrics"
            f"?product_id={context['product_id']}"
            f"&repository_id={context['repository_id']}"
            "&date=2026-06-01"
        ),
        headers=admin_headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == created["id"]

    audit_events = client.get(
        f"/api/audit/events?subject_type=gitlab_daily_code_metric&subject_id={created['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == ["gitlab_daily_code_metric.created"]


def test_gitlab_daily_code_metrics_validate_context_roles_and_ranges():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_gitlab_context(admin_headers)

    forbidden = client.post(
        "/api/devops/gitlab/daily-code-metrics",
        json={
            "metric_date": "2026-06-01",
            "product_id": context["product_id"],
            "repository_id": context["repository_id"],
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN"

    invalid_score = client.post(
        "/api/devops/gitlab/daily-code-metrics",
        json={
            "metric_date": "2026-06-01",
            "product_id": context["product_id"],
            "quality_score": 120,
            "repository_id": context["repository_id"],
        },
        headers=admin_headers,
    )
    assert invalid_score.status_code == 400
    assert invalid_score.json()["detail"]["code"] == "VALIDATION_ERROR"

    missing_repository = client.post(
        "/api/devops/gitlab/daily-code-metrics",
        json={
            "metric_date": "2026-06-01",
            "product_id": context["product_id"],
            "repository_id": "repo_missing",
        },
        headers=admin_headers,
    )
    assert missing_repository.status_code == 404
    assert missing_repository.json()["detail"]["code"] == "NOT_FOUND"


def test_devops_operational_metrics_support_server_pagination_sort_and_filters():
    admin_headers = auth_headers()
    context = create_gitlab_context(admin_headers)
    version = client.post(
        f"/api/products/{context['product_id']}/versions",
        json={"code": "v2.0.0", "name": "v2.0.0"},
        headers=admin_headers,
    ).json()["data"]

    client.post(
        "/api/devops/gitlab/daily-code-metrics",
        json={
            "commit_count": 3,
            "metric_date": "2026-06-01",
            "product_id": context["product_id"],
            "repository_id": context["repository_id"],
            "status": "collected",
        },
        headers=admin_headers,
    )
    release = client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "build-20260601-ops",
            "environment": "prod",
            "job_name": "enterprise-ai-brain-deploy",
            "product_id": context["product_id"],
            "status": "success",
            "version_id": version["id"],
        },
        headers=admin_headers,
    ).json()["data"]

    filtered = client.get(
        (
            "/api/devops/operational-metrics"
            "?category=Jenkins 发布"
            "&name=ai-brain"
            "&status=success"
            "&page=1&page_size=1"
            "&sort_by=updated_at&sort_order=desc"
        ),
        headers=admin_headers,
    ).json()["data"]

    assert filtered["total"] == 1
    assert filtered["page"] == 1
    assert filtered["page_size"] == 1
    assert filtered["items"][0]["id"] == release["id"]
    assert filtered["items"][0]["category"] == "Jenkins 发布"
    assert filtered["items"][0]["name"] == "enterprise-ai-brain-deploy"

    invalid_sort = client.get(
        "/api/devops/operational-metrics?page=1&page_size=10&sort_by=unsupported",
        headers=admin_headers,
    )
    assert invalid_sort.status_code == 400
    assert invalid_sort.json()["detail"]["code"] == "VALIDATION_ERROR"
