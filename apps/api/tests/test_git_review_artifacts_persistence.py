from test_database_persistence import (
    FakeSnapshotRepository,
    app,
    apply_payload_to_store,
    auth_headers,
    client,
    gitlab_review_context_payload,
)

import app.services.git_review as git_review_service
from app.core.persistence import PersistentMemoryStore, PostgresRuntimeStore
from app.core.users import MemoryUserRepository


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


def test_gitlab_snapshot_writes_repository_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    def seed_snapshot_context() -> None:
        product = {
            "code": "GITLAB-DBFIRST",
            "id": "product_gitlab_dbfirst",
            "name": "GitLab DB-first 产品",
            "status": "active",
        }
        version = {
            "code": "v1",
            "id": "version_gitlab_dbfirst",
            "name": "v1",
            "product_id": "product_gitlab_dbfirst",
            "status": "active",
        }
        git_repository = {
            "default_branch": "main",
            "git_provider": "gitlab",
            "id": "repo_gitlab_dbfirst",
            "name": "主仓库",
            "product_id": "product_gitlab_dbfirst",
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        }
        requirement = {
            "content": "GitLab snapshot DB-first",
            "created_by": "user_admin",
            "id": "requirement_gitlab_dbfirst",
            "priority": "P1",
            "product_id": "product_gitlab_dbfirst",
            "status": "ready_for_dev",
            "task_ids": ["task_gitlab_solution_dbfirst"],
            "title": "GitLab snapshot DB-first",
            "version_id": "version_gitlab_dbfirst",
        }
        technical_solution = {
            "created_by": "user_admin",
            "current_step": "complete_archive",
            "graph_run_ids": [],
            "id": "task_gitlab_solution_dbfirst",
            "input_json": {},
            "output_json": {"kind": "technical_solution", "summary": "已确认技术方案"},
            "product_context": {},
            "product_id": "product_gitlab_dbfirst",
            "requirement_id": "requirement_gitlab_dbfirst",
            "requirement_snapshot": {"id": "requirement_gitlab_dbfirst"},
            "review_ids": [],
            "status": "completed",
            "task_type": "technical_solution",
            "title": "已确认技术方案",
            "version_id": "version_gitlab_dbfirst",
        }
        repository.product_config_payload = {
            "product_git_repositories": {"repo_gitlab_dbfirst": git_repository},
            "product_modules": {},
            "product_versions": {"version_gitlab_dbfirst": version},
            "products": {"product_gitlab_dbfirst": product},
            "related_systems": {},
        }
        repository.requirements_payload = {
            "requirements": {"requirement_gitlab_dbfirst": requirement}
        }
        repository.ai_tasks_payload = {
            "ai_tasks": {"task_gitlab_solution_dbfirst": technical_solution}
        }

    def preview_with_files(files: list[dict]) -> dict:
        return {
            "author": {"name": "Dev", "username": "dev"},
            "base_sha": "base",
            "changed_file_count": len(files),
            "changed_files_summary": files,
            "diff_refs": {"base_sha": "base", "head_sha": "head"},
            "head_sha": "head",
            "mr_iid": 42,
            "project_id": "100",
            "project_path": "org/repo",
            "source_branch": "feature/db-first",
            "target_branch": "main",
            "title": "DB-first MR",
            "web_url": "https://gitlab.example.com/org/repo/-/merge_requests/42",
            "writeback_allowed": False,
        }

    seed_snapshot_context()
    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()
    monkeypatch.setattr(
        git_review_service,
        "gitlab_preview",
        lambda _repository, _mr_iid: preview_with_files(
            [{"additions": 3, "deletions": 1, "path": "apps/api/app/main.py"}]
        ),
    )

    try:
        headers = auth_headers()
        preview_response = client.get(
            "/api/devops/gitlab/merge-requests/repo_gitlab_dbfirst/42/preview",
            headers=headers,
        )
        assert preview_response.status_code == 200

        snapshot = client.post(
            "/api/devops/gitlab/merge-requests/repo_gitlab_dbfirst/42/snapshot",
            json={
                "requirement_id": "requirement_gitlab_dbfirst",
                "technical_solution_task_id": "task_gitlab_solution_dbfirst",
            },
            headers=headers,
        ).json()["data"]

        use_empty_postgres_runtime_store()
        assert list(repository.gitlab_review_payload["gitlab_mr_snapshots"]) == [snapshot["id"]]

        reused = client.post(
            "/api/devops/gitlab/merge-requests/repo_gitlab_dbfirst/42/snapshot",
            json={
                "requirement_id": "requirement_gitlab_dbfirst",
                "technical_solution_task_id": "task_gitlab_solution_dbfirst",
            },
            headers=headers,
        ).json()["data"]
        assert reused["id"] == snapshot["id"]

        use_empty_postgres_runtime_store()
        assert list(repository.gitlab_review_payload["gitlab_mr_snapshots"]) == [snapshot["id"]]

        monkeypatch.setattr(
            git_review_service,
            "gitlab_preview",
            lambda _repository, _mr_iid: preview_with_files(
                [
                    {"additions": 1, "deletions": 0, "path": f"file_{index}.py"}
                    for index in range(51)
                ]
            ),
        )
        failed = client.post(
            "/api/devops/gitlab/merge-requests/repo_gitlab_dbfirst/99/snapshot",
            json={
                "requirement_id": "requirement_gitlab_dbfirst",
                "technical_solution_task_id": "task_gitlab_solution_dbfirst",
            },
            headers=headers,
        )
        assert failed.status_code == 413

        use_empty_postgres_runtime_store()
        assert list(repository.gitlab_review_payload["gitlab_mr_snapshots"]) == [snapshot["id"]]
        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        assert "gitlab_mr.previewed" in event_types
        assert "gitlab_mr.snapshotted" in event_types
        assert "gitlab_mr.snapshot_reused" in event_types
        assert "gitlab_mr.snapshot_failed" in event_types
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users


def test_github_list_and_preview_audits_write_repository_without_request_persist(monkeypatch):
    original_store = app.state.store
    original_users = app.state.user_repository
    repository = FakeSnapshotRepository()

    def use_empty_postgres_runtime_store() -> PostgresRuntimeStore:
        runtime_store = PostgresRuntimeStore(repository)
        app.state.store = runtime_store
        return runtime_store

    use_empty_postgres_runtime_store()
    repository.product_config_payload = {
        "product_git_repositories": {
            "repo_github_dbfirst": {
                "credential_ref": "ghp_direct_local_token",
                "default_branch": "main",
                "git_provider": "github",
                "id": "repo_github_dbfirst",
                "name": "GitHub 主仓库",
                "product_id": "product_github_dbfirst",
                "project_path": "zeek428/e-ai-brain",
                "remote_url": "git@github.com:zeek428/e-ai-brain.git",
                "repo_type": "code",
                "root_path": "/",
                "status": "active",
            }
        },
        "product_modules": {},
        "product_versions": {},
        "products": {
            "product_github_dbfirst": {
                "code": "GITHUB-DBFIRST",
                "id": "product_github_dbfirst",
                "name": "GitHub DB-first 产品",
                "status": "active",
            }
        },
        "related_systems": {},
    }
    use_empty_postgres_runtime_store()
    app.state.user_repository = MemoryUserRepository.seeded()

    def github_pull_requests(
        repo: dict,
        *,
        state: str,
        limit: int,
    ) -> list[dict]:
        return [
            {
                "author": {"name": "zeek428", "username": "zeek428"},
                "base_sha": "base",
                "created_at": "2026-06-03T08:00:00Z",
                "head_sha": "head",
                "number": 3,
                "project_path": "zeek428/e-ai-brain",
                "repository_id": repo["id"],
                "source_branch": "feature/db-first",
                "state": state,
                "target_branch": "main",
                "title": "DB-first PR",
                "updated_at": "2026-06-03T09:00:00Z",
                "web_url": "https://github.com/zeek428/e-ai-brain/pull/3",
                "writeback_allowed": False,
            }
        ][:limit]

    def github_preview(repo: dict, pr_number: int) -> dict:
        return {
            "author": {"name": "zeek428", "username": "zeek428"},
            "base_sha": "base",
            "changed_file_count": 1,
            "changed_files_summary": [
                {"additions": 4, "deletions": 1, "path": "apps/api/app/main.py"}
            ],
            "diff_refs": {"base_sha": "base", "head_sha": "head"},
            "head_sha": "head",
            "mr_iid": pr_number,
            "project_id": None,
            "project_path": "zeek428/e-ai-brain",
            "repository_id": repo["id"],
            "source_branch": "feature/db-first",
            "target_branch": "main",
            "title": "DB-first PR",
            "web_url": "https://github.com/zeek428/e-ai-brain/pull/3",
            "writeback_allowed": False,
        }

    monkeypatch.setattr(git_review_service, "github_pull_requests", github_pull_requests)
    monkeypatch.setattr(git_review_service, "github_preview", github_preview)

    try:
        headers = auth_headers()
        listed = client.get(
            "/api/devops/github/pull-requests/repo_github_dbfirst?state=all&limit=2",
            headers=headers,
        )
        assert listed.status_code == 200

        use_empty_postgres_runtime_store()
        preview = client.get(
            "/api/devops/github/pull-requests/repo_github_dbfirst/3/preview",
            headers=headers,
        )
        assert preview.status_code == 200

        use_empty_postgres_runtime_store()
        event_types = [
            event["event_type"] for event in repository.audit_events_payload["audit_events"]
        ]
        assert "github_pr.listed" in event_types
        assert "github_pr.previewed" in event_types
    finally:
        app.state.store = original_store
        app.state.user_repository = original_users
