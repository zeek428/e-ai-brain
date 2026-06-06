from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, store
from app.core.trace import envelope, get_trace_id
from app.services.lifecycle_context import lifecycle_context_response

router = APIRouter(tags=["lifecycle"])


@router.get("/api/lifecycle/context")
def lifecycle_context(
    request: Request,
    subject_type: str | None = None,
    subject_id: str | None = None,
    product_id: str | None = None,
    version_id: str | None = None,
    module_code: str | None = None,
    direction: str = "both",
    include_risks: bool = True,
    user: dict[str, Any] = CurrentUser,
) -> dict[str, Any]:
    return envelope(
        lifecycle_context_response(
            current_store=store(request),
            direction=direction,
            include_risks=include_risks,
            module_code=module_code,
            product_id=product_id,
            subject_id=subject_id,
            subject_type=subject_type,
            user=user,
            version_id=version_id,
        ),
        get_trace_id(request),
    )
