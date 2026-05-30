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


def create_draft_task(headers: dict[str, str]) -> dict[str, str]:
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
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "API 契约补齐",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "补齐文档声明的基础查询和取消接口。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    generated = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    return {
        "requirement_id": requirement["id"],
        "task_id": generated["task_id"],
    }


def test_brain_apps_and_task_list_contracts_are_available():
    headers = auth_headers()
    context = create_draft_task(headers)

    brain_apps = client.get("/api/brain-apps", headers=headers).json()["data"]
    assert brain_apps["items"][0]["code"] == "rd_brain"
    assert brain_apps["items"][0]["status"] == "active"

    tasks = client.get(
        "/api/ai-tasks?status=draft&task_type=product_detail_design",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in tasks["items"]] == [context["task_id"]]


def test_review_detail_cancel_task_and_knowledge_document_list_contracts():
    headers = auth_headers()
    context = create_draft_task(headers)
    cancelled = client.post(
        f"/api/ai-tasks/{context['task_id']}/cancel",
        headers=headers,
    ).json()["data"]
    assert cancelled["status"] == "cancelled"

    second_context = create_draft_task(headers)
    started = client.post(
        f"/api/ai-tasks/{second_context['task_id']}/start",
        headers=headers,
    ).json()["data"]
    review = client.get(
        f"/api/reviews/{started['review_id']}",
        headers=headers,
    ).json()["data"]
    assert review["id"] == started["review_id"]
    assert review["version"] == 1

    document = client.post(
        "/api/knowledge/documents",
        json={"title": "API 契约文档", "content": "contract search source"},
        headers=headers,
    ).json()["data"]
    documents = client.get("/api/knowledge/documents", headers=headers).json()["data"]
    assert [item["id"] for item in documents["items"]] == [document["id"]]
