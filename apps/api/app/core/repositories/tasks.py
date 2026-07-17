from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.task_writes import TaskWriteRepository
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.core.task_titles import code_inspection_remediation_title


class TaskReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_requirements: Callable[[Any, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
        upsert_model_gateway_logs: Callable[[Any, list[dict[str, Any]]], None] | None = None,
        upsert_code_review_reports: Callable[[Any, dict[str, dict[str, Any]]], None] | None = None,
        upsert_bugs: Callable[[Any, dict[str, dict[str, Any]]], None] | None = None,
        upsert_knowledge_deposits: Callable[[Any, dict[str, dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._upsert_requirements = upsert_requirements
        self._upsert_audit_events = upsert_audit_events
        self._upsert_model_gateway_logs = upsert_model_gateway_logs
        self._upsert_code_review_reports = upsert_code_review_reports
        self._upsert_bugs = upsert_bugs
        self._upsert_knowledge_deposits = upsert_knowledge_deposits
        self._write_repository = TaskWriteRepository(connect, delete_missing=delete_missing)

    def load_ai_tasks(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                ai_tasks = self._load_ai_tasks(cursor)
        return {"ai_tasks": ai_tasks}

    def save_ai_tasks(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_ai_tasks(payload)

    def save_ai_task_record(
        self,
        task: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_tasks(cursor, {task["id"]: task})
                if audit_event is not None:
                    self._require_callback(self._upsert_audit_events, "audit upsert")
                    self._upsert_audit_events(cursor, [audit_event])

    def list_rd_task_executor_policies(
        self,
        *,
        product_id: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            clauses.append("product_id = %s")
            params.append(product_id)
        if status is not None:
            clauses.append("status = %s")
            params.append(status)
        if task_type is not None:
            clauses.append("task_type = %s")
            params.append(task_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, name, brain_app_id, product_id, task_type, executor_type,
                           runner_id, repository_id, workspace_root, branch,
                           code_change_review_mode, instruction_template, output_contract,
                           timeout_seconds, priority, status, created_by, created_at, updated_at,
                           autonomy_mode, max_iterations, max_duration_seconds,
                           token_budget, cost_budget, quality_gate_policy_id,
                           auto_merge_risk_threshold, policy_version
                    FROM rd_task_executor_policies
                    {where}
                    ORDER BY priority ASC, task_type ASC, product_id NULLS FIRST, id ASC
                    """,
                    tuple(params),
                )
                return [self._rd_task_executor_policy_from_row(row) for row in cursor.fetchall()]

    def count_rd_task_executor_policies(
        self,
        *,
        executor_type: str | None = None,
        name: str | None = None,
        product_id: str | None = None,
        product_name: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> int:
        where, params = self._rd_task_executor_policy_where(
            executor_type=executor_type,
            name=name,
            product_id=product_id,
            product_name=product_name,
            status=status,
            task_type=task_type,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM rd_task_executor_policies AS policy
                    LEFT JOIN products AS product ON product.id = policy.product_id
                    {where}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0]) if row is not None else 0

    def list_rd_task_executor_policy_page(
        self,
        *,
        executor_type: str | None = None,
        limit: int,
        name: str | None = None,
        offset: int,
        product_id: str | None = None,
        product_name: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._rd_task_executor_policy_where(
            executor_type=executor_type,
            name=name,
            product_id=product_id,
            product_name=product_name,
            status=status,
            task_type=task_type,
        )
        order_by = self._rd_task_executor_policy_order_by(
            sort_by=sort_by,
            sort_order=sort_order,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT policy.id, policy.name, policy.brain_app_id, policy.product_id,
                           policy.task_type, policy.executor_type, policy.runner_id,
                           policy.repository_id, policy.workspace_root, policy.branch,
                           policy.code_change_review_mode,
                           policy.instruction_template, policy.output_contract,
                           policy.timeout_seconds, policy.priority, policy.status,
                           policy.created_by, policy.created_at, policy.updated_at,
                           policy.autonomy_mode, policy.max_iterations,
                           policy.max_duration_seconds, policy.token_budget,
                           policy.cost_budget, policy.quality_gate_policy_id,
                           policy.auto_merge_risk_threshold, policy.policy_version,
                           product.name AS product_name,
                           repository.name AS repository_name,
                           repository.default_branch AS repository_default_branch,
                           runner.name AS runner_name
                    FROM rd_task_executor_policies AS policy
                    LEFT JOIN products AS product ON product.id = policy.product_id
                    LEFT JOIN product_git_repositories AS repository
                      ON repository.id = policy.repository_id
                    LEFT JOIN ai_executor_runners AS runner ON runner.id = policy.runner_id
                    {where}
                    {order_by}
                    LIMIT %s OFFSET %s
                    """,
                    tuple([*params, limit, offset]),
                )
                return [self._rd_task_executor_policy_from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def _rd_task_executor_policy_where(
        *,
        executor_type: str | None = None,
        name: str | None = None,
        product_id: str | None = None,
        product_name: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            clauses.append("policy.product_id = %s")
            params.append(product_id)
        if status is not None:
            clauses.append("policy.status = %s")
            params.append(status)
        if task_type is not None:
            clauses.append("policy.task_type = %s")
            params.append(task_type)
        if executor_type is not None:
            clauses.append("policy.executor_type = %s")
            params.append(executor_type)
        if name:
            clauses.append("LOWER(policy.name) LIKE %s")
            params.append(f"%{name.strip().lower()}%")
        if product_name:
            clauses.append("LOWER(COALESCE(product.name, '')) LIKE %s")
            params.append(f"%{product_name.strip().lower()}%")
        return (f"WHERE {' AND '.join(clauses)}" if clauses else "", params)

    @staticmethod
    def _rd_task_executor_policy_order_by(
        *,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        sort_columns = {
            "executor_type": "policy.executor_type",
            "code_change_review_mode": "policy.code_change_review_mode",
            "name": "LOWER(policy.name)",
            "priority": "policy.priority",
            "product_name": "LOWER(COALESCE(product.name, ''))",
            "repository_name": "LOWER(COALESCE(repository.name, ''))",
            "runner_name": "LOWER(COALESCE(runner.name, ''))",
            "status": "policy.status",
            "task_type": "policy.task_type",
            "updated_at": "policy.updated_at",
            "workspace_root": "LOWER(policy.workspace_root)",
        }
        if sort_by and sort_by in sort_columns:
            direction = "DESC" if sort_order == "desc" else "ASC"
            return f"ORDER BY {sort_columns[sort_by]} {direction}, policy.id ASC"
        return (
            "ORDER BY policy.priority ASC, policy.task_type ASC, "
            "policy.product_id NULLS FIRST, policy.id ASC"
        )

    def save_rd_task_executor_policy_record(
        self,
        policy: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_rd_task_executor_policies(cursor, {policy["id"]: policy})
                if audit_event is not None:
                    self._require_callback(self._upsert_audit_events, "audit upsert")
                    self._upsert_audit_events(cursor, [audit_event])

    def delete_rd_task_executor_policy_record(
        self,
        policy_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM rd_task_executor_policies WHERE id = %s", (policy_id,))
                if audit_event is not None:
                    self._require_callback(self._upsert_audit_events, "audit upsert")
                    self._upsert_audit_events(cursor, [audit_event])

    def upsert_rd_task_executor_policies(
        self,
        cursor,
        policies: dict[str, dict[str, Any]],
    ) -> None:
        for policy in policies.values():
            cursor.execute(
                """
                INSERT INTO rd_task_executor_policies (
                  id, name, brain_app_id, product_id, task_type, executor_type,
                  runner_id, repository_id, workspace_root, branch, instruction_template,
                  output_contract, timeout_seconds, priority, status,
                  code_change_review_mode, created_by, created_at, updated_at,
                  autonomy_mode, max_iterations, max_duration_seconds,
                  token_budget, cost_budget, quality_gate_policy_id,
                  auto_merge_risk_threshold
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s::jsonb, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  %s, %s, %s,
                  %s, %s, %s,
                  %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  name = EXCLUDED.name,
                  brain_app_id = EXCLUDED.brain_app_id,
                  product_id = EXCLUDED.product_id,
                  task_type = EXCLUDED.task_type,
                  executor_type = EXCLUDED.executor_type,
                  runner_id = EXCLUDED.runner_id,
                  repository_id = EXCLUDED.repository_id,
                  workspace_root = EXCLUDED.workspace_root,
                  branch = EXCLUDED.branch,
                  instruction_template = EXCLUDED.instruction_template,
                  output_contract = EXCLUDED.output_contract,
                  timeout_seconds = EXCLUDED.timeout_seconds,
                  priority = EXCLUDED.priority,
                  status = EXCLUDED.status,
                  code_change_review_mode = EXCLUDED.code_change_review_mode,
                  autonomy_mode = EXCLUDED.autonomy_mode,
                  max_iterations = EXCLUDED.max_iterations,
                  max_duration_seconds = EXCLUDED.max_duration_seconds,
                  token_budget = EXCLUDED.token_budget,
                  cost_budget = EXCLUDED.cost_budget,
                  quality_gate_policy_id = EXCLUDED.quality_gate_policy_id,
                  auto_merge_risk_threshold = EXCLUDED.auto_merge_risk_threshold,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    policy["id"],
                    policy["name"],
                    policy.get("brain_app_id") or DEFAULT_BRAIN_APP_ID,
                    policy.get("product_id"),
                    policy["task_type"],
                    policy["executor_type"],
                    policy.get("runner_id"),
                    policy.get("repository_id"),
                    policy.get("workspace_root") or "",
                    policy.get("branch"),
                    policy["instruction_template"],
                    json.dumps(policy.get("output_contract") or {}, ensure_ascii=False),
                    int(policy.get("timeout_seconds") or 1800),
                    int(policy.get("priority") or 100),
                    policy.get("status") or "active",
                    policy.get("code_change_review_mode") or "manual_review",
                    policy.get("created_by"),
                    policy.get("created_at"),
                    policy.get("updated_at"),
                    policy.get("autonomy_mode") or "single_pass",
                    int(policy.get("max_iterations") or 1),
                    int(policy.get("max_duration_seconds") or 3600),
                    policy.get("token_budget"),
                    policy.get("cost_budget"),
                    policy.get("quality_gate_policy_id"),
                    policy.get("auto_merge_risk_threshold") or "low",
                ),
            )

    def upsert_ai_tasks(self, cursor, ai_tasks: dict[str, dict[str, Any]]) -> None:
        self._write_repository.upsert_ai_tasks(cursor, ai_tasks)

    @staticmethod
    def _rd_task_executor_policy_from_row(row) -> dict[str, Any]:
        policy = {
            "brain_app_id": row[2] or DEFAULT_BRAIN_APP_ID,
            "branch": row[9],
            "code_change_review_mode": row[10] or "manual_review",
            "created_at": row[17].isoformat() if row[17] else None,
            "created_by": row[16],
            "executor_type": row[5],
            "id": row[0],
            "instruction_template": row[11],
            "name": row[1],
            "output_contract": dict(row[12] or {}),
            "priority": row[14],
            "product_id": row[3],
            "repository_id": row[7],
            "runner_id": row[6],
            "status": row[15],
            "task_type": row[4],
            "timeout_seconds": row[13],
            "updated_at": row[18].isoformat() if row[18] else None,
            "workspace_root": row[8] or "",
        }
        metadata_offset = 19
        if len(row) > 19 and row[19] in {"autonomous_loop", "single_pass"}:
            policy.update(
                {
                    "autonomy_mode": row[19],
                    "max_iterations": row[20],
                    "max_duration_seconds": row[21],
                    "token_budget": row[22],
                    "cost_budget": float(row[23]) if row[23] is not None else None,
                    "quality_gate_policy_id": row[24],
                    "auto_merge_risk_threshold": row[25],
                }
            )
            metadata_offset = 26
        else:
            policy.update(
                {
                    "autonomy_mode": "single_pass",
                    "max_iterations": 1,
                    "max_duration_seconds": 3600,
                    "token_budget": None,
                    "cost_budget": None,
                    "quality_gate_policy_id": None,
                    "auto_merge_risk_threshold": "low",
                }
            )
        if len(row) > metadata_offset:
            policy["policy_version"] = int(row[metadata_offset] or 1)
            metadata_offset += 1
        if len(row) > metadata_offset:
            policy["product_name"] = row[metadata_offset]
            policy["repository_name"] = row[metadata_offset + 1]
            policy["repository_default_branch"] = row[metadata_offset + 2]
            policy["runner_name"] = row[metadata_offset + 3]
        return policy

    def load_workflow_runtime(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                graph_runs = self._load_graph_runs(cursor)
                graph_checkpoints = self._load_graph_checkpoints(cursor)
                human_reviews = self._load_human_reviews(cursor)
        return {
            "graph_checkpoints": graph_checkpoints,
            "graph_runs": graph_runs,
            "human_reviews": human_reviews,
        }

    def save_workflow_runtime(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_workflow_runtime(payload)

    def save_requirement_and_ai_task_records(
        self,
        *,
        requirement: dict[str, Any],
        task: dict[str, Any],
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._require_callback(self._upsert_requirements, "requirement upsert")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._upsert_requirements(cursor, {requirement["id"]: requirement})
                self.upsert_ai_tasks(cursor, {task["id"]: task})
                if audit_event is not None:
                    self._require_callback(self._upsert_audit_events, "audit upsert")
                    self._upsert_audit_events(cursor, [audit_event])

    def save_bug_and_ai_task_records(
        self,
        *,
        bug: dict[str, Any],
        task: dict[str, Any],
        audit_events: list[dict[str, Any]],
    ) -> None:
        self._require_callback(self._upsert_bugs, "bug upsert")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_tasks(cursor, {task["id"]: task})
                self._upsert_bugs(cursor, {bug["id"]: bug})
                if audit_events:
                    self._require_callback(self._upsert_audit_events, "audit upsert")
                    self._upsert_audit_events(cursor, audit_events)

    def save_task_start_records(
        self,
        *,
        task: dict[str, Any],
        review: dict[str, Any],
        graph_run: dict[str, Any],
        checkpoint: dict[str, Any],
        audit_events: list[dict[str, Any]],
        model_log: dict[str, Any] | None = None,
        code_review_report: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_tasks(cursor, {task["id"]: task})
                if model_log is not None:
                    self._require_callback(self._upsert_model_gateway_logs, "model log upsert")
                    self._upsert_model_gateway_logs(cursor, [model_log])
                self.upsert_human_reviews(cursor, {review["id"]: review})
                self.upsert_graph_runs(cursor, {graph_run["id"]: graph_run})
                self.upsert_graph_checkpoints(cursor, {checkpoint["id"]: checkpoint})
                if code_review_report is not None:
                    self._require_callback(
                        self._upsert_code_review_reports,
                        "code review report upsert",
                    )
                    self._upsert_code_review_reports(
                        cursor,
                        {code_review_report["id"]: code_review_report},
                    )
                self._require_callback(self._upsert_audit_events, "audit upsert")
                self._upsert_audit_events(cursor, audit_events)

    def save_review_decision_records(
        self,
        *,
        task: dict[str, Any],
        review: dict[str, Any],
        graph_run: dict[str, Any] | None,
        checkpoint: dict[str, Any] | None,
        audit_events: list[dict[str, Any]],
        requirement: dict[str, Any] | None = None,
        knowledge_deposits: list[dict[str, Any]] | None = None,
        bugs: list[dict[str, Any]] | None = None,
        code_review_report: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if requirement is not None:
                    self._require_callback(self._upsert_requirements, "requirement upsert")
                    self._upsert_requirements(cursor, {requirement["id"]: requirement})
                self.upsert_ai_tasks(cursor, {task["id"]: task})
                self.upsert_human_reviews(cursor, {review["id"]: review})
                if graph_run is not None:
                    self.upsert_graph_runs(cursor, {graph_run["id"]: graph_run})
                if checkpoint is not None:
                    self.upsert_graph_checkpoints(cursor, {checkpoint["id"]: checkpoint})
                if code_review_report is not None:
                    self._require_callback(
                        self._upsert_code_review_reports,
                        "code review report upsert",
                    )
                    self._upsert_code_review_reports(
                        cursor,
                        {code_review_report["id"]: code_review_report},
                    )
                if bugs:
                    self._require_callback(self._upsert_bugs, "bug upsert")
                    self._upsert_bugs(cursor, {bug["id"]: bug for bug in bugs})
                if knowledge_deposits:
                    self._require_callback(
                        self._upsert_knowledge_deposits,
                        "knowledge deposit upsert",
                    )
                    self._upsert_knowledge_deposits(
                        cursor,
                        {deposit["id"]: deposit for deposit in knowledge_deposits},
                    )
                self._require_callback(self._upsert_audit_events, "audit upsert")
                self._upsert_audit_events(cursor, audit_events)

    def save_task_state_records(
        self,
        *,
        task: dict[str, Any],
        audit_events: list[dict[str, Any]],
        reviews: list[dict[str, Any]] | None = None,
        graph_run: dict[str, Any] | None = None,
        checkpoint: dict[str, Any] | None = None,
        model_log: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_ai_tasks(cursor, {task["id"]: task})
                if model_log is not None:
                    self._require_callback(self._upsert_model_gateway_logs, "model log upsert")
                    self._upsert_model_gateway_logs(cursor, [model_log])
                if reviews:
                    self.upsert_human_reviews(
                        cursor,
                        {review["id"]: review for review in reviews},
                    )
                if graph_run is not None:
                    self.upsert_graph_runs(cursor, {graph_run["id"]: graph_run})
                if checkpoint is not None:
                    self.upsert_graph_checkpoints(cursor, {checkpoint["id"]: checkpoint})
                self._require_callback(self._upsert_audit_events, "audit upsert")
                self._upsert_audit_events(cursor, audit_events)

    @staticmethod
    def _require_callback(callback, label: str) -> None:
        if callback is None:
            raise RuntimeError(f"{label} callback is not configured")

    def upsert_graph_runs(self, cursor, graph_runs: dict[str, dict[str, Any]]) -> None:
        self._write_repository.upsert_graph_runs(cursor, graph_runs)

    def upsert_graph_checkpoints(
        self,
        cursor,
        graph_checkpoints: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_graph_checkpoints(cursor, graph_checkpoints)

    def upsert_human_reviews(self, cursor, human_reviews: dict[str, dict[str, Any]]) -> None:
        self._write_repository.upsert_human_reviews(cursor, human_reviews)

    def _append_ai_task_read_scope(
        self,
        where_clauses: list[str],
        *,
        read_scope: str | None,
        table_alias: str = "t",
    ) -> None:
        if read_scope is None or read_scope == "all":
            return
        if read_scope == "code_review":
            where_clauses.append(f"{table_alias}.task_type = 'code_review'")
            return
        if read_scope == "non_code_review":
            where_clauses.append(f"{table_alias}.task_type <> 'code_review'")
            return
        if read_scope == "none":
            where_clauses.append("1 = 0")
            return
        raise ValueError(f"Unsupported AI task read scope: {read_scope}")

    def _ai_task_summary_where(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        requirement_id: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
        keyword: str | None = None,
        created_by: str | None = None,
        read_scope: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if keyword is not None:
            where_clauses.append("(t.id ILIKE %s OR t.title ILIKE %s OR t.task_type ILIKE %s)")
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
        if created_by is not None:
            where_clauses.append("t.created_by ILIKE %s")
            params.append(f"%{created_by}%")
        if status is not None:
            where_clauses.append("t.status = %s")
            params.append(status)
        if task_type is not None:
            where_clauses.append("t.task_type = %s")
            params.append(task_type)
        if product_id is not None:
            where_clauses.append("t.product_id = %s")
            params.append(product_id)
        if product_scope_ids is not None:
            if product_scope_ids:
                where_clauses.append("t.product_id = ANY(%s)")
                params.append(product_scope_ids)
            else:
                where_clauses.append("1 = 0")
        if requirement_id is not None:
            where_clauses.append("t.requirement_id = %s")
            params.append(requirement_id)
        if created_from is not None:
            where_clauses.append("COALESCE(t.created_at, t.updated_at) >= %s")
            params.append(created_from)
        if created_to is not None:
            where_clauses.append("COALESCE(t.created_at, t.updated_at) <= %s")
            params.append(created_to)
        self._append_ai_task_read_scope(where_clauses, read_scope=read_scope)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_clause, params

    def count_ai_task_summaries(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        requirement_id: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
        keyword: str | None = None,
        created_by: str | None = None,
        read_scope: str | None = None,
    ) -> int:
        where_clause, params = self._ai_task_summary_where(
            status=status,
            task_type=task_type,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            requirement_id=requirement_id,
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            created_by=created_by,
            read_scope=read_scope,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM ai_tasks t
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_ai_task_summaries(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        requirement_id: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
        keyword: str | None = None,
        created_by: str | None = None,
        read_scope: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        where_clause, params = self._ai_task_summary_where(
            status=status,
            task_type=task_type,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            requirement_id=requirement_id,
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            created_by=created_by,
            read_scope=read_scope,
        )
        sort_columns = {
            "created_at": "COALESCE(t.created_at, t.updated_at)",
            "created_by": "t.created_by",
            "id": "t.id",
            "product_id": "t.product_id",
            "product_name": "COALESCE(p.name, t.product_context->'product'->>'name')",
            "status": "t.status",
            "task_type": "t.task_type",
            "title": "t.title",
            "updated_at": "COALESCE(t.updated_at, t.created_at)",
        }
        order_column = sort_columns.get(sort_by, sort_columns["created_at"])
        order_direction = "ASC" if sort_order == "asc" else "DESC"
        paging_clause = ""
        if limit is not None:
            paging_clause += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            paging_clause += " OFFSET %s"
            params.append(offset)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT t.id, t.brain_app_id, t.requirement_id, t.task_type, t.title,
                           t.status, t.product_id, t.version_id, t.module_code,
                           t.current_step, t.created_by, t.created_at, t.updated_at,
                           COALESCE(p.name, t.product_context->'product'->>'name'),
                           t.input_json
                    FROM ai_tasks t
                    LEFT JOIN products p ON p.id = t.product_id
                    {where_clause}
                    ORDER BY {order_column} {order_direction}, t.id ASC
                    {paging_clause}
                    """,
                    tuple(params),
                )
                return [
                    {
                        "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                        "created_at": row[11].isoformat() if row[11] else None,
                        "created_by": row[10],
                        "current_step": row[9],
                        "id": row[0],
                        "module_code": row[8],
                        "product_id": row[6],
                        "product_name": row[13],
                        "requirement_id": row[2],
                        "status": row[5],
                        "task_type": row[3],
                        "title": (
                            code_inspection_remediation_title(
                                row[14] if isinstance(row[14], dict) else {},
                                fallback_title=row[4],
                            )
                            if row[3] == "code_inspection_remediation"
                            else row[4]
                        ),
                        "updated_at": row[12].isoformat() if row[12] else None,
                        "version_id": row[7],
                    }
                    for row in cursor.fetchall()
                ]

    def _load_ai_tasks(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, brain_app_id, requirement_id, task_type, title, status,
                   product_id, version_id,
                   module_code, requirement_snapshot, product_context, input_json, output_json,
                   current_step, error_code, error_message, created_by, created_at, updated_at
            FROM ai_tasks
            ORDER BY id
            """
        )
        ai_tasks = {}
        for row in cursor.fetchall():
            task = {
                "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                "created_at": row[17].isoformat() if row[17] else None,
                "created_by": row[16],
                "current_step": row[13],
                "error_code": row[14],
                "error_message": row[15],
                "graph_run_ids": [],
                "id": row[0],
                "input_json": dict(row[11] or {}),
                "module_code": row[8],
                "output_json": row[12],
                "product_context": dict(row[10] or {}),
                "product_id": row[6],
                "requirement_id": row[2],
                "requirement_snapshot": row[9],
                "review_ids": [],
                "status": row[5],
                "task_type": row[3],
                "title": row[4],
                "updated_at": row[18].isoformat() if row[18] else None,
                "version_id": row[7],
            }
            ai_tasks[row[0]] = task
        return ai_tasks

    def _load_graph_runs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, task_type, status, current_step, checkpoint_id,
                   runtime, node_path, state_snapshot, started_at, completed_at,
                   created_at, updated_at
            FROM graph_runs
            ORDER BY started_at, id
            """
        )
        return {
            row[0]: {
                "ai_task_id": row[1],
                "checkpoint_id": row[5],
                "completed_at": row[10].isoformat() if row[10] else None,
                "created_at": row[11].isoformat() if row[11] else None,
                "current_step": row[4],
                "id": row[0],
                "node_path": list(row[7] or []),
                "runtime": row[6],
                "started_at": row[9].isoformat() if row[9] else None,
                "state_snapshot": dict(row[8] or {}),
                "status": row[3],
                "task_type": row[2],
                "updated_at": row[12].isoformat() if row[12] else None,
            }
            for row in cursor.fetchall()
        }

    def _load_graph_checkpoints(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, graph_run_id, ai_task_id, current_step, state_snapshot,
                   created_at, updated_at
            FROM graph_checkpoints
            ORDER BY created_at, id
            """
        )
        return {
            row[0]: {
                "ai_task_id": row[2],
                "created_at": row[5].isoformat() if row[5] else None,
                "current_step": row[3],
                "graph_run_id": row[1],
                "id": row[0],
                "state_snapshot": dict(row[4] or {}),
                "updated_at": row[6].isoformat() if row[6] else None,
            }
            for row in cursor.fetchall()
        }

    def _load_human_reviews(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, stage, status, version, content, edited_content,
                   decision_reason, decided_by, questions, decided_at, created_at, updated_at
            FROM human_reviews
            ORDER BY created_at, id
            """
        )
        human_reviews = {}
        for row in cursor.fetchall():
            review = {
                "ai_task_id": row[1],
                "content": dict(row[5] or {}),
                "created_at": row[11].isoformat() if row[11] else None,
                "decided_at": row[10].isoformat() if row[10] else None,
                "decided_by": row[8],
                "decision_reason": row[7],
                "edited_content": row[6],
                "id": row[0],
                "questions": list(row[9] or []),
                "stage": row[2],
                "status": row[3],
                "updated_at": row[12].isoformat() if row[12] else None,
                "version": row[4],
            }
            if review["edited_content"] is None:
                review.pop("edited_content")
            if review["decision_reason"] is None:
                review.pop("decision_reason")
            if review["decided_by"] is None:
                review.pop("decided_by")
            if review["decided_at"] is None:
                review.pop("decided_at")
            if not review["questions"]:
                review.pop("questions")
            human_reviews[row[0]] = review
        return human_reviews

    def _pending_review_summary_where(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        read_scope: str | None = None,
    ) -> tuple[str, list[Any]]:
        where_clauses = ["r.status = 'pending'"]
        params: list[Any] = []
        if ai_task_id is not None:
            where_clauses.append("r.ai_task_id = %s")
            params.append(ai_task_id)
        if product_scope_ids is not None:
            if product_scope_ids:
                where_clauses.append("t.product_id = ANY(%s)")
                params.append(product_scope_ids)
            else:
                where_clauses.append("1 = 0")
        self._append_ai_task_read_scope(where_clauses, read_scope=read_scope, table_alias="t")
        where_clause = f"WHERE {' AND '.join(where_clauses)}"
        return where_clause, params

    def count_pending_review_summaries(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        read_scope: str | None = None,
    ) -> int:
        where_clause, params = self._pending_review_summary_where(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            read_scope=read_scope,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM human_reviews r
                    JOIN ai_tasks t ON t.id = r.ai_task_id
                    {where_clause}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_pending_review_summaries(
        self,
        *,
        ai_task_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        product_scope_ids: list[str] | None = None,
        read_scope: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        where_clause, params = self._pending_review_summary_where(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            read_scope=read_scope,
        )
        sort_columns = {
            "ai_task_id": "r.ai_task_id",
            "created_at": "COALESCE(r.created_at, r.updated_at)",
            "id": "r.id",
            "stage": "r.stage",
            "status": "r.status",
            "updated_at": "COALESCE(r.updated_at, r.created_at)",
        }
        order_column = sort_columns.get(sort_by, sort_columns["created_at"])
        order_direction = "ASC" if sort_order == "asc" else "DESC"
        paging_clause = ""
        if limit is not None:
            paging_clause += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            paging_clause += " OFFSET %s"
            params.append(offset)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT r.id, r.ai_task_id, r.stage, r.status, r.content, r.version,
                           r.created_at, r.updated_at
                    FROM human_reviews r
                    JOIN ai_tasks t ON t.id = r.ai_task_id
                    {where_clause}
                    ORDER BY {order_column} {order_direction}, r.id ASC
                    {paging_clause}
                    """,
                    tuple(params),
                )
                return [
                    {
                        "ai_task_id": row[1],
                        "content": row[4],
                        "created_at": row[6].isoformat() if row[6] else None,
                        "id": row[0],
                        "stage": row[2],
                        "status": row[3],
                        "updated_at": row[7].isoformat() if row[7] else None,
                        "version": row[5],
                    }
                    for row in cursor.fetchall()
                ]
