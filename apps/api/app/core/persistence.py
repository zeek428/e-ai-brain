from __future__ import annotations

from pathlib import Path
from time import sleep
from typing import Any

from app.core.db import DatabaseConnectionPool
from app.core.persistence_repositories import install_snapshot_repositories
from app.core.persistence_runtime import PostgresRuntimeStore as PostgresRuntimeStore
from app.core.persistent_memory_store import PersistentMemoryStore as PersistentMemoryStore


class PostgresSnapshotRepository:
    def __init__(
        self,
        database_url: str,
        *,
        ensure_schema_compatibility: bool = False,
        pool_max_size: int = 5,
    ) -> None:
        self.database_url = database_url
        self._pool = DatabaseConnectionPool(
            factory=self._open_connection,
            max_size=pool_max_size,
        )
        install_snapshot_repositories(self)
        if ensure_schema_compatibility:
            self._ensure_schema_compatibility()

    def _open_connection(self):
        import psycopg

        last_error: Exception | None = None
        for _ in range(20):
            try:
                return psycopg.connect(self.database_url)
            except psycopg.OperationalError as exc:
                last_error = exc
                sleep(0.5)
        raise last_error or RuntimeError("PostgreSQL connection failed")

    def _connect(self, *, autocommit: bool = True):
        return self._pool.connection(autocommit=autocommit)

    def _ensure_schema_compatibility(self) -> None:
        """Patch safe additive schema gaps for existing local Postgres volumes."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    ALTER TABLE IF EXISTS requirements
                      ADD COLUMN IF NOT EXISTS assignee text
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE IF EXISTS requirements
                      ADD COLUMN IF NOT EXISTS source text DEFAULT 'business_department'
                    """
                )
                cursor.execute(
                    """
                    UPDATE requirements
                    SET source = 'business_department'
                    WHERE source IS NULL
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE IF EXISTS requirements
                      ALTER COLUMN source SET DEFAULT 'business_department',
                      ALTER COLUMN source SET NOT NULL
                    """
                )
                cursor.execute(
                    """
                    DO $$
                    BEGIN
                      IF to_regclass('public.requirements') IS NOT NULL THEN
                        CREATE INDEX IF NOT EXISTS idx_requirements_assignee
                          ON requirements (assignee);
                        CREATE INDEX IF NOT EXISTS idx_requirements_source_created
                          ON requirements (source, created_at DESC);
                      END IF;
                    END $$;
                    """
                )
                self._apply_additive_migration(
                    cursor,
                    "028_assistant_message_references.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "036_integration_plugins.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "038_plugin_connection_request_config.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "039_task_center_operational_menus.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "037_knowledge_management_assets.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "040_scheduled_job_knowledge_references.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "041_code_inspection_governance.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "042_code_inspection_committer_dimension.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "043_official_devops_plugins.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "044_scheduled_job_run_source.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "045_scheduled_job_collector_types.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "046_code_inspection_plugin_source.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "047_plugin_connection_last_test_summary.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "048_plugin_connection_test_history.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "049_ai_executor_runners.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "050_code_inspection_remediation_tasks.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "051_ai_executor_runner_controls.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "052_move_rd_tasks_menu.sql",
                )

    def next_id(self, prefix: str) -> str:
        return self._system_state_repository.next_id(prefix)

    def _apply_additive_migration(self, cursor: Any, filename: str) -> None:
        migration_path = Path(__file__).resolve().parents[1] / "db" / "migrations" / filename
        if not migration_path.exists():
            return
        for statement in migration_path.read_text(encoding="utf-8").split(";"):
            sql = statement.strip()
            if sql:
                cursor.execute(sql)

    def load(self) -> dict[str, Any] | None:
        return self._system_state_repository.load_snapshot()

    def save(self, payload: dict[str, Any]) -> None:
        self._system_state_repository.save_snapshot(payload)

    def load_product_config(self) -> dict[str, Any]:
        return self._product_config_read_repository.load_product_config()

    def load_brain_apps(self) -> dict[str, Any]:
        return self._brain_app_read_repository.load_brain_apps()

    def list_products(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_products(active_only=active_only)

    def count_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._product_config_read_repository.count_product_summaries(
            active_only=active_only,
            code=code,
            name=name,
            owner_team=owner_team,
            status=status,
        )

    def list_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "display_order",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_product_summaries(
            active_only=active_only,
            code=code,
            name=name,
            owner_team=owner_team,
            status=status,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        return self._product_config_read_repository.get_product(product_id)

    def list_product_versions(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_product_versions(
            product_id,
            active_only=active_only,
        )

    def list_product_modules(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_product_modules(
            product_id,
            active_only=active_only,
        )

    def list_product_git_repositories(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_product_git_repositories(
            product_id,
            active_only=active_only,
        )

    def list_product_version_branch_configs(self, version_id: str) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_product_version_branch_configs(version_id)

    def list_related_systems(
        self,
        *,
        active_only: bool = False,
        product_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_related_systems(
            active_only=active_only,
            product_id=product_id,
        )

    def load_requirements(self) -> dict[str, Any]:
        return self._requirement_read_repository.load_requirements()

    def list_product_version_summaries(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_product_version_summaries(
            active_only=active_only,
        )

    def count_product_version_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._product_config_read_repository.count_product_version_summaries(
            active_only=active_only,
            code=code,
            name=name,
            product=product,
            product_id=product_id,
            status=status,
        )

    def list_product_version_summaries_page(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "code",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        return self._product_config_read_repository.list_product_version_summaries_page(
            active_only=active_only,
            code=code,
            name=name,
            product=product,
            product_id=product_id,
            status=status,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def count_requirement_summaries(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> int:
        return self._requirement_read_repository.count_requirement_summaries(
            priority=priority,
            product=product,
            product_id=product_id,
            source=source,
            status=status,
            title=title,
            version=version,
            version_id=version_id,
        )

    def list_requirement_summaries(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        return self._requirement_read_repository.list_requirement_summaries(
            priority=priority,
            product=product,
            product_id=product_id,
            source=source,
            status=status,
            title=title,
            version=version,
            version_id=version_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def count_ai_task_summaries(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        product_id: str | None = None,
        requirement_id: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
        keyword: str | None = None,
        created_by: str | None = None,
        read_scope: str | None = None,
    ) -> int:
        return self._task_read_repository.count_ai_task_summaries(
            status=status,
            task_type=task_type,
            product_id=product_id,
            requirement_id=requirement_id,
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            created_by=created_by,
            read_scope=read_scope,
        )

    def list_ai_task_summaries(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        product_id: str | None = None,
        requirement_id: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
        keyword: str | None = None,
        created_by: str | None = None,
        read_scope: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        return self._task_read_repository.list_ai_task_summaries(
            status=status,
            task_type=task_type,
            product_id=product_id,
            requirement_id=requirement_id,
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            created_by=created_by,
            read_scope=read_scope,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def list_pending_review_summaries(
        self,
        *,
        read_scope: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._task_read_repository.list_pending_review_summaries(read_scope=read_scope)

    def load_ai_tasks(self) -> dict[str, Any]:
        return self._task_read_repository.load_ai_tasks()

    def load_workflow_runtime(self) -> dict[str, Any]:
        return self._task_read_repository.load_workflow_runtime()

    def get_task_workflow_source_rows(self) -> dict[str, Any]:
        audit_payload = self.load_audit_events() or {}
        bugs_payload = self.load_bugs() or {}
        gitlab_metrics_payload = self.load_gitlab_daily_code_metrics() or {}
        jenkins_releases_payload = self.load_jenkins_release_records() or {}
        model_gateway_payload = self.load_model_gateway() or {}
        online_metrics_payload = self.load_online_log_metrics() or {}
        requirements_payload = self.load_requirements() or {}
        tasks_payload = self.load_ai_tasks() or {}
        workflow_payload = self.load_workflow_runtime() or {}
        product_config_payload = self.load_product_config() or {}
        knowledge_payload = self.load_knowledge() or {}
        review_payload = self.load_gitlab_review() or {}
        mock_payload = self.load_mock_writebacks() or {}
        return {
            "audit_events": list(audit_payload.get("audit_events") or []),
            "bugs": list((bugs_payload.get("bugs") or {}).values()),
            "code_review_reports": list(
                (review_payload.get("code_review_reports") or {}).values()
            ),
            "gitlab_daily_code_metrics": list(
                (gitlab_metrics_payload.get("gitlab_daily_code_metrics") or {}).values()
            ),
            "gitlab_mr_snapshots": list(
                (review_payload.get("gitlab_mr_snapshots") or {}).values()
            ),
            "graph_checkpoints": list(
                (workflow_payload.get("graph_checkpoints") or {}).values()
            ),
            "graph_runs": list((workflow_payload.get("graph_runs") or {}).values()),
            "human_reviews": list((workflow_payload.get("human_reviews") or {}).values()),
            "jenkins_release_records": list(
                (jenkins_releases_payload.get("jenkins_release_records") or {}).values()
            ),
            "knowledge_deposits": list(
                (knowledge_payload.get("knowledge_deposits") or {}).values()
            ),
            "model_gateway_configs": list(
                (model_gateway_payload.get("model_gateway_configs") or {}).values()
            ),
            "model_gateway_logs": list(model_gateway_payload.get("model_gateway_logs") or []),
            "mock_writebacks": list((mock_payload.get("mock_writebacks") or {}).values()),
            "online_log_metrics": list(
                (online_metrics_payload.get("online_log_metrics") or {}).values()
            ),
            "product_git_repositories": list(
                (product_config_payload.get("product_git_repositories") or {}).values()
            ),
            "product_modules": list(
                (product_config_payload.get("product_modules") or {}).values()
            ),
            "product_version_branch_configs": list(
                (product_config_payload.get("product_version_branch_configs") or {}).values()
            ),
            "product_versions": list(
                (product_config_payload.get("product_versions") or {}).values()
            ),
            "products": list((product_config_payload.get("products") or {}).values()),
            "related_systems": list(
                (product_config_payload.get("related_systems") or {}).values()
            ),
            "requirements": list((requirements_payload.get("requirements") or {}).values()),
            "tasks": list((tasks_payload.get("ai_tasks") or {}).values()),
        }

    def load_knowledge(self) -> dict[str, Any]:
        return self._knowledge_read_repository.load_knowledge()

    def list_knowledge_documents(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._knowledge_read_repository.list_knowledge_documents(
            user_roles=user_roles,
            user_id=user_id,
            global_knowledge_access=global_knowledge_access,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            keyword=keyword,
            doc_type=doc_type,
            folder_id=folder_id,
            index_status=index_status,
            knowledge_space_id=knowledge_space_id,
        )

    def list_knowledge_deposits(
        self,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._knowledge_read_repository.list_knowledge_deposits(status=status)

    def get_knowledge_deposit(self, deposit_id: str) -> dict[str, Any] | None:
        return self._knowledge_read_repository.get_knowledge_deposit(deposit_id=deposit_id)

    def has_readable_vector_chunks(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_id: str | None = None,
        knowledge_space_scope_ids: list[str] | None = None,
    ) -> bool:
        return self._knowledge_read_repository.has_readable_vector_chunks(
            user_roles=user_roles,
            user_id=user_id,
            global_knowledge_access=global_knowledge_access,
            knowledge_space_id=knowledge_space_id,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
        )

    def search_knowledge_chunks(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_id: str | None = None,
        knowledge_space_scope_ids: list[str] | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._knowledge_read_repository.search_knowledge_chunks(
            user_roles=user_roles,
            user_id=user_id,
            global_knowledge_access=global_knowledge_access,
            knowledge_space_id=knowledge_space_id,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            query=query,
        )

    def load_audit_events(self) -> dict[str, Any]:
        return self._audit_read_repository.load_audit_events()

    def list_audit_events(
        self,
        *,
        ai_task_id: str | None = None,
        actor_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        event_type: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
    ) -> list[dict[str, Any]]:
        return self._audit_read_repository.list_audit_events(
            ai_task_id=ai_task_id,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            created_from=created_from,
            created_to=created_to,
        )

    def load_bugs(self) -> dict[str, Any]:
        return self._bug_read_repository.load_bugs()

    def count_bug_summaries(
        self,
        *,
        module: str | None = None,
        product_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> int:
        return self._bug_read_repository.count_bug_summaries(
            module=module,
            product_id=product_id,
            severity=severity,
            source=source,
            status=status,
            title=title,
            version=version,
            version_id=version_id,
        )

    def list_bug_summaries(
        self,
        *,
        module: str | None = None,
        product_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        return self._bug_read_repository.list_bug_summaries(
            module=module,
            product_id=product_id,
            severity=severity,
            source=source,
            status=status,
            title=title,
            version=version,
            version_id=version_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def list_bugs(
        self,
        *,
        product_id: str | None = None,
        version_id: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("b.product_id = %s")
            params.append(product_id)
        if version_id is not None:
            where_clauses.append("b.version_id = %s")
            params.append(version_id)
        if status is not None:
            where_clauses.append("b.status = %s")
            params.append(status)
        if severity is not None:
            where_clauses.append("b.severity = %s")
            params.append(severity)
        if source is not None:
            where_clauses.append("b.source = %s")
            params.append(source)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT b.id, b.product_id, b.version_id, b.module_code, b.source, b.title,
                           b.severity, b.description, b.status, b.assignee, b.related_task_id,
                           b.requirement_id, b.reproduce_steps, b.evidence, b.duplicate_of_bug_id,
                           b.created_by, b.created_at, b.updated_at, v.code, v.name
                    FROM bugs b
                    LEFT JOIN product_versions v ON v.id = b.version_id
                    {where_clause}
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

    def load_gitlab_daily_code_metrics(self) -> dict[str, Any]:
        return self._devops_read_repository.load_gitlab_daily_code_metrics()

    def list_gitlab_daily_code_metrics(
        self,
        *,
        product_id: str | None = None,
        repository_id: str | None = None,
        metric_date: Any | None = None,
    ) -> list[dict[str, Any]]:
        return self._devops_read_repository.list_gitlab_daily_code_metrics(
            metric_date=metric_date,
            product_id=product_id,
            repository_id=repository_id,
        )

    def load_jenkins_release_records(self) -> dict[str, Any]:
        return self._devops_read_repository.load_jenkins_release_records()

    def list_jenkins_release_records(
        self,
        *,
        product_id: str | None = None,
        version_id: str | None = None,
        status: str | None = None,
        environment: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._devops_read_repository.list_jenkins_release_records(
            environment=environment,
            product_id=product_id,
            status=status,
            version_id=version_id,
        )

    def load_online_log_metrics(self) -> dict[str, Any]:
        return self._devops_read_repository.load_online_log_metrics()

    def list_online_log_metrics(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        environment: str | None = None,
        from_value: Any | None = None,
        to_value: Any | None = None,
    ) -> list[dict[str, Any]]:
        return self._devops_read_repository.list_online_log_metrics(
            environment=environment,
            from_value=from_value,
            module_code=module_code,
            product_id=product_id,
            to_value=to_value,
        )

    def list_operational_metric_items(
        self,
        *,
        category: str | None = None,
        name: str | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        return self._devops_read_repository.list_operational_metric_items(
            category=category,
            name=name,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def list_collector_runs(
        self,
        *,
        collector_type: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        source_system: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._operational_collection_read_repository.list_collector_runs(
            collector_type=collector_type,
            product_id=product_id,
            status=status,
            source_system=source_system,
        )

    def list_pending_attribution_items(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        resolved_product_id: str | None = None,
        collector_run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._operational_collection_read_repository.list_pending_attribution_items(
            source_type=source_type,
            status=status,
            resolved_product_id=resolved_product_id,
            collector_run_id=collector_run_id,
        )

    def load_user_feedback(self) -> dict[str, Any]:
        return self._user_insight_read_repository.load_user_feedback()

    def list_user_feedback(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._user_insight_read_repository.list_user_feedback(
            created_by=created_by,
            feature_code=feature_code,
            module_code=module_code,
            product_id=product_id,
            status=status,
        )

    def load_user_usage_metrics(self) -> dict[str, Any]:
        return self._user_insight_read_repository.load_user_usage_metrics()

    def list_user_usage_metrics(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        user_segment: str | None = None,
        from_value: Any | None = None,
        to_value: Any | None = None,
    ) -> list[dict[str, Any]]:
        return self._user_insight_read_repository.list_user_usage_metrics(
            feature_code=feature_code,
            from_value=from_value,
            module_code=module_code,
            product_id=product_id,
            to_value=to_value,
            user_segment=user_segment,
        )

    def load_iteration_planning(self) -> dict[str, Any]:
        return self._user_insight_read_repository.load_iteration_planning()

    def list_iteration_plan_suggestions(
        self,
        *,
        product_id: str | None = None,
        planning_cycle: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._user_insight_read_repository.list_iteration_plan_suggestions(
            planning_cycle=planning_cycle,
            product_id=product_id,
            status=status,
        )

    def list_user_insight_items(
        self,
        *,
        category: str | None = None,
        summary: str | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        return self._user_insight_read_repository.list_user_insight_items(
            category=category,
            summary=summary,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def load_lifecycle_context(self) -> dict[str, Any]:
        return self._lifecycle_dashboard_read_repository.load_lifecycle_context()

    def get_lifecycle_context_source_rows(
        self,
        *,
        product_id: str | None = None,
    ) -> dict[str, Any]:
        return self._lifecycle_dashboard_read_repository.get_lifecycle_context_source_rows(
            product_id=product_id,
        )

    def load_dashboard_snapshots(self) -> dict[str, Any]:
        return self._lifecycle_dashboard_read_repository.load_dashboard_snapshots()

    def get_dashboard_it_team_source_rows(
        self,
        *,
        user_roles: list[str],
        product_id: str | None = None,
    ) -> dict[str, Any]:
        return self._lifecycle_dashboard_read_repository.get_dashboard_it_team_source_rows(
            user_roles=user_roles,
            product_id=product_id,
        )

    def load_collector_runs(self) -> dict[str, Any]:
        return self._operational_collection_read_repository.load_collector_runs()

    def load_pending_attribution(self) -> dict[str, Any]:
        return self._operational_collection_read_repository.load_pending_attribution()

    def load_model_gateway(self) -> dict[str, Any]:
        return self._model_gateway_read_repository.load_model_gateway()

    def list_model_gateway_configs(self) -> list[dict[str, Any]]:
        return self._model_gateway_read_repository.list_model_gateway_configs()

    def list_ai_skills(
        self,
        *,
        code: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._scheduled_ai_job_read_repository.list_ai_skills(
            code=code,
            status=status,
        )

    def list_ai_agents(
        self,
        *,
        brain_app_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._scheduled_ai_job_read_repository.list_ai_agents(
            brain_app_id=brain_app_id,
            status=status,
        )

    def list_scheduled_jobs(
        self,
        *,
        enabled: bool | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._scheduled_ai_job_read_repository.list_scheduled_jobs(
            enabled=enabled,
            job_type=job_type,
            status=status,
        )

    def list_scheduled_job_runs(
        self,
        *,
        scheduled_job_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._scheduled_ai_job_read_repository.list_scheduled_job_runs(
            scheduled_job_id=scheduled_job_id,
            status=status,
        )

    def save_code_inspection_records(
        self,
        *,
        report: dict[str, Any],
        findings: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        return self._code_inspection_read_repository.save_code_inspection_records(
            report=report,
            findings=findings,
            notifications=notifications,
            audit_event=audit_event,
        )

    def list_code_inspection_reports(
        self,
        *,
        product_id: str | None = None,
        repository_id: str | None = None,
        risk_level: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._code_inspection_read_repository.list_code_inspection_reports(
            product_id=product_id,
            repository_id=repository_id,
            risk_level=risk_level,
            status=status,
        )

    def get_code_inspection_detail(self, report_id: str) -> dict[str, Any] | None:
        return self._code_inspection_read_repository.get_code_inspection_detail(report_id)

    def list_plugins(
        self,
        *,
        protocol: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_plugins(protocol=protocol, status=status)

    def list_plugin_connections(
        self,
        *,
        environment: str | None = None,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_plugin_connections(
            environment=environment,
            plugin_id=plugin_id,
            status=status,
        )

    def list_plugin_actions(
        self,
        *,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_plugin_actions(
            plugin_id=plugin_id,
            status=status,
        )

    def list_plugin_invocation_logs(
        self,
        *,
        action_id: str | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_plugin_invocation_logs(
            action_id=action_id,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )

    def list_ai_executor_runners(
        self,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_ai_executor_runners(status=status)

    def list_ai_executor_tasks(
        self,
        *,
        runner_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_ai_executor_tasks(
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )

    def list_model_gateway_logs(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._model_gateway_read_repository.list_model_gateway_logs(
            ai_task_id=ai_task_id,
            purpose=purpose,
            status=status,
        )

    def load_assistant_chat(self) -> dict[str, Any]:
        return self._assistant_chat_read_repository.load_assistant_chat()

    def list_assistant_conversations(self, *, user_id: str) -> list[dict[str, Any]]:
        return self._assistant_chat_read_repository.list_assistant_conversations(user_id=user_id)

    def list_assistant_conversation_messages(
        self,
        *,
        conversation_id: str,
        user_id: str,
    ) -> list[dict[str, Any]] | None:
        return self._assistant_chat_read_repository.list_assistant_conversation_messages(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    def load_gitlab_review(self) -> dict[str, Any]:
        return self._git_review_read_repository.load_gitlab_review()

    def load_mock_writebacks(self) -> dict[str, Any]:
        return self._mock_writeback_read_repository.load_mock_writebacks()

    def save_product_config(self, payload: dict[str, Any]) -> None:
        self._product_config_read_repository.save_product_config(payload)

    def save_product_config_record(
        self,
        collection_name: str,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._product_config_read_repository.save_product_config_record(
            collection_name,
            record,
            audit_event=audit_event,
        )

    def delete_product_config_record(
        self,
        collection_name: str,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._product_config_read_repository.delete_product_config_record(
            collection_name,
            record_id,
            audit_event=audit_event,
        )

    def save_requirements(self, payload: dict[str, Any]) -> None:
        self._requirement_read_repository.save_requirements(payload)

    def save_requirement_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._requirement_read_repository.save_requirement_record(
            record,
            audit_event=audit_event,
        )

    def delete_requirement_record(
        self,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._requirement_read_repository.delete_requirement_record(
            record_id,
            audit_event=audit_event,
        )

    def save_ai_tasks(self, payload: dict[str, Any]) -> None:
        self._task_read_repository.save_ai_tasks(payload)

    def save_ai_task_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._task_read_repository.save_ai_task_record(
            record,
            audit_event=audit_event,
        )

    def save_requirement_and_ai_task_records(
        self,
        *,
        requirement: dict[str, Any],
        task: dict[str, Any],
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._task_read_repository.save_requirement_and_ai_task_records(
            requirement=requirement,
            task=task,
            audit_event=audit_event,
        )

    def save_task_start_records(
        self,
        *,
        task: dict[str, Any],
        review: dict[str, Any],
        graph_run: dict[str, Any],
        checkpoint: dict[str, Any],
        audit_events: list[dict[str, Any]],
        model_log: dict[str, Any] | None = None,
        code_review_report: dict[str, Any] | None = None,
    ) -> None:
        self._task_read_repository.save_task_start_records(
            task=task,
            review=review,
            graph_run=graph_run,
            checkpoint=checkpoint,
            audit_events=audit_events,
            model_log=model_log,
            code_review_report=code_review_report,
        )

    def save_review_decision_records(
        self,
        *,
        task: dict[str, Any],
        review: dict[str, Any],
        graph_run: dict[str, Any] | None,
        checkpoint: dict[str, Any] | None,
        audit_events: list[dict[str, Any]],
        requirement: dict[str, Any] | None = None,
        knowledge_deposits: list[dict[str, Any]] | None = None,
        bugs: list[dict[str, Any]] | None = None,
        code_review_report: dict[str, Any] | None = None,
    ) -> None:
        self._task_read_repository.save_review_decision_records(
            task=task,
            review=review,
            graph_run=graph_run,
            checkpoint=checkpoint,
            audit_events=audit_events,
            requirement=requirement,
            knowledge_deposits=knowledge_deposits,
            bugs=bugs,
            code_review_report=code_review_report,
        )

    def save_task_state_records(
        self,
        *,
        task: dict[str, Any],
        audit_events: list[dict[str, Any]],
        reviews: list[dict[str, Any]] | None = None,
        graph_run: dict[str, Any] | None = None,
        checkpoint: dict[str, Any] | None = None,
        model_log: dict[str, Any] | None = None,
    ) -> None:
        self._task_read_repository.save_task_state_records(
            task=task,
            audit_events=audit_events,
            reviews=reviews,
            graph_run=graph_run,
            checkpoint=checkpoint,
            model_log=model_log,
        )

    def save_workflow_runtime(self, payload: dict[str, Any]) -> None:
        self._task_read_repository.save_workflow_runtime(payload)

    def save_knowledge(self, payload: dict[str, Any]) -> None:
        self._knowledge_read_repository.save_knowledge(payload)

    def claim_knowledge_import_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        lock_ttl_seconds: float,
    ) -> bool:
        return self._knowledge_read_repository.claim_knowledge_import_job(
            job_id=job_id,
            worker_id=worker_id,
            lock_ttl_seconds=lock_ttl_seconds,
        )

    def save_knowledge_document_records(
        self,
        *,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
        model_logs: list[dict[str, Any]] | None = None,
    ) -> None:
        self._knowledge_read_repository.save_knowledge_document_records(
            document=document,
            chunks=chunks,
            audit_event=audit_event,
            model_logs=model_logs,
        )

    def delete_knowledge_document_records(
        self,
        *,
        document_id: str,
        deposits: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._knowledge_read_repository.delete_knowledge_document_records(
            document_id=document_id,
            deposits=deposits,
            audit_event=audit_event,
        )

    def save_knowledge_deposit_records(
        self,
        *,
        deposit: dict[str, Any],
        audit_event: dict[str, Any] | None = None,
        document: dict[str, Any] | None = None,
        chunks: list[dict[str, Any]] | None = None,
        model_logs: list[dict[str, Any]] | None = None,
    ) -> None:
        self._knowledge_read_repository.save_knowledge_deposit_records(
            deposit=deposit,
            audit_event=audit_event,
            document=document,
            chunks=chunks,
            model_logs=model_logs,
        )

    def save_audit_events(self, payload: dict[str, Any]) -> None:
        self._audit_read_repository.save_audit_events(payload)

    def append_audit_event(self, audit_event: dict[str, Any]) -> None:
        self._audit_read_repository.append_audit_event(audit_event)

    def save_bugs(self, payload: dict[str, Any]) -> None:
        self._bug_read_repository.save_bugs(payload)

    def save_bug_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._bug_read_repository.save_bug_record(record, audit_event=audit_event)

    def delete_bug_record(
        self,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._bug_read_repository.delete_bug_record(record_id, audit_event=audit_event)

    def save_gitlab_daily_code_metrics(self, payload: dict[str, Any]) -> None:
        self._devops_read_repository.save_gitlab_daily_code_metrics(payload)

    def save_gitlab_daily_code_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._devops_read_repository.save_gitlab_daily_code_metric_record(
            record,
            audit_event=audit_event,
        )

    def save_jenkins_release_records(self, payload: dict[str, Any]) -> None:
        self._devops_read_repository.save_jenkins_release_records(payload)

    def save_jenkins_release_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._devops_read_repository.save_jenkins_release_record(
            record,
            audit_event=audit_event,
        )

    def save_online_log_metrics(self, payload: dict[str, Any]) -> None:
        self._devops_read_repository.save_online_log_metrics(payload)

    def save_online_log_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._devops_read_repository.save_online_log_metric_record(
            record,
            audit_event=audit_event,
        )

    def save_user_feedback(self, payload: dict[str, Any]) -> None:
        self._user_insight_read_repository.save_user_feedback(payload)

    def save_user_feedback_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._user_insight_read_repository.save_user_feedback_record(
            record,
            audit_event=audit_event,
        )

    def save_user_usage_metrics(self, payload: dict[str, Any]) -> None:
        self._user_insight_read_repository.save_user_usage_metrics(payload)

    def save_user_usage_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._user_insight_read_repository.save_user_usage_metric_record(
            record,
            audit_event=audit_event,
        )

    def save_iteration_planning(self, payload: dict[str, Any]) -> None:
        self._user_insight_read_repository.save_iteration_planning(payload)

    def save_iteration_suggestion_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._user_insight_read_repository.save_iteration_suggestion_record(
            record,
            audit_event=audit_event,
        )

    def save_iteration_decision_records(
        self,
        *,
        suggestion: dict[str, Any],
        decision: dict[str, Any],
        audit_events: list[dict[str, Any]],
        requirement: dict[str, Any] | None = None,
    ) -> None:
        self._user_insight_read_repository.save_iteration_decision_records(
            suggestion=suggestion,
            decision=decision,
            audit_events=audit_events,
            requirement=requirement,
        )

    def save_lifecycle_context(self, payload: dict[str, Any]) -> None:
        self._lifecycle_dashboard_read_repository.save_lifecycle_context(payload)

    def save_dashboard_snapshots(self, payload: dict[str, Any]) -> None:
        self._lifecycle_dashboard_read_repository.save_dashboard_snapshots(payload)

    def save_dashboard_metric_snapshot_record(self, snapshot: dict[str, Any]) -> None:
        self._lifecycle_dashboard_read_repository.save_dashboard_metric_snapshot_record(snapshot)

    def save_collector_runs(self, payload: dict[str, Any]) -> None:
        self._operational_collection_read_repository.save_collector_runs(payload)

    def save_collector_run_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._operational_collection_read_repository.save_collector_run_record(
            record,
            audit_event=audit_event,
        )

    def save_ai_skill_record(
        self,
        skill: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._scheduled_ai_job_read_repository.save_ai_skill_record(
            skill,
            audit_event=audit_event,
        )

    def save_ai_agent_record(
        self,
        agent: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._scheduled_ai_job_read_repository.save_ai_agent_record(
            agent,
            audit_event=audit_event,
        )

    def save_scheduled_job_record(
        self,
        job: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._scheduled_ai_job_read_repository.save_scheduled_job_record(
            job,
            audit_event=audit_event,
        )

    def delete_scheduled_job_record(
        self,
        job_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._scheduled_ai_job_read_repository.delete_scheduled_job_record(
            job_id,
            audit_event=audit_event,
        )

    def save_scheduled_job_run_record(
        self,
        run: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._scheduled_ai_job_read_repository.save_scheduled_job_run_record(
            run,
            audit_event=audit_event,
        )

    def save_plugin_record(
        self,
        plugin: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.save_plugin_record(plugin, audit_event=audit_event)

    def delete_plugin_record(
        self,
        plugin_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.delete_plugin_record(plugin_id, audit_event=audit_event)

    def save_plugin_connection_record(
        self,
        connection: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.save_plugin_connection_record(
            connection,
            audit_event=audit_event,
        )

    def delete_plugin_connection_record(
        self,
        connection_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.delete_plugin_connection_record(
            connection_id,
            audit_event=audit_event,
        )

    def save_plugin_action_record(
        self,
        action: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.save_plugin_action_record(
            action,
            audit_event=audit_event,
        )

    def delete_plugin_action_record(
        self,
        action_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.delete_plugin_action_record(
            action_id,
            audit_event=audit_event,
        )

    def save_plugin_invocation_log_record(
        self,
        log: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.save_plugin_invocation_log_record(
            log,
            audit_event=audit_event,
        )

    def save_ai_executor_runner_record(
        self,
        runner: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.save_ai_executor_runner_record(
            runner,
            audit_event=audit_event,
        )

    def delete_ai_executor_runner_record(
        self,
        runner_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.delete_ai_executor_runner_record(
            runner_id,
            audit_event=audit_event,
        )

    def save_ai_executor_task_record(
        self,
        task: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._plugin_read_repository.save_ai_executor_task_record(
            task,
            audit_event=audit_event,
        )

    def save_pending_attribution(self, payload: dict[str, Any]) -> None:
        self._operational_collection_read_repository.save_pending_attribution(payload)

    def save_pending_attribution_item_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._operational_collection_read_repository.save_pending_attribution_item_record(
            record,
            audit_event=audit_event,
        )

    def save_model_gateway(self, payload: dict[str, Any]) -> None:
        self._model_gateway_read_repository.save_model_gateway(payload)

    def save_model_gateway_records(
        self,
        payload: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._model_gateway_read_repository.save_model_gateway_records(
            payload,
            audit_event=audit_event,
        )

    def save_assistant_chat(self, payload: dict[str, Any]) -> None:
        self._assistant_chat_read_repository.save_assistant_chat(payload)

    def save_assistant_chat_records(
        self,
        *,
        conversation: dict[str, Any] | None,
        messages: list[dict[str, Any]],
        audit_events: list[dict[str, Any]],
        model_log: dict[str, Any] | None = None,
    ) -> None:
        self._assistant_chat_read_repository.save_assistant_chat_records(
            conversation=conversation,
            messages=messages,
            audit_events=audit_events,
            model_log=model_log,
        )

    def save_gitlab_review(self, payload: dict[str, Any]) -> None:
        self._git_review_read_repository.save_gitlab_review(payload)

    def save_gitlab_review_snapshot_record(
        self,
        *,
        snapshot: dict[str, Any] | None,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._git_review_read_repository.save_gitlab_review_snapshot_record(
            snapshot=snapshot,
            audit_event=audit_event,
        )

    def save_mock_writebacks(self, payload: dict[str, Any]) -> None:
        self._mock_writeback_read_repository.save_mock_writebacks(payload)

    def save_mock_writeback_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._mock_writeback_read_repository.save_mock_writeback_record(
            record,
            audit_event=audit_event,
        )
