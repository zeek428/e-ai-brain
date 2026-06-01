from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_release_context(headers: dict[str, str]) -> dict[str, str]:
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "release-product", "name": "发布验证产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1.2.0", "name": "v1.2.0"},
        headers=headers,
    ).json()["data"]
    return {
        "product_id": product["id"],
        "version_id": version["id"],
    }


def test_jenkins_releases_are_recorded_queried_and_audited():
    admin_headers = auth_headers()
    context = create_release_context(admin_headers)

    created = client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "build-20260601-17",
            "build_number": 17,
            "commit_sha": "abc123def456",
            "deployed_at": "2026-06-01T12:30:00Z",
            "duration_seconds": 480,
            "environment": "staging",
            "job_name": "rd-platform-deploy",
            "product_id": context["product_id"],
            "source_channel": "manual_import",
            "started_at": "2026-06-01T12:22:00Z",
            "status": "success",
            "trigger_actor": "jenkins-admin",
            "version_id": context["version_id"],
        },
        headers=admin_headers,
    ).json()["data"]

    assert created["id"].startswith("jenkins_release_")
    assert created["product_id"] == context["product_id"]
    assert created["version_id"] == context["version_id"]
    assert created["job_name"] == "rd-platform-deploy"
    assert created["status"] == "success"
    assert created["duration_seconds"] == 480

    listed = client.get(
        (
            "/api/devops/jenkins/releases"
            f"?product_id={context['product_id']}"
            f"&version_id={context['version_id']}"
            "&status=success"
        ),
        headers=admin_headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == created["id"]

    audit_events = client.get(
        f"/api/audit/events?subject_type=jenkins_release&subject_id={created['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == ["jenkins_release.created"]


def test_jenkins_releases_validate_context_roles_and_status():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_release_context(admin_headers)

    forbidden = client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "build-1",
            "job_name": "rd-platform-deploy",
            "product_id": context["product_id"],
            "version_id": context["version_id"],
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN"

    invalid_status = client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "build-2",
            "job_name": "rd-platform-deploy",
            "product_id": context["product_id"],
            "status": "unknown",
            "version_id": context["version_id"],
        },
        headers=admin_headers,
    )
    assert invalid_status.status_code == 400
    assert invalid_status.json()["detail"]["code"] == "VALIDATION_ERROR"

    missing_version = client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "build-3",
            "job_name": "rd-platform-deploy",
            "product_id": context["product_id"],
            "version_id": "version_missing",
        },
        headers=admin_headers,
    )
    assert missing_version.status_code == 404
    assert missing_version.json()["detail"]["code"] == "NOT_FOUND"

    archived_version = client.post(
        f"/api/products/{context['product_id']}/versions",
        json={"code": "v1.2.1-archived", "name": "v1.2.1 archived", "status": "archived"},
        headers=admin_headers,
    ).json()["data"]
    archived_response = client.post(
        "/api/devops/jenkins/releases",
        json={
            "build_id": "build-4",
            "job_name": "rd-platform-deploy",
            "product_id": context["product_id"],
            "version_id": archived_version["id"],
        },
        headers=admin_headers,
    )
    assert archived_response.status_code == 400
    assert archived_response.json()["detail"]["code"] == "PRODUCT_VERSION_ARCHIVED"
