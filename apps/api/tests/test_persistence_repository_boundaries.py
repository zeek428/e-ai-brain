from datetime import UTC, datetime
from pathlib import Path

from app.core.persistence import PersistentMemoryStore, PostgresSnapshotRepository
from app.core.repositories.assistant_chat import AssistantChatReadRepository
from app.core.repositories.audit import AuditReadRepository
from app.core.repositories.brain_apps import BrainAppReadRepository
from app.core.repositories.bugs import BugReadRepository
from app.core.repositories.code_inspections import CodeInspectionReadRepository
from app.core.repositories.devops import DevopsReadRepository
from app.core.repositories.execution_governance import ExecutionGovernanceReadRepository
from app.core.repositories.git_review import GitReviewReadRepository
from app.core.repositories.knowledge import KnowledgeReadRepository
from app.core.repositories.knowledge_writes import KnowledgeWriteRepository
from app.core.repositories.lifecycle_dashboard import LifecycleDashboardReadRepository
from app.core.repositories.mock_writeback import MockWritebackReadRepository
from app.core.repositories.model_gateway import ModelGatewayReadRepository
from app.core.repositories.operational_collection import OperationalCollectionReadRepository
from app.core.repositories.plugins import PluginReadRepository
from app.core.repositories.product_config import ProductConfigReadRepository
from app.core.repositories.product_config_writes import ProductConfigWriteRepository
from app.core.repositories.requirements import RequirementReadRepository
from app.core.repositories.scheduled_ai_jobs import ScheduledAiJobReadRepository
from app.core.repositories.system_state import SystemStateRepository
from app.core.repositories.table_maintenance import TableMaintenanceRepository
from app.core.repositories.tasks import TaskReadRepository
from app.core.repositories.user_insights import UserInsightReadRepository
from app.core.repositories.user_insights_writes import UserInsightWriteRepository
from app.services.assistant_action_drafts import ASSISTANT_DRAFT_ACTIONS
from tests.test_database_persistence import FakeSnapshotRepository


class _StaticCursor:
    def __init__(self, rows: list[tuple]) -> None:
        self.rows = rows
        self.queries: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query: str, params: tuple | None = None) -> None:
        self.queries.append(query)

    def fetchall(self) -> list[tuple]:
        return self.rows


class _StaticConnection:
    def __init__(self, cursor: _StaticCursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self) -> _StaticCursor:
        return self._cursor


def test_postgres_system_state_delegates_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        SystemStateRepository,
        "next_id",
        lambda self, prefix: calls.append(("next_id", {"prefix": prefix})) or f"{prefix}_123",
    )
    monkeypatch.setattr(
        SystemStateRepository,
        "load_snapshot",
        lambda self: calls.append(("load_snapshot", {})) or {"source": "load_snapshot"},
    )
    monkeypatch.setattr(
        SystemStateRepository,
        "save_snapshot",
        lambda self, payload: calls.append(("save_snapshot", {"payload": payload})),
    )

    assert repository.next_id("requirement") == "requirement_123"
    assert repository.load() == {"source": "load_snapshot"}
    repository.save({"requirements": {}})

    assert calls == [
        ("next_id", {"prefix": "requirement"}),
        ("load_snapshot", {}),
        ("save_snapshot", {"payload": {"requirements": {}}}),
    ]


def test_ai_executor_task_product_scope_includes_deployment_runs():
    repository = PluginReadRepository(lambda: None)

    where, params = repository._ai_executor_task_where(
        product_scope_ids=["product_scope"],
    )

    assert "FROM deployment_runs scoped_deployment_run" in where
    assert "JOIN deployment_requests scoped_deployment" in where
    assert "scoped_deployment_run.id = ai_executor_tasks.deployment_run_id" in where
    assert params == [["product_scope"]] * 4


def test_postgres_table_maintenance_delegates_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []
    cursor = object()

    monkeypatch.setattr(
        TableMaintenanceRepository,
        "delete_missing",
        lambda self, cursor, table_name, items: calls.append(
            ("delete_missing", {"cursor": cursor, "items": items, "table_name": table_name})
        ),
    )
    monkeypatch.setattr(
        TableMaintenanceRepository,
        "delete_missing_ids",
        lambda self, cursor, table_name, item_ids: calls.append(
            (
                "delete_missing_ids",
                {"cursor": cursor, "item_ids": item_ids, "table_name": table_name},
            )
        ),
    )

    repository._delete_missing(
        cursor,
        "requirements",
        {"requirement_001": {"id": "requirement_001"}},
    )
    repository._delete_missing_ids(cursor, "audit_events", ["audit_001"])

    assert calls == [
        (
            "delete_missing",
            {
                "cursor": cursor,
                "items": {"requirement_001": {"id": "requirement_001"}},
                "table_name": "requirements",
            },
        ),
        (
            "delete_missing_ids",
            {"cursor": cursor, "item_ids": ["audit_001"], "table_name": "audit_events"},
        ),
    ]


def test_postgres_scheduled_job_run_list_delegates_run_ids_filter(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[dict] = []

    def fake_list_scheduled_job_runs(
        self,
        *,
        run_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        calls.append(
            {
                "run_ids": run_ids,
                "scheduled_job_id": scheduled_job_id,
                "status": status,
            },
        )
        return [{"id": "scheduled_job_run_001"}]

    monkeypatch.setattr(
        ScheduledAiJobReadRepository,
        "list_scheduled_job_runs",
        fake_list_scheduled_job_runs,
    )

    assert repository.list_scheduled_job_runs(
        run_ids=["scheduled_job_run_001"],
        scheduled_job_id="scheduled_job_001",
        status="failed",
    ) == [{"id": "scheduled_job_run_001"}]
    assert calls == [
        {
            "run_ids": ["scheduled_job_run_001"],
            "scheduled_job_id": "scheduled_job_001",
            "status": "failed",
        },
    ]


def test_postgres_schema_compatibility_applies_recent_additive_migrations(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    applied_migrations: list[str] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql: str) -> None:
            assert sql.strip()

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(repository, "_connect", lambda: FakeConnection())
    monkeypatch.setattr(
        repository,
        "_apply_additive_migration",
        lambda cursor, filename: applied_migrations.append(filename),
    )

    repository._ensure_schema_compatibility()

    assert "028_assistant_message_references.sql" in applied_migrations
    assert "036_integration_plugins.sql" in applied_migrations
    assert "038_plugin_connection_request_config.sql" in applied_migrations
    assert "039_task_center_operational_menus.sql" in applied_migrations
    assert "044_scheduled_job_run_source.sql" in applied_migrations
    assert "045_scheduled_job_collector_types.sql" in applied_migrations
    assert "046_code_inspection_plugin_source.sql" in applied_migrations
    assert "047_plugin_connection_last_test_summary.sql" in applied_migrations
    assert "048_plugin_connection_test_history.sql" in applied_migrations
    assert "050_code_inspection_remediation_tasks.sql" in applied_migrations
    assert "053_menu_management.sql" in applied_migrations
    assert "054_assistant_action_drafts.sql" in applied_migrations
    assert "058_assistant_action_draft_expiry.sql" in applied_migrations
    assert "059_assistant_rd_task_drafts.sql" in applied_migrations
    assert "063_assistant_chat_runs.sql" in applied_migrations
    assert "069_execution_trace_read_model.sql" in applied_migrations
    assert "070_code_inspection_suppression_approval.sql" in applied_migrations
    assert "073_code_inspection_risk_acceptance_expiry.sql" in applied_migrations
    assert "074_internal_data_source_plugin.sql" in applied_migrations
    assert "075_internal_data_source_detail_permission.sql" in applied_migrations
    assert "076_assistant_action_naming.sql" in applied_migrations
    assert "077_ai_agent_packages.sql" in applied_migrations
    assert "078_ai_executor_approval_requests.sql" in applied_migrations
    assert "079_plugin_invocation_log_nullable_config_refs.sql" in applied_migrations
    assert "083_viewer_menu_task_boundary.sql" in applied_migrations
    assert "084_viewer_assistant_menu_boundary.sql" in applied_migrations
    assert "085_viewer_product_read_menu.sql" in applied_migrations
    assert "086_dingtalk_oauth_ephemeral_states.sql" in applied_migrations
    assert "087_user_profile_contact.sql" in applied_migrations
    assert "088_dingtalk_corp_name.sql" in applied_migrations
    assert "089_user_password_login_state.sql" in applied_migrations
    assert "090_role_boundary_cleanup.sql" in applied_migrations
    assert "093_bug_fix_task_type.sql" in applied_migrations
    assert "100_operational_deployment_menu.sql" in applied_migrations
    assert "101_deployment_strategies.sql" in applied_migrations
    assert "102_autonomous_delivery_governance.sql" in applied_migrations


def test_postgres_execution_governance_delegates_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[dict] = []

    def fake_list_quality_gate_policies(self, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        return [{"id": "quality_gate_policy_001"}]

    monkeypatch.setattr(
        ExecutionGovernanceReadRepository,
        "list_quality_gate_policies",
        fake_list_quality_gate_policies,
    )

    assert repository.list_quality_gate_policies(
        phase="pre_merge",
        product_id="product_001",
        product_scope_ids=["product_001"],
        status="active",
        task_type="development_planning",
    ) == [{"id": "quality_gate_policy_001"}]
    assert calls == [
        {
            "phase": "pre_merge",
            "product_id": "product_001",
            "product_scope_ids": ["product_001"],
            "status": "active",
            "task_type": "development_planning",
        }
    ]


def test_assistant_action_draft_constraint_migrations_cover_supported_actions():
    migrations_dir = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations"

    for filename in (
        "054_assistant_action_drafts.sql",
        "057_assistant_analysis_drafts.sql",
        "059_assistant_rd_task_drafts.sql",
    ):
        sql = (migrations_dir / filename).read_text(encoding="utf-8")
        missing_actions = sorted(
            action for action in ASSISTANT_DRAFT_ACTIONS if f"'{action}'" not in sql
        )
        assert missing_actions == []


def test_assistant_message_status_migration_adds_check_constraint():
    migrations_dir = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations"
    sql = (migrations_dir / "063_assistant_chat_runs.sql").read_text(encoding="utf-8")

    assert "ck_assistant_messages_status" in sql
    assert "DO $$" not in sql
    for status in ("pending", "completed", "cancelled", "failed"):
        assert f"'{status}'" in sql


def test_postgres_brain_app_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str):
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return {"brain_apps": {"rd_brain": {"source": name}}}

        return _call

    monkeypatch.setattr(
        BrainAppReadRepository,
        "load_brain_apps",
        record_call("load_brain_apps"),
    )

    assert repository.load_brain_apps()["brain_apps"]["rd_brain"]["source"] == (
        "load_brain_apps"
    )
    assert calls == [("load_brain_apps", {})]


def test_postgres_product_config_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str):
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return 7 if name.startswith("count_") else [{"source": name}]

        return _call

    monkeypatch.setattr(
        ProductConfigReadRepository,
        "load_product_config",
        record_call("load_product_config"),
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "count_product_summaries",
        record_call("count_product_summaries"),
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "list_product_summaries",
        record_call("list_product_summaries"),
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "get_product",
        lambda self, product_id: calls.append(("get_product", {"product_id": product_id}))
        or {"source": "get_product"},
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "get_product_version",
        lambda self, version_id: calls.append(("get_product_version", {"version_id": version_id}))
        or {"source": "get_product_version"},
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "get_product_git_repository",
        lambda self, repository_id: calls.append(
            ("get_product_git_repository", {"repository_id": repository_id})
        )
        or {"source": "get_product_git_repository"},
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "get_product_module",
        lambda self, module_id: calls.append(("get_product_module", {"module_id": module_id}))
        or {"source": "get_product_module"},
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "product_module_has_related_records",
        lambda self, product_id, module_code: calls.append(
            (
                "product_module_has_related_records",
                {"module_code": module_code, "product_id": product_id},
            )
        )
        or False,
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "product_version_has_related_records",
        lambda self, version_id: calls.append(
            ("product_version_has_related_records", {"version_id": version_id})
        )
        or False,
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "get_related_system",
        lambda self, system_id: calls.append(("get_related_system", {"system_id": system_id}))
        or {"source": "get_related_system"},
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "get_related_system_by_code",
        lambda self, code: calls.append(("get_related_system_by_code", {"code": code}))
        or {"source": "get_related_system_by_code"},
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "get_product_version_branch_config",
        lambda self, branch_config_id: calls.append(
            (
                "get_product_version_branch_config",
                {"branch_config_id": branch_config_id},
            )
        )
        or {"source": "get_product_version_branch_config"},
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "list_product_versions",
        lambda self, product_id, **kwargs: calls.append(
            ("list_product_versions", {"product_id": product_id, **kwargs})
        )
        or [{"source": "list_product_versions"}],
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "list_product_modules",
        lambda self, product_id, **kwargs: calls.append(
            ("list_product_modules", {"product_id": product_id, **kwargs})
        )
        or [{"source": "list_product_modules"}],
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "list_product_git_repositories",
        lambda self, product_id, **kwargs: calls.append(
            ("list_product_git_repositories", {"product_id": product_id, **kwargs})
        )
        or [{"source": "list_product_git_repositories"}],
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "list_related_systems",
        record_call("list_related_systems"),
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "count_product_version_summaries",
        record_call("count_product_version_summaries"),
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "list_product_version_summaries_page",
        record_call("list_product_version_summaries_page"),
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "list_product_version_summaries",
        record_call("list_product_version_summaries"),
    )

    assert repository.load_product_config()[0]["source"] == "load_product_config"
    assert repository.count_product_summaries(status="active") == 7
    assert repository.list_product_summaries(code="AI")[0]["source"] == "list_product_summaries"
    assert repository.get_product("product_001")["source"] == "get_product"
    assert repository.get_product_version("version_001")["source"] == "get_product_version"
    assert repository.get_product_git_repository("repo_001")["source"] == (
        "get_product_git_repository"
    )
    assert repository.get_product_module("module_001")["source"] == "get_product_module"
    assert repository.product_module_has_related_records("product_001", "core") is False
    assert repository.product_version_has_related_records("version_001") is False
    assert repository.get_related_system("related_001")["source"] == "get_related_system"
    assert repository.get_related_system_by_code("CRM")["source"] == (
        "get_related_system_by_code"
    )
    assert repository.get_product_version_branch_config("version_branch_001")["source"] == (
        "get_product_version_branch_config"
    )
    assert repository.list_product_versions("product_001", active_only=True)[0]["source"] == (
        "list_product_versions"
    )
    assert repository.list_product_modules("product_001")[0]["source"] == "list_product_modules"
    assert repository.list_product_git_repositories("product_001")[0]["source"] == (
        "list_product_git_repositories"
    )
    assert repository.list_related_systems(product_id="product_001")[0]["source"] == (
        "list_related_systems"
    )
    assert repository.count_product_version_summaries(product_id="product_001") == 7
    assert repository.list_product_version_summaries_page(status="testing")[0]["source"] == (
        "list_product_version_summaries_page"
    )
    assert repository.list_product_version_summaries(active_only=True)[0]["source"] == (
        "list_product_version_summaries"
    )

    assert [name for name, _ in calls] == [
        "load_product_config",
        "count_product_summaries",
        "list_product_summaries",
        "get_product",
        "get_product_version",
        "get_product_git_repository",
        "get_product_module",
        "product_module_has_related_records",
        "product_version_has_related_records",
        "get_related_system",
        "get_related_system_by_code",
        "get_product_version_branch_config",
        "list_product_versions",
        "list_product_modules",
        "list_product_git_repositories",
        "list_related_systems",
        "count_product_version_summaries",
        "list_product_version_summaries_page",
        "list_product_version_summaries",
    ]
    assert calls[3][1] == {"product_id": "product_001"}
    assert calls[4][1] == {"version_id": "version_001"}
    assert calls[5][1] == {"repository_id": "repo_001"}
    assert calls[6][1] == {"module_id": "module_001"}
    assert calls[7][1] == {"module_code": "core", "product_id": "product_001"}
    assert calls[8][1] == {"version_id": "version_001"}
    assert calls[9][1] == {"system_id": "related_001"}
    assert calls[10][1] == {"code": "CRM"}
    assert calls[11][1] == {"branch_config_id": "version_branch_001"}
    assert calls[12][1] == {"active_only": True, "product_id": "product_001"}
    assert calls[15][1] == {"active_only": False, "product_id": "product_001"}


def test_postgres_product_config_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"args": args, "kwargs": kwargs}))

        return _call

    monkeypatch.setattr(
        ProductConfigReadRepository,
        "save_product_config",
        record_save("save_product_config"),
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "save_product_config_record",
        record_save("save_product_config_record"),
    )
    monkeypatch.setattr(
        ProductConfigReadRepository,
        "delete_product_config_record",
        record_save("delete_product_config_record"),
    )

    payload = {"products": {"product_001": {"id": "product_001"}}}
    record = {"id": "product_001", "code": "AI"}
    audit_event = {"id": "audit_001", "event_type": "product.updated"}

    repository.save_product_config(payload)
    repository.save_product_config_record("products", record, audit_event=audit_event)
    repository.delete_product_config_record("products", "product_001", audit_event=audit_event)

    assert calls == [
        ("save_product_config", {"args": (payload,), "kwargs": {}}),
        (
            "save_product_config_record",
            {"args": ("products", record), "kwargs": {"audit_event": audit_event}},
        ),
        (
            "delete_product_config_record",
            {"args": ("products", "product_001"), "kwargs": {"audit_event": audit_event}},
        ),
    ]


def test_product_config_record_writes_use_single_transaction():
    connect_calls: list[dict] = []
    executed_sql: list[str] = []
    audit_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql: str, params=None):  # type: ignore[no-untyped-def]
            executed_sql.append(sql)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    repository = ProductConfigWriteRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    record = {
        "default_branch": "main",
        "git_provider": "github",
        "id": "repo_atomic",
        "name": "事务仓库",
        "product_id": "product_atomic",
        "project_path": "org/repo",
        "repo_type": "code",
        "root_path": "/",
        "status": "active",
    }
    audit_event = {"id": "audit_atomic", "event_type": "product_git_repository.updated"}

    repository.save_product_config_record(
        "product_git_repositories",
        record,
        audit_event=audit_event,
    )
    repository.delete_product_config_record(
        "product_git_repositories",
        "repo_atomic",
        audit_event=audit_event,
    )

    assert connect_calls == [{"autocommit": False}, {"autocommit": False}]
    assert len(audit_calls) == 2
    assert audit_calls == [[audit_event], [audit_event]]
    assert "INSERT INTO product_git_repositories" in executed_sql[0]
    assert "DELETE FROM product_git_repositories WHERE id = %s" in executed_sql[1]


def test_requirement_record_writes_use_single_transaction():
    connect_calls: list[dict] = []
    executed_sql: list[str] = []
    audit_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql: str, params=None):  # type: ignore[no-untyped-def]
            executed_sql.append(sql)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    repository = RequirementReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    record = {
        "content": "事务需求内容",
        "created_by": "user_admin",
        "id": "requirement_atomic",
        "product_id": "product_atomic",
        "title": "事务需求",
        "version_id": "version_atomic",
    }
    audit_event = {"id": "audit_requirement_atomic", "event_type": "requirement.updated"}

    repository.save_requirements({"requirements": {"requirement_atomic": record}})
    repository.save_requirement_record(record, audit_event=audit_event)
    repository.delete_requirement_record("requirement_atomic", audit_event=audit_event)

    assert connect_calls == [
        {"autocommit": False},
        {"autocommit": False},
        {"autocommit": False},
    ]
    assert audit_calls == [[audit_event], [audit_event]]
    assert any("INSERT INTO requirements" in sql for sql in executed_sql)
    assert "DELETE FROM requirements WHERE id = %s" in executed_sql[-1]


def test_postgres_ai_executor_task_page_read_delegates_to_plugin_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_count(self, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(("count_ai_executor_tasks", kwargs))
        return 7

    def record_page(self, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(("list_ai_executor_tasks_page", kwargs))
        return [{"id": "ai_executor_task_sql"}]

    monkeypatch.setattr(PluginReadRepository, "count_ai_executor_tasks", record_count)
    monkeypatch.setattr(PluginReadRepository, "list_ai_executor_tasks_page", record_page)

    assert (
        repository.count_ai_executor_tasks(
            ai_task_id="ai_task_001",
            runner_id="runner_001",
            scheduled_job_run_id="scheduled_run_001",
            status="queued",
        )
        == 7
    )
    assert repository.list_ai_executor_tasks_page(
        ai_task_id="ai_task_001",
        limit=10,
        offset=20,
        runner_id="runner_001",
        scheduled_job_run_id="scheduled_run_001",
        sort_by="created_at",
        sort_order="desc",
        status="queued",
    ) == [{"id": "ai_executor_task_sql"}]

    assert calls == [
        (
            "count_ai_executor_tasks",
            {
                "ai_task_id": "ai_task_001",
                "product_scope_ids": None,
                "runner_id": "runner_001",
                "scheduled_job_run_id": "scheduled_run_001",
                "status": "queued",
            },
        ),
        (
            "list_ai_executor_tasks_page",
            {
                "ai_task_id": "ai_task_001",
                "limit": 10,
                "offset": 20,
                "product_scope_ids": None,
                "runner_id": "runner_001",
                "scheduled_job_run_id": "scheduled_run_001",
                "sort_by": "created_at",
                "sort_order": "desc",
                "status": "queued",
            },
        ),
    ]


def test_runner_related_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    executed_sql: list[str] = []
    upsert_calls: list[tuple[str, dict]] = []
    audit_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql: str, params=None):  # type: ignore[no-untyped-def]
            executed_sql.append(sql)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def record_upsert(name: str):
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            upsert_calls.append((name, items))

        return _call

    monkeypatch.setattr(
        PluginReadRepository,
        "upsert_ai_executor_runners",
        record_upsert("runner"),
    )
    monkeypatch.setattr(
        PluginReadRepository,
        "upsert_ai_executor_tasks",
        record_upsert("task"),
    )
    monkeypatch.setattr(
        PluginReadRepository,
        "upsert_plugin_invocation_logs",
        record_upsert("plugin_log"),
    )

    repository = PluginReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    audit_event = {"id": "audit_runner_atomic", "event_type": "ai_executor_task.updated"}

    repository.save_ai_executor_runner_record(
        {"id": "runner_atomic"},
        audit_event=audit_event,
    )
    repository.save_ai_executor_task_record(
        {"id": "runner_task_atomic"},
        audit_event=audit_event,
    )
    repository.save_plugin_invocation_log_record(
        {"id": "plugin_log_atomic"},
        audit_event=audit_event,
    )
    repository.delete_ai_executor_runner_record(
        "runner_atomic",
        audit_event=audit_event,
    )

    assert connect_calls == [
        {"autocommit": False},
        {"autocommit": False},
        {"autocommit": False},
        {"autocommit": False},
    ]
    assert upsert_calls == [
        ("runner", {"runner_atomic": {"id": "runner_atomic"}}),
        ("task", {"runner_task_atomic": {"id": "runner_task_atomic"}}),
        ("plugin_log", {"plugin_log_atomic": {"id": "plugin_log_atomic"}}),
    ]
    assert audit_calls == [[audit_event], [audit_event], [audit_event], [audit_event]]
    assert "DELETE FROM ai_executor_runners WHERE id = %s" in executed_sql[-1]


def test_scheduled_job_runner_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    executed_sql: list[str] = []
    upsert_calls: list[tuple[str, dict]] = []
    audit_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql: str, params=None):  # type: ignore[no-untyped-def]
            executed_sql.append(sql)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def record_upsert(name: str):
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            upsert_calls.append((name, items))

        return _call

    monkeypatch.setattr(
        ScheduledAiJobReadRepository,
        "upsert_scheduled_jobs",
        record_upsert("job"),
    )
    monkeypatch.setattr(
        ScheduledAiJobReadRepository,
        "upsert_scheduled_job_runs",
        record_upsert("run"),
    )

    repository = ScheduledAiJobReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    audit_event = {"id": "audit_scheduled_atomic", "event_type": "scheduled_job_run.updated"}

    repository.save_scheduled_job_record({"id": "job_atomic"}, audit_event=audit_event)
    repository.save_scheduled_job_run_record({"id": "run_atomic"}, audit_event=audit_event)
    repository.delete_scheduled_job_record("job_atomic", audit_event=audit_event)

    assert connect_calls == [
        {"autocommit": False},
        {"autocommit": False},
        {"autocommit": False},
    ]
    assert upsert_calls == [
        ("job", {"job_atomic": {"id": "job_atomic"}}),
        ("run", {"run_atomic": {"id": "run_atomic"}}),
    ]
    assert audit_calls == [[audit_event], [audit_event], [audit_event]]
    assert "DELETE FROM scheduled_jobs WHERE id = %s" in executed_sql[-1]


def test_collector_run_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    upsert_calls: list[dict] = []
    audit_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def record_upsert(self, cursor, items):  # type: ignore[no-untyped-def]
        upsert_calls.append(items)

    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "upsert_collector_runs",
        record_upsert,
    )

    repository = OperationalCollectionReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    audit_event = {"id": "audit_collector_atomic", "event_type": "collector_run.updated"}

    repository.save_collector_run_record(
        {"id": "collector_atomic"},
        audit_event=audit_event,
    )

    assert connect_calls == [{"autocommit": False}]
    assert upsert_calls == [{"collector_atomic": {"id": "collector_atomic"}}]
    assert audit_calls == [[audit_event]]


def test_assistant_action_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    upsert_calls: list[tuple[str, dict]] = []
    audit_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def record_upsert(name: str):
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            upsert_calls.append((name, items))

        return _call

    monkeypatch.setattr(
        AssistantChatReadRepository,
        "upsert_assistant_action_drafts",
        record_upsert("draft"),
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "upsert_assistant_action_runs",
        record_upsert("run"),
    )

    repository = AssistantChatReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    draft = {"id": "assistant_action_draft_atomic"}
    run = {"id": "assistant_action_run_atomic"}
    audit_event = {"id": "audit_assistant_action_atomic"}

    repository.save_assistant_action_records(
        draft=draft,
        run=run,
        audit_events=[audit_event],
    )

    assert connect_calls == [{"autocommit": False}]
    assert upsert_calls == [
        ("draft", {"assistant_action_draft_atomic": draft}),
        ("run", {"assistant_action_run_atomic": run}),
    ]
    assert audit_calls == [[audit_event]]


def test_assistant_chat_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    upsert_calls: list[tuple[str, dict]] = []
    audit_calls: list[list[dict]] = []
    model_log_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def upsert_model_gateway_logs(cursor, model_logs):  # type: ignore[no-untyped-def]
        model_log_calls.append(model_logs)

    def record_upsert(name: str):
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            upsert_calls.append((name, items))

        return _call

    monkeypatch.setattr(
        AssistantChatReadRepository,
        "upsert_assistant_chat_runs",
        record_upsert("chat_run"),
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "upsert_assistant_conversations",
        record_upsert("conversation"),
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "upsert_assistant_messages",
        record_upsert("message"),
    )

    repository = AssistantChatReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
        upsert_model_gateway_logs=upsert_model_gateway_logs,
    )
    chat_run = {"id": "assistant_chat_run_atomic"}
    conversation = {"id": "assistant_conversation_atomic"}
    message = {"id": "assistant_message_atomic"}
    model_log = {"id": "model_gateway_log_atomic"}
    audit_event = {"id": "audit_assistant_chat_atomic"}

    repository.save_assistant_chat_records(
        chat_run=chat_run,
        conversation=conversation,
        messages=[message],
        model_log=model_log,
        audit_events=[audit_event],
    )

    assert connect_calls == [{"autocommit": False}]
    assert upsert_calls == [
        ("chat_run", {"assistant_chat_run_atomic": chat_run}),
        ("conversation", {"assistant_conversation_atomic": conversation}),
        ("message", {"assistant_message_atomic": message}),
    ]
    assert model_log_calls == [[model_log]]
    assert audit_calls == [[audit_event]]


def test_code_inspection_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    upsert_calls: list[tuple[str, dict]] = []
    audit_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def record_upsert(name: str):
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            upsert_calls.append((name, items))

        return _call

    monkeypatch.setattr(
        CodeInspectionReadRepository,
        "upsert_code_inspection_reports",
        record_upsert("report"),
    )
    monkeypatch.setattr(
        CodeInspectionReadRepository,
        "upsert_code_inspection_findings",
        record_upsert("finding"),
    )
    monkeypatch.setattr(
        CodeInspectionReadRepository,
        "upsert_code_inspection_notifications",
        record_upsert("notification"),
    )

    repository = CodeInspectionReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    report = {"id": "code_inspection_report_atomic"}
    finding = {"id": "code_inspection_finding_atomic"}
    notification = {"id": "code_inspection_notification_atomic"}
    audit_event = {"id": "audit_code_inspection_atomic"}

    repository.save_code_inspection_records(
        report=report,
        findings=[finding],
        notifications=[notification],
        audit_event=audit_event,
    )

    assert connect_calls == [{"autocommit": False}]
    assert upsert_calls == [
        ("report", {"code_inspection_report_atomic": report}),
        ("finding", {"code_inspection_finding_atomic": finding}),
        ("notification", {"code_inspection_notification_atomic": notification}),
    ]
    assert audit_calls == [[audit_event]]


def test_postgres_requirement_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str):
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return 7 if name.startswith("count_") else [{"source": name}]

        return _call

    monkeypatch.setattr(
        RequirementReadRepository,
        "load_requirements",
        record_call("load_requirements"),
    )
    monkeypatch.setattr(
        RequirementReadRepository,
        "count_requirement_summaries",
        record_call("count_requirement_summaries"),
    )
    monkeypatch.setattr(
        RequirementReadRepository,
        "list_requirement_summaries",
        record_call("list_requirement_summaries"),
    )

    assert repository.load_requirements()[0]["source"] == "load_requirements"
    assert repository.count_requirement_summaries(
        source="user_feedback",
        status="planned",
    ) == 7
    assert repository.list_requirement_summaries(
        product_id="product_001",
        source="product_planning",
    )[0]["source"] == "list_requirement_summaries"

    assert [name for name, _ in calls] == [
        "load_requirements",
        "count_requirement_summaries",
        "list_requirement_summaries",
    ]
    assert calls[1][1]["source"] == "user_feedback"
    assert calls[1][1]["status"] == "planned"
    assert calls[2][1]["product_id"] == "product_001"
    assert calls[2][1]["source"] == "product_planning"
    assert calls[2][1]["sort_by"] == "created_at"
    assert calls[2][1]["sort_order"] == "desc"


def test_postgres_requirement_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"args": args, "kwargs": kwargs}))

        return _call

    monkeypatch.setattr(
        RequirementReadRepository,
        "save_requirements",
        record_save("save_requirements"),
    )
    monkeypatch.setattr(
        RequirementReadRepository,
        "save_requirement_record",
        record_save("save_requirement_record"),
    )
    monkeypatch.setattr(
        RequirementReadRepository,
        "delete_requirement_record",
        record_save("delete_requirement_record"),
    )

    payload = {"requirements": {"requirement_001": {"id": "requirement_001"}}}
    record = {"id": "requirement_001", "title": "需求"}
    audit_event = {"id": "audit_001", "event_type": "requirement.updated"}

    repository.save_requirements(payload)
    repository.save_requirement_record(record, audit_event=audit_event)
    repository.delete_requirement_record("requirement_001", audit_event=audit_event)

    assert calls == [
        ("save_requirements", {"args": (payload,), "kwargs": {}}),
        (
            "save_requirement_record",
            {"args": (record,), "kwargs": {"audit_event": audit_event}},
        ),
        (
            "delete_requirement_record",
            {"args": ("requirement_001",), "kwargs": {"audit_event": audit_event}},
        ),
    ]


def test_postgres_task_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str):
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return 7 if name.startswith("count_") else [{"source": name}]

        return _call

    monkeypatch.setattr(
        TaskReadRepository,
        "load_ai_tasks",
        record_call("load_ai_tasks"),
    )
    monkeypatch.setattr(
        TaskReadRepository,
        "load_workflow_runtime",
        record_call("load_workflow_runtime"),
    )
    monkeypatch.setattr(
        TaskReadRepository,
        "count_ai_task_summaries",
        record_call("count_ai_task_summaries"),
    )
    monkeypatch.setattr(
        TaskReadRepository,
        "list_ai_task_summaries",
        record_call("list_ai_task_summaries"),
    )
    monkeypatch.setattr(
        TaskReadRepository,
        "list_pending_review_summaries",
        record_call("list_pending_review_summaries"),
    )

    assert repository.load_ai_tasks()[0]["source"] == "load_ai_tasks"
    assert repository.load_workflow_runtime()[0]["source"] == "load_workflow_runtime"
    assert repository.count_ai_task_summaries(status="running", read_scope="all") == 7
    assert repository.list_ai_task_summaries(product_id="product_001")[0]["source"] == (
        "list_ai_task_summaries"
    )
    assert repository.list_pending_review_summaries(read_scope="code_review")[0]["source"] == (
        "list_pending_review_summaries"
    )

    assert [name for name, _ in calls] == [
        "load_ai_tasks",
        "load_workflow_runtime",
        "count_ai_task_summaries",
        "list_ai_task_summaries",
        "list_pending_review_summaries",
    ]
    assert calls[2][1]["status"] == "running"
    assert calls[2][1]["read_scope"] == "all"
    assert calls[3][1]["product_id"] == "product_001"
    assert calls[3][1]["sort_by"] == "created_at"
    assert calls[3][1]["sort_order"] == "desc"
    assert calls[4][1]["read_scope"] == "code_review"


def test_ai_task_summary_repository_projects_code_inspection_location_title():
    now = datetime(2026, 7, 7, 2, 46, 15, tzinfo=UTC)
    cursor = _StaticCursor(
        [
            (
                "task_legacy",
                "rd_brain",
                None,
                "code_inspection_remediation",
                "[Code Inspection Remediation] 硬编码敏感凭据",
                "draft",
                "product_119",
                None,
                None,
                None,
                "user_admin",
                now,
                now,
                "AI Brain",
                {
                    "file_path": "apps/api/app/auth.py",
                    "line_number": 80,
                    "rule_id": "secrets.hardcoded_credential",
                    "title": "硬编码敏感凭据",
                },
            )
        ]
    )
    repository = TaskReadRepository(lambda: _StaticConnection(cursor))

    items = repository.list_ai_task_summaries(task_type="code_inspection_remediation")

    assert "t.input_json" in cursor.queries[0]
    assert items[0]["title"] == (
        "[Code Inspection Remediation] "
        "apps/api/app/auth.py:80 · 硬编码敏感凭据"
    )
    assert "input_json" not in items[0]


def test_postgres_task_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(self, payload):  # type: ignore[no-untyped-def]
        calls.append(("save_ai_tasks", {"payload": payload}))

    def record_runtime_save(self, payload):  # type: ignore[no-untyped-def]
        calls.append(("save_workflow_runtime", {"payload": payload}))

    def record_named_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))

        return _call

    monkeypatch.setattr(TaskReadRepository, "save_ai_tasks", record_save)
    monkeypatch.setattr(TaskReadRepository, "save_workflow_runtime", record_runtime_save)
    monkeypatch.setattr(
        TaskReadRepository,
        "save_requirement_and_ai_task_records",
        record_named_save("save_requirement_and_ai_task_records"),
    )
    monkeypatch.setattr(
        TaskReadRepository,
        "save_task_start_records",
        record_named_save("save_task_start_records"),
    )
    monkeypatch.setattr(
        TaskReadRepository,
        "save_review_decision_records",
        record_named_save("save_review_decision_records"),
    )
    monkeypatch.setattr(
        TaskReadRepository,
        "save_task_state_records",
        record_named_save("save_task_state_records"),
    )

    payload = {"ai_tasks": {"task_001": {"id": "task_001"}}}
    runtime_payload = {"graph_runs": {"graph_run_001": {"id": "graph_run_001"}}}
    requirement = {"id": "requirement_001"}
    task = {"id": "task_001"}
    review = {"id": "review_001"}
    graph_run = {"id": "graph_run_001"}
    checkpoint = {"id": "checkpoint_001"}
    audit_event = {"id": "audit_001"}
    audit_events = [{"id": "audit_002"}]
    model_log = {"id": "model_log_001"}
    code_review_report = {"id": "code_review_report_001"}
    bug = {"id": "bug_001"}
    deposit = {"id": "deposit_001"}

    repository.save_ai_tasks(payload)
    repository.save_workflow_runtime(runtime_payload)
    repository.save_requirement_and_ai_task_records(
        requirement=requirement,
        task=task,
        audit_event=audit_event,
    )
    repository.save_task_start_records(
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        audit_events=audit_events,
        model_log=model_log,
        code_review_report=code_review_report,
    )
    repository.save_review_decision_records(
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        audit_events=audit_events,
        requirement=requirement,
        knowledge_deposits=[deposit],
        bugs=[bug],
        code_review_report=code_review_report,
    )
    repository.save_task_state_records(
        task=task,
        audit_events=audit_events,
        reviews=[review],
        graph_run=graph_run,
        checkpoint=checkpoint,
        model_log=model_log,
    )

    assert calls == [
        ("save_ai_tasks", {"payload": payload}),
        ("save_workflow_runtime", {"payload": runtime_payload}),
        (
            "save_requirement_and_ai_task_records",
            {"requirement": requirement, "task": task, "audit_event": audit_event},
        ),
        (
            "save_task_start_records",
            {
                "task": task,
                "review": review,
                "graph_run": graph_run,
                "checkpoint": checkpoint,
                "audit_events": audit_events,
                "model_log": model_log,
                "code_review_report": code_review_report,
            },
        ),
        (
            "save_review_decision_records",
            {
                "task": task,
                "review": review,
                "graph_run": graph_run,
                "checkpoint": checkpoint,
                "audit_events": audit_events,
                "requirement": requirement,
                "knowledge_deposits": [deposit],
                "bugs": [bug],
                "code_review_report": code_review_report,
            },
        ),
        (
            "save_task_state_records",
            {
                "task": task,
                "audit_events": audit_events,
                "reviews": [review],
                "graph_run": graph_run,
                "checkpoint": checkpoint,
                "model_log": model_log,
            },
        ),
    ]


def test_postgres_bug_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str):
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return 7 if name.startswith("count_") else [{"source": name}]

        return _call

    monkeypatch.setattr(
        BugReadRepository,
        "load_bugs",
        record_call("load_bugs"),
    )
    monkeypatch.setattr(
        BugReadRepository,
        "count_bug_summaries",
        record_call("count_bug_summaries"),
    )
    monkeypatch.setattr(
        BugReadRepository,
        "list_bug_summaries",
        record_call("list_bug_summaries"),
    )

    assert repository.load_bugs()[0]["source"] == "load_bugs"
    assert repository.count_bug_summaries(status="open", severity="P1") == 7
    assert repository.list_bug_summaries(product_id="product_001")[0]["source"] == (
        "list_bug_summaries"
    )

    assert [name for name, _ in calls] == [
        "load_bugs",
        "count_bug_summaries",
        "list_bug_summaries",
    ]
    assert calls[1][1]["status"] == "open"
    assert calls[1][1]["severity"] == "P1"
    assert calls[2][1]["product_id"] == "product_001"
    assert calls[2][1]["sort_by"] == "created_at"
    assert calls[2][1]["sort_order"] == "desc"


def test_postgres_bug_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"args": args, "kwargs": kwargs}))

        return _call

    def record_clean(self, bugs):  # type: ignore[no-untyped-def]
        calls.append(("clean_bug_references", {"bugs": bugs}))
        return {"cleaned": {"id": "cleaned"}}

    def record_clear(self, cursor, bugs):  # type: ignore[no-untyped-def]
        calls.append(("clear_dangling_bug_duplicates", {"cursor": cursor, "bugs": bugs}))

    def record_upsert(self, cursor, bugs):  # type: ignore[no-untyped-def]
        calls.append(("upsert_bugs", {"cursor": cursor, "bugs": bugs}))

    monkeypatch.setattr(BugReadRepository, "save_bugs", record_save("save_bugs"))
    monkeypatch.setattr(BugReadRepository, "save_bug_record", record_save("save_bug_record"))
    monkeypatch.setattr(
        BugReadRepository,
        "delete_bug_record",
        record_save("delete_bug_record"),
    )
    monkeypatch.setattr(BugReadRepository, "clean_bug_references", record_clean)
    monkeypatch.setattr(BugReadRepository, "clear_dangling_bug_duplicates", record_clear)
    monkeypatch.setattr(BugReadRepository, "upsert_bugs", record_upsert)

    payload = {"bugs": {"bug_001": {"id": "bug_001"}}}
    bug = {"id": "bug_001", "title": "缺陷"}
    audit_event = {"id": "audit_001", "event_type": "bug.updated"}
    cursor = object()

    repository.save_bugs(payload)
    repository.save_bug_record(bug, audit_event=audit_event)
    repository.delete_bug_record("bug_001", audit_event=audit_event)
    assert repository._clean_bug_references({"bug_001": bug}) == {"cleaned": {"id": "cleaned"}}
    repository._clear_dangling_bug_duplicates(cursor, {"bug_001": bug})
    repository._upsert_bugs(cursor, {"bug_001": bug})

    assert calls == [
        ("save_bugs", {"args": (payload,), "kwargs": {}}),
        ("save_bug_record", {"args": (bug,), "kwargs": {"audit_event": audit_event}}),
        ("delete_bug_record", {"args": ("bug_001",), "kwargs": {"audit_event": audit_event}}),
        ("clean_bug_references", {"bugs": {"bug_001": bug}}),
        ("clear_dangling_bug_duplicates", {"cursor": cursor, "bugs": {"bug_001": bug}}),
        ("upsert_bugs", {"cursor": cursor, "bugs": {"bug_001": bug}}),
    ]


def test_bug_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    upsert_calls: list[dict] = []
    audit_calls: list[list[dict]] = []
    executed_sql: list[str] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql: str, params=None):  # type: ignore[no-untyped-def]
            executed_sql.append(sql)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def record_upsert(self, cursor, bugs):  # type: ignore[no-untyped-def]
        upsert_calls.append(bugs)

    monkeypatch.setattr(BugReadRepository, "upsert_bugs", record_upsert)

    repository = BugReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    bug = {"id": "bug_atomic", "title": "事务缺陷"}
    audit_event = {"id": "audit_bug_atomic", "event_type": "bug.updated"}

    repository.save_bug_record(bug, audit_event=audit_event)
    repository.delete_bug_record("bug_atomic", audit_event=audit_event)

    assert connect_calls == [{"autocommit": False}, {"autocommit": False}]
    assert upsert_calls == [{"bug_atomic": bug}]
    assert audit_calls == [[audit_event], [audit_event]]
    assert any("DELETE FROM bugs" in sql for sql in executed_sql)


def test_postgres_user_insight_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result=None):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result or {"items": [{"source": name}], "total": 1}

        return _call

    def record_get_user_feedback(self, feedback_id):  # type: ignore[no-untyped-def]
        calls.append(("get_user_feedback", {"feedback_id": feedback_id}))
        return {"id": feedback_id, "source": "get_user_feedback"}

    monkeypatch.setattr(
        UserInsightReadRepository,
        "load_user_feedback",
        record_call("load_user_feedback", {"user_feedback": {}}),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "list_user_feedback",
        record_call("list_user_feedback", [{"source": "list_user_feedback"}]),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "get_user_feedback",
        record_get_user_feedback,
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "load_user_usage_metrics",
        record_call("load_user_usage_metrics", {"user_usage_metrics": {}}),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "list_user_usage_metrics",
        record_call("list_user_usage_metrics", [{"source": "list_user_usage_metrics"}]),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "load_iteration_planning",
        record_call(
            "load_iteration_planning",
            {"iteration_plan_decisions": {}, "iteration_plan_suggestions": {}},
        ),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "list_iteration_plan_suggestions",
        record_call(
            "list_iteration_plan_suggestions",
            [{"source": "list_iteration_plan_suggestions"}],
        ),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "list_user_insight_items",
        record_call("list_user_insight_items"),
    )

    assert repository.load_user_feedback() == {"user_feedback": {}}
    assert repository.list_user_feedback(
        created_by="user_admin",
        feature_code="search",
        module_code="knowledge",
        product_id="product_001",
        status="resolved",
    )[0]["source"] == "list_user_feedback"
    assert repository.get_user_feedback("feedback_001") == {
        "id": "feedback_001",
        "source": "get_user_feedback",
    }
    assert repository.load_user_usage_metrics() == {"user_usage_metrics": {}}
    assert repository.list_user_usage_metrics(
        feature_code="search",
        from_value="2026-06-01T00:00:00+00:00",
        module_code="knowledge",
        product_id="product_001",
        to_value="2026-06-06T00:00:00+00:00",
        user_segment="enterprise",
    )[0]["source"] == "list_user_usage_metrics"
    assert repository.load_iteration_planning() == {
        "iteration_plan_decisions": {},
        "iteration_plan_suggestions": {},
    }
    assert repository.list_iteration_plan_suggestions(
        planning_cycle="2026-06",
        product_id="product_001",
        status="adopted",
    )[0]["source"] == "list_iteration_plan_suggestions"
    result = repository.list_user_insight_items(
        category="用户反馈",
        page=2,
        page_size=20,
        product_id="product_001",
        sort_by="updated_at",
        sort_order="desc",
        status="resolved",
        summary="layout",
    )

    assert result["items"][0]["source"] == "list_user_insight_items"
    assert calls == [
        ("load_user_feedback", {}),
        (
            "list_user_feedback",
                {
                    "created_by": "user_admin",
                    "feature_code": "search",
                    "limit": None,
                    "module_code": "knowledge",
                    "offset": None,
                    "product_id": "product_001",
                    "status": "resolved",
                    "summary_only": False,
                },
            ),
        ("get_user_feedback", {"feedback_id": "feedback_001"}),
        ("load_user_usage_metrics", {}),
        (
            "list_user_usage_metrics",
            {
                "feature_code": "search",
                "from_value": "2026-06-01T00:00:00+00:00",
                "module_code": "knowledge",
                "product_id": "product_001",
                "to_value": "2026-06-06T00:00:00+00:00",
                "user_segment": "enterprise",
            },
        ),
        ("load_iteration_planning", {}),
        (
            "list_iteration_plan_suggestions",
            {
                "planning_cycle": "2026-06",
                "product_id": "product_001",
                "status": "adopted",
            },
        ),
        (
            "list_user_insight_items",
            {
                "category": "用户反馈",
                "page": 2,
                "page_size": 20,
                "product_id": "product_001",
                "sort_by": "updated_at",
                "sort_order": "desc",
                "status": "resolved",
                "summary": "layout",
            },
        )
    ]


def test_postgres_user_insight_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"args": args, "kwargs": kwargs}))

        return _call

    def record_upsert(name: str):  # type: ignore[no-untyped-def]
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            calls.append((name, {"cursor": cursor, "items": items}))

        return _call

    monkeypatch.setattr(
        UserInsightReadRepository,
        "save_user_feedback",
        record_save("save_user_feedback"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "save_user_feedback_record",
        record_save("save_user_feedback_record"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "save_user_feedback_requirement_conversion",
        record_save("save_user_feedback_requirement_conversion"),
        raising=False,
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "save_user_usage_metrics",
        record_save("save_user_usage_metrics"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "save_user_usage_metric_record",
        record_save("save_user_usage_metric_record"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "save_iteration_planning",
        record_save("save_iteration_planning"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "save_iteration_suggestion_record",
        record_save("save_iteration_suggestion_record"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "save_iteration_decision_records",
        record_save("save_iteration_decision_records"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "upsert_user_feedback",
        record_upsert("upsert_user_feedback"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "upsert_user_usage_metrics",
        record_upsert("upsert_user_usage_metrics"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "upsert_iteration_plan_suggestions",
        record_upsert("upsert_iteration_plan_suggestions"),
    )
    monkeypatch.setattr(
        UserInsightReadRepository,
        "upsert_iteration_plan_decisions",
        record_upsert("upsert_iteration_plan_decisions"),
    )

    feedback_payload = {"user_feedback": {"feedback_001": {"id": "feedback_001"}}}
    feedback = {"id": "feedback_002"}
    usage_payload = {"user_usage_metrics": {"usage_001": {"id": "usage_001"}}}
    usage = {"id": "usage_002"}
    planning_payload = {
        "iteration_plan_decisions": {"decision_001": {"id": "decision_001"}},
        "iteration_plan_suggestions": {"suggestion_001": {"id": "suggestion_001"}},
    }
    suggestion = {"id": "suggestion_002"}
    decision = {"id": "decision_002"}
    requirement = {"id": "requirement_001"}
    audit_event = {"id": "audit_001"}
    audit_events = [{"id": "audit_002"}]
    cursor = object()

    repository.save_user_feedback(feedback_payload)
    repository.save_user_feedback_record(feedback, audit_event=audit_event)
    repository.save_user_feedback_requirement_conversion(
        audit_events=audit_events,
        feedback=feedback,
        requirement=requirement,
    )
    repository.save_user_usage_metrics(usage_payload)
    repository.save_user_usage_metric_record(usage, audit_event=audit_event)
    repository.save_iteration_planning(planning_payload)
    repository.save_iteration_suggestion_record(suggestion, audit_event=audit_event)
    repository.save_iteration_decision_records(
        suggestion=suggestion,
        decision=decision,
        audit_events=audit_events,
        requirement=requirement,
    )
    repository._upsert_user_feedback(cursor, feedback_payload["user_feedback"])
    repository._upsert_user_usage_metrics(cursor, usage_payload["user_usage_metrics"])
    repository._upsert_iteration_plan_suggestions(
        cursor,
        planning_payload["iteration_plan_suggestions"],
    )
    repository._upsert_iteration_plan_decisions(
        cursor,
        planning_payload["iteration_plan_decisions"],
    )

    assert calls == [
        ("save_user_feedback", {"args": (feedback_payload,), "kwargs": {}}),
        (
            "save_user_feedback_record",
            {"args": (feedback,), "kwargs": {"audit_event": audit_event}},
        ),
        (
            "save_user_feedback_requirement_conversion",
            {
                "args": (),
                "kwargs": {
                    "audit_events": audit_events,
                    "feedback": feedback,
                    "requirement": requirement,
                },
            },
        ),
        ("save_user_usage_metrics", {"args": (usage_payload,), "kwargs": {}}),
        (
            "save_user_usage_metric_record",
            {"args": (usage,), "kwargs": {"audit_event": audit_event}},
        ),
        ("save_iteration_planning", {"args": (planning_payload,), "kwargs": {}}),
        (
            "save_iteration_suggestion_record",
            {"args": (suggestion,), "kwargs": {"audit_event": audit_event}},
        ),
        (
            "save_iteration_decision_records",
            {
                "args": (),
                "kwargs": {
                    "audit_events": audit_events,
                    "decision": decision,
                    "requirement": requirement,
                    "suggestion": suggestion,
                },
            },
        ),
        (
            "upsert_user_feedback",
            {"cursor": cursor, "items": feedback_payload["user_feedback"]},
        ),
        (
            "upsert_user_usage_metrics",
            {"cursor": cursor, "items": usage_payload["user_usage_metrics"]},
        ),
        (
            "upsert_iteration_plan_suggestions",
            {"cursor": cursor, "items": planning_payload["iteration_plan_suggestions"]},
        ),
        (
            "upsert_iteration_plan_decisions",
            {"cursor": cursor, "items": planning_payload["iteration_plan_decisions"]},
        ),
    ]


def test_iteration_planning_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    upsert_calls: list[tuple[str, dict]] = []
    audit_calls: list[list[dict]] = []
    requirement_calls: list[dict] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def upsert_requirements(cursor, requirements):  # type: ignore[no-untyped-def]
        requirement_calls.append(requirements)

    def record_upsert(name: str):
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            upsert_calls.append((name, items))

        return _call

    monkeypatch.setattr(
        UserInsightWriteRepository,
        "upsert_iteration_plan_suggestions",
        record_upsert("suggestion"),
    )
    monkeypatch.setattr(
        UserInsightWriteRepository,
        "upsert_iteration_plan_decisions",
        record_upsert("decision"),
    )

    repository = UserInsightWriteRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
        upsert_requirements=upsert_requirements,
    )
    suggestion = {"id": "suggestion_atomic"}
    decision = {"id": "decision_atomic"}
    requirement = {"id": "requirement_atomic"}
    audit_event = {"id": "audit_iteration_atomic"}
    decision_audit_event = {"id": "audit_iteration_decision_atomic"}

    repository.save_iteration_suggestion_record(
        suggestion,
        audit_event=audit_event,
    )
    repository.save_iteration_decision_records(
        suggestion=suggestion,
        decision=decision,
        audit_events=[audit_event, decision_audit_event],
        requirement=requirement,
    )

    assert connect_calls == [{"autocommit": False}, {"autocommit": False}]
    assert upsert_calls == [
        ("suggestion", {"suggestion_atomic": suggestion}),
        ("suggestion", {"suggestion_atomic": suggestion}),
        ("decision", {"decision_atomic": decision}),
    ]
    assert requirement_calls == [{"requirement_atomic": requirement}]
    assert audit_calls == [[audit_event], [audit_event, decision_audit_event]]


def test_postgres_devops_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result=None):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result or {"items": [{"source": name}], "total": 1}

        return _call

    monkeypatch.setattr(
        DevopsReadRepository,
        "load_gitlab_daily_code_metrics",
        record_call(
            "load_gitlab_daily_code_metrics",
            {"gitlab_daily_code_metrics": {}},
        ),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "list_gitlab_daily_code_metrics",
        record_call("list_gitlab_daily_code_metrics", [{"source": "list_gitlab"}]),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "load_jenkins_release_records",
        record_call("load_jenkins_release_records", {"jenkins_release_records": {}}),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "list_jenkins_release_records",
        record_call("list_jenkins_release_records", [{"source": "list_jenkins"}]),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "load_online_log_metrics",
        record_call("load_online_log_metrics", {"online_log_metrics": {}}),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "list_online_log_metrics",
        record_call("list_online_log_metrics", [{"source": "list_online_logs"}]),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "list_operational_metric_items",
        record_call("list_operational_metric_items"),
    )

    assert repository.load_gitlab_daily_code_metrics() == {"gitlab_daily_code_metrics": {}}
    assert repository.list_gitlab_daily_code_metrics(
        metric_date="2026-06-06",
        product_id="product_001",
        repository_id="repo_001",
    )[0]["source"] == "list_gitlab"
    assert repository.load_jenkins_release_records() == {"jenkins_release_records": {}}
    assert repository.list_jenkins_release_records(
        environment="prod",
        product_id="product_001",
        status="success",
        version_id="version_001",
    )[0]["source"] == "list_jenkins"
    assert repository.load_online_log_metrics() == {"online_log_metrics": {}}
    assert repository.list_online_log_metrics(
        environment="prod",
        module_code="core",
        product_id="product_001",
    )[0]["source"] == "list_online_logs"
    result = repository.list_operational_metric_items(
        category="GitLab 指标",
        exclude_category="运维部署",
        name="repo-api",
        page=3,
        page_size=15,
        sort_by="updated_at",
        sort_order="desc",
        status="collected",
    )

    assert result["items"][0]["source"] == "list_operational_metric_items"
    assert calls == [
        ("load_gitlab_daily_code_metrics", {}),
        (
            "list_gitlab_daily_code_metrics",
            {
                "metric_date": "2026-06-06",
                "product_id": "product_001",
                "repository_id": "repo_001",
            },
        ),
        ("load_jenkins_release_records", {}),
        (
            "list_jenkins_release_records",
            {
                "environment": "prod",
                "product_id": "product_001",
                "status": "success",
                "version_id": "version_001",
            },
        ),
        ("load_online_log_metrics", {}),
        (
            "list_online_log_metrics",
            {
                "environment": "prod",
                "from_value": None,
                "module_code": "core",
                "product_id": "product_001",
                "to_value": None,
            },
        ),
        (
            "list_operational_metric_items",
            {
                "category": "GitLab 指标",
                "exclude_category": "运维部署",
                "name": "repo-api",
                "page": 3,
                "page_size": 15,
                "product_scope_ids": None,
                "sort_by": "updated_at",
                "sort_order": "desc",
                "status": "collected",
            },
        )
    ]


def test_postgres_devops_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"args": args, "kwargs": kwargs}))

        return _call

    def record_upsert(name: str):  # type: ignore[no-untyped-def]
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            calls.append((name, {"cursor": cursor, "items": items}))

        return _call

    monkeypatch.setattr(
        DevopsReadRepository,
        "save_gitlab_daily_code_metrics",
        record_save("save_gitlab_daily_code_metrics"),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "save_gitlab_daily_code_metric_record",
        record_save("save_gitlab_daily_code_metric_record"),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "save_jenkins_release_records",
        record_save("save_jenkins_release_records"),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "save_jenkins_release_record",
        record_save("save_jenkins_release_record"),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "save_online_log_metrics",
        record_save("save_online_log_metrics"),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "save_online_log_metric_record",
        record_save("save_online_log_metric_record"),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "upsert_gitlab_daily_code_metrics",
        record_upsert("upsert_gitlab_daily_code_metrics"),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "upsert_jenkins_release_records",
        record_upsert("upsert_jenkins_release_records"),
    )
    monkeypatch.setattr(
        DevopsReadRepository,
        "upsert_online_log_metrics",
        record_upsert("upsert_online_log_metrics"),
    )

    gitlab_payload = {"gitlab_daily_code_metrics": {"gitlab_001": {"id": "gitlab_001"}}}
    gitlab_record = {"id": "gitlab_002"}
    jenkins_payload = {"jenkins_release_records": {"release_001": {"id": "release_001"}}}
    jenkins_record = {"id": "release_002"}
    online_payload = {"online_log_metrics": {"online_001": {"id": "online_001"}}}
    online_record = {"id": "online_002"}
    audit_event = {"id": "audit_001"}
    cursor = object()

    repository.save_gitlab_daily_code_metrics(gitlab_payload)
    repository.save_gitlab_daily_code_metric_record(gitlab_record, audit_event=audit_event)
    repository.save_jenkins_release_records(jenkins_payload)
    repository.save_jenkins_release_record(jenkins_record, audit_event=audit_event)
    repository.save_online_log_metrics(online_payload)
    repository.save_online_log_metric_record(online_record, audit_event=audit_event)
    repository._upsert_gitlab_daily_code_metrics(
        cursor,
        gitlab_payload["gitlab_daily_code_metrics"],
    )
    repository._upsert_jenkins_release_records(cursor, jenkins_payload["jenkins_release_records"])
    repository._upsert_online_log_metrics(cursor, online_payload["online_log_metrics"])

    assert calls == [
        ("save_gitlab_daily_code_metrics", {"args": (gitlab_payload,), "kwargs": {}}),
        (
            "save_gitlab_daily_code_metric_record",
            {"args": (gitlab_record,), "kwargs": {"audit_event": audit_event}},
        ),
        ("save_jenkins_release_records", {"args": (jenkins_payload,), "kwargs": {}}),
        (
            "save_jenkins_release_record",
            {"args": (jenkins_record,), "kwargs": {"audit_event": audit_event}},
        ),
        ("save_online_log_metrics", {"args": (online_payload,), "kwargs": {}}),
        (
            "save_online_log_metric_record",
            {"args": (online_record,), "kwargs": {"audit_event": audit_event}},
        ),
        (
            "upsert_gitlab_daily_code_metrics",
            {"cursor": cursor, "items": gitlab_payload["gitlab_daily_code_metrics"]},
        ),
        (
            "upsert_jenkins_release_records",
            {"cursor": cursor, "items": jenkins_payload["jenkins_release_records"]},
        ),
        (
            "upsert_online_log_metrics",
            {"cursor": cursor, "items": online_payload["online_log_metrics"]},
        ),
    ]


def test_postgres_knowledge_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        KnowledgeReadRepository,
        "load_knowledge",
        record_call(
            "load_knowledge",
            {
                "knowledge_assets": {},
                "knowledge_chunk_sets": {},
                "knowledge_chunks": {},
                "knowledge_deposits": {},
                "knowledge_documents": {},
                "knowledge_folders": {},
                "knowledge_import_jobs": {},
                "knowledge_space_members": {},
                "knowledge_spaces": {},
            },
        ),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "list_knowledge_documents",
        record_call("list_knowledge_documents", [{"source": "list_knowledge_documents"}]),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "list_knowledge_deposits",
        record_call("list_knowledge_deposits", [{"source": "list_knowledge_deposits"}]),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "count_knowledge_deposits",
        record_call("count_knowledge_deposits", 5),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "list_knowledge_deposits_page",
        record_call(
            "list_knowledge_deposits_page",
            [{"source": "list_knowledge_deposits_page"}],
        ),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "get_knowledge_deposit",
        record_call("get_knowledge_deposit", {"source": "get_knowledge_deposit"}),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "has_readable_vector_chunks",
        record_call("has_readable_vector_chunks", True),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "search_knowledge_chunks",
        record_call("search_knowledge_chunks", [{"source": "search_knowledge_chunks"}]),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "claim_knowledge_import_job",
        record_call("claim_knowledge_import_job", True),
    )

    assert repository.load_knowledge() == {
        "knowledge_assets": {},
        "knowledge_chunk_sets": {},
        "knowledge_chunks": {},
        "knowledge_deposits": {},
        "knowledge_documents": {},
        "knowledge_folders": {},
        "knowledge_import_jobs": {},
        "knowledge_space_members": {},
        "knowledge_spaces": {},
    }
    assert repository.list_knowledge_documents(
        user_roles=["rd_owner"],
        keyword="设计",
        doc_type="prd",
        index_status="indexed",
    )[0]["source"] == "list_knowledge_documents"
    assert repository.list_knowledge_deposits(status="pending")[0]["source"] == (
        "list_knowledge_deposits"
    )
    assert repository.count_knowledge_deposits(status="pending") == 5
    assert repository.list_knowledge_deposits_page(
        limit=10,
        offset=20,
        sort_by="updated_at",
        sort_order="desc",
        status="pending",
    )[0]["source"] == "list_knowledge_deposits_page"
    assert repository.get_knowledge_deposit("deposit_001") == {
        "source": "get_knowledge_deposit"
    }
    assert repository.has_readable_vector_chunks(user_roles=["admin"]) is True
    assert repository.search_knowledge_chunks(
        product_id="product_001",
        user_roles=["product_owner"],
        query="AI Brain",
        version_id="version_001",
    )[0]["source"] == "search_knowledge_chunks"
    assert repository.claim_knowledge_import_job(
        job_id="knowledge_import_job_001",
        worker_id="worker_001",
        lock_ttl_seconds=120,
    ) is True

    assert calls == [
        ("load_knowledge", {}),
        (
            "list_knowledge_documents",
                {
                    "doc_type": "prd",
                    "folder_id": None,
                    "global_knowledge_access": False,
                    "index_status": "indexed",
                    "keyword": "设计",
                    "knowledge_space_id": None,
                    "knowledge_space_scope_ids": None,
                    "user_id": None,
                    "user_roles": ["rd_owner"],
                },
            ),
        ("list_knowledge_deposits", {"status": "pending"}),
        ("count_knowledge_deposits", {"status": "pending"}),
        (
            "list_knowledge_deposits_page",
            {
                "limit": 10,
                "offset": 20,
                "sort_by": "updated_at",
                "sort_order": "desc",
                "status": "pending",
            },
        ),
        ("get_knowledge_deposit", {"deposit_id": "deposit_001"}),
        (
            "has_readable_vector_chunks",
            {
                "global_knowledge_access": False,
                "knowledge_space_id": None,
                "knowledge_space_scope_ids": None,
                "user_id": None,
                "user_roles": ["admin"],
            },
        ),
        (
            "search_knowledge_chunks",
            {
                "global_knowledge_access": False,
                "knowledge_space_id": None,
                "knowledge_space_scope_ids": None,
                "product_id": "product_001",
                "query": "AI Brain",
                "user_id": None,
                "user_roles": ["product_owner"],
                "version_id": "version_001",
            },
        ),
        (
            "claim_knowledge_import_job",
            {
                "job_id": "knowledge_import_job_001",
                "lock_ttl_seconds": 120,
                "worker_id": "worker_001",
            },
        ),
    ]


def test_postgres_knowledge_document_page_read_model_delegates_to_domain_repository(
    monkeypatch,
):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        KnowledgeReadRepository,
        "count_knowledge_document_summaries",
        record_call("count_knowledge_document_summaries", 9),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "list_knowledge_document_summaries_page",
        record_call(
            "list_knowledge_document_summaries_page",
            [{"source": "list_knowledge_document_summaries_page"}],
        ),
    )

    assert repository.count_knowledge_document_summaries(
        user_roles=["knowledge_owner"],
        user_id="user_knowledge",
        global_knowledge_access=False,
        knowledge_space_scope_ids=["space_001"],
        keyword="规范",
        doc_type="runbook",
        folder_id="folder_001",
        index_status="text_indexed",
        knowledge_space_id="space_001",
        permission_role="knowledge_owner",
    ) == 9
    assert repository.list_knowledge_document_summaries_page(
        user_roles=["knowledge_owner"],
        user_id="user_knowledge",
        global_knowledge_access=False,
        knowledge_space_scope_ids=["space_001"],
        keyword="规范",
        doc_type="runbook",
        folder_id="folder_001",
        index_status="text_indexed",
        knowledge_space_id="space_001",
        permission_role="knowledge_owner",
        limit=20,
        offset=40,
        sort_by="updated_at",
        sort_order="desc",
    )[0]["source"] == "list_knowledge_document_summaries_page"

    expected_filters = {
        "doc_type": "runbook",
        "folder_id": "folder_001",
        "global_knowledge_access": False,
        "index_status": "text_indexed",
        "keyword": "规范",
        "knowledge_space_id": "space_001",
        "knowledge_space_scope_ids": ["space_001"],
        "permission_role": "knowledge_owner",
        "user_id": "user_knowledge",
        "user_roles": ["knowledge_owner"],
    }
    assert calls == [
        ("count_knowledge_document_summaries", expected_filters),
        (
            "list_knowledge_document_summaries_page",
            {
                **expected_filters,
                "limit": 20,
                "offset": 40,
                "sort_by": "updated_at",
                "sort_order": "desc",
            },
        ),
    ]


def test_postgres_knowledge_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"args": args, "kwargs": kwargs}))

        return _call

    def record_clean(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, documents, items):  # type: ignore[no-untyped-def]
            calls.append((name, {"documents": documents, "items": items}))
            return result

        return _call

    def record_clear(name: str):  # type: ignore[no-untyped-def]
        def _call(self, cursor, documents):  # type: ignore[no-untyped-def]
            calls.append((name, {"cursor": cursor, "documents": documents}))

        return _call

    def record_upsert(name: str):  # type: ignore[no-untyped-def]
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            calls.append((name, {"cursor": cursor, "items": items}))

        return _call

    monkeypatch.setattr(KnowledgeReadRepository, "save_knowledge", record_save("save_knowledge"))
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "save_knowledge_document_records",
        record_save("save_knowledge_document_records"),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "delete_knowledge_document_records",
        record_save("delete_knowledge_document_records"),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "save_knowledge_deposit_records",
        record_save("save_knowledge_deposit_records"),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "clean_knowledge_deposit_references",
        record_clean("clean_knowledge_deposit_references", {"deposit": {"id": "deposit"}}),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "clean_knowledge_chunk_references",
        record_clean("clean_knowledge_chunk_references", {"chunk": {"id": "chunk"}}),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "clear_dangling_knowledge_chunk_documents",
        record_clear("clear_dangling_knowledge_chunk_documents"),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "clear_dangling_knowledge_deposit_documents",
        record_clear("clear_dangling_knowledge_deposit_documents"),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "upsert_knowledge_documents",
        record_upsert("upsert_knowledge_documents"),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "upsert_knowledge_chunks",
        record_upsert("upsert_knowledge_chunks"),
    )
    monkeypatch.setattr(
        KnowledgeReadRepository,
        "upsert_knowledge_deposits",
        record_upsert("upsert_knowledge_deposits"),
    )

    payload = {"knowledge_documents": {"doc_001": {"id": "doc_001"}}}
    document = {"id": "doc_001", "title": "知识"}
    chunk = {"id": "chunk_001", "document_id": "doc_001"}
    deposit = {"id": "deposit_001", "ai_task_id": "task_001"}
    audit_event = {"id": "audit_001", "event_type": "knowledge.updated"}
    model_logs = [{"id": "model_log_001"}]
    cursor = object()

    repository.save_knowledge(payload)
    repository.save_knowledge_document_records(
        document=document,
        chunks=[chunk],
        audit_event=audit_event,
        model_logs=model_logs,
    )
    repository.delete_knowledge_document_records(
        document_id="doc_001",
        deposits=[deposit],
        audit_event=audit_event,
    )
    repository.save_knowledge_deposit_records(
        deposit=deposit,
        audit_event=audit_event,
        document=document,
        chunks=[chunk],
        model_logs=model_logs,
    )
    assert repository._clean_knowledge_deposit_references(
        {"doc_001": document},
        {"d": deposit},
    ) == {"deposit": {"id": "deposit"}}
    assert repository._clean_knowledge_chunk_references({"doc_001": document}, {"c": chunk}) == {
        "chunk": {"id": "chunk"}
    }
    repository._clear_dangling_knowledge_chunk_documents(cursor, {"doc_001": document})
    repository._clear_dangling_knowledge_deposit_documents(cursor, {"doc_001": document})
    repository._upsert_knowledge_documents(cursor, {"doc_001": document})
    repository._upsert_knowledge_chunks(cursor, {"chunk_001": chunk})
    repository._upsert_knowledge_deposits(cursor, {"deposit_001": deposit})

    assert calls == [
        ("save_knowledge", {"args": (payload,), "kwargs": {}}),
        (
            "save_knowledge_document_records",
            {
                "args": (),
                "kwargs": {
                    "audit_event": audit_event,
                    "chunks": [chunk],
                    "document": document,
                    "model_logs": model_logs,
                },
            },
        ),
        (
            "delete_knowledge_document_records",
            {
                "args": (),
                "kwargs": {
                    "audit_event": audit_event,
                    "deposits": [deposit],
                    "document_id": "doc_001",
                },
            },
        ),
        (
            "save_knowledge_deposit_records",
            {
                "args": (),
                "kwargs": {
                    "audit_event": audit_event,
                    "chunks": [chunk],
                    "deposit": deposit,
                    "document": document,
                    "model_logs": model_logs,
                },
            },
        ),
        (
            "clean_knowledge_deposit_references",
            {"documents": {"doc_001": document}, "items": {"d": deposit}},
        ),
        (
            "clean_knowledge_chunk_references",
            {"documents": {"doc_001": document}, "items": {"c": chunk}},
        ),
        (
            "clear_dangling_knowledge_chunk_documents",
            {"cursor": cursor, "documents": {"doc_001": document}},
        ),
        (
            "clear_dangling_knowledge_deposit_documents",
            {"cursor": cursor, "documents": {"doc_001": document}},
        ),
        ("upsert_knowledge_documents", {"cursor": cursor, "items": {"doc_001": document}}),
        ("upsert_knowledge_chunks", {"cursor": cursor, "items": {"chunk_001": chunk}}),
        ("upsert_knowledge_deposits", {"cursor": cursor, "items": {"deposit_001": deposit}}),
    ]


def test_knowledge_deposit_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    upsert_calls: list[tuple[str, dict]] = []
    audit_calls: list[list[dict]] = []
    model_log_calls: list[list[dict]] = []
    executed_sql: list[tuple[str, tuple]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params=()):  # type: ignore[no-untyped-def]
            executed_sql.append((" ".join(str(sql).split()), tuple(params)))

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def record_upsert(name: str):
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            upsert_calls.append((name, items))

        return _call

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def upsert_model_gateway_logs(cursor, model_logs):  # type: ignore[no-untyped-def]
        model_log_calls.append(model_logs)

    monkeypatch.setattr(
        KnowledgeWriteRepository,
        "upsert_knowledge_documents",
        record_upsert("document"),
    )
    monkeypatch.setattr(
        KnowledgeWriteRepository,
        "upsert_knowledge_chunks",
        record_upsert("chunk"),
    )
    monkeypatch.setattr(
        KnowledgeWriteRepository,
        "upsert_knowledge_deposits",
        record_upsert("deposit"),
    )

    repository = KnowledgeWriteRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
        upsert_model_gateway_logs=upsert_model_gateway_logs,
    )
    document = {"id": "knowledge_atomic"}
    chunk = {"id": "knowledge_atomic_chunk_001", "document_id": "knowledge_atomic"}
    deposit = {"id": "deposit_atomic"}
    audit_event = {"id": "audit_atomic"}
    model_log = {"id": "model_log_atomic"}

    repository.save_knowledge_deposit_records(
        deposit=deposit,
        audit_event=audit_event,
        document=document,
        chunks=[chunk],
        model_logs=[model_log],
    )

    assert connect_calls == [{"autocommit": False}]
    assert executed_sql == [
        ("DELETE FROM knowledge_chunks WHERE document_id = %s", ("knowledge_atomic",))
    ]
    assert upsert_calls == [
        ("document", {"knowledge_atomic": document}),
        ("chunk", {"knowledge_atomic_chunk_001": chunk}),
        ("deposit", {"deposit_atomic": deposit}),
    ]
    assert model_log_calls == [[model_log]]
    assert audit_calls == [[audit_event]]


def test_postgres_assistant_chat_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        AssistantChatReadRepository,
        "load_assistant_chat",
        record_call(
            "load_assistant_chat",
            {
                "assistant_action_drafts": {},
                "assistant_action_runs": {},
                "assistant_chat_runs": {},
                "assistant_conversations": {},
                "assistant_messages": {},
            },
        ),
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "list_assistant_chat_runs",
        record_call("list_assistant_chat_runs", [{"source": "list_assistant_chat_runs"}]),
        raising=False,
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "get_assistant_chat_run",
        record_call("get_assistant_chat_run", {"source": "get_assistant_chat_run"}),
        raising=False,
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "list_assistant_conversations",
        record_call("list_assistant_conversations", [{"source": "list_assistant_conversations"}]),
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "list_assistant_conversation_messages",
        record_call(
            "list_assistant_conversation_messages",
            [{"source": "list_assistant_conversation_messages"}],
        ),
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "list_assistant_action_drafts",
        record_call("list_assistant_action_drafts", [{"source": "list_assistant_action_drafts"}]),
        raising=False,
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "list_assistant_action_draft_workbench_page",
        record_call(
            "list_assistant_action_draft_workbench_page",
            {"source": "list_assistant_action_draft_workbench_page"},
        ),
        raising=False,
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "get_assistant_action_draft",
        record_call("get_assistant_action_draft", {"source": "get_assistant_action_draft"}),
        raising=False,
    )

    assert repository.load_assistant_chat() == {
        "assistant_action_drafts": {},
        "assistant_action_runs": {},
        "assistant_chat_runs": {},
        "assistant_conversations": {},
        "assistant_messages": {},
    }
    assert repository.list_assistant_chat_runs(user_id="user_admin")[0]["source"] == (
        "list_assistant_chat_runs"
    )
    assert repository.get_assistant_chat_run(run_id="assistant_chat_run_001") == {
        "source": "get_assistant_chat_run"
    }
    assert repository.list_assistant_conversations(user_id="user_admin")[0]["source"] == (
        "list_assistant_conversations"
    )
    assert repository.list_assistant_conversation_messages(
        conversation_id="conversation_001",
        user_id="user_admin",
    )[0]["source"] == "list_assistant_conversation_messages"
    assert repository.list_assistant_action_drafts(user_id="user_admin")[0]["source"] == (
        "list_assistant_action_drafts"
    )
    assert repository.list_assistant_action_draft_workbench_page(
        action="create_analysis_draft",
        created_from=None,
        created_to=None,
        keyword="草案",
        limit=10,
        offset=0,
        sort_by="updated_at",
        sort_order="desc",
        status="pending",
        user_id="user_admin",
        validation_status="passed",
    ) == {"source": "list_assistant_action_draft_workbench_page"}
    assert repository.get_assistant_action_draft(draft_id="assistant_action_draft_001") == {
        "source": "get_assistant_action_draft"
    }

    assert calls == [
        ("load_assistant_chat", {}),
        ("list_assistant_chat_runs", {"user_id": "user_admin"}),
        ("get_assistant_chat_run", {"run_id": "assistant_chat_run_001"}),
        ("list_assistant_conversations", {"cursor": None, "limit": None, "user_id": "user_admin"}),
        (
            "list_assistant_conversation_messages",
            {"conversation_id": "conversation_001", "user_id": "user_admin"},
        ),
        ("list_assistant_action_drafts", {"user_id": "user_admin"}),
        (
            "list_assistant_action_draft_workbench_page",
            {
                "action": "create_analysis_draft",
                "created_from": None,
                "created_to": None,
                "keyword": "草案",
                "limit": 10,
                "offset": 0,
                "sort_by": "updated_at",
                "sort_order": "desc",
                "status": "pending",
                "user_id": "user_admin",
                "validation_status": "passed",
            },
        ),
        ("get_assistant_action_draft", {"draft_id": "assistant_action_draft_001"}),
    ]


def test_postgres_assistant_chat_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            payload = args[0] if args else None
            call = dict(kwargs)
            if payload is not None:
                call["payload"] = payload
            calls.append((name, call))

        return _call

    def record_conversation_upsert(self, cursor, conversations):  # type: ignore[no-untyped-def]
        calls.append(
            (
                "upsert_assistant_conversations",
                {"cursor": cursor, "conversations": conversations},
            )
        )

    def record_message_upsert(self, cursor, messages):  # type: ignore[no-untyped-def]
        calls.append(("upsert_assistant_messages", {"cursor": cursor, "messages": messages}))

    def record_chat_run_upsert(self, cursor, runs):  # type: ignore[no-untyped-def]
        calls.append(("upsert_assistant_chat_runs", {"cursor": cursor, "runs": runs}))

    monkeypatch.setattr(
        AssistantChatReadRepository,
        "save_assistant_chat",
        record_save("save_assistant_chat"),
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "save_assistant_chat_records",
        record_save("save_assistant_chat_records"),
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "save_assistant_action_records",
        record_save("save_assistant_action_records"),
        raising=False,
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "delete_assistant_conversations",
        record_save("delete_assistant_conversations"),
        raising=False,
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "upsert_assistant_conversations",
        record_conversation_upsert,
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "upsert_assistant_messages",
        record_message_upsert,
    )
    monkeypatch.setattr(
        AssistantChatReadRepository,
        "upsert_assistant_chat_runs",
        record_chat_run_upsert,
    )

    payload = {
        "assistant_chat_runs": {"assistant_chat_run_001": {"id": "assistant_chat_run_001"}},
        "assistant_conversations": {"conversation_001": {"id": "conversation_001"}},
        "assistant_messages": {"message_001": {"id": "message_001"}},
    }
    chat_run = {"id": "assistant_chat_run_002"}
    conversation = {"id": "conversation_002"}
    messages = [{"id": "message_002"}]
    draft = {"id": "assistant_action_draft_001"}
    run = {"id": "assistant_action_run_001"}
    audit_events = [{"id": "audit_001"}]
    model_log = {"id": "model_log_001"}
    cursor = object()

    repository.save_assistant_chat(payload)
    repository.save_assistant_chat_records(
        chat_run=chat_run,
        conversation=conversation,
        messages=messages,
        audit_events=audit_events,
        model_log=model_log,
    )
    repository.save_assistant_action_records(
        draft=draft,
        run=run,
        audit_events=audit_events,
    )
    repository.delete_assistant_conversations(
        audit_event=audit_events[0],
        conversation_ids=["conversation_001"],
        user_id="user_admin",
    )
    repository._upsert_assistant_conversations(cursor, payload["assistant_conversations"])
    repository._upsert_assistant_messages(cursor, payload["assistant_messages"])
    repository._upsert_assistant_chat_runs(cursor, payload["assistant_chat_runs"])

    assert calls == [
        ("save_assistant_chat", {"payload": payload}),
        (
            "save_assistant_chat_records",
            {
                "conversation": conversation,
                "chat_run": chat_run,
                "messages": messages,
                "audit_events": audit_events,
                "model_log": model_log,
            },
        ),
        (
            "save_assistant_action_records",
            {"draft": draft, "run": run, "audit_events": audit_events},
        ),
        (
            "delete_assistant_conversations",
            {
                "audit_event": audit_events[0],
                "conversation_ids": ["conversation_001"],
                "user_id": "user_admin",
            },
        ),
        (
            "upsert_assistant_conversations",
            {"cursor": cursor, "conversations": payload["assistant_conversations"]},
        ),
        (
            "upsert_assistant_messages",
            {"cursor": cursor, "messages": payload["assistant_messages"]},
        ),
        (
            "upsert_assistant_chat_runs",
            {"cursor": cursor, "runs": payload["assistant_chat_runs"]},
        ),
    ]


def test_postgres_model_gateway_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "load_model_gateway",
        record_call(
            "load_model_gateway",
            {"model_gateway_configs": {}, "model_gateway_logs": []},
        ),
    )
    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "list_model_gateway_configs",
        record_call("list_model_gateway_configs", [{"source": "list_model_gateway_configs"}]),
    )
    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "get_model_gateway_config",
        lambda self, config_id: calls.append(
            ("get_model_gateway_config", {"config_id": config_id})
        )
        or {"source": "get_model_gateway_config"},
    )
    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "list_model_gateway_logs",
        record_call("list_model_gateway_logs", [{"source": "list_model_gateway_logs"}]),
    )

    assert repository.load_model_gateway() == {
        "model_gateway_configs": {},
        "model_gateway_logs": [],
    }
    assert repository.list_model_gateway_configs()[0]["source"] == "list_model_gateway_configs"
    assert repository.get_model_gateway_config("model_gateway_config_001")["source"] == (
        "get_model_gateway_config"
    )
    assert repository.list_model_gateway_logs(
        ai_task_id="task_001",
        purpose="chat",
        status="success",
    )[0]["source"] == "list_model_gateway_logs"

    assert calls == [
        ("load_model_gateway", {}),
        ("list_model_gateway_configs", {}),
        ("get_model_gateway_config", {"config_id": "model_gateway_config_001"}),
        (
            "list_model_gateway_logs",
            {"ai_task_id": "task_001", "purpose": "chat", "status": "success"},
        ),
    ]


def test_postgres_model_gateway_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, payload, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"payload": payload, **kwargs}))

        return _call

    def record_log_upsert(self, cursor, logs):  # type: ignore[no-untyped-def]
        calls.append(("upsert_model_gateway_logs", {"cursor": cursor, "logs": logs}))

    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "save_model_gateway",
        record_save("save_model_gateway"),
    )
    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "save_model_gateway_records",
        record_save("save_model_gateway_records"),
    )
    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "upsert_model_gateway_config_record",
        lambda self, config, **kwargs: calls.append(
            ("upsert_model_gateway_config_record", {"config": config, **kwargs})
        ),
    )
    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "delete_model_gateway_config_record",
        lambda self, config_id, **kwargs: calls.append(
            ("delete_model_gateway_config_record", {"config_id": config_id, **kwargs})
        ),
    )
    monkeypatch.setattr(
        ModelGatewayReadRepository,
        "upsert_model_gateway_logs",
        record_log_upsert,
    )

    payload = {
        "model_gateway_configs": {"model_gateway_config_001": {"id": "model_gateway_config_001"}},
        "model_gateway_logs": [{"id": "model_log_001"}],
    }
    audit_event = {"id": "audit_001", "event_type": "model_gateway.config_created"}
    cursor = object()

    repository.save_model_gateway(payload)
    repository.save_model_gateway_records(payload, audit_event=audit_event)
    repository.upsert_model_gateway_config_record(
        {"id": "model_gateway_config_002"},
        audit_event=audit_event,
    )
    repository.delete_model_gateway_config_record(
        "model_gateway_config_002",
        audit_event=audit_event,
    )
    repository._upsert_model_gateway_logs(cursor, [{"id": "model_log_002"}])

    assert calls == [
        ("save_model_gateway", {"payload": payload}),
        ("save_model_gateway_records", {"payload": payload, "audit_event": audit_event}),
        (
            "upsert_model_gateway_config_record",
            {"config": {"id": "model_gateway_config_002"}, "audit_event": audit_event},
        ),
        (
            "delete_model_gateway_config_record",
            {"config_id": "model_gateway_config_002", "audit_event": audit_event},
        ),
        ("upsert_model_gateway_logs", {"cursor": cursor, "logs": [{"id": "model_log_002"}]}),
    ]


def test_postgres_audit_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        AuditReadRepository,
        "load_audit_events",
        record_call("load_audit_events", {"audit_events": []}),
    )
    monkeypatch.setattr(
        AuditReadRepository,
        "list_audit_events",
        record_call("list_audit_events", [{"source": "list_audit_events"}]),
    )

    assert repository.load_audit_events() == {"audit_events": []}
    assert repository.list_audit_events(
        actor_id="user_admin",
        ai_task_id="task_001",
        subject_type="requirement",
        subject_id="requirement_001",
        event_type="requirement.created",
        created_from="2026-06-01T00:00:00+00:00",
        created_to="2026-06-02T00:00:00+00:00",
    )[0]["source"] == "list_audit_events"

    assert calls == [
        ("load_audit_events", {}),
        (
            "list_audit_events",
            {
                "actor_id": "user_admin",
                "ai_task_id": "task_001",
                "created_from": "2026-06-01T00:00:00+00:00",
                "created_to": "2026-06-02T00:00:00+00:00",
                "event_type": "requirement.created",
                "subject_id": "requirement_001",
                "subject_type": "requirement",
            },
        ),
    ]


def test_postgres_audit_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, payload_or_event):  # type: ignore[no-untyped-def]
            calls.append((name, {"value": payload_or_event}))

        return _call

    def record_upsert(self, cursor, audit_events):  # type: ignore[no-untyped-def]
        calls.append((("upsert_audit_events"), {"cursor": cursor, "audit_events": audit_events}))

    monkeypatch.setattr(
        AuditReadRepository,
        "save_audit_events",
        record_save("save_audit_events"),
    )
    monkeypatch.setattr(
        AuditReadRepository,
        "append_audit_event",
        record_save("append_audit_event"),
    )
    monkeypatch.setattr(AuditReadRepository, "upsert_audit_events", record_upsert)

    payload = {"audit_events": [{"id": "audit_001", "event_type": "requirement.created"}]}
    audit_event = {"id": "audit_002", "event_type": "requirement.updated"}
    cursor = object()

    repository.save_audit_events(payload)
    repository.append_audit_event(audit_event)
    repository._upsert_audit_events(cursor, [audit_event])

    assert calls == [
        ("save_audit_events", {"value": payload}),
        ("append_audit_event", {"value": audit_event}),
        ("upsert_audit_events", {"cursor": cursor, "audit_events": [audit_event]}),
    ]


def test_postgres_operational_collection_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "load_collector_runs",
        record_call("load_collector_runs", {"collector_runs": {}}),
    )
    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "list_collector_runs",
        record_call("list_collector_runs", [{"source": "list_collector_runs"}]),
    )
    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "load_pending_attribution",
        record_call("load_pending_attribution", {"pending_attribution_items": {}}),
    )
    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "list_pending_attribution_items",
        record_call(
            "list_pending_attribution_items",
            [{"source": "list_pending_attribution_items"}],
        ),
    )

    assert repository.load_collector_runs() == {"collector_runs": {}}
    assert repository.list_collector_runs(
        collector_type="gitlab_daily_code_metric",
        product_id="product_001",
        status="succeeded",
        source_system="gitlab",
    )[0]["source"] == "list_collector_runs"
    assert repository.load_pending_attribution() == {"pending_attribution_items": {}}
    assert repository.list_pending_attribution_items(
        source_type="user_feedback",
        status="resolved",
        resolved_product_id="product_001",
        collector_run_id="collector_run_001",
    )[0]["source"] == "list_pending_attribution_items"

    assert calls == [
        ("load_collector_runs", {}),
        (
            "list_collector_runs",
            {
                "collector_type": "gitlab_daily_code_metric",
                "product_id": "product_001",
                "source_system": "gitlab",
                "status": "succeeded",
            },
        ),
        ("load_pending_attribution", {}),
        (
            "list_pending_attribution_items",
            {
                "collector_run_id": "collector_run_001",
                "resolved_product_id": "product_001",
                "source_type": "user_feedback",
                "status": "resolved",
            },
        ),
    ]


def test_postgres_operational_collection_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"args": args, "kwargs": kwargs}))

        return _call

    def record_upsert(name: str):  # type: ignore[no-untyped-def]
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            calls.append((name, {"cursor": cursor, "items": items}))

        return _call

    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "save_collector_runs",
        record_save("save_collector_runs"),
    )
    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "save_collector_run_record",
        record_save("save_collector_run_record"),
    )
    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "save_pending_attribution",
        record_save("save_pending_attribution"),
    )
    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "save_pending_attribution_item_record",
        record_save("save_pending_attribution_item_record"),
    )
    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "upsert_collector_runs",
        record_upsert("upsert_collector_runs"),
    )
    monkeypatch.setattr(
        OperationalCollectionReadRepository,
        "upsert_pending_attribution_items",
        record_upsert("upsert_pending_attribution_items"),
    )

    collector_payload = {"collector_runs": {"collector_001": {"id": "collector_001"}}}
    collector = {"id": "collector_002"}
    attribution_payload = {
        "pending_attribution_items": {"pending_001": {"id": "pending_001"}}
    }
    attribution = {"id": "pending_002"}
    audit_event = {"id": "audit_001"}
    cursor = object()

    repository.save_collector_runs(collector_payload)
    repository.save_collector_run_record(collector, audit_event=audit_event)
    repository.save_pending_attribution(attribution_payload)
    repository.save_pending_attribution_item_record(attribution, audit_event=audit_event)
    repository._upsert_collector_runs(cursor, collector_payload["collector_runs"])
    repository._upsert_pending_attribution_items(
        cursor,
        attribution_payload["pending_attribution_items"],
    )

    assert calls == [
        ("save_collector_runs", {"args": (collector_payload,), "kwargs": {}}),
        (
            "save_collector_run_record",
            {"args": (collector,), "kwargs": {"audit_event": audit_event}},
        ),
        ("save_pending_attribution", {"args": (attribution_payload,), "kwargs": {}}),
        (
            "save_pending_attribution_item_record",
            {"args": (attribution,), "kwargs": {"audit_event": audit_event}},
        ),
        (
            "upsert_collector_runs",
            {"cursor": cursor, "items": collector_payload["collector_runs"]},
        ),
        (
            "upsert_pending_attribution_items",
            {"cursor": cursor, "items": attribution_payload["pending_attribution_items"]},
        ),
    ]


def test_postgres_git_review_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        GitReviewReadRepository,
        "load_gitlab_review",
        record_call(
            "load_gitlab_review",
            {"code_review_reports": {}, "gitlab_mr_snapshots": {}},
        ),
    )

    assert repository.load_gitlab_review() == {
        "code_review_reports": {},
        "gitlab_mr_snapshots": {},
    }
    assert calls == [("load_gitlab_review", {})]


def test_postgres_git_review_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            payload = args[0] if args else None
            call = dict(kwargs)
            if payload is not None:
                call["payload"] = payload
            calls.append((name, call))

        return _call

    def record_snapshot_upsert(self, cursor, snapshots):  # type: ignore[no-untyped-def]
        calls.append(("upsert_gitlab_mr_snapshots", {"cursor": cursor, "snapshots": snapshots}))

    def record_report_upsert(self, cursor, reports):  # type: ignore[no-untyped-def]
        calls.append(("upsert_code_review_reports", {"cursor": cursor, "reports": reports}))

    monkeypatch.setattr(
        GitReviewReadRepository,
        "save_gitlab_review",
        record_save("save_gitlab_review"),
    )
    monkeypatch.setattr(
        GitReviewReadRepository,
        "save_gitlab_review_snapshot_record",
        record_save("save_gitlab_review_snapshot_record"),
    )
    monkeypatch.setattr(
        GitReviewReadRepository,
        "upsert_gitlab_mr_snapshots",
        record_snapshot_upsert,
    )
    monkeypatch.setattr(
        GitReviewReadRepository,
        "upsert_code_review_reports",
        record_report_upsert,
    )

    payload = {
        "gitlab_mr_snapshots": {"snapshot_001": {"id": "snapshot_001"}},
        "code_review_reports": {"report_001": {"id": "report_001"}},
    }
    snapshot = {"id": "snapshot_002"}
    audit_event = {"id": "audit_001", "event_type": "gitlab_mr.snapshot_created"}
    cursor = object()

    repository.save_gitlab_review(payload)
    repository.save_gitlab_review_snapshot_record(snapshot=snapshot, audit_event=audit_event)
    repository._upsert_gitlab_mr_snapshots(cursor, payload["gitlab_mr_snapshots"])
    repository._upsert_code_review_reports(cursor, payload["code_review_reports"])

    assert calls == [
        ("save_gitlab_review", {"payload": payload}),
        (
            "save_gitlab_review_snapshot_record",
            {"snapshot": snapshot, "audit_event": audit_event},
        ),
        (
            "upsert_gitlab_mr_snapshots",
            {"cursor": cursor, "snapshots": payload["gitlab_mr_snapshots"]},
        ),
        (
            "upsert_code_review_reports",
            {"cursor": cursor, "reports": payload["code_review_reports"]},
        ),
    ]


def test_git_review_snapshot_record_writes_use_single_transaction(monkeypatch):
    connect_calls: list[dict] = []
    upsert_calls: list[dict] = []
    audit_calls: list[list[dict]] = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return FakeCursor()

    class FakeConnect:
        def __call__(self, *, autocommit: bool = True):
            connect_calls.append({"autocommit": autocommit})
            return FakeConnection()

    def upsert_audit_events(cursor, audit_events):  # type: ignore[no-untyped-def]
        audit_calls.append(audit_events)

    def record_snapshot_upsert(self, cursor, snapshots):  # type: ignore[no-untyped-def]
        upsert_calls.append(snapshots)

    monkeypatch.setattr(
        GitReviewReadRepository,
        "upsert_gitlab_mr_snapshots",
        record_snapshot_upsert,
    )

    repository = GitReviewReadRepository(
        FakeConnect(),
        upsert_audit_events=upsert_audit_events,
    )
    snapshot = {"id": "snapshot_atomic"}
    audit_event = {"id": "audit_git_review_atomic"}

    repository.save_gitlab_review_snapshot_record(
        snapshot=snapshot,
        audit_event=audit_event,
    )

    assert connect_calls == [{"autocommit": False}]
    assert upsert_calls == [{"snapshot_atomic": snapshot}]
    assert audit_calls == [[audit_event]]


def test_postgres_mock_writeback_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        MockWritebackReadRepository,
        "load_mock_writebacks",
        record_call("load_mock_writebacks", {"mock_writebacks": {}}),
    )

    assert repository.load_mock_writebacks() == {"mock_writebacks": {}}
    assert calls == [("load_mock_writebacks", {})]


def test_postgres_mock_writeback_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            payload = args[0] if args else None
            call = dict(kwargs)
            if payload is not None:
                call["payload"] = payload
            calls.append((name, call))

        return _call

    def record_issue_rows(self, writebacks):  # type: ignore[no-untyped-def]
        calls.append(("mock_issue_rows", {"writebacks": writebacks}))
        return {"mock_issue_001": {"id": "mock_issue_001"}}

    def record_issue_upsert(self, cursor, issues):  # type: ignore[no-untyped-def]
        calls.append(("upsert_mock_issues", {"cursor": cursor, "issues": issues}))

    monkeypatch.setattr(
        MockWritebackReadRepository,
        "save_mock_writebacks",
        record_save("save_mock_writebacks"),
    )
    monkeypatch.setattr(
        MockWritebackReadRepository,
        "save_mock_writeback_record",
        record_save("save_mock_writeback_record"),
    )
    monkeypatch.setattr(MockWritebackReadRepository, "mock_issue_rows", record_issue_rows)
    monkeypatch.setattr(MockWritebackReadRepository, "upsert_mock_issues", record_issue_upsert)

    payload = {
        "mock_writebacks": {
            "mock_issue:task_001": {"idempotency_key": "mock_issue:task_001"}
        }
    }
    record = {"idempotency_key": "mock_issue:task_002"}
    audit_event = {"id": "audit_001", "event_type": "mock_issue.written"}
    cursor = object()

    repository.save_mock_writebacks(payload)
    repository.save_mock_writeback_record(record, audit_event=audit_event)
    assert repository._mock_issue_rows(payload["mock_writebacks"]) == {
        "mock_issue_001": {"id": "mock_issue_001"}
    }
    repository._upsert_mock_issues(cursor, {"mock_issue_002": {"id": "mock_issue_002"}})

    assert calls == [
        ("save_mock_writebacks", {"payload": payload}),
        ("save_mock_writeback_record", {"payload": record, "audit_event": audit_event}),
        ("mock_issue_rows", {"writebacks": payload["mock_writebacks"]}),
        (
            "upsert_mock_issues",
            {"cursor": cursor, "issues": {"mock_issue_002": {"id": "mock_issue_002"}}},
        ),
    ]


def test_postgres_lifecycle_dashboard_read_models_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_call(name: str, result):  # type: ignore[no-untyped-def]
        def _call(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, kwargs))
            return result

        return _call

    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "load_lifecycle_context",
        record_call(
            "load_lifecycle_context",
            {"lifecycle_context_edges": {}, "lifecycle_risk_signals": {}},
        ),
    )
    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "get_lifecycle_context_source_rows",
        record_call(
            "get_lifecycle_context_source_rows",
            {"requirements": [], "lifecycle_context_edges": [], "lifecycle_risk_signals": []},
        ),
    )
    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "load_dashboard_snapshots",
        record_call("load_dashboard_snapshots", {"dashboard_metric_snapshots": {}}),
    )
    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "get_dashboard_it_team_source_rows",
        record_call("get_dashboard_it_team_source_rows", {"requirements": []}),
    )

    assert repository.load_lifecycle_context() == {
        "lifecycle_context_edges": {},
        "lifecycle_risk_signals": {},
    }
    assert repository.get_lifecycle_context_source_rows(product_id="product_001") == {
        "requirements": [],
        "lifecycle_context_edges": [],
        "lifecycle_risk_signals": [],
    }
    assert repository.load_dashboard_snapshots() == {"dashboard_metric_snapshots": {}}
    assert repository.get_dashboard_it_team_source_rows(
        user_roles=["admin"],
        product_id="product_001",
    ) == {"requirements": []}

    assert calls == [
        ("load_lifecycle_context", {}),
        ("get_lifecycle_context_source_rows", {"product_id": "product_001"}),
        ("load_dashboard_snapshots", {}),
        (
            "get_dashboard_it_team_source_rows",
            {"product_id": "product_001", "user_roles": ["admin"]},
        ),
    ]


def test_postgres_lifecycle_dashboard_writes_delegate_to_domain_repository(monkeypatch):
    repository = PostgresSnapshotRepository("postgresql://unused")
    calls: list[tuple[str, dict]] = []

    def record_save(name: str):  # type: ignore[no-untyped-def]
        def _call(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((name, {"args": args, "kwargs": kwargs}))

        return _call

    def record_upsert(name: str):  # type: ignore[no-untyped-def]
        def _call(self, cursor, items):  # type: ignore[no-untyped-def]
            calls.append((name, {"cursor": cursor, "items": items}))

        return _call

    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "save_lifecycle_context",
        record_save("save_lifecycle_context"),
    )
    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "save_dashboard_snapshots",
        record_save("save_dashboard_snapshots"),
    )
    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "save_dashboard_metric_snapshot_record",
        record_save("save_dashboard_metric_snapshot_record"),
    )
    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "upsert_lifecycle_context_edges",
        record_upsert("upsert_lifecycle_context_edges"),
    )
    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "upsert_lifecycle_risk_signals",
        record_upsert("upsert_lifecycle_risk_signals"),
    )
    monkeypatch.setattr(
        LifecycleDashboardReadRepository,
        "upsert_dashboard_metric_snapshots",
        record_upsert("upsert_dashboard_metric_snapshots"),
    )

    lifecycle_payload = {
        "lifecycle_context_edges": {"edge_001": {"id": "edge_001"}},
        "lifecycle_risk_signals": {"risk_001": {"id": "risk_001"}},
    }
    dashboard_payload = {
        "dashboard_metric_snapshots": {"dashboard_001": {"id": "dashboard_001"}}
    }
    snapshot = {"id": "dashboard_002"}
    cursor = object()

    repository.save_lifecycle_context(lifecycle_payload)
    repository.save_dashboard_snapshots(dashboard_payload)
    repository.save_dashboard_metric_snapshot_record(snapshot)
    repository._upsert_lifecycle_context_edges(
        cursor,
        lifecycle_payload["lifecycle_context_edges"],
    )
    repository._upsert_lifecycle_risk_signals(
        cursor,
        lifecycle_payload["lifecycle_risk_signals"],
    )
    repository._upsert_dashboard_metric_snapshots(
        cursor,
        dashboard_payload["dashboard_metric_snapshots"],
    )

    assert calls == [
        ("save_lifecycle_context", {"args": (lifecycle_payload,), "kwargs": {}}),
        ("save_dashboard_snapshots", {"args": (dashboard_payload,), "kwargs": {}}),
        ("save_dashboard_metric_snapshot_record", {"args": (snapshot,), "kwargs": {}}),
        (
            "upsert_lifecycle_context_edges",
            {"cursor": cursor, "items": lifecycle_payload["lifecycle_context_edges"]},
        ),
        (
            "upsert_lifecycle_risk_signals",
            {"cursor": cursor, "items": lifecycle_payload["lifecycle_risk_signals"]},
        ),
        (
            "upsert_dashboard_metric_snapshots",
            {"cursor": cursor, "items": dashboard_payload["dashboard_metric_snapshots"]},
        ),
    ]


class FakeDbFirstIdRepository(FakeSnapshotRepository):
    def __init__(self) -> None:
        super().__init__()
        self.allocated_prefixes: list[str] = []

    def next_id(self, prefix: str) -> str:
        self.allocated_prefixes.append(prefix)
        return f"{prefix}_101"


def test_persistent_store_delegates_new_ids_to_repository_when_available():
    repository = FakeDbFirstIdRepository()
    store = PersistentMemoryStore.from_repository(repository)

    assert store.new_id("requirement") == "requirement_101"
    assert repository.allocated_prefixes == ["requirement"]
    assert store.counters["requirement"] == 101


def test_persistent_store_does_not_restore_business_state_from_app_snapshot_payload():
    repository = FakeSnapshotRepository()
    repository.payload = {
        "ai_tasks": {
            "task_snapshot_only": {
                "id": "task_snapshot_only",
                "product_id": "product_snapshot_only",
                "requirement_id": "requirement_snapshot_only",
                "status": "completed",
                "task_type": "product_detail_design",
                "title": "旧快照任务",
            }
        },
        "products": {
            "product_snapshot_only": {
                "code": "SNAPSHOT-ONLY",
                "id": "product_snapshot_only",
                "name": "旧快照产品",
                "status": "active",
            }
        },
        "requirements": {
            "requirement_snapshot_only": {
                "content": "旧 app_state_snapshots 中的需求不能作为生产恢复源。",
                "created_by": "user_admin",
                "id": "requirement_snapshot_only",
                "priority": "P1",
                "product_id": "product_snapshot_only",
                "status": "ready_for_dev",
                "task_ids": ["task_snapshot_only"],
                "title": "旧快照需求",
            }
        },
    }

    store = PersistentMemoryStore.from_repository(repository)

    assert "product_snapshot_only" not in store.products
    assert "requirement_snapshot_only" not in store.requirements
    assert "task_snapshot_only" not in store.ai_tasks


def test_persistent_store_persist_does_not_write_app_snapshot_payload():
    repository = FakeSnapshotRepository()
    store = PersistentMemoryStore.from_repository(repository)
    store.products["product_no_snapshot"] = {
        "code": "NO-SNAPSHOT",
        "id": "product_no_snapshot",
        "name": "不写 app_state 快照",
        "status": "active",
    }

    store.persist()

    assert repository.payload is None
    assert repository.product_config_payload["products"]["product_no_snapshot"]["code"] == (
        "NO-SNAPSHOT"
    )
