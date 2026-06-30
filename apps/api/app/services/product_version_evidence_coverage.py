from __future__ import annotations

from typing import Any


def version_evidence_coverage(
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
