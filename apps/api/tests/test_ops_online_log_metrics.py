from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_online_log_context(headers: dict[str, str]) -> dict[str, str]:
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "ops-product", "name": "线上运营产品"},
        headers=headers,
    ).json()["data"]
    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "checkout", "name": "结算模块"},
        headers=headers,
    ).json()["data"]
    return {
        "module_code": module["code"],
        "product_id": product["id"],
    }


def test_online_log_metrics_are_recorded_queried_and_audited():
    admin_headers = auth_headers()
    context = create_online_log_context(admin_headers)

    created = client.post(
        "/api/ops/online-log-metrics",
        json={
            "anomaly_summary": "checkout error spike after release",
            "core_event_count": 240,
            "environment": "prod",
            "error_count": 12,
            "module_code": context["module_code"],
            "p95_latency_ms": 318.5,
            "p99_latency_ms": 640.25,
            "product_id": context["product_id"],
            "request_count": 2400,
            "source_channel": "manual_import",
            "status": "collected",
            "top_errors": [
                {"count": 7, "message": "PaymentTimeout"},
                {"count": 5, "message": "InventoryLockFailed"},
            ],
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=admin_headers,
    ).json()["data"]

    assert created["id"].startswith("online_log_metric_")
    assert created["product_id"] == context["product_id"]
    assert created["module_code"] == "checkout"
    assert created["environment"] == "prod"
    assert created["request_count"] == 2400
    assert created["error_count"] == 12
    assert created["error_rate"] == 0.005
    assert created["top_errors"][0]["message"] == "PaymentTimeout"

    listed = client.get(
        (
            "/api/ops/online-log-metrics"
            f"?product_id={context['product_id']}"
            "&module_code=checkout"
            "&environment=prod"
            "&from=2026-06-01T00:30:00Z"
            "&to=2026-06-01T02:00:00Z"
        ),
        headers=admin_headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == created["id"]

    audit_events = client.get(
        f"/api/audit/events?subject_type=online_log_metric&subject_id={created['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == ["online_log_metric.created"]


def test_online_log_metrics_validate_context_roles_and_ranges():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_online_log_context(admin_headers)

    forbidden = client.post(
        "/api/ops/online-log-metrics",
        json={
            "environment": "prod",
            "product_id": context["product_id"],
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN"

    invalid_window = client.post(
        "/api/ops/online-log-metrics",
        json={
            "environment": "prod",
            "product_id": context["product_id"],
            "window_end": "2026-06-01T00:00:00Z",
            "window_start": "2026-06-01T01:00:00Z",
        },
        headers=admin_headers,
    )
    assert invalid_window.status_code == 400
    assert invalid_window.json()["detail"]["code"] == "VALIDATION_ERROR"

    negative_count = client.post(
        "/api/ops/online-log-metrics",
        json={
            "environment": "prod",
            "error_count": -1,
            "product_id": context["product_id"],
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=admin_headers,
    )
    assert negative_count.status_code == 400
    assert negative_count.json()["detail"]["code"] == "VALIDATION_ERROR"

    missing_module = client.post(
        "/api/ops/online-log-metrics",
        json={
            "environment": "prod",
            "module_code": "missing",
            "product_id": context["product_id"],
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=admin_headers,
    )
    assert missing_module.status_code == 404
    assert missing_module.json()["detail"]["code"] == "NOT_FOUND"
