from fastapi.testclient import TestClient

from app.main import app
from tests.requirement_fixtures import seed_accepted_assessment_provenance

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
    seed_accepted_assessment_provenance(app.state.store, requirement)
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


def test_approve_executor_review_uses_nested_summary_for_knowledge_deposit():
    headers = auth_headers()
    app.state.store.reset()
    task_id = "task_executor_review"
    review_id = "review_executor_review"
    now = "2026-07-03T21:15:00+00:00"
    app.state.store.ai_tasks[task_id] = {
        "id": task_id,
        "task_type": "code_inspection_remediation",
        "title": "[Code Inspection Remediation] 硬编码敏感凭据",
        "status": "waiting_review",
        "current_step": "executor_completed",
        "product_id": "product_119",
        "version_id": None,
        "module_id": None,
        "requirement_id": None,
        "created_by": "user_admin",
        "created_at": now,
        "updated_at": now,
        "input_json": {},
        "output_json": {
            "executor": {"status": "succeeded", "executor_type": "codex"},
            "result": {
                "exit_code": 0,
                "summary": "已完成硬编码敏感凭据整改。",
                "output_preview": "Codex executor completed successfully.",
            },
        },
        "graph_run_ids": [],
    }
    app.state.store.human_reviews[review_id] = {
        "id": review_id,
        "ai_task_id": task_id,
        "stage": "code_inspection_remediation",
        "status": "pending",
        "version": 1,
        "content": app.state.store.snapshot(app.state.store.ai_tasks[task_id]["output_json"]),
        "edited_content": None,
        "created_by": "user_admin",
        "decided_by": None,
        "decided_at": None,
        "created_at": now,
        "updated_at": now,
    }

    response = client.post(
        f"/api/reviews/{review_id}/approve",
        json={"version": 1},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {"review_status": "approved", "task_status": "completed"}
    deposits = list(app.state.store.knowledge_deposits.values())
    assert len(deposits) == 1
    assert deposits[0]["content"] == "已完成硬编码敏感凭据整改。"


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

    direct_restart = client.post(f"/api/ai-tasks/{task_id}/start", headers=headers)
    assert direct_restart.status_code == 409
    assert direct_restart.json()["detail"]["code"] == "TASK_STATE_INVALID"

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
