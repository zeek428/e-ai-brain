from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product(headers: dict[str, str]) -> dict:
    return client.post(
        "/api/products",
        json={"code": "collector-product", "name": "采集运行产品"},
        headers=headers,
    ).json()["data"]


def test_collector_runs_return_real_empty_list_without_placeholder_rows():
    app.state.store.reset()
    headers = auth_headers()

    response = client.get("/api/collectors/runs", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "total": 0}


def test_collector_run_create_patch_filter_and_audit():
    app.state.store.reset()
    admin_headers = auth_headers()
    product = create_product(admin_headers)

    created = client.post(
        "/api/collectors/runs",
        json={
            "collector_type": "gitlab_daily_code_metric",
            "product_id": product["id"],
            "source_system": "gitlab",
            "status": "running",
            "payload_summary": {"repository_path": "rd/api"},
        },
        headers=admin_headers,
    )

    assert created.status_code == 200
    run = created.json()["data"]
    assert run["id"].startswith("collector_run_")
    assert run["collector_type"] == "gitlab_daily_code_metric"
    assert run["product_id"] == product["id"]
    assert run["records_imported"] == 0
    assert run["finished_at"] is None

    patched = client.patch(
        f"/api/collectors/runs/{run['id']}",
        json={"status": "succeeded", "records_imported": 3},
        headers=admin_headers,
    )

    assert patched.status_code == 200
    updated = patched.json()["data"]
    assert updated["status"] == "succeeded"
    assert updated["records_imported"] == 3
    assert updated["finished_at"]

    listed = client.get(
        f"/api/collectors/runs?collector_type=gitlab_daily_code_metric&product_id={product['id']}",
        headers=admin_headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == run["id"]

    audit = client.get(
        f"/api/audit/events?subject_type=collector_run&subject_id={run['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert {event["event_type"] for event in audit} == {
        "collector_run.created",
        "collector_run.updated",
    }


def test_collector_runs_validate_state_context_and_permissions():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    product = create_product(admin_headers)

    forbidden = client.post(
        "/api/collectors/runs",
        json={
            "collector_type": "gitlab_daily_code_metric",
            "product_id": product["id"],
            "source_system": "gitlab",
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN"

    invalid_product = client.post(
        "/api/collectors/runs",
        json={
            "collector_type": "gitlab_daily_code_metric",
            "product_id": "product_missing",
            "source_system": "gitlab",
        },
        headers=admin_headers,
    )
    assert invalid_product.status_code == 404
    assert invalid_product.json()["detail"]["code"] == "NOT_FOUND"

    failed_without_error = client.post(
        "/api/collectors/runs",
        json={
            "collector_type": "online_log_metric",
            "product_id": product["id"],
            "source_system": "elk",
            "status": "failed",
        },
        headers=admin_headers,
    )
    assert failed_without_error.status_code == 400
    assert failed_without_error.json()["detail"]["code"] == "VALIDATION_ERROR"

    created = client.post(
        "/api/collectors/runs",
        json={
            "collector_type": "user_feedback",
            "product_id": product["id"],
            "source_system": "feedback-api",
        },
        headers=admin_headers,
    ).json()["data"]

    terminal = client.patch(
        f"/api/collectors/runs/{created['id']}",
        json={"status": "cancelled"},
        headers=admin_headers,
    )
    assert terminal.status_code == 200

    reopen = client.patch(
        f"/api/collectors/runs/{created['id']}",
        json={"status": "running"},
        headers=admin_headers,
    )
    assert reopen.status_code == 409
    assert reopen.json()["detail"]["code"] == "COLLECTOR_RUN_STATE_INVALID"

    forbidden_update = client.patch(
        f"/api/collectors/runs/{created['id']}",
        json={"records_imported": 1},
        headers=reviewer_headers,
    )
    assert forbidden_update.status_code == 403
    assert forbidden_update.json()["detail"]["code"] == "FORBIDDEN"
