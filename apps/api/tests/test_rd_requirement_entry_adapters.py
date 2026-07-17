from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.store import MemoryStore
from app.main import app
from app.services.code_inspection_detail_projection import code_inspection_governance_summary
from app.services.code_inspections import create_tasks_for_findings


client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def create_product(headers: dict[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/products",
        json={"code": "entry-adapter", "name": "入口适配产品", "status": "active"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_requirement(headers: dict[str, str], product_id: str) -> dict[str, str]:
    response = client.post(
        "/api/requirements",
        json={
            "content": "用于验证研发入口必须经由需求适配器。",
            "product_id": product_id,
            "title": "入口适配需求",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def assert_collaboration_required(response) -> None:
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "RD_COLLABORATION_REQUIRED"
    assert detail["details"]["retryable"] is False
    assert detail["details"]["next_action"]


def test_bug_promotion_links_one_open_requirement_instead_of_creating_ai_task():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    bug_response = client.post(
        "/api/bugs",
        json={
            "description": "巡检发现严重问题。",
            "product_id": product["id"],
            "severity": "major",
            "source": "manual_test",
            "title": "入口适配 Bug",
        },
        headers=headers,
    )
    assert bug_response.status_code == 200, bug_response.text
    bug = bug_response.json()["data"]

    first = client.post(f"/api/bugs/{bug['id']}/promote-ai-task", headers=headers)
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    assert first_data["requirement_id"]
    assert first_data.get("ai_task_id") is None
    assert first_data["assessment_url"] == (
        f"/api/requirements/{first_data['requirement_id']}/assessments"
    )
    assert app.state.store.ai_tasks == {}

    second = client.post(f"/api/bugs/{bug['id']}/promote-ai-task", headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["data"]["requirement_id"] == first_data["requirement_id"]
    assert len(app.state.store.requirements) == 1


def test_legacy_requirement_task_generation_endpoints_are_non_mutating_compatibility_errors():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    requirement = create_requirement(headers, product["id"])
    app.state.store.requirements[requirement["id"]]["status"] = "planned"
    before_task_ids = list(app.state.store.requirements[requirement["id"]]["task_ids"])

    assert_collaboration_required(
        client.post(f"/api/requirements/{requirement['id']}/generate-task", headers=headers)
    )
    assert_collaboration_required(
        client.post(
            "/api/requirements/batch-generate-tasks",
            json={"product_id": product["id"], "requirement_ids": [requirement["id"]]},
            headers=headers,
        )
    )
    assert app.state.store.requirements[requirement["id"]]["task_ids"] == before_task_ids
    assert app.state.store.ai_tasks == {}


def test_delivery_batch_advance_rejects_delivery_targets_without_partial_mutation():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    requirement = create_requirement(headers, product["id"])

    assert_collaboration_required(
        client.post(
            "/api/requirements/batch-advance-status",
            json={
                "requirement_ids": [requirement["id"]],
                "target_status": "ready_for_release",
            },
            headers=headers,
        )
    )
    assert app.state.store.requirements[requirement["id"]]["status"] == "submitted"


def _v2_task(*, task_id: str, product_id: str, status: str = "draft") -> dict[str, object]:
    return {
        "brain_app_id": "rd_brain",
        "collaboration_run_id": "run-entry-adapter",
        "created_at": "2026-07-18T00:00:00+00:00",
        "created_by": "user_admin",
        "current_step": "draft",
        "graph_run_ids": [],
        "id": task_id,
        "input_json": {},
        "module_code": None,
        "output_json": None,
        "product_context": {},
        "product_id": product_id,
        "requirement_id": None,
        "requirement_snapshot": None,
        "review_ids": [],
        "status": status,
        "task_type": "product_detail_design",
        "title": task_id,
        "updated_at": "2026-07-18T00:00:00+00:00",
        "version_id": None,
        "work_item_id": "work-item-entry-adapter",
    }


def test_public_v2_task_start_and_cancel_are_rejected_without_state_changes():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    task = _v2_task(task_id="task-v2-entry-adapter", product_id=product["id"])
    app.state.store.ai_tasks[task["id"]] = task

    assert_collaboration_required(client.post(f"/api/ai-tasks/{task['id']}/start", headers=headers))
    assert_collaboration_required(client.post(f"/api/ai-tasks/{task['id']}/cancel", headers=headers))
    assert app.state.store.ai_tasks[task["id"]]["status"] == "draft"


def test_mixed_batch_cancel_with_v2_task_is_atomic():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    legacy_task = _v2_task(task_id="task-legacy-entry-adapter", product_id=product["id"])
    legacy_task.pop("collaboration_run_id")
    legacy_task.pop("work_item_id")
    v2_task = _v2_task(task_id="task-v2-entry-adapter", product_id=product["id"])
    app.state.store.ai_tasks[legacy_task["id"]] = legacy_task
    app.state.store.ai_tasks[v2_task["id"]] = v2_task

    assert_collaboration_required(
        client.post(
            "/api/ai-tasks/batch-cancel",
            json={"task_ids": [legacy_task["id"], v2_task["id"]]},
            headers=headers,
        )
    )
    assert app.state.store.ai_tasks[legacy_task["id"]]["status"] == "draft"
    assert app.state.store.ai_tasks[v2_task["id"]]["status"] == "draft"


def test_public_ai_task_create_and_retry_are_retired_compatibility_entrypoints():
    app.state.store.reset()
    headers = auth_headers()
    product = create_product(headers)
    requirement = create_requirement(headers, product["id"])
    retry_task = _v2_task(
        task_id="task-v2-retry-entry-adapter",
        product_id=product["id"],
        status="failed",
    )
    retry_task["current_step"] = "model_gateway_failed"
    app.state.store.ai_tasks[retry_task["id"]] = retry_task
    assert_collaboration_required(
        client.post(
            "/api/ai-tasks",
            json={
                "input": {},
                "requirement_id": requirement["id"],
                "task_type": "product_detail_design",
                "title": "不应从公开端点创建",
            },
            headers=headers,
        )
    )
    assert_collaboration_required(
        client.post(
            "/api/ai-tasks/batch-retry",
            json={"task_ids": ["task-v2-retry-entry-adapter"]},
            headers=headers,
        )
    )
    assert app.state.store.ai_tasks[retry_task["id"]]["status"] == "failed"


def test_code_inspection_remediation_creates_requirement_and_requirement_coverage():
    current_store = MemoryStore()
    current_store.products["product-entry-adapter"] = {
        "id": "product-entry-adapter",
        "status": "active",
    }
    report = {
        "created_requirement_ids": [],
        "created_task_ids": ["historical-task"],
        "id": "report-entry-adapter",
        "product_id": "product-entry-adapter",
    }
    finding = {
        "created_at": "2026-07-18T00:00:00+00:00",
        "created_bug_id": None,
        "created_requirement_id": None,
        "created_task_id": "historical-task",
        "description": "不安全的 SQL 拼接。",
        "id": "finding-entry-adapter",
        "recommendation": "使用参数化查询。",
        "severity": "critical",
        "title": "SQL 注入风险",
    }
    created_ids = create_tasks_for_findings(
        current_store,
        findings=[finding],
        report=report,
        severity_threshold="high",
        user={"id": "user_admin"},
    )

    assert created_ids == [finding["created_requirement_id"]]
    assert current_store.ai_tasks == {}
    assert report["created_requirement_ids"] == created_ids
    governance = code_inspection_governance_summary(report, [finding])
    assert governance["requirement_coverage_rate"] == 1
    assert governance["uncovered_requirement_finding_count"] == 0
    assert governance["historical_task_coverage_rate"] == 1
