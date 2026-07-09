from __future__ import annotations

from typing import Any

from app.services.product_version_delivery_overview import (
    failed_release,
    successful_release,
)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _branch_quality_summary(
    branch_quality_governance: list[dict[str, Any]],
    summary: dict[str, int],
) -> dict[str, int]:
    def sum_field(field: str) -> int:
        return sum(_safe_int(item.get(field)) for item in branch_quality_governance)

    return {
        "action_required_branch_count": _safe_int(
            summary.get("branch_quality_action_required")
        ),
        "pending_scan_branch_count": _safe_int(summary.get("branch_quality_pending_scan")),
        "pending_suppression_count": _safe_int(
            summary.get("branch_quality_pending_suppressions")
        ),
        "quality_gate_failed_report_count": sum_field("quality_gate_failed_report_count"),
        "quality_gate_violation_count": sum_field("quality_gate_violation_count"),
    }


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "blocked": 0,
        "missing": 0,
        "not_applicable": 0,
        "ready": 0,
        "risk": 0,
    }
    for item in items:
        status = str(item.get("status") or "")
        if status in counts:
            counts[status] += 1
    return counts


def _readiness_item(
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


def _release_readiness_level(status_counts: dict[str, int]) -> str:
    if status_counts["blocked"] or status_counts["missing"]:
        return "error"
    if status_counts["risk"]:
        return "warning"
    if status_counts["ready"]:
        return "success"
    return "info"


def _release_readiness_value(status_counts: dict[str, int]) -> str:
    if status_counts["blocked"] or status_counts["missing"]:
        return "发布准备未通过"
    if status_counts["risk"]:
        return "发布准备存在风险"
    if status_counts["ready"]:
        return "发布准备基本就绪"
    return "暂无发布准备项"


def _release_readiness_summary(status_counts: dict[str, int]) -> str:
    actionable_total = (
        status_counts["blocked"]
        + status_counts["missing"]
        + status_counts["ready"]
        + status_counts["risk"]
    )
    if status_counts["blocked"] or status_counts["missing"]:
        return (
            f"{status_counts['blocked']} 项阻塞、{status_counts['missing']} 项缺失，"
            f"需完成发布准备后再推进；已就绪 {status_counts['ready']}/{actionable_total} 项。"
        )
    if status_counts["risk"]:
        return (
            f"{status_counts['risk']} 项存在风险，建议补齐后再发布；"
            f"已就绪 {status_counts['ready']}/{actionable_total} 项。"
        )
    if actionable_total:
        return f"发布准备清单已就绪 {status_counts['ready']}/{actionable_total} 项。"
    return "当前版本状态暂无发布准备检查项。"


def version_release_readiness_checklist(
    *,
    blockers: list[dict[str, Any]],
    branch_quality_governance: list[dict[str, Any]],
    deployments: list[dict[str, Any]],
    releases: list[dict[str, Any]],
    status_impact: dict[str, Any] | None,
    summary: dict[str, int],
    version_id: str,
) -> dict[str, Any]:
    branch_quality = _branch_quality_summary(branch_quality_governance, summary)
    blocked_requirement_count = (
        len(status_impact.get("blocked_requirements") or []) if status_impact else 0
    )
    target_status = str(status_impact.get("target_status") or "") if status_impact else ""
    release_blocker_count = sum(
        1 for blocker in blockers if blocker.get("source_type") == "jenkins_release"
    )
    deployment_blocker_count = sum(
        1 for blocker in blockers if blocker.get("source_type") == "deployment_request"
    )
    successful_deployment_count = sum(
        1 for deployment in deployments if successful_release(deployment)
    )
    failed_deployment_count = sum(1 for deployment in deployments if failed_release(deployment))
    has_successful_deployment = successful_deployment_count > 0
    successful_release_count = sum(1 for release in releases if successful_release(release))
    failed_release_count = sum(1 for release in releases if failed_release(release))
    has_successful_release = successful_release_count > 0
    severe_quality_count = _safe_int(summary.get("severe_code_inspection_reports"))
    severe_bug_count = _safe_int(summary.get("severe_bugs"))
    open_bug_count = _safe_int(summary.get("open_bugs"))

    if blocked_requirement_count:
        requirement_item = _readiness_item(
            action_label="处理需求",
            action_target_id=version_id,
            action_target_type="requirements",
            detail=f"状态推进仍有 {blocked_requirement_count} 条需求阻塞。",
            key="requirements",
            level="error",
            status="blocked",
            title="需求范围",
            value="需求未满足准入",
        )
    elif _safe_int(summary.get("requirements")):
        requirement_item = _readiness_item(
            action_label="查看需求",
            action_target_id=version_id,
            action_target_type="requirements",
            detail=f"{summary['requirements']} 条需求纳入版本，状态推进无阻塞。",
            key="requirements",
            level="success",
            status="ready",
            title="需求范围",
            value="需求可推进",
        )
    else:
        requirement_item = _readiness_item(
            action_label="归集需求",
            action_target_id=version_id,
            action_target_type="requirements",
            detail="当前版本尚未归集需求，无法形成发布范围。",
            key="requirements",
            level="error",
            status="missing",
            title="需求范围",
            value="需求范围缺失",
        )

    task_item = _readiness_item(
        action_label="查看任务",
        action_target_id=version_id,
        action_target_type="tasks_by_version",
        detail=(
            f"{summary['tasks']} 个研发任务已关联版本。"
            if _safe_int(summary.get("tasks"))
            else "当前版本尚未关联研发任务。"
        ),
        key="tasks",
        level="success" if _safe_int(summary.get("tasks")) else "error",
        status="ready" if _safe_int(summary.get("tasks")) else "missing",
        title="研发任务",
        value="任务已关联" if _safe_int(summary.get("tasks")) else "任务缺失",
    )

    branch_pressure = (
        branch_quality["action_required_branch_count"]
        + branch_quality["pending_scan_branch_count"]
    )
    if not _safe_int(summary.get("branch_configs")):
        branch_item = _readiness_item(
            action_label="维护分支",
            action_target_id=version_id,
            action_target_type="product_version",
            detail="当前版本尚未维护代码分支。",
            key="branches",
            level="error",
            status="missing",
            title="代码分支",
            value="分支缺失",
        )
    else:
        branch_item = _readiness_item(
            action_label="维护分支" if branch_pressure else "查看分支",
            action_target_id=version_id,
            action_target_type="product_version",
            detail=(
                f"{summary['branch_configs']} 个分支，待治理 "
                f"{branch_quality['action_required_branch_count']} 个，待巡检 "
                f"{branch_quality['pending_scan_branch_count']} 个。"
            ),
            key="branches",
            level="error" if branch_pressure else "success",
            status="blocked" if branch_pressure else "ready",
            title="代码分支",
            value="分支待治理" if branch_pressure else "分支就绪",
        )

    quality_pressure = severe_quality_count + branch_quality["quality_gate_failed_report_count"]
    if not _safe_int(summary.get("code_inspection_reports")):
        inspection_item = _readiness_item(
            action_label="执行巡检",
            action_target_id=version_id,
            action_target_type="code_inspection_dashboard",
            detail="当前版本分支尚无代码巡检报告。",
            key="inspections",
            level="error",
            status="missing",
            title="代码巡检",
            value="巡检缺失",
        )
    else:
        inspection_item = _readiness_item(
            action_label="治理巡检" if quality_pressure else "查看巡检",
            action_target_id=version_id,
            action_target_type="code_inspection_dashboard",
            detail=(
                f"{summary['code_inspection_reports']} 份报告，严重风险 "
                f"{severe_quality_count} 份，质量门禁失败 "
                f"{branch_quality['quality_gate_failed_report_count']} 份，"
                f"待审批忽略 {branch_quality['pending_suppression_count']} 个。"
            ),
            key="inspections",
            level="error" if quality_pressure else "success",
            status="blocked" if quality_pressure else "ready",
            title="代码巡检",
            value="质量门禁未通过" if quality_pressure else "质量门禁通过",
        )

    if _safe_int(summary.get("pending_code_review_reports")):
        review_item = _readiness_item(
            action_label="处理评审",
            action_target_id=version_id,
            action_target_type="code_review_reports_by_version",
            detail=f"{summary['pending_code_review_reports']} 份代码评审仍待确认。",
            key="code-reviews",
            level="error",
            status="blocked",
            title="代码评审",
            value="评审待确认",
        )
    elif _safe_int(summary.get("code_review_reports")):
        review_item = _readiness_item(
            action_label="查看评审",
            action_target_id=version_id,
            action_target_type="code_review_reports_by_version",
            detail=f"{summary['code_review_reports']} 份代码评审已完成确认。",
            key="code-reviews",
            level="success",
            status="ready",
            title="代码评审",
            value="评审已确认",
        )
    else:
        review_item = _readiness_item(
            action_label="补充评审",
            action_target_id=version_id,
            action_target_type="code_review_reports_by_version",
            detail="当前版本尚无代码评审报告。",
            key="code-reviews",
            level="warning",
            status="risk",
            title="代码评审",
            value="评审证据待补齐",
        )

    if severe_bug_count:
        bug_item = _readiness_item(
            action_label="处理 Bug",
            action_target_id=version_id,
            action_target_type="bugs",
            detail=f"{severe_bug_count} 个严重 Bug 未关闭，全部未关闭 Bug {open_bug_count} 个。",
            key="bugs",
            level="error",
            status="blocked",
            title="Bug 收敛",
            value="严重 Bug 未关闭",
        )
    elif open_bug_count:
        bug_item = _readiness_item(
            action_label="处理 Bug",
            action_target_id=version_id,
            action_target_type="bugs",
            detail=f"{open_bug_count} 个普通 Bug 未关闭。",
            key="bugs",
            level="warning",
            status="risk",
            title="Bug 收敛",
            value="Bug 待收敛",
        )
    else:
        bug_item = _readiness_item(
            action_label="查看 Bug",
            action_target_id=version_id,
            action_target_type="bugs",
            detail=f"{summary['bugs']} 个 Bug 已收敛。",
            key="bugs",
            level="success",
            status="ready",
            title="Bug 收敛",
            value="Bug 已收敛",
        )

    knowledge_count = _safe_int(summary.get("knowledge_deposits"))
    searchable_knowledge_count = _safe_int(summary.get("searchable_knowledge_deposits"))
    if not knowledge_count:
        knowledge_item = _readiness_item(
            action_label="补充沉淀",
            action_target_id=version_id,
            action_target_type="knowledge_deposits_by_version",
            detail="当前版本尚无知识沉淀。",
            key="knowledge-deposits",
            level="warning",
            status="risk",
            title="知识沉淀",
            value="沉淀待补齐",
        )
    elif searchable_knowledge_count < knowledge_count:
        knowledge_item = _readiness_item(
            action_label="修复索引",
            action_target_id=version_id,
            action_target_type="knowledge_deposits_by_version",
            detail=f"{searchable_knowledge_count}/{knowledge_count} 条知识沉淀可检索。",
            key="knowledge-deposits",
            level="warning",
            status="risk",
            title="知识沉淀",
            value="索引待修复",
        )
    else:
        knowledge_item = _readiness_item(
            action_label="查看沉淀",
            action_target_id=version_id,
            action_target_type="knowledge_deposits_by_version",
            detail=(
                f"{searchable_knowledge_count}/{knowledge_count} 条知识沉淀可检索，"
                f"向量就绪 {summary['vectorized_knowledge_deposits']} 条。"
            ),
            key="knowledge-deposits",
            level="success",
            status="ready",
            title="知识沉淀",
            value="知识可检索",
        )

    deployment_must_be_successful = target_status == "released"
    if deployment_must_be_successful and not has_successful_deployment:
        deployment_item = _readiness_item(
            action_label="发起部署",
            action_target_id=version_id,
            action_target_type="deployments",
            detail=(
                f"推进到已发布需要成功运维部署单；当前成功 {successful_deployment_count} 个，"
                f"失败 {failed_deployment_count} 个，部署阻塞 {deployment_blocker_count} 个。"
            ),
            key="deployments",
            level="error",
            status="missing",
            title="运维部署",
            value="成功部署缺失",
        )
    elif failed_deployment_count or deployment_blocker_count:
        deployment_item = _readiness_item(
            action_label="处理部署",
            action_target_id=version_id,
            action_target_type="deployments",
            detail=(
                f"成功 {successful_deployment_count} 个，失败 {failed_deployment_count} 个，"
                f"部署阻塞 {deployment_blocker_count} 个。"
            ),
            key="deployments",
            level="error" if deployment_blocker_count else "warning",
            status="blocked" if deployment_blocker_count else "risk",
            title="运维部署",
            value="部署待治理",
        )
    elif has_successful_deployment:
        deployment_item = _readiness_item(
            action_label="查看部署",
            action_target_id=version_id,
            action_target_type="deployments",
            detail=f"已有 {successful_deployment_count} 个成功部署单。",
            key="deployments",
            level="success",
            status="ready",
            title="运维部署",
            value="部署已完成",
        )
    else:
        deployment_item = _readiness_item(
            action_label="查看部署",
            action_target_id=version_id,
            action_target_type="deployments",
            detail="当前阶段暂不强制要求成功部署单。",
            key="deployments",
            level="info",
            status="not_applicable",
            title="运维部署",
            value="部署待执行",
        )

    release_must_be_successful = False
    if release_must_be_successful and not has_successful_release:
        release_item = _readiness_item(
            action_label="补充发布",
            action_target_id=version_id,
            action_target_type="releases",
            detail=(
                f"推进到已发布需要成功发布记录；当前成功 {successful_release_count} 条，"
                f"失败 {failed_release_count} 条，发布阻塞 {release_blocker_count} 个。"
            ),
            key="releases",
            level="error",
            status="missing",
            title="发布证据",
            value="成功发布缺失",
        )
    elif failed_release_count or release_blocker_count:
        release_item = _readiness_item(
            action_label="排查发布",
            action_target_id=version_id,
            action_target_type="releases",
            detail=(
                f"成功 {successful_release_count} 条，失败 {failed_release_count} 条，"
                f"发布阻塞 {release_blocker_count} 个。"
            ),
            key="releases",
            level="error" if release_blocker_count else "warning",
            status="blocked" if release_blocker_count else "risk",
            title="发布证据",
            value="发布待治理",
        )
    elif has_successful_release:
        release_item = _readiness_item(
            action_label="查看发布",
            action_target_id=version_id,
            action_target_type="releases",
            detail=f"已有 {successful_release_count} 条成功发布记录。",
            key="releases",
            level="success",
            status="ready",
            title="发布证据",
            value="发布证据可用",
        )
    else:
        release_item = _readiness_item(
            action_label="查看发布",
            action_target_id=version_id,
            action_target_type="releases",
            detail="当前阶段暂不强制要求成功发布记录。",
            key="releases",
            level="info",
            status="not_applicable",
            title="发布证据",
            value="发布后补证",
        )

    if not status_impact:
        status_item = _readiness_item(
            detail="当前版本状态暂无下一阶段推进影响。",
            key="status-impact",
            level="info",
            status="not_applicable",
            title="状态推进",
            value="无需推进",
        )
    elif blocked_requirement_count:
        status_item = _readiness_item(
            action_label="处理推进阻塞",
            action_target_id=version_id,
            action_target_type="product_version_advance",
            detail=f"推进到 {target_status} 仍有 {blocked_requirement_count} 条需求阻塞。",
            key="status-impact",
            level="error",
            status="blocked",
            title="状态推进",
            value="推进阻塞",
        )
    else:
        status_item = _readiness_item(
            action_label="推进状态",
            action_target_id=version_id,
            action_target_type="product_version_advance",
            detail=(
                f"推进到 {target_status} 将同步 "
                f"{len(status_impact.get('updated_requirements') or [])} 条需求，"
                f"保持 {len(status_impact.get('unchanged_requirements') or [])} 条。"
            ),
            key="status-impact",
            level="success",
            status="ready",
            title="状态推进",
            value="影响已预览",
        )

    items = [
        requirement_item,
        task_item,
        branch_item,
        inspection_item,
        review_item,
        bug_item,
        knowledge_item,
        deployment_item,
        release_item,
        status_item,
    ]
    status_counts = _status_counts(items)
    return {
        "blocked_items": status_counts["blocked"],
        "items": items,
        "level": _release_readiness_level(status_counts),
        "missing_items": status_counts["missing"],
        "not_applicable_items": status_counts["not_applicable"],
        "ready_items": status_counts["ready"],
        "risk_items": status_counts["risk"],
        "summary": _release_readiness_summary(status_counts),
        "title": "发布准备清单",
        "total_items": len(items),
        "value": _release_readiness_value(status_counts),
    }
