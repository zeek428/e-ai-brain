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
        json={"code": "feedback-product", "name": "反馈产品"},
        headers=headers,
    ).json()["data"]
    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "knowledge", "name": "知识中心"},
        headers=headers,
    ).json()["data"]
    return {
        "module_code": module["code"],
        "product_id": product["id"],
    }


def test_user_feedback_supports_create_filter_update_and_audit():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_product_context(admin_headers)

    created = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "知识检索结果经常找不到最近方案。",
            "feature_code": "search",
            "feedback_type": "improvement",
            "module_code": context["module_code"],
            "product_id": context["product_id"],
            "satisfaction_score": 2,
            "sentiment": "negative",
            "source_channel": "in_app",
            "tags": ["search", "relevance"],
        },
        headers=reviewer_headers,
    ).json()["data"]

    assert created["id"].startswith("feedback_")
    assert created["created_by"] == "user_reviewer"
    assert created["status"] == "open"
    assert created["tags"] == ["search", "relevance"]
    assert app.state.store.user_feedback[created["id"]]["status"] == "open"

    filtered = client.get(
        (
            "/api/insights/user-feedback"
            f"?product_id={context['product_id']}&module_code=knowledge&status=open"
        ),
        headers=admin_headers,
    ).json()["data"]
    assert filtered["total"] == 1
    assert [item["id"] for item in filtered["items"]] == [created["id"]]

    updated = client.patch(
        f"/api/insights/user-feedback/{created['id']}",
        json={
            "status": "triaged",
            "triage_note": "归入知识检索相关性优化。",
        },
        headers=admin_headers,
    ).json()["data"]
    assert updated["status"] == "triaged"
    assert updated["triage_note"] == "归入知识检索相关性优化。"
    assert app.state.store.user_feedback[created["id"]]["status"] == "triaged"

    audit_events = client.get(
        f"/api/audit/events?subject_type=user_feedback&subject_id={created['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == [
        "user_feedback.updated",
        "user_feedback.created",
    ]


def test_user_feedback_can_convert_to_requirement_and_sync_status():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_product_context(admin_headers)

    feedback = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "建议把用户洞察里的有效反馈快速转成需求。",
            "feedback_type": "improvement",
            "module_code": context["module_code"],
            "product_id": context["product_id"],
        },
        headers=reviewer_headers,
    ).json()["data"]

    converted = client.post(
        f"/api/insights/user-feedback/{feedback['id']}/convert-requirement",
        json={
            "priority": "P0",
            "title": "用户反馈快速转需求",
            "triage_note": "反馈有效，进入需求评审。",
        },
        headers=admin_headers,
    ).json()["data"]

    requirement = converted["requirement"]
    linked_feedback = converted["feedback"]
    assert requirement["source"] == "user_feedback"
    assert requirement["product_id"] == context["product_id"]
    assert requirement["module_code"] == context["module_code"]
    assert requirement["priority"] == "P0"
    assert requirement["status"] == "submitted"
    assert linked_feedback["status"] == "linked"
    assert linked_feedback["related_requirement_id"] == requirement["id"]
    assert linked_feedback["triage_note"] == "反馈有效，进入需求评审。"
    assert app.state.store.requirements[requirement["id"]]["source"] == "user_feedback"
    assert app.state.store.user_feedback[feedback["id"]]["status"] == "linked"

    listed = client.get(
        f"/api/requirements?source=user_feedback&product_id={context['product_id']}",
        headers=admin_headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == requirement["id"]

    duplicate = client.post(
        f"/api/insights/user-feedback/{feedback['id']}/convert-requirement",
        json={"title": "重复转需求"},
        headers=admin_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "RESOURCE_IN_USE"


def test_user_feedback_rejects_invalid_context_values_and_update_roles():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_product_context(admin_headers)

    invalid_product = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "产品不存在。",
            "feedback_type": "improvement",
            "product_id": "product_missing",
        },
        headers=admin_headers,
    )
    assert invalid_product.status_code == 404
    assert invalid_product.json()["detail"]["code"] == "NOT_FOUND"

    invalid_score = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "评分超出范围。",
            "feedback_type": "improvement",
            "product_id": context["product_id"],
            "satisfaction_score": 6,
        },
        headers=admin_headers,
    )
    assert invalid_score.status_code == 400
    assert invalid_score.json()["detail"]["code"] == "VALIDATION_ERROR"

    feedback = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "需要产品负责人处理。",
            "feedback_type": "question",
            "product_id": context["product_id"],
        },
        headers=reviewer_headers,
    ).json()["data"]
    forbidden_update = client.patch(
        f"/api/insights/user-feedback/{feedback['id']}",
        json={"status": "resolved"},
        headers=reviewer_headers,
    )
    assert forbidden_update.status_code == 403
    assert forbidden_update.json()["detail"]["code"] == "FORBIDDEN"


def test_user_insight_items_support_server_pagination_sort_and_filters():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_product_context(admin_headers)

    client.post(
        "/api/insights/usage-metrics",
        json={
            "active_users": 20,
            "event_count": 120,
            "feature_code": "dashboard",
            "module_code": context["module_code"],
            "product_id": context["product_id"],
            "user_segment": "admin",
            "window_end": "2026-06-01T01:00:00Z",
            "window_start": "2026-06-01T00:00:00Z",
        },
        headers=admin_headers,
    )
    feedback = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "知识检索详情页需要支持按迭代版本过滤。",
            "feedback_type": "improvement",
            "module_code": context["module_code"],
            "product_id": context["product_id"],
            "source_channel": "in_app",
        },
        headers=reviewer_headers,
    ).json()["data"]

    filtered = client.get(
        (
            "/api/insights/items"
            "?category=用户反馈"
            "&summary=迭代版本"
            "&status=open"
            "&page=1&page_size=1"
            "&sort_by=updated_at&sort_order=desc"
        ),
        headers=admin_headers,
    ).json()["data"]

    assert filtered["total"] == 1
    assert filtered["page"] == 1
    assert filtered["page_size"] == 1
    assert filtered["items"][0]["id"] == feedback["id"]
    assert filtered["items"][0]["category"] == "用户反馈"
    assert filtered["items"][0]["summary"] == "知识检索详情页需要支持按迭代版本过滤。"

    invalid_sort = client.get(
        "/api/insights/items?page=1&page_size=10&sort_by=unsupported",
        headers=admin_headers,
    )
    assert invalid_sort.status_code == 400
    assert invalid_sort.json()["detail"]["code"] == "VALIDATION_ERROR"
