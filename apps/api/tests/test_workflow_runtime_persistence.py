from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

import app.main as main
import app.services.model_gateway as model_gateway_service
from app.core.persistence import PersistentMemoryStore
from app.core.users import MemoryUserRepository
from tests.requirement_fixtures import seed_accepted_assessment_provenance


def test_workflow_runtime_is_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.ai_tasks["task_012"] = {
        "created_by": "user_admin",
        "current_step": "interrupt_for_human_review",
        "graph_run_ids": ["graph_run_004"],
        "id": "task_012",
        "input_json": {},
        "module_code": None,
        "output_json": {"kind": "product_detail_design", "summary": "结构表输出"},
        "product_context": {},
        "product_id": "product_001",
        "requirement_id": "requirement_001",
        "requirement_snapshot": {"id": "requirement_001"},
        "review_ids": ["review_006"],
        "status": "waiting_review",
        "task_type": "product_detail_design",
        "title": "产品详细设计：结构表验证",
        "version_id": "version_001",
    }
    current_store.graph_runs["graph_run_004"] = {
        "ai_task_id": "task_012",
        "checkpoint_id": "checkpoint_005",
        "completed_at": None,
        "current_step": "interrupt_for_human_review",
        "id": "graph_run_004",
        "started_at": "2026-05-31T10:00:00+00:00",
        "state_snapshot": {"review_id": "review_006", "task_status": "waiting_review"},
        "status": "interrupted",
        "task_type": "product_detail_design",
    }
    current_store.graph_checkpoints["checkpoint_005"] = {
        "ai_task_id": "task_012",
        "created_at": "2026-05-31T10:00:01+00:00",
        "current_step": "interrupt_for_human_review",
        "graph_run_id": "graph_run_004",
        "id": "checkpoint_005",
        "state_snapshot": {"review_id": "review_006", "task_status": "waiting_review"},
    }
    current_store.human_reviews["review_006"] = {
        "ai_task_id": "task_012",
        "content": {"kind": "product_detail_design", "summary": "结构表输出"},
        "id": "review_006",
        "stage": "product_detail_design",
        "status": "pending",
        "version": 1,
    }

    current_store.persist()

    assert repository.workflow_runtime_payload is not None
    assert repository.workflow_runtime_payload["graph_runs"]["graph_run_004"]["status"] == (
        "interrupted"
    )
    assert (
        repository.workflow_runtime_payload["graph_checkpoints"]["checkpoint_005"]["graph_run_id"]
        == "graph_run_004"
    )
    assert repository.workflow_runtime_payload["human_reviews"]["review_006"]["status"] == (
        "pending"
    )

    repository.payload = {
        "ai_tasks": {
            "task_012": {
                "created_by": "user_admin",
                "current_step": "draft",
                "graph_run_ids": [],
                "id": "task_012",
                "input_json": {},
                "module_code": None,
                "output_json": None,
                "product_context": {},
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "requirement_snapshot": {"id": "requirement_001"},
                "review_ids": [],
                "status": "draft",
                "task_type": "product_detail_design",
                "title": "产品详细设计：结构表验证",
                "version_id": "version_001",
            }
        },
        "counters": {},
    }
    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.human_reviews["review_006"]["content"]["summary"] == "结构表输出"
    assert rebuilt_store.graph_runs["graph_run_004"]["checkpoint_id"] == "checkpoint_005"
    assert rebuilt_store.graph_checkpoints["checkpoint_005"]["current_step"] == (
        "interrupt_for_human_review"
    )
    assert rebuilt_store.ai_tasks["task_012"]["review_ids"] == ["review_006"]
    assert rebuilt_store.ai_tasks["task_012"]["graph_run_ids"] == ["graph_run_004"]
    assert rebuilt_store.ai_tasks["task_012"]["checkpoint_id"] == "checkpoint_005"
    assert rebuilt_store.new_id("review") == "review_007"
    assert rebuilt_store.new_id("graph_run") == "graph_run_005"
    assert rebuilt_store.new_id("checkpoint") == "checkpoint_006"


def test_empty_workflow_runtime_tables_ignore_snapshot_runtime_data():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "graph_checkpoints": {
            "checkpoint_001": {
                "ai_task_id": "task_001",
                "created_at": "2026-05-31T10:00:01+00:00",
                "current_step": "interrupt_for_human_review",
                "graph_run_id": "graph_run_001",
                "id": "checkpoint_001",
                "state_snapshot": {"review_id": "review_001"},
            }
        },
        "graph_runs": {
            "graph_run_001": {
                "ai_task_id": "task_001",
                "checkpoint_id": "checkpoint_001",
                "completed_at": None,
                "current_step": "interrupt_for_human_review",
                "id": "graph_run_001",
                "started_at": "2026-05-31T10:00:00+00:00",
                "state_snapshot": {"review_id": "review_001"},
                "status": "interrupted",
                "task_type": "product_detail_design",
            }
        },
        "human_reviews": {
            "review_001": {
                "ai_task_id": "task_001",
                "content": {"summary": "快照 Review"},
                "id": "review_001",
                "stage": "product_detail_design",
                "status": "pending",
                "version": 1,
            }
        },
        "counters": {"checkpoint": 1, "graph_run": 1, "review": 1},
    }
    repository.workflow_runtime_payload = {
        "graph_checkpoints": {},
        "graph_runs": {},
        "human_reviews": {},
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert rebuilt_store.human_reviews == {}
    assert rebuilt_store.graph_runs == {}
    assert rebuilt_store.graph_checkpoints == {}


def test_orphan_snapshot_workflow_runtime_is_ignored_after_structured_task_migration():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "graph_checkpoints": {
            "checkpoint_009": {
                "ai_task_id": "task_missing",
                "created_at": "2026-05-31T10:00:01+00:00",
                "current_step": "interrupt_for_human_review",
                "graph_run_id": "graph_run_009",
                "id": "checkpoint_009",
                "state_snapshot": {},
            }
        },
        "graph_runs": {
            "graph_run_009": {
                "ai_task_id": "task_missing",
                "checkpoint_id": "checkpoint_009",
                "completed_at": None,
                "current_step": "interrupt_for_human_review",
                "id": "graph_run_009",
                "started_at": "2026-05-31T10:00:00+00:00",
                "state_snapshot": {},
                "status": "interrupted",
                "task_type": "product_detail_design",
            }
        },
        "human_reviews": {
            "review_009": {
                "ai_task_id": "task_missing",
                "content": {},
                "id": "review_009",
                "stage": "product_detail_design",
                "status": "pending",
                "version": 1,
            }
        },
        "counters": {"checkpoint": 9, "graph_run": 9, "review": 9},
    }
    repository.ai_tasks_payload = {
        "ai_tasks": {
            "task_001": {
                "created_by": "user_admin",
                "current_step": "draft",
                "id": "task_001",
                "input_json": {},
                "module_code": None,
                "output_json": None,
                "product_context": {},
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "requirement_snapshot": {"id": "requirement_001"},
                "status": "draft",
                "task_type": "product_detail_design",
                "title": "结构表任务",
                "version_id": "version_001",
            }
        }
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    rebuilt_store.persist()

    assert rebuilt_store.graph_runs == {}
    assert rebuilt_store.graph_checkpoints == {}
    assert rebuilt_store.human_reviews == {}
    assert repository.workflow_runtime_payload == {
        "graph_checkpoints": {},
        "graph_runs": {},
        "human_reviews": {},
    }
    assert rebuilt_store.new_id("review") == "review_001"


def test_pending_reviews_route_uses_direct_repository_query():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.ai_tasks_payload = {
        "ai_tasks": {
            "task_perf_001": {
                "id": "task_perf_001",
                "brain_app_id": "rd_brain",
                "current_step": "human_review",
                "created_by": "user_admin",
                "product_id": "product_perf",
                "requirement_id": "req_perf",
                "status": "waiting_review",
                "task_type": "product_detail_design",
                "title": "任务管理查询性能优化",
            }
        }
    }
    repository.workflow_runtime_payload = {
        "graph_checkpoints": {},
        "graph_runs": {},
        "human_reviews": {
            "review_perf_001": {
                "ai_task_id": "task_perf_001",
                "content": {"summary": "性能优化确认"},
                "id": "review_perf_001",
                "stage": "human_review",
                "status": "pending",
                "version": 1,
            }
        },
    }
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        pending = client.get("/api/reviews/pending", headers=headers).json()["data"]

        assert [item["id"] for item in pending["items"]] == ["review_perf_001"]
        assert repository.task_workflow_source_row_reads == 0
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_pending_reviews_route_uses_repository_pagination_and_task_filter():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    count_kwargs = {}
    list_kwargs = {}

    def count_pending_review_summaries(**kwargs):
        count_kwargs.update(kwargs)
        return 23

    def list_pending_review_summaries(**kwargs):
        list_kwargs.update(kwargs)
        return [
            {
                "ai_task_id": kwargs.get("ai_task_id"),
                "content": {"summary": "第二页确认项"},
                "created_at": "2026-06-28T01:00:00+00:00",
                "id": "review_page_006",
                "stage": "technical_solution",
                "status": "pending",
                "updated_at": "2026-06-28T02:00:00+00:00",
                "version": 2,
            }
        ]

    repository.count_pending_review_summaries = count_pending_review_summaries
    repository.list_pending_review_summaries = list_pending_review_summaries
    app.state.store = PersistentMemoryStore.from_repository(repository)
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        response = client.get(
            "/api/reviews/pending"
            "?ai_task_id=task_perf_001"
            "&page=2"
            "&page_size=5"
            "&sort_by=updated_at"
            "&sort_order=asc",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()["data"]

        assert payload["items"][0]["id"] == "review_page_006"
        assert payload["page"] == 2
        assert payload["page_size"] == 5
        assert payload["total"] == 23
        assert payload["query"]["name"] == "pending_reviews"
        assert payload["query"]["filters"] == {"ai_task_id": "task_perf_001"}
        assert payload["performance"]["total"] == 23
        assert count_kwargs == {
            "ai_task_id": "task_perf_001",
            "product_scope_ids": None,
            "read_scope": "all",
        }
        assert list_kwargs == {
            "ai_task_id": "task_perf_001",
            "limit": 5,
            "offset": 5,
            "product_scope_ids": None,
            "read_scope": "all",
            "sort_by": "updated_at",
            "sort_order": "asc",
        }
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def _create_generated_design_task(
    headers: dict[str, str],
    *,
    product_code: str,
    product_name: str,
    requirement_title: str,
) -> dict:
    product = client.post(
        "/api/products",
        json={"code": product_code, "name": product_name},
        headers=headers,
    ).json()["data"]
    version = client.post(
        f"/api/products/{product['id']}/versions",
        json={"code": "v1", "name": "v1", "status": "active"},
        headers=headers,
    ).json()["data"]
    requirement = client.post(
        "/api/requirements",
        json={
            "content": f"{requirement_title} 必须在失败时直接写 repository。",
            "product_id": product["id"],
            "title": requirement_title,
            "version_id": version["id"],
        },
        headers=headers,
    ).json()["data"]
    seed_accepted_assessment_provenance(app.state.store, requirement)
    client.post(
        f"/api/requirements/{requirement['id']}/approve",
        json={"comment": "进入设计"},
        headers=headers,
    )
    return client.post(
        f"/api/requirements/{requirement['id']}/generate-task",
        headers=headers,
    ).json()["data"]


def test_start_task_config_failure_writes_failed_state_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    monkeypatch.setattr(main.settings, "model_gateway_base_url", "")
    monkeypatch.setattr(main.settings, "model_gateway_api_key", "")
    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        generated = _create_generated_design_task(
            headers,
            product_code="CONFIG-FAIL-DBFIRST",
            product_name="配置失败 DB-first 产品",
            requirement_title="模型配置失败 DB-first",
        )
        draft_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        response = client.post(f"/api/ai-tasks/{generated['task_id']}/start", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "MODEL_GATEWAY_CONFIG_INVALID"

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        assert detail["status"] == "failed"
        assert detail["current_step"] == "model_gateway_config_invalid"
        assert detail["updated_at"] != draft_detail["updated_at"]
        assert f"task:{generated['task_id']}:failed" in repository.task_state_direct_writes
        assert any(
            event["event_type"] == "ai_task.failed"
            for event in repository.audit_events_payload["audit_events"]
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_start_task_call_failure_and_retry_write_failed_logs_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    def fail_urlopen(_request, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(model_gateway_service, "urlopen", fail_urlopen)
    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        generated = _create_generated_design_task(
            headers,
            product_code="CALL-FAIL-DBFIRST",
            product_name="调用失败 DB-first 产品",
            requirement_title="模型调用失败 DB-first",
        )

        first_failed = client.post(f"/api/ai-tasks/{generated['task_id']}/start", headers=headers)
        assert first_failed.status_code == 502
        assert first_failed.json()["detail"]["code"] == "MODEL_GATEWAY_FAILED"

        use_rebuilt_store_without_request_persist()
        retry_failed = client.post(f"/api/ai-tasks/{generated['task_id']}/start", headers=headers)
        assert retry_failed.status_code == 502
        assert retry_failed.json()["detail"]["code"] == "MODEL_GATEWAY_FAILED"

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        logs = client.get(
            f"/api/model-gateway/logs?ai_task_id={generated['task_id']}",
            headers=headers,
        ).json()["data"]["items"]
        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        assert detail["status"] == "failed"
        assert detail["current_step"] == "model_gateway_failed"
        assert len(logs) == 2
        assert all(log["status"] == "failed" for log in logs)
        assert all(log["error"] == "Model gateway request failed" for log in logs)
        assert event_types.count("model_gateway.called") == 2
        assert "ai_task.retry_started" in event_types
        assert repository.task_state_direct_writes.count(f"task:{generated['task_id']}:failed") == 2
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_approve_review_writes_completion_records_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "APPROVE-DBFIRST", "name": "审批 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "审批 Review 后所有完成态记录必须直接写 repository。",
                "product_id": product["id"],
                "title": "Review 审批 DB-first",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        seed_accepted_assessment_provenance(app.state.store, requirement)
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入设计"},
            headers=headers,
        )
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        use_rebuilt_store_without_request_persist()
        waiting_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        approved = client.post(
            f"/api/reviews/{started['review_id']}/approve",
            json={"version": 1},
            headers=headers,
        ).json()["data"]
        assert approved["task_status"] == "completed"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        requirement_detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={generated['task_id']}",
            headers=headers,
        ).json()["data"]["items"]

        assert detail["status"] == "completed"
        assert detail["pending_review"] is None
        assert detail["reviews"]["items"][0]["status"] == "approved"
        assert detail["reviews"]["items"][0]["decided_at"]
        assert detail["current_step"] == "complete_archive"
        assert detail["updated_at"] != waiting_detail["updated_at"]
        assert detail["knowledge_deposits"]["items"][0]["status"] == "pending"
        assert requirement_detail["status"] == "ready_for_dev"
        assert graph_runs[0]["status"] == "completed"
        assert graph_runs[0]["current_step"] == "complete_archive"
        assert (
            f"review:{generated['task_id']}:{started['review_id']}:completed"
            in repository.workflow_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_edit_approve_review_writes_completion_records_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "EDIT-APPROVE-DBFIRST", "name": "编辑审批 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]
        requirement = client.post(
            "/api/requirements",
            json={
                "content": "编辑审批 Review 后完成态记录也必须直接写 repository。",
                "product_id": product["id"],
                "title": "Review 编辑审批 DB-first",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]
        seed_accepted_assessment_provenance(app.state.store, requirement)
        client.post(
            f"/api/requirements/{requirement['id']}/approve",
            json={"comment": "进入设计"},
            headers=headers,
        )
        generated = client.post(
            f"/api/requirements/{requirement['id']}/generate-task",
            headers=headers,
        ).json()["data"]
        started = client.post(
            f"/api/ai-tasks/{generated['task_id']}/start",
            headers=headers,
        ).json()["data"]
        use_rebuilt_store_without_request_persist()
        waiting_detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]

        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        edited = client.post(
            f"/api/reviews/{started['review_id']}/edit-approve",
            json={
                "version": 1,
                "edited_content": {
                    "summary": "人工编辑后的方案摘要",
                    "acceptance_criteria": ["保存 edited_approved 决策"],
                },
            },
            headers=headers,
        ).json()["data"]
        assert edited["task_status"] == "completed"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        detail = client.get(
            f"/api/ai-tasks/{generated['task_id']}",
            headers=headers,
        ).json()["data"]
        requirement_detail = client.get(
            f"/api/requirements/{requirement['id']}",
            headers=headers,
        ).json()["data"]
        graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={generated['task_id']}",
            headers=headers,
        ).json()["data"]["items"]

        assert detail["status"] == "completed"
        assert detail["pending_review"] is None
        assert detail["output"]["summary"] == "人工编辑后的方案摘要"
        assert detail["reviews"]["items"][0]["status"] == "edited_approved"
        assert detail["reviews"]["items"][0]["edited_content"]["summary"] == "人工编辑后的方案摘要"
        assert detail["reviews"]["items"][0]["decided_at"]
        assert detail["current_step"] == "complete_archive"
        assert detail["updated_at"] != waiting_detail["updated_at"]
        assert detail["knowledge_deposits"]["items"][0]["content"] == "人工编辑后的方案摘要"
        assert requirement_detail["status"] == "ready_for_dev"
        assert graph_runs[0]["status"] == "completed"
        assert graph_runs[0]["current_step"] == "complete_archive"
        assert (
            f"review:{generated['task_id']}:{started['review_id']}:completed"
            in repository.workflow_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_reject_and_more_info_reviews_write_decisions_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "REVIEW-BRANCH-DBFIRST", "name": "Review 分支 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]

        def create_started_task(title: str) -> tuple[dict, dict]:
            requirement = client.post(
                "/api/requirements",
                json={
                    "content": f"{title} 的 Review 分支必须直接写 repository。",
                    "product_id": product["id"],
                    "title": title,
                    "version_id": version["id"],
                },
                headers=headers,
            ).json()["data"]
            seed_accepted_assessment_provenance(app.state.store, requirement)
            client.post(
                f"/api/requirements/{requirement['id']}/approve",
                json={"comment": "进入设计"},
                headers=headers,
            )
            generated = client.post(
                f"/api/requirements/{requirement['id']}/generate-task",
                headers=headers,
            ).json()["data"]
            started = client.post(
                f"/api/ai-tasks/{generated['task_id']}/start",
                headers=headers,
            ).json()["data"]
            use_rebuilt_store_without_request_persist()
            waiting_detail = client.get(
                f"/api/ai-tasks/{generated['task_id']}",
                headers=headers,
            ).json()["data"]
            return started, waiting_detail

        rejected_start, rejected_waiting_detail = create_started_task("Review reject DB-first")
        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        rejected = client.post(
            f"/api/reviews/{rejected_start['review_id']}/reject",
            json={"version": 1, "decision_reason": "方案风险过高"},
            headers=headers,
        ).json()["data"]
        assert rejected["task_status"] == "failed"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        rejected_detail = client.get(
            f"/api/ai-tasks/{rejected_start['id']}",
            headers=headers,
        ).json()["data"]
        rejected_graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={rejected_start['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert rejected_detail["status"] == "failed"
        assert rejected_detail["pending_review"] is None
        assert rejected_detail["reviews"]["items"][0]["status"] == "rejected"
        assert rejected_detail["reviews"]["items"][0]["decision_reason"] == "方案风险过高"
        assert rejected_detail["reviews"]["items"][0]["decided_at"]
        assert rejected_detail["updated_at"] != rejected_waiting_detail["updated_at"]
        assert rejected_graph_runs[0]["status"] == "failed"
        assert rejected_graph_runs[0]["current_step"] == "failed"

        more_info_start, more_info_waiting_detail = create_started_task("Review more-info DB-first")
        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        more_info = client.post(
            f"/api/reviews/{more_info_start['review_id']}/request-more-info",
            json={"version": 1, "questions": ["请补充边界条件和验收口径"]},
            headers=headers,
        ).json()["data"]
        assert more_info["task_status"] == "waiting_more_info"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        more_info_detail = client.get(
            f"/api/ai-tasks/{more_info_start['id']}",
            headers=headers,
        ).json()["data"]
        more_info_graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={more_info_start['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert more_info_detail["status"] == "waiting_more_info"
        assert more_info_detail["pending_review"] is None
        assert more_info_detail["reviews"]["items"][0]["status"] == "requested_more_info"
        assert more_info_detail["reviews"]["items"][0]["questions"] == ["请补充边界条件和验收口径"]
        assert more_info_detail["reviews"]["items"][0]["decided_at"]
        assert more_info_detail["updated_at"] != more_info_waiting_detail["updated_at"]
        assert more_info_graph_runs[0]["status"] == "interrupted"
        assert more_info_graph_runs[0]["current_step"] == "wait_for_more_info"
        assert (
            f"review:{rejected_start['id']}:{rejected_start['review_id']}:failed"
            in repository.workflow_direct_writes
        )
        assert (
            f"review:{more_info_start['id']}:{more_info_start['review_id']}:waiting_more_info"
            in repository.workflow_direct_writes
        )
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_cancel_and_submit_more_info_write_task_state_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "TASK-STATE-DBFIRST", "name": "任务状态 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1", "status": "active"},
            headers=headers,
        ).json()["data"]

        def create_started_task(title: str) -> dict:
            requirement = client.post(
                "/api/requirements",
                json={
                    "content": f"{title} 的任务状态必须直接写 repository。",
                    "product_id": product["id"],
                    "title": title,
                    "version_id": version["id"],
                },
                headers=headers,
            ).json()["data"]
            seed_accepted_assessment_provenance(app.state.store, requirement)
            client.post(
                f"/api/requirements/{requirement['id']}/approve",
                json={"comment": "进入设计"},
                headers=headers,
            )
            generated = client.post(
                f"/api/requirements/{requirement['id']}/generate-task",
                headers=headers,
            ).json()["data"]
            started = client.post(
                f"/api/ai-tasks/{generated['task_id']}/start",
                headers=headers,
            ).json()["data"]
            use_rebuilt_store_without_request_persist()
            return started

        cancelled_start = create_started_task("Cancel DB-first")
        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        cancelled = client.post(
            f"/api/ai-tasks/{cancelled_start['id']}/cancel",
            headers=headers,
        ).json()["data"]
        assert cancelled["status"] == "cancelled"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        cancelled_detail = client.get(
            f"/api/ai-tasks/{cancelled_start['id']}",
            headers=headers,
        ).json()["data"]
        cancelled_graph_runs = client.get(
            f"/api/graph-runs?ai_task_id={cancelled_start['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert cancelled_detail["status"] == "cancelled"
        assert cancelled_detail["pending_review"] is None
        assert cancelled_detail["reviews"]["items"][0]["status"] == "cancelled"
        assert cancelled_detail["reviews"]["items"][0]["decided_at"]
        assert cancelled_graph_runs[0]["status"] == "cancelled"
        assert cancelled_graph_runs[0]["current_step"] == "cancelled"

        more_info_start = create_started_task("Submit more-info DB-first")
        client.post(
            f"/api/reviews/{more_info_start['review_id']}/request-more-info",
            json={"version": 1, "questions": ["请补充验收边界"]},
            headers=headers,
        )
        use_rebuilt_store_without_request_persist()
        app.state.store.ai_tasks = {}
        app.state.store.graph_runs = {}
        app.state.store.graph_checkpoints = {}
        app.state.store.human_reviews = {}
        repository.task_workflow_source_row_reads = 0
        more_info = client.post(
            f"/api/ai-tasks/{more_info_start['id']}/more-info",
            json={"answers": [{"question": "请补充验收边界", "answer": "补充 P0 验收边界"}]},
            headers=headers,
        ).json()["data"]
        assert more_info["status"] == "draft"
        assert repository.task_workflow_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        more_info_detail = client.get(
            f"/api/ai-tasks/{more_info_start['id']}",
            headers=headers,
        ).json()["data"]
        assert more_info_detail["status"] == "draft"
        assert more_info_detail["current_step"] == "draft"
        assert more_info_detail["input"]["more_info_answers"] == [
            {"question": "请补充验收边界", "answer": "补充 P0 验收边界"}
        ]
        assert f"task:{cancelled_start['id']}:cancelled" in repository.task_state_direct_writes
        assert f"task:{more_info_start['id']}:draft" in repository.task_state_direct_writes
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
