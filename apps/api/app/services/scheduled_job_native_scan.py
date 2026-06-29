from __future__ import annotations

from typing import Any

from app.services.code_inspections import execute_code_inspection_result_actions
from app.services.native_code_scanner import NATIVE_CODE_SCAN_MODE, run_native_code_scan


def native_code_scan_repository_ids(job: dict[str, Any]) -> list[str]:
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
    collector_run_id: str | None,
    job: dict[str, Any],
    repository_ids: list[str],
    run_id: str,
    skill_codes: list[str],
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    report_ids: list[str] = []
    reports_by_repository: dict[str, dict[str, Any]] = {}
    action_results: list[dict[str, Any]] = []
    bug_ids: list[str] = []
    deduplicated_bug_ids: list[str] = []
    notification_ids: list[str] = []
    task_ids: list[str] = []
    severe_finding_count = 0
    total_findings = 0
    total_source_findings = 0
    risk_level = "low"
    native_scans: list[dict[str, Any]] = []
    for repository_id in repository_ids:
        scanned_job = native_code_scan_job_for_repository(job, repository_id=repository_id)
        plugin_summary = run_native_code_scan(
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
        inspection_result = execute_code_inspection_result_actions(
            current_store,
            collector_run_id=collector_run_id,
            job=scanned_job,
            plugin_summary=plugin_summary,
            result_actions=job.get("result_actions") or [],
            run_id=run_id,
            user=user,
        )
        report = inspection_result["report"]
        report_ids.append(report["id"])
        total_findings += int(inspection_result["finding_count"])
        severe_finding_count += int(report.get("severe_finding_count") or 0)
        risk_level = highest_code_inspection_risk(risk_level, report.get("risk_level"))
        action_results.extend(inspection_result["action_results"])
        bug_ids.extend(inspection_result["bug_ids"])
        deduplicated_bug_ids.extend(inspection_result["deduplicated_bug_ids"])
        notification_ids.extend(inspection_result["notification_ids"])
        task_ids.extend(inspection_result.get("task_ids") or [])
        native_scan = (plugin_summary.get("response_summary") or {}).get("native_scan")
        if isinstance(native_scan, dict):
            native_scans.append(native_scan)
        reports_by_repository[repository_id] = {
            "branch": report.get("branch"),
            "finding_count": report.get("finding_count"),
            "report_id": report["id"],
            "risk_level": report.get("risk_level"),
            "severe_finding_count": report.get("severe_finding_count"),
        }
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
                    "label": "结果动作反馈内容",
                    "records_imported": total_findings,
                    "status": "succeeded",
                    "write_target": "code_inspection_reports",
                },
                "result_actions": action_results,
                "task_creation": {
                    "created_task_ids": task_ids,
                    "label": "严重问题自动创建整改任务",
                    "records_imported": len(task_ids),
                    "status": "succeeded",
                },
            },
            "finding_count": total_findings,
            "notification_ids": notification_ids,
            "processing": {
                "model_gateway_called": False,
                "multi_repository": True,
                "repository_count": len(repository_ids),
                "skill_codes": skill_codes,
                "skill_ids": list(job.get("skill_ids", [])),
            },
            "report_count": len(report_ids),
            "report_ids": report_ids,
            "reports_by_repository": reports_by_repository,
            "result_actions": job.get("result_actions") or [],
            "risk_level": risk_level,
            "severe_finding_count": severe_finding_count,
            "task_ids": task_ids,
        },
        total_findings,
    )


def queued_native_scan_result_summary(
    *,
    job: dict[str, Any],
    repository: dict[str, Any] | None,
    skill_codes: list[str],
) -> dict[str, Any]:
    job_config = job.get("config_json") or {}
    repository_id = job_config.get("repository_id")
    repository = repository or {}
    branch = job_config.get("branch") or repository.get("default_branch")
    return {
        "execution_nodes": {
            "code_inspection_report": {
                "label": "代码巡检报告写入结果",
                "records_imported": 0,
                "status": "queued",
            },
            "native_scan": {
                "branch": branch,
                "label": "本地完整代码静态扫描",
                "records_imported": 0,
                "repository_id": repository_id,
                "scan_mode": NATIVE_CODE_SCAN_MODE,
                "status": "queued",
            },
            "result_action": {
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
