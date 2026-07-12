from app.core.store import MemoryStore
from app.services.external_operation_reconciliation import (
    reconcile_external_operations,
    record_external_operation,
)


def test_unknown_external_operation_is_reconciled_without_redispatch() -> None:
    store = MemoryStore()
    operation = record_external_operation(
        store,
        idempotency_key="git:merge:001",
        operation_type="git_merge",
        product_id="product_001",
        provider="gitlab",
        status="unknown",
    )

    outcomes = reconcile_external_operations(
        store,
        provider_lookup=lambda item: {"provider_status": "succeeded", "receipt": "mr:42"},
    )

    assert outcomes == [{"id": operation["id"], "status": "succeeded"}]
    assert store.external_operations[operation["id"]]["dispatch_count"] == 1
