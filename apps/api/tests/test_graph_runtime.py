from importlib import import_module

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPECTED_LANGGRAPH_NODE_PATH = [
    "retrieve_context",
    "generate_task_output",
    "interrupt_for_human_review",
]


def test_ai_task_graph_is_compiled_by_langgraph():
    try:
        graph_runtime = import_module("app.core.graph_runtime")
    except ModuleNotFoundError as exc:
        pytest.fail(f"graph runtime module missing: {exc}")

    compiled_graph = graph_runtime.build_ai_task_graph()

    assert type(compiled_graph).__module__.startswith("langgraph.")
    result = graph_runtime.run_ai_task_graph(
        {
            "id": "task_001",
            "task_type": "product_detail_design",
            "status": "running",
            "output_json": {"kind": "product_detail_design"},
        },
        review_id="review_001",
    )
    assert result["runtime"] == "langgraph"
    assert result["node_path"] == EXPECTED_LANGGRAPH_NODE_PATH
    assert result["current_step"] == "interrupt_for_human_review"
    assert result["task_status"] == "waiting_review"


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_design_task(headers: dict[str, str]) -> str:
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
            "title": "Graph Runtime 可追踪",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "任务启动后需要记录 graph run 和 checkpoint。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    return task["task_id"]


def test_starting_task_creates_graph_run_checkpoint_and_task_detail_projection():
    headers = auth_headers()
    task_id = create_design_task(headers)

    started = client.post(f"/api/ai-tasks/{task_id}/start", headers=headers).json()["data"]
    assert started["status"] == "waiting_review"
    assert started["graph_run_id"].startswith("graph_run_")
    assert started["checkpoint_id"].startswith("checkpoint_")
    assert started["current_step"] == "interrupt_for_human_review"

    runs = client.get(f"/api/graph-runs?ai_task_id={task_id}", headers=headers).json()["data"]
    assert runs["total"] == 1
    run = runs["items"][0]
    assert run["id"] == started["graph_run_id"]
    assert run["ai_task_id"] == task_id
    assert run["status"] == "interrupted"
    assert run["runtime"] == "langgraph"
    assert run["node_path"] == EXPECTED_LANGGRAPH_NODE_PATH
    assert run["current_step"] == "interrupt_for_human_review"
    assert run["checkpoint_id"] == started["checkpoint_id"]
    assert run["state_snapshot"]["task_status"] == "waiting_review"
    assert run["state_snapshot"]["review_id"] == started["review_id"]
    assert run["state_snapshot"]["graph_runtime"]["package"] == "langgraph"
    assert run["state_snapshot"]["graph_runtime"]["node_path"] == EXPECTED_LANGGRAPH_NODE_PATH

    task_detail = client.get(f"/api/ai-tasks/{task_id}", headers=headers).json()["data"]
    assert task_detail["current_step"] == "interrupt_for_human_review"
    assert task_detail["pending_review"]["id"] == started["review_id"]
    assert [run_item["id"] for run_item in task_detail["graph_runs"]] == [started["graph_run_id"]]
    assert task_detail["input"]["requirement_id"] == task_detail["requirement_id"]
    assert task_detail["output"]["kind"] == "product_detail_design"

    client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    completed_detail = client.get(f"/api/ai-tasks/{task_id}", headers=headers).json()["data"]
    assert completed_detail["pending_review"] is None
    assert completed_detail["current_step"] == "complete_archive"
    assert completed_detail["graph_runs"][0]["status"] == "completed"
