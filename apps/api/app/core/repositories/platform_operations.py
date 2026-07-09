from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from typing import Any


def _json(value: Any, default: Any) -> str:
    if value is None:
        value = default
    return json.dumps(value, ensure_ascii=False)


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


class PlatformOperationsRepository:
    def __init__(self, connect: Callable[..., AbstractContextManager[Any]]) -> None:
        self._connect = connect

    def list_system_alert_incidents(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, source, component, title, severity, status, owner, message,
                           action_href, first_seen_at, last_seen_at, acknowledged_at,
                           acknowledged_by, resolved_at, resolved_by, close_reason,
                           postmortem, metadata, created_at, updated_at
                    FROM system_alert_incidents
                    ORDER BY
                      CASE status
                        WHEN 'open' THEN 0
                        WHEN 'acknowledged' THEN 1
                        WHEN 'resolving' THEN 2
                        WHEN 'ignored' THEN 3
                        ELSE 4
                      END,
                      last_seen_at DESC,
                      id ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [self._system_alert_incident_from_row(row) for row in cursor.fetchall()]

    def upsert_system_alert_incidents(
        self,
        alerts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not alerts:
            return self.list_system_alert_incidents(limit=100)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for alert in alerts:
                    cursor.execute(
                        """
                        INSERT INTO system_alert_incidents (
                          id, source, component, title, severity, status, owner,
                          message, action_href, last_seen_at, metadata
                        )
                        VALUES (
                          %s, %s, %s, %s, %s, 'open', %s, %s, %s, now(), %s::jsonb
                        )
                        ON CONFLICT (id) DO UPDATE SET
                          source = EXCLUDED.source,
                          component = EXCLUDED.component,
                          title = EXCLUDED.title,
                          severity = EXCLUDED.severity,
                          owner = COALESCE(system_alert_incidents.owner, EXCLUDED.owner),
                          message = EXCLUDED.message,
                          action_href = EXCLUDED.action_href,
                          last_seen_at = now(),
                          metadata = system_alert_incidents.metadata || EXCLUDED.metadata,
                          updated_at = now()
                        """,
                        (
                            alert["id"],
                            alert.get("source") or "system_check",
                            alert.get("component"),
                            alert.get("title") or alert["id"],
                            alert.get("severity") or "low",
                            alert.get("owner"),
                            alert.get("message"),
                            alert.get("action_href"),
                            _json(alert.get("metadata"), {}),
                        ),
                    )
        return self.list_system_alert_incidents(limit=100)

    def update_system_alert_incident(
        self,
        alert_id: str,
        *,
        close_reason: str | None = None,
        owner: str | None = None,
        postmortem: str | None = None,
        status: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE system_alert_incidents
                    SET
                      status = COALESCE(%s, status),
                      owner = COALESCE(%s, owner),
                      close_reason = COALESCE(%s, close_reason),
                      postmortem = COALESCE(%s, postmortem),
                      acknowledged_at = CASE
                        WHEN %s IN ('acknowledged', 'resolving') AND acknowledged_at IS NULL
                        THEN now()
                        ELSE acknowledged_at
                      END,
                      acknowledged_by = CASE
                        WHEN %s IN ('acknowledged', 'resolving') AND acknowledged_by IS NULL
                        THEN %s
                        ELSE acknowledged_by
                      END,
                      resolved_at = CASE
                        WHEN %s IN ('closed', 'ignored') THEN now()
                        ELSE resolved_at
                      END,
                      resolved_by = CASE
                        WHEN %s IN ('closed', 'ignored') THEN %s
                        ELSE resolved_by
                      END,
                      updated_at = now()
                    WHERE id = %s
                    RETURNING id, source, component, title, severity, status, owner,
                              message, action_href, first_seen_at, last_seen_at,
                              acknowledged_at, acknowledged_by, resolved_at, resolved_by,
                              close_reason, postmortem, metadata, created_at, updated_at
                    """,
                    (
                        status,
                        owner,
                        close_reason,
                        postmortem,
                        status,
                        status,
                        actor_id,
                        status,
                        status,
                        actor_id,
                        alert_id,
                    ),
                )
                row = cursor.fetchone()
        return self._system_alert_incident_from_row(row) if row else None

    def list_system_alert_subscriptions(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, scope, channel, target, severity_min, enabled,
                           created_by, created_at, updated_at
                    FROM system_alert_subscriptions
                    ORDER BY enabled DESC, severity_min DESC, id ASC
                    """
                )
                return [
                    {
                        "id": row[0],
                        "scope": row[1],
                        "channel": row[2],
                        "target": row[3],
                        "severity_min": row[4],
                        "enabled": bool(row[5]),
                        "created_by": row[6],
                        "created_at": _iso(row[7]),
                        "updated_at": _iso(row[8]),
                    }
                    for row in cursor.fetchall()
                ]

    def save_system_alert_subscription(self, subscription: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO system_alert_subscriptions (
                      id, scope, channel, target, severity_min, enabled, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                      scope = EXCLUDED.scope,
                      channel = EXCLUDED.channel,
                      target = EXCLUDED.target,
                      severity_min = EXCLUDED.severity_min,
                      enabled = EXCLUDED.enabled,
                      updated_at = now()
                    RETURNING id, scope, channel, target, severity_min, enabled,
                              created_by, created_at, updated_at
                    """,
                    (
                        subscription["id"],
                        subscription.get("scope") or "global",
                        subscription["channel"],
                        subscription["target"],
                        subscription.get("severity_min") or "medium",
                        bool(subscription.get("enabled", True)),
                        subscription.get("created_by"),
                    ),
                )
                row = cursor.fetchone()
        return {
            "id": row[0],
            "scope": row[1],
            "channel": row[2],
            "target": row[3],
            "severity_min": row[4],
            "enabled": bool(row[5]),
            "created_by": row[6],
            "created_at": _iso(row[7]),
            "updated_at": _iso(row[8]),
        }

    def list_system_alert_rules(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, source, component, severity_min, owner,
                           notification_scope, condition_json, enabled,
                           created_by, updated_by, created_at, updated_at
                    FROM system_alert_rules
                    ORDER BY enabled DESC, source ASC, severity_min DESC, id ASC
                    """
                )
                return [self._system_alert_rule_from_row(row) for row in cursor.fetchall()]

    def save_system_alert_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO system_alert_rules (
                      id, name, source, component, severity_min, owner,
                      notification_scope, condition_json, enabled, created_by, updated_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                      name = EXCLUDED.name,
                      source = EXCLUDED.source,
                      component = EXCLUDED.component,
                      severity_min = EXCLUDED.severity_min,
                      owner = EXCLUDED.owner,
                      notification_scope = EXCLUDED.notification_scope,
                      condition_json = EXCLUDED.condition_json,
                      enabled = EXCLUDED.enabled,
                      updated_by = EXCLUDED.updated_by,
                      updated_at = now()
                    RETURNING id, name, source, component, severity_min, owner,
                              notification_scope, condition_json, enabled,
                              created_by, updated_by, created_at, updated_at
                    """,
                    (
                        rule["id"],
                        rule["name"],
                        rule.get("source") or "system_check",
                        rule.get("component"),
                        rule.get("severity_min") or "medium",
                        rule.get("owner"),
                        rule.get("notification_scope") or "global",
                        _json(rule.get("condition_json"), {}),
                        bool(rule.get("enabled", True)),
                        rule.get("created_by"),
                        rule.get("updated_by") or rule.get("created_by"),
                    ),
                )
                row = cursor.fetchone()
        return self._system_alert_rule_from_row(row)

    def insert_knowledge_quality_event(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO knowledge_quality_events (
                      id, event_type, query, knowledge_space_id, user_id, hit_count,
                      no_result, citation_count, latency_ms, retrieval_modes,
                      feedback_value, feedback_comment, citation_chunk_id,
                      citation_document_id, related_event_id, trace_id, metadata
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                      %s, %s, %s, %s, %s, %s, %s::jsonb
                    )
                    RETURNING id, event_type, query, knowledge_space_id, user_id,
                              hit_count, no_result, citation_count, latency_ms,
                              retrieval_modes, feedback_value, feedback_comment,
                              citation_chunk_id, citation_document_id, related_event_id,
                              trace_id, metadata, created_at
                    """,
                    (
                        event["id"],
                        event["event_type"],
                        event.get("query"),
                        event.get("knowledge_space_id"),
                        event.get("user_id"),
                        _safe_int(event.get("hit_count")),
                        bool(event.get("no_result")),
                        _safe_int(event.get("citation_count")),
                        event.get("latency_ms"),
                        _json(event.get("retrieval_modes"), {}),
                        event.get("feedback_value"),
                        event.get("feedback_comment"),
                        event.get("citation_chunk_id"),
                        event.get("citation_document_id"),
                        event.get("related_event_id"),
                        event.get("trace_id"),
                        _json(event.get("metadata"), {}),
                    ),
                )
                row = cursor.fetchone()
        return self._knowledge_quality_event_from_row(row)

    def list_knowledge_quality_events(
        self,
        *,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        where = "WHERE event_type = %s" if event_type else ""
        params: tuple[Any, ...] = (event_type, limit) if event_type else (limit,)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, event_type, query, knowledge_space_id, user_id, hit_count,
                           no_result, citation_count, latency_ms, retrieval_modes,
                           feedback_value, feedback_comment, citation_chunk_id,
                           citation_document_id, related_event_id, trace_id, metadata,
                           created_at
                    FROM knowledge_quality_events
                    {where}
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    params,
                )
                return [self._knowledge_quality_event_from_row(row) for row in cursor.fetchall()]

    def knowledge_quality_summary(self, *, since_days: int = 30) -> dict[str, Any]:
        since_at = datetime.now(UTC) - timedelta(days=max(1, since_days))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE event_type IN ('search', 'rag')) AS query_count,
                      COUNT(*) FILTER (
                        WHERE event_type IN ('search', 'rag') AND no_result IS TRUE
                      ) AS no_result_count,
                      COALESCE(SUM(citation_count) FILTER (WHERE event_type = 'rag'), 0)
                        AS citation_count,
                      COUNT(*) FILTER (WHERE event_type = 'citation_click') AS citation_click_count,
                      COUNT(*) FILTER (WHERE event_type = 'feedback') AS feedback_count,
                      COUNT(*) FILTER (
                        WHERE event_type = 'feedback' AND feedback_value = 'useful'
                      ) AS useful_feedback_count,
                      COUNT(*) FILTER (
                        WHERE event_type = 'feedback' AND feedback_value IN ('not_useful', 'incorrect')
                      ) AS negative_feedback_count,
                      ROUND(AVG(latency_ms) FILTER (WHERE event_type IN ('search', 'rag')), 2)
                        AS avg_latency_ms
                    FROM knowledge_quality_events
                    WHERE created_at >= %s
                    """,
                    (since_at,),
                )
                row = cursor.fetchone() or (0, 0, 0, 0, 0, 0, 0, None)
        query_count = _safe_int(row[0])
        no_result_count = _safe_int(row[1])
        citation_count = _safe_int(row[2])
        citation_click_count = _safe_int(row[3])
        feedback_count = _safe_int(row[4])
        useful_feedback_count = _safe_int(row[5])
        negative_feedback_count = _safe_int(row[6])
        return {
            "avg_latency_ms": float(row[7]) if row[7] is not None else None,
            "citation_click_count": citation_click_count,
            "citation_click_rate": round(citation_click_count / citation_count, 4)
            if citation_count
            else None,
            "citation_count": citation_count,
            "feedback_count": feedback_count,
            "negative_feedback_count": negative_feedback_count,
            "no_result_count": no_result_count,
            "no_result_rate": round(no_result_count / query_count, 4) if query_count else None,
            "query_count": query_count,
            "rag_citation_accuracy_proxy": round(useful_feedback_count / feedback_count, 4)
            if feedback_count
            else None,
            "since_days": since_days,
            "useful_feedback_count": useful_feedback_count,
        }

    def _system_alert_incident_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "source": row[1],
            "component": row[2],
            "title": row[3],
            "severity": row[4],
            "status": row[5],
            "owner": row[6],
            "message": row[7],
            "action_href": row[8],
            "first_seen_at": _iso(row[9]),
            "last_seen_at": _iso(row[10]),
            "acknowledged_at": _iso(row[11]),
            "acknowledged_by": row[12],
            "resolved_at": _iso(row[13]),
            "resolved_by": row[14],
            "close_reason": row[15],
            "postmortem": row[16],
            "metadata": row[17] if isinstance(row[17], dict) else {},
            "created_at": _iso(row[18]),
            "updated_at": _iso(row[19]),
        }

    def _system_alert_rule_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "name": row[1],
            "source": row[2],
            "component": row[3],
            "severity_min": row[4],
            "owner": row[5],
            "notification_scope": row[6],
            "condition_json": row[7] if isinstance(row[7], dict) else {},
            "enabled": bool(row[8]),
            "created_by": row[9],
            "updated_by": row[10],
            "created_at": _iso(row[11]),
            "updated_at": _iso(row[12]),
        }

    def _knowledge_quality_event_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "event_type": row[1],
            "query": row[2],
            "knowledge_space_id": row[3],
            "user_id": row[4],
            "hit_count": _safe_int(row[5]),
            "no_result": bool(row[6]),
            "citation_count": _safe_int(row[7]),
            "latency_ms": float(row[8]) if row[8] is not None else None,
            "retrieval_modes": row[9] if isinstance(row[9], dict) else {},
            "feedback_value": row[10],
            "feedback_comment": row[11],
            "citation_chunk_id": row[12],
            "citation_document_id": row[13],
            "related_event_id": row[14],
            "trace_id": row[15],
            "metadata": row[16] if isinstance(row[16], dict) else {},
            "created_at": _iso(row[17]),
        }
