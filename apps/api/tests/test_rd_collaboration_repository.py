from __future__ import annotations

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg import sql

from app.core.graph_checkpointer import build_checkpointer
from app.core.persistence import PostgresSnapshotRepository
from app.core.persistence_runtime import PostgresRuntimeStore
from app.core.rd_collaboration_graph import build_rd_collaboration_graph, rd_collaboration_thread_id
from app.core.repositories.rd_collaboration import (
    RdCollaborationReadRepository,
    RdCollaborationRepositoryError,
    RdCollaborationVersionConflictError,
)
from app.main import app
from app.services.rd_collaboration_decisions import answer_decision_request
from app.services.rd_collaboration_graph_runtime import RdCollaborationGraphRuntime
from app.services.rd_collaboration_planning import start_collaboration_run
from app.services.rd_requirement_entry_adapters import create_or_link_rd_requirement
from app.services.rd_work_item_scheduler import claim_work_item, review_work_item
from app.workers.execution_worker import run_execution_worker_iteration
from tests.test_technical_solution_export import auth_headers

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations"
DEFAULT_POSTGRES_ADMIN_URL = "postgresql://ai_brain:ai_brain_password@127.0.0.1:5432/postgres"


@pytest.fixture(scope="session")
def postgres_admin_url() -> str:
    database_url = os.getenv(
        "AI_BRAIN_TEST_POSTGRES_ADMIN_URL",
        DEFAULT_POSTGRES_ADMIN_URL,
    )
    try:
        with psycopg.connect(database_url, autocommit=True) as connection:
            connection.execute("SELECT 1")
    except psycopg.OperationalError as exc:
        pytest.skip(f"real PostgreSQL is required for collaboration repository tests: {exc}")
    return database_url


def _database_url(admin_url: str, database_name: str) -> str:
    return str(psycopg.conninfo.make_conninfo(admin_url, dbname=database_name))


@contextmanager
def _temporary_database(admin_url: str) -> Iterator[str]:
    database_name = f"ai_brain_rd_repo_{uuid4().hex}"
    with psycopg.connect(admin_url, autocommit=True) as admin_connection:
        admin_connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )
    try:
        database_url = _database_url(admin_url, database_name)
        with psycopg.connect(database_url, autocommit=True) as connection:
            for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                connection.execute(migration_path.read_text(encoding="utf-8"))
        yield database_url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin_connection:
            admin_connection.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                (database_name,),
            )
            admin_connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
            )


@pytest.fixture
def repository(postgres_admin_url: str) -> Iterator[PostgresSnapshotRepository]:
    with _temporary_database(postgres_admin_url) as database_url:
        value = PostgresSnapshotRepository(database_url, pool_max_size=8)
        try:
            yield value
        finally:
            value._pool.close()


def _insert_product_version(
    repository: PostgresSnapshotRepository,
    *,
    prefix: str,
    status: str = "planning",
    scope_version: int = 1,
) -> dict[str, str]:
    ids = {
        "product": f"{prefix}-product",
        "version": f"{prefix}-version",
    }
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            "INSERT INTO products (id, code, name) VALUES (%s, %s, %s)",
            (ids["product"], f"{prefix}-code", f"{prefix} product"),
        )
        connection.execute(
            """
            INSERT INTO product_versions (
              id, product_id, code, name, status, scope_version
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                ids["version"],
                ids["product"],
                f"{prefix}-v1",
                f"{prefix} v1",
                status,
                scope_version,
            ),
        )
    return ids


def test_postgres_checkpointer_restores_collaboration_cursor(
    repository: PostgresSnapshotRepository,
) -> None:
    settings = SimpleNamespace(
        is_test_env=False,
        persistence_mode="postgres",
        database_url=repository.database_url,
    )
    first_checkpointer = build_checkpointer(settings)
    config = {"configurable": {"thread_id": rd_collaboration_thread_id("run-checkpoint")}}
    try:
        first_graph = build_rd_collaboration_graph(first_checkpointer)
        first_graph.invoke(
            {
                "collaboration_run_id": "run-checkpoint",
                "current_step": "start",
                "processed_event_ids": [],
            },
            config=config,
        )
        first_graph.invoke({"event_id": "event-1"}, config=config)

        second_checkpointer = build_checkpointer(settings)
        try:
            restored = build_rd_collaboration_graph(second_checkpointer).get_state(config)
        finally:
            second_checkpointer.conn.close()
    finally:
        first_checkpointer.conn.close()

    assert restored.values["collaboration_run_id"] == "run-checkpoint"
    assert restored.values["processed_event_ids"] == ["event-1"]


def test_incompatible_postgres_checkpoint_creates_a_human_takeover_decision(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="graph-checkpoint-takeover")
    run_id = str(seeded["run"]["id"])
    checkpointer = build_checkpointer(
        SimpleNamespace(
            is_test_env=False,
            persistence_mode="postgres",
            database_url=repository.database_url,
        )
    )
    try:
        runtime = RdCollaborationGraphRuntime(
            PostgresRuntimeStore(repository),
            checkpointer=checkpointer,
        )
        runtime.write_incompatible_checkpoint_for_test(run_id)

        result = runtime.handle_event(
            collaboration_run_id=run_id,
            event_id="graph-checkpoint-event",
            event_type="work_item.completed",
        )
    finally:
        checkpointer.conn.close()

    decision = repository.get_decision_request(f"graph-checkpoint-takeover:{run_id}")
    assert result["checkpoint_status"] == "incompatible"
    assert repository.get_rd_collaboration_run(run_id)["status"] == "waiting_human"
    assert decision is not None
    assert decision["decision_type"] == "graph_checkpoint_incompatible"


def test_postgres_domain_event_retries_after_checkpoint_failure_without_duplicates(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="graph-checkpoint-retry")
    run_id = str(seeded["run"]["id"])
    checkpointer = build_checkpointer(
        SimpleNamespace(
            is_test_env=False,
            persistence_mode="postgres",
            database_url=repository.database_url,
        )
    )
    try:
        runtime = RdCollaborationGraphRuntime(
            PostgresRuntimeStore(repository),
            checkpointer=checkpointer,
        )
        runtime.fail_next_checkpoint_write()
        first = runtime.handle_event(
            collaboration_run_id=run_id,
            event_id="graph-retry-event",
            event_type="work_item.completed",
        )
        replay = runtime.handle_event(
            collaboration_run_id=run_id,
            event_id="graph-retry-event",
            event_type="work_item.completed",
        )
    finally:
        checkpointer.conn.close()

    events = repository.list_rd_collaboration_events(run_id)
    feedback = repository.list_role_feedback_records(run_id)
    outbox = repository.list_execution_outbox_events(
        aggregate_type="rd_collaboration_run",
        aggregate_id=run_id,
        status=None,
    )
    audit = repository.list_audit_events(subject_type="rd_collaboration_run", subject_id=run_id)
    assert first["checkpoint_status"] == "failed"
    assert replay["checkpoint_status"] == "persisted"
    assert [event["id"] for event in events] == ["graph-retry-event"]
    assert len(feedback) == 1
    assert len(outbox) == 0
    assert len(audit) == 1


def test_postgres_workflow_rows_round_trip_stable_ai_task_thread_metadata(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="graph-thread-metadata")
    requirement_id = "graph-thread-metadata-requirement"
    task_id = "graph-thread-metadata-task"
    graph_run_id = "graph-thread-metadata-run"
    checkpoint_id = "graph-thread-metadata-checkpoint"
    _insert_requirement(repository, ids, requirement_id=requirement_id, version_id=ids["version"])
    repository.save_ai_tasks(
        {
            "ai_tasks": {
                task_id: {
                    "id": task_id,
                    "brain_app_id": "rd_brain",
                    "requirement_id": requirement_id,
                    "task_type": "technical_solution",
                    "title": "graph metadata",
                    "status": "waiting_review",
                    "product_id": ids["product"],
                    "version_id": ids["version"],
                    "product_context": {},
                    "input_json": {},
                    "output_json": None,
                    "created_by": "user_admin",
                }
            }
        }
    )
    repository.save_workflow_runtime(
        {
            "graph_runs": {
                graph_run_id: {
                    "id": graph_run_id,
                    "ai_task_id": task_id,
                    "task_type": "technical_solution",
                    "status": "interrupted",
                    "thread_id": f"ai_task:{task_id}",
                    "subject_type": "ai_task",
                    "subject_id": task_id,
                    "graph_definition": "ai_task",
                    "graph_version": "v1",
                    "node_path": [],
                    "state_snapshot": {},
                }
            },
            "graph_checkpoints": {
                checkpoint_id: {
                    "id": checkpoint_id,
                    "graph_run_id": graph_run_id,
                    "ai_task_id": task_id,
                    "current_step": "interrupt_for_human_review",
                    "thread_id": f"ai_task:{task_id}",
                    "subject_type": "ai_task",
                    "subject_id": task_id,
                    "graph_definition": "ai_task",
                    "graph_version": "v1",
                    "state_snapshot": {},
                }
            },
            "human_reviews": {},
        }
    )

    payload = repository.load_workflow_runtime()
    graph_run = payload["graph_runs"][graph_run_id]
    checkpoint = payload["graph_checkpoints"][checkpoint_id]
    assert graph_run["thread_id"] == f"ai_task:{task_id}"
    assert graph_run["graph_definition"] == "ai_task"
    assert checkpoint["thread_id"] == f"ai_task:{task_id}"
    assert checkpoint["graph_version"] == "v1"


def test_requirement_entry_adapter_uses_postgres_product_and_reuses_open_requirement(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = _insert_product_version(repository, prefix="entry-adapter-postgres")
    current_store = PostgresRuntimeStore(repository)
    evidence = {"content": "PostgreSQL 入口适配需求", "title": "PostgreSQL 入口适配需求"}

    created = create_or_link_rd_requirement(
        current_store,
        evidence=evidence,
        product_id=ids["product"],
        source_id="draft-entry-adapter-postgres",
        source_type="assistant_action_draft",
        user={"id": "user_admin", "roles": ["admin"]},
    )

    def _unexpected_full_requirement_load() -> dict[str, object]:
        raise AssertionError("adapter lookup must use the source-adapter-key repository query")

    monkeypatch.setattr(repository, "load_requirements", _unexpected_full_requirement_load)
    reused = create_or_link_rd_requirement(
        current_store,
        evidence=evidence,
        product_id=ids["product"],
        source_id="draft-entry-adapter-postgres",
        source_type="assistant_action_draft",
        user={"id": "user_admin", "roles": ["admin"]},
    )

    assert created["created"] is True
    assert reused["created"] is False
    assert reused["requirement_id"] == created["requirement_id"]
    source_adapter_key = "assistant_action_draft:draft-entry-adapter-postgres"
    requirement = repository.get_open_requirement_by_source_adapter_key(source_adapter_key)
    assert requirement is not None
    assert requirement["source_adapter_key"] == source_adapter_key


def test_requirement_entry_adapter_create_or_link_is_atomic_in_postgres(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="entry-adapter-postgres-race")
    evidence = {"content": "并发入口适配需求", "title": "并发入口适配需求"}

    def create() -> dict[str, object]:
        return create_or_link_rd_requirement(
            PostgresRuntimeStore(repository),
            evidence=evidence,
            product_id=ids["product"],
            source_id="draft-entry-adapter-postgres-race",
            source_type="assistant_action_draft",
            user={"id": "user_admin", "roles": ["admin"]},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create(), range(2)))

    requirement_ids = {str(result["requirement_id"]) for result in results}
    assert len(requirement_ids) == 1
    assert sorted(bool(result["created"]) for result in results) == [False, True]
    requirement = repository.get_open_requirement_by_source_adapter_key(
        "assistant_action_draft:draft-entry-adapter-postgres-race"
    )
    assert requirement is not None
    assert requirement["id"] in requirement_ids


def _policy_record(ids: dict[str, str], *, prefix: str) -> dict[str, object]:
    return {
        "id": f"{prefix}-policy",
        "name": f"{prefix} policy",
        "brain_app_id": "rd_brain",
        "product_id": ids["product"],
        "task_type": "code_change",
        "executor_type": "codex",
        "instruction_template": "execute safely",
        "status": "active",
    }


def test_unified_policy_transaction_persists_strategy_and_reconciles_bindings(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="unified-policy")
    created = repository.save_unified_rd_policy(
        {
            **_policy_record(ids, prefix="unified-policy"),
            "strategy_config": {
                "matching_config": {"task_types": ["development_planning", "testing"]},
                "team_config": {"required_role_codes": ["developer", "tester"]},
            },
        },
        role_bindings=[
            {
                "id": "binding-developer",
                "role_code": "developer",
                "actor_mode": "ai",
                "status": "active",
            },
            {
                "id": "binding-tester",
                "role_code": "tester",
                "actor_mode": "human",
                "status": "active",
            },
        ],
    )
    assert created["policy_version"] == 1
    assert repository.get_rd_task_executor_policy(created["id"])["strategy_config"][
        "matching_config"
    ]["task_types"] == ["development_planning", "testing"]
    assert [
        item["role_code"] for item in repository.list_rd_policy_role_bindings(created["id"])
    ] == ["developer", "tester"]

    updated = repository.save_unified_rd_policy(
        {**created, "strategy_config": {"matching_config": {"task_types": ["testing"]}}},
        role_bindings=[
            {
                "id": "binding-tester-v2",
                "role_code": "tester",
                "actor_mode": "ai",
                "status": "active",
            },
        ],
        expected_policy_version=1,
    )
    assert updated["policy_version"] == 2
    assert [
        item["role_code"] for item in repository.list_rd_policy_role_bindings(updated["id"])
    ] == ["tester"]


def test_unified_policy_route_persists_server_binding_ids_in_postgres(
    repository: PostgresSnapshotRepository,
) -> None:
    original_store = app.state.store
    app.state.store = PostgresRuntimeStore(repository)
    client = TestClient(app)
    payload = {
        "name": "Postgres route strategy",
        "brain_app_id": "rd_brain",
        "status": "active",
        "matching_config": {"task_types": ["development_planning"]},
        "assessment_config": {},
        "iteration_config": {},
        "delivery_target": "ready_for_release",
        "team_config": {"required_role_codes": ["developer"]},
        "autonomy_config": {},
        "quality_gate_config": {},
        "git_config": {},
        "experience_reuse_config": {},
        "deployment_config": {},
        "role_bindings": [{"role_code": "developer", "actor_mode": "ai", "status": "active"}],
    }
    try:
        created = client.post(
            "/api/delivery/rd-task-executor-policies", json=payload, headers=auth_headers()
        )
        assert created.status_code == 200
        policy = created.json()["data"]["policy"]
        binding = repository.list_rd_policy_role_bindings(policy["id"])[0]
        assert binding["id"] == f"rd_policy_binding_{policy['id']}_developer"
        assert (
            repository.get_rd_task_executor_policy(policy["id"])["strategy_config"]["name"]
            == payload["name"]
        )
        updated = client.patch(
            f"/api/delivery/rd-task-executor-policies/{policy['id']}",
            json={"expected_policy_version": 1, "changes": {"name": "Postgres route strategy v2"}},
            headers=auth_headers(),
        )
        assert updated.status_code == 200
        assert repository.list_rd_policy_role_bindings(policy["id"])[0]["id"] == binding["id"]
        stale = client.patch(
            f"/api/delivery/rd-task-executor-policies/{policy['id']}",
            json={"expected_policy_version": 1, "changes": {"name": "stale policy"}},
            headers=auth_headers(),
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "RD_VERSION_CONFLICT"
        assert stale.json()["detail"]["details"] == {"current_policy_version": 2}
        assert repository.get_rd_task_executor_policy(policy["id"])["strategy_config"]["name"] == (
            "Postgres route strategy v2"
        )
        assert repository.list_rd_policy_role_bindings(policy["id"])[0]["id"] == binding["id"]
    finally:
        app.state.store = original_store


def test_unified_policy_executor_filter_uses_all_active_role_bindings(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="multi-role-filter")
    for profile_id, executor_type in (("profile-codex", "codex"), ("profile-claude", "claude")):
        repository.save_rd_executor_profile_record(
            {
                "id": profile_id,
                "brain_app_id": "rd_brain",
                "code": profile_id,
                "name": profile_id,
                "executor_type": executor_type,
                "created_by": "user_admin",
            }
        )
    policy = repository.save_unified_rd_policy(
        {
            **_policy_record(ids, prefix="multi-role-filter"),
            "strategy_config": {"matching_config": {"task_types": ["development_planning"]}},
        },
        role_bindings=[
            {
                "id": "binding-codex",
                "role_code": "developer",
                "actor_mode": "ai",
                "primary_executor_profile_id": "profile-codex",
                "status": "active",
            },
            {
                "id": "binding-claude",
                "role_code": "reviewer",
                "actor_mode": "ai",
                "primary_executor_profile_id": "profile-claude",
                "status": "active",
            },
        ],
    )

    def listed(executor_type: str) -> list[dict]:
        return repository.list_rd_task_executor_policy_page(
            executor_type=executor_type,
            limit=20,
            offset=0,
        )

    assert [item["id"] for item in listed("codex")] == [policy["id"]]
    assert [item["id"] for item in listed("claude")] == [policy["id"]]
    assert listed("openclaw") == []


def _base_snapshot(policy: dict[str, object], *, prefix: str) -> dict[str, object]:
    return {
        "id": f"{prefix}-snapshot-base",
        "policy_id": policy["id"],
        "policy_version": 1,
        "parent_snapshot_id": None,
        "snapshot_kind": "base",
        "resolution_context_key": f"policy:{policy['id']}:version:1",
        "resolution_revision": 0,
        "schema_version": 1,
        "content_hash": f"{prefix}-base-hash",
        "payload_json": {
            "allowed_tools": ["read", "test"],
            "forbidden_tools": ["deploy"],
            "max_parallelism": 2,
        },
        "created_by": "user_admin",
    }


def _insert_requirement(
    repository: PostgresSnapshotRepository,
    ids: dict[str, str],
    *,
    requirement_id: str,
    status: str = "approved",
    version_id: str | None = None,
) -> None:
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO requirements (
              id, brain_app_id, title, product_id, version_id, description,
              priority, source, status, created_by
            )
            VALUES (%s, 'rd_brain', %s, %s, %s, 'seed', 'P1',
                    'business_department', %s, 'user_admin')
            """,
            (
                requirement_id,
                f"{requirement_id} title",
                ids["product"],
                version_id,
                status,
            ),
        )


def _accepted_assessment(
    *,
    assessment_id: str,
    requirement_id: str,
    snapshot_id: str,
    revision: int = 1,
) -> dict[str, object]:
    return {
        "id": assessment_id,
        "requirement_id": requirement_id,
        "requirement_revision": revision,
        "initial_strategy_snapshot_id": snapshot_id,
        "final_strategy_snapshot_id": snapshot_id,
        "strategy_snapshot_id": snapshot_id,
        "structured_assessment": {"complete": True},
        "status": "accepted",
        "created_by": "user_admin",
        "decided_by": "user_admin",
        "decided_at": datetime.now(UTC),
    }


def _version_snapshot(
    *,
    base_snapshot_id: str,
    ids: dict[str, str],
    policy_id: str,
    prefix: str,
    scope_version: int = 1,
) -> dict[str, object]:
    return {
        "id": f"{prefix}-snapshot-version",
        "policy_id": policy_id,
        "policy_version": 1,
        "parent_snapshot_id": base_snapshot_id,
        "snapshot_kind": "version_resolved",
        "resolution_context_key": (f"version:{ids['version']}:scope:{scope_version}"),
        "resolution_revision": 1,
        "schema_version": 1,
        "content_hash": f"{prefix}-version-hash",
        "payload_json": {"resolved": True},
        "created_by": "user_admin",
    }


def _run_record(
    *,
    ids: dict[str, str],
    snapshot_id: str,
    prefix: str,
    status: str = "running",
    scope_version: int = 1,
    generation: int = 1,
    supersedes_run_id: str | None = None,
) -> dict[str, object]:
    return {
        "id": f"{prefix}-run-g{generation}",
        "brain_app_id": "rd_brain",
        "product_id": ids["product"],
        "product_version_id": ids["version"],
        "strategy_snapshot_id": snapshot_id,
        "run_generation": generation,
        "supersedes_run_id": supersedes_run_id,
        "scope_version": scope_version,
        "plan_version": 0,
        "status": status,
        "delivery_target": "ready_for_release",
        "graph_version": "v1",
        "created_by": "user_admin",
    }


def _run_scope(
    *,
    assessment_id: str,
    final_snapshot_id: str,
    requirement_id: str,
    run_id: str,
    prefix: str,
) -> dict[str, object]:
    return {
        "id": f"{prefix}-run-scope-{requirement_id}",
        "collaboration_run_id": run_id,
        "requirement_id": requirement_id,
        "requirement_revision": 1,
        "assessment_id": assessment_id,
        "final_strategy_snapshot_id": final_snapshot_id,
        "acceptance_criteria_hash": f"{requirement_id}-acceptance",
        "repository_scope_hash": f"{requirement_id}-repository",
    }


def _seed_exact_run(
    repository: PostgresSnapshotRepository,
    *,
    prefix: str,
    run_status: str = "running",
    version_status: str = "active",
) -> dict[str, object]:
    ids = _insert_product_version(
        repository,
        prefix=prefix,
        status=version_status,
    )
    policy = _policy_record(ids, prefix=prefix)
    repository.save_rd_task_executor_policy_record(policy)
    base = repository.freeze_base_policy_snapshot(_base_snapshot(policy, prefix=prefix))
    requirement_id = f"{prefix}-requirement"
    assessment_id = f"{prefix}-assessment"
    _insert_requirement(
        repository,
        ids,
        requirement_id=requirement_id,
        status="planned",
        version_id=ids["version"],
    )
    assessment = _accepted_assessment(
        assessment_id=assessment_id,
        requirement_id=requirement_id,
        snapshot_id=str(base["id"]),
    )
    repository.save_assessment_bundle(assessment=assessment, opinions=[])
    version_snapshot = _version_snapshot(
        base_snapshot_id=str(base["id"]),
        ids=ids,
        policy_id=str(policy["id"]),
        prefix=prefix,
    )
    repository.merge_version_policy_snapshot_with_sources(
        snapshot=version_snapshot,
        sources=[
            {
                "id": f"{prefix}-source",
                "snapshot_id": version_snapshot["id"],
                "source_snapshot_id": base["id"],
                "requirement_id": requirement_id,
                "assessment_id": assessment_id,
            }
        ],
    )
    run = _run_record(
        ids=ids,
        snapshot_id=str(version_snapshot["id"]),
        prefix=prefix,
        status=run_status,
    )
    scope = _run_scope(
        assessment_id=assessment_id,
        final_snapshot_id=str(base["id"]),
        requirement_id=requirement_id,
        run_id=str(run["id"]),
        prefix=prefix,
    )
    repository.create_collaboration_run_with_exact_scope(
        run=run,
        scope_rows=[scope],
    )
    return {
        **ids,
        "policy": policy,
        "base_snapshot": base,
        "requirement": requirement_id,
        "assessment": assessment_id,
        "version_snapshot": version_snapshot,
        "run": run,
        "scope": scope,
    }


def _seed_startable_collaboration_version(
    repository: PostgresSnapshotRepository,
    *,
    prefix: str,
    role_bindings: list[dict[str, object]],
) -> dict[str, object]:
    ids = _insert_product_version(repository, prefix=prefix, status="planning")
    policy = _policy_record(ids, prefix=prefix)
    repository.save_rd_task_executor_policy_record(policy)
    base = _base_snapshot(policy, prefix=prefix)
    base["payload_json"] = {"role_bindings": role_bindings}
    base = repository.freeze_base_policy_snapshot(base)
    requirement_id = f"{prefix}-requirement"
    _insert_requirement(
        repository,
        ids,
        requirement_id=requirement_id,
        status="planned",
        version_id=ids["version"],
    )
    repository.save_assessment_bundle(
        assessment=_accepted_assessment(
            assessment_id=f"{prefix}-assessment",
            requirement_id=requirement_id,
            snapshot_id=str(base["id"]),
        ),
        opinions=[],
    )
    return {**ids, "policy": policy, "base_snapshot": base}


def test_postgres_rd_delivery_facts_are_immutable_and_bundle_rolls_back(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="delivery-facts")
    run = seeded["run"]
    delivery = {
        "id": "delivery-facts-delivery",
        "product_id": seeded["product"],
        "collaboration_run_id": run["id"],
        "product_version_id": seeded["version"],
        "work_item_id": "delivery-facts-work-item",
        "repository_id": "delivery-facts-repository",
        "provider": "gitlab",
        "working_branch": "rd/delivery-facts/work",
        "version_branch": "release/v1",
        "target_branch": "main",
        "local_commit_sha": "local-sha-1",
        "workspace_isolation": {"status": "isolated", "worktree_path": "/tmp/delivery"},
        "outbox_event_id": "delivery-facts-outbox",
    }
    persisted = repository.save_rd_delivery_evidence_record(
        record=delivery,
        record_type="rd_git_delivery",
    )
    assert persisted["evidence_hash"].startswith("sha256:")

    with repository._connect(autocommit=True) as connection:
        with pytest.raises(psycopg.Error):
            connection.execute(
                "UPDATE rd_delivery_evidence_records SET payload_json = '{}'::jsonb WHERE id = %s",
                (delivery["id"],),
            )

    bad_delivery = {**delivery, "id": "delivery-facts-rollback", "outbox_event_id": "bad-outbox"}
    with pytest.raises(psycopg.Error):
        repository.save_rd_git_delivery_bundle(
            delivery=bad_delivery,
            outbox_event={
                "id": "bad-outbox",
                "aggregate_type": "rd_git_delivery",
                "aggregate_id": bad_delivery["id"],
                "event_type": "rd.git_delivery.push_requested",
                "idempotency_key": "bad-outbox",
                "payload": {"delivery_id": bad_delivery["id"]},
                "status": "not-a-valid-outbox-status",
            },
        )

    records = repository.list_rd_delivery_evidence_records(record_type="rd_git_delivery")
    assert [record["id"] for record in records] == [delivery["id"]]


def _decision_record(
    ids: dict[str, object],
    *,
    decision_id: str,
    subject_type: str = "rd_collaboration_run",
    subject_id: str | None = None,
    status: str = "pending",
    expires_at: datetime | None = None,
    answer_actor_selector: dict[str, object] | None = None,
    answer_schema: dict[str, object] | None = None,
) -> dict[str, object]:
    effective_subject_id = subject_id or str(ids["run"]["id"])
    scope_change = subject_type == "rd_scope_change_request"
    options_json = (
        [
            {
                "code": "approve_apply_and_restart",
                "label": "Approve",
                "outcome": "approve",
                "subject_transition": "cancel_and_restart",
                "requires_comment": False,
                "input_schema": {},
                "effect_preview": {},
            },
            {
                "code": "reject_keep_current_scope",
                "label": "Reject",
                "outcome": "reject",
                "subject_transition": "resume",
                "requires_comment": False,
                "input_schema": {},
                "effect_preview": {},
            },
        ]
        if scope_change
        else [
            {
                "code": "continue",
                "label": "Continue",
                "outcome": "approve",
                "subject_transition": "resume",
                "requires_comment": False,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "modules": {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["modules"],
                    "additionalProperties": False,
                },
                "effect_preview": {},
            },
            {
                "code": "more_info",
                "label": "More info",
                "outcome": "request_more_info",
                "subject_transition": "keep_paused",
                "requires_comment": True,
                "input_schema": {},
                "effect_preview": {},
            },
        ]
    )
    return {
        "id": decision_id,
        "brain_app_id": "rd_brain",
        "product_id": ids["product"],
        "subject_type": subject_type,
        "subject_id": effective_subject_id,
        "decision_type": "scope_change" if scope_change else "risk",
        "plan_version": 0,
        "options_json": options_json,
        "options_hash": f"{decision_id}-options-v1",
        "decision_actor_selector": {"user_ids": ["user_admin"]},
        "answer_actor_selector": answer_actor_selector or {"user_ids": ["user_admin"]},
        "answer_schema": answer_schema
        or {
            "type": "object",
            "properties": {"detail": {"type": "string"}},
            "required": ["detail"],
            "additionalProperties": False,
        },
        "status": status,
        "expires_at": expires_at or datetime.now(UTC) + timedelta(hours=1),
        "timeout_policy": "escalate_keep_paused",
        "escalation_target_selector": {"role_codes": ["rd_owner"]},
        "version": 1,
        "created_by": "user_admin",
    }


def test_repository_is_registered_and_crud_keeps_actor_and_executor_identity_separate(
    repository: PostgresSnapshotRepository,
) -> None:
    assert isinstance(repository._rd_collaboration_read_repository, RdCollaborationReadRepository)

    repository.save_rd_role_definition_record(
        {
            "id": "role-dev",
            "brain_app_id": "rd_brain",
            "code": "developer",
            "name": "Developer",
            "created_by": "user_admin",
        }
    )
    repository.save_rd_ai_employee_record(
        {
            "id": "ai-dev",
            "brain_app_id": "rd_brain",
            "code": "ai-developer",
            "name": "AI Developer",
            "created_by": "user_admin",
        }
    )
    repository.save_rd_executor_profile_record(
        {
            "id": "executor-dev",
            "brain_app_id": "rd_brain",
            "code": "codex-dev",
            "name": "Codex Dev",
            "executor_type": "codex",
            "created_by": "user_admin",
        }
    )

    assert repository.get_rd_role_definition("role-dev")["code"] == "developer"
    assert repository.get_rd_ai_employee("ai-dev")["id"] == "ai-dev"
    assert repository.get_rd_executor_profile("executor-dev")["id"] == "executor-dev"
    assert repository.list_rd_role_definitions(status="active")[0]["id"] == "role-dev"


def test_postgres_start_rejects_empty_bindings_without_persisting_a_run(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_startable_collaboration_version(
        repository,
        prefix="start-empty-seats",
        role_bindings=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        start_collaboration_run(
            PostgresRuntimeStore(repository),
            product_version_id=str(seeded["version"]),
            request_id="start-empty-seats",
            scope_version=1,
            actor={"id": "user_admin", "roles": ["admin"]},
        )

    assert exc_info.value.detail["code"] == "RD_ROLE_ASSIGNMENT_REQUIRED"
    assert repository.list_rd_collaboration_runs(product_version_id=str(seeded["version"])) == []
    assert repository.list_rd_run_seats("missing-run") == []
    assert repository.get_product_version(str(seeded["version"]))["status"] == "planning"


def test_postgres_start_freezes_the_resolved_valid_role_seat(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_startable_collaboration_version(
        repository,
        prefix="start-freeze-seats",
        role_bindings=[
            {
                "id": "start-freeze-developer-binding",
                "role_code": "developer",
                "actor_mode": "human",
                "candidate_human_user_ids": ["user_admin"],
                "status": "active",
            }
        ],
    )
    repository.save_rd_role_definition_record(
        {
            "id": "start-freeze-developer-role",
            "brain_app_id": "rd_brain",
            "code": "developer",
            "name": "Developer",
            "assignable_subject_types": ["human_user"],
            "created_by": "user_admin",
        }
    )

    started = start_collaboration_run(
        PostgresRuntimeStore(repository),
        product_version_id=str(seeded["version"]),
        request_id="start-freeze-seats",
        scope_version=1,
        actor={"id": "user_admin", "roles": ["admin"]},
    )

    seats = repository.list_rd_run_seats(started["run"]["id"])
    assert [(seat["role_code"], seat["human_user_id"], seat["status"]) for seat in seats] == [
        ("developer", "user_admin", "active")
    ]
    assert repository.get_product_version(str(seeded["version"]))["status"] == "active"


def test_policy_patch_increments_version_and_enforces_one_active_scope(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="policy-version")
    policy = _policy_record(ids, prefix="policy-version")
    created = repository.save_rd_task_executor_policy_record(policy)
    assert created["policy_version"] == 1

    updated = repository.save_rd_task_executor_policy_record(
        {**policy, "instruction_template": "new instructions"},
        expected_policy_version=1,
    )
    assert updated["policy_version"] == 2

    with pytest.raises(RdCollaborationVersionConflictError) as stale:
        repository.save_rd_task_executor_policy_record(
            {**policy, "instruction_template": "stale"},
            expected_policy_version=1,
        )
    assert stale.value.current_version == 2

    duplicate = {**policy, "id": "policy-version-duplicate", "task_type": "code_review"}
    with pytest.raises(RdCollaborationRepositoryError, match="active") as conflict:
        repository.save_rd_task_executor_policy_record(duplicate)
    assert conflict.value.code == "RD_EXECUTION_POLICY_INVALID"


def test_base_and_assessment_snapshots_are_idempotent_and_immutable(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="snapshot")
    policy = _policy_record(ids, prefix="snapshot")
    repository.save_rd_task_executor_policy_record(policy)
    base_record = _base_snapshot(policy, prefix="snapshot")
    base = repository.freeze_base_policy_snapshot(base_record)
    assert repository.freeze_base_policy_snapshot(base_record)["id"] == base["id"]

    reused = repository.derive_assessment_policy_snapshot(
        base_snapshot_id=str(base["id"]),
        snapshot={
            **base_record,
            "id": "snapshot-derived-empty",
            "parent_snapshot_id": base["id"],
            "snapshot_kind": "assessment_resolved",
            "resolution_context_key": "assessment:snapshot-assessment",
            "resolution_revision": 1,
        },
    )
    assert reused["id"] == base["id"]

    derived = repository.derive_assessment_policy_snapshot(
        base_snapshot_id=str(base["id"]),
        snapshot={
            **base_record,
            "id": "snapshot-derived-1",
            "parent_snapshot_id": base["id"],
            "snapshot_kind": "assessment_resolved",
            "resolution_context_key": "assessment:snapshot-assessment",
            "resolution_revision": 1,
            "content_hash": "snapshot-tightened-hash",
            "payload_json": {"allowed_tools": ["read"], "forbidden_tools": ["deploy"]},
        },
    )
    assert derived["parent_snapshot_id"] == base["id"]

    with repository._connect(autocommit=False) as connection:
        with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
            connection.execute(
                "UPDATE rd_task_executor_policy_snapshots "
                "SET content_hash = 'changed' WHERE id = %s",
                (base["id"],),
            )


def test_assessment_bundle_and_version_merge_preserve_exact_relational_sources(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="merge", status="active")
    policy = _policy_record(ids, prefix="merge")
    repository.save_rd_task_executor_policy_record(policy)
    base = repository.freeze_base_policy_snapshot(_base_snapshot(policy, prefix="merge"))

    sources: list[dict[str, object]] = []
    for number in (2, 1):
        requirement_id = f"merge-requirement-{number}"
        assessment_id = f"merge-assessment-{number}"
        _insert_requirement(
            repository,
            ids,
            requirement_id=requirement_id,
            status="planned",
            version_id=ids["version"],
        )
        repository.save_assessment_bundle(
            assessment=_accepted_assessment(
                assessment_id=assessment_id,
                requirement_id=requirement_id,
                snapshot_id=str(base["id"]),
            ),
            opinions=[
                {
                    "id": f"merge-opinion-{number}",
                    "assessment_id": assessment_id,
                    "role_code": "developer",
                    "input_revision": 1,
                    "strategy_snapshot_id": base["id"],
                    "opinion_round": 1,
                    "conclusion_json": {"result": "accept"},
                }
            ],
        )
        sources.append(
            {
                "id": f"merge-source-{number}",
                "snapshot_id": "merge-snapshot-version",
                "source_snapshot_id": base["id"],
                "requirement_id": requirement_id,
                "assessment_id": assessment_id,
            }
        )

    snapshot = _version_snapshot(
        base_snapshot_id=str(base["id"]),
        ids=ids,
        policy_id=str(policy["id"]),
        prefix="merge",
    )
    persisted = repository.merge_version_policy_snapshot_with_sources(
        snapshot=snapshot,
        sources=sources,
    )
    assert persisted["id"] == snapshot["id"]
    assert [
        row["requirement_id"]
        for row in repository.list_rd_policy_snapshot_sources(str(snapshot["id"]))
    ] == ["merge-requirement-1", "merge-requirement-2"]


def test_create_run_exact_scope_rolls_back_on_deferred_source_mismatch(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="exact-good")
    assert repository.get_rd_collaboration_run(str(seeded["run"]["id"]))["status"] == "running"

    other = _insert_product_version(repository, prefix="exact-bad", status="active")
    policy = _policy_record(other, prefix="exact-bad")
    repository.save_rd_task_executor_policy_record(policy)
    base = repository.freeze_base_policy_snapshot(_base_snapshot(policy, prefix="exact-bad"))
    requirement_id = "exact-bad-requirement"
    _insert_requirement(
        repository,
        other,
        requirement_id=requirement_id,
        status="planned",
        version_id=other["version"],
    )
    assessment_id = "exact-bad-assessment"
    repository.save_assessment_bundle(
        assessment=_accepted_assessment(
            assessment_id=assessment_id,
            requirement_id=requirement_id,
            snapshot_id=str(base["id"]),
        ),
        opinions=[],
    )
    snapshot = _version_snapshot(
        base_snapshot_id=str(base["id"]),
        ids=other,
        policy_id=str(policy["id"]),
        prefix="exact-bad",
    )
    repository.merge_version_policy_snapshot_with_sources(
        snapshot=snapshot,
        sources=[
            {
                "id": "exact-bad-source",
                "snapshot_id": snapshot["id"],
                "source_snapshot_id": base["id"],
                "requirement_id": requirement_id,
                "assessment_id": assessment_id,
            }
        ],
    )
    run = _run_record(
        ids=other,
        snapshot_id=str(snapshot["id"]),
        prefix="exact-bad",
    )
    with pytest.raises(psycopg.errors.RaiseException, match="exact run requirement scope"):
        repository.create_collaboration_run_with_exact_scope(run=run, scope_rows=[])
    assert repository.get_rd_collaboration_run(str(run["id"])) is None


def test_restart_creates_new_generation_without_mutating_terminal_run(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="restart", run_status="failed")
    old_run = repository.get_rd_collaboration_run(str(seeded["run"]["id"]))
    next_run = _run_record(
        ids={"product": seeded["product"], "version": seeded["version"]},
        snapshot_id=str(seeded["version_snapshot"]["id"]),
        prefix="restart",
        status="draft",
        generation=2,
        supersedes_run_id=str(seeded["run"]["id"]),
    )
    next_scope = _run_scope(
        assessment_id=str(seeded["assessment"]),
        final_snapshot_id=str(seeded["base_snapshot"]["id"]),
        requirement_id=str(seeded["requirement"]),
        run_id=str(next_run["id"]),
        prefix="restart-g2",
    )
    restarted = repository.restart_terminal_collaboration_run(
        terminal_run_id=str(seeded["run"]["id"]),
        run=next_run,
        scope_rows=[next_scope],
    )
    assert restarted["run_generation"] == 2
    assert repository.get_rd_collaboration_run(str(seeded["run"]["id"])) == old_run


def test_requirement_assignment_increments_scope_once_and_freezes_during_active_run(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="assign")
    _insert_requirement(
        repository,
        ids,
        requirement_id="assign-requirement",
        status="approved",
    )
    assigned = repository.assign_requirement_to_version_and_increment_scope(
        requirement_id="assign-requirement",
        product_version_id=ids["version"],
        expected_scope_version=1,
    )
    assert assigned["scope_version"] == 2
    replay = repository.assign_requirement_to_version_and_increment_scope(
        requirement_id="assign-requirement",
        product_version_id=ids["version"],
        expected_scope_version=2,
    )
    assert replay["scope_version"] == 2

    _insert_requirement(
        repository,
        ids,
        requirement_id="assign-preselected-requirement",
        status="approved",
        version_id=ids["version"],
    )
    preselected = repository.assign_requirement_to_version_and_increment_scope(
        requirement_id="assign-preselected-requirement",
        product_version_id=ids["version"],
        expected_scope_version=2,
    )
    assert preselected["scope_version"] == 3
    assert preselected["requirement"]["status"] == "planned"

    seeded = _seed_exact_run(repository, prefix="assign-frozen")
    _insert_requirement(
        repository,
        {"product": seeded["product"], "version": seeded["version"]},
        requirement_id="assign-frozen-new",
        status="approved",
    )
    with pytest.raises(RdCollaborationRepositoryError) as frozen:
        repository.assign_requirement_to_version_and_increment_scope(
            requirement_id="assign-frozen-new",
            product_version_id=str(seeded["version"]),
            expected_scope_version=1,
        )
    assert frozen.value.code == "RD_SCOPE_FROZEN"
    assert frozen.value.details["next_action"] == "create_scope_change_request"


def test_batch_schedule_locks_accumulated_capacity_dependencies_and_repository_scope(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="batch-atomic")
    policy = _policy_record(ids, prefix="batch-atomic")
    repository.save_rd_task_executor_policy_record(policy)
    snapshot = repository.freeze_base_policy_snapshot(
        {
            **_base_snapshot(policy, prefix="batch-atomic"),
            "payload_json": {
                "delivery_target": "ready_for_release",
                "git_config": {"repository_ids": ["batch-atomic-repository"]},
                "iteration_config": {"capacity": {"max_requirements": 2}},
            },
        }
    )
    for requirement_id in ("batch-atomic-a-dependency", "batch-atomic-z-dependent"):
        _insert_requirement(repository, ids, requirement_id=requirement_id)
        repository.save_assessment_bundle(
            assessment={
                **_accepted_assessment(
                    assessment_id=f"{requirement_id}-assessment",
                    requirement_id=requirement_id,
                    snapshot_id=str(snapshot["id"]),
                ),
                "dependency_summary": (
                    [{"hard": True, "requirement_id": "batch-atomic-a-dependency"}]
                    if requirement_id.endswith("dependent")
                    else []
                ),
            },
            opinions=[],
        )

    with pytest.raises(RdCollaborationRepositoryError) as repository_failure:
        repository.batch_schedule_requirements_into_planning_version(
            product_id=ids["product"],
            product_version_id=ids["version"],
            requirement_ids=["batch-atomic-a-dependency", "batch-atomic-z-dependent"],
            audit_events=[],
        )
    assert repository_failure.value.code == "ITERATION_CONSTRAINT_UNSATISFIED"
    assert "repository_incompatible" in str(repository_failure.value)
    assert repository.get_product_version(ids["version"])["scope_version"] == 1

    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO product_git_repositories (
              id, product_id, repo_type, name, remote_url, git_provider, default_branch, status
            ) VALUES (%s, %s, 'service', 'batch', 'https://example.invalid/batch.git',
                      'gitlab', 'main', 'active')
            """,
            ("batch-atomic-repository", ids["product"]),
        )
        connection.execute(
            """
            INSERT INTO product_version_branch_configs (
              id, product_id, version_id, repository_id, base_branch, working_branch
            ) VALUES ('batch-atomic-branch', %s, %s, 'batch-atomic-repository', 'main',
                      'feature/batch-atomic')
            """,
            (ids["product"], ids["version"]),
        )

    scheduled = repository.batch_schedule_requirements_into_planning_version(
        product_id=ids["product"],
        product_version_id=ids["version"],
        requirement_ids=["batch-atomic-a-dependency", "batch-atomic-z-dependent"],
        audit_events=[],
    )
    assert [item["id"] for item in scheduled["requirements"]] == [
        "batch-atomic-a-dependency",
        "batch-atomic-z-dependent",
    ]
    assert scheduled["version"]["scope_version"] == 3

    _insert_requirement(repository, ids, requirement_id="batch-atomic-third")
    repository.save_assessment_bundle(
        assessment=_accepted_assessment(
            assessment_id="batch-atomic-third-assessment",
            requirement_id="batch-atomic-third",
            snapshot_id=str(snapshot["id"]),
        ),
        opinions=[],
    )
    with pytest.raises(RdCollaborationRepositoryError) as capacity_failure:
        repository.batch_schedule_requirements_into_planning_version(
            product_id=ids["product"],
            product_version_id=ids["version"],
            requirement_ids=["batch-atomic-third"],
            audit_events=[],
        )
    assert capacity_failure.value.code == "ITERATION_CONSTRAINT_UNSATISFIED"
    assert "capacity_exhausted" in str(capacity_failure.value)
    assert (
        repository.load_requirements()["requirements"]["batch-atomic-third"]["status"] == "approved"
    )
    assert repository.get_product_version(ids["version"])["scope_version"] == 3


def test_batch_schedule_api_uses_postgres_atomic_membership_write(
    repository: PostgresSnapshotRepository,
) -> None:
    ids = _insert_product_version(repository, prefix="batch-api")
    policy = _policy_record(ids, prefix="batch-api")
    repository.save_rd_task_executor_policy_record(policy)
    snapshot = repository.freeze_base_policy_snapshot(_base_snapshot(policy, prefix="batch-api"))
    requirement_ids = ["batch-api-one", "batch-api-two"]
    for requirement_id in requirement_ids:
        _insert_requirement(repository, ids, requirement_id=requirement_id)
        repository.save_assessment_bundle(
            assessment=_accepted_assessment(
                assessment_id=f"{requirement_id}-assessment",
                requirement_id=requirement_id,
                snapshot_id=str(snapshot["id"]),
            ),
            opinions=[],
        )

    headers = auth_headers()
    original_store = app.state.store
    app.state.store = PostgresRuntimeStore(repository)
    try:
        response = TestClient(app).post(
            "/api/requirements/batch-schedule",
            json={
                "product_id": ids["product"],
                "requirement_ids": requirement_ids,
                "version_id": ids["version"],
            },
            headers=headers,
        )
    finally:
        app.state.store = original_store

    assert response.status_code == 200, response.text
    assert response.json()["data"]["updated_count"] == 2
    assert repository.get_product_version(ids["version"])["scope_version"] == 3
    scheduled = repository.load_requirements()["requirements"]
    assert all(
        scheduled[requirement_id]["status"] == "planned" for requirement_id in requirement_ids
    )


def test_requirement_revision_scope_change_is_rejected_while_run_is_active(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="revision-frozen")
    requirement = repository.load_requirements()["requirements"][seeded["requirement"]]

    with pytest.raises(RdCollaborationRepositoryError) as frozen:
        repository.save_requirement_revision_with_assessment_supersession(
            {
                **requirement,
                "assessment_revision": 2,
                "content": "scope-changing revision",
                "status": "submitted",
            }
        )

    assert frozen.value.code == "RD_SCOPE_FROZEN"
    assert frozen.value.details["next_action"] == "create_scope_change_request"
    assert repository.get_product_version(seeded["version"])["scope_version"] == 1
    assert (
        repository.load_requirements()["requirements"][seeded["requirement"]]["status"] == "planned"
    )


def test_requirement_revision_increments_scope_but_display_only_edit_does_not(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="revision-scope", run_status="failed")
    version = repository.get_product_version(seeded["version"])
    assert version is not None
    repository.save_product_config_record("product_versions", {**version, "status": "planning"})
    requirement = repository.load_requirements()["requirements"][seeded["requirement"]]

    repository.save_requirement_revision_with_assessment_supersession(
        {
            **requirement,
            "assessment_revision": 2,
            "content": "scope-changing revision",
            "status": "submitted",
        }
    )

    assert repository.get_product_version(seeded["version"])["scope_version"] == 2
    revised = repository.load_requirements()["requirements"][seeded["requirement"]]
    repository.save_requirement_record({**revised, "approval_comment": "display-only"})
    assert repository.get_product_version(seeded["version"])["scope_version"] == 2


def test_requirement_patch_api_rejects_scope_change_while_run_is_active(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="revision-api-frozen")
    headers = auth_headers()
    original_store = app.state.store
    app.state.store = PostgresRuntimeStore(repository)
    try:
        response = TestClient(app).patch(
            f"/api/requirements/{seeded['requirement']}",
            json={"content": "change frozen iteration scope"},
            headers=headers,
        )
    finally:
        app.state.store = original_store

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "RD_SCOPE_FROZEN"
    assert response.headers["x-trace-id"]
    assert repository.get_product_version(seeded["version"])["scope_version"] == 1
    assert (
        repository.load_requirements()["requirements"][seeded["requirement"]]["status"] == "planned"
    )


def test_branch_baseline_change_is_rejected_while_run_is_active(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="branch-frozen")
    branch_id = "branch-frozen-config"
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO product_git_repositories (
              id, product_id, repo_type, name, remote_url, git_provider, default_branch, status
            ) VALUES (%s, %s, 'service', 'branch-frozen', 'https://example.invalid/branch-frozen.git',
                      'gitlab', 'main', 'active')
            """,
            ("branch-frozen-repository", seeded["product"]),
        )
        connection.execute(
            """
            INSERT INTO product_version_branch_configs (
              id, product_id, version_id, repository_id, base_branch, working_branch
            ) VALUES (%s, %s, %s, %s, 'main', 'feature/frozen')
            """,
            (branch_id, seeded["product"], seeded["version"], "branch-frozen-repository"),
        )
    branch_config = repository.get_product_version_branch_config(branch_id)
    assert branch_config is not None

    with pytest.raises(RdCollaborationRepositoryError) as frozen:
        repository.save_product_config_record(
            "product_version_branch_configs",
            {**branch_config, "base_branch": "release/frozen"},
        )

    assert frozen.value.code == "RD_SCOPE_FROZEN"
    assert repository.get_product_version(seeded["version"])["scope_version"] == 1
    assert repository.get_product_version_branch_config(branch_id)["base_branch"] == "main"


def test_branch_baseline_change_increments_scope_but_description_does_not(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="branch-scope", run_status="failed")
    version = repository.get_product_version(seeded["version"])
    assert version is not None
    repository.save_product_config_record("product_versions", {**version, "status": "planning"})
    branch_id = "branch-scope-config"
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO product_git_repositories (
              id, product_id, repo_type, name, remote_url, git_provider, default_branch, status
            ) VALUES (%s, %s, 'service', 'branch-scope', 'https://example.invalid/branch-scope.git',
                      'gitlab', 'main', 'active')
            """,
            ("branch-scope-repository", seeded["product"]),
        )
        connection.execute(
            """
            INSERT INTO product_version_branch_configs (
              id, product_id, version_id, repository_id, base_branch, working_branch
            ) VALUES (%s, %s, %s, %s, 'main', 'feature/scope')
            """,
            (branch_id, seeded["product"], seeded["version"], "branch-scope-repository"),
        )
    branch_config = repository.get_product_version_branch_config(branch_id)
    assert branch_config is not None

    repository.save_product_config_record(
        "product_version_branch_configs",
        {**branch_config, "base_branch": "release/scope"},
    )
    assert repository.get_product_version(seeded["version"])["scope_version"] == 2
    changed = repository.get_product_version_branch_config(branch_id)
    repository.save_product_config_record(
        "product_version_branch_configs",
        {**changed, "description": "display-only"},
    )
    assert repository.get_product_version(seeded["version"])["scope_version"] == 2


def test_scope_change_request_is_idempotent_pauses_run_and_reject_resumes_it(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="scope-reject")
    decision = _decision_record(
        seeded,
        decision_id="scope-reject-decision",
        subject_type="rd_scope_change_request",
        subject_id="scope-reject-request",
    )
    request = {
        "id": "scope-reject-request",
        "product_version_id": seeded["version"],
        "request_id": "scope-reject-key",
        "source_run_id": seeded["run"]["id"],
        "expected_scope_version": 1,
        "expected_run_generation": 1,
        "operations_json": [
            {
                "op": "remove_requirement",
                "requirement_id": seeded["requirement"],
                "destination": "approved_pool",
            }
        ],
        "operations_hash": "scope-reject-hash",
        "reason": "remove requirement",
        "decision_request_id": decision["id"],
        "requested_by": "user_admin",
    }
    operations = [
        {
            "id": "scope-reject-operation",
            "scope_change_request_id": request["id"],
            "position": 0,
            "op": "remove_requirement",
            "requirement_id": seeded["requirement"],
            "destination": "approved_pool",
        }
    ]
    created = repository.create_scope_change_request(
        request=request,
        operations=operations,
        decision_request=decision,
    )
    replay = repository.create_scope_change_request(
        request=request,
        operations=operations,
        decision_request=decision,
    )
    assert replay["id"] == created["id"]
    assert (
        repository.list_rd_scope_change_request_operations(created["id"])[0]["id"]
        == "scope-reject-operation"
    )
    paused = repository.get_rd_collaboration_run(str(seeded["run"]["id"]))
    assert paused["status"] == "waiting_human"
    assert paused["resume_state"] == "running"

    result = repository.apply_scope_change_bundle(
        scope_change_request_id=str(request["id"]),
        decision="reject_keep_current_scope",
        decided_by="user_admin",
        expected_decision_version=1,
    )
    assert result["scope_change_request"]["status"] == "rejected"
    assert result["run"]["status"] == "running"
    assert result["product_version"]["scope_version"] == 1


def test_invalid_scope_change_is_rejected_before_it_creates_a_pause(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="scope-preflight")
    decision = _decision_record(
        seeded,
        decision_id="scope-preflight-decision",
        subject_type="rd_scope_change_request",
        subject_id="scope-preflight-request",
    )
    request = {
        "id": "scope-preflight-request",
        "product_version_id": seeded["version"],
        "request_id": "scope-preflight-key",
        "source_run_id": seeded["run"]["id"],
        "expected_scope_version": 1,
        "expected_run_generation": 1,
        "operations_json": [
            {
                "op": "replace_requirement_snapshot",
                "requirement_id": "missing-requirement",
                "requirement_revision": 1,
                "assessment_id": "missing-assessment",
                "final_strategy_snapshot_id": seeded["base_snapshot"]["id"],
            }
        ],
        "operations_hash": "scope-preflight-hash",
        "reason": "invalid replacement",
        "decision_request_id": decision["id"],
        "requested_by": "user_admin",
    }

    with pytest.raises(RdCollaborationRepositoryError) as invalid:
        repository.create_scope_change_request(
            request=request,
            operations=[
                {
                    "id": "scope-preflight-operation",
                    "scope_change_request_id": request["id"],
                    "position": 0,
                    **request["operations_json"][0],
                }
            ],
            decision_request=decision,
        )

    assert invalid.value.code == "RD_SCOPE_CHANGE_INVALID"
    assert repository.get_rd_collaboration_run(str(seeded["run"]["id"]))["status"] == "running"
    assert repository.get_rd_scope_change_request(request["id"]) is None


def test_concurrent_scope_change_same_request_replays_and_different_request_fences(
    repository: PostgresSnapshotRepository,
) -> None:
    same = _seed_exact_run(repository, prefix="scope-race-same")

    def create_request(
        seeded: dict[str, object],
        *,
        suffix: str,
        request_key: str,
    ) -> dict[str, object]:
        request_id = f"scope-race-{suffix}"
        decision = _decision_record(
            seeded,
            decision_id=f"{request_id}-decision",
            subject_type="rd_scope_change_request",
            subject_id=request_id,
        )
        request = {
            "id": request_id,
            "product_version_id": seeded["version"],
            "request_id": request_key,
            "source_run_id": seeded["run"]["id"],
            "expected_scope_version": 1,
            "expected_run_generation": 1,
            "operations_json": [
                {
                    "op": "remove_requirement",
                    "requirement_id": seeded["requirement"],
                    "destination": "approved_pool",
                }
            ],
            "operations_hash": f"{request_id}-hash",
            "reason": "concurrency fence",
            "decision_request_id": decision["id"],
            "requested_by": "user_admin",
        }
        operation = {
            "id": f"{request_id}-operation",
            "scope_change_request_id": request_id,
            "position": 0,
            "op": "remove_requirement",
            "requirement_id": seeded["requirement"],
            "destination": "approved_pool",
        }
        return {
            "request": request,
            "decision_request": decision,
            "operations": [operation],
        }

    same_command = create_request(same, suffix="same", request_key="same-key")
    with ThreadPoolExecutor(max_workers=2) as executor:
        same_results = list(
            executor.map(
                lambda _: repository.create_scope_change_request(**same_command),
                range(2),
            )
        )
    assert {row["id"] for row in same_results} == {"scope-race-same"}

    different = _seed_exact_run(repository, prefix="scope-race-different")
    commands = [
        create_request(different, suffix="different-a", request_key="different-a"),
        create_request(different, suffix="different-b", request_key="different-b"),
    ]

    def submit(command: dict[str, object]) -> dict[str, object] | str:
        try:
            return repository.create_scope_change_request(**command)
        except RdCollaborationRepositoryError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        different_results = list(executor.map(submit, commands))
    assert sum(isinstance(result, dict) for result in different_results) == 1
    assert different_results.count("RD_SCOPE_FROZEN") == 1


def test_scope_change_approval_cancels_generation_and_increments_scope_exactly_once(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="scope-apply")
    new_requirement_id = "scope-apply-new-requirement"
    _insert_requirement(
        repository,
        {"product": seeded["product"], "version": seeded["version"]},
        requirement_id=new_requirement_id,
        status="approved",
    )
    new_assessment_id = "scope-apply-new-assessment"
    repository.save_assessment_bundle(
        assessment=_accepted_assessment(
            assessment_id=new_assessment_id,
            requirement_id=new_requirement_id,
            snapshot_id=str(seeded["base_snapshot"]["id"]),
        ),
        opinions=[],
    )
    repository.save_rd_work_item_record(
        {
            "id": "scope-apply-work",
            "collaboration_run_id": seeded["run"]["id"],
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "implement",
            "objective": "implement",
            "status": "running",
            "idempotency_key": "scope-apply-work",
            "lease_owner": "worker-a",
            "lease_expires_at": datetime.now(UTC) + timedelta(minutes=10),
        }
    )
    repository.save_work_item_attempt_bundle(
        work_item_id="scope-apply-work",
        expected_statuses=["running"],
        next_status="running",
        attempt={
            "id": "scope-apply-attempt",
            "work_item_id": "scope-apply-work",
            "attempt_no": 1,
            "idempotency_key": "scope-apply-attempt",
            "status": "running",
        },
    )
    decision = _decision_record(
        seeded,
        decision_id="scope-apply-decision",
        subject_type="rd_scope_change_request",
        subject_id="scope-apply-request",
    )
    request = {
        "id": "scope-apply-request",
        "product_version_id": seeded["version"],
        "request_id": "scope-apply-key",
        "source_run_id": seeded["run"]["id"],
        "expected_scope_version": 1,
        "expected_run_generation": 1,
        "operations_json": [
            {
                "op": "add_requirement",
                "requirement_id": new_requirement_id,
                "requirement_revision": 1,
                "assessment_id": new_assessment_id,
                "final_strategy_snapshot_id": seeded["base_snapshot"]["id"],
            }
        ],
        "operations_hash": "scope-apply-hash",
        "reason": "add requirement",
        "decision_request_id": decision["id"],
        "requested_by": "user_admin",
    }
    repository.create_scope_change_request(
        request=request,
        decision_request=decision,
        operations=[
            {
                "id": "scope-apply-operation",
                "scope_change_request_id": request["id"],
                "position": 0,
                "op": "add_requirement",
                "requirement_id": new_requirement_id,
                "requirement_revision": 1,
                "assessment_id": new_assessment_id,
                "final_strategy_snapshot_id": seeded["base_snapshot"]["id"],
            }
        ],
    )

    result = repository.apply_scope_change_bundle(
        scope_change_request_id=str(request["id"]),
        decision="approve_apply_and_restart",
        decided_by="user_admin",
        expected_decision_version=1,
    )
    assert result["run"]["status"] == "cancelled"
    assert result["run"]["completion_reason"] == "scope_change"
    assert result["product_version"]["scope_version"] == 2
    assert result["scope_change_request"]["applied_scope_version"] == 2
    assert repository.get_rd_work_item("scope-apply-work")["status"] == "cancelled"
    assert repository.get_rd_work_item_attempt("scope-apply-attempt")["status"] == "cancelled"

    replay = repository.apply_scope_change_bundle(
        scope_change_request_id=str(request["id"]),
        decision="approve_apply_and_restart",
        decided_by="user_admin",
        expected_decision_version=1,
    )
    assert replay["product_version"]["scope_version"] == 2


@pytest.mark.parametrize("version_status", ["ready_for_release", "deploying"])
def test_ready_boundary_scope_change_returns_followup_resolution(
    repository: PostgresSnapshotRepository,
    version_status: str,
) -> None:
    seeded = _seed_exact_run(
        repository,
        prefix=f"ready-{version_status}",
        run_status="completed",
        version_status=version_status,
    )
    decision = _decision_record(
        seeded,
        decision_id=f"ready-{version_status}-decision",
        subject_type="rd_scope_change_request",
        subject_id=f"ready-{version_status}-request",
    )
    with pytest.raises(RdCollaborationRepositoryError) as frozen:
        repository.create_scope_change_request(
            request={
                "id": f"ready-{version_status}-request",
                "product_version_id": seeded["version"],
                "request_id": f"ready-{version_status}-key",
                "source_run_id": seeded["run"]["id"],
                "expected_scope_version": 1,
                "expected_run_generation": 1,
                "operations_json": [],
                "operations_hash": f"ready-{version_status}-hash",
                "reason": "late change",
                "decision_request_id": decision["id"],
                "requested_by": "user_admin",
            },
            decision_request=decision,
            operations=[],
        )
    assert frozen.value.code == "RD_SCOPE_FROZEN"
    assert frozen.value.details == {
        "retryable": False,
        "resolution": "new_planning_version",
        "next_action": "create_followup_requirement",
    }


def test_claim_ready_work_item_is_atomic(repository: PostgresSnapshotRepository) -> None:
    seeded = _seed_exact_run(repository, prefix="claim")
    repository.save_rd_work_item_record(
        {
            "id": "claim-work",
            "collaboration_run_id": seeded["run"]["id"],
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "claim me",
            "objective": "claim me",
            "status": "ready",
            "idempotency_key": "claim-work",
        }
    )

    first = repository.claim_ready_work_item("claim-work", lease_owner="worker-a")
    second = repository.claim_ready_work_item("claim-work", lease_owner="worker-b")
    assert first["lease_owner"] == "worker-a"
    assert second is None


def test_postgres_review_approval_promotes_blocked_successor_before_its_claim(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="dependency-promotion")
    run_id = str(seeded["run"]["id"])
    repository.save_rd_run_seat_record(
        {
            "id": "dependency-owner-seat",
            "collaboration_run_id": run_id,
            "role_code": "developer",
            "subject_type": "human_user",
            "human_user_id": "user_admin",
        }
    )
    repository.save_rd_run_seat_record(
        {
            "id": "dependency-reviewer-seat",
            "collaboration_run_id": run_id,
            "role_code": "tester",
            "subject_type": "human_user",
            "human_user_id": "user_reviewer",
        }
    )
    repository.save_rd_work_item_record(
        {
            "id": "dependency-root",
            "collaboration_run_id": run_id,
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "root",
            "objective": "complete root",
            "owner_seat_id": "dependency-owner-seat",
            "reviewer_seat_id": "dependency-reviewer-seat",
            "status": "reviewing",
            "idempotency_key": "dependency-root",
        }
    )
    repository.save_rd_work_item_record(
        {
            "id": "dependency-successor",
            "collaboration_run_id": run_id,
            "plan_version": 1,
            "work_item_type": "testing",
            "title": "successor",
            "objective": "verify root",
            "owner_seat_id": "dependency-owner-seat",
            "reviewer_seat_id": "dependency-reviewer-seat",
            "status": "blocked",
            "idempotency_key": "dependency-successor",
        }
    )
    repository.save_rd_work_item_dependency_record(
        {
            "id": "dependency-root-to-successor",
            "collaboration_run_id": run_id,
            "plan_version": 1,
            "predecessor_work_item_id": "dependency-root",
            "successor_work_item_id": "dependency-successor",
        }
    )
    repository.save_work_item_attempt_bundle(
        work_item_id="dependency-root",
        expected_statuses=["reviewing"],
        next_status="reviewing",
        attempt={
            "id": "dependency-root-attempt",
            "work_item_id": "dependency-root",
            "attempt_no": 1,
            "idempotency_key": "dependency-root-attempt",
            "status": "completed",
        },
    )
    store = PostgresRuntimeStore(repository)

    approved = review_work_item(
        store,
        work_item_id="dependency-root",
        decision="approve",
        comment=None,
        actor={"id": "user_reviewer", "roles": ["reviewer"]},
        version=2,
        idempotency_key="approve-dependency-root",
    )

    assert approved["work_item"]["status"] == "completed"
    successor = repository.get_rd_work_item("dependency-successor")
    assert successor is not None
    assert successor["status"] == "ready"
    claimed = claim_work_item(
        store,
        work_item_id="dependency-successor",
        actor={"id": "user_admin", "roles": ["admin"]},
        expected_version=int(successor["version"]),
        lease_seconds=60,
        idempotency_key="claim-dependency-successor",
    )
    assert claimed["work_item"]["status"] == "running"


def test_execution_worker_projects_committed_work_item_event_to_postgres_graph_cursor(
    repository: PostgresSnapshotRepository,
) -> None:
    """The production worker must advance the durable cursor from a scheduler event.

    The scheduler's review transaction is deliberately the producer here: this
    proves the LangGraph runtime is reachable from the real command/event path,
    instead of only from a runtime unit test.
    """
    seeded = _seed_exact_run(repository, prefix="graph-worker-projection")
    run_id = str(seeded["run"]["id"])
    repository.save_rd_run_seat_record(
        {
            "id": "graph-worker-owner-seat",
            "collaboration_run_id": run_id,
            "role_code": "developer",
            "subject_type": "human_user",
            "human_user_id": "user_admin",
        }
    )
    repository.save_rd_run_seat_record(
        {
            "id": "graph-worker-reviewer-seat",
            "collaboration_run_id": run_id,
            "role_code": "tester",
            "subject_type": "human_user",
            "human_user_id": "user_reviewer",
        }
    )
    repository.save_rd_work_item_record(
        {
            "id": "graph-worker-work-item",
            "collaboration_run_id": run_id,
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "advance collaboration cursor",
            "objective": "advance collaboration cursor",
            "owner_seat_id": "graph-worker-owner-seat",
            "reviewer_seat_id": "graph-worker-reviewer-seat",
            "status": "reviewing",
            "idempotency_key": "graph-worker-work-item",
        }
    )
    repository.save_work_item_attempt_bundle(
        work_item_id="graph-worker-work-item",
        expected_statuses=["reviewing"],
        next_status="reviewing",
        attempt={
            "id": "graph-worker-attempt",
            "work_item_id": "graph-worker-work-item",
            "attempt_no": 1,
            "idempotency_key": "graph-worker-attempt",
            "status": "completed",
        },
    )
    store = PostgresRuntimeStore(repository)

    reviewed = review_work_item(
        store,
        work_item_id="graph-worker-work-item",
        decision="approve",
        comment=None,
        actor={"id": "user_reviewer", "roles": ["reviewer"]},
        version=2,
        idempotency_key="graph-worker-approve",
    )
    assert reviewed["work_item"]["status"] == "completed"
    scheduler_event = next(
        event
        for event in repository.list_rd_collaboration_events(run_id)
        if event["event_key"] == "review:graph-worker-work-item:graph-worker-approve"
    )

    checkpointer = build_checkpointer(
        SimpleNamespace(
            is_test_env=False,
            persistence_mode="postgres",
            database_url=repository.database_url,
        )
    )
    try:
        runtime = RdCollaborationGraphRuntime(store, checkpointer=checkpointer)
        runtime.fail_next_checkpoint_write()
        failed = run_execution_worker_iteration(
            store,
            worker_id="graph-projection-worker",
            rd_collaboration_graph_runtime=runtime,
        )
        recovered = run_execution_worker_iteration(
            store,
            worker_id="graph-projection-worker",
            rd_collaboration_graph_runtime=runtime,
        )
        settled = run_execution_worker_iteration(
            store,
            worker_id="graph-projection-worker",
            rd_collaboration_graph_runtime=runtime,
        )
        assert failed["rd_collaboration_graph_event_count"] == 0
        assert recovered["rd_collaboration_graph_event_count"] == 1
        assert settled["rd_collaboration_graph_event_count"] == 0

        checkpoint = build_rd_collaboration_graph(checkpointer).get_state(
            {"configurable": {"thread_id": rd_collaboration_thread_id(run_id)}}
        )
    finally:
        checkpointer.conn.close()

    assert checkpoint.values["graph_definition"] == "rd_collaboration"
    assert checkpoint.values["graph_version"] == "v1"
    assert checkpoint.values["processed_event_ids"] == [f"event-projection:{scheduler_event['id']}"]
    graph_events = [
        event
        for event in repository.list_rd_collaboration_events(run_id)
        if event["event_key"] == f"graph-event:event-projection:{scheduler_event['id']}"
    ]
    assert len(graph_events) == 1
    assert (
        len(
            repository.list_execution_outbox_events(
                aggregate_type="rd_collaboration_run",
                aggregate_id=run_id,
                status=None,
            )
        )
        == 0
    )
    assert (
        len(
            [
                item
                for item in repository.list_role_feedback_records(run_id)
                if item["source_event_id"] == f"event-projection:{scheduler_event['id']}"
            ]
        )
        == 1
    )


def test_concurrent_claim_uses_skip_locked_and_only_one_worker_wins(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="claim-race")
    repository.save_rd_work_item_record(
        {
            "id": "claim-race-work",
            "collaboration_run_id": seeded["run"]["id"],
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "claim race",
            "objective": "claim race",
            "status": "ready",
            "idempotency_key": "claim-race-work",
        }
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                repository.claim_ready_work_item,
                "claim-race-work",
                lease_owner=f"worker-{number}",
            )
            for number in (1, 2)
        ]
        results = [future.result(timeout=10) for future in futures]
    assert sum(result is not None for result in results) == 1


def test_high_risk_cancel_continue_fences_old_attempt_and_requires_new_attempt(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="cancel-high-risk")
    repository.save_rd_work_item_record(
        {
            "id": "cancel-high-risk-work",
            "collaboration_run_id": seeded["run"]["id"],
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "sensitive change",
            "objective": "sensitive change",
            "status": "ready",
            "risk_level": "high",
            "idempotency_key": "cancel-high-risk-work",
        }
    )
    claimed = repository.claim_ready_work_item(
        "cancel-high-risk-work",
        lease_owner="worker-old",
        attempt={
            "id": "cancel-high-risk-attempt-1",
            "work_item_id": "cancel-high-risk-work",
            "attempt_no": 1,
            "idempotency_key": "cancel-high-risk-attempt-1",
            "status": "running",
        },
    )
    decision = _decision_record(
        seeded,
        decision_id="cancel-high-risk-decision",
        subject_type="rd_work_item",
        subject_id="cancel-high-risk-work",
    )
    decision["options_json"] = [
        {
            "code": "continue_ready",
            "label": "Continue with a new attempt",
            "outcome": "reject",
            "subject_transition": "ready",
            "requires_comment": False,
            "input_schema": {},
            "effect_preview": {},
        }
    ]
    decision["options_hash"] = "cancel-high-risk-options-v1"
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO ai_tasks (
              id, brain_app_id, requirement_id, task_type, title, status,
              product_id, version_id, created_by, collaboration_run_id, work_item_id
            ) VALUES (%s, 'rd_brain', %s, 'development_planning', 'linked high-risk', 'running',
                      %s, %s, 'user_admin', %s, %s)
            """,
            (
                "cancel-high-risk-task",
                seeded["requirement"],
                seeded["product"],
                seeded["version"],
                seeded["run"]["id"],
                "cancel-high-risk-work",
            ),
        )
        connection.execute(
            """
            INSERT INTO human_reviews (id, ai_task_id, stage, status)
            VALUES ('cancel-high-risk-review', 'cancel-high-risk-task', 'execution', 'pending')
            """
        )
        connection.execute(
            """
            INSERT INTO execution_outbox_events (
              id, aggregate_type, aggregate_id, event_type, idempotency_key, status
            ) VALUES (
              'cancel-high-risk-processing', 'ai_task', 'cancel-high-risk-task',
              'runner.execute', 'cancel-high-risk-processing', 'processing'
            )
            """
        )
    paused = repository.cancel_work_item_bundle(
        work_item_id="cancel-high-risk-work",
        expected_version=int(claimed["version"]),
        high_risk=True,
        decision_request=decision,
    )
    assert paused["work_item"]["status"] == "waiting_human"
    assert paused["attempt"]["status"] == "waiting_human"
    assert paused["work_item"]["lease_owner"] is None
    with repository._connect() as connection:
        task_status = connection.execute(
            "SELECT status FROM ai_tasks WHERE id = 'cancel-high-risk-task'"
        ).fetchone()[0]
        review_status = connection.execute(
            "SELECT status FROM human_reviews WHERE id = 'cancel-high-risk-review'"
        ).fetchone()[0]
        outbox_types = {
            row[0]
            for row in connection.execute(
                "SELECT event_type FROM execution_outbox_events "
                "WHERE aggregate_id = 'cancel-high-risk-work' "
                "OR id LIKE 'outbox:work-item:cancel-high-risk-work:%'"
            ).fetchall()
        }
    assert task_status == "cancelled"
    assert review_status == "cancelled"
    assert {"rd.work_item.cancel_runner", "rd.work_item.reconcile_cancellation"}.issubset(
        outbox_types
    )

    continued = repository.apply_decision_bundle(
        decision_request_id="cancel-high-risk-decision",
        selected_option_code="continue_ready",
        input_json=None,
        comment=None,
        decided_by="user_admin",
        expected_version=1,
    )
    assert continued["work_item"]["status"] == "ready"
    assert (
        repository.get_rd_work_item_attempt("cancel-high-risk-attempt-1")["status"] == "cancelled"
    )

    reclaimed = repository.claim_ready_work_item(
        "cancel-high-risk-work",
        lease_owner="worker-new",
        attempt={
            "id": "cancel-high-risk-attempt-2",
            "work_item_id": "cancel-high-risk-work",
            "attempt_no": 2,
            "idempotency_key": "cancel-high-risk-attempt-2",
            "status": "running",
        },
    )
    assert reclaimed["attempt"]["id"] == "cancel-high-risk-attempt-2"
    assert reclaimed["lease_owner"] == "worker-new"


def test_high_risk_cancel_rejects_late_task_and_review_persistence_writes(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="cancel-stale-persistence")
    work_item_id = "cancel-stale-persistence-work"
    task_id = "cancel-stale-persistence-task"
    review_id = "cancel-stale-persistence-review"
    attempt_id = "cancel-stale-persistence-attempt"
    repository.save_rd_work_item_record(
        {
            "id": work_item_id,
            "collaboration_run_id": seeded["run"]["id"],
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "fenced delivery",
            "objective": "fenced delivery",
            "status": "ready",
            "risk_level": "high",
            "idempotency_key": work_item_id,
        }
    )
    claimed = repository.claim_ready_work_item(
        work_item_id,
        lease_owner="worker-old",
        attempt={
            "id": attempt_id,
            "work_item_id": work_item_id,
            "attempt_no": 1,
            "idempotency_key": attempt_id,
            "status": "running",
        },
    )
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO ai_tasks (
              id, brain_app_id, requirement_id, task_type, title, status,
              product_id, version_id, created_by, collaboration_run_id, work_item_id
            ) VALUES (%s, 'rd_brain', %s, 'development_planning', 'fenced delivery', 'running',
                      %s, %s, 'user_admin', %s, %s)
            """,
            (
                task_id,
                seeded["requirement"],
                seeded["product"],
                seeded["version"],
                seeded["run"]["id"],
                work_item_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO human_reviews (id, ai_task_id, stage, status)
            VALUES (%s, %s, 'execution', 'pending')
            """,
            (review_id, task_id),
        )

    decision = _decision_record(
        seeded,
        decision_id="cancel-stale-persistence-decision",
        subject_type="rd_work_item",
        subject_id=work_item_id,
    )
    cancelled = repository.cancel_work_item_bundle(
        work_item_id=work_item_id,
        expected_version=int(claimed["version"]),
        high_risk=True,
        decision_request=decision,
    )
    assert cancelled["work_item"]["status"] == "waiting_human"

    stale_task = repository.load_ai_tasks()["ai_tasks"][task_id]
    stale_task.update(
        {
            "status": "completed",
            "current_step": "completed",
            "output_json": {"late_worker": True},
        }
    )
    stale_review = repository.load_workflow_runtime()["human_reviews"][review_id]
    stale_review.update(
        {
            "status": "approved",
            "decision_reason": "late worker completion",
        }
    )

    repository.save_task_state_records(
        task=stale_task,
        audit_events=[],
        reviews=[stale_review],
    )
    repository.save_review_decision_records(
        task=stale_task,
        review=stale_review,
        graph_run=None,
        checkpoint=None,
        audit_events=[],
    )

    with repository._connect() as connection:
        task_status = connection.execute(
            "SELECT status FROM ai_tasks WHERE id = %s", (task_id,)
        ).fetchone()[0]
        review_status = connection.execute(
            "SELECT status FROM human_reviews WHERE id = %s", (review_id,)
        ).fetchone()[0]
    assert task_status == "cancelled"
    assert review_status == "cancelled"
    assert repository.get_rd_work_item_attempt(attempt_id)["status"] == "waiting_human"
    persisted_item = repository.get_rd_work_item(work_item_id)
    assert persisted_item["status"] == "waiting_human"
    assert persisted_item["lease_owner"] is None
    assert persisted_item["suspended_decision_request_id"] == decision["id"]
    assert repository.get_rd_collaboration_run(seeded["run"]["id"])["status"] == "running"


def test_low_risk_cancellation_fences_linked_task_review_and_external_work(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="cancel-linked")
    repository.save_rd_work_item_record(
        {
            "id": "cancel-linked-work",
            "collaboration_run_id": seeded["run"]["id"],
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "cancel linked delivery",
            "objective": "cancel linked delivery",
            "status": "ready",
            "risk_level": "low",
            "idempotency_key": "cancel-linked-work",
        }
    )
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO ai_tasks (
              id, brain_app_id, requirement_id, task_type, title, status,
              product_id, version_id, created_by, collaboration_run_id, work_item_id
            ) VALUES (%s, 'rd_brain', %s, 'development_planning', 'linked', 'running',
                      %s, %s, 'user_admin', %s, %s)
            """,
            (
                "cancel-linked-task",
                seeded["requirement"],
                seeded["product"],
                seeded["version"],
                seeded["run"]["id"],
                "cancel-linked-work",
            ),
        )
        connection.execute(
            """
            INSERT INTO human_reviews (id, ai_task_id, stage, status)
            VALUES ('cancel-linked-review', 'cancel-linked-task', 'execution', 'pending')
            """
        )
        connection.execute(
            """
            INSERT INTO execution_outbox_events (
              id, aggregate_type, aggregate_id, event_type, idempotency_key, status
            ) VALUES (
              'cancel-linked-processing', 'ai_task', 'cancel-linked-task',
              'runner.execute', 'cancel-linked-processing', 'processing'
            )
            """
        )

    result = repository.cancel_work_item_bundle(
        work_item_id="cancel-linked-work",
        expected_version=1,
        high_risk=False,
    )

    assert result["work_item"]["status"] == "cancelled"
    with repository._connect() as connection:
        task_status = connection.execute(
            "SELECT status FROM ai_tasks WHERE id = 'cancel-linked-task'"
        ).fetchone()[0]
        review_status = connection.execute(
            "SELECT status FROM human_reviews WHERE id = 'cancel-linked-review'"
        ).fetchone()[0]
        outbox_types = {
            row[0]
            for row in connection.execute(
                "SELECT event_type FROM execution_outbox_events "
                "WHERE aggregate_id = 'cancel-linked-work' "
                "OR id LIKE 'outbox:work-item:cancel-linked-work:%'"
            ).fetchall()
        }
    assert task_status == "cancelled"
    assert review_status == "cancelled"
    assert {"rd.work_item.cancel_runner", "rd.work_item.reconcile_cancellation"}.issubset(
        outbox_types
    )


def test_idempotent_command_replays_immutable_response_and_rolls_back_failure(
    repository: PostgresSnapshotRepository,
) -> None:
    calls = 0

    def operation(cursor):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        cursor.execute(
            "INSERT INTO rd_collaboration_events "
            "(id, collaboration_run_id, event_type, event_key, subject_type, subject_id) "
            "VALUES ('never', 'missing', 'test', 'never', 'test', 'never')"
        )
        return {}

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        repository.execute_idempotent_rd_command(
            command_type="test",
            aggregate_type="test",
            aggregate_id="test",
            idempotency_key="failed",
            request_hash="failed-hash",
            operation=operation,
            command_record_id="failed-command",
        )
    assert repository.get_rd_command_idempotency_record("failed-command") is None

    def success(_cursor):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        return {
            "result_type": "thing",
            "result_id": "thing-1",
            "http_status": 201,
            "response_json": {"data": {"value": 1}, "trace_id": "first"},
        }

    first = repository.execute_idempotent_rd_command(
        command_type="create",
        aggregate_type="thing",
        aggregate_id="thing-1",
        idempotency_key="same",
        request_hash="same-hash",
        operation=success,
        command_record_id="command-1",
    )
    with repository._connect(autocommit=False) as connection:
        connection.execute("SELECT 1")
    replay = repository.execute_idempotent_rd_command(
        command_type="create",
        aggregate_type="thing",
        aggregate_id="thing-1",
        idempotency_key="same",
        request_hash="same-hash",
        operation=lambda _cursor: pytest.fail("replay must not rerun operation"),
        command_record_id="command-other",
    )
    assert first["http_status"] == replay["http_status"] == 201
    assert replay["response_json"]["data"] == {"value": 1}
    assert replay["idempotent_replay"] is True

    with pytest.raises(RdCollaborationRepositoryError) as conflict:
        repository.execute_idempotent_rd_command(
            command_type="create",
            aggregate_type="thing",
            aggregate_id="thing-1",
            idempotency_key="same",
            request_hash="different-hash",
            operation=success,
            command_record_id="command-conflict",
        )
    assert conflict.value.code == "RD_IDEMPOTENCY_CONFLICT"


def test_claim_replay_secret_is_valid_until_database_expiry_then_scrubbed(
    repository: PostgresSnapshotRepository,
) -> None:
    repository.execute_idempotent_rd_command(
        command_type="claim",
        aggregate_type="rd_work_item",
        aggregate_id="secret-work",
        idempotency_key="secret-key",
        request_hash="secret-hash",
        command_record_id="secret-command",
        operation=lambda _cursor: {
            "result_type": "rd_work_item_attempt",
            "result_id": "secret-attempt",
            "http_status": 200,
            "response_json": {"data": {"secret_ref": "secret-command"}},
        },
    )
    repository.save_and_scrub_claim_replay_secret(
        secret={
            "id": "secret-1",
            "command_record_id": "secret-command",
            "secret_ciphertext": "ciphertext",
            "key_id": "test-key",
            "expires_at": datetime.now(UTC) + timedelta(minutes=5),
        }
    )
    assert repository.get_valid_claim_replay_secret("secret-command")["secret_ciphertext"] == (
        "ciphertext"
    )

    with repository._connect(autocommit=False) as connection:
        connection.execute(
            "UPDATE rd_command_replay_secrets SET expires_at = now() - interval '1 second' "
            "WHERE command_record_id = 'secret-command'"
        )
    scrubbed = repository.save_and_scrub_claim_replay_secret()
    assert scrubbed["scrubbed_count"] == 1
    assert repository.get_valid_claim_replay_secret("secret-command") is None


def test_suspend_and_decide_run_uses_optimistic_version_and_validates_input(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="decision")
    decision = _decision_record(seeded, decision_id="decision-1")
    repository.save_decision_request_record(decision)
    paused = repository.suspend_collaboration_run(
        collaboration_run_id=str(seeded["run"]["id"]),
        decision_request_id="decision-1",
        expected_version=1,
    )
    assert paused["status"] == "waiting_human"

    with pytest.raises(RdCollaborationRepositoryError) as invalid:
        repository.apply_decision_bundle(
            decision_request_id="decision-1",
            selected_option_code="continue",
            input_json={"unknown": True},
            comment=None,
            decided_by="user_admin",
            expected_version=1,
        )
    assert invalid.value.code == "RD_DECISION_INPUT_INVALID"
    assert repository.get_decision_request("decision-1")["status"] == "pending"

    result = repository.apply_decision_bundle(
        decision_request_id="decision-1",
        selected_option_code="continue",
        input_json={"modules": ["payments"]},
        comment=None,
        decided_by="user_admin",
        expected_version=1,
    )
    assert result["decision_request"]["status"] == "approved"
    assert result["decision_request"]["version"] == 2
    assert result["run"]["status"] == "running"

    with pytest.raises(RdCollaborationVersionConflictError):
        repository.apply_decision_bundle(
            decision_request_id="decision-1",
            selected_option_code="continue",
            input_json={"modules": ["payments"]},
            comment=None,
            decided_by="user_admin",
            expected_version=1,
        )


def test_decision_apply_enforces_the_frozen_actor_selector_in_postgres(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="decision-selector")
    decision = _decision_record(seeded, decision_id="selector-decision")
    repository.save_decision_request_record(decision)
    repository.suspend_collaboration_run(
        collaboration_run_id=str(seeded["run"]["id"]),
        decision_request_id="selector-decision",
        expected_version=1,
    )

    with pytest.raises(RdCollaborationRepositoryError) as denied:
        repository.apply_decision_bundle(
            decision_request_id="selector-decision",
            selected_option_code="continue",
            input_json={"modules": ["payments"]},
            comment=None,
            decided_by="cross-product-user",
            actor_role_codes=["rd_owner"],
            expected_version=1,
        )

    assert denied.value.code == "PERMISSION_DENIED"
    assert repository.get_decision_request("selector-decision")["status"] == "pending"


def test_decision_apply_rejects_admin_that_is_not_in_the_frozen_selector_in_postgres(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="decision-admin-selector")
    decision = _decision_record(seeded, decision_id="admin-selector-decision")
    repository.save_decision_request_record(decision)
    repository.suspend_collaboration_run(
        collaboration_run_id=str(seeded["run"]["id"]),
        decision_request_id="admin-selector-decision",
        expected_version=1,
    )

    with pytest.raises(RdCollaborationRepositoryError) as denied:
        repository.apply_decision_bundle(
            decision_request_id="admin-selector-decision",
            selected_option_code="continue",
            input_json={"modules": ["payments"]},
            comment=None,
            decided_by="user_reviewer",
            actor_role_codes=["admin"],
            expected_version=1,
        )

    assert denied.value.code == "PERMISSION_DENIED"
    assert repository.get_decision_request("admin-selector-decision")["status"] == "pending"


def test_postgres_decision_selector_denial_maps_to_forbidden_http_status(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="decision-selector-http")
    decision = _decision_record(seeded, decision_id="selector-http-decision")
    decision["decision_actor_selector"] = {"user_ids": ["user_reviewer"]}
    repository.save_decision_request_record(decision)
    repository.suspend_collaboration_run(
        collaboration_run_id=str(seeded["run"]["id"]),
        decision_request_id="selector-http-decision",
        expected_version=1,
    )
    original_store = app.state.store
    app.state.store = PostgresRuntimeStore(repository)
    try:
        client = TestClient(app)
        login = client.post(
            "/api/auth/login",
            json={"username": "admin@example.com", "password": "admin123"},
        )
        response = client.post(
            "/api/delivery/decision-requests/selector-http-decision/decide",
            json={
                "selected_option": "continue",
                "input": {"modules": ["payments"]},
                "version": 1,
                "idempotency_key": "selector-http-admin-attempt",
            },
            headers={"Authorization": f"Bearer {login.json()['data']['access_token']}"},
        )
    finally:
        app.state.store = original_store

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PERMISSION_DENIED"
    assert response.json()["detail"]["trace_id"]
    assert repository.get_decision_request("selector-http-decision")["status"] == "pending"


def test_request_more_info_and_answer_selector_reopens_pending_without_resuming(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="answer")
    decision = _decision_record(
        seeded,
        decision_id="answer-decision",
        answer_actor_selector={"user_ids": ["user_admin"]},
    )
    repository.save_decision_request_record(decision)
    repository.suspend_collaboration_run(
        collaboration_run_id=str(seeded["run"]["id"]),
        decision_request_id="answer-decision",
        expected_version=1,
    )
    more_info = repository.apply_decision_bundle(
        decision_request_id="answer-decision",
        selected_option_code="more_info",
        input_json=None,
        comment="need details",
        decided_by="user_admin",
        expected_version=1,
    )
    assert more_info["decision_request"]["status"] == "waiting_more_info"
    assert more_info["run"]["status"] == "waiting_human"

    with pytest.raises(RdCollaborationRepositoryError) as denied:
        repository.answer_decision_request(
            decision_request_id="answer-decision",
            expected_version=2,
            actor_id="user_viewer",
            actor_role_codes=[],
            actor_seat_ids=[],
            answer_json={"detail": "complete"},
            evidence_json=[],
            options_json=decision["options_json"],
            options_hash="answer-options-v2",
        )
    assert denied.value.code == "PERMISSION_DENIED"

    answered = repository.answer_decision_request(
        decision_request_id="answer-decision",
        expected_version=2,
        actor_id="user_admin",
        actor_role_codes=[],
        actor_seat_ids=[],
        answer_json={"detail": "complete"},
        evidence_json=[{"ref": "document-1"}],
        options_json=decision["options_json"],
        options_hash="answer-options-v2",
    )
    assert answered["status"] == "pending"
    assert answered["version"] == 3
    assert (
        repository.get_rd_collaboration_run(str(seeded["run"]["id"]))["status"] == "waiting_human"
    )


def test_postgres_answer_selector_resolves_the_callers_frozen_run_seat(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="answer-seat-selector")
    run_id = str(seeded["run"]["id"])
    repository.save_rd_run_seat_record(
        {
            "id": "answer-seat-selector-seat",
            "collaboration_run_id": run_id,
            "role_code": "product_manager",
            "subject_type": "human_user",
            "human_user_id": "user_reviewer",
        }
    )
    decision = _decision_record(
        seeded,
        decision_id="answer-seat-selector-decision",
        answer_actor_selector={"seat_ids": ["answer-seat-selector-seat"]},
    )
    repository.save_decision_request_record(decision)
    repository.suspend_collaboration_run(
        collaboration_run_id=run_id,
        decision_request_id="answer-seat-selector-decision",
        expected_version=1,
    )
    repository.apply_decision_bundle(
        decision_request_id="answer-seat-selector-decision",
        selected_option_code="more_info",
        input_json=None,
        comment="need evidence",
        decided_by="user_admin",
        expected_version=1,
    )

    answered = answer_decision_request(
        PostgresRuntimeStore(repository),
        decision_request_id="answer-seat-selector-decision",
        answer={"detail": "attached"},
        evidence=[{"ref": "evidence-1"}],
        actor={"id": "user_reviewer", "roles": ["reviewer"]},
        version=2,
        idempotency_key="answer-seat-selector",
    )

    assert answered["decision_request"]["status"] == "pending"
    assert answered["decision_request"]["version"] == 3


def test_database_time_expiry_is_idempotent_and_keeps_subject_paused(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="expiry")
    due = _decision_record(
        seeded,
        decision_id="expiry-old",
        expires_at=datetime.now(UTC) + timedelta(milliseconds=50),
    )
    repository.save_decision_request_record(due)
    repository.suspend_collaboration_run(
        collaboration_run_id=str(seeded["run"]["id"]),
        decision_request_id="expiry-old",
        expected_version=1,
    )
    with repository._connect() as connection:
        connection.execute("SELECT pg_sleep(0.08)")
    successor = _decision_record(
        seeded,
        decision_id="expiry-new",
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    successor["supersedes_decision_request_id"] = "expiry-old"
    successor["escalation_level"] = 1
    event = {
        "id": "expiry-event",
        "collaboration_run_id": seeded["run"]["id"],
        "event_type": "decision.expired",
        "event_key": "decision.expired:expiry-old",
        "subject_type": "decision_request",
        "subject_id": "expiry-old",
        "payload_json": {},
    }
    first = repository.expire_and_escalate_decision_request(
        decision_request_id="expiry-old",
        successor_request=successor,
        expiry_event=event,
    )
    second = repository.expire_and_escalate_decision_request(
        decision_request_id="expiry-old",
        successor_request=successor,
        expiry_event=event,
    )
    assert first["expired_request"]["status"] == "expired"
    assert second["successor_request"]["id"] == "expiry-new"
    run = repository.get_rd_collaboration_run(str(seeded["run"]["id"]))
    assert run["status"] == "waiting_human"
    assert run["suspended_decision_request_id"] == "expiry-new"
    assert len(repository.list_rd_collaboration_events(str(seeded["run"]["id"]))) == 1


def test_feedback_is_insert_once_under_concurrent_graph_replay(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="feedback")
    repository.save_rd_collaboration_event_record(
        {
            "id": "feedback-event",
            "collaboration_run_id": seeded["run"]["id"],
            "event_type": "feedback.created",
            "event_key": "feedback-event",
            "subject_type": "collaboration_run",
            "subject_id": seeded["run"]["id"],
            "payload_json": {},
        }
    )
    feedback = {
        "id": "feedback-record",
        "brain_app_id": "rd_brain",
        "product_id": seeded["product"],
        "collaboration_run_id": seeded["run"]["id"],
        "feedback_kind": "review",
        "source_event_id": "feedback-event",
        "feedback_fingerprint": "same-fingerprint",
        "role_code": "developer",
        "human_user_id": "user_admin",
        "strategy_snapshot_id": seeded["version_snapshot"]["id"],
        "producer_subject_type": "service",
        "producer_subject_id": "quality_gate",
    }
    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = list(
            executor.map(
                lambda _: repository.save_role_feedback_once(feedback),
                range(2),
            )
        )
    assert {row["id"] for row in rows} == {"feedback-record"}
    assert len(repository.list_role_feedback_records(str(seeded["run"]["id"]))) == 1


def test_experience_version_sources_and_reviewer_producer_separation(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="experience")
    repository.save_rd_collaboration_event_record(
        {
            "id": "experience-event",
            "collaboration_run_id": seeded["run"]["id"],
            "event_type": "feedback.created",
            "event_key": "experience-event",
            "subject_type": "collaboration_run",
            "subject_id": seeded["run"]["id"],
            "payload_json": {},
        }
    )
    feedback = repository.save_role_feedback_once(
        {
            "id": "experience-feedback",
            "brain_app_id": "rd_brain",
            "product_id": seeded["product"],
            "collaboration_run_id": seeded["run"]["id"],
            "feedback_kind": "review",
            "source_event_id": "experience-event",
            "feedback_fingerprint": "experience-feedback-fingerprint",
            "role_code": "developer",
            "human_user_id": "user_admin",
            "strategy_snapshot_id": seeded["version_snapshot"]["id"],
            "producer_subject_type": "human_user",
            "producer_subject_id": "user_admin",
        }
    )
    candidate = {
        "id": "experience-1",
        "experience_key": "developer:payments",
        "brain_app_id": "rd_brain",
        "product_scope": [seeded["product"]],
        "role_code": "developer",
        "work_item_type": "implementation",
        "scenario": "payments",
        "risk_scope": {"maximum": "high"},
        "content": {"guidance": "run idempotency tests"},
        "strategy_snapshot_id": seeded["version_snapshot"]["id"],
        "confidence": 0.9,
        "status": "pending",
    }
    first = repository.save_rd_role_experience_record(
        candidate,
        sources=[
            {
                "id": "experience-source-1",
                "experience_id": "experience-1",
                "role_feedback_record_id": feedback["id"],
                "strategy_snapshot_id": seeded["version_snapshot"]["id"],
            }
        ],
    )
    second = repository.save_rd_role_experience_record(
        {**candidate, "id": "experience-2", "content": {"guidance": "new evidence"}},
        sources=[
            {
                "id": "experience-source-2",
                "experience_id": "experience-2",
                "role_feedback_record_id": feedback["id"],
                "strategy_snapshot_id": seeded["version_snapshot"]["id"],
            }
        ],
    )
    assert (first["version"], second["version"]) == (1, 2)

    with pytest.raises(RdCollaborationRepositoryError) as self_review:
        repository.decide_role_experience(
            experience_id="experience-1",
            decision="approve",
            expected_review_version=1,
            reviewer_subject_type="human_user",
            reviewer_subject_id="user_admin",
            reviewer_role_code=None,
            reviewer_seat_id=None,
            require_independent_reviewer=False,
        )
    assert self_review.value.code == "PERMISSION_DENIED"

    approved = repository.decide_role_experience(
        experience_id="experience-1",
        decision="approve",
        expected_review_version=1,
        reviewer_subject_type="human_user",
        reviewer_subject_id="user_reviewer",
        reviewer_role_code="rd_owner",
        reviewer_seat_id=None,
        require_independent_reviewer=True,
    )
    assert approved["status"] == "approved"
    assert approved["review_version"] == 2


def test_database_constraints_reject_invalid_identity_dependency_and_plan_duplicates(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="constraints")
    repository.save_rd_work_item_record(
        {
            "id": "constraints-work-a",
            "collaboration_run_id": seeded["run"]["id"],
            "plan_version": 1,
            "work_item_type": "implementation",
            "title": "a",
            "objective": "a",
            "status": "draft",
            "idempotency_key": "constraints-work-a",
        }
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        repository.save_rd_run_seat_record(
            {
                "id": "invalid-seat",
                "collaboration_run_id": seeded["run"]["id"],
                "role_code": "developer",
                "subject_type": "ai_employee",
                "human_user_id": "user_admin",
            }
        )
    with pytest.raises(psycopg.errors.CheckViolation):
        repository.save_rd_work_item_dependency_record(
            {
                "id": "invalid-dependency",
                "collaboration_run_id": seeded["run"]["id"],
                "plan_version": 1,
                "predecessor_work_item_id": "constraints-work-a",
                "successor_work_item_id": "constraints-work-a",
            }
        )
    with pytest.raises(psycopg.errors.UniqueViolation):
        repository.save_rd_work_item_record(
            {
                "id": "constraints-work-duplicate",
                "collaboration_run_id": seeded["run"]["id"],
                "plan_version": 1,
                "work_item_type": "implementation",
                "title": "duplicate",
                "objective": "duplicate",
                "status": "draft",
                "idempotency_key": "constraints-work-a",
            }
        )


def test_assessment_command_replays_same_hash_and_rejects_conflicting_hash(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="assessment-command")
    command = {
        "id": "assessment-command-1",
        "assessment_id": seeded["assessment"],
        "operation": "decision",
        "idempotency_key": "same-key",
        "request_hash": "sha256:same",
        "created_by": "user_admin",
    }
    calls = 0

    def effect(_transaction):
        nonlocal calls
        calls += 1
        return {"assessment_id": seeded["assessment"], "result": "deferred"}

    first = repository.execute_requirement_assessment_command(command, effect)
    replay = repository.execute_requirement_assessment_command(command, effect)

    assert first == {"assessment_id": seeded["assessment"], "result": "deferred"}
    assert replay["result"] == "deferred"
    assert replay["idempotent_replay"] is True
    assert calls == 1

    with pytest.raises(RdCollaborationRepositoryError, match="different request"):
        repository.execute_requirement_assessment_command(
            {**command, "id": "assessment-command-2", "request_hash": "sha256:different"},
            effect,
        )


def test_assessment_start_command_is_scoped_to_requirement_request_id(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="assessment-start-command")
    secondary_assessment = {
        "id": "assessment-start-command-secondary",
        "requirement_id": seeded["requirement"],
        "requirement_revision": 2,
        "product_id": seeded["product"],
        "initial_strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "final_strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "structured_assessment": {},
        "status": "evaluating",
        "created_by": "user_admin",
    }
    repository.save_assessment_bundle(assessment=secondary_assessment, opinions=[])
    command = {
        "id": "assessment-start-command-1",
        "assessment_id": seeded["assessment"],
        "requirement_id": seeded["requirement"],
        "operation": "start",
        "idempotency_key": "same-request-id",
        "request_hash": "sha256:start-request",
        "created_by": "user_admin",
    }

    first = repository.execute_requirement_assessment_command(
        command, lambda _transaction: {"assessment_id": seeded["assessment"]}
    )
    replay = repository.execute_requirement_assessment_command(
        {
            **command,
            "id": "assessment-start-command-2",
            "assessment_id": secondary_assessment["id"],
        },
        lambda _transaction: {"unexpected": True},
    )

    assert first == {"assessment_id": seeded["assessment"]}
    assert replay == {"assessment_id": seeded["assessment"], "idempotent_replay": True}
    with pytest.raises(RdCollaborationRepositoryError, match="different request"):
        repository.execute_requirement_assessment_command(
            {
                **command,
                "id": "assessment-start-command-3",
                "assessment_id": secondary_assessment["id"],
                "request_hash": "sha256:other-request",
            },
            lambda _transaction: {"unexpected": True},
        )


def test_assessment_command_rolls_back_effect_when_provenance_is_invalid(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="assessment-command-rollback")
    command = {
        "id": "assessment-command-rollback-1",
        "assessment_id": seeded["assessment"],
        "operation": "answers",
        "idempotency_key": "invalid-provenance",
        "request_hash": "sha256:invalid-provenance",
        "created_by": "user_admin",
    }

    def invalid_effect(_transaction):
        raise RdCollaborationRepositoryError(
            "ASSESSMENT_EXECUTION_REQUIRED", "typed execution provenance is required"
        )

    with pytest.raises(RdCollaborationRepositoryError, match="typed execution provenance"):
        repository.execute_requirement_assessment_command(command, invalid_effect)
    assert (
        repository.get_requirement_assessment_command(
            assessment_id=seeded["assessment"],
            operation="answers",
            idempotency_key="invalid-provenance",
        )
        is None
    )


def test_assessment_ai_completion_uses_frozen_pg_execution_attribution(
    repository: PostgresSnapshotRepository,
) -> None:
    from app.services.requirement_assessments import complete_ai_assessment_execution_from_runner

    seeded = _seed_exact_run(repository, prefix="assessment-ai-completion")
    repository.save_rd_ai_employee_record(
        {
            "id": "assessment-ai-completion-ai",
            "brain_app_id": "rd_brain",
            "code": "assessment-ai-completion-ai",
            "name": "Assessment AI",
            "created_by": "user_admin",
        }
    )
    repository.save_rd_executor_profile_record(
        {
            "id": "assessment-ai-completion-profile",
            "brain_app_id": "rd_brain",
            "code": "assessment-ai-completion-profile",
            "name": "Assessment Profile",
            "executor_type": "codex",
            "created_by": "user_admin",
        }
    )
    source_assessment = repository.get_requirement_assessment(str(seeded["assessment"]))
    assert source_assessment is not None
    assessment = source_assessment
    opinion = {
        "id": "assessment-ai-completion-opinion",
        "assessment_id": assessment["id"],
        "role_code": "architect",
        "ai_employee_id": "assessment-ai-completion-ai",
        "executor_profile_id": "assessment-ai-completion-profile",
        "input_revision": 1,
        "strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "opinion_round": 1,
        "conclusion_json": {},
        "evidence_refs": [],
        "risk_summary": {},
        "cost_summary": {},
        "assigned_subject_type": "ai_employee",
        "assigned_ai_employee_id": "assessment-ai-completion-ai",
    }
    execution = {
        "id": "assessment-ai-completion-execution",
        "assessment_id": assessment["id"],
        "opinion_id": opinion["id"],
        "role_code": "architect",
        "actor_type": "ai_employee",
        "ai_employee_id": "assessment-ai-completion-ai",
        "executor_profile_id": "assessment-ai-completion-profile",
        "input_revision": 1,
        "strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "execution_kind": "assessment_only",
        "side_effect_policy": "no_code_git_deploy_runner_work_item",
        "status": "pending",
    }
    repository.save_assessment_bundle(
        assessment=assessment,
        opinions=[opinion],
        executions=[execution],
    )
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            INSERT INTO model_gateway_logs (
              id, provider, model, purpose, status, executor_profile_id,
              product_id, requirement_revision, strategy_snapshot_id
            ) VALUES (%s, 'test', 'test-model', 'model_gateway', 'succeeded',
                      %s, %s, %s, %s)
            """,
            (
                "assessment-ai-completion-model-log",
                "assessment-ai-completion-profile",
                seeded["product"],
                1,
                seeded["base_snapshot"]["id"],
            ),
        )
    with pytest.raises(HTTPException) as exc_info:
        complete_ai_assessment_execution_from_runner(
            current_store=PostgresRuntimeStore(repository),
            assessment_id=assessment["id"],
            execution_id=execution["id"],
            executor_profile_id="assessment-ai-completion-profile",
            runner_id="assessment-ai-completion-runner",
            model_result={
                "model_invocation_id": "assessment-ai-completion-model-log",
                "assessment_opinion": {"conclusion_json": {"recommendation": "accept"}},
            },
        )
    assert exc_info.value.detail["code"] == "ASSESSMENT_GATEWAY_REQUIRED"
    persisted_execution = repository.get_requirement_assessment_execution(execution["id"])
    assert persisted_execution["status"] == "pending"


def test_assessment_runner_completion_commits_task_opinion_audit_and_outbox_atomically(
    repository: PostgresSnapshotRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = _seed_exact_run(repository, prefix="assessment-runner-atomic")
    assessment = repository.get_requirement_assessment(str(seeded["assessment"]))
    assert assessment is not None
    runner_id = "assessment-runner-atomic-runner"
    profile_id = "assessment-runner-atomic-profile"
    employee_id = "assessment-runner-atomic-ai"
    repository.save_ai_executor_runner_record(
        {
            "id": runner_id,
            "name": "Assessment runner",
            "token_hash": sha256(b"runner-secret").hexdigest(),
            "executor_types": ["codex"],
            "workspace_roots": ["/srv/workspaces/project-a"],
            "created_by": "user_admin",
        }
    )
    repository.save_rd_ai_employee_record(
        {
            "id": employee_id,
            "brain_app_id": "rd_brain",
            "code": employee_id,
            "name": "Assessment AI",
            "created_by": "user_admin",
        }
    )
    repository.save_rd_executor_profile_record(
        {
            "id": profile_id,
            "brain_app_id": "rd_brain",
            "code": profile_id,
            "name": "Assessment profile",
            "executor_type": "codex",
            "runner_id": runner_id,
            "workspace_capabilities": {"assessment_workspace_root": "/srv/workspaces/project-a"},
            "created_by": "user_admin",
        }
    )
    opinion = {
        "id": "assessment-runner-atomic-opinion",
        "assessment_id": assessment["id"],
        "role_code": "architect",
        "ai_employee_id": employee_id,
        "executor_profile_id": profile_id,
        "input_revision": 1,
        "strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "opinion_round": 1,
        "conclusion_json": {},
        "evidence_refs": [],
        "risk_summary": {},
        "cost_summary": {},
        "assigned_subject_type": "ai_employee",
        "assigned_ai_employee_id": employee_id,
    }
    execution = {
        "id": "assessment-runner-atomic-execution",
        "assessment_id": assessment["id"],
        "opinion_id": opinion["id"],
        "role_code": "architect",
        "actor_type": "ai_employee",
        "ai_employee_id": employee_id,
        "executor_profile_id": profile_id,
        "input_revision": 1,
        "strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "execution_kind": "assessment_only",
        "side_effect_policy": "no_code_git_deploy_runner_work_item",
        "status": "pending",
    }
    repository.save_assessment_bundle(
        assessment=assessment, opinions=[opinion], executions=[execution]
    )
    task = {
        "id": "assessment-runner-atomic-task",
        "runner_id": runner_id,
        "executor_type": "codex",
        "instruction": "Assess requirement only",
        "workspace_root": "/srv/workspaces/project-a",
        "input_payload": {
            "assessment_id": assessment["id"],
            "assessment_execution_id": execution["id"],
            "executor_profile_id": profile_id,
            "product_id": seeded["product"],
            "requirement_id": seeded["requirement"],
            "requirement_revision": 1,
            "strategy_snapshot_id": seeded["base_snapshot"]["id"],
        },
        "request_config": {"assessment_only": True},
        "result_json": {},
        "logs": [],
        "status": "queued",
        "created_by": "user_admin",
        "task_kind": "assessment",
    }
    repository.save_ai_executor_task_record(task)
    with repository._connect(autocommit=False) as connection:
        connection.execute(
            """
            UPDATE requirement_assessment_executions
            SET ai_executor_task_id = %s, runner_id = %s
            WHERE id = %s
            """,
            (task["id"], runner_id, execution["id"]),
        )
        connection.execute(
            """
            INSERT INTO model_gateway_logs (
              id, provider, model, purpose, status, executor_profile_id,
              product_id, requirement_revision, strategy_snapshot_id
            ) VALUES (%s, 'test', 'test-model', 'unrelated_operation', 'succeeded',
                      %s, %s, %s, %s)
            """,
            (
                "assessment-runner-atomic-unrelated-log",
                profile_id,
                seeded["product"],
                1,
                seeded["base_snapshot"]["id"],
            ),
        )
    completed_task = {
        **task,
        "status": "succeeded",
        "result_json": {"model_invocation_id": "assessment-runner-atomic-log"},
    }
    kwargs = {
        "task": completed_task,
        "assessment_id": assessment["id"],
        "execution_id": execution["id"],
        "executor_profile_id": profile_id,
        "runner_id": runner_id,
        "audit_event": {
            "id": "assessment-runner-atomic-audit",
            "event_type": "ai_executor_task.succeeded",
            "actor_id": runner_id,
            "subject_type": "ai_executor_task",
            "subject_id": task["id"],
            "payload": {},
        },
        "outbox_event": {
            "id": "assessment-runner-atomic-outbox",
            "aggregate_type": "requirement_assessment_execution",
            "aggregate_id": execution["id"],
            "event_type": "requirement_assessment.runner_completed",
            "idempotency_key": "assessment-runner-atomic-outbox",
            "payload_json": {},
        },
    }

    original_store = app.state.store
    app.state.store = PostgresRuntimeStore(repository)
    try:
        claimed = TestClient(app).post(
            "/api/system/ai-executor-tasks/claim",
            json={"executor_type": "codex", "runner_id": runner_id},
            headers={"X-Runner-Token": "runner-secret"},
        )
        assert claimed.status_code == 200
        assert claimed.json()["data"]["task"]["id"] == task["id"]
    finally:
        app.state.store = original_store

    original_complete = repository.complete_ai_assessment_runner_task
    repository.complete_ai_assessment_runner_task = lambda **_kwargs: (_ for _ in ()).throw(
        psycopg.OperationalError("forced persistence failure")
    )
    app.state.store = PostgresRuntimeStore(repository)
    try:
        unavailable = TestClient(app).post(
            f"/api/system/ai-executor-tasks/{task['id']}/complete",
            json={
                "runner_id": runner_id,
                "status": "succeeded",
                "result_json": {
                    "model_invocation_id": "assessment-runner-atomic-log",
                    "assessment_opinion": {"conclusion_json": {"recommendation": "accept"}},
                },
            },
            headers={"X-Runner-Token": "runner-secret"},
        )
        assert unavailable.status_code == 503
        assert unavailable.json()["detail"]["code"] == "PERSISTENCE_UNAVAILABLE"
        assert unavailable.headers["x-trace-id"]
    finally:
        repository.complete_ai_assessment_runner_task = original_complete
        app.state.store = original_store

    with pytest.raises(RdCollaborationRepositoryError, match="successful frozen assessment"):
        repository.complete_ai_assessment_runner_task(
            **kwargs, model_invocation_id="missing-model-invocation"
        )
    assert repository.get_requirement_assessment_execution(execution["id"])["status"] == "pending"
    assert repository.list_ai_executor_tasks(runner_id=runner_id)[0]["status"] == "claimed"

    with pytest.raises(RdCollaborationRepositoryError, match="successful frozen assessment"):
        repository.complete_ai_assessment_runner_task(
            **kwargs, model_invocation_id="assessment-runner-atomic-unrelated-log"
        )
    assert repository.get_requirement_assessment_execution(execution["id"])["status"] == "pending"

    def gateway_result(_store, *, task):
        output = {"summary": "accept", "conclusion_json": {"recommendation": "accept"}}
        payload = task["input_payload"]
        return output, {
            "id": "assessment-runner-atomic-gateway-log",
            "provider": "test",
            "model": "test-model",
            "purpose": "requirement_assessment",
            "status": "succeeded",
            "tokens": {},
            "latency_ms": 1,
            "executor_profile_id": payload["executor_profile_id"],
            "product_id": payload["product_id"],
            "requirement_revision": payload["requirement_revision"],
            "strategy_snapshot_id": payload["strategy_snapshot_id"],
            "ai_executor_task_id": task["id"],
            "requirement_assessment_execution_id": payload["assessment_execution_id"],
        }

    monkeypatch.setattr(
        "app.services.ai_executor_assessment_gateway.call_model_gateway_for_task", gateway_result
    )
    app.state.store = PostgresRuntimeStore(repository)
    try:
        completed = TestClient(app).post(
            f"/api/system/ai-executor-tasks/{task['id']}/execute-assessment-gateway",
            json={"runner_id": runner_id},
            headers={"X-Runner-Token": "runner-secret"},
        )
        assert completed.status_code == 200, completed.text
        assert (
            completed.json()["data"]["model_invocation_id"]
            == "assessment-runner-atomic-gateway-log"
        )
    finally:
        app.state.store = original_store
    assert repository.get_requirement_assessment_execution(execution["id"])["status"] == "completed"
    assert repository.list_ai_executor_tasks(runner_id=runner_id)[0]["status"] == "succeeded"
    assert any(
        item["subject_id"] == task["id"] and item["event_type"] == "ai_executor_task.succeeded"
        for item in repository.list_audit_events()
    )
    with repository._connect() as connection:
        assert connection.execute(
            "SELECT 1 FROM execution_outbox_events WHERE id = %s",
            (f"assessment-runner-complete-{task['id']}",),
        ).fetchone()


def test_substantive_requirement_edit_cancels_prior_nonterminal_assessments(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(
        repository,
        prefix="assessment-edit-supersession",
        run_status="failed",
    )
    version = repository.get_product_version(seeded["version"])
    assert version is not None
    repository.save_product_config_record("product_versions", {**version, "status": "planning"})
    requirement = repository.load_requirements()["requirements"][seeded["requirement"]]
    current_assessment = repository.get_requirement_assessment(seeded["assessment"])
    assert current_assessment is not None
    revision_two = {**requirement, "assessment_revision": 2, "status": "submitted"}
    repository.save_requirement_record(revision_two)
    stale_assessment = {
        **current_assessment,
        "id": "assessment-edit-supersession-stale",
        "requirement_revision": 2,
        "status": "evaluating",
        "version": 1,
    }
    repository.save_assessment_bundle(assessment=stale_assessment, opinions=[])

    repository.save_requirement_revision_with_assessment_supersession(
        {**revision_two, "assessment_revision": 3, "title": "Changed requirement"}
    )

    assert repository.get_requirement_assessment(stale_assessment["id"])["status"] == "cancelled"
    persisted = repository.load_requirements()["requirements"][seeded["requirement"]]
    assert persisted["assessment_revision"] == 3


def test_stale_assessment_acceptance_cannot_approve_newer_requirement_revision(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(
        repository,
        prefix="assessment-stale-acceptance",
        run_status="failed",
    )
    version = repository.get_product_version(seeded["version"])
    assert version is not None
    repository.save_product_config_record("product_versions", {**version, "status": "planning"})
    requirement = repository.load_requirements()["requirements"][seeded["requirement"]]
    repository.save_requirement_record(
        {**requirement, "status": "submitted", "assessment_revision": 2}
    )
    assessment = repository.get_requirement_assessment(seeded["assessment"])
    assert assessment is not None
    command = {
        "id": "assessment-stale-acceptance-command",
        "assessment_id": assessment["id"],
        "operation": "decision",
        "idempotency_key": "stale-acceptance",
        "request_hash": "sha256:stale-acceptance",
        "created_by": "user_admin",
    }

    with pytest.raises(RdCollaborationRepositoryError, match="Requirement must still be submitted"):
        repository.execute_requirement_assessment_command(
            command,
            lambda transaction: transaction.accept_requirement_assessment(
                {
                    **assessment,
                    "decided_by": "user_admin",
                    "decided_at": datetime.now(UTC).isoformat(),
                },
                expected_version=int(assessment["version"]),
                requirement_id=seeded["requirement"],
            ),
        )
    assert (
        repository.load_requirements()["requirements"][seeded["requirement"]]["status"]
        == "submitted"
    )


def test_accepting_assessment_groups_requirement_and_increments_scope(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(
        repository,
        prefix="assessment-iteration-grouping",
        run_status="failed",
        version_status="planning",
    )
    requirement_id = "assessment-iteration-grouping-new-requirement"
    assessment_id = "assessment-iteration-grouping-new-assessment"
    _insert_requirement(
        repository,
        {"product": seeded["product"], "version": seeded["version"]},
        requirement_id=requirement_id,
        status="submitted",
    )
    assessment = {
        **_accepted_assessment(
            assessment_id=assessment_id,
            requirement_id=requirement_id,
            snapshot_id=seeded["base_snapshot"]["id"],
        ),
        "status": "waiting_human",
        "version": 1,
    }
    repository.save_assessment_bundle(assessment=assessment, opinions=[])
    command = {
        "id": "assessment-iteration-grouping-command",
        "assessment_id": assessment_id,
        "operation": "decision",
        "idempotency_key": "assessment-iteration-grouping",
        "request_hash": "sha256:assessment-iteration-grouping",
        "created_by": "user_admin",
    }

    accepted = repository.execute_requirement_assessment_command(
        command,
        lambda transaction: transaction.accept_requirement_assessment(
            {
                **assessment,
                "decided_by": "user_admin",
                "decided_at": datetime.now(UTC).isoformat(),
            },
            expected_version=1,
            requirement_id=requirement_id,
        ),
    )

    assert accepted["grouping"]["status"] == "planned"
    assert accepted["grouping"]["version_id"] == seeded["version"]
    assert accepted["grouping"]["version"]["scope_version"] == 2
    assert repository.load_requirements()["requirements"][requirement_id]["status"] == "planned"


def test_assessment_api_returns_trace_envelope_for_invalid_assessment_state(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="assessment-api-envelope")
    original_store = app.state.store
    app.state.store = PostgresRuntimeStore(repository)
    try:
        response = TestClient(app).post(
            f"/api/requirement-assessments/{seeded['assessment']}/opinions",
            json={"role_code": "developer", "conclusion_json": {"recommendation": "accept"}},
            headers=auth_headers(),
        )
        assert response.status_code == 409
        body = response.json()
        assert body["detail"]["code"] == "ASSESSMENT_STATE_INVALID"
        assert response.headers["x-trace-id"]
    finally:
        app.state.store = original_store


def test_assessment_api_wraps_repository_failures_in_trace_envelope(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="assessment-api-repository-error")
    original_store = app.state.store
    original_get = repository.get_requirement_assessment
    app.state.store = PostgresRuntimeStore(repository)
    repository.get_requirement_assessment = lambda _assessment_id: (_ for _ in ()).throw(
        RdCollaborationRepositoryError("ASSESSMENT_REPOSITORY_FAILURE", "forced repository failure")
    )
    try:
        response = TestClient(app).post(
            f"/api/requirement-assessments/{seeded['assessment']}/opinions",
            json={"role_code": "developer", "conclusion_json": {"recommendation": "accept"}},
            headers=auth_headers(),
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "ASSESSMENT_REPOSITORY_FAILURE"
        assert response.headers["x-trace-id"]
    finally:
        repository.get_requirement_assessment = original_get
        app.state.store = original_store


def test_assessment_api_replays_canonical_policy_conflict_with_decision_request(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="assessment-api-policy-conflict")
    requirement_id = "assessment-api-policy-conflict-pending-requirement"
    _insert_requirement(
        repository,
        seeded,
        requirement_id=requirement_id,
        status="submitted",
        version_id=str(seeded["version"]),
    )
    waiting = {
        "id": "assessment-api-policy-conflict-pending-assessment",
        "requirement_id": requirement_id,
        "requirement_revision": 1,
        "product_id": seeded["product"],
        "initial_strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "final_strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "strategy_snapshot_id": seeded["base_snapshot"]["id"],
        "structured_assessment": {},
        "status": "waiting_human",
        "version": 1,
        "opinion_round": 1,
        "created_by": "user_admin",
    }
    repository.save_assessment_bundle(
        assessment=waiting,
        opinions=[],
    )
    repository.save_assessment_bundle(
        assessment=waiting,
        opinions=[
            {
                "id": "assessment-api-policy-conflict-architect",
                "assessment_id": waiting["id"],
                "role_code": "architect",
                "input_revision": 1,
                "strategy_snapshot_id": seeded["base_snapshot"]["id"],
                "opinion_round": 1,
                "conclusion_json": {"recommendation": "accept"},
                "evidence_refs": [],
                "risk_summary": {},
                "cost_summary": {},
            },
            {
                "id": "assessment-api-policy-conflict-reviewer",
                "assessment_id": waiting["id"],
                "role_code": "reviewer",
                "input_revision": 1,
                "strategy_snapshot_id": seeded["base_snapshot"]["id"],
                "opinion_round": 1,
                "conclusion_json": {"recommendation": "reject"},
                "evidence_refs": [],
                "risk_summary": {},
                "cost_summary": {},
            },
        ],
    )
    original_store = app.state.store
    app.state.store = PostgresRuntimeStore(repository)
    try:
        payload = {"decision": "accept", "version": waiting["version"], "idempotency_key": "K"}
        client = TestClient(app)
        first = client.post(
            f"/api/requirement-assessments/{waiting['id']}/decisions",
            json=payload,
            headers=auth_headers(),
        )
        replay = client.post(
            f"/api/requirement-assessments/{waiting['id']}/decisions",
            json=payload,
            headers=auth_headers(),
        )
        new_key = client.post(
            f"/api/requirement-assessments/{waiting['id']}/decisions",
            json={**payload, "version": 2, "idempotency_key": "K2"},
            headers=auth_headers(),
        )
    finally:
        app.state.store = original_store

    for response in (first, replay, new_key):
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == "RD_POLICY_HUMAN_DECISION_REQUIRED"
        assert detail["decision_request_id"]
        assert detail["next_action"] == "resolve_policy_decision"
        assert response.headers["x-trace-id"]
    command = repository.get_requirement_assessment_command(
        assessment_id=waiting["id"], operation="decision", idempotency_key="K"
    )
    assert command is not None and command["status"] == "completed"


def test_assessment_public_command_replay_and_hash_conflict(
    repository: PostgresSnapshotRepository,
) -> None:
    seeded = _seed_exact_run(repository, prefix="assessment-public-command")
    command = {
        "id": "assessment-public-command-1",
        "assessment_id": seeded["assessment"],
        "operation": "opinion",
        "idempotency_key": "public-key",
        "request_hash": "sha256:public-one",
        "created_by": "user_admin",
    }
    response = repository.execute_requirement_assessment_command(
        command, lambda _transaction: {"status": "recorded"}
    )
    replay = repository.execute_requirement_assessment_command(
        command, lambda _transaction: {"status": "mutated-again"}
    )
    assert response == {"status": "recorded"}
    assert replay == {"status": "recorded", "idempotent_replay": True}
    with pytest.raises(RdCollaborationRepositoryError) as conflict:
        repository.execute_requirement_assessment_command(
            {**command, "id": "assessment-public-command-2", "request_hash": "sha256:public-two"},
            lambda _transaction: {"status": "different"},
        )
    assert conflict.value.code == "RD_IDEMPOTENCY_CONFLICT"
