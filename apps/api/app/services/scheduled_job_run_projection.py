from __future__ import annotations

from typing import Any

from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)


def _trace_graph_needs_debug_projection(trace_graph: Any) -> bool:
    if not isinstance(trace_graph, dict):
        return True
    nodes = trace_graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return True
    for node in nodes:
        if not isinstance(node, dict):
            return True
        if (
            "stage" not in node
            or "debug_actions" not in node
            or "rerun_hint" not in node
            or "rerun_plan" not in node
            or "snapshot_status" not in node
        ):
            return True
        rerun_plan = node.get("rerun_plan")
        if (
            not isinstance(rerun_plan, dict)
            or rerun_plan.get("plan_version") != "trace_node_rerun_v2"
        ):
            return True
    return False


def scheduled_job_run_source_summary(
    source_run: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if source_run is None:
        return None
    return {
        "error_code": source_run.get("error_code"),
        "finished_at": source_run.get("finished_at"),
        "id": source_run["id"],
        "latency_ms": source_run.get("latency_ms"),
        "records_imported": source_run.get("records_imported", 0),
        "started_at": source_run.get("started_at"),
        "status": source_run.get("status"),
        "trigger_type": source_run.get("trigger_type"),
    }


def public_scheduled_job_run_projection(
    run: dict[str, Any],
    *,
    source_run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    public_run = dict(run)
    result_summary = dict(public_run.get("result_summary") or {})
    if _trace_graph_needs_debug_projection(result_summary.get("trace_graph")):
        trace_graph = JobExecutionEngine.trace_graph_for_run(public_run)
        if trace_graph is not None:
            result_summary["trace_graph"] = trace_graph
            public_run["result_summary"] = result_summary
    if run.get("source_run_id"):
        public_run["source_run_summary"] = scheduled_job_run_source_summary(source_run)
    return public_run
