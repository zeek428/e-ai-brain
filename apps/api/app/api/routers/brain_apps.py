from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, api_error, store
from app.core.trace import envelope, get_trace_id
from app.services.brain_apps import brain_app_rows, find_brain_app

router = APIRouter(prefix="/api/brain-apps", tags=["brain_apps"])


@router.get("")
def list_brain_apps(
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    items = sorted(brain_app_rows(current_store).values(), key=lambda item: item["code"])
    return envelope({"items": items, "total": len(items)}, get_trace_id(request))


@router.get("/{brain_app_id}")
def get_brain_app(
    brain_app_id: str,
    request: Request,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    current_store = store(request)
    brain_app = find_brain_app(brain_app_rows(current_store), brain_app_id)
    if brain_app is None:
        raise api_error(404, "NOT_FOUND", "Brain app not found")
    return envelope(brain_app, get_trace_id(request))
