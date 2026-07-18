"""Canonical product-scope checks for R&D collaboration aggregates."""

from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services.product_scope import require_product_scope


def _get(store: Any, collection: str, record_id: str, method: str) -> dict[str, Any] | None:
    repository = getattr(store, "repository", None)
    getter = getattr(repository, method, None)
    if callable(getter):
        row = getter(record_id)
        return dict(row) if row is not None else None
    values = getattr(store, collection, {})
    return dict(values[record_id]) if isinstance(values, dict) and record_id in values else None


def _require(user: dict[str, Any], product_id: Any) -> None:
    require_product_scope(
        user,
        product_id,
        code="FORBIDDEN",
        message="Collaboration aggregate is outside the current product scope",
        status_code=403,
    )


def require_version_scope(store: Any, user: dict[str, Any], version_id: str) -> dict[str, Any]:
    version = _get(store, "product_versions", version_id, "get_product_version")
    if version is None:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    _require(user, version.get("product_id"))
    return version


def require_run_scope(store: Any, user: dict[str, Any], run_id: str) -> dict[str, Any]:
    run = _get(store, "rd_collaboration_runs", run_id, "get_rd_collaboration_run")
    if run is None:
        raise api_error(404, "NOT_FOUND", "Collaboration run not found")
    _require(user, run.get("product_id"))
    return run


def require_work_item_scope(store: Any, user: dict[str, Any], work_item_id: str) -> dict[str, Any]:
    item = _get(store, "rd_work_items", work_item_id, "get_rd_work_item")
    if item is None:
        raise api_error(404, "NOT_FOUND", "Work item not found")
    require_run_scope(store, user, str(item["collaboration_run_id"]))
    return item


def require_decision_scope(
    store: Any,
    user: dict[str, Any],
    decision_request_id: str,
) -> dict[str, Any]:
    decision = _get(store, "decision_requests", decision_request_id, "get_decision_request")
    if decision is None:
        raise api_error(404, "NOT_FOUND", "Decision request not found")
    _require(user, decision.get("product_id"))
    return decision


def require_scope_change_scope(
    store: Any, user: dict[str, Any], scope_change_request_id: str
) -> dict[str, Any]:
    request = _get(
        store,
        "rd_scope_change_requests",
        scope_change_request_id,
        "get_rd_scope_change_request",
    )
    if request is None:
        raise api_error(404, "NOT_FOUND", "Scope change request not found")
    require_version_scope(store, user, str(request["product_version_id"]))
    return request


def require_requirement_scope(
    store: Any,
    user: dict[str, Any],
    requirement_id: str,
) -> dict[str, Any]:
    requirement = _get(store, "requirements", requirement_id, "get_requirement")
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    _require(user, requirement.get("product_id"))
    return requirement
