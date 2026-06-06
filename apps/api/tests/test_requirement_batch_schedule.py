from fastapi.testclient import TestClient

from app.main import app
from app.services.requirements import save_audit_event

client = TestClient(app)


class FakeAuditRepository:
    def __init__(self) -> None:
        self.appended: list[dict[str, str]] = []
        self.save_called = False

    def append_audit_event(self, audit_event: dict[str, str]) -> None:
        self.appended.append(audit_event)

    def save_audit_events(self, payload: dict[str, object]) -> None:
        self.save_called = True


class FakeRepositoryStore:
    def __init__(self, repository: FakeAuditRepository) -> None:
        self.repository = repository


def test_single_batch_audit_is_appended_without_replacing_existing_repository_events():
    repository = FakeAuditRepository()
    audit_event = {"event_type": "requirement.batch_scheduled", "id": "audit_new"}

    save_audit_event(FakeRepositoryStore(repository), audit_event)

    assert repository.appended == [audit_event]
    assert repository.save_called is False


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
    return client.post(
        f"/api/products/{product_id}/versions",
        json={"code": code, "name": code, "status": status},
        headers=headers,
    ).json()["data"]


def create_requirement(
    headers: dict[str, str],
    product_id: str,
    title: str,
    version_id: str | None = None,
) -> dict[str, str]:
    payload = {
        "content": f"{title} 内容",
        "priority": "P1",
        "product_id": product_id,
        "title": title,
    }
    if version_id:
        payload["version_id"] = version_id
    return client.post("/api/requirements", json=payload, headers=headers).json()["data"]


def approve_requirement(headers: dict[str, str], requirement_id: str) -> dict[str, str]:
    return client.post(
        f"/api/requirements/{requirement_id}/approve",
        json={"comment": "进入需求池"},
        headers=headers,
    ).json()["data"]


def test_batch_schedule_updates_eligible_requirements_and_records_audit():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "batch-product")
    target_version = create_version(headers, product["id"], "2026-06")
    old_version = create_version(headers, product["id"], "2026-05")
    other_product = create_product(headers, "batch-other")
    other_version = create_version(headers, other_product["id"], "other-v1")

    pool_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "需求池需求")["id"],
    )
    planned_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "已排期需求", old_version["id"])["id"],
    )
    submitted_requirement = create_requirement(headers, product["id"], "待评审需求")
    other_requirement = approve_requirement(
        headers,
        create_requirement(headers, other_product["id"], "其他产品需求", other_version["id"])["id"],
    )

    response = client.post(
        "/api/requirements/batch-schedule",
        json={
            "product_id": product["id"],
            "reason": "归集到 2026-06 迭代",
            "requirement_ids": [
                pool_requirement["id"],
                planned_requirement["id"],
                submitted_requirement["id"],
                other_requirement["id"],
            ],
            "version_id": target_version["id"],
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["batch_id"].startswith("requirement_batch_")
    assert data["product_id"] == product["id"]
    assert data["version_id"] == target_version["id"]
    assert [item["id"] for item in data["updated"]] == [
        pool_requirement["id"],
        planned_requirement["id"],
    ]
    assert {
        item["id"]: item["code"]
        for item in data["skipped"]
    } == {
        submitted_requirement["id"]: "REQUIREMENT_STATE_INVALID",
        other_requirement["id"]: "PRODUCT_MISMATCH",
    }

    listed = client.get(
        f"/api/requirements?product_id={product['id']}",
        headers=headers,
    ).json()["data"]["items"]
    by_id = {item["id"]: item for item in listed}
    assert by_id[pool_requirement["id"]]["status"] == "planned"
    assert by_id[pool_requirement["id"]]["version_id"] == target_version["id"]
    assert by_id[planned_requirement["id"]]["status"] == "planned"
    assert by_id[planned_requirement["id"]]["version_id"] == target_version["id"]
    assert by_id[submitted_requirement["id"]]["status"] == "submitted"
    assert by_id[submitted_requirement["id"]]["version_id"] is None

    batch_audits = client.get(
        f"/api/audit/events?subject_type=requirement_batch&subject_id={data['batch_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in batch_audits] == ["requirement.batch_scheduled"]
    assert batch_audits[0]["payload"]["updated_count"] == 2
    assert batch_audits[0]["payload"]["skipped_count"] == 2

    requirement_audits = client.get(
        f"/api/audit/events?event_type=requirement.updated&subject_id={pool_requirement['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert requirement_audits[0]["payload"]["batch_id"] == data["batch_id"]
    assert requirement_audits[0]["payload"]["from_version_id"] is None
    assert requirement_audits[0]["payload"]["to_version_id"] == target_version["id"]


def test_batch_schedule_rejects_archived_target_version():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "archived-batch-product")
    archived_version = create_version(headers, product["id"], "old", status="archived")
    requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "不可归档版本需求")["id"],
    )

    response = client.post(
        "/api/requirements/batch-schedule",
        json={
            "product_id": product["id"],
            "requirement_ids": [requirement["id"]],
            "version_id": archived_version["id"],
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PRODUCT_VERSION_ARCHIVED"


def test_batch_assign_owner_updates_requirements_and_records_audit():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "batch-owner-product")
    requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "负责人待分配")["id"],
    )
    closed_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "已关闭需求")["id"],
    )
    client.post(f"/api/requirements/{closed_requirement['id']}/close", headers=headers)

    response = client.post(
        "/api/requirements/batch-assign-owner",
        json={
            "assignee": "rd_owner@example.com",
            "reason": "批量归口给研发负责人",
            "requirement_ids": [
                requirement["id"],
                closed_requirement["id"],
                requirement["id"],
                "requirement_missing",
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["batch_id"].startswith("requirement_owner_batch_")
    assert data["assignee"] == "rd_owner@example.com"
    assert data["updated_count"] == 1
    assert data["skipped_count"] == 3
    assert data["updated"][0]["id"] == requirement["id"]
    assert data["updated"][0]["assignee"] == "rd_owner@example.com"
    assert data["skipped"] == [
        {
            "code": "REQUIREMENT_STATE_INVALID",
            "id": closed_requirement["id"],
            "message": "Closed or cancelled requirements cannot be assigned",
        },
        {
            "code": "DUPLICATE_REQUIREMENT",
            "id": requirement["id"],
            "message": "Requirement was already included in this batch",
        },
        {
            "code": "NOT_FOUND",
            "id": "requirement_missing",
            "message": "Requirement not found",
        },
    ]

    detail = client.get(f"/api/requirements/{requirement['id']}", headers=headers).json()["data"]
    assert detail["assignee"] == "rd_owner@example.com"
    batch_audits = client.get(
        f"/api/audit/events?subject_type=requirement_owner_batch&subject_id={data['batch_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in batch_audits] == [
        "requirement.batch_owner_assigned"
    ]
    requirement_audits = client.get(
        f"/api/audit/events?event_type=requirement.updated&subject_id={requirement['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert requirement_audits[0]["payload"]["operation"] == "batch_assign_owner"


def test_batch_advance_status_updates_valid_requirements_and_records_audit():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "batch-status-product")
    version = create_version(headers, product["id"], "batch-status-v1")
    requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "待开发需求", version["id"])["id"],
    )
    unscheduled_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "未排期需求")["id"],
    )
    accepted_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "已验收需求")["id"],
    )
    client.patch(
        f"/api/requirements/{accepted_requirement['id']}",
        json={"version_id": None},
        headers=headers,
    )
    app.state.store.requirements[accepted_requirement["id"]]["status"] = "accepted"

    response = client.post(
        "/api/requirements/batch-advance-status",
        json={
            "reason": "批量推进到待开发",
            "requirement_ids": [
                requirement["id"],
                unscheduled_requirement["id"],
                accepted_requirement["id"],
                requirement["id"],
                "requirement_missing",
            ],
            "target_status": "ready_for_dev",
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["batch_id"].startswith("requirement_status_batch_")
    assert data["target_status"] == "ready_for_dev"
    assert data["updated_count"] == 1
    assert data["skipped_count"] == 4
    assert data["updated"][0]["id"] == requirement["id"]
    assert data["updated"][0]["status"] == "ready_for_dev"
    assert data["skipped"] == [
        {
            "code": "REQUIREMENT_VERSION_REQUIRED",
            "id": unscheduled_requirement["id"],
            "message": "Requirement must be scheduled to a version before advancing to this status",
        },
        {
            "code": "REQUIREMENT_STATE_INVALID",
            "id": accepted_requirement["id"],
            "message": "Requirement cannot be advanced to target status",
        },
        {
            "code": "DUPLICATE_REQUIREMENT",
            "id": requirement["id"],
            "message": "Requirement was already included in this batch",
        },
        {
            "code": "NOT_FOUND",
            "id": "requirement_missing",
            "message": "Requirement not found",
        },
    ]

    detail = client.get(f"/api/requirements/{requirement['id']}", headers=headers).json()["data"]
    assert detail["status"] == "ready_for_dev"
    batch_audits = client.get(
        f"/api/audit/events?subject_type=requirement_status_batch&subject_id={data['batch_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in batch_audits] == [
        "requirement.batch_status_advanced"
    ]
    requirement_audits = client.get(
        f"/api/audit/events?event_type=requirement.updated&subject_id={requirement['id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert requirement_audits[0]["payload"]["operation"] == "batch_advance_status"
    assert requirement_audits[0]["payload"]["to_status"] == "ready_for_dev"


def test_batch_generate_tasks_creates_tasks_for_planned_requirements_and_records_audit():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers, "batch-task-product")
    version = create_version(headers, product["id"], "2026-07")

    first_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "批量生成任务 A", version["id"])["id"],
    )
    second_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "批量生成任务 B", version["id"])["id"],
    )
    pool_requirement = approve_requirement(
        headers,
        create_requirement(headers, product["id"], "未排期需求")["id"],
    )

    response = client.post(
        "/api/requirements/batch-generate-tasks",
        json={
            "product_id": product["id"],
            "reason": "批量进入产品详细设计",
            "requirement_ids": [
                first_requirement["id"],
                second_requirement["id"],
                pool_requirement["id"],
                first_requirement["id"],
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["batch_id"].startswith("requirement_task_batch_")
    assert data["generated_count"] == 2
    assert [item["requirement_id"] for item in data["generated"]] == [
        first_requirement["id"],
        second_requirement["id"],
    ]
    assert [item["task_status"] for item in data["generated"]] == ["draft", "draft"]
    assert {
        item["id"]: item["code"]
        for item in data["skipped"]
    } == {
        pool_requirement["id"]: "REQUIREMENT_STATE_INVALID",
        first_requirement["id"]: "DUPLICATE_REQUIREMENT",
    }

    first_detail = client.get(
        f"/api/requirements/{first_requirement['id']}",
        headers=headers,
    ).json()["data"]
    second_detail = client.get(
        f"/api/requirements/{second_requirement['id']}",
        headers=headers,
    ).json()["data"]
    pool_detail = client.get(
        f"/api/requirements/{pool_requirement['id']}",
        headers=headers,
    ).json()["data"]
    assert first_detail["status"] == "designing"
    assert second_detail["status"] == "designing"
    assert pool_detail["status"] == "approved"
    assert len(first_detail["task_ids"]) == 1
    assert len(second_detail["task_ids"]) == 1
    assert pool_detail["task_ids"] == []

    batch_audits = client.get(
        f"/api/audit/events?subject_type=requirement_task_batch&subject_id={data['batch_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert [event["event_type"] for event in batch_audits] == [
        "requirement.batch_tasks_generated"
    ]
    assert batch_audits[0]["payload"]["generated_count"] == 2
    assert batch_audits[0]["payload"]["skipped_count"] == 2
