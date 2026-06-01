from fastapi.testclient import TestClient

from app.main import app
from tests.test_technical_solution_export import (
    auth_headers,
    create_confirmed_product_detail_task,
)

client = TestClient(app)


def create_confirmed_technical_solution_task(headers: dict[str, str]) -> tuple[dict[str, str], str]:
    requirement, design_task_id = create_confirmed_product_detail_task(headers)
    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "technical_solution",
            "title": "技术方案：v1.1 后续任务",
            "requirement_id": requirement["id"],
            "input": {"product_detail_design_task_id": design_task_id},
        },
        headers=headers,
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]
    client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    return requirement, created["id"]


def test_development_planning_runs_to_human_review_from_confirmed_technical_solution():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)

    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "development_planning",
            "title": "开发计划：v1.1 后续任务",
            "requirement_id": requirement["id"],
            "input": {"technical_solution_task_id": technical_solution_task_id},
        },
        headers=headers,
    ).json()["data"]
    assert created["status"] == "draft"

    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]

    assert started["status"] == "waiting_review"
    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert detail["output"]["kind"] == "development_planning"
    assert detail["output"]["development_tasks"]
    assert detail["output"]["implementation_steps"]

    confirmed = client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    ).json()["data"]
    assert confirmed == {"review_status": "approved", "task_status": "completed"}

    requirement_detail = client.get(
        f"/api/requirements/{requirement['id']}",
        headers=headers,
    ).json()["data"]
    assert requirement_detail["task_ids"][-1] == created["id"]


def test_automated_testing_approval_creates_ai_auto_test_bugs():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)

    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "automated_testing",
            "title": "自动化测试：v1.1 后续任务",
            "requirement_id": requirement["id"],
            "input": {"technical_solution_task_id": technical_solution_task_id},
        },
        headers=headers,
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]

    assert started["status"] == "waiting_review"
    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert detail["output"]["kind"] == "automated_testing"
    assert detail["output"]["bug_suggestions"]

    confirmed = client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    ).json()["data"]
    assert confirmed["task_status"] == "completed"

    bugs = client.get(
        "/api/bugs?source=ai_auto_test",
        headers=headers,
    ).json()["data"]["items"]
    assert len(bugs) == len(detail["output"]["bug_suggestions"])
    assert bugs[0]["related_task_id"] == created["id"]
    assert bugs[0]["requirement_id"] == requirement["id"]
    assert bugs[0]["source"] == "ai_auto_test"
    assert bugs[0]["status"] == "open"


def test_v1_1_followup_task_requires_confirmed_technical_solution():
    headers = auth_headers()
    requirement, _design_task_id = create_confirmed_product_detail_task(headers)

    response = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "development_planning",
            "title": "开发计划：未确认技术方案",
            "requirement_id": requirement["id"],
            "input": {"technical_solution_task_id": "task_missing"},
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "TECHNICAL_SOLUTION_NOT_CONFIRMED"
