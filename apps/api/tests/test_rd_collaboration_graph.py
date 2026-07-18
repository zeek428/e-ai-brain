from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from app.core.store import MemoryStore


def _test_settings() -> SimpleNamespace:
    return SimpleNamespace(is_test_env=True, persistence_mode="memory", database_url="")


def _config(collaboration_run_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": f"rd_collaboration_run:{collaboration_run_id}"}}


def test_collaboration_graph_resumes_from_persisted_checkpoint() -> None:
    from app.core.graph_checkpointer import build_checkpointer
    from app.core.rd_collaboration_graph import build_rd_collaboration_graph

    graph = build_rd_collaboration_graph(build_checkpointer(_test_settings()))
    config = _config("run-1")

    first = graph.invoke(
        {
            "collaboration_run_id": "run-1",
            "current_step": "start",
            "processed_event_ids": [],
        },
        config=config,
    )
    resumed = graph.invoke({"event_id": "event-1"}, config=config)

    assert first["current_step"] == "wait_work_item_events"
    assert resumed["current_step"] == "wait_work_item_events"
    assert resumed["processed_event_ids"] == ["event-1"]


def test_domain_commit_survives_checkpoint_failure_without_duplicate_side_effects() -> None:
    from app.core.graph_checkpointer import build_checkpointer
    from app.services.rd_collaboration_graph_runtime import RdCollaborationGraphRuntime

    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "strategy_snapshot_id": "snapshot-1",
        "status": "running",
    }
    runtime = RdCollaborationGraphRuntime(
        store,
        checkpointer=build_checkpointer(_test_settings()),
    )

    runtime.fail_next_checkpoint_write()
    first = runtime.handle_event(
        collaboration_run_id="run-1",
        event_id="event-1",
        event_type="work_item.completed",
    )
    replay = runtime.handle_event(
        collaboration_run_id="run-1",
        event_id="event-1",
        event_type="work_item.completed",
    )

    assert first["checkpoint_status"] == "failed"
    assert replay["checkpoint_status"] == "persisted"
    assert runtime.domain_transition_count("event-1") == 1
    assert runtime.outbox_count("event-1") == 0
    assert runtime.role_feedback_count(source_event_id="event-1") == 1


def test_incompatible_checkpoint_fails_closed_to_human_takeover() -> None:
    from app.core.graph_checkpointer import build_checkpointer
    from app.services.rd_collaboration_graph_runtime import RdCollaborationGraphRuntime

    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "strategy_snapshot_id": "snapshot-1",
        "status": "running",
    }
    runtime = RdCollaborationGraphRuntime(
        store,
        checkpointer=build_checkpointer(_test_settings()),
    )
    runtime.write_incompatible_checkpoint_for_test("run-1")

    result = runtime.handle_event(
        collaboration_run_id="run-1",
        event_id="event-1",
        event_type="work_item.completed",
    )

    assert result["checkpoint_status"] == "incompatible"
    assert result["human_takeover_required"] is True
    assert store.rd_collaboration_runs["run-1"]["status"] == "waiting_human"
    decision = store.decision_requests["graph-takeover:run-1"]
    assert decision["decision_type"] == "graph_checkpoint_incompatible"
    assert decision["status"] == "pending"


def test_concurrent_event_replay_keeps_one_domain_transition() -> None:
    from app.core.graph_checkpointer import build_checkpointer
    from app.services.rd_collaboration_graph_runtime import RdCollaborationGraphRuntime

    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "strategy_snapshot_id": "snapshot-1",
        "status": "running",
    }
    runtime = RdCollaborationGraphRuntime(
        store,
        checkpointer=build_checkpointer(_test_settings()),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: runtime.handle_event(
                    collaboration_run_id="run-1",
                    event_id="event-1",
                    event_type="work_item.completed",
                ),
                range(2),
            )
        )

    assert {result["checkpoint_status"] for result in results} == {"persisted"}
    assert runtime.domain_transition_count("event-1") == 1
    assert runtime.outbox_count("event-1") == 0
    assert runtime.role_feedback_count(source_event_id="event-1") == 1


def test_graph_projection_scans_past_settled_events_before_applying_limit() -> None:
    """A full earlier page must not starve a newer uncheckpointed scheduler fact."""
    from app.core.graph_checkpointer import build_checkpointer
    from app.services.rd_collaboration_graph_event_projection import (
        process_rd_collaboration_graph_events,
    )
    from app.services.rd_collaboration_graph_runtime import RdCollaborationGraphRuntime

    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "strategy_snapshot_id": "snapshot-1",
        "status": "running",
    }
    for number in range(101):
        event_id = f"scheduler-{number:03d}"
        store.rd_collaboration_events[event_id] = {
            "id": event_id,
            "collaboration_run_id": "run-1",
            "event_type": "work_item.completed",
            "event_key": f"scheduler:{event_id}",
            "subject_type": "rd_work_item",
            "subject_id": f"work-item-{number:03d}",
            "payload_json": {},
            "occurred_at": f"2026-07-18T00:00:{number:03d}+00:00",
        }
    runtime = RdCollaborationGraphRuntime(
        store,
        checkpointer=build_checkpointer(_test_settings()),
    )
    runtime.graph.invoke(
        {
            "collaboration_run_id": "run-1",
            "processed_event_ids": [
                f"event-projection:scheduler-{number:03d}" for number in range(100)
            ],
        },
        config=_config("run-1"),
    )

    persisted = process_rd_collaboration_graph_events(store, limit=100, runtime=runtime)

    assert persisted == 1
    assert runtime.is_event_checkpointed(
        collaboration_run_id="run-1",
        event_id="event-projection:scheduler-100",
    )


def test_graph_event_commit_does_not_enqueue_unsupported_execution_outbox_event() -> None:
    from app.core.graph_checkpointer import build_checkpointer
    from app.services.rd_collaboration_graph_runtime import RdCollaborationGraphRuntime

    store = MemoryStore()
    store.rd_collaboration_runs["run-1"] = {
        "id": "run-1",
        "brain_app_id": "rd_brain",
        "product_id": "product-1",
        "strategy_snapshot_id": "snapshot-1",
        "status": "running",
    }
    runtime = RdCollaborationGraphRuntime(
        store,
        checkpointer=build_checkpointer(_test_settings()),
    )

    result = runtime.handle_event(
        collaboration_run_id="run-1",
        event_id="event-1",
        event_type="work_item.completed",
    )

    assert result["checkpoint_status"] == "persisted"
    assert runtime.outbox_count("event-1") == 0
    assert store.execution_outbox_events == {}
