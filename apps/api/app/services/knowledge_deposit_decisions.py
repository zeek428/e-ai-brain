from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.knowledge_deposits import (
    apply_knowledge_document_to_memory,
    ensure_roles,
    get_knowledge_deposit,
    record_audit_event,
    replace_knowledge_chunks_result,
    save_knowledge_deposit_records,
    uses_repository_context,
)


def approve_knowledge_deposit_result(
    *,
    current_store: Any,
    deposit_id: str,
    permission_roles: list[str],
    title: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    deposit = get_knowledge_deposit(current_store, deposit_id)
    if deposit is None:
        raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
    if deposit["status"] != "pending":
        raise api_error(409, "KNOWLEDGE_DEPOSIT_STATE_INVALID", "Deposit is not pending")
    ensure_roles(permission_roles)

    document_id = current_store.new_id("knowledge")
    now = datetime.now(UTC).isoformat()
    document = {
        "id": document_id,
        "title": title or deposit["title"],
        "content": deposit["content"],
        "doc_type": "task_deposit",
        "permission_roles": permission_roles,
        "tags": ["task_deposit"],
        "index_status": "pending_index",
        "index_error": None,
        "vector_index_error": None,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    model_log_start_index = len(current_store.model_gateway_logs)
    document, chunks = replace_knowledge_chunks_result(current_store, document)
    deposit = {
        **deposit,
        "status": "approved",
        "knowledge_document_id": document_id,
        "updated_at": now,
    }
    if not uses_repository_context(current_store):
        apply_knowledge_document_to_memory(current_store, document, chunks)
        current_store.knowledge_deposits[deposit_id] = deposit
    audit_event = record_audit_event(
        current_store,
        event_type="knowledge_deposit.approved",
        actor_id=user["id"],
        subject_id=deposit_id,
    )
    save_knowledge_deposit_records(
        current_store,
        deposit=deposit,
        document=document,
        chunks=chunks,
        audit_event=audit_event,
        model_logs=current_store.model_gateway_logs[model_log_start_index:],
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
    if not uses_repository_context(current_store):
        current_store.knowledge_deposits[deposit_id] = deposit
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
