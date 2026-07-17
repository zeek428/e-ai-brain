from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations"
MIGRATION_NAME = "109_requirement_driven_rd_collaboration.sql"


@pytest.fixture
def migration_sql() -> str:
    migration_path = MIGRATIONS_DIR / MIGRATION_NAME
    assert migration_path.exists(), f"missing migration: {MIGRATION_NAME}"
    return migration_path.read_text(encoding="utf-8")


def _normalized(sql: str) -> str:
    return " ".join(sql.lower().split())


def _table_body(sql: str, table_name: str) -> str:
    match = re.search(
        rf"CREATE TABLE IF NOT EXISTS\s+{re.escape(table_name)}\s*\((.*?)\n\);",
        sql,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert match is not None, f"missing table: {table_name}"
    return match.group(1)


def _assert_columns(sql: str, table_name: str, columns: set[str]) -> None:
    body = _table_body(sql, table_name)
    for column in columns:
        assert re.search(rf"(?m)^\s*{re.escape(column)}\s+", body), (
            f"{table_name}.{column} is missing"
        )


def _assert_no_column(sql: str, table_name: str, column: str) -> None:
    body = _table_body(sql, table_name)
    assert not re.search(rf"(?m)^\s*{re.escape(column)}\s+", body)


def _assert_unique(sql: str, table_name: str, columns: tuple[str, ...]) -> None:
    body = _normalized(_table_body(sql, table_name))
    joined = ", ".join(columns)
    assert f"unique ({joined})" in body or f"unique({joined})" in body


def _assert_fk_restrict(
    sql: str,
    table_name: str,
    column: str,
    target_table: str,
) -> None:
    body = _normalized(_table_body(sql, table_name))
    pattern = (
        rf"{re.escape(column)}\s+[^,]*references\s+{re.escape(target_table)}\s*\([^)]*\)"
        r"\s+on delete restrict"
    )
    assert re.search(pattern, body), (
        f"{table_name}.{column} must reference {target_table} ON DELETE RESTRICT"
    )


def test_requirement_driven_collaboration_migration_is_registered():
    persistence_source = (
        Path(__file__).resolve().parents[1] / "app" / "core" / "persistence.py"
    ).read_text(encoding="utf-8")

    assert MIGRATION_NAME in persistence_source


def test_migration_creates_the_complete_unified_collaboration_schema(migration_sql: str):
    for table_name in (
        "rd_role_definitions",
        "rd_ai_employees",
        "rd_executor_profiles",
        "rd_task_executor_policy_role_bindings",
        "rd_task_executor_policy_snapshots",
        "rd_task_executor_policy_snapshot_sources",
        "requirement_assessments",
        "requirement_assessment_opinions",
        "rd_collaboration_runs",
        "rd_collaboration_run_requirements",
        "rd_scope_change_requests",
        "rd_scope_change_request_operations",
        "rd_run_seats",
        "rd_role_sessions",
        "rd_work_items",
        "rd_work_item_dependencies",
        "rd_work_item_attempts",
        "rd_collaboration_events",
        "decision_requests",
        "rd_command_idempotency_records",
        "rd_command_replay_secrets",
        "role_feedback_records",
        "rd_role_experience_records",
        "rd_role_experience_sources",
        "rd_collaboration_upgrade_state",
    ):
        _table_body(migration_sql, table_name)


def test_task3_repository_optimistic_versions_are_persisted_by_migration_109(
    migration_sql: str,
) -> None:
    work_item_body = _normalized(_table_body(migration_sql, "rd_work_items"))
    normalized = _normalized(migration_sql)

    assert "version bigint not null default 1" in work_item_body
    assert "version > 0" in work_item_body
    assert (
        "alter table if exists rd_work_items add column if not exists version bigint not null "
        "default 1"
    ) in normalized
    assert (
        "alter table if exists product_version_branch_configs add column if not exists "
        "branch_config_version bigint not null default 1"
    ) in normalized
    assert "add column if not exists base_commit_sha text" in normalized
    assert "ck_rd_work_items_version" in normalized
    assert "ck_product_version_branch_configs_version" in normalized


def test_scope_change_operation_check_matches_approved_typed_destinations(
    migration_sql: str,
) -> None:
    body = _normalized(_table_body(migration_sql, "rd_scope_change_request_operations"))

    assert re.search(
        r"op = 'remove_requirement'.*destination = 'approved_pool'",
        body,
    )
    assert re.search(
        r"op = 'update_repository_baseline'.*destination is null",
        body,
    )


def test_new_collaboration_tables_follow_timestamp_mutability_contract(migration_sql: str):
    immutable_tables = {
        "rd_task_executor_policy_snapshots",
        "rd_task_executor_policy_snapshot_sources",
        "rd_collaboration_run_requirements",
        "rd_scope_change_request_operations",
        "rd_command_idempotency_records",
        "role_feedback_records",
    }
    mutable_tables = {
        "rd_role_definitions",
        "rd_ai_employees",
        "rd_executor_profiles",
        "rd_task_executor_policy_role_bindings",
        "requirement_assessments",
        "requirement_assessment_opinions",
        "rd_collaboration_runs",
        "rd_scope_change_requests",
        "rd_run_seats",
        "rd_role_sessions",
        "rd_work_items",
        "rd_work_item_dependencies",
        "rd_work_item_attempts",
        "rd_collaboration_events",
        "decision_requests",
        "rd_command_replay_secrets",
        "rd_role_experience_records",
        "rd_role_experience_sources",
        "rd_collaboration_upgrade_state",
    }

    for table_name in mutable_tables:
        body = _table_body(migration_sql, table_name)
        assert re.search(r"\bcreated_at\s+timestamptz\s+not null\s+default now\(\)", body, re.I)
        assert re.search(r"\bupdated_at\s+timestamptz\s+not null\s+default now\(\)", body, re.I)
    for table_name in immutable_tables:
        body = _table_body(migration_sql, table_name)
        assert re.search(r"\bcreated_at\s+timestamptz\s+not null\s+default now\(\)", body, re.I)
        assert not re.search(r"\bupdated_at\s+", body, re.I)

    normalized = _normalized(migration_sql)
    for table_name in immutable_tables:
        assert f"trg_{table_name}_immutable" in normalized
    assert (
        "raise exception 'immutable collaboration fact rows cannot be updated or deleted'"
        in normalized
    )


def test_policy_snapshot_is_insert_only_and_has_exact_identity(migration_sql: str):
    _assert_columns(
        migration_sql,
        "rd_task_executor_policy_snapshots",
        {
            "policy_id",
            "policy_version",
            "parent_snapshot_id",
            "snapshot_kind",
            "resolution_context_key",
            "resolution_revision",
            "schema_version",
            "content_hash",
            "payload_json",
            "created_by",
            "created_at",
        },
    )
    _assert_no_column(migration_sql, "rd_task_executor_policy_snapshots", "updated_at")
    _assert_unique(
        migration_sql,
        "rd_task_executor_policy_snapshots",
        (
            "policy_id",
            "policy_version",
            "snapshot_kind",
            "resolution_context_key",
            "resolution_revision",
        ),
    )
    body = _normalized(_table_body(migration_sql, "rd_task_executor_policy_snapshots"))
    for column in (
        "policy_id",
        "policy_version",
        "snapshot_kind",
        "resolution_context_key",
        "resolution_revision",
        "schema_version",
        "content_hash",
        "payload_json",
        "created_by",
        "created_at",
    ):
        assert re.search(rf"\b{column}\b[^,]*\bnot null\b", body)
    assert "snapshot_kind in ('base', 'assessment_resolved', 'version_resolved')" in body
    assert "'policy:' || policy_id || ':version:' || policy_version::text" in body
    assert "resolution_context_key ~ '^assessment:[^:]+$'" in body
    assert "resolution_revision between 1 and 2" in body
    assert "resolution_context_key ~ '^version:[^:]+:scope:[0-9]+$'" in body
    assert "on delete restrict" in body
    normalized = _normalized(migration_sql)
    assert "idx_rd_policy_snapshot_content_hash" in normalized
    assert "trg_rd_policy_snapshot_parent_integrity" in normalized
    assert (
        "foreign key (policy_id) references rd_task_executor_policies(id) on delete restrict"
        in normalized
    )
    assert "foreign key (policy_id, policy_version)" not in normalized
    assert "trg_rd_policy_snapshot_current_policy_version" in normalized
    assert "check (policy_version > 0)" in normalized
    assert "trg_rd_task_executor_policy_version_monotonic" in normalized
    assert "new.policy_version < old.policy_version" in normalized
    assert "trg_requirement_assessment_provenance_immutable" in normalized
    assert "if old.status = 'accepted'" in normalized
    assert "old.parent_snapshot_id is null" in normalized or "parent_snapshot_id is null" in body


def test_version_resolved_snapshot_sources_are_deferred_exact_and_immutable(
    migration_sql: str,
):
    _assert_columns(
        migration_sql,
        "rd_task_executor_policy_snapshot_sources",
        {"snapshot_id", "source_snapshot_id", "requirement_id", "assessment_id", "created_at"},
    )
    _assert_no_column(migration_sql, "rd_task_executor_policy_snapshot_sources", "updated_at")
    _assert_unique(
        migration_sql,
        "rd_task_executor_policy_snapshot_sources",
        ("snapshot_id", "requirement_id"),
    )
    body = _normalized(_table_body(migration_sql, "rd_task_executor_policy_snapshot_sources"))
    assert "unique (snapshot_id, source_snapshot_id)" not in body
    for column, target in (
        ("snapshot_id", "rd_task_executor_policy_snapshots"),
        ("source_snapshot_id", "rd_task_executor_policy_snapshots"),
        ("requirement_id", "requirements"),
        ("assessment_id", "requirement_assessments"),
    ):
        _assert_fk_restrict(
            migration_sql,
            "rd_task_executor_policy_snapshot_sources",
            column,
            target,
        )
    normalized = _normalized(migration_sql)
    assert "create constraint trigger trg_rd_policy_snapshot_source_integrity" in normalized
    assert "deferrable initially deferred" in normalized
    assert "source_count" in normalized and "scope_count" in normalized
    assert "same policy id and version" in normalized
    assert "exact run requirement scope" in normalized


def test_run_requirement_scope_is_immutable_and_exact(migration_sql: str):
    _assert_columns(
        migration_sql,
        "rd_collaboration_run_requirements",
        {
            "collaboration_run_id",
            "requirement_id",
            "requirement_revision",
            "assessment_id",
            "final_strategy_snapshot_id",
            "acceptance_criteria_hash",
            "repository_scope_hash",
            "created_at",
        },
    )
    _assert_no_column(migration_sql, "rd_collaboration_run_requirements", "updated_at")
    _assert_unique(
        migration_sql,
        "rd_collaboration_run_requirements",
        ("collaboration_run_id", "requirement_id"),
    )
    normalized = _normalized(migration_sql)
    assert "trg_rd_collaboration_run_requirements_immutable" in normalized
    assert "create constraint trigger trg_rd_collaboration_run_scope_integrity" in normalized
    assert "deferrable initially deferred" in normalized
    assert "status <> 'accepted'" in normalized


def test_run_pause_generation_decision_expiry_and_fence_are_constrained(migration_sql: str):
    _assert_fk_restrict(
        migration_sql,
        "rd_collaboration_runs",
        "suspended_decision_request_id",
        "decision_requests",
    )
    _assert_fk_restrict(
        migration_sql,
        "rd_collaboration_runs",
        "supersedes_run_id",
        "rd_collaboration_runs",
    )
    _assert_unique(migration_sql, "rd_collaboration_runs", ("product_version_id", "run_generation"))
    run_body = _normalized(_table_body(migration_sql, "rd_collaboration_runs"))
    assert "status = 'waiting_human'" in run_body
    assert "resume_state in ('running', 'integrating', 'verifying')" in run_body
    assert "suspended_decision_request_id is not null" in run_body
    assert "suspended_at is not null" in run_body
    normalized = _normalized(migration_sql)
    assert "where supersedes_run_id is not null" in normalized
    assert "where status not in ('completed', 'failed', 'cancelled')" in normalized
    assert "trg_rd_collaboration_run_scope_identity_immutable" in normalized
    assert "failed or cancelled terminal collaboration runs are immutable" in normalized
    assert "if tg_op = 'insert' then" in normalized
    assert "collaboration run snapshot must match frozen version and scope" in normalized
    for frozen_field in (
        "product_id",
        "product_version_id",
        "strategy_snapshot_id",
        "run_generation",
        "supersedes_run_id",
        "scope_version",
    ):
        assert f"new.{frozen_field}" in normalized
        assert f"old.{frozen_field}" in normalized

    decision_body = _normalized(_table_body(migration_sql, "decision_requests"))
    for field in (
        "expires_at",
        "timeout_policy",
        "escalation_target_selector",
        "escalation_level",
        "expired_at",
        "expiry_event_id",
        "supersedes_decision_request_id",
    ):
        assert re.search(rf"\b{field}\b", decision_body)
    assert "idx_decision_requests_expiry_due" in normalized
    assert "where status in ('pending', 'waiting_more_info')" in normalized
    assert "where expiry_event_id is not null" in normalized
    assert "where supersedes_decision_request_id is not null" in normalized

    upgrade_body = _normalized(_table_body(migration_sql, "rd_collaboration_upgrade_state"))
    assert "fence_mode in ('disabled', 'draining', 'cutover_locked')" in upgrade_body
    for field in (
        "version",
        "schema_version",
        "cleanup_started_at",
        "cleanup_completed_at",
        "abort_reason",
        "abort_actor_id",
        "aborted_at",
    ):
        assert re.search(rf"\b{field}\b", upgrade_body)
    assert "values ('rd_collaboration', 'disabled', 1, 1)" in normalized


def test_all_rd_commands_have_permanent_idempotency_and_expiring_secret_replay(
    migration_sql: str,
):
    _assert_columns(
        migration_sql,
        "rd_command_idempotency_records",
        {
            "command_type",
            "aggregate_type",
            "aggregate_id",
            "idempotency_key",
            "request_hash",
            "result_type",
            "result_id",
            "http_status",
            "response_hash",
            "response_json",
            "created_at",
        },
    )
    _assert_no_column(migration_sql, "rd_command_idempotency_records", "expires_at")
    _assert_no_column(migration_sql, "rd_command_idempotency_records", "updated_at")
    _assert_unique(
        migration_sql,
        "rd_command_idempotency_records",
        ("command_type", "aggregate_type", "aggregate_id", "idempotency_key"),
    )
    _assert_columns(
        migration_sql,
        "rd_command_replay_secrets",
        {
            "command_record_id",
            "secret_ciphertext",
            "key_id",
            "expires_at",
            "scrubbed_at",
            "created_at",
            "updated_at",
        },
    )
    _assert_unique(migration_sql, "rd_command_replay_secrets", ("command_record_id",))
    normalized = _normalized(migration_sql)
    assert "scrub_expired_rd_command_replay_secrets" in normalized
    assert "secret_ciphertext = null" in normalized
    assert "scrubbed_at = now()" in normalized
    assert "expires_at <= now()" in normalized
    assert "rd_claim_lease_expired" in normalized


def test_scope_change_requests_are_versioned_typed_and_governed(migration_sql: str):
    _assert_columns(
        migration_sql,
        "rd_scope_change_requests",
        {
            "product_version_id",
            "request_id",
            "source_run_id",
            "source_run_state",
            "expected_scope_version",
            "expected_run_generation",
            "operations_json",
            "operations_hash",
            "status",
            "decision_request_id",
            "applied_scope_version",
            "requested_by",
            "applied_at",
            "created_at",
            "updated_at",
        },
    )
    _assert_unique(migration_sql, "rd_scope_change_requests", ("product_version_id", "request_id"))
    _assert_fk_restrict(
        migration_sql,
        "rd_scope_change_requests",
        "source_run_id",
        "rd_collaboration_runs",
    )
    _assert_fk_restrict(
        migration_sql,
        "rd_scope_change_requests",
        "decision_request_id",
        "decision_requests",
    )
    request_body = _normalized(_table_body(migration_sql, "rd_scope_change_requests"))
    assert "status in ('pending_decision', 'applied', 'rejected')" in request_body
    assert "status = 'pending_decision' and decision_request_id is not null" in request_body
    assert "status = 'applied'" in request_body
    assert "applied_scope_version is not null" in request_body
    assert "applied_at is not null" in request_body
    normalized = _normalized(migration_sql)
    assert "where status = 'pending_decision'" in normalized
    assert "trg_rd_scope_change_request_proposal_immutable" in normalized

    _assert_columns(
        migration_sql,
        "rd_scope_change_request_operations",
        {
            "scope_change_request_id",
            "position",
            "op",
            "requirement_id",
            "requirement_revision",
            "assessment_id",
            "final_strategy_snapshot_id",
            "repository_id",
            "branch_config_version",
            "base_commit_sha",
            "destination",
            "created_at",
        },
    )
    _assert_unique(
        migration_sql,
        "rd_scope_change_request_operations",
        ("scope_change_request_id", "position"),
    )
    operation_body = _normalized(_table_body(migration_sql, "rd_scope_change_request_operations"))
    assert (
        "op in ('add_requirement', 'remove_requirement', "
        "'replace_requirement_snapshot', 'update_repository_baseline')" in operation_body
    )
    for column, target in (
        ("scope_change_request_id", "rd_scope_change_requests"),
        ("requirement_id", "requirements"),
        ("assessment_id", "requirement_assessments"),
        ("final_strategy_snapshot_id", "rd_task_executor_policy_snapshots"),
        ("repository_id", "product_git_repositories"),
    ):
        _assert_fk_restrict(migration_sql, "rd_scope_change_request_operations", column, target)

    assert "add column if not exists supersedes_requirement_id" in normalized
    assert "add column if not exists source_collaboration_run_id" in normalized
    assert "ck_requirements_supersedes_source_run" in normalized
    assert "trg_requirement_lineage_integrity" in normalized
    assert "idx_requirements_collaboration_lineage" in normalized


def test_feedback_producer_identity_is_distinct_scoped_and_immutable(migration_sql: str):
    _assert_columns(
        migration_sql,
        "role_feedback_records",
        {
            "collaboration_run_id",
            "feedback_kind",
            "source_event_id",
            "feedback_fingerprint",
            "producer_subject_type",
            "producer_subject_id",
            "producer_role_code",
            "producer_seat_id",
            "created_at",
        },
    )
    _assert_no_column(migration_sql, "role_feedback_records", "updated_at")
    body = _normalized(_table_body(migration_sql, "role_feedback_records"))
    for column in (
        "collaboration_run_id",
        "feedback_kind",
        "source_event_id",
        "feedback_fingerprint",
        "producer_subject_type",
        "producer_subject_id",
    ):
        assert re.search(rf"\b{column}\b[^,]*\bnot null\b", body)
    assert "producer_subject_type in ('human_user', 'ai_employee', 'service')" in body
    for service_code in (
        "collaboration_orchestrator",
        "quality_gate",
        "delivery_reconciler",
        "decision_expiry_worker",
    ):
        assert f"'{service_code}'" in body
    assert "producer_role_code is null and producer_seat_id is null" in body
    assert "producer_role_code is not null and producer_seat_id is not null" in body
    _assert_fk_restrict(migration_sql, "role_feedback_records", "producer_seat_id", "rd_run_seats")
    _assert_unique(
        migration_sql,
        "role_feedback_records",
        ("collaboration_run_id", "feedback_fingerprint"),
    )
    _assert_unique(migration_sql, "rd_collaboration_events", ("collaboration_run_id", "id"))
    assert "foreign key (collaboration_run_id, source_event_id)" in body
    assert "references rd_collaboration_events(collaboration_run_id, id) on delete restrict" in body
    normalized = _normalized(migration_sql)
    assert "create constraint trigger trg_role_feedback_producer_subject" in normalized
    assert "deferrable initially deferred" in normalized
    assert "from users" in normalized
    assert "from rd_ai_employees" in normalized
    assert "trg_role_feedback_producer_seat_role" in normalized
    assert normalized.count("for key share") >= 3
    assert "producer seat subject must match producer subject type and id" in normalized
    assert "trg_rd_run_seat_feedback_identity_immutable" in normalized
    assert "feedback-referenced seat identity is immutable from creation" in normalized
    assert "trg_users_feedback_producer_identity" in normalized
    assert "trg_rd_ai_employees_feedback_producer_identity" in normalized
    assert "trg_role_feedback_records_immutable" in normalized


def test_graph_version_task_links_permissions_and_runtime_grants_are_additive(
    migration_sql: str,
):
    normalized = _normalized(migration_sql)
    assert "add column if not exists policy_version bigint not null default 1" in normalized
    assert (
        "create unique index if not exists uk_rd_task_executor_policies_active_product"
        not in normalized
    )
    assert (
        "create unique index if not exists uk_rd_task_executor_policies_active_default"
        not in normalized
    )
    assert "idx_rd_task_executor_policies_active_product_advisory" in normalized
    assert "idx_rd_task_executor_policies_active_default_advisory" in normalized
    assert "add column if not exists scope_version bigint not null default 1" in normalized
    for table_name in ("graph_runs", "graph_checkpoints"):
        assert f"alter table if exists {table_name}" in normalized
    for column in ("subject_type", "subject_id", "thread_id", "graph_definition", "graph_version"):
        assert normalized.count(f"add column if not exists {column}") >= 2
    assert "add column if not exists collaboration_run_id" in normalized
    assert "add column if not exists work_item_id" in normalized
    assert "'ready_for_release'" in normalized and "'deploying'" in normalized

    for permission in (
        "delivery.rd_roles.manage",
        "delivery.rd_ai_employees.manage",
        "delivery.rd_executor_profiles.manage",
        "delivery.requirement_assessments.read",
        "delivery.requirement_assessments.decide",
        "delivery.rd_collaboration.read",
        "delivery.rd_collaboration.plan",
        "delivery.rd_collaboration.work",
        "delivery.decision_requests.decide",
        "delivery.decision_requests.answer",
        "delivery.rd_role_experiences.read",
        "delivery.rd_role_experiences.decide",
    ):
        assert f"'{permission}'" in normalized

    assert "grant select, insert on rd_task_executor_policy_snapshots" in normalized
    assert "grant select, insert on rd_task_executor_policy_snapshot_sources" in normalized
    assert "grant select, insert on rd_collaboration_run_requirements" in normalized
    assert "grant update" not in normalized.split("-- immutable runtime grants", 1)[-1]
    assert "grant delete" not in normalized.split("-- immutable runtime grants", 1)[-1]


def test_migration_trigger_and_late_constraint_creation_is_replay_safe(migration_sql: str):
    normalized = _normalized(migration_sql)
    trigger_names = re.findall(r"create (?:constraint )?trigger ([a-z0-9_]+)", normalized)

    assert trigger_names
    for trigger_name in trigger_names:
        assert f"drop trigger if exists {trigger_name}" in normalized
    assert "drop constraint if exists fk_rd_work_items_suspended_attempt" in normalized


def test_store_exposes_and_resets_new_collaboration_collections():
    from app.core.store import MemoryStore

    store = MemoryStore()
    collection_names = (
        "rd_role_definitions",
        "rd_ai_employees",
        "rd_executor_profiles",
        "rd_task_executor_policy_role_bindings",
        "rd_task_executor_policy_snapshots",
        "rd_task_executor_policy_snapshot_sources",
        "requirement_assessments",
        "requirement_assessment_opinions",
        "rd_collaboration_runs",
        "rd_collaboration_run_requirements",
        "rd_scope_change_requests",
        "rd_scope_change_request_operations",
        "rd_run_seats",
        "rd_role_sessions",
        "rd_work_items",
        "rd_work_item_dependencies",
        "rd_work_item_attempts",
        "rd_collaboration_events",
        "decision_requests",
        "rd_command_idempotency_records",
        "rd_command_replay_secrets",
        "role_feedback_records",
        "rd_role_experience_records",
        "rd_role_experience_sources",
        "rd_collaboration_upgrade_state",
    )
    for collection_name in collection_names:
        collection = getattr(store, collection_name)
        collection["test"] = {"id": "test"}

    store.reset()

    assert all(getattr(store, name) == {} for name in collection_names)
