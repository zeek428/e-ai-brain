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


def create_product_and_version(
    headers: dict[str, str],
    *,
    product_status: str = "active",
) -> tuple[dict[str, str], dict[str, str]]:
    product = client.post(
        "/api/products",
        json={"code": "rd-platform", "name": "研发大脑平台", "status": product_status},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1 MVP", "status": "active"},
        headers=headers,
    ).json()["data"]
    return product, version


def test_requirement_list_detail_reject_and_close_state_machine():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers)

    first = client.post(
        "/api/requirements",
        json={
            "title": "需求状态机",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "需求需要可列表、可详情、可驳回、可关闭。",
        },
        headers=headers,
    ).json()["data"]
    second = client.post(
        "/api/requirements",
        json={
            "title": "待审批过滤",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "需求列表支持按产品和状态过滤。",
        },
        headers=headers,
    ).json()["data"]

    pending = client.get(
        f"/api/requirements?product_id={product['id']}&status=pending_approval",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in pending["items"]] == [second["id"], first["id"]]

    reject_without_reason = client.post(
        f"/api/requirements/{first['id']}/reject",
        json={},
        headers=headers,
    )
    assert reject_without_reason.status_code == 400
    assert reject_without_reason.json()["detail"]["code"] == "VALIDATION_ERROR"

    rejected = client.post(
        f"/api/requirements/{first['id']}/reject",
        json={"rejection_reason": "目标边界不清晰"},
        headers=headers,
    ).json()["data"]
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "目标边界不清晰"

    closed = client.post(f"/api/requirements/{first['id']}/close", headers=headers).json()["data"]
    assert closed["status"] == "closed"

    generate_from_closed = client.post(
        f"/api/requirements/{first['id']}/generate-task",
        headers=headers,
    )
    assert generate_from_closed.status_code == 409
    assert generate_from_closed.json()["detail"]["code"] == "REQUIREMENT_STATE_INVALID"

    detail = client.get(f"/api/requirements/{first['id']}", headers=headers).json()["data"]
    assert detail["status"] == "closed"
    assert detail["task_ids"] == []

    audit_events = client.get(
        f"/api/audit/events?subject_type=requirement&subject_id={first['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in audit_events] == [
        "requirement.closed",
        "requirement.rejected",
        "requirement.created",
    ]


def test_requirement_can_start_in_backlog_and_be_planned_into_iteration_version():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers)

    requirement = client.post(
        "/api/requirements",
        json={
            "title": "未排期需求",
            "product_id": product["id"],
            "content": "新增需求时还不知道在哪个版本迭代。",
        },
        headers=headers,
    ).json()["data"]
    assert requirement["status"] == "submitted"
    assert requirement["version_id"] is None

    approved = client.post(
        f"/api/requirements/{requirement['id']}/approve",
        json={"comment": "进入需求池"},
        headers=headers,
    ).json()["data"]
    assert approved["status"] == "approved"
    assert approved["version_id"] is None

    generate_before_planning = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    )
    assert generate_before_planning.status_code == 409
    assert generate_before_planning.json()["detail"]["code"] == "REQUIREMENT_STATE_INVALID"

    planned = client.patch(
        f"/api/requirements/{requirement['id']}",
        json={"version_id": version["id"]},
        headers=headers,
    ).json()["data"]
    assert planned["status"] == "planned"
    assert planned["version_id"] == version["id"]

    generated = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    assert generated["task_status"] == "draft"

    detail = client.get(f"/api/requirements/{requirement['id']}", headers=headers).json()["data"]
    assert detail["status"] == "designing"
    assert detail["task_ids"] == [generated["task_id"]]


def test_requirement_list_returns_product_and_iteration_version_projection():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers)

    requirement = client.post(
        "/api/requirements",
        json={
            "title": "聚合查询需求",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "列表接口需要直接返回产品和迭代版本展示字段。",
        },
        headers=headers,
    ).json()["data"]

    listed = client.get("/api/requirements", headers=headers).json()["data"]["items"][0]

    assert listed["id"] == requirement["id"]
    assert listed["product_code"] == product["code"]
    assert listed["product_name"] == product["name"]
    assert listed["version_code"] == version["code"]
    assert listed["version_name"] == version["name"]


def test_product_versions_batch_list_returns_product_projection():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers)

    response = client.get("/api/product-versions?active_only=true", headers=headers)

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items == [
        {
            **version,
            "product_code": product["code"],
            "product_name": product["name"],
        }
    ]


def test_requirement_cannot_be_created_for_inactive_product():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers, product_status="inactive")

    response = client.post(
        "/api/requirements",
        json={
            "title": "无效产品",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "inactive 产品不能继续创建需求。",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PRODUCT_INACTIVE"
