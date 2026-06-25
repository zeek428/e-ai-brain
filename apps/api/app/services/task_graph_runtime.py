from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.graph_runtime import run_ai_task_graph


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def latest_graph_run(current_store: Any, task: dict[str, Any]) -> dict[str, Any] | None:
    graph_run_ids = task.get("graph_run_ids", [])
    if not graph_run_ids:
        return None
    return current_store.graph_runs.get(graph_run_ids[-1])


def write_graph_checkpoint(
    current_store: Any,
    *,
    graph_run: dict[str, Any],
    task: dict[str, Any],
    current_step: str,
    state_snapshot: dict[str, Any],
) -> dict[str, Any]:
    snapshot = current_store.snapshot(state_snapshot)
    if graph_run.get("runtime") and "graph_runtime" not in snapshot:
        snapshot["graph_runtime"] = {
            "package": graph_run["runtime"],
            "node_path": current_store.snapshot(graph_run.get("node_path", [])),
        }
    checkpoint_id = current_store.new_id("checkpoint")
    checkpoint = {
        "id": checkpoint_id,
        "graph_run_id": graph_run["id"],
        "ai_task_id": task["id"],
        "current_step": current_step,
        "state_snapshot": current_store.snapshot(snapshot),
        "created_at": datetime.now(UTC).isoformat(),
    }
    if not uses_repository_context(current_store):
        _memory_dict(current_store, "graph_checkpoints")[checkpoint_id] = checkpoint
    graph_run["checkpoint_id"] = checkpoint_id
    graph_run["current_step"] = current_step
    graph_run["state_snapshot"] = current_store.snapshot(snapshot)
    task["current_step"] = current_step
    task["checkpoint_id"] = checkpoint_id
    return checkpoint


def transition_latest_graph_run(
    current_store: Any,
    *,
    task: dict[str, Any],
    status: str,
    current_step: str,
    state_snapshot: dict[str, Any],
) -> dict[str, Any] | None:
    graph_run = latest_graph_run(current_store, task)
    if graph_run is None:
        task["current_step"] = current_step
        return None
    graph_run["status"] = status
    if status in {"completed", "failed", "cancelled"}:
        graph_run["completed_at"] = datetime.now(UTC).isoformat()
    return write_graph_checkpoint(
        current_store,
        graph_run=graph_run,
        task=task,
        current_step=current_step,
        state_snapshot=state_snapshot,
    )


def start_graph_run(
    current_store: Any,
    *,
    task: dict[str, Any],
    review_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    graph_run_id = current_store.new_id("graph_run")
    graph_state = run_ai_task_graph(task, review_id=review_id)
    graph_run = {
        "id": graph_run_id,
        "ai_task_id": task["id"],
        "task_type": task["task_type"],
        "status": "interrupted",
        "runtime": graph_state["runtime"],
        "node_path": current_store.snapshot(graph_state.get("node_path", [])),
        "current_step": graph_state["current_step"],
        "checkpoint_id": None,
        "state_snapshot": {},
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": None,
    }
    if not uses_repository_context(current_store):
        _memory_dict(current_store, "graph_runs")[graph_run_id] = graph_run
    task.setdefault("graph_run_ids", []).append(graph_run_id)
    checkpoint = write_graph_checkpoint(
        current_store,
        graph_run=graph_run,
        task=task,
        current_step=graph_state["current_step"],
        state_snapshot={
            "task_status": graph_state["task_status"],
            "task_type": task["task_type"],
            "review_id": review_id,
            "output_kind": graph_state.get("output_kind"),
            "graph_runtime": graph_state["runtime_metadata"],
        },
    )
    return graph_run, checkpoint


def graph_runs_for_task(current_store: Any, task_id: str) -> list[dict[str, Any]]:
    runs = [
        run
        for run in current_store.graph_runs.values()
        if run["ai_task_id"] == task_id
    ]
    runs.sort(key=lambda run: run["started_at"])
    return runs
