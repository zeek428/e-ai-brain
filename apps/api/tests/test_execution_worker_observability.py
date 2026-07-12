from app.core.store import MemoryStore
from app.services.execution_worker_observability import execution_operations_overview
from app.workers.execution_worker import run_execution_worker_iteration


def test_worker_iteration_records_heartbeat(monkeypatch) -> None:
    store = MemoryStore()
    monkeypatch.setattr(
        "app.workers.execution_worker.process_execution_outbox_events", lambda *_args, **_kwargs: 2
    )
    monkeypatch.setattr(
        "app.workers.execution_worker.process_external_event_inbox_events",
        lambda *_args, **_kwargs: 1,
    )
    monkeypatch.setattr(
        "app.workers.execution_worker.sync_due_jenkins_deployments", lambda *_args, **_kwargs: 3
    )

    counts = run_execution_worker_iteration(store, worker_id="worker_001")

    assert counts["outbox_count"] == 2
    assert store.execution_worker_heartbeats["worker_001"]["claimed_count"] == 6
    assert execution_operations_overview(store)["workers"][0]["worker_id"] == "worker_001"


def test_worker_overview_includes_operational_backlog_and_reconciliation() -> None:
    store = MemoryStore()
    store.execution_outbox_events = {
        "outbox_001": {
            "id": "outbox_001",
            "status": "pending",
            "attempt_count": 2,
            "created_at": "2026-07-11T00:00:00+00:00",
            "updated_at": "2026-07-11T00:01:00+00:00",
        },
        "outbox_002": {
            "id": "outbox_002",
            "status": "dead_letter",
            "attempt_count": 5,
            "created_at": "2026-07-11T00:00:00+00:00",
            "updated_at": "2026-07-11T00:01:00+00:00",
        },
        "outbox_003": {
            "id": "outbox_003",
            "status": "processing",
            "attempt_count": 1,
            "lease_until": "2026-07-11T00:00:01+00:00",
            "created_at": "2026-07-11T00:00:00+00:00",
            "updated_at": "2026-07-11T00:01:00+00:00",
        },
    }
    store.external_operations = {
        "operation_001": {
            "id": "operation_001",
            "status": "manual_reconciliation",
            "provider": "jenkins",
            "operation_type": "deployment_dispatch_requested",
            "updated_at": "2026-07-11T00:00:00+00:00",
        }
    }

    overview = execution_operations_overview(store)

    assert overview["backlog"]["pending_count"] == 2
    assert overview["backlog"]["dead_letter_count"] == 1
    assert overview["backlog"]["expired_lease_count"] == 1
    assert overview["reconciliation"]["manual_count"] == 1
    assert overview["reconciliation"]["items"][0]["provider"] == "jenkins"
