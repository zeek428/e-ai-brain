from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.audit import AuditReadRepository
from app.core.repositories.devops_writes import DevopsWriteRepository
from app.core.repositories.requirements import RequirementReadRepository


class ExecutionGovernanceVersionConflictError(RuntimeError):
    def __init__(self, current_version: int | None) -> None:
        super().__init__("Execution governance record version conflict")
        self.current_version = current_version


class ExecutionGovernanceWriteRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._audit_repository = AuditReadRepository(connect)
        self._devops_repository = DevopsWriteRepository(connect)
        self._requirement_repository = RequirementReadRepository(connect)
        self._upsert_audit_events_callback = upsert_audit_events

    def save_quality_gate_policy_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
        expected_version: int | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self._lock_version(
                    cursor,
                    table_name="quality_gate_policies",
                    record_id=str(record["id"]),
                    expected_version=expected_version,
                )
                self.upsert_quality_gate_policies(cursor, {str(record["id"]): record})
                self._upsert_audit_events(cursor, audit_events or [])

    def save_execution_context_manifest_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        persisted = dict(record)
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                    (record["subject_type"], record["subject_id"]),
                )
                cursor.execute(
                    """
                    SELECT id, version
                    FROM execution_context_manifests
                    WHERE subject_type = %s
                      AND subject_id = %s
                      AND content_hash = %s
                    """,
                    (
                        record["subject_type"],
                        record["subject_id"],
                        record["content_hash"],
                    ),
                )
                duplicate = cursor.fetchone()
                if duplicate is not None:
                    persisted["id"] = duplicate[0]
                    persisted["version"] = int(duplicate[1])
                    return persisted
                cursor.execute(
                    """
                    SELECT COALESCE(max(version), 0) + 1
                    FROM execution_context_manifests
                    WHERE subject_type = %s AND subject_id = %s
                    """,
                    (record["subject_type"], record["subject_id"]),
                )
                version_row = cursor.fetchone()
                persisted["version"] = int(version_row[0]) if version_row else 1
                self.upsert_execution_context_manifests(
                    cursor,
                    {str(persisted["id"]): persisted},
                )
                self._upsert_audit_events(cursor, [audit_event] if audit_event else [])
        return persisted

    def save_execution_attestation_record(self, record: dict[str, Any]) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_execution_attestations(cursor, {str(record["id"]): record})

    def save_trusted_delivery_record(
        self,
        *,
        record: dict[str, Any],
        record_type: str,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO trusted_delivery_records (
                      record_type, id, product_id, payload_json, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s::jsonb, COALESCE(%s::timestamptz, now()),
                            COALESCE(%s::timestamptz, now()))
                    ON CONFLICT (record_type, id) DO UPDATE SET
                      product_id = EXCLUDED.product_id,
                      payload_json = EXCLUDED.payload_json,
                      updated_at = EXCLUDED.updated_at
                    """,
                    (
                        record_type,
                        record["id"],
                        record.get("product_id"),
                        json.dumps(record, ensure_ascii=False),
                        record.get("created_at"),
                        record.get("updated_at") or record.get("created_at"),
                    ),
                )

    def save_rd_delivery_evidence_record(
        self,
        *,
        record: dict[str, Any],
        record_type: str,
    ) -> None:
        self.save_trusted_delivery_record(record=record, record_type=record_type)

    def save_execution_resource_grant_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self._lock_version(
                    cursor,
                    table_name="execution_resource_grants",
                    record_id=str(record["id"]),
                    expected_version=expected_version,
                )
                self.upsert_execution_resource_grants(
                    cursor,
                    {str(record["id"]): record},
                )
                self._upsert_audit_events(cursor, [audit_event] if audit_event else [])

    def upsert_execution_attestations(
        self,
        cursor: Any,
        records: dict[str, dict[str, Any]],
    ) -> None:
        for record in records.values():
            cursor.execute(
                """
                INSERT INTO execution_attestations (
                  id, subject_type, subject_id, runner_task_id, runner_id,
                  trust_domain, trust_boundary_id, payload_json, payload_sha256,
                  signature, public_key_fingerprint, verification_status,
                  verification_error_code, verified_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s, %s::jsonb, %s,
                  %s, %s, %s,
                  %s, %s::timestamptz, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (runner_task_id) DO UPDATE SET
                  payload_json = EXCLUDED.payload_json,
                  payload_sha256 = EXCLUDED.payload_sha256,
                  signature = EXCLUDED.signature,
                  public_key_fingerprint = EXCLUDED.public_key_fingerprint,
                  verification_status = EXCLUDED.verification_status,
                  verification_error_code = EXCLUDED.verification_error_code,
                  verified_at = EXCLUDED.verified_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    record["id"],
                    record["subject_type"],
                    record["subject_id"],
                    record["runner_task_id"],
                    record["runner_id"],
                    record["trust_domain"],
                    record.get("trust_boundary_id"),
                    json.dumps(record.get("payload") or {}),
                    record["payload_sha256"],
                    record.get("signature"),
                    record.get("public_key_fingerprint"),
                    record["verification_status"],
                    record.get("verification_error_code"),
                    record.get("verified_at"),
                    record.get("created_at"),
                    record.get("updated_at") or record.get("created_at"),
                ),
            )

    def save_external_event_inbox_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_external_event_inbox(
                    cursor,
                    {str(record["id"]): record},
                )
                self._upsert_audit_events(cursor, [audit_event] if audit_event else [])

    def create_deployment_dispatch_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        deployment: dict[str, Any],
        outbox_event: dict[str, Any],
        requirements: list[dict[str, Any]],
        run: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self._devops_repository.upsert_deployment_requests(
                    cursor,
                    {str(deployment["id"]): deployment},
                )
                self._devops_repository.upsert_deployment_runs(
                    cursor,
                    {str(run["id"]): run},
                )
                self.upsert_deployment_run_steps(
                    cursor,
                    {str(step["id"]): step for step in steps},
                )
                self.upsert_execution_outbox_events(
                    cursor,
                    {str(outbox_event["id"]): outbox_event},
                )
                self._requirement_repository.upsert_requirements(
                    cursor,
                    {str(requirement["id"]): requirement for requirement in requirements},
                )
                self._upsert_audit_events(cursor, audit_events)

    def save_deployment_dispatch_failure_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        deployment: dict[str, Any],
        outbox_event: dict[str, Any],
        requirements: list[dict[str, Any]],
        run: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self._devops_repository.upsert_deployment_requests(
                    cursor,
                    {str(deployment["id"]): deployment},
                )
                self._devops_repository.upsert_deployment_runs(
                    cursor,
                    {str(run["id"]): run},
                )
                self.upsert_deployment_run_steps(
                    cursor,
                    {str(step["id"]): step for step in steps},
                )
                self.upsert_execution_outbox_events(
                    cursor,
                    {str(outbox_event["id"]): outbox_event},
                )
                self._requirement_repository.upsert_requirements(
                    cursor,
                    {str(requirement["id"]): requirement for requirement in requirements},
                )
                self._upsert_audit_events(cursor, audit_events)

    def save_deployment_dispatch_result_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        outbox_event: dict[str, Any],
        run: dict[str, Any],
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self._devops_repository.upsert_deployment_runs(
                    cursor,
                    {str(run["id"]): run},
                )
                self.upsert_execution_outbox_events(
                    cursor,
                    {str(outbox_event["id"]): outbox_event},
                )
                self._upsert_audit_events(cursor, audit_events)

    def save_execution_outbox_event_record(
        self,
        event: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_execution_outbox_events(cursor, {str(event["id"]): event})
                self._upsert_audit_events(cursor, [audit_event] if audit_event else [])

    def save_deployment_run_steps_records(
        self,
        steps: list[dict[str, Any]],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_deployment_run_steps(
                    cursor,
                    {str(step["id"]): step for step in steps},
                )
                self._upsert_audit_events(cursor, audit_events or [])

    def save_quality_gate_bundle_record(
        self,
        *,
        audit_events: list[dict[str, Any]] | None,
        checks: list[dict[str, Any]],
        run: dict[str, Any],
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_quality_gate_runs(cursor, {str(run["id"]): run})
                self.upsert_quality_gate_checks(
                    cursor,
                    {str(check["id"]): check for check in checks},
                )
                self._upsert_audit_events(cursor, audit_events or [])

    def save_agent_loop_bundle_record(
        self,
        *,
        audit_events: list[dict[str, Any]] | None,
        iterations: list[dict[str, Any]],
        run: dict[str, Any],
    ) -> None:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                self.upsert_agent_loop_runs(cursor, {str(run["id"]): run})
                self.upsert_agent_loop_iterations(
                    cursor,
                    {str(iteration["id"]): iteration for iteration in iterations},
                )
                self._upsert_audit_events(cursor, audit_events or [])

    def upsert_agent_loop_runs(
        self,
        cursor: Any,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        for run in runs.values():
            cursor.execute(
                """
                INSERT INTO agent_loop_runs (
                  id, ai_task_id, product_id, objective_json, status,
                  current_iteration, max_iterations, max_duration_seconds,
                  token_budget, cost_budget, token_used, cost_used,
                  context_manifest_id, context_version,
                  quality_gate_policy_id, stop_reason, started_at, finished_at,
                  version, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::jsonb, %s,
                  %s, %s, %s,
                  %s, %s, %s, %s,
                  %s, %s,
                  %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  objective_json = EXCLUDED.objective_json,
                  status = EXCLUDED.status,
                  current_iteration = EXCLUDED.current_iteration,
                  max_iterations = EXCLUDED.max_iterations,
                  max_duration_seconds = EXCLUDED.max_duration_seconds,
                  token_budget = EXCLUDED.token_budget,
                  cost_budget = EXCLUDED.cost_budget,
                  token_used = EXCLUDED.token_used,
                  cost_used = EXCLUDED.cost_used,
                  context_manifest_id = EXCLUDED.context_manifest_id,
                  context_version = EXCLUDED.context_version,
                  quality_gate_policy_id = EXCLUDED.quality_gate_policy_id,
                  stop_reason = EXCLUDED.stop_reason,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  version = EXCLUDED.version,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    run["id"],
                    run["ai_task_id"],
                    run.get("product_id"),
                    json.dumps(run.get("objective", {}), ensure_ascii=False),
                    run.get("status", "planning"),
                    int(run.get("current_iteration", 0)),
                    int(run.get("max_iterations", 3)),
                    int(run.get("max_duration_seconds", 3600)),
                    run.get("token_budget"),
                    run.get("cost_budget"),
                    int(run.get("token_used", 0)),
                    run.get("cost_used", 0),
                    run.get("context_manifest_id"),
                    int(run.get("context_version", 1)),
                    run.get("quality_gate_policy_id"),
                    run.get("stop_reason"),
                    run.get("started_at"),
                    run.get("finished_at"),
                    int(run.get("version", 1)),
                    run.get("created_by"),
                    run.get("created_at"),
                    run.get("updated_at") or run.get("created_at"),
                ),
            )

    def upsert_agent_loop_iterations(
        self,
        cursor: Any,
        iterations: dict[str, dict[str, Any]],
    ) -> None:
        for iteration in iterations.values():
            cursor.execute(
                """
                INSERT INTO agent_loop_iterations (
                  id, loop_run_id, iteration_number, coding_runner_task_id,
                  verifier_runner_task_id, quality_gate_run_id, status,
                  plan_json, change_summary, test_evidence, failure_analysis,
                  verification_summary, context_version, token_usage,
                  cost_amount, started_at, finished_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s,
                  %s, %s, %s,
                  %s::jsonb, %s, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s, %s,
                  %s, %s::timestamptz, %s::timestamptz,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  coding_runner_task_id = EXCLUDED.coding_runner_task_id,
                  verifier_runner_task_id = EXCLUDED.verifier_runner_task_id,
                  quality_gate_run_id = EXCLUDED.quality_gate_run_id,
                  status = EXCLUDED.status,
                  plan_json = EXCLUDED.plan_json,
                  change_summary = EXCLUDED.change_summary,
                  test_evidence = EXCLUDED.test_evidence,
                  failure_analysis = EXCLUDED.failure_analysis,
                  verification_summary = EXCLUDED.verification_summary,
                  context_version = EXCLUDED.context_version,
                  token_usage = EXCLUDED.token_usage,
                  cost_amount = EXCLUDED.cost_amount,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    iteration["id"],
                    iteration["loop_run_id"],
                    int(iteration["iteration_number"]),
                    iteration.get("coding_runner_task_id"),
                    iteration.get("verifier_runner_task_id"),
                    iteration.get("quality_gate_run_id"),
                    iteration.get("status", "planning"),
                    json.dumps(iteration.get("plan", {}), ensure_ascii=False),
                    iteration.get("change_summary"),
                    json.dumps(iteration.get("test_evidence", []), ensure_ascii=False),
                    json.dumps(iteration.get("failure_analysis", {}), ensure_ascii=False),
                    json.dumps(iteration.get("verification_summary", {}), ensure_ascii=False),
                    int(iteration.get("context_version", 1)),
                    int(iteration.get("token_usage", 0)),
                    iteration.get("cost_amount", 0),
                    iteration.get("started_at"),
                    iteration.get("finished_at"),
                    iteration.get("created_at"),
                    iteration.get("updated_at") or iteration.get("created_at"),
                ),
            )

    def upsert_quality_gate_runs(
        self,
        cursor: Any,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        for run in runs.values():
            cursor.execute(
                """
                INSERT INTO quality_gate_runs (
                  id, policy_id, policy_snapshot, phase, subject_type,
                  subject_id, product_id, context_manifest_id, status,
                  risk_level, independent_evidence_count, summary,
                  blocked_reasons, started_at, finished_at, created_by,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s::jsonb, %s, %s,
                  %s, %s, %s, %s,
                  %s, %s, %s,
                  %s::jsonb, %s::timestamptz, %s::timestamptz, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  policy_id = EXCLUDED.policy_id,
                  policy_snapshot = EXCLUDED.policy_snapshot,
                  context_manifest_id = EXCLUDED.context_manifest_id,
                  status = EXCLUDED.status,
                  risk_level = EXCLUDED.risk_level,
                  independent_evidence_count = EXCLUDED.independent_evidence_count,
                  summary = EXCLUDED.summary,
                  blocked_reasons = EXCLUDED.blocked_reasons,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    run["id"],
                    run.get("policy_id"),
                    json.dumps(run.get("policy_snapshot", {}), ensure_ascii=False),
                    run["phase"],
                    run["subject_type"],
                    run["subject_id"],
                    run.get("product_id"),
                    run.get("context_manifest_id"),
                    run.get("status", "pending"),
                    run.get("risk_level", "medium"),
                    int(run.get("independent_evidence_count", 0)),
                    run.get("summary"),
                    json.dumps(run.get("blocked_reasons", []), ensure_ascii=False),
                    run.get("started_at"),
                    run.get("finished_at"),
                    run.get("created_by"),
                    run.get("created_at"),
                    run.get("updated_at") or run.get("created_at"),
                ),
            )

    def upsert_quality_gate_checks(
        self,
        cursor: Any,
        checks: dict[str, dict[str, Any]],
    ) -> None:
        for check in checks.values():
            cursor.execute(
                """
                INSERT INTO quality_gate_checks (
                  id, quality_gate_run_id, check_type, status, source,
                  required, independent, evidence_ref, command_catalog_code,
                  exit_code, duration_ms, summary, details_json, started_at,
                  finished_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s, %s, %s,
                  %s, %s, %s, %s::jsonb, %s::timestamptz,
                  %s::timestamptz, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  status = EXCLUDED.status,
                  source = EXCLUDED.source,
                  required = EXCLUDED.required,
                  independent = EXCLUDED.independent,
                  evidence_ref = EXCLUDED.evidence_ref,
                  command_catalog_code = EXCLUDED.command_catalog_code,
                  exit_code = EXCLUDED.exit_code,
                  duration_ms = EXCLUDED.duration_ms,
                  summary = EXCLUDED.summary,
                  details_json = EXCLUDED.details_json,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    check["id"],
                    check["quality_gate_run_id"],
                    check["check_type"],
                    check.get("status", "pending"),
                    check.get("source", "platform_verifier"),
                    bool(check.get("required", True)),
                    bool(check.get("independent", False)),
                    check.get("evidence_ref"),
                    check.get("command_catalog_code"),
                    check.get("exit_code"),
                    check.get("duration_ms"),
                    check.get("summary"),
                    json.dumps(check.get("details", {}), ensure_ascii=False),
                    check.get("started_at"),
                    check.get("finished_at"),
                    check.get("created_at"),
                    check.get("updated_at") or check.get("created_at"),
                ),
            )

    def upsert_quality_gate_policies(
        self,
        cursor: Any,
        policies: dict[str, dict[str, Any]],
    ) -> None:
        for policy in policies.values():
            created_at = policy.get("created_at")
            updated_at = policy.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO quality_gate_policies (
                  id, name, product_id, task_type, phase, risk_levels,
                  required_checks, protected_paths, max_changed_files,
                  max_changed_lines, required_ci_contexts,
                  minimum_independent_evidence, manual_review_on_migration,
                  status, version, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::jsonb,
                  %s::jsonb, %s::jsonb, %s,
                  %s, %s::jsonb,
                  %s, %s,
                  %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  name = EXCLUDED.name,
                  product_id = EXCLUDED.product_id,
                  task_type = EXCLUDED.task_type,
                  phase = EXCLUDED.phase,
                  risk_levels = EXCLUDED.risk_levels,
                  required_checks = EXCLUDED.required_checks,
                  protected_paths = EXCLUDED.protected_paths,
                  max_changed_files = EXCLUDED.max_changed_files,
                  max_changed_lines = EXCLUDED.max_changed_lines,
                  required_ci_contexts = EXCLUDED.required_ci_contexts,
                  minimum_independent_evidence = EXCLUDED.minimum_independent_evidence,
                  manual_review_on_migration = EXCLUDED.manual_review_on_migration,
                  status = EXCLUDED.status,
                  version = EXCLUDED.version,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    policy["id"],
                    policy["name"],
                    policy.get("product_id"),
                    policy.get("task_type"),
                    policy["phase"],
                    json.dumps(policy.get("risk_levels", []), ensure_ascii=False),
                    json.dumps(policy.get("required_checks", []), ensure_ascii=False),
                    json.dumps(policy.get("protected_paths", []), ensure_ascii=False),
                    policy.get("max_changed_files"),
                    policy.get("max_changed_lines"),
                    json.dumps(policy.get("required_ci_contexts", []), ensure_ascii=False),
                    int(policy.get("minimum_independent_evidence", 1)),
                    bool(policy.get("manual_review_on_migration", True)),
                    policy.get("status", "active"),
                    int(policy.get("version", 1)),
                    policy.get("created_by"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_execution_context_manifests(
        self,
        cursor: Any,
        manifests: dict[str, dict[str, Any]],
    ) -> None:
        for manifest in manifests.values():
            cursor.execute(
                """
                INSERT INTO execution_context_manifests (
                  id, subject_type, subject_id, product_id, version,
                  content_hash, requirement_refs, bug_refs, repository_ref,
                  branch, knowledge_refs, acceptance_criteria,
                  permission_snapshot, retrieval_summary, truncation_summary,
                  iteration_context, created_by, created_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s, COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    manifest["id"],
                    manifest["subject_type"],
                    manifest["subject_id"],
                    manifest.get("product_id"),
                    int(manifest.get("version", 1)),
                    manifest["content_hash"],
                    json.dumps(manifest.get("requirement_refs", []), ensure_ascii=False),
                    json.dumps(manifest.get("bug_refs", []), ensure_ascii=False),
                    json.dumps(manifest.get("repository_ref", {}), ensure_ascii=False),
                    manifest.get("branch"),
                    json.dumps(manifest.get("knowledge_refs", []), ensure_ascii=False),
                    json.dumps(manifest.get("acceptance_criteria", []), ensure_ascii=False),
                    json.dumps(manifest.get("permission_snapshot", {}), ensure_ascii=False),
                    json.dumps(manifest.get("retrieval_summary", {}), ensure_ascii=False),
                    json.dumps(manifest.get("truncation_summary", {}), ensure_ascii=False),
                    json.dumps(manifest.get("iteration_context", {}), ensure_ascii=False),
                    manifest.get("created_by"),
                    manifest.get("created_at"),
                ),
            )

    def upsert_deployment_run_steps(
        self,
        cursor: Any,
        steps: dict[str, dict[str, Any]],
    ) -> None:
        for step in steps.values():
            created_at = step.get("created_at")
            updated_at = step.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO deployment_run_steps (
                  id, deployment_run_id, step_type, status, sequence,
                  quality_gate_run_id, summary, evidence_json, started_at,
                  finished_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s, %s::jsonb, %s::timestamptz,
                  %s::timestamptz, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  status = EXCLUDED.status,
                  quality_gate_run_id = EXCLUDED.quality_gate_run_id,
                  summary = EXCLUDED.summary,
                  evidence_json = EXCLUDED.evidence_json,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    step["id"],
                    step["deployment_run_id"],
                    step["step_type"],
                    step.get("status", "pending"),
                    int(step["sequence"]),
                    step.get("quality_gate_run_id"),
                    step.get("summary"),
                    json.dumps(step.get("evidence", {}), ensure_ascii=False),
                    step.get("started_at"),
                    step.get("finished_at"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_execution_resource_grants(
        self,
        cursor: Any,
        grants: dict[str, dict[str, Any]],
    ) -> None:
        for grant in grants.values():
            created_at = grant.get("created_at")
            updated_at = grant.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO execution_resource_grants (
                  id, product_id, environment, resource_type, resource_id,
                  target_code, status, version, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  status = EXCLUDED.status,
                  version = EXCLUDED.version,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    grant["id"],
                    grant["product_id"],
                    grant["environment"],
                    grant["resource_type"],
                    grant["resource_id"],
                    grant.get("target_code", ""),
                    grant.get("status", "active"),
                    int(grant.get("version") or 1),
                    grant.get("created_by"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_external_event_inbox(
        self,
        cursor: Any,
        events: dict[str, dict[str, Any]],
    ) -> None:
        for event in events.values():
            cursor.execute(
                """
                INSERT INTO external_event_inbox (
                  id, provider, event_type, delivery_id, signature_status,
                  payload_hash, payload_json, status, attempt_count,
                  lease_owner, lease_until, error_message, received_at,
                  processed_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s::jsonb, %s, %s,
                  %s, %s::timestamptz, %s,
                  COALESCE(%s::timestamptz, now()), %s::timestamptz,
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (provider, delivery_id) DO UPDATE SET
                  status = EXCLUDED.status,
                  attempt_count = EXCLUDED.attempt_count,
                  lease_owner = EXCLUDED.lease_owner,
                  lease_until = EXCLUDED.lease_until,
                  error_message = EXCLUDED.error_message,
                  processed_at = EXCLUDED.processed_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    event["id"],
                    event["provider"],
                    event["event_type"],
                    event["delivery_id"],
                    event["signature_status"],
                    event["payload_hash"],
                    json.dumps(event.get("payload", {}), ensure_ascii=False),
                    event.get("status", "pending"),
                    int(event.get("attempt_count") or 0),
                    event.get("lease_owner"),
                    event.get("lease_until"),
                    event.get("error_message"),
                    event.get("received_at"),
                    event.get("processed_at"),
                    event.get("updated_at"),
                ),
            )

    def upsert_execution_outbox_events(
        self,
        cursor: Any,
        events: dict[str, dict[str, Any]],
    ) -> None:
        for event in events.values():
            created_at = event.get("created_at")
            updated_at = event.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO execution_outbox_events (
                  id, aggregate_type, aggregate_id, event_type, idempotency_key,
                  payload_json, status, attempt_count, available_at,
                  lease_owner, lease_until, last_error, created_at, updated_at,
                  processed_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s::jsonb, %s, %s, COALESCE(%s::timestamptz, now()),
                  %s, %s::timestamptz, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now()), %s::timestamptz
                )
                ON CONFLICT (idempotency_key) DO UPDATE SET
                  payload_json = EXCLUDED.payload_json,
                  status = EXCLUDED.status,
                  attempt_count = EXCLUDED.attempt_count,
                  available_at = EXCLUDED.available_at,
                  lease_owner = EXCLUDED.lease_owner,
                  lease_until = EXCLUDED.lease_until,
                  last_error = EXCLUDED.last_error,
                  updated_at = EXCLUDED.updated_at,
                  processed_at = EXCLUDED.processed_at
                """,
                (
                    event["id"],
                    event["aggregate_type"],
                    event["aggregate_id"],
                    event["event_type"],
                    event["idempotency_key"],
                    json.dumps(event.get("payload", {}), ensure_ascii=False),
                    event.get("status", "pending"),
                    int(event.get("attempt_count", 0)),
                    event.get("available_at"),
                    event.get("lease_owner"),
                    event.get("lease_until"),
                    event.get("last_error"),
                    created_at,
                    updated_at,
                    event.get("processed_at"),
                ),
            )

    def _upsert_audit_events(
        self,
        cursor: Any,
        audit_events: list[dict[str, Any]],
    ) -> None:
        if not audit_events:
            return
        if self._upsert_audit_events_callback is not None:
            self._upsert_audit_events_callback(cursor, audit_events)
            return
        self._audit_repository.upsert_audit_events(cursor, audit_events)

    @staticmethod
    def _lock_version(
        cursor: Any,
        *,
        expected_version: int | None,
        record_id: str,
        table_name: str,
    ) -> None:
        if expected_version is None:
            return
        cursor.execute(
            f"SELECT version FROM {table_name} WHERE id = %s FOR UPDATE",
            (record_id,),
        )
        row = cursor.fetchone()
        current_version = int(row[0]) if row is not None else None
        if current_version != expected_version:
            raise ExecutionGovernanceVersionConflictError(current_version)
