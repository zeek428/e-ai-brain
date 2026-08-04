"""Canonical Git branch names for isolated R&D work items."""

from __future__ import annotations

import hashlib
import re

_UNSAFE_REF_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


def _ref_component(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Git branch component is required")
    normalized = _UNSAFE_REF_COMPONENT.sub("-", raw).strip(".-")
    if not normalized:
        normalized = "item"
    if normalized.endswith(".lock"):
        normalized = f"{normalized[:-5].rstrip('.-') or 'item'}-lock"
    if normalized == raw:
        return normalized
    suffix = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{normalized}-{suffix}"


def rd_work_item_branch_name(collaboration_run_id: str, work_item_id: str) -> str:
    """Return the valid, deterministic branch for one frozen work item."""
    return f"rd/{_ref_component(collaboration_run_id)}/{_ref_component(work_item_id)}"
