from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from app.core.repositories.execution_governance import ExecutionGovernanceReadRepository
from app.core.repositories.execution_governance_writes import (
    ExecutionGovernanceVersionConflictError,
    ExecutionGovernanceWriteRepository,
)


class _Cursor:
    def __init__(self, rows: list[tuple] | None = None) -> None:
        self.rows = rows or []
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((" ".join(sql.split()), tuple(params or ())))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self._cursor


class _Connect:
    def __init__(self, cursor: _Cursor) -> None:
        self.cursor = cursor
        self.autocommit_values: list[bool] = []

    @contextmanager
    def __call__(self, *, autocommit: bool = True):
        self.autocommit_values.append(autocommit)
        yield _Connection(self.cursor)


def test_autonomous_delivery_migration_defines_governance_primitives():
    migration = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "db"
        / "migrations"
        / "102_autonomous_delivery_governance.sql"
    )

    sql = migration.read_text(encoding="utf-8")

    for table_name in (
        "quality_gate_policies",
        "quality_gate_runs",
        "quality_gate_checks",
        "agent_loop_runs",
        "agent_loop_iterations",
        "execution_context_manifests",
        "execution_outbox_events",
        "execution_resource_grants",
        "external_event_inbox",
        "deployment_run_steps",
        "knowledge_document_versions",
        "knowledge_processing_profiles",
        "knowledge_citation_feedback",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in sql
    assert "minimum_independent_evidence" in sql
    assert "autonomy_mode" in sql
    assert "rollout_strategy" in sql
    assert "window_enforcement" in sql
    assert "idx_execution_outbox_claim" in sql
    assert "idx_external_event_inbox_claim" in sql
    assert "UNIQUE (provider, delivery_id)" in sql
    assert "UNIQUE (loop_run_id, iteration_number)" in sql


def test_quality_gate_policy_list_is_product_scoped():
    cursor = _Cursor(
        rows=[
            (
                "quality_gate_policy_001",
                "研发合并默认门禁",
                "product_001",
                "development_planning",
                "pre_merge",
                ["low", "medium"],
                [{"type": "unit_test", "required": True}],
                ["apps/api/app/db/migrations/**"],
                40,
                1200,
                ["backend-tests"],
                1,
                True,
                "active",
                3,
                "user_admin",
                None,
                None,
            )
        ]
    )
    repository = ExecutionGovernanceReadRepository(_Connect(cursor))

    policies = repository.list_quality_gate_policies(
        phase="pre_merge",
        product_id="product_001",
        product_scope_ids=["product_001"],
        status="active",
        task_type="development_planning",
    )

    assert policies == [
        {
            "created_by": "user_admin",
            "id": "quality_gate_policy_001",
            "manual_review_on_migration": True,
            "max_changed_files": 40,
            "max_changed_lines": 1200,
            "minimum_independent_evidence": 1,
            "name": "研发合并默认门禁",
            "phase": "pre_merge",
            "product_id": "product_001",
            "protected_paths": ["apps/api/app/db/migrations/**"],
            "required_checks": [{"required": True, "type": "unit_test"}],
            "required_ci_contexts": ["backend-tests"],
            "risk_levels": ["low", "medium"],
            "status": "active",
            "task_type": "development_planning",
            "version": 3,
        }
    ]
    sql, params = cursor.executed[0]
    assert "FROM quality_gate_policies" in sql
    assert "product_id = ANY(%s)" in sql
    assert "product_id IS NULL" in sql
    assert params == (
        "product_001",
        "development_planning",
        "pre_merge",
        "active",
        ["product_001"],
    )


def test_quality_gate_policy_write_uses_optimistic_lock():
    cursor = _Cursor(rows=[(2,)])
    connect = _Connect(cursor)
    repository = ExecutionGovernanceWriteRepository(connect)
    policy = {
        "id": "quality_gate_policy_001",
        "name": "研发合并默认门禁",
        "phase": "pre_merge",
        "risk_levels": ["low", "medium"],
        "required_checks": [{"type": "unit_test", "required": True}],
        "protected_paths": [],
        "required_ci_contexts": [],
        "minimum_independent_evidence": 1,
        "manual_review_on_migration": True,
        "status": "active",
        "version": 3,
    }

    repository.save_quality_gate_policy_record(policy, expected_version=2)

    assert connect.autocommit_values == [False]
    assert "FOR UPDATE" in cursor.executed[0][0]
    assert "INSERT INTO quality_gate_policies" in cursor.executed[1][0]
    assert json.loads(cursor.executed[1][1][6]) == [
        {"required": True, "type": "unit_test"}
    ]

    stale_cursor = _Cursor(rows=[(3,)])
    stale_repository = ExecutionGovernanceWriteRepository(_Connect(stale_cursor))
    with pytest.raises(ExecutionGovernanceVersionConflictError) as exc_info:
        stale_repository.save_quality_gate_policy_record(policy, expected_version=2)
    assert exc_info.value.current_version == 3
    assert len(stale_cursor.executed) == 1


def test_claim_execution_outbox_events_uses_skip_locked_lease():
    cursor = _Cursor(
        rows=[
            (
                "outbox_001",
                "deployment_request",
                "deployment_001",
                "runner_task_dispatch",
                "deployment:deployment_001:run_001",
                {"deployment_run_id": "run_001"},
                "processing",
                1,
                None,
                "worker-001",
                None,
                None,
                None,
                None,
                None,
            )
        ]
    )
    repository = ExecutionGovernanceReadRepository(_Connect(cursor))

    events = repository.claim_execution_outbox_events(
        lease_seconds=30,
        limit=10,
        worker_id="worker-001",
    )

    assert events[0]["event_type"] == "runner_task_dispatch"
    assert events[0]["payload"] == {"deployment_run_id": "run_001"}
    sql, params = cursor.executed[0]
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "lease_until" in sql
    assert params == (10, "worker-001", 30)


def test_deployment_dispatch_bundle_uses_one_transaction():
    cursor = _Cursor()
    connect = _Connect(cursor)
    repository = ExecutionGovernanceWriteRepository(connect)

    repository.create_deployment_dispatch_transaction(
        deployment={
            "id": "deployment_001",
            "product_id": "product_001",
            "version_id": "version_001",
            "title": "生产发布",
            "requirement_ids": ["requirement_001"],
            "environment": "prod",
            "risk_level": "medium",
            "gate_summary": {"status": "ready"},
            "status": "preflight",
            "created_by": "user_admin",
        },
        run={
            "id": "deployment_run_001",
            "deployment_request_id": "deployment_001",
            "executor_type": "deployment",
            "deployment_method": "docker",
            "executor_channel": "runner",
            "status": "queued",
            "created_by": "user_admin",
        },
        steps=[
            {
                "id": "deployment_step_001",
                "deployment_run_id": "deployment_run_001",
                "step_type": "preflight",
                "status": "pending",
                "sequence": 1,
            }
        ],
        outbox_event={
            "id": "outbox_001",
            "aggregate_type": "deployment_request",
            "aggregate_id": "deployment_001",
            "event_type": "deployment_preflight",
            "idempotency_key": "deployment:deployment_001:preflight:1",
            "payload": {"deployment_run_id": "deployment_run_001"},
            "status": "pending",
        },
        audit_events=[
            {
                "id": "audit_001",
                "event_type": "deployment.dispatch_queued",
                "actor_id": "user_admin",
                "subject_type": "deployment_request",
                "subject_id": "deployment_001",
                "payload": {},
            }
        ],
        requirements=[
            {
                "id": "requirement_001",
                "product_id": "product_001",
                "title": "生产发布需求",
                "content": "发布到生产环境",
                "status": "deploying",
                "created_by": "user_admin",
                "version_id": "version_001",
            }
        ],
    )

    assert connect.autocommit_values == [False]
    executed_sql = "\n".join(sql for sql, _ in cursor.executed)
    assert "INSERT INTO deployment_requests" in executed_sql
    assert "INSERT INTO deployment_runs" in executed_sql
    assert "INSERT INTO deployment_run_steps" in executed_sql
    assert "INSERT INTO execution_outbox_events" in executed_sql
    assert "INSERT INTO requirements" in executed_sql
    assert "INSERT INTO audit_events" in executed_sql


def test_deployment_dispatch_failure_bundle_uses_one_transaction():
    cursor = _Cursor()
    connect = _Connect(cursor)
    repository = ExecutionGovernanceWriteRepository(connect)

    repository.save_deployment_dispatch_failure_transaction(
        deployment={
            "id": "deployment_001",
            "product_id": "product_001",
            "version_id": "version_001",
            "title": "生产发布",
            "requirement_ids": ["requirement_001"],
            "environment": "prod",
            "risk_level": "medium",
            "gate_summary": {"status": "ready"},
            "status": "failed",
            "created_by": "user_admin",
        },
        run={
            "id": "deployment_run_001",
            "deployment_request_id": "deployment_001",
            "executor_type": "jenkins",
            "deployment_method": "jenkins",
            "executor_channel": "integration",
            "status": "failed",
            "created_by": "user_admin",
        },
        steps=[
            {
                "id": "deployment_step_001",
                "deployment_run_id": "deployment_run_001",
                "step_type": "deploy",
                "status": "failed",
                "sequence": 2,
            }
        ],
        outbox_event={
            "id": "outbox_001",
            "aggregate_type": "deployment_request",
            "aggregate_id": "deployment_001",
            "event_type": "deployment_dispatch_requested",
            "idempotency_key": "deployment:deployment_001:run_001",
            "payload": {"deployment_run_id": "deployment_run_001"},
            "status": "dead_letter",
        },
        requirements=[
            {
                "id": "requirement_001",
                "product_id": "product_001",
                "title": "生产发布需求",
                "content": "发布到生产环境",
                "status": "ready_for_release",
                "created_by": "user_admin",
                "version_id": "version_001",
            }
        ],
        audit_events=[
            {
                "id": "audit_001",
                "event_type": "execution.outbox.dead_lettered",
                "actor_id": "worker_001",
                "subject_type": "execution_outbox_event",
                "subject_id": "outbox_001",
                "payload": {},
            }
        ],
    )

    assert connect.autocommit_values == [False]
    executed_sql = "\n".join(sql for sql, _ in cursor.executed)
    assert "INSERT INTO deployment_requests" in executed_sql
    assert "INSERT INTO deployment_runs" in executed_sql
    assert "INSERT INTO deployment_run_steps" in executed_sql
    assert "INSERT INTO execution_outbox_events" in executed_sql
    assert "INSERT INTO requirements" in executed_sql
    assert "INSERT INTO audit_events" in executed_sql
