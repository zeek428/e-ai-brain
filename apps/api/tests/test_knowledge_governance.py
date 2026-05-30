from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_completed_design_task(headers: dict[str, str]) -> str:
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
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "知识治理闭环",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "任务产出需要成为知识沉淀候选，并支持模拟 Issue 幂等生成。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task_response = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    )
    task = task_response.json()["data"]
    started = client.post(f"/api/ai-tasks/{task['task_id']}/start", headers=headers).json()["data"]
    client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    return task["task_id"]


def test_knowledge_search_filters_permissions_and_deposits_are_reviewable():
    app.state.store.reset()
    admin_headers = auth_headers()
    reviewer_headers = auth_headers("reviewer@example.com", "reviewer123")

    admin_doc = client.post(
        "/api/knowledge/documents",
        json={
            "title": "管理员策略",
            "content": "admin-only launch policy",
            "permission_roles": ["admin"],
        },
        headers=admin_headers,
    ).json()["data"]
    reviewer_doc = client.post(
        "/api/knowledge/documents",
        json={
            "title": "Review 指南",
            "content": "reviewer code review checklist",
            "permission_roles": ["reviewer"],
        },
        headers=admin_headers,
    ).json()["data"]

    results = client.post(
        "/api/knowledge/search",
        json={"query": "review", "top_k": 5},
        headers=reviewer_headers,
    ).json()["data"]["items"]
    assert [item["document_id"] for item in results] == [reviewer_doc["id"]]
    assert admin_doc["id"] not in [item["document_id"] for item in results]

    task_id = create_completed_design_task(admin_headers)
    deposits = client.get("/api/knowledge/deposits?status=pending", headers=admin_headers).json()[
        "data"
    ]["items"]
    assert deposits[0]["ai_task_id"] == task_id
    assert deposits[0]["status"] == "pending"

    approved = client.post(
        f"/api/knowledge/deposits/{deposits[0]['id']}/approve",
        json={"title": "知识治理闭环沉淀"},
        headers=admin_headers,
    ).json()["data"]
    assert approved["status"] == "approved"
    assert approved["knowledge_document_id"].startswith("knowledge_")


def test_mock_issue_writeback_is_idempotent_for_completed_task():
    app.state.store.reset()
    headers = auth_headers()
    task_id = create_completed_design_task(headers)

    first = client.get(f"/api/writeback/results/{task_id}", headers=headers).json()["data"]
    second = client.get(f"/api/writeback/results/{task_id}", headers=headers).json()["data"]

    assert first["status"] == "completed"
    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["issues"] == second["issues"]
    assert len(first["issues"]) == 1


def test_knowledge_deposit_can_be_rejected_once_with_reason():
    app.state.store.reset()
    headers = auth_headers()
    task_id = create_completed_design_task(headers)
    deposit = client.get("/api/knowledge/deposits?status=pending", headers=headers).json()[
        "data"
    ]["items"][0]

    rejected = client.post(
        f"/api/knowledge/deposits/{deposit['id']}/reject",
        json={"reason": "内容仍需人工整理"},
        headers=headers,
    ).json()["data"]
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "内容仍需人工整理"
    assert rejected["ai_task_id"] == task_id

    second_reject = client.post(
        f"/api/knowledge/deposits/{deposit['id']}/reject",
        json={"reason": "重复驳回"},
        headers=headers,
    )
    assert second_reject.status_code == 409
    assert second_reject.json()["detail"]["code"] == "KNOWLEDGE_DEPOSIT_STATE_INVALID"

    rejected_items = client.get(
        "/api/knowledge/deposits?status=rejected",
        headers=headers,
    ).json()["data"]["items"]
    assert [item["id"] for item in rejected_items] == [deposit["id"]]
