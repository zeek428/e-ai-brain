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


def build_confirmed_solution_context(headers: dict[str, str]) -> dict[str, str]:
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
            "git_provider": "gitlab",
            "project_path": "platform/ai-brain",
            "credential_ref": "secret/gitlab-readonly",
        },
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "title": "Review MR 输入快照",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "需要在代码 Review 前保存 GitLab MR diff 快照。",
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
            "title": "技术方案：Review MR 输入快照",
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
    return {
        "repository_id": repository["id"],
        "requirement_id": requirement["id"],
        "technical_solution_task_id": solution_task["id"],
    }


def test_gitlab_mr_preview_and_snapshot_are_read_only_and_immutable():
    headers = auth_headers()
    context = build_confirmed_solution_context(headers)

    preview = client.get(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/42/preview",
        headers=headers,
    ).json()["data"]
    assert preview["mr_iid"] == 42
    assert preview["project_path"] == "platform/ai-brain"
    assert preview["writeback_allowed"] is False
    assert preview["changed_file_count"] == 2

    snapshot = client.post(
        f"/api/devops/gitlab/merge-requests/{context['repository_id']}/42/snapshot",
        json={
            "requirement_id": context["requirement_id"],
            "technical_solution_task_id": context["technical_solution_task_id"],
        },
        headers=headers,
    ).json()["data"]
    assert snapshot["id"].startswith("snapshot_")
    assert snapshot["mr_iid"] == 42
    assert snapshot["diff_size_bytes"] > 0
    assert snapshot["diff_limit_bytes"] >= snapshot["diff_size_bytes"]
    assert snapshot["snapshot_hash"]
    assert snapshot["writeback_allowed"] is False

    audit_events = client.get(
        f"/api/audit/events?subject_type=gitlab_mr_snapshot&subject_id={snapshot['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == ["gitlab_mr.snapshotted"]
