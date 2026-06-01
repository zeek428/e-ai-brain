from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product_context(headers: dict[str, str]) -> dict[str, str]:
    app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": "usage-product", "name": "使用指标产品"},
        headers=headers,
    ).json()["data"]
    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "search", "name": "搜索模块"},
        headers=headers,
    ).json()["data"]
    return {
        "module_code": module["code"],
        "product_id": product["id"],
    }


def test_usage_metrics_are_recorded_queried_and_audited():
    admin_headers = auth_headers()
    context = create_product_context(admin_headers)

    created = client.post(
        "/api/insights/usage-metrics",
        json={
            "active_users": 42,
            "avg_duration_seconds": 36.5,
            "bounce_rate": 0.18,
            "conversion_count": 15,
            "conversion_rate": 0.36,
            "error_count": 2,
            "event_count": 120,
            "feature_code": "semantic-search",
            "module_code": context["module_code"],
            "product_id": context["product_id"],
            "source_channel": "manual_import",
            "user_segment": "rd",
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=admin_headers,
    ).json()["data"]

    assert created["id"].startswith("usage_")
    assert created["active_users"] == 42
    assert created["feature_code"] == "semantic-search"
    assert created["window_start"] == "2026-06-01T00:00:00+00:00"

    listed = client.get(
        (
            "/api/insights/usage-metrics"
            f"?product_id={context['product_id']}&module_code=search"
            "&feature_code=semantic-search&user_segment=rd"
            "&from=2026-06-01T00:30:00Z&to=2026-06-01T02:00:00Z"
        ),
        headers=admin_headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == created["id"]

    audit_events = client.get(
        f"/api/audit/events?subject_type=usage_metric&subject_id={created['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == ["usage_metric.created"]


def test_usage_metrics_validate_context_roles_and_ranges():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_product_context(admin_headers)

    forbidden = client.post(
        "/api/insights/usage-metrics",
        json={
            "feature_code": "semantic-search",
            "product_id": context["product_id"],
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN"

    invalid_range = client.post(
        "/api/insights/usage-metrics",
        json={
            "conversion_rate": 1.5,
            "feature_code": "semantic-search",
            "product_id": context["product_id"],
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=admin_headers,
    )
    assert invalid_range.status_code == 400
    assert invalid_range.json()["detail"]["code"] == "VALIDATION_ERROR"

    missing_product = client.post(
        "/api/insights/usage-metrics",
        json={
            "feature_code": "semantic-search",
            "product_id": "product_missing",
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=admin_headers,
    )
    assert missing_product.status_code == 404
    assert missing_product.json()["detail"]["code"] == "NOT_FOUND"
