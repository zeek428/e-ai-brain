from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_datetime_timestamp,
    list_text_matches,
    paginated_list_payload,
    sort_list_items,
)
from app.core.trace import envelope

EXECUTION_TRACE_SORT_FIELDS = {
    "duration_ms",
    "failed_node_count",
    "id",
    "node_count",
    "root_type",
    "started_at",
    "status",
    "updated_at",
}

EXECUTION_TRACE_SOURCE_TYPES = {
    "ai_executor_task",
    "audit_event",
    "code_inspection_report",
    "model_gateway_log",
    "plugin_invocation_log",
    "scheduled_job_run",
}

EXECUTION_TRACE_STATUSES = {
    "cancelled",
    "failed",
    "partial",
    "queued",
    "running",
    "skipped",
    "succeeded",
    "unknown",
}

FAILED_STATUSES = {"cancelled", "failed"}
RUNNING_STATUSES = {"pending", "queued", "running"}
SENSITIVE_KEYWORDS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
)


def parse_trace_datetime(value: str, field_name: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"Invalid {field_name}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def _trace_snapshot_repository(current_store: Any) -> Any | None:
    repository = _repository(current_store)
    required_methods = (
        "count_execution_trace_snapshots",
        "get_execution_trace_snapshot",
        "list_execution_trace_snapshots",
        "refresh_execution_trace_snapshots",
    )
    if repository and all(
        callable(getattr(repository, method, None)) for method in required_methods
    ):
        return repository
    return None


def _refresh_trace_snapshots(current_store: Any) -> Any | None:
    repository = _trace_snapshot_repository(current_store)
    if repository is None:
        return None
    traces = ExecutionTraceBuilder(current_store).traces()
    repository.refresh_execution_trace_snapshots(traces)
    return repository


def _repository_list(current_store: Any, method_name: str, fallback: Any) -> list[dict[str, Any]]:
    repository = _repository(current_store)
    method = getattr(repository, method_name, None)
    if callable(method):
        return list(method())
    if isinstance(fallback, dict):
        return list(fallback.values())
    return list(fallback or [])


def _records(current_store: Any) -> dict[str, list[dict[str, Any]]]:
    return {
        "audit_events": _repository_list(
            current_store,
            "list_audit_events",
            getattr(current_store, "audit_events", []),
        ),
        "code_inspection_reports": _repository_list(
            current_store,
            "list_code_inspection_reports",
            getattr(current_store, "code_inspection_reports", {}),
        ),
        "model_gateway_logs": _repository_list(
            current_store,
            "list_model_gateway_logs",
            getattr(current_store, "model_gateway_logs", []),
        ),
        "plugin_invocation_logs": _repository_list(
            current_store,
            "list_plugin_invocation_logs",
            getattr(current_store, "plugin_invocation_logs", {}),
        ),
        "ai_executor_tasks": _repository_list(
            current_store,
            "list_ai_executor_tasks",
            getattr(current_store, "ai_executor_tasks", {}),
        ),
        "scheduled_job_runs": _repository_list(
            current_store,
            "list_scheduled_job_runs",
            getattr(current_store, "scheduled_job_runs", {}),
        ),
    }


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "<truncated>"
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(keyword in normalized_key for keyword in SENSITIVE_KEYWORDS):
                sanitized[str(key)] = "<redacted>"
            else:
                sanitized[str(key)] = _sanitize(item, depth=depth + 1)
        return sanitized
    if isinstance(value, list):
        if len(value) > 50:
            return [_sanitize(item, depth=depth + 1) for item in value[:50]] + ["<truncated>"]
        return [_sanitize(item, depth=depth + 1) for item in value]
    if isinstance(value, str) and len(value) > 2000:
        return f"{value[:2000]}..."
    return value


def _id_set(*values: Any) -> set[str]:
    result: set[str] = set()
    for value in values:
        if isinstance(value, (list, tuple, set)):
            result.update(_id_set(*value))
        elif value is not None and str(value).strip():
            result.add(str(value))
    return result


def _collect_ids(value: Any, suffixes: tuple[str, ...]) -> set[str]:
    ids: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(normalized_key.endswith(suffix) for suffix in suffixes):
                ids.update(_id_set(item))
            ids.update(_collect_ids(item, suffixes))
    elif isinstance(value, list):
        for item in value:
            ids.update(_collect_ids(item, suffixes))
    return ids


def _duration_ms(started_at: Any, finished_at: Any) -> int | None:
    if not started_at or not finished_at:
        return None
    try:
        started = parse_trace_datetime(str(started_at), "started_at")
        finished = parse_trace_datetime(str(finished_at), "finished_at")
    except Exception:
        return None
    return max(0, int((finished - started).total_seconds() * 1000))


def _status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"success", "succeeded", "completed", "healthy", "recorded"}:
        return "succeeded"
    if normalized in {"failure", "failed", "error"}:
        return "failed"
    if normalized in {"cancelled", "canceled"}:
        return "cancelled"
    if normalized in RUNNING_STATUSES:
        return normalized
    if normalized in {"skipped"}:
        return "skipped"
    return normalized or "unknown"


def _merge_status(statuses: list[str]) -> str:
    normalized = [_status(status) for status in statuses if status]
    if any(status in FAILED_STATUSES for status in normalized):
        return "failed"
    if any(status in RUNNING_STATUSES for status in normalized):
        return "running"
    if normalized and all(status == "succeeded" for status in normalized):
        return "succeeded"
    if normalized:
        return normalized[0]
    return "unknown"


def _node(
    *,
    duration_ms: int | None = None,
    error_code: Any = None,
    error_message: Any = None,
    finished_at: Any = None,
    label: str,
    metadata: dict[str, Any] | None = None,
    source_id: str,
    source_type: str,
    started_at: Any = None,
    status: Any = None,
    summary: Any = None,
) -> dict[str, Any]:
    return {
        "duration_ms": duration_ms,
        "error_code": str(error_code) if error_code else None,
        "error_message": str(error_message) if error_message else None,
        "finished_at": str(finished_at) if finished_at else None,
        "id": f"{source_type}:{source_id}",
        "label": label,
        "metadata": _sanitize(metadata or {}),
        "source_id": source_id,
        "source_type": source_type,
        "started_at": str(started_at) if started_at else None,
        "status": _status(status),
        "summary": str(summary) if summary else "",
    }


def _edge(source: str, target: str, label: str = "") -> dict[str, str]:
    return {"from": source, "label": label, "to": target}


def _indexed(records: list[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        value = record.get(field)
        if value is None:
            continue
        result.setdefault(str(value), []).append(record)
    return result


def _by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record["id"]): record for record in records if record.get("id")}


class ExecutionTraceBuilder:
    def __init__(self, current_store: Any) -> None:
        self.records = _records(current_store)
        self.runs = self.records["scheduled_job_runs"]
        self.plugins = self.records["plugin_invocation_logs"]
        self.tasks = self.records["ai_executor_tasks"]
        self.model_logs = self.records["model_gateway_logs"]
        self.audit_events = self.records["audit_events"]
        self.reports = self.records["code_inspection_reports"]
        self.plugins_by_id = _by_id(self.plugins)
        self.plugins_by_run = _indexed(self.plugins, "scheduled_job_run_id")
        self.tasks_by_id = _by_id(self.tasks)
        self.tasks_by_run = _indexed(self.tasks, "scheduled_job_run_id")
        self.tasks_by_plugin = _indexed(self.tasks, "plugin_invocation_log_id")
        self.model_logs_by_id = _by_id(self.model_logs)
        self.model_logs_by_ai_task = _indexed(self.model_logs, "ai_task_id")
        self.reports_by_run = _indexed(self.reports, "scheduled_job_run_id")
        self.reports_by_plugin = _indexed(self.reports, "plugin_invocation_log_id")
        self.audit_by_subject_id = _indexed(self.audit_events, "subject_id")
        self.audit_by_ai_task = _indexed(self.audit_events, "ai_task_id")

    def traces(self) -> list[dict[str, Any]]:
        traces: list[dict[str, Any]] = []
        consumed = {
            "audit_event": set(),
            "ai_executor_task": set(),
            "code_inspection_report": set(),
            "model_gateway_log": set(),
            "plugin_invocation_log": set(),
            "scheduled_job_run": set(),
        }
        for run in self.runs:
            trace = self.trace_for_run(run)
            traces.append(trace)
            for source_type, ids in trace["related_ids"].items():
                consumed.setdefault(source_type, set()).update(ids)

        for plugin in self.plugins:
            plugin_id = str(plugin.get("id") or "")
            if plugin_id and plugin_id not in consumed["plugin_invocation_log"]:
                trace = self.trace_for_plugin(plugin)
                traces.append(trace)
                for source_type, ids in trace["related_ids"].items():
                    consumed.setdefault(source_type, set()).update(ids)

        for task in self.tasks:
            task_id = str(task.get("id") or "")
            if task_id and task_id not in consumed["ai_executor_task"]:
                trace = self.trace_for_task(task)
                traces.append(trace)
                for source_type, ids in trace["related_ids"].items():
                    consumed.setdefault(source_type, set()).update(ids)

        for report in self.reports:
            report_id = str(report.get("id") or "")
            if report_id and report_id not in consumed["code_inspection_report"]:
                traces.append(self.trace_for_report(report))

        for model_log in self.model_logs:
            log_id = str(model_log.get("id") or "")
            if log_id and log_id not in consumed["model_gateway_log"]:
                traces.append(self.trace_for_model_log(model_log))

        for audit_event in self.audit_events:
            event_id = str(audit_event.get("id") or "")
            if event_id and event_id not in consumed["audit_event"]:
                traces.append(self.trace_for_audit_event(audit_event))

        return traces

    def trace_for_run(self, run: dict[str, Any]) -> dict[str, Any]:
        run_id = str(run["id"])
        nodes = [self.run_node(run)]
        edges: list[dict[str, str]] = []
        related = self._empty_related()
        related["scheduled_job_run"].add(run_id)

        stage_nodes, stage_edges = self.stage_nodes(run)
        if stage_nodes:
            edges.append(_edge(nodes[0]["id"], stage_nodes[0]["id"], "contains"))
        nodes.extend(stage_nodes)
        edges.extend(stage_edges)

        plugin_ids = _id_set(run.get("plugin_invocation_log_id"))
        plugin_ids.update(
            _collect_ids(run.get("result_summary") or {}, ("plugin_invocation_log_id",))
        )
        plugins = list(self.plugins_by_run.get(run_id, []))
        plugins.extend(
            self.plugins_by_id[plugin_id]
            for plugin_id in plugin_ids
            if plugin_id in self.plugins_by_id
        )
        for plugin in _unique_records(plugins):
            nodes.append(self.plugin_node(plugin))
            edges.append(
                _edge(
                    f"scheduled_job_run:{run_id}",
                    f"plugin_invocation_log:{plugin['id']}",
                    "invokes",
                )
            )
            related["plugin_invocation_log"].add(str(plugin["id"]))

        tasks = list(self.tasks_by_run.get(run_id, []))
        for plugin in plugins:
            tasks.extend(self.tasks_by_plugin.get(str(plugin.get("id")), []))
        for task in _unique_records(tasks):
            nodes.append(self.task_node(task))
            source = (
                f"plugin_invocation_log:{task['plugin_invocation_log_id']}"
                if task.get("plugin_invocation_log_id")
                else f"scheduled_job_run:{run_id}"
            )
            edges.append(_edge(source, f"ai_executor_task:{task['id']}", "dispatches"))
            related["ai_executor_task"].add(str(task["id"]))

        model_log_ids = _collect_ids(
            run.get("result_summary") or {}, ("model_log_id", "model_gateway_log_id")
        )
        for task in tasks:
            model_log_ids.update(_collect_ids(task, ("model_log_id", "model_gateway_log_id")))
            model_log_ids.update(
                str(log.get("id"))
                for log in self.model_logs_by_ai_task.get(str(task.get("ai_task_id")), [])
            )
        for log_id in model_log_ids:
            model_log = self.model_logs_by_id.get(log_id)
            if model_log is None:
                continue
            nodes.append(self.model_log_node(model_log))
            edges.append(
                _edge(f"scheduled_job_run:{run_id}", f"model_gateway_log:{log_id}", "calls_model")
            )
            related["model_gateway_log"].add(log_id)

        reports = list(self.reports_by_run.get(run_id, []))
        for plugin in plugins:
            reports.extend(self.reports_by_plugin.get(str(plugin.get("id")), []))
        for report in _unique_records(reports):
            nodes.append(self.report_node(report))
            edges.append(
                _edge(
                    f"scheduled_job_run:{run_id}",
                    f"code_inspection_report:{report['id']}",
                    "writes_report",
                )
            )
            related["code_inspection_report"].add(str(report["id"]))

        self._attach_audit(
            nodes, edges, related, run_id, root_node_id=f"scheduled_job_run:{run_id}"
        )
        return self._trace_payload(
            nodes=nodes,
            edges=edges,
            related=related,
            root=run,
            root_type="scheduled_job_run",
            title=f"定时作业运行 {run_id}",
        )

    def trace_for_plugin(self, plugin: dict[str, Any]) -> dict[str, Any]:
        plugin_id = str(plugin["id"])
        nodes = [self.plugin_node(plugin)]
        edges: list[dict[str, str]] = []
        related = self._empty_related()
        related["plugin_invocation_log"].add(plugin_id)
        for task in self.tasks_by_plugin.get(plugin_id, []):
            nodes.append(self.task_node(task))
            edges.append(
                _edge(
                    f"plugin_invocation_log:{plugin_id}",
                    f"ai_executor_task:{task['id']}",
                    "dispatches",
                )
            )
            related["ai_executor_task"].add(str(task["id"]))
        for report in self.reports_by_plugin.get(plugin_id, []):
            nodes.append(self.report_node(report))
            edges.append(
                _edge(
                    f"plugin_invocation_log:{plugin_id}",
                    f"code_inspection_report:{report['id']}",
                    "writes_report",
                )
            )
            related["code_inspection_report"].add(str(report["id"]))
        self._attach_audit(
            nodes, edges, related, plugin_id, root_node_id=f"plugin_invocation_log:{plugin_id}"
        )
        return self._trace_payload(
            nodes=nodes,
            edges=edges,
            related=related,
            root=plugin,
            root_type="plugin_invocation_log",
            title=f"插件调用 {plugin_id}",
        )

    def trace_for_task(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = str(task["id"])
        nodes = [self.task_node(task)]
        edges: list[dict[str, str]] = []
        related = self._empty_related()
        related["ai_executor_task"].add(task_id)
        for model_log in self.model_logs_by_ai_task.get(str(task.get("ai_task_id")), []):
            nodes.append(self.model_log_node(model_log))
            edges.append(
                _edge(
                    f"ai_executor_task:{task_id}",
                    f"model_gateway_log:{model_log['id']}",
                    "calls_model",
                )
            )
            related["model_gateway_log"].add(str(model_log["id"]))
        self._attach_audit(
            nodes, edges, related, task_id, root_node_id=f"ai_executor_task:{task_id}"
        )
        return self._trace_payload(
            nodes=nodes,
            edges=edges,
            related=related,
            root=task,
            root_type="ai_executor_task",
            title=f"执行器任务 {task_id}",
        )

    def trace_for_report(self, report: dict[str, Any]) -> dict[str, Any]:
        report_id = str(report["id"])
        nodes = [self.report_node(report)]
        edges: list[dict[str, str]] = []
        related = self._empty_related()
        related["code_inspection_report"].add(report_id)
        self._attach_audit(
            nodes, edges, related, report_id, root_node_id=f"code_inspection_report:{report_id}"
        )
        return self._trace_payload(
            nodes=nodes,
            edges=edges,
            related=related,
            root=report,
            root_type="code_inspection_report",
            title=f"代码巡检报告 {report_id}",
        )

    def trace_for_model_log(self, model_log: dict[str, Any]) -> dict[str, Any]:
        log_id = str(model_log["id"])
        nodes = [self.model_log_node(model_log)]
        related = self._empty_related()
        related["model_gateway_log"].add(log_id)
        return self._trace_payload(
            nodes=nodes,
            edges=[],
            related=related,
            root=model_log,
            root_type="model_gateway_log",
            title=f"模型调用 {log_id}",
        )

    def trace_for_audit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event_id = str(event["id"])
        nodes = [self.audit_node(event)]
        related = self._empty_related()
        related["audit_event"].add(event_id)
        return self._trace_payload(
            nodes=nodes,
            edges=[],
            related=related,
            root=event,
            root_type="audit_event",
            title=f"审计事件 {event.get('event_type') or event_id}",
        )

    def run_node(self, run: dict[str, Any]) -> dict[str, Any]:
        return _node(
            duration_ms=run.get("latency_ms")
            or _duration_ms(run.get("started_at"), run.get("finished_at")),
            error_code=run.get("error_code"),
            error_message=run.get("error_message"),
            finished_at=run.get("finished_at"),
            label="定时作业运行",
            metadata={
                "collector_run_id": run.get("collector_run_id"),
                "records_imported": run.get("records_imported"),
                "scheduled_job_id": run.get("scheduled_job_id"),
                "source_run_id": run.get("source_run_id"),
                "trigger_type": run.get("trigger_type"),
            },
            source_id=str(run["id"]),
            source_type="scheduled_job_run",
            started_at=run.get("started_at") or run.get("created_at"),
            status=run.get("status"),
            summary=run.get("error_message")
            or _summary_from_result(run.get("result_summary"))
            or run.get("status"),
        )

    def plugin_node(self, plugin: dict[str, Any]) -> dict[str, Any]:
        return _node(
            duration_ms=plugin.get("latency_ms"),
            error_code=plugin.get("error_code"),
            error_message=plugin.get("error_message"),
            finished_at=plugin.get("updated_at"),
            label="插件调用",
            metadata={
                "action_id": plugin.get("action_id"),
                "connection_id": plugin.get("connection_id"),
                "plugin_id": plugin.get("plugin_id"),
                "request_summary": plugin.get("request_summary"),
                "response_summary": plugin.get("response_summary"),
                "scheduled_job_id": plugin.get("scheduled_job_id"),
                "scheduled_job_run_id": plugin.get("scheduled_job_run_id"),
                "trace_id": plugin.get("trace_id"),
                "trigger_type": plugin.get("trigger_type"),
            },
            source_id=str(plugin["id"]),
            source_type="plugin_invocation_log",
            started_at=plugin.get("created_at"),
            status=plugin.get("status"),
            summary=plugin.get("error_message") or plugin.get("status"),
        )

    def task_node(self, task: dict[str, Any]) -> dict[str, Any]:
        return _node(
            duration_ms=_duration_ms(
                task.get("claimed_at") or task.get("created_at"), task.get("finished_at")
            ),
            error_code=task.get("error_code"),
            error_message=task.get("error_message"),
            finished_at=task.get("finished_at"),
            label="AI 执行器任务",
            metadata={
                "ai_task_id": task.get("ai_task_id"),
                "executor_type": task.get("executor_type"),
                "plugin_invocation_log_id": task.get("plugin_invocation_log_id"),
                "request_config": task.get("request_config"),
                "result_json": task.get("result_json"),
                "runner_id": task.get("runner_id"),
                "scheduled_job_id": task.get("scheduled_job_id"),
                "scheduled_job_run_id": task.get("scheduled_job_run_id"),
                "workspace_root": task.get("workspace_root"),
            },
            source_id=str(task["id"]),
            source_type="ai_executor_task",
            started_at=task.get("claimed_at") or task.get("created_at"),
            status=task.get("status"),
            summary=task.get("error_message") or task.get("executor_type") or task.get("status"),
        )

    def model_log_node(self, log: dict[str, Any]) -> dict[str, Any]:
        return _node(
            duration_ms=log.get("latency_ms"),
            error_message=log.get("error"),
            finished_at=log.get("updated_at") or log.get("created_at"),
            label="模型网关调用",
            metadata={
                "ai_task_id": log.get("ai_task_id"),
                "model": log.get("model"),
                "model_gateway_config_id": log.get("model_gateway_config_id"),
                "provider": log.get("provider"),
                "purpose": log.get("purpose"),
                "tokens": log.get("tokens"),
            },
            source_id=str(log["id"]),
            source_type="model_gateway_log",
            started_at=log.get("created_at"),
            status=log.get("status"),
            summary=log.get("error") or f"{log.get('provider', '-')}/{log.get('model', '-')}",
        )

    def report_node(self, report: dict[str, Any]) -> dict[str, Any]:
        return _node(
            duration_ms=_duration_ms(report.get("scan_started_at"), report.get("scan_finished_at")),
            error_message=report.get("coverage_warning"),
            finished_at=report.get("scan_finished_at") or report.get("updated_at"),
            label="代码巡检报告",
            metadata={
                "branch": report.get("branch"),
                "commit_sha": report.get("commit_sha"),
                "finding_count": report.get("finding_count"),
                "plugin_invocation_log_id": report.get("plugin_invocation_log_id"),
                "product_id": report.get("product_id"),
                "quality_gate": report.get("quality_gate"),
                "repository_id": report.get("repository_id"),
                "risk_level": report.get("risk_level"),
                "scheduled_job_id": report.get("scheduled_job_id"),
                "scheduled_job_run_id": report.get("scheduled_job_run_id"),
                "severe_finding_count": report.get("severe_finding_count"),
            },
            source_id=str(report["id"]),
            source_type="code_inspection_report",
            started_at=report.get("scan_started_at") or report.get("created_at"),
            status=report.get("status"),
            summary=report.get("summary") or report.get("risk_level"),
        )

    def audit_node(self, event: dict[str, Any]) -> dict[str, Any]:
        result = event.get("result") or (
            "failed" if event.get("payload", {}).get("error") else "success"
        )
        return _node(
            label="审计事件",
            metadata={
                "actor_id": event.get("actor_id"),
                "ai_task_id": event.get("ai_task_id"),
                "event_type": event.get("event_type"),
                "payload": event.get("payload"),
                "sequence": event.get("sequence"),
                "subject_id": event.get("subject_id"),
                "subject_type": event.get("subject_type"),
            },
            source_id=str(event["id"]),
            source_type="audit_event",
            started_at=event.get("created_at"),
            status=result,
            summary=event.get("event_type"),
        )

    def stage_nodes(self, run: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        result_summary = (
            run.get("result_summary") if isinstance(run.get("result_summary"), dict) else {}
        )
        trace_graph = (
            result_summary.get("trace_graph")
            if isinstance(result_summary.get("trace_graph"), dict)
            else {}
        )
        graph_nodes = trace_graph.get("nodes") if isinstance(trace_graph.get("nodes"), list) else []
        graph_edges = trace_graph.get("edges") if isinstance(trace_graph.get("edges"), list) else []
        run_id = str(run["id"])
        if graph_nodes:
            nodes = [
                self._stage_node(run_id, graph_node)
                for graph_node in graph_nodes
                if isinstance(graph_node, dict) and graph_node.get("id")
            ]
            edges = [
                _edge(
                    f"scheduled_job_stage:{run_id}:{edge.get('from')}",
                    f"scheduled_job_stage:{run_id}:{edge.get('to')}",
                    "next",
                )
                for edge in graph_edges
                if isinstance(edge, dict) and edge.get("from") and edge.get("to")
            ]
            return nodes, edges

        execution_nodes = result_summary.get("execution_nodes")
        if not isinstance(execution_nodes, dict):
            return [], []
        ordered_keys = [
            "data_connection",
            "runner_execution",
            "skill_processing",
            "native_scan",
            "result_action",
            "code_inspection_report",
            "bug_creation",
            "task_creation",
            "notifications",
        ]
        present_keys = [key for key in ordered_keys if isinstance(execution_nodes.get(key), dict)]
        present_keys.extend(
            key
            for key, value in execution_nodes.items()
            if key not in present_keys and isinstance(value, dict)
        )
        nodes = [
            self._stage_node(run_id, {"id": key, **execution_nodes[key]}) for key in present_keys
        ]
        edges = [
            _edge(
                f"scheduled_job_stage:{run_id}:{present_keys[index]}",
                f"scheduled_job_stage:{run_id}:{present_keys[index + 1]}",
                "next",
            )
            for index in range(len(present_keys) - 1)
        ]
        return nodes, edges

    def _stage_node(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        stage_id = str(payload.get("id"))
        return _node(
            duration_ms=payload.get("duration_ms"),
            error_message=payload.get("error"),
            label=str(payload.get("label") or stage_id),
            metadata=payload,
            source_id=f"{run_id}:{stage_id}",
            source_type="scheduled_job_stage",
            started_at=payload.get("started_at"),
            status=payload.get("status") or ("failed" if payload.get("error") else "succeeded"),
            summary=payload.get("summary") or payload.get("status") or payload.get("error"),
        )

    def _attach_audit(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, str]],
        related: dict[str, set[str]],
        subject_id: str,
        *,
        root_node_id: str,
    ) -> None:
        audit_events = list(self.audit_by_subject_id.get(subject_id, []))
        for node in nodes:
            audit_events.extend(self.audit_by_subject_id.get(node["source_id"], []))
            if node["metadata"].get("ai_task_id"):
                audit_events.extend(
                    self.audit_by_ai_task.get(str(node["metadata"]["ai_task_id"]), [])
                )
        for event in _unique_records(audit_events):
            nodes.append(self.audit_node(event))
            edges.append(_edge(root_node_id, f"audit_event:{event['id']}", "audits"))
            related["audit_event"].add(str(event["id"]))

    @staticmethod
    def _empty_related() -> dict[str, set[str]]:
        return {source_type: set() for source_type in EXECUTION_TRACE_SOURCE_TYPES}

    def _trace_payload(
        self,
        *,
        edges: list[dict[str, str]],
        nodes: list[dict[str, Any]],
        related: dict[str, set[str]],
        root: dict[str, Any],
        root_type: str,
        title: str,
    ) -> dict[str, Any]:
        nodes = _unique_records(nodes)
        statuses = [node["status"] for node in nodes]
        started_at = _first_timestamp(nodes, ("started_at",)) or root.get("created_at")
        finished_at = _last_timestamp(nodes, ("finished_at", "started_at"))
        duration = root.get("latency_ms")
        if duration is None:
            duration = _duration_ms(started_at, finished_at)
        node_ids = {node["id"] for node in nodes}
        edges = [
            edge
            for edge in _unique_edges(edges)
            if edge.get("from") in node_ids and edge.get("to") in node_ids
        ]
        for source_type, ids in related.items():
            ids.update(
                node["source_id"]
                for node in nodes
                if node["source_type"] == source_type and not node["source_id"].startswith("None")
            )
        failed_node_count = sum(1 for node in nodes if node["status"] in FAILED_STATUSES)
        running_node_count = sum(1 for node in nodes if node["status"] in RUNNING_STATUSES)
        return {
            "duration_ms": duration,
            "edges": edges,
            "failed_node_count": failed_node_count,
            "id": str(root["id"]),
            "nodes": nodes,
            "node_count": len(nodes),
            "related_ids": {
                source_type: sorted(ids) for source_type, ids in related.items() if ids
            },
            "root_id": str(root["id"]),
            "root_type": root_type,
            "running_node_count": running_node_count,
            "started_at": started_at,
            "status": _merge_status(statuses),
            "summary": _first_non_empty(
                root.get("error_message"),
                root.get("summary"),
                _summary_from_result(root.get("result_summary")),
                title,
            ),
            "title": title,
            "updated_at": root.get("updated_at") or finished_at or started_at,
        }


def _unique_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for record in records:
        record_id = str(record.get("id") or "")
        if not record_id or record_id in seen:
            continue
        seen.add(record_id)
        result.append(record)
    return result


def _unique_edges(edges: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, str]] = []
    for edge in edges:
        key = (edge.get("from", ""), edge.get("to", ""), edge.get("label", ""))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        result.append(edge)
    return result


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _summary_from_result(result_summary: Any) -> str:
    if not isinstance(result_summary, dict):
        return ""
    for key in ("summary", "message", "error_message"):
        value = result_summary.get(key)
        if value:
            return str(value)
    result_action = result_summary.get("result_action")
    if isinstance(result_action, dict):
        return _first_non_empty(result_action.get("summary"), result_action.get("message"))
    return ""


def _first_timestamp(nodes: list[dict[str, Any]], fields: tuple[str, ...]) -> str | None:
    values = [
        str(node[field])
        for node in nodes
        for field in fields
        if node.get(field) and list_datetime_timestamp(node.get(field)) > 0
    ]
    return min(values, key=list_datetime_timestamp) if values else None


def _last_timestamp(nodes: list[dict[str, Any]], fields: tuple[str, ...]) -> str | None:
    values = [
        str(node[field])
        for node in nodes
        for field in fields
        if node.get(field) and list_datetime_timestamp(node.get(field)) > 0
    ]
    return max(values, key=list_datetime_timestamp) if values else None


def _trace_matches_related_id(trace: dict[str, Any], trace_id: str) -> bool:
    if trace["id"] == trace_id:
        return True
    if trace["root_id"] == trace_id:
        return True
    for values in trace.get("related_ids", {}).values():
        if trace_id in values:
            return True
    return any(node.get("source_id") == trace_id for node in trace.get("nodes", []))


def _list_item(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "duration_ms": trace.get("duration_ms"),
        "failed_node_count": trace["failed_node_count"],
        "id": trace["id"],
        "node_count": trace["node_count"],
        "related_ids": trace.get("related_ids", {}),
        "root_id": trace["root_id"],
        "root_type": trace["root_type"],
        "running_node_count": trace["running_node_count"],
        "started_at": trace.get("started_at"),
        "status": trace["status"],
        "summary": trace["summary"],
        "title": trace["title"],
        "updated_at": trace.get("updated_at"),
    }


def list_execution_traces_response(
    *,
    created_from: str | None,
    created_to: str | None,
    current_store: Any,
    keyword: str | None,
    page: int | None,
    page_size: int | None,
    sort_by: str | None,
    sort_order: str,
    source_type: str | None,
    started_at: float | None,
    status: str | None,
    trace_id: str,
) -> dict[str, Any]:
    ensure_list_enum(source_type, EXECUTION_TRACE_SOURCE_TYPES, "source_type")
    ensure_list_enum(status, EXECUTION_TRACE_STATUSES, "status")
    ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        ensure_list_enum(sort_by, EXECUTION_TRACE_SORT_FIELDS, "sort_by")
    from_at = parse_trace_datetime(created_from, "created_from") if created_from else None
    to_at = parse_trace_datetime(created_to, "created_to") if created_to else None
    repository = _refresh_trace_snapshots(current_store)
    if repository is not None:
        resolved_sort_by = sort_by or "started_at"
        with_pagination = page is not None or page_size is not None
        total = repository.count_execution_trace_snapshots(
            created_from=from_at,
            created_to=to_at,
            keyword=keyword,
            source_type=source_type,
            status=status,
        )
        resolved_page = page or 1
        resolved_page_size = page_size or 10
        limit = resolved_page_size if with_pagination else max(total, 1)
        offset = (resolved_page - 1) * resolved_page_size if with_pagination else 0
        snapshots = repository.list_execution_trace_snapshots(
            created_from=from_at,
            created_to=to_at,
            keyword=keyword,
            limit=limit,
            offset=offset,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            source_type=source_type,
            status=status,
        )
        payload: dict[str, Any] = {
            "items": [_list_item(snapshot) for snapshot in snapshots],
            "total": total,
        }
        if with_pagination:
            payload["page"] = resolved_page
            payload["page_size"] = resolved_page_size
        return envelope(
            add_list_observability(
                payload,
                filters={
                    "created_from": created_from,
                    "created_to": created_to,
                    "keyword": keyword,
                    "source_type": source_type,
                    "status": status,
                },
                list_name="execution_traces",
                page=resolved_page if with_pagination else None,
                page_size=resolved_page_size if with_pagination else None,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
                started_at=started_at,
            ),
            trace_id,
        )
    traces = [_list_item(trace) for trace in ExecutionTraceBuilder(current_store).traces()]
    if source_type:
        traces = [trace for trace in traces if trace["root_type"] == source_type]
    if status:
        traces = [trace for trace in traces if trace["status"] == status]
    if from_at or to_at:
        traces = [
            trace
            for trace in traces
            if _within_time_range(
                trace.get("started_at") or trace.get("updated_at"), from_at, to_at
            )
        ]
    traces = [
        trace
        for trace in traces
        if list_text_matches(
            {
                **trace,
                "related_text": " ".join(
                    value for values in trace.get("related_ids", {}).values() for value in values
                ),
            },
            keyword,
            ("id", "root_id", "root_type", "title", "summary", "related_text"),
        )
    ]
    traces = sort_list_items(
        traces,
        allowed_fields=EXECUTION_TRACE_SORT_FIELDS,
        default_sort_by="started_at",
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginated_list_payload(
        traces,
        filters={
            "created_from": created_from,
            "created_to": created_to,
            "keyword": keyword,
            "source_type": source_type,
            "status": status,
        },
        list_name="execution_traces",
        observed=True,
        page=page,
        page_size=page_size,
        sort_by=sort_by or "started_at",
        sort_order=sort_order,
        started_at=started_at,
        trace_id=trace_id,
    )


def get_execution_trace_response(
    *,
    current_store: Any,
    trace_id: str,
) -> dict[str, Any]:
    repository = _refresh_trace_snapshots(current_store)
    if repository is not None:
        trace = repository.get_execution_trace_snapshot(trace_id)
        if trace is not None:
            return trace
        raise api_error(404, "EXECUTION_TRACE_NOT_FOUND", "Execution trace not found")
    for trace in ExecutionTraceBuilder(current_store).traces():
        if _trace_matches_related_id(trace, trace_id):
            return trace
    raise api_error(404, "EXECUTION_TRACE_NOT_FOUND", "Execution trace not found")


def _within_time_range(value: Any, from_at: datetime | None, to_at: datetime | None) -> bool:
    if not value:
        return False
    try:
        parsed = parse_trace_datetime(str(value), "created_at")
    except Exception:
        return False
    if from_at and parsed < from_at:
        return False
    if to_at and parsed > to_at:
        return False
    return True
