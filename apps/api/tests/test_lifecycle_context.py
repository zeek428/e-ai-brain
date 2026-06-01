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


def build_mvp_lifecycle(headers: dict[str, str]) -> dict[str, str]:
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
    writeback = client.post(
        f"/api/writeback/results/{design_task['task_id']}",
        headers=headers,
    ).json()["data"]

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
    code_review_report_id = app.state.store.ai_tasks[review_task["id"]]["code_review_report_id"]
    design_deposit = next(
        deposit
        for deposit in app.state.store.knowledge_deposits.values()
        if deposit["ai_task_id"] == design_task["task_id"]
    )
    review_audit_event = next(
        event
        for event in app.state.store.audit_events
        if event.get("subject_type") == "human_review"
        and event.get("subject_id") == design_started["review_id"]
        and event["event_type"] == "review.submitted"
    )
    return {
        "requirement_id": requirement["id"],
        "product_id": product["id"],
        "design_task_id": design_task["task_id"],
        "design_review_id": design_started["review_id"],
        "solution_task_id": solution_task["id"],
        "snapshot_id": snapshot["id"],
        "review_task_id": review_task["id"],
        "review_id": review_started["review_id"],
        "code_review_report_id": code_review_report_id,
        "mock_issue_id": writeback["issues"][0]["id"],
        "knowledge_deposit_id": design_deposit["id"],
        "audit_event_id": review_audit_event["id"],
    }


def test_lifecycle_context_links_mvp_requirement_downstream_subjects_and_risks(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)
    requirement_id = lifecycle["requirement_id"]
    product_id = lifecycle["product_id"]

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


def test_lifecycle_context_traces_from_review_and_report_subjects(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)

    review_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=human_review&subject_id={lifecycle['design_review_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]

    assert review_context["subject"] == {
        "type": "human_review",
        "id": lifecycle["design_review_id"],
        "product_id": lifecycle["product_id"],
    }
    assert [item["subject_id"] for item in review_context["upstream"]] == [
        lifecycle["requirement_id"]
    ]
    review_downstream = review_context["downstream"]
    assert {
        item["subject_id"]
        for item in review_downstream
        if item["subject_type"] == "ai_task"
    } == {lifecycle["design_task_id"]}
    assert any(
        item["subject_type"] == "human_review"
        and item["subject_id"] == lifecycle["design_review_id"]
        for item in review_downstream
    )
    assert not any(
        item["subject_type"] == "ai_task"
        and item["subject_id"] == lifecycle["solution_task_id"]
        for item in review_downstream
    )

    report_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=code_review_report&subject_id={lifecycle['code_review_report_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]

    assert report_context["subject"] == {
        "type": "code_review_report",
        "id": lifecycle["code_review_report_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in report_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {lifecycle["review_task_id"]}
    assert report_context["risk_signals"][0]["source_subject_id"] == lifecycle[
        "code_review_report_id"
    ]


def test_lifecycle_context_traces_from_writeback_deposit_and_audit_subjects(monkeypatch):
    install_real_gitlab_api_stub(monkeypatch)
    headers = auth_headers()
    lifecycle = build_mvp_lifecycle(headers)

    writeback_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=mock_issue&subject_id={lifecycle['mock_issue_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]
    assert writeback_context["subject"] == {
        "type": "mock_issue",
        "id": lifecycle["mock_issue_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in writeback_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {lifecycle["design_task_id"]}

    deposit_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=knowledge_deposit&subject_id={lifecycle['knowledge_deposit_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]
    assert deposit_context["subject"] == {
        "type": "knowledge_deposit",
        "id": lifecycle["knowledge_deposit_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in deposit_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {lifecycle["design_task_id"]}

    audit_context = client.get(
        "/api/lifecycle/context"
        f"?subject_type=audit_event&subject_id={lifecycle['audit_event_id']}"
        "&direction=both&include_risks=true",
        headers=headers,
    ).json()["data"]
    assert audit_context["subject"] == {
        "type": "audit_event",
        "id": lifecycle["audit_event_id"],
        "product_id": lifecycle["product_id"],
    }
    assert {
        item["subject_id"]
        for item in audit_context["downstream"]
        if item["subject_type"] == "ai_task"
    } == {lifecycle["design_task_id"]}


def test_lifecycle_context_rejects_unknown_subject_type():
    headers = auth_headers()

    response = client.get(
        "/api/lifecycle/context?subject_type=unknown_subject&subject_id=subject_1",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
