from fastapi.testclient import TestClient

from app.core.store import MemoryStore
from app.main import app

client = TestClient(app)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin@example.com", "password": "admin123"},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_draft_task(
    headers: dict[str, str],
    *,
    product_code: str = "rd-platform",
    reset_store: bool = True,
) -> dict[str, str]:
    if reset_store:
        app.state.store.reset()
    product = client.post(
        "/api/products",
        json={"code": product_code, "name": "研发大脑平台"},
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
            "title": "API 契约补齐",
            "product_id": product["id"],
            "version_id": version["id"],
            "content": "补齐文档声明的基础查询和取消接口。",
        },
        headers=headers,
    ).json()["data"]
    client.post(f"/api/requirements/{requirement['id']}/approve", json={}, headers=headers)
    generated = client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]
    return {
        "product_id": product["id"],
        "requirement_id": requirement["id"],
        "task_id": generated["task_id"],
    }


def test_brain_apps_and_task_list_contracts_are_available():
    headers = auth_headers()
    context = create_draft_task(headers)

    brain_apps = client.get("/api/brain-apps", headers=headers).json()["data"]
    assert brain_apps["items"][0]["code"] == "rd_brain"
    assert brain_apps["items"][0]["status"] == "active"

    tasks = client.get(
        "/api/ai-tasks?status=draft&task_type=product_detail_design",
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in tasks["items"]] == [context["task_id"]]


def test_ai_task_list_supports_product_and_created_time_filters():
    headers = auth_headers()
    context = create_draft_task(headers)

    tasks = client.get(
        (
            f"/api/ai-tasks?product_id={context['product_id']}"
            "&created_from=2000-01-01T00:00:00Z"
            "&created_to=2999-12-31T23:59:59Z"
        ),
        headers=headers,
    ).json()["data"]
    assert [item["id"] for item in tasks["items"]] == [context["task_id"]]
    assert tasks["items"][0]["product_name"] == "研发大脑平台"
    assert tasks["items"][0]["created_at"]

    outside_range = client.get(
        f"/api/ai-tasks?product_id={context['product_id']}&created_to=2000-01-01T00:00:00Z",
        headers=headers,
    ).json()["data"]
    assert outside_range["items"] == []


def test_ai_task_list_supports_server_side_pagination():
    headers = auth_headers()
    first_context = create_draft_task(headers, product_code="rd-platform-page-1")
    second_context = create_draft_task(
        headers,
        product_code="rd-platform-page-2",
        reset_store=False,
    )

    first_page = client.get(
        "/api/ai-tasks?page=1&page_size=1&sort_by=id&sort_order=asc",
        headers=headers,
    ).json()["data"]
    second_page = client.get(
        "/api/ai-tasks?page=2&page_size=1&sort_by=id&sort_order=asc",
        headers=headers,
    ).json()["data"]

    assert first_page["total"] == 2
    assert first_page["page"] == 1
    assert first_page["page_size"] == 1
    assert [item["id"] for item in first_page["items"]] == [first_context["task_id"]]
    assert [item["id"] for item in second_page["items"]] == [second_context["task_id"]]

    keyword_result = client.get(
        f"/api/ai-tasks?keyword={second_context['task_id']}",
        headers=headers,
    ).json()["data"]
    owner_result = client.get(
        "/api/ai-tasks?created_by=user_admin",
        headers=headers,
    ).json()["data"]

    assert [item["id"] for item in keyword_result["items"]] == [second_context["task_id"]]
    assert owner_result["total"] == 2


def test_ai_task_list_supports_server_side_sorting():
    headers = auth_headers()
    first_context = create_draft_task(headers, product_code="rd-platform-sort-1")
    second_context = create_draft_task(
        headers,
        product_code="rd-platform-sort-2",
        reset_store=False,
    )

    sorted_by_id = client.get(
        "/api/ai-tasks?page=1&page_size=1&sort_by=id&sort_order=desc",
        headers=headers,
    ).json()["data"]
    invalid_sort = client.get(
        "/api/ai-tasks?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )

    assert sorted_by_id["page"] == 1
    assert sorted_by_id["page_size"] == 1
    assert sorted_by_id["total"] == 2
    assert [item["id"] for item in sorted_by_id["items"]] == [second_context["task_id"]]
    assert first_context["task_id"] != second_context["task_id"]
    assert invalid_sort.status_code == 400
    assert invalid_sort.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_brain_app_contract_reads_runtime_configuration():
    headers = auth_headers()
    original_store = app.state.store
    configured_store = MemoryStore()
    configured_store.brain_apps = {
        "ops_brain": {
            "id": "ops_brain",
            "code": "ops_brain",
            "name": "运营大脑",
            "status": "active",
            "description": "运行时配置读取验证。",
            "config": {"default_task_types": ["post_release_analysis"]},
        }
    }
    app.state.store = configured_store
    try:
        brain_apps = client.get("/api/brain-apps", headers=headers).json()["data"]
        assert [item["code"] for item in brain_apps["items"]] == ["ops_brain"]

        detail = client.get("/api/brain-apps/ops_brain", headers=headers).json()["data"]
        assert detail["name"] == "运营大脑"

        missing = client.get("/api/brain-apps/rd_brain", headers=headers)
        assert missing.status_code == 404
    finally:
        app.state.store = original_store


def test_review_detail_cancel_task_and_knowledge_document_list_contracts():
    headers = auth_headers()
    context = create_draft_task(headers)
    cancelled = client.post(
        f"/api/ai-tasks/{context['task_id']}/cancel",
        headers=headers,
    ).json()["data"]
    assert cancelled["status"] == "cancelled"

    second_context = create_draft_task(
        headers,
        product_code="rd-platform-batch-cancel-2",
        reset_store=False,
    )
    started = client.post(
        f"/api/ai-tasks/{second_context['task_id']}/start",
        headers=headers,
    ).json()["data"]
    review = client.get(
        f"/api/reviews/{started['review_id']}",
        headers=headers,
    ).json()["data"]
    assert review["id"] == started["review_id"]
    assert review["version"] == 1

    document = client.post(
        "/api/knowledge/documents",
        json={"title": "API 契约文档", "content": "contract search source"},
        headers=headers,
    ).json()["data"]
    documents = client.get("/api/knowledge/documents", headers=headers).json()["data"]
    assert [item["id"] for item in documents["items"]] == [document["id"]]


def test_ai_task_batch_cancel_updates_valid_tasks_and_skips_terminal_tasks():
    headers = auth_headers()
    first_context = create_draft_task(headers)
    second_context = create_draft_task(
        headers,
        product_code="rd-platform-batch-cancel-2",
        reset_store=False,
    )
    started = client.post(
        f"/api/ai-tasks/{second_context['task_id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )

    result = client.post(
        "/api/ai-tasks/batch-cancel",
        json={
            "reason": "批量取消过期任务",
            "task_ids": [
                first_context["task_id"],
                second_context["task_id"],
                first_context["task_id"],
                "task_missing",
            ],
        },
        headers=headers,
    ).json()["data"]

    assert result["updated_count"] == 1
    assert result["skipped_count"] == 3
    assert result["updated"] == [{"id": first_context["task_id"], "status": "cancelled"}]
    assert result["skipped"] == [
        {
            "code": "TASK_STATE_INVALID",
            "id": second_context["task_id"],
            "message": "Task cannot be cancelled from current status",
        },
        {
            "code": "DUPLICATE_TASK",
            "id": first_context["task_id"],
            "message": "Task was already included in this batch",
        },
        {
            "code": "NOT_FOUND",
            "id": "task_missing",
            "message": "AI task not found",
        },
    ]
    assert client.get(
        f"/api/ai-tasks/{first_context['task_id']}",
        headers=headers,
    ).json()["data"]["status"] == "cancelled"
    assert client.get(
        f"/api/ai-tasks/{second_context['task_id']}",
        headers=headers,
    ).json()["data"]["status"] == "completed"


def test_ai_task_batch_retry_restarts_retryable_failed_tasks_and_skips_invalid_items():
    headers = auth_headers()
    retry_context = create_draft_task(headers)
    terminal_context = create_draft_task(
        headers,
        product_code="rd-platform-batch-retry-2",
        reset_store=False,
    )
    started = client.post(
        f"/api/ai-tasks/{terminal_context['task_id']}/start",
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/reviews/{started['review_id']}/approve",
        json={"version": 1},
        headers=headers,
    )
    retry_task = app.state.store.ai_tasks[retry_context["task_id"]]
    retry_task["status"] = "failed"
    retry_task["current_step"] = "model_gateway_failed"

    result = client.post(
        "/api/ai-tasks/batch-retry",
        json={
            "reason": "批量重试模型网关失败任务",
            "task_ids": [
                retry_context["task_id"],
                terminal_context["task_id"],
                retry_context["task_id"],
                "task_missing",
            ],
        },
        headers=headers,
    ).json()["data"]

    assert result["retried_count"] == 1
    assert result["updated_count"] == 1
    assert result["skipped_count"] == 3
    assert result["updated"][0]["id"] == retry_context["task_id"]
    assert result["updated"][0]["status"] == "waiting_review"
    assert result["updated"][0]["review_id"].startswith("review_")
    assert result["skipped"] == [
        {
            "code": "TASK_STATE_INVALID",
            "id": terminal_context["task_id"],
            "message": "Task cannot be retried from current status",
        },
        {
            "code": "DUPLICATE_TASK",
            "id": retry_context["task_id"],
            "message": "Task was already included in this batch",
        },
        {
            "code": "NOT_FOUND",
            "id": "task_missing",
            "message": "AI task not found",
        },
    ]
    retry_detail = client.get(
        f"/api/ai-tasks/{retry_context['task_id']}",
        headers=headers,
    ).json()["data"]
    assert retry_detail["status"] == "waiting_review"
    audit_events = client.get(
        f"/api/audit/events?ai_task_id={retry_context['task_id']}",
        headers=headers,
    ).json()["data"]["items"]
    assert "ai_task.retry_started" in [event["event_type"] for event in audit_events]


def test_knowledge_document_list_supports_server_pagination_sort_and_filters():
    headers = auth_headers()
    create_draft_task(headers)
    first = client.post(
        "/api/knowledge/documents",
        json={
            "content": "contract api source",
            "doc_type": "manual",
            "permission_roles": ["admin"],
            "title": "列表知识 A",
        },
        headers=headers,
    ).json()["data"]
    second = client.post(
        "/api/knowledge/documents",
        json={
            "content": "searchable marker source",
            "doc_type": "Spec",
            "permission_roles": ["admin", "knowledge_owner"],
            "title": "列表知识 B",
        },
        headers=headers,
    ).json()["data"]

    filtered = client.get(
        "/api/knowledge/documents?keyword=marker&doc_type=Spec&permission_role=knowledge_owner"
        "&page=1&page_size=1&sort_by=title&sort_order=desc",
        headers=headers,
    ).json()["data"]
    invalid_sort = client.get(
        "/api/knowledge/documents?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )

    assert filtered["page"] == 1
    assert filtered["page_size"] == 1
    assert filtered["total"] == 1
    assert [item["id"] for item in filtered["items"]] == [second["id"]]
    assert first["id"] not in [item["id"] for item in filtered["items"]]
    assert invalid_sort.status_code == 400
    assert invalid_sort.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_audit_event_list_supports_server_pagination_sort_and_filters():
    headers = auth_headers()
    context = create_draft_task(headers)

    filtered = client.get(
        (
            "/api/audit/events?subject=ai_task"
            f"&actor=user_admin&ai_task_id={context['task_id']}"
            "&result=success&page=1&page_size=1&sort_by=event_type&sort_order=asc"
        ),
        headers=headers,
    ).json()["data"]
    invalid_sort = client.get(
        "/api/audit/events?page=1&page_size=10&sort_by=unsupported",
        headers=headers,
    )

    assert filtered["page"] == 1
    assert filtered["page_size"] == 1
    assert filtered["total"] >= 1
    assert filtered["items"][0]["actor_id"] == "user_admin"
    assert filtered["items"][0]["ai_task_id"] == context["task_id"]
    assert filtered["items"][0]["result"] == "success"
    assert invalid_sort.status_code == 400
    assert invalid_sort.json()["detail"]["code"] == "VALIDATION_ERROR"
