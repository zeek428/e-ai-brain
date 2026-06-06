from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, require_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.code_review_report import code_review_report_for_task
from app.services.task_workflow_context import task_workflow_read_store

router = APIRouter(tags=["code-review-reports"])


@router.get("/api/ai-tasks/{task_id}/code-review-report")
def get_code_review_report(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"reviewer", "rd_owner"})
    current_store = store(request)
    read_store = task_workflow_read_store(current_store)
    report = code_review_report_for_task(read_store, task_id=task_id, user=user)
    return envelope(report, get_trace_id(request))
