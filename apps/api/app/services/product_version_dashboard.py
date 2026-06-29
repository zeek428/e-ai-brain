from __future__ import annotations

from collections import Counter
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


def _successful_release(release: dict[str, Any]) -> bool:
    return str(release.get("status") or "").lower() in {
        "deployed",
        "passed",
        "released",
        "success",
        "successful",
        "succeeded",
    }


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
        if str(release.get("status") or "").lower() in {"failed", "cancelled"}:
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
    blockers = _build_blockers(
        branch_configs=branch_configs,
        bugs=bugs,
        code_inspection_reports=code_inspection_reports,
        releases=releases,
        status_impact=status_impact,
        target_status=next_status,
        version_id=version_id,
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
    return {
        "access_issues": [
            *bug_access_issues,
            *code_access_issues,
            *knowledge_access_issues,
        ],
        "blockers": blockers,
        "branch_configs": branch_configs,
        "bugs": bugs[:20],
        "bug_status_counts": _status_counts(bugs),
        "code_inspection_reports": code_inspection_reports[:20],
        "code_review_reports": code_review_reports[:20],
        "knowledge_deposits": knowledge_deposits[:20],
        "releases": releases[:20],
        "requirement_status_counts": _status_counts(requirements),
        "requirements": requirements[:50],
        "status_impact": status_impact,
        "summary": {
            "blockers": len(blockers),
            "branch_configs": len(branch_configs),
            "bugs": len(bugs),
            "code_inspection_reports": len(code_inspection_reports),
            "code_review_reports": len(code_review_reports),
            "knowledge_deposits": len(knowledge_deposits),
            "open_bugs": open_bug_count,
            "pending_code_review_reports": pending_code_review_report_count,
            "releases": len(releases),
            "requirements": len(requirements),
            "searchable_knowledge_deposits": searchable_knowledge_deposit_count,
            "severe_bugs": severe_bug_count,
            "severe_code_inspection_reports": severe_code_report_count,
            "tasks": len(tasks),
            "vectorized_knowledge_deposits": vectorized_knowledge_deposit_count,
        },
        "task_status_counts": _status_counts(tasks),
        "tasks": tasks[:30],
        "version": version_summary,
    }
