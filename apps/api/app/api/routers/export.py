from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.api.deps import CurrentUser, store
from app.core.trace import get_trace_id
from app.services.markdown_export import render_task_markdown, require_markdown_export_task
from app.services.task_workflow_context import task_workflow_read_store

router = APIRouter(tags=["export"])


@router.get("/api/export/tasks/{task_id}/markdown")
def export_task_markdown(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> PlainTextResponse:
    current_store = store(request)
    read_store = task_workflow_read_store(current_store)
    task = require_markdown_export_task(user, read_store.ai_tasks.get(task_id))

    trace_id = get_trace_id(request)
    return PlainTextResponse(
        render_task_markdown(read_store, task),
        media_type="text/markdown",
        headers={"X-Trace-Id": trace_id},
    )
