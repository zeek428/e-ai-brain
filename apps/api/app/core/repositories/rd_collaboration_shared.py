from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from contextlib import AbstractContextManager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb

from app.services.rd_policy_resolution import PolicyResolutionError, merge_policy_payloads


class RdCollaborationRepositoryError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class RdCollaborationVersionConflictError(RdCollaborationRepositoryError):
    def __init__(self, current_version: int | None) -> None:
        super().__init__(
            "RD_VERSION_CONFLICT",
            "R&D collaboration record version conflict",
            details={"current_version": current_version},
        )
        self.current_version = current_version


JSON_FIELDS = {
    "acceptance_criteria",
    "answer_actor_selector",
    "answer_json",
    "answer_schema",
    "assignable_subject_types",
    "budget_config",
    "budget_json",
    "candidate_ai_employee_ids",
    "candidate_human_user_ids",
    "capabilities",
    "capability_tags",
    "conclusion_json",
    "content",
    "context_config",
    "context_cursor",
    "cost_summary",
    "decision_actor_selector",
    "dependency_summary",
    "deterministic_validation",
    "effort_estimate",
    "escalation_target_selector",
    "evidence_json",
    "evidence_refs",
    "failure_json",
    "fallback_executor_profile_ids",
    "handoff_summary",
    "input_contract",
    "input_json",
    "llm_suggestion",
    "operations_json",
    "options_json",
    "output_contract",
    "payload_json",
    "persona_json",
    "policy_proposal_json",
    "proposed_policy_json",
    "assessment_evidence",
    "product_scope",
    "recommendation_json",
    "resume_metadata",
    "release_conditions",
    "repository_trust_domains",
    "required_permissions",
    "responsibilities",
    "responsibility_scope",
    "result_json",
    "rework_evidence",
    "reviewer_role_codes",
    "risk_scope",
    "risk_summary",
    "structured_assessment",
    "strategy_config",
    "supported_role_codes",
    "tool_config",
    "tool_trust_domains",
    "workspace_capabilities",
    "work_style_json",
}


TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "rd_role_definitions": (
        "id",
        "brain_app_id",
        "code",
        "name",
        "capabilities",
        "responsibilities",
        "maximum_risk_level",
        "assignable_subject_types",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    ),
    "rd_ai_employees": (
        "id",
        "brain_app_id",
        "code",
        "name",
        "capability_tags",
        "persona_version",
        "persona_json",
        "work_style_version",
        "work_style_json",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    ),
    "rd_executor_profiles": (
        "id",
        "brain_app_id",
        "code",
        "name",
        "executor_type",
        "runner_id",
        "model_gateway_config_id",
        "credential_ref",
        "workspace_capabilities",
        "max_concurrency",
        "supported_role_codes",
        "health_status",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    ),
    "rd_task_executor_policy_role_bindings": (
        "id",
        "policy_id",
        "role_code",
        "actor_mode",
        "candidate_human_user_ids",
        "candidate_ai_employee_ids",
        "primary_executor_profile_id",
        "fallback_executor_profile_ids",
        "repository_trust_domains",
        "tool_trust_domains",
        "context_config",
        "tool_config",
        "budget_config",
        "reviewer_role_codes",
        "required_permissions",
        "status",
        "created_at",
        "updated_at",
    ),
    "rd_run_seats": (
        "id",
        "collaboration_run_id",
        "role_code",
        "subject_type",
        "human_user_id",
        "ai_employee_id",
        "executor_profile_id",
        "responsibility_scope",
        "capacity",
        "status",
        "replaces_seat_id",
        "created_at",
        "updated_at",
    ),
    "rd_role_sessions": (
        "id",
        "collaboration_run_id",
        "seat_id",
        "session_no",
        "handoff_summary",
        "context_cursor",
        "resume_metadata",
        "status",
        "started_at",
        "ended_at",
        "created_at",
        "updated_at",
    ),
    "rd_work_items": (
        "id",
        "collaboration_run_id",
        "plan_version",
        "requirement_id",
        "work_item_type",
        "title",
        "objective",
        "owner_seat_id",
        "input_contract",
        "output_contract",
        "acceptance_criteria",
        "status",
        "resume_state",
        "suspended_attempt_id",
        "suspended_decision_request_id",
        "suspended_at",
        "release_conditions",
        "risk_level",
        "priority",
        "ai_task_id",
        "reviewer_seat_id",
        "lease_owner",
        "lease_expires_at",
        "idempotency_key",
        "version",
        "created_at",
        "updated_at",
    ),
    "rd_work_item_dependencies": (
        "id",
        "collaboration_run_id",
        "plan_version",
        "predecessor_work_item_id",
        "successor_work_item_id",
        "dependency_type",
        "status",
        "satisfied_at",
        "created_at",
        "updated_at",
    ),
    "rd_collaboration_events": (
        "id",
        "collaboration_run_id",
        "event_type",
        "event_key",
        "subject_type",
        "subject_id",
        "payload_json",
        "occurred_at",
        "processed_at",
        "created_at",
        "updated_at",
    ),
    "requirement_assessment_executions": (
        "id",
        "assessment_id",
        "opinion_id",
        "role_code",
        "runner_id",
        "model_invocation_id",
        "result_summary",
        "actor_type",
        "human_user_id",
        "ai_employee_id",
        "executor_profile_id",
        "input_revision",
        "strategy_snapshot_id",
        "execution_kind",
        "side_effect_policy",
        "status",
        "created_at",
        "updated_at",
    ),
}


POLICY_COLUMNS = (
    "id",
    "name",
    "brain_app_id",
    "product_id",
    "task_type",
    "executor_type",
    "runner_id",
    "repository_id",
    "workspace_root",
    "branch",
    "instruction_template",
    "output_contract",
    "timeout_seconds",
    "priority",
    "status",
    "code_change_review_mode",
    "autonomy_mode",
    "max_iterations",
    "max_duration_seconds",
    "token_budget",
    "cost_budget",
    "quality_gate_policy_id",
    "auto_merge_risk_threshold",
    "strategy_config",
    "created_by",
    "created_at",
    "updated_at",
)


def _adapt(value: Any, field: str) -> Any:
    if field in JSON_FIELDS and value is not None:
        return Jsonb(value)
    return value


def _row_dict(cursor: Any, row: Sequence[Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        getattr(description, "name", description[0]): value
        for description, value in zip(cursor.description, row, strict=True)
    }


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _json_response_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Make command replay snapshots JSONB-safe without losing their response shape."""
    return json.loads(json.dumps(payload, default=str))


def _response_hash(response: dict[str, Any]) -> str:
    stable = deepcopy(response)
    stable.pop("trace_id", None)
    if isinstance(stable.get("data"), dict):
        stable["data"].pop("idempotent_replay", None)
    stable.pop("idempotent_replay", None)
    return _canonical_hash(stable)


SCOPE_OPERATION_FIELDS: dict[str, tuple[str, ...]] = {
    "add_requirement": (
        "requirement_id",
        "requirement_revision",
        "assessment_id",
        "final_strategy_snapshot_id",
    ),
    "remove_requirement": ("requirement_id", "destination"),
    "replace_requirement_snapshot": (
        "requirement_id",
        "requirement_revision",
        "assessment_id",
        "final_strategy_snapshot_id",
    ),
    "update_repository_baseline": (
        "repository_id",
        "branch_config_version",
        "base_commit_sha",
    ),
}


def _canonical_scope_operations(operations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    for position, operation in enumerate(operations):
        kind = str(operation.get("op") or "")
        fields = SCOPE_OPERATION_FIELDS.get(kind)
        if fields is None:
            raise RdCollaborationRepositoryError(
                "RD_SCOPE_CHANGE_INVALID",
                "scope change operation kind is invalid",
                details={"operation_index": position, "field": "op"},
            )
        missing = [field for field in fields if operation.get(field) is None]
        if missing:
            raise RdCollaborationRepositoryError(
                "RD_SCOPE_CHANGE_INVALID",
                "scope change operation is missing required fields",
                details={"operation_index": position, "field": missing[0]},
            )
        if kind == "remove_requirement" and operation.get("destination") != "approved_pool":
            raise RdCollaborationRepositoryError(
                "RD_SCOPE_CHANGE_INVALID",
                "removed requirements must return to the approved pool",
                details={"operation_index": position, "field": "destination"},
            )
        canonical.append(
            {
                "position": position,
                "op": kind,
                **{field: operation[field] for field in fields},
            }
        )
    return canonical


class RdCollaborationTransaction:
    """One cursor shared by a command and every collaboration side effect."""

    def __init__(self, repository: Any, cursor: Any) -> None:
        self._repository = repository
        self.cursor = cursor

    def __getattr__(self, name: str) -> Any:
        # Keep raw cursor operations available to existing command callbacks while
        # giving orchestrators explicit cursor-level domain methods.
        return getattr(self.cursor, name)

    def claim_ready_work_item(
        self,
        work_item_id: str,
        *,
        lease_owner: str,
        lease_seconds: int = 900,
        expected_version: int | None = None,
        attempt: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self._repository._claim_ready_work_item_cursor(
            self.cursor,
            work_item_id,
            lease_owner=lease_owner,
            lease_seconds=lease_seconds,
            expected_version=expected_version,
            attempt=attempt,
        )

    def save_rd_task_executor_policy_record(
        self,
        record: dict[str, Any],
        *,
        expected_policy_version: int | None = None,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._repository._save_rd_task_executor_policy_record_cursor(
            self.cursor,
            record,
            expected_policy_version=expected_policy_version,
            audit_event=audit_event,
        )

    def save_rd_role_definition_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._repository._save_simple_cursor(
            self.cursor,
            "rd_role_definitions",
            record,
        )

    def save_rd_ai_employee_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._repository._save_simple_cursor(
            self.cursor,
            "rd_ai_employees",
            record,
        )

    def save_rd_executor_profile_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._repository._save_simple_cursor(
            self.cursor,
            "rd_executor_profiles",
            record,
        )

    def save_rd_policy_role_binding_record(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        return self._repository._save_simple_cursor(
            self.cursor,
            "rd_task_executor_policy_role_bindings",
            record,
        )

    def save_rd_task_executor_policy_role_binding_record(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        return self.save_rd_policy_role_binding_record(record)

    def freeze_base_policy_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return self._repository._freeze_base_policy_snapshot_cursor(self.cursor, snapshot)

    def get_rd_policy_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        self.cursor.execute(
            "SELECT * FROM rd_task_executor_policy_snapshots WHERE id = %s",
            (snapshot_id,),
        )
        return self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())

    def derive_assessment_policy_snapshot(
        self,
        *,
        base_snapshot_id: str,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        return self._repository._derive_assessment_policy_snapshot_cursor(
            self.cursor,
            base_snapshot_id=base_snapshot_id,
            snapshot=snapshot,
        )

    def merge_version_policy_snapshot_with_sources(
        self,
        *,
        snapshot: dict[str, Any],
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._repository._merge_version_policy_snapshot_with_sources_cursor(
            self.cursor,
            snapshot=snapshot,
            sources=sources,
        )

    def save_assessment_bundle(
        self,
        *,
        assessment: dict[str, Any],
        opinions: list[dict[str, Any]],
        snapshots: list[dict[str, Any]] | None = None,
        executions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self._repository._save_assessment_bundle_cursor(
            self.cursor,
            assessment=assessment,
            opinions=opinions,
            snapshots=snapshots,
            executions=executions,
        )

    def dispatch_ai_assessment_execution(self, task: dict[str, Any]) -> dict[str, Any]:
        """Create the runner task and bind it to its frozen execution in this cursor."""
        self._repository.upsert_ai_executor_tasks(self.cursor, {task["id"]: task})
        self.cursor.execute(
            """
            UPDATE requirement_assessment_executions
            SET ai_executor_task_id = %s, runner_id = %s, updated_at = now()
            WHERE id = %s AND ai_executor_task_id IS NULL
            RETURNING *
            """,
            (
                task["id"],
                task["runner_id"],
                task["input_payload"]["assessment_execution_id"],
            ),
        )
        execution = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if execution is None:
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_EXECUTION_CONFLICT",
                "Assessment execution is already dispatched or missing",
            )
        return execution

    def complete_ai_assessment_runner_task(
        self,
        *,
        task: dict[str, Any],
        assessment_id: str,
        execution_id: str,
        executor_profile_id: str,
        runner_id: str,
        model_invocation_id: str,
        audit_event: dict[str, Any],
        outbox_event: dict[str, Any],
    ) -> dict[str, Any]:
        """Commit the frozen runner task, gateway evidence, opinion and event trail together."""
        self.cursor.execute(
            """
            SELECT id, runner_id, status, input_payload
            FROM ai_executor_tasks WHERE id = %s FOR UPDATE
            """,
            (task["id"],),
        )
        persisted_task = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if persisted_task is None or persisted_task["runner_id"] != runner_id:
            raise RdCollaborationRepositoryError("NOT_FOUND", "AI executor task not found")
        if persisted_task["status"] in {"succeeded", "failed", "cancelled"}:
            raise RdCollaborationRepositoryError(
                "AI_EXECUTOR_TASK_TERMINAL", "Terminal task cannot be completed"
            )
        input_payload = persisted_task.get("input_payload") or {}
        if input_payload.get("assessment_execution_id") != execution_id:
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_EXECUTION_INVALID", "Runner task is not bound to this execution"
            )
        self.cursor.execute(
            """
            SELECT execution.*, assessment.product_id
            FROM requirement_assessment_executions execution
            JOIN requirement_assessments assessment ON assessment.id = execution.assessment_id
            WHERE execution.id = %s AND execution.assessment_id = %s
            FOR UPDATE OF execution, assessment
            """,
            (execution_id, assessment_id),
        )
        execution = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if execution is None or execution.get("status") != "pending":
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_EXECUTION_INVALID",
                "Assessment execution is not eligible for completion",
            )
        if (
            execution.get("ai_executor_task_id") != task["id"]
            or execution.get("runner_id") != runner_id
            or execution.get("executor_profile_id") != executor_profile_id
        ):
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_EXECUTION_INVALID", "Runner task provenance does not match execution"
            )
        self.cursor.execute(
            """
            SELECT id, status, executor_profile_id, product_id, requirement_revision,
                   strategy_snapshot_id, ai_executor_task_id, assessment_execution_id, output_json,
                   output_digest
            FROM requirement_assessment_model_invocations WHERE id = %s FOR UPDATE
            """,
            (model_invocation_id,),
        )
        invocation = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if invocation is None or (
            invocation.get("status") != "succeeded"
            or invocation.get("executor_profile_id") != executor_profile_id
            or invocation.get("product_id") != execution.get("product_id")
            or int(invocation.get("requirement_revision") or 0)
            != int(execution.get("input_revision") or 0)
            or invocation.get("strategy_snapshot_id") != execution.get("strategy_snapshot_id")
            or invocation.get("ai_executor_task_id") != task["id"]
            or invocation.get("assessment_execution_id") != execution_id
        ):
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_MODEL_INVOCATION_INVALID",
                "Model invocation is not a successful frozen assessment invocation",
            )
        output = invocation.get("output_json")
        if not isinstance(output, dict):
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_MODEL_INVOCATION_INVALID",
                "Model invocation output is not a structured assessment result",
            )
        if invocation.get("output_digest") != _canonical_hash(output):
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_MODEL_INVOCATION_INVALID",
                "Model invocation output digest does not match its frozen result",
            )
        opinion = self._assessment_opinion_from_gateway_output(output, executor_profile_id)
        self.cursor.execute(
            """
            UPDATE requirement_assessment_opinions
            SET conclusion_json = %s::jsonb, evidence_refs = %s::jsonb, confidence = %s,
                risk_summary = %s::jsonb, cost_summary = %s::jsonb, actor_id = %s,
                policy_proposal_json = %s::jsonb, outcome_code = %s, risk_level = %s,
                updated_at = now()
            WHERE id = %s AND conclusion_json = '{}'::jsonb
            RETURNING *
            """,
            (
                Jsonb(opinion.get("conclusion_json", {})),
                Jsonb(opinion.get("evidence_refs", [])),
                opinion.get("confidence"),
                Jsonb(opinion.get("risk_summary", {})),
                Jsonb(opinion.get("cost_summary", {})),
                opinion["actor_id"],
                Jsonb(opinion.get("policy_proposal_json", {})),
                opinion.get("outcome_code"),
                opinion.get("risk_level"),
                execution["opinion_id"],
            ),
        )
        if self.cursor.fetchone() is None:
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_OPINION_RECORDED", "Opinion is already recorded"
            )
        self.cursor.execute(
            """
            UPDATE requirement_assessment_executions
            SET status = 'completed', model_invocation_id = %s, result_summary = %s::jsonb,
                updated_at = now()
            WHERE id = %s
            """,
            (model_invocation_id, Jsonb(opinion.get("conclusion_json", {})), execution_id),
        )
        self.cursor.execute(
            """
            UPDATE requirement_assessments assessment SET status = 'waiting_human',
              version = version + 1, updated_at = now()
            WHERE assessment.id = %s AND assessment.status = 'evaluating'
              AND NOT EXISTS (
                SELECT 1 FROM requirement_assessment_opinions pending
                WHERE pending.assessment_id = assessment.id
                  AND pending.opinion_round = assessment.opinion_round
                  AND pending.conclusion_json = '{}'::jsonb
              )
            """,
            (assessment_id,),
        )
        self._repository.upsert_ai_executor_tasks(self.cursor, {task["id"]: task})
        self.save_audit_event(audit_event)
        self.save_outbox_event(outbox_event)
        return execution

    def save_assessment_model_invocation(
        self,
        *,
        task: dict[str, Any],
        execution_id: str,
        model_log: dict[str, Any],
        output: dict[str, Any],
    ) -> dict[str, Any]:
        return self.record_assessment_model_invocation(
            task=task,
            execution_id=execution_id,
            model_log=model_log,
            output=output,
        )

    @staticmethod
    def _assessment_opinion_from_gateway_output(
        output: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        """Map a frozen gateway response to the persisted assessment opinion shape."""
        conclusion = output.get("conclusion_json")
        if not isinstance(conclusion, dict):
            summary = str(output.get("summary") or "").strip()
            if not summary:
                raise RdCollaborationRepositoryError(
                    "ASSESSMENT_MODEL_INVOCATION_INVALID",
                    "Model invocation output is missing an assessment summary",
                )
            conclusion = {"summary": summary}
        return {
            "actor_id": actor_id,
            "conclusion_json": conclusion,
            "evidence_refs": output.get("evidence_refs")
            if isinstance(output.get("evidence_refs"), list)
            else [],
            "confidence": output.get("confidence"),
            "risk_summary": output.get("risk_summary")
            if isinstance(output.get("risk_summary"), dict)
            else {},
            "cost_summary": output.get("cost_summary")
            if isinstance(output.get("cost_summary"), dict)
            else {},
            "policy_proposal_json": output.get("policy_proposal_json")
            if isinstance(output.get("policy_proposal_json"), dict)
            else {},
            "outcome_code": output.get("outcome_code"),
            "risk_level": output.get("risk_level"),
        }

    def record_assessment_model_invocation(
        self,
        *,
        task: dict[str, Any],
        execution_id: str,
        model_log: dict[str, Any],
        output: dict[str, Any],
    ) -> dict[str, Any]:
        """Append one immutable gateway result bound to exactly one task/execution."""
        payload = task.get("input_payload") if isinstance(task.get("input_payload"), dict) else {}
        if payload.get("assessment_execution_id") != execution_id:
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_EXECUTION_INVALID", "Runner task is not bound to this execution"
            )
        required = {
            "executor_profile_id": payload.get("executor_profile_id"),
            "product_id": payload.get("product_id"),
            "requirement_revision": payload.get("requirement_revision"),
            "strategy_snapshot_id": payload.get("strategy_snapshot_id"),
        }
        if any(value is None or value == "" for value in required.values()):
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_EXECUTION_INVALID",
                "Runner task is missing frozen invocation provenance",
            )
        upsert_model_logs = getattr(self._repository, "upsert_model_gateway_logs", None)
        if not callable(upsert_model_logs):
            upsert_model_logs = getattr(self._repository, "_upsert_model_gateway_logs", None)
        if not callable(upsert_model_logs):
            raise RdCollaborationRepositoryError(
                "REPOSITORY_REQUIRED", "Model gateway log persistence is unavailable"
            )
        upsert_model_logs(self.cursor, [model_log])
        invocation = {
            "id": model_log["id"],
            "ai_executor_task_id": task["id"],
            "assessment_execution_id": execution_id,
            "model_gateway_log_id": model_log["id"],
            "status": model_log.get("status"),
            **required,
            "output_json": output,
            "output_digest": _canonical_hash(output),
        }
        self.cursor.execute(
            """
            INSERT INTO requirement_assessment_model_invocations (
              id, ai_executor_task_id, assessment_execution_id, model_gateway_log_id, status,
              executor_profile_id, product_id, requirement_revision, strategy_snapshot_id,
              output_json, output_digest
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            """,
            (
                invocation["id"],
                invocation["ai_executor_task_id"],
                invocation["assessment_execution_id"],
                invocation["model_gateway_log_id"],
                invocation["status"],
                invocation["executor_profile_id"],
                invocation["product_id"],
                invocation["requirement_revision"],
                invocation["strategy_snapshot_id"],
                Jsonb(invocation["output_json"]),
                invocation["output_digest"],
            ),
        )
        return invocation

    def advance_assessment_policy_round(
        self,
        *,
        assessment: dict[str, Any],
        expected_version: int,
        opinions: list[dict[str, Any]],
        executions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.cursor.execute(
            """
            UPDATE requirement_assessments
            SET final_strategy_snapshot_id = %s, strategy_snapshot_id = %s,
                opinion_round = %s, status = 'evaluating',
                proposed_policy_json = %s::jsonb, proposed_risk_level = %s,
                assessment_outcome = %s, assessment_evidence = %s::jsonb,
                version = version + 1, updated_at = now()
            WHERE id = %s AND version = %s
            RETURNING *
            """,
            (
                assessment["final_strategy_snapshot_id"],
                assessment["strategy_snapshot_id"],
                assessment["opinion_round"],
                Jsonb(assessment.get("proposed_policy_json", {})),
                assessment.get("proposed_risk_level"),
                assessment.get("assessment_outcome"),
                Jsonb(assessment.get("assessment_evidence", [])),
                assessment["id"],
                expected_version,
            ),
        )
        persisted = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if persisted is None:
            raise RdCollaborationVersionConflictError(expected_version)
        for opinion in opinions:
            self._repository._insert_assessment_opinion(self.cursor, opinion)
        for execution in executions:
            self._repository._save_simple_cursor(
                self.cursor, "requirement_assessment_executions", execution
            )
            self.cursor.execute(
                "UPDATE requirement_assessment_opinions SET execution_id = %s WHERE id = %s",
                (execution["id"], execution["opinion_id"]),
            )
        return persisted

    def record_assessment_opinion(self, opinion: dict[str, Any]) -> dict[str, Any]:
        """Conditionally persist one frozen human opinion and advance ready state in this tx."""
        self.cursor.execute(
            """
            UPDATE requirement_assessment_opinions opinion SET
              conclusion_json = %s::jsonb, evidence_refs = %s::jsonb, confidence = %s,
              risk_summary = %s::jsonb, cost_summary = %s::jsonb, actor_id = %s,
              policy_proposal_json = %s::jsonb, outcome_code = %s, risk_level = %s,
              updated_at = now()
            FROM requirement_assessments assessment
            WHERE opinion.id = %s AND assessment.id = opinion.assessment_id
              AND assessment.opinion_round = opinion.opinion_round
              AND assessment.strategy_snapshot_id = opinion.strategy_snapshot_id
              AND opinion.assigned_subject_type = 'human_user'
              AND opinion.assigned_user_id = %s AND opinion.conclusion_json = '{}'::jsonb
            RETURNING opinion.*
            """,
            (
                Jsonb(opinion.get("conclusion_json", {})),
                Jsonb(opinion.get("evidence_refs", [])),
                opinion.get("confidence"),
                Jsonb(opinion.get("risk_summary", {})),
                Jsonb(opinion.get("cost_summary", {})),
                opinion["actor_id"],
                Jsonb(opinion.get("policy_proposal_json", {})),
                opinion.get("outcome_code"),
                opinion.get("risk_level"),
                opinion["id"],
                opinion["actor_id"],
            ),
        )
        saved = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if saved is None:
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_OPINION_CONFLICT", "Opinion is stale or no longer eligible"
            )
        self.cursor.execute(
            """
            UPDATE requirement_assessments assessment SET status = 'waiting_human',
              version = version + 1, updated_at = now()
            WHERE assessment.id = %s AND assessment.status = 'evaluating'
              AND NOT EXISTS (
                SELECT 1 FROM requirement_assessment_opinions pending
                WHERE pending.assessment_id = assessment.id
                  AND pending.opinion_round = assessment.opinion_round
                  AND pending.conclusion_json = '{}'::jsonb
              )
            """,
            (saved["assessment_id"],),
        )
        return saved

    def submit_assessment_answers(
        self, *, assessment_id: str, expected_version: int, answers: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        """Cursor-scoped answer command; reject missing execution provenance before writes."""
        self.cursor.execute(
            "SELECT * FROM requirement_assessments WHERE id = %s FOR UPDATE", (assessment_id,)
        )
        assessment = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if assessment is None:
            raise RdCollaborationRepositoryError("NOT_FOUND", "Assessment not found")
        if int(assessment["version"]) != expected_version:
            raise RdCollaborationVersionConflictError(int(assessment["version"]))
        next_round = int(assessment.get("opinion_round") or 1) + 1
        self.cursor.execute(
            "SELECT * FROM requirement_assessment_opinions "
            "WHERE assessment_id = %s AND opinion_round = %s",
            (assessment_id, next_round - 1),
        )
        prior = [
            self._repository._row(cursor=self.cursor, row=row) for row in self.cursor.fetchall()
        ]
        if not prior or any(
            item is None or not item.get("assigned_subject_type") or not item.get("execution_id")
            for item in prior
        ):
            raise RdCollaborationRepositoryError(
                "ASSESSMENT_EXECUTION_REQUIRED",
                "Answer re-round requires typed execution provenance",
            )
        # Delegate the already cursor-safe implementation after its precondition has been proved.
        return self._repository._submit_assessment_answers_cursor(
            self.cursor,
            assessment_id=assessment_id,
            expected_version=expected_version,
            answers=answers,
            actor_id=actor_id,
        )

    def decide_assessment(
        self, assessment: dict[str, Any], *, expected_version: int
    ) -> dict[str, Any]:
        self.cursor.execute(
            """
            UPDATE requirement_assessments SET status = %s, decided_by = %s,
              decision_action = %s, decision_comment = %s, decided_at = %s::timestamptz,
              version = version + 1, updated_at = now()
            WHERE id = %s AND version = %s RETURNING *
            """,
            (
                assessment["status"],
                assessment.get("decided_by"),
                assessment.get("decision_action"),
                assessment.get("decision_comment"),
                assessment.get("decided_at"),
                assessment["id"],
                expected_version,
            ),
        )
        saved = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if saved is None:
            raise RdCollaborationVersionConflictError(expected_version)
        return saved

    def record_assessment_policy_conflict(
        self,
        *,
        assessment: dict[str, Any],
        expected_version: int,
        outcome_code: str,
        evidence: list[dict[str, Any]],
        decision_request: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist one actionable policy conflict with its decision command response."""
        self.cursor.execute(
            """
            SELECT * FROM decision_requests
            WHERE subject_type = 'requirement_assessment' AND subject_id = %s
              AND decision_type = 'policy_resolution' AND plan_version = %s
              AND status IN ('pending', 'waiting_more_info')
            FOR UPDATE
            """,
            (assessment["id"], int(assessment.get("opinion_round") or 1)),
        )
        existing_decision = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if existing_decision is not None:
            return {"assessment": assessment, "decision_request": existing_decision}
        self.cursor.execute(
            """
            UPDATE requirement_assessments SET status = 'waiting_human',
              assessment_outcome = %s, assessment_evidence = %s::jsonb,
              version = version + 1, updated_at = now()
            WHERE id = %s AND version = %s RETURNING *
            """,
            (outcome_code, Jsonb(evidence), assessment["id"], expected_version),
        )
        persisted = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if persisted is None:
            raise RdCollaborationVersionConflictError(expected_version)
        saved_decision = self._repository._insert_decision_request(self.cursor, decision_request)
        return {"assessment": persisted, "decision_request": saved_decision}

    def accept_requirement_assessment(
        self, assessment: dict[str, Any], *, expected_version: int, requirement_id: str
    ) -> dict[str, Any]:
        """Accept an assessment and select an iteration in the same command transaction."""
        self.cursor.execute(
            """
            UPDATE requirement_assessments SET status = 'accepted',
              final_strategy_snapshot_id = %s, strategy_snapshot_id = %s,
              decided_by = %s, decided_at = %s::timestamptz, version = version + 1,
              updated_at = now()
            WHERE id = %s AND version = %s RETURNING *
            """,
            (
                assessment["final_strategy_snapshot_id"],
                assessment["strategy_snapshot_id"],
                assessment["decided_by"],
                assessment["decided_at"],
                assessment["id"],
                expected_version,
            ),
        )
        saved = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if saved is None:
            raise RdCollaborationVersionConflictError(expected_version)
        self.cursor.execute(
            "UPDATE requirements SET status = 'approved', updated_at = now() "
            "WHERE id = %s AND status = 'submitted' AND assessment_revision = %s RETURNING id",
            (requirement_id, assessment["requirement_revision"]),
        )
        if self.cursor.fetchone() is None:
            raise RdCollaborationRepositoryError(
                "REQUIREMENT_STATE_INVALID", "Requirement must still be submitted"
            )
        return self._plan_accepted_requirement(saved, requirement_id=requirement_id)

    def _plan_accepted_requirement(
        self,
        assessment: dict[str, Any],
        *,
        requirement_id: str,
    ) -> dict[str, Any]:
        """Lock candidates, score them deterministically, and never guess a tie."""
        self.cursor.execute(
            "SELECT * FROM requirements WHERE id = %s FOR UPDATE", (requirement_id,)
        )
        requirement = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if requirement is None or requirement.get("status") != "approved":
            raise RdCollaborationRepositoryError(
                "REQUIREMENT_STATE_INVALID",
                "Requirement must be approved before iteration grouping",
            )
        self.cursor.execute(
            "SELECT * FROM rd_task_executor_policy_snapshots WHERE id = %s",
            (assessment["final_strategy_snapshot_id"],),
        )
        source_snapshot = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if source_snapshot is None:
            raise RdCollaborationRepositoryError(
                "RD_POLICY_SNAPSHOT_INVALID",
                "Accepted assessment final strategy snapshot is unavailable",
            )
        self.cursor.execute(
            """
            SELECT * FROM product_versions
            WHERE product_id = %s AND status = 'planning'
            ORDER BY id FOR UPDATE
            """,
            (requirement["product_id"],),
        )
        candidates = [
            record
            for row in self.cursor.fetchall()
            if (record := self._repository._row(cursor=self.cursor, row=row)) is not None
        ]
        scores = [
            self._iteration_candidate_score(
                candidate=candidate,
                source_snapshot=source_snapshot,
                source_assessment=assessment,
            )
            for candidate in candidates
        ]
        eligible = [item for item in scores if item["hard_eligible"]]
        idempotency_key = f"requirement:{requirement_id}:assessment:{assessment['id']}"
        if eligible:
            top_score = max(int(item["score"] or 0) for item in eligible)
            top = [item for item in eligible if item["score"] == top_score]
            if len(top) == 1:
                selected_id = str(top[0]["version_id"])
                selected = next(item for item in candidates if item["id"] == selected_id)
                assigned = self.assign_requirement_to_version_and_increment_scope(
                    requirement_id=requirement_id,
                    product_version_id=selected_id,
                    expected_scope_version=int(selected["scope_version"]),
                )
                return self._record_iteration_assignment(
                    assessment=assessment,
                    assignment_reason="unique_compatible_planning_version",
                    candidate_scores=scores,
                    created_version=False,
                    idempotency_key=idempotency_key,
                    requirement_id=requirement_id,
                    score_breakdown=top[0],
                    version=assigned,
                )
            return self._save_iteration_grouping_decision(
                assessment=assessment,
                candidate_scores=scores,
                candidate_ids=[str(item["version_id"]) for item in top],
                idempotency_key=idempotency_key,
                reason="candidate_score_tie",
                requirement=requirement,
            )

        risk_summary = assessment.get("risk_summary") or {}
        risk_level = risk_summary.get("risk_level") if isinstance(risk_summary, dict) else None
        if str(risk_level or "none") in {"high", "critical"}:
            return self._save_iteration_grouping_decision(
                assessment=assessment,
                candidate_scores=scores,
                candidate_ids=[],
                idempotency_key=idempotency_key,
                reason="high_risk_new_version",
                requirement=requirement,
            )

        new_version_id = f"product_version_{uuid4().hex}"
        new_code = f"RD-{requirement_id}-PLAN"
        self.cursor.execute(
            """
            INSERT INTO product_versions (
              id, product_id, code, name, status, scope_version, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, 'planning', 1, now(), now())
            """,
            (new_version_id, requirement["product_id"], new_code, f"{new_code} 自动规划版本"),
        )
        assigned = self.assign_requirement_to_version_and_increment_scope(
            requirement_id=requirement_id,
            product_version_id=new_version_id,
            expected_scope_version=1,
        )
        return self._record_iteration_assignment(
            assessment=assessment,
            assignment_reason="created_low_risk_planning_version",
            candidate_scores=scores,
            created_version=True,
            idempotency_key=idempotency_key,
            requirement_id=requirement_id,
            score_breakdown={
                "hard_eligible": True,
                "reasons": ["no_compatible_planning_version"],
                "score": None,
                "version_id": new_version_id,
            },
            version=assigned,
        )

    def _iteration_candidate_score(
        self,
        *,
        candidate: dict[str, Any],
        source_snapshot: dict[str, Any],
        source_assessment: dict[str, Any],
    ) -> dict[str, Any]:
        self.cursor.execute(
            """
            SELECT 1 FROM rd_collaboration_runs
            WHERE product_version_id = %s
              AND status NOT IN ('completed', 'failed', 'cancelled')
            LIMIT 1 FOR UPDATE
            """,
            (candidate["id"],),
        )
        active_run = self.cursor.fetchone() is not None
        self.cursor.execute(
            """
            SELECT requirement.id, assessment.final_strategy_snapshot_id,
                   snapshot.policy_id, snapshot.policy_version, snapshot.payload_json
            FROM requirements requirement
            LEFT JOIN LATERAL (
              SELECT * FROM requirement_assessments
              WHERE requirement_id = requirement.id
                AND requirement_revision = requirement.assessment_revision
                AND status = 'accepted'
              ORDER BY updated_at DESC, id DESC LIMIT 1
            ) assessment ON TRUE
            LEFT JOIN rd_task_executor_policy_snapshots snapshot
              ON snapshot.id = assessment.final_strategy_snapshot_id
            WHERE requirement.version_id = %s
            ORDER BY requirement.id FOR UPDATE OF requirement
            """,
            (candidate["id"],),
        )
        members = [
            record
            for row in self.cursor.fetchall()
            if (record := self._repository._row(cursor=self.cursor, row=row)) is not None
        ]
        reasons: list[str] = ["active_run"] if active_run else []
        payload = source_snapshot.get("payload_json")
        if not isinstance(payload, dict):
            payload = {}
        iteration_config = payload.get("iteration_config") if isinstance(payload, dict) else {}
        capacity = iteration_config.get("capacity") if isinstance(iteration_config, dict) else {}
        capacity_limit = (
            capacity.get("max_requirements")
            if isinstance(capacity, dict)
            else iteration_config.get("max_requirements")
            if isinstance(iteration_config, dict)
            else None
        )
        if (
            isinstance(capacity_limit, int)
            and capacity_limit > 0
            and len(members) >= capacity_limit
        ):
            reasons.append("capacity_exhausted")
        git_config = payload.get("git_config") if isinstance(payload, dict) else None
        requested_repository_ids = (
            {
                str(value)
                for value in git_config.get("repository_ids", [])
                if value is not None and str(value)
            }
            if isinstance(git_config, dict)
            else set()
        )
        if isinstance(git_config, dict) and git_config.get("repository_id"):
            requested_repository_ids.add(str(git_config["repository_id"]))
        if requested_repository_ids:
            self.cursor.execute(
                """
                SELECT repository_id FROM product_version_branch_configs
                WHERE version_id = %s AND repository_id IS NOT NULL
                FOR KEY SHARE
                """,
                (candidate["id"],),
            )
            configured_repository_ids = {str(row[0]) for row in self.cursor.fetchall()}
            if not requested_repository_ids & configured_repository_ids:
                reasons.append("repository_incompatible")
        member_ids = {str(member["id"]) for member in members}
        dependencies = source_assessment.get("dependency_summary")
        if isinstance(dependencies, list) and any(
            isinstance(dependency, dict)
            and (dependency.get("hard") is True or dependency.get("type") == "hard")
            and str(dependency.get("requirement_id") or dependency.get("dependency_requirement_id"))
            not in member_ids
            for dependency in dependencies
            if dependency.get("requirement_id") or dependency.get("dependency_requirement_id")
        ):
            reasons.append("hard_dependency_unsatisfied")
        if payload.get("delivery_target", "ready_for_release") not in {
            "ready_for_release",
            "deployed",
        }:
            reasons.append("delivery_target_incompatible")
        merge_payloads: list[dict[str, Any]] = []
        for member in members:
            if not member.get("final_strategy_snapshot_id"):
                reasons.append("member_assessment_unaccepted")
                break
            if (
                member.get("policy_id") != source_snapshot["policy_id"]
                or member.get("policy_version") != source_snapshot["policy_version"]
            ):
                reasons.append("policy_identity_mismatch")
                break
            if member["final_strategy_snapshot_id"] != source_snapshot["id"]:
                source_payload = source_snapshot.get("payload_json")
                member_payload = member.get("payload_json")
                if not isinstance(source_payload, dict) or not isinstance(member_payload, dict):
                    reasons.append("policy_merge_required")
                    break
                if not merge_payloads:
                    merge_payloads.append(source_payload)
                merge_payloads.append(member_payload)
        if not reasons and merge_payloads:
            try:
                merge_policy_payloads(merge_payloads)
            except PolicyResolutionError:
                reasons.append("policy_merge_required")
        hard_eligible = not reasons
        return {
            "capacity_limit": capacity_limit if isinstance(capacity_limit, int) else None,
            "current_requirement_count": len(members),
            "hard_eligible": hard_eligible,
            "reasons": reasons,
            "score": 1_000 - len(members) if hard_eligible else None,
            "version_id": candidate["id"],
        }

    def _record_iteration_assignment(
        self,
        *,
        assessment: dict[str, Any],
        assignment_reason: str,
        candidate_scores: list[dict[str, Any]],
        created_version: bool,
        idempotency_key: str,
        requirement_id: str,
        score_breakdown: dict[str, Any],
        version: dict[str, Any],
    ) -> dict[str, Any]:
        self.cursor.execute(
            """
            UPDATE requirement_assessments
            SET candidate_version_id = %s, assignment_reason = %s, updated_at = now()
            WHERE id = %s RETURNING *
            """,
            (version["id"], assignment_reason, assessment["id"]),
        )
        persisted = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        return {
            **(persisted or assessment),
            "grouping": {
                "candidate_scores": candidate_scores,
                "created_version": created_version,
                "idempotency_key": idempotency_key,
                "score_breakdown": score_breakdown,
                "status": "planned",
                "version": version,
                "version_id": version["id"],
            },
        }

    def _save_iteration_grouping_decision(
        self,
        *,
        assessment: dict[str, Any],
        candidate_scores: list[dict[str, Any]],
        candidate_ids: list[str],
        idempotency_key: str,
        reason: str,
        requirement: dict[str, Any],
    ) -> dict[str, Any]:
        options = [
            {"code": f"select:{version_id}", "label": f"Select {version_id}"}
            for version_id in candidate_ids
        ] + [{"code": "create_new", "label": "Create new planning version"}]
        decision = {
            "id": f"iteration_grouping_decision_{uuid4().hex}",
            "brain_app_id": requirement.get("brain_app_id") or "rd_brain",
            "product_id": requirement["product_id"],
            "subject_type": "requirement_iteration_grouping",
            "subject_id": requirement["id"],
            "decision_type": "iteration_grouping",
            "plan_version": 0,
            "options_json": options,
            "options_hash": _canonical_hash(options),
            "evidence_json": [{"candidate_scores": candidate_scores, "reason": reason}],
            "recommendation_json": {"action": "select_planning_version"},
            "decision_actor_selector": {"role_codes": ["rd_owner", "product_owner"]},
            "answer_actor_selector": {"role_codes": ["rd_owner", "product_owner"]},
            "answer_schema": {"type": "object", "additionalProperties": False},
            "status": "pending",
            "expires_at": datetime.now(UTC) + timedelta(hours=24),
            "timeout_policy": "escalate_keep_paused",
            "escalation_target_selector": {"role_codes": ["rd_owner"]},
            "version": 1,
            "created_by": assessment.get("decided_by") or requirement.get("created_by"),
        }
        saved_decision = self._repository._insert_decision_request(self.cursor, decision)
        self.cursor.execute(
            """
            UPDATE requirement_assessments
            SET assignment_reason = %s, updated_at = now()
            WHERE id = %s RETURNING *
            """,
            (reason, assessment["id"]),
        )
        persisted = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        return {
            **(persisted or assessment),
            "grouping": {
                "candidate_scores": candidate_scores,
                "created_version": False,
                "decision_request": saved_decision,
                "idempotency_key": idempotency_key,
                "status": "waiting_human",
            },
        }

    def create_collaboration_run_with_exact_scope(
        self,
        *,
        run: dict[str, Any],
        scope_rows: list[dict[str, Any]],
        snapshot: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self._repository._create_collaboration_run_with_exact_scope_cursor(
            self.cursor,
            run=run,
            scope_rows=scope_rows,
            snapshot=snapshot,
            sources=sources,
        )

    def activate_product_version_for_collaboration(
        self,
        *,
        product_version_id: str,
    ) -> dict[str, Any]:
        return self._repository._activate_product_version_for_collaboration_cursor(
            self.cursor,
            product_version_id=product_version_id,
        )

    def restart_terminal_collaboration_run(
        self,
        *,
        terminal_run_id: str,
        run: dict[str, Any],
        scope_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._repository._restart_terminal_collaboration_run_cursor(
            self.cursor,
            terminal_run_id=terminal_run_id,
            run=run,
            scope_rows=scope_rows,
        )

    def assign_requirement_to_version_and_increment_scope(
        self,
        *,
        requirement_id: str,
        product_version_id: str,
        expected_scope_version: int,
    ) -> dict[str, Any]:
        return self._repository._assign_requirement_to_version_and_increment_scope_cursor(
            self.cursor,
            requirement_id=requirement_id,
            product_version_id=product_version_id,
            expected_scope_version=expected_scope_version,
        )

    def create_scope_change_request(
        self,
        *,
        request: dict[str, Any],
        operations: list[dict[str, Any]],
        decision_request: dict[str, Any],
    ) -> dict[str, Any]:
        return self._repository._create_scope_change_request_cursor(
            self.cursor,
            request=request,
            operations=operations,
            decision_request=decision_request,
        )

    def apply_scope_change_bundle(
        self,
        *,
        scope_change_request_id: str,
        decision: str,
        decided_by: str,
        expected_decision_version: int,
        actor_role_codes: list[str] | None = None,
        cancellation_outbox_events: list[dict[str, Any]] | None = None,
        failure_injection: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        return self._repository._apply_scope_change_bundle_cursor(
            self.cursor,
            scope_change_request_id=scope_change_request_id,
            decision=decision,
            decided_by=decided_by,
            expected_decision_version=expected_decision_version,
            actor_role_codes=actor_role_codes or [],
            cancellation_outbox_events=cancellation_outbox_events,
            failure_injection=failure_injection,
        )

    def save_work_item_attempt_bundle(
        self,
        *,
        work_item_id: str,
        expected_statuses: list[str],
        next_status: str,
        attempt: dict[str, Any],
        expected_version: int | None = None,
        event: dict[str, Any] | None = None,
        task: dict[str, Any] | None = None,
        audit_events: list[dict[str, Any]] | None = None,
        failure_injection: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        return self._repository._save_work_item_attempt_bundle_cursor(
            self.cursor,
            work_item_id=work_item_id,
            expected_statuses=expected_statuses,
            next_status=next_status,
            attempt=attempt,
            expected_version=expected_version,
            event=event,
            task=task,
            audit_events=audit_events or [],
            failure_injection=failure_injection,
        )

    def dispatch_work_item_execution_bundle(
        self,
        *,
        work_item_id: str,
        expected_version: int,
        task: dict[str, Any],
        requirement: dict[str, Any] | None,
        runner_task: dict[str, Any],
        attempt: dict[str, Any],
        event: dict[str, Any],
        audit_events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._repository._dispatch_work_item_execution_bundle_cursor(
            self.cursor,
            work_item_id=work_item_id,
            expected_version=expected_version,
            task=task,
            requirement=requirement,
            runner_task=runner_task,
            attempt=attempt,
            event=event,
            audit_events=audit_events,
        )

    def save_rd_run_seat_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._repository._save_simple_cursor(self.cursor, "rd_run_seats", record)

    def fence_work_item_runner_result(self, **kwargs: Any) -> dict[str, Any]:
        return self._repository._fence_work_item_runner_result_cursor(self.cursor, **kwargs)

    def save_rd_role_session_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._repository._save_simple_cursor(self.cursor, "rd_role_sessions", record)

    def save_rd_work_item_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._repository._save_rd_work_item_record_cursor(self.cursor, record)

    def save_rd_work_item_dependency_record(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        return self._repository._save_simple_cursor(
            self.cursor,
            "rd_work_item_dependencies",
            record,
        )

    def save_rd_work_item_plan_bundle(
        self,
        *,
        collaboration_run_id: str,
        expected_run_version: int,
        work_items: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._repository._save_rd_work_item_plan_bundle_cursor(
            self.cursor,
            collaboration_run_id=collaboration_run_id,
            expected_run_version=expected_run_version,
            work_items=work_items,
            dependencies=dependencies,
        )

    def save_rd_collaboration_event_record(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        return self._repository._insert_event_cursor(self.cursor, record)

    def save_decision_request_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._repository._insert_decision_request(self.cursor, record)

    def cancel_work_item_bundle(
        self,
        *,
        work_item_id: str,
        expected_version: int,
        high_risk: bool,
        decision_request: dict[str, Any] | None = None,
        event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._repository._cancel_work_item_bundle_cursor(
            self.cursor,
            work_item_id=work_item_id,
            expected_version=expected_version,
            high_risk=high_risk,
            decision_request=decision_request,
            event=event,
        )

    def suspend_collaboration_run(
        self,
        *,
        collaboration_run_id: str,
        decision_request_id: str,
        expected_version: int,
    ) -> dict[str, Any]:
        return self._repository._suspend_collaboration_run_cursor(
            self.cursor,
            collaboration_run_id=collaboration_run_id,
            decision_request_id=decision_request_id,
            expected_version=expected_version,
        )

    def apply_decision_bundle(
        self,
        *,
        decision_request_id: str,
        selected_option_code: str,
        input_json: Any,
        comment: str | None,
        decided_by: str,
        expected_version: int,
        actor_role_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._repository._apply_decision_bundle_cursor(
            self.cursor,
            decision_request_id=decision_request_id,
            selected_option_code=selected_option_code,
            input_json=input_json,
            comment=comment,
            decided_by=decided_by,
            actor_role_codes=actor_role_codes or [],
            expected_version=expected_version,
        )

    def answer_decision_request(
        self,
        *,
        decision_request_id: str,
        expected_version: int,
        actor_id: str,
        actor_role_codes: list[str],
        actor_seat_ids: list[str],
        answer_json: Any,
        evidence_json: list[Any],
        options_json: list[dict[str, Any]],
        options_hash: str,
    ) -> dict[str, Any]:
        return self._repository._answer_decision_request_cursor(
            self.cursor,
            decision_request_id=decision_request_id,
            expected_version=expected_version,
            actor_id=actor_id,
            actor_role_codes=actor_role_codes,
            actor_seat_ids=actor_seat_ids,
            answer_json=answer_json,
            evidence_json=evidence_json,
            options_json=options_json,
            options_hash=options_hash,
        )

    def expire_and_escalate_decision_request(
        self,
        *,
        decision_request_id: str,
        successor_request: dict[str, Any],
        expiry_event: dict[str, Any],
    ) -> dict[str, Any] | None:
        return self._repository._expire_and_escalate_decision_request_cursor(
            self.cursor,
            decision_request_id=decision_request_id,
            successor_request=successor_request,
            expiry_event=expiry_event,
        )

    def save_role_feedback_once(self, record: dict[str, Any]) -> dict[str, Any]:
        return self._repository._save_role_feedback_once_cursor(self.cursor, record)

    def save_rd_role_experience_record(
        self,
        record: dict[str, Any],
        *,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._repository._save_rd_role_experience_record_cursor(
            self.cursor,
            record,
            sources=sources,
        )

    def decide_role_experience(
        self,
        *,
        experience_id: str,
        decision: str,
        expected_review_version: int,
        reviewer_subject_type: str,
        reviewer_subject_id: str,
        reviewer_role_code: str | None,
        reviewer_seat_id: str | None,
        require_independent_reviewer: bool,
    ) -> dict[str, Any]:
        return self._repository._decide_role_experience_cursor(
            self.cursor,
            experience_id=experience_id,
            decision=decision,
            expected_review_version=expected_review_version,
            reviewer_subject_type=reviewer_subject_type,
            reviewer_subject_id=reviewer_subject_id,
            reviewer_role_code=reviewer_role_code,
            reviewer_seat_id=reviewer_seat_id,
            require_independent_reviewer=require_independent_reviewer,
        )

    def save_collaboration_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return self._repository._insert_event_cursor(self.cursor, event)

    def save_outbox_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self.cursor.execute(
            """
            INSERT INTO execution_outbox_events (
              id, aggregate_type, aggregate_id, event_type,
              idempotency_key, payload_json, status, available_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s,
                    COALESCE(%s::timestamptz, now()))
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING *
            """,
            (
                event["id"],
                event["aggregate_type"],
                event["aggregate_id"],
                event["event_type"],
                event["idempotency_key"],
                Jsonb(event.get("payload_json", {})),
                event.get("status", "pending"),
                event.get("available_at"),
            ),
        )
        persisted = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if persisted is not None:
            return persisted
        self.cursor.execute(
            "SELECT * FROM execution_outbox_events WHERE idempotency_key = %s",
            (event["idempotency_key"],),
        )
        existing = self._repository._row(cursor=self.cursor, row=self.cursor.fetchone())
        if existing is None:
            raise RuntimeError("outbox replay lookup failed")
        for field in ("aggregate_type", "aggregate_id", "event_type", "payload_json"):
            expected = event.get(field, {} if field == "payload_json" else None)
            if existing[field] != expected:
                raise self._repository._idempotency_conflict(
                    "outbox idempotency key is bound to different provenance",
                    field=field,
                )
        return existing

    def save_audit_event(self, event: dict[str, Any]) -> None:
        callback: Callable[[Any, list[dict[str, Any]]], None] | None = (
            self._repository._upsert_audit_events
        )
        if callback is None:
            raise RuntimeError("audit persistence callback is not configured")
        callback(self.cursor, [event])


class RdCollaborationWriteBase:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._upsert_audit_events = upsert_audit_events

    @staticmethod
    def _row(*, cursor: Any, row: Sequence[Any] | None) -> dict[str, Any] | None:
        return _row_dict(cursor, row)

    def _in_transaction(self, operation: Callable[[Any], Any]) -> Any:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                return operation(cursor)

    def execute_requirement_assessment_command(
        self,
        command: dict[str, Any],
        effect: Callable[[RdCollaborationTransaction], dict[str, Any]],
    ) -> dict[str, Any]:
        """Reserve/check a command and commit its assessment effect and replay snapshot together."""

        def operation(cursor: Any) -> dict[str, Any]:
            cursor.execute(
                """
                INSERT INTO requirement_assessment_commands (
                  id, assessment_id, requirement_id, operation, idempotency_key, request_hash,
                  response_snapshot, status, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, '{}'::jsonb, 'pending', %s)
                ON CONFLICT DO NOTHING
                RETURNING *
                """,
                (
                    command["id"],
                    command["assessment_id"],
                    command.get("requirement_id"),
                    command["operation"],
                    command["idempotency_key"],
                    command["request_hash"],
                    command["created_by"],
                ),
            )
            persisted = _row_dict(cursor, cursor.fetchone())
            if persisted is None:
                cursor.execute(
                    """
                    SELECT * FROM requirement_assessment_commands
                    WHERE assessment_id = %s AND operation = %s AND idempotency_key = %s
                    FOR UPDATE
                    """,
                    (command["assessment_id"], command["operation"], command["idempotency_key"]),
                )
                persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None and command["operation"] == "start":
                    cursor.execute(
                        """
                        SELECT * FROM requirement_assessment_commands
                        WHERE requirement_id = %s AND operation = 'start'
                          AND idempotency_key = %s
                        FOR UPDATE
                        """,
                        (command.get("requirement_id"), command["idempotency_key"]),
                    )
                    persisted = _row_dict(cursor, cursor.fetchone())
                if persisted is None:
                    raise RuntimeError("assessment command replay lookup failed")
                if persisted["request_hash"] != command["request_hash"]:
                    raise self._idempotency_conflict(
                        "assessment command key is bound to a different request",
                        assessment_id=command["assessment_id"],
                        operation=command["operation"],
                    )
                if persisted.get("status") == "completed":
                    return {**persisted["response_snapshot"], "idempotent_replay": True}
            response = _json_response_payload(effect(RdCollaborationTransaction(self, cursor)))
            cursor.execute(
                """
                UPDATE requirement_assessment_commands
                SET response_snapshot = %s::jsonb, status = 'completed', updated_at = now()
                WHERE id = %s AND status = 'pending'
                RETURNING *
                """,
                (Jsonb(response), command["id"]),
            )
            if cursor.fetchone() is None:
                raise RuntimeError("assessment command completion lost its reservation")
            return response

        return self._in_transaction(operation)

    def complete_ai_assessment_runner_task(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: RdCollaborationTransaction(
                self, cursor
            ).complete_ai_assessment_runner_task(**kwargs)
        )

    def save_assessment_model_invocation(self, **kwargs: Any) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: RdCollaborationTransaction(
                self, cursor
            ).save_assessment_model_invocation(**kwargs)
        )

    @staticmethod
    def _idempotency_conflict(message: str, **details: Any) -> RdCollaborationRepositoryError:
        return RdCollaborationRepositoryError(
            "RD_IDEMPOTENCY_CONFLICT",
            message,
            details=details,
        )

    def _assert_immutable_replay(
        self,
        *,
        existing: dict[str, Any],
        incoming: dict[str, Any],
        fields: Iterable[str],
        message: str,
        **details: Any,
    ) -> None:
        """Reject an idempotent replay that changes immutable creation data."""
        for field in fields:
            if field in incoming and existing[field] != incoming[field]:
                raise self._idempotency_conflict(message, field=field, **details)

    def _insert_record(
        self,
        cursor: Any,
        table_name: str,
        record: dict[str, Any],
        *,
        update_on_conflict: bool,
    ) -> dict[str, Any]:
        allowed = TABLE_COLUMNS[table_name]
        columns = [column for column in allowed if column in record]
        if "id" not in columns:
            raise ValueError(f"{table_name} record requires id")
        assignments = [column for column in columns if column not in {"id", "created_at"}]
        conflict = sql.SQL("DO NOTHING")
        if update_on_conflict and assignments:
            conflict = sql.SQL("DO UPDATE SET {} ").format(
                sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(column),
                        sql.Identifier(column),
                    )
                    for column in assignments
                )
            )
        query = sql.SQL(
            "INSERT INTO {table} ({columns}) VALUES ({values}) "
            "ON CONFLICT (id) {conflict} RETURNING *"
        ).format(
            table=sql.Identifier(table_name),
            columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
            conflict=conflict,
        )
        cursor.execute(query, tuple(_adapt(record[column], column) for column in columns))
        persisted = _row_dict(cursor, cursor.fetchone())
        if persisted is not None:
            return persisted
        cursor.execute(
            sql.SQL("SELECT * FROM {} WHERE id = %s").format(sql.Identifier(table_name)),
            (record["id"],),
        )
        existing = _row_dict(cursor, cursor.fetchone())
        if existing is None:
            raise RuntimeError(f"failed to persist {table_name} record")
        return existing

    def _save_simple_cursor(
        self,
        cursor: Any,
        table_name: str,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        return self._insert_record(
            cursor,
            table_name,
            record,
            update_on_conflict=True,
        )

    def _save_simple(self, table_name: str, record: dict[str, Any]) -> dict[str, Any]:
        return self._in_transaction(
            lambda cursor: self._save_simple_cursor(cursor, table_name, record)
        )
