from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.services.task_access import can_read_task


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _read_memory_record(
    current_store: Any,
    collection_name: str,
    record_id: Any,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    record = _read_memory_dict(current_store, collection_name).get(str(record_id))
    return record if isinstance(record, dict) else None


def _find_code_review_report_for_task(
    current_store: Any,
    *,
    task: dict[str, Any],
) -> dict[str, Any] | None:
    report_id = task.get("code_review_report_id")
    report = _read_memory_record(current_store, "code_review_reports", report_id)
    if report is not None:
        return report
    task_id = str(task.get("id") or "")
    matches = [
        item
        for item in _read_memory_dict(current_store, "code_review_reports").values()
        if isinstance(item, dict) and str(item.get("task_id") or "") == task_id
    ]
    matches.sort(
        key=lambda item: str(item.get("created_at") or item.get("id") or ""),
        reverse=True,
    )
    return matches[0] if matches else None


def code_review_report_for_task(
    current_store: Any,
    *,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    task = _read_memory_record(current_store, "ai_tasks", task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "AI task not found"},
        )
    if not can_read_task(user, task):
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Insufficient task permission"},
        )
    report = _find_code_review_report_for_task(current_store, task=task)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Code review report not found"},
        )
    return {
        **report,
        "writeback_template": code_review_writeback_template(report, task=task),
    }


def code_review_writeback_template(
    report: dict[str, Any],
    *,
    task: dict[str, Any],
) -> dict[str, Any]:
    risk_level = str(report.get("risk_level") or "-")
    summary = str(report.get("summary") or "-").strip()
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    finding_lines = [_format_finding(index, item) for index, item in enumerate(findings, start=1)]
    if not finding_lines:
        finding_lines = ["- 暂无阻塞性问题。"]
    body = "\n".join(
        [
            "## AI Brain Code Review 结论",
            "",
            f"- 报告 ID：{report.get('id')}",
            f"- 任务 ID：{task.get('id')}",
            f"- 风险等级：{risk_level}",
            f"- 状态：{report.get('status') or '-'}",
            "- 远端回写：未自动回写，请人工确认后粘贴到 PR/MR 评论区。",
            "",
            "### 摘要",
            summary,
            "",
            "### Findings",
            *finding_lines,
            "",
            "> 由 Enterprise AI Brain 生成。请以人工最终确认结论为准。",
        ]
    )
    return {
        "body": body,
        "format": "markdown",
        "title": f"AI Brain Code Review: {risk_level} risk",
        "writeback_allowed": False,
        "writeback_reason": "read_only_review_flow",
    }


def _format_finding(index: int, finding: Any) -> str:
    if not isinstance(finding, dict):
        return f"{index}. {finding}"
    severity = finding.get("severity") or "-"
    summary = finding.get("summary") or finding.get("message") or "-"
    file_path = finding.get("file_path") or finding.get("file") or "-"
    line_number = finding.get("line_number") or finding.get("line") or "-"
    return f"{index}. [{severity}] {file_path}:{line_number} - {summary}"
