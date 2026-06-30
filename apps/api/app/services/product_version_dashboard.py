from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from app.services.bug_listing import bug_summary_projection
from app.services.product_config_context import (
    get_product_git_repository_record,
    get_product_version_record,
    list_product_version_branch_config_records,
    product_config_query_repository,
    product_version_summary_projection,
)
from app.services.requirement_listing import requirement_summary_projection
from app.services.task_access import can_read_task
from app.services.task_listing import task_summary_projection
from app.services.task_workflow_context import task_workflow_read_store, task_workflow_source_store
from app.services.version_status import build_version_advance_impact

VERSION_NEXT_STATUS = {
    "active": "testing",
    "planning": "active",
    "testing": "released",
}
OPEN_BUG_STATUSES = {"assigned", "fixed", "needs_info", "open", "reopened", "triaged"}
SEVERE_BUG_SEVERITIES = {"blocker", "critical"}
SEVERE_CODE_RISKS = {"critical", "high"}
PENDING_CODE_REVIEW_STATUSES = {"pending_review", "waiting_review"}
SEARCHABLE_KNOWLEDGE_INDEX_STATUSES = {"indexed", "text_indexed", "vector_indexed"}
VECTOR_READY_KNOWLEDGE_INDEX_STATUSES = {"indexed", "vector_indexed"}
BLOCKER_SEVERITY_PRIORITY = {
    "blocker": 1,
    "critical": 1,
    "high": 1,
    "medium": 2,
    "low": 3,
}
BLOCKER_SOURCE_PRIORITY = {
    "bug": 1,
    "jenkins_release": 2,
    "code_inspection_report": 3,
    "code_review_report": 4,
    "requirement": 5,
    "product_version_branch_config": 6,
}
BLOCKER_SOURCE_LABELS = {
    "bug": "Bug",
    "code_inspection_report": "代码巡检",
    "code_review_report": "代码评审",
    "jenkins_release": "发布记录",
    "product_version_branch_config": "代码分支",
    "requirement": "需求",
}
FULL_CHAIN_SUBJECT_TYPES = {
    "bug",
    "code_inspection_report",
    "code_review_report",
    "jenkins_release",
    "product_version",
    "product_version_branch_config",
    "requirement",
}


def _blocker_action_context(source_type: str) -> tuple[str, str]:
    if source_type == "requirement":
        return (
            "处理需求",
            "完成需求评审或推进需求状态，使其满足版本下一阶段准入条件。",
        )
    if source_type == "bug":
        return (
            "处理 Bug",
            "修复、验证并关闭 blocker/critical Bug 后解除发布阻塞。",
        )
    if source_type == "code_inspection_report":
        return (
            "治理巡检",
            "查看巡检详情，完成误报处理、风险接受或整改后重新扫描。",
        )
    if source_type == "code_review_report":
        return (
            "处理评审",
            "确认代码评审结论、补充整改或关闭待确认项后解除版本准入阻塞。",
        )
    if source_type == "jenkins_release":
        return (
            "排查发布",
            "排查失败或取消的发布记录，完成重新发布或登记成功发布。",
        )
    if source_type == "product_version_branch_config":
        return (
            "维护分支",
            "创建或推进版本分支状态，使其满足测试/发布准入要求。",
        )
    return ("查看对象", "打开关联对象并处理阻塞原因。")


def _dashboard_blocker(
    *,
    action_label: str | None = None,
    action_target_id: Any | None = None,
    action_target_type: str | None = None,
    blocker_id: Any,
    reason: str,
    resolution_hint: str | None = None,
    severity: str,
    source_type: str,
    title: Any,
) -> dict[str, Any]:
    default_action_label, default_resolution_hint = _blocker_action_context(source_type)
    blocker_id_text = str(blocker_id) if blocker_id is not None else None
    action_target_id_text = (
        str(action_target_id) if action_target_id is not None else blocker_id_text
    )
    return {
        "action_label": action_label or default_action_label,
        "action_target_id": action_target_id_text,
        "action_target_type": action_target_type or source_type,
        "id": blocker_id_text,
        "reason": reason,
        "resolution_hint": resolution_hint or default_resolution_hint,
        "severity": severity,
        "source_type": source_type,
        "title": title,
    }


def _blocker_sort_key(blocker: dict[str, Any]) -> tuple[int, int, str, str]:
    severity = str(blocker.get("severity") or "").lower()
    source_type = str(blocker.get("source_type") or "")
    return (
        BLOCKER_SEVERITY_PRIORITY.get(severity, 4),
        BLOCKER_SOURCE_PRIORITY.get(source_type, 99),
        str(blocker.get("title") or ""),
        str(blocker.get("action_target_id") or blocker.get("id") or ""),
    )


def _blocker_full_chain_subject(blocker: dict[str, Any]) -> tuple[str | None, str | None]:
    source_type = str(blocker.get("source_type") or "")
    blocker_id = blocker.get("id")
    if source_type in FULL_CHAIN_SUBJECT_TYPES and blocker_id:
        return source_type, str(blocker_id)
    target_type = str(blocker.get("action_target_type") or "")
    target_id = blocker.get("action_target_id")
    if target_type in FULL_CHAIN_SUBJECT_TYPES and target_id:
        return target_type, str(target_id)
    return None, None


def _version_next_actions(
    blockers: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    next_actions = []
    for index, blocker in enumerate(blockers[:limit], start=1):
        full_chain_subject_type, full_chain_subject_id = _blocker_full_chain_subject(blocker)
        source_type = str(blocker.get("source_type") or "")
        next_actions.append(
            {
                "action_label": blocker.get("action_label"),
                "action_target_id": blocker.get("action_target_id"),
                "action_target_type": blocker.get("action_target_type"),
                "full_chain_subject_id": full_chain_subject_id,
                "full_chain_subject_type": full_chain_subject_type,
                "id": blocker.get("id"),
                "priority": index,
                "reason": blocker.get("reason"),
                "resolution_hint": blocker.get("resolution_hint"),
                "severity": blocker.get("severity"),
                "source_label": BLOCKER_SOURCE_LABELS.get(source_type, source_type),
                "source_type": source_type,
                "title": blocker.get("title"),
            }
        )
    return next_actions


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _unique_labels(labels: list[str | None]) -> list[str]:
    result: list[str] = []
    for label in labels:
        if not label or label in result:
            continue
        result.append(label)
    return result


def _branch_quality_summary(
    branch_quality_governance: list[dict[str, Any]],
    summary: dict[str, int],
) -> dict[str, int]:
    def sum_field(field: str) -> int:
        return sum(_safe_int(item.get(field)) for item in branch_quality_governance)

    return {
        "accepted_risk_count": summary["branch_quality_accepted_risks"],
        "action_required_branch_count": summary["branch_quality_action_required"],
        "active_severe_finding_count": summary["branch_quality_active_severe_findings"],
        "expired_accepted_risk_count": summary["branch_quality_expired_accepted_risks"],
        "false_positive_count": summary["branch_quality_false_positives"],
        "pending_scan_branch_count": summary["branch_quality_pending_scan"],
        "pending_suppression_count": summary["branch_quality_pending_suppressions"],
        "quality_gate_failed_report_count": sum_field("quality_gate_failed_report_count"),
        "quality_gate_violation_count": sum_field("quality_gate_violation_count"),
        "uncovered_severe_bug_count": sum_field("uncovered_severe_bug_count"),
        "uncovered_severe_task_count": sum_field("uncovered_severe_task_count"),
    }


def _version_governance_conclusion(
    *,
    blockers: list[dict[str, Any]],
    branch_quality_governance: list[dict[str, Any]],
    status_impact: dict[str, Any] | None,
    summary: dict[str, int],
) -> dict[str, Any]:
    branch_quality = _branch_quality_summary(branch_quality_governance, summary)
    blocker_count = summary["blockers"] or len(blockers)
    severe_risk_count = (
        summary["severe_bugs"]
        + summary["severe_code_inspection_reports"]
        + branch_quality["active_severe_finding_count"]
    )
    pending_code_review_count = summary["pending_code_review_reports"]
    blocked_requirement_count = (
        len(status_impact.get("blocked_requirements") or []) if status_impact else 0
    )
    has_knowledge_gap = (
        summary["knowledge_deposits"] > 0
        and summary["searchable_knowledge_deposits"] < summary["knowledge_deposits"]
    )
    has_delivery_evidence_gap = (
        not summary["branch_configs"]
        or not summary["code_inspection_reports"]
        or not summary["code_review_reports"]
        or not summary["knowledge_deposits"]
    )
    risk_labels = _unique_labels(
        [
            f"发布阻塞 {blocker_count}" if blocker_count else None,
            f"未关闭 Bug {summary['open_bugs']}" if summary["open_bugs"] else None,
            f"严重质量风险 {severe_risk_count}" if severe_risk_count else None,
            (
                f"门禁失败 {branch_quality['quality_gate_failed_report_count']}"
                if branch_quality["quality_gate_failed_report_count"]
                else None
            ),
            (
                f"待治理分支 {branch_quality['action_required_branch_count']}"
                if branch_quality["action_required_branch_count"]
                else None
            ),
            (
                f"待审批忽略 {branch_quality['pending_suppression_count']}"
                if branch_quality["pending_suppression_count"]
                else None
            ),
            (
                f"到期接受风险 {branch_quality['expired_accepted_risk_count']}"
                if branch_quality["expired_accepted_risk_count"]
                else None
            ),
            (
                f"待确认评审 {pending_code_review_count}"
                if pending_code_review_count
                else None
            ),
            (
                f"状态推进阻塞 {blocked_requirement_count}"
                if blocked_requirement_count
                else None
            ),
            "知识索引未全部可检索" if has_knowledge_gap else None,
        ]
    )

    if blocker_count:
        return {
            "detail": (
                f"当前版本有 {blocker_count} 个发布阻塞项，未关闭 Bug {summary['open_bugs']} 个，"
                f"门禁失败 {branch_quality['quality_gate_failed_report_count']} 份，"
                f"状态推进阻塞需求 {blocked_requirement_count} 条。"
            ),
            "level": "error",
            "next_action": "先处理阻塞队列中的 Bug、发布记录和分支问题，再重新查看推进影响。",
            "risks": risk_labels,
            "title": "版本治理结论",
            "value": "版本暂不建议推进",
        }

    if (
        severe_risk_count
        or branch_quality["quality_gate_failed_report_count"]
        or branch_quality["action_required_branch_count"]
        or branch_quality["expired_accepted_risk_count"]
        or summary["open_bugs"]
    ):
        return {
            "detail": (
                f"严重质量风险 {severe_risk_count} 个，"
                f"待治理分支 {branch_quality['action_required_branch_count']} 个，"
                f"到期接受风险 {branch_quality['expired_accepted_risk_count']} 个，"
                f"未关闭 Bug {summary['open_bugs']} 个。"
            ),
            "level": "warning",
            "next_action": "先完成质量门禁、严重巡检和 Bug 收敛，再推进版本状态。",
            "risks": risk_labels,
            "title": "版本治理结论",
            "value": "版本需治理后推进",
        }

    has_review_or_evidence_gap = (
        pending_code_review_count
        or blocked_requirement_count
        or has_knowledge_gap
        or has_delivery_evidence_gap
    )
    if has_review_or_evidence_gap:
        return {
            "detail": (
                f"待确认评审 {pending_code_review_count} 份，"
                f"状态推进阻塞需求 {blocked_requirement_count} 条，交付证据覆盖："
                f"分支 {summary['branch_configs']}、巡检 {summary['code_inspection_reports']}、"
                f"评审 {summary['code_review_reports']}、知识 {summary['knowledge_deposits']}。"
            ),
            "level": "warning",
            "next_action": "补齐待确认评审、知识索引或交付证据后，再执行版本推进。",
            "risks": risk_labels or ["交付证据待补齐"],
            "title": "版本治理结论",
            "value": "版本证据待补齐",
        }

    return {
        "detail": (
            f"需求 {summary['requirements']} 条，任务 {summary['tasks']} 个，"
            f"分支 {summary['branch_configs']} 个，巡检 {summary['code_inspection_reports']} 份，"
            f"知识沉淀 {summary['knowledge_deposits']} 条。"
        ),
        "level": "success",
        "next_action": (
            "可按状态推进预览继续操作。"
            if status_impact
            else "当前状态暂无下一阶段，可继续观察交付健康。"
        ),
        "risks": ["暂无关键阻塞"],
        "title": "版本治理结论",
        "value": "版本具备推进基础",
    }


def _delivery_stage(
    *,
    action_label: str | None = None,
    action_target_id: Any | None = None,
    action_target_type: str | None = None,
    detail: str,
    full_chain_subject_id: Any | None = None,
    full_chain_subject_type: str | None = None,
    key: str,
    level: str,
    title: str,
    value: str,
) -> dict[str, Any]:
    return {
        "action_label": action_label,
        "action_target_id": str(action_target_id) if action_target_id else None,
        "action_target_type": action_target_type,
        "detail": detail,
        "full_chain_subject_id": str(full_chain_subject_id) if full_chain_subject_id else None,
        "full_chain_subject_type": full_chain_subject_type,
        "key": key,
        "level": level,
        "title": title,
        "value": value,
    }


def _delivery_stage_overview(
    *,
    blockers: list[dict[str, Any]],
    branch_configs: list[dict[str, Any]],
    branch_quality_governance: list[dict[str, Any]],
    bugs: list[dict[str, Any]],
    code_inspection_reports: list[dict[str, Any]],
    code_review_reports: list[dict[str, Any]],
    knowledge_deposits: list[dict[str, Any]],
    releases: list[dict[str, Any]],
    status_impact: dict[str, Any] | None,
    summary: dict[str, int],
    tasks: list[dict[str, Any]],
    version: dict[str, Any],
) -> list[dict[str, Any]]:
    branch_quality = _branch_quality_summary(branch_quality_governance, summary)
    blocked_requirement_count = (
        len(status_impact.get("blocked_requirements") or []) if status_impact else 0
    )
    running_task_count = sum(1 for task in tasks if task.get("status") == "running")
    not_created_branch_count = sum(
        1 for branch_config in branch_configs if branch_config.get("branch_status") == "not_created"
    )
    pending_scan_branch_count = summary["branch_quality_pending_scan"]
    action_required_branch_count = summary["branch_quality_action_required"]
    high_risk_inspection_count = sum(
        1
        for report in code_inspection_reports
        if str(report.get("risk_level") or "").lower() in {"blocker", *SEVERE_CODE_RISKS}
    )
    pending_code_review_count = summary["pending_code_review_reports"]
    release_blocker_count = sum(
        1 for blocker in blockers if blocker.get("source_type") == "jenkins_release"
    )
    successful_release_count = sum(1 for release in releases if _successful_release(release))
    failed_release_count = sum(1 for release in releases if _failed_release(release))
    latest_release = releases[0] if releases else {}
    latest_release_label = _release_label(latest_release) if latest_release else ""
    latest_release_time = _release_display_time(latest_release) if latest_release else ""
    first_branch_config = branch_configs[0] if branch_configs else {}
    first_code_review_report = code_review_reports[0] if code_review_reports else {}
    first_knowledge_deposit = knowledge_deposits[0] if knowledge_deposits else {}
    first_task = tasks[0] if tasks else {}
    version_id = version.get("id")
    product_id = version.get("product_id")
    branch_config_count = summary["branch_configs"]
    inspection_report_count = summary["code_inspection_reports"]
    knowledge_deposit_count = summary["knowledge_deposits"]
    searchable_knowledge_count = summary["searchable_knowledge_deposits"]
    vectorized_knowledge_count = summary["vectorized_knowledge_deposits"]
    release_count = summary["releases"]
    branch_has_pressure = (
        not_created_branch_count
        or action_required_branch_count
        or pending_scan_branch_count
    )
    inspection_gate_failed_count = branch_quality["quality_gate_failed_report_count"]
    pending_suppression_count = branch_quality["pending_suppression_count"]
    expired_accepted_risk_count = branch_quality["expired_accepted_risk_count"]
    inspection_has_detail_pressure = (
        action_required_branch_count
        or pending_scan_branch_count
        or inspection_gate_failed_count
        or pending_suppression_count
        or expired_accepted_risk_count
    )
    inspection_has_pressure = (
        high_risk_inspection_count
        or action_required_branch_count
        or pending_scan_branch_count
        or inspection_gate_failed_count
        or expired_accepted_risk_count
    )
    if not_created_branch_count:
        branch_detail = f"{branch_config_count} 个分支 · 未创建 {not_created_branch_count} 个"
    elif action_required_branch_count or pending_scan_branch_count:
        branch_detail = (
            f"{branch_config_count} 个分支 · "
            f"待治理 {action_required_branch_count} 个 · "
            f"待巡检 {pending_scan_branch_count} 个"
        )
    else:
        branch_detail = f"{branch_config_count} 个分支 · 已登记"
    if high_risk_inspection_count:
        inspection_detail = (
            f"{inspection_report_count} 份报告 · 高风险 {high_risk_inspection_count} 份"
        )
    elif inspection_has_detail_pressure:
        inspection_detail = (
            f"{inspection_report_count} 份报告 · "
            f"待治理分支 {action_required_branch_count} 个 · "
            f"待巡检 {pending_scan_branch_count} 个 · "
            f"门禁失败 {inspection_gate_failed_count} 份 · "
            f"待审批忽略 {pending_suppression_count} 个 · "
            f"到期风险 {expired_accepted_risk_count} 个"
        )
    else:
        inspection_detail = f"{inspection_report_count} 份报告 · 暂无高风险"
    code_review_action_target_id = (
        first_code_review_report.get("id") or first_task.get("id") or product_id
    )
    code_review_full_chain_subject_id = (
        first_code_review_report.get("id") or first_task.get("requirement_id")
    )
    knowledge_action_target_type = (
        "knowledge_deposit" if first_knowledge_deposit.get("id") else "product_version"
    )
    if knowledge_deposit_count:
        knowledge_detail = (
            f"{knowledge_deposit_count} 条知识沉淀 · "
            f"可检索 {searchable_knowledge_count} 条 · "
            f"向量就绪 {vectorized_knowledge_count} 条"
        )
    else:
        knowledge_detail = "暂无知识沉淀，发布前建议沉淀关键设计、巡检和整改经验"
    release_detail_parts = [
        f"{release_count} 条记录",
        f"发布阻塞 {release_blocker_count} 个" if release_blocker_count else "暂无发布阻塞",
        f"成功 {successful_release_count} 条",
        f"失败 {failed_release_count} 条",
    ]
    if latest_release:
        release_detail_parts.append(
            f"最近 {latest_release_label} · {latest_release_time or '-'}"
        )
    release_detail = " · ".join(release_detail_parts)

    return [
        _delivery_stage(
            action_label="处理需求" if blocked_requirement_count else "查看需求",
            action_target_id=version_id,
            action_target_type="requirements",
            detail=(
                f"{summary['requirements']} 条需求 · 阻塞 {blocked_requirement_count} 条"
                if blocked_requirement_count
                else f"{summary['requirements']} 条需求 · 可推进"
            ),
            key="requirements",
            level="warning" if blocked_requirement_count else "success",
            title="需求范围",
            value="范围有阻塞" if blocked_requirement_count else "范围可推进",
        ),
        _delivery_stage(
            action_label="查看任务",
            action_target_id=first_task.get("id") or product_id,
            action_target_type="ai_task" if first_task.get("id") else "tasks_by_product",
            detail=(
                f"{summary['tasks']} 个任务 · 运行中 {running_task_count} 个"
                if running_task_count
                else f"{summary['tasks']} 个任务 · 暂无运行中"
            ),
            full_chain_subject_id=first_task.get("requirement_id") or version_id,
            full_chain_subject_type=(
                "requirement" if first_task.get("requirement_id") else "product_version"
            ),
            key="tasks",
            level="info" if running_task_count else "success",
            title="研发任务",
            value="任务进行中" if running_task_count else "任务稳定",
        ),
        _delivery_stage(
            action_label="处理分支",
            action_target_id=first_branch_config.get("id") or version_id,
            action_target_type=(
                "product_version_branch_config"
                if first_branch_config.get("id")
                else "product_version"
            ),
            detail=branch_detail,
            full_chain_subject_id=first_branch_config.get("id") or version_id,
            full_chain_subject_type=(
                "product_version_branch_config"
                if first_branch_config.get("id")
                else "product_version"
            ),
            key="branches",
            level="warning" if branch_has_pressure else "success",
            title="代码分支",
            value=(
                "分支待维护"
                if not_created_branch_count
                else (
                    "分支质量待治理"
                    if action_required_branch_count or pending_scan_branch_count
                    else "分支就绪"
                )
            ),
        ),
        _delivery_stage(
            action_label="查看巡检",
            action_target_id=version_id,
            action_target_type="code_inspection_dashboard",
            detail=inspection_detail,
            key="inspections",
            level="warning" if inspection_has_pressure else "success",
            title="代码巡检",
            value="质量待治理" if inspection_has_pressure else "质量可控",
        ),
        _delivery_stage(
            action_label="处理评审" if pending_code_review_count else "查看评审",
            action_target_id=code_review_action_target_id,
            action_target_type=(
                "code_review_report"
                if first_code_review_report.get("id")
                else "ai_task"
                if first_task.get("id")
                else "tasks_by_product"
            ),
            detail=(
                f"{summary['code_review_reports']} 份报告 · 待确认 {pending_code_review_count} 份"
                if pending_code_review_count
                else f"{summary['code_review_reports']} 份报告 · 暂无待确认"
            ),
            full_chain_subject_id=code_review_full_chain_subject_id,
            full_chain_subject_type=(
                "code_review_report"
                if first_code_review_report.get("id")
                else "requirement"
                if first_task.get("requirement_id")
                else None
            ),
            key="code-reviews",
            level="warning" if pending_code_review_count else "success",
            title="代码评审",
            value="评审待确认" if pending_code_review_count else "评审已收敛",
        ),
        _delivery_stage(
            action_label="处理版本 Bug" if summary["open_bugs"] else "查看版本 Bug",
            action_target_id=version_id,
            action_target_type="bugs",
            detail=(
                f"{summary['bugs']} 个 Bug · 未关闭 {summary['open_bugs']} 个"
                if summary["open_bugs"]
                else f"{summary['bugs']} 个 Bug · 已收敛"
            ),
            full_chain_subject_id=(bugs[0] or {}).get("id") if bugs else version_id,
            full_chain_subject_type="bug" if bugs else "product_version",
            key="bugs",
            level="error" if summary["open_bugs"] else "success",
            title="Bug 收敛",
            value="Bug 待关闭" if summary["open_bugs"] else "Bug 已收敛",
        ),
        _delivery_stage(
            action_label="查看沉淀",
            action_target_id=first_knowledge_deposit.get("id") or version_id,
            action_target_type=knowledge_action_target_type,
            detail=knowledge_detail,
            full_chain_subject_id=first_knowledge_deposit.get("id") or version_id,
            full_chain_subject_type=knowledge_action_target_type,
            key="knowledge-deposits",
            level=(
                "warning"
                if knowledge_deposit_count and not searchable_knowledge_count
                else "success"
                if knowledge_deposit_count
                else "info"
            ),
            title="知识沉淀",
            value=(
                f"{searchable_knowledge_count}/{knowledge_deposit_count} 可检索"
                if knowledge_deposit_count
                else "沉淀待补齐"
            ),
        ),
        _delivery_stage(
            action_label="补充发布" if release_blocker_count else "查看发布",
            action_target_id=version_id,
            action_target_type="releases",
            detail=release_detail,
            key="releases",
            level="error" if release_blocker_count else "success",
            title="发布证据",
            value="发布待补证" if release_blocker_count else "发布证据可用",
        ),
        _delivery_stage(
            action_label="推进状态" if status_impact else None,
            action_target_id=version_id,
            action_target_type="product_version_advance" if status_impact else None,
            detail=(
                f"同步 {len(status_impact.get('updated_requirements') or [])} / "
                f"阻塞 {len(status_impact.get('blocked_requirements') or [])} / "
                f"保持 {len(status_impact.get('unchanged_requirements') or [])}"
                if status_impact
                else "当前版本没有可推进的下一阶段"
            ),
            full_chain_subject_id=version_id,
            full_chain_subject_type="product_version",
            key="status-impact",
            level=(
                "warning"
                if status_impact and status_impact.get("blocked_requirements")
                else "success"
                if status_impact
                else "info"
            ),
            title="状态推进",
            value="已预览影响" if status_impact else "无需推进",
        ),
    ]


def _evidence_domain(
    *,
    action_label: str | None = None,
    action_target_id: Any | None = None,
    action_target_type: str | None = None,
    detail: str,
    key: str,
    level: str,
    status: str,
    title: str,
    value: str,
) -> dict[str, Any]:
    return {
        "action_label": action_label,
        "action_target_id": str(action_target_id) if action_target_id else None,
        "action_target_type": action_target_type,
        "detail": detail,
        "key": key,
        "level": level,
        "status": status,
        "title": title,
        "value": value,
    }


def _access_issue_sections(access_issues: list[dict[str, str]]) -> set[str]:
    return {str(issue.get("section") or "") for issue in access_issues}


def _version_evidence_coverage(
    *,
    access_issues: list[dict[str, str]],
    blockers: list[dict[str, Any]],
    status_impact: dict[str, Any] | None,
    summary: dict[str, int],
    version_id: str,
) -> dict[str, Any]:
    blocker_sources = {str(blocker.get("source_type") or "") for blocker in blockers}
    inaccessible_sections = _access_issue_sections(access_issues)
    blocked_requirement_count = (
        len(status_impact.get("blocked_requirements") or []) if status_impact else 0
    )
    updated_requirement_count = (
        len(status_impact.get("updated_requirements") or []) if status_impact else 0
    )
    target_status = str(status_impact.get("target_status") or "") if status_impact else ""

    domains: list[dict[str, Any]] = [
        _evidence_domain(
            action_label="查看需求",
            action_target_id=version_id,
            action_target_type="requirements",
            detail=(
                f"{summary['requirements']} 条需求 · 状态推进阻塞 {blocked_requirement_count} 条"
                if summary["requirements"]
                else "版本尚未归集需求，无法确认交付范围"
            ),
            key="requirements",
            level=(
                "error"
                if blocked_requirement_count
                else "success"
                if summary["requirements"]
                else "warning"
            ),
            status=(
                "blocked"
                if blocked_requirement_count
                else "covered"
                if summary["requirements"]
                else "missing"
            ),
            title="需求范围",
            value=(
                f"{summary['requirements']} 条"
                if summary["requirements"]
                else "范围待归集"
            ),
        ),
        _evidence_domain(
            action_label="查看任务",
            action_target_id=version_id,
            action_target_type="tasks_by_version",
            detail=(
                f"{summary['tasks']} 个研发任务"
                if summary["tasks"]
                else "版本下暂无研发任务，难以判断实际开发进展"
            ),
            key="tasks",
            level="success" if summary["tasks"] else "warning",
            status="covered" if summary["tasks"] else "missing",
            title="研发任务",
            value=f"{summary['tasks']} 个" if summary["tasks"] else "任务待生成",
        ),
        _evidence_domain(
            action_label="维护分支",
            action_target_id=version_id,
            action_target_type="product_version",
            detail=(
                f"{summary['branch_configs']} 个版本分支 · "
                f"待治理 {summary['branch_quality_action_required']} 个"
                if summary["branch_configs"]
                else "未配置版本分支，无法串联代码巡检和发布准入"
            ),
            key="branches",
            level=(
                "error"
                if "product_version_branch_config" in blocker_sources
                else "warning"
                if summary["branch_quality_action_required"] or not summary["branch_configs"]
                else "success"
            ),
            status=(
                "blocked"
                if "product_version_branch_config" in blocker_sources
                else "risk"
                if summary["branch_quality_action_required"]
                else "covered"
                if summary["branch_configs"]
                else "missing"
            ),
            title="代码分支",
            value=(
                f"{summary['branch_configs']} 个"
                if summary["branch_configs"]
                else "分支待配置"
            ),
        ),
    ]

    if "code_inspections" in inaccessible_sections:
        domains.append(
            _evidence_domain(
                action_label="申请权限",
                action_target_id=version_id,
                action_target_type="product_version",
                detail="缺少代码巡检读取权限，无法判断分支质量、门禁和风险治理状态",
                key="inspections",
                level="warning",
                status="inaccessible",
                title="代码巡检",
                value="权限不足",
            )
        )
    else:
        domains.append(
            _evidence_domain(
                action_label="查看巡检",
                action_target_id=version_id,
                action_target_type="code_inspection_dashboard",
                detail=(
                    f"{summary['code_inspection_reports']} 份报告 · "
                    f"严重风险 {summary['severe_code_inspection_reports']} 份"
                    if summary["code_inspection_reports"]
                    else "暂无代码巡检报告，建议至少完成一次版本分支扫描"
                ),
                key="inspections",
                level=(
                    "error"
                    if "code_inspection_report" in blocker_sources
                    else "success"
                    if summary["code_inspection_reports"]
                    else "warning"
                ),
                status=(
                    "blocked"
                    if "code_inspection_report" in blocker_sources
                    else "covered"
                    if summary["code_inspection_reports"]
                    else "missing"
                ),
                title="代码巡检",
                value=(
                    f"{summary['code_inspection_reports']} 份"
                    if summary["code_inspection_reports"]
                    else "巡检待补齐"
                ),
            )
        )

    domains.extend(
        [
            _evidence_domain(
                action_label="查看评审",
                action_target_id=version_id,
                action_target_type="code_review_reports_by_version",
                detail=(
                    f"{summary['code_review_reports']} 份评审 · "
                    f"待确认 {summary['pending_code_review_reports']} 份"
                    if summary["code_review_reports"]
                    else "暂无代码评审报告，版本质量证据不完整"
                ),
                key="code-reviews",
                level=(
                    "error"
                    if "code_review_report" in blocker_sources
                    else "warning"
                    if summary["pending_code_review_reports"] or not summary["code_review_reports"]
                    else "success"
                ),
                status=(
                    "blocked"
                    if "code_review_report" in blocker_sources
                    else "risk"
                    if summary["pending_code_review_reports"]
                    else "covered"
                    if summary["code_review_reports"]
                    else "missing"
                ),
                title="代码评审",
                value=(
                    f"{summary['code_review_reports']} 份"
                    if summary["code_review_reports"]
                    else "评审待补齐"
                ),
            ),
        ]
    )

    if "bugs" in inaccessible_sections:
        domains.append(
            _evidence_domain(
                action_label="申请权限",
                action_target_id=version_id,
                action_target_type="product_version",
                detail="缺少 Bug 读取权限，无法确认缺陷收敛状态",
                key="bugs",
                level="warning",
                status="inaccessible",
                title="Bug 收敛",
                value="权限不足",
            )
        )
    else:
        domains.append(
            _evidence_domain(
                action_label="查看 Bug",
                action_target_id=version_id,
                action_target_type="bugs",
                detail=(
                    f"{summary['bugs']} 个 Bug · 未关闭 {summary['open_bugs']} 个 · "
                    f"严重 {summary['severe_bugs']} 个"
                ),
                key="bugs",
                level=(
                    "error"
                    if "bug" in blocker_sources
                    else "warning"
                    if summary["open_bugs"]
                    else "success"
                ),
                status=(
                    "blocked"
                    if "bug" in blocker_sources
                    else "risk"
                    if summary["open_bugs"]
                    else "covered"
                ),
                title="Bug 收敛",
                value=f"{summary['open_bugs']} 未关闭",
            )
        )

    if "knowledge_deposits" in inaccessible_sections:
        domains.append(
            _evidence_domain(
                action_label="申请权限",
                action_target_id=version_id,
                action_target_type="product_version",
                detail="缺少知识读取权限，无法确认知识沉淀和索引状态",
                key="knowledge-deposits",
                level="warning",
                status="inaccessible",
                title="知识沉淀",
                value="权限不足",
            )
        )
    else:
        knowledge_gap = (
            summary["knowledge_deposits"] <= 0
            or summary["searchable_knowledge_deposits"] < summary["knowledge_deposits"]
        )
        domains.append(
            _evidence_domain(
                action_label="查看沉淀",
                action_target_id=version_id,
                action_target_type="knowledge_deposits_by_version",
                detail=(
                    f"{summary['knowledge_deposits']} 条沉淀 · "
                    f"可检索 {summary['searchable_knowledge_deposits']} 条 · "
                    f"向量就绪 {summary['vectorized_knowledge_deposits']} 条"
                    if summary["knowledge_deposits"]
                    else "暂无知识沉淀，发布前建议沉淀设计、巡检和整改经验"
                ),
                key="knowledge-deposits",
                level="warning" if knowledge_gap else "success",
                status=(
                    "risk"
                    if knowledge_gap and summary["knowledge_deposits"]
                    else "missing"
                    if knowledge_gap
                    else "covered"
                ),
                title="知识沉淀",
                value=(
                    f"{summary['searchable_knowledge_deposits']}/"
                    f"{summary['knowledge_deposits']} 可检索"
                    if summary["knowledge_deposits"]
                    else "沉淀待补齐"
                ),
            )
        )

    domains.extend(
        [
            _evidence_domain(
                action_label="查看发布",
                action_target_id=version_id,
                action_target_type="releases",
                detail=(
                    f"{summary['releases']} 条发布记录 · "
                    f"成功 {summary['successful_releases']} 条 · "
                    f"失败 {summary['failed_releases']} 条"
                    if summary["releases"]
                    else "暂无发布记录，发布阶段无法确认上线证据"
                ),
                key="releases",
                level=(
                    "error"
                    if "jenkins_release" in blocker_sources
                    else "success"
                    if summary["successful_releases"]
                    else "warning"
                ),
                status=(
                    "blocked"
                    if "jenkins_release" in blocker_sources
                    else "covered"
                    if summary["successful_releases"]
                    else "missing"
                ),
                title="发布证据",
                value=(
                    f"{summary['successful_releases']} 成功"
                    if summary["successful_releases"]
                    else "发布待补证"
                ),
            ),
            _evidence_domain(
                action_label="推进状态" if status_impact else None,
                action_target_id=version_id if status_impact else None,
                action_target_type="product_version_advance" if status_impact else None,
                detail=(
                    f"目标 {target_status} · 同步 {updated_requirement_count} · "
                    f"阻塞 {blocked_requirement_count}"
                    if status_impact
                    else "当前版本状态没有可推进的下一阶段"
                ),
                key="status-impact",
                level=(
                    "error"
                    if blocked_requirement_count
                    else "success"
                    if status_impact
                    else "info"
                ),
                status=(
                    "blocked"
                    if blocked_requirement_count
                    else "covered"
                    if status_impact
                    else "not_applicable"
                ),
                title="状态推进",
                value=(
                    "推进受阻"
                    if blocked_requirement_count
                    else "影响已预览"
                    if status_impact
                    else "无需推进"
                ),
            ),
        ]
    )

    scored_domains = [domain for domain in domains if domain["status"] != "not_applicable"]
    total_domains = len(scored_domains)
    blocking_domains = sum(1 for domain in scored_domains if domain["level"] == "error")
    gap_domains = sum(
        1
        for domain in scored_domains
        if domain["status"] in {"inaccessible", "missing", "risk"}
    )
    covered_domains = sum(1 for domain in scored_domains if domain["status"] == "covered")
    score = int(round((covered_domains / total_domains) * 100)) if total_domains else 100
    level = "error" if blocking_domains else "warning" if gap_domains else "success"
    if blocking_domains:
        summary_text = f"{blocking_domains} 个交付域存在阻断，需先处理阻塞队列。"
    elif gap_domains:
        summary_text = f"{gap_domains} 个交付域证据待补齐，建议补证后再推进。"
    else:
        summary_text = "核心交付证据已覆盖，可结合状态推进影响继续操作。"

    return {
        "blocking_domains": blocking_domains,
        "covered_domains": covered_domains,
        "domains": domains,
        "gap_domains": gap_domains,
        "level": level,
        "score": score,
        "summary": summary_text,
        "total_domains": total_domains,
    }


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_memory_dict(current_store, collection_name).values())


def _version_dashboard_read_store(current_store: Any, version_id: str) -> Any:
    repository = getattr(current_store, "repository", None)
    load_rows = getattr(repository, "get_product_version_dashboard_source_rows", None)
    if callable(load_rows):
        return task_workflow_source_store(load_rows(version_id), repository=repository)
    return task_workflow_read_store(current_store)


def _has_permission(user: dict[str, Any], permission: str) -> bool:
    roles = set(user.get("roles") or [])
    permissions = set(user.get("permissions") or [])
    return "admin" in roles or "system.admin" in permissions or permission in permissions


def _public_branch_config(
    branch_config: dict[str, Any],
    current_store: Any,
) -> dict[str, Any]:
    repository = (
        get_product_git_repository_record(
            current_store,
            str(branch_config.get("repository_id") or ""),
        )
        or {}
    )
    return {
        **branch_config,
        "repository_default_branch": branch_config.get("repository_default_branch")
        or repository.get("default_branch"),
        "repository_name": branch_config.get("repository_name") or repository.get("name"),
        "repository_path": branch_config.get("repository_path") or repository.get("project_path"),
        "repository_provider": branch_config.get("repository_provider")
        or repository.get("git_provider"),
    }


def _branch_configs_for_version(
    current_store: Any,
    version_id: str,
) -> list[dict[str, Any]]:
    repository = product_config_query_repository(current_store)
    list_branch_configs = getattr(repository, "list_product_version_branch_configs", None)
    if callable(list_branch_configs):
        items = list_branch_configs(version_id)
    else:
        items = list_product_version_branch_config_records(current_store, version_id)
    result = [_public_branch_config(item, current_store) for item in items]
    result.sort(
        key=lambda item: (
            item.get("repository_name") or "",
            item.get("working_branch") or "",
        )
    )
    return result


def _status_counts(items: list[dict[str, Any]], field: str = "status") -> list[dict[str, Any]]:
    counts = Counter(str(item.get(field) or "-") for item in items)
    return [{"count": count, field: key} for key, count in sorted(counts.items())]


def _version_requirements(current_store: Any, version_id: str) -> list[dict[str, Any]]:
    requirements = [
        requirement_summary_projection(requirement, current_store)
        for requirement in _memory_records(current_store, "requirements")
        if requirement.get("version_id") == version_id
    ]
    requirements.sort(
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    return requirements


def _version_tasks(
    current_store: Any,
    *,
    requirement_ids: set[str],
    user: dict[str, Any],
    version_id: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for task in _memory_records(current_store, "ai_tasks"):
        if not can_read_task(user, task):
            continue
        if task.get("version_id") == version_id or task.get("requirement_id") in requirement_ids:
            tasks.append(task_summary_projection(task, current_store))
    tasks.sort(
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    return tasks


def _version_bugs(
    current_store: Any,
    *,
    code_inspection_reports: list[dict[str, Any]],
    requirement_ids: set[str],
    task_ids: set[str],
    user: dict[str, Any],
    version_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not _has_permission(user, "bug.read"):
        return [], [
            {
                "code": "bug.read",
                "message": "缺少 Bug 读取权限，版本驾驶舱已隐藏 Bug 明细。",
                "section": "bugs",
            }
        ]
    report_bug_ids = {
        str(bug_id)
        for report in code_inspection_reports
        for bug_id in (report.get("created_bug_ids") or [])
        if bug_id
    }
    bugs = [
        bug_summary_projection(bug, current_store)
        for bug in _memory_records(current_store, "bugs")
        if bug.get("version_id") == version_id
        or bug.get("requirement_id") in requirement_ids
        or bug.get("related_task_id") in task_ids
        or str(bug.get("id") or "") in report_bug_ids
    ]
    bugs.sort(
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    return bugs, []


def _version_code_inspection_reports(
    current_store: Any,
    *,
    branch_configs: list[dict[str, Any]],
    product_id: str,
    user: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not _has_permission(user, "code_inspection.read"):
        return [], [
            {
                "code": "code_inspection.read",
                "message": "缺少代码巡检读取权限，版本驾驶舱已隐藏代码巡检明细。",
                "section": "code_inspections",
            }
        ]
    branch_keys = {
        (config.get("repository_id"), config.get("working_branch"))
        for config in branch_configs
        if config.get("repository_id") and config.get("working_branch")
    }
    reports: list[dict[str, Any]] = []
    for report in _memory_records(current_store, "code_inspection_reports"):
        if report.get("product_id") != product_id:
            continue
        if branch_keys:
            report_key = (report.get("repository_id"), report.get("branch"))
            if report_key not in branch_keys:
                continue
        reports.append(dict(report))
    reports.sort(
        key=lambda item: item.get("created_at") or item.get("scan_finished_at") or "",
        reverse=True,
    )
    return reports, []


def _public_code_review_report(
    report: dict[str, Any],
    *,
    task: dict[str, Any] | None,
) -> dict[str, Any]:
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    return {
        "archived_at": report.get("archived_at"),
        "executor": report.get("executor") if isinstance(report.get("executor"), dict) else {},
        "finding_count": len(findings),
        "gitlab_mr_snapshot_id": report.get("gitlab_mr_snapshot_id"),
        "gitlab_writeback_performed": bool(report.get("gitlab_writeback_performed")),
        "id": report.get("id"),
        "review_id": report.get("review_id"),
        "risk_level": report.get("risk_level") or "medium",
        "status": report.get("status") or "-",
        "summary": report.get("summary") or report.get("id"),
        "task_id": report.get("task_id"),
        "task_title": (task or {}).get("title"),
    }


def _version_code_review_reports(
    current_store: Any,
    *,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    task_by_id = {str(task["id"]): task for task in tasks if task.get("id")}
    linked_report_ids = {
        str(task.get("code_review_report_id"))
        for task in tasks
        if task.get("code_review_report_id")
    }
    reports: list[dict[str, Any]] = []
    for report in _memory_records(current_store, "code_review_reports"):
        report_id = str(report.get("id") or "")
        task_id = str(report.get("task_id") or "")
        if report_id not in linked_report_ids and task_id not in task_by_id:
            continue
        reports.append(_public_code_review_report(report, task=task_by_id.get(task_id)))
    reports.sort(
        key=lambda item: (
            item.get("archived_at") or "",
            item.get("id") or "",
        ),
        reverse=True,
    )
    return reports


def _version_releases(current_store: Any, version_id: str) -> list[dict[str, Any]]:
    releases = [
        dict(release)
        for release in _memory_records(current_store, "jenkins_release_records")
        if release.get("version_id") == version_id
    ]
    releases.sort(
        key=lambda item: (
            item.get("deployed_at") or item.get("started_at") or item.get("created_at") or ""
        ),
        reverse=True,
    )
    return releases


def _public_knowledge_deposit(
    deposit: dict[str, Any],
    *,
    chunk_counts: dict[str, int] | None,
    document: dict[str, Any] | None,
    task: dict[str, Any] | None,
) -> dict[str, Any]:
    document_id = str(deposit.get("knowledge_document_id") or "")
    index_status = (
        document.get("index_status") if document is not None else "missing" if document_id else None
    )
    chunk_count = int((chunk_counts or {}).get("total_chunks") or 0)
    embedding_chunk_count = int((chunk_counts or {}).get("embedding_chunks") or 0)
    retrieval_mode = _knowledge_retrieval_mode(
        chunk_count=chunk_count,
        embedding_chunk_count=embedding_chunk_count,
        index_status=str(index_status or ""),
    )
    return {
        "ai_task_id": deposit.get("ai_task_id"),
        "id": deposit.get("id"),
        "knowledge_chunk_count": chunk_count,
        "knowledge_document_id": deposit.get("knowledge_document_id"),
        "knowledge_document_title": (document or {}).get("title"),
        "knowledge_embedding_chunk_count": embedding_chunk_count,
        "knowledge_index_error": (document or {}).get("index_error")
        or (document or {}).get("vector_index_error"),
        "knowledge_index_status": index_status,
        "knowledge_retrieval_mode": retrieval_mode,
        "status": deposit.get("status") or "-",
        "task_title": (task or {}).get("title"),
        "title": deposit.get("title") or deposit.get("id"),
        "updated_at": deposit.get("updated_at") or deposit.get("created_at"),
    }


def _knowledge_chunk_counts(
    current_store: Any,
    *,
    active_chunk_set_id: str | None,
    document_id: str,
) -> dict[str, int]:
    total_chunks = 0
    embedding_chunks = 0
    for chunk in _memory_records(current_store, "knowledge_chunks"):
        if chunk.get("document_id") != document_id:
            continue
        if active_chunk_set_id and chunk.get("chunk_set_id") != active_chunk_set_id:
            continue
        total_chunks += 1
        if chunk.get("embedding") is not None:
            embedding_chunks += 1
    return {
        "embedding_chunks": embedding_chunks,
        "total_chunks": total_chunks,
    }


def _knowledge_retrieval_mode(
    *,
    chunk_count: int,
    embedding_chunk_count: int,
    index_status: str,
) -> str:
    if index_status not in SEARCHABLE_KNOWLEDGE_INDEX_STATUSES or chunk_count <= 0:
        return "unavailable"
    if index_status in VECTOR_READY_KNOWLEDGE_INDEX_STATUSES and embedding_chunk_count > 0:
        return "hybrid"
    return "keyword"


def _version_knowledge_deposits(
    current_store: Any,
    *,
    tasks: list[dict[str, Any]],
    user: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not _has_permission(user, "knowledge.read"):
        return [], [
            {
                "code": "knowledge.read",
                "message": "缺少知识读取权限，版本驾驶舱已隐藏知识沉淀明细。",
                "section": "knowledge_deposits",
            }
        ]
    task_by_id = {str(task["id"]): task for task in tasks if task.get("id")}
    document_by_id = {
        str(document["id"]): document
        for document in _memory_records(current_store, "knowledge_documents")
        if document.get("id")
    }
    deposits = [
        _public_knowledge_deposit(
            deposit,
            chunk_counts=_knowledge_chunk_counts(
                current_store,
                active_chunk_set_id=(
                    document_by_id.get(str(deposit.get("knowledge_document_id") or "")) or {}
                ).get("active_chunk_set_id"),
                document_id=str(deposit.get("knowledge_document_id") or ""),
            ),
            document=document_by_id.get(str(deposit.get("knowledge_document_id") or "")),
            task=task_by_id.get(str(deposit.get("ai_task_id") or "")),
        )
        for deposit in _memory_records(current_store, "knowledge_deposits")
        if str(deposit.get("ai_task_id") or "") in task_by_id
    ]
    deposits.sort(
        key=lambda item: item.get("updated_at") or "",
        reverse=True,
    )
    return deposits, []


def _quality_gate_failed(report: dict[str, Any]) -> bool:
    quality_gate = report.get("quality_gate")
    if not isinstance(quality_gate, dict):
        return False
    return str(quality_gate.get("status") or "").lower() == "failed"


def _quality_gate_violation_count(report: dict[str, Any]) -> int:
    quality_gate = report.get("quality_gate")
    if not isinstance(quality_gate, dict):
        return 0
    violations = quality_gate.get("violations")
    if not isinstance(violations, list):
        return 0
    return sum(1 for violation in violations if isinstance(violation, dict))


def _parse_optional_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _accepted_risk_is_expired(finding: dict[str, Any]) -> bool:
    if finding.get("suppression_status") != "approved":
        return False
    if finding.get("suppression_reason") != "accepted_risk":
        return False
    expires_at = _parse_optional_datetime(finding.get("suppression_expires_at"))
    if expires_at is None:
        return False
    return expires_at <= datetime.now(UTC)


def _suppression_is_effective(finding: dict[str, Any]) -> bool:
    return finding.get("suppression_status") == "approved" and not _accepted_risk_is_expired(
        finding
    )


def _code_inspection_findings_by_report(
    code_inspection_findings: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    findings_by_report: dict[str, list[dict[str, Any]]] = {}
    for finding in code_inspection_findings:
        report_id = str(finding.get("report_id") or "")
        if not report_id:
            continue
        findings_by_report.setdefault(report_id, []).append(finding)
    return findings_by_report


def _finding_governance_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "accepted_risk_count": 0,
        "active_severe_finding_count": 0,
        "active_severe_bug_covered_count": 0,
        "active_severe_task_covered_count": 0,
        "expired_accepted_risk_count": 0,
        "false_positive_count": 0,
        "pending_suppression_count": 0,
        "suppressed_finding_count": 0,
    }
    for finding in findings:
        suppression_status = str(finding.get("suppression_status") or "none")
        suppression_reason = str(finding.get("suppression_reason") or "")
        if suppression_status == "pending":
            counts["pending_suppression_count"] += 1
        if suppression_status == "approved":
            counts["suppressed_finding_count"] += 1
            if suppression_reason == "false_positive":
                counts["false_positive_count"] += 1
            if suppression_reason == "accepted_risk":
                counts["accepted_risk_count"] += 1
                if _accepted_risk_is_expired(finding):
                    counts["expired_accepted_risk_count"] += 1
        is_active_severe_finding = (
            str(finding.get("severity") or "").lower() in SEVERE_CODE_RISKS
            and not _suppression_is_effective(finding)
        )
        if is_active_severe_finding:
            counts["active_severe_finding_count"] += 1
            if finding.get("created_bug_id"):
                counts["active_severe_bug_covered_count"] += 1
            if finding.get("created_task_id"):
                counts["active_severe_task_covered_count"] += 1
    return counts


def _suppression_summary_count(report: dict[str, Any], key: str) -> int:
    suppression_summary = report.get("suppression_summary")
    if not isinstance(suppression_summary, dict):
        return 0
    try:
        return int(suppression_summary.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _report_sort_key(report: dict[str, Any]) -> str:
    return str(
        report.get("scan_finished_at")
        or report.get("updated_at")
        or report.get("created_at")
        or ""
    )


def _version_branch_quality_governance(
    *,
    branch_configs: list[dict[str, Any]],
    code_inspection_findings: list[dict[str, Any]],
    code_inspection_reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings_by_report = _code_inspection_findings_by_report(code_inspection_findings)
    branch_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for config in branch_configs:
        repository_id = str(config.get("repository_id") or "")
        branch = str(config.get("working_branch") or "")
        if not repository_id or not branch:
            continue
        branch_rows[(repository_id, branch)] = {
            "_latest_report_sort_key": "",
            "branch": branch,
            "branch_config_id": config.get("id"),
            "accepted_risk_count": 0,
            "active_severe_finding_count": 0,
            "created_bug_count": 0,
            "created_task_count": 0,
            "expired_accepted_risk_count": 0,
            "false_positive_count": 0,
            "finding_count": 0,
            "id": str(config.get("id") or f"{repository_id}:{branch}"),
            "latest_report_id": None,
            "latest_report_summary": None,
            "latest_report_time": None,
            "quality_gate_failed_report_count": 0,
            "quality_gate_violation_count": 0,
            "report_count": 0,
            "repository_id": repository_id,
            "repository_name": config.get("repository_name") or repository_id,
            "severe_finding_count": 0,
            "status": "pending_scan",
            "suppressed_finding_count": 0,
            "pending_suppression_count": 0,
            "uncovered_severe_bug_count": 0,
            "uncovered_severe_task_count": 0,
        }

    for report in code_inspection_reports:
        repository_id = str(report.get("repository_id") or "")
        branch = str(report.get("branch") or "")
        if not repository_id or not branch:
            continue
        row = branch_rows.setdefault(
            (repository_id, branch),
            {
                "_latest_report_sort_key": "",
                "accepted_risk_count": 0,
                "active_severe_finding_count": 0,
                "branch": branch,
                "branch_config_id": None,
                "created_bug_count": 0,
                "created_task_count": 0,
                "expired_accepted_risk_count": 0,
                "false_positive_count": 0,
                "finding_count": 0,
                "id": f"{repository_id}:{branch}",
                "latest_report_id": None,
                "latest_report_summary": None,
                "latest_report_time": None,
                "quality_gate_failed_report_count": 0,
                "quality_gate_violation_count": 0,
                "report_count": 0,
                "repository_id": repository_id,
                "repository_name": report.get("repository_name") or repository_id,
                "severe_finding_count": 0,
                "status": "pending_scan",
                "suppressed_finding_count": 0,
                "pending_suppression_count": 0,
                "uncovered_severe_bug_count": 0,
                "uncovered_severe_task_count": 0,
            },
        )
        finding_count = int(report.get("finding_count") or 0)
        severe_finding_count = int(report.get("severe_finding_count") or 0)
        created_bug_count = len(report.get("created_bug_ids") or [])
        created_task_count = len(report.get("created_task_ids") or [])
        report_findings = findings_by_report.get(str(report.get("id") or ""), [])
        finding_governance = _finding_governance_counts(report_findings)
        active_severe_finding_count = (
            finding_governance["active_severe_finding_count"]
            if report_findings
            else severe_finding_count
        )
        active_severe_bug_covered_count = (
            finding_governance["active_severe_bug_covered_count"]
            if report_findings
            else created_bug_count
        )
        active_severe_task_covered_count = (
            finding_governance["active_severe_task_covered_count"]
            if report_findings
            else created_task_count
        )
        row["report_count"] += 1
        row["finding_count"] += finding_count
        row["severe_finding_count"] += severe_finding_count
        row["active_severe_finding_count"] += active_severe_finding_count
        row["created_bug_count"] += created_bug_count
        row["created_task_count"] += created_task_count
        row["uncovered_severe_bug_count"] += max(
            active_severe_finding_count - active_severe_bug_covered_count,
            0,
        )
        row["uncovered_severe_task_count"] += max(
            active_severe_finding_count - active_severe_task_covered_count,
            0,
        )
        row["suppressed_finding_count"] += (
            finding_governance["suppressed_finding_count"]
            if report_findings
            else int(report.get("suppressed_finding_count") or 0)
        )
        row["false_positive_count"] += (
            finding_governance["false_positive_count"]
            if report_findings
            else _suppression_summary_count(report, "false_positive")
        )
        row["accepted_risk_count"] += (
            finding_governance["accepted_risk_count"]
            if report_findings
            else _suppression_summary_count(report, "accepted_risk")
        )
        row["expired_accepted_risk_count"] += finding_governance["expired_accepted_risk_count"]
        row["pending_suppression_count"] += finding_governance["pending_suppression_count"]
        if _quality_gate_failed(report):
            row["quality_gate_failed_report_count"] += 1
        row["quality_gate_violation_count"] += _quality_gate_violation_count(report)
        report_sort_key = _report_sort_key(report)
        if report_sort_key >= str(row.get("_latest_report_sort_key") or ""):
            row["_latest_report_sort_key"] = report_sort_key
            row["latest_report_id"] = report.get("id")
            row["latest_report_summary"] = report.get("summary") or report.get("id")
            row["latest_report_time"] = (
                report.get("scan_finished_at")
                or report.get("updated_at")
                or report.get("created_at")
            )

    rows = []
    for row in branch_rows.values():
        if row["report_count"] <= 0:
            row["status"] = "pending_scan"
        elif (
            row["quality_gate_failed_report_count"]
            or row["active_severe_finding_count"]
            or row["expired_accepted_risk_count"]
            or row["pending_suppression_count"]
            or row["uncovered_severe_bug_count"]
            or row["uncovered_severe_task_count"]
        ):
            row["status"] = "action_required"
        else:
            row["status"] = "healthy"
        row.pop("_latest_report_sort_key", None)
        rows.append(row)

    rows.sort(
        key=lambda item: (
            {"action_required": 0, "pending_scan": 1, "healthy": 2}.get(
                str(item.get("status") or ""),
                99,
            ),
            -(int(item.get("uncovered_severe_bug_count") or 0)),
            -(int(item.get("quality_gate_failed_report_count") or 0)),
            str(item.get("repository_name") or ""),
            str(item.get("branch") or ""),
        )
    )
    return rows


def _successful_release(release: dict[str, Any]) -> bool:
    return str(release.get("status") or "").lower() in {
        "deployed",
        "passed",
        "released",
        "success",
        "successful",
        "succeeded",
    }


def _failed_release(release: dict[str, Any]) -> bool:
    return str(release.get("status") or "").lower() in {
        "canceled",
        "cancelled",
        "failed",
        "failure",
    }


def _release_time_value(release: dict[str, Any]) -> str:
    return str(
        release.get("deployed_at")
        or release.get("started_at")
        or release.get("created_at")
        or ""
    )


def _release_display_time(release: dict[str, Any]) -> str:
    raw_time = _release_time_value(release)
    parsed = _parse_optional_datetime(raw_time)
    if parsed is None:
        return raw_time.replace("T", " ").split("+", 1)[0].split("Z", 1)[0][:16]
    return parsed.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")


def _release_label(release: dict[str, Any]) -> str:
    status = str(release.get("status") or "-")
    job_name = str(release.get("job_name") or "").strip()
    build_id = str(release.get("build_id") or "").strip()
    subject = job_name or build_id or str(release.get("id") or "").strip()
    return f"{status} {subject}".strip()


def _branch_blockers(
    *,
    branch_configs: list[dict[str, Any]],
    target_status: str | None,
) -> list[dict[str, Any]]:
    if target_status is None:
        return []
    if target_status == "testing":
        allowed = {"active", "testing", "merged", "released"}
    elif target_status == "released":
        allowed = {"merged", "released"}
    else:
        return []
    blockers = []
    for config in branch_configs:
        status = str(config.get("branch_status") or "not_created")
        if status in allowed:
            continue
        blockers.append(
            _dashboard_blocker(
                blocker_id=config.get("id"),
                reason=f"分支状态 {status} 不满足版本推进到 {target_status} 的要求",
                severity="medium",
                source_type="product_version_branch_config",
                title=config.get("working_branch") or config.get("id"),
            )
        )
    return blockers


def _build_blockers(
    *,
    branch_configs: list[dict[str, Any]],
    bugs: list[dict[str, Any]],
    code_inspection_reports: list[dict[str, Any]],
    code_review_reports: list[dict[str, Any]],
    releases: list[dict[str, Any]],
    status_impact: dict[str, Any] | None,
    target_status: str | None,
    version_id: str,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if status_impact is not None:
        for requirement in status_impact.get("blocked_requirements") or []:
            blockers.append(
                _dashboard_blocker(
                    blocker_id=requirement.get("id"),
                    reason=requirement.get("block_reason") or "需求状态阻塞版本推进",
                    severity="high" if target_status == "released" else "medium",
                    source_type="requirement",
                    title=requirement.get("title"),
                )
            )
    for bug in bugs:
        if bug.get("status") in OPEN_BUG_STATUSES and bug.get("severity") in SEVERE_BUG_SEVERITIES:
            blockers.append(
                _dashboard_blocker(
                    blocker_id=bug.get("id"),
                    reason=f"{bug.get('severity')} Bug 仍未关闭",
                    severity="high",
                    source_type="bug",
                    title=bug.get("title"),
                )
            )
    for report in code_review_reports:
        if str(report.get("status") or "").lower() in PENDING_CODE_REVIEW_STATUSES:
            blockers.append(
                _dashboard_blocker(
                    blocker_id=report.get("id"),
                    reason="代码评审仍待确认，未完成版本准入确认",
                    severity="high" if target_status == "released" else "medium",
                    source_type="code_review_report",
                    title=report.get("summary") or report.get("task_title") or report.get("id"),
                )
            )
    for report in code_inspection_reports:
        if report.get("risk_level") in SEVERE_CODE_RISKS or _quality_gate_failed(report):
            blockers.append(
                _dashboard_blocker(
                    blocker_id=report.get("id"),
                    reason="代码巡检存在高风险或质量门禁失败",
                    severity="high" if report.get("risk_level") == "critical" else "medium",
                    source_type="code_inspection_report",
                    title=report.get("summary") or report.get("id"),
                )
            )
    for release in releases:
        if _failed_release(release):
            blockers.append(
                _dashboard_blocker(
                    blocker_id=release.get("id"),
                    reason="发布记录失败或取消",
                    severity="high",
                    source_type="jenkins_release",
                    title=release.get("job_name") or release.get("build_id") or release.get("id"),
                )
            )
    if target_status == "released" and not any(
        _successful_release(release) for release in releases
    ):
        blockers.append(
            _dashboard_blocker(
                action_target_id=version_id,
                action_target_type="product_version",
                blocker_id=None,
                reason="缺少成功发布记录，不能确认版本已完成发布。",
                resolution_hint="登记或同步成功发布记录后解除发布阻塞。",
                severity="high",
                source_type="jenkins_release",
                title="缺少成功发布记录",
            )
        )
    blockers.extend(_branch_blockers(branch_configs=branch_configs, target_status=target_status))
    return blockers


def product_version_dashboard_response(
    *,
    current_store: Any,
    version_id: str,
    user: dict[str, Any],
) -> dict[str, Any] | None:
    read_store = _version_dashboard_read_store(current_store, version_id)
    version = get_product_version_record(read_store, version_id)
    if version is None:
        return None

    product_id = str(version.get("product_id") or "")
    version_summary = product_version_summary_projection(version, read_store)
    requirements = _version_requirements(read_store, version_id)
    requirement_ids = {str(requirement["id"]) for requirement in requirements}
    tasks = _version_tasks(
        read_store,
        requirement_ids=requirement_ids,
        user=user,
        version_id=version_id,
    )
    task_ids = {str(task["id"]) for task in tasks}
    code_review_reports = _version_code_review_reports(read_store, tasks=tasks)
    knowledge_deposits, knowledge_access_issues = _version_knowledge_deposits(
        read_store,
        tasks=tasks,
        user=user,
    )
    branch_configs = _branch_configs_for_version(read_store, version_id)
    code_inspection_reports, code_access_issues = _version_code_inspection_reports(
        read_store,
        branch_configs=branch_configs,
        product_id=product_id,
        user=user,
    )
    bugs, bug_access_issues = _version_bugs(
        read_store,
        code_inspection_reports=code_inspection_reports,
        requirement_ids=requirement_ids,
        task_ids=task_ids,
        user=user,
        version_id=version_id,
    )
    releases = _version_releases(read_store, version_id)
    next_status = VERSION_NEXT_STATUS.get(str(version.get("status") or ""))
    status_impact = (
        {
            "target_status": next_status,
            **build_version_advance_impact(
                read_store,
                target_status=next_status,
                version_id=version_id,
            ),
        }
        if next_status
        else None
    )
    blockers = sorted(
        _build_blockers(
            branch_configs=branch_configs,
            bugs=bugs,
            code_inspection_reports=code_inspection_reports,
            code_review_reports=code_review_reports,
            releases=releases,
            status_impact=status_impact,
            target_status=next_status,
            version_id=version_id,
        ),
        key=_blocker_sort_key,
    )
    next_actions = _version_next_actions(blockers)
    code_inspection_report_ids = {
        str(report.get("id") or "") for report in code_inspection_reports if report.get("id")
    }
    branch_quality_governance = (
        []
        if code_access_issues
        else _version_branch_quality_governance(
            branch_configs=branch_configs,
            code_inspection_findings=[
                finding
                for finding in _memory_records(read_store, "code_inspection_findings")
                if str(finding.get("report_id") or "") in code_inspection_report_ids
            ],
            code_inspection_reports=code_inspection_reports,
        )
    )
    open_bug_count = sum(1 for bug in bugs if bug.get("status") in OPEN_BUG_STATUSES)
    severe_bug_count = sum(
        1
        for bug in bugs
        if bug.get("status") in OPEN_BUG_STATUSES and bug.get("severity") in SEVERE_BUG_SEVERITIES
    )
    severe_code_report_count = sum(
        1
        for report in code_inspection_reports
        if report.get("risk_level") in SEVERE_CODE_RISKS or _quality_gate_failed(report)
    )
    pending_code_review_report_count = sum(
        1
        for report in code_review_reports
        if str(report.get("status") or "").lower() in PENDING_CODE_REVIEW_STATUSES
    )
    searchable_knowledge_deposit_count = sum(
        1
        for deposit in knowledge_deposits
        if deposit.get("knowledge_retrieval_mode") in {"hybrid", "keyword"}
    )
    vectorized_knowledge_deposit_count = sum(
        1 for deposit in knowledge_deposits if deposit.get("knowledge_retrieval_mode") == "hybrid"
    )
    summary = {
        "blockers": len(blockers),
        "branch_configs": len(branch_configs),
        "branch_quality_action_required": sum(
            1
            for item in branch_quality_governance
            if item.get("status") == "action_required"
        ),
        "branch_quality_accepted_risks": sum(
            int(item.get("accepted_risk_count") or 0) for item in branch_quality_governance
        ),
        "branch_quality_active_severe_findings": sum(
            int(item.get("active_severe_finding_count") or 0)
            for item in branch_quality_governance
        ),
        "branch_quality_expired_accepted_risks": sum(
            int(item.get("expired_accepted_risk_count") or 0)
            for item in branch_quality_governance
        ),
        "branch_quality_false_positives": sum(
            int(item.get("false_positive_count") or 0) for item in branch_quality_governance
        ),
        "branch_quality_pending_scan": sum(
            1 for item in branch_quality_governance if item.get("status") == "pending_scan"
        ),
        "branch_quality_pending_suppressions": sum(
            int(item.get("pending_suppression_count") or 0)
            for item in branch_quality_governance
        ),
        "bugs": len(bugs),
        "code_inspection_reports": len(code_inspection_reports),
        "code_review_reports": len(code_review_reports),
        "knowledge_deposits": len(knowledge_deposits),
        "open_bugs": open_bug_count,
        "pending_code_review_reports": pending_code_review_report_count,
        "failed_releases": sum(1 for release in releases if _failed_release(release)),
        "releases": len(releases),
        "requirements": len(requirements),
        "searchable_knowledge_deposits": searchable_knowledge_deposit_count,
        "severe_bugs": severe_bug_count,
        "severe_code_inspection_reports": severe_code_report_count,
        "successful_releases": sum(1 for release in releases if _successful_release(release)),
        "tasks": len(tasks),
        "vectorized_knowledge_deposits": vectorized_knowledge_deposit_count,
    }
    governance_conclusion = _version_governance_conclusion(
        blockers=blockers,
        branch_quality_governance=branch_quality_governance,
        status_impact=status_impact,
        summary=summary,
    )
    delivery_stage_overview = _delivery_stage_overview(
        blockers=blockers,
        branch_configs=branch_configs,
        branch_quality_governance=branch_quality_governance,
        bugs=bugs,
        code_inspection_reports=code_inspection_reports,
        code_review_reports=code_review_reports,
        knowledge_deposits=knowledge_deposits,
        releases=releases,
        status_impact=status_impact,
        summary=summary,
        tasks=tasks,
        version=version_summary,
    )
    access_issues = [
        *bug_access_issues,
        *code_access_issues,
        *knowledge_access_issues,
    ]
    evidence_coverage = _version_evidence_coverage(
        access_issues=access_issues,
        blockers=blockers,
        status_impact=status_impact,
        summary=summary,
        version_id=version_id,
    )
    return {
        "access_issues": access_issues,
        "blockers": blockers,
        "branch_configs": branch_configs,
        "branch_quality_governance": branch_quality_governance[:20],
        "bugs": bugs[:20],
        "bug_status_counts": _status_counts(bugs),
        "code_inspection_reports": code_inspection_reports[:20],
        "code_review_reports": code_review_reports[:20],
        "delivery_stage_overview": delivery_stage_overview,
        "evidence_coverage": evidence_coverage,
        "governance_conclusion": governance_conclusion,
        "knowledge_deposits": knowledge_deposits[:20],
        "next_actions": next_actions,
        "releases": releases[:20],
        "requirement_status_counts": _status_counts(requirements),
        "requirements": requirements[:50],
        "status_impact": status_impact,
        "summary": summary,
        "task_status_counts": _status_counts(tasks),
        "tasks": tasks[:30],
        "version": version_summary,
    }
