from __future__ import annotations

from typing import Any

from app.services.plugins import (
    records_imported_from_mapping,
    result_write_preview,
)


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
        return {
            "action_id": plugin_summary.get("action_id") or job.get("plugin_action_id"),
            "connection_environment": plugin_summary.get("connection_environment"),
            "connection_id": plugin_summary.get("connection_id")
            or job.get("plugin_connection_id"),
            "input_mapping": resolved_plugin_input_mapping,
            "label": "数据连接获取内容",
            "latency_ms": plugin_summary.get("latency_ms"),
            "plugin_invocation_log_id": plugin_summary.get("invocation_log_id"),
            "records_imported": records_imported,
            "request_method": request_summary.get("method")
            or request_preview.get("method"),
            "request_summary": request_summary,
            "request_url": request_summary.get("url") or request_preview.get("url"),
            "response_status_code": response_summary.get("status_code"),
            "response_summary": response_summary,
            "status": plugin_summary.get("status") or "unknown",
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
        response_summary["ai_processed"] = True
        response_summary["json"] = ai_processing["output_json"]
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
