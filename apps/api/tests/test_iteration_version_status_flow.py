from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers(username: str = "admin@example.com", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_product(headers: dict[str, str], code: str) -> dict[str, str]:
    return client.post(
        "/api/products",
        json={"code": code, "name": code},
        headers=headers,
    ).json()["data"]


def create_version(
    headers: dict[str, str],
    product_id: str,
    code: str,
    status: str = "planning",
) -> dict[str, str]:
    response = client.post(
        f"/api/products/{product_id}/versions",
        json={"code": code, "name": code, "status": status},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["data"]


def create_requirement(
    headers: dict[str, str],
    product_id: str,
    title: str,
    version_id: str,
) -> dict[str, str]:
    return client.post(
        "/api/requirements",
        json={
            "content": f"{title} 内容",
            "priority": "P1",
            "product_id": product_id,
            "title": title,
            "version_id": version_id,
        },
        headers=headers,
    ).json()["data"]


def approve_requirement(headers: dict[str, str], requirement_id: str) -> dict[str, str]:
    return client.post(
        f"/api/requirements/{requirement_id}/approve",
        json={"comment": "进入版本范围"},
        headers=headers,
    ).json()["data"]


def set_requirement_status(requirement_id: str, status: str) -> None:
    app.state.store.requirements[requirement_id]["status"] = status


def set_version_status(version_id: str, status: str) -> None:
    app.state.store.product_versions[version_id]["status"] = status


def get_requirement(headers: dict[str, str], requirement_id: str) -> dict[str, str]:
    return client.get(f"/api/requirements/{requirement_id}", headers=headers).json()["data"]


def test_advancing_planning_version_to_active_moves_planned_requirements_to_ready_for_dev():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-flow-active")
    version = create_version(headers, product["id"], "2026-07", status="planning")
    requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "启动开发需求", version["id"])["id"],
    )

    response = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"reason": "版本进入开发", "target_status": "active"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["from_status"] == "planning"
    assert data["target_status"] == "active"
    assert data["version"]["status"] == "active"
    assert data["blocked_requirements"] == []
    assert data["updated_requirements"] == [
        {
            "from_status": "planned",
            "id": requirement["id"],
            "title": "启动开发需求",
            "to_status": "ready_for_dev",
        }
    ]
    assert get_requirement(headers, requirement["id"])["status"] == "ready_for_dev"

    audits = client.get(
        f"/api/audit/events?subject_type=product_version&subject_id={version['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert "product_version.status_advanced" in [event["event_type"] for event in audits]


def test_advancing_active_version_to_testing_previews_blocks_and_allows_forced_transition():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-flow-testing")
    version = create_version(headers, product["id"], "2026-08", status="active")
    planned_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "仍未开发需求", version["id"])["id"],
    )
    review_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "已评审需求", version["id"])["id"],
    )
    set_requirement_status(review_requirement["id"], "code_reviewing")

    preview = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"preview_only": True, "target_status": "testing"},
        headers=headers,
    )

    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["preview_only"] is True
    assert preview_data["version"]["status"] == "active"
    assert preview_data["updated_requirements"] == [
        {
            "from_status": "code_reviewing",
            "id": review_requirement["id"],
            "title": "已评审需求",
            "to_status": "testing",
        }
    ]
    assert preview_data["blocked_requirements"] == [
        {
            "block_reason": "需求尚未完成开发评审，进入测试会形成版本风险",
            "id": planned_requirement["id"],
            "status": "planned",
            "title": "仍未开发需求",
        }
    ]
    assert get_requirement(headers, review_requirement["id"])["status"] == "code_reviewing"

    blocked = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"target_status": "testing"},
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "PRODUCT_VERSION_STATUS_BLOCKED"

    forced = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"force": True, "reason": "带风险进入测试", "target_status": "testing"},
        headers=headers,
    )

    assert forced.status_code == 200
    forced_data = forced.json()["data"]
    assert forced_data["version"]["status"] == "testing"
    assert get_requirement(headers, review_requirement["id"])["status"] == "testing"
    assert get_requirement(headers, planned_requirement["id"])["status"] == "planned"
    assert forced_data["blocked_requirements"][0]["id"] == planned_requirement["id"]


def test_advancing_testing_version_to_released_blocks_unfinished_requirements():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-flow-release")
    version = create_version(headers, product["id"], "2026-09", status="active")
    testing_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "测试完成需求", version["id"])["id"],
    )
    ready_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "待发布需求", version["id"])["id"],
    )
    unfinished_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "开发中需求", version["id"])["id"],
    )
    set_requirement_status(testing_requirement["id"], "testing")
    set_requirement_status(ready_requirement["id"], "ready_for_release")
    set_requirement_status(unfinished_requirement["id"], "developing")
    set_version_status(version["id"], "testing")

    blocked = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"force": True, "target_status": "released"},
        headers=headers,
    )

    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "PRODUCT_VERSION_STATUS_BLOCKED"
    assert get_requirement(headers, testing_requirement["id"])["status"] == "testing"

    set_requirement_status(unfinished_requirement["id"], "deferred")
    released = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"reason": "版本发布", "target_status": "released"},
        headers=headers,
    )

    assert released.status_code == 200
    released_data = released.json()["data"]
    assert released_data["version"]["status"] == "released"
    assert {
        item["id"]: item["to_status"]
        for item in released_data["updated_requirements"]
    } == {
        testing_requirement["id"]: "released",
        ready_requirement["id"]: "released",
    }
    assert get_requirement(headers, testing_requirement["id"])["status"] == "released"
    assert get_requirement(headers, ready_requirement["id"])["status"] == "released"
    assert get_requirement(headers, unfinished_requirement["id"])["status"] == "deferred"

    archived = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        json={"reason": "版本历史归档", "target_status": "archived"},
        headers=headers,
    )

    assert archived.status_code == 200
    archived_data = archived.json()["data"]
    assert archived_data["version"]["status"] == "archived"
    assert archived_data["blocked_requirements"] == []
    assert {item["id"] for item in archived_data["unchanged_requirements"]} == {
        testing_requirement["id"],
        ready_requirement["id"],
        unfinished_requirement["id"],
    }


def test_direct_version_status_patch_requires_advance_endpoint():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "version-flow-direct-patch")
    version = create_version(headers, product["id"], "2026-10", status="planning")

    response = client.patch(
        f"/api/product-versions/{version['id']}",
        json={"status": "active"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "PRODUCT_VERSION_STATUS_ADVANCE_REQUIRED"
