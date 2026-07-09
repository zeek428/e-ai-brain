from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

SEVERE_CODE_RISKS = {"critical", "high"}


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


def successful_release(release: dict[str, Any]) -> bool:
    return str(release.get("status") or "").lower() in {
        "deployed",
        "passed",
        "released",
        "success",
        "successful",
        "succeeded",
    }


def failed_release(release: dict[str, Any]) -> bool:
    return str(release.get("status") or "").lower() in {
        "canceled",
        "cancelled",
        "failed",
        "failure",
        "rolled_back",
    }


def _release_time_value(release: dict[str, Any]) -> str:
    return str(
        release.get("deployed_at")
        or release.get("started_at")
        or release.get("created_at")
        or ""
    )


def release_display_time(release: dict[str, Any]) -> str:
    raw_time = _release_time_value(release)
    parsed = _parse_optional_datetime(raw_time)
    if parsed is None:
        return raw_time.replace("T", " ").split("+", 1)[0].split("Z", 1)[0][:16]
    return parsed.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")


def release_label(release: dict[str, Any]) -> str:
    status = str(release.get("status") or "-")
    title = str(release.get("title") or "").strip()
    job_name = str(release.get("job_name") or "").strip()
    build_id = str(release.get("build_id") or "").strip()
    subject = title or job_name or build_id or str(release.get("id") or "").strip()
    return f"{status} {subject}".strip()


def version_governance_conclusion(
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


def version_delivery_stage_overview(
    *,
    blockers: list[dict[str, Any]],
    branch_configs: list[dict[str, Any]],
    branch_quality_governance: list[dict[str, Any]],
    bugs: list[dict[str, Any]],
    code_inspection_reports: list[dict[str, Any]],
    code_review_reports: list[dict[str, Any]],
    deployments: list[dict[str, Any]],
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
    deployment_blocker_count = sum(
        1 for blocker in blockers if blocker.get("source_type") == "deployment_request"
    )
    successful_release_count = sum(1 for release in releases if successful_release(release))
    failed_release_count = sum(1 for release in releases if failed_release(release))
    successful_deployment_count = sum(
        1 for deployment in deployments if successful_release(deployment)
    )
    failed_deployment_count = sum(1 for deployment in deployments if failed_release(deployment))
    latest_deployment = deployments[0] if deployments else {}
    latest_deployment_label = release_label(latest_deployment) if latest_deployment else ""
    latest_deployment_time = release_display_time(latest_deployment) if latest_deployment else ""
    latest_release = releases[0] if releases else {}
    latest_release_label = release_label(latest_release) if latest_release else ""
    latest_release_time = release_display_time(latest_release) if latest_release else ""
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
    deployment_count = summary.get("deployments", len(deployments))
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
    deployment_detail_parts = [
        f"{deployment_count} 个部署单",
        f"部署阻塞 {deployment_blocker_count} 个" if deployment_blocker_count else "暂无部署阻塞",
        f"成功 {successful_deployment_count} 个",
        f"失败 {failed_deployment_count} 个",
    ]
    if latest_deployment:
        deployment_detail_parts.append(
            f"最近 {latest_deployment_label} · {latest_deployment_time or '-'}"
        )
    deployment_detail = " · ".join(deployment_detail_parts)

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
            action_label="处理部署" if deployment_blocker_count else "查看部署",
            action_target_id=latest_deployment.get("id") or version_id,
            action_target_type=(
                "deployment_request" if latest_deployment.get("id") else "product_version"
            ),
            detail=deployment_detail,
            full_chain_subject_id=latest_deployment.get("id") or version_id,
            full_chain_subject_type=(
                "deployment_request" if latest_deployment.get("id") else "product_version"
            ),
            key="deployments",
            level=(
                "error"
                if deployment_blocker_count
                else "success"
                if successful_deployment_count
                else "warning"
            ),
            title="运维部署",
            value=(
                "部署待治理"
                if deployment_blocker_count
                else "部署已成功"
                if successful_deployment_count
                else "部署待执行"
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
