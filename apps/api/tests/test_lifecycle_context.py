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


def build_mvp_lifecycle(headers: dict[str, str]) -> tuple[str, str]:
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
            "title": "全流程感知 MVP",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "从需求追踪到设计、方案、Review、回写、知识沉淀和审计。",
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
    client.post(f"/api/writeback/results/{design_task['task_id']}", headers=headers)

    solution_task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "technical_solution",
            "title": "技术方案：全流程感知 MVP",
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
    review_task = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "code_review",
            "title": "Review MR !42",
            "requirement_id": requirement["id"],
            "input": {"gitlab_mr_snapshot_id": snapshot["id"]},
        },
        headers=headers,
    ).json()["data"]
    review_started = client.post(
        f"/api/ai-tasks/{review_task['id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{review_started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    return requirement["id"], product["id"]


def test_lifecycle_context_links_mvp_requirement_downstream_subjects_and_risks(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    requirement_id, product_id = build_mvp_lifecycle(headers)

    context = client.get(
        f"/api/lifecycle/context?subject_type=requirement&subject_id={requirement_id}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]

    assert context["status"] == "available"
    assert context["subject"] == {
        "type": "requirement",
        "id": requirement_id,
        "product_id": product_id,
    }

    downstream = context["downstream"]
    relation_types = {item["relation_type"] for item in downstream}
    assert {
        "generates_product_detail_design",
        "generates_technical_solution",
        "generates_code_review",
        "creates_human_review",
        "creates_mock_issue",
        "creates_knowledge_deposit",
        "creates_audit_event",
    }.issubset(relation_types)

    task_types = {
        item["metadata"].get("task_type")
        for item in downstream
        if item["subject_type"] == "ai_task"
    }
    assert {"product_detail_design", "technical_solution", "code_review"}.issubset(task_types)

    assert any(item["subject_type"] == "code_review_report" for item in downstream)
    assert any(item["subject_type"] == "knowledge_deposit" for item in downstream)
    assert any(item["subject_type"] == "mock_issue" for item in downstream)
    assert any(item["subject_type"] == "audit_event" for item in downstream)

    risk = context["risk_signals"][0]
    assert risk["risk_type"] == "code_review_medium_risk"
    assert risk["source_subject_type"] == "code_review_report"
    assert risk["severity"] == "medium"
    assert "Review" in risk["impact_summary"]
    assert risk["recommendation"]

    assert "automated_testing" in context["missing_context"]
    assert context["summary"]["downstream_count"] == len(downstream)


def test_lifecycle_context_requires_query_anchor():
    headers = auth_headers()

    response = client.get("/api/lifecycle/context", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "LIFECYCLE_SUBJECT_REQUIRED"
