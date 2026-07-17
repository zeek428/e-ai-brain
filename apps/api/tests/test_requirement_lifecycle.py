from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
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


def test_viewer_cannot_mutate_requirement_management():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers)
    requirement = client.post(
        "/api/requirements",
        json={
            "content": "只读角色不能修改需求管理数据。",
            "product_id": product["id"],
            "title": "Viewer 权限边界",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]

    viewer_username = f"requirement-viewer-{uuid4().hex[:8]}@example.com"
    created_viewer = client.post(
        "/api/users",
        json={
            "display_name": "Requirement Viewer",
            "password": "password123",
            "roles": ["viewer"],
            "status": "active",
            "username": viewer_username,
        },
        headers=headers,
    )
    assert created_viewer.status_code == 200, created_viewer.text
    viewer_headers = auth_headers(viewer_username, "password123")

    mutation_attempts = [
        (
            "post",
            "/api/requirements",
            {
                "content": "viewer 不应能新增需求。",
                "product_id": product["id"],
                "title": "Viewer 新增需求",
            },
        ),
        (
            "patch",
            f"/api/requirements/{requirement['id']}",
            {"title": "viewer 不应能编辑需求"},
        ),
        ("delete", f"/api/requirements/{requirement['id']}", None),
        (
            "post",
            f"/api/requirements/{requirement['id']}/approve",
            {"comment": "viewer 不应能审批"},
        ),
        (
            "post",
            f"/api/requirements/{requirement['id']}/reject",
            {"rejection_reason": "viewer 不应能驳回"},
        ),
        ("post", f"/api/requirements/{requirement['id']}/generate-task", None),
        (
            "post",
            "/api/requirements/batch-schedule",
            {
                "product_id": product["id"],
                "requirement_ids": [requirement["id"]],
                "version_id": version["id"],
            },
        ),
        (
            "post",
            "/api/requirements/batch-assign-owner",
            {"assignee": "viewer", "requirement_ids": [requirement["id"]]},
        ),
        (
            "post",
            "/api/requirements/batch-advance-status",
            {"requirement_ids": [requirement["id"]], "target_status": "ready_for_dev"},
        ),
        (
            "post",
            "/api/requirements/batch-generate-tasks",
            {"product_id": product["id"], "requirement_ids": [requirement["id"]]},
        ),
    ]

    for method_name, path, payload in mutation_attempts:
        request = getattr(client, method_name)
        response = (
            request(path, json=payload, headers=viewer_headers)
            if payload is not None
            else request(path, headers=viewer_headers)
        )
        assert response.status_code == 403, f"{method_name.upper()} {path}: {response.text}"
        assert response.json()["detail"]["code"] == "FORBIDDEN"


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
    app.state.store.requirement_assessments = {
        "accepted-first": {
            "id": "accepted-first",
            "requirement_id": first["id"],
            "status": "accepted",
        }
    }

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
    app.state.store.requirement_assessments = {
        "accepted-backlog": {
            "id": "accepted-backlog",
            "requirement_id": requirement["id"],
            "status": "accepted",
        }
    }

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
    assert planned["status"] == "submitted"
    assert planned["version_id"] == version["id"]
    app.state.store.requirement_assessments["accepted-after-edit"] = {
        "id": "accepted-after-edit",
        "requirement_id": requirement["id"],
        "requirement_revision": planned["assessment_revision"],
        "status": "accepted",
    }
    reapproved = client.post(
        f"/api/requirements/{requirement['id']}/approve",
        json={"comment": "评估更新后重新批准"},
        headers=headers,
    ).json()["data"]
    assert reapproved["status"] == "planned"

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


def test_requirement_source_is_persisted_and_filterable():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers)

    created = client.post(
        "/api/requirements",
        json={
            "content": "产品规划产生的需求需要保留来源。",
            "priority": "P1",
            "product_id": product["id"],
            "source": "product_planning",
            "title": "来源字段需求",
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    assert created["source"] == "product_planning"

    listed = client.get(
        "/api/requirements?source=product_planning&sort_by=source",
        headers=headers,
    ).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == created["id"]
    assert listed["items"][0]["source"] == "product_planning"

    invalid = client.get("/api/requirements?source=unknown", headers=headers)
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_requirement_list_supports_server_pagination_sort_and_filters():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers)
    other_product = client.post(
        "/api/products",
        json={"code": "other-product", "name": "其他产品"},
        headers=headers,
    ).json()["data"]

    for title, target_product_id in [
        ("Alpha 远程查询需求", product["id"]),
        ("Beta 远程查询需求", product["id"]),
        ("Gamma 其他产品需求", other_product["id"]),
    ]:
        client.post(
            "/api/requirements",
            json={
                "content": f"{title} 内容",
                "priority": "P1",
                "product_id": target_product_id,
                "title": title,
                "version_id": version["id"] if target_product_id == product["id"] else None,
            },
            headers=headers,
        )

    first_page = client.get(
        (
            "/api/requirements?title=远程查询&product=rd-platform&version=v1"
            "&page=1&page_size=1&sort_by=title&sort_order=asc"
        ),
        headers=headers,
    ).json()["data"]
    second_page = client.get(
        (
            "/api/requirements?title=远程查询&product=rd-platform&version=v1"
            "&page=2&page_size=1&sort_by=title&sort_order=asc"
        ),
        headers=headers,
    ).json()["data"]

    assert first_page["page"] == 1
    assert first_page["page_size"] == 1
    assert first_page["total"] == 2
    assert [item["title"] for item in first_page["items"]] == ["Alpha 远程查询需求"]
    assert [item["title"] for item in second_page["items"]] == ["Beta 远程查询需求"]

    invalid_sort = client.get(
        "/api/requirements?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )
    assert invalid_sort.status_code == 400
    assert invalid_sort.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_management_lists_include_query_observability_metadata():
    app.state.store.reset()
    headers = auth_headers()
    product, version = create_product_and_version(headers)
    client.post(
        "/api/requirements",
        json={
            "content": "列表查询需要记录性能观测信息。",
            "priority": "P1",
            "product_id": product["id"],
            "title": "查询观测需求",
            "version_id": version["id"],
        },
        headers=headers,
    )

    requirements = client.get(
        (
            "/api/requirements?title=查询观测&product=rd-platform&version=v1"
            "&page=1&page_size=1&sort_by=title&sort_order=asc"
        ),
        headers=headers,
    ).json()["data"]
    tasks = client.get(
        "/api/ai-tasks?status=draft&page=1&page_size=10&sort_by=created_at&sort_order=desc",
        headers=headers,
    ).json()["data"]

    assert requirements["query"] == {
        "filters": {
            "product": "rd-platform",
            "title": "查询观测",
            "version": "v1",
        },
        "name": "requirements",
        "page": 1,
        "page_size": 1,
        "sort_by": "title",
        "sort_order": "asc",
    }
    assert requirements["performance"]["result_count"] == 1
    assert requirements["performance"]["total"] == 1
    assert requirements["performance"]["duration_ms"] >= 0
    assert requirements["performance"]["slow"] is False
    assert requirements["performance"]["slow_threshold_ms"] > 0
    assert tasks["query"]["filters"] == {"status": "draft"}
    assert tasks["query"]["name"] == "ai_tasks"
    assert tasks["performance"]["result_count"] == 0


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


def test_product_versions_batch_list_supports_server_pagination_sort_and_filters():
    app.state.store.reset()
    headers = auth_headers()
    product = client.post(
        "/api/products",
        json={"code": "server-list-product", "name": "服务端查询产品"},
        headers=headers,
    ).json()["data"]
    other_product = client.post(
        "/api/products",
        json={"code": "another-product", "name": "其他产品"},
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "2026-06", "name": "六月迭代", "status": "planning"},
        headers=headers,
    )
    client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "2026-07", "name": "七月迭代", "status": "planning"},
        headers=headers,
    )
    client.post(
        f"/api/products/{other_product['id']}/versions",
        json={"code": "2026-08", "name": "其他迭代", "status": "planning"},
        headers=headers,
    )

    first_page = client.get(
        (
            "/api/product-versions?product=server-list-product&status=planning"
            "&page=1&page_size=1&sort_by=code&sort_order=desc"
        ),
        headers=headers,
    ).json()["data"]
    second_page = client.get(
        (
            "/api/product-versions?product=server-list-product&status=planning"
            "&page=2&page_size=1&sort_by=code&sort_order=desc"
        ),
        headers=headers,
    ).json()["data"]

    assert first_page["page"] == 1
    assert first_page["page_size"] == 1
    assert first_page["total"] == 2
    assert [item["code"] for item in first_page["items"]] == ["2026-07"]
    assert [item["code"] for item in second_page["items"]] == ["2026-06"]


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
