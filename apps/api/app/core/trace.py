from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request


def new_trace_id() -> str:
    return f"trace_{uuid4().hex}"


def get_trace_id(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if trace_id is None:
        trace_id = new_trace_id()
        request.state.trace_id = trace_id
    return trace_id


def envelope(data: Any, trace_id: str) -> dict[str, Any]:
    return {"data": data, "trace_id": trace_id}
