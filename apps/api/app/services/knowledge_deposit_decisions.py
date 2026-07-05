from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.knowledge_deposits import (
    create_knowledge_document_result,
    get_knowledge_deposit,
    record_audit_event,
    save_knowledge_deposit_records,
)


def approve_knowledge_deposit_result(
    *,
    current_store: Any,
    deposit_id: str,
    folder_id: str | None,
    knowledge_space_id: str,
    permission_roles: list[str],
    title: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    deposit = get_knowledge_deposit(current_store, deposit_id)
    if deposit is None:
        raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
    if deposit["status"] != "pending":
        raise api_error(409, "KNOWLEDGE_DEPOSIT_STATE_INVALID", "Deposit is not pending")
    now = datetime.now(UTC).isoformat()
    document = create_knowledge_document_result(
        content=deposit["content"],
        current_store=current_store,
        doc_type="task_deposit",
        folder_id=folder_id,
        knowledge_space_id=knowledge_space_id,
        permission_roles=permission_roles,
        product_id=None,
        tags=["task_deposit"],
        title=title or deposit["title"],
        user=user,
    )
    deposit = {
        **deposit,
        "status": "approved",
        "knowledge_document_id": document["id"],
        "knowledge_space_id": knowledge_space_id,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="knowledge_deposit.approved",
        actor_id=user["id"],
        subject_id=deposit_id,
    )
    save_knowledge_deposit_records(
        current_store,
        deposit=deposit,
        audit_event=audit_event,
    )
    return deposit


def reject_knowledge_deposit_result(
    *,
    current_store: Any,
    deposit_id: str,
    reason: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    deposit = get_knowledge_deposit(current_store, deposit_id)
    if deposit is None:
        raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
    if deposit["status"] != "pending":
        raise api_error(409, "KNOWLEDGE_DEPOSIT_STATE_INVALID", "Deposit is not pending")
    deposit = {
        **deposit,
        "status": "rejected",
        "rejection_reason": reason,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    audit_event = record_audit_event(
        current_store,
        event_type="knowledge_deposit.rejected",
        actor_id=user["id"],
        subject_id=deposit_id,
    )
    save_knowledge_deposit_records(
        current_store,
        deposit=deposit,
        audit_event=audit_event,
    )
    return deposit
