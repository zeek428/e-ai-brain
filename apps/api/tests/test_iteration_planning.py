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
        json={"code": "planning-product", "name": "规划产品"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "2026Q3", "name": "2026 Q3", "status": "planning"},
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
        "version_id": version["id"],
    }


def test_iteration_suggestions_generate_from_real_evidence_and_convert_after_decision():
    admin_headers = auth_headers()
    context = create_product_context(admin_headers)
    feedback = client.post(
        "/api/insights/user-feedback",
        json={
            "content": "知识检索结果命中率偏低。",
            "feedback_type": "improvement",
            "module_code": context["module_code"],
            "product_id": context["product_id"],
            "satisfaction_score": 2,
            "sentiment": "negative",
        },
        headers=admin_headers,
    ).json()["data"]
    bug = client.post(
        "/api/bugs",
        json={
            "description": "搜索排序偶发返回过期方案。",
            "module_code": context["module_code"],
            "product_id": context["product_id"],
            "severity": "major",
            "source": "manual_test",
            "title": "搜索排序返回过期方案",
            "version_id": context["version_id"],
        },
        headers=admin_headers,
    ).json()["data"]

    before_requirements = client.get("/api/requirements", headers=admin_headers).json()["data"]
    generated = client.post(
        "/api/planning/iteration-suggestions",
        json={
            "constraints": {"max_suggestions": 2},
            "module_codes": [context["module_code"]],
            "planning_cycle": "2026Q3",
            "product_id": context["product_id"],
            "version_id": context["version_id"],
        },
        headers=admin_headers,
    ).json()["data"]

    assert generated["total"] == 1
    suggestion = generated["items"][0]
    assert suggestion["id"].startswith("suggestion_")
    assert suggestion["status"] == "suggested"
    assert suggestion["confidence_level"] == "medium"
    assert suggestion["priority"] == "P1"
    assert suggestion["product_id"] == context["product_id"]
    assert suggestion["version_id"] == context["version_id"]
    assert [
        (evidence["subject_type"], evidence["subject_id"])
        for evidence in suggestion["evidence"]
    ] == [
        ("user_feedback", feedback["id"]),
        ("bug", bug["id"]),
    ]
    after_generate_requirements = client.get("/api/requirements", headers=admin_headers).json()[
        "data"
    ]
    assert after_generate_requirements["total"] == before_requirements["total"]

    listed = client.get(
        (
            "/api/planning/iteration-suggestions"
            f"?product_id={context['product_id']}&planning_cycle=2026Q3&status=suggested"
        ),
        headers=admin_headers,
    ).json()["data"]
    assert [item["id"] for item in listed["items"]] == [suggestion["id"]]

    decided = client.post(
        f"/api/planning/iteration-suggestions/{suggestion['id']}/decide",
        json={
            "comment": "采纳为下阶段需求。",
            "convert_to_requirement": True,
            "decision": "edited_accepted",
            "edited_scope": "先优化知识中心搜索排序和召回。",
            "edited_title": "优化知识检索召回与排序",
        },
        headers=admin_headers,
    ).json()["data"]

    assert decided["status"] == "converted_to_requirement"
    assert decided["decision"] == "edited_accepted"
    assert decided["converted_requirement_id"].startswith("requirement_")
    requirement = client.get(
        f"/api/requirements?product_id={context['product_id']}",
        headers=admin_headers,
    ).json()["data"]["items"][0]
    assert requirement["id"] == decided["converted_requirement_id"]
    assert requirement["title"] == "优化知识检索召回与排序"
    assert requirement["status"] == "pending_approval"

    audit_events = client.get(
        f"/api/audit/events?subject_type=iteration_plan_suggestion&subject_id={suggestion['id']}",
        headers=admin_headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == [
        "iteration_suggestion.decided",
        "iteration_suggestion.generated",
    ]


def test_iteration_suggestions_reject_invalid_context_and_roles():
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_product_context(admin_headers)

    forbidden = client.post(
        "/api/planning/iteration-suggestions",
        json={
            "planning_cycle": "2026Q3",
            "product_id": context["product_id"],
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN"

    missing_product = client.post(
        "/api/planning/iteration-suggestions",
        json={
            "planning_cycle": "2026Q3",
            "product_id": "product_missing",
        },
        headers=admin_headers,
    )
    assert missing_product.status_code == 404
    assert missing_product.json()["detail"]["code"] == "NOT_FOUND"
