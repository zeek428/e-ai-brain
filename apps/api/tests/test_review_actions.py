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


def create_waiting_review_task(headers: dict[str, str]) -> tuple[str, str]:
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
            "title": "人工确认状态机",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "确认动作需要覆盖修改采纳、驳回和补充信息。",
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
    return task["task_id"], started["review_id"]


def test_edit_approve_updates_output_and_completes_task():
    headers = auth_headers()
    task_id, review_id = create_waiting_review_task(headers)

    result = client.post(
        f"/api/reviews/{review_id}/edit-approve",
        json={"version": 1, "edited_content": {"summary": "人工修改后的详细设计"}},
        headers=headers,
    ).json()["data"]

    assert result["review_status"] == "edited_approved"
    assert result["task_status"] == "completed"
    detail = client.get(f"/api/ai-tasks/{task_id}", headers=headers).json()["data"]
    assert detail["output_json"]["summary"] == "人工修改后的详细设计"


def test_reject_and_request_more_info_move_task_to_documented_states():
    headers = auth_headers()
    _task_id, review_id = create_waiting_review_task(headers)
    rejected = client.post(
        f"/api/reviews/{review_id}/reject",
        json={"version": 1, "decision_reason": "缺少边界说明"},
        headers=headers,
    ).json()["data"]
    assert rejected["review_status"] == "rejected"
    assert rejected["task_status"] == "failed"

    task_id, review_id = create_waiting_review_task(headers)
    more_info = client.post(
        f"/api/reviews/{review_id}/request-more-info",
        json={"version": 1, "questions": ["请补充验收边界"]},
        headers=headers,
    ).json()["data"]
    assert more_info["review_status"] == "requested_more_info"
    assert more_info["task_status"] == "waiting_more_info"

    submitted = client.post(
        f"/api/ai-tasks/{task_id}/more-info",
        json={"answers": [{"question": "请补充验收边界", "answer": "补充 P0 验收边界"}]},
        headers=headers,
    ).json()["data"]
    assert submitted["status"] == "draft"


def test_review_version_conflict_returns_documented_error_code():
    headers = auth_headers()
    _task_id, review_id = create_waiting_review_task(headers)

    conflict = client.post(
        f"/api/reviews/{review_id}/approve",
        json={"version": 2},
        headers=headers,
    )

    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "REVIEW_VERSION_CONFLICT"
