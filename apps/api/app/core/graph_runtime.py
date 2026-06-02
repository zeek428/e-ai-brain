from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

LANGGRAPH_RUNTIME = "langgraph"
AI_TASK_GRAPH_NODE_PATH = [
    "retrieve_context",
    "generate_task_output",
    "interrupt_for_human_review",
]


class AiTaskGraphState(TypedDict, total=False):
    current_step: str
    node_path: list[str]
    output_kind: str | None
    review_id: str
    runtime: str
    runtime_metadata: dict[str, Any]
    task_id: str
    task_status: str
    task_type: str


def _append_node(
    state: AiTaskGraphState,
    *,
    node_name: str,
    current_step: str,
) -> AiTaskGraphState:
    node_path = list(state.get("node_path", []))
    node_path.append(node_name)
    return {
        "current_step": current_step,
        "node_path": node_path,
        "runtime": LANGGRAPH_RUNTIME,
    }


def _retrieve_context(state: AiTaskGraphState) -> AiTaskGraphState:
    return _append_node(
        state,
        node_name="retrieve_context",
        current_step="retrieve_context",
    )


def _generate_task_output(state: AiTaskGraphState) -> AiTaskGraphState:
    next_state = _append_node(
        state,
        node_name="generate_task_output",
        current_step="generate_task_output",
    )
    next_state["output_kind"] = state.get("output_kind") or state.get("task_type")
    return next_state


def _interrupt_for_human_review(state: AiTaskGraphState) -> AiTaskGraphState:
    next_state = _append_node(
        state,
        node_name="interrupt_for_human_review",
        current_step="interrupt_for_human_review",
    )
    next_state["task_status"] = "waiting_review"
    next_state["runtime_metadata"] = {
        "package": LANGGRAPH_RUNTIME,
        "node_path": next_state["node_path"],
    }
    return next_state


def build_ai_task_graph():
    graph = StateGraph(AiTaskGraphState)
    graph.add_node("retrieve_context", _retrieve_context)
    graph.add_node("generate_task_output", _generate_task_output)
    graph.add_node("interrupt_for_human_review", _interrupt_for_human_review)
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "generate_task_output")
    graph.add_edge("generate_task_output", "interrupt_for_human_review")
    graph.add_edge("interrupt_for_human_review", END)
    return graph.compile()


def run_ai_task_graph(task: dict[str, Any], *, review_id: str) -> AiTaskGraphState:
    graph = build_ai_task_graph()
    result = graph.invoke(
        {
            "current_step": task.get("current_step") or "task_started",
            "node_path": [],
            "output_kind": (task.get("output_json") or {}).get("kind"),
            "review_id": review_id,
            "runtime": LANGGRAPH_RUNTIME,
            "task_id": task["id"],
            "task_status": task["status"],
            "task_type": task["task_type"],
        }
    )
    result["runtime"] = LANGGRAPH_RUNTIME
    result["runtime_metadata"] = {
        "package": LANGGRAPH_RUNTIME,
        "node_path": list(result.get("node_path", [])),
    }
    return result
