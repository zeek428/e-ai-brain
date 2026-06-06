from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.services.task_access import can_read_task


def code_review_report_for_task(
    current_store: Any,
    *,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    task = current_store.ai_tasks.get(task_id)
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
    report_id = task.get("code_review_report_id")
    if not report_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Code review report not found"},
        )
    report = current_store.code_review_reports.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Code review report not found"},
        )
    return report
