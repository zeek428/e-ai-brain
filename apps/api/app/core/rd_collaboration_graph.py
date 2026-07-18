"""The durable execution cursor for an R&D collaboration run.

The graph has no business-side write nodes.  Its sole job is to retain which
already-committed collaboration events have been observed by the scheduler.
That separation makes a failed checkpoint write safe to retry.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

RD_COLLABORATION_GRAPH_DEFINITION = "rd_collaboration"
RD_COLLABORATION_GRAPH_VERSION = "v1"


def rd_collaboration_thread_id(collaboration_run_id: str) -> str:
    run_id = str(collaboration_run_id).strip()
    if not run_id:
        raise ValueError("collaboration_run_id is required")
    return f"rd_collaboration_run:{run_id}"


def _merge_event_ids(current: list[str] | None, update: list[str] | None) -> list[str]:
    merged = list(current or [])
    for event_id in update or []:
        if event_id not in merged:
            merged.append(event_id)
    return merged


class RdCollaborationGraphState(TypedDict, total=False):
    collaboration_run_id: str
    current_step: str
    domain_status: str
    domain_version: int
    event_id: str | None
    graph_definition: str
    graph_version: str
    processed_event_ids: Annotated[list[str], _merge_event_ids]


def _read_domain_state(state: RdCollaborationGraphState) -> RdCollaborationGraphState:
    return {
        "collaboration_run_id": str(state["collaboration_run_id"]),
        "current_step": "read_domain_state",
        "graph_definition": RD_COLLABORATION_GRAPH_DEFINITION,
        "graph_version": RD_COLLABORATION_GRAPH_VERSION,
    }


def _record_committed_event(state: RdCollaborationGraphState) -> RdCollaborationGraphState:
    event_id = str(state.get("event_id") or "").strip()
    if not event_id or event_id in (state.get("processed_event_ids") or []):
        return {"current_step": "wait_work_item_events"}
    return {
        "current_step": "wait_work_item_events",
        "processed_event_ids": [event_id],
    }


def _wait_work_item_events(_: RdCollaborationGraphState) -> RdCollaborationGraphState:
    return {"current_step": "wait_work_item_events"}


def build_rd_collaboration_graph(checkpointer: Any):
    graph = StateGraph(RdCollaborationGraphState)
    graph.add_node("read_domain_state", _read_domain_state)
    graph.add_node("record_committed_event", _record_committed_event)
    graph.add_node("wait_work_item_events", _wait_work_item_events)
    graph.add_edge(START, "read_domain_state")
    graph.add_edge("read_domain_state", "record_committed_event")
    graph.add_edge("record_committed_event", "wait_work_item_events")
    graph.add_edge("wait_work_item_events", END)
    return graph.compile(checkpointer=checkpointer)
