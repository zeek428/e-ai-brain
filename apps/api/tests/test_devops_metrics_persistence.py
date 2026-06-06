from test_database_persistence import FakeSnapshotRepository

from app.core.persistence import PersistentMemoryStore


def test_gitlab_daily_code_metrics_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "devops-product",
            "id": "product_001",
            "name": "研发运营产品",
            "status": "active",
        }
    }
    store.product_git_repositories = {
        "repo_001": {
            "default_branch": "main",
            "git_provider": "gitlab",
            "id": "repo_001",
            "name": "devops-api",
            "product_id": "product_001",
            "project_path": "rd/devops-api",
            "remote_url": "https://gitlab.internal/rd/devops-api.git",
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        }
    }
    store.gitlab_daily_code_metrics = {
        "gitlab_metric_010": {
            "active_author_count": 4,
            "additions": 320,
            "author_metrics": [{"author": "alice", "commit_count": 3}],
            "changed_files": 18,
            "collected_at": "2026-06-01T08:00:00+00:00",
            "commit_count": 7,
            "created_at": "2026-06-01T08:00:00+00:00",
            "created_by": "user_admin",
            "deletions": 48,
            "id": "gitlab_metric_010",
            "merge_request_count": 2,
            "metric_date": "2026-06-01",
            "product_id": "product_001",
            "quality_score": 88.5,
            "repository_id": "repo_001",
            "risk_count": 1,
            "source_channel": "manual_import",
            "status": "collected",
            "updated_at": "2026-06-01T08:05:00+00:00",
        }
    }

    store.persist()

    assert repository.gitlab_daily_code_metrics_payload == {
        "gitlab_daily_code_metrics": store.gitlab_daily_code_metrics,
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": store.product_git_repositories,
        "product_modules": {},
        "product_versions": {},
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.gitlab_daily_code_metrics_payload = {
        "gitlab_daily_code_metrics": store.gitlab_daily_code_metrics,
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.gitlab_daily_code_metrics["gitlab_metric_010"]["commit_count"] == 7
    assert rebuilt_store.new_id("gitlab_metric") == "gitlab_metric_011"



def test_jenkins_release_records_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "release-product",
            "id": "product_001",
            "name": "发布验证产品",
            "status": "active",
        }
    }
    store.product_versions = {
        "version_001": {
            "code": "v1.2.0",
            "id": "version_001",
            "name": "v1.2.0",
            "product_id": "product_001",
            "status": "active",
        }
    }
    store.jenkins_release_records = {
        "jenkins_release_010": {
            "build_id": "build-20260601-17",
            "build_number": 17,
            "commit_sha": "abc123def456",
            "created_at": "2026-06-01T12:30:00+00:00",
            "created_by": "user_admin",
            "deployed_at": "2026-06-01T12:30:00+00:00",
            "duration_seconds": 480,
            "environment": "staging",
            "id": "jenkins_release_010",
            "job_name": "rd-platform-deploy",
            "product_id": "product_001",
            "source_channel": "manual_import",
            "started_at": "2026-06-01T12:22:00+00:00",
            "status": "success",
            "trigger_actor": "jenkins-admin",
            "updated_at": "2026-06-01T12:30:00+00:00",
            "version_id": "version_001",
        }
    }

    store.persist()

    assert repository.jenkins_release_records_payload == {
        "jenkins_release_records": store.jenkins_release_records,
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": store.product_versions,
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.jenkins_release_records_payload = {
        "jenkins_release_records": store.jenkins_release_records,
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.jenkins_release_records["jenkins_release_010"]["status"] == "success"
    assert rebuilt_store.new_id("jenkins_release") == "jenkins_release_011"



def test_online_log_metrics_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "ops-product",
            "id": "product_001",
            "name": "线上运营产品",
            "status": "active",
        }
    }
    store.product_modules = {
        "module_001": {
            "code": "checkout",
            "id": "module_001",
            "name": "结算模块",
            "product_id": "product_001",
            "status": "active",
        }
    }
    store.online_log_metrics = {
        "online_log_metric_010": {
            "anomaly_summary": "checkout error spike after release",
            "core_event_count": 240,
            "created_at": "2026-06-01T01:05:00+00:00",
            "created_by": "user_admin",
            "environment": "prod",
            "error_count": 12,
            "error_rate": 0.005,
            "id": "online_log_metric_010",
            "module_code": "checkout",
            "p95_latency_ms": 318.5,
            "p99_latency_ms": 640.25,
            "product_id": "product_001",
            "request_count": 2400,
            "source_channel": "manual_import",
            "status": "collected",
            "top_errors": [{"count": 7, "message": "PaymentTimeout"}],
            "updated_at": "2026-06-01T01:05:00+00:00",
            "window_end": "2026-06-01T01:00:00+00:00",
            "window_start": "2026-06-01T00:00:00+00:00",
        }
    }

    store.persist()

    assert repository.online_log_metrics_payload == {
        "online_log_metrics": store.online_log_metrics,
    }

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": store.product_modules,
        "product_versions": {},
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.online_log_metrics_payload = {
        "online_log_metrics": store.online_log_metrics,
    }

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.online_log_metrics["online_log_metric_010"]["environment"] == "prod"
    assert rebuilt_store.new_id("online_log_metric") == "online_log_metric_011"



def test_collector_runs_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore(repository)
    store.products = {
        "product_001": {
            "code": "collector-product",
            "id": "product_001",
            "name": "采集运行产品",
            "status": "active",
        }
    }
    store.collector_runs = {
        "collector_run_010": {
            "collector_type": "gitlab_daily_code_metric",
            "created_at": "2026-06-01T08:00:00+00:00",
            "created_by": "user_admin",
            "error_message": None,
            "finished_at": "2026-06-01T08:05:00+00:00",
            "id": "collector_run_010",
            "payload_summary": {"repository_path": "rd/api"},
            "product_id": "product_001",
            "records_imported": 3,
            "source_system": "gitlab",
            "started_at": "2026-06-01T08:00:00+00:00",
            "status": "succeeded",
            "updated_at": "2026-06-01T08:05:00+00:00",
        }
    }

    store.persist()

    assert repository.collector_runs_payload == {"collector_runs": store.collector_runs}

    restored_repository = FakeSnapshotRepository()
    restored_repository.product_config_payload = {
        "product_git_repositories": {},
        "product_modules": {},
        "product_versions": {},
        "products": store.products,
        "related_systems": {},
    }
    restored_repository.collector_runs_payload = {"collector_runs": store.collector_runs}

    rebuilt_store = PersistentMemoryStore.from_repository(restored_repository)

    assert rebuilt_store.collector_runs["collector_run_010"]["records_imported"] == 3
    assert rebuilt_store.new_id("collector_run") == "collector_run_011"

