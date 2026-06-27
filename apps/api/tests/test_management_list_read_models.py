from app.core.persistence import PostgresRuntimeStore
from app.core.users import MemoryUserRepository
from tests.test_database_persistence import FakeSnapshotRepository, app, auth_headers, client


def _use_repository(repository: FakeSnapshotRepository):
    original_store = app.state.store
    original_users = app.state.user_repository
    app.state.store = PostgresRuntimeStore(repository)
    app.state.user_repository = MemoryUserRepository.seeded()
    return original_store, original_users


def _restore_repository(original_store, original_users) -> None:
    app.state.store = original_store
    app.state.user_repository = original_users


def test_operational_metrics_use_repository_read_model_for_sql_pagination():
    class ReadModelOnlyOperationalRepository(FakeSnapshotRepository):
        def __init__(self) -> None:
            super().__init__()
            self.operational_metric_reads: list[dict] = []

        def list_gitlab_daily_code_metrics(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("operational metrics should not load all GitLab metrics")

        def list_jenkins_release_records(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("operational metrics should not load all Jenkins releases")

        def list_online_log_metrics(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("operational metrics should not load all online logs")

        def list_operational_metric_items(self, **kwargs):  # type: ignore[no-untyped-def]
            self.operational_metric_reads.append(dict(kwargs))
            return {
                "items": [
                    {
                        "build_id": "build-read-model",
                        "category": "Jenkins 发布",
                        "id": "jenkins_release_read_model",
                        "name": "enterprise-ai-brain-deploy",
                        "product_id": "product_read_model",
                        "status": "success",
                        "updated_at": "2026-06-05T09:30:00+00:00",
                        "value": "build-read-model",
                        "version_id": "version_read_model",
                    }
                ],
                "page": 1,
                "page_size": 1,
                "total": 2,
            }

    repository = ReadModelOnlyOperationalRepository()
    original_store, original_users = _use_repository(repository)

    try:
        response = client.get(
            (
                "/api/devops/operational-metrics"
                "?category=Jenkins 发布"
                "&name=deploy"
                "&status=success"
                "&page=1&page_size=1"
                "&sort_by=updated_at&sort_order=desc"
            ),
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert data["items"][0]["id"] == "jenkins_release_read_model"
        assert repository.operational_metric_reads == [
            {
                "category": "Jenkins 发布",
                "name": "deploy",
                "page": 1,
                "page_size": 1,
                "sort_by": "updated_at",
                "sort_order": "desc",
                "status": "success",
            }
        ]
    finally:
        _restore_repository(original_store, original_users)


def test_insight_items_use_repository_read_model_for_sql_pagination():
    class ReadModelOnlyInsightRepository(FakeSnapshotRepository):
        def __init__(self) -> None:
            super().__init__()
            self.user_insight_item_reads: list[dict] = []

        def list_user_usage_metrics(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("insight items should not load all usage metrics")

        def list_user_feedback(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("insight items should not load all feedback rows")

        def list_iteration_plan_suggestions(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("insight items should not load all iteration suggestions")

        def list_user_insight_items(self, **kwargs):  # type: ignore[no-untyped-def]
            self.user_insight_item_reads.append(dict(kwargs))
            return {
                "items": [
                    {
                        "category": "用户反馈",
                        "confidence_level": "-",
                        "converted_requirement_id": "-",
                        "feature_code": "search",
                        "feedback_type": "improvement",
                        "id": "feedback_read_model",
                        "module_code": "knowledge",
                        "owner": "user_admin",
                        "planning_cycle": "-",
                        "priority": "-",
                        "product_id": "product_read_model",
                        "status": "open",
                        "summary": "迭代版本筛选反馈",
                        "updated_at": "2026-06-05T09:00:00+00:00",
                        "version_id": "-",
                    }
                ],
                "page": 1,
                "page_size": 1,
                "total": 3,
            }

    repository = ReadModelOnlyInsightRepository()
    original_store, original_users = _use_repository(repository)

    try:
        response = client.get(
            (
                "/api/insights/items"
                "?category=用户反馈"
                "&summary=迭代版本"
                "&status=open"
                "&page=1&page_size=1"
                "&sort_by=updated_at&sort_order=desc"
            ),
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert data["items"][0]["id"] == "feedback_read_model"
        assert repository.user_insight_item_reads == [
            {
                "category": "用户反馈",
                "page": 1,
                "page_size": 1,
                "sort_by": "updated_at",
                "sort_order": "desc",
                "status": "open",
                "summary": "迭代版本",
            }
        ]
    finally:
        _restore_repository(original_store, original_users)


def test_requirement_list_uses_repository_read_model_for_sql_pagination():
    class ReadModelOnlyRequirementRepository(FakeSnapshotRepository):
        def __init__(self) -> None:
            super().__init__()
            self.requirement_counts: list[dict] = []
            self.requirement_reads: list[dict] = []

        def get_task_workflow_source_rows(self) -> dict:  # type: ignore[override]
            raise AssertionError("requirement list should not load task workflow source rows")

        def count_requirement_summaries(self, **kwargs):  # type: ignore[no-untyped-def]
            self.requirement_counts.append(dict(kwargs))
            return 2

        def list_requirement_summaries(self, **kwargs):  # type: ignore[no-untyped-def]
            self.requirement_reads.append(dict(kwargs))
            return [
                {
                    "brain_app_id": "rd_brain",
                    "content": "read model requirement",
                    "created_at": "2026-06-05T09:10:00+00:00",
                    "created_by": "user_admin",
                    "id": "requirement_read_model",
                    "module_code": "assistant",
                    "priority": "P0",
                    "product_code": "AI-BRAIN",
                    "product_id": "product_read_model",
                    "product_name": "AI Brain",
                    "status": "testing",
                    "task_ids": [],
                    "title": "SQL read model requirement",
                    "updated_at": "2026-06-05T09:20:00+00:00",
                    "version_code": "v1",
                    "version_id": "version_read_model",
                    "version_name": "v1",
                }
            ]

    repository = ReadModelOnlyRequirementRepository()
    original_store, original_users = _use_repository(repository)

    try:
        response = client.get(
            (
                "/api/requirements"
                "?priority=P0"
                "&product=AI-BRAIN"
                "&product_id=product_read_model"
                "&status=testing"
                "&title=SQL"
                "&version=v1"
                "&version_id=version_read_model"
                "&page=2&page_size=1"
                "&sort_by=title&sort_order=asc"
            ),
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 2
        assert data["page"] == 2
        assert data["page_size"] == 1
        assert data["items"][0]["id"] == "requirement_read_model"
        expected_query = {
            "priority": "P0",
            "product": "AI-BRAIN",
            "product_id": "product_read_model",
            "source": None,
            "status": "testing",
            "title": "SQL",
            "version": "v1",
            "version_id": "version_read_model",
        }
        assert repository.requirement_counts == [expected_query]
        assert repository.requirement_reads == [
            {
                **expected_query,
                "limit": 1,
                "offset": 1,
                "sort_by": "title",
                "sort_order": "asc",
            }
        ]
    finally:
        _restore_repository(original_store, original_users)


def test_bug_list_uses_repository_read_model_for_sql_pagination():
    class ReadModelOnlyBugRepository(FakeSnapshotRepository):
        def __init__(self) -> None:
            super().__init__()
            self.bug_counts: list[dict] = []
            self.bug_reads: list[dict] = []

        def list_bugs(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("bug list should not load all bug rows")

        def count_bug_summaries(self, **kwargs):  # type: ignore[no-untyped-def]
            self.bug_counts.append(dict(kwargs))
            return 4

        def list_bug_summaries(self, **kwargs):  # type: ignore[no-untyped-def]
            self.bug_reads.append(dict(kwargs))
            return [
                {
                    "assignee": "qa@example.com",
                    "created_at": "2026-06-05T08:00:00+00:00",
                    "created_by": "user_admin",
                    "description": "read model bug",
                    "evidence": {"url": "/delivery/bugs"},
                    "id": "bug_read_model",
                    "module_code": "assistant",
                    "product_id": "product_read_model",
                    "reproduce_steps": ["open bug page"],
                    "severity": "major",
                    "source": "manual_test",
                    "status": "triaged",
                    "title": "SQL read model bug",
                    "updated_at": "2026-06-05T08:30:00+00:00",
                    "version_code": "v1",
                    "version_id": "version_read_model",
                    "version_name": "v1",
                }
            ]

    repository = ReadModelOnlyBugRepository()
    original_store, original_users = _use_repository(repository)

    try:
        response = client.get(
            (
                "/api/bugs"
                "?module=assistant"
                "&product_id=product_read_model"
                "&severity=major"
                "&source=manual_test"
                "&status=triaged"
                "&title=SQL"
                "&version=v1"
                "&version_id=version_read_model"
                "&page=2&page_size=2"
                "&sort_by=title&sort_order=asc"
            ),
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 4
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert data["items"][0]["id"] == "bug_read_model"
        expected_query = {
            "module": "assistant",
            "product_id": "product_read_model",
            "severity": "major",
            "source": "manual_test",
            "status": "triaged",
            "title": "SQL",
            "version": "v1",
            "version_id": "version_read_model",
        }
        assert repository.bug_counts == [expected_query]
        assert repository.bug_reads == [
            {
                **expected_query,
                "limit": 2,
                "offset": 2,
                "sort_by": "title",
                "sort_order": "asc",
            }
        ]
    finally:
        _restore_repository(original_store, original_users)


def test_product_list_uses_repository_read_model_for_sql_pagination():
    class ReadModelOnlyProductRepository(FakeSnapshotRepository):
        def __init__(self) -> None:
            super().__init__()
            self.product_counts: list[dict] = []
            self.product_reads: list[dict] = []

        def list_products(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("product list should not load all product rows")

        def count_product_summaries(self, **kwargs):  # type: ignore[no-untyped-def]
            self.product_counts.append(dict(kwargs))
            return 5

        def list_product_summaries(self, **kwargs):  # type: ignore[no-untyped-def]
            self.product_reads.append(dict(kwargs))
            return [
                {
                    "code": "AI-BRAIN",
                    "current_version_code": "v1",
                    "current_version_name": "v1",
                    "description": "read model product",
                    "display_order": 10,
                    "id": "product_read_model",
                    "module_count": 2,
                    "name": "AI Brain",
                    "owner_team": "platform",
                    "status": "active",
                }
            ]

    repository = ReadModelOnlyProductRepository()
    original_store, original_users = _use_repository(repository)

    try:
        response = client.get(
            (
                "/api/products"
                "?active_only=true"
                "&code=AI"
                "&name=Brain"
                "&owner_team=platform"
                "&status=active"
                "&page=2&page_size=2"
                "&sort_by=name&sort_order=asc"
            ),
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 5
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert data["items"][0]["id"] == "product_read_model"
        expected_query = {
            "active_only": True,
            "code": "AI",
            "name": "Brain",
            "owner_team": "platform",
            "status": "active",
        }
        assert repository.product_counts == [expected_query]
        assert repository.product_reads == [
            {
                **expected_query,
                "limit": 2,
                "offset": 2,
                "sort_by": "name",
                "sort_order": "asc",
            }
        ]
    finally:
        _restore_repository(original_store, original_users)


def test_product_version_list_uses_repository_read_model_for_sql_pagination():
    class ReadModelOnlyProductVersionRepository(FakeSnapshotRepository):
        def __init__(self) -> None:
            super().__init__()
            self.version_counts: list[dict] = []
            self.version_reads: list[dict] = []

        def list_product_version_summaries(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("product version list should not load all versions")

        def count_product_version_summaries(self, **kwargs):  # type: ignore[no-untyped-def]
            self.version_counts.append(dict(kwargs))
            return 6

        def list_product_version_summaries_page(self, **kwargs):  # type: ignore[no-untyped-def]
            self.version_reads.append(dict(kwargs))
            return [
                {
                    "code": "v1",
                    "created_at": "2026-06-05T07:30:00+00:00",
                    "description": "read model version",
                    "id": "version_read_model",
                    "name": "v1",
                    "product_code": "AI-BRAIN",
                    "product_id": "product_read_model",
                    "product_name": "AI Brain",
                    "release_date": None,
                    "start_date": "2026-06-05",
                    "status": "active",
                    "updated_at": "2026-06-05T08:00:00+00:00",
                }
            ]

    repository = ReadModelOnlyProductVersionRepository()
    original_store, original_users = _use_repository(repository)

    try:
        response = client.get(
            (
                "/api/product-versions"
                "?active_only=true"
                "&code=v"
                "&name=v1"
                "&product=AI"
                "&product_id=product_read_model"
                "&status=active"
                "&page=3&page_size=2"
                "&sort_by=name&sort_order=asc"
            ),
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 6
        assert data["page"] == 3
        assert data["page_size"] == 2
        assert data["items"][0]["id"] == "version_read_model"
        expected_query = {
            "active_only": True,
            "code": "v",
            "name": "v1",
            "product": "AI",
            "product_id": "product_read_model",
            "status": "active",
        }
        assert repository.version_counts == [expected_query]
        assert repository.version_reads == [
            {
                **expected_query,
                "limit": 2,
                "offset": 4,
                "sort_by": "name",
                "sort_order": "asc",
            }
        ]
    finally:
        _restore_repository(original_store, original_users)


def test_rd_task_executor_policy_list_uses_repository_read_model_for_sql_pagination():
    class ReadModelOnlyRdExecutorPolicyRepository(FakeSnapshotRepository):
        def __init__(self) -> None:
            super().__init__()
            self.count_reads: list[dict] = []
            self.page_reads: list[dict] = []

        def list_rd_task_executor_policies(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("RD executor policies should not load all policies")

        def save_rd_task_executor_policy_record(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("list test should not write RD executor policies")

        def delete_rd_task_executor_policy_record(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("list test should not delete RD executor policies")

        def count_rd_task_executor_policies(self, **kwargs):  # type: ignore[no-untyped-def]
            self.count_reads.append(dict(kwargs))
            return 3

        def list_rd_task_executor_policy_page(self, **kwargs):  # type: ignore[no-untyped-def]
            self.page_reads.append(dict(kwargs))
            return [
                {
                    "brain_app_id": "rd_brain",
                    "branch": "feature/runner",
                    "created_at": "2026-06-27T08:00:00+00:00",
                    "created_by": "user_admin",
                    "executor_type": "codex",
                    "id": "rd_executor_policy_read_model",
                    "instruction_template": "处理 {{task_id}}",
                    "name": "Codex 开发实现策略",
                    "output_contract": {"summary": "string"},
                    "priority": 20,
                    "product_id": "product_ai_brain",
                    "product_name": "AI Brain",
                    "repository_default_branch": "master",
                    "repository_id": "repo_ai_brain",
                    "repository_name": "AI Brain Web",
                    "runner_id": "runner_codex",
                    "runner_name": "Codex Runner",
                    "status": "active",
                    "task_type": "development_planning",
                    "timeout_seconds": 1800,
                    "updated_at": "2026-06-27T08:10:00+00:00",
                    "workspace_root": "/workspace/e-ai-brain",
                }
            ]

    repository = ReadModelOnlyRdExecutorPolicyRepository()
    original_store, original_users = _use_repository(repository)

    try:
        response = client.get(
            (
                "/api/delivery/rd-task-executor-policies"
                "?name=Codex"
                "&executor_type=codex"
                "&product_name=AI"
                "&status=active"
                "&task_type=development_planning"
                "&page=1&page_size=1"
                "&sort_by=priority&sort_order=desc"
            ),
            headers=auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert data["items"][0]["id"] == "rd_executor_policy_read_model"
        assert data["items"][0]["product_name"] == "AI Brain"
        assert data["performance"]["result_count"] == 1
        assert repository.count_reads == [
            {
                "executor_type": "codex",
                "name": "Codex",
                "product_id": None,
                "product_name": "AI",
                "status": "active",
                "task_type": "development_planning",
            }
        ]
        assert repository.page_reads == [
            {
                "executor_type": "codex",
                "limit": 1,
                "name": "Codex",
                "offset": 0,
                "product_id": None,
                "product_name": "AI",
                "sort_by": "priority",
                "sort_order": "desc",
                "status": "active",
                "task_type": "development_planning",
            }
        ]
    finally:
        _restore_repository(original_store, original_users)
