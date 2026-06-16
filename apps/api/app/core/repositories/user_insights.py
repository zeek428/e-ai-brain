from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from app.core.repositories.user_insights_lists import UserInsightListRepository
from app.core.repositories.user_insights_writes import UserInsightWriteRepository


class UserInsightReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
        upsert_requirements: Callable[[Any, dict[str, dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._list_repository = UserInsightListRepository(connect)
        self._write_repository = UserInsightWriteRepository(
            connect,
            delete_missing=delete_missing,
            upsert_audit_events=upsert_audit_events,
            upsert_requirements=upsert_requirements,
        )

    def save_user_feedback(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_user_feedback(payload)

    def save_user_feedback_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.save_user_feedback_record(record, audit_event=audit_event)

    def save_user_feedback_requirement_conversion(
        self,
        *,
        audit_events: list[dict[str, Any]],
        feedback: dict[str, Any],
        requirement: dict[str, Any],
    ) -> None:
        self._write_repository.save_user_feedback_requirement_conversion(
            audit_events=audit_events,
            feedback=feedback,
            requirement=requirement,
        )

    def save_user_usage_metrics(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_user_usage_metrics(payload)

    def save_user_usage_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.save_user_usage_metric_record(record, audit_event=audit_event)

    def save_iteration_planning(self, payload: dict[str, Any]) -> None:
        self._write_repository.save_iteration_planning(payload)

    def save_iteration_suggestion_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.save_iteration_suggestion_record(
            record,
            audit_event=audit_event,
        )

    def save_iteration_decision_records(
        self,
        *,
        suggestion: dict[str, Any],
        decision: dict[str, Any],
        audit_events: list[dict[str, Any]],
        requirement: dict[str, Any] | None = None,
    ) -> None:
        self._write_repository.save_iteration_decision_records(
            suggestion=suggestion,
            decision=decision,
            audit_events=audit_events,
            requirement=requirement,
        )

    def upsert_user_feedback(
        self,
        cursor,
        feedback_items: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_user_feedback(cursor, feedback_items)

    def upsert_user_usage_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_user_usage_metrics(cursor, metrics)

    def upsert_iteration_plan_suggestions(
        self,
        cursor,
        suggestions: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_iteration_plan_suggestions(cursor, suggestions)

    def upsert_iteration_plan_decisions(
        self,
        cursor,
        decisions: dict[str, dict[str, Any]],
    ) -> None:
        self._write_repository.upsert_iteration_plan_decisions(cursor, decisions)

    def load_user_feedback(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                feedback = self._load_user_feedback(cursor)
        return {"user_feedback": feedback}

    def list_user_feedback(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("product_id = %s")
            params.append(product_id)
        if module_code is not None:
            where_clauses.append("module_code = %s")
            params.append(module_code)
        if feature_code is not None:
            where_clauses.append("feature_code = %s")
            params.append(feature_code)
        if status is not None:
            where_clauses.append("status = %s")
            params.append(status)
        if created_by is not None:
            where_clauses.append("created_by = %s")
            params.append(created_by)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, module_code, feature_code, source_channel,
                           feedback_type, sentiment, satisfaction_score, content, tags,
                           related_requirement_id, status, triage_note, created_by,
                           created_at, updated_at
                    FROM user_feedback
                    {where_clause}
                    ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._user_feedback_from_row(row) for row in cursor.fetchall()]

    def load_user_usage_metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                metrics = self._load_user_usage_metrics(cursor)
        return {"user_usage_metrics": metrics}

    def list_user_usage_metrics(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        user_segment: str | None = None,
        from_value: Any | None = None,
        to_value: Any | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("product_id = %s")
            params.append(product_id)
        if module_code is not None:
            where_clauses.append("module_code = %s")
            params.append(module_code)
        if feature_code is not None:
            where_clauses.append("feature_code = %s")
            params.append(feature_code)
        if user_segment is not None:
            where_clauses.append("user_segment = %s")
            params.append(user_segment)
        if from_value is not None:
            where_clauses.append("window_end >= %s")
            params.append(from_value)
        if to_value is not None:
            where_clauses.append("window_start <= %s")
            params.append(to_value)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, module_code, feature_code, user_segment,
                           window_start, window_end, active_users, event_count,
                           conversion_count, conversion_rate, avg_duration_seconds,
                           bounce_rate, error_count, source_channel, created_by,
                           created_at, updated_at
                    FROM user_usage_metrics
                    {where_clause}
                    ORDER BY window_start DESC,
                             COALESCE(updated_at, created_at) DESC,
                             id DESC
                    """,
                    tuple(params),
                )
                return [self._user_usage_metric_from_row(row) for row in cursor.fetchall()]

    def load_iteration_planning(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                suggestions = self._load_iteration_plan_suggestions(cursor)
                decisions = self._load_iteration_plan_decisions(cursor)
        return {
            "iteration_plan_decisions": decisions,
            "iteration_plan_suggestions": suggestions,
        }

    def list_iteration_plan_suggestions(
        self,
        *,
        product_id: str | None = None,
        planning_cycle: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("product_id = %s")
            params.append(product_id)
        if planning_cycle is not None:
            where_clauses.append("planning_cycle = %s")
            params.append(planning_cycle)
        if status is not None:
            where_clauses.append("status = %s")
            params.append(status)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, planning_cycle, version_id, module_codes, title,
                           status, priority, priority_score, confidence_level,
                           recommendation_reason, business_value, risk_signals, dependencies,
                           estimated_effort, evidence, evidence_insufficient, created_by,
                           converted_requirement_id, created_at, updated_at
                    FROM iteration_plan_suggestions
                    {where_clause}
                    ORDER BY priority_score DESC,
                             COALESCE(updated_at, created_at) DESC,
                             id DESC
                    """,
                    tuple(params),
                )
                return [self._iteration_plan_suggestion_from_row(row) for row in cursor.fetchall()]

    def list_user_insight_items(
        self,
        *,
        category: str | None = None,
        summary: str | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        return self._list_repository.list_user_insight_items(
            category=category,
            summary=summary,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def _load_user_feedback(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, module_code, feature_code, source_channel,
                   feedback_type, sentiment, satisfaction_score, content, tags,
                   related_requirement_id, status, triage_note, created_by,
                   created_at, updated_at
            FROM user_feedback
            ORDER BY created_at, id
            """
        )
        return {row[0]: self._user_feedback_from_row(row) for row in cursor.fetchall()}

    def _load_user_usage_metrics(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, module_code, feature_code, user_segment,
                   window_start, window_end, active_users, event_count,
                   conversion_count, conversion_rate, avg_duration_seconds,
                   bounce_rate, error_count, source_channel, created_by,
                   created_at, updated_at
            FROM user_usage_metrics
            ORDER BY window_start, id
            """
        )
        return {row[0]: self._user_usage_metric_from_row(row) for row in cursor.fetchall()}

    def _load_iteration_plan_suggestions(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, planning_cycle, version_id, module_codes, title,
                   status, priority, priority_score, confidence_level,
                   recommendation_reason, business_value, risk_signals, dependencies,
                   estimated_effort, evidence, evidence_insufficient, created_by,
                   converted_requirement_id, created_at, updated_at
            FROM iteration_plan_suggestions
            ORDER BY created_at, id
            """
        )
        return {
            row[0]: self._iteration_plan_suggestion_from_row(row)
            for row in cursor.fetchall()
        }

    def _load_iteration_plan_decisions(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, suggestion_id, decision, comment, edited_title, edited_scope,
                   convert_to_requirement, created_requirement_id, decided_by, decided_at,
                   created_at, updated_at
            FROM iteration_plan_decisions
            ORDER BY decided_at, id
            """
        )
        return {row[0]: self._iteration_plan_decision_from_row(row) for row in cursor.fetchall()}

    def _user_feedback_from_row(self, row) -> dict[str, Any]:
        feedback = {
            "content": row[8],
            "created_at": row[14].isoformat() if row[14] else None,
            "created_by": row[13],
            "feature_code": row[3],
            "feedback_type": row[5],
            "id": row[0],
            "module_code": row[2],
            "product_id": row[1],
            "related_requirement_id": row[10],
            "satisfaction_score": row[7],
            "sentiment": row[6],
            "source_channel": row[4],
            "status": row[11],
            "tags": list(row[9] or []),
            "triage_note": row[12],
            "updated_at": row[15].isoformat() if row[15] else None,
        }
        for optional_key in (
            "created_at",
            "feature_code",
            "module_code",
            "related_requirement_id",
            "satisfaction_score",
            "sentiment",
            "triage_note",
            "updated_at",
        ):
            if feedback[optional_key] is None:
                feedback.pop(optional_key)
        return feedback

    def _user_usage_metric_from_row(self, row) -> dict[str, Any]:
        metric = {
            "active_users": row[7],
            "avg_duration_seconds": float(row[11]) if row[11] is not None else None,
            "bounce_rate": float(row[12]) if row[12] is not None else None,
            "conversion_count": row[9],
            "conversion_rate": float(row[10]) if row[10] is not None else None,
            "created_at": row[16].isoformat() if row[16] else None,
            "created_by": row[15],
            "error_count": row[13],
            "event_count": row[8],
            "feature_code": row[3],
            "id": row[0],
            "module_code": row[2],
            "product_id": row[1],
            "source_channel": row[14],
            "updated_at": row[17].isoformat() if row[17] else None,
            "user_segment": row[4],
            "window_end": row[6].isoformat() if row[6] else None,
            "window_start": row[5].isoformat() if row[5] else None,
        }
        for optional_key in (
            "avg_duration_seconds",
            "bounce_rate",
            "conversion_rate",
            "created_at",
            "module_code",
            "source_channel",
            "updated_at",
        ):
            if metric[optional_key] is None:
                metric.pop(optional_key)
        return metric

    def _iteration_plan_suggestion_from_row(self, row) -> dict[str, Any]:
        suggestion = {
            "business_value": row[11],
            "confidence_level": row[9],
            "converted_requirement_id": row[18],
            "created_at": row[19].isoformat() if row[19] else None,
            "created_by": row[17],
            "dependencies": list(row[13] or []),
            "estimated_effort": row[14],
            "evidence": list(row[15] or []),
            "evidence_insufficient": row[16],
            "id": row[0],
            "module_codes": list(row[4] or []),
            "planning_cycle": row[2],
            "priority": row[7],
            "priority_score": row[8],
            "product_id": row[1],
            "recommendation_reason": row[10],
            "risk_signals": list(row[12] or []),
            "status": row[6],
            "title": row[5],
            "updated_at": row[20].isoformat() if row[20] else None,
            "version_id": row[3],
        }
        for optional_key in (
            "converted_requirement_id",
            "created_at",
            "updated_at",
            "version_id",
        ):
            if suggestion[optional_key] is None:
                suggestion.pop(optional_key)
        return suggestion

    def _iteration_plan_decision_from_row(self, row) -> dict[str, Any]:
        decision = {
            "comment": row[3],
            "convert_to_requirement": row[6],
            "created_at": row[10].isoformat() if row[10] else None,
            "created_requirement_id": row[7],
            "decided_at": row[9].isoformat() if row[9] else None,
            "decided_by": row[8],
            "decision": row[2],
            "edited_scope": row[5],
            "edited_title": row[4],
            "id": row[0],
            "suggestion_id": row[1],
            "updated_at": row[11].isoformat() if row[11] else None,
        }
        for optional_key in (
            "comment",
            "created_at",
            "created_requirement_id",
            "decided_at",
            "edited_scope",
            "edited_title",
            "updated_at",
        ):
            if decision[optional_key] is None:
                decision.pop(optional_key)
        return decision
