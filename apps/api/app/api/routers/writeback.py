from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, require_roles, store
from app.core.trace import envelope, get_trace_id
from app.services.mock_writeback import create_mock_writeback_result, read_mock_writeback_result
from app.services.task_workflow_context import task_workflow_read_store, task_workflow_write_store

router = APIRouter(tags=["writeback"])


@router.get("/api/writeback/results/{task_id}")
def get_writeback_results(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    read_store = task_workflow_read_store(store(request))
    result = read_mock_writeback_result(read_store, task_id)
    return envelope(result, get_trace_id(request))


@router.post("/api/writeback/results/{task_id}")
def create_writeback_results(
    task_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    current_store = task_workflow_write_store(store(request))
    result = create_mock_writeback_result(current_store, task_id=task_id, actor_id=user["id"])
    return envelope(result, get_trace_id(request))
