from fastapi.testclient import TestClient

from app.main import app
from tests.test_technical_solution_export import auth_headers
from tests.test_v1_1_task_types import create_confirmed_technical_solution_task

client = TestClient(app)


def create_codex_runner(headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/system/ai-executor-runners",
        json={
            "executor_types": ["codex"],
            "name": "本地 Codex 研发执行器",
            "protocol": "runner_polling",
            "runner_token": "runner-secret",
            "workspace_roots": ["/Users/zeek/source/e-ai-brain"],
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_rd_task_executor_policy_queues_runner_and_creates_review_on_success():
    headers = auth_headers()
    requirement, technical_solution_task_id = create_confirmed_technical_solution_task(headers)
    runner = create_codex_runner(headers)

    policy_response = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "codex",
            "instruction_template": (
                "处理任务 {{task_id}} / {{task_title}}，需求 {{requirement_id}}。"
            ),
            "name": "开发计划走 Codex",
            "output_contract": {"summary": "string"},
            "priority": 10,
            "product_id": requirement["product_id"],
            "runner_id": runner["id"],
            "status": "active",
            "task_type": "development_planning",
            "timeout_seconds": 600,
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert policy_response.status_code == 200
    policy = policy_response.json()["data"]
    assert policy["executor_type"] == "codex"
    assert policy["runner_id"] == runner["id"]
    assert "agent" not in policy
    assert "skill" not in policy

    created = client.post(
        "/api/ai-tasks",
        json={
            "input": {"technical_solution_task_id": technical_solution_task_id},
            "requirement_id": requirement["id"],
            "task_type": "development_planning",
            "title": "开发计划：走本地执行器",
        },
        headers=headers,
    ).json()["data"]

    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers)
    assert started.status_code == 200
    start_payload = started.json()["data"]
    assert start_payload["status"] == "running"
    assert start_payload["current_step"] == "waiting_ai_executor"
    assert start_payload["executor_policy_id"] == policy["id"]
    assert start_payload["runner_id"] == runner["id"]

    runner_task_id = start_payload["executor_task_id"]
    claimed = client.post(
        "/api/system/ai-executor-tasks/claim",
        json={"executor_type": "codex", "runner_id": runner["id"]},
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert claimed.status_code == 200
    claimed_task = claimed.json()["data"]["task"]
    assert claimed_task["id"] == runner_task_id
    assert claimed_task["ai_task_id"] == created["id"]
    assert claimed_task["instruction"].startswith(f"处理任务 {created['id']}")

    completed = client.post(
        f"/api/system/ai-executor-tasks/{runner_task_id}/complete",
        json={
            "logs": [{"level": "info", "message": "codex finished"}],
            "result_json": {"summary": "开发计划已生成", "tasks": ["补充接口", "联调页面"]},
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers={"X-Runner-Token": "runner-secret"},
    )
    assert completed.status_code == 200

    detail = client.get(f"/api/ai-tasks/{created['id']}", headers=headers).json()["data"]
    assert detail["status"] == "waiting_review"
    assert detail["current_step"] == "executor_completed"
    assert detail["input"]["executor"]["runner_task_id"] == runner_task_id
    assert detail["output"]["executor"]["runner_id"] == runner["id"]
    assert detail["output"]["result"]["summary"] == "开发计划已生成"
    assert detail["pending_review"]["status"] == "pending"
    assert detail["pending_review"]["stage"] == "development_planning"

    runner_tasks = client.get(
        f"/api/system/ai-executor-tasks?ai_task_id={created['id']}",
        headers=headers,
    ).json()["data"]
    assert runner_tasks["total"] == 1
    assert runner_tasks["items"][0]["id"] == runner_task_id


def test_rd_task_executor_policy_rejects_agent_and_skill_fields():
    headers = auth_headers()
    app.state.store.reset()
    runner = create_codex_runner(headers)

    rejected = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "agent_id": "agent_001",
            "executor_type": "codex",
            "instruction_template": "不应允许 Agent 或 Skill 字段",
            "name": "错误策略",
            "runner_id": runner["id"],
            "skill_ids": ["skill_001"],
            "task_type": "development_planning",
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert rejected.status_code == 422


def test_rd_task_executor_policy_rejects_model_gateway_executor():
    headers = auth_headers()
    app.state.store.reset()
    runner = create_codex_runner(headers)

    rejected = client.post(
        "/api/delivery/rd-task-executor-policies",
        json={
            "executor_type": "model_gateway",
            "instruction_template": "不应允许模型网关作为研发工程执行器",
            "name": "错误策略",
            "runner_id": runner["id"],
            "task_type": "development_planning",
            "workspace_root": "/Users/zeek/source/e-ai-brain",
        },
        headers=headers,
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["code"] == "VALIDATION_ERROR"
