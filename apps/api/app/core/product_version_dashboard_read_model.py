from __future__ import annotations

from typing import Any

from app.core.store import DEFAULT_BRAIN_APP_ID


def product_version_dashboard_source_rows(repository: Any, version_id: str) -> dict[str, Any]:
    source_rows = _empty_task_workflow_source_rows()
    version = repository.get_product_version(version_id)
    if version is None:
        return source_rows

    product_id = str(version.get("product_id") or "")
    product = repository.get_product(product_id) if product_id else None
    branch_configs = repository.list_product_version_branch_configs(version_id)
    branch_keys = {
        (config.get("repository_id"), config.get("working_branch"))
        for config in branch_configs
        if config.get("repository_id") and config.get("working_branch")
    }
    requirements = repository.list_requirement_summaries(
        version_id=version_id,
        limit=None,
        sort_by="updated_at",
        sort_order="desc",
    )
    requirement_ids = [str(item["id"]) for item in requirements if item.get("id")]
    tasks = _list_version_tasks(
        repository,
        requirement_ids=requirement_ids,
        version_id=version_id,
    )
    task_ids = [str(item["id"]) for item in tasks if item.get("id")]
    code_inspection_reports = repository.list_code_inspection_reports(product_id=product_id)
    if branch_keys:
        code_inspection_reports = [
            report
            for report in code_inspection_reports
            if (report.get("repository_id"), report.get("branch")) in branch_keys
        ]
    report_bug_ids = [
        str(bug_id)
        for report in code_inspection_reports
        for bug_id in (report.get("created_bug_ids") or [])
        if bug_id
    ]
    knowledge_deposits = _list_knowledge_deposits_for_tasks(repository, task_ids)
    knowledge_document_ids = [
        str(item["knowledge_document_id"])
        for item in knowledge_deposits
        if item.get("knowledge_document_id")
    ]
    source_rows.update(
        {
            "bugs": _list_version_bugs(
                repository,
                product_id=product_id,
                report_bug_ids=report_bug_ids,
                requirement_ids=requirement_ids,
                task_ids=task_ids,
                version_id=version_id,
            ),
            "code_inspection_findings": _list_lightweight_code_inspection_findings_for_reports(
                repository,
                [
                    str(report["id"])
                    for report in code_inspection_reports
                    if report.get("id")
                ],
            ),
            "code_inspection_reports": code_inspection_reports,
            "code_review_reports": _list_code_review_reports_for_tasks(repository, task_ids),
            "jenkins_release_records": repository.list_jenkins_release_records(
                version_id=version_id,
            ),
            "knowledge_chunks": _list_lightweight_knowledge_chunks_for_documents(
                repository,
                knowledge_document_ids,
            ),
            "knowledge_deposits": knowledge_deposits,
            "knowledge_documents": _list_knowledge_documents_by_ids(
                repository,
                knowledge_document_ids,
            ),
            "product_git_repositories": (
                repository.list_product_git_repositories(product_id) if product_id else []
            ),
            "product_modules": repository.list_product_modules(product_id) if product_id else [],
            "product_version_branch_configs": branch_configs,
            "product_versions": [version],
            "products": [product] if product is not None else [],
            "related_systems": (
                repository.list_related_systems(product_id=product_id) if product_id else []
            ),
            "requirements": requirements,
            "tasks": tasks,
        }
    )
    return source_rows


def _empty_task_workflow_source_rows() -> dict[str, Any]:
    return {
        "audit_events": [],
        "bugs": [],
        "code_inspection_reports": [],
        "code_inspection_findings": [],
        "code_review_reports": [],
        "gitlab_daily_code_metrics": [],
        "gitlab_mr_snapshots": [],
        "graph_checkpoints": [],
        "graph_runs": [],
        "human_reviews": [],
        "jenkins_release_records": [],
        "knowledge_chunks": [],
        "knowledge_deposits": [],
        "knowledge_documents": [],
        "model_gateway_configs": [],
        "model_gateway_logs": [],
        "mock_writebacks": [],
        "online_log_metrics": [],
        "product_git_repositories": [],
        "product_modules": [],
        "product_version_branch_configs": [],
        "product_versions": [],
        "products": [],
        "related_systems": [],
        "requirements": [],
        "tasks": [],
    }


def _list_version_tasks(
    repository: Any,
    *,
    requirement_ids: list[str],
    version_id: str,
) -> list[dict[str, Any]]:
    where_clause = "t.version_id = %s"
    params: list[Any] = [version_id]
    if requirement_ids:
        where_clause = "(t.version_id = %s OR t.requirement_id = ANY(%s))"
        params.append(requirement_ids)
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT t.id, t.brain_app_id, t.requirement_id, t.task_type, t.title,
                       t.status, t.product_id, t.version_id, t.module_code,
                       t.current_step, t.created_by, t.created_at, t.updated_at,
                       COALESCE(p.name, t.product_context->'product'->>'name')
                FROM ai_tasks t
                LEFT JOIN products p ON p.id = t.product_id
                WHERE {where_clause}
                ORDER BY COALESCE(t.updated_at, t.created_at) DESC, t.id ASC
                """,
                tuple(params),
            )
            return [
                {
                    "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                    "created_at": row[11].isoformat() if row[11] else None,
                    "created_by": row[10],
                    "current_step": row[9],
                    "id": row[0],
                    "module_code": row[8],
                    "product_id": row[6],
                    "product_name": row[13],
                    "requirement_id": row[2],
                    "status": row[5],
                    "task_type": row[3],
                    "title": row[4],
                    "updated_at": row[12].isoformat() if row[12] else None,
                    "version_id": row[7],
                }
                for row in cursor.fetchall()
            ]


def _list_version_bugs(
    repository: Any,
    *,
    product_id: str,
    report_bug_ids: list[str],
    requirement_ids: list[str],
    task_ids: list[str],
    version_id: str,
) -> list[dict[str, Any]]:
    relation_clauses = ["b.version_id = %s"]
    params: list[Any] = [product_id, version_id]
    if requirement_ids:
        relation_clauses.append("b.requirement_id = ANY(%s)")
        params.append(requirement_ids)
    if task_ids:
        relation_clauses.append("b.related_task_id = ANY(%s)")
        params.append(task_ids)
    if report_bug_ids:
        relation_clauses.append("b.id = ANY(%s)")
        params.append(report_bug_ids)
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT b.id, b.product_id, b.version_id, b.module_code, b.source, b.title,
                       b.severity, b.description, b.status, b.assignee, b.related_task_id,
                       b.requirement_id, b.reproduce_steps, b.evidence, b.duplicate_of_bug_id,
                       b.created_by, b.created_at, b.updated_at, v.code, v.name
                FROM bugs b
                LEFT JOIN product_versions v ON v.id = b.version_id
                WHERE b.product_id = %s
                  AND ({' OR '.join(relation_clauses)})
                ORDER BY b.created_at DESC, b.id DESC
                """,
                tuple(params),
            )
            bugs = []
            for row in cursor.fetchall():
                bug = {
                    "assignee": row[9],
                    "created_at": row[16].isoformat() if row[16] else None,
                    "created_by": row[15],
                    "description": row[7],
                    "duplicate_of_bug_id": row[14],
                    "evidence": dict(row[13] or {}),
                    "id": row[0],
                    "module_code": row[3],
                    "product_id": row[1],
                    "related_task_id": row[10],
                    "reproduce_steps": list(row[12] or []),
                    "requirement_id": row[11],
                    "severity": row[6],
                    "source": row[4],
                    "status": row[8],
                    "title": row[5],
                    "updated_at": row[17].isoformat() if row[17] else None,
                    "version_code": row[18],
                    "version_id": row[2],
                    "version_name": row[19],
                }
                for optional_key in (
                    "assignee",
                    "created_at",
                    "duplicate_of_bug_id",
                    "module_code",
                    "related_task_id",
                    "requirement_id",
                    "updated_at",
                    "version_code",
                    "version_id",
                    "version_name",
                ):
                    if bug[optional_key] is None:
                        bug.pop(optional_key)
                bugs.append(bug)
            return bugs


def _list_code_review_reports_for_tasks(
    repository: Any,
    task_ids: list[str],
) -> list[dict[str, Any]]:
    if not task_ids:
        return []
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, task_id, gitlab_mr_snapshot_id, executor, summary, risk_level,
                       findings, status, review_id, archived_at, error_code,
                       gitlab_writeback_performed, created_at, updated_at
                FROM code_review_reports
                WHERE task_id = ANY(%s)
                ORDER BY created_at DESC, id DESC
                """,
                (task_ids,),
            )
            reports = []
            for row in cursor.fetchall():
                report = {
                    "archived_at": row[9].isoformat() if row[9] else None,
                    "created_at": row[12].isoformat() if row[12] else None,
                    "error_code": row[10],
                    "executor": dict(row[3] or {}),
                    "findings": list(row[6] or []),
                    "gitlab_mr_snapshot_id": row[2],
                    "gitlab_writeback_performed": row[11],
                    "id": row[0],
                    "review_id": row[8],
                    "risk_level": row[5],
                    "status": row[7],
                    "summary": row[4],
                    "task_id": row[1],
                    "updated_at": row[13].isoformat() if row[13] else None,
                }
                for optional_key in (
                    "archived_at",
                    "created_at",
                    "error_code",
                    "review_id",
                    "updated_at",
                ):
                    if report[optional_key] is None:
                        report.pop(optional_key)
                reports.append(report)
            return reports


def _list_lightweight_code_inspection_findings_for_reports(
    repository: Any,
    report_ids: list[str],
) -> list[dict[str, Any]]:
    if not report_ids:
        return []
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, report_id, severity, created_bug_id, created_task_id,
                       suppression_status, suppression_reason, suppression_expires_at
                FROM code_inspection_findings
                WHERE report_id = ANY(%s)
                """,
                (report_ids,),
            )
            return [
                {
                    "created_bug_id": row[3],
                    "created_task_id": row[4],
                    "id": row[0],
                    "report_id": row[1],
                    "severity": row[2],
                    "suppression_expires_at": row[7].isoformat() if row[7] else None,
                    "suppression_reason": row[6],
                    "suppression_status": row[5] or "none",
                }
                for row in cursor.fetchall()
            ]


def _list_knowledge_deposits_for_tasks(
    repository: Any,
    task_ids: list[str],
) -> list[dict[str, Any]]:
    if not task_ids:
        return []
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, ai_task_id, deposit_type, title, content, content_hash, status,
                       knowledge_document_id, rejection_reason, created_at, updated_at
                FROM knowledge_deposits
                WHERE ai_task_id = ANY(%s)
                ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
                """,
                (task_ids,),
            )
            return [
                repository._knowledge_read_repository.knowledge_deposit_from_row(row)
                for row in cursor.fetchall()
            ]


def _list_knowledge_documents_by_ids(
    repository: Any,
    document_ids: list[str],
) -> list[dict[str, Any]]:
    if not document_ids:
        return []
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, brain_app_id, product_id, version_id, title, content, source_type,
                       doc_type, permission_scope, permission_roles, index_status, index_error,
                       vector_index_error, tags, created_by, created_at, updated_at,
                       knowledge_space_id, folder_id, source_asset_id, parsed_asset_id,
                       active_chunk_set_id, parser_engine, chunk_strategy, document_version
                FROM knowledge_documents
                WHERE id = ANY(%s)
                """,
                (document_ids,),
            )
            return [
                repository._knowledge_read_repository._knowledge_document_from_row(row)
                for row in cursor.fetchall()
            ]


def _list_lightweight_knowledge_chunks_for_documents(
    repository: Any,
    document_ids: list[str],
) -> list[dict[str, Any]]:
    if not document_ids:
        return []
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, document_id, chunk_set_id, embedding IS NOT NULL
                FROM knowledge_chunks
                WHERE document_id = ANY(%s)
                """,
                (document_ids,),
            )
            return [
                {
                    "chunk_set_id": row[2],
                    "document_id": row[1],
                    "embedding": True if row[3] else None,
                    "id": row[0],
                }
                for row in cursor.fetchall()
            ]
