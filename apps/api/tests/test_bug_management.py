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
        json={"code": "rd-platform", "name": "研发大脑平台"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1 MVP"},
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


def create_bug(headers: dict[str, str], context: dict[str, str], **overrides) -> dict[str, object]:
    payload = {
        "description": "viewer 能看到 rd 权限 chunk。",
        "module_code": context["module_code"],
        "product_id": context["product_id"],
        "severity": "critical",
        "source": "ai_auto_test",
        "title": "知识检索权限过滤异常",
        "version_id": context["version_id"],
    }
    payload.update(overrides)
    return client.post("/api/bugs", json=payload, headers=headers).json()["data"]


def test_bug_management_creates_filters_and_updates_state_machine():
    headers = auth_headers()
    context = create_product_context(headers)

    bug = create_bug(headers, context)
    assert bug["status"] == "needs_info"
    assert bug["source"] == "ai_auto_test"
    assert bug["severity"] == "critical"
    other_version = client.post(
        f"/api/products/{context['product_id']}/versions",
        json={"code": "v2", "name": "v2 验收"},
        headers=headers,
    ).json()["data"]

    filtered = client.get(
        (
            f"/api/bugs?product_id={context['product_id']}"
            f"&status=needs_info&version_id={context['version_id']}"
        ),
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in filtered["items"]] == [bug["id"]]
    assert filtered["items"][0]["version_code"] == "v1"
    assert filtered["items"][0]["version_name"] == "v1 MVP"

    other_version_bugs = client.get(
        (
            f"/api/bugs?product_id={context['product_id']}"
            f"&version_id={other_version['id']}"
        ),
        headers=headers,
    ).json()["data"]
    assert other_version_bugs["items"] == []

    triaged = client.patch(
        f"/api/bugs/{bug['id']}",
        json={
            "evidence": {"test_run_id": "test_run_001"},
            "reproduce_steps": ["使用 viewer 登录", "搜索受限关键词"],
            "status": "triaged",
        },
        headers=headers,
    ).json()["data"]
    assert triaged["status"] == "triaged"

    assigned = client.patch(
        f"/api/bugs/{bug['id']}",
        json={"assignee": "rd_owner@example.com", "status": "assigned"},
        headers=headers,
    ).json()["data"]
    assert assigned["assignee"] == "rd_owner@example.com"
    assert assigned["status"] == "assigned"

    for next_status in ["fixed", "verified", "closed"]:
        updated = client.patch(
            f"/api/bugs/{bug['id']}",
            json={"status": next_status},
            headers=headers,
        ).json()["data"]
        assert updated["status"] == next_status

    audit_events = client.get(
        f"/api/audit/events?subject_type=bug&subject_id={bug['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == [
        "bug.updated",
        "bug.updated",
        "bug.updated",
        "bug.updated",
        "bug.updated",
        "bug.created",
    ]


def test_bug_duplicate_merge_keeps_duplicate_out_of_open_queue():
    headers = auth_headers()
    context = create_product_context(headers)
    primary = create_bug(
        headers,
        context,
        reproduce_steps=["打开知识检索", "搜索受限内容"],
        source="manual_test",
    )

    duplicate = create_bug(
        headers,
        context,
        duplicate_of_bug_id=primary["id"],
        source="manual_test",
        title="重复的权限过滤异常",
    )

    assert duplicate["status"] == "closed"
    assert duplicate["duplicate_of_bug_id"] == primary["id"]
    open_bugs = client.get(
        f"/api/bugs?product_id={context['product_id']}&status=open",
        headers=headers,
    ).json()["data"]["items"]
    assert [item["id"] for item in open_bugs] == [primary["id"]]


def test_bug_management_rejects_invalid_context_state_and_roles():
    headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")
    context = create_product_context(headers)

    forbidden = client.post(
        "/api/bugs",
        json={
            "description": "reviewer 不应登记 Bug。",
            "product_id": context["product_id"],
            "severity": "major",
            "source": "manual_test",
            "title": "越权登记",
        },
        headers=reviewer_headers,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN"

    bug = create_bug(
        headers,
        context,
        reproduce_steps=["打开知识检索", "搜索受限内容"],
        source="manual_test",
    )
    invalid_transition = client.patch(
        f"/api/bugs/{bug['id']}",
        json={"status": "verified"},
        headers=headers,
    )
    assert invalid_transition.status_code == 409
    assert invalid_transition.json()["detail"]["code"] == "BUG_STATE_INVALID"

    invalid_version = client.post(
        "/api/bugs",
        json={
            "description": "版本不属于产品。",
            "product_id": context["product_id"],
            "severity": "major",
            "source": "manual_test",
            "title": "错配版本",
            "version_id": "version_missing",
        },
        headers=headers,
    )
    assert invalid_version.status_code == 404
    assert invalid_version.json()["detail"]["code"] == "NOT_FOUND"
