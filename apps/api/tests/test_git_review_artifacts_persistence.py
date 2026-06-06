from test_database_persistence import (
    FakeSnapshotRepository,
    apply_payload_to_store,
    gitlab_review_context_payload,
)

from app.core.persistence import PersistentMemoryStore


def test_gitlab_review_artifacts_are_persisted_through_fine_grained_repository_payload():
    repository = FakeSnapshotRepository()
    current_store = PersistentMemoryStore.from_repository(repository)
    apply_payload_to_store(current_store, gitlab_review_context_payload())
    current_store.gitlab_mr_snapshots["snapshot_009"] = {
        "author": {"username": "dev"},
        "base_sha": "base",
        "changed_files_summary": [{"additions": 2, "deletions": 1, "path": "app.py"}],
        "created_at": "2026-05-31T10:00:00+00:00",
        "created_by": "user_admin",
        "diff_limit_bytes": 500000,
        "diff_refs": {"base_sha": "base", "head_sha": "head"},
        "diff_size_bytes": 1234,
        "diff_storage_ref": "memory://gitlab-mr-diff/snapshot_009",
        "head_sha": "head",
        "id": "snapshot_009",
        "mr_iid": 12,
        "product_id": "product_001",
        "project_id": "123",
        "project_path": "group/project",
        "repository_id": "repo_001",
        "requirement_id": "requirement_001",
        "snapshot_hash": "hash_009",
        "source_branch": "feature",
        "target_branch": "main",
        "technical_solution_task_id": "task_002",
        "title": "MR title",
        "version_id": "version_001",
        "writeback_allowed": False,
    }
    current_store.code_review_reports["report_004"] = {
        "archived_at": None,
        "error_code": None,
        "executor": {"name": "code-review"},
        "findings": [{"file_path": "app.py", "severity": "high"}],
        "gitlab_mr_snapshot_id": "snapshot_009",
        "gitlab_writeback_performed": False,
        "id": "report_004",
        "review_id": "review_003",
        "risk_level": "high",
        "status": "pending_review",
        "summary": "Review summary",
        "task_id": "task_003",
    }

    current_store.persist()

    assert repository.gitlab_review_payload == {
        "code_review_reports": {
            "report_004": current_store.code_review_reports["report_004"],
        },
        "gitlab_mr_snapshots": {
            "snapshot_009": current_store.gitlab_mr_snapshots["snapshot_009"],
        },
    }


def test_structured_gitlab_review_restore_sync_counters_and_task_links():
    repository = FakeSnapshotRepository()
    context_payload = gitlab_review_context_payload()
    repository.payload = {
        "ai_tasks": {
            "task_003": {
                "created_by": "user_admin",
                "id": "task_003",
                "product_id": "product_001",
                "requirement_id": "requirement_001",
                "status": "waiting_review",
                "task_type": "code_review",
                "title": "Code Review",
                "version_id": "version_001",
            }
        },
        "human_reviews": context_payload["human_reviews"],
        "product_git_repositories": context_payload["product_git_repositories"],
        "product_versions": context_payload["product_versions"],
        "products": context_payload["products"],
        "requirements": context_payload["requirements"],
        "code_review_reports": {
            "report_002": {
                "gitlab_mr_snapshot_id": "snapshot_002",
                "id": "report_002",
                "risk_level": "low",
                "status": "draft",
                "summary": "旧快照报告",
                "task_id": "task_002",
            }
        },
        "counters": {"report": 2, "snapshot": 2, "task": 3},
        "gitlab_mr_snapshots": {
            "snapshot_002": {
                "id": "snapshot_002",
                "snapshot_hash": "old_hash",
            }
        },
    }
    repository.ai_tasks_payload = {"ai_tasks": context_payload["ai_tasks"]}
    repository.product_config_payload = {
        "product_git_repositories": context_payload["product_git_repositories"],
        "product_modules": {},
        "product_versions": context_payload["product_versions"],
        "products": context_payload["products"],
    }
    repository.requirements_payload = {"requirements": context_payload["requirements"]}
    repository.workflow_runtime_payload = {
        "graph_checkpoints": {},
        "graph_runs": {},
        "human_reviews": context_payload["human_reviews"],
    }
    repository.gitlab_review_payload = {
        "code_review_reports": {
            "report_004": {
                "executor": {"name": "code-review"},
                "findings": [],
                "gitlab_mr_snapshot_id": "snapshot_009",
                "gitlab_writeback_performed": False,
                "id": "report_004",
                "risk_level": "high",
                "status": "pending_review",
                "summary": "结构表报告",
                "task_id": "task_003",
            }
        },
        "gitlab_mr_snapshots": {
            "snapshot_009": {
                "author": {"username": "dev"},
                "base_sha": "base",
                "changed_files_summary": [],
                "created_by": "user_admin",
                "diff_limit_bytes": 500000,
                "diff_refs": {"base_sha": "base", "head_sha": "head"},
                "diff_size_bytes": 1234,
                "diff_storage_ref": "memory://gitlab-mr-diff/snapshot_009",
                "head_sha": "head",
                "id": "snapshot_009",
                "mr_iid": 12,
                "product_id": "product_001",
                "project_id": "123",
                "project_path": "group/project",
                "repository_id": "repo_001",
                "requirement_id": "requirement_001",
                "snapshot_hash": "hash_009",
                "source_branch": "feature",
                "target_branch": "main",
                "technical_solution_task_id": "task_002",
                "title": "MR title",
                "version_id": "version_001",
                "writeback_allowed": False,
            }
        },
    }

    rebuilt_store = PersistentMemoryStore.from_repository(repository)

    assert list(rebuilt_store.gitlab_mr_snapshots) == ["snapshot_009"]
    assert list(rebuilt_store.code_review_reports) == ["report_004"]
    assert rebuilt_store.ai_tasks["task_003"]["code_review_report_id"] == "report_004"
    assert rebuilt_store.new_id("snapshot") == "snapshot_010"
    assert rebuilt_store.new_id("report") == "report_005"


def test_stale_gitlab_review_artifacts_with_missing_references_are_not_persisted():
    repository = FakeSnapshotRepository()
    payload = gitlab_review_context_payload()
    payload["gitlab_mr_snapshots"] = {
        "snapshot_005": {
            "author": {"username": "dev"},
            "changed_files_summary": [],
            "created_by": "user_admin",
            "diff_limit_bytes": 500000,
            "diff_refs": {},
            "diff_size_bytes": 100,
            "diff_storage_ref": "memory://gitlab-mr-diff/snapshot_005",
            "head_sha": "head",
            "id": "snapshot_005",
            "mr_iid": 5,
            "product_id": "product_001",
            "repository_id": "repo_005",
            "requirement_id": "requirement_001",
            "snapshot_hash": "stale_hash",
            "source_branch": "feature",
            "target_branch": "main",
            "technical_solution_task_id": "task_002",
            "title": "Stale MR",
            "version_id": "version_001",
            "writeback_allowed": False,
        }
    }
    payload["code_review_reports"] = {
        "report_005": {
            "executor": {},
            "findings": [],
            "gitlab_mr_snapshot_id": "snapshot_005",
            "gitlab_writeback_performed": False,
            "id": "report_005",
            "risk_level": "low",
            "status": "pending_review",
            "summary": "Stale report",
            "task_id": "task_003",
        }
    }
    repository.payload = payload

    rebuilt_store = PersistentMemoryStore.from_repository(repository)
    rebuilt_store.persist()

    assert rebuilt_store.gitlab_mr_snapshots == {}
    assert rebuilt_store.code_review_reports == {}
    assert repository.gitlab_review_payload == {
        "code_review_reports": {},
        "gitlab_mr_snapshots": {},
    }
