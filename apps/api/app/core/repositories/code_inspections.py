from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


def _json(value: Any, default: Any) -> str:
    if value is None:
        value = default
    return json.dumps(value, ensure_ascii=False)


class CodeInspectionReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._upsert_audit_events = upsert_audit_events

    def save_code_inspection_records(
        self,
        *,
        report: dict[str, Any],
        findings: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self.upsert_code_inspection_reports(cursor, {report["id"]: report})
                self.upsert_code_inspection_findings(
                    cursor,
                    {finding["id"]: finding for finding in findings},
                )
                self.upsert_code_inspection_notifications(
                    cursor,
                    {notification["id"]: notification for notification in notifications},
                )
                if audit_event is not None and self._upsert_audit_events is not None:
                    self._upsert_audit_events(cursor, [audit_event])

    def list_code_inspection_reports(
        self,
        *,
        product_id: str | None = None,
        repository_id: str | None = None,
        risk_level: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._where(
            {
                "product_id": product_id,
                "repository_id": repository_id,
                "risk_level": risk_level,
                "status": status,
            }
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, product_id, repository_id, repository, scheduled_job_id,
                           scheduled_job_run_id, collector_run_id, plugin_invocation_log_id,
                           source_system, branch, commit_sha, summary, risk_level,
                           finding_count, severe_finding_count, status, result_actions,
                           created_bug_ids, notification_ids, created_by, created_at, updated_at
                    FROM code_inspection_reports
                    {where}
                    ORDER BY created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._report_from_row(row) for row in cursor.fetchall()]

    def get_code_inspection_detail(self, report_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, product_id, repository_id, repository, scheduled_job_id,
                           scheduled_job_run_id, collector_run_id, plugin_invocation_log_id,
                           source_system, branch, commit_sha, summary, risk_level,
                           finding_count, severe_finding_count, status, result_actions,
                           created_bug_ids, notification_ids, created_by, created_at, updated_at
                    FROM code_inspection_reports
                    WHERE id = %s
                    """,
                    (report_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                report = self._report_from_row(row)
                cursor.execute(
                    """
                    SELECT id, report_id, rule_id, category, severity, title, description,
                           file_path, line_number, recommendation, raw, created_bug_id,
                           created_at, updated_at
                    FROM code_inspection_findings
                    WHERE report_id = %s
                    ORDER BY
                      CASE severity
                        WHEN 'critical' THEN 4
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 1
                        ELSE 0
                      END DESC,
                      file_path ASC,
                      line_number ASC NULLS LAST,
                      id ASC
                    """,
                    (report_id,),
                )
                findings = [self._finding_from_row(row) for row in cursor.fetchall()]
                cursor.execute(
                    """
                    SELECT id, report_id, channel, target, status, message, request_config,
                           response_summary, created_by, created_at, updated_at
                    FROM code_inspection_notifications
                    WHERE report_id = %s
                    ORDER BY created_at ASC, id ASC
                    """,
                    (report_id,),
                )
                notifications = [self._notification_from_row(row) for row in cursor.fetchall()]
        return {"findings": findings, "notifications": notifications, "report": report}

    def upsert_code_inspection_reports(
        self,
        cursor,
        reports: dict[str, dict[str, Any]],
    ) -> None:
        for report in reports.values():
            cursor.execute(
                """
                INSERT INTO code_inspection_reports (
                  id, product_id, repository_id, repository, scheduled_job_id,
                  scheduled_job_run_id, collector_run_id, plugin_invocation_log_id,
                  source_system, branch, commit_sha, summary, risk_level, finding_count,
                  severe_finding_count, status, result_actions, created_bug_ids,
                  notification_ids, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::jsonb, %s,
                  %s, %s, %s,
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  repository_id = EXCLUDED.repository_id,
                  repository = EXCLUDED.repository,
                  scheduled_job_id = EXCLUDED.scheduled_job_id,
                  scheduled_job_run_id = EXCLUDED.scheduled_job_run_id,
                  collector_run_id = EXCLUDED.collector_run_id,
                  plugin_invocation_log_id = EXCLUDED.plugin_invocation_log_id,
                  source_system = EXCLUDED.source_system,
                  branch = EXCLUDED.branch,
                  commit_sha = EXCLUDED.commit_sha,
                  summary = EXCLUDED.summary,
                  risk_level = EXCLUDED.risk_level,
                  finding_count = EXCLUDED.finding_count,
                  severe_finding_count = EXCLUDED.severe_finding_count,
                  status = EXCLUDED.status,
                  result_actions = EXCLUDED.result_actions,
                  created_bug_ids = EXCLUDED.created_bug_ids,
                  notification_ids = EXCLUDED.notification_ids,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    report["id"],
                    report.get("product_id"),
                    report.get("repository_id"),
                    _json(report.get("repository"), {}),
                    report.get("scheduled_job_id"),
                    report.get("scheduled_job_run_id"),
                    report.get("collector_run_id"),
                    report.get("plugin_invocation_log_id"),
                    report.get("source_system"),
                    report.get("branch"),
                    report.get("commit_sha"),
                    report.get("summary") or "",
                    report.get("risk_level", "medium"),
                    report.get("finding_count", 0),
                    report.get("severe_finding_count", 0),
                    report.get("status", "completed"),
                    _json(report.get("result_actions"), []),
                    _json(report.get("created_bug_ids"), []),
                    _json(report.get("notification_ids"), []),
                    report.get("created_by"),
                    report.get("created_at"),
                    report.get("updated_at") or report.get("created_at"),
                ),
            )

    def upsert_code_inspection_findings(
        self,
        cursor,
        findings: dict[str, dict[str, Any]],
    ) -> None:
        for finding in findings.values():
            cursor.execute(
                """
                INSERT INTO code_inspection_findings (
                  id, report_id, rule_id, category, severity, title, description,
                  file_path, line_number, recommendation, raw, created_bug_id,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s::jsonb, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  rule_id = EXCLUDED.rule_id,
                  category = EXCLUDED.category,
                  severity = EXCLUDED.severity,
                  title = EXCLUDED.title,
                  description = EXCLUDED.description,
                  file_path = EXCLUDED.file_path,
                  line_number = EXCLUDED.line_number,
                  recommendation = EXCLUDED.recommendation,
                  raw = EXCLUDED.raw,
                  created_bug_id = EXCLUDED.created_bug_id,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    finding["id"],
                    finding["report_id"],
                    finding.get("rule_id"),
                    finding.get("category", "quality"),
                    finding.get("severity", "medium"),
                    finding["title"],
                    finding.get("description") or "",
                    finding.get("file_path") or "",
                    finding.get("line_number"),
                    finding.get("recommendation") or "",
                    _json(finding.get("raw"), {}),
                    finding.get("created_bug_id"),
                    finding.get("created_at"),
                    finding.get("updated_at") or finding.get("created_at"),
                ),
            )

    def upsert_code_inspection_notifications(
        self,
        cursor,
        notifications: dict[str, dict[str, Any]],
    ) -> None:
        for notification in notifications.values():
            cursor.execute(
                """
                INSERT INTO code_inspection_notifications (
                  id, report_id, channel, target, status, message, request_config,
                  response_summary, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s::jsonb,
                  %s::jsonb, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  channel = EXCLUDED.channel,
                  target = EXCLUDED.target,
                  status = EXCLUDED.status,
                  message = EXCLUDED.message,
                  request_config = EXCLUDED.request_config,
                  response_summary = EXCLUDED.response_summary,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    notification["id"],
                    notification["report_id"],
                    notification["channel"],
                    notification.get("target"),
                    notification.get("status", "recorded"),
                    notification.get("message") or "",
                    _json(notification.get("request_config"), {}),
                    _json(notification.get("response_summary"), {}),
                    notification.get("created_by"),
                    notification.get("created_at"),
                    notification.get("updated_at") or notification.get("created_at"),
                ),
            )

    def _where(self, values: dict[str, Any]) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in values.items():
            if value is None:
                continue
            clauses.append(f"{field} = %s")
            params.append(value)
        return (f"WHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _report_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "product_id": row[1],
            "repository_id": row[2],
            "repository": row[3] or {},
            "scheduled_job_id": row[4],
            "scheduled_job_run_id": row[5],
            "collector_run_id": row[6],
            "plugin_invocation_log_id": row[7],
            "source_system": row[8],
            "branch": row[9],
            "commit_sha": row[10],
            "summary": row[11],
            "risk_level": row[12],
            "finding_count": row[13],
            "severe_finding_count": row[14],
            "status": row[15],
            "result_actions": row[16] or [],
            "created_bug_ids": row[17] or [],
            "notification_ids": row[18] or [],
            "created_by": row[19],
            "created_at": row[20].isoformat() if row[20] else None,
            "updated_at": row[21].isoformat() if row[21] else None,
        }

    def _finding_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "report_id": row[1],
            "rule_id": row[2],
            "category": row[3],
            "severity": row[4],
            "title": row[5],
            "description": row[6],
            "file_path": row[7],
            "line_number": row[8],
            "recommendation": row[9],
            "raw": row[10] or {},
            "created_bug_id": row[11],
            "created_at": row[12].isoformat() if row[12] else None,
            "updated_at": row[13].isoformat() if row[13] else None,
        }

    def _notification_from_row(self, row: Any) -> dict[str, Any]:
        return {
            "id": row[0],
            "report_id": row[1],
            "channel": row[2],
            "target": row[3],
            "status": row[4],
            "message": row[5],
            "request_config": row[6] or {},
            "response_summary": row[7] or {},
            "created_by": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
        }
