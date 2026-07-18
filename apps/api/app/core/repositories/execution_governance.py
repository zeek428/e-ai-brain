from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.execution_governance_writes import (
    ExecutionGovernanceWriteRepository,
)


def _without_none(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if value is not None}


class ExecutionGovernanceReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._write_repository = ExecutionGovernanceWriteRepository(
            connect,
            upsert_audit_events=upsert_audit_events,
        )

    def save_trusted_delivery_record(
        self,
        *,
        record: dict[str, Any],
        record_type: str,
    ) -> None:
        """Expose the paired write adapter for worker heartbeat persistence."""
        self._write_repository.save_trusted_delivery_record(
            record=record,
            record_type=record_type,
        )

    def save_rd_delivery_evidence_record(
        self,
        *,
        record: dict[str, Any],
        record_type: str,
    ) -> None:
        """Persist P0 Git/reconciliation/readiness evidence by semantic boundary."""
        self._write_repository.save_rd_delivery_evidence_record(
            record=record,
            record_type=record_type,
        )

    def list_quality_gate_policies(
        self,
        *,
        phase: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in (
            ("product_id", product_id),
            ("task_type", task_type),
            ("phase", phase),
            ("status", status),
        ):
            if value is not None:
                clauses.append(f"{field} = %s")
                params.append(value)
        if product_scope_ids is not None:
            normalized_scope = [
                str(scope_id) for scope_id in product_scope_ids if str(scope_id).strip()
            ]
            if normalized_scope:
                clauses.append("(product_id IS NULL OR product_id = ANY(%s))")
                params.append(normalized_scope)
            else:
                clauses.append("product_id IS NULL")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, name, product_id, task_type, phase, risk_levels,
                           required_checks, protected_paths, max_changed_files,
                           max_changed_lines, required_ci_contexts,
                           minimum_independent_evidence,
                           manual_review_on_migration, status, version, created_by,
                           created_at, updated_at
                    FROM quality_gate_policies
                    {where}
                    ORDER BY product_id NULLS LAST, task_type NULLS FIRST,
                             phase, version DESC, id
                    """,
                    tuple(params),
                )
                return [self._quality_gate_policy_from_row(row) for row in cursor.fetchall()]

    def get_quality_gate_policy(self, policy_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, product_id, task_type, phase, risk_levels,
                           required_checks, protected_paths, max_changed_files,
                           max_changed_lines, required_ci_contexts,
                           minimum_independent_evidence,
                           manual_review_on_migration, status, version, created_by,
                           created_at, updated_at
                    FROM quality_gate_policies
                    WHERE id = %s
                    """,
                    (policy_id,),
                )
                row = cursor.fetchone()
        return self._quality_gate_policy_from_row(row) if row else None

    def list_execution_context_manifests(
        self,
        *,
        product_scope_ids: list[str] | None = None,
        subject_id: str | None = None,
        subject_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if subject_type is not None:
            clauses.append("subject_type = %s")
            params.append(subject_type)
        if subject_id is not None:
            clauses.append("subject_id = %s")
            params.append(subject_id)
        if product_scope_ids is not None:
            normalized_scope = [str(item) for item in product_scope_ids if str(item).strip()]
            if normalized_scope:
                clauses.append("product_id = ANY(%s)")
                params.append(normalized_scope)
            else:
                clauses.append("FALSE")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, subject_type, subject_id, product_id, version,
                           content_hash, requirement_refs, bug_refs, repository_ref,
                           branch, knowledge_refs, acceptance_criteria,
                           permission_snapshot, retrieval_summary, truncation_summary,
                           iteration_context, created_by, created_at
                    FROM execution_context_manifests
                    {where}
                    ORDER BY created_at DESC, version DESC, id
                    """,
                    tuple(params),
                )
                return [self._context_manifest_from_row(row) for row in cursor.fetchall()]

    def list_quality_gate_runs(
        self,
        *,
        phase: str | None = None,
        product_scope_ids: list[str] | None = None,
        subject_id: str | None = None,
        subject_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in (
            ("phase", phase),
            ("subject_type", subject_type),
            ("subject_id", subject_id),
        ):
            if value is not None:
                clauses.append(f"{field} = %s")
                params.append(value)
        if product_scope_ids is not None:
            normalized_scope = [str(item) for item in product_scope_ids if str(item).strip()]
            if normalized_scope:
                clauses.append("product_id = ANY(%s)")
                params.append(normalized_scope)
            else:
                clauses.append("FALSE")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, policy_id, policy_snapshot, phase, subject_type,
                           subject_id, product_id, context_manifest_id, status,
                           risk_level, independent_evidence_count, summary,
                           blocked_reasons, started_at, finished_at, created_by,
                           created_at, updated_at
                    FROM quality_gate_runs
                    {where}
                    ORDER BY created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._quality_gate_run_from_row(row) for row in cursor.fetchall()]

    def list_quality_gate_checks(self, quality_gate_run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, quality_gate_run_id, check_type, status, source,
                           required, independent, evidence_ref,
                           command_catalog_code, exit_code, duration_ms, summary,
                           details_json, started_at, finished_at, created_at,
                           updated_at
                    FROM quality_gate_checks
                    WHERE quality_gate_run_id = %s
                    ORDER BY created_at, id
                    """,
                    (quality_gate_run_id,),
                )
                return [self._quality_gate_check_from_row(row) for row in cursor.fetchall()]

    def list_execution_attestations(
        self,
        *,
        subject_id: str | None = None,
        runner_task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in (("subject_id", subject_id), ("runner_task_id", runner_task_id)):
            if value is not None:
                clauses.append(f"{field} = %s")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, subject_type, subject_id, runner_task_id, runner_id,
                           trust_domain, trust_boundary_id, payload_json, payload_sha256,
                           signature, public_key_fingerprint, verification_status,
                           verification_error_code, verified_at, created_at, updated_at
                    FROM execution_attestations
                    {where}
                    ORDER BY created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._execution_attestation_from_row(row) for row in cursor.fetchall()]

    def list_trusted_delivery_records(
        self,
        *,
        product_scope_ids: list[str] | None = None,
        record_type: str,
    ) -> list[dict[str, Any]]:
        clauses = ["record_type = %s"]
        params: list[Any] = [record_type]
        if product_scope_ids is not None:
            normalized_scope = [str(item) for item in product_scope_ids if str(item).strip()]
            if normalized_scope:
                clauses.append("product_id = ANY(%s)")
                params.append(normalized_scope)
            else:
                clauses.append("FALSE")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, payload_json, created_at, updated_at
                    FROM trusted_delivery_records
                    WHERE {" AND ".join(clauses)}
                    ORDER BY updated_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [
                    {
                        **(row[2] or {}),
                        "id": row[0],
                        "product_id": row[1],
                        "created_at": row[3],
                        "updated_at": row[4],
                    }
                    for row in cursor.fetchall()
                ]

    def list_rd_delivery_evidence_records(
        self,
        *,
        record_type: str,
        product_scope_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return self.list_trusted_delivery_records(
            product_scope_ids=product_scope_ids,
            record_type=record_type,
        )

    def list_agent_loop_runs(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if ai_task_id is not None:
            clauses.append("ai_task_id = %s")
            params.append(ai_task_id)
        if product_scope_ids is not None:
            normalized_scope = [str(item) for item in product_scope_ids if str(item).strip()]
            if normalized_scope:
                clauses.append("product_id = ANY(%s)")
                params.append(normalized_scope)
            else:
                clauses.append("FALSE")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, ai_task_id, product_id, objective_json, status,
                           current_iteration, max_iterations, max_duration_seconds,
                           token_budget, cost_budget, token_used, cost_used,
                           context_manifest_id, context_version,
                           quality_gate_policy_id, stop_reason, started_at,
                           finished_at, version, created_by, created_at, updated_at
                    FROM agent_loop_runs
                    {where}
                    ORDER BY created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._agent_loop_run_from_row(row) for row in cursor.fetchall()]

    def list_agent_loop_iterations(self, loop_run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, loop_run_id, iteration_number,
                           coding_runner_task_id, verifier_runner_task_id,
                           quality_gate_run_id, status, plan_json,
                           change_summary, test_evidence, failure_analysis,
                           verification_summary, context_version, token_usage,
                           cost_amount, started_at, finished_at, created_at,
                           updated_at
                    FROM agent_loop_iterations
                    WHERE loop_run_id = %s
                    ORDER BY iteration_number, id
                    """,
                    (loop_run_id,),
                )
                return [self._agent_loop_iteration_from_row(row) for row in cursor.fetchall()]

    def list_execution_resource_grants(
        self,
        *,
        environment: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        resource_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in (
            ("product_id", product_id),
            ("environment", environment),
            ("resource_type", resource_type),
            ("status", status),
        ):
            if value is not None:
                clauses.append(f"{field} = %s")
                params.append(value)
        if product_scope_ids is not None:
            normalized_scope = [str(item) for item in product_scope_ids if str(item).strip()]
            if normalized_scope:
                clauses.append("product_id = ANY(%s)")
                params.append(normalized_scope)
            else:
                clauses.append("FALSE")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, environment, resource_type, resource_id,
                           target_code, status, version, created_by, created_at,
                           updated_at
                    FROM execution_resource_grants
                    {where}
                    ORDER BY product_id, environment, resource_type, resource_id,
                             target_code
                    """,
                    tuple(params),
                )
                return [self._resource_grant_from_row(row) for row in cursor.fetchall()]

    def claim_execution_outbox_events(
        self,
        *,
        lease_seconds: int,
        limit: int,
        worker_id: str,
    ) -> list[dict[str, Any]]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    WITH claimed AS (
                      SELECT id
                      FROM execution_outbox_events
                      WHERE status IN ('pending', 'failed', 'processing')
                        AND available_at <= now()
                        AND (lease_until IS NULL OR lease_until <= now())
                      ORDER BY available_at, created_at, id
                      FOR UPDATE SKIP LOCKED
                      LIMIT %s
                    )
                    UPDATE execution_outbox_events event
                    SET status = 'processing',
                        attempt_count = event.attempt_count + 1,
                        lease_owner = %s,
                        lease_until = now() + (%s * interval '1 second'),
                        updated_at = now()
                    FROM claimed
                    WHERE event.id = claimed.id
                    RETURNING event.id, event.aggregate_type, event.aggregate_id,
                              event.event_type, event.idempotency_key,
                              event.payload_json, event.status, event.attempt_count,
                              event.available_at, event.lease_owner,
                              event.lease_until, event.last_error, event.created_at,
                              event.updated_at, event.processed_at
                    """,
                    (limit, worker_id, lease_seconds),
                )
                return [self._outbox_event_from_row(row) for row in cursor.fetchall()]

    def list_execution_outbox_events(
        self,
        *,
        aggregate_id: str | None = None,
        aggregate_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in (
            ("aggregate_type", aggregate_type),
            ("aggregate_id", aggregate_id),
            ("status", status),
        ):
            if value is not None:
                clauses.append(f"{field} = %s")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, aggregate_type, aggregate_id, event_type,
                           idempotency_key, payload_json, status, attempt_count,
                           available_at, lease_owner, lease_until, last_error,
                           created_at, updated_at, processed_at
                    FROM execution_outbox_events
                    {where}
                    ORDER BY created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._outbox_event_from_row(row) for row in cursor.fetchall()]

    def list_deployment_run_steps(
        self,
        *,
        deployment_run_id: str,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, deployment_run_id, step_type, status, sequence,
                           quality_gate_run_id, summary, evidence_json,
                           started_at, finished_at, created_at, updated_at
                    FROM deployment_run_steps
                    WHERE deployment_run_id = %s
                    ORDER BY sequence, id
                    """,
                    (deployment_run_id,),
                )
                return [self._deployment_run_step_from_row(row) for row in cursor.fetchall()]

    def claim_external_event_inbox(
        self,
        *,
        lease_seconds: int,
        limit: int,
        worker_id: str,
    ) -> list[dict[str, Any]]:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    WITH claimed AS (
                      SELECT id
                      FROM external_event_inbox
                      WHERE status IN ('pending', 'failed', 'processing')
                        AND signature_status IN ('verified', 'not_applicable')
                        AND (lease_until IS NULL OR lease_until <= now())
                      ORDER BY received_at, id
                      FOR UPDATE SKIP LOCKED
                      LIMIT %s
                    )
                    UPDATE external_event_inbox event
                    SET status = 'processing',
                        attempt_count = event.attempt_count + 1,
                        lease_owner = %s,
                        lease_until = now() + (%s * interval '1 second'),
                        updated_at = now()
                    FROM claimed
                    WHERE event.id = claimed.id
                    RETURNING event.id, event.provider, event.event_type,
                              event.delivery_id, event.signature_status,
                              event.payload_hash, event.payload_json, event.status,
                              event.attempt_count, event.lease_owner,
                              event.lease_until, event.error_message,
                              event.received_at, event.processed_at, event.updated_at
                    """,
                    (limit, worker_id, lease_seconds),
                )
                return [self._external_event_from_row(row) for row in cursor.fetchall()]

    def list_external_event_inbox(
        self,
        *,
        delivery_id: str | None = None,
        provider: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in (
            ("provider", provider),
            ("delivery_id", delivery_id),
            ("status", status),
        ):
            if value is not None:
                clauses.append(f"{field} = %s")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, provider, event_type, delivery_id,
                           signature_status, payload_hash, payload_json, status,
                           attempt_count, lease_owner, lease_until, error_message,
                           received_at, processed_at, updated_at
                    FROM external_event_inbox
                    {where}
                    ORDER BY received_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._external_event_from_row(row) for row in cursor.fetchall()]

    def save_quality_gate_policy_record(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.save_quality_gate_policy_record(*args, **kwargs)

    def save_execution_context_manifest_record(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._write_repository.save_execution_context_manifest_record(*args, **kwargs)

    def save_execution_attestation_record(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.save_execution_attestation_record(*args, **kwargs)

    def save_execution_resource_grant_record(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.save_execution_resource_grant_record(*args, **kwargs)

    def save_external_event_inbox_record(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.save_external_event_inbox_record(*args, **kwargs)

    def save_quality_gate_bundle_record(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.save_quality_gate_bundle_record(*args, **kwargs)

    def save_agent_loop_bundle_record(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.save_agent_loop_bundle_record(*args, **kwargs)

    def save_deployment_dispatch_result_transaction(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._write_repository.save_deployment_dispatch_result_transaction(*args, **kwargs)

    def save_execution_outbox_event_record(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.save_execution_outbox_event_record(*args, **kwargs)

    def save_deployment_run_steps_records(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.save_deployment_run_steps_records(*args, **kwargs)

    def create_deployment_dispatch_transaction(self, *args: Any, **kwargs: Any) -> None:
        self._write_repository.create_deployment_dispatch_transaction(*args, **kwargs)

    def save_deployment_dispatch_failure_transaction(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._write_repository.save_deployment_dispatch_failure_transaction(
            *args,
            **kwargs,
        )

    @staticmethod
    def _quality_gate_policy_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "name": row[1],
                "product_id": row[2],
                "task_type": row[3],
                "phase": row[4],
                "risk_levels": row[5] or [],
                "required_checks": row[6] or [],
                "protected_paths": row[7] or [],
                "max_changed_files": row[8],
                "max_changed_lines": row[9],
                "required_ci_contexts": row[10] or [],
                "minimum_independent_evidence": row[11],
                "manual_review_on_migration": row[12],
                "status": row[13],
                "version": row[14],
                "created_by": row[15],
                "created_at": row[16],
                "updated_at": row[17],
            }
        )

    @staticmethod
    def _context_manifest_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "subject_type": row[1],
                "subject_id": row[2],
                "product_id": row[3],
                "version": row[4],
                "content_hash": row[5],
                "requirement_refs": row[6] or [],
                "bug_refs": row[7] or [],
                "repository_ref": row[8] or {},
                "branch": row[9],
                "knowledge_refs": row[10] or [],
                "acceptance_criteria": row[11] or [],
                "permission_snapshot": row[12] or {},
                "retrieval_summary": row[13] or {},
                "truncation_summary": row[14] or {},
                "iteration_context": row[15] or {},
                "created_by": row[16],
                "created_at": row[17],
            }
        )

    @staticmethod
    def _quality_gate_run_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "policy_id": row[1],
                "policy_snapshot": row[2] or {},
                "phase": row[3],
                "subject_type": row[4],
                "subject_id": row[5],
                "product_id": row[6],
                "context_manifest_id": row[7],
                "status": row[8],
                "risk_level": row[9],
                "independent_evidence_count": row[10],
                "summary": row[11],
                "blocked_reasons": row[12] or [],
                "started_at": row[13],
                "finished_at": row[14],
                "created_by": row[15],
                "created_at": row[16],
                "updated_at": row[17],
            }
        )

    @staticmethod
    def _quality_gate_check_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "quality_gate_run_id": row[1],
                "check_type": row[2],
                "status": row[3],
                "source": row[4],
                "required": row[5],
                "independent": row[6],
                "evidence_ref": row[7],
                "command_catalog_code": row[8],
                "exit_code": row[9],
                "duration_ms": row[10],
                "summary": row[11],
                "details": row[12] or {},
                "started_at": row[13],
                "finished_at": row[14],
                "created_at": row[15],
                "updated_at": row[16],
            }
        )

    @staticmethod
    def _execution_attestation_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "subject_type": row[1],
                "subject_id": row[2],
                "runner_task_id": row[3],
                "runner_id": row[4],
                "trust_domain": row[5],
                "trust_boundary_id": row[6],
                "payload": row[7] or {},
                "payload_sha256": row[8],
                "signature": row[9],
                "public_key_fingerprint": row[10],
                "verification_status": row[11],
                "verification_error_code": row[12],
                "verified_at": row[13],
                "created_at": row[14],
                "updated_at": row[15],
            }
        )

    @staticmethod
    def _agent_loop_run_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "ai_task_id": row[1],
                "product_id": row[2],
                "objective": row[3] or {},
                "status": row[4],
                "current_iteration": row[5],
                "max_iterations": row[6],
                "max_duration_seconds": row[7],
                "token_budget": row[8],
                "cost_budget": float(row[9]) if row[9] is not None else None,
                "token_used": row[10],
                "cost_used": float(row[11] or 0),
                "context_manifest_id": row[12],
                "context_version": row[13],
                "quality_gate_policy_id": row[14],
                "stop_reason": row[15],
                "started_at": row[16],
                "finished_at": row[17],
                "version": row[18],
                "created_by": row[19],
                "created_at": row[20],
                "updated_at": row[21],
            }
        )

    @staticmethod
    def _agent_loop_iteration_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "loop_run_id": row[1],
                "iteration_number": row[2],
                "coding_runner_task_id": row[3],
                "verifier_runner_task_id": row[4],
                "quality_gate_run_id": row[5],
                "status": row[6],
                "plan": row[7] or {},
                "change_summary": row[8],
                "test_evidence": row[9] or [],
                "failure_analysis": row[10] or {},
                "verification_summary": row[11] or {},
                "context_version": row[12],
                "token_usage": row[13],
                "cost_amount": float(row[14] or 0),
                "started_at": row[15],
                "finished_at": row[16],
                "created_at": row[17],
                "updated_at": row[18],
            }
        )

    @staticmethod
    def _resource_grant_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "product_id": row[1],
                "environment": row[2],
                "resource_type": row[3],
                "resource_id": row[4],
                "target_code": row[5],
                "status": row[6],
                "version": row[7],
                "created_by": row[8],
                "created_at": row[9],
                "updated_at": row[10],
            }
        )

    @staticmethod
    def _outbox_event_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "aggregate_type": row[1],
                "aggregate_id": row[2],
                "event_type": row[3],
                "idempotency_key": row[4],
                "payload": row[5] or {},
                "status": row[6],
                "attempt_count": row[7],
                "available_at": row[8],
                "lease_owner": row[9],
                "lease_until": row[10],
                "last_error": row[11],
                "created_at": row[12],
                "updated_at": row[13],
                "processed_at": row[14],
            }
        )

    @staticmethod
    def _external_event_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "provider": row[1],
                "event_type": row[2],
                "delivery_id": row[3],
                "signature_status": row[4],
                "payload_hash": row[5],
                "payload": row[6] or {},
                "status": row[7],
                "attempt_count": row[8],
                "lease_owner": row[9],
                "lease_until": row[10],
                "error_message": row[11],
                "received_at": row[12],
                "processed_at": row[13],
                "updated_at": row[14],
            }
        )

    @staticmethod
    def _deployment_run_step_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return _without_none(
            {
                "id": row[0],
                "deployment_run_id": row[1],
                "step_type": row[2],
                "status": row[3],
                "sequence": row[4],
                "quality_gate_run_id": row[5],
                "summary": row[6],
                "evidence": row[7] or {},
                "started_at": row[8],
                "finished_at": row[9],
                "created_at": row[10],
                "updated_at": row[11],
            }
        )
