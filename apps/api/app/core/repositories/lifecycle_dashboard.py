from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class LifecycleDashboardReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        list_ai_task_summaries: Callable[..., list[dict[str, Any]]],
        list_audit_events: Callable[..., list[dict[str, Any]]],
        list_bugs: Callable[..., list[dict[str, Any]]],
        list_gitlab_daily_code_metrics: Callable[..., list[dict[str, Any]]],
        list_iteration_plan_suggestions: Callable[..., list[dict[str, Any]]],
        list_jenkins_release_records: Callable[..., list[dict[str, Any]]],
        list_online_log_metrics: Callable[..., list[dict[str, Any]]],
        list_products: Callable[..., list[dict[str, Any]]],
        list_requirement_summaries: Callable[..., list[dict[str, Any]]],
        list_user_feedback: Callable[..., list[dict[str, Any]]],
        list_user_usage_metrics: Callable[..., list[dict[str, Any]]],
        load_gitlab_review: Callable[[], dict[str, Any] | None],
        load_knowledge: Callable[[], dict[str, Any] | None],
        load_mock_writebacks: Callable[[], dict[str, Any] | None],
        load_product_config: Callable[[], dict[str, Any] | None],
        load_workflow_runtime: Callable[[], dict[str, Any] | None],
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing
        self._list_ai_task_summaries = list_ai_task_summaries
        self._list_audit_events = list_audit_events
        self._list_bugs = list_bugs
        self._list_gitlab_daily_code_metrics = list_gitlab_daily_code_metrics
        self._list_iteration_plan_suggestions = list_iteration_plan_suggestions
        self._list_jenkins_release_records = list_jenkins_release_records
        self._list_online_log_metrics = list_online_log_metrics
        self._list_products = list_products
        self._list_requirement_summaries = list_requirement_summaries
        self._list_user_feedback = list_user_feedback
        self._list_user_usage_metrics = list_user_usage_metrics
        self._load_gitlab_review = load_gitlab_review
        self._load_knowledge = load_knowledge
        self._load_mock_writebacks = load_mock_writebacks
        self._load_product_config = load_product_config
        self._load_workflow_runtime = load_workflow_runtime

    def save_lifecycle_context(self, payload: dict[str, Any]) -> None:
        edges = payload.get("lifecycle_context_edges", {})
        risks = payload.get("lifecycle_risk_signals", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "lifecycle_risk_signals", risks)
                    self._delete_missing(cursor, "lifecycle_context_edges", edges)
                self.upsert_lifecycle_context_edges(cursor, edges)
                self.upsert_lifecycle_risk_signals(cursor, risks)

    def save_dashboard_snapshots(self, payload: dict[str, Any]) -> None:
        snapshots = payload.get("dashboard_metric_snapshots", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "dashboard_metric_snapshots", snapshots)
                self.upsert_dashboard_metric_snapshots(cursor, snapshots)

    def save_dashboard_metric_snapshot_record(self, snapshot: dict[str, Any]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_dashboard_metric_snapshots(cursor, {snapshot["id"]: snapshot})

    def upsert_lifecycle_context_edges(
        self,
        cursor,
        edges: dict[str, dict[str, Any]],
    ) -> None:
        for edge in edges.values():
            created_at = edge.get("created_at") or edge.get("observed_at")
            updated_at = edge.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO lifecycle_context_edges (
                  id, source_subject_type, source_subject_id, target_subject_type,
                  target_subject_id, relation_type, product_id, version_id,
                  module_code, confidence, source_module, observed_at, metadata,
                  summary, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), %s::jsonb, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  source_subject_type = EXCLUDED.source_subject_type,
                  source_subject_id = EXCLUDED.source_subject_id,
                  target_subject_type = EXCLUDED.target_subject_type,
                  target_subject_id = EXCLUDED.target_subject_id,
                  relation_type = EXCLUDED.relation_type,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  confidence = EXCLUDED.confidence,
                  source_module = EXCLUDED.source_module,
                  observed_at = EXCLUDED.observed_at,
                  metadata = EXCLUDED.metadata,
                  summary = EXCLUDED.summary,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    edge["id"],
                    edge["source_subject_type"],
                    edge["source_subject_id"],
                    edge["target_subject_type"],
                    edge["target_subject_id"],
                    edge["relation_type"],
                    edge.get("product_id"),
                    edge.get("version_id"),
                    edge.get("module_code"),
                    edge.get("confidence", 1.0),
                    edge.get("source_module", "lifecycle_context"),
                    edge.get("observed_at"),
                    json.dumps(edge.get("metadata", {}), ensure_ascii=False),
                    edge.get("summary"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_lifecycle_risk_signals(
        self,
        cursor,
        risks: dict[str, dict[str, Any]],
    ) -> None:
        for risk in risks.values():
            created_at = risk.get("created_at") or risk.get("observed_at")
            updated_at = risk.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO lifecycle_risk_signals (
                  id, product_id, version_id, module_code, requirement_id, task_id,
                  risk_type, severity, source_subject_type, source_subject_id,
                  impact_summary, recommendation, observed_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  requirement_id = EXCLUDED.requirement_id,
                  task_id = EXCLUDED.task_id,
                  risk_type = EXCLUDED.risk_type,
                  severity = EXCLUDED.severity,
                  source_subject_type = EXCLUDED.source_subject_type,
                  source_subject_id = EXCLUDED.source_subject_id,
                  impact_summary = EXCLUDED.impact_summary,
                  recommendation = EXCLUDED.recommendation,
                  observed_at = EXCLUDED.observed_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    risk["id"],
                    risk.get("product_id"),
                    risk.get("version_id"),
                    risk.get("module_code"),
                    risk.get("requirement_id"),
                    risk.get("task_id"),
                    risk["risk_type"],
                    risk["severity"],
                    risk["source_subject_type"],
                    risk["source_subject_id"],
                    risk["impact_summary"],
                    risk["recommendation"],
                    risk.get("observed_at"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_dashboard_metric_snapshots(
        self,
        cursor,
        snapshots: dict[str, dict[str, Any]],
    ) -> None:
        for snapshot in snapshots.values():
            created_at = snapshot.get("created_at")
            updated_at = snapshot.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO dashboard_metric_snapshots (
                  id, product_id, time_range, window_start, window_end, metrics,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::timestamptz, %s::timestamptz, %s::jsonb,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  time_range = EXCLUDED.time_range,
                  window_start = EXCLUDED.window_start,
                  window_end = EXCLUDED.window_end,
                  metrics = EXCLUDED.metrics,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    snapshot["id"],
                    snapshot.get("product_id"),
                    snapshot.get("time_range", "all"),
                    snapshot.get("window_start"),
                    snapshot.get("window_end"),
                    json.dumps(snapshot.get("metrics", {}), ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def load_lifecycle_context(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                edges = self._load_lifecycle_context_edges(cursor)
                risks = self._load_lifecycle_risk_signals(cursor)
        return {
            "lifecycle_context_edges": edges,
            "lifecycle_risk_signals": risks,
        }

    def get_lifecycle_context_source_rows(
        self,
        *,
        product_id: str | None = None,
    ) -> dict[str, Any]:
        rows = self.get_dashboard_it_team_source_rows(
            user_roles=["admin"],
            product_id=product_id,
        )
        lifecycle_payload = self.load_lifecycle_context() or {}
        rows["lifecycle_context_edges"] = list(
            (lifecycle_payload.get("lifecycle_context_edges") or {}).values()
        )
        rows["lifecycle_risk_signals"] = list(
            (lifecycle_payload.get("lifecycle_risk_signals") or {}).values()
        )
        return rows

    def load_dashboard_snapshots(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                snapshots = self._load_dashboard_metric_snapshots(cursor)
        return {"dashboard_metric_snapshots": snapshots}

    def get_dashboard_it_team_source_rows(
        self,
        *,
        user_roles: list[str],
        product_id: str | None = None,
    ) -> dict[str, Any]:
        workflow = self._load_workflow_runtime() or {}
        knowledge = self._load_knowledge() or {}
        product_config = self._load_product_config() or {}
        review_payload = self._load_gitlab_review() or {}
        mock_payload = self._load_mock_writebacks() or {}
        user_role_set = set(user_roles)
        knowledge_documents = [
            dict(document)
            for document in (knowledge.get("knowledge_documents") or {}).values()
            if "admin" in user_role_set
            or user_role_set.intersection(document.get("permission_roles", []))
        ]
        return {
            "audit_events": self._list_audit_events(),
            "bugs": self._list_bugs(product_id=product_id),
            "code_review_reports": list(
                (review_payload.get("code_review_reports") or {}).values()
            ),
            "gitlab_daily_code_metrics": self._list_gitlab_daily_code_metrics(
                product_id=product_id
            ),
            "gitlab_mr_snapshots": list(
                (review_payload.get("gitlab_mr_snapshots") or {}).values()
            ),
            "human_reviews": list((workflow.get("human_reviews") or {}).values()),
            "iteration_plan_suggestions": self._list_iteration_plan_suggestions(
                product_id=product_id
            ),
            "jenkins_release_records": self._list_jenkins_release_records(
                product_id=product_id
            ),
            "knowledge_deposits": list(
                (knowledge.get("knowledge_deposits") or {}).values()
            ),
            "knowledge_documents": knowledge_documents,
            "mock_writebacks": list((mock_payload.get("mock_writebacks") or {}).values()),
            "online_log_metrics": self._list_online_log_metrics(product_id=product_id),
            "product_git_repositories": list(
                (product_config.get("product_git_repositories") or {}).values()
            ),
            "product_modules": list((product_config.get("product_modules") or {}).values()),
            "product_versions": list((product_config.get("product_versions") or {}).values()),
            "products": self._list_products(active_only=True),
            "requirements": self._list_requirement_summaries(product_id=product_id),
            "tasks": self._list_ai_task_summaries(product_id=product_id),
            "user_feedback": self._list_user_feedback(product_id=product_id),
            "user_usage_metrics": self._list_user_usage_metrics(product_id=product_id),
        }

    def _load_lifecycle_context_edges(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, source_subject_type, source_subject_id, target_subject_type,
                   target_subject_id, relation_type, product_id, version_id,
                   module_code, confidence, source_module, observed_at, metadata,
                   summary, created_at, updated_at
            FROM lifecycle_context_edges
            ORDER BY observed_at, id
            """
        )
        edges = {}
        for row in cursor.fetchall():
            edge = {
                "confidence": float(row[9]) if row[9] is not None else 1.0,
                "created_at": row[14].isoformat() if row[14] else None,
                "id": row[0],
                "metadata": dict(row[12] or {}),
                "module_code": row[8],
                "observed_at": row[11].isoformat() if row[11] else None,
                "product_id": row[6],
                "relation_type": row[5],
                "source_module": row[10],
                "source_subject_id": row[2],
                "source_subject_type": row[1],
                "summary": row[13],
                "target_subject_id": row[4],
                "target_subject_type": row[3],
                "updated_at": row[15].isoformat() if row[15] else None,
                "version_id": row[7],
            }
            for optional_key in (
                "created_at",
                "module_code",
                "observed_at",
                "product_id",
                "summary",
                "updated_at",
                "version_id",
            ):
                if edge[optional_key] is None:
                    edge.pop(optional_key)
            edges[row[0]] = edge
        return edges

    def _load_lifecycle_risk_signals(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, version_id, module_code, requirement_id, task_id,
                   risk_type, severity, source_subject_type, source_subject_id,
                   impact_summary, recommendation, observed_at, created_at, updated_at
            FROM lifecycle_risk_signals
            ORDER BY observed_at, id
            """
        )
        risks = {}
        for row in cursor.fetchall():
            risk = {
                "created_at": row[13].isoformat() if row[13] else None,
                "id": row[0],
                "impact_summary": row[10],
                "module_code": row[3],
                "observed_at": row[12].isoformat() if row[12] else None,
                "product_id": row[1],
                "recommendation": row[11],
                "requirement_id": row[4],
                "risk_type": row[6],
                "severity": row[7],
                "source_subject_id": row[9],
                "source_subject_type": row[8],
                "task_id": row[5],
                "updated_at": row[14].isoformat() if row[14] else None,
                "version_id": row[2],
            }
            for optional_key in (
                "created_at",
                "module_code",
                "observed_at",
                "product_id",
                "requirement_id",
                "task_id",
                "updated_at",
                "version_id",
            ):
                if risk[optional_key] is None:
                    risk.pop(optional_key)
            risks[row[0]] = risk
        return risks

    def _load_dashboard_metric_snapshots(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, time_range, window_start, window_end, metrics,
                   created_at, updated_at
            FROM dashboard_metric_snapshots
            ORDER BY updated_at, id
            """
        )
        snapshots = {}
        for row in cursor.fetchall():
            snapshot = {
                "created_at": row[6].isoformat() if row[6] else None,
                "id": row[0],
                "metrics": dict(row[5] or {}),
                "product_id": row[1],
                "time_range": row[2],
                "updated_at": row[7].isoformat() if row[7] else None,
                "window_end": row[4].isoformat() if row[4] else None,
                "window_start": row[3].isoformat() if row[3] else None,
            }
            for optional_key in (
                "created_at",
                "product_id",
                "updated_at",
                "window_end",
                "window_start",
            ):
                if snapshot[optional_key] is None:
                    snapshot.pop(optional_key)
            snapshots[row[0]] = snapshot
        return snapshots
