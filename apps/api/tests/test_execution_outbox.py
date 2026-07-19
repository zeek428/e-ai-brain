from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.core.config import Settings
from app.core.store import MemoryStore

COMPOSE = Path("../../docker-compose.yml")


def test_execution_worker_is_not_embedded_in_api_by_default(monkeypatch):
    monkeypatch.delenv("EXECUTION_WORKER_EMBEDDED_ENABLED", raising=False)

    assert Settings().execution_worker_embedded_enabled is False

    monkeypatch.setenv("EXECUTION_WORKER_EMBEDDED_ENABLED", "true")

    assert Settings().execution_worker_embedded_enabled is True


def test_execution_worker_iteration_processes_outbox_and_jenkins_sync(monkeypatch):
    from app.workers import execution_worker

    calls: list[tuple[str, str]] = []
    store = object()
    monkeypatch.setattr(
        execution_worker,
        "process_external_event_inbox_events",
        lambda current_store, *, worker_id: calls.append(("external", worker_id)) or 4,
    )
    monkeypatch.setattr(
        execution_worker,
        "process_execution_outbox_events",
        lambda current_store, *, worker_id: calls.append(("outbox", worker_id)) or 2,
    )
    monkeypatch.setattr(
        execution_worker,
        "process_rd_collaboration_graph_events",
        lambda current_store, *, runtime=None: (
            calls.append(("collaboration_graph", "execution-worker-test")) or 5
        ),
    )
    monkeypatch.setattr(
        execution_worker,
        "plan_pending_collaboration_runs",
        lambda current_store, *, planner=None: calls.append(
            ("collaboration_plan", "execution-worker-test")
        )
        or {"planned_run_ids": ["run-1"], "skipped_run_ids": []},
    )
    monkeypatch.setattr(
        execution_worker,
        "dispatch_ready_ai_work_items",
        lambda current_store: calls.append(("collaboration_dispatch", "execution-worker-test"))
        or {
            "dispatched_work_item_ids": ["work-1"],
            "human_review_required_work_item_ids": [],
            "skipped_work_item_ids": [],
        },
        raising=False,
    )
    monkeypatch.setattr(
        execution_worker,
        "sync_due_jenkins_deployments",
        lambda current_store, *, worker_id: calls.append(("jenkins", worker_id)) or 3,
    )

    result = execution_worker.run_execution_worker_iteration(
        store,
        worker_id="execution-worker-test",
    )

    assert result == {
        "external_event_count": 4,
        "jenkins_sync_count": 3,
        "outbox_count": 2,
        "rd_collaboration_auto_dispatch_count": 1,
        "rd_collaboration_graph_event_count": 5,
        "rd_collaboration_plan_count": 1,
        "reconciliation_count": 0,
    }
    assert calls == [
        ("outbox", "execution-worker-test"),
        ("external", "execution-worker-test"),
        ("collaboration_graph", "execution-worker-test"),
        ("collaboration_plan", "execution-worker-test"),
        ("collaboration_dispatch", "execution-worker-test"),
        ("jenkins", "execution-worker-test"),
    ]


def test_compose_runs_execution_worker_separately_from_api():
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "execution-worker:" in compose
    assert 'EXECUTION_WORKER_EMBEDDED_ENABLED: "false"' in compose
    assert 'command: ["python", "-m", "app.workers"]' in compose


def test_only_memory_runtime_processes_execution_outbox_inline():
    from app.services.operational_deployments import (
        _should_process_execution_outbox_inline,
    )

    assert _should_process_execution_outbox_inline(MemoryStore()) is True
    assert _should_process_execution_outbox_inline(SimpleNamespace(repository=object())) is False
