from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.code_inspections import execute_code_inspection_result_actions
from app.services.native_code_scanner import NATIVE_CODE_SCAN_MODE, run_native_code_scan
from app.services.product_config_context import list_product_git_repository_records
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)


def native_code_scan_repository_ids(
    job: dict[str, Any],
    *,
    current_store: Any | None = None,
) -> list[str]:
    config = job.get("config_json") or {}
    configured_ids = config.get("repository_ids")
    repository_ids: list[str] = []
    if isinstance(configured_ids, list):
        repository_ids.extend(
            str(repository_id).strip()
            for repository_id in configured_ids
            if str(repository_id or "").strip()
        )
    single_repository_id = str(config.get("repository_id") or "").strip()
    if single_repository_id:
        repository_ids.append(single_repository_id)
    if not repository_ids and current_store is not None:
        product_id = str(job.get("product_id") or "").strip()
        if product_id:
            repositories = [
                repository
                for repository in list_product_git_repository_records(
                    current_store,
                    product_id,
                    active_only=True,
                )
                if str(repository.get("repo_type") or "code") == "code"
            ]
            repositories.sort(
                key=lambda repository: (
                    str(repository.get("name") or ""),
                    str(repository.get("id") or ""),
                ),
            )
            repository_ids.extend(
                str(repository["id"])
                for repository in repositories
                if str(repository.get("id") or "").strip()
            )
    seen: set[str] = set()
    unique_ids: list[str] = []
    for repository_id in repository_ids:
        if repository_id in seen:
            continue
        seen.add(repository_id)
        unique_ids.append(repository_id)
    return unique_ids


def native_code_scan_job_for_repository(
    job: dict[str, Any],
    *,
    repository_id: str,
) -> dict[str, Any]:
    config = dict(job.get("config_json") or {})
    config["repository_id"] = repository_id
    return {**job, "config_json": config}


def highest_code_inspection_risk(current: str | None, candidate: str | None) -> str:
    ranks = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    current_value = str(current or "low")
    candidate_value = str(candidate or "low")
    return (
        candidate_value
        if ranks.get(candidate_value, 1) > ranks.get(current_value, 1)
        else current_value
    )


def execute_native_multi_code_inspection_summary(
    current_store: Any,
    *,
    ai_processor: Callable[
        [dict[str, Any], dict[str, Any], dict[str, Any], int],
        tuple[dict[str, Any] | None, dict[str, Any]],
    ]
    | None = None,
    collector_run_id: str | None,
    job: dict[str, Any],
    repository_ids: list[str],
    run_id: str,
    scan_runner: Callable[..., dict[str, Any]] | None = None,
    skill_codes: list[str],
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    report_ids: list[str] = []
    reports_by_repository: dict[str, dict[str, Any]] = {}
    action_results: list[dict[str, Any]] = []
    bug_ids: list[str] = []
    deduplicated_bug_ids: list[str] = []
    notification_ids: list[str] = []
    requirement_ids: list[str] = []
    severe_finding_count = 0
    model_gateway_called = False
    native_scan_items: list[dict[str, Any]] = []
    repository_execution: dict[str, dict[str, Any]] = {}
    result_action_items: list[dict[str, Any]] = []
    skill_processing_items: list[dict[str, Any]] = []
    total_findings = 0
    total_source_findings = 0
    risk_level = "low"
    native_scans: list[dict[str, Any]] = []
    scan_runner = scan_runner or run_native_code_scan
    for repository_id in repository_ids:
        scanned_job = native_code_scan_job_for_repository(job, repository_id=repository_id)
        plugin_summary = scan_runner(
            current_store,
            job=scanned_job,
            run_id=run_id,
            user=user,
        )
        source_response_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
        if not isinstance(source_response_json, dict):
            source_response_json = {}
        source_findings = source_response_json.get("findings")
        source_finding_count = len(source_findings) if isinstance(source_findings, list) else 0
        total_source_findings += source_finding_count
        ai_processing = None
        effective_plugin_summary = plugin_summary
        if ai_processor is not None:
            ai_processing, effective_plugin_summary = ai_processor(
                scanned_job,
                plugin_summary,
                source_response_json,
                source_finding_count,
            )
            model_gateway_called = model_gateway_called or ai_processing is not None
        inspection_result = execute_code_inspection_result_actions(
            current_store,
            collector_run_id=collector_run_id,
            job=scanned_job,
            plugin_summary=effective_plugin_summary,
            result_actions=job.get("result_actions") or [],
            run_id=run_id,
            user=user,
        )
        report = inspection_result["report"]
        skill_node = JobExecutionEngine.code_inspection_skill_processing_node(
            ai_processing=ai_processing,
            job=scanned_job,
            output_mapping={
                "findings_path": "$.findings",
                "write_target": "code_inspection_reports",
            },
            skill_codes=skill_codes,
            source_finding_count=source_finding_count,
        )
        skill_node = {
            **skill_node,
            "label": "AI执行处理内容",
            "repository_id": repository_id,
        }
        result_action_node = JobExecutionEngine.code_inspection_result_action_node(
            inspection_result=inspection_result,
            report=report,
        )
        result_action_node = {
            **result_action_node,
            "label": "结果动作反馈内容",
            "repository_id": repository_id,
        }
        skill_processing_items.append(skill_node)
        result_action_items.append(result_action_node)
        report_ids.append(report["id"])
        total_findings += int(inspection_result["finding_count"])
        severe_finding_count += int(report.get("severe_finding_count") or 0)
        risk_level = highest_code_inspection_risk(risk_level, report.get("risk_level"))
        action_results.extend(inspection_result["action_results"])
        bug_ids.extend(inspection_result["bug_ids"])
        deduplicated_bug_ids.extend(inspection_result["deduplicated_bug_ids"])
        notification_ids.extend(inspection_result["notification_ids"])
        requirement_ids.extend(inspection_result.get("requirement_ids") or [])
        native_scan = (plugin_summary.get("response_summary") or {}).get("native_scan")
        native_scan_node: dict[str, Any] = {}
        if isinstance(native_scan, dict):
            native_scans.append(native_scan)
            native_scan_node = {
                **native_scan,
                "label": "本地完整代码静态扫描",
                "records_imported": source_finding_count,
                "repository_id": repository_id,
                "scan_mode": NATIVE_CODE_SCAN_MODE,
                "status": "succeeded",
            }
            native_scan_items.append(native_scan_node)
        reports_by_repository[repository_id] = {
            "branch": report.get("branch"),
            "finding_count": report.get("finding_count"),
            "report_id": report["id"],
            "risk_level": report.get("risk_level"),
            "severe_finding_count": report.get("severe_finding_count"),
        }
        repository_execution[repository_id] = {
            "code_inspection_report": reports_by_repository[repository_id],
            "native_scan": native_scan_node,
            "result_action": result_action_node,
            "skill_processing": skill_node,
        }
    skill_processing_status = (
        "succeeded"
        if model_gateway_called
        else ("not_run" if skill_codes else "not_configured")
    )
    return (
        {
            "bug_ids": bug_ids,
            "deduplicated_bug_ids": deduplicated_bug_ids,
            "execution_nodes": {
                "bug_creation": {
                    "created_bug_ids": bug_ids,
                    "deduplicated_bug_ids": deduplicated_bug_ids,
                    "label": "严重问题自动创建 Bug",
                    "records_imported": len(bug_ids),
                    "status": "succeeded",
                },
                "code_inspection_report": {
                    "label": "代码巡检报告写入结果",
                    "records_imported": len(report_ids),
                    "report_ids": report_ids,
                    "risk_level": risk_level,
                    "severe_finding_count": severe_finding_count,
                    "status": "succeeded",
                },
                "native_scan": {
                    "items": native_scan_items,
                    "label": "本地完整代码静态扫描",
                    "native_scans": native_scans,
                    "records_imported": total_source_findings,
                    "repository_count": len(repository_ids),
                    "reports_by_repository": reports_by_repository,
                    "scan_mode": NATIVE_CODE_SCAN_MODE,
                    "status": "succeeded",
                },
                "notifications": {
                    "created_notification_ids": notification_ids,
                    "label": "问题消息通知",
                    "records_imported": len(notification_ids),
                    "status": "succeeded",
                },
                "result_action": {
                    "feedback": {
                        "report_count": len(report_ids),
                        "report_ids": report_ids,
                        "reports_by_repository": reports_by_repository,
                        "write_target": "code_inspection_reports",
                    },
                    "items": result_action_items,
                    "label": "结果动作反馈内容",
                    "records_imported": total_findings,
                    "status": "succeeded",
                    "write_target": "code_inspection_reports",
                },
                "result_actions": action_results,
                "skill_processing": {
                    "items": skill_processing_items,
                    "label": "AI执行处理内容",
                    "model_gateway_called": model_gateway_called,
                    "records_imported": total_findings,
                    "repository_count": len(repository_ids),
                    "skill_codes": skill_codes,
                    "skill_ids": list(job.get("skill_ids", [])),
                    "status": skill_processing_status,
                },
                "requirement_creation": {
                    "created_requirement_ids": requirement_ids,
                    "label": "严重问题创建整改需求",
                    "records_imported": len(requirement_ids),
                    "status": "succeeded" if requirement_ids else "not_configured",
                },
            },
            "finding_count": total_findings,
            "notification_ids": notification_ids,
            "processing": {
                "model_gateway_called": model_gateway_called,
                "multi_repository": True,
                "repository_count": len(repository_ids),
                "skill_codes": skill_codes,
                "skill_ids": list(job.get("skill_ids", [])),
            },
            "repository_execution": repository_execution,
            "report_count": len(report_ids),
            "report_ids": report_ids,
            "reports_by_repository": reports_by_repository,
            "result_actions": job.get("result_actions") or [],
            "risk_level": risk_level,
            "severe_finding_count": severe_finding_count,
            "requirement_ids": requirement_ids,
        },
        total_findings,
    )


def code_inspection_single_result_summary(
    *,
    ai_processing: dict[str, Any] | None,
    async_worker: bool = False,
    effective_plugin_summary: dict[str, Any],
    include_native_scan: bool,
    inspection_result: dict[str, Any],
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    skill_codes: list[str],
    source_finding_count: int,
) -> dict[str, Any]:
    report = inspection_result["report"]
    native_scan_summary = (plugin_summary.get("response_summary") or {}).get("native_scan")
    execution_nodes: dict[str, Any] = {
        "bug_creation": {
            "created_bug_ids": inspection_result["bug_ids"],
            "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
            "label": "严重问题自动创建 Bug",
            "records_imported": len(inspection_result["bug_ids"]),
            "status": "succeeded",
        },
        "requirement_creation": {
            "created_requirement_ids": inspection_result.get("requirement_ids") or [],
            "label": "严重问题创建整改需求",
            "records_imported": len(inspection_result.get("requirement_ids") or []),
            "status": "succeeded" if inspection_result.get("requirement_ids") else "not_configured",
        },
        "code_inspection_report": {
            "finding_count": report["finding_count"],
            "label": "代码巡检报告写入结果",
            "report_id": report["id"],
            "risk_level": report["risk_level"],
            "severe_finding_count": report["severe_finding_count"],
            "status": "succeeded",
        },
        "data_connection": JobExecutionEngine.data_connection_execution_node(
            job=job,
            plugin_summary=plugin_summary,
            records_imported=source_finding_count,
            resolved_plugin_input_mapping=resolved_plugin_input_mapping,
        ),
        **(
            {"runner_execution": ai_processing["runner_node"]}
            if isinstance((ai_processing or {}).get("runner_node"), dict)
            else {}
        ),
        "notifications": {
            "created_notification_ids": inspection_result["notification_ids"],
            "label": "问题消息通知",
            "records_imported": len(inspection_result["notification_ids"]),
            "status": "succeeded",
        },
        "result_action": JobExecutionEngine.code_inspection_result_action_node(
            inspection_result=inspection_result,
            report=report,
        ),
        "result_actions": inspection_result["action_results"],
        "skill_processing": JobExecutionEngine.code_inspection_skill_processing_node(
            ai_processing=ai_processing,
            job=job,
            output_mapping=output_mapping,
            skill_codes=skill_codes,
            source_finding_count=source_finding_count,
        ),
    }
    if include_native_scan:
        execution_nodes["native_scan"] = {
            **(native_scan_summary if isinstance(native_scan_summary, dict) else {}),
            "label": "本地完整代码静态扫描",
            "records_imported": source_finding_count,
            "scan_mode": NATIVE_CODE_SCAN_MODE,
            "status": "succeeded",
        }
    processing = {
        "model_gateway_called": ai_processing is not None,
        "skill_codes": skill_codes,
        "skill_ids": list(job.get("skill_ids", [])),
    }
    if async_worker:
        processing["async_worker"] = True
    return {
        "bug_ids": inspection_result["bug_ids"],
        "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
        "execution_nodes": execution_nodes,
        "finding_count": report["finding_count"],
        "notification_ids": inspection_result["notification_ids"],
        "plugin": effective_plugin_summary,
        "processing": processing,
        "report_id": report["id"],
        "result_actions": inspection_result["result_actions"],
        "risk_level": report["risk_level"],
        "severe_finding_count": report["severe_finding_count"],
        "requirement_ids": inspection_result.get("requirement_ids") or [],
    }


def queued_native_scan_result_summary(
    *,
    job: dict[str, Any],
    repository: dict[str, Any] | None,
    repositories: list[dict[str, Any]] | None = None,
    skill_codes: list[str],
) -> dict[str, Any]:
    job_config = job.get("config_json") or {}
    repository_id = job_config.get("repository_id")
    repository = repository or {}
    branch = job_config.get("branch") or repository.get("default_branch")
    repository_items = [
        {
            "branch": job_config.get("branch") or item.get("default_branch"),
            "label": "本地完整代码静态扫描",
            "records_imported": 0,
            "repository_id": item.get("id"),
            "scan_mode": NATIVE_CODE_SCAN_MODE,
            "status": "queued",
        }
        for item in (repositories or [])
        if item.get("id")
    ]
    repository_count = len(repository_items) if repository_items else (1 if repository_id else 0)
    return {
        "execution_nodes": {
            "code_inspection_report": {
                "label": "代码巡检报告写入结果",
                "records_imported": 0,
                "status": "queued",
            },
            "native_scan": {
                "branch": branch,
                "items": repository_items,
                "label": "本地完整代码静态扫描",
                "records_imported": 0,
                "repository_count": repository_count,
                "repository_id": repository_id,
                "scan_mode": NATIVE_CODE_SCAN_MODE,
                "status": "queued",
            },
            "skill_processing": {
                "items": [
                    {
                        "label": "AI执行处理内容",
                        "model_gateway_called": False,
                        "repository_id": item.get("repository_id"),
                        "status": "queued",
                    }
                    for item in repository_items
                ],
                "label": "AI执行处理内容",
                "model_gateway_called": False,
                "repository_count": repository_count,
                "skill_codes": skill_codes,
                "skill_ids": list(job.get("skill_ids", [])),
                "status": "queued" if skill_codes else "not_configured",
            },
            "result_action": {
                "items": [
                    {
                        "label": "结果动作反馈内容",
                        "records_imported": 0,
                        "repository_id": item.get("repository_id"),
                        "status": "queued",
                        "write_target": "code_inspection_reports",
                    }
                    for item in repository_items
                ],
                "label": "结果动作反馈内容",
                "records_imported": 0,
                "status": "queued",
                "write_target": "code_inspection_reports",
            },
        },
        "processing": {
            "async_worker": True,
            "model_gateway_called": False,
            "skill_codes": skill_codes,
            "skill_ids": list(job.get("skill_ids", [])),
        },
    }
