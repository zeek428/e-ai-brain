from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class UserInsightWriteRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
        upsert_requirements: Callable[[Any, dict[str, dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing
        self._upsert_audit_events = upsert_audit_events
        self._upsert_requirements = upsert_requirements

    def save_user_feedback(self, payload: dict[str, Any]) -> None:
        feedback = payload.get("user_feedback", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "user_feedback", feedback)
                self.upsert_user_feedback(cursor, feedback)

    def save_user_feedback_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_user_feedback(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_user_feedback_requirement_conversion(
        self,
        *,
        audit_events: list[dict[str, Any]],
        feedback: dict[str, Any],
        requirement: dict[str, Any],
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._upsert_requirements is not None:
                    self._upsert_requirements(cursor, {requirement["id"]: requirement})
                self.upsert_user_feedback(cursor, {feedback["id"]: feedback})
                if self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, audit_events)

    def save_user_usage_metrics(self, payload: dict[str, Any]) -> None:
        metrics = payload.get("user_usage_metrics", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "user_usage_metrics", metrics)
                self.upsert_user_usage_metrics(cursor, metrics)

    def save_user_usage_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_user_usage_metrics(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_iteration_planning(self, payload: dict[str, Any]) -> None:
        suggestions = payload.get("iteration_plan_suggestions", {})
        decisions = payload.get("iteration_plan_decisions", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if self._delete_missing is not None:
                    self._delete_missing(cursor, "iteration_plan_decisions", decisions)
                    self._delete_missing(cursor, "iteration_plan_suggestions", suggestions)
                self.upsert_iteration_plan_suggestions(cursor, suggestions)
                self.upsert_iteration_plan_decisions(cursor, decisions)

    def save_iteration_suggestion_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_iteration_plan_suggestions(cursor, {record["id"]: record})
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def save_iteration_decision_records(
        self,
        *,
        suggestion: dict[str, Any],
        decision: dict[str, Any],
        audit_events: list[dict[str, Any]],
        requirement: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if requirement is not None and self._upsert_requirements is not None:
                    self._upsert_requirements(cursor, {requirement["id"]: requirement})
                self.upsert_iteration_plan_suggestions(cursor, {suggestion["id"]: suggestion})
                self.upsert_iteration_plan_decisions(cursor, {decision["id"]: decision})
                if self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, audit_events)

    def upsert_user_feedback(
        self,
        cursor,
        feedback_items: dict[str, dict[str, Any]],
    ) -> None:
        for feedback in feedback_items.values():
            created_at = feedback.get("created_at")
            updated_at = feedback.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO user_feedback (
                  id, product_id, module_code, feature_code, source_channel,
                  feedback_type, sentiment, satisfaction_score, content, tags,
                  related_requirement_id, status, triage_note, created_by,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  module_code = EXCLUDED.module_code,
                  feature_code = EXCLUDED.feature_code,
                  source_channel = EXCLUDED.source_channel,
                  feedback_type = EXCLUDED.feedback_type,
                  sentiment = EXCLUDED.sentiment,
                  satisfaction_score = EXCLUDED.satisfaction_score,
                  content = EXCLUDED.content,
                  tags = EXCLUDED.tags,
                  related_requirement_id = EXCLUDED.related_requirement_id,
                  status = EXCLUDED.status,
                  triage_note = EXCLUDED.triage_note,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    feedback["id"],
                    feedback["product_id"],
                    feedback.get("module_code"),
                    feedback.get("feature_code"),
                    feedback.get("source_channel", "in_app"),
                    feedback["feedback_type"],
                    feedback.get("sentiment"),
                    feedback.get("satisfaction_score"),
                    feedback["content"],
                    json.dumps(feedback.get("tags", []), ensure_ascii=False),
                    feedback.get("related_requirement_id"),
                    feedback.get("status", "open"),
                    feedback.get("triage_note"),
                    feedback["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def upsert_user_usage_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        for metric in metrics.values():
            created_at = metric.get("created_at")
            updated_at = metric.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO user_usage_metrics (
                  id, product_id, module_code, feature_code, user_segment,
                  window_start, window_end, active_users, event_count,
                  conversion_count, conversion_rate, avg_duration_seconds,
                  bounce_rate, error_count, source_channel, created_by,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  module_code = EXCLUDED.module_code,
                  feature_code = EXCLUDED.feature_code,
                  user_segment = EXCLUDED.user_segment,
                  window_start = EXCLUDED.window_start,
                  window_end = EXCLUDED.window_end,
                  active_users = EXCLUDED.active_users,
                  event_count = EXCLUDED.event_count,
                  conversion_count = EXCLUDED.conversion_count,
                  conversion_rate = EXCLUDED.conversion_rate,
                  avg_duration_seconds = EXCLUDED.avg_duration_seconds,
                  bounce_rate = EXCLUDED.bounce_rate,
                  error_count = EXCLUDED.error_count,
                  source_channel = EXCLUDED.source_channel,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    metric["id"],
                    metric["product_id"],
                    metric.get("module_code"),
                    metric["feature_code"],
                    metric.get("user_segment", "all"),
                    metric["window_start"],
                    metric["window_end"],
                    metric.get("active_users", 0),
                    metric.get("event_count", 0),
                    metric.get("conversion_count", 0),
                    metric.get("conversion_rate"),
                    metric.get("avg_duration_seconds"),
                    metric.get("bounce_rate"),
                    metric.get("error_count", 0),
                    metric.get("source_channel"),
                    metric["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def upsert_iteration_plan_suggestions(
        self,
        cursor,
        suggestions: dict[str, dict[str, Any]],
    ) -> None:
        for suggestion in suggestions.values():
            created_at = suggestion.get("created_at")
            updated_at = suggestion.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO iteration_plan_suggestions (
                  id, product_id, planning_cycle, version_id, module_codes, title,
                  status, priority, priority_score, confidence_level,
                  recommendation_reason, business_value, risk_signals, dependencies,
                  estimated_effort, evidence, evidence_insufficient, created_by,
                  converted_requirement_id, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  planning_cycle = EXCLUDED.planning_cycle,
                  version_id = EXCLUDED.version_id,
                  module_codes = EXCLUDED.module_codes,
                  title = EXCLUDED.title,
                  status = EXCLUDED.status,
                  priority = EXCLUDED.priority,
                  priority_score = EXCLUDED.priority_score,
                  confidence_level = EXCLUDED.confidence_level,
                  recommendation_reason = EXCLUDED.recommendation_reason,
                  business_value = EXCLUDED.business_value,
                  risk_signals = EXCLUDED.risk_signals,
                  dependencies = EXCLUDED.dependencies,
                  estimated_effort = EXCLUDED.estimated_effort,
                  evidence = EXCLUDED.evidence,
                  evidence_insufficient = EXCLUDED.evidence_insufficient,
                  created_by = EXCLUDED.created_by,
                  converted_requirement_id = EXCLUDED.converted_requirement_id,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    suggestion["id"],
                    suggestion["product_id"],
                    suggestion["planning_cycle"],
                    suggestion.get("version_id"),
                    json.dumps(suggestion.get("module_codes", []), ensure_ascii=False),
                    suggestion["title"],
                    suggestion.get("status", "suggested"),
                    suggestion.get("priority", "P2"),
                    suggestion.get("priority_score", 0),
                    suggestion.get("confidence_level", "low"),
                    suggestion["recommendation_reason"],
                    suggestion["business_value"],
                    json.dumps(suggestion.get("risk_signals", []), ensure_ascii=False),
                    json.dumps(suggestion.get("dependencies", []), ensure_ascii=False),
                    suggestion.get("estimated_effort", "medium"),
                    json.dumps(suggestion.get("evidence", []), ensure_ascii=False),
                    suggestion.get("evidence_insufficient", False),
                    suggestion["created_by"],
                    suggestion.get("converted_requirement_id"),
                    created_at,
                    updated_at,
                ),
            )

    def upsert_iteration_plan_decisions(
        self,
        cursor,
        decisions: dict[str, dict[str, Any]],
    ) -> None:
        for decision in decisions.values():
            created_at = decision.get("created_at") or decision.get("decided_at")
            updated_at = decision.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO iteration_plan_decisions (
                  id, suggestion_id, decision, comment, edited_title, edited_scope,
                  convert_to_requirement, created_requirement_id, decided_by, decided_at,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  suggestion_id = EXCLUDED.suggestion_id,
                  decision = EXCLUDED.decision,
                  comment = EXCLUDED.comment,
                  edited_title = EXCLUDED.edited_title,
                  edited_scope = EXCLUDED.edited_scope,
                  convert_to_requirement = EXCLUDED.convert_to_requirement,
                  created_requirement_id = EXCLUDED.created_requirement_id,
                  decided_by = EXCLUDED.decided_by,
                  decided_at = EXCLUDED.decided_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    decision["id"],
                    decision["suggestion_id"],
                    decision["decision"],
                    decision.get("comment"),
                    decision.get("edited_title"),
                    decision.get("edited_scope"),
                    decision.get("convert_to_requirement", False),
                    decision.get("created_requirement_id"),
                    decision["decided_by"],
                    decision.get("decided_at"),
                    created_at,
                    updated_at,
                ),
            )
