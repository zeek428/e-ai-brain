from __future__ import annotations

from typing import Any

from fastapi import HTTPException

BUG_SOURCES = {
    "ai_auto_test",
    "ai_post_release",
    "code_inspection",
    "deployment_failure",
    "manual_test",
}
BUG_SEVERITIES = {"blocker", "critical", "major", "minor"}
BUG_STATUSES = {
    "assigned",
    "closed",
    "fixed",
    "needs_info",
    "open",
    "reopened",
    "triaged",
    "verified",
}
BUG_STATUS_TRANSITIONS = {
    "open": {"triaged", "assigned", "closed"},
    "needs_info": {"open", "triaged", "closed"},
    "triaged": {"assigned", "closed"},
    "assigned": {"fixed", "reopened", "closed"},
    "fixed": {"verified", "reopened"},
    "verified": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"triaged", "assigned", "closed"},
}


def _domain_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


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


def validate_bug_enums(
    *,
    source: str | None = None,
    severity: str | None = None,
    status: str | None = None,
) -> None:
    if source is not None and source not in BUG_SOURCES:
        raise _domain_error(400, "VALIDATION_ERROR", "Unsupported bug source")
    if severity is not None and severity not in BUG_SEVERITIES:
        raise _domain_error(400, "VALIDATION_ERROR", "Unsupported bug severity")
    if status is not None and status not in BUG_STATUSES:
        raise _domain_error(400, "VALIDATION_ERROR", "Unsupported bug status")


def validate_bug_context(
    current_store: Any,
    *,
    product_id: str,
    version_id: str | None = None,
    module_code: str | None = None,
    requirement_id: str | None = None,
    related_task_id: str | None = None,
    duplicate_of_bug_id: str | None = None,
    bug_id: str | None = None,
) -> None:
    if _read_memory_record(current_store, "products", product_id) is None:
        raise _domain_error(404, "NOT_FOUND", "Product not found")
    if version_id is not None:
        version = _read_memory_record(current_store, "product_versions", version_id)
        if version is None or version["product_id"] != product_id:
            raise _domain_error(404, "NOT_FOUND", "Product version not found")
    if module_code is not None and not any(
        module["product_id"] == product_id and module["code"] == module_code
        for module in _read_memory_dict(current_store, "product_modules").values()
    ):
        raise _domain_error(404, "NOT_FOUND", "Product module not found")
    if requirement_id is not None:
        requirement = _read_memory_record(current_store, "requirements", requirement_id)
        if requirement is None or requirement["product_id"] != product_id:
            raise _domain_error(404, "NOT_FOUND", "Requirement not found")
    if related_task_id is not None:
        task = _read_memory_record(current_store, "ai_tasks", related_task_id)
        if task is None or task["product_id"] != product_id:
            raise _domain_error(404, "NOT_FOUND", "AI task not found")
    if duplicate_of_bug_id is not None:
        if duplicate_of_bug_id == bug_id:
            raise _domain_error(400, "VALIDATION_ERROR", "Bug cannot duplicate itself")
        duplicate = _read_memory_record(current_store, "bugs", duplicate_of_bug_id)
        if duplicate is None or duplicate["product_id"] != product_id:
            raise _domain_error(404, "NOT_FOUND", "Duplicate bug not found")


def initial_bug_status(payload: Any) -> str:
    if getattr(payload, "duplicate_of_bug_id", None):
        return "closed"
    if (
        getattr(payload, "source", None) == "ai_auto_test"
        and not getattr(payload, "reproduce_steps", None)
    ):
        return "needs_info"
    return "open"


def ensure_bug_status_transition(current_status: str, next_status: str) -> None:
    if current_status == next_status:
        return
    allowed = BUG_STATUS_TRANSITIONS.get(current_status, set())
    if next_status not in allowed:
        raise _domain_error(409, "BUG_STATE_INVALID", "Bug cannot move to requested status")
