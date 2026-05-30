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


def reset_store() -> None:
    app.state.store.reset()


def test_requirement_to_product_detail_design_human_review_flow():
    reset_store()
    headers = auth_headers()

    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台", "owner_team": "AI Platform"},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1 MVP"},
        headers=headers,
    ).json()["data"]
    module = client.post(
        f"/api/products/{product['id']}/modules",
        json={"code": "requirements", "name": "需求管理"},
        headers=headers,
    ).json()["data"]
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain API",
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
            "credential_ref": "secret/gitlab-readonly",
        },
        headers=headers,
    ).json()["data"]

    assert repository["git_provider"] == "gitlab"
    assert "credential_secret" not in repository

    requirement_response = client.post(
        "/api/requirements",
        json={
            "title": "支持需求审批闭环",
            "product_id": product["id"],
            "version_id": version["id"],
            "module_code": module["code"],
            "content": "作为产品负责人，我希望审批后的需求生成产品详细设计任务。",
            "priority": "P0",
        },
        headers=headers,
    )
    requirement = requirement_response.json()["data"]
    assert requirement["status"] == "pending_approval"

    approved = client.post(
        f"/api/requirements/{requirement['id']}/approve",
        json={"comment": "进入 MVP-A"},
        headers=headers,
    ).json()["data"]
    assert approved["status"] == "approved"

    generated = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    task_id = generated["task_id"]
    assert generated["task_type"] == "product_detail_design"
    assert generated["task_status"] == "draft"

    started = client.post(f"/api/ai-tasks/{task_id}/start", headers=headers).json()["data"]
    assert started["status"] == "waiting_review"
    review_id = started["review_id"]

    pending_reviews = client.get("/api/reviews/pending", headers=headers).json()["data"]["items"]
    assert [review["id"] for review in pending_reviews] == [review_id]

    review_result = client.post(
        f"/api/reviews/{review_id}/approve",
        json={"version": 1},
        headers=headers,
    ).json()["data"]
    assert review_result["review_status"] == "approved"
    assert review_result["task_status"] == "completed"

    task_detail = client.get(f"/api/ai-tasks/{task_id}", headers=headers).json()["data"]
    assert task_detail["status"] == "completed"
    assert task_detail["requirement_snapshot"]["title"] == "支持需求审批闭环"
    assert task_detail["output_json"]["kind"] == "product_detail_design"

    audit_events = client.get(f"/api/audit/events?ai_task_id={task_id}", headers=headers).json()[
        "data"
    ]["items"]
    assert [event["event_type"] for event in audit_events] == [
        "review.submitted",
        "human_review.created",
        "ai_task.started",
        "model_gateway.called",
        "ai_task.created",
    ]
