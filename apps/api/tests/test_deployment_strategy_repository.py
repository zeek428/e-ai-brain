import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from app.core.repositories.devops import DevopsReadRepository
from app.core.repositories.devops_writes import (
    DeploymentSchemeVersionConflictError,
    DevopsWriteRepository,
)
from app.core.repositories.plugins import PluginReadRepository


class _Cursor:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=()):  # type: ignore[no-untyped-def]
        self.executed.append((" ".join(str(sql).split()), tuple(params)))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _Connection:
    def __init__(self, cursor: _Cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self._cursor


class _Connect:
    def __init__(self, cursor: _Cursor):
        self.cursor = cursor

    @contextmanager
    def __call__(self, *, autocommit: bool = True):
        del autocommit
        yield _Connection(self.cursor)


def test_deployment_strategy_migration_defines_scheme_and_execution_metadata():
    migration = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "db"
        / "migrations"
        / "101_deployment_strategies.sql"
    )

    sql = migration.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS deployment_schemes" in sql
    assert "deployment_method" in sql
    assert "executor_channel" in sql
    assert "idx_deployment_schemes_one_active_default" in sql
    assert "ADD COLUMN IF NOT EXISTS deployment_scheme_id" in sql
    assert "ADD COLUMN IF NOT EXISTS scheme_snapshot" in sql
    assert "ADD COLUMN IF NOT EXISTS deployment_run_id" in sql
    assert "ADD COLUMN IF NOT EXISTS capabilities" in sql
    assert "cancel_requested" in sql
    assert "WHERE NOT EXISTS" in sql
    assert "existing_default.is_default = true" in sql
    assert "existing_default.status = 'active'" in sql


def test_deployment_scheme_repository_lists_product_scoped_schemes():
    cursor = _Cursor(
        rows=[
            (
                "deployment_scheme_001",
                "product_001",
                "prod-manual",
                "生产人工部署",
                "prod",
                "manual",
                "manual",
                None,
                None,
                None,
                None,
                1800,
                {"notes": "人工确认"},
                True,
                "active",
                1,
                "user_admin",
                None,
                None,
            )
        ]
    )
    repository = DevopsReadRepository(_Connect(cursor))

    result = repository.list_deployment_schemes(
        environment="prod",
        product_id="product_001",
        product_scope_ids=["product_001"],
        status="active",
    )

    assert result == [
        {
            "code": "prod-manual",
            "config": {"notes": "人工确认"},
            "created_by": "user_admin",
            "deployment_method": "manual",
            "environment": "prod",
            "executor_channel": "manual",
            "id": "deployment_scheme_001",
            "is_default": True,
            "name": "生产人工部署",
            "product_id": "product_001",
            "status": "active",
            "timeout_seconds": 1800,
            "version": 1,
        }
    ]
    sql, params = cursor.executed[0]
    assert "FROM deployment_schemes" in sql
    assert "product_id = ANY(%s)" in sql
    assert params == ("product_001", "prod", "active", ["product_001"])


def test_deployment_scheme_repository_writes_versioned_config():
    cursor = _Cursor()
    repository = DevopsWriteRepository(_Connect(cursor))
    scheme = {
        "id": "deployment_scheme_001",
        "product_id": "product_001",
        "code": "prod-docker",
        "name": "生产 Docker 部署",
        "environment": "prod",
        "deployment_method": "docker",
        "executor_channel": "runner",
        "runner_id": "ai_executor_runner_003",
        "target_code": "production-compose",
        "timeout_seconds": 1800,
        "config": {"health_check_url": "/health"},
        "is_default": True,
        "status": "active",
        "version": 3,
        "created_by": "user_admin",
    }

    repository.upsert_deployment_schemes(cursor, {scheme["id"]: scheme})

    sql, params = cursor.executed[0]
    assert "INSERT INTO deployment_schemes" in sql
    assert "version = EXCLUDED.version" in sql
    assert params[0] == "deployment_scheme_001"
    assert params[6] == "runner"
    assert json.loads(params[12]) == {"health_check_url": "/health"}
    assert params[15] == 3


def test_deployment_scheme_repository_locks_and_rejects_stale_version():
    scheme = {
        "id": "deployment_scheme_001",
        "product_id": "product_001",
        "code": "prod-manual",
        "name": "生产人工部署",
        "environment": "prod",
        "deployment_method": "manual",
        "executor_channel": "manual",
        "timeout_seconds": 1800,
        "config": {},
        "is_default": True,
        "status": "active",
        "version": 5,
        "created_by": "user_admin",
    }
    current_cursor = _Cursor(rows=[(4,)])
    repository = DevopsWriteRepository(_Connect(current_cursor))

    repository.save_deployment_scheme_record(scheme, expected_version=4)

    assert "SELECT version FROM deployment_schemes" in current_cursor.executed[0][0]
    assert "FOR UPDATE" in current_cursor.executed[0][0]
    assert "UPDATE deployment_schemes" in current_cursor.executed[1][0]
    assert "version = version + 1" in current_cursor.executed[1][0]
    assert "INSERT INTO deployment_schemes" in current_cursor.executed[2][0]

    stale_cursor = _Cursor(rows=[(5,)])
    stale_repository = DevopsWriteRepository(_Connect(stale_cursor))
    with pytest.raises(DeploymentSchemeVersionConflictError) as exc_info:
        stale_repository.save_deployment_scheme_record(scheme, expected_version=4)

    assert exc_info.value.current_version == 5
    assert len(stale_cursor.executed) == 1


def test_ai_executor_task_write_links_deployment_run_and_cancel_requested_status():
    cursor = _Cursor()
    repository = PluginReadRepository(_Connect(cursor))

    repository.upsert_ai_executor_tasks(
        cursor,
        {
            "ai_executor_task_001": {
                "id": "ai_executor_task_001",
                "deployment_run_id": "deployment_run_001",
                "executor_type": "deployment",
                "instruction": "execute deployment target",
                "workspace_root": "/workspace",
                "status": "cancel_requested",
            }
        },
    )

    sql, params = cursor.executed[0]
    assert "deployment_run_id" in sql
    assert "deployment" in params
    assert "cancel_requested" in params
    assert "deployment_run_001" in params


def test_ai_executor_runner_write_persists_deployment_capability():
    cursor = _Cursor()
    repository = PluginReadRepository(_Connect(cursor))

    repository.upsert_ai_executor_runners(
        cursor,
        {
            "runner_deploy": {
                "id": "runner_deploy",
                "name": "部署 Runner",
                "executor_types": ["codex"],
                "capabilities": ["deployment"],
                "token_hash": "hash",
            }
        },
    )

    sql, params = cursor.executed[0]
    assert "capabilities" in sql
    assert json.loads(params[-1]) == ["deployment"]


def test_claim_due_deployment_runs_uses_skip_locked_lease():
    cursor = _Cursor(
        rows=[
            (
                "deployment_run_jenkins",
                "deployment_request_001",
                "jenkins",
                "jenkins",
                "integration",
                None,
                "plugin_invocation_log_001",
                "folder/deploy",
                None,
                "queued",
                None,
                "https://jenkins.example.com/queue/item/1/",
                None,
                {},
                [],
                "deployment-start:1:1",
                None,
                0,
                "worker-1",
                None,
                None,
                None,
                None,
                "user_admin",
                None,
                None,
            )
        ]
    )
    repository = DevopsReadRepository(_Connect(cursor))

    runs = repository.claim_due_deployment_runs(
        lease_seconds=30,
        limit=10,
        worker_id="worker-1",
    )

    assert runs[0]["id"] == "deployment_run_jenkins"
    sql, params = cursor.executed[0]
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "sync_lease_until" in sql
    assert params == (10, "worker-1", 30)
