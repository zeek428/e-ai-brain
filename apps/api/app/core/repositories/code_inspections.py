from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

CODE_INSPECTION_REPORT_SELECT = """
id, product_id, repository_id, repository, scheduled_job_id,
scheduled_job_run_id, collector_run_id, plugin_invocation_log_id,
plugin_action_id, plugin_connection_id, source_system, branch,
commit_sha, summary, risk_level, scan_mode, scanner_name,
is_full_scan, files_scanned, lines_scanned, rules_loaded,
coverage_warning, artifact_ref, checkout_path,
checkout_path_retained, remote_url_hash, remote_url_summary,
scan_started_at, scan_finished_at, scanner_version, rules_version,
suppressed_finding_count, suppression_summary, quality_gate,
scan_profile, previous_report_id, previous_comparison,
finding_count, severe_finding_count, status, result_actions,
created_bug_ids, notification_ids, created_task_ids,
committer_count, committer_summary, created_by, created_at, updated_at
"""

CODE_INSPECTION_REPORT_SORT_COLUMNS = {
    "created_at": "created_at",
    "committer_count": "committer_count",
    "finding_count": "finding_count",
    "id": "id",
    "risk_level": "risk_level",
    "severe_finding_count": "severe_finding_count",
    "status": "status",
    "updated_at": "updated_at",
}


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
                    SELECT {CODE_INSPECTION_REPORT_SELECT}
                    FROM code_inspection_reports
                    {where}
                    ORDER BY created_at DESC, id DESC
                    """,
                    tuple(params),
                )
                return [self._report_from_row(row) for row in cursor.fetchall()]

    def count_code_inspection_reports(
        self,
        *,
        committer: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        repository_id: str | None = None,
        risk_level: str | None = None,
        status: str | None = None,
        title: str | None = None,
    ) -> int:
        where, params = self._report_where(
            {
                "product_id": product_id,
                "repository_id": repository_id,
                "risk_level": risk_level,
                "status": status,
            },
            committer=committer,
            product_scope_ids=product_scope_ids,
            title=title,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM code_inspection_reports {where}",
                    tuple(params),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0

    def list_code_inspection_reports_page(
        self,
        *,
        committer: str | None = None,
        limit: int,
        offset: int,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        repository_id: str | None = None,
        risk_level: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
        title: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = self._report_where(
            {
                "product_id": product_id,
                "repository_id": repository_id,
                "risk_level": risk_level,
                "status": status,
            },
            committer=committer,
            product_scope_ids=product_scope_ids,
            title=title,
        )
        sort_column = CODE_INSPECTION_REPORT_SORT_COLUMNS.get(sort_by, "created_at")
        direction = "ASC" if sort_order == "asc" else "DESC"
        nulls = "NULLS FIRST" if direction == "ASC" else "NULLS LAST"
        params.extend([limit, offset])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {CODE_INSPECTION_REPORT_SELECT}
                    FROM code_inspection_reports
                    {where}
                    ORDER BY {sort_column} {direction} {nulls}, id {direction}
                    LIMIT %s OFFSET %s
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
                           plugin_action_id, plugin_connection_id, source_system, branch,
                           commit_sha, summary, risk_level, scan_mode, scanner_name,
                           is_full_scan, files_scanned, lines_scanned, rules_loaded,
                           coverage_warning, artifact_ref, checkout_path,
                           checkout_path_retained, remote_url_hash, remote_url_summary,
                           scan_started_at, scan_finished_at, scanner_version, rules_version,
                           suppressed_finding_count, suppression_summary, quality_gate,
                           scan_profile, previous_report_id, previous_comparison,
                           finding_count, severe_finding_count, status, result_actions,
                           created_bug_ids, notification_ids, created_task_ids,
                           committer_count, committer_summary, created_by, created_at, updated_at
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
                           file_path, line_number, recommendation, raw, committer_name,
                           committer_email, committer_username, created_bug_id,
                           created_task_id, suppression_status, suppression_reason,
                           suppression_note, suppression_requested_by,
                           suppression_requested_at, suppression_reviewed_by,
                           suppression_reviewed_at, created_at, updated_at
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
                  plugin_action_id, plugin_connection_id, source_system, branch,
                  commit_sha, summary, risk_level, scan_mode, scanner_name,
                  is_full_scan, files_scanned, lines_scanned, rules_loaded,
                  coverage_warning, artifact_ref, checkout_path, checkout_path_retained,
                  remote_url_hash, remote_url_summary, scan_started_at, scan_finished_at,
                  scanner_version, rules_version, suppressed_finding_count, suppression_summary,
                  quality_gate, scan_profile, previous_report_id, previous_comparison,
                  finding_count, severe_finding_count, status,
                  result_actions, created_bug_ids, notification_ids, created_task_ids,
                  committer_count, committer_summary, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::jsonb, %s,
                  %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                  %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb,
                  %s, %s, %s, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s::jsonb, %s, %s::jsonb, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  repository_id = EXCLUDED.repository_id,
                  repository = EXCLUDED.repository,
                  scheduled_job_id = EXCLUDED.scheduled_job_id,
                  scheduled_job_run_id = EXCLUDED.scheduled_job_run_id,
                  collector_run_id = EXCLUDED.collector_run_id,
                  plugin_invocation_log_id = EXCLUDED.plugin_invocation_log_id,
                  plugin_action_id = EXCLUDED.plugin_action_id,
                  plugin_connection_id = EXCLUDED.plugin_connection_id,
                  source_system = EXCLUDED.source_system,
                  branch = EXCLUDED.branch,
                  commit_sha = EXCLUDED.commit_sha,
                  summary = EXCLUDED.summary,
                  risk_level = EXCLUDED.risk_level,
                  scan_mode = EXCLUDED.scan_mode,
                  scanner_name = EXCLUDED.scanner_name,
                  is_full_scan = EXCLUDED.is_full_scan,
                  files_scanned = EXCLUDED.files_scanned,
                  lines_scanned = EXCLUDED.lines_scanned,
                  rules_loaded = EXCLUDED.rules_loaded,
                  coverage_warning = EXCLUDED.coverage_warning,
                  artifact_ref = EXCLUDED.artifact_ref,
                  checkout_path = EXCLUDED.checkout_path,
                  checkout_path_retained = EXCLUDED.checkout_path_retained,
                  remote_url_hash = EXCLUDED.remote_url_hash,
                  remote_url_summary = EXCLUDED.remote_url_summary,
                  scan_started_at = EXCLUDED.scan_started_at,
                  scan_finished_at = EXCLUDED.scan_finished_at,
                  scanner_version = EXCLUDED.scanner_version,
                  rules_version = EXCLUDED.rules_version,
                  suppressed_finding_count = EXCLUDED.suppressed_finding_count,
                  suppression_summary = EXCLUDED.suppression_summary,
                  quality_gate = EXCLUDED.quality_gate,
                  scan_profile = EXCLUDED.scan_profile,
                  previous_report_id = EXCLUDED.previous_report_id,
                  previous_comparison = EXCLUDED.previous_comparison,
                  finding_count = EXCLUDED.finding_count,
                  severe_finding_count = EXCLUDED.severe_finding_count,
                  status = EXCLUDED.status,
                  result_actions = EXCLUDED.result_actions,
                  created_bug_ids = EXCLUDED.created_bug_ids,
                  notification_ids = EXCLUDED.notification_ids,
                  created_task_ids = EXCLUDED.created_task_ids,
                  committer_count = EXCLUDED.committer_count,
                  committer_summary = EXCLUDED.committer_summary,
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
                    report.get("plugin_action_id"),
                    report.get("plugin_connection_id"),
                    report.get("source_system"),
                    report.get("branch"),
                    report.get("commit_sha"),
                    report.get("summary") or "",
                    report.get("risk_level", "medium"),
                    report.get("scan_mode"),
                    report.get("scanner_name"),
                    bool(report.get("is_full_scan")),
                    report.get("files_scanned", 0),
                    report.get("lines_scanned", 0),
                    _json(report.get("rules_loaded"), []),
                    report.get("coverage_warning"),
                    report.get("artifact_ref"),
                    report.get("checkout_path"),
                    bool(report.get("checkout_path_retained")),
                    report.get("remote_url_hash"),
                    report.get("remote_url_summary"),
                    report.get("scan_started_at"),
                    report.get("scan_finished_at"),
                    report.get("scanner_version"),
                    report.get("rules_version"),
                    report.get("suppressed_finding_count", 0),
                    _json(report.get("suppression_summary"), {}),
                    _json(report.get("quality_gate"), {}),
                    _json(report.get("scan_profile"), {}),
                    report.get("previous_report_id"),
                    _json(report.get("previous_comparison"), {}),
                    report.get("finding_count", 0),
                    report.get("severe_finding_count", 0),
                    report.get("status", "completed"),
                    _json(report.get("result_actions"), []),
                    _json(report.get("created_bug_ids"), []),
                    _json(report.get("notification_ids"), []),
                    _json(report.get("created_task_ids"), []),
                    report.get("committer_count", 0),
                    _json(report.get("committer_summary"), []),
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
                  file_path, line_number, recommendation, raw, committer_name,
                  committer_email, committer_username, created_bug_id,
                  created_task_id, suppression_status, suppression_reason,
                  suppression_note, suppression_requested_by, suppression_requested_at,
                  suppression_reviewed_by, suppression_reviewed_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s::jsonb, %s,
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s::timestamptz, %s,
                  %s::timestamptz, COALESCE(%s::timestamptz, now()),
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
                  committer_name = EXCLUDED.committer_name,
                  committer_email = EXCLUDED.committer_email,
                  committer_username = EXCLUDED.committer_username,
                  created_bug_id = EXCLUDED.created_bug_id,
                  created_task_id = EXCLUDED.created_task_id,
                  suppression_status = EXCLUDED.suppression_status,
                  suppression_reason = EXCLUDED.suppression_reason,
                  suppression_note = EXCLUDED.suppression_note,
                  suppression_requested_by = EXCLUDED.suppression_requested_by,
                  suppression_requested_at = EXCLUDED.suppression_requested_at,
                  suppression_reviewed_by = EXCLUDED.suppression_reviewed_by,
                  suppression_reviewed_at = EXCLUDED.suppression_reviewed_at,
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
                    finding.get("committer_name"),
                    finding.get("committer_email"),
                    finding.get("committer_username"),
                    finding.get("created_bug_id"),
                    finding.get("created_task_id"),
                    finding.get("suppression_status") or "none",
                    finding.get("suppression_reason"),
                    finding.get("suppression_note"),
                    finding.get("suppression_requested_by"),
                    finding.get("suppression_requested_at"),
                    finding.get("suppression_reviewed_by"),
                    finding.get("suppression_reviewed_at"),
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

    def _report_where(
        self,
        values: dict[str, Any],
        *,
        committer: str | None,
        product_scope_ids: list[str] | None,
        title: str | None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        for field, value in values.items():
            if value is None:
                continue
            clauses.append(f"{field} = %s")
            params.append(value)
        if product_scope_ids is not None:
            if product_scope_ids:
                clauses.append("product_id = ANY(%s)")
                params.append(product_scope_ids)
            else:
                clauses.append("FALSE")
        normalized_title = str(title or "").strip().lower()
        if normalized_title:
            probe = f"%{normalized_title}%"
            clauses.append(
                "(lower(id) LIKE %s OR lower(summary) LIKE %s OR lower(repository_id) LIKE %s)"
            )
            params.extend([probe, probe, probe])
        normalized_committer = str(committer or "").strip().lower()
        if normalized_committer:
            clauses.append("lower(committer_summary::text) LIKE %s")
            params.append(f"%{normalized_committer}%")
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
            "plugin_action_id": row[8],
            "plugin_connection_id": row[9],
            "source_system": row[10],
            "branch": row[11],
            "commit_sha": row[12],
            "summary": row[13],
            "risk_level": row[14],
            "scan_mode": row[15],
            "scanner_name": row[16],
            "is_full_scan": bool(row[17]),
            "files_scanned": row[18] or 0,
            "lines_scanned": row[19] or 0,
            "rules_loaded": row[20] or [],
            "coverage_warning": row[21],
            "artifact_ref": row[22],
            "checkout_path": row[23],
            "checkout_path_retained": bool(row[24]),
            "remote_url_hash": row[25],
            "remote_url_summary": row[26],
            "scan_started_at": row[27].isoformat() if row[27] else None,
            "scan_finished_at": row[28].isoformat() if row[28] else None,
            "scanner_version": row[29],
            "rules_version": row[30],
            "suppressed_finding_count": row[31] or 0,
            "suppression_summary": row[32] or {},
            "quality_gate": row[33] or {},
            "scan_profile": row[34] or {},
            "previous_report_id": row[35],
            "previous_comparison": row[36] or {},
            "finding_count": row[37],
            "severe_finding_count": row[38],
            "status": row[39],
            "result_actions": row[40] or [],
            "created_bug_ids": row[41] or [],
            "notification_ids": row[42] or [],
            "created_task_ids": row[43] or [],
            "committer_count": row[44] or 0,
            "committer_summary": row[45] or [],
            "created_by": row[46],
            "created_at": row[47].isoformat() if row[47] else None,
            "updated_at": row[48].isoformat() if row[48] else None,
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
            "committer_name": row[11],
            "committer_email": row[12],
            "committer_username": row[13],
            "created_bug_id": row[14],
            "created_task_id": row[15],
            "suppression_status": row[16] or "none",
            "suppression_reason": row[17],
            "suppression_note": row[18],
            "suppression_requested_by": row[19],
            "suppression_requested_at": row[20].isoformat() if row[20] else None,
            "suppression_reviewed_by": row[21],
            "suppression_reviewed_at": row[22].isoformat() if row[22] else None,
            "created_at": row[23].isoformat() if row[23] else None,
            "updated_at": row[24].isoformat() if row[24] else None,
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
