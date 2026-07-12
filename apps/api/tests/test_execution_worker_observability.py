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
