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


def reviewer_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "reviewer@example.com", "password": "reviewer123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_confirmed_product_detail_task(headers: dict[str, str]) -> tuple[dict[str, str], str]:
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
            "title": "生成技术方案",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "审批后需要生成详细设计和技术方案。",
            "priority": "P0",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    generated = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    started = client.post(f"/api/ai-tasks/{generated['task_id']}/start", headers=headers).json()[
        "data"
    ]
    client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    return requirement, generated["task_id"]


def test_technical_solution_requires_confirmed_design_and_exports_markdown():
    headers = auth_headers()
    requirement, design_task_id = create_confirmed_product_detail_task(headers)

    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "technical_solution",
            "title": "技术方案：生成技术方案",
            "requirement_id": requirement["id"],
            "input": {"product_detail_design_task_id": design_task_id},
        },
        headers=headers,
    ).json()["data"]
    assert created["status"] == "draft"

    started = client.post(f"/api/ai-tasks/{created['id']}/start", headers=headers).json()["data"]
    assert started["status"] == "waiting_review"

    confirmed = client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    ).json()["data"]
    assert confirmed["task_status"] == "completed"

    markdown = client.get(f"/api/export/tasks/{created['id']}/markdown", headers=headers)
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert markdown.headers["x-trace-id"].startswith("trace_")
    assert "# 生成技术方案" in markdown.text
    assert "## 产品详细设计" in markdown.text
    assert "## 技术方案" in markdown.text
    assert "审批后需要生成详细设计和技术方案。" in markdown.text


def test_markdown_export_obeys_task_read_permissions():
    headers = auth_headers()
    requirement, design_task_id = create_confirmed_product_detail_task(headers)
    created = client.post(
        "/api/ai-tasks",
        json={
            "task_type": "technical_solution",
            "title": "技术方案：生成技术方案",
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

    forbidden = client.get(
        f"/api/export/tasks/{created['id']}/markdown",
        headers=reviewer_headers(),
    )

    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "FORBIDDEN"
