from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any


class GitReviewReadRepository:
    def __init__(
        self,
        connect: Callable[..., AbstractContextManager[Any]],
        *,
        delete_missing: Callable[[Any, str, dict[str, dict[str, Any]]], None] | None = None,
        upsert_audit_events: Callable[[Any, list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._connect = connect
        self._delete_missing = delete_missing
        self._upsert_audit_events = upsert_audit_events

    def load_gitlab_review(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                snapshots = self._load_gitlab_mr_snapshots(cursor)
                reports = self._load_code_review_reports(cursor)
        return {
            "code_review_reports": reports,
            "gitlab_mr_snapshots": snapshots,
        }

    def save_gitlab_review(self, payload: dict[str, Any]) -> None:
        snapshots = payload.get("gitlab_mr_snapshots", {})
        reports = payload.get("code_review_reports", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing_git_review_rows(
                    cursor,
                    snapshots=snapshots,
                    reports=reports,
                )
                self.upsert_gitlab_mr_snapshots(cursor, snapshots)
                self.upsert_code_review_reports(cursor, reports)

    def save_gitlab_review_snapshot_record(
        self,
        *,
        snapshot: dict[str, Any] | None,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if snapshot is not None:
                    self.upsert_gitlab_mr_snapshots(cursor, {snapshot["id"]: snapshot})
                if audit_event is not None:
                    if self._upsert_audit_events is None:
                        raise RuntimeError("Audit upsert callback is not configured")
                    self._upsert_audit_events(cursor, [audit_event])

    def _load_gitlab_mr_snapshots(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, repository_id, product_id, version_id, project_id, project_path,
                   mr_iid, title, author, source_branch, target_branch, base_sha,
                   head_sha, diff_refs, changed_files_summary, diff_storage_ref,
                   diff_size_bytes, diff_limit_bytes, snapshot_hash, requirement_id,
                   technical_solution_task_id, created_by, created_at, updated_at,
                   writeback_allowed
            FROM gitlab_mr_snapshots
            ORDER BY created_at, id
            """
        )
        snapshots = {}
        for row in cursor.fetchall():
            snapshot = {
                "author": dict(row[8] or {}),
                "base_sha": row[11],
                "changed_files_summary": list(row[14] or []),
                "created_at": row[22].isoformat() if row[22] else None,
                "created_by": row[21],
                "diff_limit_bytes": row[17],
                "diff_refs": dict(row[13] or {}),
                "diff_size_bytes": row[16],
                "diff_storage_ref": row[15],
                "head_sha": row[12],
                "id": row[0],
                "mr_iid": row[6],
                "product_id": row[2],
                "project_id": row[4],
                "project_path": row[5],
                "repository_id": row[1],
                "requirement_id": row[19],
                "snapshot_hash": row[18],
                "source_branch": row[9],
                "target_branch": row[10],
                "technical_solution_task_id": row[20],
                "title": row[7],
                "updated_at": row[23].isoformat() if row[23] else None,
                "version_id": row[3],
                "writeback_allowed": row[24],
            }
            for optional_key in (
                "base_sha",
                "created_at",
                "project_id",
                "project_path",
                "updated_at",
                "version_id",
            ):
                if snapshot[optional_key] is None:
                    snapshot.pop(optional_key)
            snapshots[row[0]] = snapshot
        return snapshots

    def _load_code_review_reports(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, task_id, gitlab_mr_snapshot_id, executor, summary, risk_level,
                   findings, status, review_id, archived_at, error_code,
                   gitlab_writeback_performed, created_at, updated_at
            FROM code_review_reports
            ORDER BY created_at, id
            """
        )
        reports = {}
        for row in cursor.fetchall():
            report = {
                "archived_at": row[9].isoformat() if row[9] else None,
                "created_at": row[12].isoformat() if row[12] else None,
                "error_code": row[10],
                "executor": dict(row[3] or {}),
                "findings": list(row[6] or []),
                "gitlab_mr_snapshot_id": row[2],
                "gitlab_writeback_performed": row[11],
                "id": row[0],
                "review_id": row[8],
                "risk_level": row[5],
                "status": row[7],
                "summary": row[4],
                "task_id": row[1],
                "updated_at": row[13].isoformat() if row[13] else None,
            }
            for optional_key in (
                "archived_at",
                "created_at",
                "error_code",
                "review_id",
                "updated_at",
            ):
                if report[optional_key] is None:
                    report.pop(optional_key)
            reports[row[0]] = report
        return reports

    def _delete_missing_git_review_rows(
        self,
        cursor,
        *,
        snapshots: dict[str, dict[str, Any]],
        reports: dict[str, dict[str, Any]],
    ) -> None:
        if self._delete_missing is None:
            raise RuntimeError("Git review delete callback is not configured")
        self._delete_missing(cursor, "code_review_reports", reports)
        self._delete_missing(cursor, "gitlab_mr_snapshots", snapshots)

    def upsert_gitlab_mr_snapshots(
        self,
        cursor,
        snapshots: dict[str, dict[str, Any]],
    ) -> None:
        for snapshot in snapshots.values():
            created_at = snapshot.get("created_at")
            updated_at = snapshot.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO gitlab_mr_snapshots (
                  id, repository_id, product_id, version_id, project_id, project_path,
                  mr_iid, title, author, source_branch, target_branch, base_sha, head_sha,
                  diff_refs, changed_files_summary, diff_storage_ref, diff_size_bytes,
                  diff_limit_bytes, snapshot_hash, requirement_id, technical_solution_task_id,
                  created_by, created_at, updated_at, writeback_allowed
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                  %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  repository_id = EXCLUDED.repository_id,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  project_id = EXCLUDED.project_id,
                  project_path = EXCLUDED.project_path,
                  mr_iid = EXCLUDED.mr_iid,
                  title = EXCLUDED.title,
                  author = EXCLUDED.author,
                  source_branch = EXCLUDED.source_branch,
                  target_branch = EXCLUDED.target_branch,
                  base_sha = EXCLUDED.base_sha,
                  head_sha = EXCLUDED.head_sha,
                  diff_refs = EXCLUDED.diff_refs,
                  changed_files_summary = EXCLUDED.changed_files_summary,
                  diff_storage_ref = EXCLUDED.diff_storage_ref,
                  diff_size_bytes = EXCLUDED.diff_size_bytes,
                  diff_limit_bytes = EXCLUDED.diff_limit_bytes,
                  snapshot_hash = EXCLUDED.snapshot_hash,
                  requirement_id = EXCLUDED.requirement_id,
                  technical_solution_task_id = EXCLUDED.technical_solution_task_id,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at,
                  writeback_allowed = EXCLUDED.writeback_allowed
                """,
                (
                    snapshot["id"],
                    snapshot["repository_id"],
                    snapshot["product_id"],
                    snapshot.get("version_id"),
                    snapshot.get("project_id"),
                    snapshot.get("project_path"),
                    snapshot["mr_iid"],
                    snapshot["title"],
                    json.dumps(snapshot.get("author"), ensure_ascii=False),
                    snapshot["source_branch"],
                    snapshot["target_branch"],
                    snapshot.get("base_sha"),
                    snapshot["head_sha"],
                    json.dumps(snapshot.get("diff_refs"), ensure_ascii=False),
                    json.dumps(snapshot.get("changed_files_summary", []), ensure_ascii=False),
                    snapshot["diff_storage_ref"],
                    snapshot.get("diff_size_bytes", 0),
                    snapshot.get("diff_limit_bytes", 0),
                    snapshot["snapshot_hash"],
                    snapshot["requirement_id"],
                    snapshot["technical_solution_task_id"],
                    snapshot["created_by"],
                    created_at,
                    updated_at,
                    snapshot.get("writeback_allowed", False),
                ),
            )

    def upsert_code_review_reports(
        self,
        cursor,
        reports: dict[str, dict[str, Any]],
    ) -> None:
        for report in reports.values():
            created_at = report.get("created_at")
            updated_at = report.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO code_review_reports (
                  id, task_id, gitlab_mr_snapshot_id, executor, summary, risk_level,
                  findings, status, review_id, archived_at, error_code,
                  gitlab_writeback_performed, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s,
                  %s::timestamptz, %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  task_id = EXCLUDED.task_id,
                  gitlab_mr_snapshot_id = EXCLUDED.gitlab_mr_snapshot_id,
                  executor = EXCLUDED.executor,
                  summary = EXCLUDED.summary,
                  risk_level = EXCLUDED.risk_level,
                  findings = EXCLUDED.findings,
                  status = EXCLUDED.status,
                  review_id = EXCLUDED.review_id,
                  archived_at = EXCLUDED.archived_at,
                  error_code = EXCLUDED.error_code,
                  gitlab_writeback_performed = EXCLUDED.gitlab_writeback_performed,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    report["id"],
                    report["task_id"],
                    report["gitlab_mr_snapshot_id"],
                    json.dumps(report.get("executor", {}), ensure_ascii=False),
                    report["summary"],
                    report["risk_level"],
                    json.dumps(report.get("findings", []), ensure_ascii=False),
                    report.get("status", "draft"),
                    report.get("review_id"),
                    report.get("archived_at"),
                    report.get("error_code"),
                    report.get("gitlab_writeback_performed", False),
                    created_at,
                    updated_at,
                ),
            )
