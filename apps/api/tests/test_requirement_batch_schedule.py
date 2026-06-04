from fastapi.testclient import TestClient

from app.main import _save_audit_event, app

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

    _save_audit_event(FakeRepositoryStore(repository), audit_event)

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
