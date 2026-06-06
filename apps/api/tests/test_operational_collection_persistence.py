from test_database_persistence import FakeSnapshotRepository, app, auth_headers, client

from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.users import MemoryUserRepository


def test_operational_lists_use_repository_when_runtime_store_is_stale():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()
    repository.collector_runs_payload = {
        "collector_runs": {
            "collector_run_repo_001": {
                "collector_type": "gitlab_daily_code_metric",
                "created_at": "2026-06-03T08:00:00+00:00",
                "created_by": "user_admin",
                "error_message": None,
                "finished_at": "2026-06-03T08:10:00+00:00",
                "id": "collector_run_repo_001",
                "payload_summary": {"repository_path": "rd/api"},
                "product_id": "product_ops_repo",
                "records_imported": 5,
                "source_system": "gitlab",
                "started_at": "2026-06-03T08:00:00+00:00",
                "status": "succeeded",
                "updated_at": "2026-06-03T08:10:00+00:00",
            },
            "collector_run_repo_002": {
                "collector_type": "jenkins_release",
                "created_at": "2026-06-03T09:00:00+00:00",
                "created_by": "user_admin",
                "error_message": None,
                "finished_at": None,
                "id": "collector_run_repo_002",
                "payload_summary": {},
                "product_id": "product_other",
                "records_imported": 0,
                "source_system": "jenkins",
                "started_at": "2026-06-03T09:00:00+00:00",
                "status": "running",
                "updated_at": "2026-06-03T09:00:00+00:00",
            },
        }
    }
    repository.pending_attribution_payload = {
        "pending_attribution_items": {
            "pending_attr_repo_001": {
                "collector_run_id": "collector_run_repo_001",
                "confidence": 0.91,
                "created_at": "2026-06-03T08:12:00+00:00",
                "created_by": "user_admin",
                "id": "pending_attr_repo_001",
                "raw_payload": {"repository_path": "rd/api"},
                "raw_subject_id": "metric-1",
                "resolution_action": "link_existing_context",
                "resolution_note": "归属产品",
                "resolved_at": "2026-06-03T08:15:00+00:00",
                "resolved_by": "user_admin",
                "resolved_module_code": None,
                "resolved_product_id": "product_ops_repo",
                "resolved_requirement_id": None,
                "resolved_subject_id": None,
                "resolved_subject_type": None,
                "source_system": "gitlab",
                "source_type": "gitlab_daily_code_metric",
                "status": "resolved",
                "suggested_module_code": None,
                "suggested_product_id": None,
                "summary": "GitLab 指标待归属",
                "updated_at": "2026-06-03T08:15:00+00:00",
            },
            "pending_attr_repo_002": {
                "collector_run_id": None,
                "confidence": 0.4,
                "created_at": "2026-06-03T08:20:00+00:00",
                "created_by": "user_admin",
                "id": "pending_attr_repo_002",
                "raw_payload": {},
                "raw_subject_id": "metric-2",
                "resolution_action": None,
                "resolution_note": None,
                "resolved_at": None,
                "resolved_by": None,
                "resolved_module_code": None,
                "resolved_product_id": None,
                "resolved_requirement_id": None,
                "resolved_subject_id": None,
                "resolved_subject_type": None,
                "source_system": "gitlab",
                "source_type": "user_feedback",
                "status": "pending",
                "suggested_module_code": None,
                "suggested_product_id": None,
                "summary": "其他待归属",
                "updated_at": "2026-06-03T08:20:00+00:00",
            },
        }
    }
    repository.gitlab_daily_code_metrics_payload = {
        "gitlab_daily_code_metrics": {
            "gitlab_metric_repo_001": {
                "active_author_count": 3,
                "additions": 120,
                "author_metrics": [{"author": "alice", "commit_count": 2}],
                "changed_files": 8,
                "collected_at": "2026-06-03T08:30:00+00:00",
                "commit_count": 6,
                "created_at": "2026-06-03T08:30:00+00:00",
                "created_by": "user_admin",
                "deletions": 30,
                "id": "gitlab_metric_repo_001",
                "merge_request_count": 2,
                "metric_date": "2026-06-03",
                "product_id": "product_ops_repo",
                "repository_id": "repo_ops_repo",
                "risk_count": 1,
                "source_channel": "manual_import",
                "status": "collected",
                "updated_at": "2026-06-03T08:30:00+00:00",
            }
        }
    }
    repository.jenkins_release_records_payload = {
        "jenkins_release_records": {
            "jenkins_release_repo_001": {
                "build_id": "build-001",
                "created_at": "2026-06-03T08:40:00+00:00",
                "created_by": "user_admin",
                "deployed_at": "2026-06-03T08:50:00+00:00",
                "environment": "staging",
                "id": "jenkins_release_repo_001",
                "job_name": "deploy-api",
                "product_id": "product_ops_repo",
                "status": "success",
                "updated_at": "2026-06-03T08:50:00+00:00",
                "version_id": "version_ops_repo",
            }
        }
    }
    repository.online_log_metrics_payload = {
        "online_log_metrics": {
            "online_log_metric_repo_001": {
                "core_event_count": 80,
                "created_at": "2026-06-03T09:00:00+00:00",
                "created_by": "user_admin",
                "environment": "prod",
                "error_count": 2,
                "error_rate": 0.02,
                "id": "online_log_metric_repo_001",
                "module_code": "assistant",
                "product_id": "product_ops_repo",
                "request_count": 100,
                "status": "normal",
                "top_errors": [{"code": "E_TIMEOUT", "count": 2}],
                "updated_at": "2026-06-03T09:00:00+00:00",
                "window_end": "2026-06-03T09:00:00+00:00",
                "window_start": "2026-06-03T08:00:00+00:00",
            }
        }
    }
    stale_store = PersistentMemoryStore.from_repository(repository)
    stale_store.collector_runs = {}
    stale_store.pending_attribution_items = {}
    stale_store.gitlab_daily_code_metrics = {}
    stale_store.jenkins_release_records = {}
    stale_store.online_log_metrics = {}
    app.state.store = stale_store
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        collectors = client.get(
            "/api/collectors/runs?collector_type=gitlab_daily_code_metric"
            "&product_id=product_ops_repo&status=succeeded&source_system=gitlab",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in collectors] == ["collector_run_repo_001"]

        pending = client.get(
            "/api/attribution/pending-items?source_type=gitlab_daily_code_metric"
            "&status=resolved&resolved_product_id=product_ops_repo"
            "&collector_run_id=collector_run_repo_001",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in pending] == ["pending_attr_repo_001"]

        gitlab_metrics = client.get(
            "/api/devops/gitlab/daily-code-metrics?product_id=product_ops_repo"
            "&repository_id=repo_ops_repo&date=2026-06-03",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in gitlab_metrics] == ["gitlab_metric_repo_001"]
        assert gitlab_metrics[0]["author_metrics"] == [
            {"author": "alice", "commit_count": 2}
        ]

        releases = client.get(
            "/api/devops/jenkins/releases?product_id=product_ops_repo"
            "&version_id=version_ops_repo&status=success&environment=staging",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in releases] == ["jenkins_release_repo_001"]

        online_logs = client.get(
            "/api/ops/online-log-metrics?product_id=product_ops_repo"
            "&module_code=assistant&environment=prod"
            "&from=2026-06-03T08:00:00Z&to=2026-06-03T09:00:00Z",
            headers=headers,
        ).json()["data"]["items"]
        assert [item["id"] for item in online_logs] == ["online_log_metric_repo_001"]
        assert online_logs[0]["top_errors"] == [{"code": "E_TIMEOUT", "count": 2}]
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_operational_routes_write_repository_without_request_persist():
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    try:
        headers = auth_headers()
        product = client.post(
            "/api/products",
            json={"code": "OPS-DBFIRST", "name": "运营 DB-first 产品"},
            headers=headers,
        ).json()["data"]
        version = client.post(
            f"/api/products/{product['id']}/versions",
            json={"code": "v1", "name": "v1"},
            headers=headers,
        ).json()["data"]
        module = client.post(
            f"/api/products/{product['id']}/modules",
            json={"code": "checkout", "name": "结算模块"},
            headers=headers,
        ).json()["data"]
        repository_record = client.post(
            f"/api/products/{product['id']}/git-repositories",
            json={
                "default_branch": "main",
                "git_provider": "gitlab",
                "name": "运营仓库",
                "project_path": "rd/ops-dbfirst",
                "remote_url": "https://gitlab.internal/rd/ops-dbfirst.git",
                "repo_type": "code",
                "root_path": "/",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        collector = client.post(
            "/api/collectors/runs",
            json={
                "collector_type": "gitlab_daily_code_metric",
                "payload_summary": {"repository_path": "rd/ops-dbfirst"},
                "product_id": product["id"],
                "source_system": "gitlab",
                "status": "running",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        patched_collector = client.patch(
            f"/api/collectors/runs/{collector['id']}",
            json={"records_imported": 6, "status": "succeeded"},
            headers=headers,
        ).json()["data"]
        assert patched_collector["status"] == "succeeded"

        use_empty_postgres_runtime_store()
        collector_list = client.get(
            f"/api/collectors/runs?product_id={product['id']}&status=succeeded",
            headers=headers,
        ).json()["data"]["items"]
        assert collector_list[0]["records_imported"] == 6

        pending = client.post(
            "/api/attribution/pending-items",
            json={
                "collector_run_id": collector["id"],
                "confidence": 0.62,
                "raw_payload": {"repository_path": "unknown/repo"},
                "raw_subject_id": "metric-ext-1",
                "source_system": "gitlab",
                "source_type": "gitlab_daily_code_metric",
                "summary": "待归属 GitLab 指标",
                "suggested_product_id": product["id"],
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        resolved = client.post(
            f"/api/attribution/pending-items/{pending['id']}/resolve",
            json={
                "resolution_action": "link_existing_context",
                "resolution_note": "归属到 AI Brain 运营测试产品",
                "resolved_product_id": product["id"],
            },
            headers=headers,
        ).json()["data"]
        assert resolved["status"] == "resolved"

        use_empty_postgres_runtime_store()
        pending_list = client.get(
            f"/api/attribution/pending-items?status=resolved&resolved_product_id={product['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert pending_list[0]["id"] == pending["id"]

        gitlab_metric = client.post(
            "/api/devops/gitlab/daily-code-metrics",
            json={
                "active_author_count": 2,
                "additions": 120,
                "author_metrics": [{"author": "alice", "commit_count": 2}],
                "changed_files": 8,
                "commit_count": 3,
                "deletions": 12,
                "metric_date": "2026-06-03",
                "merge_request_count": 1,
                "product_id": product["id"],
                "repository_id": repository_record["id"],
                "risk_count": 0,
                "source_channel": "manual_import",
                "status": "collected",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        gitlab_metrics = client.get(
            f"/api/devops/gitlab/daily-code-metrics?repository_id={repository_record['id']}",
            headers=headers,
        ).json()["data"]["items"]
        assert gitlab_metrics[0]["id"] == gitlab_metric["id"]

        release = client.post(
            "/api/devops/jenkins/releases",
            json={
                "build_id": "build-dbfirst-1",
                "build_number": 1,
                "duration_seconds": 420,
                "environment": "staging",
                "job_name": "ai-brain-deploy",
                "product_id": product["id"],
                "started_at": "2026-06-03T10:00:00Z",
                "status": "success",
                "version_id": version["id"],
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        releases = client.get(
            f"/api/devops/jenkins/releases?product_id={product['id']}&status=success",
            headers=headers,
        ).json()["data"]["items"]
        assert releases[0]["id"] == release["id"]

        online_metric = client.post(
            "/api/ops/online-log-metrics",
            json={
                "core_event_count": 500,
                "environment": "prod",
                "error_count": 5,
                "module_code": module["code"],
                "p95_latency_ms": 250.0,
                "product_id": product["id"],
                "request_count": 1000,
                "status": "collected",
                "top_errors": [{"count": 5, "message": "Timeout"}],
                "window_end": "2026-06-03T11:00:00Z",
                "window_start": "2026-06-03T10:00:00Z",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        online_metrics = client.get(
            f"/api/ops/online-log-metrics?product_id={product['id']}&module_code={module['code']}",
            headers=headers,
        ).json()["data"]["items"]
        assert online_metrics[0]["id"] == online_metric["id"]

        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        for event_type in [
            "collector_run.created",
            "collector_run.updated",
            "pending_attribution.created",
            "pending_attribution.resolved",
            "gitlab_daily_code_metric.created",
            "jenkins_release.created",
            "online_log_metric.created",
        ]:
            assert event_type in event_types
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
