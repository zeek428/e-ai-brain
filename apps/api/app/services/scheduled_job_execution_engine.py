from __future__ import annotations

from typing import Any

from app.services.plugins import (
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
            "connection_id": plugin_summary.get("connection_id")
            or job.get("plugin_connection_id"),
            "input_mapping": resolved_plugin_input_mapping,
            "label": "数据连接获取内容",
            "latency_ms": plugin_summary.get("latency_ms"),
            "plugin_invocation_log_id": plugin_summary.get("invocation_log_id"),
            "processing_mode": request_summary.get("processing_mode")
            or response_summary.get("processing_mode"),
            "records_imported": records_imported,
            "request_method": request_summary.get("method")
            or request_preview.get("method"),
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
            [
                (summary.get("response_summary") or {}).get("json")
                for summary in summaries
            ],
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
            "input_mapping": resolved_plugin_input_mapping,
            "latency_ms": summary.get("latency_ms"),
            "plugin_invocation_log_id": summary.get("invocation_log_id"),
            "request_method": request_summary.get("method") or request_preview.get("method"),
            "request_summary": request_summary,
            "request_url": request_summary.get("url") or request_preview.get("url"),
            "response_status_code": response_summary.get("status_code"),
            "response_summary": response_summary,
            "status": summary.get("status") or "unknown",
        }

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
                "write_target": plugin_output_mapping.get("write_target")
                or "scheduled_job_result",
                "write_target_label": write_preview.get("write_target_label")
                or plugin_output_mapping.get("write_target")
                or "scheduled_job_result",
            },
            "skill_processing": {
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "note": "当前作业类型未执行平台 Skill/大模型处理，结果直接来自插件动作。",
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
                "task_ids": inspection_result.get("task_ids") or [],
            },
            "label": "结果动作反馈内容",
            "records_imported": int(report.get("finding_count") or 0),
            "status": "succeeded",
            "write_target": "code_inspection_reports",
        }

    @staticmethod
    def trace_graph_for_run(run: dict[str, Any]) -> dict[str, Any] | None:
        result_summary = run.get("result_summary") or {}
        execution_nodes = result_summary.get("execution_nodes")
        if not isinstance(execution_nodes, dict) or not execution_nodes:
            return None
        config_snapshot = run.get("config_snapshot") or {}
        retry_count = int(config_snapshot.get("max_retry_count") or 0)
        ordered_node_ids = [
            "data_connection",
            "native_scan",
            "runner_execution",
            "skill_processing",
            "result_action",
            "task_creation",
            "bug_creation",
            "notifications",
            "code_inspection_report",
        ]
        present_ids = [node_id for node_id in ordered_node_ids if node_id in execution_nodes]
        for node_id in execution_nodes:
            if node_id not in present_ids and isinstance(execution_nodes.get(node_id), dict):
                present_ids.append(node_id)
        graph_nodes = [
            ScheduledJobExecutionEngine._trace_graph_node(
                node_id,
                execution_nodes.get(node_id),
                retry_count=retry_count,
            )
            for node_id in present_ids
        ]
        graph_edges = [
            {"from": present_ids[index], "to": present_ids[index + 1]}
            for index in range(len(present_ids) - 1)
        ]
        return {"edges": graph_edges, "nodes": graph_nodes}

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
            duration_ms = 0
        status = str(node.get("status") or ("empty" if not node else "available"))
        error_message = node.get("error_message")
        error_code = node.get("error_code")
        error = (
            {"code": error_code, "message": error_message}
            if error_code or error_message or status in {"failed", "timed_out", "cancelled"}
            else None
        )
        return {
            "duration_ms": max(0, int(duration_ms)),
            "error": error,
            "id": node_id,
            "input": ScheduledJobExecutionEngine._trace_node_input(node_id, node),
            "label": node.get("label") or node_id,
            "output": ScheduledJobExecutionEngine._trace_node_output(node_id, node),
            "retry_count": retry_count,
            "status": status,
        }

    @staticmethod
    def _trace_node_input(node_id: str, node: dict[str, Any]) -> dict[str, Any]:
        if node_id == "data_connection":
            value = node.get("input_mapping")
            return dict(value) if isinstance(value, dict) else {}
        if node_id == "skill_processing":
            value = node.get("input")
            return dict(value) if isinstance(value, dict) else {}
        if node_id == "result_action":
            return {
                "records_imported": node.get("records_imported"),
                "write_target": node.get("write_target"),
            }
        return {}

    @staticmethod
    def _trace_node_output(node_id: str, node: dict[str, Any]) -> dict[str, Any]:
        if node_id == "data_connection":
            return {
                "connection_count": node.get("connection_count"),
                "records_imported": node.get("records_imported"),
                "response_status_code": node.get("response_status_code"),
            }
        if node_id == "skill_processing":
            value = node.get("output")
            return dict(value) if isinstance(value, dict) else {}
        if node_id in {"result_action", "task_creation", "bug_creation", "notifications"}:
            feedback = node.get("feedback")
            if isinstance(feedback, dict):
                return dict(feedback)
            return {
                key: node.get(key)
                for key in ("created_task_ids", "created_bug_ids", "created_notification_ids")
                if key in node
            }
        if node_id == "runner_execution":
            result_json = node.get("result_json")
            return dict(result_json) if isinstance(result_json, dict) else {}
        return {}
