from fastapi.testclient import TestClient
from gitlab_fakes import install_real_gitlab_api_stub

from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def build_mr_snapshot(headers: dict[str, str]) -> tuple[str, str]:
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
    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        json={
            "name": "AI Brain API",
            "remote_url": "https://gitlab.example.com/platform/ai-brain.git",
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
            "credential_ref": "env:GITLAB_READONLY_TOKEN",
        },
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "内部 MR Code Review",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "需要基于 MR diff 生成内部代码 Review 报告。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    design_task = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    design_started = client.post(
        f"/api/ai-tasks/{design_task['task_id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{design_started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    solution_task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "technical_solution",
            "title": "技术方案：内部 MR Code Review",
            "requirement_id": requirement["id"],
            "input": {"product_detail_design_task_id": design_task["task_id"]},
        },
        headers=headers,
    ).json()["data"]
    solution_started = client.post(
        f"/api/ai-tasks/{solution_task['id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{solution_started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    snapshot = client.post(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/42/snapshot",
        json={
            "requirement_id": requirement["id"],
            "technical_solution_task_id": solution_task["id"],
        },
        headers=headers,
    ).json()["data"]
    return requirement["id"], snapshot["id"]


def test_code_review_report_is_confirmed_and_archived_without_gitlab_writeback(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, snapshot_id = build_mr_snapshot(headers)

    task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42",
            "requirement_id": requirement_id,
            "input": {"gitlab_mr_snapshot_id": snapshot_id},
        },
        headers=headers,
    ).json()["data"]
    assert task["status"] == "draft"

    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers).json()["data"]
    assert started["status"] == "waiting_review"

    pending_report = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert pending_report["status"] == "pending_review"
    assert pending_report["risk_level"] == "medium"
    assert pending_report["findings"][0]["severity"] == "high"
    assert pending_report["gitlab_writeback_performed"] is False

    confirmed = client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    ).json()["data"]
    assert confirmed["task_status"] == "completed"

    archived = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert archived["status"] == "confirmed"
    assert archived["archived_at"].startswith("20")
    assert archived["gitlab_writeback_performed"] is False

    audit_response = client.get(
        f"/api/audit/events?ai_task_id={task['id']}",
        headers=headers,
    )
    event_types = [event["event_type"] for event in audit_response.json()["data"]["items"]]
    assert event_types == [
        "review.submitted",
        "human_review.created",
        "code_review.generated",
        "ai_task.started",
        "model_gateway.called",
        "ai_task.created",
    ]


def test_code_review_report_edit_approve_also_confirms_and_archives_report(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, snapshot_id = build_mr_snapshot(headers)

    task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42 with edits",
            "requirement_id": requirement_id,
            "input": {"gitlab_mr_snapshot_id": snapshot_id},
        },
        headers=headers,
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers).json()["data"]

    result = client.post(
        f"/api/reviews/{started['review_id']}/edit-approve",
        json={
            "version": 1,
            "edited_content": {
                "summary": "人工确认后保留一处高风险问题并补充边界测试建议。"
            },
        },
        headers=headers,
    ).json()["data"]

    assert result["task_status"] == "completed"
    archived = client.get(
        f"/api/ai-tasks/{task['id']}/code-review-report",
        headers=headers,
    ).json()["data"]
    assert archived["status"] == "confirmed"
    assert archived["archived_at"].startswith("20")
    assert archived["summary"] == "人工确认后保留一处高风险问题并补充边界测试建议。"
    assert archived["gitlab_writeback_performed"] is False
