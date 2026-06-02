from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_later_phase_entries_return_empty_lists_without_fake_data():
    headers = auth_headers()
    endpoints = [
        "/api/devops/gitlab/daily-code-metrics",
        "/api/devops/jenkins/releases",
        "/api/ops/online-log-metrics",
        "/api/insights/usage-metrics",
        "/api/insights/user-feedback",
        "/api/planning/iteration-suggestions",
    ]

    for endpoint in endpoints:
        body = client.get(endpoint, headers=headers).json()
        assert body["trace_id"].startswith("trace_")
        assert body["data"]["items"] == []
        assert body["data"]["total"] == 0
        assert "placeholder" not in body["data"]
        assert "available_phase" not in body["data"]


def test_dashboard_it_team_returns_real_mvp_aggregate_without_fake_rows():
    app.state.store.reset()
    headers = auth_headers()
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
    pending_requirement = client.post(
        "/api/requirements",
        json={
            "content": "进入首页看板待审批需求统计。",
            "product_id": product["id"],
            "title": "首页看板待审批需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    approved_requirement = client.post(
        "/api/requirements",
        json={
            "content": "进入首页看板 AI 任务统计。",
            "product_id": product["id"],
            "title": "首页看板任务需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/requirements/{approved_requirement['id']}/approve",
        json={},
        headers=headers,
    )
    generated = client.post(
        f"/api/requirements/{approved_requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    started = client.post(
        f"/api/ai-tasks/{generated['task_id']}/start",
        headers=headers,
    ).json()["data"]
    knowledge = client.post(
        "/api/knowledge/documents",
        json={
            "content": "dashboard knowledge source",
            "permission_roles": ["admin"],
            "product_id": product["id"],
            "title": "首页看板知识",
        },
        headers=headers,
    ).json()["data"]
    other_product = client.post(
        "/api/products",
        json={"code": "unrelated", "name": "无关产品"},
        headers=headers,
    ).json()["data"]
    unrelated_knowledge = client.post(
        "/api/knowledge/documents",
        json={
            "content": "unrelated dashboard knowledge source",
            "permission_roles": ["admin"],
            "product_id": other_product["id"],
            "title": "无关产品知识",
        },
        headers=headers,
    ).json()["data"]

    dashboard = client.get(
        f"/api/dashboard/it-team?product_id={product['id']}&time_range=7d",
        headers=headers,
    ).json()["data"]

    assert dashboard["summary"]["active_products"] == 1
    assert dashboard["summary"]["ai_tasks"] == 1
    assert dashboard["summary"]["audit_events"] < len(app.state.store.audit_events)
    assert dashboard["summary"]["knowledge_deposits"] == 0
    assert dashboard["summary"]["knowledge_documents"] == 1
    assert dashboard["summary"]["pending_reviews"] == 1
    assert dashboard["summary"]["requirements"] == 2
    assert {"status": "pending_approval", "count": 1} in dashboard["requirement_status_counts"]
    assert {"status": "task_created", "count": 1} in dashboard["requirement_status_counts"]
    assert dashboard["task_status_counts"] == [{"status": "waiting_review", "count": 1}]
    assert dashboard["latest_tasks"][0]["id"] == generated["task_id"]
    assert dashboard["pending_reviews"][0]["id"] == started["review_id"]
    assert dashboard["recent_knowledge_documents"][0]["id"] == knowledge["id"]
    assert all(
        event["subject_id"] != unrelated_knowledge["id"]
        for event in dashboard["recent_audit_events"]
    )
    assert "items" not in dashboard
    assert pending_requirement["title"] in dashboard["requirement_titles"]
