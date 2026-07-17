from __future__ import annotations

from typing import Any

from app.services.plugin_result_mapping import (
    records_imported_from_mapping,
    result_write_preview,
)

CODE_INSPECTION_SOURCE_METADATA_FIELDS = (
    "artifact_ref",
    "branch",
    "checkout_path",
    "checkout_path_retained",
    "commit_sha",
    "coverage_warning",
    "external_scanner_status",
    "files_scanned",
    "incremental_file_count",
    "incremental_from_commit",
    "is_full_scan",
    "lines_scanned",
    "quality_gate",
    "remote_url_hash",
    "remote_url_summary",
    "repository_id",
    "rules_loaded",
    "rules_version",
    "scan_finished_at",
    "scan_mode",
    "scan_profile",
    "scan_started_at",
    "scanner_name",
    "scanner_version",
    "suppressed_finding_count",
    "suppression_summary",
)
CODE_INSPECTION_NATIVE_SCAN_MODE = "native_full_scan"


class ScheduledJobExecutionEngine:
    """Build scheduled job execution traces and execution-time helper summaries."""

    @staticmethod
    def uses_ai_processing(
        job: dict[str, Any],
        *,
        ai_required_job_types: set[str],
    ) -> bool:
        return (
            job.get("execution_mode") in {"ai_assisted", "ai_generated"}
            or job.get("job_type") in ai_required_job_types
        )

    @staticmethod
    def plugin_result_write_preview(
        plugin_summary: dict[str, Any],
        plugin_output_mapping: dict[str, Any],
    ) -> dict[str, Any]:
        return result_write_preview(
            plugin_summary.get("response_summary") or {},
            plugin_output_mapping,
        )

    @classmethod
    def plugin_records_imported_from_result(
        cls,
        plugin_summary: dict[str, Any],
        plugin_output_mapping: dict[str, Any],
    ) -> int:
        preview = cls.plugin_result_write_preview(plugin_summary, plugin_output_mapping)
        records_imported = preview.get("records_imported")
        if isinstance(records_imported, int) and records_imported >= 0:
            return records_imported
        return records_imported_from_mapping(
            plugin_summary.get("response_summary") or {},
            plugin_output_mapping,
        )

    @staticmethod
    def data_connection_execution_node(
        *,
        job: dict[str, Any],
        plugin_summary: dict[str, Any],
        records_imported: int,
        resolved_plugin_input_mapping: dict[str, Any],
    ) -> dict[str, Any]:
        request_summary = plugin_summary.get("request_summary") or {}
        request_preview = request_summary.get("request_preview") or {}
        response_summary = plugin_summary.get("response_summary") or {}
        node = {
            "action_id": plugin_summary.get("action_id") or job.get("plugin_action_id"),
            "connection_environment": plugin_summary.get("connection_environment"),
            "connection_id": plugin_summary.get("connection_id") or job.get("plugin_connection_id"),
            "error_code": plugin_summary.get("error_code"),
            "error_message": plugin_summary.get("error_message"),
            "input_mapping": resolved_plugin_input_mapping,
            "label": "数据连接获取内容",
            "latency_ms": plugin_summary.get("latency_ms"),
            "plugin_invocation_log_id": plugin_summary.get("invocation_log_id"),
            "processing_mode": request_summary.get("processing_mode")
            or response_summary.get("processing_mode"),
            "records_imported": records_imported,
            "request_method": request_summary.get("method") or request_preview.get("method"),
            "request_summary": request_summary,
            "request_url": request_summary.get("url") or request_preview.get("url"),
            "response_status_code": response_summary.get("status_code"),
            "response_summary": response_summary,
            "status": plugin_summary.get("status") or "unknown",
        }
        items = plugin_summary.get("items")
        if isinstance(items, list):
            node["connection_count"] = int(plugin_summary.get("connection_count") or len(items))
            node["failed_count"] = int(plugin_summary.get("failed_count") or 0)
            node["failure_policy"] = plugin_summary.get("failure_policy")
            node["invocation_log_ids"] = [
                item.get("plugin_invocation_log_id")
                for item in items
                if isinstance(item, dict) and item.get("plugin_invocation_log_id")
            ]
            node["items"] = items
            node["merge_strategy"] = plugin_summary.get("merge_strategy")
            node["successful_count"] = int(plugin_summary.get("successful_count") or 0)
        return node

    @classmethod
    def merged_plugin_summary(
        cls,
        summaries: list[dict[str, Any]],
        *,
        failure_policy: str,
        merge_strategy: str,
        resolved_plugin_input_mapping: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not summaries:
            return None
        if len(summaries) == 1:
            return summaries[0]
        merged_json = cls._merged_response_json(
            [(summary.get("response_summary") or {}).get("json") for summary in summaries],
            merge_strategy=merge_strategy,
        )
        first = summaries[0]
        first_response_summary = first.get("response_summary") or {}
        statuses = [str(summary.get("status") or "unknown") for summary in summaries]
        successful_count = sum(1 for status in statuses if status == "succeeded")
        failed_count = sum(1 for status in statuses if status != "succeeded")
        status = (
            "succeeded"
            if failed_count == 0
            else "failed"
            if successful_count == 0
            else "partial_failed"
        )
        first_failed = next(
            (summary for summary in summaries if str(summary.get("status")) != "succeeded"),
            {},
        )
        items = [
            cls._plugin_summary_item(
                summary,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            )
            for summary in summaries
        ]
        return {
            **first,
            "connection_count": len(summaries),
            "error_code": first_failed.get("error_code"),
            "error_message": first_failed.get("error_message"),
            "failed_count": failed_count,
            "failure_policy": failure_policy,
            "items": items,
            "latency_ms": sum(
                int(summary.get("latency_ms") or 0)
                for summary in summaries
                if isinstance(summary.get("latency_ms"), int | float)
            ),
            "merge_strategy": merge_strategy,
            "response_summary": {
                **first_response_summary,
                "json": merged_json,
                "merged_from_connection_count": len(summaries),
            },
            "status": status,
            "successful_count": successful_count,
        }

    @staticmethod
    def _merged_response_json(values: list[Any], *, merge_strategy: str) -> Any:
        dict_values = [value for value in values if isinstance(value, dict)]
        if merge_strategy != "append_json_arrays" or not dict_values:
            return dict_values[0] if dict_values else {}
        merged: dict[str, Any] = {}
        for value in dict_values:
            for key, item in value.items():
                if isinstance(item, list):
                    merged.setdefault(key, [])
                    if isinstance(merged[key], list):
                        merged[key].extend(item)
                    continue
                if isinstance(item, int | float) and key.endswith("count"):
                    current = merged.get(key)
                    merged[key] = (current if isinstance(current, int | float) else 0) + item
                    continue
                if key not in merged:
                    merged[key] = item
        return merged

    @staticmethod
    def _plugin_summary_item(
        summary: dict[str, Any],
        *,
        resolved_plugin_input_mapping: dict[str, Any],
    ) -> dict[str, Any]:
        request_summary = summary.get("request_summary") or {}
        request_preview = request_summary.get("request_preview") or {}
        response_summary = summary.get("response_summary") or {}
        return {
            "action_id": summary.get("action_id"),
            "connection_environment": summary.get("connection_environment"),
            "connection_id": summary.get("connection_id"),
            "error_code": summary.get("error_code"),
            "error_message": summary.get("error_message"),
            "input_mapping": resolved_plugin_input_mapping,
            "latency_ms": summary.get("latency_ms"),
            "plugin_invocation_log_id": summary.get("invocation_log_id"),
            "request_method": request_summary.get("method") or request_preview.get("method"),
            "request_summary": request_summary,
            "request_url": request_summary.get("url") or request_preview.get("url"),
            "records_imported": ScheduledJobExecutionEngine._response_records_imported(
                response_summary,
            ),
            "response_status_code": response_summary.get("status_code"),
            "response_summary": response_summary,
            "status": summary.get("status") or "unknown",
        }

    @staticmethod
    def _response_records_imported(response_summary: dict[str, Any]) -> int | None:
        raw_json = response_summary.get("json")
        if not isinstance(raw_json, dict):
            return None
        row_count = raw_json.get("row_count")
        if isinstance(row_count, int) and row_count >= 0:
            return row_count
        for key in ("rows", "items", "records"):
            value = raw_json.get(key)
            if isinstance(value, list):
                return len(value)
        return None

    @staticmethod
    def runner_execution_node(plugin_summary: dict[str, Any]) -> dict[str, Any] | None:
        response_summary = plugin_summary.get("response_summary") or {}
        runner = response_summary.get("runner")
        if not isinstance(runner, dict):
            return None
        return {
            "error_code": runner.get("error_code"),
            "error_message": runner.get("error_message"),
            "executor_type": runner.get("executor_type"),
            "finished_at": runner.get("finished_at"),
            "label": "AI 执行器执行内容",
            "logs": runner.get("logs") or [],
            "model_gateway_called": runner.get("model_gateway_called"),
            "model_gateway_log_id": runner.get("model_gateway_log_id"),
            "result_json": runner.get("result_json") or {},
            "runner_id": runner.get("runner_id"),
            "runner_task_id": runner.get("runner_task_id"),
            "status": runner.get("status") or "unknown",
            "workspace_root": runner.get("workspace_root"),
        }

    @classmethod
    def has_pending_runner(cls, plugin_summary: dict[str, Any] | None) -> bool:
        if plugin_summary is None:
            return False
        node = cls.runner_execution_node(plugin_summary)
        return bool(node and node.get("status") in {"queued", "claimed", "running"})

    @classmethod
    def plugin_action_execution_nodes(
        cls,
        *,
        job: dict[str, Any],
        plugin_output_mapping: dict[str, Any],
        plugin_records_imported: int,
        plugin_summary: dict[str, Any],
        resolved_plugin_input_mapping: dict[str, Any],
        skill_codes: list[str],
    ) -> dict[str, Any]:
        skill_ids = list(job.get("skill_ids", []))
        write_preview = cls.plugin_result_write_preview(plugin_summary, plugin_output_mapping)
        result_action_feedback = {
            "plugin_invocation_log_id": plugin_summary.get("invocation_log_id"),
            "records_imported": plugin_records_imported,
            "response_summary": plugin_summary.get("response_summary") or {},
            "write_preview": write_preview,
        }
        for key in (
            "delivery_id",
            "delivery_status",
            "sample_records",
            "subject",
        ):
            if key in write_preview:
                result_action_feedback[key] = write_preview[key]
        runner_node = cls.runner_execution_node(plugin_summary)
        result_action_status = plugin_summary.get("status") or "unknown"
        if runner_node and runner_node.get("status") in {"queued", "claimed", "running"}:
            result_action_status = "waiting_runner"
        nodes = {
            "data_connection": cls.data_connection_execution_node(
                job=job,
                plugin_summary=plugin_summary,
                records_imported=plugin_records_imported,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            ),
            "result_action": {
                "action_id": plugin_summary.get("action_id") or job.get("plugin_action_id"),
                "feedback": result_action_feedback,
                "label": "结果动作反馈内容",
                "records_imported": plugin_records_imported,
                "status": result_action_status,
                "write_target": plugin_output_mapping.get("write_target") or "scheduled_job_result",
                "write_target_label": write_preview.get("write_target_label")
                or plugin_output_mapping.get("write_target")
                or "scheduled_job_result",
            },
            "skill_processing": {
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "note": "当前作业类型未执行平台 Skill/大模型处理，结果直接来自动作。",
                "processing_mode": "plugin_structured_output",
                "skill_codes": skill_codes,
                "skill_ids": skill_ids,
                "status": "not_configured" if not skill_ids else "not_run",
            },
        }
        if runner_node is not None:
            nodes["runner_execution"] = runner_node
        return nodes

    @staticmethod
    def code_inspection_plugin_summary_for_ai_output(
        plugin_summary: dict[str, Any],
        *,
        ai_processing: dict[str, Any],
    ) -> dict[str, Any]:
        response_summary = dict(plugin_summary.get("response_summary") or {})
        source_json = response_summary.get("json")
        output_json = ai_processing["output_json"]
        if (
            isinstance(source_json, dict)
            and isinstance(output_json, dict)
            and source_json.get("scan_mode") == CODE_INSPECTION_NATIVE_SCAN_MODE
        ):
            merged_json = {**source_json, **output_json}
            for field in CODE_INSPECTION_SOURCE_METADATA_FIELDS:
                if field in source_json:
                    merged_json[field] = source_json[field]
            output_json = merged_json
        response_summary["ai_processed"] = True
        response_summary["json"] = output_json
        return {**plugin_summary, "response_summary": response_summary}

    @staticmethod
    def code_inspection_skill_processing_node(
        *,
        ai_processing: dict[str, Any] | None,
        job: dict[str, Any],
        output_mapping: dict[str, Any],
        skill_codes: list[str],
        source_finding_count: int,
    ) -> dict[str, Any]:
        skill_ids = list(job.get("skill_ids", []))
        if ai_processing is None:
            return {
                "input": {
                    "findings_path": str(output_mapping.get("findings_path") or "$.findings"),
                    "source_finding_count": source_finding_count,
                },
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "note": (
                    "当前代码巡检作业为确定性执行，插件扫描结果直接进入结果动作。"
                    "如需 AI 复核，请将执行模式设置为 AI 辅助或 AI 生成并配置 Agent/Skill/模型。"
                ),
                "processing_mode": "plugin_structured_output",
                "skill_codes": skill_codes,
                "skill_ids": skill_ids,
                "status": "not_configured" if not skill_ids else "not_run",
            }
        output_json = ai_processing["output_json"]
        findings = output_json.get("findings") if isinstance(output_json, dict) else []
        return {
            "input": {
                "findings_path": str(output_mapping.get("findings_path") or "$.findings"),
                "knowledge_references": ai_processing.get("knowledge_references") or [],
                "source_compaction": ai_processing.get("source_compaction"),
                "source_finding_count": source_finding_count,
            },
            "label": "Skill 处理后内容",
            "model_gateway_called": True,
            "model_gateway_config_id": ai_processing["model_gateway_config_id"],
            "model_log_id": ai_processing["model_log_id"],
            "note": "代码扫描返回内容已通过平台 AI 大模型处理为代码巡检报告可消费的结构化 JSON。",
            "output": {
                "finding_count": len(findings) if isinstance(findings, list) else 0,
                "processed_json": output_json,
                "risk_level": (
                    output_json.get("risk_level") if isinstance(output_json, dict) else None
                ),
                "summary": output_json.get("summary") if isinstance(output_json, dict) else None,
            },
            "processing_mode": "model_gateway_json_transform",
            "skill_codes": skill_codes,
            "skill_ids": skill_ids,
            "status": ai_processing["status"],
        }

    @staticmethod
    def code_inspection_result_action_node(
        *,
        inspection_result: dict[str, Any],
        report: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "action_results": inspection_result["action_results"],
            "feedback": {
                "bug_ids": inspection_result["bug_ids"],
                "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
                "notification_ids": inspection_result["notification_ids"],
                "report_id": report["id"],
                "requirement_ids": inspection_result.get("requirement_ids") or [],
            },
            "label": "结果动作反馈内容",
            "records_imported": int(report.get("finding_count") or 0),
            "status": "succeeded",
            "write_target": "code_inspection_reports",
        }

    @classmethod
    def trace_graph_for_run(cls, run: dict[str, Any]) -> dict[str, Any] | None:
        result_summary = run.get("result_summary") or {}
        execution_nodes = result_summary.get("execution_nodes")
        if not isinstance(execution_nodes, dict) or not execution_nodes:
            return None
        config_snapshot = run.get("config_snapshot") or {}
        retry_count = int(config_snapshot.get("max_retry_count") or 0)
        present_entries = cls._trace_graph_entries(execution_nodes)
        if not present_entries:
            return None
        graph_nodes = [
            ScheduledJobExecutionEngine._trace_graph_node(
                node_id,
                node,
                retry_count=retry_count,
            )
            for node_id, node in present_entries
        ]
        present_ids = [node_id for node_id, _node in present_entries]
        graph_edges = cls._trace_graph_edges(present_ids)
        return {"edges": graph_edges, "nodes": graph_nodes}

    @classmethod
    def _trace_graph_edges(cls, present_ids: list[str]) -> list[dict[str, str]]:
        if len(present_ids) < 2:
            return []
        grouped_layers: list[tuple[str, list[str]]] = []
        for node_id in present_ids:
            canonical_id = cls._canonical_trace_node_id(node_id)
            if grouped_layers and grouped_layers[-1][0] == canonical_id:
                grouped_layers[-1][1].append(node_id)
            else:
                grouped_layers.append((canonical_id, [node_id]))

        edges: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for index in range(len(grouped_layers) - 1):
            from_nodes = grouped_layers[index][1]
            to_nodes = grouped_layers[index + 1][1]
            for from_node in from_nodes:
                for to_node in to_nodes:
                    edge_key = (from_node, to_node)
                    if edge_key in seen:
                        continue
                    seen.add(edge_key)
                    edges.append({"from": from_node, "to": to_node})
        return edges

    @staticmethod
    def _trace_graph_entries(execution_nodes: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        has_requirement_creation = isinstance(execution_nodes.get("requirement_creation"), dict)
        ordered_node_ids = [
            "data_connection",
            "native_scan",
            "runner_execution",
            "skill_processing",
            "result_action",
            "requirement_creation",
            "bug_creation",
            "notifications",
            "code_inspection_report",
        ]
        if not has_requirement_creation:
            ordered_node_ids.insert(6, "task_creation")
        entries: list[tuple[str, dict[str, Any]]] = []
        seen: set[str] = set()
        for node_id in ordered_node_ids:
            if node_id == "data_connection":
                for entry in ScheduledJobExecutionEngine._expanded_trace_nodes(
                    node_id,
                    execution_nodes.get("data_connection"),
                    item_key="items",
                    label_prefix="数据连接获取内容",
                ):
                    entries.append(entry)
                    seen.add(entry[0])
                if any(entry[0].startswith("data_connection_") for entry in entries):
                    seen.add(node_id)
                continue
            if node_id == "result_action":
                expanded_result_actions = ScheduledJobExecutionEngine._expanded_trace_nodes(
                    node_id,
                    execution_nodes.get("result_actions"),
                    label_prefix="结果动作反馈内容",
                )
                if expanded_result_actions:
                    for entry in expanded_result_actions:
                        entries.append(entry)
                        seen.add(entry[0])
                    seen.add(node_id)
                    continue
            node = execution_nodes.get(node_id)
            if isinstance(node, dict):
                entries.append((node_id, node))
                seen.add(node_id)
        for node_id, node in execution_nodes.items():
            if (
                node_id in {"result_actions"}
                or node_id in seen
                or (has_requirement_creation and node_id == "task_creation")
            ):
                continue
            if isinstance(node, dict):
                entries.append((node_id, node))
                seen.add(node_id)
        return entries

    @staticmethod
    def _expanded_trace_nodes(
        node_id: str,
        raw_node: Any,
        *,
        item_key: str | None = None,
        label_prefix: str,
    ) -> list[tuple[str, dict[str, Any]]]:
        if isinstance(raw_node, dict) and item_key:
            raw_items = raw_node.get(item_key)
        else:
            raw_items = raw_node
        if not isinstance(raw_items, list) or not raw_items:
            return [(node_id, raw_node)] if isinstance(raw_node, dict) else []
        entries: list[tuple[str, dict[str, Any]]] = []
        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                continue
            expanded_node = dict(item)
            expanded_node.setdefault("label", f"{label_prefix} {index}")
            expanded_node.setdefault("status", item.get("status") or "unknown")
            if node_id == "data_connection":
                expanded_node["connection_index"] = index
            if node_id == "result_action":
                expanded_node["action_index"] = index
            entries.append((f"{node_id}_{index}", expanded_node))
        if entries:
            return entries
        return [(node_id, raw_node)] if isinstance(raw_node, dict) else []

    @staticmethod
    def _trace_graph_node(
        node_id: str,
        raw_node: Any,
        *,
        retry_count: int,
    ) -> dict[str, Any]:
        node = raw_node if isinstance(raw_node, dict) else {}
        duration_ms = node.get("latency_ms")
        if not isinstance(duration_ms, int | float):
            duration_ms = node.get("duration_ms")
        if not isinstance(duration_ms, int | float):
            duration_ms = 0
        status = str(node.get("status") or ("empty" if not node else "available"))
        error_message = node.get("error_message")
        error_code = node.get("error_code")
        error = (
            {"code": error_code, "message": error_message}
            if error_code
            or error_message
            or status in {"failed", "timed_out", "cancelled", "dead_letter"}
            else None
        )
        canonical_id = ScheduledJobExecutionEngine._canonical_trace_node_id(node_id)
        trace_input = ScheduledJobExecutionEngine._trace_node_input(node_id, node)
        trace_output = ScheduledJobExecutionEngine._trace_node_output(node_id, node)
        stage, stage_label = ScheduledJobExecutionEngine._trace_node_stage(canonical_id)
        rerun_plan = ScheduledJobExecutionEngine._trace_node_rerun_plan(
            canonical_id=canonical_id,
            error=error,
            node=node,
            node_id=node_id,
            trace_input=trace_input,
            trace_output=trace_output,
        )
        return {
            "debug_actions": ScheduledJobExecutionEngine._trace_node_debug_actions(
                rerun_plan=rerun_plan,
                input_payload=trace_input,
                output_payload=trace_output,
                error=error,
            ),
            "duration_ms": max(0, int(duration_ms)),
            "error": error,
            "id": node_id,
            "input": trace_input,
            "label": node.get("label") or node_id,
            "output": trace_output,
            "rerun_hint": ScheduledJobExecutionEngine._trace_node_rerun_hint(canonical_id),
            "rerun_plan": rerun_plan,
            "rerun_supported": bool(rerun_plan.get("single_node_supported")),
            "retry_count": retry_count,
            "snapshot_status": rerun_plan["snapshot_status"],
            "stage": stage,
            "stage_label": stage_label,
            "status": status,
        }

    @staticmethod
    def _trace_node_stage(canonical_id: str) -> tuple[str, str]:
        if canonical_id in {"data_connection", "native_scan"}:
            return "data_connection", "数据连接"
        if canonical_id == "runner_execution":
            return "ai_executor", "AI执行器"
        if canonical_id == "skill_processing":
            return "ai_processing", "AI执行"
        if canonical_id == "result_action":
            return "result_action", "动作"
        if canonical_id in {
            "bug_creation",
            "code_inspection_report",
            "notifications",
            "requirement_creation",
            "task_creation",
        }:
            return "business_side_effect", "业务副作用"
        return "other", "其他"

    @staticmethod
    def _trace_node_debug_actions(
        *,
        rerun_plan: dict[str, Any],
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
        error: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if input_payload:
            actions.append(
                {
                    "enabled": True,
                    "label": "复制输入",
                    "type": "copy_input",
                },
            )
        if output_payload:
            actions.append(
                {
                    "enabled": True,
                    "label": "复制输出",
                    "type": "copy_output",
                },
            )
        if error:
            actions.append(
                {
                    "enabled": True,
                    "label": "复制错误",
                    "type": "copy_error",
                },
            )
        if rerun_plan:
            actions.append(
                {
                    "enabled": True,
                    "label": "复制复跑计划",
                    "type": "copy_rerun_plan",
                },
            )
        return actions

    @staticmethod
    def _trace_node_rerun_plan(
        *,
        canonical_id: str,
        error: dict[str, Any] | None,
        node: dict[str, Any],
        node_id: str,
        trace_input: dict[str, Any],
        trace_output: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot_status = {
            "error": error is not None,
            "input": bool(trace_input),
            "output": bool(trace_output),
        }
        idempotency_key = ScheduledJobExecutionEngine._trace_node_idempotency_key(
            canonical_id,
            node,
            node_id=node_id,
        )
        plan = {
            "blocked_by": ["single_node_rerun_execution_guarded"],
            "can_preview_from_snapshot": bool(trace_input or trace_output),
            "full_run_supported": True,
            "idempotency_key": idempotency_key,
            "node_id": node_id,
            "plan_version": "trace_node_rerun_v2",
            "required_controls": [
                "node_input_snapshot",
                "idempotency_guard",
                "downstream_invalidation",
            ],
            "safe_next_action": "rerun_full_scheduled_job",
            "side_effect_policy": "none",
            "single_node_supported": False,
            "snapshot_status": snapshot_status,
            "status": "planning_required",
        }
        if canonical_id == "data_connection":
            blocked_by: list[str] = []
            if not snapshot_status["input"]:
                blocked_by.append("request_snapshot_missing")
            if not idempotency_key:
                blocked_by.append("connection_read_idempotency_missing")
            plan.update(
                {
                    "blocked_by": blocked_by,
                    "downstream_invalidation_strategy": (
                        "isolated_single_node_run" if not blocked_by else None
                    ),
                    "required_controls": [
                        "request_snapshot",
                        "connection_read_idempotency",
                        "downstream_ai_and_action_invalidation",
                    ],
                    "safe_next_action": (
                        "confirm_single_node_rerun"
                        if not blocked_by
                        else "rerun_full_scheduled_job"
                    ),
                    "side_effect_policy": "external_read_or_fetch",
                    "single_node_supported": not blocked_by,
                    "status": "ready" if not blocked_by else "blocked_by_controls",
                },
            )
        elif canonical_id == "skill_processing":
            blocked_by = []
            if not snapshot_status["input"]:
                blocked_by.append("ai_input_snapshot_missing")
            if not idempotency_key:
                blocked_by.append("model_gateway_idempotency_missing")
            plan.update(
                {
                    "blocked_by": blocked_by,
                    "downstream_invalidation_strategy": (
                        "isolated_single_node_run" if not blocked_by else None
                    ),
                    "required_controls": [
                        "data_connection_output_snapshot",
                        "knowledge_reference_snapshot",
                        "model_gateway_idempotency_key",
                        "downstream_invalidation",
                    ],
                    "safe_next_action": (
                        "confirm_single_node_rerun"
                        if not blocked_by
                        else "rerun_full_scheduled_job"
                    ),
                    "side_effect_policy": "model_gateway_cost_and_output_drift",
                    "single_node_supported": not blocked_by,
                    "status": "ready" if not blocked_by else "blocked_by_controls",
                },
            )
        elif canonical_id == "runner_execution":
            plan.update(
                {
                    "blocked_by": ["trace_node_runner_retry_binding_pending"],
                    "required_controls": [
                        "runner_task_snapshot",
                        "workspace_whitelist_check",
                        "runner_retry_policy",
                    ],
                    "safe_next_action": "retry_ai_executor_task",
                    "side_effect_policy": "local_workspace_mutation",
                },
            )
        elif canonical_id == "result_action":
            action_type = str(node.get("type") or node.get("action_type") or "")
            generic_result_action = action_type in {
                "save_scheduled_job_result",
                "send_notification",
            }
            blocked_by = []
            if not generic_result_action:
                blocked_by.append("write_idempotency_not_confirmed")
            if not snapshot_status["input"]:
                blocked_by.append("action_input_snapshot_missing")
            if not snapshot_status["output"]:
                blocked_by.append("action_output_snapshot_missing")
            if not idempotency_key:
                blocked_by.append("write_target_idempotency_missing")
            plan.update(
                {
                    "blocked_by": blocked_by,
                    "generic_result_action": generic_result_action,
                    "required_controls": [
                        "action_input_snapshot",
                        "action_output_snapshot",
                        "write_target_idempotency_key",
                    ],
                    "safe_next_action": (
                        "confirm_single_node_rerun"
                        if not blocked_by
                        else "rerun_full_scheduled_job"
                    ),
                    "side_effect_policy": (
                        "generic_result_write_record"
                        if generic_result_action
                        else "external_or_business_write"
                    ),
                    "single_node_supported": not blocked_by,
                    "status": "ready" if not blocked_by else "blocked_by_side_effect_guard",
                },
            )
        elif canonical_id in {
            "bug_creation",
            "code_inspection_report",
            "notifications",
            "requirement_creation",
            "task_creation",
        }:
            plan.update(
                {
                    "blocked_by": ["business_side_effect_node"],
                    "full_run_supported": False,
                    "required_controls": [
                        "business_write_deduplication",
                        "manual_approval",
                    ],
                    "safe_next_action": "inspect_then_manual_repair",
                    "side_effect_policy": "business_write",
                    "status": "blocked_by_business_side_effect",
                },
            )
        plan["rerun_controls"] = ScheduledJobExecutionEngine._trace_node_rerun_controls(
            idempotency_key=idempotency_key,
            plan=plan,
            snapshot_status=snapshot_status,
        )
        plan["control_summary"] = ScheduledJobExecutionEngine._trace_node_rerun_control_summary(
            plan["rerun_controls"],
        )
        return plan

    @staticmethod
    def _trace_node_rerun_controls(
        *,
        idempotency_key: str | None,
        plan: dict[str, Any],
        snapshot_status: dict[str, bool],
    ) -> list[dict[str, Any]]:
        return [
            ScheduledJobExecutionEngine._trace_node_rerun_control(
                control_key,
                idempotency_key=idempotency_key,
                plan=plan,
                snapshot_status=snapshot_status,
            )
            for control_key in plan.get("required_controls") or []
        ]

    @staticmethod
    def _trace_node_rerun_control_summary(
        controls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for control in controls:
            status = str(control.get("status") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        return {
            "blocked_count": status_counts.get("blocked", 0),
            "missing_count": status_counts.get("missing", 0),
            "needs_review_count": status_counts.get("needs_review", 0),
            "satisfied_count": status_counts.get("satisfied", 0),
            "status_counts": status_counts,
            "total": len(controls),
        }

    @staticmethod
    def _trace_node_rerun_control(
        control_key: str,
        *,
        idempotency_key: str | None,
        plan: dict[str, Any],
        snapshot_status: dict[str, bool],
    ) -> dict[str, Any]:
        label_by_key = {
            "action_input_snapshot": "动作输入快照",
            "action_output_snapshot": "动作输出快照",
            "business_write_deduplication": "业务写入去重",
            "connection_read_idempotency": "连接读取幂等",
            "data_connection_output_snapshot": "数据连接输出快照",
            "downstream_ai_and_action_invalidation": "下游 AI/动作失效策略",
            "downstream_invalidation": "下游失效策略",
            "human_confirmation_for_side_effect": "副作用人工确认",
            "idempotency_guard": "幂等防重控制",
            "knowledge_reference_snapshot": "知识引用快照",
            "manual_approval": "人工审批",
            "model_gateway_idempotency_key": "模型网关幂等键",
            "node_input_snapshot": "节点输入快照",
            "request_snapshot": "请求快照",
            "runner_retry_policy": "Runner 重试策略",
            "runner_task_snapshot": "Runner 任务快照",
            "workspace_whitelist_check": "工作区白名单校验",
            "write_target_idempotency_key": "写入目标幂等键",
        }
        blocked_controls = {
            "business_write_deduplication",
            "connection_read_idempotency",
            "downstream_ai_and_action_invalidation",
            "downstream_invalidation",
            "runner_retry_policy",
        }
        review_controls = {
            "human_confirmation_for_side_effect",
            "manual_approval",
            "workspace_whitelist_check",
        }
        snapshot_controls = {
            "action_input_snapshot",
            "action_output_snapshot",
            "data_connection_output_snapshot",
            "knowledge_reference_snapshot",
            "node_input_snapshot",
            "request_snapshot",
            "runner_task_snapshot",
        }
        idempotency_controls = {
            "idempotency_guard",
            "model_gateway_idempotency_key",
            "write_target_idempotency_key",
        }
        status = "missing"
        reason = "控制项尚未满足"
        if control_key in snapshot_controls:
            has_snapshot = bool(snapshot_status.get("input") or snapshot_status.get("output"))
            status = "satisfied" if has_snapshot else "missing"
            reason = "已有可用于预检的节点快照" if has_snapshot else "缺少节点快照"
        elif control_key == "connection_read_idempotency":
            status = "satisfied" if idempotency_key else "blocked"
            reason = (
                "已使用原插件调用日志生成连接读取幂等键"
                if idempotency_key
                else "缺少原插件调用日志，无法建立连接读取幂等键"
            )
        elif control_key in {
            "downstream_ai_and_action_invalidation",
            "downstream_invalidation",
        }:
            isolated = plan.get("downstream_invalidation_strategy") == "isolated_single_node_run"
            status = "satisfied" if isolated else "blocked"
            reason = (
                "单节点复跑会生成独立运行记录，下游 AI 和动作不执行"
                if isolated
                else "缺少下游 AI/动作隔离策略"
            )
        elif control_key in idempotency_controls:
            status = "satisfied" if idempotency_key else "missing"
            reason = "已生成幂等键" if idempotency_key else "缺少幂等键"
        elif control_key in blocked_controls:
            status = "blocked"
            reason = "需要服务端执行保护后才能开放单节点复跑"
        elif control_key in review_controls:
            status = "needs_review"
            reason = "需要运行时校验或人工确认"

        return {
            "key": control_key,
            "label": label_by_key.get(control_key, control_key),
            "reason": reason,
            "required": True,
            "satisfied": status == "satisfied",
            "status": status,
        }

    @staticmethod
    def _trace_node_idempotency_key(
        canonical_id: str,
        node: dict[str, Any],
        *,
        node_id: str,
    ) -> str | None:
        if canonical_id == "runner_execution" and node.get("runner_task_id"):
            return f"ai_executor_task:{node['runner_task_id']}"
        if canonical_id == "skill_processing":
            model_log_id = node.get("model_log_id") or node.get("model_gateway_log_id")
            if model_log_id:
                return f"model_gateway_log:{model_log_id}"
            model_gateway_config_id = node.get("model_gateway_config_id")
            if model_gateway_config_id:
                return f"skill_processing:{node_id}:{model_gateway_config_id}"
            if node.get("model_gateway_called") is True:
                return f"skill_processing:{node_id}:model_gateway"
        feedback = node.get("feedback")
        if isinstance(feedback, dict) and feedback.get("plugin_invocation_log_id"):
            return f"plugin_invocation_log:{feedback['plugin_invocation_log_id']}"
        if node.get("plugin_invocation_log_id"):
            return f"plugin_invocation_log:{node['plugin_invocation_log_id']}"
        if canonical_id == "result_action" and (
            node.get("type") or node.get("action_type") or node.get("write_target")
        ):
            return (
                "result_action:"
                f"{node_id}:"
                f"{node.get('type') or node.get('action_type') or 'unknown'}:"
                f"{node.get('write_target') or 'scheduled_job_result'}"
            )
        if canonical_id == "result_action" and node.get("action_id"):
            return f"result_action:{node.get('action_id')}:{node.get('write_target') or 'unknown'}"
        return None

    @staticmethod
    def _trace_node_rerun_hint(canonical_id: str) -> str:
        if canonical_id == "data_connection":
            return (
                "可先做复跑预检；请求快照、读取幂等和下游隔离满足时"
                "可单独重跑数据连接，否则请复跑整条作业。"
            )
        if canonical_id == "skill_processing":
            return (
                "可先做复跑预检；输入快照、模型幂等和下游隔离满足时"
                "可单独重跑 AI 处理，否则请复跑整条作业。"
            )
        if canonical_id == "result_action":
            return (
                "可先做复跑预检；动作输入输出快照和写入幂等满足时"
                "可单独重跑结果动作，否则请复跑整条作业。"
            )
        return "可先做复跑预检；控制项满足时支持单节点复跑，否则请复跑整条运行记录。"

    @staticmethod
    def _trace_node_input(node_id: str, node: dict[str, Any]) -> dict[str, Any]:
        canonical_id = ScheduledJobExecutionEngine._canonical_trace_node_id(node_id)
        if canonical_id == "data_connection":
            value = node.get("input_mapping")
            result = dict(value) if isinstance(value, dict) else {}
            for key in ("action_id", "connection_id", "connection_index"):
                if key in node:
                    result[key] = node.get(key)
            return result
        if canonical_id == "skill_processing":
            value = node.get("input")
            return dict(value) if isinstance(value, dict) else {}
        if canonical_id == "result_action":
            return {
                "action_code": node.get("action_code"),
                "action_id": node.get("action_id"),
                "action_index": node.get("action_index"),
                "action_name": node.get("action_name"),
                "records_imported": node.get("records_imported"),
                "write_target": node.get("write_target"),
            }
        return {}

    @staticmethod
    def _trace_node_output(node_id: str, node: dict[str, Any]) -> dict[str, Any]:
        canonical_id = ScheduledJobExecutionEngine._canonical_trace_node_id(node_id)
        if canonical_id == "data_connection":
            return {
                "connection_count": node.get("connection_count"),
                "records_imported": node.get("records_imported"),
                "response_status_code": node.get("response_status_code"),
            }
        if canonical_id == "skill_processing":
            value = node.get("output")
            return dict(value) if isinstance(value, dict) else {}
        if canonical_id in {
            "result_action",
            "requirement_creation",
            "task_creation",
            "bug_creation",
            "notifications",
        }:
            feedback = node.get("feedback")
            if isinstance(feedback, dict):
                return dict(feedback)
            return {
                key: node.get(key)
                for key in (
                    "created_requirement_ids",
                    "created_task_ids",
                    "created_bug_ids",
                    "created_notification_ids",
                )
                if key in node
            }
        if canonical_id == "runner_execution":
            result_json = node.get("result_json")
            return dict(result_json) if isinstance(result_json, dict) else {}
        return {}

    @staticmethod
    def _canonical_trace_node_id(node_id: str) -> str:
        for prefix in ("data_connection", "result_action"):
            if node_id == prefix or node_id.startswith(f"{prefix}_"):
                return prefix
        return node_id
