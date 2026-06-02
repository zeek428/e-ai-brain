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
        json={"code": "pending-attr-product", "name": "待归属测试产品"},
        headers=headers,
    ).json()["data"]


def test_pending_attribution_items_are_real_empty_lists_without_placeholders():
    app.state.store.reset()
    headers = auth_headers()

    response = client.get("/api/attribution/pending-items", headers=headers)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body == {"items": [], "total": 0}


def test_pending_attribution_create_resolve_filter_and_audit():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)

    created = client.post(
        "/api/attribution/pending-items",
        json={
            "source_type": "user_feedback",
            "source_system": "feedback-api",
            "raw_subject_id": "feedback-ext-42",
            "summary": "Cannot map module search-v2",
            "raw_payload": {"module_hint": "search-v2"},
            "suggested_module_code": "search",
            "confidence": 0.44,
        },
        headers=headers,
    )
    assert created.status_code == 200
    item = created.json()["data"]
    assert item["id"].startswith("pending_attr_")
    assert item["status"] == "pending"
    assert item["resolved_product_id"] is None

    resolved = client.post(
        f"/api/attribution/pending-items/{item['id']}/resolve",
        json={
            "resolution_action": "link_existing_context",
            "resolved_product_id": product["id"],
            "resolution_note": "Mapped by product owner",
        },
        headers=headers,
    )
    assert resolved.status_code == 200
    resolved_item = resolved.json()["data"]
    assert resolved_item["status"] == "resolved"
    assert resolved_item["resolved_product_id"] == product["id"]
    assert resolved_item["resolved_by"] == "user_admin"
    assert resolved_item["resolved_at"]

    listed = client.get(
        f"/api/attribution/pending-items?status=resolved&source_type=user_feedback&"
        f"resolved_product_id={product['id']}",
        headers=headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == item["id"]

    audit = client.get(
        f"/api/audit/events?subject_type=pending_attribution_item&subject_id={item['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert {event["event_type"] for event in audit} == {
        "pending_attribution.created",
        "pending_attribution.resolved",
    }


def test_pending_attribution_ignore_and_state_permissions():
    app.state.store.reset()
    headers = auth_headers()
    reviewer_headers = auth_headers(username="reviewer@example.com", password="reviewer123")

    forbidden = client.post(
        "/api/attribution/pending-items",
        json={
            "source_type": "gitlab_daily_code_metric",
            "source_system": "gitlab",
            "summary": "Unknown repository",
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403

    created = client.post(
        "/api/attribution/pending-items",
        json={
            "source_type": "gitlab_daily_code_metric",
            "source_system": "gitlab",
            "summary": "Unknown repository",
            "raw_payload": {"repository_path": "unknown/repo"},
        },
        headers=headers,
    ).json()["data"]

    ignored = client.post(
        f"/api/attribution/pending-items/{created['id']}/resolve",
        json={"resolution_action": "ignore_as_noise", "resolution_note": "Test import noise"},
        headers=headers,
    )
    assert ignored.status_code == 200
    assert ignored.json()["data"]["status"] == "ignored"

    second_resolution = client.post(
        f"/api/attribution/pending-items/{created['id']}/resolve",
        json={"resolution_action": "ignore_as_noise"},
        headers=headers,
    )
    assert second_resolution.status_code == 409
    assert second_resolution.json()["detail"]["code"] == "PENDING_ATTRIBUTION_STATE_INVALID"
