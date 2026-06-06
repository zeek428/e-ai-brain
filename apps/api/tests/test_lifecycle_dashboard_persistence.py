from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore
from app.core.users import MemoryUserRepository


def test_lifecycle_context_and_dashboard_snapshots_persist_through_fine_grained_repository():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    current_store.products["product_021"] = {
        "code": "LIFE",
        "id": "product_021",
        "name": "生命周期产品",
        "status": "active",
    }
    current_store.lifecycle_context_edges["lifecycle_edge_001"] = {
        "confidence": 1.0,
        "id": "lifecycle_edge_001",
        "metadata": {"status": "completed"},
        "module_code": "core",
        "observed_at": "2026-06-02T10:00:00+00:00",
        "product_id": "product_021",
        "relation_type": "generates_technical_solution",
        "source_module": "ai_task",
        "source_subject_id": "requirement_021",
        "source_subject_type": "requirement",
        "summary": "技术方案",
        "target_subject_id": "task_021",
        "target_subject_type": "ai_task",
        "version_id": "version_021",
    }
    current_store.lifecycle_risk_signals["lifecycle_risk_001"] = {
        "id": "lifecycle_risk_001",
        "impact_summary": "Review 报告提示中风险。",
        "module_code": "core",
        "observed_at": "2026-06-02T10:00:00+00:00",
        "product_id": "product_021",
        "recommendation": "补充边界测试。",
        "requirement_id": "requirement_021",
        "risk_type": "code_review_medium_risk",
        "severity": "medium",
        "source_subject_id": "report_021",
        "source_subject_type": "code_review_report",
        "task_id": "task_021",
        "version_id": "version_021",
    }
    current_store.dashboard_metric_snapshots["dashboard_snapshot_product_021_7d"] = {
        "id": "dashboard_snapshot_product_021_7d",
        "metrics": {"summary": {"ai_tasks": 1, "requirements": 1}},
        "product_id": "product_021",
        "time_range": "7d",
        "window_end": "2026-06-02T10:00:00+00:00",
        "window_start": "2026-05-26T10:00:00+00:00",
    }

    current_store.persist()

    assert repository.lifecycle_context_payload == {
        "lifecycle_context_edges": current_store.lifecycle_context_edges,
        "lifecycle_risk_signals": current_store.lifecycle_risk_signals,
    }
    assert repository.dashboard_payload == {
        "dashboard_metric_snapshots": current_store.dashboard_metric_snapshots,
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    assert rebuilt_store.lifecycle_context_edges == current_store.lifecycle_context_edges
    assert rebuilt_store.lifecycle_risk_signals == current_store.lifecycle_risk_signals
    assert rebuilt_store.dashboard_metric_snapshots == current_store.dashboard_metric_snapshots
    assert rebuilt_store.new_id("lifecycle_edge") == "lifecycle_edge_002"
    assert rebuilt_store.new_id("lifecycle_risk") == "lifecycle_risk_002"
    assert rebuilt_store.new_id("dashboard_snapshot") == "dashboard_snapshot_001"


def test_lifecycle_and_dashboard_handlers_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    now = "2026-06-03T10:00:00+00:00"
    repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {
            "version_lifecycle_dbfirst": {
                "code": "v1",
                "created_at": now,
                "id": "version_lifecycle_dbfirst",
                "name": "v1",
                "product_id": "product_lifecycle_dbfirst",
                "status": "active",
                "updated_at": now,
            }
        },
        "products": {
            "product_lifecycle_dbfirst": {
                "code": "LIFECYCLE-DBFIRST",
                "created_at": now,
                "id": "product_lifecycle_dbfirst",
                "name": "生命周期 DB-first 产品",
                "status": "active",
                "updated_at": now,
            }
        },
        "related_systems": {},
    }
    repository.requirements_payload = {
        "requirements": {
            "requirement_lifecycle_dbfirst": {
                "content": "生命周期查询需要直接写 repository。",
                "created_at": now,
                "created_by": "user_admin",
                "id": "requirement_lifecycle_dbfirst",
                "priority": "P1",
                "product_id": "product_lifecycle_dbfirst",
                "status": "ready_for_dev",
                "task_ids": ["task_lifecycle_dbfirst"],
                "title": "生命周期 DB-first",
                "updated_at": now,
                "version_id": "version_lifecycle_dbfirst",
            }
        }
    }
    repository.ai_tasks_payload = {
        "ai_tasks": {
            "task_lifecycle_dbfirst": {
                "created_at": now,
                "created_by": "user_admin",
                "current_step": "complete_archive",
                "graph_run_ids": [],
                "id": "task_lifecycle_dbfirst",
                "input_json": {},
                "output_json": {"summary": "已完成产品详细设计"},
                "product_context": {},
                "product_id": "product_lifecycle_dbfirst",
                "requirement_id": "requirement_lifecycle_dbfirst",
                "requirement_snapshot": {"id": "requirement_lifecycle_dbfirst"},
                "review_ids": [],
                "status": "completed",
                "task_type": "product_detail_design",
                "title": "产品详细设计",
                "updated_at": now,
                "version_id": "version_lifecycle_dbfirst",
            }
        }
    }

    def use_rebuilt_store_without_request_persist() -> None:
        rebuilt_store = PersistentMemoryStore.from_repository(repository)
        rebuilt_store.persist = lambda: None
        app.state.store = rebuilt_store

    use_rebuilt_store_without_request_persist()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        lifecycle = client.get(
            "/api/lifecycle/context"
            "?subject_type=requirement&subject_id=requirement_lifecycle_dbfirst"
            "&direction=downstream&include_risks=false",
            headers=headers,
        ).json()["data"]
        assert [item["subject_id"] for item in lifecycle["downstream"]] == [
            "task_lifecycle_dbfirst"
        ]
        assert repository.lifecycle_source_row_reads == 1

        use_rebuilt_store_without_request_persist()
        assert app.state.store.lifecycle_context_edges
        edge = next(iter(app.state.store.lifecycle_context_edges.values()))
        assert edge["target_subject_id"] == "task_lifecycle_dbfirst"

        dashboard = client.get(
            "/api/dashboard/it-team?product_id=product_lifecycle_dbfirst&time_range=7d",
            headers=headers,
        ).json()["data"]
        assert dashboard["summary"]["ai_tasks"] == 1

        use_rebuilt_store_without_request_persist()
        assert app.state.store.dashboard_metric_snapshots
        snapshot = next(iter(app.state.store.dashboard_metric_snapshots.values()))
        assert snapshot["product_id"] == "product_lifecycle_dbfirst"
        assert snapshot["metrics"]["summary"]["ai_tasks"] == 1
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_lifecycle_and_dashboard_use_repository_source_rows_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    now = "2026-06-03T12:00:00+00:00"
    repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {
            "version_read_model": {
                "code": "v1",
                "created_at": now,
                "id": "version_read_model",
                "name": "v1",
                "product_id": "product_read_model",
                "status": "active",
                "updated_at": now,
            }
        },
        "products": {
            "product_read_model": {
                "code": "READ-MODEL",
                "created_at": now,
                "id": "product_read_model",
                "name": "读模型产品",
                "status": "active",
                "updated_at": now,
            }
        },
        "related_systems": {},
    }
    repository.requirements_payload = {
        "requirements": {
            "requirement_read_model": {
                "content": "看板和生命周期读取必须优先走 repository 快照。",
                "created_at": now,
                "created_by": "user_admin",
                "id": "requirement_read_model",
                "priority": "P1",
                "product_id": "product_read_model",
                "status": "ready_for_dev",
                "task_ids": ["task_read_model"],
                "title": "读模型迁移",
                "updated_at": now,
                "version_id": "version_read_model",
            }
        }
    }
    repository.ai_tasks_payload = {
        "ai_tasks": {
            "task_read_model": {
                "created_at": now,
                "created_by": "user_admin",
                "current_step": "complete_archive",
                "graph_run_ids": [],
                "id": "task_read_model",
                "input_json": {},
                "output_json": {"summary": "读模型聚合任务"},
                "product_context": {},
                "product_id": "product_read_model",
                "requirement_id": "requirement_read_model",
                "requirement_snapshot": {"id": "requirement_read_model"},
                "review_ids": [],
                "status": "completed",
                "task_type": "product_detail_design",
                "title": "读模型聚合任务",
                "updated_at": now,
                "version_id": "version_read_model",
            }
        }
    }

    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.persist = lambda: None
    stale_store.requirements = {}
    stale_store.ai_tasks = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()
    app.state.dashboard_cache = {}

    try:
        headers = auth_headers()
        dashboard = client.get(
            "/api/dashboard/it-team?product_id=product_read_model",
            headers=headers,
        ).json()["data"]
        assert dashboard["summary"]["requirements"] == 1
        assert dashboard["summary"]["ai_tasks"] == 1
        assert dashboard["metadata"]["dashboard_cache"]["cache_hit"] is False
        assert repository.dashboard_source_row_reads == 1
        assert repository.dashboard_snapshot_direct_writes

        cached_dashboard = client.get(
            "/api/dashboard/it-team?product_id=product_read_model",
            headers=headers,
        ).json()["data"]
        assert cached_dashboard["summary"]["requirements"] == 1
        assert cached_dashboard["metadata"]["dashboard_cache"]["cache_hit"] is True
        assert repository.dashboard_source_row_reads == 1

        refreshed_dashboard = client.get(
            "/api/dashboard/it-team?product_id=product_read_model&refresh=true",
            headers=headers,
        ).json()["data"]
        assert refreshed_dashboard["summary"]["ai_tasks"] == 1
        assert refreshed_dashboard["metadata"]["dashboard_cache"]["cache_hit"] is False
        assert repository.dashboard_source_row_reads == 2

        lifecycle = client.get(
            "/api/lifecycle/context"
            "?subject_type=requirement&subject_id=requirement_read_model"
            "&direction=downstream&include_risks=false",
            headers=headers,
        ).json()["data"]
        assert [item["subject_id"] for item in lifecycle["downstream"]] == [
            "task_read_model"
        ]
        assert repository.lifecycle_source_row_reads == 1
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
